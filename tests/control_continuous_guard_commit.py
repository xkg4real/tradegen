"""Durable guard transaction and restart table over invented evidence; temporary roots only, no network or keys."""
from contextlib import contextmanager
from dataclasses import fields, replace
from datetime import timedelta
from decimal import Decimal
import json
from types import SimpleNamespace
from unittest.mock import patch

from execution_accounts.baseline_store import CheckpointStore
from execution_accounts.model import canonical
from execution_control import store as control_store
from execution_control.controller import _fold
from execution_control.store import GENESIS, Journal, JournalError, Transaction, guard_pending
from execution_launch.baseline_head import BaselineHead, CheckpointChain
from execution_launch.continuous_guard import _FRESH, GuardCheckpoint, _checkpoint, plan_continuous_guard
from execution_launch.continuous_guard_commit import (
    _PREPARE_KEYS, COMPLETE, CONSISTENT, DIVERGENCE, FRESH, PENDING_CROSS_STORE, PENDING_FINALIZATION,
    PENDING_GUARD_BEFORE_BASELINE, PREPARE, REFUSED, GuardChain, GuardCheckpointStore, classify_restart,
    commit_continuous_guard,
)
from tests import compliance_fixtures as F
from tests.control_continuous_guard import START, build, refused, seed
from tests.launch_baseline_head import head_root


class Crash(Exception):
    """A simulated process death at one step."""


class Head:
    """A real retained head behind the coordinator's read/compare_and_set seam, with an optional fault.
    `held` records whether the control journal transaction was active at each call (lock order)."""
    def __init__(self, real, *, log=None, name="", crash=False, refuse=False, value=None):
        self.real, self.log, self.name, self.crash, self.refuse, self.value = real, log, name, crash, refuse, value
        self.held = []

    def read(self):
        self.held.append(getattr(control_store._THREAD, "active", False))
        return self.value if self.value is not None else self.real.read()

    def compare_and_set(self, old, new):
        self.held.append(getattr(control_store._THREAD, "active", False))
        if self.log is not None:
            self.log.append(self.name)
        if self.crash:
            raise Crash()
        return False if self.refuse else self.real.compare_and_set(old, new)


@contextmanager
def stack(**seed_args):
    with F.temp_home() as home, head_root() as hroot:
        state, pol, context = seed(**seed_args)
        bstore, gstore = CheckpointStore(root=home), GuardCheckpointStore(root=home)
        bhead = BaselineHead(root=hroot, name="baseline-head", chain=CheckpointChain(bstore))
        ghead = BaselineHead(root=hroot, name="continuous-guard", chain=GuardChain(gstore))
        bstore.seed(state.baseline, expected_head=state.baseline.state_digest)
        bhead.initialize_reviewed_head(state.baseline.state_digest)
        gstore.seed(state, expected_head=state.state_sha256)
        ghead.initialize_reviewed_head(state.state_sha256)
        # Store, head and journal objects cache nothing, so reusing them is a process restart over the same roots.
        yield SimpleNamespace(state=state, policy=pol, context=context, journal=Journal(),
                              bstore=bstore, gstore=gstore, bhead=bhead, ghead=ghead)


def commit(s, package, *, guard=None, baseline=None, now=None, control=GENESIS):
    return commit_continuous_guard(package, now=now or package["now"], expected_guard_head=s.state.state_sha256,
        expected_baseline_head=s.state.baseline.state_digest, expected_control_head=control, journal=s.journal,
        guard_store=s.gstore, guard_head=guard or s.ghead, baseline_store=s.bstore, baseline_head=baseline or s.bhead)


def rows(s):
    with s.journal.transaction() as tx:
        return tx.events


def kinds(s):
    return [row["kind"] for row in rows(s)]


def classify(s, *, guard_head=None, control=GENESIS):
    return classify_restart(rows(s), guard_head=guard_head or s.ghead.read(), baseline_head=s.bhead.read(),
        expected_guard_head=s.state.state_sha256, expected_baseline_head=s.state.baseline.state_digest,
        expected_control_head=control)


@contextmanager
def crash_on_append(kind, log=None):
    original = Transaction.append

    def append(self, row_kind, data, *, now):
        if log is not None:
            log.append(row_kind)
        if row_kind == kind:
            raise Crash()
        return original(self, row_kind, data, now=now)
    with patch.object(Transaction, "append", append):
        yield


def test_happy_path_orders_prepare_halt_baseline_guard_then_completion():
    for prices, halted in ((("110", "105", "115"), True), (("101",), False)):
        with stack() as s:
            assert classify(s).status == FRESH and not classify(s).new_entries_blocked
            package = build(s.state, s.policy, s.context, prices)
            order = []
            guard, baseline = Head(s.ghead, log=order, name="guard_cas"), Head(s.bhead, log=order, name="baseline_cas")
            received = package["now"]+timedelta(seconds=10)         # receipt time, later than the evidence time
            with crash_on_append(None, order):
                receipt = commit(s, package, guard=guard, baseline=baseline, now=received)
            assert order == [PREPARE] + ["halt"]*halted + ["baseline_cas", "guard_cas", COMPLETE], order
            assert all(guard.held + baseline.held)                  # journal lock outermost at every head call
            assert receipt.guard_head == s.ghead.read() and receipt.baseline_head == s.bhead.read()
            assert receipt.permanently_halted is halted and not receipt.replayed
            assert s.gstore.load(expected_head=receipt.guard_head).permanently_halted is halted
            state = classify(s)
            assert state.status == CONSISTENT and state.new_entries_blocked is halted
            assert state.transaction_id == receipt.transaction_id
            prepare = rows(s)[0]["data"]
            assert prepare["halt_required"] is halted and prepare["control_head_sha256"] == GENESIS
            assert rows(s)[0]["utc"] == control_store._utc(received) != control_store._utc(package["now"])
            plan = plan_continuous_guard(s.state, **package)
            assert prepare["required_records"] == [canonical(record) for record in plan.required_records]
            assert any(r["kind"] == "permanent_floor_halt" for r in prepare["required_records"]) is halted
            again = commit(s, package, now=package["now"]+timedelta(minutes=1))
            assert again.replayed and again.transaction_id == receipt.transaction_id
            assert kinds(s) == [PREPARE] + ["halt"]*halted + [COMPLETE]
            _fold(rows(s))                                          # the controller folds guard rows as inert
            assert not guard_pending(rows(s)) and guard_pending(rows(s)[:1])


def test_crash_after_each_step_is_classified_then_completed_by_idempotent_replay():
    cases = (("prepare", PENDING_GUARD_BEFORE_BASELINE, [PREPARE]),
             ("halt", PENDING_GUARD_BEFORE_BASELINE, [PREPARE, "halt"]),
             ("baseline", PENDING_CROSS_STORE, [PREPARE, "halt"]),
             ("guard", PENDING_FINALIZATION, [PREPARE, "halt"]))
    for step, status, written in cases:
        with stack() as s:
            package = build(s.state, s.policy, s.context)
            try:
                if step == "prepare":
                    with crash_on_append("halt"):
                        commit(s, package)
                elif step == "halt":       # baseline store already replaced, its head not yet advanced
                    commit(s, package, baseline=Head(s.bhead, crash=True))
                elif step == "baseline":   # guard store already replaced, its head not yet advanced
                    commit(s, package, guard=Head(s.ghead, crash=True))
                else:
                    with crash_on_append(COMPLETE):
                        commit(s, package)
            except (Crash, ValueError):
                pass
            else:
                raise AssertionError(step)
            state = classify(s)
            assert state.status == status and state.new_entries_blocked, (step, state)
            assert kinds(s) == written, (step, kinds(s))
            receipt = commit(s, package, now=package["now"]+timedelta(minutes=5))
            assert receipt.replayed and receipt.permanently_halted, step
            assert kinds(s) == [PREPARE, "halt", COMPLETE], (step, kinds(s))
            assert classify(s).status == CONSISTENT
            commit(s, package, now=package["now"]+timedelta(minutes=6))
            assert kinds(s) == [PREPARE, "halt", COMPLETE], step


def test_guard_advanced_with_baseline_old_is_divergence_and_refused():
    with stack() as s:
        package = build(s.state, s.policy, s.context)
        refused(lambda: commit(s, package, baseline=Head(s.bhead, crash=True)), "GUARD_BASELINE_HEAD_UPDATE_FAILED")
        new = plan_continuous_guard(s.state, **package).proposed_checkpoint
        s.gstore.commit(new, expected_previous_head=s.state.state_sha256)
        assert s.ghead.compare_and_set(s.state.state_sha256, new.state_sha256)
        state = classify(s)
        assert state.status == DIVERGENCE and state.new_entries_blocked
        refused(lambda: commit(s, package), "GUARD_RESTART_DIVERGENCE")
        assert kinds(s) == [PREPARE, "halt"]


def test_baseline_cas_refusal_leaves_pending_and_publishes_nothing():
    with stack() as s:
        package = build(s.state, s.policy, s.context)
        refused(lambda: commit(s, package, baseline=Head(s.bhead, refuse=True)), "GUARD_BASELINE_HEAD_UPDATE_REFUSED")
        assert kinds(s) == [PREPARE, "halt"]
        assert s.bhead.read() == s.state.baseline.state_digest and s.ghead.read() == s.state.state_sha256
        assert classify(s).status == PENDING_GUARD_BEFORE_BASELINE and classify(s).new_entries_blocked
        assert commit(s, package).replayed and classify(s).status == CONSISTENT


def test_existing_halt_is_preserved_never_duplicated_and_never_cleared():
    with stack() as s:                                            # local halt the guard checkpoint does not carry
        with s.journal.transaction() as tx:
            tx.append("halt", {"floor": "100"}, now=START)
        control = rows(s)[-1]["row_sha256"]
        state = classify(s, control=control)
        assert state.status == FRESH and state.permanently_halted and state.new_entries_blocked
        refused(lambda: commit(s, build(s.state, s.policy, s.context, ("101",)), control=control),
                "GUARD_CONTROL_HALT_NOT_IN_GUARD")
        assert kinds(s) == ["halt"]
    with stack(equity="100", high="110", floor="110", halted=True) as s:
        with s.journal.transaction() as tx:
            tx.append("halt", {"floor": "110"}, now=START)
        control = rows(s)[-1]["row_sha256"]
        package = build(s.state, s.policy, s.context, ("101",))
        receipt = commit(s, package, control=control)
        assert receipt.permanently_halted and kinds(s) == ["halt", PREPARE, COMPLETE]
        assert classify(s, control=control).status == CONSISTENT and classify(s, control=control).new_entries_blocked
        first = s.gstore.load(expected_head=receipt.guard_head)
        follow = build(first, s.policy, replace(s.context, observed_at=first.baseline.asof), ("116",))
        second = plan_continuous_guard(first, **follow).proposed_checkpoint
        def variant(base, **changes):
            return _checkpoint(**{f.name: getattr(base, f.name) for f in fields(GuardCheckpoint)
                                  if f.name != "state_sha256"} | changes)
        for changes, code in (({"permanently_halted": False}, "GUARD_STORE_LATCH_ROLLBACK"),
                              ({"owner_head_sha256": "a"*64}, "GUARD_STORE_AUTHORITY_CHANGED"),
                              ({"previous_guard_sha256": "b"*64}, "GUARD_STORE_TRANSITION_REFUSED")):
            refused(lambda: s.gstore.commit(variant(second, **changes), expected_previous_head=first.state_sha256),
                    code)
        s.gstore.commit(second, expected_previous_head=first.state_sha256)      # the floor ratchets to the new peak
        third = plan_continuous_guard(second, **build(second, s.policy,
            replace(s.context, observed_at=second.baseline.asof), ("117",))).proposed_checkpoint
        lowered = variant(third, applied_floor_krw=second.applied_floor_krw-3)  # valid record, below the ratchet
        assert third.baseline.approved_effective_floor <= lowered.applied_floor_krw < second.applied_floor_krw
        refused(lambda: s.gstore.commit(lowered, expected_previous_head=second.state_sha256),
                "GUARD_STORE_LATCH_ROLLBACK")
        assert s.gstore.commit(third, expected_previous_head=second.state_sha256).new_head == third.state_sha256


def test_a_store_rolled_back_under_an_advanced_head_never_yields_a_receipt():
    for name, code in (("gstore", "GUARD_CHECKPOINT"), ("bstore", "GUARD_BASELINE")):
        for pending in (True, False):
            with stack() as s:
                package = build(s.state, s.policy, s.context)
                path = getattr(s, name)._root / "checkpoint.json"
                old = path.read_bytes()
                if pending:                                           # both heads advanced, completion missing
                    try:
                        with crash_on_append(COMPLETE):
                            commit(s, package)
                    except Crash:
                        pass
                else:
                    commit(s, package)
                written = kinds(s)
                path.write_bytes(old)
                refused(lambda: commit(s, package, now=package["now"]+timedelta(minutes=1)), code + "_STORE_MISMATCH")
                assert kinds(s) == written, (name, pending)


def test_stale_evidence_and_clock_rollback_refuse_before_any_write():
    with stack() as s:
        package = build(s.state, s.policy, s.context)
        refused(lambda: commit(s, package, now=package["now"]+_FRESH+timedelta(microseconds=1)),
                "GUARD_COMMIT_EVIDENCE_STALE")
        refused(lambda: commit(s, package, now=package["now"]-timedelta(microseconds=1)),
                "GUARD_COMMIT_CLOCK_ROLLBACK")
        assert kinds(s) == []
        with s.journal.transaction() as tx:
            tx.append("kill", {"session_id": "other", "reason": "owner_requested"},
                      now=package["now"]+timedelta(seconds=5))
        refused(lambda: commit(s, package, control=rows(s)[-1]["row_sha256"]), "GUARD_JOURNAL_CLOCK_ROLLBACK")
        assert kinds(s) == ["kill"] and s.ghead.read() == s.state.state_sha256


def test_classifier_refuses_missing_halts_conflicts_lone_completions_and_unchained_heads():
    with stack() as s:
        receipt = commit(s, build(s.state, s.policy, s.context))
        old, new = (s.state.state_sha256, s.state.baseline.state_digest), (receipt.guard_head, receipt.baseline_head)
        done, head = rows(s), rows(s)[-1]["row_sha256"]

        def at(events, heads, expected=old, control=GENESIS):
            return classify_restart(events, guard_head=heads[0], baseline_head=heads[1],
                expected_guard_head=expected[0], expected_baseline_head=expected[1], expected_control_head=control)
        cases = [(at([r for r in done if r["kind"] != "halt"], new), "GUARD_RESTART_EFFECT_MISSING"),
                 (at(done[-1:], old, control=head), "GUARD_RESTART_JOURNAL_INVALID"),
                 (at(done, new, expected=(new[0], "e"*64), control=head), "GUARD_RESTART_HEAD_UNKNOWN"),
                 (at(done, (new[0], "e"*64), expected=(new[0], "e"*64), control=head), "GUARD_RESTART_HEAD_UNKNOWN")]
        cases += [(at(done, heads), "GUARD_RESTART_COMPLETION_CONFLICT")
                  for heads in ((old[0], new[1]), (new[0], old[1]), old)]
        for state, reason in cases:
            assert (state.status, state.reason) == (REFUSED, reason) and state.new_entries_blocked, (state, reason)
        assert at(done, new, expected=new, control=head).status == FRESH       # the next transaction chains on


def test_guard_store_refuses_edited_and_duplicate_key_records():
    with stack() as s:
        path = s.gstore._root / "checkpoint.json"
        raw = path.read_bytes()
        body = json.loads(raw)
        edited = json.dumps(body | {"applied_floor_krw": "50"}, sort_keys=True, separators=(",", ":")).encode()
        duplicate = raw[:-1] + b',"anchor_sha256":' + json.dumps(body["anchor_sha256"]).encode() + b"}"
        for bad in (edited, duplicate):
            path.write_bytes(bad)
            refused(lambda: s.gstore.load(expected_head=s.state.state_sha256), "GUARD_STORE_CHECKPOINT_INVALID")
        path.write_bytes(raw)
        assert s.gstore.load(expected_head=s.state.state_sha256).state_sha256 == s.state.state_sha256


def test_controller_folds_guard_rows_and_a_pending_prepare_blocks_only_new_entries():
    from execution_control.session import prepare_session
    from tests.control_controller import reserve, send, snapshot
    from tests.control_session import _preparation_args, signed_control
    prepare = {key: "a"*64 for key in _PREPARE_KEYS} | {"path_start": "x", "path_end": "x", "halt_required": False,
                                                        "required_records": []}

    def append(env, kind, data):
        with env.journal.transaction() as tx:
            tx.append(kind, data, now=env.now)

    def last_kind(env):
        with env.journal.transaction() as tx:
            return tx.events[-1]["kind"], guard_pending(tx.events)
    with signed_control() as env:
        append(env, PREPARE, prepare)
        refused(lambda: reserve(env), "local no-entry latch active")
        append(env, COMPLETE, {"transaction_id": "a"*64})
        assert reserve(env).status == "RESERVED"                       # reserved before the next prepare
        append(env, PREPARE, prepare)
        refused(lambda: send(env), "local no-entry latch active")       # an earlier buy is not sent while pending
        assert not env.adapter.requests and env.controller.states()[0].status == "RESERVED"
        append(env, COMPLETE, {"transaction_id": "a"*64})
        assert send(env).status == "ACKNOWLEDGED"
    with signed_control() as env:                                       # exits and latches while pending
        append(env, PREPARE, prepare)
        env.controller.observe(now=env.now)
        snapshot(env, positions=replace(env.observation.positions, holdings={("upbit", "BTC"): 0.001}),
                 holdings={("upbit", "fixture-account", "spot", "KRW-BTC"): Decimal("0.001")})
        sell = replace(env.order, side="sell", client_id="reducing-exit")
        assert reserve(env, sell).status == "RESERVED"
        assert env.controller.dispatch(sell.client_id, now=env.now).status == "ACKNOWLEDGED"
        env.controller.kill(env.session_id, reason="owner_requested", now=env.now)
        assert last_kind(env) == ("kill", True)
        env.controller.halt(floor=Decimal("100"), now=env.now)
        assert last_kind(env) == ("halt", True)
    with signed_control(prepare=False, arm=False) as env:
        append(env, PREPARE, prepare)
        refused(lambda: prepare_session(**_preparation_args(env)), "SESSION_PREPARATION_GUARD_PENDING")
        with env.journal.transaction() as tx:
            assert [row["kind"] for row in tx.events] == [PREPARE]


def test_a_halt_written_into_a_pending_non_halting_transaction_blocks_its_completion():
    with stack() as s:
        package = build(s.state, s.policy, s.context, ("101",))         # this guard does not halt
        refused(lambda: commit(s, package, baseline=Head(s.bhead, crash=True)), "GUARD_BASELINE_HEAD_UPDATE_FAILED")
        with s.journal.transaction() as tx:                              # the row Controller.halt writes
            tx.append("halt", {"floor": "100"}, now=package["now"])
        state = classify(s)
        assert (state.status, state.reason) == (REFUSED, "GUARD_RESTART_FOREIGN_ROW_IN_TRANSACTION")
        assert state.new_entries_blocked and state.permanently_halted
        refused(lambda: commit(s, package, now=package["now"]+timedelta(minutes=1)),
                "GUARD_RESTART_FOREIGN_ROW_IN_TRANSACTION")
        assert kinds(s) == [PREPARE, "halt"]
        assert s.ghead.read() == s.state.state_sha256 and s.bhead.read() == s.state.baseline.state_digest


def test_different_package_under_pending_prepare_refuses():
    with stack() as s:
        package = build(s.state, s.policy, s.context)
        refused(lambda: commit(s, package, baseline=Head(s.bhead, crash=True)), "GUARD_BASELINE_HEAD_UPDATE_FAILED")
        other = build(s.state, s.policy, s.context, ("101",))
        refused(lambda: commit(s, other, now=package["now"]), "GUARD_PENDING_TRANSACTION_MISMATCH")
        assert kinds(s) == [PREPARE, "halt"] and classify(s).status == PENDING_GUARD_BEFORE_BASELINE


def test_unknown_unreadable_or_mismatched_heads_refuse_before_any_write():
    with stack() as s:
        package = build(s.state, s.policy, s.context)

        class Broken:
            def read(self):
                raise OSError("unavailable")

            def compare_and_set(self, old, new):
                raise AssertionError("must not advance")
        for guard in (Head(s.ghead, value="f"*64), Broken()):
            refused(lambda: commit(s, package, guard=guard), "GUARD_RESTART_HEAD_UNKNOWN")
        refused(lambda: commit(s, package, control="f"*64), "GUARD_RESTART_HEAD_UNKNOWN")
        assert kinds(s) == []
        receipt = commit(s, package)
        assert classify(s, guard_head="f"*64).status == REFUSED
        unrelated = classify_restart(rows(s), guard_head=receipt.guard_head, baseline_head=receipt.baseline_head,
            expected_guard_head="e"*64, expected_baseline_head="e"*64, expected_control_head=GENESIS)
        assert unrelated.status == REFUSED and unrelated.new_entries_blocked
        orphan = [row for row in rows(s) if row["kind"] != PREPARE]
        assert classify_restart(orphan, guard_head=receipt.guard_head, baseline_head=receipt.baseline_head,
            expected_guard_head=s.state.state_sha256, expected_baseline_head=s.state.baseline.state_digest,
            expected_control_head=GENESIS).reason == "GUARD_RESTART_JOURNAL_INVALID"


def test_commit_never_reenters_the_control_journal():
    with stack() as s:
        package = build(s.state, s.policy, s.context)
        with s.journal.transaction():
            try:
                commit(s, package)
            except JournalError:
                pass
            else:
                raise AssertionError("nested journal transaction accepted")
        assert kinds(s) == [] and s.ghead.read() == s.state.state_sha256


if __name__ == "__main__":
    from tests.control_acceptance import _main
    raise SystemExit(_main(["control_continuous_guard_commit"]))
