# Upbit KRW universe, stage 1: implementation plan index

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement each PR plan task by task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Let one fixed rotation strategy hold any eligible Upbit KRW coin, one coin at a time, under a signed
eligibility rule, a daily public snapshot, per-coin odds and the existing session, floor and order controls.

**Architecture:** Ten PR plans, merged in order by the owner. Pure compliance code first (rule, flag classes,
snapshot format and verification), then public data readers and the snapshot writer, then the gate, then execution
in five parts (control, profile and program, terms/orders/accounts, driver and history, runner and coordinator),
then the universe study.

**Tech Stack:** Python 3.13 (venv at `TRADEGEN_PR9/.venv`, read-only), stdlib `json`, `hashlib`, `decimal`,
`dataclasses`, the repo's own transport, compliance, odds and launch modules. No new dependency.

**Spec:** [2026-11-11-upbit-krw-universe-design.md](../specs/2026-11-11-upbit-krw-universe-design.md) (revision 3,
owner-approved 2026-11-11). Every PR plan argues from it; executors read both.

## Global constraints

- Base: `origin/main` at fd85850. One branch and one PR per plan, each cut from `main` after the previous PR merged.
  The owner merges every PR on GitHub; never merge with tools. The repository is public: no secrets, amounts,
  account data or personal data in code, tests, docs or PR text.
- No new dependency; never `pip install`. The venv is read-only.
- `core/compliance` imports only stdlib, `yaml`, `cryptography`, `core.isolation` and `core.compliance`
  (`tests/compliance_guards.py:190-193`).
- `execution_control` imports only stdlib, `core.isolation`, `core.compliance`, `core.odds`, `execution.snapshot`,
  `execution.positions`, `execution_control`, `execution_orders`, and the two pinned `execution_launch.instrument_refresh`
  names in `controller.py` and `session.py` (`tests/control_guards.py:15`, `23-26`, `62-85`, `103`). No `/v1/` literal.
- `execution_accounts` writes no files (`tests/accounts_guards.py:11`, `95-96`). Pinned writers live in
  `execution_launch` or `execution_network` (`tests/launch_guards.py` `PINNED_WRITES`). `execution_launch` never
  references `load_context` and holds no `/v1/` literal.
- Upbit public paths are added only to `execution/upbit_inquiry.py` `ENDPOINTS` and `PUBLIC`; the pins in
  `tests/execution_guards.py` and `tests/renewal_boundaries.py` are updated by hand after review, never regenerated.
- Fixed-symbol (KRW-BTC) profiles, protocols, programs and sessions keep today's digests byte for byte. Every new
  dataclass field defaults to `None` and is left out of its canonical encoding when `None`; every closed-key parser
  accepts the old key set and the old set plus the new keys (spec section 10).
- Tests are offline: fake `transport._send` seams and fixtures, all KEYLESS inputs, temporary state. Never call a real
  exchange, never read `.env`, never write the real `~/.tradegen` or `~/.nextgen`. Set `TRADEGEN_RUNS_DIR` to scratch.
- No signing, arming, session preparation with real data, or live order. `core/compliance/kr_rules.yaml`,
  `instruments.yaml` and `core/odds/venues.yaml` are not edited by these PRs; the owner adds `universe_rule` to
  `venues.yaml` and signs it after code-approve (spec section 16).
- Line endings are byte-exact (`.gitattributes` is `* -text`). Python and YAML files are LF, except
  `execution_launch/study.py` (CRLF); `docs/superpowers` specs and plans are CRLF, except
  `2026-10-23-compliance-gate-and-odds-engine-design.md` (LF). Never `sed -i`. Before each commit, `git diff --stat` must equal
  `git diff --stat --ignore-cr-at-eol`.
- Frozen and pinned files stay byte-identical (`grokteam/out/PREREG_book.json`, `frozen_book/`, frozen research).
- Commit messages end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. PR bodies end with
  `🤖 Generated with [Claude Code](https://claude.com/claude-code)`.
- This is software design, not legal, tax or investment advice.

## Running tests

The repo has no pytest. Each suite exposes `tests()` with its isolation wrapper. Focused runs use this function
(define it once per shell, after setting `SCRATCH` to your session scratchpad directory as a Git Bash path):

```bash
PY="$HOME/OneDrive/Desktop/TRADEGEN_PR9/.venv/Scripts/python.exe"
export TRADEGEN_RUNS_DIR="${SCRATCH:?set SCRATCH to your session scratchpad directory}/runs_scratch"
focus() { "$PY" -X utf8 -c "import importlib,sys; from tests.run_all import run; s=importlib.import_module('tests.'+sys.argv[1]+'_acceptance'); rows=run([(n,f) for n,f in s.tests() if sys.argv[2] in n]); sys.exit(0 if rows and not any(r['status']=='FAIL' for r in rows) else 1)" "$@"; }
```

`focus <suite> <module>/<test_name>` runs matching tests, where `<suite>` is one of `compliance`, `odds`,
`execution`, `control`, `accounts`, `launch`. A new test module is added to its suite's `MODULES` tuple
(`tests/<suite>_acceptance.py`) in the same task that creates it. The full suite is
`"$PY" -X utf8 -m tests.run_all` (long; run once per PR before the PR is opened).

## PR order and dependencies

| Plan | Scope (spec sections) | Needs |
|---|---|---|
| [PR 0](2026-11-11-upbit-krw-universe-pr0-driver-pin.md) | Driver pin fix for fixed profiles (12, first bullet) | main |
| [PR 1](2026-11-11-upbit-krw-universe-pr1-compliance-pure.md) | Rule parser, flag classes, snapshot format and verification, `Universe`, `universe_path`, research note (4, 5) | main |
| [PR 2](2026-11-11-upbit-krw-universe-pr2-data.md) | Public Upbit helpers, snapshot builder, `daily_bars`, per-slot flag and ticker source, snapshot writer and CLI (5, 7, 9) | PR 1 |
| [PR 3](2026-11-11-upbit-krw-universe-pr3-gate.md) | `Context.universe`, read-back, gate exit/buy/recorded-order paths, public `lookup` (8, 18) | PR 1 |
| [PR 4a](2026-11-11-upbit-krw-universe-pr4a-control.md) | `RiskResult.universe`, `OrderState` fields, kill reason, session encoding, journal kind, odds batch, session binding and verification, odds card wording (6, 7, 9) | PR 3 |
| [PR 4b](2026-11-11-upbit-krw-universe-pr4b-profile-program.md) | Universe profile and protocol fields, digest selectors at every site, `_bound_profile`, program kind and chooser (10, 12, 14) | PR 0, PR 1 |
| [PR 4c](2026-11-11-upbit-krw-universe-pr4c-terms-orders-accounts.md) | Terms authority v2, renewal with `allow_symbol_change`, IOC orders, collector/provider/E1 for unlisted and thin coins, E1 alerts (10, 11, 15) | PR 2, PR 3, PR 4b |
| [PR 4d](2026-11-11-upbit-krw-universe-pr4d-driver-history.md) | Universe driver, LiveHistory following the trade coin, history row v2, incremental chooser and frame inputs (12) | PR 2, PR 4c |
| [PR 4e](2026-11-11-upbit-krw-universe-pr4e-runner-coordinator.md) | Runner allow-list, sell guard and session checks, coordinator sequence, trade-coin choice, events, toasts, status, preparation with a batch, console `odds`, rehearsal wiring (7, 9, 10, 12, 13, 15) | PR 4a, PR 4d |
| [PR 5](2026-11-11-upbit-krw-universe-pr5-study.md) | Evaluator `forward-universe-v1`, universe capture, per-market parsers, size check, family `prior_attempts`, study rule, tooling, doc amendments (14, 18) | PR 4e |

Deviations from spec section 19:

- The program kind and chooser move from PR 5 to PR 4b, because LiveHistory (PR 4d) runs the chooser before the
  study exists. With them move `UNIVERSE_EVALUATOR_REVISION`, `strategy._protocol` accepting `forward-universe-v1`,
  and the `tools/research/prepare_launch_example.py:70` digest selector; PR 5 only checks the selector.
- PR 4 is split into 4a to 4e as the spec allows.
- Spec section 14's one-request-per-market fallback is deferred until the section 17 measurement. PR 5 sends one batch
  GET for books and one for ticks and records a refused batch as `unavailable`.
- If the separate driver-renewal session lands the driver pin first, PR 0 is skipped and PR 4b rebases on it.

## Interface contract

New names only; existing names come from the code at fd85850. A plan that needs a different name changes this table
first. Types use `datetime` (aware, UTC), `date`, `Decimal`.

### PR 0, driver

- `execution_launch/driver.py` `_validate_frame(callback, frame, observation)`, signature unchanged, refuses
  `FIXED_DRIVER_SCOPE_MISMATCH` when `observation.profile` is not a `LaunchProfile` or its `(venue, market,
  account_scope)` differs from the protocol's and the driver profile's, and `FIXED_DRIVER_PROFILE_CHANGED` when its
  contract digest differs. Both codes exist today; no new name.

### PR 1, `core/compliance`

- `rules.py`
  - `UNIVERSE_MARKET = re.compile(r"KRW-[A-Z][A-Z0-9]{0,11}")`.
  - `@dataclass(frozen=True, kw_only=True) class UniverseRule: source: str; quote: str; exclude: tuple[str, ...];
    min_listing_days: int; median_days: int; min_median_value_krw: int` (`exclude` stored sorted).
  - `Venue.universe_rule: UniverseRule | None = None`; `"universe_rule"` added to `_VENUE_OPTIONAL`.
  - `universe_rule_sha256(rule: UniverseRule) -> str`: sha256 hex of `json.dumps(body, sort_keys=True,
    separators=(",", ":"), ensure_ascii=True)` where `body` is the six fields with `exclude` as a list.
  - `FLAG_CLASSES = ("unflagged", "warning", "caution", "unknown", "absent")`.
  - `flag_class(entry: Mapping | None) -> str`: one market object of `market/all?is_details=true`; `None` is
    `"absent"`. Rules exactly as spec section 4.
  - `market_flags(body: bytes) -> dict[str, str]`: every market in the body whose id matches `UNIVERSE_MARKET`,
    mapped to its class. Raises `UniverseError` if the body is not a JSON list of objects.
  - `universe_requests(rule: UniverseRule, market_all_body: bytes, day: date) -> tuple[tuple[str, tuple[tuple[str, str], ...]], ...]`:
    the exact `(path, params)` set, sorted. `market/all` params `(("is_details", "true"),)`. Candle params, in this
    order: `("market", m), ("to", "<YYYY-MM-DD>T00:00:00Z"), ("count", "<n>")`.
  - `universe_eligible(rule: UniverseRule, receipts: Sequence[Mapping], day: date) -> tuple[tuple[str, ...], tuple[tuple[str, Decimal], ...]]`:
    `(listed, eligible)`; `listed` sorted; `eligible` sorted by market, each with its median daily value.
  - `universe_top_n(universe: Universe, n: int) -> tuple[str, ...]`: largest median first, ties by market ascending.
  - `encode_universe_snapshot(rule: UniverseRule, day: date, receipts: Sequence[Mapping]) -> tuple[bytes, str]`.
  - `verify_universe_snapshot(raw: bytes, rule_sha256: str) -> Universe`.
  - `class UniverseError(ValueError)` with refusal codes `UNIVERSE_RULE_INVALID`, `UNIVERSE_BODY_INVALID`,
    `UNIVERSE_RECEIPT_INVALID`, `UNIVERSE_REQUEST_SET_MISMATCH`, `UNIVERSE_NOT_FINAL`, `UNIVERSE_MANIFEST_MISMATCH`,
    `UNIVERSE_RULE_MISMATCH`.
  - Plain receipt: a dict with exactly `path`, `params` (list of `[k, v]`), `account_scope` (`"public"`),
    `received_at`, `server_time` (ISO 8601 UTC strings), `raw_body_b64`, `sha256`.
- `model.py`: `@dataclass(frozen=True, kw_only=True) class Universe: day: date; rule_sha256: str; snapshot_sha256: str;
  built_at: datetime; valid_from: datetime; valid_until: datetime; listed: tuple[str, ...];
  eligible: tuple[tuple[str, Decimal], ...]`.
- `owner.py`: `universe_path(day: date, sha256: str) -> Path`, under the same root as `evidence_path()`, as
  `universe/<YYYY-MM-DD>/<sha256>.json`; `universe_dir(day: date) -> Path`.

### PR 2, data

- `execution/upbit_inquiry.py`: `MARKET_ALL_PATH = "/v1/market/all"`, `CANDLES_DAYS_PATH = "/v1/candles/days"`;
  `CANDLE_COUNT_MAX = 200`; `candle_params(market: str, to: datetime, count: int) -> tuple[tuple[str, str], ...]`;
  `market_all() -> Answer`; `daily_candles(market: str, to: datetime, count: int) -> Answer` (`count` 1..200);
  `orderbook_instruments(markets: Sequence[str]) -> Answer`; `tickers(markets: Sequence[str]) -> Answer`.
- `execution_accounts/universe.py`
  - `build_universe_snapshot(rule: UniverseRule, day: date, *, clock) -> tuple[bytes, str]`.
  - `@dataclass(frozen=True) class UniverseBars: market: str; bars: tuple[tuple[str, float, float], ...];
    receipt_sha256: tuple[str, ...]` (each bar `(UTC date "YYYY-MM-DD", open, close)`, the row `load_leg`'s
    `upbit_daily` path yields, oldest first).
  - `daily_bars(markets: Sequence[str], *, now: datetime, clock) -> dict[str, UniverseBars]`.
  - `@dataclass(frozen=True) class FlagRead: ok: bool; received_at: datetime | None; sha256: str | None;
    flags: Mapping[str, str]` (KRW markets present in the read, each with its class).
  - `@dataclass(frozen=True) class TickerRead: ok: bool; received_at: datetime | None; sha256: str | None;
    prices: Mapping[str, tuple[Decimal, datetime]]` (trade price, trade time).
  - `@dataclass(frozen=True) class UniverseSlotSource: clock: Callable` with `read_flags() -> FlagRead` and
    `read_tickers(markets: Sequence[str]) -> TickerRead`. Never raises for a failed read; returns `ok=False`. A
    non-callable clock refuses `UNIVERSE_CLOCK_REQUIRED`.
  - PR 5 adds `answer: Answer | None = None` as the last field of `FlagRead` and `TickerRead` (`repr=False`,
    `compare=False`).
- `execution_launch/universe_store.py`: `write_snapshot(raw: bytes, day: date, sha256: str) -> Path` (`O_EXCL` on a
  temporary file, then `os.rename` after an existence check; never replaces; no `os.link`, because `scan_links`
  refuses hard links); `main(argv=None) -> int` for `snapshot --state-root <root>`.

### PR 3, gate

- `core/compliance/model.py`: `Context.universe: Universe | None = None`, sealed into `ctx_hash` only when not `None`.
- `core/compliance/model.py`: `context_hash(ctx) -> str`, used by `seal_context` and the profile and review code.
- `core/compliance/owner.py`: `load_context` fills `universe` through `_universe_now(now, active) -> Universe | None`,
  which wraps `_universe_in_force(now, rule_sha256)`, never raises and returns `None` on any failure; verification is
  cached in `_UNIVERSE_VERIFIED` by file sha256.
- `core/compliance/gate.py`: `lookup(ctx, state, venue, symbol, exits: bool, *, recorded: bool = False)
  -> rules.Instrument | None` (`state` a `model.ApprovedState`, `venue` its `rules.Venue`);
  `market_listed(state, venue, inst, counter) -> bool`; block reasons `state: universe no_rule`,
  `state: universe no_snapshot`, `state: universe not_eligible`.

### PR 4a, `execution_control`

- `RiskResult.universe: Universe | None = None`.
- `OrderState.side: str | None = None`, `OrderState.symbol: str | None = None`, `OrderState.updated_at: datetime | None = None`
  (always set for orders created after this PR).
- `Controller.kill(session_id, *, reason, now)` records `reason` when the clock check passes.
- `PreparedSession.universe_batch_digest: str | None = None`.
- `store.EVENT_KINDS` gains `"universe_odds_batch"`.
- `execution_control/universe_odds.py`: `@dataclass(frozen=True) class CoinOdds: market: str; plan_hash: str;
  seed_hex: str; inputs_digest: str; report_digest: str; passed: bool`; `@dataclass(frozen=True) class UniverseBatch:
  batch_digest: str; seoul_date: date; template_plan_hash: str; code_hash: str; state_hash: str; owner_head: str;
  rule_sha256: str; snapshot_sha256: str; n: int; coins: tuple[CoinOdds, ...]; started_at: datetime;
  finished_at: datetime; prior_batches: int`; `run_batch(controller, template, bars: Mapping[str, UniverseBars], *,
  n: int, now: datetime, clock) -> UniverseBatch`; `registered_batch(batch_digest: str) -> UniverseBatch | None`.
- `session.prepare_session(..., universe_batch: UniverseBatch | None = None)`; refusal codes
  `SESSION_UNIVERSE_BATCH_UNREGISTERED`, `SESSION_UNIVERSE_BATCH_STALE`, `SESSION_UNIVERSE_BATCH_FAILED`,
  `SESSION_UNIVERSE_TEMPLATE_INVALID`.

### PR 4b, profile and program

- `execution_launch/profile.py`: `LaunchProfile.universe_rule_sha256: str | None = None`;
  `rule_terms_digest(rules, *, universe_rule_sha256: str | None = None) -> str`.
- `execution_launch/strategy.py`: `ForwardProtocol.universe_rule_sha256: str | None = None`;
  `UNIVERSE_EVALUATOR_REVISION = "forward-universe-v1"`.
- `execution_launch/program.py`: kind `"universe_top1_momentum"` with `ProgramSpec` fields `lookback_slots: int`,
  `min_hold_slots: int`, `switch_margin: Decimal`, `max_candidates: int`, `universe_rule_sha256: str` (each `None`
  for other kinds); `@dataclass(frozen=True) class ChooserState: held: str | None; hold_count: int`;
  `@dataclass(frozen=True) class ChooserSlot: top_n: tuple[str, ...]; flags: Mapping[str, str];
  prices: Mapping[str, Decimal]` (`prices` holds only defined prices; an unavailable flag read gives empty `flags`
  and `prices`; an unavailable ticker read gives empty `prices` and keeps `flags`); `choose(spec: ProgramSpec, state: ChooserState, now_slot: ChooserSlot, lag_slot: ChooserSlot | None)
  -> tuple[str | None, ChooserState]` (the decided coin or `None` for cash; spec section 14 rules 1 to 8, with
  `r_X = price_X(k) / price_X(k-L) - 1` from `now_slot` and `lag_slot`).

### PR 4c, terms, orders, accounts

- `execution_accounts/instrument_terms.py`: `UniverseTermsAuthority` (version 2, `universe_sha256` instead of
  `symbol`, `maximum_notional_krw` as a buy cap); `E1UpbitTermsSource.read(symbol: str | None = None)`;
  `TERMS_MARKET_INACTIVE` and `TERMS_MARKET_MISMATCHED` replace `TERMS_MARKET_INACTIVE_OR_MISMATCHED`.
- `execution_launch/instrument_refresh.py`: `renew_profile(..., allow_symbol_change: bool = False)`.
- `execution_control/model.py`: Upbit `time_in_force` in `{"gtc", "ioc"}`.
- `UniverseTermsAuthority(*, account_scope, universe_sha256, lot_size, min_quantity, maximum_notional_krw,
  provenance_sha256, identity_binding_sha256, valid_from, valid_until)`; `authority_digest` accepts both versions
  (v1 byte-identical).
- `TermsObservation.observed_maximum_krw: Decimal`; `within_buy_cap(observation: TermsObservation) -> bool` (`True`
  for v1; v2 needs `observed_maximum_krw >= maximum_notional_krw`); `TERMS_SYMBOL_MISMATCH`,
  `TERMS_KRW_SYMBOL_REQUIRED`.
- `renew_profile` refusals `RENEWAL_SYMBOL_CHANGE_REFUSED` (flag on a fixed profile) and
  `RENEWAL_BUY_ABOVE_UNIVERSE_CAP`.
- `execution_accounts.model.Position.unlisted: bool | None = None` (left out of `canonical` while `None`); the provider
  accepts price 0 only with `unlisted is True`. The collector reads `market/all` only when a coin is held.
- `execution.snapshot.Snapshot.market_flags: Mapping[str, str] | None = None`; `execution.checks.universe_check(ctx,
  now)` with text keys `HELD_UNLISTED`, `HELD_WARNING`, `HELD_FLAGS_UNKNOWN`, `UNIVERSE_NO_SNAPSHOT`.
- `tools/owner/rehearsal.py`: `AccountAudit.universe_terms_authority: UniverseTermsAuthority | None = None`.

### PR 4d, driver and history

- `execution_launch/driver.py`: `@dataclass(frozen=True, kw_only=True) class UniverseBar: observed_at: datetime;
  received_at: datetime; symbol: str; tick_size: Decimal; bid: Decimal | None; ask: Decimal | None;
  mark: Decimal | None; source_sha256: str | None` (book fields `None` when the book was unavailable; `PaperBar` is
  unchanged). `@dataclass(frozen=True, kw_only=True) class ChooserInputs: held: str | None; hold_count: int;
  top_n: tuple[str, ...]; flags: tuple[tuple[str, str], ...]; prices: tuple[tuple[str, Decimal], ...];
  lag_prices: tuple[tuple[str, Decimal], ...] | None`. `HistoryFrame.universe_sha256: str | None = None` and
  `HistoryFrame.chooser_inputs: ChooserInputs | None = None` (omitted when `None`). `chooser_decision(program:
  ProgramSpec, inputs: ChooserInputs) -> tuple[str | None, ChooserState]`; refusals
  `FIXED_DRIVER_CHOOSER_INPUTS_REQUIRED`, `FIXED_DRIVER_BOOK_UNAVAILABLE`.
- `execution_launch/live_history.py`: `@dataclass(frozen=True) class SlotUniverse: snapshot: Universe | None;
  flags: FlagRead; tickers: TickerRead; allow: frozenset[str]; reasons: tuple[str, ...]; events: tuple[str, ...]`;
  `LiveHistory.record_slot(book, account, *, trade_symbol: str | None = None, universe: SlotUniverse | None = None,
  tick_size: Decimal | None = None, positions: tuple[Position, ...] = ()) -> str` (a universe window needs the first
  three keywords and accepts `book=None`); `LiveHistory.recorded_allow: frozenset[str] | None`;
  `SIZE_FALLBACK = "HISTORY_ROW_SIZE_FALLBACK"`; refusals `HISTORY_BOOK_OFF_TICK` and `HISTORY_BOOK_MARKET_MISMATCH`
  write nothing, so the caller can record the slot again with `book=None`.

### PR 4e, runner and coordinator

- `Runner.run(timestamps, *, max_steps, should_stop, entry_allow: frozenset[str] | None = None)` and the same keyword
  on `Runner.tick`; refusal codes `RUNNER_UNIVERSE_ENTRY_NOT_ALLOWED`, `RUNNER_UNIVERSE_SNAPSHOT_MISMATCH`,
  `RUNNER_UNIVERSE_COIN_NOT_IN_BATCH`; sell guard reuses `RUNNER_OUTSTANDING_ORDERS` as `blocked`.
  `Runner.refresh_instrument_rules(renewal, *, now, account=None)` with `RUNNER_UNIVERSE_NOT_FLAT`.
- `prepare_launch_session(..., universe_batch=None)` and `Coordinator.prepare(..., universe_batch=None)`;
  `Coordinator.odds_batch(template, read_bars)` with refusals `COORDINATOR_UNIVERSE_REQUIRED`, `UNIVERSE_NO_SNAPSHOT`
  and `COORDINATOR_ODDS_BATCH_FAILED`; `LiveHistory.decided_symbol() -> str | None`.
- The tick's `entry_allow` is `LiveHistory.recorded_allow`. A `record_slot` refusal of the book is retried once with
  `book=None` in the same slot.
- Coordinator codes: `COORDINATOR_NO_TRADE_BOOK`, `COORDINATOR_UNIVERSE_DISARM`, `COORDINATOR_HISTORY_REFUSED`,
  `COORDINATOR_EVENT_FAILED`; buy-block reasons `UNIVERSE_EXTRA_HOLDING`, `UNIVERSE_REMAINDER_UNSELLABLE`,
  `TERMS_TARGET_UNAVAILABLE`, `UNIVERSE_FLAGS_UNAVAILABLE`, `UNIVERSE_TICKERS_UNAVAILABLE`, `UNIVERSE_NO_SNAPSHOT`,
  `UNIVERSE_RULE_MISMATCH`, `UNIVERSE_HELD_FLAG_UNCERTAIN`; event codes `UNIVERSE_MARKET_VANISHED`,
  `UNIVERSE_OTHER_COIN_WARNING`.
- `core/compliance/alerts.py`: public `toast(title: str, body: str) -> bool` over `_toast`;
  `execution_launch/toast_queue.py`: `ToastQueue` (one daemon worker, FIFO, failures dropped).

### PR 5, study

- `execution_accounts/quotes.py`: `parse_orderbooks(receipt, symbols: Sequence[str], now: datetime)
  -> dict[str, OrderbookQuote | str]` (a refusal code string for a market that fails);
  `read_orderbooks(symbols, *, clock) -> SourceReceipt`.
- `execution_accounts/instrument_terms.py`: `parse_instruments(receipt, symbols: Sequence[str])
  -> dict[str, Decimal | str]` (each market's tick or its refusal code); `read_instruments(symbols, *, clock)
  -> SourceReceipt`.
- `execution_launch/strategy.py`: `MAX_FRAME_MARKETS = 320` (re-exported by `study.py`),
  `UNIVERSE_CAPTURE_KIND = "tradegen-universe-capture/1"`.
- `execution_launch/study.py`: `UNIVERSE_SELECTION_RULE = "upbit-krw-universe-top1-v1"`,
  `STUDY_UNIVERSE_CANDIDATES_LIMIT = 3`, `UNIVERSE_CAPTURE_LIMIT = 12 * 1024 * 1024`;
  `build_study_plan(..., prior_attempts: Sequence[str] = ())`; `run_universe_capture(plan, *, rules, source, clock,
  wait_until, record) -> CaptureOutcome` (`rules` the frozen instrument rules, checked by `strategy._universe_rules`
  before any read); refusal `STUDY_CAPTURE_BOOKS_OVER_LIMIT`.
- The `capture` command takes `--profile PROFILE.json` exactly for a universe plan (else `STUDY_ARGUMENTS_INVALID`).

## Task conventions

Every task: write the failing test, run it with `focus` and see the stated failure, write the smallest change, run
the focused test and the module's tests, then commit only the files the task names. Each PR plan's last task runs
the guards (`compliance_guards`, `control_guards`, `accounts_guards`, `launch_guards`, `execution_guards`,
`renewal_boundaries`) and the full suite, then opens the PR with a body that lists the spec sections covered, the
tests added and what stays unverified.
