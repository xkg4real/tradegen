"""Crypto analytics on keyless Upbit / Binance data: the kimchi premium, funding
as carry, a six-component market-regime score, the ETH/BTC ratio test, the
weekday table, and an out-of-sample scorecard for the app's GARCH(1,1)-t on
Bitcoin. Nothing here trades; every number carries its sample size.

  kimchi_premium      p = P_Upbit(KRW-BTC) / (P_Binance(BTCUSDT) · USDKRW) − 1,
                      1-year z, ADF, half-life, and the next-7-day predictive
                      regression (Makarov & Schoar 2020 JFE; Choi, Lehar &
                      Stauffer). A signal, never a trade: FETA remittance caps,
                      the Travel Rule and the 2027 tax close the arbitrage.
  funding_carry       8-hourly funding → annualised carry (×1,095), its
                      percentile since 2019-09-10, crowded flags, and the
                      decile event study (BIS WP 1087: high carry predicts
                      crashes; He, Manela, Ross & von Wachter 2022).
  regime_score        the six components of the crypto-regime-analyzer skill
                      (trend 25 %, alt breadth 20 %, dominance 15 %, funding
                      15 %, drawdown & vol 15 %, thrust 10 %) re-authored with
                      explicit thresholds; the skill itself says its bands are
                      "heuristic descriptive bands, not validated allocation
                      rules", and candidate C6's gate decides whether the
                      posture line ships.
  eth_btc_test        ADF / half-life on ln(ETH/BTC); a null is expected.
  weekday_table       returns and volume by weekday (Baur et al. 2019: no
                      persistent return effect, lower weekend volume).
  garch_scorecard     rolling GARCH-t refits (365-day annualisation), one-day
                      99 % / 95 % VaR hits, PIT, QLIKE against EWMA(0.94) —
                      inputs for `core.quant.validate.score_distribution`.

User-material refs: 계량2 §5.3 (unit roots) and §6.2 (single-equation
cointegration) for the premium; Shreve II §9.3.2 p. 383 (PDF 399) for the
domestic/foreign measure; the models primer §6.3–6.4 and §7.7 for ν and the
guardrails; STAT248 §21.2.3 for the estimate asymptotics.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date
from typing import Optional, Sequence

import numpy as np
from scipy import stats as sps

from core.quant.strategies import adf_pvalue, half_life
from core.quant.validate import newey_west_t

CRYPTO_DAYS = 365


def _align(*series: dict[str, float]) -> tuple[list[str], list[np.ndarray]]:
    common = sorted(set.intersection(*(set(s) for s in series)))
    return common, [np.array([s[d] for d in common], dtype=float) for s in series]


# --------------------------------------------------------------------------- #
# Kimchi premium
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class KimchiPremium:
    dates: tuple[str, ...]
    premium_pct: np.ndarray = field(repr=False)
    z_1y: np.ndarray = field(repr=False)
    btc_usd: np.ndarray = field(repr=False)
    last_pct: float = 0.0
    last_z: float = 0.0
    mean_pct: float = 0.0
    max_pct: float = 0.0
    adf_p: float = 1.0
    half_life_days: float = math.inf
    pred_slope: float = 0.0            # next-7-day BTC return on z
    pred_t: float = 0.0                # Newey–West t (lag 6)
    n: int = 0
    note: str = ""


def kimchi_premium(upbit_krw: dict[str, float], binance_usdt: dict[str, float],
                   usdkrw: dict[str, float], *, z_window: int = 365, horizon: int = 7) -> KimchiPremium:
    """Inputs are {date: close} dicts; USD/KRW is forward-filled by date because
    the FX fixing has no weekend rows."""
    dates = sorted(set(upbit_krw) & set(binance_usdt))
    fx_dates = np.array(sorted(usdkrw))
    fx_vals = np.array([usdkrw[d] for d in fx_dates], dtype=float)
    idx = np.searchsorted(fx_dates, np.array(dates), side="right") - 1
    keep = idx >= 0
    dates = [d for d, k in zip(dates, keep) if k]
    fx = fx_vals[idx[keep]]
    kr = np.array([upbit_krw[d] for d in dates])
    us = np.array([binance_usdt[d] for d in dates])
    prem = (kr / (us * fx) - 1.0) * 100.0
    z = np.full(prem.size, np.nan)
    for t in range(min(z_window, 90), prem.size):
        w = prem[max(0, t - z_window):t]
        sd = w.std(ddof=1)
        z[t] = (prem[t] - w.mean()) / sd if sd > 0 else 0.0
    fwd = np.full(prem.size, np.nan)
    if prem.size > horizon + 1:
        fwd[:-horizon] = np.log(us[horizon:] / us[:-horizon])
    ok = np.isfinite(z) & np.isfinite(fwd)
    slope, t = 0.0, float("nan")
    if ok.sum() > 60:
        X = np.column_stack([np.ones(ok.sum()), z[ok]])
        beta, *_ = np.linalg.lstsq(X, fwd[ok], rcond=None)
        resid = fwd[ok] - X @ beta
        xc = z[ok] - z[ok].mean()
        # HAC t for the slope from the moment condition series (overlapping 7-day returns → lag h−1)
        score = resid * xc
        se = math.sqrt(_hac_var(score, horizon - 1) * ok.sum()) / np.sum(xc ** 2)
        slope, t = float(beta[1]), float(beta[1] / se) if se > 0 else float("nan")
    return KimchiPremium(dates=tuple(dates), premium_pct=prem, z_1y=z, btc_usd=us, last_pct=float(prem[-1]),
                         last_z=float(z[-1]) if np.isfinite(z[-1]) else 0.0, mean_pct=float(prem.mean()),
                         max_pct=float(prem.max()), adf_p=adf_pvalue(prem), half_life_days=half_life(prem),
                         pred_slope=slope, pred_t=t, n=int(prem.size),
                         note=("USD/KRW forward-filled by date (FRED noon fixing vs UTC-midnight closes: a few hours "
                               "of FX drift); a positive premium means Korea pays more than the world price."))


def _hac_var(u: np.ndarray, lag: int) -> float:
    u = np.asarray(u, dtype=float)
    n = u.size
    s = float(u @ u) / n
    for k in range(1, lag + 1):
        s += 2.0 * (1.0 - k / (lag + 1.0)) * float(u[k:] @ u[:-k]) / n
    return s / n


# --------------------------------------------------------------------------- #
# Funding carry
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class FundingCarry:
    dates: tuple[str, ...]
    daily_rate: np.ndarray = field(repr=False)        # sum of the day's 8-hourly rates
    carry_ann_pct: np.ndarray = field(repr=False)     # trailing-7-day mean × 1,095 × 100
    last_ann_pct: float = 0.0
    percentile: float = 0.0                           # of the trailing-7d mean since the start
    flag: str = "normal"
    top_decile_fwd30: float = float("nan")            # mean forward 30-day BTC log return
    bottom_decile_fwd30: float = float("nan")
    bootstrap_p: float = float("nan")                 # P(top ≥ bottom) under resampling
    n: int = 0


def funding_carry(funding_daily: dict[str, float], btc_close: dict[str, float], *, window: int = 7,
                  fwd: int = 30, seed: int = 3) -> FundingCarry:
    dates, (f, px) = _align(funding_daily, btc_close)
    n = len(dates)
    if n < window + fwd + 30:
        raise ValueError(f"need more than {window + fwd + 30} days of aligned funding and prices, got {n}")
    trail = np.convolve(f, np.ones(window) / window, mode="full")[:n]
    trail[:window - 1] = np.nan
    carry_ann = trail / 1.0 * 3 * CRYPTO_DAYS * 100.0 / 1.0   # per-day sum × 365 ≈ mean8h × 1,095
    carry_ann = trail * CRYPTO_DAYS * 100.0
    last = float(carry_ann[-1])
    hist = carry_ann[np.isfinite(carry_ann)]
    pct = float(np.mean(hist <= last))
    flag = "crowded long" if pct >= 0.9 else "crowded short" if pct <= 0.1 else "normal"
    fwd_ret = np.full(n, np.nan)
    fwd_ret[:-fwd] = np.log(px[fwd:] / px[:-fwd])
    ok = np.isfinite(trail) & np.isfinite(fwd_ret)
    tr, fr = trail[ok], fwd_ret[ok]
    q_hi, q_lo = np.quantile(tr, [0.9, 0.1])
    top, bot = fr[tr >= q_hi], fr[tr <= q_lo]
    rng = np.random.default_rng(seed)
    if top.size > 10 and bot.size > 10:
        diff = np.array([rng.choice(top, top.size).mean() - rng.choice(bot, bot.size).mean() for _ in range(2000)])
        p = float(np.mean(diff >= 0))
    else:
        p = float("nan")
    return FundingCarry(dates=tuple(dates), daily_rate=f, carry_ann_pct=carry_ann, last_ann_pct=last, percentile=pct,
                        flag=flag, top_decile_fwd30=float(top.mean()) if top.size else float("nan"),
                        bottom_decile_fwd30=float(bot.mean()) if bot.size else float("nan"), bootstrap_p=p, n=n)


# --------------------------------------------------------------------------- #
# Regime score
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class RegimeComponent:
    key: str
    label: str
    weight: float
    score: Optional[float]          # 0–100, None when unavailable
    signal: str


@dataclass(frozen=True)
class RegimeScore:
    score: float
    zone: str                       # RISK_ON | NEUTRAL | RISK_OFF
    components: tuple[RegimeComponent, ...]
    effective_weights: dict[str, float]
    as_of: str
    note: str = ("Heuristic descriptive bands re-authored from the crypto-regime-analyzer skill; not validated "
                 "allocation rules until candidate C6 passes its gate.")


def _sma(x: np.ndarray, n: int) -> float:
    return float(np.mean(x[-n:])) if x.size >= n else float("nan")


def regime_score(btc: np.ndarray, majors: dict[str, np.ndarray], *, funding_ann_pct: Optional[float] = None,
                 dominance_30d_change: Optional[float] = None, as_of: str = "") -> RegimeScore:
    """`btc` and each major: daily closes (≥ 200). Components with missing
    inputs are dropped and their weight redistributed proportionally."""
    comps: list[RegimeComponent] = []
    p = float(btc[-1])
    s50, s200 = _sma(btc, 50), _sma(btc, 200)
    slope200 = (s200 / _sma(btc[:-20], 200) - 1.0) if btc.size >= 220 else float("nan")
    if math.isfinite(s200):
        if p > s50 > s200 and slope200 > 0:
            sc, sig = 100.0, "price above a rising 50/200 stack"
        elif p > s200 and p > s50:
            sc, sig = 75.0, "price above both averages, 50 below 200"
        elif p > s200 or p > s50:
            sc, sig = 45.0, "price above one average only"
        elif p < s50 < s200 and slope200 < 0:
            sc, sig = 0.0, "price below a falling 50/200 stack"
        else:
            sc, sig = 20.0, "price below both averages"
        comps.append(RegimeComponent("trend", "BTC trend structure", 0.25, sc, sig))
    else:
        comps.append(RegimeComponent("trend", "BTC trend structure", 0.25, None, "insufficient history"))
    above200 = [float(x[-1]) > _sma(x, 200) for x in majors.values() if x.size >= 200]
    above50 = [float(x[-1]) > _sma(x, 50) for x in majors.values() if x.size >= 50]
    if above200:
        breadth = 100.0 * np.mean(above200)
        bonus = 10.0 if above50 and np.mean(above50) > 0.5 else 0.0
        comps.append(RegimeComponent("breadth", "Alt breadth (above 200-DMA)", 0.20, min(100.0, breadth + bonus),
                                     f"{np.mean(above200):.0%} of {len(above200)} majors above their 200-DMA"))
    else:
        comps.append(RegimeComponent("breadth", "Alt breadth (above 200-DMA)", 0.20, None, "no major with 200 sessions"))
    if dominance_30d_change is not None and math.isfinite(s200):
        up = p > s200
        if up:
            sc, sig = (60.0, "dominance rising in an uptrend: BTC-led") if dominance_30d_change > 0 else (85.0, "dominance falling in an uptrend: broad participation")
        else:
            sc, sig = (30.0, "dominance rising in a downtrend: flight to BTC") if dominance_30d_change > 0 else (10.0, "dominance falling in a downtrend: broad liquidation")
        comps.append(RegimeComponent("dominance", "BTC dominance direction", 0.15, sc, sig))
    else:
        comps.append(RegimeComponent("dominance", "BTC dominance direction", 0.15, None, "no dominance history yet (accumulates daily)"))
    if funding_ann_pct is not None and math.isfinite(funding_ann_pct):
        a = abs(funding_ann_pct)
        if a > 30:
            sc, sig = 20.0, f"funding {funding_ann_pct:+.0f} %/yr: leverage crowded"
        elif a > 10:
            sc, sig = 50.0, f"funding {funding_ann_pct:+.0f} %/yr: elevated"
        else:
            sc, sig = 80.0, f"funding {funding_ann_pct:+.0f} %/yr: sane"
        comps.append(RegimeComponent("funding", "Perpetual funding", 0.15, sc, sig))
    else:
        comps.append(RegimeComponent("funding", "Perpetual funding", 0.15, None, "funding unavailable"))
    if btc.size >= 250:
        dd = 1.0 - p / float(np.max(btc[-365:]))
        r = np.diff(np.log(btc[-366:]))
        rv = np.array([np.std(r[i - 30:i]) for i in range(30, r.size)]) * math.sqrt(CRYPTO_DAYS)
        vol_pct = float(np.mean(rv <= rv[-1])) if rv.size else 0.5
        sc = 90.0 if dd < 0.10 else 70.0 if dd < 0.25 else 40.0 if dd < 0.50 else 15.0
        if vol_pct > 0.9:
            sc = max(0.0, sc - 20.0)
        comps.append(RegimeComponent("drawdown", "Drawdown & volatility position", 0.15, sc,
                                     f"{dd:.0%} below the 1-year high; 30-day vol at the {vol_pct:.0%} percentile"))
    else:
        comps.append(RegimeComponent("drawdown", "Drawdown & volatility position", 0.15, None, "insufficient history"))
    pos30 = [float(x[-1]) > float(x[-31]) for x in list(majors.values()) + [btc] if x.size >= 31]
    if pos30:
        comps.append(RegimeComponent("thrust", "30-day momentum thrust", 0.10, 100.0 * float(np.mean(pos30)),
                                     f"{np.mean(pos30):.0%} of the universe up over 30 days"))
    else:
        comps.append(RegimeComponent("thrust", "30-day momentum thrust", 0.10, None, "insufficient history"))
    live = [c for c in comps if c.score is not None]
    wsum = sum(c.weight for c in live) or 1.0
    eff = {c.key: c.weight / wsum for c in live}
    score = float(sum(c.score * eff[c.key] for c in live)) if live else float("nan")
    zone = "RISK_ON" if score >= 80 else "RISK_OFF" if score < 40 else "NEUTRAL"
    return RegimeScore(score=score, zone=zone, components=tuple(comps), effective_weights=eff,
                       as_of=as_of or date.today().isoformat())


# --------------------------------------------------------------------------- #
# ETH/BTC and weekday
# --------------------------------------------------------------------------- #
def eth_btc_test(eth: dict[str, float], btc: dict[str, float]) -> dict:
    dates, (e, b) = _align(eth, btc)
    x = np.log(e / b)
    return {"n": len(dates), "last_ratio": float(e[-1] / b[-1]), "adf_p": adf_pvalue(x),
            "half_life_days": half_life(x), "z_2y": float((x[-1] - x[-730:].mean()) / x[-730:].std(ddof=1)) if x.size > 100 else float("nan"),
            "verdict": ("mean-reverting at 5 %" if adf_pvalue(x) < 0.05 else "no rejection of a unit root (the expected null)")}


def weekday_table(dates: Sequence[str], close: np.ndarray, volume: np.ndarray) -> dict:
    r = np.diff(np.log(np.asarray(close, dtype=float)))
    wd = np.array([date.fromisoformat(d[:10]).weekday() for d in dates[1:]])
    vol = np.asarray(volume, dtype=float)[1:]
    names = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
    rows = []
    for k, nm in enumerate(names):
        m = wd == k
        if m.sum() < 5:
            continue
        rows.append({"day": nm, "n": int(m.sum()), "mean_ret_pct": float(r[m].mean() * 100),
                     "vol_pct": float(r[m].std(ddof=1) * 100), "mean_volume": float(vol[m].mean())})
    # any weekday different from the rest, Bonferroni over 7 tests
    p_min = 1.0
    for k in range(7):
        m = wd == k
        if m.sum() > 5 and (~m).sum() > 5:
            p_min = min(p_min, float(sps.ttest_ind(r[m], r[~m], equal_var=False).pvalue))
    wk = vol[wd < 5]; we = vol[wd >= 5]
    p_vol = float(sps.ttest_ind(wk, we, equal_var=False).pvalue) if we.size > 5 else float("nan")
    return {"rows": rows, "return_effect_p_bonferroni": min(1.0, p_min * 7),
            "weekend_volume_ratio": float(we.mean() / wk.mean()) if we.size and wk.size else float("nan"),
            "weekend_volume_p": p_vol}


# --------------------------------------------------------------------------- #
# GARCH-t scorecard on crypto
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class GarchScorecard:
    dates: tuple[str, ...]
    hits95: np.ndarray = field(repr=False)
    hits99: np.ndarray = field(repr=False)
    inband90: np.ndarray = field(repr=False)
    pit: np.ndarray = field(repr=False)
    qlike_garch: np.ndarray = field(repr=False)
    qlike_ewma: np.ndarray = field(repr=False)
    nonconv: np.ndarray = field(repr=False)         # solver failure at the origin's fit
    at_stationarity: np.ndarray = field(repr=False)  # the persistence guardrail bound at the fit
    nu_path: np.ndarray = field(repr=False)
    gamma_path: np.ndarray = field(repr=False)       # GJR only; zeros for the symmetric model
    lambda_path: np.ndarray = field(default_factory=lambda: np.zeros(0), repr=False)   # skew-t only
    model: str = "garch_t"
    n_refits: int = 0
    note: str = ""


def garch_scorecard(dates: Sequence[str], close: np.ndarray, *, window: int = 730, refit: int = 7,
                    start: Optional[int] = None, model: str = "garch_t") -> GarchScorecard:
    """Rolling one-day-ahead scoring of GARCH(1,1)-t (the app's fit), GJR-
    GARCH(1,1)-t (`core.quant.gjr`, the leverage challenger) or GJR with
    Hansen skewed-t innovations ("gjr_skewt", the skew challenger), refit every
    `refit` sessions on the trailing `window`, against EWMA(0.94): VaR hits,
    the 90 % band, the PIT of the realised return, QLIKE with next-day r² as
    the realised-variance proxy. A fit that sits on the stationarity guardrail
    is recorded separately from a solver failure. Everything is daily."""
    from core.quant.garch import fit_garch
    from core.quant.gjr import fit_gjr, next_variance, skewt_cdf, skewt_ppf
    if model not in ("garch_t", "gjr_t", "gjr_skewt"):
        raise ValueError("model must be 'garch_t', 'gjr_t' or 'gjr_skewt'")
    px = np.asarray(close, dtype=float)
    r = np.diff(np.log(px))
    T = r.size
    start = start or window
    if T < start + 60:
        raise ValueError(f"need at least {start + 60} returns, got {T}")
    h95, h99, band, pit, ql_g, ql_e, nc, st, nus, gam, lams, out_dates = [], [], [], [], [], [], [], [], [], [], [], []
    fit = None
    conv, at_st = True, False
    ewma_var = float(np.var(r[:start]))
    lam = 0.94
    last_sig2 = float(np.var(r[:start]))
    for t in range(start, T):
        if fit is None or (t - start) % refit == 0:
            try:
                fit = (fit_garch(r[t - window:t], dist="t", profile=False) if model == "garch_t"
                       else fit_gjr(r[t - window:t], dist="skewt" if model == "gjr_skewt" else "t"))
                conv = fit.converged
                at_st = "stationarity" in fit.at_bound
                last_sig2 = fit.cond_vol[-1] ** 2
            except Exception:
                fit, conv, at_st = None, False, False
        if fit is None:
            continue
        eps_prev = r[t - 1] - fit.mean_daily
        if model != "garch_t":
            sig2 = next_variance(fit, eps_prev, last_sig2)
        else:
            sig2 = fit.omega + fit.alpha * eps_prev ** 2 + fit.beta * last_sig2
        last_sig2 = sig2
        sig = math.sqrt(max(sig2, 1e-12))
        x = (r[t] - fit.mean_daily) / sig
        skew = float(getattr(fit, "lam", 0.0))
        if skew != 0.0:
            u = float(skewt_cdf(x, fit.nu, skew))
            q95, q99, q05, q95u = (float(skewt_ppf(q, fit.nu, skew)) for q in (0.05, 0.01, 0.05, 0.95))
        elif fit.effectively_normal:
            u = float(sps.norm.cdf(x)); q95, q99, q05, q95u = sps.norm.ppf(0.05), sps.norm.ppf(0.01), sps.norm.ppf(0.05), sps.norm.ppf(0.95)
        else:
            nu = fit.nu
            scale = math.sqrt((nu - 2.0) / nu)                # unit-variance t
            u = float(sps.t.cdf(x / scale, nu))
            q95, q99, q05, q95u = (sps.t.ppf(q, nu) * scale for q in (0.05, 0.01, 0.05, 0.95))
        h95.append(x <= q95); h99.append(x <= q99); band.append(q05 <= x <= q95u); pit.append(u)
        rv = r[t] ** 2
        ql_g.append(rv / sig2 - math.log(rv / sig2 + 1e-18) - 1.0)
        ql_e.append(rv / ewma_var - math.log(rv / ewma_var + 1e-18) - 1.0)
        ewma_var = lam * ewma_var + (1 - lam) * r[t] ** 2
        nc.append(not conv and not at_st); st.append(at_st)
        nus.append(fit.nu if not fit.effectively_normal else math.inf)
        gam.append(getattr(fit, "gamma", 0.0))
        lams.append(skew)
        out_dates.append(dates[t + 1])
    return GarchScorecard(dates=tuple(out_dates), hits95=np.asarray(h95), hits99=np.asarray(h99), inband90=np.asarray(band),
                          pit=np.asarray(pit), qlike_garch=np.asarray(ql_g), qlike_ewma=np.asarray(ql_e),
                          nonconv=np.asarray(nc), at_stationarity=np.asarray(st), nu_path=np.asarray(nus),
                          gamma_path=np.asarray(gam), lambda_path=np.asarray(lams), model=model, n_refits=int(math.ceil((T - start) / refit)),
                          note=f"{model}: window {window}, refit every {refit} sessions, {T - start} one-day origins")


# --------------------------------------------------------------------------- #
# Self-check (synthetic)
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    rng = np.random.default_rng(4)
    n = 900
    ds = [str(np.datetime64("2023-01-01") + np.timedelta64(i, "D")) for i in range(n)]
    us = 30000 * np.exp(np.cumsum(rng.normal(0.0005, 0.03, n)))
    fx = 1350 + np.cumsum(rng.normal(0, 3, n))
    prem_true = np.zeros(n)
    for t in range(1, n):
        prem_true[t] = 0.9 * prem_true[t - 1] + rng.normal(0, 0.3)
    kr = us * fx * (1 + prem_true / 100)
    kp = kimchi_premium(dict(zip(ds, kr)), dict(zip(ds, us)), {d: v for d, v in zip(ds, fx) if date.fromisoformat(d).weekday() < 5})
    assert kp.n > 800 and abs(kp.mean_pct - prem_true.mean()) < 0.3 and kp.adf_p < 0.05 and 3 < kp.half_life_days < 15
    assert math.isfinite(kp.pred_t)
    fund = {d: float(v) for d, v in zip(ds, rng.normal(0.0003, 0.0005, n))}
    fc = funding_carry(fund, dict(zip(ds, us)))
    assert fc.n == n and math.isfinite(fc.last_ann_pct) and 0 <= fc.percentile <= 1 and fc.flag in ("normal", "crowded long", "crowded short")
    majors = {k: 100 * np.exp(np.cumsum(rng.normal(0.001, 0.04, 400))) for k in ("ETH", "SOL", "XRP", "BNB")}
    rs = regime_score(us[-400:], majors, funding_ann_pct=8.0, dominance_30d_change=-0.01)
    assert 0 <= rs.score <= 100 and rs.zone in ("RISK_ON", "NEUTRAL", "RISK_OFF") and abs(sum(rs.effective_weights.values()) - 1) < 1e-9
    rs2 = regime_score(us[-400:], majors)
    assert rs2.components[2].score is None and rs2.components[3].score is None and abs(sum(rs2.effective_weights.values()) - 1) < 1e-9
    down = 100 * np.exp(np.cumsum(rng.normal(-0.004, 0.03, 400)))
    assert regime_score(down, {"ETH": down}).score < regime_score(100 * np.exp(np.cumsum(rng.normal(0.004, 0.02, 400))), {"ETH": majors["ETH"]}).score
    eb = eth_btc_test(dict(zip(ds, majors["ETH"].tolist() * 3)) if False else dict(zip(ds[:400], majors["ETH"])), dict(zip(ds[:400], us[:400])))
    assert eb["n"] == 400 and eb["verdict"]
    wt = weekday_table(ds, us, rng.random(n) * 100 + (np.array([date.fromisoformat(d).weekday() < 5 for d in ds]) * 50))
    assert len(wt["rows"]) == 7 and wt["weekend_volume_ratio"] < 1.0 and wt["weekend_volume_p"] < 0.01
    from core.quant.garch import simulate_garch_series
    r = simulate_garch_series(2e-5, 0.08, 0.90, 5.0, n=1400, seed=3)
    px = 100 * np.exp(np.cumsum(r))
    sc = garch_scorecard([str(np.datetime64("2021-01-01") + np.timedelta64(i, "D")) for i in range(px.size)], px,
                         window=600, refit=20, start=600)
    assert sc.hits95.size > 700 and 0.02 < sc.hits95.mean() < 0.09 and sc.pit.min() >= 0 and sc.pit.max() <= 1
    assert np.mean(sc.qlike_garch) < np.mean(sc.qlike_ewma) + 0.05, (np.mean(sc.qlike_garch), np.mean(sc.qlike_ewma))
    assert sc.at_stationarity.size == sc.hits95.size and not np.any(sc.nonconv & sc.at_stationarity)
    sg = garch_scorecard([str(np.datetime64("2021-01-01") + np.timedelta64(i, "D")) for i in range(px.size)], px,
                         window=600, refit=40, start=600, model="gjr_t")
    assert sg.model == "gjr_t" and sg.hits95.size == sc.hits95.size and np.all(sg.gamma_path >= 0)
    print("ok")
