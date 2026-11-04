"""Invented marks and source receipts; no live study, network or authorization."""
from dataclasses import asdict, replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal, localcontext
import hashlib
import json

from execution_accounts.collector import SourceReceipt
from execution_accounts.quotes import parse_orderbook
from execution_control.model import InstrumentRules
from execution_launch.paper_capture import (
    CaptureArchive, CaptureError, PaperCapture, capture_json, parse_replay_input,
    replay_capture, sample_prefetched_book,
)
from execution_launch.profile import rule_terms_digest
from execution_launch.program import (
    ProgramError, ProgramSpec, parameters_json, parse_program, program_digest,
    program_json, target_fraction,
)
from execution_launch.runner import StrategyDriver, program_digest as runner_program_digest
from execution_launch.strategy import (
    EVALUATOR_REVISION, ForwardProtocol, PaperBar, assess_strategy,
    evaluate_capture_json, evidence_digest, register_protocol,
)

D = Decimal
START = datetime(2031, 1, 1, tzinfo=timezone.utc)
PROGRAM_ARTIFACT = b"invented program artifact for offline fixture only"
CAPTURE_ARTIFACT = b"invented capture source artifact for offline fixture only"


def fixture():
    program = ProgramSpec(schema_version=1, strategy_id="fixture-trend-v1",
        kind="moving_average_trend", fast_window=2, slow_window=4, exposure_fraction=D("0.5"))
    rules = InstrumentRules(venue="upbit", market="spot", symbol="KRW-BTC", lot_size=D("0.01"),
        tick_size=D("1"), min_quantity=D("0.01"), min_notional_krw=D("1"), fee_fraction=D("0.001"),
        asof=START, source_digest="a"*64)
    protocol = ForwardProtocol(schema_version=1, study_id="fixture-capture-v1", strategy_id=program.strategy_id,
        strategy_code_sha256=program_digest(program, PROGRAM_ARTIFACT), capture_source_id="fixture-source",
        capture_source_code_sha256=hashlib.sha256(CAPTURE_ARTIFACT).hexdigest(),
        evaluator_revision=EVALUATOR_REVISION, profile_contract_digest="b"*64,
        rule_terms_digest=rule_terms_digest(rules), venue="upbit", market="spot", symbol="KRW-BTC",
        quote_currency="KRW", preregistered_at=START-timedelta(days=1), capture_start=START,
        capture_end=START+timedelta(hours=1), initial_cash_quote=D("10000"), fee_fraction=D("0.001"),
        slippage_bps=D("0"), bar_seconds=60, minimum_fill_delay_seconds=1, minimum_observations=60,
        minimum_roundtrips=20, block_length=5, bootstrap_replications=999,
        family_members=(program.strategy_id,), alpha=D("0.05"), max_drawdown=D("0.2"),
        review_max_age_seconds=3600, seed=83)
    bars = tuple(PaperBar(observed_at=START+timedelta(minutes=i),
        received_at=START+timedelta(minutes=i,seconds=1), bid=D(100+i%10), ask=D(102+i%10),
        mark=D(101+i%10), quote_krw=D(1), source_sha256=evidence_digest(("invented-row",i))) for i in range(61))
    return program, protocol, register_protocol(protocol), bars, rules


def playback(program, protocol, registry, bars, **changes):
    args = dict(program_artifact=PROGRAM_ARTIFACT, capture_source_artifact=CAPTURE_ARTIFACT,
                source_kind="synthetic", now=bars[-1].received_at)
    return replay_capture(protocol, registry, program, bars, **(args | changes))


def reject(call, code=None):
    try:
        call()
    except ValueError as exc:
        if code is not None:
            assert str(exc) == code, (str(exc), code)
        return
    raise AssertionError("expected refusal")


def recorder(program, protocol, registry):
    clock = [START-timedelta(seconds=1)]
    capture = PaperCapture(protocol, registry, program, program_artifact=PROGRAM_ARTIFACT,
        capture_source_artifact=CAPTURE_ARTIFACT, clock=lambda:clock[0])
    return capture, clock


def book(slot=START, *, symbol="KRW-BTC", received_delta=-1, asof_delta=-2, bid=100, ask=102):
    asof = slot+timedelta(seconds=asof_delta)
    delta = asof-datetime(1970,1,1,tzinfo=timezone.utc)
    stamp = (delta.days*86400+delta.seconds)*1000+delta.microseconds//1000
    raw = json.dumps([{"market":symbol,"level":0,"timestamp":stamp,
        "total_ask_size":3,"total_bid_size":4,"orderbook_units":[
            {"ask_price":ask,"bid_price":bid,"ask_size":3,"bid_size":4}]}]).encode()
    receipt = SourceReceipt(path="/v1/orderbook", params=(("markets",symbol),("level","0"),("count","30")),
        account_scope="public-upbit-orderbook", received_at=slot+timedelta(seconds=received_delta),
        server_time=slot+timedelta(seconds=received_delta), raw_body=raw, sha256=hashlib.sha256(raw).hexdigest())
    return parse_orderbook(receipt,symbol=symbol,now=receipt.received_at)


def test_program_warmup_equality_cash_and_prefix_decisions_are_exact():
    program, *_ = fixture()
    assert target_fraction(program, ()) == 0
    assert target_fraction(program, (D(1),D(2),D(3))) == 0
    assert target_fraction(program, (D(1),D(2),D(3),D(4))) == D("0.5")
    assert target_fraction(program, (D(4),D(3),D(2),D(1))) == 0
    assert target_fraction(program, (D(2),)*4) == 0
    cash = replace(program, kind="cash", fast_window=0, slow_window=0, exposure_fraction=D(0))
    assert target_fraction(cash, (D(1),D(2))) == 0
    marks = (D("100000000000000000000001"),D("100000000000000000000002"),
             D("100000000000000000000003"),D("100000000000000000000004"))
    with localcontext() as context:
        context.prec = 3
        assert target_fraction(program, marks) == D("0.5")


def test_program_schema_bounds_and_json_do_not_accept_implicit_parameters():
    program, *_ = fixture()
    assert parse_program(program_json(program)) == program
    for change in ({"fast_window":True},{"slow_window":4097},{"exposure_fraction":D("1.01")},
                   {"kind":"arbitrary_code"},{"kind":"cash"},{"strategy_id":"private invalid identifier"}):
        reject(lambda change=change:program_json(replace(program,**change)))
    for raw in ('{"schema_version":1,"schema_version":1}', '{}', '{"x":NaN}',
                program_json(program).replace('"0.5"','0.5'),
                program_json(program).replace('"0.5"','"5e-1"'), b'\xff', b' '*16385):
        reject(lambda raw=raw:parse_program(raw))
    for marks in ((1,), (True,), (D("NaN"),), (D(0),), [D(1)], (D("1e100"),)):
        reject(lambda marks=marks:target_fraction(program,marks))


def test_program_identity_matches_runner_and_binds_source_and_parameters():
    program, *_ = fixture()
    driver = StrategyDriver(callback=lambda data,parameters:None, artifact=PROGRAM_ARTIFACT,
                            parameters_json=parameters_json(program))
    assert runner_program_digest(driver) == program_digest(program,PROGRAM_ARTIFACT)
    assert program_digest(replace(program,exposure_fraction=D("0.50")),PROGRAM_ARTIFACT) == program_digest(program,PROGRAM_ARTIFACT)
    assert program_digest(program,PROGRAM_ARTIFACT+b"changed") != program_digest(program,PROGRAM_ARTIFACT)
    assert program_digest(replace(program,fast_window=1),PROGRAM_ARTIFACT) != program_digest(program,PROGRAM_ARTIFACT)


def test_replay_export_runs_existing_evaluator_and_never_becomes_live_evidence():
    program, protocol, registry, bars, rules = fixture()
    archive = playback(program,protocol,registry,bars)
    raw = capture_json(archive)
    assert set(json.loads(raw)) == {"registry","bars","decisions","source_kind"}
    assert len(archive.decisions) == 60 and archive.source_kind == "synthetic"
    result = evaluate_capture_json(protocol,raw,rules,now=bars[-1].received_at)
    assert result.primary.observations == 60 and result.primary.cash_nonnegative
    assessment = assess_strategy(protocol,result,profile_contract_digest=protocol.profile_contract_digest,
        rule_terms_digest=protocol.rule_terms_digest,strategy_code_sha256=protocol.strategy_code_sha256,
        now=bars[-1].received_at)
    assert not assessment.research_review_ready and not assessment.execution_ready
    assert "STRATEGY_NONPROSPECTIVE_SOURCE" in assessment.reasons


def test_replay_parser_is_strict_and_cannot_import_decisions_or_upgrade_origin():
    program, protocol, registry, bars, _ = fixture()
    body = json.loads(capture_json(playback(program,protocol,registry,bars)))
    del body["decisions"]
    parsed_registry, parsed_bars, kind = parse_replay_input(json.dumps(body))
    assert parsed_registry == registry and parsed_bars == bars and kind == "synthetic"
    for changed in (body|{"source_kind":"prospective_paper_capture"}, body|{"decisions":[]},
                    body|{"PASS":True}):
        reject(lambda changed=changed:parse_replay_input(json.dumps(changed)))
    reject(lambda:parse_replay_input('{"bars":[],"bars":[]}'),"CAPTURE_JSON_DUPLICATE_KEY")
    wrong = json.loads(json.dumps(body)); wrong["bars"][0]["mark"] = 101.0
    reject(lambda:parse_replay_input(json.dumps(wrong)),"CAPTURE_JSON_NUMBER_INVALID")


def test_future_marks_cannot_rewrite_earlier_replay_decisions():
    program, protocol, registry, bars, _ = fixture()
    original = playback(program,protocol,registry,bars)
    altered = tuple(replace(row,bid=D(400),ask=D(402),mark=D(401)) if i>=30 else row for i,row in enumerate(bars))
    changed = playback(program,protocol,registry,altered)
    assert original.decisions[:30] == changed.decisions[:30]
    assert original.decisions[30:] != changed.decisions[30:]


def test_protocol_registry_and_both_code_artifacts_are_bound_before_recording():
    program, protocol, registry, bars, _ = fixture()
    reject(lambda:playback(program,protocol,registry,bars,program_artifact=b"wrong"),"CAPTURE_PROGRAM_BINDING_MISMATCH")
    reject(lambda:playback(program,protocol,registry,bars,capture_source_artifact=b"wrong"),"CAPTURE_SOURCE_BINDING_MISMATCH")
    reject(lambda:playback(replace(program,fast_window=1),protocol,registry,bars),"CAPTURE_PROGRAM_BINDING_MISMATCH")
    reject(lambda:playback(program,protocol,(),bars),"CAPTURE_PROTOCOL_NOT_REGISTERED")
    wrong = replace(protocol,capture_end=protocol.capture_end+timedelta(seconds=1))
    reject(lambda:playback(program,wrong,register_protocol(wrong),bars),"CAPTURE_WINDOW_GRID_INVALID")


def test_replay_missing_duplicate_future_and_late_slots_refuse_without_backfill():
    program, protocol, registry, bars, _ = fixture()
    reject(lambda:playback(program,protocol,registry,bars,source_kind="prospective_paper_capture"),"CAPTURE_BATCH_NOT_PROSPECTIVE")
    reject(lambda:playback(program,protocol,registry,bars[1:]),"CAPTURE_SLOT_GAP_OR_DUPLICATE")
    reject(lambda:playback(program,protocol,registry,(bars[0],)+bars),"CAPTURE_SLOT_GAP_OR_DUPLICATE")
    reject(lambda:playback(program,protocol,registry,bars[:-1]),"CAPTURE_WINDOW_INCOMPLETE")
    reject(lambda:playback(program,protocol,registry,bars,now=bars[-1].observed_at),"CAPTURE_FUTURE_RECEIPT")
    late = (replace(bars[0],received_at=bars[0].observed_at+timedelta(seconds=59,microseconds=1)),)+bars[1:]
    reject(lambda:playback(program,protocol,registry,late),"CAPTURE_DECISION_TOO_LATE")


def test_stream_records_actual_clock_and_exact_prefix_then_exports_complete_window():
    program, protocol, registry, bars, rules = fixture()
    capture, clock = recorder(program,protocol,registry)
    for i,row in enumerate(bars):
        clock[0] = row.received_at+timedelta(seconds=1)
        decision = capture.append(row)
        if i<len(bars)-1:
            assert decision.decided_at == clock[0] and decision.decided_at > row.received_at
            assert decision.target_fraction == target_fraction(program,tuple(b.mark for b in bars[:i+1]))
        else:
            assert decision is None
    archive = capture.finish()
    assert archive.source_kind == "prospective_paper_capture"
    result = evaluate_capture_json(protocol,capture_json(archive),rules,now=clock[0])
    assessment = assess_strategy(protocol,result,profile_contract_digest=protocol.profile_contract_digest,
        rule_terms_digest=protocol.rule_terms_digest,strategy_code_sha256=protocol.strategy_code_sha256,now=clock[0])
    assert "STRATEGY_TRUSTED_REVIEW_REQUIRED" in assessment.reasons
    assert not assessment.research_review_ready and not assessment.execution_ready
    reject(lambda:capture.append(bars[-1]),"CAPTURE_ALREADY_CLOSED")
    reject(capture.finish,"CAPTURE_ALREADY_CLOSED")


def test_stream_start_clock_and_slot_refusals_do_not_fill_missing_history():
    program, protocol, registry, bars, _ = fixture()
    reject(lambda:PaperCapture(protocol,registry,program,program_artifact=PROGRAM_ARTIFACT,
        capture_source_artifact=CAPTURE_ARTIFACT,clock=lambda:START),"CAPTURE_MUST_START_BEFORE_WINDOW")
    capture, clock = recorder(program,protocol,registry)
    clock[0] = bars[1].received_at
    reject(lambda:capture.append(bars[1]),"CAPTURE_SLOT_GAP_OR_DUPLICATE")
    assert capture.snapshot().bars == ()
    reject(lambda:capture.append(bars[0]),"CAPTURE_DECISION_TOO_LATE")
    clock[0] = bars[0].received_at
    reject(lambda:capture.append(bars[0]),"CAPTURE_CLOCK_ROLLBACK")
    reject(capture.finish,"CAPTURE_CLOCK_ROLLBACK")


def test_partial_stream_can_be_archived_but_mutated_past_records_refuse():
    program, protocol, registry, bars, rules = fixture()
    capture, clock = recorder(program,protocol,registry)
    clock[0] = bars[0].received_at
    decision = capture.append(bars[0])
    partial = capture.snapshot()
    assert len(json.loads(capture_json(partial))["bars"]) == 1
    reject(lambda:evaluate_capture_json(protocol,capture_json(partial),rules,now=clock[0]))
    reject(capture.finish,"CAPTURE_WINDOW_INCOMPLETE")
    object.__setattr__(decision,"target_fraction",D("0.7"))
    reject(capture.snapshot,"CAPTURE_HISTORY_CHANGED")


def test_prefetched_sampling_preserves_real_source_times_and_exact_raw_digest():
    original = book()
    before = (original.asof,original.received_at,original.receipt.raw_body,original.source_sha256)
    sampled_at = START+timedelta(seconds=1)
    row = sample_prefetched_book(original,slot=START,sampled_at=sampled_at)
    assert row.observed_at == START and row.received_at == sampled_at
    assert row.bid == D(100) and row.ask == D(102) and row.mark == D(101)
    assert row.source_sha256 == hashlib.sha256(original.receipt.raw_body).hexdigest()
    assert before == (original.asof,original.received_at,original.receipt.raw_body,original.source_sha256)
    assert original.received_at < row.observed_at < row.received_at


def test_sampling_refuses_post_slot_future_stale_or_changed_book():
    original = book()
    reject(lambda:sample_prefetched_book(book(received_delta=1,asof_delta=0),slot=START,
        sampled_at=START+timedelta(seconds=2)),"CAPTURE_BOOK_NOT_AVAILABLE_AT_SLOT")
    reject(lambda:sample_prefetched_book(original,slot=START,sampled_at=START-timedelta(seconds=1)),
           "CAPTURE_BOOK_NOT_AVAILABLE_AT_SLOT")
    reject(lambda:sample_prefetched_book(original,slot=START,sampled_at=START+timedelta(seconds=11)))
    altered = replace(original,source_sha256="f"*64)
    reject(lambda:sample_prefetched_book(altered,slot=START,sampled_at=START+timedelta(seconds=1)))


def test_stream_book_adapter_uses_injected_sample_time_and_keeps_original_receipts():
    program, protocol, registry, _, _ = fixture()
    capture, clock = recorder(program,protocol,registry)
    clock[0] = START+timedelta(seconds=1)
    original = book()
    decision = capture.append_book(original)
    assert decision.decided_at == clock[0]
    assert capture.sampled_receipts == ((0,original.receipt),)
    assert capture.snapshot().bars[0].source_sha256 == original.receipt.sha256
    # A source from another market is never relabeled to the protocol's symbol.
    capture, clock = recorder(program,protocol,registry)
    clock[0] = START+timedelta(seconds=1)
    reject(lambda:capture.append_book(book(symbol="KRW-ETH")),"CAPTURE_BOOK_MARKET_MISMATCH")
    assert capture.snapshot().bars == () and capture.sampled_receipts == ()
