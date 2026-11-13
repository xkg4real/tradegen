"""Hand-computed hypothetical ledgers; no live quotes, approvals or account facts.

Short fixtures exercise the unissued arithmetic layer. They deliberately do not
claim to satisfy a preregistered study's observation/statistical thresholds.
"""
from datetime import datetime, timedelta, timezone
from decimal import Decimal, localcontext
from fractions import Fraction
from types import SimpleNamespace

from execution_control.model import InstrumentRules
from execution_launch.carry_evaluator import (
    CarryArithmeticError, FifoLot, decimal_text, parse_decimal_text,
    release_fifo_cost, simulate_carry,
)
from execution_launch.managed_behavior import (
    BEHAVIOR_REVISION, CARRY_EVALUATOR_REVISION, TERMINAL_ACCOUNTING,
    benchmark_fixed_decision_v2, behavior_digest, derive_fixed_decision_v2,
)
from execution_launch.program import ProgramSpec

D = Decimal
START = datetime(2035, 1, 1, tzinfo=timezone.utc)


def fixture(marks=('100', '110', '100', '130'), *, fee='0.01', exposure='1',
            initial='1000', lot='1', tick='1', minimum='1', slip='0'):
    # A namespace is explicitly not an issued ForwardProtocol/capture receipt.
    p = SimpleNamespace(schema_version=2, evaluator_revision=CARRY_EVALUATOR_REVISION,
        behavior_revision=BEHAVIOR_REVISION, terminal_accounting=TERMINAL_ACCOUNTING,
        management_behavior_sha256=behavior_digest(), universe_rule_sha256=None,
        initial_cash_quote=D(initial), fee_fraction=D(fee), slippage_bps=D(slip),
        capture_end=START+timedelta(minutes=len(marks)-1), venue='upbit', market='spot',
        quote_currency='KRW', symbol='KRW-BTC')
    rules = InstrumentRules(venue='upbit', market='spot', symbol='KRW-BTC', lot_size=D(lot),
        tick_size=D(tick), min_quantity=D(lot), min_notional_krw=D(minimum), fee_fraction=D(fee),
        asof=START-timedelta(minutes=1), source_digest='a'*64)
    program = ProgramSpec(schema_version=1, strategy_id='synthetic-carry-arithmetic',
        kind='moving_average_trend', fast_window=1, slow_window=2, exposure_fraction=D(exposure))
    bars = tuple(SimpleNamespace(observed_at=START+timedelta(minutes=i), bid=D(mark),
        ask=D(mark), mark=D(mark), quote_krw=D(1), source_sha256=f'{i+1:064x}')
        for i, mark in enumerate(marks))
    decisions = tuple(derive_fixed_decision_v2(program, tuple(row.mark for row in bars[:i+1]),
        bar_index=i, decided_at=bar.observed_at+timedelta(seconds=1), history_sha256=f'{i+30:064x}')
        for i, bar in enumerate(bars))
    return p, bars, decisions, rules, program


def arithmetic(**kwargs):
    p, bars, decisions, rules, _ = fixture(**kwargs)
    return simulate_carry(p, bars, decisions, rules)


def refused(call, code=None):
    try:
        call()
    except CarryArithmeticError as exc:
        if code is not None:
            assert str(exc) == code, (str(exc), code)
        return
    raise AssertionError('invalid hypothetical arithmetic accepted')


def assert_identity(metrics, initial):
    # Independent monetary identity using the exact strings, not display floats.
    cash = D(metrics.terminal_cash_quote)
    marked = D(metrics.terminal_units)*D(metrics.terminal_mark_quote)
    realized = D(metrics.realized_net_profit_quote)
    unrealized = D(metrics.unrealized_net_profit_quote)
    assert cash+marked-D(initial) == realized+unrealized
    assert cash+marked == D(metrics.terminal_marked_equity_quote)


def test_carry_final_mark_is_not_a_sale_and_fee_enters_inventory_cost():
    m, returns = arithmetic()
    # Buy nine at 100, charge 9; E marks 9 units at 130 without selling.
    assert (m.terminal_units, m.terminal_cash_quote, m.terminal_inventory_cost_quote) == ('9', '91', '909')
    assert (m.terminal_marked_equity_quote, m.realized_net_profit_quote,
            m.unrealized_net_profit_quote, m.total_fees_quote_exact) == ('1261', '0', '261', '9')
    assert m.turnover_quote_exact == '900' and m.completed_roundtrips == 0
    assert m.total_return == .261 and returns == (0.0, -.009, float(Fraction(270, 991)))
    assert m.terminal_observed_at == START+timedelta(minutes=3)
    assert m.terminal_source_sha256 == f'{4:064x}'
    assert_identity(m, '1000')


def test_valid_sell_at_deadline_remains_sell_verdict_but_has_no_execution_authority():
    m, _ = arithmetic()
    assert m.terminal_decision_state == 'cash_target'
    assert m.terminal_decision_cause == 'trend_not_above'
    assert m.terminal_execution_block_reasons == ('MANAGED_DEADLINE_REACHED', 'MANAGED_AUTHORITY_UNAVAILABLE')
    assert m.terminal_units == '9' and m.realized_net_profit_quote == '0'


def test_predeadline_explicit_sell_realizes_both_fees_and_final_entry_is_blocked():
    m, _ = arithmetic(marks=('100', '110', '100', '120', '130'))
    # 1000 - 900 - 9 + 1080 - 10.8 = 1160.2.
    assert (m.terminal_units, m.terminal_cash_quote, m.terminal_inventory_cost_quote) == ('0', '1160.2', '0')
    assert (m.realized_net_profit_quote, m.unrealized_net_profit_quote) == ('160.2', '0')
    assert m.total_fees_quote_exact == '19.8' and m.turnover_quote_exact == '1980'
    assert m.completed_roundtrips == 1 and m.total_return == .1602
    assert m.terminal_decision_state == 'long_target'
    assert m.terminal_execution_block_reasons == ('MANAGED_DEADLINE_REACHED',)
    assert_identity(m, '1000')


def test_realized_loss_is_signed_and_valuation_does_not_hide_it():
    m, _ = arithmetic(marks=('100', '110', '100', '80', '90'))
    assert m.realized_net_profit_quote == '-196.2'
    assert m.terminal_cash_quote == '803.8' and m.unrealized_net_profit_quote == '0'
    assert m.total_fees_quote_exact == '16.2' and m.completed_roundtrips == 1
    assert_identity(m, '1000')


def test_long_with_negative_allocation_gap_does_not_rebalance_sell():
    m, _ = arithmetic(marks=('90', '100', '110', '220', '230'), exposure='.5', fee='0')
    # Four units cost 440. At 220 their weight exceeds 50%; LONG still holds.
    assert m.terminal_units == '4' and m.terminal_cash_quote == '560'
    assert m.turnover_quote_exact == '440' and m.realized_net_profit_quote == '0'
    assert m.unrealized_net_profit_quote == '480' and m.completed_roundtrips == 0
    assert_identity(m, '1000')


def test_unavailable_observation_cannot_become_an_exit_or_fake_hold_verdict():
    p, bars, decisions, rules, program = fixture(marks=('100', '110', '100', '120', '130'))
    unavailable = derive_fixed_decision_v2(program, tuple(row.mark for row in bars[:3]),
        bar_index=2, decided_at=decisions[2].decided_at, history_sha256=decisions[2].history_sha256,
        input_status='unavailable')
    decisions = decisions[:2]+(unavailable,)+decisions[3:]
    m, _ = simulate_carry(p, bars, decisions, rules)
    assert m.terminal_units == '9' and m.realized_net_profit_quote == '0'
    assert m.turnover_quote_exact == '900' and m.completed_roundtrips == 0
    # Now place the recorded unavailable decision immediately before E.
    last = derive_fixed_decision_v2(program, tuple(row.mark for row in bars[:4]),
        bar_index=3, decided_at=decisions[3].decided_at, history_sha256=decisions[3].history_sha256,
        input_status='unavailable')
    m, _ = simulate_carry(p, bars, decisions[:3]+(last,)+decisions[4:], rules)
    assert m.terminal_decision_state == 'unavailable'
    assert m.terminal_execution_block_reasons == ('MANAGED_DECISION_UNAVAILABLE', 'MANAGED_DEADLINE_REACHED')
    assert m.terminal_units == '9'


def test_final_positive_target_cannot_open_first_position():
    m, _ = arithmetic(marks=('100', '110', '120'))
    assert m.terminal_units == '0' and m.terminal_cash_quote == '1000'
    assert m.terminal_decision_state == 'long_target' and m.turnover_quote_exact == '0'
    assert m.terminal_execution_block_reasons == ('MANAGED_DEADLINE_REACHED',)


def test_all_cost_delay_and_benchmark_scenarios_preserve_carry_policy():
    p, bars, decisions, rules, _ = fixture()
    base, _ = simulate_carry(p, bars, decisions, rules)
    double, _ = simulate_carry(p, bars, decisions, rules, cost_multiple=2)
    delayed, _ = simulate_carry(p, bars, decisions, rules, lag=2)
    benchmark, _ = simulate_carry(p, bars, decisions, rules, buy_hold=True)
    assert (base.terminal_units, double.terminal_units, delayed.terminal_units, benchmark.terminal_units) == ('9', '9', '0', '9')
    assert (double.terminal_cash_quote, double.total_fees_quote_exact, double.unrealized_net_profit_quote) == ('82', '18', '252')
    assert delayed.turnover_quote_exact == '0' and delayed.total_return == 0
    assert (benchmark.terminal_cash_quote, benchmark.total_fees_quote_exact,
            benchmark.unrealized_net_profit_quote) == ('0.1', '9.9', '170.1')
    assert benchmark.terminal_decision_cause == 'benchmark_buy_hold'
    for m in (base, double, delayed, benchmark):
        assert 'MANAGED_DEADLINE_REACHED' in m.terminal_execution_block_reasons
        assert m.completed_roundtrips == 0 and m.realized_net_profit_quote == '0'
        assert_identity(m, '1000')


def test_fifo_partial_thirds_keep_exact_final_residual():
    lots = (FifoLot(quantity=D(3), cost_quote=D(1)),)
    lots, first = release_fifo_cost(lots, D(1))
    assert first == D('.333333333333333333')
    lots, second = release_fifo_cost(lots, D(1))
    assert second == D('.333333333333333333')
    lots, final = release_fifo_cost(lots, D(1))
    assert final == D('.333333333333333334') and lots == ()
    assert first+second+final == 1


def test_fifo_cross_lots_preserves_fee_inclusive_basis_and_sub18dp_residue():
    lots = (FifoLot(quantity=D(2), cost_quote=D(21)), FifoLot(quantity=D(3), cost_quote=D('33.3')))
    remaining, released = release_fifo_cost(lots, D(3))
    assert released == D('32.1') and remaining == (FifoLot(quantity=D(2), cost_quote=D('22.2')),)
    remaining, released_last = release_fifo_cost(remaining, D(2))
    assert not remaining and released+released_last == D('54.3')
    lots = (FifoLot(quantity=D(2), cost_quote=D('0.0000000000000000001')),)
    remaining, released = release_fifo_cost(lots, D(1))
    assert released == 0
    remaining, released = release_fifo_cost(remaining, D(1))
    assert not remaining and released == D('0.0000000000000000001')


def test_sell_below_minimum_stays_unrealized_and_terminal_dust_is_not_fabricated_sale():
    m, _ = arithmetic(marks=('1', '2', '1', '.01', '.01'), initial='10', fee='0', tick='.01')
    assert m.terminal_units == '10' and m.terminal_cash_quote == '0'
    assert m.terminal_inventory_cost_quote == '10' and m.unrealized_net_profit_quote == '-9.9'
    assert m.realized_net_profit_quote == '0' and m.rejected_small_orders == 1
    assert m.completed_roundtrips == 0 and m.total_fees_quote_exact == '0'
    assert_identity(m, '10')


def test_buy_below_minimum_is_counted_without_inventory_or_fee():
    m, _ = arithmetic(minimum='1001')
    assert m.rejected_small_orders == 1 and m.terminal_units == '0'
    assert m.terminal_cash_quote == '1000' and m.total_fees_quote_exact == '0'
    assert m.turnover_quote_exact == '0'


def test_slippage_rounds_against_paper_trader_on_tick_before_sizing():
    m, _ = arithmetic(fee='0', slip='1')
    # Raw ask 100*(1+.0001)=100.01 rounds up to tick 101, so nine units cost 909.
    assert m.terminal_units == '9' and m.terminal_cash_quote == '91'
    assert m.terminal_inventory_cost_quote == '909' and m.turnover_quote_exact == '909'
    assert m.unrealized_net_profit_quote == '261'


def test_decimal_context_does_not_change_ledger_or_fifo_hashes():
    normal, returns = arithmetic()
    with localcontext() as ctx:
        ctx.prec = 3
        small, small_returns = arithmetic()
        remaining, released = release_fifo_cost((FifoLot(quantity=D(3), cost_quote=D(1)),), D(1))
    assert small == normal and returns == small_returns
    assert released == D('.333333333333333333')
    assert remaining[0].cost_quote == D('.666666666666666667')


def test_signed_codec_requires_canonical_bounded_strings():
    for value, text in ((D('-1.2500'), '-1.25'), (D('-0'), '0'), (D('1E+3'), '1000'), (D('1E-18'), '0.000000000000000001')):
        assert decimal_text(value) == text and parse_decimal_text(text) == value
    for value in ('-0', '+1', '01', '1.0', '1e2', 'NaN', 'Infinity', '.1', '-.1', ' 1', True, '1'*4097):
        refused(lambda value=value: parse_decimal_text(value), 'CARRY_DECIMAL_INVALID')
    for value in (D('NaN'), D('Infinity'), D('1e101'), D('1e-2049'), 1, True):
        refused(lambda value=value: decimal_text(value), 'CARRY_DECIMAL_INVALID')


def test_benchmark_marker_in_actual_input_never_bypasses_program_evaluation():
    p, bars, decisions, rules, _ = fixture()
    fake = benchmark_fixed_decision_v2(bar_index=0, decided_at=decisions[0].decided_at,
                                      history_sha256=decisions[0].history_sha256)
    for benchmark in (False, True):
        refused(lambda: simulate_carry(p, bars, (fake,)+decisions[1:], rules, buy_hold=benchmark),
                'CARRY_BENCHMARK_NOT_STRATEGY')


def test_arithmetic_rejects_incomplete_fifo_wrong_scenario_and_wrong_terminal_mark():
    refused(lambda: release_fifo_cost((FifoLot(quantity=D(1), cost_quote=D(10)),), D(2)), 'CARRY_FIFO_INCOMPLETE')
    refused(lambda: release_fifo_cost([], D(1)), 'CARRY_FIFO_INVALID')
    refused(lambda: FifoLot(quantity=D(0), cost_quote=D(1)), 'CARRY_AMOUNT_INVALID')
    p, bars, decisions, rules, _ = fixture()
    for kwargs in ({'lag': True}, {'lag': 3}, {'cost_multiple': True}, {'cost_multiple': 0}, {'buy_hold': 1}):
        refused(lambda kwargs=kwargs: simulate_carry(p, bars, decisions, rules, **kwargs), 'CARRY_SCENARIO_INVALID')
    p.capture_end += timedelta(minutes=1)
    refused(lambda: simulate_carry(p, bars, decisions, rules), 'CARRY_TERMINAL_TIME_INVALID')


def test_changed_fill_price_or_terminal_mark_changes_the_appropriate_commitment():
    base, _ = arithmetic()
    p, bars, decisions, rules, _ = fixture()
    # Terminal mark affects valuation, not the preceding simulated fill journal.
    changed = SimpleNamespace(**{**vars(bars[-1]), 'mark': D(140), 'bid': D(140), 'ask': D(140)})
    marked, _ = simulate_carry(p, bars[:-1]+(changed,), decisions, rules)
    assert marked.fills_sha256 == base.fills_sha256 and marked.lots_sha256 == base.lots_sha256
    assert marked.unrealized_net_profit_quote == '351'
    slipped, _ = arithmetic(slip='1')
    assert slipped.fills_sha256 != base.fills_sha256 and slipped.lots_sha256 != base.lots_sha256


def test_delayed_tiny_window_records_absence_of_decision_without_selling():
    p, bars, decisions, rules, _ = fixture(marks=('100', '110'))
    m, returns = simulate_carry(p, bars, decisions, rules, lag=2)
    assert returns == (0.0,) and m.terminal_units == '0'
    assert m.terminal_decision_state == 'not_yet_available' and m.terminal_decision_cause == 'fill_delay'
    assert m.terminal_execution_block_reasons == ('MANAGED_FILL_DELAY', 'MANAGED_DEADLINE_REACHED')


def test_unexecuted_final_mark_and_warmup_do_not_need_a_positive_stressed_execution_bid():
    # A valid .01 mark is not a zero sale price: the stressed hypothetical bid
    # rounds to zero, but warmup and the E-blocked entry generate no fill.
    p, bars, decisions, rules, _ = fixture(marks=('.01', '.02', '.01'), initial='1',
        fee='0', slip='1', tick='.01')
    m, returns = simulate_carry(p, bars, decisions, rules)
    assert m.terminal_mark_quote == '0.01' and m.terminal_units == '0'
    assert m.terminal_cash_quote == '1' and m.turnover_quote_exact == '0'
    assert m.terminal_decision_state == 'long_target' and returns == (0.0, 0.0)
    assert m.terminal_execution_block_reasons == ('MANAGED_DEADLINE_REACHED',)
    # Extending E by one slot makes the same low-tick row an actual entry
    # candidate; the existing driver's positive stressed-bid sizing rule remains.
    p, bars, decisions, rules, _ = fixture(marks=('.01', '.02', '.01', '.02'), initial='1',
        fee='0', slip='1', tick='.01')
    refused(lambda: simulate_carry(p, bars, decisions, rules), 'CARRY_EXECUTION_PRICE_INVALID')


def test_held_terminal_inventory_is_marked_even_when_hypothetical_sell_bid_rounds_to_zero():
    m, _ = arithmetic(marks=('.01', '.02', '.02', '.01'), initial='1', fee='0',
        slip='1', tick='.01', minimum='.01')
    # At i=2: ask .020002 rounds to .03, buying 33 units for .99.
    # At E: price .01 is only a mark, leaving .01 cash + .33 inventory.
    assert (m.terminal_units, m.terminal_cash_quote, m.terminal_inventory_cost_quote) == ('33', '0.01', '0.99')
    assert m.terminal_marked_equity_quote == '0.34' and m.unrealized_net_profit_quote == '-0.66'
    assert m.realized_net_profit_quote == '0' and m.completed_roundtrips == 0
    assert_identity(m, '1')
