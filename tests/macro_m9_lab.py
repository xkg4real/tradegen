"""Sprint 6 package C: Quant Lab (M9, R-16; core/quant/lab.py, docs/quant_lab_grading.py) and the deferred R-17
hooks (M10; the CRYPTO clock branch of core/calendars/clocks.py, the FX instrument predicate of
core/quant/instruments.py). I-11 mechanics on synthetic series, I-11 threshold / replay clauses NOT_RUN naming the
KOSPI fixture, T-REPRO-01c, T-CRYPTO-01, T-FX-01, and the labelled SMOKE grading on local vendor closes.
Hermetic: inline synthetic series with fixed dates (never `synthetic_history`), tempfile outputs only, no network,
nothing under ~/.nextgen; the shipped store is read, never written (T-HERM-02)."""
from __future__ import annotations

import ast
import hashlib
import json
import math
import tempfile
from dataclasses import fields
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import numpy as np

from core.calendars import clocks as K
from core.ficc.macro_schema import canonical_json
from core.quant import lab
from core.quant import montecarlo as MC
from core.quant import vol_estimators as E
from core.quant.gjr import simulate_gjr_series
from core.quant.history import History
from core.quant.instruments import (FX_BOOKS, INSTRUMENT_BOOKS, CostLowered, check_cost_policy, cost_per_side,
                                    fx_instrument_check, header_checks)
from tests.notrun import NotRun, require_fixture

ROOT = Path(__file__).resolve().parents[1]
STORE_PATH = ROOT / "data" / "macro" / "rules_v2.0.0.json"
KOSPI_FIXTURE = "krx_kospi_official_close_1997-01-03_2026-10-02.csv"       # F01; F13 = yahoo_KS11_1996-12_2026-10-02.csv
GJR = (2e-6, 0.03, 0.10, 0.90, 6.0)                                        # omega, alpha, gamma, beta, nu
UTC = timezone.utc


def U(*a):
    return datetime(*a, tzinfo=UTC)


def _raises(fn, exc=Exception, needle=""):
    try:
        fn()
    except exc as e:
        assert needle.lower() in str(e).lower(), f"{needle!r} not in {e}"
        return e
    raise AssertionError(f"expected {exc.__name__}")


def weekdays(end: str, n: int) -> list[str]:
    out, d = [], date.fromisoformat(end)
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d.isoformat())
        d -= timedelta(days=1)
    return out[::-1]


def gjr_sim(n: int, seed: int, params=GJR):
    """(r, sigma_next) of a GJR-t DGP: sigma_next[t] is the true 1-day sigma of r[t+1] known at close t."""
    omega, alpha, gamma, beta, nu = params
    rng = np.random.default_rng(seed)
    z = rng.standard_t(nu, size=n) * math.sqrt((nu - 2) / nu)
    r, sig = np.empty(n), np.empty(n)
    s2, e = omega / (1 - alpha - beta - gamma / 2), 0.0
    for t in range(n):
        s2 = omega + (alpha + gamma * (e < 0)) * e * e + beta * s2
        e = math.sqrt(s2) * z[t]
        r[t] = e
        sig[t] = math.sqrt(omega + (alpha + gamma * (e < 0)) * e * e + beta * s2)
    return r, sig


def true_var_h(sig1, h: int, params=GJR):
    omega, alpha, gamma, beta, _ = params
    p = alpha + beta + gamma / 2
    s2bar = omega / (1 - p)
    return h * s2bar + (sig1 ** 2 - s2bar) * (1 - p ** h) / (1 - p)


def fhs_fan(r, var_h, h: int, *, min_pool: int = 252) -> np.ndarray:
    """A correctly specified fan for the gate mechanics: (T, 9) deciles of R_{t->t+h} = sqrt(var_h[t]) x the
    expanding pool of realised z_h(s) = R_{s->s+h} / sqrt(var_h[s]) (each entering once realised at s + h)."""
    from core.quant.forecast_eval import _Pool
    T = r.size
    sig = np.sqrt(var_h)
    cum = np.concatenate([[0.0], np.cumsum(r)])
    R = np.full(T, np.nan)
    R[:T - h] = cum[h + 1:T + 1] - cum[1:T - h + 1]
    Q, pool = np.full((T, 9), np.nan), _Pool()
    for t in range(T):
        if t >= h:
            pool.add(R[t - h] / sig[t - h])
        if len(pool) >= min_pool:
            Q[t] = [sig[t] * pool.quantile(l) for l in lab.DECILES]
    return Q


def _true_lines(n=5000, seed=1):
    r, sig = gjr_sim(n, seed)
    dates = weekdays("2026-10-02", n)
    line = lab.fhs_tail(r, sig, model="true_fhs")
    fans = {h: lab.fan_pit(r, fhs_fan(r, true_var_h(sig, h), h), h) for h in (21, 126)}
    z = r[1:] / sig[:-1]
    return r, sig, dates, line, fans, z


PERIODS_ALL = {"2016-26": (None, None), "2026": ("2026-01-01", None)}


def _store_get_factory():
    from core.rules.macro_rules import load_store
    store = load_store()

    def get(key):
        try:
            return store.get(key)
        except KeyError:
            return None
    return store, get


def _fx_header(**over) -> dict:
    h = {"rule_id": "R-17", "instrument_book": "FX_broker_spot", "rebalance": "daily", "no_trade_band": 0.0,
         "notional_nav": {"ref": "sleeves.FX.notional_nav"}, "fill_model": "broker_spot",
         "costs": {"per_side": "read_from_gate", "floor": "tick_floor", "stress": 2.0, "stress_line": "printed"},
         "printed_lines": ["exec_variants_ABC"], "nav_fx": {"series": "USDKRW_1530_SNAPSHOT", "role": "forward_sim"}}
    h.update(over)
    return h


# --------------------------------------------------------------------------- #
# I-11: fit clause (expanding >= 10-year windows)
# --------------------------------------------------------------------------- #
def test_i11_fit_clause_expanding_windows():
    """`lab_fit` fits on every return through the last date; < 10 calendar years -> insufficient_history (never
    presented as calibrated); the grading driver's forecast at origin t reads r[:t+1] only (prefix property of the
    expanding M3 driver); the lab config is expanding, and no 504-close window exists in the lab module."""
    r = simulate_gjr_series(*GJR, n=2800, seed=4)
    dates = weekdays("2026-10-02", 2800)                     # ~11.1 calendar years
    f = lab.lab_fit(r, dates, model="gjr_t")
    assert f.status == "ok" and f.n_obs == r.size == 2800 and f.fit.n_obs == 2800 and f.acts is False, f
    assert f.first_date == dates[0] and f.last_date == dates[-1]
    short = lab.lab_fit(r[-2000:], dates[-2000:], model="gjr_t")
    assert short.status == "insufficient_history" and short.fit is None and "10 years" in short.reason, short
    assert lab.has_min_history(dates, 2799) and not lab.has_min_history(dates[-2000:], 1999)
    _raises(lambda: lab.lab_fit(r, dates, model="ewma"), ValueError, "garch_t")
    g = lab.lab_fit(r, dates, model="garch_t")
    assert g.status == "ok" and g.fit.n_obs == 2800
    # prefix property: appending later data leaves earlier forecasts unchanged (origin t reads r[:t+1] only)
    short_r = simulate_gjr_series(*GJR, n=700, seed=5)
    full = E.gjr_t(short_r, 1, min_years=1, refit_every=42)
    part = E.gjr_t(short_r[:600], 1, min_years=1, refit_every=42)
    ok = part.ok
    assert ok.sum() > 100 and np.array_equal(full.ok[:600], ok)
    assert np.array_equal(full.var[:600][ok], part.var[ok])
    sig_full, sig_part = lab.gjr_sigma(short_r, 1, min_years=1, refit_every=42), lab.gjr_sigma(short_r[:600], 1, min_years=1, refit_every=42)
    assert np.allclose(sig_full[:600][ok], sig_part[ok], rtol=0, atol=0)
    assert lab.LAB_CONFIG["fit"] == {"window": "expanding", "min_years": 10, "refit_every_origins": 21}
    src = (ROOT / "core" / "quant" / "lab.py").read_text(encoding="utf-8")
    assert "504" not in src.replace("504-close window", "").replace("trailing 504", ""), "no 504-close window in the lab"
    assert lab.MIN_YEARS == E.MIN_YEARS == 10 and lab.REFIT_EVERY == E.REFIT_EVERY == 21


test_i11_fit_clause_expanding_windows.test_ids = ["I-11"]


# --------------------------------------------------------------------------- #
# I-11: tails, the envelope, the two periods, the withheld envelope
# --------------------------------------------------------------------------- #
def test_i11_tails_envelope_lines_and_periods():
    """fast FHS and GJR-EVT lines; envelope == elementwise max in loss units with ok = a.ok & b.ok; the report has
    exactly the two periods "2016-26" and "2026" with different n, Kupiec / Christoffersen keys at 95 % and 99 %, the
    ES Z2 line with z2 and p; a GPD fit with xi >= 1 fails closed and `envelope` carries the reason."""
    r, sig = gjr_sim(3000, 2)
    dates = weekdays("2026-10-02", 3000)
    r_simple = np.expm1(r)
    fast = lab.fhs_tail(r, lab.sma20_sigma(r_simple), model="fast_fhs")
    evt = lab.evt_tail(r, sig, refit_every=21)
    assert fast.status == "ok" and evt.status == "ok" and evt.fit.ok and 0 <= evt.fit.xi < 1 and evt.fit.k >= 50, (evt.status, evt.fit)
    assert fast.acts is False and evt.acts is False
    env = lab.envelope(fast, evt)
    both = fast.ok & evt.ok
    assert env.model == "envelope" and np.array_equal(env.ok, both) and both.sum() > 1500
    for name in ("var95", "var99", "var975", "es975"):
        a, b, e = getattr(fast, name), getattr(evt, name), getattr(env, name)
        assert np.array_equal(e[both], np.maximum(a[both], b[both])), name
        assert np.all(np.isnan(e[~both])) and np.all(e[both] > 0)
    assert np.all(env.var99[both] >= env.var975[both]) and np.all(env.var975[both] >= env.var95[both])
    assert np.all(env.es975[both] >= env.var975[both])            # ES beyond its VaR
    rep = lab.grade_line(r, dates, env, periods=PERIODS_ALL, fans={}, z_pool=r[1:] / sig[:-1], gpd=evt.fit)
    assert list(rep["periods"]) == ["2016-26", "2026"] and rep["periods"]["2016-26"]["n"] != rep["periods"]["2026"]["n"]
    for P in rep["periods"].values():
        for lvl in ("var95", "var99"):
            assert {"rate", "kupiec_p", "ind_p", "cc_p", "tick_loss"} <= set(P[lvl]), P[lvl]
        assert {"z2", "p", "rejected_5pct", "law"} <= set(P["es975"]) and "GPD" in P["es975"]["law"]
        assert P["basel"]["last_250"] in ("green", "yellow", "red", None)
    assert rep["model"] == "envelope" and rep["acts"] is False
    # injected EVT failure (xi = 1.2): the line is all-failed, the envelope has no ok origin and names the reason
    bad = lambda z: lab.GpdFit(1.2, 0.5, 2.0, 100, 1000, False, "xi=1.200 >= 1: infinite tail mean (injected)")   # noqa: E731
    evt_bad = lab.evt_tail(r, sig, gpd_fitter=bad)
    assert evt_bad.status == "evt_fit_failed" and not evt_bad.ok.any() and "xi=1.2" in evt_bad.reason
    env_bad = lab.envelope(fast, evt_bad)
    assert env_bad.status == "evt_fit_failed" and not env_bad.ok.any() and "xi=1.2" in env_bad.reason
    real = lab.gpd_tail(r[1:] / sig[:-1])
    assert real.ok and real.n == 2999 and real.k == 299 and abs(lab.gpd_quantile(real, 0.99)) > lab.gpd_quantile(real, 0.95) > real.u
    assert not lab.gpd_tail(np.r_[r[1:400] / sig[:399]]).ok                              # k = 39 < 50 fails closed
    assert lab.PATH_COLOUR_LABEL == "path-vol quartile" and lab.LAB_CONFIG["path_colour_label"] == "path-vol quartile"


test_i11_tails_envelope_lines_and_periods.test_ids = ["I-11"]


def test_i11_grade_lab_end_to_end_synthetic():
    """`grade_lab` on a synthetic GJR-t series with the real expanding GJR fits: model envelope with both components,
    the two periods, h126 and the 2026 lines reported not gated, repro record, no R-06 label word on a lab line; an
    injected EVT failure withholds the envelope and grades fast FHS alone with the reason. Verdict asserted as a
    class member only (never that a synthetic series PASSes)."""
    n = 3300
    r = simulate_gjr_series(*GJR, n=n, seed=4)
    closes = 100.0 * np.exp(np.cumsum(np.r_[0.0, r]))
    dates = weekdays("2026-10-02", n + 1)
    gaps = np.zeros(n + 1)
    gaps[-200::7] = 2                                             # some post-holiday sessions for the bucket table
    labels = np.array(["normal"] * (n + 1), dtype=object)
    labels[-300:] = "elevated"
    ctx = lab.LabContext(refit_every=252, gap_sessions=gaps, labels=labels, knowledge_utc="2026-10-02T07:00:00Z",
                         config_hash="cfg-synthetic", package_version="test")
    g = lab.grade_lab("KR", (dates, closes), ctx)
    assert g.model == "envelope" and g.components == ("fast_fhs", "gjr_evt") and g.acts is False and g.note == ""
    assert g.verdict in ("PASS", "FAIL", "NOT_RUN") and g.verdict == g.gate["status"] == g.report["gate"]["status"]
    assert set(g.report["periods"]) == {"2016-26", "2026"} and g.y2026_reported["n"] < g.report["periods"]["2016-26"]["n"]
    assert g.fan_pit_h21["h"] == 21 and g.h126_reported["h"] == 126 and g.fan_pit_h21["overlap"] is False
    assert g.gate["reported_not_gated"] == ["fan_pit_h126", "period_2026"]
    assert set(g.report["components_lines"]) == {"fast_fhs", "gjr_evt"} and "2016-26" in g.report["components_lines"]["gjr_evt"]
    assert g.repro == {"seed": 11, "config_hash": "cfg-synthetic", "data_snapshot_id": lab.data_snapshot_md5(dates, closes),
                       "package_version": "test", "git_hash": "UNVERSIONED", "knowledge_utc": "2026-10-02T07:00:00Z"}
    assert g.post_holiday["n_us_2"]["n"] > 0 and g.post_holiday["n_us_2"]["var95_rate_scaled"] <= g.post_holiday["n_us_2"]["var95_rate_unscaled"]
    assert set(g.per_label) == set(lab.R06_LABELS) and g.per_label["elevated"]["n"] > 0 and g.per_label["calm"]["n"] == 0
    text = "\n".join(l for l in g.lines)
    assert "reported, not gated" in text and "gated" in text and "path-vol" not in text
    assert not any(w in text.lower() for w in lab.R06_LABELS), "R-06 label words never caption a lab line"
    js = lab.grade_to_json(g)
    json.dumps(js)                                                 # plain JSON
    assert js["config"]["source"].startswith("core.quant.lab.LAB_CONFIG") and js["acts"] is False
    bad = lambda z: lab.GpdFit(1.2, 0.5, 2.0, 100, 1000, False, "xi=1.200 >= 1 (injected)")      # noqa: E731
    g2 = lab.grade_lab("KR", (dates, closes), lab.LabContext(refit_every=252, gpd_fitter=bad))
    assert g2.model == "fast_fhs" and g2.components == ("fast_fhs",) and "withheld" in g2.note and "xi=1.2" in g2.note
    assert g2.report["components_lines"]["gjr_evt"]["status"] == "evt_fit_failed" and "withheld" in g2.lines[0]
    assert g2.verdict == "NOT_RUN" and "withheld" in g2.gate["reason"]          # no verdict without the envelope
    assert g2.var_1d["displayable"] is False and g2.var_1d["var99"] is None and g2.var_1d["b5"]["gjr_evt"] == "NOT_RUN"
    # the 1-day VaR is shown only when every component passes 1-day B5 (L1747 (2)); numbers withheld otherwise
    v = g.var_1d
    assert v["origin"] == dates[-1] and set(v["b5"]) == {"fast_fhs", "gjr_evt"} and v["scale"] == 1.0
    assert v["displayable"] == all(s == "PASS" for s in v["b5"].values())
    assert (v["var99"] is not None) == v["displayable"] and any(l.startswith("1-day VaR (envelope)") for l in g.lines)
    assert g.fan_pit_h21["model"] == "garch_t" and g.fan_pit_h21["drift"] == "premium" and g.fan_pit_h21["n_origins"] >= 20


test_i11_grade_lab_end_to_end_synthetic.test_ids = ["I-11"]


# --------------------------------------------------------------------------- #
# I-11: the M9 gate (mechanics on synthetic series; thresholds on the fixture NOT_RUN)
# --------------------------------------------------------------------------- #
def test_i11_gate_mechanics_true_dgp_passes_misspecified_fails():
    """A correctly specified line (the true GJR-t sigma, FHS tails, the true h-day fan) passes the four gates; the same
    line with the out-of-sample sigma x 0.6 fails Kupiec / CC at 99 % and the Z2 line (simulated under the line's own
    predictive law, H0); m9_gate at the threshold edges
    (0.0499 vs 0.05, 0.0099 vs 0.01, n = 199) and its blindness to h126 / 2026."""
    r, sig, dates, line, fans, z = _true_lines()
    rep = lab.grade_line(r, dates, line, periods=PERIODS_ALL, fans=fans, z_pool=z)
    g = rep["gate"]
    assert g["status"] == "PASS", g
    L = rep["periods"]["2016-26"]
    assert L["n"] >= 4000 and 0.005 <= L["var99"]["rate"] <= 0.015 and L["var99"]["kupiec_p"] >= 0.05 and L["var99"]["cc_p"] >= 0.05
    assert L["es975"]["p"] >= 0.05 and L["es975"]["rejected_5pct"] is False and L["es975"]["B"] == 2000 and L["es975"]["seed"] == 11
    assert fans[21]["chi2_p"] >= 0.01 and fans[21]["n_origins"] >= 200 and sum(fans[21]["counts"]) == fans[21]["n_origins"]
    assert fans[126]["n_origins"] < fans[21]["n_origins"] and "h126" not in str(g["lines"])
    assert L["basel"]["last_250"] == "green" and L["basel"]["windows"]["red"] == 0
    assert set(g["lines"]) == {"var99_kupiec_p", "var99_cc_p", "es975_z2_p", "fan_pit_h21_chi2_p"}
    bad = lab.fhs_tail(r, sig * 0.6, model="misspecified", pool_sigma=sig)
    rep2 = lab.grade_line(r, dates, bad, periods=PERIODS_ALL, fans=fans, z_pool=z)
    L2 = rep2["periods"]["2016-26"]
    assert rep2["gate"]["status"] == "FAIL" and L2["var99"]["rate"] > 0.03 and L2["var99"]["kupiec_p"] < 0.05 and L2["var99"]["cc_p"] < 0.05, L2["var99"]
    assert L2["es975"]["p"] < 0.05 and L2["es975"]["rejected_5pct"] is True, L2["es975"]
    assert L2["basel"]["last_250"] == "red"
    # threshold edges: a line at its threshold passes, one below fails, n < 200 or a missing line is NOT_RUN
    def report(k=0.5, cc=0.5, es=0.5, fan=0.5, n=1000, nfan=100):
        return {"periods": {"2016-26": {"n": n, "var99": {"kupiec_p": k, "cc_p": cc}, "es975": {"p": es}},
                            "2026": {"n": 50, "var99": {"kupiec_p": 0.0, "cc_p": 0.0}, "es975": {"p": 0.0}}},
                "fan_pit": {"h21": {"chi2_p": fan, "n_origins": nfan}, "h126": {"chi2_p": 0.0, "n_origins": 10}}}
    assert lab.m9_gate(report())["status"] == "PASS"
    assert lab.m9_gate(report(k=0.05))["status"] == "PASS" and lab.m9_gate(report(k=0.0499))["status"] == "FAIL"
    assert lab.m9_gate(report(cc=0.05))["status"] == "PASS" and lab.m9_gate(report(cc=0.0499))["status"] == "FAIL"
    assert lab.m9_gate(report(es=0.05))["status"] == "PASS" and lab.m9_gate(report(es=0.0499))["status"] == "FAIL"
    assert lab.m9_gate(report(fan=0.01))["status"] == "PASS" and lab.m9_gate(report(fan=0.0099))["status"] == "FAIL"
    assert lab.m9_gate(report(n=199))["status"] == "NOT_RUN" and lab.m9_gate(report(n=200))["status"] == "PASS"
    assert lab.m9_gate(report(k=float("nan")))["status"] == "NOT_RUN" and lab.m9_gate(report(nfan=19))["status"] == "NOT_RUN"
    assert lab.m9_gate({"periods": {}, "fan_pit": {}})["status"] == "NOT_RUN"
    assert lab.m9_gate(report())["reported_not_gated"] == ["fan_pit_h126", "period_2026"]
    assert lab.basel_zone(4, 250) == "green" and lab.basel_zone(5, 250) == "yellow" and lab.basel_zone(10, 250) == "red"
    assert lab.basel_zone(2, 125) == "green" and lab.basel_zone(3, 125) == "yellow" and lab.basel_zone(0, 0) == "NOT_RUN"


test_i11_gate_mechanics_true_dgp_passes_misspecified_fails.test_ids = ["I-11"]


def test_i11_fan_pit_grades_the_lab_garch_t_fan():
    """The gated fan is the lab's own: at each origin the deciles equal those of montecarlo.run_monte_carlo(garch_t,
    drift premium rf 3 % + ERP 4 %, same seed and paths) on the closes through that origin (expanding fit; later data
    never changes an earlier fan); origins are non-overlapping, inside the period, >= 10 years of history; seeded."""
    n = 2900
    closes = 100.0 * np.exp(np.cumsum(np.r_[0.0, simulate_gjr_series(*GJR, n=n, seed=6)]))
    r = np.diff(np.log(closes))                                   # grade_lab's and History.log_returns' form
    dates = weekdays("2026-10-02", n + 1)
    rdates = dates[1:]
    org = lab.fan_origins(rdates, 21, start="2016-01-01")
    assert org and all(b - a >= 21 for a, b in zip(org, org[1:])) and org[-1] + 21 < n
    assert lab.has_min_history(rdates, org[0]) and not lab.has_min_history(rdates, org[0] - 1)
    t = org[0]
    Q = lab.garch_fan_quantiles(r, 21, [t], n_paths=500, seed=11)
    assert np.isnan(Q[t - 1]).all() and np.isfinite(Q[t]).all() and np.all(np.diff(Q[t]) > 0)
    mc = MC.run_monte_carlo(History("SYN", "SYNTHETIC", tuple(dates[:t + 2]), tuple(closes[:t + 2])), model="garch_t",
                            n_paths=500, horizon_days=21, seed=11, drift="premium", rf_rate=0.03, erp=0.04)
    want = np.quantile(np.log(mc.terminal / mc.spot), lab.DECILES)
    assert np.max(np.abs(Q[t] - want)) < 1e-12, (Q[t], want)
    later = lab.garch_fan_quantiles(r[:t + 300], 21, [t], n_paths=500, seed=11)
    assert np.array_equal(later[t], Q[t])                                        # expanding: r[:t+1] only
    again = lab.garch_fan_quantiles(r, 21, [t], n_paths=500, seed=11)
    other = lab.garch_fan_quantiles(r, 21, [t], n_paths=500, seed=12)
    assert np.array_equal(again[t], Q[t]) and _rel(Q[t], other[t]) > 1e-6
    fp = lab.fan_pit(r, lab.garch_fan_quantiles(r, 21, org, n_paths=300, seed=11), 21)
    assert fp["n_origins"] == len(org) and sum(fp["counts"]) == len(org) and fp["overlap"] is False


test_i11_fan_pit_grades_the_lab_garch_t_fan.test_ids = ["I-11", "T-REPRO-01c"]


def test_i11_kospi_oos_2016_26_thresholds_refdata():
    """The M9 acceptance itself: the envelope on KOSPI closes from 2005 or earlier through 2026-10-02 (official close
    7,003.74), KR + US calendars for gap_sessions. NOT_RUN naming the fixture; never a vendor substitute."""
    require_fixture(KOSPI_FIXTURE)
    raise NotRun("REFDATA: " + KOSPI_FIXTURE + " listed but the I-11 run also needs the signed KR/US calendars (gap_sessions)")


test_i11_kospi_oos_2016_26_thresholds_refdata.test_ids = ["I-11"]


# --------------------------------------------------------------------------- #
# I-11: replay library
# --------------------------------------------------------------------------- #
def test_i11_replay_synthetic_companion():
    """A 28-close inline path from the 9,114.55 peak falling exactly 38.6 % over 27 returns with a stub regime_tags:
    n_sessions 27, index_return -0.386, regime at_start price_limit 0.30, book_return for a non-empty book, unmapped
    instruments listed at zero, acts False; letf_path_return on the local-cache numbers; the eight declared windows."""
    rp = lab.REPLAY_BY_ID["KR-2026-06-23_07-30"]
    assert rp.start == "2026-06-23" and rp.end == "2026-07-30" and rp.market == "KR" and len(lab.REPLAYS) == 8
    assert [x.replay_id for x in lab.REPLAYS][:3] == ["KR-1997-11_12", "KR-1998-03_06", "KR-2000-04-17"]
    dates = weekdays("2026-07-30", 28)
    assert dates[0] == "2026-06-23"
    del dates[18]                                                 # one in-window holiday: 27 sessions, as the spec counts
    dates = ["2026-06-22"] + dates + ["2026-07-31"]
    closes = np.r_[9114.55 * (1 - 0.386) ** (np.arange(28) / 27.0), 6000.0]
    tags = {"price_limit": 0.30, "fx_regime": None, "etf_available": True, "random_end": True}

    def regime_tags(market, d):
        assert market == "KR" and isinstance(d, date)
        return dict(tags, closing_call=(d >= date(2026, 7, 1)))
    res = lab.replay(rp, dates, closes, regime_tags=regime_tags, book={"069500": 0.6, "005930": 0.4},
                     instrument_closes={"069500": (dates, closes)}, repro={"seed": 11})
    assert res.status == "ok" and res.n_sessions == 27 and abs(res.index_return + 0.386) < 1e-9 and res.acts is False
    assert res.dates[0] == "2026-06-23" and res.dates[-1] == "2026-07-30" and res.index_path.size == 27
    assert res.regime["at_start"]["price_limit"] == 0.30 and res.regime["at_start"]["closing_call"] is False
    assert res.regime["changes"] == [("2026-07-01", "closing_call", False, True)]
    r_day = closes[1:28] / closes[:27] - 1.0
    assert abs(res.book_return - (np.prod(1.0 + 0.6 * r_day) - 1.0)) < 1e-12 and res.unmapped == ("005930",)   # 0.4 unmapped at zero
    assert -0.386 < res.book_return < 0.6 * -0.386 + 0.03
    assert abs(res.max_dd + 0.386) < 1e-9 and res.worst_day[0] in res.dates and res.repro == {"seed": 11}
    assert "current" not in json.dumps(lab._jsonable(res.regime)).lower()
    full = lab.replay(rp, dates, closes, regime_tags=regime_tags, book={"069500": 1.0}, instrument_closes={"069500": (dates, closes)})
    assert abs(full.book_return - full.index_return) < 1e-12 and full.unmapped == ()

    def raising(market, d):
        raise KeyError("kr_regime_tags unsigned")
    miss = lab.replay(rp, dates, closes, regime_tags=raising)
    assert miss.status == "missing_input" and "unsigned" in miss.reason and abs(miss.index_return + 0.386) < 1e-9
    assert lab.replay(rp, dates[1:], closes[1:]).status == "missing_input"            # no close before the window
    assert lab.replay(lab.REPLAY_BY_ID["KR-2008-10"], dates, closes).status == "missing_input"
    v = lab.letf_path_return(-0.4081, 0.08121, 2)
    assert abs(v + 0.677) < 1e-3 and abs(v + 0.684) < 0.01 and abs(lab.letf_path_return(-0.4081, 0.08121, 2, carry=0.01) - (v - 0.01 * (1 + v))) < 1e-2
    assert abs(lab.letf_path_return(0.1, 0.0, 1.0) - 0.1) < 1e-15 and abs(lab.letf_path_return(0.0, 0.0, 3.0)) < 1e-15


test_i11_replay_synthetic_companion.test_ids = ["I-11"]


def test_i11_replay_kospi_path_refdata():
    """The replay clause on the real path: ^KS11 / KRX official closes 2026-06-22 -> 2026-07-30 (peak 9,114.55,
    -38.6 % in 27 sessions), the signed KR regime-tag file and a book state. NOT_RUN naming the fixture."""
    require_fixture(KOSPI_FIXTURE)
    raise NotRun("REFDATA: " + KOSPI_FIXTURE + " listed but the replay also needs the signed kr_regime_tags file and a persisted book state")


test_i11_replay_kospi_path_refdata.test_ids = ["I-11"]


# --------------------------------------------------------------------------- #
# I-11 rule (6): no lab output is read by a sizing module
# --------------------------------------------------------------------------- #
FORBIDDEN = ("core.quant.lab", "core.quant.montecarlo", "core.ficc.ratesim")


def _sizing_modules() -> list[Path]:
    named = ["core/quant/risk.py", "core/quant/risk_layer.py", "core/quant/signals.py", "core/quant/optimize.py",
             "core/quant/vol_estimators.py", "core/quant/sleeves.py", "core/ficc/macro_artifacts.py",
             "core/skills/pipeline.py", "core/skills/macro_daily.py"]
    paths = [ROOT / p for p in named] + sorted((ROOT / "core" / "engine").glob("*.py")) + sorted((ROOT / "core" / "rules").glob("*.py"))
    return [p for p in paths if p.is_file()]


def _lab_imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    hits = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            hits += [a.name for a in node.names if a.name.startswith(FORBIDDEN)]
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            if mod.startswith(FORBIDDEN):
                hits.append(mod)
            elif mod in ("core.quant", "core.ficc"):
                hits += [f"{mod}.{a.name}" for a in node.names if f"{mod}.{a.name}" in FORBIDDEN]
    return hits


def test_i11_no_sizing_module_reads_lab():
    """Static AST scan: none of the sizing modules (risk layer, sleeves, books, pipeline, signals, optimiser,
    estimators, engine, rules, artifact builders) imports core.quant.lab, montecarlo or ratesim; a planted import in a
    temp copy trips the scan; every lab result type carries acts = False; the envelope is not a fifth fan model."""
    mods = _sizing_modules()
    assert len(mods) >= 8 and any(p.name == "books.py" for p in mods) and any(p.name == "risk_layer.py" for p in mods)
    bad = {p.relative_to(ROOT).as_posix(): _lab_imports(p) for p in mods if _lab_imports(p)}
    assert not bad, f"sizing modules importing lab outputs: {bad}"
    with tempfile.TemporaryDirectory() as tmp:
        planted = Path(tmp) / "risk_layer_copy.py"
        planted.write_text((ROOT / "core/quant/risk_layer.py").read_text(encoding="utf-8")
                           + "\nfrom core.quant.lab import grade_lab\nimport core.quant.montecarlo as mc\n", encoding="utf-8")
        assert _lab_imports(planted) == ["core.quant.lab", "core.quant.montecarlo"]
        planted.write_text("from core.ficc import ratesim\n", encoding="utf-8")
        assert _lab_imports(planted) == ["core.ficc.ratesim"]
    for cls in lab.RESULT_TYPES:
        f = {x.name: x for x in fields(cls)}["acts"]
        assert f.default is False, cls
    assert MC.MODELS == ("garch_t", "gbm", "jump", "bootstrap") and "envelope" not in MC.MODELS


test_i11_no_sizing_module_reads_lab.test_ids = ["I-11"]


# --------------------------------------------------------------------------- #
# T-REPRO-01c
# --------------------------------------------------------------------------- #
def _rel(a, b) -> float:
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    return float(np.max(np.abs(a - b) / np.maximum(np.abs(a), 1e-300))) if a.size else 0.0


def test_t_repro_01c_lab_outputs_reproducible_under_the_seed():
    """The same seed and input arrays give identical lab outputs (Z2 simulation, the grading report, the fan PIT) and
    identical Monte Carlo paths for every `montecarlo.MODELS` entry (relative difference <= 1e-12); a different seed
    changes the stochastic outputs; the repro record carries seed, config_hash, data_snapshot_id, package_version;
    no clock is read by the lab or the grading script."""
    r, sig, dates, line, fans, z = _true_lines(n=2000, seed=3)
    a = lab.grade_line(r, dates, line, periods=PERIODS_ALL, fans=fans, z_pool=z)
    b = lab.grade_line(r, dates, line, periods=PERIODS_ALL, fans=fans, z_pool=z)
    assert canonical_json(lab._jsonable(a)) == canonical_json(lab._jsonable(b))
    x, es, var = r[1:], line.es975[:-1], line.var975[:-1]
    z1 = lab.es_z2(x, es, var_forecasts=var, scale=sig[:-1], z_pool=z, seed=11)
    z2 = lab.es_z2(x, es, var_forecasts=var, scale=sig[:-1], z_pool=z, seed=11)
    z3 = lab.es_z2(x, es, var_forecasts=var, scale=sig[:-1], z_pool=z, seed=12)
    assert z1 == z2 and z1["z2"] == z3["z2"] and z1["p"] != z3["p"] and z1["seed"] == 11
    gpd = lab.gpd_tail(z)
    g1 = lab.es_z2(x, es, var_forecasts=var, scale=sig[:-1], z_pool=z, gpd=gpd, seed=11)
    assert g1 == lab.es_z2(x, es, var_forecasts=var, scale=sig[:-1], z_pool=z, gpd=gpd, seed=11) and g1["p"] != z1["p"]
    ctx = lab.LabContext(seed=11, config_hash="cfg", package_version="v", knowledge_utc="2026-10-02T07:00:00Z")
    rec = lab.repro_record(ctx, dates, r)
    assert set(rec) == {"seed", "config_hash", "data_snapshot_id", "package_version", "git_hash", "knowledge_utc"}
    assert rec["data_snapshot_id"] == lab.data_snapshot_md5(dates, r) != lab.data_snapshot_md5(dates, r * 1.0001)
    closes = tuple((100.0 * np.exp(np.cumsum(np.r_[0.0, r[:400]]))).tolist())
    h = History("SYN", "SYNTHETIC", tuple(weekdays("2026-10-02", 401)), closes)
    for model in MC.MODELS:
        m1 = MC.run_monte_carlo(h, model=model, n_paths=300, horizon_days=30, seed=7)
        m2 = MC.run_monte_carlo(h, model=model, n_paths=300, horizon_days=30, seed=7)
        m3 = MC.run_monte_carlo(h, model=model, n_paths=300, horizon_days=30, seed=8)
        for p in MC.FAN_PERCENTILES:
            assert _rel(m1.fan[p], m2.fan[p]) <= 1e-12, model
        assert _rel(m1.terminal, m2.terminal) <= 1e-12 and _rel(m1.sample_paths, m2.sample_paths) <= 1e-12, model
        assert _rel(m1.terminal, m3.terminal) > 1e-6, model
    for path in (ROOT / "core/quant/lab.py", ROOT / "docs/quant_lab_grading.py"):
        src = path.read_text(encoding="utf-8")
        tree = ast.parse(src)
        calls = {ast.unparse(n.func) for n in ast.walk(tree) if isinstance(n, ast.Call)}
        assert not {"datetime.now", "datetime.utcnow", "time.time", "date.today"} & calls, (path.name, calls & {"datetime.now", "time.time", "date.today"})
        assert "default_rng(seed" in src or "default_rng(" not in src


test_t_repro_01c_lab_outputs_reproducible_under_the_seed.test_ids = ["T-REPRO-01c"]


# --------------------------------------------------------------------------- #
# T-CRYPTO-01 (R-17, deferred): the clock branch exists; no sleeve, book or card does
# --------------------------------------------------------------------------- #
def test_t_crypto_01_clock_annualisation_and_no_crypto_sleeve():
    """decision_time_utc("CRYPTO", d) = 00:00:00Z on d+1 (tz-aware, year end, weekends, never NotASession, no
    calendar file read), close_print_bound_utc the same instant, is_session always True; annualisation 365 against
    252 for equities; nothing registered: no crypto sleeve key in the store, no CRYPTO card in the registry, and a
    crypto_venue header is refused on its typed owner nulls (notional, venue currency / nav_fx)."""
    d = date(2026, 10, 2)
    t = K.decision_time_utc("CRYPTO", d)
    assert t == U(2026, 10, 3, 0, 0, 0) and t.tzinfo is not None and t.utcoffset() == timedelta(0)
    assert K.decision_time_utc("CRYPTO", date(2026, 12, 31)) == U(2027, 1, 1)
    for wd in (date(2026, 10, 3), date(2026, 10, 4)):                                   # Saturday, Sunday
        assert K.is_session("CRYPTO", wd) is True
        assert K.decision_time_utc("CRYPTO", wd) == U(wd.year, wd.month, wd.day) + timedelta(days=1)
    assert K.close_print_bound_utc("CRYPTO", d) == t and K.next_session("CRYPTO", d) == date(2026, 10, 3)
    assert K.prev_session("CRYPTO", date(2026, 10, 5)) == date(2026, 10, 4)
    _raises(lambda: K.decision_time_utc("CRYPTO", "2026-10-02"), TypeError, "datetime.date")
    assert K.annualisation_days("CRYPTO") == 365 and K.annualisation_days("KR") == K.annualisation_days("US") == 252
    assert K.CRYPTO_VENUES == ("UPBIT", "BINANCE", "COINGECKO")
    from core.crypto.analytics import CRYPTO_DAYS
    assert CRYPTO_DAYS == 365
    rng = np.random.default_rng(11)
    x = rng.normal(0, 0.02, 2000)
    s = float(np.std(x, ddof=1))
    assert abs(s * math.sqrt(K.annualisation_days("CRYPTO")) / (s * math.sqrt(K.annualisation_days("KR"))) - math.sqrt(365 / 252)) < 1e-12
    from core.calendars.store import CalendarUnsigned, CalendarCoverageError, NotASession
    # the KR clock still fails closed on the unsigned shipped set; CRYPTO did not touch it
    _raises(lambda: K.decision_time_utc("KR", d), (CalendarUnsigned, CalendarCoverageError, NotASession))
    store, get = _store_get_factory()
    assert get("time.markets.CRYPTO") == {"tz": "UTC", "decision_utc": "00:00:00Z of d+1", "venue_declared": True, "annualisation_days": 365}
    assert get("sleeves.CRYPTO") is None and set(get("sleeves")) == {"US", "KR"} and get("sleeves.CRYPTO.notional_nav") is None
    from core.quant import cards
    assert "CRYPTO" not in {c.market for c in cards.REGISTRY} and not any("crypto" in c.card_id.lower() for c in cards.REGISTRY)
    assert not any(c.instrument_book == "crypto_venue" for c in cards.REGISTRY)
    header = {"rule_id": "R-17", "instrument_book": "crypto_venue", "rebalance": "daily", "no_trade_band": 0.0,
              "notional_nav": {"ref": "sleeves.CRYPTO.notional_nav"}, "fill_model": "venue_close",
              "costs": {"per_side": "read_from_gate", "floor": "tick_floor", "stress": 2.0, "stress_line": "printed"},
              "printed_lines": ["exec_variants_ABC"]}
    out = header_checks(header, get, rule={"rule_id": "R-17", "market": "CRYPTO"})
    assert any(r.startswith("2 ") and "owner input" in r and "sleeves.CRYPTO.notional_nav" in r for r in out), out
    assert any(r.startswith("9 ") and "nav_fx" in r for r in out), out
    assert cost_per_side("crypto_venue").bp == 10.0 and INSTRUMENT_BOOKS["crypto_venue"].venue is None
    books_src = (ROOT / "core/engine/books.py").read_text(encoding="utf-8")
    assert "recommended:CRYPTO" not in books_src and "CRYPTO" not in books_src.split('"""', 2)[2]


test_t_crypto_01_clock_annualisation_and_no_crypto_sleeve.test_ids = ["T-CRYPTO-01"]


def test_t_crypto_01_asof_join_with_staleness_labels_owner():
    """"weekday macro data joined as-of with staleness labels" is specified with the sleeve (R-17 DEFERRED): no series
    is bound to a CRYPTO consumer in data/macro/series_registry.yaml and no venue row is declared."""
    raise NotRun("OWNER: crypto sleeve (R-17 deferred): declare the venue row (UPBIT | BINANCE | COINGECKO, bar close "
                 "00:00:00Z of d+1), sleeves.CRYPTO.notional_nav and the CRYPTO consumer bindings before the as-of join exists")


test_t_crypto_01_asof_join_with_staleness_labels_owner.test_ids = ["T-CRYPTO-01"]


# --------------------------------------------------------------------------- #
# T-FX-01 (R-17, deferred): the instrument predicate
# --------------------------------------------------------------------------- #
def test_t_fx_01_fx_card_without_a_declared_instrument_is_refused():
    """An FX-market rule with instrument_book missing / null / KRX_ETF_line / crypto_venue is refused naming R-17;
    FX_KRX_USD_futures (+ roll_calendar) and FX_broker_spot pass the predicate; a multi_line header with an FX line
    outside the FX books is refused; an FX book on a non-FX rule is refused; FX costs 10 bp from the gate table and a
    header literal below it raises (T-COST-03 unchanged); the shipped store is byte-identical afterwards."""
    fx_rule = {"rule_id": "R-17", "market": "FX"}
    kr_rule = {"rule_id": "R-03", "market": "KR"}
    assert FX_BOOKS == frozenset({"FX_KRX_USD_futures", "FX_broker_spot"})
    for book in (None, "KRX_ETF_line", "crypto_venue", "US_shares_KIS"):
        h = _fx_header(instrument_book=book)
        if book is None:
            del h["instrument_book"]
        msgs = fx_instrument_check(h, fx_rule)
        assert len(msgs) == 1 and "R-17" in msgs[0] and "T-FX-01" in msgs[0] and msgs[0].startswith("13 "), (book, msgs)
        assert any(m.startswith("13 ") for m in header_checks(h, lambda k: None, rule=fx_rule)), book
    assert fx_instrument_check(_fx_header(instrument_book=None), fx_rule)
    assert fx_instrument_check(_fx_header(), fx_rule) == []
    assert fx_instrument_check(_fx_header(instrument_book="FX_KRX_USD_futures", roll_calendar={"rule": "roll_before_expiry"}), fx_rule) == []
    assert not any(m.startswith("13 ") for m in header_checks(_fx_header(), lambda k: 2e9, rule=fx_rule))
    multi = _fx_header(instrument_book="multi_line", instrument_lines=[{"market": "FX", "instrument_book": "KRX_ETF_line"},
                                                                       {"market": "KR", "instrument_book": "KRX_ETF_line"}])
    assert any("13 " in m and "FX line" in m for m in fx_instrument_check(multi, fx_rule))
    good = dict(multi, instrument_lines=[{"market": "FX", "instrument_book": "FX_broker_spot"}, {"market": "KR", "instrument_book": "KRX_ETF_line"}])
    assert fx_instrument_check(good, fx_rule) == [] and fx_instrument_check(good, kr_rule) == []
    assert any("not 'FX'" in m for m in fx_instrument_check(_fx_header(), kr_rule))
    assert any("not 'FX'" in m for m in fx_instrument_check(_fx_header(), None))          # no market: fail closed
    assert cost_per_side("FX_broker_spot").bp == 10.0 and cost_per_side("FX_KRX_USD_futures").bp == 10.0
    low = _fx_header(costs={"per_side": "read_from_gate", "floor": "tick_floor", "stress": 2.0, "stress_line": "printed", "bp": 5.0})
    _raises(lambda: check_cost_policy(low, INSTRUMENT_BOOKS["FX_broker_spot"]), CostLowered, "below the fx table rate 10.0")
    assert any(m.startswith("10 cost") for m in header_checks(low, lambda k: 2e9, rule=fx_rule))
    # through validate_card_header on the shipped store: refused naming R-17, nothing written
    from core.rules.macro_rules import RuleObject, validate_card_header
    before = hashlib.md5(STORE_PATH.read_bytes()).hexdigest()
    store, _ = _store_get_factory()
    rule = RuleObject(rule_id="R-17", kind="CONVENTION", market="FX")
    rep = validate_card_header(_fx_header(instrument_book="KRX_ETF_line"), store, rule=rule)
    assert not rep.ok and any("R-17" in i.message and "T-FX-01" in i.message for i in rep.errors), [i.message for i in rep.errors]
    rep_ok = validate_card_header(_fx_header(), store, rule=rule)
    assert not any("13 FX" in i.message for i in rep_ok.errors)
    assert hashlib.md5(STORE_PATH.read_bytes()).hexdigest() == before


test_t_fx_01_fx_card_without_a_declared_instrument_is_refused.test_ids = ["T-FX-01"]


def test_t_fx_01_granularity_floor_needs_the_contract_multiplier_owner():
    """FX_KRX_USD_futures is a futures book: roll_calendar required and the R-26 5 % granularity floor applies, but one
    contract's KRW notional needs the contract multiplier (typed null, owner input) -> NOT_RUN OWNER."""
    h = _fx_header(instrument_book="FX_KRX_USD_futures")
    out = header_checks(h, lambda k: 2e9, rule={"rule_id": "R-17", "market": "FX"})
    assert any(m.startswith("6 futures") and "roll_calendar" in m for m in out), out
    assert any(m.startswith("6 granularity") and "owner input" in m and "multiplier" in m for m in out), out
    assert INSTRUMENT_BOOKS["FX_KRX_USD_futures"].contract_multiplier is None and INSTRUMENT_BOOKS["FX_KRX_USD_futures"].kind == "futures"
    from core.quant.instruments import owner_inputs
    assert "FX_KRX_USD_futures.contract_multiplier" in owner_inputs()
    raise NotRun("OWNER: FX_KRX_USD_futures contract multiplier and roll calendar (R-26 granularity floor; R-17 deferred)")


test_t_fx_01_granularity_floor_needs_the_contract_multiplier_owner.test_ids = ["T-FX-01"]


# --------------------------------------------------------------------------- #
# The labelled SMOKE grading on local vendor closes (rulings section 1: a dry run, never a card run)
# --------------------------------------------------------------------------- #
def test_smoke_grading_on_local_closes_runs_offline_and_is_labelled_vendor_data():
    """docs/quant_lab_grading.py --smoke grades KODEX 200 from the local Yahoo cache (last row dropped) into a temp
    dir with the SMOKE / VENDOR DATA label on every output; the formal run refuses naming the KOSPI fixtures and
    writes nothing. Runs under the hermetic guard (no provider import)."""
    from docs import quant_lab_grading as Q
    assert "SMOKE" in Q.LABEL and "VENDOR DATA" in Q.LABEL and "not a card run" in Q.LABEL
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "quant_lab"
        m = Q.run_smoke(out=out, refit_every=500, symbols={"KODEX200": Q.SYMBOLS["KODEX200"]}, with_config_hash=False)
        assert m["run"] == "smoke" and m["seed"] == 11 and m["label"] == Q.LABEL and m["git_hash"] == "UNVERSIONED"
        rep = json.loads((out / "KODEX200.json").read_text(encoding="utf-8"))
        assert rep["label"] == Q.LABEL and rep["acts"] is False and rep["market"] == "KR" and rep["lines"][-1] == Q.LABEL
        assert rep["verdict"] in ("PASS", "FAIL", "NOT_RUN") and "SMOKE" in m["verdicts"]["KODEX200"]
        assert rep["periods"]["2016-26"]["n"] > rep["periods"]["2026"]["n"] > 100 and rep["repro"]["seed"] == 11
        assert m["results_md5"] == hashlib.md5(canonical_json({"KODEX200": rep}).encode("utf-8")).hexdigest()
        assert m["inputs_md5"]["yf_069500.KS.csv"] == Q.md5_file(Q.CACHE / "yf_069500.KS.csv")
        formal = Path(tmp) / "formal"
        assert Q.run_formal(out=formal) == 2 and not formal.exists()
        assert Q.main(["--out", str(formal)]) == 2 and not formal.exists()
    dates, closes = Q.load_closes("yf_069500.KS.csv")
    assert dates[0] == "2007-01-29" and dates[-1] == "2026-09-22" and closes.size == len(dates)      # last row dropped


test_smoke_grading_on_local_closes_runs_offline_and_is_labelled_vendor_data.test_ids = []


def tests():
    return [(name, fn) for name, fn in sorted(globals().items()) if name.startswith("test_") and callable(fn)]


if __name__ == "__main__":
    from tests.macro_acceptance import run_module
    raise SystemExit(run_module(globals()))
