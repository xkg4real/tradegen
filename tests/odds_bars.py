"""Odds plan Task 15: the unsigned bar loader core/oddsdata/bars.py (spec 4 "Bars", 7.2 "Price series", "Data
rules"; O1, O6, O7, O13; Q6, Q7, Q13, Q35, Q36).

Every test runs inside tests.odds_acceptance._wrap, which sets the four seams to macro_acceptance._boom. A test that
needs data nests its fakes inside that patch with `_seams(...)`; restoring puts the raising stub back. No test
reaches a data client or yfinance for real: the seam-body tests call the real functions kept in
tests.odds_acceptance.REAL_SEAMS against fake client classes or a fake `yfinance` module."""
from __future__ import annotations

import ast
import contextlib
import dataclasses
import json
import math
import os
import subprocess
import sys
import types
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from core.compliance import model
from core.odds import plan as P
from core.oddsdata import bars
from tests import compliance_guards as CG
from tests import macro_acceptance as MA
from tests import odds_acceptance as OA

ROOT = Path(__file__).resolve().parents[1]
UTC, KST = timezone.utc, model.KST
DAY = date(2026, 10, 23)                               # the plan's start, a Friday
NOW = datetime(2026, 10, 23, 9, 0, tzinfo=KST)         # 00:00Z: the crypto bar of 2026-10-22 is final from here
AFTER_CLOSE = datetime(2026, 10, 23, 16, 0, tzinfo=KST)  # the KRX bar of 2026-10-23 is final from 15:40 KST
START = DAY - timedelta(days=bars.HISTORY_DAYS)        # 2016-10-25, the window's first date
CRYPTO, KRX, US = (types.SimpleNamespace(section=s) for s in ("crypto", "krx", "us"))


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
@contextlib.contextmanager
def _seams(**fakes):
    """The named seams of core.oddsdata.bars replaced by fakes for the block, nested inside the suite's raising
    patch; afterwards every seam is the raising stub again."""
    saved = {name: vars(bars)[name] for name in fakes}
    for name, fake in fakes.items():
        setattr(bars, name, fake)
    try:
        yield
    finally:
        for name, value in saved.items():
            setattr(bars, name, value)
        assert all(vars(bars)[name] is MA._boom for name in OA.SEAMS), "a seam was left unpatched"


def _raises(fn, exc=Exception) -> Exception:
    try:
        fn()
    except exc as e:
        return e
    raise AssertionError(f"expected {exc.__name__}")


def _plan(venue: str, symbol: str, start: date = DAY) -> P.Plan:
    return P.Plan(name="bars test", track="compounding", stake_krw=42_000.0, target_krw=42_000_000.0,
                  fx_krw_per_usd=1_400.0, start=start, horizon_days=10,
                  leg=P.Leg(venue=venue, symbol=symbol, model="bootstrap"), fraction=P.fixed(1.0))


def _dates(first: date, last: date, *, weekdays: bool = False) -> list[str]:
    out, d = [], first
    while d <= last:
        if not weekdays or d.weekday() < 5:
            out.append(d.isoformat())
        d += timedelta(days=1)
    return out


def _candles(dates, opens, closes):
    """What crypto_client's UpbitPublic().daily and BinancePublic().daily return (the fields bars reads)."""
    return types.SimpleNamespace(dates=tuple(dates), open=tuple(opens), close=tuple(closes))


def _frame(ticker: str, dates, opens, closes):
    """A yfinance 1.4 download frame: (Price, Ticker) MultiIndex columns, a tz-naive daily DatetimeIndex."""
    import pandas as pd
    cols = pd.MultiIndex.from_tuples([("Close", ticker), ("Open", ticker)], names=["Price", "Ticker"])
    return pd.DataFrame(list(zip(closes, opens)), index=pd.DatetimeIndex(list(dates), name="Date"), columns=cols)


def _kis_fake(rows: list[dict], calls: list):
    """KISClient().daily as KIS answers: the last KIS_PAGE rows dated in [start, end] (YYYYMMDD), ascending."""
    def fake(code, start, end):
        calls.append((code, start, end))
        return [dict(r) for r in rows if start <= r["date"].replace("-", "") <= end][-bars.KIS_PAGE:]
    return fake


def _kis_rows(dates) -> list[dict]:
    return [{"date": d, "open": 100.0 + i, "high": 110.0 + i, "low": 90.0 + i, "close": 101.0 + i, "volume": 1.0,
             "source": "KIS"} for i, d in enumerate(dates)]


def _upbit_fake(calls: list, dates, opens, closes):
    def fake(market, days):
        calls.append((market, days))
        return _candles(dates, opens, closes)
    return fake


# --------------------------------------------------------------------------- #
# Seams: patched by the suite, the only importers of a client, nothing loaded at import
# --------------------------------------------------------------------------- #
def test_unpatched_seams_are_refused_inside_the_suite():
    """O13: inside the odds wrapper every seam is the raising stub, so a test that forgets a fake is refused, and the
    real functions are kept for the seam-body tests."""
    assert OA.SEAMS == ("_kis_daily", "_upbit_daily", "_binance_daily", "_yf_download")
    for name, args in (("_kis_daily", ("005930", "20260101", "20261022")), ("_upbit_daily", ("KRW-BTC", 10)),
                       ("_binance_daily", ("BTCUSDT", 10)), ("_yf_download", (["SPY"], "2026-01-01", "2026-02-01"))):
        assert vars(bars)[name] is MA._boom, name
        _raises(lambda: getattr(bars, name)(*args), MA.HermeticViolation)
        real = OA.REAL_SEAMS[name]
        assert real is not MA._boom and real.__module__ == "core.oddsdata.bars" and real.__name__ == name, name
    _raises(lambda: bars.upbit_part("KRW-BTC", date(2026, 1, 1), DAY, NOW), MA.HermeticViolation)
    _raises(lambda: bars.load_leg(_plan("kis", "005930"), KRX, NOW), MA.HermeticViolation)
    assert not bars.cache_dir().exists()                # a refused fetch caches nothing


def test_only_the_seams_import_a_data_client_or_yfinance():
    """An AST scan of bars.py: the functions that import data.* or yfinance are exactly SEAMS, each a module-level
    function importing inside its body; nothing imports config, and nothing imports a client at module level."""
    rel = "core/oddsdata/bars.py"
    tree = ast.parse((ROOT / rel).read_text(encoding="utf-8"))
    importers = []
    for node, module, _names, funcs in CG._imports(rel, tree):
        top = module.split(".")[0]
        assert top != "config", f"{rel}:{node.lineno} imports config"
        if top in ("data", "yfinance"):
            assert funcs, f"{rel}:{node.lineno} imports {module} at module level"
            importers.append(funcs[-1])
    assert sorted(importers) == sorted(OA.SEAMS), importers
    top_defs = {n.name for n in tree.body if isinstance(n, ast.FunctionDef)}
    assert set(OA.SEAMS) <= top_defs, top_defs


def test_importing_bars_loads_no_data_client_config_or_yfinance():
    """A fresh interpreter that imports core.oddsdata.bars holds no data.*, config or yfinance module afterwards."""
    prog = (f"import json, sys; sys.path.insert(0, {str(ROOT)!r}); import core.oddsdata.bars; "
            "print(json.dumps(sorted(m for m in sys.modules if m.split('.')[0] in ('data', 'config', 'yfinance'))))")
    done = subprocess.run([sys.executable, "-I", "-B", "-c", prog], cwd=str(ROOT), capture_output=True, timeout=120)
    assert done.returncode == 0, done.stderr.decode("utf-8", errors="replace")[-2000:]
    assert json.loads(done.stdout.decode("utf-8").splitlines()[-1]) == [], done.stdout


def test_yf_seam_moves_the_tz_cache_before_downloading():
    """The real `_yf_download` against a fake yfinance module: set_tz_cache_location gets <home>/odds/yfinance
    (created through checked_target) before download, which gets explicit dates and auto_adjust=True."""
    calls = []
    fake = types.ModuleType("yfinance")
    fake.set_tz_cache_location = lambda where: calls.append(("tz", where))
    fake.download = lambda tickers, **kw: calls.append(("download", tickers, kw)) or "frame"
    saved = sys.modules.get("yfinance")
    sys.modules["yfinance"] = fake
    try:
        out = OA.REAL_SEAMS["_yf_download"](["SPY"], "2026-01-01", "2026-02-01")
    finally:
        if saved is None:
            sys.modules.pop("yfinance", None)
        else:
            sys.modules["yfinance"] = saved
    where = bars.odds_dir() / "yfinance"
    assert out == "frame" and where.is_dir()
    assert where.resolve().is_relative_to(Path(os.environ["TRADEGEN_HOME"]).resolve()), where
    assert calls == [("tz", str(where)),
                     ("download", ["SPY"], {"start": "2026-01-01", "end": "2026-02-01", "auto_adjust": True,
                                            "progress": False, "threads": False, "multi_level_index": True})], calls
    assert vars(bars)["_yf_download"] is MA._boom                     # the seam was never reloaded or unpatched


def test_client_seams_call_their_client_as_documented():
    """The real `_kis_daily`, `_upbit_daily` and `_binance_daily` against fake client classes (swapped on the
    already imported client modules, restored afterwards)."""
    from data.crypto import crypto_client
    from data.krx import kis_client
    calls = []

    class FakeKIS:
        def daily(self, code, *, start=None, end=None, adjusted=True):
            calls.append(("kis", code, start, end, adjusted))
            return ["kis rows"]

    class FakeUpbit:
        def daily(self, market="KRW-BTC", *, days=504):
            calls.append(("upbit", market, days))
            return "upbit candles"

    class FakeBinance:
        def daily(self, symbol="BTCUSDT", *, days=504, interval="1d", market="spot"):
            calls.append(("binance", symbol, days, interval, market))
            return "binance candles"

    saved = (kis_client.KISClient, crypto_client.UpbitPublic, crypto_client.BinancePublic)
    kis_client.KISClient, crypto_client.UpbitPublic, crypto_client.BinancePublic = FakeKIS, FakeUpbit, FakeBinance
    try:
        got = (OA.REAL_SEAMS["_kis_daily"]("005930", "20160101", "20261022"),
               OA.REAL_SEAMS["_upbit_daily"]("KRW-BTC", 297), OA.REAL_SEAMS["_binance_daily"]("BTCUSDT", 297))
    finally:
        kis_client.KISClient, crypto_client.UpbitPublic, crypto_client.BinancePublic = saved
    assert got == (["kis rows"], "upbit candles", "binance candles"), got
    assert calls == [("kis", "005930", "20160101", "20261022", True), ("upbit", "KRW-BTC", 297),
                     ("binance", "BTCUSDT", 297, "1d", "spot")], calls


# --------------------------------------------------------------------------- #
# Parts: paging, row filters, finality
# --------------------------------------------------------------------------- #
def test_kis_pages_backwards_and_drops_bad_rows():
    """O7: 100 rows a call, each call ending the day before the earliest row held, until a short page; rows whose
    open or close is None, zero, negative or not finite are dropped."""
    days = _dates(date(2025, 12, 1), DAY, weekdays=True)[-230:]
    rows = _kis_rows(days)
    for i, field, value in ((5, "open", None), (50, "close", 0.0), (120, "open", -1.0), (200, "close", math.nan)):
        rows[i][field] = value
    calls = []
    with _seams(_kis_daily=_kis_fake(rows, calls)):
        part = bars.kis_part("005930", date(2025, 1, 1), DAY + timedelta(days=1), AFTER_CLOSE)
    assert [c[1] for c in calls] == ["20250101"] * 3, calls
    assert [c[2] for c in calls] == ["20261023", (date.fromisoformat(days[130]) - timedelta(days=1)).strftime("%Y%m%d"),
                                     (date.fromisoformat(days[30]) - timedelta(days=1)).strftime("%Y%m%d")], calls
    good = [i for i in range(230) if i not in (5, 50, 120, 200)]
    assert part == bars.Part(symbol="005930", source="KIS", dates=tuple(days[i] for i in good),
                             open=tuple(100.0 + i for i in good), close=tuple(101.0 + i for i in good),
                             adjustment="split"), part


def test_kis_paging_stops_at_the_window_start_and_the_page_cap():
    """O7: paging stops at the window start, after KIS_MAX_PAGES calls, and on a full page that adds no new date."""
    assert (bars.HISTORY_DAYS, bars.CACHE_ENV, bars.KIS_MAX_PAGES) == (3650, "TRADEGEN_ODDS_BARS_CACHE", 60)
    days = _dates(date(2025, 12, 1), DAY, weekdays=True)[-200:]
    calls = []
    with _seams(_kis_daily=_kis_fake(_kis_rows(days), calls)):
        part = bars.kis_part("005930", date.fromisoformat(days[0]), DAY + timedelta(days=1), AFTER_CLOSE)
    assert len(calls) == 2 and part.dates == tuple(days), calls      # two full pages, then the window start
    saved, calls = bars.KIS_MAX_PAGES, []
    bars.KIS_MAX_PAGES = 1
    try:
        with _seams(_kis_daily=_kis_fake(_kis_rows(days), calls)):
            part = bars.kis_part("005930", date(2025, 1, 1), DAY + timedelta(days=1), AFTER_CLOSE)
    finally:
        bars.KIS_MAX_PAGES = saved
    assert len(calls) == 1 and part.dates == tuple(days[-100:]), calls
    calls, page = [], _kis_rows(days[-100:])

    def stuck(code, start, end):
        calls.append(end)
        return [dict(r) for r in page]                                # the same full page whatever is asked
    with _seams(_kis_daily=stuck):
        part = bars.kis_part("005930", date(2025, 1, 1), DAY + timedelta(days=1), AFTER_CLOSE)
    assert len(calls) == 2 and part.dates == tuple(days[-100:]), calls


def test_kis_paging_reaches_a_row_dated_on_the_window_start():
    """Consecutive dates: the second page ends the day after the window start, so a third call asks for the start
    alone and its row is kept."""
    days = _dates(date(2026, 4, 5), date(2026, 10, 22))[-201:]
    calls = []
    with _seams(_kis_daily=_kis_fake(_kis_rows(days), calls)):
        part = bars.kis_part("005930", date.fromisoformat(days[0]), DAY, AFTER_CLOSE)
    assert len(calls) == 3 and calls[-1][1:] == (days[0].replace("-", ""),) * 2, calls
    assert part.dates == tuple(days), part.dates[:2]


def test_a_krx_bar_dated_today_is_final_from_1540_kst():
    calls = []
    with _seams(_kis_daily=_kis_fake(_kis_rows(["2026-10-21", "2026-10-22", "2026-10-23"]), calls)):
        before = bars.kis_part("069500", date(2026, 10, 1), DAY + timedelta(days=1),
                               datetime(2026, 10, 23, 15, 39, 59, tzinfo=KST))
        after = bars.kis_part("069500", date(2026, 10, 1), DAY + timedelta(days=1),
                              datetime(2026, 10, 23, 15, 40, tzinfo=KST))
    assert before.dates == ("2026-10-21", "2026-10-22") and after.dates[-1] == "2026-10-23", (before, after)
    assert [c[2] for c in calls] == ["20261022", "20261023"], calls  # a non-final date is never even asked for
    assert not bars.final_krx(DAY, datetime(2026, 10, 23, 6, 39, 59, tzinfo=UTC))
    assert bars.final_krx(DAY, datetime(2026, 10, 23, 6, 40, tzinfo=UTC))


def test_crypto_candles_are_filtered_to_the_window_and_to_final_bars():
    """Upbit and Binance: dates outside the window dropped; bar d kept only from 00:00Z of d + 1; an open or close of
    0.0 (Upbit's missing field) dropped; `days` reaches back to the window start plus one spare."""
    dates = _dates(date(2025, 12, 25), DAY)                         # 2025-12-25 .. 2026-10-23, the last one running
    opens = [1000.0 + i for i in range(len(dates))]
    closes = [1001.0 + i for i in range(len(dates))]
    opens[20], closes[40] = 0.0, 0.0
    start, end = date(2026, 1, 1), DAY + timedelta(days=1)
    late = datetime(2026, 10, 23, 8, 59, 59, tzinfo=KST)            # 23:59:59Z on 2026-10-22
    keep = [i for i, d in enumerate(dates) if "2026-01-01" <= d and i not in (20, 40)]
    for fetch, seam, symbol, source in ((bars.upbit_part, "_upbit_daily", "KRW-BTC", "UPBIT"),
                                        (bars.binance_part, "_binance_daily", "BTCUSDT", "BINANCE")):
        calls = []
        with _seams(**{seam: _upbit_fake(calls, dates, opens, closes)}):
            early, final = fetch(symbol, start, end, late), fetch(symbol, start, end, NOW)
        assert calls == [(symbol, 296), (symbol, 297)], calls
        assert early.dates == tuple(dates[i] for i in keep if dates[i] <= "2026-10-21"), early.dates[-3:]
        assert final == bars.Part(symbol=symbol, source=source, dates=tuple(dates[i] for i in keep[:-1]),
                                  open=tuple(opens[i] for i in keep[:-1]), close=tuple(closes[i] for i in keep[:-1]),
                                  adjustment=""), final.dates[-3:]
    assert not bars.final_crypto(date(2026, 10, 22), late) and bars.final_crypto(date(2026, 10, 22), NOW)


def test_a_us_bar_is_final_from_1610_new_york_on_the_next_seoul_date():
    """O6: EST and EDT days; the close and the finality instant both fall on the Asia/Seoul date d + 1; yahoo_part
    asks yfinance only for final dates (its end is exclusive)."""
    for d, edge_kst in ((date(2026, 1, 2), datetime(2026, 1, 3, 6, 10, tzinfo=KST)),
                        (date(2026, 7, 2), datetime(2026, 7, 3, 5, 10, tzinfo=KST))):
        assert not bars.final_us(d, edge_kst - timedelta(seconds=1)) and bars.final_us(d, edge_kst), d
        assert datetime(d.year, d.month, d.day, 16, 0, tzinfo=bars.ET).astimezone(KST).date() == d + timedelta(days=1)
        assert datetime(d.year, d.month, d.day, 13, 0, tzinfo=bars.ET).astimezone(KST).date() == d + timedelta(days=1)
    calls, dates = [], ["2026-06-30", "2026-07-01", "2026-07-02"]

    def fake(tickers, start, end):
        calls.append((tickers, start, end))
        return _frame("SPY", dates, [500.0, 501.0, 502.0], [505.0, math.nan, 507.0])
    edge = datetime(2026, 7, 3, 5, 10, tzinfo=KST)
    with _seams(_yf_download=fake):
        before = bars.yahoo_part("SPY", date(2026, 6, 29), date(2026, 7, 3), edge - timedelta(seconds=1))
        after = bars.yahoo_part("SPY", date(2026, 6, 29), date(2026, 7, 3), edge)
    assert calls == [(["SPY"], "2026-06-29", "2026-07-02"), (["SPY"], "2026-06-29", "2026-07-03")], calls
    assert before.dates == ("2026-06-30",) and after.dates == ("2026-06-30", "2026-07-02"), (before, after)
    assert after == bars.Part(symbol="SPY", source="YAHOO", dates=("2026-06-30", "2026-07-02"), open=(500.0, 502.0),
                              close=(505.0, 507.0), adjustment="total"), after


def test_an_fx_bar_is_final_from_0000z_two_days_later():
    x, edge = date(2026, 10, 21), datetime(2026, 10, 23, 0, 0, tzinfo=UTC)
    assert not bars.final_fx(x, edge - timedelta(seconds=1)) and bars.final_fx(x, edge)
    with _seams(_yf_download=lambda tickers, start, end: _frame("KRW=X", ["2026-10-20", "2026-10-21"],
                                                                  [1390.0, 1391.0], [1392.0, 1393.0])):
        before = bars.yahoo_part("KRW=X", date(2026, 10, 1), DAY, edge - timedelta(seconds=1))
        after = bars.yahoo_part("KRW=X", date(2026, 10, 1), DAY, edge)
    assert before.dates == ("2026-10-20",) and after.dates == ("2026-10-20", "2026-10-21"), (before, after)
    assert after.adjustment == "" and after.source == "YAHOO" and after.symbol == "KRW=X", after


# --------------------------------------------------------------------------- #
# Legs: KRW composition, labels, components and md5
# --------------------------------------------------------------------------- #
def test_series_labels_components_and_md5_for_krx_and_upbit():
    """The KRX and Upbit legs: symbol, source, adjustment, status, the one component and series_md5 exactly; the
    loader never labels anything synthetic."""
    days = ["2026-10-20", "2026-10-21", "2026-10-22"]
    with _seams(_kis_daily=_kis_fake(_kis_rows(days), [])):
        krx = bars.load_leg(_plan("kis", "005930"), KRX, NOW)
    o, c = (100.0, 101.0, 102.0), (101.0, 102.0, 103.0)
    part = P.series_md5("005930", "KIS", days, o, c, "split", "final")
    assert krx == P.Series(symbol="005930", source="KIS", dates=tuple(days), open=o, close=c, adjustment="split",
                           status="final", md5=P.series_md5("005930", "KIS", days, o, c, "split", "final"),
                           components=(("KIS:005930", part),), proxy_dates=None), krx
    with _seams(_upbit_daily=lambda market, n: _candles(days + ["2026-10-23"], (1.0, 2.0, 3.0, 4.0),
                                                         (1.5, 2.5, 3.5, 4.5))):
        btc = bars.load_leg(_plan("upbit", "BTC"), CRYPTO, NOW)
    o, c = (1.0, 2.0, 3.0), (1.5, 2.5, 3.5)
    md5 = P.series_md5("KRW-BTC", "UPBIT", days, o, c, "", "final")
    assert btc == P.Series(symbol="KRW-BTC", source="UPBIT", dates=tuple(days), open=o, close=c, adjustment="",
                           status="final", md5=md5, components=(("UPBIT:KRW-BTC", md5),), proxy_dates=None), btc
    for s in (krx, btc):
        assert s.status == "final" and "SYNTHETIC" not in s.source.upper(), s


def test_a_failed_feed_raises_and_never_falls_back():
    """Spec 9: SYNTHETIC_REFUSED is never produced by the loader, because it never degrades: a feed that fails
    raises, and nothing is cached. A leg no feed serves (another section, an OKX symbol other than BTC) and a naive
    `now` are refused before any fetch."""
    def down(market, days):
        raise RuntimeError("feed down")
    with _seams(_upbit_daily=down):
        err = _raises(lambda: bars.load_leg(_plan("upbit", "BTC"), CRYPTO, NOW), RuntimeError)
    assert str(err) == "feed down" and not bars.cache_dir().exists(), err
    _raises(lambda: bars.load_leg(_plan("kis", "005930"), types.SimpleNamespace(section="jp"), NOW), ValueError)
    _raises(lambda: bars.load_leg(_plan("okx", "ETH"), CRYPTO, NOW), ValueError)
    _raises(lambda: bars.load_leg(_plan("upbit", "BTC"), CRYPTO, datetime(2026, 10, 23, 9, 0)), ValueError)


def test_us_krw_prices_use_fx_of_the_day_before_for_the_open():
    """O6, Q35: open_KRW = open_USD x FX(d - 1), close_KRW = close_USD x FX(d), FX(x) the close of the last final
    KRW=X bar dated on or before x; a row with no such bar is dropped. At 09:00 KST on 2026-10-23 the NY bar of
    2026-10-22 is final (16:10 EDT = 05:10 KST) and the KRW=X bar of 2026-10-22 is not (00:00Z of 2026-10-24)."""
    us_days = ["2026-10-14", "2026-10-15", "2026-10-16", "2026-10-19", "2026-10-20", "2026-10-21", "2026-10-22"]
    fx_days = ["2026-10-15", "2026-10-16", "2026-10-19", "2026-10-20", "2026-10-21", "2026-10-22"]
    us_o = [600.0 + i for i in range(7)]
    us_c = [601.0 + i for i in range(7)]
    fx_c = {d: 1380.0 + 2 * i for i, d in enumerate(fx_days)}
    calls = []

    def fake(tickers, start, end):
        calls.append((tickers, start, end))
        if tickers == ["SPY"]:
            return _frame("SPY", us_days, us_o, us_c)
        return _frame("KRW=X", fx_days, [v - 1.0 for v in fx_c.values()], list(fx_c.values()))
    with _seams(_yf_download=fake):
        s = bars.load_leg(_plan("kis", "SPY"), US, NOW)
    assert calls == [(["SPY"], START.isoformat(), "2026-10-23"), (["KRW=X"], START.isoformat(), "2026-10-22")], calls
    fx = {"2026-10-15": fx_c["2026-10-15"], "2026-10-16": fx_c["2026-10-16"], "2026-10-18": fx_c["2026-10-16"],
          "2026-10-19": fx_c["2026-10-19"], "2026-10-20": fx_c["2026-10-20"], "2026-10-21": fx_c["2026-10-21"],
          "2026-10-22": fx_c["2026-10-21"]}                          # FX(x): the last final bar on or before x
    keep = [2, 3, 4, 5, 6]                                           # 10-14 and 10-15 have no FX(d - 1)
    before = {"2026-10-16": "2026-10-15", "2026-10-19": "2026-10-18", "2026-10-20": "2026-10-19",
              "2026-10-21": "2026-10-20", "2026-10-22": "2026-10-21"}
    dates = tuple(us_days[i] for i in keep)
    opens = tuple(us_o[i] * fx[before[us_days[i]]] for i in keep)
    closes = tuple(us_c[i] * fx[us_days[i]] for i in keep)
    fx_part = bars.Part(symbol="KRW=X", source="YAHOO", dates=tuple(fx_days[:-1]),
                        open=tuple(fx_c[d] - 1.0 for d in fx_days[:-1]), close=tuple(fx_c[d] for d in fx_days[:-1]),
                        adjustment="")
    us_part = bars.Part(symbol="SPY", source="YAHOO", dates=tuple(us_days), open=tuple(us_o), close=tuple(us_c),
                        adjustment="total")
    assert s == P.Series(symbol="SPY", source="YAHOO:SPY*YAHOO:KRW=X", dates=dates, open=opens, close=closes,
                         adjustment="total", status="final",
                         md5=P.series_md5("SPY", "YAHOO:SPY*YAHOO:KRW=X", dates, opens, closes, "total", "final"),
                         components=(("YAHOO:SPY", bars.part_md5(us_part)), ("YAHOO:KRW=X", bars.part_md5(fx_part))),
                         proxy_dates=None), s


def test_the_okx_composite_uses_krw_usdt_and_krw_x_before_it():
    """O7, Q35: BTCUSDT x KRW-USDT on the same UTC date; before the first KRW-USDT candle, KRW=X with FX(d - 1) and
    FX(d), recorded as proxy_dates; a later date with no KRW-USDT candle is dropped. With KRW-USDT on every date the
    FX feed is never asked (its seam would raise)."""
    btc_days = _dates(date(2026, 10, 10), date(2026, 10, 22))
    usdt_days = [d for d in _dates(date(2026, 10, 15), date(2026, 10, 22)) if d != "2026-10-18"]
    fx_days = _dates(date(2026, 10, 8), date(2026, 10, 22))
    btc_o = {d: 100_000.0 + i for i, d in enumerate(btc_days)}
    btc_c = {d: 100_500.0 + i for i, d in enumerate(btc_days)}
    usdt_o = {d: 1390.0 + i for i, d in enumerate(usdt_days)}
    usdt_c = {d: 1391.0 + i for i, d in enumerate(usdt_days)}
    fx_c = {d: 1370.0 + i for i, d in enumerate(fx_days)}
    asked = []

    def upbit(market, n):
        asked.append(market)
        return _candles(usdt_days, [usdt_o[d] for d in usdt_days], [usdt_c[d] for d in usdt_days])

    def binance(symbol, n):
        asked.append(symbol)
        return _candles(btc_days, [btc_o[d] for d in btc_days], [btc_c[d] for d in btc_days])

    def yf(tickers, start, end):
        asked.append(tickers[0])
        return _frame("KRW=X", fx_days, [v - 1.0 for v in fx_c.values()], list(fx_c.values()))
    with _seams(_upbit_daily=upbit, _binance_daily=binance, _yf_download=yf):
        s = bars.load_leg(_plan("okx", "BTC"), CRYPTO, NOW)
    assert asked == ["BTCUSDT", "KRW-USDT", "KRW=X"], asked
    before = {d: (date.fromisoformat(d) - timedelta(days=1)).isoformat() for d in btc_days}
    want = [(d, btc_o[d] * fx_c[before[d]], btc_c[d] * fx_c[d]) for d in btc_days if d < "2026-10-15"]
    want += [(d, btc_o[d] * usdt_o[d], btc_c[d] * usdt_c[d]) for d in btc_days if d in usdt_o]
    assert s.dates == tuple(w[0] for w in want) and "2026-10-18" not in s.dates, s.dates
    assert s.open == tuple(w[1] for w in want) and s.close == tuple(w[2] for w in want)
    assert (s.symbol, s.source, s.adjustment, s.status) == ("BTC", "BINANCE:BTCUSDT*UPBIT:KRW-USDT", "", "final"), s
    assert s.proxy_dates == ("2026-10-10", "2026-10-14"), s.proxy_dates
    fx_final = [d for d in fx_days if d <= "2026-10-21"]              # KRW=X x is final from 00:00Z of x + 2
    parts = (bars.Part(symbol="BTCUSDT", source="BINANCE", dates=tuple(btc_days), open=tuple(btc_o.values()),
                       close=tuple(btc_c.values()), adjustment=""),
             bars.Part(symbol="KRW-USDT", source="UPBIT", dates=tuple(usdt_days), open=tuple(usdt_o.values()),
                       close=tuple(usdt_c.values()), adjustment=""),
             bars.Part(symbol="KRW=X", source="YAHOO", dates=tuple(fx_final),
                       open=tuple(fx_c[d] - 1.0 for d in fx_final), close=tuple(fx_c[d] for d in fx_final),
                       adjustment=""))
    labels = ("BINANCE:BTCUSDT", "UPBIT:KRW-USDT", "YAHOO:KRW=X")
    assert s.components == tuple(zip(labels, map(bars.part_md5, parts))), s.components
    assert s.md5 == P.series_md5("BTC", s.source, s.dates, s.open, s.close, "", "final"), s.md5
    with _seams(_upbit_daily=lambda m, n: _candles(btc_days, [1.0] * len(btc_days), [2.0] * len(btc_days)),
                _binance_daily=binance):
        full = bars.load_leg(_plan("okx", "BTC", date(2026, 10, 24)), CRYPTO, datetime(2026, 10, 24, 9, 0, tzinfo=KST))
    assert full.proxy_dates is None and [lb for lb, _m in full.components] == ["BINANCE:BTCUSDT", "UPBIT:KRW-USDT"]
    assert full.close == tuple(btc_c[d] * 2.0 for d in btc_days), full.close

    # P63: needed historical proxy data cannot silently vanish on an FX outage.
    with _seams(_upbit_daily=upbit, _binance_daily=binance,
                _yf_download=lambda tickers, start, end: _frame("KRW=X", [], [], [])):
        err = _raises(lambda: bars.load_leg(_plan("okx", "BTC"), CRYPTO, NOW, refetch=True), RuntimeError)
    assert "FX proxy" in str(err), err


# --------------------------------------------------------------------------- #
# The cache (Q13, Q36)
# --------------------------------------------------------------------------- #
def _counting_upbit(calls: list, step: float = 0.0):
    days = _dates(date(2026, 10, 1), date(2026, 10, 22))

    def fake(market, n):
        calls.append(market)
        return _candles(days, [1000.0 + step + i for i in range(len(days))],
                        [1001.0 + step + i for i in range(len(days))])
    return fake


@contextlib.contextmanager
def _cache_off():
    """TRADEGEN_ODDS_BARS_CACHE=0 for the block, the previous value restored afterwards."""
    saved = os.environ.get(bars.CACHE_ENV)
    os.environ[bars.CACHE_ENV] = "0"
    try:
        yield
    finally:
        if saved is None:
            os.environ.pop(bars.CACHE_ENV, None)
        else:
            os.environ[bars.CACHE_ENV] = saved


def test_the_cache_round_trips_and_is_keyed_by_window():
    calls = []
    with _seams(_upbit_daily=_counting_upbit(calls)):
        first = bars.load_leg(_plan("upbit", "BTC"), CRYPTO, NOW)
        again = bars.load_leg(_plan("upbit", "BTC"), CRYPTO, NOW)
    assert first == again and calls == ["KRW-BTC"], calls             # the second load reads the cache
    name = f"UPBIT_KRW-BTC_{START.isoformat()}_{DAY.isoformat()}.json"
    path = bars.cache_dir() / name
    raw = path.read_bytes()
    doc = json.loads(raw)
    assert raw == (model.canonical_json(doc) + "\n").encode("utf-8") and doc["fetched_utc"] == "2026-10-23T00:00:00Z"
    assert doc["dates"] == list(first.dates) and doc["status"] == "final" and doc["adjustment"] == ""
    manifest = (bars.cache_dir() / "MANIFEST.jsonl").read_text(encoding="utf-8").splitlines()
    assert manifest == [model.canonical_json({"file": name, "sha256": model.sha256_hex(raw)})], manifest
    assert bars.read_cached("UPBIT", "KRW-BTC", START, DAY).dates == first.dates
    assert bars.read_cached("UPBIT", "KRW-BTC", START + timedelta(days=1), DAY) is None    # another window
    assert bars.read_cached("UPBIT", "KRW-BTC", START, DAY - timedelta(days=1)) is None
    assert bars._cache_name("YAHOO", "KRW=X", START, DAY) == f"YAHOO_KRW=X_{START.isoformat()}_2026-10-23.json"
    assert bars._cache_name("KIS", "A/B C", START, DAY).startswith("KIS_A_B_C_")


def test_the_cache_key_ends_at_the_first_bar_not_yet_final():
    """Q13: a pull made while the 2026-10-22 candle still ran (08:59:59 KST) is keyed by end 2026-10-22, so the run at
    09:00 KST, when that candle is final, fetches again instead of reusing the shorter pull."""
    calls, late = [], datetime(2026, 10, 23, 8, 59, 59, tzinfo=KST)
    with _seams(_upbit_daily=_counting_upbit(calls)):
        early = bars.load_leg(_plan("upbit", "BTC"), CRYPTO, late)
        final = bars.load_leg(_plan("upbit", "BTC"), CRYPTO, NOW)
    assert calls == ["KRW-BTC", "KRW-BTC"], calls
    assert early.dates[-1] == "2026-10-21" and final.dates[-1] == "2026-10-22", (early.dates[-1:], final.dates[-1:])
    for end in ("2026-10-22", "2026-10-23"):
        assert (bars.cache_dir() / f"UPBIT_KRW-BTC_{START.isoformat()}_{end}.json").is_file(), end


def test_an_empty_pull_is_never_cached():
    """yfinance reports a failed download as an empty frame, not an error: such a pull is never pinned, so the next run
    asks again (the core refuses the empty series, DATA_INVALID sub `series`)."""
    with _seams(_yf_download=lambda tickers, start, end: _frame(tickers[0], [], [], [])):
        s = bars.load_leg(_plan("kis", "SPY"), US, NOW)
    assert s.dates == () and not bars.cache_dir().exists(), s


def test_the_cache_fails_closed_on_a_file_that_disagrees_with_its_manifest():
    with _seams(_upbit_daily=_counting_upbit([])):
        bars.load_leg(_plan("upbit", "BTC"), CRYPTO, NOW)
    path = bars.cache_dir() / f"UPBIT_KRW-BTC_{START.isoformat()}_{DAY.isoformat()}.json"
    raw = path.read_bytes()
    path.write_bytes(raw.replace(b'"close":[1001.0', b'"close":[9001.0'))
    err = _raises(lambda: bars.read_cached("UPBIT", "KRW-BTC", START, DAY), RuntimeError)
    assert "sha256 differs" in str(err), err
    _raises(lambda: bars.load_leg(_plan("upbit", "BTC"), CRYPTO, NOW), RuntimeError)   # never refetched silently
    manifest = bars.cache_dir() / "MANIFEST.jsonl"
    manifest.write_text("not json\n", encoding="utf-8")
    _raises(lambda: bars.read_cached("UPBIT", "KRW-BTC", START, DAY), RuntimeError)
    for malformed in ({"file": path.name}, {"file": path.name, "sha256": "a", "extra": 1},
                      {"file": path.name, "sha256": True}, [], None):
        manifest.write_text(json.dumps(malformed) + "\n", encoding="utf-8")
        _raises(lambda: bars.read_cached("UPBIT", "KRW-BTC", START, DAY), RuntimeError)
    manifest.write_text("", encoding="utf-8")
    assert bars.read_cached("UPBIT", "KRW-BTC", START, DAY) is None    # a file without its line reads as missing


def test_the_cache_fails_closed_on_a_pinned_file_that_is_not_that_part():
    """Q36: a file whose bytes match their manifest line but which is not a final part of the asked source and symbol
    (sorted dates inside the key's window, prices > 0, the source's adjustment) raises; so does another symbol whose
    file name collides ("KRW BTC" and "KRW_BTC" both become KRW_BTC)."""
    good = bars.Part(symbol="KRW-BTC", source="UPBIT", dates=("2026-10-20", "2026-10-21"), open=(1.0, 2.0),
                     close=(1.5, 2.5), adjustment="")
    bars.write_cached(good, START, DAY, NOW)
    assert bars.read_cached("UPBIT", "KRW-BTC", START, DAY) == good
    for bad in (dataclasses.replace(good, status="provisional"), dataclasses.replace(good, dates=good.dates[::-1]),
                dataclasses.replace(good, close=(1.5, -2.5)), dataclasses.replace(good, adjustment="total"),
                dataclasses.replace(good, close=(1.5,)), dataclasses.replace(good, open=(True, 2.0)),
                dataclasses.replace(good, dates=("2026-10-20", "2026-10-20")),
                dataclasses.replace(good, open=(10**400, 2.0)),
                dataclasses.replace(good, dates=("2016-10-24", "2026-10-21")),      # before the window start
                dataclasses.replace(good, dates=("2026-10-20", "2026-10-23"))):     # on the key's end
        bars.write_cached(bad, START, DAY, NOW)                        # pinned: its manifest line is the last one
        err = _raises(lambda: bars.read_cached("UPBIT", "KRW-BTC", START, DAY), RuntimeError)
        assert "not a cached part of UPBIT KRW-BTC" in str(err), (bad, err)
    path = bars.write_cached(good, START, DAY, NOW)
    document = json.loads(path.read_bytes())
    variants = [{k: v for k, v in document.items() if k != "close"}, {**document, "extra": 1},
                {**document, "dates": None}, {**document, "source": "KIS"}]
    for malformed in variants:
        raw = (json.dumps(malformed) + "\n").encode("utf-8")
        path.write_bytes(raw)
        (bars.cache_dir() / "MANIFEST.jsonl").write_text(
            model.canonical_json({"file": path.name, "sha256": model.sha256_hex(raw)}) + "\n", encoding="utf-8")
        _raises(lambda: bars.read_cached("UPBIT", "KRW-BTC", START, DAY), RuntimeError)
    bars.write_cached(dataclasses.replace(good, symbol="KRW BTC"), START, DAY, NOW)
    err = _raises(lambda: bars.read_cached("UPBIT", "KRW_BTC", START, DAY), RuntimeError)
    assert "not a cached part of UPBIT KRW_BTC" in str(err), err


def test_the_cache_is_skipped_when_switched_off_and_on_refetch():
    """TRADEGEN_ODDS_BARS_CACHE=0 skips the write and the read (an existing cache file is not read); refetch skips
    the read and appends a manifest line, which wins from then on."""
    calls = []
    with _cache_off(), _seams(_upbit_daily=_counting_upbit(calls)):
        bars.load_leg(_plan("upbit", "BTC"), CRYPTO, NOW)
        bars.load_leg(_plan("upbit", "BTC"), CRYPTO, NOW)
    assert len(calls) == 2 and not bars.cache_dir().exists(), calls  # neither read nor written
    with _seams(_upbit_daily=_counting_upbit(calls)):
        bars.load_leg(_plan("upbit", "BTC"), CRYPTO, NOW)              # cached now
    with _cache_off(), _seams(_upbit_daily=_counting_upbit(calls, step=7.0)):
        off = bars.load_leg(_plan("upbit", "BTC"), CRYPTO, NOW)        # the cached file is not read
    assert len(calls) == 4 and off.open[0] == 1007.0, (calls, off.open[:1])
    with _seams(_upbit_daily=_counting_upbit(calls, step=5.0)):
        fresh = bars.load_leg(_plan("upbit", "BTC"), CRYPTO, NOW, refetch=True)
    with _seams():
        cached = bars.load_leg(_plan("upbit", "BTC"), CRYPTO, NOW)  # the last manifest line wins; no fetch
    assert len(calls) == 5 and fresh == cached and fresh.open[0] == 1005.0, (calls, fresh.open[:1])
    lines = (bars.cache_dir() / "MANIFEST.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2 and json.loads(lines[0])["file"] == json.loads(lines[1])["file"], lines


def test_the_cache_writes_only_through_checked_target():
    """A0: bars.cache_dir() runs state_root()'s link scan first, on a clean temp home (memoised), so the refusal
    below comes from checked_target on the file itself: a hard-linked cache file is never rewritten."""
    base = bars.cache_dir()
    part = bars.Part(symbol="KRW-BTC", source="UPBIT", dates=("2026-10-21",), open=(1.0,), close=(2.0,), adjustment="")
    path = bars.write_cached(part, START, DAY, NOW)
    os.link(path, base / "second_name.json")
    before = path.read_bytes()
    err = _raises(lambda: bars.write_cached(part, START, DAY, NOW), RuntimeError)
    assert "writing it would change another file" in str(err), err
    assert path.read_bytes() == before and not (base / f"{path.name}.tmp").exists()


def test_the_tmp_and_the_manifest_are_checked_too():
    """A0 for the two other targets of write_cached: a hard-linked MANIFEST.jsonl or a hard-linked leftover .tmp is
    refused before anything is written."""
    base = bars.cache_dir()
    part = bars.Part(symbol="KRW-BTC", source="UPBIT", dates=("2026-10-21",), open=(1.0,), close=(2.0,), adjustment="")
    path = bars.write_cached(part, START, DAY, NOW)
    manifest, tmp = base / "MANIFEST.jsonl", base / f"{path.name}.tmp"
    os.link(manifest, base / "manifest_copy.jsonl")
    before = (path.read_bytes(), manifest.read_bytes())
    err = _raises(lambda: bars.write_cached(part, START, DAY, NOW), RuntimeError)
    assert "odds bars MANIFEST" in str(err) and "writing it would change another file" in str(err), err
    os.remove(base / "manifest_copy.jsonl")
    tmp.write_bytes(b"left over")
    os.link(tmp, base / "tmp_copy")
    err = _raises(lambda: bars.write_cached(part, START, DAY, NOW), RuntimeError)
    assert "odds bars cache tmp" in str(err) and "writing it would change another file" in str(err), err
    assert (path.read_bytes(), manifest.read_bytes()) == before and tmp.read_bytes() == b"left over"


def test_the_bars_paths_stay_under_the_tradegen_home():
    """The odds twin of macro_m0_rules.test_every_state_path_stays_out_of_quantgen: with TRADEGEN_HOME unset the
    cache and the yfinance folder resolve under ~/.tradegen and nothing is created; a home inside QUANTGEN is refused
    before any I/O."""
    from core import isolation
    real = Path.home() / ".tradegen"
    existed = (real / "odds").exists()
    saved = os.environ.pop("TRADEGEN_HOME")
    try:
        for p in (bars.cache_dir(), bars.odds_dir() / "yfinance"):
            assert p.resolve().is_relative_to(real.resolve()), p
        os.environ["TRADEGEN_HOME"] = str(isolation.QUANTGEN_STATE / "odds_home")
        _raises(bars.cache_dir, RuntimeError)
    finally:
        os.environ["TRADEGEN_HOME"] = saved
    assert (real / "odds").exists() == existed
