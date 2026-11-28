"""Flat-only authentic Upbit KRW interval producer for ContinuousAccountProvider.

``UpbitIntervalSource.collect`` runs one complete, fenced ``collect_upbit`` capture before the tick time is
chosen and stages exactly one BaselineFrame; ``__call__`` hands that frame back without any I/O. The only
interval extrema the authenticated evidence proves today are a flat interval's: zero inventory at the endpoint
and no fill or external flow at or after the previous endpoint, so marked equity is the constant KRW cash and
``minimum == maximum == equity`` exactly. A held position, a fill inside the interval (a round trip that leaves
the endpoints equal included) or any flow refuses; a reviewed intra-interval price path would be needed to go
further, so after a first fill this producer stops the chain (owner open item).

Boundaries: a required 22:00 KST cutoff or the next Seoul midnight must end an interval exactly. A capture whose
first balance read is at or before the boundary and whose fenced observation is at or after it spans the
boundary; its evidence is stamped at the boundary instant (rows, server time and the manifest stay as captured;
each page's own digest is recomputed for the new end). A balance first read after the boundary is never
relabelled. For a capture spanning midnight the collector's structural self-check receives a module-private
opening baseline (the previous state's values at the midnight instant, which under the flat rule are the
reducer's real opening); it is never exported, never staged, and is discarded before the bridge runs the
reducer's own ``risk_baseline``. The capture's fenced observation must still lie within 30 s of
``previous.asof``, the freshness rule every capture meets (R17), so a boundary capture never heals a longer
gap; recovery stays the reviewed re-anchor.

An explicitly provisioned cross-check recorder can persist a verified discrepancy in the local control journal.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from copy import deepcopy
from datetime import datetime, time, timedelta
from decimal import Decimal, DecimalException, Inexact, localcontext
from threading import Lock
from pathlib import Path

from collections.abc import Mapping
from core.compliance.model import KST
from execution_accounts.baseline import (BaselineError, BaselineInterval, BaselineState, _required_cutoff,
                                         advance_baseline, risk_baseline)
from execution_accounts.baseline_bridge import BaselineFrame, BidGapObservation, advance_account_baseline
from execution_accounts.collector import CoverageEvidence, OpeningAnchor, SourceReceipt, TradeFeeEvidence, instant
from execution_accounts.model import (AccountEvidence, CashBalance, EvidencePage, Position,
                                      RiskBaseline, content_digest)
from execution_accounts.continuous import (COVERAGE_CONTRACT, MAX_DURATION, MAX_HELD_MARKETS, MAX_PRINTS, CoverageRequest,
                                           ContinuousEvidenceError, ContinuousPath, PathValuation, PriceMark,
                                           VerifiedCoverage, value_path, value_trade_paths, verify_coverage)
from execution_launch.continuous_archive import archive_candidate
from execution_launch.path_check_guard import PathCheckRecorder
from execution_control.risk import account_fills
from execution_accounts.provider import EvidenceError, _fresh, build_observation
from execution_accounts.upbit_collector import CollectionResult, TradeWindowResult, collect_upbit

BOUNDARY_LEAD_SECONDS = 10   # calibration knob: a boundary capture must start inside this window before the boundary
_ZERO = Decimal(0)


class AccountIntervalError(ValueError):
    """Fixed codes only; never account values, paths or source exception text."""


def _require(ok, code):
    if not ok:
        raise AccountIntervalError(code)


@dataclass(frozen=True, kw_only=True)
class StagedInterval:
    """One prefetched flat interval: the frame for the provider plus the original receipts and manifest for the
    caller's private archive. ``observed_at`` is the real fenced observation, at or after ``frame.interval.end``.
    The collector's self-check bundle is not retained."""
    frame: BaselineFrame
    receipts: tuple[SourceReceipt, ...]
    manifest_sha256: str
    observed_at: datetime


def _pending_boundary(previous):
    """The next exact interval end the reducer requires: a pending 22:00 cutoff, else the next Seoul midnight."""
    cutoff = _required_cutoff(previous)
    if cutoff is not None and previous.asof < cutoff:
        return cutoff, False
    day = previous.asof.astimezone(KST).date()
    return datetime.combine(day + timedelta(days=1), time(), tzinfo=KST), True


def split_boundary_intervals(start: datetime, end: datetime, *, first_trading_day,
                             previous_day_realized_net_krw, recovery_cutoff_seconds: int | None = 79200
                             ) -> tuple[tuple[datetime, datetime], ...]:
    """Deterministically split [start, end) across required 22:00 KST recovery and 00:00 KST midnight boundaries."""
    s = instant(start)
    e = instant(end)
    _require(s < e, "ACCOUNT_INTERVAL_INPUT_REQUIRED")
    segments: list[tuple[datetime, datetime]] = []
    cur = s
    prev_profit = previous_day_realized_net_krw
    while True:
        cur_day = cur.astimezone(KST).date()
        eligible_cutoff = (
            recovery_cutoff_seconds is not None
            and ((prev_profit is None and cur_day == first_trading_day) or prev_profit == _ZERO)
        )
        cutoff = (
            datetime.combine(cur_day, time(), tzinfo=KST) + timedelta(seconds=recovery_cutoff_seconds)
            if eligible_cutoff else None
        )
        midnight = datetime.combine(cur_day + timedelta(days=1), time(), tzinfo=KST)
        boundary = cutoff if (cutoff is not None and cur < cutoff) else midnight
        if e <= boundary:
            segments.append((cur, e))
            break
        segments.append((cur, boundary))
        if boundary == midnight:
            prev_profit = _ZERO if prev_profit is None else prev_profit
        cur = boundary
    return tuple(segments)


def _opening_collection_baseline(previous, opening):
    """Collector self-check input for a capture spanning Seoul midnight; module-private, never exported or staged.

    The collector validates its bundle against a same-day baseline at most 30 s old, and no reducer export can
    carry the new day before the interval exists. Under the flat rule these are the reducer's real midnight
    opening values; the bridge then reconciles the reducer's own export against the same accounts.
    """
    return RiskBaseline(day_start_equity=previous.equity_krw, prior_high_watermark=previous.high_watermark,
                        observed_daily_loss=_ZERO, approved_effective_floor=previous.approved_effective_floor,
                        first_trading_day=previous.first_trading_day, asof=opening,
                        source_sha256=previous.state_digest)


def _stamped(account, end):
    """The same evidence stamped at the boundary instant; rows and the manifest are unchanged, and each page's
    own digest is recomputed for the new end."""
    return replace(account, observed_at=end, restrictions=replace(account.restrictions, asof=end),
                   fx=tuple(replace(rate, asof=end) for rate in account.fx),
                   pages=tuple(replace(page, end=end, page_sha256="") for page in account.pages))


def _closed_orders_at_cutoff(orders, accepted_fills):
    """Only a fully filled order is proved closed solely by its fills before the cutoff."""
    filled = {}
    for fill in accepted_fills:
        filled[fill.order_id] = filled.get(fill.order_id, _ZERO) + fill.quantity
    _require(all(order.status == "filled" and filled.get(order.order_id, _ZERO) == order.quantity
                 for order in orders), "ACCOUNT_INTERVAL_BOUNDARY_ORDER_EVIDENCE_REQUIRED")
    return orders


def _reconstruct_cutoff_account(account: AccountEvidence, cutoff: datetime, valuation: PathValuation,
                                accepted_fills, flows, manifest_sha256: str) -> AccountEvidence:
    marks_by_sym = {m.symbol: m for m in valuation.closing_marks}
    units_by_sym = dict(valuation.closing_units)
    positions = tuple(
        Position(
            market="spot", symbol=sym, quote_currency="KRW", units=qty,
            price=marks_by_sym[sym].price, asof=marks_by_sym[sym].asof, base_currency=sym[4:],
        )
        for sym, qty in sorted(units_by_sym.items())
    )
    orig_orders = tuple(order for page in account.pages if page.kind == "orders" for order in page.rows)
    projected_orders = _closed_orders_at_cutoff(orig_orders, accepted_fills)
    pages = tuple(
        EvidencePage(kind=kind, cursor=None, next_cursor=None, start=account.origin, end=cutoff,
                     rows=tuple(rows), source_sha256=manifest_sha256)
        for kind, rows in (("fills", accepted_fills), ("flows", flows), ("orders", projected_orders))
    )
    return replace(
        account,
        balances=(CashBalance(currency="KRW", total=valuation.closing_cash_krw, settled=valuation.closing_cash_krw),),
        positions=positions,
        pages=pages,
        observed_at=cutoff,
    )


def _opening_trade_marks(retained, prior_prints, symbols, units, *, start, equity, cash):
    """Use only prices knowable at the interval opening, or the unique residual at that instant."""
    marks = {symbol: retained[symbol] for symbol in symbols if symbol in retained}
    for symbol in symbols:
        if symbol not in marks and symbol in prior_prints:
            trade = prior_prints[symbol]
            _require(trade.market == symbol and trade.at < start, "ACCOUNT_INTERVAL_OPENING_MARK_INVALID")
            marks[symbol] = PriceMark(symbol=symbol, price=trade.price, asof=trade.at)
    _require(all(type(mark) is PriceMark and mark.symbol == symbol and mark.asof <= start
                 and type(mark.price) is Decimal and mark.price.is_finite() and mark.price > _ZERO
                 for symbol, mark in marks.items()), "ACCOUNT_INTERVAL_OPENING_MARK_INVALID")
    missing = [symbol for symbol, amount in units if amount > _ZERO and symbol not in marks]
    if len(missing) == 1:
        symbol = missing[0]
        known = sum((qty * marks[sym].price for sym, qty in units if sym in marks), _ZERO)
        price = (equity - cash - known) / dict(units)[symbol]
        _require(price > _ZERO, "ACCOUNT_INTERVAL_OPENING_MARK_INVALID")
        marks[symbol] = PriceMark(symbol=symbol, price=price, asof=start)
    _require(all(symbol in marks for symbol in symbols), "ACCOUNT_INTERVAL_OPENING_MARK_REQUIRED")
    return marks


def _capture_bid_gap(value, account_scope, at):
    threshold = value(at, account_scope) if callable(value) else value
    _require(threshold is None or (type(threshold) is Decimal and threshold.is_finite()
                                   and _ZERO < threshold <= Decimal("0.05")),
             "ACCOUNT_INTERVAL_BID_GAP_POLICY_INVALID")
    return BidGapObservation(account_scope=account_scope, asof=at, threshold=threshold)


def upbit_held_interval_frames(previous: BaselineState, collection: CollectionResult, *,
                               trade_path: Mapping[str, object], bid_gap_y=None,
                               opening_marks: Mapping[str, PriceMark | Decimal] | tuple[PriceMark, ...] | None = None
                               ) -> tuple[BaselineFrame, ...]:
    """Build 1 or 2 reconciled BaselineFrames over Approach A multi-coin trade windows + order fills.

    When `[previous.asof, observed)` straddles a required `22:00 KST` recovery cutoff or `00:00 KST` Seoul
    midnight, deterministically splits into `[previous.asof, boundary)` and `[boundary, observed)`.
    """
    try:
        with localcontext() as numeric:
            numeric.prec = 512
            numeric.traps[Inexact] = True
            _require(type(previous) is BaselineState and type(collection) is CollectionResult
                     and isinstance(trade_path, Mapping) and len(trade_path) <= MAX_HELD_MARKETS,
                     "ACCOUNT_INTERVAL_INPUT_REQUIRED")
            bundle, receipts = collection.bundle, collection.receipts
            _require(len(bundle.accounts) == 1 and bool(receipts)
                     and bundle.accounts[0].venue == "upbit" and bundle.accounts[0].execution_quote == "KRW"
                     and bundle.accounts[0].account_scope == previous.account_scope
                     and all(page.source_sha256 == collection.manifest_sha256 for page in bundle.accounts[0].pages)
                     and bundle.risk_baseline.first_trading_day == previous.first_trading_day,
                     "ACCOUNT_INTERVAL_COLLECTION_BINDING_INVALID")
            account = bundle.accounts[0]
            first, observed = receipts[0].received_at, account.observed_at
            _require(previous.asof < first <= observed, "ACCOUNT_INTERVAL_CAPTURE_NOT_AFTER_PREVIOUS")
            _fresh(previous.asof, observed)

            endpoint_gap = _capture_bid_gap(bid_gap_y, account.account_scope, observed)
            observation = build_observation(bundle, now=observed, bid_gap_y=endpoint_gap.threshold)
            all_fills = observation.fills
            _require(all(f.executed_at < observed for f in all_fills), "ACCOUNT_INTERVAL_FILL_AFTER_BOUNDARY")

            seen_flows = {}
            flows_list = []
            flow_delta = _ZERO
            for page in account.pages:
                if page.kind == "flows":
                    for flow in page.rows:
                        if flow.flow_id in seen_flows:
                            _require(seen_flows[flow.flow_id] == flow, "ACCOUNT_INTERVAL_FLOW_CONTRADICTION")
                            continue
                        seen_flows[flow.flow_id] = flow
                        _require(flow.effective_at < previous.asof, "ACCOUNT_INTERVAL_EXTERNAL_FLOW_UNSUPPORTED")
                        _require(flow.currency == "KRW" and flow.kind in ("deposit", "withdrawal"),
                                 "ACCOUNT_INTERVAL_EXTERNAL_FLOW_UNSUPPORTED")
                        flows_list.append(flow)
                        flow_delta += flow.amount if flow.kind == "deposit" else -flow.amount

            _require(len(account.opening_cash) == 1 and account.opening_cash[0].currency == "KRW",
                     "ACCOUNT_INTERVAL_KRW_ANCHOR_REQUIRED")
            base_anchor_cash = account.opening_cash[0].amount + flow_delta

            # Determine exact segment endpoints (splitting across 22:00 KST or 00:00 KST if straddled,
            # or stopping at boundary when first <= boundary <= observed in non-straddled bracket mode).
            segments: list[tuple[datetime, datetime]] = []
            cur_state = previous
            # Check if capture straddles boundary (`previous.asof < boundary < observed`)
            boundary0, _ = _pending_boundary(previous)
            if observed <= boundary0:
                segments.append((previous.asof, observed))
            else:
                segments.append((previous.asof, boundary0))
                if boundary0 < observed:
                    segments.append((boundary0, observed))

            # Normalize opening_marks dict
            marks_seed: dict[str, PriceMark] = {}
            if isinstance(opening_marks, Mapping):
                for sym, val in opening_marks.items():
                    marks_seed[sym] = val if type(val) is PriceMark else PriceMark(symbol=sym, price=val, asof=previous.asof)
            elif isinstance(opening_marks, tuple):
                for val in opening_marks:
                    marks_seed[val.symbol] = val

            # Extract all prints per market from trade_path
            all_prints_by_sym: dict[str, tuple[object, ...]] = {}
            opening_print_by_sym: dict[str, object] = {}
            proof_digests: list[tuple[str, str]] = []
            total_prints = 0
            for sym, win in sorted(trade_path.items()):
                _require(getattr(win, "ticker_discrepancy", None) is None,
                         "ACCOUNT_INTERVAL_TICKER_CHECK_BLOCK_ALERT_REQUIRED")
                if hasattr(win, "prints"):
                    _require(win.market == sym and win.start == previous.asof and win.end == observed,
                             "ACCOUNT_INTERVAL_TRADE_WINDOW_MISMATCH")
                raw_prints = getattr(win, "prints", win)
                _require(type(raw_prints) in (tuple, list), "ACCOUNT_INTERVAL_TRADE_WINDOW_MISMATCH")
                total_prints += len(raw_prints)
                _require(total_prints <= MAX_PRINTS, "ACCOUNT_INTERVAL_TRADE_WINDOW_TOO_LARGE")
                for item in raw_prints:
                    stamp = item.asof if type(item) is PriceMark else (item[0] if type(item) is tuple else item.at)
                    _require(previous.asof <= stamp < observed, "ACCOUNT_INTERVAL_TRADE_WINDOW_MISMATCH")
                all_prints_by_sym[sym] = tuple(raw_prints)
                op = getattr(win, "opening_print", None)
                if op is not None:
                    opening_print_by_sym[sym] = op
                psh = getattr(win, "proof_sha256", None)
                if type(psh) is str:
                    proof_digests.append((sym, psh))

            frames: list[BaselineFrame] = []
            cur_marks = dict(marks_seed)
            for seg_idx, (seg_start, seg_end) in enumerate(segments):
                hist_fills = tuple(f for f in all_fills if f.executed_at < seg_start)
                seg_fills = tuple(f for f in all_fills if seg_start <= f.executed_at < seg_end)
                prior_acc = account_fills(hist_fills)
                _require(prior_acc.ok and prior_acc.duplicate_count == 0, "ACCOUNT_INTERVAL_PRIOR_HISTORY_REFUSED")
                seg_cash = base_anchor_cash + sum(
                    (amt for venue, scope, amt in prior_acc.cash_deltas_by_account_krw
                     if venue == "upbit" and scope == previous.account_scope),
                    _ZERO,
                )
                seg_units = tuple((row[3], row[4]) for row in prior_acc.inventory if row[4] != 0)
                required_syms = set(dict(seg_units)) | {f.symbol for f in seg_fills}
                _require(required_syms <= set(all_prints_by_sym), "ACCOUNT_INTERVAL_TRADE_WINDOW_REQUIRED")
                active_syms = sorted(required_syms | set(all_prints_by_sym))
                _require(len(active_syms) <= MAX_HELD_MARKETS, "ACCOUNT_INTERVAL_EXTREMA_EVIDENCE_REQUIRED")

                cur_marks = _opening_trade_marks(
                    cur_marks, opening_print_by_sym, active_syms, seg_units,
                    start=seg_start, equity=cur_state.equity_krw, cash=seg_cash,
                )

                seg_trade_path = {}
                for sym in active_syms:
                    pts = []
                    for item in all_prints_by_sym.get(sym, ()):
                        p_at = item.asof if type(item) is PriceMark else (item[0] if isinstance(item, tuple) else item.at)
                        if seg_start <= p_at < seg_end:
                            pts.append(item)
                    seg_trade_path[sym] = tuple(pts)

                valuation = value_trade_paths(
                    seg_trade_path,
                    opening_marks=cur_marks,
                    opening_cash_krw=seg_cash,
                    opening_units=seg_units,
                    historical_fills=hist_fills,
                    interval_fills=seg_fills,
                    previous_equity_krw=cur_state.equity_krw,
                    previous_realized_net_krw=cur_state.realized_net_total_krw,
                    start=seg_start,
                    end=seg_end,
                    account_scope=previous.account_scope,
                    conservative_ms=True,
                    closing_marks=({
                        pos.symbol: PriceMark(symbol=pos.symbol, price=pos.price, asof=pos.asof)
                        for pos in account.positions if pos.unlisted is not True
                    } if seg_end == observed else None),
                )

                if seg_end == observed:
                    _require(len(account.balances) == 1 and account.balances[0].currency == "KRW"
                             and valuation.closing_cash_krw == account.balances[0].total,
                             "ACCOUNT_INTERVAL_CLOSING_CASH_MISMATCH")
                    closing_units = tuple(sorted((pos.symbol, pos.units) for pos in account.positions))
                    _require(valuation.closing_units == closing_units,
                             "ACCOUNT_INTERVAL_CLOSING_HOLDINGS_MISMATCH")
                    c_marks = {m.symbol: m for m in valuation.closing_marks}
                    _require(all(pos.price == c_marks[pos.symbol].price for pos in account.positions),
                             "ACCOUNT_INTERVAL_CLOSING_MARK_MISMATCH")
                    seg_accounts = (account,)
                else:
                    cutoff_acc = _reconstruct_cutoff_account(
                        account, seg_end, valuation, hist_fills + seg_fills,
                        tuple(flows_list), collection.manifest_sha256,
                    )
                    seg_accounts = (cutoff_acc,)

                gap = endpoint_gap if seg_end == observed else _capture_bid_gap(bid_gap_y, account.account_scope, seg_end)
                cov_sha = content_digest((collection.manifest_sha256, seg_start, seg_end, tuple(proof_digests), gap))
                interval = BaselineInterval(
                    account_scope=previous.account_scope,
                    sequence=cur_state.sequence + 1,
                    previous_state_digest=cur_state.state_digest,
                    start=seg_start,
                    end=seg_end,
                    equity_krw=valuation.equity_krw,
                    minimum_equity_krw=valuation.minimum_equity_krw,
                    maximum_equity_krw=valuation.maximum_equity_krw,
                    realized_net_total_krw=valuation.realized_net_total_krw,
                    gross_external_inflows_krw=_ZERO,
                    gross_external_outflows_krw=_ZERO,
                    source_sha256=content_digest(seg_accounts),
                    coverage_sha256=cov_sha,
                )
                reconcile_now = observed if seg_end.astimezone(KST).date() == observed.astimezone(KST).date() else seg_end
                update = advance_account_baseline(cur_state, interval, seg_accounts, now=reconcile_now, bid_gap=gap)
                cur_state = update.state
                for cm in valuation.closing_marks:
                    cur_marks[cm.symbol] = cm
                frames.append(BaselineFrame(interval=interval, accounts=seg_accounts, bid_gap=gap))

            return tuple(frames)
    except (AccountIntervalError, ContinuousEvidenceError, EvidenceError, BaselineError):
        raise
    except (ValueError, TypeError, AttributeError, KeyError, IndexError, DecimalException, OverflowError):
        raise AccountIntervalError("ACCOUNT_INTERVAL_EVIDENCE_REFUSED") from None


def upbit_interval_frame(previous: BaselineState, collection: CollectionResult, *,
                         trade_path: Mapping[str, object] | None = None, bid_gap_y=None,
                         opening_marks: Mapping[str, PriceMark | Decimal] | tuple[PriceMark, ...] | None = None
                         ) -> BaselineFrame:
    """Pure: one flat interval [previous.asof, end) over one capture, or held interval when trade_path supplied."""
    if trade_path is not None:
        frames = upbit_held_interval_frames(previous, collection, trade_path=trade_path, opening_marks=opening_marks,
                                           bid_gap_y=bid_gap_y)
        _require(len(frames) == 1, "ACCOUNT_INTERVAL_BOUNDARY_SPLIT_REQUIRED")
        return frames[0]
    try:
        _require(type(previous) is BaselineState and type(collection) is CollectionResult,
                 "ACCOUNT_INTERVAL_INPUT_REQUIRED")
        bundle, receipts = collection.bundle, collection.receipts
        _require(len(bundle.accounts) == 1 and bool(receipts)
                 and bundle.accounts[0].venue == "upbit" and bundle.accounts[0].execution_quote == "KRW"
                 and all(page.source_sha256 == collection.manifest_sha256 for page in bundle.accounts[0].pages)
                 and bundle.risk_baseline.first_trading_day == previous.first_trading_day,
                 "ACCOUNT_INTERVAL_COLLECTION_BINDING_INVALID")
        account = bundle.accounts[0]
        first, observed = receipts[0].received_at, account.observed_at
        _require(previous.asof < first, "ACCOUNT_INTERVAL_CAPTURE_NOT_AFTER_PREVIOUS")
        boundary, _ = _pending_boundary(previous)
        if observed < boundary:
            end = observed
        else:
            _require(first <= boundary, "ACCOUNT_INTERVAL_BOUNDARY_MISSED")
            end = boundary
        # ponytail: flat-only exact extrema; held intervals need a reviewed price-path source
        _require(account.positions == (), "ACCOUNT_INTERVAL_EXTREMA_EVIDENCE_REQUIRED")
        for page in account.pages:
            if page.kind == "fills":
                _require(all(row.executed_at < previous.asof for row in page.rows),
                         "ACCOUNT_INTERVAL_EXTREMA_EVIDENCE_REQUIRED")
            elif page.kind == "flows":
                _require(all(row.effective_at < previous.asof for row in page.rows),
                         "ACCOUNT_INTERVAL_EXTERNAL_FLOW_UNSUPPORTED")
        equity = build_observation(bundle, now=observed).risk.equity
        accounts = (account if end == observed else _stamped(account, end),)
        interval = BaselineInterval(account_scope=previous.account_scope, sequence=previous.sequence + 1,
            previous_state_digest=previous.state_digest, start=previous.asof, end=end, equity_krw=equity,
            minimum_equity_krw=equity, maximum_equity_krw=equity,
            realized_net_total_krw=previous.realized_net_total_krw,
            gross_external_inflows_krw=_ZERO, gross_external_outflows_krw=_ZERO,
            source_sha256=content_digest(accounts), coverage_sha256=collection.manifest_sha256)
        return BaselineFrame(interval=interval, accounts=accounts)
    except (AccountIntervalError, EvidenceError, BaselineError):
        raise
    except (ValueError, TypeError, AttributeError, KeyError, IndexError, DecimalException, OverflowError):
        raise AccountIntervalError("ACCOUNT_INTERVAL_EVIDENCE_REFUSED") from None


class UpbitIntervalSource:
    """``source(previous, now)`` for ContinuousAccountProvider over one prefetched collection.

    ``collect`` fetches and stages before the tick time is chosen; ``__call__`` returns the staged frame without
    I/O when it extends ``previous`` or is its committed endpoint, so same-tick redelivery advances the head once.
    Frames live in memory only: after a restart the provider refuses until a fresh ``collect``.
    When ``trade_window_collector`` is configured, held positions (<= 4 KRW markets), interval fills, open-order
    locks, and straddled 22:00 / 00:00 KST boundary splits are evaluated via Approach A ``value_trade_paths``.
    """

    @property
    def execution_ready(self) -> bool:
        """A retained preview does not establish production coverage or order authority."""
        return False

    def __init__(self, *, trade_window_collector=None, order_fill_collector=None, opening_marks=None,
                 bid_gap_y=None, path_check_recorder=None):
        _require(path_check_recorder is None or (type(path_check_recorder) is PathCheckRecorder
                 and callable(trade_window_collector)), "ACCOUNT_INTERVAL_INPUT_REQUIRED")
        self._path_check_recorder = path_check_recorder
        self._bid_gap_y = bid_gap_y
        _require(trade_window_collector is None or callable(trade_window_collector),
                 "ACCOUNT_INTERVAL_INPUT_REQUIRED")
        _require(order_fill_collector is None or callable(order_fill_collector),
                 "ACCOUNT_INTERVAL_INPUT_REQUIRED")
        self._lock = Lock()          # guards _staged and _frames only; collect_upbit runs outside it
        self._staged = None
        self._frames: tuple[BaselineFrame, ...] = ()
        self._trade_window_collector = trade_window_collector
        self._order_fill_collector = order_fill_collector
        self._marks_by_state: dict[str, dict[str, PriceMark]] = {}
        self._seed_marks = opening_marks

    @property
    def staged_frames(self) -> tuple[BaselineFrame, ...]:
        with self._lock:
            return self._frames

    def collect(self, collector_source, *, previous: BaselineState, anchor: OpeningAnchor,
                coverage: CoverageEvidence, clock, trade_fees: tuple[TradeFeeEvidence, ...] = (),
                opening_marks=None) -> StagedInterval:
        try:
            _require(type(previous) is BaselineState and callable(clock) and type(trade_fees) is tuple,
                     "ACCOUNT_INTERVAL_INPUT_REQUIRED")
            _require(getattr(collector_source, "account_scope", None) == previous.account_scope,
                     "ACCOUNT_INTERVAL_SCOPE_MISMATCH")
            exported = risk_baseline(previous, now=previous.asof, expected_head=previous.state_digest)
            started = instant(clock())
            boundary, midnight = _pending_boundary(previous)
            held_mode = self._trade_window_collector is not None
            if not held_mode:
                _require(started <= boundary, "ACCOUNT_INTERVAL_BOUNDARY_MISSED")
                in_window = boundary - started <= timedelta(seconds=BOUNDARY_LEAD_SECONDS)
            else:
                in_window = boundary - started <= timedelta(seconds=BOUNDARY_LEAD_SECONDS)
            baseline = _opening_collection_baseline(previous, boundary) if in_window and midnight else exported
            collection = collect_upbit(collector_source, anchor=anchor, coverage=coverage, risk_baseline=baseline,
                                       clock=clock, trade_fees=trade_fees,
                                       allow_proportional_fees=held_mode)
            observed = collection.bundle.accounts[0].observed_at
            if in_window and midnight:   # R17: and the 30 s rule against previous.asof that every capture meets
                _fresh(previous.asof, observed)
            if not held_mode:
                frame = upbit_interval_frame(previous, collection)
                _require(not in_window or frame.interval.end == boundary, "ACCOUNT_INTERVAL_BOUNDARY_NOT_BRACKETED")
                frames = (frame,)
                receipts = collection.receipts
            else:
                account = collection.bundle.accounts[0]
                fills_page = next((p.rows for p in account.pages if p.kind == "fills"), ())
                orders_page = next((p.rows for p in account.pages if p.kind == "orders"), ())
                hist_fills = tuple(f for f in fills_page if f.executed_at < previous.asof)
                in_fills = tuple(f for f in fills_page if previous.asof <= f.executed_at < observed)
                prior_acc = account_fills(hist_fills)
                _require(prior_acc.ok and prior_acc.duplicate_count == 0, "ACCOUNT_INTERVAL_PRIOR_HISTORY_REFUSED")
                prior_syms = {row[3] for row in prior_acc.inventory if row[4] != 0}
                held_syms = {pos.symbol for pos in account.positions if pos.units > _ZERO}
                fill_syms = {f.symbol for f in in_fills}
                active_syms = sorted(prior_syms | held_syms | fill_syms)
                _require(len(active_syms) <= MAX_HELD_MARKETS, "ACCOUNT_INTERVAL_EXTREMA_EVIDENCE_REQUIRED")
                extra_receipts: list[SourceReceipt] = []
                order_details = {}
                if in_fills:
                    _require(self._order_fill_collector is not None, "ACCOUNT_INTERVAL_ORDER_DETAIL_REQUIRED")
                    in_oids = sorted({f.order_id for f in in_fills})
                    for oid in in_oids:
                        of_res = self._order_fill_collector(
                            collector_source, oid, account_scope=previous.account_scope,
                            fee_evidence=trade_fees, clock=clock,
                        )
                        captured = {f.fill_id: f for f in fills_page if f.order_id == oid}
                        checked = {f.fill_id: f for f in of_res.fills}
                        _require(of_res.order_id == oid and len(checked) == len(of_res.fills)
                                 and checked == captured and of_res.order is not None
                                 and of_res.order in orders_page and type(of_res.receipt) is SourceReceipt,
                                 "ACCOUNT_INTERVAL_ORDER_DETAIL_MISMATCH")
                        order_details[oid] = of_res
                        extra_receipts.append(of_res.receipt)
                trade_windows = {}
                for sym in active_syms:
                    win = self._trade_window_collector(
                        collector_source, sym, start=previous.asof, end=observed,
                        account_scope=previous.account_scope, clock=clock,
                    )
                    _require(type(win) is TradeWindowResult and win.market == sym
                             and win.start == previous.asof and win.end == observed
                             and type(win.receipts) is tuple and bool(win.receipts)
                             and all(type(receipt) is SourceReceipt and receipt.account_scope == previous.account_scope
                                     for receipt in win.receipts), "ACCOUNT_INTERVAL_TRADE_WINDOW_MISMATCH")
                    if self._path_check_recorder is not None:
                        recorder = self._path_check_recorder
                        _require(recorder.account_scope == previous.account_scope, "ACCOUNT_INTERVAL_CHECK_SCOPE")
                        order_ids = frozenset(f.order_id for f in in_fills if f.symbol == sym)
                        recorder.check_window(win, tuple(order_details[oid] for oid in sorted(order_ids)),
                            expected_order_ids=order_ids, now=clock(),
                            trade_fees=tuple(fee for fee in trade_fees if fee.order_id in order_ids))
                    trade_windows[sym] = win
                    extra_receipts.extend(win.receipts)
                with self._lock:
                    cached_marks = dict(self._marks_by_state.get(previous.state_digest, {}))
                eff_marks = opening_marks if opening_marks is not None else (cached_marks or self._seed_marks)
                if not active_syms and not in_fills and observed <= boundary:
                    frame = upbit_interval_frame(previous, collection)
                    gap = _capture_bid_gap(self._bid_gap_y, account.account_scope, frame.interval.end)
                    coverage_hash = content_digest((frame.interval.coverage_sha256, gap))
                    frames = (replace(frame, interval=replace(frame.interval, coverage_sha256=coverage_hash),
                                      bid_gap=gap),)
                else:
                    frames = upbit_held_interval_frames(
                        previous, collection, trade_path=trade_windows, opening_marks=eff_marks, bid_gap_y=self._bid_gap_y,
                    )
                receipts = collection.receipts + tuple(extra_receipts)
                # Cache closing marks keyed by each frame's resulting state digest
                sim_state = previous
                new_marks_cache: dict[str, dict[str, PriceMark]] = {}
                for fr in frames:
                    sim_state = advance_baseline(sim_state, fr.interval)
                    fr_acc = fr.accounts[0]
                    new_marks_cache[sim_state.state_digest] = {
                        pos.symbol: PriceMark(symbol=pos.symbol, price=pos.price, asof=pos.asof)
                        for pos in fr_acc.positions
                    }
                with self._lock:
                    self._marks_by_state = new_marks_cache
            staged = StagedInterval(frame=frames[-1], receipts=receipts,
                                    manifest_sha256=collection.manifest_sha256,
                                    observed_at=observed)
        except (AccountIntervalError, ContinuousEvidenceError, EvidenceError, BaselineError):
            raise
        except Exception:
            raise AccountIntervalError("ACCOUNT_INTERVAL_COLLECTION_FAILED") from None
        with self._lock:
            self._staged = staged
            self._frames = frames
        return staged

    def __call__(self, previous: BaselineState, now: datetime) -> BaselineFrame:
        try:
            _require(type(previous) is BaselineState and type(now) is datetime and now.utcoffset() is not None,
                     "ACCOUNT_INTERVAL_INPUT_REQUIRED")
            with self._lock:
                staged = self._staged
                frames = self._frames
            _require(staged is not None and bool(frames), "ACCOUNT_INTERVAL_PREFETCH_REQUIRED")
            _require(staged.observed_at <= now, "ACCOUNT_INTERVAL_EVIDENCE_AFTER_TICK")
            for candidate in frames:
                interval = candidate.interval
                extends = (interval.previous_state_digest == previous.state_digest
                           and interval.sequence == previous.sequence + 1)
                if extends:
                    return candidate
            last = frames[-1]
            interval = last.interval
            committed = (interval.sequence == previous.sequence and interval.end == previous.asof
                         and content_digest(interval) == previous.last_interval_digest)
            _require(committed, "ACCOUNT_INTERVAL_PREFETCH_REQUIRED")
            return last
        except AccountIntervalError:
            raise
        except (ValueError, TypeError, AttributeError):
            raise AccountIntervalError("ACCOUNT_INTERVAL_EVIDENCE_REFUSED") from None


@dataclass(frozen=True, kw_only=True)
class ContinuousCapture:
    """Source view without the collector's temporary risk-baseline self-check."""
    accounts: tuple[AccountEvidence, ...]
    receipts: tuple[SourceReceipt, ...]
    manifest_sha256: str
    observed_at: datetime


@dataclass(frozen=True, kw_only=True)
class ContinuousIntervalPreview:
    """Verified source-path mathematics, deliberately NOT a BaselineFrame.

    Current owner limits, chronological D12 floor ratchets and durable E2 halt
    integration are still required before any account baseline may advance.
    Consequently ContinuousAccountProvider rejects this type.
    """
    interval: BaselineInterval
    accounts: tuple[AccountEvidence, ...]
    path: ContinuousPath
    coverage: VerifiedCoverage
    valuation: PathValuation

    @property
    def execution_ready(self):
        return False


@dataclass(frozen=True, kw_only=True)
class StagedContinuousCandidate:
    preview: ContinuousIntervalPreview
    path_sha256: str
    manifest_sha256: str
    observed_at: datetime
    capture: ContinuousCapture
    anchor: OpeningAnchor
    collection_coverage: CoverageEvidence
    trade_fees: tuple[TradeFeeEvidence, ...]
    collection_requested_at: datetime
    collection_clock: tuple[datetime, ...]
    collection_baseline_sha256: str

    @property
    def first_received_at(self):
        return self.capture.receipts[0].received_at

    @property
    def collection_started_at(self):
        return self.collection_clock[0]

    @property
    def collection_completed_at(self):
        return self.collection_clock[1]

    @property
    def execution_ready(self):
        return False


def preview_continuous_upbit_interval(previous: BaselineState, collection: CollectionResult,
                                    path: ContinuousPath, *, coverage_verifier, now: datetime) -> ContinuousIntervalPreview:
    """Exact arithmetic wrapper for the independently authenticated held path."""
    try:
        with localcontext() as numeric:
            numeric.prec = 512
            numeric.traps[Inexact] = True
            return _preview_continuous_upbit_interval(previous, collection, path,
                                                    coverage_verifier=coverage_verifier, now=now)
    except (AccountIntervalError, ContinuousEvidenceError, EvidenceError, BaselineError):
        raise
    except (ValueError, TypeError, AttributeError, KeyError, DecimalException, OverflowError):
        raise AccountIntervalError("ACCOUNT_INTERVAL_CONTINUOUS_EVIDENCE_REFUSED") from None


def _preview_continuous_upbit_interval(previous: BaselineState, collection: CollectionResult,
                                    path: ContinuousPath, *, coverage_verifier, now: datetime,
                                    retained_coverage: VerifiedCoverage | None = None) -> ContinuousIntervalPreview:
    """A held-position candidate after independently authenticated complete-path evidence.

    The original fenced capture reconciles cash, positions, history and fees.
    A reviewed verifier must additionally authenticate every ordered valuation
    change through the half-open endpoint. No production Upbit coverage verifier
    is shipped. Raw snapshots, a heartbeat, or a boolean cannot use this path.
    The baseline reducer and bridge recheck the derived extrema and counters.
    """
    try:
        _require(type(previous) is BaselineState and type(collection) is CollectionResult,
                 "ACCOUNT_INTERVAL_INPUT_REQUIRED")
        bundle, receipts = collection.bundle, collection.receipts
        _require(len(bundle.accounts) == 1 and bool(receipts)
                 and bundle.accounts[0].venue == "upbit" and bundle.accounts[0].execution_quote == "KRW"
                 and bundle.accounts[0].account_scope == previous.account_scope
                 and all(page.source_sha256 == collection.manifest_sha256 for page in bundle.accounts[0].pages)
                 and bundle.risk_baseline.first_trading_day == previous.first_trading_day,
                 "ACCOUNT_INTERVAL_COLLECTION_BINDING_INVALID")
        account = bundle.accounts[0]
        first, observed = receipts[0].received_at, account.observed_at
        _require(previous.asof < first <= observed <= now, "ACCOUNT_INTERVAL_CAPTURE_NOT_AFTER_PREVIOUS")
        _fresh(previous.asof, observed)
        boundary, _ = _pending_boundary(previous)
        end = min(observed, boundary)
        _require(observed < boundary or first <= boundary, "ACCOUNT_INTERVAL_BOUNDARY_MISSED")
        _require(type(path) is ContinuousPath and path.account_scope == previous.account_scope
                 and path.previous_state_digest == previous.state_digest
                 and path.start == previous.asof and path.end == end,
                 "ACCOUNT_INTERVAL_PRICE_PATH_BINDING_INVALID")
        observation = build_observation(bundle, now=observed)
        fills = observation.fills
        _require(all(fill.executed_at < end for fill in fills), "ACCOUNT_INTERVAL_FILL_AFTER_BOUNDARY")
        historical = tuple(fill for fill in fills if fill.executed_at < previous.asof)
        inside = tuple(fill for fill in fills if previous.asof <= fill.executed_at < end)
        prior = account_fills(historical)
        _require(prior.ok and prior.duplicate_count == 0, "ACCOUNT_INTERVAL_PRIOR_HISTORY_REFUSED")
        _require(len(account.opening_cash) == 1 and account.opening_cash[0].currency == "KRW",
                 "ACCOUNT_INTERVAL_KRW_ANCHOR_REQUIRED")
        cash = account.opening_cash[0].amount
        cash += sum((amount for venue, scope, amount in prior.cash_deltas_by_account_krw
                     if venue == "upbit" and scope == previous.account_scope), _ZERO)
        seen_flows = {}
        for page in account.pages:
            if page.kind == "flows":
                for flow in page.rows:
                    if flow.flow_id in seen_flows:
                        _require(seen_flows[flow.flow_id] == flow, "ACCOUNT_INTERVAL_FLOW_CONTRADICTION")
                        continue
                    seen_flows[flow.flow_id] = flow
                    _require(flow.effective_at < previous.asof,
                             "ACCOUNT_INTERVAL_EXTERNAL_FLOW_UNSUPPORTED")
                    _require(flow.currency == "KRW" and flow.kind in ("deposit", "withdrawal"),
                             "ACCOUNT_INTERVAL_EXTERNAL_FLOW_UNSUPPORTED")
                    cash += flow.amount if flow.kind == "deposit" else -flow.amount
        units = tuple((row[3], row[4]) for row in prior.inventory if row[4] != 0)
        valuation = value_path(path, opening_cash_krw=cash, opening_units=units, historical_fills=historical,
            interval_fills=inside, previous_equity_krw=previous.equity_krw,
            previous_realized_net_krw=previous.realized_net_total_krw)
        _require(len(account.balances) == 1 and account.balances[0].currency == "KRW"
                 and valuation.closing_cash_krw == account.balances[0].total,
                 "ACCOUNT_INTERVAL_CLOSING_CASH_MISMATCH")
        closing_units = tuple(sorted((position.symbol, position.units) for position in account.positions))
        _require(valuation.closing_units == closing_units, "ACCOUNT_INTERVAL_CLOSING_HOLDINGS_MISMATCH")
        marks = {mark.symbol: mark for mark in valuation.closing_marks}
        if end == observed:
            _require(all(position.price == marks[position.symbol].price for position in account.positions)
                     and valuation.equity_krw == observation.risk.equity,
                     "ACCOUNT_INTERVAL_CLOSING_MARK_MISMATCH")
            accounts = (account,)
        else:
            # The fenced capture brackets the boundary and has no account changes.
            # Prices are reconstructed from the verified path at the boundary,
            # never copied backwards from a later ticker snapshot.
            endpoint = _stamped(account, end)
            endpoint = replace(endpoint, positions=tuple(replace(position, price=marks[position.symbol].price,
                asof=end) for position in endpoint.positions))
            accounts = (endpoint,)
        capture_sha = content_digest((collection.manifest_sha256, collection.bundle.accounts, accounts))
        if retained_coverage is None:
            proof = verify_coverage(path, account_capture_sha256=capture_sha,
                                    verifier=coverage_verifier, now=now)
        else:
            # Audit replay checks an EXISTING external claim's binding. It does
            # not call a verifier, issue a new proof or refresh verified_at.
            _require(coverage_verifier is None and type(retained_coverage) is VerifiedCoverage,
                     "ACCOUNT_INTERVAL_REPLAY_CLAIM_REQUIRED")
            from execution_accounts.collector import digest
            request = CoverageRequest(path_sha256=content_digest(path), account_capture_sha256=capture_sha,
                account_scope=path.account_scope, stream_epoch=path.stream_epoch, start=path.start, end=path.end,
                first_sequence=path.first_sequence, watermark_sequence=path.watermark_sequence)
            digest(retained_coverage.authority_sha256); digest(retained_coverage.source_proof_sha256)
            instant(retained_coverage.verified_at)
            _require(retained_coverage.request_sha256 == content_digest(request)
                     and retained_coverage.contract == COVERAGE_CONTRACT,
                     "CONTINUOUS_COVERAGE_BINDING_MISMATCH")
            _require(path.watermark_received_at <= retained_coverage.verified_at <= now
                     and now-path.end <= MAX_DURATION, "CONTINUOUS_COVERAGE_STALE_OR_FUTURE")
            proof = retained_coverage
        _require(proof.verified_at >= observed, "ACCOUNT_INTERVAL_COVERAGE_BEFORE_CAPTURE")
        interval = BaselineInterval(account_scope=previous.account_scope, sequence=previous.sequence+1,
            previous_state_digest=previous.state_digest, start=previous.asof, end=end,
            equity_krw=valuation.equity_krw, minimum_equity_krw=valuation.minimum_equity_krw,
            maximum_equity_krw=valuation.maximum_equity_krw, realized_net_total_krw=valuation.realized_net_total_krw,
            gross_external_inflows_krw=_ZERO, gross_external_outflows_krw=_ZERO,
            source_sha256=content_digest(accounts), coverage_sha256=content_digest((path, proof)))
        # Includes midnight/cutoff, all FIFO counters and account-mark reconciliation.
        advance_account_baseline(previous, interval, accounts, now=now)
        return ContinuousIntervalPreview(interval=interval, accounts=accounts, path=path,
                                         coverage=proof, valuation=valuation)
    except (AccountIntervalError, ContinuousEvidenceError, EvidenceError, BaselineError):
        raise
    except (ValueError, TypeError, AttributeError, KeyError, IndexError, DecimalException, OverflowError):
        raise AccountIntervalError("ACCOUNT_INTERVAL_CONTINUOUS_EVIDENCE_REFUSED") from None


class ContinuousUpbitCandidateSource:
    """Candidate capture only; cannot serve ContinuousAccountProvider or live trading.

    ``path_source(previous, capture, end)`` must return a candidate from an
    already-running continuous recorder. ``coverage_verifier(request, path)``
    independently authenticates the source contract. Both are trusted reviewed
    code dependencies; neither is loaded from a user JSON field. A class check
    alone must never enable controlled execution. The shipped production source
    remains flat-only until a venue completeness adapter has been established.
    """
    def __init__(self, *, path_source, coverage_verifier, archive_root: Path):
        _require(callable(path_source) and callable(coverage_verifier),
                 "ACCOUNT_INTERVAL_CONTINUOUS_INTEGRATIONS_REQUIRED")
        self._lock, self._staged = Lock(), None
        self._path_source, self._coverage_verifier = path_source, coverage_verifier
        _require(isinstance(archive_root, Path) and archive_root.is_absolute(),
                 "ACCOUNT_INTERVAL_CONTINUOUS_ARCHIVE_REQUIRED")
        self._archive_root = archive_root

    def collect(self, collector_source, *, previous: BaselineState, anchor: OpeningAnchor,
                coverage: CoverageEvidence, clock, trade_fees: tuple[TradeFeeEvidence, ...] = ()) -> StagedContinuousCandidate:
        with self._lock:
            self._staged = None
        try:
            _require(type(previous) is BaselineState and callable(clock) and type(trade_fees) is tuple,
                     "ACCOUNT_INTERVAL_INPUT_REQUIRED")
            _require(getattr(collector_source, "account_scope", None) == previous.account_scope,
                     "ACCOUNT_INTERVAL_SCOPE_MISMATCH")
            from execution_launch.guard_capture_material import (
                _snapshot_inputs, _retain_capture, _admit_tree, _admit_preview)
            _admit_tree(previous)
            exported = risk_baseline(previous, now=previous.asof, expected_head=previous.state_digest)
            previous = deepcopy(previous)
            started = instant(clock())
            boundary, midnight = _pending_boundary(previous)
            _require(started <= boundary, "ACCOUNT_INTERVAL_BOUNDARY_MISSED")
            in_window = boundary-started <= timedelta(seconds=BOUNDARY_LEAD_SECONDS)
            # Collector self-check only; no opening baseline is published. The
            # bridge subsequently derives the true midnight opening from the path.
            baseline = _opening_collection_baseline(previous, boundary) if in_window and midnight else exported
            anchor, coverage, trade_fees = _snapshot_inputs(anchor, coverage, trade_fees)
            baseline_sha = content_digest(baseline)
            collection_times = []
            def capture_clock():
                _require(len(collection_times) < 2, "ACCOUNT_INTERVAL_COLLECTION_CLOCK_INVALID")
                value = clock()
                instant(value)
                collection_times.append(value)
                return value
            collection = collect_upbit(collector_source, anchor=anchor, coverage=coverage, risk_baseline=baseline,
                                       clock=capture_clock, trade_fees=trade_fees)
            _require(len(collection_times) == 2, "ACCOUNT_INTERVAL_COLLECTION_CLOCK_INVALID")
            capture = _retain_capture(collection)
            observed = capture.observed_at
            end = min(observed, boundary)
            # Trusted integrations receive detached data, not aliases of the
            # original evidence retained for later exact collector replay.
            path = self._path_source(deepcopy(previous), deepcopy(capture), end)
            now = instant(clock())
            preview = preview_continuous_upbit_interval(previous, collection, path,
                                                    coverage_verifier=self._coverage_verifier, now=now)
            _require(not in_window or preview.interval.end == boundary, "ACCOUNT_INTERVAL_BOUNDARY_NOT_BRACKETED")
            _admit_preview(preview)
            _admit_tree(preview)
            candidate_sha = archive_candidate(path, root=self._archive_root)
            staged = StagedContinuousCandidate(preview=deepcopy(preview), path_sha256=candidate_sha,
                manifest_sha256=collection.manifest_sha256, observed_at=now, capture=capture,
                anchor=anchor, collection_coverage=coverage, trade_fees=trade_fees,
                collection_requested_at=started, collection_clock=tuple(collection_times),
                collection_baseline_sha256=baseline_sha)
        except (AccountIntervalError, ContinuousEvidenceError, EvidenceError, BaselineError):
            raise
        except Exception:
            raise AccountIntervalError("ACCOUNT_INTERVAL_CONTINUOUS_COLLECTION_FAILED") from None
        with self._lock:
            self._staged = staged
        return staged

    def latest(self):
        """The last audit candidate, never an account-provider frame."""
        with self._lock:
            _require(self._staged is not None, "ACCOUNT_INTERVAL_PREFETCH_REQUIRED")
            return self._staged

    def __call__(self, previous, now):
        raise AccountIntervalError("CONTINUOUS_LIVE_RISK_INTEGRATION_REQUIRED")
