"""Persistent run history.

Each run owns a directory under `~/.nextgen/runs/<run_id>/` containing whatever
the skill wrote plus `transcript.log` and `run.json`. This module only handles
the index: append a record, list recent records newest-first, and reload one.

History is deliberately file-backed rather than a database. The artifacts are
already files, the transcript is already a file, and an operator inspecting a
bad run should be able to open the folder without NEXTGEN running.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import config
from core.skills.runner import RunResult


@dataclass(frozen=True)
class RunRecord:
    run_id: str
    skill_id: str
    entrypoint: str
    status: str
    exit_code: Optional[int]
    started_at: str
    finished_at: str
    duration_s: float
    run_dir: Path
    artifacts: tuple[str, ...]
    error: str = ""
    workflow_id: str = ""

    @property
    def ok(self) -> bool:
        return self.status == "ok"

    def transcript(self) -> str:
        path = self.run_dir / "transcript.log"
        try:
            return path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return "(transcript unavailable)"


def record(result: RunResult, *, workflow_id: str = "") -> RunRecord:
    """Write `run.json` next to the artifacts and return the indexed record."""
    payload = result.to_record()
    payload["workflow_id"] = workflow_id
    try:
        (result.run_dir / "run.json").write_text(
            json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
        )
    except Exception:
        pass
    return _from_payload(payload)


def _from_payload(payload: dict) -> RunRecord:
    return RunRecord(
        run_id=str(payload.get("run_id") or ""),
        skill_id=str(payload.get("skill_id") or ""),
        entrypoint=str(payload.get("entrypoint") or ""),
        status=str(payload.get("status") or ""),
        exit_code=payload.get("exit_code"),
        started_at=str(payload.get("started_at") or ""),
        finished_at=str(payload.get("finished_at") or ""),
        duration_s=float(payload.get("duration_s") or 0.0),
        run_dir=Path(str(payload.get("run_dir") or "")),
        artifacts=tuple(payload.get("artifacts") or ()),
        error=str(payload.get("error") or ""),
        workflow_id=str(payload.get("workflow_id") or ""),
    )


def recent(limit: int = 100) -> tuple[RunRecord, ...]:
    root = config.runs_dir()
    if not root.is_dir():
        return ()
    records: list[RunRecord] = []
    for directory in sorted(root.iterdir(), reverse=True):
        if not directory.is_dir():
            continue
        manifest = directory / "run.json"
        if not manifest.is_file():
            continue
        try:
            records.append(_from_payload(json.loads(manifest.read_text(encoding="utf-8"))))
        except Exception:
            continue
        if len(records) >= limit:
            break
    return tuple(records)


def by_id(run_id: str) -> Optional[RunRecord]:
    manifest = config.runs_dir() / run_id / "run.json"
    try:
        return _from_payload(json.loads(manifest.read_text(encoding="utf-8")))
    except Exception:
        return None


def latest_for_skill(skill_id: str) -> Optional[RunRecord]:
    for rec in recent(limit=250):
        if rec.skill_id == skill_id:
            return rec
    return None
