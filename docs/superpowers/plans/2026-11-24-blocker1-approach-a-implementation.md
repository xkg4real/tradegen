# Blocker 1 approach A (A1/A2) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver checklist task M7-T3: approach A's A1 (preview-only trade-list path, cross-checks, account-change evidence, the signed bid-gap limit) and A2 (live floor, gap and flow rules) as a sequence of small, independently reviewable PRs, starting with A1-1, the BR-26 signed bid-gap limit.

**Architecture:** A1 adds pure, preview-only modules under `execution_accounts/` (walk, path valuation, cross-checks, fee allocation, lots) plus the public read allowlist and a shared rate-limit hold, and wires them into `ContinuousUpbitCandidateSource` while its `__call__` keeps refusing. A2 then changes the live guard, controller, reducer and coordinator: entry block, epoch handover, floor at every point, flow adjustment, long intervals and app/owner units. A0 (PR #67, `tools/research/upbit_trade_probe.py`) is done and is not rebuilt; its algorithms are ported, never imported.

**Tech Stack:** Python 3 standard library only in `execution*` and `core/compliance` (`decimal`, `dataclasses`, `datetime`); `cryptography` Ed25519 only in the owner log and signer; the repo's own acceptance runners (`tests/<suite>_acceptance.py`, plain `assert` tests; `unittest` only under `tools/research/`). No new dependency.

**Spec:** `docs/superpowers/specs/2026-11-20-blocker1-held-interval-approach-a-design.md` (sections 3.1-3.8, 4, 5, 7, 9) and the owner decisions merged with it as PR #71 head `ba5f7fd` (main `41f255f`). The spec cites rev `1fd8792`; every `path:line` in this plan is current at HEAD (`41f255f`, whose tree equals `4de4379`). Only `tools/signer/sign.py` moved since `1fd8792` (the spec's `3157-3158` is now `3180-3181`).

## Global Constraints

- The repo is public: no private value (L, the daily loss limit, any signed Y, X, M, Md, any amount or account identifier) in code, tests, docs, commit messages or PR text; tests use obviously synthetic fixtures (for example 21000.0, 5000.0, Y 0.02) and the public 5% ceiling only.
- No network in tests: every test runs under the suite wrapper (`hermetic()`, temp `TRADEGEN_HOME`); transports are fakes.
- Never arm, sign, send an order or read keys or `.env`; never run `tools/signer/sign.py` interactively or anything that signs with a real key; tests use `tests/compliance_fixtures.py` `test_key()` (fixed public seed) only.
- The owner merges every PR and does every `code_approved`, `review-approve` and limit signature; sessions only open PRs.
- Line endings are preserved byte for byte (`.gitattributes`: `* -text`): the code files here are LF, some docs are CRLF; edit with the Edit tool or Python bytes, never `sed -i`; `git diff --stat` must equal `git diff --stat --ignore-cr-at-eol` before every push.
- D14 is the code-approval closure of `core/compliance/owner.py:998-1003` (`code_files`): `core/compliance/*.py`, `core/odds/*.py`, `execution/*.py`, everything under `execution_control/`, `execution_orders/`, `execution_accounts/`, `execution_network/`, `execution_launch/`, `tools/owner/`, and every repo file they import; any edit there changes the code hash and needs the one later `code_approved`. `tools/signer/` and `tools/research/` are outside D14.
- The driver identity list is `execution_launch/driver.py:38-85` `_SOURCE_FILES` (46 files) and `:88-92` `_CARRY_SOURCE_FILES` (49), mirrored by `tools/signer/sign.py:1415-1462` `_REVIEW_SOURCES` and `:1464-1468` `_REVIEW_CARRY_SOURCES`; editing a listed file changes `deployment_code_sha256`; a new module imported by a listed file is added to all four lists in the same PR.
- A change to `tools/signer/sign.py` or to the owner-log schema needs the owner's code approval; that PR's body says so in its first paragraph.
- `tests/renewal_boundaries.py:21-38` `INITIALIZERS` pins the module-level surface (imports, declarations, classes, defaults) of 16 files, including `execution/transport.py`, `execution/upbit_inquiry.py`, `execution_accounts/collector.py`, `model.py`, `provider.py` and `execution_control/risk.py`; a PR that changes one of those surfaces re-pins that one value in the same PR, after reviewing the new top-level code, and says so in the PR body (checked by `tests/control_guards.py:238-245`).
- A1 lands before the study freeze: `execution_launch/study.py:63-65` `CAPTURE_FILES` hashes `execution/transport.py` and `execution/upbit_inquiry.py`, so A1-2 and A1-3 move the study capture digest. This is intended: the frozen study must capture with the trade-list allowlist and the rate-limit hold in place. No A1 PR edits `study.py` or adds a module to `CAPTURE_FILES`; the fixed and carry capture digests move only through those two hashed files. If universe PR 5 hashes the same two files in its own `UNIVERSE_CAPTURE_FILES`, that digest moves too, so whichever merges second re-runs its capture-digest tests. No A1 or A2 PR edits `execution_accounts/quotes.py`.
- The coordinator stays rehearsal-only (`execution_launch/coordinator.py:394`, `COORDINATOR_MODE_UNSUPPORTED`) and `ContinuousUpbitCandidateSource.__call__` keeps raising `CONTINUOUS_LIVE_RISK_INTEGRATION_REQUIRED` (`execution_launch/account_interval.py:481-482`) until controlled mode (M7-T6) and A2-8.
- Never `git add -A`; add exact paths. Every commit message ends with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

---

## PR sequence

A1 is preview only: nothing in A1 changes what the live path accepts, except that A1-6 stops refusing old marks and A1-9/A1-10 stop refusing evidence the old collector rejected (those refusals are replaced by records the preview path consumes). The committing flat producer `upbit_interval_frame` (`execution_launch/account_interval.py:98-138`, used by `UpbitIntervalSource.collect` `:154-182`) keeps its boundary bracket (`:111-117`) and its flat-only refusal (`:118-126`) through A1; A2-6 and A2-8 change them. A2 changes live behaviour and stays behind the rehearsal-only coordinator until M7-T6.

Dependency keys: O27 = PR #71 merge (done 2026-11-24 18:40:59 KST, `41f255f`); O28 = the owner's A0 observation run; O30 = PR #70 merge (BR-26 research tool, after M11-T3a fixes); PR #69 = Android/Windows alert draft (M7-T10); M7-T8 standing deployment (`standing_armed`, `sign.py`, owner-log fold); M7-T10 Telegram and HTTPS passkey approval; M7-T11 protective sell execution and the end-slot target 0.

### A1-1: BR-26 signed bid-gap limit

- **Goal:** the owner log and the independent signer accept an optional third `limit_set` field `bid_gap_fraction` (exact decimal, `0 < f <= 0.05` inclusive; malformed, nonfinite or out-of-range refused); two-field records and their signatures stay valid; D12 folds the new field; `owner.bid_gap_fraction(state)` returns the effective static Y; `risk.judge_bid_gap` is the pure BR-10 judgment.
- **Rules:** BR-26 (static signed limit: "BR-26, owner decision" paragraph and the static half of "Implementation boundary"), BR-10 (judgment), OQ10 (the judgment's flag only; the live buy gate is A2-1).
- **Files:**
  - Modify `core/compliance/owner.py:158-159` (`limit_set` schema), `:172-173` (after `_DATA`, add `_OPTIONAL`), `:176-191` (`_data_problem`, lines 183 and 185), `:628-637` (owner-state imports, new `_FOLD_KEYS`, `_TIGHTER`; `_LIMIT_KEYS` stays two keys because `tests/odds_plan.py:142` pins it to `core/odds/plan.py:41`), `:745` and `:768` (fold pairs and the `limits=` filter use `_FOLD_KEYS`), insert before `:775` (`bid_gap_fraction`).
  - Modify `tools/signer/sign.py:38-42` (help text), `:217-218` (`SCHEMAS["limit_set"]`), `:233` (after `_DATA`), `:236-250` (`_data_problem`, lines 243 and 245).
  - Modify `execution_control/risk.py` (append after `:511`).
  - Tests: `tests/compliance_owner.py` (append after `:1019`), `tests/compliance_signer.py` (append after `:2013`), `tests/control_risk.py` (append after `:400`), `tests/renewal_boundaries.py:32` (reviewed re-pin of the `risk.py` initialization surface).
- **D14:** yes (`owner.py`, `risk.py`). **Driver identity:** both files are listed (`driver.py:81` owner.py, `:61` risk.py; mirrors `tools/signer/sign.py:1458`, `:1438`), so the hash moves; no list change. **sign.py:** yes, schema copy and help text; owner code approval required. **CAPTURE_FILES:** no.
- **Tests:** see "A1-1 detailed tasks" (9 compliance tests, 5 risk tests).
- **Depends on:** O27 (done). Independent of every other PR here. M7-T8 also edits `sign.py` and the owner-log fold: A1-1 lands first and M7-T8 rebases on it.
- **Owner steps:** review the owner-log schema and signer change (code approval in the PR body), merge. Signing a private Y comes after the single `code_approved` (spec section 8).

### A1-2: Public read allowlist for the trade list and 1-minute candles

- **Goal:** `GET /v1/trades/ticks` and `GET /v1/candles/minutes/1` (no trailing slash) are allowed public reads and capture endpoints, with fixed helpers in the `daily_candles` style.
- **Rules:** none owned; enables BR-2 (A1-4) and BR-8 (A1-8).
- **Files:**
  - Modify `execution/upbit_inquiry.py:17-23` (`ENDPOINTS`), `:24-29` (`READ_CAPTURE_ENDPOINTS`), `:30-31` (`PUBLIC`), `:34-36` (path constants), append helpers after `:100`.
  - Modify `tests/execution_guards.py:855-859` (`READ_CAPTURE_ENDPOINTS_PIN`), `:1129-1133` (expected Upbit set), `:1149-1154` (asserts, exact `PUBLIC`).
  - Modify `tests/execution_read_capture.py:69-73` (rename and widen to 11 pairs).
  - Modify `tests/execution_upbit.py` (twins after `:257` and `:279`).
  - Modify `tests/renewal_boundaries.py:25` (reviewed re-pin of the `execution/upbit_inquiry.py` initialization surface: new allowlist pairs and path constants; procedure as A1-1 Task 4).
  - Pocket transfer records (OQ11, N17): `execution/upbit_inquiry.py` has no pocket endpoint (`:17-31`) and is in `CAPTURE_FILES` (`execution_launch/study.py:63-65`), so the read must be decided here, before the study freeze. If N17 finds a documented read endpoint, add it to `ENDPOINTS` and `READ_CAPTURE_ENDPOINTS` in this PR with pinned tests; otherwise this PR adds none (see N17).
- **Interfaces (Produces):** `TRADES_TICKS_PATH = "/v1/trades/ticks"`, `TRADE_TICKS_COUNT_MAX = 500`, `trade_ticks_params(market: str, *, to: str | None, count: int, cursor: str | None, days_ago: int | None) -> tuple[tuple[str, str], ...]` (`to` is `HH:MM:SS`, `cursor` a decimal string, `days_ago` 1-7 or None), `trade_ticks(market: str, *, to: str | None = None, count: int = 500, cursor: str | None = None, days_ago: int | None = None) -> Answer`; `MINUTE_CANDLES_PATH = "/v1/candles/minutes/1"`, `minute_candles(market: str, to: datetime, count: int) -> Answer` (reuses `candle_params`). All refuse with `InquiryRefused` before any send.
- **D14:** yes (`execution/`). **Driver identity:** no. **sign.py:** no. **CAPTURE_FILES:** the tuple is unchanged but `upbit_inquiry.py`'s hash moves the study capture digest.
- **Tests:**
  - `tests/execution_guards.py::test_allowlists_are_pinned` (updated): `ENDPOINTS` has 17 pairs, `READ_CAPTURE_ENDPOINTS` 11, `PUBLIC` 7, capture set still a strict subset.
  - `tests/execution_read_capture.py::test_exact_capture_subset_is_eleven_existing_get_pairs` (renamed from `..._nine_...`): the exact 11-pair set.
  - `tests/execution_upbit.py::test_trade_list_and_minute_candle_helpers_send_fixed_keyless_gets`: exact path and param order, only `Accept` sent (no `Origin`), no trailing slash, `to` quoted as `%3A`.
  - `tests/execution_upbit.py::test_trade_list_and_minute_candle_helpers_refuse_bad_input_before_any_send`: count 0 and 501, `days_ago` 0 and 8, `KRW-KRW`, naive candle `to`, non-digit cursor, malformed `to` all refuse with no send.
  - `tests/launch_upbit_read_archive.py:163` `test_record_codec_acceptance_does_not_allow_excluded_endpoint_archival` must still pass unchanged (it uses an excluded path).
  - `tests/control_guards.py::test_renewal_*` pass after the `:25` re-pin.
- **Depends on:** nothing here. Before the study freeze. N17 is decided before this PR's detailed plan.
- **Owner steps:** merge.

### A1-3: Venue rate-limit hold and shared public read budget

- **Goal:** a 429 or 418 is never retried inside its wait; the status, `Retry-After` and `Remaining-Req` reach the caller; a persisted hold shared across units, processes and restarts refuses public reads before send until it expires.
- **Rules:** BR-18 (rate-limit and retry semantics; the coordinator lock and status progress are delivered in A2-6), OQ17 and BR-24 "Public read capacity" (the shared hold and the unknown-sharing default; egress tracking is N18).
- **Files:**
  - Modify `execution/transport.py:54-57` (constants), `:293-373` (`request`; retry branches `:342-345` connection, `:359-362` 429/5xx: 429 no longer retried, 5xx and connection errors still once), `:545-563` (`_check_answer`: 418/429 raise `VenueRateLimited`). `_send` stays byte-identical (`SEND_SOURCE`, `tests/execution_guards.py:787-793`); `Answer` (`:89-96`) and `UpbitReadEvent` (`:99-114`) stay unchanged, so `READ_CAPTURE_AST_SHA256` (`tests/execution_guards.py:853-854`) moves only if `_check_answer` is inside its hashed region: re-pin it in this PR with a one-line note if it moves.
  - Modify `tests/renewal_boundaries.py:24` (reviewed re-pin of the `execution/transport.py` initialization surface: new constants and `class VenueRateLimited`; procedure as A1-1 Task 4).
  - Create `execution_accounts/public_read_budget.py` (not `execution_launch/`: the launch guard rejects every `execution.transport` import there, `tests/launch_guards.py:575-577, 584-586`, except the exact archive capture import `:513-519`). Lock with `O_EXCL` plus a JSON hold in one configured coordination directory, using the A0 probe's file names and formats (`upbit-public-session.lock`, `upbit-public-cooldown.json` with exactly `retry_at_unix` and `status`; `tools/research/upbit_trade_probe.py:238-294`, `_retry_deadline` `:222-235`), re-implemented, so the app and the probe's `--coordination-dir` (`:666`) honour each other's holds when pointed at the same folder (O28 uses `%USERPROFILE%\TRADEGEN-A0\public-budget`); QUANTGEN readers on the same route join by the same documented format (N18).
  - Modify `tests/accounts_guards.py:21-27` (`TRANSPORT_IMPORTS["public_read_budget.py"] = frozenset({"InquiryRefused", "VenueRateLimited"})`) and add a reviewed write exception for the lock and hold file beside `CHECKPOINT_WRITES`.
  - Modify tests `tests/execution_transport.py:776` (`test_a_get_is_retried_once_on_connection_errors_429_and_5xx` becomes `test_a_get_is_retried_once_on_connection_errors_and_5xx_but_never_on_429`), `tests/execution_read_capture.py:104, 179, 210, 228, 251` (replace 429 with 503 so they keep testing the retry path), `tests/launch_upbit_read_integration.py:194` (`test_retry_keeps_first_429_or_503_and_second_response_under_one_logical_call` loops over 503 only; a new 429 case asserts one attempt and a refusal carrying the `VenueRateLimited` fields). Before the detailed plan, grep `tests/` for `429` (today also `tests/execution_transport.py:806`, the KIS POST message, `tests/launch_strategy.py`, `tests/engine_acceptance.py`, `tests/quant_acceptance.py`) and list every test that relies on a 429 retry.
  - Create `tests/accounts_public_read_budget.py`; register it in `tests/accounts_acceptance.py:9` `MODULES` (completeness test `tests/accounts_guards.py:264`).
- **Interfaces (Produces):** `class VenueRateLimited(InquiryError)` with `status: int`, `retry_after_s: int | None`, `remaining_req: str | None`, `server_utc: datetime | None` (message unchanged: `"upbit <path>: HTTP 418"`); `class PublicReadBudget` with `__init__(self, root: Path)`, `hold_until(self) -> datetime | None`, `record(self, error: VenueRateLimited, *, now: datetime) -> datetime`, `check(self, *, now: datetime) -> None` (raises `InquiryRefused("PUBLIC_READ_HOLD")` while held or while another participant holds the session lock). Every public-read caller (the A1-4 walker, the A1-8 audit, the A1-13 path source) calls `check` with its clock before each request and `record` on a caught `VenueRateLimited`. It is not registered through `inquiry_guard`: transport calls each guard as `guard(stage)` and turns any guard exception into `InquiryRefused("E1_GUARD_REFUSED")` (`execution/transport.py:416-421`), which would hide `PUBLIC_READ_HOLD`. Pacing assumes shared capacity at all times (the BR-24 default for unknown sharing); there is no per-process allowance that ignores the hold.
- **D14:** yes. **Driver identity:** not yet (`public_read_budget.py` is listed in A1-13 when a listed file imports it). **sign.py:** no here. **CAPTURE_FILES:** `transport.py`'s hash moves the study capture digest.
- **Tests:**
  - `test_a_get_is_retried_once_on_connection_errors_and_5xx_but_never_on_429`: sleeps `[0.2]` after a 429 and `VenueRateLimited.retry_after_s` carries the header.
  - `tests/accounts_public_read_budget.py::test_429_and_418_hold_reads_until_retry_after_across_restarts`: a new `PublicReadBudget` on the same root still refuses (port of probe test `:511`).
  - `::test_absolute_deadline_honours_server_duration_when_the_local_clock_is_ahead` (port of `:522`).
  - `::test_418_without_retry_after_uses_the_conservative_backoff_and_never_shortens_a_longer_hold`.
  - `::test_hold_refuses_before_send_and_never_touches_the_network` (fake transport records zero sends; the refusal code is `PUBLIC_READ_HOLD`).
  - `::test_a_hold_or_session_lock_written_in_the_probe_format_is_honoured_and_ours_is_readable_by_the_probe` (byte format shared with `tools/research/upbit_trade_probe.py:238-294`).
  - `tests/control_guards.py::test_renewal_*` pass after the `:24` re-pin.
- **Depends on:** nothing here (parallel to A1-1 and A1-2).
- **Owner steps:** merge; confirm the PC/network arrangement during A0 (OQ17) and point the app and the probe at the same coordination folder.

### A1-4: Trade-list walk, read gate and reach

- **Goal:** a pure walker reads `[S, E)` of one coin's public trade list only after the read gate, pages by cursor, de-duplicates and refuses every partial or unordered outcome.
- **Rules:** BR-1, BR-2, BR-17 (the reach refusal; the live chain stop is OQ7 in A2-6).
- **Files:**
  - Create `execution_accounts/trade_list.py` (calls only `execution/upbit_inquiry.py` helpers, the `execution_accounts/universe.py:18-19` pattern, so it holds no `/v1/` literal); parse with `execution_accounts/collector.py:23-62` `number`/`instant` and `:77-99` `SourceReceipt`.
  - Modify `tests/accounts_guards.py:21-27` (`TRANSPORT_IMPORTS["trade_list.py"] = frozenset({"Answer", "inquiry_clock"})`).
  - Create `tests/accounts_trade_list.py`; register it in `tests/accounts_acceptance.py:9` `MODULES` (completeness test `tests/accounts_guards.py:264`).
- **Interfaces (Produces):** `SETTLE = timedelta(seconds=1)` (fixed from A0), `REACH_UTC_DAYS = 7`; `@dataclass(frozen=True, kw_only=True) class PublicTrade: market: str; trade_id: int; at: datetime; price: Decimal; volume: Decimal; ask_bid: str`; `@dataclass(frozen=True, kw_only=True) class TradeWalk: market: str; start: datetime; end: datetime; trades: tuple[PublicTrade, ...]; receipts: tuple[Answer, ...]; gate_server_utc: datetime`; `walk_trade_list(fetch: Callable[..., Answer], *, market: str, start: datetime, end: datetime, gate_server_utc: datetime, max_pages: int) -> TradeWalk`. Refusal codes (`TradeListError(code)`): `TRADE_LIST_READ_GATE_NOT_REACHED`, `TRADE_LIST_DATE_HEADER_REQUIRED`, `TRADE_LIST_SERVER_DAY_MISMATCH`, `TRADE_LIST_TRADE_ID_CHANGED`, `TRADE_LIST_CURSOR_NOT_PROGRESSING`, `TRADE_LIST_PAGE_LIMIT_REACHED`, `TRADE_LIST_BEYOND_REACH`, `TRADE_LIST_ROW_INVALID`.
- **D14:** yes. **Driver identity:** listed in A1-13. **sign.py:** no here. **CAPTURE_FILES:** no.
- **Tests (`tests/accounts_trade_list.py`):**
  - `test_walk_paginates_by_received_cursor_and_deduplicates_by_id` (port of probe `:212`): duplicates dropped, ids never assumed ordered.
  - `test_walk_refuses_a_cursor_loop_after_retaining_pages` (`:226`).
  - `test_walk_refuses_a_changed_row_for_the_same_id` (`:234`).
  - `test_walk_reads_both_utc_days_across_0900_kst_and_omits_to_at_utc_midnight` (`:245`).
  - `test_walk_refuses_a_server_day_mismatch_and_a_missing_date` (`:259`, `:267`).
  - `test_interval_membership_is_half_open_by_millisecond` (`:290`): `S <= at < E`.
  - `test_page_limit_fails_the_path_instead_of_returning_a_partial_walk` (`:202`): `TRADE_LIST_PAGE_LIMIT_REACHED`, never a bounded result.
  - `test_read_gate_requires_server_time_at_or_after_end_plus_settle_plus_one_second`: one second short refuses with no request sent.
  - `test_start_beyond_seven_utc_days_refuses_beyond_reach`.
  - `test_every_page_request_has_no_origin_header_and_no_trailing_slash` (fake transport capture).
- **Depends on:** A1-2, A1-3; O28 for the final `SETTLE` (code lands with 1 s). Resolve open questions N1-N3 first.
- **Owner steps:** merge; run A0 (O28).

### A1-5: Trade-path valuation for every coin

- **Goal:** a pure fold values the account at every point of `[S, E)` from the walks, our fills and flows, with exact extremes.
- **Rules:** BR-4, BR-24 (coin set), OQ13 (coverage: owner, out-of-universe and dust holdings get paths; unlisted at 0).
- **Files:** Create `execution_accounts/trade_path.py`; create `tests/accounts_trade_path.py`, register in `tests/accounts_acceptance.py:9`.
- **Interfaces:** Consumes `PublicTrade`, `TradeWalk` (A1-4), `execution_control/risk.py:109-126` `Fill`, `execution_accounts/model.py:79-85` `ExternalFlow`. Produces `@dataclass(frozen=True, kw_only=True) class TradePathValuation: opening_equity_krw: Decimal; closing_equity_krw: Decimal; minimum_equity_krw: Decimal; minimum_at: datetime; maximum_equity_krw: Decimal; maximum_at: datetime; closing_marks: tuple[tuple[str, Decimal, datetime], ...]; points: int`; `coins_needing_paths(*, opening_units: Mapping[str, Decimal], fills: tuple[Fill, ...], flows: tuple[ExternalFlow, ...], residual_symbols: frozenset[str], unlisted: Mapping[str, datetime]) -> tuple[str, ...]`; `value_trade_path(*, start: datetime, end: datetime, opening_cash_krw: Decimal, opening_units: Mapping[str, Decimal], opening_marks: Mapping[str, tuple[Decimal, datetime]], walks: Mapping[str, TradeWalk], fills: tuple[Fill, ...], flows: tuple[ExternalFlow, ...], unlisted: Mapping[str, datetime]) -> TradePathValuation`.
- **D14:** yes. **Driver identity:** listed in A1-13. **sign.py / CAPTURE_FILES:** no.
- **Tests:**
  - `test_same_millisecond_set_is_judged_at_every_price_with_holdings_before_and_after_our_fill`: the minimum does not depend on row order inside one millisecond.
  - `test_extremes_include_opening_and_closing_values_and_every_print`: no filtering (Q8).
  - `test_unlisted_coin_drops_to_zero_at_the_listing_read_as_a_judged_point`.
  - `test_every_coin_with_a_balance_fill_flow_or_residual_gets_a_path_except_unlisted`.
  - `test_owner_out_of_universe_and_dust_holdings_are_valued`.
  - `test_valuation_is_exact_and_independent_of_ambient_decimal_context`.
  - `test_incoming_coin_flow_uses_the_higher_and_outgoing_the_lower_of_mark_and_next_trade` (BR-21: a stale mark at `done_at` never creates a gain).
- **Depends on:** A1-4.
- **Owner steps:** merge.

### A1-6: Marks without an age limit and bid evidence in the capture

- **Goal:** the collector keeps the last trade as the mark however old, records the best bid as capture evidence (not into `Position`), records an unreadable bid or empty book instead of refusing, and the provider and continuous checks stop refusing old marks while still refusing future ones.
- **Rules:** BR-3 (and the BR-20 rows it replaces: `provider.py:236`, `upbit_collector.py:436-438, 450-458`, `continuous.py:198-199, 233-234`).
- **Files:**
  - Modify `execution_accounts/upbit_collector.py:132-141` (`_best_bid` returns `None` for an empty book instead of refusing), `:436-438`, `:444-458` (unlisted branch `:447-449` unchanged), `CollectionResult` (gains `bid_observations: tuple[BidObservation, ...] = ()`).
  - Modify `execution_accounts/provider.py:234-237` (drop `_fresh` at `:236` for held-coin marks; keep the no-future check and the unlisted checks).
  - Modify `execution_accounts/continuous.py:198-199`, `:233-234` (remove the 30 s age, keep "not after S").
  - Tests: `tests/accounts_collector.py:336-350, 403-416`, `tests/accounts_provider.py` (`test_stale_fx_prices_or_restrictions_are_not_relabelled_fresh`, positions case), `tests/accounts_continuous.py`.
- **Interfaces:** Produces `@dataclass(frozen=True, kw_only=True) class BidObservation: symbol: str; mark: Decimal; mark_at: datetime; server_at: datetime; bid: Decimal | None` (in `execution_accounts/upbit_collector.py`); the collector has no Y, so judging with `risk.judge_bid_gap` (A1-1) happens in the path source (A1-13).
- **D14:** yes. **Driver identity:** `upbit_collector.py`, `provider.py`, `continuous.py` are listed; hash moves; no list change. **sign.py / CAPTURE_FILES:** no.
- **Tests:**
  - First add the missing tests the continuous map names (`CONTINUOUS_OPENING_MARK_STALE_OR_FUTURE`, `COLLECTOR_TICKER_STALE_OR_FUTURE`) on HEAD, then change them: `tests/accounts_continuous.py::test_opening_mark_of_any_age_is_accepted_but_a_future_one_refuses`.
  - `tests/accounts_collector.py::test_stale_last_trade_stays_the_mark_and_the_bid_is_recorded_as_evidence` (replaces `:336`).
  - `::test_a_thin_coin_keeps_its_last_trade_mark_and_an_empty_book_is_recorded_not_refused` (replaces `:403`; OQ10).
  - `tests/accounts_provider.py`: the positions case accepts an old mark and refuses a future one.
  - The unlisted tests (`tests/accounts_collector.py:363, 377, 419, 434`) pass unchanged.
- **Depends on:** A1-1 (input shapes of `judge_bid_gap`), A1-5.
- **Owner steps:** merge.

### A1-7: Ticker and own-fill cross-checks

- **Goal:** pure checks that turn a ticker/trade-list mismatch or an own-fill miss into a check-block-alert finding (preview record only; no journal write yet).
- **Rules:** BR-6, BR-7.
- **Files:** Create `execution_accounts/path_checks.py`, `tests/accounts_path_checks.py` (register in `tests/accounts_acceptance.py:9`).
- **Interfaces:** Produces `@dataclass(frozen=True, kw_only=True) class CheckFinding: kind: str; symbol: str; price: Decimal; at: datetime; evidence_sha256: str` with kinds `TICKER_MISMATCH`, `OWN_FILL_MISS`, `CANDLE_LOW`, `CANDLE_HIGH`, `CANDLE_MINUTE`; `ticker_findings(walk: TradeWalk, ticker_trade: PublicTrade, *, to_bound: datetime) -> tuple[CheckFinding, ...]`; `own_fill_findings(walk: TradeWalk, fills: tuple[Fill, ...], *, prevented_order_ids: frozenset[str]) -> tuple[CheckFinding, ...]`.
- **D14:** yes. **Driver identity:** A1-13. **sign.py / CAPTURE_FILES:** no.
- **Tests:**
  - `test_ticker_trade_before_to_missing_from_the_walk_is_a_mismatch_at_the_ticker_price`.
  - `test_ticker_trade_at_or_after_to_is_not_compared`.
  - `test_ticker_trade_older_than_start_is_compared_with_the_opening_mark` (open question N4 default).
  - `test_own_fill_matches_by_millisecond_price_and_volume_without_ask_bid` (OQ18 leaves `ask_bid` unresolved).
  - `test_self_match_prevented_volume_is_not_a_miss_but_the_orders_fills_are_checked`.
  - `test_a_miss_yields_a_finding_at_our_fill_price`.
- **Depends on:** A1-4, A1-5.
- **Owner steps:** merge.

### A1-8: Minute-candle audit (lagging)

- **Goal:** once a 1-minute candle is final, compare its low and high with the path's trades in that minute; a mismatch is a finding at the candle low; the candle high never raises H.
- **Rules:** BR-8.
- **Files:** Create `execution_accounts/candle_audit.py` (reads through `upbit_inquiry.minute_candles`, A1-2); `tests/accounts_candle_audit.py` (register).
- **Interfaces:** Produces `CANDLE_FINALITY = timedelta(seconds=...)` (from A0), `audit_minutes(trades: tuple[PublicTrade, ...], candles: tuple[MinuteCandle, ...], *, now_server: datetime) -> tuple[CheckFinding, ...]`; `@dataclass(frozen=True, kw_only=True) class MinuteCandle: market: str; start: datetime; low: Decimal; high: Decimal`.
- **D14:** yes. **Driver identity:** A1-13. **sign.py / CAPTURE_FILES:** no.
- **Tests:** `test_candle_low_below_the_paths_lowest_trade_is_a_finding_at_the_candle_low`; `test_candle_high_above_the_paths_highest_trade_is_a_finding_and_never_a_new_high`; `test_candle_for_a_minute_without_a_path_trade_and_the_reverse_are_findings`; `test_a_minute_that_is_not_final_yet_is_not_audited`; `test_minutes_of_long_intervals_are_covered`.
- **Depends on:** A1-2, A1-4, A1-7 (`CheckFinding`); O28 for `CANDLE_FINALITY`.
- **Owner steps:** merge.

### A1-9: Per-fill fee allocation

- **Goal:** replace the three fee refusals with captured `trade_fee` first, a pro-rata remainder by funds (rounded down in integer fee quanta, residue on the last fill), and the notional fallback with an allocation record and alert.
- **Rules:** BR-5, OQ15.
- **Files:** Modify `execution_accounts/upbit_collector.py:247-264` (`_fees`), `:356-364` (the `Inexact` trap stays; allocation is done in integer quanta so it never signals), `CollectionResult` (gains `fee_allocations: tuple[FeeAllocation, ...] = ()`); tests `tests/accounts_collector.py:158` (rewritten), `:173` (kept), `tests/launch_account_interval.py:275` (fee half of `test_flow_and_fee_coverage_refuse`), `tests/launch_guard_capture_material.py:327`.
- **Interfaces:** Produces `@dataclass(frozen=True, kw_only=True) class FeeAllocation: order_id: str; method: str; parts: tuple[tuple[str, Decimal], ...]; alert: bool` with methods `captured`, `pro_rata_remainder`, `notional_fallback`.
- **D14:** yes. **Driver identity:** `upbit_collector.py` listed; hash moves. **sign.py / CAPTURE_FILES:** no.
- **Tests:** `test_uncaptured_fills_split_the_fee_remainder_by_funds_rounding_down_with_the_residue_last` (replaces `test_multitrade_order_does_not_guess_fee_allocations`); `test_no_captured_fill_splits_the_whole_paid_fee_by_funds`; `test_negative_remainder_or_a_captured_mismatch_falls_back_to_notional_keeps_paid_fee_and_alerts`; `test_zero_fee_multitrade_and_unused_fee_evidence_are_distinguished` (`:173`, unchanged); `test_allocation_parts_sum_exactly_to_paid_fee_under_a_trapping_context`.
- **Depends on:** A1-6 (same file; avoids conflicts). Open question N6 (fee precision).
- **Owner steps:** merge.

### A1-10: Every account change recorded as evidence

- **Goal:** the collector and provider accept every order type, KRW and coin flows, pending flows (unsettled), withdrawal fees and, if A1-2 added a pocket read under N17, pocket records, replacing the exclusive-account fence and lock equalities with recorded differences. Without that read a pocket move is an unresolved OQ8 residual.
- **Rules:** BR-21, OQ1, OQ11.
- **Files:**
  - Modify `execution_accounts/collector.py:112-130` (`CoverageEvidence` fence fields replaced by a scope record).
  - Modify `execution_accounts/upbit_collector.py:237-243` (transfer scope), `:279-286` and `:313-321` (order types `limit`, `price`, `market`, `best`; `watch` per N9), `:325-343` (flows), `:402-405` (KRW and coin lock equalities become recorded differences), `:440-441` (fence check).
  - Modify `execution_accounts/provider.py:212-229` (coin flows into inventory, withdrawal fee in the cash rebuild), `:245-248` (inventory difference preserved as a residual record), `:268-298` (non-limit order quantities and reservations).
  - Modify `execution_accounts/model.py:79-85` (`ExternalFlow` gains `fee: Decimal | None = None`, `status: str | None = None`, omitted at default by `canonical`, `:19-38`, like `Position.unlisted` at `:21-23`).
  - Modify consumers `tools/owner/rehearsal.py:58-59, 134-145, 255, 400` and `execution_launch/guard_capture_format.py:159-165`.
  - Modify `tests/renewal_boundaries.py:27` and `:29` (reviewed re-pins of the `execution_accounts/collector.py` and `execution_accounts/model.py` initialization surfaces: `CoverageEvidence` and `ExternalFlow` fields; procedure as A1-1 Task 4).
- **Interfaces:** Produces `@dataclass(frozen=True, kw_only=True) class BalanceResidual: currency: str; observed: Decimal; expected: Decimal; status: str` (status `unresolved`), and `CollectionResult.residuals: tuple[BalanceResidual, ...] = ()`.
- **D14:** yes. **Driver identity:** `collector.py`, `upbit_collector.py`, `provider.py`, `model.py` listed; hash moves; no list change. **sign.py / CAPTURE_FILES:** no.
- **Tests:** `test_price_market_and_best_orders_are_accepted_with_their_own_quantity_rules` (replaces the `ord_type: price` case of `tests/accounts_collector.py:184`); `test_coin_and_krw_flows_pending_and_reversed_states_are_recorded_not_refused` (replaces `:194`); `test_withdrawal_fee_is_part_of_the_outflow`; `test_lock_differences_are_recorded_as_residuals_not_refused` (replaces `:135`); `test_fence_is_replaced_by_the_scope_record` (replaces `:209`, zero-inventory anchor kept); `tests/accounts_provider.py::test_coin_deposit_enters_inventory_and_an_unmatched_difference_is_preserved` (replaces `:153`, `:162`, `:293` cases); `test_canonical_bodies_of_existing_flows_are_unchanged` (digest stability); `tests/control_guards.py::test_renewal_*` pass after the `:27` and `:29` re-pins.
- **Depends on:** A1-9. Open questions N8-N11, N17.
- **Owner steps:** merge; enabling the pocket-management permission is a separate owner step (OQ11).

### A1-11: Classification, lot ledger and origin tags

- **Goal:** classify each change as `app`, `owner`, `deposit`, `withdrawal`, `pocket_transfer` or `unexplained`; keep per-coin FIFO lots with origin; charge owner-initiated outflows to free app units first; keep unresolved residuals with their evidence.
- **Rules:** BR-25, OQ8 (records and unresolved status; booking into equity is A2-4).
- **Files:** Create `execution_accounts/lots.py`, `tests/accounts_lots.py` (register).
- **Interfaces:** Consumes `CollectionResult` (A1-10), journal client ids (`execution_launch/committed_startup.py:520-521` test). Produces `ORIGINS = ("app", "owner", "deposit", "withdrawal", "pocket_transfer", "unexplained")`; `@dataclass(frozen=True, kw_only=True) class ClassifiedChange: origin: str; currency: str; units: Decimal; at: datetime; evidence_sha256: str; status: str`; `classify_changes(result: CollectionResult, *, journal_client_ids: frozenset[str]) -> tuple[ClassifiedChange, ...]`; `@dataclass(frozen=True) class LotLedger` with `apply(self, change: ClassifiedChange, *, free_app_units: Decimal) -> LotLedger`, `app_units(self, symbol: str) -> Decimal`, `owner_units(self, symbol: str) -> Decimal`.
- **D14:** yes. **Driver identity:** A1-13. **sign.py / CAPTURE_FILES:** no.
- **Tests:** `test_journal_client_id_makes_an_app_fill_whatever_its_prefix`; `test_empty_identifier_order_is_owner_only_after_reconciliation_else_unresolved`; `test_owner_outflow_is_charged_to_free_app_units_first_then_owner_units`; `test_units_locked_by_an_open_app_sell_are_not_charged`; `test_pocket_move_carries_lot_origin` (with records from the N17 read; without it, `test_pocket_move_without_transfer_records_stays_an_unresolved_residual`); `test_unexplained_residual_keeps_evidence_and_unresolved_status_until_linked_once`; `test_coin_deposit_creates_an_owner_lot` (N10).
- **Depends on:** A1-10.
- **Owner steps:** merge.

### A1-12: Boundary rebuild (preview)

- **Goal:** the Seoul-midnight and 22:00 boundary value is rebuilt from the first capture within 30 s after it (holdings and cash minus fills and flows in `[boundary, first read)`, prices at the boundary marks); the bracketed boundary unit is the first attempt and a slot or monitor capture inside the bound is the retry.
- **Rules:** BR-11, BR-12 (running case stops as today; the forgiven-gap branch is enabled by A2-6). Preview only: the rebuilt value is computed and archived on the candidate path; the committing flat producer keeps today's bracket acceptance (`execution_launch/account_interval.py:111-117`, `:154-182`, its docstring `:13-20`), and A2-6 switches it.
- **Files:** Modify `execution_launch/account_interval.py:44` (constant beside `BOUNDARY_LEAD_SECONDS`), `:304-306`, `:313` (`preview_continuous_upbit_interval`), `:431-436`, `:458` (`ContinuousUpbitCandidateSource.collect`); `execution_launch/guard_capture_material.py:259-265`, `:284` (mirror); tests `tests/launch_account_interval.py` (new candidate-source tests; the `UpbitIntervalSource` bracketing tests stay unchanged).
- **Interfaces:** Produces `BOUNDARY_REBUILD_BOUND = timedelta(seconds=30)`; `@dataclass(frozen=True, kw_only=True) class BoundaryValue: boundary: datetime; cash_krw: Decimal; units: tuple[tuple[str, Decimal], ...]; marks: tuple[tuple[str, Decimal, datetime], ...]; first_read_server_utc: datetime`; `rebuild_boundary(*, boundary: datetime, capture, changes_since: tuple, marks_at_boundary: Mapping[str, tuple[Decimal, datetime]]) -> BoundaryValue`; `boundary_status(*, boundary: datetime, first_read_server_utc: datetime | None, forgiven: bool) -> str` returning `REBUILT`, `MISSED` or `FORGIVEN_SPLIT`.
- **D14:** yes. **Driver identity:** `account_interval.py`, `guard_capture_material.py` listed; hash moves. **sign.py / CAPTURE_FILES:** no.
- **Tests:** `test_boundary_rebuilt_from_a_capture_29s_after_midnight_subtracts_fills_and_flows_since`; `test_capture_31s_after_the_boundary_is_missed_while_running`; `test_slot_20_to_30s_after_a_boundary_rebuilds_it_in_its_own_capture`; `test_rebuilt_value_is_computed_not_a_relabelled_later_balance`; `test_a_rebuilt_2200_within_the_bound_can_supply_recovery_proof`; `test_bracketing_capture_is_stamped_at_boundary_without_relabelling` and `test_after_2200_late_capture_never_becomes_boundary` (`tests/launch_account_interval.py:349, 372`, both on `UpbitIntervalSource`) pass unchanged.
- **Depends on:** A1-5, A1-10, A1-11.
- **Owner steps:** merge.

### A1-13: Capture schema 2 and the trade-list path source (preview wiring)

- **Goal:** `ContinuousUpbitCandidateSource` gets the trade-list path source; the coverage verifier re-reads and runs BR-6/BR-7; BR-10 is judged with `risk.judge_bid_gap` and the static Y from `owner.bid_gap_fraction`; a new capture schema keeps the raw trade-list, ticker, orderbook and candle responses and the BR-25 origin tag of every fill and flow; `__call__` still refuses. The committing flat source `UpbitIntervalSource` and its `upbit_interval_frame` refusal `:118-126` are unchanged (A2-8 removes it).
- **Rules:** BR-25 (origin tags in the capture archive); otherwise delivers the spec section 4 rows for `path_source` and the capture packet, and the BR-20 rows `continuous.py:157-159, 186` (receipt and watermark bound becomes `(E - S) + SETTLE + 1 s + READ_BUDGET`).
- **Files:**
  - Create `execution_accounts/trade_path_source.py` (transport users must live in `execution_accounts`; `execution_launch` may not hold `/v1/` literals or import transport, `tests/launch_guards.py:734-738`).
  - Modify `execution_launch/guard_capture_format.py:26` (`SCHEMA_VERSION = 2`, schema 1 still decoded), `:105`, `:140-213` (field pins, including the per-fill and per-flow `origin` from A1-11's `ORIGINS`), `execution_launch/guard_capture_material.py:31-41` (caps, `_TREE_TYPES`), `:130-139`, `execution_accounts/continuous.py:32-37` (new `COVERAGE_CONTRACT` value for the trade-list path), `:157-159`, `:186`, `execution_launch/account_interval.py:397-414` (wiring). `account_interval.py:118-126` stays: it is inside `upbit_interval_frame`, which only the committing `UpbitIntervalSource` (`:154-182`) calls; the candidate source never reaches it (`:416-473` goes through `path_source` and `preview_continuous_upbit_interval`).
  - Modify `execution_launch/driver.py:38-85` and `tools/signer/sign.py:1415-1462`: add `execution_accounts/trade_list.py`, `trade_path.py`, `path_checks.py`, `candle_audit.py`, `lots.py`, `trade_path_source.py` and `execution_accounts/public_read_budget.py` (whichever a listed file now imports).
  - Tests: `tests/launch_guard_capture_material.py`, `tests/launch_guard_capture_archive.py`, `tests/launch_account_interval.py` (new candidate-source tests; `test_held_inventory_interval_refuses_without_price_path` `:265` stays unchanged), `tests/compliance_signer.py::test_detached_review_source_closure_covers_each_lossless_history_dependency`, `tests/launch_driver_carry.py`, `tests/launch_carry_review.py`.
- **Interfaces:** Produces `class TradeListPathSource` with `__call__(self, previous, capture, end) -> ContinuousPath`-compatible preview (the existing `path_source(previous, capture, end)` call at `account_interval.py:454`); `READ_BUDGET` (from A0).
- **D14:** yes. **Driver identity:** yes, list grows (new modules). **sign.py:** yes (`_REVIEW_SOURCES` mirror) — owner code approval required. **CAPTURE_FILES:** no.
- **Tests:** `test_trade_list_capture_round_trips_raw_pages_ticker_book_and_candles_in_schema_two`; `test_fill_and_flow_origin_tags_round_trip_in_schema_two`; `test_schema_one_archives_still_replay_unchanged`; `test_candidate_source_with_the_trade_list_path_stays_preview_only` (`__call__` raises `CONTINUOUS_LIVE_RISK_INTEGRATION_REQUIRED`); `test_candidate_source_previews_true_extrema_for_held_inventory` (drives `ContinuousUpbitCandidateSource.collect` with the trade-list `path_source`; `test_held_inventory_interval_refuses_without_price_path` still passes on `UpbitIntervalSource` with `env.head.commits == []`); `test_bid_gap_is_judged_with_the_static_signed_y_in_force_before_the_observation`; `test_an_oversized_gap_refuses_with_an_explicit_code_never_truncates` (N12); the identity-list closure tests pass with the new files.
- **Depends on:** A1-1 and A1-3 through A1-12; O28 for `READ_BUDGET`.
- **Owner steps:** code approval of the `sign.py` mirror (PR body), merge.

### A1-14: Offline adaptive working-Y replay (research only)

- **Goal:** replay a candidate direction model's working-Y decisions over archived A1 observations under the static signed ceiling, offline, with `live_eligible=false`.
- **Rules:** BR-26 ("Directional evidence" and "Observation order and replay", offline half).
- **Files:** Extend PR #70's `tools/research/adaptive_bid_gap_replay.py` (`replay(document)`, schema `tradegen-adaptive-bid-gap-replay-v1`) and `tools/research/adaptive_bid_gap_preview.py` (`MAX_Y`, `evaluate`) once merged; create `tools/research/bid_gap_archive_adapter.py` and `tools/research/test_bid_gap_archive_adapter.py` (`unittest`). Outside D14; never imported by `execution*` or D14 files (CLAUDE.md 7.4).
- **Interfaces:** `read_observations(snapshot: Path, *, expected_sha256: str, cutoff: datetime) -> tuple[dict, ...]` (refuses data after the cutoff, checks hash and model version); `replay_with_ceiling(observations, *, signed_ceiling: Decimal, model: dict) -> dict`.
- **D14 / driver identity / sign.py / CAPTURE_FILES:** no.
- **Tests:** `test_a_proposal_applies_only_to_later_observations`; `test_an_increase_needs_a_later_clean_observation_at_the_prior_tighter_threshold`; `test_a_quote_failure_never_widens_y`; `test_restart_without_history_uses_the_static_signed_value_and_never_a_looser_one`; `test_duplicate_observation_keeps_the_first_result`; `test_a_smaller_signed_cap_clamps_from_its_effective_instant`; `test_every_working_y_is_within_zero_and_the_signed_ceiling_and_five_percent`; `test_output_is_never_live_eligible`; `test_a_directional_calibration_failure_keeps_the_working_y`; `test_same_quote_repricing_never_revises_a_past_quote`; `test_a_stale_proposal_is_retained_not_applied`; `test_an_increase_is_refused_while_a_block_stop_or_halt_is_outstanding`; `test_a_raised_signed_ceiling_never_lifts_a_tighter_working_y`.
- **Depends on:** O30 (PR #70 merged after M11-T3a), A1-1, A1-13; O32 only for QuantGPT inputs.
- **Owner steps:** merge O30 first; merge this PR.

### A2-1: Entry-block latch and durable alert record

- **Goal:** a durable `entry_block` journal latch that refuses every new buy (never a sell, cancel or the owner's exit); the `entry_unblock` journal kind, folded only when bound to the active block, account, deployment and policy terms with its authority evidence; the OQ10 gate that refuses every new buy and every buy preparation while no signed Y is in force; and a durable unique alert per (coin, kind, time) with per-channel attempts. No Controller method writes `entry_unblock` in this PR: the release method lands with M7-T10 and accepts only a verified approval object from the existing approval-broker contract (`tools/approval_broker/authority_contract.py`, WebAuthn verification), so no unverified release route exists before OQ9's routes are defined.
- **Rules:** BR-9(b) (latch and release record), BR-9(c) (durable record), OQ10 (live buy gate), OQ14 (record; remote delivery is M7-T10).
- **Files:** Modify `execution_control/store.py:25-28` (`EVENT_KINDS` gains `entry_block`, `entry_unblock`), `execution_control/controller.py:219-245` (`_event_data` shapes), `:280-412` (`_fold`), `:1051-1059` (`_buy_latches`: entry latch, and refuse while `owner.bid_gap_fraction(ctx.owner) is None` whatever the holdings); `execution_control/session.py:164-168` (`prepare_session` refuses with no signed Y in force, after `owner.load_context`); `execution_launch/continuous_guard_commit.py:196-200` (an `entry_block` is written only outside an open guard transaction); create `execution_launch/alert_store.py`; `execution_launch/coordinator.py:617-627` (`_toast_once` also persists); add `alert_store.py` to the identity lists and `sign.py` mirror. Existing buy and preparation tests sign a synthetic Y (0.02) in their fixture owner logs.
- **Interfaces:** `Controller.block_entries(*, cause: str, evidence_sha256: str, now: datetime) -> str` (block id); `entry_unblock` event data `{block_id, account_scope, deployment_sha256, policy_sha256, authority, evidence_sha256}`, folded only when every field matches the active block and terms; `AlertStore.record(*, coin: str, kind: str, at: datetime, body: str) -> str`, `AlertStore.attempt(alert_id: str, channel: str, *, ok: bool, now: datetime) -> None`.
- **D14:** yes. **Driver identity:** `store.py`, `controller.py`, `coordinator.py` listed (`session.py` is D14 but not in `_SOURCE_FILES`); `alert_store.py` added. **sign.py:** yes (mirror) — code approval. **CAPTURE_FILES:** no.
- **Tests:** `tests/control_store.py::test_invalid_payloads_and_events_never_extend_the_journal` (`:75`, extended to the new kinds); `tests/control_controller.py::test_entry_block_refuses_every_new_buy_but_never_a_sell_cancel_or_exit`; `::test_entry_unblock_must_name_the_active_block_account_deployment_and_policy`; `::test_entry_unblock_clears_only_its_block_and_leaves_daily_stop_halt_and_other_blocks` (journal rows written by the fixture store); `::test_no_entry_unblock_writer_exists_before_the_verified_release_route`; `::test_restart_leaves_the_entry_block_latched`; `::test_no_buy_is_admitted_on_a_flat_account_without_a_signed_y`; `tests/control_session.py::test_no_buy_is_prepared_on_a_flat_account_without_a_signed_y`; `tests/control_continuous_guard_commit.py::test_entry_block_is_never_written_inside_an_open_guard_transaction`; `tests/launch_alert_store.py::test_alert_is_unique_per_coin_kind_and_time_and_tracks_channels_separately`; `::test_a_failed_send_retries_from_the_record_and_a_successful_send_is_deduplicated`.
- **Depends on:** A1-13 (and A1-1's `owner.bid_gap_fraction`). PR #69 and M7-T10 consume the record; the release routes and the `entry_unblock` writer are outside (OQ9, M7-T10).
- **Owner steps:** code approval (mirror), merge.

### A2-2: Owner epoch handover and Y in the owner claim

- **Goal:** owner-log appends that leave the limit terms unchanged (including the app's own `system_halt`/`system_disarm`) no longer end the chain; intervals are cut where a D12 change takes effect; the owner claim carries the signed Y.
- **Rules:** BR-15 (with the signed-terms binding of BR-26's "Implementation boundary": `OwnerContextClaim`, `_owner_terms`, the producer's limit read).
- **Files:** `execution_launch/continuous_guard.py:63-75` (`OwnerContextClaim.signed_bid_gap_fraction: Decimal | None`), `:192-194` (`_owner_terms` compares limit terms, not the head), `:369-372`, `:464-465`, `:537-538`; `execution_launch/committed_account.py:73-74`, `:281-284`, `:358`; `execution_launch/committed_producer.py:277-306` (`_owner_read` adds `owner.bid_gap_fraction`), `:317-320`, `:467-468`, `:480`, `:492` (the bracket `:464-466` is A2-5's); `execution_launch/continuous_guard_commit.py:135-136`; `execution_control/controller.py:762-770`, `:774-782`; `execution_launch/guard_generation_format.py:38-39`, `:168-180`; `core/compliance/owner.py` new `limit_terms_at(check: LogCheck, *, at_utc: str, session_id: str | None) -> dict[str, float]` (the D12 terms in force at an instant, tightenings counted from their stamp; `owner_state` counts a tightening stamped after `now_utc` at once, so it cannot replay an instant).
- **D14:** yes. **Driver identity:** all listed; hash moves. **sign.py:** no. **CAPTURE_FILES:** no. The claim change moves every package digest: a new generation schema version or a reviewed re-anchor (N13).
- **Tests:** `test_owner_log_append_with_unchanged_limit_terms_continues_the_chain`; `test_a_tightening_inside_an_interval_cuts_it_at_the_entry`; `test_a_loosening_takes_effect_at_the_next_seoul_midnight_cut`; `test_cut_point_applied_floor_respects_raw_protections_and_the_new_signed_floor`; `test_limit_terms_at_replays_an_instant_without_future_tightenings`; update `tests/control_continuous_guard.py:228` and `tests/control_committed_account.py:248`.
- **Depends on:** A1-1, A2-1. Coordinate with M7-T9 (new owner epoch) and M7-T8 (owner-log fold): A2-2 owns BR-15, they build on it.
- **Owner steps:** merge.

### A2-3: Floor at every point, halt order and the check-block-alert re-check

- **Goal:** judge every path point against the flow-adjusted floor seeded from the controller fold and the signed L; carry a breach as the commit's in-transaction `halt` row before the baseline and guard advance; write `system_halt` only after completion through a Controller method; turn CBA findings into a re-check, an entry block and an alert; run the BR-8 candle audit live as a lagging step and hold its post-commit breach as a pending halt for the next commit.
- **Rules:** BR-8 (live scheduling of A1-8's `audit_minutes`), BR-9(a), BR-13, BR-14.
- **Files:** `execution_launch/continuous_guard.py:438-440` (closing-mark mismatch becomes CBA), `:470-474` (seed from `execution_control/controller.py:786-812` `_risk_view`), `:479-528`; `execution_launch/account_interval.py:346-349`; `execution_launch/continuous_guard_commit.py:366-385`; `execution_control/controller.py:814-838`, `:1381-1397` (fallback only); `tests/control_guards.py:205-211` keeps `append_system_entry` inside `controller.py`. The lagging audit: a coordinator step (`execution_launch/coordinator.py`, beside the monitor units) that, once `CANDLE_FINALITY` has passed for a minute, reads the final 1-minute candles through `execution_accounts/candle_audit.py`, reads that minute's path trades from the guard capture archive (`execution_launch/guard_capture_archive.py`, schema 2 from A1-13), covers the minutes of long intervals, and hands each finding to CBA and a breach to the pending halt; exact sites are fixed in this PR's detailed plan.
- **D14:** yes. **Driver identity:** listed; hash moves. **sign.py / CAPTURE_FILES:** no.
- **Tests:** `test_breach_at_an_interior_trade_halts_with_the_halt_row_before_baseline_and_guard`; `test_cba_price_rechecks_floor_and_daily_loss_and_sets_the_entry_block`; `test_daily_loss_breach_at_a_cba_price_sets_the_daily_stop_never_a_halt`; `test_candle_audit_breach_after_commit_is_held_as_a_pending_halt_for_the_next_commit`; `test_live_candle_audit_runs_only_after_finality_and_reads_archived_path_trades`; `test_live_candle_audit_covers_the_minutes_of_a_long_interval`; `test_candle_audit_finding_sets_the_entry_block_and_alert_at_once_and_the_halt_lands_in_the_next_commit`; `test_system_halt_reaches_the_owner_log_only_after_completion`; `test_guard_seed_uses_the_controller_fold_not_the_checkpoint_floor_alone`; update `tests/control_continuous_guard.py:153` and `tests/control_continuous_guard_commit.py:102`.
- **Depends on:** A2-1, A2-2; A1-8 and A1-13 for the audit and the archived trades.
- **Owner steps:** merge.

### A2-4: Flow-adjusted reducer and protected raw floors

- **Goal:** a flow-adjusted reducer convention with cumulative flow F and the protected raw principal and high-water amounts, journaled with each risk snapshot, judged at every point with the adjusted floor (BR-13) and used in buy admission; confirmed OQ8 residuals booked once, unresolved ones never.
- **Rules:** BR-22, BR-13 (the protected raw-KRW floor half), OQ2, OQ3, OQ8 (booking; A1-11 keeps the records).
- **Files:** `execution_accounts/baseline.py:51-65`, `:127-137` (`externally_cashflow_adjusted`, matching `execution_launch/profile.py:36`), `:140-150`, `:185-218` (schema 3), `:234`, `:278-283`, `:309-311`, `:315`, `:332-352`; `execution_accounts/model.py:171-180` (`RiskBaseline` fields omitted at default); `execution_accounts/baseline_bridge.py:61-62`, `:71-76`; `execution_control/controller.py:219-245`, `:295-317`, `:1061-1065`; `execution_launch/continuous_guard.py:420-426`, `:447`, `:480`; `execution_launch/guard_capture_material.py:308-311`; `execution_launch/account_interval.py:133`, `:385`; `docs/account-baseline-integration.md:200-218` (re-anchor carries F and both raw floors).
- **D14:** yes. **Driver identity:** listed; hash moves. **sign.py / CAPTURE_FILES:** no.
- **Tests:** `test_deposit_changes_f_once_and_creates_no_loss_allowance`; `test_withdrawal_cannot_lower_raw_principal_or_protected_high_water_floor`; `test_withdrawal_below_a_protected_floor_records_blocks_entries_and_alerts`; `test_adjusted_h_never_falls_on_a_flow_and_day_opening_stays_fixed`; `test_schema_three_digest_binds_the_flow_convention_and_schema_one_two_roundtrip_unchanged`; `test_moving_to_the_flow_convention_needs_the_reviewed_re_anchor`; `test_interior_point_below_the_protected_raw_floor_halts`; `test_confirmed_negative_residual_is_a_loss_judged_against_floor_and_daily_loss`; `test_confirmed_positive_residual_is_a_flow_and_never_raises_adjusted_h`; `test_unresolved_residual_is_never_booked`; `test_later_correction_links_to_the_observation_and_books_once`; keep `tests/accounts_baseline.py:74` for `no_external_flows`.
- **Depends on:** A1-11, A2-3. Open question N14.
- **Owner steps:** merge; the reviewed re-anchor onto the new convention after M7-T3 (spec section 8).

### A2-5: Long-interval kind in the reducer and the baseline head

- **Goal:** the reducer accepts a long-interval kind bounded by reach, exempts unjudged split pieces from the extrema and daily-loss fold through a digest-bound marker, and commits a multi-piece gap as one unit.
- **Rules:** BR-20 (owner of the table; its A1 rows were delivered by A1-6 and A1-13).
- **Files:** `execution_accounts/baseline.py:80-124` (interval kind, `judged_minimum_equity_krw`, state `unjudged_split`, all omitted at default), `:153-177`, `:208-211`, `:291-311`; `execution_launch/baseline_head.py:14-19`, `:61-65` (head schema 2 multi-step successor), `:111-114`, `:233-248`; `execution_accounts/baseline_store.py:169-178`; `execution_accounts/continuous.py:184-187`; `execution_launch/account_interval.py:169-170`, `:303`, `:377-378`; `execution_accounts/provider.py:357-359`; `execution_launch/continuous_guard.py:373-375`, `:387-390`; `execution_launch/guard_capture_material.py:253-255`, `:285-287`; `execution_launch/committed_producer.py:281`, `:301-305`, `:406-411`, `:464-466` (`OWNER_INTERVAL_NOT_BRACKETED`: for a long interval the limit terms are folded from the owner log with A2-2's `limit_terms_at`, not bracketed live around S); `execution_launch/committed_startup.py:203-213`.
- **D14:** yes. **Driver identity:** listed; hash moves. **sign.py / CAPTURE_FILES:** no.
- **Tests:** rewrite `tests/launch_baseline_head.py:151` (its line 176 asserts that a 31 s interval refuses); `test_unjudged_split_piece_is_exempt_only_with_the_digest_bound_marker`; `test_required_2200_in_an_unjudged_piece_creates_no_recovery_checkpoint`; `test_all_pieces_commit_as_one_unit_or_none`; `test_ordinary_intervals_keep_every_30s_rule`; `test_freshness_applies_to_the_last_piece_only`; `test_long_interval_owner_terms_are_folded_from_the_log_not_bracketed_live` (both the producer `:464-466` and the guard `:373-375`).
- **Depends on:** A2-4 (and A2-2's `limit_terms_at`).
- **Owner steps:** merge.

### A2-6: Gap detection, forgiven-gap judging and the rollback defence

- **Goal:** detect a suspend or restart (bootstrap, or a gap unit whose timer woke more than 30 s late with no unit running), rebuild the gap in the gap unit or bootstrap (never the 15 s startup unit), judge the first 30 s after the true S point by point, raise H with the gap high, judge E after the raise, apply the BR-19 checks, stop the chain beyond reach, and show rebuild progress in status while holding the work lock.
- **Rules:** BR-16, BR-19, OQ6, OQ7 (live stop, entry block and alert beyond reach); BR-18's lock and status lines; the live half of BR-11/BR-12 (the committing producer accepts a boundary rebuilt within 30 s; one rebuilt later inside a forgiven gap is an SD 6.2 missed-boundary safety stop).
- **Files:** `execution_launch/coordinator.py:274-299` (timer lateness), `:302-337` (status fields, including the gap's true lowest point), `:1182-1191`, `:1218-1219`, `:1231`, `:1272-1282`, `:1284-1305`; `tools/owner/launch.py:227-245`, `:296-297`; `execution_launch/continuous_guard.py:479-528` (exempt unjudged points); `execution_launch/committed_startup.py:247-250` with `execution_launch/continuous_guard_commit.py:182-244` unchanged; the live boundary switch moved from A1-12: `execution_launch/account_interval.py:13-20` (docstring), `:111-117` (`upbit_interval_frame` bracket), `:154-182` (`UpbitIntervalSource.collect`), tests `tests/launch_account_interval.py:349, 372` (the bracketing tests) and `tests/launch_coordinator.py` `test_default_boundary_lead_*` (around `:1336-1409`).
- **D14:** yes. **Driver identity:** listed; hash moves. **sign.py / CAPTURE_FILES:** no.
- **Tests:** rewrite `tests/launch_coordinator.py::test_long_suspend_stops_the_account_chain_without_a_tick` as `test_long_suspend_rebuilds_the_gap_in_the_gap_unit_and_judges_the_first_record_after_it`; `test_an_overrun_without_a_suspend_is_judged_at_every_point`; `test_a_breach_in_the_first_30s_after_the_true_start_is_not_forgiven`; `test_the_gap_high_raises_h_before_e_is_judged`; `test_a_required_2200_inside_the_unjudged_portion_stays_unverified_and_latches_the_daily_stop`; `test_gap_start_equals_the_journal_baseline_time_and_server_time_follows_the_last_event`; `test_gap_rebuild_refuses_a_start_below_the_journal_fold_or_a_changed_day_opening`; `test_gap_rebuild_restores_f_and_raw_protections_from_the_same_checkpoint`; `test_cba_price_in_the_unjudged_gap_sets_the_entry_block_and_alerts_without_judging`; `test_gap_true_low_is_archived_and_shown_in_status`; `test_boundary_rebuilt_after_the_bound_in_a_forgiven_gap_is_an_sd_6_2_safety_stop`; `test_committing_producer_accepts_a_boundary_rebuilt_within_30s_and_stops_the_chain_after_it_while_running`; `test_a_gap_beyond_seven_utc_days_stops_the_chain_blocks_entries_and_alerts`; `tests/launch_owner_ops.py::test_rebuild_holds_the_work_lock_and_disarm_returns_pending_with_progress`.
- **Depends on:** A2-5, A1-12 (rebuild function). Coordinate with M7-T9 (long-gap recovery): A2-6 owns the rebuild; M7-T9 builds the lifecycle on it.
- **Owner steps:** merge.

### A2-7: App units and owner units in sizing, startup and limits

- **Goal:** every app sell is capped at app units; sizing, anchors, flat checks and universe helpers read app units and app cash net of owner reservations; startup allows reconciled personal holdings and orders and defers entries for an unresolved origin; the next-day budget uses the lower of app-only and whole-account realized results.
- **Rules:** BR-23, OQ4, OQ12; BR-25's consumer half (the study, the odds and the outcome ladder read app fills only; account P&L reads all).
- **Files:** every fill reader on the study, odds and outcome-ladder paths filters on the A1-13 `origin` tag; the detailed plan lists them from a grep of `CollectionResult`/`Fill` consumers at that HEAD (today at least `execution_control/risk.py:299-311`'s prior-day realized input and the first-trading-day counts of N11); `execution_launch/driver.py:318-347` (`:336`), `:466-489`, `:494-512`; `execution_launch/live_history.py:169-171`, `:191-197`, `:556-574`; `execution_launch/runner.py:405-413`; `execution_launch/coordinator.py:141-166`, `:584-585`, `:769-804`, `:1080-1081`; `execution_launch/committed_startup.py:80-90`, `:401-429`, `:515-582`; `execution_control/controller.py:992-1026`, `:1051-1059`; `execution_launch/continuous_guard.py:474`, `:532`.
- **D14:** yes. **Driver identity:** listed; hash moves. **sign.py / CAPTURE_FILES:** no.
- **Tests:** `test_every_app_sell_is_capped_at_app_units_and_never_sells_tracked_owner_units`; `test_owner_coin_outside_the_universe_no_longer_latches_the_extra_holding`; `test_reserved_cash_of_an_owner_order_is_excluded_once`; `test_reconciled_personal_order_allows_startup_and_an_unresolved_origin_defers_entries`; `test_prior_day_budget_uses_the_lower_of_app_only_and_whole_account_results`; `test_anchor_rows_without_the_new_fields_still_parse`; `test_an_owner_fill_never_enters_a_strategy_result_but_counts_in_account_pnl`; coded tests for `FIXED_DRIVER_RESERVED_CASH_UNSUPPORTED` and `FIXED_DRIVER_OUTSTANDING_ORDER_UNSUPPORTED` (none name them today).
- **Depends on:** A1-11, A2-4. M7-T11 edits the same driver function (`driver.py:448-450`, `:568-570`): land A2-7 first.
- **Owner steps:** merge.

### A2-8: Live trade-list source and the live working Y

- **Goal:** open the candidate source under controlled mode, move the class pins to the new source, switch the committing producer's held route to the trade-list path, persist the threshold in force per observation, and refuse adaptive working Y unconditionally: no signed adaptive-terms record exists in M7-T3 (N19), so static Y is the only live mode.
- **Rules:** BR-26 (live: threshold history, restart recovery; static mode only), BR-21's producer row (the flat-only refusal `execution_launch/account_interval.py:118-126`).
- **Files:** `execution_launch/account_interval.py:481-482`, `:118-126` (held intervals take the trade-list path; the BR-21 producer refusal goes, together with the live source switch); `execution_launch/committed_producer.py:165`, `:188-189`, `:212-214`; `execution_launch/guard_capture_archive.py:254`; a persisted threshold record (journal kind or store; N15); test `tests/launch_account_interval.py:265` (`test_held_inventory_interval_refuses_without_price_path` becomes `test_held_inventory_interval_commits_true_extrema_from_the_trade_list_path`).
- **Interfaces:** `@dataclass(frozen=True, kw_only=True) class BidGapThreshold: observation_seq: int; market: str; input_cutoff: datetime; prior: Decimal | None; applied: Decimal; proposed: Decimal | None; probabilities: tuple[tuple[str, Decimal], ...]; uncertainty: Decimal | None; effective_seq: int | None; policy_sha256: str; model_sha256: str | None; reason: str` (static mode: `proposed`, `probabilities`, `uncertainty` and `model_sha256` empty).
- **D14:** yes. **Driver identity:** listed; hash moves. **sign.py / CAPTURE_FILES:** no.
- **Tests:** `test_live_source_uses_the_static_signed_y_and_y_zero_when_unset`; `test_the_applied_threshold_is_the_one_in_force_before_the_observation`; `test_restart_cannot_restore_a_looser_working_y`; `test_an_unknown_applied_threshold_after_restart_sets_the_entry_block_with_y_zero`; `test_a_repeated_observation_keeps_its_first_threshold_record_and_never_revises_a_past_quote`; `test_adaptive_working_y_is_refused_unconditionally` (the adaptive cases, stale proposals, increases under an outstanding block, stop or halt, and a raised ceiling over a tighter working Y, are tested offline in A1-14 and live in the N19 task); `test_held_inventory_interval_commits_true_extrema_from_the_trade_list_path`; `tests/launch_committed_account.py::test_existing_live_candidate_source_gate_remains_closed` changes to "opens only under controlled mode".
- **Depends on:** A2-1 through A2-7; M7-T8 (valid deployment), M7-T6 (controlled mode). Adaptive use waits for model qualification, M11-T5 and the adaptive-terms code task of N19.
- **Owner steps:** merge; one `code_approved` after A1 and A2 merge, then the study freeze, then signing Y (spec 7.4).

### Rule and decision coverage

| Item | PR | Item | PR |
|---|---|---|---|
| BR-1 | A1-4 | BR-14 | A2-3 |
| BR-2 | A1-4 | BR-15 | A2-2 |
| BR-3 | A1-6 | BR-16 | A2-6 |
| BR-4 | A1-5 | BR-17 | A1-4 |
| BR-5 | A1-9 | BR-18 | A1-3 |
| BR-6 | A1-7 | BR-19 | A2-6 |
| BR-7 | A1-7 | BR-20 | A2-5 |
| BR-8 | A1-8 (pure audit), A2-3 (live lagging step) | BR-21 | A1-10; producer refusal `account_interval.py:118-126` in A2-8 |
| BR-9(a) | A2-3 | BR-22 | A2-4 |
| BR-9(b) | A2-1 | BR-23 | A2-7 |
| BR-9(c) | A2-1 | BR-24 | A1-5 |
| BR-10 | A1-1 | BR-25 | A1-11 (classification), A1-13 (archive tags), A2-7 (app-only consumers) |
| BR-11 | A1-12 (preview), A2-6 (committing producer) | BR-26 static signed limit | A1-1 |
| BR-12 | A1-12 (preview), A2-6 (live) | BR-26 offline adaptive replay | A1-14 |
| BR-13 | A2-3 (adjusted floor), A2-4 (raw floor) | BR-26 live threshold history, static mode | A2-8 |
| | | BR-26 signed adaptive terms (owner-log record, D12 fold, signer mirror, live validation) | outside M7-T3: the N19 code task after M11-T5; A2-8 refuses adaptive Y until then |

| Decision | PR or owner outside M7-T3 |
|---|---|
| OQ1 | A1-10 |
| OQ2 | A2-4 |
| OQ3 | A2-4 |
| OQ4 | A2-7 |
| OQ5 | outside: M7-T11 (expiry-only end-slot sale, `driver.py:448-450, 568-570`) and M7-T5 (PH/SD/CL texts); A2-7 only caps sells at app units |
| OQ6 | A2-6 |
| OQ7 | A2-6 |
| OQ8 | A1-11 (records, unresolved status), A2-4 (booking) |
| OQ9 | outside: M7-T10 (manual Telegram/WebAuthn release, and the only `entry_unblock` writer, taking a verified approval object); automatic release waits for the open question below and M11-T5. A2-1 provides the latch and the `entry_unblock` record fold both routes must satisfy |
| OQ10 | A1-1 (judgment), A2-1 (live buy and preparation gate) |
| OQ11 | A1-10 (records); the pocket transfer read is N17 (A1-2); provisioning the permission is an owner step |
| OQ12 | A2-7 |
| OQ13 | A1-5 (coverage); the risk sale is outside: M7-T11, and the personal-unit sale authority is an open question below |
| OQ14 | A2-1 (durable record); delivery outside: M7-T10 and PR #69 |
| OQ15 | A1-9 |
| OQ16 | outside: M7-T8 (standing deployment ends on restart or a handoff over 30 s) |
| OQ17 | A1-3 (shared hold in the probe's format, always-shared pacing); egress and route-change tracking is N18 |
| OQ18 | outside: A0 (M7-T3a done, observation O28); no code |

---

## A1-1 detailed tasks

All commands run from the clone root in Git Bash. Set once per shell:

```bash
cd <the clone root>
PY=".venv/Scripts/python.exe"   # the checkout's own venv, or any Python with the pinned requirements
```

`-I` drops the current directory from `sys.path`, so every command inserts it. The suite runners wrap each test in `hermetic()` and a temporary `TRADEGEN_HOME`; never call `tests/run_all.py`'s `main` for a check, because it rewrites the tracked `qa/acceptance_results.json`.

All four edited source files and the three test files are LF (`git ls-files --eol`); the Edit tool keeps them LF.

### Task 1: Owner-log schema accepts the optional `bid_gap_fraction`

**Files:**
- Modify: `core/compliance/owner.py:158-159` (`_DATA["limit_set"]`), `:172-173` (end of `_DATA`), `:176-191` (`_data_problem`)
- Test: `tests/compliance_owner.py` (append after the last line, `:1019`)

**Interfaces:**
- Consumes: `owner._data_problem(kind: str, data) -> str`, `owner.verify_log(lines: list[bytes], pubkey_raw: bytes, anchors) -> LogCheck`, test helpers `_fake_signed`, `_broken`, `_home`, `_raw` (`tests/compliance_owner.py:90-99, 37, 54`), `F.write_log`, `F.test_key` (`tests/compliance_fixtures.py:135-147, 111-120`).
- Produces: `owner._OPTIONAL: dict[str, frozenset[str]]` (`{"limit_set": frozenset({"bid_gap_fraction"})}`); `_data_problem` accepts `limit_set` with or without `bid_gap_fraction`, validated as `_number(v) and 0 < v <= 0.05`. Tests in Tasks 3 use `_TWO` and the `Decimal` import from this block.

- [ ] **Step 1: Write the failing tests**

Append to `tests/compliance_owner.py`:

```python


# --------------------------------------------------------------------------- #
# BR-26: the optional signed bid-gap limit `bid_gap_fraction` in limit_set (5% inclusive ceiling)
# --------------------------------------------------------------------------- #
from decimal import Decimal  # noqa: E402

_TWO = {"total_loss_floor_krw": 21000.0, "daily_loss_krw": 5000.0}


def test_bid_gap_fraction_is_an_optional_bounded_limit_set_field():
    assert owner._data_problem("limit_set", _TWO) == "", "two-field records stay valid"
    for good in (0.05, 0.02, 0.0001, 1e-06):
        assert owner._data_problem("limit_set", {**_TWO, "bid_gap_fraction": good}) == "", good
    for bad in (0, 0.0, -0.0, -0.01, 0.05000000000000001, 0.050001, 0.06, 1, 1.0, True, False, "0.02", None,
                float("nan"), float("inf"), 10 ** 400, [0.02]):
        assert owner._data_problem("limit_set", {**_TWO, "bid_gap_fraction": bad}) == \
            "has invalid bid_gap_fraction", bad
    assert owner._data_problem("limit_set", {"total_loss_floor_krw": 21000.0, "bid_gap_fraction": 0.02}) \
        .startswith("keys "), "the optional field never replaces a required one"
    assert owner._data_problem("limit_set", {**_TWO, "bid_gap_fraction": 0.02, "note": "x"}).startswith("keys ")
    assert owner._data_problem("cap_set", {"key": "okx_equity_share", "value": 0.1, "bid_gap_fraction": 0.02}) \
        .startswith("keys "), "only limit_set has the optional field"
    assert _broken([_fake_signed("limit_set", {**_TWO, "bid_gap_fraction": 0.06})]) == \
        "line 1: limit_set data has invalid bid_gap_fraction"


def test_bid_gap_two_and_three_field_limit_sets_verify_in_one_signed_log():
    key = F.test_key()
    entries = [("limit_set", _TWO), ("limit_set", {**_TWO, "bid_gap_fraction": 0.035})]
    lines = F.write_log(_home(), entries)
    check = owner.verify_log(lines, _raw(key), [])
    assert check.ok, check.reason
    assert [e.data for e in check.entries] == [_TWO, {**_TWO, "bid_gap_fraction": 0.035}]
    assert b'"bid_gap_fraction":0.035,' in lines[1], "the signed line holds the exact decimal text"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:
```bash
"$PY" -X utf8 -I -B -c "import sys; sys.path.insert(0, '.'); from tests.compliance_acceptance import _main; raise SystemExit(_main(['compliance_owner/test_bid_gap']))"
```
Expected: `0/2 passed, 2 failed`, with `FAIL compliance_owner/test_bid_gap_fraction_is_an_optional_bounded_limit_set_field AssertionError: 0.05` and `FAIL compliance_owner/test_bid_gap_two_and_three_field_limit_sets_verify_in_one_signed_log AssertionError: line 2: limit_set data keys [...] are not [...]`. If cryptography is missing the second reports `NOT_RUN PENDING`.

- [ ] **Step 3: Write the minimal implementation**

In `core/compliance/owner.py`, replace lines 158-159:

```python
    "limit_set": {"total_loss_floor_krw": lambda v: _number(v) and v >= 0,
                  "daily_loss_krw": lambda v: _number(v) and v > 0},
```

with:

```python
    "limit_set": {"total_loss_floor_krw": lambda v: _number(v) and v >= 0,
                  "daily_loss_krw": lambda v: _number(v) and v > 0,
                  "bid_gap_fraction": lambda v: _number(v) and 0 < v <= 0.05},     # BR-26: optional, 5% inclusive
```

Replace the end of `_DATA` (lines 172-173):

```python
    "system_disarm": {"session_id": _text, "reason": _text},
}
```

with:

```python
    "system_disarm": {"session_id": _text, "reason": _text},
}

# BR-26: a limit_set may omit bid_gap_fraction, so every two-field record and its signature stays valid.
_OPTIONAL = {"limit_set": frozenset({"bid_gap_fraction"})}
```

In `_data_problem`, replace lines 183-185:

```python
    if set(data) != set(schema):
        return f"keys {sorted(map(str, data))} are not {sorted(schema)}"
    bad = sorted(k for k, ok in schema.items() if not ok(data[k]))
```

with:

```python
    if not set(schema) - _OPTIONAL.get(kind, frozenset()) <= set(data) <= set(schema):
        return f"keys {sorted(map(str, data))} are not {sorted(schema)}"
    bad = sorted(k for k, ok in schema.items() if k in data and not ok(data[k]))
```

Why a float: `canonical_json` (`core/compliance/model.py:59-61`) writes a float with `repr`, so the signed line holds the shortest decimal that round-trips, which is exactly what the owner typed (`0.035`); `_number` already refuses bool, NaN, infinity and ints too large for a float, and no int lies in `(0, 0.05]`.

- [ ] **Step 4: Run the tests to verify they pass**

Run the Step 2 command, then the schema tests that must stay green:
```bash
"$PY" -X utf8 -I -B -c "import sys; sys.path.insert(0, '.'); from tests.compliance_acceptance import _main; raise SystemExit(_main(['compliance_owner/']))"
```
Expected: `2/2 passed`, then every `compliance_owner/` test passes (including `test_event_data_schemas_are_exact`).

- [ ] **Step 5: Commit**

```bash
git add core/compliance/owner.py tests/compliance_owner.py
git commit -F - <<'EOF'
Accept optional bid_gap_fraction in owner limit_set (BR-26)

Two-field limit_set records and their signatures stay valid; a third field
bid_gap_fraction is accepted only as a finite JSON number in (0, 0.05].

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

### Task 2: The independent signer's schema copy matches

**Files:**
- Modify: `tools/signer/sign.py:38-42` (help text), `:217-218` (`SCHEMAS["limit_set"]`), `:233` (after `_DATA`), `:236-250` (`_data_problem`)
- Test: `tests/compliance_signer.py` (append after the last line, `:2013`)

**Interfaces:**
- Consumes: Task 1's owner schema; `signer._data_problem`, `signer.check_data(kind, data) -> None`, `signer.entry_line(signing_key, seq, prev_sha256, kind, data, utc) -> tuple[bytes, str]` (`tools/signer/sign.py:138-143`); test helpers `_VALID`, `_EDGES`, `UTC`, `_need_crypto`, `_raw` (`tests/compliance_signer.py:33-58, 27, 76-78, 150-151`), `fx.test_key`.
- Produces: `signer._OPTIONAL` equal to `owner._OPTIONAL`; `check_data("limit_set", {..., "bid_gap_fraction": y})` accepts exactly what owner.py accepts.

- [ ] **Step 1: Write the failing tests**

Append to `tests/compliance_signer.py`:

```python


# -- BR-26: the optional bid_gap_fraction field of limit_set ---------------------------------------------------------
_Y_EDGES = (0.05, 0.02, 1e-06, 0.05000000000000001, 0.050001, 0.06, -0.01, "0.02")


def test_signer_bid_gap_fraction_schema_matches_owner_both_ways():
    """With and without the optional field, the signer's copy agrees with owner._data_problem on every edge value,
    and check_data never accepts a limit_set owner.py rejects."""
    three = {**_VALID["limit_set"], "bid_gap_fraction": 0.02}
    cases = [three, _VALID["limit_set"], {**three, "extra": 1}]
    cases += [{**three, field: edge} for field in three for edge in _EDGES + _Y_EDGES]
    cases += [{k: v for k, v in three.items() if k != field} for field in three]
    for data in cases:
        mine, theirs = signer._data_problem("limit_set", data), owner._data_problem("limit_set", data)
        assert (mine == "") == (theirs == ""), (data, mine, theirs)
        try:
            signer.check_data("limit_set", data)
        except ValueError:
            continue
        assert theirs == "", (data, theirs)
    signer.check_data("limit_set", three)
    for bad in (0.06, 0, "0.02", True):
        try:
            signer.check_data("limit_set", {**three, "bid_gap_fraction": bad})
        except ValueError as exc:
            assert "bid_gap_fraction" in str(exc), exc
        else:
            raise AssertionError(f"signed a bid_gap_fraction of {bad!r}")


def test_signer_signs_bid_gap_and_legacy_limit_sets_that_owner_verifies():
    _need_crypto()
    key = fx.test_key()
    lines, prev = [], owner.GENESIS_PREV
    for seq, data in enumerate((_VALID["limit_set"], {**_VALID["limit_set"], "bid_gap_fraction": 0.05}), start=1):
        signer.check_data("limit_set", data)
        line, prev = signer.entry_line(key, seq, prev, "limit_set", data, UTC)
        lines.append(line)
    check = owner.verify_log(lines, _raw(key), [])
    assert check.ok, check.reason
    assert check.entries[1].data["bid_gap_fraction"] == 0.05 and "bid_gap_fraction" not in check.entries[0].data
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:
```bash
"$PY" -X utf8 -I -B -c "import sys; sys.path.insert(0, '.'); from tests.compliance_acceptance import _main; raise SystemExit(_main(['compliance_signer/test_signer_']))"
```
Expected, per test (other `test_signer_*` tests in that module may also be selected by the substring and must pass):
- `test_signer_bid_gap_fraction_schema_matches_owner_both_ways` fails on its agreement assert, because Task 1 already makes owner.py accept the field: `AssertionError: ({'total_loss_floor_krw': 21000.0, 'daily_loss_krw': 5000.0, 'bid_gap_fraction': 0.02}, "keys ['bid_gap_fraction', 'daily_loss_krw', 'total_loss_floor_krw'] are not ['daily_loss_krw', 'total_loss_floor_krw']", '')` (signer "keys ...", owner "").
- `test_signer_signs_bid_gap_and_legacy_limit_sets_that_owner_verifies` fails with `ValueError: limit_set: data keys ['bid_gap_fraction', 'daily_loss_krw', 'total_loss_floor_krw'] are not ['daily_loss_krw', 'total_loss_floor_krw']`.

- [ ] **Step 3: Write the minimal implementation**

In `tools/signer/sign.py`, replace lines 217-218:

```python
    "limit_set": {"total_loss_floor_krw": lambda v: _number(v) and v >= 0,
                  "daily_loss_krw": lambda v: _number(v) and v > 0},
```

with:

```python
    "limit_set": {"total_loss_floor_krw": lambda v: _number(v) and v >= 0,
                  "daily_loss_krw": lambda v: _number(v) and v > 0,
                  "bid_gap_fraction": lambda v: _number(v) and 0 < v <= 0.05},     # BR-26: optional, 5% inclusive
```

Replace line 233:

```python
_DATA = {**SCHEMAS, **SYSTEM_SCHEMAS}
```

with:

```python
_DATA = {**SCHEMAS, **SYSTEM_SCHEMAS}

# BR-26: a limit_set may omit bid_gap_fraction, so every two-field record and its signature stays valid.
_OPTIONAL = {"limit_set": frozenset({"bid_gap_fraction"})}
```

In `_data_problem`, replace lines 243-245:

```python
    if set(data) != set(schema):
        return f"keys {sorted(map(str, data))} are not {sorted(schema)}"
    bad = sorted(k for k, ok in schema.items() if not ok(data[k]))
```

with:

```python
    if not set(schema) - _OPTIONAL.get(kind, frozenset()) <= set(data) <= set(schema):
        return f"keys {sorted(map(str, data))} are not {sorted(schema)}"
    bad = sorted(k for k, ok in schema.items() if k in data and not ok(data[k]))
```

In the help text, replace line 42:

```
                            armed on or before the day you set it, and never after a system_halt
```

with:

```
                            armed on or before the day you set it, and never after a system_halt.
                            limit_set may add bid_gap_fraction, the bid-gap limit Y with 0 < Y <= 0.05
                            (a smaller Y is tighter; leaving it out keeps the Y in force)
```

`_cmd_event` (`:3176-3182`) already turns every numeric `limit_set` value into a float (`:3180-3181`), so `--data '{"total_loss_floor_krw": ..., "daily_loss_krw": ..., "bid_gap_fraction": 0.02}'` needs no other change; a string such as `"0.02"` is refused by `check_data`.

- [ ] **Step 4: Run the tests to verify they pass**

Run the Step 2 command, then the whole signer module (it holds the copies against owner.py both ways):
```bash
"$PY" -X utf8 -I -B -c "import sys; sys.path.insert(0, '.'); from tests.compliance_acceptance import _main; raise SystemExit(_main(['compliance_signer/']))"
```
Expected: all pass, including `test_check_data_is_never_looser_than_owner` and `test_every_event_the_signer_accepts_verifies`. This module is slow (several minutes).

- [ ] **Step 5: Commit**

```bash
git add tools/signer/sign.py tests/compliance_signer.py
git commit -F - <<'EOF'
Mirror the optional bid_gap_fraction in the independent signer (BR-26)

The signer's schema copy accepts exactly what owner.py accepts; the event
help text names the field. This changes tools/signer/sign.py and needs the
owner's code approval.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

### Task 3: D12 folds `bid_gap_fraction`; effective static Y lookup

**Files:**
- Modify: `core/compliance/owner.py:628-637` (imports, new `_FOLD_KEYS`, `_TIGHTER`), `:745` (fold pairs), `:768` (`limits=` filter), insert before `:775` (`def in_force`). Line numbers are before Task 1's edit; after it they shift by +4 (`:632-641`, `:749`, `:772`, `:779`). `_LIMIT_KEYS` stays the two-key tuple: `tests/odds_plan.py:142` asserts `P.LIMIT_KEYS == owner._LIMIT_KEYS == ("total_loss_floor_krw", "daily_loss_krw")` (`core/odds/plan.py:41`), and the odds plan requires exactly those two (`core/odds/plan.py:354`).
- Test: `tests/compliance_owner.py` (append after Task 1's block)

**Interfaces:**
- Consumes: `owner.owner_state(check, *, date, now_utc, session_id, fingerprint_now, first_recorded) -> model.OwnerState`; helpers `_state_log`, `_state_at`, `_state_kst`, `_state_limits` (`tests/compliance_owner.py:610-641`); `_TWO` and `Decimal` from Task 1's block; `model.OwnerState.broken` (`core/compliance/model.py:152-154`).
- Produces: `OwnerState.limits` holds `"bid_gap_fraction": float` once in force (absent while unset); `owner.bid_gap_fraction(state: model.OwnerState) -> Decimal | None`. A1-13 and A2-2 call it.

- [ ] **Step 1: Write the failing tests**

Append to `tests/compliance_owner.py`:

```python


def _state_y(y: float, at: _dt.datetime, floor: float = 21_000.0, daily: float = 5_000.0):
    return ("limit_set", {"total_loss_floor_krw": floor, "daily_loss_krw": daily, "bid_gap_fraction": y}, at)


def test_state_bid_gap_unset_is_tightest_and_the_first_value_loosens_from_the_next_seoul_date():
    check = _state_log(_state_limits(21_000.0, 5_000.0, _state_kst(2026, 10, 10)),
                       _state_y(0.02, _state_kst(2026, 10, 24, 10)))
    today = _state_at(check, _state_kst(2026, 10, 24, 11))
    assert today.limits == {"total_loss_floor_krw": 21_000.0, "daily_loss_krw": 5_000.0}, "unset is the tightest"
    assert owner.bid_gap_fraction(today) is None
    assert _state_at(check, _state_kst(2026, 10, 24, 23, 59, 59)).limits.get("bid_gap_fraction") is None
    tomorrow = _state_at(check, _state_kst(2026, 10, 25, 0, 0, 0))
    assert tomorrow.limits["bid_gap_fraction"] == 0.02 and owner.bid_gap_fraction(tomorrow) == Decimal("0.02")


def test_state_bid_gap_decrease_applies_at_its_entry_and_an_increase_waits():
    check = _state_log(_state_y(0.03, _state_kst(2026, 10, 10)),
                       _state_y(0.01, _state_kst(2026, 10, 24, 10)),
                       _state_y(0.04, _state_kst(2026, 10, 24, 12)))
    assert _state_at(check, _state_kst(2026, 10, 24, 9)).limits["bid_gap_fraction"] == 0.01, "stamped ahead, applies"
    assert _state_at(check, _state_kst(2026, 10, 24, 13)).limits["bid_gap_fraction"] == 0.01
    assert _state_at(check, _state_kst(2026, 10, 25)).limits["bid_gap_fraction"] == 0.04, "the increase, next day"
    same = _state_log(_state_y(0.03, _state_kst(2026, 10, 10)), _state_y(0.03, _state_kst(2026, 10, 24, 10)))
    assert _state_at(same, _state_kst(2026, 10, 24, 11)).limits["bid_gap_fraction"] == 0.03


def test_state_bid_gap_loosening_waits_for_an_armed_session_and_never_follows_a_halt():
    rows = [_state_y(0.01, _state_kst(2026, 10, 20)),
            ("session_armed", {"session_id": "S1"}, _state_kst(2026, 10, 22, 10)),
            _state_y(0.03, _state_kst(2026, 10, 22, 12))]
    check, at = _state_log(*rows), _state_kst(2026, 10, 24)
    assert _state_at(check, at, session_id="S1").limits["bid_gap_fraction"] == 0.01, "armed before it"
    assert _state_at(check, at).limits["bid_gap_fraction"] == 0.03, "no session: the loosening counts"
    halted = _state_log(_state_limits(21_000.0, 5_000.0, _state_kst(2026, 10, 10)),
                        ("system_halt", {"floor_krw": 21_000.0}, _state_kst(2026, 10, 12)),
                        _state_y(0.02, _state_kst(2026, 10, 14)))
    state = _state_at(halted, _state_kst(2026, 10, 24))
    assert "bid_gap_fraction" not in state.limits and owner.bid_gap_fraction(state) is None, \
        "a first Y signed after a halt is a loosening and never counts"
    tighter = _state_log(_state_y(0.03, _state_kst(2026, 10, 10)),
                         ("system_halt", {"floor_krw": 21_000.0}, _state_kst(2026, 10, 12)),
                         _state_y(0.01, _state_kst(2026, 10, 14)))
    assert _state_at(tighter, _state_kst(2026, 10, 24)).limits["bid_gap_fraction"] == 0.01, "a decrease still applies"


def test_state_two_field_limit_set_leaves_a_signed_bid_gap_unchanged():
    check = _state_log(_state_y(0.02, _state_kst(2026, 10, 10)),
                       _state_limits(30_000.0, 4_000.0, _state_kst(2026, 10, 24, 10)))
    assert _state_at(check, _state_kst(2026, 10, 24, 11)).limits == {
        "total_loss_floor_krw": 30_000.0, "daily_loss_krw": 4_000.0, "bid_gap_fraction": 0.02}


def test_bid_gap_fraction_lookup_is_the_exact_signed_decimal_or_none():
    check = _state_log(_state_y(json.loads('{"y": 0.035}')["y"], _state_kst(2026, 10, 10)))
    state = _state_at(check, _state_kst(2026, 10, 24))
    assert owner.bid_gap_fraction(state) == Decimal("0.035") != Decimal(0.035), "the signed text, not binary noise"
    assert str(owner.bid_gap_fraction(state)) == "0.035"
    assert owner.bid_gap_fraction(model.OwnerState.broken("x")) is None, "a broken log has no Y"
    assert owner.bid_gap_fraction(_state_at(_state_log(), _state_kst(2026, 10, 24))) is None
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:
```bash
"$PY" -X utf8 -I -B -c "import sys; sys.path.insert(0, '.'); from tests.compliance_acceptance import _main; raise SystemExit(_main(['bid_gap']))"
```
Expected: Task 1's two tests pass; the five new ones fail: `AttributeError: module 'core.compliance.owner' has no attribute 'bid_gap_fraction'` (two tests), `KeyError: 'bid_gap_fraction'` (two tests) and `AssertionError` (`test_state_two_field_limit_set_leaves_a_signed_bid_gap_unchanged`). Task 2's signer tests also match `bid_gap` and pass.

- [ ] **Step 3: Write the minimal implementation**

In `core/compliance/owner.py`, replace (Task 1 shifted these by +4 lines):

```python
from core.compliance import model, rules  # noqa: E402

_LOG_STAMP = "%Y-%m-%dT%H:%M:%SZ"
_LIMIT_KEYS = ("total_loss_floor_krw", "daily_loss_krw")
_TIGHTER = {"okx_equity_share": lambda new, old: new <= old,           # a smaller cap
            "total_loss_floor_krw": lambda new, old: new >= old,       # a larger floor
            "daily_loss_krw": lambda new, old: new <= old}             # a smaller daily loss
```

with:

```python
from decimal import Decimal  # noqa: E402

from core.compliance import model, rules  # noqa: E402

_LOG_STAMP = "%Y-%m-%dT%H:%M:%SZ"
_LIMIT_KEYS = ("total_loss_floor_krw", "daily_loss_krw")
_FOLD_KEYS = _LIMIT_KEYS + ("bid_gap_fraction",)                      # BR-26: folded and kept, never required
_TIGHTER = {"okx_equity_share": lambda new, old: new <= old,           # a smaller cap
            "total_loss_floor_krw": lambda new, old: new >= old,       # a larger floor
            "daily_loss_krw": lambda new, old: new <= old,             # a smaller daily loss
            "bid_gap_fraction": lambda new, old: new <= old}           # a smaller bid gap Y (BR-26)
```

In `_owner_fold`, replace:

```python
            pairs = [(d["key"], d["value"])] if e.kind == "cap_set" else [(k, d[k]) for k in _LIMIT_KEYS]
```

with:

```python
            pairs = [(d["key"], d["value"])] if e.kind == "cap_set" else [(k, d[k]) for k in _FOLD_KEYS if k in d]
```

(Without `if k in d` every two-field record raises `KeyError`, which `owner_state` turns into a BROKEN owner state everywhere.)

In `owner_state`'s return, replace:

```python
        limits={k: v for k, v in values.items() if k in _LIMIT_KEYS}, addresses=frozenset(addresses),
```

with:

```python
        limits={k: v for k, v in values.items() if k in _FOLD_KEYS}, addresses=frozenset(addresses),
```

Insert immediately before `def in_force(check: LogCheck) -> dict[str, tuple[str, int]]:`:

```python
def bid_gap_fraction(state: model.OwnerState) -> Decimal | None:
    """BR-26: the effective static signed bid-gap limit Y as the exact decimal the owner signed (the shortest
    round-trip text of the logged JSON number, which is the text in the canonical line), or None when no Y is in
    force or the state is not OK. None means BR-10 checks held coins at Y = 0 and no buy is prepared (OQ10)."""
    value = state.limits.get("bid_gap_fraction") if state.ok else None
    return None if value is None else Decimal(repr(value))


```

The existing fold already gives the D12 behaviour: unset counts as the tightest (`old is None`), so the first value and any increase go through `loosening_counts` (next Seoul date, before the first halt, outside a session armed on or before it), and a decrease or an equal value applies at its entry even when stamped ahead. The `limits=` filter now keeps the key. Every reader of `OwnerState.limits` reads named keys, with `.get` (`execution_control/controller.py:775, 803, 823, 907, 1063`, `execution_launch/committed_producer.py:289`, `execution/checks.py:135-138`) or by direct index of the two required keys (`core/odds/costs.py:357`, `core/odds/simulate.py:506-510`), or checks the two-key `LIMIT_KEYS` (`core/odds/plan.py:354`), so a third key changes none of them. `tests/odds_plan.py:142` pins `owner._LIMIT_KEYS`, which this task leaves at two keys.

- [ ] **Step 4: Run the tests to verify they pass**

Run the Step 2 command, then all owner-state tests and the odds plan pin:
```bash
"$PY" -X utf8 -I -B -c "import sys; sys.path.insert(0, '.'); from tests.compliance_acceptance import _main; raise SystemExit(_main(['compliance_owner/']))"
"$PY" -X utf8 -I -B -c "import sys; sys.path.insert(0, '.'); from tests.odds_acceptance import _main; raise SystemExit(_main(['odds_plan/']))"
```
Expected: `9/9 passed` for `bid_gap`, every `compliance_owner/` test passes (`test_state_no_loosening_after_a_halt` and `test_state_daily_loss_tightens_and_loosens` still see exactly two keys), and every `odds_plan/` test passes (`test_constants_are_the_contracts` still sees the two-key `_LIMIT_KEYS`).

- [ ] **Step 5: Commit**

```bash
git add core/compliance/owner.py tests/compliance_owner.py
git commit -F - <<'EOF'
Fold bid_gap_fraction under D12 and expose the static signed Y (BR-26)

Unset counts as the tightest; the first value and any increase loosen from
the next Asia/Seoul date under the armed-session and halt rules; a decrease
applies at its entry; a two-field record leaves Y unchanged.
owner.bid_gap_fraction returns the exact signed decimal or None.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

### Task 4: Pure BR-10 bid-gap judgment

**Files:**
- Modify: `execution_control/risk.py` (append after the last line, `:511`; uses `_ZERO` `:21`, `_decimal` `:144-145`, `_stamp` `:148-154`, `_context` `:161-164` and the existing `DecimalException`, `localcontext`, `timedelta` imports at `:12-13`)
- Test: `tests/control_risk.py` (append after the last line, `:400`; uses `D`, `NOW` `:8-9`)
- Modify: `tests/renewal_boundaries.py:32` (the reviewed `INITIALIZERS` pin for `execution_control/risk.py`; the new constants and class change its module-level surface)

**Interfaces:**
- Consumes: the Y in force before the observation, as `owner.bid_gap_fraction(state)` (Task 3) returns it.
- Produces: `BID_GAP_MAXIMUM = Decimal("0.05")`; `@dataclass(frozen=True, kw_only=True) class BidGapJudgment: outcome: str; threshold: Decimal; recheck_price: Decimal | None; entry_block: bool; buy_preparation_allowed: bool` with outcomes `MARK_FRESH`, `CLEAR`, `BID_GAP`, `QUOTE_UNAVAILABLE`; `judge_bid_gap(*, mark: Decimal, mark_at: datetime, server_at: datetime, bid: Decimal | None, threshold: Decimal | None) -> BidGapJudgment`, `ValueError("BID_GAP_INPUT_INVALID")` otherwise. A1-13 calls it per held coin; A2-3 turns `BID_GAP`/`QUOTE_UNAVAILABLE` into CBA.

- [ ] **Step 1: Write the failing tests**

Append to `tests/control_risk.py`:

```python


# -- BR-10 / BR-26 bid-gap judgment (pure; the caller supplies the Y in force before this observation) ------------
from dataclasses import fields  # noqa: E402

from execution_control.risk import BID_GAP_MAXIMUM, BidGapJudgment, judge_bid_gap  # noqa: E402

_MARK_AT = NOW - timedelta(minutes=5)


def _gap(**changes):
    return judge_bid_gap(**({"mark": D("100"), "mark_at": _MARK_AT, "server_at": NOW, "bid": D("99"),
                             "threshold": D("0.02")} | changes))


def test_bid_gap_compares_the_bid_with_the_mark_at_the_threshold_in_force():
    assert BID_GAP_MAXIMUM == D("0.05")
    clear = _gap(bid=D("98.01"))
    assert (clear.outcome, clear.entry_block, clear.recheck_price) == ("CLEAR", False, None)
    assert clear.threshold == D("0.02") and clear.buy_preparation_allowed
    at_limit = _gap(bid=D("98"))
    assert (at_limit.outcome, at_limit.entry_block, at_limit.recheck_price) == ("BID_GAP", True, D("98")), \
        "bid <= mark x (1 - Y) includes equality"
    below = _gap(bid=D("90"))
    assert below.outcome == "BID_GAP" and below.recheck_price == D("90"), "CBA re-checks at the bid, not the mark"
    assert _gap(bid=D("101")).outcome == "CLEAR", "a bid above the last trade is no gap"
    assert _gap(threshold=D("0.05"), bid=D("95.01")).outcome == "CLEAR"
    assert _gap(threshold=D("0.05"), bid=D("95")).outcome == "BID_GAP"


def test_bid_gap_without_a_signed_y_checks_at_zero_and_prepares_no_buy():
    same = _gap(threshold=None, bid=D("100"))
    assert same.outcome == "BID_GAP" and same.threshold == D("0") and not same.buy_preparation_allowed
    above = _gap(threshold=None, bid=D("100.01"))
    assert above.outcome == "CLEAR" and not above.buy_preparation_allowed and not above.entry_block


def test_bid_gap_reads_only_marks_older_than_thirty_seconds_by_server_time():
    fresh = _gap(mark_at=NOW - timedelta(seconds=30), bid=D("1"))
    assert (fresh.outcome, fresh.entry_block, fresh.recheck_price) == ("MARK_FRESH", False, None)
    assert _gap(mark_at=NOW - timedelta(seconds=30), bid=None).outcome == "MARK_FRESH", "no bid read is needed"
    assert _gap(mark_at=NOW - timedelta(seconds=30, milliseconds=1), bid=D("1")).outcome == "BID_GAP"


def test_a_quote_failure_is_its_own_outcome_and_never_widens_y():
    failed = _gap(bid=None)
    assert (failed.outcome, failed.entry_block, failed.recheck_price) == ("QUOTE_UNAVAILABLE", True, None), \
        "an unreadable bid or empty book blocks entries without a price re-check (OQ10)"
    assert failed.threshold == D("0.02"), "the Y in force is reported unchanged"
    unset = _gap(bid=None, threshold=None)
    assert unset.threshold == D("0") and not unset.buy_preparation_allowed
    assert {f.name for f in fields(BidGapJudgment)} == {
        "outcome", "threshold", "recheck_price", "entry_block", "buy_preparation_allowed"}, \
        "the judgment proposes no new Y and carries no sell"


def test_bid_gap_inputs_are_exact_bounded_and_independent_of_ambient_rounding():
    for bad in ({"mark": 100.0}, {"mark": D("0")}, {"mark": D("NaN")}, {"bid": D("0")}, {"bid": D("-1")},
                {"bid": 99.0}, {"threshold": D("0")}, {"threshold": D("-0.01")}, {"threshold": D("0.0500001")},
                {"threshold": 0.02}, {"mark_at": NOW + timedelta(seconds=1)},
                {"server_at": datetime(2026, 10, 20, 14, 0)}, {"mark": D("1." + "1" * 90)}):
        try:
            _gap(**bad)
        except ValueError as exc:
            assert str(exc) == "BID_GAP_INPUT_INVALID", (bad, exc)
        else:
            raise AssertionError(bad)
    with localcontext() as ctx:
        ctx.prec = 3
        assert _gap(mark=D("123.456"), bid=D("120.98688"), threshold=D("0.02")).outcome == "BID_GAP"
        assert _gap(mark=D("123.456"), bid=D("120.98689"), threshold=D("0.02")).outcome == "CLEAR"
    tiny = _gap(mark=D("12345.678"), bid=D("12000"), threshold=D(repr(5e-324)))
    assert tiny.outcome == "BID_GAP" and tiny.threshold == D("5E-324"), "every Y the schema accepts is judged"
    assert _gap(mark=D("12345.678"), bid=D("12345.678"), threshold=D("5E-324")).outcome == "CLEAR"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:
```bash
"$PY" -X utf8 -I -B -c "import sys; sys.path.insert(0, '.'); from tests.control_acceptance import _main; raise SystemExit(_main(['control_risk']))"
```
Expected: `0/1 passed, 1 failed` with `FAIL control_risk/import ImportError: cannot import name 'BID_GAP_MAXIMUM' from 'execution_control.risk'`.

- [ ] **Step 3: Write the minimal implementation**

Append to `execution_control/risk.py`:

```python


BID_GAP_MAXIMUM = Decimal("0.05")          # BR-26: the software-wide ceiling on Y, inclusive; never a private value
_STALE_MARK = timedelta(seconds=30)        # BR-10: a bid is read only for a mark older than this by server time


@dataclass(frozen=True, kw_only=True)
class BidGapJudgment:
    """BR-10 for one held coin at one observation. A diagnosis only: never a sell, a cancel or a permit, and it
    proposes no new Y (BR-26: a decision made from this observation applies only to later ones)."""
    outcome: str                        # MARK_FRESH | CLEAR | BID_GAP | QUOTE_UNAVAILABLE
    threshold: Decimal                  # the Y applied: the one in force before this observation, 0 when none
    recheck_price: Decimal | None       # BID_GAP only: the bid, for the BR-9(a) floor and daily-loss re-check
    entry_block: bool                   # BID_GAP or QUOTE_UNAVAILABLE: set the entry block and alert (BR-9(b))
    buy_preparation_allowed: bool       # False while no signed Y is in force (OQ10); the entry block is separate


def judge_bid_gap(*, mark: Decimal, mark_at: datetime, server_at: datetime, bid: Decimal | None,
                  threshold: Decimal | None) -> BidGapJudgment:
    """BR-10 with BR-26's threshold order. `mark` is the coin's last public trade (its time `mark_at`), `server_at`
    the observation's Upbit server time, `bid` the best bid read for this observation (None when it could not be
    read or the book was empty) and `threshold` the Y already in force for this observation (None when no signed Y
    is in force, which checks at Y = 0 and prepares no buy). A mark at most 30 s old needs no bid. Otherwise
    bid <= mark x (1 - Y) is BID_GAP, whose re-check price is the bid; the mark stays the last trade for equity, the
    minimum, the maximum and H. A missing bid is QUOTE_UNAVAILABLE: entry block and alert, no price re-check, and
    never evidence for a wider Y. ValueError("BID_GAP_INPUT_INVALID") on anything else."""
    try:
        valid = (_decimal(mark) and mark > 0 and _stamp(mark_at) and _stamp(server_at) and mark_at <= server_at
                 and (bid is None or (_decimal(bid) and bid > 0))
                 and (threshold is None or (_decimal(threshold) and _ZERO < threshold <= BID_GAP_MAXIMUM)))
        applied = _ZERO if threshold is None else threshold
        if valid and server_at-mark_at > _STALE_MARK and bid is not None:
            with localcontext(_context()):
                gap = mark-bid >= mark*applied     # bid <= mark x (1 - Y), exact for any signed Y
    except (DecimalException, TypeError):
        valid = False
    if not valid:
        raise ValueError("BID_GAP_INPUT_INVALID")
    allowed = threshold is not None
    if server_at-mark_at <= _STALE_MARK:
        return BidGapJudgment(outcome="MARK_FRESH", threshold=applied, recheck_price=None, entry_block=False,
                              buy_preparation_allowed=allowed)
    if bid is None:
        return BidGapJudgment(outcome="QUOTE_UNAVAILABLE", threshold=applied, recheck_price=None,
                              entry_block=True, buy_preparation_allowed=allowed)
    return BidGapJudgment(outcome="BID_GAP" if gap else "CLEAR", threshold=applied,
                          recheck_price=bid if gap else None, entry_block=gap, buy_preparation_allowed=allowed)
```

`_context()` is precision 80 with `Inexact` trapped, so the arithmetic is exact or the input is refused; the ambient context never matters. The comparison is written as `mark - bid >= mark x Y`, algebraically equal to `bid <= mark x (1 - Y)`, because `1 - Y` for a tiny signed Y (the schema accepts any positive float up to 0.05, down to `5e-324`) needs hundreds of digits and would trap, while `mark x Y` needs only the digits of `mark` plus at most 17 for a float-derived Y.

The new top-level code changes `risk.py`'s pinned initialization surface. Run the guard to see it:

```bash
"$PY" -X utf8 -I -B -c "import sys; sys.path.insert(0, '.'); from tests.control_acceptance import _main; raise SystemExit(_main(['control_guards/test_renewal']))"
```

Expected before the re-pin: `FAIL control_guards/test_renewal_validation_has_only_reviewed_pure_calls_and_import_surfaces` and `FAIL control_guards/test_renewal_effect_closure_rejects_source_io_clock_aliases_and_import_time_effects` (`execution_control/risk.py: initialization surface changed`). Review the added top-level statements (two constants built from literals, one frozen dataclass with no defaults, one function definition; no import, no I/O, no clock), then in `tests/renewal_boundaries.py` replace line 32:

```python
    "execution_control/risk.py": "852ae2f20707670b8f0429ec34da5cd338f1aeb5a812c83867f190dfc63b42b0",
```

with:

```python
    "execution_control/risk.py": "91f3f88c7d4608962ae98b873f89ab08cbc3e951605ce00b8809acff2b8d7db0",
```

That value is the surface digest of HEAD's `risk.py` with exactly the Step 3 block appended. If the block differs by any byte of code (comments and docstrings do not count), recompute it and review again:

```bash
"$PY" -X utf8 -I -B -c "import sys; sys.path.insert(0, '.'); from pathlib import Path; from tests.renewal_boundaries import _surface; print(_surface(Path('execution_control/risk.py').read_text(encoding='utf-8')))"
```

- [ ] **Step 4: Run the tests to verify they pass**

Run the Step 2 command, then the guard command above.
Expected: every `control_risk/` test passes (the five new ones plus the 28 existing), and both `control_guards/test_renewal_*` tests pass.

- [ ] **Step 5: Commit**

```bash
git add execution_control/risk.py tests/control_risk.py tests/renewal_boundaries.py
git commit -F - <<'EOF'
Add the pure BR-10 bid-gap judgment with the BR-26 threshold order

judge_bid_gap compares the best bid with the last-trade mark at the Y in
force before the observation; unset Y checks at 0 and prepares no buy; a
quote failure is its own outcome and never widens Y. Never sells.
Re-pins the reviewed risk.py initialization surface in renewal_boundaries.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

### Task 5: Verify, check line endings and open the PR

**Files:** none changed.

- [ ] **Step 1: Run the related suites** (commands in "Verification" below: compliance, control and odds in full, then the whole suite). Expected: no new failure compared with a baseline run on `origin/main`.
- [ ] **Step 2: Check line-ending parity**

```bash
git ls-files --eol core/compliance/owner.py tools/signer/sign.py execution_control/risk.py tests/compliance_owner.py tests/compliance_signer.py tests/control_risk.py tests/renewal_boundaries.py
test "$(git diff --stat origin/main...HEAD)" = "$(git diff --stat --ignore-cr-at-eol origin/main...HEAD)" && echo PARITY_OK
```
Expected: every row `i/lf w/lf attr/-text`, then `PARITY_OK`.

- [ ] **Step 3: Push and open the PR** with this body (first paragraph is mandatory):

```
This PR changes tools/signer/sign.py and the owner-log schema (limit_set gains the optional field
bid_gap_fraction). It needs the owner's code approval before merge (spec section 8; design approved under O25/O27).

A1-1 of the blocker 1 approach A plan (M7-T3), BR-26 static signed limit and BR-10 judgment:
- owner.py and sign.py accept limit_set with or without bid_gap_fraction (finite JSON number, 0 < f <= 0.05);
  existing two-field records and signatures verify unchanged.
- D12: unset is the tightest; the first value and any increase loosen from the next Asia/Seoul date (armed-session
  and halt rules); a decrease applies at its entry; a two-field record leaves Y unchanged.
- owner.bid_gap_fraction(state) -> exact Decimal or None; risk.judge_bid_gap is the pure BR-10 judgment.
Touches D14 files core/compliance/owner.py and execution_control/risk.py (both in the driver identity list, so
deployment_code_sha256 moves). tests/renewal_boundaries.py re-pins the reviewed risk.py initialization surface
(new top-level constants, BidGapJudgment and judge_bid_gap; no import, I/O or clock). No CAPTURE_FILES change. No live behaviour change: nothing calls the new functions yet.
Tests: 9 compliance and 5 control tests added; compliance, control and whole-suite runs listed below.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
```

---

## Later PRs

Each PR below gets its own detailed plan (writing-plans format, TDD tasks with full code) before any coding, written against the HEAD of that day. The task lists here fix names, files and test intents only.

### A1-2 tasks
0. **Decide N17** (pocket transfer read) from the documentation and the A0/OQ18 results; record the outcome in the PR body.
1. **Allowlists and pins.** Files: `execution/upbit_inquiry.py:17-31`, `tests/execution_guards.py:855-859, 1129-1133, 1149-1154`, `tests/execution_read_capture.py:69-73`, `tests/renewal_boundaries.py:25` (reviewed re-pin). Produces the two pairs in `ENDPOINTS`, `READ_CAPTURE_ENDPOINTS`, `PUBLIC`. Tests: `test_allowlists_are_pinned` (17/11/7 sets), `test_exact_capture_subset_is_eleven_existing_get_pairs` (exact set, strict subset), `test_capture_endpoint_pin_does_not_expand_inquiry_permission` (`:1392`, unchanged, still passes).
2. **Helpers.** Files: `execution/upbit_inquiry.py` after `:100`, `tests/execution_upbit.py`. Produces `trade_ticks_params`, `trade_ticks`, `minute_candles` and the constants above. Tests: `test_trade_list_and_minute_candle_helpers_send_fixed_keyless_gets` (exact path, params, `Accept` only), `test_trade_list_and_minute_candle_helpers_refuse_bad_input_before_any_send` (no send on bad input).

### A1-3 tasks
1. **No retry inside a venue wait.** Files: `execution/transport.py:54-57, 293-373, 545-563`, `tests/renewal_boundaries.py:24` (reviewed re-pin), `tests/execution_transport.py:776`, `tests/execution_read_capture.py:104, 179, 210, 228, 251`, `tests/launch_upbit_read_integration.py:194`, and any other 429-retry test the grep finds. Produces `VenueRateLimited`. Tests: `test_a_get_is_retried_once_on_connection_errors_and_5xx_but_never_on_429` (sleeps `[0.2]` on 429), `test_rate_limit_error_carries_status_retry_after_and_remaining_req` (fields from headers, message unchanged), the five read-capture tests on 503 (unchanged assertions otherwise), the read-integration retry test on 503 plus its one-attempt 429 case.
2. **Shared hold.** Files: create `execution_accounts/public_read_budget.py`, `tests/accounts_public_read_budget.py`, register in `tests/accounts_acceptance.py:9`; `tests/accounts_guards.py:21-27` (`TRANSPORT_IMPORTS`) and its reviewed write exception. Produces `PublicReadBudget(root).hold_until/record/check`. Tests: `test_429_and_418_hold_reads_until_retry_after_across_restarts`, `test_absolute_deadline_honours_server_duration_when_the_local_clock_is_ahead`, `test_418_without_retry_after_uses_the_conservative_backoff_and_never_shortens_a_longer_hold`, `test_hold_refuses_before_send_and_never_touches_the_network`, `test_a_hold_or_session_lock_written_in_the_probe_format_is_honoured_and_ours_is_readable_by_the_probe`.

### A1-4 tasks
1. **Row parsing and the read gate.** File `execution_accounts/trade_list.py`. Produces `PublicTrade`, `TradeListError`, `SETTLE`. Tests: `test_rows_parse_exact_decimals_and_millisecond_utc_times` (strict JSON, Decimal), `test_read_gate_requires_server_time_at_or_after_end_plus_settle_plus_one_second` (one second short: no request).
2. **Walk.** Produces `TradeWalk`, `walk_trade_list`, `REACH_UTC_DAYS`. Tests: the eight ported walk tests listed in the PR sequence.
3. **Registration.** Files `tests/accounts_guards.py:21-27`, `tests/accounts_acceptance.py:9`. Tests: `test_account_suite_is_complete_and_registered` (`tests/accounts_guards.py:264`) and the route guard pass with the new module.

### A1-5 tasks
1. **Coin set.** `coins_needing_paths`. Test: `test_every_coin_with_a_balance_fill_flow_or_residual_gets_a_path_except_unlisted`.
2. **Fold with same-millisecond sets.** `value_trade_path`, `TradePathValuation`. Tests: the remaining five listed in the PR sequence.

### A1-6 tasks
1. **Pin the old codes first.** Add tests on HEAD for `CONTINUOUS_OPENING_MARK_STALE_OR_FUTURE` and `COLLECTOR_TICKER_STALE_OR_FUTURE` (they have none), then change them with the code.
2. **Collector marks and bid evidence.** `upbit_collector.py:132-141, 436-458`, `BidObservation`. Tests: `test_stale_last_trade_stays_the_mark_and_the_bid_is_recorded_as_evidence`, `test_a_thin_coin_keeps_its_last_trade_mark_and_an_empty_book_is_recorded_not_refused`.
3. **Provider and continuous age checks.** `provider.py:236`, `continuous.py:198-199, 233-234`. Tests: positions case of `test_stale_fx_prices_or_restrictions_are_not_relabelled_fresh` (old accepted, future refused), `test_opening_mark_of_any_age_is_accepted_but_a_future_one_refuses`.

### A1-7 tasks
1. **Ticker comparison.** `ticker_findings`, `CheckFinding`. Tests: the three ticker tests listed.
2. **Own-fill canary.** `own_fill_findings`. Tests: the three canary tests listed.

### A1-8 tasks
1. **Audit.** `MinuteCandle`, `audit_minutes`, `CANDLE_FINALITY`. Tests: the five audit tests listed.

### A1-9 tasks
1. **Integer-quanta allocation.** `_fees` rewrite and `FeeAllocation`. Tests: the five fee tests listed, plus the updated fee halves of `tests/launch_account_interval.py:275` and `tests/launch_guard_capture_material.py:327`.

### A1-10 tasks
1. **Order types.** `upbit_collector.py:279-286, 313-321`, provider `:268-298`. Test: `test_price_market_and_best_orders_are_accepted_with_their_own_quantity_rules`.
2. **Flows.** `upbit_collector.py:325-343`, provider `:212-229`, `model.py:79-85`. Tests: `test_coin_and_krw_flows_pending_and_reversed_states_are_recorded_not_refused`, `test_withdrawal_fee_is_part_of_the_outflow`, `test_canonical_bodies_of_existing_flows_are_unchanged`.
3. **Fence, locks and residuals.** `collector.py:112-130`, `upbit_collector.py:237-243, 402-405, 440-441`, provider `:245-248`, consumers in `tools/owner/rehearsal.py` and `guard_capture_format.py:159-165`. Tests: `test_lock_differences_are_recorded_as_residuals_not_refused`, `test_fence_is_replaced_by_the_scope_record`, `test_coin_deposit_enters_inventory_and_an_unmatched_difference_is_preserved`.

### A1-11 tasks
1. **Classification.** `classify_changes`, `ClassifiedChange`, `ORIGINS`. Tests: the two classification tests listed.
2. **Lot ledger.** `LotLedger`. Tests: outflow charging, locked units, pocket origin, coin deposit lot.
3. **Residual records.** Test: `test_unexplained_residual_keeps_evidence_and_unresolved_status_until_linked_once`.

### A1-12 tasks
1. **Rebuild function.** `rebuild_boundary`, `BoundaryValue`, `boundary_status`. Tests: rebuild at 29 s, missed at 31 s, computed not relabelled.
2. **Wire into the candidate preview and the material replay.** `account_interval.py:44, 304-306, 313, 431-436, 458`, `guard_capture_material.py:259-265, 284`. Tests: the slot 20-30 s test, the recovery-proof test; the `UpbitIntervalSource` bracketing tests pass unchanged (the committing switch is A2-6).

### A1-13 tasks
1. **Capture schema 2.** `guard_capture_format.py:26, 105, 140-213` (including the `origin` field pins), `guard_capture_material.py:31-41, 130-139`. Tests: schema 2 round trip, origin tag round trip, schema 1 replay unchanged, oversized gap refusal.
2. **Path source and coverage verifier.** Create `execution_accounts/trade_path_source.py`; `continuous.py:32-37, 157-159, 186`; `account_interval.py:397-414` (`:118-126` unchanged). Tests: preview-only gate, held-inventory preview through `ContinuousUpbitCandidateSource.collect`, `test_held_inventory_interval_refuses_without_price_path` unchanged, bid gap judged with the Y in force before the observation.
3. **Identity lists.** `driver.py:38-85`, `sign.py:1415-1462`. Tests: `test_detached_review_source_closure_covers_each_lossless_history_dependency`, `tests/launch_driver_carry.py` and `tests/launch_carry_review.py` closure tests.

### A1-14 tasks
1. **Archive adapter.** `tools/research/bid_gap_archive_adapter.py` `read_observations`. Tests: hash, cutoff and model-version refusals.
2. **Replay with the signed ceiling.** `replay_with_ceiling` on PR #70's `replay`. Tests: the thirteen replay tests listed.

### A2-1 tasks
1. **Journal kinds and fold.** `store.py:25-28`, `controller.py:219-245, 280-412`. Test: extended `test_invalid_payloads_and_events_never_extend_the_journal`.
2. **Buy latch, unblock fold and the OQ10 gate.** `controller.py:1051-1059`, `Controller.block_entries` (no release method; M7-T10 adds it on a verified approval object), `session.py:164-168`. Tests: the seven controller and session tests listed.
3. **Guard transaction rule.** `continuous_guard_commit.py:196-200`. Test: `test_entry_block_is_never_written_inside_an_open_guard_transaction`.
4. **Durable alerts.** Create `execution_launch/alert_store.py`; `coordinator.py:617-627`; identity lists. Tests: the two alert tests listed.

### A2-2 tasks
1. **Terms at an instant.** `owner.limit_terms_at`. Test: `test_limit_terms_at_replays_an_instant_without_future_tightenings`.
2. **Claim and term comparison.** `continuous_guard.py:63-75, 192-194, 369-372`, `committed_account.py:73-74, 281-284, 358`, `committed_producer.py:277-306, 317-320`, `continuous_guard_commit.py:135-136`, `controller.py:762-782`, `guard_generation_format.py:38-39, 168-180`. Tests: unchanged-terms continuation, updated `:228` and `:248` tests.
3. **Cuts.** Interval cutting at D12 effect points. Tests: tightening cut, loosening cut, cut-point floor.

### A2-3 tasks
1. **Seed and judge every point.** `continuous_guard.py:470-528`. Tests: interior-trade halt, controller-fold seed.
2. **CBA re-check.** `continuous_guard.py:438-440`, `account_interval.py:346-349`. Tests: CBA re-check, daily-loss stop.
3. **Halt order and pending halt.** `continuous_guard_commit.py:366-385`, `controller.py:814-838`. Tests: owner-log halt after completion, pending halt.
4. **Live candle audit.** The lagging coordinator step over `candle_audit.audit_minutes` and the archived path trades. Tests: the three live audit tests listed.

### A2-4 tasks
1. **Reducer convention and schema 3.** `baseline.py:51-65, 127-150, 185-218, 234, 278-283`. Tests: digest binding, re-anchor requirement, schema 1/2 round trip.
2. **F and raw protections.** `baseline.py:309-315, 332-352`, `model.py:171-180`, `controller.py:219-245, 295-317, 1061-1065`, and the raw-floor check at every judged point in `continuous_guard.py:479-528`. Tests: deposit, withdrawal, protected-floor alert, adjusted H, interior point below the protected raw floor.
2b. **OQ8 booking.** Confirmed residuals from A1-11 are booked once (negative as a loss judged against the floor and daily loss, positive as a flow that never raises adjusted H); unresolved ones are never booked; a later correction links to the observation. Tests: the four residual tests listed.
3. **Remove the coupled flow refusals.** `baseline_bridge.py:61-62, 71-76`, `continuous_guard.py:420-426, 447`, `guard_capture_material.py:308-311`, `account_interval.py:133, 385`, and the doc `docs/account-baseline-integration.md:200-218`. Tests: the updated bridge and guard flow tests.

### A2-5 tasks
1. **Interval kind and marker.** `baseline.py:80-124, 153-177, 208-211, 291-311`. Tests: marker exemption, 22:00 without checkpoint, ordinary rules kept.
2. **Multi-piece commit.** `baseline_head.py:14-19, 61-65, 111-114, 233-248`, `baseline_store.py:169-178`. Tests: all-or-none commit, rewritten `launch_baseline_head.py:151`.
3. **The remaining 30 s sites.** Every site listed under A2-5 Files, including the producer's owner bracket `committed_producer.py:464-466` with the guard's `continuous_guard.py:373-375`. Tests: `test_freshness_applies_to_the_last_piece_only`, `test_long_interval_owner_terms_are_folded_from_the_log_not_bracketed_live`.

### A2-6 tasks
1. **Timer lateness.** `coordinator.py:274-299, 1182-1191`. Tests: suspend vs overrun.
2. **Rebuild placement and status.** `coordinator.py:302-337, 1218-1219, 1231, 1272-1305`, `tools/owner/launch.py:227-245, 296-297`. Tests: gap-unit rebuild, disarm pending with progress.
3. **Judging and the BR-19 checks.** `continuous_guard.py:479-528`, `committed_startup.py:247-250`. Tests: first-30 s breach, gap high then E, unverified 22:00, unjudged CBA price, true low in archive and status, BR-19 start/time/fold/day-opening checks and the F and raw-protection restore, beyond-reach stop.
4. **Committing boundary switch (from A1-12).** `account_interval.py:13-20, 111-117, 154-182`. Tests: the rebuilt-within-30 s producer test, the SD 6.2 forgiven-gap boundary test, updated `tests/launch_account_interval.py:349, 372` and `test_default_boundary_lead_*`.

### A2-7 tasks
1. **Driver and history.** `driver.py:318-347, 466-489, 494-512`, `live_history.py:169-197, 556-574`. Tests: app-unit sell cap, reserved cash once, anchor rows parse, the two coded driver tests.
2. **Runner and coordinator universe helpers.** `runner.py:405-413`, `coordinator.py:141-166, 769-804, 1080-1081`. Test: owner coin outside the universe.
3. **Startup and limits.** `committed_startup.py:80-90, 401-429, 515-582`, `coordinator.py:584-585`, `controller.py:992-1026`, `continuous_guard.py:474, 532`. Tests: startup with a personal order, prior-day budget minimum.
4. **App-only strategy results (BR-25).** The study, odds and outcome-ladder fill readers filter on the `origin` tag. Test: `test_an_owner_fill_never_enters_a_strategy_result_but_counts_in_account_pnl`.

### A2-8 tasks
1. **Threshold history.** `BidGapThreshold` persisted per observation. Tests: threshold in force before the observation, restart never looser, unknown threshold after restart (entry block, Y = 0), repeated observation keeps its first record.
2. **Open the gate and move the pins.** `account_interval.py:118-126, 481-482`, `committed_producer.py:165, 188-189, 212-214`, `guard_capture_archive.py:254`. Tests: static Y live, adaptive refused unconditionally, held interval commits from the trade-list path (replaces `tests/launch_account_interval.py:265`), gate test updated.

---

## Open owner questions

### OQ9: automatic release of an entry block
1. Against what is the model's advantage measured: the decision without the model, a fixed benchmark buy, or holding cash, and over which horizon?
2. Which benefit metric counts: expected net return after fees, spread and slippage; hit rate; or a risk-adjusted figure?
3. What acceptance criterion releases the latch: which minimum, with what confidence, over how many out-of-sample observations, and how often must the model be re-qualified?
4. Which block causes may an automatic release cover (ticker mismatch, own-fill miss, candle audit, bid gap, quote failure, protected-floor alert), and which always need the manual route?

### OQ13: authority to sell personal (owner) lots
1. Which assets and which personal lots are eligible?
2. What is the maximum sale quantity (per event, per day, overall)?
3. Which independently established risk trigger (for example a floor breach or the daily stop) may start such a sale? A bid gap, a mismatch, expiry and restart are excluded by OQ5 ("never forces a sale"), and an unlisted coin has no executable sale price (BR-3).
4. What price rule applies: a minimum executable price, a maximum slippage from the bid, or both?
5. When does the authority expire, and how is it revoked?

### Decisions the design leaves open (proposed defaults)

- **N1 Walk cursor.** BR-2: "`cursor` = the oldest `sequential_id` on the page" and "`sequential_id` does not guarantee order". Default: use the last received row's id, as the A0 probe does (`tools/research/upbit_trade_probe.py:515`), and refuse a cursor that does not progress.
- **N2 Reach.** BR-17: "goes back at most 7 UTC days (`days_ago` 1 to 7)". The probe allows today plus 6 earlier days (`days_ago` 0-6, 0 omitted, `:484-488`). Default: today plus `days_ago` 1-6 until A0 shows `days_ago=7` returns data; `REACH_UTC_DAYS` is fixed from that.
- **N3 Read-gate source.** BR-1: "only once server time is at or after E + SETTLE + 1 s"; the design does not say which response supplies that time before the walk. Default: the BR-6 ticker read's `server_utc` (read first), and every page's Date must also be at or after the gate.
- **N4 Ticker trades older than S.** BR-6: "A mismatch is a ticker trade stamped before the walk's `to` bound ... not in the walked pages". The walk stops at S, so an older ticker trade is never in it. Default: compare only ticker trades with S <= t < `to`; an older ticker trade must equal the opening mark instead.
- **N5 A later two-field `limit_set`, and unsetting Y.** BR-26: "Preserve the existing two-field `limit_set` records". Default (implemented in A1-1): a record without `bid_gap_fraction` leaves Y unchanged; Y cannot be unset again (0 is out of range); to tighten as far as possible the owner signs a smaller positive Y.
- **N6 A first Y after a halt.** BR-26: "The first positive signed limit ... follows D12, including its ... halt restrictions". Under D12 a loosening never counts after any `system_halt`, so after a halt no Y can ever take effect and BR-10 checks at Y = 0 with no buy preparation for good. Default: keep D12 as written; the owner confirms or decides that a reviewed re-anchor resets it.
- **N7 Exactness of Y.** BR-26: "Accept exact decimal fractions". Default (A1-1): the signed value is the shortest round-trip decimal of the JSON number, which is the canonical line's text; no further decimal-place limit.
- **N8 Fee precision.** BR-5: "rounded down to the fee's precision". Default: the number of decimal places of the venue's `paid_fee` string for that order, done in integer quanta so the `Inexact` trap never fires.
- **N9 Stop-limit (`watch`) owner orders.** BR-21 lists "limit, price, market, best"; the collector reads `watch` orders (`upbit_collector.py:377, 432`) and refuses them (`:280`). Default: a `watch` order is an owner order with its reported lock, reconciled like the others.
- **N10 Coin deposits and FIFO.** BR-23: "Owner units = owner buy fills + coin deposits + ...". `account_fills` refuses a sale without a buy lot (`execution_control/risk.py:486-488`). Default: a coin deposit creates an owner lot valued as BR-21 values the deposit, outside app profit.
- **N11 First trading day and owner fills.** The first-trading-day checks count every fill (`upbit_collector.py:391-393`, `provider.py:383-384, 401-402`). Default: count app fills only (BR-25: "The study ... use app fills only").
- **N12 Capacity for long gaps.** BR-24 and BR-17 assume a 7-day gap is walkable; batches are capped at 2000 calls and 64 MiB (`execution_launch/upbit_read_format.py:46-52`), events at 20000 (`execution_accounts/continuous.py:32`). Default: refuse with an explicit code, keep the head at S and alert (BR-18); never truncate; raise the caps only from A0 page counts.
- **N13 Package digests after the claim change.** BR-15 and BR-26 add terms to `OwnerContextClaim`, which moves every package digest (`content_digest`). Default: a new generation schema version; existing archives stay readable and replay under schema 1.
- **N14 Positivity under flow adjustment.** BR-22: "Adjusted equity is marked equity minus F"; the reducer requires positive equity (`execution_accounts/baseline.py:196-197, 230-232, 275-276`) and the controller refuses `start <= 0` (`execution_control/controller.py:298`). Default: keep raw marked equity positive in the state and carry F separately; a raw equity of 0 (full withdrawal, or only unlisted coins) stops the chain with an alert until the reviewed re-anchor.
- **N15 Where the working-Y history lives.** BR-26: "Record market, policy/model digest, input cutoff, ... observation sequence and effective sequence". Default: a dedicated append-only store beside the guard archive, not a control-journal kind, so it never interferes with open guard transactions (`continuous_guard_commit.py:196-200`).
- **N16 Controlled mode versus A2.** Spec 7.3: "A2, live, after controlled mode"; checklist M7-T6 (controlled launcher) waits on M7-T3. Default: A2 PRs land and are tested in rehearsal mode; M7-T6 lifts `coordinator.py:394` afterwards.
- **N17 Pocket transfer records.** BR-21/OQ11: `포켓관리` "may also be needed to read the transfer records". `execution/upbit_inquiry.py:17-31` has no such endpoint, and any later addition moves the study capture digest (`execution_launch/study.py:63-65`). Default: before A1-2's detailed plan, read Upbit's documentation and the A0/OQ18 results; if a documented query-only read exists, A1-2 adds it to `ENDPOINTS` and `READ_CAPTURE_ENDPOINTS` with pinned tests before the freeze. If not, in M7-T3 a pocket move stays an unresolved OQ8 residual (A1-10, A1-11), and adding the read later is its own task after OQ11 provisioning that re-runs the study capture digest.
- **N18 Egress tracking.** BR-24: "Track the currently observed egress ... For unknown sharing or a change of public egress, assume shared capacity, reduce pacing or pause". Observing the public egress needs a request to a non-venue service, which no allowlist permits. Default: A1-3 treats sharing as always unknown (shared pacing, the hold in one coordination folder shared with the A0 probe in its file format, documented for QUANTGEN readers); route-change detection is a later task after the O28 network observation, and the owner confirms the PC/network arrangement (OQ17).
- **N19 Signed adaptive terms.** BR-26 "Signed terms": an adaptive deployment binds the model, evidence source, asset scope, horizon, confidence criterion and direction-to-Y mapping by digest, and loosening them follows D12. A1-1 adds only the static `bid_gap_fraction`. Default: the owner-log record for those terms (`owner.py` schema, D12 fold with loosening at the next Seoul date, the `sign.py` mirror with owner code approval, and A2-8-style live validation) is a separate code task after M11-T5 decides the model and signing scope, outside M7-T3; until it lands A2-8 refuses adaptive working Y unconditionally and the live Y is the static signed value.

---

## Verification

From the clone root in Git Bash:

```bash
cd <the clone root>
PY=".venv/Scripts/python.exe"   # the checkout's own venv, or any Python with the pinned requirements
```

Related tests for A1-1 (about 20 s each plus the slow signer module):

```bash
"$PY" -X utf8 -I -B -c "import sys; sys.path.insert(0, '.'); from tests.compliance_acceptance import _main; raise SystemExit(_main(['bid_gap']))"
"$PY" -X utf8 -I -B -c "import sys; sys.path.insert(0, '.'); from tests.compliance_acceptance import _main; raise SystemExit(_main(['compliance_owner/']))"
"$PY" -X utf8 -I -B -c "import sys; sys.path.insert(0, '.'); from tests.compliance_acceptance import _main; raise SystemExit(_main(['compliance_signer/']))"
"$PY" -X utf8 -I -B -c "import sys; sys.path.insert(0, '.'); from tests.control_acceptance import _main; raise SystemExit(_main(['control_risk/']))"
"$PY" -X utf8 -I -B -c "import sys; sys.path.insert(0, '.'); from tests.control_acceptance import _main; raise SystemExit(_main(['control_guards/']))"
"$PY" -X utf8 -I -B -c "import sys; sys.path.insert(0, '.'); from tests.odds_acceptance import _main; raise SystemExit(_main(['odds_plan/']))"
```

Expected: `9/9 passed` for `bid_gap`, and every test in the other selections passes (`compliance_signer/test_commands_sign_exactly_what_was_shown` excepted when not run with the checkout's own `.venv`; see below).

Each suite in full (none of these writes a repo file):

```bash
for s in compliance control execution odds; do
  "$PY" -X utf8 -I -B -c "import sys; sys.path.insert(0, '.'); from tests.${s}_acceptance import _main; raise SystemExit(_main([]))" > "/tmp/a1_$s.log" 2>&1; echo "$s exit $?"
done
for s in accounts launch; do
  "$PY" -X utf8 -I -B -c "import sys; sys.path.insert(0, '.'); from tests.${s}_acceptance import main; raise SystemExit(main([]))" > "/tmp/a1_$s.log" 2>&1; echo "$s exit $?"
done
grep -h "^FAIL" /tmp/a1_*.log
```

The whole suite without writing `qa/acceptance_results.json` (a tracked file that `tests/run_all.py main` rewrites):

```bash
"$PY" -X utf8 -I -B -c "import sys; sys.path.insert(0, '.'); from tests.run_all import tests, run; r = run(tests()); f = [x['test'] for x in r if x['status'] == 'FAIL']; print(len(r), 'run;', len(f), 'failed:', f); raise SystemExit(1 if f else 0)" > /tmp/a1_all.log 2>&1; tail -1 /tmp/a1_all.log
```

Expected: no failure that the same command does not also show on `origin/main`. With any venv other than the checkout's own `.venv`, two compliance tests fail on both because the venv is not the checkout's own `.venv`: `compliance_guards/test_cryptography_is_pinned_installed_and_usable` ("cryptography loaded from another venv, not .venv") and `compliance_signer/test_commands_sign_exactly_what_was_shown` ("run the suite with .venv/Scripts/python.exe"). They are environmental and must be identical before and after; on the owner's PC with `.venv` both pass. Measured on a scratch copy of `41f255f` with A1-1 applied: compliance 466/473 passed, 2 failed (those two), 5 not run; control passes once `tests/renewal_boundaries.py:32` is re-pinned.

Working tree and line endings:

```bash
git status --short                       # only the files this PR names
git ls-files --eol <each changed file>   # unchanged i/ and w/ columns
test "$(git diff --stat origin/main...HEAD)" = "$(git diff --stat --ignore-cr-at-eol origin/main...HEAD)" && echo PARITY_OK
```

Expected: `PARITY_OK`. If the two stats differ, a line-ending change slipped in: restore the file's original endings with Python bytes, never `sed -i`.
