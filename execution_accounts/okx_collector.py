"""Reconcile an explicitly supplied OKX v5 cash-spot capture. No default transport.

The source must return SourceReceipt for each fetch(path, params). The reviewed
opening statement covers the main trading pocket, with empty inventory, no
orders and no assets in other pockets. This reader supports a quiescent capture
within the two-hour retention of incompletely filled canceled orders. Transfers,
rebates, margin and other pockets need additional evidence and are refused.
See docs/superpowers/plans/wip-2026-10-24/venues/okx.md sections 5.1–5.9.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal, Inexact, localcontext
import re

from execution.okx_inquiry import ALGO_TYPES, self_check
from execution_accounts.collector import CoverageEvidence, SourceReceipt, digest, identifier, instant, number, require
from execution_accounts.model import (
    AccountBundle, AccountEvidence, AccountRestrictions, BrokerOrder, CashAmount,
    CashBalance, EvidencePage, FxRate, Position, RiskBaseline, content_digest,
)
from execution_accounts.provider import EvidenceError, build_observation
from execution_control.risk import Fill

_CONFIG = "/api/v5/account/config"
_BALANCE = "/api/v5/account/balance"
_PENDING = "/api/v5/trade/orders-pending"
_HISTORY = "/api/v5/trade/orders-history"
_FILLS = "/api/v5/trade/fills"
_BILLS = "/api/v5/account/bills"
_QUOTES = ("USDT", "USDC")
_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)
_ZERO = Decimal(0)


@dataclass(frozen=True, kw_only=True)
class OkxOpeningAnchor:
    account_scope: str
    uid_sha256: str  # content_digest of the privately reviewed main UID string
    origin: datetime
    opening_cash: tuple[CashAmount, ...]
    inventory_and_open_orders: str
    source_sha256: str


@dataclass(frozen=True, kw_only=True)
class OkxCollection:
    bundle: AccountBundle
    receipts: tuple[SourceReceipt, ...]
    anchor: OkxOpeningAnchor
    coverage: CoverageEvidence
    fill_fx: tuple[FxRate, ...]
    manifest_sha256: str


def _rows(value):
    require(type(value) is list and all(type(row) is dict for row in value), "OKX_ROWS_INVALID")
    return value


def _one(rows):
    require(len(rows) == 1, "OKX_SINGLE_RECORD_REQUIRED")
    return rows[0]


def _digits(value):
    require(type(value) is str and re.fullmatch(r"[1-9][0-9]{0,31}", value) is not None, "OKX_NUMERIC_ID_INVALID")
    return value


def _at(ms):
    require(type(ms) is str and re.fullmatch(r"[0-9]{1,15}", ms) is not None, "OKX_TIMESTAMP_REQUIRED")
    return _EPOCH + timedelta(milliseconds=int(ms))


def _ccy(value):
    require(type(value) is str and re.fullmatch(r"[A-Z][A-Z0-9]{0,11}", value) is not None, "OKX_CURRENCY_INVALID")
    return value


def _pair(row):
    market = row.get("instId")
    require(row.get("instType") == "SPOT" and type(market) is str, "OKX_SPOT_INSTRUMENT_REQUIRED")
    parts = market.split("-")
    require(len(parts) == 2 and parts[1] in _QUOTES and _ccy(parts[0]) not in _QUOTES, "OKX_PAIR_UNSUPPORTED")
    return parts


class _Archive:
    def __init__(self, source, scope, start, limit):
        self.source, self.scope, self.start, self.limit = source, scope, start, limit
        self.receipts = []
        self.byte_count = 0

    def read(self, path, params=()):
        require(len(self.receipts) < self.limit, "OKX_CAPTURE_REQUEST_LIMIT")
        try:
            r = self.source.fetch(path, params)
        except Exception:
            raise EvidenceError("OKX_ARCHIVE_READ_FAILED") from None
        require(type(r) is SourceReceipt and (r.path, r.params, r.account_scope) == (path, params, self.scope),
                "OKX_RECEIPT_SCOPE_MISMATCH")
        lower = self.receipts[-1].received_at if self.receipts else self.start
        require(lower <= instant(r.received_at) <= self.start + timedelta(seconds=30)
                and abs(instant(r.server_time) - r.received_at) <= timedelta(seconds=60),
                "OKX_RECEIPT_TIME_INVALID")
        require(type(r.raw_body) is bytes, "OKX_RECEIPT_BYTES_REQUIRED")
        self.byte_count += len(r.raw_body)
        require(self.byte_count <= 32 * 1024 * 1024, "OKX_ARCHIVE_BYTE_LIMIT")
        envelope = r.decode()
        require(type(envelope) is dict and envelope.get("code") == "0", "OKX_ARCHIVE_RESPONSE_FAILED")
        self.receipts.append(r)
        return _rows(envelope.get("data"))

    def pages(self, path, cursor_key, params=()):
        # A short page can be intermediate. Require forward progress to an explicit empty response.
        query = (*params, ("limit", "100"))
        cursor = None
        result = []
        while True:
            rows = self.read(path, (*query, ("after", cursor)) if cursor else query)
            if not rows:
                return result
            require(len(rows) <= 100, "OKX_PAGE_OVERSIZED")
            for row in rows:
                next_id = _digits(row.get(cursor_key))
                require(cursor is None or int(next_id) < int(cursor), "OKX_PAGINATION_NOT_DESCENDING")
                cursor = next_id
            result.extend(rows)


def _check_config(archive, anchor):
    row = _one(archive.read(_CONFIG))
    uid = _digits(row.get("uid"))
    require(not self_check(row) and row.get("type") == "0" and row.get("mainUid") == uid
            and content_digest(uid) == digest(anchor.uid_sha256), "OKX_MAIN_READONLY_SPOT_REQUIRED")


def _check_other_pockets(archive, origin):
    require(not archive.read("/api/v5/account/positions"), "OKX_DERIVATIVE_OR_MARGIN_POSITION")
    for row in archive.read("/api/v5/asset/balances"):
        require(all(number(row.get(key)) == 0 for key in ("bal", "availBal", "frozenBal")),
                "OKX_FUNDING_POCKET_NOT_EMPTY")
    valuation = _one(archive.read("/api/v5/asset/asset-valuation", (("ccy", "USDT"),)))
    details = valuation.get("details")
    require(type(details) is dict and set(details) <= {"funding", "earn", "trading", "classic"}
            and all(number(details.get(key)) == 0 for key in ("funding", "earn"))
            and ("classic" not in details or number(details["classic"]) == 0), "OKX_OTHER_POCKET_EXPOSURE")
    require(not archive.read("/api/v5/finance/savings/balance"), "OKX_SAVINGS_UNSUPPORTED")
    for row in archive.read("/api/v5/finance/flexible-loan/loan-info"):
        require(not _rows(row.get("loanData")), "OKX_LOAN_UNSUPPORTED")
    for path in ("/api/v5/asset/deposit-history", "/api/v5/asset/withdrawal-history"):
        # Historical funding activity cannot establish a trading-pocket deposit.
        # The timestamp cursor is ambiguous on ties, so pages() rejects them.
        for row in archive.pages(path, "ts"):
            require(_at(row.get("ts")) < origin and row.get("state") == "2",
                    "OKX_EXTERNAL_FLOW_OR_PENDING_MOVEMENT")
    for kind in ALGO_TYPES:
        require(not archive.read("/api/v5/trade/orders-algo-pending", (("ordType", kind),)), "OKX_ALGO_UNSUPPORTED")


def _balances(archive):
    balances = {}
    rows = _rows(_one(archive.read(_BALANCE)).get("details"))
    for row in rows:
        currency = _ccy(row.get("ccy"))
        total, locked = number(row.get("cashBal")), number(row.get("frozenBal"))
        require(currency not in balances and total == locked + number(row.get("availBal"))
                and number(row.get("eq")) == total, "OKX_BALANCE_CONTRADICTION")
        require(number(row.get("liab")) == 0 and row.get("autoLendStatus") in ("unsupported", "off")
                and row.get("autoLendMtAmt") is not None
                and (row["autoLendMtAmt"] == "" or number(row["autoLendMtAmt"]) == 0),
                "OKX_LIABILITY_OR_LENDING")
        balances[currency] = (total, locked)
    return balances


def _order(row, *, pending, origin, cutoff):
    _, quote = _pair(row)
    side = row.get("side")
    require(side in ("buy", "sell") and row.get("tdMode") == "cash" and row.get("ordType") == "limit",
            "OKX_CASH_LIMIT_ORDER_REQUIRED")
    created, updated = _at(row.get("cTime")), _at(row.get("uTime"))
    require(origin <= created <= updated <= cutoff, "OKX_ORDER_OUTSIDE_WINDOW")
    oid = _digits(row.get("ordId"))
    client = row.get("clOrdId")
    require(type(client) is str and re.fullmatch(r"[A-Za-z0-9]{0,32}", client) is not None, "OKX_CLIENT_ID_INVALID")
    states = {"live": "open", "partially_filled": "partial"} if pending else {"filled": "filled", "canceled": "canceled"}
    require(row.get("state") in states, "OKX_ORDER_STATE_INVALID")
    quantity, filled = number(row.get("sz"), positive=True), number(row.get("accFillSz"))
    price = number(row.get("px"), positive=True)
    remaining = quantity - filled if pending else _ZERO
    return BrokerOrder(client_id=client, order_id=oid, market="spot", symbol=row["instId"], side=side,
        quote_currency=quote, quantity=quantity, filled_quantity=filled, remaining_quantity=remaining,
        limit_price=price, reserved_cash=remaining * price if side == "buy" else _ZERO,
        status=states[row["state"]], cancelable_quantity=remaining)


def _historical_rates(rates):
    require(type(rates) is tuple, "OKX_EXECUTION_FX_REQUIRED")
    by_time = {}
    for rate in rates:
        require(type(rate) is FxRate and rate.currency in _QUOTES and type(rate.krw) is Decimal,
                "OKX_EXECUTION_FX_REQUIRED")
        digest(rate.source_sha256)
        number(rate.krw, positive=True, json_number=True)
        key = (rate.currency, instant(rate.asof))
        require(key not in by_time, "OKX_DUPLICATE_EXECUTION_FX")
        by_time[key] = rate.krw
    return by_time


def _fee(raw):
    require(type(raw) is str, "OKX_SIGNED_FEE_REQUIRED")
    debited = raw.startswith("-")
    amount = number(raw[1:] if debited else raw)
    require(debited or amount == 0, "OKX_REBATE_OR_THIRD_CURRENCY_FEE")
    return amount


def _fill(row, scope, order, rate, at):
    base, quote = _pair(row)
    require(order.symbol == row["instId"] and order.side == row.get("side")
            and order.client_id == row.get("clOrdId"), "OKX_FILL_ORDER_MISMATCH")
    fee = _fee(row.get("fee"))
    fee_ccy = _ccy(row.get("feeCcy"))
    require(fee_ccy in (base, quote), "OKX_REBATE_OR_THIRD_CURRENCY_FEE")
    price = number(row.get("fillPx"), positive=True)
    require(price <= order.limit_price if order.side == "buy" else price >= order.limit_price, "OKX_FILL_LIMIT_MISMATCH")
    # OKX trade IDs are instrument scoped; bind them to the instrument in the normalized ID.
    return Fill(venue="okx", account_scope=scope, order_id=order.order_id,
                fill_id=order.symbol + ":" + _digits(row.get("tradeId")), market="spot", symbol=order.symbol,
                side=order.side, quantity=number(row.get("fillSz"), positive=True), price=price,
                quote_currency=quote, quote_krw=rate, fee_amount=fee, fee_currency=fee_ccy,
                executed_at=at, base_currency=base)


def _collect(source, *, anchor, coverage, risk_baseline, execution_quote, current_fx, fill_fx, clock, max_requests):
    require(type(anchor) is OkxOpeningAnchor and type(coverage) is CoverageEvidence
            and type(risk_baseline) is RiskBaseline and callable(clock), "OKX_REVIEWED_EVIDENCE_REQUIRED")
    require(type(max_requests) is int and 1 <= max_requests <= 1000, "OKX_CAPTURE_LIMIT_INVALID")
    start, origin = instant(clock()), instant(anchor.origin)
    scope = identifier(source.account_scope)
    require(scope == anchor.account_scope == coverage.account_scope, "OKX_ACCOUNT_SCOPE_MISMATCH")
    require(anchor.inventory_and_open_orders == "verified-zero" and type(anchor.opening_cash) is tuple
            and execution_quote in _QUOTES and type(current_fx) is tuple, "OKX_CASH_ANCHOR_REQUIRED")
    digest(anchor.source_sha256)
    digest(coverage.source_sha256)
    require(origin <= start and instant(coverage.history_from) <= origin
            and instant(coverage.quiescent_from) <= start and coverage.identity_binding == "reviewed-credential-to-main-pocket"
            and coverage.history_retention == "reviewed-complete-since-origin"
            and coverage.transfer_scope == "reviewed-no-external-flows-or-pocket-transfers"
            and coverage.account_mode == "reviewed-okx-main-cash-spot-only", "OKX_COVERAGE_INCOMPLETE")
    require(start - origin < timedelta(hours=2), "OKX_CANCELED_ORDER_RETENTION_EXCEEDED")
    archive = _Archive(source, scope, start, max_requests)
    _check_config(archive, anchor)
    _check_other_pockets(archive, origin)
    balances = _balances(archive)
    pending = archive.pages(_PENDING, "ordId")
    terminal = archive.pages(_HISTORY, "ordId", (("instType", "SPOT"),))
    orders, order_times, order_fees, locks = {}, {}, {}, {}
    for active, rows in ((True, pending), (False, terminal)):
        for row in rows:
            times = (_at(row.get("cTime")), _at(row.get("uTime")))
            require(times[0] <= times[1] <= start, "OKX_ORDER_OUTSIDE_WINDOW")
            if not active and times[1] < origin:
                continue
            order = _order(row, pending=active, origin=origin, cutoff=start)
            oid = order.order_id
            require(oid not in orders, "OKX_ORDER_ID_CONFLICT")
            orders[oid] = order
            order_times[oid] = times
            rebate = row.get("rebate")
            require(rebate == "" or number(rebate) == 0, "OKX_ORDER_REBATE_UNSUPPORTED")
            fee = row.get("fee")
            paid = _ZERO if not order.filled_quantity and fee == "" else _fee(fee)
            fee_ccy = row.get("feeCcy")
            require((paid == 0 and fee_ccy == "") or fee_ccy in _pair(row), "OKX_ORDER_FEE_CURRENCY_INVALID")
            order_fees[oid] = (paid, fee_ccy)
            if active:
                ccy = order.quote_currency if order.side == "buy" else _pair(row)[0]
                amount = order.reserved_cash if order.side == "buy" else order.remaining_quantity
                locks[ccy] = locks.get(ccy, _ZERO) + amount
    for ccy in set(balances) | set(locks):
        require(locks.get(ccy, _ZERO) == balances.get(ccy, (_ZERO, _ZERO))[1], "OKX_UNEXPLAINED_FROZEN_BALANCE")

    rates = _historical_rates(fill_fx)
    used_rates, fills, trades, paid_by_order = set(), [], {}, {}
    for row in archive.pages(_FILLS, "billId"):
        at = _at(row.get("fillTime"))
        require(at <= _at(row.get("ts")) <= start, "OKX_FILL_UNMATCHED_OR_OUTSIDE_WINDOW")
        if at < origin:
            continue
        order = orders.get(_digits(row.get("ordId")))
        require(order is not None and order_times[order.order_id][0] <= at <= order_times[order.order_id][1],
                "OKX_FILL_UNMATCHED_OR_OUTSIDE_WINDOW")
        key = (order.quote_currency, at)
        require(key in rates, "OKX_EXECUTION_FX_REQUIRED")
        fill = _fill(row, scope, order, rates[key], at)
        require(fill.fill_id not in trades, "OKX_DUPLICATE_FILL")
        if fill.fee_amount:
            require(fill.fee_currency == order_fees[order.order_id][1], "OKX_ORDER_FEE_MISMATCH")
        paid_by_order[order.order_id] = paid_by_order.get(order.order_id, _ZERO) + fill.fee_amount
        used_rates.add(key)
        trades[fill.fill_id] = fill
        fills.append(fill)
    require(all(paid_by_order.get(oid, _ZERO) == fee for oid, (fee, _) in order_fees.items()),
            "OKX_ORDER_FEE_MISMATCH")
    require(used_rates == set(rates), "OKX_UNUSED_EXECUTION_FX")
    _check_bills(archive, trades, origin, start)

    positions = []
    for ccy, (amount, _) in sorted(balances.items()):
        if ccy in _QUOTES or amount == 0:
            continue
        # Preserve the acquisition market for FIFO, even if an alternative pair trades the same base.
        pairs = {f.symbol for f in fills if f.base_currency == ccy}
        require(len(pairs) == 1, "OKX_INVENTORY_MARKET_UNPROVEN")
        symbol, = pairs
        ticker = _one(archive.read("/api/v5/market/ticker", (("instId", symbol),)))
        require(ticker.get("instId") == symbol and _pair(ticker)[0] == ccy, "OKX_MARKET_SCOPE_MISMATCH")
        # Bid on the timestamped ticker is a contemporary liquidation mark, not last-trade time.
        positions.append(Position(market="spot", symbol=symbol, base_currency=ccy, quote_currency=_pair(ticker)[1],
                                  units=amount, price=number(ticker.get("bidPx"), positive=True), asof=_at(ticker.get("ts"))))
    require(_balances(archive) == balances and archive.pages(_PENDING, "ordId") == pending,
            "OKX_ACCOUNT_CHANGED_DURING_CAPTURE")
    _check_config(archive, anchor)
    end = instant(clock())
    require(start <= end <= start + timedelta(seconds=30) and archive.receipts[-1].received_at <= end
            and end <= instant(coverage.history_through) and end <= instant(coverage.quiescent_until),
            "OKX_CAPTURE_WINDOW_INCOMPLETE")
    require(end - origin < timedelta(hours=2), "OKX_CANCELED_ORDER_RETENTION_EXCEEDED")
    manifest = content_digest((anchor, coverage, risk_baseline, execution_quote, current_fx, fill_fx,
        tuple((r.path, r.params, r.account_scope, r.received_at, r.server_time, r.sha256) for r in archive.receipts)))
    pages = tuple(EvidencePage(kind=k, cursor=None, next_cursor=None, start=origin, end=end,
                rows=tuple(rows), source_sha256=manifest) for k, rows in (("fills", fills), ("orders", orders.values()), ("flows", ())))
    account = AccountEvidence(venue="okx", account_scope=scope, execution_quote=execution_quote, origin=origin,
        opening_cash=anchor.opening_cash, opening_source_sha256=anchor.source_sha256,
        balances=tuple(CashBalance(currency=c, total=bal[0], settled=bal[0]) for c, bal in sorted(balances.items()) if c in _QUOTES),
        positions=tuple(positions), fx=current_fx, pages=pages, restrictions=AccountRestrictions(cash_mode="cash",
            borrowing_enabled=False, auto_loan=False, liabilities=(), asof=end, source_sha256=manifest),
        observed_at=end, server_time=archive.receipts[-1].server_time)
    bundle = AccountBundle(accounts=(account,), risk_baseline=risk_baseline)
    build_observation(bundle, now=end)
    return OkxCollection(bundle=bundle, receipts=tuple(archive.receipts), anchor=anchor, coverage=coverage,
                         fill_fx=fill_fx, manifest_sha256=manifest)


def _check_bills(archive, trades, origin, cutoff):
    # Require a balanced ledger entry for both legs of each fill, including the charged fee.
    ledger = {}
    for row in archive.pages(_BILLS, "billId"):
        at = _at(row.get("ts"))
        if at < origin:
            continue
        require(at <= cutoff and row.get("type") == "2" and row.get("mgnMode") == "cash"
                and row.get("interest") in ("", "0"), "OKX_NONTRADE_BILL_UNSUPPORTED")
        base, quote = _pair(row)
        key = row["instId"] + ":" + _digits(row.get("tradeId"))
        fill = trades.get(key)
        currency = _ccy(row.get("ccy"))
        require(fill is not None and row.get("ordId") == fill.order_id and currency in (base, quote)
                and at >= fill.executed_at, "OKX_BILL_FILL_MISMATCH")
        change = row.get("balChg")
        require(type(change) is str, "OKX_BILL_AMOUNT_INVALID")
        delta = -number(change[1:]) if change.startswith("-") else number(change)
        ledger[(key, currency)] = ledger.get((key, currency), _ZERO) + delta
    for key, fill in trades.items():
        base = fill.quantity if fill.side == "buy" else -fill.quantity
        quote = -base * fill.price
        base -= fill.fee_amount if fill.fee_currency == fill.base_currency else _ZERO
        quote -= fill.fee_amount if fill.fee_currency == fill.quote_currency else _ZERO
        require(ledger.get((key, fill.base_currency)) == base and ledger.get((key, fill.quote_currency)) == quote,
                "OKX_BILL_FILL_MISMATCH")


def collect_okx(source, *, anchor: OkxOpeningAnchor, coverage: CoverageEvidence, risk_baseline: RiskBaseline,
                execution_quote: str, current_fx: tuple[FxRate, ...], fill_fx: tuple[FxRate, ...], clock,
                max_requests: int = 100) -> OkxCollection:
    """Capture from a reviewed offline source or raise EvidenceError.

    Supply sourced KRW marks for every settlement currency in current_fx, and
    one sourced quote/KRW fix per (currency, execution instant) in fill_fx.
    The source authenticity, rate evidence and coverage review belong to the
    caller. The manifest preserves those references and the raw receipt chain.
    """
    try:
        with localcontext() as context:
            context.prec = 512
            context.traps[Inexact] = True
            return _collect(source, anchor=anchor, coverage=coverage, risk_baseline=risk_baseline,
                            execution_quote=execution_quote, current_fx=current_fx, fill_fx=fill_fx,
                            clock=clock, max_requests=max_requests)
    except EvidenceError:
        raise
    except (ValueError, TypeError, KeyError, AttributeError, ArithmeticError):
        raise EvidenceError("OKX_EVIDENCE_SCHEMA_INVALID") from None
