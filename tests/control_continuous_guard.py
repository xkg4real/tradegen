"""Chronological guard plans over invented raw paths; no actual authority or I/O."""
from dataclasses import replace
from datetime import date, datetime, timedelta
from decimal import Decimal, localcontext
from unittest.mock import patch

from core.compliance.model import KST
from execution_accounts.baseline import BaselineAnchor, BaselineConventions, BaselineInterval, initialize_baseline
from execution_accounts.continuous import (
    COVERAGE_CONTRACT, ContinuousPath, EquityEvent, PriceMark, VerifiedCoverage, verify_coverage, value_path,
)
from execution_accounts.model import (
    AccountEvidence, AccountRestrictions, BrokerOrder, CashAmount, CashBalance, EvidencePage,
    FxRate, Position, RiskBaseline, content_digest,
)
from execution_launch.continuous_guard import (
    AccountCaptureInputs, GuardAnchor, OwnerContextClaim, ValuationInputs,
    plan_continuous_guard, reviewed_guard_anchor,
)
from execution_control.risk import Fill, RecoveryCondition, RiskPolicy

D = Decimal
START = datetime(2026, 11, 6, 20, tzinfo=KST)
SCOPE = "synthetic-guard-account"


def policy(*, initial="100", activation="6000", recovery=False):
    return RiskPolicy(version="test-only", initial_equity=D(initial), drawdown_activation_equity=D(activation),
        positive_profit_loss_fraction=D("0.35"), peak_drawdown_fraction=D("0.35"),
        zero_profit_day_target_fraction=D("0.3"), first_day_loss_budget=D("10"), zero_profit_day_loss_budget=D("10"),
        valuation_convention="marked_equity", daily_loss_convention="externally_reconciled",
        recovery_condition=RecoveryCondition(cutoff_seconds=79200, timezone="Asia/Seoul",
                                            reference="day_start_marked_equity") if recovery else None)


def owner(at, *, floor="100", daily="10"):
    return OwnerContextClaim(owner_head_sha256="1"*64, code_sha256="2"*64, code_approval_sha256="3"*64,
        signed_floor_krw=D(floor), signed_daily_loss_krw=D(daily), observed_at=at, source_sha256="4"*64)


def seed(*, start=START, pol=None, floor="100", daily="10", equity="100", high=None,
         loss="0", daily_stopped=False, halted=False):
    pol = pol or policy()
    high = equity if high is None else high
    baseline = initialize_baseline(BaselineConventions(daily_loss="maximum_net_equity_loss_from_day_open",
        external_flows="no_external_flows", max_interval_seconds=30,
        recovery_cutoff_seconds=79200 if pol.recovery_condition else None),
        BaselineAnchor(account_scope=SCOPE,
            baseline=RiskBaseline(day_start_equity=D(equity), prior_high_watermark=D(high),
                observed_daily_loss=D(loss), approved_effective_floor=D(floor), first_trading_day=start.date(),
                asof=start, source_sha256="5"*64),
            equity_krw=D(equity), realized_net_total_krw=D(0), day_open_realized_net_total_krw=D(0),
            previous_day_realized_net_krw=None, sequence=0))
    context = owner(start, floor=floor, daily=daily)
    anchor = GuardAnchor(baseline_state_sha256=baseline.state_digest, control_journal_head_sha256="6"*64,
        high_watermark=D(high), day_start_equity=D(equity), observed_daily_loss=D(loss), applied_floor_krw=D(floor),
        daily_stopped=daily_stopped, permanently_halted=halted, recorded_at=start, source_sha256="7"*64)
    checkpoint = reviewed_guard_anchor(anchor, baseline=baseline, policy=pol, owner=context)
    return checkpoint, pol, context


def build(checkpoint, pol, before, prices=("110", "105", "115"), *, end=None, same_instant=False):
    baseline = checkpoint.baseline
    start = baseline.asof
    end = end or start+timedelta(seconds=len(prices)+1)
    # One historical zero-fee unit at original price 100; the path's opening
    # valuation can differ after a preceding interval without changing FIFO P&L.
    historical = (Fill(venue="upbit", account_scope=SCOPE, order_id="buy-origin", fill_id="fill-origin",
        market="spot", symbol="KRW-BTC", side="buy", quantity=D(1), price=D("100"), quote_currency="KRW",
        quote_krw=D(1), fee_amount=D(0), fee_currency="KRW", base_currency="BTC",
        executed_at=START-timedelta(hours=2)),)
    first_sequence = checkpoint.next_sequence if checkpoint.next_sequence is not None else 1
    events = tuple(EquityEvent(sequence=first_sequence+index, at=start+timedelta(seconds=1 if same_instant else index+1),
        received_at=start+timedelta(seconds=1 if same_instant else index+1), source_sha256="8"*64,
        mark=PriceMark(symbol="KRW-BTC", price=D(price), asof=start+timedelta(seconds=1 if same_instant else index+1)))
        for index, price in enumerate(prices))
    path = ContinuousPath(account_scope=SCOPE, stream_epoch="synthetic-epoch", previous_state_digest=baseline.state_digest,
        start=start, end=end, opening_marks=(PriceMark(symbol="KRW-BTC", price=baseline.equity_krw, asof=start),),
        first_sequence=first_sequence, events=events, watermark_sequence=first_sequence+len(events), watermark_received_at=end,
        watermark_source_sha256="9"*64)
    inputs = ValuationInputs(opening_cash_krw=D(0), opening_units=(("KRW-BTC", D(1)),),
                             historical_fills=historical, interval_fills=())
    ending_price = D(prices[-1]) if prices else baseline.equity_krw
    manifest_sha = "a"*64
    origin = START-timedelta(hours=3)
    trade_order = BrokerOrder(client_id="", order_id="buy-origin", market="spot", symbol="KRW-BTC",
        side="buy", quote_currency="KRW", quantity=D(1), filled_quantity=D(1), remaining_quantity=D(0),
        limit_price=D("100"), reserved_cash=D(0), status="filled", cancelable_quantity=D(0))
    pages = tuple(EvidencePage(kind=kind, cursor=None, next_cursor=None, start=origin, end=end,
        rows=rows, source_sha256=manifest_sha)
        for kind, rows in (("fills", historical), ("flows", ()), ("orders", (trade_order,))))
    account = AccountEvidence(venue="upbit", account_scope=SCOPE, execution_quote="KRW", origin=origin,
        opening_cash=(CashAmount(currency="KRW", amount=D("100")),), opening_source_sha256="e"*64,
        balances=(CashBalance(currency="KRW", total=D(0), settled=D(0)),),
        positions=(Position(market="spot", symbol="KRW-BTC", base_currency="BTC", quote_currency="KRW",
                            units=D(1), price=ending_price, asof=end),),
        fx=(FxRate(currency="KRW", krw=D(1), asof=end, source_sha256=manifest_sha),), pages=pages,
        restrictions=AccountRestrictions(cash_mode="cash", borrowing_enabled=False, auto_loan=False,
            liabilities=(), asof=end, source_sha256=manifest_sha), observed_at=end, server_time=end)
    capture = AccountCaptureInputs(manifest_sha256=manifest_sha, captured_accounts=(account,),
                                    endpoint_accounts=(account,), first_received_at=end)
    capture_sha = content_digest((manifest_sha, capture.captured_accounts, capture.endpoint_accounts))
    def synthetic(request, supplied_path):
        return VerifiedCoverage(request_sha256=content_digest(request), contract=COVERAGE_CONTRACT,
            authority_sha256="b"*64, source_proof_sha256="c"*64, verified_at=supplied_path.watermark_received_at)
    coverage = verify_coverage(path, account_capture_sha256=capture_sha, verifier=synthetic, now=end)
    valuation = value_path(path, opening_cash_krw=inputs.opening_cash_krw, opening_units=inputs.opening_units,
        historical_fills=inputs.historical_fills, interval_fills=inputs.interval_fills,
        previous_equity_krw=baseline.equity_krw, previous_realized_net_krw=baseline.realized_net_total_krw)
    interval = BaselineInterval(account_scope=SCOPE, sequence=baseline.sequence+1,
        previous_state_digest=baseline.state_digest, start=start, end=end, equity_krw=valuation.equity_krw,
        minimum_equity_krw=valuation.minimum_equity_krw, maximum_equity_krw=valuation.maximum_equity_krw,
        realized_net_total_krw=valuation.realized_net_total_krw, gross_external_inflows_krw=D(0),
        gross_external_outflows_krw=D(0), source_sha256=content_digest(capture.endpoint_accounts),
        coverage_sha256=content_digest((path, coverage)))
    return dict(baseline_before=baseline, policy=pol, owner_before=before,
        owner_after=replace(before, observed_at=end), path=path, valuation_inputs=inputs,
        account_capture=capture, coverage=coverage, interval=interval, now=end)


def refused(call, code):
    try:
        call()
    except ValueError as exc:
        assert str(exc) == code, (str(exc), code)
        return
    raise AssertionError("expected " + code)


def test_peak_drop_recovery_latches_permanent_halt_despite_clean_endpoint_summary():
    state, pol, context = seed()
    args = build(state, pol, context)
    plan = plan_continuous_guard(state, **args)
    assert args["interval"].minimum_equity_krw == D("100")
    assert args["interval"].maximum_equity_krw == args["interval"].equity_krw == D("115")
    assert plan.proposed_checkpoint.permanently_halted
    assert plan.proposed_checkpoint.applied_floor_krw == D("115")
    halt, = (r for r in plan.required_records if r.kind == "permanent_floor_halt")
    assert halt.source_at == START+timedelta(seconds=2) and halt.floor_krw == D("110")
    assert halt.recorded_at == args["now"] > halt.source_at
    assert "PERSISTENT_HALT" in plan.points[-1].reasons
    assert plan.execution_ready is False and "GUARD_DURABLE_COMMIT_PROTOCOL_REQUIRED" in plan.blockers


def test_same_timestamp_events_preserve_authenticated_sequence_order():
    state, pol, context = seed()
    plan = plan_continuous_guard(state, **build(state, pol, context, same_instant=True))
    assert tuple(point.equity_krw for point in plan.points) == tuple(map(D, ("100", "110", "105", "115", "115")))
    halt, = (r for r in plan.required_records if r.kind == "permanent_floor_halt")
    assert halt.source_at == START+timedelta(seconds=1)


def test_d12_floor_ratchet_survives_activation_threshold_inside_interval():
    state, pol, context = seed(pol=policy(activation="110"))
    args = build(state, pol, context, ("109", "110", "108", "115"))
    plan = plan_continuous_guard(state, **args)
    assert plan.proposed_checkpoint.applied_floor_krw == D("109")
    assert plan.proposed_checkpoint.permanently_halted
    halt, = (r for r in plan.required_records if r.kind == "permanent_floor_halt")
    assert halt.floor_krw == D("109")


def test_current_controller_floor_is_not_replaced_by_lower_configured_floor():
    state, pol, context = seed(pol=policy(activation="100"), floor="100")
    plan = plan_continuous_guard(state, **build(state, pol, context, ("99", "105")))
    assert plan.proposed_checkpoint.permanently_halted
    assert plan.proposed_checkpoint.applied_floor_krw == D("100")


def test_prior_halt_persists_across_next_interval_without_duplicate_halt_record():
    state, pol, context = seed()
    first = plan_continuous_guard(state, **build(state, pol, context))
    next_state = first.proposed_checkpoint
    second = plan_continuous_guard(next_state, **build(next_state, pol,
        replace(context, observed_at=next_state.baseline.asof), ("116",)))
    assert second.proposed_checkpoint.permanently_halted
    assert not any(record.kind == "permanent_floor_halt" for record in second.required_records)
    assert all("PERSISTENT_HALT" in point.reasons for point in second.points)


def test_old_day_daily_limit_breach_is_recorded_before_midnight_reset():
    start = datetime(2026, 11, 6, 23, 59, 50, tzinfo=KST)
    state, pol, context = seed(start=start, pol=policy(initial="50", activation="50"), floor="65", daily="0.5")
    end = datetime(2026, 11, 7, tzinfo=KST)
    plan = plan_continuous_guard(state, **build(state, pol, context, ("99", "100"), end=end))
    assert not plan.proposed_checkpoint.permanently_halted
    assert not plan.proposed_checkpoint.daily_stopped
    assert plan.proposed_checkpoint.observed_daily_loss == 0
    daily, = (r for r in plan.required_records if r.kind == "daily_stop")
    assert daily.policy_day == date(2026, 11, 6) and daily.recorded_at == end
    assert daily.source_at == start+timedelta(seconds=1)
    assert plan.points[-2].boundary_side == "left" and plan.points[-2].daily_stopped
    assert plan.points[-1].boundary_side == "right" and not plan.points[-1].daily_stopped


def test_floor_breach_survives_midnight_with_high_watermark_and_floor():
    start = datetime(2026, 11, 6, 23, 59, 50, tzinfo=KST)
    state, pol, context = seed(start=start)
    plan = plan_continuous_guard(state, **build(state, pol, context,
        end=datetime(2026, 11, 7, tzinfo=KST)))
    assert plan.proposed_checkpoint.permanently_halted
    assert plan.proposed_checkpoint.high_watermark == D("115")
    assert plan.proposed_checkpoint.applied_floor_krw == D("115")
    assert plan.proposed_checkpoint.baseline.day_start_equity == D("115")
    assert "PERSISTENT_HALT" in plan.points[-1].reasons


def test_recovery_cutoff_uses_exact_boundary_equity_and_stops_failed_recovery():
    start = datetime(2026, 11, 6, 21, 59, 50, tzinfo=KST)
    state, pol, context = seed(start=start, pol=policy(initial="50", activation="50", recovery=True), floor="65")
    end = datetime(2026, 11, 6, 22, tzinfo=KST)
    plan = plan_continuous_guard(state, **build(state, pol, context, ("99",), end=end))
    assert plan.proposed_checkpoint.daily_stopped
    assert plan.proposed_checkpoint.baseline.recovery_checkpoint.equity_krw == D("99")
    assert "RECOVERY_DEADLINE_BREACHED" in plan.points[-1].reasons


def test_recovery_before_cutoff_can_recover_without_erasing_daily_max_loss():
    start = datetime(2026, 11, 6, 21, 59, 50, tzinfo=KST)
    state, pol, context = seed(start=start, pol=policy(initial="50", activation="50", recovery=True), floor="65")
    end = datetime(2026, 11, 6, 22, tzinfo=KST)
    plan = plan_continuous_guard(state, **build(state, pol, context, ("99", "100"), end=end))
    assert not plan.proposed_checkpoint.daily_stopped
    assert plan.proposed_checkpoint.observed_daily_loss == D("1")
    assert plan.proposed_checkpoint.baseline.recovery_checkpoint.equity_krw == D("100")


def test_changed_owner_head_code_or_effective_limit_requires_real_timeline():
    state, pol, context = seed()
    args = build(state, pol, context)
    for change in (dict(owner_head_sha256="f"*64), dict(code_sha256="f"*64),
                   dict(signed_floor_krw=D("99")), dict(signed_daily_loss_krw=D("11"))):
        altered = args | {"owner_after": replace(args["owner_after"], **change)}
        refused(lambda: plan_continuous_guard(state, **altered), "GUARD_OWNER_TIMELINE_REQUIRED")


def test_same_owner_head_does_not_hide_a_scheduled_midnight_limit_change():
    start = datetime(2026, 11, 6, 23, 59, 50, tzinfo=KST)
    state, pol, context = seed(start=start)
    args = build(state, pol, context, end=datetime(2026, 11, 7, tzinfo=KST))
    args["owner_after"] = replace(args["owner_after"], signed_daily_loss_krw=D("20"))
    refused(lambda: plan_continuous_guard(state, **args), "GUARD_OWNER_TIMELINE_REQUIRED")


def test_owner_claim_must_exist_before_interval_and_cover_source_verification():
    state, pol, context = seed()
    args = build(state, pol, context)
    late = args | {"owner_before": replace(context, observed_at=START+timedelta(microseconds=1))}
    refused(lambda: plan_continuous_guard(state, **late), "GUARD_OWNER_INTERVAL_NOT_BRACKETED")
    early = args | {"owner_after": replace(args["owner_after"], observed_at=args["path"].end-timedelta(microseconds=1))}
    refused(lambda: plan_continuous_guard(state, **early), "GUARD_OWNER_INTERVAL_NOT_BRACKETED")


def test_coverage_request_and_account_capture_are_rebound_before_reduction():
    state, pol, context = seed()
    args = build(state, pol, context)
    changed = replace(args["account_capture"], captured_accounts=(replace(
        args["account_capture"].captured_accounts[0], opening_source_sha256="f"*64),))
    refused(lambda: plan_continuous_guard(state, **(args | {"account_capture": changed})),
            "GUARD_COVERAGE_BINDING_MISMATCH")
    refused(lambda: plan_continuous_guard(state, **(args | {"coverage": True})), "GUARD_COVERAGE_CLAIM_REQUIRED")


def test_fake_aggregate_extrema_are_rejected_by_raw_event_replay():
    state, pol, context = seed()
    args = build(state, pol, context)
    args["interval"] = replace(args["interval"], minimum_equity_krw=D("99"))
    refused(lambda: plan_continuous_guard(state, **args), "GUARD_INTERVAL_REPLAY_MISMATCH")


def test_exact_duplicate_plan_is_idempotent_but_does_not_refresh_evidence():
    state, pol, context = seed()
    args = build(state, pol, context)
    first = plan_continuous_guard(state, **args)
    repeated = plan_continuous_guard(first.proposed_checkpoint, **(args | {"now": args["now"]+timedelta(seconds=1)}))
    assert repeated.idempotent and not repeated.required_records and not repeated.points
    assert repeated.proposed_checkpoint == first.proposed_checkpoint
    refused(lambda: plan_continuous_guard(first.proposed_checkpoint,
        **(args | {"now": args["now"]+timedelta(seconds=31)})), "GUARD_OWNER_INTERVAL_NOT_BRACKETED")


def test_duplicate_with_changed_proof_claim_refuses_even_when_path_is_unchanged():
    state, pol, context = seed()
    args = build(state, pol, context)
    first = plan_continuous_guard(state, **args)
    args["coverage"] = replace(args["coverage"], source_proof_sha256="f"*64)
    args["interval"] = replace(args["interval"], coverage_sha256=content_digest((args["path"], args["coverage"])))
    refused(lambda: plan_continuous_guard(first.proposed_checkpoint, **args), "GUARD_DUPLICATE_CONTRADICTION")


def test_checkpoint_cannot_clear_halt_or_floor_without_digest_change():
    state, pol, context = seed()
    args = build(state, pol, context)
    first = plan_continuous_guard(state, **args)
    changed = replace(first.proposed_checkpoint, permanently_halted=False)
    refused(lambda: plan_continuous_guard(changed, **args), "GUARD_CHECKPOINT_CHANGED")


def test_new_profile_policy_is_not_applied_silently_to_old_guard_epoch():
    state, pol, context = seed()
    args = build(state, pol, context)
    args["policy"] = replace(pol, peak_drawdown_fraction=D("0.4"))
    refused(lambda: plan_continuous_guard(state, **args), "GUARD_AUTHORITY_EPOCH_CHANGED")


def test_explicit_anchor_refuses_missing_halt_and_daily_stop_history():
    refused(lambda: seed(equity="100", high="110", floor="110"), "GUARD_ANCHOR_HALT_HISTORY_REQUIRED")
    refused(lambda: seed(loss="10"), "GUARD_ANCHOR_DAILY_STOP_HISTORY_REQUIRED")
    state, _, _ = seed(equity="100", high="110", floor="110", halted=True)
    assert state.permanently_halted


def test_guard_is_independent_of_ambient_decimal_precision():
    state, pol, context = seed()
    args = build(state, pol, context)
    with localcontext() as numeric:
        numeric.prec = 2
        plan = plan_continuous_guard(state, **args)
    assert plan.proposed_checkpoint.high_watermark == D("115")
    assert plan.proposed_checkpoint.permanently_halted


def test_equal_equity_cannot_replace_authenticated_holding_with_half_cash_and_hide_loss():
    state, pol, context = seed(pol=policy(initial="50", activation="50"), floor="65", daily="7")
    args = build(state, pol, context, ("90", "100"))
    assert plan_continuous_guard(state, **args).proposed_checkpoint.daily_stopped
    original = args["valuation_inputs"]
    altered = replace(original, opening_cash_krw=D("50"), opening_units=(("KRW-BTC", D("0.5")),),
        historical_fills=(replace(original.historical_fills[0], quantity=D("0.5")),))
    # Raw path, coverage receipt and authenticated account rows are unchanged.
    # Their equity happens to match, but actual cash/units/FIFO history do not.
    forged = args | {"valuation_inputs": altered,
                     "interval": replace(args["interval"], minimum_equity_krw=D("95"))}
    refused(lambda: plan_continuous_guard(state, **forged), "GUARD_VALUATION_ACCOUNT_BINDING_MISMATCH")


def rebind_claims(args, *, path=None, capture=None):
    result = dict(args)
    path = args["path"] if path is None else path
    capture = args["account_capture"] if capture is None else capture
    digest = content_digest((capture.manifest_sha256, capture.captured_accounts, capture.endpoint_accounts))
    def synthetic(request, supplied_path):
        return VerifiedCoverage(request_sha256=content_digest(request), contract=COVERAGE_CONTRACT,
            authority_sha256="b"*64, source_proof_sha256="c"*64, verified_at=supplied_path.watermark_received_at)
    proof = verify_coverage(path, account_capture_sha256=digest, verifier=synthetic, now=args["now"])
    result.update(path=path, account_capture=capture, coverage=proof,
                  interval=replace(args["interval"], coverage_sha256=content_digest((path, proof))))
    return result


def test_epoch_change_and_cross_interval_sequence_gap_require_reviewed_restart():
    state, pol, context = seed()
    first = plan_continuous_guard(state, **build(state, pol, context, ("101",)))
    state = first.proposed_checkpoint
    args = build(state, pol, replace(context, observed_at=state.baseline.asof), ("102",))
    new_epoch = rebind_claims(args, path=replace(args["path"], stream_epoch="different-epoch"))
    refused(lambda: plan_continuous_guard(state, **new_epoch), "GUARD_STREAM_EPOCH_CHANGED")
    path = args["path"]
    gap = replace(path, first_sequence=path.first_sequence+1,
        events=tuple(replace(event, sequence=event.sequence+1) for event in path.events),
        watermark_sequence=path.watermark_sequence+1)
    gap_args = rebind_claims(args, path=gap)
    refused(lambda: plan_continuous_guard(state, **gap_args), "GUARD_STREAM_SEQUENCE_GAP")


def test_receipt_time_cannot_move_backwards_across_intervals():
    state, pol, context = seed()
    args = build(state, pol, context, ("101",))
    args["now"] += timedelta(seconds=10)
    first = plan_continuous_guard(state, **args)
    state = first.proposed_checkpoint
    following = build(state, pol, replace(context, observed_at=state.baseline.asof), ("102",))
    refused(lambda: plan_continuous_guard(state, **following), "GUARD_CLOCK_ROLLBACK")


def test_captured_snapshot_cannot_be_newer_than_its_coverage_verification():
    state, pol, context = seed()
    args = build(state, pol, context)
    capture = args["account_capture"]
    changed = replace(capture, captured_accounts=(replace(capture.captured_accounts[0],
        observed_at=args["now"]+timedelta(seconds=1)),))
    refused(lambda: plan_continuous_guard(state, **rebind_claims(args, capture=changed)),
            "GUARD_CAPTURE_TIME_BINDING_MISMATCH")


def test_captured_account_cannot_change_cash_history_during_boundary_reconstruction():
    state, pol, context = seed()
    args = build(state, pol, context)
    capture = args["account_capture"]
    changed = replace(capture, captured_accounts=(replace(capture.captured_accounts[0],
        opening_cash=(CashAmount(currency="KRW", amount=D("200")),)),))
    refused(lambda: plan_continuous_guard(state, **rebind_claims(args, capture=changed)),
            "GUARD_CAPTURE_ENDPOINT_CONTRADICTION")


def test_reviewed_anchor_profit_arithmetic_uses_fixed_exact_context():
    from execution_launch import continuous_guard as guard
    state, pol, context = seed()
    baseline = initialize_baseline(state.baseline.conventions, BaselineAnchor(account_scope=SCOPE,
        baseline=RiskBaseline(day_start_equity=D("100"), prior_high_watermark=D("100"),
            observed_daily_loss=D(0), approved_effective_floor=D("100"), first_trading_day=START.date(),
            asof=START, source_sha256="5"*64), equity_krw=D("100"), realized_net_total_krw=D("123.45"),
        day_open_realized_net_total_krw=D("100.01"), previous_day_realized_net_krw=None, sequence=0))
    anchor = GuardAnchor(baseline_state_sha256=baseline.state_digest, control_journal_head_sha256="6"*64,
        high_watermark=D("100"), day_start_equity=D("100"), observed_daily_loss=D(0), applied_floor_krw=D("100"),
        daily_stopped=False, permanently_halted=False, recorded_at=START, source_sha256="7"*64)
    seen, evaluate = [], guard.evaluate
    def spy(policy_value, observation, **kwargs):
        seen.append(observation.current_day_realized_net_profit)
        return evaluate(policy_value, observation, **kwargs)
    with patch.object(guard, "evaluate", spy), localcontext() as numeric:
        numeric.prec = 2
        reviewed_guard_anchor(anchor, baseline=baseline, policy=pol, owner=context)
    assert seen == [D("23.44")]


def test_late_capture_cannot_hide_longer_gap_behind_a_fresh_endpoint():
    state, pol, context = seed()
    args = build(state, pol, context, ("101",), end=START+timedelta(seconds=20))
    capture = args["account_capture"]
    late_account = replace(capture.captured_accounts[0], observed_at=START+timedelta(seconds=40))
    capture = replace(capture, captured_accounts=(late_account,))
    args = rebind_claims(args, capture=capture)
    args["coverage"] = replace(args["coverage"], verified_at=START+timedelta(seconds=40))
    args["interval"] = replace(args["interval"], coverage_sha256=content_digest((args["path"], args["coverage"])))
    args["owner_after"] = replace(args["owner_after"], observed_at=START+timedelta(seconds=40))
    args["now"] = START+timedelta(seconds=40)
    refused(lambda: plan_continuous_guard(state, **args), "GUARD_CAPTURE_TIME_BINDING_MISMATCH")
