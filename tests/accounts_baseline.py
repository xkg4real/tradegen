"""Exact baseline state transitions over invented source intervals; no live input."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal, localcontext
import json

from core.compliance.model import KST
from execution_accounts.baseline import (
    BaselineAnchor, BaselineConventions, BaselineError, BaselineInterval,
    advance_baseline, initialize_baseline, restore_state, risk_baseline, state_json,
)
from execution_accounts.model import RiskBaseline

D = Decimal
NOW = datetime(2026, 10, 25, 1, tzinfo=timezone.utc)
SHA = "a" * 64


def fixture(now=NOW, *, first=False):
    day = now.astimezone(KST).date()
    base = RiskBaseline(day_start_equity=D("1000"), prior_high_watermark=D("1100"),
        observed_daily_loss=D("100"), approved_effective_floor=D("700"),
        first_trading_day=day if first else day-timedelta(days=3), asof=now, source_sha256=SHA)
    anchor = BaselineAnchor(account_scope="baseline-fixture", baseline=base, equity_krw=D("900"),
        realized_net_total_krw=D("80"), day_open_realized_net_total_krw=D("100"),
        previous_day_realized_net_krw=None if first else D("10"), sequence=7)
    conventions = BaselineConventions(daily_loss="maximum_net_equity_loss_from_day_open",
        external_flows="no_external_flows", max_interval_seconds=30)
    return initialize_baseline(conventions, anchor)


def interval(state, **changes):
    values = dict(account_scope=state.account_scope, sequence=state.sequence+1,
        previous_state_digest=state.state_digest, start=state.asof, end=state.asof+timedelta(seconds=10),
        equity_krw=state.equity_krw, minimum_equity_krw=state.equity_krw,
        maximum_equity_krw=state.equity_krw, realized_net_total_krw=state.realized_net_total_krw,
        gross_external_inflows_krw=D("0"), gross_external_outflows_krw=D("0"),
        source_sha256="b"*64, coverage_sha256="c"*64)
    return BaselineInterval(**(values | changes))


def refuses(call, code):
    try:
        call()
    except BaselineError as exc:
        assert str(exc) == code, (str(exc), code)
    else:
        raise AssertionError("expected baseline refusal")


def test_baseline_export_preserves_first_day_approved_floor_and_actual_timestamp():
    state = fixture()
    result = risk_baseline(state, now=state.asof+timedelta(seconds=5), expected_head=state.state_digest)
    assert result.asof == state.asof
    assert result.first_trading_day == state.first_trading_day
    assert result.prior_high_watermark == D("1100") and result.day_start_equity == D("1000")
    assert result.observed_daily_loss == D("100") and result.approved_effective_floor == D("700")
    assert result.source_sha256 == state.state_digest


def test_interval_peak_and_trough_are_not_inferred_from_recovered_endpoints():
    start = fixture()
    first = advance_baseline(start, interval(start, equity_krw=D("950"),
        minimum_equity_krw=D("800"), maximum_equity_krw=D("1200")))
    assert first.observed_daily_loss == D("200") and first.high_watermark == D("1200")
    recovered = advance_baseline(first, interval(first, equity_krw=D("1100"),
        minimum_equity_krw=D("950"), maximum_equity_krw=D("1100")))
    assert recovered.observed_daily_loss == D("200")
    assert recovered.day_start_equity == D("1000") and recovered.high_watermark == D("1200")
    assert recovered.first_trading_day == start.first_trading_day
    assert start.equity_krw == D("900")  # The earlier checkpoint is immutable.


def test_unknown_gross_and_offsetting_external_flows_are_refused():
    state = fixture()
    for changes in ({"gross_external_inflows_krw": None}, {"gross_external_outflows_krw": None}):
        refuses(lambda: advance_baseline(state, interval(state, **changes)),
                "BASELINE_EXTERNAL_FLOW_COVERAGE_REQUIRED")
    for incoming, outgoing in ((D("1"), D("0")), (D("0"), D("1")), (D("1"), D("1"))):
        refuses(lambda: advance_baseline(state, interval(state, gross_external_inflows_krw=incoming,
                gross_external_outflows_krw=outgoing)), "BASELINE_EXTERNAL_FLOW_UNSUPPORTED")


def test_incomplete_time_windows_and_sequence_or_digest_rollbacks_refuse():
    state = fixture()
    for changes in ({"start": state.asof+timedelta(seconds=1)}, {"end": state.asof},
                    {"end": state.asof+timedelta(seconds=31)}):
        refuses(lambda: advance_baseline(state, interval(state, **changes)), "BASELINE_TIME_GAP_OR_ROLLBACK")
    for changes in ({"sequence": state.sequence+2}, {"sequence": state.sequence-1},
                    {"previous_state_digest": "d"*64}):
        refuses(lambda: advance_baseline(state, interval(state, **changes)), "BASELINE_CHAIN_GAP_OR_ROLLBACK")
    refuses(lambda: advance_baseline(state, interval(state, account_scope="other")), "BASELINE_SCOPE_MISMATCH")
    refuses(lambda: advance_baseline(state, interval(state, coverage_sha256="")), "BASELINE_DIGEST_REQUIRED")


def test_identical_redelivery_is_idempotent_and_changed_duplicate_is_rejected():
    start = fixture(); sample = interval(start)
    state = advance_baseline(start, sample)
    assert advance_baseline(state, sample) is state
    refuses(lambda: advance_baseline(state, replace(sample, source_sha256="f"*64)),
            "BASELINE_DUPLICATE_CONTRADICTION")
    refuses(lambda: risk_baseline(state, now=state.asof+timedelta(seconds=31), expected_head=state.state_digest),
            "BASELINE_STALE_OR_FUTURE")


def test_interval_extrema_must_bound_both_snapshots_without_rounding():
    state = fixture()
    for changes in ({"minimum_equity_krw": D("901")}, {"maximum_equity_krw": D("899")},
                    {"equity_krw": D("1200"), "maximum_equity_krw": D("1199")}):
        refuses(lambda: advance_baseline(state, interval(state, **changes)),
                "BASELINE_INTERVAL_EXTREMA_CONTRADICTION")


def test_midnight_requires_an_exact_opening_snapshot_and_keeps_lifetime_peak():
    midnight = datetime(2026, 10, 26, tzinfo=KST)
    state = fixture(midnight-timedelta(seconds=10))
    refuses(lambda: advance_baseline(state, interval(state, end=midnight+timedelta(seconds=1))),
            "BASELINE_MIDNIGHT_OPENING_REQUIRED")
    opening = advance_baseline(state, interval(state, end=midnight, equity_krw=D("880"),
        minimum_equity_krw=D("850"), maximum_equity_krw=D("1150"), realized_net_total_krw=D("70")))
    assert opening.day_start_equity == D("880") and opening.observed_daily_loss == 0
    assert opening.high_watermark == D("1150") and opening.previous_day_realized_net_krw == D("-30")
    assert opening.first_trading_day == state.first_trading_day
    after = advance_baseline(opening, interval(opening, equity_krw=D("870"), minimum_equity_krw=D("865")))
    assert after.observed_daily_loss == D("15") and after.day_start_equity == D("880")
    assert after.previous_day_realized_net_krw == D("-30")


def test_first_day_exception_does_not_restart_after_seoul_rollover_or_restore():
    midnight = datetime(2026, 10, 26, tzinfo=KST)
    original = fixture(midnight-timedelta(seconds=10), first=True)
    assert original.previous_day_realized_net_krw is None
    second = advance_baseline(original, interval(original, end=midnight))
    restored = restore_state(state_json(second), expected_head=second.state_digest)
    assert restored == second and restored.first_trading_day == original.first_trading_day
    assert restored.previous_day_realized_net_krw == D("-20")
    assert restored.first_trading_day != restored.asof.astimezone(KST).date()


def test_checkpoint_roundtrip_requires_separately_retained_expected_head():
    before = fixture(); after = advance_baseline(before, interval(before))
    assert restore_state(state_json(after), expected_head=after.state_digest) == after
    refuses(lambda: restore_state(state_json(before), expected_head=after.state_digest), "BASELINE_CHECKPOINT_MISMATCH")
    refuses(lambda: risk_baseline(before, now=before.asof, expected_head=after.state_digest), "BASELINE_CHECKPOINT_MISMATCH")
    body = json.loads(state_json(after)); body["first_trading_day"] = "2026-10-24"
    refuses(lambda: restore_state(json.dumps(body), expected_head=after.state_digest), "BASELINE_STATE_CHANGED")


def test_freshness_never_crosses_seoul_day_even_within_thirty_seconds():
    midnight = datetime(2026, 10, 26, tzinfo=KST)
    state = fixture(midnight-timedelta(seconds=1))
    for now in (midnight, state.asof-timedelta(seconds=1)):
        refuses(lambda: risk_baseline(state, now=now, expected_head=state.state_digest), "BASELINE_STALE_OR_FUTURE")


def test_unknown_conventions_and_mutated_state_do_not_get_reinterpreted():
    state = fixture()
    for conventions in (replace(state.conventions, daily_loss="unspecified"),
                        replace(state.conventions, external_flows="additive_cashflow")):
        bad = replace(state, conventions=conventions)
        code = "BASELINE_DAILY_LOSS_CONVENTION_UNSUPPORTED" if conventions.daily_loss == "unspecified" else "BASELINE_FLOW_CONVENTION_UNSUPPORTED"
        refuses(lambda: advance_baseline(bad, interval(state)), code)
    refuses(lambda: advance_baseline(replace(state, observed_daily_loss=D("99")), interval(state)),
            "BASELINE_DAILY_LOSS_CONTRADICTION")
    refuses(lambda: advance_baseline(replace(state, equity_krw=D("901")), interval(state)), "BASELINE_STATE_CHANGED")


def test_numeric_types_nonfinite_and_ambient_decimal_precision_cannot_change_accounting():
    state = fixture()
    for bad in (0.1, True, D("NaN"), D("Infinity")):
        refuses(lambda: advance_baseline(state, interval(state, equity_krw=bad)), "BASELINE_EXACT_DECIMAL_REQUIRED")
    sample = interval(state, equity_krw=D("900.1234567890123456789"),
        minimum_equity_krw=D("899.0000000000000000001"), maximum_equity_krw=D("901.1234567890123456789"))
    normal = advance_baseline(state, sample)
    with localcontext() as numeric:
        numeric.prec = 3
        small = advance_baseline(state, sample)
        assert small == normal
        assert restore_state(state_json(small), expected_head=small.state_digest) == normal
    assert normal.observed_daily_loss == D("100.9999999999999999999")


def test_malformed_checkpoint_json_cannot_smuggle_numbers_fields_or_duplicate_values():
    state = fixture(); raw = state_json(state)
    refuses(lambda: restore_state(raw[:-1]+',"schema_version":1}', expected_head=state.state_digest),
            "BASELINE_DUPLICATE_JSON_KEY")
    body = json.loads(raw); body["equity_krw"] = 900
    refuses(lambda: restore_state(json.dumps(body), expected_head=state.state_digest), "BASELINE_CHECKPOINT_NUMBER_INVALID")
    body = json.loads(raw); body["approval"] = True
    refuses(lambda: restore_state(json.dumps(body), expected_head=state.state_digest), "BASELINE_CHECKPOINT_SCHEMA_INVALID")
    refuses(lambda: restore_state(b"x"*65537, expected_head=state.state_digest), "BASELINE_CHECKPOINT_TOO_LARGE")


def test_exported_baseline_fits_existing_provider_without_implying_trade_permission():
    from tests.accounts_provider import bundle
    from execution_accounts.provider import build_observation
    sample = bundle(now=NOW, opening=D("900"))
    state = fixture()
    baseline = risk_baseline(state, now=NOW, expected_head=state.state_digest)
    observed = build_observation(replace(sample, risk_baseline=baseline), now=NOW)
    assert observed.risk.equity == state.equity_krw
    assert observed.risk.prior_high_watermark == state.high_watermark
    assert observed.risk.observed_daily_loss == state.observed_daily_loss
