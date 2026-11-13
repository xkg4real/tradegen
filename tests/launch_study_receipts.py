"""Actual recorder and invented public responses only; no live source claims."""
from dataclasses import replace
from datetime import timedelta
from functools import lru_cache
import base64
import hashlib
import json
from types import SimpleNamespace
from unittest.mock import patch

from execution_launch import managed_behavior as M
from execution_launch import strategy as S
from execution_launch import study as U
from execution_launch import study_receipts as R
from execution_launch.capture_v2 import capture_json_v2
from execution_launch.paper_capture import capture_json
from tests import launch_study as F


@lru_cache(maxsize=4)
def fixture(carry=False, aborted=False):
    template = F.template()
    if carry:
        template = replace(template, schema_version=2, evaluator_revision=M.CARRY_EVALUATOR_REVISION,
            behavior_revision=M.BEHAVIOR_REVISION, terminal_accounting=M.TERMINAL_ACCOUNTING,
            management_behavior_sha256=M.behavior_digest())
    plan = U.build_study_plan(F.profile(), F.PROGRAMS, template=template,
                             plan_id='receipt-fixture', asset='BTC', risk_group='crypto-btc')
    driver = F.Driver(plan)
    if aborted:
        driver.on_wait = lambda when: when < driver.slot(3) - timedelta(seconds=5)
    def clock():
        # Every candidate samples the SAME earlier receipt at its own real call
        # time, deliberately distinct from both receipt and sibling sample time.
        elapsed = driver.clock[0] - driver.start
        if elapsed >= timedelta(0) and elapsed % F.BAR < timedelta(seconds=1):
            driver.clock[0] += timedelta(microseconds=1000)
        return driver.clock[0]
    before = dict(S._EVALUATED)
    outcome = U.run_capture(plan, book_source=driver.read, clock=clock,
        wait_until=driver.wait_until, record=driver.lines.append)
    assert outcome.complete is (not aborted) and S._EVALUATED == before
    captures = {candidate.protocol.study_id: (capture_json_v2(archive) if carry else capture_json(archive)).encode('ascii')
                for candidate, archive in zip(plan.candidates, outcome.archives)}
    return SimpleNamespace(plan=plan, captures=captures, receipt_log=b''.join(driver.lines),
                           outcome=outcome, lines=tuple(driver.lines))


def check(env, **changes):
    args = dict(plan=env.plan, captures=env.captures, receipt_log=env.receipt_log)
    args.update(changes)
    return R.validate_study_receipts(**args)


def refused(call, code=None):
    try:
        call()
    except R.StudyReceiptError as exc:
        if code is not None:
            assert str(exc) == code, (str(exc), code)
        return
    raise AssertionError('invalid receipt evidence accepted')


def altered_log(env, index, change):
    lines = list(env.lines)
    row = json.loads(lines[index])
    change(row)
    lines[index] = U._line(row)
    return b''.join(lines)


def test_actual_fixed_and_carry_recorders_audit_all_candidates_without_evaluation_or_source_io():
    for carry in (False, True):
        env = fixture(carry)
        before = dict(S._EVALUATED)
        with patch.object(S, 'evaluate_capture_json', side_effect=AssertionError('evaluation forbidden')), \
             patch.object(U, '_fixed_file', side_effect=AssertionError('source I/O forbidden')), \
             patch.object(U, 'validate_study_plan', side_effect=AssertionError('source I/O forbidden')):
            audit = check(env)
        assert S._EVALUATED == before
        assert audit.slot_count == 61 and audit.receipt_count == 62
        assert audit.plan_digest == S.evidence_digest(env.plan)
        assert audit.receipt_log_sha256 == hashlib.sha256(env.receipt_log).hexdigest()
        assert dict(audit.capture_digests) == {key:hashlib.sha256(raw).hexdigest() for key,raw in env.captures.items()}
        receipt_time = json.loads(env.lines[1])['receipt']['received_at']
        samples = [json.loads(raw)['bars'][0]['received_at'] for raw in env.captures.values()]
        assert len(set(samples)) == 3 and all(value != receipt_time for value in samples)


def test_audit_encoding_is_versioned_and_does_not_claim_authority():
    audit = check(fixture())
    raw = R.receipt_audit_bytes(audit)
    assert json.loads(raw)['schema_version'] == 1
    assert R.receipt_audit_digest(audit) == hashlib.sha256(b'tradegen-study-receipt-audit/1\n' + raw).hexdigest()
    assert R.receipt_audit_digest(audit) != hashlib.sha256(raw).hexdigest()
    assert not {'approved', 'source_authenticated', 'execution_ready'} & set(json.loads(raw))
    refused(lambda: R.receipt_audit_bytes(replace(audit, slot_count=True)), 'STUDY_RECEIPTS_AUDIT_INVALID')
    broken = replace(audit)
    object.__delattr__(broken, 'receipt_count')
    refused(lambda: R.receipt_audit_digest(broken), 'STUDY_RECEIPTS_AUDIT_INVALID')


def test_complete_recorded_abort_is_distinct_from_missing_or_truncated_end_and_never_evaluates():
    for carry in (False, True):
        env = fixture(carry, True)
        assert not env.outcome.complete and json.loads(env.lines[-1])['end'] == 'STUDY_CAPTURE_STOPPED'
        with patch.object(S, 'evaluate_capture_json', side_effect=AssertionError('evaluation forbidden')):
            refused(lambda: check(env), 'STUDY_RECEIPTS_CAPTURE_ABORTED')
            refused(lambda: check(env, receipt_log=env.receipt_log[:-1]), 'STUDY_RECEIPTS_LOG_INCOMPLETE')
            refused(lambda: check(env, receipt_log=b''.join(env.lines[:-1])))
        damaged = altered_log(env, -2, lambda row: row['receipt'].__setitem__('sha256', '0' * 64))
        refused(lambda: check(env, receipt_log=damaged), 'STUDY_RECEIPTS_RECEIPT_INVALID')


def test_last_receipt_hash_raw_body_and_source_scope_changes_refuse():
    env = fixture()
    changes = (
        lambda row: row['receipt'].__setitem__('sha256', '0' * 64),
        lambda row: row['receipt'].__setitem__('raw_body_b64', '@@@'),
        lambda row: row['receipt'].__setitem__('path', '/v1/accounts'),
        lambda row: row['receipt'].__setitem__('account_scope', 'invented-private-scope'),
        lambda row: row['receipt']['params'][0].__setitem__(1, 'KRW-OTHER'),
        lambda row: row['receipt'].__setitem__('unexpected', True),
    )
    for change in changes:
        refused(lambda change=change: check(env, receipt_log=altered_log(env, -2, change)))


def test_rehashed_malformed_orderbook_is_not_accepted_as_original_evidence():
    env = fixture()
    def change(row):
        receipt = row['receipt']
        body = json.loads(base64.b64decode(receipt['raw_body_b64']))
        body[0]['orderbook_units'][0]['bid_price'] = True
        raw = json.dumps(body).encode()
        receipt['raw_body_b64'] = base64.b64encode(raw).decode()
        receipt['sha256'] = hashlib.sha256(raw).hexdigest()
    refused(lambda: check(env, receipt_log=altered_log(env, -2, change)), 'STUDY_RECEIPTS_RECEIPT_INVALID')
    # Rehashing malformed JSON or a duplicate key does not make the receipt
    # parseable. The real SourceReceipt decoder, not only the resource scanner,
    # must reject both original bodies.
    original = base64.b64decode(json.loads(env.lines[-2])['receipt']['raw_body_b64'])
    assert original.startswith(b'[{')
    duplicate = b'[{"market":"KRW-IGNORED",' + original[2:]
    for invalid in (duplicate, b'[{]'):
        def corrupt(row):
            row['receipt']['raw_body_b64'] = base64.b64encode(invalid).decode()
            row['receipt']['sha256'] = hashlib.sha256(invalid).hexdigest()
        refused(lambda: check(env, receipt_log=altered_log(env, -2, corrupt)), 'STUDY_RECEIPTS_RECEIPT_INVALID')


def test_slot_boolean_gap_duplicate_extra_fields_and_post_end_data_refuse():
    env = fixture()
    for index, change in (
        (1, lambda row: row.__setitem__('slot', False)),
        (2, lambda row: row.__setitem__('slot', 0)),
        (2, lambda row: row.__setitem__('slot', 2)),
        (2, lambda row: row.__setitem__('unrecognized', 1)),
    ):
        refused(lambda: check(env, receipt_log=altered_log(env, index, change)), 'STUDY_RECEIPTS_LOG_FORMAT_INVALID')
    for raw in (env.receipt_log + env.lines[-1], env.receipt_log + env.lines[1], b''.join(env.lines[:2] + env.lines[3:])):
        refused(lambda raw=raw: check(env, receipt_log=raw))


def test_duplicate_json_key_and_nonfinite_or_float_tokens_refuse():
    env = fixture()
    for prefix in (b'"slot":0,', b'"extra":NaN,', b'"extra":1.5,'):
        lines = list(env.lines)
        lines[-2] = b'{' + prefix + lines[-2][1:]
        refused(lambda: check(env, receipt_log=b''.join(lines)), 'STUDY_RECEIPTS_LOG_FORMAT_INVALID')


def test_last_candidate_last_bar_or_decision_damage_is_not_hidden_by_valid_receipts():
    for carry in (False, True):
        env = fixture(carry)
        key = env.plan.candidates[-1].protocol.study_id
        for change in (
            lambda body: body['bars'][-1].__setitem__('source_sha256', '0' * 64),
            lambda body: body['decisions'][-1].__setitem__('history_sha256', '0' * 64),
            lambda body: body.__setitem__('source_kind', 'retrospective_replay'),
        ):
            body = json.loads(env.captures[key]); change(body)
            refused(lambda: check(env, captures=env.captures | {key:json.dumps(body).encode()}))


def test_log_decision_mismatch_and_legacy_terminal_null_carry_terminal_typed_contract():
    env = fixture()
    raw = altered_log(env, 5, lambda row: row['decisions'][0].__setitem__(1, '0' if row['decisions'][0][1] != '0' else '1'))
    refused(lambda: check(env, receipt_log=raw), 'STUDY_RECEIPTS_EVIDENCE_MISMATCH')
    refused(lambda: check(env, receipt_log=altered_log(env, -2, lambda row: row['decisions'][0].__setitem__(1, '0'))),
            'STUDY_RECEIPTS_EVIDENCE_MISMATCH')
    carry = fixture(True)
    refused(lambda: check(carry, receipt_log=altered_log(carry, -2, lambda row: row['decisions'][0].__setitem__(1, None))))


def test_receipt_after_slot_cannot_be_relabelled_as_historical_prefetch():
    env = fixture()
    def change(row):
        slot = S._date(row['observed_at'])
        row['receipt']['received_at'] = S._plain(slot + timedelta(seconds=1))
        row['receipt']['server_time'] = row['receipt']['received_at']
    refused(lambda: check(env, receipt_log=altered_log(env, -2, change)), 'STUDY_RECEIPTS_RECEIPT_INVALID')


def test_missing_extra_or_wrongly_typed_candidate_inputs_refuse_without_io():
    env = fixture()
    key = next(iter(env.captures))
    for captures in ({k:v for k,v in env.captures.items() if k != key},
                     env.captures | {'extra':b'{}'}, env.captures | {key:'{}'}):
        refused(lambda captures=captures: check(env, captures=captures), 'STUDY_RECEIPTS_CAPTURE_FAMILY_INVALID')


def test_log_line_record_body_and_capture_limits_exact_and_one_under():
    env = fixture()
    largest_body = max(len(base64.b64decode(json.loads(line).get('receipt', json.loads(line).get('probe', {})).get('raw_body_b64', '')))
                       for line in env.lines)
    exact = R.ReceiptLimits(max_log_bytes=len(env.receipt_log), max_line_bytes=max(len(line) - 1 for line in env.lines),
        max_records=len(env.lines), max_body_bytes=largest_body, max_candidates=len(env.captures),
        max_capture_bytes=max(map(len, env.captures.values())), max_total_capture_bytes=sum(map(len, env.captures.values())))
    assert check(env, limits=exact).slot_count == 61
    for name in ('max_log_bytes', 'max_line_bytes', 'max_records', 'max_body_bytes', 'max_candidates',
                 'max_capture_bytes', 'max_total_capture_bytes'):
        refused(lambda name=name: check(env, limits=replace(exact, **{name:getattr(exact, name) - 1})),
                'STUDY_RECEIPTS_RESOURCE_LIMIT')


def test_newline_density_and_json_depth_are_rejected_before_json_decode():
    env = fixture()
    limits = replace(R.DEFAULT_LIMITS, max_records=3)
    # The plan legitimately parses its own protocols first. Observe only the
    # receipt-log decoder here, not the shared stdlib JSON function it uses too.
    with patch.object(R, '_json', side_effect=AssertionError('receipt decoding before LF admission')):
        refused(lambda: check(env, receipt_log=b'\n' * 4, limits=limits), 'STUDY_RECEIPTS_RESOURCE_LIMIT')
    with patch.object(R.json, 'loads', side_effect=AssertionError('must reject before decoder')):
        refused(lambda: R._json(b'[' * 13 + b'0' + b']' * 13, R.DEFAULT_LIMITS), 'STUDY_RECEIPTS_RESOURCE_LIMIT')
    assert R._json(b'[' * 12 + b'0' + b']' * 12, R.DEFAULT_LIMITS) is not None


def test_json_nodes_are_bounded_before_decoder_and_invalid_limits_refuse():
    limits = replace(R.DEFAULT_LIMITS, max_json_nodes=3)
    with patch.object(R.json, 'loads', side_effect=AssertionError('must reject before decoder')):
        refused(lambda: R._json(b'[0,0,0,0]', limits), 'STUDY_RECEIPTS_RESOURCE_LIMIT')
    for changes in (dict(max_records=True), dict(max_line_bytes=0), dict(max_body_bytes=131073)):
        refused(lambda: R.ReceiptLimits(**changes), 'STUDY_RECEIPTS_LIMITS_INVALID')
