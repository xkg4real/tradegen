"""One façade over the three KRX providers, with an explicit preference order.

Capability routing rather than a single "primary provider", because the three
sources do not overlap:

    quote / OHLCV   KIS first (live, per-symbol), KRX marketplace as fallback
                    (session close, whole-market, keyless)
    whole market    KRX marketplace only — KIS has no all-instruments endpoint
    index levels    KIS first, KRX marketplace fallback
    filings         OpenDART only
    financials      OpenDART only

Every result carries the provider that produced it, so a screen never shows a
KIS live price and a KRX previous close side by side without saying which is
which. Failures degrade to the next provider and, if none can serve, return an
empty result plus a reason — never a fabricated value.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import config
from data.krx.kis_client import KISClient, KISError, Quote
from data.krx.krx_market_client import KRXError, KRXMarketClient
from data.krx.opendart_client import DARTError, OpenDARTClient


@dataclass(frozen=True)
class Answer:
    """A result plus the provenance the UI is required to display."""
    data: object
    source: str
    ok: bool = True
    reason: str = ""

    def __bool__(self) -> bool:
        return self.ok


class KRXGateway:
    """Construction performs no network request."""

    def __init__(self):
        self.kis = KISClient()
        self.dart = OpenDARTClient()
        self.krx = KRXMarketClient()

    # -- status --------------------------------------------------------------
    def status(self) -> list[dict]:
        out = []
        for name, client in (("KIS", self.kis), ("OpenDART", self.dart), ("KRX", self.krx)):
            state = client.status()
            out.append({"provider": name, **state})
        return out

    @property
    def any_ready(self) -> bool:
        return self.krx.ready or self.kis.ready or self.dart.ready

    # -- prices --------------------------------------------------------------
    def quote(self, ticker: str) -> Answer:
        if self.kis.ready:
            try:
                return Answer(self.kis.quote(ticker), "KIS")
            except KISError as exc:
                last = str(exc)
            except Exception as exc:
                last = type(exc).__name__
        else:
            last = "KIS not configured"

        rows = self.krx.all_quotes("ALL")
        code = ticker.strip().split(".", 1)[0].zfill(6)
        for row in rows:
            if row["ticker"] == code:
                quote = Quote(
                    ticker=row["ticker"], name=row["name"], price=row["close"],
                    change=row["change"], change_pct=row["change_pct"],
                    volume=row["volume"], market_cap=row["market_cap"],
                    high=row["high"], low=row["low"], open=row["open"],
                    as_of=row["as_of"], source="KRX",
                )
                return Answer(quote, "KRX")
        return Answer(None, "", ok=False,
                      reason=f"no provider returned {ticker} ({last})")

    def daily(self, ticker: str, *, start: Optional[str] = None,
              end: Optional[str] = None) -> Answer:
        if self.kis.ready:
            try:
                rows = self.kis.daily(ticker, start=start, end=end)
                if rows:
                    return Answer(rows, "KIS")
            except KISError as exc:
                return Answer([], "", ok=False, reason=str(exc))
            except Exception as exc:
                return Answer([], "", ok=False, reason=type(exc).__name__)
        return Answer([], "", ok=False,
                      reason="daily OHLCV needs KIS. The KRX Open API serves a "
                             "whole session at a time, not per-symbol history.")

    def market_snapshot(self, market: str = "ALL") -> Answer:
        rows = self.krx.all_quotes(market)
        if rows:
            return Answer(rows, "KRX")
        return Answer([], "", ok=False,
                      reason="No KRX snapshot. Set KRX_API_KEY (free at "
                             "data.krx.co.kr); the keyless export is blocked.")

    def indices(self) -> Answer:
        results = []
        if self.kis.ready:
            for name in ("KOSPI", "KOSDAQ", "KOSPI200"):
                try:
                    results.append(self.kis.index(name))
                except Exception:
                    continue
            if results:
                return Answer(results, "KIS")
        rows = self.krx.indices()
        if rows:
            return Answer(rows, "KRX")
        return Answer([], "", ok=False, reason="no index provider responded")

    # -- disclosures ---------------------------------------------------------
    def filings(self, ticker: str, *, days: int = 90, limit: int = 50) -> Answer:
        if not self.dart.ready:
            return Answer([], "", ok=False,
                          reason="filings need OPENDART_API_KEY (free from dart.fss.or.kr)")
        try:
            return Answer(self.dart.filings(ticker, days=days, limit=limit), "OpenDART")
        except DARTError as exc:
            return Answer([], "", ok=False, reason=str(exc))

    def financials(self, ticker: str, *, year: Optional[int] = None,
                   report: str = "FY") -> Answer:
        if not self.dart.ready:
            return Answer([], "", ok=False,
                          reason="financials need OPENDART_API_KEY (free from dart.fss.or.kr)")
        try:
            return Answer(self.dart.financials(ticker, year=year, report=report), "OpenDART")
        except DARTError as exc:
            return Answer([], "", ok=False, reason=str(exc))
