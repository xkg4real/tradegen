"""Acceptance checks for the QUANTGEN FICC core.

Hermetic by construction: `_no_network()` replaces the two — and only two —
socket-opening functions in `core.ficc.data` (`_fred_fetch`, `_yf_fetch`)
with one that raises, and disables the on-disk cache so a warm cache cannot
mask the degradation path. Under it, `auto` must come back SYNTHETIC with the
provider named in `note`, and an explicit provider must raise `FICCError`.
Everything else runs on `source="synthetic"`.

Grouped the way the core is grouped: data, curves, bonds, swaps, fx, ratesim,
macro, structured, insights, charts. Expensive fixtures are built once.
"""
from __future__ import annotations

import contextlib
import functools
import json
import math

import numpy as np

import config
from core.ficc import bonds, curves, data, fx, insights, macro, ratesim, structured, swaps
from core.ficc.common import BP, KEY_TENORS, UST_TENORS, FICCError, bp_text, pct_text


# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #
@contextlib.contextmanager
def _no_network():
    """Every provider call raises; cache TTL 0 so nothing on disk can answer."""
    def _boom(*_a, **_k):
        raise FICCError("offline (acceptance suite)")
    saved = (data._fred_fetch, data._yf_fetch, config.FICC_CACHE_TTL_SECONDS)
    data._fred_fetch = data._yf_fetch = _boom
    config.FICC_CACHE_TTL_SECONDS = 0.0
    try:
        yield
    finally:
        data._fred_fetch, data._yf_fetch, config.FICC_CACHE_TTL_SECONDS = saved


def _raises(fn, exc=FICCError):
    try:
        fn()
    except exc:
        return
    raise AssertionError(f"expected {exc.__name__}")


_PAR = (0.052, 0.051, 0.050, 0.047, 0.044, 0.043, 0.042, 0.043, 0.044, 0.047, 0.046)
_UP = (0.035, 0.036, 0.037, 0.038, 0.040, 0.041, 0.043, 0.044, 0.045, 0.047, 0.046)
_BOND = bonds.Bond(coupon=0.05, maturity=10.0, name="5% 10y")


@functools.lru_cache(maxsize=None)
def _curve():
    return curves.bootstrap_par_curve(UST_TENORS, _PAR, date="2026-09-04", source="TEST")


@functools.lru_cache(maxsize=None)
def _up_curve():
    return curves.bootstrap_par_curve(UST_TENORS, _UP, date="2026-09-04", source="TEST")


@functools.lru_cache(maxsize=None)
def _panel():
    return data.synthetic_curve_panel(days=200)


@functools.lru_cache(maxsize=None)
def _report():
    return curves.analyze_curve(_panel())


@functools.lru_cache(maxsize=None)
def _carry_inputs():
    pairs = {c: ("USD" + c if c in ("JPY", "KRW", "CAD", "CHF") else c + "USD")
             for c in data.G10_KRW if c != "USD"}
    spots = {p: data.synthetic_fx(p, days=300) for p in pairs.values()}
    rates = {c: data.synthetic_series(f"RATE_{c}", days=300, kind="rate") for c in data.G10_KRW}
    return spots, rates


@functools.lru_cache(maxsize=None)
def _sheet():
    return macro.macro_sheet(source="synthetic", days=300)


@functools.lru_cache(maxsize=None)
def _ppn():
    return structured.principal_protected_note(_up_curve(), spot=1.10, vol=0.08,
                                               r_for_or_div=0.02, maturity=3.0)


# --------------------------------------------------------------------------- #
# Data
# --------------------------------------------------------------------------- #
def test_data_synthetic_is_deterministic_and_labeled():
    a = data.synthetic_series("DGS10", days=100, kind="rate")
    assert a.values == data.synthetic_series("DGS10", days=100, kind="rate").values
    assert a.values != data.synthetic_series("DGS2", days=100, kind="rate").values
    assert a.source == "SYNTHETIC" and a.note, "synthetic must label itself"
    assert data.synthetic_fx("EURUSD", days=50).values == data.synthetic_fx("EUR/USD",
                                                                              days=50).values
    assert np.array_equal(data.synthetic_curve_panel(days=30).yields,
                          data.synthetic_curve_panel(days=30).yields)


def test_data_synthetic_never_touches_the_cache():
    before = set(data._MEM)
    saved = config.FICC_CACHE_TTL_SECONDS
    config.FICC_CACHE_TTL_SECONDS = 3600.0
    try:
        with _no_network():                              # network dead, cache "on"
            config.FICC_CACHE_TTL_SECONDS = 3600.0
            data.load_series("DGS10", source="synthetic", days=50)
            data.load_fx_spot("USDJPY", source="synthetic", days=50)
            data.load_treasury_curve(source="synthetic", days=30)
    finally:
        config.FICC_CACHE_TTL_SECONDS = saved
    assert set(data._MEM) == before, "synthetic results must never be cached"


def test_data_auto_degrades_to_synthetic_naming_the_provider():
    with _no_network():
        s = data.load_series("DGS10", days=100)
        assert s.source == "SYNTHETIC" and "FRED failed" in s.note and "offline" in s.note
        f = data.load_fx_spot("USDKRW")
        assert f.source == "SYNTHETIC" and "YFINANCE failed" in f.note and f.label == "USD/KRW"
        p = data.load_treasury_curve()
        assert p.source == "SYNTHETIC" and "FRED failed" in p.note
        r = data.load_short_rate("USD")
        assert r.source == "SYNTHETIC" and "FRED failed" in r.note
        many = data.load_many(["DGS2", "EURUSD=X"], days=50)
        assert {v.source for v in many.values()} == {"SYNTHETIC"}


def test_data_explicit_provider_raises_offline():
    with _no_network():
        for bad in (lambda: data.load_series("DGS10", source="fred"),
                    lambda: data.load_fx_spot("EURUSD", source="yfinance"),
                    lambda: data.load_treasury_curve(source="fred"),
                    lambda: data.load_short_rate("EUR", source="fred"),
                    lambda: data.load_treasury_curve(source="yfinance"),
                    lambda: data.load_series("X", source="bloomberg")):
            _raises(bad)
        pr = data.probe()
        assert pr["fred"]["ok"] is False and pr["yfinance"]["ok"] is False


def test_data_shapes_are_clean():
    p = _panel()
    assert p.yields.shape == (200, 11) and not np.isnan(p.yields).any() and len(p) == 200
    snap = p.latest()
    assert snap.tenors == UST_TENORS and 0.0 < snap.par_yields[8] < 0.15
    assert "monthly" in data.load_short_rate("KRW", source="synthetic").note
    assert "daily" in data.load_short_rate("USD", source="synthetic").note
    s = data.synthetic_series("SOFR", days=60, kind="rate")
    assert s.change(5) is not None and s.change(100) is None and len(s.window(10)) == 10


# --------------------------------------------------------------------------- #
# Curves
# --------------------------------------------------------------------------- #
def test_curve_bootstrap_round_trips_par_inputs():
    flat = curves.bootstrap_par_curve(UST_TENORS, [0.05] * len(UST_TENORS))
    z_cont = 2 * math.log1p(0.025)
    assert all(abs(z - z_cont) < 1e-6 for t, z in zip(flat.tenors, flat.zeros) if t >= 1.0)
    c = _curve()
    for t, y in zip(UST_TENORS, _PAR):
        got = c.par_rate(t) if t >= 1.0 else (1.0 / c.df(t) - 1.0) / t
        assert abs(got - y) < 1e-8, (t, got, y)
    sparse = curves.bootstrap_par_curve([1, 2, 5, 10, 30], [0.047, 0.044, 0.042, 0.044, 0.046])
    assert abs(sparse.par_rate(30.0) - 0.046) < 1e-8, "must survive a sparse grid"


def test_curve_df_is_one_at_zero_and_monotone():
    c = _curve()
    assert c.df(0.0) == 1.0
    grid = np.linspace(0.0, 40.0, 401)
    assert np.all(np.diff(c.df(grid)) < 0), "DF must fall with tenor"
    assert abs(c.fwd(1.0, 2.0) - (c.df(1.0) / c.df(2.0) - 1.0)) < 1e-14


def test_curve_bumps_are_local_and_parallel():
    c = _curve()
    up = c.shifted(10.0)
    assert all(abs((zu - z0) - 10 * BP) < 1e-12 for zu, z0 in zip(up.zeros, c.zeros))
    kr = c.key_rate_shifted(5.0, 10.0)
    assert abs(kr.zero(5.0) - c.zero(5.0) - 10 * BP) < 1e-12
    assert abs(kr.zero(10.0) - c.zero(10.0)) < 1e-12 and abs(kr.zero(3.0) - c.zero(3.0)) < 1e-12


def test_curve_ns_fit_is_tight():
    exact = curves.nelson_siegel(np.array(UST_TENORS), 0.045, -0.01, 0.02, 2.0)
    assert curves.fit_nelson_siegel(UST_TENORS, exact).rmse < 1e-6
    snap = _panel().latest()
    assert curves.fit_nelson_siegel(snap.tenors, snap.par_yields).rmse < 5 * BP
    assert curves.fit_nelson_siegel(snap.tenors, snap.par_yields, svensson=True).rmse < 5 * BP


def test_curve_report_uses_allowed_regime_and_shape_strings():
    for m in ("bootstrap", "nelson_siegel", "svensson"):
        rep = curves.analyze_curve(_panel(), lookback=20, method=m)
        assert rep.curve.method == m
        assert rep.shape in ("normal", "flat", "inverted", "humped")
        assert rep.regime in macro.CURVE_REGIMES
        assert set(rep.descriptors) >= {"2s10s", "5s30s", "3m10y", "2s5s10s_fly", "level",
                                        "1y1y", "2y1y", "5y5y", "1y_fwd_1y_ahead"}
        assert "2s10s" in rep.changes and "10y" in rep.changes and rep.lookback == 20
    d = _report().descriptors
    snap = _panel().latest()
    par = dict(zip(snap.tenors, snap.par_yields))
    assert abs(d["2s10s"] - (par[10.0] - par[2.0])) < 1e-12


def test_curve_pca_explains_level_first():
    pca = curves.curve_pca(_panel())
    assert pca.explained[0] > 0.5 and np.all(pca.loadings[:, 0] > 0), "PC1 = level, positive"
    assert pca.loadings[-1, 1] > 0, "PC2 = slope, long end positive"
    assert pca.scores.shape == (len(_panel()) - 1, 3) and float(np.sum(pca.explained)) <= 1 + 1e-12
    _raises(lambda: curves.curve_pca(data.synthetic_curve_panel(days=30)))


# --------------------------------------------------------------------------- #
# Bonds
# --------------------------------------------------------------------------- #
def test_bond_par_prices_at_100_and_yield_round_trips():
    assert abs(bonds.price_from_yield(_BOND, 0.05) - 100.0) < 1e-9
    assert abs(bonds.yield_from_price(_BOND, 100.0) - 0.05) < 1e-12
    frac = bonds.Bond(coupon=0.04, maturity=7.3)
    assert abs(bonds.yield_from_price(frac, bonds.price_from_yield(frac, 0.045)) - 0.045) < 1e-12


def test_bond_duration_matches_numeric_derivative():
    y, h = 0.05, 1e-5
    p0, pu, pd = (bonds.price_from_yield(_BOND, v) for v in (y, y + h, y - h))
    num_mac = -(pu - pd) / (2 * h) * (1 + y / _BOND.freq) / p0
    assert abs(bonds.macaulay_duration(_BOND, y) - num_mac) < 1e-6
    mod = bonds.macaulay_duration(_BOND, y) / (1 + y / _BOND.freq)
    assert abs(bonds.modified_duration(_BOND, y) - mod) < 1e-9
    assert abs(bonds.dv01(_BOND, y) - bonds.modified_duration(_BOND, y) * 100.0) < 1e-9


def test_bond_convexity_is_positive_and_numeric():
    y, h = 0.05, 1e-5
    p0, pu, pd = (bonds.price_from_yield(_BOND, v) for v in (y, y + h, y - h))
    cvx = bonds.convexity(_BOND, y)
    assert cvx > 0 and abs(cvx - (pu - 2 * p0 + pd) / h ** 2 / p0) < 1e-3


def test_bond_flat_curve_reprices_the_yield():
    y = 0.05
    flat = curves.flat_curve(_BOND.freq * math.log1p(y / _BOND.freq))
    assert abs(bonds.price_from_curve(_BOND, flat) - bonds.price_from_yield(_BOND, y)) < 1e-9


def test_bond_krd_sums_to_dv01():
    flat = curves.flat_curve(2 * math.log1p(0.025))
    krd = bonds.key_rate_dv01(_BOND, flat)
    assert set(krd) == set(KEY_TENORS)
    assert abs(sum(krd.values()) / bonds.dv01(_BOND, 0.05) - 1.0) < 0.03
    assert krd[10.0] > krd[2.0] > 0 and abs(krd[30.0]) < 1e-6
    a = bonds.analyze_bond(_BOND, price=98.0, curve=_curve())
    assert abs(sum(a.krd.values()) / a.dv01 - 1.0) < 0.05


def test_bond_z_spread_round_trips():
    c = _curve()
    z = bonds.z_spread(_BOND, c, 95.0)
    assert abs(bonds.price_from_curve(_BOND, c, spread=z) - 95.0) < 1e-9
    a = bonds.analyze_bond(_BOND, price=98.0, curve=c)
    assert abs(bonds.price_from_curve(_BOND, c, spread=a.z_spread) - 98.0) < 1e-9
    assert abs(a.carry_roll.total - a.carry_roll.carry - a.carry_roll.rolldown) < 1e-12


def test_bond_scenarios_show_convexity():
    a = bonds.analyze_bond(_BOND, price=98.0, curve=_curve())
    rows = bonds.scenario_pnl(_BOND, _curve(), 98.0)
    assert [r.name for r in rows] == list(bonds.DEFAULT_SCENARIOS)
    by = {r.name: r for r in rows}
    assert by["+25bp parallel"].pnl < 0 < by["-25bp parallel"].pnl
    assert by["+100bp parallel"].pnl > -100 * a.dv01, "a +100bp loss is cushioned by convexity"
    assert by["-100bp parallel"].pnl > 100 * a.dv01, "a -100bp gain is boosted by convexity"
    assert by["bear steepener"].pnl < 0 < by["bull flattener"].pnl


def test_bond_analyze_requires_exactly_one_of_price_or_yield():
    _raises(lambda: bonds.analyze_bond(_BOND), ValueError)
    _raises(lambda: bonds.analyze_bond(_BOND, price=99.0, ytm=0.05), ValueError)
    flat = bonds.analyze_bond(_BOND, ytm=0.05)
    assert "flat" in flat.note and abs(flat.curve_price - 100.0) < 1e-9


def test_futures_hedge_arithmetic():
    assert abs(bonds.futures_hedge_ratio(800.0, 65.0, 0.8) - 800.0 * 0.8 / 65.0) < 1e-12


# --------------------------------------------------------------------------- #
# Swaps
# --------------------------------------------------------------------------- #
def test_swap_at_par_has_zero_pv_and_payer_dv01_positive():
    c = _curve()
    payer = swaps.analyze_swap(swaps.Swap(tenor=10.0), c)
    recv = swaps.analyze_swap(swaps.Swap(tenor=10.0, pay_fixed=False), c)
    assert abs(payer.pv) < 1e-6 and payer.dv01 > 0 and abs(recv.dv01 + payer.dv01) < 1e-6
    assert 500 < payer.dv01 < 1000, payer.dv01
    assert abs(payer.par_rate - swaps.par_swap_rate(c, 10.0)) < 1e-14


def test_swap_krd_sums_to_dv01():
    rep = swaps.analyze_swap(swaps.Swap(tenor=10.0), _curve())
    assert abs(sum(rep.krd.values()) - rep.dv01) < 0.01 * rep.dv01
    assert set(rep.fwd_rates) == {"1y1y", "2y1y", "5y5y", "10y10y"}
    assert abs(rep.fwd_rates["5y5y"] - swaps.par_swap_rate(_curve(), 5.0, start=5.0)) < 1e-14


def test_swap_off_market_pv_is_minus_spread_times_annuity():
    c = _curve()
    off = swaps.Swap(tenor=5.0, fixed_rate=swaps.par_swap_rate(c, 5.0) + 0.01)
    assert abs(swaps.swap_pv(off, c) + 1e6 * 0.01 * swaps.annuity(c, 5.0)) < 1e-6


def test_swaption_put_call_parity():
    c = _curve()
    sp = swaps.price_swaption(swaps.Swaption(1.0, 5.0, strike=0.05), c, vol=0.008)
    sr = swaps.price_swaption(swaps.Swaption(1.0, 5.0, strike=0.05, payer=False), c, vol=0.008)
    assert abs((sp.premium - sr.premium) - sp.annuity * (sp.forward - 0.05) * 1e6) < 1e-6
    assert sp.delta > 0 > sr.delta and sp.theta_1d < 0
    assert abs(sp.premium_bp - sp.premium / 1e6 / BP) < 1e-9


def test_black_and_bachelier_agree_atm_and_implied_vols_round_trip():
    F, K, T, vol = 0.04, 0.04, 2.0, 0.25
    b = swaps.black76(F, K, T, vol)
    n = swaps.bachelier(F, K, T, vol * F)
    assert abs(b.price / n.price - 1.0) < 0.02
    assert abs(swaps.implied_black_vol(b.price, F, K, T) - vol) < 1e-6
    assert abs(swaps.implied_normal_vol(n.price, F, K, T) - vol * F) < 1e-6
    nv = swaps.normal_from_black(F, 0.045, T, 0.3)
    assert abs(swaps.black_from_normal(F, 0.045, T, nv) - 0.3) < 1e-6
    sb = swaps.price_swaption(swaps.Swaption(1.0, 5.0), _curve(), vol=0.30, model="black")
    back = swaps.price_swaption(swaps.Swaption(1.0, 5.0), _curve(), vol=sb.other_model_vol)
    assert abs(back.premium - sb.premium) < 1e-6, "other_model_vol must reprice the premium"


def test_implied_vol_outside_no_arb_raises():
    F, K, T = 0.04, 0.04, 2.0
    _raises(lambda: swaps.implied_black_vol(0.0, F, K, T))
    _raises(lambda: swaps.implied_black_vol(2 * F, F, K, T))
    _raises(lambda: swaps.price_swaption(swaps.Swaption(1.0, 5.0), _curve(), vol=0.3,
                                         model="sabr"))


def test_cap_is_sum_of_caplets_and_cap_minus_floor_is_the_swap():
    c = _curve()
    cap = swaps.price_cap_floor(c, 5.0, None, vol=0.008)
    assert abs(cap.premium - sum(r[3] for r in cap.caplets)) < 1e-9
    assert abs(cap.strike - swaps.par_swap_rate(c, 5.0, freq=4)) < 1e-14 and cap.cap
    flo = swaps.price_cap_floor(c, 5.0, cap.strike, vol=0.008, cap=False)
    swap_val = sum((e - s) * c.df(e) * (f - cap.strike) * 1e6 for s, e, f, _ in cap.caplets)
    assert abs((cap.premium - flo.premium) - swap_val) < 1e-6 and not flo.cap


def test_atm_straddle_is_twice_the_atm_payer():
    c = _curve()
    two = swaps.atm_straddle(c, 1.0, 5.0, vol=0.008, notional=1e6)
    payer = swaps.price_swaption(swaps.Swaption(1.0, 5.0), c, vol=0.008).premium
    assert abs(two - 2 * payer) < 1e-6 * two


# --------------------------------------------------------------------------- #
# FX
# --------------------------------------------------------------------------- #
_S, _K, _T, _RD, _RF, _V = 1.10, 1.12, 0.5, 0.045, 0.03, 0.09


def test_fx_forward_is_cip_and_its_basis_is_zero():
    F = fx.forward(_S, _RD, _RF, _T)
    assert abs(F - _S * math.exp((_RD - _RF) * _T)) < 1e-14
    assert abs(fx.implied_basis(_S, F, _RD, _RF, _T)) < 1e-12
    assert fx.carry(_RD, _RF) == _RF - _RD


def test_fx_forward_points_follow_the_pip_rule():
    F = fx.forward(_S, _RD, _RF, _T)
    assert abs(fx.forward_points(_S, F) - (F - _S) / 1e-4) < 1e-9
    assert abs(fx.forward_points(150.0, 149.0) + 100.0) < 1e-9


def test_gk_parity_and_delta_bounds():
    c = fx.garman_kohlhagen(_S, _K, _T, _RD, _RF, _V, True)
    p = fx.garman_kohlhagen(_S, _K, _T, _RD, _RF, _V, False)
    parity = _S * math.exp(-_RF * _T) - _K * math.exp(-_RD * _T)
    assert abs((c.price - p.price) - parity) < 1e-12
    assert 0 < c.delta_spot < 1 and -1 < p.delta_spot < 0 and c.gamma > 0 and c.vega > 0
    deep = fx.garman_kohlhagen(_S, 0.5, _T, _RD, _RF, _V)
    assert abs(deep.delta_spot - math.exp(-_RF * _T)) < 1e-6


def test_gk_implied_vol_round_trips():
    c = fx.garman_kohlhagen(_S, _K, _T, _RD, _RF, _V, True)
    p = fx.garman_kohlhagen(_S, _K, _T, _RD, _RF, _V, False)
    assert abs(fx.implied_vol_gk(c.price, _S, _K, _T, _RD, _RF) - _V) < 1e-8
    assert abs(fx.implied_vol_gk(p.price, _S, _K, _T, _RD, _RF, call=False) - _V) < 1e-8


def test_strike_from_delta_round_trips():
    for call, sign in ((True, 1.0), (False, -1.0)):
        k = fx.strike_from_delta(0.25, _S, _T, _RD, _RF, _V, call=call)
        got = fx.garman_kohlhagen(_S, k, _T, _RD, _RF, _V, call).delta_spot
        assert abs(got - sign * 0.25) < 1e-10
    kf = fx.strike_from_delta(0.25, _S, _T, _RD, _RF, _V, forward_delta=True)
    assert abs(fx.garman_kohlhagen(_S, kf, _T, _RD, _RF, _V).delta_fwd - 0.25) < 1e-10


def test_smile_ordering_follows_the_risk_reversal():
    pts = fx.smile_from_quotes(fx.SmileQuote(_T, 0.09, 0.01, 0.003), _S, _RD, _RF)
    assert [x.label for x in pts] == ["25d put", "ATM", "25d call"]
    assert pts[0].strike < pts[1].strike < pts[2].strike
    assert pts[2].vol > pts[0].vol, "rr > 0 means calls are dearer than puts"
    assert abs(pts[0].delta + 0.25) < 1e-9 and abs(pts[2].delta - 0.25) < 1e-9
    neg = fx.smile_from_quotes(fx.SmileQuote(_T, 0.09, -0.01, 0.003), _S, _RD, _RF)
    assert neg[2].vol < neg[0].vol


def test_sabr_reproduces_its_quotes():
    F = fx.forward(_S, _RD, _RF, _T)
    pts = fx.smile_from_quotes(fx.SmileQuote(_T, 0.09, 0.01, 0.003), _S, _RD, _RF)
    Ks = np.array([x.strike for x in pts])
    true = fx.sabr_vol(F, Ks, _T, 0.09, 1.0, -0.25, 0.8)
    fit = fx.calibrate_sabr(F, _T, Ks, true, beta=1.0)
    assert fit.rmse < 1e-4 and np.all(np.abs(fx.smile_curve(fit, F, _T, Ks) - true) < 1e-4)
    fit_q = fx.calibrate_sabr(F, _T, Ks, [x.vol for x in pts])
    assert fit_q.rmse < 1e-4 and fit_q.converged and fit_q.beta == 1.0


def test_carry_table_inverts_usd_base_pairs():
    spots, rates = _carry_inputs()
    rows = fx.carry_table(spots, rates)
    assert len(rows) == 7 and all(a.score >= b.score for a, b in zip(rows, rows[1:]))
    jpy = next(r for r in rows if r.ccy == "JPY")
    assert jpy.pair == "USDJPY" and jpy.spot == spots["USDJPY"].last
    assert abs(jpy.carry - (rates["JPY"].last - rates["USD"].last)) < 1e-12
    assert abs(jpy.mom_3m - (spots["USDJPY"].values[-64] / jpy.spot - 1.0)) < 1e-12
    eur = next(r for r in rows if r.ccy == "EUR")
    assert abs(eur.mom_3m - (eur.spot / spots["EURUSD"].values[-64] - 1.0)) < 1e-12


def test_carry_backtest_is_sane_and_costs_only_hurt():
    spots, rates = _carry_inputs()
    bt = fx.carry_backtest(spots, rates, top_n=3, cost_bps=5.0)
    assert bt.equity[0] == 1.0 and bt.bench_equity[0] == 1.0
    assert not np.isnan(bt.equity).any() and len(bt.dates) == bt.equity.size == 300
    assert all(len(l) == 3 and len(s) == 3 and not set(l) & set(s) for _, l, s in bt.positions)
    free = fx.carry_backtest(spots, rates, top_n=3, cost_bps=0.0)
    dear = fx.carry_backtest(spots, rates, top_n=3, cost_bps=50.0)
    assert dear.equity[-1] < bt.equity[-1] < free.equity[-1]
    assert free.n_rebalances == bt.n_rebalances, "costs must not change the signals"
    assert fx.carry_backtest(spots, rates, top_n=3, cost_bps=5.0).equity.tolist() == \
        bt.equity.tolist(), "deterministic"


# --------------------------------------------------------------------------- #
# Rate simulation
# --------------------------------------------------------------------------- #
@functools.lru_cache(maxsize=None)
def _sofr():
    return data.load_short_rate("USD", source="synthetic", days=756)


def test_ratesim_is_seeded_and_reproducible():
    v = ratesim.calibrate(_sofr(), model="vasicek")
    assert v.kappa >= 0.01 and v.sigma > 0
    a = ratesim.simulate(v, n_paths=500, seed=7)
    b = ratesim.simulate(v, n_paths=500, seed=7)
    c = ratesim.simulate(v, n_paths=500, seed=8)
    assert a.terminal.tolist() == b.terminal.tolist() and a.terminal[3] != c.terminal[3]
    for t in (1, len(a.times) - 1):
        assert a.fan[5][t] <= a.fan[25][t] <= a.fan[50][t] <= a.fan[75][t] <= a.fan[95][t]


def test_ratesim_vasicek_reverts_to_theta():
    v = ratesim.calibrate(_sofr(), model="vasicek")
    sv = ratesim.simulate(v, horizon=30.0, n_paths=2000, steps_per_year=52)
    assert abs(sv.mean_terminal - v.theta) <= 0.10 * abs(v.theta)


def test_ratesim_cir_stays_non_negative():
    c = ratesim.calibrate(_sofr(), model="cir")
    sc = ratesim.simulate(c, horizon=2.0, n_paths=2000)
    assert float(np.min(sc.fan[5])) >= 0.0 and float(np.min(sc.terminal)) >= 0.0


def test_ratesim_hull_white_matches_the_curve_at_t0():
    hw = ratesim.calibrate(_sofr(), model="hull_white")
    crv = _report().curve
    r0 = crv.inst_fwd(0.0)
    for T in (0.5, 2.0, 10.0, 30.0):
        assert abs(ratesim.zcb_price(hw, r0, 0.0, T, curve=crv) - crv.df(T)) < 1e-6, T
    sh = ratesim.simulate(hw, horizon=1.0, n_paths=500, curve=crv)
    assert abs(sh.params.r0 - r0) < 1e-12 and len(sh.model_curve_at_horizon) == len(KEY_TENORS)


def test_horizon_pv_var_is_a_non_negative_loss():
    v = ratesim.calibrate(_sofr(), model="vasicek")
    sim = ratesim.simulate(v, horizon=1.0, n_paths=1000, threshold=0.05)
    assert sim.prob_above is not None and 0.0 <= sim.prob_above <= 1.0
    crv = _report().curve
    hb = ratesim.horizon_pv_distribution(v, sim, kind="bond", bond=_BOND, curve=crv)
    hs = ratesim.horizon_pv_distribution(v, sim, kind="swap", swap=swaps.Swap(tenor=10.0),
                                         curve=crv)
    for h in (hb, hs):
        assert h.pvs.size == 500 and np.all(np.isfinite(h.pvs))
        assert h.var95 >= 0 and h.cvar95 >= h.var95 and h.p05 <= h.mean <= h.p95


# --------------------------------------------------------------------------- #
# Macro
# --------------------------------------------------------------------------- #
def test_macro_rows_are_bounded_and_regimes_are_from_the_sets():
    sheet = _sheet()
    assert len(sheet.rows) == len(macro.INDICATORS) and sheet.sources == {"SYNTHETIC": 18}
    for r in sheet.rows:
        assert -6 <= r.z_1y <= 6 and 0 <= r.pct_1y <= 1, r
        assert r.chg_3m is not None and r.last_date == sheet.as_of
    assert sheet.regime.curve in macro.CURVE_REGIMES and sheet.regime.risk in macro.RISK_REGIMES
    assert sheet.regime.dollar in macro.DOLLAR_REGIMES
    assert sheet.regime.inflation in macro.TREND_REGIMES
    assert sheet.regime.real_rates in macro.TREND_REGIMES
    assert sheet.regime.summary and "SYNTHETIC" in sheet.note
    assert sheet.row("DGS10").last < 0.15 and sheet.row("nope") is None


def test_macro_briefs_are_json_payloads():
    d = macro.daily_brief(_sheet())
    w = macro.weekly_brief(_sheet(), _report())
    assert len(d["movers_z"]) == 5 and d["curve"]["10y"] and d["regime"]
    assert len(w["weekly_changes"]) == 18 and w["curve_report"]["shape"] == _report().shape
    json.dumps(d), json.dumps(w)


def test_macro_sheet_offline_auto_is_loudly_synthetic_and_fred_raises():
    with _no_network():
        sheet = macro.macro_sheet(days=300)
        assert sheet.sources == {"SYNTHETIC": 18} and len(sheet.synthetic_ids) == 18
        assert "18/18" in sheet.note
        _raises(lambda: macro.macro_sheet(source="fred", days=300))
        _raises(lambda: macro.macro_sheet(days=10), ValueError)


# --------------------------------------------------------------------------- #
# Structured
# --------------------------------------------------------------------------- #
def test_ppn_fair_below_issue_with_positive_participation():
    ppn = _ppn()
    assert ppn.fair_value <= ppn.issue_price and ppn.participation > 0
    assert abs(ppn.margin - (ppn.issue_price - ppn.fair_value)) < 1e-9
    assert abs(sum(l.value for l in ppn.legs) - ppn.fair_value) < 1e-9
    pay = dict(ppn.payoff_grid)
    assert abs(pay[1.10] - 100.0) < 1e-9 and pay[1.10 * 1.5] > 100.0
    assert ppn.greeks["delta"] > 0 and ppn.greeks["vega"] > 0 and ppn.greeks["dv01"] > 0
    _raises(lambda: structured.principal_protected_note(_up_curve(), spot=1.1, vol=0.08,
                                                        maturity=0.25, margin=5.0))


def test_reverse_convertible_coupon_beats_the_zcb_rate():
    rc = structured.reverse_convertible(_up_curve(), spot=1.10, vol=0.10, r_for_or_div=0.02,
                                        maturity=1.0, strike_pct=0.95)
    assert rc.coupon > _up_curve().par_rate(1.0, 1), "short put must buy a higher coupon"
    assert abs(rc.fair_value - (rc.issue_price - rc.margin)) < 1e-9
    pay = dict(rc.payoff_grid)
    assert pay[1.10 * 0.5] < pay[1.10 * 0.9] < pay[1.10] == pay[1.10 * 1.5]
    assert rc.greeks["vega"] < 0 and rc.legs[1].value < 0


def test_dcd_enhanced_yield_beats_the_plain_deposit():
    c = _up_curve()
    dcd = structured.dual_currency_deposit(c, spot=1350.0, vol=0.09, r_for=0.045, maturity=0.25,
                                           strike=1300.0, base_ccy="USD", quote_ccy="KRW")
    assert dcd.coupon > (1.0 / c.df(0.25) - 1.0) / 0.25 and dcd.currency == "KRW"
    pay = dict(dcd.payoff_grid)
    assert pay[1350.0 * 0.9] < pay[1350.0], "converted below the strike"


def test_steepener_note_warns_about_convexity():
    st = structured.steepener_note(_up_curve(), maturity=5.0, leverage=4.0, floor=0.0, cap=0.06)
    assert "convexity" in st.note.lower()
    assert 0.0 <= st.coupon <= 0.06 and st.participation == 4.0
    assert st.greeks["dv01_2s10s"] > 0 and st.greeks["delta"] == 0.0
    assert any("10y receiver" in h.instrument for h in st.hedge)


def test_hedge_sheet_sizes_spot_swaps_and_futures():
    ppn, c = _ppn(), _up_curve()
    g = ppn.greeks
    assert ppn.hedge[0].quantity < 0 and abs(ppn.hedge[0].quantity + g["delta"] / 0.011) < 1e-6
    assert any("payer swap" in h.instrument for h in ppn.hedge)
    fut = structured.hedge_sheet(ppn, curve=c, futures_dv01_per_contract=65.0)
    assert any(h.unit == "contracts" and abs(h.quantity + g["dv01"] / 65.0) < 1e-9 for h in fut)


# --------------------------------------------------------------------------- #
# Insights
# --------------------------------------------------------------------------- #
def _clean(text: str) -> str:
    assert "None" not in text and "nan" not in text.split() and len(text) > 80, text
    return text


def test_narratives_state_their_numbers():
    rep = _report()
    t = _clean(insights.narrate_curve(rep, curves.curve_pca(_panel())))
    assert rep.shape in t and rep.regime in t and bp_text(rep.descriptors["2s10s"]) in t
    assert "SYNTHETIC" in t and "PCA" in t

    ba = bonds.analyze_bond(_BOND, price=98.5, curve=rep.curve)
    rows = bonds.scenario_pnl(_BOND, rep.curve, 98.5)
    t = _clean(insights.narrate_bond(ba, rows))
    assert f"{ba.dv01:,.0f}" in t and min(rows, key=lambda r: r.pnl).name in t

    sr = swaps.analyze_swap(swaps.Swap(tenor=10.0), rep.curve)
    t = _clean(insights.narrate_swap(sr))
    assert f"{sr.dv01:+,.0f}" in t and pct_text(sr.par_rate, decimals=3) in t

    swn = swaps.price_swaption(swaps.Swaption(1.0, 5.0), rep.curve, vol=0.0080)
    assert f"{swn.premium:,.0f}" in _clean(insights.narrate_swaption(swn))
    cf = swaps.price_cap_floor(rep.curve, 5.0, None, vol=0.0080)
    assert f"{len(cf.caplets)} caplets" in _clean(insights.narrate_cap_floor(cf))

    fwd = fx.forward(_S, _RD, _RF, _T)
    t = _clean(insights.narrate_fx_forward("EURUSD", _S, fwd, fx.forward_points(_S, fwd),
                                           fx.carry(_RD, _RF), basis=-0.0012))
    assert "EUR/USD" in t and "-12.0bp" in t
    gk = fx.garman_kohlhagen(_S, _K, _T, _RD, _RF, _V)
    assert f"{gk.delta_spot:+.3f}" in _clean(insights.narrate_fx_option(gk))

    spots, rates = _carry_inputs()
    crows, bt = fx.carry_table(spots, rates), fx.carry_backtest(spots, rates)
    t = _clean(insights.narrate_carry(crows, bt))
    assert max(crows, key=lambda r: r.score).ccy in t and f"Sharpe {bt.sharpe:.2f}" in t

    prm = ratesim.calibrate(_sofr())
    sim = ratesim.simulate(prm, n_paths=500, threshold=0.05)
    t = _clean(insights.narrate_ratesim(sim))
    assert pct_text(sim.mean_terminal) in t and "Vasicek" in t

    sheet = _sheet()
    t = _clean(insights.narrate_macro(sheet))
    assert sheet.as_of in t and pct_text(sheet.row("DGS10").last) in t
    daily = _clean(insights.narrate_daily_brief(sheet))
    assert sheet.regime.curve in daily and "P19" in daily and "regime is" not in daily   # a descriptive read (rulings 9)

    t = _clean(insights.narrate_structured(_ppn()))
    assert f"{_ppn().fair_value:.2f}" in t and f"{_ppn().participation * 100:.0f}%" in t


def test_weekly_strategy_states_its_views():
    t = _clean(insights.narrate_weekly_strategy(_sheet(), _report(),
                                                fx.carry_table(*_carry_inputs())))
    assert "Duration:" in t and "Curve:" in t and "FX:" in t and "Carry:" in t
    assert f"{_report().descriptors['2s10s'] / BP:+.0f}bp" in t
    _clean(insights.narrate_weekly_strategy(_sheet()))


def test_report_prompt_and_deep_analysis_degrade_without_network():
    assert insights.report_prompt("daily_market_commentary")
    assert insights.report_prompt("weekly_fi_fx_strategy") and insights.report_prompt("bond") == ""
    saved = config.anthropic_key
    config.anthropic_key = lambda: ""
    try:
        a = insights.deep_analysis("weekly_fi_fx_strategy", macro.daily_brief(_sheet()),
                                   question="views?")
    finally:
        config.anthropic_key = saved
    assert a.text == "" and "ANTHROPIC_API_KEY" in a.error


# --------------------------------------------------------------------------- #
# Charts
# --------------------------------------------------------------------------- #
def test_every_fchart_renders_a_data_uri_image():
    import ui.fcharts as fc
    from core.theme import set_mode
    set_mode("dark")
    panel, rep = _panel(), _report()
    curve = rep.curve
    ba = bonds.analyze_bond(_BOND, ytm=0.045, curve=curve)
    pts = fx.smile_from_quotes(fx.SmileQuote(_T, 0.10, 0.01, 0.003), _S, _RD, _RF)
    F = fx.forward(_S, _RD, _RF, _T)
    fit = fx.calibrate_sabr(F, _T, [p.strike for p in pts], [p.vol for p in pts])
    ks = np.linspace(pts[0].strike * 0.97, pts[-1].strike * 1.03, 40)
    prm = ratesim.calibrate(_sofr())
    sim = ratesim.simulate(prm, n_paths=300, threshold=0.05)
    hpv = ratesim.horizon_pv_distribution(prm, sim, kind="bond", bond=_BOND, curve=curve)
    spots, rates = _carry_inputs()
    images = [
        fc.curve_chart(rep), fc.curve_history_chart(panel), fc.pca_chart(curves.curve_pca(panel)),
        fc.krd_chart(ba.krd, "Bond KRD"),
        fc.scenario_chart(bonds.scenario_pnl(_BOND, curve, ba.price)),
        fc.price_yield_chart(_BOND, ba.ytm),
        fc.smile_chart(ks, fx.smile_curve(fit, F, _T, ks), pts, F),
        fc.payoff_chart(_ppn()), fc.rate_fan_chart(sim), fc.horizon_pv_hist(hpv),
        fc.fx_spot_chart(spots["EURUSD"], ((0.25, 1.105), (1.0, 1.12))),
        fc.carry_equity_chart(fx.carry_backtest(spots, rates)),
        fc.carry_bar_chart(fx.carry_table(spots, rates)),
        fc.macro_z_chart(_sheet()),
        fc.caplet_chart(swaps.price_cap_floor(curve, 5.0, None, vol=0.008)),
    ]
    assert len(images) == 15
    for img in images:
        assert img.src.startswith("data:image/png;base64,"), "chart must inline its PNG"
        assert len(img.src) > 1000, "suspiciously empty chart"



# --------------------------------------------------------------------------- #
# Regressions from the adversarial review
# --------------------------------------------------------------------------- #
def test_bond_carry_roll_is_a_holding_period_pnl():
    """Roll-down must not smuggle coupon accrual: on a flat curve a par bond has
    ~zero roll and ~zero breakeven, and on any curve the breakeven yield move
    actually reproduces the horizon P&L through the price/yield function."""
    from core.ficc import bonds, curves
    from core.ficc.common import BP
    flat = curves.flat_curve(0.045)
    b = bonds.Bond(coupon=0.045, maturity=10.0)
    px = bonds.price_from_curve(b, flat)
    cr = bonds.carry_roll(b, flat, px)
    assert abs(cr.rolldown) < 0.05, f"flat-curve roll-down {cr.rolldown} is accrual leaking in"
    assert abs(cr.breakeven_bp) < 2.0, f"flat-curve breakeven {cr.breakeven_bp}bp"
    # Sloped synthetic curve: the breakeven move wipes out carry+roll (to first order).
    from core.ficc.data import synthetic_curve_panel
    curve = curves.curve_from_snapshot(synthetic_curve_panel(days=60).latest())
    a = bonds.analyze_bond(b, ytm=0.045, curve=curve)
    cr = a.carry_roll
    shocked = bonds.price_from_yield(b, a.ytm + cr.breakeven_bp * BP)
    assert abs((a.price - shocked) - cr.total) < 0.05 + abs(cr.total) * 0.05,         f"breakeven {cr.breakeven_bp}bp does not reproduce total {cr.total}"
    assert abs(cr.breakeven_bp) < 200, "a 3m breakeven in the hundreds of bp is a unit bug"


def test_weekly_strategy_names_a_positive_carry_long():
    """The carry line must be a carry trade: whenever some currency earns positive
    carry the named long has positive carry, whatever the momentum score says."""
    from core.ficc import data, fx, macro, insights
    sheet = macro.macro_sheet(source="synthetic")
    spots = {p: data.synthetic_fx(p) for p in ("EURUSD", "USDJPY", "GBPUSD", "AUDUSD",
                                                "USDCAD", "USDCHF", "USDKRW")}
    rates = {c: data.synthetic_series(f"RATE_{c}", kind="rate") for c in data.G10_KRW}
    rows = fx.carry_table(spots, rates)
    text = insights.narrate_weekly_strategy(sheet, carry_rows=rows)
    assert "Carry:" in text
    positive = [r for r in rows if r.carry > 0]
    if positive:
        best = max(positive, key=lambda r: r.carry_to_vol)
        assert f"long {best.ccy}" in text, text[text.index("Carry:"):][:200]
    else:
        assert "no currency in the basket earns positive carry" in text

def tests():
    return [(name, fn) for name, fn in sorted(globals().items())
            if name.startswith("test_") and callable(fn)]


if __name__ == "__main__":
    import sys
    import time
    import traceback
    failed = 0
    for name, fn in tests():
        t0 = time.perf_counter()
        try:
            fn()
            print(f"PASS {name} ({time.perf_counter() - t0:.2f}s)")
        except Exception:
            failed += 1
            print(f"FAIL {name}")
            traceback.print_exc()
    print(f"{len(tests()) - failed}/{len(tests())} passed")
    sys.exit(1 if failed else 0)
