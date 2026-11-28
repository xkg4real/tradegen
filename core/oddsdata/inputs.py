"""Unsigned inputs of the odds engine besides the bars (spec 4 "Calendars", "Provenance", 7.3 "Seeds"; O1, O6, O12;
R2-6; Q6, Q12, Q22, Q34, Q36).

The calendar set comes only from the owner's approved store, and only when owner.calendar_in_force names it and the
stored copy, with the files sessions() reads already loaded from it, still hashes to that name; the horizon's
sessions and dated KRX price limits are read from that set with `cal=` on every call, never from core.calendars'
default set. The session rules of its `calendars` config block (the KR Saturday-session cut-off, the close times)
come from the shipped rules store, which tree_hash records and the calendar sha does not cover (O1: the session list
is computed by unsigned code). `repo_anchor` and `tree_hash` are copies of core.quant.gate_ledger.repo_anchor and
core.ficc.macro_artifacts.tree_hash (R2-6: this package imports neither; tests/odds_inputs.py pins each copy to its
original). The comparison state lives in state_root()/odds/state.json, written atomically through checked_target; a
file that does not parse fails closed and the owner deletes it."""
from __future__ import annotations

import hashlib
import importlib.metadata
import re
from datetime import date, datetime, timedelta
from pathlib import Path

import yaml

from core.calendars import clocks, regime
from core.calendars.store import CalendarCoverageError, CalendarSet, CalendarUnsigned
from core.compliance import owner, rules
from core.odds_registry import STATE_SCHEMA, begin_run, state_path
from core.odds import plan as P

REPO = Path(__file__).resolve().parents[2]
UNVERSIONED = "UNVERSIONED"                                    # == core.quant.gate_ledger.UNVERSIONED
TREE_GLOBS = ("core/**/*.py", "data/macro/**/*", "config.py")  # == core.ficc.macro_artifacts.TREE_GLOBS
_MD5_FILES = {"KR": ("holidays_KRX", "kr_regime_tags", "kr_sessions"), "US": ("holidays_NYSE",)}


# --------------------------------------------------------------------------- #
# Calendar and sessions (Q6, Q22)
# --------------------------------------------------------------------------- #
def calendar_for(now: datetime) -> tuple[CalendarSet | None, str, str]:
    """(set, sha, error): the calendar set the owner approved and that is in force at `now`, read from the owner's
    store; (None, "", "unsigned: ...") when there is none or the stored copy no longer hashes to its approval. The
    files sessions() reads are loaded before that hash, so an edit made after it is never read."""
    sha = owner.calendar_in_force(now)
    if sha is None:
        return None, "", "unsigned: no signed calendar approval"
    folder = owner.store_dir() / "calendar" / sha
    cal = CalendarSet(folder)
    try:
        for fid in sorted({f for files in _MD5_FILES.values() for f in files}):
            cal.refusal(fid)                   # loads and caches the file, or its refusal, with the manifest
        intact = rules.calendar_sha256(folder) == sha
    except (OSError, rules.Invalid, UnicodeDecodeError, yaml.YAMLError):
        intact = False
    if not intact:
        return None, "", "unsigned: the stored calendar set does not hash to its approval"
    return cal, sha, ""


def sessions(market: str, start: date, horizon_days: int, cal: CalendarSet | None
             ) -> tuple[tuple[str, ...], tuple[float, ...], tuple[tuple[str, str], ...], str, str]:
    """(dates, KRX price limits, (file id, md5) pairs, calendar version, error) of the half-open horizon
    [start, start + horizon_days). CRYPTO: every date, no calendar. KR and US: the sessions of `cal` (KR with the
    price limit in force on each date); a missing or unsigned set gives "unsigned: ...", a horizon outside its
    coverage "coverage: ...", both with no dates."""
    if market == "CRYPTO":
        return tuple((start + timedelta(days=i)).isoformat() for i in range(horizon_days)), (), (), "", ""
    if market not in _MD5_FILES:
        raise ValueError(f"sessions: market {market!r} is not KR, US or CRYPTO")
    if cal is None:
        return (), (), (), "", "unsigned: no signed calendar set"
    try:
        found = clocks.sessions_between(market, start, start + timedelta(days=horizon_days - 1), cal=cal)
        limits = tuple(float(regime.regime_tags("KR", d, cal=cal)["price_limit"]) for d in found) \
            if market == "KR" else ()
        md5s = tuple((fid, cal.file(fid).md5) for fid in _MD5_FILES[market])
        version = cal.version
    except CalendarUnsigned as exc:
        return (), (), (), "", f"unsigned: {exc}"
    except CalendarCoverageError as exc:
        return (), (), (), "", f"coverage: {exc}"
    return tuple(d.isoformat() for d in found), limits, md5s, version, ""


# --------------------------------------------------------------------------- #
# Provenance (R2-6): copies of gate_ledger.repo_anchor and macro_artifacts.tree_hash
# --------------------------------------------------------------------------- #
def repo_anchor(root: Path = REPO) -> str:
    """`git:<sha>` of HEAD when the folder is a git repository, else UNVERSIONED (copy of gate_ledger's)."""
    head = Path(root) / ".git" / "HEAD"
    try:
        text = head.read_text(encoding="utf-8").strip()
        if text.startswith("ref:"):
            ref = text[4:].strip()
            loose = Path(root) / ".git" / ref
            if loose.is_file():
                text = loose.read_text(encoding="utf-8").strip()
            else:                                   # after `git gc` / `git pack-refs` the ref lives in packed-refs only
                packed = (Path(root) / ".git" / "packed-refs").read_text(encoding="utf-8").splitlines()
                text = next((ln.split()[0] for ln in packed if ln.endswith(" " + ref)), "")
        return f"git:{text}" if re.fullmatch(r"[0-9a-f]{40}", text) else UNVERSIONED
    except OSError:
        return UNVERSIONED


def tree_hash(root: Path = REPO) -> str:
    """sha256 over sorted relative paths + bytes of core/**/*.py, data/macro/**, config.py (macro_artifacts' copy)."""
    root = Path(root)
    files = sorted({p for g in TREE_GLOBS for p in root.glob(g) if p.is_file()},
                   key=lambda p: p.relative_to(root).as_posix())
    h = hashlib.sha256()
    for p in files:
        h.update(p.relative_to(root).as_posix().encode("utf-8") + b"\0" + p.read_bytes() + b"\0")
    return h.hexdigest()


def provenance() -> P.Provenance:
    """The repo anchor, the tree hash and the installed cryptography version ("absent" when it is not installed)."""
    try:
        crypto = importlib.metadata.version("cryptography")
    except importlib.metadata.PackageNotFoundError:
        crypto = "absent"
    return P.Provenance(repo_anchor=repo_anchor(), tree_hash=tree_hash(), cryptography=crypto)


# --------------------------------------------------------------------------- #
# The comparison state (Q12, Q34, Q36)
# --------------------------------------------------------------------------- #
def build_inputs(plan, now: datetime, *, series, sessions_info, calendar_sha: str, replay, run) -> P.Inputs:
    """plan.Inputs from the pieces: `sessions_info` is the 5-tuple of sessions(), `run` the 5-tuple of begin_run()."""
    dates, limits, md5s, version, error = sessions_info
    cid, counter, k, j, seen = run
    return P.Inputs(now=now, series=series, sessions=dates, price_limits=limits, calendar_sha256=calendar_sha,
                    calendar_version=version, calendar_md5s=md5s, calendar_error=error, replay=replay,
                    comparison_id=cid, run_counter=counter, comparison_plans=k, comparison_typed=j,
                    plan_runs=seen[P.plan_hash(plan)], provenance=provenance())
