"""KIS (한국투자증권) Open API — read-only market data beyond KRX stocks.

`data.krx.kis_client` covers KRX stock quotes and daily bars. This module
reaches the other asset domains the same app key serves, all of them through
quotation endpoints that carry no account number:

    ETF / ETN          NAV, 괴리율, tracking error, the constituent basket
    KRX derivatives    KOSPI200 / mini / KOSDAQ150 futures, KTB and USD futures
                       (market code CF), the option board with IV and Greeks
    Overseas stock     NAS / NYS / AMS / HKS / TSE ... quotes and daily bars
    Overseas charts    indices (N), FX fixings incl. 원/달러 (X), KRW and US
                       benchmark yields (I)
    Overseas futures   CBOE VX, ICE DX, CME BTC daily bars (CME ES / NQ / ZN /
                       6E / GC / CL / SR3 answer HTTP 500 on a stock-account
                       key, so Yahoo continuous contracts stay the research feed)
    Exchange-traded bonds  KTB prices with yields, daily history, issue terms
    Domestic flows     investor net buying, short-sale volume

SCOPE BOUNDARY (same as kis_client): no order, cancel, balance or any other
account-mutating path exists here or anywhere in the repository.

PROBED LIVE 2026-09-25 with the operator's stock-account key (results in
docs/ASSET_EXPANSION_SPEC.md): every endpoint below answered; rows per call and
the paging rule are recorded on each function. Field names are the ones KIS
returned, not the ones the sample files document.

Every function returns plain Python (dataclasses of tuples) so callers never see
a KIS field name; `Bars.to_history` hands the closes to the quant core.
"""
from __future__ import annotations

import io
import re
import zipfile
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any, Optional

import config
from data.krx.kis_client import KISClient, KISError, KISUnavailable, _f

try:
    from data.net import session as _requests        # shared session: retry + backoff
except Exception:                                    # pragma: no cover
    _requests = None

MASTER_URL = "https://new.real.download.dws.co.kr/common/master/"
_MASTERS = ("fo_idx_code_mts", "fo_com_code", "bond_code", "ffcode", "frgn_code")

# Market division codes (FID_COND_MRKT_DIV_CODE) confirmed by the probe.
MKT_STOCK, MKT_INDEX, MKT_BOND = "J", "U", "B"
MKT_FUT, MKT_OPT, MKT_COMMODITY_FUT = "F", "O", "CF"      # CF: KTB, KOFR, USD/JPY/EUR/CNH, gold
CHART_INDEX, CHART_FX, CHART_YIELD = "N", "X", "I"

# KRW benchmark yields served by the chart endpoint under market "I" (percent).
KRW_YIELD_CODES = {
    "Y0104": ("KTB 1y", 1.0), "Y0101": ("KTB 3y", 3.0), "Y0105": ("KTB 5y", 5.0),
    "Y0106": ("KTB 10y", 10.0), "Y0116": ("KTB 20y", 20.0), "Y0117": ("KTB 30y", 30.0),
    "Y0112": ("CD 91d", 0.25), "Y0114": ("Call 1d", 1 / 365), "Y0102": ("Corp AA- 3y", 3.0),
}
US_YIELD_CODES = {"Y0202": ("UST 10y", 10.0), "Y0201": ("UST 30y", 30.0), "Y0204": ("Fed funds", 1 / 365)}
KRW_CURVE_TENORS = (("Y0112", 0.25), ("Y0104", 1.0), ("Y0101", 3.0), ("Y0105", 5.0),
                    ("Y0106", 10.0), ("Y0116", 20.0), ("Y0117", 30.0))    # CD 91d + KTB par grid
FX_KRW_CODE = "FX@KRW"          # 원/달러 (KMB) daily fixing, market X
INDEX_CODES = {"SPX": "S&P 500", ".DJI": "Dow Jones"}

# Overseas exchange codes accepted by /overseas-price (EXCD).
OVERSEAS_EXCHANGES = ("NAS", "NYS", "AMS", "HKS", "TSE", "SHS", "SZS", "HSX", "HNX")


@dataclass(frozen=True)
class Bars:
    symbol: str
    dates: tuple[str, ...]                # ISO, ascending
    close: tuple[float, ...]
    open: tuple[float, ...] = ()
    high: tuple[float, ...] = ()
    low: tuple[float, ...] = ()
    volume: tuple[float, ...] = ()
    source: str = "KIS"
    note: str = ""
    extra: dict = field(default_factory=dict)

    def __len__(self) -> int:
        return len(self.close)

    def to_history(self, symbol: str | None = None):
        from core.quant.history import History
        return History(symbol=symbol or self.symbol, source=self.source,
                       dates=self.dates, closes=self.close, note=self.note)


@dataclass(frozen=True)
class OptionQuote:
    strike: float
    last: Optional[float]
    bid: Optional[float]
    ask: Optional[float]
    iv: Optional[float]                   # KIS implied vol, decimal (hts_ints_vltl / 100)
    delta: Optional[float]
    gamma: Optional[float]
    vega: Optional[float]
    theta: Optional[float]
    open_interest: Optional[float]
    volume: Optional[float]
    theo: Optional[float]                 # KIS theoretical price (hts_thpr)
    code: str = ""
    atm: str = ""

    @property
    def mid(self) -> Optional[float]:
        if self.bid and self.ask and self.bid > 0 and self.ask > 0:
            return 0.5 * (self.bid + self.ask)
        return self.last if self.last and self.last > 0 else None


@dataclass(frozen=True)
class OptionBoard:
    expiry_yyyymm: str
    expiry_date: str                      # ISO, second Thursday
    calls: tuple[OptionQuote, ...]        # ascending strike
    puts: tuple[OptionQuote, ...]
    as_of: str
    source: str = "KIS"


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _ymd(d: date) -> str:
    return d.strftime("%Y%m%d")


def _iso(text: str) -> str:
    t = str(text or "").strip()
    return f"{t[:4]}-{t[4:6]}-{t[6:8]}" if len(t) == 8 else t


def _start(days: int) -> date:
    return date.today() - timedelta(days=int(days * 1.6) + 10)


def _bars(symbol: str, rows: list[dict], keys: dict[str, str], *, note: str = "",
          extra: dict | None = None) -> Bars:
    """rows: KIS dicts; keys: {'date': ..., 'close': ..., 'open': ..., ...}."""
    seen: dict[str, dict] = {}
    for r in rows:
        d = _iso(r.get(keys["date"]))
        c = _f(r.get(keys["close"]))
        if d and c is not None and c > 0:
            seen[d] = r
    ds = sorted(seen)
    col = lambda k: tuple(float(_f(seen[d].get(keys[k])) or 0.0) for d in ds) if k in keys else ()  # noqa: E731
    return Bars(symbol=symbol, dates=tuple(ds), close=tuple(float(_f(seen[d][keys["close"]])) for d in ds),
                open=col("open"), high=col("high"), low=col("low"), volume=col("volume"),
                note=note, extra=extra or {})


class KISMarkets:
    """Thin read-only wrapper over the non-stock KIS quotation domains."""

    def __init__(self, client: KISClient | None = None):
        self.client = client or KISClient()

    @property
    def ready(self) -> bool:
        return self.client.ready

    def _get(self, path: str, tr_id: str, params: dict, *, tr_cont: str = "") -> dict:
        if not self.ready:
            raise KISUnavailable("Set KIS_APP_KEY and KIS_APP_SECRET to enable KIS")
        if tr_cont:
            return self.client._get(path, tr_id, params, tr_cont=tr_cont)
        return self.client._get(path, tr_id, params)

    def _more_pages(self) -> bool:
        hdr = getattr(self.client, "last_headers", None) or {}
        return str(hdr.get("tr_cont", "")).strip().upper() in ("F", "M")

    def _page_back(self, fetch, *, days: int, list_key: str, date_key: str,
                   max_pages: int | None = None) -> list[dict]:
        """Call `fetch(end_yyyymmdd)` repeatedly, each time ending the day before
        the earliest date already held, until `days` rows are in hand, a page is
        empty or repeats, or the start date is passed."""
        start = _start(days)
        end: Optional[str] = None
        rows: dict[str, dict] = {}
        pages = max_pages or (days // 30 + 4)
        for _ in range(pages):
            payload = fetch(end or _ymd(date.today()))
            page = payload.get(list_key) or []
            fresh = [r for r in page if r.get(date_key) and _iso(r[date_key]) not in rows]
            if not fresh:
                break
            for r in fresh:
                rows[_iso(r[date_key])] = r
            if len(rows) >= days:
                break
            earliest = min(_iso(r[date_key]) for r in fresh)
            nxt = date.fromisoformat(earliest) - timedelta(days=1)
            if nxt < start:
                break
            end = _ymd(nxt)
        keep = sorted(rows)[-days:]                 # the most recent `days` sessions
        return [rows[d] for d in keep]

    # -- ETF / ETN ------------------------------------------------------------
    def etf_quote(self, code: str) -> dict:
        """Price, NAV, 괴리율 (dprt, %), tracking error (trc_errt, %), AUM, CU size,
        LP holdings, listing date, target index. One call."""
        out = self._get("/uapi/etfetn/v1/quotations/inquire-price", "FHPST02400000",
                        {"FID_COND_MRKT_DIV_CODE": MKT_STOCK, "FID_INPUT_ISCD": code}).get("output") or {}
        return {
            "code": code, "price": _f(out.get("stck_prpr")), "nav": _f(out.get("nav")),
            "premium_pct": _f(out.get("dprt")), "tracking_error_pct": _f(out.get("trc_errt")),
            "aum": _f(out.get("etf_ntas_ttam")), "cu_units": _f(out.get("etf_cu_unit_scrt_cnt")),
            "shares": _f(out.get("etf_crcl_stcn")), "lp_holding_pct": _f(out.get("lp_hldn_rate")),
            "listed": _iso(out.get("stck_lstn_date")), "target_index": str(out.get("etf_rprs_bstp_kor_isnm") or ""),
            "dividend_cycle": str(out.get("etf_dvdn_cycl") or ""), "type": str(out.get("etf_div_name") or ""),
            "as_of": date.today().isoformat(),
        }

    def etf_nav_daily(self, code: str, *, days: int = 504) -> Bars:
        """Close, NAV and 괴리율 per session. 100 rows per call, paged on DATE_2.
        `extra['nav']` and `extra['premium_pct']` align with `dates`."""
        def fetch(end):
            return self._get("/uapi/etfetn/v1/quotations/nav-comparison-daily-trend", "FHPST02440200",
                             {"FID_COND_MRKT_DIV_CODE": MKT_STOCK, "FID_INPUT_ISCD": code,
                              "FID_INPUT_DATE_1": _ymd(_start(days)), "FID_INPUT_DATE_2": end})
        rows = self._page_back(fetch, days=days, list_key="output", date_key="stck_bsop_date")
        b = _bars(code, rows, {"date": "stck_bsop_date", "close": "stck_clpr", "volume": "acml_vol"})
        by = {_iso(r["stck_bsop_date"]): r for r in rows}
        nav = tuple(float(_f(by[d].get("nav")) or 0.0) for d in b.dates)
        prem = tuple(float(_f(by[d].get("dprt")) or 0.0) for d in b.dates)
        return Bars(**{**b.__dict__, "extra": {"nav": nav, "premium_pct": prem}})

    def etf_components(self, code: str) -> list[dict]:
        """Constituents with weight (etf_cnfg_issu_rlim, %) and CU shares."""
        p = self._get("/uapi/etfetn/v1/quotations/inquire-component-stock-price", "FHKST121600C0",
                      {"FID_COND_MRKT_DIV_CODE": MKT_STOCK, "FID_INPUT_ISCD": code,
                       "FID_COND_SCR_DIV_CODE": "11216"})
        return [{"code": str(r.get("stck_shrn_iscd") or ""), "name": str(r.get("hts_kor_isnm") or ""),
                 "price": _f(r.get("stck_prpr")), "weight_pct": _f(r.get("etf_cnfg_issu_rlim")),
                 "cu_shares": _f(r.get("etf_cu_unit_scrt_cnt"))} for r in p.get("output2") or []]

    # -- KRX futures and options ---------------------------------------------
    @staticmethod
    def futures_market(code: str) -> str:
        """Index products (A01 KOSPI200, A05 mini, A06 KOSDAQ150, old 101/105/106)
        quote under F; KTB, KOFR, currency and gold futures under CF."""
        c = code.strip().upper()
        prod = c[1:3] if c[:1].isalpha() else c[1:3]
        return MKT_FUT if prod in ("01", "05", "06", "07") else MKT_COMMODITY_FUT

    def futures_quote(self, code: str) -> dict:
        """Price, basis, KIS theoretical price and 괴리율, open interest, Greeks-lite,
        remaining days, and the underlying index level. One call."""
        p = self._get("/uapi/domestic-futureoption/v1/quotations/inquire-price", "FHMIF10000000",
                      {"FID_COND_MRKT_DIV_CODE": self.futures_market(code), "FID_INPUT_ISCD": code})
        o = p.get("output1") or {}
        if not o:
            raise KISError(f"{code}: KIS returned no futures quote (wrong code or market)")
        idx = p.get("output3") or p.get("output2") or {}
        return {
            "code": code, "name": str(o.get("hts_kor_isnm") or "").strip(),
            "price": _f(o.get("futs_prpr")), "change": _f(o.get("futs_prdy_vrss")),
            "open": _f(o.get("futs_oprc")), "high": _f(o.get("futs_hgpr")), "low": _f(o.get("futs_lwpr")),
            "volume": _f(o.get("acml_vol")), "open_interest": _f(o.get("hts_otst_stpl_qty")),
            "basis": _f(o.get("basis")), "market_basis": _f(o.get("mrkt_basis")),
            "theo": _f(o.get("hts_thpr")), "premium_pct": _f(o.get("dprt")),
            "last_trade_date": _iso(o.get("futs_last_tr_date")), "days_left": _f(o.get("hts_rmnn_dynu")),
            "delta": _f(o.get("delta_val")), "underlying": str(idx.get("hts_kor_isnm") or ""),
            "underlying_level": _f(idx.get("bstp_nmix_prpr")), "as_of": date.today().isoformat(),
        }

    def futures_daily(self, code: str, *, days: int = 504) -> Bars:
        """Daily OHLCV of one contract, expired contracts included. 100 rows per
        call, paged on DATE_2. Stitch contracts with `continuous_futures`."""
        mk = self.futures_market(code)

        def fetch(end):
            return self._get("/uapi/domestic-futureoption/v1/quotations/inquire-daily-fuopchartprice",
                             "FHKIF03020100",
                             {"FID_COND_MRKT_DIV_CODE": mk, "FID_INPUT_ISCD": code,
                              "FID_INPUT_DATE_1": _ymd(_start(days)), "FID_INPUT_DATE_2": end,
                              "FID_PERIOD_DIV_CODE": "D"})
        rows = self._page_back(fetch, days=days, list_key="output2", date_key="stck_bsop_date")
        return _bars(code, rows, {"date": "stck_bsop_date", "close": "futs_prpr", "open": "futs_oprc",
                                  "high": "futs_hgpr", "low": "futs_lwpr", "volume": "acml_vol"})

    def continuous_futures(self, codes: list[str], *, days: int = 504) -> Bars:
        """Back-adjusted continuous series from a list of contract codes ordered
        oldest → newest: each contract is used until the next one's first date
        minus 5 sessions, and earlier segments are multiplied by the price ratio
        at the splice (ratio adjustment, so returns are preserved)."""
        segs = [self.futures_daily(c, days=days) for c in codes]
        segs = [s for s in segs if len(s)]
        if not segs:
            raise KISError("no futures history for any of the given codes")
        dates: list[str] = []
        closes: list[float] = []
        used: list[str] = []
        for i, s in enumerate(segs):
            nxt = segs[i + 1] if i + 1 < len(segs) else None
            cutoff = nxt.dates[min(5, len(nxt) - 1)] if nxt else "9999-12-31"
            keep = [(d, c) for d, c in zip(s.dates, s.close) if d < cutoff and (not dates or d > dates[-1])]
            if keep and closes:                          # splice: scale history to the new contract
                d0 = keep[0][0]
                prev = next((c for d, c in zip(s.dates, s.close) if d == dates[-1]), None)
                if prev:
                    ratio = prev / closes[-1]
                    closes = [c * ratio for c in closes]
            for d, c in keep:
                dates.append(d); closes.append(c)
            used.append(s.symbol)
        return Bars(symbol="+".join(used), dates=tuple(dates), close=tuple(closes),
                    note=f"ratio-adjusted at {len(used) - 1} splice(s), 5 sessions before each expiry")

    def futures_board(self, cls: str = "MKI") -> list[dict]:
        """Listed futures of one family (MKI = mini KOSPI200 monthlies) with price,
        theoretical price, bid/ask, open interest and remaining days."""
        p = self._get("/uapi/domestic-futureoption/v1/quotations/display-board-futures", "FHPIF05030200",
                      {"FID_COND_MRKT_DIV_CODE": MKT_FUT, "FID_COND_SCR_DIV_CODE": "20503",
                       "FID_COND_MRKT_CLS_CODE": cls})
        return [{"code": str(r.get("futs_shrn_iscd") or ""), "name": str(r.get("hts_kor_isnm") or "").strip(),
                 "price": _f(r.get("futs_prpr")), "theo": _f(r.get("hts_thpr")),
                 "bid": _f(r.get("futs_bidp")), "ask": _f(r.get("futs_askp")),
                 "open_interest": _f(r.get("hts_otst_stpl_qty")), "volume": _f(r.get("acml_vol"))}
                for r in p.get("output") or []]

    def option_expiries(self) -> list[str]:
        """Listed KOSPI200 monthly option expiries as 'YYYYMM', nearest first."""
        p = self._get("/uapi/domestic-futureoption/v1/quotations/display-board-option-list", "FHPIO056104C0",
                      {"FID_COND_SCR_DIV_CODE": "509", "FID_COND_MRKT_DIV_CODE": "", "FID_COND_MRKT_CLS_CODE": ""})
        return [str(r.get("mtrt_yymm")) for r in p.get("output") or [] if r.get("mtrt_yymm")]

    @staticmethod
    def kospi200_expiry(yyyymm: str) -> date:
        """Second Thursday of the month (KRX monthly index options and futures)."""
        y, m = int(yyyymm[:4]), int(yyyymm[4:6])
        first = date(y, m, 1)
        thursday = first + timedelta(days=(3 - first.weekday()) % 7)
        return thursday + timedelta(days=7)

    def option_board(self, yyyymm: str) -> OptionBoard:
        """The KOSPI200 option chain of one monthly expiry: up to 100 calls and
        100 puts with strike, bid/ask/last, KIS implied vol, Greeks, open
        interest and volume. A snapshot; KIS keeps no chain history, so callers
        that need history must store boards day by day."""
        params = {"FID_COND_MRKT_DIV_CODE": MKT_OPT, "FID_COND_SCR_DIV_CODE": "20503",
                  "FID_MRKT_CLS_CODE": "CO", "FID_MTRT_CNT": yyyymm,
                  "FID_MRKT_CLS_CODE1": "PO", "FID_COND_MRKT_CLS_CODE": ""}
        path = "/uapi/domestic-futureoption/v1/quotations/display-board-callput"
        # The board answers 100 strikes per page, highest first; follow the
        # exchange's continuation header until the whole chain is in hand.
        calls_raw: dict[str, dict] = {}
        puts_raw: dict[str, dict] = {}
        p = self._get(path, "FHPIF05030100", params)
        for _ in range(8):
            fresh = 0
            for r in p.get("output1") or []:
                k = str(r.get("acpr"))
                if k not in calls_raw:
                    calls_raw[k] = r; fresh += 1
            for r in p.get("output2") or []:
                k = str(r.get("acpr"))
                if k not in puts_raw:
                    puts_raw[k] = r; fresh += 1
            if not fresh or not self._more_pages():
                break
            p = self._get(path, "FHPIF05030100", params, tr_cont="N")

        def parse(rows) -> tuple[OptionQuote, ...]:
            out = []
            for r in rows or []:
                k = _f(r.get("acpr"))
                if k is None:
                    continue
                iv = _f(r.get("hts_ints_vltl"))
                out.append(OptionQuote(
                    strike=k, last=_f(r.get("optn_prpr")), bid=_f(r.get("optn_bidp")), ask=_f(r.get("optn_askp")),
                    iv=(iv / 100.0 if iv is not None and iv > 0 else None),
                    delta=_f(r.get("delta_val")), gamma=_f(r.get("gama")), vega=_f(r.get("vega")),
                    theta=_f(r.get("theta")), open_interest=_f(r.get("hts_otst_stpl_qty")),
                    volume=_f(r.get("acml_vol")), theo=_f(r.get("hts_thpr")),
                    code=str(r.get("optn_shrn_iscd") or ""), atm=str(r.get("atm_cls_name") or "").strip()))
            return tuple(sorted(out, key=lambda q: q.strike))
        return OptionBoard(expiry_yyyymm=yyyymm, expiry_date=self.kospi200_expiry(yyyymm).isoformat(),
                           calls=parse(list(calls_raw.values())), puts=parse(list(puts_raw.values())),
                           as_of=datetime.now().isoformat(timespec="minutes"))

    def option_chain(self, yyyymm: str, spot: float, *, width: float = 0.10, step_pts: float = 2.5,
                     include_book: bool = True, max_series: int = 160) -> OptionBoard:
        """The KOSPI200 monthly chain of one expiry around `spot`, one quotation
        call per series (the board endpoint stops at its highest 100 strikes,
        which on a 1,100 index never reaches the money). Series codes and
        strikes come from the keyless master (`option_codes`); `width` is the
        half-range in fraction of spot, `step_pts` the strike spacing kept
        (2.5 = every listed strike, 5 = every other). With `include_book` the
        top-of-book bid/ask is fetched too (a second call per series)."""
        codes = option_codes(yyyymm)
        if not codes:
            raise KISError(f"no {yyyymm} KOSPI200 option series in the master")
        lo, hi = spot * (1 - width), spot * (1 + width)
        keep = [c for c in codes if lo <= c["strike"] <= hi and abs((c["strike"] / step_pts) - round(c["strike"] / step_pts)) < 1e-9]
        if len(keep) > max_series:                        # keep the strikes nearest the money
            keep = sorted(keep, key=lambda c: abs(c["strike"] - spot))[:max_series]
        quotes: dict[str, list] = {"C": [], "P": []}
        for c in keep:
            o = self._get("/uapi/domestic-futureoption/v1/quotations/inquire-price", "FHMIF10000000",
                          {"FID_COND_MRKT_DIV_CODE": MKT_OPT, "FID_INPUT_ISCD": c["code"]}).get("output1") or {}
            bid = ask = None
            if include_book:
                try:
                    bk = self._get("/uapi/domestic-futureoption/v1/quotations/inquire-asking-price", "FHMIF10010000",
                                   {"FID_COND_MRKT_DIV_CODE": MKT_OPT, "FID_INPUT_ISCD": c["code"]})
                    bid, ask = _top_of_book(bk)
                except KISError:
                    pass
            iv = _f(o.get("hts_ints_vltl"))
            quotes[c["kind"]].append(OptionQuote(
                strike=c["strike"], last=_f(o.get("futs_prpr")), bid=bid, ask=ask,
                iv=(iv / 100.0 if iv is not None and iv > 0 else None),
                delta=_f(o.get("delta_val")), gamma=_f(o.get("gama")), vega=_f(o.get("vega")), theta=_f(o.get("theta")),
                open_interest=_f(o.get("hts_otst_stpl_qty")), volume=_f(o.get("acml_vol")), theo=_f(o.get("hts_thpr")),
                code=c["code"], atm=("ATM" if abs(c["strike"] - spot) <= step_pts / 2 else "")))
        return OptionBoard(expiry_yyyymm=yyyymm, expiry_date=self.kospi200_expiry(yyyymm).isoformat(),
                           calls=tuple(sorted(quotes["C"], key=lambda q: q.strike)),
                           puts=tuple(sorted(quotes["P"], key=lambda q: q.strike)),
                           as_of=datetime.now().isoformat(timespec="minutes"))

    def last_session(self) -> str:
        """ISO date of the last KOSPI200 session (the date every last print and
        KIS implied vol on the board belongs to when the market is closed)."""
        return self.index_daily("2001", days=12).dates[-1]

    def index_daily(self, code: str = "2001", *, days: int = 504) -> Bars:
        """KOSPI (0001) / KOSDAQ (1001) / KOSPI200 (2001) daily OHLCV; 50 rows per
        call, paged on DATE_2."""
        def fetch(end):
            return self._get("/uapi/domestic-stock/v1/quotations/inquire-daily-indexchartprice", "FHKUP03500100",
                             {"FID_COND_MRKT_DIV_CODE": MKT_INDEX, "FID_INPUT_ISCD": code,
                              "FID_INPUT_DATE_1": _ymd(_start(days)), "FID_INPUT_DATE_2": end,
                              "FID_PERIOD_DIV_CODE": "D"})
        rows = self._page_back(fetch, days=days, list_key="output2", date_key="stck_bsop_date",
                               max_pages=days // 40 + 4)
        return _bars(f"INDEX:{code}", rows, {"date": "stck_bsop_date", "close": "bstp_nmix_prpr",
                                              "open": "bstp_nmix_oprc", "high": "bstp_nmix_hgpr",
                                              "low": "bstp_nmix_lwpr", "volume": "acml_vol"})

    # -- Overseas stock / index / FX / yields ---------------------------------
    def overseas_quote(self, excd: str, symb: str) -> dict:
        p = self._get("/uapi/overseas-price/v1/quotations/price", "HHDFS00000300",
                      {"AUTH": "", "EXCD": excd.upper(), "SYMB": symb.upper()}).get("output") or {}
        return {"symbol": f"{excd.upper()}:{symb.upper()}", "last": _f(p.get("last")),
                "prev": _f(p.get("base")), "change_pct": _f(p.get("rate")), "volume": _f(p.get("tvol")),
                "as_of": date.today().isoformat(), "note": "delayed unless a real-time entitlement exists"}

    def overseas_daily(self, excd: str, symb: str, *, days: int = 504, adjusted: bool = True) -> Bars:
        """Daily bars; `adjusted` sends MODP=1 (수정주가 반영), which adjusts for
        splits and other capital changes. Cash dividends are NOT reinvested, so
        this is a price-return series. 100 rows per call, paged by BYMD = the
        earliest date returned minus one day."""
        excd, symb = excd.upper(), symb.upper()

        def fetch(end):
            bymd = "" if end == _ymd(date.today()) else end
            return self._get("/uapi/overseas-price/v1/quotations/dailyprice", "HHDFS76240000",
                             {"AUTH": "", "EXCD": excd, "SYMB": symb, "GUBN": "0", "BYMD": bymd,
                              "MODP": "1" if adjusted else "0"})
        rows = self._page_back(fetch, days=days, list_key="output2", date_key="xymd")
        return _bars(f"{excd}:{symb}", rows, {"date": "xymd", "close": "clos", "open": "open",
                                              "high": "high", "low": "low", "volume": "tvol"},
                     note="adjusted close" if adjusted else "unadjusted close")

    def overseas_chart(self, market: str, code: str, *, days: int = 504) -> Bars:
        """Indices (N: SPX, .DJI), FX fixings (X: FX@KRW = 원/달러) and benchmark
        yields in percent (I: Y0101 국고채 3년 ... see KRW_YIELD_CODES). 100 rows
        per call, paged on DATE_2."""
        def fetch(end):
            return self._get("/uapi/overseas-price/v1/quotations/inquire-daily-chartprice", "FHKST03030100",
                             {"FID_COND_MRKT_DIV_CODE": market, "FID_INPUT_ISCD": code,
                              "FID_INPUT_DATE_1": _ymd(_start(days)), "FID_INPUT_DATE_2": end,
                              "FID_PERIOD_DIV_CODE": "D"})
        rows = self._page_back(fetch, days=days, list_key="output2", date_key="stck_bsop_date")
        if not rows:
            raise KISError(f"{market}/{code}: KIS returned no chart rows (unknown code for this market?)")
        return _bars(f"{market}:{code}", rows, {"date": "stck_bsop_date", "close": "ovrs_nmix_prpr",
                                                "open": "ovrs_nmix_oprc", "high": "ovrs_nmix_hgpr",
                                                "low": "ovrs_nmix_lwpr", "volume": "acml_vol"})

    def krw_yield_daily(self, code: str = "Y0101", *, days: int = 504) -> Bars:
        """KRW benchmark yield history in PERCENT (KTB 1/3/5/10/20/30y, CD 91d, call)."""
        return self.overseas_chart(CHART_YIELD, code, days=days)

    def usdkrw_daily(self, *, days: int = 504) -> Bars:
        return self.overseas_chart(CHART_FX, FX_KRW_CODE, days=days)

    def krw_yields_snapshot(self) -> list[dict]:
        """Today's Korean benchmark yields (percent) and their daily change:
        국고채 1/3/5/10/20/30년, 회사채, 통안증권, CD 91일, CP, call."""
        p = self._get("/uapi/domestic-stock/v1/quotations/comp-interest", "FHPST07020000",
                      {"FID_COND_MRKT_DIV_CODE": "I", "FID_COND_SCR_DIV_CODE": "20702",
                       "FID_DIV_CLS_CODE": "", "FID_DIV_CLS_CODE1": ""})
        out = []
        for r in p.get("output1") or []:
            code = str(r.get("bcdt_code") or "")
            out.append({"code": code, "label": str(r.get("hts_kor_isnm") or "").strip(),
                        "yield_pct": _f(r.get("bond_mnrt_prpr")), "change_pct": _f(r.get("bond_mnrt_prdy_vrss")),
                        "tenor": KRW_YIELD_CODES.get(code, ("", None))[1]})
        return out

    # -- Overseas futures -------------------------------------------------------
    def ovf_daily(self, srs_cd: str, exch_cd: str, *, days: int = 504) -> Bars:
        """Daily bars of one dated overseas contract (VXV26@CBOE, DXZ26@ICE,
        BTCU26@CME work; CME ES/NQ/ZN/6E/GC/CL/SR3 answer HTTP 500 on a stock-
        account key). 40 rows per call, paged with QRY_TP=P and INDEX_KEY."""
        rows: dict[str, dict] = {}
        end = _ymd(date.today())
        key = ""
        qry = "Q"
        for _ in range(days // 30 + 4):
            p = self._get("/uapi/overseas-futureoption/v1/quotations/daily-ccnl", "HHDFC55020100",
                          {"SRS_CD": srs_cd.upper(), "EXCH_CD": exch_cd.upper(), "START_DATE_TIME": "",
                           "CLOSE_DATE_TIME": end, "QRY_TP": qry, "QRY_CNT": "40", "QRY_GAP": "",
                           "INDEX_KEY": key})
            page = [r for r in (p.get("output2") or []) if r.get("data_date") and _iso(r["data_date"]) not in rows]
            if not page:
                break
            for r in page:
                rows[_iso(r["data_date"])] = r
            if len(rows) >= days:
                break
            earliest = min(_iso(r["data_date"]) for r in page)
            key = earliest.replace("-", "")
            end = _ymd(date.fromisoformat(earliest) - timedelta(days=1))
            qry = "P"
        return _bars(f"{srs_cd.upper()}@{exch_cd.upper()}", list(rows.values()),
                     {"date": "data_date", "close": "last_price", "open": "open_price",
                      "high": "high_price", "low": "low_price", "volume": "vol"})

    def ovf_contract_detail(self, codes: list[str]) -> list[dict]:
        """Exchange, currency, settlement price/date, tick size and value,
        contract size, expiry and first-notice dates for up to 32 symbols."""
        codes = [c.upper() for c in codes[:32]]
        params = {"QRY_CNT": str(len(codes))}
        for i, c in enumerate(codes, 1):
            params[f"SRS_CD_{i:02d}"] = c
        p = self._get("/uapi/overseas-futureoption/v1/quotations/search-contract-detail", "HHDFC55200000", params)
        out = []
        for code, r in zip(codes, p.get("output2") or []):
            out.append({"code": code, "exchange": str(r.get("exch_cd") or ""), "currency": str(r.get("crc_cd") or ""),
                        "settle": _f(r.get("sttl_price")), "settle_date": _iso(r.get("sttl_date")),
                        "tick_size": _f(r.get("tick_sz")), "tick_value": _f(r.get("tick_val")),
                        "contract_size": _f(r.get("ctrt_size")), "expiry": _iso(r.get("expr_date")),
                        "last_trade": _iso(r.get("trd_to_date")), "first_notice": _iso(r.get("frst_noti_date")),
                        "decimals": _f(r.get("disp_digit"))})
        return out

    # -- Exchange-traded bonds ------------------------------------------------
    def bond_quote(self, isin: str) -> dict:
        """Last price per 10,000 face and yield (ernn_rate, percent)."""
        o = self._get("/uapi/domestic-bond/v1/quotations/inquire-price", "FHKBJ773400C0",
                      {"FID_COND_MRKT_DIV_CODE": MKT_BOND, "FID_INPUT_ISCD": isin}).get("output") or {}
        return {"isin": isin, "name": str(o.get("hts_kor_isnm") or "").strip(),
                "price": _f(o.get("bond_prpr")), "yield_pct": _f(o.get("ernn_rate")),
                "prev_close": _f(o.get("bond_prdy_clpr")), "volume": _f(o.get("acml_vol")),
                "as_of": date.today().isoformat()}

    def bond_daily(self, isin: str) -> Bars:
        """Daily prices per 10,000 face; one call returned 69 sessions (about 14
        months). No date parameters; KIS decides the window."""
        p = self._get("/uapi/domestic-bond/v1/quotations/inquire-daily-price", "FHKBJ773404C0",
                      {"FID_COND_MRKT_DIV_CODE": MKT_BOND, "FID_INPUT_ISCD": isin})
        return _bars(isin, p.get("output") or [], {"date": "stck_bsop_date", "close": "bond_prpr",
                                                    "open": "bond_oprc", "high": "bond_hgpr",
                                                    "low": "bond_lwpr", "volume": "acml_vol"},
                     note="price per 10,000 KRW face; thin trading shows flat days")

    def bond_info(self, isin: str) -> dict:
        """KSD issue terms: coupon, issue and redemption dates, payment cycle."""
        o = self._get("/uapi/domestic-bond/v1/quotations/search-bond-info", "CTPF1114R",
                      {"PDNO": isin, "PRDT_TYPE_CD": "302"}).get("output") or {}
        return {"isin": isin, "raw": {k: v for k, v in o.items() if v not in ("", None)}}

    # -- Domestic flows --------------------------------------------------------
    def investor_daily(self, code: str, *, days: int = 60) -> list[dict]:
        """Daily net buying by investor type for one stock (foreign, individual,
        institution and its sub-groups); 30 rows per call, paged on DATE_1."""
        rows: dict[str, dict] = {}
        end = date.today()
        for _ in range(days // 30 + 2):
            p = self._get("/uapi/domestic-stock/v1/quotations/investor-trade-by-stock-daily", "FHPTJ04160001",
                          {"FID_COND_MRKT_DIV_CODE": MKT_STOCK, "FID_INPUT_ISCD": code,
                           "FID_INPUT_DATE_1": _ymd(end), "FID_ORG_ADJ_PRC": "", "FID_ETC_CLS_CODE": ""})
            page = [r for r in (p.get("output2") or []) if r.get("stck_bsop_date")
                    and _iso(r["stck_bsop_date"]) not in rows]
            if not page:
                break
            for r in page:
                rows[_iso(r["stck_bsop_date"])] = r
            if len(rows) >= days:
                break
            end = date.fromisoformat(min(_iso(r["stck_bsop_date"]) for r in page)) - timedelta(days=1)
        out = []
        for d in sorted(rows):
            r = rows[d]
            out.append({"date": d, "close": _f(r.get("stck_clpr")), "volume": _f(r.get("acml_vol")),
                        "foreign_net_qty": _f(r.get("frgn_ntby_qty")),
                        "foreign_reg_net_qty": _f(r.get("frgn_reg_ntby_qty")),
                        "individual_net_qty": _f(r.get("prsn_ntby_qty")),
                        "institution_net_qty": _f(r.get("orgn_ntby_qty")),
                        "raw": {k: v for k, v in r.items() if "ntby" in k}})
        return out

    def short_sale_daily(self, code: str, *, days: int = 60) -> list[dict]:
        """Daily short-sale volume, its share of volume, and cumulative figures."""
        p = self._get("/uapi/domestic-stock/v1/quotations/daily-short-sale", "FHPST04830000",
                      {"FID_COND_MRKT_DIV_CODE": MKT_STOCK, "FID_INPUT_ISCD": code,
                       "FID_INPUT_DATE_1": _ymd(_start(days)), "FID_INPUT_DATE_2": _ymd(date.today())})
        out = [{"date": _iso(r.get("stck_bsop_date")), "close": _f(r.get("stck_clpr")),
                "volume": _f(r.get("acml_vol")), "short_qty": _f(r.get("ssts_cntg_qty")),
                "short_ratio_pct": _f(r.get("ssts_vol_rlim")), "short_cum_qty": _f(r.get("acml_ssts_cntg_qty"))}
               for r in p.get("output2") or [] if r.get("stck_bsop_date")]
        return sorted(out, key=lambda r: r["date"])

    # -- Probe --------------------------------------------------------------------
    def probe(self) -> dict:
        """One cheap call per domain; used by Settings. Never raises."""
        checks = {
            "etf": lambda: self.etf_quote("069500")["nav"],
            "index_futures": lambda: self.futures_quote("A01612")["price"],
            "ktb_futures": lambda: self.futures_quote(front_contract("KTB3") or "A65612")["price"],
            "options": lambda: len(self.option_expiries()),
            "overseas_stock": lambda: self.overseas_quote("NAS", "AAPL")["last"],
            "krw_yields": lambda: len(self.krw_yields_snapshot()),
            "overseas_futures": lambda: len(self.ovf_contract_detail(["VXV26"])),
            "bonds": lambda: self.bond_quote("KR103501GE31")["price"],
        }
        out = {}
        for name, fn in checks.items():
            try:
                v = fn()
                out[name] = {"ok": v is not None and v != 0, "detail": str(v)}
            except Exception as exc:
                out[name] = {"ok": False, "detail": f"{type(exc).__name__}: {exc}"}
        return out


# --------------------------------------------------------------------------- #
# Keyless instrument master files (symbol truth; no login needed)
# --------------------------------------------------------------------------- #
_MASTER_CACHE: dict[str, list[str]] = {}


def load_master(name: str) -> list[str]:
    """Lines of one KIS master file (cp949), fetched once per process."""
    if name not in _MASTERS:
        raise ValueError(f"Unknown master {name!r}. One of {_MASTERS}.")
    if name in _MASTER_CACHE:
        return _MASTER_CACHE[name]
    if _requests is None:
        raise KISError("requests is not installed")
    resp = _requests.get(f"{MASTER_URL}{name}.mst.zip", timeout=config.HTTP_TIMEOUT_SECONDS)
    if resp.status_code != 200:
        raise KISError(f"master {name}: HTTP {resp.status_code}")
    zf = zipfile.ZipFile(io.BytesIO(resp.content))
    text = zf.read(zf.namelist()[0]).decode("cp949", errors="replace")
    _MASTER_CACHE[name] = text.splitlines()
    return _MASTER_CACHE[name]


def _top_of_book(payload: dict) -> tuple[Optional[float], Optional[float]]:
    """Best bid/ask from an asking-price payload whatever KIS names the
    fields: the first key containing 'bidp'/'askp' with a positive value.
    After the 15:45 close KIS keeps showing the closing auction's unmatched
    orders (`aspr_acpt_hour` 154500: a 1.7-point bid under a 34-point option),
    which are not quotes; the book is then reported as empty."""
    bid = ask = None
    for key in ("output1", "output2", "output"):
        block = payload.get(key)
        rows = block if isinstance(block, list) else [block] if isinstance(block, dict) else []
        for row in rows:
            hour = str(row.get("aspr_acpt_hour") or "")
            if "154500" <= hour < "180000":               # ponytail: night session (18:00–06:00) hours pass through untested
                return None, None
            for k, v in row.items():
                kl = k.lower()
                x = _f(v)
                if x is None or x <= 0:
                    continue
                if "bidp" in kl and bid is None:
                    bid = x
                elif "askp" in kl and ask is None:
                    ask = x
            if bid is not None and ask is not None:
                return bid, ask
    return bid, ask


def option_codes(yyyymm: str, product: str = "KOSPI200") -> list[dict]:
    """KOSPI200 monthly option series from fo_idx_code_mts: rows whose first
    field is 5 (calls) or 6 (puts): [{code, isin, kind 'C'|'P', strike, expiry}]."""
    out = []
    for line in load_master("fo_idx_code_mts"):
        parts = line.split("|")
        if len(parts) < 9 or parts[0] not in ("5", "6"):
            continue
        desc = parts[3].strip()
        if not desc.startswith(("C ", "P ")) or yyyymm not in desc or product not in parts[8]:
            continue
        try:
            strike = float(parts[5])
        except ValueError:
            continue
        out.append({"code": parts[1].strip(), "isin": parts[2].strip(), "kind": "C" if parts[0] == "5" else "P",
                    "strike": strike, "expiry": yyyymm})
    return sorted(out, key=lambda r: (r["kind"], r["strike"]))


def index_futures_contracts(product: str = "KOSPI200") -> list[dict]:
    """KRX index futures from fo_idx_code_mts: [{code, isin, name, order, underlying}],
    order 1 = front month. product: KOSPI200 | 미니KOSPI200 | KOSDAQ150 (substring match)."""
    out = []
    for line in load_master("fo_idx_code_mts"):
        parts = line.split("|")
        if len(parts) < 9 or not parts[3].strip().startswith("F "):
            continue
        code, isin, name, order, und = parts[1].strip(), parts[2].strip(), parts[3].strip(), parts[6].strip(), parts[8].strip()
        if product and product not in und and product not in name:
            continue
        try:
            order_n = int(order)
        except ValueError:
            order_n = 99
        out.append({"code": code, "isin": isin, "name": name, "order": order_n, "underlying": und})
    return sorted(out, key=lambda r: (r["order"], r["name"]))


_COM_RE = re.compile(r"^(\d\d)([A-Z0-9]{6})\s+(KR[A-Z0-9]{10})(.+?)\s+(F|SP)\s+(\S+)\s+(\d{9})")


def commodity_futures_contracts(keyword: str = "3년국채") -> list[dict]:
    """KTB / KOFR / currency / gold futures from fo_com_code (fixed width):
    [{code, isin, name, expiry_yyyymm, order}], order 1 = front month."""
    out = []
    for line in load_master("fo_com_code"):
        m = _COM_RE.match(line)
        if not m or m.group(5) != "F":
            continue
        name = m.group(4).strip()
        if keyword and keyword not in name:
            continue
        out.append({"code": m.group(2), "isin": m.group(3), "name": name,
                    "expiry_yyyymm": m.group(6), "order": int(m.group(7)[-1] or 9)})
    return sorted(out, key=lambda r: (r["order"], r["expiry_yyyymm"]))


_FRONT_KEYWORDS = {"KTB3": "3년국채", "KTB5": "5년국채", "KTB10": "10년국채", "KTB30": "30년국채",
                   "USD": "미국달러", "KOFR": "KOFR", "GOLD": "금"}


def front_contract(product: str = "KOSPI200") -> Optional[str]:
    """Front-month short code for a product family, from the live master."""
    try:
        if product in _FRONT_KEYWORDS:
            rows = commodity_futures_contracts(_FRONT_KEYWORDS[product])
        else:
            rows = index_futures_contracts(product)
    except Exception:
        return None
    return rows[0]["code"] if rows else None


_BOND_RE = re.compile(r"^(\w{4})(KR[A-Z0-9]{10})(국고\d{5}-\d{4}\(\d{2}-\d+\))")


def ktb_issues() -> list[dict]:
    """Korea Treasury Bonds from bond_code: [{isin, name, coupon, maturity_yyyymm}];
    the name encodes coupon (03250 = 3.250 %) and maturity (2903 = 2029-03)."""
    out: dict[str, dict] = {}
    for line in load_master("bond_code"):
        m = _BOND_RE.match(line)
        if not m:
            continue
        name = m.group(3)
        coupon = int(name[2:7]) / 1000.0
        yymm = name[8:12]
        out[m.group(2)] = {"isin": m.group(2), "name": name, "coupon_pct": coupon,
                           "maturity_yyyymm": f"20{yymm[:2]}{yymm[2:]}"}
    return sorted(out.values(), key=lambda r: r["maturity_yyyymm"])


def provider_status() -> dict:
    """Presence-only summary for Settings (no network)."""
    return {"id": "kis_markets", "label": "KIS asset domains (ETF, F/O, overseas, bonds)",
            "ready": config.kis_ready(), "vars": ("KIS_APP_KEY", "KIS_APP_SECRET"),
            "note": "Read-only quotation endpoints; probed 2026-09-25 with a stock-account key: "
                    "ETF NAV, KOSPI200/KTB/USD futures, option board, overseas stocks, KRW yields, "
                    "CBOE VX / ICE DX / CME BTC bars, KTB prices. CME ES/NQ/ZN/6E/GC/CL history is refused."}


if __name__ == "__main__":
    # Offline self-check on the parsers and the paging logic with a fake client.
    class _Fake:
        ready = True

        def __init__(self):
            self.calls = 0

        def _get(self, path, tr_id, params):
            self.calls += 1
            # An empty BYMD means "up to today", as at KIS. A fixed stand-in date here broke this check once the
            # paging window, which _start() measures from date.today(), moved past it (2026-10-10 onward).
            end = params.get("FID_INPUT_DATE_2") or params.get("BYMD")
            end_d = date.fromisoformat(_iso(end)) if end else date.today()
            rows = [{"stck_bsop_date": _ymd(end_d - timedelta(days=i)), "futs_prpr": f"{1000 + i}",
                     "xymd": _ymd(end_d - timedelta(days=i)), "clos": f"{100 + i}",
                     "stck_clpr": f"{100 + i}", "nav": f"{100.5 + i}", "dprt": "-0.20", "acml_vol": "10"}
                    for i in range(0, 5)]
            return {"rt_cd": "0", "output": rows, "output2": rows, "output1": {"futs_prpr": "1000"}}

    km = KISMarkets(client=_Fake())
    b = km.futures_daily("A01612", days=12)
    assert len(b) == 12 and b.dates == tuple(sorted(b.dates)) and b.close[-1] == 1000.0, b
    assert km.client.calls == 3, km.client.calls
    nav = km.etf_nav_daily("069500", days=7)
    assert len(nav) == 7 and len(nav.extra["nav"]) == 7 and nav.extra["premium_pct"][0] == -0.2
    ov = km.overseas_daily("nas", "aapl", days=6)
    assert ov.symbol == "NAS:AAPL" and len(ov) == 6
    assert KISMarkets.futures_market("A01612") == "F" and KISMarkets.futures_market("A65612") == "CF"
    assert KISMarkets.futures_market("101W12") == "F" and KISMarkets.futures_market("A75612") == "CF"
    assert KISMarkets.kospi200_expiry("202610") == date(2026, 10, 8)
    assert KISMarkets.kospi200_expiry("202612") == date(2026, 12, 10)
    m = _COM_RE.match("11A65612   KR4A656C00093년국채    F 202612                      000000001BM33년채")
    assert m and m.group(2) == "A65612" and m.group(6) == "202612" and m.group(7)[-1] == "1"
    bm = _BOND_RE.match("F902KR103501GE31국고03250-2903(24-1)                    13202401232024031020290310   Y")
    assert bm and bm.group(2) == "KR103501GE31"
    h = b.to_history()
    assert h.source == "KIS" and len(h) == 12
    print("ok")
