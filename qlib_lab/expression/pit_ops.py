"""Bitemporal Point-in-Time (PIT) Engine & Operators (PIT, PRef, PITYoY, PITMoM, D1, D2, D3/Q1).

Integrates directly with core.ficc.pit (PITStore, yoy, mom, VALUE_STATUS_RANK) and enforces:
- known_at = max(available_at / received_at, retrieved_at / receipt_at) <= as_of;
- obs_date / release_date NEVER used as known_at;
- calendar-aware monthly offsets (never positional index shifts across missing months);
- D1 first-ever (source_id, item_id, payload_hash) receipt detection with heartbeat check;
- D2 96/672 15-min slot volume ratio where missing heartbeat slots yield NaN (never 0);
- D3/Q1 pinned model_version + prompt_sha256 filter with retroactive backfill rejection.
"""
from __future__ import annotations

import bisect
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
import math
from typing import Any, Mapping, Sequence

import numpy as np

from core.ficc import pit as core_pit
from qlib_lab.exceptions import CausalLagViolationError, LookAheadSyntaxError
from qlib_lab.expression.ast_nodes import EvalContext, ExprNode, PITSeriesRefNode
from qlib_lab.expression.ops import OperatorNode


def _to_utc_dt(value: Any) -> datetime:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            raise ValueError(f"Naive datetime refused in PIT engine: {value!r}")
        return value.astimezone(timezone.utc)
    if isinstance(value, (int, float, np.integer, np.floating)):
        return datetime.fromtimestamp(float(value), tz=timezone.utc)
    if isinstance(value, str):
        text = value[:-1] + "+00:00" if value.endswith("Z") else value
        dt = datetime.fromisoformat(text)
        if dt.tzinfo is None:
            raise ValueError(f"Naive timestamp string refused in PIT engine: {value!r}")
        return dt.astimezone(timezone.utc)
    raise ValueError(f"Unsupported UTC timestamp: {value!r}")


def _to_date(value: Any) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        return date.fromisoformat(value[:10])
    raise ValueError(f"Unsupported obs_date: {value!r}")


@dataclass(frozen=True)
class DIDMEventRecord:
    """Bitemporal event item for D1 (PITNewEventFlag)."""

    source_id: str
    item_id: str
    payload_sha256: str
    received_at_utc: datetime
    value: float = 1.0


@dataclass(frozen=True)
class SlotObservation:
    """15-minute slot item count & fetch heartbeat for D2 (PITSlotRatio)."""

    slot_end_utc: datetime
    item_count: int
    fetched_at_utc: datetime


@dataclass(frozen=True)
class PinnedScoreRecord:
    """Bitemporal LLM/V0 score or judgment record for D3/Q1 (PITPinnedScoreMean)."""

    record_id: str
    score: float
    received_at_utc: datetime
    receipt_at_utc: datetime
    model_version: str
    prompt_sha256: str
    event_type: str = "default"
    retroactive: bool = False

    @property
    def known_at_utc(self) -> datetime:
        return max(self.received_at_utc, self.receipt_at_utc)


@dataclass
class BitemporalPITProvider:
    """Unified bitemporal provider bridging core.ficc.pit.PITStore and D1/D2/D3/Q1 event feeds."""

    pit_store: core_pit.PITStore | None = None
    registry: Any = None
    # Custom in-memory bitemporal series rows: {series_id: [dict(obs_date, value, available_at_utc, retrieved_at_utc, ...)]}
    custom_series: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    # D1 event streams: {series_id: [DIDMEventRecord, ...]}
    event_streams: dict[str, list[DIDMEventRecord]] = field(default_factory=dict)
    # Source/delivery heartbeat status intervals or callable/log: {series_id: [(as_of_start_epoch, as_of_end_epoch, ok_bool)]}
    # Or explicit set/list of healthy run timestamps with max_cadence_seconds: {series_id: (sorted_run_epochs, cadence_sec)}
    source_heartbeats: dict[str, tuple[list[float], float]] = field(default_factory=dict)
    # D2 slot logs: {series_id: [SlotObservation, ...]}
    slot_streams: dict[str, list[SlotObservation]] = field(default_factory=dict)
    # D3/Q1 score logs: {series_id: [PinnedScoreRecord, ...]}
    score_streams: dict[str, list[PinnedScoreRecord]] = field(default_factory=dict)
    # Diagnostic counters
    diagnostics: dict[str, int] = field(default_factory=dict)

    def add_series_row(
        self,
        series_id: str,
        obs_date: date | str,
        value: float,
        *,
        available_at_utc: Any,
        retrieved_at_utc: Any,
        value_status: str = "first_release",
        source: str = "PIT",
        vintage: date | str | None = None,
    ) -> None:
        avail = _to_utc_dt(available_at_utc)
        retr = _to_utc_dt(retrieved_at_utc)
        od = _to_date(obs_date)
        vint = _to_date(vintage) if vintage is not None else None
        if value_status not in core_pit.VALUE_STATUS_RANK:
            raise ValueError(f"Unknown value_status {value_status!r}")
        self.custom_series.setdefault(series_id, []).append(
            {
                "series_id": series_id,
                "obs_date": od,
                "value": float(value),
                "available_at_utc": avail,
                "retrieved_at_utc": retr,
                "value_status": value_status,
                "source": source,
                "vintage": vint,
            }
        )

    def register_heartbeat(self, series_id: str, run_timestamps_utc: Sequence[Any], max_stale_seconds: float) -> None:
        epochs = sorted(_to_utc_dt(t).timestamp() for t in run_timestamps_utc)
        self.source_heartbeats[series_id] = (epochs, float(max_stale_seconds))

    def is_heartbeat_healthy(self, series_id: str, as_of_epoch: float) -> bool:
        hb = self.source_heartbeats.get(series_id)
        if hb is None:
            return True
        epochs, max_stale = hb
        idx = bisect.bisect_right(epochs, as_of_epoch) - 1
        if idx < 0:
            return False
        return (as_of_epoch - epochs[idx]) <= max_stale + 1e-9

    def visible_series_rows(self, series_id: str, as_of_dt: datetime) -> dict[date, dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        if self.pit_store is not None and series_id in self.pit_store.series_ids():
            rows.extend(self.pit_store.rows(series_id))
        if series_id in self.custom_series:
            rows.extend(self.custom_series[series_id])
        vis = [r for r in rows if r["available_at_utc"] <= as_of_dt and r["retrieved_at_utc"] <= as_of_dt]
        if not vis:
            return {}
        precedence = ()
        if self.registry is not None and hasattr(self.registry, "series") and series_id in self.registry.series:
            precedence = tuple(self.registry.series[series_id].get("sources") or ())
        return core_pit._best_per_obs(vis, precedence)


def _require_provider(ctx: EvalContext) -> BitemporalPITProvider:
    prov = ctx.pit_provider
    if prov is None:
        raise ValueError("PIT expression requires a BitemporalPITProvider or PITStore on EvalContext")
    if isinstance(prov, core_pit.PITStore):
        wrapped = BitemporalPITProvider(pit_store=prov)
        ctx.pit_provider = wrapped
        return wrapped
    if isinstance(prov, BitemporalPITProvider):
        return prov
    raise TypeError(f"Unsupported pit_provider type: {type(prov).__name__}")


def _extract_series_id(arg: ExprNode | str) -> str:
    if isinstance(arg, PITSeriesRefNode):
        return arg.series_id
    if isinstance(arg, str):
        return arg[2:] if arg.startswith("$$") else arg
    raise TypeError(f"PIT operator expects a $$series reference, got {arg!r}")


def evaluate_pit_collapse(series_id: str, ctx: EvalContext, period_offset: int = 0) -> np.ndarray:
    if period_offset < 0:
        raise LookAheadSyntaxError(f"PRef($${series_id}, {period_offset}) cannot reference future periods")
    prov = _require_provider(ctx)
    col = np.full(ctx.T, np.nan, dtype=np.float64)
    for t in range(ctx.T):
        as_of_dt = ctx.datetimes_utc[t].to_pydatetime()
        if not prov.is_heartbeat_healthy(series_id, ctx.as_of_epochs[t]):
            continue
        best = prov.visible_series_rows(series_id, as_of_dt)
        if len(best) <= period_offset:
            continue
        ordered_dates = sorted(best.keys())
        chosen_date = ordered_dates[-1 - period_offset]
        col[t] = float(best[chosen_date]["value"])
    return np.repeat(col[:, None], ctx.N, axis=1)


class PIT(OperatorNode):
    """Collapse bitemporal $$series onto the bar grid as of each bar's UTC timestamp."""

    op_name = "PIT"

    def __init__(self, series_ref: PITSeriesRefNode | str) -> None:
        sid = _extract_series_id(series_ref)
        self.series_id = sid
        super().__init__((), (sid,))

    def compute(self, child_values: Sequence[np.ndarray], ctx: EvalContext) -> np.ndarray:
        _ = child_values
        return evaluate_pit_collapse(self.series_id, ctx, period_offset=0)


class PRef(OperatorNode):
    """Reference k-th prior period of bitemporal $$series visible at as_of (k >= 0 strictly)."""

    op_name = "PRef"

    def __init__(self, series_ref: PITSeriesRefNode | str, k: int = 0) -> None:
        if isinstance(k, bool) or not isinstance(k, int):
            raise ValueError(f"PRef offset k must be an integer, got {k!r}")
        if k < 0:
            raise LookAheadSyntaxError(
                f"PRef(..., {k}) references a future period; strictly forbidden in bitemporal PIT"
            )
        self.series_id = _extract_series_id(series_ref)
        self.k = int(k)
        super().__init__((), (self.series_id, self.k))

    def compute(self, child_values: Sequence[np.ndarray], ctx: EvalContext) -> np.ndarray:
        _ = child_values
        return evaluate_pit_collapse(self.series_id, ctx, period_offset=self.k)


class _PITCalendarChangeOp(OperatorNode):
    months_back: int = 12

    def __init__(self, series_ref: PITSeriesRefNode | str, kind: str = "pct") -> None:
        if kind not in ("pct", "diff"):
            raise ValueError("kind must be 'pct' or 'diff'")
        self.series_id = _extract_series_id(series_ref)
        self.kind = kind
        super().__init__((), (self.series_id, self.kind))

    def compute(self, child_values: Sequence[np.ndarray], ctx: EvalContext) -> np.ndarray:
        _ = child_values
        prov = _require_provider(ctx)
        col = np.full(ctx.T, np.nan, dtype=np.float64)
        for t in range(ctx.T):
            as_of_dt = ctx.datetimes_utc[t].to_pydatetime()
            if not prov.is_heartbeat_healthy(self.series_id, ctx.as_of_epochs[t]):
                continue
            best = prov.visible_series_rows(self.series_id, as_of_dt)
            if not best:
                continue
            monthly_map: dict[date, float] = {}
            # Collapse to month_start; if multiple dates in same month, latest obs_date wins
            for obs_d in sorted(best.keys()):
                monthly_map[core_pit.month_start(obs_d)] = float(best[obs_d]["value"])
            latest_month = max(monthly_map.keys())
            mv = core_pit.calendar_change(monthly_map, latest_month, self.months_back, kind=self.kind)
            if not mv.flagged and math.isfinite(mv.value):
                col[t] = float(mv.value)
        return np.repeat(col[:, None], ctx.N, axis=1)


class PITYoY(_PITCalendarChangeOp):
    """Calendar-aware 12-month YoY change via core.ficc.pit.calendar_change (missing endpoint -> NaN)."""

    op_name = "PITYoY"
    months_back = 12


class PITMoM(_PITCalendarChangeOp):
    """Calendar-aware 1-month MoM change via core.ficc.pit.calendar_change (missing endpoint -> NaN)."""

    op_name = "PITMoM"
    months_back = 1


class PITNewEventFlag(OperatorNode):
    """D1: 1.0 if a new item or changed payload had its FIRST-EVER receipt within (as_of - window_hours, as_of].

    Re-fetching an unchanged vintage/payload with a fresher received_at does NOT fire D1.
    Missing scheduled source heartbeat yields NaN (never imputed to 0).
    """

    op_name = "PITNewEventFlag"

    def __init__(self, series_ref: PITSeriesRefNode | str, window_hours: float = 24.0) -> None:
        if float(window_hours) <= 0:
            raise ValueError("window_hours must be > 0")
        self.series_id = _extract_series_id(series_ref)
        self.window_hours = float(window_hours)
        super().__init__((), (self.series_id, self.window_hours))

    def compute(self, child_values: Sequence[np.ndarray], ctx: EvalContext) -> np.ndarray:
        _ = child_values
        prov = _require_provider(ctx)
        win_sec = self.window_hours * 3600.0

        # Collect first-ever receipt timestamps per distinct (source_id, item_id, payload_hash)
        first_seen: dict[tuple[str, str, str], float] = {}
        if self.series_id in prov.event_streams:
            for ev in prov.event_streams[self.series_id]:
                key = (ev.source_id, ev.item_id, ev.payload_sha256)
                ts = _to_utc_dt(ev.received_at_utc).timestamp()
                if key not in first_seen or ts < first_seen[key]:
                    first_seen[key] = ts
        else:
            # Also support PITStore / custom_series rows deduplicated by (source, obs_date, vintage, value)
            rows: list[dict[str, Any]] = []
            if prov.pit_store is not None and self.series_id in prov.pit_store.series_ids():
                rows.extend(prov.pit_store.rows(self.series_id))
            if self.series_id in prov.custom_series:
                rows.extend(prov.custom_series[self.series_id])
            for r in rows:
                known_ts = max(r["available_at_utc"], r["retrieved_at_utc"]).timestamp()
                payload_key = f"{r.get('vintage')}:{r.get('value')}:{r.get('value_status')}"
                key = (str(r.get("source", "")), str(r["obs_date"]), payload_key)
                if key not in first_seen or known_ts < first_seen[key]:
                    first_seen[key] = known_ts

        sorted_first_epochs = sorted(first_seen.values())
        col = np.full(ctx.T, np.nan, dtype=np.float64)
        for t in range(ctx.T):
            as_of_ep = ctx.as_of_epochs[t]
            if not prov.is_heartbeat_healthy(self.series_id, as_of_ep):
                continue
            lo = bisect.bisect_right(sorted_first_epochs, as_of_ep - win_sec)
            hi = bisect.bisect_right(sorted_first_epochs, as_of_ep)
            col[t] = 1.0 if hi > lo else 0.0
        return np.repeat(col[:, None], ctx.N, axis=1)


class PITSlotRatio(OperatorNode):
    """D2: GDELT 96-slot (24h) / 672-slot (7d) volume ratio with strict heartbeat-gap NaN semantics.

    Numerator requires ALL `num_slots` (default 96) slots fetched at or before `as_of`.
    Denominator requires at least `min_den_coverage` (default 0.95) of `den_slots` (default 672) slots fetched.
    A slot missing from the run log is missing (NaN), NEVER zero.
    """

    op_name = "PITSlotRatio"

    def __init__(
        self,
        series_ref: PITSeriesRefNode | str,
        num_slots: int = 96,
        den_slots: int = 672,
        slot_seconds: int = 900,
        min_den_coverage: float = 0.95,
    ) -> None:
        if num_slots < 1 or den_slots < num_slots or slot_seconds < 1:
            raise ValueError("Invalid slot configuration for PITSlotRatio")
        if not (0.0 < float(min_den_coverage) <= 1.0):
            raise ValueError("min_den_coverage must lie in (0, 1]")
        self.series_id = _extract_series_id(series_ref)
        self.num_slots = int(num_slots)
        self.den_slots = int(den_slots)
        self.slot_seconds = int(slot_seconds)
        self.min_den_coverage = float(min_den_coverage)
        super().__init__((), (self.series_id, self.num_slots, self.den_slots, self.slot_seconds, self.min_den_coverage))

    def compute(self, child_values: Sequence[np.ndarray], ctx: EvalContext) -> np.ndarray:
        _ = child_values
        prov = _require_provider(ctx)
        slots = prov.slot_streams.get(self.series_id, [])

        # Map slot_end_epoch -> earliest fetched_at and corresponding count
        slot_map: dict[int, tuple[float, int]] = {}
        for obs in slots:
            se = int(round(_to_utc_dt(obs.slot_end_utc).timestamp()))
            fa = _to_utc_dt(obs.fetched_at_utc).timestamp()
            cur = slot_map.get(se)
            if cur is None or fa < cur[0]:
                slot_map[se] = (fa, int(obs.item_count))

        min_den_needed = int(math.ceil(self.min_den_coverage * self.den_slots))
        step = self.slot_seconds
        col = np.full(ctx.T, np.nan, dtype=np.float64)

        for t in range(ctx.T):
            as_of_ep = ctx.as_of_epochs[t]
            anchor = int(math.floor(as_of_ep / step) * step)
            num_sum = 0.0
            num_present = 0
            den_sum = 0.0
            den_present = 0

            missing_num = False
            for k in range(self.den_slots):
                slot_end = anchor - k * step
                rec = slot_map.get(slot_end)
                if rec is not None and rec[0] <= as_of_ep:
                    cnt = float(rec[1])
                    den_present += 1
                    den_sum += cnt
                    if k < self.num_slots:
                        num_present += 1
                        num_sum += cnt
                else:
                    if k < self.num_slots:
                        missing_num = True
                        break

            if missing_num or num_present < self.num_slots or den_present < min_den_needed:
                continue
            den_mean_per_num = (den_sum / float(den_present)) * float(self.num_slots)
            if den_mean_per_num <= 1e-15:
                continue
            col[t] = num_sum / den_mean_per_num

        return np.repeat(col[:, None], ctx.N, axis=1)


class PITPinnedScoreMean(OperatorNode):
    """D3/Q1: Pinned (model_version, prompt_sha256) score mean or risk-judgment flag over trailing window_hours.

    Enforces known_at = max(received_at, receipt_at) <= as_of, rejects retroactive=True records,
    and ignores unpinned model/prompt versions while counting them in provider.diagnostics.
    mode: 'mean' (D3 score average) or 'flag' (Q1 binary 0/1 risk judgment presence).
    """

    op_name = "PITPinnedScoreMean"

    def __init__(
        self,
        series_ref: PITSeriesRefNode | str,
        window_hours: float = 24.0,
        model_version: str = "",
        prompt_sha256: str = "",
        mode: str = "mean",
        empty_value: float = float("nan"),
    ) -> None:
        if not model_version or not prompt_sha256:
            raise ValueError("PITPinnedScoreMean requires explicit pinned model_version and prompt_sha256")
        if mode not in ("mean", "flag"):
            raise ValueError("mode must be 'mean' or 'flag'")
        self.series_id = _extract_series_id(series_ref)
        self.window_hours = float(window_hours)
        self.model_version = str(model_version)
        self.prompt_sha256 = str(prompt_sha256)
        self.mode = mode
        self.empty_value = 0.0 if mode == "flag" and math.isnan(float(empty_value)) else float(empty_value)
        super().__init__(
            (),
            (self.series_id, self.window_hours, self.model_version, self.prompt_sha256, self.mode, self.empty_value),
        )

    def compute(self, child_values: Sequence[np.ndarray], ctx: EvalContext) -> np.ndarray:
        _ = child_values
        prov = _require_provider(ctx)
        records = prov.score_streams.get(self.series_id, [])
        win_sec = self.window_hours * 3600.0

        pinned_items: list[tuple[float, float]] = []
        unpinned_count = 0
        for rec in records:
            if rec.retroactive:
                raise CausalLagViolationError(
                    f"Retroactive score record {rec.record_id!r} in $${self.series_id} is forbidden (no retroactive data)"
                )
            if rec.model_version != self.model_version or rec.prompt_sha256 != self.prompt_sha256:
                unpinned_count += 1
                continue
            known_ep = rec.known_at_utc.timestamp()
            pinned_items.append((known_ep, float(rec.score)))

        prov.diagnostics[f"{self.series_id}_ignored_unpinned"] = unpinned_count
        pinned_items.sort(key=lambda pair: pair[0])
        known_epochs = [p[0] for p in pinned_items]
        scores = [p[1] for p in pinned_items]

        col = np.full(ctx.T, np.nan, dtype=np.float64)
        for t in range(ctx.T):
            as_of_ep = ctx.as_of_epochs[t]
            if not prov.is_heartbeat_healthy(self.series_id, as_of_ep):
                continue
            lo = bisect.bisect_right(known_epochs, as_of_ep - win_sec)
            hi = bisect.bisect_right(known_epochs, as_of_ep)
            if hi <= lo:
                col[t] = self.empty_value
            elif self.mode == "flag":
                col[t] = 1.0 if any(s > 0.0 for s in scores[lo:hi]) else 0.0
            else:
                col[t] = float(math.fsum(scores[lo:hi]) / float(hi - lo))
        return np.repeat(col[:, None], ctx.N, axis=1)
