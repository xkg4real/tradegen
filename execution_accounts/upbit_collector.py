"""Conservative Upbit KRW main-pocket collector over E1 authenticated GETs.

The source is explicit; importing this module sends nothing. API pagination does
not establish retention, identity or atomicity. Reviewed coverage evidence is
mandatory. Unsupported cash flows, order types and ambiguous fees refuse.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal, Inexact, localcontext
import os
from pathlib import Path
import re

from core.isolation import checked_target
from core.compliance.model import KST
from execution.transport import inquiry_clock, request
from execution_accounts.collector import (
    CoverageEvidence, OpeningAnchor, SourceReceipt, TradeFeeEvidence,
    digest, identifier, instant, number, require, when,
)
from execution_accounts.model import (
    AccountBundle, AccountEvidence, AccountRestrictions, BrokerOrder, CashAmount,
    CashBalance, EvidencePage, ExternalFlow, FxRate, Position, RiskBaseline, content_digest,
)
from execution_accounts.provider import EvidenceError, build_observation
from execution_control.risk import Fill

_ZERO = Decimal(0)
_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)
_WEEK_MS = 7 * 86400 * 1000
_CCY = re.compile(r"[A-Z][A-Z0-9]{0,11}")
_ALLOWED = frozenset({"/v1/accounts", "/v1/orders/open", "/v1/orders/closed", "/v1/order",
                      "/v1/deposits", "/v1/withdraws", "/v1/ticker"})


class E1UpbitSource:
    """Explicit production binding. No implicit clock, credentials or home.

    Credential *names* must already be present in the process environment before
    every call. E1 alone reads their values; therefore its .env fallback is never
    selected. Caller controls the environment exclusively during collection.
    This object does not prove that its credentials belong to ``account_scope``;
    the reviewed identity binding in CoverageEvidence must establish that.
    """

    def __init__(self, *, account_scope: str, state_directory: Path, clock):
        self.account_scope = identifier(account_scope)
        require(callable(clock), "COLLECTOR_CLOCK_REQUIRED")
        self.clock = clock
        self.state_directory = Path(state_directory)
        self._preflight()

    def _preflight(self):
        require(self.state_directory.is_absolute(), "COLLECTOR_EXPLICIT_HOME_REQUIRED")
        configured = os.environ.get("TRADEGEN_HOME")
        require(type(configured) is str and bool(configured)
                and Path(configured).is_absolute()
                and Path(configured).resolve() == self.state_directory.resolve(),
                "COLLECTOR_EXPLICIT_HOME_REQUIRED")
        require(all(name in os.environ for name in ("UPBIT_ACCESS_KEY", "UPBIT_SECRET_KEY")),
                "COLLECTOR_ENV_CREDENTIAL_NAMES_REQUIRED")
        try:
            checked_target(self.state_directory, "collector state")
            instant(self.clock())
        except (ValueError, RuntimeError, OSError):
            raise EvidenceError("COLLECTOR_PREFLIGHT_REFUSED") from None

    def fetch(self, path: str, params: tuple[tuple[str, str], ...]) -> SourceReceipt:
        require(path in _ALLOWED, "COLLECTOR_ENDPOINT_REFUSED")
        self._preflight()
        try:
            with inquiry_clock(self.clock):
                if path == "/v1/accounts":
                    answer = request("upbit", "GET", "/v1/accounts", params)
                elif path == "/v1/orders/open":
                    answer = request("upbit", "GET", "/v1/orders/open", params)
                elif path == "/v1/orders/closed":
                    answer = request("upbit", "GET", "/v1/orders/closed", params)
                elif path == "/v1/order":
                    answer = request("upbit", "GET", "/v1/order", params)
                elif path == "/v1/deposits":
                    answer = request("upbit", "GET", "/v1/deposits", params)
                elif path == "/v1/withdraws":
                    answer = request("upbit", "GET", "/v1/withdraws", params)
                else:
                    answer = request("upbit", "GET", "/v1/ticker", params)
        except Exception:
            raise EvidenceError("COLLECTOR_AUTHENTICATED_READ_FAILED") from None
        require(answer.server_utc is not None, "COLLECTOR_SERVER_TIME_REQUIRED")
        result = SourceReceipt(path=path, params=tuple(params), account_scope=self.account_scope,
            received_at=answer.received_utc, server_time=answer.server_utc,
            raw_body=answer.raw_body, sha256=answer.sha256)
        result.decode()
        return result


@dataclass(frozen=True, kw_only=True)
class CollectionResult:
    bundle: AccountBundle
    receipts: tuple[SourceReceipt, ...]
    manifest_sha256: str


def _rows(value):
    require(type(value) is list and all(type(row) is dict for row in value), "COLLECTOR_ROWS_INVALID")
    return value


def _ccy(value):
    require(type(value) is str and _CCY.fullmatch(value) is not None, "COLLECTOR_CURRENCY_INVALID")
    return value


def _market(value):
    require(type(value) is str and value.startswith("KRW-"), "COLLECTOR_KRW_SPOT_REQUIRED")
    base = _ccy(value[4:])
    require(base != "KRW", "COLLECTOR_MARKET_INVALID")
    return base


def _ms(value):
    delta = instant(value) - _EPOCH
    return (delta.days * 86400 + delta.seconds) * 1000 + delta.microseconds // 1000


def _merge(rows, other):
    for row in other:
        key = identifier(row.get("uuid"))
        require(key not in rows or rows[key] == row, "COLLECTOR_DUPLICATE_CONTRADICTION")
        rows[key] = row


class _Capture:
    def __init__(self, source, scope, start, *, max_requests, max_rows):
        self.source, self.scope, self.start = source, scope, start
        self.max_requests, self.max_rows = max_requests, max_rows
        self.receipts = []
        self.row_count = 0

    def get(self, path, params=()):
        require(len(self.receipts) < self.max_requests, "COLLECTOR_REQUEST_BOUND_EXCEEDED")
        receipt = self.source.fetch(path, tuple(params))
        require(type(receipt) is SourceReceipt and receipt.path == path and receipt.params == tuple(params)
                and receipt.account_scope == self.scope, "COLLECTOR_RECEIPT_SCOPE_MISMATCH")
        instant(receipt.received_at); instant(receipt.server_time)
        require(receipt.received_at >= self.start, "COLLECTOR_RECEIPT_BEFORE_CAPTURE")
        require(not self.receipts or receipt.received_at >= self.receipts[-1].received_at,
                "COLLECTOR_RECEIPT_CLOCK_REGRESSED")
        require(abs(receipt.server_time-receipt.received_at) <= timedelta(seconds=60),
                "COLLECTOR_SERVER_CLOCK_MISMATCH")
        body = receipt.decode()
        self.receipts.append(receipt)
        self.row_count += len(body) if type(body) is list else 1
        require(self.row_count <= self.max_rows, "COLLECTOR_ROW_BOUND_EXCEEDED")
        return body

    def pages(self, path, *, states=()):
        rows = {}
        page = 1
        while True:
            body = _rows(self.get(path, (*(("states[]", value) for value in states),
                                        ("page", str(page)), ("limit", "100"), ("order_by", "asc"))))
            require(len(body) <= 100, "COLLECTOR_PAGE_LIMIT_EXCEEDED")
            # Numbered pages must make progress; boundary duplication is not a cursor proof.
            require(not any(row.get("uuid") in rows for row in body), "COLLECTOR_PAGE_OVERLAP")
            _merge(rows, body)
            if len(body) < 100:
                return rows
            page += 1

    def closed(self, origin, cutoff):
        result = {}
        pending = []
        # Make boundary timestamps interior to at least one query. The public
        # contract does not promise inclusive boundaries or millisecond tie order.
        lo = _ms(origin) - 1
        last = _ms(cutoff) + (1 if cutoff.microsecond % 1000 else 0) + 1
        while lo < last:
            hi = min(lo + _WEEK_MS, last)
            pending.append((lo, hi))
            if hi == last:
                break
            lo = hi - 1
        if not pending:
            pending.append((lo, last))
        while pending:
            lo, hi = pending.pop()
            body = _rows(self.get("/v1/orders/closed", (("states[]", "done"), ("states[]", "cancel"),
                ("start_time", str(lo)), ("end_time", str(hi)), ("limit", "1000"), ("order_by", "asc"))))
            require(len(body) <= 1000, "COLLECTOR_PAGE_LIMIT_EXCEEDED")
            for row in body:
                at = when(row.get("created_at"))
                require(lo <= _ms(at) <= hi, "COLLECTOR_CLOSED_WINDOW_MISMATCH")
                require(row.get("state") in ("done", "cancel"), "COLLECTOR_CLOSED_STATE_INVALID")
            if len(body) == 1000:
                require(hi-lo > 2, "COLLECTOR_SATURATED_TIMESTAMP")
                mid = (lo+hi)//2
                pending.extend(((lo, mid+1), (mid, hi)))
            else:
                _merge(result, body)
        # The millisecond query rounds down; prior-origin rows are outside the reviewed anchor.
        return {key: row for key, row in result.items() if when(row.get("created_at")) >= origin}


def _validate_proofs(anchor, coverage, baseline, scope, start):
    require(type(anchor) is OpeningAnchor and type(coverage) is CoverageEvidence
            and type(baseline) is RiskBaseline, "COLLECTOR_REVIEWED_EVIDENCE_REQUIRED")
    require(identifier(anchor.account_scope) == identifier(coverage.account_scope) == scope,
            "COLLECTOR_COVERAGE_SCOPE_MISMATCH")
    digest(anchor.source_sha256); digest(coverage.source_sha256)
    require(type(anchor.cash_krw) is Decimal, "COLLECTOR_EXACT_ANCHOR_REQUIRED")
    number(anchor.cash_krw, json_number=True)
    origin = instant(anchor.origin)
    require(origin <= start and anchor.inventory_and_open_orders == "verified-zero",
            "COLLECTOR_ZERO_INVENTORY_AND_OPEN_ORDERS_ANCHOR_REQUIRED")
    require(instant(coverage.history_from) <= origin
            and instant(coverage.history_through) >= start,
            "COLLECTOR_HISTORY_RETENTION_EVIDENCE_REQUIRED")
    require(instant(coverage.quiescent_from) <= start <= instant(coverage.quiescent_until),
            "COLLECTOR_QUIESCENT_CAPTURE_EVIDENCE_REQUIRED")
    require(coverage.identity_binding == "reviewed-credential-to-main-pocket"
            and coverage.history_retention == "reviewed-complete-since-origin"
            and coverage.transfer_scope == "reviewed-no-unreported-flows-or-pocket-transfers"
            and coverage.account_mode == "reviewed-krw-spot-cash-only",
            "COLLECTOR_SOURCE_OBLIGATIONS_UNRESOLVED")
    return origin


def _fees(order_id, rows, paid, evidence, consumed):
    supplied = [item for item in evidence if item.order_id == order_id]
    if supplied:
        require(len(supplied) == len(rows), "COLLECTOR_FEE_COVERAGE_INCOMPLETE")
        result = {}
        for item in supplied:
            digest(item.source_sha256); identifier(item.fill_id)
            require(type(item.fee_krw) is Decimal, "COLLECTOR_EXACT_FEE_REQUIRED")
            amount = number(item.fee_krw, json_number=True)
            require(item.fill_id not in result, "COLLECTOR_DUPLICATE_FEE_EVIDENCE")
            result[item.fill_id] = amount
            consumed.add((order_id, item.fill_id))
        require(set(result) == {row.get("uuid") for row in rows} and sum(result.values(), _ZERO) == paid,
                "COLLECTOR_FEE_RECONCILIATION_MISMATCH")
        return result
    require(rows or paid == 0, "COLLECTOR_FEE_WITHOUT_TRADES")
    require(len(rows) <= 1 or paid == 0, "COLLECTOR_PER_TRADE_FEE_EVIDENCE_REQUIRED")
    return {identifier(row.get("uuid")): paid if len(rows) == 1 else _ZERO for row in rows}


def _order(detail, listed, scope, origin, cutoff, fee_evidence, consumed):
    require(type(detail) is dict, "COLLECTOR_ORDER_DETAIL_REQUIRED")
    order_id = identifier(detail.get("uuid"))
    # Cross-check every shared accounting field, not just the order UUID.
    for key in ("uuid", "market", "side", "ord_type", "state", "created_at", "volume", "remaining_volume",
                "executed_volume", "price", "locked", "paid_fee", "trades_count", "identifier"):
        if key in listed:
            require(key in detail and listed[key] == detail[key], "COLLECTOR_ORDER_CHANGED_DURING_CAPTURE")
    require(origin <= when(detail.get("created_at")) <= cutoff, "COLLECTOR_ORDER_OUTSIDE_ANCHOR")
    symbol = detail.get("market"); base = _market(symbol)
    require(detail.get("side") in ("bid", "ask"), "COLLECTOR_ORDER_SIDE_INVALID")
    side = "buy" if detail["side"] == "bid" else "sell"
    # Market/best/watch orders need separate quantity and reservation semantics.
    require(detail.get("ord_type") == "limit" and detail.get("state") in ("wait", "done", "cancel"),
            "COLLECTOR_ORDER_TYPE_OR_STATE_UNSUPPORTED")
    quantity = number(detail.get("volume"), positive=True)
    executed = number(detail.get("executed_volume")); remaining = number(detail.get("remaining_volume"))
    price = number(detail.get("price"), positive=True); locked = number(detail.get("locked"))
    paid = number(detail.get("paid_fee"))
    require(executed + remaining == quantity, "COLLECTOR_ORDER_QUANTITY_MISMATCH")
    active = detail["state"] == "wait"
    require(not active or remaining > 0, "COLLECTOR_ACTIVE_ORDER_EMPTY")
    require(active or locked == 0, "COLLECTOR_TERMINAL_RESERVATION_PRESENT")
    require(detail["state"] != "done" or remaining == 0, "COLLECTOR_DONE_ORDER_INCOMPLETE")
    trades = _rows(detail.get("trades"))
    require(type(detail.get("trades_count")) is int and detail["trades_count"] == len(trades),
            "COLLECTOR_TRADE_DETAILS_INCOMPLETE")
    fee_map = _fees(order_id, trades, paid, fee_evidence, consumed)
    fills = []; seen = set()
    for row in trades:
        fill_id = identifier(row.get("uuid"))
        require(fill_id not in seen, "COLLECTOR_DUPLICATE_TRADE")
        seen.add(fill_id)
        require(row.get("market") == symbol and row.get("side") == detail["side"],
                "COLLECTOR_TRADE_ORDER_MISMATCH")
        at = when(row.get("created_at"))
        require(when(detail["created_at"]) <= at <= cutoff, "COLLECTOR_TRADE_OUTSIDE_CAPTURE")
        units = number(row.get("volume"), positive=True); trade_price = number(row.get("price"), positive=True)
        require(number(row.get("funds"), positive=True) == units*trade_price, "COLLECTOR_TRADE_FUNDS_MISMATCH")
        fills.append(Fill(venue="upbit", account_scope=scope, order_id=order_id, fill_id=fill_id, market="spot",
            symbol=symbol, side=side, quantity=units, price=trade_price, quote_currency="KRW", quote_krw=Decimal(1),
            fee_amount=fee_map[fill_id], fee_currency="KRW", executed_at=at, base_currency=base))
    require(sum((fill.quantity for fill in fills), _ZERO) == executed, "COLLECTOR_EXECUTED_VOLUME_MISMATCH")
    if active and side == "sell":
        require(locked == remaining, "COLLECTOR_SELL_LOCK_MISMATCH")
    status = ("partial" if executed else "open") if active else ("filled" if detail["state"] == "done" else "canceled")
    client = detail.get("identifier") or ""
    require(type(client) is str, "COLLECTOR_CLIENT_ID_INVALID")
    if client:
        identifier(client)
    order = BrokerOrder(client_id=client, order_id=order_id, market="spot", symbol=symbol, side=side,
        quote_currency="KRW", quantity=quantity, filled_quantity=executed,
        remaining_quantity=remaining if active else _ZERO, limit_price=price,
        reserved_cash=locked if active and side == "buy" else _ZERO, status=status,
        cancelable_quantity=remaining if active else _ZERO)
    return order, fills, (base, locked if active and side == "sell" else _ZERO)


def _flows(rows, kind, origin, cutoff):
    result = []
    for key, row in rows.items():
        created = when(row.get("created_at"))
        require(created <= cutoff, "COLLECTOR_FLOW_AFTER_CUTOFF")
        state = "ACCEPTED" if kind == "deposit" else "DONE"
        require(row.get("state") == state, "COLLECTOR_PENDING_OR_REVERSED_FLOW_UNSUPPORTED")
        at = when(row.get("done_at"))
        require(created <= at <= cutoff, "COLLECTOR_FLOW_TIME_INVALID")
        if at < origin:
            continue
        require(row.get("currency") == "KRW" and row.get("transaction_type") == "default",
                "COLLECTOR_EXTERNAL_FLOW_UNSUPPORTED")
        require(number(row.get("fee")) == 0, "COLLECTOR_FLOW_FEE_CONVENTION_UNREVIEWED")
        require(row.get("type") == ("deposit" if kind == "deposit" else "withdraw"),
                "COLLECTOR_FLOW_KIND_MISMATCH")
        result.append(ExternalFlow(flow_id=kind+":"+key, currency="KRW", kind=kind,
            amount=number(row.get("amount"), positive=True), effective_at=at))
    return result


def collect_upbit(source, *, anchor: OpeningAnchor, coverage: CoverageEvidence,
                  risk_baseline: RiskBaseline, clock, trade_fees: tuple[TradeFeeEvidence, ...] = (),
                  max_requests: int = 2000, max_rows: int = 100000) -> CollectionResult:
    """Capture, normalize and reconcile; return no bundle on any unresolved gap.

    Source injection is a trusted boundary for offline broker archives/tests.
    Use E1UpbitSource for real authenticated reads after owner setup. No default
    source exists. Full-history scanning is bounded; a large account needs a
    separately reviewed archival adapter rather than silently truncated history.
    """
    try:
        with localcontext() as context:
            context.prec = 512
            context.traps[Inexact] = True
            return _collect(source, anchor, coverage, risk_baseline, clock, trade_fees, max_requests, max_rows)
    except EvidenceError:
        raise
    except (ValueError, TypeError, KeyError, AttributeError, ArithmeticError, OverflowError):
        raise EvidenceError("COLLECTOR_SOURCE_SCHEMA_INVALID") from None


def _collect(source, anchor, coverage, baseline, clock, trade_fees, max_requests, max_rows):
    require(callable(clock), "COLLECTOR_CLOCK_REQUIRED")
    require(type(max_requests) is int and 1 <= max_requests <= 10000
            and type(max_rows) is int and 1 <= max_rows <= 1000000, "COLLECTOR_BOUNDS_INVALID")
    require(type(trade_fees) is tuple and all(type(item) is TradeFeeEvidence for item in trade_fees),
            "COLLECTOR_FEE_EVIDENCE_INVALID")
    start = instant(clock()); scope = identifier(source.account_scope)
    origin = _validate_proofs(anchor, coverage, baseline, scope, start)
    capture = _Capture(source, scope, start, max_requests=max_requests, max_rows=max_rows)
    first_balances = _rows(capture.get("/v1/accounts"))
    open_rows = capture.pages("/v1/orders/open", states=("wait", "watch"))
    closed_rows = capture.closed(origin, start)
    require(not (set(open_rows) & set(closed_rows)), "COLLECTOR_ORDER_STATE_CHANGED")
    listed = dict(closed_rows); _merge(listed, list(open_rows.values()))
    deposits = capture.pages("/v1/deposits")
    withdrawals = capture.pages("/v1/withdraws")
    orders = []; fills = []; sell_locks = {}; consumed = set()
    for oid, row in sorted(listed.items()):
        detail = capture.get("/v1/order", (("uuid", oid),))
        order, trades, (base, locked) = _order(detail, row, scope, origin, start, trade_fees, consumed)
        orders.append(order); fills.extend(trades)
        sell_locks[base] = sell_locks.get(base, _ZERO) + locked
    require(consumed == {(item.order_id, item.fill_id) for item in trade_fees}
            and len(consumed) == len(trade_fees), "COLLECTOR_UNUSED_OR_DUPLICATE_FEE_EVIDENCE")
    if fills:
        require(min(fill.executed_at.astimezone(KST).date() for fill in fills) == baseline.first_trading_day,
                "COLLECTOR_FIRST_TRADING_DAY_CONTRADICTS_HISTORY")
    flows = _flows(deposits, "deposit", origin, start) + _flows(withdrawals, "withdrawal", origin, start)
    balances = {}; locks = {}
    for row in first_balances:
        currency = _ccy(row.get("currency"))
        require(currency not in balances, "COLLECTOR_DUPLICATE_BALANCE")
        locked = number(row.get("locked")); total = number(row.get("balance")) + locked
        balances[currency] = total; locks[currency] = locked
    require("KRW" in balances, "COLLECTOR_KRW_BALANCE_REQUIRED")
    require(locks["KRW"] == sum((order.reserved_cash for order in orders), _ZERO),
            "COLLECTOR_CASH_LOCK_RECONCILIATION_MISMATCH")
    require(all(locks.get(base, _ZERO) == sell_locks.get(base, _ZERO)
                for base in (set(locks) | set(sell_locks)) - {"KRW"}), "COLLECTOR_ASSET_LOCK_RECONCILIATION_MISMATCH")
    markets = tuple(sorted("KRW-"+base for base, amount in balances.items() if base != "KRW" and amount > 0))
    marks = {}
    if markets:
        for row in _rows(capture.get("/v1/ticker", (("markets", ",".join(markets)),))):
            symbol = row.get("market"); _market(symbol)
            require(symbol in markets and symbol not in marks, "COLLECTOR_TICKER_SCOPE_MISMATCH")
            require(type(row.get("timestamp")) is int and type(row.get("trade_timestamp")) is int,
                    "COLLECTOR_TICKER_TIME_REQUIRED")
            require(row["trade_timestamp"] <= row["timestamp"], "COLLECTOR_TICKER_TIME_CONTRADICTION")
            marks[symbol] = (number(row.get("trade_price"), positive=True, json_number=True),
                             _EPOCH + timedelta(milliseconds=row["trade_timestamp"]),
                             _EPOCH + timedelta(milliseconds=row["timestamp"]))
        require(set(marks) == set(markets), "COLLECTOR_TICKER_COVERAGE_INCOMPLETE")
    # This detects many races; the external fence is still required (ABA is possible).
    require(_rows(capture.get("/v1/accounts")) == first_balances, "COLLECTOR_BALANCES_CHANGED_DURING_CAPTURE")
    require(capture.pages("/v1/orders/open", states=("wait", "watch")) == open_rows,
            "COLLECTOR_OPEN_ORDERS_CHANGED_DURING_CAPTURE")
    require(capture.pages("/v1/deposits") == deposits and capture.pages("/v1/withdraws") == withdrawals,
            "COLLECTOR_FLOWS_CHANGED_DURING_CAPTURE")
    observed = instant(clock())
    require(start <= observed <= coverage.quiescent_until and observed <= coverage.history_through,
            "COLLECTOR_COVERAGE_ENDED_DURING_CAPTURE")
    require(all(start <= receipt.received_at <= observed for receipt in capture.receipts),
            "COLLECTOR_RECEIPT_OUTSIDE_CAPTURE")
    # A full collection must finish in the account provider's 30-second freshness budget.
    require(observed-start <= timedelta(seconds=30), "COLLECTOR_CAPTURE_TOO_SLOW")
    positions = []
    for symbol in markets:
        price, at, published = marks[symbol]
        require(timedelta(0) <= observed-at <= timedelta(seconds=30)
                and timedelta(0) <= observed-published <= timedelta(seconds=30),
                "COLLECTOR_TICKER_STALE_OR_FUTURE")
        positions.append(Position(market="spot", symbol=symbol, base_currency=symbol[4:], quote_currency="KRW",
            units=balances[symbol[4:]], price=price, asof=at))
    manifest = content_digest((anchor, coverage, trade_fees, tuple((r.path, r.params, r.account_scope,
        r.received_at, r.server_time, r.sha256) for r in capture.receipts)))
    pages = tuple(EvidencePage(kind=kind, cursor=None, next_cursor=None, start=origin, end=observed,
        rows=tuple(rows), source_sha256=manifest) for kind, rows in (("fills", fills), ("flows", flows), ("orders", orders)))
    account = AccountEvidence(venue="upbit", account_scope=scope, execution_quote="KRW", origin=origin,
        opening_cash=(CashAmount(currency="KRW", amount=anchor.cash_krw),), opening_source_sha256=anchor.source_sha256,
        balances=(CashBalance(currency="KRW", total=balances["KRW"], settled=balances["KRW"]),),
        positions=tuple(positions), fx=(FxRate(currency="KRW", krw=Decimal(1), asof=observed, source_sha256=manifest),),
        pages=pages, restrictions=AccountRestrictions(cash_mode="cash", borrowing_enabled=False, auto_loan=False,
            liabilities=(), asof=observed, source_sha256=coverage.source_sha256),
        observed_at=observed, server_time=capture.receipts[-1].server_time)
    bundle = AccountBundle(accounts=(account,), risk_baseline=baseline)
    build_observation(bundle, now=observed)
    return CollectionResult(bundle=bundle, receipts=tuple(capture.receipts), manifest_sha256=manifest)
