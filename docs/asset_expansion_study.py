"""The asset-expansion validation study: every candidate model or strategy of
QUANTGEN version 3 is run through the gate in `core.quant.validate` on real
history, and the verdict (PASS / REVISE / REJECT / INSUFFICIENT_DATA) decides
what the app offers by default.

Run:   python docs/asset_expansion_study.py [--quick] [--only id1,id2] [--refresh]
Out:   docs/asset_expansion/results.csv      one row per (card, metric)
       docs/asset_expansion/results.md       the tables the README quotes
       docs/asset_expansion/cards/<id>.json  one model card per candidate
       docs/asset_expansion/manifest.json    md5 of results.csv, data spans, run date
Cache: docs/asset_expansion/cache/*.csv      prices as downloaded (re-runs are offline)

Data: Yahoo Finance (US ETFs, sector SPDRs, futures continuous contracts,
^VIX/^VIX3M/VIXY, BTC-USD, KRX ETFs and stocks as .KS), FRED (Treasury curve,
DGS3MO, DEXKOUS), Upbit and Binance public endpoints (KRW-BTC, BTCUSDT,
funding), KIS for the live option board and KOSPI200 futures (today's
reconciliation only; KIS keeps no chain history). Every strategy signals on
close t and earns from t+1; costs are the pre-registered per-side numbers
(KRX ETF 3 bp, US via KIS 50 bp, KRX stock 35 bp incl. tax, crypto 10 bp,
futures 5 bp) and every card also reports the 2× stress.

Citations for each candidate are in reports/QUANTGEN asset coverage expansion.md
(the shortlist table) and are copied onto the card.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import time
import traceback
from dataclasses import asdict
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
for stream in (sys.stdout, sys.stderr):
    try:
        stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import config                                                     # noqa: E402
from core.quant import strategies as S                             # noqa: E402
from core.quant import validate as V                               # noqa: E402
from core.quant.history import History                             # noqa: E402

OUT = ROOT / "docs" / "asset_expansion"
CACHE = OUT / "cache"
CARDS = OUT / "cards"
for d in (OUT, CACHE, CARDS):
    d.mkdir(parents=True, exist_ok=True)

COST = V.COST_BP_PER_SIDE   # the gate's table (P10): same six numbers, one definition
SEED = 11
QUICK = False


# --------------------------------------------------------------------------- #
# Data (cached)
# --------------------------------------------------------------------------- #
def _cached(name: str, loader) -> pd.Series:
    f = CACHE / (name.replace("=", "_").replace("^", "_").replace(":", "_").replace("/", "_") + ".csv")
    if f.exists() and not REFRESH:
        s = pd.read_csv(f, index_col=0, parse_dates=True).iloc[:, 0]
    else:
        s = loader()
        s = s.dropna()
        s.name = name
        s.to_csv(f)
    s = s.dropna()
    s.index = pd.to_datetime(s.index)
    return s[s > 0] if (s > 0).all() or name.startswith("_") is False else s


def yf(symbol: str, start: str = "1995-01-01") -> pd.Series:
    def load():
        import yfinance
        df = yfinance.download(symbol, start=start, auto_adjust=True, progress=False, threads=False)
        if df is None or df.empty:
            raise RuntimeError(f"Yahoo returned nothing for {symbol}")
        close = df["Close"]
        s = close.iloc[:, 0] if isinstance(close, pd.DataFrame) else close
        return s.astype(float)
    return _cached(f"yf_{symbol}", load)


def fred(series_id: str, start: str = "1990-01-01") -> pd.Series:
    def load():
        import pandas_datareader.data as web
        return web.DataReader(series_id, "fred", start).iloc[:, 0].astype(float)
    f = CACHE / f"fred_{series_id}.csv"
    if f.exists() and not REFRESH:
        s = pd.read_csv(f, index_col=0, parse_dates=True).iloc[:, 0]
    else:
        s = load(); s.to_csv(f)
    s.index = pd.to_datetime(s.index)
    return s.dropna()


def upbit(market: str = "KRW-BTC") -> pd.Series:
    def load():
        from data.crypto.crypto_client import UpbitPublic
        c = UpbitPublic().daily(market, days=4000)
        return pd.Series(c.close, index=pd.to_datetime(c.dates))
    return _cached(f"upbit_{market}", load)


def binance(symbol: str = "BTCUSDT") -> pd.Series:
    def load():
        from data.crypto.crypto_client import BinancePublic
        c = BinancePublic().daily(symbol, days=4000)
        return pd.Series(c.close, index=pd.to_datetime(c.dates))
    return _cached(f"binance_{symbol}", load)


def binance_funding(symbol: str = "BTCUSDT") -> pd.Series:
    def load():
        from data.crypto.crypto_client import BinancePublic
        f = BinancePublic().funding(symbol, days=3000)
        d = f.daily()
        return pd.Series(list(d.values()), index=pd.to_datetime(list(d.keys())))
    f = CACHE / f"binance_funding_{symbol}.csv"
    if f.exists() and not REFRESH:
        s = pd.read_csv(f, index_col=0, parse_dates=True).iloc[:, 0]
    else:
        s = load(); s.to_csv(f)
    s.index = pd.to_datetime(s.index)
    return s


def panel(series: dict[str, pd.Series], *, start: str | None = None) -> S.Panel:
    df = pd.concat(series, axis=1).dropna()
    if start:
        df = df[df.index >= start]
    if len(df) < 300:
        raise RuntimeError(f"only {len(df)} shared sessions for {list(series)}")
    return S.Panel(dates=tuple(d.strftime("%Y-%m-%d") for d in df.index), symbols=tuple(df.columns),
                   prices=df.to_numpy(dtype=float), sources=tuple("STUDY" for _ in df.columns))


def rf_daily(index) -> np.ndarray:
    try:
        s = fred("DGS3MO").reindex(index, method="ffill").fillna(0.03) / 100.0 / 252.0
        return s.to_numpy(dtype=float)
    except Exception:
        return np.full(len(index), 0.03 / 252.0)


# --------------------------------------------------------------------------- #
# Cards
# --------------------------------------------------------------------------- #
ROWS: list[dict] = []
CARD_LIST: list[V.ModelCard] = []
DATA_SPANS: dict[str, str] = {}


def _rows(card_id: str, **metrics) -> None:
    for k, v in metrics.items():
        if isinstance(v, (tuple, list)):
            for i, x in enumerate(v):
                ROWS.append({"card": card_id, "metric": f"{k}_{i}", "value": x})
        else:
            ROWS.append({"card": card_id, "metric": k, "value": v})


def strategy_card(card_id: str, *, hypothesis: str, fn, grid: list[dict], pnl: S.Panel, cost_bps: float,
                  embargo: int, bench: np.ndarray | None, universe: dict, citations: list[str],
                  cash_daily=0.0, rules: dict | None = None, ledger: list[str] | None = None,
                  n_trials: int | None = None, domain: dict | None = None) -> V.ModelCard:
    """`n_trials` counts every configuration ever tried for this card (the grid
    plus earlier grids recorded in `ledger`), so a revision deflates harder;
    `domain` names the natural limits of a parameter (an edge there is not an
    unexplored region)."""
    t0 = time.time()
    n_trials = n_trials or len(grid)
    M, Ms, Tv = S.pnl_matrix(pnl.prices, fn, grid, cost_bps=cost_bps, cash_daily=cash_daily)
    dates = pnl.dates[1:]
    wf = V.walk_forward(M, dates, turnover=Tv, pnl_stress=Ms, embargo=embargo)
    b = None
    if bench is not None:
        # align the benchmark's daily returns with the OOS dates
        bd = dict(zip(dates, bench))
        b = np.array([bd[d] for d in wf.dates])
    if QUICK:
        V.GATE["bootstrap_B"] = 300
    sc = V.score_strategy(wf, grid=grid, full_pnl=M, n_trials=n_trials, bench_daily=b, seed=SEED, domain=domain)
    chosen = grid[wf.chosen[-1]] if wf.chosen else {}
    stats = {k: v for k, v in asdict(sc).items() if k not in ("lines", "regime")}
    stats["regime"] = sc.regime
    stats["chosen_last"] = chosen
    stats["bench_sharpe"] = sc.bench_sr
    stats["walk_forward"] = wf.note
    stats["seconds"] = round(time.time() - t0, 1)
    card = V.ModelCard(card_id=card_id, kind="strategy", hypothesis=hypothesis,
                       rules=rules or {"family": fn.__name__, "grid": grid, "cost_bps_per_side": cost_bps, "embargo": embargo},
                       universe=universe, data={"sessions": len(pnl), "start": pnl.dates[0], "end": pnl.dates[-1],
                                                "source": "Yahoo adjusted close unless stated"},
                       costs={"cost_bps": cost_bps, "stress_multiplier": V.GATE["cost_stress"]},
                       protocol={k: V.GATE[k] for k in ("w_is", "w_oos", "min_is", "ci_level", "bootstrap_B", "block")},
                       trials={"N_planned": len(grid), "N_total": n_trials, "ledger": ledger or []}, seed=SEED,
                       stats=stats, tests={"dsr": sc.dsr, "pbo": sc.pbo, "ci90": sc.ci90, "sr_stress": sc.sr_stress},
                       decision=sc.decision, decision_reason=sc.reason, revise_target=sc.revise_target,
                       lines=sc.lines, citations=citations)
    _rows(card_id, decision=sc.decision, sr_oos=sc.sr_oos, ci_lo=sc.ci90[0], ci_hi=sc.ci90[1], dsr=sc.dsr, pbo=sc.pbo,
          oos_is=sc.oos_is, sr_stress=sc.sr_stress, years_positive=sc.years_positive, plateau=sc.plateau,
          n_trades=sc.n_trades, n_sessions=sc.n_sessions, max_drawdown=sc.max_drawdown, bench_sharpe=sc.bench_sr,
          total_return=sc.total_return, haircut_sr=sc.haircut_sr)
    return card


def model_card(card_id: str, *, kind: str, hypothesis: str, decision: str, reason: str, stats: dict, tests: dict,
               lines: list[str], universe: dict, data: dict, citations: list[str], revise: str | None = None,
               rules: dict | None = None) -> V.ModelCard:
    card = V.ModelCard(card_id=card_id, kind=kind, hypothesis=hypothesis, rules=rules or {}, universe=universe, data=data,
                       costs={}, protocol={}, trials={"N_planned": 1, "N_total": 1, "ledger": []}, seed=SEED,
                       stats=stats, tests=tests, decision=decision, decision_reason=reason, revise_target=revise,
                       lines=lines, citations=citations)
    flat = {k: v for k, v in {**stats, **tests}.items() if isinstance(v, (int, float, str, bool))}
    _rows(card_id, decision=decision, **flat)
    return card


def error_card(card_id: str, exc: Exception) -> V.ModelCard:
    tb = traceback.format_exc(limit=3)
    card = V.ModelCard(card_id=card_id, kind="error", hypothesis="", rules={}, universe={}, data={}, costs={}, protocol={},
                       trials={}, seed=SEED, stats={}, tests={}, decision="INSUFFICIENT_DATA",
                       decision_reason=f"{type(exc).__name__}: {exc}", revise_target="fix the data or the code",
                       lines=[tb], citations=[])
    _rows(card_id, decision="INSUFFICIENT_DATA", error=str(exc))
    return card


# --------------------------------------------------------------------------- #
# Candidates
# --------------------------------------------------------------------------- #
US_SLEEVES = ["SPY", "QQQ", "TLT", "GLD"]
KRX_SLEEVES = ["069500.KS", "152380.KS", "132030.KS", "229200.KS"]      # KODEX 200, 국채선물10년, 골드선물, 코스닥150
SPDRS = ["XLB", "XLE", "XLF", "XLI", "XLK", "XLP", "XLU", "XLV", "XLY"]
FUTURES = ["ZF=F", "ZN=F", "ZB=F", "GC=F", "SI=F", "CL=F", "NG=F", "ZC=F", "ZS=F", "HG=F"]
CIT = {
    "trend": ["Faber 2007/2013 SSRN 962461", "Moskowitz, Ooi & Pedersen 2012 JFE 104", "RN→FH §6.1, §6.5, §6.8 pp. 13–16"],
    "vol": ["Moreira & Muir 2017 JF 72", "Cederburg, O'Doherty, Wang & Yan 2020 JFE 138", "BKM Ch. 6 slides 6-20 to 6-22"],
    "rp": ["Asness, Frazzini & Pedersen 2012 FAJ 68", "BKM Ch. 7 slides 7-5 to 7-8", "Boyd §4.4.1 p. 155"],
    "xs": ["Jegadeesh & Titman 1993 JF 48", "Asness, Moskowitz & Pedersen 2013 JF 68", "McLean & Pontiff 2016 JF 71"],
    "tsmom": ["Moskowitz, Ooi & Pedersen 2012 JFE 104 eq. (1), (5)", "Primer §1.3 p. 7", "MTSA §8.2.2 p. 294"],
    "pairs": ["Gatev, Goetzmann & Rouwenhorst 2006 RFS 19", "Do & Faff 2010 FAJ 66", "MTSA §5.3.2 p. 170, §6.2.3 pp. 215–219, §6.3.2 pp. 228–238"],
    "crypto_trend": ["Liu & Tsyvinski 2021 RFS 34", "Detzel et al. 2021 FM", "MTSA §5.2 p. 161"],
    "vix": ["Simon & Campasano 2014 J. Derivatives 21(3)", "Eraker & Wu 2017 JFE 125", "RN→FH §5.1 p. 11, §5.5 p. 13"],
    "fxmom": ["Menkhoff, Sarno, Schmeling & Schrimpf 2012 JFE 106", "RN→FH §6.9 p. 17", "ECON302 Ch1 slides 9–17"],
    "dollar": ["Lustig, Roussanov & Verdelhan 2014 JFE 111", "Fama 1984 JME 14", "Shreve II 9.3.16 p. 385 (PDF 401)"],
    "dns": ["Diebold & Li 2006 J. Econometrics 130 (NBER w10048 pp. 12–16)", "Berkeley Lec 6 §1.1", "MTSA §2.4.3 p. 85"],
    "fly": ["Litterman & Scheinkman 1991 JFI 1", "Lay §7.1 p. 397, §7.5 pp. 426–433", "MTSA §5.3.2 p. 170"],
    "garch": ["Primer §6.3–6.4, §7.7", "ARCHITECTURE_REVIEW B5", "Berkeley Lec 8 §3 (coverage, PIT)", "Kupiec 1995; Christoffersen 1998"],
    "kimchi": ["Makarov & Schoar 2020 JFE 135", "Choi, Lehar & Stauffer (SSRN 3189051)", "MTSA §5.3.2, §5.3.4–5.3.5"],
    "funding": ["Schmeling, Schrimpf & Todorov 2023 BIS WP 1087", "He, Manela, Ross & von Wachter 2022 (arXiv 2212.06888)"],
    "ethbtc": ["MTSA Ch. 5–6", "Shreve II Ex. 4.4.10 p. 150 (PDF 166)"],
    "weekday": ["Baur, Cahill, Godfrey & Liu 2019 FRL 31", "ECON302 Ch1 slides 2–7"],
    "letf": ["Avellaneda & Zhang 2010 SIAM JFM 1 eq. (10)", "Cheng & Madhavan 2009 JOIM", "Shreve II §4.4.3 p. 147", "Primer §5.4 p. 15"],
    "board": ["Shreve II §4.5.4–4.5.6 pp. 158–162 (PDF 174–178)", "Gatheral & Jacquier 2014 QF 14", "Cboe VIX methodology pp. 7–9", "RN→FH p. 19"],
    "basis": ["Shreve II Thm 5.6.2 p. 241, eq. 5.6.11 p. 247", "Cornell & French 1983 JFM 3", "Ko 2022 KJFS 51"],
}


def run_trend(sleeves: list[str], cost_key: str, cid: str, start: str) -> V.ModelCard:
    pn = panel({s: yf(s) for s in sleeves}, start=start)
    rf = rf_daily(pd.to_datetime(pn.dates))
    grid = S.grid_from(rule=["sma", "tsmom"], lookback=[126, 210, 252], step=[21, 42])
    bench = (pn.prices[1:] / pn.prices[:-1] - 1.0).mean(axis=1)
    return strategy_card(cid, hypothesis="Faber SMA / MOP sign trend switch on ETF sleeves beats equal-weight buy-and-hold "
                         "on Sharpe and drawdown (long or cash, 1/N per sleeve)",
                         fn=S.trend_switch, grid=grid, pnl=pn, cost_bps=COST[cost_key], embargo=21, bench=bench,
                         universe={"symbols": sleeves, "venue": cost_key}, citations=CIT["trend"], cash_daily=rf)


def run_vol_target(symbol: str, cost_key: str, cid: str, start: str) -> V.ModelCard:
    pn = panel({symbol: yf(symbol)}, start=start)
    rf = rf_daily(pd.to_datetime(pn.dates))
    grid = S.grid_from(target=[0.08, 0.10, 0.12, 0.15], window=[22, 44], step=[21])
    bench = pn.prices[1:, 0] / pn.prices[:-1, 0] - 1.0
    return strategy_card(cid, hypothesis="Capped volatility targeting w = min(1, σ*/σ̂) raises Sharpe and cuts drawdown "
                         "against buy-and-hold (Moreira–Muir in Cederburg's real-time form)",
                         fn=S.vol_target, grid=grid, pnl=pn, cost_bps=COST[cost_key], embargo=21, bench=bench,
                         universe={"symbols": [symbol], "venue": cost_key}, citations=CIT["vol"], cash_daily=rf)


def run_risk_parity(sleeves: list[str], cost_key: str, cid: str, start: str) -> V.ModelCard:
    pn = panel({s: yf(s) for s in sleeves}, start=start)
    grid = S.grid_from(window=[125, 250, 500, 750], step=[21, 63])
    bench = (pn.prices[1:] / pn.prices[:-1] - 1.0).mean(axis=1)
    return strategy_card(cid, hypothesis="Equal-risk-contribution allocation across sleeves beats equal weight on Sharpe "
                         "(unlevered; the 2022 stock-bond correlation regime is inside the sample)",
                         fn=S.risk_parity, grid=grid, pnl=pn, cost_bps=COST[cost_key], embargo=63, bench=bench,
                         universe={"symbols": sleeves, "venue": cost_key}, citations=CIT["rp"])


def run_xs_momentum(cid: str) -> V.ModelCard:
    pn = panel({s: yf(s) for s in SPDRS}, start="1999-01-01")
    grid = S.grid_from(lookback=[126, 189, 252], skip=[5, 21], top=[1 / 3], step=[21, 42], long_only=[True])
    bench = (pn.prices[1:] / pn.prices[:-1] - 1.0).mean(axis=1)
    return strategy_card(cid, hypothesis="12-1 cross-sectional momentum across the nine sector SPDRs (long top third) "
                         "beats the equal-weight sector basket after 50 bp per side",
                         fn=S.xs_momentum, grid=grid, pnl=pn, cost_bps=COST["us"], embargo=21, bench=bench,
                         universe={"symbols": SPDRS, "venue": "us"}, citations=CIT["xs"])


def run_tsmom(cid: str) -> V.ModelCard:
    pn = panel({s: yf(s) for s in FUTURES}, start="2001-01-01")
    rf = rf_daily(pd.to_datetime(pn.dates))
    grid = S.grid_from(lookback=[63, 126, 252], vol_target_ann=[0.20, 0.40], cap=[1.0], step=[21, 42], long_only=[False])
    bench = (pn.prices[1:] / pn.prices[:-1] - 1.0).mean(axis=1)
    return strategy_card(cid, hypothesis="MOP time-series momentum (12-month sign, 40 %/σ sizing, long/short) on ten "
                         "Yahoo continuous futures earns a positive net Sharpe out of sample after 2009 "
                         "(caveat: Yahoo's roll treatment is undocumented)",
                         fn=S.tsmom, grid=grid, pnl=pn, cost_bps=COST["futures"], embargo=21, bench=bench,
                         universe={"symbols": FUTURES, "venue": "futures"}, citations=CIT["tsmom"], cash_daily=rf)


def run_crypto_trend(symbol: str, loader, cid: str) -> V.ModelCard:
    s = loader()
    pn = panel({symbol: s})
    # The composite is the mean of nine sign votes, so it lives on the lattice k/9: a hysteresis of
    # 0.05, 0.1 or 0.2 is the same rule ("long from 1/9"), which made the first grid three rules
    # in six costumes (duplicate columns corrupt the plateau, PBO and DSR). The grid is now the
    # lattice midpoints, one distinct rule each; 0 is the natural floor (long on a bare majority).
    # The five values are the whole domain: 0 = long on a bare majority, 0.889 = long only when unanimous.
    grid = S.grid_from(hysteresis=[0.0, 0.222, 0.444, 0.667, 0.889])
    bench = pn.prices[1:, 0] / pn.prices[:-1, 0] - 1.0
    return strategy_card(cid, hypothesis="Short-horizon sign votes plus price/MA ratios (long/flat with hysteresis) beat "
                         "buy-and-hold BTC on Sharpe with a 25 % smaller drawdown",
                         fn=S.crypto_trend, grid=grid, pnl=pn, cost_bps=COST["crypto"], embargo=1, bench=bench,
                         universe={"symbols": [symbol], "venue": "crypto"}, citations=CIT["crypto_trend"],
                         domain={"hysteresis": (0.0, 0.889)}, n_trials=11,
                         ledger=["run 2/3: hysteresis [0.05, 0.1, 0.2, 0.3, 0.4, 0.5] (6 trials, three of them duplicates on "
                                 "the vote lattice) → REVISE on a grid edge for BTC-USD",
                                 "run 4: the complete lattice [0, 2/9, 4/9, 6/9, 8/9] with its ends declared as the domain; "
                                 "N_total = 11 trials for the DSR"])


def run_pairs(y: str, x: str, cost_key: str, cid: str, long_only: bool, start: str = "2005-01-01") -> V.ModelCard:
    pn = panel({y: yf(y), x: yf(x)}, start=start)
    grid = S.grid_from(formation=[126, 252], trading=[126], entry=[1.5, 2.0, 2.5, 3.0], exit=[0.0], long_only=[long_only])

    def fn(prices, **theta):
        W, _ = S.pairs(prices, **theta)
        return W
    fn.__name__ = "pairs"
    _, diag = S.pairs(pn.prices, formation=252, trading=126, entry=2.0)
    bench = (pn.prices[1:] / pn.prices[:-1] - 1.0).mean(axis=1) if long_only else None
    card = strategy_card(cid, hypothesis=f"{y}/{x}: the Engle–Granger spread mean-reverts fast enough to trade at 2σ "
                         f"after {COST[cost_key]:.0f} bp per side ({'long-only tilt' if long_only else 'dollar-neutral'})",
                         fn=fn, grid=grid, pnl=pn, cost_bps=COST[cost_key], embargo=5, bench=bench,
                         universe={"symbols": [y, x], "venue": cost_key}, citations=CIT["pairs"])
    card.stats["share_cointegrated"] = diag.share_cointegrated
    card.stats["median_half_life"] = float(np.median([h for h in diag.half_lives if math.isfinite(h)] or [float("nan")]))
    card.lines.insert(0, f"ADF rejects a unit root in {diag.share_cointegrated:.0%} of the {len(diag.adf_p)} formation windows; "
                         f"median half-life {card.stats['median_half_life']:.0f} sessions (gate: ≥ 60 % and 5–40 sessions).")
    _rows(cid, share_cointegrated=diag.share_cointegrated, median_half_life=card.stats["median_half_life"])
    return card


def run_vix(cid: str) -> V.ModelCard:
    from core.ficc import vol_products as VP
    vix, vix3m, vixy, spy = yf("^VIX"), yf("^VIX3M"), yf("VIXY"), yf("SPY")
    df = pd.concat({"VIX": vix, "VIX3M": vix3m, "VIXY": vixy, "SPY": spy}, axis=1).dropna()
    dates = tuple(d.strftime("%Y-%m-%d") for d in df.index)
    grid = S.grid_from(threshold=[0.02, 0.04, 0.06, 0.08], exit=[0.0, 0.02])
    P = df[["VIXY", "SPY"]].to_numpy(dtype=float)
    b = VP.term_structure(df["VIX"].to_numpy(), df["VIX3M"].to_numpy())
    r = np.diff(np.log(P), axis=0)
    beta = np.concatenate([[np.nan], VP.rolling_beta(r[:, 0], r[:, 1], 60)])

    def fn(prices, **theta):
        return VP.roll_down_positions(b, beta, threshold=theta["threshold"], exit=theta["exit"], hedge=True, beta_step=0.25)
    fn.__name__ = "vix_roll_down"
    pn = S.Panel(dates=dates, symbols=("VIXY", "SPY"), prices=P)
    bench = -(P[1:, 0] / P[:-1, 0] - 1.0)          # unconditional short VIXY
    return strategy_card(cid, hypothesis="Short the VIX ETP while VIX3M/VIX − 1 exceeds a contango threshold, hedged with "
                         "a rolling SPY beta (reset only when it moves by 0.25), earns the roll-down with a smaller drawdown "
                         "than the unhedged short (Simon–Campasano)", fn=fn, grid=grid, pnl=pn, cost_bps=5.0, embargo=1, bench=bench,
                         universe={"symbols": ["^VIX", "^VIX3M", "VIXY", "SPY"], "venue": "us (10 bp per side, futures-like)"},
                         citations=CIT["vix"])


def run_fx(cid: str, kind: str) -> V.ModelCard:
    from core.ficc import fx_styles as FX
    from core.ficc.data import G10_KRW, load_fx_spot, load_policy_rates
    pairs = {c: ("USD" + c if c in ("JPY", "KRW", "CAD", "CHF") else c + "USD") for c in G10_KRW if c != "USD"}
    spots = {p: load_fx_spot(p, source="auto", days=6000) for p in pairs.values()}
    rates = load_policy_rates(list(G10_KRW), source="auto", days=6000)
    bad = [k for k, s in spots.items() if s.source == "SYNTHETIC"] + [k for k, s in rates.items() if s.source == "SYNTHETIC"]
    if bad:
        raise RuntimeError(f"synthetic inputs: {bad}")
    if kind == "momentum":
        grid = [{"formation_months": f} for f in (1, 3)]
        runs = [FX.momentum_backtest(spots, rates, formation_months=f, cost_bps=COST["fx"]) for f in (1, 3)]
        runs_s = [FX.momentum_backtest(spots, rates, formation_months=f, cost_bps=2 * COST["fx"]) for f in (1, 3)]
        hyp = "Cross-sectional FX momentum (1-1 and 3-1) on G10+KRW earns a positive net return with t > 2 after 2010"
        cit = CIT["fxmom"]
    else:
        grid = [{"rebalance_days": 21}]
        runs = [FX.dollar_carry_backtest(spots, rates, cost_bps=COST["fx"] / 2)]
        runs_s = [FX.dollar_carry_backtest(spots, rates, cost_bps=COST["fx"])]
        hyp = "Dollar carry (long the foreign basket when the average forward discount is positive) has a positive OOS Sharpe"
        cit = CIT["dollar"]
    common = sorted(set.intersection(*(set(r.dates) for r in runs)))
    def col(bt):
        lookup = dict(zip(bt.dates, bt.equity))
        eq = np.array([lookup[d] for d in common])
        return np.diff(eq) / eq[:-1]
    M = np.column_stack([col(r) for r in runs])
    Ms = np.column_stack([col(r) for r in runs_s])
    dates = tuple(common[1:])
    Tv = np.zeros_like(M)
    for j, r in enumerate(runs):
        reb = {d for d, _, _ in r.positions}
        Tv[:, j] = np.array([1.0 if d in reb else 0.0 for d in dates])
    wf = V.walk_forward(M, dates, turnover=Tv, pnl_stress=Ms, embargo=21)
    from core.ficc.fx import carry_backtest
    cb = carry_backtest(spots, rates, top_n=3, cost_bps=5.0)
    lk = dict(zip(cb.dates, cb.equity))
    bench = np.array([lk.get(d, np.nan) for d in wf.dates])
    bench = np.where(np.isfinite(bench), bench, np.nan)
    bench_r = np.concatenate([[0.0], np.diff(bench) / bench[:-1]]) if np.isfinite(bench).all() else None
    sc = V.score_strategy(wf, grid=grid, full_pnl=M, n_trials=len(grid), bench_daily=bench_r, seed=SEED)
    stats = {k: v for k, v in asdict(sc).items() if k not in ("lines",)}
    stats["carry_basket_sharpe"] = cb.sharpe
    if bench_r is not None and len(bench_r) == len(wf.pnl):
        stats["corr_with_carry"] = float(np.corrcoef(wf.pnl, bench_r)[0, 1])
    card = V.ModelCard(card_id=cid, kind="strategy", hypothesis=hyp, rules={"grid": grid, "cost_bps_per_leg": COST["fx"]},
                       universe={"pairs": list(pairs.values()), "venue": "fx (read-only; KRX 통화선물 for execution)"},
                       data={"sessions": len(common), "start": common[0], "end": common[-1], "source": "FRED H.10 / Yahoo, OECD short rates"},
                       costs={"cost_bps": COST["fx"]}, protocol={k: V.GATE[k] for k in ("w_is", "w_oos", "min_is")},
                       trials={"N_planned": len(grid), "N_total": len(grid), "ledger": []}, seed=SEED, stats=stats,
                       tests={"dsr": sc.dsr, "pbo": sc.pbo, "ci90": sc.ci90}, decision=sc.decision,
                       decision_reason=sc.reason, revise_target=sc.revise_target, lines=sc.lines, citations=cit)
    _rows(cid, decision=sc.decision, sr_oos=sc.sr_oos, ci_lo=sc.ci90[0], ci_hi=sc.ci90[1], dsr=sc.dsr, pbo=sc.pbo,
          sr_stress=sc.sr_stress, years_positive=sc.years_positive, carry_basket_sharpe=cb.sharpe,
          corr_with_carry=stats.get("corr_with_carry", float("nan")))
    return card


def run_dns(cid: str) -> V.ModelCard:
    from core.ficc import curve_models as CM
    from core.ficc.data import load_treasury_curve
    pnl = load_treasury_curve(source="fred", days=9500)
    st = CM.dns_study(pnl, horizons=(6, 12), first_forecast_month=120)
    ev = [1.0, 2.0, 5.0, 10.0, 30.0]
    idx = [list(st.tenors).index(t) for t in ev]
    beats = int(np.sum(st.rmse_dns[12][idx] < st.rmse_rw[12][idx]))
    sig = int(np.sum(st.dm_t[12][idx] < -1.96))
    decision = "PASS" if beats >= 4 and sig >= 3 else "REVISE" if beats >= 3 else "REJECT"
    lines = [f"12-month forecasts ({st.n_forecasts[12]} origins): DNS beats the random walk at {beats} of 5 maturities "
             f"(1/2/5/10/30y) and significantly (DM t < −1.96) at {sig}: gate needs 4 and 3.",
             "RMSE in bp — DNS vs RW at 12m: " + ", ".join(f"{t:g}y {st.rmse_dns[12][i] * 1e4:.0f}/{st.rmse_rw[12][i] * 1e4:.0f}"
                                                            for t, i in zip(ev, idx)),
             f"6-month: DNS beats RW at {int(np.sum(st.rmse_dns[6][idx] < st.rmse_rw[6][idx]))} of 5.",
             f"Daily NS fit RMSE {st.fit_rmse_bp:.1f} bp with λ fixed at 0.0609/month; AR(1) γ per factor at 12m: "
             + ", ".join(f"{g:.2f}" for g in st.ar_coefficients[1])]
    return model_card(cid, kind="model", hypothesis="Diebold–Li AR(1) factor forecasts beat the random walk at 12 months on "
                      "≥ 4 of 5 maturities with DM p < 0.05 at ≥ 3", decision=decision,
                      reason=f"{beats}/5 maturities beaten, {sig}/5 significant",
                      stats={"beats_rw_12m": beats, "significant_12m": sig, "n_forecasts_12m": st.n_forecasts[12],
                             "fit_rmse_bp": st.fit_rmse_bp, "rmse_dns_12m_bp": [float(x * 1e4) for x in st.rmse_dns[12][idx]],
                             "rmse_rw_12m_bp": [float(x * 1e4) for x in st.rmse_rw[12][idx]],
                             "dm_t_12m": [float(x) for x in st.dm_t[12][idx]]},
                      tests={"dm_t_min": float(np.min(st.dm_t[12][idx]))}, lines=lines,
                      universe={"curve": "US Treasury par (FRED)"}, data={"months": len(CM._month_ends(pnl.dates)), "start": pnl.dates[0], "end": pnl.dates[-1]},
                      citations=CIT["dns"], revise=None if decision == "PASS" else "no claim at h = 1; use h = 12 only")


def run_fly(cid: str) -> V.ModelCard:
    from core.ficc import curve_models as CM
    from core.ficc.data import load_treasury_curve
    pnl = load_treasury_curve(source="fred", days=9500)
    fs = CM.butterfly_signal(pnl, window=250, entry=2.0, exit=0.0, max_hold=60)
    cost_bp = 1.0                                          # per leg per round trip, yield bp
    ok = fs.adf_p < 0.05 and fs.hit_rate > 0.55 and fs.mean_pnl_per_trade_bp > 2 * cost_bp and fs.half_life < 120 and fs.n_trades >= 30
    decision = "PASS" if ok else ("REJECT" if fs.half_life > 120 or fs.adf_p > 0.10 else "REVISE")
    lines = [f"Fly = {fs.weights[0]:.2f}·2y + 5y + {fs.weights[2]:.2f}·10y (bp), PCA-neutral to level and slope; "
             f"ADF p = {fs.adf_p:.3f}, half-life {fs.half_life:.0f} sessions (gate: p < 0.05, < 120).",
             f"{fs.n_trades} trades at |z| > 2: hit rate {fs.hit_rate:.0%}, mean {fs.mean_pnl_per_trade_bp:.1f} bp per trade "
             f"against {2 * cost_bp:.0f} bp of round-trip cost (gate: > 55 %, > 2× cost, ≥ 30 trades)."]
    return model_card(cid, kind="strategy", hypothesis="The PCA-neutral 2-5-10 butterfly mean-reverts and its 2σ rule "
                      "earns more than twice its cost per trade", decision=decision,
                      reason="all fly criteria met" if ok else "see lines", stats={"weights": list(fs.weights), "n_trades": fs.n_trades,
                      "hit_rate": fs.hit_rate, "mean_pnl_per_trade_bp": fs.mean_pnl_per_trade_bp, "half_life": fs.half_life},
                      tests={"adf_p": fs.adf_p}, lines=lines, universe={"curve": "US Treasury 2/5/10y (FRED)"},
                      data={"sessions": len(pnl), "start": pnl.dates[0], "end": pnl.dates[-1]}, citations=CIT["fly"])


def run_garch(symbol: str, loader, cid: str, window: int = 730, model: str = "garch_t") -> V.ModelCard:
    from core.crypto.analytics import garch_scorecard
    s = loader()
    s = s[s.index >= "2012-01-01"] if symbol != "BTC-USD" else s
    dates = tuple(d.strftime("%Y-%m-%d") for d in s.index)
    sc = garch_scorecard(dates, s.to_numpy(dtype=float), window=window, refit=7 if not QUICK else 21, model=model)
    ds = V.score_distribution(hits95=sc.hits95, hits99=sc.hits99, inband90=sc.inband90, pit=sc.pit, nonconv=sc.nonconv)
    dm = V.dm_test(sc.qlike_garch, sc.qlike_ewma, lag=5)
    label = {"gjr_t": "GJR-GARCH(1,1)-t", "gjr_skewt": "GJR-GARCH(1,1) skew-t"}.get(model, "GARCH(1,1)-t")
    st_share = float(np.mean(sc.at_stationarity)) if sc.at_stationarity.size else 0.0
    lines = list(ds.lines) + [f"QLIKE {label} {np.mean(sc.qlike_garch):.3f} vs EWMA(0.94) {np.mean(sc.qlike_ewma):.3f}: "
                              f"Diebold–Mariano t {dm['t']:+.2f} (negative favours the model; the crypto gate needs p < 0.10).",
                              f"Fitted ν: median {np.nanmedian(sc.nu_path[np.isfinite(sc.nu_path)]) if np.isfinite(sc.nu_path).any() else float('nan'):.1f}; "
                              f"{np.mean(~np.isfinite(sc.nu_path)):.0%} of refits effectively normal; the persistence sat on the "
                              f"stationarity guardrail (near-integrated variance) at {st_share:.0%} of origins"
                              + (f"; median leverage γ {np.median(sc.gamma_path):.3f}" if model != "garch_t" else "")
                              + (f"; median skew λ {np.median(sc.lambda_path):+.3f} (negative = longer left tail)." if model == "gjr_skewt" else ".")]
    if st_share > 0.05 and ds.decision == "PASS":
        ds.decision, ds.reason = "REVISE", f"calibrated, but the variance is near-integrated at {st_share:.0%} of origins"
        ds.revise_target = "a longer window or an integrated-variance specification"
    return model_card(cid, kind="distribution", hypothesis=f"{label} one-day-ahead fans on {symbol} are calibrated "
                      "(Kupiec/Christoffersen/PIT) and beat EWMA on QLIKE", decision=ds.decision, reason=ds.reason,
                      stats={"model": model, "n_origins": ds.n, "exceed95": ds.kupiec95["rate"], "exceed99": ds.kupiec99["rate"],
                             "coverage90": ds.coverage90["coverage"], "qlike_model": float(np.mean(sc.qlike_garch)),
                             "qlike_ewma": float(np.mean(sc.qlike_ewma)), "dm_t": dm["t"], "dm_p": dm["p"],
                             "nonconv_share": ds.nonconv_share, "stationarity_share": st_share, "traffic": ds.traffic,
                             "median_gamma": float(np.median(sc.gamma_path)) if sc.gamma_path.size else 0.0,
                             "median_lambda": float(np.median(sc.lambda_path)) if sc.lambda_path.size else 0.0},
                      tests={"kupiec95_p": ds.kupiec95["p"], "kupiec99_p": ds.kupiec99["p"], "cc_p": ds.christoffersen["p_cc"],
                             "pit_ks_p": ds.pit["ks_p"], "berkowitz_p": ds.pit["berkowitz_p"]},
                      lines=lines, universe={"symbol": symbol}, data={"sessions": len(s), "start": dates[0], "end": dates[-1], "window": window},
                      citations=CIT["garch"] + (["Glosten, Jagannathan & Runkle 1993 JF 48", "ARCHITECTURE_REVIEW B8"] if model != "garch_t" else [])
                      + (["Hansen 1994 IER 35 (skewed t)"] if model == "gjr_skewt" else []),
                      revise=ds.revise_target)


def run_kimchi(cid: str) -> V.ModelCard:
    from core.crypto.analytics import kimchi_premium
    up, bn, fx = upbit("KRW-BTC"), binance("BTCUSDT"), fred("DEXKOUS", "2017-01-01")
    kp = kimchi_premium({d.strftime("%Y-%m-%d"): v for d, v in up.items()}, {d.strftime("%Y-%m-%d"): v for d, v in bn.items()},
                        {d.strftime("%Y-%m-%d"): v for d, v in fx.items()})
    signal_ok = kp.adf_p < 0.05 and kp.half_life_days < 30 and math.isfinite(kp.pred_t) and kp.pred_t < -2
    decision = "PASS" if signal_ok else "REVISE"
    lines = [f"Premium now {kp.last_pct:+.2f} % (z {kp.last_z:+.2f}); mean {kp.mean_pct:.2f} %, max {kp.max_pct:.1f} % over {kp.n} days "
             f"since {kp.dates[0]}.",
             f"ADF p = {kp.adf_p:.3f}, half-life {kp.half_life_days:.0f} days (gate: p < 0.05, < 30 days).",
             f"Next-7-day BTC return on the premium z: slope {kp.pred_slope:+.4f}, Newey–West t {kp.pred_t:+.2f} "
             f"(gate: t < −2 for a sentiment signal; otherwise a descriptive tile only).", kp.note]
    return model_card(cid, kind="model", hypothesis="The kimchi premium is stationary with a short half-life and a high "
                      "premium predicts weaker BTC returns over the next week", decision=decision,
                      reason="predictive sign confirmed" if signal_ok else "descriptive tile only: the predictive test did not pass",
                      stats={"last_pct": kp.last_pct, "mean_pct": kp.mean_pct, "max_pct": kp.max_pct, "half_life_days": kp.half_life_days,
                             "pred_slope": kp.pred_slope, "pred_t": kp.pred_t, "n": kp.n},
                      tests={"adf_p": kp.adf_p}, lines=lines, universe={"legs": ["Upbit KRW-BTC", "Binance BTCUSDT", "FRED DEXKOUS"]},
                      data={"start": kp.dates[0], "end": kp.dates[-1]}, citations=CIT["kimchi"],
                      revise=None if signal_ok else "keep as a monitor; never feed the composite")


def run_funding(cid: str) -> V.ModelCard:
    from core.crypto.analytics import funding_carry
    f, px = binance_funding("BTCUSDT"), binance("BTCUSDT")
    fc = funding_carry({d.strftime("%Y-%m-%d"): v for d, v in f.items()}, {d.strftime("%Y-%m-%d"): v for d, v in px.items()})
    sign_ok = fc.top_decile_fwd30 < fc.bottom_decile_fwd30 and fc.bootstrap_p < 0.05
    decision = "PASS" if sign_ok else "REVISE"
    lines = [f"Funding now {fc.last_ann_pct:+.1f} %/yr (7-day mean), {fc.percentile:.0%} percentile since {fc.dates[0]}: {fc.flag}.",
             f"Forward 30-day BTC return after top-decile funding {fc.top_decile_fwd30:+.2%} vs bottom decile "
             f"{fc.bottom_decile_fwd30:+.2%}; bootstrap P(top ≥ bottom) = {fc.bootstrap_p:.3f} (gate: < 0.05, the BIS sign)."]
    return model_card(cid, kind="model", hypothesis="High perpetual funding (crowded longs) predicts weaker 30-day BTC returns",
                      decision=decision, reason="BIS sign confirmed" if sign_ok else "sign not confirmed: the regime component is labelled unvalidated",
                      stats={"last_ann_pct": fc.last_ann_pct, "percentile": fc.percentile, "flag": fc.flag,
                             "top_decile_fwd30": fc.top_decile_fwd30, "bottom_decile_fwd30": fc.bottom_decile_fwd30, "n": fc.n},
                      tests={"bootstrap_p": fc.bootstrap_p}, lines=lines, universe={"symbol": "BTCUSDT perpetual"},
                      data={"start": fc.dates[0], "end": fc.dates[-1]}, citations=CIT["funding"],
                      revise=None if sign_ok else "component 4 stays with the skill's raw thresholds")


def run_ethbtc(cid: str) -> V.ModelCard:
    from core.crypto.analytics import eth_btc_test
    e, b = binance("ETHUSDT"), binance("BTCUSDT")
    r = eth_btc_test({d.strftime("%Y-%m-%d"): v for d, v in e.items()}, {d.strftime("%Y-%m-%d"): v for d, v in b.items()})
    decision = "REVISE" if r["adf_p"] < 0.05 else "REJECT"
    return model_card(cid, kind="model", hypothesis="ln(ETH/BTC) is mean-reverting (null expected)", decision=decision,
                      reason=r["verdict"], stats={"n": r["n"], "half_life_days": r["half_life_days"], "z_2y": r["z_2y"], "last_ratio": r["last_ratio"]},
                      tests={"adf_p": r["adf_p"]}, lines=[f"ADF p = {r['adf_p']:.3f}, half-life {r['half_life_days']:.0f} days over {r['n']} days: {r['verdict']}."],
                      universe={"pair": "ETHUSDT / BTCUSDT"}, data={"n": r["n"]}, citations=CIT["ethbtc"],
                      revise="closed: the ratio has trended for years" if decision == "REJECT" else "OOS z-rule test pending")


def run_weekday(cid: str) -> V.ModelCard:
    from core.crypto.analytics import weekday_table
    from data.crypto.crypto_client import BinancePublic
    c = BinancePublic().daily("BTCUSDT", days=4000)
    wt = weekday_table(c.dates, np.asarray(c.close), np.asarray(c.quote_volume))
    null_ok = wt["return_effect_p_bonferroni"] > 0.05
    lines = [f"No weekday mean return differs after Bonferroni (p = {wt['return_effect_p_bonferroni']:.2f}): "
             f"{'the expected null' if null_ok else 'a weekday effect appears'}.",
             f"Weekend volume is {wt['weekend_volume_ratio']:.0%} of weekday volume (p = {wt['weekend_volume_p']:.1e}); "
             f"weekend slippage set at 2× in the crypto backtests." if wt['weekend_volume_ratio'] < 1 else "Weekend volume is not lower."]
    return model_card(cid, kind="model", hypothesis="Weekday returns carry no persistent effect; weekend liquidity is lower (a cost input)",
                      decision="PASS" if null_ok else "REVISE", reason="cost input set", stats={"rows": wt["rows"], "weekend_volume_ratio": wt["weekend_volume_ratio"]},
                      tests={"return_p_bonferroni": wt["return_effect_p_bonferroni"], "weekend_volume_p": wt["weekend_volume_p"]},
                      lines=lines, universe={"symbol": "BTCUSDT"}, data={"days": len(c)}, citations=CIT["weekday"])


def run_letf(cid: str) -> V.ModelCard:
    from core.ficc.equity_deriv import letf_drag, letf_realised_drag
    from core.quant.garch import fit_garch, forecast_variance
    lev, idx = yf("122630.KS"), yf("069500.KS")        # KODEX 200 as the KOSPI200 price proxy (Yahoo has no ^KS200 depth)
    df = pd.concat({"L": lev, "S": idx}, axis=1).dropna()
    df = df[df.index >= "2011-01-01"]
    if len(df) < 504 + 63:
        raise RuntimeError(f"only {len(df)} shared sessions between 122630.KS and 069500.KS")
    L, Sx = df["L"].to_numpy(), df["S"].to_numpy()
    r = np.diff(np.log(Sx))
    errs_g, errs_0, errs_last, pairs_ = [], [], [], []
    last_real = 0.0
    q = 63
    for t in range(504, len(df) - q, q):
        fit = fit_garch(r[t - 504:t], dist="t", profile=False)
        var_path = forecast_variance(fit, q)
        fc = letf_drag(2.0, var_path, fee=0.0064)["drag"]
        real = letf_realised_drag(L[t:t + q + 1], Sx[t:t + q + 1], 2.0)
        errs_g.append(abs(fc - real)); errs_0.append(abs(real)); errs_last.append(abs(last_real - real))
        pairs_.append((fc, real)); last_real = real
    fc_a, re_a = np.array([p[0] for p in pairs_]), np.array([p[1] for p in pairs_])
    X = np.column_stack([np.ones(fc_a.size), fc_a])
    beta, *_ = np.linalg.lstsq(X, re_a, rcond=None)
    r2 = 1 - np.sum((re_a - X @ beta) ** 2) / np.sum((re_a - re_a.mean()) ** 2)
    mae_g, mae_0, mae_l = (float(np.mean(x)) for x in (errs_g, errs_0, errs_last))
    ok = mae_g < 0.8 * min(mae_0, mae_l) and 0.7 <= beta[1] <= 1.3 and r2 >= 0.5
    decision = "PASS" if ok else "REVISE"
    lines = [f"{len(pairs_)} quarters: MAE of the GARCH-based drag forecast {mae_g * 1e4:.0f} bp vs naive-zero {mae_0 * 1e4:.0f} bp "
             f"and last-quarter {mae_l * 1e4:.0f} bp (gate: ≥ 20 % below both).",
             f"Realised on forecast: slope {beta[1]:.2f}, R² {r2:.2f} (gate: slope in [0.7, 1.3], R² ≥ 0.5).",
             f"Mean realised quarterly drag of KODEX 레버리지 vs 2× KOSPI200: {re_a.mean() * 1e4:+.0f} bp."]
    return model_card(cid, kind="model", hypothesis="The Avellaneda–Zhang drag with the app's GARCH-t variance term structure "
                      "forecasts KODEX 레버리지's quarterly shortfall versus 2× KOSPI200", decision=decision,
                      reason="forecast beats both naive benchmarks" if ok else "see lines",
                      stats={"quarters": len(pairs_), "mae_garch_bp": mae_g * 1e4, "mae_zero_bp": mae_0 * 1e4, "mae_last_bp": mae_l * 1e4,
                             "slope": float(beta[1]), "r2": float(r2), "mean_realised_drag_bp": float(re_a.mean() * 1e4)},
                      tests={}, lines=lines, universe={"letf": "122630.KS", "index": "^KS200"},
                      data={"start": str(df.index[0].date()), "end": str(df.index[-1].date())}, citations=CIT["letf"])


def run_board(cid: str) -> V.ModelCard:
    """Today's KOSPI200 option board: inversion vs KIS IV, parity, static arbitrage, SVI, MFIV, RND, box rate."""
    from core.ficc import equity_deriv as ED
    from data.kis_markets import KISMarkets
    from data.kis_markets import front_contract
    km = KISMarkets()
    exp = km.option_expiries()
    near = exp[0]
    fq0 = km.futures_quote(front_contract("KOSPI200") or "A01612")
    board = km.option_chain(near, float(fq0["underlying_level"]), width=0.10, step_pts=2.5, include_book=True)
    ys = km.krw_yields_snapshot()
    cd = next((y["yield_pct"] for y in ys if y["code"] == "Y0112"), 3.0) / 100.0
    # last prints and KIS IVs belong to the last session, so T is measured from it, not from today
    sess = km.last_session()
    T = max((date.fromisoformat(board.expiry_date) - date.fromisoformat(sess)).days, 1) / 365.0
    live = any(x.bid and x.ask for x in board.calls + board.puts)
    q = ED.board_quotes(board)
    F, k0 = ED.implied_forward(q, cd, T)
    pts = ED.chain_implied_vols(q, F, T, cd, quoted_only=True, max_moneyness=0.15)
    if len(pts) < 5:
        pts = ED.chain_implied_vols(q, F, T, cd, quoted_only=False, max_moneyness=0.10)
    rec = ED.reconcile_iv(pts)
    par = ED.parity_residuals(q, F, T, cd)
    arb = ED.static_arbitrage(q, quoted_only=True, F=F, max_moneyness=0.15)
    fit = ED.fit_svi([p.log_moneyness for p in pts], [p.iv for p in pts], T,
                     weights=[1.0 / max(p.spread or 0.05, 0.01) for p in pts])
    mv = ED.mfiv(q, F, T, cd)
    rnd = ED.rnd_from_svi(fit, F, cd)
    within = float(np.mean([x["within"] for x in par if x["within"] is not None])) if par else float("nan")
    atm = min(pts, key=lambda p: abs(p.log_moneyness))
    ok = live and rec["ok"] and within >= 0.95 and arb["call_butterfly"] + arb["put_butterfly"] == 0 and fit.rmse_near_volpts <= 0.5 and fit.arbitrage_free
    lines = [f"Expiry {board.expiry_date} (T = {T * 365:.0f} days from the last session {sess}), CD 91d {cd:.2%}, parity-implied forward {F:.2f} (K₀ {k0:.1f}); "
             f"{len(q)} strikes on the board, {len(board.calls)} calls / {len(board.puts)} puts; "
             + ("live two-sided quotes." if live else "captured with the market closed: last prints of different moments, no quotes, "
                                                     "so the parity, butterfly and reconciliation checks below are indicative only."),
             f"Black-76 inversion of {len(pts)} {'two-sided-quoted OTM mids' if live else 'OTM last prints'} within ±15 % of F vs KIS IV: median gap {rec['median_volpts']:.2f} vol pts, "
             f"90th pct {rec['p90_volpts']:.2f} (gate: ≤ 0.5 and ≤ 1.5).",
             f"Put–call parity within half the summed spread on {within:.0%} of near strikes (gate ≥ 95 %); butterfly violations "
             f"calls {arb['call_butterfly']} / puts {arb['put_butterfly']}, vertical {arb['call_vertical']} / {arb['put_vertical']}.",
             f"SVI: RMSE {fit.rmse_volpts:.2f} vol pts ({fit.rmse_near_volpts:.2f} within |k| ≤ 0.15), ρ {fit.rho:+.2f}, min g(k) {fit.min_g:+.3f} "
             f"({'arbitrage-free' if fit.arbitrage_free else 'butterfly arbitrage in the fit'}).",
             f"ATM implied vol {atm.iv:.1%}; model-free implied vol {mv['vol']:.1%} from {mv['n_strikes']} strikes; RND integrates to "
             f"{rnd['integral']:.3f} with mean {rnd['mean'] / F - 1:+.2%} vs F."]
    return model_card(cid, kind="model", hypothesis="The app's Black-76 inversion, parity checks, SVI and MFIV reconcile with the "
                      "live KOSPI200 board (candidate O1/O5/O6, today's snapshot)", decision="PASS" if ok else "REVISE",
                      reason=("today's board reconciles" if ok else
                              f"market closed at capture: last prints of {sess} only; run during a session (09:00–15:45 KST)" if not live else
                              "see lines; a single-day snapshot, history must accumulate"),
                      stats={"expiry": board.expiry_date, "T_days": T * 365, "session": sess, "live_quotes": live,
                             "forward": F, "atm_iv": atm.iv, "mfiv": mv["vol"],
                             "svi_rmse": fit.rmse_volpts, "svi_rho": fit.rho, "svi_min_g": fit.min_g, "rnd_integral": rnd["integral"],
                             "n_points": len(pts), "parity_within": within, "cd91": cd},
                      tests={"iv_median_gap": rec["median_volpts"], "iv_p90_gap": rec["p90_volpts"],
                             "butterfly_violations": arb["call_butterfly"] + arb["put_butterfly"]},
                      lines=lines, universe={"board": f"KOSPI200 {near}"}, data={"as_of": board.as_of, "source": "KIS display_board_callput"},
                      citations=CIT["board"], revise=None if ok else ("re-run during the session" if not live else
                                                                       "accumulate daily boards; check the KIS IV convention"))


def run_basis(cid: str) -> V.ModelCard:
    from core.ficc.equity_deriv import basis_report
    from data.kis_markets import KISMarkets, front_contract
    km = KISMarkets()
    code = front_contract("KOSPI200") or "A01612"
    fq = km.futures_quote(code)
    cd = next((y["yield_pct"] for y in km.krw_yields_snapshot() if y["code"] == "Y0112"), 3.0) / 100.0
    T = (fq["days_left"] or 1) / 365.0
    rep = basis_report(fq["price"], fq["underlying_level"], cd, T, div_pts=0.0, exchange_theo=fq["theo"])
    ok = rep.theo_gap_pts is not None and abs(rep.theo_gap_pts) <= 0.1 + 0.02 * fq["underlying_level"] * T   # allow the dividend gap
    lines = [f"{fq['name']} {fq['price']:.2f} vs KOSPI200 {fq['underlying_level']:.2f}: basis {rep.basis_pts:+.2f} pts, "
             f"fair value {rep.fair:.2f} at CD 91d {cd:.2%} over {T * 365:.0f} days (no dividend points), mispricing {rep.mispricing_bp:+.0f} bp.",
             f"KIS theoretical {fq['theo']:.2f} (gap {rep.theo_gap_pts:+.2f} pts): the dividend-point convention is the difference; "
             f"implied simple funding rate {rep.implied_rate:.2%}."]
    return model_card(cid, kind="model", hypothesis="The app's cost-of-carry fair value reconciles with KIS's theoretical price "
                      "once dividend points are aligned", decision="PASS" if ok else "REVISE", reason="within the dividend band" if ok else "see lines",
                      stats={"futures": fq["price"], "spot": fq["underlying_level"], "fair": rep.fair, "theo_kis": fq["theo"],
                             "mispricing_bp": rep.mispricing_bp, "implied_rate": rep.implied_rate, "cd91": cd, "days": fq["days_left"]},
                      tests={"theo_gap_pts": rep.theo_gap_pts}, lines=lines, universe={"contract": code},
                      data={"as_of": fq["as_of"]}, citations=CIT["basis"], revise=None if ok else "add the December dividend-point estimate")


CANDIDATES = {
    "S_E1_trend_us": lambda: run_trend(US_SLEEVES, "us", "S_E1_trend_us", "2004-12-01"),
    "S_E1_trend_krx": lambda: run_trend(KRX_SLEEVES, "krx_etf", "S_E1_trend_krx", "2012-01-01"),
    "S_E2_voltarget_spy": lambda: run_vol_target("SPY", "us", "S_E2_voltarget_spy", "1994-01-01"),
    "S_E2_voltarget_kodex200": lambda: run_vol_target("069500.KS", "krx_etf", "S_E2_voltarget_kodex200", "2003-01-01"),
    "S_E3_riskparity_us": lambda: run_risk_parity(["SPY", "TLT", "GLD"], "us", "S_E3_riskparity_us", "2004-12-01"),
    "S_E5_xsmom_sectors": lambda: run_xs_momentum("S_E5_xsmom_sectors"),
    "S_B3_tsmom_futures": lambda: run_tsmom("S_B3_tsmom_futures"),
    "S_C3_crypto_trend_btcusd": lambda: run_crypto_trend("BTC-USD", lambda: yf("BTC-USD", "2014-09-17"), "S_C3_crypto_trend_btcusd"),
    "S_C3_crypto_trend_krwbtc": lambda: run_crypto_trend("KRW-BTC", lambda: upbit("KRW-BTC"), "S_C3_crypto_trend_krwbtc"),
    "S_E8_pairs_kodex_tiger": lambda: run_pairs("069500.KS", "102110.KS", "krx_etf", "S_E8_pairs_kodex_tiger", False, "2009-01-01"),
    "S_S6_pairs_samsung_pref": lambda: run_pairs("005935.KS", "005930.KS", "krx_stock", "S_S6_pairs_samsung_pref", True, "2005-01-01"),
    "S_S6_pairs_hyundai_kia": lambda: run_pairs("000270.KS", "005380.KS", "krx_stock", "S_S6_pairs_hyundai_kia", False, "2005-01-01"),
    "S_E8_pairs_gld_iau": lambda: run_pairs("IAU", "GLD", "us", "S_E8_pairs_gld_iau", False, "2005-06-01"),
    "S_V1_vix_rolldown": lambda: run_vix("S_V1_vix_rolldown"),
    "S_V3_fx_momentum": lambda: run_fx("S_V3_fx_momentum", "momentum"),
    "S_V4_dollar_carry": lambda: run_fx("S_V4_dollar_carry", "dollar"),
    "M_B1_dns": lambda: run_dns("M_B1_dns"),
    "S_B2_pca_fly": lambda: run_fly("S_B2_pca_fly"),
    "D_C2_garch_btc": lambda: run_garch("BTC-USD", lambda: yf("BTC-USD", "2014-09-17"), "D_C2_garch_btc"),
    "D_Q_garch_spy": lambda: run_garch("SPY", lambda: yf("SPY"), "D_Q_garch_spy", window=504),
    "D_Q_garch_kodex200": lambda: run_garch("069500.KS", lambda: yf("069500.KS"), "D_Q_garch_kodex200", window=504),
    "D_C2_gjr_btc": lambda: run_garch("BTC-USD", lambda: yf("BTC-USD", "2014-09-17"), "D_C2_gjr_btc", model="gjr_t"),
    "D_Q_gjr_spy": lambda: run_garch("SPY", lambda: yf("SPY"), "D_Q_gjr_spy", window=504, model="gjr_t"),
    "D_Q_gjr_kodex200": lambda: run_garch("069500.KS", lambda: yf("069500.KS"), "D_Q_gjr_kodex200", window=504, model="gjr_t"),
    "D_C2_skewt_btc": lambda: run_garch("BTC-USD", lambda: yf("BTC-USD", "2014-09-17"), "D_C2_skewt_btc", model="gjr_skewt"),
    "D_Q_skewt_spy": lambda: run_garch("SPY", lambda: yf("SPY"), "D_Q_skewt_spy", window=504, model="gjr_skewt"),
    "D_Q_skewt_kodex200": lambda: run_garch("069500.KS", lambda: yf("069500.KS"), "D_Q_skewt_kodex200", window=504, model="gjr_skewt"),
    "M_C1_kimchi": lambda: run_kimchi("M_C1_kimchi"),
    "M_C4_funding": lambda: run_funding("M_C4_funding"),
    "M_C8_ethbtc": lambda: run_ethbtc("M_C8_ethbtc"),
    "M_C7_weekday": lambda: run_weekday("M_C7_weekday"),
    "M_E4_letf_drag": lambda: run_letf("M_E4_letf_drag"),
    "M_O1_board_today": lambda: run_board("M_O1_board_today"),
    "M_O2_basis_today": lambda: run_basis("M_O2_basis_today"),
}


# --------------------------------------------------------------------------- #
# Reporting
# --------------------------------------------------------------------------- #
def write_results() -> None:
    """results.csv / results.md / manifest.json over every card: the ones this
    run produced plus, after a `--only` run, the untouched cards read back from
    `cards/` (their rows are kept, their md5 re-stamped to the merged CSV)."""
    run_ids = {c.card_id for c in CARD_LIST}
    df = pd.DataFrame(ROWS)
    if (OUT / "results.csv").exists() and run_ids:
        old = pd.read_csv(OUT / "results.csv")
        df = pd.concat([old[~old["card"].isin(run_ids)], df], ignore_index=True)
    df.to_csv(OUT / "results.csv", index=False)
    md5 = hashlib.md5((OUT / "results.csv").read_bytes()).hexdigest()
    kept = {c["card_id"]: c for c in V.load_cards(CARDS) if c["card_id"] not in run_ids}
    cards = [json.loads(c.to_json()) for c in CARD_LIST] + list(kept.values())
    cards.sort(key=lambda c: list(CANDIDATES).index(c["card_id"]) if c["card_id"] in CANDIDATES else 999)
    for c in cards:
        c["results_file"], c["results_md5"] = "docs/asset_expansion/results.csv", md5
        (CARDS / f"{c['card_id']}.json").write_text(json.dumps(c, ensure_ascii=False, indent=1), encoding="utf-8")
    lines = ["# Asset-expansion validation study", "",
             f"Run {date.today().isoformat()} · seed {SEED} · results.csv md5 `{md5}` · gate `core/quant/validate.py`"
             + (f" · this run re-scored {', '.join(sorted(run_ids))}" if kept else ""), "",
             "Every strategy: purged walk-forward (IS 756 / OOS 126 sessions), signals on close t, earn from t+1, "
             "pre-registered per-side costs (KRX ETF 3 bp, US via KIS 50 bp, KRX stock 35 bp, crypto 10 bp, futures 5 bp) "
             "and a 2× stress. PASS needs the bootstrap 90 % Sharpe interval above zero, deflated Sharpe ≥ 0.95, "
             "no over-search (PBO ≤ 0.05, or the in-sample winner losing out of sample in ≤ 10 % of the CSCV splits, since a "
             "flat plateau puts PBO at 0.5 by construction), OOS/IS ≥ 0.5, ≥ 60 % positive years, survival at 2× costs, a "
             "parameter plateau (an edge only counts on an axis with ≥ 3 values), ≥ 100 trades and, when a benchmark exists, "
             "a paired-bootstrap Sharpe difference with one-sided p ≤ 0.10. "
             "Distributional models need Kupiec, Christoffersen, 90 % coverage and PIT tests over ≥ 500 origins.", "",
             "| Card | Kind | Decision | Reason | Key numbers |", "|---|---|---|---|---|"]
    for c in cards:
        s = c["stats"]
        if c["kind"] == "strategy" and "sr_oos" in s:
            key = (f"SR_OOS {s['sr_oos']:.2f} [{s['ci90'][0]:.2f}, {s['ci90'][1]:.2f}], DSR {s['dsr']:.2f}, PBO {s['pbo']:.2f}, "
                   f"2× costs {s['sr_stress']:.2f}, years+ {s['years_positive']:.0%}, trades {s['n_trades']}, "
                   f"bench SR {s.get('bench_sharpe', float('nan')):.2f}")
        else:
            key = "; ".join(f"{k} {v:.3g}" if isinstance(v, float) else f"{k} {v}" for k, v in list(c["tests"].items())[:4])
        lines.append(f"| {c['card_id']} | {c['kind']} | **{c['decision']}** | {c['decision_reason']} | {key} |")
    lines += ["", "## Plain-language lines per card", ""]
    for c in cards:
        lines.append(f"### {c['card_id']} — {c['decision']}")
        lines.append(f"*{c['hypothesis']}*")
        lines.append("")
        for ln in c["lines"]:
            lines.append(f"- {ln}")
        if c["citations"]:
            lines.append(f"- Sources: {'; '.join(c['citations'])}")
        lines.append("")
    (OUT / "results.md").write_text("\n".join(lines), encoding="utf-8")
    (OUT / "manifest.json").write_text(json.dumps({"run": date.today().isoformat(), "seed": SEED, "results_md5": md5,
                                                    "quick": QUICK, "cards": [c["card_id"] for c in cards],
                                                    "rescored": sorted(run_ids),
                                                    "decisions": {c["card_id"]: c["decision"] for c in cards}},
                                                   indent=1), encoding="utf-8")


def main() -> int:
    global QUICK, REFRESH
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true", help="fewer bootstrap draws and refits")
    ap.add_argument("--only", default="", help="comma-separated card ids")
    ap.add_argument("--refresh", action="store_true", help="ignore the price cache")
    a = ap.parse_args()
    QUICK, REFRESH = a.quick, a.refresh
    only = [x.strip() for x in a.only.split(",") if x.strip()]
    todo = {k: v for k, v in CANDIDATES.items() if not only or k in only}
    t_all = time.time()
    for cid, fn in todo.items():
        t0 = time.time()
        try:
            card = fn()
        except Exception as exc:                      # a failed candidate must not stop the study
            card = error_card(cid, exc)
        CARD_LIST.append(card)
        print(f"{card.decision:18s} {cid:32s} {card.decision_reason[:70]:70s} {time.time() - t0:6.1f}s", flush=True)
    write_results()
    print(f"\n{len(CARD_LIST)} cards in {time.time() - t_all:.0f}s → {OUT / 'results.md'}")
    return 0


REFRESH = False
if __name__ == "__main__":
    raise SystemExit(main())
