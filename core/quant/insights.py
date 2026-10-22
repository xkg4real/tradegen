"""AI-generated analysis of quant results.

Two layers, always in this order:

  1. **Local narrative** — a deterministic written read of the numbers,
     produced by this module with no network. It exists so every analysis
     screen carries an interpretation even with zero keys configured, and so
     the tests can assert on its content.
  2. **Claude deep analysis** — when `ANTHROPIC_API_KEY` is set, the same
     structured payload is sent to the Claude API for a genuinely generative
     read: cross-metric tensions, scenario framing, what to watch next. The
     result is labeled with the model that wrote it.

The narrative never invents numbers: everything it states is computed upstream
and formatted here. The Claude prompt likewise receives only the computed
payload, and the response is displayed as analysis, not executed as anything.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass

try:
    import requests as _requests
except Exception:                                    # pragma: no cover
    _requests = None

import config
from core.quant.backtest import BacktestResult
from core.quant.garch import LR_5PCT, NU_NORMAL
from core.quant.montecarlo import MCResult
from core.quant.optimize import OptimizedPortfolio
from core.quant.risk import RiskReport
from core.quant.signals import SignalReport

_API_URL = "https://api.anthropic.com/v1/messages"
_API_VERSION = "2023-06-01"


@dataclass(frozen=True)
class Analysis:
    text: str
    engine: str                       # "local" or the Claude model id
    error: str = ""                   # non-empty when the AI call failed


def ai_ready() -> bool:
    return bool(config.anthropic_key()) and _requests is not None


# --------------------------------------------------------------------------- #
# Local deterministic narratives
# --------------------------------------------------------------------------- #
def _pct(x: float) -> str:
    return f"{x * 100:+.1f}%"


def _narrate_garch(mc: MCResult) -> str:
    """The GARCH calibration sentence: levels, dynamics, tails, and every
    guardrail flag spelled out — the operator cannot judge a silent failure."""
    g = mc.garch
    v = lambda x: f"{x * 100:.1f}%"
    uncond = (f"an unconditional {v(g.uncond_vol)}" if math.isfinite(g.uncond_vol)
              else "an undefined unconditional level")
    half = (f"halves in {g.half_life:.0f} sessions" if math.isfinite(g.half_life)
            else "never decays (integrated variance)")
    out = [
        f"Calibration (GARCH(1,1)-{g.dist} on {g.n_obs} sessions): conditional "
        f"vol today {v(g.cond_vol_last)} against {uncond} "
        f"and a {mc.horizon_days}-session horizon vol of {v(mc.garch_horizon_vol)}.",
        f"alpha {g.alpha:.3f}, beta {g.beta:.3f}, persistence {g.persistence:.3f} "
        f"— a variance shock {half}.",
    ]
    if g.dist == "t":
        tail = ("innovation tails heavier than normal" if g.lr_t_vs_normal > LR_5PCT
                else "the t tail did not beat a normal GARCH on this sample")
        if "alpha" in g.at_bound:
            tail += "; alpha sits at its bound, so the LR reference distribution is only indicative"
        nu_txt = ("normal innovations (eta = 0)" if math.isinf(g.nu)
                  else f"nu = {g.nu:.0f}, effectively normal" if g.effectively_normal
                  else f"nu = {g.nu:.1f}")
        out.append(f"{nu_txt}: {tail} (LR {g.lr_t_vs_normal:.1f} vs {LR_5PCT}).")
    else:
        out.append("Normal innovations (no tail parameter).")
    # Precision (B2): the intervals, or why there are none. Never a bare number.
    if g.se:
        iv = lambda n, d=3: "{:.{d}f} to {:.{d}f}".format(*g.interval(n), d=d)
        lo, hi = g.half_life_interval
        prec = (f"95% intervals: alpha {iv('alpha')}, beta {iv('beta')}, persistence "
                f"{iv('persistence', 4)} (half-life {lo:.0f} to "        # 4 dp like the tile: 0.9997 is not 1.000
                + ("inf" if math.isinf(hi) else f"{hi:.0f}") + " sessions)")
    else:
        prec = f"Standard errors undefined: {g.se_note}"
    if g.nu_interval is not None:
        fmt = lambda x: ("normal" if math.isinf(x) else f">{NU_NORMAL:.0f}" if x > NU_NORMAL else f"{x:.1f}")
        prec += (f"; nu {fmt(g.nu_interval[0])} to {fmt(g.nu_interval[1])} by profile likelihood"
                 + ("; indicative only with alpha at its bound" if "alpha" in g.at_bound else ""))
    at_bound_iv = [n for n in g.interval_at_bound if n != "persistence"]
    if at_bound_iv:
        prec += ("; the interval reaches a bound for " + ", ".join(at_bound_iv)
                 + ", so it is indicative only")
    if "persistence" in g.interval_at_bound:
        prec += "; the persistence interval reaches 1, so an integrated variance is not excluded"
    out.append(prec + ". The unconditional vol carries no interval by design.")
    d = g.delta_aic_vs_gbm
    out.append(f"dAIC vs GBM {d:+.1f} — "
               + ("GARCH is preferred." if d > 0 else "GBM is not beaten here."))
    flags = []
    if not g.converged:
        flags.append("the solver did not converge; treat the calibration as indicative")
    ab = set(g.at_bound)
    if "stationarity" in ab or "beta" in ab:
        flags.append("near-integrated: the sample cannot pin down where vol "
                     "settles; use a longer history")
    if "nu" in ab:
        flags.append("tails heavier than the model allows")
    if "omega" in ab:
        flags.append("unconditional vol undefined")
    if "alpha" in ab:
        flags.append("alpha at 0: no reaction to shocks, so beta and the half-life are not identified"
                     if g.alpha < 1e-3 else "alpha at its cap: shock response is capped by the guardrail")
    if flags:
        out.append("Guardrails: " + "; ".join(flags) + ".")
    return " ".join(out)


def _narrate_drift(mc: MCResult) -> str:
    """The drift the cone is centred on, with its arithmetic, so the operator
    can see that the median is an assumption and not a forecast."""
    note = getattr(mc, "drift_note", "") or f"{mc.mu_annual * 100:+.1f}% a year"
    lead = {"premium": "Drift (risk-premium view)", "zero": "Drift",
            "rf": "Drift (risk-neutral)", "sample": "Drift (sample mean)"
            }.get(getattr(mc, "drift_mode", ""), "Drift")
    return f"{lead}: {note}."


def narrate_monte_carlo(mc: MCResult) -> str:
    lines = [
        f"Across {mc.n_paths:,} simulated {mc.model.upper()} paths over "
        f"{mc.horizon_days} sessions, {mc.symbol} ends at a median of "
        f"{mc.median_terminal:,.2f} against a spot of {mc.spot:,.2f} "
        f"({_pct(mc.median_terminal / mc.spot - 1)}).",
        f"The middle 90% of outcomes spans {mc.p05:,.2f} to {mc.p95:,.2f}; "
        f"the simulation assigns a {mc.prob_loss * 100:.0f}% probability of "
        f"finishing below spot.",
        f"Horizon VaR({mc.var_level * 100:.0f}) is {mc.var_pct * 100:.1f}% of "
        f"position value, and the expected loss beyond that point (CVaR) is "
        f"{mc.cvar_pct * 100:.1f}%.",
    ]
    lines.append(_narrate_garch(mc) if mc.garch is not None else
                 f"Calibration: annualized volatility {mc.sigma_annual * 100:.1f}%.")
    if getattr(mc, "bound_note", ""):
        lines.append(mc.bound_note)
    lines.append(_narrate_drift(mc))
    if mc.prob_target is not None and mc.target:
        lines.append(f"Probability of reaching the {mc.target:,.2f} target: "
                     f"{mc.prob_target * 100:.0f}%.")
    if mc.jump_note:
        lines.append(mc.jump_note)
    spread = (mc.p95 - mc.p05) / mc.spot
    if spread > 0.8:
        lines.append("The outcome cone is wide relative to spot — position "
                     "sizing matters more than direction here.")
    elif spread < 0.25:
        lines.append("The outcome cone is narrow — the calibrated volatility "
                     "is low, so tail surprises would come from regime change, "
                     "not from this distribution.")
    return " ".join(lines)


def narrate_risk(r: RiskReport) -> str:
    dd = f"{r.max_drawdown * 100:.1f}%"
    lines = [
        f"Over {r.sessions} sessions {r.symbol} returned {_pct(r.ann_return)} "
        f"annualized at {r.ann_vol * 100:.1f}% volatility — Sharpe "
        f"{r.sharpe:.2f}, Sortino {r.sortino:.2f}.",
        f"The worst peak-to-trough drawdown was {dd}; one-day "
        f"VaR({r.var_level * 100:.0f}) is {r.var_1d * 100:.1f}% with a tail "
        f"average (CVaR) of {r.cvar_1d * 100:.1f}%.",
    ]
    if r.kurtosis > 2:
        lines.append(f"Excess kurtosis of {r.kurtosis:.1f} means fat tails: "
                     "normal-distribution risk numbers will understate the extremes.")
    if r.skew < -0.5:
        lines.append("Returns are left-skewed — the big days are the down days.")
    elif r.skew > 0.5:
        lines.append("Returns are right-skewed — the outliers have been to the upside.")
    if r.sharpe > 1:
        lines.append("Risk-adjusted performance over this window has been strong.")
    elif r.sharpe < 0:
        lines.append("The series has not paid for its risk over this window.")
    return " ".join(lines)


def narrate_signals(s: SignalReport) -> str:
    agree = [c for c in s.components if c.score * s.composite > 0]
    dissent = [c for c in s.components if c.score * s.composite < 0 and abs(c.score) > 20]
    lines = [f"The composite technical read on {s.symbol} is {s.composite:+.0f} "
             f"— {s.stance}."]
    if agree:
        strongest = max(agree, key=lambda c: abs(c.score))
        lines.append(f"The strongest supporting component is {strongest.label.lower()} "
                     f"({strongest.score:+.0f}): {strongest.reason}")
    if dissent:
        d = max(dissent, key=lambda c: abs(c.score))
        lines.append(f"Dissenting: {d.label.lower()} ({d.score:+.0f}) — {d.reason}")
    else:
        lines.append("No component materially dissents from the composite.")
    return " ".join(lines)


def narrate_backtest(b: BacktestResult) -> str:
    verdict = ("beat" if b.beat_benchmark else "lost to")
    lines = [
        f"The {b.strategy} strategy on {b.symbol} returned "
        f"{_pct(b.total_return)} over {b.sessions} sessions and {verdict} "
        f"buy-and-hold ({_pct(b.bench_return)}).",
        f"It was in the market {b.exposure * 100:.0f}% of the time, traded "
        f"{b.n_trades} times at {b.cost_bps:.0f} bps per side, with a maximum "
        f"drawdown of {b.max_drawdown * 100:.1f}% against the benchmark's "
        f"{b.bench_max_drawdown * 100:.1f}%.",
    ]
    if b.win_rate is not None:
        lines.append(f"Closed-trade win rate: {b.win_rate * 100:.0f}%.")
    if not b.beat_benchmark and b.max_drawdown > b.bench_max_drawdown:
        lines.append("It underperformed with *shallower* drawdowns — the "
                     "strategy is buying protection with return. Whether that "
                     "trade is worth it depends on your tolerance, not the backtest.")
    elif not b.beat_benchmark:
        lines.append("It underperformed without reducing drawdown — this "
                     "configuration earns nothing for its complexity.")
    lines.append("One backtest window is one sample; treat the number as a "
                 "description of the past, not a forecast.")
    return " ".join(lines)


def narrate_portfolio(p: OptimizedPortfolio) -> str:
    top = sorted(zip(p.symbols, p.weights), key=lambda x: -x[1])[:3]
    top_txt = ", ".join(f"{s} {w * 100:.0f}%" for s, w in top)
    lines = [
        f"The {p.objective.replace('_', '-')} portfolio allocates most weight "
        f"to {top_txt}, for an expected {_pct(p.ann_return)} annualized at "
        f"{p.ann_vol * 100:.1f}% volatility (Sharpe {p.sharpe:.2f}).",
    ]
    if p.risk_contrib is not None:
        rc_top = sorted(zip(p.symbols, p.risk_contrib), key=lambda x: -x[1])[0]
        lines.append(f"{rc_top[0]} contributes {rc_top[1] * 100:.0f}% of total "
                     "portfolio risk — weight and risk are not the same thing.")
    if not p.converged:
        lines.append("The solver did not converge; treat these weights as approximate.")
    if p.note:
        lines.append(p.note)
    lines.append("Expected returns are estimated from the sample window and are "
                 "the least stable input here; the volatility structure is more "
                 "trustworthy than the return forecast.")
    return " ".join(lines)


# --------------------------------------------------------------------------- #
# Claude deep analysis
# --------------------------------------------------------------------------- #
_SYSTEM = (
    "You are the analysis engine inside QUANTGEN, a personal quantitative "
    "trading application covering equities and FICC: rates, government and "
    "corporate bonds, interest-rate swaps and swaptions, FX spot, forwards and "
    "options, structured notes, and the macro regime. You receive computed "
    "results (Monte Carlo simulations, risk metrics, optimizer output, "
    "technical signals, backtests, yield-curve descriptors, DV01/key-rate "
    "risk, option Greeks, carry tables, macro z-scores) as JSON. Write a "
    "sharp, concrete interpretation for the operator, in the voice of a "
    "sell-side rates/FX strategist writing for a trading desk: what the "
    "numbers jointly imply, where they disagree, what regime or assumption "
    "they are most sensitive to, what the trade expression would be, and "
    "what would invalidate the read. Use only the numbers provided — never "
    "invent data; quote rates in percent and changes in basis points. 3–6 "
    "short paragraphs, no headers, no bullet lists, no disclaimers about "
    "being an AI; the operator knows financial risk is theirs. If the "
    "operator's question asks for a report format, follow that format."
)


def _payload_to_json(payload: dict) -> str:
    def default(o):
        try:
            import numpy as np
            if isinstance(o, np.ndarray):
                return o.tolist()[:50]
            if isinstance(o, (np.floating, np.integer)):
                return float(o)
        except Exception:
            pass
        return str(o)
    return json.dumps(payload, default=default)


def deep_analysis(kind: str, payload: dict, *, question: str = "") -> Analysis:
    """Send a structured result to Claude. Returns Analysis with error set (and
    empty text) when unconfigured or the call fails — the caller already has
    the local narrative, so failure here degrades, never blocks."""
    key = config.anthropic_key()
    if not key:
        return Analysis("", "none", error="ANTHROPIC_API_KEY is not configured.")
    if _requests is None:
        return Analysis("", "none", error="The requests package is not installed.")
    model = config.ai_model()
    user_msg = (f"Analysis type: {kind}\n\nComputed results:\n"
                f"{_payload_to_json(payload)}")
    if question.strip():
        user_msg += f"\n\nThe operator specifically asks: {question.strip()}"
    try:
        resp = _requests.post(
            _API_URL,
            headers={"x-api-key": key, "anthropic-version": _API_VERSION,
                     "content-type": "application/json"},
            json={"model": model, "max_tokens": 1500, "system": _SYSTEM,
                  "messages": [{"role": "user", "content": user_msg}]},
            timeout=60,
        )
    except Exception as exc:
        return Analysis("", model, error=f"Claude API request failed: {exc}")
    if resp.status_code == 401:
        return Analysis("", model, error="Claude API rejected the key (HTTP 401).")
    if resp.status_code != 200:
        detail = ""
        try:
            detail = resp.json().get("error", {}).get("message", "")[:200]
        except Exception:
            pass
        return Analysis("", model, error=f"Claude API answered HTTP {resp.status_code}. {detail}".strip())
    try:
        blocks = resp.json().get("content", [])
        text = "\n\n".join(b.get("text", "") for b in blocks
                           if b.get("type") == "text").strip()
    except Exception:
        return Analysis("", model, error="Claude API returned an unreadable body.")
    if not text:
        return Analysis("", model, error="Claude API returned no text.")
    return Analysis(text, model)
