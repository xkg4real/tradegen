# spec_M1_pit_contracts — M1 point-in-time store, data contracts, staleness by role (R-01, R-19)

Sources. Spec = `QUANTGEN_Quant_Council_2026-10-03/claude_code/QUANTGEN_MACRO_INTEGRATION.md` (cited `L<line>`); tasks = `prep/tasks/M1.json`; code = repo files (cited `file:Lline`). Binding = field names, parameters, bounds, formulas, thresholds, status strings (L89, L1808). Paths and function names marked "proposed" may be renamed (L963, L1808). Where silent: no exposure change, specification book only, fail closed (L89).

Out of this brief (calendars brief owns them; interface only here): TASK-M1-03, -04, -05 and the calendar half of -06 / -18 (R-20, L1983-2113).

---

## A. Scope

| Task | Deliverable (one line) | Target files (E = exists, N = new/proposed) | Exit tests |
|---|---|---|---|
| M1-01 | KIS quote-field check: 069500 and 005930 bid/ask at 15:19:59 KST on 20 sessions; record level-1 fields, exchange vs receipt timestamps, market-division code + price field of the KRX regular-session official close, whether the app key can trade; else record "not run" (L44, L6363) | N `docs/kis_quote_check.py` (read-only recorder, allowlisted paths only); N result record `<macro_artifact_dir>/m1/kis_quote_check.json`; E `data/krx/kis_client.py` | T-RO-02 (record clause) |
| M1-02 | Frozen allowlist of KIS quotation endpoints; any other path raises before a request is built; Claude API without tools | E `config.py` (+`KIS_QUOTATION_ALLOWLIST`); E `data/krx/kis_client.py:L176` (`KISClient._get`, single choke point; `data/kis_markets.py:L169-174` delegates to it); E `core/quant/insights.py:L312-318` (no `tools` key today) | T-RO-02 |
| M1-06 (R-19 half) | Publication rules per schedule; owner-signed source-exception list consumed by staleness | calendars brief builds; this area reads `publication_instant`, `next_expected_obs`, `add_publication_bdays`, `source_skipped` | T-H15-01, T-H10-02, T-VIX-01, T-AVAIL-01 |
| M1-07 | Append-only bitemporal store, `PITValue` v2, `MissingInput`, `RunContext`, `data_snapshot_id`, `fetch_log.jsonl` | N `core/ficc/pit.py` | T-PROV-01 |
| M1-08 | Series registry: fields, bindings, groups, range groups, channels | N `core/ficc/series_registry.yaml`; loader in N `core/ficc/contracts.py` | T-SER-02, T-ROLE-02, T-H10-01 |
| M1-09 | Per-series data contract; acting input without a contract refused; violations = missing input | same file as registry (`contract:` sub-map; `contracts.yaml` is "proposed", L1822) | T-ROLE-02, T-SER-02 |
| M1-10 | `pit_value()` as-of read with provisional-row guard and consumer bindings | N `core/ficc/pit.py` | T-PROV-01, T-SER-02 |
| M1-11 | Official close primary; status assignment; reconciliation; no bar-derived / flat-OHLC close | E `core/quant/history.py` (official-close loader keeps OHLCV); N `core/ficc/pit.py` (reconcile, dispute log) | T-BAR-01, T-BAR-02, T-PRINT-01 |
| M1-12 (bug) | `~/.nextgen/ficc_cache` never serves a pre-close row to an acting read; `data.ingest` | E `core/ficc/data.py:L216-251,L422-456`; E `core/quant/history.py:L398-451`; N ingest in `core/ficc/pit.py` | T-PROV-01 (cache regression) |
| M1-13 | Derived and monthly series as PIT records; calendar-offset arithmetic; Oct-2025 gap; ALFRED vintages | N `core/ficc/pit.py` (`put_derived`, monthly helpers) | T-MISS-01 |
| M1-14 | Named series required; futures roll days flagged and excluded | registry + `core/ficc/contracts.py`; E `core/quant/history.py` | T-SER-01 |
| M1-15 | Synthetic / auto-degraded value for an acting input → `MissingInput("synthetic_rejected")` | `core/ficc/pit.py` ingest stamps `provider_mode`, `synthetic`; E `core/ficc/data.py:L474-505` unchanged | T-SYN-01 |
| M1-16 | Schedule-aware `is_stale`, `expected_available_utc`, `pit_last` | N `core/ficc/contracts.py` | T-STALE-01, G-STALE-01 |
| M1-17 | Role-based failure actions, per-(book, series) and per-book counters, admission-derived bindings | N `core/ficc/contracts.py` (`on_input_failure`); N `core/engine/books.py` (counters) | T-ROLE-01, T-MISS-02 |
| M1-18 (R-19 half) | `usable_cross_market` | N `core/ficc/contracts.py` | T-XMKT-01, T-TZ-01 |
| M1-19 | Close stamping; independent lag audit; `LookAheadError`; positional-shift linter | N `core/ficc/lag_audit.py`; E `core/quant/backtest.py` (raise site) | T-LAG-01, T-LAG-02, T-CLOSE-01 (quarantine clauses) |
| M1-20 | Minimal per-book runtime: book ids, DISARMED/ARMED/HALTED, OPS class, automatic re-arm, governance events | N `core/engine/books.py` (do not alter `core/engine/state.py`, see F-2) | T-ROLE-01, T-LAG-01, T-MISS-02 (HALT clauses) |
| M1-21 | Read-only ECOS provider; Treasury par-yield channel with logged posting time; data acquisition register | E `core/ficc/data.py` (+`_ecos_fetch`, `_treasury_fetch` as the only new socket functions); `tests/fixtures/macro/MANIFEST.csv` | T-H15-01 (Treasury clause), T-SAT-01 (completeness clause) |
| M1-22 | Generate and md5-freeze golden fixtures at M1's exit; refuse non-post-close fixtures | N `tests/fixtures/macro/` + generator `docs/macro_fixtures.py`; validator in `core/ficc/pit.py` (`check_fixture`) | T-FIX-01, G-POST-01 (M1 rows) |
| M1-23 | M1 measurements: KODEX 200 basket publication instant, KRX/NYSE 30 s print bounds, FRED VIX posting lag (20 sessions) | signed registry / calendar revisions only | T-CAL-01 |

---

## B. Build spec

### B0. File layout (decision; see F-1)

`core/ficc/data.py`, `core/calendars.py` and `core/markets.py` are single modules, not packages. Fewest-files mapping:

| New file | Holds |
|---|---|
| `core/ficc/pit.py` | types, store, `pit_value`, `pit_last`, `data_snapshot_id`, `RunContext`, stamping, quarantine, reconciliation, derived records, cache rule, ingest, fixture check |
| `core/ficc/contracts.py` | registry loader + validation, `contract`, `expected_available_utc`, `is_stale`, `on_input_failure`, `usable_cross_market`, named-series guard, roll days |
| `core/ficc/lag_audit.py` | independent audit, `LookAheadError`, positional-shift linter |
| `core/ficc/series_registry.yaml` | registry + contracts + groups (PyYAML is already a dependency: `requirements.txt`) |
| `core/engine/books.py` | per-book runtime (OPS), counters |

Storage engine is not specified (silent). Use one JSONL file per `series_id` under `<store_dir>/` opened in append mode, plus `<store_dir>/fetch_log.jsonl`; stdlib only. `<store_dir>` = a new `config.pit_store_dir()` (default `~/.nextgen/pit_store`, env override), separate from `config.ficc_cache_dir()` (`config.py:L334`). Tests pass a temporary directory (T-HERM-02, L5608).

### B1. Types (L965-1021; binding)

```python
@dataclass(frozen=True)
class PITValue:
    series_id: str
    value: float
    obs_date: date                    # monthly series: first day of the reference month (L1351)
    session_date: date | None         # required for close-type inputs
    obs_utc: datetime                 # e.g. the scheduled close
    obs_kind: Literal["close", "quote_snapshot", "release", "bar", "derived"]   # "close-type" means obs_kind == "close"
    value_status: Literal["official_close", "vendor_close", "live_snapshot", "provisional_intraday", "first_release",
                          "revised", "vendor_derived", "vendor_derived_across_gap"]
    dispute: bool
    available_at_utc: datetime
    available_at_source: Literal["published", "calendar_bound", "inferred_from_retrieval"]
    retrieved_at_utc: datetime        # first-seen
    vintage: date | None              # ALFRED realtime_start; None for unrevised market prices
    source: str                       # KIS, KRX, FRED, ALFRED, Treasury, ECOS, Yahoo, FMP
    channel: str | None               # "H.15", "Treasury par yield", "ECOS 731Y003/0000003", "KIS live"
    provider_mode: Literal["explicit", "auto"]
    synthetic: bool
    content_hash: str                 # md5 of the record
    role: Literal["acting_exposure", "forward_sim", "risk_model", "context", "history"]   # of the caller's binding
    books: tuple[str, ...]            # HALT scope

@dataclass(frozen=True)
class MissingInput:
    series_id: str
    reason: Literal["missing", "stale", "provisional_intraday", "session_mismatch", "synthetic_rejected"]
    role: Literal["acting_exposure", "forward_sim", "risk_model", "context", "history"]
    books: tuple[str, ...]

# StaleCheck = Fresh | Stale("missing") | Stale("missed_release")          (L1018)
# RunContext{decision_utc, knowledge_utc, run_mode}; run_mode in {live, backtest, replay}   (L1105, L4198)
```

- `"disputed"` and `"warmup"` are statuses of a used value, never `MissingInput` reasons (L994).
- All timestamps UTC, ISO-8601 with "Z" (L1273).
- `knowledge_utc`: pinned once per run, never defaults to "now", written to every artifact. live = end of the `pit_snapshot` fetches; backtest = the card's data snapshot; replay = the artifact's `knowledge_utc` (L1001-1003, L4197).

### B2. Store (L1272-1283, L1493 (4), L4196-4202)

Stored row = every `PITValue` field except `role`, `books`, `dispute` (attached or computed at read). Derived rows also store `inputs: [content_hash, …]` (lineage).

| Rule | Text | Line |
|---|---|---|
| Append-only, bitemporal | corrections are new rows; rows never mutated (`rows_mutated: never`) | L1282, L4202 |
| Dedupe | `dedupe_key: [series_id, obs_date, vintage, source, value, value_status]`; a row is appended only when its content changes | L4202, L1283 |
| First-seen | `first_seen_is_retrieved_at: true`; an unchanged-content fetch is written only to `fetch_log.jsonl` | L1279, L4202 |
| `fetch_log.jsonl` line | `series_id, fetch_utc, provider, status, content-hash digest` | L1279 |
| `content_hash` | "md5 of the record" (L986). Composition not given: use md5 of canonical JSON of the `dedupe_key` fields (F-6) | L986 |
| `data_snapshot_id(knowledge_utc) -> str` | md5 of the sorted content hashes visible at `knowledge_utc` (rows with `retrieved_at_utc <= knowledge_utc`); order-invariant; unchanged when a later correction is appended | L1014, L5616 |

`available_at_utc` / `available_at_source` stamping (binding):

| Case | `available_at_utc` | `available_at_source` | Line |
|---|---|---|---|
| Official close, exchange print time logged | print time; must be ≤ `close_print_bound_utc(m, d)`; later → fail closed + calendar-review alert, never re-stamped | `published` (implied: the only remaining enum value) | L1311-1312, L2031 |
| Official close, no print time | `close_print_bound_utc(m, d)` | `calendar_bound` | L1312 |
| Official close, any | `obs_utc = decision_time_utc(m, d)`; a receipt time is only `retrieved_at_utc` | — | L2025-2031 |
| Backfilled history (fetched after its publication window) | registry publication rule for each `obs_date` | `calendar_bound` (never `inferred_from_retrieval`) | L1278 |
| Live row, vendor gives no publication time | retrieval time (an upper bound) | `inferred_from_retrieval` | L1278, L1496 |
| ALFRED vintage | `realtime_start` date at the publisher's scheduled release time (BLS/BEA 08:30 ET) | `calendar_bound` | L1278 |
| Obs older than the series' first ALFRED vintage | as above; `vintage = null`, `value_status = revised`, label `pre_vintage_history` (printed by every backtest that reads it) | — | L1278 |
| Unrevised daily market series (DGS10, DEXKOUS, VIXCLS) | publication calendar, not ALFRED | — | L1278 |
| Re-posting channel (FRED for VIXCLS, DTWEXBGS) | that channel's posting time: FRED `last_updated` live; a declared lag in history | — | L1278 |
| Treasury par yield | logged first-seen posting time (expected instant for staleness stays 18:00 ET) | not stated; `inferred_from_retrieval` live (first-seen by the poller), `calendar_bound` in backfilled history | L1850 |
| ECOS 15:30 close, live | ECOS posting time | `inferred_from_retrieval` | L1414 |
| ECOS backfilled history | 15:30:00 KST of K (15:00:00 before 2016-08-01); `timing = value_proxy` | `calendar_bound` | L1414 |
| Derived | latest `available_at_utc` of its inputs; `value_status` = weakest input status | — | L1282 |

### B3. `pit_value` (L998-1013, L1317-1319; T-PROV-01 L5612)

```python
def pit_value(series_id: str, decision_utc: datetime, knowledge_utc: datetime, consumer: str,
              require_session: date | None = None) -> PITValue | MissingInput
def pit_last(series_id, decision_utc, knowledge_utc)   # latest record with available_at_utc <= decision_utc,
                                                       # retrieved_at_utc <= knowledge_utc (L1858)
```

Algorithm:

1. `binding = registry.binding(series_id, consumer)` → `(role, books)`. An entry without a `consumer` key binds every consumer of the series; a bare book kind means that kind's book in the series' market (L1105). No binding and consumer is not a `context` consumer → raise (L1891, T-SER-02). Consumer `nav` never raises (L1888). `run_mode = live` and series is `DEXKOUS` and the consumer is acting or risk-model → raise (T-H10-01 L5632; `data.usdkrw.production_reads_dexkous: false` L4222).
2. Visible rows: `available_at_utc <= decision_utc` and `retrieved_at_utc <= knowledge_utc`.
3. Close-type acting read (registry `obs_kind = close`, role `acting_exposure`): `require_session` is mandatory, calling without it raises (L1012). Candidates = visible rows with `obs_date == require_session`; none → `MissingInput("missing")`, even when the previous session's close is visible (L1009-1010).
4. Within one `(series_id, obs_date)` pick by: `value_status` rank `official_close > revised > first_release > vendor_close > vendor_derived > vendor_derived_across_gap > live_snapshot > provisional_intraday` (L1004-1005; `data.value_status_rank` L4199), then registry source precedence, then latest `available_at_utc`, then latest `retrieved_at_utc`.
5. Close-type acting read: selected `value_status != "official_close"` → `MissingInput("provisional_intraday")`; selected `session_date != require_session` → `MissingInput("session_mismatch")` (a mis-dated row) (L1007-1011, L1318). Applies even if `available_at_utc` precedes the decision.
6. `synthetic` or `provider_mode == "auto"` degraded value for an acting input → `MissingInput("synthetic_rejected")` (L985, L5611). Context consumer: returned and labelled.
7. Backtest may read `vendor_close` only when its card header declares that vendor as `data.source` (L1013, L1319, `data.vendor_close_in_backtests` L4200). Live and forward decisions accept only `official_close` for close-type acting inputs (L1319).
8. `dispute`: computed at read from the visible rows of the same `obs_date` (B4); returned `PITValue.dispute = True`, artifact status `disputed`; passes the guard; never a failure (L1321, T-BAR-02).

T-PROV-01 trace (decision_utc fixed `2026-10-02T06:30:30Z`, consumer `R-06`, `require_session = 2026-10-02`): knowledge 01:31Z → no row of that session visible → `MissingInput("missing")`; 02:00Z → vendor row (retrieved 01:56Z, `provisional_intraday`) → `MissingInput("provisional_intraday")`; 07:00Z → KIS row (`available_at_utc` 06:30:30Z `calendar_bound`, retrieved 06:40:45Z, `official_close`) → 7,003.74.

A missing close at decision t is `missing` through step 3, not through `is_stale` (whose deadline is the next session's bound + grace). The acting read path is therefore: `pit_value` → contract check (B10) → `is_stale` (B11) → `MissingInput` on any failure. The spec defines no wrapper name; `MissingInput.reason = "stale"` is produced only there (F-11).

### B4. Value status, quarantine, reconciliation (L1317-1326, L1380-1382, L1493 (3), L4204-4212)

Status assignment (binding, L1319):

| Row | `value_status` | `obs_kind` |
|---|---|---|
| KRX-session close field of KIS, or the KRX marketplace, retrieved ≥ `close_print_bound_utc` + 10 min | `official_close` | `close` |
| Vendor daily row retrieved ≥ that instant | `vendor_close` | `close` |
| Any row of a close-type series retrieved before that instant | never stored as a close (L1323) → `provisional_intraday` (T-PROV-01 fixture) | not `close` (F-5) |
| Quote read during or after the session; a current-price read | `live_snapshot` | `quote_snapshot` (L1496) |
| Vendor "last" after 15:30 KST; NXT / KRX after-market print | never a close (L1289) | — |

- Quarantine anchor: `close_print_bound_utc` of the row's session + `data.reject_rows_retrieved_before_close_plus_minutes: 10` (L4206). Boundary inclusive: retrieved 06:40:29Z → never `official_close`; 06:40:30Z → `official_close` (T-CLOSE-01 L5617).
- A record with `available_at_utc` 06:31Z is rejected for the 06:30:30Z decision; an official close with exchange print time 06:30:20Z is accepted (L5617).
- Only the KIS market-division code and price field identified by M1-01 is ever stamped `official_close`; those code values are UNVERIFIED until then (L1496). Candidate fields already in the repo: `FID_COND_MRKT_DIV_CODE = "J"` + `stck_clpr` (`data/krx/kis_client.py:L259,L277`); index `"U"` + `bstp_nmix_prpr` (`data/kis_markets.py:L441-449`); KRX marketplace `idx/krx_dd_trd`, `sto/stk_bydd_trd` (`data/krx/krx_market_client.py:L36-40`). See F-4.
- Official-source outage: fail closed; never fall back to a vendor intraday print (L1496).

Reconciliation (`data.reconciliation: {primary: [KIS, KRX], secondary: vendor, tol_index_bp: 1, tol_stock: exact, on_mismatch: disputed_use_official_and_alert, auto_correct: false}`, L4207-4208):

```
reconcile(series_id, obs_date, ctx) -> {"ok" | "disputed" | "vendor_missing"}
  index: |official/vendor - 1| <= 1 bp            stock: exact, on a declared adjustment_basis
  mismatch       -> use official, dispute = true, status "disputed", alert, append dispute log; never a failure
  vendor absent on a KRX session -> "vendor_missing" (not a dispute)        (L1320, T-BAR-02)
  never auto-correct                                                        (L1322)
```

- Stocks reconcile like with like: raw official closes plus effective-dated corporate-action factors from KRX or DART, stored with their announcement `available_at_utc`; never raw against adjusted (L1320). `_yf_fetch` downloads with `auto_adjust=True` (`core/ficc/data.py:L200`), so the vendor stock leg needs an unadjusted fetch for reconciliation.
- Record whether loader closes are price or total-return (finding A3, L1384): reuse `History.adjustment` (`core/quant/history.py:L61-64`).
- Flat-OHLC, zero-volume row on a session day = stale carry: flagged and alerted, never stored as a close, never read as a zero return (L1324, `data.stale_carry_flag` L4209). `kis_history` keeps only `close` (`core/quant/history.py:L204-210`); the official-close loader must keep OHLCV (`KISClient.daily` already returns it, `kis_client.py:L272-279`).
- `data.daily_close_from_bars: forbidden`; bars carry `bar_end`, the closing auction is its own bar, `available_at = bar_end + latency` (L1325, L4210-4211).
- Open-quality flag: OHLC open equal to the prior close (`data.open_quality_flag: open_equals_prior_close`, L4212); per-series ratio consumed by R-30 (M3).
- Circuit-breaker print is never a close: 2026-03-09 close 5,251.87 (−5.96%); −8.11% was a 10:31 print (L1382, T-PRINT-01).

### B5. Cache rule and ingest (TASK-M1-12; L1283, L4201-4203)

Defect today: `core/ficc/data.py:_cache_get` (L223-238) serves any payload younger than `config.FICC_CACHE_TTL_SECONDS` (6 h, `config.py:L331`) keyed `provider_id_days`; `_provider_rows` is cache-first (L430-435). `core/quant/history.py:_cached` (L398-451) already shortens the TTL to 600 s for a series fetched while its market may be trading (L356, L427-432), which narrows but does not close the hole for acting reads.

Rule (binding, L1283):

```
serve_cached(series, decision_utc, cached) iff
    cached.retrieved_at_utc > most recent due publication instant <= decision_utc of that series
    close-type series: cached.retrieved_at_utc > close_print_bound_utc(m, decided_session) + 10 min
else re-fetch; a failed re-fetch -> MissingInput, never the cached row
the cache never holds derived values of acting inputs
a cached value keeps its retrieved_at_utc          (the cache file's "ts" is that instant)
```

Minimal change: acting and risk-model reads go only through the PIT store; the store's ingest calls the provider fetchers directly and applies the rule above when it consults the cache. UI and context loaders (`load_series`, `load_history`) keep their current cache behaviour. Regression case replays the incident: cache file written 01:56Z containing the 2-Oct row 6,943.66 → read at knowledge 02:00Z = `MissingInput("provisional_intraday")`; at 07:00Z = 7,003.74 `[official_close]`.

`data.ingest` (verbatim L4201-4203):
```yaml
ingest: {trigger: [pit_snapshot, publication_schedule], retries_min: [1, 5, 15, 60], decision_deadline: next_session_open_minus_30min,
         dedupe_key: [series_id, obs_date, vintage, source, value, value_status], first_seen_is_retrieved_at: true, fetch_log: fetch_log.jsonl, rows_mutated: never,
         posting_time_pollers: {TREASURY_PAR: "17:30-21:00 ET every 5 min", FRED_REPOSTS: last_updated}}   # deadline and poll window: default, judgment
```
M1 builds `ingest(series_id, now_utc) -> appended: bool` (fetch, stamp, dedupe, append or log). The scheduler that fires it at `pit_snapshot` and on each publication schedule is the M8 workflow (L1198-1201).

### B6. Derived and monthly series (TASK-M1-13; L1282, L1350-1355, L1370-1374, L4217-4219)

- Derived series (σ̂, rv20, YoY and 3-month changes, corr63, z-scores, the paper momentum series, contract notionals): PIT records with `obs_kind = derived`; `available_at_utc` = latest input `available_at_utc`; `value_status` = weakest input status by the B3 rank; `content_hash` covers the inputs' content hashes; recomputed whenever an input row changes; never served from the cache.
- A derived acting value with any non-`official_close` close-type input → `MissingInput("provisional_intraday")` (L1282).
- Monthly series: explicit monthly index keyed by the first day of the reference month = `obs_date` (L1351).
- YoY and 3-month changes by calendar offset, never positional `shift` (`data.monthly_lag_method: calendar`).
- Missing month (Oct-2025 CPI and household survey): NaN and flagged for every derived value that uses it as an endpoint or as a member of an averaging window: YoY for Oct-2025 and Oct-2026, MoM for Oct and Nov 2025, Sahm's 3-month means. An endpoint change whose window merely contains it is computed: Aug-2026 CPI YoY = 3.353% ± 0.01; the positional 3.713% must never be produced (L1353-1355, T-MISS-01 L5624).
- In-house derived: `data.derived_series_in_house: [sahm, yoy, taylor_range]`; a vendor value across a gap is tagged `vendor_derived_across_gap` (FRED SAHMCURRENT shows 0.25 for Oct-2025 although UNRATE is missing, L1354).
- Vintages: `data.vintages: {source: alfred, store_first_release: true, store_latest: true}`; FRED `output_type=4` gives initial releases (L1373). Acting rules use only unrevised market-priced series (L1374); core PCE YoY (risk model) is read as of its vintage (L5637).

### B7. Named series and futures rolls (TASK-M1-14; L1376-1378, L4220-4221)

- `data.named_series_required: true`; `data.brent_series: {spot: DCOILBRENTEU, futures: BZ=F}`. A read of `"Brent"` raises (T-SER-01).
- Roll days are flagged and excluded from return computations: BZ=F 2026-04-01 (−14.5%).
- Futures books use a fixed roll calendar; the expiring KOSPI200 contract stops trading at 15:20 KST; continuous-contract returns across rolls are never computed (L1378, §10 item 19 L6148-6149). `KISMarkets.continuous_futures` (`data/kis_markets.py:L291-317`, ratio-adjusted) and Yahoo `=F` tickers stay display-only: never bound in the registry (F-18).

### B8. Synthetic rejection (TASK-M1-15; L374, L548, L4214-4216)

Routing rule kept as is: an explicit provider that fails raises; only `auto` degrades to labelled synthetic (`core/ficc/data.py:L500-504`, `core/quant/history.py:L484-504`). Ingest stamps `provider_mode` and `synthetic`; acting read → `MissingInput`, `status = "synthetic_rejected"`, `fail_closed = true`; context item allowed and labelled (T-SYN-01). `data.interpolate: false`.

### B9. Registry (TASK-M1-08; L1388-1403, L1883-1891)

Per-series fields (verbatim names): `series_id`, `source`, `channel`, `frequency`, `obs_calendar` (KRX, NYSE, FED, SIFMA, CBOE, JPX, SSE, HKEX, TWSE, CME or ECOS), `publication_schedule` `{calendar, time, tz}` (e.g. `{calendar: FED, time: "16:15", tz: America/New_York}`), `release_event_type`, the time zone of `obs_date`, `grace_publication_bdays` (1), `bindings` `[{consumer, role, books}]`, `halt_after_consecutive_decisions` (acting bindings; 2), `timing_class` (live, publication or value_proxy), `production_channel`, `history_channel` (selected by `run_mode`), `adjustment_basis`, `obs_kind`, range checks, the cross-source tolerance. R-19's input list also names `schedule_id` and `grace_pub_bdays` (L1833).

Load-time validation (each a refusal):

| Check | Line |
|---|---|
| An acting input without a contract cannot be registered | L1846, L1955 |
| An acting or forward_sim mapping entry without an explicit `books` list is refused; `books: []` registers a dormant binding and is allowed | L1891, T-ROLE-02 |
| A scalar entry in `data_contracts.roles` means its market's recommended and specification books | L1891, L1917-1918 |
| Roles are bound per (series, consumer, books), never per series | L1891 |
| A group id in `roles` or a range-group name in `ranges` must be declared as a group and resolve to existing member series ids; a group name is never a series id | L1891, T-SER-02 |
| Every series id referenced by the rules store, `data_contracts.roles`, card headers and §4.2 exists with a contract; unknown id fails | T-SER-02 L5630 |
| Any book that reads a factor whose acting inputs are not bound to it is refused | L1889, T-SCOPE-01 (g) |
| `USD_LIVE_PROXY` is named before M2 (default, judgment: `DX-Y.NYB`) | L1431, L6030 |

Bindings follow admission (L1889): at every decision the runtime derives each binding's book list from the admissions (`verdict_filter`, M8) without editing the `roles` entry; each change of a derived binding is a governance event (`kind: binding_change`, L4104) in the same run. In M1 no card is PASS, so derived = declared; implement `derive_bindings(admissions: dict[str, bool])` with an injected map.

### B10. Contract (TASK-M1-09; L1838-1846, L1882)

```python
def contract(series_id: str) -> DataContract
# DataContract: dtype, unit, decimals in the core; range; monotone obs_date; publication schedule and grace;
#               cross-source tolerance; role and failure action
```

Ranges (verbatim L1916): `ranges: {abs_daily_return_max: {KOSPI: 0.30}, VIXCLS: [5, 150], yields_pct: {US_TREASURY: [-1, 20], KR_CALL_CD: [-1, 40]}}` (Korean rates ran at 16–25% in 1997–98).

Contract violations = a value out of range, a schema error, a non-monotone date, a provisional row for a close-type input → treated as a missing input with the role's action (L1882). Reason code for the first three is not given; use `"missing"` (F-7).

### B11. Staleness (TASK-M1-16; L1357-1368, L1847-1865; normative step 3)

```python
def expected_available_utc(series_id: str, last_obs: date) -> datetime
#   = publication_instant(series, next_expected_obs(series, last_obs)); never the availability of last_obs itself (L1015-1017)

def is_stale(series, decision_utc, knowledge_utc):
    rec = pit_last(series, decision_utc, knowledge_utc)
    if rec is None:
        return Stale("missing")
    d_next = cal.next_expected_obs(series, rec.obs_date)        # skips source-exception dates
    due = cal.publication_instant(series, d_next)
    deadline = cal.add_publication_bdays(series, due, contract(series).grace_pub_bdays)   # default 1
    return Stale("missed_release") if decision_utc > deadline else Fresh()
```

Publication rules (step 2, L1847-1852; `time.publication` L4167-4173):

| Schedule | Expected instant |
|---|---|
| H.15 (DGS10 and every H.15 series) | 16:15 ET on the next Fed business day after D |
| H.10 (DEXKOUS, DTWEXBGS, DEXJPUS) | 16:15 ET on the Monday following the week; next Fed business day when that Monday is a federal holiday |
| Treasury par-yield curve | 18:00 ET on D (scheduled; "may be delayed"); the logged first-seen posting time is the record's `available_at_utc` |
| BLS | 08:30 ET; BEA: its release calendar |
| Market closes | the session's close-print bound |

- Source-exception dates generate no expected observation: Good-Friday bond-market closures, 2017-01-20, 2018-12-05, 2020-11-27, 2020-12-24, DC storm closures 2016-01-22 and 2018-03-02; versioned, owner-signed list at `data_contracts.source_exceptions: core/calendars/data/source_skipped.yaml` (L1854, L1902).
- Unscheduled delays: the series' `release_event_type` event with `status = delayed` or `cancelled` moves or removes the expected instant (`data_contracts.unscheduled_delay: event_status_delayed`, L1367, L4271).
- If the publication calendar cannot be read: every acting input fails closed and every risk-model input takes its conservative default; never a fallback to observation-age staleness (L1956).
- Negative control: reading `expected_available_utc` as the availability of `last_obs` itself flags DEXKOUS on about 80% of decisions; the implementation must not (L1963 (e)).
- Artifact fields: `inputs[].expected_available_utc` (the next-due instant), `inputs[].stale_deadline_utc` (L3644-3645). Example: KOSPI close of 2026-10-02 → `2026-10-06T06:30:30Z` / `2026-10-07T06:30:30Z`; DEXKOUS dated 2026-09-25 (available `2026-09-28T20:15:00Z`) → `2026-10-05T20:15:00Z` / `2026-10-06T20:15:00Z` (L3661-3668).

### B12. Failure action by role, counters (TASK-M1-17; L1866-1882, L1903-1914, L1107-1111)

```python
def on_input_failure(series_id, check) -> FailureAction      # L1826; needs the binding as well (F-9)
```

| Role | Action | Config (verbatim L1904-1914) |
|---|---|---|
| `acting_exposure` | input returns `MissingInput`; component state unchanged; `fail_closed = true`; alert; counters +1 for bound books only; no interpolation | `{action: fail_closed, alert: true, halt_after_consecutive_decisions: 2, scope: bound_books, book_counter_halt_after: 2}` |
| `risk_model` | `hedge_credit_off = TRUE`; `hedge_failure` from the labelled live USD proxy; alert; operator escalation after 2 missed releases; never HALT; an exception inside `hedge_state` takes the same default (consumer arrives in M2) | `{action: conservative_default, set: {hedge_credit_off: true}, hedge_failure_from: USD_LIVE_PROXY, operator_alert_after_missed_releases: 2, halt: never, also_on: hedge_state_exception}` |
| `risk_model_covariance` | carry the series' last valid covariance terms labelled stale for ≤ 5 decisions, then drop and label; never sets `hedge_credit_off` | `{action: carry_last_valid_terms_stale_then_drop, carry_max_decisions: 5, alert: true, halt: never, sets_hedge_credit_off: false}` |
| `context` | labelled `stale` in `context_log`; nothing else | `{action: label_stale}` |
| `forward_sim` | that FORWARD-SIM book fails closed (multiplier carried), alert; never HALTs another book | `{action: fail_closed_that_book, alert: true, halt: never}` |
| `history` | read by the card harness only; an uncovered span refuses the card | `{action: refuse_card_if_span_not_covered, alert: true, read_by_weight_decisions: false}` |
| not failures | a `warmup` input before the book's first ARMED decision (neutral 1.0, status `warmup`); a disputed official close | `not_failures: [warmup_before_first_armed_decision, disputed]` |

Counters (L1869-1871), kept per book in the runtime state:

```
input_counter[book][series]  = consecutive decisions at which that input failed closed; reset at its next fresh decision
book_counter[book]           = consecutive decisions at which ANY acting input bound to the book WITH THE DEFAULT LIMIT failed closed;
                               reset at a decision at which all of them are fresh
HALT(book, OPS) when input_counter reaches the binding's halt_after_consecutive_decisions
                     (default 2; KODEX200_PDF 5; NAV_LINE_CLOSES 3)
                 or book_counter reaches book_counter_halt_after (2)        -> two inputs failing on alternate decisions HALT at the 2nd
only bound books count: an input bound to no recommended book never HALTs one; an input bound only to the specification book HALTs it alone
halt.reason_code = "acting_input_stale:<series_id>"                          (L1951)
```

Status-code map `MissingInput.reason` → `macro_state.inputs[].status` (L1108): `missing → missing`; `stale → stale_missed_release`; `provisional_intraday → provisional_rejected`; `session_mismatch → session_mismatch`; `synthetic_rejected → synthetic_rejected`; `Stale("missing") → missing`; `Stale("missed_release") → stale_missed_release`; stale context input → `stale`. Only these count as failures. Full enum: `ok, stale, stale_missed_release, missing, provisional_rejected, session_mismatch, synthetic_rejected, disputed, warmup` (L3650).

After a book has been ARMED, fewer valid observations than a factor's minimum is `MissingInput("missing")`, never neutral 1.0 (L1111).

### B13. Cross-market availability (TASK-M1-18; L1332-1339, L1892-1894)

```python
def usable_cross_market(market: str, obs_date: date, decision_utc: datetime) -> bool:
    return close_print_bound_utc(market, obs_date) + timedelta(seconds=60) < decision_utc      # strict <
# data_contracts.cross_market: {rule: "close_print_bound_utc(m, D) + buffer < decision_utc", buffer_s: 60}   (L1915)
```

- US- or New-York-dated datum dated D enters the KRX decision of K only if `D <= K − 1 calendar day` and `available_at_utc <=` the KRX `decision_utc` on K (`time.cross_tz_rule`, L1333, L4164).
- Never the US session dated K for a KRX close-to-close return dated K (L1335).
- Covariances use synchronous or lagged returns, never a same-date join across asynchronous closes (L1339, L1894).

### B14. Lag audit and close stamping (TASK-M1-19; L1210-1217, L1493 (1), L1497, L2025-2033)

```python
class LookAheadError(Exception): ...
def lag_audit(inputs: list[PITValue], ctx: RunContext, market: str) -> dict   # {"checked": int, "violations": [...]}
```

For every acting and risk-model input (context is skipped, L3703), recomputed from `core/calendars` and the registry, independently of `pit_value`:

| Check | Line |
|---|---|
| `usable_at(series, obs_date, market) <= decision_utc` | L1211-1212 |
| `available_at_utc >= publication_instant(series, obs_date)`; closes: ≥ the scheduled close; a derived input: each input of its lineage | L1212-1213 |
| `retrieved_at_utc <= knowledge_utc` | L1213 |
| R-01 status and session checks | L1213-1214 |

Violation record fields: `series_id, obs_date, check, expected_usable_at_utc, stamped_available_at_utc` (L3543-3547); written to `macro_state.lag_audit`.

| Where | Effect | Line |
|---|---|---|
| Backtest | raise `LookAheadError`; the result or forward record it touches is invalid | L1497, T-LAG-01 |
| Runtime, acting input | HALT (OPS) the books the input feeds; operator re-arm | L1214, L1179 |
| Runtime, risk-model input | `hedge_credit_off` + alert, never HALT (covariance-only: carried then dropped) | L1215-1216 |
| A provisional row reaching an acting input | counts as a lag-audit violation | L1497 |
| Positional `shift` on a series with gaps | rejected by the linter / audit | T-LAG-02 L5610 |
| Deferred | "refuses to write the card", `timing_probe` exception (rows tagged `synthetic_lookahead = true`) → M7 | L5582-5584 |

### B15. Per-book runtime, OPS class only (TASK-M1-20; L1178-1180, L1081-1086, L6363)

Book ids: `recommended:<market>`, `specification:<market>`, `forward_sim:<rule>`, `refusal:<rule>`, `card:<card_id>:<on|off|S>` (L1180).

```python
def runtime_halt(book_id: str, cls: Literal["RISK", "OPS"], reason: str) -> None     # M1: "OPS" only
def runtime_rearm(book_id: str, mode: Literal["auto", "operator"], operator: str | None = None) -> None
```

| Transition | Rule | Line |
|---|---|---|
| DISARMED → ARMED | automatic, only for a book never ARMED, at the first decision where every acting input bound to the book is fresh and past warm-up, calendars cover ≥ 60 sessions ahead, and (card books) the header is committed; governance event `book_state` | L1180, L4116-4118 |
| ARMED → HALTED (OPS) | bound acting input at its limit; lag-audit violation; calendar coverage (`calendar_coverage`) | L1178 |
| HALTED → ARMED (OPS) | automatic at the first decision at which the cause has cleared; no refusal window, no reference reset, no cap; operator re-arm after a lag-audit violation or an acting-artifact schema failure | L1179 |
| Idempotence | a HALT while HALTED is idempotent for its own cause; a different cause joins `halt.causes[]` `{class, reason_code, since_utc, rearm_mode, rearm_not_before, cleared_utc}`; top-level `class`, `reason_code`, `since_utc` restate `causes[0]`; top-level `rearm_mode` is `operator` while any uncleared cause needs the operator | L1179 |
| Scope | only books whose own bound acting input failed; a global failure (PIT store, calendars) HALTs every book that reads it, never "the engine" | L1178 |
| Effective time | a HALT decided at the close of t sets the weights decided at t to 0 | L1178 |
| Logging | every HALT, re-arm, state change = one `governance_events.jsonl` line | L1179, L4096 |
| Never a trigger | stale or failing `risk_model` / `context` input; `disputed`; `warmup` before first ARMED; an input not bound to the book | L1178 |
| Left to M5 | RISK class, operator kill, heartbeat, NAV, remaining OPS triggers | L6363, L6367 |

State persisted per book (`macro_state.runtime[]`, L3608-3623): `book_id, engine_state, halt, consecutive_failures, book_counter` (+ `post_rearm_cap_until, nav, hwm_hard, ref_step`, null in M1).

### B16. KIS read-only guard and quote-field check (TASK-M1-01, -02; T-RO-02 L5606)

- `config.KIS_QUOTATION_ALLOWLIST: frozenset[str]` = the 24 distinct `/uapi/.../quotations/...` paths in use today (3 in `data/krx/kis_client.py:L229,L256,L290`; 21 in `data/kis_markets.py:L211-618`).
- First statement of `KISClient._get`: `if path not in config.KIS_QUOTATION_ALLOWLIST: raise KISError(...)`, before credentials are read or headers built (`kis_client.py:L183`). The token POST `/oauth2/tokenP` (`kis_client.py:L158-163`) is the one non-quotation call and stays hard-coded.
- Claude API: called without tools, its text never parsed by an acting module. Today's payload has `model, max_tokens, system, messages` only (`core/quant/insights.py:L316-317`); add a test that no module under the acting path imports `core.quant.insights` / `core.ficc.insights`.
- Credentials stay env-only (L1253).
- Quote-field check record (proposed shape): `{status: "not run" | "run", sessions: [...], level1_fields: [...], exchange_ts_field, receipt_ts_field, official_close: {market_div_code, price_field}, app_key_can_trade: true | false | "unknown", evidence}`. Without KIS access: `status: "not run"`; R-27 snapshots, R-08 spread snapshots and the R-26 stress-line calibration stay labelled UNVERIFIED; if the fields are missing, open BL-C02 (L44, L6363). Nothing else in M1 waits for it.

### B17. Providers (TASK-M1-21; L905, L1414-1416, L1427, L6022-6035)

| Provider | Rule |
|---|---|
| BoK ECOS (read-only) | statistic 731Y003, item 0000003, "원/달러(종가 15:30)", daily from 1990-03-02; live reads `inferred_from_retrieval`; backfilled history `calendar_bound` at 15:30:00 KST of K (15:00:00 before 2016-08-01), `timing = value_proxy` |
| `BOK_CALL_RATE` | ECOS statistic code, item and observation calendar supplied by the owner before the M7 freeze (L1416, L6029, L76) |
| US Treasury daily par-yield curve | logs its first-seen posting time; poll `17:30-21:00 ET every 5 min` (L4203); usable +1 business day for a US close decision |
| Acquisition | KRX official KOSPI daily closes from 1997-01-03 with Saturday sessions (KRX marketplace); JPX, SSE, HKEX, TWSE, CME, Cboe calendars; licence, owner, md5 per file, else "not a fixture" (L6035) |

Not substitutes: `KISMarkets.usdkrw_daily` (`FX@KRW`, a daily fixing, `kis_markets.py:L64,L496`) is not the ECOS 15:30 close; KIS `Y0114` "Call 1d" and `Y0112` "CD 91d" (`kis_markets.py:L59`) are not the ECOS history series.

### B18. Fixtures (TASK-M1-22; L22, L5492, L1493 (5), L6018)

```python
def check_fixture(path) -> None    # raises on refusal
#   any close-type row with retrieved_at_utc < close_print_bound_utc(row session) + 10 min -> refused
#   any publication-timed row retrieved before its publication_instant               -> refused
#   synthetic store fixtures built by a test (T-PROV-01) are labelled and exempt
```

- Generated once, at M1's exit, by QUANTGEN's own data layer from the frozen reference files under `/home/claude/quantgen_macro_data/` (`CATALOG.md`, `scripts/`, `results/`): values unchanged; provenance fields and `value_status` added; historical close-type vendor rows `available_at_source = calendar_bound`; md5 per file.
- A regeneration before the M7 freeze must reproduce the same md5s or is a fixture change logged in the manifest with the tests it re-baselines.
- `data.fixtures: {post_close_only: true, min_minutes_after_close: 10, md5_per_file: true}` (L4213).
- The reference directory is not on this machine: the generator and validator can be built and tested; the generation itself cannot run (D, F-20).

### B19. M1 measurements (TASK-M1-23; L6010, L1411, L1426)

KODEX 200 basket publication instant (until measured: `expected_available_utc` = 08:00 KST on the next KRX session, `halt_after_consecutive_decisions: 5`, last basket carried with its age printed); KRX and NYSE 30 s print bounds against logged exchange print times; FRED `last_updated` for VIXCLS on 20 sessions. Each result enters only as a signed calendar or registry revision with a new test case; a record is never re-stamped.

---

## C. Schemas and config

### C1. Rules-store blocks read (written by M0-05; the rule governs if §7 differs, L4132)

`data` (verbatim L4195-4224):
```yaml
data:
  store: {append_only: true, bitemporal: true, as_of_reads: true, snapshot_id: md5_of_visible_content_hashes}
  knowledge_utc: {pinned_once_per_run: true, defaults_to_now: false, written_to_every_artifact: true}
  run_mode: {values: [live, backtest, replay], selects: [production_channel, history_channel]}
  value_status_rank: [official_close, revised, first_release, vendor_close, vendor_derived, vendor_derived_across_gap, live_snapshot, provisional_intraday]
  vendor_close_in_backtests: only_if_card_header_declares_the_vendor_as_data_source
  ingest: {trigger: [pit_snapshot, publication_schedule], retries_min: [1, 5, 15, 60], decision_deadline: next_session_open_minus_30min,
           dedupe_key: [series_id, obs_date, vintage, source, value, value_status], first_seen_is_retrieved_at: true, fetch_log: fetch_log.jsonl, rows_mutated: never,
           posting_time_pollers: {TREASURY_PAR: "17:30-21:00 ET every 5 min", FRED_REPOSTS: last_updated}}
  value_status_required_for_close_inputs: official_close
  require_session_match: true
  reject_rows_retrieved_before_close_plus_minutes: 10
  reconciliation: {primary: [KIS, KRX], secondary: vendor, tol_index_bp: 1, tol_stock: exact,
                   on_mismatch: disputed_use_official_and_alert, auto_correct: false}
  stale_carry_flag: flat_ohlc_zero_volume_on_session_day
  daily_close_from_bars: forbidden
  bars: {stamp: bar_end, closing_auction_own_bar: true, available_at: bar_end_plus_latency}
  open_quality_flag: open_equals_prior_close
  fixtures: {post_close_only: true, min_minutes_after_close: 10, md5_per_file: true}
  fail_closed_on_missing_acting_input: true
  synthetic_for_acting_inputs: forbidden
  interpolate: false
  monthly_lag_method: calendar
  vintages: {source: alfred, store_first_release: true, store_latest: true}
  derived_series_in_house: [sahm, yoy, taylor_range]
  named_series_required: true
  brent_series: {spot: DCOILBRENTEU, futures: BZ=F}
  usdkrw: {input: [ECOS_1530_CLOSE, USDKRW_1530_SNAPSHOT], proxy: DEXKOUS, proxy_timing: H10_publication, production_reads_dexkous: false,
           record_fx_regime: true}
  us10y: {production: US10Y_KIS_QUOTE, history: [TREASURY_PAR, DGS10], dgs10_strict_lag_bdays: 2, treasury_lag_bdays: 1, live_proxy_history: "^TNX"}
```
`us10y` lag counts document the usual case only; code uses `usable_at()` (L4224).

`time.publication` (verbatim L4167-4173):
```yaml
publication:
  H15: {posted: "16:15 ET on the next Fed business day"}
  H10: {posted: "Monday 16:15 ET; next business day if Monday is a Federal holiday"}
  TREASURY_PAR: {posted: "usually by 18:00 ET on D", log_posting_time: true, us_close_decision_bdays: 1}
  VIXCLS: {official_close: "16:15 ET", us_close_decision_bdays: 1}
  BLS: {posted: "08:30 ET"}
  ECOS_USDKRW: {close_kst: "15:30", close_1500_until: "2016-08-01", snapshot_1530_from: "2026-07-06"}
```
Also `time.cross_tz_rule`, `time.cross_market_rule: data_contracts.cross_market`, `time.business_days: {publication: fed_sifma_calendar, decision: exchange_calendar}` (L4164-4166).

`data_contracts` (verbatim L1898-1943, plus `unscheduled_delay` from L4271; replaces v1.2's `time.max_staleness`):
```yaml
data_contracts:
  staleness_rule: schedule_aware
  grace_publication_bdays: 1
  source_exceptions: core/calendars/data/source_skipped.yaml
  on_failure:
    acting_exposure: {action: fail_closed, alert: true, halt_after_consecutive_decisions: 2, scope: bound_books,
                      book_counter_halt_after: 2}
    risk_model:      {action: conservative_default, set: {hedge_credit_off: true},
                      hedge_failure_from: USD_LIVE_PROXY, operator_alert_after_missed_releases: 2, halt: never,
                      also_on: hedge_state_exception}
    context:         {action: label_stale}
    forward_sim:     {action: fail_closed_that_book, alert: true, halt: never}
    history:         {action: refuse_card_if_span_not_covered, alert: true, read_by_weight_decisions: false}
    risk_model_covariance: {action: carry_last_valid_terms_stale_then_drop, carry_max_decisions: 5, alert: true, halt: never,
                            sets_hedge_credit_off: false}
    not_failures:    [warmup_before_first_armed_decision, disputed]
  cross_market: {rule: "close_print_bound_utc(m, D) + buffer < decision_utc", buffer_s: 60}
  ranges: {abs_daily_return_max: {KOSPI: 0.30}, VIXCLS: [5, 150], yields_pct: {US_TREASURY: [-1, 20], KR_CALL_CD: [-1, 40]}}
  roles:
    KOSPI_OFFICIAL_CLOSE: {role: acting_exposure, books: [specification]}
    US_SLEEVE_OFFICIAL_CLOSE: {role: acting_exposure, books: []}
    NAV_LINE_CLOSES: [{role: acting_exposure, consumer: nav, books: [recommended, specification], halt_after_consecutive_decisions: 3},
                      {role: forward_sim, consumer: nav, books: ["forward_sim:R-28", "forward_sim:R-29"]}]
    SPX_OFFICIAL_CLOSE: [{role: forward_sim, consumer: R-28_R-29, books: ["forward_sim:R-28", "forward_sim:R-29"]},
                         {role: risk_model, consumer: corr63},
                         {role: risk_model, consumer: korea_covariance, action: risk_model_covariance}]
    SOX_CLOSE: {role: risk_model, consumer: korea_covariance, action: risk_model_covariance}
    KODEX200_PDF: {role: acting_exposure, books: [recommended, specification], halt_after_consecutive_decisions: 5}
    KRX_MARKET_CAPS_005930_000660_KOSPI: {role: acting_exposure, books: [recommended, specification]}
    MOM_PAPER_LS_SERIES: {role: acting_exposure, books: [specification]}
    DM_MKT_RET_24M: {role: acting_exposure, books: [specification]}
    DM_MKT_VOL_126: {role: acting_exposure, books: [specification]}
    NON_KR_INDEX_MONTH_END_CLOSES: {role: forward_sim, books: ["forward_sim:R-28"]}
    USD_LIVE_PROXY: risk_model
    PCEPILFE: risk_model
    US10Y_KIS_QUOTE: [{role: risk_model, consumer: corr63}, {role: context, consumer: R-12_refusal_book}]
    DGS10: [{role: risk_model, consumer: corr63_backtests}, {role: context, consumer: R-12_refusal_book}]
    ASIA_INDEX_CLOSES: {role: risk_model, consumer: korea_covariance, action: risk_model_covariance}
    DTWEXBGS: context
    DEXKOUS: context
    ECOS_1530_CLOSE: [{role: context, consumer: R-11_refusal_book}, {role: forward_sim, consumer: nav_fx_backtests, books: ["forward_sim:R-29"]}]
    USDKRW_1530_SNAPSHOT: [{role: context, consumer: R-11_refusal_book}, {role: forward_sim, consumer: nav_fx, books: ["forward_sim:R-29"]}]
    BOK_CALL_RATE: history
    US_RF: history
  unscheduled_delay: event_status_delayed
```
Comments carried by the source: `KOSPI_OFFICIAL_CLOSE` and `MOM_PAPER_LS_SERIES` gain the recommended book while `verdict_filter` admits R-06 KR / R-03; vt enters the recommended book as 1.0 until then (L1919, L1929). `US_SLEEVE_OFFICIAL_CLOSE` has no book while `sleeves.US.line = none` (D5, L1920).

### C2. Artifact fields this area fills (schema owned by M0-08)

`macro_state.$defs.input` required (L3633-3634): `name, series_id, source, obs_date, session_date, obs_kind, value, value_status, dispute, available_at_utc, available_at_source, retrieved_at_utc, expected_available_utc, stale_deadline_utc, vintage, timing, role, books, status, content_hash` (+ optional `channel`). `timing` enum `live | publication | value_proxy` = registry `timing_class`.

`macro_state.lag_audit` (L3541-3547): `{checked: int >= 0, violations: [{series_id, obs_date, check, expected_usable_at_utc, stamped_available_at_utc}]}`.

`macro_state.runtime[]` (L3608-3623): `book_id, engine_state ∈ {DISARMED, ARMED, HALTED}, halt {class ∈ {RISK, OPS}, reason_code, component, series_id, since_utc, rearm_not_before, rearm_mode ∈ {auto, operator}, causes[], ack_by, ack_utc} | null, post_rearm_cap_until, nav, hwm_hard, ref_step, consecutive_failures {series_id: int}, book_counter`.

`macro_state.alerts[]` (L3625-3629): `alert_id, code, severity ∈ {info, warn, page}, component, series_id, books, first_seen_utc, count, escalated, ack_utc`. Also `macro_state.fail_closed`, `flags.hedge_reasons[] ⊆ {ok, risk_model_input_stale, risk_model_exception, corr_positive, core_pce_ge_3}`, `context_log.items[].stale` (L1946-1951).

`governance_event` (L4099-4110): required `schema, schema_version, event_id, utc, kind, book_id, rule_id, key, actor, reason, refs, prev_row_md5`; kinds used here: `halt, rearm, book_state, binding_change, calendar_change`; actor `runtime`.

`tests/fixtures/macro/MANIFEST.csv` columns (L6018): file, source, series, span, `retrieved_at_utc`, the `value_status` and `available_at_source` rule, md5, tests that read it (+ licence, owner, L6035).

### C3. Series registry (data-file source)

Role codes (L1396-1403): A = `acting_exposure`; R = `risk_model` (covariance-only → action `risk_model_covariance`); F = `forward_sim`; X = `context` (refusal book, display only); C = `context`; H = `history`; P = planned (not registered, no binding). All rows: `grace_publication_bdays: 1`. "id" column: S = id given by the spec, P = id proposed here (spec names the series but not an id).

Publication schedules (`schedule_id`; S = named in L1833 / L4167-4173, P = proposed):

| schedule_id | obs_calendar | `publication_schedule` | Usable at (lag) |
|---|---|---|---|
| `KRX_CLOSE` (P) | KRX | `close_print_bound_utc("KR", d)` (06:30:30Z today) | the decision of d itself; cross-market: bound + 60 s < decision |
| `NYSE_CLOSE` (P) | NYSE | `close_print_bound_utc("US", d)` (20:00:30Z EDT / 21:00:30Z EST) | US close of d; KRX close of K ≥ d + 1 calendar day |
| `<M>_CLOSE`, M ∈ JP, CN, HK, TW (P) | JPX, SSE, HKEX, TWSE | scheduled close + `calendars.<M>.close_print_bound_s` (0) | general cross-market rule |
| `FRED_H15` (S) | bond-market days for observations (F-14); FED for publication | `{calendar: FED, time: "16:15", tz: America/New_York}`, next Fed business day after D | first US / KRX close after the posting instant |
| `H10` (S) | FED | Monday 16:15 ET after the week; next Fed business day if a federal holiday | first KRX close after publication (normally Tuesday KST); first US close after it |
| `TREASURY_PAR` (S) | SIFMA | 18:00 ET on D (expected); logged posting time = `available_at_utc` | first close after the logged time (+1 business day, US close) |
| `VIXCLS` (S) | CBOE | official close 16:15 ET; FRED channel: logged `last_updated` (live), declared lag (history) | US close of D+1; KRX close of K ≥ D+1 |
| `BLS` (S) | release calendar | 08:30 ET on the release date; event `status` moves/removes it | first decision after release |
| `BEA` (P) | release calendar | per BEA calendar | first decision after release |
| `ECOS_1530` (S) | ECOS | 15:30 KST on K (15:00 before 2016-08-01) | value timing for the same-day KRX decision (labelled) |
| `KODEX_PDF` (P) | KRX | 08:00 KST on the next KRX session (default, judgment; measured in M1) | decision at close t reads the basket dated t−1 |
| `LIVE_QUOTE` (P) | venue | quote stamp ≤ the decision instant | same decision |
| `AS_POSTED` (P) | source | first-seen retrieval | first decision after it |
| `DERIVED` (P) | inputs | latest input `available_at_utc` | inputs' rules |

The `obs_calendar` of `TREASURY_PAR` (SIFMA), `BLS` and `BEA` is inferred; the spec lists the allowed calendar ids (L1390) without assigning them to these schedules.

Korea (L1405-1418):

| series_id | id | Source / channel | Freq | schedule | `value_status` rule | Role → bindings (consumer; books; halt_after) | Contract / notes |
|---|---|---|---|---|---|---|---|
| `KOSPI_OFFICIAL_CLOSE` | S | KIS Open API (KRX official), KRX marketplace primary; Yahoo `^KS11` secondary, reconciliation only | daily | `KRX_CLOSE` | `official_close` only from the KRX regular-session close field, retrieved ≥ bound + 10 min | A → `{role: acting_exposure, books: [specification]}` + recommended while admitted; no `consumer` key, so it binds every consumer (T-PROV-01 reads as `R-06`); 2 | `abs_daily_return_max` 0.30; tol 1 bp; `obs_kind: close`; `timing_class: live` |
| `KOSPI200_OFFICIAL_CLOSE`, `KRX_<code>_OHLCV` | P | same | daily | `KRX_CLOSE` | same | A in §4.2; no `roles` entry → dormant until a consumer binds | OHLC from the same field set (R-30) |
| `KRX_005930_OFFICIAL_CLOSE`, `KRX_000660_OFFICIAL_CLOSE` | P | KIS / KRX marketplace | daily | `KRX_CLOSE` | same | A (look-through caps) | tol exact; `adjustment_basis` declared |
| group `KRX_MARKET_CAPS_005930_000660_KOSPI` = `KRX_005930_MARKET_CAP`, `KRX_000660_MARKET_CAP`, `KOSPI_TOTAL_MARKET_CAP` | S group / P members | KIS / KRX marketplace | daily | `KRX_CLOSE` | KRX close | A → `{role: acting_exposure, books: [recommended, specification]}`; 2 | — |
| `KODEX200_PDF` | S | KIS or KRX (proposed) | daily | `KODEX_PDF` | basket as published | A → `{role: acting_exposure, books: [recommended, specification], halt_after_consecutive_decisions: 5}` | last basket carried, age printed, bound recomputed on current prices |
| group `NAV_LINE_CLOSES` = e.g. `KRX_069500_OFFICIAL_CLOSE` | S group / P member | KIS / KRX | daily | `KRX_CLOSE` | `official_close` | consumer `nav`: `acting_exposure` [recommended, specification], 3; `forward_sim` ["forward_sim:R-28", "forward_sim:R-29"] | `pit_value` never raises for `nav` |
| `KOSPI_NET_BUY_FOREIGN`, `_INSTITUTION`, `_INDIVIDUAL` | P | KIS investor flows (`kis_markets.py:L587-614`) | daily, final after close | after the close | preliminary intraday figures stamped with their own time | C | log from day one (BL-C06) |
| KRX margin debt; LETF AUM and value traded | — | KRX / KOFIA (new provider) | daily | per source | — | C once acquired; P until then (not registered) | BL-U01 |
| `ECOS_1530_CLOSE` | S | BoK ECOS 731Y003 item 0000003, from 1990-03-02 | daily | `ECOS_1530` | live: `inferred_from_retrieval`; history: `calendar_bound`, `timing = value_proxy` | X `{role: context, consumer: R-11_refusal_book}`; `{role: forward_sim, consumer: nav_fx_backtests, books: ["forward_sim:R-29"]}` | FX-regime metadata recorded with every KRW input |
| `USDKRW_1530_SNAPSHOT` | S | timestamped 15:30:00 KST snapshot (from 2026-07-06) | daily | `LIVE_QUOTE` | `live_snapshot`, `obs_kind: quote_snapshot` | `{role: context, consumer: R-11_refusal_book}`; `{role: forward_sim, consumer: nav_fx, books: ["forward_sim:R-29"]}` | never "the close" (L1305) |
| `DEXKOUS` | S | FRED, H.10, noon New York | daily obs, weekly publication | `H10` | `first_release`, `published` | `context` | labelled proxy; production never reads it |
| `BOK_BASE_RATE`, `KR_CPI` | P | BoK ECOS / KOSIS | event / monthly | release timestamp | — | C | — |
| `BOK_CALL_RATE` | S | BoK ECOS (code and item from the owner) | daily | release timestamp; obs_calendar ECOS | — | H → `history` | range group `KR_CALL_CD` [−1, 40]% |
| `KR_CD91` | P | BoK ECOS | daily | release timestamp | — | C | range group `KR_CALL_CD` |
| `VKOSPI`, `KOSPI200_MFIV_1530` | P | KRX; Derivatives page | daily | close | MFIV snapshot stamped `live` | C | never a sizing input (§10 item 30) |
| DART, KIND, index-change announcements | — | OpenDART; KIND; KRX / MSCI | event | filing timestamp | — | C (calendar flag) | event store, not a series |

United States (L1420-1440):

| series_id | id | Source / channel | Freq | schedule | `value_status` rule | Role → bindings | Contract / notes |
|---|---|---|---|---|---|---|---|
| `US_SLEEVE_OFFICIAL_CLOSE` | S | KIS quotes; FMP EOD history; Yahoo secondary | daily | `NYSE_CLOSE` | `official_close` | A → `{role: acting_exposure, books: []}` while D5 = none | dormant binding |
| `SPX_OFFICIAL_CLOSE` | S | same | daily | `NYSE_CLOSE` | `official_close` | F `{consumer: R-28_R-29, books: ["forward_sim:R-28", "forward_sim:R-29"]}`; R `{consumer: corr63}`; R `{consumer: korea_covariance, action: risk_model_covariance}` | — |
| CME E-mini / Micro E-mini S&P 500; KOSPI200 and mini front months | P | KIS read-only quotes (CME via KIS UNVERIFIED; `kis_markets.py:L13-15` records HTTP 500 for CME ES); fixed roll calendar | daily | venue close | — | F (R-29); A only for a futures-line card that passes | no continuous-contract returns across rolls |
| `VIXCLS`, `VXVCLS` | S | FRED (CBOE); Yahoo `^VIX`, `^VIX3M`; live snapshot 16:00 ET | daily | `VIXCLS` | 16:00 ET snapshot stamped `live` | C (R-08 annotation; R-13) | `VIXCLS: [5, 150]`; registry names the production channel of the R-08 annotation |
| `US10Y_KIS_QUOTE` | S | KIS US 10y yield quote stamped ≤ the US close (candidate `Y0202`, `kis_markets.py:L61`) | daily | `LIVE_QUOTE` | `live_snapshot` | R `{consumer: corr63}`; X `{role: context, consumer: R-12_refusal_book}` | production channel |
| `DGS10` | S | FRED, H.15 | daily | `FRED_H15` | `first_release` | R `{consumer: corr63_backtests}`; `{role: context, consumer: R-12_refusal_book}` | `US_TREASURY` [−1, 20]%; strict +2 business days (US close) |
| `UST_PAR_10Y` (`TREASURY_PAR`) | P | US Treasury CMT, posting time logged | daily | `TREASURY_PAR` | `first_release` | history channel of the US 10y | `US_TREASURY` |
| `^TNX` | S (ticker) | Yahoo | daily | live-feed proxy from 2015 | `vendor_close` | history proxy, labelled value timing | — |
| `DFII10`, `T10YIE`, `T5YIFR`, `DGS2`, `DGS30`, `T10Y3M`, `T10Y2Y` | S | FRED (H.15-based); Treasury par and real par for CMT legs | daily | `FRED_H15` or `TREASURY_PAR` | `first_release` | C | range-group membership: see F-12 |
| `THREEFYTP10` | S | FRED (Kim–Wright; never mixed with ACM) | daily, posted with a lag | `AS_POSTED` | — | C | — |
| `^MOVE` | S | Yahoo | daily | close | `vendor_close` | C | — |
| `DTWEXBGS` | S | FRED, H.10 | daily obs, weekly publication | `H10` | `first_release` | `context`; never acting | — |
| `USD_LIVE_PROXY` | S | default `DX-Y.NYB` (Yahoo, ICE US Dollar Index) | daily | `LIVE_QUOTE` | `obs_kind: quote_snapshot`, stamped ≤ the decision instant; a vendor daily "close" stamped after it is never used | R → `risk_model` (`hedge_state`) | named before M2 |
| `DEXJPUS` | S | FRED H.10; KIS or Yahoo live quote | daily | `H10` / live | — | C; P (FX sleeve) | — |
| `BAMLH0A0HYM2`, `BAA10Y` | S | FRED (HY OAS ≈ 1-day lag; on FRED only since 2023-10) | daily | next day | — | C (BL-C03) | — |
| `DCOILBRENTEU`, `BZ=F` | S | FRED/EIA spot; Yahoo ICE front month | daily | per source | — | C; Monte Carlo scenarios and replays | named-series guard; roll days |
| `PCEPILFE` | S | FRED + ALFRED vintages; first release (`output_type=4`) and current | monthly | `BEA` | `first_release` / `revised` with `vintage` | R → `risk_model` (core PCE YoY, `hedge_state`); C | monthly index |
| `PCEPI`, `CPIAUCSL`, `CPILFESL` | S | FRED / ALFRED | monthly | `BEA` / `BLS` | same | C | Oct-2025 CPI missing |
| `UNRATE`, `SAHMREALTIME`, `PAYEMS`, `ICSA` | S | FRED / ALFRED; Sahm also in-house | monthly / weekly | release time | first print, current value, vintage date | C | Oct-2025 household data missing; gap → NaN |
| `FEDFUNDS`, `DFEDTARU`; FOMC statements; SEP Table 2 | S | Fed; FRED | event | statement time 14:00 ET | — | Calendar; C; Monte Carlo priors | — |
| `USEPUINDXD` | S | FRED | daily | `AS_POSTED` | — | C | — |
| VRP inputs (VIX², 21-day realised variance) | P | derived in-house | daily | `DERIVED` | weakest input | C (R-13) | — |
| `US_RF` | S | French daily `RF` (as posted) or FRED `DTB3` (H.15; annual rate accrued act_365) | daily | `AS_POSTED` / `FRED_H15` | — | H → `history` | each card's `cash_convention.cash_series` names one |

Other (L1442-1449):

| series_id | id | Source | Freq | schedule | Role → bindings | Notes |
|---|---|---|---|---|---|---|
| Ken French factor files (US daily 5-factor, Mom, ST_Rev; regional Mom daily; monthly 1926+) | — | French Data Library | daily / monthly | `AS_POSTED` | H | frozen in fixtures, md5 per file; daily Mkt-RF from 1926-07 not yet acquired (HTTP 403) |
| `SOX_CLOSE` | S | KIS (US indices); Yahoo | daily | `NYSE_CLOSE` | R `{role: risk_model, consumer: korea_covariance, action: risk_model_covariance}`; C (opening-gap log) | carried stale ≤ 5 decisions, then dropped |
| group `ASIA_INDEX_CLOSES` = Nikkei, Shanghai, HSI, TAIEX (`NIKKEI225_CLOSE`, `SHANGHAI_CLOSE`, `HSI_CLOSE`, `TAIEX_CLOSE`) | S group / P members | KIS; Yahoo | daily | `JP_CLOSE`, `CN_CLOSE`, `HK_CLOSE`, `TW_CLOSE` | R `{role: risk_model, consumer: korea_covariance, action: risk_model_covariance}` | synchronous or lagged returns only |
| group `NON_KR_INDEX_MONTH_END_CLOSES` = S&P 500, Nikkei 225, HSI, DAX, FTSE 100, TAIEX (default set, L2994) | S group / P members | per index | month-end close | market close | F `{role: forward_sim, books: ["forward_sim:R-28"]}` | `session_date` = last session of the month (L2978) |
| `MOM_PAPER_LS_SERIES` | S | derived (R-03, M4) | daily | `DERIVED` | A `{role: acting_exposure, books: [specification]}` + recommended while admitted | — |
| `DM_MKT_RET_24M`, `DM_MKT_VOL_126` | S | derived (R-04, M4) | — | `DERIVED` | A `{role: acting_exposure, books: [specification]}` | — |
| Release and holiday calendars | — | official notices | event / effective-dated | — | Calendar (`core/calendars`) | not series |

Fixture-only vendor series (history channels; L5715, L6018): Yahoo `^KS11`, `^GSPC`, `SPY`, `KRW=X`, `^TNX`, `^RUT`; FRED `NASDAQ100`; FRED `IRSTCI01KRM156N` (PX2 cash fixture).

Range groups: `US_TREASURY`, `KR_CALL_CD` (members declared in the registry, L1891).

---

## D. Tests

Feasibility: SYNTH = hermetic with inline or synthetic fixtures; REFDATA = needs frozen reference data absent from this machine; OWNER = needs owner input, credentials or live sessions. All tier `fast` unless noted. §9.1 rows govern over the §9.0 council wording (L5505).

| Test | M1 assertion (exact) | Fixture | Class |
|---|---|---|---|
| T-PROV-01 (L5612) | Store rows: vendor 6,943.66 (`obs_utc` 01:30Z, `available_at_utc` 01:30Z, `retrieved_at_utc` 01:56Z, `provisional_intraday`); KIS 7,003.74 (`available_at_utc` 06:30:30Z `calendar_bound`, `retrieved_at_utc` 06:40:45Z, `official_close`). `pit_value('KOSPI_OFFICIAL_CLOSE', decision_utc=2026-10-02T06:30:30Z, knowledge_utc=…, consumer='R-06', require_session=2026-10-02)` = `MissingInput("missing")` at 01:31Z, `MissingInput("provisional_intraday")` at 02:00Z, 7,003.74 `[official_close]` at 07:00Z. Cache regression (M1-12): same answers with the 10:56 KST row in the cache | synthetic store file, labelled, exempt from the post-close rule | SYNTH |
| T-FIX-01 (L5613) | A fixture any of whose close-type rows has `retrieved_at_utc < close_print_bound_utc(session) + 10 min`, or any publication-timed row retrieved before its `publication_instant`, is refused | inline good / bad fixtures | SYNTH |
| T-FIX-01, regeneration clause | DLA §7 corrected values regenerate at Level-1 tolerance | `/home/claude/quantgen_macro_data/` | REFDATA |
| G-POST-01, M1 rows (L5572, L5819-5834) | KOSPI close 2 Oct 7,003.74; return +0.46%; drawdown from the 9,114.55 peak −23.2% (−23.16%); close / 200-day 1.107; Samsung / SK hynix ₩276,000 / ₩1,841,000; KRW=X last row 1,356.84 (1 Oct), 20-observation change −0.11%, provisional 2-Oct row dropped. Level 1: prices exact, max DD ±1 pp, window returns ±1 pp, other ratios ±0.01 (L5734-5735) | Yahoo `^KS11`, `005930.KS`, `000660.KS`, `KRW=X` post-patch files; `QX_DLA_postpatch.csv`. Local cache has no `^KS11`, `000660`, `KRW=X`, and `yf_005930.KS.csv` ends 2026-09-23: no substitute. Only the drawdown identity 7,003.74 / 9,114.55 − 1 = −23.16% is checkable inline | REFDATA |
| G-POST-01, other rows | rv20, vt, G-KR-01/02/02b → M2; G-B5-01 → M3; pair share → M5; R-06 KR p_ni, ΔSR → M7; G-KR-05 → M8 (L5573-5577) | — | deferred |
| T-BAR-01 (L5614) | A bar-derived close, or a flat-OHLC zero-volume row on a session day, is never stored as a close; mismatch > 1 bp (index) or any (stock) → `disputed`, official value used, alert; nothing auto-corrected. R-27 clause → M5 | inline rows | SYNTH |
| T-BAR-02 (L5615) | Disputed official close → `PITValue`, `dispute = true`, status `disputed`, passes the provisional guard, alert, no failure counter increment; vendor row absent on a KRX session → `vendor_missing` | inline rows | SYNTH |
| T-PRINT-01 (L5631) | KOSPI close 2026-03-09 = 5,251.87 (−5.96%); the intraday −8.11% is never stored as a close | inline rows (official close + 10:31 print); real `^KS11` not local | SYNTH (logic); REFDATA (real file) |
| T-CLOSE-01, data clauses (L5617) | Print time 06:30:20Z accepted; `available_at_utc` 06:31Z rejected; receipt time only in `retrieved_at_utc`; official close retrieved 06:45Z without print time stored with `available_at_utc` 06:30:30Z `calendar_bound` and accepted; KIS close row retrieved 06:40:29Z never `official_close` (read returns `MissingInput`), 06:40:30Z is; US close stamped 20:00:02Z accepted for 2026-10-01. "Workflow never starts before 06:40:30Z" → M8 | inline rows + calendar functions | SYNTH |
| T-SER-01 (L5629) | Unnamed "Brent" raises; BZ=F roll day 2026-04-01 (−14.5%) flagged and excluded from return computations | inline BZ=F rows; local cache has `yf_CL_F.csv`, not BZ=F | SYNTH |
| T-SER-02 (L5630) | Every series id referenced by the rules store, `data_contracts.roles`, card headers and §4.2 exists with a contract; unknown id fails; group and range-group names resolve to existing members; a group name used as a series id fails; `pit_value` raises for a non-context consumer with no binding | registry file | SYNTH |
| T-SYN-01 (L5611) | `auto` provider degrading to labelled synthetic for an acting input → `MissingInput`, `status = "synthetic_rejected"`, `fail_closed = true`; same provider for a context item allowed and labelled | existing `_no_network` pattern (`tests/ficc_acceptance.py:L31-41`) | SYNTH |
| T-MISS-01 (L5624) | CPI YoY Aug-2026 = 3.353% ± 0.01; positional 3.713% not produced; YoY for Oct-2025 and Oct-2026, MoM for Oct and Nov 2025, Sahm 3-month means NaN and flagged; Aug-2026 endpoint YoY computed; vendor value across the gap tagged `vendor_derived_across_gap` | logic: inline monthly index with Oct-2025 absent. Real values: FRED `CPIAUCSL`, `UNRATE`, `SAHMCURRENT` snapshot of 2026-10-02 (not local) | SYNTH (logic); REFDATA (3.353 on real data) |
| T-MISS-02, acting clauses (L5625) | Acting input missing or stale → state unchanged, `fail_closed = true`, alert, no interpolation; same failure for more than one decision → HALTED. Risk-model and risk-layer exception clauses → M2 / M5 | synthetic store + books | SYNTH |
| T-STALE-01 (L1963, L5620) | Decisions 2016-01-04 → 2026-09-25, US and KRX closes. (a) without the list DTWEXBGS and DEXKOUS stale on ≤ 1% (0.42–0.89% expected) and every hit's `d_next` is in the source-skipped list; (b) with the list no flag; (c) DGS10 strict H.15 ≤ 1% (0.33%), VIXCLS 0%; (d) deleting one H.10 release flags the next decision after the grace; (e) negative control ≈ 80% (79.8%) must not be what the code does | FRED snapshot (DTWEXBGS, DEXKOUS, DGS10, VIXCLS) + official calendars 2016–26. Local substitute for DEXKOUS only: `docs/asset_expansion/cache/fred_DEXKOUS.csv` (2017-01-02 → 2026-09-18), weekday US-close grid, rule-based federal holidays: probe gave (a) 12 / 2,529 = 0.47%, `d_next` ∈ {2017-01-20, 2020-11-27, 2020-12-24}; (b) 0; (e) 79.8%; (d) week of 2024-03-04 deleted → first flagged decision 2024-03-13 | REFDATA (full); local substitute covers DEXKOUS clauses a, b, d, e |
| G-STALE-01 (L5901-5908) | DTWEXBGS 100.0% / 98.6% ("1 trading day"), 100% / 100% ("3 days"), 0.89% / 0.80% schedule-aware, age 6 / 12; DEXKOUS 100.0% / 98.6%, 100% / 100%, 0.52% / 0.42%, 6 / 12; DGS10 strict 99.52% / 95.9%, 42.0% / 42.4%, 0.33% / 0.34%, 2 / 5; VIXCLS 0.0% / 2.1%, 1.9% / 2.0%, 0% / 0%, 1 / 4 (US close / KRX close) | as above + `results/QX_DLA_staleness.csv` | REFDATA |
| T-ROLE-01, M1 clauses (L1964, L5621) | Stale acting input → `fail_closed = true`, alert, state unchanged: miss 1 → fail closed; miss 2 → its bound books HALTED (OPS) and no other; a fresh decision resets the counter and re-arms; two acting inputs bound to one book failing on alternate decisions HALT it at the 2nd decision; unreadable publication calendar fails every acting input closed; stale context input → label only. Risk-model clause and "sets every risk-model default" → M2 | synthetic store + books | SYNTH |
| T-ROLE-02, M1 clauses (L1969) | Dec-1997 Korean call rate passes `KR_CALL_CD` [−1, 40]%; an acting or forward_sim binding without a `books` key refused at registration; `books: []` valid and binds no book. corr63 clause → M2; missing cash day → M7; FORWARD-SIM clause → M8 | inline value in the 16–25% band (real series needs the owner's ECOS code) | SYNTH |
| T-H10-01 (L5632) | `run_mode = live`: reading DEXKOUS for an acting or risk-model input raises | registry | SYNTH |
| T-H10-02 (L1966, L5633) | DEXKOUS dated Fri 2026-09-25 usable from the KRX close of Tue 2026-09-29 and not before; at the 2026-10-02 KRX close the latest usable DEXKOUS is dated 2026-09-25; week of 2026-10-05 usable from the KRX close of Wed 2026-10-14 (Columbus Day) | calendar functions (KRX 2026 holidays exist in `data/calendars/KRX.json`) | SYNTH |
| T-H15-01 (L1965, L5634) | DGS10 dated D available 16:15 ET on the next Fed business day; Fri 2015-01-02 → KRX close Tue 2015-01-06, not Mon 2015-01-05; DGS10 dated 2026-10-09 → US close 2026-10-14; Treasury channel with a logged posting time usable +1 business day; flag first on in data dated 2026-09-23 earns in the strict book from 2026-09-28 | inline calendar rows for 2015 (repo calendars cover 2026–27 only) | SYNTH (inline calendar); OWNER (signed files) |
| T-VIX-01 (L5635) | Production channel: VIX(D) read at its 16:15 ET close not usable at the US close of D; usable at the US close of D+1 and the KRX close of K ≥ D+1; FRED `VIXCLS(D)` usable from the first decision after the logged (live) or declared (history) FRED posting time | registry channel rules | SYNTH; measured lag OWNER (20 sessions) |
| T-XMKT-01 (L1967) | Non-CSAT D ≥ 2024-11-05: same-date TSE close not usable at the KRX close; 2016-08-01 … 2024-11-04 usable; before 2016-08-01 not; CSAT 2025-11-13 at 07:30:30Z: TSE (06:30Z) and Shanghai (07:00Z) usable; pre-2016 CSAT with the configured 16:00 KST close: TSE usable, Shanghai not; same-date TAIEX usable at every weekday KRX close; same-date HKEX never | effective-dated close times | SYNTH; signed SSE / HKEX / TWSE times OWNER |
| T-TZ-01 (L5622) | KOSPI return dated 2026-10-02 → latest usable US close dated 2026-09-30; dated 2026-10-01 → 2026-09-29; NYSE close 2026-01-15 → 06:00 KST 2026-01-16; 2026-07-15 → 05:00 KST 2026-07-16; 2006-03-20 → 21:00Z; 2006-04-03 → 20:00Z | zoneinfo | SYNTH |
| T-LAG-01, M1 clauses (L5609) | Datum with `available_at_utc > decision_utc` in any acting input → backtest raises `LookAheadError`; at runtime the books it feeds go HALTED (OPS); a provisional row is treated the same way; the audit recomputes `usable_at` independently of `pit_value`. Card-refusal clause and `timing_probe` exception → M7 | synthetic store + books | SYNTH |
| T-LAG-02, M1 clause (L5610) | Positional `shift` on a series with gaps rejected by the linter / audit. "Must change the result" on vt → M2; `timing_probe` → M7 | inline gapped series | SYNTH |
| T-AVAIL-01 (L5619) | Exact: DGS10 Fri 2015-01-02 → KRX Tue 2015-01-06; DEXKOUS week of 2026-10-05 → KRX Wed 2026-10-14; DGS10 2026-10-09 → US close 2026-10-14; CSAT 2025-11-13 close 07:30Z; fails on an injected registry error (e.g. H.15 posted at D, not D+1) | calendar functions + registry | SYNTH (inline); OWNER ("built from official calendars") |
| T-SAT-01, completeness clause (L2097) | Every `is_session` date of the KRX official-close fixture has exactly one close row; Monday / Tue–Fri variance ratio 2.30 in 1997–98 printed | KRX official KOSPI closes from 1997-01-03 with Saturdays | REFDATA + OWNER |
| T-RO-02 (L5606) | KIS client accepts only the allowlisted quotation endpoints; any trading or account path raises before a request is built; Claude API called without tools, text never parsed by an acting module | patched transport asserting zero calls | SYNTH |
| T-RO-02, record clause | Whether the app key can trade is checked beside the quote-field check and recorded | owner attestation, 20 live sessions | OWNER |
| T-RO-02, I-01 transport clause | zero non-allowlisted requests recorded | — | deferred M8 |
| T-CAL-01 (M1-23) | A changed bound or schedule enters only as a signed calendar version; an unsigned file is refused and KR acting inputs fail closed | inline unsigned file | SYNTH |
| T-HEDGE-01, R-19 table (L1968) | Stale DTWEXBGS alone changes no hedge flag; live USD proxy and DTWEXBGS both stale → `hedge_credit_off = TRUE`, no acting component fails closed, vt unchanged | — | deferred M2 (built `macro_state` M6) |
| T-HERM-01 / -02 (L5607-5608) | Every new provider function patched to raise; tests write only to temporary copies | — | SYNTH (binds every row) |

Scratch probe behind the T-STALE-01 local numbers: `scratchpad/m1pit/stale_probe.py` (not repo code).

---

## E. Interfaces

Needs from M0:

| From | What |
|---|---|
| M0-05 | rules-store accessor for `data`, `data_contracts`, `time`, `calendars` blocks |
| M0-07 | `governance_events.jsonl` appender (kinds `halt`, `rearm`, `book_state`, `binding_change`) |
| M0-08 | `macro_state.v2.0` schema (`$defs/input`, `lag_audit`, `runtime`) |
| M0-11 | artifact writer; it holds a `data_snapshot_id` stub that M1 replaces |
| M0-02 / M0-03 | hermetic harness with a `runs_from` registry; MANIFEST loader with md5 check |

Needs from the calendars brief (R-20; L1024-1041, L1991-1996):

```python
decision_time_utc(market, session_date) -> datetime        # scheduled close; raises NotASession
close_print_bound_utc(market, session_date) -> datetime    # decision instant
is_session(market, date); session(market, date)
fed_business_day(date); sifma_status(date); nyse_holiday(date)
publication_instant(series, obs_date) -> datetime
next_expected_obs(series, obs_date) -> date                # skips source-exception dates
add_publication_bdays(series, instant, n) -> datetime
usable_at(series_id, obs_date, market) -> datetime         # first decision_utc that may use it
```
A missing or unsigned calendar version must surface as an exception this area turns into "every acting input of that market fails closed" (L2088).

Repo state the calendar functions start from: `data/calendars/*.json` cover 2026-01-01 → 2027-12-31 (SSE → 2026-12-31), hold holidays and two KRX late-open days only (no CSAT session, no effective-dated close times, no FED / SIFMA / ECOS sets); `core/calendars.is_trading_day` returns `None` outside coverage (`core/calendars.py:L144-154`). Availability tests on 2015–2025 dates therefore need inline calendar rows or the signed files.

Exposes to later milestones:

| Consumer | Uses |
|---|---|
| M2-01 `market_vol_target`, M2-04 `hedge_state` | `pit_value`, `MissingInput`, counters, warm-up rule, `on_input_failure` risk-model default, derived records |
| M2-08, M7-02 | generated fixtures and MANIFEST |
| M3-01 | OHLC rows, open-quality flag, stale-carry flag |
| M4-03 / M4-04 | `put_derived` for `MOM_PAPER_LS_SERIES`, `DM_MKT_RET_24M`, `DM_MKT_VOL_126` |
| M5-01, M5-03, M5-07, M5-10, M5-11 | `KODEX200_PDF` binding and carry; per-book runtime (RISK class added on top); VIX channel; bar convention |
| M6-02 | stale labels, vintages, first prints for `context_log` |
| M7-09, M7-12, M7-13 | `history` role and span coverage; `lag_audit`, `LookAheadError`, `timing_probe` exception hook |
| M8-01 | `macro.pit_snapshot`, `data_ok`, `macro.lag_audit` steps; `RunContext`; `data_snapshot_id`; derived bindings from `verdict_filter` |
| Tech-fund data layer (R3 §5.1, L146-165 of `R3_TF_neural_link.md`) | same store for DATA-4: OpenDART usable from the close of `rcept_dt` + 1 session with first-filed values; EDGAR acceptance ≤ 15:30 ET usable at close d, else d+1; DATA-6 investor flows logged with timestamps (XS-01) |

---

## F. Ambiguities, contradictions, conservative readings

| # | Issue | Lines | Reading taken |
|---|---|---|---|
| F-1 | Spec places code "inside the existing package" `core/ficc/data` and data under `core/calendars/data/`; both are single modules in the repo | L906, L1990; `core/ficc/data.py`, `core/calendars.py` | Sibling modules (B0); calendar data location is the calendars brief's call; config path values kept as keys, resolved by the loader |
| F-2 | Per-book runtime needs automatic arming and automatic OPS re-arm; the existing engine state machine never re-arms itself and restarts DISARMED | L1179-1180; `core/engine/state.py:L10-13,L141-149` | New per-book structure; existing `EngineState` and its acceptance checks untouched |
| F-3 | "Whether the KIS app key can trade is checked" cannot be probed without calling a trading or account path, which the guard and P0 forbid | L5606, L491-492 | Owner attestation recorded in the check record; code never calls a non-allowlisted path; default `"unknown"` |
| F-4 | The KIS field that carries the KRX regular-session official close is UNVERIFIED until M1-01; NXT trades from 15:40 KST, the same instant as close + 10 min | L1496 | Until a signed registry revision names the field, live KIS rows are not stamped `official_close` (fail closed); KRX marketplace rows may be. Hermetic tests use synthetic rows |
| F-5 | `obs_kind` of a pre-quarantine vendor row is not stated ("never stored as a close"; T-PROV-01 gives only `provisional_intraday`) | L1323, L5612 | `obs_kind = "quote_snapshot"`, `value_status = "provisional_intraday"`, same `series_id`; "close-type" is decided by the registry's `obs_kind` |
| F-6 | `content_hash` composition and the join used for `data_snapshot_id` are not given | L986, L1014 | md5 of canonical JSON of the `dedupe_key` fields; snapshot = md5 of `"\n".join(sorted(hashes))` |
| F-7 | `MissingInput.reason` for a range, schema or monotonicity violation is not in the 5-value enum | L993, L1882 | `"missing"` |
| F-8 | HALT threshold wording: "reaches" N vs "more consecutive decisions than its declared limit" vs "beyond its 5 misses" | L1870, L1178, L5674 | HALT when the counter equals N (2nd, 3rd, 5th miss): the earlier, fail-closed reading |
| F-9 | `on_input_failure(series_id, check)` has no binding argument although actions are per (series, consumer, books) | L1826, L1891 | Add the binding (or the `MissingInput`) as a parameter |
| F-10 | "A series with no binding may be read only by a `context` consumer" needs a way to tell consumer kinds; a scalar `roles` entry binds every consumer, so T-H10-01 does not follow from bindings alone | L1105, L1891, L5632 | Registry declares `consumers: {name: kind}`; unknown consumer = non-context → raises; DEXKOUS in live mode raises for any non-context consumer |
| F-11 | No named wrapper combines `pit_value`, the contract check and `is_stale`; `MissingInput("stale")` has no stated producer | L993, L1108, L1202-1205 | One read helper in `core/ficc/contracts.py` returns `PITValue | MissingInput`; it is what `data_ok` calls in M8 |
| F-12 | Range units: core uses decimals, ranges are in percent, FRED arrives in percent. `US_TREASURY: [-1, 20]` membership is undeclared; 10-year TIPS yields have printed below −1% (analyst recollection, not in the sources) | L373, L1393, L1916; `core/ficc/data.py:L20-22` | Store source units, declare `unit` in the contract, apply ranges in that unit; `US_TREASURY` = nominal yields only (DGS*, DTB3, par yields); DFII10 and spread series outside it |
| F-13 | The source-exception list is given as one list, but H.10 and H.15 skip different dates. Local `fred_DEXKOUS.csv` has values on 2018-03-02 and on Good Fridays, and is blank on 2018-12-24, 2019-01-14, 2019-02-20, 2021-01-20, which the list omits | L1854 | Key the list per schedule; owner signs the additions. Mid-week H.10 gaps never become `d_next` (the week publishes at once), so they change no staleness result |
| F-14 | Observation calendars differ by release. Local H.10 file (`fred_DEXKOUS.csv`): no observation on the Friday before a Saturday holiday (2017-11-10, 2020-07-03, 2021-12-24, 2021-12-31, 2023-11-10, 2026-07-03). Local H.15 file (`fred_DGS3MO.csv`): values on 2017-11-10, 2021-12-31, 2023-11-10, 2016-01-22, 2018-03-02, 2017-01-20, 2020-11-27, 2020-12-24; blank on 2020-07-03, 2021-12-24, 2026-07-03, 2018-12-05, 2019-04-19 | L1390, L1994, L2024 | Registry `obs_calendar` is per schedule: H.10 = FED with federal observance (Saturday → Friday, Sunday → Monday); H.15 = bond-market days. With the Reserve-Bank rule for H.10 the probe shows 1.27% hits, above the 1% bound. Owner signs both sets (same finding in `spec_M1_calendars.md` F rows 6-7) |
| F-15 | Lag-audit HALT needs an operator re-arm at M1 (task M1-20) while §12 says M5 adds the operator re-arm cases | L1179, L6363 | M1 keeps the book HALTED with `rearm_mode: operator` and provides `runtime_rearm(…, "operator")` |
| F-16 | Book counter counts only inputs "with the default limit"; reason code for a book-counter HALT is not given | L1869-1870, L1951 | KODEX200_PDF and NAV_LINE_CLOSES misses do not feed the book counter; reason code names the input failing at the HALT decision |
| F-17 | DISARMED → ARMED requires inputs "past warm-up" before any factor exists | L1180 | In M1 a book arms when every bound acting input is fresh and calendars cover ≥ 60 sessions; warm-up joins with M2 |
| F-18 | `KISMarkets.continuous_futures` builds a ratio-adjusted continuous series; `load_history` routes `=F` tickers to Yahoo continuous contracts | L1378, L6149; `data/kis_markets.py:L291-317` | Display paths only; no registry binding; card and book paths use the fixed roll calendar |
| F-19 | §9.0 words T-PROV-01 as `provisional_intraday` at 10:31 KST and T-FIX-01 as "last row"; §9.1 says `missing` at 10:31 and "any close-type row" | L5509 vs L5612-5613 | §9.1 governs (L5505) |
| F-20 | Reference data under `/home/claude/quantgen_macro_data/` is absent, so the golden fixtures and their md5s cannot be produced | L22, L5492 | Build generator and validator; register REFDATA tests as not run (never as passed); no golden value is restated from memory |
| F-21 | VIX production channel for the R-08 annotation is "named in the registry" but not chosen | L1426 | FRED with logged posting time; until 20 sessions are logged, usable no earlier than the US close of D+1 |
| F-22 | T-SER-02 scans card headers, which exist from M7 | L5630 | Scan what exists at each milestone |
| F-23 | ECOS access (key name, endpoint) and the Treasury endpoint are not specified; `.env.example` has no ECOS key | L1414, L1427 | New env var by the existing `_clean` pattern (`config.py:L33-40`); absent key → provider unavailable, explicit read raises |
| F-24 | `data.ingest.decision_deadline: next_session_open_minus_30min` and the retry ladder are "default, judgment" and need a scheduler | L4201-4203 | M1 ships the single-shot ingest; scheduling arrives with M8 |
| F-25 | The §6.1 example stamps a DEXKOUS row retrieved on 2026-10-02 (published 2026-09-28) `available_at_source: "published"`, while §4.1 says a row fetched after its publication window is `calendar_bound` | L3665-3667 vs L1278 | `published` only when the source supplies the publication time (exchange print time, FRED `last_updated`, a release timestamp); an instant computed from the registry schedule is `calendar_bound`. Both values pass the schema enum |

---

## G. DO-NOT-BUILD and invariants binding this area

| Item | Rule | Line |
|---|---|---|
| P0, §10 item 21 | No order, cancel, withdrawal, deposit-address or transfer path; KIS read-only; no broker execution adapter | L491-492, L6162 |
| §10 item 19 (`harm · G`) | No Yahoo continuous-futures returns across rolls; no unnamed "Brent"; no intraday circuit-breaker print as a close; no positional lags on monthly series with gaps; no H.10 / H.15 data used as if same-day; no US-session data on same-date KOSPI close-to-close returns; no provisional, intraday or bar-derived row as an acting close | L6148-6155 |
| §10 item 26 | Value-timing series must be labelled VALUE or NON-COMPLIANT; a production rule may not read the published series in their place | L6182 |
| §10.3 | "A production rule reading a value-timed or unpublished series; a provisional or bar-derived acting close" is refused (T-LAG-01, T-PROV-01, T-BAR-01) | L6250 |
| P5 | `available_at_utc <= decision_utc`; lags calendar-based; nothing silently interpolated; staleness against the publication schedule, never the observation's age | L536-550 |
| P16 | Nothing may freeze or quietly shrink the book: staleness is schedule-aware and role-based; a HALT is scoped to its book | L636-641 |
| P18 | No acting decision on a provisional, intraday, bar-derived or stale input; only `acting_exposure` inputs can escalate to HALTED and only for bound books; a `risk_model`, `context`, `forward_sim` or `history` input never HALTs a recommended book | L648-651 |
| Store | Append-only; rows never mutated; a close is never re-stamped; never auto-correct a dispute | L1282, L1311, L1322 |
| Knowledge time | `knowledge_utc` never "now" | L1001-1003 |
| Cache | Never holds derived values of acting inputs; a failed re-fetch is `MissingInput`, never the cached row | L1283 |
| Outage | Official-source outage: fail closed, never a vendor intraday print | L1496 |
| Calendar | Publication calendar unreadable: fail closed; never observation-age staleness | L1956 |
| DTWEXBGS, DEXKOUS | DTWEXBGS is never an acting input; production never reads DEXKOUS | L1368, L1414, L1886 |
| Access path | Every function reads data only through `pit_value`; no function reads a raw DataFrame of a series directly | L1105-1106 |
| Tests | Hermetic; no production state written; fixtures from post-close files only | L5491-5495 |
| Credentials | Env-only | L1253 |
| Tech-fund TF-01 | Fills and closes never use NXT or after-hours prints | `R3_TF_neural_link.md` L132 |
| Tech-fund TF-03 | Eligibility and universe screens on data up to t−1; corporate-action-adjusted returns with \|dln shares\| > 1% flagged; monthly timing on month-end prices | `R3_TF_neural_link.md` L146 |
