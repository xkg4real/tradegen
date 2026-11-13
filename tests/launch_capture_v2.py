"""Invented causal carry evidence; no source authentication or live approval."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
import hashlib
import json

from execution_launch import capture_v2 as C, managed_behavior as M, paper_capture as P
from execution_launch.program import parameters_json, program_digest
from execution_launch.strategy import evaluate_capture_json, evidence_digest, register_protocol
from tests import launch_capture as F


def fixture():
    program, legacy, _, bars, rules = F.fixture()
    protocol = replace(legacy, schema_version=2, evaluator_revision=M.CARRY_EVALUATOR_REVISION,
        behavior_revision=M.BEHAVIOR_REVISION, terminal_accounting=M.TERMINAL_ACCOUNTING,
        management_behavior_sha256=M.behavior_digest())
    bars = tuple(replace(row, bid=Decimal(100+i), ask=Decimal(102+i), mark=Decimal(101+i))
                 for i, row in enumerate(bars))
    return program, protocol, register_protocol(protocol), bars, rules


def replay(program, protocol, registry, bars, **changes):
    args = dict(program_artifact=F.PROGRAM_ARTIFACT, capture_source_artifact=F.CAPTURE_ARTIFACT,
                source_kind="synthetic", now=bars[-1].received_at)
    return P.replay_capture_v2(protocol, registry, program, bars, **(args | changes))


def rewrite_decision(row, **changes):
    body = row | changes
    unsigned = {key: value for key, value in body.items() if key != "decision_sha256"}
    body["decision_sha256"] = hashlib.sha256(json.dumps(unsigned, sort_keys=True,
        separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("ascii")).hexdigest()
    return body


def test_replay_roundtrip_rederives_warmup_and_the_final_positive_verdict():
    program, protocol, registry, bars, _ = fixture()
    archive = replay(program, protocol, registry, bars)
    assert archive.program == program and archive.program_parameters_json == parameters_json(program)
    assert archive.program_artifact_sha256 == hashlib.sha256(F.PROGRAM_ARTIFACT).hexdigest()
    assert len(archive.decisions) == len(bars)
    assert [(row.state, row.cause, row.target_fraction) for row in archive.decisions[:3]] == [
        ("warmup", "insufficient_history", None)] * 3
    assert archive.decisions[-1].state == "long_target"
    assert archive.decisions[-1].bar_index == len(bars)-1
    assert archive.decisions[-1].decided_at >= protocol.capture_end
    raw = C.capture_json_v2(archive)
    assert C.parse_capture_v2(protocol, raw) == archive
    assert C.capture_json_v2(C.parse_capture_v2(protocol, raw)) == raw


def test_streaming_capture_records_actual_decision_times_and_keeps_the_final_bar():
    program, protocol, registry, bars, _ = fixture()
    clock = [protocol.capture_start-timedelta(seconds=1)]
    capture = P.PaperCaptureV2(protocol, registry, program, program_artifact=F.PROGRAM_ARTIFACT,
        capture_source_artifact=F.CAPTURE_ARTIFACT, clock=lambda: clock[0])
    for bar in bars:
        clock[0] = bar.received_at + timedelta(seconds=1)
        decision = capture.append(bar)
        assert decision.decided_at == clock[0]
    archive = capture.finish()
    assert archive.source_kind == "prospective_paper_capture" and len(archive.decisions) == len(bars)
    assert C.parse_capture_v2(protocol, C.capture_json_v2(archive)) == archive
    F.reject(lambda: capture.append(bars[-1]), "CAPTURE_ALREADY_CLOSED")


def test_incomplete_trial_can_be_archived_but_not_imported_as_complete_evidence():
    program, protocol, registry, bars, _ = fixture()
    clock = [protocol.capture_start-timedelta(seconds=1)]
    capture = P.PaperCaptureV2(protocol, registry, program, program_artifact=F.PROGRAM_ARTIFACT,
        capture_source_artifact=F.CAPTURE_ARTIFACT, clock=lambda: clock[0])
    for bar in bars[:2]:
        clock[0] = bar.received_at
        capture.append(bar)
    partial = capture.snapshot()
    assert len(partial.bars) == len(partial.decisions) == 2
    raw = C.capture_json_v2(partial)
    F.reject(lambda: C.parse_capture_v2(protocol, raw))
    F.reject(capture.finish, "CAPTURE_WINDOW_INCOMPLETE")
    assert capture.snapshot() == partial


def test_valid_prefetched_receipt_is_preserved_and_bad_book_is_not_an_unavailable_bar():
    program, protocol, registry, _, _ = fixture()
    clock = [protocol.capture_start-timedelta(seconds=1)]
    capture = P.PaperCaptureV2(protocol, registry, program, program_artifact=F.PROGRAM_ARTIFACT,
        capture_source_artifact=F.CAPTURE_ARTIFACT, clock=lambda: clock[0])
    book = F.book(slot=protocol.capture_start)
    clock[0] = protocol.capture_start
    decision = capture.append_book(book)
    assert decision.state == "warmup" and capture.sampled_receipts == ((0, book.receipt),)
    before = capture.snapshot()
    clock[0] += timedelta(seconds=protocol.bar_seconds)
    F.reject(lambda: capture.append_book(book))  # Stale original quote cannot backfill the next slot.
    assert capture.snapshot() == before and capture.sampled_receipts == ((0, book.receipt),)


def test_legacy_capture_shape_and_numeric_final_behavior_remain_separate():
    program, protocol, registry, bars, _ = F.fixture()
    legacy = F.playback(program, protocol, registry, bars)
    body = json.loads(P.capture_json(legacy))
    assert set(body) == {"registry", "source_kind", "bars", "decisions"}
    assert len(body["decisions"]) == len(body["bars"])-1
    assert set(body["decisions"][0]) == {"bar_index", "decided_at", "history_sha256", "target_fraction"}
    assert body["decisions"][0]["target_fraction"] == "0"
    carry = fixture()
    F.reject(lambda: F.playback(*carry[:4]), "CAPTURE_PROTOCOL_REVISION_MISMATCH")
    F.reject(lambda: replay(program, protocol, registry, bars), "CAPTURE_PROTOCOL_REVISION_MISMATCH")
    F.reject(lambda: C.parse_capture_v2(carry[1], P.capture_json(legacy)))
    F.reject(lambda: P.capture_json(replay(*carry[:4])), "CAPTURE_ARCHIVE_REQUIRED")


def test_forged_but_correctly_rehashed_verdict_prefix_and_availability_are_rejected():
    program, protocol, registry, bars, _ = fixture()
    raw = C.capture_json_v2(replay(program, protocol, registry, bars))
    for change in (
        dict(state="cash_target", cause="trend_not_above", target_fraction="0"),
        dict(state="warmup", cause="insufficient_history", target_fraction=None),
        dict(state="unavailable", cause="input_unavailable", target_fraction=None),
        dict(history_sha256="f"*64), dict(bar_index=3),
        dict(cause="benchmark_buy_hold", target_fraction="1"),
        dict(decided_at=(protocol.capture_end+timedelta(seconds=protocol.bar_seconds)).isoformat(timespec="microseconds")),
    ):
        body = json.loads(raw)
        body["decisions"][-1] = rewrite_decision(body["decisions"][-1], **change)
        F.reject(lambda: C.parse_capture_v2(protocol, json.dumps(body)))


def test_program_artifact_parameters_behavior_and_registration_cannot_be_substituted():
    program, protocol, registry, bars, _ = fixture()
    raw = C.capture_json_v2(replay(program, protocol, registry, bars))
    mutations = (
        {"program_artifact_sha256": "a"*64},
        {"program_parameters_json": parameters_json(replace(program, exposure_fraction=Decimal("0.7")))},
        {"program_parameters_json": json.dumps(json.loads(parameters_json(program)), indent=2)},
        {"behavior_sha256": "b"*64}, {"registry": []}, {"schema_version": True},
    )
    for change in mutations:
        F.reject(lambda: C.parse_capture_v2(protocol, json.dumps(json.loads(raw) | change)))
    F.reject(lambda: replay(program, protocol, registry, bars, program_artifact=b"wrong artifact"),
             "CAPTURE_PROGRAM_BINDING_MISMATCH")
    F.reject(lambda: replay(program, protocol, registry, bars, capture_source_artifact=b"wrong source"),
             "CAPTURE_SOURCE_BINDING_MISMATCH")


def test_malformed_missing_and_late_observations_are_refused_without_unavailable_fallback():
    program, protocol, registry, bars, _ = fixture()
    raw = C.capture_json_v2(replay(program, protocol, registry, bars))
    for mutate in (
        lambda body: body["bars"].pop(5),
        lambda body: body["decisions"].pop(),
        lambda body: body["bars"][0].update(mark="NaN"),
        lambda body: body["bars"][0].update(mark="0"),
        lambda body: body["bars"][0].update(bid="999"),
        lambda body: body["bars"][0].update(source_sha256="not-a-hash"),
        lambda body: body["decisions"][0].update(decided_at=body["decisions"][3]["decided_at"]),
    ):
        body = json.loads(raw)
        mutate(body)
        F.reject(lambda: C.parse_capture_v2(protocol, json.dumps(body)))
    F.reject(lambda: replay(program, protocol, registry, bars, source_kind="prospective_paper_capture"),
             "CAPTURE_BATCH_NOT_PROSPECTIVE")


def test_closed_archive_and_decision_schemas_refuse_duplicate_unknown_and_numeric_fields():
    program, protocol, registry, bars, _ = fixture()
    raw = C.capture_json_v2(replay(program, protocol, registry, bars))
    F.reject(lambda: C.parse_capture_v2(protocol, '{"schema_version":2,'+raw[1:]))
    F.reject(lambda: C.parse_capture_v2(protocol, json.dumps(json.loads(raw) | {"approved": True})))
    for field, value in (("target_fraction", 0.5), ("bar_index", False),
                         ("decision_sha256", "a"*64), ("approved", True)):
        body = json.loads(raw)
        body["decisions"][-1][field] = value
        F.reject(lambda: C.parse_capture_v2(protocol, json.dumps(body)))


def test_imported_v2_evidence_reaches_the_actual_evaluator_and_keeps_open_inventory():
    program, protocol, registry, bars, rules = fixture()
    archive = replay(program, protocol, registry, bars)
    result = evaluate_capture_json(protocol, C.capture_json_v2(archive), rules, now=bars[-1].received_at)
    assert result.behavior_revision == M.BEHAVIOR_REVISION and result.schema_version == 2
    assert Decimal(result.primary.terminal_units) > 0 and result.primary.completed_roundtrips == 0
    assert Decimal(result.primary.realized_net_profit_quote) == 0
    assert Decimal(result.primary.unrealized_net_profit_quote) > 0
    assert result.source_kind == "synthetic"


def test_same_numeric_target_does_not_erase_warmup_cash_or_strategy_sell_causes():
    program, protocol, registry, bars, _ = fixture()
    falling = tuple(replace(row, bid=Decimal(200-i), ask=Decimal(202-i), mark=Decimal(201-i))
                    for i, row in enumerate(bars))
    archive = replay(program, protocol, registry, falling)
    assert archive.decisions[0].target_fraction is None and archive.decisions[0].state == "warmup"
    assert archive.decisions[-1].target_fraction == 0 and archive.decisions[-1].cause == "trend_not_above"
    cash = replace(program, kind="cash", fast_window=0, slow_window=0, exposure_fraction=Decimal(0))
    cash_protocol = replace(protocol, strategy_code_sha256=program_digest(cash, F.PROGRAM_ARTIFACT))
    cash_archive = replay(cash, cash_protocol, register_protocol(cash_protocol), bars)
    assert all(row.cause == "always_cash" and row.state == "cash_target" for row in cash_archive.decisions)


def test_nonmidpoint_mark_within_the_spread_cannot_issue_even_fully_rehashed_typed_evidence():
    program, protocol, registry, bars, rules = fixture()
    archive = replay(program, protocol, registry, bars)
    altered = (replace(bars[0], mark=bars[0].bid+Decimal("0.5")),) + bars[1:]
    assert altered[0].bid < altered[0].mark < altered[0].ask
    F.reject(lambda: replay(program, protocol, registry, altered), "CAPTURE_V2_MARK_NOT_MIDPOINT")
    # Recompute every prefix and decision: rejection must come from quote semantics,
    # not merely a stale outer or decision hash.
    chain, marks, decisions = "", (), []
    for index, bar in enumerate(altered):
        chain = evidence_digest((chain, bar))
        marks += (bar.mark,)
        decisions.append(M.derive_fixed_decision_v2(program, marks, bar_index=index,
            decided_at=bar.received_at, history_sha256=chain))
    forged = replace(archive, bars=altered, decisions=tuple(decisions))
    F.reject(lambda: C.validate_capture_v2(protocol, forged), "CAPTURE_V2_MARK_NOT_MIDPOINT")
    raw = C.capture_json_v2(forged)
    F.reject(lambda: C.parse_capture_v2(protocol, raw))
    F.reject(lambda: evaluate_capture_json(protocol, raw, rules, now=bars[-1].received_at))
    clock = [protocol.capture_start-timedelta(seconds=1)]
    recorder = P.PaperCaptureV2(protocol, registry, program, program_artifact=F.PROGRAM_ARTIFACT,
        capture_source_artifact=F.CAPTURE_ARTIFACT, clock=lambda: clock[0])
    before = recorder.snapshot()
    clock[0] = altered[0].received_at
    F.reject(lambda: recorder.append(altered[0]), "CAPTURE_V2_MARK_NOT_MIDPOINT")
    assert recorder.snapshot() == before
