"""Closed packet-format tests over the real collector with invented GET replies.

Temporary fixture homes only. Retained source/coverage claims remain synthetic.
No tests grant current account/source authority or make an order/API call.
"""
from collections.abc import Mapping
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import replace
from datetime import timedelta, timezone
from decimal import Decimal
import hashlib
import json
from unittest.mock import patch

from execution_launch import guard_capture_format as F
from execution_launch import guard_capture_material as M
from tests import launch_guard_capture_material as V
from tests.accounts_continuous import held_series

D = Decimal


@contextmanager
def fixture():
    with held_series() as env:
        captured = V.capture(env)
        encoded = F.build_capture_archive(captured.staged, env.state)
        yield env, captured.staged, encoded


def refused(call, code=None):
    try:
        call()
    except F.GuardCaptureFormatError as exc:
        assert str(exc) in {'CAPTURE_FORMAT_INVALID', 'CAPTURE_RESOURCE_LIMIT',
            'CAPTURE_LIMITS_INVALID', 'CAPTURE_PAYLOAD_MISMATCH', 'CAPTURE_BASELINE_MISMATCH'}, str(exc)
        if code is not None:
            assert str(exc) == code, (str(exc), code)
        return str(exc)
    raise AssertionError('expected fixed capture format refusal')


def decode(encoded, *, payloads=None, limits=F.DEFAULT_LIMITS, expected=None):
    return F.parse_capture_archive(encoded.payloads if payloads is None else payloads,
        expected_previous_state_sha256=encoded.previous_state_sha256 if expected is None else expected, limits=limits)


def edited(encoded, change):
    values = dict(encoded.payloads)
    body = json.loads(values['packet'])
    change(body)
    values['packet'] = json.dumps(body, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()
    return values


def stage(body):
    return body['staged']['v']


def preview(body):
    return stage(body)['preview']['v']


def receipt(body, index=0):
    return stage(body)['capture']['v']['receipts']['v'][index]['v']


def test_actual_complete_stage_roundtrip_uses_exact_full_inventory_and_new_digest_domain():
    with fixture() as (env, staged, encoded):
        result = decode(encoded)
        assert M._same(result.staged, staged) and M._same(result.previous, env.state)
        assert len(result.inventory) == len(staged.capture.receipts)+2
        assert tuple(v.logical_id for v in result.inventory) == tuple(sorted(encoded.payloads))
        assert encoded.packet_sha256 == hashlib.sha256(F.PACKET_DOMAIN+encoded.payloads['packet']).hexdigest()
        assert encoded.packet_sha256 != hashlib.sha256(encoded.payloads['packet']).hexdigest()
        assert not any((result.source_authenticated, result.current_freshness_verified,
                        result.guard_committed, result.execution_ready))
        assert 'account_scope' not in repr(result) and 'raw_body' not in repr(encoded)


def test_decimal_signed_zero_positive_exponent_and_scale_are_lossless():
    with fixture() as (env, staged, _):
        for number in (D('-0.00'), D('0.00'), D('1E+1'), D('10'), D('10.000')):
            mark = replace(staged.preview.path.opening_marks[0], price=number)
            changed = replace(staged, preview=replace(staged.preview,
                path=replace(staged.preview.path, opening_marks=(mark,))))
            encoded = F.build_capture_archive(changed, env.state)
            actual = decode(encoded).staged.preview.path.opening_marks[0].price
            assert actual.as_tuple() == number.as_tuple()
        a = F.build_capture_archive(replace(staged, anchor=replace(staged.anchor, cash_krw=D('1E+1'))), env.state)
        b = F.build_capture_archive(replace(staged, anchor=replace(staged.anchor, cash_krw=D('10'))), env.state)
        assert a.packet_sha256 != b.packet_sha256


def test_optional_position_none_is_preserved_instead_of_becoming_false():
    with fixture() as (env, staged, _):
        account = staged.capture.accounts[0]
        account = replace(account, positions=(replace(account.positions[0], unlisted=None),))
        changed = replace(staged, capture=replace(staged.capture, accounts=(account,)))
        actual = decode(F.build_capture_archive(changed, env.state)).staged.capture.accounts[0]
        assert actual.positions[0].unlisted is None


def test_raw_malformed_response_and_wrong_claim_are_preserved_for_later_audit():
    with fixture() as (env, staged, _):
        raw = b'  {broken: original response\n'
        first = replace(staged.capture.receipts[0], raw_body=raw, sha256='f'*64)
        changed = replace(staged, capture=replace(staged.capture, receipts=(first,)+staged.capture.receipts[1:]))
        encoded = F.build_capture_archive(changed, env.state)
        actual = decode(encoded)
        assert encoded.payloads['receipt-000000'] == raw
        assert actual.staged.capture.receipts[0].sha256 == 'f'*64
        assert encoded.inventory[2].sha256 == hashlib.sha256(raw).hexdigest()
        V.refused(lambda: M.prepare_guard_capture_material(actual.staged, actual.previous, now=actual.staged.observed_at))


def test_input_mutation_cannot_change_encoded_packet_and_decodes_are_detached():
    with fixture() as (_, staged, encoded):
        prior = encoded.payloads['packet']
        first = decode(encoded)
        object.__setattr__(staged.anchor, 'cash_krw', D('1'))
        object.__setattr__(first.staged.anchor, 'cash_krw', D('2'))
        second = decode(encoded)
        assert encoded.payloads['packet'] == prior
        assert second.staged.anchor.cash_krw not in (D('1'), D('2'))
        try:
            encoded.payloads['packet'] = b'changed'
        except TypeError:
            pass
        else:
            raise AssertionError('payload map mutable')


def test_original_collection_times_survive_utc_representation_without_refresh():
    with fixture() as (env, staged, _):
        shifted = replace(staged, observed_at=staged.observed_at.astimezone(timezone(timedelta(hours=9))))
        result = decode(F.build_capture_archive(shifted, env.state))
        assert result.staged.observed_at == staged.observed_at
        assert result.staged.observed_at.utcoffset() == timedelta(0)
        assert result.staged.collection_clock == staged.collection_clock
        assert result.staged.preview.coverage.verified_at == staged.preview.coverage.verified_at


def test_packet_noncanonical_bytes_duplicate_keys_and_extra_top_fields_refuse():
    with fixture() as (_, _, encoded):
        for raw in (b' '+encoded.payloads['packet'], encoded.payloads['packet']+b'\n',
                    b'{"schema_version":1,'+encoded.payloads['packet'][1:]):
            values = dict(encoded.payloads, packet=raw)
            refused(lambda: decode(encoded, payloads=values), 'CAPTURE_FORMAT_INVALID')
        values = edited(encoded, lambda b: b.update(extra=False))
        refused(lambda: decode(encoded, payloads=values), 'CAPTURE_FORMAT_INVALID')


def test_unknown_class_tag_extra_fields_and_dataclass_type_substitution_refuse():
    with fixture() as (_, _, encoded):
        mutations = (
            lambda b: stage(b)['anchor'].update({'$': 'os.system'}),
            lambda b: stage(b)['anchor']['v'].update(extra=False),
            lambda b: stage(b)['anchor'].update({'$': 'CoverageEvidence'}),
            lambda b: b.update(schema_version=True),
            lambda b: b.update(replay_revision='future-unapproved'))
        for mutate in mutations:
            values = edited(encoded, mutate)
            refused(lambda: decode(encoded, payloads=values), 'CAPTURE_FORMAT_INVALID')


def test_bool_integer_decimal_and_string_fields_are_not_interchangeable():
    with fixture() as (_, _, encoded):
        mutations = (
            lambda b: preview(b)['path']['v'].update(first_sequence=True),
            lambda b: stage(b)['capture']['v']['accounts']['v'][0]['v']['restrictions']['v'].update(auto_loan=0),
            lambda b: stage(b)['anchor']['v'].update(cash_krw='100000'),
            lambda b: stage(b)['anchor']['v'].update(cash_krw=100000),
            lambda b: stage(b)['anchor']['v'].update(cash_krw={'$': 'decimal', 'v': [False, '1', 0]}))
        for mutate in mutations:
            values = edited(encoded, mutate)
            refused(lambda: decode(encoded, payloads=values), 'CAPTURE_FORMAT_INVALID')


def test_illegal_decimal_spelling_nonfinite_or_float_never_decodes():
    with fixture() as (_, _, encoded):
        for parts in ([0, '01', 0], [0, '', 0], [0, '1', 513], [0, '1'*513, 0], [0, '\u0661', 0], [2, '1', 0]):
            values = edited(encoded, lambda b: stage(b)['anchor']['v'].update(cash_krw={'$': 'decimal', 'v': parts}))
            refused(lambda: decode(encoded, payloads=values), 'CAPTURE_FORMAT_INVALID')
        for raw in (b'{"schema_version":1.0}', b'{"schema_version":NaN}'):
            refused(lambda: decode(encoded, payloads=dict(encoded.payloads, packet=raw)), 'CAPTURE_FORMAT_INVALID')


def test_naive_noncanonical_datetime_and_date_tag_substitution_refuse():
    with fixture() as (_, _, encoded):
        for stamp in ('2026-10-26T20:00:00', '2026-10-26T20:00:00Z', '2026-10-26T20:00:00+09:00'):
            values = edited(encoded, lambda b: stage(b).update(observed_at={'$': 'datetime', 'v': stamp}))
            refused(lambda: decode(encoded, payloads=values), 'CAPTURE_FORMAT_INVALID')
        values = edited(encoded, lambda b: b['previous']['v'].update(first_trading_day={'$': 'datetime', 'v': '2026-10-26T00:00:00+00:00'}))
        refused(lambda: decode(encoded, payloads=values), 'CAPTURE_FORMAT_INVALID')


def test_lists_and_constructor_normalization_are_not_lossless_decoding():
    with fixture() as (_, _, encoded):
        values = edited(encoded, lambda b: receipt(b).update(params=receipt(b)['params']['v']))
        refused(lambda: decode(encoded, payloads=values), 'CAPTURE_FORMAT_INVALID')
        # EvidencePage normally recomputes empty digest. Decoder must reject that repair.
        values = edited(encoded, lambda b: stage(b)['capture']['v']['accounts']['v'][0]['v']['pages']['v'][0]['v'].update(page_sha256=''))
        refused(lambda: decode(encoded, payloads=values), 'CAPTURE_FORMAT_INVALID')


def test_raw_references_must_match_every_receipt_position_not_just_existing_key():
    with fixture() as (_, _, encoded):
        assert len(encoded.inventory) > 3
        values = edited(encoded, lambda b: receipt(b).update(raw_body={'$': 'receipt', 'v': 'receipt-000001'}))
        refused(lambda: decode(encoded, payloads=values), 'CAPTURE_FORMAT_INVALID')
        values = edited(encoded, lambda b: stage(b)['anchor']['v'].update(cash_krw={'$': 'receipt', 'v': 'receipt-000000'}))
        refused(lambda: decode(encoded, payloads=values), 'CAPTURE_FORMAT_INVALID')


def test_payload_missing_extra_renamed_or_changed_bytes_are_refused():
    with fixture() as (_, _, encoded):
        missing = dict(encoded.payloads); missing.pop('receipt-000000')
        extra = dict(encoded.payloads, unexpected=b'anything')
        renamed = dict(encoded.payloads); renamed['receipt-999999'] = renamed.pop('receipt-000000')
        changed = dict(encoded.payloads); changed['receipt-000000'] += b' '
        for values in (missing, extra, renamed, changed):
            refused(lambda: decode(encoded, payloads=values))


def test_inventory_type_length_hash_order_and_extra_field_bind_complete_packet():
    with fixture() as (_, _, encoded):
        mutations = (
            lambda b: b['payloads'][0].update(byte_count=True),
            lambda b: b['payloads'][0].update(sha256='f'*64),
            lambda b: b['payloads'][0].update(extra=0),
            lambda b: b['payloads'].reverse(),
            lambda b: b['payloads'].pop())
        for mutate in mutations:
            values = edited(encoded, mutate)
            refused(lambda: decode(encoded, payloads=values), 'CAPTURE_PAYLOAD_MISMATCH')


def test_explicit_predecessor_digest_and_actual_baseline_integrity_are_required():
    with fixture() as (_, _, encoded):
        refused(lambda: decode(encoded, expected='f'*64), 'CAPTURE_BASELINE_MISMATCH')
        for expected in (None, True, 'F'*64, 'bad'):
            refused(lambda: F.parse_capture_archive(encoded.payloads, expected_previous_state_sha256=expected), 'CAPTURE_BASELINE_MISMATCH')
        values = edited(encoded, lambda b: b['previous']['v'].update(high_watermark={'$': 'decimal', 'v': [0, '1', 0]}))
        refused(lambda: decode(encoded, payloads=values), 'CAPTURE_BASELINE_MISMATCH')


def test_legacy_baseline_bytes_must_match_typed_predecessor_even_with_new_payload_hash():
    with fixture() as (_, _, encoded):
        values = dict(encoded.payloads)
        values['baseline'] += b' '
        body = json.loads(values['packet'])
        body['payloads'][0].update(byte_count=len(values['baseline']), sha256=hashlib.sha256(values['baseline']).hexdigest())
        values['packet'] = json.dumps(body, sort_keys=True, separators=(',', ':')).encode()
        refused(lambda: decode(encoded, payloads=values), 'CAPTURE_BASELINE_MISMATCH')


def test_extra_or_deleted_dataclass_fields_refuse_before_dynamic_payload_traversal():
    with fixture() as (env, staged, _):
        extra = deepcopy(staged)
        object.__setattr__(extra.anchor, 'unexpected', object())
        refused(lambda: F.build_capture_archive(extra, env.state), 'CAPTURE_FORMAT_INVALID')
        missing = deepcopy(staged)
        object.__delattr__(missing.anchor, 'cash_krw')
        refused(lambda: F.build_capture_archive(missing, env.state), 'CAPTURE_FORMAT_INVALID')
        for value in (D('NaN'), D('Infinity'), D('1E+513')):
            changed = replace(staged, anchor=replace(staged.anchor, cash_krw=value))
            refused(lambda: F.build_capture_archive(changed, env.state), 'CAPTURE_FORMAT_INVALID')


def test_raw_count_single_and_aggregate_limits_have_exact_boundaries():
    with fixture() as (env, staged, encoded):
        receipts = staged.capture.receipts
        largest = max(len(value.raw_body) for value in receipts)
        total = sum(len(value.raw_body) for value in receipts)
        limits = replace(F.DEFAULT_LIMITS, max_receipts=len(receipts), max_receipt_bytes=largest,
                         max_total_receipt_bytes=total)
        assert F.build_capture_archive(staged, env.state, limits=limits).packet_sha256 == encoded.packet_sha256
        for limited in (replace(limits, max_receipts=len(receipts)-1),
                        replace(limits, max_receipt_bytes=largest-1), replace(limits, max_total_receipt_bytes=total-1)):
            refused(lambda: F.build_capture_archive(staged, env.state, limits=limited), 'CAPTURE_RESOURCE_LIMIT')
            refused(lambda: decode(encoded, limits=limited), 'CAPTURE_RESOURCE_LIMIT')


def test_packet_predecessor_and_whole_payload_byte_limits_have_exact_boundaries():
    with fixture() as (env, staged, encoded):
        limits = replace(F.DEFAULT_LIMITS, max_packet_bytes=len(encoded.payloads['packet']),
            max_baseline_bytes=len(encoded.payloads['baseline']), max_total_bytes=sum(map(len, encoded.payloads.values())))
        assert F.build_capture_archive(staged, env.state, limits=limits).packet_sha256 == encoded.packet_sha256
        for field in ('max_packet_bytes', 'max_baseline_bytes', 'max_total_bytes'):
            lower = replace(limits, **{field: getattr(limits, field)-1})
            refused(lambda: decode(encoded, limits=lower), 'CAPTURE_RESOURCE_LIMIT')


def test_invalid_limits_including_deleted_slot_are_fixed_before_encoding_or_parsing():
    with fixture() as (env, staged, encoded):
        for name, maximum in F._LIMIT_CEILINGS:
            for value in (True, 0, maximum+1):
                refused(lambda: replace(F.DEFAULT_LIMITS, **{name: value}), 'CAPTURE_LIMITS_INVALID')
        broken = replace(F.DEFAULT_LIMITS)
        object.__delattr__(broken, 'max_packet_bytes')
        for action in (lambda: F.build_capture_archive(staged, env.state, limits=broken),
                       lambda: decode(encoded, limits=broken), lambda: decode(encoded, limits=object())):
            refused(action, 'CAPTURE_LIMITS_INVALID')


def test_oversized_and_deep_json_admission_precedes_json_loads():
    with fixture() as (_, _, encoded):
        for raw, limits in ((b' '*100, replace(F.DEFAULT_LIMITS, max_packet_bytes=99)),
                            (b'['*100+b']'*100, F.DEFAULT_LIMITS),
                            (b'"'+b'x'*(12*65536+3)+b'"', F.DEFAULT_LIMITS)):
            with patch.object(F.json, 'loads', side_effect=AssertionError('parsed before admission')):
                refused(lambda: decode(encoded, payloads=dict(encoded.payloads, packet=raw), limits=limits), 'CAPTURE_RESOURCE_LIMIT')


def test_tuple_and_scalar_admission_precedes_metadata_json_encoder():
    with fixture() as (env, staged, _):
        too_many = replace(staged, trade_fees=(staged.anchor,)*100001)
        too_large = replace(staged, anchor=replace(staged.anchor, account_scope='x'*65537))
        with patch.object(F, '_json_bytes', side_effect=AssertionError('encoded before typed admission')):
            for changed in (too_many, too_large):
                refused(lambda: F.build_capture_archive(changed, env.state), 'CAPTURE_RESOURCE_LIMIT')


def test_bounded_nodes_text_and_semantic_depth_are_independent_admission_limits():
    with fixture() as (env, staged, encoded):
        for limits in (replace(F.DEFAULT_LIMITS, max_nodes=1), replace(F.DEFAULT_LIMITS, max_text_bytes=1),
                       replace(F.DEFAULT_LIMITS, max_depth=1), replace(F.DEFAULT_LIMITS, max_rows=1)):
            refused(lambda: F.build_capture_archive(staged, env.state, limits=limits), 'CAPTURE_RESOURCE_LIMIT')
            refused(lambda: decode(encoded, limits=limits), 'CAPTURE_RESOURCE_LIMIT')


def test_no_source_callback_clock_baseline_advancement_or_material_audit_during_codec():
    with fixture() as (env, staged, encoded):
        with patch.object(M, 'prepare_guard_capture_material', side_effect=AssertionError('audit during codec')), \
             patch.object(F.B, 'advance_baseline', side_effect=AssertionError('state advanced')):
            assert F.build_capture_archive(staged, env.state).packet_sha256 == encoded.packet_sha256
            assert decode(encoded).previous.state_digest == env.state.state_digest


def test_underreported_mapping_cannot_bypass_incremental_item_count_bound():
    class Miscounted(Mapping):
        def __len__(self): return 1
        def __iter__(self): raise AssertionError('items path expected')
        def __getitem__(self, key): raise AssertionError('items path expected')
        def items(self):
            yield 'baseline', b'x'
            yield 'packet', b'x'
            yield 'receipt-000000', b'x'
            yield 'receipt-000001', b'x'
            raise AssertionError('iterated past refused count')
    refused(lambda: F.parse_capture_archive(Miscounted(), expected_previous_state_sha256='a'*64,
        limits=replace(F.DEFAULT_LIMITS, max_receipts=1)), 'CAPTURE_RESOURCE_LIMIT')


def test_astral_unicode_exact_scalar_limit_roundtrips_ensure_ascii_surrogates():
    with fixture() as (env, staged, _):
        original = '\U0001f680'*65536
        changed = replace(staged, preview=replace(staged.preview,
            path=replace(staged.preview.path, stream_epoch=original)))
        encoded = F.build_capture_archive(changed, env.state)
        assert decode(encoded).staged.preview.path.stream_epoch == original
        assert b'\\ud83d\\ude80' in encoded.payloads['packet']


def test_receipt_subfield_and_aggregate_page_row_limits_apply_before_encoding():
    with fixture() as (env, staged, _):
        for name, value in (('path', 'x'*129), ('account_scope', 'x'*129), ('params', (('x'*129, 'y'),))):
            first = replace(staged.capture.receipts[0], **{name: value})
            changed = replace(staged, capture=replace(staged.capture, receipts=(first,)+staged.capture.receipts[1:]))
            refused(lambda: F.build_capture_archive(changed, env.state), 'CAPTURE_RESOURCE_LIMIT')
        account = staged.capture.accounts[0]
        row = next(row for page in account.pages for row in page.rows)
        pages = tuple(replace(page, rows=(row,)*40000, page_sha256='a'*64) for page in account.pages)
        assert len(pages) == 3
        changed = replace(staged, capture=replace(staged.capture, accounts=(replace(account, pages=pages),)))
        with patch.object(F, '_json_bytes', side_effect=AssertionError('encoded before page aggregate bound')):
            refused(lambda: F.build_capture_archive(changed, env.state), 'CAPTURE_RESOURCE_LIMIT')
