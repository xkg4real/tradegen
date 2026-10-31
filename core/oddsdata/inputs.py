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
import json
import math
import os
import re
from datetime import date, datetime, timedelta
from pathlib import Path

import yaml

from core.calendars import clocks, regime
from core.calendars.store import CalendarCoverageError, CalendarSet, CalendarUnsigned
from core.compliance import model, owner, rules
from core.isolation import checked_target, state_root
from core.odds import plan as P

REPO = Path(__file__).resolve().parents[2]
UNVERSIONED = "UNVERSIONED"                                    # == core.quant.gate_ledger.UNVERSIONED
TREE_GLOBS = ("core/**/*.py", "data/macro/**/*", "config.py")  # == core.ficc.macro_artifacts.TREE_GLOBS
STATE_SCHEMA = "tradegen.odds_state/1"
CID_RE = r"c[0-9]{6}"
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
def state_path() -> Path:
    return state_root() / "odds" / "state.json"


def _number(v) -> bool:
    try:
        return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)
    except OverflowError:
        return False


def _hex64(v) -> bool:
    return isinstance(v, str) and re.fullmatch(r"[0-9a-f]{64}", v) is not None


def _state_ok(doc) -> bool:
    """A tradegen.odds_state/1 document: every comparison holds its own run counter (1 <= run <= runs, its id
    c<run:06d>, so ids and runs are unique and a new id is never an issued one), sorted unique plan hashes and sorted
    unique typed rates."""
    if not (isinstance(doc, dict) and set(doc) == {"schema", "runs", "comparisons"} and doc["schema"] == STATE_SCHEMA
            and isinstance(doc["runs"], int) and not isinstance(doc["runs"], bool) and doc["runs"] >= 0
            and isinstance(doc["comparisons"], dict)):
        return False
    for cid, comp in doc["comparisons"].items():
        if not (re.fullmatch(CID_RE, cid) and isinstance(comp, dict) and set(comp) == {"run", "plans", "typed"}
                and isinstance(comp["run"], int) and not isinstance(comp["run"], bool)
                and 1 <= comp["run"] <= doc["runs"] and cid == f"c{comp['run']:06d}"
                and isinstance(comp["plans"], list)
                and all(_hex64(h) for h in comp["plans"]) and comp["plans"] == sorted(set(comp["plans"]))
                and isinstance(comp["typed"], list) and all(_number(p) for p in comp["typed"])
                and comp["typed"] == sorted(set(comp["typed"]))):
            return False
    return True


def _read_state(path: Path) -> dict:
    if not path.exists():
        return {"schema": STATE_SCHEMA, "runs": 0, "comparisons": {}}
    try:
        doc = json.loads(path.read_bytes().decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        doc = None
    if not _state_ok(doc):
        raise RuntimeError(f"odds state {path}: not a {STATE_SCHEMA} file; the owner deletes it before the next run")
    return doc


def begin_run(comparison: str | None, plan_hashes: list[str], typed: list[float]
              ) -> tuple[str, int, int, int, dict[str, int]]:
    """Opens one run: a new comparison (comparison None, id c<runs:06d>, its run counter fixed at creation) or an
    issued one (its own counter reused, so every invocation of it gets the same seed). Adds the plan hashes and typed
    win rates, writes the state atomically, and returns (id, run counter, K plans, J typed rates, R per plan hash:
    the number of comparisons whose plans hold it). ValueError, writing nothing, for an id that is malformed or was
    never issued, or a plan hash or rate that is not one."""
    # ponytail: one writer at a time. Two overlapping runs read the same `runs`, issue the same new id and counter
    # (one seed), and the later os.replace drops the other's plans; take an exclusive state.lock (open "x" after
    # checked_target) if runs can ever overlap. Ids stop at c999999: run 1,000,000 writes c1000000, which the next
    # read refuses; widen CID_RE before that.
    if comparison is not None and not (isinstance(comparison, str) and re.fullmatch(CID_RE, comparison)):
        raise ValueError(f"comparison id {comparison!r} is not c followed by six digits")
    if not all(_hex64(h) for h in plan_hashes) or not all(_number(p) for p in typed):
        raise ValueError("begin_run: plan hashes are 64 hex characters and typed rates finite numbers")
    path = state_path()
    state = _read_state(path)
    comps = state["comparisons"]
    if comparison is not None and comparison not in comps:
        raise ValueError(f"comparison {comparison} was never issued; leave --comparison out to start a new one")
    state["runs"] += 1
    cid = comparison or f"c{state['runs']:06d}"
    comp = comps.setdefault(cid, {"run": state["runs"], "plans": [], "typed": []})
    comp["plans"] = sorted(set(comp["plans"]) | set(plan_hashes))
    comp["typed"] = sorted(set(comp["typed"]) | {float(p) for p in typed})
    base = path.parent
    checked_target(base, "odds folder", within=state_root())     # a junction made after state_root()'s scan (A0)
    target = checked_target(path, "odds state", within=base)
    tmp = checked_target(base / "state.json.tmp", "odds state tmp", within=base)
    base.mkdir(parents=True, exist_ok=True)
    tmp.write_bytes((model.canonical_json(state) + "\n").encode("utf-8"))
    os.replace(tmp, target)
    seen = {h: sum(h in c["plans"] for c in comps.values()) for h in plan_hashes}
    return cid, comp["run"], len(comp["plans"]), len(comp["typed"]), seen


def build_inputs(plan, now: datetime, *, series, sessions_info, calendar_sha: str, replay, run) -> P.Inputs:
    """plan.Inputs from the pieces: `sessions_info` is the 5-tuple of sessions(), `run` the 5-tuple of begin_run()."""
    dates, limits, md5s, version, error = sessions_info
    cid, counter, k, j, seen = run
    return P.Inputs(now=now, series=series, sessions=dates, price_limits=limits, calendar_sha256=calendar_sha,
                    calendar_version=version, calendar_md5s=md5s, calendar_error=error, replay=replay,
                    comparison_id=cid, run_counter=counter, comparison_plans=k, comparison_typed=j,
                    plan_runs=seen[P.plan_hash(plan)], provenance=provenance())
