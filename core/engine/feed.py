"""Turns whatever a provider returns into the `Quote` the evaluator wants.

Responsibilities that do not belong in the evaluator:

  * **Routing.** `core.markets` says which provider answers for a market and
    what suffix that provider wants on the symbol. Nothing here hard-codes a
    venue; adding one is a row in that table.

  * **Grouping by provider.** A tick needs a quote for every active rule, so
    `fetch_many` collects the symbols per provider and hands each provider its
    whole list at once. Whether that becomes one request or many is the
    provider's business: FMP's multi-symbol endpoints are a paid feature
    (HTTP 402 on this plan), so its client loops and throttles internally.

  * **Remembering the previous price.** `CROSSES_UP` and `CROSSES_DOWN` are the
    only conditions that need history, and they need exactly one observation of
    it. Keeping it here leaves the evaluator a pure function of (rule, quote).

  * **Counting misses.** A single timeout must not stop the engine, and a
    feed that stays down must. The feed counts recent failed fetches per
    symbol (`misses`; a good quote pays one back) and records whether the failure is one that waiting
    cannot fix (`is_permanent`: plan refusal, unconfigured provider, unknown
    venue). The runtime turns those two facts into a bounded grace window.

  * **Refusing to invent a timestamp.** If a provider returns a row with no
    `as_of`, this does *not* stamp it "now". A fabricated timestamp would
    defeat the staleness guard entirely — the engine would trade happily on a
    week-old row because the feed told it the row was fresh. A quote with no
    usable timestamp is returned as `None`, which the evaluator treats as
    missing data and halts on.

Providers are constructed lazily. A build with no FMP key must still start, and
an operator with only Korean rules should never cause an FMP client to exist.
"""
from __future__ import annotations

import threading
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Iterable, Optional

from core import markets
from core.engine.evaluator import Quote


def _to_decimal(value) -> Optional[Decimal]:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None


def _to_datetime(value) -> Optional[datetime]:
    """Parse a provider timestamp. Returns None rather than guessing."""
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    text = str(value).strip()
    for parse in (
        lambda s: datetime.fromisoformat(s),
        lambda s: datetime.strptime(s, "%Y%m%d%H%M%S"),
        lambda s: datetime.strptime(s, "%Y-%m-%d %H:%M:%S"),
        lambda s: datetime.strptime(s, "%Y%m%d"),
        lambda s: datetime.strptime(s, "%Y-%m-%d"),
    ):
        try:
            parsed = parse(text)
        except (ValueError, TypeError):
            continue
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    return None


class QuoteFeed:
    def __init__(self, krx_gateway=None, fmp_client=None):
        self.krx = krx_gateway
        self._fmp = fmp_client
        self._fmp_resolved = fmp_client is not None
        self._lock = threading.RLock()
        self._previous: dict[str, Decimal] = {}
        self._last_error: dict[str, str] = {}
        self._misses: dict[str, int] = {}       # failed fetches, minus one per good quote
        self._permanent: set[str] = set()       # failures a retry cannot fix

    # -- providers -----------------------------------------------------------
    @property
    def fmp(self):
        """Built on first use so a missing key never blocks startup."""
        if not self._fmp_resolved:
            with self._lock:
                if not self._fmp_resolved:
                    try:
                        from data.fmp import FMPQuoteClient
                        self._fmp = FMPQuoteClient()
                    except Exception:
                        self._fmp = None
                    self._fmp_resolved = True
        return self._fmp

    def provider_status(self) -> list[dict]:
        """Presence-only report, for Settings and the rule builder."""
        out = []
        if self.krx is not None:
            for row in self.krx.status():
                out.append({"scope": "KRX", **row})
        client = self.fmp
        status = (client.status() if client is not None
                  else {"ready": False, "reason": "FMP client unavailable"})
        out.append({"scope": "Global", "provider": "FMP", **status})
        return out

    # -- reads ---------------------------------------------------------------
    def last_error(self, symbol: str) -> str:
        with self._lock:
            return self._last_error.get(symbol, "")

    def previous(self, symbol: str) -> Optional[Decimal]:
        with self._lock:
            return self._previous.get(symbol)

    def misses(self, symbol: str) -> int:
        """Failed fetches of this symbol still held against it: each failure
        adds one, each good quote pays one back."""
        with self._lock:
            return self._misses.get(symbol, 0)

    def is_permanent(self, symbol: str) -> bool:
        """True when the last failure is one that trying again cannot fix."""
        with self._lock:
            return symbol in self._permanent

    def degraded(self) -> list[tuple[str, int, str]]:
        """(symbol, misses, last error) for each symbol whose last fetch failed."""
        with self._lock:
            return [(s, n, self._last_error[s]) for s, n in sorted(self._misses.items())
                    if n > 0 and s in self._last_error]

    def clear_misses(self) -> None:
        """A fresh grace window. Called when the operator arms the engine."""
        with self._lock:
            self._misses.clear()

    def reset(self) -> None:
        """Practice reset also drops crossing history: a stale prior price
        would make the first evaluation afterwards look like a crossing."""
        with self._lock:
            self._previous.clear()
            self._last_error.clear()
            self._misses.clear()
            self._permanent.clear()

    # -- fetch ---------------------------------------------------------------
    def fetch(self, symbol: str, market: str) -> Optional[Quote]:
        return self.fetch_many([(symbol, market)]).get(symbol)

    def fetch_many(self, pairs: Iterable[tuple[str, str]]
                   ) -> dict[str, Optional[Quote]]:
        """One request per provider, not per symbol."""
        wanted = [(s, m) for s, m in pairs if s]
        by_provider: dict[str, list[tuple[str, str]]] = {}
        results: dict[str, Optional[Quote]] = {}

        for symbol, market in wanted:
            provider = markets.provider_for(market)
            if not provider:
                self._fail(symbol,
                           f"market {market or '(blank)'} is not a known venue",
                           permanent=True)
                results[symbol] = None
                continue
            by_provider.setdefault(provider, []).append((symbol, market))

        for symbol, market in by_provider.get(markets.KRX, []):
            price, as_of, source = self._from_krx(symbol)
            # An empty source means `_from_krx` already recorded why it failed;
            # passing that on to `_record` would overwrite the real reason with
            # "no usable price".
            results[symbol] = (self._record(symbol, price, as_of, source)
                               if source else None)

        for symbol, quote in self._from_fmp(by_provider.get(markets.FMP, [])).items():
            results[symbol] = quote

        with self._lock:
            # Once per symbol, not per (symbol, market) pair. A good quote pays
            # one miss back rather than clearing the count, so a feed that
            # fails most passes still runs out of grace instead of leaving the
            # engine armed and mostly blind.
            for symbol in {s for s, _ in wanted}:
                held = self._misses.get(symbol, 0)
                self._misses[symbol] = (max(0, held - 1) if results.get(symbol) is not None
                                        else held + 1)
        return results

    # -- provider adapters ---------------------------------------------------
    def _from_krx(self, symbol: str):
        """-> (price, as_of, source). Any failure yields (None, None, '')."""
        if self.krx is None:
            self._fail(symbol, "KRX gateway not available", permanent=True)
            return None, None, ""
        try:
            answer = self.krx.quote(symbol)
        except Exception as exc:
            self._fail(symbol, f"{type(exc).__name__}: {exc}")
            return None, None, ""
        if not answer or answer.data is None:
            self._fail(symbol, answer.reason or "no data")
            return None, None, ""
        quote = answer.data
        return (_to_decimal(getattr(quote, "price", None)),
                _to_datetime(getattr(quote, "as_of", None)),
                answer.source or "KIS")

    def _from_fmp(self, pairs: list[tuple[str, str]]
                  ) -> dict[str, Optional[Quote]]:
        if not pairs:
            return {}
        client = self.fmp
        if client is None or not client.ready:
            reason = (client.status()["reason"] if client is not None
                      else "FMP client unavailable")
            return {symbol: self._fail_none(symbol, reason, permanent=True)
                    for symbol, _ in pairs}

        # The provider symbol differs from what the operator typed, so keep a
        # map back to the rule's own symbol — that is the key the engine uses.
        lookup = {markets.provider_symbol(market, symbol).upper(): symbol
                  for symbol, market in pairs}
        try:
            fetched = client.quotes(list(lookup))
        except Exception as exc:
            reason = f"{type(exc).__name__}: {exc}"
            # A plan refusal (HTTP 402) is a subscription fact; the client
            # remembers it and no amount of waiting changes it.
            blocked = client.plan_blocked()
            return {symbol: self._fail_none(symbol,
                                            client.error_for(provider_symbol) or reason,
                                            permanent=provider_symbol in blocked)
                    for provider_symbol, symbol in lookup.items()}

        blocked = client.plan_blocked()
        out: dict[str, Optional[Quote]] = {}
        for provider_symbol, symbol in lookup.items():
            row = fetched.get(provider_symbol)
            if row is None:
                out[symbol] = self._fail_none(
                    symbol,
                    client.error_for(provider_symbol)
                    or f"FMP returned no row for {provider_symbol}",
                    permanent=provider_symbol in blocked)
                continue
            out[symbol] = self._record(symbol, _to_decimal(row.price),
                                       _to_datetime(row.as_of), row.source)
        return out

    # -- shared bookkeeping --------------------------------------------------
    def _record(self, symbol: str, price: Optional[Decimal],
                as_of: Optional[datetime], source: str) -> Optional[Quote]:
        """Validate, roll the previous price forward, and build the Quote."""
        if price is None or price <= 0:
            return self._fail_none(symbol, "provider returned no usable price")
        if as_of is None:
            return self._fail_none(symbol, "provider returned no timestamp")
        with self._lock:
            previous = self._previous.get(symbol)
            self._previous[symbol] = price
            self._last_error.pop(symbol, None)
            self._permanent.discard(symbol)
        return Quote(symbol=symbol, price=price, previous=previous,
                     as_of=as_of, source=source)

    def _fail(self, symbol: str, reason: str, *, permanent: bool = False) -> None:
        with self._lock:
            self._last_error[symbol] = reason
            if permanent:
                self._permanent.add(symbol)
            else:
                self._permanent.discard(symbol)

    def _fail_none(self, symbol: str, reason: str, *, permanent: bool = False) -> None:
        self._fail(symbol, reason, permanent=permanent)
        return None
