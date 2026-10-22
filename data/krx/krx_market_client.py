"""KRX Data marketplace — whole-market Korean snapshots.

TWO SURFACES, AND ONLY ONE OF THEM STILL WORKS
-----------------------------------------------
1. **Official Open API** (`data-dbg.krx.co.kr/svc/apis`), authenticated with an
   `AUTH_KEY` header. Free to register at data.krx.co.kr. This is the supported
   path and the one this client prefers.

2. **Keyless CSV export** (`data.krx.co.kr`, the OTP → download.cmd dance the
   browser performs). Verified against the live site on 2026-08-18: the OTP
   endpoint answers `HTTP 403`, and the JSON endpoint answers `HTTP 400 LOGOUT`
   even behind a seeded session cookie. KRX has closed it to non-browser
   clients.

The keyless path is kept because it costs nothing to try and may be reopened,
but `probe()` reports its true state so the UI can say "blocked by KRX" instead
of showing an empty table and letting the operator assume the market is quiet.
No method here ever fabricates a value to cover a dead provider.
"""
from __future__ import annotations

import csv
import io
from datetime import datetime, timezone
from typing import Optional

import config

try:
    import requests                  # engine fallback path: one attempt; the grace window is the retry
except Exception:                                    # pragma: no cover
    requests = None

# --- official Open API -------------------------------------------------------
_API_ENDPOINTS = {
    "KOSPI": "sto/stk_bydd_trd",
    "KOSDAQ": "sto/ksq_bydd_trd",
    "INDEX": "idx/krx_dd_trd",
}

# --- legacy keyless export ---------------------------------------------------
_BLD_ALL_QUOTES = "dbms/MDC/STAT/standard/MDCSTAT01501"
_MARKET_IDS = {"ALL": "ALL", "KOSPI": "STK", "KOSDAQ": "KSQ", "KONEX": "KNX"}
_BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Referer": "http://data.krx.co.kr/contents/MDC/MDI/mdiLoader/index.cmd",
    "X-Requested-With": "XMLHttpRequest",
}


class KRXError(RuntimeError):
    pass


def _f(value) -> Optional[float]:
    try:
        text = str(value).strip().replace(",", "").replace("%", "")
        return float(text) if text not in ("", "-", "None") else None
    except Exception:
        return None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _session_date(date: Optional[str]) -> str:
    return date or datetime.now().strftime("%Y%m%d")


class KRXMarketClient:
    """Whole-market KRX data. Construction performs no network request."""

    def __init__(self, *, timeout_s: Optional[float] = None):
        self.timeout_s = timeout_s or config.HTTP_TIMEOUT_SECONDS
        self.has_key = bool(config.krx_key())
        self.ready = requests is not None

    # -- official Open API ---------------------------------------------------
    def _api(self, endpoint: str, params: dict) -> list[dict]:
        if requests is None:
            raise KRXError("requests library unavailable")
        key = config.krx_key()
        if not key:
            raise KRXError("KRX_API_KEY not set")
        url = f"{config.KRX_BASE_URL.rstrip('/')}/{endpoint}"
        try:
            resp = requests.get(url, headers={"AUTH_KEY": key}, params=params,
                                timeout=max(self.timeout_s, 30))
        except Exception as exc:
            raise KRXError(f"{endpoint}: {type(exc).__name__}") from None
        if resp.status_code == 401:
            raise KRXError(f"{endpoint}: KRX rejected the AUTH_KEY")
        if resp.status_code != 200:
            raise KRXError(f"{endpoint}: HTTP {resp.status_code}")
        try:
            payload = resp.json()
        except Exception:
            raise KRXError(f"{endpoint}: response was not JSON") from None
        block = payload.get("OutBlock_1")
        if not isinstance(block, list):
            raise KRXError(f"{endpoint}: unexpected response shape")
        return block

    # -- legacy keyless export ----------------------------------------------
    def _csv(self, bld: str, params: dict) -> list[dict]:
        if requests is None:
            raise KRXError("requests library unavailable")
        try:
            otp = requests.post(
                config.KRX_OTP_URL,
                data={**params, "bld": bld, "name": "fileDown", "url": bld},
                headers=_BROWSER_HEADERS, timeout=self.timeout_s,
            )
            if otp.status_code == 403:
                raise KRXError("KRX blocks the keyless export (HTTP 403)")
            if otp.status_code != 200 or not otp.text.strip():
                raise KRXError(f"OTP request failed (HTTP {otp.status_code})")
            resp = requests.post(
                config.KRX_DOWNLOAD_URL, data={"code": otp.text.strip()},
                headers=_BROWSER_HEADERS, timeout=max(self.timeout_s, 30),
            )
            if resp.status_code != 200:
                raise KRXError(f"CSV download failed (HTTP {resp.status_code})")
        except KRXError:
            raise
        except Exception as exc:
            raise KRXError(str(type(exc).__name__)) from None
        for encoding in ("euc-kr", "cp949", "utf-8-sig"):
            try:
                return list(csv.DictReader(io.StringIO(resp.content.decode(encoding))))
            except Exception:
                continue
        raise KRXError("could not decode CSV")

    # -- endpoints -----------------------------------------------------------
    def all_quotes(self, market: str = "ALL", *, date: Optional[str] = None) -> list[dict]:
        """Every listed instrument's session close. Empty list means unavailable
        — check `probe()` for the reason rather than reading it as 'no data'."""
        day = _session_date(date)
        if self.has_key:
            markets = ("KOSPI", "KOSDAQ") if market.upper() == "ALL" else (market.upper(),)
            out: list[dict] = []
            for name in markets:
                endpoint = _API_ENDPOINTS.get(name)
                if not endpoint:
                    continue
                try:
                    for raw in self._api(endpoint, {"basDd": day}):
                        out.append(self._from_api(raw, name))
                except KRXError:
                    continue
            if out:
                return out
        try:
            rows = self._csv(_BLD_ALL_QUOTES, {
                "mktId": _MARKET_IDS.get(market.upper(), "ALL"), "trdDd": day,
                "share": "1", "money": "1", "csvxls_isNo": "false",
            })
        except KRXError:
            return []
        return [q for q in (self._from_csv(r, market) for r in rows) if q]

    def _from_api(self, raw: dict, market: str) -> dict:
        return {
            "ticker": str(raw.get("ISU_SRT_CD") or "").strip(),
            "name": str(raw.get("ISU_NM") or "").strip(),
            "market": market,
            "close": _f(raw.get("TDD_CLSPRC")),
            "change": _f(raw.get("CMPPREVDD_PRC")),
            "change_pct": _f(raw.get("FLUC_RT")),
            "open": _f(raw.get("TDD_OPNPRC")),
            "high": _f(raw.get("TDD_HGPRC")),
            "low": _f(raw.get("TDD_LWPRC")),
            "volume": _f(raw.get("ACC_TRDVOL")),
            "turnover": _f(raw.get("ACC_TRDVAL")),
            "market_cap": _f(raw.get("MKTCAP")),
            "shares": _f(raw.get("LIST_SHRS")),
            "currency": "KRW",
            "as_of": _now(),
            "source": "KRX Open API",
        }

    def _from_csv(self, raw: dict, market: str) -> Optional[dict]:
        code = (raw.get("종목코드") or "").strip()
        if not code:
            return None
        return {
            "ticker": code,
            "name": (raw.get("종목명") or "").strip(),
            "market": (raw.get("시장구분") or market.upper()).strip(),
            "close": _f(raw.get("종가")),
            "change": _f(raw.get("대비")),
            "change_pct": _f(raw.get("등락률")),
            "open": _f(raw.get("시가")),
            "high": _f(raw.get("고가")),
            "low": _f(raw.get("저가")),
            "volume": _f(raw.get("거래량")),
            "turnover": _f(raw.get("거래대금")),
            "market_cap": _f(raw.get("시가총액")),
            "shares": _f(raw.get("상장주식수")),
            "currency": "KRW",
            "as_of": _now(),
            "source": "KRX",
        }

    def indices(self, *, date: Optional[str] = None) -> list[dict]:
        if not self.has_key:
            return []
        try:
            rows = self._api(_API_ENDPOINTS["INDEX"], {"basDd": _session_date(date)})
        except KRXError:
            return []
        out = []
        for raw in rows:
            name = str(raw.get("IDX_NM") or "").strip()
            if not name:
                continue
            out.append({
                "name": name,
                "level": _f(raw.get("CLSPRC_IDX")),
                "change": _f(raw.get("CMPPREVDD_IDX")),
                "change_pct": _f(raw.get("FLUC_RT")),
                "volume": _f(raw.get("ACC_TRDVOL")),
                "as_of": _now(),
                "source": "KRX Open API",
            })
        return out

    # -- diagnostics ---------------------------------------------------------
    def probe(self) -> dict:
        """Actually test the configured path so Settings can tell the truth."""
        if requests is None:
            return {"ready": False, "path": "none", "reason": "requests library unavailable"}
        if self.has_key:
            try:
                self._api(_API_ENDPOINTS["KOSPI"], {"basDd": _session_date(None)})
                return {"ready": True, "path": "open-api", "reason": ""}
            except KRXError as exc:
                return {"ready": False, "path": "open-api", "reason": str(exc)}
        try:
            self._csv(_BLD_ALL_QUOTES, {"mktId": "ALL", "trdDd": _session_date(None),
                                        "share": "1", "money": "1", "csvxls_isNo": "false"})
            return {"ready": True, "path": "keyless-csv", "reason": ""}
        except KRXError as exc:
            return {"ready": False, "path": "keyless-csv",
                    "reason": f"{exc}. Register a free KRX_API_KEY at data.krx.co.kr."}

    def status(self) -> dict:
        if requests is None:
            return {"ready": False, "reason": "requests library unavailable"}
        if self.has_key:
            return {"ready": True, "reason": "", "detail": "KRX Open API key set"}
        return {"ready": False,
                "reason": "no KRX_API_KEY; the keyless export is blocked by KRX",
                "detail": "keyless-csv (blocked)"}
