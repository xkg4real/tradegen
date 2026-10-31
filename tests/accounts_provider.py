"""Exact synthetic account evidence, with no files, real credentials or network."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal, localcontext

from execution_accounts.model import (
    AccountBundle, AccountEvidence, AccountRestrictions, BrokerOrder, CashAmount,
    CashBalance, EvidencePage, ExternalFlow, FxRate, MarketTradeDate, Position,
    RiskBaseline,
)
from execution_accounts.provider import EvidenceError, ReconciledAccountProvider, assess_bundle, build_observation
from execution_control.risk import Fill

D = Decimal
NOW = datetime(2026, 10, 26, 1, tzinfo=timezone.utc)
SCOPE = "evidence-fixture"
SHA = "a" * 64


def bundle(now=NOW, *, fills=(), flows=(), orders=(), opening=D("1000000"), cash=None, units=None, price=D("120")):
    origin = now-timedelta(days=10)
    pages = tuple(EvidencePage(kind=kind, cursor=None, next_cursor=None, start=origin, end=now,
                              rows=rows, source_sha256=SHA)
                  for kind, rows in (("fills", fills), ("flows", flows), ("orders", orders)))
    positions = () if units is None else (Position(market="spot", symbol="KRW-BTC", base_currency="BTC",
        quote_currency="KRW", units=units, price=price, asof=now),)
    account = AccountEvidence(venue="upbit", account_scope=SCOPE, execution_quote="KRW", origin=origin,
        opening_cash=(CashAmount(currency="KRW", amount=opening),), opening_source_sha256=SHA,
        balances=(CashBalance(currency="KRW", total=opening if cash is None else cash,
                              settled=opening if cash is None else cash),), positions=positions,
        fx=(FxRate(currency="KRW", krw=D("1"), asof=now, source_sha256=SHA),), pages=pages,
        restrictions=AccountRestrictions(cash_mode="cash", borrowing_enabled=False, auto_loan=False,
            liabilities=(), asof=now, source_sha256=SHA), observed_at=now, server_time=now)
    baseline = RiskBaseline(day_start_equity=D("1000000"), prior_high_watermark=D("1000000"),
        observed_daily_loss=D("0"), approved_effective_floor=D("750000"),
        first_trading_day=(now-timedelta(days=5)).date(), asof=now, source_sha256=SHA)
    return AccountBundle(accounts=(account,), risk_baseline=baseline)


def change_account(value, **changes):
    return replace(value, accounts=(replace(value.accounts[0], **changes),))


def page_rows(value, kind, rows):
    account=value.accounts[0]
    return change_account(value, pages=tuple(replace(page, rows=rows, page_sha256="") if page.kind == kind else page
                                            for page in account.pages))


def refused(value, code=None, now=NOW):
    try:
        build_observation(value, now=now)
    except EvidenceError as exc:
        if code is not None:
            assert exc.code == code, (exc.code, code)
        return
    raise AssertionError("expected evidence refusal")


def fill(*, side="buy", quantity=D("2"), price=D("100"), fee=D("2"), order="buy1", fid="fill1", at=None):
    return Fill(venue="upbit", account_scope=SCOPE, order_id=order, fill_id=fid, market="spot", symbol="KRW-BTC",
        side=side, quantity=quantity, price=price, quote_currency="KRW", quote_krw=D("1"), fee_amount=fee,
        fee_currency="KRW", executed_at=at or NOW-timedelta(days=1), base_currency="BTC")


def order(*, side="buy", quantity=D("2"), filled=D("2"), price=D("100"), oid="buy1", client="client1", status="filled"):
    remaining = quantity-filled if status in ("open", "partial") else D("0")
    return BrokerOrder(client_id=client, order_id=oid, market="spot", symbol="KRW-BTC", side=side,
        quote_currency="KRW", quantity=quantity, filled_quantity=filled, remaining_quantity=remaining,
        limit_price=price, reserved_cash=remaining*price if side=="buy" else D("0"), status=status)


def test_complete_cash_only_account_constructs_e2_observation_but_no_execution_permission():
    value=bundle()
    observation=build_observation(value, now=NOW)
    assert observation.positions.equity_krw==1000000.0
    assert observation.settled_cash_krw=={('upbit',SCOPE):D('1000000')}
    assert observation.quote_currency_by_account=={('upbit',SCOPE):'KRW'}
    assert observation.quote_rates_krw=={('upbit',SCOPE,'KRW'):D('1')}
    assert observation.held_exposure_krw[('upbit',SCOPE)]==D('1000000')
    assert observation.inventory_exposure_krw[('upbit',SCOPE)]==0
    assert observation.risk.current_day_realized_net_profit==0
    assessment=assess_bundle(value,now=NOW)
    assert assessment.account_evidence_ready and not assessment.execution_ready
    assert SCOPE not in repr(assessment) and '1000000' not in repr(assessment)


def test_missing_empty_history_page_never_means_zero_activity():
    value=bundle()
    for kind in ('fills','flows','orders'):
        refused(change_account(value,pages=tuple(p for p in value.accounts[0].pages if p.kind!=kind)),
                'HISTORY_COVERAGE_MISSING')
    refused(change_account(value,pages=()),'HISTORY_COVERAGE_MISSING')


def test_cursor_chains_refuse_gaps_loops_early_terminals_and_unfinished_pages():
    value=bundle();account=value.accounts[0];original=account.pages[0]
    first=replace(original,next_cursor='next',page_sha256='')
    second=replace(original,cursor='next',page_sha256='')
    good=change_account(value,pages=(first,second,*account.pages[1:]))
    assert build_observation(good,now=NOW).fills==()
    for pages in ((first,*account.pages[1:]),
                  (first,replace(second,cursor='missing',page_sha256=''),*account.pages[1:]),
                  (original,second,*account.pages[1:]),
                  (first,replace(second,next_cursor='next',page_sha256=''),second,*account.pages[1:])):
        refused(change_account(value,pages=pages))


def test_history_window_source_digest_and_mutated_page_are_checked():
    value=bundle();account=value.accounts[0]
    for bad in (replace(account.pages[0],start=account.origin+timedelta(seconds=1),page_sha256=''),
                replace(account.pages[0],source_sha256='',page_sha256=''),
                replace(account.pages[0],page_sha256='f'*64)):
        refused(change_account(value,pages=(bad,*account.pages[1:])))
    page=replace(account.pages[0])
    object.__setattr__(page,'rows',(fill(),))
    refused(change_account(value,pages=(page,*account.pages[1:])),'PAGE_DIGEST_MISMATCH')


def test_exact_cash_inventory_fees_and_daily_fifo_profit_reconcile():
    buy=fill();sell=fill(side='sell',quantity=D('1'),price=D('120'),fee=D('1'),order='sell1',fid='fill2',at=NOW)
    value=bundle(fills=(buy,sell),opening=D('1000'),cash=D('917'),units=D('1'),
        orders=(order(),order(side='sell',quantity=D('1'),filled=D('1'),price=D('120'),oid='sell1',client='client2')))
    observation=build_observation(value,now=NOW)
    assert observation.risk.equity==D('1037')
    assert observation.risk.current_day_realized_net_profit==D('18')
    assert observation.risk.prior_day_realized_net_profit==0
    assert observation.reconciled_client_ids=={'client1','client2'}
    assert observation.held_exposure_krw[('upbit',SCOPE)]==D('1037')
    assert observation.inventory_exposure_krw[('upbit',SCOPE)]==D('120')
    assert observation.holdings[('upbit',SCOPE,'spot','KRW-BTC')]==D('1')


def test_missing_acquisition_fee_fx_or_changed_fill_identity_refuses():
    value=bundle(fills=(fill(),),opening=D('1000'),cash=D('798'),units=D('2'))
    for bad in (replace(fill(),fee_amount=None),replace(fill(),quote_krw=D('2')),
                replace(fill(),account_scope='different'),replace(fill(),base_currency='ETH')):
        refused(page_rows(value,'fills',(bad,)))
    sell=fill(side='sell',quantity=D('1'),fee=D('1'),order='sell')
    refused(page_rows(value,'fills',(sell,)),'FIFO_ACCOUNTING_REFUSED')


def test_identical_fills_and_flows_are_idempotent_but_contradictions_refuse():
    buy=fill();value=bundle(fills=(buy,buy),opening=D('1000'),cash=D('798'),units=D('2'))
    assert len(build_observation(value,now=NOW).fills)==1
    refused(page_rows(value,'fills',(buy,replace(buy,price=D('101')))),'FIFO_ACCOUNTING_REFUSED')
    deposit=ExternalFlow(flow_id='deposit',currency='KRW',kind='deposit',amount=D('50'),effective_at=NOW)
    value=bundle(flows=(deposit,deposit),opening=D('1000'),cash=D('1050'))
    assert build_observation(value,now=NOW).risk.equity==1050
    refused(page_rows(value,'flows',(deposit,replace(deposit,amount=D('51')))),'FLOW_ID_CONTRADICTION')


def test_deposits_change_equity_without_manufacturing_realized_profit():
    deposit=ExternalFlow(flow_id='funding',currency='KRW',kind='deposit',amount=D('500'),effective_at=NOW)
    value=bundle(opening=D('1000'),cash=D('1500'),flows=(deposit,))
    observation=build_observation(value,now=NOW)
    assert observation.risk.equity==1500 and observation.risk.current_day_realized_net_profit==0
    refused(page_rows(value,'flows',()),'CASH_RECONCILIATION_MISMATCH')
    refused(page_rows(value,'flows',(replace(deposit,kind='interest'),)),'FLOW_KIND_UNSUPPORTED')


def test_inventory_and_cash_mismatch_never_return_partial_observations():
    value=bundle(fills=(fill(),),opening=D('1000'),cash=D('798'),units=D('2'))
    refused(change_account(value,balances=(CashBalance(currency='KRW',total=D('799'),settled=D('799')),)),
            'CASH_RECONCILIATION_MISMATCH')
    refused(change_account(value,positions=()),'INVENTORY_RECONCILIATION_MISMATCH')
    refused(change_account(value,positions=(replace(value.accounts[0].positions[0],units=D('3')),)),
            'INVENTORY_RECONCILIATION_MISMATCH')


def test_cash_quote_binding_uses_only_one_settled_currency_not_portfolio_equity():
    value=bundle();account=value.accounts[0]
    account=replace(account,venue='okx',execution_quote='USDT',
        opening_cash=(CashAmount(currency='USDT',amount=D('100')),CashAmount(currency='USDC',amount=D('200'))),
        balances=(CashBalance(currency='USDT',total=D('100'),settled=D('80')),
                  CashBalance(currency='USDC',total=D('200'),settled=D('200'))),
        fx=(FxRate(currency='USDT',krw=D('1400'),asof=NOW,source_sha256=SHA),
            FxRate(currency='USDC',krw=D('1390'),asof=NOW,source_sha256=SHA)))
    observation=build_observation(replace(value,accounts=(account,)),now=NOW)
    assert observation.risk.equity==D('418000')
    assert observation.settled_cash_krw[('okx',SCOPE)]==D('112000')
    assert observation.quote_currency_by_account[('okx',SCOPE)]=='USDT'
    assert observation.quote_rates_krw=={('okx',SCOPE,'USDT'):D('1400'),('okx',SCOPE,'USDC'):D('1390')}
    assert observation.held_exposure_krw[('okx',SCOPE)]==D('418000')
    assert observation.positions.exposure['okx'].held_krw==418000.0
    assert observation.inventory_exposure_krw[('okx',SCOPE)]==0
    refused(replace(value,accounts=(replace(account,execution_quote='USD'),)),'EXECUTION_QUOTE_UNSUPPORTED')


def test_open_orders_stay_visible_as_reservations_and_promises():
    pending=order(quantity=D('1'),filled=D('0'),status='open',client='pending')
    value=bundle(opening=D('1000'),orders=(pending,))
    observation=build_observation(value,now=NOW)
    assert observation.positions.exposure['upbit'].reservations=={'pending':100.0}
    assert observation.settled_cash_krw[('upbit',SCOPE)]==1000
    buy=fill();sell=order(side='sell',quantity=D('1'),filled=D('0'),status='open',oid='sell',client='sell')
    observation=build_observation(bundle(fills=(buy,),opening=D('1000'),cash=D('798'),units=D('2'),orders=(sell,)),now=NOW)
    assert observation.positions.exposure['upbit'].promised_sell_units=={'BTC':1.0}


def test_order_fill_contradictions_and_unfunded_open_reservations_refuse():
    value=bundle(fills=(fill(),),opening=D('1000'),cash=D('798'),units=D('2'),orders=(order(),))
    refused(page_rows(value,'orders',(replace(order(),filled_quantity=D('1')),)),'ORDER_QUANTITY_CONTRADICTION')
    refused(page_rows(value,'orders',(replace(order(),order_id='wrong'),)),'ORDER_FILL_RECONCILIATION_MISMATCH')
    pending=order(quantity=D('20'),filled=D('0'),status='open')
    refused(bundle(opening=D('1000'),orders=(pending,)),'OPEN_BUY_EXCEEDS_SETTLED_CASH')


def test_account_clock_freshness_and_seoul_date_agreement_are_required():
    value=bundle()
    refused(change_account(value,observed_at=NOW-timedelta(seconds=31)),'EVIDENCE_STALE_OR_FUTURE')
    refused(change_account(value,server_time=NOW+timedelta(seconds=61)),'SERVER_CLOCK_OR_SEOUL_DAY_MISMATCH')
    boundary=NOW.replace(hour=15,minute=0,second=1)
    value=bundle(boundary)
    refused(change_account(value,server_time=boundary-timedelta(seconds=2)),
            'SERVER_CLOCK_OR_SEOUL_DAY_MISMATCH',now=boundary)
    previous=boundary-timedelta(seconds=10)
    old_pages=tuple(replace(page,end=previous,page_sha256='') for page in value.accounts[0].pages)
    refused(change_account(value,observed_at=previous,pages=old_pages),
            'ACCOUNT_HISTORY_NOT_CURRENT_SEOUL_DAY',now=boundary)


def test_stale_fx_prices_or_restrictions_are_not_relabelled_fresh():
    value=bundle(fills=(fill(),),opening=D('1000'),cash=D('798'),units=D('2'))
    account=value.accounts[0];old=NOW-timedelta(seconds=31)
    for changes in ({'fx':(replace(account.fx[0],asof=old),)},
                    {'positions':(replace(account.positions[0],asof=old),)},
                    {'restrictions':replace(account.restrictions,asof=old)}):
        refused(change_account(value,**changes),'EVIDENCE_STALE_OR_FUTURE')


def test_borrowing_liabilities_and_ambiguous_cash_settlement_refuse():
    value=bundle();restrictions=value.accounts[0].restrictions
    for changed in (replace(restrictions,borrowing_enabled=True),replace(restrictions,auto_loan=True),
                    replace(restrictions,cash_mode='margin'),replace(restrictions,borrowing_enabled=0)):
        refused(change_account(value,restrictions=changed),'CASH_ONLY_ACCOUNT_REQUIRED')
    refused(change_account(value,restrictions=replace(restrictions,liabilities=(CashAmount(currency='KRW',amount=D('1')),))),
            'ACCOUNT_LIABILITY_PRESENT')
    refused(change_account(value,balances=(CashBalance(currency='KRW',total=D('1000000'),settled=D('1000001')),)),
            'BALANCE_CONTRADICTION')


def test_numeric_float_bool_nonfinite_and_legacy_precision_loss_refuse():
    for amount in (True,1.0,D('NaN'),D('Infinity'),D('-1'),D('1e100')):
        value=bundle()
        refused(change_account(value,balances=(CashBalance(currency='KRW',total=amount,settled=amount),)))
    refused(bundle(opening=D('1000000.000000000000000000001')),'LEGACY_PRECISION_LOSS')
    with localcontext() as context:
        context.prec=2
        assert build_observation(bundle(opening=D('123456.789')),now=NOW).risk.equity==D('123456.789')


def test_explicit_kis_local_trade_date_is_not_inferred_from_seoul_date():
    value=bundle();account=value.accounts[0]
    account=replace(account,venue='kis',execution_quote='USD',
        opening_cash=(CashAmount(currency='USD',amount=D('1000')),),
        balances=(CashBalance(currency='USD',total=D('1000'),settled=D('1000')),),
        fx=(FxRate(currency='USD',krw=D('1400'),asof=NOW,source_sha256=SHA),))
    value=replace(value,accounts=(account,))
    refused(value,'KIS_CURRENT_TRADE_DATE_MISSING')
    date_row=MarketTradeDate(market='nasd',trade_date='20261025',asof=NOW,source_sha256=SHA)
    observation=build_observation(change_account(value,trade_dates=(date_row,)),now=NOW)
    assert observation.venue_trade_dates[('kis',SCOPE,'nasd')]=='20261025'
    refused(change_account(value,trade_dates=(replace(date_row,trade_date='20260230'),)),'KIS_TRADE_DATE_INVALID')


def test_unknown_or_duplicate_scopes_and_mixed_markets_fail_closed():
    value=bundle()
    refused(replace(value,accounts=(value.accounts[0],value.accounts[0])), 'MULTIPLE_ACCOUNTS_PER_VENUE_UNSUPPORTED')
    refused(change_account(value,account_scope=''), 'EVIDENCE_ID')
    value=bundle(fills=(fill(),),opening=D('1000'),cash=D('798'),units=D('2'))
    position=value.accounts[0].positions[0]
    refused(change_account(value,positions=(position,position)),'MULTIPLE_MARKETS_FOR_BASE_UNSUPPORTED')


def test_future_or_missing_risk_baseline_and_forged_first_day_refuse():
    value=bundle();baseline=value.risk_baseline
    for bad in (replace(baseline,source_sha256=''),replace(baseline,asof=NOW+timedelta(seconds=1)),
                replace(baseline,first_trading_day=(NOW+timedelta(days=1)).date()),
                replace(baseline,prior_high_watermark=D('1'))):
        refused(replace(value,risk_baseline=bad))
    first=build_observation(replace(value,risk_baseline=replace(baseline,first_trading_day=NOW.date())),now=NOW)
    assert first.risk.is_first_trading_day and first.risk.prior_day_realized_net_profit is None


def test_recent_cash_anchor_cannot_hide_the_prior_day_loss_history():
    value=bundle();account=value.accounts[0]
    origin=NOW-timedelta(hours=1)
    pages=tuple(replace(page,start=origin,page_sha256='') for page in account.pages)
    refused(change_account(value,origin=origin,pages=pages),'HISTORY_START_AFTER_FIRST_TRADING_DAY')


def test_nonsettlement_asset_cannot_be_relabelled_cash_to_erase_exposure():
    value=bundle()
    refused(change_account(value,opening_cash=(CashAmount(currency='BTC',amount=D('1')),)),
            'NONSETTLEMENT_CASH_CURRENCY_UNSUPPORTED')
    refused(change_account(value,fx=(*value.accounts[0].fx,
                FxRate(currency='BTC',krw=D('100'),asof=NOW,source_sha256=SHA))), 'FX_CURRENCY_UNSUPPORTED')
    flow=ExternalFlow(flow_id='not-cash',currency='BTC',kind='deposit',amount=D('1'),effective_at=NOW)
    refused(page_rows(value,'flows',(flow,)),'FLOW_CURRENCY_UNSUPPORTED')


def test_provider_failures_and_wrong_e1_input_are_sanitized_without_fallback():
    def bad_source(now):
        raise RuntimeError('secret account amount and credential must not be repeated')
    try:
        ReconciledAccountProvider(bad_source)(NOW)
    except EvidenceError as exc:
        assert str(exc)=='EVIDENCE_SOURCE_FAILED'
    else:
        raise AssertionError('expected provider failure')
    assert not assess_bundle({'ok':True,'cash':1000},now=NOW).account_evidence_ready
    seen=[]
    def source(now):
        seen.append(now)
        return bundle(now)
    assert ReconciledAccountProvider(source)(NOW).no_credit
    assert seen==[NOW]


def test_reconciled_provider_works_with_real_signed_controller_and_dry_run():
    from tests.control_session import signed_control
    from tests import compliance_fixtures as F
    value=bundle(F.NOW)
    # Bind the fixture's local account identifier without pretending to contact a broker.
    value=change_account(value,account_scope='fixture-account')
    observation=build_observation(value,now=F.NOW)
    with signed_control(observation=observation) as env:
        env.controller.account_provider=ReconciledAccountProvider(lambda now:value)
        assert env.controller.reserve(env.order,env.rules,session_id=env.session_id,now=env.now).status=='RESERVED'
        assert env.controller.dispatch(env.order.client_id,now=env.now).status=='ACKNOWLEDGED'
        assert len(env.adapter.requests)==1
