"""Real local guard commits projected read-only; invented owner/coverage/account evidence.

The fixtures use actual Journal transactions, checkpoint stores, and independent
retained heads in temporary roots. Their coverage and owner claims are explicitly
synthetic: these tests establish local provenance, never production authority.
"""
from contextlib import contextmanager, ExitStack
from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta
from decimal import Decimal
import threading
from unittest.mock import patch

from core.compliance.model import KST
from execution_accounts import baseline_bridge as B
from execution_accounts.baseline_store import CheckpointStore
from execution_accounts.model import content_digest
from execution_control.capability import digest as control_digest
from execution_control.store import GENESIS, Journal, Transaction
from execution_launch import committed_account as C
from execution_launch.account_interval import AccountIntervalError, ContinuousUpbitCandidateSource
from execution_launch.baseline_head import BaselineHead, CheckpointChain
from execution_launch.continuous_guard_commit import (
    COMPLETE, GuardChain, GuardCheckpointStore, commit_continuous_guard,
)
from tests import control_continuous_guard_commit as G
from tests.control_continuous_guard import START, build, policy

D = Decimal


def refused(call, code=None):
    try:
        call()
    except C.CommittedAccountError as exc:
        assert str(exc).startswith("COMMITTED_ACCOUNT_"), str(exc)
        if code is not None:
            assert str(exc) == code, (str(exc), code)
        return str(exc)
    raise AssertionError("expected committed-account refusal")


def provider(s, package, receipt, **changes):
    values = dict(package=package, receipt=receipt,
        expected_guard_head=s.state.state_sha256,
        expected_baseline_head=s.state.baseline.state_digest,
        expected_control_head=GENESIS, journal=s.journal, guard_store=s.gstore,
        guard_head=s.ghead, baseline_store=s.bstore, baseline_head=s.bhead)
    return C.CommittedAccountProvider(**(values | changes))


@contextmanager
def committed(*, prices=("101",), end=None, **seed):
    with G.stack(**seed) as s:
        package = build(s.state, s.policy, s.context, prices, end=end)
        receipt = G.commit(s, package)
        yield s, package, receipt


def files(s):
    """Only the two explicit temporary fixture roots, never a configured real home."""
    roots = (s.bstore._root.parent, s.bhead._root)
    return {(index, str(path.relative_to(root))): path.read_bytes()
            for index, root in enumerate(roots) for path in root.rglob("*") if path.is_file()}


def read(s, bridge, now):
    with s.journal.transaction() as tx:
        return bridge.read(now=now, transaction=tx)


def risk_row(s, *, high="120", floor="118", stop=True, at=None):
    at = at or START + timedelta(seconds=3)
    data = dict(policy_digest=control_digest(s.policy), day=at.astimezone(KST).date().isoformat(),
        high_watermark=high, day_start_equity="100", effective_floor=floor,
        calculated_floor=floor, daily_stopped=stop, floor_relaxation_approved=False)
    with s.journal.transaction() as tx:
        return tx.append("risk_snapshot", data, now=at)


def test_real_commit_projection_is_read_only_and_not_an_account_provider():
    with committed() as (s, package, receipt):
        bridge = provider(s, package, receipt)
        before = files(s)
        with s.journal.transaction() as tx, ExitStack() as blocked:
            for obj, name in ((Journal, "transaction"), (Journal, "snapshot"),
                              (Transaction, "append"), (CheckpointStore, "commit"),
                              (CheckpointStore, "seed"), (GuardCheckpointStore, "commit"),
                              (GuardCheckpointStore, "seed"), (BaselineHead, "compare_and_set"),
                              (BaselineHead, "initialize_reviewed_head"), (B, "advance_baseline"),
                              (B, "initialize_baseline")):
                blocked.enter_context(patch.object(obj, name, side_effect=AssertionError("unexpected mutation")))
            result = bridge.read(now=package["now"], transaction=tx)
            again = bridge.read(now=package["now"], transaction=tx)
        assert files(s) == before and result == again
        assert result.execution_ready is False and not callable(bridge)
        assert not hasattr(bridge, "commit") and not hasattr(bridge, "publish")
        assert result.transaction_id == receipt.transaction_id
        assert result.guard_head == receipt.guard_head and result.baseline_head == receipt.baseline_head
        assert result.completion_head == result.receipt_control_head == result.observed_control_head
        assert result.observation.asof == package["interval"].end
        assert result.observation.risk.equity == D("101")
        try:
            result.execution_ready = True
        except (FrozenInstanceError, AttributeError):
            pass
        else:
            raise AssertionError("projection granted execution readiness")


def test_existing_live_candidate_source_gate_remains_closed():
    # __call__ unconditionally refuses; no collector or API is constructed.
    candidate = object.__new__(ContinuousUpbitCandidateSource)
    try:
        candidate(None, START)
    except AccountIntervalError as exc:
        assert str(exc) == "CONTINUOUS_LIVE_RISK_INTEGRATION_REQUIRED"
    else:
        raise AssertionError("read-only bridge opened a production source")


def test_restart_uses_actual_stores_and_heads_without_readopting_or_advancing():
    with committed() as (s, package, receipt):
        first = read(s, provider(s, package, receipt), package["now"])
        before = files(s)
        bstore = CheckpointStore(root=s.bstore._root.parent)
        gstore = GuardCheckpointStore(root=s.gstore._root.parent)
        restarted = provider(s, package, receipt,
            baseline_store=bstore, guard_store=gstore,
            baseline_head=BaselineHead(root=s.bhead._root, name=s.bhead._dir.name,
                                       chain=CheckpointChain(bstore)),
            guard_head=BaselineHead(root=s.ghead._root, name=s.ghead._dir.name, chain=GuardChain(gstore)))
        assert read(s, restarted, package["now"]) == first
        assert files(s) == before


def test_replayed_receipt_can_name_later_tail_while_completion_is_preserved():
    with committed() as (s, package, receipt):
        complete_head = receipt.control_head
        risk_row(s, at=package["now"])
        with s.journal.transaction() as tx:
            tail = tx.append("kill", {"session_id": "fixture-session", "reason": "owner_requested"},
                             now=package["now"])
        replayed = G.commit(s, package)
        assert replayed.replayed and replayed.control_head == tail["row_sha256"] != complete_head
        result = read(s, provider(s, package, replayed), package["now"])
        assert result.completion_head == complete_head
        assert result.receipt_control_head == result.observed_control_head == tail["row_sha256"]
        assert result.observation.risk.prior_high_watermark == D("120")
        assert result.observation.risk.approved_effective_floor == D("118")
        assert result.daily_stopped


def test_fresh_receipt_does_not_hide_later_risk_and_halt_suffix():
    with committed() as (s, package, receipt):
        risk_row(s, at=package["now"])
        with s.journal.transaction() as tx:
            tail = tx.append("halt", {"floor": "119"}, now=package["now"])
        before = files(s)
        result = read(s, provider(s, package, receipt), package["now"])
        assert result.receipt_control_head == receipt.control_head
        assert result.observed_control_head == tail["row_sha256"] != receipt.control_head
        assert result.observation.risk.halted and result.daily_stopped
        assert result.observation.risk.prior_high_watermark >= D("120")
        assert result.observation.risk.approved_effective_floor >= D("118")
        assert files(s) == before


def test_intrainterval_peak_drop_recovery_keeps_guard_halt_and_floor():
    with committed(prices=("110", "105", "115")) as (s, package, receipt):
        result = read(s, provider(s, package, receipt), package["now"])
        assert result.observation.risk.equity == D("115")
        assert result.observation.risk.prior_high_watermark == D("115")
        assert result.observation.risk.approved_effective_floor == D("115")
        assert result.observation.risk.halted
        # Endpoint baseline alone did not contain this interval's ratcheted floor.
        assert s.bstore.load(expected_head=receipt.baseline_head).approved_effective_floor < D("115")


def test_daily_stop_is_separate_from_permanent_halt_and_survives_recovery():
    with committed(prices=("99", "100"), pol=policy(initial="50", activation="50"),
                   floor="65", daily="0.5") as (s, package, receipt):
        result = read(s, provider(s, package, receipt), package["now"])
        assert result.daily_stopped and not result.observation.risk.halted
        assert result.policy_day == package["now"].astimezone(KST).date()
        assert result.observation.risk.observed_daily_loss == D("1")
        assert result.observation.risk.equity == result.observation.risk.day_start_equity == D("100")


def test_midnight_retains_old_day_violation_without_relabeling_it_as_today():
    start = datetime(2026, 11, 6, 23, 59, 50, tzinfo=KST)
    end = datetime(2026, 11, 7, tzinfo=KST)
    with committed(prices=("99", "100"), start=start, end=end,
                   pol=policy(initial="50", activation="50"), floor="65", daily="0.5") as (s, package, receipt):
        before = files(s)
        result = read(s, provider(s, package, receipt), end)
        assert result.policy_day == end.date() and not result.daily_stopped
        assert result.observation.risk.observed_daily_loss == 0
        assert not result.observation.risk.halted and files(s) == before
        prepare = G.rows(s)[0]["data"]
        daily = [row for row in prepare["required_records"] if row["kind"] == "daily_stop"]
        assert daily and daily[0]["policy_day"] == start.date().isoformat()


def test_recovery_checkpoint_keeps_exact_source_and_failed_recovery_stop():
    start = datetime(2026, 11, 6, 21, 59, 50, tzinfo=KST)
    end = datetime(2026, 11, 6, 22, tzinfo=KST)
    with committed(prices=("99",), start=start, end=end,
                   pol=policy(initial="50", activation="50", recovery=True), floor="65") as (s, package, receipt):
        result = read(s, provider(s, package, receipt), end)
        retained = s.bstore.load(expected_head=receipt.baseline_head).recovery_checkpoint
        assert result.observation.risk.recovery_checkpoint == retained
        assert retained.source_sha256 == package["interval"].source_sha256
        assert retained.equity_krw == D("99") and result.daily_stopped
        assert not result.observation.risk.halted


def test_only_active_exact_bound_transaction_on_owning_thread_is_accepted():
    with committed() as (s, package, receipt):
        bridge = provider(s, package, receipt)
        fake = Transaction(s.journal, [], 0)
        refused(lambda: bridge.read(now=package["now"], transaction=fake))
        with s.journal.transaction() as tx:
            outcome = []
            thread = threading.Thread(target=lambda: outcome.append(refused(
                lambda: bridge.read(now=package["now"], transaction=tx))))
            thread.start(); thread.join(timeout=5)
            assert not thread.is_alive() and len(outcome) == 1
        refused(lambda: bridge.read(now=package["now"], transaction=tx))
        other = Journal(root=s.journal._root.parent / "other-control")
        with other.transaction() as foreign:
            refused(lambda: bridge.read(now=package["now"], transaction=foreign))


def test_receipt_and_predecessor_substitution_never_create_provenance():
    with committed() as (s, package, receipt):
        for field in ("transaction_id", "guard_head", "baseline_head", "control_head"):
            bad = replace(receipt, **{field: "f" * 64})
            refused(lambda: read(s, provider(s, package, bad), package["now"]))
        for field in ("expected_guard_head", "expected_baseline_head", "expected_control_head"):
            refused(lambda: read(s, provider(s, package, receipt, **{field: "f" * 64}), package["now"]))
        refused(lambda: read(s, provider(s, package, replace(receipt, permanently_halted=True)), package["now"]))


def test_changed_endpoint_and_input_package_cannot_reuse_committed_receipt():
    with committed() as (s, package, receipt):
        capture = package["account_capture"]
        account = replace(capture.endpoint_accounts[0], opening_source_sha256="f" * 64)
        changed = replace(capture, endpoint_accounts=(account,))
        altered = package | {"account_capture": changed}
        refused(lambda: read(s, provider(s, altered, receipt), package["now"]))
        # A fresh matching hash of substituted accounts still is not this commit.
        altered["interval"] = replace(package["interval"], source_sha256=content_digest((account,)))
        refused(lambda: read(s, provider(s, altered, receipt), package["now"]))
        altered = package | {"owner_after": replace(package["owner_after"], source_sha256="f" * 64)}
        refused(lambda: read(s, provider(s, altered, receipt), package["now"]))


def test_checkpoint_rollback_under_advanced_head_is_refused_without_repair():
    for store_name in ("gstore", "bstore"):
        with G.stack() as s:
            path = getattr(s, store_name)._root / "checkpoint.json"
            original = path.read_bytes()
            package = build(s.state, s.policy, s.context, ("101",))
            receipt = G.commit(s, package)
            bridge = provider(s, package, receipt)
            path.write_bytes(original)
            before = files(s)
            refused(lambda: read(s, bridge, package["now"]))
            assert files(s) == before


def test_missing_completion_is_not_repaired_or_published():
    with G.stack() as s:
        package = build(s.state, s.policy, s.context, ("101",))
        try:
            with G.crash_on_append(COMPLETE):
                G.commit(s, package)
        except G.Crash:
            pass
        else:
            raise AssertionError("completion fault did not fire")
        # An invented receipt cannot repair a genuinely pending durable prefix.
        from execution_launch.continuous_guard_commit import GuardCommitReceipt
        row = G.rows(s)[0]
        receipt = GuardCommitReceipt(transaction_id=row["data"]["transaction_id"],
            guard_head=s.ghead.read(), baseline_head=s.bhead.read(), control_head=row["row_sha256"],
            permanently_halted=False, replayed=False)
        before = files(s)
        refused(lambda: read(s, provider(s, package, receipt), package["now"]))
        assert files(s) == before


def test_store_change_during_reconciliation_is_caught_before_return():
    for store_name in ("gstore", "bstore"):
        with committed() as (s, package, receipt):
            bridge = provider(s, package, receipt)
            path = getattr(s, store_name)._root / "checkpoint.json"
            original = C.reconcile_committed_baseline
            seen = []
            def changed(*args, **kwargs):
                answer = original(*args, **kwargs)
                path.write_bytes(b"{}")
                seen.append(True)
                return answer
            with patch.object(C, "reconcile_committed_baseline", changed):
                refused(lambda: read(s, bridge, package["now"]))
            assert seen == [True] and path.read_bytes() == b"{}"


def test_retained_head_change_during_reconciliation_is_caught_before_return():
    for head_name in ("ghead", "bhead"):
        with G.stack() as s:
            path = getattr(s, head_name)._dir / "head.json"
            prior = path.read_bytes()
            package = build(s.state, s.policy, s.context, ("101",))
            receipt = G.commit(s, package)
            bridge = provider(s, package, receipt)
            original = C.reconcile_committed_baseline
            seen = []
            def changed(*args, **kwargs):
                answer = original(*args, **kwargs)
                path.write_bytes(prior)
                seen.append(True)
                return answer
            with patch.object(C, "reconcile_committed_baseline", changed):
                refused(lambda: read(s, bridge, package["now"]))
            assert seen == [True] and path.read_bytes() == prior


def test_freshness_exact_boundary_rollback_and_seoul_rollover():
    with committed() as (s, package, receipt):
        bridge = provider(s, package, receipt)
        now = package["now"]
        result = read(s, bridge, now + timedelta(seconds=30))
        assert result.observation.asof == now  # no restamping old evidence
        refused(lambda: read(s, bridge, now - timedelta(microseconds=1)))
        refused(lambda: read(s, bridge, now + timedelta(seconds=30, microseconds=1)))
    start = datetime(2026, 11, 6, 23, 59, 55, tzinfo=KST)
    with committed(start=start) as (s, package, receipt):
        bridge = provider(s, package, receipt)
        refused(lambda: read(s, bridge, datetime(2026, 11, 7, tzinfo=KST)))


def test_invalid_later_controller_lifecycle_is_not_hidden_by_valid_guard():
    with committed() as (s, package, receipt):
        with s.journal.transaction() as tx:
            tx.append("acknowledged", {"client_id": "never-reserved", "order_digest": "a" * 64,
                "venue_order_id": "unknown", "metadata": {}}, now=package["now"])
        before = files(s)
        refused(lambda: read(s, provider(s, package, receipt), package["now"]))
        assert files(s) == before


def test_same_day_denominator_and_post_commit_relaxation_are_not_silently_merged():
    for changes in ({"day_start_equity": "99"}, {"floor_relaxation_approved": True}):
        with committed() as (s, package, receipt):
            data = dict(policy_digest=control_digest(s.policy), day=START.date().isoformat(),
                high_watermark="120", day_start_equity="100", effective_floor="110",
                calculated_floor="110", daily_stopped=False, floor_relaxation_approved=False) | changes
            with s.journal.transaction() as tx:
                tx.append("risk_snapshot", data, now=package["now"])
            before = files(s)
            refused(lambda: read(s, provider(s, package, receipt), package["now"]))
            assert files(s) == before


def test_original_caller_package_mutation_does_not_change_the_retained_snapshot():
    with committed() as (s, package, receipt):
        bridge = provider(s, package, receipt)
        original_now = package["now"]
        expected = read(s, bridge, original_now)
        capture = package["account_capture"]
        # Bypass a frozen dataclass solely to reproduce a caller mutating its
        # own original object after construction; the holder must own its copy.
        object.__setattr__(capture.endpoint_accounts[0], "opening_source_sha256", "f" * 64)
        package["now"] = original_now + timedelta(seconds=1)
        assert read(s, bridge, original_now) == expected


def test_control_prefix_change_during_reconciliation_is_not_returned_as_old_proof():
    with committed() as (s, package, receipt):
        bridge = provider(s, package, receipt)
        original = C.reconcile_committed_baseline
        with s.journal.transaction() as tx:
            def changed(*args, **kwargs):
                answer = original(*args, **kwargs)
                tx.append("kill", {"session_id": "fixture-session", "reason": "owner_requested"},
                          now=package["now"])
                return answer
            with patch.object(C, "reconcile_committed_baseline", changed):
                refused(lambda: bridge.read(now=package["now"], transaction=tx))
            assert tx.events[-1]["kind"] == "kill"


def test_current_prefix_time_cannot_be_after_the_requested_observation_time():
    with committed() as (s, package, receipt):
        with s.journal.transaction() as tx:
            tx.append("kill", {"session_id": "fixture-session", "reason": "owner_requested"},
                      now=package["now"] + timedelta(seconds=1))
        refused(lambda: read(s, provider(s, package, receipt), package["now"]))


def test_original_package_time_is_bound_even_though_commit_receipt_time_can_be_later():
    with committed() as (s, package, receipt):
        later = package["now"] + timedelta(seconds=1)
        altered = package | {"now": later}
        refused(lambda: read(s, provider(s, altered, receipt), later))
        # A later actual commit retry time is supported, with the original
        # evidence package retained rather than restamped to match receipt time.
        replayed = G.commit(s, package, now=later)
        answer = read(s, provider(s, package, replayed), later)
        assert answer.observation.asof == package["now"]


def test_head_change_inside_final_store_load_is_not_missed_by_preload_readback():
    with G.stack() as s:
        head_path = s.ghead._dir / "head.json"
        prior = head_path.read_bytes()
        package = build(s.state, s.policy, s.context, ("101",))
        receipt = G.commit(s, package)
        bridge = provider(s, package, receipt)
        original = s.bstore.load
        calls = []
        def changed(*args, **kwargs):
            answer = original(*args, **kwargs)
            calls.append(True)
            if len(calls) == 2:
                head_path.write_bytes(prior)
            return answer
        with patch.object(s.bstore, "load", changed):
            refused(lambda: read(s, bridge, package["now"]))
        assert len(calls) == 2 and head_path.read_bytes() == prior


def test_actual_journal_bytes_changed_after_transaction_load_are_refused():
    with committed() as (s, package, receipt):
        bridge = provider(s, package, receipt)
        path = s.journal._root / "journal.jsonl"
        with s.journal.transaction() as tx:
            # Preserve the cached events and byte length while damaging the
            # actual stored row; the held prefix alone is no longer sufficient.
            raw = path.read_bytes()
            altered = raw.replace(receipt.transaction_id.encode(), b"f" * 64, 1)
            assert len(altered) == len(raw) and altered != raw
            path.write_bytes(altered)
            refused(lambda: bridge.read(now=package["now"], transaction=tx))
        assert path.read_bytes() == altered


def test_latest_precommit_control_floor_is_retained_without_undoing_earlier_approved_relaxation():
    for prior_relaxation, expected_floor in ((False, D("120")), (True, D("110"))):
        with G.stack() as s:
            data = dict(policy_digest=control_digest(s.policy), day=START.date().isoformat(),
                high_watermark="120", day_start_equity="100", effective_floor="120",
                calculated_floor="110", daily_stopped=False, floor_relaxation_approved=False)
            with s.journal.transaction() as tx:
                if prior_relaxation:
                    previous_day = START - timedelta(days=1)
                    tx.append("risk_snapshot", data | {"day": previous_day.date().isoformat()}, now=previous_day)
                    data |= {"effective_floor": "110", "floor_relaxation_approved": True}
                predecessor = tx.append("risk_snapshot", data, now=START)["row_sha256"]
            package = build(s.state, s.policy, s.context, ("101",))
            receipt = G.commit(s, package, control=predecessor)
            result = read(s, provider(s, package, receipt, expected_control_head=predecessor), package["now"])
            assert result.observation.risk.approved_effective_floor == expected_floor
            assert result.observation.risk.prior_high_watermark == D("120")


def test_suffix_uses_actual_controller_policy_digest_without_changing_guard_commitment():
    with committed(pol=policy(initial="1E+2")) as (s, package, receipt):
        assert control_digest(s.policy) != content_digest(s.policy)
        risk_row(s, at=package["now"])
        answer = read(s, provider(s, package, receipt), package["now"])
        assert answer.policy_sha256 == content_digest(s.policy)
        assert answer.observation.risk.approved_effective_floor == D("118")
        assert answer.daily_stopped


def test_journal_open_race_is_a_fixed_refusal_without_private_os_details():
    with committed() as (s, package, receipt):
        bridge = provider(s, package, receipt)
        with s.journal.transaction() as tx:
            original = s.journal._read
            removed = []
            def disappear(name, maximum):
                if name == "journal.jsonl" and not removed:
                    (s.journal._root / name).unlink()
                    removed.append(True)
                return original(name, maximum)
            with patch.object(s.journal, "_read", disappear):
                refused(lambda: bridge.read(now=package["now"], transaction=tx))
        assert removed == [True] and not (s.journal._root / "journal.jsonl").exists()
