"""Parse `skills-index.yaml` into typed metadata.

The index is the trading-skills repository's own manifest — 72 entries, each
declaring category, status, summary, timeframe, difficulty, integrations,
inputs, outputs, and the workflows it participates in. NEXTGEN treats it as the
single source of truth for *what exists*; `entrypoints.py` answers *what can
actually run*, and `readiness.py` answers *what can run right now*.

Parsing is defensive on purpose: the index is maintained in another repository
and a missing or renamed field must degrade one skill card, never the app.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Optional

import yaml

import config


@dataclass(frozen=True)
class Integration:
    id: str
    type: str = ""
    requirement: str = "required"   # required | recommended | optional | not_required
    note: str = ""

    @property
    def blocking(self) -> bool:
        return self.requirement == "required"


@dataclass(frozen=True)
class SkillMeta:
    id: str
    display_name: str
    category: str = ""
    status: str = ""                # production | beta
    summary: str = ""
    timeframe: str = ""
    difficulty: str = ""
    integrations: tuple[Integration, ...] = ()
    inputs: tuple[str, ...] = ()
    outputs: tuple[str, ...] = ()
    workflows: tuple[str, ...] = ()

    @property
    def directory(self) -> Path:
        return config.skills_root() / "skills" / self.id

    @property
    def skill_md(self) -> Path:
        return self.directory / "SKILL.md"

    def integration_ids(self) -> tuple[str, ...]:
        return tuple(i.id for i in self.integrations)


def _as_tuple(value) -> tuple[str, ...]:
    if not value:
        return ()
    if isinstance(value, str):
        return (value,)
    return tuple(str(v) for v in value if v is not None)


def _integration(raw) -> Optional[Integration]:
    if not isinstance(raw, dict) or not raw.get("id"):
        return None
    return Integration(
        id=str(raw.get("id")),
        type=str(raw.get("type") or ""),
        requirement=str(raw.get("requirement") or "required"),
        note=str(raw.get("note") or ""),
    )


def _skill(raw) -> Optional[SkillMeta]:
    if not isinstance(raw, dict) or not raw.get("id"):
        return None
    sid = str(raw["id"])
    integrations = tuple(
        i for i in (_integration(r) for r in (raw.get("integrations") or [])) if i
    )
    return SkillMeta(
        id=sid,
        display_name=str(raw.get("display_name") or sid.replace("-", " ").title()),
        category=str(raw.get("category") or ""),
        status=str(raw.get("status") or ""),
        summary=str(raw.get("summary") or "").strip(),
        timeframe=str(raw.get("timeframe") or ""),
        difficulty=str(raw.get("difficulty") or ""),
        integrations=integrations,
        inputs=_as_tuple(raw.get("inputs")),
        outputs=_as_tuple(raw.get("outputs")),
        workflows=_as_tuple(raw.get("workflows")),
    )


@lru_cache(maxsize=4)
def _load(root_str: str) -> tuple[SkillMeta, ...]:
    path = Path(root_str) / "skills-index.yaml"
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception:
        return ()
    if not isinstance(raw, dict):
        return ()
    skills = tuple(s for s in (_skill(r) for r in (raw.get("skills") or [])) if s)
    return tuple(sorted(skills, key=lambda s: s.display_name.casefold()))


def all_skills(root: Path | None = None) -> tuple[SkillMeta, ...]:
    return _load(str(root or config.skills_root()))


def by_id(skill_id: str, root: Path | None = None) -> Optional[SkillMeta]:
    for s in all_skills(root):
        if s.id == skill_id:
            return s
    return None


def categories(root: Path | None = None) -> tuple[str, ...]:
    seen: list[str] = []
    for s in all_skills(root):
        if s.category and s.category not in seen:
            seen.append(s.category)
    return tuple(sorted(seen))


def reload() -> None:
    """Drop the parse cache so a Settings change or repo edit is picked up."""
    _load.cache_clear()
