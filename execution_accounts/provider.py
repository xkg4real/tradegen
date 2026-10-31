"""Reconcile normalized exact evidence into the E2 account-provider interface.

No HTTP, file, credential, owner-log or wall-clock access occurs here. The
authenticated collector supplies identity, complete pages and an audited opening
anchor. A matching hash proves content integrity, not broker authenticity.
Readiness here describes account evidence, never permission to place an order.
"""
from __future__ import annotations

from collections.abc import Callable
from datetime import date, datetime, timedelta
from decimal import Decimal, DecimalException, Inexact, localcontext
import math
import re

from core.compliance import model as compliance
from execution_control.controller import AccountObservation
from execution_control.risk import Fill, RiskObservation, account_fills
from execution_accounts.model import (
    AccountBundle, AccountEvidence, AccountRestrictions, BrokerOrder, CashAmount,
    CashBalance, EvidenceAssessment, EvidencePage, ExternalFlow, FxRate, MarketTradeDate, Position,
    RiskBaseline, page_digest,
)

_ZERO = Decimal(0)
_ID = re.compile(r"[A-Za-z0-9_.:/-]{1,128}")
_CCY = re.compile(r"[A-Z][A-Z0-9]{0,11}")
_SHA = re.compile(r"[0-9a-f]{64}")
_STALE = timedelta(seconds=30)


class EvidenceError(ValueError):
    """Fixed diagnostic code; neither source rows nor personal values are quoted."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _require(condition, code):
    if not condition:
        raise EvidenceError(code)


def _id(value, code="EVIDENCE_ID"):
    _require(type(value) is str and _ID.fullmatch(value) is not None, code)
    return value


def _currency(value):
    _require(type(value) is str and _CCY.fullmatch(value) is not None, "CURRENCY_INVALID")
    return value


def _sha(value):
    _require(type(value) is str and _SHA.fullmatch(value) is not None, "SOURCE_DIGEST_REQUIRED")


def _instant(value):
    _require(type(value) is datetime and value.utcoffset() is not None, "AWARE_TIME_REQUIRED")
    return value


def _fresh(value, now):
    _instant(value)
    _require(timedelta(0) <= now-value <= _STALE, "EVIDENCE_STALE_OR_FUTURE")


def _amount(value, *, positive=False):
    _require(type(value) is Decimal and value.is_finite(), "EXACT_DECIMAL_REQUIRED")
    _require(len(value.as_tuple().digits) <= 60 and -40 <= value.as_tuple().exponent <= 40,
             "DECIMAL_RANGE_UNSUPPORTED")
    _require(value > 0 if positive else value >= 0, "AMOUNT_OUT_OF_RANGE")
    return value


def _legacy(value):
    output = float(value)
    _require(math.isfinite(output) and Decimal(str(output)) == value, "LEGACY_PRECISION_LOSS")
    return output


def _instrument(venue, market, symbol, quote):
    _id(market); _id(symbol); _currency(quote)
    if venue == "kis":
        _require(market in ("krx", "nasd", "nyse", "amex"), "INSTRUMENT_MARKET_UNSUPPORTED")
        _require(quote == ("KRW" if market == "krx" else "USD"), "INSTRUMENT_QUOTE_MISMATCH")
        _require(re.fullmatch(r"[0-9]{6}" if market == "krx" else r"[A-Z][A-Z0-9.]{0,19}", symbol) is not None,
                 "INSTRUMENT_SYMBOL_UNSUPPORTED")
        return symbol
    _require(market == "spot", "INSTRUMENT_MARKET_UNSUPPORTED")
    parts = symbol.split("-")
    _require(len(parts) == 2, "INSTRUMENT_SYMBOL_UNSUPPORTED")
    base, represented_quote = (parts[1], parts[0]) if venue == "upbit" else (parts[0], parts[1])
    _currency(base)
    _require(represented_quote == quote and base != quote, "INSTRUMENT_QUOTE_MISMATCH")
    _require(quote == "KRW" if venue == "upbit" else quote in ("USDT", "USDC"),
             "INSTRUMENT_QUOTE_UNSUPPORTED")
    return base


def _identity(venue, scope, record):
    _id(record.order_id)
    if venue != "kis":
        _require(record.order_date == "" and record.broker_org_id == "", "CRYPTO_BROKER_IDENTITY_INVALID")
        return venue, scope, record.order_id
    _require(type(record.order_date) is str and re.fullmatch(r"[0-9]{8}", record.order_date) is not None,
             "KIS_TRADE_DATE_REQUIRED")
    try:
        datetime.strptime(record.order_date, "%Y%m%d")
    except ValueError:
        raise EvidenceError("KIS_TRADE_DATE_INVALID") from None
    _require(re.fullmatch(r"[0-9]{1,20}", record.order_id) is not None, "KIS_ORDER_ID_INVALID")
    org = record.broker_org_id
    _require(type(org) is str and (not org or re.fullmatch(r"[0-9]{1,20}", org) is not None),
             "KIS_BROKER_ORG_INVALID")
    _require(record.market != "krx" or bool(org), "KIS_BROKER_ORG_REQUIRED")
    return venue, scope, record.market, record.order_date, org, record.order_id


def _pages(account, kind):
    pages = [p for p in account.pages if p.kind == kind]
    _require(bool(pages), "HISTORY_COVERAGE_MISSING")
    cursor, seen, rows = None, set(), []
    for index, page in enumerate(pages):
        _require(type(page) is EvidencePage and type(page.rows) is tuple, "PAGE_SCHEMA_INVALID")
        _sha(page.source_sha256); _sha(page.page_sha256)
        _require(page.page_sha256 == page_digest(page), "PAGE_DIGEST_MISMATCH")
        _require(page.start == account.origin and page.end == account.observed_at,
                 "HISTORY_WINDOW_INCOMPLETE")
        _require(page.cursor == cursor and page.cursor not in seen, "PAGINATION_GAP_OR_LOOP")
        if page.cursor is not None:
            _id(page.cursor, "CURSOR_INVALID")
        if page.next_cursor is not None:
            _id(page.next_cursor, "CURSOR_INVALID")
        seen.add(page.cursor)
        _require(index == len(pages)-1 or page.next_cursor is not None, "PAGINATION_AFTER_TERMINAL")
        cursor = page.next_cursor
        rows.extend(page.rows)
    _require(cursor is None, "PAGINATION_INCOMPLETE")
    return tuple(rows)


def _dedupe(rows, key, code):
    seen = {}
    for row in rows:
        identity = key(row)
        _require(identity not in seen or seen[identity] == row, code)
        seen[identity] = row
    return tuple(seen.values())


def _account(account, now):
    _require(type(account) is AccountEvidence and account.venue in ("kis", "upbit", "okx"),
             "ACCOUNT_SCHEMA_INVALID")
    _id(account.account_scope); _currency(account.execution_quote)
    supported_quotes = {"upbit": ("KRW",), "okx": ("USDT", "USDC"), "kis": ("KRW", "USD")}
    _require(account.execution_quote in supported_quotes[account.venue], "EXECUTION_QUOTE_UNSUPPORTED")
    _instant(account.origin); _fresh(account.observed_at, now); _instant(account.server_time)
    _require(account.observed_at.astimezone(compliance.KST).date() == now.astimezone(compliance.KST).date(),
             "ACCOUNT_HISTORY_NOT_CURRENT_SEOUL_DAY")
    _require(account.origin <= account.observed_at, "OPENING_ANCHOR_AFTER_SNAPSHOT")
    _require(abs(now-account.server_time) <= timedelta(seconds=60)
             and now.astimezone(compliance.KST).date() == account.server_time.astimezone(compliance.KST).date(),
             "SERVER_CLOCK_OR_SEOUL_DAY_MISMATCH")
    _sha(account.opening_source_sha256)
    for name in ("opening_cash", "balances", "positions", "fx", "pages", "trade_dates"):
        _require(type(getattr(account, name)) is tuple, "ACCOUNT_COLLECTION_INVALID")
    _require(all(type(p) is EvidencePage and p.kind in ("fills", "flows", "orders") for p in account.pages),
             "PAGE_KIND_UNSUPPORTED")
    restrictions = account.restrictions
    _require(type(restrictions) is AccountRestrictions, "RESTRICTIONS_REQUIRED")
    _fresh(restrictions.asof, now); _sha(restrictions.source_sha256)
    _require(restrictions.cash_mode == "cash" and restrictions.borrowing_enabled is False
             and restrictions.auto_loan is False, "CASH_ONLY_ACCOUNT_REQUIRED")
    for row in restrictions.liabilities:
        _require(type(row) is CashAmount, "LIABILITY_SCHEMA_INVALID")
        _currency(row.currency); _amount(row.amount)
        _require(row.amount == 0, "ACCOUNT_LIABILITY_PRESENT")
    opening, balances, fx = {}, {}, {}
    for row in account.opening_cash:
        _require(type(row) is CashAmount, "OPENING_CASH_SCHEMA_INVALID")
        _currency(row.currency); _amount(row.amount)
        _require(row.currency in supported_quotes[account.venue], "NONSETTLEMENT_CASH_CURRENCY_UNSUPPORTED")
        _require(row.currency not in opening, "DUPLICATE_OPENING_CURRENCY")
        opening[row.currency] = row.amount
    _require(bool(opening), "OPENING_CASH_ANCHOR_REQUIRED")
    for row in account.balances:
        _require(type(row) is CashBalance, "BALANCE_SCHEMA_INVALID")
        _currency(row.currency); _amount(row.total); _amount(row.settled)
        _require(row.currency in supported_quotes[account.venue], "NONSETTLEMENT_CASH_CURRENCY_UNSUPPORTED")
        _require(row.settled <= row.total and row.currency not in balances, "BALANCE_CONTRADICTION")
        balances[row.currency] = row
    for row in account.fx:
        _require(type(row) is FxRate, "FX_SCHEMA_INVALID")
        _currency(row.currency); _amount(row.krw, positive=True); _fresh(row.asof, now); _sha(row.source_sha256)
        _require(row.currency in supported_quotes[account.venue], "FX_CURRENCY_UNSUPPORTED")
        _require(row.currency not in fx and (row.currency != "KRW" or row.krw == 1), "FX_CONTRADICTION")
        fx[row.currency] = row.krw
    _require(account.execution_quote in balances and account.execution_quote in fx, "SPENDABLE_CURRENCY_MISSING")
    _require(set(opening) <= set(balances) and set(balances) <= set(fx), "CASH_CURRENCY_OR_FX_MISSING")
    fills = _pages(account, "fills")
    for fill in fills:
        _require(type(fill) is Fill, "FILL_SCHEMA_INVALID")
        _require((fill.venue, fill.account_scope) == (account.venue, account.account_scope), "FILL_ACCOUNT_MISMATCH")
        _instant(fill.executed_at)
        _require(account.origin <= fill.executed_at <= account.observed_at, "FILL_OUTSIDE_COVERAGE")
        base = _instrument(account.venue, fill.market, fill.symbol, fill.quote_currency)
        _require(not fill.base_currency or fill.base_currency == base, "FILL_BASE_CURRENCY_MISMATCH")
    accounting = account_fills(fills)
    _require(accounting.ok, "FIFO_ACCOUNTING_REFUSED")
    flows = _pages(account, "flows")
    for flow in flows:
        _require(type(flow) is ExternalFlow, "FLOW_SCHEMA_INVALID")
        _id(flow.flow_id); _currency(flow.currency); _amount(flow.amount, positive=True); _instant(flow.effective_at)
        _require(flow.currency in supported_quotes[account.venue], "FLOW_CURRENCY_UNSUPPORTED")
        _require(flow.kind in ("deposit", "withdrawal"), "FLOW_KIND_UNSUPPORTED")
        _require(account.origin <= flow.effective_at <= account.observed_at, "FLOW_OUTSIDE_COVERAGE")
    flows = _dedupe(flows, lambda row: row.flow_id, "FLOW_ID_CONTRADICTION")
    reconstructed = dict(opening)
    for _, _, currency, amount in accounting.cash_deltas_by_currency:
        reconstructed[currency] = reconstructed.get(currency, _ZERO) + amount
    for flow in flows:
        reconstructed[flow.currency] = reconstructed.get(flow.currency, _ZERO) + (
            flow.amount if flow.kind == "deposit" else -flow.amount)
    _require(set(reconstructed) <= set(balances), "CASH_HISTORY_CURRENCY_MISSING")
    _require(all(row.total == reconstructed.get(currency, _ZERO) for currency, row in balances.items()),
             "CASH_RECONCILIATION_MISMATCH")
    actual, bases, marked, holdings = {}, set(), _ZERO, {}
    for position in account.positions:
        _require(type(position) is Position, "POSITION_SCHEMA_INVALID")
        base = _instrument(account.venue, position.market, position.symbol, position.quote_currency)
        _require(position.base_currency == base, "POSITION_BASE_CURRENCY_MISMATCH")
        _amount(position.units); _amount(position.price, positive=True); _fresh(position.asof, now)
        _require(base not in bases, "MULTIPLE_MARKETS_FOR_BASE_UNSUPPORTED")
        _require(position.quote_currency in fx, "POSITION_FX_MISSING")
        bases.add(base)
        key = (account.venue, account.account_scope, position.market, position.symbol)
        actual[key] = position.units
        holdings[(account.venue, base)] = _legacy(position.units)
        marked += position.units * position.price * fx[position.quote_currency]
    expected = {tuple(row[:4]): row[4] for row in accounting.inventory}
    _require(all(actual.get(key, _ZERO) == quantity for key, quantity in expected.items())
             and all(expected.get(key, _ZERO) == quantity for key, quantity in actual.items()),
             "INVENTORY_RECONCILIATION_MISMATCH")
    orders = _pages(account, "orders")
    for order in orders:
        _require(type(order) is BrokerOrder, "ORDER_SCHEMA_INVALID")
        _identity(account.venue, account.account_scope, order)
    orders = _dedupe(orders, lambda row: _identity(account.venue, account.account_scope, row), "ORDER_ID_CONTRADICTION")
    reservations, promises, reconciled, cancelable, trade_dates = {}, {}, set(), {}, {}
    reserved_by_currency = {}
    used_clients = set()
    for order in orders:
        base = _instrument(account.venue, order.market, order.symbol, order.quote_currency)
        _require(order.side in ("buy", "sell"), "ORDER_SIDE_INVALID")
        _require(order.status in ("open", "partial", "filled", "canceled", "rejected"), "ORDER_STATUS_UNSUPPORTED")
        _require(type(order.client_id) is str, "CLIENT_ID_INVALID")
        if order.client_id:
            _id(order.client_id)
            _require(order.client_id not in used_clients, "CLIENT_ID_DUPLICATED")
            used_clients.add(order.client_id)
        for value in (order.filled_quantity, order.remaining_quantity, order.reserved_cash):
            _amount(value)
        _amount(order.quantity, positive=True); _amount(order.limit_price, positive=True)
        _require(order.filled_quantity <= order.quantity, "ORDER_QUANTITY_CONTRADICTION")
        active = order.status in ("open", "partial")
        _require(order.remaining_quantity == (order.quantity-order.filled_quantity if active else _ZERO),
                 "ORDER_QUANTITY_CONTRADICTION")
        _require(order.status != "filled" or order.filled_quantity == order.quantity, "ORDER_QUANTITY_CONTRADICTION")
        _require(order.status not in ("open", "rejected") or order.filled_quantity == 0, "ORDER_QUANTITY_CONTRADICTION")
        _require(order.status != "partial" or 0 < order.filled_quantity < order.quantity, "ORDER_QUANTITY_CONTRADICTION")
        identity = _identity(account.venue, account.account_scope, order)
        matching = [f for f in accounting.accepted_fills if _identity(account.venue, account.account_scope, f) == identity]
        _require(sum((f.quantity for f in matching), _ZERO) == order.filled_quantity
                 and all((f.market, f.symbol, f.side) == (order.market, order.symbol, order.side) for f in matching),
                 "ORDER_FILL_RECONCILIATION_MISMATCH")
        if order.client_id:
            reconciled.add(order.client_id)
        if order.cancelable_quantity is not None:
            _amount(order.cancelable_quantity)
            _require(order.cancelable_quantity <= order.remaining_quantity, "CANCELABLE_QUANTITY_CONTRADICTION")
            if order.client_id:
                cancelable[order.client_id] = order.cancelable_quantity
        if active and order.side == "buy":
            _require(order.quote_currency in fx and order.reserved_cash >= order.remaining_quantity*order.limit_price,
                     "ORDER_CASH_RESERVATION_INCOMPLETE")
            reservations[order.client_id or "broker:"+order.order_id] = _legacy(order.reserved_cash*fx[order.quote_currency])
            reserved_by_currency[order.quote_currency] = reserved_by_currency.get(order.quote_currency, _ZERO)+order.reserved_cash
        else:
            _require(order.reserved_cash == 0, "UNEXPECTED_CASH_RESERVATION")
        if active and order.side == "sell":
            promises[base] = promises.get(base, _ZERO)+order.remaining_quantity
    _require(all(amount <= Decimal(str(holdings.get((account.venue, base), 0))) for base, amount in promises.items()),
             "OPEN_SELL_EXCEEDS_HOLDING")
    _require(all(currency in balances and amount <= balances[currency].settled
                 for currency, amount in reserved_by_currency.items()), "OPEN_BUY_EXCEEDS_SETTLED_CASH")
    # Trade dates are supplied separately by the collector, not guessed from the
    # local or Seoul date; historical orders cannot establish today's KIS date.
    if account.venue != "kis":
        _require(not account.trade_dates, "CRYPTO_TRADE_DATE_UNEXPECTED")
    for row in account.trade_dates:
        _require(type(row) is MarketTradeDate and row.market in ("krx", "nasd", "nyse", "amex"),
                 "KIS_MARKET_DATE_INVALID")
        _fresh(row.asof, now); _sha(row.source_sha256)
        _require(type(row.trade_date) is str and re.fullmatch(r"[0-9]{8}", row.trade_date) is not None,
                 "KIS_TRADE_DATE_REQUIRED")
        try:
            datetime.strptime(row.trade_date, "%Y%m%d")
        except ValueError:
            raise EvidenceError("KIS_TRADE_DATE_INVALID") from None
        key = (account.venue, account.account_scope, row.market)
        _require(key not in trade_dates, "KIS_TRADE_DATE_DUPLICATED")
        trade_dates[key] = row.trade_date
    if account.venue == "kis":
        _require(bool(trade_dates) and (account.execution_quote != "KRW" or
                 (account.venue, account.account_scope, "krx") in trade_dates), "KIS_CURRENT_TRADE_DATE_MISSING")
        _require(all((account.venue, account.account_scope, p.market) in trade_dates for p in account.positions),
                 "KIS_CURRENT_TRADE_DATE_MISSING")
    cash_equity = sum((row.total*fx[currency] for currency, row in balances.items()), _ZERO)
    exposure = compliance.Exposure(held_krw=_legacy(cash_equity+marked), reservations=reservations,
                                  promised_sell_units={base: _legacy(value) for base, value in promises.items()})
    available = balances[account.execution_quote].settled*fx[account.execution_quote]
    return dict(equity=cash_equity+marked, marked=marked, available=available, holdings=holdings,
                exact_holdings=actual, exposure=exposure, fills=accounting.accepted_fills,
                daily=accounting.realized_by_account_day_krw, reconciled=reconciled,
                cancelable=cancelable, trade_dates=trade_dates, clients=used_clients, rates=fx)


def build_observation(bundle: AccountBundle, *, now: datetime) -> AccountObservation:
    """Return E2 data after exact reconciliation, or raise a redacted EvidenceError.

This does not check/sign/arm owner state or grant an execution permit. A source
must provide genuine account data; internally consistent forged rows are not
authenticated by these mathematical checks.
"""
    try:
        with localcontext() as numeric:
            numeric.prec = 512
            numeric.traps[Inexact] = True
            return _build(bundle, now)
    except EvidenceError:
        raise
    except (ValueError, TypeError, AttributeError, KeyError, DecimalException, OverflowError):
        raise EvidenceError("EVIDENCE_SCHEMA_OR_ARITHMETIC_INVALID") from None


def _build(bundle, now):
    _instant(now)
    _require(type(bundle) is AccountBundle and type(bundle.accounts) is tuple and 0 < len(bundle.accounts) <= 3,
             "ACCOUNT_BUNDLE_REQUIRED")
    baseline = bundle.risk_baseline
    _require(type(baseline) is RiskBaseline, "RISK_BASELINE_REQUIRED")
    _fresh(baseline.asof, now); _sha(baseline.source_sha256)
    today = now.astimezone(compliance.KST).date()
    _require(baseline.asof.astimezone(compliance.KST).date() == today, "RISK_DAY_MISMATCH")
    _require(type(baseline.first_trading_day) is date and baseline.first_trading_day <= today, "FIRST_TRADING_DAY_INVALID")
    _amount(baseline.day_start_equity, positive=True); _amount(baseline.prior_high_watermark)
    _amount(baseline.observed_daily_loss)
    _require(baseline.prior_high_watermark >= baseline.day_start_equity, "HIGH_WATERMARK_CONTRADICTION")
    if baseline.approved_effective_floor is not None:
        _amount(baseline.approved_effective_floor)
    scopes, cash, holdings, exact_holdings, exposures, held, inventory, quotes, rates = {}, {}, {}, {}, {}, {}, {}, {}, {}
    fills, days, stamps, server_stamps, all_clients = [], [], [], [], set()
    reconciled, cancelable, trade_dates = set(), {}, {}
    equity = _ZERO
    for account in bundle.accounts:
        _require(type(account) is AccountEvidence, "ACCOUNT_SCHEMA_INVALID")
        _require(account.venue not in scopes, "MULTIPLE_ACCOUNTS_PER_VENUE_UNSUPPORTED")
        _instant(account.origin)
        _require(account.origin.astimezone(compliance.KST).date() <= baseline.first_trading_day,
                 "HISTORY_START_AFTER_FIRST_TRADING_DAY")
        result = _account(account, now)
        _require(not all_clients.intersection(result['clients']), "CROSS_ACCOUNT_CLIENT_ID_COLLISION")
        all_clients.update(result['clients'])
        key = (account.venue, account.account_scope)
        scopes[account.venue] = account.account_scope
        cash[key], held[key], quotes[key] = result['available'], result['equity'], account.execution_quote
        inventory[key] = result['marked']
        rates.update({(*key,currency): rate for currency,rate in result['rates'].items()})
        holdings.update(result['holdings']); exact_holdings.update(result['exact_holdings'])
        exposures[account.venue] = result['exposure']
        equity += result['equity']; fills.extend(result['fills']); days.extend(result['daily'])
        stamps.append(account.observed_at); server_stamps.append(account.server_time)
        reconciled.update(result['reconciled']); cancelable.update(result['cancelable'])
        trade_dates.update(result['trade_dates'])
    _require(equity > 0, "NONPOSITIVE_EQUITY")
    _require(max(server_stamps)-min(server_stamps) <= timedelta(seconds=60), "VENUE_CLOCK_DISAGREEMENT")
    asof = min(stamps)
    current = sum((amount for _, _, day, amount in days if day == today), _ZERO)
    previous = sum((amount for _, _, day, amount in days if day == today-timedelta(days=1)), _ZERO)
    first = baseline.first_trading_day == today
    observation = RiskObservation(equity=equity, prior_high_watermark=baseline.prior_high_watermark,
        day_start_equity=baseline.day_start_equity, current_day_realized_net_profit=current,
        prior_day_realized_net_profit=None if first else previous, observed_daily_loss=baseline.observed_daily_loss,
        approved_effective_floor=baseline.approved_effective_floor, is_first_trading_day=first, asof=asof)
    return AccountObservation(positions=compliance.Positions(equity_krw=_legacy(equity), holdings=holdings,
        exposure=exposures), account_scopes=scopes, settled_cash_krw=cash, holdings=exact_holdings,
        risk=observation, asof=asof, server_time=min(server_stamps), no_credit=True, fills=tuple(fills),
        reconciled_client_ids=frozenset(reconciled), venue_trade_dates=trade_dates,
        cancellable_quantities=cancelable, held_exposure_krw=held, quote_currency_by_account=quotes,
        inventory_exposure_krw=inventory, quote_rates_krw=rates)


def assess_bundle(bundle: AccountBundle, *, now: datetime) -> EvidenceAssessment:
    """Sanitized data readiness; even a successful assessment grants no execution permission."""
    try:
        observation = build_observation(bundle, now=now)
    except EvidenceError as exc:
        return EvidenceAssessment(account_evidence_ready=False, execution_ready=False,
                                  reasons=(exc.code,), account_count=0, fill_count=0)
    return EvidenceAssessment(account_evidence_ready=True, execution_ready=False,
                              reasons=("OWNER_SESSION_AND_EXECUTION_CHECKS_SEPARATE",),
                              account_count=len(observation.account_scopes), fill_count=len(observation.fills))


class ReconciledAccountProvider:
    """Explicit collector injection; no hidden default or fallback to E1 snapshots."""

    def __init__(self, evidence_source: Callable[[datetime], AccountBundle]):
        if not callable(evidence_source):
            raise ValueError("evidence source must be callable")
        self._source = evidence_source

    def __call__(self, now: datetime) -> AccountObservation:
        try:
            bundle = self._source(now)
        except Exception:
            raise EvidenceError("EVIDENCE_SOURCE_FAILED") from None
        return build_observation(bundle, now=now)
