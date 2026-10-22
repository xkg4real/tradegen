"""Independent lag audit and the positional-shift linter (M1; R-01 rules (1) and (6); R-20 rule 3; section 3.9
`macro.lag_audit`; T-LAG-01, T-LAG-02, T-CLOSE-01 quarantine clauses).

`lag_audit(inputs, ctx, market, registry, clocks)` recomputes, for every acting and risk-model input and
independently of `pit_value`, the first instant the datum may be used from the calendars and the registry, and
records `{checked, violations[]}` in the `macro_state.lag_audit` shape. It refuses a raw-frame read (anything that
is not a `PITValue`): every acting read goes through the store. In a backtest a violation raises `LookAheadError`;
at runtime the caller HALTs (OPS) the books the input feeds (`violation.books`, operator re-arm).

`assert_no_positional_shift(dates, offset)` rejects a positional `shift` on a series with gaps (T-LAG-02).
# integration: core.calendars.clocks (close_print_bound_utc, publication_instant)
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta

from core.ficc.contracts import CROSS_MARKET_BUFFER_S, Registry, pit, usable_cross_market
from core.ficc.pit import PITValue, RunContext, iso_utc

AUDITED_ROLES = ("acting_exposure", "risk_model", "forward_sim")


class LookAheadError(Exception):
    """A datum reached an acting input before it could be known (or a raw frame bypassed the store)."""


class RawFrameRead(LookAheadError):
    """An acting input was handed a raw frame/array instead of PITValue records (L1105-1106)."""


class PositionalShiftRejected(ValueError):
    """A positional shift on a series with calendar gaps (section 10 item 19)."""


@dataclass(frozen=True)
class Violation:
    series_id: str
    obs_date: date
    check: str
    expected_usable_at_utc: datetime
    stamped_available_at_utc: datetime
    books: tuple[str, ...] = ()

    def record(self) -> dict:
        return {"series_id": self.series_id, "obs_date": self.obs_date.isoformat(), "check": self.check,
                "expected_usable_at_utc": iso_utc(self.expected_usable_at_utc),
                "stamped_available_at_utc": iso_utc(self.stamped_available_at_utc)}


def usable_at(registry: Registry, series_id: str, obs_date: date, clocks) -> datetime | None:
    """The earliest instant a datum dated obs_date may be read, from the calendars and the registry alone:
    closes -> close_print_bound_utc(market, obs_date); published series -> publication_instant; live quotes and
    as-posted series -> None (their stamp is the bound)."""
    s = registry.series[series_id]
    if s["obs_kind"] == "close":
        return clocks.close_print_bound_utc(registry.market(series_id), obs_date)
    if s["schedule"] in ("LIVE_QUOTE", "AS_POSTED", "DERIVED"):
        return None
    return clocks.publication_instant(series_id, obs_date)


def _audit_one(v: PITValue, ctx: RunContext, registry: Registry, clocks, lineage, market: str) -> list[Violation]:
    out = []
    if v.available_at_utc > ctx.decision_utc:
        out.append(Violation(v.series_id, v.obs_date, "available_at_utc <= decision_utc", ctx.decision_utc,
                             v.available_at_utc, v.books))
    if v.retrieved_at_utc > ctx.knowledge_utc:
        out.append(Violation(v.series_id, v.obs_date, "retrieved_at_utc <= knowledge_utc", ctx.knowledge_utc,
                             v.retrieved_at_utc, v.books))
    if registry.is_series(v.series_id):
        if v.obs_kind == "derived":
            for inp in lineage.get(v.content_hash, ()):
                out += _audit_one(inp, ctx, registry, clocks, lineage, market)
        else:
            bound = usable_at(registry, v.series_id, v.obs_date, clocks)
            if bound is not None:
                if bound > ctx.decision_utc:
                    out.append(Violation(v.series_id, v.obs_date, "usable_at <= decision_utc", bound,
                                         v.available_at_utc, v.books))
                if v.available_at_utc < bound and v.available_at_source != "published":
                    out.append(Violation(v.series_id, v.obs_date, "available_at_utc >= publication_instant", bound,
                                         v.available_at_utc, v.books))
            other = registry.market(v.series_id)
            if registry.obs_kind(v.series_id) == "close" and other not in (None, market):
                # R-19 rule 6: another market's close needs bound(other, D) + 60 s < decision; a same-date HK close never
                if not usable_cross_market(other, v.obs_date, ctx.decision_utc, clocks) or (
                        other == "HK" and v.obs_date >= ctx.decision_utc.date()):
                    xb = clocks.close_print_bound_utc(other, v.obs_date) + timedelta(seconds=CROSS_MARKET_BUFFER_S)
                    out.append(Violation(v.series_id, v.obs_date, "cross-market bound + 60 s < decision_utc", xb,
                                         v.available_at_utc, v.books))
        if v.role == "acting_exposure" and (registry.obs_kind(v.series_id) == "close" or v.obs_kind == "close"):
            if v.value_status != "official_close" and not (ctx.run_mode == "backtest" and v.value_status == "vendor_close"):
                out.append(Violation(v.series_id, v.obs_date, "value_status == official_close",
                                     v.available_at_utc, v.available_at_utc, v.books))
            if v.session_date != v.obs_date:
                out.append(Violation(v.series_id, v.obs_date, "session_date == decided session",
                                     v.available_at_utc, v.available_at_utc, v.books))
            q = clocks.close_print_bound_utc(registry.market(v.series_id), v.obs_date) + timedelta(minutes=pit.QUARANTINE_MINUTES)
            if v.retrieved_at_utc < q and v.value_status in pit.CLOSE_STATUSES:
                out.append(Violation(v.series_id, v.obs_date, "retrieved_at_utc >= close + 10 min", q,
                                     v.retrieved_at_utc, v.books))
    return out


def lag_audit(inputs, ctx: RunContext, market: str, registry: Registry, clocks, *, lineage: dict | None = None) -> dict:
    """Audit every acting / risk-model / forward-sim input (context skipped). Returns
    `{"checked": n, "violations": [...], "books": [...]}`; raises LookAheadError in a backtest."""
    lineage = lineage or {}
    checked, violations = 0, []
    for v in inputs:
        if not isinstance(v, PITValue):
            raise RawFrameRead(f"{market}: acting input of type {type(v).__name__} did not come from the store")
        if v.role not in AUDITED_ROLES:
            continue
        checked += 1
        violations += _audit_one(v, ctx, registry, clocks, lineage, market)
    books = sorted({b for x in violations for b in x.books})
    if violations and ctx.run_mode == "backtest":
        first = violations[0]
        raise LookAheadError(f"{first.series_id} {first.obs_date}: {first.check} (expected "
                             f"{iso_utc(first.expected_usable_at_utc)}, stamped {iso_utc(first.stamped_available_at_utc)})")
    return {"checked": checked, "violations": [x.record() for x in violations], "books": books}


def assert_no_positional_shift(dates, offset: int, *, expected_step: timedelta | None = None) -> None:
    """A positional shift of `offset` observations is only a calendar shift when the series has no gaps; with a
    gap it is rejected (monthly series with a missing month, daily series across holidays beyond `expected_step`)."""
    ds = sorted(dates)
    if offset == 0 or len(ds) < 2:
        return
    gaps = []
    for a, b in zip(ds, ds[1:]):
        if expected_step is None:
            if pit.add_months(a, 1) != pit.month_start(b):
                gaps.append((a, b))
        elif b - a != expected_step:
            gaps.append((a, b))
    if gaps:
        raise PositionalShiftRejected(f"positional shift of {offset} on a series with {len(gaps)} gap(s), first "
                                      f"{gaps[0][0]} -> {gaps[0][1]}: use a calendar offset")


__all__ = [n for n in dir() if not n.startswith("_")]
