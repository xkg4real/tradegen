"""OpenDART (전자공시시스템) — Korean corporate filings and reported financials.

OpenDART keys the whole system on an eight-digit `corp_code` that is *not* the
stock ticker. The mapping ships as a ~20 MB zipped XML at `/corpCode.xml`, so
this client downloads it once and caches the parsed ticker→corp_code map under
`~/.tradegen/dart_corp_codes.json`. Without that cache every lookup would cost a
20 MB download, which is why the first call is slow and every later one is not.

Endpoints used, all read-only:

    corpCode.xml         ticker -> corp_code map (cached)
    list.json            filing list for a company and date range
    fnlttSinglAcnt.json  single-company financial statement accounts
"""
from __future__ import annotations

import io
import json
import re
import threading
import time
import zipfile
from datetime import datetime, timedelta, timezone
from typing import Optional
from xml.etree import ElementTree

import config
from core.isolation import checked_target

try:
    from data.net import session as requests         # shared session: retry + backoff
except Exception:                                    # pragma: no cover
    requests = None


class DARTError(RuntimeError):
    """An OpenDART call failed. Never carries the key in its message."""


class DARTUnavailable(DARTError):
    pass


_CACHE_PATH = config.state_root() / "dart_corp_codes.json"
_CACHE_TTL_S = 7 * 24 * 3600
_CACHE_LOCK = threading.Lock()

# OpenDART returns its own status codes in the body with HTTP 200.
_STATUS_TEXT = {
    "010": "unregistered key",
    "011": "key temporarily suspended",
    "013": "no data for that query",
    "020": "request quota exceeded",
    "100": "invalid parameter",
    "800": "service under maintenance",
}

REPORT_CODES = {
    "Q1": "11013", "H1": "11012", "Q3": "11014", "FY": "11011",
}


class OpenDARTClient:
    def __init__(self, *, base_url: Optional[str] = None, timeout_s: Optional[float] = None):
        self.base_url = (base_url or config.OPENDART_BASE_URL).rstrip("/")
        self.timeout_s = timeout_s or config.HTTP_TIMEOUT_SECONDS
        self.ready = bool(config.opendart_ready() and requests is not None)

    def _need(self) -> str:
        if not self.ready:
            raise DARTUnavailable("Set OPENDART_API_KEY to enable OpenDART")
        return config.opendart_key()

    def _get(self, path: str, params: dict) -> dict:
        key = self._need()
        try:
            resp = requests.get(f"{self.base_url}/{path}",
                                params={**params, "crtfc_key": key},
                                timeout=self.timeout_s)
        except Exception as exc:
            raise DARTError(f"{path}: {type(exc).__name__}") from None
        if resp.status_code != 200:
            raise DARTError(f"{path}: HTTP {resp.status_code}")
        try:
            payload = resp.json()
        except Exception:
            raise DARTError(f"{path}: response was not JSON") from None
        status = str(payload.get("status", "000"))
        if status not in ("000", "013"):
            raise DARTError(f"{path}: {_STATUS_TEXT.get(status, 'error ' + status)}")
        return payload

    # -- corp code map -------------------------------------------------------
    def _load_cache(self) -> Optional[dict[str, dict]]:
        try:
            blob = json.loads(_CACHE_PATH.read_text(encoding="utf-8"))
        except Exception:
            return None
        if time.time() - float(blob.get("fetched_at", 0)) > _CACHE_TTL_S:
            return None
        entries = blob.get("entries")
        return entries if isinstance(entries, dict) else None

    def _store_cache(self, entries: dict[str, dict]) -> None:
        target = checked_target(_CACHE_PATH, "OpenDART cache")       # A0: outside the try, so a refusal propagates
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(
                json.dumps({"fetched_at": time.time(), "entries": entries},
                           ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception:
            pass

    def corp_codes(self, *, refresh: bool = False) -> dict[str, dict]:
        """ticker -> {corp_code, corp_name}. Downloads and caches on first use."""
        with _CACHE_LOCK:
            if not refresh:
                cached = self._load_cache()
                if cached is not None:
                    return cached
            key = self._need()
            try:
                resp = requests.get(f"{self.base_url}/corpCode.xml",
                                    params={"crtfc_key": key},
                                    timeout=max(self.timeout_s, 60))
            except Exception as exc:
                raise DARTError(f"corpCode: {type(exc).__name__}") from None
            if resp.status_code != 200:
                raise DARTError(f"corpCode: HTTP {resp.status_code}")
            try:
                archive = zipfile.ZipFile(io.BytesIO(resp.content))
                xml = archive.read(archive.namelist()[0])
            except Exception:
                # A key error comes back as a tiny XML body, not a zip.
                text = resp.content[:400].decode("utf-8", errors="replace")
                code = re.search(r"<status>(\d+)</status>", text)
                reason = _STATUS_TEXT.get(code.group(1), "unreadable response") if code else "unreadable response"
                raise DARTError(f"corpCode: {reason}") from None
            entries: dict[str, dict] = {}
            for node in ElementTree.fromstring(xml).iter("list"):
                ticker = (node.findtext("stock_code") or "").strip()
                corp = (node.findtext("corp_code") or "").strip()
                if ticker and corp:               # skip unlisted entities
                    entries[ticker] = {
                        "corp_code": corp,
                        "corp_name": (node.findtext("corp_name") or "").strip(),
                    }
            self._store_cache(entries)
            return entries

    def resolve(self, ticker: str) -> Optional[dict]:
        return self.corp_codes().get(_six(ticker))

    # -- endpoints -----------------------------------------------------------
    def filings(self, ticker: str, *, days: int = 90, limit: int = 50) -> list[dict]:
        """Recent disclosure filings for a listed company."""
        entry = self.resolve(ticker)
        if entry is None:
            raise DARTError(f"'{ticker}' is not a listed KRX company in the DART map")
        end = datetime.now()
        payload = self._get("list.json", {
            "corp_code": entry["corp_code"],
            "bgn_de": (end - timedelta(days=days)).strftime("%Y%m%d"),
            "end_de": end.strftime("%Y%m%d"),
            "page_count": min(max(limit, 1), 100),
        })
        rows = []
        for raw in payload.get("list") or []:
            receipt = str(raw.get("rcept_no") or "")
            rows.append({
                "date": str(raw.get("rcept_dt") or ""),
                "title": str(raw.get("report_nm") or "").strip(),
                "filer": str(raw.get("flr_nm") or "").strip(),
                "corp_name": str(raw.get("corp_name") or "").strip(),
                "receipt_no": receipt,
                "url": f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={receipt}" if receipt else "",
                "source": "OpenDART",
            })
        return rows[:limit]

    def financials(self, ticker: str, *, year: Optional[int] = None,
                   report: str = "FY") -> list[dict]:
        """Reported statement accounts for one company and reporting period."""
        entry = self.resolve(ticker)
        if entry is None:
            raise DARTError(f"'{ticker}' is not a listed KRX company in the DART map")
        year = year or (datetime.now().year - 1)
        code = REPORT_CODES.get(report.upper())
        if code is None:
            raise DARTError(f"unknown report period '{report}'")
        payload = self._get("fnlttSinglAcnt.json", {
            "corp_code": entry["corp_code"],
            "bsns_year": str(year),
            "reprt_code": code,
        })
        rows = []
        for raw in payload.get("list") or []:
            rows.append({
                "statement": str(raw.get("sj_nm") or ""),
                "account": str(raw.get("account_nm") or ""),
                "this_term": str(raw.get("thstrm_amount") or ""),
                "prev_term": str(raw.get("frmtrm_amount") or ""),
                "currency": str(raw.get("currency") or "KRW"),
                "source": "OpenDART",
            })
        return rows

    def status(self) -> dict:
        if not config.opendart_ready():
            return {"ready": False, "reason": "OPENDART_API_KEY not set"}
        if requests is None:
            return {"ready": False, "reason": "requests library unavailable"}
        return {"ready": True, "reason": ""}


def _six(ticker: str) -> str:
    raw = (ticker or "").strip().upper().split(".", 1)[0]
    if raw.startswith("A") and raw[1:].isdigit():
        raw = raw[1:]
    return raw.zfill(6) if raw.isdigit() else raw
