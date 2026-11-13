"""Pure carry behavior boundaries over invented input; no state or authority."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal, localcontext
from types import SimpleNamespace

from execution_launch import managed_behavior as B
from execution_launch.program import ProgramSpec, target_fraction

D = Decimal
NOW = datetime(2026, 11, 13, tzinfo=timezone.utc)
SHA = 'a' * 64


def refused(call, code=None):
    try:
        call()
    except ValueError as exc:
        if code:
            assert str(exc) == code, (str(exc), code)
        return
    raise AssertionError('expected refusal')


def program():
    return ProgramSpec(schema_version=1, strategy_id='synthetic-carry', kind='moving_average_trend',
                       fast_window=1, slow_window=2, exposure_fraction=D('0.5'))


def decision(marks=('1', '2'), **changes):
    marks = tuple(D(v) for v in marks)
    options = dict(bar_index=len(marks)-1, decided_at=NOW, history_sha256=SHA)
    return B.derive_fixed_decision_v2(program(), marks, **(options | changes))


def test_behavior_dispatch_rejects_mixed_revisions_and_unsupported_universe():
    legacy = SimpleNamespace(schema_version=1, evaluator_revision='forward-paper-v1', universe_rule_sha256=None)
    assert B.resolve_behavior(legacy) == 'legacy-fixed-v1'
    universe = SimpleNamespace(schema_version=1, evaluator_revision='forward-universe-v1', universe_rule_sha256=SHA)
    assert B.resolve_behavior(universe) == 'legacy-universe-v1'
    carry = dict(schema_version=2, evaluator_revision=B.CARRY_EVALUATOR_REVISION,
                 behavior_revision=B.BEHAVIOR_REVISION, terminal_accounting=B.TERMINAL_ACCOUNTING,
                 management_behavior_sha256=B.behavior_digest(), universe_rule_sha256=None)
    assert B.resolve_behavior(SimpleNamespace(**carry)) == B.BEHAVIOR_REVISION
    for change in ({'schema_version': True}, {'schema_version': 1}, {'behavior_revision': None},
                   {'terminal_accounting': 'liquidate'}, {'management_behavior_sha256': 'b' * 64},
                   {'evaluator_revision': 'forward-universe-carry-v2'}, {'universe_rule_sha256': SHA}):
        refused(lambda: B.resolve_behavior(SimpleNamespace(**(carry | change))),
                'MANAGED_BEHAVIOR_REVISION_REQUIRED')


def test_behavior_document_copies_cannot_change_the_bound_contract():
    original = B.behavior_digest()
    changed = B.behavior_document()
    changed['scope'].append('margin')
    changed['deadline_action'] = 'sell'
    assert B.behavior_digest() == original
    assert B.behavior_document()['scope'] == ['upbit', 'spot', 'KRW', 'fixed', 'gtc']


def test_fixed_decisions_distinguish_warmup_valid_cash_long_and_unavailable():
    assert (decision(('1',)).state, decision(('1',)).target_fraction) == ('warmup', None)
    long = decision()
    assert (long.state, long.cause, long.target_fraction) == ('long_target', 'trend_above', D('0.5'))
    cash = decision(('2', '1'))
    assert (cash.state, cash.cause, cash.target_fraction) == ('cash_target', 'trend_not_above', D(0))
    unavailable = decision(input_status='unavailable')
    assert (unavailable.state, unavailable.cause, unavailable.target_fraction) == ('unavailable', 'input_unavailable', None)
    cash_program = replace(program(), kind='cash', fast_window=0, slow_window=0, exposure_fraction=D(0))
    constant = B.derive_fixed_decision_v2(cash_program, (D(1),), bar_index=0,
                                        decided_at=NOW, history_sha256=SHA)
    assert constant.cause == 'always_cash'
    assert target_fraction(program(), (D(1), D(2))) == D('0.5')
    assert target_fraction(program(), (D(2), D(1))) == 0


def test_malformed_prefix_is_never_relabelled_as_recorded_unavailable():
    for marks in (('NaN',), ('-1',), ('0',)):
        refused(lambda: decision(marks, input_status='unavailable'))
    refused(lambda: decision(bar_index=9), 'MANAGED_PREFIX_INVALID')
    refused(lambda: decision(input_status='provider-exception-text'), 'MANAGED_INPUT_STATUS_INVALID')


def test_decision_codec_binds_cause_prefix_time_revision_and_target():
    original = decision()
    document = B.decision_document(original)
    assert B.parse_decision_document(document) == original
    for change in ({'history_sha256': 'b' * 64}, {'bar_index': 3},
                   {'decided_at': NOW + timedelta(seconds=1)}, {'target_fraction': D('0.4')}):
        refused(lambda: B.decision_digest(replace(original, **change)), 'MANAGED_DECISION_DIGEST_MISMATCH')
    for change in ({'cause': 'input_unavailable'}, {'behavior_sha256': 'b' * 64}, {'schema_version': True}):
        refused(lambda: B.decision_digest(replace(original, **change)))
    for change in ({'target_fraction': '0.50'}, {'target_fraction': 0.5}, {'decided_at': NOW.isoformat()},
                   {'unreviewed_extra': 'x'}):
        refused(lambda: B.parse_decision_document(document | change))


def intent(value, *, cash='0', units='10', mark='10', slot=NOW, deadline=None):
    return B.derive_fixed_intent_v2(value, cash_quote=D(cash), units=D(units), mark=D(mark),
                                  slot=slot, deadline=deadline or NOW + timedelta(seconds=60))


def test_long_hold_never_creates_a_reducing_rebalance_even_over_target():
    value = intent(decision())
    assert value.action == 'hold' and not value.execution_block_reasons
    assert value.decision_state == 'long_target'
    under = intent(decision(), cash='100', units='0')
    assert under.action == 'entry' and under.target_fraction == D('0.5')


def test_only_valid_cash_can_propose_reduction_before_deadline():
    sell = intent(decision(('2', '1')))
    assert sell.action == 'exit' and not sell.execution_block_reasons
    warmup = intent(decision(('1',)))
    assert warmup.action == 'hold' and warmup.decision_state == 'warmup'
    unavailable = intent(decision(input_status='unavailable'))
    assert unavailable.action == 'hold' and unavailable.execution_block_reasons == ('MANAGED_DECISION_UNAVAILABLE',)


def test_deadline_preserves_candidate_verdict_but_blocks_buy_and_sell_at_boundary():
    before = NOW + timedelta(seconds=59, microseconds=999999)
    end = NOW + timedelta(seconds=60)
    assert intent(decision(), cash='100', units='0', slot=before, deadline=end).action == 'entry'
    entry = intent(decision(), cash='100', units='0', slot=end, deadline=end)
    assert entry.action == 'entry' and entry.execution_block_reasons == ('MANAGED_DEADLINE_REACHED',)
    sell = intent(decision(('2', '1')), slot=end, deadline=end)
    assert sell.action == 'exit' and sell.decision_state == 'cash_target'
    assert sell.execution_block_reasons == ('MANAGED_DEADLINE_REACHED', 'MANAGED_AUTHORITY_UNAVAILABLE')
    assert intent(decision(), slot=end, deadline=end).action == 'hold'


def test_intent_uses_exact_high_precision_ledger_values_not_decimal_context_rounding():
    with localcontext() as context:
        context.prec = 6
        value = intent(decision(), cash='10000000000000000000000000000.000000000000000001',
                       units='10000000000000000000000000000', mark='1')
        assert value.action == 'entry'
    refused(lambda: intent(decision(), cash='-1'), 'MANAGED_ACCOUNT_AMOUNT_INVALID')
    refused(lambda: intent(decision(), slot=NOW-timedelta(microseconds=1)), 'MANAGED_DECISION_IN_FUTURE')


def test_benchmark_is_an_explicit_counterfactual_and_not_a_strategy_verdict():
    value = B.benchmark_fixed_decision_v2(bar_index=1, decided_at=NOW, history_sha256=SHA)
    assert value.state == 'long_target' and value.cause == 'benchmark_buy_hold' and value.target_fraction == 1
    assert value != decision()
    assert B.parse_decision_document(B.decision_document(value)) == value
