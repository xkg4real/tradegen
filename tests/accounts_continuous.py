"""Synthetic continuous-path tests; no real feed, key, owner state or order call.

The verifier below is explicitly a TEST double. Its acceptance does not establish
that an Upbit production coverage authority exists.
"""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal, localcontext
import gc
from pathlib import Path
from unittest.mock import patch
import weakref

from execution_accounts.continuous import (
    COVERAGE_CONTRACT, ContinuousEvidenceError, ContinuousPath, ContinuousPriceRecorder,
    EquityEvent, PriceMark, VerifiedCoverage, archive_candidate, validate_path, value_path, verify_coverage,
)
from execution_accounts.baseline_bridge import ContinuousAccountProvider, advance_account_baseline
from execution_accounts.model import content_digest
from execution_accounts.provider import build_observation
from execution_launch.account_interval import (
    ContinuousUpbitCandidateSource, ContinuousCapture, preview_continuous_upbit_interval, upbit_interval_frame,
)
from execution_launch import account_interval as AI
from tests import compliance_fixtures as F
from tests.launch_account_interval import (
    ANCHOR, BUY, COVERAGE, FakeClock, FakeUpbit, SCOPE, at, order, series,
)

D = Decimal
START = at(26, 20)


def refused(call, code):
    try:
        call()
    except ValueError as exc:
        assert str(exc) == code, (str(exc), code)
        return
    raise AssertionError("expected " + code)


def mark(price, when=START, symbol="KRW-BTC"):
    return PriceMark(symbol=symbol, price=D(price), asof=when)


def mark_event(sequence, price, when, *, symbol="KRW-BTC"):
    return EquityEvent(sequence=sequence, at=when, received_at=when, source_sha256="e"*64,
                       mark=mark(price, when, symbol))


def fill_event(sequence, fill):
    return EquityEvent(sequence=sequence, at=fill.executed_at, received_at=fill.executed_at,
                       source_sha256="f"*64, fill=fill)


def candidate(previous, end, *, opening="10050", events=(), received=None):
    return ContinuousPath(account_scope=SCOPE, stream_epoch="synthetic-epoch-1",
        previous_state_digest=previous.state_digest, start=previous.asof, end=end,
        opening_marks=(mark(opening, previous.asof),), first_sequence=10, events=tuple(events),
        watermark_sequence=10+len(events), watermark_received_at=received or end,
        watermark_source_sha256="a"*64)


def synthetic_verifier(request, path):
    """An explicit invented source authority, never imported by production code."""
    return VerifiedCoverage(request_sha256=content_digest(request), contract=COVERAGE_CONTRACT,
        authority_sha256="b"*64, source_proof_sha256="c"*64, verified_at=path.watermark_received_at)


def held_series(start=START, **kwargs):
    return series(start, exchange=FakeUpbit(cash="89995", btc="1", orders=(BUY,), ticker="10050"),
                  fees=(), realized=D(0), loss=D(0), **kwargs)


def build(previous, collection, path, *, verifier=synthetic_verifier):
    return preview_continuous_upbit_interval(previous, collection, path, coverage_verifier=verifier,
                                          now=path.watermark_received_at)


def test_held_path_records_hidden_drawdown_and_peak_despite_equal_endpoints():
    with held_series() as env:
        collection = env.capture(START+timedelta(seconds=5))
        events = (mark_event(10, "9900", START+timedelta(seconds=1)),
                  mark_event(11, "10200", START+timedelta(seconds=2)),
                  mark_event(12, "10050", START+timedelta(seconds=3)))
        path = candidate(env.state, collection.bundle.accounts[0].observed_at, events=events)
        frame = build(env.state, collection, path)
        assert frame.interval.equity_krw == env.state.equity_krw == D("100045")
        assert frame.interval.minimum_equity_krw == D("99895")
        assert frame.interval.maximum_equity_krw == D("100195")
        update = advance_account_baseline(env.state, frame.interval, frame.accounts, now=path.end)
        assert update.state.high_watermark == D("100195")
        assert update.state.observed_daily_loss == D("105")


def test_default_flat_producer_still_refuses_held_inventory():
    with held_series() as env:
        collection = env.capture(START+timedelta(seconds=5))
        refused(lambda: upbit_interval_frame(env.state, collection), "ACCOUNT_INTERVAL_EXTREMA_EVIDENCE_REQUIRED")


def test_fill_fee_and_roundtrip_valley_are_not_erased_by_flat_endpoint():
    with series(START, exchange=FakeUpbit(cash="100000", orders=()), fees=(), realized=D(0),
                high=D("100000"), loss=D(0)) as env:
        buy = order("buy-new", "bid", START+timedelta(seconds=1), "10000",
                    [("fill-buy-new", "1", "10000")], paid_fee="5")
        sell = order("sell-new", "ask", START+timedelta(seconds=4), "10010",
                     [("fill-sell-new", "1", "10010")], paid_fee="5")
        collection = env.capture(START+timedelta(seconds=5), exchange=FakeUpbit(cash="100000", orders=(buy, sell)))
        fills = build_observation(collection.bundle, now=collection.bundle.accounts[0].observed_at).fills
        events = (fill_event(10, fills[0]), mark_event(11, "9900", START+timedelta(seconds=2)),
                  mark_event(12, "10010", START+timedelta(seconds=3)), fill_event(13, fills[1]))
        path = candidate(env.state, collection.bundle.accounts[0].observed_at, opening="10000", events=events)
        frame = build(env.state, collection, path)
        assert frame.interval.equity_krw == D("100000")
        assert frame.interval.minimum_equity_krw == D("99895")
        assert frame.interval.maximum_equity_krw == D("100005")
        assert frame.interval.realized_net_total_krw == D(0)


def test_first_buy_uses_fee_and_last_known_mark_and_reconciles_positions():
    with series(START, exchange=FakeUpbit(cash="100000", orders=()), fees=(), realized=D(0),
                high=D("100000"), loss=D(0)) as env:
        buy = order("buy-new", "bid", START+timedelta(seconds=1), "10000",
                    [("fill-buy-new", "1", "10000")], paid_fee="5")
        collection = env.capture(START+timedelta(seconds=5),
                                 exchange=FakeUpbit(cash="89995", btc="1", orders=(buy,), ticker="10000"))
        fills = build_observation(collection.bundle, now=collection.bundle.accounts[0].observed_at).fills
        path = candidate(env.state, collection.bundle.accounts[0].observed_at, opening="10000",
                         events=(fill_event(10, fills[0]),))
        frame = build(env.state, collection, path)
        assert frame.interval.equity_krw == frame.interval.minimum_equity_krw == D("99995")
        assert frame.interval.maximum_equity_krw == D("100000")


def test_missing_fill_is_refused_even_when_candidate_hash_is_valid():
    with series(START, exchange=FakeUpbit(cash="100000", orders=()), fees=(), realized=D(0),
                high=D("100000"), loss=D(0)) as env:
        buy = order("buy-new", "bid", START+timedelta(seconds=1), "10000",
                    [("fill-buy-new", "1", "10000")], paid_fee="5")
        collection = env.capture(START+timedelta(seconds=5),
                                 exchange=FakeUpbit(cash="89995", btc="1", orders=(buy,), ticker="10000"))
        path = candidate(env.state, collection.bundle.accounts[0].observed_at, opening="10000")
        refused(lambda: build(env.state, collection, path), "CONTINUOUS_FILL_COVERAGE_MISMATCH")


def test_candidate_without_independent_verifier_or_with_boolean_proof_refuses():
    with held_series() as env:
        collection = env.capture(START+timedelta(seconds=5))
        path = candidate(env.state, collection.bundle.accounts[0].observed_at)
        refused(lambda: build(env.state, collection, path, verifier=None), "CONTINUOUS_COVERAGE_VERIFIER_REQUIRED")
        for result in (True, {"complete": True}, content_digest(path)):
            refused(lambda: build(env.state, collection, path, verifier=lambda *args: result),
                    "CONTINUOUS_VERIFIED_COVERAGE_REQUIRED")


def test_verifier_receipt_cannot_be_reused_for_another_path_or_capture():
    with held_series() as env:
        collection = env.capture(START+timedelta(seconds=5))
        path = candidate(env.state, collection.bundle.accounts[0].observed_at)
        proof = verify_coverage(path, account_capture_sha256="d"*64, verifier=synthetic_verifier, now=path.end)
        refused(lambda: build(env.state, collection, path, verifier=lambda *args: proof),
                "CONTINUOUS_COVERAGE_BINDING_MISMATCH")


def test_verifier_exceptions_are_redacted_and_never_fall_back_to_flat():
    with held_series() as env:
        collection = env.capture(START+timedelta(seconds=5))
        path = candidate(env.state, collection.bundle.accounts[0].observed_at)
        def bad(*args):
            raise RuntimeError("private balance and account text must not leak")
        refused(lambda: build(env.state, collection, path, verifier=bad), "CONTINUOUS_COVERAGE_VERIFICATION_FAILED")


def test_ending_at_2200_captures_actual_recovery_value_from_path():
    start = at(26, 21, 59, 40)
    with held_series(start) as env:
        env.exchange.ticker = "10080"
        collection = env.capture(at(26, 22))
        path = candidate(env.state, at(26, 22), events=(mark_event(10, "10080", start+timedelta(seconds=15)),))
        frame = build(env.state, collection, path)
        update = advance_account_baseline(env.state, frame.interval, frame.accounts, now=path.end)
        assert update.state.recovery_checkpoint.cutoff_at == at(26, 22)
        assert update.state.recovery_checkpoint.equity_krw == D("100075")


def test_bracketed_boundary_reconstructs_price_instead_of_backdating_later_ticker():
    start = at(26, 21, 59, 40)
    with held_series(start) as env:
        # At 200 ms per clock call the ticker reply is after 22:00.
        env.exchange.ticker = "10300"
        collection = env.capture(at(26, 21, 59, 59), step_ms=200)
        observed = collection.bundle.accounts[0].observed_at
        assert collection.bundle.accounts[0].positions[0].asof > at(26, 22)
        path = candidate(env.state, at(26, 22), received=observed,
                         events=(mark_event(10, "10080", start+timedelta(seconds=15)),))
        frame = build(env.state, collection, path)
        assert frame.interval.end == at(26, 22)
        assert frame.accounts[0].positions[0].price == D("10080")
        assert frame.accounts[0].positions[0].asof == at(26, 22)
        assert collection.bundle.accounts[0].positions[0].price == D("10300")
        assert frame.interval.equity_krw == D("100075")


def test_late_boundary_is_never_relabelled():
    start = at(26, 21, 59, 40)
    with held_series(start) as env:
        collection = env.capture(at(26, 22, 0, 1))
        path = candidate(env.state, at(26, 22), received=collection.bundle.accounts[0].observed_at)
        refused(lambda: build(env.state, collection, path), "ACCOUNT_INTERVAL_BOUNDARY_MISSED")


def test_half_open_interval_refuses_event_exactly_at_end():
    with held_series() as env:
        end = START+timedelta(seconds=5)
        path = candidate(env.state, end, events=(mark_event(10, "10050", end),))
        refused(lambda: validate_path(path), "CONTINUOUS_HALF_OPEN_BOUNDARY_REQUIRED")


def test_recorder_gap_is_sticky_and_cannot_be_healed_by_later_rows():
    recorder = ContinuousPriceRecorder(account_scope=SCOPE, stream_epoch="epoch", previous_state_digest="a"*64,
        start=START, opening_marks=(mark("10050"),), first_sequence=10)
    refused(lambda: recorder.append(mark_event(11, "10050", START+timedelta(seconds=1))),
            "CONTINUOUS_EVENT_REFUSED")
    refused(lambda: recorder.append(mark_event(10, "10050", START+timedelta(seconds=1))),
            "CONTINUOUS_EPOCH_BROKEN")
    refused(lambda: recorder.seal(end=START+timedelta(seconds=5), watermark_sequence=10,
        watermark_received_at=START+timedelta(seconds=5), watermark_source_sha256="e"*64), "CONTINUOUS_EPOCH_BROKEN")


def test_recorder_duplicates_are_idempotent_and_changed_duplicate_breaks_epoch():
    recorder = ContinuousPriceRecorder(account_scope=SCOPE, stream_epoch="epoch", previous_state_digest="a"*64,
        start=START, opening_marks=(mark("10050"),), first_sequence=10)
    event = mark_event(10, "10000", START+timedelta(seconds=1))
    recorder.append(event); recorder.append(event)
    refused(lambda: recorder.append(replace(event, mark=mark("9999", event.at))), "CONTINUOUS_EVENT_REFUSED")
    refused(lambda: recorder.append(mark_event(11, "10050", START+timedelta(seconds=2))), "CONTINUOUS_EPOCH_BROKEN")


def test_disconnect_is_sticky_and_new_recorder_does_not_adopt_old_epoch():
    recorder = ContinuousPriceRecorder(account_scope=SCOPE, stream_epoch="epoch", previous_state_digest="a"*64,
        start=START, opening_marks=(mark("10050"),), first_sequence=10)
    recorder.disconnect()
    refused(lambda: recorder.append(mark_event(10, "10050", START+timedelta(seconds=1))), "CONTINUOUS_EPOCH_BROKEN")
    assert not hasattr(recorder, "resume") and not hasattr(recorder, "reset")


def test_recorder_seal_checks_watermark_and_cannot_append_after_seal():
    recorder = ContinuousPriceRecorder(account_scope=SCOPE, stream_epoch="epoch", previous_state_digest="a"*64,
        start=START, opening_marks=(mark("10050"),), first_sequence=10)
    recorder.append(mark_event(10, "10000", START+timedelta(seconds=1)))
    end = START+timedelta(seconds=5)
    path = recorder.seal(end=end, watermark_sequence=11, watermark_received_at=end, watermark_source_sha256="e"*64)
    assert len(path.events) == 1
    refused(lambda: recorder.append(mark_event(11, "10050", START+timedelta(seconds=2))), "CONTINUOUS_EPOCH_SEALED")


def test_path_refuses_sequence_gap_future_time_and_long_duration():
    with held_series() as env:
        path = candidate(env.state, START+timedelta(seconds=5),
                         events=(mark_event(10, "10050", START+timedelta(seconds=1)),))
        refused(lambda: validate_path(replace(path, watermark_sequence=20)), "CONTINUOUS_SEQUENCE_GAP")
        future = replace(path.events[0], received_at=START)
        refused(lambda: validate_path(replace(path, events=(future,))), "CONTINUOUS_TIME_GAP_OR_ROLLBACK")
        refused(lambda: validate_path(replace(path, end=START+timedelta(seconds=31),
            watermark_received_at=START+timedelta(seconds=31))), "CONTINUOUS_TIME_GAP_OR_ROLLBACK")


def test_endpoint_mark_contradiction_refuses_even_with_permissive_test_verifier():
    with held_series() as env:
        collection = env.capture(START+timedelta(seconds=5))
        path = candidate(env.state, collection.bundle.accounts[0].observed_at,
                         events=(mark_event(10, "10200", START+timedelta(seconds=1)),))
        refused(lambda: build(env.state, collection, path), "ACCOUNT_INTERVAL_CLOSING_MARK_MISMATCH")


def test_private_archive_is_idempotent_and_tampered_record_refuses():
    with held_series() as env:
        path = candidate(env.state, START+timedelta(seconds=5))
        value = archive_candidate(path, root=env.home)
        assert archive_candidate(path, root=env.home) == value == content_digest(path)
        target = env.home / "execution-price-paths" / (value+".json")
        target.write_bytes(b"partial record")
        refused(lambda: archive_candidate(path, root=env.home), "CONTINUOUS_ARCHIVE_CHANGED")


def test_private_archive_refuses_outside_root_and_file_links():
    with held_series() as env:
        path = candidate(env.state, START+timedelta(seconds=5))
        refused(lambda: archive_candidate(path, root=env.home/"another-root"), "CONTINUOUS_ARCHIVE_ROOT_MISMATCH")
        value = content_digest(path)
        directory = env.home / "execution-price-paths"
        directory.mkdir()
        outside = env.home / "outside"
        outside.write_text("do not touch")
        target = directory / (value+".json")
        # Hardlinks work without elevated Windows symlink privileges.
        target.hardlink_to(outside)
        refused(lambda: archive_candidate(path, root=env.home), "CONTINUOUS_ARCHIVE_PATH_REFUSED")
        assert outside.read_text() == "do not touch"


def test_integrated_source_archives_and_redelivers_then_invalidates_failed_prefetch():
    with held_series() as env:
        def path_source(previous, collection, end):
            return candidate(previous, end, received=collection.observed_at)
        source = ContinuousUpbitCandidateSource(path_source=path_source, coverage_verifier=synthetic_verifier,
                                               archive_root=env.home)
        clock = FakeClock(START+timedelta(seconds=5))
        env.exchange.clock = clock
        staged = source.collect(env.exchange, previous=env.state, anchor=ANCHOR, coverage=COVERAGE,
                                 clock=clock, trade_fees=())
        assert source.latest() == staged
        refused(lambda: source(env.state, staged.observed_at), "CONTINUOUS_LIVE_RISK_INTEGRATION_REQUIRED")
        assert len(list((env.home/"execution-price-paths").glob("*.json"))) == 1
        # A failed collection must not leave the previous valid staged frame available.
        env.exchange.account_scope = "wrong-scope"
        refused(lambda: source.collect(env.exchange, previous=env.state, anchor=ANCHOR, coverage=COVERAGE,
                                       clock=clock), "ACCOUNT_INTERVAL_SCOPE_MISMATCH")
        refused(source.latest, "ACCOUNT_INTERVAL_PREFETCH_REQUIRED")


def test_midnight_path_rolls_day_counters_without_resetting_high_watermark():
    start = at(27, 23, 59, 40)
    with held_series(start, day_start=D("100045"), previous=D(0)) as env:
        def path_source(previous, collection, end):
            return candidate(previous, end, received=collection.observed_at,
                             events=(mark_event(10, "10080", start+timedelta(seconds=15)),))
        source = ContinuousUpbitCandidateSource(path_source=path_source, coverage_verifier=synthetic_verifier,
                                               archive_root=env.home)
        env.exchange.ticker = "10300"
        env.exchange.clock = clock = FakeClock(at(27, 23, 59, 59), 200)
        staged = source.collect(env.exchange, previous=env.state, anchor=ANCHOR, coverage=COVERAGE,
                                 clock=clock, trade_fees=())
        update = advance_account_baseline(env.state, staged.preview.interval, staged.preview.accounts,
                                          now=staged.observed_at)
        assert update.state.asof == at(28, 0)
        assert update.state.day_start_equity == D("100075")
        assert update.state.high_watermark == env.state.high_watermark == D("100100")
        assert update.state.previous_day_realized_net_krw == 0
        assert update.state.observed_daily_loss == 0


def test_exact_decimal_context_is_independent_of_ambient_rounding():
    with held_series() as env:
        collection = env.capture(START+timedelta(seconds=5))
        path = candidate(env.state, collection.bundle.accounts[0].observed_at)
        with localcontext() as numeric:
            numeric.prec = 3
            frame = build(env.state, collection, path)
        assert frame.interval.equity_krw == D("100045")


def test_source_never_publishes_or_archives_unverified_evidence():
    with held_series() as env:
        source = ContinuousUpbitCandidateSource(
            path_source=lambda previous, collection, end: candidate(previous, end),
            coverage_verifier=lambda *args: True, archive_root=env.home)
        env.exchange.clock = clock = FakeClock(START+timedelta(seconds=5))
        refused(lambda: source.collect(env.exchange, previous=env.state, anchor=ANCHOR, coverage=COVERAGE,
                                       clock=clock, trade_fees=()), "CONTINUOUS_VERIFIED_COVERAGE_REQUIRED")
        assert not (env.home/"execution-price-paths").exists()
        refused(source.latest, "ACCOUNT_INTERVAL_PREFETCH_REQUIRED")
        refused(lambda: source(env.state, START+timedelta(seconds=5)), "CONTINUOUS_LIVE_RISK_INTEGRATION_REQUIRED")


def test_chronological_peak_drop_recovery_remains_visible_and_cannot_advance_live_head():
    with held_series() as env:
        env.exchange.ticker = "11550"
        collection = env.capture(START+timedelta(seconds=5))
        path = candidate(env.state, collection.bundle.accounts[0].observed_at, events=(
            mark_event(10, "11050", START+timedelta(seconds=1)),
            mark_event(11, "10550", START+timedelta(seconds=2)),
            mark_event(12, "11550", START+timedelta(seconds=3))))
        preview = build(env.state, collection, path)
        assert tuple(point.equity_krw for point in preview.valuation.points) == tuple(map(D,
            ("100045", "101045", "100545", "101545", "101545")))
        assert preview.interval.minimum_equity_krw == env.state.equity_krw
        assert preview.interval.maximum_equity_krw == preview.interval.equity_krw
        # Aggregates alone hide the middle peak->drop. The candidate must not
        # enter ContinuousAccountProvider even with a synthetic coverage receipt.
        assert preview.execution_ready is False
        provider = ContinuousAccountProvider(source=lambda *args: preview, store=env.store, trusted_head=env.head)
        refused(lambda: provider(path.end), "BASELINE_PROVIDER_FRAME_REQUIRED")
        assert env.current() == env.state and not env.head.commits


def test_candidate_capture_does_not_export_temporary_midnight_baseline():
    start = at(27, 23, 59, 40)
    with held_series(start, day_start=D("100045"), previous=D(0)) as env:
        refs = []
        original = AI.collect_upbit
        def spy(*args, **kwargs):
            refs.append(weakref.ref(kwargs["risk_baseline"]))
            return original(*args, **kwargs)
        def paths(previous, capture, end):
            assert type(capture) is ContinuousCapture
            assert not hasattr(capture, "bundle") and not hasattr(capture, "risk_baseline")
            return candidate(previous, end, received=capture.observed_at, events=(
                mark_event(10, "9900", start+timedelta(seconds=5)),
                mark_event(11, "10080", start+timedelta(seconds=15))))
        source = ContinuousUpbitCandidateSource(path_source=paths, coverage_verifier=synthetic_verifier,
                                               archive_root=env.home)
        env.exchange.ticker = "10300"
        env.exchange.clock = clock = FakeClock(at(27, 23, 59, 59), 200)
        with patch.object(AI, "collect_upbit", spy):
            staged = source.collect(env.exchange, previous=env.state, anchor=ANCHOR, coverage=COVERAGE,
                                     clock=clock, trade_fees=())
        gc.collect()
        assert len(refs) == 1 and refs[0]() is None
        assert min(point.equity_krw for point in staged.preview.valuation.points) == D("99895")
        assert staged.preview.interval.end == at(28, 0)
        refused(lambda: source(env.state, staged.observed_at), "CONTINUOUS_LIVE_RISK_INTEGRATION_REQUIRED")
        assert not env.head.commits
