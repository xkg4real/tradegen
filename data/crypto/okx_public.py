"""OKX public market data: keyless, read-only, GET only.

The live crypto paths read OKX here (odds bars, load_history's ...USDT symbols, the Crypto and Settings pages); Upbit
stays in crypto_client. crypto_client keeps BinancePublic byte for byte because the frozen grokteam BOOK desk and the
asset-expansion study import it and its sha256 is pinned (grokteam/out/PREREG_book.json,
research_lab/data_manifest.json); no live path calls it.

  * Spot daily: market/history-candles, bar=1Dutc (opens 00:00 UTC, the date Upbit's candle and bars.final_crypto
    use; plain 1D opens 16:00 UTC). 300 rows a call, newest first, paged back with `after` (exclusive). BTC-USDT and
    ETH-USDT start 2018-01-11. The forming bar is returned, as Upbit and Binance return theirs.
  * Funding of the USDT perpetual (BTC-USDT-SWAP): public/funding-rate-history, realizedRate. OKX keeps about three
    months; nothing older is on this endpoint.
  * Premium: public/mark-price, market/index-tickers and public/funding-rate (OKX has no single premiumIndex).

Every call goes through crypto_client._get, looked up at call time (the shared session, the throttle and the
suites' hermetic patches). The host execution already allow-lists is tried first and the documented production host
second, the way the Binance spot client tried its two hosts; a reply that is not an OKX envelope with code "0" fails
on the spot (a rate limit can come back as HTTP 200 with code 50011, and no other host would answer differently).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from data.crypto import crypto_client as CC
from data.crypto.crypto_client import Candles, CryptoError, FundingSeries

OKX_HOSTS = ("https://www.okx.com/api/v5",       # the host execution already allow-lists (probed 2026-11-03)
             "https://openapi.okx.com/api/v5")   # the production host the docs name (#overview-production-trading-services)
_PAGE = 300                                       # history-candles rows per call (the documented maximum)


def _inst(symbol: str) -> str:
    """BTCUSDT -> BTC-USDT; an OKX id (BTC-USDT, ETH-BTC) is kept."""
    s = symbol.strip().upper()
    if "-" in s:
        return s
    if s.endswith("USDT") and len(s) > 4:
        return f"{s[:-4]}-USDT"
    raise CryptoError(f"OKX: {symbol!r} is neither BASE-QUOTE (ETH-BTC) nor a ...USDT symbol")


def _okx(path: str, params: dict, *, label: str) -> list:
    last: Exception | None = None
    for base in OKX_HOSTS:
        try:
            r = CC._get(f"{base}{path}", params, label=label)
            break
        except CryptoError as exc:
            last = exc
    else:
        raise CryptoError(f"{label}: no OKX host answered ({last})")
    if not (isinstance(r, dict) and str(r.get("code")) == "0" and isinstance(r.get("data"), list)):
        code, msg = (r.get("code"), r.get("msg") or "") if isinstance(r, dict) else ("?", "not an OKX envelope")
        raise CryptoError(f"{label}: OKX code {code} {msg}".rstrip())
    return r["data"]


def _first(path: str, params: dict, *, label: str) -> dict:
    rows = _okx(path, params, label=label)
    if not rows or not isinstance(rows[0], dict):
        raise CryptoError(f"{label}: OKX returned no row")
    return rows[0]


def _utc(ms) -> datetime:
    return datetime.fromtimestamp(int(ms) / 1000, tz=timezone.utc)


class OKXPublic:
    source = "OKX"

    def daily(self, symbol: str = "BTC-USDT", *, days: int = 504) -> Candles:
        """The last `days` UTC daily candles of a spot pair, oldest first."""
        sym, inst = symbol.strip().upper(), _inst(symbol)
        rows: dict[int, list] = {}
        after = None
        for _ in range(days // 100 + 2):          # room for 100-row pages, should OKX ever cap below _PAGE
            params = {"instId": inst, "bar": "1Dutc", "limit": min(_PAGE, max(1, days - len(rows)))}
            if after is not None:
                params["after"] = after
            fresh = [k for k in _okx("/market/history-candles", params, label=f"OKX {inst}") if int(k[0]) not in rows]
            for k in fresh:
                rows[int(k[0])] = k
            if not fresh or len(rows) >= days:
                break
            after = min(rows)                     # exclusive: the next page is older
        if not rows:
            raise CryptoError(f"OKX returned no candles for {inst}.")
        ts = sorted(rows)
        col = lambda i: tuple(float(rows[t][i]) for t in ts)                 # noqa: E731
        return Candles(symbol=sym, dates=tuple(_utc(t).strftime("%Y-%m-%d") for t in ts), close=col(4), open=col(1),
                       high=col(2), low=col(3), volume=col(5), quote_volume=col(7), source=self.source,
                       note=f"OKX spot 1Dutc candle, UTC, {inst.rsplit('-', 1)[1]} quote")

    def funding(self, symbol: str = "BTCUSDT", *, days: int = 730) -> FundingSeries:
        """Settled funding of the USDT perpetual over the last `days`, as far back as OKX keeps it (about three
        months)."""
        # ponytail: one call; 400 rows is ~133 days at 8 h. Page with after= if a 1-4 h coin is ever asked for.
        inst = _inst(symbol) + "-SWAP"
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        page = _okx("/public/funding-rate-history", {"instId": inst, "limit": 400}, label=f"OKX funding {inst}")
        try:
            rows = {int(r["fundingTime"]): float(r["realizedRate"]) for r in page if _utc(r["fundingTime"]) >= cutoff}
        except (KeyError, TypeError, ValueError) as exc:
            raise CryptoError(f"OKX funding {inst}: malformed row ({type(exc).__name__})") from None
        if not rows:
            raise CryptoError(f"OKX returned no funding history for {inst}.")
        ts = sorted(rows)
        return FundingSeries(symbol=symbol.upper(), times=tuple(_utc(t).isoformat(timespec="minutes") for t in ts),
                             rates=tuple(rows[t] for t in ts), source=self.source)

    def premium_index(self, symbol: str = "BTCUSDT") -> dict:
        """The fields Binance's premiumIndex gave, from three OKX calls."""
        inst = _inst(symbol)
        swap = inst + "-SWAP"
        mark = float(_first("/public/mark-price", {"instType": "SWAP", "instId": swap}, label="OKX mark")["markPx"])
        index = float(_first("/market/index-tickers", {"instId": inst}, label="OKX index")["idxPx"])
        fr = _first("/public/funding-rate", {"instId": swap}, label="OKX funding rate")
        return {"symbol": symbol.upper(), "mark": mark, "index": index,
                "premium_pct": (mark / index - 1.0) * 100 if index else 0.0,
                "last_funding_rate": float(fr.get("fundingRate") or 0.0),
                "next_funding_time": _utc(fr.get("fundingTime") or 0).isoformat(timespec="minutes"),
                "as_of": datetime.now(timezone.utc).isoformat(timespec="seconds")}


def provider_status() -> list[dict]:
    """crypto_client's rows with its Binance row replaced by OKX's (crypto_client itself is hash-pinned)."""
    okx = {"id": "okx", "label": "OKX (public candles, funding)", "ready": CC._requests is not None, "vars": (),
           "note": "Keyless public data only; this reads no OKX account. Funding history reaches back about three "
                   "months. Korea blocks some offshore exchange sites: test below."}
    return [okx if r["id"] == "binance" else r for r in CC.provider_status()]


def probe() -> dict:
    """One cheap call per host. Never raises."""
    out = {}
    for name, fn in (("upbit", lambda: CC.UpbitPublic().ticker("KRW-BTC")[0]["price"]),
                     ("okx_spot", lambda: OKXPublic().daily("BTC-USDT", days=2).close[-1]),
                     ("okx_swap", lambda: OKXPublic().premium_index("BTCUSDT")["mark"])):
        try:
            v = fn()
            out[name] = {"ok": bool(v), "detail": f"last {v:,.2f}"}
        except Exception as exc:
            out[name] = {"ok": False, "detail": f"{type(exc).__name__}: {exc}"}
    return out
