"""Parse `workflows/*.yaml` — the repository's multi-skill pipelines.

A workflow is the unit an operator actually runs: "market regime daily" is four
ordered steps across three skills, producing named artifacts that later steps
consume. The YAML carries more than a step list — cadence, an api_profile, an
estimated duration, a `when_to_run` / `when_not_to_run` pair, a manual review
checklist, and per-step `decision_gate` flags.

Two of those deserve special handling in the UI rather than being flattened into
prose:

  * `when_not_to_run` is the author's own guardrail (typically "this posture is
    not a buy/sell signal"). It is surfaced before the run starts, not buried in
    a detail pane.
  * `decision_gate: true` marks a step that ends in a human judgement. The
    runner stops there and shows `decision_question` instead of racing on.

Japanese variants (`*_ja`) exist throughout the source files; they are kept so a
future locale can use them, but English is what the cockpit renders today.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Optional

import yaml

import config


@dataclass(frozen=True)
class Step:
    step: int
    name: str
    skill: str
    optional: bool = False
    consumes: tuple[str, ...] = ()
    produces: tuple[str, ...] = ()
    decision_gate: bool = False
    decision_question: str = ""
    name_ja: str = ""


@dataclass(frozen=True)
class Artifact:
    id: str
    produced_by_step: Optional[int] = None
    required: bool = True
    downstream_hints: tuple[str, ...] = ()


@dataclass(frozen=True)
class WorkflowMeta:
    id: str
    display_name: str
    cadence: str = ""
    estimated_minutes: Optional[int] = None
    difficulty: str = ""
    api_profile: str = ""
    when_to_run: str = ""
    when_not_to_run: str = ""
    required_skills: tuple[str, ...] = ()
    optional_skills: tuple[str, ...] = ()
    steps: tuple[Step, ...] = ()
    artifacts: tuple[Artifact, ...] = ()
    manual_review: tuple[str, ...] = ()
    journal_destination: str = ""
    source: Optional[Path] = None

    @property
    def skill_ids(self) -> tuple[str, ...]:
        seen: list[str] = []
        for s in self.steps:
            if s.skill and s.skill not in seen:
                seen.append(s.skill)
        return tuple(seen)

    @property
    def decision_gates(self) -> tuple[Step, ...]:
        return tuple(s for s in self.steps if s.decision_gate)


def _tup(value) -> tuple[str, ...]:
    if not value:
        return ()
    if isinstance(value, str):
        return (value,)
    return tuple(str(v).strip() for v in value if v is not None)


def _clean(value) -> str:
    return " ".join(str(value or "").split())


def _step(raw) -> Optional[Step]:
    if not isinstance(raw, dict) or not raw.get("skill"):
        return None
    try:
        number = int(raw.get("step") or 0)
    except Exception:
        number = 0
    return Step(
        step=number,
        name=_clean(raw.get("name")) or str(raw.get("skill")),
        skill=str(raw.get("skill")),
        optional=bool(raw.get("optional")),
        consumes=_tup(raw.get("consumes")),
        produces=_tup(raw.get("produces")),
        decision_gate=bool(raw.get("decision_gate")),
        decision_question=_clean(raw.get("decision_question")),
        name_ja=_clean(raw.get("name_ja")),
    )


def _artifact(raw) -> Optional[Artifact]:
    if not isinstance(raw, dict) or not raw.get("id"):
        return None
    step = raw.get("produced_by_step")
    try:
        step = int(step) if step is not None else None
    except Exception:
        step = None
    return Artifact(
        id=str(raw["id"]),
        produced_by_step=step,
        required=bool(raw.get("required", True)),
        downstream_hints=_tup(raw.get("downstream_hints")),
    )


def _workflow(path: Path) -> Optional[WorkflowMeta]:
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(raw, dict) or not raw.get("id"):
        return None
    minutes = raw.get("estimated_minutes")
    try:
        minutes = int(minutes) if minutes is not None else None
    except Exception:
        minutes = None
    steps = tuple(s for s in (_step(r) for r in (raw.get("steps") or [])) if s)
    return WorkflowMeta(
        id=str(raw["id"]),
        display_name=str(raw.get("display_name") or raw["id"]),
        cadence=str(raw.get("cadence") or ""),
        estimated_minutes=minutes,
        difficulty=str(raw.get("difficulty") or ""),
        api_profile=str(raw.get("api_profile") or ""),
        when_to_run=_clean(raw.get("when_to_run")),
        when_not_to_run=_clean(raw.get("when_not_to_run")),
        required_skills=_tup(raw.get("required_skills")),
        optional_skills=_tup(raw.get("optional_skills")),
        steps=tuple(sorted(steps, key=lambda s: s.step)),
        artifacts=tuple(a for a in (_artifact(r) for r in (raw.get("artifacts") or [])) if a),
        manual_review=_tup(raw.get("manual_review")),
        journal_destination=str(raw.get("journal_destination") or ""),
        source=path,
    )


@lru_cache(maxsize=4)
def _load(root_str: str) -> tuple[WorkflowMeta, ...]:
    directory = Path(root_str) / "workflows"
    if not directory.is_dir():
        return ()
    found = []
    for path in sorted(directory.glob("*.yaml")):
        wf = _workflow(path)
        if wf is not None:
            found.append(wf)
    return tuple(found)


def all_workflows(root: Path | None = None) -> tuple[WorkflowMeta, ...]:
    return _load(str(root or config.skills_root()))


def by_id(workflow_id: str, root: Path | None = None) -> Optional[WorkflowMeta]:
    for wf in all_workflows(root):
        if wf.id == workflow_id:
            return wf
    return None


def reload() -> None:
    _load.cache_clear()
