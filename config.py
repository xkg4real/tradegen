"""Local configuration for the NEXTGEN skill cockpit.

Two independent credential families, deliberately kept apart:

  * SKILL providers (FINVIZ / Alpaca / FXMacroData) — consumed by the scripts
    inside the trading-skills repository. NEXTGEN never reads the values itself;
    it only reports presence and forwards them to a subprocess env.

  * FMP is BOTH. The skill library forwards it to subprocesses, and the trading
    system reads it directly to quote non-Korean venues. One key, two consumers
    — worth stating, because the rest of this module keeps the two credential
    families apart and FMP is the deliberate exception.

  * KRX providers (KIS / OpenDART / KRX marketplace) — consumed by NEXTGEN's own
    read-only Korean market data layer, because the skill library has no KRX
    coverage at all.

A blank value keeps that provider unavailable. Nothing is ever logged, echoed
into a run transcript, or written to a run artifact.
"""
from __future__ import annotations

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass


def _clean(name: str) -> str:
    """Read an env var, rejecting blanks and unedited <placeholder> values."""
    value = (os.getenv(name) or "").strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        value = value[1:-1].strip()
    if value.startswith("<") and value.endswith(">"):
        return ""
    return value


def _present(name: str) -> bool:
    return bool(_clean(name))


# --------------------------------------------------------------------------- #
# TRADEGEN state root
# --------------------------------------------------------------------------- #
# TRADEGEN was split off QUANTGEN on 2026-10-23. QUANTGEN keeps ~/.nextgen (its trial ledgers, frozen studies
# and KIS token), so every mutable TRADEGEN path resolves under ~/.tradegen and the overrides carry TRADEGEN_
# names: an OS-level QUANTGEN_* / NEXTGEN_* variable (which load_dotenv never overrides) cannot redirect it.
from core.isolation import QUANTGEN_REPO, QUANTGEN_STATE, refuse_quantgen  # noqa: E402,F401  (also used by writers)
import core.isolation as _isolation  # noqa: E402


def state_path(env: str, default: Path) -> Path:
    """`env` when set, else `default`; refused inside QUANTGEN (refuse_quantgen)."""
    return refuse_quantgen(_clean(env) or default, env)


def state_root() -> Path:
    """TRADEGEN_HOME, else ~/.tradegen; refused inside QUANTGEN and, once per process and root, when it holds a
    symlink, a junction or a hard link (core.isolation.state_root; A0)."""
    return _isolation.state_root()


# --------------------------------------------------------------------------- #
# Trading-skills repository
# --------------------------------------------------------------------------- #
_DEFAULT_SKILLS_ROOT = (
    Path.home() / "Downloads" / "claude-trading-skills-main" / "claude-trading-skills-main"
)


def skills_root() -> Path:
    """Filesystem root of the trading-skills repository."""
    override = _clean("NEXTGEN_SKILLS_ROOT")
    return Path(override) if override else _DEFAULT_SKILLS_ROOT


def skills_root_valid(root: Path | None = None) -> bool:
    root = root or skills_root()
    return (root / "skills-index.yaml").is_file() and (root / "skills").is_dir()


# Interpreter used to run skill scripts. Defaults to the one running NEXTGEN.
def skill_python() -> str:
    import sys
    return _clean("NEXTGEN_SKILL_PYTHON") or sys.executable


SKILL_TIMEOUT_SECONDS = float(_clean("NEXTGEN_SKILL_TIMEOUT") or "300")

# Where run transcripts and artifacts are written.
def runs_dir() -> Path:
    return state_path("TRADEGEN_RUNS_DIR", state_root() / "runs")


# --------------------------------------------------------------------------- #
# Skill-provider credentials (forwarded to subprocesses, never read for value)
# --------------------------------------------------------------------------- #
# Maps a skills-index integration id -> the env var(s) that satisfy it.
SKILL_CREDENTIALS: dict[str, tuple[str, ...]] = {
    "fmp": ("FMP_API_KEY",),
    "finviz": ("FINVIZ_API_KEY",),
    "alpaca": ("ALPACA_API_KEY", "ALPACA_SECRET_KEY"),
    "fxmacrodata": ("FXMACRODATA_API_KEY",),
}

# Integration ids that need no credential at all.
KEYLESS_INTEGRATIONS = frozenset({
    "local_calculation", "public_csv", "coingecko", "binance_funding",
    "yfinance", "websearch",
})

# Integration ids satisfied by a file the operator supplies at run time.
FILE_INPUT_INTEGRATIONS = frozenset({
    "prices_json", "user_input", "chart_image", "mt5_local_files",
    "news_events_json", "catalyst_events_json", "profiles_json",
})


def skill_credential_present(integration_id: str) -> bool:
    names = SKILL_CREDENTIALS.get(integration_id)
    if not names:
        return False
    return all(_present(n) for n in names)


def skill_env() -> dict[str, str]:
    """Environment handed to a skill subprocess: inherited os.environ plus any
    configured provider keys. Values are copied straight through and are never
    inspected, logged, or persisted by NEXTGEN."""
    env = dict(os.environ)
    for names in SKILL_CREDENTIALS.values():
        for name in names:
            value = _clean(name)
            if value:
                env[name] = value
    env.setdefault("PYTHONIOENCODING", "utf-8")
    env.setdefault("PYTHONUTF8", "1")
    return env


# --------------------------------------------------------------------------- #
# FMP — NEXTGEN's own read-only quotes for every venue outside Korea
# --------------------------------------------------------------------------- #
# Only the quote endpoint is used. FMP's screeners, ratings and price targets
# are deliberately not wrapped: the trading system executes the operator's
# rules and must not acquire a source of opinions.
def fmp_key() -> str:
    return _clean("FMP_API_KEY")


def fmp_ready() -> bool:
    return bool(fmp_key())


# The /api/v3 path was retired on 2025-08-31 and answers HTTP 403 for keys
# issued after that date. /stable is the current API.
FMP_BASE_URL = _clean("FMP_BASE_URL") or "https://financialmodelingprep.com/stable"

# Minimum seconds between refetches of the same symbol. The engine ticks every
# few seconds; without this, one rule would spend a daily quota in an hour.
# Must stay well under QUOTE_MAX_AGE_SECONDS or the cache itself would age a
# quote past the staleness guard.
FMP_MIN_INTERVAL_SECONDS = float(_clean("NEXTGEN_FMP_MIN_INTERVAL") or "20")


# --------------------------------------------------------------------------- #
# KRX providers — NEXTGEN's own read-only Korean market data
# --------------------------------------------------------------------------- #
# KIS is a brokerage API. Only its market-data endpoints are implemented here;
# no order, cancel, or account-mutation path exists anywhere in this codebase.
def kis_ready() -> bool:
    return _present("KIS_APP_KEY") and _present("KIS_APP_SECRET")


def kis_credentials() -> tuple[str, str]:
    return _clean("KIS_APP_KEY"), _clean("KIS_APP_SECRET")


KIS_BASE_URL = _clean("KIS_BASE_URL") or "https://openapi.koreainvestment.com:9443"

# Read-only guard (v2 M1, TASK-M1-02; spec P0, T-RO-02): the frozen allowlist of KIS quotation endpoints. The
# single KIS choke point (data/krx/kis_client.py KISClient._get) refuses any other path before a credential is
# read or a request is built. The 24 paths in use (kis_client.py, data/kis_markets.py) plus the asking-price path
# of the owner-run quote-field check (docs/kis_quote_check.py). Never a /trading/, /oauth2/ or account path.
KIS_QUOTATION_ALLOWLIST = frozenset({
    "/uapi/domestic-stock/v1/quotations/inquire-price",
    "/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice",
    "/uapi/domestic-stock/v1/quotations/inquire-index-price",
    "/uapi/domestic-stock/v1/quotations/inquire-daily-indexchartprice",
    "/uapi/domestic-stock/v1/quotations/inquire-asking-price-exp-ccn",
    "/uapi/domestic-stock/v1/quotations/comp-interest",
    "/uapi/domestic-stock/v1/quotations/investor-trade-by-stock-daily",
    "/uapi/domestic-stock/v1/quotations/daily-short-sale",
    "/uapi/etfetn/v1/quotations/inquire-price",
    "/uapi/etfetn/v1/quotations/nav-comparison-daily-trend",
    "/uapi/etfetn/v1/quotations/inquire-component-stock-price",
    "/uapi/domestic-futureoption/v1/quotations/inquire-price",
    "/uapi/domestic-futureoption/v1/quotations/inquire-daily-fuopchartprice",
    "/uapi/domestic-futureoption/v1/quotations/display-board-futures",
    "/uapi/domestic-futureoption/v1/quotations/display-board-option-list",
    "/uapi/domestic-futureoption/v1/quotations/display-board-callput",
    "/uapi/domestic-futureoption/v1/quotations/inquire-asking-price",
    "/uapi/overseas-price/v1/quotations/price",
    "/uapi/overseas-price/v1/quotations/dailyprice",
    "/uapi/overseas-price/v1/quotations/inquire-daily-chartprice",
    "/uapi/overseas-futureoption/v1/quotations/daily-ccnl",
    "/uapi/overseas-futureoption/v1/quotations/search-contract-detail",
    "/uapi/domestic-bond/v1/quotations/inquire-price",
    "/uapi/domestic-bond/v1/quotations/inquire-daily-price",
    "/uapi/domestic-bond/v1/quotations/search-bond-info",
})


def opendart_ready() -> bool:
    return _present("OPENDART_API_KEY")


def opendart_key() -> str:
    return _clean("OPENDART_API_KEY")


OPENDART_BASE_URL = _clean("OPENDART_BASE_URL") or "https://opendart.fss.or.kr/api"

# The KRX data marketplace exposes some datasets without a key and others with
# one. Absence of a key does not disable the client; it narrows what it serves.
def krx_key() -> str:
    return _clean("KRX_API_KEY")


def krx_ready() -> bool:
    # Was unconditionally True when the keyless CSV export worked. KRX now
    # answers HTTP 403 to it, so readiness genuinely depends on the key.
    return bool(krx_key())


KRX_BASE_URL = _clean("KRX_BASE_URL") or "https://data-dbg.krx.co.kr/svc/apis"
KRX_OTP_URL = "http://data.krx.co.kr/comm/fileDn/GenerateOTP/generate.cmd"
KRX_DOWNLOAD_URL = "http://data.krx.co.kr/comm/fileDn/download_csv/download.cmd"

HTTP_TIMEOUT_SECONDS = float(_clean("NEXTGEN_HTTP_TIMEOUT") or "12")


def krx_provider_status() -> list[dict]:
    """Presence-only report for the Settings page. No values are returned."""
    return [
        {"id": "kis", "label": "KIS (한국투자증권)", "ready": kis_ready(),
         "vars": ("KIS_APP_KEY", "KIS_APP_SECRET"),
         "note": "Read-only quotes, OHLCV and index levels for KOSPI/KOSDAQ."},
        {"id": "opendart", "label": "OpenDART (금융감독원)", "ready": opendart_ready(),
         "vars": ("OPENDART_API_KEY",),
         "note": "Corporate filings and reported financials. Free key."},
        {"id": "krx", "label": "KRX Data marketplace", "ready": krx_ready(),
         "vars": ("KRX_API_KEY",),
         "note": "Whole-market session snapshots. The keyless CSV export now "
                 "returns HTTP 403, so the free Open API key is required."},
    ]


def skill_provider_status() -> list[dict]:
    return [
        {"id": "fmp", "label": "Financial Modeling Prep",
         "ready": skill_credential_present("fmp"), "vars": ("FMP_API_KEY",),
         "note": "Required by 28 skills."},
        {"id": "finviz", "label": "FinViz Elite",
         "ready": skill_credential_present("finviz"), "vars": ("FINVIZ_API_KEY",),
         "note": "Required by 4 screener skills."},
        {"id": "alpaca", "label": "Alpaca",
         "ready": skill_credential_present("alpaca"),
         "vars": ("ALPACA_API_KEY", "ALPACA_SECRET_KEY"),
         "note": "Portfolio and broker-side planning skills."},
        {"id": "fxmacrodata", "label": "FXMacroData",
         "ready": skill_credential_present("fxmacrodata"),
         "vars": ("FXMACRODATA_API_KEY",),
         "note": "Macro release calendar."},
    ]


# --------------------------------------------------------------------------- #
# Trading system storage
# --------------------------------------------------------------------------- #
# Rules the operator authored, the simulated order book, and the engine's halt
# state. Kept beside the run transcripts, on this machine only.
def trading_dir() -> Path:
    return state_path("TRADEGEN_TRADING_DIR", state_root() / "trading")


# Macro overlay v2 mutable state (artifacts, governance_events.jsonl, book states, alerts). The
# shipped section 7 store stays read-only in the repository; nothing mutable lives there.
def macro_dir() -> Path:
    return state_path("TRADEGEN_MACRO_DIR", state_root() / "macro")


# How old a quote may be before the engine halts rather than acting on it.
QUOTE_MAX_AGE_SECONDS = float(_clean("NEXTGEN_QUOTE_MAX_AGE") or "120")

# Seconds between evaluation passes while armed.
ENGINE_TICK_SECONDS = float(_clean("NEXTGEN_ENGINE_TICK") or "5")

# How many passes a symbol's quote may be missing, for a reason that can clear
# by itself (timeout, 5xx, rate limit), before the engine halts. During the
# window the rule is skipped and nothing can fire: the engine still never acts
# without a fresh quote. 0 restores halt-on-the-first-miss; the runtime caps it
# at 10. A failure that waiting cannot fix (plan refusal, missing key, unknown
# venue) halts at once whatever this is set to. Counted in passes, not seconds:
# a pass lasts the tick interval plus however long the failing request takes.
NO_DATA_GRACE_TICKS = int(float(_clean("NEXTGEN_NO_DATA_GRACE") or "3"))


# --------------------------------------------------------------------------- #
# QUANTGEN — quant analysis credentials (personal build)
# --------------------------------------------------------------------------- #
# The NEXTGEN client product deliberately had no opinion source. QUANTGEN is
# the operator's personal instrument, so two new credential families exist:
#
#   * ANTHROPIC_API_KEY — Claude API, for AI deep analysis of computed quant
#     results. Absent, every screen still renders its local deterministic
#     narrative; the "Deep analysis" action simply says what is missing.
#   * GS_CLIENT_ID / GS_CLIENT_SECRET — GS Marquee OAuth credentials for
#     gs_quant's session tier (instrument pricing). gs_quant's offline
#     timeseries analytics need no credentials at all.
def anthropic_key() -> str:
    return _clean("ANTHROPIC_API_KEY")


def ai_ready() -> bool:
    return bool(anthropic_key())


def ai_model() -> str:
    return _clean("QUANTGEN_AI_MODEL") or "claude-sonnet-5"


def gs_client_id() -> str:
    return _clean("GS_CLIENT_ID")


def gs_client_secret() -> str:
    return _clean("GS_CLIENT_SECRET")


def quant_provider_status() -> list[dict]:
    """Presence-only report for the Settings page. No values are returned."""
    return [
        {"id": "anthropic", "label": "Claude API (deep analysis)",
         "ready": ai_ready(), "vars": ("ANTHROPIC_API_KEY",),
         "note": f"AI narrative analysis of quant results. Model: {ai_model()}."},
        {"id": "gs", "label": "GS Marquee (gs_quant session)",
         "ready": bool(gs_client_id() and gs_client_secret()),
         "vars": ("GS_CLIENT_ID", "GS_CLIENT_SECRET"),
         "note": "Optional. Offline gs_quant analytics work without it."},
    ]


# --------------------------------------------------------------------------- #
# Crypto — keyless public data (Upbit, Binance) and an optional read-only
# Upbit key. The key must be issued with 자산조회 (balance) scope only; QUANTGEN
# never implements an order, withdrawal or transfer path on any venue and
# never holds a private key or seed phrase.
# --------------------------------------------------------------------------- #
def upbit_ready() -> bool:
    return _present("UPBIT_ACCESS_KEY") and _present("UPBIT_SECRET_KEY")


def upbit_keys() -> tuple[str, str]:
    return _clean("UPBIT_ACCESS_KEY"), _clean("UPBIT_SECRET_KEY")


def crypto_provider_status() -> list[dict]:
    """Presence-only report for the Settings page. No values are returned."""
    from data.crypto.crypto_client import provider_status
    return provider_status()


# --------------------------------------------------------------------------- #
# FICC — keyless market data (FRED, Yahoo) and its cache
# --------------------------------------------------------------------------- #
# Both providers are keyless, so "ready" only means the library is importable.
# `core.ficc.data` is the single module that calls them; everything else in
# the FICC core is offline and answers on labeled SYNTHETIC data when asked.
FRED_BASE_URL = _clean("FRED_BASE_URL") or "https://fred.stlouisfed.org/graph/fredgraph.csv"

# Seconds a fetched series stays valid in the FICC cache. 0 disables caching.
FICC_CACHE_TTL_SECONDS = float(_clean("NEXTGEN_FICC_CACHE_TTL") or str(6 * 3600))


def ficc_cache_dir() -> Path:
    return state_path("TRADEGEN_FICC_CACHE", state_root() / "ficc_cache")


def ficc_provider_status() -> list[dict]:
    """Presence-only report for the Settings page (keyless: presence == importable)."""
    from core.ficc.data import fred_ready, yfinance_ready
    return [
        {"id": "fred", "label": "FRED (St. Louis Fed)", "ready": fred_ready(), "vars": (),
         "note": "Keyless. Treasury curve, SOFR, OECD short rates, credit OAS, macro."},
        {"id": "yfinance", "label": "Yahoo Finance (yfinance)", "ready": yfinance_ready(),
         "vars": (), "note": "Keyless. FX spot, futures and index levels."},
    ]
