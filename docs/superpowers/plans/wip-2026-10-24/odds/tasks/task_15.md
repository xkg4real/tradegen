### Task 15: Bars loading in the unsigned package (`core/oddsdata/bars.py`)

**Files:**
- Create: `core/oddsdata/bars.py` (LF, UTF-8, no BOM)
- Test: `tests/odds_bars.py` (create; LF, UTF-8, no BOM)

No existing file is edited, so the DRIFT RULE has nothing to apply here. `tests/odds_acceptance.py` already lists
`odds_bars` in MODULES (Task 1), and its `_wrap` starts patching the four seams the moment `core/oddsdata/bars.py`
is a file.

**Interfaces:**
- Consumes:
  - Task 1 (`tests/odds_acceptance.py`): `SEAMS == ("_kis_daily", "_upbit_daily", "_binance_daily",
    "_yf_download")`; `REAL_SEAMS: dict[str, Callable]` (the real seam functions, recorded from `vars(bars)` the
    first time `_wrap` patches); `_wrap(fn)` (inside `hermetic()` and `temp_home()`, every SEAMS name of
    `core.oddsdata.bars` set to `tests.macro_acceptance._boom` and restored afterwards; Task 1's `_main` runs the
    entries of the imported `tests.odds_acceptance`, so a test reads `tests.odds_acceptance.REAL_SEAMS` under `-m`
    and under `run_all` alike). `tests.macro_acceptance._boom`, `HermeticViolation`.
    `tests.compliance_guards._imports(rel, tree)` yielding `(node, module, names, enclosing functions)` (reused by
    name; the follow-up renames none).
  - Task 5 (`core.odds.plan`, contract 5.1-5.3): `Plan`, `Leg`, `fixed(f)`, `Series` (fields `symbol, source, dates,
    open, close, adjustment, status, md5, components=(), proxy_dates=None`), `series_md5(symbol, source, dates, open_,
    close, adjustment, status) -> str`, `FEEDS` (`(venue, section) -> feed`).
  - Repo (read-only; the follow-up's Task 7 changes only `KISClient.token` and `core/ficc/data.py`'s `_cache_put`,
    neither of which this task calls):
    - `core.isolation.checked_target(path, what, *, within)`, `state_root()`, `QUANTGEN_STATE`;
    - `core.compliance.model.KST`, `canonical_json`, `sha256_hex`, `iso_utc`;
    - `data.krx.kis_client.KISClient().daily(code, *, start, end, adjusted=True) -> list[dict]`: ascending rows
      `{date (ISO), open, high, low, close, volume, source}` with None for a blank field, at most 100 rows a call,
      dates YYYYMMDD (kis_client.py:273-306);
    - `data.crypto.crypto_client.UpbitPublic().daily(market, *, days)` and `BinancePublic().daily(symbol, *, days)`:
      a `Candles` whose `.dates` are UTC dates and whose `.open` and `.close` are float tuples (a missing Upbit field
      reads 0.0; crypto_client.py:137-163, 192-226);
    - yfinance 1.4.1: `download(tickers, start=, end=, auto_adjust=, progress=, threads=, multi_level_index=)` (end
      exclusive; columns a (Price, Ticker) MultiIndex; a tz-naive daily index) and `set_tz_cache_location(dir)`.
- Produces (`core/oddsdata/bars.py`, contract section 11), for Task 18's CLI:
  - constants `HISTORY_DAYS = 3650`, `KIS_PAGE = 100`, `KIS_MAX_PAGES = 60`, `FX_TICKER = "KRW=X"`,
    `ET = zoneinfo.ZoneInfo("America/New_York")`, `CACHE_ENV = "TRADEGEN_ODDS_BARS_CACHE"` (exactly contract 11.2);
  - the seams `_kis_daily(code, start, end) -> list[dict]`, `_upbit_daily(market, days)`, `_binance_daily(symbol,
    days)`, `_yf_download(tickers, start, end)`, each importing its client inside its body;
  - paths `odds_dir() -> Path` (`state_root() / "odds"`), `cache_dir() -> Path` (`odds_dir() / "bars"`), `_yf_dir()
    -> Path` (checked, then created); each resolved at call time;
  - finality `final_crypto(d, now)`, `final_krx(d, now)`, `final_us(d, now)`, `final_fx(x, now) -> bool`;
  - `Part` (frozen, kw_only: `symbol, source, dates, open, close, adjustment, status="final"`), `part_md5(part) ->
    str`;
  - `kis_part(code, start, end, now)`, `upbit_part(market, start, end, now)`, `binance_part(symbol, start, end,
    now)`, `yahoo_part(ticker, start, end, now) -> Part`: the rows dated in `[start, end)`, final at `now`, with
    open and close finite and > 0;
  - the cache `read_cached(source, symbol, start, end) -> Part | None` and `write_cached(part, start, end, now) ->
    Path`;
  - `load_leg(plan, inst, now, *, refetch: bool = False) -> plan.Series` (`inst` is the leg's `rules.Instrument`;
    only `inst.section` is read; ValueError for a naive `now` or a leg no feed serves);
  - module-private (contract section 0, listed here): `_UTC` (`timezone.utc`), `_MANIFEST` (`"MANIFEST.jsonl"`),
    `_final_for`, `_final_end`, `_price`, `_iso`, `_ymd`, `_days_back`, `_make_part`, `_frame_rows`, `_cache_on`,
    `_cache_name`, `_manifest`, `_part_from(raw, source, symbol, start, end, name)`, `_cached_part`, `_rows`,
    `_day_before`, `_fx_at`, `_joined`, `_series`, `_okx_btc`, `_UNSAFE`, `_PART_KEYS`.

**Plan decisions used:** Q6 (finality instants, US dating, KRW=X), Q7 (feeds per venue), Q13 (seams, cache, yfinance
tz cache, harness), Q23 (`HISTORY_DAYS`), Q35 (KRW composition, FX(x), FX finality, `proxy_dates`), Q36 (cache
format, fail closed), Q40 (the wrapper and `REAL_SEAMS`); RULINGS O1, O6, O7, O13.

Design notes (read before Step 3):
- The window is `[plan.start - HISTORY_DAYS, plan.start)`. Finality grows with the date, so "drop every bar that is
  not final" is the same as cutting the window's end back to the first date that is not final (`_final_end`). A
  date that is not final is never even asked of KIS or yfinance.
- The cache key `(source, symbol, start, end)` uses that cut end. A pull cached while the last bar was still running
  is never reused once the bar is final: the next run asks for a longer window under a new file name. Within one
  key the cache pins the pull (reruns reproduce); `--refetch` bypasses the read, and `TRADEGEN_ODDS_BARS_CACHE=0`
  bypasses the read and the write.
- Nothing falls back: a feed that raises propagates (the CLI exits 4), and the file holds no synthetic route, so the
  loader never produces what the core refuses as SYNTHETIC_REFUSED. The core still checks shapes, dates, staleness
  and the md5 itself (Q39).
- An OKX leg asks for KRW=X only when some BTCUSDT date precedes the first KRW-USDT candle; a later date without a
  KRW-USDT candle is dropped, never priced through FX.
- Every write follows `checked_target` in the same function: the cache file, its `.tmp` and `MANIFEST.jsonl` (each
  `within=cache_dir()`) before the mkdir, and the yfinance folder before its mkdir. Nothing is memoised, so a refused
  write leaves no in-memory state behind (the FICC memo minor of DIGEST 5.4).
- A cache file whose bytes differ from their manifest line, a manifest line that is not one, or a pinned file that is
  not a well-formed final part of that source and symbol raises RuntimeError (Q36: fail closed; the owner deletes the
  bars folder). Well-formed means: status `final`, the asked source and symbol, the source's adjustment (`split` for
  KIS, `total` for Yahoo other than KRW=X, empty otherwise), sorted unique ISO dates inside the key's `[start, end)`,
  and open and close finite and > 0. `_UNSAFE` maps several symbols to one file name ("KRW BTC" and "KRW_BTC"), so
  the symbol check is what stops one symbol from reading another's prices.
- An empty pull is never cached: yfinance reports a failed download as an empty frame, not an error, and pinning it
  would keep a brief outage for the whole window. The core refuses the empty series (DATA_INVALID sub `series`:
  Task 5's `_series_problem` needs at least two dates; sub `empty` is a horizon with no session).
- Series dates are each feed's own date: the KRX date for KIS, the New York date for US bars, Yahoo's own date for
  KRW=X, the UTC date for crypto. Spec 4 "Bars" says US and FX bars are mapped to the Asia/Seoul date of their close;
  this plan keeps the market date in the series and applies the Seoul close date d + 1 where `simulate` dates a check
  (Q6, Q22). This is a departure from the spec text, listed under the plan header's "For spec rev 3.3".
- The KRW=X part covers the same window as the leg, so a US row (or an FX-proxied OKX row) whose FX(d - 1) falls
  before the KRW=X part's first date is dropped: with the window starting 2016-10-25, the leg's first date or two.
  Deterministic, and negligible against 3,650 days of history.
- The tests' clock is `NOW = 2026-10-23 09:00 KST`, which is 00:00Z: from that instant the crypto bar of 2026-10-22
  and the KRW=X bar of 2026-10-21 are final, and the New York bar of 2026-10-22 has been final since 05:10 KST.

- [ ] **Step 1: Write the failing tests**

  Create `tests/odds_bars.py` (whole file, LF):

```python
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
                dataclasses.replace(good, dates=("2016-10-24", "2026-10-21")),      # before the window start
                dataclasses.replace(good, dates=("2026-10-20", "2026-10-23"))):     # on the key's end
        bars.write_cached(bad, START, DAY, NOW)                        # pinned: its manifest line is the last one
        err = _raises(lambda: bars.read_cached("UPBIT", "KRW-BTC", START, DAY), RuntimeError)
        assert "not a cached part of UPBIT KRW-BTC" in str(err), (bad, err)
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
```

- [ ] **Step 2: Run to verify it fails**

  Precondition (git and grep only): the tests read `tests.odds_acceptance.REAL_SEAMS` (contract 3.1), which a `-m`
  run fills only when Task 1's `_main` runs the entries of the imported copy, not of `__main__`. From the repo root:

```bash
grep -n "from tests import odds_acceptance as suite" tests/odds_acceptance.py
```

  Expected: one line, inside `_main`. If it prints nothing, stop and rule before going on: three seam-body tests
  would fail with KeyError under `-m` while passing under `run_all`.

  Every Python command of this task runs from the repo root in Git Bash behind the overlap check of contract
  section 0 (the `test -z` prefix; when it prints a process, wait and run the line again):

```bash
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && .venv/Scripts/python.exe -m tests.odds_acceptance odds_bars/
```

  Expected: a traceback, then

```
FAIL odds_bars/import ImportError: cannot import name 'bars' from 'core.oddsdata' (C:\Users\whydi\OneDrive\Desktop\TRADEGEN\core\oddsdata\__init__.py)

0/1 passed, 1 failed, 0 not run
```

  and exit code 1.

- [ ] **Step 3: Implement**

  Create `core/oddsdata/bars.py` (whole file, LF):

```python
"""Unsigned bar loading for the odds engine (spec 4 "Bars", 7.2 "Price series", "Data rules"; O1, O6, O7, O13; Q6,
Q7, Q13, Q35, Q36).

Outside the D14 closure: `core.oddsdata` is not `core.odds`, so the signed core receives these bars as plain data and
recomputes their md5 itself. Only the four seams reach a data client or yfinance; each imports its client inside and
is looked up at call time, so the odds suite patches them. A bar is kept once it is final (crypto d at 00:00Z of
d + 1, KRX d at 15:40 KST, US d at 16:10 New York time, KRW=X x at 00:00Z of x + 2), and a row whose open or close is
missing, not finite or <= 0 is dropped. Nothing here falls back to synthetic data: a feed that fails raises. Every
downloaded part is cached under state_root()/odds/bars, keyed by (source, symbol, start, end), where end is the first
date of the window that is not final yet, and pinned by its sha256 in MANIFEST.jsonl; TRADEGEN_ODDS_BARS_CACHE=0
turns the cache off."""
from __future__ import annotations

import bisect
import dataclasses
import json
import math
import os
import re
import zoneinfo
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from core.compliance import model
from core.isolation import checked_target, state_root
from core.odds import plan as P

HISTORY_DAYS = 3650                    # calendar days of history before the plan's start (Q23)
KIS_PAGE = 100                         # rows one KIS daily call returns at most
KIS_MAX_PAGES = 60
FX_TICKER = "KRW=X"                    # Yahoo's KRW per USD (O6; inside the series hash)
ET = zoneinfo.ZoneInfo("America/New_York")      # built once at import; KST is core.compliance.model.KST
_UTC = timezone.utc
CACHE_ENV = "TRADEGEN_ODDS_BARS_CACHE"
_MANIFEST = "MANIFEST.jsonl"
_UNSAFE = re.compile(r"[^A-Za-z0-9.=-]")
_PART_KEYS = frozenset({"symbol", "source", "dates", "open", "close", "adjustment", "status", "fetched_utc"})


# --------------------------------------------------------------------------- #
# Seams: the only functions that reach a data client or yfinance (looked up at call time)
# --------------------------------------------------------------------------- #
def _kis_daily(code: str, start: str, end: str) -> list[dict]:
    """KIS daily rows of `code` from `start` to `end` (YYYYMMDD, both included), at most KIS_PAGE, split-adjusted."""
    from data.krx import kis_client
    return kis_client.KISClient().daily(code, start=start, end=end, adjusted=True)


def _upbit_daily(market: str, days: int):
    """The last `days` Upbit daily candles of `market` (a crypto_client.Candles)."""
    from data.crypto import crypto_client
    return crypto_client.UpbitPublic().daily(market, days=days)


def _binance_daily(symbol: str, days: int):
    """The last `days` Binance spot daily klines of `symbol` (a crypto_client.Candles)."""
    from data.crypto import crypto_client
    return crypto_client.BinancePublic().daily(symbol, days=days)


def _yf_download(tickers: list[str], start: str, end: str):
    """yfinance daily bars over [start, end) (yfinance's end is exclusive), total-return adjusted, with its time-zone
    cache moved under the odds folder first (never %LOCALAPPDATA%)."""
    import yfinance
    d = _yf_dir()
    yfinance.set_tz_cache_location(str(d))
    return yfinance.download(tickers, start=start, end=end, auto_adjust=True, progress=False, threads=False,
                             multi_level_index=True)


# --------------------------------------------------------------------------- #
# Paths (resolved at call time, so a test's TRADEGEN_HOME moves them; computing a path creates nothing)
# --------------------------------------------------------------------------- #
def odds_dir() -> Path:
    return state_root() / "odds"


def cache_dir() -> Path:
    return odds_dir() / "bars"


def _yf_dir() -> Path:
    base = odds_dir()
    d = checked_target(base / "yfinance", "odds yfinance cache", within=base)
    d.mkdir(parents=True, exist_ok=True)
    return d


# --------------------------------------------------------------------------- #
# Finality (Q6, Q35): fixed instants, no data/macro read
# --------------------------------------------------------------------------- #
def final_crypto(d: date, now: datetime) -> bool:
    """A crypto daily bar dated d spans 00:00Z of d to 00:00Z of d + 1."""
    return now >= datetime(d.year, d.month, d.day, tzinfo=_UTC) + timedelta(days=1)


def final_krx(d: date, now: datetime) -> bool:
    return now >= datetime(d.year, d.month, d.day, 15, 40, tzinfo=model.KST)


def final_us(d: date, now: datetime) -> bool:
    """New York date d, which closes on the Asia/Seoul date d + 1 in EST and EDT alike."""
    return now >= datetime(d.year, d.month, d.day, 16, 10, tzinfo=ET)


def final_fx(x: date, now: datetime) -> bool:
    """The KRW=X bar's close instant is not published (DIGEST open question 1), so a day of margin."""
    return now >= datetime(x.year, x.month, x.day, tzinfo=_UTC) + timedelta(days=2)


def _final_for(source: str, symbol: str):
    if source == "KIS":
        return final_krx
    if source == "YAHOO":
        return final_fx if symbol == FX_TICKER else final_us
    return final_crypto


def _final_end(start: date, end: date, now: datetime, final) -> date:
    """The end of the final part of [start, end): every date before it is final at `now` (finality is monotone)."""
    while end > start and not final(end - timedelta(days=1), now):
        end -= timedelta(days=1)
    return end


# --------------------------------------------------------------------------- #
# Parts: one downloaded series each, final rows only
# --------------------------------------------------------------------------- #
@dataclass(frozen=True, kw_only=True)
class Part:
    """One downloaded series in its own quote (KRW for KIS and Upbit, USD for Yahoo, USDT for Binance)."""
    symbol: str
    source: str
    dates: tuple[str, ...]
    open: tuple[float, ...]
    close: tuple[float, ...]
    adjustment: str
    status: str = "final"


def part_md5(part: Part) -> str:
    return P.series_md5(part.symbol, part.source, part.dates, part.open, part.close, part.adjustment, part.status)


def _price(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value > 0


def _iso(text) -> bool:
    try:
        return isinstance(text, str) and date.fromisoformat(text).isoformat() == text
    except ValueError:
        return False


def _ymd(d: date) -> str:
    return d.isoformat().replace("-", "")


def _days_back(start: date, now: datetime) -> int:
    """Upbit and Binance count daily bars back from now: enough to reach `start`, plus one spare."""
    return max(1, (now.astimezone(_UTC).date() - start).days + 2)


def _make_part(symbol: str, source: str, rows, start: date, end: date, adjustment: str) -> Part:
    """The rows dated in [start, end) whose open and close are finite numbers > 0, one per date, sorted."""
    lo, hi, kept = start.isoformat(), end.isoformat(), {}
    for d, o, c in rows:
        if _iso(d) and lo <= d < hi and _price(o) and _price(c):
            kept[d] = (float(o), float(c))
    dates = tuple(sorted(kept))
    return Part(symbol=symbol, source=source, dates=dates, open=tuple(kept[d][0] for d in dates),
                close=tuple(kept[d][1] for d in dates), adjustment=adjustment)


def kis_part(code: str, start: date, end: date, now: datetime) -> Part:
    """KIS daily rows paged backwards, KIS_PAGE a call and at most KIS_MAX_PAGES calls: each call ends the day before
    the earliest row already held, until a short page, a page with no new date, or the window start."""
    end = _final_end(start, end, now, final_krx)
    rows: dict[str, tuple] = {}
    hi = end - timedelta(days=1)
    for _ in range(KIS_MAX_PAGES):
        if hi < start:
            break
        page = list(_kis_daily(code, _ymd(start), _ymd(hi)) or [])
        fresh = [r for r in page if isinstance(r, dict) and _iso(r.get("date")) and r["date"] not in rows]
        for r in fresh:
            rows[r["date"]] = (r.get("open"), r.get("close"))
        if not fresh or len(page) < KIS_PAGE:
            break
        hi = date.fromisoformat(min(r["date"] for r in fresh)) - timedelta(days=1)
    return _make_part(code, "KIS", [(d, o, c) for d, (o, c) in rows.items()], start, end, "split")


def upbit_part(market: str, start: date, end: date, now: datetime) -> Part:
    end = _final_end(start, end, now, final_crypto)
    rows = []
    if end > start:
        candles = _upbit_daily(market, _days_back(start, now))
        rows = list(zip(candles.dates, candles.open, candles.close))
    return _make_part(market, "UPBIT", rows, start, end, "")


def binance_part(symbol: str, start: date, end: date, now: datetime) -> Part:
    end = _final_end(start, end, now, final_crypto)
    rows = []
    if end > start:
        candles = _binance_daily(symbol, _days_back(start, now))
        rows = list(zip(candles.dates, candles.open, candles.close))
    return _make_part(symbol, "BINANCE", rows, start, end, "")


def yahoo_part(ticker: str, start: date, end: date, now: datetime) -> Part:
    end = _final_end(start, end, now, _final_for("YAHOO", ticker))
    rows = _frame_rows(_yf_download([ticker], start.isoformat(), end.isoformat()), ticker) if end > start else []
    return _make_part(ticker, "YAHOO", rows, start, end, "" if ticker == FX_TICKER else "total")


def _frame_rows(frame, ticker: str) -> list[tuple]:
    """(date, open, close) of a yfinance frame with (Price, Ticker) columns; [] when it lacks the ticker."""
    if frame is None or len(frame) == 0:
        return []
    try:
        opens, closes = frame[("Open", ticker)].tolist(), frame[("Close", ticker)].tolist()
    except KeyError:
        return []
    return [(stamp.date().isoformat(), o, c) for stamp, o, c in zip(frame.index, opens, closes)]


# --------------------------------------------------------------------------- #
# The bars cache (Q13, Q36): the grokteam write_cached pattern
# --------------------------------------------------------------------------- #
def _cache_on() -> bool:
    return os.environ.get(CACHE_ENV, "").strip() != "0"


def _cache_name(source: str, symbol: str, start: date, end: date) -> str:
    return f"{source}_{_UNSAFE.sub('_', symbol)}_{start.isoformat()}_{end.isoformat()}.json"


def _manifest(path: Path) -> dict[str, str]:
    """file name -> sha256, the last line for a name winning; RuntimeError on a line that is not a manifest line."""
    pinned = {}
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        try:
            row = json.loads(line)
            ok = (isinstance(row, dict) and set(row) == {"file", "sha256"}
                  and all(isinstance(v, str) for v in row.values()))
        except ValueError:
            ok = False
        if not ok:
            raise RuntimeError(f"odds bars cache: {path} line {n} is not a manifest line; delete the bars folder")
        pinned[row["file"]] = row["sha256"]
    return pinned


def _part_from(raw: bytes, source: str, symbol: str, start: date, end: date, name: str) -> Part:
    """The pinned part, refused unless it is a final part of (source, symbol) with the source's adjustment, sorted
    unique ISO dates inside [start, end) and finite prices > 0."""
    lo, hi = start.isoformat(), end.isoformat()
    adjustment = {"KIS": "split", "YAHOO": "" if symbol == FX_TICKER else "total"}.get(source, "")
    try:
        doc = json.loads(raw.decode("utf-8"))
        if not isinstance(doc, dict) or set(doc) != _PART_KEYS:
            raise ValueError("not a cached part")
        part = Part(symbol=doc["symbol"], source=doc["source"], dates=tuple(doc["dates"]), open=tuple(doc["open"]),
                    close=tuple(doc["close"]), adjustment=doc["adjustment"], status=doc["status"])
        good = (part.symbol == symbol and part.source == source and part.status == "final"
                and part.adjustment == adjustment and len(part.dates) == len(part.open) == len(part.close)
                and all(_iso(d) and lo <= d < hi for d in part.dates)
                and list(part.dates) == sorted(set(part.dates)) and all(_price(v) for v in part.open + part.close))
    except (UnicodeDecodeError, ValueError, TypeError):
        good = False
    if not good:
        raise RuntimeError(f"odds bars cache {name}: not a cached part of {source} {symbol}; delete it and run again")
    return part


def read_cached(source: str, symbol: str, start: date, end: date) -> Part | None:
    """The cached part of (source, symbol, start, end); None when the cache is off, or the file or its manifest line
    is missing; RuntimeError when the file disagrees with its manifest sha256 or is not that part (fail closed: the
    owner deletes it)."""
    if not _cache_on():
        return None
    base = cache_dir()
    name = _cache_name(source, symbol, start, end)
    path, manifest = base / name, base / _MANIFEST
    if not path.is_file() or not manifest.is_file():
        return None
    pinned = _manifest(manifest).get(name)
    if pinned is None:
        return None
    raw = path.read_bytes()
    if model.sha256_hex(raw) != pinned:
        raise RuntimeError(f"odds bars cache {name}: its sha256 differs from {_MANIFEST}; delete it and run again")
    return _part_from(raw, source, symbol, start, end, name)


def write_cached(part: Part, start: date, end: date, now: datetime) -> Path:
    """Writes `part` as the cache file of (part.source, part.symbol, start, end) and pins its sha256 in the manifest:
    every target checked first (A0), then a tmp file, os.replace, and one appended manifest line."""
    base = cache_dir()
    name = _cache_name(part.source, part.symbol, start, end)
    path = checked_target(base / name, "odds bars cache", within=base)
    tmp = checked_target(base / f"{name}.tmp", "odds bars cache tmp", within=base)
    manifest = checked_target(base / _MANIFEST, "odds bars MANIFEST", within=base)
    raw = (model.canonical_json({**dataclasses.asdict(part), "fetched_utc": model.iso_utc(now)}) + "\n").encode("utf-8")
    base.mkdir(parents=True, exist_ok=True)
    tmp.write_bytes(raw)
    os.replace(tmp, path)
    with open(manifest, "a", encoding="utf-8", newline="\n") as fh:
        fh.write(model.canonical_json({"file": name, "sha256": model.sha256_hex(raw)}) + "\n")
    return path


def _cached_part(fetch, source: str, symbol: str, start: date, end: date, now: datetime, refetch: bool) -> Part:
    """The part from the cache (skipped on refetch), else fetched and, when it holds a row, cached."""
    end = _final_end(start, end, now, _final_for(source, symbol))
    hit = None if refetch else read_cached(source, symbol, start, end)
    if hit is not None:
        return hit
    part = fetch(symbol, start, end, now)
    if part.dates and _cache_on():
        write_cached(part, start, end, now)
    return part


# --------------------------------------------------------------------------- #
# The leg's KRW series (Q7, Q35)
# --------------------------------------------------------------------------- #
def _rows(part: Part):
    return zip(part.dates, part.open, part.close)


def _day_before(d: str) -> str:
    return (date.fromisoformat(d) - timedelta(days=1)).isoformat()


def _fx_at(fx: Part | None, day: str) -> float | None:
    """FX(x): the close of the last final KRW=X bar dated on or before x; None when there is none."""
    i = bisect.bisect_right(fx.dates, day) if fx is not None else 0
    return fx.close[i - 1] if i else None


def _joined(d: str, o: float, c: float, k_open: float | None, k_close: float | None) -> tuple | None:
    if k_open is None or k_close is None or not (_price(o * k_open) and _price(c * k_close)):
        return None
    return d, o * k_open, c * k_close


def _series(symbol: str, source: str, adjustment: str, rows: list, parts: list, proxy=None) -> P.Series:
    dates, opens, closes = (tuple(r[0] for r in rows), tuple(r[1] for r in rows), tuple(r[2] for r in rows))
    return P.Series(symbol=symbol, source=source, dates=dates, open=opens, close=closes, adjustment=adjustment,
                    status="final", md5=P.series_md5(symbol, source, dates, opens, closes, adjustment, "final"),
                    components=tuple((f"{p.source}:{p.symbol}", part_md5(p)) for p in parts), proxy_dates=proxy)


def _okx_btc(get) -> P.Series:
    """BTCUSDT x KRW-USDT on the same UTC date; before the first KRW-USDT candle, KRW=X (FX(d - 1) for the open,
    FX(d) for the close), recorded as proxy_dates. A date after the first KRW-USDT candle without one is dropped."""
    btc, usdt = get(binance_part, "BINANCE", "BTCUSDT"), get(upbit_part, "UPBIT", "KRW-USDT")
    first = usdt.dates[0] if usdt.dates else None
    fx = get(yahoo_part, "YAHOO", FX_TICKER) if any(first is None or d < first for d in btc.dates) else None
    quote = {d: (o, c) for d, o, c in _rows(usdt)}
    rows, proxied = [], []
    for d, o, c in _rows(btc):
        if first is not None and d >= first:
            row = _joined(d, o, c, *quote.get(d, (None, None)))
        else:
            row = _joined(d, o, c, _fx_at(fx, _day_before(d)), _fx_at(fx, d))
            proxied += [d] if row else []
        rows += [row] if row else []
    parts = [btc, usdt] + ([fx] if fx is not None else [])
    return _series("BTC", "BINANCE:BTCUSDT*UPBIT:KRW-USDT", "", rows, parts,
                   (proxied[0], proxied[-1]) if proxied else None)


def load_leg(plan: P.Plan, inst, now: datetime, *, refetch: bool = False) -> P.Series:
    """The KRW series of the plan's leg over [plan.start - HISTORY_DAYS, plan.start), final rows only. `inst` is the
    leg's rules.Instrument from the approved map; ValueError for a leg no feed serves (the core refuses it first)."""
    if not isinstance(now, datetime) or now.utcoffset() is None:
        raise ValueError(f"bars: now must be an aware datetime, got {now!r}")
    leg, end = plan.leg, plan.start
    start = end - timedelta(days=HISTORY_DAYS)

    def get(fetch, source: str, symbol: str) -> Part:
        return _cached_part(fetch, source, symbol, start, end, now, refetch)

    feed = P.FEEDS.get((leg.venue, inst.section))
    if feed == "kis_daily":
        part = get(kis_part, "KIS", leg.symbol)
        return _series(leg.symbol, "KIS", "split", list(_rows(part)), [part])
    if feed == "upbit_daily":
        part = get(upbit_part, "UPBIT", "KRW-" + leg.symbol)
        return _series(part.symbol, "UPBIT", "", list(_rows(part)), [part])
    if feed == "yfinance":
        us, fx = get(yahoo_part, "YAHOO", leg.symbol), get(yahoo_part, "YAHOO", FX_TICKER)
        rows = [_joined(d, o, c, _fx_at(fx, _day_before(d)), _fx_at(fx, d)) for d, o, c in _rows(us)]
        return _series(leg.symbol, f"YAHOO:{leg.symbol}*YAHOO:{FX_TICKER}", "total", [r for r in rows if r], [us, fx])
    if feed == "binance_x_upbit_usdt" and leg.symbol == "BTC":
        return _okx_btc(get)
    raise ValueError(f"bars: no feed serves {leg.venue} {inst.section} {leg.symbol!r}")
```

- [ ] **Step 4: Run to verify it passes**

  Each line below is one command, run on its own from the repo root in Git Bash, with the overlap prefix of Step 2.

```bash
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && .venv/Scripts/python.exe -m tests.odds_acceptance odds_bars/
```

  Expected: 25 `PASS odds_bars/test_...` lines, then `25/25 passed, 0 failed, 0 not run` (exit code 0). The module
  takes about 2 s, plus the one-time import of the hermetic touchpoints (about 3 to 5 s) when it is the first module
  of the run; `test_importing_bars_loads_no_data_client_config_or_yfinance` starts one fresh interpreter (about
  1 s). The odds wrapper's watch must not fire: no test writes outside its temp home.

  The odds guards, which now scan `core/oddsdata/bars.py` (raw words through `compliance_guards._raw_hits`, the
  oddsdata import bans and dynamic imports, the clock only in `run.py`'s `main()`, the `__main__` block only in
  `run.py`, every write after `checked_target`):

```bash
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && .venv/Scripts/python.exe -m tests.odds_acceptance odds_guards/
```

  Expected: no FAIL line, and the same tail Task 1 recorded under "Runs" in the execution ledger (exit code 0). A
  failure names the offending file and text: fix `bars.py`, never the guard.

  The compliance guards (their core-wide raw-word scan, `CORE_RAW_CI`, covers every file of `core/`):

```bash
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && .venv/Scripts/python.exe -m tests.compliance_acceptance compliance_guards/
```

  Expected: no FAIL line and the tail the previous task recorded under "Runs" (exit code 0).

  The core-wide scans (Global Constraints: every task that changes `core/`), one line at a time:

```bash
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && .venv/Scripts/python.exe -m tests.macro_m0_harness
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && .venv/Scripts/python.exe -m tests.macro_tf_gov
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && .venv/Scripts/python.exe -m tests.macro_m7_ledger
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && .venv/Scripts/python.exe -m tests.macro_m8_forward
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && .venv/Scripts/python.exe -m tests.macro_m6_context
```

  Expected: each prints no FAIL line and ends with `0 failed` and exit code 0, with the passed and not-run counts
  Task 1 recorded under "Runs" (T-RO-01 now scans `bars.py` too: no order, withdrawal or deposit route, no order
  client import).

  The cockpit suite (test_08, test_09, test_16, test_18). The restore of the tracked CRLF results file sits after
  `;` on the same line, so it runs even when the suite fails:

```bash
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && KIS_APP_KEY='<unset>' KIS_APP_SECRET='<unset>' KIS_ACCOUNT_8='<unset>' KIS_ACCOUNT_PD='<unset>' UPBIT_ACCESS_KEY='<unset>' UPBIT_SECRET_KEY='<unset>' OKX_API_KEY='<unset>' OKX_API_SECRET='<unset>' OKX_API_PASSPHRASE='<unset>' OPENDART_API_KEY='<unset>' KRX_API_KEY='<unset>' FMP_API_KEY='<unset>' ANTHROPIC_API_KEY='<unset>' GS_CLIENT_ID='<unset>' GS_CLIENT_SECRET='<unset>' FINVIZ_API_KEY='<unset>' ALPACA_API_KEY='<unset>' ALPACA_SECRET_KEY='<unset>' FXMACRODATA_API_KEY='<unset>' .venv/Scripts/python.exe tests/run_all.py --suite cockpit; echo "exit $?"; git checkout -- qa/acceptance_results.json
```

  Expected: the run ends with `0 failed` and the counts Task 1 recorded, then `exit 0`.

  Then (git only; no overlap check needed):

```bash
git status --short
```

  Expected: exactly `?? core/oddsdata/bars.py`, `?? tests/odds_bars.py` and
  `?? docs/superpowers/plans/2026-10-24-odds-engine-execution-ledger.md`. Append the tails of these runs, one line
  each, under "Runs" in the execution ledger (LF; it stays untracked).

- [ ] **Step 5: Commit**

```bash
git add core/oddsdata/bars.py tests/odds_bars.py
git diff --cached --stat
git diff --cached --stat --ignore-cr-at-eol
```

  The two stat outputs must be identical (both files are LF). Then:

```bash
git commit -m "feat(odds): unsigned bar loader with finality, KRW series and the bars cache" -m "Task 15: core/oddsdata/bars.py (four seams, KIS paging, Upbit, Binance and yfinance parts, the US x KRW=X and OKX composites, the checked cache) and tests/odds_bars.py." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
