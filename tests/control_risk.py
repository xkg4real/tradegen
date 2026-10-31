"""Pure risk/accounting tests: synthetic Decimal records, no account or I/O."""
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, localcontext

from execution_control.risk import Fill, RiskObservation, RiskPolicy, account_fills, evaluate

D = Decimal
NOW = datetime(2026, 10, 20, 14, 0, tzinfo=timezone.utc)


def _policy(**changes):
    return replace(RiskPolicy(version="fixture-v1", initial_equity=D("2000"),
                              drawdown_activation_equity=D("8000"),
                              positive_profit_loss_fraction=D("0.2"), peak_drawdown_fraction=D("0.25"),
                              zero_profit_day_target_fraction=D("0.1")), **changes)


def _observation(**changes):
    return replace(RiskObservation(equity=D("2500"), prior_high_watermark=D("2500"),
                                   day_start_equity=D("2500"), current_day_realized_net_profit=D("0"),
                                   prior_day_realized_net_profit=D("50"), observed_daily_loss=D("0"),
                                   approved_effective_floor=D("2500"), is_first_trading_day=False,
                                   asof=NOW), **changes)


def _fill(**changes):
    return replace(Fill(venue="upbit", account_scope="fixture-account", order_id="buy-a", fill_id="fill-a",
                        market="KRW", symbol="KRW-BTC", side="buy", quantity=D("10"), price=D("100"),
                        quote_currency="KRW", quote_krw=D("1"), fee_amount=D("10"), fee_currency="KRW",
                        executed_at=NOW, base_currency="BTC"), **changes)


def _sell(**changes):
    return _fill(**({"side": "sell", "order_id": "sell-a", "fill_id": "sell-fill-a",
                    "executed_at": NOW+timedelta(minutes=1)} | changes))


def test_floor_equality_is_distinct_from_fee_breach():
    boundary = evaluate(_policy(), _observation())
    assert not boundary.new_entry_blocked and not boundary.protective_action_needed
    assert boundary.effective_floor == D("2500") and boundary.daily_loss_budget == D("10")
    fee_loss = evaluate(_policy(), _observation(equity=D("2499.7"), observed_daily_loss=D("0.3")))
    assert fee_loss.new_entry_blocked and fee_loss.protective_action_needed
    assert "EQUITY_BELOW_EFFECTIVE_FLOOR" in fee_loss.reasons and fee_loss.exits_allowed


def test_activation_never_automatically_relaxes_the_effective_floor():
    under = evaluate(_policy(), _observation(equity=D("7999.99"), prior_high_watermark=D("7999.99"),
                                            approved_effective_floor=D("7999.99")))
    on = evaluate(_policy(), _observation(equity=D("8000"), prior_high_watermark=D("7999.99"),
                                         approved_effective_floor=D("7999.99")))
    assert under.calculated_floor == D("7999.99") and not under.relaxation_pending
    assert on.calculated_floor == D("6000") and on.effective_floor == D("7999.99") and on.relaxation_pending
    high = evaluate(_policy(), _observation(equity=D("12000"), prior_high_watermark=D("8000"),
                                           approved_effective_floor=D("7999.99")))
    assert high.effective_floor == D("9000") and not high.relaxation_pending
    principal = evaluate(_policy(peak_drawdown_fraction=D("0.9")),
                         _observation(equity=D("8000"), prior_high_watermark=D("8000"),
                                      approved_effective_floor=D("2000")))
    assert principal.calculated_floor == D("2000")


def test_first_day_missing_zero_and_loss_states_stay_distinct():
    missing = evaluate(_policy(), _observation(prior_day_realized_net_profit=None))
    first = evaluate(_policy(), _observation(prior_day_realized_net_profit=None, is_first_trading_day=True))
    zero = evaluate(_policy(), _observation(prior_day_realized_net_profit=D("0")))
    assert missing.reasons == ("PREVIOUS_DAY_RESULT_MISSING",)
    assert first.reasons == ("FIRST_DAY_LOSS_BUDGET_UNCONFIGURED",)
    assert zero.reasons == ("ZERO_PROFIT_DAY_LOSS_BUDGET_UNCONFIGURED",)
    assert missing.daily_profit_target is None and first.daily_profit_target is None
    assert zero.daily_profit_target == D("250")
    allowed = evaluate(_policy(first_day_loss_budget=D("8")),
                       _observation(prior_day_realized_net_profit=None, is_first_trading_day=True))
    assert not allowed.new_entry_blocked and allowed.daily_loss_budget == D("8")
    prior_loss = evaluate(_policy(first_day_loss_budget=D("8")),
                          _observation(prior_day_realized_net_profit=D("-1"), is_first_trading_day=True))
    assert prior_loss.new_entry_blocked and prior_loss.daily_loss_budget == D("0")
    assert "PREVIOUS_DAY_LOSS" in prior_loss.reasons and prior_loss.exits_allowed


def test_target_is_diagnostic_and_does_not_increase_budget_or_override_stop():
    policy = _policy(zero_profit_day_loss_budget=D("7"))
    miss = evaluate(policy, _observation(prior_day_realized_net_profit=D("0"),
                                        current_day_realized_net_profit=D("249.99")))
    met = evaluate(policy, _observation(prior_day_realized_net_profit=D("0"),
                                       current_day_realized_net_profit=D("250")))
    assert miss.daily_profit_target_met is False and met.daily_profit_target_met is True
    assert not miss.new_entry_blocked and not met.new_entry_blocked
    assert miss.daily_loss_budget == met.daily_loss_budget == D("7")
    stopped = evaluate(policy, _observation(prior_day_realized_net_profit=D("0"),
                                           current_day_realized_net_profit=D("500"), observed_daily_loss=D("7")))
    assert stopped.new_entry_blocked and stopped.daily_profit_target_met
    assert stopped.protective_action_needed and stopped.exits_allowed


def test_daily_loss_is_explicit_and_positive_reference_does_not_reset_a_halt():
    exhausted = evaluate(_policy(), _observation(observed_daily_loss=D("10"),
                                                current_day_realized_net_profit=D("200")))
    assert exhausted.new_entry_blocked and "DAILY_LOSS_BUDGET_REACHED" in exhausted.reasons
    halted = evaluate(_policy(), _observation(halted=True))
    assert halted.new_entry_blocked and halted.protective_action_needed and "PERSISTENT_HALT" in halted.reasons
    conflict = evaluate(_policy(), _observation(legacy_floor_conflict=True))
    assert conflict.new_entry_blocked and "LEGACY_FLOOR_POLICY_CONFLICT" in conflict.reasons


def test_unknown_data_and_flows_do_not_become_verified_zero_profit():
    for change, reason in (({"data_complete": False}, "INCOMPLETE_ACCOUNTING_DATA"),
                           ({"external_flows_known": False}, "EXTERNAL_FLOWS_UNKNOWN"),
                           ({"approved_effective_floor": None}, "EFFECTIVE_FLOOR_UNCONFIGURED")):
        result = evaluate(_policy(), _observation(**change))
        assert result.new_entry_blocked and reason in result.reasons and result.exits_allowed


def test_risk_malformed_decimal_inputs_and_naive_time_fail_closed():
    for bad in (D("NaN"), D("sNaN"), D("Infinity"), 2.0, 2, True):
        assert evaluate(_policy(), _observation(equity=bad)).new_entry_blocked
    for change in ({"asof": NOW.replace(tzinfo=None)}, {"is_first_trading_day": 1},
                   {"day_start_equity": D("2501")}, {"observed_daily_loss": D("-1")}):
        assert evaluate(_policy(), _observation(**change)).new_entry_blocked
    for change in ({"peak_drawdown_fraction": D("1")}, {"first_day_loss_budget": D("-1")},
                   {"zero_profit_day_loss_budget": D("NaN")}, {"version": ""}):
        assert evaluate(_policy(**change), _observation()).new_entry_blocked
    assert evaluate(None, _observation()).reasons == ("INVALID_ARGUMENT_TYPE",)


def test_risk_arithmetic_is_independent_of_ambient_decimal_precision():
    with localcontext() as context:
        context.prec = 2
        result = evaluate(_policy(), _observation(equity=D("7999.999999999999999"),
                                                 prior_high_watermark=D("7999.999999999999999"),
                                                 approved_effective_floor=D("7999.999999999999999")))
    assert result.calculated_floor == D("7999.999999999999999") and not result.new_entry_blocked
    huge = evaluate(_policy(), _observation(equity=D("1e999999999")))
    assert huge.reasons == ("ARITHMETIC_NOT_EXACT_OR_FINITE",)


def test_fifo_acquisition_and_exit_fees_allocate_across_partial_lots():
    second = _fill(order_id="buy-b", fill_id="fill-b", quantity=D("5"), price=D("120"), fee_amount=D("5"),
                   executed_at=NOW+timedelta(seconds=1))
    sale = _sell(quantity=D("12"), price=D("150"), fee_amount=D("12"))
    result = account_fills((_fill(), second, sale))
    assert result.ok and result.realized_net_profit_krw == D("536")
    assert result.inventory == (("upbit", "fixture-account", "KRW", "KRW-BTC", D("3"), D("363")),)
    assert result.cash_deltas_by_account_krw == (("upbit", "fixture-account", D("173")),)
    assert result.order_quantities == (("upbit", "fixture-account", "KRW", "", "", "buy-a", D("10")),
                                       ("upbit", "fixture-account", "KRW", "", "", "buy-b", D("5")),
                                       ("upbit", "fixture-account", "KRW", "", "", "sell-a", D("12")))


def test_duplicate_fill_is_idempotent_but_contradiction_refuses_every_output():
    buy, sale = _fill(), _sell(quantity=D("2"), price=D("150"), fee_amount=D("2"))
    result = account_fills((sale, buy, buy, sale))
    assert result.ok and result.duplicate_count == 2 and result.accepted_fills == (buy, sale)
    assert result.realized_net_profit_krw == D("96")
    for changed in (replace(buy, price=D("101")), replace(buy, fee_amount=D("9")),
                    replace(buy, executed_at=NOW+timedelta(seconds=1))):
        bad = account_fills((buy, changed))
        assert not bad.ok and bad.reasons == ("CONTRADICTORY_DUPLICATE_FILL",)
        assert bad.realized_net_profit_krw is None and bad.inventory == () and bad.order_quantities == ()


def test_same_fill_ids_on_different_accounts_or_venues_do_not_collide():
    one = _fill()
    two = replace(one, account_scope="other-account")
    three = replace(one, venue="okx")
    result = account_fills((one, two, three))
    assert result.ok and len(result.inventory) == 3 and result.duplicate_count == 0
    isolated_sale = replace(_sell(), account_scope="absent-account")
    assert account_fills((one, isolated_sale)).reasons == ("INCOMPLETE_ACQUISITION_HISTORY",)


def test_partial_cost_rounding_conserves_the_last_lot_remainder():
    buy = _fill(quantity=D("3"), price=D("1"), fee_amount=D("1"))
    sales = tuple(_sell(order_id="sale-"+str(i), fill_id="sale-fill-"+str(i), quantity=D("1"),
                        price=D("2"), fee_amount=D("0"), executed_at=NOW+timedelta(minutes=i+1))
                  for i in range(3))
    first = account_fills((buy, sales[0]))
    assert first.ok and first.realized_net_profit_krw == D("0.666666666666666667")
    final = account_fills((buy, *sales))
    assert final.ok and final.realized_net_profit_krw == D("2") and final.inventory == ()
    assert final.cash_deltas_by_account_krw[0][-1] == D("2")


def test_base_asset_fees_reduce_inventory_without_fake_quote_cash_debit():
    buy = _fill(quantity=D("10"), price=D("10"), fee_amount=D("2"), fee_currency="BTC")
    sale = _sell(quantity=D("3"), price=D("20"), fee_amount=D("1"), fee_currency="BTC")
    result = account_fills((buy, sale))
    assert result.ok and result.realized_net_profit_krw == D("10")
    assert result.inventory[0][-2:] == (D("4"), D("50"))
    assert result.cash_deltas_by_currency == (("upbit", "fixture-account", "KRW", D("-40")),)
    assert account_fills((replace(buy, fee_amount=D("10")),)).reasons == ("BASE_FEE_EXHAUSTS_BUY_QUANTITY",)


def test_explicit_fx_and_krw_fee_are_allocated_without_double_charging():
    buy = _fill(venue="kis", market="nasd", symbol="XYZ", base_currency="XYZ", quote_currency="USD",
                order_id="17", order_date="20261020",
                quote_krw=D("1000"), quantity=D("2"), price=D("3"), fee_amount=D("10"))
    sale = replace(buy, order_id="18", fill_id="sale-a-1", side="sell", quantity=D("1"), price=D("4"),
                   quote_krw=D("1100"), fee_amount=D("5"), executed_at=NOW+timedelta(minutes=1))
    result = account_fills((buy, sale))
    assert result.ok and result.realized_net_profit_krw == D("1390")
    assert result.inventory[0][-2:] == (D("1"), D("3005"))
    assert result.cash_deltas_by_currency == (("kis", "fixture-account", "KRW", D("-15")),
                                             ("kis", "fixture-account", "USD", D("-2")))
    assert result.cash_deltas_by_account_krw == (("kis", "fixture-account", D("-1615")),)


def test_daily_realized_result_uses_execution_seoul_date_not_input_order():
    buy = _fill(quantity=D("2"), price=D("100"), fee_amount=D("0"))
    early = _sell(order_id="sale-early", fill_id="early", quantity=D("1"), price=D("110"), fee_amount=D("0"),
                  executed_at=NOW.replace(hour=14, minute=59, second=59))
    late = _sell(order_id="sale-late", fill_id="late", quantity=D("1"), price=D("120"), fee_amount=D("0"),
                 executed_at=NOW.replace(hour=15, minute=0, second=0))
    result = account_fills((late, early, buy))
    assert result.ok and result.realized_by_account_day_krw == (
        ("upbit", "fixture-account", date(2026, 10, 20), D("10")),
        ("upbit", "fixture-account", date(2026, 10, 21), D("20")))


def test_missing_fees_fx_or_third_token_fee_requires_reconciliation():
    for change, expected in (({"fee_amount": None}, "MISSING_OR_INVALID_FEE"),
                             ({"fee_currency": None}, "MISSING_OR_INVALID_FEE_CURRENCY"),
                             ({"quote_krw": None}, "MISSING_OR_INVALID_QUOTE_KRW"),
                             ({"quote_krw": D("2")}, "INCONSISTENT_KRW_RATE"),
                             ({"fee_currency": "BNB"}, "UNSUPPORTED_FEE_CURRENCY")):
        result = account_fills((_fill(**change),))
        assert not result.ok and result.reasons == (expected,) and result.inventory == ()


def test_accounting_identity_conflicts_and_sell_without_history_fail_closed():
    assert account_fills((_sell(),)).reasons == ("INCOMPLETE_ACQUISITION_HISTORY",)
    changed = _fill(fill_id="second-fill", symbol="KRW-ETH", base_currency="ETH")
    assert account_fills((_fill(), changed)).reasons == ("INCONSISTENT_ORDER_FILL_IDENTITY",)
    changed = _fill(order_id="other-order", fill_id="second-fill", base_currency="ETH")
    assert account_fills((_fill(), changed)).reasons == ("INCONSISTENT_INSTRUMENT_CURRENCY",)
    too_much = _sell(quantity=D("11"))
    assert account_fills((_fill(), too_much)).reasons == ("INCOMPLETE_ACQUISITION_HISTORY",)


def test_accounting_bad_numbers_types_time_and_overflow_never_return_partial_totals():
    for change in ({"quantity": D("NaN")}, {"price": 1.0}, {"fee_amount": True},
                   {"quantity": D("0")}, {"fee_amount": D("-1")},
                   {"executed_at": NOW.replace(tzinfo=None)}, {"account_scope": ""}):
        result = account_fills((_fill(), _fill(fill_id="bad-fill", **change)))
        assert not result.ok and result.realized_net_profit_krw is None and result.inventory == ()
    assert account_fills([_fill()]).reasons == ("INVALID_FILL_COLLECTION",)
    assert account_fills((None,)).reasons == ("INVALID_FILL_TYPE",)
    huge = account_fills((_fill(price=D("1e999999999")),))
    assert huge.reasons == ("ACCOUNTING_ARITHMETIC_NOT_EXACT_OR_FINITE",)


def test_accounting_is_independent_of_ambient_precision_and_does_not_mark_open_profit():
    buy = _fill()
    with localcontext() as context:
        context.prec = 2
        result = account_fills((buy,))
    assert result.ok and result.realized_net_profit_krw == D("0")
    assert result.inventory[0][-2:] == (D("10"), D("1010"))
    assert result.cash_deltas_by_account_krw[0][-1] == D("-1010")
    empty = account_fills(())
    assert empty.ok and empty.realized_net_profit_krw == D("0") and empty.inventory == ()


def _kis_fill(**changes):
    return _fill(**({"venue": "kis", "market": "krx", "symbol": "005930", "base_currency": "STOCK",
                    "order_id": "17", "order_date": "20261020", "broker_org_id": "0042"} | changes))


def test_kis_reused_raw_order_and_fill_ids_are_scoped_by_authoritative_date():
    buy = _kis_fill()
    sale = replace(buy, side="sell", order_date="20261021", price=D("110"),
                   executed_at=NOW+timedelta(days=1))
    result = account_fills((sale, buy))
    assert result.ok and result.duplicate_count == 0 and result.realized_net_profit_krw == D("80")
    assert result.inventory == () and result.accepted_fills == (buy, sale)
    assert result.order_quantities == (
        ("kis", "fixture-account", "krx", "20261020", "0042", "17", D("10")),
        ("kis", "fixture-account", "krx", "20261021", "0042", "17", D("10")))


def test_kis_market_and_broker_org_scope_do_not_hide_same_identity_contradictions():
    one = _kis_fill()
    other_org = replace(one, broker_org_id="0043")
    other_market = replace(one, market="nasd", symbol="XYZ", base_currency="XYZ", broker_org_id="")
    result = account_fills((one, other_org, other_market, one))
    assert result.ok and result.duplicate_count == 1 and len(result.order_quantities) == 3
    assert result.order_quantities == (
        ("kis", "fixture-account", "krx", "20261020", "0042", "17", D("10")),
        ("kis", "fixture-account", "krx", "20261020", "0043", "17", D("10")),
        ("kis", "fixture-account", "nasd", "20261020", "", "17", D("10")))
    contradictory = replace(one, price=D("101"))
    assert account_fills((one, contradictory)).reasons == ("CONTRADICTORY_DUPLICATE_FILL",)
    other_side = replace(one, side="sell", fill_id="other-fill")
    assert account_fills((one, other_side)).reasons == ("INCONSISTENT_ORDER_FILL_IDENTITY",)


def test_kis_date_is_valid_explicit_and_is_not_guessed_from_execution_utc():
    us = _kis_fill(market="nasd", broker_org_id="", symbol="XYZ", base_currency="XYZ",
                   order_date="20261020", executed_at=NOW.replace(day=21, hour=1))
    result = account_fills((us,))
    assert result.ok and result.order_quantities[0][3] == "20261020"
    for invalid in ("", None, "2026-10-20", "20260230", "00001020", "２０２６１０２０"):
        assert account_fills((replace(us, order_date=invalid),)).reasons == ("MISSING_OR_INVALID_KIS_ORDER_DATE",)
    assert account_fills((_kis_fill(broker_org_id=""),)).reasons == ("MISSING_KIS_BROKER_ORG_ID",)
    assert account_fills((_kis_fill(broker_org_id="-1"),)).reasons == ("INVALID_KIS_BROKER_ORG_ID",)
    assert account_fills((_kis_fill(order_id="20261020:17"),)).reasons == ("INVALID_KIS_ORDER_ID",)
    assert account_fills((_kis_fill(market="KRX"),)).reasons == ("INVALID_KIS_FILL_MARKET",)


def test_crypto_dates_and_orgs_cannot_be_used_to_evade_duplicate_detection():
    for venue in ("upbit", "okx"):
        fill = _fill(venue=venue)
        dated = replace(fill, order_date="20261020")
        org = replace(fill, broker_org_id="0042")
        assert account_fills((fill, dated)).reasons == ("UNEXPECTED_CRYPTO_ORDER_DATE",)
        assert account_fills((fill, org)).reasons == ("UNEXPECTED_CRYPTO_BROKER_ORG_ID",)
        other_market = replace(fill, market="USDT")
        assert account_fills((fill, other_market)).reasons == ("CONTRADICTORY_DUPLICATE_FILL",)
