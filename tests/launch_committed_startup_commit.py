"""Retained evaluation-time binding over actual temporary guard commits.

Only the path/account/coverage inputs are synthetic, as in the existing guard
fixture. Plans, checkpoint stores, independent heads, Journal and commit/replay
are real; no source authenticity or current owner authority is asserted here.
"""
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import json
from unittest.mock import patch

from execution_control.store import GENESIS, Journal
from execution_launch import continuous_guard_commit as C
from execution_launch.continuous_guard import ContinuousGuardError, plan_continuous_guard
from tests import control_continuous_guard_commit as G
from tests.control_continuous_guard import build


_OMITTED = object()
_MISMATCH = "GUARD_COMMIT_EVALUATION_TIME_MISMATCH"


def commit(s, package, *, expected=_OMITTED, now=None):
    options = {} if expected is _OMITTED else {"expected_evaluated_at": expected}
    return C.commit_continuous_guard(package, now=package["now"] if now is None else now,
        expected_guard_head=s.state.state_sha256,
        expected_baseline_head=s.state.baseline.state_digest, expected_control_head=GENESIS,
        journal=s.journal, guard_store=s.gstore, guard_head=s.ghead,
        baseline_store=s.bstore, baseline_head=s.bhead, **options)


def refused(call, code):
    try:
        call()
    except ContinuousGuardError as exc:
        assert str(exc) == code, (str(exc), code)
    else:
        raise AssertionError("expected " + code)


def snapshot(s):
    return (s.ghead.read(), s.bhead.read(),
        (s.gstore._root / "checkpoint.json").read_bytes(),
        (s.bstore._root / "checkpoint.json").read_bytes(),
        json.dumps(G.rows(s), sort_keys=True, separators=(",", ":")))


def pending(s, package, stage):
    if stage == "guard_before_head":
        G.refused(lambda: G.commit(s, package, guard=G.Head(s.ghead, crash=True)),
                  "GUARD_CHECKPOINT_HEAD_UPDATE_FAILED")
        assert G.classify(s).status == C.PENDING_CROSS_STORE
    else:
        assert stage == "before_complete"
        try:
            with G.crash_on_append(C.COMPLETE):
                G.commit(s, package)
        except G.Crash:
            pass
        else:
            raise AssertionError("actual completion append was not interrupted")
        assert G.classify(s).status == C.PENDING_FINALIZATION


def test_fresh_commit_binds_original_instant_and_keeps_receipt_time_and_halt_distinct():
    for prices, halted in ((("101",), False), (("110", "105", "115"), True)):
        with G.stack() as s:
            package = build(s.state, s.policy, s.context, prices)
            expected = package["now"].astimezone(timezone.utc)
            received = expected + timedelta(seconds=5)
            actual = plan_continuous_guard(s.state, **package)
            receipt = commit(s, package, expected=expected, now=received)
            stored = s.gstore.load(expected_head=receipt.guard_head)
            assert stored == actual.proposed_checkpoint
            assert stored.recorded_at == expected and stored.recorded_at != received
            assert receipt.permanently_halted is halted and not receipt.replayed
            assert [row["kind"] for row in G.rows(s)] == [C.PREPARE] + ["halt"] * halted + [C.COMPLETE]
            assert all(datetime.fromisoformat(row["utc"]) == received for row in G.rows(s))


def test_optional_and_package_times_require_exact_aware_datetime_before_journal():
    class DateSubclass(datetime):
        pass

    with G.stack() as s:
        package = build(s.state, s.policy, s.context)
        at = package["now"]
        bad = (True, 0, 1.0, at.isoformat(), at.replace(tzinfo=None),
               DateSubclass(at.year, at.month, at.day, at.hour, at.minute, at.second, tzinfo=at.tzinfo))
        before = snapshot(s)
        with patch.object(Journal, "transaction", side_effect=AssertionError("must refuse before journal")):
            for value in bad:
                refused(lambda: commit(s, package, expected=value, now=at), "GUARD_AWARE_TIME_REQUIRED")
                malformed = dict(package, now=value)
                refused(lambda: commit(s, malformed, expected=at, now=at), "GUARD_AWARE_TIME_REQUIRED")
        assert snapshot(s) == before


def test_retained_time_different_from_supplied_package_refuses_before_journal():
    with G.stack() as s:
        package = build(s.state, s.policy, s.context)
        before = snapshot(s)
        with patch.object(Journal, "transaction", side_effect=AssertionError("must refuse before journal")):
            refused(lambda: commit(s, package, expected=package["now"] + timedelta(microseconds=1)), _MISMATCH)
        assert snapshot(s) == before


def test_consistent_same_time_retry_keeps_original_checkpoint_and_all_durable_bytes():
    with G.stack() as s:
        package = build(s.state, s.policy, s.context)
        first = commit(s, package, expected=package["now"])
        before = snapshot(s)
        second = commit(s, package, expected=package["now"].astimezone(timezone.utc),
                        now=package["now"] + timedelta(minutes=2))
        assert second.replayed and second.transaction_id == first.transaction_id
        assert second.guard_head == first.guard_head and second.control_head == first.control_head
        assert snapshot(s) == before


def test_changed_evaluation_duplicate_is_refused_but_legacy_omitted_and_none_still_replay():
    with G.stack() as s:
        original = build(s.state, s.policy, s.context)
        changed = dict(original, now=original["now"] + timedelta(seconds=1))
        first_plan = plan_continuous_guard(s.state, **original)
        other_plan = plan_continuous_guard(s.state, **changed)
        assert first_plan.input_sha256 == other_plan.input_sha256
        assert first_plan.proposed_checkpoint.state_sha256 != other_plan.proposed_checkpoint.state_sha256
        first = commit(s, original)
        before = snapshot(s)
        refused(lambda: commit(s, changed, expected=changed["now"]), _MISMATCH)
        assert snapshot(s) == before
        for optional in (_OMITTED, None):
            replay = commit(s, changed, expected=optional)
            assert replay.replayed and replay.transaction_id == first.transaction_id
            assert replay.guard_head == first.guard_head
            assert s.gstore.load(expected_head=replay.guard_head).recorded_at == original["now"]
            assert snapshot(s) == before


def test_pending_stored_successor_time_mismatch_refuses_before_further_commit_then_exact_resumes():
    for stage in ("guard_before_head", "before_complete"):
        with G.stack() as s:
            package = build(s.state, s.policy, s.context)
            pending(s, package, stage)
            before = snapshot(s)
            changed = dict(package, now=package["now"] + timedelta(seconds=1))
            refused(lambda: commit(s, changed, expected=changed["now"]), _MISMATCH)
            assert snapshot(s) == before
            replay = commit(s, package, expected=package["now"], now=changed["now"])
            assert replay.replayed and replay.permanently_halted
            assert G.classify(s).status == C.CONSISTENT
            assert G.kinds(s) == [C.PREPARE, "halt", C.COMPLETE]
            assert s.gstore.load(expected_head=replay.guard_head).recorded_at == package["now"]


def test_pending_changed_now_legacy_none_preserves_existing_completion_semantics():
    for stage in ("guard_before_head", "before_complete"):
        with G.stack() as s:
            package = build(s.state, s.policy, s.context)
            pending(s, package, stage)
            changed = dict(package, now=package["now"] + timedelta(seconds=1))
            replay = commit(s, changed, expected=None)
            assert replay.replayed and G.classify(s).status == C.CONSISTENT
            assert s.gstore.load(expected_head=replay.guard_head).recorded_at == package["now"]
            assert G.kinds(s) == [C.PREPARE, "halt", C.COMPLETE]


def test_actual_competing_commit_between_preflight_and_journal_lock_cannot_rebind_retained_time():
    with G.stack() as s:
        original = build(s.state, s.policy, s.context)
        retained = dict(original, now=original["now"] + timedelta(seconds=2))
        competing = dict(original, now=original["now"] + timedelta(seconds=1))
        preflight = plan_continuous_guard(s.state, **retained)
        assert preflight.proposed_checkpoint.recorded_at == retained["now"]
        original_transaction = Journal.transaction
        raced = []

        @contextmanager
        def before_actual_lock(journal):
            if journal is s.journal and not raced:
                raced.append(None)
                winner = commit(s, competing, expected=competing["now"])
                raced[0] = (winner, snapshot(s))
            with original_transaction(journal) as tx:
                yield tx

        with patch.object(Journal, "transaction", before_actual_lock):
            refused(lambda: commit(s, retained, expected=retained["now"]), _MISMATCH)
        winner, after_winner = raced[0]
        assert winner.guard_head != preflight.proposed_checkpoint.state_sha256
        assert snapshot(s) == after_winner
        assert s.gstore.load(expected_head=winner.guard_head).recorded_at == competing["now"]
        assert G.kinds(s).count(C.PREPARE) == G.kinds(s).count(C.COMPLETE) == 1


def test_package_now_mutation_after_admission_is_not_hidden_by_duplicate_checkpoint():
    with G.stack() as s:
        original = build(s.state, s.policy, s.context)
        committed = commit(s, original)
        expected = original["now"]
        before = snapshot(s)
        candidate = dict(original)
        original_transaction = Journal.transaction
        changed = []

        @contextmanager
        def mutate_before_lock(journal):
            if journal is s.journal and not changed:
                changed.append(True)
                candidate["now"] = expected + timedelta(seconds=1)
            with original_transaction(journal) as tx:
                yield tx

        with patch.object(Journal, "transaction", mutate_before_lock):
            refused(lambda: commit(s, candidate, expected=expected, now=expected + timedelta(seconds=1)), _MISMATCH)
        assert snapshot(s) == before
        assert s.gstore.load(expected_head=committed.guard_head).recorded_at == expected
