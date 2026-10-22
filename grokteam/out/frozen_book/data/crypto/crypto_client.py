"""Crypto market data for QUANTGEN — keyless first, read-only always.

Two public providers and one optional read-only account:

  * **Upbit** (FIU-registered Korean exchange) — daily candles for KRW pairs
    (KRW-BTC from 2017-09-25), 200 rows per call, 10 requests/s per IP.
  * **Binance** (public market data only; no account is ever assumed) — spot
    klines (BTCUSDT from 2017-08-17, 1,000 per call), USDⓈ-M perpetual funding
    history (from 2019-09-10, 8-hourly, 1,000 per call), the premium index and
    the 30-day open-interest history. Spot data is read from the dedicated
    data host first and the main host second, because Korean network blocks
    of unregistered exchanges have been announced for the main domains.
  * **Upbit account, 자산조회 (balance) scope only** — `GET /v1/accounts` with a
    stdlib HS512 JWT when UPBIT_ACCESS_KEY / UPBIT_SECRET_KEY are set. The
    balances carry `avg_buy_price`, which is the cost-basis record the 2027
    virtual-asset tax will need.

REFUSALS, BY CONSTRUCTION
-------------------------
* No order, cancel, withdrawal, deposit-address or transfer endpoint exists in
  this module, on any venue, whatever scope a supplied key carries.
* No private key, seed phrase, keystore or hardware-wallet secret is ever
  requested, stored or parsed; a future on-chain reader takes public addresses.
* No transaction is ever signed. No account on an unregistered foreign
  exchange is assumed: Binance is data only.
* No third-party crypto library: three `requests.get` patterns and ten lines
  of `hmac` cover every endpoint above.

Routing mirrors `core.quant.history`: an explicit provider that fails RAISES
`CryptoError`; only the `auto` route in `core.quant.history` degrades.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import config

try:
    from data.net import session as _requests        # shared session: retry + backoff
except Exception:                                    # pragma: no cover
    _requests = None

UPBIT = "https://api.upbit.com/v1"
BINANCE_SPOT = ("https://data-api.binance.vision/api/v3", "https://api.binance.com/api/v3")
BINANCE_FAPI = "https://fapi.binance.com"
COINGECKO = "https://api.coingecko.com/api/v3"

_UPBIT_PAGE, _BINANCE_PAGE, _FUNDING_PAGE = 200, 1000, 1000
_MIN_GAP_S = 0.12                                    # ≤ ~8 req/s, under Upbit's 10/s group limit
_last_call = {"t": 0.0}


class CryptoError(RuntimeError):
    """A provider was asked and could not answer; the message says why."""


@dataclass(frozen=True)
class Candles:
    symbol: str
    dates: tuple[str, ...]                # ISO date (daily) or ISO datetime (intraday), ascending
    close: tuple[float, ...]
    open: tuple[float, ...] = ()
    high: tuple[float, ...] = ()
    low: tuple[float, ...] = ()
    volume: tuple[float, ...] = ()        # base volume
    quote_volume: tuple[float, ...] = ()  # quote-currency turnover (KRW on Upbit, USDT on Binance)
    source: str = ""
    note: str = ""

    def __len__(self) -> int:
        return len(self.close)

    def to_history(self, symbol: str | None = None):
        from core.quant.history import History
        return History(symbol=symbol or self.symbol, source=self.source, dates=self.dates,
                       closes=self.close, note=self.note)


@dataclass(frozen=True)
class FundingSeries:
    symbol: str
    times: tuple[str, ...]                # ISO datetime UTC, ascending, 8-hourly
    rates: tuple[float, ...]              # decimal per funding interval
    source: str = "BINANCE"

    def __len__(self) -> int:
        return len(self.rates)

    def daily(self) -> dict[str, float]:
        """Sum of the funding rates paid per UTC day (three intervals)."""
        out: dict[str, float] = {}
        for t, r in zip(self.times, self.rates):
            out[t[:10]] = out.get(t[:10], 0.0) + r
        return out


def _throttle() -> None:
    gap = time.monotonic() - _last_call["t"]
    if gap < _MIN_GAP_S:
        time.sleep(_MIN_GAP_S - gap)
    _last_call["t"] = time.monotonic()


def _get(url: str, params: dict | None = None, headers: dict | None = None, *, label: str) -> Any:
    if _requests is None:
        raise CryptoError("The requests package is not installed.")
    _throttle()
    try:
        resp = _requests.get(url, params=params or {}, headers=headers or {},
                             timeout=config.HTTP_TIMEOUT_SECONDS)
    except Exception as exc:
        raise CryptoError(f"{label}: {type(exc).__name__}") from None
    if resp.status_code == 429:
        raise CryptoError(f"{label}: rate limited (HTTP 429); slow down")
    if resp.status_code != 200:
        raise CryptoError(f"{label}: HTTP {resp.status_code}")
    try:
        return resp.json()
    except Exception:
        raise CryptoError(f"{label}: response was not JSON") from None


# --------------------------------------------------------------------------- #
# Upbit public
# --------------------------------------------------------------------------- #
class UpbitPublic:
    source = "UPBIT"

    def daily(self, market: str = "KRW-BTC", *, days: int = 504) -> Candles:
        """Daily candles (KST 09:00 boundary), paged backwards with `to`."""
        market = market.upper()
        rows: dict[str, dict] = {}
        to: Optional[str] = None
        for _ in range(days // _UPBIT_PAGE + 2):
            params = {"market": market, "count": min(_UPBIT_PAGE, max(1, days - len(rows)))}
            if to:
                params["to"] = to
            page = _get(f"{UPBIT}/candles/days", params, label=f"Upbit {market}")
            if not isinstance(page, list) or not page:
                break
            fresh = 0
            for r in page:
                d = str(r.get("candle_date_time_utc") or "")[:10]
                if d and d not in rows:
                    rows[d] = r; fresh += 1
            if not fresh or len(rows) >= days:
                break
            oldest = min(rows)
            to = f"{oldest}T00:00:00Z"
        if not rows:
            raise CryptoError(f"Upbit returned no candles for {market}.")
        ds = sorted(rows)
        g = lambda k: tuple(float(rows[d].get(k) or 0.0) for d in ds)   # noqa: E731
        return Candles(symbol=market, dates=tuple(ds), close=g("trade_price"), open=g("opening_price"),
                       high=g("high_price"), low=g("low_price"), volume=g("candle_acc_trade_volume"),
                       quote_volume=g("candle_acc_trade_price"), source=self.source,
                       note="Upbit daily candle, UTC date, KRW quote")

    def ticker(self, markets: list[str] | str = "KRW-BTC") -> list[dict]:
        m = ",".join(markets) if isinstance(markets, list) else markets
        page = _get(f"{UPBIT}/ticker", {"markets": m.upper()}, label="Upbit ticker")
        return [{"market": r.get("market"), "price": float(r.get("trade_price") or 0.0),
                 "change_pct": float(r.get("signed_change_rate") or 0.0) * 100,
                 "volume_24h_krw": float(r.get("acc_trade_price_24h") or 0.0),
                 "as_of": datetime.now(timezone.utc).isoformat(timespec="seconds")} for r in page]


# --------------------------------------------------------------------------- #
# Binance public (data only)
# --------------------------------------------------------------------------- #
def _binance_spot(path: str, params: dict, *, label: str) -> Any:
    last: Exception | None = None
    for base in BINANCE_SPOT:
        try:
            return _get(f"{base}{path}", params, label=label)
        except CryptoError as exc:
            last = exc
    raise CryptoError(f"{label}: no Binance spot host answered ({last})")


class BinancePublic:
    source = "BINANCE"

    def daily(self, symbol: str = "BTCUSDT", *, days: int = 504, interval: str = "1d",
              market: str = "spot") -> Candles:
        """Klines paged backwards with endTime. interval 1d (default) or 1h;
        market 'spot' (/api/v3) or 'perp' (/fapi/v1, from 2019-09-08)."""
        symbol = symbol.upper()
        rows: dict[int, list] = {}
        end_ms: Optional[int] = None
        per_call = 1500 if market == "perp" else _BINANCE_PAGE
        for _ in range(days // per_call + 2):
            params = {"symbol": symbol, "interval": interval, "limit": min(per_call, max(1, days - len(rows)))}
            if end_ms:
                params["endTime"] = end_ms
            if market == "perp":
                page = _get(f"{BINANCE_FAPI}/fapi/v1/klines", params, label=f"Binance perp {symbol}")
            else:
                page = _binance_spot("/klines", params, label=f"Binance {symbol}")
            if not isinstance(page, list) or not page:
                break
            fresh = 0
            for k in page:
                t = int(k[0])
                if t not in rows:
                    rows[t] = k; fresh += 1
            if not fresh or len(rows) >= days:
                break
            end_ms = min(rows) - 1
        if not rows:
            raise CryptoError(f"Binance returned no klines for {symbol}.")
        ts = sorted(rows)
        fmt = (lambda t: datetime.fromtimestamp(t / 1000, tz=timezone.utc).strftime("%Y-%m-%d")) if interval == "1d" \
            else (lambda t: datetime.fromtimestamp(t / 1000, tz=timezone.utc).isoformat(timespec="minutes"))
        col = lambda i: tuple(float(rows[t][i]) for t in ts)                 # noqa: E731
        return Candles(symbol=symbol, dates=tuple(fmt(t) for t in ts), close=col(4), open=col(1),
                       high=col(2), low=col(3), volume=col(5), quote_volume=col(7), source=self.source,
                       note=f"Binance {market} {interval} kline, UTC, {symbol[-4:]} quote")

    def funding(self, symbol: str = "BTCUSDT", *, days: int = 730) -> FundingSeries:
        """8-hourly funding history, paged by explicit windows (the endpoint
        ignores startTime=0). ~333 days per 1,000-row call."""
        symbol = symbol.upper()
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=days)
        rows: dict[int, float] = {}
        cursor = start
        for _ in range(days // 300 + 3):
            page = _get(f"{BINANCE_FAPI}/fapi/v1/fundingRate",
                        {"symbol": symbol, "startTime": int(cursor.timestamp() * 1000),
                         "endTime": int(end.timestamp() * 1000), "limit": _FUNDING_PAGE},
                        label=f"Binance funding {symbol}")
            if not isinstance(page, list) or not page:
                break
            for r in page:
                rows[int(r["fundingTime"])] = float(r["fundingRate"])
            last = max(int(r["fundingTime"]) for r in page)
            if len(page) < _FUNDING_PAGE or last >= int(end.timestamp() * 1000) - 1:
                break
            cursor = datetime.fromtimestamp(last / 1000 + 1, tz=timezone.utc)
        if not rows:
            raise CryptoError(f"Binance returned no funding history for {symbol}.")
        ts = sorted(rows)
        return FundingSeries(symbol=symbol,
                             times=tuple(datetime.fromtimestamp(t / 1000, tz=timezone.utc)
                                         .isoformat(timespec="minutes") for t in ts),
                             rates=tuple(rows[t] for t in ts))

    def premium_index(self, symbol: str = "BTCUSDT") -> dict:
        r = _get(f"{BINANCE_FAPI}/fapi/v1/premiumIndex", {"symbol": symbol.upper()}, label="Binance premium")
        mark, index = float(r.get("markPrice") or 0.0), float(r.get("indexPrice") or 0.0)
        return {"symbol": symbol.upper(), "mark": mark, "index": index,
                "premium_pct": (mark / index - 1.0) * 100 if index else 0.0,
                "last_funding_rate": float(r.get("lastFundingRate") or 0.0),
                "next_funding_time": datetime.fromtimestamp(int(r.get("nextFundingTime") or 0) / 1000,
                                                            tz=timezone.utc).isoformat(timespec="minutes"),
                "as_of": datetime.now(timezone.utc).isoformat(timespec="seconds")}

    def open_interest_hist(self, symbol: str = "BTCUSDT", *, period: str = "1d", limit: int = 30) -> list[dict]:
        """Last 30 days only (the endpoint's archive); accumulate locally for more."""
        page = _get(f"{BINANCE_FAPI}/futures/data/openInterestHist",
                    {"symbol": symbol.upper(), "period": period, "limit": min(limit, 500)},
                    label="Binance open interest")
        return [{"time": datetime.fromtimestamp(int(r["timestamp"]) / 1000, tz=timezone.utc).isoformat(timespec="minutes"),
                 "open_interest": float(r.get("sumOpenInterest") or 0.0),
                 "open_interest_usd": float(r.get("sumOpenInterestValue") or 0.0)} for r in page]


# --------------------------------------------------------------------------- #
# CoinGecko public (universe only; history is capped at 365 days keylessly)
# --------------------------------------------------------------------------- #
def coingecko_top(n: int = 20) -> list[dict]:
    page = _get(f"{COINGECKO}/coins/markets", {"vs_currency": "usd", "order": "market_cap_desc",
                                               "per_page": min(max(n, 1), 250), "page": 1}, label="CoinGecko markets")
    return [{"id": r.get("id"), "symbol": str(r.get("symbol") or "").upper(), "name": r.get("name"),
             "market_cap": float(r.get("market_cap") or 0.0), "price": float(r.get("current_price") or 0.0)}
            for r in page]


# --------------------------------------------------------------------------- #
# Upbit account — 자산조회 (read) scope only
# --------------------------------------------------------------------------- #
def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def upbit_jwt(access_key: str, secret_key: str, query: str = "") -> str:
    """HS512 JWT per docs.upbit.com/kr/reference/auth: payload access_key + nonce
    (+ SHA512 query_hash when a query string is sent)."""
    header = _b64url(json.dumps({"alg": "HS512", "typ": "JWT"}, separators=(",", ":")).encode())
    payload: dict = {"access_key": access_key, "nonce": str(uuid.uuid4())}
    if query:
        payload["query_hash"] = hashlib.sha512(query.encode()).hexdigest()
        payload["query_hash_alg"] = "SHA512"
    body = _b64url(json.dumps(payload, separators=(",", ":")).encode())
    sig = hmac.new(secret_key.encode(), f"{header}.{body}".encode(), hashlib.sha512).digest()
    return f"{header}.{body}.{_b64url(sig)}"


class UpbitAccount:
    """Balances only. There is no order path in this class or this module."""

    def __init__(self):
        self.ready = config.upbit_ready() and _requests is not None

    def balances(self) -> list[dict]:
        if not self.ready:
            raise CryptoError("Set UPBIT_ACCESS_KEY and UPBIT_SECRET_KEY (자산조회 scope) to read balances.")
        access, secret = config.upbit_keys()
        token = upbit_jwt(access, secret)
        page = _get(f"{UPBIT}/accounts", headers={"Authorization": f"Bearer {token}"}, label="Upbit accounts")
        out = []
        for r in page if isinstance(page, list) else []:
            bal, locked = float(r.get("balance") or 0.0), float(r.get("locked") or 0.0)
            out.append({"currency": r.get("currency"), "balance": bal, "locked": locked,
                        "avg_buy_price": float(r.get("avg_buy_price") or 0.0),
                        "unit_currency": r.get("unit_currency"), "total": bal + locked})
        return out


# --------------------------------------------------------------------------- #
# Status and probe
# --------------------------------------------------------------------------- #
def provider_status() -> list[dict]:
    return [
        {"id": "upbit", "label": "Upbit (public candles)", "ready": _requests is not None, "vars": (),
         "note": "Keyless. KRW-BTC daily since 2017-09-25; FIU-registered venue."},
        {"id": "binance", "label": "Binance (public klines, funding)", "ready": _requests is not None, "vars": (),
         "note": "Keyless data only; no account is ever assumed. Hosts may be blocked in Korea: test below."},
        {"id": "upbit_account", "label": "Upbit account (자산조회 only)", "ready": config.upbit_ready(),
         "vars": ("UPBIT_ACCESS_KEY", "UPBIT_SECRET_KEY"),
         "note": "Issue the key with 자산조회 scope only, allow-list this IP; keys expire after one year. "
                 "QUANTGEN never implements an order path."},
    ]


def probe() -> dict:
    """One cheap call per host. Never raises."""
    out = {}
    for name, fn in (("upbit", lambda: UpbitPublic().ticker("KRW-BTC")[0]["price"]),
                     ("binance_spot", lambda: BinancePublic().daily("BTCUSDT", days=2).close[-1]),
                     ("binance_futures", lambda: BinancePublic().premium_index("BTCUSDT")["mark"])):
        try:
            v = fn()
            out[name] = {"ok": bool(v), "detail": f"last {v:,.2f}"}
        except Exception as exc:
            out[name] = {"ok": False, "detail": f"{type(exc).__name__}: {exc}"}
    return out


if __name__ == "__main__":
    # Offline self-check: JWT shape and the paging/parsing on a fake transport.
    tok = upbit_jwt("A" * 40, "S" * 40, "market=KRW-BTC")
    h, b, s = tok.split(".")
    hdr = json.loads(base64.urlsafe_b64decode(h + "=="))
    pay = json.loads(base64.urlsafe_b64decode(b + "=="))
    assert hdr == {"alg": "HS512", "typ": "JWT"} and pay["access_key"] == "A" * 40
    assert pay["query_hash"] == hashlib.sha512(b"market=KRW-BTC").hexdigest() and pay["query_hash_alg"] == "SHA512"
    assert "query_hash" not in json.loads(base64.urlsafe_b64decode(upbit_jwt("a", "b").split(".")[1] + "=="))
    import sys
    me = sys.modules[__name__]
    calls = []

    def fake_get(url, params=None, headers=None, *, label):
        calls.append((url, dict(params or {})))
        if "candles/days" in url:
            to = params.get("to", "2026-09-25T00:00:00Z")[:10]
            d0 = datetime.fromisoformat(to)
            return [{"candle_date_time_utc": (d0 - timedelta(days=i + (1 if "to" in params else 0))).strftime("%Y-%m-%dT00:00:00"),
                     "trade_price": 100 + i, "opening_price": 99, "high_price": 101, "low_price": 98,
                     "candle_acc_trade_volume": 1, "candle_acc_trade_price": 100} for i in range(params["count"])]
        if "klines" in url:
            end = params.get("endTime", int(datetime(2026, 9, 25, tzinfo=timezone.utc).timestamp() * 1000))
            return [[end - i * 86_400_000, "1", "2", "0.5", str(50 + i), "9", 0, "450"] for i in range(params["limit"])]
        if "fundingRate" in url:
            st = params["startTime"]
            return [{"fundingTime": st + i * 8 * 3_600_000, "fundingRate": "0.0001"} for i in range(3)]
        raise AssertionError(url)
    me._get = fake_get
    c = UpbitPublic().daily("krw-btc", days=450)
    assert len(c) == 450 and c.dates == tuple(sorted(c.dates)) and c.symbol == "KRW-BTC", (len(c), c.symbol)
    assert len([u for u, _ in calls if "candles" in u]) == 3
    k = BinancePublic().daily("btcusdt", days=1500)
    assert len(k) == 1500 and k.dates[0] < k.dates[-1] and k.close[-1] == 50.0
    f = BinancePublic().funding("BTCUSDT", days=10)
    assert len(f) == 3 and abs(sum(f.daily().values()) - 0.0003) < 1e-12
    print("ok")
