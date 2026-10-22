"""Portfolio construction: Markowitz frontier, max-Sharpe, min-vol, risk parity.

scipy's SLSQP does the constrained optimization (long-only, fully invested,
optional per-asset cap). Risk parity is solved on the same machinery by
minimizing the dispersion of risk contributions. The efficient frontier is
traced by sweeping target returns between the min-vol portfolio's return and
the best single asset's, minimizing volatility at each stop.

Every optimizer starts from equal weights and the result reports whether the
solver actually converged — a portfolio built on a failed optimization is
worse than no portfolio, so `converged=False` is surfaced, never swallowed.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from scipy.optimize import minimize

from core.quant.risk import BasketStats, portfolio_point

OBJECTIVES = ("max_sharpe", "min_vol", "risk_parity", "equal_weight")


@dataclass(frozen=True)
class OptimizedPortfolio:
    objective: str
    symbols: tuple[str, ...]
    weights: np.ndarray = field(repr=False, default=None)
    ann_return: float = 0.0
    ann_vol: float = 0.0
    sharpe: float = 0.0
    converged: bool = True
    note: str = ""
    risk_contrib: np.ndarray = field(repr=False, default=None)  # fraction of total risk


@dataclass(frozen=True)
class Frontier:
    vols: np.ndarray = field(repr=False, default=None)
    rets: np.ndarray = field(repr=False, default=None)
    cloud_vols: np.ndarray = field(repr=False, default=None)    # random portfolios
    cloud_rets: np.ndarray = field(repr=False, default=None)
    cloud_sharpes: np.ndarray = field(repr=False, default=None)


def _risk_contributions(w: np.ndarray, cov: np.ndarray) -> np.ndarray:
    port_var = float(w @ cov @ w)
    if port_var <= 0:
        return np.full_like(w, 1.0 / w.size)
    marginal = cov @ w
    return w * marginal / port_var


def _solve(objective_fn, n: int, *, cap: float) -> tuple[np.ndarray, bool]:
    w0 = np.full(n, 1.0 / n)
    bounds = [(0.0, cap)] * n
    cons = [{"type": "eq", "fun": lambda w: np.sum(w) - 1.0}]
    res = minimize(objective_fn, w0, method="SLSQP", bounds=bounds,
                   constraints=cons, options={"maxiter": 500, "ftol": 1e-10})
    w = np.clip(res.x, 0.0, cap)
    s = w.sum()
    if s > 0:
        w = w / s
    return w, bool(res.success)


def optimize_portfolio(stats: BasketStats, *, objective: str = "max_sharpe",
                       rf_rate: float = 0.03, max_weight: float = 1.0) -> OptimizedPortfolio:
    objective = (objective or "max_sharpe").lower()
    if objective not in OBJECTIVES:
        raise ValueError(f"Unknown objective {objective!r}. One of {OBJECTIVES}.")
    n = len(stats.symbols)
    cap = float(min(max(max_weight, 1.0 / n + 1e-9), 1.0))
    mu, cov = stats.mean_returns, stats.cov

    note = ""
    if objective == "equal_weight":
        w, ok = np.full(n, 1.0 / n), True
    elif objective == "min_vol":
        w, ok = _solve(lambda w: w @ cov @ w, n, cap=cap)
    elif objective == "max_sharpe":
        def neg_sharpe(w):
            vol = np.sqrt(max(w @ cov @ w, 1e-12))
            return -((w @ mu - rf_rate) / vol)
        w, ok = _solve(neg_sharpe, n, cap=cap)
    else:  # risk_parity
        def rc_dispersion(w):
            rc = _risk_contributions(np.clip(w, 1e-9, None), cov)
            return float(np.sum((rc - 1.0 / n) ** 2))
        w, ok = _solve(rc_dispersion, n, cap=cap)
        note = "Weights equalize each asset's contribution to portfolio risk."

    ret, vol, sharpe = portfolio_point(w, stats, rf_rate=rf_rate)
    if not ok:
        note = (note + " " if note else "") + "Solver did not report convergence; treat weights as approximate."
    return OptimizedPortfolio(objective=objective, symbols=stats.symbols,
                              weights=w, ann_return=ret, ann_vol=vol,
                              sharpe=sharpe, converged=ok, note=note.strip(),
                              risk_contrib=_risk_contributions(w, cov))


def efficient_frontier(stats: BasketStats, *, points: int = 25,
                       rf_rate: float = 0.03, n_cloud: int = 1500,
                       seed: int = 11) -> Frontier:
    n = len(stats.symbols)
    mu, cov = stats.mean_returns, stats.cov

    lo = optimize_portfolio(stats, objective="min_vol", rf_rate=rf_rate)
    hi_ret = float(np.max(mu))
    targets = np.linspace(lo.ann_return, hi_ret, points)
    vols, rets = [], []
    for t in targets:
        cons = [{"type": "eq", "fun": lambda w: np.sum(w) - 1.0},
                {"type": "eq", "fun": lambda w, t=t: w @ mu - t}]
        res = minimize(lambda w: w @ cov @ w, np.full(n, 1.0 / n),
                       method="SLSQP", bounds=[(0.0, 1.0)] * n,
                       constraints=cons, options={"maxiter": 300, "ftol": 1e-10})
        if res.success:
            vols.append(float(np.sqrt(max(res.fun, 0.0))))
            rets.append(float(t))

    rng = np.random.default_rng(seed)
    raw = rng.dirichlet(np.ones(n), size=n_cloud)
    c_rets = raw @ mu
    c_vols = np.sqrt(np.maximum(np.einsum("ij,jk,ik->i", raw, cov, raw), 0.0))
    with np.errstate(divide="ignore", invalid="ignore"):
        c_sharpe = np.where(c_vols > 0, (c_rets - rf_rate) / c_vols, 0.0)

    return Frontier(vols=np.array(vols), rets=np.array(rets),
                    cloud_vols=c_vols, cloud_rets=c_rets, cloud_sharpes=c_sharpe)


# --------------------------------------------------------------------------- #
# R-15 cross-market base weights (v2.0, M4): inverse vol on weekly returns, EWMA lambda 0.97 acting,
# a Ledoit-Wolf 156-week line printed beside it (L858-859, L1716). Never routed through optimize_portfolio:
# no HRP, no minimum variance, no renormalisation of a sleeve budget.
# --------------------------------------------------------------------------- #
IV_COV = "ewma_weekly_0.97"
IV_SERIES = {"KR": "KOSPI_OFFICIAL_CLOSE", "US": "SPX_OFFICIAL_CLOSE", "JP": "NIKKEI225_CLOSE",
             "CN": "SHANGHAI_CLOSE", "HK": "HSI_CLOSE", "TW": "TAIEX_CLOSE"}   # IV_m input per market (F-14, judgment)
IV_CONSUMER = "R-15"


def weekly_returns(dates, values) -> np.ndarray:
    """Simple returns between the last observation of consecutive ISO weeks (F-14)."""
    last: dict[tuple[int, int], float] = {}
    for d, v in zip(dates, values):
        last[d.isocalendar()[:2]] = float(v)
    px = np.array([last[k] for k in sorted(last)], dtype=float)
    return px[1:] / px[:-1] - 1.0 if px.size > 1 else np.zeros(0)


def ewma_sigma(r: np.ndarray, lam: float = 0.97, *, seed_n: int = 26) -> float:
    """Zero-mean EWMA sigma of a return series: var_t = lam var_{t-1} + (1-lam) r_t^2, seeded with the sample
    variance of the first `seed_n` observations (F-14)."""
    r = np.asarray(r, dtype=float)
    r = r[np.isfinite(r)]
    if r.size < 2:
        return float("nan")
    var = float(np.var(r[:seed_n], ddof=1)) if r.size >= 2 else float(r[0] ** 2)
    for x in r[min(seed_n, r.size):]:
        var = lam * var + (1.0 - lam) * float(x) ** 2
    return float(np.sqrt(var))


def inverse_vol_from_sigmas(sigmas: dict[str, float]) -> dict[str, float]:
    """IV_m = (1/sigma_m) / sum_k (1/sigma_k); one market -> {m: 1.0}; none -> {}. A non-finite or zero sigma raises."""
    if not sigmas:
        return {}
    inv = {}
    for m, s in sigmas.items():
        if not (np.isfinite(s) and s > 0):
            raise ValueError(f"inverse_vol: sigma of {m} is {s!r}")
        inv[m] = 1.0 / float(s)
    tot = sum(inv.values())
    out = {m: v / tot for m, v in inv.items()}
    assert abs(sum(out.values()) - 1.0) < 1e-12 and all(0.0 < w <= 1.0 for w in out.values())
    return out


def inverse_vol_from_weekly(weekly: dict[str, np.ndarray], lam: float = 0.97) -> dict[str, float]:
    return inverse_vol_from_sigmas({m: ewma_sigma(r, lam) for m, r in weekly.items()})


def ledoit_wolf_cov(X: np.ndarray) -> np.ndarray:
    """Ledoit-Wolf (2004) shrinkage toward scaled identity, numpy only (sklearn is absent); printed, never acting."""
    X = np.asarray(X, dtype=float)
    n, p = X.shape
    Xc = X - X.mean(axis=0)
    S = Xc.T @ Xc / n
    mu = np.trace(S) / p
    F = mu * np.eye(p)
    d2 = float(np.sum((S - F) ** 2)) / p
    b2 = sum(float(np.sum((np.outer(x, x) - S) ** 2)) for x in Xc) / (n * n * p)
    shrink = min(1.0, b2 / d2) if d2 > 0 else 1.0
    return shrink * F + (1.0 - shrink) * S


def ledoit_wolf_line(weekly: dict[str, np.ndarray], weeks: int = 156) -> tuple[dict[str, float], str]:
    """Inverse-vol weights from the diagonal of the LW covariance of the last `weeks` weekly returns (printed only)."""
    if not weekly:
        return {}, "LW-156w: no markets"
    names = sorted(weekly)
    n = min(len(weekly[m]) for m in names)
    if n < 2:
        return {}, "LW-156w: insufficient weekly history"
    X = np.column_stack([np.asarray(weekly[m], dtype=float)[-min(n, weeks):] for m in names])
    cov = ledoit_wolf_cov(X)
    iv = inverse_vol_from_sigmas({m: float(np.sqrt(cov[i, i])) for i, m in enumerate(names)})
    return iv, "LW-156w (printed, not acting): " + ", ".join(f"{m} {iv[m]:.4f}" for m in names)


def inverse_vol_weights(markets, decision_utc, cov: str = IV_COV, *, store=None, knowledge_utc=None, weekly=None,
                        series=None, registry=None, sessions=None, lam: float = 0.97, min_weeks: int = 52,
                        consumer: str = IV_CONSUMER):
    """IV_m over `markets` (R-15, L1716). Acting path: every market's registered close series is read through
    `pit_value` (the binding check, latest official close of the decided session) and `pit_window` (official closes
    only); weekly simple returns on the last session of each ISO week; EWMA lambda 0.97. `weekly` (market -> weekly
    returns) bypasses the store for tests and research. Returns `dict[market, float]` with sum 1, or a `MissingInput`
    (fail closed: the caller carries its previous base weights). `cov` other than the registered acting line raises."""
    if cov != IV_COV:
        raise ValueError(f"inverse_vol_weights: cov {cov!r} is not the acting line {IV_COV!r} (no HRP, no min-variance)")
    markets = list(markets)
    if not markets:
        return {}
    if weekly is None:
        from core.ficc import pit as P                   # lazy: optimize.py stays importable without the data layer
        if store is None or knowledge_utc is None:
            raise ValueError("inverse_vol_weights: a PIT store and knowledge_utc are required without `weekly`")
        series = dict(IV_SERIES, **(series or {}))
        weekly = {}
        for m in markets:
            sid = series.get(m)
            if sid is None:
                return P.MissingInput(f"IV:{m}", "missing", "acting_exposure", (), detail=f"no IV_m input registered for {m}")
            session = (sessions or {}).get(m) or decision_utc.date()
            try:
                latest = P.pit_value(store, sid, decision_utc, knowledge_utc, consumer, session, registry=registry)
            except P.UnboundConsumer as exc:             # F-14: no acting binding -> no IV, fail closed with a name
                return P.MissingInput(sid, "missing", "acting_exposure", (), detail=str(exc))
            if isinstance(latest, P.MissingInput):
                return latest
            rows = P.pit_window(store, sid, decision_utc, knowledge_utc, registry=registry, statuses=("official_close",))
            r = weekly_returns([v.obs_date for v in rows], [v.value for v in rows])
            if r.size < min_weeks:
                return P.MissingInput(sid, "missing", latest.role, latest.books,
                                      detail=f"{r.size} weekly returns < {min_weeks} (IV_m warm-up)")
            weekly[m] = r
    weekly = {m: np.asarray(weekly[m], dtype=float) for m in markets}
    return inverse_vol_from_weekly(weekly, lam)
