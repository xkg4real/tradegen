"""Acceptance checks for the QUANTGEN quant core.

Hermetic by construction: every check runs on synthetic series and patches the
credential readers to a known state before touching anything that could reach
a network. A test suite that silently spends an FMP quota — or silently calls
the Claude API because the operator's shell happened to export a key — is a
test suite nobody runs twice.

Grouped the way the core is grouped: history, Monte Carlo, risk, optimizer,
signals, backtest, insights, gs_quant, charts.
"""
from __future__ import annotations

import contextlib
import math
from datetime import datetime, timezone

import numpy as np

import config
from core.quant import gsq, insights
from core.quant.backtest import run_backtest
from core.quant.history import (History, HistoryError, load_history,
                                synthetic_history)
from core.quant.garch import (BOUNDS, LR_5PCT, NU_NORMAL, STATIONARITY_MAX, Z95, Z_BOUND, bounded_t_stats,
                              fit_garch, forecast_variance, horizon_vol,
                              simulate_garch_series)
from core.quant.montecarlo import MODELS, run_monte_carlo
from core.quant.optimize import efficient_frontier, optimize_portfolio
from core.quant.risk import align_histories, analyze_history
from core.quant.signals import compute_signals, rsi


@contextlib.contextmanager
def _no_credentials():
    """Force every provider to 'absent' for the duration, whatever the shell
    environment says."""
    # fmp_key is patched too: `fmp_history` reads the key, not the readiness
    # flag, so with a real key in .env the "explicit provider must raise" check
    # would otherwise reach FMP, succeed, and spend quota to fail the test.
    saved = (config.fmp_ready, config.fmp_key, config.kis_ready, config.anthropic_key)
    config.fmp_ready = lambda: False
    config.fmp_key = lambda: ""
    config.kis_ready = lambda: False
    config.anthropic_key = lambda: ""
    try:
        yield
    finally:
        (config.fmp_ready, config.fmp_key, config.kis_ready,
         config.anthropic_key) = saved


def _trend_history(slope: float, *, days: int = 300, noise: float = 0.001,
                   seed: int = 3) -> History:
    rng = np.random.default_rng(seed)
    log_px = math.log(100) + np.cumsum(slope + rng.normal(0, noise, days))
    closes = tuple(float(x) for x in np.exp(log_px))
    dates = tuple(f"2025-{(i // 28) % 12 + 1:02d}-{i % 28 + 1:02d}" for i in range(days))
    return History(symbol="TREND", source="SYNTHETIC", dates=dates, closes=closes)


# --------------------------------------------------------------------------- #
# History
# --------------------------------------------------------------------------- #
def test_synthetic_is_deterministic_per_symbol():
    a1, a2 = synthetic_history("AAPL"), synthetic_history("AAPL")
    b = synthetic_history("MSFT")
    assert a1.closes == a2.closes, "same symbol must reproduce the same series"
    assert a1.closes != b.closes, "different symbols must differ"
    assert a1.source == "SYNTHETIC" and a1.note, "synthetic must label itself"


def test_load_history_rejects_blank_and_unknown_source():
    for bad_call in (lambda: load_history(""),
                     lambda: load_history("AAPL", source="bloomberg")):
        try:
            bad_call()
        except HistoryError:
            continue
        raise AssertionError("expected HistoryError")


def test_auto_routing_falls_back_to_labeled_synthetic():
    with _no_credentials():
        us = load_history("AAPL", source="auto")
        kr = load_history("005930", source="auto")
    assert us.source == "SYNTHETIC" and "FMP_API_KEY" in us.note
    assert kr.source == "SYNTHETIC" and "KIS" in kr.note


def test_explicit_provider_without_key_raises_not_simulates():
    with _no_credentials():
        try:
            load_history("AAPL", source="fmp")
        except HistoryError:
            return
    raise AssertionError("explicit fmp source without a key must raise")


def test_history_cache_serves_a_rerun_without_asking_the_provider_again():
    import os
    import tempfile
    import core.quant.history as H
    calls = []

    def fake_fmp(symbol, *, days=504):
        calls.append((symbol, days))
        h = synthetic_history(symbol, days=days)
        return History(h.symbol, "FMP", h.dates, h.closes, note="fake provider",
                       adjustment="total")

    saved = (H.fmp_history, config.fmp_ready, config.fmp_key,
             config.FICC_CACHE_TTL_SECONDS, os.environ.get("NEXTGEN_FICC_CACHE"),
             H._may_be_trading, H._CACHE_LIVE_TTL)
    H.fmp_history = fake_fmp
    real_may_be_trading = H._may_be_trading
    H._may_be_trading = lambda *a: False                    # market closed: bars are final
    config.fmp_ready = lambda: True
    config.fmp_key = lambda: "k"
    config.FICC_CACHE_TTL_SECONDS = 3600.0
    os.environ["NEXTGEN_FICC_CACHE"] = tempfile.mkdtemp()
    try:
        first = load_history("AAPL", days=120)
        again = load_history("AAPL", days=120)
        assert calls == [("AAPL", 120)], "the rerun must be served from disk"
        assert (again.dates, again.closes, again.source) == (first.dates, first.closes, "FMP")
        assert again.adjustment == "total", "the return convention must survive the round trip"
        assert "cached" in again.note and "cached" not in first.note, "a cache hit must say so"
        load_history("AAPL", days=60)
        assert len(calls) == 2, "a different window is a different series"
        config.FICC_CACHE_TTL_SECONDS = 0.0
        load_history("AAPL", days=120)
        assert len(calls) == 3, "a TTL of 0 switches the cache off"
        # Fetched while the market may be trading, the last bar is a running
        # price: such a series is kept for the short live window only.
        config.FICC_CACHE_TTL_SECONDS = 3600.0
        H._may_be_trading = lambda *a: True
        H._CACHE_LIVE_TTL = 0.0
        load_history("MSFT", days=120)
        load_history("MSFT", days=120)
        assert calls.count(("MSFT", 120)) == 2, "a mid-session series must not be kept for hours"
        H._CACHE_LIVE_TTL = 600.0
        load_history("NVDA", days=120)
        load_history("NVDA", days=120)
        assert calls.count(("NVDA", 120)) == 1, "inside the live window a rerun is still served from disk"
        # A file with no `live` flag (written before the flag existed) is not
        # trusted as final, and neither is one whose market has traded since.
        import json as _json
        import time as _time
        from pathlib import Path
        H._may_be_trading = lambda *a: False
        cache = Path(os.environ["NEXTGEN_FICC_CACHE"])
        load_history("TSLA", days=120)
        path = cache / "HIST_FMP_TSLA_120.json"
        stored = _json.loads(path.read_text("utf-8"))
        assert stored["live"] is False and stored["adjustment"] == "total"
        stored["ts"] = _time.time() - 900                    # fifteen minutes old
        legacy = {k: v for k, v in stored.items() if k != "live"}
        path.write_text(_json.dumps(legacy), "utf-8")
        load_history("TSLA", days=120)
        assert calls.count(("TSLA", 120)) == 2, "an unflagged file older than the live window is refetched"
        stored["ts"] = _time.time() - 900
        path.write_text(_json.dumps(stored), "utf-8")
        load_history("TSLA", days=120)
        assert calls.count(("TSLA", 120)) == 2, "a final file is served"
        # ...until its market trades again: sampled between the write and now.
        H._may_be_trading = lambda provider, symbol, at=None: at is not None and \
            (datetime.now(timezone.utc) - at).total_seconds() < 600
        load_history("TSLA", days=120)
        assert calls.count(("TSLA", 120)) == 3, "a session since the write makes the file a bar short"
        H._may_be_trading = lambda *a: False
        # Without a key the provider is asked directly and must raise, even
        # though a perfectly good cached file for this symbol is on disk.
        config.FICC_CACHE_TTL_SECONDS = 3600.0
        config.fmp_key = lambda: ""
        H.fmp_history = saved[0]
        try:
            load_history("AAPL", source="fmp", days=120)
        except HistoryError:
            pass
        else:
            raise AssertionError("a cached file must not stand in for a missing key")
    finally:
        (H.fmp_history, config.fmp_ready, config.fmp_key,
         config.FICC_CACHE_TTL_SECONDS) = saved[:4]
        H._may_be_trading, H._CACHE_LIVE_TTL = saved[5:]
        assert H._may_be_trading is real_may_be_trading
        if saved[4] is None:
            os.environ.pop("NEXTGEN_FICC_CACHE", None)
        else:
            os.environ["NEXTGEN_FICC_CACHE"] = saved[4]


def test_fmp_history_asks_for_dividend_adjusted_closes_and_reports_refusals_honestly():
    import core.quant.history as H

    class _Resp:
        def __init__(self, payload, status=200):
            self._payload, self.status_code = payload, status

        def json(self):
            return self._payload

    class _HTTP:
        def __init__(self, resp):
            self.resp, self.urls = resp, []

        def get(self, url, **kwargs):
            self.urls.append(url)
            return self.resp

    rows = [{"date": f"2026-{1 + i // 28:02d}-{1 + i % 28:02d}", "adjClose": 100.0 + i}
            for i in range(40)]
    saved = (H._requests, config.fmp_key)
    config.fmp_key = lambda: "SECRETKEY"
    try:
        H._requests = http = _HTTP(_Resp(rows))
        h = H.fmp_history("KO", days=30)
        assert http.urls[0].endswith("/historical-price-eod/dividend-adjusted")
        assert len(h) == 30 and h.last == 139.0
        assert "dividends" in h.note and "NOT" not in h.note and h.adjustment == "total"
        # One row without adjClose must not splice a raw close into the series.
        mixed = [dict(r) for r in rows]
        mixed[-1] = {"date": rows[-1]["date"], "close": 999.0}
        H._requests = _HTTP(_Resp(mixed))
        m = H.fmp_history("KO", days=30)
        assert 999.0 not in m.closes and m.adjustment == "total"
        assert "1 session(s) without adjClose dropped" in m.note, "a dropped row must be reported"
        # A response without adjClose is price-only, and must say so.
        H._requests = _HTTP(_Resp([{"date": r["date"], "close": r["adjClose"]} for r in rows]))
        price_only = H.fmp_history("KO", days=30)
        assert "NOT dividend-adjusted" in price_only.note and price_only.adjustment == "split"
        # A quota refusal is a JSON object: report it, and never echo the key.
        H._requests = _HTTP(_Resp({"Error Message": "Limit Reach. apikey=SECRETKEY"}))
        try:
            H.fmp_history("KO")
        except HistoryError as exc:
            assert "Limit Reach" in str(exc) and "SECRETKEY" not in str(exc)
        else:
            raise AssertionError("a refusal must not be reported as 'no history'")
        H._requests = _HTTP(_Resp([], status=429))
        try:
            H.fmp_history("KO")
        except HistoryError as exc:
            assert "rate limit" in str(exc)
        else:
            raise AssertionError("HTTP 429 must raise")
    finally:
        H._requests, config.fmp_key = saved


def test_the_cache_knows_when_a_market_may_be_trading():
    from core.quant.history import _may_be_trading
    utc = timezone.utc
    krx_session = datetime(2026, 8, 19, 2, 0, tzinfo=utc)          # 11:00 KST Wednesday
    krx_evening = datetime(2026, 8, 19, 11, 0, tzinfo=utc)         # 20:00 KST
    just_after_close = datetime(2026, 8, 19, 6, 45, tzinfo=utc)    # 15:45 KST: closing print may lag
    assert _may_be_trading("KIS", "005930", krx_session)
    assert _may_be_trading("YFINANCE", "005930.KS", krx_session)
    assert not _may_be_trading("KIS", "005930", krx_evening)
    assert _may_be_trading("KIS", "005930", just_after_close), "an hour's margin after the bell"
    # KRX futures and the FX fixing keep other hours: no calendar, so any weekday counts.
    assert _may_be_trading("KIS", "A01612", krx_evening) and _may_be_trading("KIS", "FX@KRW", krx_evening)
    us_session = datetime(2026, 8, 19, 15, 0, tzinfo=utc)          # 11:00 ET
    thanksgiving = datetime(2026, 11, 26, 16, 0, tzinfo=utc)
    assert _may_be_trading("FMP", "AAPL", us_session) and _may_be_trading("KIS", "NAS:AAPL", us_session)
    assert not _may_be_trading("FMP", "AAPL", krx_session)         # 22:00 ET
    assert not _may_be_trading("FMP", "AAPL", thanksgiving), "a market holiday is a closed market"
    saturday = datetime(2026, 8, 22, 12, 0, tzinfo=utc)
    assert _may_be_trading("CRYPTO", "KRW-BTC", saturday) and _may_be_trading("YFINANCE", "BTC-USD", saturday)
    assert not _may_be_trading("YFINANCE", "^VIX", saturday)
    assert _may_be_trading("YFINANCE", "ZN=F", datetime(2026, 8, 23, 23, 0, tzinfo=utc)), "Sunday evening UTC"


def test_each_loader_states_its_return_convention():
    import core.ficc.data as ficc
    import core.quant.history as H
    import data.krx.kis_client as kis
    from core.quant.history import convention_warning
    rows = [(f"2026-{1 + i // 28:02d}-{1 + i % 28:02d}", 100.0 + i) for i in range(40)]

    class _FakeKIS:
        def daily(self, code, **kwargs):
            return [{"date": d, "close": c} for d, c in rows] if kwargs.get("end") is None else []

    saved = (ficc._yf_fetch, kis.KISClient, config.kis_ready)
    ficc._yf_fetch = lambda tickers, period: {tickers[0]: list(rows)}
    kis.KISClient = _FakeKIS
    config.kis_ready = lambda: True
    try:
        krx = H.kis_history("005930", days=30)
        yahoo = H.yf_history("005930.KS", days=30)
        index = H.yf_history("^VIX", days=30)
        assert (krx.adjustment, yahoo.adjustment, index.adjustment) == ("split", "total", "")
        assert convention_warning([krx, yahoo]) and not convention_warning([krx, index])
    finally:
        ficc._yf_fetch, kis.KISClient, config.kis_ready = saved


def test_a_panel_mixing_total_and_price_return_series_is_called_out():
    from core.quant.history import convention_warning
    day = ("2026-01-02",)
    total = History("VZ", "FMP", day, (1.0,), adjustment="total")
    price = History("055550", "KIS", day, (1.0,), adjustment="split")
    index = History("^VIX", "YFINANCE", day, (1.0,))
    assert convention_warning([total, index]) == "" and convention_warning([price, index]) == ""
    text = convention_warning([total, price, index])
    assert "VZ" in text and "055550" in text and "^VIX" not in text


# --------------------------------------------------------------------------- #
# Monte Carlo
# --------------------------------------------------------------------------- #
def test_mc_is_seeded_and_reproducible():
    h = synthetic_history("AAPL")
    a = run_monte_carlo(h, n_paths=1000, horizon_days=60, seed=7)
    b = run_monte_carlo(h, n_paths=1000, horizon_days=60, seed=7)
    c = run_monte_carlo(h, n_paths=1000, horizon_days=60, seed=8)
    assert a.median_terminal == b.median_terminal
    assert a.median_terminal != c.median_terminal


def test_mc_fan_percentiles_are_ordered():
    h = synthetic_history("NVDA")
    mc = run_monte_carlo(h, n_paths=2000, horizon_days=40)
    for t in (1, 20, 40):
        assert (mc.fan[5][t] <= mc.fan[25][t] <= mc.fan[50][t]
                <= mc.fan[75][t] <= mc.fan[95][t])
    assert all(abs(mc.fan[p][0] - mc.spot) < 1e-9 for p in mc.fan), \
        "every percentile starts at spot"


def test_mc_var_and_cvar_are_coherent():
    h = synthetic_history("TSLA")
    mc = run_monte_carlo(h, n_paths=3000, horizon_days=60)
    assert 0.0 <= mc.var_pct <= 1.0
    assert mc.cvar_pct >= mc.var_pct, "expected shortfall is at least VaR"


def test_mc_target_probability_brackets():
    h = synthetic_history("AAPL")
    lo = run_monte_carlo(h, n_paths=2000, horizon_days=60, target=h.last * 0.4)
    hi = run_monte_carlo(h, n_paths=2000, horizon_days=60, target=h.last * 3.0)
    assert lo.prob_target > 0.95, "a target far below p05 is nearly certain"
    assert hi.prob_target < 0.05, "a target far above p95 is nearly impossible"


def test_mc_jump_degrades_to_gbm_without_outliers():
    # Tiny uniform noise has no >3σ outliers... construct near-constant returns.
    h = _trend_history(0.0005, noise=0.0008)
    mc = run_monte_carlo(h, model="jump", n_paths=500, horizon_days=20)
    # Either it found no jumps (degrade note) or it calibrated some; the
    # invariant is that the note always says which happened.
    assert mc.jump_note, "jump model must state its calibration"


def test_mc_all_models_run():
    h = synthetic_history("MSFT")
    assert MODELS == ("garch_t", "gbm", "jump", "bootstrap")
    for model in MODELS:
        mc = run_monte_carlo(h, model=model, n_paths=400, horizon_days=30)
        assert mc.terminal.size == 400
        assert (mc.garch is not None) == (model == "garch_t")


# --------------------------------------------------------------------------- #
# Risk
# --------------------------------------------------------------------------- #
def test_risk_vol_and_drawdown_match_numpy_whatever_engine():
    h = synthetic_history("AAPL")
    rep = analyze_history(h)
    r = h.log_returns()
    vol = float(np.std(r, ddof=1)) * math.sqrt(252)
    px = h.prices()
    mdd = float(np.min(px / np.maximum.accumulate(px) - 1.0))
    assert abs(rep.ann_vol - vol) < 1e-6, f"{rep.engine} vol disagrees with numpy"
    assert abs(rep.max_drawdown - mdd) < 1e-6
    assert rep.engine in ("gs_quant", "local")


def test_risk_var_cvar_bounds():
    rep = analyze_history(synthetic_history("NVDA"))
    assert 0.0 <= rep.var_1d <= abs(rep.worst_day) + 1e-9
    assert rep.cvar_1d >= rep.var_1d
    assert 0.0 <= rep.positive_days <= 1.0


def test_align_histories_requires_overlap():
    a = synthetic_history("AAPL", days=40)
    b = History("X", "SYNTHETIC", tuple(f"1999-01-{i + 1:02d}" for i in range(20)),
                tuple(float(i + 1) for i in range(20)))
    try:
        align_histories([a, b])
    except ValueError:
        return
    raise AssertionError("disjoint histories must raise")


# --------------------------------------------------------------------------- #
# Optimizer
# --------------------------------------------------------------------------- #
def _basket():
    return align_histories([synthetic_history(s)
                            for s in ("AAPL", "MSFT", "NVDA", "TLT")])


def test_optimizer_weights_are_a_long_only_allocation():
    stats = _basket()
    for objective in ("max_sharpe", "min_vol", "risk_parity", "equal_weight"):
        p = optimize_portfolio(stats, objective=objective)
        assert abs(float(np.sum(p.weights)) - 1.0) < 1e-6, objective
        assert float(np.min(p.weights)) >= -1e-9, objective


def test_optimizer_objectives_actually_optimize():
    stats = _basket()
    eq = optimize_portfolio(stats, objective="equal_weight")
    ms = optimize_portfolio(stats, objective="max_sharpe")
    mv = optimize_portfolio(stats, objective="min_vol")
    assert ms.sharpe >= eq.sharpe - 1e-9, "max_sharpe must not lose to 1/N"
    assert mv.ann_vol <= eq.ann_vol + 1e-9, "min_vol must not exceed 1/N vol"


def test_risk_parity_equalizes_risk_contributions():
    p = optimize_portfolio(_basket(), objective="risk_parity")
    rc = np.asarray(p.risk_contrib)
    assert float(np.max(np.abs(rc - 0.25))) < 0.02, rc


def test_max_weight_cap_is_respected():
    p = optimize_portfolio(_basket(), objective="max_sharpe", max_weight=0.4)
    assert float(np.max(p.weights)) <= 0.4 + 1e-6


def test_frontier_is_traced_and_cloud_is_dominated():
    stats = _basket()
    fr = efficient_frontier(stats, points=12, n_cloud=400)
    assert fr.vols.size >= 6, "frontier tracing failed on most targets"
    assert fr.cloud_vols.size == 400
    # The frontier at min vol must not sit above (worse than) every random
    # portfolio: its min vol should be <= the cloud's min vol + tolerance.
    assert float(np.min(fr.vols)) <= float(np.min(fr.cloud_vols)) + 1e-3


# --------------------------------------------------------------------------- #
# Signals
# --------------------------------------------------------------------------- #
def test_signals_read_the_trend_direction():
    up = compute_signals(_trend_history(+0.002))
    down = compute_signals(_trend_history(-0.002))
    assert up.composite > 0, f"uptrend read as {up.composite}"
    assert down.composite < 0, f"downtrend read as {down.composite}"


def test_signal_scores_and_weights_are_bounded():
    rep = compute_signals(synthetic_history("AAPL"))
    assert -100.0 <= rep.composite <= 100.0
    for c in rep.components:
        assert -100.0 <= c.score <= 100.0, c.key
        assert c.reason, c.key
    assert abs(sum(c.weight for c in rep.components) - 1.0) < 0.25, \
        "weights should roughly form a whole"


def test_rsi_stays_in_bounds():
    px = synthetic_history("TSLA").prices()
    assert 0.0 <= rsi(px) <= 100.0
    assert rsi(np.linspace(1, 2, 50)) == 100.0, "pure uptrend has no losses"


# --------------------------------------------------------------------------- #
# Backtest
# --------------------------------------------------------------------------- #
def test_backtest_costs_only_hurt():
    h = synthetic_history("AAPL")
    free = run_backtest(h, strategy="ma_cross", cost_bps=0.0)
    paid = run_backtest(h, strategy="ma_cross", cost_bps=100.0)
    assert paid.total_return <= free.total_return + 1e-12
    assert free.n_trades == paid.n_trades, "costs must not change the signals"


def test_backtest_has_no_lookahead():
    # A strategy long from bar k earns returns from bar k+1 onward. On a
    # strictly rising series, always-long-from-day-1 momentum(lookback=1) must
    # match buy-and-hold from bar 1 (it cannot capture bar 0→1, decided at 1).
    days = 100
    closes = tuple(100.0 * (1.01 ** i) for i in range(days))
    dates = tuple(f"2025-01-{i % 28 + 1:02d}" for i in range(days))
    h = History("UP", "SYNTHETIC", dates, closes)
    bt = run_backtest(h, strategy="momentum", params={"lookback": 1}, cost_bps=0.0)
    expected = closes[-1] / closes[1] - 1.0
    assert abs(bt.total_return - expected) < 1e-9, \
        f"{bt.total_return} vs {expected} — a mismatch here is lookahead"


def test_backtest_rejects_inverted_ma_params():
    try:
        run_backtest(synthetic_history("AAPL"), strategy="ma_cross",
                     params={"fast": 50, "slow": 20})
    except ValueError:
        return
    raise AssertionError("fast >= slow must raise")


def test_backtest_exposure_and_drawdown_sane():
    bt = run_backtest(synthetic_history("MSFT"), strategy="rsi_revert")
    assert 0.0 <= bt.exposure <= 1.0
    assert bt.max_drawdown <= 0.0


# --------------------------------------------------------------------------- #
# Insights
# --------------------------------------------------------------------------- #
def test_narratives_state_their_numbers():
    h = synthetic_history("AAPL")
    mc = run_monte_carlo(h, n_paths=500, horizon_days=30)
    text = insights.narrate_monte_carlo(mc)
    assert f"{mc.n_paths:,}" in text and str(mc.horizon_days) in text
    rep = analyze_history(h)
    assert f"{rep.sharpe:.2f}" in insights.narrate_risk(rep)
    bt = run_backtest(h)
    assert bt.strategy in insights.narrate_backtest(bt)


def test_deep_analysis_without_key_degrades_without_network():
    with _no_credentials():
        result = insights.deep_analysis("test", {"x": 1})
    assert result.text == "" and "ANTHROPIC_API_KEY" in result.error


# --------------------------------------------------------------------------- #
# gs_quant
# --------------------------------------------------------------------------- #
def test_gsq_status_is_coherent():
    st = gsq.status()
    assert st.installed in (True, False)
    if st.installed:
        assert st.offline_analytics, "installed gs_quant must serve offline analytics"
    assert st.detail, "status must always explain itself"


def test_gsq_pricing_without_session_explains_itself():
    out = gsq.price_example_swap()
    if not out["ok"]:
        assert out["detail"]


# --------------------------------------------------------------------------- #
# Charts
# --------------------------------------------------------------------------- #
def test_every_chart_renders_a_data_uri_image():
    import ui.qcharts as qcharts
    from core.theme import set_mode
    set_mode("dark")
    h = synthetic_history("AAPL")
    mc = run_monte_carlo(h, n_paths=300, horizon_days=20)
    bt = run_backtest(h)
    stats = _basket()
    fr = efficient_frontier(stats, points=6, n_cloud=100)
    ports = [optimize_portfolio(stats, objective="max_sharpe")]
    images = [
        qcharts.price_chart(h),
        qcharts.fan_chart(h, mc),
        qcharts.terminal_histogram(mc),
        qcharts.equity_chart(bt),
        qcharts.frontier_chart(fr, ports),
        qcharts.corr_heatmap(stats.corr, stats.symbols),
        qcharts.cond_vol_chart(h, mc.garch),
    ]
    for img in images:
        assert img.src.startswith("data:image/png;base64,"), "chart must inline its PNG"
        assert len(img.src) > 1000, "suspiciously empty chart"


# --------------------------------------------------------------------------- #
# GARCH(1,1)-t
# --------------------------------------------------------------------------- #
_TRUE = dict(omega=2e-6, alpha=0.08, beta=0.90, nu=6.0)


def _garch_history(*, n: int = 1500, seed: int = 11, drift: float = 0.0) -> History:
    """Price history whose returns are a synthetic GARCH(1,1)-t series."""
    from datetime import date, timedelta
    r = simulate_garch_series(_TRUE["omega"], _TRUE["alpha"], _TRUE["beta"],
                              _TRUE["nu"], n=n, seed=seed) + drift
    closes = tuple(float(x) for x in 100.0 * np.exp(np.concatenate([[0.0], np.cumsum(r)])))
    d0 = date(2020, 1, 1)
    dates = tuple((d0 + timedelta(days=i)).isoformat() for i in range(len(closes)))
    return History(symbol="GARCH", source="SYNTHETIC", dates=dates, closes=closes)


def test_garch_recovers_parameters_on_simulated_series():
    r = simulate_garch_series(_TRUE["omega"], _TRUE["alpha"], _TRUE["beta"],
                              _TRUE["nu"], n=3000, seed=1)
    fit = fit_garch(r, dist="t")
    assert fit.dist == "t" and fit.n_obs == 3000
    assert abs(fit.alpha - 0.08) < 0.05, fit.alpha
    assert abs(fit.beta - 0.90) < 0.06, fit.beta
    assert 4.0 < fit.nu < 10.0, fit.nu
    assert fit.converged, fit.note
    assert abs(fit.persistence - (fit.alpha + fit.beta)) < 1e-12
    assert 0.0 < fit.half_life < math.inf
    assert abs(fit.half_life - math.log(0.5) / math.log(fit.persistence)) < 1e-9
    assert fit.cond_vol.shape == (3000,) and float(np.min(fit.cond_vol)) > 0.0
    assert fit.kurtosis_excess > 0.0
    # B2: the fit carries its precision, and on 3,000 sessions every 95% interval
    # holds the truth; the half-life interval is the persistence one mapped through.
    assert set(fit.se) == {"omega", "alpha", "beta", "eta", "persistence"}, fit.se_note
    for name, truth in (("omega", _TRUE["omega"]), ("alpha", _TRUE["alpha"]),
                        ("beta", _TRUE["beta"]), ("persistence", _TRUE["alpha"] + _TRUE["beta"])):
        lo, hi = fit.interval(name)
        assert lo <= truth <= hi, (name, lo, hi)
        assert hi - lo < 0.1 or name == "omega", (name, hi - lo)
    # The prototype's independently computed standard errors (bulletin B.4, row 1):
    # two-sided, so a wrong scale (the omega mapping) or a changed difference step fails.
    for name, ref in (("omega", 5.7e-7), ("alpha", 0.0102), ("beta", 0.0117),
                      ("eta", 0.0175), ("persistence", 0.0065)):
        assert abs(fit.se[name] / ref - 1.0) < 0.15, (name, fit.se[name], ref)
    lo, hi = fit.eta_interval
    assert lo <= 1.0 / _TRUE["nu"] <= hi and 0.0 < lo < hi < 0.4, fit.eta_interval
    assert fit.nu_interval == (1.0 / hi, 1.0 / lo)
    hl_lo, hl_hi = fit.half_life_interval
    true_hl = math.log(0.5) / math.log(_TRUE["alpha"] + _TRUE["beta"])
    assert hl_lo <= true_hl <= hl_hi and hl_lo < fit.half_life < hl_hi
    assert "nu" not in fit.interval_at_bound and fit.se_note == ""
    assert fit_garch(r, dist="t", profile=False).eta_interval is None


def test_garch_scaled_t_shocks_have_unit_variance():
    # alpha = beta = 0 makes sigma^2 == omega, so var(r)/omega is the variance
    # of the scaled innovation. It must be 1, and it must still be a t.
    omega = 1e-4
    for dist, kurt_lo, kurt_hi in (("t", 1.0, math.inf), ("normal", -0.3, 0.3)):
        r = simulate_garch_series(omega, 0.0, 0.0, 6.0, n=100_000, seed=3, dist=dist)
        var_ratio = float(np.var(r)) / omega
        assert abs(var_ratio - 1.0) < 0.03, (dist, var_ratio)
        z = (r - r.mean()) / r.std()
        kurt = float(np.mean(z**4)) - 3.0
        assert kurt_lo < kurt < kurt_hi, (dist, kurt)


def test_garch_respects_bounds_and_flags_on_gbm_series():
    r = synthetic_history("AAPL").log_returns()           # iid lognormal: no clustering
    fit = fit_garch(r)
    for name in ("omega", "alpha", "beta", "nu"):
        lo, hi = BOUNDS[name]
        assert lo <= getattr(fit, name) <= hi, (name, getattr(fit, name))
    assert fit.persistence <= STATIONARITY_MAX + 1e-9
    assert isinstance(fit.at_bound, tuple)
    assert all(n in (*BOUNDS, "stationarity") for n in fit.at_bound), fit.at_bound
    assert fit.note, "fit must always describe itself"
    # The t contains the normal (eta = 1/nu can reach 0): on a series with no
    # heavier tail the fit says so instead of hitting a cap, and LR cannot be negative.
    assert fit.effectively_normal and fit.innovation == "normal", fit.note
    assert fit.lr_t_vs_normal >= 0.0, fit.lr_t_vs_normal
    assert "normal innovations" in fit.note and "nu" not in fit.at_bound, fit.note
    assert abs(fit.mean_daily - float(np.mean(r))) < 1e-15, "mu is the sample mean, fixed"
    # B2: the profile interval reaches the normal exactly when the LR tile says the
    # t did not beat it, and a fit either has standard errors or says why not.
    assert fit.nu_interval is not None and math.isinf(fit.nu_interval[1]), fit.nu_interval
    assert (fit.eta_interval[0] == 0.0) == (fit.lr_t_vs_normal <= LR_5PCT)
    # On iid data the information matrix is singular (alpha at 0 leaves beta
    # unidentified): the documented state is "SE undefined", said in the note.
    assert not fit.se and "not positive definite" in fit.se_note, (fit.se, fit.se_note)
    assert "standard errors undefined" in fit.note, fit.note
    for bad in (lambda: fit_garch(r[:50]), lambda: fit_garch(r, dist="cauchy")):
        try:
            bad()
        except ValueError:
            continue
        raise AssertionError("short sample / unknown dist must raise ValueError")


def test_garch_t_beats_normal_and_gbm_on_clustered_series():
    r = simulate_garch_series(_TRUE["omega"], _TRUE["alpha"], _TRUE["beta"],
                              _TRUE["nu"], n=2000, seed=5)
    fit = fit_garch(r)
    assert fit.loglik >= fit.loglik_normal - 1e-6, (fit.loglik, fit.loglik_normal)
    assert fit.loglik >= fit.loglik_gbm, (fit.loglik, fit.loglik_gbm)
    assert abs(fit.lr_t_vs_normal - 2.0 * (fit.loglik - fit.loglik_normal)) < 1e-6
    assert fit.lr_t_vs_normal > LR_5PCT, "t tails must be significant on a t series"
    assert fit.delta_aic_vs_gbm > 0.0, "GARCH must be preferred to GBM on clustered data"
    assert abs(fit.aic - (2 * 4 - 2 * fit.loglik)) < 1e-6
    assert abs(fit.bic - (4 * math.log(fit.n_obs) - 2 * fit.loglik)) < 1e-6
    normal = fit_garch(r, dist="normal")
    assert normal.nu == math.inf and normal.kurtosis_excess == 0.0
    assert abs(normal.aic - (2 * 3 - 2 * normal.loglik)) < 1e-6
    assert normal.eta_interval is None and normal.nu_interval is None
    assert set(normal.se) == {"omega", "alpha", "beta", "persistence"} and normal.se_note == ""


def test_garch_forecast_variance_converges_to_unconditional():
    fit = fit_garch(simulate_garch_series(_TRUE["omega"], _TRUE["alpha"],
                                          _TRUE["beta"], _TRUE["nu"], n=2000, seed=5))
    assert fit.persistence < 1.0
    fv = forecast_variance(fit, 5000)
    assert fv.shape == (5000,) and float(np.min(fv)) > 0.0
    assert abs(fv[0] * 252 - fit.cond_vol_last**2) < 1e-12, "first step is the fit's forecast"
    uncond = fit.omega / (1.0 - fit.persistence)
    assert abs(fv[-1] / uncond - 1.0) < 0.01, (fv[-1], uncond)
    assert abs(fit.uncond_vol - math.sqrt(uncond * 252)) < 1e-9
    hv = horizon_vol(fit, 60)
    lo, hi = sorted((fit.cond_vol_last, fit.uncond_vol))
    assert lo - 1e-9 <= hv <= hi + 1e-9, "horizon vol sits between today and the long run"
    assert np.array_equal(fv, forecast_variance(fit, 5000)), "deterministic"


def test_mc_default_model_is_garch_t_seeded_and_reproducible():
    h = _garch_history()
    a = run_monte_carlo(h, n_paths=800, horizon_days=40, seed=7)
    b = run_monte_carlo(h, n_paths=800, horizon_days=40, seed=7)
    c = run_monte_carlo(h, n_paths=800, horizon_days=40, seed=8)
    assert a.model == "garch_t" and a.garch is not None and a.drift_mode == "premium"
    assert np.array_equal(a.terminal, b.terminal)
    assert not np.array_equal(a.terminal, c.terminal)
    assert a.sigma_annual == a.garch.cond_vol_last
    s = run_monte_carlo(h, n_paths=800, horizon_days=40, seed=7, drift="sample")
    assert abs(s.mu_annual - s.garch.mean_daily * 252) < 1e-12, "sample mode uses the sample mean"
    v_in = bounded_t_stats(a.garch.nu, Z_BOUND)[1]
    assert abs(a.garch_horizon_vol - horizon_vol(a.garch, 40, var_in=v_in)) < 1e-12, \
        "the horizon-vol tile describes the bounded paths the fan is drawn from"
    assert a.cvar_pct >= a.var_pct and a.terminal.size == 800


def test_mc_zero_drift_lowers_median_on_positive_drift_series():
    h = _garch_history(drift=0.002)
    for model in MODELS:
        sample = run_monte_carlo(h, model=model, n_paths=2000, horizon_days=60, seed=7,
                                 drift="sample")
        zero = run_monte_carlo(h, model=model, n_paths=2000, horizon_days=60,
                               seed=7, drift="zero")
        assert sample.drift_mode == "sample" and zero.drift_mode == "zero"
        assert zero.median_terminal < sample.median_terminal, model
        assert zero.mu_annual == 0.0, f"{model}: zero drift reports mu = 0"


# --------------------------------------------------------------------------- #
# Drift modes (docs/drift_study: the sample mean has no forecasting power)
# --------------------------------------------------------------------------- #
def test_drift_modes_are_ordered_and_documented():
    from core.quant.montecarlo import DRIFTS
    assert DRIFTS == ("premium", "zero", "rf", "sample")
    h = synthetic_history("AAPL")
    out = {}
    for model in MODELS:
        for d in DRIFTS:
            out[(model, d)] = run_monte_carlo(h, model=model, drift=d, n_paths=3000,
                                              horizon_days=126, seed=7,
                                              rf_rate=0.04, erp=0.05)
        # Same seed and model: the only difference between modes is the drift,
        # so the medians must rank exactly like the drifts.
        med = {d: out[(model, d)].median_terminal for d in DRIFTS}
        mu = {d: out[(model, d)].mu_annual for d in DRIFTS}
        assert mu["premium"] > mu["rf"], model
        assert med["premium"] > med["rf"], model
        assert med["premium"] > med["zero"] or mu["premium"] <= 0.0, model
    mc = out[("garch_t", "premium")]
    assert mc.rf_rate == 0.04 and mc.erp == 0.05
    assert "rf 4.00%" in mc.drift_note and "ERP 5.00%" in mc.drift_note
    assert out[("gbm", "rf")].erp == 0.0 and out[("gbm", "zero")].rf_rate == 0.0
    text = insights.narrate_monte_carlo(mc)
    assert "risk-premium" in text and "rf 4.00%" in text


def test_drift_zero_centres_the_cone_and_sample_reproduces_the_mean():
    """Zero drift: the median path sits on spot. Sample drift under GBM: the
    median terminal is spot * exp(mu * T) — the old code subtracted half the
    variance from a mean that was already a log drift."""
    h = synthetic_history("MSFT")
    zero = run_monte_carlo(h, model="gbm", drift="zero", n_paths=20000, horizon_days=63, seed=3)
    assert abs(zero.median_terminal / zero.spot - 1.0) < 0.02, zero.median_terminal / zero.spot
    samp = run_monte_carlo(h, model="gbm", drift="sample", n_paths=20000, horizon_days=252, seed=3)
    mu = float(np.mean(h.log_returns())) * 252
    assert abs(samp.median_terminal / samp.spot - math.exp(mu)) < 0.02 * math.exp(mu)


def test_unknown_drift_raises():
    try:
        run_monte_carlo(synthetic_history("AAPL"), drift="bogus", n_paths=200, horizon_days=5)
    except ValueError as exc:
        assert "premium" in str(exc)
        return
    raise AssertionError("an unknown drift mode must raise")


def test_garch_narrative_states_persistence_and_nu():
    mc = run_monte_carlo(_garch_history(), n_paths=500, horizon_days=30)
    g = mc.garch
    text = insights.narrate_monte_carlo(mc)
    def stated(x: float, *decimals: int) -> bool:   # format-agnostic: 2 or 3 dp
        return any(f"{x:.{d}f}" in text for d in decimals)
    assert stated(g.persistence, 2, 3), "persistence must be stated"
    assert stated(g.nu, 1, 2), "nu must be stated"
    assert stated(g.alpha, 2, 3) and stated(g.beta, 2, 3)
    assert any(f"{g.half_life:.{d}f} sessions" in text for d in (0, 1)),         "half-life in sessions must be stated"
    assert ("heavier than normal" in text) == (g.lr_t_vs_normal > LR_5PCT)
    # B2: the precision sentence is there, with the intervals (or the reason for none)
    assert ("95% intervals" in text) == bool(g.se) and ("Standard errors undefined" in text) == (not g.se)
    if g.se:
        lo, hi = g.interval("persistence")
        assert f"persistence {lo:.4f} to {hi:.4f}" in text, text
    assert g.nu_interval is not None and "by profile likelihood" in text
    assert f"nu {g.nu_interval[0]:.1f} to" in text, text
    assert "unconditional vol carries no interval" in text
    zero = insights.narrate_monte_carlo(
        run_monte_carlo(_garch_history(), n_paths=500, horizon_days=30, drift="zero"))
    assert "zero" in zero.lower(), "zero-drift mode must be named"


# --------------------------------------------------------------------------- #
# Bounded innovations and the exact per-step martingale correction
# (docs/ARCHITECTURE_REVIEW.md findings A1 and A2; docs/bounded_innovation_sweep.md)
# --------------------------------------------------------------------------- #
def test_bounded_t_draws_respect_the_bound_and_keep_the_shape():
    """Only draws beyond Z_BOUND are replaced; inside it the law is the fitted t,
    and an unbounded draw with the same seed is identical on every other day."""
    from scipy import stats as _st
    from core.quant.garch import Z_BOUND, _draw_z, _t_scale, bounded_t_stats
    nu, n = 3.1, 400_000
    z = _draw_z(np.random.default_rng(11), nu, "t", n)
    assert float(np.abs(z).max()) <= Z_BOUND
    s = _t_scale(nu)
    for q in (0.01, 0.05, 0.5, 0.95, 0.99):
        want = s * float(_st.t.ppf(q, nu))
        assert abs(float(np.quantile(z, q)) - want) < 0.03 * (1.0 + abs(want)), (q, want)
    mass, var_in = bounded_t_stats(nu, Z_BOUND)
    assert 0.99 < mass < 1.0 and var_in < 1.0, (mass, var_in)
    assert abs(float(np.var(z)) - var_in) < 0.03, (float(np.var(z)), var_in)
    zu = _draw_z(np.random.default_rng(11), nu, "t", n, bound=None)
    inside = np.abs(zu) <= Z_BOUND
    assert np.array_equal(z[inside], zu[inside]), "bounded and unbounded draws differ only beyond the bound"
    assert not inside.all(), "the unbounded t must have produced at least one day beyond the bound"


def test_martingale_correction_matches_quadrature_and_the_normal_closed_form():
    from scipy.integrate import quad
    from core.quant.garch import Z_BOUND, martingale_correction, t_density
    panels = ((-Z_BOUND, -1.0), (-1.0, 1.0), (1.0, Z_BOUND))
    for nu in (2.6, 3.1, 6.0, 30.0):
        den = sum(quad(lambda x: t_density(x, nu), a, b, limit=400)[0] for a, b in panels)
        for sig in (0.005, 0.02, 0.08, 0.3):
            num = sum(quad(lambda x: math.exp(sig * x) * t_density(x, nu), a, b, limit=400)[0]
                      for a, b in panels)
            got = float(martingale_correction(sig, nu, "t")[0])
            assert abs(got - math.log(num / den)) < 1e-7, (nu, sig, got, math.log(num / den))
    assert abs(float(martingale_correction(0.02, 6.0, "normal")[0]) - 0.5 * 0.02 ** 2) < 1e-15
    big = float(martingale_correction(7.0, 6.0, "t")[0])          # beyond the table: direct sum
    assert math.isfinite(big) and big > 0.0
    try:
        martingale_correction(0.02, 6.0, "t", bound=None)
    except ValueError:
        pass
    else:
        raise AssertionError("an unbounded t must refuse to produce a correction")


def test_rate_modes_make_the_discounted_price_a_martingale_for_every_model():
    """rf mode: E[P_T] = spot * exp(rf T) for GBM, jump, bootstrap and GARCH-t
    alike; premium: exp((rf + ERP) T). The series has a conditional vol well
    above its sample vol, which is where the old single-sigma correction failed."""
    from core.quant.garch import Z_BOUND
    from core.quant.history import TRADING_DAYS as TD
    h = _garch_history(n=1000, seed=3, drift=0.0004)
    H, rf, erp = 63, 0.03, 0.04
    for model in MODELS:
        for drift, rate in (("rf", rf), ("premium", rf + erp)):
            mc = run_monte_carlo(h, model=model, n_paths=40_000, horizon_days=H, seed=7,
                                 drift=drift, rf_rate=rf, erp=erp)
            x = mc.terminal / mc.spot
            gap = abs(float(x.mean()) - math.exp(rate * H / TD))
            se = float(x.std(ddof=1)) / math.sqrt(x.size)
            assert gap < 3.0 * se, (model, drift, gap, se)
            assert abs(mc.mu_annual - (rate - mc.correction_annual)) < 1e-12
            assert mc.correction_annual > 0.0
    for model in MODELS:                                     # same seed: the modes differ by ERP only
        a = run_monte_carlo(h, model=model, n_paths=2000, horizon_days=H, seed=7,
                            drift="premium", rf_rate=rf, erp=erp)
        b = run_monte_carlo(h, model=model, n_paths=2000, horizon_days=H, seed=7,
                            drift="rf", rf_rate=rf, erp=erp)
        assert abs((a.mu_annual - b.mu_annual) - erp) < 1e-9, model
        assert abs(a.correction_annual - b.correction_annual) < 1e-12, model
        assert a.median_terminal > b.median_terminal, model
    g = run_monte_carlo(h, model="garch_t", n_paths=500, horizon_days=20, seed=7, drift="rf")
    assert g.z_bound == Z_BOUND and f"bounded at ±{Z_BOUND:g}" in g.drift_note
    assert "convexity correction" in g.drift_note and "pricing measure" in g.drift_note
    z = run_monte_carlo(h, model="garch_t", n_paths=500, horizon_days=20, seed=7, drift="zero")
    assert z.correction_annual == 0.0 and z.mu_annual == 0.0
    for mc in (g, z):                                        # the cap is reported in every drift mode
        assert f"capped at ±{Z_BOUND:g}" in mc.bound_note and "within the horizon" in mc.bound_note
        assert mc.bound_note in insights.narrate_monte_carlo(mc)
    assert run_monte_carlo(h, model="gbm", n_paths=200, horizon_days=5, seed=7).bound_note == ""


def test_lr_is_nonnegative_and_correctly_sized_under_the_null():
    """Step 6 of the B1 fix (docs/B1_FIX_BULLETIN.md): on normal-innovation GARCH
    series the t-vs-normal LR is never negative, about half the fits land exactly
    on the normal (the boundary null puts half its mass at 0), and the false-
    positive rate at LR_5PCT stays within sampling error of its nominal 5%."""
    n = 200
    lrs, at_zero = [], 0
    for seed in range(n):
        r = simulate_garch_series(_TRUE["omega"], _TRUE["alpha"], _TRUE["beta"], _TRUE["nu"],
                                  n=500, seed=1000 + seed, dist="normal")
        fit = fit_garch(r, dist="t", profile=False)      # 200 profiles would add a minute
        lrs.append(fit.lr_t_vs_normal)
        at_zero += math.isinf(fit.nu)
        assert fit.loglik >= fit.loglik_normal - 1e-6, (seed, fit.loglik - fit.loglik_normal)
    lrs = np.array(lrs)
    assert float(lrs.min()) >= 0.0, "LR must be non-negative for nested models"
    size = float(np.mean(lrs > LR_5PCT))
    assert size <= 0.05 + 2.0 * math.sqrt(0.05 * 0.95 / n), f"size {size:.3f} at {LR_5PCT}"
    assert 0.30 <= at_zero / n <= 0.70, f"share at eta = 0: {at_zero / n:.2f}"
    # B2: the profile interval's lower end sits at the normal exactly when
    # LR <= LR_5PCT, and that must hold inside the band (2.706, 3.841] where the
    # boundary cut 1.353 and the interior cut 1.92 disagree, not only far from it.
    band = [s for s, lr in enumerate(lrs) if LR_5PCT < lr <= 3.841][:2]
    below = [s for s, lr in enumerate(lrs) if 1.0 < lr <= LR_5PCT][:2]
    assert band and below, "the null series must put LRs on both sides of 2.706"
    for seed in band + below:
        fit = fit_garch(simulate_garch_series(_TRUE["omega"], _TRUE["alpha"], _TRUE["beta"], _TRUE["nu"],
                                              n=500, seed=1000 + seed, dist="normal"), dist="t")
        lo, hi = fit.eta_interval
        assert (lo == 0.0) == (fit.lr_t_vs_normal <= LR_5PCT), (seed, fit.eta_interval, fit.lr_t_vs_normal)
        assert math.isinf(fit.nu_interval[1]) == (lo == 0.0)
        if fit.lr_t_vs_normal > LR_5PCT:                 # the t beats the normal: the range must not say "normal"
            assert 0.0 < lo < hi and 1.0 / lo > NU_NORMAL / 2, (seed, fit.nu_interval)


def test_interval_coverage_on_simulated_t_garch():
    """Step 6 of the B2 fix (docs/B2_FIX_BULLETIN.md): on 50 correctly specified
    t-GARCH series of 1,000 sessions the 95% Wald intervals of alpha, beta and
    eta, and the profile interval of eta, each hold the truth at least 85% of
    the time, a fit without a covariance counting as a miss. Every fit either
    has standard errors or a reason, and the profile's lower end is at the
    normal exactly when the LR statistic is below its 5% point."""
    n, T = 50, 1000
    eta_true = 1.0 / _TRUE["nu"]
    truth = {"alpha": _TRUE["alpha"], "beta": _TRUE["beta"], "eta": eta_true,
             "persistence": _TRUE["alpha"] + _TRUE["beta"]}
    hits = {k: 0 for k in (*truth, "profile")}
    missing = 0
    for seed in range(n):
        r = simulate_garch_series(_TRUE["omega"], _TRUE["alpha"], _TRUE["beta"], _TRUE["nu"],
                                  n=T, seed=5000 + seed)
        fit = fit_garch(r, dist="t")
        assert bool(fit.se) != bool(fit.se_note), (seed, fit.se_note)
        lo, hi = fit.eta_interval
        assert 0.0 <= lo <= hi <= 0.4, (seed, fit.eta_interval)
        assert (lo == 0.0) == (fit.lr_t_vs_normal <= LR_5PCT), (seed, lo, fit.lr_t_vs_normal)
        hits["profile"] += lo <= eta_true <= hi
        if not fit.se:
            missing += 1
            continue
        for name, val in truth.items():
            est = 1.0 / fit.nu if name == "eta" else getattr(fit, name)   # 1/inf = 0: eta at the normal
            a, b = est - Z95 * fit.se[name], est + Z95 * fit.se[name]
            hits[name] += a <= val <= b
    cover = {k: v / n for k, v in hits.items()}
    assert missing <= 0.1 * n, f"{missing} of {n} fits without standard errors"
    for name in ("alpha", "beta", "eta", "profile", "persistence"):
        assert cover[name] >= 0.85, f"{name} coverage {cover[name]:.2f} (missing {missing})"


def test_intervals_reaching_a_bound_are_flagged():
    """Bulletin B.4, row 3: a t(3) series of 500 sessions fits nu near 2.7 with a
    profile interval that reaches the nu floor 2.5, and a persistence interval
    that reaches 1; both must be named in interval_at_bound (the chips), the
    profile's upper end clamped at 0.4, and the note must say so."""
    f = fit_garch(simulate_garch_series(2e-6, 0.10, 0.80, 3.0, n=500, seed=9))
    assert f.eta_interval[1] == 0.4 and f.nu_interval[0] == 2.5, f.eta_interval
    assert {"nu", "persistence"} <= set(f.interval_at_bound), f.interval_at_bound
    assert f.interval("persistence")[1] >= 1.0 and math.isinf(f.half_life_interval[1])
    assert "persistence interval reaches 1" in f.note and "95% interval reaches a bound" in f.note
    assert "omega" not in f.interval_at_bound            # no tile, so never in the chip


def test_horizon_vol_describes_the_bounded_paths():
    """With a heavy-tailed fit the bounded innovation carries less than unit
    variance, so the simulated variance mean-reverts below the fit's level; the
    horizon-vol tile must follow the paths, not the unbounded formula."""
    from core.quant.garch import simulate_returns
    # A fast-decaying fit (half-life a few sessions): a capped 22-sigma day still
    # multiplies the variance ~50x, but it fades within a week, so the average
    # variance over 40,000 paths is estimable. On a near-integrated fit the same
    # average is carried by a few hundred exploded paths and is not.
    r = simulate_garch_series(2e-6, 0.10, 0.80, 3.0, n=2000, seed=9)
    fit = fit_garch(r, dist="t")
    assert fit.nu < 4.0, fit.note                            # the case the bound is visible in
    v_in = bounded_t_stats(fit.nu, Z_BOUND)[1]
    assert v_in < 0.99
    H = 252
    ret, _ = simulate_returns(fit, n_paths=40_000, horizon=H, seed=3, drift_daily=0.0)
    realised = math.sqrt(float(np.mean(ret ** 2)) * 252)  # average vol of the paths drawn
    bounded, unbounded = horizon_vol(fit, H, var_in=v_in), horizon_vol(fit, H)
    assert abs(realised / bounded - 1.0) < 0.03, (realised, bounded, unbounded)
    assert unbounded / bounded - 1.0 > 0.03, "the unbounded formula must overstate the fan's vol here"
    mc = run_monte_carlo(_garch_history(), n_paths=300, horizon_days=10, seed=7)
    assert "below the fit's own forecast" in mc.bound_note


def tests():
    return [(name, fn) for name, fn in sorted(globals().items())
            if name.startswith("test_") and callable(fn)]
