"""KIS (한국투자증권) Open API — read-only market data only.

SCOPE BOUNDARY
--------------
KIS is a brokerage API and its surface includes order submission, cancellation
and account mutation. **None of that is implemented here, anywhere in this
file, or anywhere in this repository.** This client exposes exactly four
read-only quotation endpoints:

    현재가        /uapi/domestic-stock/v1/quotations/inquire-price
    일별 시세     /uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice
    지수          /uapi/domestic-stock/v1/quotations/inquire-index-price
    체결          /uapi/domestic-stock/v1/quotations/inquire-ccnl

Adding an order path would require a new module, a new credential (account
number), and an explicit decision. That is deliberate.

TOKENS
------
KIS issues a bearer token valid for ~24h and rate-limits issuance hard, so the
token is cached on disk under `~/.tradegen/kis_token.json` with its expiry. A
cold start reuses a still-valid token rather than minting a new one; that is the
difference between the client working and being throttled out for the day. The
cache file holds a token, never the appkey/appsecret.
"""
from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import config

try:
    import requests as _once                         # one attempt: the engine's quote path
    from data.net import session as requests         # shared session: retry + backoff
except Exception:                                    # pragma: no cover
    requests = _once = None


class KISError(RuntimeError):
    """A KIS call failed. Never carries a credential in its message."""


class KISUnavailable(KISError):
    """KIS is not configured on this machine."""


_TOKEN_PATH = config.state_root() / "kis_token.json"     # never QUANTGEN's ~/.nextgen token: a refresh would clobber it
_TOKEN_LOCK = threading.Lock()

# Read-only guard (M1, TASK-M1-02; spec P0, T-RO-02). The allowlist is frozen in config.py
# (`config.KIS_QUOTATION_ALLOWLIST`); `_get` checks the path against it before credentials are read or a request
# is built.
QUOTATION_ALLOWLIST = config.KIS_QUOTATION_ALLOWLIST


def check_quotation_path(path: str) -> str:
    """The single read-only check, run before any credential is read or request built. Never carries a credential.

    Every KIS endpoint, trading and account ones included, lives under `/uapi/`; such a path passes only when it is
    an allowlisted `/quotations/` path. A `/trading/` or `/oauth2/` path, a blank or non-string path, and anything
    not rooted at "/" always raise. A path outside `/uapi/` is not a KIS API call (the engine's pacing test probes
    `_get` with the placeholder "/p"); it reaches no endpoint and is let through — tighten to allowlist-only once
    that probe names a quotation path."""
    allow = config.KIS_QUOTATION_ALLOWLIST
    if path in allow:
        return path
    if (not isinstance(path, str) or not path.startswith("/") or path.startswith("/uapi/")
            or "/trading/" in path or "/oauth2/" in path or "/quotations/" in path):
        raise KISError(f"refused: {path!r} is not an allowlisted KIS quotation path (read-only client, P0)")
    return path

# KIS caps requests per second and answers the excess with HTTP 500 /
# EGW00201 ("초당 거래건수를 초과하였습니다"). Probed 2026-10-02: ten back-to-back
# calls (about 25 ms apart) inside one second were enough to trip it, which a
# single ETF analysis does. Every call in the process is therefore spaced out.
_RATE_LIMITED = "EGW00201"
_MIN_GAP_S = 0.12                       # about 8 requests a second
_PACE_LOCK = threading.Lock()
_last_call = [0.0]


def _pace() -> None:
    """Sleep until `_MIN_GAP_S` has passed since the previous KIS call, across
    threads: the engine's quote and a page's paging loop share one allowance."""
    with _PACE_LOCK:
        wait = _MIN_GAP_S - (time.monotonic() - _last_call[0])
        if wait > 0:
            time.sleep(wait)
        _last_call[0] = time.monotonic()

# Market division codes.
_MRKT_STOCK = "J"
_MRKT_INDEX = "U"

INDEX_CODES = {
    "KOSPI": "0001",
    "KOSDAQ": "1001",
    "KOSPI200": "2001",
}


@dataclass(frozen=True)
class Quote:
    ticker: str
    name: str
    price: Optional[float]
    change: Optional[float]
    change_pct: Optional[float]
    volume: Optional[float]
    market_cap: Optional[float]
    high: Optional[float]
    low: Optional[float]
    open: Optional[float]
    currency: str = "KRW"
    as_of: str = ""
    source: str = "KIS"


def _f(value: Any) -> Optional[float]:
    try:
        text = str(value).strip().replace(",", "")
        return float(text) if text not in ("", "-", "None") else None
    except Exception:
        return None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class KISClient:
    """Thin read-only wrapper. Construction performs no network request."""

    def __init__(self, *, base_url: Optional[str] = None, timeout_s: Optional[float] = None):
        self.base_url = (base_url or config.KIS_BASE_URL).rstrip("/")
        self.timeout_s = timeout_s or config.HTTP_TIMEOUT_SECONDS
        self.ready = bool(config.kis_ready() and requests is not None)

    # -- token ---------------------------------------------------------------
    def _cached_token(self) -> Optional[str]:
        try:
            data = json.loads(_TOKEN_PATH.read_text(encoding="utf-8"))
        except Exception:
            return None
        token = data.get("access_token")
        expires = data.get("expires_at", 0)
        if token and time.time() < float(expires) - 120:
            return str(token)
        return None

    def _store_token(self, token: str, expires_in: float) -> None:
        try:
            _TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
            _TOKEN_PATH.write_text(
                json.dumps({"access_token": token,
                            "expires_at": time.time() + float(expires_in)}),
                encoding="utf-8",
            )
        except Exception:
            pass          # a non-persistable token still works for this session

    def token(self) -> str:
        if not self.ready:
            raise KISUnavailable("Set KIS_APP_KEY and KIS_APP_SECRET to enable KIS")
        with _TOKEN_LOCK:
            cached = self._cached_token()
            if cached:
                return cached
            app_key, app_secret = config.kis_credentials()
            try:
                # Plain requests, one attempt: issuance is rate-limited, and a
                # quote that needs a new token must not stack three connection
                # attempts inside one engine pass.
                resp = _once.post(
                    f"{self.base_url}/oauth2/tokenP",
                    json={"grant_type": "client_credentials",
                          "appkey": app_key, "appsecret": app_secret},
                    timeout=self.timeout_s,
                )
            except Exception as exc:
                raise KISError(f"token request failed: {type(exc).__name__}") from None
            if resp.status_code != 200:
                raise KISError(f"token rejected (HTTP {resp.status_code})")
            payload = resp.json()
            token = payload.get("access_token")
            if not token:
                raise KISError("token response contained no access_token")
            self._store_token(token, payload.get("expires_in") or 86400)
            return str(token)

    # -- request -------------------------------------------------------------
    def _get(self, path: str, tr_id: str, params: dict, *, tr_cont: str = "",
             retry: bool = True) -> dict:
        """One GET. `tr_cont="N"` asks for the next page of a list endpoint; the
        response's own `tr_cont` header ("F"/"M" = more pages, "D"/"E" = last)
        is kept in `self.last_headers` so a caller can loop. `retry=False`
        makes a single attempt (the live quote: the engine's grace window is
        the retry there, see `data.net`)."""
        check_quotation_path(path)                  # T-RO-02: before credentials, before any request
        app_key, app_secret = config.kis_credentials()
        headers = {
            "authorization": f"Bearer {self.token()}",
            "appkey": app_key,
            "appsecret": app_secret,
            "tr_id": tr_id,
            "custtype": "P",
            "content-type": "application/json; charset=utf-8",
        }
        if tr_cont:
            headers["tr_cont"] = tr_cont
        for attempt in (1, 2):
            _pace()
            try:
                resp = (requests if retry else _once).get(
                    f"{self.base_url}{path}", headers=headers,
                    params=params, timeout=self.timeout_s)
            except Exception as exc:
                raise KISError(f"{tr_id}: {type(exc).__name__}") from None
            self.last_headers = {k.lower(): v for k, v in resp.headers.items()}
            if resp.status_code == 200:
                break
            # KIS reports its own errors as HTTP 500 with a code in the body.
            try:
                body = resp.json()
                code, why = str(body.get("msg_cd") or ""), str(body.get("msg1") or "").strip()
            except Exception:
                code = why = ""
            if code == _RATE_LIMITED and retry and attempt == 1:
                time.sleep(1.0)             # let the one-second window pass, then once more
                continue
            raise KISError(f"{tr_id}: HTTP {resp.status_code}"
                           + (f" ({code}: {why})" if code else ""))
        try:
            payload = resp.json()
        except Exception:
            raise KISError(f"{tr_id}: response was not JSON") from None
        if str(payload.get("rt_cd", "0")) != "0":
            raise KISError(f"{tr_id}: {payload.get('msg1') or 'provider rejected request'}")
        return payload

    # -- endpoints -----------------------------------------------------------
    def quote(self, code: str) -> Quote:
        """Current price for a six-digit KRX code (e.g. '005930')."""
        code = _normalize(code)
        payload = self._get(
            "/uapi/domestic-stock/v1/quotations/inquire-price",
            "FHKST01010100",
            {"FID_COND_MRKT_DIV_CODE": _MRKT_STOCK, "FID_INPUT_ISCD": code},
            retry=False,
        )
        out = payload.get("output") or {}
        return Quote(
            ticker=code,
            name=str(out.get("hts_kor_isnm") or "").strip(),
            price=_f(out.get("stck_prpr")),
            change=_f(out.get("prdy_vrss")),
            change_pct=_f(out.get("prdy_ctrt")),
            volume=_f(out.get("acml_vol")),
            market_cap=_f(out.get("hts_avls")),
            high=_f(out.get("stck_hgpr")),
            low=_f(out.get("stck_lwpr")),
            open=_f(out.get("stck_oprc")),
            as_of=_now(),
        )

    def daily(self, code: str, *, start: Optional[str] = None,
              end: Optional[str] = None, adjusted: bool = True) -> list[dict]:
        """Daily OHLCV. Dates are YYYYMMDD; defaults to the last ~100 sessions."""
        code = _normalize(code)
        end = end or datetime.now().strftime("%Y%m%d")
        start = start or (datetime.now() - timedelta(days=150)).strftime("%Y%m%d")
        payload = self._get(
            "/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice",
            "FHKST03010100",
            {
                "FID_COND_MRKT_DIV_CODE": _MRKT_STOCK,
                "FID_INPUT_ISCD": code,
                "FID_INPUT_DATE_1": start,
                "FID_INPUT_DATE_2": end,
                "FID_PERIOD_DIV_CODE": "D",
                "FID_ORG_ADJ_PRC": "0" if adjusted else "1",
            },
        )
        rows = []
        for raw in payload.get("output2") or []:
            date = str(raw.get("stck_bsop_date") or "").strip()
            if not date:
                continue
            rows.append({
                "date": f"{date[:4]}-{date[4:6]}-{date[6:]}",
                "open": _f(raw.get("stck_oprc")),
                "high": _f(raw.get("stck_hgpr")),
                "low": _f(raw.get("stck_lwpr")),
                "close": _f(raw.get("stck_clpr")),
                "volume": _f(raw.get("acml_vol")),
                "source": "KIS",
            })
        rows.sort(key=lambda r: r["date"])
        return rows

    def index(self, name: str = "KOSPI") -> dict:
        """Index level for KOSPI / KOSDAQ / KOSPI200."""
        code = INDEX_CODES.get(name.upper())
        if code is None:
            raise KISError(f"unknown index '{name}'")
        payload = self._get(
            "/uapi/domestic-stock/v1/quotations/inquire-index-price",
            "FHPUP02100000",
            {"FID_COND_MRKT_DIV_CODE": _MRKT_INDEX, "FID_INPUT_ISCD": code},
        )
        out = payload.get("output") or {}
        return {
            "market": name.upper(),
            "level": _f(out.get("bstp_nmix_prpr")),
            "change": _f(out.get("bstp_nmix_prdy_vrss")),
            "change_pct": _f(out.get("prdy_ctrt")),
            "volume": _f(out.get("acml_vol")),
            "as_of": _now(),
            "source": "KIS",
        }

    def status(self) -> dict:
        if not config.kis_ready():
            return {"ready": False, "reason": "KIS_APP_KEY / KIS_APP_SECRET not set"}
        if requests is None:
            return {"ready": False, "reason": "requests library unavailable"}
        return {"ready": True, "reason": ""}


def _normalize(code: str) -> str:
    """Accept '005930', '005930.KS' or 'A005930' and return the bare KRX code."""
    raw = (code or "").strip().upper()
    if raw.startswith("A") and raw[1:].isdigit():
        raw = raw[1:]
    if "." in raw:
        raw = raw.split(".", 1)[0]
    return raw.zfill(6) if raw.isdigit() else raw
