"""Acceptance checks for the version-3 asset expansion: the KIS asset-domain
client, the keyless crypto client, the validation gate, the strategy engine,
the equity-derivatives core, the curve models, FX styles, VIX products and
the crypto analytics.

Hermetic by construction: every network touchpoint is replaced by a fake
transport (`KISMarkets(client=_FakeKIS())`, `crypto_client._get`) or the
existing FICC patch, so the suite can never spend a KIS quota or hit an
exchange. Each module's own `__main__` self-check is also invoked here, so the
worked invariants live next to the code and run in one place.
"""
from __future__ import annotations

import contextlib
import math
import runpy
import sys
from datetime import date, timedelta
from pathlib import Path

import numpy as np

import config

ROOT = Path(__file__).resolve().parents[1]


def _selfcheck(rel: str):
    """Run a module's __main__ block as a test (it asserts on its own invariants)."""
    def run():
        runpy.run_path(str(ROOT / rel), run_name="__main__")
    run.__name__ = f"selfcheck_{rel.replace('/', '_').replace('.py', '')}"
    return run


# --------------------------------------------------------------------------- #
# KIS asset domains (fake transport)
# --------------------------------------------------------------------------- #
class _FakeKIS:
    ready = True

    def __init__(self):
        self.calls: list[tuple[str, str, dict]] = []

    def _get(self, path, tr_id, params):
        self.calls.append((path, tr_id, dict(params)))
        end = params.get("FID_INPUT_DATE_2") or params.get("BYMD") or params.get("CLOSE_DATE_TIME") or ""
        end_d = date.fromisoformat(f"{end[:4]}-{end[4:6]}-{end[6:8]}") if end else date(2026, 9, 25)
        day = lambda i: (end_d - timedelta(days=i)).strftime("%Y%m%d")           # noqa: E731
        if path.endswith("display-board-callput"):
            rows = lambda kind: [{"acpr": f"{1000 + 10 * i:.2f}", "optn_prpr": "5.0", "optn_bidp": "4.9", "optn_askp": "5.1",   # noqa: E731
                                  "hts_ints_vltl": "18.5", "delta_val": "0.5", "gama": "0.01", "vega": "1", "theta": "-0.1",
                                  "hts_otst_stpl_qty": "100", "acml_vol": "10", "hts_thpr": "5.0",
                                  "optn_shrn_iscd": f"{kind}01610C{i:02d}", "atm_cls_name": "ATM" if i == 12 else ""} for i in range(25)]
            return {"rt_cd": "0", "output1": rows("B"), "output2": rows("C")}
        if path.endswith("display-board-option-list"):
            return {"rt_cd": "0", "output": [{"mtrt_yymm": "202610"}, {"mtrt_yymm": "202611"}]}
        if path.endswith("comp-interest"):
            return {"rt_cd": "0", "output1": [{"bcdt_code": "Y0112", "hts_kor_isnm": "C D (91일)", "bond_mnrt_prpr": "3.21", "bond_mnrt_prdy_vrss": "0.0"},
                                              {"bcdt_code": "Y0101", "hts_kor_isnm": "국고채 3년", "bond_mnrt_prpr": "4.01", "bond_mnrt_prdy_vrss": "-0.03"}]}
        if path.endswith("inquire-price") and "futureoption" in path:
            if params["FID_INPUT_ISCD"].startswith(("A65", "A75")):      # empty quote, whatever the market code
                return {"rt_cd": "0", "output1": {}, "output3": {"bstp_nmix_prpr": "1126.12"}}
            return {"rt_cd": "0", "output1": {"hts_kor_isnm": "F 202612", "futs_prpr": "1127.75", "basis": "6.66", "hts_thpr": "1132.78",
                                              "dprt": "-0.44", "hts_rmnn_dynu": "79", "hts_otst_stpl_qty": "134791"},
                    "output3": {"hts_kor_isnm": "KOSPI200", "bstp_nmix_prpr": "1126.12"}}
        if path.endswith("daily-ccnl"):
            return {"rt_cd": "0", "output1": {"index_key": day(39)},
                    "output2": [{"data_date": day(i), "open_price": "  18.0", "high_price": "  18.1", "low_price": "  17.9",
                                 "last_price": f"  {17.0 + i * 0.01:.2f}", "vol": "100"} for i in range(40)]}
        if path.endswith("etfetn/v1/quotations/inquire-price"):
            return {"rt_cd": "0", "output": {"stck_prpr": "113145", "nav": "113214.24", "dprt": "-0.06", "trc_errt": "0.12",
                                             "etf_ntas_ttam": "1", "etf_cu_unit_scrt_cnt": "50000", "stck_lstn_date": "20021014"}}
        if path.endswith("domestic-bond/v1/quotations/inquire-price"):
            return {"rt_cd": "0", "output": {"stnd_iscd": params["FID_INPUT_ISCD"], "hts_kor_isnm": "국고03250-2903", "bond_prpr": "9823.00", "ernn_rate": "3.30"}}
        if path.endswith("overseas-price/v1/quotations/price"):
            return {"rt_cd": "0", "output": {"last": "337.2", "base": "335.9", "rate": "+0.38", "tvol": "100"}}
        rows = [{"stck_bsop_date": day(i), "futs_prpr": f"{1000 + i}", "futs_oprc": "1", "futs_hgpr": "1", "futs_lwpr": "1",
                 "xymd": day(i), "clos": f"{100 + i}", "open": "1", "high": "1", "low": "1", "tvol": "1",
                 "stck_clpr": f"{100 + i}", "nav": f"{100.5 + i}", "dprt": "-0.20", "acml_vol": "10",
                 "ovrs_nmix_prpr": f"{4.0 + i * 0.001:.3f}", "bstp_nmix_prpr": f"{1100 + i}", "bond_prpr": "9800",
                 "frgn_ntby_qty": "5", "ssts_cntg_qty": "3", "ssts_vol_rlim": "1.5"} for i in range(0, 5)]
        return {"rt_cd": "0", "output": rows, "output1": {"nrec": "5"}, "output2": rows}


def test_kis_markets_paging_and_shapes():
    from data.kis_markets import KISMarkets
    km = KISMarkets(client=_FakeKIS())
    fut = km.futures_daily("A01612", days=12)
    assert len(fut) == 12 and fut.dates == tuple(sorted(fut.dates)) and fut.source == "KIS"
    assert sum(1 for p, _, _ in km.client.calls if p.endswith("fuopchartprice")) == 3, "12 rows need three 5-row pages"
    assert km.futures_quote("A01612")["theo"] == 1132.78
    try:
        km.futures_quote("A65612")
    except Exception as exc:                          # empty output1 under market F must raise, not return zeros
        assert "no futures quote" in str(exc)
    else:
        raise AssertionError("empty futures quote must raise")
    assert [p["FID_COND_MRKT_DIV_CODE"] for _, _, p in km.client.calls if "A65612" in p.get("FID_INPUT_ISCD", "")] == ["CF"]
    nav = km.etf_nav_daily("069500", days=7)
    assert len(nav) == 7 and nav.extra["premium_pct"][-1] == -0.2
    board = km.option_board("202610")
    assert len(board.calls) == 25 == len(board.puts) and board.calls[0].strike < board.calls[-1].strike
    assert board.calls[0].iv == 0.185 and board.expiry_date == "2026-10-08"
    assert km.option_expiries() == ["202610", "202611"]
    ys = km.krw_yields_snapshot()
    assert ys[0]["code"] == "Y0112" and ys[0]["tenor"] == 0.25
    y = km.krw_yield_daily("Y0101", days=6)
    assert y.symbol == "I:Y0101" and len(y) == 6
    vx = km.ovf_daily("VXV26", "CBOE", days=60)
    assert len(vx) >= 40 and vx.symbol == "VXV26@CBOE"
    ov = km.overseas_daily("nas", "aapl", days=6)
    assert ov.symbol == "NAS:AAPL" and ov.note == "adjusted close"
    assert km.bond_quote("KR103501GE31")["yield_pct"] == 3.3
    inv = km.investor_daily("005930", days=8)
    assert len(inv) >= 5 and inv[0]["foreign_net_qty"] == 5.0
    assert km.etf_quote("069500")["nav"] == 113214.24
    h = fut.to_history()
    assert h.symbol == "A01612" and len(h) == 12


def test_kis_markets_offline_is_unavailable_without_keys():
    from data.kis_markets import KISMarkets
    from data.krx.kis_client import KISUnavailable
    saved = config.kis_ready
    config.kis_ready = lambda: False
    try:
        km = KISMarkets()
        assert not km.ready
        try:
            km.etf_quote("069500")
        except KISUnavailable:
            pass
        else:
            raise AssertionError("must raise KISUnavailable")
    finally:
        config.kis_ready = saved


def test_master_parsers():
    from data.kis_markets import _BOND_RE, _COM_RE, KISMarkets
    m = _COM_RE.match("11A65612   KR4A656C00093년국채    F 202612                      000000001BM33년채")
    assert m and m.group(2) == "A65612" and m.group(6) == "202612" and m.group(7)[-1] == "1"
    b = _BOND_RE.match("F902KR103501GE31국고03250-2903(24-1)                    13202401232024031020290310   Y")
    assert b and b.group(2) == "KR103501GE31"
    assert KISMarkets.futures_market("A05610") == "F" and KISMarkets.futures_market("A67612") == "CF"


# --------------------------------------------------------------------------- #
# Crypto client (fake transport) and history routing
# --------------------------------------------------------------------------- #
def test_crypto_client_refusals_and_router():
    import data.crypto.crypto_client as cc
    src = (ROOT / "data" / "crypto" / "crypto_client.py").read_text(encoding="utf-8")
    for forbidden in ("/v1/orders", "/v1/withdraws", "/api/v3/order", "private_key", "seed_phrase", "import ccxt", "import web3"):
        assert forbidden not in src.replace("No order, cancel, withdrawal", ""), forbidden
    saved = cc._get
    calls = []

    def fake(url, params=None, headers=None, *, label):
        calls.append(url)
        if "candles" in url:
            return [{"candle_date_time_utc": f"2026-09-{25 - i:02d}T00:00:00", "trade_price": 100 + i, "opening_price": 1,
                     "high_price": 1, "low_price": 1, "candle_acc_trade_volume": 1, "candle_acc_trade_price": 1} for i in range(5)]
        if "klines" in url:
            return [[1758758400000 - i * 86400000, "1", "2", "0.5", str(50 + i), "9", 0, "450"] for i in range(5)]
        if "accounts" in url:
            assert headers["Authorization"].startswith("Bearer ")
            return [{"currency": "BTC", "balance": "0.5", "locked": "0", "avg_buy_price": "90000000", "unit_currency": "KRW"}]
        raise AssertionError(url)
    cc._get = fake
    try:
        u = cc.UpbitPublic().daily("KRW-BTC", days=5)
        assert len(u) == 5 and u.source == "UPBIT" and u.to_history().source == "UPBIT"
        b = cc.BinancePublic().daily("BTCUSDT", days=5)
        assert len(b) == 5 and b.close[-1] == 50.0
        saved_ready, saved_keys = config.upbit_ready, config.upbit_keys
        config.upbit_ready = lambda: True
        config.upbit_keys = lambda: ("a" * 40, "s" * 40)
        try:
            bal = cc.UpbitAccount().balances()
            assert bal[0]["avg_buy_price"] == 90_000_000.0 and bal[0]["total"] == 0.5
        finally:
            config.upbit_ready, config.upbit_keys = saved_ready, saved_keys
        from core.quant.history import load_history
        # Cache off: these five fake rows must neither be answered by a real
        # cached KRW-BTC series nor be written where the app would read them.
        saved_ttl, config.FICC_CACHE_TTL_SECONDS = config.FICC_CACHE_TTL_SECONDS, 0.0
        try:
            h = load_history("KRW-BTC", source="auto")
        finally:
            config.FICC_CACHE_TTL_SECONDS = saved_ttl
        assert h.source == "UPBIT" and len(h) == 5
        assert not any("binance" in c for c in calls[:1])
    finally:
        cc._get = saved
    from core.quant.history import _looks_crypto, _looks_kis_market, _looks_yahoo
    assert _looks_crypto("ETHUSDT") and _looks_kis_market("A65612") and _looks_yahoo("ZN=F") and not _looks_yahoo("SPY")
    assert not _looks_kis_market("SPY") and not _looks_kis_market("005930")


def test_etf_page_sleeves_use_adjusted_closes_and_survive_their_loss():
    """A KRX ETF's sleeve statistics run on split-adjusted closes, and losing
    that series must not lose the quote, premium and basket already fetched."""
    import data.kis_markets as km_mod
    import ui.etf_page as etf
    from core.quant.history import History, HistoryError, synthetic_history
    n = 400
    base = synthetic_history("069500", days=n)
    # The NAV series' raw close: the same fund with an unadjusted 2-for-1 split halfway.
    raw = tuple(c * (2.0 if i < n // 2 else 1.0) for i, c in enumerate(base.closes))
    premium = tuple(float(x) for x in 0.2 * np.sin(np.arange(n) * 1.7))

    class _FakeKM:
        def etf_quote(self, code):
            return {"price": raw[-1]}

        def etf_nav_daily(self, code, *, days=504):
            return km_mod.Bars(code, base.dates, raw, extra={"nav": raw, "premium_pct": premium})

        def etf_components(self, code):
            return []

    saved = (km_mod.KISMarkets, etf.load_history, config.kis_ready)
    km_mod.KISMarkets = _FakeKM
    config.kis_ready = lambda: True
    try:
        etf.load_history = lambda code, **kw: History(code, "KIS", base.dates, base.closes,
                                                      note="KIS 수정주가 (test)", adjustment="split")
        a = etf.analyze("069500", days=n)
        assert a["sleeve_basis"] == "KIS 수정주가 (test)" and len(a["sleeve_dates"]) == n
        raw_px = np.asarray(raw)
        raw_mdd = etf.S.summary(raw_px[1:] / raw_px[:-1] - 1.0)["max_drawdown"]
        assert abs(a["sleeves"]["buy_hold"]["max_drawdown"]) < abs(raw_mdd), "the split must not be booked as a crash"
        assert a["price"][0] == raw[0], "the premium chart keeps the raw price / NAV pair"

        def unavailable(code, **kw):
            raise HistoryError("KIS returned only 20 usable sessions")
        etf.load_history = unavailable
        b = etf.analyze("069500", days=n)
        assert b["quote"] and "premium_stats" in b and "sleeves" in b
        assert "NOT split-adjusted" in b["sleeve_basis"] and "20 usable sessions" in b["sleeve_basis"]
    finally:
        km_mod.KISMarkets, etf.load_history, config.kis_ready = saved


def test_history_auto_still_degrades_without_keys():
    """The existing invariant: plain tickers without FMP stay SYNTHETIC (no Yahoo call)."""
    from core.quant.history import load_history
    saved = (config.fmp_ready, config.fmp_key, config.kis_ready)
    config.fmp_ready = lambda: False
    config.fmp_key = lambda: ""
    config.kis_ready = lambda: False
    try:
        assert load_history("AAPL").source == "SYNTHETIC"
        assert load_history("A01612").source == "SYNTHETIC" and "KIS" in load_history("A01612").note
    finally:
        config.fmp_ready, config.fmp_key, config.kis_ready = saved


# --------------------------------------------------------------------------- #
# The gate on a known edge
# --------------------------------------------------------------------------- #
def test_gate_rejects_noise_and_keeps_a_real_edge():
    from core.quant import validate as V
    rng = np.random.default_rng(3)
    T = 2520
    dates = [(date(2016, 1, 1) + timedelta(days=int(i * 365.25 / 252))).isoformat() for i in range(T)]
    grid = [{"a": i} for i in range(12)]
    good = np.column_stack([rng.normal(1.2 / math.sqrt(252) * 0.01, 0.01, T)] + [rng.normal(0, 0.01, T) for _ in range(11)])
    noise = rng.normal(0, 0.01, (T, 12))
    turn = np.abs(rng.normal(0, 0.2, (T, 12)))
    saved_b = V.GATE["bootstrap_B"]
    V.GATE["bootstrap_B"] = 300
    try:
        wf_g = V.walk_forward(good, dates, turnover=turn, pnl_stress=good - 0.0001, embargo=1)
        wf_n = V.walk_forward(noise, dates, turnover=turn, embargo=1)
        sg = V.score_strategy(wf_g, grid=grid, full_pnl=good, n_trials=12)
        sn = V.score_strategy(wf_n, grid=grid, full_pnl=noise, n_trials=12)
        assert sg.ci90[0] > 0 and sg.sr_oos > 0.7, (sg.sr_oos, sg.ci90)
        assert sn.decision != "PASS" and sn.dsr < 0.95, (sn.decision, sn.dsr)
        assert sg.dsr > sn.dsr, (sg.dsr, sn.dsr)
        assert all(isinstance(l, str) and l for l in sg.lines) and len(sg.lines) >= 8
        assert V.kupiec(rng.random(1000) < 0.05, 0.05)["p"] > 0.05
        assert V.pit_tests(rng.random(800))["ks_p"] > 0.05
        card = V.ModelCard(card_id="t", kind="strategy", hypothesis="h", rules={}, universe={}, data={}, costs={}, protocol={},
                           trials={}, seed=1, stats={}, tests={}, decision=sg.decision, decision_reason=sg.reason,
                           revise_target=sg.revise_target, lines=sg.lines)
        assert '"decision"' in card.to_json()
    finally:
        V.GATE["bootstrap_B"] = saved_b          # the leak every later in-process bootstrap inherited


def test_strategies_are_causal():
    """Shifting the future must not change today's weight."""
    from core.quant import strategies as S
    rng = np.random.default_rng(8)
    P = 100 * np.exp(np.cumsum(rng.normal(0.0003, 0.01, (900, 3)), axis=0))
    P2 = P.copy()
    P2[600:] *= np.exp(np.cumsum(rng.normal(0.01, 0.02, (300, 3)), axis=0))
    for fn, kw in ((S.trend_switch, {"lookback": 126}), (S.vol_target, {"target": 0.12}),
                   (S.xs_momentum, {"lookback": 126}), (S.tsmom, {"lookback": 126}), (S.crypto_trend, {})):
        W1, W2 = fn(P, **kw), fn(P2, **kw)
        assert np.allclose(W1[:599], W2[:599]), fn.__name__
    W1, _ = S.pairs(P[:, :2], formation=252, trading=126)
    W2, _ = S.pairs(P2[:, :2], formation=252, trading=126)
    assert np.allclose(W1[:599], W2[:599])


def test_gate_counts_whole_years_and_costs_by_the_table():
    """The five-year rule counts whole years, not calendar years touched; a run's cost floor is QUANTGEN's table."""
    from core.quant import validate as V
    days = [d.isoformat() for d in (date(2021, 11, 1) + timedelta(days=i) for i in range(1216)) if d.weekday() < 5]
    ys = V.year_stats(days, np.ones(len(days)))
    assert days[-1] == "2025-02-28" and len(ys["by_year"]) == 5 and ys["n_years"] == 3, ys["n_years"]
    assert V.full_years("2020-01-02", "2025-01-02") == 5 and V.full_years("2020-01-02", "2025-01-01") == 4
    assert V.cost_floor_bp(["SPY", "069500"])[0] == 50.0 and V.cost_floor_bp(["069500", "152380"])[0] == 3.0
    assert V.cost_floor_bp(["SPY", "SHEL.L"])[0] is None, "a venue QUANTGEN cannot cost gives no floor"
    assert [V.cost_class(s) for s in ("EURUSD=X", "ES=F", "BTC-USD", "KRW-BTC", "BRK-B")] ==         ["fx", "futures", "crypto", "crypto", "us"]
    assert [V.cost_class(s) for s in ("005930", "005935.KS", "105560", "BTCUSDT", "NAS:AAPL", "A01612", "FX@KRW")] ==         ["krx_stock", "krx_stock", "krx_stock", "crypto", "us", "futures", "fx"], "stocks at 35 bp, not the ETF row"


def tests():
    return [
        ("kis_markets_paging_and_shapes", test_kis_markets_paging_and_shapes),
        ("kis_markets_unavailable_without_keys", test_kis_markets_offline_is_unavailable_without_keys),
        ("kis_master_parsers", test_master_parsers),
        ("crypto_client_refusals_and_router", test_crypto_client_refusals_and_router),
        ("history_auto_degrades_without_keys", test_history_auto_still_degrades_without_keys),
        ("etf_page_adjusted_sleeves", test_etf_page_sleeves_use_adjusted_closes_and_survive_their_loss),
        ("gate_noise_vs_edge", test_gate_rejects_noise_and_keeps_a_real_edge),
        ("strategies_are_causal", test_strategies_are_causal),
        ("gate_whole_years_and_cost_floor", test_gate_counts_whole_years_and_costs_by_the_table),
        ("selfcheck_kis_markets", _selfcheck("data/kis_markets.py")),
        ("selfcheck_crypto_client", _selfcheck("data/crypto/crypto_client.py")),
        ("selfcheck_validate", _selfcheck("core/quant/validate.py")),
        ("selfcheck_strategies", _selfcheck("core/quant/strategies.py")),
        ("selfcheck_strategy_lab", _selfcheck("ui/strategy_lab_page.py")),
        ("selfcheck_equity_deriv", _selfcheck("core/ficc/equity_deriv.py")),
        ("selfcheck_curve_models", _selfcheck("core/ficc/curve_models.py")),
        ("selfcheck_fx_styles", _selfcheck("core/ficc/fx_styles.py")),
        ("selfcheck_vol_products", _selfcheck("core/ficc/vol_products.py")),
        ("selfcheck_crypto_analytics", _selfcheck("core/crypto/analytics.py")),
    ]


if __name__ == "__main__":
    sys.path.insert(0, str(ROOT))
    for name, fn in tests():
        fn()
        print("PASS", name)
