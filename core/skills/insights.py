"""Read what a step actually concluded, in a shape the UI can draw.

A workflow step ends with a wall of transcript and a JSON report on disk. That
is fine for research and useless at a decision gate: when the cockpit stops and
asks whether new risk is allowed, restricted, or cash-priority, the operator
should not have to scroll back through four hundred lines to remember that
breadth scored 79 and uptrend participation scored 29.

Most scoring skills in the repository share a report convention — a composite
score, a zone, an exposure band, and a set of weighted components each with its
own score and a one-line `signal`. Eleven skills emit `component_scores`;
twenty-one emit a `composite_score`. This module normalises that into one
`Insight`, which the gate summary reads as sentences and the bar chart reads as
numbers.

Nothing here computes or interprets. Every number is copied out of the report
the skill wrote, and a field that is absent stays absent rather than being
filled with a default — a composite of `None` is drawn as "no score", never as
zero. The judgement at the gate belongs to the operator, so this module's only
job is to put the skill's own findings where they can be seen at once.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, Sequence

MAX_FACTS = 8
MAX_COMPONENTS = 12

# Report plumbing rather than findings: never shown as a fact.
_SKIP_FACT = re.compile(
    r"url|uri|path|dir|file|schema|version|generated|timestamp|_at$|^id$|"
    r"api_key|_key$|elapsed|runtime|"
    # Already rendered as the score, the zone and the exposure band.
    r"^composite_score|^zone|^exposure_guidance",
    re.IGNORECASE,
)
# Decoration the scripts print around their summaries, plus the scaffolding of
# a Python traceback. The caret rows CPython emits under a failing expression
# are the least useful six lines a transcript can end with, and ending on them
# is exactly what a crashing script does.
_RULE = re.compile(r"^[=\-_*~^#\s]+$")
_FRAME = re.compile(r'^(?:File ".*", line \d+|Traceback \(most recent call last\):)')


@dataclass(frozen=True)
class Component:
    """One scored part of a skill's verdict."""
    key: str
    label: str
    score: float
    weight: float = 0.0
    signal: str = ""

    @property
    def band(self) -> str:
        """Palette token for the score. Always paired with the printed number —
        colour is a second channel here, never the only one."""
        if self.score >= 70:
            return "success"
        if self.score >= 40:
            return "accent"
        return "error"


@dataclass(frozen=True)
class Insight:
    skill_id: str = ""
    source: Optional[Path] = None
    score: Optional[float] = None
    zone: str = ""
    guidance: str = ""
    components: tuple[Component, ...] = ()
    warnings: tuple[str, ...] = ()
    facts: tuple[tuple[str, str], ...] = ()
    quality: str = ""
    lines: tuple[str, ...] = ()

    @property
    def empty(self) -> bool:
        return not (self.components or self.facts or self.lines
                    or self.score is not None)

    @property
    def band(self) -> str:
        if self.score is None:
            return "muted"
        return Component("", "", self.score).band

    @property
    def headline(self) -> str:
        """One line naming the finding, for the step row and the gate digest."""
        bits = []
        if self.score is not None:
            bits.append(f"{self.score:g}/100")
        if self.zone:
            bits.append(self.zone)
        if self.guidance:
            bits.append(self.guidance)
        if bits:
            return " — ".join(bits)
        if self.facts:
            return ", ".join(f"{k} {v}" for k, v in self.facts[:3])
        return self.lines[-1] if self.lines else ""


# --------------------------------------------------------------------------- #
# Report readers
# --------------------------------------------------------------------------- #
def _number(value: Any) -> Optional[float]:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _label_for(key: str) -> str:
    return key.replace("_", " ").replace("-", " ").strip().capitalize()


def _components(report: dict) -> tuple[Component, ...]:
    """`composite.component_scores`, or a flat `component_scores` map."""
    composite = report.get("composite")
    block = None
    if isinstance(composite, dict):
        block = composite.get("component_scores")
    if not isinstance(block, dict):
        block = report.get("component_scores")
    if not isinstance(block, dict):
        return ()

    details = report.get("components")
    details = details if isinstance(details, dict) else {}
    found: list[Component] = []
    for key, raw in block.items():
        if isinstance(raw, dict):
            score = _number(raw.get("score"))
            label = str(raw.get("label") or _label_for(key))
            weight = _number(raw.get("weight")) or 0.0
        else:
            score = _number(raw)
            label, weight = _label_for(key), 0.0
        if score is None:
            continue
        detail = details.get(key)
        signal = ""
        if isinstance(detail, dict):
            signal = str(detail.get("signal") or "")
        found.append(Component(key=str(key), label=label, score=score,
                               weight=weight, signal=signal))
    return tuple(found[:MAX_COMPONENTS])


def _warnings(report: dict) -> tuple[str, ...]:
    composite = report.get("composite")
    raw = composite.get("active_warnings") if isinstance(composite, dict) else None
    if not isinstance(raw, list):
        return ()
    out = []
    for item in raw:
        if isinstance(item, dict):
            text = str(item.get("label") or item.get("flag") or "").strip()
        else:
            text = str(item).strip()
        if text:
            out.append(text)
    return tuple(out[:6])


def _facts(report: dict) -> tuple[tuple[str, str], ...]:
    """Top-level scalars, for reports that carry a verdict but no components —
    exposure-coach's `recommendation` / `exposure_ceiling_pct` / `bias`."""
    out: list[tuple[str, str]] = []
    for key, value in report.items():
        if isinstance(value, (dict, list)) or value is None:
            continue
        if _SKIP_FACT.search(str(key)):
            continue
        if isinstance(value, bool):
            text = "yes" if value else "no"
        elif isinstance(value, float):
            text = f"{value:g}"
        else:
            text = str(value).strip()
        if not text:
            continue
        if str(key).endswith("_pct") and _number(value) is not None:
            text += "%"
        out.append((_label_for(str(key)), text[:120]))
        if len(out) >= MAX_FACTS:
            break
    return tuple(out)


def read(path: Path, *, skill_id: str = "") -> Optional[Insight]:
    """Parse one JSON report. Returns None if it is not a readable object."""
    try:
        report = json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(report, dict):
        return None

    composite = report.get("composite")
    composite = composite if isinstance(composite, dict) else {}
    score = _number(composite.get("composite_score"))
    if score is None:
        score = _number(report.get("composite_score"))
    zone = str(composite.get("zone") or report.get("zone") or "")
    guidance = str(composite.get("exposure_guidance")
                   or report.get("exposure_guidance") or "")
    quality = ""
    dq = composite.get("data_quality")
    if isinstance(dq, dict):
        quality = str(dq.get("label") or "")

    components = _components(report)
    return Insight(
        skill_id=skill_id,
        source=Path(path),
        score=score,
        zone=zone,
        guidance=guidance,
        components=components,
        warnings=_warnings(report),
        # Kept even when components exist: exposure-coach's components are only
        # the two upstream scores, and its actual verdict — the recommendation,
        # the ceiling, the confidence — lives in the top-level scalars.
        facts=_facts(report),
        quality=quality,
    )


# --------------------------------------------------------------------------- #
# Transcript fallback
# --------------------------------------------------------------------------- #
def from_transcript(text: str, *, skill_id: str = "", limit: int = 6) -> Insight:
    """When a step writes no JSON, keep its closing lines rather than nothing.

    No parsing and no inference: these are the script's own last words, which
    is the most honest summary available for a skill that reports in prose.
    """
    lines = []
    for raw in (text or "").splitlines():
        line = raw.rstrip()
        if not line.strip() or _RULE.match(line):
            continue
        if line.startswith("$ ") or line.startswith("# cwd="):
            continue
        if _FRAME.match(line.strip()):
            continue
        lines.append(line.strip())
    return Insight(skill_id=skill_id, lines=tuple(lines[-limit:]))


# --------------------------------------------------------------------------- #
# Picking the report out of a run
# --------------------------------------------------------------------------- #
def _candidates(artifacts: Sequence[Path]) -> list[Path]:
    out = []
    for path in artifacts:
        path = Path(path)
        if path.suffix.lower() != ".json":
            continue
        name = path.name.lower()
        # `*_history.json` is an append-only log of past runs and `run.json` is
        # the cockpit's own bookkeeping; neither is this run's finding.
        if "history" in name or name == "run.json":
            continue
        out.append(path)
    return sorted(out, key=lambda p: (p.stat().st_mtime if p.exists() else 0),
                  reverse=True)


def digest(result) -> Insight:
    """The best available summary of a finished run.

    Prefers this run's JSON report; falls back to the transcript's closing
    lines so a gate summary is never blank.
    """
    skill_id = getattr(result, "skill_id", "") or ""
    for path in _candidates(getattr(result, "artifacts", ()) or ()):
        found = read(path, skill_id=skill_id)
        if found is not None and not found.empty:
            return found

    # A step that failed has already been given a sentence by `diagnose`. That
    # sentence is a better summary than the tail of its transcript, which for a
    # crash is the inside of a traceback.
    verdict = getattr(result, "diagnosis", None)
    if verdict is not None and not getattr(verdict, "benign", True):
        said = tuple(x for x in (getattr(verdict, "headline", ""),
                                 getattr(verdict, "detail", "")) if x)
        if said:
            return Insight(skill_id=skill_id, lines=said)
    return from_transcript(getattr(result, "stdout", "") or "", skill_id=skill_id)
