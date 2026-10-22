"""Execute a skill script as a subprocess and capture everything it produced.

Design points that matter:

  * **Working directory is the run directory, not the skill directory.** Skill
    scripts insert their own folder onto `sys.path`, so imports work from
    anywhere, but most of them write reports relative to the current directory.
    Running inside a fresh per-run folder means artifacts land where NEXTGEN can
    find them and never pollute the skills repository.

  * **Credentials are passed by environment only.** `config.skill_env()` builds
    the child environment; nothing in this module reads a key's value, and the
    transcript written to disk contains only the argv, never the env.

  * **Output is streamed, not buffered to completion.** Screener skills run for
    minutes; the UI needs to show progress. `on_line` fires per line on the
    reader thread, so callers marshal to the UI thread themselves.

  * **Timeout kills the process tree.** A hung HTTP call inside a skill must not
    strand the cockpit; on Windows the child is terminated via taskkill so
    grandchildren die with it.
"""
from __future__ import annotations

import os
import re
import shlex
import subprocess
import sys
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional, Sequence

import config
from core.skills.diagnose import Cause, Diagnosis, diagnose
from core.skills.entrypoints import Entrypoint

_ARTIFACT_SUFFIXES = {".json", ".md", ".csv", ".html", ".yaml", ".yml", ".txt", ".png"}

# Two-layer masking, applied before a line is stored or shown.
#
# 1. Exact match against the credentials actually configured. This is the real
#    guarantee: if a skill or a stack trace echoes a key, it is caught whatever
#    shape it has.
# 2. A conservative heuristic for unconfigured secrets — a 32+ character run of
#    *pure* alphanumerics. Separators are deliberately excluded so that report
#    filenames like `market_breadth_2026-08-18_152347.json` are left intact; an
#    earlier version included `_` and `-` and mangled every artifact name in the
#    transcript.
_OPAQUE = re.compile(r"\b[A-Za-z0-9]{32,}\b")


def _mask(token: str) -> str:
    return f"{token[:4]}…{token[-2:]}" if len(token) > 8 else "…"


def _configured_secrets() -> tuple[str, ...]:
    values = []
    for names in config.SKILL_CREDENTIALS.values():
        for name in names:
            value = config._clean(name)
            if len(value) >= 8:
                values.append(value)
    # Longest first so a key that contains another is masked whole.
    return tuple(sorted(set(values), key=len, reverse=True))


def _redact(line: str) -> str:
    for secret in _configured_secrets():
        if secret in line:
            line = line.replace(secret, _mask(secret))
    return _OPAQUE.sub(lambda m: _mask(m.group(0)), line)


class Status(str):
    RUNNING = "running"
    OK = "ok"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"
    ERROR = "error"


@dataclass
class RunResult:
    run_id: str
    skill_id: str
    entrypoint: str
    argv: tuple[str, ...]
    status: str
    exit_code: Optional[int]
    started_at: str
    finished_at: str
    duration_s: float
    run_dir: Path
    stdout: str = ""
    stderr: str = ""
    artifacts: tuple[Path, ...] = ()
    error: str = ""
    diagnosis: Optional[Diagnosis] = None

    @property
    def ok(self) -> bool:
        return self.status == Status.OK

    @property
    def cause(self) -> Cause:
        return self.diagnosis.cause if self.diagnosis else Cause.UNKNOWN

    @property
    def headline(self) -> str:
        """One line saying what happened, for the status row.

        Never falls back to the bare exit code: that was the original
        complaint, since `exit code 2` names the mechanism and not the cause.
        """
        if self.diagnosis is not None:
            return self.diagnosis.headline
        return self.error or ("Completed." if self.ok else "Did not complete.")

    def to_record(self) -> dict:
        return {
            "run_id": self.run_id,
            "skill_id": self.skill_id,
            "entrypoint": self.entrypoint,
            "argv": list(self.argv),
            "status": self.status,
            "exit_code": self.exit_code,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_s": round(self.duration_s, 3),
            "run_dir": str(self.run_dir),
            "artifacts": [a.name for a in self.artifacts],
            "error": self.error,
            "cause": self.cause.value,
            "headline": self.headline,
        }


class RunHandle:
    """Cancellation token handed back to the UI while a run is in flight."""

    def __init__(self) -> None:
        self._proc: Optional[subprocess.Popen] = None
        self._cancelled = threading.Event()
        self._lock = threading.Lock()

    def _attach(self, proc: subprocess.Popen) -> None:
        with self._lock:
            self._proc = proc
            if self._cancelled.is_set():
                _kill(proc)

    @property
    def cancelled(self) -> bool:
        return self._cancelled.is_set()

    def cancel(self) -> None:
        self._cancelled.set()
        with self._lock:
            if self._proc is not None:
                _kill(self._proc)


def _kill(proc: subprocess.Popen) -> None:
    if proc.poll() is not None:
        return
    try:
        if os.name == "nt":
            # Kill the whole tree; a skill may have spawned a helper.
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                capture_output=True, check=False,
            )
        else:
            proc.terminate()
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass


def _new_run_dir(skill_id: str) -> tuple[str, Path]:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    run_id = f"{stamp}-{skill_id}-{uuid.uuid4().hex[:6]}"
    path = config.runs_dir() / run_id
    path.mkdir(parents=True, exist_ok=True)
    return run_id, path


def _collect_artifacts(run_dir: Path) -> tuple[Path, ...]:
    out = []
    for path in sorted(run_dir.rglob("*")):
        if path.is_file() and path.suffix.lower() in _ARTIFACT_SUFFIXES:
            if path.name in {"transcript.log", "run.json"}:
                continue
            out.append(path)
    return tuple(out)


def run_skill(
    entrypoint: Entrypoint,
    args: Sequence[str] = (),
    *,
    on_line: Optional[Callable[[str], None]] = None,
    timeout_s: Optional[float] = None,
    handle: Optional[RunHandle] = None,
) -> RunResult:
    """Run one skill script to completion. Blocking; call from a worker thread."""
    timeout_s = timeout_s or config.SKILL_TIMEOUT_SECONDS
    handle = handle or RunHandle()
    run_id, run_dir = _new_run_dir(entrypoint.skill_id)
    argv = (config.skill_python(), str(entrypoint.path), *args)
    started = time.perf_counter()
    started_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    lines: list[str] = []

    def emit(text: str) -> None:
        clean = _redact(text.rstrip("\r\n"))
        lines.append(clean)
        if on_line is not None:
            try:
                on_line(clean)
            except Exception:
                pass

    emit(f"$ {shlex.join(argv[1:])}")
    emit(f"# cwd={run_dir}")

    status = Status.OK
    exit_code: Optional[int] = None
    error = ""

    try:
        proc = subprocess.Popen(
            argv,
            cwd=str(run_dir),
            env=config.skill_env(),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )
    except Exception as exc:                     # interpreter missing, bad path
        finished = time.perf_counter()
        return RunResult(
            run_id=run_id, skill_id=entrypoint.skill_id, entrypoint=entrypoint.name,
            argv=argv[1:], status=Status.ERROR, exit_code=None,
            started_at=started_at,
            finished_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            duration_s=finished - started, run_dir=run_dir,
            stdout="\n".join(lines), error=f"{type(exc).__name__}: {exc}",
        )

    handle._attach(proc)

    def pump() -> None:
        assert proc.stdout is not None
        for raw in proc.stdout:
            emit(raw)

    reader = threading.Thread(target=pump, name=f"skillrun-{run_id}", daemon=True)
    reader.start()

    try:
        exit_code = proc.wait(timeout=timeout_s)
    except subprocess.TimeoutExpired:
        _kill(proc)
        status = Status.TIMEOUT
        error = f"exceeded {timeout_s:.0f}s timeout"
        try:
            exit_code = proc.wait(timeout=10)
        except Exception:
            exit_code = None
    reader.join(timeout=5)

    if handle.cancelled:
        status = Status.CANCELLED
        error = error or "cancelled by operator"
    elif status == Status.OK and exit_code != 0:
        status = Status.FAILED
        error = f"exit code {exit_code}"

    duration = time.perf_counter() - started
    transcript = "\n".join(lines)
    verdict = diagnose(status=status, exit_code=exit_code,
                       stdout=transcript, error=error)
    result = RunResult(
        run_id=run_id,
        skill_id=entrypoint.skill_id,
        entrypoint=entrypoint.name,
        argv=tuple(argv[1:]),
        status=status,
        exit_code=exit_code,
        started_at=started_at,
        finished_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        duration_s=duration,
        run_dir=run_dir,
        stdout=transcript,
        artifacts=_collect_artifacts(run_dir),
        error=error,
        diagnosis=verdict,
    )
    _write_transcript(result)
    return result


def _write_transcript(result: RunResult) -> None:
    try:
        (result.run_dir / "transcript.log").write_text(result.stdout, encoding="utf-8")
    except Exception:
        pass


def describe_args(entrypoint: Entrypoint, *, timeout_s: float = 20) -> str:
    """Return the script's own `--help` text, so the UI never guesses its flags."""
    try:
        proc = subprocess.run(
            [config.skill_python(), str(entrypoint.path), "--help"],
            cwd=str(entrypoint.path.parent),
            env=config.skill_env(),
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=timeout_s,
        )
    except Exception as exc:
        return f"(could not read --help: {type(exc).__name__})"
    text = (proc.stdout or proc.stderr or "").strip()
    return _redact(text) if text else "(this script declares no --help output)"
