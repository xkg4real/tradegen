"""GROKTEAM BOOK desk: the guide's BOOK + SIZE rules, paper-traded on Kalshi KXBTCD ("BTC above K at the hour",
settled on the 60-second BRTI average), with QUANTGEN's GARCH-t as the "own probability" the guide never specifies.

    python -m grokteam.book [--start 2025-01-15] [--end YYYY-MM-DD] [--limit N]

fetches every settled event not yet cached, replays all of them and writes grokteam/out/book/. Candles are
timestamped records, so the forward window (decisions after the freeze, grokteam.prereg) is the archive code on
later events and the machine need not be awake at decision times. The forward window is blinded until
FORWARD_END: before it, its events are fetched and cached but never replayed; on or after it, the first run with
every forward event in hand is the one look, written once to out/book/FORWARD_LOOK.json and only re-printed after.

Read-only HTTP: Kalshi public market data and Binance public klines; no account, key or order endpoint. Raw pulls
are cached under ~/.nextgen/grokteam as gzip JSON with a sha256 MANIFEST, verified on every read. Nothing in
paper_live is imported (its engine silences all warnings at import).

One event closing at T (top of a UTC hour):
  decision  T-30m. S = Binance BTCUSDT close of the 1m bar ending at T-30m, times (1 + basis); basis = median
            (BRTI settlement / Binance 1m VWAP before the close - 1) over the last 24 events settled in the 48 h
            before the decision. sigma, nu = GARCH(1,1)-t (core.quant.garch) on the last 2,000 closed 1h
            bars, de-seasonalised by hour-of-day x weekend. Quotes = yes_ask / yes_bid of the latest 1m candle
            ending at or before T-30m and no more than 30 min earlier (Kalshi's historical tier writes a candle
            only when a quote changes or a trade prints), on the 12 strikes nearest S. p_yes = P(S_T > K) under
            the fitted t, zero drift.
  fill      the candle ending T-29m: its ask for YES, 1 - bid for NO, at most its volume (no candle: no fill).
  fee       ceil-to-cent(0.07 x C x P x (1 - P)) per order (series fee_type quadratic, multiplier 1), inside
            the dollars staked.
  settle    the market's result; every bet is held to settlement, so the guide's 7-open cap never binds.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import inspect
import json
import math
import os
import sys
import threading
import time
from collections import deque
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import scipy.stats as sps
from scipy.optimize import minimize
from scipy.special import expit

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.quant import garch as G  # noqa: E402

OUT = Path(__file__).resolve().parent / "out" / "book"
DATA = Path(os.environ.get("GROKTEAM_DATA") or Path.home() / ".nextgen" / "grokteam")
PREREG = Path(__file__).resolve().parent / "out" / "PREREG_book.json"
LOOK = OUT / "FORWARD_LOOK.json"
KALSHI = "https://api.elections.kalshi.com/trade-api/v2"
SERIES, FAMILY = "KXBTCD", "GROKTEAM-BOOK"
EVENT_CACHE = f"{SERIES}-v2"           # v2: decision quote = last candle within quote_stale_s (v1 kept 3 minutes)
GUIDE = "https://lazyowen.com/guides/grok-bot-trading-team-setup (published 2026-10-20)"
KALSHI_RPS, FETCH_THREADS = 8.0, 10    # ceiling of the adaptive pace (the public limit is undocumented); pool of 10
ET = ZoneInfo("America/New_York")
nan = math.nan

# Everything that decides a trade. A change here is a new ledger row (a new trial), never an edit of an old one.
RULES = dict(
    decision_s=1800, fill_lag_s=60, quote_stale_s=1800, strikes=12,
    garch=dict(window=2000, dist="t", season="hour-of-day x weekend RMS", drift=0.0),
    basis=dict(n=24, min_n=12, max_age_h=48),
    fee_rate=0.07, shadow_usd=60.0, equity0=1000.0, cap_frac=0.06, min_order=50.0,
    score=dict(mid=(0.02, 0.98), clip=0.001),
)
ACCOUNTS = {
    # guide BOOK rule with QUANTGEN's calibrated p and the cost gate in binary form (edge > 2 x fee per contract)
    "PRED-GATED": dict(prob="cal", band=[0.80, 0.97], max_spread=0.03, edge="fee", fee_mult=2.0, size="half_kelly"),
    # the guide as written: |own p - price| > 8 points, own p = the raw model
    "PRED-LIT8": dict(prob="raw", band=[0.10, 0.90], max_spread=None, edge="abs", edge_min=0.08, size="half_kelly"),
    # no model: the favourite-longshot bias alone
    "PRED-FLB": dict(prob=None, band=[0.90, 0.95], max_spread=0.03, target=0.93, size="flat"),
}
MODEL_ACCOUNTS = ("PRED-GATED", "PRED-LIT8")
ARCHIVE_START, CAL_END, FORWARD_END, FREEZE_BY = "2025-01-15", "2026-01-01", "2027-02-01", "2026-10-25"
# How the readout decides; frozen with the hypotheses (grokteam.prereg).
VERDICT = dict(ci=0.90, block_days=5, holm_alpha=0.10, skill_p=0.10, null_p=0.10, mde_factor=2.4865,
               target_edge=0.01, max_skip=0.05)
# Events opened while designing (2026-10-21 probes); excluded from every statistic.
SEEN = {"KXBTCD-24DEC1617", "KXBTCD-25JAN1511", "KXBTCD-25JAN1517", "KXBTCD-25JUN1014", "KXBTCD-25JUN1017",
        "KXBTCD-25SEP1014", "KXBTCD-25DEC1017", "KXBTCD-26JAN1414", "KXBTCD-26AUG1917", "KXBTCD-26AUG2019",
        "KXBTCD-26OCT2014", "KXBTCD-26OCT2017", "KXBTCD-26OCT2019"}


def ts(text: str | None) -> int | None:
    return None if not text else int(datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp())


def day_s(iso_day: str) -> int:
    return int(datetime.fromisoformat(iso_day).replace(tzinfo=timezone.utc).timestamp())


# ----------------------------------------------------------------------------- cache
_MANIFESTS: dict[Path, dict[str, str]] = {}


def _manifest(folder: Path) -> dict[str, str]:
    if folder not in _MANIFESTS:
        m, p = {}, folder / "MANIFEST.jsonl"
        if p.exists():
            for line in p.read_text(encoding="utf-8").splitlines():
                try:                                           # a line cut by a crash: its file reads as missing
                    rec = json.loads(line)
                    m[rec["file"]] = rec["sha256"]
                except (ValueError, KeyError, TypeError):
                    continue
        _MANIFESTS[folder] = m
    return _MANIFESTS[folder]


def write_cached(path: Path, obj) -> None:
    """gzip JSON (mtime 0: equal content, equal bytes), tmp-then-replace, then its sha256 line in the folder's
    MANIFEST.jsonl; a file without a manifest line reads as missing and is fetched again."""
    raw = gzip.compress(json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8"), mtime=0)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_bytes(raw)
    os.replace(tmp, path)
    sha = hashlib.sha256(raw).hexdigest()
    with open(path.parent / "MANIFEST.jsonl", "a", encoding="utf-8") as fh:
        fh.write(json.dumps({"file": path.name, "sha256": sha}) + "\n")
    _manifest(path.parent)[path.name] = sha


def read_cached(path: Path):
    """The cached object, None when absent; raises when the bytes no longer match their manifest sha256."""
    sha = _manifest(path.parent).get(path.name)
    if sha is None or not path.exists():
        return None
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != sha:
        raise RuntimeError(f"{path}: sha256 does not match MANIFEST.jsonl; the cached pull was altered")
    return json.loads(gzip.decompress(raw))


# ----------------------------------------------------------------------------- HTTP
_pace_lock, _pace = threading.Lock(), dict(next=0.0, rps=KALSHI_RPS, ok=0)


def _slot() -> None:
    """One call slot every 1 / rps seconds across all fetch threads."""
    with _pace_lock:
        slot = max(time.monotonic(), _pace["next"])
        _pace["next"] = slot + 1.0 / _pace["rps"]
    time.sleep(max(0.0, slot - time.monotonic()))


def _throttled(pause: float) -> None:
    """A 429: every thread waits `pause` seconds and the rate drops by a fifth (floor 2/s); 500 clean calls in a
    row raise it by 5% again, up to KALSHI_RPS. The public limit is undocumented, so the pace finds it."""
    with _pace_lock:
        _pace["next"] = max(_pace["next"], time.monotonic() + pause)
        _pace["rps"], _pace["ok"] = max(2.0, _pace["rps"] * 0.8), 0


def kalshi(path: str, **params) -> dict:
    """GET on Kalshi's public market-data API at the shared pace. A 429 pauses every thread (2 s doubling to 64 s)
    and slows the pace; a 5xx or a dropped connection waits the same and retries; a 404 raises KeyError."""
    from data.net import session
    err = ""
    for wait in (2, 4, 8, 16, 32, 64, None):
        _slot()
        try:
            r = session.get(KALSHI + path, params=params, timeout=30, headers={"Accept": "application/json"})
            if r.status_code == 200:
                with _pace_lock:
                    _pace["ok"] += 1
                    if _pace["ok"] >= 500:
                        _pace["rps"], _pace["ok"] = min(KALSHI_RPS, _pace["rps"] * 1.05), 0
                return r.json()
            if r.status_code == 404:
                raise KeyError(path)
            err = f"HTTP {r.status_code}"
            if r.status_code not in (429, 500, 502, 503, 504):
                break
            if r.status_code == 429 and wait is not None:
                _throttled(wait)
                continue
        except KeyError:
            raise
        except Exception as exc:                       # connection reset, timeout
            err = type(exc).__name__
        if wait is None:
            break
        time.sleep(wait)
    raise RuntimeError(f"Kalshi {path}: {err}")


def binance_1m(start_s: int, n: int) -> list[list]:
    """BTCUSDT 1m klines from bar open `start_s`: [open_s, close, vwap]. QUANTGEN's Binance route (data host
    first, main host second)."""
    from data.crypto import crypto_client as CC
    rows = CC._binance_spot("/klines", dict(symbol="BTCUSDT", interval="1m", startTime=start_s * 1000, limit=n),
                            label="Binance BTCUSDT 1m")
    return [[int(k[0]) // 1000, float(k[4]), float(k[7]) / float(k[5]) if float(k[5]) > 0 else float(k[4])]
            for k in rows]


def hourly_bars(need_close_s: int) -> tuple[np.ndarray, np.ndarray]:
    """Closed BTCUSDT 1h bars (open_s, close) through QUANTGEN's BinancePublic client, cached; fetched again when
    the cache ends before `need_close_s`. The bar still forming at fetch time is dropped, so a later decision can
    never see a partial close."""
    p = DATA / "binance" / "BTCUSDT_1h.json.gz"
    bars = read_cached(p)
    if not bars or bars["open_s"][-1] + 3600 < need_close_s:
        from data.crypto.crypto_client import BinancePublic
        now = int(time.time())
        hours = (now - day_s("2024-09-01")) // 3600 + 24
        c = BinancePublic().daily("BTCUSDT", interval="1h", days=int(hours))
        o = [ts(d) for d in c.dates]
        keep = [i for i, t in enumerate(o) if t + 3600 <= now]
        bars = dict(open_s=[o[i] for i in keep], close=[c.close[i] for i in keep], fetched_s=now)
        write_cached(p, bars)
    return np.asarray(bars["open_s"], dtype=np.int64), np.asarray(bars["close"], dtype=float)


# ----------------------------------------------------------------------------- Kalshi pulls
def settled_events(until_s: int) -> list[dict]:
    """Every settled KXBTCD event with a strike date, oldest first: {event, close_s}. Re-listed when the cached
    list ends more than two hours before `until_s`, and always once after FORWARD_END + 1 h, so the one look
    sees the window's last events."""
    p = DATA / "kalshi" / "events.json.gz"
    ev = read_cached(p)
    end = day_s(FORWARD_END) + 3600
    if not ev or ev["listed_s"] < until_s - 7200 or (until_s >= end > ev["listed_s"]):
        rows, cursor = [], ""
        while True:
            d = kalshi("/events", series_ticker=SERIES, status="settled", limit=200, **({"cursor": cursor} if cursor else {}))
            rows += [dict(event=e["event_ticker"], close_s=ts(e["strike_date"])) for e in d.get("events", [])
                     if e.get("strike_date")]
            cursor = d.get("cursor") or ""
            if not cursor:
                break
        ev = dict(listed_s=int(time.time()), events=sorted(rows, key=lambda e: e["close_s"]))
        write_cached(p, ev)
    return ev["events"]


def _px(d: dict | None, k: str = "close") -> float | None:
    v = None if not d else d.get(k, d.get(k + "_dollars"))
    return None if v in (None, "") else float(v)


def fetch_event(event: str, close_s: int, cutoff_s: int) -> dict:
    """One event's record: settlement, Binance at decision and close, and for the strikes nearest the Binance price
    the latest 1m candle ending in [decision - quote_stale_s, decision] plus the fill candle (decision +
    fill_lag_s). Markets settled before Kalshi's cutoff are served by /historical."""
    hist = close_s < cutoff_s
    markets = []
    for use_hist in (hist, not hist):                          # an event near the cutoff may sit on either side
        cursor = ""
        while True:
            try:
                d = kalshi("/historical/markets" if use_hist else "/markets", event_ticker=event, limit=1000,
                           **({"cursor": cursor} if cursor else {}))
            except KeyError:
                break
            markets += d.get("markets", [])
            cursor = d.get("cursor") or ""
            if not cursor:
                break
        if markets:
            hist = use_hist
            break
    dec = close_s - RULES["decision_s"]
    k = binance_1m(dec - 60, 31)                               # bars opening dec-60 .. close-60
    spot = next((c for t, c, _ in k if t == dec - 60), None)
    vwap_close = next((v for t, _, v in k if t == close_s - 60), None)
    exp = next((float(m["expiration_value"]) for m in markets if m.get("expiration_value")), None)
    settled = max((ts(m.get("settlement_ts")) or 0 for m in markets), default=0) or None
    pick = sorted((m for m in markets if m.get("strike_type") == "greater" and m.get("floor_strike") is not None),
                  key=lambda m: abs(float(m["floor_strike"]) - spot))[:RULES["strikes"]] if spot else []
    lo, fill = dec - RULES["quote_stale_s"], dec + RULES["fill_lag_s"]
    strikes = []
    for m in pick:
        paths = [f"/historical/markets/{m['ticker']}/candlesticks", f"/series/{SERIES}/markets/{m['ticker']}/candlesticks"]
        cs = None
        for path in (paths if hist else paths[::-1]):
            try:
                cs = kalshi(path, start_ts=lo, end_ts=fill, period_interval=1).get("candlesticks", [])
                break
            except KeyError:
                continue
        cs = cs or []
        pre = [c for c in cs if lo <= c["end_period_ts"] <= dec]
        keep = ([max(pre, key=lambda c: c["end_period_ts"])] if pre else []) + [c for c in cs if c["end_period_ts"] == fill]
        strikes.append(dict(ticker=m["ticker"], strike=float(m["floor_strike"]), result=m.get("result"),
                            candles={str(c["end_period_ts"]): [_px(c.get("yes_ask")), _px(c.get("yes_bid")),
                                                              float(c.get("volume", c.get("volume_fp")) or 0)]
                                     for c in keep}))
    return dict(event=event, close_s=close_s, decision_s=dec, historical=hist, n_markets=len(markets),
                expiration_value=exp, settled_s=settled, spot=spot, binance_vwap_close=vwap_close, strikes=strikes)


def fetch_all(evs: list[dict]) -> tuple[list[dict], list[str]]:
    """(records, failed event tickers) for `evs`, fetching the ones not cached. A failed event is left for the next
    run; the forward look refuses to run while any of its events is missing."""
    folder = DATA / "kalshi" / EVENT_CACHE
    out, todo = [], []
    for e in evs:
        rec = read_cached(folder / f"{e['event']}.json.gz")
        if rec:
            out.append(rec)
        else:
            todo.append(e)
    t0, failed = time.time(), []
    if todo:
        cutoff = ts(kalshi("/historical/cutoff")["market_settled_ts"])
        with ThreadPoolExecutor(max_workers=FETCH_THREADS) as pool:  # the pace is shared; threads only hide latency
            futs = {pool.submit(fetch_event, e["event"], e["close_s"], cutoff): e for e in todo}
            for i, fut in enumerate(as_completed(futs), 1):
                e = futs[fut]
                try:
                    rec = fut.result()
                    write_cached(folder / f"{e['event']}.json.gz", rec)   # writes stay on this thread
                    out.append(rec)
                except Exception as exc:
                    failed.append(e["event"])
                    print(f"  {e['event']}: {exc}", flush=True)
                if i % 100 == 0 or i == len(todo):
                    eta = (time.time() - t0) / i * (len(todo) - i) / 60
                    print(f"fetched {i}/{len(todo)} events ({len(failed)} failed), pace {_pace['rps']:.1f}/s, about {eta:.0f} min left", flush=True)
    return sorted(out, key=lambda r: r["close_s"]), failed


# ----------------------------------------------------------------------------- model
def _group(open_s: np.ndarray) -> np.ndarray:
    """Hour-of-day (UTC) x weekend: 48 groups."""
    o = np.asarray(open_s, dtype=np.int64)
    weekend = ((o // 86400 + 3) % 7) >= 5                      # 1970-01-01 was a Thursday
    return (o % 86400) // 3600 + 24 * weekend


def model_at(dec_s: int, close_s: int, bars_open: np.ndarray, bars_close: np.ndarray) -> tuple:
    """(ok, sigma_tau, nu, why) for a decision. Hourly BTC volatility is strongly seasonal, so each return is divided
    by its hour-of-day x weekend RMS over the same window before the fit and each forecast step is scaled back by
    its group's RMS. The standardised returns are fed to garch.fit_garch at x 0.01, the daily-variance scale its
    omega is optimised in (garch.py _OMEGA_SCALE); at unit variance omega never leaves its start. Returns spanning a
    missing bar are dropped. Skipped (and counted): a fit on a parameter bound, a fit that did not converge, a
    missing last bar. garch.py's 'stationarity' flag (alpha + beta > 0.995, a warning in daily units) is not a
    skip: hourly persistence sits there routinely, and a one-step forecast uses only the filtered variance. Nor is
    a non-converged fit carrying that flag: L-BFGS-B reports ABNORMAL when the optimum sits on garch.py's penalty
    wall at STATIONARITY_MAX (all 120 such fits sampled from the 2026 archive were at 0.9989-0.9995; owner's
    ruling, 2026-10-22, before the freeze)."""
    W = RULES["garch"]["window"]
    top = dec_s - dec_s % 3600                                 # open of the bar the decision sits in
    j = int(np.searchsorted(bars_open, top - 3600, side="right"))
    if j == 0 or bars_open[j - 1] != top - 3600:
        return False, nan, nan, "last hourly bar missing"
    o, c = bars_open[max(0, j - W - 60):j], bars_close[max(0, j - W - 60):j]
    ok = np.diff(o) == 3600
    r, ro = np.diff(np.log(c))[ok][-W:], o[1:][ok][-W:]
    if r.size < W:
        return False, nan, nan, "too few hourly bars"
    g = _group(ro)
    rms = np.array([math.sqrt(np.mean(r[g == k] ** 2)) if (g == k).sum() >= 5 else nan for k in range(48)])
    if not np.isfinite(rms[np.unique(g)]).all():
        return False, nan, nan, "thin seasonal group"
    fit = G.fit_garch(r / rms[g] * 0.01, dist="t", profile=False)
    bad = tuple(b for b in fit.at_bound if b != "stationarity")
    if bad or not (fit.converged or "stationarity" in fit.at_bound):
        return False, nan, nan, "fit on bound: " + ",".join(bad or ("no convergence",))
    steps = math.ceil((close_s - top) / 3600)
    v = G.forecast_variance(fit, steps) * 1e4                  # back to unit-RMS units
    var = 0.0
    for h in range(steps):
        start, end = max(top + 3600 * h, dec_s), min(top + 3600 * (h + 1), close_s)
        gk = int(_group(np.array([top + 3600 * h]))[0])
        if not math.isfinite(rms[gk]):
            return False, nan, nan, "thin seasonal group"
        var += v[h] * rms[gk] ** 2 * (end - start) / 3600
    return True, math.sqrt(var), fit.nu, ""


def p_above(K: float, S: float, sigma: float, nu: float) -> float:
    """P(S_T > K) for log(S_T / S) = sigma x z, z the unit-variance t(nu) (normal above garch.NU_NORMAL)."""
    x = math.log(K / S) / sigma
    if not math.isfinite(nu) or nu > G.NU_NORMAL:
        return float(sps.norm.sf(x))
    return float(sps.t.sf(x / math.sqrt((nu - 2.0) / nu), nu))


def model_digest() -> str:
    """What the cached fits depend on: the GARCH settings, garch.py and the code of model_at and _group."""
    h = hashlib.sha256(json.dumps([RULES["garch"], RULES["decision_s"]], sort_keys=True).encode())
    h.update(Path(G.__file__).read_bytes())
    h.update((inspect.getsource(model_at) + inspect.getsource(_group)).encode())
    return h.hexdigest()[:16]


def fit_calibration(p_raw, y) -> dict:
    """Logistic recalibration p_cal = 1 / (1 + exp(-(a + b logit p_raw))), maximum likelihood."""
    eps = RULES["score"]["clip"]
    x = np.log(np.clip(p_raw, eps, 1 - eps) / (1 - np.clip(p_raw, eps, 1 - eps)))
    y = np.asarray(y, dtype=float)

    def nll(w):
        z = w[0] + w[1] * x
        return float(np.sum(np.logaddexp(0, z) - y * z)), np.array([np.sum(expit(z) - y), np.sum((expit(z) - y) * x)])
    res = minimize(nll, np.array([0.0, 1.0]), jac=True, method="BFGS")
    return dict(a=float(res.x[0]), b=float(res.x[1]), n=int(y.size))


def calibrate(p_raw, cal: dict) -> np.ndarray:
    eps = RULES["score"]["clip"]
    p = np.clip(np.asarray(p_raw, dtype=float), eps, 1 - eps)
    return expit(cal["a"] + cal["b"] * np.log(p / (1 - p)))


# ----------------------------------------------------------------------------- replay
def window_of(close_s: int, freeze_s: int | None) -> str:
    if close_s < day_s(ARCHIVE_START) or close_s >= day_s(FORWARD_END):
        return ""
    if close_s < day_s(CAL_END):
        return "cal"
    return "forward" if freeze_s is not None and close_s - RULES["decision_s"] > freeze_s else "eval"


def strike_table(records: list[dict], freeze_s: int | None, digest: str | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """One row per event (model inputs, basis, window) and one per fetched strike (quotes at decision and fill,
    p_raw, outcome). The model is fitted once per decision and cached by model_digest()."""
    need = max((r["decision_s"] for r in records), default=0)
    bo, bc = hourly_bars(need - need % 3600)
    mpath = DATA / "model" / f"{digest or model_digest()}.json.gz"
    cache = read_cached(mpath) or {}
    basis_q: deque = deque()
    ev_rows, st_rows, fresh = [], [], 0
    bcfg = RULES["basis"]
    for r in records:
        dec, close = r["decision_s"], r["close_s"]
        win = window_of(close, freeze_s)
        recent = [b for s, b in basis_q if dec - 3600 * bcfg["max_age_h"] <= s <= dec][-bcfg["n"]:]
        basis = float(np.median(recent)) if len(recent) >= bcfg["min_n"] else None
        if r.get("expiration_value") and r.get("binance_vwap_close") and r.get("settled_s"):
            basis_q.append((r["settled_s"], r["expiration_value"] / r["binance_vwap_close"] - 1))
            if len(basis_q) > 200:
                basis_q.popleft()
        key = str(dec)
        if key not in cache:
            cache[key] = list(model_at(dec, close, bo, bc))
            fresh += 1
            if fresh % 500 == 0:
                write_cached(mpath, cache)
                print(f"  model fits: {fresh} new", flush=True)
        ok, sig, nu, why = cache[key]
        S = r["spot"] * (1 + basis) if (r.get("spot") and basis is not None) else None
        if ok and S is None:
            why = "no Binance price" if not r.get("spot") else "basis: too few settled events"
        model_ok = bool(ok and S is not None)
        ev_rows.append(dict(event=r["event"], close_s=close, window=win, seen=r["event"] in SEEN, spot=r.get("spot"),
                            basis=basis, S=S, sigma=sig, nu=nu, model_ok=model_ok, why=why,
                            n_strikes=len(r["strikes"])))
        f = str(dec + RULES["fill_lag_s"])
        for s in r["strikes"]:
            if s["result"] not in ("yes", "no"):
                continue
            pre = [int(k) for k in s["candles"] if dec - RULES["quote_stale_s"] <= int(k) <= dec]
            q, qf = (s["candles"][str(max(pre))] if pre else None), s["candles"].get(f)
            st_rows.append(dict(event=r["event"], close_s=close, window=win, ticker=s["ticker"], strike=s["strike"],
                                y=int(s["result"] == "yes"),
                                p_raw=p_above(s["strike"], S, sig, nu) if model_ok else nan,
                                ask=q[0] if q else None, bid=q[1] if q else None, quote_age_s=dec - max(pre) if pre else nan,
                                f_ask=qf[0] if qf else None, f_bid=qf[1] if qf else None, f_vol=qf[2] if qf else 0.0))
    if fresh:
        write_cached(mpath, cache)
    ev, st = pd.DataFrame(ev_rows), pd.DataFrame(st_rows)
    for c in ("ask", "bid", "f_ask", "f_bid"):
        st[c] = pd.to_numeric(st[c], errors="coerce").round(4)  # cent ticks; no float noise in bands and ties
        st.loc[(st[c] <= 0) | (st[c] >= 1), c] = nan            # 0 = no bid, 1 = no ask
    st["mid"] = (st["ask"] + st["bid"]) / 2
    lo, hi = RULES["score"]["mid"]
    st["scored"] = st["ask"].notna() & st["bid"].notna() & (st["bid"] < st["ask"]) & st["mid"].between(lo, hi)
    return ev, st


def fee(contracts: int, price: float, mult: float = 1.0) -> float:
    """Kalshi's quadratic taker fee for one order, rounded up to the cent."""
    return math.ceil(round(RULES["fee_rate"] * mult * contracts * price * (1 - price) * 100, 6)) / 100


def buy(dollars: float, price: float, win: bool, cap: float, fee_mult: float = 1.0) -> tuple[int, float, float]:
    """Contracts bought with `dollars` at `price`, fee included in the dollars (at most `cap` contracts), net P&L
    and premium paid including the fee."""
    c = int(min(math.floor(dollars / price + 1e-9), math.floor(cap)))
    while c > 0 and c * price + fee(c, price, fee_mult) > dollars + 1e-9:
        c -= 1
    if c <= 0:
        return 0, 0.0, 0.0
    f = fee(c, price, fee_mult)
    return c, c * (float(win) - price) - f, c * price + f


def candidates(acct: dict, rows: pd.DataFrame) -> list[dict]:
    """Every (strike, side) an account may take at the decision, with its price, spread and edge."""
    out = []
    lo, hi = acct["band"]
    pcol = {"cal": "p_cal", "raw": "p_raw"}.get(acct["prob"])
    for row in rows.itertuples(index=False):
        spread = round(row.ask - row.bid, 4) if (math.isfinite(row.ask) and math.isfinite(row.bid)) else nan
        p_yes = getattr(row, pcol) if pcol else nan
        for side, m, ps in (("yes", row.ask, p_yes), ("no", round(1 - row.bid, 4), 1 - p_yes)):
            if not math.isfinite(m) or not lo <= m <= hi:
                continue
            if acct.get("max_spread") is not None and not spread <= acct["max_spread"]:
                continue
            if pcol:
                if not math.isfinite(ps):
                    continue
                edge = ps - m
                need = (acct["fee_mult"] * RULES["fee_rate"] * m * (1 - m)) if acct["edge"] == "fee" else acct["edge_min"]
                if not edge > need:
                    continue
            else:
                ps, edge = nan, nan
            out.append(dict(ticker=row.ticker, strike=row.strike, side=side, m=m, p=ps, edge=edge, spread=spread,
                            y=row.y, f_ask=row.f_ask, f_bid=row.f_bid, f_vol=row.f_vol))
    return out


def choose(acct: dict, cands: list[dict]) -> dict | None:
    """One bet per event: the largest edge, or for the model-free account the price nearest its target."""
    if not cands:
        return None
    if acct["prob"]:
        return max(cands, key=lambda c: (c["edge"], c["ticker"], c["side"]))
    return min(cands, key=lambda c: (abs(c["m"] - acct["target"]), c["ticker"], c["side"]))


def stake(acct: dict, bet: dict, equity: float) -> float:
    """SIZE: half Kelly (b = (1 - m) / m) capped at 6% of equity, or a flat $60 capped the same way; under the
    $50 minimum order it is 0, which also halts an account below $833.33 for good."""
    cap = RULES["cap_frac"] * equity
    if acct["size"] == "half_kelly":
        d = 0.5 * max(0.0, (bet["p"] - bet["m"]) / (1 - bet["m"])) * equity
    else:
        d = RULES["shadow_usd"]
    d = min(d, cap)
    return d if d >= RULES["min_order"] else 0.0


def fill_price(bet: dict) -> float:
    return bet["f_ask"] if bet["side"] == "yes" else (round(1 - bet["f_bid"], 4) if math.isfinite(bet["f_bid"]) else nan)


def run_accounts(st: pd.DataFrame) -> pd.DataFrame:
    """Every account's bets in event order: the $60 shadow book (the unit of every statistic, no equity
    feedback), its 2x-fee + 1-cent stress, the coin-flip side on the same strike, and the $1,000 path restarted
    at the start of each window."""
    bets, equity = [], {}
    for event, rows in st.groupby("event", sort=False):
        w = rows["window"].iat[0]
        if not w or event in SEEN:
            continue
        for name, acct in ACCOUNTS.items():
            bet = choose(acct, candidates(acct, rows))
            if bet is None:
                continue
            P = fill_price(bet)
            rec = dict(account=name, event=event, close_s=int(rows["close_s"].iat[0]), window=w, **bet, P=P)
            if not (math.isfinite(P) and 0 < P < 1 and bet["f_vol"] >= 1):
                bets.append(dict(rec, filled=False))
                continue
            won = (bet["side"] == "yes") == bool(bet["y"])
            c, pnl, prem = buy(RULES["shadow_usd"], P, won, bet["f_vol"])
            c2, pnl2, prem2 = buy(RULES["shadow_usd"], min(P + 0.01, 0.99), won, bet["f_vol"], fee_mult=2.0)
            coin = nan
            if math.isfinite(bet["f_ask"]) and math.isfinite(bet["f_bid"]):
                legs = [buy(RULES["shadow_usd"], px, ok, bet["f_vol"]) for px, ok in
                        ((bet["f_ask"], bet["y"] == 1), (1 - bet["f_bid"], bet["y"] == 0))]
                if all(leg[0] > 0 for leg in legs):
                    coin = 0.5 * sum(leg[1] / leg[2] for leg in legs)
            E = equity.setdefault((name, w), RULES["equity0"])
            d = stake(acct, bet, E)
            ca, pnla, _ = buy(d, P, won, bet["f_vol"]) if d else (0, 0.0, 0.0)
            equity[(name, w)] = E + pnla
            bets.append(dict(rec, filled=c > 0, won=won, contracts=c, pnl=pnl, premium=prem,
                             ret=pnl / prem if prem else nan, ret_stress=pnl2 / prem2 if prem2 else nan,
                             coin_ret=coin, stake=d, acct_contracts=ca, acct_pnl=pnla, equity=E + pnla))
    return pd.DataFrame(bets)


# ----------------------------------------------------------------------------- readout
def block_t(ret, close_s, start_s: int, alpha_ci: float = VERDICT["ci"]) -> dict:
    """Mean per-bet return with a cluster-robust SE over calendar blocks of VERDICT['block_days'] UTC days; the
    one-sided p of mean > 0 and the two-sided interval come from t(G - 1)."""
    r = np.asarray(ret, dtype=float)
    ok = np.isfinite(r)
    r, cs = r[ok], np.asarray(close_s)[ok]
    n = r.size
    if n < 2:
        return dict(n=int(n), mean=float(r.mean()) if n else nan, se=nan, t=nan, p=nan, lo=nan, hi=nan, G=0, sd=nan)
    blk = (cs // 86400 - start_s // 86400) // VERDICT["block_days"]      # 5-day blocks of whole UTC days
    m = r.mean()
    S = pd.Series(r - m).groupby(blk).sum().to_numpy()
    Gn = S.size
    se = math.sqrt(Gn / (Gn - 1) * float(np.sum(S ** 2))) / n if Gn > 1 else nan
    t = m / se if se and math.isfinite(se) and se > 0 else nan
    q = sps.t.ppf(0.5 + alpha_ci / 2, Gn - 1) if Gn > 1 else nan
    return dict(n=int(n), mean=float(m), se=float(se), t=float(t), G=int(Gn), sd=float(r.std(ddof=1)),
                p=float(sps.t.sf(t, Gn - 1)) if math.isfinite(t) else nan,
                lo=float(m - q * se) if math.isfinite(se) else nan, hi=float(m + q * se) if math.isfinite(se) else nan)


def skill(st: pd.DataFrame, pcol: str) -> dict:
    """Per-event mean log loss of the model against the market mid on the scored strikes, Diebold-Mariano
    (core.quant.forecast_eval.dm_test, two-sided p): skill means t < 0 and p / 2 <= VERDICT['skill_p']."""
    from core.quant import forecast_eval as FE
    s = st[st["scored"] & st[pcol].notna()]
    if s.empty:
        return dict(n_events=0, n_strikes=0, passed=False)
    eps = RULES["score"]["clip"]
    ll = lambda p, y: -(y * np.log(np.clip(p, eps, 1 - eps)) + (1 - y) * np.log(np.clip(1 - p, eps, 1 - eps)))  # noqa: E731
    s = s.assign(l_mod=ll(s[pcol], s["y"]), l_mkt=ll(s["mid"], s["y"]),
                 b_mod=(s[pcol] - s["y"]) ** 2, b_mkt=(s["mid"] - s["y"]) ** 2)
    per = s.groupby("event", sort=False)[["l_mod", "l_mkt"]].mean()
    dm = FE.dm_test(per["l_mod"].to_numpy(), per["l_mkt"].to_numpy()) if len(per) > 20 else dict(t=nan, p=nan)
    half = (dm["p"] / 2 if dm["t"] < 0 else 1 - dm["p"] / 2) if math.isfinite(dm["p"]) else nan   # H1: model loss lower
    return dict(n_events=int(len(per)), n_strikes=int(len(s)), logloss_model=float(s["l_mod"].mean()),
                logloss_market=float(s["l_mkt"].mean()), brier_model=float(s["b_mod"].mean()),
                brier_market=float(s["b_mkt"].mean()), dm_t=float(dm["t"]), p_one_sided=half,
                passed=bool(math.isfinite(dm["t"]) and dm["t"] < 0 and half <= VERDICT["skill_p"]),
                reliability_model=FE.reliability_table(s[pcol], s["y"]),
                reliability_market=FE.reliability_table(s["mid"], s["y"]))


def readout(ev: pd.DataFrame, st: pd.DataFrame, bets: pd.DataFrame, cals: dict) -> dict:
    """Per window: model skip rate, skill, each account's shadow-book statistics, Holm across the three accounts,
    the nulls, the $1,000 path and the pre-registered verdict (exploratory outside the forward window)."""
    from core.quant import gate_stats as GS
    out = dict(calibration=cals)
    for win in ("cal", "eval", "forward"):
        e = ev[(ev["window"] == win) & ~ev["seen"]]
        if e.empty:
            continue
        start = int(e["close_s"].min())
        has_data = e["spot"].notna() & (e["n_strikes"] > 0)
        skip = float(1 - e.loc[has_data, "model_ok"].mean()) if has_data.any() else nan
        W = dict(events=int(len(e)), events_with_data=int(has_data.sum()), model_skip_rate=skip,
                 skip_reasons=e.loc[has_data & ~e["model_ok"], "why"].str.split(":").str[0].value_counts().to_dict(),
                 from_utc=datetime.fromtimestamp(start, timezone.utc).isoformat()[:16],
                 to_utc=datetime.fromtimestamp(int(e["close_s"].max()), timezone.utc).isoformat()[:16],
                 exploratory=win != "forward", accounts={})
        sw = st[(st["window"] == win) & ~st["event"].isin(SEEN)]
        W["skill_raw"] = skill(sw, "p_raw")
        W["skill_cal"] = skill(sw, "p_cal") if sw["p_cal"].notna().any() else None
        b = bets[bets["window"] == win] if not bets.empty else bets
        for name, acct in ACCOUNTS.items():
            a = b[(b["account"] == name)] if not b.empty else b
            f = a[a["filled"]] if not a.empty else a
            stt = block_t(f["ret"], f["close_s"], start) if not f.empty else block_t([], [], start)
            stress = float(f["ret_stress"].mean()) if not f.empty else nan
            sd = stt["sd"]
            path = f.sort_values("close_s") if not f.empty else f
            R = dict(signals=int(len(a)), filled=int(len(f)), hit_rate=float(f["won"].mean()) if len(f) else nan,
                     mean_price=float(f["P"].mean()) if len(f) else nan, **{f"ret_{k}": v for k, v in stt.items()},
                     ret_stress_mean=stress, mde=VERDICT["mde_factor"] * sd / math.sqrt(stt["n"]) if stt["n"] > 1 else nan,
                     n_star=int(math.ceil((VERDICT["mde_factor"] * sd / VERDICT["target_edge"]) ** 2)) if math.isfinite(sd) else None,
                     equity_end=float(path["equity"].iat[-1]) if len(path) else RULES["equity0"],
                     equity_min=float(path["equity"].min()) if len(path) else RULES["equity0"],
                     acct_bets=int((path["acct_contracts"] > 0).sum()) if len(path) else 0)
            if len(f):
                cn = f[f["coin_ret"].notna()]
                R["vs_coin"] = block_t(cn["ret"] - cn["coin_ret"], cn["close_s"], start)
                et = pd.to_datetime(f["close_s"], unit="s", utc=True).dt.tz_convert(ET).dt.hour
                R["by_et_hour"] = f.groupby(et)["ret"].agg(["count", "mean"]).round(4).reset_index().values.tolist()
                sp = pd.cut(f["spread"], [-1, 0.0101, 0.0301, 1], labels=["<=1c", "2-3c", ">3c"])
                R["by_spread"] = f.groupby(sp, observed=True)["ret"].agg(["count", "mean"]).round(4).reset_index().values.tolist()
            W["accounts"][name] = R
        g, fl = W["accounts"]["PRED-GATED"], b[(b["account"] == "PRED-FLB") & b["filled"]] if not b.empty else b
        ga = b[(b["account"] == "PRED-GATED") & b["filled"]] if not b.empty else b
        if len(ga) and len(fl):
            blk = lambda x: (x["close_s"] // 86400 - start // 86400) // VERDICT["block_days"]  # noqa: E731
            d = (ga.groupby(blk(ga))["ret"].mean() - fl.groupby(blk(fl))["ret"].mean()).dropna()
            g["vs_flb"] = dict(blocks=int(d.size), mean=float(d.mean()) if d.size else nan,
                               p=float(sps.ttest_1samp(d, 0, alternative="greater").pvalue) if d.size > 2 else nan)
        ps = [W["accounts"][n]["ret_p"] for n in ACCOUNTS]
        holm = GS.holm_adjusted([p if math.isfinite(p) else 1.0 for p in ps])
        for n, h in zip(ACCOUNTS, holm):
            W["accounts"][n]["holm_p"] = float(h)
            W["accounts"][n]["verdict"] = verdict(n, W)
        out[win] = W
    return out


def verdict(name: str, W: dict) -> str:
    """REJECT: skill gate failed (model accounts) or the interval lies below 0. PAPER-CANDIDATE: Holm p and the
    interval clear, the stress mean is positive and the nulls are beaten. Else INCONCLUSIVE. A model skip rate above
    VERDICT['max_skip'] makes the model accounts INVALID. MDE and N* (the bets a target_edge needs) are reported,
    not gated: at a 1% target the forward window could never reach N* (owner's ruling, 2026-10-21)."""
    R = W["accounts"][name]
    if name in MODEL_ACCOUNTS and not W["model_skip_rate"] <= VERDICT["max_skip"]:
        return "INVALID"
    if R["ret_n"] == 0:
        return "NO-BETS"
    if name in MODEL_ACCOUNTS:
        sk = W["skill_cal"] if ACCOUNTS[name]["prob"] == "cal" else W["skill_raw"]
        if not (sk and sk["passed"]):
            return "REJECT"
    if R["ret_hi"] < 0:
        return "REJECT"
    nulls = [R.get("vs_coin", {}).get("p", nan)] if name in MODEL_ACCOUNTS else []
    if name == "PRED-GATED":
        nulls.append(R.get("vs_flb", {}).get("p", nan))
    beats = all(math.isfinite(p) and p <= VERDICT["null_p"] for p in nulls)
    if R["holm_p"] <= VERDICT["holm_alpha"] and R["ret_lo"] > 0 and R["ret_stress_mean"] > 0 and beats:
        return "PAPER-CANDIDATE"
    return "INCONCLUSIVE"


# ----------------------------------------------------------------------------- ledger
def trial_rows(run_utc: str) -> list[dict]:
    """One gate_ledger row per trading account. params hold everything that decides its trades, so a changed
    rule is a new configuration (a new trial) and a re-run of the same one appends nothing."""
    from core.quant import gate_ledger as GL
    return [dict(rule=FAMILY, timing_class="COMPLIANT", span=[ARCHIVE_START, "9999-12-31"], market="KALSHI",
                 run_utc=run_utc, phase="research", run_kind="trial", run_utc_anchor=GL.repo_anchor(),
                 params=json.loads(json.dumps(dict(account=name, rule=acct, shared=RULES,
                                                   underlying="BTC; Kalshi KXBTCD, settled on the 60 s BRTI average"),
                                              sort_keys=True)),
                 source=f"grokteam book {name}; {GUIDE}") for name, acct in ACCOUNTS.items()]


def register_trials(ledger_dir: Path | None = None) -> list:
    import config as QC
    from core.quant import gate_ledger as GL
    d = Path(ledger_dir or os.environ.get("GROKTEAM_LEDGER_DIR") or QC.macro_dir() / "ledgers")
    led = GL.family_ledger(FAMILY, d)
    run = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return [GL.register_trial(led, row, script="grokteam/book.py") for row in trial_rows(run)]


# ----------------------------------------------------------------------------- main
def frozen() -> dict | None:
    return json.loads(PREREG.read_text(encoding="utf-8")) if PREREG.exists() else None


def forward_gate(records: list[dict], fwd: list[str], failed: list[str], freeze_s: int, now_s: float,
                 smoke: bool = False, diffs=(), pending=()) -> tuple[list[dict], str]:
    """(records to replay, status) for the forward window, the one look of the pre-registration. Forward events
    (decision after the freeze) are dropped before FORWARD_END, on a smoke or partial run, once the look is on disk,
    while the code differs from the frozen record (VOID: nothing forward is shown), and while any of them is missing
    or not yet settled; only status 'look' replays them. `now_s` is the time the event listing was taken for."""
    keep = [r for r in records if r["decision_s"] <= freeze_s]
    if smoke or now_s < day_s(FORWARD_END) + 3600:
        return keep, f"blinded until {FORWARD_END}: {len(records) - len(keep)} forward events cached, none replayed"
    if LOOK.exists():
        return keep, "taken"
    if diffs:
        fix = "restore grokteam/out/frozen_book" + ("; reinstall the libraries in PREREG_book.json['versions']"
                                                    if "versions" in diffs else "")
        return keep, f"VOID: changed since the freeze ({', '.join(diffs)}); {fix}, then rerun"
    have = {r["event"] for r in records}
    missing = [e for e in fwd if e not in have or e in failed] + list(pending)
    if missing:
        return keep, f"incomplete: {len(missing)} forward events missing or unsettled (e.g. {missing[:3]}); rerun later"
    return records, "look"


def unsettled_in_window(freeze_s: int) -> list[str]:
    """Events of the forward window that have closed but not settled (or are still open): the look waits for them."""
    out = []
    for status in ("closed", "open"):
        cursor = ""
        while True:
            d = kalshi("/events", series_ticker=SERIES, status=status, limit=200, **({"cursor": cursor} if cursor else {}))
            out += [e["event_ticker"] for e in d.get("events", []) if e.get("strike_date")
                    and freeze_s < ts(e["strike_date"]) - RULES["decision_s"] and ts(e["strike_date"]) < day_s(FORWARD_END)]
            cursor = d.get("cursor") or ""
            if not cursor:
                break
    return out


def main(argv=None) -> dict:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--start", default=ARCHIVE_START)
    ap.add_argument("--end", default=None, help="last close date (UTC, exclusive); default now")
    ap.add_argument("--limit", type=int, default=0, help="smoke run: the last N events only; nothing registered")
    a = ap.parse_args(argv)
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    from grokteam import prereg
    code0, md0 = prereg.code_digests(), model_digest()          # the code this run loaded; checked again at the end
    partial = bool(a.limit) or a.end is not None or a.start != ARCHIVE_START   # never the freeze's input, never the look
    fz = frozen()
    if fz is None and prereg.FROZEN_COPY.exists():
        raise SystemExit(f"{PREREG} is missing but {prereg.FROZEN_COPY} exists: the freeze happened and its record is "
                         "lost. Restore it (OneDrive version history) before running; forward events stay withheld.")
    if not a.limit:
        reg = register_trials()
        print(f"ledger {FAMILY}: {sum(r.appended for r in reg)} new trial rows, {len(reg)} configurations")
    end_s = day_s(a.end) if a.end else int(time.time())
    evs = [e for e in settled_events(end_s) if day_s(a.start) <= e["close_s"] < min(end_s, day_s(FORWARD_END))]
    evs = evs[-a.limit:] if a.limit else evs
    print(f"{len(evs)} settled events from {a.start}", flush=True)
    records, failed = fetch_all(evs)
    freeze_s = ts(fz["frozen_utc"]) if fz else None
    status = None
    if freeze_s is not None:
        fwd = [e["event"] for e in evs if e["close_s"] - RULES["decision_s"] > freeze_s]
        at_look = not partial and end_s >= day_s(FORWARD_END) + 3600 and not LOOK.exists()
        records, status = forward_gate(records, fwd, failed, freeze_s, end_s, smoke=partial,
                                       diffs=prereg.check(fz) if at_look else (),
                                       pending=unsettled_in_window(freeze_s) if at_look else ())
        print(f"forward window: {status}", flush=True)
    ev, st = strike_table(records, freeze_s, md0)
    cal_rows = st[(st["window"] == "cal") & st["scored"] & st["p_raw"].notna() & ~st["event"].isin(SEEN)]
    cals = dict(cal=fit_calibration(cal_rows["p_raw"], cal_rows["y"]) if len(cal_rows) > 100 else None)
    arch = st[st["window"].isin(["cal", "eval"]) & st["scored"] & st["p_raw"].notna() & ~st["event"].isin(SEEN)]
    cals["archive"] = fit_calibration(arch["p_raw"], arch["y"]) if len(arch) > 100 else None
    cals["frozen"] = fz["calibration"] if fz else None
    st["p_cal"] = nan
    for win, key in (("eval", "cal"), ("forward", "frozen")):
        m = (st["window"] == win) & st["p_raw"].notna()
        if cals[key] and m.any():
            st.loc[m, "p_cal"] = calibrate(st.loc[m, "p_raw"], cals[key])
    bets = run_accounts(st)
    rep = readout(ev, st, bets, cals)
    drift = prereg.code_digests() != code0 or model_digest() != md0   # a pinned file edited while this ran
    rep.update(rules=RULES, accounts=ACCOUNTS, verdict_rules=VERDICT, model_digest=md0, code=code0,
               code_drift=drift, frozen_utc=fz["frozen_utc"] if fz else None, smoke=partial or drift,
               failed_events=failed, forward_status=status, run_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"))
    if status == "taken":
        rep["forward"] = json.loads(LOOK.read_text(encoding="utf-8"))["forward"]
    elif status == "look" and not drift:
        OUT.mkdir(parents=True, exist_ok=True)
        LOOK.write_text(json.dumps(dict(forward=rep["forward"], run_utc=rep["run_utc"], code=rep["code"]),
                                   indent=1, default=str), encoding="utf-8")
    elif status == "look":
        rep.pop("forward", None)
        rep["forward_status"] = "VOID: a pinned file changed during this run; rerun"
    out = OUT if not partial else OUT.parent / "book_smoke"     # a partial run never overwrites the archive
    out.mkdir(parents=True, exist_ok=True)
    ev.to_csv(out / "events.csv.gz", index=False)
    st.to_csv(out / "strikes.csv.gz", index=False)
    bets.to_csv(out / "bets.csv.gz", index=False)
    (out / "summary.json").write_text(json.dumps(rep, indent=1, default=str), encoding="utf-8")
    text = report_text(rep)
    (out / "readout.txt").write_text(text, encoding="utf-8")
    print(text)
    return rep


def report_text(rep: dict) -> str:
    L = [f"forward window: {rep['forward_status']}"] if rep.get("forward_status") else []
    if rep.get("failed_events"):
        L.append(f"{len(rep['failed_events'])} events failed to fetch (rerun to retry): {rep['failed_events'][:5]}")
    for win in ("cal", "eval", "forward"):
        W = rep.get(win)
        if not W:
            continue
        tag = "EXPLORATORY" if W["exploratory"] else "CONFIRMATORY"
        L.append(f"== {win} {W['from_utc']} .. {W['to_utc']} ({tag}): {W['events']} events, "
                 f"{W['events_with_data']} with data, model skipped {W['model_skip_rate']:.1%} {W['skip_reasons']}")
        for k in ("skill_raw", "skill_cal"):
            s = W.get(k)
            if s and s.get("n_events"):
                L.append(f"   {k}: log loss model {s['logloss_model']:.4f} vs market {s['logloss_market']:.4f}, "
                         f"Brier {s['brier_model']:.4f} vs {s['brier_market']:.4f}, DM t {s['dm_t']:.2f} "
                         f"p1 {s['p_one_sided']:.3f} -> {'PASS' if s['passed'] else 'FAIL'} ({s['n_events']} events)")
        for n, R in W["accounts"].items():
            L.append(f"   {n:11s} {R['filled']:5d}/{R['signals']:5d} filled  hit {R['hit_rate']:.3f}  "
                     f"net/$ {R['ret_mean']:+.4f} [{R['ret_lo']:+.4f}, {R['ret_hi']:+.4f}]  p {R['ret_p']:.3f} "
                     f"holm {R['holm_p']:.3f}  stress {R['ret_stress_mean']:+.4f}  MDE {R['mde']:.4f}  "
                     f"N* {R['n_star']}  $1,000 -> {R['equity_end']:.2f} (min {R['equity_min']:.2f})  {R['verdict']}")
    return "\n".join(L)


if __name__ == "__main__":
    main()
