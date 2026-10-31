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
    try:
        return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value > 0
    except OverflowError:
        return False


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
    if fx is not None and not fx.dates:
        raise RuntimeError("odds bars: required FX proxy history is empty")
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
