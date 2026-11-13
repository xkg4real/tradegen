"""Pure generation metadata cases; invented hashes/claims are never authority.

No account/source verifier, clock, filesystem, commit, owner or transport runs.
Actual capture/package/archive integration is covered by the adapter's fixtures.
"""
from dataclasses import FrozenInstanceError, fields, replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import hashlib
import json
from unittest.mock import patch

from execution_control.risk import RiskPolicy, RecoveryCondition
from execution_launch.continuous_guard import OwnerContextClaim
from execution_launch.continuous_guard_commit import GuardCommitReceipt
from execution_launch import guard_capture_format as C
from execution_launch import guard_generation_format as F

D = Decimal
T0 = datetime(2026, 11, 13, 3, 4, 5, 6007, tzinfo=timezone.utc)


def sha(label):
    return hashlib.sha256(label.encode('ascii')).hexdigest()


def policy():
    return RiskPolicy(version='fixture-v1', initial_equity=D('100.00'),
        drawdown_activation_equity=D('6E+3'), positive_profit_loss_fraction=D('.35'),
        peak_drawdown_fraction=D('.35'), zero_profit_day_target_fraction=D('.30'))


def claim(label, observed_at=T0):
    return OwnerContextClaim(owner_head_sha256=sha(label+'-owner'), code_sha256=sha('code'),
        code_approval_sha256=sha('code-approval'), signed_floor_krw=D('100.00'),
        signed_daily_loss_krw=D('10.0'), observed_at=observed_at, source_sha256=sha(label+'-source'))


def input_record(**changes):
    values = dict(schema_version=1, kind='GUARD_INPUT', replay_revision='guard-capture-material-v1',
        capture_archive_digest=sha('capture-archive'), capture_packet_sha256=sha('capture-packet'),
        capture_material_sha256=sha('capture-material'), previous_state_sha256=sha('previous'),
        expected_guard_head=sha('old-guard'), expected_baseline_head=sha('old-baseline'),
        expected_control_head=sha('old-control'), package_sha256=sha('whole-package'),
        input_sha256=sha('guard-input'), policy=policy(), owner_before=claim('before', T0-timedelta(seconds=2)),
        owner_after=claim('after'), evaluated_at=T0+timedelta(seconds=1))
    values.update(changes)
    return F.GuardInputRecord(**values)


def completion_record(**changes):
    values = dict(schema_version=1, kind='GUARD_COMPLETION', input_archive_digest=sha('input-archive'),
        input_record_sha256=sha('input-record'), package_sha256=sha('whole-package'),
        input_sha256=sha('guard-input'), receipt=GuardCommitReceipt(transaction_id=sha('transaction'),
            guard_head=sha('new-guard'), baseline_head=sha('new-baseline'),
            control_head=sha('receipt-prefix'), permanently_halted=True, replayed=False),
        completion_head=sha('complete-row'), observed_control_head=sha('observed-tail'),
        recorded_at=T0+timedelta(seconds=5))
    values.update(changes)
    return F.GuardCompletionRecord(**values)


def canonical(body):
    return json.dumps(body, sort_keys=True, separators=(',', ':'), ensure_ascii=True,
                      allow_nan=False).encode('ascii')


def refused(call, code='GENERATION_FORMAT_INVALID'):
    try:
        call()
    except F.GuardGenerationFormatError as exc:
        assert str(exc) == code, (str(exc), code)
        return
    raise AssertionError('expected fixed metadata refusal')


def edited(record, change, *, completion=False):
    body = json.loads(F.completion_bytes(record) if completion else F.input_bytes(record))
    change(body)
    return canonical(body)


def test_exact_input_golden_document_and_domain_digest():
    # Independent explicit field/number/time wire, not a serialization of dataclass fields.
    wire_policy = {'version':'fixture-v1', 'initial_equity':{'$':'decimal','v':[0,'10000',-2]},
        'drawdown_activation_equity':{'$':'decimal','v':[0,'6',3]},
        'positive_profit_loss_fraction':{'$':'decimal','v':[0,'35',-2]},
        'peak_drawdown_fraction':{'$':'decimal','v':[0,'35',-2]},
        'zero_profit_day_target_fraction':{'$':'decimal','v':[0,'30',-2]},
        'first_day_loss_budget':None, 'zero_profit_day_loss_budget':None,
        'valuation_convention':'marked_equity', 'daily_loss_convention':'externally_reconciled',
        'recovery_condition':None}
    def wire_owner(label, instant):
        return {'owner_head_sha256':sha(label+'-owner'), 'code_sha256':sha('code'),
            'code_approval_sha256':sha('code-approval'),
            'signed_floor_krw':{'$':'decimal','v':[0,'10000',-2]},
            'signed_daily_loss_krw':{'$':'decimal','v':[0,'100',-1]},
            'observed_at':{'$':'datetime','v':instant}, 'source_sha256':sha(label+'-source')}
    expected = canonical({'schema_version':1, 'kind':'GUARD_INPUT',
        'replay_revision':'guard-capture-material-v1', 'capture_archive_digest':sha('capture-archive'),
        'capture_packet_sha256':sha('capture-packet'), 'capture_material_sha256':sha('capture-material'),
        'previous_state_sha256':sha('previous'), 'expected_guard_head':sha('old-guard'),
        'expected_baseline_head':sha('old-baseline'), 'expected_control_head':sha('old-control'),
        'package_sha256':sha('whole-package'), 'input_sha256':sha('guard-input'),
        'policy':wire_policy, 'owner_before':wire_owner('before','2026-11-13T03:04:03.006007+00:00'),
        'owner_after':wire_owner('after','2026-11-13T03:04:05.006007+00:00'),
        'evaluated_at':{'$':'datetime','v':'2026-11-13T03:04:06.006007+00:00'}})
    record = input_record()
    assert F.input_bytes(record) == expected
    assert F.input_bytes(F.parse_input(expected)) == expected
    assert F.input_digest(record) == hashlib.sha256(b'tradegen-guard-generation-input/1\n'+expected).hexdigest()
    assert F.input_digest(record) != hashlib.sha256(expected).hexdigest()


def test_exact_completion_golden_preserves_receipt_complete_and_observed_prefix_roles():
    record = completion_record()
    expected = canonical({'schema_version':1, 'kind':'GUARD_COMPLETION',
        'input_archive_digest':sha('input-archive'), 'input_record_sha256':sha('input-record'),
        'package_sha256':sha('whole-package'), 'input_sha256':sha('guard-input'),
        'receipt':{'transaction_id':sha('transaction'), 'guard_head':sha('new-guard'),
            'baseline_head':sha('new-baseline'), 'control_head':sha('receipt-prefix'),
            'permanently_halted':True, 'replayed':False},
        'completion_head':sha('complete-row'), 'observed_control_head':sha('observed-tail'),
        'recorded_at':{'$':'datetime','v':'2026-11-13T03:04:10.006007+00:00'}})
    assert F.completion_bytes(record) == expected
    parsed = F.parse_completion(expected)
    assert len({parsed.receipt.control_head, parsed.completion_head, parsed.observed_control_head}) == 3
    assert {f.name for f in fields(parsed.receipt)} == {
        'transaction_id','guard_head','baseline_head','control_head','permanently_halted','replayed'}
    assert F.completion_digest(record) == hashlib.sha256(b'tradegen-guard-generation-completion/1\n'+expected).hexdigest()
    assert F.completion_bytes(parsed) == expected


def test_decimal_sign_scale_and_positive_exponent_survive_all_nested_paths():
    digests = set()
    for amount in (D('-0.00'), D('0.00'), D('1E+2'), D('100'), D('100.000')):
        record = input_record(policy=replace(policy(), initial_equity=amount),
                              owner_before=replace(claim('before'), signed_floor_krw=amount))
        parsed = F.parse_input(F.input_bytes(record))
        assert parsed.policy.initial_equity.as_tuple() == amount.as_tuple()
        assert parsed.owner_before.signed_floor_krw.as_tuple() == amount.as_tuple()
        digests.add(F.input_digest(record))
    assert len(digests) == 5


def test_original_instants_normalize_to_utc_without_becoming_recording_time():
    offset = timezone(timedelta(hours=9))
    original = input_record(evaluated_at=T0.astimezone(offset),
        owner_after=claim('after', (T0-timedelta(seconds=1)).astimezone(offset)))
    restored = F.parse_input(F.input_bytes(original))
    assert restored.evaluated_at == T0 and restored.evaluated_at.utcoffset() == timedelta(0)
    assert restored.owner_after.observed_at == T0-timedelta(seconds=1)
    completion = completion_record(recorded_at=T0+timedelta(days=1))
    assert F.parse_completion(F.completion_bytes(completion)).recorded_at == T0+timedelta(days=1)
    assert restored.evaluated_at != completion.recorded_at


def test_optional_values_are_explicit_and_supported_recovery_condition_is_lossless():
    record = input_record(policy=replace(policy(), first_day_loss_budget=D('-0.0'),
        zero_profit_day_loss_budget=D('12.000'), recovery_condition=RecoveryCondition(
            cutoff_seconds=79200, timezone='Asia/Seoul', reference='day_start_marked_equity')))
    actual = F.parse_input(F.input_bytes(record)).policy
    assert actual.first_day_loss_budget.as_tuple() == D('-0.0').as_tuple()
    assert actual.zero_profit_day_loss_budget.as_tuple() == D('12.000').as_tuple()
    assert actual.recovery_condition == record.policy.recovery_condition
    for field in ('first_day_loss_budget','zero_profit_day_loss_budget','recovery_condition'):
        raw = edited(input_record(), lambda b, field=field: b['policy'].pop(field))
        refused(lambda: F.parse_input(raw))


def test_record_construction_detaches_nested_objects_without_arbitrary_copy_hooks():
    before, after, pol = claim('before'), claim('after'), policy()
    receipt = completion_record().receipt
    record = input_record(policy=pol, owner_before=before, owner_after=after)
    complete = completion_record(receipt=receipt)
    prior, prior_complete = F.input_bytes(record), F.completion_bytes(complete)
    object.__setattr__(pol, 'initial_equity', D('999'))
    object.__setattr__(before, 'signed_floor_krw', D('999'))
    object.__setattr__(after, 'observed_at', T0+timedelta(days=1))
    object.__setattr__(receipt, 'control_head', sha('changed'))
    assert F.input_bytes(record) == prior and F.completion_bytes(complete) == prior_complete
    assert record.policy is not pol and record.owner_after is not after and complete.receipt is not receipt
    try:
        record.kind = 'changed'
    except FrozenInstanceError:
        pass
    else:
        raise AssertionError('record is mutable')


def test_unknown_nested_attributes_and_subclasses_are_rejected_before_copying():
    class Trap:
        def __deepcopy__(self, memo):
            raise AssertionError('arbitrary copy hook called')
        def __repr__(self):
            raise AssertionError('arbitrary repr called')
    for obj, field in ((policy(),'policy'), (claim('before'),'owner_before'),
                       (completion_record().receipt,'receipt')):
        object.__setattr__(obj, 'extra', Trap())
        factory = completion_record if field == 'receipt' else input_record
        refused(lambda obj=obj, field=field, factory=factory: factory(**{field:obj}))
    calls = []
    class FieldKey:
        def __hash__(self):
            calls.append('hash'); return 0
    pol = policy()
    vars(pol).pop('version'); vars(pol)[FieldKey()] = 'fixture-v1'
    calls.clear()
    refused(lambda: input_record(policy=pol))
    assert not calls  # Even a same-size malformed attribute map executes no key hook.
    class ForeignPolicy(RiskPolicy):
        pass
    refused(lambda: input_record(policy=ForeignPolicy(**vars(policy()))))
    class ForeignRecord(F.GuardInputRecord):
        pass
    values = {f.name:getattr(input_record(),f.name) for f in fields(F.GuardInputRecord)}
    refused(lambda: ForeignRecord(**values))


def test_missing_nested_attributes_deleted_slots_and_replaced_types_are_fixed_refusals():
    pol = policy(); object.__delattr__(pol, 'version')
    refused(lambda: input_record(policy=pol))
    record = input_record(); object.__delattr__(record, 'capture_archive_digest')
    refused(lambda: F.input_bytes(record))
    complete = completion_record(); object.__setattr__(complete, 'receipt', {})
    refused(lambda: F.completion_bytes(complete))
    record = input_record(); object.__setattr__(record.owner_after, 'signed_floor_krw', True)
    refused(lambda: F.input_bytes(record))


def test_bool_is_not_int_or_decimal_and_receipt_flags_are_exact_bool():
    for bad in (True, 1.0, D(1), '1'):
        refused(lambda bad=bad: input_record(schema_version=bad))
    for bad in (True, 1, 1.0, '1'):
        refused(lambda bad=bad: input_record(policy=replace(policy(), initial_equity=bad)))
    for field in ('permanently_halted','replayed'):
        for bad in (0, 1, None, 'false'):
            receipt = replace(completion_record().receipt, **{field:bad})
            refused(lambda receipt=receipt: completion_record(receipt=receipt))


def test_closed_revision_kind_and_every_hash_field_are_enforced():
    for changes in ({'schema_version':2}, {'kind':'GUARD_COMPLETION'}, {'replay_revision':'future'},
                    {'kind':'GUARD_INPUT\n'}):
        refused(lambda changes=changes: input_record(**changes))
    record = input_record()
    for field in fields(record):
        if field.name.endswith(('_sha256','_digest','_head')):
            for bad in ('A'*64, 'a'*63, 'a'*65, b'a'*64, 'g'*64):
                refused(lambda field=field, bad=bad: replace(record, **{field.name:bad}))
    for field in ('transaction_id','guard_head','baseline_head','control_head'):
        refused(lambda field=field: completion_record(receipt=replace(
            completion_record().receipt, **{field:'A'*64})))


def test_supported_condition_and_optional_budget_rules_are_not_relaxed():
    good = RecoveryCondition(cutoff_seconds=79200, timezone='Asia/Seoul', reference='day_start_marked_equity')
    for changes in ({'cutoff_seconds':True}, {'cutoff_seconds':79199}, {'timezone':'UTC'},
                    {'reference':'latest_equity'}):
        refused(lambda changes=changes: input_record(policy=replace(policy(),
            recovery_condition=replace(good, **changes))))
    for field in ('first_day_loss_budget','zero_profit_day_loss_budget'):
        refused(lambda field=field: input_record(policy=replace(policy(), **{field:D('-0.01')})))


def test_owner_claim_amount_semantics_are_preserved_without_authenticating_it():
    for field, amounts in (('signed_floor_krw',(D('-1'), D('1E+41'), D('1E-41'), D('1'*61))),
                           ('signed_daily_loss_krw',(D('0'), D('-0.00'), D('-1')))):
        for amount in amounts:
            refused(lambda field=field, amount=amount: input_record(owner_after=replace(
                claim('after'), **{field:amount})))
    # Syntactically valid invented claims are accepted as data, not a current owner issuer.
    record = input_record(owner_after=claim('entirely-invented'))
    assert not any(hasattr(record, name) for name in ('verified_owner','execution_ready','permit','source_authenticated'))
    assert record.owner_after.source_sha256 == sha('entirely-invented-source')


def test_finite_decimal_bounds_precede_any_expanding_formatting():
    for amount in (D('NaN'), D('sNaN'), D('Infinity'), D('-Infinity')):
        refused(lambda amount=amount: input_record(policy=replace(policy(), initial_equity=amount)))
    for amount in (D('1E+1000000000'), D('1E-1000000000'), D('1'*513), D('1'*100000)):
        with patch.object(C._Codec, 'value', side_effect=AssertionError('scalar helper entered before admission')):
            refused(lambda amount=amount: input_record(policy=replace(policy(), initial_equity=amount)),
                    'GENERATION_RESOURCE_LIMIT')
    for amount in (D('1E+512'), D('1E-512'), D('1'*512)):
        record = input_record(policy=replace(policy(), initial_equity=amount))
        assert F.parse_input(F.input_bytes(record)).policy.initial_equity.as_tuple() == amount.as_tuple()


def test_naive_invalid_and_subclass_datetimes_are_refused():
    class ForeignDatetime(datetime):
        pass
    for bad in (T0.replace(tzinfo=None), T0.replace(year=1), T0.replace(year=9999),
                ForeignDatetime(2026,11,13,tzinfo=timezone.utc), '2026-11-13', None):
        refused(lambda bad=bad: input_record(evaluated_at=bad))
        refused(lambda bad=bad: completion_record(recorded_at=bad))
    raw = edited(input_record(), lambda b: b['owner_after']['observed_at'].update(v='2026-99-13T00:00:00+00:00'))
    refused(lambda: F.parse_input(raw))


def test_noncanonical_duplicate_unknown_and_missing_json_fields_refuse():
    raw = F.input_bytes(input_record())
    for bad in (b' '+raw, raw+b'\n', b'{"schema_version":1,'+raw[1:],
                raw.replace(b':',b': ',1), b'\xff'+raw):
        refused(lambda bad=bad: F.parse_input(bad))
    for is_completion, change in ((False,lambda b: b.update(extra=1)),
                   (False,lambda b: b.pop('input_sha256')),
                   (False,lambda b: b['owner_before'].update(extra=False)),
                   (True,lambda b: b['receipt'].update(recorded_at='not-a-receipt-field'))):
        record = completion_record() if is_completion else input_record()
        altered = edited(record, change, completion=is_completion)
        refused(lambda altered=altered, is_completion=is_completion:
            (F.parse_completion if is_completion else F.parse_input)(altered))


def test_unknown_scalar_tags_noncanonical_scalars_and_raw_json_numbers_refuse():
    record = input_record()
    for tagged in ({'$':'Decimal','v':[0,'1',0]}, {'$':'decimal','v':[True,'1',0]},
                   {'$':'decimal','v':[0,'01',0]}, {'$':'decimal','v':[0,'1',True]},
                   {'$':'decimal','v':[0,'1',513]}, {'$':'decimal','v':[0,'1',0],'extra':0},
                   1, True, None):
        raw = edited(record, lambda b, tagged=tagged: b['policy'].update(initial_equity=tagged))
        refused(lambda raw=raw: F.parse_input(raw))
    for value in (b'1.0', b'1e0', b'NaN', b'Infinity', b'-Infinity'):
        raw = F.input_bytes(record).replace(b'"schema_version":1', b'"schema_version":'+value)
        refused(lambda raw=raw: F.parse_input(raw))
    for instant in ('2026-11-13T03:04:06.006007Z','2026-11-13T12:04:06.006007+09:00'):
        raw = edited(record, lambda b, instant=instant: b['evaluated_at'].update(v=instant))
        refused(lambda raw=raw: F.parse_input(raw))


def test_record_byte_depth_node_and_text_preflight_happens_before_json_allocation():
    samples = (b' '*65537, b'['*13+b'null'+b']'*13,
               b'['+b','.join([b'null']*2048)+b']', b'"'+b'a'*16385+b'"')
    with patch.object(F.json, 'loads', side_effect=AssertionError('JSON parser entered before admission')):
        for raw in samples:
            refused(lambda raw=raw: F.parse_input(raw), 'GENERATION_RESOURCE_LIMIT')
    for raw in (bytearray(b'{}'), '{}', memoryview(b'{}')):
        refused(lambda raw=raw: F.parse_input(raw))
    refused(lambda: F.parse_input(b''), 'GENERATION_RESOURCE_LIMIT')


def _budgets(document):
    nodes, text, maximum_depth = 0, 0, 0
    pending = [(document,0)]
    while pending:
        value, depth = pending.pop(); nodes += 1
        if type(value) is str:
            text += len(value)
        elif type(value) in (dict,list):
            depth += 1; maximum_depth = max(maximum_depth,depth)
            if type(value) is dict:
                pending.extend((item,depth) for pair in value.items() for item in pair)
            else:
                pending.extend((item,depth) for item in value)
    return dict(max_nodes=nodes,max_text_bytes=text,max_depth=maximum_depth)


def test_exact_record_and_structure_budget_boundaries_are_symmetric():
    for record, encode, parse in ((input_record(),F.input_bytes,F.parse_input),
                                   (completion_record(),F.completion_bytes,F.parse_completion)):
        raw = encode(record)
        limits = dict(max_record_bytes=len(raw), **_budgets(json.loads(raw)))
        exact = F.GenerationFormatLimits(**limits)
        assert encode(record,limits=exact) == raw and encode(parse(raw,limits=exact)) == raw
        for name,value in limits.items():
            too_small = F.GenerationFormatLimits(**dict(limits,**{name:value-1}))
            refused(lambda: encode(record,limits=too_small),'GENERATION_RESOURCE_LIMIT')
            refused(lambda: parse(raw,limits=too_small),'GENERATION_RESOURCE_LIMIT')


def test_limits_cannot_expand_hard_ceilings_accept_bool_or_hide_deleted_slots():
    for name,maximum in (('max_record_bytes',65536),('max_nodes',2048),('max_text_bytes',16384),('max_depth',12)):
        for bad in (0,-1,True,1.0,maximum+1):
            refused(lambda name=name,bad=bad: F.GenerationFormatLimits(**{name:bad}),'GENERATION_LIMITS_INVALID')
    for bad in (None,{},C.DEFAULT_LIMITS):
        refused(lambda bad=bad:F.input_bytes(input_record(),limits=bad),'GENERATION_LIMITS_INVALID')
    limits = F.GenerationFormatLimits(); object.__delattr__(limits,'max_nodes')
    refused(lambda:F.parse_input(b'{}',limits=limits),'GENERATION_LIMITS_INVALID')


def test_bounded_integer_parse_and_overlong_typed_scalars_are_fixed_refusals():
    refused(lambda:F.parse_input(b'{"schema_version":'+b'9'*81+b'}'),'GENERATION_RESOURCE_LIMIT')
    refused(lambda:input_record(policy=replace(policy(),version='a'*129)))
    raw = edited(input_record(),lambda b:b['policy']['initial_equity'].update(v=[0,'1'*513,0]))
    refused(lambda:F.parse_input(raw))
    raw = edited(input_record(),lambda b:b['evaluated_at'].update(v='x'*41))
    refused(lambda:F.parse_input(raw))


def test_receipt_replay_flag_and_each_record_observation_have_distinct_identity():
    original = completion_record()
    digest = F.completion_digest(original)
    for changes in ({'receipt':replace(original.receipt,replayed=True)},
                    {'receipt':replace(original.receipt,control_head=sha('later-receipt-prefix'))},
                    {'completion_head':sha('another-complete')},
                    {'observed_control_head':sha('later-observed-prefix')},
                    {'recorded_at':original.recorded_at+timedelta(microseconds=1)}):
        assert F.completion_digest(replace(original,**changes)) != digest
    record = input_record()
    later = replace(record,evaluated_at=record.evaluated_at+timedelta(microseconds=1))
    # Existing package/input digest claims are preserved, not recalculated or relabelled here.
    assert later.input_sha256 == record.input_sha256 and later.package_sha256 == record.package_sha256
    assert F.input_digest(later) != F.input_digest(record)


def test_capture_registry_is_unchanged_and_returned_records_are_not_shared_cached_instances():
    before = dict(C._SCHEMAS)
    raw, complete = F.input_bytes(input_record()), F.completion_bytes(completion_record())
    a,b = F.parse_input(raw),F.parse_input(raw)
    c,d = F.parse_completion(complete),F.parse_completion(complete)
    assert a is not b and a.policy is not b.policy and a.owner_after is not b.owner_after
    assert c is not d and c.receipt is not d.receipt
    assert C._SCHEMAS == before and set(C._SCHEMAS) == set(before)
    assert not any(name in C._SCHEMAS for name in ('GuardInputRecord','GuardCompletionRecord','RiskPolicy','OwnerContextClaim'))
    assert 'signed_floor_krw' not in repr(a)
