"""Resolve which script inside a skill directory NEXTGEN should actually run.

The trading-skills repository has no declared entrypoint field, so this module
derives one. Three tiers, most specific first:

  1. `_PRIMARY` — a curated choice for the 15 skills that ship several CLIs and
     where picking alphabetically would run the wrong thing (e.g. running
     `finviz_stock_client.py` instead of `screen_canslim.py`).
  2. `scripts/<skill_id with dashes as underscores>.py` — the convention the
     repository follows for 9 skills.
  3. The single remaining script that looks like a CLI.

A script "looks like a CLI" when it has a `__main__` guard and reads arguments.
Six skills have no such script at all; they are instruction-only and surface in
the UI as documentation rather than as something with a Run button.

Every candidate is returned, not just the winner — the detail view lists the
secondary scripts so a skill's other entry points stay reachable.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Optional

# Curated primary script for skills that expose more than one CLI.
_PRIMARY: dict[str, str] = {
    "breadth-chart-analyst": "fetch_breadth_csv.py",
    "canslim-screener": "screen_canslim.py",
    "downtrend-duration-analyzer": "analyze_downtrends.py",
    "earnings-calendar": "fetch_earnings_fmp.py",
    "edge-candidate-agent": "auto_detect_candidates.py",
    "institutional-flow-tracker": "track_institutional_flow.py",
    "kanchi-dividend-sop": "build_sop_plan.py",
    "mt5-robot-tester": "mt5_batch_tester.py",
    "pair-trade-screener": "find_pairs.py",
    "parabolic-short-trade-planner": "screen_parabolic.py",
    "signal-postmortem": "postmortem_analyzer.py",
    "skill-idea-miner": "mine_session_logs.py",
    "strategy-pivot-designer": "detect_stagnation.py",
    "trader-memory-core": "trader_memory_cli.py",
    "trading-skills-navigator": "recommend.py",
}

_MAIN_GUARD = re.compile(r"""__name__\s*==\s*['"]__main__['"]""")


@dataclass(frozen=True)
class Entrypoint:
    skill_id: str
    path: Path
    primary: bool = False

    @property
    def name(self) -> str:
        return self.path.name

    @property
    def label(self) -> str:
        return self.path.stem.replace("_", " ")


def _is_cli(path: Path) -> bool:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return False
    if not _MAIN_GUARD.search(text):
        return False
    return ("argparse" in text) or ("sys.argv" in text)


@lru_cache(maxsize=256)
def _candidates(scripts_dir_str: str) -> tuple[str, ...]:
    scripts = Path(scripts_dir_str)
    if not scripts.is_dir():
        return ()
    found = []
    for path in sorted(scripts.glob("*.py")):
        if path.name.startswith("_") or path.name.startswith("test_"):
            continue
        if _is_cli(path):
            found.append(path.name)
    return tuple(found)


def entrypoints(skill_id: str, skill_dir: Path) -> tuple[Entrypoint, ...]:
    """All runnable scripts for a skill, primary first. Empty when doc-only."""
    scripts = skill_dir / "scripts"
    names = _candidates(str(scripts))
    if not names:
        return ()

    preferred: Optional[str] = None
    if skill_id in _PRIMARY and _PRIMARY[skill_id] in names:
        preferred = _PRIMARY[skill_id]
    else:
        conventional = f"{skill_id.replace('-', '_')}.py"
        if conventional in names:
            preferred = conventional
        elif len(names) == 1:
            preferred = names[0]

    ordered = ([preferred] if preferred else []) + [n for n in names if n != preferred]
    return tuple(
        Entrypoint(skill_id=skill_id, path=scripts / n, primary=(n == preferred))
        for n in ordered
    )


def primary(skill_id: str, skill_dir: Path) -> Optional[Entrypoint]:
    for ep in entrypoints(skill_id, skill_dir):
        if ep.primary:
            return ep
    return None


def is_runnable(skill_id: str, skill_dir: Path) -> bool:
    return primary(skill_id, skill_dir) is not None


def reload() -> None:
    _candidates.cache_clear()
