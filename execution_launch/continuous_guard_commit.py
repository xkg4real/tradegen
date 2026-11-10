"""Durable local guard transaction and its pure restart classifier; never a live authorization.

``commit_continuous_guard`` applies a recomputed ``GuardPlan`` in the contract order of
docs/continuous-guard-commit-contract.md: verify the caller's expected guard, baseline and controller heads;
append ``continuous_guard_prepare`` at the current receipt time; persist the local ``halt`` latch; commit the
baseline and advance its separately retained head by compare-and-set; commit the guard checkpoint and advance its
head; append ``continuous_guard_complete``. A crash or refusal at any step leaves a pending transaction that
``classify_restart`` reports with new entries blocked; re-running the same package converges without duplicate
rows. The package is still unauthenticated evidence (no venue completeness authority, owner signature or source
verifier exists here), ``GuardPlan.execution_ready`` stays false, nothing is published to the controller, and the
continuous candidate source keeps its refusal. Nothing here fetches, signs, arms or orders.

Lock order, the same as ``Controller.observe``: the control journal transaction is taken first and held for the
whole commit; inside it each trusted head takes its own lock and, during compare-and-set, the checkpoint store
lock. No store or head lock is ever held while the journal lock is requested, and the journal is never entered
again (its nested transaction refusal stands). The controller's ``_fold`` does not know the two new kinds, so a
journal holding them is refused by the controller until a production adapter defines how it folds them.
"""
from __future__ import annotations

from dataclasses import dataclass, fields
from datetime import datetime
from decimal import Decimal, DecimalException, Inexact, localcontext
import json

from execution_accounts.baseline import _NUMBER, restore_state, state_json
from execution_accounts.baseline_store import CheckpointError, CheckpointStore, CommitReceipt, _require
from execution_accounts.model import canonical, content_digest
from execution_control.store import GENESIS, Journal, _utc
from execution_launch.continuous_guard import (
    _FRESH, _SHA, ContinuousGuardError, GuardCheckpoint, _hash, _instant, _need, _validate_checkpoint,
    plan_continuous_guard,
)

PREPARE, COMPLETE = "continuous_guard_prepare", "continuous_guard_complete"
FRESH, CONSISTENT, DIVERGENCE, REFUSED = "FRESH", "CONSISTENT", "DIVERGENCE", "REFUSED"
PENDING_GUARD_BEFORE_BASELINE = "PENDING_GUARD_BEFORE_BASELINE"
PENDING_CROSS_STORE = "PENDING_CROSS_STORE"
PENDING_FINALIZATION = "PENDING_FINALIZATION"
_PACKAGE_KEYS = frozenset({"baseline_before", "policy", "owner_before", "owner_after", "path", "valuation_inputs",
                           "account_capture", "coverage", "interval", "now"})
_PREPARE_DIGESTS = ("transaction_id", "input_sha256", "owner_sha256", "control_head_sha256", "path_sha256",
                    "old_guard_sha256", "new_guard_sha256", "old_baseline_sha256", "new_baseline_sha256")
_PREPARE_KEYS = frozenset(_PREPARE_DIGESTS + ("path_start", "path_end", "halt_required", "required_records"))
_DECIMALS = ("high_watermark", "applied_floor_krw", "observed_daily_loss")


# --- guard checkpoint record and store -------------------------------------------------------------------------

def _guard_bytes(state):
    try:
        _require(type(state) is GuardCheckpoint, "GUARD_STORE_CHECKPOINT_INVALID")
        body = canonical(state)
        body["baseline"] = json.loads(state_json(state.baseline))
        return json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")
    except CheckpointError:
        raise
    except (ValueError, TypeError, AttributeError, DecimalException):
        raise CheckpointError("GUARD_STORE_CHECKPOINT_INVALID") from None


def _restore_guard(raw, expected_head):
    """Verify against the separately retained guard head; never infer the latest checkpoint."""
    try:
        _require(type(expected_head) is str and _SHA.fullmatch(expected_head) is not None,
                 "GUARD_STORE_EXPECTED_HEAD_REQUIRED")

        def pairs(items):
            out = {}
            for key, value in items:
                _require(key not in out, "GUARD_STORE_CHECKPOINT_INVALID")
                out[key] = value
            return out

        def bad_number(_):
            raise CheckpointError("GUARD_STORE_CHECKPOINT_INVALID")
        body = json.loads(raw, object_pairs_hook=pairs, parse_float=bad_number, parse_constant=bad_number)
        _require(type(body) is dict and set(body) == {f.name for f in fields(GuardCheckpoint)}
                 and type(body["baseline"]) is dict and type(body["recorded_at"]) is str,
                 "GUARD_STORE_CHECKPOINT_INVALID")
        body["baseline"] = restore_state(json.dumps(body["baseline"]),
                                         expected_head=body["baseline"].get("state_digest"))
        for name in _DECIMALS:
            value = body[name]
            _require(type(value) is str and len(value) <= 128 and _NUMBER.fullmatch(value) is not None,
                     "GUARD_STORE_CHECKPOINT_INVALID")
            body[name] = Decimal(value)
        body["recorded_at"] = datetime.fromisoformat(body["recorded_at"])
        state = GuardCheckpoint(**body)
        with localcontext() as numeric:
            numeric.prec = 512; numeric.traps[Inexact] = True
            _validate_checkpoint(state)
        _require(state.state_sha256 == expected_head, "GUARD_STORE_CHECKPOINT_MISMATCH")
        return state
    except CheckpointError:
        raise
    except (ValueError, TypeError, AttributeError, KeyError, DecimalException, OverflowError, UnicodeError,
            RecursionError):
        raise CheckpointError("GUARD_STORE_CHECKPOINT_INVALID") from None


class GuardCheckpointStore(CheckpointStore):
    """The baseline store's fixed paths, locks, temporary file, fsync and replace below
    TRADEGEN_HOME/execution-guard; only the record codec and the transition rules differ."""
    _DIRECTORY = "execution-guard"

    def _restore(self, raw, expected_head):
        return _restore_guard(raw, expected_head)

    def _encode(self, state):
        raw = _guard_bytes(state)
        _restore_guard(raw, state.state_sha256)
        return raw

    def seed(self, state: GuardCheckpoint, *, expected_head: str) -> CommitReceipt:
        """Explicit first setup from a reviewed anchor checkpoint and an empty local store."""
        restored = _restore_guard(_guard_bytes(state), expected_head)
        _require(not restored.previous_guard_sha256, "GUARD_STORE_ANCHOR_REQUIRED")
        with self._locked(create=True):
            _require(not (self._root / "checkpoint.json").exists(), "GUARD_STORE_ALREADY_INITIALIZED")
            self._write(restored)
        return CommitReceipt(previous_head=None, new_head=restored.state_sha256, sequence=restored.baseline.sequence)

    def commit(self, state: GuardCheckpoint, *, expected_previous_head: str) -> CommitReceipt:
        restored = _restore_guard(_guard_bytes(state), getattr(state, "state_sha256", None))
        with self._locked():
            previous = self._load(expected_previous_head)
            _require(restored.previous_guard_sha256 == previous.state_sha256
                     and restored.baseline.previous_state_digest == previous.baseline.state_digest
                     and restored.baseline.sequence == previous.baseline.sequence+1
                     and restored.recorded_at >= previous.recorded_at, "GUARD_STORE_TRANSITION_REFUSED")
            for name in ("owner_head_sha256", "code_sha256", "policy_sha256", "anchor_sha256"):
                _require(getattr(restored, name) == getattr(previous, name), "GUARD_STORE_AUTHORITY_CHANGED")
            _require(restored.high_watermark >= previous.high_watermark
                     and restored.applied_floor_krw >= previous.applied_floor_krw
                     and (restored.permanently_halted or not previous.permanently_halted),
                     "GUARD_STORE_LATCH_ROLLBACK")
            self._write(restored)
        return CommitReceipt(previous_head=previous.state_sha256, new_head=restored.state_sha256,
                             sequence=restored.baseline.sequence)


class GuardChain:
    """The guard store as the chain behind a ``BaselineHead`` (the CheckpointChain contract). Each committed
    guard advance consumes exactly one baseline interval, so the head's sequence is the embedded baseline's."""
    def __init__(self, store: GuardCheckpointStore) -> None:
        _need(type(store) is GuardCheckpointStore, "GUARD_STORE_REQUIRED")
        self._store = store

    def seed(self, digest: str) -> int:
        state = self._store.load(expected_head=digest)
        _need(not state.previous_guard_sha256, "GUARD_SEED_REQUIRED")
        return state.baseline.sequence

    def successor(self, old: str, new: str) -> int:
        state = self._store.load(expected_head=new)
        _need(state.previous_guard_sha256 == old, "GUARD_TRANSITION_UNVERIFIED")
        return state.baseline.sequence


# --- pure restart classifier -----------------------------------------------------------------------------------

@dataclass(frozen=True, kw_only=True)
class RestartState:
    status: str
    reason: str
    transaction_id: str = ""
    new_guard_sha256: str = ""
    new_baseline_sha256: str = ""
    permanently_halted: bool = False

    @property
    def new_entries_blocked(self):
        """Pending, divergent, refused or locally halted state blocks entries; FRESH and CONSISTENT remain
        subject to the current owner, session, source and controller checks."""
        return self.status not in (FRESH, CONSISTENT) or self.permanently_halted


def classify_restart(events, *, guard_head, baseline_head, expected_guard_head: str,
                     expected_baseline_head: str, expected_control_head: str) -> RestartState:
    """The contract's restart table over journal rows and the retained heads (None when unreadable).

    Expected heads are the caller's predecessors; they are never inferred from a balance or a local file.
    """
    halted = False
    try:
        for value in (expected_guard_head, expected_baseline_head, expected_control_head):
            _hash(value)
        open_tx = last = None
        control = GENESIS
        for row in events:
            kind, data = row["kind"], row["data"]
            if open_tx is not None and kind not in ("halt", COMPLETE):
                return RestartState(status=REFUSED, reason="GUARD_RESTART_FOREIGN_ROW_IN_TRANSACTION")
            if kind == "halt":
                halted = True
            elif kind == PREPARE:
                _need(open_tx is None and type(data) is dict and set(data) == _PREPARE_KEYS
                      and type(data["halt_required"]) is bool and row["prev_sha256"] == data["control_head_sha256"]
                      and data["old_guard_sha256"] != data["new_guard_sha256"]
                      and data["old_baseline_sha256"] != data["new_baseline_sha256"], "GUARD_RESTART_JOURNAL_INVALID")
                for name in _PREPARE_DIGESTS:
                    _hash(data[name])
                open_tx = last = data
            elif kind == COMPLETE:
                _need(open_tx is not None and data == {"transaction_id": open_tx["transaction_id"]},
                      "GUARD_RESTART_JOURNAL_INVALID")
                open_tx = None
            control = row["row_sha256"]
    except (ContinuousGuardError, KeyError, TypeError, AttributeError):
        return RestartState(status=REFUSED, reason="GUARD_RESTART_JOURNAL_INVALID", permanently_halted=halted)
    expected = (expected_guard_head, expected_baseline_head)
    if open_tx is None and (last is None or expected != (last["old_guard_sha256"], last["old_baseline_sha256"])):
        if (guard_head, baseline_head) == expected and control == expected_control_head:
            return RestartState(status=FRESH, reason="", permanently_halted=halted)
        return RestartState(status=REFUSED, reason="GUARD_RESTART_HEAD_UNKNOWN", permanently_halted=halted)
    tx = open_tx or last
    if (expected != (tx["old_guard_sha256"], tx["old_baseline_sha256"])
            or tx["control_head_sha256"] != expected_control_head):
        return RestartState(status=REFUSED, reason="GUARD_RESTART_PREDECESSOR_MISMATCH", permanently_halted=halted)
    known = dict(transaction_id=tx["transaction_id"], new_guard_sha256=tx["new_guard_sha256"],
                 new_baseline_sha256=tx["new_baseline_sha256"], permanently_halted=halted)
    guard ="old" if guard_head == tx["old_guard_sha256"] else "new" if guard_head == tx["new_guard_sha256"] else None
    base = ("old" if baseline_head == tx["old_baseline_sha256"]
            else "new" if baseline_head == tx["new_baseline_sha256"] else None)
    if guard is None or base is None:
        return RestartState(status=REFUSED, reason="GUARD_RESTART_HEAD_UNKNOWN", **known)
    if open_tx is None:
        if (guard, base) != ("new", "new"):
            return RestartState(status=REFUSED, reason="GUARD_RESTART_COMPLETION_CONFLICT", **known)
        if tx["halt_required"] and not halted:
            return RestartState(status=REFUSED, reason="GUARD_RESTART_EFFECT_MISSING", **known)
        return RestartState(status=CONSISTENT, reason="", **known)
    status = {("old", "old"): PENDING_GUARD_BEFORE_BASELINE, ("old", "new"): PENDING_CROSS_STORE,
              ("new", "old"): DIVERGENCE, ("new", "new"): PENDING_FINALIZATION}[guard, base]
    return RestartState(status=status, reason="GUARD_RESTART_" + status, **known)


# --- commit coordinator ----------------------------------------------------------------------------------------

@dataclass(frozen=True, kw_only=True)
class GuardCommitReceipt:
    """All local durable state agrees: prepare, halt latch when required, both heads and the completion.
    Not a live observation, frame, authorization or arming input."""
    transaction_id: str
    guard_head: str
    baseline_head: str
    control_head: str
    permanently_halted: bool
    replayed: bool


def _read(head):
    try:
        value = head.read()
    except Exception:
        return None
    return value if type(value) is str and _SHA.fullmatch(value) is not None else None


def _previous_guard(store, old, new):
    """The predecessor checkpoint, or this transaction's committed successor after a crash; the reducer's
    exact-duplicate path then proves the successor was produced by the same package from ``old``."""
    try:
        return store.load(expected_head=old)
    except ValueError:
        pass
    try:
        _hash(new)
        state = store.load(expected_head=new)
    except ValueError:
        raise ContinuousGuardError("GUARD_CHECKPOINT_UNAVAILABLE") from None
    _need(state.previous_guard_sha256 == old, "GUARD_CHECKPOINT_UNAVAILABLE")
    return state


def _advance(store, head, old, state, new, code):
    """Store commit (skipped when this exact successor is already stored) then head compare-and-set."""
    current = _read(head)
    if current == new:
        return
    _need(current == old, code + "_HEAD_CONFLICT")
    try:
        store.load(expected_head=new)
    except ValueError:
        try:
            store.commit(state, expected_previous_head=old)
        except Exception:
            raise ContinuousGuardError(code + "_STORE_COMMIT_REFUSED") from None
    try:
        accepted = head.compare_and_set(old, new)
    except Exception:
        raise ContinuousGuardError(code + "_HEAD_UPDATE_FAILED") from None
    _need(accepted is True, code + "_HEAD_UPDATE_REFUSED")


def commit_continuous_guard(package: dict, *, now: datetime, expected_guard_head: str, expected_baseline_head: str,
                            expected_control_head: str, journal: Journal, guard_store: GuardCheckpointStore,
                            guard_head, baseline_store: CheckpointStore, baseline_head) -> GuardCommitReceipt:
    """Apply (or idempotently resume) one recomputed guard plan; refuse rather than repair or guess.

    ``package`` holds the exact ``plan_continuous_guard`` keyword inputs; the plan is recomputed here and never
    deserialized. ``now`` is the current receipt time for journal rows. A refusal after the prepare row leaves
    the transaction pending; only the same package can resume it.
    """
    _instant(now)
    for value in (expected_guard_head, expected_baseline_head, expected_control_head):
        _hash(value)
    _need(type(package) is dict and set(package) == _PACKAGE_KEYS, "GUARD_PACKAGE_REQUIRED")
    _need(type(journal) is Journal and type(guard_store) is GuardCheckpointStore
          and type(baseline_store) is CheckpointStore
          and all(callable(getattr(h, n, None))
                  for h in (guard_head, baseline_head) for n in ("read", "compare_and_set")),
          "GUARD_COMMIT_INTEGRATIONS_REQUIRED")
    with journal.transaction() as tx:                       # outermost lock, as Controller.observe takes it
        events = tx.events
        _need(not events or now >= datetime.fromisoformat(events[-1]["utc"]), "GUARD_JOURNAL_CLOCK_ROLLBACK")
        state = classify_restart(events, guard_head=_read(guard_head), baseline_head=_read(baseline_head),
                                 expected_guard_head=expected_guard_head, expected_baseline_head=expected_baseline_head,
                                 expected_control_head=expected_control_head)
        _need(state.status not in (REFUSED, DIVERGENCE), state.reason)
        previous = _previous_guard(guard_store, expected_guard_head, state.new_guard_sha256)
        plan = plan_continuous_guard(previous, **package)
        new_guard = plan.proposed_checkpoint
        new_baseline = new_guard.baseline
        _need(plan.previous_guard_sha256 == expected_guard_head
              and plan.previous_baseline_sha256 == expected_baseline_head, "GUARD_PREDECESSOR_MISMATCH")
        _need(plan.recorded_at <= now, "GUARD_COMMIT_CLOCK_ROLLBACK")
        path = package["path"]
        binding = {"input_sha256": plan.input_sha256,
                   "owner_sha256": content_digest((package["owner_before"], package["owner_after"])),
                   "control_head_sha256": expected_control_head, "path_sha256": plan.path_sha256,
                   "old_guard_sha256": expected_guard_head, "new_guard_sha256": new_guard.state_sha256,
                   "old_baseline_sha256": expected_baseline_head, "new_baseline_sha256": new_baseline.state_digest}
        transaction_id = content_digest(tuple(sorted(binding.items())))
        if state.status == FRESH:
            _need(now-plan.recorded_at <= _FRESH, "GUARD_COMMIT_EVIDENCE_STALE")
            # An existing local halt is never cleared by a guard state that does not carry it.
            _need(previous.permanently_halted or not state.permanently_halted, "GUARD_CONTROL_HALT_NOT_IN_GUARD")
            tx.append(PREPARE, binding | {
                "transaction_id": transaction_id, "path_start": _utc(path.start), "path_end": _utc(path.end),
                "halt_required": new_guard.permanently_halted,
                "required_records": [canonical(record) for record in plan.required_records]}, now=now)
        else:
            _need(state.transaction_id == transaction_id, "GUARD_PENDING_TRANSACTION_MISMATCH")
        if state.status != CONSISTENT:
            if new_guard.permanently_halted and not any(row["kind"] == "halt" for row in tx.events):
                floor = next((record.floor_krw for record in plan.required_records
                              if record.kind == "permanent_floor_halt"), new_guard.applied_floor_krw)
                tx.append("halt", {"floor": str(floor)}, now=now)
            _advance(baseline_store, baseline_head, expected_baseline_head, new_baseline, new_baseline.state_digest,
                     "GUARD_BASELINE")
            _advance(guard_store, guard_head, expected_guard_head, new_guard, new_guard.state_sha256,
                     "GUARD_CHECKPOINT")
            tx.append(COMPLETE, {"transaction_id": transaction_id}, now=now)
        _need(_read(baseline_head) == new_baseline.state_digest and _read(guard_head) == new_guard.state_sha256,
              "GUARD_COMMIT_HEADS_DISAGREE")
        rows = tx.events
        return GuardCommitReceipt(transaction_id=transaction_id, guard_head=new_guard.state_sha256,
                                  baseline_head=new_baseline.state_digest, control_head=rows[-1]["row_sha256"],
                                  permanently_halted=any(row["kind"] == "halt" for row in rows),
                                  replayed=state.status != FRESH)
