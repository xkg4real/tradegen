"""Daily price history, from whichever provider can actually serve it.

Three sources, one shape:

  * **FMP** — `/stable/historical-price-eod/dividend-adjusted` for US (and,
    plan permitting, international) tickers: closes adjusted for splits AND
    dividends. (`/full` carries no `adjClose` on the stable API — probed
    2026-10-02 — so reading it gave split-only prices.)
  * **KIS** — daily OHLCV for KRX codes (6-digit tickers), through the same
    client the NEXTGEN base uses for the KRX page.
  * **SYNTHETIC** — a seeded geometric Brownian motion path derived from the
    symbol name. Deterministic per symbol, so charts and tests are stable.
    This is what makes every analysis screen in QUANTGEN work with zero keys
    configured; the result carries `source="SYNTHETIC"` and a note saying so,
    because a simulated series silently passed off as market data would poison
    every number computed downstream.

Provider answers are remembered on disk (`_cached`) for the FICC cache TTL, so
re-running an analysis does not spend quota on bars that have not changed. A
cached series says so in its `note`.

`load_history` picks a provider automatically (KIS for 6-digit codes, FMP for
everything else, synthetic as the explicit or last-resort fallback) and always
answers with a `History` whose `source` and `note` say where the prices came
from and why.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import time
from dataclasses import dataclass, field, replace
from datetime import date, datetime, timedelta, timezone

import numpy as np

try:
    from data.net import session as _requests        # shared session: retry + backoff
except Exception:                                    # pragma: no cover
    _requests = None

import config
from core import markets
from core.isolation import checked_target

TRADING_DAYS = 252


class HistoryError(RuntimeError):
    """A provider was asked and could not answer. The message says why."""


@dataclass(frozen=True)
class History:
    symbol: str
    source: str                       # "FMP" | "KIS" | "YFINANCE" | "UPBIT" | "BINANCE" | "SYNTHETIC"
    dates: tuple[str, ...]            # ISO dates, ascending
    closes: tuple[float, ...]
    note: str = ""
    # "total" = adjusted for splits AND dividends (a total-return series);
    # "split" = adjusted for splits only (a price-return series);
    # ""      = not applicable (index, FX, futures, crypto, synthetic) or unknown.
    adjustment: str = ""
    # M1 provenance (appended with a default so positional construction keeps working):
    # "provisional_intraday" = fetched while the market may have been trading, the last bar is a running price;
    # ""                     = no status claimed (a History is a display shape; acting reads use core.ficc.pit).
    status: str = ""

    def __len__(self) -> int:
        return len(self.closes)

    @property
    def last(self) -> float:
        return self.closes[-1]

    @property
    def first_date(self) -> str:
        return self.dates[0] if self.dates else ""

    @property
    def last_date(self) -> str:
        return self.dates[-1] if self.dates else ""

    def prices(self) -> np.ndarray:
        return np.asarray(self.closes, dtype=float)

    def log_returns(self) -> np.ndarray:
        px = self.prices()
        return np.diff(np.log(px))

    def simple_returns(self) -> np.ndarray:
        px = self.prices()
        return px[1:] / px[:-1] - 1.0


def _clean_rows(rows: list[tuple[str, float]]) -> tuple[tuple[str, ...], tuple[float, ...]]:
    rows = [(d, c) for d, c in rows if c is not None and c > 0]
    rows.sort(key=lambda r: r[0])
    dates = tuple(d for d, _ in rows)
    closes = tuple(float(c) for _, c in rows)
    return dates, closes


def convention_warning(hists) -> str:
    """One sentence when a panel mixes total-return and price-return series,
    "" when it does not. Their returns differ by the dividend yield, which an
    optimiser reads as a difference between the assets."""
    total = [h.symbol for h in hists if h.adjustment == "total"]
    split = [h.symbol for h in hists if h.adjustment == "split"]
    if not (total and split):
        return ""
    return (f"Mixed return conventions: {', '.join(total)} include reinvested dividends, "
            f"{', '.join(split)} are price-only (dividends not included). Their returns differ "
            f"by the dividend yield, so weights and comparisons are tilted toward the first group. "
            f"To compare like with like use one convention for every symbol: Yahoo for total return "
            f"(a KRX code as 005930.KS), or KIS for price return (a US ticker as NAS:AAPL).")


# --------------------------------------------------------------------------- #
# FMP
# --------------------------------------------------------------------------- #
def fmp_history(symbol: str, *, days: int = 504) -> History:
    if _requests is None:
        raise HistoryError("The requests package is not installed.")
    key = config.fmp_key()
    if not key:
        raise HistoryError("FMP_API_KEY is not configured.")
    from data.fmp.quote_client import _redact
    start = (date.today() - timedelta(days=int(days * 1.6) + 10)).isoformat()
    url = f"{config.FMP_BASE_URL}/historical-price-eod/dividend-adjusted"
    try:
        resp = _requests.get(url, params={"symbol": symbol, "from": start, "apikey": key},
                             timeout=config.HTTP_TIMEOUT_SECONDS)
    except Exception as exc:
        # The exception text carries the request URL, and the URL carries the key.
        raise HistoryError(f"FMP request failed: {_redact(str(exc), key)}") from None
    if resp.status_code == 402:
        raise HistoryError(f"The FMP plan does not cover {symbol!r} (HTTP 402).")
    if resp.status_code in (401, 403):
        raise HistoryError(f"FMP rejected the API key (HTTP {resp.status_code}).")
    if resp.status_code == 429:
        raise HistoryError("FMP rate limit reached (HTTP 429): the request quota is spent.")
    if resp.status_code != 200:
        raise HistoryError(f"FMP answered HTTP {resp.status_code}.")
    try:
        payload = resp.json()
    except Exception as exc:
        raise HistoryError("FMP returned a non-JSON body.") from exc
    # /stable answers a plain list; older shapes wrap it in {"historical": [...]}.
    records = payload.get("historical") if isinstance(payload, dict) else payload
    if isinstance(payload, dict) and not records:
        # A quota or plan refusal arrives as a JSON object. Reporting it as
        # "no history" would send the operator hunting for a symbol problem.
        message = payload.get("Error Message") or payload.get("message")
        if message:
            raise HistoryError(f"FMP: {_redact(str(message), key)}")
    if not isinstance(records, list) or not records:
        raise HistoryError(f"FMP has no daily history for {symbol!r}.")
    rows = []
    # Decided once for the whole response: taking adjClose on some rows and the
    # raw close on others would splice two price scales into one series.
    dividend_adjusted = any(isinstance(r, dict) and r.get("adjClose") is not None
                            for r in records)
    price_field = "adjClose" if dividend_adjusted else "close"
    dropped = sum(1 for r in records if isinstance(r, dict) and r.get(price_field) is None)
    for rec in records:
        if not isinstance(rec, dict):
            continue
        d = str(rec.get("date") or "")[:10]
        c = rec.get(price_field)
        try:
            c = float(c)
        except (TypeError, ValueError):
            continue
        if d:
            rows.append((d, c))
    dates, closes = _clean_rows(rows)
    if len(closes) < 30:
        raise HistoryError(f"FMP returned only {len(closes)} usable sessions for {symbol!r}.")
    return History(symbol=symbol.upper(), source="FMP",
                   dates=dates[-days:], closes=closes[-days:],
                   note=("FMP close adjusted for splits and dividends" if dividend_adjusted
                         else "FMP close, NOT dividend-adjusted (no adjClose in the response)")
                        + (f"; {dropped} session(s) without {price_field} dropped" if dropped else ""),
                   adjustment="total" if dividend_adjusted else "split")


# --------------------------------------------------------------------------- #
# KIS (KRX codes)
# --------------------------------------------------------------------------- #
def kis_history(code: str, *, days: int = 504) -> History:
    """KIS serves about 100 sessions per call, so the window is paged backwards:
    each call ends the day before the earliest session already held, until
    `days` sessions are in hand or the exchange has nothing older to give."""
    if not config.kis_ready():
        raise HistoryError("KIS credentials are not configured.")
    from data.krx.kis_client import KISClient
    client = KISClient()
    start = (date.today() - timedelta(days=int(days * 1.6) + 10)).strftime("%Y%m%d")
    rows_by_date: dict[str, float] = {}
    end: str | None = None
    for _ in range(days // 100 + 3):                 # a few spare pages for holidays
        try:
            page = client.daily(code, start=start, end=end)
        except Exception as exc:
            raise HistoryError(f"KIS daily history failed: {exc}") from exc
        fresh = [(r["date"], r.get("close")) for r in page
                 if r.get("date") and r["date"] not in rows_by_date]
        if not fresh:
            break
        for d, c in fresh:
            if c is not None and c > 0:
                rows_by_date[d] = float(c)
        if len(rows_by_date) >= days:
            break
        earliest = min(d for d, _ in fresh)
        end = (date.fromisoformat(earliest) - timedelta(days=1)).strftime("%Y%m%d")
        if end < start:
            break
    dates, closes = _clean_rows(list(rows_by_date.items()))
    if len(closes) < 30:
        raise HistoryError(f"KIS returned only {len(closes)} usable sessions for {code!r}.")
    return History(symbol=code, source="KIS", dates=dates[-days:], closes=closes[-days:],
                   note="KIS 수정주가: adjusted for splits and rights, cash dividends not included",
                   adjustment="split")


# --------------------------------------------------------------------------- #
# Synthetic — deterministic per symbol
# --------------------------------------------------------------------------- #
def synthetic_history(symbol: str, *, days: int = 504, seed: int | None = None) -> History:
    """A seeded GBM path with symbol-derived drift, volatility and start price.

    The same symbol always produces the same series, so a demo screen does not
    repaint itself into a different market on every refresh.
    """
    sym = (symbol or "DEMO").upper()
    if seed is None:
        seed = int.from_bytes(hashlib.sha256(sym.encode()).digest()[:4], "big")
    rng = np.random.default_rng(seed)
    # Parameters vary by symbol but stay inside plausible equity ranges.
    mu = 0.02 + (seed % 17) / 100.0            # 2%..18% annual drift
    sigma = 0.14 + (seed % 23) / 100.0         # 14%..36% annual vol
    s0 = 20.0 + (seed % 400)
    dt = 1.0 / TRADING_DAYS
    shocks = rng.normal((mu - 0.5 * sigma**2) * dt, sigma * math.sqrt(dt), size=days - 1)
    log_px = np.concatenate([[math.log(s0)], math.log(s0) + np.cumsum(shocks)])
    closes = tuple(float(x) for x in np.exp(log_px))
    end = date.today()
    ds: list[str] = []
    d = end
    while len(ds) < days:
        if d.weekday() < 5:
            ds.append(d.isoformat())
        d -= timedelta(days=1)
    dates = tuple(reversed(ds))
    return History(symbol=sym, source="SYNTHETIC", dates=dates, closes=closes,
                   note=f"Simulated series (GBM, μ={mu:.0%}, σ={sigma:.0%}) — "
                        "no market data provider was used.")


# --------------------------------------------------------------------------- #
# Yahoo Finance, crypto venues and the other KIS domains (version 3)
# --------------------------------------------------------------------------- #
def yf_history(symbol: str, *, days: int = 504) -> History:
    """Any Yahoo ticker: ETFs (SPY), indices (^VIX), continuous futures (ZN=F),
    FX (KRW=X), crypto (BTC-USD), KRX (005930.KS). Adjusted closes, through the
    FICC data module's single Yahoo touchpoint (patched to raise in tests)."""
    from core.ficc.data import _yf_fetch, _period_for
    try:
        rows = _yf_fetch([symbol], _period_for(days)).get(symbol) or []
    except Exception as exc:
        raise HistoryError(f"Yahoo Finance failed for {symbol!r}: {exc}") from exc
    dates, closes = _clean_rows([(d, c) for d, c in rows])
    if len(closes) < 30:
        raise HistoryError(f"Yahoo Finance returned only {len(closes)} usable sessions for {symbol!r}.")
    s = symbol.upper()
    pays_no_dividend = s.startswith("^") or s.endswith(("=F", "=X", "-USD", "-KRW"))
    return History(symbol=s, source="YFINANCE", dates=dates[-days:], closes=closes[-days:],
                   note="Yahoo adjusted close", adjustment="" if pays_no_dividend else "total")


def crypto_history(symbol: str, *, days: int = 504) -> History:
    """`KRW-BTC` (Upbit, KRW) or `BTCUSDT` (Binance spot, USDT), keyless."""
    from data.crypto.crypto_client import BinancePublic, CryptoError, UpbitPublic
    s = symbol.upper()
    try:
        if s.startswith("KRW-") or s.startswith("BTC-") or s.startswith("USDT-"):
            return UpbitPublic().daily(s, days=days).to_history()
        return BinancePublic().daily(s, days=days).to_history()
    except CryptoError as exc:
        raise HistoryError(str(exc)) from exc


def kis_market_history(symbol: str, *, days: int = 504) -> History:
    """The non-stock KIS domains by symbol shape: `NAS:AAPL` overseas stock,
    `A01612` / `A65612` / `101W12` a KRX futures contract, `KR103501GE31` a bond
    ISIN, `Y0101` a KRW benchmark yield (percent), `FX@KRW` the 원/달러 fixing."""
    if not config.kis_ready():
        raise HistoryError("KIS credentials are not configured.")
    from data.kis_markets import CHART_FX, CHART_YIELD, KISMarkets, OVERSEAS_EXCHANGES
    km = KISMarkets()
    s = symbol.strip().upper()
    try:
        if ":" in s and s.split(":", 1)[0] in OVERSEAS_EXCHANGES:
            ex, sym = s.split(":", 1)
            # MODP=1 is 수정주가: splits, not dividends.
            return replace(km.overseas_daily(ex, sym, days=days).to_history(), adjustment="split")
        if s.startswith("KR") and len(s) == 12:
            return km.bond_daily(s).to_history()
        if s.startswith("Y0") and len(s) == 5:
            return km.overseas_chart(CHART_YIELD, s, days=days).to_history()
        if s.startswith("FX@"):
            return km.overseas_chart(CHART_FX, s, days=days).to_history()
        return km.futures_daily(s, days=days).to_history()
    except Exception as exc:
        raise HistoryError(f"KIS market history failed for {symbol!r}: {exc}") from exc


def _looks_krx(symbol: str) -> bool:
    s = symbol.strip().upper()
    if s.endswith((".KS", ".KQ")):
        s = s.split(".")[0]
    return s.isdigit() and len(s) == 6


def _looks_yahoo(symbol: str) -> bool:
    s = symbol.strip().upper()
    return s.startswith("^") or s.endswith(("=F", "=X", "-USD", "-KRW", ".KS", ".KQ"))


def _looks_crypto(symbol: str) -> bool:
    s = symbol.strip().upper()
    return s.startswith(("KRW-", "USDT-")) or (s.endswith("USDT") and s.isalnum() and 5 <= len(s) <= 12)


def _looks_kis_market(symbol: str) -> bool:
    s = symbol.strip().upper()
    if ":" in s:
        from data.kis_markets import OVERSEAS_EXCHANGES
        return s.split(":", 1)[0] in OVERSEAS_EXCHANGES
    if s.startswith("KR") and len(s) == 12 and s.isalnum():
        return True
    if s.startswith("Y0") and len(s) == 5:
        return True
    if s.startswith("FX@"):
        return True
    return len(s) in (6, 9) and s[0] in "ABCD123" and s[1:3].isdigit() and s[3:].isalnum() and not s.isdigit()


# --------------------------------------------------------------------------- #
# Disk cache — a rerun must not spend provider quota on unchanged bars
# --------------------------------------------------------------------------- #
# Looked up through `config` at call time: tests swap these functions out.
_READY = {"FMP": lambda: bool(config.fmp_key()), "KIS": lambda: config.kis_ready()}
_CACHE_MIN_ROWS = 30


_CACHE_LIVE_TTL = 600.0     # seconds a series fetched while its market may be trading is kept


def _may_be_trading(provider: str, symbol: str, at: datetime | None = None) -> bool:
    """Could the newest bar of this series still be forming at `at` (now)?

    True unless the venue is known to be closed, and to have been closed for an
    hour: a series fetched mid-session ends in a running price rather than a
    close, and the closing print can reach a provider some minutes after the
    bell. Such a series must not be kept for hours as if it were final.
    """
    s = symbol.upper()
    at = at or datetime.now(timezone.utc)
    venue = ""
    if provider == "FMP" and "." not in s:
        venue = "US"
    elif provider == "KIS" and ":" in s:
        venue = "US" if s.split(":")[0] in ("NAS", "NYS", "AMS") else ""
    elif provider in ("KIS", "YFINANCE") and _looks_krx(s):
        venue = "KRX"                 # cash equities only: KRX futures and FX keep other hours
    if venue:
        return any(markets.is_open(venue, t) is not False
                   for t in (at, at - timedelta(minutes=60)))
    # Crypto never closes. FX, futures, indices and foreign listings have no
    # calendar here: assume they may be trading on any weekday, and from
    # Sunday evening UTC when Asia and the futures session reopen.
    return (provider == "CRYPTO" or s.endswith(("-USD", "-KRW")) or at.weekday() < 5
            or (at.weekday() == 6 and at.hour >= 21))


def _traded_since(provider: str, symbol: str, ts: float) -> bool:
    """Has this series' market been open at any point since `ts`? Sampled every
    half hour. A file written with the market closed is one bar short as soon
    as a session has traded after it."""
    t, end = datetime.fromtimestamp(ts, timezone.utc), datetime.now(timezone.utc)
    while t < end:
        if _may_be_trading(provider, symbol, t):
            return True
        t += timedelta(minutes=30)
    return _may_be_trading(provider, symbol, end)


def _cached(provider: str, fetch, symbol: str, days: int) -> History:
    """`fetch(symbol, days=days)`, remembered on disk.

    Same directory and time-to-live as `core.ficc.data` (`TRADEGEN_FICC_CACHE`,
    `NEXTGEN_FICC_CACHE_TTL`; a TTL of 0 switches it off), keyed by
    provider / symbol / days. Four rules:

      * A hit says so: `note` gains "cached <fetch time>", so a stored series
        is never mistaken for a fresh download.
      * A series fetched while its market may be trading is kept for
        `_CACHE_LIVE_TTL` (ten minutes) only: its last bar is a running price.
        Fetched with the market closed, every bar is final and it is kept for
        the full TTL — or until that market trades again, whichever is first.
      * A provider whose credentials are missing is always asked directly. It
        must raise, not answer from an old file.
      * Failures are never stored, and neither is a series too short to be a
        real history.

    ponytail: whole-series refetch on expiry, and no "refetch now" control —
    delete the HIST_*.json file to force one. Fetch only the bars after the
    last stored date if provider quota ever makes that worth the code.
    """
    ttl = float(config.FICC_CACHE_TTL_SECONDS)
    if ttl <= 0 or not _READY.get(provider, lambda: True)():
        return fetch(symbol, days=days)
    name = re.sub(r"[^A-Za-z0-9_.-]", "_", f"HIST_{provider}_{symbol.upper()}_{days}")
    path = config.ficc_cache_dir() / f"{name}.json"
    try:
        p = json.loads(path.read_text("utf-8"))
        # Only an explicit `"live": false` earns the full TTL (a file from
        # before the flag existed does not), and only while the market has not
        # traded since it was written.
        final = p.get("live") is False and not _traded_since(provider, symbol, float(p["ts"]))
        limit = ttl if final else min(ttl, _CACHE_LIVE_TTL)
        if 0 <= time.time() - float(p["ts"]) < limit and len(p["dates"]) == len(p["closes"]):
            stamp = datetime.fromtimestamp(float(p["ts"])).strftime("%Y-%m-%d %H:%M")
            note = "; ".join(x for x in (str(p.get("note") or ""), f"cached {stamp}") if x)
            return History(str(p["symbol"]), str(p["source"]), tuple(p["dates"]),
                           tuple(float(c) for c in p["closes"]), note=note,
                           adjustment=str(p.get("adjustment") or ""),
                           status=str(p.get("status") or ("provisional_intraday" if p.get("live") else "")))
    except Exception:
        pass                                  # absent, expired or unreadable: fetch
    live = _may_be_trading(provider, symbol)  # judged before the request goes out
    h = fetch(symbol, days=days)
    if live and not h.status:
        h = replace(h, status="provisional_intraday")   # M1: a running last bar is never presented as a close
    if len(h) >= _CACHE_MIN_ROWS:
        path = checked_target(path, "history cache")                # A0: outside the try, so a refusal propagates
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps({"ts": time.time(), "live": live, "symbol": h.symbol,
                                        "source": h.source, "note": h.note,
                                        "adjustment": h.adjustment, "status": h.status,
                                        "dates": h.dates, "closes": h.closes}), "utf-8")
        except Exception:
            pass                              # a cache that cannot be written is not an error
    return h


SOURCES = ("auto", "fmp", "kis", "yfinance", "crypto", "synthetic")


def load_history(symbol: str, *, source: str = "auto", days: int = 504) -> History:
    """Fetch daily closes for `symbol`. `source="auto"` routes by the symbol's
    shape: 6-digit KRX codes to KIS; `KRW-BTC` / `BTCUSDT` to Upbit / Binance
    (keyless); `^VIX`, `ZN=F`, `KRW=X`, `BTC-USD` to Yahoo (keyless; a
    `005930.KS` code is a KRX code and goes to KIS — ask for `yfinance`
    explicitly to get Yahoo's dividend-adjusted series); `NAS:AAPL`, KRX derivative codes, bond ISINs and `Y0101`-style
    yields to the KIS asset domains; everything else to FMP, falling back to
    a synthetic series (with an explicit note) when no provider is configured.
    A provider that IS configured but fails raises `HistoryError` instead of
    silently simulating — a network error must not quietly change what the
    numbers mean."""
    symbol = (symbol or "").strip()
    if not symbol:
        raise HistoryError("No symbol given.")
    source = (source or "auto").lower()
    if source == "synthetic":
        return synthetic_history(symbol, days=days)
    if source == "fmp":
        return _cached("FMP", fmp_history, symbol, days)
    if source == "kis":
        return _cached("KIS", kis_market_history if _looks_kis_market(symbol) else kis_history, symbol, days)
    if source == "yfinance":
        return _cached("YFINANCE", yf_history, symbol, days)
    if source == "crypto":
        return _cached("CRYPTO", crypto_history, symbol, days)
    if source != "auto":
        raise HistoryError(f"Unknown source {source!r}. One of {SOURCES}.")
    if _looks_krx(symbol):
        if config.kis_ready():
            return _cached("KIS", kis_history, symbol.split(".")[0], days)
        h = synthetic_history(symbol, days=days)
        return History(h.symbol, h.source, h.dates, h.closes,
                       note="KIS credentials are not configured; " + h.note)
    if _looks_crypto(symbol):
        return _cached("CRYPTO", crypto_history, symbol, days)
    if _looks_yahoo(symbol):
        return _cached("YFINANCE", yf_history, symbol, days)
    if _looks_kis_market(symbol):
        if config.kis_ready():
            return _cached("KIS", kis_market_history, symbol, days)
        h = synthetic_history(symbol, days=days)
        return History(h.symbol, h.source, h.dates, h.closes,
                       note="KIS credentials are not configured; " + h.note)
    if config.fmp_ready():
        return _cached("FMP", fmp_history, symbol, days)
    h = synthetic_history(symbol, days=days)
    return History(h.symbol, h.source, h.dates, h.closes,
                   note="FMP_API_KEY is not configured; " + h.note)
