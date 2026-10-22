"""Offline check: does the 'rf' drift mode make E[P_T] = spot*exp(rf*T) for every model?
Does the 'premium' mode deliver an arithmetic growth of rf+ERP? Uses a synthetic clustered series."""
import math, numpy as np
from core.quant.history import History
from core.quant.garch import simulate_garch_series, fit_garch, horizon_vol
from core.quant.montecarlo import run_monte_carlo, TRADING_DAYS

eps = simulate_garch_series(2e-6, 0.08, 0.90, 6.0, n=1000, seed=3)
r = eps + 0.0004
px = 100.0 * np.exp(np.cumsum(r))
dates = tuple(f"d{i:04d}" for i in range(px.size))
hist = History(symbol="SYN", source="SYNTHETIC", dates=dates, closes=tuple(float(x) for x in px))
H = 126; T = H / TRADING_DAYS; rf = 0.03; erp = 0.04
fit = fit_garch(hist.log_returns(), dist="t")
sample_vol = float(np.std(hist.log_returns(), ddof=1)) * math.sqrt(TRADING_DAYS)
print(f"fit: {fit.note}")
print(f"sample vol {sample_vol:.3%} | cond vol T+1 {fit.cond_vol_last:.3%} | horizon vol {horizon_vol(fit, H):.3%} | uncond {fit.uncond_vol:.3%}")
for mode, target in (("rf", math.exp(rf * T)), ("premium", math.exp((rf + erp) * T))):
    for model in ("gbm", "garch_t", "jump", "bootstrap"):
        m = []
        for seed in (7, 8, 9):
            mc = run_monte_carlo(hist, model=model, n_paths=100_000, horizon_days=H, drift=mode,
                                 rf_rate=rf, erp=erp, seed=seed)
            m.append(mc.mean_terminal / mc.spot)
        m = np.array(m)
        print(f"{mode:8s} {model:10s} E[P_T]/spot = {m.mean():.5f} (+/- {m.std(ddof=1):.5f} over seeds)  target {target:.5f}  gap {(m.mean()-target)*100:+.2f} pts")
# nesting check: t-GARCH vs normal-GARCH on an iid normal series
g = fit_garch(np.random.default_rng(2).normal(0.0004, 0.012, 500), dist="t")
print(f"iid-normal series: LR t vs normal = {g.lr_t_vs_normal:+.3f}, nu = {g.nu:.1f}, at_bound = {g.at_bound}")
