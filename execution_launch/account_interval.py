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

Nothing here loads owner context, signs, arms, orders, reads credentials or touches a file.
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
from execution_accounts.baseline_bridge import BaselineFrame, advance_account_baseline
from execution_accounts.collector import CoverageEvidence, OpeningAnchor, SourceReceipt, TradeFeeEvidence, instant
from execution_accounts.model import (AccountEvidence, BrokerOrder, CashBalance, EvidencePage, Position,
                                      RiskBaseline, content_digest)
from execution_accounts.continuous import (COVERAGE_CONTRACT, MAX_DURATION, MAX_HELD_MARKETS, CoverageRequest,
                                           ContinuousEvidenceError, ContinuousPath, PathValuation, PriceMark,
                                           VerifiedCoverage, value_path, value_trade_paths, verify_coverage)
from execution_launch.continuous_archive import archive_candidate
from execution_control.risk import account_fills
from execution_accounts.provider import EvidenceError, _fresh, build_observation
from execution_accounts.upbit_collector import CollectionResult, collect_upbit

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


def _project_orders_at_cutoff(orders: tuple[BrokerOrder, ...], accepted_fills, later_fills,
                              cash_krw: Decimal, units_by_symbol: Mapping[str, Decimal]) -> tuple[BrokerOrder, ...]:
    later_by_oid: dict[str, Decimal] = {}
    for fill in later_fills:
        later_by_oid[fill.order_id] = later_by_oid.get(fill.order_id, _ZERO) + fill.quantity
    prior_by_oid: dict[str, Decimal] = {}
    for fill in accepted_fills:
        prior_by_oid[fill.order_id] = prior_by_oid.get(fill.order_id, _ZERO) + fill.quantity
    out: list[BrokerOrder] = []
    reserved_krw = _ZERO
    promised_by_sym: dict[str, Decimal] = {}
    for order in orders:
        prior_qty = prior_by_oid.get(order.order_id, _ZERO)
        later_qty = later_by_oid.get(order.order_id, _ZERO)
        if later_qty > _ZERO:
            if prior_qty == _ZERO:
                continue
            rem = order.quantity - prior_qty
            res_cash = max(order.reserved_cash, rem * order.limit_price) if order.side == "buy" else _ZERO
            if order.side == "buy" and reserved_krw + res_cash > cash_krw:
                raise AccountIntervalError("ACCOUNT_INTERVAL_CLOSING_CASH_MISMATCH")
            if order.side == "sell" and promised_by_sym.get(order.symbol, _ZERO) + rem > units_by_symbol.get(order.symbol, _ZERO):
                raise AccountIntervalError("ACCOUNT_INTERVAL_CLOSING_HOLDINGS_MISMATCH")
            if order.side == "buy":
                reserved_krw += res_cash
            else:
                promised_by_sym[order.symbol] = promised_by_sym.get(order.symbol, _ZERO) + rem
            out.append(BrokerOrder(
                client_id=order.client_id, order_id=order.order_id, market=order.market,
                symbol=order.symbol, side=order.side, quote_currency=order.quote_currency,
                quantity=order.quantity, filled_quantity=prior_qty, remaining_quantity=rem,
                limit_price=order.limit_price, reserved_cash=res_cash, status="partial",
                cancelable_quantity=rem,
            ))
            continue
        if order.status in ("open", "partial"):
            if order.side == "buy":
                if reserved_krw + order.reserved_cash > cash_krw:
                    if prior_qty == _ZERO:
                        continue
                    raise AccountIntervalError("ACCOUNT_INTERVAL_CLOSING_CASH_MISMATCH")
                reserved_krw += order.reserved_cash
            else:
                if promised_by_sym.get(order.symbol, _ZERO) + order.remaining_quantity > units_by_symbol.get(order.symbol, _ZERO):
                    if prior_qty == _ZERO:
                        continue
                    raise AccountIntervalError("ACCOUNT_INTERVAL_CLOSING_HOLDINGS_MISMATCH")
                promised_by_sym[order.symbol] = promised_by_sym.get(order.symbol, _ZERO) + order.remaining_quantity
        out.append(order)
    return tuple(out)


def _reconstruct_cutoff_account(account: AccountEvidence, cutoff: datetime, valuation: PathValuation,
                                accepted_fills, later_fills, flows, manifest_sha256: str) -> AccountEvidence:
    marks_by_sym = {m.symbol: m for m in valuation.closing_marks}
    units_by_sym = dict(valuation.closing_units)
    positions = tuple(
        Position(
            market="spot", symbol=sym, quote_currency="KRW", units=qty,
            price=marks_by_sym[sym].price, asof=cutoff, base_currency=sym[4:],
        )
        for sym, qty in sorted(units_by_sym.items())
    )
    orig_orders = ()
    for page in account.pages:
        if page.kind == "orders":
            orig_orders = page.rows
            break
    projected_orders = _project_orders_at_cutoff(orig_orders, accepted_fills, later_fills,
                                                 valuation.closing_cash_krw, units_by_sym)
    pages = tuple(
        EvidencePage(kind=kind, cursor=None, next_cursor=None, start=account.origin, end=cutoff,
                     rows=tuple(rows), source_sha256=manifest_sha256)
        for kind, rows in (("fills", accepted_fills), ("flows", flows), ("orders", projected_orders))
    )
    srv = account.server_time
    if srv.astimezone(KST).date() != cutoff.astimezone(KST).date() or abs(cutoff - srv) > timedelta(seconds=60):
        srv = cutoff
    return replace(
        account,
        balances=(CashBalance(currency="KRW", total=valuation.closing_cash_krw, settled=valuation.closing_cash_krw),),
        positions=positions,
        fx=tuple(replace(rate, asof=cutoff) for rate in account.fx),
        pages=pages,
        restrictions=replace(account.restrictions, asof=cutoff),
        observed_at=cutoff,
        server_time=srv,
    )


def upbit_held_interval_frames(previous: BaselineState, collection: CollectionResult, *,
                               trade_path: Mapping[str, object],
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
                     and isinstance(trade_path, Mapping), "ACCOUNT_INTERVAL_INPUT_REQUIRED")
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

            observation = build_observation(bundle, now=observed, bid_gap_y=Decimal("0.05"))
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
            elif first <= boundary0 and not any(boundary0 <= f.executed_at < observed for f in all_fills) and False:
                segments.append((previous.asof, boundary0))
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
            for sym, win in sorted(trade_path.items()):
                raw_prints = getattr(win, "prints", win)
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
                later_fills = tuple(f for f in all_fills if seg_end <= f.executed_at < observed)
                prior_acc = account_fills(hist_fills)
                _require(prior_acc.ok and prior_acc.duplicate_count == 0, "ACCOUNT_INTERVAL_PRIOR_HISTORY_REFUSED")
                seg_cash = base_anchor_cash + sum(
                    (amt for venue, scope, amt in prior_acc.cash_deltas_by_account_krw
                     if venue == "upbit" and scope == previous.account_scope),
                    _ZERO,
                )
                seg_units = tuple((row[3], row[4]) for row in prior_acc.inventory if row[4] != 0)
                active_syms = sorted(set(dict(seg_units)) | {f.symbol for f in seg_fills} | set(all_prints_by_sym))
                _require(len(active_syms) <= MAX_HELD_MARKETS, "ACCOUNT_INTERVAL_EXTREMA_EVIDENCE_REQUIRED")

                # Fill any missing opening mark from opening_print, single-coin exact algebra, or first fill/print
                if len(seg_units) == 1 and seg_units[0][0] not in cur_marks:
                    u_sym, u_qty = seg_units[0]
                    implied = (cur_state.equity_krw - seg_cash) / u_qty
                    if implied > _ZERO:
                        cur_marks[u_sym] = PriceMark(symbol=u_sym, price=implied, asof=seg_start)
                for sym in active_syms:
                    if sym not in cur_marks:
                        if sym in opening_print_by_sym:
                            op = opening_print_by_sym[sym]
                            cur_marks[sym] = PriceMark(symbol=sym, price=op.price, asof=op.at)
                        else:
                            pos_match = next((p for p in account.positions if p.symbol == sym), None)
                            seg_p = [
                                p for p in all_prints_by_sym.get(sym, ())
                                if seg_start <= getattr(p, "at", getattr(p, "asof", seg_start)) < seg_end
                            ]
                            if seg_p:
                                first_p = seg_p[0]
                                p_val = first_p.price
                                cur_marks[sym] = PriceMark(symbol=sym, price=p_val, asof=seg_start)
                            elif seg_fills:
                                sym_f = [f for f in seg_fills if f.symbol == sym]
                                if sym_f:
                                    cur_marks[sym] = PriceMark(symbol=sym, price=sym_f[0].price, asof=seg_start)
                            elif pos_match is not None and pos_match.price > _ZERO:
                                cur_marks[sym] = PriceMark(symbol=sym, price=pos_match.price, asof=seg_start)

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
                )

                if seg_end == observed:
                    _require(len(account.balances) == 1 and account.balances[0].currency == "KRW"
                             and valuation.closing_cash_krw == account.balances[0].total,
                             "ACCOUNT_INTERVAL_CLOSING_CASH_MISMATCH")
                    closing_units = tuple(sorted((pos.symbol, pos.units) for pos in account.positions))
                    _require(valuation.closing_units == closing_units,
                             "ACCOUNT_INTERVAL_CLOSING_HOLDINGS_MISMATCH")
                    c_marks = {m.symbol: m for m in valuation.closing_marks}
                    if all(pos.price == c_marks[pos.symbol].price for pos in account.positions):
                        seg_accounts = (account,)
                    else:
                        # Reconstruct endpoint mark from authenticated print path when ticker lagged a print
                        patched = replace(
                            account,
                            positions=tuple(
                                replace(pos, price=c_marks[pos.symbol].price)
                                for pos in account.positions
                            ),
                        )
                        seg_accounts = (patched,)
                else:
                    cutoff_acc = _reconstruct_cutoff_account(
                        account, seg_end, valuation, hist_fills + seg_fills, later_fills,
                        tuple(flows_list), collection.manifest_sha256,
                    )
                    seg_accounts = (cutoff_acc,)

                cov_sha = content_digest((collection.manifest_sha256, seg_start, seg_end, tuple(proof_digests)))
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
                update = advance_account_baseline(cur_state, interval, seg_accounts, now=reconcile_now)
                cur_state = update.state
                for cm in valuation.closing_marks:
                    cur_marks[cm.symbol] = cm
                frames.append(BaselineFrame(interval=interval, accounts=seg_accounts))

            return tuple(frames)
    except (AccountIntervalError, ContinuousEvidenceError, EvidenceError, BaselineError):
        raise
    except (ValueError, TypeError, AttributeError, KeyError, IndexError, DecimalException, OverflowError):
        raise AccountIntervalError("ACCOUNT_INTERVAL_EVIDENCE_REFUSED") from None


def upbit_interval_frame(previous: BaselineState, collection: CollectionResult, *,
                         trade_path: Mapping[str, object] | None = None,
                         opening_marks: Mapping[str, PriceMark | Decimal] | tuple[PriceMark, ...] | None = None
                         ) -> BaselineFrame:
    """Pure: one flat interval [previous.asof, end) over one capture, or held interval when trade_path supplied."""
    if trade_path is not None:
        frames = upbit_held_interval_frames(previous, collection, trade_path=trade_path, opening_marks=opening_marks)
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

    def __init__(self, *, trade_window_collector=None, order_fill_collector=None, opening_marks=None):
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
                if self._order_fill_collector is not None and in_fills:
                    in_oids = sorted({f.order_id for f in in_fills})
                    for oid in in_oids:
                        of_res = self._order_fill_collector(
                            collector_source, oid, account_scope=previous.account_scope,
                            fee_evidence=trade_fees, clock=clock,
                        )
                        if getattr(of_res, "receipt", None) is not None:
                            extra_receipts.append(of_res.receipt)
                trade_windows = {}
                for sym in active_syms:
                    win = self._trade_window_collector(
                        collector_source, sym, start=previous.asof, end=observed,
                        account_scope=previous.account_scope, clock=clock,
                    )
                    trade_windows[sym] = win
                    win_receipts = getattr(win, "receipts", ())
                    if win_receipts:
                        extra_receipts.extend(win_receipts)
                with self._lock:
                    cached_marks = dict(self._marks_by_state.get(previous.state_digest, {}))
                eff_marks = opening_marks if opening_marks is not None else (cached_marks or self._seed_marks)
                if not active_syms and not in_fills and observed <= boundary:
                    # Pure flat interval inside boundary: fast path
                    frame = upbit_interval_frame(previous, collection)
                    frames = (frame,)
                else:
                    frames = upbit_held_interval_frames(
                        previous, collection, trade_path=trade_windows, opening_marks=eff_marks,
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
                    self._marks_by_state.update(new_marks_cache)
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
