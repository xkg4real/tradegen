"""Market data for the FICC core — the only module in `core.ficc` that talks to
a network.

Three sources, one shape:

  * **FRED** — St. Louis Fed, keyless. `pandas_datareader` when installed,
    otherwise the raw `fredgraph.csv` endpoint through `requests`.
  * **YFINANCE** — Yahoo daily closes, keyless; FX spot ("EURUSD=X"), futures
    ("ZN=F"), indices ("^VIX").
  * **SYNTHETIC** — seeded, deterministic per id. What every screen runs on
    when a provider is down or absent, always labeled `source="SYNTHETIC"`
    with a `note` saying which provider failed and why.

Routing mirrors `core.quant.history`: an explicit provider that fails RAISES
`FICCError`; only `source="auto"` degrades to SYNTHETIC. `_fred_fetch` and
`_yf_fetch` are the two — and only two — functions that open a socket; tests
patch them to prove the degradation path without a network.

Simplifications, stated once:
  * FRED rate series arrive in percent. `load_series` returns them RAW;
    `load_treasury_curve` and `load_short_rate` divide by 100 themselves.
    Use `Series.scaled(0.01)` for anything else.
  * "days" means observations for daily series. Monthly series (OECD 3m
    interbank rates) are returned as-is and say "monthly" in their note; no
    forward-fill happens here.
  * Cache: memory + JSON files under `config.ficc_cache_dir()`, TTL
    `config.FICC_CACHE_TTL_SECONDS`, keyed by provider/id/days. Synthetic
    results are never cached. Cache failures are ignored, never raised.
  * Synthetic dates end at today's date (the one `date.today()` in the FICC
    core; pricers never call it). Synthetic *monthly* short rates are dated on
    the first weekday of each month so that consumers which forward-fill by
    date see them over the whole window, not the last n sessions.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import re
import time
from dataclasses import dataclass, field, replace
from datetime import date, datetime as _dt, timedelta, timezone as _tz

import numpy as np

try:
    import pandas_datareader.data as _pdr
except Exception:                                    # pragma: no cover
    _pdr = None
try:
    import yfinance as _yf
except Exception:                                    # pragma: no cover
    _yf = None
try:
    from data.net import session as _requests        # shared session: retry + backoff
except Exception:                                    # pragma: no cover
    _requests = None

import config
from core.ficc.common import TRADING_DAYS, UST_TENORS, FICCError

SOURCES = ("auto", "fred", "yfinance", "synthetic")
G10_KRW = ("USD", "EUR", "JPY", "GBP", "AUD", "CAD", "CHF", "KRW")   # carry universe vs USD

_TREASURY_IDS = ("DGS1MO", "DGS3MO", "DGS6MO", "DGS1", "DGS2", "DGS3", "DGS5", "DGS7",
                 "DGS10", "DGS20", "DGS30")
_IBOR_CC = {"EUR": "EZ", "JPY": "JP", "GBP": "GB", "KRW": "KR", "AUD": "AU", "CAD": "CA",
            "CHF": "CH", "USD": "US"}
_MIN_OBS = 5


# --------------------------------------------------------------------------- #
# Shapes
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Series:
    id: str
    label: str
    source: str                       # "FRED" | "YFINANCE" | "SYNTHETIC"
    dates: tuple[str, ...]            # ISO dates, ascending
    values: tuple[float, ...]
    note: str = ""

    def __len__(self) -> int:
        return len(self.values)

    @property
    def last(self) -> float:
        return self.values[-1]

    @property
    def first_date(self) -> str:
        return self.dates[0] if self.dates else ""

    @property
    def last_date(self) -> str:
        return self.dates[-1] if self.dates else ""

    def array(self) -> np.ndarray:
        return np.asarray(self.values, dtype=float)

    def change(self, n: int) -> float | None:
        """last − value n observations ago; None when the series is too short."""
        if n < 1 or len(self.values) <= n:
            return None
        return self.values[-1] - self.values[-1 - n]

    def window(self, n: int) -> "Series":
        return replace(self, dates=self.dates[-n:], values=self.values[-n:])

    def scaled(self, factor: float) -> "Series":
        return replace(self, values=tuple(v * factor for v in self.values))


@dataclass(frozen=True)
class CurveSnapshot:
    date: str
    source: str
    tenors: tuple[float, ...]
    par_yields: tuple[float, ...]     # decimals
    note: str = ""


@dataclass(frozen=True)
class CurvePanel:
    """A history of par curves: `yields[t, k]` is the decimal yield of tenor k on date t."""
    source: str
    dates: tuple[str, ...]
    tenors: tuple[float, ...]
    yields: np.ndarray = field(repr=False)   # (T, K), NaN-free
    note: str = ""

    def __len__(self) -> int:
        return len(self.dates)

    def at(self, i: int) -> CurveSnapshot:
        return CurveSnapshot(date=self.dates[i], source=self.source, tenors=self.tenors,
                             par_yields=tuple(float(x) for x in self.yields[i]), note=self.note)

    def latest(self) -> CurveSnapshot:
        return self.at(-1)


# --------------------------------------------------------------------------- #
# Readiness
# --------------------------------------------------------------------------- #
def fred_ready() -> bool:
    return _pdr is not None or _requests is not None


def yfinance_ready() -> bool:
    return _yf is not None


# --------------------------------------------------------------------------- #
# Network touchpoints — the only two. Tests patch these.
# --------------------------------------------------------------------------- #
Rows = list[tuple[str, float]]


def _fred_fetch(ids: list[str], start: str) -> dict[str, Rows]:
    """One FRED call for `ids` from ISO `start`. Returns {id: [(date, value)]}, NaN
    and '.' observations dropped. Raises on transport failure."""
    ids = list(ids)
    if _pdr is not None:
        df = _pdr.DataReader(ids, "fred", start)
        out: dict[str, Rows] = {}
        for col in df.columns:
            s = df[col].dropna()
            out[str(col)] = [(str(d)[:10], float(v)) for d, v in s.items()]
        return out
    if _requests is None:
        raise FICCError("Neither pandas_datareader nor requests is installed.")
    out = {}
    for i in ids:
        resp = _requests.get(config.FRED_BASE_URL, params={"id": i, "cosd": start},
                             timeout=config.HTTP_TIMEOUT_SECONDS)
        if resp.status_code != 200:
            raise FICCError(f"FRED answered HTTP {resp.status_code} for {i}.")
        rows: Rows = []
        for rec in csv.DictReader(io.StringIO(resp.text)):
            d = rec.get("observation_date") or rec.get("DATE") or ""
            try:
                v = float(rec.get(i, "."))
            except ValueError:
                continue
            if d and math.isfinite(v):
                rows.append((d[:10], v))
        out[i] = rows
    return out


def _yf_fetch(tickers: list[str], period: str) -> dict[str, Rows]:
    """One yfinance download for `tickers`. Returns {ticker: [(date, close)]}."""
    if _yf is None:
        raise FICCError("yfinance is not installed.")
    tickers = list(tickers)
    df = _yf.download(tickers, period=period, progress=False, auto_adjust=True, threads=False)
    if df is None or len(df) == 0:
        return {}
    close = df["Close"] if "Close" in set(df.columns.get_level_values(0)) else df
    if not hasattr(close, "columns"):                 # single-level frame → Series
        close = close.to_frame(tickers[0])
    out: dict[str, Rows] = {}
    for col in close.columns:
        s = close[col].dropna()
        out[str(col)] = [(str(d)[:10], float(v)) for d, v in s.items()]
    return out


# --------------------------------------------------------------------------- #
# Cache — memory + JSON on disk; never raises
# --------------------------------------------------------------------------- #
_MEM: dict[str, tuple[float, Rows]] = {}
_CACHE_LIVE_TTL = 600.0     # seconds a file whose last row may still be a running bar is served (TASK-M1-12)


def _cache_key(provider: str, id: str, days: int) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]", "_", f"{provider}_{id}_{days}")


def _running_bar(ts: float, rows: Rows) -> bool:
    """True when the newest row is dated on or after the UTC day the file was written: that row was a running
    price at fetch time, not a close (a Yahoo daily frame fetched mid-session already holds today's bar)."""
    if not rows:
        return False
    written = time.strftime("%Y-%m-%d", time.gmtime(ts))
    return str(rows[-1][0])[:10] >= written


def _cache_get(key: str, *, not_before: float | None = None) -> Rows | None:
    """Cached rows, or None.

    Defect fixed here (TASK-M1-12, spec L1283): this cache served any payload younger than the 6-hour TTL, so a
    file written at 10:56 KST on 2026-10-02 holding the running KOSPI print 6,943.66 was served as "the close" of
    2 Oct across the 15:30 close and into the post-close run. Two rules now bind:
      * a payload whose newest row was a running bar when written (`_running_bar`) is served for at most
        `_CACHE_LIVE_TTL` (10 min): it is at best a live_snapshot / provisional_intraday row and expires;
      * `not_before` (epoch seconds; the PIT layer passes close_print_bound_utc(session) + 10 min) refuses any
        payload retrieved at or before it, so a cached row is never served as a session close unless it was
        retrieved after that instant. A refused payload means re-fetch; a failed re-fetch is a MissingInput for the
        store, never the cached row. The file's `ts` is the row's retrieved_at_utc and is kept.
    ponytail: the running-bar test is per file (newest row vs write day), not per session calendar; a post-close
    same-day file is also limited to 10 min, which only costs a re-fetch.
    """
    ttl = float(config.FICC_CACHE_TTL_SECONDS)
    if ttl <= 0:
        return None
    hit = _MEM.get(key)
    if hit is None:
        try:
            payload = json.loads((config.ficc_cache_dir() / f"{key}.json").read_text("utf-8"))
            hit = (float(payload["ts"]), [(str(d), float(v)) for d, v in payload["rows"]])
        except Exception:
            return None
    ts, rows = hit
    if not_before is not None and ts <= float(not_before):
        return None
    limit = min(ttl, _CACHE_LIVE_TTL) if _running_bar(ts, rows) else ttl
    if 0 <= time.time() - ts < limit:
        _MEM[key] = (ts, rows)
        return rows
    return None


def _cache_put(key: str, rows: Rows) -> None:
    if float(config.FICC_CACHE_TTL_SECONDS) <= 0:
        return
    now = time.time()
    _MEM[key] = (now, rows)
    try:
        d = config.ficc_cache_dir()
        d.mkdir(parents=True, exist_ok=True)
        (d / f"{key}.json").write_text(json.dumps({"ts": now, "rows": rows}), "utf-8")
    except Exception:
        pass


# --------------------------------------------------------------------------- #
# Synthetic — deterministic per id
# --------------------------------------------------------------------------- #
def _seed(text: str) -> int:
    return int.from_bytes(hashlib.sha256(text.upper().encode()).digest()[:4], "big")


def _business_dates(days: int) -> tuple[str, ...]:
    ds: list[str] = []
    d = date.today()
    while len(ds) < days:
        if d.weekday() < 5:
            ds.append(d.isoformat())
        d -= timedelta(days=1)
    return tuple(reversed(ds))


def _month_dates(n: int) -> tuple[str, ...]:
    """First weekday of each of the last n months, ascending, ending with the current month."""
    y, m = date.today().year, date.today().month
    ds: list[str] = []
    for _ in range(n):
        d = date(y, m, 1)
        while d.weekday() >= 5:
            d += timedelta(days=1)
        ds.append(d.isoformat())
        y, m = (y, m - 1) if m > 1 else (y - 1, 12)
    return tuple(reversed(ds))


def _synthetic_kind(id: str) -> str:
    u = id.upper()
    if u.startswith(("DGS", "SOFR", "DFF", "IR3TIB", "T10Y", "DFII", "BAML", "IORB")):
        return "rate"
    if any(c in u for c in "=^.-") or u.endswith("=X"):
        return "price"
    return "level"


def synthetic_series(id: str, *, days: int = 756, kind: str = "level") -> Series:
    """Seeded from sha256(id). `rate`: OU mean-reverting around 2–5% (decimal);
    `price`: GBM; `level`: random walk. Same id, same numbers, every time."""
    if days < 2:
        raise ValueError(f"days must be >= 2, got {days}")
    if kind not in ("level", "price", "rate"):
        raise ValueError(f"kind must be level|price|rate, got {kind!r}")
    seed = _seed(id)
    rng = np.random.default_rng(seed)
    dt = 1.0 / TRADING_DAYS
    if kind == "rate":
        theta = 0.02 + (seed % 31) / 1000.0                     # 2.0%..5.0%
        kappa, sigma = 0.8, 0.006 + (seed % 5) / 1000.0
        x = np.empty(days)
        x[0] = theta + (seed % 21 - 10) / 1000.0
        z = rng.normal(size=days - 1)
        for t in range(1, days):
            x[t] = max(0.0, x[t - 1] + kappa * (theta - x[t - 1]) * dt
                        + sigma * math.sqrt(dt) * z[t - 1])
        desc = f"OU rate, mean {theta:.2%}"
    elif kind == "price":
        mu, sigma = 0.02 + (seed % 9) / 100.0, 0.15 + (seed % 16) / 100.0
        s0 = 50.0 + (seed % 200)
        shocks = rng.normal((mu - 0.5 * sigma**2) * dt, sigma * math.sqrt(dt), size=days - 1)
        x = np.exp(np.concatenate([[math.log(s0)], math.log(s0) + np.cumsum(shocks)]))
        desc = f"GBM price, vol {sigma:.0%}"
    else:
        x0 = 10.0 + (seed % 90)
        x = x0 + np.cumsum(np.concatenate([[0.0], rng.normal(0.0, x0 * 0.01, size=days - 1)]))
        desc = "random-walk level"
    return Series(id=id, label=id, source="SYNTHETIC", dates=_business_dates(days),
                  values=tuple(float(v) for v in x),
                  note=f"Simulated series ({desc}) — no market data provider was used.")


def _ns(t: np.ndarray, b0: float, b1: float, b2: float, tau: float) -> np.ndarray:
    x = t / tau
    decay = (1.0 - np.exp(-x)) / x
    return b0 + b1 * decay + b2 * (decay - np.exp(-x))


def synthetic_curve_panel(*, days: int = 504, seed: int | None = None) -> CurvePanel:
    """Nelson-Siegel parameters random-walked day to day: level ~4%, slope of
    either sign, mild curvature; tau fixed at 2y. Yields floored at 5bp."""
    if days < 2:
        raise ValueError(f"days must be >= 2, got {days}")
    seed = _seed("UST_PANEL") if seed is None else int(seed)
    rng = np.random.default_rng(seed)
    t = np.asarray(UST_TENORS)
    b0 = 0.04 + np.cumsum(np.concatenate([[0.0], rng.normal(0, 0.0006, days - 1)]))
    b1 = (0.015 * (1 if seed % 2 else -1)
          + np.cumsum(np.concatenate([[0.0], rng.normal(0, 0.0008, days - 1)])))
    b2 = 0.005 + np.cumsum(np.concatenate([[0.0], rng.normal(0, 0.0006, days - 1)]))
    y = np.vstack([_ns(t, b0[i], b1[i], b2[i], 2.0) for i in range(days)])
    y = np.maximum(y, 0.0005)
    return CurvePanel(source="SYNTHETIC", dates=_business_dates(days), tenors=tuple(UST_TENORS),
                      yields=y, note="Simulated Treasury par curve (Nelson-Siegel random walk) "
                                     "— no market data provider was used.")


_FX_START = {"EURUSD": 1.10, "USDJPY": 150.0, "USDKRW": 1350.0, "GBPUSD": 1.27, "AUDUSD": 0.66,
             "USDCAD": 1.36, "USDCHF": 0.88, "NZDUSD": 0.60, "USDCNY": 7.2, "EURJPY": 165.0,
             "EURGBP": 0.86}


def _fx_pair(pair: str) -> str:
    p = re.sub(r"[^A-Za-z]", "", (pair or "")).upper()
    p = p[:-1] if p.endswith("X") and len(p) == 7 else p
    if len(p) != 6:
        raise FICCError(f"Cannot read FX pair {pair!r}; use forms like EURUSD or USD/KRW.")
    return p


def _fx_label(pair: str) -> str:
    return f"{pair[:3]}/{pair[3:]}"


def synthetic_fx(pair: str, *, days: int = 504) -> Series:
    """GBM spot with 7–10% vol from realistic start levels (EURUSD 1.1, USDJPY 150…)."""
    p = _fx_pair(pair)
    seed = _seed("FX_" + p)
    rng = np.random.default_rng(seed)
    s0 = _FX_START.get(p, 1.0)
    sigma = 0.07 + (seed % 4) / 100.0
    dt = 1.0 / TRADING_DAYS
    shocks = rng.normal(-0.5 * sigma**2 * dt, sigma * math.sqrt(dt), size=days - 1)
    x = np.exp(np.concatenate([[math.log(s0)], math.log(s0) + np.cumsum(shocks)]))
    return Series(id=f"{p}=X", label=_fx_label(p), source="SYNTHETIC", dates=_business_dates(days),
                  values=tuple(float(v) for v in x),
                  note=f"Simulated spot (GBM, vol {sigma:.0%}) — no market data provider "
                       "was used.")


# --------------------------------------------------------------------------- #
# Provider plumbing
# --------------------------------------------------------------------------- #
def _check_source(source: str) -> str:
    s = (source or "auto").lower()
    if s not in SOURCES:
        raise FICCError(f"Unknown source {source!r}. One of {SOURCES}.")
    return s


def _route(id: str) -> str:
    if any(c in id for c in "=^.-"):
        return "YFINANCE"
    if re.fullmatch(r"[A-Za-z0-9_]+", id):
        return "FRED"
    raise FICCError(f"Cannot route {id!r}: not a FRED id nor a Yahoo ticker.")


def _start_for(days: int) -> str:
    return (date.today() - timedelta(days=int(days * 1.6) + 10)).isoformat()


def _period_for(days: int) -> str:
    for n, p in ((5, "5d"), (21, "1mo"), (63, "3mo"), (126, "6mo"), (252, "1y"),
                 (504, "2y"), (1260, "5y")):
        if days <= n:
            return p
    return "10y"


def _fetch(provider: str, ids: list[str], days: int) -> dict[str, Rows]:
    if provider == "FRED":
        return _fred_fetch(ids, _start_for(days))
    return _yf_fetch(ids, _period_for(days))


def _provider_rows(provider: str, ids: list[str], days: int, *, not_before: float | None = None,
                   pit_store=None, retrieved_at_utc=None) -> tuple[dict[str, Rows], dict[str, str]]:
    """Cache-first batch fetch. Never raises: returns (rows by id, failure reason by id).
    A failed batch of several ids is retried one id at a time so one retired id
    does not take the whole sheet down.

    M1 ingest hook: when `pit_store` (a `core.ficc.pit.PITStore` with registry and clocks) is passed, every row
    set that answers — a cache hit with its file's retrieved_at, a fresh fetch with `retrieved_at_utc` (the
    caller's pinned instant) — is handed to `pit_store.ingest_rows(provider, id, rows, retrieved_at_utc)`, which
    stamps value_status by the close + 10 min rule and appends only new content. `not_before` is the cache rule
    of `_cache_get` (epoch seconds)."""
    rows: dict[str, Rows] = {}
    errors: dict[str, str] = {}
    missing = []
    for i in ids:
        key = _cache_key(provider, i, days)
        hit = _cache_get(key, not_before=not_before)
        if hit:
            rows[i] = hit
            if pit_store is not None and key in _MEM:
                pit_store.ingest_rows(provider, i, hit, _dt.fromtimestamp(_MEM[key][0], _tz.utc))
        else:
            missing.append(i)
    fetched: dict[str, Rows] = {}
    reason = ""
    if missing:
        try:
            fetched = _fetch(provider, missing, days)
        except Exception as exc:
            reason = f"{type(exc).__name__}: {exc}"
            if len(missing) > 1:
                for i in missing:                     # ponytail: N calls only on batch failure
                    try:
                        fetched.update(_fetch(provider, [i], days))
                    except Exception as exc1:
                        errors[i] = f"{type(exc1).__name__}: {exc1}"
    for i in missing:
        r = sorted(fetched.get(i) or [])
        if len(r) < _MIN_OBS:
            errors.setdefault(i, reason or f"{provider} returned only {len(r)} observations")
        else:
            rows[i] = r
            _cache_put(_cache_key(provider, i, days), r)
            if pit_store is not None:
                stamp = retrieved_at_utc or _dt.fromtimestamp(_MEM.get(_cache_key(provider, i, days), (time.time(),))[0], _tz.utc)
                pit_store.ingest_rows(provider, i, r, stamp)
    return rows, errors


def _series_from_rows(id: str, provider: str, rows: Rows, days: int, *, label: str = "",
                      note: str = "") -> Series:
    rows = rows[-days:]
    return Series(id=id, label=label or id, source=provider,
                  dates=tuple(d for d, _ in rows), values=tuple(float(v) for _, v in rows),
                  note=note)


def _degraded(s: Series, provider: str, reason: str) -> Series:
    return replace(s, note=f"{provider} failed: {reason}; simulated series. {s.note}")


# --------------------------------------------------------------------------- #
# Loaders
# --------------------------------------------------------------------------- #
def load_many(ids: list[str], *, source: str = "auto", days: int = 756) -> dict[str, Series]:
    """One provider call per provider for all ids. `auto` routes bare
    alphanumerics to FRED and anything with = ^ . - to Yahoo; ids a provider
    cannot serve come back SYNTHETIC with the reason in `note`. An explicit
    provider that cannot serve every id raises FICCError."""
    source = _check_source(source)
    if days < _MIN_OBS:
        raise ValueError(f"days must be >= {_MIN_OBS}, got {days}")
    groups: dict[str, list[str]] = {}
    for raw in ids:
        i = (raw or "").strip()
        if not i:
            raise FICCError("Blank id.")
        prov = ("SYNTHETIC" if source == "synthetic" else source.upper() if source != "auto"
                else _route(i))
        groups.setdefault(prov, []).append(i)
    out: dict[str, Series] = {}
    for prov, group in groups.items():
        if prov == "SYNTHETIC":
            for i in group:
                out[i] = synthetic_series(i, days=days, kind=_synthetic_kind(i))
            continue
        rows, errors = _provider_rows(prov, group, days)
        for i in group:
            if i in rows:
                out[i] = _series_from_rows(i, prov, rows[i], days)
            elif source == "auto":
                out[i] = _degraded(synthetic_series(i, days=days, kind=_synthetic_kind(i)),
                                   prov, errors[i])
            else:
                raise FICCError(f"{prov} could not serve {i!r}: {errors[i]}")
    return out


def load_series(id: str, *, source: str = "auto", days: int = 756, label: str = "") -> Series:
    s = load_many([id], source=source, days=days)[id.strip()]
    return replace(s, label=label) if label else s


def load_treasury_curve(*, source: str = "auto", days: int = 504) -> CurvePanel:
    """UST constant-maturity par curve history (FRED DGS*, percent → decimal) on
    `common.UST_TENORS`. Columns are forward-filled, rows still NaN dropped.
    Tenors FRED cannot serve are dropped from the panel (noted) as long as 2y
    and 10y plus at least six tenors remain. Yahoo has no curve."""
    source = _check_source(source)
    if source == "synthetic":
        return synthetic_curve_panel(days=days)
    if source == "yfinance":
        raise FICCError("yfinance has no Treasury curve; use source='fred' or 'synthetic'.")
    try:
        return _treasury_from_fred(days)
    except FICCError as exc:
        if source == "fred":
            raise
        p = synthetic_curve_panel(days=days)
        return replace(p, note=f"FRED failed: {exc}; simulated curve panel. {p.note}")


def _treasury_from_fred(days: int) -> CurvePanel:
    rows, errors = _provider_rows("FRED", list(_TREASURY_IDS), days)
    have = [(i, t) for i, t in zip(_TREASURY_IDS, UST_TENORS) if i in rows]
    if len(have) < 6 or "DGS2" not in rows or "DGS10" not in rows:
        why = "; ".join(f"{i}: {e}" for i, e in errors.items())
        raise FICCError(f"FRED served {len(have)}/{len(_TREASURY_IDS)} tenors ({why}).")
    dates = sorted({d for i, _ in have for d, _ in rows[i]})
    pos = {d: k for k, d in enumerate(dates)}
    y = np.full((len(dates), len(have)), np.nan)
    for k, (i, _) in enumerate(have):
        for d, v in rows[i]:
            y[pos[d], k] = v / 100.0
    for k in range(y.shape[1]):                       # forward fill each column
        col = y[:, k]
        idx = np.where(np.isnan(col), 0, np.arange(len(col)))
        np.maximum.accumulate(idx, out=idx)
        y[:, k] = col[idx]
    keep = ~np.isnan(y).any(axis=1)
    y, dates = y[keep][-days:], [d for d, k in zip(dates, keep) if k][-days:]
    if len(dates) < _MIN_OBS:
        raise FICCError(f"FRED curve has only {len(dates)} complete rows.")
    note = ""
    if len(have) < len(_TREASURY_IDS):
        note = "Missing tenors: " + ", ".join(i for i in _TREASURY_IDS if i not in rows) + "."
    return CurvePanel(source="FRED", dates=tuple(dates), tenors=tuple(t for _, t in have),
                      yields=y, note=note)


def load_fx_spot(pair: str, *, source: str = "auto", days: int = 504) -> Series:
    """Spot for a pair like "EURUSD" / "USD/KRW" from Yahoo ("EURUSD=X"); label "EUR/USD"."""
    source = _check_source(source)
    p = _fx_pair(pair)
    if source == "synthetic":
        return synthetic_fx(p, days=days)
    if source == "fred":
        raise FICCError("FX spot is served by yfinance, not FRED; use source='yfinance'.")
    ticker = f"{p}=X"
    rows, errors = _provider_rows("YFINANCE", [ticker], days)
    if ticker in rows:
        return _series_from_rows(ticker, "YFINANCE", rows[ticker], days, label=_fx_label(p))
    if source == "yfinance":
        raise FICCError(f"yfinance could not serve {ticker}: {errors[ticker]}")
    return _degraded(synthetic_fx(p, days=days), "YFINANCE", errors[ticker])


# Per currency: FRED ids in preference order, each with its frequency and a
# human label. Daily policy/overnight fixings first (SOFR, ECB deposit rate,
# SONIA) because the OECD 3m interbank series run 6-8 months behind; the
# monthly series stay as fallbacks and for the currencies FRED has nothing
# daily for (JPY, KRW, AUD, CAD, CHF).
_SHORT_RATE_IDS: dict[str, tuple[tuple[str, str, str], ...]] = {
    "USD": (("SOFR", "daily", "SOFR"), ("DFF", "daily", "Fed funds effective")),
    "EUR": (("ECBDFR", "daily", "ECB deposit facility rate"),
            ("IR3TIB01EZM156N", "monthly", "3m interbank")),
    "GBP": (("IUDSOIA", "daily", "SONIA"), ("IR3TIB01GBM156N", "monthly", "3m interbank")),
    "JPY": (("IRSTCI01JPM156N", "monthly", "call rate"),
            ("IR3TIB01JPM156N", "monthly", "3m interbank")),
    "KRW": (("IR3TIB01KRM156N", "monthly", "3m interbank"),),
    "AUD": (("IR3TIB01AUM156N", "monthly", "3m interbank"),),
    "CAD": (("IR3TIB01CAM156N", "monthly", "3m interbank"),),
    "CHF": (("IR3TIB01CHM156N", "monthly", "3m interbank"),),
}


def _synthetic_short_rate(id: str, freq: str, days: int, label: str) -> Series:
    """Daily: `days` business days. Monthly: days//21 observations on month starts."""
    if freq == "daily":
        s = synthetic_series(id, days=days, kind="rate")
    else:
        n = max(_MIN_OBS, days // 21)
        s = replace(synthetic_series(id, days=n, kind="rate"), dates=_month_dates(n))
    return replace(s, label=label, note=f"{freq}; {s.note}")


def load_short_rate(ccy: str = "USD", *, source: str = "auto", days: int = 756) -> Series:
    """The funding rate for `ccy`, decimal. Daily where FRED has a daily fixing
    (SOFR, ECB deposit rate, SONIA), otherwise the OECD monthly series; the
    `note` states the frequency and the series that answered, and a monthly
    series is left monthly — consumers forward-fill by date, never interpolate."""
    source = _check_source(source)
    c = (ccy or "").strip().upper()
    if c not in _SHORT_RATE_IDS:
        raise FICCError(f"No short-rate series for {ccy!r}; one of {tuple(_SHORT_RATE_IDS)}.")
    choices = _SHORT_RATE_IDS[c]
    ids = [i for i, _, _ in choices]
    first_id, first_freq, first_name = choices[0]
    label = f"{c} short rate ({first_name})"
    if source == "synthetic":
        return _synthetic_short_rate(first_id, first_freq, days, label)
    if source == "yfinance":
        raise FICCError("Short rates come from FRED; use source='fred' or 'synthetic'.")
    rows, errors = _provider_rows("FRED", ids, days)
    for i, freq, name in choices:
        if i in rows:
            return _series_from_rows(i, "FRED", rows[i], days, label=f"{c} short rate ({name})",
                                     note=f"{freq}; FRED {i}, percent converted to decimal"
                                     ).scaled(0.01)
    why = "; ".join(f"{i}: {errors[i]}" for i in ids)
    if source == "fred":
        raise FICCError(f"FRED could not serve a {c} short rate ({why}).")
    return _degraded(_synthetic_short_rate(first_id, first_freq, days, label), "FRED", why)


def load_policy_rates(ccys: list[str], *, source: str = "auto", days: int = 756
                      ) -> dict[str, Series]:
    return {c.upper(): load_short_rate(c, source=source, days=days) for c in ccys}


def probe() -> dict:
    """One small live call per provider (FRED DGS10 30d; Yahoo EURUSD=X 5d).
    Never raises; never caches. For the Settings page."""
    out = {}
    for name, ready, call in (
            ("fred", fred_ready, lambda: _fred_fetch(["DGS10"], _start_for(20)).get("DGS10", [])),
            ("yfinance", yfinance_ready,
             lambda: _yf_fetch(["EURUSD=X"], "5d").get("EURUSD=X", []))):
        if not ready():
            out[name] = {"ok": False, "detail": "library not installed"}
            continue
        try:
            rows = call()
            out[name] = ({"ok": True, "detail": f"{len(rows)} obs, last {rows[-1][0]}"} if rows
                         else {"ok": False, "detail": "no observations returned"})
        except Exception as exc:
            out[name] = {"ok": False, "detail": f"{type(exc).__name__}: {exc}"}
    return out


# --------------------------------------------------------------------------- #
# Self-check (no network: the fetchers are stubbed to fail)
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    import sys
    me = sys.modules[__name__]

    a = synthetic_series("DGS10", days=100, kind="rate")
    assert a.values == synthetic_series("DGS10", days=100, kind="rate").values
    assert a.values != synthetic_series("DGS2", days=100, kind="rate").values
    assert all(0.0 <= v < 0.15 for v in a.values)
    assert a.change(5) is not None and a.change(200) is None
    assert len(a.window(10)) == 10 and a.scaled(100).last == a.last * 100

    p = synthetic_curve_panel(days=60)
    assert p.yields.shape == (60, 11) and not np.isnan(p.yields).any() and len(p) == 60
    snap = p.latest()
    assert snap.tenors == UST_TENORS and len(snap.par_yields) == 11
    assert 0.0 < snap.par_yields[8] < 0.1

    fx = synthetic_fx("USD/JPY", days=50)
    assert fx.label == "USD/JPY" and fx.id == "USDJPY=X" and 100 < fx.last < 220
    assert load_fx_spot("EURUSD", source="synthetic").label == "EUR/USD"
    assert load_series("SOFR", source="synthetic").source == "SYNTHETIC"
    assert load_treasury_curve(source="synthetic", days=30).yields.shape == (30, 11)
    krw = load_short_rate("KRW", source="synthetic")
    assert "monthly" in krw.note and len(krw) == 36
    y0, m0, y1, m1 = (int(x) for d in (krw.dates[0], krw.dates[-1]) for x in d.split("-")[:2])
    assert (y1 - y0) * 12 + (m1 - m0) >= 35, "monthly series must span months, not sessions"
    assert krw.values == synthetic_series("IR3TIB01KRM156N", days=36, kind="rate").values
    from core.ficc import fx as _fx                   # lazy: fx imports this module
    bt = _fx.carry_backtest({p: synthetic_fx(p) for p in ("EURUSD", "USDJPY", "USDKRW")},
                            load_policy_rates(["USD", "EUR", "JPY", "KRW"], source="synthetic"))
    assert len(bt.dates) > 300, len(bt.dates)

    saved = (me._fred_fetch, me._yf_fetch, config.FICC_CACHE_TTL_SECONDS)
    def _boom(*_a, **_k):
        raise FICCError("offline")
    me._fred_fetch = me._yf_fetch = _boom
    config.FICC_CACHE_TTL_SECONDS = 0.0
    try:
        s = load_series("DGS10", days=100)
        assert s.source == "SYNTHETIC" and "FRED failed" in s.note and "offline" in s.note
        s = load_fx_spot("USDKRW")
        assert s.source == "SYNTHETIC" and "YFINANCE failed" in s.note and s.label == "USD/KRW"
        assert load_treasury_curve().source == "SYNTHETIC"
        assert load_short_rate("USD").source == "SYNTHETIC"
        many = load_many(["DGS2", "EURUSD=X"], days=50)
        assert set(many) == {"DGS2", "EURUSD=X"}
        assert all(v.source == "SYNTHETIC" for v in many.values())
        for bad in (lambda: load_series("DGS10", source="fred"),
                    lambda: load_treasury_curve(source="fred"),
                    lambda: load_treasury_curve(source="yfinance"),
                    lambda: load_fx_spot("EURUSD", source="yfinance"),
                    lambda: load_series("X", source="bloomberg")):
            try:
                bad()
            except FICCError:
                continue
            raise AssertionError("explicit provider must raise")
        pr = probe()
        assert pr["fred"]["ok"] is False and pr["yfinance"]["ok"] is False
    finally:
        me._fred_fetch, me._yf_fetch, config.FICC_CACHE_TTL_SECONDS = saved
    print("ok")
