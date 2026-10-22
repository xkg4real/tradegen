"""Seeded scenario library: R-16 rule (4) (Council L1747 (4)); TASK-M9-03; T-REPRO-01c and the I-11 scenario clause.
CONTEXT (L1747 (6)): every result carries `acts = False`; no sizing module imports this module
(tests/macro_m9_scenarios.py scans them), and nothing here writes a file or touches a book.

- Shock windows (a)-(d) replay the anchored return path of their named factor series and of the current simulated
  book (static weights: `BookRuntime.held`, or a dict). Leveraged / inverse ETFs listed in `letf_leverage` are
  modelled from their underlying through `lab.letf_path_return` (R-26 rule 2, L2806), the carry accruing per session.
  A shock window is a deterministic replay of its inputs; the seed is recorded with them.
- The SEP band (e) is rate-path uncertainty through `ratesim.sep_band_params` / `sep_band_paths` (Vasicek / CIR /
  Hull-White), never a log-return price model: it returns rate paths only and never values the book.
- Every scenario names its Brent series (L1434; DNB item 19). Anchors the spec does not print are typed nulls with
  status OWNER_INPUT (brief F-16); a missing series -> `missing_input` naming it, nothing interpolated or substituted
  (P5). Window dates are return dates, inclusive (section 8.6 conventions, L5133-5140); "+20 days" is read as 20
  sessions of the scenario market (F-16).
Pure: no I/O, no clock. Inputs, the rules-store hash and the package version arrive through the arguments.
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field, replace
from datetime import date
from types import SimpleNamespace
from typing import Any, Mapping, Optional

import numpy as np

from core.ficc import ratesim as R
from core.ficc.common import FICCError
from core.quant import lab

BRENT_SERIES = {"spot": "DCOILBRENTEU", "futures": "BZ=F"}   # data.brent_series (L4221); "always name which" (L1434)
BRENT = BRENT_SERIES["spot"]          # multi-week windows: Dated spot, never continuous-futures returns across rolls (DNB 19)
SESSION_CLOCK = {"KR": "KOSPI_OFFICIAL_CLOSE", "US": "SPX_OFFICIAL_CLOSE"}   # whose sessions a window counts
LEVEL_SERIES = frozenset({"DFII10", "DGS10", "FEDFUNDS", "DFEDTARU"})       # percent-unit rates: level changes, decimal
KINDS = ("shock_window", "rate_band")
STATUSES = ("SPECIFIED", "OWNER_INPUT")
SEP_VINTAGE = "2023-12-13"            # the Dec-2023 SEP printing +-1.4 pp at 1 year (brief C.2 sep_band.sep_date)
KR_FACTORS = {"kospi": "KOSPI_OFFICIAL_CLOSE", "usdkrw": "ECOS_1530_CLOSE", "us10y_real": "DFII10"}
US_FACTORS = {"spx": "SPX_OFFICIAL_CLOSE"}


@dataclass(frozen=True)
class Scenario:
    id: str
    market: str                       # KR | US: whose sessions the window counts
    anchor_start: Optional[str]       # first return date, inclusive (rate band: the SEP vintage); None = owner input
    anchor_end: Optional[str]         # last return date, inclusive; None -> `horizon_sessions` sessions from the start
    horizon_sessions: Optional[int]   # the printed session count (checked against the data when both anchors are set)
    brent_series_id: str              # DCOILBRENTEU | BZ=F
    shocks: Mapping[str, float]       # the printed numbers, decimals (informative; asserted only against a fixture)
    letf_leverage: Mapping[str, tuple] = field(default_factory=dict)   # instrument -> (underlying id, L, path carry >= 0)
    status: str = "SPECIFIED"         # SPECIFIED | OWNER_INPUT
    kind: str = "shock_window"        # shock_window | rate_band
    factors: Mapping[str, str] = field(default_factory=dict)          # factor -> named series id (`series` adds Brent)
    owner_input: str = ""             # what the owner supplies while the status is OWNER_INPUT
    source: str = ""

    def __post_init__(self):
        if self.kind not in KINDS or self.status not in STATUSES or self.market not in SESSION_CLOCK:
            raise ValueError(f"{self.id}: kind {self.kind!r} / status {self.status!r} / market {self.market!r} refused")
        if self.brent_series_id not in BRENT_SERIES.values() or "brent" in self.factors:
            raise ValueError(f"{self.id}: brent_series_id must name {' or '.join(BRENT_SERIES.values())} "
                             f"(DNB item 19: never an unnamed 'Brent'), got {self.brent_series_id!r}")
        if (self.status == "OWNER_INPUT") != bool(self.owner_input):
            raise ValueError(f"{self.id}: an OWNER_INPUT status names its owner input, and only then")
        if self.anchor_start is None and self.status != "OWNER_INPUT":
            raise ValueError(f"{self.id}: a missing anchor is an owner input (status OWNER_INPUT), never invented")
        if self.kind == "shock_window" and self.anchor_end is None and not self.horizon_sessions:
            raise ValueError(f"{self.id}: a shock window needs anchor_end or horizon_sessions")
        if self.kind == "rate_band" and not ({"rmse_pp", "horizon_years", "coverage"} <= set(self.shocks)
                                             and "short_rate" in self.factors):
            raise ValueError(f"{self.id}: a rate band needs shocks rmse_pp / horizon_years / coverage and a short_rate factor")
        for inst, (und, L, carry) in self.letf_leverage.items():
            if not (isinstance(und, str) and math.isfinite(L) and L != 0 and math.isfinite(carry) and carry >= 0):
                raise ValueError(f"{self.id}: letf_leverage[{inst!r}] must be (underlying id, L != 0, carry >= 0)")

    @property
    def series(self) -> dict:
        return {**self.factors, "brent": self.brent_series_id}


@dataclass(frozen=True)
class ScenarioResult:
    scenario_id: str
    kind: str
    status: str                       # ok | missing_input
    missing: tuple = ()               # "REFDATA: ..." / "OWNER: ..."
    dates: tuple = ()                 # the window's return dates
    factor_moves: dict = field(default_factory=dict)        # factor -> move over the window (rates: level change)
    expected: dict = field(default_factory=dict)            # the printed numbers
    paths: dict = field(default_factory=dict, repr=False)   # instrument / "book" -> cumulative path; rate fan + terminal
    book_return: Optional[float] = None
    max_dd: Optional[float] = None
    rates: Any = field(default=None, repr=False)            # RateSimResult of the rate band
    band: dict = field(default_factory=dict)
    series: dict = field(default_factory=dict)              # factor -> named series id; always holds "brent"
    seed: int = lab.SEED
    repro: dict = field(default_factory=dict)
    note: str = ""
    acts: bool = False


_8_6 = "section 8.6 shock table (L5126-5140)"
SCENARIOS = (
    Scenario("oil_2026_p20", "KR", "2026-02-27", None, 20, BRENT, {"kospi": -0.155, "usdkrw": 0.052, "us10y_real": 0.0032},
             factors=KR_FACTORS, source="L1747 (4)(a); t0 = the Mar-2026 oil / geopolitical window start, KOSPI start-date "
             f"return included ({_8_6}; brief F-16 reading); +20 days = 20 KRX sessions"),
    Scenario("oil_2022_p20", "KR", None, None, 20, BRENT, {"kospi": 0.004, "usdkrw": 0.021, "us10y_real": -0.0004},
             status="OWNER_INPUT", factors=KR_FACTORS, source="L1747 (4)(a)",
             owner_input="t0 of the 2022 oil-shock replay (printed nowhere in the spec; brief F-16)"),
    Scenario("kospi_leverage_unwind_2026_07", "KR", "2026-06-23", "2026-07-30", 27, BRENT, {"kospi": -0.386},
             factors=KR_FACTORS, source="L1747 (4)(b); peak 9,114.55 on 2026-06-22, -38.6% in 27 sessions (L6441); "
             "= lab replay KR-2026-06-23_07-30"),
    Scenario("carry_unwind_2024_08", "KR", "2024-07-31", "2024-08-09", None, BRENT, {"kospi": -0.055},
             factors=KR_FACTORS, source=f"L1747 (4)(c); KOSPI window, start-date return included ({_8_6}); "
             "buy-and-hold -5.5% (G-KR-03, L5774)"),
    Scenario("carry_unwind_2024_08_us", "US", "2024-07-17", "2024-08-05", None, BRENT, {},
             factors=US_FACTORS, source=f"L1747 (4)(c); US returns after the 2024-07-16 close ({_8_6})"),
    Scenario("tariffs_2025_04", "KR", "2025-03-28", "2025-04-09", None, BRENT, {"kospi": -0.120},
             factors=KR_FACTORS, source=f"L1747 (4)(d); KOSPI window, start-date return included ({_8_6}); "
             "buy-and-hold -12.0% (G-KR-03, L5774)"),
    Scenario("tariffs_2025_04_us", "US", "2025-02-20", "2025-04-08", None, BRENT, {},
             factors=US_FACTORS, source=f"L1747 (4)(d); US returns after the 2025-02-19 close ({_8_6})"),
    Scenario("sep_rate_band", "US", SEP_VINTAGE, None, None, BRENT, {"rmse_pp": 1.4, "horizon_years": 1.0, "coverage": 0.70},
             status="OWNER_INPUT", kind="rate_band", factors={"short_rate": "FEDFUNDS"},
             owner_input="latest SEP Table 2 (only the Dec-2023 +-1.4 pp band is printed; read the latest SEP)",
             source="L1747 (4)(e); SEP Table 2 / FEDFUNDS registry row (L1437); context item L1692"),
)
SCENARIO_BY_ID = {s.id: s for s in SCENARIOS}


def scenario_library() -> list[dict]:
    """Every library scenario with its status (OWNER_INPUT rows name the input the owner supplies)."""
    return [asdict(s) for s in SCENARIOS]


def run_scenario(scenario: Scenario, book=None, returns_source: Optional[Mapping[str, tuple]] = None,
                 seed: int = lab.SEED, *, ctx: Optional[lab.LabContext] = None, rate_model: str = "vasicek",
                 n_paths: int = 5000) -> ScenarioResult:
    """Run one scenario. `book`: a `core.engine.books.BookRuntime` (its `held` weights) or {instrument: weight}, held
    static through the window. `returns_source`: series id / instrument -> (ISO dates ascending, values) (closes;
    rates in percent). `ctx` carries config_hash (rules-store hash), package_version and knowledge_utc for
    `lab.repro_record`; `seed` overrides its seed."""
    src = dict(returns_source or {})
    ctx = replace(ctx or lab.LabContext(), seed=int(seed))
    head = {"scenario_id": scenario.id, "kind": scenario.kind, "expected": dict(scenario.shocks),
            "series": scenario.series, "seed": int(seed)}
    if scenario.anchor_start is None:
        return _missing(head, ["OWNER: " + scenario.owner_input])
    if scenario.kind == "rate_band":
        return _rate_band(scenario, src, ctx, head, rate_model, n_paths)
    return _shock_window(scenario, book, src, ctx, head)


def _missing(head: dict, why) -> ScenarioResult:
    return ScenarioResult(status="missing_input", missing=tuple(why), **head)


def _series(pair) -> tuple[list[str], np.ndarray]:
    d, v = [str(x)[:10] for x in pair[0]], np.asarray(pair[1], dtype=float).reshape(-1)
    if len(d) != v.size:
        raise ValueError(f"{len(d)} dates for {v.size} values")
    return d, v


def _last_obs(d: list[str], v: np.ndarray, lo: str, hi: str) -> Optional[float]:
    """The last finite value dated in [lo, hi] (as-of; never interpolated)."""
    for x, y in zip(reversed(d), v[::-1]):
        if x < lo:
            return None
        if x <= hi and math.isfinite(y):
            return float(y)
    return None


def _window_returns(pair, base: str, dates: tuple) -> Optional[np.ndarray]:
    """Simple returns on exactly the window sessions from the `base` close; None when any close is absent."""
    pos = dict(zip(*_series(pair)))
    x = [pos.get(t) for t in (base, *dates)]
    if any(y is None or not math.isfinite(y) or y <= 0 for y in x):
        return None
    x = np.asarray(x, dtype=float)
    return x[1:] / x[:-1] - 1.0


def _letf_daily(r: np.ndarray, L: float, carry: float) -> np.ndarray:
    """Daily returns of the path formula ln(1 + R_L) = L ln(1 + R) - 1/2 (L^2 - L) sum r^2 - carry evaluated on every
    prefix of the underlying path (carry accrued per session), so the full path equals `lab.letf_path_return`."""
    n = r.size
    R_, S = np.cumprod(1.0 + r) - 1.0, np.cumsum(r * r)
    cum = np.array([lab.letf_path_return(float(R_[t]), float(S[t]), L, carry * (t + 1) / n) for t in range(n)])
    return (1.0 + cum) / np.r_[1.0, 1.0 + cum[:-1]] - 1.0


def _repro(ctx: lab.LabContext, src: Mapping, ids) -> dict:
    dates, values = [], []
    for sid in sorted(set(ids)):
        d, v = _series(src[sid])
        dates += [f"{sid}|{x}" for x in d]
        values.append(v)
    return lab.repro_record(ctx, dates, np.concatenate(values) if values else np.array([]))


def _shock_window(s: Scenario, book, src: dict, ctx: lab.LabContext, head: dict) -> ScenarioResult:
    held = book.held if hasattr(book, "held") else (book or {})
    weights = {str(i): float(w) for i, w in held.items()}
    clock = SESSION_CLOCK[s.market]
    need = [clock, *s.series.values(), *(s.letf_leverage[i][0] for i in weights if i in s.letf_leverage),
            *(i for i in weights if i not in s.letf_leverage)]
    absent = sorted({f"REFDATA: {x}" for x in need if x not in src})
    if absent:
        return _missing(head, absent)
    cd, _ = _series(src[clock])
    win = [i for i, x in enumerate(cd) if x >= s.anchor_start and (s.anchor_end is None or x <= s.anchor_end)]
    if s.anchor_end is None:
        win = win[:s.horizon_sessions]
    if not win or win[0] == 0:
        return _missing(head, [f"REFDATA: {clock} has no close before {s.anchor_start}"])
    if s.horizon_sessions is not None and len(win) != s.horizon_sessions:
        return _missing(head, [f"REFDATA: {clock} has {len(win)} sessions from {s.anchor_start}, "
                               f"the scenario prints {s.horizon_sessions}"])
    dates, base = tuple(cd[i] for i in win), cd[win[0] - 1]
    lo = cd[max(win[0] - 2, 0)]      # ponytail: a factor's base value may be one clock session old (cross-market dates)
    gaps, moves = [], {}
    for f, sid in s.series.items():
        d, v = _series(src[sid])
        a, b = _last_obs(d, v, lo, base), _last_obs(d, v, dates[0], dates[-1])
        if a is None or b is None:
            gaps.append(f"REFDATA: {sid} has no observation at {base} or inside the window")
        else:
            moves[f] = (b - a) / 100.0 if sid in LEVEL_SERIES else b / a - 1.0
    rets = {}
    for inst in weights:
        und, L, carry = s.letf_leverage.get(inst, (inst, 1.0, 0.0))
        r = _window_returns(src[und], base, dates)
        if r is None:
            gaps.append(f"REFDATA: {und} lacks a close on a window session" + (f" (underlying of {inst})" if und != inst else ""))
        else:
            rets[inst] = _letf_daily(r, L, carry) if inst in s.letf_leverage else r
    if gaps:
        return _missing(head, gaps)
    paths = {i: np.cumprod(1.0 + r) for i, r in rets.items()}
    book_ret = max_dd = None
    if weights:
        bp = np.cumprod(1.0 + sum(w * rets[i] for i, w in weights.items()))
        full = np.r_[1.0, bp]
        paths["book"], book_ret = bp, float(bp[-1] - 1.0)
        max_dd = float(np.min(full / np.maximum.accumulate(full) - 1.0))
    letf = "; ".join(f"{i}: L {L:g} on {u}, carry {c:g} (R-26 rule 2)" for i, (u, L, c) in s.letf_leverage.items() if i in weights)
    note = (f"{len(dates)} {s.market} sessions {dates[0]}..{dates[-1]} after the {base} close; deterministic replay, "
            f"seed recorded; static weights" + (f"; {letf}" if letf else ""))
    return ScenarioResult(status="ok", dates=dates, factor_moves=moves, paths=paths, book_return=book_ret, max_dd=max_dd,
                          repro=_repro(ctx, src, need), note=note, **head)


def _rate_band(s: Scenario, src: dict, ctx: lab.LabContext, head: dict, rate_model: str, n_paths: int) -> ScenarioResult:
    sid = s.factors["short_rate"]
    if sid not in src:
        return _missing(head, [f"REFDATA: {sid}"])
    d, v = _series(src[sid])
    keep = np.isfinite(v)
    d, v = [x for x, k in zip(d, keep) if k], v[keep] * (0.01 if sid in LEVEL_SERIES else 1.0)
    gap = float(np.median(np.diff([date.fromisoformat(x).toordinal() for x in d]))) if len(d) > 1 else 0.0
    try:                                     # calibrate's own dt rule: "monthly" -> 1/12, else 1/252
        base = R.calibrate(SimpleNamespace(array=lambda: v, note="monthly" if gap >= 28 else ""), model=rate_model)
    except FICCError as exc:
        return _missing(head, [f"REFDATA: {sid}: {exc}"])
    h, cov, band_pp = float(s.shocks["horizon_years"]), float(s.shocks["coverage"]), float(s.shocks["rmse_pp"])
    params = R.sep_band_params(band_pp, h, base, coverage=cov, vintage=s.anchor_start)
    sim = R.sep_band_paths(rate_model, params, int(ctx.seed), n_paths, h)
    label = "stale" if s.status == "OWNER_INPUT" else "latest"
    band = {"rmse_pp": band_pp, "coverage": cov, "horizon_years": h, "vintage": s.anchor_start, "label": label,
            "terminal_sd": float(np.std(sim.terminal)), "half_width_90": (sim.p95 - sim.p05) / 2.0}
    paths = {**{f"fan_p{p}": a for p, a in sim.fan.items()}, "terminal": sim.terminal}
    note = (f"{rate_model} short-rate paths on {sid}; SEP band vintage {s.anchor_start} labelled {label}; "
            "rate paths only: no book is valued through a price model")
    return ScenarioResult(status="ok", paths=paths, rates=sim, band=band, repro=_repro(ctx, src, [sid]), note=note, **head)
