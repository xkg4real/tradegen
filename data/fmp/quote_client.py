"""Financial Modeling Prep — read-only quotes for venues outside Korea.

Scope is deliberately one endpoint. FMP sells screeners, ratings and price
targets; none of those belong in the trading system, whose whole premise is
that the operator supplies the judgement. This client fetches a last price and
the time it was observed, and nothing else.

WHAT THE API ACTUALLY DOES (probed 2026-08-18, not assumed)
-----------------------------------------------------------
* `/api/v3/quote/...` is **dead**: HTTP 403 "Legacy Endpoint ... only available
  for legacy users who had a subscription prior to August 31, 2025". The
  current path is `/stable/quote?symbol=X`.
* A comma-separated `symbol` list returns **HTTP 402**, and `/stable/batch-quote`
  is a restricted endpoint. Batching is a paid feature, so this client issues
  one request per symbol.
* Any suffixed international symbol (`7203.T`, `VOD.L`, `SAP.DE`, …) returns
  **HTTP 402** on a plan without international coverage. US tickers work.

RATE
----
One request per symbol per tick would be ruinous: a 5-second tick is 720 calls
an hour for a single rule. `min_interval_s` therefore caps how often any one
symbol is actually refetched, and repeat calls inside that window are served
from memory. The default sits far below the engine's staleness bound, so the
cache can never be the reason a quote goes stale — it only stops the engine
asking the same question twice in a few seconds.
"""
from __future__ import annotations

import re
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, Sequence

try:
    import requests as _requests     # engine quote path: one attempt; the grace window is the retry
except Exception:                                    # pragma: no cover
    _requests = None

import config

BASE_URL = "https://financialmodelingprep.com/stable"


class FMPError(RuntimeError):
    pass


class FMPPlanError(FMPError):
    """HTTP 402 — the plan does not cover this symbol or endpoint.

    Separate from FMPError because it is permanent for a given symbol until the
    operator changes plan, so a caller can report it as a configuration problem
    rather than a transient outage.
    """


@dataclass(frozen=True)
class FMPQuote:
    symbol: str
    name: str
    price: Optional[float]
    change: Optional[float]
    change_pct: Optional[float]
    volume: Optional[float]
    market_cap: Optional[float]
    high: Optional[float]
    low: Optional[float]
    open: Optional[float]
    previous_close: Optional[float]
    exchange: str = ""
    as_of: str = ""                 # ISO-8601 UTC, or "" when FMP gave none
    source: str = "FMP"


def _f(value) -> Optional[float]:
    try:
        text = str(value).strip().replace(",", "")
        return float(text) if text not in ("", "-", "None", "null") else None
    except Exception:
        return None


def _as_of(raw) -> str:
    """Unix seconds -> ISO UTC. Returns "" rather than guessing."""
    try:
        seconds = int(raw)
    except (TypeError, ValueError):
        return ""
    if seconds <= 0:
        return ""
    try:
        return datetime.fromtimestamp(seconds, tz=timezone.utc).isoformat(
            timespec="seconds")
    except (OverflowError, OSError, ValueError):
        return ""


def _redact(text: str, key: str) -> str:
    if key:
        text = text.replace(key, "***")
    return re.sub(r"(?i)(apikey=)[^&\s]+", r"\1***", text)


class FMPQuoteClient:
    """Construction performs no network request."""

    def __init__(self, *, api_key: Optional[str] = None,
                 base_url: Optional[str] = None,
                 timeout_s: Optional[float] = None,
                 min_interval_s: Optional[float] = None,
                 clock=time.monotonic):
        self._key = api_key if api_key is not None else config.fmp_key()
        self.base_url = (base_url or config.FMP_BASE_URL).rstrip("/")
        self.timeout_s = (timeout_s if timeout_s is not None
                          else config.HTTP_TIMEOUT_SECONDS)
        self.min_interval_s = (min_interval_s if min_interval_s is not None
                               else config.FMP_MIN_INTERVAL_SECONDS)
        self._clock = clock
        self._lock = threading.RLock()
        self._cache: dict[str, tuple[float, FMPQuote]] = {}
        self._plan_blocked: dict[str, str] = {}
        # Why each symbol last failed. A batch that partially succeeds must
        # still be able to say what happened to the symbols it dropped;
        # otherwise the caller reports "no row" for a plan refusal.
        self._errors: dict[str, str] = {}

    @property
    def ready(self) -> bool:
        return bool(self._key) and _requests is not None

    def status(self) -> dict:
        if _requests is None:
            return {"ready": False, "reason": "requests library unavailable"}
        if not self._key:
            return {"ready": False,
                    "reason": "no FMP_API_KEY; markets outside Korea cannot be quoted",
                    "detail": "unconfigured"}
        return {"ready": True, "reason": "", "detail": "FMP_API_KEY set"}

    def error_for(self, symbol: str) -> str:
        """Why this symbol was not returned by the last call that wanted it."""
        with self._lock:
            return self._errors.get(symbol.strip().upper(), "")

    def plan_blocked(self) -> dict[str, str]:
        """Symbols this plan has refused, and why. Populated as they are hit."""
        with self._lock:
            return dict(self._plan_blocked)

    # -- fetch ---------------------------------------------------------------
    def quotes(self, symbols: Sequence[str]) -> dict[str, FMPQuote]:
        """One request per symbol, throttled by `min_interval_s`.

        A symbol the plan has already refused is skipped rather than retried
        every tick — a 402 is a subscription fact, not a transient failure.
        """
        wanted = [s.strip() for s in symbols if s and s.strip()]
        if not wanted:
            return {}
        if not self.ready:
            raise FMPError(self.status()["reason"])

        out: dict[str, FMPQuote] = {}
        errors: list[str] = []
        for symbol in wanted:
            key = symbol.upper()
            cached = self._cached(key)
            if cached is not None:
                out[key] = cached
                continue
            with self._lock:
                blocked = self._plan_blocked.get(key)
            if blocked:
                self._note(key, blocked)
                errors.append(blocked)
                continue
            try:
                quote = self._fetch_one(symbol)
            except FMPPlanError as exc:
                with self._lock:
                    self._plan_blocked[key] = str(exc)
                self._note(key, str(exc))
                errors.append(str(exc))
                continue
            except FMPError as exc:
                self._note(key, str(exc))
                errors.append(str(exc))
                continue
            if quote is None:
                self._note(key, f"FMP has no listing for {symbol}")
                continue
            with self._lock:
                self._cache[key] = (self._clock(), quote)
                self._errors.pop(key, None)
            out[key] = quote

        if not out and errors:
            raise FMPError(errors[0])
        return out

    def quote(self, symbol: str) -> Optional[FMPQuote]:
        return self.quotes([symbol]).get(symbol.strip().upper())

    # -- internals -----------------------------------------------------------
    def _note(self, key: str, reason: str) -> None:
        with self._lock:
            self._errors[key] = reason

    def _cached(self, key: str) -> Optional[FMPQuote]:
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return None
            fetched_at, quote = entry
            if self._clock() - fetched_at <= self.min_interval_s:
                return quote
            return None

    def _fetch_one(self, symbol: str) -> Optional[FMPQuote]:
        url = f"{self.base_url}/quote"
        try:
            response = _requests.get(
                url, params={"symbol": symbol, "apikey": self._key},
                timeout=self.timeout_s)
        except Exception as exc:
            raise FMPError(
                f"{type(exc).__name__}: {_redact(str(exc), self._key)}") from None

        if response.status_code == 402:
            raise FMPPlanError(
                f"FMP plan does not cover {symbol} (HTTP 402). Non-US venues "
                f"and multi-symbol requests need a paid international plan.")
        if response.status_code in (401, 403):
            raise FMPError(
                f"FMP rejected the request for {symbol} "
                f"(HTTP {response.status_code}): "
                f"{_redact(response.text[:160], self._key)}")
        if response.status_code == 429:
            raise FMPError("FMP rate limit reached (429).")
        if response.status_code >= 400:
            raise FMPError(f"FMP returned HTTP {response.status_code}: "
                           f"{_redact(response.text[:160], self._key)}")

        try:
            payload = response.json()
        except Exception:
            raise FMPError("FMP returned a non-JSON body.") from None

        if isinstance(payload, dict):
            message = (payload.get("Error Message") or payload.get("message")
                       or str(payload)[:160])
            raise FMPError(f"FMP: {_redact(str(message), self._key)}")
        if not isinstance(payload, list):
            raise FMPError("FMP returned an unexpected payload shape.")
        if not payload:
            return None                     # unknown symbol; not an error
        return self._to_quote(payload[0])

    @staticmethod
    def _to_quote(row: dict) -> FMPQuote:
        # The stable API renamed `changesPercentage` to `changePercentage`;
        # both are read so a future rename does not silently zero the field.
        change_pct = row.get("changePercentage")
        if change_pct is None:
            change_pct = row.get("changesPercentage")
        return FMPQuote(
            symbol=str(row.get("symbol") or "").strip(),
            name=str(row.get("name") or ""),
            price=_f(row.get("price")),
            change=_f(row.get("change")),
            change_pct=_f(change_pct),
            volume=_f(row.get("volume")),
            market_cap=_f(row.get("marketCap")),
            high=_f(row.get("dayHigh")),
            low=_f(row.get("dayLow")),
            open=_f(row.get("open")),
            previous_close=_f(row.get("previousClose")),
            exchange=str(row.get("exchange") or ""),
            as_of=_as_of(row.get("timestamp")),
        )
