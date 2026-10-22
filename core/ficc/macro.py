"""Cross-asset macro sheet and its descriptive read — the inputs of the daily
commentary and the weekly rates/FX strategy note. CONTEXT only (v2.0, section
3.6; TASK-M6-01): the 18 indicators are context inputs, the z-scores are causal
display values, and the `Regime` read is a descriptive read — not a regime model
(P19): five threshold rules, no probabilities, no latent state, no smoothing. It
never uses the calm / normal / elevated / stressed names (those are R-06's
volatility labels) and never feeds core/quant/signals, core/quant/risk or the
engine (T-CTX-01).

`macro_sheet` loads a fixed indicator list (Treasuries, real/breakeven, policy
rates, IG/HY OAS, the dollar and majors, VIX, WTI, the 10y note future and
gold), turns each into a `MacroRow` (last, 1d/1w/1m/3m changes, 1y z-score and
percentile) and reads a `Regime` off five rules. `daily_brief` / `weekly_brief`
flatten a sheet into the payloads the narratives and the Claude prompt take.

Simplifications, stated once:

  * FRED percent series (yields, spreads, OAS) are stored as DECIMALS; `unit`
    only says how the UI should print them ("pct" → 4.25%, "bp" → 95bp).
    Levels (VIX, WTI, futures, the broad-dollar index) and FX quotes are raw.
  * Changes are over 1/5/21/63 OBSERVATIONS of daily series, not calendar
    dates; z and percentile use the last 252 observations (or all if fewer).
    Weekend rows are dropped from every loaded series so DFF (a 7-day FRED
    series) counts sessions like the business-day ones.
  * The curve regime reuses `curves._regime` on DGS2/DGS10 over 20 sessions,
    so the macro page and the rates page never disagree.
  * `source="fred"`/`"yfinance"` mean "live providers, raise on failure": FRED
    ids go to FRED and Yahoo ids to Yahoo either way. Only `auto` degrades.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from datetime import date

import numpy as np

from core.ficc.common import BP, FICCError
from core.ficc.curves import _regime
from core.ficc.data import Series, load_many

_Z_WINDOW = 252
_CHANGES = (("chg_1d", 1), ("chg_1w", 5), ("chg_1m", 21), ("chg_3m", 63))
DESCRIPTIVE_READ_NOTE = "descriptive read — not a regime model (P19)"

CURVE_REGIMES = ("bull steepener", "bear steepener", "bull flattener", "bear flattener",
                 "parallel up", "parallel down", "unchanged")
RISK_REGIMES = ("risk-on", "risk-off", "neutral")
DOLLAR_REGIMES = ("strong", "weak", "range")
TREND_REGIMES = ("rising", "falling", "stable")


@dataclass(frozen=True)
class Indicator:
    id: str
    label: str
    group: str                        # "rates" | "credit" | "fx" | "risk"
    unit: str                         # "pct" | "bp" | "level" | "fx"
    source_hint: str                  # "FRED" | "YFINANCE"


INDICATORS: tuple[Indicator, ...] = (
    Indicator("DGS2", "UST 2y", "rates", "pct", "FRED"),
    Indicator("DGS10", "UST 10y", "rates", "pct", "FRED"),
    Indicator("DGS30", "UST 30y", "rates", "pct", "FRED"),
    Indicator("T10Y2Y", "2s10s", "rates", "bp", "FRED"),
    Indicator("DFII10", "10y real (TIPS)", "rates", "pct", "FRED"),
    Indicator("T10YIE", "10y breakeven", "rates", "pct", "FRED"),
    Indicator("SOFR", "SOFR", "rates", "pct", "FRED"),
    Indicator("DFF", "Fed funds", "rates", "pct", "FRED"),
    Indicator("BAMLC0A0CM", "IG OAS", "credit", "bp", "FRED"),
    Indicator("BAMLH0A0HYM2", "HY OAS", "credit", "bp", "FRED"),
    Indicator("DTWEXBGS", "Broad USD", "fx", "level", "FRED"),
    Indicator("DEXUSEU", "EUR/USD", "fx", "fx", "FRED"),
    Indicator("DEXJPUS", "USD/JPY", "fx", "fx", "FRED"),
    Indicator("DEXKOUS", "USD/KRW", "fx", "fx", "FRED"),
    Indicator("VIXCLS", "VIX", "risk", "level", "FRED"),
    Indicator("DCOILWTICO", "WTI", "risk", "level", "FRED"),
    Indicator("ZN=F", "10y note future", "risk", "level", "YFINANCE"),
    Indicator("GC=F", "Gold", "risk", "level", "YFINANCE"),
)


@dataclass(frozen=True)
class MacroRow:
    id: str
    label: str
    group: str
    unit: str
    last: float
    last_date: str
    chg_1d: float | None
    chg_1w: float | None
    chg_1m: float | None
    chg_3m: float | None
    z_1y: float
    pct_1y: float                     # percentile rank of `last` in the 1y window, 0..1
    source: str


@dataclass(frozen=True)
class Regime:
    """Descriptive read — not a regime model (P19): rule-based labels of the indicators, computed causally;
    never a state, never a gate, never read by an acting module (T-CTX-01)."""
    curve: str                        # one of CURVE_REGIMES
    risk: str                         # one of RISK_REGIMES
    dollar: str                       # one of DOLLAR_REGIMES
    inflation: str                    # one of TREND_REGIMES (10y breakeven, 1m)
    real_rates: str                   # one of TREND_REGIMES (10y TIPS, 1m)
    summary: str


@dataclass(frozen=True)
class MacroSheet:
    as_of: str
    rows: tuple[MacroRow, ...]
    regime: Regime
    sources: dict[str, int]           # count of rows per source label
    synthetic_ids: tuple[str, ...]
    note: str = ""

    def row(self, id: str) -> MacroRow | None:
        return next((r for r in self.rows if r.id == id), None)


# --------------------------------------------------------------------------- #
# Rows
# --------------------------------------------------------------------------- #
def _row(ind: Indicator, s: Series) -> MacroRow:
    if len(s) < 2:
        raise FICCError(f"{ind.id}: only {len(s)} observation(s); cannot build a row.")
    if s.source == "FRED" and ind.unit in ("pct", "bp"):
        s = s.scaled(0.01)                      # FRED percent → decimal
    x = s.array()[-_Z_WINDOW:]
    sd = float(x.std())
    z = float((x[-1] - x.mean()) / sd) if sd > 0 else 0.0
    changes = {name: s.change(n) for name, n in _CHANGES}
    return MacroRow(id=ind.id, label=ind.label, group=ind.group, unit=ind.unit,
                    last=float(s.last), last_date=s.last_date, **changes,
                    z_1y=z, pct_1y=float((x <= x[-1]).mean()), source=s.source)


def _weekdays(s: Series) -> Series:
    keep = [i for i, d in enumerate(s.dates) if date.fromisoformat(d).weekday() < 5]
    if len(keep) == len(s.dates):
        return s
    return replace(s, dates=tuple(s.dates[i] for i in keep),
                   values=tuple(s.values[i] for i in keep))


def _load(source: str, days: int) -> dict[str, Series]:
    if source in ("auto", "synthetic"):
        out = load_many([i.id for i in INDICATORS], source=source, days=days)
    else:
        out = {}
        for prov in ("FRED", "YFINANCE"):
            ids = [i.id for i in INDICATORS if i.source_hint == prov]
            out.update(load_many(ids, source=prov.lower(), days=days))
    return {i: _weekdays(s) for i, s in out.items()}


# --------------------------------------------------------------------------- #
# Descriptive read (not a regime model, P19): five threshold rules
# --------------------------------------------------------------------------- #
def _trend(chg: float | None, band: float) -> str:
    if chg is None or abs(chg) < band:
        return "stable"
    return "rising" if chg > 0 else "falling"


def _regime_from(series: dict[str, Series], rows: dict[str, MacroRow]) -> Regime:
    def chg(id: str, n: int) -> float:
        # Each series carries its own unit: FRED percent → decimal, others raw.
        s = series.get(id)
        c = s.change(n) if s is not None else None
        return float(c) * (0.01 if s.source == "FRED" else 1.0) if c is not None else 0.0

    d10, d2 = chg("DGS10", 20), chg("DGS2", 20)
    curve = _regime(d10, d2, d10 - d2)

    risk_z = (rows["VIXCLS"].z_1y + rows["BAMLH0A0HYM2"].z_1y) / 2
    risk = "risk-off" if risk_z > 0.75 else "risk-on" if risk_z < -0.5 else "neutral"

    usd = rows["DTWEXBGS"]
    usd_1m = (usd.chg_1m / (usd.last - usd.chg_1m)) if usd.chg_1m is not None else 0.0
    dollar = "strong" if usd_1m > 0.015 else "weak" if usd_1m < -0.015 else "range"

    inflation = _trend(rows["T10YIE"].chg_1m, 10 * BP)
    real = _trend(rows["DFII10"].chg_1m, 15 * BP)
    summary = (f"[{DESCRIPTIVE_READ_NOTE}] "
               f"Curve {curve} (10y {d10 / BP:+.0f}bp, 2s10s {(d10 - d2) / BP:+.0f}bp over "
               f"20 sessions); {risk} (VIX/HY z {risk_z:+.2f}); dollar {dollar} "
               f"({usd_1m * 100:+.1f}% 1m); breakevens {inflation}, real yields {real} "
               f"(1m {(rows['T10YIE'].chg_1m or 0) / BP:+.0f}bp / "
               f"{(rows['DFII10'].chg_1m or 0) / BP:+.0f}bp).")
    return Regime(curve=curve, risk=risk, dollar=dollar, inflation=inflation,
                  real_rates=real, summary=summary)


# --------------------------------------------------------------------------- #
# Sheet
# --------------------------------------------------------------------------- #
def macro_sheet(*, source: str = "auto", days: int = 504) -> MacroSheet:
    """Load every INDICATOR, build rows and the descriptive read (not a regime
    model, P19). `auto` degrades id by id to SYNTHETIC (listed in
    `synthetic_ids`); explicit providers raise. Context only: never an acting
    input (T-CTX-01; the v2 context_log reads the PIT store, not this)."""
    if days < 30:
        raise ValueError(f"days must be >= 30, got {days}")
    series = _load((source or "auto").lower(), days)
    rows = tuple(_row(ind, series[ind.id]) for ind in INDICATORS)
    by_id = {r.id: r for r in rows}
    sources: dict[str, int] = {}
    for r in rows:
        sources[r.source] = sources.get(r.source, 0) + 1
    synthetic = tuple(r.id for r in rows if r.source == "SYNTHETIC")
    notes = []
    if synthetic:
        notes.append(f"{len(synthetic)}/{len(rows)} indicators are SYNTHETIC: "
                     + ", ".join(synthetic) + ".")
    short = min(len(series[i.id]) for i in INDICATORS)
    if short < _Z_WINDOW:
        notes.append(f"Shortest series has {short} obs; z/percentile use fewer than 252.")
    return MacroSheet(as_of=max(r.last_date for r in rows), rows=rows,
                      regime=_regime_from(series, by_id), sources=sources,
                      synthetic_ids=synthetic, note=" ".join(notes))


# --------------------------------------------------------------------------- #
# Report payloads
# --------------------------------------------------------------------------- #
def _rel_1d(r: MacroRow) -> float:
    if r.chg_1d is None or r.last == r.chg_1d:
        return 0.0
    return r.chg_1d / (r.last - r.chg_1d)


def daily_brief(sheet: MacroSheet, *, top: int = 5) -> dict:
    """Movers (largest |z| and largest relative 1d change), the curve, the
    descriptive read (payload key `regime`; not a regime model, P19)."""
    rows = [asdict(r) for r in sheet.rows]
    by_z = sorted(rows, key=lambda d: abs(d["z_1y"]), reverse=True)[:top]
    # ponytail: relative 1d change ranks rates and levels on one scale; good enough for a top-5.
    by_1d = sorted(sheet.rows, key=lambda r: abs(_rel_1d(r)), reverse=True)[:top]
    curve = {k: (sheet.row(i).last if sheet.row(i) else None)
             for k, i in (("2y", "DGS2"), ("10y", "DGS10"), ("30y", "DGS30"),
                          ("2s10s", "T10Y2Y"), ("10y_real", "DFII10"),
                          ("10y_breakeven", "T10YIE"))}
    return {"as_of": sheet.as_of, "regime": asdict(sheet.regime), "curve": curve,
            "movers_z": by_z,
            "movers_1d": [dict(asdict(r), rel_1d=_rel_1d(r)) for r in by_1d],
            "rows": rows, "sources": dict(sheet.sources),
            "synthetic_ids": list(sheet.synthetic_ids), "note": sheet.note}


def weekly_brief(sheet: MacroSheet, curve_report=None, carry_rows=None) -> dict:
    """The daily payload plus 1w/1m changes, the rates page's CurveReport
    (descriptors/shape/regime/changes) and the FX carry table when given."""
    out = daily_brief(sheet)
    out["weekly_changes"] = [{"id": r.id, "label": r.label, "unit": r.unit,
                              "chg_1w": r.chg_1w, "chg_1m": r.chg_1m} for r in sheet.rows]
    if curve_report is not None:
        out["curve_report"] = {
            "date": curve_report.snapshot.date, "shape": curve_report.shape,
            "regime": curve_report.regime, "lookback": curve_report.lookback,
            "descriptors": dict(curve_report.descriptors),
            "changes": dict(curve_report.changes)}
    if carry_rows:
        out["carry"] = [asdict(r) if hasattr(r, "__dataclass_fields__") else dict(r)
                        for r in carry_rows]
    return out


# --------------------------------------------------------------------------- #
# Self-check (synthetic only — no network)
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    sheet = macro_sheet(source="synthetic", days=300)
    assert len(sheet.rows) == len(INDICATORS) and sheet.sources == {"SYNTHETIC": 18}
    assert set(sheet.synthetic_ids) == {i.id for i in INDICATORS}
    for r in sheet.rows:
        assert -6 <= r.z_1y <= 6 and 0 <= r.pct_1y <= 1, r
        assert r.chg_3m is not None and r.last_date == sheet.as_of, r
    assert sheet.row("DGS10").last < 0.15 and sheet.row("ZN=F").last > 1
    assert sheet.regime.curve in CURVE_REGIMES and sheet.regime.risk in RISK_REGIMES
    assert sheet.regime.dollar in DOLLAR_REGIMES
    assert sheet.regime.inflation in TREND_REGIMES and sheet.regime.real_rates in TREND_REGIMES
    assert "Curve" in sheet.regime.summary and "SYNTHETIC" in sheet.note
    assert macro_sheet(source="synthetic", days=300) == sheet          # deterministic

    d = daily_brief(sheet)
    assert len(d["movers_z"]) == 5 and len(d["movers_1d"]) == 5 and d["curve"]["10y"]
    w = weekly_brief(sheet)
    assert len(w["weekly_changes"]) == 18 and "curve_report" not in w

    # FRED percent → decimal, and chg_3m is None on a short series
    fred = Series("DGS10", "x", "FRED", ("2025-01-01", "2025-01-02", "2025-01-03"),
                  (4.0, 4.1, 4.3))
    row = _row(INDICATORS[1], fred)
    assert abs(row.last - 0.043) < 1e-12 and abs(row.chg_1d - 0.002) < 1e-12
    assert row.chg_3m is None and row.pct_1y == 1.0
    assert _regime(8 * BP, 0.0, 8 * BP) == "bear steepener"

    # Mixed sources: 10y FRED percent (+10bp) vs 2y SYNTHETIC decimal (+30bp) → flattener,
    # and the same with the labels swapped. A shared scale would read the 2y as +0.3bp.
    by_id = {r.id: r for r in sheet.rows}
    dates = tuple(f"2025-03-{i + 3:02d}" for i in range(21))
    pct = Series("DGS10", "x", "FRED", dates, tuple(4.0 + 0.1 * (i == 20) for i in range(21)))
    dec = Series("DGS2", "x", "SYNTHETIC", dates,
                 tuple(0.04 + 0.003 * (i == 20) for i in range(21)))
    for ten, two, want in ((pct, dec, "bear flattener (10y +10bp, 2s10s -20bp"),
                           (replace(dec, id="DGS10"), replace(pct, id="DGS2"),
                            "bear steepener (10y +30bp, 2s10s +20bp")):
        mixed = _regime_from({"DGS10": ten, "DGS2": two}, by_id)
        assert mixed.curve == want.split(" (")[0] and want in mixed.summary, mixed
    # Weekend rows go (DFF is a 7-day FRED series); a clean series is returned as-is.
    wk = _weekdays(Series("DFF", "x", "FRED", ("2025-01-03", "2025-01-04", "2025-01-05",
                                                "2025-01-06"), (1.0, 2.0, 3.0, 4.0)))
    assert wk.dates == ("2025-01-03", "2025-01-06") and wk.values == (1.0, 4.0)
    assert _weekdays(fred) is fred
    assert all(date.fromisoformat(d).weekday() < 5
               for s in _load("synthetic", 300).values() for d in s.dates)
    print("ok")
