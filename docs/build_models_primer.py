"""Build docs/QUANTGEN_Models_Primer.pdf — the teaching document for the Quant Lab.

Run from the project root:  python docs/build_models_primer.py

Every fitted or simulated number in the PDF is computed here, at build time, by
calling the same functions the app calls (core/quant/garch.py and
core/quant/montecarlo.py), so the document and the app cannot disagree. The
drift-study tables are read from docs/drift_study/results.csv, never retyped.

Data: AAPL from FMP when FMP_API_KEY is set and the network answers; otherwise
(or with PRIMER_OFFLINE=1) a synthetic GARCH(1,1)-t series from
core.quant.garch.simulate_garch_series, labelled as such in every caption.
The app's own no-key demo series, synthetic_history("AAPL"), is always used
for the "guardrail binds" example because it is a GBM path and shows exactly
what a bound-sitting fit looks like.

Typography: DejaVu fonts from matplotlib's bundle (Helvetica has no Greek);
sub/superscripts are <sub>/<super> tags, never Unicode glyphs; English only. Display
formulas (F) are LaTeX math typeset by matplotlib's mathtext in Computer Modern and placed
as images, so no TeX installation is needed. PRIMER_END_DATE=YYYY-MM-DD rebuilds the
document on the data window ending that day (the same 504 sessions as an earlier build).
"""
from __future__ import annotations

import csv
import hashlib
import math
import os
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import figure as mfigure
from matplotlib import gridspec
from matplotlib.font_manager import FontProperties
from matplotlib.mathtext import MathTextParser
from scipy import stats as sps

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (BaseDocTemplate, CondPageBreak, Frame, Image, KeepTogether, PageBreak,
                                PageTemplate, Paragraph, Preformatted, Spacer, Table,
                                TableStyle)
from reportlab.platypus.tableofcontents import TableOfContents

import config
from core.quant import garch as G
from core.quant import insights
from core.quant.garch import (BOUNDS, LR_5PCT, NU_NORMAL, STATIONARITY_MAX, TRADING_DAYS, Z95, Z_BOUND,
                              fit_garch, forecast_variance, simulate_garch_series)
from core.quant.history import History, fmp_history, synthetic_history
from core.quant.montecarlo import DRIFTS, FAN_PERCENTILES, MODELS, run_monte_carlo
from ui.quant_lab_page import _garch_blocks, _study_chips

ETA_MAX = BOUNDS["eta"][1]                            # the tail is fitted as eta = 1/nu on [0, ETA_MAX]
NU_MIN = BOUNDS["nu"][0]                              # ETA_MAX is nu = NU_MIN; eta = 0 is the normal
PROFILE_CUT, PROFILE_CUT0 = G._PROFILE_CUT, G._PROFILE_CUT0

T0 = time.time()
DOCS = ROOT / "docs"
FIG_DIR = DOCS / "primer_figures"
STUDY = DOCS / "drift_study"
OUT_PDF = DOCS / "QUANTGEN_Models_Primer.pdf"
FIG_DIR.mkdir(parents=True, exist_ok=True)

HORIZON, N_PATHS, SEED = 126, 5000, 7
_UI_SRC = (ROOT / "ui" / "quant_lab_page.py").read_text(encoding="utf-8")
RF = float(re.search(r"_RF_ASSUMED\s*=\s*([\d.]+)", _UI_SRC).group(1))          # the app's fallback rf
ERP = float(re.search(r'label="ERP %",\s*value="([\d.]+)"', _UI_SRC).group(1)) / 100.0
DRIFT_LABELS = dict(re.findall(r'\("(\w+)",\s*"([^"]+)"\)', _UI_SRC.split("_DRIFTS = [")[1].split("]")[0]))

# --------------------------------------------------------------------------- #
# Fonts
# --------------------------------------------------------------------------- #
_FONT_DIR = os.path.join(os.path.dirname(matplotlib.__file__), "mpl-data", "fonts", "ttf")
for name, file in (("DejaVuSans", "DejaVuSans.ttf"), ("DejaVuSans-Bold", "DejaVuSans-Bold.ttf"),
                   ("DejaVuSans-Oblique", "DejaVuSans-Oblique.ttf"),
                   ("DejaVuSans-BoldOblique", "DejaVuSans-BoldOblique.ttf"),
                   ("DejaVuSansMono", "DejaVuSansMono.ttf"), ("DejaVuSerif", "DejaVuSerif.ttf")):
    pdfmetrics.registerFont(TTFont(name, os.path.join(_FONT_DIR, file)))
pdfmetrics.registerFontFamily("DejaVuSans", normal="DejaVuSans", bold="DejaVuSans-Bold",
                              italic="DejaVuSans-Oblique", boldItalic="DejaVuSans-BoldOblique")
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 8, "axes.titlesize": 9,
                     "axes.labelsize": 8, "legend.fontsize": 7.5, "figure.dpi": 150,
                     "axes.grid": True, "grid.alpha": 0.3, "grid.linewidth": 0.5,
                     "axes.spines.top": False, "axes.spines.right": False})
FIG_W = 15 / 2.54                                     # 15 cm in inches
C_MAIN, C_ALT, C_GREY, C_RED, C_GREEN = "#1f4e79", "#c0504d", "#7f7f7f", "#b22222", "#2e7d32"


# --------------------------------------------------------------------------- #
# Data and every number the text quotes
# --------------------------------------------------------------------------- #
def _garch_synthetic_history(n: int = 1500, seed: int = 11) -> History:
    """Price path from the same generator, parameters and seed the acceptance tests
    use (omega 2e-6, alpha 0.08, beta 0.90, nu 6; 1,500 sessions, seed 11): clustering
    and fat tails are guaranteed, and the fit recovers the parameters cleanly."""
    from datetime import date, timedelta
    r = simulate_garch_series(2e-6, 0.08, 0.90, 6.0, n=n, seed=seed)
    closes = tuple(float(x) for x in 100.0 * np.exp(np.concatenate([[0.0], np.cumsum(r)])))
    d0 = date(2024, 1, 1)
    dates = tuple((d0 + timedelta(days=i)).isoformat() for i in range(len(closes)))
    return History(symbol="SYN-GARCH", source="SYNTHETIC", dates=dates, closes=closes,
                   note="simulate_garch_series(2e-6, 0.08, 0.90, 6.0, n=%d, seed=%d)" % (n, seed))


def load_primary() -> tuple[History, str, bool]:
    if not os.environ.get("PRIMER_OFFLINE") and config.fmp_key():
        try:
            end = os.environ.get("PRIMER_END_DATE")      # rebuild an earlier document on its own window
            h = fmp_history("AAPL", days=504 + 40 if end else 504)
            if end:
                n = sum(d <= end for d in h.dates)
                h = History(h.symbol, h.source, h.dates[n - 504:n], h.closes[n - 504:n])
            return h, (f"AAPL daily closes from FMP, {len(h)} sessions, "
                       f"{h.first_date} to {h.last_date}"), True
        except Exception as exc:                       # network absent, plan limit, anything
            print(f"FMP unavailable ({type(exc).__name__}: {exc}); using the synthetic fallback")
    h = _garch_synthetic_history()
    return h, (f"synthetic GARCH(1,1)-t series from core.quant.garch.{h.note}, "
               f"{len(h)} sessions; no market data was used"), False


def acf(x: np.ndarray, lag: int) -> float:
    return float(np.corrcoef(x[:-lag], x[lag:])[0, 1])


def _profile_curve(r: np.ndarray, fit) -> np.ndarray:
    """The profile log-likelihood in eta on the app's full grid: ln L re-maximised
    over (omega, alpha, beta) at each eta, warm-started from the previous point.
    The app's own scan (`_profile_eta`) stops early; the figure wants every point."""
    eps = r - fit.mean_daily
    eps2, var = eps ** 2, float(np.var(eps))
    joint = np.array([fit.omega, fit.alpha, fit.beta])
    start = joint.copy()
    out = np.empty(G._PROFILE_GRID.size)
    for i, g in enumerate(G._PROFILE_GRID):
        out[i], start = G._fit_fixed_eta(eps, eps2, var, float(g), (start, joint))
    return out


def tile_texts(fit, hvol: float) -> tuple[dict[str, str], list[str]]:
    """The GARCH stat strip and chip row exactly as ui/quant_lab_page.py builds
    them: {tile label: value text}, [chip text]. Chapter 9 quotes these, so the
    document cannot disagree with the screen."""
    strip, row = _garch_blocks(fit, hvol)
    tiles = {c.content.controls[0].value: c.content.controls[1].value for c in strip.controls}
    study = {c.content.value for c in _study_chips()}   # the asset-expansion chips: Expansion Primer, not here
    return tiles, [c.content.value for c in row.controls if c.content.value not in study]


def _compute():
    """Everything computed once; the chapters only format these."""
    from types import SimpleNamespace
    H, SRC, REAL = load_primary()
    r = H.log_returns()
    T = r.size
    mu_d, sd_d = float(np.mean(r)), float(np.std(r, ddof=1))
    mu_a, sd_a = mu_d * TRADING_DAYS, sd_d * math.sqrt(TRADING_DAYS)
    z = (r - mu_d) / r.std()
    kurt, skew = float(np.mean(z ** 4) - 3), float(np.mean(z ** 3))
    acf_r1 = acf(r, 1)
    acf_sq = {k: acf(r ** 2, k) for k in (1, 5, 20)}
    rv20 = np.sqrt(np.convolve(r ** 2, np.ones(20) / 20, mode="valid") * TRADING_DAYS)
    fit = fit_garch(r, dist="t")
    fit_n = fit_garch(r, dist="normal")
    z_g = (r - fit.mean_daily) / fit.cond_vol
    kurt_g = float(np.mean(((z_g - z_g.mean()) / z_g.std()) ** 4) - 3)
    fv252 = forecast_variance(fit, 252)
    # the app's own no-key demo series: a GBM path, so GARCH has nothing to find
    H_demo = synthetic_history("AAPL")
    fit_demo = fit_garch(H_demo.log_returns(), dist="t")
    # Monte Carlo runs the chapters quote
    mc = {m: run_monte_carlo(H, model=m, n_paths=N_PATHS, horizon_days=HORIZON, seed=SEED,
                             drift="premium", rf_rate=RF, erp=ERP) for m in MODELS}
    mc_drift = {d: run_monte_carlo(H, model="garch_t", n_paths=N_PATHS, horizon_days=HORIZON,
                                   seed=SEED, drift=d, rf_rate=RF, erp=ERP) for d in DRIFTS}
    mc_g, mc_gbm = mc["garch_t"], mc["gbm"]
    hvol = mc_g.garch_horizon_vol                      # as the tile shows it (bounded-innovation variance)
    narrative = insights.narrate_monte_carlo(mc_g)
    tiles, chips = tile_texts(fit, hvol)               # chapter 9.3, straight from the UI code
    _, chips_demo = tile_texts(fit_demo, 0.0)
    # Monte Carlo standard error: the same GBM run over 20 seeds at two path counts
    se = {}
    for n in (500, 5000):
        runs = [run_monte_carlo(H, model="gbm", n_paths=n, horizon_days=HORIZON, seed=s,
                                drift="premium", rf_rate=RF, erp=ERP) for s in range(20)]
        se[n] = (float(np.std([x.median_terminal for x in runs], ddof=1)),
                 float(np.std([x.var_pct for x in runs], ddof=1)),
                 float(np.std([x.cvar_pct for x in runs], ddof=1)))
    # likelihood slices for figure 6
    eps = r - fit.mean_daily
    var0 = float(np.var(eps))
    eta_hat = 0.0 if math.isinf(fit.nu) else 1.0 / fit.nu   # _loglik takes eta, not nu (B1)
    beta_grid = np.linspace(0.30, 0.999, 400)
    ll_beta = np.array([G._loglik(np.array([fit.omega, fit.alpha, b, eta_hat]), eps, eps ** 2,
                                  var0, "t") for b in beta_grid])
    # the profile log-likelihood in eta on the full grid, both series (figure 6, chapter 6.5)
    eta_grid = G._PROFILE_GRID
    prof_eta = _profile_curve(r, fit)
    prof_eta_demo = _profile_curve(H_demo.log_returns(), fit_demo)
    # drift-study reading numbers that live only in results.md
    _md = (STUDY / "results.md").read_text(encoding="utf-8")
    corr_sample = re.search(r"12-month return is ([+-]?\d\.\d+)", _md).group(1)
    se_25_2y = 0.25 / math.sqrt(2)
    return SimpleNamespace(**{k: v for k, v in locals().items() if not k.startswith("_")})


D = _compute()
print(f"data: {D.SRC}")
print(f"fit: {D.fit.note}")
print(f"demo fit: {D.fit_demo.note}")


# --------------------------------------------------------------------------- #
# Figures
# --------------------------------------------------------------------------- #
def _save(fig, name: str) -> str:
    path = FIG_DIR / name
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return str(path)


def fig1() -> str:
    px, r = D.H.prices(), D.r
    fig, ax = plt.subplots(3, 1, figsize=(FIG_W, 5.2), sharex=True,
                           gridspec_kw={"height_ratios": [1.2, 1, 1]})
    x = np.arange(px.size)
    ax[0].plot(x, px, color=C_MAIN, lw=1); ax[0].set_ylabel("close")
    ax[1].bar(x[1:], r * 100, color=C_MAIN, width=1.0); ax[1].set_ylabel("log return, %")
    ax[2].plot(x[20:], D.rv20 * 100, color=C_ALT, lw=1, label="20-session realised vol")
    ax[2].axhline(D.sd_a * 100, color=C_GREY, ls="--", lw=0.9, label="full-sample vol")
    ax[2].set_ylabel("annualised vol, %"); ax[2].set_xlabel("session"); ax[2].legend(loc="upper left")
    ax[0].set_title(f"{D.H.symbol}: price, daily log returns, rolling vol", loc="left")
    fig.align_ylabels(ax)
    return _save(fig, "fig1_returns_vol.png")


def _t_unit_pdf(x, nu):
    s = math.sqrt(nu / (nu - 2))                  # unit-variance t: pdf_t(x s) s
    return sps.t.pdf(x * s, nu) * s


def fig2() -> str:
    fig, ax = plt.subplots(1, 2, figsize=(FIG_W, 2.9))
    grid = np.linspace(-6, 6, 400)
    for a, z, title in ((ax[0], D.z, "raw returns / sample vol"),
                        (ax[1], (D.z_g - D.z_g.mean()) / D.z_g.std(),
                         "GARCH residuals eps / sigma_t")):
        a.hist(z, bins=60, density=True, color=C_MAIN, alpha=0.55, label="data")
        a.plot(grid, sps.norm.pdf(grid), color=C_GREY, lw=1.2, label="normal")
        a.plot(grid, _t_unit_pdf(grid, D.fit.nu), color=C_ALT, lw=1.2,
               label=f"t, nu = {D.fit.nu:.1f} (unit variance)")
        a.set_yscale("log"); a.set_ylim(1e-4, 1); a.set_xlim(-6, 6)
        a.set_title(title, loc="left"); a.set_xlabel("standard deviations")
    ax[0].set_ylabel("density (log scale)")
    handles, labels = ax[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=3, frameon=False,
               bbox_to_anchor=(0.5, -0.06))
    fig.tight_layout()
    return _save(fig, "fig2_tails.png")


def fig3() -> str:
    fig, ax = plt.subplots(figsize=(FIG_W, 3.0))
    x = np.arange(D.T)
    ax.plot(x, D.fit.cond_vol * math.sqrt(TRADING_DAYS) * 100, color=C_MAIN, lw=1.1,
            label="GARCH(1,1)-t conditional vol sigma_t")
    ax.plot(x[19:], D.rv20 * 100, color=C_ALT, lw=0.9, alpha=0.9, label="20-session realised vol")
    if math.isfinite(D.fit.uncond_vol):
        ax.axhline(D.fit.uncond_vol * 100, color=C_GREY, ls="--", lw=1,
                   label=f"unconditional {D.fit.uncond_vol * 100:.1f}%")
    ax.plot([D.T], [D.fit.cond_vol_last * 100], "o", color=C_MAIN, ms=4,
            label=f"next-session forecast {D.fit.cond_vol_last * 100:.1f}%")
    ax.set_ylabel("annualised vol, %"); ax.set_xlabel("session"); ax.legend(loc="upper left", ncol=2)
    ax.set_title(f"{D.H.symbol}: conditional vs realised vol (alpha {D.fit.alpha:.3f}, "
                 f"beta {D.fit.beta:.3f})", loc="left")
    return _save(fig, "fig3_cond_vol.png")


def fig4() -> str:
    fig, ax = plt.subplots(figsize=(FIG_W, 3.0))
    h = np.arange(1, 253)
    uncond = 0.20 ** 2 / TRADING_DAYS
    start = 0.32 ** 2 / TRADING_DAYS
    for p, c in ((0.90, C_ALT), (0.99, C_MAIN)):
        omega = uncond * (1 - p)
        s2, out = start, []
        for _ in h:
            out.append(s2); s2 = omega + p * s2
        out = np.sqrt(np.array(out) * TRADING_DAYS) * 100
        hl = math.log(0.5) / math.log(p)
        ax.plot(h, out, color=c, lw=1.3, label=f"alpha+beta = {p:.2f}: half-life {hl:.1f} sessions")
        ax.axvline(hl, color=c, ls=":", lw=0.8)
    fv = np.sqrt(D.fv252 * TRADING_DAYS) * 100
    ax.plot(h, fv, color=C_GREEN, lw=1.1, ls="--",
            label=f"this fit: alpha+beta = {D.fit.persistence:.3f}, half-life {D.fit.half_life:.1f}")
    ax.axhline(20, color=C_GREY, lw=0.8, ls="--", label="unconditional 20% (illustrative curves)")
    ax.set_xlabel("h sessions ahead"); ax.set_ylabel("forecast vol sqrt(sigma^2_T+h x 252), %")
    ax.set_title("Variance forecast term structure converging to omega / (1 - alpha - beta)", loc="left")
    ax.legend(loc="upper right")
    return _save(fig, "fig4_term_structure.png")


def fig5() -> str:
    fig = plt.figure(figsize=(FIG_W, 5.6))
    gs = gridspec.GridSpec(2, 2, height_ratios=[1.15, 1], figure=fig)
    px = D.H.prices()[-90:]
    hx = np.arange(-px.size + 1, 1)
    fx = np.arange(0, HORIZON + 1)
    for i, (m, c) in enumerate((("gbm", C_GREY), ("garch_t", C_MAIN))):
        mc, ax = D.mc[m], fig.add_subplot(gs[0, i])
        ax.plot(hx, px, color="black", lw=1)
        ax.fill_between(fx, mc.fan[5], mc.fan[95], color=c, alpha=0.18, label="5-95%")
        ax.fill_between(fx, mc.fan[25], mc.fan[75], color=c, alpha=0.35, label="25-75%")
        ax.plot(fx, mc.fan[50], color=c, lw=1.4, label="median")
        ax.axvline(0, color=C_GREY, lw=0.7)
        ax.set_title(f"{m.upper()}: VaR95 {mc.var_pct * 100:.1f}%, CVaR {mc.cvar_pct * 100:.1f}%",
                     loc="left")
        ax.set_xlabel("sessions from today"); ax.legend(loc="upper left")
    ax = fig.add_subplot(gs[1, :])
    lo = min(D.mc_gbm.p05, D.mc_g.p05) * 0.8
    hi = max(D.mc_gbm.p95, D.mc_g.p95) * 1.25
    bins = np.linspace(lo, hi, 80)
    ax.hist(D.mc_gbm.terminal, bins=bins, density=True, color=C_GREY, alpha=0.5, label="GBM")
    ax.hist(D.mc_g.terminal, bins=bins, density=True, color=C_MAIN, alpha=0.5, label="GARCH-t")
    ax.axvline(D.mc_g.spot, color="black", lw=1, label=f"spot {D.mc_g.spot:,.2f}")
    for mc, c in ((D.mc_gbm, C_GREY), (D.mc_g, C_MAIN)):
        ax.axvline(mc.spot * (1 - mc.var_pct), color=c, ls="--", lw=1)
    ax.set_title(f"Terminal price after {HORIZON} sessions, {N_PATHS:,} paths, seed {SEED} "
                 "(dashed: VaR95 price)", loc="left")
    ax.set_xlabel("terminal price"); ax.legend(loc="upper right")
    fig.tight_layout()
    return _save(fig, "fig5_fans.png")


def _nu_txt(x: float) -> str:
    return "normal" if math.isinf(x) else (f">{NU_NORMAL:.0f}" if x > NU_NORMAL else f"{x:.1f}")


def fig6() -> str:
    fig = plt.figure(figsize=(FIG_W, 6.0))
    gs = gridspec.GridSpec(2, 2, figure=fig)
    ax0, ax1, ax2 = fig.add_subplot(gs[0, 0]), fig.add_subplot(gs[0, 1]), fig.add_subplot(gs[1, :])
    ok = D.ll_beta > -1e9
    ax0.plot(D.beta_grid[ok], D.ll_beta[ok], color=C_MAIN, lw=1.2)
    ax0.plot([D.fit.beta], [D.fit.loglik], "o", color=C_ALT, ms=5,
             label=f"maximum: beta {D.fit.beta:.3f}, ln L {D.fit.loglik:.1f}")
    ax0.axvline(BOUNDS["beta"][1], color=C_RED, ls="--", lw=1, label="bound 0.999")
    ax0.axvline(STATIONARITY_MAX - D.fit.alpha, color=C_RED, ls=":", lw=1,
                label=f"penalty: alpha+beta > {STATIONARITY_MAX}")
    ax0.set_xlabel("beta (omega, alpha, eta at their optimum)"); ax0.set_ylabel("log-likelihood")
    lo = float(np.percentile(D.ll_beta[ok], 5))
    ax0.set_ylim(lo, D.ll_beta[ok].max() + 0.1 * (D.ll_beta[ok].max() - lo))
    ax0.set_title(f"{D.H.symbol}: a slice in beta", loc="left"); ax0.legend(loc="upper left")
    for ax, fit, prof, title, leg in ((ax1, D.fit, D.prof_eta, f"{D.H.symbol}: profile in eta", "upper left"),
                                      (ax2, D.fit_demo, D.prof_eta_demo,
                                       "synthetic_history(\"AAPL\"): the profile reaches the normal",
                                       "upper right")):
        eta_hat = 0.0 if math.isinf(fit.nu) else 1.0 / fit.nu
        lo_e, hi_e = fit.eta_interval
        nu_lo, nu_hi = fit.nu_interval
        ax.plot(D.eta_grid, prof, color=C_MAIN, lw=1.2, label="profile ln L")
        ax.plot([eta_hat], [fit.loglik], "o", color=C_ALT, ms=5,
                label=f"maximum: eta {eta_hat:.3f} (nu {_nu_txt(fit.nu)})")
        ax.axhline(fit.loglik - PROFILE_CUT, color=C_GREY, ls="--", lw=0.9,
                   label=f"cut {PROFILE_CUT:.2f} (inside)")
        ax.hlines(fit.loglik - PROFILE_CUT0, 0.0, D.eta_grid[1], color=C_RED, lw=2.2,
                  label=f"cut {PROFILE_CUT0:.3f} (at eta = 0)")
        ax.axvspan(lo_e, hi_e, color=C_GREEN, alpha=0.13,
                   label=f"95%: nu {_nu_txt(nu_lo)} to {_nu_txt(nu_hi)}")
        ax.set_ylim(fit.loglik - 12, fit.loglik + 1.5)
        ax.set_xlim(-0.005, ETA_MAX + 0.005)
        ax.set_xlabel(f"eta = 1/nu   (0 is the normal, {ETA_MAX} is nu = {NU_MIN})")
        ax.set_title(title, loc="left"); ax.legend(loc=leg, fontsize=6.5)
    ax1.set_ylabel("log-likelihood"); ax2.set_ylabel("log-likelihood")
    fig.tight_layout()
    return _save(fig, "fig6_loglik_slice.png")


FIGS = {1: fig1(), 2: fig2(), 3: fig3(), 4: fig4(), 5: fig5(), 6: fig6()}
print(f"figures written to {FIG_DIR} ({time.time() - T0:.1f}s)")


# --------------------------------------------------------------------------- #
# Drift study tables (numbers exactly as in results.csv)
# --------------------------------------------------------------------------- #
_ROWS = list(csv.DictReader(open(STUDY / "results.csv", encoding="utf-8")))
_ST: dict[tuple, dict] = {}
for _row in _ROWS:
    _ST.setdefault((_row["pass"], _row["section"], _row["method"], _row["h"], _row["group"]),
                   {})[_row["metric"]] = _row["value"]


def _f(v: str, fmt: str) -> str:
    return "" if v in ("", None) else format(float(v), fmt)


def pooled_rows(h: int) -> list[list[str]]:
    items = [(k[2], v) for k, v in _ST.items()
             if k[0] == "pass_1260" and k[1] == "pooled" and k[3] == str(h) and k[4] == "all"]
    items.sort(key=lambda kv: float(kv[1]["rmse"]))
    return [[m, _f(v["n"], ".0f"), _f(v["rmse"], ".4f"), _f(v["mae"], ".4f"), _f(v["bias"], "+.4f"),
             _f(v["skill_vs_zero"], "+.3f"), _f(v.get("hit_rate", ""), ".3f"),
             _f(v["coverage_90"], ".3f")] for m, v in items]


def dm_rows(baseline: str) -> list[list[str]]:
    out = []
    for h in (63, 252):
        items = [(k[2], v) for k, v in _ST.items()
                 if k[0] == "pass_1260" and k[1] == f"dm_vs_{baseline}" and k[3] == str(h)]
        items.sort(key=lambda kv: float(kv[1]["dm_t_nw"]))
        out += [[str(h), m, _f(v["mean_dloss"], "+.5f"), _f(v["dm_t_nw"], "+.2f"),
                 _f(v["n_origins"], ".0f"), _f(v["n_pairs"], ".0f")] for m, v in items]
    return out


def class_rows(group: str, h: int) -> list[list[str]]:
    items = [(k[2], v) for k, v in _ST.items()
             if k[0] == "pass_1260" and k[1] == "by_class" and k[3] == str(h) and k[4] == group]
    items.sort(key=lambda kv: float(kv[1]["rmse"]))
    return [[m, _f(v["n"], ".0f"), _f(v["rmse"], ".4f"), _f(v["bias"], "+.4f"),
             _f(v["skill_vs_zero"], "+.3f"), _f(v.get("hit_rate", ""), ".3f"),
             _f(v["coverage_90"], ".3f")] for m, v in items]


def se_rows() -> list[list[str]]:
    items = [(k[4], v) for k, v in _ST.items() if k[1] == "se_sample_504"]
    items.sort(key=lambda kv: float(kv[1]["mean_sigma"]))
    return [[t, _f(v["n"], ".0f"), _f(v["mean_sigma"], ".3f"), _f(v["mu_mean"], "+.3f"),
             _f(v["mu_std"], ".3f"), _f(v["theory_se"], ".3f")] for t, v in items]


def study_val(section: str, method: str, h: int, metric: str, group: str = "all",
              pass_: str = "pass_1260") -> float:
    return float(_ST[(pass_, section, method, str(h), group)][metric])


# --------------------------------------------------------------------------- #
# Styles and flowable helpers
# --------------------------------------------------------------------------- #
TEXT_W = A4[0] - 2 * 2.2 * cm
_BASE = dict(fontName="DejaVuSans", fontSize=10, leading=14, spaceAfter=6)
ST = {
    "body": ParagraphStyle("body", **_BASE),
    "H1": ParagraphStyle("H1", fontName="DejaVuSans-Bold", fontSize=16, leading=20,
                         spaceBefore=6, spaceAfter=10, keepWithNext=True),
    "TOCH": ParagraphStyle("TOCH", fontName="DejaVuSans-Bold", fontSize=16, leading=20,
                           spaceAfter=10),
    "H2": ParagraphStyle("H2", fontName="DejaVuSans-Bold", fontSize=12.5, leading=16,
                         spaceBefore=12, spaceAfter=6, keepWithNext=True),
    "H3": ParagraphStyle("H3", fontName="DejaVuSans-Bold", fontSize=10.5, leading=14,
                         spaceBefore=8, spaceAfter=4),
    "code": ParagraphStyle("code", fontName="DejaVuSansMono", fontSize=8.5, leading=11),
    "caption": ParagraphStyle("caption", fontName="DejaVuSans-Oblique", fontSize=8.5, leading=11,
                              textColor=colors.HexColor("#444444"), spaceBefore=4, spaceAfter=12),
    "cell": ParagraphStyle("cell", fontName="DejaVuSans", fontSize=8, leading=10),
    "cellb": ParagraphStyle("cellb", fontName="DejaVuSans-Bold", fontSize=8, leading=10),
    "bullet": ParagraphStyle("bullet", leftIndent=16, bulletIndent=4, bulletFontName="DejaVuSans",
                             **_BASE),
    "title": ParagraphStyle("title", fontName="DejaVuSans-Bold", fontSize=26, leading=32,
                            spaceAfter=14),
    "subtitle": ParagraphStyle("subtitle", fontName="DejaVuSans", fontSize=12.5, leading=17,
                               spaceAfter=8, textColor=colors.HexColor("#333333")),
    "small": ParagraphStyle("small", fontName="DejaVuSans", fontSize=8.5, leading=11, spaceAfter=4),
    "boxtitle": ParagraphStyle("boxtitle", fontName="DejaVuSans-Bold", fontSize=9.5, leading=12,
                               spaceAfter=3),
}
_GRID = colors.HexColor("#BBBBBB")
_HEAD_BG = colors.HexColor("#E8EEF5")
_CODE_BG = colors.HexColor("#F3F4F6")


def P(text: str, style: str = "body") -> Paragraph:
    return Paragraph(text, ST[style])


def P3(text: str) -> list:
    """An H3 that never sits alone at the foot of a page, without forcing the
    table after it to start a new page (keepWithNext would)."""
    return [CondPageBreak(3 * cm), P(text, "H3")]


_EQ_DIR = FIG_DIR / "eq"
_EQ_DIR.mkdir(exist_ok=True)
_EQ_PT, _EQ_DPI, _EQ_INDENT = 12, 600, 1.2 * cm       # 12 pt CM sits level with the 10 pt DejaVu body
_EQ_PARSER = MathTextParser("path")


def _tex_png(tex: str) -> tuple[str, float, float]:
    """One line of LaTeX math typeset by matplotlib's mathtext in Computer Modern (no TeX
    installation needed) to a PNG at _EQ_DPI; returns (path, width_pt, height_pt) at _EQ_PT."""
    key = hashlib.md5(f"{tex}|cm|{_EQ_PT}|{_EQ_DPI}".encode("utf-8")).hexdigest()[:12]
    path = _EQ_DIR / f"eq_{key}.png"
    prop = FontProperties(size=_EQ_PT, math_fontfamily="cm")     # Computer Modern, the LaTeX faces
    w, h, d, _, _ = _EQ_PARSER.parse(tex, dpi=72, prop=prop)
    fig = mfigure.Figure(figsize=(w / 72, h / 72))
    fig.text(0, d / h, tex, fontproperties=prop)
    fig.savefig(path, dpi=_EQ_DPI, format="png", bbox_inches="tight", pad_inches=0.01)
    iw, ih = ImageReader(str(path)).getSize()
    return str(path), iw * 72 / _EQ_DPI, ih * 72 / _EQ_DPI


def F(*lines: str) -> Table:
    """A display formula: each argument is one line of LaTeX math ($...$), typeset by
    _tex_png and set as an image at the formula indent, one row per line."""
    rows = []
    for tex in lines:
        path, w, h = _tex_png(tex)
        s = min(1.0, (TEXT_W - _EQ_INDENT) / w)
        assert s >= 0.85, f"formula line too wide ({w:.0f} pt), split it: {tex[:60]}"
        img = Image(path, width=w * s, height=h * s)
        img.hAlign = "LEFT"
        rows.append([img])
    t = Table(rows, colWidths=[TEXT_W], hAlign="LEFT")
    t.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), _EQ_INDENT),
                           ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                           ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2)]))
    t.spaceBefore, t.spaceAfter = 3, 7
    return t


def B(items: list[str]) -> list:
    return [Paragraph(t, ST["bullet"], bulletText="•") for t in items]


def CODE(text: str) -> Table:
    t = Table([[Preformatted(text.strip("\n"), ST["code"])]], colWidths=[TEXT_W])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), _CODE_BG),
                           ("BOX", (0, 0), (-1, -1), 0.4, _GRID),
                           ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                           ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
    t.spaceAfter = 8
    return t


def TBL(header: list[str], rows: list[list], widths: list[float] | None = None,
        font: float = 9, wrap: bool = False, align_right_from: int | None = None) -> Table:
    """A table with a header row. `wrap=True` renders cells as Paragraphs (long text)."""
    if wrap:
        data = [[Paragraph(h, ST["cellb"]) for h in header]] + \
               [[Paragraph(str(c), ST["cell"]) for c in row] for row in rows]
    else:
        data = [header] + rows
    t = Table(data, colWidths=widths, repeatRows=1)
    style = [("FONTNAME", (0, 0), (-1, 0), "DejaVuSans-Bold"),
             ("FONTNAME", (0, 1), (-1, -1), "DejaVuSans"),
             ("FONTSIZE", (0, 0), (-1, -1), font), ("LEADING", (0, 0), (-1, -1), font + 2.5),
             ("BACKGROUND", (0, 0), (-1, 0), _HEAD_BG), ("GRID", (0, 0), (-1, -1), 0.35, _GRID),
             ("VALIGN", (0, 0), (-1, -1), "TOP"),
             ("TOPPADDING", (0, 0), (-1, -1), 2.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
             ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4)]
    if align_right_from is not None:
        style.append(("ALIGN", (align_right_from, 1), (-1, -1), "RIGHT"))
    t.setStyle(TableStyle(style))
    t.spaceAfter = 8
    return t


def FIG(n: int, caption: str, path: str | None = None) -> KeepTogether:
    path = path or FIGS[n]
    iw, ih = ImageReader(path).getSize()
    img = Image(path, width=15 * cm, height=15 * cm * ih / iw)
    img.hAlign = "CENTER"
    return KeepTogether([img, P(f"<b>Figure {n}</b> — {caption}", "caption")])


def BOX(title: str, items: list[str], color: str) -> Table:
    inner = [Paragraph(title, ST["boxtitle"])] + B(items)
    t = Table([[inner]], colWidths=[TEXT_W])
    t.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 1.2, colors.HexColor(color)),
                           ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FAFAFA")),
                           ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                           ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
    t.spaceAfter = 10
    return t


def pct(x: float, d: int = 1) -> str:
    return f"{x * 100:.{d}f}%"


def spct(x: float, d: int = 1) -> str:
    return f"{x * 100:+.{d}f}%"


# --------------------------------------------------------------------------- #
# Chapters
# --------------------------------------------------------------------------- #
def ch_title() -> list:
    return [
        Spacer(1, 4 * cm),
        P("QUANTGEN Models Primer", "title"),
        P("The price-path models behind the Quant Lab: log returns, Monte Carlo, GBM, "
          "GARCH(1,1) with Student-t innovations, maximum likelihood, its guardrails and its "
          "precision, and the drift study.", "subtitle"),
        Spacer(1, 1 * cm),
        P(f"Built {time.strftime('%Y-%m-%d %H:%M')} by <font name='DejaVuSansMono'>docs/build_models_primer.py</font> "
          f"from the code in <font name='DejaVuSansMono'>core/quant/</font>.", "small"),
        P(f"Data behind every fitted number and figure 1-6: {D.SRC}.", "small"),
        P("Written for the operator of QUANTGEN. Nothing in this document is investment advice; "
          "it explains what the software computes and why.", "small"),
        PageBreak(),
    ]


def ch_toc() -> list:
    toc = TableOfContents()
    toc.levelStyles = [
        ParagraphStyle("TOC1", fontName="DejaVuSans-Bold", fontSize=10, leading=15, leftIndent=0),
        ParagraphStyle("TOC2", fontName="DejaVuSans", fontSize=9, leading=12.5, leftIndent=16),
    ]
    toc.dotsMinLevel = 0
    return [P("Contents", "TOCH"), toc, PageBreak()]


def ch0() -> list:
    return [
        P("0. How to use this document", "H1"),
        P("The Quant Lab takes a symbol, a data source, a model, a drift mode, a horizon in sessions "
          "and a number of paths. It loads up to 504 daily closes, converts them to daily log "
          "returns, calibrates the model on those returns, draws the paths from a fixed seed, and "
          "answers with a stat strip, a row of chips, three charts and a written narrative. When "
          "the model is GARCH(1,1)-t (the default) a second stat strip shows the fitted parameters "
          "and one chip per guardrail that the fit hit. This document explains every one of those "
          "numbers, in the order you need them, using values computed from the same code when the "
          "PDF was built."),
        P("Where each part of the screen is explained", "H2"),
        TBL(["Screen element", "Chapter"], [
            ["Symbol, data source, horizon, paths, target", "1 (returns), 2 (Monte Carlo)"],
            ["Model dropdown: GBM, jump diffusion, block bootstrap", "3"],
            ["Model dropdown: GARCH(1,1)-t", "4 (why), 5 (the model), 6 (the tails)"],
            ["Drift dropdown and the ERP field", "8 (the study), 1.4 (which measure)"],
            ["Spot, median terminal, 90% range, P(loss), VaR 95, CVaR, P(target)", "2"],
            ["Drift (ann.), Vol (ann.) tiles; the drift sentence; the rf chip", "3, 8"],
            ["alpha, beta, alpha+beta, half-life, nu, cond / uncond / horizon vol", "5, 6"],
            ["The intervals in brackets on those tiles: \"value (low to high)\"", "5.8 (alpha, beta, persistence, half-life), 6.5 (nu)"],
            ["LR t vs normal, dAIC vs GBM", "6.4, 7.4"],
            ["Chips: at bound, solver did not converge, SE undefined, interval touches a bound, "
             "guardrails clear, normal innovations, persistence interval reaches 1", "7.6"],
            ["Conditional vol chart, fan chart, terminal histogram", "5.4, 2.3, 2.4"],
            ["The narrative panel and every sentence it can produce", "9"],
        ], widths=[10.6 * cm, 6 * cm], wrap=True),
        BOX("Safe to change / do not change without reading chapter 7", [
            "<b>Safe, any time:</b> symbol, data source, horizon, number of paths, target price, "
            "drift mode, the ERP percentage, and the seed if you edit the call. They change the "
            "question, not the estimator.",
            "<b>Think first (chapter 7.7):</b> the nu level above which the t is treated as normal, "
            "the persistence cap, the alpha cap, the minimum-observation rule, the optimiser's "
            "starting values, the LR critical value, the profile-interval cuts. Each is a "
            "guardrail; moving one changes when the app warns you.",
            "<b>Do not touch without a test in hand (chapter 7.8):</b> the likelihood formulas, "
            "the unit-variance scaling of the t draws, the variance recursion and its starting "
            "value, the omega scaling, the annualisation constant. A mistake there corrupts every "
            "number silently: the screen still fills with plausible values.",
        ], "#1f4e79"),
        P("How to read the numbers in this document", "H2"),
        P(f"Every fitted or simulated number was produced when this file was built, by calling "
          f"<font name='DejaVuSansMono'>fit_garch</font>, "
          f"<font name='DejaVuSansMono'>run_monte_carlo</font> and their helpers on: {D.SRC}. "
          f"The drift-study tables are read from "
          f"<font name='DejaVuSansMono'>docs/drift_study/results.csv</font>. To rebuild after "
          f"a code change, run <font name='DejaVuSansMono'>python docs/build_models_primer.py</font> "
          f"from the project root; it needs no network (set PRIMER_OFFLINE=1 to force the synthetic "
          f"fallback) and finishes in well under two minutes."),
        P("One series appears throughout as the worked example, so you can follow a single fit "
          "from raw returns to the fan chart. A second series, the app's own no-key demo "
          "(<font name='DejaVuSansMono'>synthetic_history(\"AAPL\")</font>, a geometric Brownian "
          "path), is used wherever a guardrail needs to be shown binding: it is exactly what the "
          "Quant Lab shows when you choose the \"Synthetic demo\" data source."),
        PageBreak(),
    ]


def ch1() -> list:
    return [
        P("1. What a price-path model is", "H1"),
        P("1.1 A model of tomorrow's return", "H2"),
        P("A price-path model is a statement about the probability distribution of the next daily "
          "return. Every model in the Quant Lab, however elaborate, can be written as"),
        F(r"$r_{t+1} = \mu + \sigma_{t+1} z_{t+1},\qquad \mathrm{E}[z] = 0,\qquad \mathrm{Var}[z] = 1$"),
        P("with three ingredients. The <b>drift</b> μ is the expected daily return. The "
          "<b>volatility</b> σ<sub>t+1</sub> is the standard deviation of the return, which may "
          "be constant (GBM) or change from day to day (GARCH). The <b>innovation</b> z is a "
          "random draw with mean zero and variance one whose shape decides how likely extreme days "
          "are: normal for GBM, Student-t for GARCH-t, the sample's own history for the bootstrap. "
          "Choosing a model means choosing those three things. Everything the lab reports — the "
          "fan, VaR, the probability of loss — follows from that choice plus arithmetic."),
        P("1.2 Daily log returns and why logs", "H2"),
        P("The app never models prices directly. It converts the close series P<sub>t</sub> into "
          "daily log returns"),
        F(r"$r_t = \ln(P_t / P_{t-1})$"),
        P("(<font name='DejaVuSansMono'>History.log_returns()</font> is "
          "<font name='DejaVuSansMono'>np.diff(np.log(px))</font>). Logs are used for two reasons. "
          "First, they add: the log return over a week is the sum of the five daily log returns, "
          "so a horizon of h sessions is just a sum of h draws, and sums of independent draws are "
          "what statistics knows how to handle. Simple returns compound multiplicatively and do "
          "not add. Second, exponentiating a sum of log returns can never give a negative price: "
          "the simulated price is P<sub>0</sub> exp(r<sub>1</sub> + … + r<sub>h</sub>). For small "
          "moves the two are almost equal (a 1% simple return is a 0.995% log return); for large "
          "moves they differ, and the app's percentages are always converted back to prices before "
          "they are shown."),
        P("1.3 Annualising: 252 and the square root of 252", "H2"),
        P("There are about 252 trading sessions in a year, so a daily mean becomes an annual mean "
          "by multiplying by 252. Variances of independent daily returns also add, so the annual "
          "variance is 252 times the daily variance, and the annual <i>volatility</i> (its square "
          "root) is √252 ≈ 15.87 times the daily volatility:"),
        F(r"$\mu_{\mathrm{annual}} = 252\,\mu_{\mathrm{daily}},\qquad \sigma_{\mathrm{annual}} = \sqrt{252}\,\sigma_{\mathrm{daily}}$"),
        P(f"On the worked series (T = {D.T} daily returns) the sample mean is "
          f"{D.mu_d * 100:+.4f}% per day, i.e. {spct(D.mu_a)} a year, and the sample standard "
          f"deviation is {D.sd_d * 100:.3f}% per day, i.e. {pct(D.sd_a)} a year. Inside "
          f"<font name='DejaVuSansMono'>core/quant/garch.py</font> everything is kept in daily "
          f"units and annualised only at the edges (<font name='DejaVuSansMono'>TRADING_DAYS = "
          f"{TRADING_DAYS}</font>). The FICC pages quote rates in percent and changes in basis "
          f"points; here volatility is quoted in percent per year and returns in percent."),
        P("1.4 Two measures: what you simulate with and what you price with", "H2"),
        P("The Quant Lab simulates under the <b>physical measure</b>: the drift is meant to be the "
          "return you actually expect to earn, and the fan is a statement about what may happen to "
          "a position. That is the right object for risk: VaR, the probability of loss, the width "
          "of the cone. Its weakness is that the expected return is the least identifiable number "
          "in finance (chapter 8), so the physical measure is only as good as the drift you put in."),
        P("The pricing pages (options, structured notes, swaptions) work under the <b>risk-neutral "
          "measure</b>. There the drift of every asset is replaced by the risk-free rate — not "
          "because anyone expects a stock to earn the T-bill rate, but because a hedged position "
          "earns the risk-free rate, and a price that assumed anything else could be arbitraged. "
          "A risk-neutral simulation prices; it does not forecast. The Quant Lab's "
          "<i>rf</i> drift mode is that measure: it is offered so you can see what the pricing "
          "pages assume, and it is labelled as not-a-forecast for exactly this reason."),
    ]


def ch2() -> list:
    g, b = D.mc_g, D.mc_gbm
    se500, se5000 = D.se[500], D.se[5000]
    return [
        P("2. Monte Carlo", "H1"),
        P("2.1 A method, not a model", "H2"),
        P("Monte Carlo is a way of reading a distribution you cannot write down in closed form: "
          "draw many possible futures from the model, then count. The Quant Lab draws a matrix of "
          "daily log returns with one row per path and one column per session, cumulates each row, "
          "exponentiates, and multiplies by spot. The core of "
          "<font name='DejaVuSansMono'>run_monte_carlo</font> is four lines:"),
        CODE("""log_paths = np.cumsum(shocks, axis=1)                       # (n_paths, horizon)
paths = spot * np.exp(np.hstack([np.zeros((n_paths, 1)), log_paths]))
fan = {p: np.percentile(paths, p, axis=0) for p in FAN_PERCENTILES}  # 5,25,50,75,95
terminal = paths[:, -1].copy()"""),
        P("The model decides what goes into <font name='DejaVuSansMono'>shocks</font>; everything "
          "after that is the same for GBM, jump diffusion, the bootstrap and GARCH-t. That is why "
          "the risk numbers of the four models are directly comparable: they are read off the same "
          "kind of object with the same code."),
        P("2.2 Seeds and reproducibility", "H2"),
        P(f"Every run starts from <font name='DejaVuSansMono'>np.random.default_rng(seed)</font> "
          f"with seed {SEED} unless you pass another. The same inputs therefore draw exactly the "
          f"same paths, and the acceptance test "
          f"<font name='DejaVuSansMono'>test_mc_is_seeded_and_reproducible</font> checks that "
          f"seed {SEED} twice gives the same median and seed {SEED + 1} gives a different one. "
          f"A simulation that repaints on every refresh cannot be reasoned about: you could never "
          f"tell whether a change in VaR came from the market or from the dice."),
        P("2.3 The percentile fan", "H2"),
        P("At each future session the app takes the 5th, 25th, 50th, 75th and 95th percentile of the "
          "simulated prices across paths. The shaded bands are those percentiles joined up over "
          "time; the median line is the 50th. None of them is a path: no single simulated future "
          "runs along the 95th percentile, so the fan says where the price may be on a given date, "
          "not how it gets there. The faint lines behind the fan are forty real paths, kept so "
          "the eye can see what one future looks like."),
        P("2.4 VaR and CVaR from the terminal distribution", "H2"),
        P("Write the horizon loss as a fraction of spot, L = 1 − P<sub>T</sub> / spot (positive "
          "means a loss). <b>Value at risk</b> at level 95% is the loss that is exceeded on only 5% "
          "of paths; <b>conditional VaR</b> (expected shortfall) is the average loss on those 5% "
          "of paths:"),
        F(r"$\mathrm{VaR}_{95} = \text{95th percentile of } L,\qquad \mathrm{CVaR}_{95} = \mathrm{E}[\,L \mid L \geq \mathrm{VaR}_{95}\,]$"),
        CODE("""losses = 1.0 - terminal / spot                       # +ve = loss fraction
var = float(np.percentile(losses, var_level * 100))   # var_level = 0.95
tail = losses[losses >= var]
cvar = float(np.mean(tail)) if tail.size else var"""),
        P(f"Both are clipped at zero (a distribution so favourable that the 95th percentile loss is "
          f"negative shows VaR 0.0%). On the worked series over {HORIZON} sessions with "
          f"{N_PATHS:,} paths, GARCH-t gives VaR<sub>95</sub> = {pct(g.var_pct)} and CVaR = "
          f"{pct(g.cvar_pct)}; GBM on the same history and seed gives {pct(b.var_pct)} and "
          f"{pct(b.cvar_pct)}. CVaR is always at least VaR (the test "
          f"<font name='DejaVuSansMono'>test_mc_var_and_cvar_are_coherent</font> asserts it); the "
          f"gap between them is a direct read of how fat the left tail is."),
        FIG(5, f"GBM (left) and GARCH(1,1)-t (right) fans on the same history and the same seed "
               f"({SEED}), {N_PATHS:,} paths over {HORIZON} sessions: 5-95% and 25-75% bands and the "
               f"median, after the last 90 sessions of history. Below, the two terminal distributions "
               f"overlaid, with spot and each model's VaR<sub>95</sub> price (dashed). GARCH-t starts "
               f"from today's conditional vol ({pct(D.fit.cond_vol_last)}) rather than the sample "
               f"average ({pct(D.sd_a)}), and its t innovations put more mass in both tails. Source: {D.SRC}."),
        P("2.5 Probability of loss and of reaching a target", "H2"),
        P(f"P(loss) is the share of paths whose terminal price is below spot; P(target) is the "
          f"share at or above the target you typed. They are counts, not model formulas, so they "
          f"work identically for every model. Worked run: P(loss) = {pct(g.prob_loss, 0)} for "
          f"GARCH-t against {pct(b.prob_loss, 0)} for GBM; the median terminal is "
          f"{g.median_terminal:,.2f} against a spot of {g.spot:,.2f}. Note that P(loss) depends on "
          f"the drift as much as on the volatility: under the zero-drift mode the median sits on "
          f"spot and P(loss) is close to 50% by construction."),
        P("2.6 The standard error of a Monte Carlo number", "H2"),
        P("Every Monte Carlo statistic is an estimate from N random paths, and its sampling error "
          "falls as 1/√N. For a mean, the standard error is s/√N where s is the standard deviation "
          "of the terminal prices; for a percentile the constant is different but the √N is the "
          "same. Ten times more paths buys a √10 ≈ 3.2 times smaller error, no more."),
        P(f"Measured on the worked series (GBM, {HORIZON} sessions, twenty different seeds): with "
          f"500 paths the median terminal moved with a standard deviation of {se500[0]:.2f} "
          f"and VaR<sub>95</sub> with {se500[1] * 100:.2f} percentage points; with 5,000 paths "
          f"{se5000[0]:.2f} and {se5000[1] * 100:.2f} points. CVaR, which averages only the worst "
          f"5% of paths, is noisier: {se500[2] * 100:.2f} points at 500 paths and "
          f"{se5000[2] * 100:.2f} at 5,000. The default of 5,000 paths keeps the tail numbers "
          f"stable to about a tenth of a point at a cost of a second or two; 500 paths is fine for "
          f"a quick look at the median but its CVaR is a rough draft. The code clamps paths to "
          f"[200, 100,000] and the horizon to [5, {TRADING_DAYS * 5}] sessions."),
        P("2.7 What changes with the horizon", "H2"),
        P("Under a constant-vol model the cone widens with the square root of the horizon while "
          "the drift moves the centre linearly, so the drift matters more and more as the horizon "
          "grows: at 21 sessions the fan is almost all volatility; at 252 the drift assumption "
          "moves the median by roughly the annual drift. Under GARCH the first sessions are drawn "
          "with today's conditional vol, which can be far from the long-run level, and the "
          "variance forecast converges to the unconditional level over the half-life (chapter 5.5). "
          "VaR at 126 sessions is therefore not the one-day VaR times √126; the app computes each "
          "horizon on its own paths."),
    ]


def ch3() -> list:
    jump = D.mc["jump"]
    half_var = 0.5 * D.sd_a ** 2
    return [
        P("3. Geometric Brownian motion (GBM)", "H1"),
        P("3.1 The equation and its discrete step", "H2"),
        P("GBM says the price moves in continuous time with a constant expected growth rate μ and "
          "a constant volatility σ, driven by a Brownian motion W:"),
        F(r"$dS = \mu S\,dt + \sigma S\,dW$"),
        P("Itô's lemma turns that into a statement about the log price, which is what the app "
          "simulates:"),
        F(r"$d\ln S = (\mu - \sigma^2/2)\,dt + \sigma\,dW$"),
        P("Over one session (Δt = 1/252) the log return is normal with mean (μ − σ<super>2</super>/2)Δt "
          "and standard deviation σ√Δt, so the discretised step is"),
        F(r"$r_t = (\mu - \sigma^2/2)\,\Delta t + \sigma\sqrt{\Delta t}\,z_t,\qquad z_t \sim N(0,\,1)$"),
        P("3.2 Calibration and the −½σ<super>2</super> term", "H2"),
        P("Calibrating GBM is the sample mean and the sample standard deviation of the daily log "
          "returns, annualised as in chapter 1.3. The term −σ<super>2</super>/2 exists because the "
          "expected value of exp(X) is not exp(E[X]): for a normal X with mean m and variance v, "
          "E[exp(X)] = exp(m + v/2). If you want the <i>price</i> to grow at rate μ on average, the "
          "<i>log price</i> must grow at μ − σ<super>2</super>/2; the median price then grows at "
          "the lower rate and the mean at μ, the gap being the reward for holding a lognormal "
          "asset's right tail."),
        P(f"The app treats the drift as a <i>log</i> drift throughout: "
          f"<font name='DejaVuSansMono'>_simulate_gbm</font> draws zero-mean shocks "
          f"<font name='DejaVuSansMono'>rng.normal(0.0, sigma * sqrt(dt))</font> and "
          f"<font name='DejaVuSansMono'>run_monte_carlo</font> adds μ/252 to every step for every "
          f"model. The −σ<super>2</super>/2 therefore appears only inside the drift modes that "
          f"start from a rate of return on the price (rf and rf + ERP, chapter 8.6), never on top "
          f"of a sample mean that is already a log mean. On the worked series σ = {pct(D.sd_a)} "
          f"so σ<super>2</super>/2 = {pct(half_var, 2)} a year: with a {pct(RF, 2)} risk-free rate "
          f"and a {pct(ERP, 1)} premium the premium-mode log drift is "
          f"{spct(RF + ERP - half_var, 2)}. The earlier version of the code subtracted the half "
          f"variance from the sample mean as well, which biased every GBM median down; the test "
          f"<font name='DejaVuSansMono'>test_drift_zero_centres_the_cone_and_sample_reproduces_the_mean</font> "
          f"now pins the median to spot × exp(μT) under the sample mode. The ½σ<super>2</super> is "
          f"GBM's own correction; the other models subtract their own exact per-step correction "
          f"under the rate modes (the jump compensator, the bootstrap's block log-MGF, GARCH-t's "
          f"c(σ<sub>t</sub>) from each path's conditional variance; chapter 8.6), so the mean "
          f"price grows at the stated rate under every model."),
        P("3.3 What GBM gets right and wrong", "H2"),
        P("Right: it is the baseline everyone else is measured against, it has two parameters that "
          "any 21-session window can estimate, it never produces a negative price, and it is the "
          "model under which Black-Scholes and most of the pricing pages are exact. Wrong, on daily "
          "data: volatility is not constant (chapter 4.1), the tails are far fatter than normal "
          "(chapter 4.2), large moves cluster in time, and prices sometimes gap. A GBM fan drawn "
          "the day after a 6% move is too narrow; one drawn after a placid year is too wide."),
        P("3.4 Jump diffusion: patching the tails", "H2"),
        P("Merton's model adds a Poisson jump process to the diffusion. The app calibrates it by "
          "splitting the return sample at three daily standard deviations: the days beyond 3σ are "
          "the jumps, their frequency is the jump intensity λ (jumps per session), their mean and "
          "standard deviation set the jump-size distribution, and the remaining days set the "
          "diffusion. The compound process's own mean is removed so that the drift mode alone "
          "decides the centre. With no outlier in the sample the model degrades to GBM and says so "
          f"in the jump note. On the worked series the note reads: <i>{jump.jump_note}</i>"),
        P("3.5 Block bootstrap: no distribution at all", "H2"),
        P("The stationary block bootstrap resamples the observed daily returns in blocks of five "
          "consecutive sessions (wrapping around the sample), so short-run clustering and the "
          "empirical tails survive exactly as far as they exist in the data. Its strength is that it "
          "assumes nothing; its weakness is the same thing: it can never draw a move larger than any "
          "the window contains, the cone is the sample's own history reshuffled, and the returns are "
          "demeaned before resampling so that, again, only the drift mode sets the centre."),
        P("3.6 The four models side by side", "H2"),
        TBL(["Model", "Assumption", "Captures", "Misses", "When to use"], [
            ["GBM", "constant μ and σ, normal daily returns",
             "the baseline; a two-parameter fit any window supports",
             "clustering, fat tails, jumps; wrong width right after a shock",
             "as the reference every other model must beat (dAIC vs GBM); pricing logic"],
            ["Jump diffusion", "GBM plus Poisson jumps calibrated from the >3σ days",
             "gap risk; a fat left tail when the sample has one",
             "clustering; needs outliers in the window to be different from GBM",
             "a name with known event risk (earnings, policy) when the window contains such days"],
            ["Block bootstrap", "the future is a reshuffle of the past 5-session blocks",
             "the empirical tails and short-run clustering, with no formula",
             "anything the window never showed; long-memory vol; a real forecast of today's vol",
             "a sanity check on the parametric models; series whose shape you distrust"],
            ["GARCH(1,1)-t", "variance follows its own recursion; innovations are Student-t",
             "clustering, fat tails, a fan that starts from today's vol and mean-reverts",
             "jumps as such; asymmetry (down moves raising vol more than up moves)",
             "the default: daily equity, FX and rates series with at least a few hundred sessions"],
        ], widths=[2.3 * cm, 3.4 * cm, 3.6 * cm, 3.6 * cm, 3.7 * cm], font=8, wrap=True),
    ]


def ch4() -> list:
    return [
        P("4. Volatility clustering and fat tails", "H1"),
        P("Two facts about daily financial returns hold across almost every market and decade, and "
          "GBM has neither. They are the reason the Quant Lab defaults to GARCH-t."),
        P("4.1 Clustering: large moves follow large moves", "H2"),
        FIG(1, f"{D.H.symbol} — price, daily log returns and the 20-session realised volatility "
               f"(annualised) against the full-sample volatility of {pct(D.sd_a)}. Calm and turbulent "
               f"stretches are visible in the return panel and as swings of the rolling vol. Source: {D.SRC}."),
        P(f"Returns themselves are almost unpredictable: the lag-1 autocorrelation of r<sub>t</sub> on "
          f"the worked series is {D.acf_r1:+.3f}. Their <i>squares</i> are not: the autocorrelation "
          f"of r<sub>t</sub><super>2</super> is {D.acf_sq[1]:+.3f} at lag 1, {D.acf_sq[5]:+.3f} at "
          f"lag 5 and {D.acf_sq[20]:+.3f} at lag 20. Knowing yesterday's move was big does not tell "
          f"you the sign of today's, but it does tell you today's is likely to be big too. That is "
          f"volatility clustering, first modelled by Engle (1982), and it is precisely the structure "
          f"the GARCH recursion in chapter 5 is built to follow."),
        P("4.2 Fat tails: excess kurtosis", "H2"),
        P("Kurtosis measures how much of a distribution's variance comes from its extremes. For "
          "standardised returns z (mean zero, variance one) the <b>excess kurtosis</b> is"),
        F(r"$\kappa = \mathrm{E}[z^4] - 3$"),
        P(f"which is zero for the normal distribution. The risk report in "
          f"<font name='DejaVuSansMono'>core/quant/risk.py</font> prints it as "
          f"<font name='DejaVuSansMono'>mean(z**4) - 3</font>, and its narrative says \"Excess "
          f"kurtosis of X means fat tails\" whenever X exceeds 2. On the worked series the raw "
          f"returns have κ = {D.kurt:.2f} (skewness {D.skew:+.2f}). A normal distribution with the "
          f"same variance would put far fewer days beyond three standard deviations than the data "
          f"contain."),
        FIG(2, f"Histogram of standardised returns (log scale) against the standard normal density "
               f"and a unit-variance Student-t with ν = {D.fit.nu:.1f} from the fitted model. Left: raw "
               f"returns divided by the sample volatility. Right: the same returns divided by the "
               f"GARCH conditional volatility σ<sub>t</sub> — the tails that remain are what ν has to "
               f"explain. Source: {D.SRC}."),
        P(f"Fat tails in raw returns have two sources. The first is time-varying volatility: a "
          f"mixture of calm days and wild days looks fat-tailed even if each day is normal given its "
          f"own σ<sub>t</sub>. The second is genuinely fat-tailed innovations. GARCH separates them: "
          f"after dividing each return by the fitted σ<sub>t</sub>, the excess kurtosis of the "
          f"residuals falls from {D.kurt:.2f} to {D.kurt_g:.2f}. What is left is handled by the "
          f"Student-t with ν = {D.fit.nu:.1f} (chapter 6), whose own excess kurtosis 6/(ν − 4) is "
          f"{('%.2f' % D.fit.kurtosis_excess) if math.isfinite(D.fit.kurtosis_excess) else 'infinite (ν ≤ 4)'}."),
        P("4.3 Why a constant-vol fan is wrong in both directions", "H2"),
        P(f"A GBM fan uses one volatility for every future session: the sample average, "
          f"{pct(D.sd_a)} here. GARCH-t starts from today's conditional vol, "
          f"{pct(D.fit.cond_vol_last)}, and lets it decay towards the unconditional "
          f"{pct(D.fit.uncond_vol) if math.isfinite(D.fit.uncond_vol) else 'level (undefined here)'} "
          f"over a half-life of {D.fit.half_life:.1f} sessions, for an average of {pct(D.hvol)} over "
          f"the {HORIZON}-session horizon. Right after a shock the conditional vol sits above the "
          f"average and a constant-vol fan is too narrow: it understates the VaR of the next few "
          f"weeks. After a long calm the conditional vol sits below the average and the constant-vol "
          f"fan is too wide, which sounds harmless until it makes a hedge look unnecessary or a "
          f"target look unreachable. The difference shrinks with the horizon, because the GARCH "
          f"forecast converges to the same long-run level; it never disappears when the persistence "
          f"is high."),
    ]


def ch5() -> list:
    f = D.fit
    uncond_d = f.omega / (1 - f.persistence) if f.persistence < 1 else float("nan")
    return [
        P("5. GARCH(1,1)", "H1"),
        P("5.1 The equation, term by term", "H2"),
        P("Bollerslev's (1986) GARCH(1,1) keeps the return equation of chapter 1 and gives the "
          "variance its own recursion:"),
        F(r"$r_t = \mu + \varepsilon_t,\qquad \varepsilon_t = \sigma_t z_t,\qquad "
          r"\sigma_t^2 = \omega + \alpha\,\varepsilon_{t-1}^2 + \beta\,\sigma_{t-1}^2$"),
        P("Today's variance is a constant plus a share of yesterday's squared surprise plus a share of "
          "yesterday's variance. In words: <b>ω</b> (omega) is the floor, the part of the variance "
          "that is always there; <b>α</b> (alpha) is the reaction to yesterday's surprise, how much "
          "a large move raises tomorrow's variance; <b>β</b> (beta) is the memory, how much of "
          "yesterday's variance carries over regardless of what happened. The mean μ is the sample "
          "mean of the returns and is held fixed during the fit "
          "(<font name='DejaVuSansMono'>mu = float(np.mean(r))</font>): a 500-session sample cannot "
          "pin down the mean anyway, and letting the optimiser chase it only makes the volatility "
          "parameters noisier."),
        P(f"The worked fit: ω = {f.omega:.3e} (daily variance units), α = {f.alpha:.3f}, "
          f"β = {f.beta:.3f}, on T = {f.n_obs} returns with μ fixed at {f.mean_daily * 100:+.3f}% "
          f"per day. The app shows α and β to three decimals on the second stat strip, each "
          f"followed by its 95% interval in brackets (chapter 5.8)."),
        P("5.2 Persistence and the unconditional variance", "H2"),
        P("Taking expectations of the recursion and noting E[ε<super>2</super>] = E[σ<super>2</super>] "
          "in the long run gives the <b>unconditional variance</b>, the level the variance settles "
          "at when nothing new happens:"),
        F(r"$\bar\sigma^2 = \frac{\omega}{1 - \alpha - \beta}$"),
        P(f"The sum α + β is the <b>persistence</b>. The worked fit has α + β = {f.persistence:.4f}, "
          f"so σ̄<super>2</super> = {f.omega:.3e} / (1 − {f.persistence:.4f}) = {uncond_d:.3e} per "
          f"day, i.e. an unconditional vol of √({uncond_d:.3e} × 252) = {pct(f.uncond_vol)} a year; "
          f"the \"Uncond vol (ann.)\" tile. As α + β approaches 1 the denominator goes to zero and "
          f"the unconditional variance goes to infinity: the model no longer has a long-run level "
          f"to return to. The code guards this in two ways (chapter 7.6): the objective refuses "
          f"α + β > {STATIONARITY_MAX} outright, and any fit with α + β > 0.995 is flagged "
          f"\"stationarity\" and coloured red."),
        P("5.3 The half-life of a variance shock", "H2"),
        P("A deviation of the variance from its long-run level decays by the factor (α + β) each "
          "session, so the number of sessions for it to halve is"),
        F(r"$\text{half-life} = \frac{\ln 0.5}{\ln(\alpha + \beta)}$"),
        P(f"For the worked fit that is ln 0.5 / ln {f.persistence:.4f} = {f.half_life:.1f} sessions, "
          f"the \"Half-life (sessions)\" tile. A half-life of 5 sessions means the market forgets a "
          f"shock in a week; 50 sessions means a quarter; the code reports infinity when the "
          f"persistence is 1 or more."),
        P("5.4 The conditional volatility path", "H2"),
        FIG(3, f"{D.H.symbol} — the fitted conditional volatility σ<sub>t</sub> (annualised) against "
               f"the 20-session realised volatility and the unconditional level "
               f"{pct(f.uncond_vol) if math.isfinite(f.uncond_vol) else '(undefined)'}. The dot is "
               f"σ<sub>T+1</sub>, the next-session forecast ({pct(f.cond_vol_last)}) that the fan "
               f"starts from. Source: {D.SRC}."),
        P("The recursion needs a starting value. The code starts σ<sub>1</sub><super>2</super> at "
          "the sample variance of ε, i.e. at the unconditional level, and then runs forward through "
          "the whole sample (<font name='DejaVuSansMono'>_variance_path</font>, implemented as a "
          "first-order IIR filter with <font name='DejaVuSansMono'>scipy.signal.lfilter</font>: "
          "y<sub>t</sub> = x<sub>t</sub> + β y<sub>t−1</sub> with x<sub>t</sub> = ω + α "
          "ε<sub>t−1</sub><super>2</super>). The last element of that path is "
          "σ<sub>T+1</sub><super>2</super>, the one-session-ahead forecast; annualised it is the "
          "\"Cond vol (ann.)\" tile and the volatility the first simulated session is drawn with. "
          "The realised vol in the figure lags the conditional vol because it averages the past 20 "
          "days with equal weights, while GARCH weights recent days geometrically."),
        P("5.5 Forecasting the variance h sessions ahead", "H2"),
        P("Beyond the next session the expected squared surprise equals the expected variance, so "
          "the forecast recursion collapses to a single line:"),
        F(r"$\sigma_{T+h}^2 = \omega + (\alpha + \beta)\,\sigma_{T+h-1}^2,\qquad \text{equivalently}$",
          r"$\sigma_{T+h}^2 = \bar\sigma^2 + (\alpha + \beta)^{h-1}\,(\sigma_{T+1}^2 - \bar\sigma^2)$"),
        P(f"This is <font name='DejaVuSansMono'>forecast_variance</font>: it starts from "
          f"σ<sub>T+1</sub><super>2</super> and applies ω + (α + β) σ<super>2</super> h − 1 times. "
          f"The <b>horizon vol</b> the app reports is the square root of the average forecast "
          f"variance over the horizon, annualised "
          f"(<font name='DejaVuSansMono'>horizon_vol</font>): {pct(D.hvol)} for {HORIZON} sessions "
          f"on the worked fit, between today's {pct(f.cond_vol_last)} and the long-run "
          f"{pct(f.uncond_vol) if math.isfinite(f.uncond_vol) else 'level'}. The acceptance test "
          f"<font name='DejaVuSansMono'>test_garch_forecast_variance_converges_to_unconditional</font> "
          f"checks that the first step equals the fit's forecast, that step 5,000 is within 1% of "
          f"ω/(1 − α − β), and that the horizon vol lies between the two."),
        FIG(4, f"Forecast volatility √(σ<sub>T+h</sub><super>2</super> × 252) for h = 1 … 252, starting "
               f"at 32% and converging to an unconditional 20%, for persistence 0.90 (half-life 6.6 "
               f"sessions) and 0.99 (half-life 69 sessions); dotted verticals mark the half-lives. "
               f"Dashed green: the worked fit's own term structure (α + β = {f.persistence:.3f}, "
               f"half-life {f.half_life:.1f})."),
        P("5.6 IGARCH and the near-integrated flag", "H2"),
        P(f"When α + β = 1 the model is called integrated GARCH (IGARCH): the unconditional "
          f"variance is undefined, the half-life is infinite, and the variance forecast stays at "
          f"today's level forever (with ω > 0 it drifts up without bound). Daily data often push the "
          f"fit close to that line because a short window with one regime change looks like "
          f"permanent variance. The code enforces α + β ≤ {STATIONARITY_MAX} by returning a penalty "
          f"of −10<super>10</super> from the objective, and reports \"stationarity\" in "
          f"<font name='DejaVuSansMono'>at_bound</font> for any fit above 0.995; the narrative then "
          f"says \"near-integrated: the sample cannot pin down where vol settles; use a longer "
          f"history\". The fan of such a fit is honest for a few weeks and meaningless at a year, "
          f"because its width never mean-reverts."),
        P("5.7 Typical values and what unusual ones mean", "H2"),
        TBL(["Parameter", "Typical on daily equity data", "If it is unusual"], [
            ["α", "0.05 – 0.10", "near 0: no reaction to shocks, GARCH adds nothing (see the GBM "
                                "demo series in chapter 7); at 0.5 (the cap): a few outliers dominate "
                                "— look at them, try the jump model"],
            ["β", "0.85 – 0.93", "near 0: no memory, the series is closer to iid; at 0.999: integrated, "
                                "see 5.6"],
            ["α + β", "0.95 – 0.99", "> 0.995: flagged near-integrated; the unconditional vol tile is "
                                    "unreliable and the horizon vol barely decays"],
            ["half-life", "10 – 70 sessions", "under 5: the model forgets within a week and the fan is "
                                            "essentially GBM after that; over 200: the fan never "
                                            "returns to the long-run level"],
            ["ω", "10<super>−6</super> – 10<super>−5</super> (daily variance)",
             "only meaningful together with α + β; the tile shows the unconditional vol instead"],
        ], widths=[2.2 * cm, 4.4 * cm, 10 * cm], font=8.5, wrap=True),
        *sec_5_8(),
    ]


def sec_5_8() -> list:
    """5.8: the Wald intervals (B2). Every number is the fit's own."""
    f = D.fit
    ia, ib, ip = f.interval("alpha"), f.interval("beta"), f.interval("persistence")
    hl = f.half_life_interval
    hl_txt = lambda x: "inf" if math.isinf(x) else f"{x:.0f}"
    if f.se:
        worked = (f"Worked fit: α = {f.alpha:.3f} ({ia[0]:.3f} to {ia[1]:.3f}), β = {f.beta:.3f} "
                  f"({ib[0]:.3f} to {ib[1]:.3f}), α + β = {f.persistence:.4f} ({ip[0]:.4f} to "
                  f"{ip[1]:.4f}), half-life {f.half_life:.0f} ({hl_txt(hl[0])} to {hl_txt(hl[1])}) "
                  f"sessions; standard errors {f.se['alpha']:.3f}, {f.se['beta']:.3f} and "
                  f"{f.se['persistence']:.3f}. The tiles show exactly these strings: "
                  f"\"{D.tiles['alpha']}\", \"{D.tiles['beta']}\", \"{D.tiles['alpha+beta']}\", "
                  f"\"{D.tiles['Half-life (sessions)']}\".")
        at = [n for n in f.interval_at_bound if n in ("alpha", "beta")]
        reading = []
        if at:
            reading.append(f"On this window the interval for {' and '.join(at)} crosses a bound "
                           f"({'0' if ia[0] < 0 else ''}{' and ' if ia[0] < 0 and ib[1] > BOUNDS['beta'][1] else ''}"
                           f"{'1' if ib[1] > BOUNDS['beta'][1] else ''}): {f.n_obs} sessions determine the "
                           f"tail of this series far better than its dynamics, and the red chip "
                           f"\"interval touches a bound: {', '.join(at)}\" says so. A symmetric interval "
                           f"on a parameter that lives near a bound is indicative only; the estimate "
                           f"itself is still the maximum-likelihood one.")
        else:
            reading.append("On this window both intervals sit inside their bounds, so the symmetric "
                           "interval is a fair description.")
        if "persistence" in f.interval_at_bound:
            reading.append("The persistence interval reaches 1, which is the case for most two-year "
                           "samples: they do not exclude an integrated variance at 95%, and the "
                           "half-life's upper end is therefore infinite. The app shows this as a muted "
                           "chip, \"persistence interval reaches 1\", not as an error, because it is "
                           "the normal state of a 500-session fit rather than a failure of this one.")
        else:
            reading.append("The persistence interval stays below 1: this window does exclude an "
                           "integrated variance at 95%, which is rarer than it sounds on two years of data.")
        reading = " ".join(reading)
    else:
        worked = (f"Worked fit: standard errors undefined ({f.se_note}); the tiles show the values "
                  f"alone and the chip \"SE undefined\" carries the reason.")
        reading = ""
    return [
        P("5.8 How precisely are α, β and the persistence known?", "H2"),
        P("A fitted parameter is an estimate from one sample; another two years would have given "
          "another number. Maximum likelihood carries its own measure of that uncertainty: at the "
          "optimum, the curvature of the log-likelihood says how sharply the data pin each "
          "parameter down. Minus the matrix of second derivatives of ln L at the fit is the "
          "<b>observed information</b>; its inverse is the covariance of the estimates, the square "
          "roots of its diagonal are the <b>standard errors</b>, and a 95% interval is the "
          "estimate plus or minus 1.96 standard errors (the Wald interval):"),
        F(r"$\mathrm{Cov}(\hat\theta) \approx [\,-H(\hat\theta)\,]^{-1},\qquad H = \text{second derivatives of } \ln L,\qquad "
          rf"\hat\theta \pm {Z95:.2f}\,\mathrm{{SE}}(\hat\theta)$"),
        P("The code takes the second derivatives numerically (central differences in the "
          "optimiser's scaled coordinates, one-sided where a parameter sits on a bound), checks that "
          "the matrix is positive definite, and inverts it "
          "(<font name='DejaVuSansMono'>_hessian</font>, "
          "<font name='DejaVuSansMono'>_covariance</font> in "
          "<font name='DejaVuSansMono'>core/quant/garch.py</font>). The persistence α + β gets its "
          "standard error from the same covariance by the delta method (its gradient is (0, 1, 1, 0)). "
          "The half-life interval is the persistence interval mapped through ln 0.5 / ln p: the map "
          "is monotone, so the half-life interval covers the truth exactly as often as the "
          "persistence interval does, and it can never go negative, which a symmetric interval "
          "around a short half-life would."),
        P(worked),
        P(reading) if reading else Spacer(1, 0),
        P("Three things the intervals do not do, each measured before the feature was built "
          "(<font name='DejaVuSansMono'>docs/B2_FIX_BULLETIN.md</font>):"),
        *B([
            "<b>The unconditional vol carries no interval on purpose.</b> Its delta-method interval "
            "was tried on simulated series and covered the truth 42% of the time when the fitted "
            "persistence was below 0.95, and 100% of the time, with an absurd width (a median "
            "standard error of 297 vol points), above 0.995. No threshold rescues it, so the "
            "near-integrated chip carries that message instead and the tile's tooltip says why.",
            "<b>They describe sampling error, not model error.</b> On series whose innovations were "
            "a skewed mixture rather than a t, the interval for the tail parameter covered the truth "
            "76% of the time: the standard error was the right size and the estimate was biased. "
            "The intervals assume the t is the right family.",
            f"<b>They can be undefined, and the failure is informative.</b> When a difference step "
            f"leaves the domain (a near-integrated fit next to the stationarity cap) or the "
            f"information matrix is not positive definite, the chip \"SE undefined\" appears with "
            f"the reason and the tiles show the values alone. The demo series does exactly that: "
            f"with α at 0 its β is unidentified and the note reads <i>{D.fit_demo.se_note}</i>. The "
            f"profile interval of chapter 6.5 still exists in that case.",
        ]),
        P("How good are they? On 50 simulated GARCH(1,1)-t series of 1,000 sessions the 95% "
          "intervals covered the true α, β and persistence 96%, 96% and 100% of the time; the "
          "acceptance test <font name='DejaVuSansMono'>test_interval_coverage_on_simulated_t_garch</font> "
          "asserts at least 85%. On 500 sessions the same study measured 91% to 97%, with α the "
          "short one: a symmetric interval on a positive parameter near 0 is the weak spot, and "
          "the bound chip is its warning."),
    ]


def ch6() -> list:
    f = D.fit
    return [
        P("6. Student-t innovations", "H1"),
        P("6.1 The t distribution and ν", "H2"),
        P(f"The Student-t distribution with ν (nu) degrees of freedom is bell-shaped like the normal "
          f"but with heavier tails; as ν grows it converges to the normal (at ν = 30 the two are "
          f"practically indistinguishable, and above ν = {NU_NORMAL:.0f}, where the excess kurtosis "
          f"is under 0.07, the app draws and displays the innovations as normal). Its variance is "
          f"ν/(ν − 2), finite only for ν > 2, and its excess kurtosis is"),
        F(r"$\kappa_t = \frac{6}{\nu - 4},\qquad \text{finite only for } \nu > 4$"),
        P(f"so a t with ν = 5 has excess kurtosis 6, ν = 8 gives 1.5, ν = 4 gives infinity. In the "
          f"model the innovation z<sub>t</sub> is a t draw scaled to unit variance, so ν describes "
          f"only the shape of the surprises, not their size — the size is σ<sub>t</sub>'s job. "
          f"Bollerslev (1987) introduced this pairing; it is the \"-t\" in GARCH(1,1)-t."),
        P("6.2 Scaling to unit variance: the classic bug", "H2"),
        P("Because a raw t draw has variance ν/(ν − 2) rather than 1, feeding it straight into "
          "ε<sub>t</sub> = σ<sub>t</sub> z<sub>t</sub> would inflate every variance by that factor "
          "and make ω, α, β and every VaR wrong by an amount that depends on ν. The code scales:"),
        F(r"$z_t = t_\nu \times \sqrt{\frac{\nu - 2}{\nu}}$"),
        CODE(f"""def _draw_z(rng, nu, dist, size, bound=Z_BOUND):        # Z_BOUND = {Z_BOUND}
    if dist != "t" or nu > NU_NORMAL:                       # normal, or a t drawn as one
        return rng.standard_normal(size=size)
    s = math.sqrt((nu - 2.0) / nu)
    z = rng.standard_t(nu, size=size) * s
    ...                # |z| > bound: redrawn from the t restricted to [-bound, bound]
    return z"""),
        P(f"Simulated t innovations are also capped at ±{Z_BOUND}: a draw beyond the cap is replaced "
          f"by one from the same t restricted to the cap, nothing is rescaled, so inside the cap the "
          f"law is the fitted density. The cap exists because under an unbounded t the simulated "
          f"price has no finite mean and no risk-neutral drift can exist; the Quant Lab's bound note "
          f"(chapter 9.5) states what the cap removes, and the horizon-vol tile describes the paths "
          f"actually drawn."),
        P("The same factor appears inside the likelihood (chapter 7.3): the density is written for "
          "the scaled variable, so the fitted σ<sub>t</sub> is a true standard deviation. Getting "
          "one of the two places right and the other wrong is the classic mistake, and it is silent: "
          "the fit still converges, the numbers still look plausible. Two checks exist for it. The "
          "self-check in <font name='DejaVuSansMono'>python -m core.quant.garch</font> draws 200,000 "
          "scaled innovations and asserts their variance is within 3% of 1; the acceptance test "
          "<font name='DejaVuSansMono'>test_garch_scaled_t_shocks_have_unit_variance</font> "
          "simulates with α = β = 0 (so σ<super>2</super> = ω exactly) and asserts the sample "
          "variance over ω is 1 and the kurtosis is still fat."),
        P("6.3 Reading ν, and the η = 1/ν parameterisation", "H2"),
        P(f"The fit does not search over ν directly but over η = 1/ν on [0, {ETA_MAX}]. Two things "
          f"follow. η = 0 <i>is</i> the normal model: as ν → ∞ the t density converges to the "
          f"normal term by term, so the normal GARCH is a point inside the t model's parameter "
          f"space rather than a limit it can never reach. And η = {ETA_MAX} is ν = {NU_MIN}, the "
          f"heaviest tail allowed. There is no upper bound on ν any more. A fit that lands at "
          f"η = 0, or at a ν above {NU_NORMAL:.0f}, is reported as \"normal innovations\" on a muted "
          f"chip, the tile reads \"normal\", and the sampler draws normal innovations: that is an "
          f"answer, not a failure. Before this parameterisation ν was capped at 30, the cap "
          f"excluded the normal from the t model, and a series with no heavier tail sat on the cap "
          f"with a red chip and a likelihood-ratio statistic that could come out negative."),
        P(f"On daily equity data ν typically lands between 3 and 8: clearly fatter than normal. The "
          f"worked fit gives ν = {f.nu:.1f} (excess kurtosis of the innovations "
          f"{('%.2f' % f.kurtosis_excess) if math.isfinite(f.kurtosis_excess) else 'infinite, ν ≤ 4'}). "
          f"A ν at {NU_MIN} (η at {ETA_MAX}) means the sample wants tails heavier than the model "
          f"allows, usually a handful of extreme days dominating a short window; the variance of the "
          f"innovation is still finite there but only just, and the fit is fragile. The screen shows "
          f"\"at bound: nu\" and the narrative says \"tails heavier than the model allows\". The "
          f"app's demo series, a GBM path, lands on the normal: its fit reports "
          f"{'normal innovations (η = 0)' if math.isinf(D.fit_demo.nu) else f'ν = {D.fit_demo.nu:.0f}, effectively normal'} "
          f"with the note <i>{D.fit_demo.note}</i>"),
        P("6.4 The likelihood-ratio test: t versus normal, with the null on the boundary", "H2"),
        P("The t model has one more parameter than the normal GARCH and contains it at η = 0. "
          "Twice the gain in log-likelihood from the extra parameter is the likelihood-ratio "
          "statistic:"),
        F(r"$\mathrm{LR} = 2\,(\ln L_t - \ln L_{\mathrm{normal}}) \geq 0$"),
        P("It cannot be negative, because the best t fit is at least the best normal fit. The code "
          "makes sure of it: the t fit is seeded from the normal optimum (with η = 0), the normal is "
          "then re-fitted from the t's (ω, α, β) so the reference is the best normal reachable "
          "through the same code path, and the statistic is clamped at 0 against optimiser "
          "tolerance. The null hypothesis η = 0 lies on the <i>boundary</i> of [0, 0.4], so the "
          "textbook χ<super>2</super><sub>1</sub> result does not apply: about half the time the "
          "fit lands exactly on the normal and LR = 0, and the null distribution is the mixture "
          "(Self and Liang, 1987)"),
        F(rf"$\mathrm{{LR}} \sim \frac{{1}}{{2}}\,\delta_0 + \frac{{1}}{{2}}\,\chi^2_1,\qquad 5\%\ \text{{critical value }} {LR_5PCT}$",
          r"$(3.841,\ \text{the } \chi^2_1 \text{ value, is its } 2.5\%\ \text{point})$"),
        P(f"<font name='DejaVuSansMono'>fit_garch</font> fits both models on the same data and "
          f"stores <font name='DejaVuSansMono'>lr_t_vs_normal</font>. The screen shows it as the "
          f"\"LR t vs normal\" tile, green when it exceeds "
          f"<font name='DejaVuSansMono'>LR_5PCT = {LR_5PCT}</font> and grey otherwise; it is greyed "
          f"as well when α sits at its bound, because the mixture assumes α and β interior. The "
          f"narrative says \"innovation tails heavier than normal\" or \"the t tail did not beat a "
          f"normal GARCH on this sample\". Worked fit: ln L<sub>t</sub> = {f.loglik:.1f}, "
          f"ln L<sub>normal</sub> = {f.loglik_normal:.1f}, LR = {f.lr_t_vs_normal:.1f}, "
          f"{'significant' if f.lr_t_vs_normal > LR_5PCT else 'not significant'} at 5%. On the GBM "
          f"demo series LR = {D.fit_demo.lr_t_vs_normal:.1f}: nothing to gain from the t, as it "
          f"should be. The acceptance test "
          f"<font name='DejaVuSansMono'>test_lr_is_nonnegative_and_correctly_sized_under_the_null</font> "
          f"fits 200 normal-innovation series and checks that LR is never negative, that between 30% "
          f"and 70% of the fits land exactly at η = 0, and that the share above {LR_5PCT} stays "
          f"within sampling error of 5%."),
        *sec_6_5(),
    ]


def sec_6_5() -> list:
    """6.5: the profile interval for nu (B2)."""
    f, fd = D.fit, D.fit_demo
    nu_lo, nu_hi = f.nu_interval
    dlo, dhi = fd.nu_interval
    at_floor = "nu" in f.interval_at_bound
    return [
        P("6.5 How precisely is ν known? The profile interval", "H2"),
        P("A symmetric interval is the wrong shape for ν. The likelihood is flat towards the normal "
          "(a ν of 20 and a ν of 200 are nearly the same model) and steep towards 2.5, and the "
          "fitted coordinate η has a bound at 0 where the normal lives. The app therefore inverts "
          "the likelihood-ratio test instead of using a standard error: it re-maximises ln L over "
          "(ω, α, β) at each η on a grid from 0 to 0.4, which gives the <b>profile likelihood</b>, "
          "and keeps every η at which the profile stays within a cut of the maximum:"),
        F(rf"$\{{\,\eta : \max_{{\omega,\alpha,\beta}} \ln L(\omega,\alpha,\beta,\eta) \geq \ln L_{{\max}} - c\,\}}$",
          rf"$c = {PROFILE_CUT:.2f}\ \text{{inside }} (0,\,{ETA_MAX}],\qquad c = {PROFILE_CUT0:.3f}\ \text{{at }} \eta = 0$"),
        P(f"The inside cut {PROFILE_CUT:.2f} is half the χ<super>2</super><sub>1</sub> 95% point "
          f"(3.841/2). At η = 0 the null is the boundary mixture of chapter 6.4, so the cut there is "
          f"half of {LR_5PCT}, and the interval reaches \"normal\" exactly when the LR tile says the t "
          f"did not beat the normal; between 0 and the first grid point the cut ramps between the two "
          f"values so the end moves continuously with the data. The ends are mapped back by "
          f"ν = 1/η, so the range is asymmetric and can be one-sided. Worked fit: ν = {f.nu:.1f} "
          f"({_nu_txt(nu_lo)} to {_nu_txt(nu_hi)}); the tile reads \"{D.tiles['nu (tail)']}\". Demo "
          f"series: {_nu_txt(fd.nu)} ({_nu_txt(dlo)} to {_nu_txt(dhi)}). Figure 6 shows both "
          f"profiles with their cuts and intervals."),
        P((f"Reading. The lower end sits on the ν floor {NU_MIN}: the sample would like tails at "
           f"least as heavy as the model allows, and the chip \"interval touches a bound: nu\" says "
           f"so; the upper end {_nu_txt(nu_hi)} is the honest one. "
           if at_floor else
           f"Reading. Both ends are interior: the data reject tails lighter than ν = {_nu_txt(nu_hi)} "
           f"and heavier than ν = {_nu_txt(nu_lo)} at 5%. ")
          + "On 50 simulated series of 1,000 sessions with a true ν of 6 the profile interval "
            "covered the truth 90% of the time and its median ran from 4.3 to 9.0: four years of "
            "daily data identify ν to within a factor of two, no better, and two years to within "
            "a factor of three. A ν shown to one decimal is a point estimate; the bracket is what "
            "the sample knows."),
        P("The scan has a second use. Each profile point is a full refit of (ω, α, β) at a fixed η, "
          "so if any of them beats the joint fit's log-likelihood the optimiser had stalled short of "
          "the maximum; <font name='DejaVuSansMono'>fit_garch</font> then re-seeds the joint fit "
          "from that point (chapter 7.5). The check found a dead starting value that had been in "
          "the code since the beginning. Each refit warm-starts from the previous grid point, and "
          "where the result lands outside the cut, which is where an end of the interval is "
          "decided, it is retried from the joint optimum: a single warm-started run can stall on a "
          "flat ridge (the demo series, with α = 0, has one), which would dent the profile and "
          "narrow the interval. Figure 6 runs both starts at every point."),
        FIG(6, f"Top left: the log-likelihood of the worked series as a function of β with ω, α and η "
               f"held at their optimum; the dot is the fitted maximum (β = {f.beta:.3f}), the dashed "
               f"line the bound at {BOUNDS['beta'][1]}, the dotted line where the stationarity penalty "
               f"starts. Top right: the profile log-likelihood of the worked series in η = 1/ν, with "
               f"the inside cut (dashed), the boundary cut at η = 0 (red tick) and the 95% interval "
               f"(shaded): ν {_nu_txt(nu_lo)} to {_nu_txt(nu_hi)}. Bottom: the same for the app's GBM "
               f"demo series, synthetic_history(\"AAPL\"): the maximum sits at the normal end and the "
               f"interval runs from ν = {_nu_txt(dlo)} to normal, so the tile says \"normal\"."),
    ]


def ch7() -> list:
    f, fd = D.fit, D.fit_demo
    k_t, k_n, k_g = 4, 3, 2
    aic_gbm = 2 * k_g - 2 * f.loglik_gbm
    return [
        P("7. Maximum likelihood, log-likelihood, and the guardrails", "H1"),
        P("7.1 What a likelihood is", "H2"),
        P("Fix a set of parameters θ = (ω, α, β, η), η = 1/ν. The model then says how probable each observed "
          "return was: the density of r<sub>t</sub> given the variance the recursion assigns to that "
          "day. Multiply those densities over all T days and you have the probability density of the "
          "whole sample, <i>as a function of θ</i>. That function is the likelihood L(θ). Maximum "
          "likelihood picks the θ under which the data you actually saw were most probable. It is "
          "not the probability that θ is true; it is a score, and the fit is the θ with the best "
          "score."),
        P("7.2 Why the log", "H2"),
        P("A product of 500 densities around 40 each is 40<super>500</super>, far outside what a "
          "floating-point number can hold, and its derivative is unmanageable. Taking logs turns the "
          "product into a sum, keeps every term in a sane range, and leaves the maximiser unchanged "
          "because the log is increasing. Every number the app calls \"loglik\" is ln L, and "
          "differences of ln L (not ratios of L) are what the LR test and AIC use."),
        P("7.3 The per-observation formulas, as implemented", "H2"),
        P("With ε<sub>t</sub> = r<sub>t</sub> − μ and the variance path σ<sub>t</sub><super>2</super> "
          "from the recursion, the normal GARCH contributes, per day,"),
        F(r"$\ln L_t = -\frac{1}{2}\ln(2\pi) - \frac{1}{2}\ln\sigma_t^2 - \frac{\varepsilon_t^2}{2\,\sigma_t^2}$"),
        P("and the unit-variance Student-t contributes"),
        F(r"$\ln L_t = c(\nu) - \frac{1}{2}\ln\sigma_t^2 - \frac{\nu + 1}{2}\,"
          r"\ln\!\left(1 + \frac{\varepsilon_t^2}{(\nu - 2)\,\sigma_t^2}\right),$"),
        F(r"$c(\nu) = \ln\Gamma\!\left(\frac{\nu + 1}{2}\right) - \ln\Gamma\!\left(\frac{\nu}{2}\right) - \frac{1}{2}\ln\left(\pi\,(\nu - 2)\right)$"),
        P("The (ν − 2) in the denominator is the unit-variance scaling of chapter 6.2 written into "
          "the density. As η = 1/ν → 0 the t term converges to the normal term and c(ν) to "
          "−½ ln(2π), so at η = 0 the code uses the normal formula outright: the t contains the "
          "normal exactly, which is what makes the likelihood ratio of chapter 6.4 non-negative. "
          "The code is a direct transcription; <font name='DejaVuSansMono'>_t_const</font> is c(ν) "
          "(<font name='DejaVuSansMono'>gammaln</font> is ln Γ) and "
          "<font name='DejaVuSansMono'>np.log1p(x)</font> is ln(1 + x) computed accurately for "
          "small x:"),
        CODE("""if dist == "t" and params[3] >= _ETA_EPS:            # eta = 1/nu; eta = 0 IS the normal
    nu = 1.0 / params[3]
    ll = (_t_const(nu) - 0.5 * np.log(s2)
          - ((nu + 1) / 2) * np.log1p(eps2 / ((nu - 2) * s2)))
else:                                                # normal, or a t with eta = 0
    ll = -0.5 * math.log(2 * math.pi) - 0.5 * np.log(s2) - eps2 / (2 * s2)
return float(np.sum(ll))"""),
        P("Above ν = 10<super>4</super> the two ln Γ terms of c(ν) are each of order ν and cancel "
          "catastrophically (at ν = 10<super>8</super>, the finite-difference step the optimiser "
          "takes from η = 0, they produced spurious gradients of 2 × 10<super>−5</super>), so "
          "<font name='DejaVuSansMono'>_t_const</font> switches there to the Stirling expansion "
          "½ ln(ν / (2π(ν − 2))) − 1/(4ν). The GBM benchmark is the same normal formula with one "
          "constant variance, the sample variance with ddof = 1, and the sample mean "
          "(<font name='DejaVuSansMono'>loglik_iid_normal</font>). Three things are checked before "
          "the sum: α + β above the stationarity cap returns the penalty −10<super>10</super>; any "
          f"non-finite or non-positive variance on the path returns the same penalty; and η ≤ "
          f"{ETA_MAX} keeps ν ≥ {NU_MIN}, so ν − 2 never reaches zero."),
        P("7.4 AIC and BIC", "H2"),
        P("A model with more parameters always reaches a higher likelihood on the sample it was "
          "fitted to. Information criteria charge for the extra parameters:"),
        F(r"$\mathrm{AIC} = 2k - 2\ln L,\qquad \mathrm{BIC} = k\ln T - 2\ln L$"),
        P(f"where k is the number of estimated parameters (k = {k_t} for GARCH-t: ω, α, β, η; "
          f"{k_n} for the normal GARCH; {k_g} for GBM: mean and variance) and T the number of "
          f"returns. Lower is better; BIC penalises parameters harder as T grows. The app shows "
          f"<b>ΔAIC vs GBM</b> = AIC<sub>GBM</sub> − AIC<sub>GARCH-t</sub>: positive means GARCH "
          f"earned its parameters. Worked fit: AIC<sub>GARCH-t</sub> = 2×{k_t} − 2×{f.loglik:.1f} = "
          f"{f.aic:.1f}, AIC<sub>GBM</sub> = 2×{k_g} − 2×{f.loglik_gbm:.1f} = {aic_gbm:.1f}, "
          f"ΔAIC = {f.delta_aic_vs_gbm:+.1f}; BIC = {f.bic:.1f}. A rule of thumb: a ΔAIC above 10 "
          f"is decisive, between 2 and 10 is meaningful, below 2 is a tie. On the GBM demo series "
          f"ΔAIC = {fd.delta_aic_vs_gbm:+.1f}: the tile is grey and the narrative says \"GBM is not "
          f"beaten here\", which is the correct answer for a series that <i>is</i> GBM."),
        P("7.5 Numerical optimisation: L-BFGS-B, starts, bounds, convergence", "H2"),
        P("There is no formula for the θ that maximises ln L; a numerical optimiser climbs the "
          "surface. The code uses SciPy's L-BFGS-B, a quasi-Newton method that accepts box bounds "
          "on each parameter, and minimises −ln L. Five details matter:"),
        *B([
            f"<b>Starting values.</b> α<sub>0</sub> = 0.05, η<sub>0</sub> = 1/8 (ν<sub>0</sub> = 8), "
            f"and ω<sub>0</sub> = var(ε)(1 − α<sub>0</sub> − β<sub>0</sub>) so that the start already "
            f"has the sample variance as its unconditional level. β<sub>0</sub> is tried at 0.80, "
            f"0.90 and 0.94 — three runs, keep the best (the multi-start). The surface has a long "
            f"ridge along α + β ≈ constant and flat regions in η; one start can stop on a shoulder. "
            f"The third value used to be 0.95, which with α<sub>0</sub> = 0.05 started exactly on "
            f"the stationarity penalty with ω<sub>0</sub> = 0, so it was dead and some 500-session "
            f"fits stalled below the maximum; the profile scan of chapter 6.5 caught it and now "
            f"re-seeds the fit whenever one of its refits beats the joint fit. The t fit is also "
            f"seeded from the normal optimum (chapter 6.4).",
            f"<b>Scaling.</b> ω is optimised in units of 10<super>−6</super> "
            f"(<font name='DejaVuSansMono'>_OMEGA_SCALE</font>). At its natural scale, ~10<super>−6</super>, "
            f"the finite-difference gradient in ω swamps the others and L-BFGS-B stops after a "
            f"handful of iterations with α still at its start. The comment in "
            f"<font name='DejaVuSansMono'>_fit</font> records this; it was a real bug.",
            f"<b>Bounds.</b> <font name='DejaVuSansMono'>BOUNDS</font> = ω ∈ "
            f"[{BOUNDS['omega'][0]:g}, ∞), α ∈ [{BOUNDS['alpha'][0]}, {BOUNDS['alpha'][1]}], "
            f"β ∈ [{BOUNDS['beta'][0]}, {BOUNDS['beta'][1]}], η ∈ [0, {ETA_MAX}] (ν ≥ {NU_MIN}, "
            f"no upper bound), plus the stationarity penalty at α + β > {STATIONARITY_MAX}. "
            f"A parameter within 10<super>−4</super> (relative; absolute at zero) of a bound is "
            f"listed in <font name='DejaVuSansMono'>at_bound</font>; η at {ETA_MAX} is listed as "
            f"\"nu\", and η at 0 is not a bound hit but the normal (chapter 6.3).",
            "<b>Convergence.</b> <font name='DejaVuSansMono'>converged</font> is the optimiser's own "
            "success flag for the best start. False means it stopped for a reason other than "
            "\"no further improvement\": iteration limit, a line search that failed, a non-finite "
            "objective. The screen shows a red chip.",
            "<b>Precision.</b> After the optimum the code takes the observed information for the "
            "Wald intervals (chapter 5.8) and scans the profile in η for the ν interval (chapter 6.5); "
            "together they cost about as much as the fit itself. "
            "<font name='DejaVuSansMono'>fit_garch(profile=False)</font> skips the scan for callers "
            "that fit in loops.",
        ]),
        P("7.6 The guardrails, one by one", "H2"),
        P("Each row is one guardrail in <font name='DejaVuSansMono'>core/quant/garch.py</font>: what "
          "it is, why it exists, what the screen shows when it binds, what to do, and whether it is "
          "safe to change. The screen strings are quoted from "
          "<font name='DejaVuSansMono'>ui/quant_lab_page.py</font> and "
          "<font name='DejaVuSansMono'>core/quant/insights.py</font>."),
        guardrail_table(),
        P("7.7 The modifications ladder", "H2"),
        BOX("Green — change freely; they change the question, not the estimator", [
            "<b>Horizon</b> (5 to 1,260 sessions), <b>paths</b> (200 to 100,000), <b>target price</b>: "
            "read off the same paths; more paths only shrink the Monte Carlo error (chapter 2.6).",
            "<b>Seed</b> (the <font name='DejaVuSansMono'>seed</font> argument): a different but "
            "equally valid set of paths; use two seeds to see the Monte Carlo error with your own eyes.",
            "<b>Drift mode and ERP</b>: move the centre of the cone; the width is untouched (chapter 8).",
            "<b>Symbol and window length</b> (the <font name='DejaVuSansMono'>days</font> argument of "
            "<font name='DejaVuSansMono'>load_history</font>, 504 in the app): more history makes ν "
            "and the persistence better determined and the guardrails less likely to bind; fewer than "
            "100 returns is refused.",
        ], "#2e7d32"),
        BOX("Amber — allowed, but know what can go wrong", [
            f"<b>NU_NORMAL</b> ({NU_NORMAL:.0f}): the ν above which the t is drawn and displayed as "
            f"normal. Raising it changes nothing visible (the excess kurtosis above 100 is under "
            f"0.07); lowering it below about 30 labels light-but-real tails as normal. It is not a "
            f"bound of the fit: η runs freely down to 0. The η ceiling {ETA_MAX} (ν = {NU_MIN}) is "
            f"red: the t's variance needs ν > 2, and the likelihood is badly behaved below 2.5.",
            f"<b>The profile cuts</b> ({PROFILE_CUT:.2f} inside, {PROFILE_CUT0:.3f} at η = 0) and the "
            f"interval-at-bound rules only decide what the ν range and the two interval chips say. "
            f"The boundary cut must stay half of LR_5PCT, or the range can say \"normal\" while the "
            f"LR tile says the t won.",
            f"<b>The persistence cap</b> ({STATIONARITY_MAX} in the objective, 0.995 for the flag). "
            f"The flag threshold is only a warning level and is safe to tune. The penalty must stay "
            f"strictly below 1: at α + β = 1 the unconditional variance divides by zero and the "
            f"forecast recursion no longer converges, so the uncond-vol tile, the half-life and "
            f"the horizon vol all become undefined.",
            f"<b>The α cap</b> ({BOUNDS['alpha'][1]}) and the starting values. A higher α cap lets a few "
            f"outliers dictate the fit; a different β<sub>0</sub> set is fine as long as the three "
            f"starts still bracket 0.8 to 0.94 and every start satisfies α<sub>0</sub> + β<sub>0</sub> "
            f"< {STATIONARITY_MAX} (a start on the penalty is dead, chapter 7.5); an η<sub>0</sub> far "
            f"from 1/8 (say 0.38 or 0.04) starts the solver on a flat part of the surface and raises "
            f"the chance of a false convergence.",
            f"<b>The minimum sample</b> (<font name='DejaVuSansMono'>_MIN_OBS = 100</font>). Raising it "
            f"is safe (the app then refuses more series); lowering it lets four parameters be fitted "
            f"to a few dozen points and the numbers will be noise.",
            f"<b>LR_5PCT</b> ({LR_5PCT}) decides the colour of one tile, one sentence, and the "
            f"boundary end of the ν range. It is the 5% point of the boundary mixture "
            f"½δ<sub>0</sub> + ½χ<super>2</super><sub>1</sub>, not of χ<super>2</super><sub>1</sub> "
            f"(3.841 would be the 2.5% level); replacing it with another number makes the label "
            f"\"5%\" a lie. Use 5.412 if you want the 1% level and say so.",
        ], "#c77c00"),
        BOX("Red — a mistake here silently corrupts every number on the screen", [
            "<b>The likelihood formulas</b> in <font name='DejaVuSansMono'>_loglik</font> (chapter 7.3): "
            "a wrong constant, a missing ½, ν instead of ν − 2. The fit still converges; α, β, ν and "
            "every VaR are then wrong by an amount nobody can see.",
            "<b>The unit-variance scaling</b> √((ν − 2)/ν) in <font name='DejaVuSansMono'>_draw_z</font> "
            "and the matching (ν − 2) inside the density. The two must agree.",
            "<b>The variance recursion and its start</b>: <font name='DejaVuSansMono'>_variance_path</font> "
            "(the filter coefficients [1, −β] and x<sub>t</sub> = ω + α ε<sub>t−1</sub><super>2</super>), "
            "its start at var(ε), the alignment that makes the last element σ<sub>T+1</sub><super>2</super>, "
            "and the forecast recursion in <font name='DejaVuSansMono'>forecast_variance</font>. An "
            "off-by-one here makes the conditional vol lag or lead the data by a day and shifts every fan.",
            "<b>The ω scaling</b> (<font name='DejaVuSansMono'>_OMEGA_SCALE</font>) and "
            "<b>TRADING_DAYS = 252</b>: the first decides whether the optimiser moves at all, the "
            "second every annualised number in the app and the FICC pages.",
        ], "#b22222"),
        P("7.8 How to tell that something broke", "H2"),
        P("Two checks exist, and they catch different things. "
          "<font name='DejaVuSansMono'>python -m core.quant.garch</font> is a thirty-second "
          "self-check: it simulates a GARCH(1,1)-t series with known parameters (ω = 2×10<super>−6</super>, "
          "α = 0.08, β = 0.90, ν = 6), refits it, and asserts α within 0.05, β within 0.06, ν in "
          "(4, 10), convergence, unit variance of the scaled draws within 3%, convergence of the "
          "5,000-step forecast to ω/(1 − α − β) within 1%, ln L<sub>t</sub> ≥ ln L<sub>normal</sub>, "
          "that every 95% interval on that series holds the truth, and that the ν range reaches the "
          "normal exactly when LR ≤ LR_5PCT. It ends by fitting a normal iid series and checking "
          "that LR ≥ 0, that the fit is effectively normal, and that it either has standard errors "
          "or says why not. If it prints \"ok\" the estimator is intact. The acceptance suite "
          "(<font name='DejaVuSansMono'>python tests/run_all.py</font>) is broader:"),
        TBL(["If you broke …", "This test fails"], [
            ["the t density, the normal density, or the recursion",
             "test_garch_recovers_parameters_on_simulated_series (parameters drift off 0.08 / 0.90 / 6); "
             f"test_garch_t_beats_normal_and_gbm_on_clustered_series (ln L ordering, LR > {LR_5PCT}, ΔAIC > 0, "
             "AIC and BIC arithmetic)"],
            ["the η parameterisation, the seeding that makes LR ≥ 0, or the profile's boundary rule",
             "test_lr_is_nonnegative_and_correctly_sized_under_the_null (200 normal series: LR ≥ 0, 30–70% "
             "at η = 0, size within sampling error of 5%, the ν range says \"normal\" exactly when the "
             "LR chip does, including inside the band 2.706 to 3.841)"],
            ["the covariance, its ω scaling, the one-sided steps, or the profile interval",
             "test_garch_recovers_parameters_on_simulated_series (standard errors within 15% of an independent "
             "computation, every interval holds the truth); test_interval_coverage_on_simulated_t_garch "
             "(50 fits: α, β, η and the profile cover at least 85%); test_intervals_reaching_a_bound_are_flagged"],
            ["the √((ν − 2)/ν) scaling in either place",
             "test_garch_scaled_t_shocks_have_unit_variance (variance over ω must be 1, kurtosis must stay fat)"],
            ["the recursion start, its alignment, or forecast_variance",
             "test_garch_forecast_variance_converges_to_unconditional (first step = cond_vol_last<super>2</super>, "
             "step 5,000 within 1% of ω/(1−α−β), horizon vol between today and the long run)"],
            ["a bound, the stationarity cap, the 100-observation rule, the fixed mean",
             "test_garch_respects_bounds_and_flags_on_gbm_series"],
            ["the drift plumbing in run_monte_carlo (which mode adds what, the −½σ<super>2</super>)",
             "test_mc_default_model_is_garch_t_seeded_and_reproducible, "
             "test_mc_zero_drift_lowers_median_on_positive_drift_series, "
             "test_drift_modes_are_ordered_and_documented, "
             "test_drift_zero_centres_the_cone_and_sample_reproduces_the_mean, test_unknown_drift_raises"],
            ["the narrative or the numbers it quotes",
             "test_garch_narrative_states_persistence_and_nu, test_narratives_state_their_numbers"],
            ["a chart", "test_every_chart_renders_a_data_uri_image"],
        ], widths=[5.6 * cm, 11 * cm], font=8, wrap=True),
        P("A change that passes both is not proven right, but a change that fails either is proven "
          "wrong, and the failing test names the formula."),
    ]


def guardrail_table() -> Table:
    rows = [
        [f"ω ≥ {BOUNDS['omega'][0]:g}<br/>(BOUNDS[\"omega\"]), optimised in units of 10<super>−6</super>",
         "A strictly positive floor on the variance constant.",
         "ω ≤ 0 makes the variance path zero or negative and ln σ<super>2</super> undefined; the "
         "scaling keeps the ω gradient comparable to the others so the optimiser moves.",
         "Chip \"at bound: omega\"; the \"Uncond vol (ann.)\" tile turns red; narrative "
         "\"unconditional vol undefined\"; note \"omega at bound: unconditional vol undefined\".",
         "Almost always a near-integrated fit (all variance carried by β). Use a longer history; "
         "check the closes for stale or duplicated prices.",
         "Red: the floor is a numerical necessity."],
        [f"α ∈ [{BOUNDS['alpha'][0]}, {BOUNDS['alpha'][1]}]",
         "The reaction to yesterday's surprise, capped at 0.5.",
         "An α above 0.5 on daily data means one 1-σ move doubles tomorrow's variance; that is an "
         "outlier artefact, not a market. The cap keeps the solver out of that corner.",
         "\"alpha\" tile red; chip \"at bound: alpha\"; narrative \"alpha at its cap: shock "
         "response is capped by the guardrail\". At α = 0 the same chip fires and the narrative says "
         "\"alpha at 0: no reaction to shocks, so beta and the half-life are not identified\"; the LR "
         "tile and the ν range are greyed (the boundary null assumes α interior).",
         "At 0: GARCH adds nothing, check ΔAIC and use GBM or the bootstrap. At 0.5: look at the "
         "outlier days, try the jump model, lengthen the window.",
         "Amber: raising the cap only matters when it binds; lowering it forces a false fit."],
        [f"β ∈ [{BOUNDS['beta'][0]}, {BOUNDS['beta'][1]}]",
         "The memory of last period's variance.",
         "β ≥ 1 is non-stationary on its own; 0.999 leaves room for α while keeping the recursion "
         "finite.",
         "\"beta\" tile red; chip \"at bound: beta\"; narrative \"near-integrated: the sample cannot "
         "pin down where vol settles; use a longer history\".",
         "Longer history; inspect the window for a regime break at its start.",
         "Amber; never 1 or above."],
        [f"α + β ≤ {STATIONARITY_MAX} (STATIONARITY_MAX); flag at > 0.995",
         "The objective returns −10<super>10</super> above the cap; fits above 0.995 are flagged.",
         "At α + β = 1 the unconditional variance is ω/0, the half-life is infinite and the forecast "
         "never converges; every long-run tile is meaningless.",
         "\"alpha+beta\" tile red; chip \"at bound: stationarity\"; narrative as for β; note "
         "\"near-integrated (alpha+beta > 0.995)\".",
         "Longer history. Treat the fan as valid for a few weeks only.",
         "Amber for the flag level; the cap must stay below 1."],
        ["T ≥ 100 returns (_MIN_OBS)",
         "fit_garch raises ValueError on fewer than 100 returns.",
         "Four parameters on fewer than 100 points is noise, and the optimiser would still return "
         "something plausible-looking.",
         "A red notice instead of a result: \"Need at least 100 observations to fit GARCH; got N.\"",
         "Load more history (FMP serves 504 sessions; KIS about 100 per request).",
         "Amber upward (raise it freely); red downward."],
        [f"η = 1/ν ∈ [0, {ETA_MAX}] (ν ≥ {NU_MIN}); NU_NORMAL = {NU_NORMAL:.0f}",
         "The tail parameter's box, in η. η = 0 is the normal and is not a bound hit.",
         "The variance ν/(ν−2) and the scaling need ν > 2; below ~2.5 the likelihood is badly "
         "behaved. There is no upper bound on ν: the normal is inside the model, so the LR test is "
         "well defined (chapter 6.4). Above NU_NORMAL the t is drawn as a normal.",
         "Lower (η at 0.4): \"nu (tail)\" tile red; chip \"at bound: nu\"; narrative \"tails heavier "
         "than the model allows\"; note \"nu at lower bound: tails heavier than the model allows\". "
         "Normal end: muted chip \"normal innovations\", tile \"normal\", narrative \"normal "
         "innovations (eta = 0)\" or \"nu = N, effectively normal\".",
         "Normal end: the t adds nothing; read the grey LR tile and ΔAIC, a normal GARCH is enough. "
         "Lower: a few extreme days dominate; look at them, try the jump model, lengthen the window.",
         "Amber for NU_NORMAL (a display and sampling level); red for the η ceiling (ν must stay > 2)."],
        ["Three starts: β<sub>0</sub> ∈ {0.80, 0.90, 0.94}, α<sub>0</sub> = 0.05, η<sub>0</sub> = 1/8; "
         "re-seeding from the profile scan",
         "L-BFGS-B is run three times plus once from the normal optimum; the highest ln L wins. If a "
         "profile refit (chapter 6.5) beats it, the fit is re-run from that point.",
         "The surface has a ridge along α + β ≈ const and flat stretches in η; a single start can "
         "stop on a shoulder and report a local optimum as the fit. A start on the stationarity "
         "penalty (the old β<sub>0</sub> = 0.95) is dead.",
         "Nothing when it works. A bad start shows up as converged = False or as an implausible "
         "parameter (β = 0, α at 0.5).",
         "Nothing normally; if fits look unstable between windows, add a start rather than remove one.",
         "Amber: adding starts is safe (slower); removing them invites local optima."],
        ["Observed information: Cholesky test, difference steps inside the domain",
         "The covariance of the estimates (chapter 5.8) exists only when the information matrix "
         "is positive definite and every difference step stays inside the domain.",
         "A singular or indefinite matrix (α = 0 leaves β unidentified; near-integrated fits next "
         "to the cap) has no meaningful inverse; printing a number there would be a lie.",
         "Chip \"SE undefined\" (red) with the reason as tooltip; the tiles show the values alone; "
         "narrative \"Standard errors undefined: …\"; note \"standard errors undefined: …\".",
         "Read the reason: usually the near-integrated or the alpha-at-0 case, both with their own "
         "row. The ν range (profile) still exists and is the fallback.",
         "Red to ignore; it is a flag, not a setting."],
        ["Interval reaches a bound: α, β (0 or the cap), ν (2.5), persistence (1)",
         "A 95% interval that crosses a guardrail is reported, not hidden.",
         "A symmetric interval on a parameter near a bound is only indicative; a persistence "
         "interval reaching 1 means an integrated variance is not excluded.",
         "Chip \"interval touches a bound: alpha, beta, nu\" (red); muted chip \"persistence interval "
         "reaches 1\"; the narrative repeats both; the half-life's upper end reads \"inf\".",
         "Longer history is the only cure. The point estimates stand; the sample does not "
         "support their precision.",
         "Amber: the rules only affect reporting. ω is deliberately left out of the chip (no tile)."],
        ["converged (res.success of the best start)",
         "The optimiser's own success flag.",
         "A fit that stopped on an iteration limit or a failed line search is not a maximum; its "
         "numbers can be anything.",
         "Chip \"solver did not converge\"; narrative \"the solver did not converge; treat the "
         "calibration as indicative\"; note \"solver did not converge\".",
         "Try another window length; inspect the series for zeros, splits or duplicated closes.",
         "Red to ignore; it is a flag, not a setting."],
        ["at_bound detection (tolerance 10<super>−4</super>)",
         "A parameter within 10<super>−4</super> (relative; absolute at 0) of a bound is listed.",
         "A bound-sitting value is the bound, not an estimate; the operator must be told.",
         "One chip per name: \"at bound: omega / alpha / beta / nu / stationarity\"; the matching tile "
         "red. If nothing binds and the precision chips are clear: \"GARCH guardrails clear\".",
         "Read the row for that parameter.",
         "Amber: the tolerance only affects reporting."],
        [f"LR_5PCT = {LR_5PCT}",
         "The 5% point of the boundary null ½δ<sub>0</sub> + ½χ<super>2</super><sub>1</sub> for the "
         "t-vs-normal test; also half of it is the profile interval's cut at η = 0.",
         "The null η = 0 sits on the boundary, so half the null fits land exactly at LR = 0; a gain "
         f"in 2 ln L above {LR_5PCT} occurs by chance only 5% of the time (3.841 would be 2.5%).",
         "\"LR t vs normal\" tile green (above) or grey, greyed too when α sits at its bound; "
         "narrative \"innovation tails heavier than normal\" or \"the t tail did not beat a normal "
         "GARCH on this sample\"; the ν range reads \"to normal\" exactly when the tile is grey.",
         "Grey: use the normal GARCH or accept that ν is uninformative on this window.",
         "Green in effect (colour, one sentence and one interval end), but keep it the mixture's "
         "true 5% point."],
    ]
    return TBL(["Guardrail", "What it is", "Why it exists", "What you see when it binds",
                "What to do", "Safe to change?"], rows,
               widths=[2.8 * cm, 2.4 * cm, 3.0 * cm, 3.3 * cm, 2.7 * cm, 2.4 * cm], font=7.2, wrap=True)


def ch8() -> list:
    md = D.mc_drift
    p252 = {row[0]: row for row in pooled_rows(252)}
    e252 = {row[0]: row for row in class_rows("equity", 252)}
    fx252 = {row[0]: row for row in class_rows("fx", 252)}
    kr252 = {row[0]: row for row in class_rows("korea", 252)}
    bg252 = {row[0]: row for row in class_rows("bond_gold", 252)}
    dmz = lambda m, h: study_val("dm_vs_zero", m, h, "dm_t_nw")
    dms = lambda m, h: study_val("dm_vs_sample_504", m, h, "dm_t_nw")
    w_all = study_val("shrink_weight", "shrink", 21, "mean_w")
    w_eq = study_val("shrink_weight", "shrink", 21, "mean_w", group="equity")
    w_fx = study_val("shrink_weight", "shrink", 21, "mean_w", group="fx")
    pooled_hdr = ["method", "n", "rmse", "mae", "bias", "skill vs zero", "hit rate", "coverage 90"]
    pooled_w = [2.9 * cm, 1.4 * cm, 1.7 * cm, 1.7 * cm, 1.9 * cm, 2.3 * cm, 1.9 * cm, 2.3 * cm]
    class_hdr = ["method", "n", "rmse", "bias", "skill vs zero", "hit rate", "coverage 90"]
    class_w = [3.0 * cm, 1.5 * cm, 1.9 * cm, 1.9 * cm, 2.5 * cm, 2.0 * cm, 2.3 * cm]
    dm_hdr = ["h", "method", "mean dloss", "DM t (NW)", "origins", "pairs"]
    dm_w = [1.3 * cm, 3.2 * cm, 2.6 * cm, 2.4 * cm, 2.0 * cm, 2.0 * cm]
    study_figs = [
        FIG(7, "Drift study — pooled RMSE of the horizon log-return forecast by horizon, per "
               "estimator (pass_1260). Reproduced from docs/drift_study/fig1_rmse_by_horizon.png.",
            str(STUDY / "fig1_rmse_by_horizon.png")),
        FIG(8, "Drift study — the trailing 504-session sample-mean forecast against the realised "
               "252-session log return, with the 45-degree line. The cloud has no slope: the "
               f"correlation is {D.corr_sample}. Reproduced from docs/drift_study/fig2_scatter_h252.png.",
            str(STUDY / "fig2_scatter_h252.png")),
        FIG(9, "Drift study — the shrinkage weight w placed on the sample mean against trailing "
               "volatility (τ = 0.05). For most equities w is below 0.1, so the shrink estimator is "
               "almost pure rf. Reproduced from docs/drift_study/fig3_shrink_weight.png.",
            str(STUDY / "fig3_shrink_weight.png")),
    ]
    return [
        P("8. Drift", "H1"),
        P("8.1 The least identifiable input", "H2"),
        P("Volatility can be estimated from a few hundred days because every day contributes a "
          "squared surprise. The mean cannot: a sample mean over T years of a series with annual "
          "volatility σ has standard error"),
        F(r"$\mathrm{SE}(\hat\mu) = \frac{\sigma}{\sqrt{T_{\mathrm{years}}}}$"),
        P(f"and nothing about sampling more often helps — daily data do not shrink it, only more "
          f"years do. A 25%-vol stock over the app's two-year window has "
          f"SE = 0.25/√2 = {pct(D.se_25_2y)} a year, on a drift that is itself perhaps 5 to 8%. "
          f"The estimate is two to three times noisier than the thing it estimates. Merton (1980) "
          f"made this point about expected returns; it has not become less true. The consequence "
          f"for the fan chart is that the centre of the cone, if it is the sample mean, is "
          f"essentially a random number that happens to have been positive in a bull market. The "
          f"study below measured exactly how random."),
        P("8.2 The estimators compared", "H2"),
        P("Every estimator produces an annualised log drift μ; the forecast for h sessions is "
          "F = μ h/252 and it is scored against the realised log return R = ln(P<sub>t+h</sub>/P<sub>t</sub>). "
          "σ is the trailing 504-session annualised vol, rf<sub>t</sub> the 3-month T-bill on the "
          "origin date."),
        *B([
            "<b>sample_126 / 252 / 504 / 1260</b>: the trailing mean of the last w daily log returns, "
            "times 252. sample_504 was the app's old default (two years).",
            "<b>zero</b>: μ = 0. The cone centres on spot.",
            "<b>rf</b>: μ = rf<sub>t</sub> − σ<super>2</super>/2. The risk-neutral log drift: a price "
            "that grows at the T-bill rate on average.",
            "<b>rf_erp</b>: μ = rf<sub>t</sub> + ERP − σ<super>2</super>/2, with ERP an assumption by "
            "asset class: 4% equities and equity ETFs, 1% TLT and GLD, 0 for FX.",
            "<b>shrink</b>: μ = w · sample_504 + (1 − w) · rf, with w = τ<super>2</super>/(τ<super>2</super> + σ<super>2</super>/2) "
            "and τ = 0.05: the sample mean weighted by how much it can be trusted against a prior "
            "standard deviation of 5%.",
            "<b>ewma_252</b>: an exponentially weighted mean of all daily log returns with a "
            "half-life of 252 sessions, times 252. Long memory with a gentle emphasis on recent years.",
            "<b>capm</b>: μ = rf<sub>t</sub> + β<sub>SPY</sub> × 4% − σ<super>2</super>/2, with β "
            "from a 504-session regression on SPY; only for US-listed names and EWY.",
            "<b>momentum_12_1</b>: the mean of the last 252 sessions excluding the most recent 21, "
            "times 252, clipped to ±30%. The classic momentum signal turned into a drift.",
        ]),
        P("8.3 The protocol", "H2"),
        P("Seventeen tickers from 2005: SPY, QQQ, IWM, AAPL, MSFT, NVDA, TSLA, XOM, JPM, KO (equity), "
          "TLT, GLD (bond/gold), EURUSD, USDJPY, USDKRW (FX), EWY and Samsung Electronics 005930.KS "
          "(Korea). An origin every 21 SPY sessions; at each origin every estimator is computed from "
          "data up to that date only, and scored at h = 21, 63, 126 and 252 sessions ahead. The main "
          "pass (pass_1260) requires 1,260 prior returns and 252 forward sessions at every origin, "
          "so all methods share the same 3,135 (ticker, origin) pairs; a second pass relaxes the "
          "look-back to 504. Metrics: RMSE and MAE of F − R; bias (mean of F − R); skill = 1 − "
          "MSE/MSE<sub>zero</sub>; hit rate = share of origins with the right sign; coverage = share "
          "of realised returns inside F ± 1.645 σ √(h/252) (target 0.90). The Diebold-Mariano test "
          "averages the squared-error differential across tickers at each origin and computes a "
          "Newey-West t-statistic on that time series (lag h/21, because origins overlap); |t| > 1.96 "
          "is the 5% line and a negative t means the method beats the baseline. Script: "
          "<font name='DejaVuSansMono'>docs/drift_study.py</font>; every number below is read from "
          "<font name='DejaVuSansMono'>docs/drift_study/results.csv</font>."),
        P("8.4 Results", "H2"),
        *P3("Pooled, pass_1260, h = 63"),
        TBL(pooled_hdr, pooled_rows(63), widths=pooled_w, font=8, align_right_from=1),
        *P3("Pooled, pass_1260, h = 252"),
        TBL(pooled_hdr, pooled_rows(252), widths=pooled_w, font=8, align_right_from=1),
        *P3("Diebold-Mariano, baseline = sample_504 (negative t: the method beats the old default)"),
        TBL(dm_hdr, dm_rows("sample_504"), widths=dm_w, font=8, align_right_from=2),
        *P3("Diebold-Mariano, baseline = zero (negative t: the method beats a flat zero)"),
        TBL(dm_hdr, dm_rows("zero"), widths=dm_w, font=8, align_right_from=2),
        *P3("Per asset class, pass_1260, h = 252 (CAPM only where a same-calendar benchmark exists)"),
        *P3("Equity"), TBL(class_hdr, class_rows("equity", 252), widths=class_w, font=8, align_right_from=1),
        *P3("Bond / gold"), TBL(class_hdr, class_rows("bond_gold", 252), widths=class_w, font=8, align_right_from=1),
        *P3("FX"), TBL(class_hdr, class_rows("fx", 252), widths=class_w, font=8, align_right_from=1),
        *P3("Korea"), TBL(class_hdr, class_rows("korea", 252), widths=class_w, font=8, align_right_from=1),
        *P3("How noisy the sample drift is, per ticker (sample_504, annualised)"),
        TBL(["ticker", "origins", "mean σ", "mean μ̂", "std of μ̂", "theory σ/√2"], se_rows(),
            widths=[3.0 * cm, 2.0 * cm, 2.2 * cm, 2.2 * cm, 2.4 * cm, 2.6 * cm], font=8, align_right_from=1),
        *study_figs,
        P("8.5 Reading the results", "H2"),
        *B([
            f"<b>The trailing two-year mean carries no forecast information.</b> Its correlation with "
            f"the realised 12-month return is {D.corr_sample} (figure 8). Per ticker, the estimate "
            f"itself swings from origin to origin with a standard deviation of the same order as "
            f"the volatility: NVDA's two-year drift moved with a standard deviation of "
            f"{study_val('se_sample_504', 'sample_504', 252, 'mu_std', group='NVDA') * 100:.1f}% a year.",
            f"<b>The old default loses to a flat zero at every horizon.</b> Pooled RMSE at h = 252: "
            f"sample_504 {p252['sample_504'][2]} against zero {p252['zero'][2]} (skill "
            f"{p252['sample_504'][5]}); at h = 63, {pooled_rows(63)[[r[0] for r in pooled_rows(63)].index('sample_504')][2]} "
            f"against {pooled_rows(63)[[r[0] for r in pooled_rows(63)].index('zero')][2]}. The DM test "
            f"against zero gives t = {dms('zero', 252):+.2f} at h = 252 in zero's favour — consistent "
            f"in direction but not significant at 5%, so the honest statement is \"no better than "
            f"zero, probably worse\". Shorter windows are significantly worse (sample_126 "
            f"t = {dmz('sample_126', 252):+.2f}, sample_252 t = {dmz('sample_252', 252):+.2f} against zero).",
            f"<b>Longer memory helps, but it is a regime, not a rule.</b> sample_1260 has the lowest "
            f"RMSE at every horizon (h = 252: {p252['sample_1260'][2]}, skill {p252['sample_1260'][5]}; "
            f"DM t = {dms('sample_1260', 252):+.2f} against sample_504, {dmz('sample_1260', 252):+.2f} "
            f"against zero — not significant). The gain comes entirely from the equity block "
            f"(equity h = 252 RMSE {e252['sample_1260'][2]} vs zero {e252['zero'][2]}); in FX it loses "
            f"to zero ({fx252['sample_1260'][2]} vs {fx252['zero'][2]}) and in Korea too "
            f"({kr252['sample_1260'][2]} vs {kr252['zero'][2]}). A five-year mean over 2010-2025 "
            f"mostly learned that US equities went up.",
            f"<b>rf + ERP ties zero and is never the worst.</b> h = 252 RMSE {p252['rf_erp'][2]} "
            f"(skill {p252['rf_erp'][5]}, DM t = {dmz('rf_erp', 252):+.2f} against zero: a tie). It is "
            f"the best full-sample method in FX ({fx252['rf_erp'][2]}) and Korea ({kr252['rf_erp'][2]}) "
            f"and ties for first in bond/gold ({bg252['rf_erp'][2]} vs shrink {bg252['shrink'][2]}); "
            f"it is never the worst in any class.",
            f"<b>Pure rf and shrink are significantly worse than zero</b> (DM t = "
            f"{dmz('rf', 252):+.2f} and {dmz('shrink', 252):+.2f}) while rf + ERP is not: the ERP "
            f"is doing the work. Pure rf forecasts a negative drift for high-vol names because of "
            f"the −σ<super>2</super>/2 (a 40%-vol name gets rf − 8%), which is why its h = 252 hit "
            f"rate is only {p252['rf'][6]}. It is a pricing measure, not a forecast. Shrinkage as "
            f"specified collapses onto rf: the mean weight on the sample mean is {w_all:.2f} "
            f"(equity {w_eq:.2f}, FX {w_fx:.2f}; figure 9).",
            f"<b>CAPM adds nothing</b> over rf + ERP on its equity-only sample (equity h = 252: "
            f"capm {e252['capm'][2]} vs rf_erp {e252['rf_erp'][2]} vs zero {e252['zero'][2]}, all "
            f"inside noise), and it needs a benchmark on the same calendar for every market. "
            f"<b>Momentum has no edge</b>: RMSE {p252['momentum_12_1'][2]}, hit rate "
            f"{p252['momentum_12_1'][6]}, indistinguishable from the up-drift of the period.",
            f"<b>Bias and coverage.</b> Every method is biased low at h = 252 (zero {p252['zero'][4]}, "
            f"rf_erp {p252['rf_erp'][4]}) because the period was an equity bull market; hit rates "
            f"above 0.5 for positive-drift methods come from that, not from timing. Coverage of the "
            f"90% band barely depends on the drift (zero {p252['zero'][7]}, rf_erp {p252['rf_erp'][7]}, "
            f"sample_1260 {p252['sample_1260'][7]}); only the noisy short windows pull it down "
            f"(sample_126 {p252['sample_126'][7]}). The width of the cone is the vol model's job, and "
            f"it does it.",
        ]),
        P("8.6 What the app offers now, and the default", "H2"),
        P(f"<font name='DejaVuSansMono'>DRIFTS = {DRIFTS}</font>. Every mode is an annualised "
          f"<i>log</i> drift μ; every model draws zero-mean shocks and adds μ/252 to each step "
          f"(<font name='DejaVuSansMono'>resolve_drift</font> in "
          f"<font name='DejaVuSansMono'>core/quant/montecarlo.py</font>). c̄ in the formulas is "
          f"each model's own per-step convexity correction ln E[exp(shock)], averaged over the "
          f"horizon: ½σ<super>2</super> of the sample variance for GBM, that plus the jump "
          f"compensator for the jump model, the block log-MGF increments for the bootstrap, and "
          f"c(σ<sub>t</sub>) from each path's own conditional variance for GARCH-t (tabulated per "
          f"ν and cap), so the mean price grows at the stated rate under every model. The app shows "
          f"the arithmetic under the stat strip and the narrative repeats it."),
        TBL(["Mode", "Dropdown label", "μ (annualised log drift)", "Inputs and where they come from"], [
            ["premium (default)", DRIFT_LABELS["premium"], "rf + ERP − c̄",
             "rf: 3-month T-bill, FRED DGS3MO, keyless, cached; if unreachable the app assumes "
             f"{pct(RF, 2)} and shows an error-toned chip \"rf {pct(RF, 2)} assumed (FRED "
             f"unreachable)\". ERP: the \"ERP %\" field, default {ERP * 100:.1f}, hint \"equity 4 / "
             "bonds-gold 1 / FX 0\"."],
            ["zero", DRIFT_LABELS["zero"], "0", "none; the cone centres on spot"],
            ["rf", DRIFT_LABELS["rf"], "rf − c̄",
             "rf as above; the risk-neutral measure of chapter 1.4 — a pricing assumption, not a forecast"],
            ["sample", DRIFT_LABELS["sample"], "mean of the window's daily log returns × 252",
             "price history only; kept for transparency and labelled noisy"],
        ], widths=[2.6 * cm, 4.2 * cm, 3.4 * cm, 6.4 * cm], font=8, wrap=True),
        P(f"On the worked series, GARCH-t, {HORIZON} sessions, {N_PATHS:,} paths, seed {SEED}, "
          f"rf {pct(RF, 2)} and ERP {pct(ERP, 1)}, the four modes give:"),
        TBL(["Mode", "μ (ann.)", "Drift sentence shown in the app", "Median terminal", "P(loss)", "VaR 95"], [
            [d, spct(md[d].mu_annual, 2), md[d].drift_note, f"{md[d].median_terminal:,.2f}",
             pct(md[d].prob_loss, 0), pct(md[d].var_pct)] for d in DRIFTS
        ], widths=[1.8 * cm, 1.8 * cm, 7.6 * cm, 2.2 * cm, 1.5 * cm, 1.7 * cm], font=7.5, wrap=True),
        P("Why the risk-premium mode is the default: statistically it ties zero, so zero would be "
          "an equally defensible choice; the case for rf + ERP is that it is never the worst method "
          "in any asset class, its centre has an economic reading you can argue with (a T-bill rate "
          "you can look up plus a premium you chose), and it degrades to zero for FX where the ERP "
          "is 0. Use zero for stress tests. Use rf to see what the pricing pages assume. Use sample "
          "only to see what the window's own history says, knowing its standard error."),
        P("The sample mode's sentence states its own standard error (σ/√2 for two years) so the "
          "number never appears without its noise. Note the VaR column: the drift moves the centre "
          "by roughly (μ × horizon) and the tail numbers follow it, but the shape of the cone is "
          "identical across the four rows because the volatility model is."),
    ]


def ch9() -> list:
    mc, f, t = D.mc_g, D.fit, D.tiles
    return [
        P("9. Reading the Quant Lab screen", "H1"),
        P(f"This chapter walks through one result top to bottom: the worked series, GARCH(1,1)-t, "
          f"{HORIZON} sessions, {N_PATHS:,} paths, the default drift with rf {pct(RF, 2)} and "
          f"ERP {pct(ERP, 1)}. The values are what the screen showed when this PDF was built from "
          f"the same code. Tile names are the exact labels in "
          f"<font name='DejaVuSansMono'>ui/quant_lab_page.py</font>."),
        P("9.1 The first stat strip", "H2"),
        TBL(["Tile", "Value here", "Meaning", "Chapter"], [
            ["Spot", f"{mc.spot:,.2f}", "the last close; every path starts here", "2.1"],
            ["Median terminal", f"{mc.median_terminal:,.2f}", "50th percentile of the terminal prices", "2.3"],
            ["90% range", f"{mc.p05:,.0f} – {mc.p95:,.0f}", "5th to 95th percentile of the terminal prices", "2.3"],
            ["P(loss)", pct(mc.prob_loss, 0), "share of paths ending below spot; red above 50%", "2.5"],
            ["VaR 95", pct(mc.var_pct), "95th percentile of the horizon loss, fraction of spot", "2.4"],
            ["CVaR", pct(mc.cvar_pct), "mean loss on the worst 5% of paths", "2.4"],
            ["Drift (ann.)", spct(mc.mu_annual), "the annualised log drift actually used (the mode's μ)", "8.6"],
            ["Vol (ann.)", pct(mc.sigma_annual), "GARCH: the next-session conditional vol; other models: the sample vol", "5.4"],
            ["P(target)", "only with a target", "share of paths at or above the target", "2.5"],
        ], widths=[2.6 * cm, 2.6 * cm, 8.8 * cm, 1.6 * cm], font=8, wrap=True),
        P(f"Under the strip, in muted text, the drift sentence: <i>{mc.drift_note}</i>. It is the "
          f"same string the narrative prints, produced by "
          f"<font name='DejaVuSansMono'>resolve_drift</font>."),
        P("9.2 The chips", "H2"),
        TBL(["Chip", "Here", "Meaning", "Chapter"], [
            ["source: FMP / KIS / SYNTHETIC", f"source: {D.H.source}",
             "where the closes came from; SYNTHETIC is grey and comes with a red notice above the strip", "0"],
            ["first date → last date", f"{D.H.first_date} → {D.H.last_date}", "the calibration window", "1.3"],
            ["N paths", f"{mc.n_paths:,} paths", "the Monte Carlo sample size", "2.6"],
            ["model label", "GARCH(1,1)-t (default)", "which shocks were drawn", "3.6"],
            ["drift: label", f"drift: {DRIFT_LABELS[mc.drift_mode]}", "the drift mode", "8.6"],
            ["rf chip (premium and rf modes)", f"rf {pct(RF, 2)} assumed (FRED unreachable)  or  rf x.xx% (FRED DGS3MO date)",
             "where the risk-free rate came from; error-toned when assumed", "8.6"],
        ], widths=[3.6 * cm, 4.6 * cm, 5.8 * cm, 1.6 * cm], font=8, wrap=True),
        P("9.3 The GARCH strip and the guardrail chips", "H2"),
        TBL(["Tile", "Value here (as the screen prints it)", "Meaning", "Red when", "Chapter"], [
            ["alpha", t["alpha"], "reaction to yesterday's surprise; (95% interval)", "at bound", "5.1, 5.8"],
            ["beta", t["beta"], "memory; (95% interval)", "at bound", "5.1, 5.8"],
            ["alpha+beta", t["alpha+beta"], "persistence; (95% interval, delta method)", "> 0.995 (stationarity)", "5.2, 5.8"],
            ["Half-life (sessions)", t["Half-life (sessions)"], "ln 0.5 / ln(α+β); (the persistence interval mapped through)",
             "never (shows inf)", "5.3, 5.8"],
            ["nu (tail)", t["nu (tail)"], "t degrees of freedom, or \"normal\"; (95% profile interval, \"normal\" = includes η = 0)",
             "at bound (2.5); grey when alpha at bound", "6.3, 6.5"],
            ["Cond vol (ann.)", t["Cond vol (ann.)"], "next-session forecast σ<sub>T+1</sub>", "never", "5.4"],
            ["Uncond vol (ann.)", t["Uncond vol (ann.)"], "√(ω/(1−α−β) × 252); no interval by design", "omega at bound", "5.2, 5.8"],
            ["Horizon vol (ann.)", t["Horizon vol (ann.)"], "average forecast vol over the horizon, for the bounded innovations actually drawn",
             "never", "5.5"],
            ["LR t vs normal", t["LR t vs normal"], "2(ln L<sub>t</sub> − ln L<sub>normal</sub>) ≥ 0",
             f"green above {LR_5PCT}, grey otherwise or when alpha at bound", "6.4"],
            ["dAIC vs GBM", t["dAIC vs GBM"], "AIC<sub>GBM</sub> − AIC<sub>GARCH-t</sub>",
             "green above 0, grey otherwise", "7.4"],
        ], widths=[2.6 * cm, 3.4 * cm, 4.4 * cm, 3.4 * cm, 1.8 * cm], font=7.5, wrap=True),
        P(f"Chips on this run: <b>{', '.join(D.chips)}</b>. The possible chips are \"at bound: omega\", "
          f"\"at bound: alpha\", \"at bound: beta\", \"at bound: nu\", \"at bound: stationarity\", "
          f"\"solver did not converge\", \"SE undefined\", \"interval touches a bound: …\" (all red), "
          f"then \"GARCH guardrails clear\" when none of those applies, and the muted "
          f"\"normal innovations\" and \"persistence interval reaches 1\". Chapter 7.6 has one row per "
          f"chip. For comparison, the demo series (Data source = Synthetic demo) shows: "
          f"<b>{', '.join(D.chips_demo)}</b>."),
        P("9.4 The three charts", "H2"),
        *B([
            "<b>Conditional vol chart</b> (GARCH only): the fitted σ<sub>t</sub> over the window "
            "against realised vol, as in figure 3. If the line ends well above the dashed "
            "unconditional level, the first weeks of the fan are wider than a GBM fan would be, "
            "and vice versa (chapter 4.3).",
            "<b>Fan chart</b>: the last 90 sessions of history, then the 5-95% and 25-75% bands and the "
            "median, with forty sample paths behind them and the target as a dashed line if given "
            "(chapter 2.3). The bands are percentiles per date, not paths.",
            "<b>Terminal histogram</b>: all terminal prices, spot as a solid line, the VaR 95 price "
            "as a dashed red line, the target in green (chapter 2.4). The distance between the "
            "solid and dashed lines is VaR in price terms; the mass to the left of the dashed line "
            "is the 5% whose average is CVaR.",
        ]),
        P("9.5 The narrative and every sentence it can produce", "H2"),
        P("The local narrative (<font name='DejaVuSansMono'>insights.narrate_monte_carlo</font>) is "
          "deterministic and needs no key; the Claude panel, when a key is set, receives the same "
          "numbers and adds an interpretation. On this run the local narrative read:"),
        CODE(_wrap(D.narrative, 86)),
        P("The sentences, in the order they can appear, and the condition for each:"),
        TBL(["Sentence template", "When", "Chapter"], [
            ["Across N simulated MODEL paths over H sessions, SYM ends at a median of M against a spot of S (±x%).", "always", "2.3"],
            ["The middle 90% of outcomes spans A to B; the simulation assigns a p% probability of finishing below spot.", "always", "2.3, 2.5"],
            ["Horizon VaR(95) is v% of position value, and the expected loss beyond that point (CVaR) is c%.", "always", "2.4"],
            ["Calibration (GARCH(1,1)-t on T sessions): conditional vol today x% against an unconditional y% [or an undefined unconditional level] and a H-session horizon vol of z%.", "GARCH-t", "5"],
            ["alpha a, beta b, persistence p — a variance shock halves in n sessions [or never decays (integrated variance)].", "GARCH-t", "5.3"],
            [f"nu = v [or normal innovations (eta = 0) / nu = N, effectively normal]: innovation tails heavier than normal [or the t tail did not beat a normal GARCH on this sample] [; alpha sits at its bound, so the LR reference distribution is only indicative] (LR l vs {LR_5PCT}).", "GARCH-t", "6.3, 6.4"],
            ["95% intervals: alpha a to b, beta c to d, persistence p to q (half-life m to n sessions) [or Standard errors undefined: reason]; nu x to y by profile likelihood [; indicative only with alpha at its bound] [; the interval reaches a bound for …, so it is indicative only] [; the persistence interval reaches 1, so an integrated variance is not excluded]. The unconditional vol carries no interval by design.", "GARCH-t", "5.8, 6.5"],
            ["dAIC vs GBM d — GARCH is preferred. [or GBM is not beaten here.]", "GARCH-t", "7.4"],
            ["Guardrails: the solver did not converge; treat the calibration as indicative; near-integrated: the sample cannot pin down where vol settles; use a longer history; tails heavier than the model allows; unconditional vol undefined; alpha at 0: no reaction to shocks, so beta and the half-life are not identified [or alpha at its cap: shock response is capped by the guardrail].", "one clause per flag", "7.6"],
            [f"t innovations are capped at ±{Z_BOUND}: this fit expects a larger day once per N years (P x% within the horizon); the cap drops y% of innovation variance, so the fan's vol over this horizon runs z% below the fit's own forecast and VaR/CVaR exclude those days. [or Innovations are effectively normal (the t fit found no heavier tail), so they are drawn unbounded and no cap applies.]", "GARCH-t, every drift mode", "6.2"],
            ["Calibration: annualized volatility x%.", "GBM, jump, bootstrap", "3"],
            ["Drift (risk-premium view) / Drift / Drift (risk-neutral) / Drift (sample mean): <the drift sentence>.", "always", "8.6"],
            ["Probability of reaching the T target: p%.", "target given", "2.5"],
            ["Calibrated k jump days out of T (λ=… /yr, mean jump …). [or No >3σ daily moves in the sample — jump model degrades to GBM.]", "jump model", "3.4"],
            ["The outcome cone is wide relative to spot — position sizing matters more than direction here.", "(p95 − p05)/spot > 0.8", "2.3"],
            ["The outcome cone is narrow — the calibrated volatility is low, so tail surprises would come from regime change, not from this distribution.", "(p95 − p05)/spot < 0.25", "2.3"],
        ], widths=[10.8 * cm, 3.6 * cm, 1.6 * cm], font=7.5, wrap=True),
    ]


def _wrap(text: str, width: int) -> str:
    import textwrap
    return "\n".join(textwrap.wrap(text, width))


def ch10() -> list:
    f = D.fit
    return [
        P("10. Glossary and formula sheet", "H1"),
        P("10.1 Symbols and terms", "H2"),
        TBL(["Symbol / term", "Meaning"], [
            ["P<sub>t</sub>", "close on session t"],
            ["r<sub>t</sub>", "daily log return ln(P<sub>t</sub>/P<sub>t−1</sub>)"],
            ["μ", "drift: expected daily (or, annualised, yearly) log return; μ<sub>annual</sub> = 252 μ<sub>daily</sub>"],
            ["σ, σ<sub>t</sub>", "volatility: standard deviation of the return; σ<sub>t</sub> is the conditional (time-t) value; σ<sub>annual</sub> = √252 σ<sub>daily</sub>"],
            ["σ̄<super>2</super>", "unconditional variance ω/(1 − α − β)"],
            ["ε<sub>t</sub>", "the surprise r<sub>t</sub> − μ"],
            ["z<sub>t</sub>", "innovation: mean 0, variance 1; N(0,1) or scaled t<sub>ν</sub>"],
            ["ω, α, β", "GARCH(1,1) floor, reaction, memory"],
            ["α + β", "persistence; half-life ln 0.5 / ln(α + β)"],
            ["ν", "Student-t degrees of freedom; tails fatter as ν falls; normal as ν → ∞"],
            ["η = 1/ν", f"the fitted tail coordinate on [0, {ETA_MAX}]; 0 is the normal, {ETA_MAX} is ν = {NU_MIN}"],
            ["κ", "excess kurtosis E[z<super>4</super>] − 3; for t<sub>ν</sub>: 6/(ν − 4)"],
            ["ln L", "log-likelihood; loglik in the code"],
            ["LR", f"likelihood-ratio statistic 2(ln L<sub>t</sub> − ln L<sub>normal</sub>) ≥ 0; null on the boundary: ½δ<sub>0</sub> + ½χ<super>2</super><sub>1</sub>, 5% point {LR_5PCT}"],
            ["observed information, SE", "minus the second derivatives of ln L at the fit; its inverse is the covariance of the estimates and the standard errors are the square roots of its diagonal"],
            ["Wald interval", f"estimate ± {Z95:.2f} SE; used for α, β, α + β (delta method) and, mapped through, the half-life"],
            ["profile likelihood, profile interval", f"ln L re-maximised over (ω, α, β) at each η; the η within {PROFILE_CUT:.2f} of the maximum ({PROFILE_CUT0:.3f} at η = 0), mapped to ν"],
            ["AIC, BIC", "2k − 2 ln L; k ln T − 2 ln L; lower is better; ΔAIC vs GBM = AIC<sub>GBM</sub> − AIC<sub>GARCH-t</sub>"],
            ["k, T", "number of parameters; number of returns"],
            ["h, H", "sessions ahead; the horizon"],
            ["VaR<sub>95</sub>, CVaR<sub>95</sub>", "95th percentile of the horizon loss; mean loss beyond it"],
            ["rf, ERP", "risk-free rate (3-month T-bill, FRED DGS3MO); equity risk premium, an assumption"],
            ["physical / risk-neutral measure", "the distribution you expect (simulate risk with) / the one that prices hedgeable claims (drift = rf)"],
            ["persistence, IGARCH", "α + β; the integrated case α + β = 1"],
            ["L-BFGS-B", "the bounded quasi-Newton optimiser used for the fit"],
            ["at_bound, converged", "the fit's list of bound-sitting parameters; the optimiser's success flag"],
            ["DM test", "Diebold-Mariano: a t-test on the difference of squared forecast errors between two methods"],
            ["skill", "1 − MSE/MSE<sub>zero</sub>; positive beats a zero forecast"],
            ["coverage", "share of realised values inside the model's 90% band"],
        ], widths=[4.2 * cm, 12.4 * cm], font=8.5, wrap=True),
        P("10.2 Formula sheet", "H2"),
        F(r"$r_t = \ln(P_t/P_{t-1});\qquad P_T = P_0\exp\!\left(\sum r_t\right)$"),
        F(r"$\mu_a = 252\,\mu_d;\qquad \sigma_a = \sqrt{252}\,\sigma_d;\qquad \mathrm{SE}(\hat\mu) = \sigma/\sqrt{T_{\mathrm{years}}}$"),
        F(r"$\text{GBM: } d\ln S = (\mu - \sigma^2/2)\,dt + \sigma\,dW;\qquad r_t = (\mu - \sigma^2/2)\,\Delta t + \sigma\sqrt{\Delta t}\,z_t$"),
        F(r"$\text{GARCH(1,1): } \sigma_t^2 = \omega + \alpha\,\varepsilon_{t-1}^2 + \beta\,\sigma_{t-1}^2;$",
          r"$\bar\sigma^2 = \omega/(1 - \alpha - \beta);\qquad \text{half-life} = \ln 0.5/\ln(\alpha + \beta)$"),
        F(r"$\text{Forecast: } \sigma_{T+h}^2 = \bar\sigma^2 + (\alpha + \beta)^{h-1}(\sigma_{T+1}^2 - \bar\sigma^2);$",
          r"$\text{horizon vol} = \sqrt{\mathrm{mean}_h\,\sigma_{T+h}^2 \times 252}$"),
        F(r"$\text{Scaled t: } z = t_\nu\sqrt{(\nu - 2)/\nu};\qquad \kappa = 6/(\nu - 4)$"),
        F(r"$\ln L_{\mathrm{normal},t} = -\frac{1}{2}\ln 2\pi - \frac{1}{2}\ln\sigma_t^2 - \varepsilon_t^2/(2\sigma_t^2)$"),
        F(r"$\ln L_{t,t} = \ln\Gamma((\nu+1)/2) - \ln\Gamma(\nu/2) - \frac{1}{2}\ln(\pi(\nu-2)) - \frac{1}{2}\ln\sigma_t^2$",
          r"$\qquad - \frac{\nu+1}{2}\,\ln\!\left(1 + \varepsilon_t^2/((\nu-2)\sigma_t^2)\right)$"),
        F(rf"$\mathrm{{LR}} = 2(\ln L_t - \ln L_{{\mathrm{{normal}}}}) \geq 0\ \text{{ vs }}\ \frac{{1}}{{2}}\delta_0 + \frac{{1}}{{2}}\chi^2_1\ (5\%) = {LR_5PCT};$",
          r"$\mathrm{AIC} = 2k - 2\ln L;\qquad \mathrm{BIC} = k\ln T - 2\ln L$"),
        F(rf"$\text{{Wald: }} \hat\theta \pm {Z95:.2f}\,\sqrt{{[-H]^{{-1}}_{{\theta\theta}}}};$",
          rf"$\text{{profile: }} \{{\,\eta : \ln L_p(\eta) \geq \ln L_{{\max}} - {PROFILE_CUT:.2f}\,\}}\ ({PROFILE_CUT0:.3f}\ \text{{at }} \eta = 0);\qquad \nu = 1/\eta$"),
        F(r"$L = 1 - P_T/\mathrm{spot};\qquad \mathrm{VaR}_{95} = Q_{0.95}(L);\qquad \mathrm{CVaR}_{95} = \mathrm{E}[L \mid L \geq \mathrm{VaR}_{95}]$"),
        F(r"$\text{Drift modes: premium } \mu = \mathrm{rf} + \mathrm{ERP} - \bar c;\quad \text{rf } \mu = \mathrm{rf} - \bar c;$",
          r"$\text{zero } \mu = 0;\quad \text{sample } \mu = 252\,\mathrm{mean}(r);$",
          r"$\bar c = \text{each model's per-step } \ln\mathrm{E}[\exp(\text{shock})],\ \frac{1}{2}\sigma^2\ \text{for GBM}$"),
        F(r"$\text{Monte Carlo error} \propto 1/\sqrt{N}$"),
        P("10.3 The worked fit in one line", "H2"),
        P(f"<font name='DejaVuSansMono'>{f.note}</font>"),
        P("10.4 References", "H2"),
        *B([
            "Engle, R. F. (1982). Autoregressive conditional heteroscedasticity with estimates of the variance of United Kingdom inflation.",
            "Bollerslev, T. (1986). Generalized autoregressive conditional heteroskedasticity.",
            "Bollerslev, T. (1987). A conditionally heteroskedastic time series model for speculative prices and rates of return.",
            "Merton, R. C. (1980). On estimating the expected return on the market: an exploratory investigation.",
            "Hull, J. C. Options, Futures, and Other Derivatives (chapters on Wiener processes, Itô's lemma and Monte Carlo simulation).",
            "Tsay, R. S. Analysis of Financial Time Series (chapter on conditional heteroscedastic models).",
            "Diebold, F. X. and Mariano, R. S. (1995). Comparing predictive accuracy.",
        ]),
    ]


# --------------------------------------------------------------------------- #
# Document
# --------------------------------------------------------------------------- #
MARGIN = 2.2 * cm


def _footer(canv, doc) -> None:
    canv.saveState()
    canv.setFont("DejaVuSans", 8)
    canv.setFillColor(colors.HexColor("#666666"))
    canv.drawString(MARGIN, 1.3 * cm, "QUANTGEN Models Primer")
    canv.drawRightString(A4[0] - MARGIN, 1.3 * cm, str(doc.page))
    canv.restoreState()


class PrimerDoc(BaseDocTemplate):
    def __init__(self, path: str):
        super().__init__(path, pagesize=A4, leftMargin=MARGIN, rightMargin=MARGIN,
                         topMargin=MARGIN, bottomMargin=MARGIN, title="QUANTGEN Models Primer",
                         author="QUANTGEN")
        frame = Frame(self.leftMargin, self.bottomMargin, self.width, self.height, id="body")
        self.addPageTemplates([PageTemplate(id="body", frames=[frame], onPage=_footer)])

    def afterFlowable(self, flowable) -> None:
        if isinstance(flowable, Paragraph) and flowable.style.name in ("H1", "H2"):
            level = 0 if flowable.style.name == "H1" else 1
            text = flowable.getPlainText()
            key = "s" + hashlib.md5(text.encode("utf-8")).hexdigest()[:10]
            self.canv.bookmarkPage(key)
            self.canv.addOutlineEntry(text, key, level=level, closed=level > 0)
            self.notify("TOCEntry", (level, text, self.page, key))


def build() -> int:
    story = (ch_title() + ch_toc() + ch0() + ch1() + ch2() + ch3() + ch4() + ch5() + ch6()
             + ch7() + ch8() + ch9() + ch10())
    doc = PrimerDoc(str(OUT_PDF))
    doc.multiBuild(story)
    pages = doc.page
    try:
        from pypdf import PdfReader
        pages = len(PdfReader(str(OUT_PDF)).pages)
    except Exception:
        pass
    return pages


def self_check() -> None:
    """No Unicode sub/superscript glyphs in this source, and every non-ASCII character
    the text uses exists in the DejaVu faces (a missing glyph renders as a black box)."""
    src = Path(__file__).read_text(encoding="utf-8")
    bad = sorted({c for c in src if 0x2070 <= ord(c) <= 0x209F or ord(c) in (0xB2, 0xB3, 0xB9)})
    assert not bad, f"Unicode sub/superscript glyphs in source: {bad}"
    try:
        from fontTools.ttLib import TTFont as _TT
    except Exception:
        return
    cmaps = {n: _TT(os.path.join(_FONT_DIR, fn)).getBestCmap()
             for n, fn in (("Sans", "DejaVuSans.ttf"), ("Serif", "DejaVuSerif.ttf"),
                           ("Mono", "DejaVuSansMono.ttf"))}
    non_ascii = {c for c in src if ord(c) > 127}
    missing = {n: sorted(c for c in non_ascii if ord(c) not in cm) for n, cm in cmaps.items()}
    assert not missing["Sans"], f"glyphs missing from DejaVuSans: {missing['Sans']}"
    # formulas use Serif; code uses Mono — warn rather than fail on characters only used in prose
    for n in ("Serif", "Mono"):
        if missing[n]:
            print(f"note: characters absent from DejaVu{n} (must not appear in formula/code text): "
                  f"{''.join(missing[n])}")


if __name__ == "__main__":
    self_check()
    n_pages = build()
    print(f"wrote {OUT_PDF} ({n_pages} pages) in {time.time() - T0:.1f}s")
