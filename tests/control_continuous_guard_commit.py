"""Durable guard transaction and restart table over invented evidence; temporary roots only, no network or keys."""
from contextlib import contextmanager
from dataclasses import fields, replace
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch

from execution_accounts.baseline_store import CheckpointStore
from execution_control import store as control_store
from execution_control.controller import _fold
from execution_control.store import GENESIS, Journal, JournalError, Transaction
from execution_launch.baseline_head import BaselineHead, CheckpointChain
from execution_launch.continuous_guard import GuardCheckpoint, _checkpoint, plan_continuous_guard
from execution_launch.continuous_guard_commit import (
    COMPLETE, CONSISTENT, DIVERGENCE, FRESH, PENDING_CROSS_STORE, PENDING_FINALIZATION,
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
            with crash_on_append(None, order):
                receipt = commit(s, package, guard=guard, baseline=baseline)
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
            assert rows(s)[0]["utc"] == control_store._utc(package["now"])
            again = commit(s, package, now=package["now"]+timedelta(minutes=1))
            assert again.replayed and again.transaction_id == receipt.transaction_id
            assert kinds(s) == [PREPARE] + ["halt"]*halted + [COMPLETE]
            try:
                _fold(rows(s))
            except ValueError:
                pass                                                # the controller fails closed on the new kinds
            else:
                raise AssertionError("controller folded a continuous guard row")


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
        cleared = _checkpoint(**{f.name: getattr(second, f.name) for f in fields(GuardCheckpoint)
                                 if f.name != "state_sha256"} | {"permanently_halted": False})
        refused(lambda: s.gstore.commit(cleared, expected_previous_head=first.state_sha256),
                "GUARD_STORE_LATCH_ROLLBACK")


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
            expected_control_head=GENESIS).status == REFUSED


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
