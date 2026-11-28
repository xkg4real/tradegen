"""Continuous equity-path candidates, independently verified before baseline use.

The recorder detects *local* gaps and preserves an exact event sequence. It does
not prove that a venue sent every valuation change. In particular Upbit's book
snapshots, trade IDs, a heartbeat, and our own sequence numbers are not a
gap-free venue sequence. No production coverage verifier is supplied here.

The injected verifier is a separately reviewed trusted adapter, as are the
account source and trusted baseline head. It must authenticate the opening
marks, every mark/fill and their common ordering, the final source watermark,
and the absence of omitted account changes. A digest only binds its conclusion
to this precise candidate and account capture. A payload's ``complete`` flag
or an arbitrary truthy return value is never accepted as that conclusion.

No network, file write, credential, owner state, signing or order operation occurs here.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal, DecimalException, Inexact, ROUND_DOWN, localcontext
from fractions import Fraction
import re
from threading import Lock

from core.compliance import native_accel
from execution_accounts.model import content_digest
from execution_control.risk import Fill, account_fills

_ID = re.compile(r"[A-Za-z0-9_.:/-]{1,128}")
_SHA = re.compile(r"[0-9a-f]{64}")
_SYMBOL = re.compile(r"KRW-[A-Z][A-Z0-9]{0,11}")
_ZERO = Decimal(0)
_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)
_COST_SCALE = 10 ** 18
_COST_QUANTUM = Decimal("1e-18")
MAX_EVENTS = 20000
MAX_SYMBOLS = 64
MAX_HELD_MARKETS = 4
MAX_PRINTS = 12000
MAX_FILLS = 512
MAX_INTERVAL_FILLS = 128
MAX_HISTORY_FILLS = 20000
MAX_SOLVENCY_STATES = 32768
MAX_DURATION = timedelta(seconds=30)
COVERAGE_CONTRACT = "complete-ordered-account-marks-and-fills-v1"


class ContinuousEvidenceError(ValueError):
    """Fixed codes only; never echo source exceptions or private account data."""


def _require(ok, code):
    if not ok:
        raise ContinuousEvidenceError(code)


def _instant(value):
    try:
        _require(type(value) is datetime and value.utcoffset() is not None
                 and 2 <= value.year <= 9998, "CONTINUOUS_AWARE_TIME_REQUIRED")
        return value.astimezone(timezone.utc)
    except Exception:
        raise ContinuousEvidenceError("CONTINUOUS_AWARE_TIME_REQUIRED") from None


def _hash(value):
    _require(type(value) is str and _SHA.fullmatch(value) is not None, "CONTINUOUS_DIGEST_REQUIRED")


def _id(value):
    _require(type(value) is str and _ID.fullmatch(value) is not None, "CONTINUOUS_ID_REQUIRED")


def _number(value, *, positive=False):
    _require(type(value) is Decimal and value.is_finite() and len(value.as_tuple().digits) <= 60
             and -40 <= value.as_tuple().exponent <= 40
             and (value > 0 if positive else value >= 0), "CONTINUOUS_EXACT_NUMBER_REQUIRED")


@dataclass(frozen=True, kw_only=True)
class PriceMark:
    symbol: str
    price: Decimal
    asof: datetime


@dataclass(frozen=True, kw_only=True)
class EquityEvent:
    sequence: int
    at: datetime
    received_at: datetime
    source_sha256: str
    mark: PriceMark | None = None
    fill: Fill | None = None


@dataclass(frozen=True, kw_only=True)
class ContinuousPath:
    account_scope: str
    stream_epoch: str
    previous_state_digest: str
    start: datetime
    end: datetime
    opening_marks: tuple[PriceMark, ...]
    first_sequence: int
    events: tuple[EquityEvent, ...]
    watermark_sequence: int
    watermark_received_at: datetime
    watermark_source_sha256: str


@dataclass(frozen=True, kw_only=True)
class CoverageRequest:
    """Exact challenge to the independently reviewed source verifier."""
    path_sha256: str
    account_capture_sha256: str
    account_scope: str
    stream_epoch: str
    start: datetime
    end: datetime
    first_sequence: int
    watermark_sequence: int


@dataclass(frozen=True, kw_only=True)
class VerifiedCoverage:
    """A verifier's receipt, never an input accepted directly from a user file."""
    request_sha256: str
    contract: str
    authority_sha256: str
    source_proof_sha256: str
    verified_at: datetime


@dataclass(frozen=True, kw_only=True)
class EquityPoint:
    at: datetime
    equity_krw: Decimal
    realized_net_total_krw: Decimal


@dataclass(frozen=True, kw_only=True)
class PathValuation:
    equity_krw: Decimal
    minimum_equity_krw: Decimal
    maximum_equity_krw: Decimal
    realized_net_total_krw: Decimal
    closing_cash_krw: Decimal
    closing_units: tuple[tuple[str, Decimal], ...]
    closing_marks: tuple[PriceMark, ...]
    points: tuple[EquityPoint, ...]


def _mark(value):
    _require(type(value) is PriceMark and type(value.symbol) is str
             and _SYMBOL.fullmatch(value.symbol) is not None, "CONTINUOUS_MARK_INVALID")
    _number(value.price, positive=True)
    _instant(value.asof)


def _event(value, *, scope, sequence, start, previous_at, previous_received, symbols):
    _require(type(value) is EquityEvent and type(value.sequence) is int
             and 0 <= value.sequence < 2**63 and value.sequence == sequence, "CONTINUOUS_SEQUENCE_GAP")
    _instant(value.at); _instant(value.received_at); _hash(value.source_sha256)
    _require(start <= value.at and previous_at <= value.at <= value.received_at
             and previous_received <= value.received_at
             and value.received_at - start <= MAX_DURATION, "CONTINUOUS_TIME_GAP_OR_ROLLBACK")
    _require((value.mark is None) != (value.fill is None), "CONTINUOUS_EVENT_KIND_INVALID")
    if value.mark is not None:
        _mark(value.mark)
        _require(value.mark.symbol in symbols and value.mark.asof == value.at,
                 "CONTINUOUS_MARK_BINDING_INVALID")
    else:
        fill = value.fill
        _require(type(fill) is Fill and fill.venue == "upbit" and fill.account_scope == scope
                 and fill.market == "spot" and fill.symbol in symbols and fill.quote_currency == "KRW"
                 and fill.quote_krw == Decimal(1) and fill.fee_currency == "KRW"
                 and fill.base_currency == fill.symbol[4:] and fill.executed_at == value.at
                 and fill.side in ("buy", "sell") and not fill.order_date and not fill.broker_org_id,
                 "CONTINUOUS_FILL_BINDING_INVALID")
        _id(fill.order_id); _id(fill.fill_id)
        _number(fill.quantity, positive=True); _number(fill.price, positive=True); _number(fill.fee_amount)


def validate_path(path):
    """Structural validation only. Success does not establish source completeness."""
    try:
        _require(type(path) is ContinuousPath, "CONTINUOUS_PATH_REQUIRED")
        _id(path.account_scope); _id(path.stream_epoch); _hash(path.previous_state_digest)
        _instant(path.start); _instant(path.end); _instant(path.watermark_received_at)
        _hash(path.watermark_source_sha256)
        _require(timedelta(0) < path.end-path.start <= MAX_DURATION
                 and path.end <= path.watermark_received_at
                 and path.watermark_received_at-path.start <= MAX_DURATION,
                 "CONTINUOUS_TIME_GAP_OR_ROLLBACK")
        _require(type(path.first_sequence) is int and 0 <= path.first_sequence < 2**63
                 and type(path.watermark_sequence) is int
                 and type(path.events) is tuple and len(path.events) <= MAX_EVENTS
                 and path.watermark_sequence == path.first_sequence + len(path.events)
                 and path.watermark_sequence < 2**63, "CONTINUOUS_SEQUENCE_GAP")
        _require(type(path.opening_marks) is tuple and 0 < len(path.opening_marks) <= MAX_SYMBOLS,
                 "CONTINUOUS_OPENING_MARKS_REQUIRED")
        symbols = []
        for mark in path.opening_marks:
            _mark(mark)
            _require(timedelta(0) <= path.start-mark.asof <= MAX_DURATION,
                     "CONTINUOUS_OPENING_MARK_STALE_OR_FUTURE")
            symbols.append(mark.symbol)
        _require(tuple(symbols) == tuple(sorted(set(symbols))), "CONTINUOUS_MARK_SCOPE_INVALID")
        at, received = path.start, path.start
        for offset, event in enumerate(path.events):
            _event(event, scope=path.account_scope, sequence=path.first_sequence+offset, start=path.start,
                   previous_at=at, previous_received=received, symbols=symbols)
            _require(event.at < path.end and event.received_at <= path.watermark_received_at,
                     "CONTINUOUS_HALF_OPEN_BOUNDARY_REQUIRED")
            at, received = event.at, event.received_at
        return path
    except ContinuousEvidenceError:
        raise
    except (ValueError, TypeError, AttributeError, DecimalException, OverflowError):
        raise ContinuousEvidenceError("CONTINUOUS_PATH_INVALID") from None


class ContinuousPriceRecorder:
    """A bounded one-interval recorder. Any gap/disconnect poisons this epoch.

    There is deliberately no resume/backfill/reset method. Restarting collection
    requires a new reviewed opening anchor. ``seal`` returns an untrusted
    candidate, not a permission to advance the account baseline or place orders.
    Local contiguous sequence values are checked but never claimed as venue proof.
    """
    def __init__(self, *, account_scope, stream_epoch, previous_state_digest, start,
                 opening_marks, first_sequence):
        _id(account_scope); _id(stream_epoch); _hash(previous_state_digest); _instant(start)
        _require(type(first_sequence) is int and 0 <= first_sequence < 2**63, "CONTINUOUS_SEQUENCE_GAP")
        _require(type(opening_marks) is tuple and 0 < len(opening_marks) <= MAX_SYMBOLS,
                 "CONTINUOUS_OPENING_MARKS_REQUIRED")
        symbols = []
        for mark in opening_marks:
            _mark(mark)
            _require(timedelta(0) <= start-mark.asof <= MAX_DURATION,
                     "CONTINUOUS_OPENING_MARK_STALE_OR_FUTURE")
            symbols.append(mark.symbol)
        _require(tuple(symbols) == tuple(sorted(set(symbols))), "CONTINUOUS_MARK_SCOPE_INVALID")
        self._args = dict(account_scope=account_scope, stream_epoch=stream_epoch,
                          previous_state_digest=previous_state_digest, start=start,
                          opening_marks=opening_marks, first_sequence=first_sequence)
        self._symbols, self._events, self._broken, self._sealed = tuple(symbols), [], False, False
        self._lock = Lock()

    def disconnect(self):
        with self._lock:
            self._broken = True

    def append(self, event):
        with self._lock:
            _require(not self._broken, "CONTINUOUS_EPOCH_BROKEN")
            _require(not self._sealed, "CONTINUOUS_EPOCH_SEALED")
            try:
                # Exact last-event redelivery is idempotent; old or changed rows refuse.
                if self._events and event == self._events[-1]:
                    return
                _require(len(self._events) < MAX_EVENTS, "CONTINUOUS_EVENT_LIMIT")
                last = self._events[-1] if self._events else None
                _event(event, scope=self._args["account_scope"],
                       sequence=self._args["first_sequence"]+len(self._events), start=self._args["start"],
                       previous_at=last.at if last else self._args["start"],
                       previous_received=last.received_at if last else self._args["start"], symbols=self._symbols)
                self._events.append(event)
            except Exception:
                self._broken = True
                raise ContinuousEvidenceError("CONTINUOUS_EVENT_REFUSED") from None

    def seal(self, *, end, watermark_sequence, watermark_received_at, watermark_source_sha256):
        with self._lock:
            _require(not self._broken, "CONTINUOUS_EPOCH_BROKEN")
            _require(not self._sealed, "CONTINUOUS_EPOCH_SEALED")
            try:
                candidate = validate_path(ContinuousPath(**self._args, end=end, events=tuple(self._events),
                    watermark_sequence=watermark_sequence, watermark_received_at=watermark_received_at,
                    watermark_source_sha256=watermark_source_sha256))
            except Exception:
                self._broken = True
                raise ContinuousEvidenceError("CONTINUOUS_WATERMARK_REFUSED") from None
            self._sealed = True
            return candidate


def verify_coverage(path, *, account_capture_sha256, verifier, now):
    """Invoke a reviewed source verifier; no default verifier or affirmative fallback."""
    path = validate_path(path)
    _hash(account_capture_sha256); _instant(now)
    _require(callable(verifier), "CONTINUOUS_COVERAGE_VERIFIER_REQUIRED")
    coverage_request = CoverageRequest(path_sha256=content_digest(path), account_capture_sha256=account_capture_sha256,
        account_scope=path.account_scope, stream_epoch=path.stream_epoch, start=path.start, end=path.end,
        first_sequence=path.first_sequence, watermark_sequence=path.watermark_sequence)
    try:
        receipt = verifier(coverage_request, path)
    except Exception:
        raise ContinuousEvidenceError("CONTINUOUS_COVERAGE_VERIFICATION_FAILED") from None
    _require(type(receipt) is VerifiedCoverage, "CONTINUOUS_VERIFIED_COVERAGE_REQUIRED")
    _hash(receipt.authority_sha256); _hash(receipt.source_proof_sha256); _instant(receipt.verified_at)
    _require(receipt.request_sha256 == content_digest(coverage_request) and receipt.contract == COVERAGE_CONTRACT,
             "CONTINUOUS_COVERAGE_BINDING_MISMATCH")
    _require(path.watermark_received_at <= receipt.verified_at <= now
             and now-path.end <= MAX_DURATION, "CONTINUOUS_COVERAGE_STALE_OR_FUTURE")
    return receipt


def _ms_of(instant_utc: datetime) -> int:
    return (instant_utc - _EPOCH) // timedelta(milliseconds=1)


def _alloc_lot_cost(cost: Decimal, taken: Decimal, quantity: Decimal) -> Decimal:
    if taken == quantity:
        return cost
    with localcontext() as sub:
        sub.prec = 512
        sub.traps[Inexact] = False
        allocated = (cost * taken / quantity).quantize(_COST_QUANTUM, rounding=ROUND_DOWN)
    _require(allocated.is_finite() and _ZERO <= allocated <= cost, "CONTINUOUS_FIFO_HISTORY_REFUSED")
    return allocated


def _opening_fifo_lots(accepted_fills: tuple[Fill, ...], market_index: Mapping[str, int]) -> tuple[tuple[int, Decimal, Decimal], ...]:
    by_symbol: dict[str, list[list[Decimal]]] = {}
    for fill in accepted_fills:
        rows = by_symbol.setdefault(fill.symbol, [])
        notional = fill.quantity * fill.price
        if fill.side == "buy":
            rows.append([fill.quantity, notional + fill.fee_amount])
            continue
        needed = fill.quantity
        while needed > _ZERO:
            _require(bool(rows), "CONTINUOUS_FIFO_HISTORY_REFUSED")
            qty, basis = rows[0]
            taken = min(needed, qty)
            alloc = _alloc_lot_cost(basis, taken, qty)
            needed -= taken
            if taken == qty:
                rows.pop(0)
            else:
                rows[0] = [qty - taken, basis - alloc]
    out: list[tuple[int, Decimal, Decimal]] = []
    for symbol in sorted(by_symbol):
        rows = by_symbol[symbol]
        if not rows:
            continue
        _require(symbol in market_index, "CONTINUOUS_MARK_COVERAGE_INCOMPLETE")
        m_idx = market_index[symbol]
        for qty, basis in rows:
            out.append((m_idx, qty, basis))
    return tuple(out)


def _concurrent_fill_extrema(group, cash, units, min_marks, max_marks):
    """Reachable KRW equity bounds when independent markets share a fill timestamp.

    Preserve FIFO order within each market. For each per-market prefix record
    its cash/units change. If the least cash combination stays nonnegative all
    interleavings are solvent and the extremal sums factor across markets.
    Otherwise retain only feasible prefixes on a full path to the final state.
    """
    prefixes = {}
    for _, _, kind, market, qty, price, fee in group:
        rows = prefixes.setdefault(market, [(_ZERO, _ZERO)])
        spent, held = rows[-1]
        delta = qty if kind == native_accel.TG_EVENT_BUY else -qty
        rows.append((spent - delta * price - fee, held + delta))
        _require(units[market] + rows[-1][1] >= 0, "CONTINUOUS_NEGATIVE_CASH_OR_INVENTORY")
    markets = tuple(prefixes)
    low = cash + sum(u * p for u, p in zip(units, min_marks))
    high = cash + sum(u * p for u, p in zip(units, max_marks))
    if cash + sum(min(c for c, _ in rows) for rows in prefixes.values()) >= 0:
        return (low + sum(min(c + u * min_marks[m] for c, u in prefixes[m]) for m in markets),
                high + sum(max(c + u * max_marks[m] for c, u in prefixes[m]) for m in markets))

    final = tuple(len(prefixes[m]) - 1 for m in markets)
    size = 1
    for count in final:
        size *= count + 1
    _require(size <= MAX_SOLVENCY_STATES, "CONTINUOUS_UNORDERED_FILL_STATE_LIMIT")
    start = tuple(0 for _ in markets)
    reachable = {start}
    frontier = {start}
    for _ in group:
        successors = set()
        for state in frontier:
            for i, count in enumerate(state):
                if count == final[i]:
                    continue
                nxt = state[:i] + (count + 1,) + state[i+1:]
                if cash + sum(prefixes[m][v][0] for m, v in zip(markets, nxt)) >= 0:
                    successors.add(nxt)
        reachable.update(successors)
        frontier = successors
    _require(final in reachable, "CONTINUOUS_NEGATIVE_CASH_OR_INVENTORY")
    minimum, maximum = low, high
    frontier = {final}
    for _ in range(len(group) + 1):
        predecessors = set()
        for state in frontier:
            lo, hi = low, high
            for i, m in enumerate(markets):
                c, u = prefixes[m][state[i]]
                lo += c + u * min_marks[m]
                hi += c + u * max_marks[m]
                if state[i]:
                    parent = state[:i] + (state[i] - 1,) + state[i+1:]
                    if parent in reachable:
                        predecessors.add(parent)
            minimum, maximum = min(minimum, lo), max(maximum, hi)
        frontier = predecessors
    return minimum, maximum


def _fold_interval_core(
    *,
    markets: tuple[str, ...],
    opening_marks_by_market: Mapping[str, PriceMark],
    opening_cash_krw: Decimal,
    opening_units_by_market: Mapping[str, Decimal],
    opening_realized_krw: Decimal,
    opening_lots: tuple[tuple[int, Decimal, Decimal], ...],
    ordered_events: tuple[tuple[int, datetime, int, int, Decimal, Decimal, Decimal], ...],
    start: datetime,
    end: datetime,
    previous_equity_krw: Decimal,
    conservative_ms: bool,
    unordered_marks_or_fills: bool = False,
    confirmed_closes=None,
    undisclosed_closing: frozenset[str] = frozenset(),
):
    num_markets = len(markets)
    opening_units_vec = tuple(opening_units_by_market.get(sym, _ZERO) for sym in markets)
    opening_marks_vec = tuple(opening_marks_by_market[sym].price for sym in markets)
    initial_eq = opening_cash_krw + sum(
        (opening_units_vec[i] * opening_marks_vec[i] for i in range(num_markets)),
        _ZERO,
    )
    _number(initial_eq, positive=True)
    _require(initial_eq == previous_equity_krw, "CONTINUOUS_OPENING_EQUITY_MISMATCH")

    # ABI v1 collapses a tied close to one price and only visits one global
    # fill ordering. Use the exact Decimal envelopes for unordered evidence.
    if 1 <= num_markets <= MAX_HELD_MARKETS and not unordered_marks_or_fills:
        native_events = tuple(
            (at_ms, kind, m_idx, eqty, eprice, efee)
            for at_ms, _at, kind, m_idx, eqty, eprice, efee in ordered_events
        )
        fast = native_accel.fold_continuous_interval(
            num_markets=num_markets,
            opening_cash_krw=opening_cash_krw,
            opening_units=opening_units_vec,
            opening_marks=opening_marks_vec,
            opening_realized_krw=opening_realized_krw,
            opening_lots=opening_lots,
            events=native_events,
            conservative_ms=conservative_ms,
            need_points=True,
        )
        if fast is not None:
            status = fast["status"]
            if status == native_accel.TG_ERR_NEGATIVE_STATE:
                raise ContinuousEvidenceError("CONTINUOUS_NEGATIVE_CASH_OR_INVENTORY")
            _require(status == native_accel.TG_OK, "CONTINUOUS_VALUATION_REFUSED")
            closing_eq = fast["closing_equity_krw"]
            min_eq = fast["min_equity_krw"]
            max_eq = fast["max_equity_krw"]
            _number(closing_eq, positive=True)
            _number(min_eq, positive=True)
            _number(max_eq, positive=True)
            raw_pts = fast["points"]
            pts = [EquityPoint(at=start, equity_krw=raw_pts[0][0], realized_net_total_krw=raw_pts[0][1])]
            for idx, (_at_ms, ev_at, _kind, _m_idx, _eqty, _eprice, _efee) in enumerate(ordered_events):
                pts.append(EquityPoint(at=ev_at, equity_krw=raw_pts[idx + 1][0], realized_net_total_krw=raw_pts[idx + 1][1]))
            pts.append(EquityPoint(at=end, equity_krw=raw_pts[-1][0], realized_net_total_krw=raw_pts[-1][1]))
            closing_units = tuple(
                (markets[i], fast["closing_units"][i])
                for i in range(num_markets)
                if fast["closing_units"][i] != _ZERO
            )
            last_mark_at = {sym: opening_marks_by_market[sym].asof for sym in markets}
            for _at_ms, ev_at, kind, m_idx, _eqty, _eprice, _efee in ordered_events:
                if kind == native_accel.TG_EVENT_MARK:
                    last_mark_at[markets[m_idx]] = ev_at
            closing_marks = tuple(
                PriceMark(symbol=markets[i], price=fast["closing_marks"][i], asof=last_mark_at[markets[i]])
                for i in range(num_markets)
            )
            return PathValuation(
                equity_krw=closing_eq,
                minimum_equity_krw=min_eq,
                maximum_equity_krw=max_eq,
                realized_net_total_krw=fast["realized_net_krw"],
                closing_cash_krw=fast["closing_cash_krw"],
                closing_units=closing_units,
                closing_marks=closing_marks,
                points=tuple(pts),
            )

    cash = opening_cash_krw
    realized = opening_realized_krw
    units = [opening_units_by_market.get(sym, _ZERO) for sym in markets]
    marks = [opening_marks_by_market[sym] for sym in markets]
    lots: list[list[list[Decimal]]] = [[] for _ in range(num_markets)]
    for m_idx, lq, lc in opening_lots:
        lots[m_idx].append([lq, lc])

    def calc_eq(mark_prices: Sequence[Decimal]) -> Decimal:
        total = cash + sum((units[i] * mark_prices[i] for i in range(num_markets)), _ZERO)
        _number(total, positive=True)
        return total

    def apply_fill_py(kind: int, m_idx: int, qty: Decimal, price: Decimal, fee: Decimal) -> None:
        nonlocal cash, realized
        notional = qty * price
        if kind == native_accel.TG_EVENT_BUY:
            outlay = notional + fee
            next_cash = cash - outlay
            _require(next_cash >= _ZERO, "CONTINUOUS_NEGATIVE_CASH_OR_INVENTORY")
            cash = next_cash
            units[m_idx] += qty
            lots[m_idx].append([qty, outlay])
            return
        _require(units[m_idx] >= qty, "CONTINUOUS_NEGATIVE_CASH_OR_INVENTORY")
        movement = notional - fee
        next_cash = cash + movement
        _require(next_cash >= _ZERO, "CONTINUOUS_NEGATIVE_CASH_OR_INVENTORY")
        needed = qty
        released = _ZERO
        cur_lots = lots[m_idx]
        while needed > _ZERO:
            _require(bool(cur_lots), "CONTINUOUS_NEGATIVE_CASH_OR_INVENTORY")
            lot_q, lot_c = cur_lots[0]
            taken = min(needed, lot_q)
            alloc = _alloc_lot_cost(lot_c, taken, lot_q)
            released += alloc
            needed -= taken
            if taken == lot_q:
                cur_lots.pop(0)
            else:
                cur_lots[0] = [lot_q - taken, lot_c - alloc]
        cash = next_cash
        units[m_idx] -= qty
        realized += movement - released

    current = initial_eq
    low = high = current
    points = [EquityPoint(at=start, equity_krw=current, realized_net_total_krw=realized)]

    if not conservative_ms:
        for _at_ms, ev_at, kind, m_idx, eqty, eprice, efee in ordered_events:
            if kind == native_accel.TG_EVENT_MARK:
                marks[m_idx] = PriceMark(symbol=markets[m_idx], price=eprice, asof=ev_at)
            else:
                apply_fill_py(kind, m_idx, eqty, eprice, efee)
            current = calc_eq([m.price for m in marks])
            low, high = min(low, current), max(high, current)
            points.append(EquityPoint(at=ev_at, equity_krw=current, realized_net_total_krw=realized))
    else:
        idx = 0
        n_ev = len(ordered_events)
        carried_min = list(opening_marks_vec)
        carried_max = list(opening_marks_vec)
        while idx < n_ev:
            ms = ordered_events[idx][0]
            end_idx = idx
            while end_idx < n_ev and ordered_events[end_idx][0] == ms:
                end_idx += 1
            min_prices = carried_min.copy()
            max_prices = carried_max.copy()
            traded = {}
            last_marks = list(marks)
            for k in range(idx, end_idx):
                _ms_k, ev_at, kind, m_idx, _eqty, eprice, _efee = ordered_events[k]
                if kind == native_accel.TG_EVENT_MARK:
                    if eprice < min_prices[m_idx]:
                        min_prices[m_idx] = eprice
                    if eprice > max_prices[m_idx]:
                        max_prices[m_idx] = eprice
                    lo, hi = traded.get(m_idx, (eprice, eprice))
                    traded[m_idx] = (min(lo, eprice), max(hi, eprice))
                    last_marks[m_idx] = PriceMark(symbol=markets[m_idx], price=eprice, asof=ev_at)
            lo_eq = calc_eq(min_prices)
            hi_eq = calc_eq(max_prices)
            low, high = min(low, lo_eq), max(high, hi_eq)
            next_fill_group = idx
            for k in range(idx, end_idx):
                _ms_k, ev_at, kind, m_idx, eqty, eprice, efee = ordered_events[k]
                if kind == native_accel.TG_EVENT_MARK:
                    marks[m_idx] = PriceMark(symbol=markets[m_idx], price=eprice, asof=ev_at)
                else:
                    if k >= next_fill_group:
                        next_fill_group = k + 1
                        while next_fill_group < end_idx and ordered_events[next_fill_group][1] == ev_at:
                            next_fill_group += 1
                        group = ordered_events[k:next_fill_group]
                        if len({e[3] for e in group}) > 1:
                            group_low, group_high = _concurrent_fill_extrema(
                                group, cash, units, min_prices, max_prices)
                            low, high = min(low, group_low), max(high, group_high)
                    apply_fill_py(kind, m_idx, eqty, eprice, efee)
                    lo_eq = calc_eq(min_prices)
                    hi_eq = calc_eq(max_prices)
                    low, high = min(low, lo_eq), max(high, hi_eq)
                current = calc_eq([m.price for m in marks])
                points.append(EquityPoint(at=ev_at, equity_krw=current, realized_net_total_krw=realized))
            marks = last_marks
            for market, (lo, hi) in traded.items():
                proof = confirmed_closes.get(market) if confirmed_closes else None
                if proof is not None and proof[0] == ms:
                    lo = hi = proof[1]
                carried_min[market], carried_max[market] = lo, hi
            current = calc_eq([m.price for m in marks])
            low, high = min(low, current), max(high, current)
            idx = end_idx

    closing_units = tuple((markets[i], units[i]) for i in range(num_markets) if units[i] != _ZERO)
    return PathValuation(
        equity_krw=current,
        minimum_equity_krw=low,
        maximum_equity_krw=high,
        realized_net_total_krw=realized,
        closing_cash_krw=cash,
        closing_units=closing_units,
        closing_marks=tuple(mark for mark in marks if mark.symbol not in undisclosed_closing),
        points=tuple(points) + (EquityPoint(at=end, equity_krw=current, realized_net_total_krw=realized),),
    )


def value_path(path, *, opening_cash_krw, opening_units, historical_fills, interval_fills,
               previous_equity_krw, previous_realized_net_krw):
    """Derive exact event-path extrema; source authentication is a separate obligation.

    ``historical_fills`` covers origin up to but excluding start; ``interval_fills``
    is the reconciled account capture's complete [start,end) history. Their order
    at equal timestamps must match the authenticated common event ordering.
    """
    try:
        with localcontext() as numeric:
            numeric.prec = 512
            numeric.traps[Inexact] = True
            path = validate_path(path)
            _number(opening_cash_krw); _number(previous_equity_krw, positive=True)
            _require(type(previous_realized_net_krw) is Decimal and previous_realized_net_krw.is_finite(),
                     "CONTINUOUS_EXACT_NUMBER_REQUIRED")
            _require(type(opening_units) is tuple and type(historical_fills) is tuple
                     and type(interval_fills) is tuple, "CONTINUOUS_ACCOUNT_HISTORY_REQUIRED")
            _require(len(historical_fills) <= MAX_HISTORY_FILLS and len(interval_fills) <= MAX_INTERVAL_FILLS,
                     "CONTINUOUS_FILL_BOUND_EXCEEDED")
            units = {}
            for symbol, amount in opening_units:
                _require(symbol not in units and type(symbol) is str and _SYMBOL.fullmatch(symbol) is not None,
                         "CONTINUOUS_HOLDING_INVALID")
                _number(amount, positive=True)
                units[symbol] = amount
            marks = {mark.symbol: mark for mark in path.opening_marks}
            _require(set(units) <= set(marks), "CONTINUOUS_MARK_COVERAGE_INCOMPLETE")
            _require(all(type(f) is Fill and f.executed_at < path.start for f in historical_fills)
                     and all(type(f) is Fill and path.start <= f.executed_at < path.end for f in interval_fills),
                     "CONTINUOUS_FILL_CUTOFF_MISMATCH")
            _require(all(f.venue == "upbit" and f.account_scope == path.account_scope and f.market == "spot"
                         and f.quote_currency == "KRW" and f.quote_krw == Decimal(1)
                         and f.fee_currency == "KRW" for f in historical_fills+interval_fills),
                     "CONTINUOUS_FILL_BINDING_INVALID")
            observed_fills = tuple(event.fill for event in path.events if event.fill is not None)
            _require(observed_fills == interval_fills, "CONTINUOUS_FILL_COVERAGE_MISMATCH")
            before, after = account_fills(historical_fills), account_fills(historical_fills+interval_fills)
            _require(before.ok and after.ok and before.duplicate_count == 0 and after.duplicate_count == 0,
                     "CONTINUOUS_FIFO_HISTORY_REFUSED")
            _require(before.realized_net_profit_krw == previous_realized_net_krw,
                     "CONTINUOUS_OPENING_PROFIT_MISMATCH")
            expected_units = {row[3]: row[4] for row in before.inventory if row[4] != 0}
            _require(units == expected_units, "CONTINUOUS_OPENING_INVENTORY_MISMATCH")
            markets = tuple(sorted(marks))
            market_index = {sym: idx for idx, sym in enumerate(markets)}
            for fill in interval_fills:
                _require(fill.symbol in market_index, "CONTINUOUS_MARK_COVERAGE_INCOMPLETE")
            opening_lots = _opening_fifo_lots(before.accepted_fills, market_index)
            ordered_events = []
            for event in path.events:
                at_utc = event.at.astimezone(timezone.utc)
                at_ms = _ms_of(at_utc)
                if event.mark is not None:
                    ordered_events.append((
                        at_ms, event.at, native_accel.TG_EVENT_MARK, market_index[event.mark.symbol],
                        _ZERO, event.mark.price, _ZERO,
                    ))
                else:
                    fill = event.fill
                    kind = native_accel.TG_EVENT_BUY if fill.side == "buy" else native_accel.TG_EVENT_SELL
                    ordered_events.append((
                        at_ms, event.at, kind, market_index[fill.symbol],
                        fill.quantity, fill.price, fill.fee_amount,
                    ))
            valuation = _fold_interval_core(
                markets=markets,
                opening_marks_by_market=marks,
                opening_cash_krw=opening_cash_krw,
                opening_units_by_market=units,
                opening_realized_krw=before.realized_net_profit_krw,
                opening_lots=opening_lots,
                ordered_events=tuple(ordered_events),
                start=path.start,
                end=path.end,
                previous_equity_krw=previous_equity_krw,
                conservative_ms=False,
            )
            _require(dict(valuation.closing_units) == {row[3]: row[4] for row in after.inventory if row[4] != 0},
                     "CONTINUOUS_CLOSING_INVENTORY_MISMATCH")
            _require(valuation.realized_net_total_krw == after.realized_net_profit_krw,
                     "CONTINUOUS_FIFO_HISTORY_REFUSED")
            return valuation
    except ContinuousEvidenceError:
        raise
    except (ValueError, TypeError, AttributeError, KeyError, DecimalException, OverflowError):
        raise ContinuousEvidenceError("CONTINUOUS_VALUATION_REFUSED") from None


def value_trade_paths(
    trade_path: Mapping[str, object],
    *,
    opening_marks: Sequence[PriceMark] | Mapping[str, PriceMark | Decimal],
    opening_cash_krw: Decimal,
    opening_units: tuple[tuple[str, Decimal], ...],
    historical_fills: tuple[Fill, ...] = (),
    interval_fills: tuple[Fill, ...] = (),
    previous_equity_krw: Decimal,
    previous_realized_net_krw: Decimal,
    start: datetime,
    end: datetime,
    account_scope: str,
    conservative_ms: bool = True,
    closing_marks: Mapping[str, PriceMark] | None = None,
) -> PathValuation:
    """Multi-coin Approach A interval valuation (`<= 4` markets, `<= 12000` prints, `<= 512` fills).

    Deterministic merge-join across up to 4 held/traded KRW markets with exact `1e-18` `ROUND_DOWN`
    plus final residual FIFO lot cost release and conservative intra-millisecond `[min_eq, max_eq]`
    envelope for unordered public prints. Across instruments, fills with the same execution instant can
    interleave subject to cash solvency. Within an instrument the caller supplies reconciled FIFO order.
    A held coin's last millisecond with conflicting prices needs an independent closing PriceMark.
    Returned points give one ordering for inspection; the min/max include all supported orderings.
    """
    try:
        with localcontext() as numeric:
            numeric.prec = 512
            numeric.traps[Inexact] = True
            _id(account_scope)
            start_utc = _instant(start)
            end_utc = _instant(end)
            _require(start_utc < end_utc, "CONTINUOUS_TIME_GAP_OR_ROLLBACK")
            _number(opening_cash_krw)
            _number(previous_equity_krw, positive=True)
            _require(type(previous_realized_net_krw) is Decimal and previous_realized_net_krw.is_finite(),
                     "CONTINUOUS_EXACT_NUMBER_REQUIRED")
            _require(isinstance(trade_path, Mapping) and len(trade_path) <= MAX_HELD_MARKETS,
                     "CONTINUOUS_MARK_SCOPE_INVALID")
            _require(type(opening_units) is tuple and type(historical_fills) is tuple
                     and type(interval_fills) is tuple, "CONTINUOUS_ACCOUNT_HISTORY_REQUIRED")
            _require(len(historical_fills) <= MAX_HISTORY_FILLS and len(interval_fills) <= MAX_FILLS,
                     "CONTINUOUS_FILL_BOUND_EXCEEDED")

            units: dict[str, Decimal] = {}
            for symbol, amount in opening_units:
                _require(symbol not in units and type(symbol) is str and _SYMBOL.fullmatch(symbol) is not None,
                         "CONTINUOUS_HOLDING_INVALID")
                _number(amount, positive=True)
                units[symbol] = amount

            marks_map: dict[str, PriceMark] = {}
            if isinstance(opening_marks, Mapping):
                for symbol, val in opening_marks.items():
                    _require(type(symbol) is str and _SYMBOL.fullmatch(symbol) is not None, "CONTINUOUS_MARK_INVALID")
                    if type(val) is PriceMark:
                        _mark(val)
                        _require(val.symbol == symbol, "CONTINUOUS_MARK_INVALID")
                        marks_map[symbol] = val
                    else:
                        _number(val, positive=True)
                        marks_map[symbol] = PriceMark(symbol=symbol, price=val, asof=start)
            else:
                _require(isinstance(opening_marks, Sequence), "CONTINUOUS_OPENING_MARKS_REQUIRED")
                for val in opening_marks:
                    _mark(val)
                    _require(val.symbol not in marks_map, "CONTINUOUS_MARK_SCOPE_INVALID")
                    marks_map[val.symbol] = val

            _require(all(type(f) is Fill and f.executed_at < start for f in historical_fills)
                     and all(type(f) is Fill and start <= f.executed_at < end for f in interval_fills),
                     "CONTINUOUS_FILL_CUTOFF_MISMATCH")
            _require(all(f.venue == "upbit" and f.account_scope == account_scope and f.market == "spot"
                         and _SYMBOL.fullmatch(f.symbol) is not None and f.quote_currency == "KRW"
                         and f.quote_krw == Decimal(1) and f.fee_currency == "KRW"
                         and f.base_currency == f.symbol[4:] and f.side in ("buy", "sell")
                         and not f.order_date and not f.broker_org_id
                         for f in historical_fills + interval_fills),
                     "CONTINUOUS_FILL_BINDING_INVALID")
            for fill in interval_fills:
                _id(fill.order_id); _id(fill.fill_id)
                _number(fill.quantity, positive=True); _number(fill.price, positive=True); _number(fill.fee_amount)

            before = account_fills(historical_fills)
            after = account_fills(historical_fills + interval_fills)
            _require(before.ok and after.ok and before.duplicate_count == 0 and after.duplicate_count == 0,
                     "CONTINUOUS_FIFO_HISTORY_REFUSED")
            _require(before.realized_net_profit_krw == previous_realized_net_krw,
                     "CONTINUOUS_OPENING_PROFIT_MISMATCH")
            expected_units = {row[3]: row[4] for row in before.inventory if row[4] != 0}
            _require(units == expected_units, "CONTINUOUS_OPENING_INVENTORY_MISMATCH")

            active_symbols = set(units) | {f.symbol for f in interval_fills} | set(trade_path.keys())
            for symbol in active_symbols:
                _require(type(symbol) is str and _SYMBOL.fullmatch(symbol) is not None,
                         "CONTINUOUS_MARK_SCOPE_INVALID")
            _require(len(active_symbols) <= MAX_HELD_MARKETS, "CONTINUOUS_MARK_SCOPE_INVALID")

            if not active_symbols:
                _require(opening_cash_krw == previous_equity_krw and opening_cash_krw > _ZERO,
                         "CONTINUOUS_OPENING_EQUITY_MISMATCH")
                pt0 = EquityPoint(at=start, equity_krw=opening_cash_krw, realized_net_total_krw=previous_realized_net_krw)
                pt1 = EquityPoint(at=end, equity_krw=opening_cash_krw, realized_net_total_krw=previous_realized_net_krw)
                return PathValuation(
                    equity_krw=opening_cash_krw,
                    minimum_equity_krw=opening_cash_krw,
                    maximum_equity_krw=opening_cash_krw,
                    realized_net_total_krw=previous_realized_net_krw,
                    closing_cash_krw=opening_cash_krw,
                    closing_units=(),
                    closing_marks=(),
                    points=(pt0, pt1),
                )

            _require(active_symbols <= set(trade_path), "CONTINUOUS_TRADE_WINDOW_MISSING")
            markets = tuple(sorted(active_symbols))
            market_index = {sym: idx for idx, sym in enumerate(markets)}

            # Populate opening marks from trade_path opening_print when available if not already given
            for sym in markets:
                win = trade_path.get(sym)
                opening_print = getattr(win, "opening_print", None)
                if sym not in marks_map and opening_print is not None:
                    p_price = opening_print.price
                    p_at = opening_print.at
                    _number(p_price, positive=True)
                    _instant(p_at)
                    _require(getattr(opening_print, "market", sym) == sym and p_at < start,
                             "CONTINUOUS_OPENING_PRINT_MISMATCH")
                    marks_map[sym] = PriceMark(symbol=sym, price=p_price, asof=p_at)
            _require(all(mark.asof <= start for mark in marks_map.values()), "CONTINUOUS_OPENING_MARK_FUTURE")
            _require(set(markets) <= set(marks_map), "CONTINUOUS_MARK_COVERAGE_INCOMPLETE")

            # Merge-join trade prints across <= 4 markets and interval fills deterministically
            merged_rows: list[tuple[int, int, int, int, datetime, int, Decimal, Decimal, Decimal]] = []
            total_prints = 0
            group_prices = {}
            last_trade_ms = {}
            for sym in markets:
                m_idx = market_index[sym]
                raw_source = trade_path.get(sym, ())
                raw_prints = getattr(raw_source, "prints", raw_source)
                _require(isinstance(raw_prints, Sequence) and not isinstance(raw_prints, (str, bytes)),
                         "CONTINUOUS_PATH_INVALID")
                for idx_p, item in enumerate(raw_prints):
                    total_prints += 1
                    _require(total_prints <= MAX_PRINTS, "CONTINUOUS_EVENT_LIMIT")
                    if type(item) is PriceMark:
                        _mark(item)
                        _require(item.symbol == sym, "CONTINUOUS_MARK_BINDING_INVALID")
                        p_at = item.asof
                        p_ms = _ms_of(p_at.astimezone(timezone.utc))
                        p_seq = idx_p
                        p_price = item.price
                    elif hasattr(item, "price") and hasattr(item, "at"):
                        m_sym = getattr(item, "market", sym)
                        _require(m_sym == sym, "CONTINUOUS_MARK_BINDING_INVALID")
                        p_at = item.at
                        _instant(p_at)
                        p_price = item.price
                        _number(p_price, positive=True)
                        p_ms = _ms_of(p_at.astimezone(timezone.utc))
                        supplied_ms = getattr(item, "timestamp_ms", p_ms)
                        p_seq = getattr(item, "sequential_id", idx_p)
                        _require(type(supplied_ms) is int and supplied_ms == p_ms and type(p_seq) is int,
                                 "CONTINUOUS_MARK_TIME_MISMATCH")
                    elif isinstance(item, tuple) and len(item) == 2:
                        p_at, p_price = item
                        _instant(p_at)
                        _number(p_price, positive=True)
                        p_ms = _ms_of(p_at.astimezone(timezone.utc))
                        p_seq = idx_p
                    else:
                        raise ContinuousEvidenceError("CONTINUOUS_MARK_INVALID")
                    _require(start <= p_at < end, "CONTINUOUS_HALF_OPEN_BOUNDARY_REQUIRED")
                    group_prices.setdefault((sym, p_ms), set()).add(p_price)
                    last_trade_ms[sym] = max(last_trade_ms.get(sym, p_ms), p_ms)
                    merged_rows.append((
                        p_ms, 0, m_idx, p_seq, p_at, native_accel.TG_EVENT_MARK, _ZERO, p_price, _ZERO,
                    ))

            for idx_f, fill in enumerate(interval_fills):
                f_ms = _ms_of(fill.executed_at.astimezone(timezone.utc))
                m_idx = market_index[fill.symbol]
                kind = native_accel.TG_EVENT_BUY if fill.side == "buy" else native_accel.TG_EVENT_SELL
                merged_rows.append((
                    f_ms, 1, m_idx, idx_f, fill.executed_at, kind, fill.quantity, fill.price, fill.fee_amount,
                ))

            _require(closing_marks is None or isinstance(closing_marks, Mapping), "CONTINUOUS_CLOSING_MARK_INVALID")
            observed_closes = {} if closing_marks is None else closing_marks
            closing_inventory = {row[3] for row in after.inventory if row[4] != 0}
            confirmed = {}
            undisclosed = set()
            for sym, ms in last_trade_ms.items():
                prices = group_prices[(sym, ms)]
                if len(prices) == 1:
                    continue
                hint = observed_closes.get(sym)
                if hint is None:
                    _require(sym not in closing_inventory, "CONTINUOUS_CLOSING_MARK_AMBIGUOUS")
                    undisclosed.add(sym)
                    continue
                _mark(hint)
                _require(hint.symbol == sym and _ms_of(hint.asof) == ms and hint.price in prices and hint.asof < end,
                         "CONTINUOUS_CLOSING_MARK_MISMATCH")
                confirmed[market_index[sym]] = (ms, hint.price)

            def event_order(row):
                ms, is_fill, market, index, at, _, _, price, _ = row
                if is_fill:
                    # Equal-source instants retain the supplied reconciled fill sequence (FIFO).
                    return ms, is_fill, at, index
                return ms, is_fill, market, confirmed.get(market) == (ms, price), index

            merged_rows.sort(key=event_order)
            fill_markets = {}
            for fill in interval_fills:
                fill_markets.setdefault(fill.executed_at, set()).add(fill.symbol)
            ambiguous = (any(len(prices) > 1 for prices in group_prices.values())
                         or any(len(coins) > 1 for coins in fill_markets.values()))
            _require(type(conservative_ms) is bool and (conservative_ms or
                     all(merged_rows[i-1][0] != row[0] for i, row in enumerate(merged_rows) if i)),
                     "CONTINUOUS_UNORDERED_TRADES_REQUIRE_ENVELOPE")
            ordered_events = tuple(
                (r[0], r[4], r[5], r[2], r[6], r[7], r[8])
                for r in merged_rows
            )

            opening_lots = _opening_fifo_lots(before.accepted_fills, market_index)
            valuation = _fold_interval_core(
                markets=markets,
                opening_marks_by_market=marks_map,
                opening_cash_krw=opening_cash_krw,
                opening_units_by_market=units,
                opening_realized_krw=before.realized_net_profit_krw,
                opening_lots=opening_lots,
                ordered_events=ordered_events,
                start=start,
                end=end,
                previous_equity_krw=previous_equity_krw,
                conservative_ms=conservative_ms,
                unordered_marks_or_fills=ambiguous,
                confirmed_closes=confirmed,
                undisclosed_closing=frozenset(undisclosed),
            )
            _require(dict(valuation.closing_units) == {row[3]: row[4] for row in after.inventory if row[4] != 0},
                     "CONTINUOUS_CLOSING_INVENTORY_MISMATCH")
            _require(valuation.realized_net_total_krw == after.realized_net_profit_krw,
                     "CONTINUOUS_FIFO_HISTORY_REFUSED")
            return valuation
    except ContinuousEvidenceError:
        raise
    except (ValueError, TypeError, AttributeError, KeyError, DecimalException, OverflowError):
        raise ContinuousEvidenceError("CONTINUOUS_VALUATION_REFUSED") from None

