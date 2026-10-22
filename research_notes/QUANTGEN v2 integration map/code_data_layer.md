# code_data_layer — map of the existing QUANTGEN data layer (for the v2.0 build)

Scope read completely (2026-10-05): `core/ficc/data.py` (724 l), `core/ficc/macro.py` (309), `core/ficc/common.py` (71), `core/calendars.py` (199), `core/markets.py` (406), `config.py` (347), `.env.example` (50), `data/net.py` (56), `data/kis_markets.py` (839), `data/krx/{__init__,gateway,kis_client,krx_market_client,opendart_client}.py`, `data/fmp/quote_client.py` (283), `data/crypto/crypto_client.py` (395), `data/calendars/index.json` + `KRX.json` + `US.json` (structure of all 22). Also read because it shares the cache: `core/quant/history.py` (505). `.env` was not opened.

Line references: `file:line`. "SPEC" = `QUANTGEN_Quant_Council_2026-10-03/claude_code/QUANTGEN_MACRO_INTEGRATION.md`. "R3" = `QUANTGEN_techfund_research_bundle/QUANTGEN_techfund_research/research_notes/R3_TF_neural_link.md`.

Runtime facts measured on this machine: Python 3.13.14; `locale.getpreferredencoding()` = cp949, stdout cp949, `sys.flags.utf8_mode` = 0; pandas_datareader 0.11.1, yfinance 1.4.1, pyyaml 6.0.3, exchange_calendars 4.13.2 installed (dev-only dependency). Last suite run `qa/acceptance_results.json`: 266/266 PASS (cockpit 47, engine 89, ui 4, quant 53, ficc 56, expansion 17).

---

## 0. The known bug: "ficc_cache served a pre-close row as a session close" — exact location

Two independent caches write into the same directory `config.ficc_cache_dir()` (`config.py:334-336`; default `~/.nextgen/ficc_cache`, env `NEXTGEN_FICC_CACHE`). TTL for both: `config.FICC_CACHE_TTL_SECONDS` (`config.py:331`; `float(NEXTGEN_FICC_CACHE_TTL or 6*3600)` = 21600 s; 0 disables).

### 0.1 Cache A — `core/ficc/data.py` (NO protection at all; this is the defect as SPEC 1283 / TASK-M1-12 describe it)

| Step | Code | What happens |
|---|---|---|
| key | `_cache_key(provider, id, days)` `data.py:219-220` | `re.sub(r"[^A-Za-z0-9_.-]", "_", f"{provider}_{id}_{days}")` → file `{PROVIDER}_{id}_{days}.json` (`EURUSD=X` → `YFINANCE_EURUSD_X_504.json`, `^VIX` → `_VIX`) |
| fetch | `_yf_fetch(tickers, period)` `data.py:195-210` | `yf.download(tickers, period=period, progress=False, auto_adjust=True, threads=False)`; keeps only `(str(d)[:10], float(close))`. During a session Yahoo's daily frame already contains today's bar whose "Close" is the last trade so far. No timestamp, volume or bar state survives. |
| put | `_cache_put(key, rows)` `data.py:241-251` | `_MEM[key] = (now, rows)` and file `{"ts": time.time(), "rows": [[date, value], ...]}`. Unconditional (only gate: `len(r) >= _MIN_OBS` = 5 in `_provider_rows:451-455`). `ts` is one wall-clock stamp per FILE, not per row. No live flag, no session check. |
| get | `_cache_get(key)` `data.py:223-238` | hit iff `time.time() - ts < ttl` (memory first, then disk). That is the entire TTL rule: flat age < 6 h. No test of "has the market closed since `ts`", no row status. |
| serve | `_provider_rows` `data.py:422-456` → `_series_from_rows` `459-464` | returns `Series(source=provider, dates, values, note="")`. A cache hit is not marked in `note` (unlike cache B). `Series.last` / `.last_date` = today's running price dated today. |

Consequence: a file written at 10:56 KST is served until 16:56 KST, i.e. across the 15:30 close and across a post-close run at 15:40:30 KST, as "the close" of that date. Consumers: `load_series`, `load_many`, `load_fx_spot` (Yahoo), `load_treasury_curve`, `load_short_rate`, `load_policy_rates` → `macro._row` (`last`, changes, z), `macro_sheet.as_of`, FX/rates/bonds/structuring pages, `ui/crypto_page.py:59`, `ui/quant_lab_page.py:74-78`. For FRED ids the same flat TTL serves a pre-publication file as "latest" for up to 6 h after a release (staleness, not provisional).

Evidence on disk (file names and stamps only): `YFINANCE_EURUSD_X_504.json` ts 2026-09-08T01:27:41Z, last row dated 2026-09-08; `YFINANCE_GC_F_504.json` ts 2026-09-10T13:38:14Z, last row 2026-09-10; `YFINANCE_*_6000.json` written Sat 2026-09-26T15:44Z with a last row dated 2026-09-26 (a Saturday-dated Yahoo FX row). Keys only `['rows','ts']`.

### 0.2 Cache B — `core/quant/history.py::_cached` `history.py:398-451` (partially fixed; still returns a running price as a close)

- File `HIST_{provider}_{SYMBOL}_{days}.json` = `{"ts","live","symbol","source","note","adjustment","dates","closes"}` (`history.py:445-448`).
- `live = _may_be_trading(provider, symbol)` is judged BEFORE the request (`:440`). Read rule (`:430-432`): `final = p.get("live") is False and not _traded_since(provider, symbol, ts)`; `limit = ttl if final else min(ttl, _CACHE_LIVE_TTL)`; `_CACHE_LIVE_TTL = 600.0` (`:356`). A file without a `live` key is never final.
- `_may_be_trading(provider, symbol, at=None)` `:359-383`: venue = `"US"` if `provider == "FMP"` and no `.` in symbol, or `provider == "KIS"` with prefix `NAS|NYS|AMS:`; `"KRX"` if provider in (`KIS`,`YFINANCE`) and `_looks_krx(symbol)` (6 digits, optional `.KS/.KQ`). With a venue: `any(markets.is_open(venue, t) is not False for t in (at, at - 60 min))` (two sample instants only). Without: `provider == "CRYPTO" or endswith(("-USD","-KRW")) or at.weekday() < 5 or (weekday == 6 and hour >= 21)`.
- `_traded_since` `:386-395`: samples `_may_be_trading` every 30 min from `ts` to now.
- Bypass: `ttl <= 0` or `not _READY.get(provider, lambda: True)()` (`_READY = {"FMP": fmp_key, "KIS": kis_ready}`) → provider asked directly.
- Remaining holes: (a) `History` has no status field: a fresh mid-session fetch, and any hit inside 10 min, returns the running last bar as `closes[-1]` dated today; the `live` flag stays in the JSON file. (b) A cache hit only appends `"cached %Y-%m-%d %H:%M"` (naive LOCAL time, no zone) to `note`. (c) `^KS11`, `^KS200`, futures, FX have no venue → "live" on every weekday, so the KOSPI index is never final on a weekday evening (safe for the cache, useless as a status). (d) `kis_history` → `KISClient.daily` (`FID_COND_MRKT_DIV_CODE "J"`, field `stck_clpr`, `end = today`) returns today's bar mid-session with the current price in `stck_clpr`. On disk: `HIST_FMP_KO_504.json` `live=True`, ts 2026-10-01T17:19Z (13:19 ET), last row 2026-10-01.

### 0.3 What SPEC requires instead (binding text)

- SPEC 1283: the 6-hour cache "becomes the store's read-through cache"; a cached value keeps its `retrieved_at_utc`; "At a decision it may be served only if its `retrieved_at_utc` is later than the series' most recent due publication instant ≤ `decision_utc` (for a close-type series: later than `close_print_bound_utc` + 10 min of the decided session); otherwise the store re-fetches, and a failed re-fetch is a `MissingInput`, never the cached row". "The cache never holds derived values of acting inputs."
- SPEC 1323 / 4206: `data.reject_rows_retrieved_before_close_plus_minutes: 10`, anchor `close_print_bound_utc` of the row's session (06:40:30Z for KRX today).
- SPEC 4201-4203: `ingest: {trigger: [pit_snapshot, publication_schedule], retries_min: [1, 5, 15, 60], decision_deadline: next_session_open_minus_30min, dedupe_key: [series_id, obs_date, vintage, source, value, value_status], first_seen_is_retrieved_at: true, fetch_log: fetch_log.jsonl, rows_mutated: never, posting_time_pollers: {TREASURY_PAR: "17:30-21:00 ET every 5 min", FRED_REPOSTS: last_updated}}`.
- Acceptance T-PROV-01 (SPEC 1327-1329): store read for the 2-Oct-2026 KOSPI decision returns `MissingInput("missing")` at knowledge time 10:31 KST, `MissingInput("provisional_intraday")` at 11:00 KST, `7,003.74 [official_close]` at 16:00 KST; vendor row 6,943.66 (volume 99,651 vs 227,641 final).

Minimum fix surface: one guard in `_cache_get`/`_cache_put` (all `core.ficc.data` loaders route through `_provider_rows`) plus the same guard in `history._cached`; both need a per-row retrieval stamp and a calendar lookup, which do not exist yet (see D).

---

## A. File by file

### A.1 `config.py`

Purpose: env-only configuration; nothing logged. `load_dotenv()` at import (`:26-30`, failure ignored). All module-level constants are evaluated at import; tests monkeypatch attributes (`config.FICC_CACHE_TTL_SECONDS = 0.0`, `config.kis_ready = lambda: False`) and cockpit tests call `importlib.reload(config)`. Convention (binding for new code): `import config` and read `config.X` at call time; never `from config import X`.

Helpers: `_clean(name) -> str` (`:33-40`: strip, drop one layer of matching quotes, `<placeholder>` → `""`), `_present(name) -> bool`.

| Name | Line | Env var | Default / return |
|---|---|---|---|
| `skills_root() -> Path` | 55 | `NEXTGEN_SKILLS_ROOT` | `~/Downloads/claude-trading-skills-main/claude-trading-skills-main` |
| `skills_root_valid(root=None) -> bool` | 61 | | needs `skills-index.yaml` and `skills/` |
| `skill_python() -> str` | 67 | `NEXTGEN_SKILL_PYTHON` | `sys.executable` |
| `SKILL_TIMEOUT_SECONDS` | 72 | `NEXTGEN_SKILL_TIMEOUT` | 300.0 |
| `runs_dir() -> Path` | 75 | `NEXTGEN_RUNS_DIR` | `~/.nextgen/runs` |
| `SKILL_CREDENTIALS` | 84 | | `{"fmp": ("FMP_API_KEY",), "finviz": ("FINVIZ_API_KEY",), "alpaca": ("ALPACA_API_KEY","ALPACA_SECRET_KEY"), "fxmacrodata": ("FXMACRODATA_API_KEY",)}` |
| `KEYLESS_INTEGRATIONS`, `FILE_INPUT_INTEGRATIONS` | 92, 98 | | frozensets of skill integration ids |
| `skill_credential_present(id)`, `skill_env() -> dict` | 104, 111 | | `skill_env` adds `PYTHONIOENCODING=utf-8`, `PYTHONUTF8=1` |
| `fmp_key()`, `fmp_ready()` | 132, 136 | `FMP_API_KEY` | |
| `FMP_BASE_URL` | 142 | `FMP_BASE_URL` | `https://financialmodelingprep.com/stable` |
| `FMP_MIN_INTERVAL_SECONDS` | 148 | `NEXTGEN_FMP_MIN_INTERVAL` | 20.0 |
| `kis_ready()`, `kis_credentials() -> (key, secret)` | 156, 160 | `KIS_APP_KEY`, `KIS_APP_SECRET` | |
| `KIS_BASE_URL` | 164 | `KIS_BASE_URL` | `https://openapi.koreainvestment.com:9443` |
| `opendart_ready()`, `opendart_key()`, `OPENDART_BASE_URL` | 167-175 | `OPENDART_API_KEY`, `OPENDART_BASE_URL` | `https://opendart.fss.or.kr/api` |
| `krx_key()`, `krx_ready()` | 179, 183 | `KRX_API_KEY` | ready == key present |
| `KRX_BASE_URL`, `KRX_OTP_URL`, `KRX_DOWNLOAD_URL` | 189-191 | `KRX_BASE_URL` | `https://data-dbg.krx.co.kr/svc/apis`; OTP/CSV urls fixed |
| `HTTP_TIMEOUT_SECONDS` | 193 | `NEXTGEN_HTTP_TIMEOUT` | 12.0 |
| `krx_provider_status()`, `skill_provider_status()`, `quant_provider_status()`, `crypto_provider_status()`, `ficc_provider_status()` | 196, 212, 289, 316, 339 | | `list[{"id","label","ready","vars","note"}]`, presence only |
| `trading_dir() -> Path` | 236 | `NEXTGEN_TRADING_DIR` | `~/.nextgen/trading` (rules.json, engine.json) |
| `QUOTE_MAX_AGE_SECONDS` | 242 | `NEXTGEN_QUOTE_MAX_AGE` | 120.0 |
| `ENGINE_TICK_SECONDS` | 245 | `NEXTGEN_ENGINE_TICK` | 5.0 |
| `NO_DATA_GRACE_TICKS` | 254 | `NEXTGEN_NO_DATA_GRACE` | 3 (runtime caps at 10) |
| `anthropic_key()`, `ai_ready()`, `ai_model()` | 269-278 | `ANTHROPIC_API_KEY`, `QUANTGEN_AI_MODEL` | model default `"claude-sonnet-5"` |
| `gs_client_id()`, `gs_client_secret()` | 281-286 | `GS_CLIENT_ID`, `GS_CLIENT_SECRET` | |
| `upbit_ready()`, `upbit_keys()` | 308-313 | `UPBIT_ACCESS_KEY`, `UPBIT_SECRET_KEY` | |
| `FRED_BASE_URL` | 328 | `FRED_BASE_URL` | `https://fred.stlouisfed.org/graph/fredgraph.csv` |
| `FICC_CACHE_TTL_SECONDS` | 331 | `NEXTGEN_FICC_CACHE_TTL` | 21600.0 |
| `ficc_cache_dir() -> Path` | 334 | `NEXTGEN_FICC_CACHE` | `~/.nextgen/ficc_cache` |

`.env.example` documents: `FMP_API_KEY, KIS_APP_KEY, KIS_APP_SECRET, OPENDART_API_KEY, KRX_API_KEY, FINVIZ_API_KEY, ALPACA_API_KEY, ALPACA_SECRET_KEY, FXMACRODATA_API_KEY, ANTHROPIC_API_KEY, QUANTGEN_AI_MODEL=claude-sonnet-5, GS_CLIENT_ID, GS_CLIENT_SECRET, UPBIT_ACCESS_KEY, UPBIT_SECRET_KEY, NEXTGEN_FICC_CACHE, NEXTGEN_FICC_CACHE_TTL=21600, NEXTGEN_NO_DATA_GRACE=3`. Read by code but absent from `.env.example`: every other `NEXTGEN_*` and `*_BASE_URL` above, and `NEXTGEN_MAX_AGE_<MARKET>` (`core/markets.py:222`, read with `os.getenv` at import, not through `_clean`). No decision-time constant exists in `config.py` (SPEC 1998 "the decision constants become calendar lookups" has nothing to replace here). No macro artifact directory, no ECOS / Treasury / ALFRED key.

### A.2 `data/net.py`

`session: requests.Session` with `HTTPAdapter(max_retries=RETRY)` on `https://` and `http://`. `RETRY = Retry(total=2, backoff_factor=0.5, status_forcelist=(502, 503, 504), allowed_methods=("GET",), respect_retry_after_header=False, raise_on_status=False)`. `logging.getLogger("urllib3").setLevel(logging.ERROR)` (retry logs would print URLs that carry API keys). Not retried: 429, 500, any POST that reached the server. Worst case ≈ 3 × `HTTP_TIMEOUT_SECONDS` + 1 s.

Users (asserted by engine test_81): `core.ficc.data._requests`, `core.quant.history._requests`, `data.crypto.crypto_client._requests`, `data.kis_markets._requests`, `data.krx.kis_client.requests`, `data.krx.opendart_client.requests` ARE `session`. Plain `requests` (one attempt; the engine grace window is the retry): `data.fmp.quote_client._requests`, `data.krx.krx_market_client.requests`, `data.krx.kis_client._once`.

### A.3 `core/ficc/common.py`

`TRADING_DAYS = 252`; `BP = 1e-4`; `KEY_TENORS = (0.25, 1.0, 2.0, 3.0, 5.0, 7.0, 10.0, 20.0, 30.0)`; `UST_TENORS = (1/12, 0.25, 0.5, 1.0, 2.0, 3.0, 5.0, 7.0, 10.0, 20.0, 30.0)`; `class FICCError(RuntimeError)`.
`parse_tenor(text) -> float` years (`d`: n/365, `w`: n/52, `m`: n/12, `y`: n; numbers pass through; raises `FICCError`); `parse_forward_tenor("5y5y") -> (5.0, 5.0)`; `tenor_label(years) -> str`; `bp_text(x, *, signed=True)` → `'+25.0bp'`; `pct_text(x, *, decimals=2, signed=False)`.

### A.4 `core/ficc/data.py`

Purpose: the only module in `core.ficc` that opens a socket (FRED, Yahoo); SYNTHETIC fallback. Constants: `SOURCES = ("auto", "fred", "yfinance", "synthetic")`; `G10_KRW = ("USD","EUR","JPY","GBP","AUD","CAD","CHF","KRW")`; `_TREASURY_IDS = ("DGS1MO","DGS3MO","DGS6MO","DGS1","DGS2","DGS3","DGS5","DGS7","DGS10","DGS20","DGS30")` (aligned with `UST_TENORS`); `_MIN_OBS = 5`; `_IBOR_CC` (`:69`, defined, unused).

Shapes (all `@dataclass(frozen=True)`):
```python
Series(id: str, label: str, source: str,            # "FRED" | "YFINANCE" | "SYNTHETIC"
       dates: tuple[str, ...],                      # ISO dates ascending
       values: tuple[float, ...], note: str = "")
  # len, .last, .first_date, .last_date, .array() -> np.ndarray,
  # .change(n) -> float|None  (last - value n OBSERVATIONS ago; None if too short)
  # .window(n) -> Series, .scaled(factor) -> Series      (dataclasses.replace)
CurveSnapshot(date: str, source: str, tenors: tuple[float, ...], par_yields: tuple[float, ...], note: str = "")   # decimals
CurvePanel(source: str, dates: tuple[str, ...], tenors: tuple[float, ...], yields: np.ndarray (T,K) NaN-free, note: str = "")
  # len, .at(i) -> CurveSnapshot, .latest()
Rows = list[tuple[str, float]]
```

Network touchpoints (the only two; tests patch these module attributes):
- `_fred_fetch(ids: list[str], start: str) -> dict[str, Rows]` (`:163-192`): `pandas_datareader.DataReader(ids, "fred", start)` when installed (it is), else `GET config.FRED_BASE_URL?id=&cosd=` per id; NaN and `'.'` dropped; date column `observation_date` or `DATE`. Returns raw FRED units (PERCENT for rates). No `realtime_start`, vintage or `last_updated`.
- `_yf_fetch(tickers: list[str], period: str) -> dict[str, Rows]` (`:195-210`): see §0.1. `auto_adjust=True` → adjusted closes.

Readiness: `fred_ready()` (= pdr or requests importable), `yfinance_ready()`.

Cache: `_MEM: dict[str, tuple[float, Rows]]` (process-global), `_cache_key`, `_cache_get`, `_cache_put` (§0.1). Synthetic results never cached. Cache errors swallowed.

Synthetic (deterministic, seed = first 4 bytes of `sha256(text.upper())`):
- `synthetic_series(id, *, days=756, kind="level") -> Series`; `kind ∈ {"level","price","rate"}`; `days >= 2` else `ValueError`. `rate`: OU, θ 2.0–5.0% DECIMAL, κ 0.8, floored at 0. Note `"Simulated series (...) — no market data provider was used."`
- `_synthetic_kind(id)`: `rate` if id starts with `DGS, SOFR, DFF, IR3TIB, T10Y, DFII, BAML, IORB`; `price` if any of `= ^ . -`; else `level`.
- `synthetic_curve_panel(*, days=504, seed=None) -> CurvePanel` (Nelson-Siegel random walk, τ=2y, floor 5 bp); `synthetic_fx(pair, *, days=504) -> Series` (id `"{PAIR}=X"`, label `"EUR/USD"`).
- Dates: `_business_dates(days)` = weekdays ending at `date.today()` (local clock; no holiday calendar); `_month_dates(n)` first weekday of each month.

Routing: `_check_source(source)` (lower-cases, raises `FICCError` on unknown); `_route(id)`: any of `= ^ . -` → `"YFINANCE"`; `[A-Za-z0-9_]+` → `"FRED"`; else `FICCError`. `_start_for(days)` = today − `int(days*1.6)+10` calendar days; `_period_for(days)`: ≤5 `5d`, ≤21 `1mo`, ≤63 `3mo`, ≤126 `6mo`, ≤252 `1y`, ≤504 `2y`, ≤1260 `5y`, else `10y`.

`_provider_rows(provider, ids, days) -> (rows_by_id, error_by_id)` (`:422-456`): cache-first; one batch call; on batch failure retries id by id; never raises; `< _MIN_OBS` rows is an error.

Loaders (public API):
```python
load_many(ids: list[str], *, source="auto", days=756) -> dict[str, Series]      # days >= 5 else ValueError; blank id -> FICCError
load_series(id: str, *, source="auto", days=756, label="") -> Series           # RAW provider units (FRED rates in percent)
load_treasury_curve(*, source="auto", days=504) -> CurvePanel                  # FRED DGS* / 100; columns FORWARD-FILLED, NaN rows dropped;
                                                                               # needs DGS2, DGS10 and >= 6 tenors; yfinance -> FICCError
load_fx_spot(pair: str, *, source="auto", days=504) -> Series                  # Yahoo "{PAIR}=X"; source="fred" -> FICCError
load_short_rate(ccy="USD", *, source="auto", days=756) -> Series               # DECIMAL (.scaled(0.01)); note "daily; FRED SOFR, percent converted to decimal"
load_policy_rates(ccys: list[str], *, source="auto", days=756) -> dict[str, Series]
probe() -> dict     # {"fred": {"ok": bool, "detail": str}, "yfinance": {...}}; live DGS10 / EURUSD=X; never raises, never caches
```
`_SHORT_RATE_IDS` (`:582-593`, id, frequency, label; first that answers wins): USD `SOFR` daily, `DFF` daily; EUR `ECBDFR` daily, `IR3TIB01EZM156N` monthly; GBP `IUDSOIA` daily, `IR3TIB01GBM156N` monthly; JPY `IRSTCI01JPM156N` monthly, `IR3TIB01JPM156N` monthly; KRW `IR3TIB01KRM156N` monthly; AUD `IR3TIB01AUM156N`; CAD `IR3TIB01CAM156N`; CHF `IR3TIB01CHM156N`. Monthly series stay monthly ("consumers forward-fill by date").

Degradation contract (tested): explicit provider that fails RAISES `FICCError`; only `source="auto"` degrades, per id, to SYNTHETIC with `note = "{PROVIDER} failed: {reason}; simulated series. {synthetic note}"` (`_degraded`, `:467`). Curve: `"FRED failed: {exc}; simulated curve panel. ..."`.

`__main__` self-check (`:663-724`) runs offline with both fetchers stubbed and TTL 0.

### A.5 `core/ficc/macro.py`

Answers backlog BL-G06 (SPEC 1119: "the list of the 18 indicators, the z-score windows and the regime-read method" were unknown to the spec authors).

`_Z_WINDOW = 252`; `_CHANGES = (("chg_1d", 1), ("chg_1w", 5), ("chg_1m", 21), ("chg_3m", 63))` (positional observations); `CURVE_REGIMES = ("bull steepener","bear steepener","bull flattener","bear flattener","parallel up","parallel down","unchanged")`; `RISK_REGIMES = ("risk-on","risk-off","neutral")`; `DOLLAR_REGIMES = ("strong","weak","range")`; `TREND_REGIMES = ("rising","falling","stable")`.

`Indicator(id, label, group, unit, source_hint)` frozen; `group ∈ {"rates","credit","fx","risk"}`, `unit ∈ {"pct","bp","level","fx"}`, `source_hint ∈ {"FRED","YFINANCE"}`.

`INDICATORS` (18, order binding for tests):

| id | label | group | unit | hint |
|---|---|---|---|---|
| DGS2 | UST 2y | rates | pct | FRED |
| DGS10 | UST 10y | rates | pct | FRED |
| DGS30 | UST 30y | rates | pct | FRED |
| T10Y2Y | 2s10s | rates | bp | FRED |
| DFII10 | 10y real (TIPS) | rates | pct | FRED |
| T10YIE | 10y breakeven | rates | pct | FRED |
| SOFR | SOFR | rates | pct | FRED |
| DFF | Fed funds | rates | pct | FRED |
| BAMLC0A0CM | IG OAS | credit | bp | FRED |
| BAMLH0A0HYM2 | HY OAS | credit | bp | FRED |
| DTWEXBGS | Broad USD | fx | level | FRED |
| DEXUSEU | EUR/USD | fx | fx | FRED |
| DEXJPUS | USD/JPY | fx | fx | FRED |
| DEXKOUS | USD/KRW | fx | fx | FRED |
| VIXCLS | VIX | risk | level | FRED |
| DCOILWTICO | WTI | risk | level | FRED |
| ZN=F | 10y note future | risk | level | YFINANCE |
| GC=F | Gold | risk | level | YFINANCE |

Absent from the sheet (SPEC §4.2 names them): VXVCLS/VIX3M, MOVE, DGS3MO/T10Y3M, T5YIFR, THREEFYTP10, BAA10Y, Brent, any Korean series, any monthly macro (CPI/PCE/UNRATE/PAYEMS), `DX-Y.NYB`.

```python
MacroRow(id, label, group, unit, last: float, last_date: str, chg_1d, chg_1w, chg_1m, chg_3m: float|None,
         z_1y: float, pct_1y: float, source: str)                      # frozen
Regime(curve, risk, dollar, inflation, real_rates, summary: str)        # frozen
MacroSheet(as_of: str, rows: tuple[MacroRow, ...], regime: Regime, sources: dict[str, int],
           synthetic_ids: tuple[str, ...], note: str = "")              # .row(id) -> MacroRow|None
macro_sheet(*, source="auto", days=504) -> MacroSheet                   # days >= 30 else ValueError
daily_brief(sheet, *, top=5) -> dict     # keys: as_of, regime, curve{2y,10y,30y,2s10s,10y_real,10y_breakeven}, movers_z, movers_1d(+rel_1d), rows, sources, synthetic_ids, note
weekly_brief(sheet, curve_report=None, carry_rows=None) -> dict   # daily + weekly_changes[{id,label,unit,chg_1w,chg_1m}] (+ curve_report{date,shape,regime,lookback,descriptors,changes}) (+ carry)
```
Row maths (`_row`, `:119-130`): if `s.source == "FRED"` and unit in (`pct`,`bp`) → `s.scaled(0.01)` (decimal); `x = last ≤252 obs`; `z_1y = (x[-1] − mean)/std` with population std (ddof 0), 0.0 when std = 0; `pct_1y = mean(x <= x[-1])`. Trailing window ending at the last observation (causal). `_weekdays` drops weekend-dated rows from every loaded series (`:133-149`).

Regime-read method (`_regime_from`, `:161-186`): five deterministic threshold rules, no regime model (no Markov/HMM/change-point):
1. `curve = curves._regime(d10, d2, d10 − d2)` with 20-observation changes of DGS10 and DGS2 (`core/ficc/curves.py:313-322`: slope move ≥ 5 bp → bull/bear steepener/flattener, tone from d10 if |d10| ≥ 5 bp else from (d10+d2)/2; else |d10| ≥ 5 bp → parallel up/down; else unchanged).
2. `risk_z = (z_1y[VIXCLS] + z_1y[BAMLH0A0HYM2]) / 2`; `> 0.75` risk-off; `< −0.5` risk-on; else neutral.
3. `usd_1m = chg_1m / (last − chg_1m)` of DTWEXBGS; `> 0.015` strong; `< −0.015` weak; else range.
4. `inflation = _trend(T10YIE.chg_1m, 10*BP)`; 5. `real_rates = _trend(DFII10.chg_1m, 15*BP)` (`stable` inside the band or when None).
`MacroSheet.as_of = max(row.last_date)`; `note` lists SYNTHETIC ids and a short-history warning. Explicit `source="fred"|"yfinance"` means "live providers, raise on failure" (FRED ids to FRED, Yahoo ids to Yahoo).

### A.6 `core/calendars.py` + `data/calendars/*.json`

Module (NOT a package). `DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "calendars"`; `STALE_WITHIN = timedelta(days=60)` (calendar days).
```python
SpecialSession(open: time|None, close: time|None, break_start: time|None = None, break_end: time|None = None)   # frozen
  .windows() -> tuple[tuple[time, time], ...]      # () if open/close missing; two windows only when both break fields set
MarketCalendar(market: str, timezone: str, source: dict, covers_from: date, covers_to: date,
               holidays: frozenset[str], special: dict[str, SpecialSession])                                  # frozen
  .covers(day) -> bool; .days_remaining(today) -> int; .describe_source() -> str
reload() -> None                       # drop the process cache
get(market) -> MarketCalendar|None     # key upper-cased
loaded_markets() -> tuple[str, ...]
is_trading_day(market, day: date) -> bool|None     # None = unknown market or outside coverage; weekend False; else not in holidays
special_session(market, day) -> SpecialSession|None
coverage(market) -> (date, date)|None
stale_markets(today=None, within=STALE_WITHIN) -> list[{"market","covers_to","days_remaining","expired"}]
summary() -> {"markets","holidays","special_sessions","stale"}
```
`_load()` (`:91-126`): `DATA_DIR.glob("*.json")` (non-recursive), skips `index.json`, lazily, thread-safe (`_LOCK` RLock, `_CACHE`); a file that fails to parse is silently skipped. Reads only `market`, `timezone`, `source`, `covers.{from,to}`, `holidays`, `special_sessions`; the JSON `regular` block is NOT read.

JSON structure (per market): `{"market", "timezone", "source": {"library": "exchange_calendars", "version": "4.13.2", "calendar": "XKRX", "generated": "2026-08-18"}, "covers": {"from","to"}, "regular": {"open","close","break_start","break_end"}, "holidays": ["YYYY-MM-DD", ...], "special_sessions": {"YYYY-MM-DD": {"open": "HH:MM", "close": "HH:MM"}}}`. `index.json`: `{"covers", "generated", "markets": {CODE: {"calendar", "covers", "holidays": n, "special_sessions": n}}}`; no code reads it.

Coverage (all start 2026-01-01): to 2027-12-31 for KRX (XKRX, 29 holidays, 2 special), US (XNYS, 20, 3), LSE, XETRA, EURONEXT_PA, EURONEXT_AS, BIT, BME, SIX, OMX_ST, OSE, TSE (XTKS), HKEX, TWSE, ASX, TSX, B3, BMV; to 2026-12-31 only for SSE, SZSE (both XSHG), SGX, NSE (XBOM). KRX special sessions: `2026-01-02` and `2027-01-04` open 10:00 close 15:30 only; no CSAT-day entry. US special sessions: 13:00 closes on 2026-11-27, 2026-12-24, 2027-11-26. `2026-10-05` and `2026-10-09` are KRX holidays (matches T-CLOSE-02's `NotASession` case).

No Fed, SIFMA, CBOE, CME, ECOS holiday set; no publication calendar; no event calendar; no history before 2026; no effective-dated session eras; no sign-off fields.

### A.7 `core/markets.py`

Constants: `KRX = "krx"`, `FMP = "fmp"` (PROVIDER ids, lowercase); `_WEEKDAYS = frozenset({0..4})`; `DEFAULT_HARD_AGE_S = 5*24*3600`; `_RT_MAX_AGE = 180.0`.
```python
Session(tz: str, windows: tuple[tuple[time, time], ...], days: frozenset[int] = _WEEKDAYS,
        max_age_open_s: float = 120.0, max_age_hard_s: float = DEFAULT_HARD_AGE_S)          # frozen
  .local(moment) -> datetime (zoneinfo, DST-aware); .is_open(moment) -> bool (weekly pattern only, no holidays)
  .session_start(moment) -> datetime|None; .previous_close(moment) -> datetime|None (ignores holidays); .describe(moment) -> str
Market(code, label, provider, suffix="", currency="", example="", session: Session|None = None, needs_intl_plan=False)   # frozen
  .local_date(moment); .windows_for(moment) -> windows (special session replaces the regular pattern)
  .trading_state(moment) -> (state, why)     # state in {"open","closed","unknown"}
  .is_open(moment) -> bool; .session_start(moment); .describe(moment)
```
`trading_state` reasons (verbatim): `"no session defined"`, `"weekend"`, `"exchange holiday (YYYY-MM-DD)"`, `"outside calendar coverage; using regular weekly hours"`, `"special session hours"`, `"regular session"`, `"outside today's special hours (YYYY-MM-DD)"`, `"outside trading hours"`.

Module API: `all_markets()`, `get(code)`, `codes()`, `options()`, `provider_for(code) -> str`, `session_for(code)`, `is_open(code, moment) -> bool|None`, `trading_state(code, moment)` (unknown code → `("unknown", "{code} is not a known venue")`), `provider_symbol(code, symbol)` (idempotent suffix), `currency_for`, `example_for`; `BY_CODE: dict[str, Market]`.

`_MARKETS` (code · tz · windows): `KRX` Asia/Seoul 09:00–15:30 (provider `krx`, max_age_open_s 120); `US` America/New_York 09:30–16:00; `LSE` 08:00–16:30; `XETRA`, `EURONEXT_PA`, `EURONEXT_AS`, `BIT`, `BME`, `SIX`, `OMX_ST` 09:00–17:30; `OSE` 09:00–16:20; `TSE` Asia/Tokyo 09:00–11:30, 12:30–15:30; `HKEX` 09:30–12:00, 13:00–16:00; `SSE`/`SZSE` Asia/Shanghai 09:30–11:30, 13:00–15:00; `TWSE` 09:00–13:30; `SGX` 09:00–12:00, 13:00–17:00; `NSE` 09:15–15:30; `ASX` 10:00–16:00; `TSX` 09:30–16:00; `B3` 10:00–18:00; `BMV` 08:30–15:00. All except KRX: provider `fmp`, `max_age_open_s = 180`; all except KRX and US: `needs_intl_plan=True`. `_with_overrides` applies `NEXTGEN_MAX_AGE_<CODE>` once at import.

### A.8 `data/krx/`

`__init__`: exports `Answer`, `KRXGateway`.

`kis_client.py` — errors `KISError(RuntimeError)`, `KISUnavailable(KISError)`. `_TOKEN_PATH = ~/.nextgen/kis_token.json` (`{"access_token","expires_at"}`; reused until 120 s before expiry). Pacing: `_MIN_GAP_S = 0.12`, `_pace()` under `_PACE_LOCK` (process-wide); `_RATE_LIMITED = "EGW00201"` → sleep 1.0 s and one more try (only when `retry=True`). `INDEX_CODES = {"KOSPI": "0001", "KOSDAQ": "1001", "KOSPI200": "2001"}`; `_MRKT_STOCK = "J"`, `_MRKT_INDEX = "U"`.
```python
Quote(ticker, name, price, change, change_pct, volume, market_cap, high, low, open: float|None,
      currency="KRW", as_of="", source="KIS")                                    # frozen
KISClient(*, base_url=None, timeout_s=None)        # .ready = kis_ready() and requests importable; no network in __init__
  .token() -> str                                   # POST {base}/oauth2/tokenP via plain requests (one attempt)
  ._get(path, tr_id, params, *, tr_cont="", retry=True) -> dict    # THE single GET choke point; sets self.last_headers; raises KISError
  .quote(code) -> Quote                             # /uapi/domestic-stock/v1/quotations/inquire-price  FHKST01010100; retry=False
  .daily(code, *, start=None, end=None, adjusted=True) -> list[{"date" ISO,"open","high","low","close","volume","source":"KIS"}]
                                                    # .../inquire-daily-itemchartprice FHKST03010100; YYYYMMDD; default last 150 calendar days; ~100 rows/call
  .index(name="KOSPI") -> {"market","level","change","change_pct","volume","as_of","source"}   # .../inquire-index-price FHPUP02100000
  .status() -> {"ready","reason"}
_f(value) -> float|None; _normalize(code)  ('005930', '005930.KS', 'A005930' -> '005930')
```
`Quote.as_of` and `index()["as_of"]` = `_now()` = RECEIPT time in UTC (`:246`, `:301`), not an exchange timestamp. `quote` price field `stck_prpr` (current price); `daily` close field `stck_clpr`; `FID_ORG_ADJ_PRC "0"` = adjusted (수정주가: splits and rights, not dividends).

`gateway.py` — `Answer(data, source, ok=True, reason="")` frozen, falsy when not ok. `KRXGateway()` holds `.kis`, `.dart`, `.krx`; `.status()`, `.any_ready`; `.quote(ticker) -> Answer[Quote]` (KIS first; fallback scans `krx.all_quotes("ALL")` for the ticker, source `"KRX"`); `.daily(ticker, *, start, end) -> Answer[list]` (KIS only); `.market_snapshot(market="ALL")`; `.indices()` (KIS KOSPI/KOSDAQ/KOSPI200 else KRX); `.filings(ticker, *, days=90, limit=50)`; `.financials(ticker, *, year=None, report="FY")`. Failure → `Answer([], "", ok=False, reason=...)`, never a fabricated value.

`krx_market_client.py` — `KRXError`. `_API_ENDPOINTS = {"KOSPI": "sto/stk_bydd_trd", "KOSDAQ": "sto/ksq_bydd_trd", "INDEX": "idx/krx_dd_trd"}` (header `AUTH_KEY`, param `basDd`, payload `OutBlock_1`). `KRXMarketClient(*, timeout_s=None)`: `.all_quotes(market="ALL", *, date=None) -> list[dict]` keys `ticker, name, market, close (TDD_CLSPRC), change, change_pct, open, high, low, volume, turnover, market_cap, shares, currency, as_of, source ("KRX Open API" | "KRX")`; `.indices(*, date=None)` keys `name, level (CLSPRC_IDX), change, change_pct, volume, as_of, source`; `.probe() -> {"ready","path": "open-api"|"keyless-csv"|"none","reason"}`; `.status()`. `[]` means unavailable. `date=None` → `datetime.now().strftime("%Y%m%d")` (machine-local date). `as_of` = receipt time. Keyless CSV path answers HTTP 403 (kept as fallback).

`opendart_client.py` — `DARTError`, `DARTUnavailable`. `_CACHE_PATH = ~/.nextgen/dart_corp_codes.json`, `_CACHE_TTL_S = 7*24*3600`. `REPORT_CODES = {"Q1": "11013", "H1": "11012", "Q3": "11014", "FY": "11011"}`. `_STATUS_TEXT` codes `010, 011, 013, 020, 100, 800` (`000` and `013` are not errors). `OpenDARTClient`: `.corp_codes(*, refresh=False) -> {ticker: {"corp_code","corp_name"}}`; `.resolve(ticker)`; `.filings(ticker, *, days=90, limit=50) -> list[{"date" (rcept_dt, YYYYMMDD, not ISO),"title","filer","corp_name","receipt_no","url","source"}]`; `.financials(ticker, *, year=None, report="FY") -> list[{"statement","account","this_term","prev_term","currency","source"}]` (amounts are STRINGS; `rcept_no` and any filing date are dropped); `.status()`.

### A.9 `data/kis_markets.py`

All calls go through `KISMarkets._get` → `self.client._get(path, tr_id, params[, tr_cont=])` (the `tr_cont` kwarg is passed only when non-empty, because test fakes define `_get(self, path, tr_id, params)`). Every path contains `/quotations/`. `MASTER_URL = "https://new.real.download.dws.co.kr/common/master/"`, `_MASTERS = ("fo_idx_code_mts","fo_com_code","bond_code","ffcode","frgn_code")` (keyless zip, decoded cp949, cached per process in `_MASTER_CACHE`).

Constants: `MKT_STOCK, MKT_INDEX, MKT_BOND = "J","U","B"`; `MKT_FUT, MKT_OPT, MKT_COMMODITY_FUT = "F","O","CF"`; `CHART_INDEX, CHART_FX, CHART_YIELD = "N","X","I"`; `KRW_YIELD_CODES` = `Y0104` KTB 1y, `Y0101` KTB 3y, `Y0105` KTB 5y, `Y0106` KTB 10y, `Y0116` KTB 20y, `Y0117` KTB 30y, `Y0112` CD 91d, `Y0114` Call 1d, `Y0102` Corp AA- 3y; `US_YIELD_CODES` = `Y0202` UST 10y, `Y0201` UST 30y, `Y0204` Fed funds; `KRW_CURVE_TENORS`; `FX_KRW_CODE = "FX@KRW"`; `INDEX_CODES = {"SPX": "S&P 500", ".DJI": "Dow Jones"}`; `OVERSEAS_EXCHANGES = ("NAS","NYS","AMS","HKS","TSE","SHS","SZS","HSX","HNX")`.

```python
Bars(symbol, dates: tuple[str,...] ISO asc, close: tuple[float,...], open=(), high=(), low=(), volume=(),
     source="KIS", note="", extra: dict = {})                    # frozen; .to_history(symbol=None) -> core.quant.history.History
OptionQuote(strike, last, bid, ask, iv (decimal), delta, gamma, vega, theta, open_interest, volume, theo, code="", atm="")   # .mid
OptionBoard(expiry_yyyymm, expiry_date ISO, calls, puts, as_of, source="KIS")
```
`_bars` drops rows whose close is missing or ≤ 0 and fills missing O/H/L/V with `0.0`. `_start(days) = date.today() − (int(days*1.6)+10)` days. `_page_back(fetch, *, days, list_key, date_key, max_pages=None)` pages backwards by end date.

| Method | Endpoint (under `/uapi/`) · tr_id | Returns |
|---|---|---|
| `etf_quote(code)` | `etfetn/v1/quotations/inquire-price` · FHPST02400000 | dict: `code, price, nav, premium_pct, tracking_error_pct, aum, cu_units, shares, lp_holding_pct, listed, target_index, dividend_cycle, type, as_of` (local date) |
| `etf_nav_daily(code, *, days=504)` | `etfetn/v1/quotations/nav-comparison-daily-trend` · FHPST02440200 | `Bars` + `extra["nav"]`, `extra["premium_pct"]` |
| `etf_components(code)` | `etfetn/v1/quotations/inquire-component-stock-price` · FHKST121600C0 (`FID_COND_SCR_DIV_CODE 11216`) | list `{code, name, price, weight_pct, cu_shares}` — the KODEX 200 basket (PDF) path; snapshot, no date field |
| `futures_market(code)` static | | `"F"` if product digits in (`01,05,06,07`) else `"CF"` |
| `futures_quote(code)` | `domestic-futureoption/v1/quotations/inquire-price` · FHMIF10000000 | dict incl. `price, basis, theo, premium_pct, open_interest, last_trade_date, days_left, underlying_level, as_of`; empty → `KISError` |
| `futures_daily(code, *, days=504)` | `.../inquire-daily-fuopchartprice` · FHKIF03020100 | `Bars` (close `futs_prpr`) |
| `continuous_futures(codes, *, days=504)` | (uses `futures_daily`) | ratio back-adjusted `Bars`, splice 5 sessions into the next contract |
| `futures_board(cls="MKI")` | `.../display-board-futures` · FHPIF05030200 | list of dicts |
| `option_expiries()` | `.../display-board-option-list` · FHPIO056104C0 | `["YYYYMM", ...]` |
| `kospi200_expiry(yyyymm)` static | | second Thursday (`date`), holidays ignored |
| `option_board(yyyymm)` | `.../display-board-callput` · FHPIF05030100 | `OptionBoard` (≤ 100 strikes/page, continuation header) |
| `option_chain(yyyymm, spot, *, width=0.10, step_pts=2.5, include_book=True, max_series=160)` | `.../inquire-price` + `.../inquire-asking-price` · FHMIF10010000 | `OptionBoard` |
| `last_session()` | via `index_daily("2001", days=12)` | ISO date of the last KOSPI200 row (today's date mid-session) |
| `index_daily(code="2001", *, days=504)` | `domestic-stock/v1/quotations/inquire-daily-indexchartprice` · FHKUP03500100 | `Bars("INDEX:{code}")`, close `bstp_nmix_prpr`; codes `0001` KOSPI, `1001` KOSDAQ, `2001` KOSPI200; 50 rows/call |
| `overseas_quote(excd, symb)` | `overseas-price/v1/quotations/price` · HHDFS00000300 | dict, note `"delayed unless a real-time entitlement exists"` |
| `overseas_daily(excd, symb, *, days=504, adjusted=True)` | `overseas-price/v1/quotations/dailyprice` · HHDFS76240000 | `Bars("{EXCD}:{SYMB}")`, price-return (`MODP=1` splits only) |
| `overseas_chart(market, code, *, days=504)` | `overseas-price/v1/quotations/inquire-daily-chartprice` · FHKST03030100 | `Bars("{market}:{code}")`; N indices, X FX fixing, I yields in PERCENT |
| `krw_yield_daily(code="Y0101", *, days=504)`, `usdkrw_daily(*, days=504)` | wrappers of `overseas_chart` | `Bars` |
| `krw_yields_snapshot()` | `domestic-stock/v1/quotations/comp-interest` · FHPST07020000 | list `{code, label, yield_pct, change_pct, tenor}` |
| `ovf_daily(srs_cd, exch_cd, *, days=504)` | `overseas-futureoption/v1/quotations/daily-ccnl` · HHDFC55020100 | `Bars("{SRS}@{EXCH}")`; CME ES/NQ/ZN/6E/GC/CL/SR3 answer HTTP 500 on a stock-account key |
| `ovf_contract_detail(codes)` | `.../search-contract-detail` · HHDFC55200000 | list of dicts (tick size/value, expiry, first notice) |
| `bond_quote(isin)`, `bond_daily(isin)`, `bond_info(isin)` | `domestic-bond/v1/quotations/{inquire-price · FHKBJ773400C0, inquire-daily-price · FHKBJ773404C0, search-bond-info · CTPF1114R}` | dict / `Bars` (price per 10,000 face) / raw dict |
| `investor_daily(code, *, days=60)` | `domestic-stock/v1/quotations/investor-trade-by-stock-daily` · FHPTJ04160001 | list `{date, close, volume, foreign_net_qty, foreign_reg_net_qty, individual_net_qty, institution_net_qty, raw}` (per STOCK, not market-wide) |
| `short_sale_daily(code, *, days=60)` | `domestic-stock/v1/quotations/daily-short-sale` · FHPST04830000 | list `{date, close, volume, short_qty, short_ratio_pct, short_cum_qty}` |
| `probe()` | one call per domain | `{name: {"ok","detail"}}`, never raises |

Module functions: `load_master(name) -> list[str]`; `_top_of_book(payload) -> (bid, ask)` (returns `(None, None)` when `aspr_acpt_hour` in `["154500","180000")`); `option_codes(yyyymm, product="KOSPI200")`; `index_futures_contracts(product="KOSPI200")`; `commodity_futures_contracts(keyword="3년국채")`; `front_contract(product="KOSPI200") -> str|None` (`_FRONT_KEYWORDS`: `KTB3, KTB5, KTB10, KTB30, USD, KOFR, GOLD`); `ktb_issues()`; `provider_status()`.

### A.10 `data/fmp/quote_client.py`

`BASE_URL`, `FMPError`, `FMPPlanError(FMPError)` (HTTP 402, permanent per symbol). `FMPQuote(symbol, name, price, change, change_pct, volume, market_cap, high, low, open, previous_close, exchange="", as_of="", source="FMP")` frozen; `as_of` = provider `timestamp` (unix s → ISO UTC; `""` when absent — the feed then treats the quote as missing). `FMPQuoteClient(*, api_key=None, base_url=None, timeout_s=None, min_interval_s=None, clock=time.monotonic)`: `.ready`, `.status()`, `.quotes(symbols) -> dict[UPPER, FMPQuote]` (one GET `/quote?symbol=` per symbol; in-memory throttle `min_interval_s` = 20 s; plan-blocked symbols skipped; raises `FMPError` only when nothing came back and there were errors), `.quote(symbol)`, `.error_for(symbol)`, `.plan_blocked()`. `_redact(text, key)` masks the key and `apikey=...`.

### A.11 `data/crypto/crypto_client.py`

Hosts: `UPBIT`, `BINANCE_SPOT` (data host first, main second), `BINANCE_FAPI`, `COINGECKO`. `_MIN_GAP_S = 0.12` (`_throttle`, not lock-protected). `CryptoError`. `_get(url, params=None, headers=None, *, label)` is the single transport (tests replace it).
```python
Candles(symbol, dates, close, open=(), high=(), low=(), volume=(), quote_volume=(), source="", note="")   # .to_history()
FundingSeries(symbol, times, rates, source="BINANCE")                                                     # .daily() -> {UTC date: sum}
UpbitPublic().daily(market="KRW-BTC", *, days=504) -> Candles     # date = candle_date_time_utc[:10]; 200/call
UpbitPublic().ticker(markets) -> list[dict]
BinancePublic().daily(symbol="BTCUSDT", *, days=504, interval="1d", market="spot") -> Candles   # close = kline col 4, date = open time UTC
BinancePublic().funding(symbol, *, days=730) -> FundingSeries; .premium_index(symbol) -> dict; .open_interest_hist(symbol, *, period="1d", limit=30) -> list
coingecko_top(n=20) -> list[dict]
upbit_jwt(access_key, secret_key, query="") -> str;  UpbitAccount().balances() -> list[dict]      # GET /v1/accounts only
provider_status() -> list[dict];  probe() -> dict
```
The newest daily candle/kline of both venues is the bar still in progress.

### A.12 `core/quant/history.py` (context; shares the cache)

`TRADING_DAYS = 252` (second definition), `HistoryError`, `History(symbol, source, dates, closes, note="", adjustment="")` frozen (`adjustment ∈ {"total","split",""}`; `.last`, `.prices()`, `.log_returns()`, `.simple_returns()`), `convention_warning(hists) -> str`, `fmp_history`, `kis_history`, `synthetic_history`, `yf_history` (imports `core.ficc.data._yf_fetch`, `_period_for` at CALL time), `crypto_history`, `kis_market_history`, `_looks_krx/_looks_yahoo/_looks_crypto/_looks_kis_market`, `_cached` (§0.2), `SOURCES = ("auto","fmp","kis","yfinance","crypto","synthetic")`, `load_history(symbol, *, source="auto", days=504) -> History`. `auto` routing: 6-digit KRX → KIS (SYNTHETIC with note when no KIS key); crypto shapes → Upbit/Binance; Yahoo shapes (`^`, `=F`, `=X`, `-USD`, `-KRW`, `.KS`, `.KQ`) → Yahoo; KIS-market shapes → KIS; else FMP; no FMP key → SYNTHETIC with `"FMP_API_KEY is not configured; "` prefix. A configured provider that fails raises `HistoryError`.

---

## B. Cross-file flows, persistence, env

Call graph (→ = calls):
- UI `macro_page` → `macro.macro_sheet` → `data.load_many` → `_provider_rows` → `_cache_get` / `_fred_fetch` | `_yf_fetch` → `_cache_put`.
- UI `rates/bonds/structuring/fx/crypto/quant_lab` pages → `data.load_treasury_curve`, `load_short_rate`, `load_fx_spot`, `load_policy_rates`, `load_series`; `core/ficc/ratesim.py:341`, `curves`, `fx`, `fx_styles`, `curve_models` (`curve_models.py:245` → `KISMarkets`, `KRW_CURVE_TENORS`).
- UI `quant_lab/portfolio/signals/strategy_lab/etf` → `history.load_history` → `_cached` → `fmp_history` (data.net session) | `kis_history` → `KISClient.daily` | `yf_history` → `data._yf_fetch` | `crypto_history` → `UpbitPublic/BinancePublic` | `kis_market_history` → `KISMarkets`. `history._may_be_trading` → `markets.is_open` → `Market.trading_state` → `calendars.is_trading_day` / `special_session`.
- Engine: `runtime.tick` → `markets.is_open(rule.market, now) is not False` filter → `QuoteFeed.fetch_many` → `markets.provider_for`: `krx` → `KRXGateway.quote` (KIS `quote` retry=False → fallback `KRXMarketClient.all_quotes`); `fmp` → `FMPQuoteClient.quotes(provider_symbol)` → `Evaluator.evaluate` → `Market.trading_state`, `Market.session_start`, `Session.max_age_open_s`, `Session.max_age_hard_s`. `runtime.status()["calendar_stale"] = calendars.stale_markets()`. `ui/trading_page.py:383` prints "Regenerate with pkg_tools/generate_calendars.py."
- UI `krx_page` → `KRXGateway`; `settings_page` → `KRXMarketClient.probe`, `data.probe`, `KISMarkets.probe`, `crypto_client.probe`, `config.*_provider_status`; `derivatives_page`/`etf_page` → `KISMarkets`.
- Import direction: `data/*` never imports `core/*` at module import (only lazily: `Bars.to_history`, `Candles.to_history` → `core.quant.history.History`); `core.markets` imports `core.calendars`; `core.quant.history` imports `core.markets` and lazily `core.ficc.data`, `data.*`.

Persistence (all under the user's home unless overridden):

| Path | Writer | Content |
|---|---|---|
| `~/.nextgen/ficc_cache/{PROVIDER}_{id}_{days}.json` | `core.ficc.data._cache_put` | `{"ts","rows"}` |
| `~/.nextgen/ficc_cache/HIST_{provider}_{SYMBOL}_{days}.json` | `core.quant.history._cached` | `{"ts","live","symbol","source","note","adjustment","dates","closes"}` |
| `~/.nextgen/kis_token.json` | `KISClient._store_token` | bearer token + expiry (secret; do not read or copy) |
| `~/.nextgen/dart_corp_codes.json` | `OpenDARTClient._store_cache` | `{"fetched_at","entries"}`, 7-day TTL |
| `~/.nextgen/trading/` (`rules.json`, `engine.json`) | `core/rules/store.py:135`, `core/engine/runtime.py:79` | rules store, engine state |
| `~/.nextgen/runs/<run_id>/` | `core/skills/runner.py`, `runs.py` | skill run artifacts |
| `~/.nextgen/policy_events.jsonl`, `prefs.json` | no writer found in the current tree | pre-existing files |
| `data/calendars/*.json` (in repo) | offline generator (not in the tree) | holiday data |
| `qa/acceptance_results.json` (in repo) | `tests/run_all.py` | last suite result |
| `docs/asset_expansion/cache/*.csv` (in repo) | `docs/asset_expansion_study.py::_cached` | research price cache, 46 files, written 2026-09-25 ≈16:30Z |

Cache files are written with `Path.write_text(..., "utf-8")` (not atomic, no lock); a torn read is swallowed and treated as a miss.

---

## C. Existing tests for this subsystem and how tests are registered

Registration: no pytest. `tests/run_all.py` imports `tests()` from six modules and prefixes names (`cockpit/`, `engine/`, `ui/`, `quant/`, `ficc/`, `expansion/`). Each module exposes `tests() -> list[(name, zero-arg callable)]`; a test fails by raising. Four modules auto-collect `test_*` globals (sorted); `expansion_acceptance.tests()` is an explicit list and also runs module `__main__` self-checks through `_selfcheck(rel)` (`runpy.run_path(..., run_name="__main__")`). Runner forces UTF-8 on stdout/stderr, writes `qa/acceptance_results.json`, exits 1 on any failure. A new suite = new `tests/<x>_acceptance.py` with `tests()`, one import and one line in `run_all.tests()`. Hermetic helpers to reuse: `ficc_acceptance._no_network()` (patches `data._fred_fetch`, `data._yf_fetch`, sets `config.FICC_CACHE_TTL_SECONDS = 0.0`), `quant_acceptance._no_credentials()` (patches `config.fmp_ready`, `fmp_key`, `kis_ready`, `anthropic_key`), fake transports `_FakeKIS` and `crypto_client._get` replacement, `tempfile.mkdtemp()` + `os.environ["NEXTGEN_FICC_CACHE"]`.

| File · test | Asserts |
|---|---|
| ficc · `test_data_synthetic_is_deterministic_and_labeled` | same id → same values; `source == "SYNTHETIC"` and non-empty note; `EURUSD` ≡ `EUR/USD` |
| ficc · `test_data_synthetic_never_touches_the_cache` | `set(data._MEM)` unchanged after synthetic loads with TTL 3600 |
| ficc · `test_data_auto_degrades_to_synthetic_naming_the_provider` | offline `auto` → SYNTHETIC, note contains `"FRED failed"` / `"YFINANCE failed"` and `"offline"`; label `"USD/KRW"` |
| ficc · `test_data_explicit_provider_raises_offline` | explicit `fred` / `yfinance` / unknown source raise `FICCError`; `probe()` both `ok False` |
| ficc · `test_data_shapes_are_clean` | panel `(200, 11)` NaN-free; `"monthly"` in KRW short-rate note, `"daily"` in USD; `change`, `window` |
| ficc · `test_macro_rows_are_bounded_and_regimes_are_from_the_sets` | `len(rows) == len(INDICATORS)`, `sources == {"SYNTHETIC": 18}`, `-6 <= z_1y <= 6`, `0 <= pct_1y <= 1`, `chg_3m is not None`, `last_date == as_of`, regimes in the four tuples, `"SYNTHETIC" in note`, `row("nope") is None` |
| ficc · `test_macro_briefs_are_json_payloads` | 5 `movers_z`, 18 `weekly_changes`, `json.dumps` works |
| ficc · `test_macro_sheet_offline_auto_is_loudly_synthetic_and_fred_raises` | `"18/18"` in note; `source="fred"` raises; `days=10` → `ValueError` |
| quant · `test_history_cache_serves_a_rerun_without_asking_the_provider_again` | cache B end to end: rerun from disk, `"cached"` in note, `adjustment` round-trips, `days` is part of the key, TTL 0 off, live TTL (`_CACHE_LIVE_TTL` 0 vs 600), legacy file without `live` refetched after 900 s, `"live": false` served, refetch once the market traded since, missing key must raise despite a cached file; file name `HIST_FMP_TSLA_120.json` |
| quant · `test_the_cache_knows_when_a_market_may_be_trading` | `_may_be_trading` truth table: KRX 11:00 KST true, 20:00 KST false, 15:45 KST true; `A01612` / `FX@KRW` true on a weekday evening; US session true, Thanksgiving 2026-11-26 false; crypto Saturday true; `^VIX` Saturday false; `ZN=F` Sunday 23:00 UTC true |
| quant · `test_each_loader_states_its_return_convention` | `kis_history` `"split"`, `yf_history("005930.KS")` `"total"`, `^VIX` `""`; patches `ficc._yf_fetch`, `kis.KISClient`, `config.kis_ready` |
| quant · `test_fmp_history_asks_for_dividend_adjusted_closes_and_reports_refusals_honestly` | endpoint suffix, adjClose handling, key never echoed, 429 raises |
| quant · `test_auto_routing_falls_back_to_labeled_synthetic`, `test_explicit_provider_without_key_raises_not_simulates`, `test_load_history_rejects_blank_and_unknown_source`, `test_synthetic_is_deterministic_per_symbol` | routing/degradation contract of `load_history` |
| engine · `test_40`, `test_41`, `test_58`, `test_59` | every `markets.codes()` routes to `krx` or `fmp`; suffix idempotent; every market has a session with windows and `max_age_open_s < max_age_hard_s`; US session DST (`EDT`/`EST`) |
| engine · `test_51`–`test_57`, `test_60`–`test_62`, `test_65`, `test_66`, `test_76` | venue-aware freshness: closed → SKIPPED (reason contains `"closed"`), frozen feed in session → HALTED, no print today → SKIPPED (`"before today"`), dead feed → HALTED, TSE lunch → SKIPPED, weekend, unknown market → global bound (`"limit 60s"`), closed venues not fetched |
| engine · `test_67`–`test_70` | Thanksgiving reason contains `"holiday"`; Seollal 2026-02-17 KRX closed/holiday; 2026-11-27 US open at 11:00 ET, closed 13:30 ET, window end `"13:00"` |
| engine · `test_71`–`test_75` | beyond coverage → `is_trading_day is None`; every `markets.codes()` has calendar data; no calendar `expired`; EVERY loaded calendar has `source.library == "exchange_calendars"` plus `calendar` and `generated`; 20k `is_trading_day` lookups < 1 s |
| engine · `test_46`–`test_50` | FMP quote without timestamp is missing data; key redaction; per-symbol throttle; plan-blocked not retried; `FMP_MIN_INTERVAL_SECONDS < QUOTE_MAX_AGE_SECONDS` |
| engine · `test_81`, `test_82`, `test_89` | which modules use `data.net.session` vs plain requests (see A.2); retry is real against a local HTTP server and logs no key; KIS pacing `_MIN_GAP_S`, one retry on `EGW00201`, none with `retry=False` |
| cockpit · `test_08`, `test_09` | raw text of every `core/`, `data/`, `ui/` `.py` + `main.py` + `config.py` must not contain (case-insensitive) `order_cash, order-cash, place_order, submit_order, TTTC0802U, TTTC0801U, VTTC0802U`, nor (case-sensitive) `KIS_ACCOUNT`, `CANO`, `ACNT_PRDT_CD` |
| cockpit · `test_13`, `test_16`, `test_17` | settings page never calls `kis_credentials()` / `opendart_key()` / `_clean(`; every runtime file is UTF-8; `acceptance.py` / `run_all.py` never call `read_text()` without an encoding |
| cockpit · `test_21`, `test_22` | `KRXGateway().daily/.filings` failures carry a reason; providers == `{"KIS","OpenDART","KRX"}` |
| expansion · `kis_markets_paging_and_shapes`, `kis_markets_unavailable_without_keys`, `kis_master_parsers`, `crypto_client_refusals_and_router`, `history_auto_degrades_without_keys`, `selfcheck_kis_markets`, `selfcheck_crypto_client` | paging counts, `CF` market code, option board parsing (`iv 0.185`, expiry `2026-10-08`), yields symbol `"I:Y0101"`, `KISUnavailable` without keys, crypto source text must not contain `/v1/orders, /v1/withdraws, /api/v3/order, private_key, seed_phrase, import ccxt, import web3`, Upbit/Binance parsing with TTL 0 |
| ui · `flet_api_guard` (4) | static scan of `ui/*.py` only: `page.<method>` exists, kwargs of listed `ft.*` controls exist, attribute assignments exist, palette tokens exist |

Not covered anywhere: cache A read/write behaviour (TTL, key, stamping); `KRXMarketClient` parsing; `OpenDARTClient`; `KISClient.daily/index` parsing; `load_treasury_curve` forward-fill; anything about value status, availability, publication timing or staleness.

---

## D. Extension points for v2

### D.1 Where the SPEC functions land, and what already exists

| SPEC item (lines) | Natural home | Reuse (do not duplicate) | Missing today |
|---|---|---|---|
| `PITValue`, `MissingInput`, `pit_value`, `pit_last`, `data_snapshot_id`, `RunContext` (961-1021; TASK-M1-07/10) | new sibling module beside `core/ficc/data.py`, re-exported from `core.ficc.data` if the spec name `core.ficc.data.pit_value` must resolve | `FICCError`; `config.ficc_cache_dir()` pattern for a new store dir; `Series`/`History` stay as UI shapes (adapter from store rows) | append-only store, per-row `retrieved_at_utc`, `value_status`, `session_date`, `content_hash`, `fetch_log.jsonl` |
| read-through cache rule (1283; TASK-M1-12) | `data._cache_get/_cache_put` and `history._cached` | both already funnel every loader; `history._may_be_trading`/`markets.is_open` for a display-only "live" label | calendar lookup `close_print_bound_utc`; row-level stamp |
| series registry + `contracts.yaml`, `contract`, `expected_available_utc`, `is_stale`, `on_input_failure`, `usable_cross_market` (1386-1402, 1821-1827; TASK-M1-08/09/16/17/18) | data files next to `core/ficc/data.py`; functions in the new sibling module | `macro.INDICATORS` (18 context rows), `_SHORT_RATE_IDS`, `_TREASURY_IDS`, `KRW_YIELD_CODES`, `US_YIELD_CODES`, `INDEX_CODES` as the seed of the registry; pyyaml is already a dependency | roles, bindings, publication schedules, ranges, groups |
| `decision_time_utc`, `close_print_bound_utc`, `is_session`, `session`, `fed_business_day`, `sifma_status`, `nyse_holiday`, `publication_instant`, `next_expected_obs`, `add_publication_bdays`, `usable_at`, `regime_tags`, `gap_sessions` (1023-1041, 1989-1996; TASK-M1-03..06) | `core/calendars` | for 2026-01-01 … 2027-12-31: `calendars.is_trading_day`, `special_session`, `Market.windows_for`, `Session.local` (zoneinfo DST) already give session yes/no, early closes (US 13:00) and the 10:00 first-day open; `stale_markets` for the coverage alert | everything before 2026; KRX eras (15:00 close to 2016-07-31, CSAT 10:00–16:30, Saturday sessions before 1998-12-12, random end); Fed/SIFMA/CBOE/CME/ECOS sets; print bounds; sign-off; `NotASession`; regime tags; source-skipped list |
| event calendar (R-10, §6.3) | `core/calendars` | none (no event store exists; the release-calendar skills are external subprocess skills) | all |
| official close primary + reconciliation (TASK-M1-11) | `core/quant/history` + store | `KISClient.daily` (`stck_clpr`, market `J`), `KISMarkets.index_daily` (`bstp_nmix_prpr`, market `U`, codes `0001`/`2001`), `KRXMarketClient.all_quotes`/`indices` (`TDD_CLSPRC`, `CLSPRC_IDX`), `yf_history` as the secondary | status stamping; which KIS field/division is the KRX regular-session close is UNVERIFIED (SPEC 1496, QF1-A25) |
| KIS read-only allowlist (TASK-M1-02) | top of `KISClient._get` (every KIS GET, including all of `KISMarkets`, passes through it) + `token()` | the 24 quotation paths listed in A.8/A.9, all containing `/quotations/`; `load_master` uses a different host | allowlist constant in `config.py` |
| new providers ECOS, Treasury par yields, ALFRED (TASK-M1-21) | new client modules under `data/`, called from `core.ficc.data` | `data.net.session` (retry policy), `config._clean`, the `*_provider_status()` pattern, `probe()` pattern | keys/env vars, endpoints; must be added to the hermetic patch list |
| macro builders `build_macro_state`, `build_overlay_decisions`, `build_context_log`, `log_break` (1072-1076) | `core/ficc/macro.py` | `MacroSheet`/`MacroRow` as the context-item source; `daily_brief` gains a section | builders, schemas |
| macro artifact dir (SPEC 4126) | `config.py`, same shape as `trading_dir()` | `_clean`, `Path.home()/".nextgen"/...` convention | function + env var name (owner/coordinator choice) |
| tech-fund DATA-4 (R3 153-158): OpenDART usable from the close of `rcept_dt` + 1 session, first-filed values | `OpenDARTClient` + store | `filings()` gives `date` (= `rcept_dt`, date-only) and `receipt_no` | `financials()` drops `rcept_no`/filing date, so statements cannot be made point-in-time without changing its return rows |
| tech-fund DATA-5 regime flags (R3 160-165) | same data file as SPEC `regime_tags` (`kr_regime_tags.yaml`) | exact ban dates are in R3 162: 2008-10-01..2009-05-31, 2011-08-11..11-09, 2020-03-16..2021-05-02 (index stocks only to 2023-11-05), 2023-11-06..2025-03-30; sell tax 0.18% (2024), 0.15% (2025), 0.20% (2026) | file |

What each fetcher can honestly stamp today (input to `value_status` / `available_at_source`):

| Fetcher | Value | Time information returned | v2 consequence |
|---|---|---|---|
| `KISClient.quote` | `stck_prpr` | receipt time only | `live_snapshot`, `obs_kind = quote_snapshot`; never a close |
| `KISClient.daily`, `KISMarkets.index_daily` | `stck_clpr` / `bstp_nmix_prpr` per `stck_bsop_date` | none | `official_close` only when retrieved ≥ `close_print_bound_utc` + 10 min, `available_at_source = calendar_bound`; today's row before that is `provisional_intraday` |
| `KRXMarketClient.all_quotes/indices` | `TDD_CLSPRC` / `CLSPRC_IDX` per `basDd` | receipt time | same rule; publication lag of the Open API is unmeasured |
| `data._yf_fetch`, `yf_history` | adjusted close per date | none | `vendor_close` if retrieved after close + 10 min, else `provisional_intraday`; adjusted history is restated by the vendor |
| `data._fred_fetch` | value per observation date, raw units | none (no `realtime_start`, no `last_updated`) | `calendar_bound` from the publication rule; vintages need another endpoint |
| `FMPQuoteClient` | `price` | provider `timestamp` (last trade) | `live_snapshot` |
| `fmp_history` | `adjClose` per date | none | `vendor_close` / provisional by retrieval time |
| Upbit / Binance daily | close per UTC date | none (Binance kline close time ignored) | newest bar is in progress until 00:00:00Z of d+1 (SPEC 1291) |

### D.2 Naming collisions and identifier mismatches

- Market ids: SPEC uses `KR, US, JP, CN, HK, TW, CRYPTO, FX` (SPEC 1036-1037) and holiday sets `KRX, NYSE, FED, SIFMA, CBOE, CME, JPX, SSE, HKEX, TWSE, ECOS` (2074). Existing keys: `markets.BY_CODE` / calendar files use `KRX, US, TSE, SSE, SZSE, HKEX, TWSE, ...`. `"US"` is both the existing venue code (calendar XNYS) and a SPEC market id; `"KR"` → `markets.get("KR")` is `None` and `trading_state("KR", ...)` returns `("unknown", "KR is not a known venue")`. A mapping `{KR: KRX, US: US (NYSE), JP: TSE (JPX), CN: SSE, HK: HKEX, TW: TWSE}` is required in exactly one place.
- `markets.KRX = "krx"` / `markets.FMP = "fmp"` are provider ids, not venues.
- `Session`: `core.markets.Session` (tz, windows, freshness bounds) vs SPEC `session(market, date) -> Session` (open, close, closing call, special flags; 1993). `core.calendars.SpecialSession` is a third shape.
- `is_trading_day` (returns `None` outside coverage) vs SPEC `is_session` (must fail closed as OPS HALT `reason = calendar_coverage`, never a silent `NotASession`; 2090).
- `calendars.get`, `calendars.coverage`, `calendars.summary`, `calendars.reload`, `markets.get`, `markets.is_open`, `markets.trading_state` are taken names.
- `core.ficc.macro.Regime`, `CURVE_REGIMES`, `RISK_REGIMES` vs SPEC `regime_tags` (market-structure tags) and P19 (SPEC 1124-1126: the existing read is rule-based, so it may stay only as a descriptive summary, "never presented as a regime state", never feeding signals/risk/engine, and never reusing calm/normal/elevated/stressed).
- `probe` exists in `core.ficc.data`, `KISMarkets`, `KRXMarketClient`, `crypto_client`; `provider_status` in `kis_markets`, `crypto_client`, `config`.
- `INDEX_CODES` is defined twice with different content (`kis_client`: KOSPI/KOSDAQ/KOSPI200; `kis_markets`: SPX/.DJI). `_f`, `_now` are redefined per client. `TRADING_DAYS` twice.
- `SOURCES` differs between `core.ficc.data` and `core.quant.history`.
- pyproject `version = "2.0.0"` already; "v2.0" of the SPEC is not the package version.
- SPEC series ids that do not exist as loader ids: `KOSPI_OFFICIAL_CLOSE`, `SPX_OFFICIAL_CLOSE`, `US10Y_KIS_QUOTE`, `USD_LIVE_PROXY`, `ECOS_1530_CLOSE`, `USDKRW_1530_SNAPSHOT`, `BOK_CALL_RATE`, `US_RF`, `KODEX200_PDF`, group ids. `data._route` would send any bare alphanumeric id (e.g. an ECOS code) to FRED: registry-driven routing is needed for them.

### D.3 Constraints

- Frozen dataclasses everywhere (`Series`, `CurvePanel`, `MacroRow`, `MacroSheet`, `Market`, `Session`, `MarketCalendar`, `Quote`, `Bars`, `Candles`, `History`); modify with `dataclasses.replace`. Adding a field with a default at the END is backward compatible; positional construction is used in tests and code (`History(h.symbol, h.source, h.dates, h.closes, note=...)`, `Series("DGS10", "x", "FRED", dates, values)`), so never insert a field before existing ones.
- `core/ficc/data.py` is a module whose private attributes are an interface: tests and `history.yf_history` use `data._fred_fetch`, `data._yf_fetch`, `data._MEM`, `data._period_for`, patched by attribute assignment and looked up at call time. If it becomes a package, these must stay module-level attributes of `core.ficc.data` resolved at call time, or the hermetic patch silently stops working.
- `core/calendars.py` is a module; the SPEC config keys name `core/calendars/data/source_skipped.yaml` (1902) and `core/calendars/data/kr_regime_tags.yaml` (2075). A directory `core/calendars/` cannot coexist with `core/calendars.py` as importable siblings (the package wins). Converting requires moving the code to `core/calendars/__init__.py` and changing `DATA_DIR` from `parents[1]` to `parents[2]`.
- Any `*.json` dropped directly into `data/calendars/` with a `market` key is loaded as a `MarketCalendar` and must satisfy engine `test_74` (`source.library == "exchange_calendars"`). SPEC R-20 says `exchange_calendars` XKRX is "a cross-check only, never the source" (2003). Signed v2 calendar files therefore go into a subdirectory (the glob is non-recursive) or use YAML.
- `macro.INDICATORS` length 18 and `sources == {"SYNTHETIC": 18}` are asserted in two test files and the module self-check; new context series belong in the registry, not appended there (or the tests are changed on purpose).
- Degradation contract is tested and must survive for display paths: explicit provider raises, `auto` degrades to labelled SYNTHETIC. SPEC forbids it for acting inputs (`MissingInput("synthetic_rejected")`, T-SYN-01): enforce in `pit_value`, not by changing the loaders.
- New network touchpoints must be patchable the same way and added to `_no_network()`; HTTP through `data.net.session` (GET-only retry). Engine `test_81` pins which existing modules use which transport.
- Cockpit `test_08`/`test_09` scan raw source text including comments and docstrings of everything under `core/`, `data/`, `ui/`: the forbidden tokens of the SPEC's static read-only scan (T-RO-01) must be listed in `tests/` only. The uppercase substring `CANO` is forbidden anywhere in runtime source (e.g. an uppercase constant containing "CANONICAL" fails `test_09`).
- Files are read/written with an explicit `"utf-8"`; console output needs the runner's UTF-8 reconfigure (see E).
- Flet 0.85 API guard applies to `ui/*.py` only; nothing in this subsystem imports Flet.
- Read-only: no order/cancel/account path exists in any client here; `UpbitAccount.balances` is the only authenticated account read.

---

## E. Gotchas

1. Cache A has no live/close awareness and no hit marker (§0.1); cache B's fix is cache-lifetime only (§0.2). Neither `Series` nor `History` can express "provisional".
2. Cache keys include `days`: the same series is stored several times (`FRED_DFF_504`, `_756`, `_6000`) with different retrieval times, so two pages can show different "last" values. Stored rows are not truncated to `days` (`FRED_DGS10_504.json` holds 557 rows).
3. `_MEM` is process-global and only expires by TTL; a test asserts on its key set.
4. `KISClient.quote().as_of` and `index()["as_of"]` are receipt times, so the engine's freshness test always sees a KIS quote as fresh; SPEC 1496 lists exactly this as an open question (QF1-A25).
5. `kis_client.py` docstring says "exactly four read-only quotation endpoints" (incl. `inquire-ccnl`); three are implemented (`quote`, `daily`, `index`).
6. Naive local clock in dates: `date.today()` / `datetime.now()` in `data._business_dates`, `_month_dates`, `_start_for`, `history.fmp_history`, `kis_history`, `synthetic_history`, `KISClient.daily`, every `KISMarkets` method (`_start`, `as_of`), `KRXMarketClient._session_date`, `OpenDARTClient.filings`. Correct only while the machine runs in KST; SPEC requires UTC storage and no "now" default (1273, 1002).
7. Windows/cp949: default stdout and `open()` encoding are cp949 on this machine; a plain `print` of an en dash raised `UnicodeEncodeError` during this mapping. `tests/run_all.py` reconfigures stdout; any new script (study, fixture builder, skill) must do the same or set `PYTHONUTF8=1` (`config.skill_env()` already does for skill subprocesses). KIS master files are cp949; the KRX CSV is tried as `euc-kr`, `cp949`, `utf-8-sig`. Korean literals live in source (`"3년국채"`, CSV headers).
8. The helper `prep/readlines.py` in the scratchpad has a literal newline inside a string literal and does not run (SyntaxError); a corrected copy is needed to print long spec lines.
9. README is stale: "229 checks" / "245 checks" (README 347, 379) vs 266 actual; "Python 3.10+" vs 3.13.14 in use.
10. `pkg_tools/generate_calendars.py` is referenced by `core/calendars.py:4`, `requirements-dev.txt` and `ui/trading_page.py:383` but is not in the tree, so the shipped calendars cannot be regenerated from this checkout.
11. Calendar coverage: SSE, SZSE, SGX, NSE end 2026-12-31 → listed by `stale_markets()` from 2026-11-01 and `expired` from 2027-01-01, at which point engine `test_73` fails. Every calendar starts 2026-01-01: `is_trading_day("KRX", date(2025, 11, 13))` is `None`, so no SPEC golden date before 2026 can be answered (T-CLOSE-02 needs 2015, 2016, 2025).
12. `KRX.json` has no CSAT session (only the two first-trading-day 10:00 opens); `markets` hard-codes 09:00–15:30. On a CSAT day the engine would treat 09:00–10:00 as open and 15:30–16:30 as closed.
13. The JSON `regular` block is ignored by code and can disagree with `core/markets.py` (SGX: JSON says no break, `markets.py` has 12:00–13:00). `SZSE` is generated from `XSHG`.
14. A special session without break fields replaces a two-window lunch pattern by one continuous window (`SpecialSession.windows`).
15. `Session.is_open` and `Session.previous_close` ignore holidays; only `Market.*` methods are calendar-aware.
16. `stale_markets` counts calendar days (60), SPEC coverage counts sessions (60 warn / 20 page; 2077).
17. Units are not uniform: `load_series` returns raw FRED percent; `load_short_rate` and `load_treasury_curve` return decimals; `macro._row` rescales only when `s.source == "FRED"` and unit is `pct`/`bp`; `KISMarkets.krw_yield_daily` / `krw_yields_snapshot` return PERCENT; `OptionQuote.iv` is decimal. A registry `unit` field is the only safe place to settle this.
18. Positional arithmetic: `Series.change(n)` and `macro._CHANGES` count observations; monthly FRED series are returned as-is. SPEC 1352 forbids positional shifts for derived monthly values (CPI YoY 3.35% vs 3.71%).
19. `load_treasury_curve` forward-fills each tenor column silently (`data.py:544-548`); SPEC 1496 names silent forward-fill as a failure mode.
20. `MacroSheet.as_of = max(last_date)` hides that rows have different last dates (weekly H.10 series, credit OAS lag); there is no staleness label per row.
21. Yahoo FX series contain weekend-dated rows; only `macro._weekdays` removes them, `load_fx_spot` does not.
22. `yfinance` `auto_adjust=True`: stock/ETF history is restated on every distribution, so an append-only store sees old dates change content; index, FX and futures series are unaffected.
23. `_bars` / `Candles` fill missing open/high/low/volume with `0.0`; a zero is "missing", not a price (matters for range estimators, R-30). `_bars` silently drops rows with close ≤ 0.
24. `KISMarkets.continuous_futures` is a ratio back-adjusted splice; SPEC 1378 forbids continuous-futures returns across rolls for books (fixed roll calendar). `kospi200_expiry` ignores holidays.
25. `KRXGateway.quote` fallback downloads the whole market to find one ticker (engine path, plain `requests`, timeout ≥ 30 s). `KRXMarketClient.all_quotes()` with today's date returns `[]` until KRX publishes the session.
26. `cockpit/test_21` calls `KRXGateway().daily("005930")` and `.filings("005930")` without patching credentials: with keys configured it can reach KIS and OpenDART (1.97 s in the last run). `cockpit/test_19` runs a real skill subprocess and writes under `config.runs_dir()`. Both matter for the SPEC's T-HERM-01/02.
27. `quant_lab_page.py:74-78` loads the risk-free rate with `source="auto"`: it can be SYNTHETIC (labelled in `note` only).
28. `_cache_key` sanitisation can collide in principle (`^VIX` and `_VIX`); `HIST_` prefix separates cache B from cache A in the same directory.
29. `OpenDARTClient.filings()["date"]` is `YYYYMMDD` while every other client returns ISO dates.
30. `NEXTGEN_MAX_AGE_<MARKET>` is read once at import of `core.markets`; changing it needs a restart.
31. `KISMarkets._more_pages` reads `client.last_headers`, an instance attribute overwritten by every call: not safe if one `KISClient` is shared across threads. `crypto_client._throttle` has no lock.
32. Local research CSVs (`docs/asset_expansion/cache`): written 2026-09-25 ≈16:30Z (US session open, crypto bar open), so the last rows of US and crypto files are mid-session prints; `yf__KS200.csv` holds one row; there is no `^KS11` (KOSPI) history file. They do not satisfy the post-close fixture rule (SPEC 1493 item 5) as they stand.

---

## Ambiguities (source silent or contradictory) and the conservative reading

| # | Issue | Lines | Conservative reading |
|---|---|---|---|
| 1 | SPEC says PIT functions live "inside the existing package" `core/ficc/data`, which is a single module with patched private attributes | SPEC 906, 966; `data.py` whole | Keep `core/ficc/data.py` importable with the same attributes; add the store beside it and re-export. No behaviour change to existing loaders. |
| 2 | SPEC paths `core/calendars/data/*.yaml` vs `core/calendars.py` being a module | SPEC 1902, 1990, 2075; `calendars.py:32` | Convert to a package keeping the public API byte-compatible, or keep the module and record the deviating path in one place; either way the 2026–27 JSON loader and its tests stay untouched. Coordinator decision. |
| 3 | Which cache is "the ficc_cache" of TASK-M1-12 | SPEC 1283; §0 here | Both: apply the retrieval-time rule to cache A and cache B. |
| 4 | Source of pre-2026 calendars (KRX eras, CSAT dates, Saturday closes, pre-2015 random-end extensions, Fed/SIFMA/NYSE holidays, source-skipped dates) | SPEC 2013-2016, 2063-2067 (`from_krx_notice`, "UNVERIFIED"), 2053 | No owner-signed file → every acting input of that market fails closed (SPEC 2088); functions raise for uncovered dates; cards over uncovered spans are refused. `exchange_calendars` may be used as a cross-check only. |
| 5 | KIS field/division that is the KRX regular-session official close; exchange vs receipt time | SPEC 1496; `kis_client.py:238-246, 277` | Until the M1 check is recorded: stamp `official_close` only for daily rows retrieved ≥ `close_print_bound_utc` + 10 min with `available_at_source = calendar_bound`; treat `quote()` as `live_snapshot`; label dependent features UNVERIFIED. |
| 6 | SPEC market ids vs existing venue codes (`US` is both) | SPEC 1036-1037, 2074; `markets.py:248-252` | One explicit mapping table; existing `markets`/`calendars` keys unchanged. |
| 7 | Macro "regime" display vs P19 | SPEC 1124-1126; `macro.py:161-186` | Method is rule-based (no model): keep as descriptive text, rename the presentation so it is not a "regime state", never route it to sizing. |
| 8 | ALFRED vintages / FRED `last_updated` / ECOS / Treasury posting time need endpoints the code does not have; whether a key is required is not stated | SPEC 1278, 1373, 4203 | Not available → the affected inputs are context-only with `available_at_source = calendar_bound`; nothing acting depends on them (SPEC 1374). |
| 9 | Short-sale ban and sell-tax dates: SPEC gives months, R3 gives days | SPEC 2043-2044; R3 162 | Use the R3 day-level dates in the tag file, marked unsigned until the owner signs; an unsigned file is refused (SPEC 2053). |
| 10 | The 2-Oct-2026 incident data (vendor row 6,943.66, official 7,003.74) is not on this machine (no `^KS11` cache or CSV) | SPEC 1327-1329 | T-PROV-01 runs on a labelled synthetic store fixture built by the test (allowed by SPEC 1493 item 5). |
