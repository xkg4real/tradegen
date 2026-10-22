"""In-process, headless runner for the `macro_daily` pipeline (section 3.9 L1191-1250; R-35; TASK-M8-01,
TASK-M8-06, TASK-M8-07; T-CLOSE-01 workflow clause, T-OBS-02, T-OBS-04, T-REPLAY-01; rulings 2 and 3.13).

Generic part only. The strict YAML loader (an unknown key or an unregistered step name refuses at load); the
ordered execution of skills and gates; the acting-step error rule (an error in `macro.pit_snapshot` ..
`verdict_filter` sets `acting_error`, skips the remaining acting compute steps except `macro.build_artifacts`,
blocks `macro.engine_feed`, pages RUN_ERROR; every other step error is recorded and paged, L1239-1245); the start
bound (`close_print_bound_utc + 10 min`: 06:40:29Z refused, 06:40:30Z starts, L1194); one artifact per decision (a
later run of a decision that already has a live row is a replay, L1199); the run record appended in `finally`
even when a step raised (L1237); `missed_decisions` (pure, L1246) and the canonical comparison of two artifacts
for a replay (R-01 rule 7). Steps and gates are `fn(ctx) -> dict` registered by `core.skills.macro_daily`;
`macro.run_record` is the runner's epilogue. Nothing here imports Flet, `core.skills.runner` or
`core.skills.workflows` (the legacy parser is untouched); clock, calendars and paths are injected.
"""
from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Callable, Iterable, Mapping
from zoneinfo import ZoneInfo

import yaml

from core.ficc.macro_schema import VOLATILE_FIELDS, canonical_json

ACTING_STEPS = ("macro.pit_snapshot", "data_ok", "macro.lag_audit", "macro.vol_and_overlays",
                "macro.build_artifacts", "bounds_ok", "verdict_filter")
RUN_MODES = ("live", "backtest", "replay")
STEP_KINDS = ("skill", "gate")
TOP_KEYS = frozenset({"name", "runs", "run_mode", "steps"})
START_DELAY = timedelta(minutes=10)                                   # L1194: no provisional row is read (R-01)
RUN_LOG = "run_log.jsonl"
RUN_ERROR = "RUN_ERROR"
EPILOGUE = "macro.run_record"
# ponytail: fixed opening times for the `late` test (L5311) and the ingest deadline; the signed session rows
# (core.calendars.clocks.session) carry the real ones once the owner signs the calendars.
OPEN_LOCAL = {"KR": ("09:00", "Asia/Seoul"), "US": ("09:30", "America/New_York"), "JP": ("09:00", "Asia/Tokyo"),
              "CN": ("09:30", "Asia/Shanghai"), "HK": ("09:30", "Asia/Hong_Kong"), "TW": ("09:00", "Asia/Taipei")}


class PipelineLoadError(ValueError):
    """The YAML names something the runner does not know: refused at load (fail closed)."""


class TooEarly(Exception):
    """`clock()` is before `close_print_bound_utc + 10 min`: nothing is read, nothing is written."""


@dataclass(frozen=True)
class PipelineStep:
    kind: str
    name: str


@dataclass(frozen=True)
class Pipeline:
    name: str
    runs: tuple[tuple[str, str], ...]
    run_mode: str
    steps: tuple[PipelineStep, ...]
    source: Path

    @property
    def step_names(self) -> tuple[str, ...]:
        return tuple(s.name for s in self.steps)


def load_pipeline(path, *, known_steps: Iterable[str], known_gates: Iterable[str]) -> Pipeline:
    """Strict reader of `core/skills/macro_workflows/*.yaml` (section 3.9 shape: name, runs, run_mode, steps of
    `skill:` or `gate:`). Never routed through `core.skills.workflows` (code_skills_workflows D.2)."""
    path = Path(path)
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(doc, dict):
        raise PipelineLoadError(f"{path.name}: top level must be a mapping")
    extra = sorted(set(doc) - TOP_KEYS)
    if extra:
        raise PipelineLoadError(f"{path.name}: unknown key(s) {extra}")
    name = doc.get("name")
    if not isinstance(name, str) or not name:
        raise PipelineLoadError(f"{path.name}: name must be a non-empty string")
    runs = []
    for r in doc.get("runs") or []:
        if isinstance(r, dict) and len(r) == 1:
            (k, v), = r.items()
            runs.append((str(k), str(v)))
        elif isinstance(r, str) and ":" in r:
            k, v = r.split(":", 1)
            runs.append((k.strip(), v.strip()))
        else:
            raise PipelineLoadError(f"{path.name}: runs entry {r!r} is not `after_close: <venue>`")
    mode = doc.get("run_mode")
    if mode not in RUN_MODES:
        raise PipelineLoadError(f"{path.name}: run_mode {mode!r} not in {RUN_MODES}")
    known = {"skill": set(known_steps), "gate": set(known_gates)}
    steps = []
    for i, raw in enumerate(doc.get("steps") or [], start=1):
        if not isinstance(raw, dict) or len(raw) != 1 or next(iter(raw)) not in STEP_KINDS:
            raise PipelineLoadError(f"{path.name}: step {i} must be exactly one of `skill: <name>` / `gate: <name>`")
        kind, sname = next(iter(raw.items()))
        if sname not in known[kind]:
            raise PipelineLoadError(f"{path.name}: step {i} names an unregistered {kind} {sname!r}")
        steps.append(PipelineStep(kind, str(sname)))
    if not steps:
        raise PipelineLoadError(f"{path.name}: no steps")
    return Pipeline(name, tuple(runs), mode, tuple(steps), path)


# --------------------------------------------------------------------------- #
# Clock arithmetic (injected `clocks`: close_print_bound_utc, is_session)
# --------------------------------------------------------------------------- #
def earliest_start_utc(clocks, market: str, session_date: date) -> datetime:
    return clocks.close_print_bound_utc(market, session_date) + START_DELAY


def next_session(clocks, market: str, d: date, max_days: int = 45) -> date:
    probe = d
    for _ in range(max_days):
        probe += timedelta(days=1)
        if clocks.is_session(market, probe):
            return probe
    raise ValueError(f"{market}: no session within {max_days} days after {d}")


def next_open_utc(clocks, market: str, session_date: date) -> datetime:
    """The next session's opening instant (the `late` bound, L5311; the ingest deadline is 30 min before it)."""
    hhmm, tz = OPEN_LOCAL[market]
    d = next_session(clocks, market, session_date)
    hh, mm = (int(x) for x in hhmm.split(":"))
    return datetime(d.year, d.month, d.day, hh, mm, tzinfo=ZoneInfo(tz)).astimezone(ZoneInfo("UTC"))


def run_id_for(name: str, now: datetime) -> str:
    return f"{now.strftime('%Y%m%d-%H%M%S')}-{name}-{uuid.uuid4().hex[:6]}"


def iso(dt: datetime | None) -> str | None:
    return None if dt is None else dt.astimezone(ZoneInfo("UTC")).strftime("%Y-%m-%dT%H:%M:%SZ")


# --------------------------------------------------------------------------- #
# Run context and the runner
# --------------------------------------------------------------------------- #
@dataclass
class RunContext:
    """The one mutable object of a run; steps read `services` and leave their results in `state`."""
    market: str
    session_date: date
    decision_utc: datetime
    run_mode: str
    run_id: str
    started_utc: datetime
    clock: Callable[[], datetime]
    services: object = None
    knowledge_utc: datetime | None = None
    acting_error: bool = False
    late: bool = False
    step_results: list = field(default_factory=list)
    feed_blocked: dict = field(default_factory=dict)           # book_id -> reason (verdict_filter mismatch)
    artifacts: list = field(default_factory=list)              # relative paths written this run
    state: dict = field(default_factory=dict)

    def pin_knowledge(self, when: datetime) -> datetime:
        """`data.knowledge_utc.pinned_once_per_run`: the first pin wins, a later call never moves it."""
        if self.knowledge_utc is None:
            if when is None or when.tzinfo is None:
                raise ValueError("knowledge_utc must be a tz-aware instant (never 'now' by default, L4197)")
            self.knowledge_utc = when
        return self.knowledge_utc

    def record(self, step: PipelineStep, status: str, **extra) -> dict:
        row = {"name": step.name, "kind": step.kind, "status": status, "error": None, **extra}
        self.step_results.append(row)
        return row


def _page(alerts, code: str, ctx: RunContext, *, component: str, detail: str) -> None:
    if alerts is None:
        return
    alerts.raise_alert(code, "page", component, when=ctx.decision_utc, detail=detail,
                       books=(f"recommended:{ctx.market}", f"specification:{ctx.market}"))


def live_row(path: Path, market: str, session_date: date) -> dict | None:
    rows = [r for r in read_run_log(path) if r.get("market") == market and r.get("session_date") == session_date.isoformat()
            and r.get("run_mode", "live") == "live"]
    return rows[-1] if rows else None


def has_live_row(path: Path, market: str, session_date: date) -> bool:
    return live_row(path, market, session_date) is not None


def parse_iso(text: str) -> datetime:
    return datetime.fromisoformat(text.replace("Z", "+00:00"))


def run_pipeline(p: Pipeline, *, market: str, session_date: date, clock: Callable[[], datetime], clocks,
                 steps: Mapping[str, Callable], gates: Mapping[str, Callable], run_log, services=None,
                 run_mode: str | None = None, knowledge_utc: datetime | None = None, alerts=None, on_start=None) -> dict:
    """Run one decision of `market` and return the run record (also appended to `run_log`). Raises `TooEarly`
    before the start bound and `NotASession` on a non-session; nothing else propagates past the run record."""
    decision_utc = clocks.close_print_bound_utc(market, session_date)
    mode = run_mode or p.run_mode
    if mode not in RUN_MODES:
        raise ValueError(f"run_mode {mode!r} not in {RUN_MODES}")
    now = clock()
    if mode == "live" and now < earliest_start_utc(clocks, market, session_date):
        raise TooEarly(f"{market} {session_date}: {iso(now)} is before the start bound "
                       f"{iso(earliest_start_utc(clocks, market, session_date))} (close_print_bound_utc + 10 min, L1194)")
    run_log = Path(run_log)
    earlier = live_row(run_log, market, session_date) if mode == "live" else None
    if earlier is not None:
        mode = "replay"                                        # L1199: never a second forward decision
        if knowledge_utc is None and earlier.get("knowledge_utc"):
            knowledge_utc = parse_iso(earlier["knowledge_utc"])   # the audit re-reads at the decision's own knowledge instant
    ctx = RunContext(market, session_date, decision_utc, mode, run_id_for(p.name, now), now, clock, services,
                     knowledge_utc=knowledge_utc)
    if mode == "live":
        try:
            ctx.late = now > next_open_utc(clocks, market, session_date)
        except Exception:                                      # no next session in coverage: not late, recorded by the steps
            ctx.late = False
    status = "ok"
    record: dict = {}
    try:
        if on_start is not None:
            on_start(ctx)
        for step in p.steps:
            if step.name == EPILOGUE:
                continue
            fn = (steps if step.kind == "skill" else gates)[step.name]
            if ctx.acting_error and step.name in ACTING_STEPS and step.name != "macro.build_artifacts":
                ctx.record(step, "skipped", reason="an earlier acting step raised (L1241)")
                continue
            if step.name == "macro.engine_feed" and (ctx.acting_error or mode != "live" or ctx.late):
                why = ("acting-step error: the books carry their weights (L1242)" if ctx.acting_error
                       else f"run_mode {mode}: audit / dry run only" if mode != "live" else "late run: display only (L5311)")
                ctx.record(step, "blocked", reason=why)
                continue
            try:
                out = fn(ctx)
                st = "fail" if isinstance(out, Mapping) and out.get("status") == "fail" else "ok"
                ctx.record(step, st, result=out if isinstance(out, Mapping) else None)
            except Exception as exc:                           # noqa: BLE001  (every step error is recorded, L1239)
                err = f"{type(exc).__name__}: {exc}"
                ctx.record(step, "error", error=err)
                status = "error"
                if step.name in ACTING_STEPS:
                    ctx.acting_error = True
                _page(alerts, RUN_ERROR, ctx, component=step.name, detail=err)
    finally:
        finished = clock()
        prov = ctx.state.get("provenance") or {}
        record = {"run_id": ctx.run_id, "market": market, "session_date": session_date.isoformat(),
                  "decision_utc": iso(decision_utc), "knowledge_utc": iso(ctx.knowledge_utc),
                  "started_utc": iso(ctx.started_utc), "finished_utc": iso(finished), "run_mode": mode,
                  "status": status, "late": bool(ctx.late), "acting_error": bool(ctx.acting_error),
                  "git_hash": prov.get("git_hash", "UNVERSIONED"), "tree_hash": prov.get("tree_hash"),
                  "config_hash": prov.get("config_hash"), "data_snapshot_id": prov.get("data_snapshot_id"),
                  "artifacts": list(ctx.artifacts)}
        epilogue = steps.get(EPILOGUE)
        if epilogue is not None:
            try:
                extra = epilogue(ctx) or {}
                record.update({k: v for k, v in extra.items() if k not in record})
                ctx.record(PipelineStep("skill", EPILOGUE), "ok")
            except Exception as exc:                           # noqa: BLE001
                err = f"{type(exc).__name__}: {exc}"
                ctx.record(PipelineStep("skill", EPILOGUE), "error", error=err)
                record["status"] = "error"
                _page(alerts, RUN_ERROR, ctx, component=EPILOGUE, detail=err)
        record["steps"] = list(ctx.step_results)
        append_run_record(record, run_log)
    return record


# --------------------------------------------------------------------------- #
# run_log.jsonl
# --------------------------------------------------------------------------- #
def append_run_record(record: dict, path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "ab") as fh:                               # append-only, binary, LF; raises (rulings 5)
        fh.write(canonical_json(record).encode("utf-8") + b"\n")
        fh.flush()
        os.fsync(fh.fileno())


def read_run_log(path) -> list[dict]:
    """Run rows only (a context writer's error line, written by `run_context_step`, carries no run_id)."""
    path = Path(path)
    if not path.is_file():
        return []
    rows = [json.loads(line) for line in path.read_bytes().decode("utf-8").split("\n") if line.strip()]
    return [r for r in rows if isinstance(r, dict) and r.get("run_id")]


def missed_decisions(expected: Iterable[tuple[str, date, datetime]], rows: Iterable[dict]) -> list[dict]:
    """Pure (L1246-1247): a decision with no live run row, or whose every live row has an acting-step error, is
    missed (a later replay never cures it, F-12). Returns one dict per missed decision."""
    by: dict[tuple[str, str], list[dict]] = {}
    for r in rows:
        if r.get("run_mode", "live") == "live":
            by.setdefault((r.get("market"), r.get("session_date")), []).append(r)
    out = []
    for market, d, decision_utc in expected:
        key = (market, d.isoformat() if isinstance(d, date) else str(d))
        live = by.get(key, [])
        if not live:
            reason = "no_run"
        elif all(r.get("acting_error") for r in live):
            reason = "acting_step_error"
        else:
            continue
        out.append({"market": market, "session_date": key[1], "decision_utc": iso(decision_utc) if isinstance(decision_utc, datetime) else decision_utc,
                    "reason": reason})
    return out


# --------------------------------------------------------------------------- #
# Replay comparison (R-01 rule 7; reproducibility.determinism, L4683)
# --------------------------------------------------------------------------- #
def canonical_bytes(artifact: Mapping, ignore: Iterable[str] = ()) -> bytes:
    """UTF-8 JSON, sorted keys, repr floats, no insignificant whitespace; the volatile fields (and `ignore`) excluded."""
    skip = set(VOLATILE_FIELDS) | set(ignore)
    return canonical_json({k: v for k, v in artifact.items() if k not in skip}).encode("utf-8")


def compare_artifacts(a: Mapping, b: Mapping, ignore: Iterable[str] = ()) -> list[str]:
    """Top-level keys whose canonical bytes differ ([] = byte-identical after canonicalisation)."""
    if canonical_bytes(a, ignore) == canonical_bytes(b, ignore):
        return []
    keys = sorted((set(a) | set(b)) - set(VOLATILE_FIELDS) - set(ignore))
    return [k for k in keys if canonical_json(a.get(k)) != canonical_json(b.get(k))]


__all__ = [n for n in dir() if not n.startswith("_")]
