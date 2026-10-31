"""Exact value identity and instrument admission checks; no external services."""
from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timezone
from decimal import Decimal, localcontext

from execution_control.model import InstrumentRules, Order, decimal_text, order_body, order_digest, rules_digest, validate_order

D = Decimal
NOW = datetime(2026, 10, 31, tzinfo=timezone.utc)


def sample_order(**changes):
    values = dict(client_id="example-1", account_scope="profileA", venue="upbit", market="spot", symbol="KRW-BTC",
                  side="buy", quantity=D("0.002"), limit_price=D("1000000"), quote_krw=D("1"))
    return Order(**(values | changes))


def sample_rules(**changes):
    values = dict(venue="upbit", market="spot", symbol="KRW-BTC", lot_size=D("0.0001"), tick_size=D("100"),
                  min_quantity=D("0.001"), min_notional_krw=D("1000"), fee_fraction=D("0.001"), asof=NOW,
                  source_digest="a" * 64)
    return InstrumentRules(**(values | changes))


def _raises(call, error=ValueError):
    try:
        call()
    except error:
        return
    raise AssertionError("expected refusal")


def test_every_order_field_binds_its_digest_and_scope():
    order = sample_order()
    assert set(order_body(order)) == {"client_id", "account_scope", "venue", "market", "symbol", "side", "quantity",
                                     "limit_price", "quote_krw", "time_in_force"}
    assert order_body(order)["quantity"] == "0.002"
    for changes in (dict(client_id="example-2"), dict(account_scope="profileB"), dict(symbol="KRW-ETH"),
                    dict(side="sell"), dict(quantity=D("0.003")), dict(limit_price=D("1000100")),
                    dict(venue="okx", symbol="BTC-USDT", quote_krw=D("1300")),
                    dict(venue="kis", market="nasd", symbol="AAPL", quantity=D("1"), quote_krw=D("1300"),
                         time_in_force="day")):
        assert order_digest(replace(order, **changes)) != order_digest(order)
    _raises(lambda: replace(order, time_in_force="ioc"))


def test_equivalent_decimal_spellings_have_one_digest_and_no_context_rounding():
    base = sample_order()
    same = replace(base, quantity=D("0.002000"), limit_price=D("1E+6"), quote_krw=D("1.00"))
    with localcontext() as ctx:
        ctx.prec = 2
        assert order_digest(same) == order_digest(base)
        assert decimal_text(D("123456789.123456789")) == "123456789.123456789"
        validate_order(base, sample_rules())
    assert decimal_text(D("-0.000")) == "0"


def test_lot_tick_and_minimums_are_refused_without_rounding():
    rules = sample_rules()
    for change in (dict(quantity=D("0.00201")), dict(limit_price=D("1000001")), dict(quantity=D("0.0009"))):
        _raises(lambda change=change: validate_order(sample_order(**change), rules))
    _raises(lambda: validate_order(sample_order(), replace(rules, min_notional_krw=D("2000.00001"))))
    validate_order(sample_order(), replace(rules, min_notional_krw=D("2000")))


def test_decimal_input_types_nonfinite_and_unbounded_values_refused():
    for bad in (1, 1.0, True, "1", D("NaN"), D("sNaN"), D("Infinity"), D("-1"), D("0"), D("1e1000000")):
        _raises(lambda bad=bad: sample_order(quantity=bad))
    for changes in (dict(lot_size=D("0")), dict(tick_size=D("-1")), dict(fee_fraction=D("1.1")),
                    dict(min_notional_krw=False), dict(asof=NOW.replace(tzinfo=None)), dict(source_digest="bad")):
        _raises(lambda changes=changes: sample_rules(**changes))


def test_market_scope_and_cash_share_constraints_are_exact():
    for changes in (dict(venue="unknown"), dict(market="margin"), dict(symbol="BTC"), dict(account_scope=""),
                    dict(client_id="a/b"), dict(side="short"), dict(quote_krw=D("1300"))):
        _raises(lambda changes=changes: sample_order(**changes))
    _raises(lambda: sample_order(venue="kis", market="krx", symbol="005930", quantity=D("0.5"), time_in_force="day"))
    _raises(lambda: sample_order(venue="kis", market="KRX", symbol="005930", quantity=D("1"), time_in_force="day"))
    _raises(lambda: sample_order(venue="kis", market="krx", symbol="005930", quantity=D("1")))
    assert sample_order(venue="kis", market="krx", symbol="005930", quantity=D("1"), time_in_force="day").time_in_force == "day"
    _raises(lambda: validate_order(sample_order(), sample_rules(symbol="KRW-ETH")))
    _raises(lambda: sample_order(unrecognized=True), TypeError)


def test_mutated_frozen_objects_are_revalidated_at_digest_and_admission():
    order = sample_order()
    _raises(lambda: setattr(order, "quantity", D("1")), FrozenInstanceError)
    object.__setattr__(order, "quantity", 1.0)
    _raises(lambda: order_digest(order))
    _raises(lambda: validate_order(order, sample_rules()))
    rules = sample_rules()
    object.__setattr__(rules, "source_digest", "not approved")
    _raises(lambda: rules_digest(rules))
    _raises(lambda: validate_order(sample_order(), rules))


def test_rule_provenance_and_fee_changes_change_digest():
    rules = sample_rules()
    for changes in (dict(source_digest="b" * 64), dict(fee_fraction=D("0.002")), dict(tick_size=D("10")),
                    dict(asof=NOW.replace(hour=1)), dict(min_quantity=D("0.002"))):
        assert rules_digest(replace(rules, **changes)) != rules_digest(rules)
