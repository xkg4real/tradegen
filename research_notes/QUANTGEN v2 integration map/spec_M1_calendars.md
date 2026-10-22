# spec_M1_calendars — R-20 effective-dated calendars, regime tags, publication calendars, cross-market availability (QUANTGEN v2.0, milestone M1)

Reference conventions used below
- `S:n` = line n of `QUANTGEN_Quant_Council_2026-10-03/claude_code/QUANTGEN_MACRO_INTEGRATION.md` (6,479 lines).
- `T:` = task id in `QUANTGEN_V2_TASKS.json`. `BL:` = `QUANTGEN_MACRO_BACKLOG.md` line. `TF:` = `QUANTGEN_techfund_research/research_notes/R3_TF_neural_link.md` line.
- `XC` = cross-check run on this machine on 2026-10-05 against the locally installed `exchange_calendars 4.13.2` (a dev-only dependency, `requirements-dev.txt`). The spec forbids it as a source ("`exchange_calendars` XKRX serves as a cross-check only, never as the source", S:2003). XC facts below are evidence for the owner, never values to sign on the owner's behalf.
- `LC` = evidence from local cache files under `docs/asset_expansion/cache/`.
- Everything under `/home/claude/...` is absent on this machine.
- "(proposed)" = name or location chosen in this brief; the spec allows renaming ("Rename them to match the codebase if necessary", S:963) but binds semantics.

---

## 0. What exists today (repo facts the build must respect)

| Item | Fact |
|---|---|
| `core/calendars.py` | A single **module** (200 lines). API: `get(market)`, `loaded_markets()`, `is_trading_day(market, day) -> True/False/None` (None = outside coverage), `special_session(market, day)`, `coverage(market)`, `stale_markets(today, within=60 days)`, `summary()`, `reload()`, dataclasses `SpecialSession`, `MarketCalendar`. Reads `data/calendars/*.json` (`DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "calendars"`). |
| `data/calendars/*.json` | 22 venue files + `index.json`, generated 2026-08-18 from `exchange_calendars 4.13.2`. Shape: `{market, timezone, source{library, version, calendar, generated}, covers{from,to}, regular{open,close,break_start,break_end}, holidays[], special_sessions{date:{open,close}}}`. Coverage 2026-01-01 → 2027-12-31 (SSE, SZSE, SGX, NSE end 2026-12-31). No `signed_off_by`, no effective-dated rows, no history before 2026. |
| `data/calendars/KRX.json` | holidays include 2026-10-05, 2026-10-09; special sessions only `2026-01-02` and `2027-01-04` (10:00 open). **No CSAT day** (the library carries CSAT rows only through 2020-12-03, XC). 2025-11-13 is outside coverage. |
| `data/calendars/US.json` | early closes 2026-11-27, 2026-12-24, 2027-11-26 at 13:00; 2025-07-03 is outside coverage. |
| `core/markets.py` | Venue table keyed by **venue code** (`KRX`, `US`, `TSE`, `HKEX`, `SSE`, `SZSE`, `TWSE`, …) with a dataclass named `Session(tz, windows, days, max_age_open_s, max_age_hard_s)` holding today's hours as constants (KRX 09:00–15:30; TSE 09:00–11:30 / 12:30–15:30; SSE …–15:00; HKEX …–16:00; TWSE 09:00–13:30). `Market.trading_state()` combines it with `core.calendars`. |
| Callers of the legacy API | `core/markets.py`, `core/engine/runtime.py:173` (`calendars.stale_markets()`), `ui/trading_page.py:372-385`, `tests/engine_acceptance.py` tests 69–75 (test 74 asserts `source.library == "exchange_calendars"` for every loaded market; test 71 asserts `is_trading_day` returns `None` beyond coverage). These are part of the 266 checks and must keep passing. |
| v2 functions | None exists: no `decision_time_utc`, `close_print_bound_utc`, `NotASession`, `regime_tags`, `usable_at`, `publication_instant`, `fed_business_day` anywhere in `*.py`. "API unchanged from v1.2" (S:1991) refers to the v1.2 specification, not to code. |
| `config.py` | Holds no decision-time constant (grep for `15:30`, `06:30`, `KST`, `decision` finds nothing). "The decision constants become calendar lookups" (S:1998) therefore means: add none. |
| Libraries | Python 3.13.14; `zoneinfo` + `tzdata` available; `PyYAML 6.0.3` is a declared dependency; `jsonschema` is not installed; `pandas` available. `pkg_tools/generate_calendars.py` (named in the legacy docstring) is not in the repo. |
| Note folder | `research_notes/QUANTGEN v2 integration map/` was empty before this file. |

---

## A. Scope

| Task | One-line deliverable | Target files (existing = E, proposed = P) |
|---|---|---|
| T:TASK-M1-03 (R-20 rules 1–3) | Effective-dated market clocks: `decision_time_utc`, `close_print_bound_utc`, `is_session`, `session`, `nyse_holiday`; `NotASession`; KR, US, JP, CN, HK, TW | `core/calendars/` package (P; converts E `core/calendars.py`), `core/calendars/clocks.py` (P), `core/calendars/data/*.yaml` (P), `core/markets.py` (E; market-id ↔ venue map only), `config.py` (E; no constant added) |
| T:TASK-M1-04 (R-20 rules 4–5) | `regime_tags(market, d) -> dict` from the owner-signed Korean regime-tag file; raise outside coverage; refuse a card whose span is not covered | `core/calendars/regime.py` (P), `core/calendars/data/kr_regime_tags.yaml` (path verbatim, S:2075), `tests/fixtures/macro/kr_regime_tags_expected.csv` (P) |
| T:TASK-M1-05 (R-20 rule 6, fail-closed) | Change control (unsigned file refused at load; every acting input of that market fails closed; governance event per change; one test per change) and the 60-session coverage horizon (warn 60, page 20, outside → OPS HALT `calendar_coverage`) | `core/calendars/store.py` (P), `core/calendars/data/MANIFEST.yaml` (P), hook into `core/engine/runtime` (owned by T:TASK-M1-20) and the M0 governance appender (T:TASK-M0-07) |
| T:TASK-M1-06 (R-19 rule 2, R-20 rule 2, §4.1) | Separate holiday sets; `fed_business_day`, `sifma_status`, `publication_instant`, `next_expected_obs`, `add_publication_bdays`; owner-signed source-exception list; US event instant → KST → next KRX session (`kr_open_gap_session`) | `core/calendars/publication.py` (P), `core/calendars/data/source_skipped.yaml` (path verbatim, S:1902), `core/calendars/data/holidays_<SET>.yaml` (P), `core/calendars/data/publication_schedules.yaml` (P) |
| T:TASK-M1-18 (calendar half) | `usable_at(series_id, obs_date, market) -> datetime`; the general cross-market rule `close_print_bound_utc(M, D) + 60 s < decision_utc`; D ≤ K − 1 for US-dated data at KRX decisions | `core/calendars/publication.py` (P); `core/ficc/data.usable_cross_market` is the data brief's |
| T:TASK-M1-19 (calendar half) | The bound used to stamp `available_at_utc` (`calendar_bound`) and as the lag-audit instant | consumes `close_print_bound_utc`; store logic is the data brief's |
| T:TASK-M1-23 (spike) | Record the M1 measurements as signed calendar or registry revisions (KRX and NYSE 30 s print bounds; FRED VIX posting lag; KODEX 200 basket publication instant) | data-file revisions only; OWNER (live sessions, KIS credentials) |
| §6.3 `event_calendar` | Schema recorded in section C3. The event store, window generator and artifact are M5 (T:TASK-M5-08, T:TASK-M5-09). M1 builds only the instant → KST → next-KRX-session mapping that T-TZ-02 asserts. | `core/calendars/clocks.py` (P) |

Out of scope here (other briefs): the PIT store, registry, contracts, `is_stale`, role actions, runtime, KIS guard, fixtures (T:TASK-M1-01, -02, -07 … -17, -20 … -22).

---

## B. Build spec, module by module

### B0. Layout decision (needed before any code)

The two data paths are verbatim config values: `calendars.regime_tags_file: core/calendars/data/kr_regime_tags.yaml` (S:2075, S:4192) and `data_contracts.source_exceptions: core/calendars/data/source_skipped.yaml` (S:1902, S:4229). A directory `core/calendars/` cannot coexist with the module `core/calendars.py`.

Recommended: convert `core/calendars.py` into a package.
- `core/calendars/__init__.py` = the current file body unchanged, with one edit: `DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "calendars"`. Re-export the v2 names listed in B2–B7.
- The legacy JSON files, `core/markets.Market.trading_state` and engine tests 69–75 stay untouched. The v2 loader never reads `data/calendars/*.json`, and the legacy loader never reads `core/calendars/data/`.
- If the app is ever installed as a wheel, add `[tool.setuptools.package-data] "core.calendars" = ["data/*.yaml"]` to `pyproject.toml` (today the app runs from the source tree).

Alternative (smaller diff, breaks the verbatim paths): keep the module, put the v2 code in one new module and the data under `data/calendars/v2/`, and change the two rules-store values. Not recommended: T:TASK-M0-05 reproduces those keys verbatim.

YAML hazard (PyYAML is YAML 1.1): an unquoted `15:30` parses as the integer 930 and an unquoted `2016-08-01` as a `date`. Quote every time and date string in every data file, as the spec's config does. Load with `yaml.safe_load` only.

Market identifiers (S:1036-1037, S:3538): v2 functions take the §6.1 enum `KR, US, JP, EU, TW, CN, HK, IN, EM, CRYPTO, FX`; venue codes are used only inside `core/markets`. M1 implements `KR, US, JP, CN, HK, TW`. Map (proposed, in `core/markets.py`): `MACRO_MARKET_VENUE = {"KR": "KRX", "US": "US", "JP": "TSE", "CN": "SSE", "HK": "HKEX", "TW": "TWSE"}` and `MARKET_HOLIDAY_SET = {"KR": "KRX", "US": "NYSE", "JP": "JPX", "CN": "SSE", "HK": "HKEX", "TW": "TWSE"}`. `CRYPTO` is M10 (R-17, T:TASK-M10-01: `decision_time_utc('CRYPTO', d)` = 00:00:00Z of d+1); any other id raises `KeyError`.

### B1. `core/calendars/store.py` — signed files, change control, coverage (T:TASK-M1-05)

```python
class NotASession(Exception)            # S:2087 (name binding)
class CalendarUnsigned(Exception)       # proposed name; T-CAL-01
class CalendarCoverageError(Exception)  # proposed name; T-CAL-02 -> OPS HALT reason "calendar_coverage"

@dataclass(frozen=True)
class CalendarFile:                      # proposed
    file_id: str; version: str; md5: str
    covers_from: date; covers_to: date
    signed_off_by: str                   # non-empty or the file is refused
    rows: tuple[dict, ...]               # each row: effective_from, effective_to, source_url, retrieved_at_utc, signed_off_by (S:2001)

def load_file(file_id: str, data_dir: Path | None = None) -> CalendarFile
def status(market_or_set: str, decision_date: date) -> dict   # {signed, version, covers_from, covers_to, sessions_left, alerts[]}
def check_coverage(decision_date: date, markets: Iterable[str]) -> list[dict]   # alerts; raises CalendarCoverageError outside coverage
```

Rules (binding):
1. **Row fields.** "Calendar data files, each row with `effective_from`, `effective_to`, `source_url` (or the notice reference), `retrieved_at_utc` and `signed_off_by`" (S:2001). "Every change carries the official source, the retrieval date and an owner sign-off" (S:1990).
2. **Refusal at load (T-CAL-01, S:2100).** A calendar, regime-tag, publication-schedule or source-exception file without `signed_off_by` (missing, null or empty, at file level or on any row) raises `CalendarUnsigned` at load. Consequence: "A missing or unsigned calendar version makes every acting input of that market fail closed (R-19)" (S:2088). R-19 adds: "If the publication calendar cannot be read, every acting input fails closed and every risk-model input takes its conservative default. There is never a fallback to observation-age staleness" (S:1956).
3. **Change control (S:2053, S:2076).** `change_control: {owner_sign_off: required, test_per_change: required}`. "A calendar change is a new version of the data file, with the owner's sign-off and a new test case. An unsigned change is refused." Enforcement (proposed, the spec names no mechanism): `core/calendars/data/MANIFEST.yaml` with one row per data file `{file, version, md5, signed_off_by, test_ids[]}`; the loader refuses a file whose md5 differs from its manifest row (an edit under an old signature is an unsigned change) or whose row has an empty `test_ids`.
4. **Governance event.** "calendar or notional change" writes one `governance_event` line (S:4096); kind enum value `calendar_change` (S:4104). Proposed payload: `{kind: "calendar_change", book_id: null, rule_id: "R-20", key: <file_id>, old: {version, md5}, new: {version, md5, signed_off_by}, actor: "owner", reason, refs: ["R-20 rule 6", "T-CAL-01"]}`, written through the M0 appender (T:TASK-M0-07) when a loaded version differs from the last logged one.
5. **Coverage horizon (S:2077, S:2090, S:2101).** `coverage: {min_sessions_ahead: 60, warn_at_sessions_left: 60, page_at_sessions_left: 20, outside_coverage: OPS_HALT}`.
   - `sessions_left(file, decision_date)` = number of sessions of the file's own market (business days for FED, SIFMA, ECOS, publication schedules) with `decision_date < d ≤ covers_to`.
   - `sessions_left ≤ 60` → alert severity `warn`; `≤ 20` → severity `page` (alert shape of §6.1, S:3625-3626: `{alert_id, code, severity ∈ {info, warn, page}, component, first_seen_utc, count}`; proposed `code = "calendar_coverage"`).
   - Decision date outside `[covers_from, covers_to]` → `CalendarCoverageError`; at runtime it is "an OPS HALT with `reason = calendar_coverage`, never a silent `NotASession`" (S:2090): `runtime_halt(book_id, "OPS", "calendar_coverage")` for every book that reads that calendar ("A global failure (the PIT store, the calendars, the `core/engine` QuoteFeed) HALTs every book that reads it; it never HALTs 'the engine' as such", S:1178). The reason code is in the §7 enum (S:4357).
   - Applies to "every calendar, regime-tag and publication-schedule file" (S:2090).
   - DISARMED → ARMED needs "the calendars cover ≥ 60 sessions ahead (T-CAL-02)" (S:1180). An ARMED book whose coverage falls under 60 only alerts; it HALTs only when a decision date is outside coverage.
   - OPS re-arm (S:1179): "HALTED until the cause clears (input fresh, heartbeat restored, artifact valid, NAV available, calendar signed); the book re-arms automatically at the first decision at which the cause has cleared". "No refusal window, **no reference reset**, no post-re-arm cap."
6. **Deadline.** "The 2027 KRX, NYSE, Fed and SIFMA files are signed off before 2026-11-01 (default, judgment)" (S:2101).
7. **Never sign for the owner.** No shipped data file may carry a non-empty `signed_off_by` written by the build. Draft files ship with `signed_off_by: null`, are refused at load, and leave every KR and US acting input failed closed and every book DISARMED until the owner signs. Hermetic tests use fixture files in a temporary `data_dir` whose signer string is visibly a fixture (e.g. `"TEST-FIXTURE (not an owner sign-off)"`); the production loader takes no `data_dir` argument from application code.

### B2. `core/calendars/clocks.py` — sessions and clocks (T:TASK-M1-03)

Signatures (S:1024-1037, S:1991-1994):

```python
def decision_time_utc(market: str, session_date: date) -> datetime      # the scheduled official close; NOT decision_utc
def close_print_bound_utc(market: str, session_date: date) -> datetime  # scheduled close + print bound = the decision instant
def is_session(market: str, d: date) -> bool
def session(market: str, d: date) -> SessionInfo                        # spec name `Session` (open, close, closing call, special flags)
def nyse_holiday(d: date) -> bool
```

The spec's return type name `Session` collides with the existing `core.markets.Session`; use `SessionInfo` (proposed): `{market, session_date, tz, open_local, close_local, open_utc, close_utc, close_print_bound_utc, closing_call_local: (start, end) | None, lunch_break_local: (start, end) | None, flags: frozenset ⊆ {csat, first_trading_day, saturday, early_close}, random_end: {kind, bound_s, extension_s}, calendar_version}`.

All returned datetimes are timezone-aware UTC. Local → UTC conversion uses `zoneinfo` (`Asia/Seoul` has no daylight saving; `America/New_York` "via zoneinfo … never a fixed month rule", S:1290).

**Algorithm, `decision_time_utc(market, d)`**
1. Load the market's signed files (B1). Unsigned → `CalendarUnsigned`. `d` outside coverage → `CalendarCoverageError`.
2. `not is_session(market, d)` → raise `NotASession`; "it never rolls silently to the next day" (S:2087).
3. Local scheduled close, then convert to UTC.

KR local scheduled close, first match wins:

| Order | Condition | Close (KST) | Source |
|---|---|---|---|
| 1 | Saturday session: `d.weekday() == 5` and `d < 1998-12-12` | `saturday_session_close_kst` from the signed file (`from_krx_notice`). Value absent → raise (fail closed); never substitute the weekday close | S:2015, S:2066-2067 |
| 2 | CSAT day (date list in the signed file) | `csat_session_kst` window end: `"16:00"` to 2016-07-31 (config value, "pre-2016 window UNVERIFIED: confirm from the KRX notice at the M1 sign-off"); `"16:30"` from 2016-08-01 (07:30Z) | S:2013, S:2063 |
| 3 | Otherwise | `close_kst`: `"15:00"` to 2016-07-31 (06:00Z); `"15:30"` from 2016-08-01 (06:30Z) | S:2010, S:2059 |

Other markets:

| Market | Scheduled close | Source |
|---|---|---|
| US | `close_et: "16:00"`; `early_close_et: "13:00"` on NYSE early-close dates; `tz: America/New_York`. 20:00Z in EDT, 21:00Z in EST; early close 17:00Z in EDT (e.g. 2025-07-03), 18:00Z in EST (e.g. 2026-11-27) | S:2021, S:2069, S:1290 |
| JP | `close_jst`: `"15:00"` (06:00Z) to 2024-11-04; `"15:30"` (06:30Z) from 2024-11-05 | S:2022, S:2070 |
| CN | `close_cst: from_sse_notices` (15:00 CST = 07:00Z today) | S:2023, S:2071, S:1338 |
| HK | `close_hkt: from_hkex_notices` (16:00 HKT = 08:00Z today; "closing auction from the notices") | S:2023, S:2072 |
| TW | `close_tst: from_twse_notices` (13:30 TST = 05:30Z today; "earlier hours from the notices") | S:2023, S:2073 |

**Algorithm, `close_print_bound_utc(market, d)`** = `decision_time_utc(market, d)` + bound seconds:

| Market / era | Bound | Source |
|---|---|---|
| KR, `d ≥ 2015-06-15` | `+ max_s` = 30 s (`random_end: {from: "2015-06-15", kind: unconditional, max_s: 30}`): 06:00:30Z through 2016-07-29, 06:30:30Z from 2016-08-01, CSAT close + 30 s (07:30:30Z from 2016-08-01) | S:2012, S:2029, S:2062 |
| KR, `d ≤ 2015-06-14` | `+ print_tolerance_s` = 30 s, `+` the extension the KRX notice records for a session whose conditional random end was triggered (`triggered_extensions: from_krx_notice`; per-session rows in the signed file; 0 s when no row exists) | S:2012, S:2029, S:2061 |
| US | `+ calendars.US.close_print_bound_s` = 30 s, DST-aware ("M1 confirms the bound from logged print times") | S:2021, S:2069 |
| JP, CN, HK, TW | `+ calendars.<m>.close_print_bound_s` = 0 s ("default, judgment: the 60 s buffer covers dissemination") | S:2023, S:2070-2073 |

Meaning of the two clocks (binding):
- `decision_time_utc` = scheduled close; an official close of session d is stored with `obs_utc = decision_time_utc(m, d)` (S:2026).
- `close_print_bound_utc` = the decision instant: `macro_state.decision_utc` (S:3535), the lag-audit instant (S:2033), and the upper bound of a close's `available_at_utc` (S:2027). `available_at_utc` is "the exchange print time when it is logged, else the bound (`calendar_bound`); a receipt time is only ever `retrieved_at_utc`. A close whose logged print time exceeds its bound fails closed with a calendar-review alert and is never re-stamped" (S:2031).
- Quarantine anchor used by the data layer: `close_print_bound_utc + 10 min` (06:40:30Z for KRX today; S:1323, `data.reject_rows_retrieved_before_close_plus_minutes: 10`, S:4206).

**`is_session(market, d)`**
- KR: inside coverage; not in the KRX holiday set; Monday–Friday, or a Saturday with `d < saturday_sessions_before` (`"1998-12-12"`). T-SAT-01: true "for every non-holiday Saturday d < 1998-12-12 and false for every Saturday from 1998-12-12 on" (S:2097). Sundays never.
- US: Monday–Friday and `not nyse_holiday(d)`. JP, CN, HK, TW: Monday–Friday and not in the market's own set (JPX, SSE, HKEX, TWSE), plus any weekend sessions their signed notices record.
- Outside coverage: raise `CalendarCoverageError` (the v2 API never returns `None`; the legacy `is_trading_day` keeps its `None`).

**`session(market, d)` content, KR**

| Field | Rule | Source |
|---|---|---|
| open | 09:00 KST today (S:1289); `first_trading_day_open_kst: "10:00"` on the first trading day of the year; 10:00 on CSAT days (`csat_session_kst` window start) | S:2014, S:2065, S:1629 |
| closing call | `closing_call_kst`: `["14:50","15:00"]` to 2016-07-31; `["15:20","15:30"]` from 2016-08-01. CSAT: `csat_closing_call_kst`: `from_krx_notice` to 2016-07-31; `["16:20","16:30"]` from 2016-08-01 ("R-27 CSAT snapshot; confirm at the M1 sign-off") | S:2011, S:2060, S:2064 |
| lunch break | present "Until May-2000; the exact date comes from the official notice"; window from the notice | S:2016 |
| random end | `{to: "2015-06-14", kind: conditional, print_tolerance_s: 30, triggered_extensions: from_krx_notice}`, `{from: "2015-06-15", kind: unconditional, max_s: 30}` | S:2061-2062 |
| excluded from signals | `excluded_sessions: [{venue: NXT, window_kst: ["15:40","20:00"]}, {venue: KRX_after_market, from: "2026-09-14", window_kst: ["16:00","20:00"]}]`; "a vendor 'last' after 15:30 is never stored as the close" | S:2017, S:2068, S:1289 |
| KOSPI200 futures | "The expiring contract stops at 15:20 KST on its last trading day (R-26 roll rule)" (data for R-26; no clock function in M1) | S:2018 |

`nyse_holiday(d)`: membership in the NYSE holiday set only. The Fed, SIFMA and NYSE sets are three separate sets (S:1994, S:2024).

### B3. Holiday sets and business-day helpers (T:TASK-M1-06)

```python
def fed_business_day(d: date) -> bool     # Mon-Fri and not in the FED set
def sifma_status(d: date) -> str          # proposed domain: "open" | "early_close" | "closed" (the spec gives the name only, S:1994)
```

- `holiday_sets: [KRX, NYSE, FED, SIFMA, CBOE, CME, JPX, SSE, HKEX, TWSE, ECOS]` — "kept separate (QF2-A11); every registered input's obs_calendar" (S:2074, S:4191). One file per set (proposed `holidays_<SET>.yaml`), each signed and coverage-checked.
- Binding distinction: "On Columbus and Veterans Day the NYSE is open and the Fed is closed (R-19's H.15 / H.10 rules)" (S:2024). `time.business_days: {publication: fed_sifma_calendar, decision: exchange_calendar}` (S:4166). "Publication business days come from the publisher's calendar (Fed, SIFMA), not the equity trading-day index" (S:541).
- `obs_calendar` values a series may name: "KRX, NYSE, FED, SIFMA, CBOE, JPX, SSE, HKEX, TWSE, CME or ECOS, the BoK ECOS business days of `BOK_CALL_RATE`" (S:1390).

### B4. `core/calendars/publication.py` — publication calendars (T:TASK-M1-06; consumed by R-19 step 3)

```python
def publication_instant(series: str, obs_date: date) -> datetime      # UTC; when the observation dated obs_date is published
def next_expected_obs(series: str, obs_date: date) -> date            # next date in the series' obs_calendar; skips source-exception dates
def add_publication_bdays(series: str, instant: datetime, n: int) -> datetime   # n business days on the series' publication calendar, same local wall time
def source_skipped(series: str) -> frozenset[date]                    # proposed accessor over source_skipped.yaml
```

Each series' schedule comes from its registry row: `publication_schedule` = "a calendar id, a local time and an IANA time zone, e.g. `{calendar: FED, time: "16:15", tz: America/New_York}`" plus `obs_calendar`, `release_event_type` and `grace_publication_bdays` (S:1390-1391). The registry is the data brief's (T:TASK-M1-08); to avoid a circular import between `core/calendars` and `core/ficc/data`, resolve `series → schedule` with a lazy import inside these functions or pass the schedule object.

Schedule rules (verbatim sources S:1847-1852, S:1299-1305, S:4167-4173):

| Schedule | `publication_instant(series, D)` |
|---|---|
| H.15 (DGS10 and every H.15 series; `H15: {posted: "16:15 ET on the next Fed business day"}`) | 16:15 `America/New_York` on the next **Fed** business day after D |
| H.10 (DEXKOUS, DTWEXBGS, DEXJPUS; `H10: {posted: "Monday 16:15 ET; next business day if Monday is a Federal holiday"}`) | 16:15 ET on the Monday following D's business week; when that Monday is a federal holiday, the next Fed business day |
| Treasury par-yield curve (`TREASURY_PAR: {posted: "usually by 18:00 ET on D", log_posting_time: true, us_close_decision_bdays: 1}`) | 18:00 ET on D = the expected instant for staleness; "the logged (first-seen) posting time is the record's `available_at_utc`" |
| BLS (`BLS: {posted: "08:30 ET"}`) | 08:30 ET on the release date from the BLS calendar |
| BEA | "its release calendar" |
| VIX / VIX3M (`VIXCLS: {official_close: "16:15 ET", us_close_decision_bdays: 1}`) | Cboe or Yahoo channel: 16:15 ET on D (value timing, labelled). FRED channel: "FRED's logged posting time (`last_updated`, logged for 20 sessions in M1; history uses that measured lag, declared in the registry)" (S:1426) |
| Re-posting channels (FRED for VIXCLS or DTWEXBGS) | "the publication instant is that channel's posting time (FRED `last_updated` when live; a declared lag in history), not the primary source's" (S:1278) |
| Market closes | "the session's close-print bound (R-20)" = `close_print_bound_utc(m, D)` |
| ECOS USD/KRW (`ECOS_USDKRW: {close_kst: "15:30", close_1500_until: "2016-08-01", snapshot_1530_from: "2026-07-06"}`) | 15:30:00 KST of K (15:00:00 before 2016-08-01); backfilled history is `calendar_bound` at that instant with `timing = value_proxy`; live reads are `inferred_from_retrieval` (S:1414) |
| KODEX 200 basket (`KODEX200_PDF`) | "`expected_available_utc` = 08:00 KST on the next KRX session (default, judgment)" until measured in M1 (S:1411) |

- **Source-exception list** (S:1854): "the Good-Friday bond-market closures, 2017-01-20, 2018-12-05, 2020-11-27, 2020-12-24, and the DC storm closures of 2016-01-22 and 2018-03-02 … sit in a versioned, owner-signed exception list in `core/calendars` and generate no expected observation." `next_expected_obs` skips them (S:1861).
- **Delays.** "each series names its release event (`release_event_type`, §4.2), whose `delayed` or `cancelled` status moves or removes the expected instant" (S:1367). M1 needs a minimal read path over release events `{event_id, type, scheduled_utc, status}`; the full store is M5.
- **`add_publication_bdays`**: used as `deadline = add_publication_bdays(series, due, contract(series).grace_pub_bdays)` with default 1 (S:1863, `grace_publication_bdays: 1`, S:1901). Step n business days of the series' publication calendar and keep the local wall-clock time (DST-aware).
- R-19 step 3 (owned by the data brief; shown because it fixes how these functions are called, S:1857-1864):

```python
def is_stale(series, decision_utc, knowledge_utc):
    rec = pit_last(series, decision_utc, knowledge_utc)
    if rec is None:
        return Stale("missing")
    d_next = cal.next_expected_obs(series, rec.obs_date)        # skips source-exception dates
    due = cal.publication_instant(series, d_next)               # schedule rule of step 2
    deadline = cal.add_publication_bdays(series, due, contract(series).grace_pub_bdays)   # default 1
    return Stale("missed_release") if decision_utc > deadline else Fresh()
```

### B5. `usable_at` and cross-market availability (T:TASK-M1-18)

```python
def usable_at(series_id: str, obs_date: date, market: str) -> datetime   # first decision_utc of `market` that may use the datum (S:1038)
```

Rules (binding):
1. **Availability (R-01 rule 1, S:1493).** `available_at_utc ≤ decision_utc`, where `decision_utc = close_print_bound_utc(market, session)`.
2. **Publication-timed series.** `usable_at` = `close_print_bound_utc(market, s)` for the first session `s` of `market` with `close_print_bound_utc(market, s) ≥ publication_instant(series, obs_date)` ("the first US close after the posting instant", "the first KRX close after the posting instant", S:1342-1343).
3. **General cross-market rule (S:1336, S:1892, `cross_market: {rule: "close_print_bound_utc(m, D) + buffer < decision_utc", buffer_s: 60}`, S:1915).** A close of market M dated D is usable at `decision_utc` if and only if `close_print_bound_utc(M, D) + 60 s < decision_utc` (strict). `usable_at` = the bound of the first session of `market` satisfying it. A market's own close is usable at its own decision (`available_at_utc ≤ close_print_bound_utc`).
4. **US data at KRX decisions (S:1333, `cross_tz_rule: "us_dated_D_usable_for_KR_close_K_iff_D_le_K_minus_1_and_available_at_le_decision"`, S:4164).** A US- or New-York-dated datum dated D enters the KRX decision at the close of Korea date K only if D ≤ K − 1 calendar day **and** its `available_at_utc` ≤ the KRX `decision_utc` on K. Both conditions apply.
5. **Forbidden case (S:1335).** "Never use the US session dated K for a KRX close-to-close return dated K."
6. "Covariances use synchronous or lagged returns, never a same-date join across asynchronous closes" (S:1339, S:1894).
7. `us10y` lag counts in §7 are documentation only: "code uses usable_at() (first close after the publication instant); counted on NYSE days the DGS10 count leaks on Columbus and Veterans Day" (S:4224).

Worked values the rule must reproduce (KRX decision of the same date D; all derived from rule 3):

| Case | `bound(M, D) + 60 s` | KRX `decision_utc` | Usable |
|---|---|---|---|
| TSE, non-CSAT, D ≥ 2024-11-05 | 06:31:00Z | 06:30:30Z | no |
| TSE, non-CSAT, 2016-08-01 … 2024-11-04 | 06:01:00Z | 06:30:30Z | yes |
| TSE, non-CSAT, D < 2016-08-01 | 06:01:00Z | 06:00:30Z (plus any signed pre-2015-06-15 extension) | no |
| CSAT 2025-11-13, TSE | 06:31:00Z | 07:30:30Z | yes |
| CSAT 2025-11-13, Shanghai | 07:01:00Z | 07:30:30Z | yes |
| pre-2016 CSAT with the configured 16:00 KST close, TSE / Shanghai | 06:01:00Z / 07:01:00Z | 07:00:30Z | yes / no |
| TAIEX, every weekday KRX close | 05:31:00Z | ≥ 06:00:30Z | yes |
| HKEX (16:00 HKT) | 08:01:00Z or later | ≤ 07:30:30Z | no |

### B6. `core/calendars/regime.py` — `regime_tags` (T:TASK-M1-04)

```python
def regime_tags(market: str, d: date) -> dict     # S:1039, S:1996
```

- "`regime_tags('KR', date)` returns the effective value of each tag. Dates given to the month come from the review sources. The exact day is taken from the official notice when the calendar file is signed off" (S:2034).
- Tag keys (R-20 rule 4, S:2036-2047; these names govern over the abbreviations in the §3.5 comment `close_time`, `short_ban`, `sell_tax`, S:1039-1040): `price_limit`, `saturday_session`, `close_time_kst`, `closing_call`, `random_end`, `lunch_break`, `fx_regime`, `etf_available`, `short_sale_ban`, `sell_tax_pct`, `tick_regime`, `letf_rules`, `usdkrw_onshore_hours`.

| Tag | Effective-dated values (verbatim) |
|---|---|
| `price_limit` | ±6% from Apr-1995; ±8% from Nov-1996; ±12% from Mar-1998; ±15% from Dec-1998; ±30% from 2015-06-15. Returned as a fraction: 0.08, 0.12, 0.15, 0.30 (T-REGIME-01) |
| `saturday_session` | true before 1998-12-12 |
| `close_time_kst`, `closing_call`, `random_end`, `lunch_break` | as rule 1 (B2 tables) |
| `fx_regime` | `peg_1997` for 1997-09-22 → 1997-10-17 (won at 912.3–914.9 on the ECOS 15:30 close; the band broke in late Oct-1997); otherwise the regime recorded from BoK sources |
| `etf_available` | true from KODEX 200's listing in Oct-2002 (the exact date is in the KRX listing record) |
| `short_sale_ban` | 2008-10 → 2009; 2011-08 → 2011; 2020-03 → 2021-05; 2023-11 → 2025-03 (KCMI; exact dates from the FSC notices) |
| `sell_tax_pct` | Anchors 0.30 (2019), 0.15 (2025), 0.20 (2026; 0.05% transaction tax + 0.15% rural special tax). ETFs are exempt. The full step schedule comes from the official notices. Unit is percent (0.20 = 0.20%) |
| `tick_regime` | stocks reformed 2023-01-25; ETFs ₩1 tick below ₩2,000 from 2023-12-11 |
| `letf_rules` | single-stock leveraged-ETF rules of 2026-05-27 and 2026-07-16 |
| `usdkrw_onshore_hours` | close 15:00 KST → 15:30 KST (2016-08-01) → 02:00 KST next day (Jul-2024) → 24 hours (from 2026-07-06) |

- Algorithm: for each tag, the row with `effective_from ≤ d ≤ effective_to` (open-ended `effective_to: null`). Exactly one row per tag per date; zero or two matches is a load-time error.
- Fail-closed (S:2089): "A tag requested for a date the file does not cover raises. A card whose span is not fully covered by the regime-tag file is refused." A market without a tag file raises.
- Uses (S:2049-2052): long-sample cards print their checks per regime and declare one primary out-of-sample line (R-22); "R-18 logs a market-structure break when a tag changes; any card whose evidence straddles the break prints the split"; futures-line books print a ban-period basis line (R-26); every episode carries the tags of its peak date (S:5096).
- Output: `macro_state.extras.regime_tags` on every KR record (S:2082, S:3630); `model_card.macro.regime_line_results[]` (S:2083); `episodes[].regime_tags` (S:2385, S:4034).

### B7. Event-time mapping and gap tags

M1 (T-TZ-02):

```python
def kr_open_gap_session(event_utc: datetime) -> date      # proposed helper: first KRX session whose open is later than event_utc
```
- FOMC 2026-09-16 14:00 EDT = 18:00Z = 2026-09-17 03:00 KST → `2026-09-17`. Sep NFP 2026-10-02 08:30 EDT = 12:30Z = 21:30 KST → `2026-10-06` (KRX closed 2026-10-05) (S:5623, S:3850).
- Set only for `kr_open_gap_event_types: [US_CPI, US_NFP, FOMC, HYPERSCALER_EARNINGS]` (S:4382); null otherwise.

M5 (I-06b, I-06c; signature fixed now, S:1041):

```python
def gap_sessions(market: str, session_date: date) -> int   # n_US >= 0: US sessions since the previous KRX close (R-10)
```
- n_US = number of NYSE sessions whose close falls after the previous KRX close and before the KRX session K. Checks: K = 2026-10-06 → 2 (US sessions of 2 and 5 Oct; S:3700); K = 2026-10-12 → 2 (US sessions of 8 and 9 Oct; S:6313); K = 2026-11-27 → 0 (NYSE closed 2026-11-26; S:5696); an ordinary session → 1.
- `var_display_scale` = `sqrt(max(n_US, 1))`, display only; `gap_sessions = 0` is valid (S:168, S:3576-3577, S:4383). "No event tag changes any weight" (S:1634, `tags_change_weights: false`, S:4386).
- `macro_state.effective_session` = "the session whose return the decision earns (t+1)" (S:3537) = the next `is_session` date after the decided session (2026-10-02 → 2026-10-06, S:3660).

### B8. `core/markets.py`, `config.py`

- `core/markets.py`: add the two maps of B0; leave `_MARKETS`, `Session` and `trading_state` as they are (they serve the live quote engine). "`core/markets` holds the session; `core/calendars` holds the holidays, DST and every effective-dated rule" (S:1285).
- `config.py`: add nothing for clocks. "`decision_time_utc` (the scheduled close), `close_print_bound_utc` (the decision instant) and `usable_at` are calendar lookups, never constants" (S:1285); `scheduled_close_utc: calendar_lookup, close_print_bound_utc: calendar_lookup # … never read as constants` (S:4160).

---

## C. Schemas and config

### C1. Config keys read by this area (rules store, written by T:TASK-M0-05; verbatim)

`calendars` block (S:2057-2077, repeated S:4174-4194):

```yaml
calendars:                                           # R-20; data files in core/calendars/data/ (owner-signed)
  KR:
    close_kst: [{to: "2016-07-31", time: "15:00"}, {from: "2016-08-01", time: "15:30"}]
    closing_call_kst: [{to: "2016-07-31", window: ["14:50", "15:00"]}, {from: "2016-08-01", window: ["15:20", "15:30"]}]
    random_end: [{to: "2015-06-14", kind: conditional, print_tolerance_s: 30, triggered_extensions: from_krx_notice},
                 {from: "2015-06-15", kind: unconditional, max_s: 30}]   # bound = scheduled close + max_s, or + print_tolerance_s before 2015-06-15
    csat_session_kst: [{to: "2016-07-31", window: ["10:00", "16:00"]}, {from: "2016-08-01", window: ["10:00", "16:30"]}]   # pre-2016 window UNVERIFIED: confirm from the KRX notice at the M1 sign-off
    csat_closing_call_kst: [{to: "2016-07-31", window: from_krx_notice}, {from: "2016-08-01", window: ["16:20", "16:30"]}]   # R-27 CSAT snapshot; confirm at the M1 sign-off
    first_trading_day_open_kst: "10:00"
    saturday_sessions_before: "1998-12-12"
    saturday_session_close_kst: from_krx_notice       # owner-signed at M1; decision_time_utc and the bound exist for Saturdays
    excluded_sessions: [{venue: NXT, window_kst: ["15:40", "20:00"]}, {venue: KRX_after_market, from: "2026-09-14", window_kst: ["16:00", "20:00"]}]
  US: {close_et: "16:00", early_close_et: "13:00", holiday_set: NYSE, tz: America/New_York, close_print_bound_s: 30}   # M1 confirms the bound from logged print times
  JP: {close_jst: [{to: "2024-11-04", time: "15:00"}, {from: "2024-11-05", time: "15:30"}], close_print_bound_s: 0}   # default, judgment: the 60 s buffer covers dissemination
  CN: {close_cst: from_sse_notices, close_print_bound_s: 0}          # SSE 15:00 CST today; effective-dated, owner-signed at M1 (§9.5)
  HK: {close_hkt: from_hkex_notices, close_print_bound_s: 0}         # HKEX 16:00 HKT today (closing auction from the notices)
  TW: {close_tst: from_twse_notices, close_print_bound_s: 0}         # TWSE 13:30 TST today (earlier hours from the notices)
  holiday_sets: [KRX, NYSE, FED, SIFMA, CBOE, CME, JPX, SSE, HKEX, TWSE, ECOS]   # kept separate (QF2-A11); every registered input's obs_calendar
  regime_tags_file: core/calendars/data/kr_regime_tags.yaml
  change_control: {owner_sign_off: required, test_per_change: required}
  coverage: {min_sessions_ahead: 60, warn_at_sessions_left: 60, page_at_sessions_left: 20, outside_coverage: OPS_HALT}   # T-CAL-02
```

`time` block (S:4153-4173; keys and values verbatim, some trailing comments trimmed):

```yaml
time:
  storage_tz: UTC
  decision: close_t_earn_t_plus_1        # QUANTGEN rule 02
  calendars: effective_dated             # R-20
  decision_instant: close_print_bound_utc
  markets:
    KR:  {tz: Asia/Seoul, session: calendars.KR, scheduled_close_utc: calendar_lookup, close_print_bound_utc: calendar_lookup,
          session_rules: calendars.KR, regime_tags: calendars.regime_tags_file, open_no_entry_minutes: 30}
    US:  {tz: America/New_York, session: ["09:30","16:00"], decision_utc: close_print_bound_utc, session_rules: calendars.US}
    CRYPTO: {tz: UTC, decision_utc: "00:00:00Z of d+1", venue_declared: true, annualisation_days: 365}   # R-17; deferred
  cross_tz_rule: "us_dated_D_usable_for_KR_close_K_iff_D_le_K_minus_1_and_available_at_le_decision"
  cross_market_rule: data_contracts.cross_market   # R-19
  business_days: {publication: fed_sifma_calendar, decision: exchange_calendar}
  publication:
    H15: {posted: "16:15 ET on the next Fed business day"}
    H10: {posted: "Monday 16:15 ET; next business day if Monday is a Federal holiday"}
    TREASURY_PAR: {posted: "usually by 18:00 ET on D", log_posting_time: true, us_close_decision_bdays: 1}
    VIXCLS: {official_close: "16:15 ET", us_close_decision_bdays: 1}
    BLS: {posted: "08:30 ET"}
    ECOS_USDKRW: {close_kst: "15:30", close_1500_until: "2016-08-01", snapshot_1530_from: "2026-07-06"}
```

`data_contracts` keys this area serves (S:1899-1915): `staleness_rule: schedule_aware`; `grace_publication_bdays: 1`; `source_exceptions: core/calendars/data/source_skipped.yaml   # owner-signed, versioned`; `cross_market: {rule: "close_print_bound_utc(m, D) + buffer < decision_utc", buffer_s: 60}   # buffer: default, judgment`.

`data` keys that use the bound (S:4206, S:4213): `reject_rows_retrieved_before_close_plus_minutes: 10   # anchor: close_print_bound_utc of the row's session`; `fixtures: {post_close_only: true, min_minutes_after_close: 10, md5_per_file: true}`.

`events` keys that touch the calendar (S:4380-4386; M5 consumers): `kr_open: {block_first_session_minutes: 30, window_kst: ["09:00","09:30"], late_open_window_kst: ["10:00","10:30"], late_open_days: [first_trading_day_of_year, csat]}`; `kr_open_gap_event_types: [US_CPI, US_NFP, FOMC, HYPERSCALER_EARNINGS]`; `multi_session_gap: {tag: gap_sessions, gap_sessions_min: 0, var_display_scale: "sqrt(max(n_us, 1))", report_separately: true, gross_rule: false}`; `daily_book_blackouts: false`; `tags_change_weights: false`.

Runtime enum this area raises into (S:4356-4358): `OPS: [lag_audit_violation, acting_field_schema_or_bounds_failure, acting_input_fail_closed_beyond_declared_misses, feed_heartbeat_loss_60s, acting_risk_layer_exception, whole_book_nav_unavailable_gt_2_decisions, calendar_coverage, operator_kill, acting_step_error_beyond_limit]`.

Precedence: "If a rule and this listing ever differ, the rule governs and this listing is fixed" (S:4132).

### C2. Data files under `core/calendars/data/` (proposed shapes; every file signed, versioned, coverage-checked)

Common envelope (proposed): `{file_id, version, covers: {from, to}, signed_off_by, rows: [...]}`; every row carries `effective_from`, `effective_to`, `source_url` (or the notice reference), `retrieved_at_utc`, `signed_off_by` (S:2001).

| File | Content | Row fields beyond the common five |
|---|---|---|
| `kr_sessions.yaml` (P) | KRX date-level facts the config cannot hold | `csat_days[]`; `saturday_session_close_kst`; `triggered_random_end_extensions[] = {session_date, extension_s}`; `lunch_break = {window_kst, last_date}`; pre-2016 CSAT window and closing call; regular open time by era |
| `holidays_<SET>.yaml` (P), SET ∈ {KRX, NYSE, FED, SIFMA, CBOE, CME, JPX, SSE, HKEX, TWSE, ECOS} | closed dates; NYSE early closes; SIFMA early-close recommendations | `date`, `kind ∈ {closed, early_close}`, `name` |
| `market_closes.yaml` (P) | effective-dated close times for CN, HK, TW from the exchange notices (US and JP are in the config) | `market`, `close_local`, `tz` |
| `publication_schedules.yaml` (P) | the `time.publication` rules as rows, plus BLS and BEA release dates and the FRED re-posting lags | `schedule_id`, `calendar`, `time`, `tz`, `rule ∈ {next_bday_after_obs, monday_after_week, same_day, release_calendar, channel_posting_time}` |
| `kr_regime_tags.yaml` (verbatim path) | one row per (tag, effective range) | `tag`, `value` |
| `source_skipped.yaml` (verbatim path) | dates the source legitimately skipped | `series` (or channel), `date`, `reason` |
| `MANIFEST.yaml` (P) | change control | `file`, `version`, `md5`, `signed_off_by`, `test_ids[]` |

Committed expected-values file for T-REGIME-01 (proposed `tests/fixtures/macro/kr_regime_tags_expected.csv`): one row per date 1995-01-01 … 2026-12-31 with the 13 tag values, "built from the official notices (including `price_limit` before Apr-1995)" (S:2098); md5-listed in `tests/fixtures/macro/MANIFEST.csv` (T:TASK-M0-03).

### C3. `event_calendar` artifact, schema 2.0 (§6.3, S:3800-3857; "one file per calendar version; entries per event; `core/calendars`"; built at M5)

New in 2.0 (S:3802-3806): the BoK decision and the press conference are separate event types; a `KRX_HOLIDAY_GAP` type with `gap_sessions` and `var_display_scale`; the `annotate_only` window action; a file envelope that carries the common provenance fields once; `gap_sessions ≥ 0`.

```json
{"$id":"quantgen/event_calendar.v2.0","type":"object",
 "required":["schema","schema_version","read_only","generated_at_utc","knowledge_utc","git_hash","config_hash","data_snapshot_id","calendar_version","events"],
 "properties":{"schema":{"const":"quantgen.event_calendar"},"schema_version":{"const":"2.0"},"read_only":{"const":true},
  "generated_at_utc":{"type":"string","format":"date-time"},"knowledge_utc":{"type":"string","format":"date-time"},
  "git_hash":{"type":"string"},"config_hash":{"type":"string"},"data_snapshot_id":{"type":"string"},
  "calendar_version":{"type":"string","description":"the owner-signed core/calendars data version (T-CAL-01)"},
  "events":{"type":"array","items":{"$ref":"#/$defs/event"}}},
 "$defs":{"event":{"type":"object",
  "required":["event_id","type","region","scheduled_utc","status","source","windows"],
  "properties":{"event_id":{"type":"string"},
   "type":{"enum":["FOMC","US_CPI","US_NFP","US_OTHER_RELEASE","BOK_DECISION","BOK_PRESS_CONFERENCE","BOJ","ECB","KOSPI200_EXPIRY","INDEX_CHANGE","HYPERSCALER_EARNINGS","OIL_GEO","FX_INTERVENTION","KRX_HOLIDAY_GAP","POLICY_FRAMEWORK_CHANGE","MARKET_STRUCTURE_CHANGE","OTHER"]},
   "region":{"type":"string"},"scheduled_utc":{"type":"string","format":"date-time"},
   "status":{"enum":["scheduled","released","cancelled","delayed"]},"released_utc":{"type":["string","null"],"format":"date-time"},
   "source":{"type":"string"},
   "windows":{"type":"array","items":{"type":"object","required":["market","action","start_utc","end_utc"],
      "properties":{"market":{"type":"string"},"action":{"enum":["evaluator_block_new_intraday_entries","evaluator_block_new_futures_entries","annotate_only"]},
                    "start_utc":{"type":"string","format":"date-time"},"end_utc":{"type":"string","format":"date-time"},
                    "resume_condition":{"type":["string","null"]}}}},
   "kr_open_gap_session":{"type":["string","null"],"format":"date"},
   "gap_sessions":{"type":["integer","null"],"minimum":0},
   "var_display_scale":{"type":["number","null"],"description":"sqrt(max(n_US, 1)) for multi-session gaps; display only"},
   "scenario_tag":{"type":["string","null"]},"notes":{"type":"string"}}}}}
```

Envelope example (S:3836-3837): `{"schema":"quantgen.event_calendar","schema_version":"2.0","read_only":true,"generated_at_utc":"2026-10-02T06:41:07Z","knowledge_utc":"2026-10-02T06:40:50Z","git_hash":"<sha>","config_hash":"<sha>","data_snapshot_id":"<md5>","calendar_version":"<signed version>","events":[]}`.

Example entries (S:3843-3856), usable as test vectors:
- `{"event_id":"FOMC-2026-10-28","type":"FOMC","region":"US","scheduled_utc":"2026-10-28T18:00:00Z","status":"scheduled","released_utc":null,"source":"federalreserve.gov FOMC calendar","windows":[{"market":"US","action":"evaluator_block_new_intraday_entries","start_utc":"2026-10-28T17:45:00Z","end_utc":"2026-10-28T19:00:00Z","resume_condition":"VIX < pre-14:00 ET level else 19:30Z"},{"market":"KR_FUT_NIGHT","action":"evaluator_block_new_futures_entries","start_utc":"2026-10-28T17:45:00Z","end_utc":"2026-10-28T19:00:00Z","resume_condition":null}],"kr_open_gap_session":"2026-10-29","gap_sessions":null,"var_display_scale":null,"scenario_tag":null,"notes":"KR opening-gap event night"}` (14:00 EDT = 18:00 UTC = 03:00 KST on 29 Oct).
- `{"event_id":"US-NFP-2026-10-02","type":"US_NFP","region":"US","scheduled_utc":"2026-10-02T12:30:00Z","status":"scheduled","released_utc":null,"source":"bls.gov Employment Situation schedule","windows":[{"market":"US","action":"evaluator_block_new_intraday_entries","start_utc":"2026-10-02T12:25:00Z","end_utc":"2026-10-02T14:00:00Z","resume_condition":"10:00 ET"}],"kr_open_gap_session":"2026-10-06","gap_sessions":null,"var_display_scale":null,"scenario_tag":null,"notes":"KR opening-gap event; the 6 Oct session is also tagged KRX_HOLIDAY_GAP"}`.

Validation failure of an `event_calendar` artifact is "labelled and alerted", "refused and quarantined with its errors", and never a HALT (S:1178, S:1226-1227).

### C4. Artifact fields this area feeds

| Field | Rule | Source |
|---|---|---|
| `macro_state.decision_utc` | "close_print_bound_utc(market, decided_session) from the calendar (R-20)" | S:3535 |
| `macro_state.decided_session`, `effective_session` | the session decided on (t); the session whose return the decision earns (t+1) | S:3536-3537 |
| `macro_state.market` | enum `["KR","US","JP","EU","TW","CN","HK","IN","EM","CRYPTO","FX"]` | S:3538 |
| `macro_state.extras.regime_tags` | on every KR record | S:2082, S:3630 |
| `macro_state.flags.kr_open_gap_event`, `gap_sessions` (integer ≥ 0), `var_display_scale` (number ≥ 1) | display fields; never HALT | S:3575-3577, S:3370 |
| `macro_state.inputs[].expected_available_utc`, `stale_deadline_utc` | from `publication_instant(next_expected_obs(...))` and `add_publication_bdays` | S:1947, S:3521 |
| `macro_state.runtime[].halt` | `{class: OPS, reason_code: "calendar_coverage", since_utc, rearm_mode: auto, causes[…]}` | S:3608-3617 |
| `event_calendar.calendar_version` | the owner-signed data version | S:3814 |
| `governance_event.kind = "calendar_change"` | one line per calendar change | S:4096, S:4104 |
| `model_card.macro.regime_line_results[]`, `episodes[].regime_tags`, `saturday_sessions_before` in the card header | R-22, R-32 | S:2083, S:2385, S:3965, S:4937 |

### C5. Fact register

**C5a. Effective-dated facts the spec gives**

| # | Fact | Source |
|---|---|---|
| 1 | KRX regular close 15:00 KST (06:00Z) through 2016-07-31; 15:30 KST (06:30Z) from 2016-08-01. 142 golden-sample sessions of 2016 closed at 06:00Z | S:2010, S:2029, S:2106 |
| 2 | KRX closing call 14:50–15:00 KST before 2016-08-01; 15:20–15:30 KST from 2016-08-01 | S:2011 |
| 3 | KRX random end: conditional until 2015-06-14; unconditional, ≤ 30 s, from 2015-06-15. Close prints 15:00:00–15:00:30 KST through 2016-07-29 and 15:30:00–15:30:30 KST from 2016-08-01 | S:2012 |
| 4 | KRX CSAT day: session 10:00–16:30 KST from 2016-08-01, close 07:30Z, bound 07:30:30Z; example 2025-11-13. CSAT closing call 16:20–16:30 from 2016-08-01. Pre-2016 window configured 10:00–16:00, UNVERIFIED. "10 CSAT days a decade" | S:2013, S:2063-2064, S:2107 |
| 5 | KRX first trading day of the year opens 10:00 KST | S:2014 |
| 6 | KRX Saturday sessions on non-holiday Saturdays before 1998-12-12, with their own half-day close. Yahoo ^KS11 omits them. Monday / Tue–Fri variance ratio 2.30 in 1997–98 (1.33 / 1.15 / 1.11 in later regimes) | S:2015, S:2097, BL:1257 |
| 7 | KRX lunch break until May-2000 | S:2016, S:1289 |
| 8 | Excluded from signals: NXT after-market 15:40–20:00; KRX after-market 16:00–20:00 from 2026-09-14 | S:2017 |
| 9 | KOSPI200 futures: the expiring contract stops at 15:20 KST on its last trading day | S:2018 |
| 10 | KRX regular session today 09:00–15:30; first 30 minutes are no-entry (09:00–09:30; 10:00–10:30 on 10:00-open days) | S:1289, S:1629 |
| 11 | KRX non-sessions named: 2026-10-05 (substitute holiday), 2026-10-09 (Hangul Day), 2026-03-02 (substitute holiday). KRX sessions named: 2015-01-05, 2015-01-06, 2016-07-29, 2016-08-01, 2025-11-13, 2026-03-03, 2026-09-29, 2026-10-01, 2026-10-02, 2026-10-06, 2026-10-12, 2026-10-14, 2026-11-26, 2026-11-27; 2011-10-04 "a real session" missing from ^KS11 | S:2096, S:3700, S:6313, S:1636, S:1495, S:5696 |
| 12 | NYSE close 16:00 ET (20:00Z EDT, 21:00Z EST); early closes 13:00 ET: 17:00Z in EDT (2025-07-03), 18:00Z in EST (2026-11-27); bound + 30 s. DST: second Sunday of March to first Sunday of November since 2007; first Sunday of April to last Sunday of October before. 2006-03-20 → 21:00Z; 2006-04-03 → 20:00Z; 2026-01-15 → 21:00Z; 2026-10-01 → 20:00Z | S:1290, S:2021, S:5617, S:5622 |
| 13 | NYSE closed 2026-11-26 (Thanksgiving). NYSE open and the Fed closed on Columbus Day (Mon 2026-10-12) and Veterans Day | S:5696, S:2024, S:6313 |
| 14 | TSE close 15:00 JST (06:00Z) through 2024-11-04; 15:30 JST (06:30Z) from 2024-11-05 | S:2022 |
| 15 | Today: SSE 15:00 CST (07:00Z), HKEX 16:00 HKT (08:00Z), TWSE 13:30 TST (05:30Z) ("standard hours; UNVERIFIED in QF2") | S:2023, S:1338 |
| 16 | H.15 posted 16:15 ET on the next Fed business day after D. H.10 posted Monday 16:15 ET for the previous business week (next business day after a holiday Monday). Treasury par yields "usually available … by 6:00 PM Eastern Time" on D. BLS 08:30 ET. FOMC statement 14:00 ET. VIX / VIX3M official close 16:15 ET. BoK decision ≈ 09:50 KST; press conference ≈ 11:10 KST | S:1297-1304 |
| 17 | Onshore USD/KRW close (ECOS 731Y003 item 0000003) 15:30 KST, 15:00 before 2016-08-01; 02:00 KST next day from Jul-2024; 24 hours from 2026-07-06 (Mon 06:00 → Sat 06:00) | S:1305, S:2047 |
| 18 | Source-skipped dates: Good-Friday bond-market closures; 2017-01-20; 2018-12-05; 2020-11-27; 2020-12-24; DC storm closures 2016-01-22 and 2018-03-02 | S:1854 |
| 19 | Regime tags: the table in B6 | S:2036-2047 |
| 20 | Events: FOMC 2026-09-16 14:00 EDT; FOMC 2026-10-28 14:00 EDT; Sep NFP 2026-10-02 08:30 EDT; the Oct-2025 CPI was never published (cancelled event) | S:5623, S:3840, S:3850, S:1625 |
| 21 | Counts (evidence, not gated): 599 / 2,938 DGS10 leaks under the v1.2 KRX mapping; 85 Fed-holiday decisions; 75 holiday Mondays; 86 KRX-only and 156 NYSE-only sessions in 2016–26 | S:2107 |
| 22 | Tech-fund trail, status "traced" (candidate values for the regime file, still subject to sign-off): short-sale bans 2008-10-01..2009-05-31; 2011-08-11..2011-11-09; 2020-03-16..2021-05-02 full, then index stocks only until 2023-11-05; 2023-11-06..2025-03-30; resumed 2025-03-31. Price limits ±30% since 2015-06-15. Sell tax 0.18% (2024), 0.15% (2025), 0.20% from 2026-01-01 (0.05 + 0.15 rural), about 0.30% in 2019. Value-up split date 2024-02-26 | TF:162, TF:1118-1126 |

**C5b. Facts only the owner can supply** (S:76, S:5465, S:2034, S:6033)

| # | Owner input | Blocks |
|---|---|---|
| 1 | `signed_off_by` on every calendar, regime-tag, publication-schedule and source-exception file | every live acting input; T-CAL-01 |
| 2 | The 2027 KRX, NYSE, Fed and SIFMA files, signed before 2026-11-01 | T-CAL-02 |
| 3 | Pre-2015-06-15 conditional random-end extensions (per session) | `close_print_bound_utc` before 2015-06-15 |
| 4 | Saturday-session close times before 1998-12-12 | `decision_time_utc` on Saturdays; T-CLOSE-02 clause |
| 5 | Lunch-break dates (exact end in May-2000) and window | `lunch_break` tag; `session()` |
| 6 | The pre-2016 CSAT session window and its closing call | T-CLOSE-02 and T-XMKT-01 clauses; R-27 snapshot |
| 7 | The CSAT date list (the spec names one date, 2025-11-13) | CSAT closes on real dates |
| 8 | KRX holiday lists from official notices for the whole card span (substitute and election holidays included) | `is_session('KR', …)`; T-SAT-01 |
| 9 | SSE, HKEX and TWSE close times, effective-dated; the JPX, SSE, HKEX, TWSE, CME and Cboe calendars with licence, owner and md5 | T-XMKT-01 on real dates; §9.5 |
| 10 | The Fed holiday schedule, SIFMA recommendations, the NYSE holiday and early-close list | publication instants; `sifma_status` |
| 11 | Exact days for month-level regime dates: price limits Apr-1995, Nov-1996, Mar-1998, Dec-1998; `price_limit` before Apr-1995; the KODEX 200 listing day in Oct-2002; short-sale-ban boundaries from the FSC notices; the full sell-tax step schedule; `fx_regime` outside the 1997 peg; the Jul-2024 onshore-hours day | T-REGIME-01 full-range clause |
| 12 | The ETF tick table before 2023-12-11 (R-26 instrument table; signed with the calendars) | R-26 |
| 13 | The source-exception list per series, signed; the Good-Friday years | T-STALE-01 (b) |
| 14 | BLS and BEA release calendars; the ECOS observation calendar and code of `BOK_CALL_RATE` (before the M7 header commit) | monthly publication instants; R-22 cash leg |
| 15 | M1 measurements: the KODEX 200 basket publication instant; confirmation of the KRX and NYSE 30 s print bounds against logged exchange print times; FRED's VIX posting lag over 20 sessions | T:TASK-M1-23; needs live sessions and KIS credentials |

---

## D. Tests

Feasibility classes: **SYNTH** = hermetic with inline or temp-dir fixture calendars; **REFDATA** = needs frozen reference data absent here; **OWNER** = needs owner input, credentials or live sessions. Rule of precedence: "Both statements must pass; the rule's table carries the detail" for ids in both §9.1 and a rule table (S:5601). All listed tests have `runs_from` M1 (S:5551).

| Test | Exact assertion | Fixture | Class |
|---|---|---|---|
| **T-CLOSE-01** (S:5617), calendar clauses | `decision_time_utc("KR", 2026-10-02)` = 06:30Z; `close_print_bound_utc("KR", 2026-10-02)` = 06:30:30Z; `decision_time_utc("US", 2026-10-01)` = 20:00Z and `close_print_bound_utc("US", 2026-10-01)` = 20:00:30Z; `decision_time_utc("US", 2026-01-15)` = 21:00Z | signed fixture KR and US calendars for 2026 | SYNTH |
| T-CLOSE-01, store clauses (data brief; use the bound) | a close with print time 06:30:20Z accepted; a record with `available_at_utc` 06:31Z rejected; an official close retrieved 06:45Z without print time stored with `available_at_utc` 06:30:30Z (`calendar_bound`) and accepted; a KIS close row retrieved 06:40:29Z is never `official_close`, one retrieved 06:40:30Z is; a US close stamped 20:00:02Z accepted | synthetic store rows | SYNTH |
| T-CLOSE-01, deferred clause | "the workflow never starts before 06:40:30Z (§3.9)" | — | M8 (S:5588) |
| **T-CLOSE-02** (S:2096, S:5618) | `decision_time_utc('KR', 2016-07-29)` = 06:00Z; `('KR', 2016-08-01)` = 06:30Z; `close_print_bound_utc('KR', 2026-10-02)` = 06:30:30Z; `('KR', 2016-07-29)` = 06:00:30Z; `('KR', 2025-11-13)` = 07:30:30Z; `decision_time_utc('KR', 2025-11-13)` = 07:30Z; bound = scheduled close + 30 s print tolerance before 2015-06-15; "A pre-2016 CSAT date and a pre-1998-12-12 Saturday return the signed calendar's close and bound"; `decision_time_utc('KR', 2026-10-05)` raises `NotASession`; `('US', 2026-11-27)` = 18:00Z; `('US', 2025-07-03)` = 17:00Z; `close_print_bound_utc('US', 2026-10-01)` = 20:00:30Z; Saturday sessions before 1998-12-12 present; regime tags returned for any date | fixture KR calendar holding CSAT 2025-11-13, one pre-2016 CSAT date, one pre-1998-12-12 Saturday with a fixture close value, holiday 2026-10-05; fixture NYSE early closes. Assert the Saturday and pre-2016 CSAT values against the fixture file, not against a hard-coded hour | SYNTH; the same assertions on the real signed files are OWNER |
| **T-SAT-01** (S:2097) | `is_session('KR', d)` true for every non-holiday Saturday d < 1998-12-12 and false for every Saturday from 1998-12-12 on | fixture holiday set; loop over every Saturday in the fixture span | SYNTH |
| T-SAT-01, completeness | "A KOSPI fixture that lacks those Saturdays fails the completeness check: every `is_session` date has exactly one close row (the Monday / Tue–Fri variance ratio 2.30 in 1997–98 is printed; EX2)" | mechanism: a synthetic close list without Saturdays must fail. Real fixture: KRX official KOSPI closes from 1997-01-03 with Saturdays (KRX marketplace; BL:1221) and Yahoo ^KS11 1997–98 for the 2.30 ratio | mechanism SYNTH; real data REFDATA. No local substitute: the cache holds no ^KS11 history (`yf__KS200.csv` has one row; `yf_069500.KS.csv` starts 2007-01-29) |
| **T-REGIME-01** (S:2098), point clauses | `regime_tags('KR', 1997-06-02).price_limit` = 0.08; `(1998-06-01)` = 0.12; `(1999-06-01)` = 0.15; `(2015-06-15)` = 0.30; `fx_regime` on 1997-10-01 = `peg_1997`; `etf_available` on 2002-01-02 = false; `short_sale_ban` on 2024-06-03 = true; `sell_tax_pct` on 2026-10-02 = 0.20 | fixture tag file; every asserted date lies strictly inside a month-level range the spec states | SYNTH |
| T-REGIME-01, full-range clause | "Every date from 1995-01-01 to 2026-12-31 returns a full tag set, equal to a committed expected-values file built from the official notices (including `price_limit` before Apr-1995)" | the committed expected-values file | OWNER (exact days, pre-1995 limit, sell-tax steps, BoK regimes) |
| T-REGIME-01, raise clause (S:2089) | a date outside the file raises; a card span not fully covered is refused | fixture | SYNTH |
| **T-AVAIL-01** (S:2099, S:5619, S:3463) | exact match of the golden availability table: DGS10 dated Fri 2015-01-02 → KRX close of Tue 2015-01-06; DEXKOUS for the week of 2026-10-05 → KRX close of Wed 2026-10-14; DGS10 dated 2026-10-09 → US close of 2026-10-14; the CSAT close of 2025-11-13 at 07:30Z. "An injected registry error (e.g. H.15 posted at D, not D+1) makes the test fail" | fixture FED set (2015-01-01 holiday; 2026-10-12 Columbus Day), KRX set (2026-10-05, 2026-10-09 closed; CSAT 2025-11-13), NYSE set; a mutated registry copy for the negative leg | SYNTH; "built from official calendars" on the signed files is OWNER. Also listed in the M7 pre-freeze harness list (S:4813) |
| **T-CAL-01** (S:2100) | "A calendar file without `signed_off_by` is refused at load, and every KR acting input fails closed" | temp-dir file without the field; a stub acting read | SYNTH (the fail-closed half needs the data brief's `pit_value`) |
| **T-CAL-02** (S:2101), mechanism | every calendar, regime-tag and publication-schedule file covers ≥ 60 sessions of its market beyond the decision date; `warn` at 60 sessions left; `page` at 20; a decision date outside coverage "fails closed as an OPS HALT with `reason = calendar_coverage`, never a silent `NotASession`" | fixture file ending N sessions after the decision date for N ∈ {61, 60, 20, 0}; the M1 runtime (T:TASK-M1-20) | SYNTH |
| T-CAL-02, deadline clause | "The 2027 KRX, NYSE, Fed and SIFMA files are signed off before 2026-11-01 (default, judgment)" | the real files | OWNER |
| **T-TZ-01** (S:5622) | for the KOSPI return dated 2026-10-02 (decided at the KRX close of 2026-10-01) the latest usable US close is dated 2026-09-30; for the return dated 2026-10-01 it is 2026-09-29; NYSE close of 2026-01-15 = 06:00 KST on 2026-01-16; of 2026-07-15 = 05:00 KST on 2026-07-16; no same-date Shanghai or HKEX close on non-CSAT days, nor a same-date TSE close outside 2016-08-01 → 2024-11-04; the same-date TAIEX close on weekdays; NYSE close of 2006-03-20 = 21:00Z and of 2006-04-03 = 20:00Z | fixture calendars; `zoneinfo` | SYNTH |
| **T-TZ-02** (S:5623) | the 2026-09-16 statement (14:00 EDT) is 2026-09-17 03:00 KST, `kr_open_gap_session = 2026-09-17`; the Sep NFP (2026-10-02 08:30 EDT) maps to `kr_open_gap_session = 2026-10-06` | fixture KRX set with 2026-10-05 closed | SYNTH |
| **T-XMKT-01** (S:1967) | the eight rows of the B5 table, stated over "every non-CSAT date D … on which both KRX and TSE trade"; "Saturday sessions follow their signed close times" | fixture KR, JP, CN, HK, TW calendars; loop over the fixture span | SYNTH; the full official span is OWNER (item C5b-9) |
| **T-H10-02** (S:1966, S:5633) | DEXKOUS dated Fri 2026-09-25 usable from the KRX close of Tue 2026-09-29 "and not before"; at the KRX close of 2026-10-02 the latest usable DEXKOUS is dated 2026-09-25; the week of 2026-10-05 usable from the KRX close of Wed 2026-10-14, "not before" | fixture FED and KRX sets | SYNTH |
| **T-H15-01** (S:1965, S:5634) | DGS10 dated D has `available_at` = 16:15 ET on the next Fed business day after D; Fri 2015-01-02 → KRX Tue 2015-01-06, not Mon 2015-01-05; DGS10 dated 2026-10-09 usable at the US close of 2026-10-14; the Treasury par-yield channel with a logged posting time is usable +1 business day; R4b state row: the flag first on in data dated 2026-09-23 earns in the strict book from 2026-09-28 | fixture FED, NYSE, KRX sets. Timing check of the state row: DGS10 dated 2026-09-23 → posted 2026-09-24 16:15 ET → first US close 2026-09-25 → earns 2026-09-28 | SYNTH for timing; the flag's value needs DGS10 history (REFDATA; not in the cache) |
| **T-VIX-01** (S:5635) | VIX(D) read at its 16:15 ET close is not usable at the US close of D, and is usable at the US close of D+1 and at the KRX close of K ≥ D+1; FRED `VIXCLS(D)` usable from the first decision after the logged (live) or declared (history) FRED posting time | fixture schedule rows for both channels | SYNTH; the declared history lag is an M1 measurement (OWNER) |
| **T-H10-01** (S:5632) | in `run_mode = live`, reading DEXKOUS for an acting or risk-model input raises | registry and `pit_value` (data brief) | SYNTH |
| T-STALE-01 / G-STALE-01 (S:1963, S:5620, S:5905-5908) — owned by the staleness brief; depends on B3–B4 | over decisions 2016-01-04 → 2026-09-25: DTWEXBGS 0.89% / 0.80%, DEXKOUS 0.52% / 0.42%, DGS10 0.33% / 0.34%, VIXCLS 0% (US close / KRX close); every hit's `d_next` in the source-skipped list; with the list loaded no flag; negative control ≈ 80% (79.8%) must not be what the code does | `results/QX_DLA_staleness.csv`, FRED DTWEXBGS, DEXKOUS, DGS10, VIXCLS and the Fed, KRX, NYSE calendars for 2016–26 | REFDATA. Partial local substitutes: `fred_DEXKOUS.csv` (2017-01-02 → 2026-09-18), `fred_DGS3MO.csv` (an H.15 series with the DGS10 observation calendar, 1990 → 2026-09-23), `yf__VIX.csv` (Yahoo ^VIX, 1995 → 2026-09-25). No local DTWEXBGS or DGS10. Clauses (d) and (e) are SYNTH |
| I-06, I-06b, I-06c (S:5694-5696) | event store, `gap_sessions` values of B7, `KRX_HOLIDAY_GAP`, √max(n_US, 1) | — | M5; `gap_sessions` values are SYNTH on fixture calendars |

Deferred clauses touching this area (S:5567-5597): only T-CLOSE-01's workflow clause (M8). The HALT clauses stay at M1 "because M1 builds the OPS-only per-book runtime" (S:5597).

Cross-check tests worth keeping (proposed, dev-only, skipped when `exchange_calendars` is absent; never a pass condition for a signed file): draft holiday sets equal XKRX / XNYS session lists; every date with a row in `yf_SPY.csv` is `is_session('US')`.

---

## E. Interfaces

**Needs from earlier milestones and M1 siblings**

| From | What | Shape |
|---|---|---|
| T:TASK-M0-05 (rules store) | the `calendars`, `time`, `events` and `data_contracts.{cross_market, source_exceptions, grace_publication_bdays}` blocks | read accessor returning the YAML of C1 as dicts; literal `from_krx_notice` / `from_*_notices` values mean "read the signed data file" |
| T:TASK-M0-07 (governance appender) | `calendar_change` events | one §6.6 line per change |
| T:TASK-M0-08 (schema registry) | `quantgen/event_calendar.v2.0` | used from M5 |
| T:TASK-M0-03 (fixture manifest) | md5 rows for the expected-values file, the source-skipped list and fixture calendars | `tests/fixtures/macro/MANIFEST.csv` |
| T:TASK-M1-08 (series registry) | per series: `obs_calendar`, `publication_schedule {calendar, time, tz}`, `release_event_type`, `grace_publication_bdays`, `channel`, `obs_kind`, market of a close series | lookup by `series_id` (lazy import) |
| T:TASK-M1-20 (runtime) | `runtime_halt(book_id, "OPS", "calendar_coverage")`; automatic re-arm when the cause clears; the ARM precondition "calendars cover ≥ 60 sessions ahead" | `runtime_halt(book_id: str, cls: Literal["RISK","OPS"], reason: str) -> None` (S:1081) |
| Alert sink (M8 banner; M1 structured objects) | `warn` and `page` alerts | `{alert_id, code, severity, component, first_seen_utc, count}` |

**Exposes to later milestones**

| Name | Shape | Consumers |
|---|---|---|
| `decision_time_utc(market, session_date) -> datetime` | UTC; raises `NotASession`, `CalendarUnsigned`, `CalendarCoverageError` | close stamping `obs_utc` (T:TASK-M1-19); R-17 CRYPTO clock (M10) |
| `close_print_bound_utc(market, session_date) -> datetime` | UTC | `macro_state.decision_utc`; lag audit; `available_at_utc` bound; quarantine `+ 10 min`; `usable_cross_market`; workflow start (M8) |
| `is_session`, `session -> SessionInfo` | bool; record | completeness checks (T:TASK-M1-21, -22); R-27 snapshot time = closing-call start − 1 min (15:19 KST since 2016-08-01, 14:49 before, CSAT equivalent; S:2906); R-10 open windows; `macro.missed_decisions` (S:1246) |
| `next_session(market, d)`, `prev_session(market, d)` (proposed helpers) | date | `effective_session`; counters in sessions of the book's primary-market calendar (RISK re-arm t+10, R-31 21-session dwell; S:1179, S:1182) |
| `fed_business_day`, `sifma_status`, `nyse_holiday` | bool / str / bool | publication rules; R-19 |
| `publication_instant`, `next_expected_obs`, `add_publication_bdays`, `source_skipped` | datetime / date / datetime / frozenset | `expected_available_utc`, `is_stale` (T:TASK-M1-16); cache-serving rule (T:TASK-M1-12); fixture refusal (T-FIX-01) |
| `usable_at(series_id, obs_date, market) -> datetime` | UTC | independent lag audit (`expected_usable_at_utc` in `lag_audit.violations[]`, S:3544); `timing_profile` (R-34) |
| `regime_tags(market, d) -> dict` | 13 keys (B6) | `macro_state.extras`; R-22 regime lines and episodes (T:TASK-M7-08, -10); R-18 structure-break log (T:TASK-M6-04); R-26 ban-period basis line; replay library (T:TASK-M9-04); tech-fund TF-05 regime flags on KRX cards (TF:160) |
| `kr_open_gap_session(event_utc)`, `gap_sessions(market, session_date)` | date; int ≥ 0 | event store and tags (T:TASK-M5-08, -09) |
| `status(market, decision_date)`, `check_coverage(...)` | dict; alerts | ARM precondition; Macro-page banner; `event_calendar.calendar_version` |
| Exceptions `NotASession`, `CalendarUnsigned`, `CalendarCoverageError` | — | data layer maps the last two to fail-closed acting inputs and conservative risk-model defaults |

---

## F. Ambiguities, contradictions and conservative readings

| # | Issue | Lines | Conservative reading adopted |
|---|---|---|---|
| 1 | Nothing is signed. The spec requires an owner sign-off on every file, and says `exchange_calendars` is never the source. The only calendar data in the repo is library-generated and unsigned | S:2001, S:2003, S:2100 | Ship draft files with `signed_off_by: null`. They are refused; KR and US acting inputs fail closed; books stay DISARMED. Tests use temp-dir fixtures. The build never writes a signature |
| 2 | T-CAL-02 runs from M1, but §12 lists "calendar coverage" among "the remaining OPS triggers" added at M5 | S:5551 vs S:6367 | Build the coverage check and the `calendar_coverage` OPS HALT in M1 (§9.0a and §9.0b "are the authoritative exit lists", S:5546; T:TASK-M1-05 says the same) |
| 3 | Coverage arithmetic: `min_sessions_ahead: 60` and `warn_at_sessions_left: 60` are equal | S:2077 | `sessions_left ≤ 60` warns (so a file at exactly 60 both satisfies the minimum and warns); `≤ 20` pages; outside coverage HALTs. An ARMED book under 60 only alerts |
| 4 | The regime-tag file must itself cover ≥ 60 sessions ahead, yet T-REGIME-01's expected file ends 2026-12-31. A KR file ending 2026-12-31 has exactly 60 sessions left after 2026-10-05 and 59 after 2026-10-06 (computed from the legacy KRX holiday list) | S:2090, S:2098 | Give every file an explicit `covers.to` separate from row effectiveness; the live regime file must extend into 2027 and be signed with the 2027 calendars. The expected-values test span stays 1995-01-01 … 2026-12-31 |
| 5 | Which `MissingInput.reason` an unsigned or unreadable calendar produces is not stated; the enum is `missing, stale, provisional_intraday, session_mismatch, synthetic_rejected` | S:993, S:1956, S:2088 | `MissingInput("missing")` with `fail_closed = true` and an alert code naming the calendar; risk-model inputs take the conservative default. No new enum value |
| 6 | "Fed business day": the spec names "the Fed holiday schedule" and "the Board is closed" but not which schedule applies when a holiday falls on a Saturday (Reserve Banks open the preceding Friday; the Board closed). LC: `fred_DEXKOUS.csv` is blank on 2017-11-10, 2021-12-31 and 2023-11-10 (Friday-observed Saturday holidays) while `fred_DGS3MO.csv` has values on those dates | S:1341-1342, S:2002 | Owner signs the FED set. Until then treat such Fridays as non-business days for H.10 and H.15 posting (later posting, so no look-ahead) |
| 7 | The source-skipped list is given as dates without a series mapping; Good-Friday years are not enumerated. LC: Good Fridays are blank in the H.15 series for 2016–2020, 2022, 2024, 2025 but present for 2021, 2023, 2026; DEXKOUS has values on every Good Friday; 2017-01-20, 2020-11-27, 2020-12-24 are blank in DEXKOUS only; 2018-12-05 in both; 2018-03-02 has a DEXKOUS value (the DC storm dates presumably concern DTWEXBGS, absent locally). DEXKOUS is also blank on 2018-12-24, 2019-01-14, 2019-02-20, 2021-01-20, which the spec does not list | S:1854, S:1963 | Key `source_skipped.yaml` by series (or channel) and date; owner signs. Do not infer membership from data at run time |
| 8 | H.15 observation calendar is not stated. LC shows H.15 observations follow the bond-market (SIFMA) closures, not the federal-holiday set | S:1390, S:1848 | The registry row names `obs_calendar`; the calendar layer offers both FED and SIFMA sets and assumes neither |
| 9 | Registry field names differ: `schedule_id`, `grace_pub_bdays` (R-19 inputs and pseudo-code) vs `publication_schedule`, `grace_publication_bdays` (§4.2, §7) | S:1833, S:1863 vs S:1390-1391, S:1901 | Use the §4.2 / §7 names in data; accept `grace_pub_bdays` as the contract attribute |
| 10 | `regime_tags` key names differ between §3.5's comment (`close_time`, `short_ban`, `sell_tax`) and R-20's table and tests (`close_time_kst`, `short_sale_ban`, `sell_tax_pct`) | S:1039-1040 vs S:2036-2047, S:2098 | The R-20 names (the rule text binds, S:963) |
| 11 | Value vocabulary is undefined for `closing_call`, `random_end`, `lunch_break`, `tick_regime`, `letf_rules`, `usdkrw_onshore_hours`, and for `fx_regime` outside `peg_1997` | S:2040-2047 | Values are whatever the signed expected-values file defines; draft proposals stay unsigned. Do not invent BoK regime names |
| 12 | Units differ by tag: `price_limit` is a fraction (0.08), `sell_tax_pct` is percent (0.20) | S:2098 | Keep both verbatim; cost code must not read `sell_tax_pct` as a fraction |
| 13 | `sell_tax_pct` anchors only: "0.30 (2019), 0.15 (2025), 0.20 (2026)"; the tech-fund trail adds 0.18% (2024) and "from 2026-01-01"; no local source gives the 2019–2023 steps or days | S:2044, TF:1119-1121 | Steps between anchors are OWNER; the point test (2026-10-02 = 0.20) is safe |
| 14 | `short_sale_ban` is boolean in the test, but 2021-05-03 … 2023-11-05 was a partial regime (index stocks resumed) per the tech-fund trail | S:2043, TF:1125 | Keep the boolean as the spec lists it (false in the partial period). If stock-level cards need the partial regime, add a separate tag by a signed revision; do not overload the boolean |
| 15 | `csat_session_kst` has a concrete pre-2016 value (10:00–16:00) while the rule table says the window "comes from the KRX notice (… UNVERIFIED until signed)" | S:2063 vs S:2013 | Treat 16:00 as a configured placeholder; the signed file governs. XC agrees with 10:00–16:00 for 2008–2015 |
| 16 | CSAT dates are not listed (one example). XC has CSAT rows only through 2020-12-03 and lists both 2017-11-16 and 2017-11-23 | S:2013 | OWNER list. Without it a CSAT day would be stamped with the regular close; a close printed after its bound then "fails closed with a calendar-review alert" (S:2031), which is the safe failure |
| 17 | `first_trading_day_open_kst: "10:00"` and the regular open are not effective-dated. XC shows 09:30 opens before 1998-12-07 and 10:30 first-day opens in 1995–1998 | S:2014, S:2065 | Opens do not enter the decision clock. `session().open` before the signed notice range is OWNER; the 10:00 rule applies as written inside it |
| 18 | `close_kst` has no start date. XC shows a 15:20 close before 1995 | S:2059 | KR coverage starts no earlier than the signed file's `covers.from` (1995-01-01 for tags; closes are needed from 1997-01-03, S:6026); earlier dates raise `CalendarCoverageError` |
| 19 | Required historical depth per holiday set is not stated | S:6026, S:6033 | Infer from consumers: KRX ≥ 1995-01-01; NYSE ≥ 1990 (US daily cards) and at least 2006 (T-TZ-01); FED and SIFMA ≥ 2015-01-01 (T-AVAIL-01, T-STALE-01); JPX, SSE, HKEX, TWSE ≥ the Korea-covariance span. Uncovered dates raise; a card on an uncovered span is refused |
| 20 | T-XMKT-01 says a same-date HKEX close "never is" usable, but HKEX half-days close at 12:00 HKT and the "if and only if" rule would admit them | S:1967 vs S:1892 | Never admit a same-date HKEX close (one extra day of lag in a covariance-only input; no look-ahead risk). Record as a signed-calendar question |
| 21 | Saturday closes: XC models pre-1998-12-12 Saturdays with the weekday 15:00 close, contradicting the spec's "own (half-day) close time" | S:2015 | No Saturday close without the owner's value; `decision_time_utc` on such a date raises until it is signed |
| 22 | Strictness of the publication comparison: R-01 uses `available_at_utc ≤ decision_utc`; the cross-market rule is strict with a 60 s buffer | S:1493, S:1892 | `≤` for publication-timed data, strict `<` with the buffer for closes of another market, exactly as written |
| 23 | The declared FRED VIX history lag is unmeasured | S:1426, S:6010 | Until measured, FRED `VIXCLS(D)` is usable from the US close of D+1 (`us_close_decision_bdays: 1`), never at the close of D |
| 24 | "test_per_change: required" has no stated mechanism | S:2053, S:2076 | The manifest of B1 rule 3; a file whose md5 is not in the manifest, or whose row names no test id, is refused |
| 25 | QF2-M5's "86 KRX-only and 156 NYSE-only sessions in 2016–26" vs XC's 85 and 150 over 2016-01-04 … 2026-09-25 | S:2107 | Evidence only, not a golden; do not assert either number |
| 26 | The legacy live engine (`core/markets`, `data/calendars/KRX.json`) has no CSAT special session for 2026 | repo | Outside R-20's text. Flag to the coordinator; do not change legacy behaviour inside this task |

---

## G. DO-NOT-BUILD items and invariants binding this area

Invariants
- **P0 read-only** (S:491): nothing here builds or imports an order path; calendar artifacts carry `read_only: true` (S:3811).
- **P5** (S:536-547): everything point-in-time; `decision_utc` from the effective-dated calendar; "Lags are calendar-based, never positional. Publication business days come from the publisher's calendar (Fed, SIFMA), not the equity trading-day index"; "Nothing is ever silently interpolated."
- **Never a constant** (S:1285, S:4160): no decision time, close time or bound hard-coded outside the calendar data and rules store.
- **Never roll** (S:2087): `decision_time_utc` on a non-session raises `NotASession`.
- **Never re-stamp** (S:2031): a close printed after its bound fails closed with a calendar-review alert. A changed bound "enters only as a signed calendar version" (T:TASK-M1-23).
- **Never observation-age staleness** (S:1956), including when the publication calendar is unreadable.
- **`exchange_calendars` is a cross-check only** (S:2003): it stays out of runtime dependencies and out of the signed data's provenance.
- **Holiday sets stay separate** (S:2074): no merged "US business day".
- **HALT scope** (S:1178): a calendar failure HALTs (OPS) every book that reads that calendar, never "the engine"; OPS re-arm is automatic once the calendar is signed or covered (S:1179); a `context_log` or `event_calendar` validation failure never HALTs.
- **P16** (S:636-639): nothing may freeze the book; an operational HALT clears when its cause clears.
- **No event tag changes any weight** (S:1634; `tags_change_weights: false`, `daily_book_blackouts: false`, S:4385-4386); gap flags and regime tags are annotations and display inputs.
- **Hermetic tests** (S:5491-5495): no network; fixtures md5-listed; tests write only to temporary copies.
- **No owner signature by the build** (B1 rule 7).

DO-NOT-BUILD (§10.2 "Events, calendars and data")
- Item 12 (S:6133-6136): 24-hour pre-event blackouts; swing-book blackouts around FOMC, CPI, NFP, BoK or export prints; a KRX quad-witching blackout; the index expiry-close fade.
- Item 13 (S:6137): calendar and supply-timing tilts (quarter-end tilts, KRW April seasonality, export-print tilts, issuance or IPO-window multipliers, buyback-blackout multipliers).
- Item 19 (S:6148-6155), data shortcuts: "H.10 or H.15 data used as if same-day"; "US-session data on KOSPI close-to-close returns of the same date"; positional lags on monthly series with gaps; intraday circuit-breaker prints as closes; a provisional, intraday or bar-derived row as an acting close.
- R-10 "Not built" (S:1635): 24-hour blackouts; daily-book blackouts; quad-witching blackout; momentum decision-day size-down.
- P19 (S:653): no regime-model state, acting or displayed. `regime_tags` are dated market-structure facts, not a model state. The spec lists only printing, logging and labelling uses for them (S:2049-2052); a use that changed exposure would need its own card.
