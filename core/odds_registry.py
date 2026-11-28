"""Shared comparison history for the odds CLI and the owner planner (Q12/Q34/Q36).

The CLI and owner console must issue from the same locked sequence and retain
the same plan-run counts across processes. This module consumes no market data.
"""
from __future__ import annotations

import json
import math
import os
from pathlib import Path
import re

from core.compliance import model
from core.isolation import checked_target, state_root

STATE_SCHEMA = "tradegen.odds_state/1"
CID_RE = r"c[0-9]{6}"


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
    if comparison is not None and not (isinstance(comparison, str) and re.fullmatch(CID_RE, comparison)):
        raise ValueError(f"comparison id {comparison!r} is not c followed by six digits")
    if not all(_hex64(h) for h in plan_hashes) or not all(_number(p) for p in typed):
        raise ValueError("begin_run: plan hashes are 64 hex characters and typed rates finite numbers")
    path = state_path()
    base = checked_target(path.parent, "odds folder", within=state_root())
    if comparison is not None and not base.exists():
        raise ValueError("unknown comparison")
    base.mkdir(parents=True, exist_ok=True)
    lock = checked_target(base.parent / "odds-registry.lock", "odds registry lock", within=base.parent)
    with lock.open("a+b") as handle:
        _lock_registry(handle)
        return _register_locked(path, comparison, plan_hashes, typed)


def _lock_registry(handle):
    # Closing this handle releases the lock, including after process failure.
    handle.seek(0)
    if os.name == "nt":
        import msvcrt
        msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
    else:
        import fcntl
        fcntl.flock(handle, fcntl.LOCK_EX)


def _register_locked(path, comparison, plan_hashes, typed):
    base = path.parent
    checked_target(path, "odds state", within=base)
    state = _read_state(path)
    if state["runs"] >= 999999:
        raise ValueError("odds comparison counter exhausted")
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
    with tmp.open("wb") as out:
        out.write((model.canonical_json(state) + "\n").encode("utf-8"))
        out.flush()
        os.fsync(out.fileno())
    os.replace(tmp, target)
    seen = {h: sum(h in c["plans"] for c in comps.values()) for h in plan_hashes}
    return cid, comp["run"], len(comp["plans"]), len(comp["typed"]), seen
