# Upbit KRW universe PR 5: universe study evaluator, capture, per-market parsers, family accounting and docs Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let the prospective study freeze, capture and evaluate up to three `universe_top1_momentum` candidates
(PR 4b's program kind and chooser) over the Upbit KRW universe, with the `forward-universe-v1` evaluator, the
`upbit-krw-universe-top1-v1` study rule, family accounting through `prior_attempts`, a 12 MiB capture size check,
batch book and tick parsers that judge each market on its own, the draft tooling and the five doc amendments.

**Architecture:** `execution_accounts/quotes.py` and `execution_accounts/instrument_terms.py` gain an account-free
batch reader and a per-market parser each, built from the existing single-market checks. `execution_accounts/universe.py`
keeps the raw `Answer` on its flag and ticker reads so the capture can record raw bodies. `execution_launch/strategy.py`
gains the `forward-universe-v1` evaluator over a compact `capture.json` (a market index, one table per snapshot, one
frame per slot), sharing the fixed evaluator's order arithmetic, metrics and result registration. `execution_launch/study.py`
gains the study rule, the program-specific feasibility, `prior_attempts`, the candidate cap, the size bound,
`run_universe_capture` (one shared set of public reads per slot, each candidate's chooser fed incrementally and its
lag-1, double-cost and lag-2 evaluator paths replayed with the evaluator's own step, so a deferred sell keeps its book
request) and the `main` wiring. The fixed KRW-BTC study path keeps its behaviour and digests, except that
`CAPTURE_FILES` gains three files (spec section 14), so every new plan binds a new capture-source digest.

**Tech Stack:** Python 3.13 (venv at `TRADEGEN_PR9/.venv`, read-only), stdlib `dataclasses`, `decimal`, `fractions`,
`collections`, `json`, `hashlib`, `base64`. No new dependency.

**Spec:** [2026-11-11-upbit-krw-universe-design.md](../specs/2026-11-11-upbit-krw-universe-design.md), sections 14 and 18

## Global Constraints

All constraints in the index apply: [2026-11-11-upbit-krw-universe-index.md](2026-11-11-upbit-krw-universe-index.md)
(base, one branch and PR, no new dependency, offline tests, `focus` runner, byte-exact line endings, never `sed -i`,
commit trailer, PR body ending, the owner merges).

Constraints specific to this PR, verbatim from the spec:

- "`price_X(j)` is the `trade_price` from slot j's ticker read, defined only if X's trade time is within 60 seconds of
  slot j. `r_X(k) = price_X(k) / price_X(k - L) - 1`, defined only when both prices are defined. A slot whose flag
  read or ticker read is `unavailable` gives no prices at all." (section 14)
- "The snapshot is read through `rules.verify_universe_snapshot` from the capture process's state root, and its rule
  sha256 must equal the protocol's. The raw snapshot bytes, the raw flag bodies and the raw ticker bodies go to the
  uncapped `receipts.jsonl` sink (`study.py:382`)." (section 14)
- "`capture.json` holds one table per distinct snapshot (sha256 to day, valid_from, valid_until and the top-N list)
  and compact per-slot frames: the snapshot sha256, the flag exceptions (coins that are not `unflagged`, with their
  class), and prices for listed coins. Fixed maxima: a market index below `MAX_FRAME_MARKETS = 320`, a flag class as
  one digit, a price as a decimal string of at most 16 characters, and a trade time as a signed millisecond offset
  from the slot within 60,000. A read with more than 320 markets is recorded as `unavailable`, never truncated; a
  coin whose price or trade time falls outside these maxima has no price at that slot." (section 14)
- "Books: for slot j, each candidate's chooser is updated incrementally on frames up to j-1, keeping the same bounded
  state as LiveHistory (the last L+1 price vectors, h and the hold count). The needed coins are the targets of
  decisions d[j-1] and d[j-2] of every candidate (what a flat lag-1 or lag-2 path buys) and the coin that each of
  the candidate's three evaluator paths (lag-1, lag-1 at double cost, lag-2) still holds (its sell, its mark and the
  terminal liquidation, including a sell deferred because its book was unusable). The capture replays each path from
  the recorded books and decisions with the evaluator's own step and the frozen instrument rules, so a sell deferred
  for any number of slots keeps its book request; because a replayed fill depends on the lot and minimums, a
  universe `capture` takes the profile (`--profile`) and checks its rules before any read. The set is deduplicated,
  cash skipped, plus KRW-BTC for the benchmark, intersected with the KRW markets in slot j's flag read. A needed coin missing from that
  read is recorded as `vanished` and not requested. If the flag read failed, the needed coins are requested as they
  are." (section 14)
- "New parsers return a result per market: `parse_orderbooks(receipt, symbols, now)` in
  `execution_accounts/quotes.py` and `parse_instruments(receipt, symbols)` in `execution_accounts/instrument_terms.py`.
  Each applies the existing single-market checks to each market on its own: `parse_orderbooks` keeps the 10-second
  book rule (`quotes.py:135`, `155-156`); `parse_instruments` applies `instrument_terms.py:192-201` and the receipt
  checks per market. If Upbit refuses several markets in one request (section 17), the capture sends one request per
  market. `parse_orderbook` and the single-instrument check stay as they are for the live runner." (section 14)
- "A book or tick that is `unavailable` or `vanished` is recorded and never raises `STUDY_CAPTURE_SOURCE_FAILED`. A
  stop, a missed slot, a sink failure or a failed account-free probe still ends every candidate's trial, as today."
  (section 14)
- "`CAPTURE_FILES` (`study.py:59-61`) gains `execution_accounts/instrument_terms.py`, `execution_accounts/universe.py`
  and `core/compliance/rules.py`, so `capture_source_code_sha256` binds every reader and parser the capture uses."
  (section 14)
- "A plan has at most 3 candidates (`STUDY_UNIVERSE_CANDIDATES_LIMIT`), so at most 16 books per slot (per candidate
  two decision targets and three held coins, plus KRW-BTC). A larger set is refused
  (`STUDY_CAPTURE_BOOKS_OVER_LIMIT`), never truncated; within the candidate cap it cannot occur." (section 14)
- "**Size.** A freeze check `STUDY_UNIVERSE_CAPTURE_SIZE` refuses a plan whose worst case (slots x the largest frame
  at `MAX_FRAME_MARKETS`, every coin flagged and every field at maximum length, plus 16 books, decisions and envelope)
  exceeds 12 MiB, leaving headroom under `MAX_CAPTURE_BYTES`. The check computes that worst case with the capture's
  own encoder, not from a prose estimate. A 48-hour window at 5-minute bars (577 slots) fits; any plan whose computed
  worst case is over 12 MiB is refused at freeze." (section 14)
- "**Evaluator revision** `forward-universe-v1`: holds at most one coin; a switch sells A at the decision slot plus
  lag and buys B one slot later, like the live driver; the lag-2 stress uses the same rule; no buy at an execution
  slot where the target is not in that slot's top-N of the snapshot in force, is not `unflagged`, or has no usable
  book or tick; no sell of a coin at a slot with no usable book for it (the trade moves to the next slot that has
  one); each bar is checked and rounded with its own recorded symbol and tick (not `strategy.py:290`'s single
  symbol); lot, minimums and fees come from the common rules; NAV marks the held coin at its book midpoint, or at
  `price_X(j)` when the book is unavailable. If neither exists, that candidate ends as a disclosed failed trial; a
  stale mark is never carried forward. The KRW-BTC benchmark follows the same rule; if it cannot be marked, the trial
  ends for every candidate, as today; a vanished coin fails only the candidates whose lag-1 or lag-2 path holds it at
  that slot; others continue; the terminal liquidation is assumed to fill fully at the bid, as today. [...] If the
  held coin has no usable book at the terminal slot, that candidate ends as a disclosed failed trial; no ticker-price
  fill is assumed; it returns the existing `ValidationResult` and `PaperMetrics` and registers its result in
  `_EVALUATED` (`strategy.py:444-445`), so `assess_strategy` accepts it (`498-500`)." (section 14)
- "**Study rule** `upbit-krw-universe-top1-v1`, accepted alongside the old rule. The freeze-time feasibility check
  becomes program-specific: warm-up L, and at most `(returns - L + 1) // max(m, 2)` round trips." (section 14)
- "`build_study_plan` takes `prior_attempts`, the registered `study_id`s of earlier attempts for the same selection,
  and each protocol's `family_members` becomes the sorted union of this plan's candidate ids and those ids.
  `study.py:216` changes to "every candidate carries the same family tuple and the tuple contains every candidate
  id". The larger K then applies to the feasibility check, the Sharpe bound and the family-adjusted p." (section 14)
- "Docs that say "single market": `docs/launch-workflow.md`, `docs/remaining-market-readiness-2026-11-06.md`,
  `docs/upbit-quote-contract.md`, `docs/instrument-term-renewal.md`, `docs/quote-timing-diagnostics.md`." (section 18)
- Tests (section 19, study): "one family member per frozen rotation, `prior_attempts` in K, the candidate cap, frame
  causality of book selection, a lag-2 switch (A, A, B, B) with the terminal bar, the warning exit through rule 1, a
  failed ticker frame, one stale book among several, a vanished non-held coin, a vanished coin held only in the lag-2
  path, an unavailable held-coin book marked from the ticker, one at the terminal slot, an unavailable benchmark, the
  worst-case size at 577 slots and a long window refused at freeze, and an evaluator run on a capture alone". The
  chooser cases belong to PR 4b (index deviation).

PR-specific rules that follow from the index:

- Base: `origin/main` after PR 4e merged. Branch `claude/universe-pr5-study`. PR 4b already delivered the program kind,
  `ChooserState`, `ChooserSlot`, `choose`, `UNIVERSE_EVALUATOR_REVISION` and the universe digests; this PR never
  redefines them.
- Line endings, checked at fd85850 with Python byte counts: `execution_launch/study.py` is CRLF (690 of 690 lines);
  every other file this PR touches is LF (`execution_accounts/quotes.py`, `execution_accounts/instrument_terms.py`,
  `execution_launch/strategy.py`, `tests/accounts_quotes.py`, `tests/launch_instrument_refresh.py`,
  `tests/launch_shortened_study.py`, `tests/launch_acceptance.py`, `tests/renewal_boundaries.py`,
  `tools/research/prepare_shortened_study.py` and the five docs). PR 2 created `execution_accounts/universe.py` and
  `tests/accounts_universe.py` as LF. New files are LF. In `study.py` every replaced and new line ends in `\r\n`: use
  the Edit tool or Python on bytes, never `sed -i`, and after every `study.py` edit run
  `"$PY" -B -c "b=open('execution_launch/study.py','rb').read(); assert b.count(b'\n') == b.count(b'\r\n'), 'mixed'"`.
- Upstream PRs shift lines. fd85850 line numbers are hints; every edit below quotes the text to locate.
- `tests/accounts_guards.py`: in `execution_accounts`, no call may be named `replace`, `request` (except the pinned
  `request("upbit", "GET", "/v1/orderbook", params)` in `quotes.py`), `send`, `_issue`, `compile` (other than
  `re.compile`), `write_text` or `mkdir`; a string constant containing `/v1/` must be a route of that file
  (`quotes.py` has only `"/v1/orderbook"`; `instrument_terms.py` and `universe.py` have none, docstrings included);
  `instrument_terms.py` imports only `Answer` and `inquiry_clock` from `execution.transport`.
- `tests/launch_guards.py` and the T15 test (`tests/launch_study.py:715-748`): `study.py` and `strategy.py` hold no
  string matching `(?i)/(?:v1|uapi|api/v5)/`; `study.py` reads a clock only inside `main`, has no top-level import of
  `execution_accounts.quotes`, `execution.transport`, `execution_orders` or `execution_control` (function-local
  imports are allowed), never names `home` or `state_root`, and its top-level statements are only the docstring,
  imports, plain assignments (no annotated assignment), functions, classes and the final `__main__` guard. The CLI
  tests patch `S.datetime` and `S.time`, so no runtime code outside `main` may use the names `datetime` or `time`.
- `tests/renewal_boundaries.py` pins the initialization surface of `execution_accounts/instrument_terms.py`; Task 2
  updates that one pin by hand after reviewing the diff. The bodies listed in its `CALLS` stay byte-identical.
- Python commands in steps use the index's `$PY` and `focus`. Tests stay offline: fake `transport._send` through
  `tests/execution_fixtures.serve`, scripted sources and temporary directories only.

## File Structure

- Modify `execution_accounts/quotes.py`: `_MAX_MARKETS`, `_markets`, `_batch_params`, `_decoded`, `_book`,
  `parse_orderbooks`, `read_orderbooks`; `parse_orderbook` reuses `_decoded` and `_book` with unchanged behaviour.
- Modify `execution_accounts/instrument_terms.py`: `_MAX_INSTRUMENTS`, `_markets`, `_instrument_tick`,
  `parse_instruments`, `read_instruments` (appended; reviewed bodies untouched).
- Modify `execution_accounts/universe.py`: `FlagRead.answer`, `TickerRead.answer`; the slot reads keep the `Answer`.
- Modify `execution_launch/strategy.py`: universe constants, `_order`, `_metrics`, `_issue_result`, `_registry`
  (extracted, fixed behaviour unchanged), the universe dispatch in `evaluate_capture_json`, and `_UniverseView`,
  `_price`, `_indexed`, `_universe_tables`, `_universe_view`, `_universe_inputs`, `_UniversePath`, `_universe_run`,
  `_universe_rules`, `_evaluate_universe`.
- Modify `execution_launch/study.py` (CRLF): constants, `CAPTURE_FILES`, `_structure`, `_room`, `_feasible`,
  `validate_study_plan`, `build_study_plan`, `_draft`, `run_capture`, the universe capture (`UniverseArchive`,
  `universe_capture_json`, `_quiet`, `_on_time`, `_raw`, `_snapshot_in_force`, `_needed`, `_price_text`, `_prices`,
  `_book_rows`, `_frame`, `_chooser_slot`, `_snapshot_tables`, `_replays`, `_universe_archive`,
  `_universe_capture_bound`, `run_universe_capture`), `_OPTIONAL`, `_arguments`, `_snapshot_files`, `_universe_source`
  and `main`.
- Modify `tools/research/prepare_shortened_study.py`: `prior_attempts` pass through `prepare_draft`.
- Modify `tests/renewal_boundaries.py`: the `instrument_terms.py` initialization pin.
- Modify `tests/launch_acceptance.py`: add `launch_universe_study` last in `MODULES`.
- Create `tests/launch_universe_study.py`.
- Modify tests: `tests/accounts_quotes.py`, `tests/launch_instrument_refresh.py`, `tests/accounts_universe.py`,
  `tests/launch_shortened_study.py`.
- Modify docs: `docs/launch-workflow.md`, `docs/remaining-market-readiness-2026-11-06.md`,
  `docs/upbit-quote-contract.md`, `docs/instrument-term-renewal.md`, `docs/quote-timing-diagnostics.md`.
- Verify only: `tools/research/prepare_launch_example.py` (a fixed launch example, PR 4b already passes the selector at
  its line 70; no study draft in it).

## Contract notes

Index contract for PR 5, and where this plan departs from the index or the spec:

- `parse_orderbooks(receipt, symbols, now) -> dict[str, OrderbookQuote | str]`, as the index says: the per-market
  value is the `OrderbookQuote` that `parse_orderbook` returns.
- `parse_instruments(receipt, symbols) -> dict[str, Decimal | str]`, as the index says: each market's tick or its
  refusal code. It never issues `InstrumentRules`, which need the lot, minimums, fee, asof and authority digest that
  only the keyed `/v1/orders/chance` read and the reviewed `TermsAuthority` supply; the study only needs the tick
  (spec: "each bar is checked and rounded with its own recorded symbol and tick"; lot, minimums and fees come from
  the common rules).
- `MAX_FRAME_MARKETS = 320` is defined in `execution_launch/strategy.py` (the evaluator needs it and must not import
  `study.py`) and imported by `study.py`, as the index says.
- `UNIVERSE_SELECTION_RULE`, `STUDY_UNIVERSE_CANDIDATES_LIMIT = 3`, `UNIVERSE_CAPTURE_LIMIT = 12 * 1024 * 1024` and
  `build_study_plan(..., prior_attempts: Sequence[str] = ())` are exactly as the index says. `prior_attempts` must be
  a tuple or list of distinct `_ID` strings that are not candidate ids (`STUDY_PRIOR_ATTEMPTS_INVALID`).
- Additions: `quotes.read_orderbooks(symbols, *, clock) -> SourceReceipt`; `instrument_terms.read_instruments(symbols,
  *, clock) -> SourceReceipt`; `FlagRead.answer` and `TickerRead.answer` (`Answer | None`, last field, default `None`,
  `repr=False`, `compare=False`); `strategy.UNIVERSE_CAPTURE_KIND = "tradegen-universe-capture/1"`,
  `MAX_PRICE_CHARS = 16`, `MAX_PRICE_OFFSET_MS = 60000`; `study.UniverseArchive`, `study.universe_capture_json`;
  private helpers `strategy._order`, `_metrics`, `_issue_result`, `_registry`, `_universe_tables`, `_universe_view`,
  `_universe_inputs`, `_UniversePath`, `_universe_run`, `_universe_rules`, `_evaluate_universe` and `study._room`,
  `_needed`, `_frame`, `_universe_capture_bound` (named in tests).
- `run_universe_capture(plan, *, rules, source, clock, wait_until, record) -> CaptureOutcome`, as the index says.
  The capture replays each candidate's evaluator paths to learn which coin each still holds (next note), and
  whether a replayed trade fills depends on the lot and minimums of the frozen rules, so it takes them and checks
  them with the evaluator's own `_universe_rules` before any read (`STRATEGY_RULES_MISMATCH`). The `capture` command
  therefore takes `--profile PROFILE.json` for a universe plan; a universe plan without it, or a fixed plan with it,
  is `STUDY_ARGUMENTS_INVALID` (spec section 14).
- Needed books (spec section 14): every candidate's decisions d[j-1] and d[j-2], plus the coin held by each of its
  replayed paths, the two lag-1 runs (primary and double cost) and the lag-2 run. Each path is a
  `strategy._UniversePath` stepped over the frame the capture just recorded, decoded by the evaluator's own
  `_universe_view`, so "did the sell execute" (a usable book, and a fill above the lot and minimums) is the same code
  in capture and evaluator, never a second predicate. A sell deferred for any number of slots keeps its book request;
  a path the evaluator would fail is dropped, since that trial fails whatever is requested later. Why the spec's
  list (section 14, revised after review) has no d[j-3] and three held coins: at slot j a path trades only the coin it holds
  or, when flat, d[j-1] (lag 1) or d[j-2] (lag 2), and marks the coin it holds after that trade; the lag-2 buy of
  d[j-3] at slot j-1 is that path's held coin at j, or never filled, so d[j-3] adds no book the evaluator reads. The
  evaluator runs two lag-1 paths, and lot or minimum rounding can split them (the double-cost path keeps a remainder
  the primary sold), so each candidate has three held coins, not two. Without d[j-3] the set is at most
  3 x (2 + 3) + 1 = 16 (`_MAX_BOOKS`) by construction, so the spec's 16-book bound holds and no new event ends a
  trial; `STUDY_CAPTURE_BOOKS_OVER_LIMIT` stays as a guard that no plan within `STUDY_UNIVERSE_CANDIDATES_LIMIT`
  reaches, never a truncated request. In the Task 6 fixtures every slot asks for the same books as the list with
  d[j-3] would.
- New refusal codes: `QUOTE_MARKETS_INVALID`, `QUOTE_BOOK_LIST_REQUIRED`, `QUOTE_MARKET_MISSING`,
  `QUOTE_MARKET_DUPLICATED`; `TERMS_MARKETS_INVALID`, `TERMS_INSTRUMENT_LIST_REQUIRED`, `TERMS_INSTRUMENT_UNREQUESTED`,
  `TERMS_INSTRUMENT_MISSING`, `TERMS_INSTRUMENT_DUPLICATED`; `STRATEGY_UNIVERSE_CAPTURE_INVALID`,
  `STRATEGY_UNIVERSE_SNAPSHOT_NOT_IN_FORCE`, `STRATEGY_UNIVERSE_HELD_COIN_VANISHED`,
  `STRATEGY_UNIVERSE_MARK_UNAVAILABLE`, `STRATEGY_UNIVERSE_TERMINAL_BOOK_UNAVAILABLE`,
  `STRATEGY_UNIVERSE_BENCHMARK_UNAVAILABLE`; `STUDY_UNIVERSE_TOO_MANY_CANDIDATES`, `STUDY_PRIOR_ATTEMPTS_INVALID`,
  `STUDY_UNIVERSE_CAPTURE_SIZE`, `STUDY_CAPTURE_JSON_TOO_LARGE`, `STUDY_CAPTURE_DECISION_TOO_LATE`,
  `STUDY_CAPTURE_BOOKS_OVER_LIMIT`.
- Choices the spec leaves open: the selection rule is inferred from the template's evaluator revision; a universe
  plan keeps `StudyPlan.schema_version == 1`; `MarketSelection.symbol` of a universe plan is the protocol symbol
  `KRW-BTC` (the benchmark); `CaptureOutcome.archives` holds `UniverseArchive`s for a universe plan; the family check
  at `study.py:216` accepts a family that is a superset of the candidate ids for fixed plans too (spec wording); a day
  with several verified snapshot files uses the one with the earliest `(built_at, snapshot_sha256)`.
- Size bound, measured by running `_universe_capture_bound` and `universe_capture_json` as written in Task 6, with
  `_MAX_BOOKS = 16`, on a three-candidate plan: the worst-case frame line is 14,868 bytes (14,088 with the earlier
  ten books) and a decision line 191 bytes (192 from slot 1,000 on). `UNIVERSE_CAPTURE_LIMIT` (12 MiB, 12,582,912
  bytes) therefore admits about 835 slots, about 69.5 hours of 5-minute bars (832 with three 96-character study ids
  and a top-320 table). 577 slots (48 hours): 8,697,081 bytes (8.70 MB), fits. 865 slots (72 hours): 13,034,304
  bytes (13.03 MB), over the limit: the freeze check refuses a 72-hour universe study at 5-minute bars. The live
  coordinator's 72-hour `UNIVERSE_WINDOW_MAX` (PR 4e) is not changed by this plan; it bounds live sessions, not
  studies. 1,153 slots (96 hours): 17.37 MB, refused. The Task 6 size test's 577 frames built with `_frame` encode
  to 8,682,079 bytes against a bound of 8,697,081.
- Not planned: the one-request-per-market fallback. Spec section 14 makes it conditional on Upbit refusing batches,
  which is the section 17 measurement that has not been made; this plan sends one batch GET for books and one for
  ticks and records an unavailable batch as unavailable. If the measurement shows refusals, the fallback is a follow-up
  inside `_universe_source`.

---

### Task 0: Branch and upstream checks

**Files:**
- No file change.

**Interfaces:**
- Consumes: PR 1 (`FLAG_CLASSES`, `universe_top_n`, `verify_universe_snapshot`, `Universe`, `owner.universe_dir`),
  PR 2 (`orderbook_instruments`, `tickers`, `FlagRead`, `TickerRead`, `UniverseSlotSource`), PR 4b
  (`UNIVERSE_EVALUATOR_REVISION`, `_rule_terms(rules, universe_rule_sha256)`, omit-none fields, `ChooserState`,
  `ChooserSlot`, `choose`, the study selector sites), PR 4c (universe profiles require `time_in_force="ioc"`).
- Produces: the branch.

- [ ] **Step 1: Cut the branch**

```bash
git fetch origin
git switch -c claude/universe-pr5-study origin/main
git log --oneline -12
git status --short
```

Expected: the log shows the merges of PR 0 through PR 4e; `git status` lists only the untracked `docs/superpowers`
spec and plan files, which this plan never commits.

- [ ] **Step 2: Confirm the upstream names this plan builds on**

```bash
grep -n "^UNIVERSE_EVALUATOR_REVISION = \|^def _rule_terms(rules, universe_rule_sha256)\|omit_none" execution_launch/strategy.py
grep -n "^class ChooserState\|^class ChooserSlot\|^def choose" execution_launch/program.py
grep -c "universe_rule_sha256=profile.universe_rule_sha256" execution_launch/study.py
grep -n "^FLAG_CLASSES\|^def universe_top_n\|^def verify_universe_snapshot" core/compliance/rules.py
grep -n "^class Universe:" core/compliance/model.py
grep -n "^def universe_dir" core/compliance/owner.py
grep -n "^class FlagRead\|^class TickerRead\|^class UniverseSlotSource\|^_NO_FLAGS\|^_NO_TICKERS" execution_accounts/universe.py
grep -n "^def orderbook_instruments\|^def tickers" execution/upbit_inquiry.py
grep -n '"ioc"' execution_launch/profile.py
```

Expected: every grep prints at least one line, and the `grep -c` prints `2`. If any name is missing, stop and report
which one: this plan's code calls them as written.

- [ ] **Step 3: Baseline the suites this PR touches**

```bash
focus launch launch_study/
focus launch launch_strategy/
focus launch launch_shortened_study/
focus launch launch_instrument_refresh/
focus accounts accounts_quotes/
focus accounts accounts_universe/
focus control control_guards/
```

Expected: exit 0 for each. A FAIL row on the unmodified branch stops the plan: report it.

---

### Task 1: Batch book reader and per-market book parser

**Files:**
- Modify: `execution_accounts/quotes.py` (fd85850: imports 9-18, `_MAX_AGE` 25, `_params` 62-63, `parse_orderbook`
  123-178; locate by the quoted text)
- Test: `tests/accounts_quotes.py` (import line 11; append after the last line, 242 at fd85850)

**Interfaces:**
- Consumes: `execution.transport.request`, `inquiry_clock`, `Answer`; `SourceReceipt` (`collector.py`).
- Produces: `parse_orderbooks(receipt: SourceReceipt, symbols: Sequence[str], now: datetime) -> dict[str,
  OrderbookQuote | str]`; `read_orderbooks(symbols: Sequence[str], *, clock: Callable) -> SourceReceipt` (path
  `/v1/orderbook`, params `(("markets", "A,B,..."), ("level", "0"), ("count", "30"))`, scope
  `public-upbit-orderbook`); codes `QUOTE_MARKETS_INVALID` (not a list or tuple of 1 to 16 distinct `KRW-` symbols),
  `QUOTE_BOOK_LIST_REQUIRED`, `QUOTE_MARKET_MISSING`, `QUOTE_MARKET_DUPLICATED`. `parse_orderbook` is unchanged in
  behaviour.

- [ ] **Step 1: Write the failing tests**

In `tests/accounts_quotes.py`, replace the line:

```python
from execution_accounts.quotes import E1UpbitQuoteSource, QuoteError, parse_orderbook, to_runner_quote
```

with:

```python
from execution_accounts.quotes import (E1UpbitQuoteSource, OrderbookQuote, QuoteError, parse_orderbook,
                                       parse_orderbooks, read_orderbooks, to_runner_quote)
```

(If an upstream PR changed that import, keep its names and add `OrderbookQuote`, `parse_orderbooks` and
`read_orderbooks`.)

Append to the end of `tests/accounts_quotes.py`:

```python


BATCH = ("KRW-BTC", "KRW-ETH", "KRW-XRP")
BAD_MARKET_SETS = ((), ["KRW-BTC", "KRW-BTC"], ("KRW-btc",), ("KRW-KRW",), "KRW-BTC",
                   tuple(f"KRW-A{n}" for n in range(17)))


def book_row(market, **changes):
    return body()[0] | {"market": market} | changes


def batch_receipt(rows, symbols=BATCH, **changes):
    params = (("markets", ",".join(symbols)), ("level", "0"), ("count", "30"))
    return receipt(rows, **({"params": params} | changes))


def test_batch_books_apply_the_single_market_checks_per_market():
    stale = int(NOW.timestamp()) * 1000 - 10001
    books = parse_orderbooks(batch_receipt([book_row("KRW-BTC"), book_row("KRW-ETH", timestamp=stale)]), BATCH, NOW)
    assert type(books["KRW-BTC"]) is OrderbookQuote and books["KRW-BTC"].bid == 99
    assert books["KRW-ETH"] == "QUOTE_BOOK_STALE_OR_FUTURE" and books["KRW-XRP"] == "QUOTE_MARKET_MISSING"
    crossed = book_row("KRW-ETH", orderbook_units=[dict(ask_price=99, bid_price=101, ask_size=2, bid_size=3)])
    books = parse_orderbooks(batch_receipt([book_row("KRW-BTC"), book_row("KRW-BTC"), crossed]), BATCH, NOW)
    assert books == {"KRW-BTC": "QUOTE_MARKET_DUPLICATED", "KRW-ETH": "QUOTE_LOCKED_OR_CROSSED_BOOK",
                     "KRW-XRP": "QUOTE_MARKET_MISSING"}
    assert parse_orderbooks(receipt(), ("KRW-BTC",), NOW) == {"KRW-BTC": parse()}


def test_batch_book_receipts_refuse_as_a_whole():
    rows = [book_row("KRW-BTC")]
    for changes in ({"path": "/v1/orderbooks"}, {"account_scope": "public-upbit-terms"}, {"params": PARAMS}):
        refusal(lambda: parse_orderbooks(batch_receipt(rows, **changes), BATCH, NOW), "QUOTE_RECEIPT_SCOPE_MISMATCH")
    refusal(lambda: parse_orderbooks(batch_receipt(rows, BATCH[::-1]), BATCH, NOW), "QUOTE_RECEIPT_SCOPE_MISMATCH")
    refusal(lambda: parse_orderbooks(batch_receipt(rows, sha256="a" * 64), BATCH, NOW), "QUOTE_RECEIPT_INVALID")
    refusal(lambda: parse_orderbooks(batch_receipt(rows), BATCH, NOW + timedelta(seconds=11)),
            "QUOTE_RECEIPT_STALE_OR_FUTURE")
    for value in ({"market": "KRW-BTC"}, [None]):
        refusal(lambda: parse_orderbooks(batch_receipt(value), BATCH, NOW), "QUOTE_BOOK_LIST_REQUIRED")
    refusal(lambda: parse_orderbooks(batch_receipt(rows + [book_row("KRW-SOL")]), BATCH, NOW), "QUOTE_MARKET_MISMATCH")
    for symbols in BAD_MARKET_SETS:
        refusal(lambda: parse_orderbooks(batch_receipt(rows), symbols, NOW), "QUOTE_MARKETS_INVALID")
        refusal(lambda: read_orderbooks(symbols, clock=lambda: NOW), "QUOTE_MARKETS_INVALID")


def test_batch_book_read_is_one_public_get_under_the_clock():
    raw = batch_receipt([book_row("KRW-BTC"), book_row("KRW-ETH")], ("KRW-BTC", "KRW-ETH")).raw_body
    with patch.object(keys, "read", side_effect=AssertionError("credential read forbidden")) as key_read, \
            patch.object(transport, "_clock", lambda: NOW - timedelta(days=1)), \
            F.serve({("GET", "/v1/orderbook"): lambda call: (200, {"Date": F.DATE_HEADER}, raw)}) as calls:
        read = read_orderbooks(("KRW-BTC", "KRW-ETH"), clock=lambda: NOW)
    assert not key_read.called and len(calls) == 1 and "Authorization" not in calls[0]["headers"]
    assert calls[0]["url"] == "https://api.upbit.com/v1/orderbook?markets=KRW-BTC,KRW-ETH&level=0&count=30"
    assert read.raw_body == raw and read.received_at == NOW and read.server_time == NOW
    books = parse_orderbooks(read, ("KRW-BTC", "KRW-ETH"), NOW)
    assert books["KRW-BTC"].bid == 99 and books["KRW-ETH"].ask == 101
    with patch("execution_accounts.quotes.request", side_effect=RuntimeError("synthetic")):
        refusal(lambda: read_orderbooks(("KRW-BTC",), clock=lambda: NOW), "QUOTE_PUBLIC_INQUIRY_FAILED")
    refusal(lambda: read_orderbooks(("KRW-BTC",), clock=None), "QUOTE_CLOCK_REQUIRED")
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
focus accounts accounts_quotes/
```

Expected: exit 1; the row `accounts_quotes/import` FAILs with `ImportError: cannot import name 'parse_orderbooks'`.

- [ ] **Step 3: Implement**

In `execution_accounts/quotes.py`, replace the line `from contextlib import ExitStack` with:

```python
from collections.abc import Sequence
from contextlib import ExitStack
```

Replace the line `_MAX_AGE = timedelta(seconds=10)` with:

```python
_MAX_AGE = timedelta(seconds=10)
_MAX_MARKETS = 16                       # spec section 14: 3 candidates x (3 decisions + 2 held coins) + KRW-BTC
```

Replace the two lines of `_params`:

```python
def _params(symbol):
    return (("markets", _symbol(symbol)), ("level", "0"), ("count", "30"))
```

with:

```python
def _params(symbol):
    return (("markets", _symbol(symbol)), ("level", "0"), ("count", "30"))


def _markets(symbols):
    _require(type(symbols) in (list, tuple) and 1 <= len(symbols) <= _MAX_MARKETS
             and all(type(s) is str and _SYMBOL.fullmatch(s) is not None and s != "KRW-KRW" for s in symbols)
             and len(set(symbols)) == len(symbols), "QUOTE_MARKETS_INVALID")
    return tuple(symbols)


def _batch_params(symbols):
    return (("markets", ",".join(symbols)), ("level", "0"), ("count", "30"))
```

Replace the whole `parse_orderbook` function (from `def parse_orderbook(receipt: SourceReceipt, *, symbol: str, now:
datetime) -> OrderbookQuote:` through `        source_sha256=receipt.sha256, receipt=receipt)`) with:

```python
def _decoded(receipt, params, now):
    """Receipt checks shared by the single and batch parsers: exact path, parameters and scope, the 10-second
    receipt age, the server clock, the size and the decoding."""
    _require(type(receipt) is SourceReceipt and receipt.path == "/v1/orderbook"
             and receipt.params == params and type(receipt.params) is tuple
             and receipt.account_scope == _PUBLIC_SCOPE, "QUOTE_RECEIPT_SCOPE_MISMATCH")
    received = _instant(receipt.received_at); server = _instant(receipt.server_time)
    _require(timedelta(0) <= now-received <= _MAX_AGE, "QUOTE_RECEIPT_STALE_OR_FUTURE")
    _require(abs(received-server) <= timedelta(seconds=60), "QUOTE_SERVER_CLOCK_MISMATCH")
    _require(type(receipt.raw_body) is bytes and 0 < len(receipt.raw_body) <= _MAX_BYTES,
             "QUOTE_BODY_TOO_LARGE_OR_EMPTY")
    try:
        body = receipt.decode()
    except (ValueError, TypeError, ArithmeticError):
        raise QuoteError("QUOTE_RECEIPT_INVALID") from None
    return body, received, server


def _book(row, symbol, receipt, received, server, now):
    """One market's row: market, native level, the 10-second book time, depth order and totals."""
    _require(row.get("market") == symbol, "QUOTE_MARKET_MISMATCH")
    level = _amount(row.get("level"), positive=False)
    _require(level == 0, "QUOTE_AGGREGATED_DEPTH_REFUSED")
    stamp = row.get("timestamp")
    _require(type(stamp) is int and 0 < stamp <= 2**63-1, "QUOTE_TIMESTAMP_INVALID")
    try:
        asof = _EPOCH + timedelta(milliseconds=stamp)
    except OverflowError:
        raise QuoteError("QUOTE_TIMESTAMP_INVALID") from None
    _require(timedelta(0) <= received-asof <= _MAX_AGE and now-asof <= _MAX_AGE,
             "QUOTE_BOOK_STALE_OR_FUTURE")
    units = row.get("orderbook_units")
    _require(type(units) is list and 1 <= len(units) <= 30,
             "QUOTE_DEPTH_EMPTY_OR_OVERSIZED")
    levels = []
    for unit in units:
        _require(type(unit) is dict, "QUOTE_LEVEL_INVALID")
        item = BookLevel(ask=_amount(unit.get("ask_price")), bid=_amount(unit.get("bid_price")),
            ask_size=_amount(unit.get("ask_size")), bid_size=_amount(unit.get("bid_size")))
        _require(item.bid < item.ask, "QUOTE_LOCKED_OR_CROSSED_BOOK")
        _require(not levels or item.ask > levels[-1].ask and item.bid < levels[-1].bid,
                 "QUOTE_DEPTH_NOT_STRICTLY_ORDERED")
        levels.append(item)
    total_ask = _amount(row.get("total_ask_size")); total_bid = _amount(row.get("total_bid_size"))
    with localcontext() as numeric:
        numeric.prec = 256
        numeric.traps[Inexact] = True
        _require(total_ask >= sum((v.ask_size for v in levels), Decimal(0))
                 and total_bid >= sum((v.bid_size for v in levels), Decimal(0)),
                 "QUOTE_DEPTH_TOTAL_CONTRADICTION")
    return OrderbookQuote(symbol=symbol, asof=asof, received_at=received, server_time=server,
        levels=tuple(levels), total_ask_size=total_ask, total_bid_size=total_bid,
        source_sha256=receipt.sha256, receipt=receipt)


def parse_orderbook(receipt: SourceReceipt, *, symbol: str, now: datetime) -> OrderbookQuote:
    """Validate exact bytes, selected market, native depth, clocks and spread.

    Up to 30 displayed price levels are retained. Totals may include depth not
    displayed; this does not claim an entire venue book or fill availability.
    The strict local freshness policy permits no future-dated quote or receipt.
    """
    _symbol(symbol); now = _instant(now)
    body, received, server = _decoded(receipt, _params(symbol), now)
    _require(type(body) is list and len(body) == 1 and type(body[0]) is dict,
             "QUOTE_SINGLE_BOOK_REQUIRED")
    return _book(body[0], symbol, receipt, received, server, now)


def parse_orderbooks(receipt: SourceReceipt, symbols: Sequence[str], now: datetime) -> dict[str, OrderbookQuote | str]:
    """Each requested market's book from one batch read, or that market's refusal code (spec section 14).

    The receipt checks apply to the whole read and raise. Each row then gets parse_orderbook's single-market checks
    on its own, the 10-second book rule included, so one stale, crossed, missing or repeated market is a code string
    and never hides the others. A row naming a market that was not requested refuses the whole read.
    """
    symbols = _markets(symbols); now = _instant(now)
    body, received, server = _decoded(receipt, _batch_params(symbols), now)
    _require(type(body) is list and all(type(row) is dict for row in body), "QUOTE_BOOK_LIST_REQUIRED")
    _require(all(row.get("market") in symbols for row in body), "QUOTE_MARKET_MISMATCH")
    books = {}
    for symbol in symbols:
        rows = [row for row in body if row.get("market") == symbol]
        if len(rows) != 1:
            books[symbol] = "QUOTE_MARKET_MISSING" if not rows else "QUOTE_MARKET_DUPLICATED"
            continue
        try:
            books[symbol] = _book(rows[0], symbol, receipt, received, server, now)
        except QuoteError as exc:
            books[symbol] = str(exc)
    return books


def read_orderbooks(symbols: Sequence[str], *, clock: Callable) -> SourceReceipt:
    """One public batch GET of up to sixteen distinct KRW books under an explicit clock, for the study capture.

    No route and no keys. The caller parses the receipt with parse_orderbooks; this returns it unadmitted.
    """
    symbols = _markets(symbols)
    _require(callable(clock), "QUOTE_CLOCK_REQUIRED")
    params = _batch_params(symbols)
    try:
        before = _instant(clock())
        with inquiry_clock(clock):
            answer = request("upbit", "GET", "/v1/orderbook", params)
        after = _instant(clock())
    except Exception:
        raise QuoteError("QUOTE_PUBLIC_INQUIRY_FAILED") from None
    _require(type(answer) is Answer and answer.server_utc is not None,
             "QUOTE_SERVER_TIME_REQUIRED")
    received = _instant(answer.received_utc)
    _require(before <= received <= after, "QUOTE_RECEIPT_OUTSIDE_REQUEST")
    return SourceReceipt(path="/v1/orderbook", params=params, account_scope=_PUBLIC_SCOPE,
        received_at=received, server_time=answer.server_utc,
        raw_body=answer.raw_body, sha256=answer.sha256)
```

- [ ] **Step 4: Run the tests to verify they pass**

```bash
focus accounts accounts_quotes/
focus accounts accounts_guards/
focus launch launch_quote_diagnostics/
```

Expected: exit 0 for each; the three new `accounts_quotes/test_batch_book...` rows PASS and every existing
`accounts_quotes` row still PASSes (the single-market parser behaves as before).

- [ ] **Step 5: Commit**

```bash
git add execution_accounts/quotes.py tests/accounts_quotes.py
diff <(git diff --cached --stat) <(git diff --cached --stat --ignore-cr-at-eol)
git commit -m "$(cat <<'EOF'
feat(accounts): batch public book read and per-market book parser

read_orderbooks sends one keyless GET for up to sixteen KRW books under
an explicit clock; parse_orderbooks checks the receipt as a whole and then
applies parse_orderbook's single-market checks (the 10-second book rule
included) to each market on its own, returning the book or that market's
refusal code (universe spec section 14). parse_orderbook is unchanged in
behaviour; it now shares the receipt and row checks.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
)"
```

Expected: the `diff` prints nothing; the commit succeeds.

---

### Task 2: Batch tick reader and per-market instrument parser

**Files:**
- Modify: `execution_accounts/instrument_terms.py` (imports 10-25, `_MAX_BODY` 32; append at the end of the file)
- Modify: `tests/renewal_boundaries.py` (the `"execution_accounts/instrument_terms.py"` line of `INITIALIZERS`, line 28
  at fd85850)
- Test: `tests/launch_instrument_refresh.py` (imports at the top; append at the end)

**Interfaces:**
- Consumes: `execution.upbit_inquiry.orderbook_instruments(markets) -> Answer` (PR 2) and `TERMS_INSTRUMENTS_PATH` (existing, `execution/upbit_inquiry.py:24`);
  the existing `_receipt`, `_number`, `_time`, `_require`, `_SYMBOL`, `_PUBLIC_SCOPE`.
- Produces: `parse_instruments(receipt: SourceReceipt, symbols: Sequence[str]) -> dict[str, Decimal | str]`;
  `read_instruments(symbols: Sequence[str], *, clock: Callable) -> SourceReceipt` (path `TERMS_INSTRUMENTS_PATH`,
  params `(("markets", "A,B,..."),)`, scope `public-upbit-terms`); codes `TERMS_MARKETS_INVALID`,
  `TERMS_INSTRUMENT_LIST_REQUIRED`, `TERMS_INSTRUMENT_UNREQUESTED`, `TERMS_INSTRUMENT_MISSING`,
  `TERMS_INSTRUMENT_DUPLICATED`. `E1UpbitTermsSource` and every reviewed body are unchanged.

- [ ] **Step 1: Write the failing tests**

In `tests/launch_instrument_refresh.py`, replace the line `from execution import transport, upbit_inquiry` with
`from execution import keys, transport, upbit_inquiry`, and replace the line
`from execution_accounts import instrument_terms as T` with:

```python
from execution_accounts import instrument_terms as T
from execution_accounts.collector import SourceReceipt
```

and add `from tests import execution_fixtures as EF` directly before the line
`from tests.launch_profile import fixture_profile`.

Append to the end of `tests/launch_instrument_refresh.py`:

```python


TERMS_BATCH = ("KRW-AAA", "KRW-BBB", "KRW-BTC", "KRW-CCC", "KRW-DDD")


def instrument(market, **changes):
    return {"market": market, "tick_size": "1", "quote_currency": "KRW", "supported_levels": ["0", "1000"]} | changes


def instruments_receipt(rows, symbols=TERMS_BATCH, **changes):
    raw = json.dumps(rows).encode()
    return SourceReceipt(**(dict(path=upbit_inquiry.TERMS_INSTRUMENTS_PATH, params=(("markets", ",".join(symbols)),),
        account_scope="public-upbit-terms", received_at=NOW, server_time=NOW, raw_body=raw,
        sha256=hashlib.sha256(raw).hexdigest()) | changes))


def test_batch_instruments_apply_the_single_instrument_checks_per_market():
    rows = [instrument("KRW-AAA", tick_size="0.001"), instrument("KRW-BBB", quote_currency="BTC"),
            instrument("KRW-BTC", supported_levels=["1000"]), instrument("KRW-CCC", tick_size="0")]
    assert T.parse_instruments(instruments_receipt(rows), TERMS_BATCH) == {
        "KRW-AAA": D("0.001"), "KRW-BBB": "TERMS_CURRENCY_MISMATCH", "KRW-BTC": "TERMS_NATIVE_BOOK_UNSUPPORTED",
        "KRW-CCC": "TERMS_NUMBER_INVALID", "KRW-DDD": "TERMS_INSTRUMENT_MISSING"}
    pair = ("KRW-AAA", "KRW-BTC")
    assert T.parse_instruments(instruments_receipt([instrument("KRW-AAA")] * 2, pair), pair) == {
        "KRW-AAA": "TERMS_INSTRUMENT_DUPLICATED", "KRW-BTC": "TERMS_INSTRUMENT_MISSING"}
    refused(lambda: T.parse_instruments(instruments_receipt(rows + [instrument("KRW-EEE")]), TERMS_BATCH),
            "TERMS_INSTRUMENT_UNREQUESTED")
    refused(lambda: T.parse_instruments(instruments_receipt({"market": "KRW-AAA"}), TERMS_BATCH),
            "TERMS_INSTRUMENT_LIST_REQUIRED")
    for wrong in (instruments_receipt(rows, TERMS_BATCH[::-1]), instruments_receipt(rows, account_scope="test-scope"),
                  object()):
        refused(lambda: T.parse_instruments(wrong, TERMS_BATCH), "TERMS_RECEIPT_SCOPE_MISMATCH")
    refused(lambda: T.parse_instruments(instruments_receipt(rows, server_time=NOW + timedelta(seconds=61)),
                                        TERMS_BATCH), "TERMS_SERVER_CLOCK_MISMATCH")
    for symbols in ((), ["KRW-AAA", "KRW-AAA"], ("KRW-aaa",), ("KRW-KRW",), "KRW-AAA",
                    tuple(f"KRW-A{n}" for n in range(17))):
        refused(lambda: T.parse_instruments(instruments_receipt(rows), symbols), "TERMS_MARKETS_INVALID")
        refused(lambda: T.read_instruments(symbols, clock=lambda: NOW), "TERMS_MARKETS_INVALID")


def test_batch_instrument_read_is_one_public_get_under_the_clock():
    raw = json.dumps([instrument("KRW-BTC"), instrument("KRW-ETH")]).encode()
    route = {("GET", upbit_inquiry.TERMS_INSTRUMENTS_PATH):
             lambda call: (200, {"Date": format_datetime(NOW, usegmt=True)}, raw)}
    with patch.object(keys, "read", side_effect=AssertionError("credential read forbidden")) as key_read, \
            EF.serve(route) as calls:
        read = T.read_instruments(("KRW-BTC", "KRW-ETH"), clock=lambda: NOW)
    assert not key_read.called and len(calls) == 1 and "Authorization" not in calls[0]["headers"]
    assert calls[0]["url"] == "https://api.upbit.com/v1/orderbook/instruments?markets=KRW-BTC,KRW-ETH"
    assert read.raw_body == raw and read.params == (("markets", "KRW-BTC,KRW-ETH"),)
    assert T.parse_instruments(read, ("KRW-BTC", "KRW-ETH")) == {"KRW-BTC": D("1"), "KRW-ETH": D("1")}
    with patch.object(T, "orderbook_instruments", side_effect=RuntimeError("synthetic")):
        refused(lambda: T.read_instruments(("KRW-BTC",), clock=lambda: NOW), "TERMS_INQUIRY_FAILED")
    refused(lambda: T.read_instruments(("KRW-BTC",), clock=None), "TERMS_CLOCK_REQUIRED")
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
focus launch launch_instrument_refresh/test_batch_instrument
```

Expected: exit 1; both rows FAIL with `AttributeError: module 'execution_accounts.instrument_terms' has no attribute
'parse_instruments'`.

- [ ] **Step 3: Implement**

In `execution_accounts/instrument_terms.py`, replace the line `from contextlib import ExitStack` with:

```python
from collections.abc import Sequence
from contextlib import ExitStack
```

Add one new line directly after the line that starts `from execution.upbit_inquiry import`:

```python
from execution.upbit_inquiry import orderbook_instruments
```

Replace the line `_MAX_BODY = 131072` with:

```python
_MAX_BODY = 131072
_MAX_INSTRUMENTS = 16                   # spec section 14: the study asks at most sixteen markets per slot
```

Append to the end of the file (two blank lines before the first new line):

```python
def _markets(symbols):
    _require(type(symbols) in (list, tuple) and 1 <= len(symbols) <= _MAX_INSTRUMENTS
             and all(type(s) is str and _SYMBOL.fullmatch(s) is not None and s != "KRW-KRW" for s in symbols)
             and len(set(symbols)) == len(symbols), "TERMS_MARKETS_INVALID")
    return tuple(symbols)


def _instrument_tick(instrument):
    """The single-instrument checks of parse_term_receipts for one row: KRW quote, native level "0", a tick."""
    _require(instrument.get("quote_currency") == "KRW", "TERMS_CURRENCY_MISMATCH")
    levels = instrument.get("supported_levels")
    _require(type(levels) is list and 1 <= len(levels) <= 64
             and all(type(v) is str for v in levels) and "0" in levels,
             "TERMS_NATIVE_BOOK_UNSUPPORTED")
    return _number(instrument.get("tick_size"), positive=True)


def parse_instruments(receipt: SourceReceipt, symbols: Sequence[str]) -> dict[str, Decimal | str]:
    """Each requested market's tick from one public batch read, or that market's refusal code (spec section 14).

    The receipt checks (exact path, parameters and scope, server clock, size, decoding) apply to the whole read and
    raise; a row naming a market that was not requested refuses the whole read. The result is a tick for paper
    rounding, never InstrumentRules: lot, minimums, fees and the authority stay with E1UpbitTermsSource.
    """
    symbols = _markets(symbols)
    _require(type(receipt) is SourceReceipt, "TERMS_RECEIPT_SCOPE_MISMATCH")
    received = _time(receipt.received_at)
    body = _receipt(receipt, path=TERMS_INSTRUMENTS_PATH, params=(("markets", ",".join(symbols)),),
                    scope=_PUBLIC_SCOPE, before=received, checked=received)
    _require(type(body) is list and all(type(row) is dict for row in body), "TERMS_INSTRUMENT_LIST_REQUIRED")
    _require(all(row.get("market") in symbols for row in body), "TERMS_INSTRUMENT_UNREQUESTED")
    ticks = {}
    for symbol in symbols:
        rows = [row for row in body if row.get("market") == symbol]
        if len(rows) != 1:
            ticks[symbol] = "TERMS_INSTRUMENT_MISSING" if not rows else "TERMS_INSTRUMENT_DUPLICATED"
            continue
        try:
            ticks[symbol] = _instrument_tick(rows[0])
        except TermsError as exc:
            ticks[symbol] = str(exc)
    return ticks


def read_instruments(symbols: Sequence[str], *, clock: Callable) -> SourceReceipt:
    """One public batch read of up to sixteen distinct KRW instruments under an explicit clock, for the study
    capture.

    No account key, route, authority or issued observation; the caller parses the receipt with parse_instruments.
    """
    symbols = _markets(symbols)
    _require(callable(clock), "TERMS_CLOCK_REQUIRED")
    try:
        before = _time(clock())
        with inquiry_clock(clock):
            answer = orderbook_instruments(symbols)
        after = _time(clock())
    except Exception:
        raise TermsError("TERMS_INQUIRY_FAILED") from None
    _require(type(answer) is Answer and answer.server_utc is not None, "TERMS_SERVER_TIME_REQUIRED")
    received = _time(answer.received_utc)
    _require(before <= received <= after, "TERMS_RECEIPT_OUTSIDE_REQUEST")
    return SourceReceipt(path=TERMS_INSTRUMENTS_PATH, params=(("markets", ",".join(symbols)),),
        account_scope=_PUBLIC_SCOPE, received_at=received, server_time=answer.server_utc,
        raw_body=answer.raw_body, sha256=answer.sha256)
```

- [ ] **Step 4: Run the tests; review and update the renewal pin**

```bash
focus launch launch_instrument_refresh/
focus accounts accounts_guards/
focus control control_guards/test_renewal
```

Expected: the first two exit 0 (both new rows PASS). The third exits 1 with
`execution_accounts/instrument_terms.py: initialization surface changed` and nothing else: the reviewed bodies in
`CALLS` are untouched, only the imports, the constant and the new definitions changed.

Review that the surface change is exactly the two imports, `_MAX_INSTRUMENTS` and the four new functions:

```bash
git diff -- execution_accounts/instrument_terms.py
"$PY" -X utf8 -c "from pathlib import Path; from tests.renewal_boundaries import _surface; print(_surface(Path('execution_accounts/instrument_terms.py').read_text(encoding='utf-8')))"
```

In `tests/renewal_boundaries.py`, replace the 64-hex value on the line that starts
`    "execution_accounts/instrument_terms.py": "` with the printed value (Edit tool; keep the line's quotes and
trailing comma). Then:

```bash
focus control control_guards/
```

Expected: exit 0 (both renewal tests PASS, including the negative controls).

- [ ] **Step 5: Commit**

```bash
git add execution_accounts/instrument_terms.py tests/launch_instrument_refresh.py tests/renewal_boundaries.py
diff <(git diff --cached --stat) <(git diff --cached --stat --ignore-cr-at-eol)
git commit -m "$(cat <<'EOF'
feat(accounts): batch public tick read and per-market instrument parser

read_instruments sends one keyless instruments GET for up to sixteen KRW
markets under an explicit clock; parse_instruments checks the receipt as a
whole and applies the single-instrument checks (KRW quote, native level 0,
positive tick) to each market on its own, returning a tick or that market's
refusal code (universe spec section 14). It never issues InstrumentRules.
The renewal initialization pin of instrument_terms.py is updated after
review; every reviewed body is unchanged.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
)"
```

Expected: the `diff` prints nothing; the commit succeeds.

---

### Task 3: Slot reads keep the raw answer

**Files:**
- Modify: `execution_accounts/universe.py` (`FlagRead`, `TickerRead`, `UniverseSlotSource.read_flags`,
  `UniverseSlotSource.read_tickers`; created by PR 2, locate by the quoted text)
- Test: `tests/accounts_universe.py` (append at the end)

**Interfaces:**
- Consumes: PR 2's `FlagRead`, `TickerRead`, `_NO_FLAGS`, `_NO_TICKERS`, `UniverseSlotSource`.
- Produces: `FlagRead.answer` and `TickerRead.answer`: `Answer | None = field(default=None, repr=False,
  compare=False)`, the last field. An ok read carries its `Answer`; a failed read carries the `Answer` when one came
  back (a body that did not parse) and `None` when the request itself failed; `_NO_FLAGS.answer` and
  `_NO_TICKERS.answer` are `None`. Every existing field and equality is unchanged.

- [ ] **Step 1: Write the failing test**

Append to the end of `tests/accounts_universe.py`:

```python


def test_slot_reads_keep_the_raw_answer_for_the_study_receipts():
    ticker_raw = json.dumps([ticker("KRW-BTC", 101)]).encode("utf-8")
    source = U.UniverseSlotSource(clock=lambda: BUILT)
    with F.serve({("GET", "/v1/market/all"): answered(MARKET_ALL_RAW),
                  ("GET", "/v1/ticker"): answered(ticker_raw)}):
        flags, prices = source.read_flags(), source.read_tickers(("KRW-BTC",))
    assert flags.answer.raw_body == MARKET_ALL_RAW and flags.answer.received_utc == BUILT
    assert prices.answer.raw_body == ticker_raw and prices.answer.received_utc == BUILT
    assert "answer" not in repr(flags) and "answer" not in repr(prices)
    assert flags == U.FlagRead(ok=True, received_at=flags.received_at, sha256=flags.sha256, flags=flags.flags)
    with F.serve({("GET", "/v1/market/all"): answered(b'{"market": "KRW-BTC"}')}):
        bad = source.read_flags()
    assert unavailable(bad) and bad.answer.raw_body == b'{"market": "KRW-BTC"}'
    error = lambda call: (500, {"Date": BUILT_HEADER}, b'{"error":{"name":"server_error"}}')
    with F.serve({("GET", "/v1/ticker"): error}):
        failed = source.read_tickers(["KRW-BTC"])
    assert unavailable(failed) and failed.answer is None
    assert U._NO_FLAGS.answer is None and U._NO_TICKERS.answer is None
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
focus accounts accounts_universe/test_slot_reads_keep
```

Expected: exit 1; the row FAILs with `AttributeError: 'FlagRead' object has no attribute 'answer'`.

- [ ] **Step 3: Implement**

In `execution_accounts/universe.py`, in `class FlagRead`, replace the field line `    flags: Mapping[str, str]` with:

```python
    flags: Mapping[str, str]
    answer: Answer | None = field(default=None, repr=False, compare=False)   # raw body for the study receipts
```

In `class TickerRead`, replace the field line `    prices: Mapping[str, tuple[Decimal, datetime]]` with:

```python
    prices: Mapping[str, tuple[Decimal, datetime]]
    answer: Answer | None = field(default=None, repr=False, compare=False)   # raw body for the study receipts
```

In `UniverseSlotSource.read_flags`, replace the body from `        try:` through
`        return FlagRead(ok=True, received_at=answer.received_utc, sha256=answer.sha256, flags=flags)` with:

```python
        answer = None
        try:
            with inquiry_clock(self.clock):
                answer = market_all()
            _require(type(answer) is Answer and 0 < len(answer.raw_body) <= MAX_MARKET_ALL_BODY,
                     "UNIVERSE_BODY_EMPTY_OR_OVERSIZED")
            flags = MappingProxyType(dict(rules.market_flags(answer.raw_body)))
        except Exception:
            if type(answer) is not Answer:
                return _NO_FLAGS
            return FlagRead(ok=False, received_at=None, sha256=None, flags=MappingProxyType({}), answer=answer)
        return FlagRead(ok=True, received_at=answer.received_utc, sha256=answer.sha256, flags=flags, answer=answer)
```

In `UniverseSlotSource.read_tickers`, replace the body from `        try:` through
`        return TickerRead(ok=True, received_at=answer.received_utc, sha256=answer.sha256, prices=prices)` with:

```python
        answer = None
        try:
            with inquiry_clock(self.clock):
                answer = tickers(markets)
            _require(type(answer) is Answer and 0 < len(answer.raw_body) <= MAX_TICKER_BODY,
                     "UNIVERSE_BODY_EMPTY_OR_OVERSIZED")
            prices = MappingProxyType(_ticker_prices(answer.raw_body, markets))
        except Exception:
            if type(answer) is not Answer:
                return _NO_TICKERS
            return TickerRead(ok=False, received_at=None, sha256=None, prices=MappingProxyType({}), answer=answer)
        return TickerRead(ok=True, received_at=answer.received_utc, sha256=answer.sha256, prices=prices,
                          answer=answer)
```

(If PR 2 landed these bodies with different wording, keep its checks and change only: `answer = None` before the
`try`, the `except` branch, and `answer=answer` on the ok result. No `replace(...)` call: `tests/accounts_guards.py`
forbids it in `execution_accounts`.)

- [ ] **Step 4: Run the tests to verify they pass**

```bash
focus accounts accounts_universe/
focus accounts accounts_guards/
```

Expected: exit 0 for both; every earlier `accounts_universe` row still PASSes.

- [ ] **Step 5: Commit**

```bash
git add execution_accounts/universe.py tests/accounts_universe.py
diff <(git diff --cached --stat) <(git diff --cached --stat --ignore-cr-at-eol)
git commit -m "$(cat <<'EOF'
feat(accounts): flag and ticker slot reads keep their raw answer

FlagRead and TickerRead gain answer (last field, not in repr or equality)
so the universe study capture can put the raw market/all and ticker bodies
in its uncapped receipts sink (universe spec section 14). A read whose body
did not parse keeps its answer; a failed request still returns the shared
unavailable value.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
)"
```

Expected: the `diff` prints nothing; the commit succeeds.

---

### Task 4: Study rule, feasibility, family accounting and the candidate cap

**Files:**
- Modify: `execution_launch/study.py` (CRLF; fd85850 lines 29, 52-54, 58-61, 69, 170-226, 229-267, 350-361,
  511-518)
- Modify: `tests/launch_acceptance.py` (`MODULES`, lines 9-15 at fd85850)
- Create: `tests/launch_universe_study.py`

**Interfaces:**
- Consumes: `UNIVERSE_EVALUATOR_REVISION` (PR 4b), `ProgramSpec` universe fields (PR 4b), `LaunchProfile` and
  `ForwardProtocol.universe_rule_sha256` (PR 4b).
- Produces: `UNIVERSE_SELECTION_RULE = "upbit-krw-universe-top1-v1"`, `STUDY_UNIVERSE_CANDIDATES_LIMIT = 3`,
  `UNIVERSE_CAPTURE_LIMIT = 12 * 1024 * 1024`; `_room(returns, program) -> int`; `build_study_plan(profile, programs,
  *, template, plan_id, asset, risk_group, registry=(), prior_attempts=())`; `_draft(raw)` returns names with
  `prior_attempts` (a tuple, empty by default); codes `STUDY_UNIVERSE_TOO_MANY_CANDIDATES`,
  `STUDY_PRIOR_ATTEMPTS_INVALID`; `CAPTURE_FILES` with the three new files; `run_capture` refuses a universe plan
  (`STUDY_PLAN_SCHEMA_INVALID`).

- [ ] **Step 1: Write the failing tests**

Create `tests/launch_universe_study.py` (LF) with:

```python
"""Universe study over invented 2031 data: scripted public reads on a one-cell clock, list sinks, temporary
directories and a stubbed snapshot verifier. Nothing here fetches, signs, arms, publishes, reads a credential or
touches a real home."""
from __future__ import annotations

import base64
from contextlib import ExitStack
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from functools import lru_cache
import hashlib
import json
import os
from pathlib import Path
import tempfile
from types import MappingProxyType, SimpleNamespace
from unittest.mock import patch

from core.compliance.model import Universe
from core.compliance.rules import FLAG_CLASSES
from execution.upbit_inquiry import TERMS_INSTRUMENTS_PATH
from execution_accounts import universe as U
from execution_accounts.collector import SourceReceipt
from execution_accounts.quotes import ORDERBOOK_PATH, QuoteError
from execution_launch import strategy as T, study as S
from execution_launch.profile import profile_body
from execution_launch.program import ProgramSpec, program_json
from execution_launch.strategy import UNIVERSE_EVALUATOR_REVISION, _plain, protocol_json
from tests import launch_study as L

D = Decimal
RULE = "c" * 64
AAA, BBB, BTC, CCC = "KRW-AAA", "KRW-BBB", "KRW-BTC", "KRW-CCC"
START, BAR = L.START, L.BAR


# -- plan fixtures -----------------------------------------------------------------------------------------------

def rotation(strategy_id, *, lookback=1, hold=2, margin="0.05", n=2):
    return ProgramSpec(schema_version=2, strategy_id=strategy_id, kind="universe_top1_momentum", fast_window=0,
                       slow_window=0, exposure_fraction=D("1"), lookback_slots=lookback, min_hold_slots=hold,
                       switch_margin=D(margin), max_candidates=n, universe_rule_sha256=RULE)


ROTATION = rotation("fixture-rotation-a")


def uprofile(**changes):
    return L.profile(universe_rule_sha256=RULE, time_in_force="ioc", **changes)


def utemplate(observations=60, **changes):
    return L.template(observations, evaluator_revision=UNIVERSE_EVALUATOR_REVISION, universe_rule_sha256=RULE,
                      study_id="fixture-universe-study", **changes)


def uplan(observations=60, programs=(ROTATION,), prior_attempts=(), **changes):
    return S.build_study_plan(uprofile(), programs, template=utemplate(observations, **changes),
                              plan_id="fixture-universe-plan-2031", asset="KRW-UNIVERSE", risk_group="crypto-krw",
                              prior_attempts=prior_attempts)


# -- plan rules ----------------------------------------------------------------------------------------------------

def test_universe_feasibility_uses_warmup_and_hold_slots():
    assert S._room(60, L.C) == 28 and S._room(60, ROTATION) == 30
    p = uplan()
    assert p.selection_rule == S.UNIVERSE_SELECTION_RULE == "upbit-krw-universe-top1-v1"
    assert p.candidates[0].protocol.family_members == (ROTATION.strategy_id,)      # one member per rotation
    assert S.validate_study_plan(p) == T.evidence_digest(p)
    uplan(programs=(rotation("fixture-rotation-h3", hold=3),))                      # 60 // 3 = 20 trips
    L.refused(lambda: uplan(programs=(rotation("fixture-rotation-h4", hold=4),)), "STUDY_ROUNDTRIPS_INFEASIBLE")
    uplan(programs=(rotation("fixture-rotation-l21", lookback=21),))                # 40 // 2 = 20 trips
    L.refused(lambda: uplan(programs=(rotation("fixture-rotation-l22", lookback=22),)), "STUDY_ROUNDTRIPS_INFEASIBLE")


def test_prior_attempts_join_every_family_and_count_in_k():
    priors = ("old-universe-study.r1", "old-universe-study.r2", "old-universe-study.r3")
    p = uplan(prior_attempts=priors, alpha=D("0.004"))                              # K = 4: 4 / 1000 <= 0.004
    assert all(c.protocol.family_members == tuple(sorted((ROTATION.strategy_id,) + priors)) for c in p.candidates)
    L.refused(lambda: uplan(prior_attempts=priors, alpha=D("0.003")), "STUDY_PVALUE_RESOLUTION_INFEASIBLE")
    for bad in ("old-universe-study.r1", ("x y",), ("a", "a"), (ROTATION.strategy_id,), (1,)):
        L.refused(lambda: uplan(prior_attempts=bad), "STUDY_PRIOR_ATTEMPTS_INVALID")
    fixed = S.build_study_plan(L.profile(), L.PROGRAMS, template=L.template(), plan_id="fixture-plan-2031",
                               asset="BTC", risk_group="crypto-btc",
                               prior_attempts=("old-48h-study.fixture-ma-1-2-a",))
    assert fixed.selection_rule == S.SELECTION_RULE
    assert all(len(c.protocol.family_members) == 4 for c in fixed.candidates)


def test_universe_plans_cap_candidates_and_refuse_mixed_kinds():
    three = tuple(rotation("fixture-rotation-" + c) for c in "abc")
    assert len(uplan(programs=three).candidates) == 3
    L.refused(lambda: uplan(programs=three + (rotation("fixture-rotation-d"),)), "STUDY_UNIVERSE_TOO_MANY_CANDIDATES")
    L.refused(lambda: uplan(programs=(ROTATION, L.A)), "STUDY_PLAN_SCHEMA_INVALID")
    L.refused(lambda: L.plan(programs=(ROTATION,)), "STUDY_PLAN_SCHEMA_INVALID")
    L.refused(lambda: S.build_study_plan(L.profile(), (ROTATION,), template=utemplate(),
                                         plan_id="fixture-universe-plan-2031", asset="KRW-UNIVERSE",
                                         risk_group="crypto-krw"), "STUDY_PLAN_SCHEMA_INVALID")
    assert S.STUDY_UNIVERSE_CANDIDATES_LIMIT == 3 and S.UNIVERSE_CAPTURE_LIMIT == 12 * 1024 * 1024


def test_draft_accepts_optional_prior_attempts():
    body = json.loads(L.draft_json())
    names = S._draft(json.dumps(body))[2]
    assert names == {"plan_id": "fixture-plan-2031", "asset": "BTC", "risk_group": "crypto-btc", "prior_attempts": ()}
    body["prior_attempts"] = ["old-48h-study.fixture-ma-1-2-a"]
    assert S._draft(json.dumps(body))[2]["prior_attempts"] == ("old-48h-study.fixture-ma-1-2-a",)
    for bad in ({"prior_attempts": "old-48h-study"}, {"extra": []}):
        L.refused(lambda: S._draft(json.dumps(json.loads(L.draft_json()) | bad)), "STUDY_PLAN_SCHEMA_INVALID")


def test_capture_files_bind_the_universe_readers_and_the_fixed_capture_refuses_universe_plans():
    assert {"execution_accounts/instrument_terms.py", "execution_accounts/universe.py",
            "core/compliance/rules.py"} <= set(S.CAPTURE_FILES)
    L.refused(lambda: S.run_capture(uplan(), book_source=lambda: None, clock=lambda: START - timedelta(days=1),
                                    wait_until=lambda when: True, record=lambda line: None),
              "STUDY_PLAN_SCHEMA_INVALID")
```

In `tests/launch_acceptance.py`, add `"launch_universe_study"` as the last entry of `MODULES`: replace the closing
`)` of the `MODULES` tuple (after `"launch_owner_rehearsal"` at fd85850, or after whatever entry an upstream PR
appended last) with `,\n           "launch_universe_study")` so the new name sits on its own continuation line,
aligned with the other names.

- [ ] **Step 2: Run the tests to verify they fail**

```bash
focus launch launch_universe_study/
```

Expected: exit 1; every row FAILs, for example `TypeError: build_study_plan() got an unexpected keyword argument
'prior_attempts'` and `AttributeError: module 'execution_launch.study' has no attribute '_room'`.

- [ ] **Step 3: Implement** (CRLF file: every new and replaced line ends in `\r\n`)

In `execution_launch/study.py`, replace the line `from collections.abc import Mapping` with
`from collections.abc import Mapping, Sequence`.

Replace the `from execution_launch.strategy import (...)` statement (three lines at fd85850, starting
`from execution_launch.strategy import (ForwardProtocol,`) with:

```python
from execution_launch.strategy import (UNIVERSE_EVALUATOR_REVISION, ForwardProtocol, Registration,
                                       StrategyEvidenceError, ValidationResult, _HASH, _ID, _date, _instant, _json,
                                       _object, _plain, assess_strategy, evaluate_capture_json, evidence_digest,
                                       parse_protocol, register_protocol)
```

Replace:

```python
SELECTION_RULE = "upbit-krw-single-asset-v1"
CAPTURE_FILES = ("execution_launch/study.py", "execution_launch/paper_capture.py", "execution_launch/program.py",
                 "execution_launch/strategy.py", "execution_accounts/quotes.py", "execution/transport.py",
                 "execution/upbit_inquiry.py")
```

with:

```python
SELECTION_RULE = "upbit-krw-single-asset-v1"
UNIVERSE_SELECTION_RULE = "upbit-krw-universe-top1-v1"
STUDY_UNIVERSE_CANDIDATES_LIMIT = 3
UNIVERSE_CAPTURE_LIMIT = 12 * 1024 * 1024  # spec section 14: headroom under workflow.MAX_CAPTURE_BYTES (16 MiB)
CAPTURE_FILES = ("execution_launch/study.py", "execution_launch/paper_capture.py", "execution_launch/program.py",
                 "execution_launch/strategy.py", "execution_accounts/quotes.py", "execution/transport.py",
                 "execution/upbit_inquiry.py", "execution_accounts/instrument_terms.py",
                 "execution_accounts/universe.py", "core/compliance/rules.py")
```

Replace the line `_WORK_LIMIT = 10_000_000                   # equals the evaluator's inference budget
(strategy.run_paper_validation)` with itself followed by:

```python
_UNIVERSE_KIND = "universe_top1_momentum"
```

In `_structure`, replace:

```python
             and plan.selection_rule == SELECTION_RULE and type(plan.candidates) is tuple and plan.candidates
```

with:

```python
             and plan.selection_rule in (SELECTION_RULE, UNIVERSE_SELECTION_RULE)
             and type(plan.candidates) is tuple and plan.candidates
```

and replace:

```python
    _require(all(c.program.kind != "cash" for c in plan.candidates), "STUDY_CASH_MEMBER_CANNOT_QUALIFY")
    return ids
```

with:

```python
    _require(all(c.program.kind != "cash" for c in plan.candidates), "STUDY_CASH_MEMBER_CANNOT_QUALIFY")
    universe = plan.selection_rule == UNIVERSE_SELECTION_RULE
    _require(all((c.program.kind == _UNIVERSE_KIND) == universe
                 and (c.protocol.evaluator_revision == UNIVERSE_EVALUATOR_REVISION) == universe
                 and c.program.universe_rule_sha256 == c.protocol.universe_rule_sha256 for c in plan.candidates),
             "STUDY_PLAN_SCHEMA_INVALID")
    _require(not universe or len(plan.candidates) <= STUDY_UNIVERSE_CANDIDATES_LIMIT,
             "STUDY_UNIVERSE_TOO_MANY_CANDIDATES")
    return ids


def _room(returns, program):
    """The most round trips a candidate can complete in the window (spec section 14): after the warm-up, two slots
    per trip for a fixed program and max(m, 2) for a rotation."""
    if program.kind == _UNIVERSE_KIND:
        return (returns - program.lookback_slots + 1) // max(program.min_hold_slots, 2)
    return (returns - program.slow_window + 1) // 2
```

In `_feasible`, replace:

```python
    _require(all((returns - c.program.slow_window + 1) // 2 >= protocol.minimum_roundtrips for c in candidates),
             "STUDY_ROUNDTRIPS_INFEASIBLE")
```

with:

```python
    _require(all(_room(returns, c.program) >= protocol.minimum_roundtrips for c in candidates),
             "STUDY_ROUNDTRIPS_INFEASIBLE")
```

In `validate_study_plan`, replace:

```python
    _require(all(p.family_members == ids for p in protocols), "STUDY_FAMILY_INCOMPLETE")
```

with:

```python
    family = protocols[0].family_members                 # spec section 14: one tuple, holding every candidate id
    _require(all(p.family_members == family for p in protocols) and set(ids) <= set(family),
             "STUDY_FAMILY_INCOMPLETE")
```

Replace the signature and docstring of `build_study_plan`:

```python
def build_study_plan(profile: LaunchProfile, programs: tuple[ProgramSpec, ...], *, template: ForwardProtocol,
                     plan_id: str, asset: str, risk_group: str,
                     registry: tuple[Registration, ...] = ()) -> StudyPlan:
    """Freeze K candidates from one complete private profile and one template protocol.

    Each program gets the profile variant carrying its identifier and installed-code digest, and a protocol whose
    study id, strategy fields, profile contract, rule terms, capture source, capital, fee and family are derived
    from the profile and the installed code; the template's other terms are common to every candidate.
    """
```

with:

```python
def build_study_plan(profile: LaunchProfile, programs: tuple[ProgramSpec, ...], *, template: ForwardProtocol,
                     plan_id: str, asset: str, risk_group: str,
                     registry: tuple[Registration, ...] = (), prior_attempts: Sequence[str] = ()) -> StudyPlan:
    """Freeze K candidates from one complete private profile and one template protocol.

    Each program gets the profile variant carrying its identifier and installed-code digest, and a protocol whose
    study id, strategy fields, profile contract, rule terms, capture source, capital, fee and family are derived
    from the profile and the installed code; the template's other terms are common to every candidate.
    prior_attempts are the registered study ids of earlier attempts for the same selection: every protocol's family
    is the sorted union of this plan's candidate ids and them, so retries count in K (spec section 14). A template
    with the forward-universe-v1 evaluator makes a universe plan; its profile must carry the same universe rule.
    """
```

Replace:

```python
    _require(len(set(ids)) == len(ids), "STUDY_PLAN_SCHEMA_INVALID")
```

with:

```python
    _require(len(set(ids)) == len(ids), "STUDY_PLAN_SCHEMA_INVALID")
    _require(type(prior_attempts) in (tuple, list)
             and all(type(v) is str and _ID.fullmatch(v) is not None for v in prior_attempts)
             and len(set(prior_attempts)) == len(prior_attempts) and not set(prior_attempts) & set(ids),
             "STUDY_PRIOR_ATTEMPTS_INVALID")
    family = tuple(sorted(set(ids) | set(prior_attempts)))
    _require(profile.universe_rule_sha256 == template.universe_rule_sha256, "STUDY_PLAN_SCHEMA_INVALID")
    selection_rule = (UNIVERSE_SELECTION_RULE if template.evaluator_revision == UNIVERSE_EVALUATOR_REVISION
                      else SELECTION_RULE)
```

Replace `fee_fraction=profile.instrument_rules.fee_fraction, family_members=ids)` with
`fee_fraction=profile.instrument_rules.fee_fraction, family_members=family)` (keep the line's indentation), and
replace `    plan = StudyPlan(schema_version=1, plan_id=plan_id, selection_rule=SELECTION_RULE, asset=asset,` with
`    plan = StudyPlan(schema_version=1, plan_id=plan_id, selection_rule=selection_rule, asset=asset,`.

In `run_capture`, replace:

```python
    digest = validate_study_plan(plan)
    protocol = plan.candidates[0].protocol
    artifact, source = _fixed_file(PROGRAM_SOURCE), capture_source_artifact()
```

with:

```python
    digest = validate_study_plan(plan)
    _require(plan.selection_rule == SELECTION_RULE, "STUDY_PLAN_SCHEMA_INVALID")   # universe: run_universe_capture
    protocol = plan.candidates[0].protocol
    artifact, source = _fixed_file(PROGRAM_SOURCE), capture_source_artifact()
```

Replace the whole `_draft` function:

```python
def _draft(raw):
    body = _json(raw, _MAX_PLAN_BYTES)
    _require(type(body) is dict and set(body) == {"schema_version", "plan_id", "asset", "risk_group", "template",
                                                   "programs"}
             and type(body["schema_version"]) is int and body["schema_version"] == 1
             and type(body["programs"]) is list, "STUDY_PLAN_SCHEMA_INVALID")
    return (parse_protocol(json.dumps(body["template"])), tuple(parse_program(json.dumps(p)) for p in body["programs"]),
            {name: body[name] for name in ("plan_id", "asset", "risk_group")})
```

with:

```python
def _draft(raw):
    body = _json(raw, _MAX_PLAN_BYTES)
    required = {"schema_version", "plan_id", "asset", "risk_group", "template", "programs"}
    _require(type(body) is dict and set(body) in (required, required | {"prior_attempts"})
             and type(body["schema_version"]) is int and body["schema_version"] == 1
             and type(body["programs"]) is list and type(body.get("prior_attempts", [])) is list,
             "STUDY_PLAN_SCHEMA_INVALID")
    names = {name: body[name] for name in ("plan_id", "asset", "risk_group")}
    names["prior_attempts"] = tuple(body.get("prior_attempts", ()))
    return (parse_protocol(json.dumps(body["template"])), tuple(parse_program(json.dumps(p)) for p in body["programs"]),
            names)
```

Check the line endings:

```bash
"$PY" -B -c "b=open('execution_launch/study.py','rb').read(); assert b.count(b'\n') == b.count(b'\r\n'), 'mixed'"
```

- [ ] **Step 4: Run the tests to verify they pass**

```bash
focus launch launch_universe_study/
focus launch launch_study/
focus launch launch_shortened_study/
focus launch launch_guards/
```

Expected: exit 0 for each; the five new rows PASS and every fixed-study row still PASSes (the family test at
`launch_study.py:334-341` still gets `STUDY_FAMILY_INCOMPLETE`).

- [ ] **Step 5: Commit**

```bash
git add execution_launch/study.py tests/launch_universe_study.py tests/launch_acceptance.py
diff <(git diff --cached --stat) <(git diff --cached --stat --ignore-cr-at-eol)
git commit -m "$(cat <<'EOF'
feat(study): universe study rule, rotation feasibility and prior attempts

A template with the forward-universe-v1 evaluator freezes an
upbit-krw-universe-top1-v1 plan of at most three universe_top1_momentum
candidates bound to the profile's rule; feasibility allows
(returns - L + 1) // max(m, 2) round trips; build_study_plan takes
prior_attempts and every family becomes the sorted union with them, and the
draft carries them (universe spec section 14). CAPTURE_FILES binds the
instrument, universe and rules readers. The fixed capture refuses a
universe plan.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
)"
```

Expected: the `diff` prints nothing (`study.py` stayed CRLF); the commit succeeds.

---

### Task 5: The forward-universe-v1 evaluator

**Files:**
- Modify: `execution_launch/strategy.py` (LF; fd85850 anchors: `_EVALUATED` line 30, `_simulate` 332-391,
  `run_paper_validation` 435-446, `evaluate_capture_json` 603-613, end of file 625; locate by the quoted text, PR 4b
  shifted lines)
- Test: `tests/launch_universe_study.py` (append)

**Interfaces:**
- Consumes: `_rule_terms(rules, universe_rule_sha256)`, `UNIVERSE_EVALUATOR_REVISION`, `_protocol` accepting it (PR 4b).
- Produces: `MAX_FRAME_MARKETS = 320`, `MAX_PRICE_CHARS = 16`, `MAX_PRICE_OFFSET_MS = 60000`,
  `UNIVERSE_CAPTURE_KIND = 'tradegen-universe-capture/1'`, `_MAX_BOOKS = 16`, `_FLAG_DIGITS = range(1, 5)` (the
  indexes of `FLAG_CLASSES` other than `unflagged`), `_BENCHMARK = 'KRW-BTC'`; `evaluate_capture_json(protocol, raw,
  rules, *, now)` dispatches a universe protocol to `_evaluate_universe` and returns the same issued
  `ValidationResult`. For Task 6's capture: `_universe_tables(snapshots)`, `_universe_view(frame, markets, tables,
  slot, step) -> (view, sampled)` (one frame, checked and decoded exactly as `_universe_inputs` does),
  `_UniversePath(protocol, rules, *, cost_multiple=1, lag=1, benchmark=False)` with `.step(i, view, decisions, *,
  terminal)` and `.held` (one evaluator run; `_universe_run` is a loop over it) and `_universe_rules(protocol,
  rules)` (the evaluator's terms check). Capture format (one JSON object, keys exactly `kind`, `registry`,
  `source_kind`, `markets`, `snapshots`, `frames`, `decisions`):
  - `markets`: distinct `KRW-` names, at most 320; every index below refers to it.
  - `snapshots`: `{sha256: {"day": "YYYY-MM-DD", "valid_from": iso, "valid_until": iso, "top": [market, ...]}}`.
  - `frames[i]`: `{"observed_at", "sampled_at", "snapshot": sha256 | null, "flags": [[index, digit 1-4], ...] | null,
    "prices": [[index, price text, offset ms], ...] | null, "books": [[index, bid, ask, tick, book sha256] |
    [index, "vanished" | "unavailable"], ...]}` with at most 16 books.
  - `decisions[i]`: `{"bar_index": i, "decided_at": iso, "history_sha256": prefix i, "coin": market | null,
    "fraction": decimal text}`; `coin` is null exactly when `fraction` is `"0"`.
- Refusal codes as listed in the Contract notes.

- [ ] **Step 1: Write the failing tests**

Append to the end of `tests/launch_universe_study.py`:

```python


# -- evaluator -----------------------------------------------------------------------------------------------------

MARKETS = [AAA, BBB, BTC]
SNAP = "1" * 64
COINS = tuple({10: AAA, 11: AAA, 12: BBB, 13: BBB, 56: AAA, 57: AAA, 58: BBB, 59: BBB}.get(i) for i in range(60))


def table(top=(AAA, BBB)):
    return {"day": "2031-01-05", "valid_from": _plain(START - timedelta(days=1)),
            "valid_until": _plain(START + timedelta(days=1)), "top": list(top)}


def mids(i):
    return {AAA: 144 if i == 60 else 120 if i >= 14 else 100, BBB: 120 if i >= 16 else 100, BTC: 100}


def frame_row(i, *, unavailable=(), vanished=(), unpriced=(), flags=(), tickers=True, snapshot=SNAP, prices=None):
    slot = START + BAR * i
    values = mids(i) | (prices or {})
    books = [[n, "unavailable"] if m in unavailable else [n, "vanished"] if m in vanished else
             [n, str(values[m] - 1), str(values[m] + 1), "1", "e" * 64] for n, m in enumerate(MARKETS)]
    priced = None if flags is None or not tickers else [[n, str(values[m]), -1000] for n, m in enumerate(MARKETS)
                                                         if m not in unpriced and m not in vanished]
    return {"observed_at": _plain(slot), "sampled_at": _plain(slot + timedelta(seconds=2)), "snapshot": snapshot,
            "flags": None if flags is None else sorted([MARKETS.index(m), FLAG_CLASSES.index(k)] for m, k in flags),
            "prices": priced, "books": books}


def capture_body(changes=None, coins=COINS, tables=None):
    frames = [frame_row(i, **(changes or {}).get(i, {})) for i in range(61)]
    chain = T.capture_history_digests(frames)
    decisions = [{"bar_index": i, "decided_at": frames[i]["sampled_at"], "history_sha256": chain[i], "coin": c,
                  "fraction": "1" if c else "0"} for i, c in enumerate(coins)]
    return {"kind": T.UNIVERSE_CAPTURE_KIND, "registry": [], "source_kind": "synthetic", "markets": list(MARKETS),
            "snapshots": tables or {SNAP: table()}, "frames": frames, "decisions": decisions}


@lru_cache(maxsize=None)
def protocol():
    return uplan().candidates[0].protocol


def simulate(data, lag=1, benchmark=False):
    views, decisions, _ = T._universe_inputs(protocol(), json.loads(json.dumps(data)))
    return T._universe_run(protocol(), views, decisions, L.rules(), lag=lag, benchmark=benchmark)


def outcome(call):
    try:
        call()
    except T.StrategyEvidenceError as exc:
        return str(exc)
    return "PASS"


def test_universe_evaluator_switches_two_slots_and_stresses_one_more():
    data = capture_body()
    (primary, net), (delayed_metrics, delayed), (bench, _) = (simulate(data), simulate(data, lag=2),
                                                              simulate(data, benchmark=True))
    # (A, A, B, B) at decisions 10-13 and again at 56-59: lag 1 sells A at 13 and buys B at 14; lag 2 one slot later;
    # the terminal bar 60 liquidates.
    assert net[13] < 0 < delayed[13] and net[15] == 0.0 < delayed[15] and net[59] == 0.0 < delayed[59]
    assert (primary.completed_roundtrips, delayed_metrics.completed_roundtrips, bench.completed_roundtrips) == (3, 3, 1)
    cash = simulate(capture_body(coins=(None,) * 60))[0]
    assert cash.completed_roundtrips == 0 and cash.total_return == 0.0


def test_universe_buys_need_top_n_unflagged_and_a_book():
    tables = {SNAP: table(), "3" * 64: table((BBB,))}
    for change in ({"flags": ((AAA, "caution"),)}, {"unavailable": (AAA,)}, {"flags": None},
                   {"snapshot": "3" * 64}, {"snapshot": None}):
        assert simulate(capture_body({11: change}, tables=tables))[1][10] == 0.0, change   # the buy at 11 is skipped
    assert simulate(capture_body({13: {"flags": ((AAA, "warning"),)}}))[1][12] < 0          # a flag never blocks a sell


def test_universe_marks_defers_and_fails_held_coins_honestly():
    assert simulate(capture_body({12: {"unavailable": (AAA,), "prices": {AAA: 110}}}))[1][11] > 0   # ticker mark
    deferred = simulate(capture_body({13: {"unavailable": (AAA,)}}))[1]
    assert deferred[12] == 0.0 and deferred[13] > 0                                         # the sell moves to 14
    assert outcome(lambda: simulate(capture_body({13: {"unavailable": (AAA,), "unpriced": (AAA,)}}))) == \
        "STRATEGY_UNIVERSE_MARK_UNAVAILABLE"
    terminal = capture_body({60: {"unavailable": (AAA,)}})
    assert outcome(lambda: simulate(terminal, lag=2)) == "STRATEGY_UNIVERSE_TERMINAL_BOOK_UNAVAILABLE"
    assert outcome(lambda: simulate(terminal)) == "PASS"
    benchmark = capture_body({20: {"unavailable": (BTC,), "unpriced": (BTC,)}})
    assert outcome(lambda: simulate(benchmark, benchmark=True)) == "STRATEGY_UNIVERSE_BENCHMARK_UNAVAILABLE"
    non_held = capture_body({30: {"vanished": (BBB,)}})
    assert [outcome(lambda lag=lag: simulate(non_held, lag=lag)) for lag in (1, 2)] == ["PASS", "PASS"]
    lag_two = capture_body({14: {"vanished": (AAA,)}})
    assert [outcome(lambda lag=lag: simulate(lag_two, lag=lag)) for lag in (1, 2)] == \
        ["PASS", "STRATEGY_UNIVERSE_HELD_COIN_VANISHED"]


def test_universe_capture_decoding_refuses_malformed_frames_and_decisions():
    def broken(code, edit):
        body = json.loads(json.dumps(capture_body()))
        edit(body)
        assert outcome(lambda: T._universe_inputs(protocol(), body)) == code, code

    invalid = "STRATEGY_UNIVERSE_CAPTURE_INVALID"
    broken(invalid, lambda b: b["markets"].__setitem__(0, "KRW-KRW"))
    broken(invalid, lambda b: b["markets"].__setitem__(1, AAA))
    broken(invalid, lambda b: b["markets"].extend("KRW-Z" + format(n, "03d") for n in range(318)))
    broken(invalid, lambda b: b["frames"][3].update(flags=[[0, 0]]))
    broken(invalid, lambda b: b["frames"][3].update(flags=None))                  # prices without a flag read
    broken(invalid, lambda b: b["frames"][3]["prices"][0].__setitem__(1, "01"))
    broken(invalid, lambda b: b["frames"][3]["prices"][0].__setitem__(1, "1" * 17))
    broken(invalid, lambda b: b["frames"][3]["prices"][0].__setitem__(2, 60001))
    broken(invalid, lambda b: b["frames"][3]["books"].__setitem__(0, [0, "gone"]))
    broken(invalid, lambda b: b["frames"][3].update(extra=1))
    broken("STRATEGY_QUOTE_SPREAD_INVALID", lambda b: b["frames"][3]["books"].__setitem__(0, [0, "100", "100", "1",
                                                                                               "e" * 64]))
    broken("STRATEGY_QUOTE_OFF_TICK", lambda b: b["frames"][3]["books"].__setitem__(0, [0, "99.5", "101", "1",
                                                                                         "e" * 64]))
    broken("STRATEGY_UNIVERSE_SNAPSHOT_NOT_IN_FORCE", lambda b: b["frames"][3].update(snapshot="3" * 64))
    broken("STRATEGY_UNIVERSE_SNAPSHOT_NOT_IN_FORCE", lambda b: b["snapshots"][SNAP].update(
        valid_until=_plain(START + BAR)))
    broken("STRATEGY_CAPTURE_CLOCK_INVALID", lambda b: b["frames"][3].update(sampled_at=_plain(START + 4 * BAR)))
    broken(invalid, lambda b: b["decisions"][10].update(coin=CCC))
    broken(invalid, lambda b: b["decisions"][10].update(fraction="0"))
    broken("STRATEGY_DECISION_INPUT_MISMATCH", lambda b: b["decisions"][10].update(history_sha256="0" * 64))
    broken("STRATEGY_DECISION_LOOKAHEAD_OR_LATE", lambda b: b["decisions"][5].update(
        decided_at=_plain(START + 6 * BAR - timedelta(seconds=59))))
    broken("STRATEGY_LEVERAGE_UNSUPPORTED", lambda b: b["decisions"][10].update(fraction="1.5"))
    broken("STRATEGY_CAPTURE_WINDOW_INCOMPLETE", lambda b: b["frames"].pop())
    broken("STRATEGY_DECISION_COVERAGE_INCOMPLETE", lambda b: b["decisions"].pop())

    def books(count):                                       # frame 3 with count book rows over count markets
        def edit(b):
            b["markets"].extend("KRW-Z" + format(n, "02d") for n in range(count - len(MARKETS)))
            b["frames"][3]["books"].extend([n, "unavailable"] for n in range(len(MARKETS), count))
        return edit
    broken("STRATEGY_DECISION_INPUT_MISMATCH", books(16))   # 16 books decode; only the edited history differs
    broken(invalid, books(17))
    assert T._FLAG_DIGITS == range(1, len(FLAG_CLASSES)) and T.MAX_FRAME_MARKETS == 320 and T._MAX_BOOKS == 16


def test_universe_capture_json_is_evaluated_and_assessed_like_the_fixed_one():
    p = uplan()
    proto = p.candidates[0].protocol
    end = proto.capture_end + timedelta(seconds=60)
    data = capture_body() | {"registry": _plain(p.registry), "source_kind": "prospective_paper_capture"}
    with patch.dict(T._EVALUATED, clear=True):
        result = T.evaluate_capture_json(proto, json.dumps(data), L.rules(), now=end)
        assert result.primary.completed_roundtrips == 3 and result.benchmark.completed_roundtrips == 1
        assert (result.started_at, result.ended_at) == (proto.capture_start, proto.capture_end)
        assessment = T.assess_strategy(proto, result, profile_contract_digest=proto.profile_contract_digest,
                                       rule_terms_digest=proto.rule_terms_digest,
                                       strategy_code_sha256=proto.strategy_code_sha256, now=end)
        assert "STRATEGY_TRUSTED_REVIEW_REQUIRED" in assessment.reasons and not assessment.research_review_ready
    evaluate = lambda body, rules=L.rules(), now=end: T.evaluate_capture_json(proto, json.dumps(body), rules, now=now)
    assert outcome(lambda: evaluate(data | {"kind": "other"})) == "STRATEGY_CAPTURE_JSON_SCHEMA_INVALID"
    assert outcome(lambda: evaluate(data | {"registry": []})) == "STRATEGY_PROTOCOL_NOT_REGISTERED"
    assert outcome(lambda: evaluate(data, now=proto.capture_end)) == "STRATEGY_CAPTURE_NOT_FINISHED"
    assert outcome(lambda: evaluate(data, replace(L.rules(), fee_fraction=D("0.002")))) == "STRATEGY_RULES_MISMATCH"
    fixed = L.plan().candidates[0].protocol
    assert outcome(lambda: T.evaluate_capture_json(fixed, json.dumps(data), L.rules(), now=end)) == \
        "STRATEGY_CAPTURE_JSON_SCHEMA_INVALID"
    fixed_shape = {"registry": [], "source_kind": "synthetic", "bars": [], "decisions": []}
    assert outcome(lambda: evaluate(fixed_shape)) == "STRATEGY_CAPTURE_JSON_SCHEMA_INVALID"
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
focus launch launch_universe_study/test_universe_
```

Expected: exit 1; the five new rows FAIL with `AttributeError: module 'execution_launch.strategy' has no attribute
'UNIVERSE_CAPTURE_KIND'` (or `'_universe_inputs'`). The filter also matches the two Task 4 rows
`test_universe_feasibility_uses_warmup_and_hold_slots` and `test_universe_plans_cap_candidates_and_refuse_mixed_kinds`,
which still PASS.

- [ ] **Step 3: Implement**

In `execution_launch/strategy.py`, replace the line `_EVALUATED: dict[int, tuple[object, str]] = {}` with:

```python
_EVALUATED: dict[int, tuple[object, str]] = {}
# forward-universe-v1 capture maxima (universe spec section 14); study.py imports them for its size bound.
MAX_FRAME_MARKETS = 320
MAX_PRICE_CHARS = 16
MAX_PRICE_OFFSET_MS = 60000
UNIVERSE_CAPTURE_KIND = 'tradegen-universe-capture/1'
_MAX_BOOKS = 16                          # 3 candidates x (decisions j-1, j-2 and 3 held-path coins) + KRW-BTC
_FLAG_DIGITS = range(1, 5)               # core.compliance.rules.FLAG_CLASSES indexes other than "unflagged"
_MARKET = re.compile(r'KRW-[A-Z][A-Z0-9]{0,11}')
_PRICE = re.compile(r'(?:0|[1-9][0-9]*)(?:\.[0-9]*[1-9])?')
_DAY = re.compile(r'[0-9]{4}-[0-9]{2}-[0-9]{2}')
_BENCHMARK = 'KRW-BTC'
_ARCHIVE_KEYS = frozenset({'kind', 'registry', 'source_kind', 'markets', 'snapshots', 'frames', 'decisions'})
_TABLE_KEYS = frozenset({'day', 'valid_from', 'valid_until', 'top'})
_FRAME_KEYS = frozenset({'observed_at', 'sampled_at', 'snapshot', 'flags', 'prices', 'books'})
_DECISION_KEYS = frozenset({'bar_index', 'decided_at', 'history_sha256', 'coin', 'fraction'})
_BOOK_STATES = ('vanished', 'unavailable')
```

Directly before the line `def _simulate(protocol, bars, decisions, rules, *, cost_multiple=1, lag=1, buy_hold=False):`
insert:

```python
def _order(target, nav, units, mark, bid, ask, cash, fee, lot):
    """(side, lot-rounded quantity, price) that moves units toward target * nav, fees included; shared by both
    evaluator revisions."""
    gap = target*nav-units*mark
    if gap > 0:
        quantity = _floor_lots(gap/(ask*(1+fee)-target*(ask*(1+fee)-mark)), lot)
        return 'buy', min(quantity, _floor_lots(cash/(ask*(1+fee)), lot)), ask
    if gap < 0:
        return 'sell', min(units, _ceil_lots(-gap/(mark-target*(mark-bid*(1-fee))), lot)), bid
    return 'none', Fraction(0), mark


def _metrics(navs, trips, rejected, fees, turnover):
    """PaperMetrics and the per-bar net returns of one NAV path; shared by both evaluator revisions."""
    returns = tuple(float(b/a-1) for a, b in zip(navs, navs[1:]))
    _require(all(math.isfinite(v) and v > -1 for v in returns), "STRATEGY_RETURN_INVALID")
    peak, drawdown = navs[0], Fraction(0)
    for nav in navs:
        peak = max(peak, nav); drawdown = max(drawdown, 1-nav/peak)
    metrics = PaperMetrics(observations=len(returns), completed_roundtrips=trips,
        rejected_small_orders=rejected, total_return=float(navs[-1]/navs[0]-1),
        mean_return=math.fsum(returns)/len(returns), max_drawdown=float(drawdown),
        total_fees_quote=float(fees), turnover_quote=float(turnover), terminal_units='0', cash_nonnegative=True)
    return metrics, returns


```

In `_simulate`, replace:

```python
            nav = cash+units*mark
            gap = target*nav-units*mark
            if gap > 0:
                quantity = _floor_lots(gap/(ask*(1+fee)-target*(ask*(1+fee)-mark)), lot)
                quantity = min(quantity, _floor_lots(cash/(ask*(1+fee)), lot))
                side, price = 'buy', ask
            elif gap < 0:
                quantity = min(units, _ceil_lots(-gap/(mark-target*(mark-bid*(1-fee))), lot))
                side, price = 'sell', bid
            else:
                quantity, side, price = Fraction(0), 'none', mark
```

with:

```python
            nav = cash+units*mark
            side, quantity, price = _order(target, nav, units, mark, bid, ask, cash, fee, lot)
```

and replace the end of `_simulate`:

```python
    _require(units == 0, "STRATEGY_TERMINAL_DUST_UNLIQUIDATED")
    returns = tuple(float(b/a-1) for a, b in zip(navs, navs[1:]))
    _require(all(math.isfinite(v) and v > -1 for v in returns), "STRATEGY_RETURN_INVALID")
    peak, drawdown = navs[0], Fraction(0)
    for nav in navs:
        peak = max(peak, nav); drawdown = max(drawdown, 1-nav/peak)
    metrics = PaperMetrics(observations=len(returns), completed_roundtrips=trips,
        rejected_small_orders=rejected, total_return=float(navs[-1]/navs[0]-1),
        mean_return=math.fsum(returns)/len(returns), max_drawdown=float(drawdown),
        total_fees_quote=float(fees), turnover_quote=float(turnover), terminal_units='0', cash_nonnegative=True)
    return metrics, returns
```

with:

```python
    _require(units == 0, "STRATEGY_TERMINAL_DUST_UNLIQUIDATED")
    return _metrics(navs, trips, rejected, fees, turnover)
```

Directly before the line `def run_paper_validation(protocol, bars, decisions, rules, *, registry, source_kind, now):`
insert:

```python
def _issue_result(protocol, sha, registry_sha, *, inputs, source_kind, started_at, ended_at, now, primary, net,
                  doubled, delayed, benchmark, buy_hold):
    """The block-bootstrap p-value, the ValidationResult and its _EVALUATED registration (so assess_strategy
    accepts it); shared by both evaluator revisions."""
    differences = tuple(a-b for a, b in zip(net, buy_hold))
    p = _block_p(differences, protocol.block_length, protocol.bootstrap_replications, protocol.seed)
    result = ValidationResult(protocol_digest=sha, registry_digest=registry_sha,
        inputs_digest=inputs, source_kind=source_kind,
        started_at=started_at, ended_at=ended_at, evaluated_at=now,
        primary=primary, double_cost=doubled, extra_bar_delay=delayed, benchmark=benchmark,
        benchmark_excess_mean=math.fsum(differences)/len(differences), benchmark_p=p,
        family_adjusted_p=min(1.0, p*len(protocol.family_members)),
        net_returns=net, benchmark_returns=buy_hold)
    _require(len(_EVALUATED) < 128, "STRATEGY_EVALUATION_REGISTRY_FULL")
    _EVALUATED[id(result)] = (result, evidence_digest(result))
    return result


```

In `run_paper_validation`, replace:

```python
    differences = tuple(a-b for a, b in zip(net, buy_hold))
    p = _block_p(differences, protocol.block_length, protocol.bootstrap_replications, protocol.seed)
    result = ValidationResult(protocol_digest=sha, registry_digest=registry_sha,
        inputs_digest=evidence_digest((bars, decisions)), source_kind=source_kind,
        started_at=bars[0].observed_at, ended_at=bars[-1].observed_at, evaluated_at=now,
        primary=primary, double_cost=doubled, extra_bar_delay=delayed, benchmark=benchmark,
        benchmark_excess_mean=math.fsum(differences)/len(differences), benchmark_p=p,
        family_adjusted_p=min(1.0, p*len(protocol.family_members)),
        net_returns=net, benchmark_returns=buy_hold)
    _require(len(_EVALUATED) < 128, "STRATEGY_EVALUATION_REGISTRY_FULL")
    _EVALUATED[id(result)] = (result, evidence_digest(result))
    return result
```

with:

```python
    return _issue_result(protocol, sha, registry_sha, inputs=evidence_digest((bars, decisions)),
                         source_kind=source_kind, started_at=bars[0].observed_at, ended_at=bars[-1].observed_at,
                         now=now, primary=primary, net=net, doubled=doubled, delayed=delayed, benchmark=benchmark,
                         buy_hold=buy_hold)
```

Directly before the line `def evaluate_capture_json(protocol, raw, rules, *, now):` insert:

```python
def _registry(items):
    """Registration rows from capture JSON; validate_registry checks the chain."""
    registry = []
    for item in items:
        body = _object(item, Registration); body['registered_at'] = _date(body['registered_at'])
        registry.append(Registration(**body))
    return registry


```

In `evaluate_capture_json`, replace:

```python
    """Strict evidence import reruns arithmetic, never imports a precomputed PASS."""
    data = _json(raw, _MAX_CAPTURE_BYTES)
```

with:

```python
    """Strict evidence import reruns arithmetic, never imports a precomputed PASS.

    A forward-universe-v1 protocol reads the universe capture format (universe spec section 14) instead.
    """
    data = _json(raw, _MAX_CAPTURE_BYTES)
    if type(protocol) is ForwardProtocol and protocol.evaluator_revision == UNIVERSE_EVALUATOR_REVISION:
        return _evaluate_universe(protocol, data, rules, now=now)
```

and replace:

```python
    registry, bars, decisions = [], [], []
    for item in data['registry']:
        body = _object(item, Registration); body['registered_at'] = _date(body['registered_at'])
        registry.append(Registration(**body))
```

with:

```python
    registry, bars, decisions = _registry(data['registry']), [], []
```

Append to the end of `execution_launch/strategy.py` (two blank lines before the first new line):

```python
# -- forward-universe-v1 (universe spec section 14) ---------------------------------------------------------------

@dataclass(frozen=True)
class _UniverseView:
    """One decoded frame: flag exceptions (None when the flag read was unavailable), the candidate's top-N of the
    snapshot in force, books by market ((bid, ask, tick, sha256) or a state) and ticker prices by market."""
    flags: frozenset | None
    top: tuple
    books: dict
    prices: dict


def _price(text):
    _require(type(text) is str and len(text) <= MAX_PRICE_CHARS and _PRICE.fullmatch(text) is not None
             and text != '0', 'STRATEGY_UNIVERSE_CAPTURE_INVALID')
    return Fraction(text)


def _indexed(rows, markets, widths):
    _require(type(rows) is list and all(type(row) is list and len(row) in widths and type(row[0]) is int
                                        and 0 <= row[0] < len(markets) for row in rows)
             and len({row[0] for row in rows}) == len(rows), 'STRATEGY_UNIVERSE_CAPTURE_INVALID')
    return rows


def _universe_tables(snapshots):
    """sha256 -> (valid_from, valid_until, top-N) of a capture's snapshot tables, each checked."""
    tables = {}
    for sha, table in snapshots.items():
        _require(_HASH.fullmatch(sha) is not None and type(table) is dict and set(table) == _TABLE_KEYS
                 and type(table['day']) is str and _DAY.fullmatch(table['day']) is not None
                 and type(table['top']) is list
                 and all(type(m) is str and _MARKET.fullmatch(m) is not None for m in table['top'])
                 and len(set(table['top'])) == len(table['top']), 'STRATEGY_UNIVERSE_CAPTURE_INVALID')
        start, end = _date(table['valid_from']), _date(table['valid_until'])
        _require(start < end, 'STRATEGY_UNIVERSE_CAPTURE_INVALID')
        tables[sha] = (start, end, tuple(table['top']))
    return tables


def _universe_view(frame, markets, tables, slot, step):
    """One frame recorded for slot, checked and decoded: (view, sampled time). _universe_inputs decodes every frame
    with it, and study.py's universe capture decodes each frame it records with it before stepping its replayed
    paths, so both read the same view."""
    _require(type(frame) is dict and set(frame) == _FRAME_KEYS, 'STRATEGY_UNIVERSE_CAPTURE_INVALID')
    _require(_date(frame['observed_at']) == slot, 'STRATEGY_CAPTURE_GAP_OR_DUPLICATE')
    at = _date(frame['sampled_at'])
    _require(slot <= at < slot+step, 'STRATEGY_CAPTURE_CLOCK_INVALID')
    sha = frame['snapshot']
    table = tables.get(sha) if type(sha) is str else None
    _require(sha is None or table is not None and table[0] <= slot < table[1],
             'STRATEGY_UNIVERSE_SNAPSHOT_NOT_IN_FORCE')
    flags = None
    if frame['flags'] is not None:
        rows = _indexed(frame['flags'], markets, (2,))
        _require(all(type(kind) is int and kind in _FLAG_DIGITS for _, kind in rows),
                 'STRATEGY_UNIVERSE_CAPTURE_INVALID')
        flags = frozenset(markets[n] for n, _ in rows)
    prices = {}
    if frame['prices'] is not None:
        rows = _indexed(frame['prices'], markets, (3,))
        _require(flags is not None and all(type(offset) is int and abs(offset) <= MAX_PRICE_OFFSET_MS
                                           for _, _, offset in rows), 'STRATEGY_UNIVERSE_CAPTURE_INVALID')
        prices = {markets[n]: _price(text) for n, text, _ in rows}
    rows = _indexed(frame['books'], markets, (2, 5))
    _require(len(rows) <= _MAX_BOOKS, 'STRATEGY_UNIVERSE_CAPTURE_INVALID')
    books = {}
    for row in rows:
        if len(row) == 2:
            _require(row[1] in _BOOK_STATES, 'STRATEGY_UNIVERSE_CAPTURE_INVALID')
            books[markets[row[0]]] = row[1]
            continue
        bid, ask, tick = (_price(text) for text in row[1:4])
        _require(type(row[4]) is str and _HASH.fullmatch(row[4]) is not None, 'STRATEGY_UNIVERSE_CAPTURE_INVALID')
        _require(bid < ask, 'STRATEGY_QUOTE_SPREAD_INVALID')
        _require((bid/tick).denominator == 1 and (ask/tick).denominator == 1, 'STRATEGY_QUOTE_OFF_TICK')
        books[markets[row[0]]] = (bid, ask, tick, row[4])
    return _UniverseView(flags=flags, top=() if sha is None else table[2], books=books, prices=prices), at


def _universe_inputs(protocol, data):
    """Decode one universe capture against the protocol's grid: (views, decisions, last sampled time).

    Every frame is checked before any decision; a decision must name the prefix digest of the frames it saw and
    land at least the fill delay before the next slot.
    """
    step = timedelta(seconds=protocol.bar_seconds)
    delay = timedelta(seconds=protocol.minimum_fill_delay_seconds)
    markets, frames, items = data['markets'], data['frames'], data['decisions']
    _require(len(markets) <= MAX_FRAME_MARKETS
             and all(type(m) is str and _MARKET.fullmatch(m) is not None and m != 'KRW-KRW' for m in markets)
             and len(set(markets)) == len(markets), 'STRATEGY_UNIVERSE_CAPTURE_INVALID')
    tables = _universe_tables(data['snapshots'])
    slots = (protocol.capture_end-protocol.capture_start)//step+1
    _require(len(frames) == slots <= _MAX_ROWS, 'STRATEGY_CAPTURE_WINDOW_INCOMPLETE')
    _require(len(items) == slots-1, 'STRATEGY_DECISION_COVERAGE_INCOMPLETE')
    views, sampled, prefixes, chain = [], [], [], ''
    for i, frame in enumerate(frames):
        view, at = _universe_view(frame, markets, tables, protocol.capture_start+i*step, step)
        chain = evidence_digest((chain, frame)); prefixes.append(chain)
        views.append(view); sampled.append(at)
    names, decisions = set(markets), []
    for i, item in enumerate(items):
        _require(type(item) is dict and set(item) == _DECISION_KEYS, 'STRATEGY_CAPTURE_JSON_SCHEMA_INVALID')
        _require(type(item['bar_index']) is int and item['bar_index'] == i, 'STRATEGY_DECISION_ORDER_INVALID')
        at = _date(item['decided_at'])
        _require(item['history_sha256'] == prefixes[i], 'STRATEGY_DECISION_INPUT_MISMATCH')
        fraction = _decimal(item['fraction'])
        _require(fraction <= 1, 'STRATEGY_LEVERAGE_UNSUPPORTED')
        coin = item['coin']
        _require((coin is None) == (fraction == 0) and (coin is None or type(coin) is str and coin in names),
                 'STRATEGY_UNIVERSE_CAPTURE_INVALID')
        _require(sampled[i] <= at and at+delay <= protocol.capture_start+(i+1)*step,
                 'STRATEGY_DECISION_LOOKAHEAD_OR_LATE')
        decisions.append((coin, Fraction(fraction)))
    return tuple(views), tuple(decisions), max(sampled)


class _UniversePath:
    """One forward-universe-v1 NAV path holding at most one coin (spec section 14), advanced one decoded frame at a
    time. A switch sells the held coin at the decision slot plus lag and buys the new one a slot later; a buy needs
    the target in the slot's top-N, unflagged and a book; a sell without a book moves to the next slot that has one;
    the mark is the book midpoint, else the slot's ticker price, else the trial fails. benchmark=True holds KRW-BTC
    from the lag on and any failure is STRATEGY_UNIVERSE_BENCHMARK_UNAVAILABLE. _universe_run steps it over a whole
    capture; study.py's universe capture steps each candidate's lag-1, double-cost and lag-2 paths on the frames it
    records, so the coin it keeps asking a book for is the coin held here."""

    def __init__(self, protocol, rules, *, cost_multiple=1, lag=1, benchmark=False):
        self.lag, self.benchmark, self.rules = lag, benchmark, rules
        self.fee = Fraction(protocol.fee_fraction)*cost_multiple
        self.slip = Fraction(protocol.slippage_bps)*cost_multiple/10000
        self.cash, self.units, self.held = Fraction(protocol.initial_cash_quote), Fraction(0), None
        self.fees, self.turnover, self.trips, self.rejected = Fraction(0), Fraction(0), 0, 0
        self.navs = [self.cash]

    def fail(self, code):
        raise StrategyEvidenceError('STRATEGY_UNIVERSE_BENCHMARK_UNAVAILABLE' if self.benchmark else code)

    def step(self, i, view, decisions, *, terminal):
        """Slot i (from 1): trade toward decisions[i - lag] (cash before the lag and at the terminal bar), then mark."""
        rules = self.rules
        if terminal or i < self.lag:
            coin, fraction = None, Fraction(0)
        else:
            coin, fraction = (_BENCHMARK, Fraction(1)) if self.benchmark else decisions[i-self.lag]
        if self.held is not None and view.books.get(self.held) == 'vanished':
            self.fail('STRATEGY_UNIVERSE_HELD_COIN_VANISHED')
        trade, target = ((self.held, fraction if coin == self.held else Fraction(0)) if self.held
                         else (coin, fraction))
        book = view.books.get(trade)
        if type(book) is tuple:
            bid = _floor_lots(book[0]*(1-self.slip), book[2])
            ask = _ceil_lots(book[1]*(1+self.slip), book[2])
            _require(bid > 0, 'STRATEGY_SLIPPAGE_INVALID')
            mark = (book[0]+book[1])/2
            side, quantity, price = _order(target, self.cash+self.units*mark, self.units, mark, bid, ask, self.cash,
                                           self.fee, Fraction(rules.lot_size))
            if side == 'buy' and not self.benchmark and (view.flags is None or trade in view.flags
                                                         or trade not in view.top):
                quantity = Fraction(0)
            if quantity:
                if quantity < Fraction(rules.min_quantity) or quantity*price < Fraction(rules.min_notional_krw):
                    self.rejected += 1
                    if terminal:
                        self.fail('STRATEGY_TERMINAL_DUST_UNLIQUIDATED')
                else:
                    charge = quantity*price*self.fee
                    self.cash += quantity*price-charge if side == 'sell' else -quantity*price-charge
                    self.units += quantity if side == 'buy' else -quantity
                    self.fees += charge; self.turnover += quantity*price
                    _require(self.cash >= 0 and self.units >= 0, 'STRATEGY_CASH_OR_POSITION_NEGATIVE')
                    self.trips += side == 'sell' and self.units == 0
                    self.held = trade if self.units else None
        elif terminal and self.held is not None:
            self.fail('STRATEGY_UNIVERSE_TERMINAL_BOOK_UNAVAILABLE')
        nav = self.cash
        if self.held is not None:
            book = view.books.get(self.held)
            if type(book) is tuple:
                mark = (book[0]+book[1])/2
            elif self.held in view.prices:
                mark = view.prices[self.held]
            else:
                self.fail('STRATEGY_UNIVERSE_MARK_UNAVAILABLE')
            nav = self.cash+self.units*mark
        _require(0 < nav <= 10**100, 'STRATEGY_NAV_OUT_OF_RANGE')
        self.navs.append(nav)


def _universe_run(protocol, views, decisions, rules, *, cost_multiple=1, lag=1, benchmark=False):
    """One whole _UniversePath over a decoded capture: its PaperMetrics and per-bar net returns."""
    path = _UniversePath(protocol, rules, cost_multiple=cost_multiple, lag=lag, benchmark=benchmark)
    for i in range(1, len(views)):
        path.step(i, views[i], decisions, terminal=i == len(views)-1)
    _require(path.units == 0, 'STRATEGY_TERMINAL_DUST_UNLIQUIDATED')
    return _metrics(path.navs, path.trips, path.rejected, path.fees, path.turnover)


def _universe_rules(protocol, rules):
    """The evaluator's terms check, shared with study.py's universe capture: InstrumentRules for the protocol's venue
    and market, bound to its rule-terms digest, with a fee no higher than the protocol's."""
    _require(type(rules) is InstrumentRules
             and _rule_terms(rules, protocol.universe_rule_sha256) == protocol.rule_terms_digest
             and (rules.venue, rules.market) == (protocol.venue, protocol.market)
             and protocol.fee_fraction >= rules.fee_fraction, "STRATEGY_RULES_MISMATCH")


def _evaluate_universe(protocol, data, rules, *, now):
    """forward-universe-v1 over one complete universe capture: run_paper_validation's registry, source, window and
    inference rules, the benchmark first (its failure ends every candidate's trial), then the primary, double-cost
    and extra-delay runs."""
    sha = _protocol(protocol); _instant(now)
    _require(type(data) is dict and set(data) == _ARCHIVE_KEYS and data['kind'] == UNIVERSE_CAPTURE_KIND
             and all(type(data[k]) is list for k in ('registry', 'markets', 'frames', 'decisions'))
             and type(data['snapshots']) is dict, 'STRATEGY_CAPTURE_JSON_SCHEMA_INVALID')
    registry = tuple(_registry(data['registry']))
    registry_sha = validate_registry(registry)
    _require(any(r.study_id == protocol.study_id and r.protocol_digest == sha
                 and r.registered_at == protocol.preregistered_at for r in registry),
             "STRATEGY_PROTOCOL_NOT_REGISTERED")
    source_kind = data['source_kind']
    _require(source_kind in ('prospective_paper_capture', 'synthetic', 'retrospective_replay'),
             "STRATEGY_SOURCE_KIND_INVALID")
    _universe_rules(protocol, rules)
    views, decisions, last = _universe_inputs(protocol, data)
    _require(now >= last and now >= protocol.capture_end, "STRATEGY_CAPTURE_NOT_FINISHED")
    _require(len(views)-1 >= protocol.minimum_observations, "STRATEGY_OBSERVATIONS_INSUFFICIENT")
    _require(protocol.bootstrap_replications*((len(views)-1)//protocol.block_length+1) <= 10000000,
             'STRATEGY_INFERENCE_WORK_LIMIT')
    benchmark, buy_hold = _universe_run(protocol, views, decisions, rules, benchmark=True)
    primary, net = _universe_run(protocol, views, decisions, rules)
    doubled, _ = _universe_run(protocol, views, decisions, rules, cost_multiple=2)
    delayed, _ = _universe_run(protocol, views, decisions, rules, lag=2)
    inputs = evidence_digest([data['markets'], data['snapshots'], data['frames'], data['decisions']])
    return _issue_result(protocol, sha, registry_sha, inputs=inputs, source_kind=source_kind,
                         started_at=protocol.capture_start, ended_at=protocol.capture_end, now=now,
                         primary=primary, net=net, doubled=doubled, delayed=delayed, benchmark=benchmark,
                         buy_hold=buy_hold)
```

- [ ] **Step 4: Run the tests to verify they pass**

```bash
focus launch launch_universe_study/
focus launch launch_strategy/
focus launch launch_study/
focus launch launch_capture/
focus launch launch_guards/
```

Expected: exit 0 for each. `launch_strategy`, `launch_study` and `launch_capture` passing unchanged proves the
extracted `_order`, `_metrics`, `_issue_result` and `_registry` keep the fixed evaluator's arithmetic and results.

- [ ] **Step 5: Commit**

```bash
git add execution_launch/strategy.py tests/launch_universe_study.py
diff <(git diff --cached --stat) <(git diff --cached --stat --ignore-cr-at-eol)
git commit -m "$(cat <<'EOF'
feat(strategy): forward-universe-v1 evaluator over compact universe captures

evaluate_capture_json sends a universe protocol to a decoder of the
universe capture (market index, snapshot tables, per-slot frames) and a
one-coin path: two-slot switches, buys only in the top-N, unflagged and with
a book, sells deferred to the next book, ticker marks when the book is
unavailable, and disclosed failures for a held coin that vanished, has no
mark or no terminal book, or a benchmark that cannot be marked (universe
spec section 14). Order arithmetic, metrics and result registration are
shared with forward-paper-v1, whose results are unchanged. Each run is a
_UniversePath stepped one decoded frame at a time, so the universe capture
can replay it to learn which coin a path still holds.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
)"
```

Expected: the `diff` prints nothing; the commit succeeds.

---

### Task 6: Universe capture and the size check

**Files:**
- Modify: `execution_launch/study.py` (CRLF; imports at the top, constants after `_UNIVERSE_KIND`,
  `validate_study_plan`, a new section after `run_capture`)
- Test: `tests/launch_universe_study.py` (append)

**Interfaces:**
- Consumes: `FLAG_CLASSES`, `universe_top_n`, `verify_universe_snapshot` (PR 1); `ChooserState`, `ChooserSlot`,
  `choose` (PR 4b); `parse_orderbooks` (Task 1), `parse_instruments` (Task 2), `FlagRead.answer` and
  `TickerRead.answer` (Task 3); the strategy constants, `_universe_tables`, `_universe_view`, `_UniversePath` and
  `_universe_rules` (Task 5).
- Produces: `UniverseArchive(registry, source_kind, markets, snapshots, frames, decisions)` (frozen, kw_only);
  `universe_capture_json(archive) -> str` (refuses above `MAX_CAPTURE_BYTES` with `STUDY_CAPTURE_JSON_TOO_LARGE`);
  `run_universe_capture(plan, *, rules, source, clock, wait_until, record) -> CaptureOutcome` where `rules` are the
  frozen `InstrumentRules` (checked by `_universe_rules`, `STRATEGY_RULES_MISMATCH`) and `source` has
  `read_flags() -> FlagRead`, `read_tickers(markets) -> TickerRead`, `read_books(markets) -> SourceReceipt`,
  `read_ticks(markets) -> SourceReceipt` (the last two may raise) and `snapshots(day) -> list[bytes]`;
  `_needed(paths, replays, index)`: the books slot index asks for, every candidate's decisions index-1 and index-2
  and the coin held by each of its replayed lag-1, double-cost and lag-2 paths, plus KRW-BTC: at most
  3 x (2 + 3) + 1 = `_MAX_BOOKS` by construction (`STUDY_CAPTURE_BOOKS_OVER_LIMIT` above it is a guard that no plan
  within the candidate cap reaches);
  `validate_study_plan` refuses a universe plan above `UNIVERSE_CAPTURE_LIMIT` (`STUDY_UNIVERSE_CAPTURE_SIZE`);
  `STUDY_CAPTURE_DECISION_TOO_LATE` when the slot's sample leaves less than the fill delay before the next slot.
  `receipts.jsonl` lines: `{"probe": raw read}`, `{"snapshot": base64, "sha256": hex}` once per new snapshot file,
  `{"slot", "observed_at", "flags", "tickers", "books", "ticks", "decisions"}` per slot, then `{"end": reason}`.

- [ ] **Step 1: Write the failing tests**

Append to the end of `tests/launch_universe_study.py`:

```python


# -- capture -------------------------------------------------------------------------------------------------------

SNAPSHOT_RAW = {date(2031, 1, 5): b"fixture-snapshot-2031-01-05", date(2031, 1, 6): b"fixture-snapshot-2031-01-06"}
RULES_ROWS = ((100, 100, 100), (100, 100, 110), (110, 100, 120), (111, 100, 130), (112, 120, 140), (113, 122, 150),
              (113, 125, 160), (113, 130, 170), (113, 130, 180), (130, 130, 190), (140, 130, 200), (140, 130, 210),
              (140, 130, 220))                                      # mids of AAA, BBB, CCC; KRW-BTC stays at 100
RULES_FLAGS = {8: {BBB: "warning"}, 9: {AAA: "caution"}}
RULES_DECISIONS = (None, None, AAA, AAA, BBB, BBB, BBB, BBB, None, None, AAA, AAA) + (None,) * 48
VANISH_ROWS = ((100, 100, 100), (100, 100, 100), (110, 100, 100), (99, 100, 100))
DEFER_ROWS = ((100, 100, 100), (100, 100, 100), (110, 100, 100), (120, 100, 100), (120, 120, 100), (120, 132, 100),
              (120, 145, 100), (120, 160, 100), (120, 176, 100), (120, 194, 100), (120, 213, 100), (120, 234, 100),
              (120, 258, 100))                                      # hold 1: decisions AAA at 2-3, BBB at 4-12, cash


def universe(day, sha):
    built = datetime(day.year, day.month, day.day, 0, 12, tzinfo=timezone.utc)
    return Universe(day=day, rule_sha256=RULE, snapshot_sha256=sha, built_at=built,
                    valid_from=built + timedelta(minutes=28), valid_until=built + timedelta(days=1, minutes=28),
                    listed=(AAA, BBB, BTC, CCC), eligible=((AAA, D(3)), (BBB, D(2)), (CCC, D(1))))


SNAPSHOTS = {SNAPSHOT_RAW[date(2031, 1, 5)]: universe(date(2031, 1, 5), "1" * 64),
             SNAPSHOT_RAW[date(2031, 1, 6)]: universe(date(2031, 1, 6), "2" * 64)}


def verify(raw, rule_sha256):
    assert rule_sha256 == RULE
    return SNAPSHOTS[raw]


def scripted(rows):
    return lambda index: rows[min(index, len(rows) - 1)]


def rules_asked(index):
    for last, coins in ((2, (BTC,)), (4, (AAA, BTC)), (6, (AAA, BBB, BTC)), (10, (BBB, BTC)), (14, (AAA, BTC))):
        if index <= last:
            return coins
    return (BTC,)


class Feed:
    """A scripted universe source on a one-cell clock. Reads happen at slot - 5 s; mids come from rows(index) for
    AAA, BBB and CCC and KRW-BTC is 100; flags, absent coins, book overrides (bid, ask, age seconds) and outages are
    keyed by slot index."""

    def __init__(self, plan, rows, *, flags=None, absent=None, books=None, flags_down=(), tickers_down=(),
                 books_down=(), stop_at=None):
        self.plan, self.rows = plan, rows
        self.start = plan.candidates[0].protocol.capture_start
        self.now = [self.start - timedelta(seconds=120)]
        self.flags, self.absent, self.books = flags or {}, absent or {}, books or {}
        self.flags_down, self.tickers_down, self.books_down = flags_down, tickers_down, books_down
        self.stop_at, self.lines, self.asked = stop_at, [], {}

    def index(self):
        return max(0, round((self.now[0] - self.start) / BAR))

    def mid(self, coin, index):
        return 100 if coin == BTC else dict(zip((AAA, BBB, CCC), self.rows(index)))[coin]

    def answer(self, body):
        raw = json.dumps(body).encode()
        return SimpleNamespace(raw_body=raw, received_utc=self.now[0], server_utc=self.now[0],
                               sha256=hashlib.sha256(raw).hexdigest())

    def read_flags(self):
        i = self.index()
        if i in self.flags_down:
            return U.FlagRead(ok=False, received_at=None, sha256=None, flags=MappingProxyType({}))
        flags = {c: self.flags.get(i, {}).get(c, "unflagged") for c in (AAA, BBB, BTC, CCC)
                 if c not in self.absent.get(i, ())}
        return U.FlagRead(ok=True, received_at=self.now[0], sha256="a" * 64, flags=MappingProxyType(flags),
                          answer=self.answer(flags))

    def read_tickers(self, markets):
        i = self.index()
        if i in self.tickers_down:
            return U.TickerRead(ok=False, received_at=None, sha256=None, prices=MappingProxyType({}))
        traded = self.now[0] - timedelta(seconds=1)
        prices = {c: (D(self.mid(c, i)), traded) for c in markets}
        return U.TickerRead(ok=True, received_at=self.now[0], sha256="b" * 64, prices=MappingProxyType(prices),
                            answer=self.answer({c: str(p) for c, (p, _) in prices.items()}))

    def read_books(self, asked):
        i = self.index()
        self.asked[i] = tuple(asked)
        if i in self.books_down:
            raise QuoteError("QUOTE_PUBLIC_INQUIRY_FAILED")
        rows = []
        for coin in asked:
            mid = self.mid(coin, i)
            bid, ask, age = self.books.get(i, {}).get(coin, (mid - 1, mid + 1, 2))
            stamp = int((self.now[0] - timedelta(seconds=age)).timestamp()) * 1000
            rows.append(dict(market=coin, timestamp=stamp, level=0, total_ask_size=10, total_bid_size=10,
                             orderbook_units=[dict(ask_price=ask, bid_price=bid, ask_size=1, bid_size=1)]))
        raw = json.dumps(rows, separators=(",", ":")).encode()
        return SourceReceipt(path=ORDERBOOK_PATH, params=(("markets", ",".join(asked)), ("level", "0"),
                                                          ("count", "30")),
                             account_scope="public-upbit-orderbook", received_at=self.now[0],
                             server_time=self.now[0], raw_body=raw, sha256=hashlib.sha256(raw).hexdigest())

    def read_ticks(self, asked):
        rows = [{"market": c, "tick_size": "1", "quote_currency": "KRW", "supported_levels": ["0"]} for c in asked]
        raw = json.dumps(rows).encode()
        return SourceReceipt(path=TERMS_INSTRUMENTS_PATH, params=(("markets", ",".join(asked)),),
                             account_scope="public-upbit-terms", received_at=self.now[0], server_time=self.now[0],
                             raw_body=raw, sha256=hashlib.sha256(raw).hexdigest())

    def snapshots(self, day):
        return [SNAPSHOT_RAW[day]] if day in SNAPSHOT_RAW else []

    def wait_until(self, when):
        if self.stop_at is not None and when >= self.stop_at:
            return False
        self.now[0] = max(self.now[0], when)
        return True

    def run(self):
        with patch.object(S, "verify_universe_snapshot", verify):
            return S.run_universe_capture(self.plan, rules=L.rules(), source=self, clock=lambda: self.now[0],
                                          wait_until=self.wait_until, record=self.lines.append)


def replay(plan, archive, lag=1):
    p = plan.candidates[0].protocol
    views, coins, _ = T._universe_inputs(p, json.loads(S.universe_capture_json(archive)))
    return T._universe_run(p, views, coins, L.rules(), lag=lag)


def holdings(plan, archive, lag):
    """The coin the evaluator's run at this lag holds after each slot, stepped by its own _UniversePath."""
    p = plan.candidates[0].protocol
    views, coins, _ = T._universe_inputs(p, json.loads(S.universe_capture_json(archive)))
    path, held = T._UniversePath(p, L.rules(), lag=lag), [None]
    for i in range(1, len(views)):
        path.step(i, views[i], coins, terminal=i == len(views) - 1)
        held.append(path.held)
    return held


def test_universe_capture_records_frames_and_drives_the_chooser():
    p = uplan()
    feed = Feed(p, scripted(RULES_ROWS), flags=RULES_FLAGS, tickers_down=(5,))
    result = feed.run()
    assert result.complete and result.reason is None and result.slots_recorded == 61 and len(feed.lines) == 65
    lines = [json.loads(line) for line in feed.lines]
    assert [n for n, line in enumerate(lines) if "snapshot" in line] == [1, 10]     # Jan 5, then Jan 6 at 00:40
    raw = SNAPSHOT_RAW[date(2031, 1, 5)]
    assert lines[1] == {"snapshot": base64.b64encode(raw).decode("ascii"), "sha256": hashlib.sha256(raw).hexdigest()}
    assert lines[2]["flags"]["raw_body_b64"] and lines[2]["books"]["path"] == ORDERBOOK_PATH
    archive = result.archives[0]
    order = list(archive.markets)
    assert tuple(d["coin"] for d in archive.decisions) == RULES_DECISIONS      # d8: BBB warning exits by rule 1
    assert all(feed.asked[i] == rules_asked(i) for i in range(61))
    assert archive.frames[7]["snapshot"] == "1" * 64 and archive.frames[8]["snapshot"] == "2" * 64
    assert archive.frames[5]["prices"] is None and archive.frames[5]["flags"] == []   # failed ticker read
    assert archive.frames[8]["flags"] == [[order.index(BBB), 1]] and archive.frames[9]["flags"] == [[order.index(AAA), 2]]
    assert archive.snapshots["1" * 64]["top"] == [AAA, BBB] and set(archive.snapshots) == {"1" * 64, "2" * 64}
    assert [replay(p, archive, lag)[0].completed_roundtrips for lag in (1, 2)] == [3, 3]


def test_universe_book_selection_uses_only_earlier_frames():
    p = uplan()
    base = Feed(p, scripted(RULES_ROWS), flags=RULES_FLAGS, tickers_down=(5,))
    changed = Feed(p, scripted(RULES_ROWS[:7] + ((100, 100, 100),)), flags=RULES_FLAGS, tickers_down=(5,))
    first, second = base.run().archives[0], changed.run().archives[0]
    assert all(base.asked[i] == changed.asked[i] for i in range(8))           # slot 7 asks before frame 7 exists
    assert [d["coin"] for d in first.decisions[:7]] == [d["coin"] for d in second.decisions[:7]]
    assert first.decisions[7]["coin"] == BBB and second.decisions[7]["coin"] is None


def test_universe_vanished_and_stale_books_fail_only_their_holders():
    p = uplan(programs=(rotation("fixture-rotation-v", hold=1),))
    feed = Feed(p, scripted(VANISH_ROWS), books={4: {BTC: (99, 101, 11)}}, absent={5: (AAA,)})
    result = feed.run()
    archive = result.archives[0]
    order = list(archive.markets)
    assert result.complete and tuple(d["coin"] for d in archive.decisions) == (None, None, AAA) + (None,) * 57
    books = {i: {order[row[0]]: row[1:] for row in archive.frames[i]["books"]} for i in (4, 5)}
    assert books[4][BTC] == ["unavailable"] and books[4][AAA][:3] == ["98", "100", "1"]   # one stale book of two
    assert books[5][AAA] == ["vanished"] and feed.asked[5] == (BTC,)
    assert replay(p, archive)[0].completed_roundtrips == 1                    # lag 1 sold AAA at slot 4
    assert outcome(lambda: replay(p, archive, lag=2)) == "STRATEGY_UNIVERSE_HELD_COIN_VANISHED"
    proto = p.candidates[0].protocol
    with patch.dict(T._EVALUATED, clear=True):
        assert outcome(lambda: T.evaluate_capture_json(proto, S.universe_capture_json(archive), L.rules(),
                                                       now=proto.capture_end + timedelta(seconds=60))) == \
            "STRATEGY_UNIVERSE_HELD_COIN_VANISHED"


def test_universe_deferred_sells_keep_their_book_requests():
    p = uplan(programs=(rotation("fixture-rotation-s", hold=1),))
    runs = []
    for stale in (range(5, 9), range(6, 10)):                       # AAA's book 11 s old there: unavailable
        feed = Feed(p, scripted(DEFER_ROWS), books={i: {AAA: (119, 121, 11)} for i in stale})
        result = feed.run()
        archive = result.archives[0]
        order = list(archive.markets)
        books = [{order[row[0]]: row[1:] for row in frame["books"]} for frame in archive.frames]
        assert result.complete and [d["coin"] for d in archive.decisions[:14]] == \
            [None, None, AAA, AAA] + [BBB] * 9 + [None]
        assert all(books[i][AAA] == ["unavailable"] for i in stale) and \
            books[stale[-1] + 1][AAA][:3] == ["119", "121", "1"]
        assert [replay(p, archive, lag)[0].completed_roundtrips for lag in (1, 2)] == [2, 2]
        runs.append((feed, archive))
    (first, deferred), (second, lagged) = runs
    # Lag 1 sells AAA from slot 5 and lag 2 from slot 6; AAA's book is unusable at 5-8 and the decisions stop naming
    # AAA after slot 5, yet both paths keep asking for it and sell it at slot 9, its first usable book.
    assert [i for i in range(61) if AAA in first.asked[i]] == list(range(3, 10))
    assert holdings(p, deferred, 1)[3:11] == [AAA] * 6 + [None, BBB]
    assert holdings(p, deferred, 2)[4:11] == [AAA] * 5 + [None, BBB]
    # Lag 1 sells AAA at slot 5; only the lag-2 path still holds it, unusable at 6-9, and sells it at slot 10.
    assert [i for i in range(61) if AAA in second.asked[i]] == list(range(3, 11))
    assert holdings(p, lagged, 1)[3:7] == [AAA, AAA, None, BBB]
    assert holdings(p, lagged, 2)[4:12] == [AAA] * 6 + [None, BBB]
    # AAA unusable at 4-8: lag 2 never buys it (it buys BBB at slot 6); only the lag-1 path holds it, and sells it at 9.
    alone = Feed(p, scripted(DEFER_ROWS), books={i: {AAA: (119, 121, 11)} for i in range(4, 9)})
    result = alone.run()
    archive = result.archives[0]
    assert result.complete and [i for i in range(61) if AAA in alone.asked[i]] == list(range(3, 10))
    assert AAA not in holdings(p, archive, 2) and holdings(p, archive, 1)[3:11] == [AAA] * 6 + [None, BBB]
    assert [replay(p, archive, lag)[0].completed_roundtrips for lag in (1, 2)] == [2, 1]
    # Three candidates' decisions index-1 and index-2 and three held coins each: 16 books, the most a plan needs; a
    # fourth decision list, beyond the candidate cap, is refused, never truncated.
    coins = [["KRW-C" + format(10 * n + k, "02d") for k in range(3)] for n in range(3)]
    held = [[SimpleNamespace(held="KRW-H" + format(3 * n + k, "02d")) for k in range(3)] for n in range(3)]
    assert len(S._needed(coins, held, 3)) == 16
    L.refused(lambda: S._needed(coins + [["KRW-X00"] * 3], held, 3), "STUDY_CAPTURE_BOOKS_OVER_LIMIT")


def test_universe_capture_probe_stop_and_book_outage():
    p = uplan()
    down = Feed(p, scripted(RULES_ROWS), flags_down=(0,))
    L.refused(down.run, "STUDY_PREWINDOW_PROBE_FAILED")
    assert down.lines == []
    stopped = Feed(p, scripted(RULES_ROWS), stop_at=START + 10 * BAR - S._PREFETCH_LEAD)
    result = stopped.run()
    assert not result.complete and result.reason == "STUDY_CAPTURE_STOPPED" and result.slots_recorded == 10
    assert len(result.archives[0].frames) == 10 and json.loads(stopped.lines[-1]) == {"end": "STUDY_CAPTURE_STOPPED"}
    outage = Feed(p, scripted(RULES_ROWS), books_down=(3,))
    result = outage.run()
    assert result.complete and all(row[1:] == ["unavailable"] for row in result.archives[0].frames[3]["books"])
    for plan, rules, code in ((L.plan(), L.rules(), "STUDY_PLAN_SCHEMA_INVALID"),
                              (p, replace(L.rules(), fee_fraction=D("0.002")), "STRATEGY_RULES_MISMATCH")):
        L.refused(lambda: S.run_universe_capture(plan, rules=rules, source=outage,
                                                 clock=lambda: START - timedelta(days=1),
                                                 wait_until=lambda when: True, record=lambda line: None), code)


def test_universe_capture_size_bound_covers_the_worst_frame_and_refuses_long_windows():
    p = uplan(576)                                                            # 48 hours of 5-minute bars, 577 slots
    coins = ["KRW-Y" + format(n, "011d") for n in range(S.MAX_FRAME_MARKETS)]
    names, wide = {}, "9" * S.MAX_PRICE_CHARS
    frame = S._frame(START, START, SimpleNamespace(snapshot_sha256="1" * 64), {coin: "caution" for coin in coins},
                     {coin: (wide, -S.MAX_PRICE_OFFSET_MS) for coin in coins},
                     {coin: [wide, wide, wide, "e" * 64] for coin in coins[-16:]}, names, ())
    assert len(names) == S.MAX_FRAME_MARKETS and len(frame["flags"]) == len(frame["prices"]) == 320
    stamp = _plain(START)
    table_row = {"day": "2031-01-06", "valid_from": stamp, "valid_until": stamp, "top": coins[:2]}
    decision = {"bar_index": 576, "decided_at": stamp, "history_sha256": "e" * 64, "coin": coins[0], "fraction": "1"}
    archive = S.UniverseArchive(registry=p.registry, source_kind="prospective_paper_capture", markets=tuple(names),
                                snapshots={format(n, "064x"): table_row for n in range(4)}, frames=(frame,) * 577,
                                decisions=(decision,) * 576)
    actual, bound = len(S.universe_capture_json(archive)), S._universe_capture_bound(p)
    assert actual <= bound < actual + 65536 and bound <= S.UNIVERSE_CAPTURE_LIMIT and len(frame["books"]) == 16
    L.refused(lambda: uplan(864), "STUDY_UNIVERSE_CAPTURE_SIZE")             # 72 hours, 865 slots: about 13.03 MB
    assert S.MAX_FRAME_MARKETS == T.MAX_FRAME_MARKETS == 320
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
focus launch launch_universe_study/test_universe_capture
focus launch launch_universe_study/test_universe_book
focus launch launch_universe_study/test_universe_vanished
focus launch launch_universe_study/test_universe_deferred
```

Expected: exit 1 for each. The five new rows that run a `Feed`
(`test_universe_capture_records_frames_and_drives_the_chooser`,
`test_universe_book_selection_uses_only_earlier_frames`,
`test_universe_vanished_and_stale_books_fail_only_their_holders`,
`test_universe_deferred_sells_keep_their_book_requests` and `test_universe_capture_probe_stop_and_book_outage`,
whose `L.refused` catches only `ValueError`) FAIL with
`AttributeError: <module 'execution_launch.study' from '...'> does not have the attribute 'verify_universe_snapshot'`
(the module's full path in place of `...`), raised by `patch.object` in `Feed.run` before any capture code runs;
`test_universe_capture_size_bound_covers_the_worst_frame_and_refuses_long_windows` FAILs with
`AttributeError: module 'execution_launch.study' has no attribute 'MAX_FRAME_MARKETS'`. The first filter also matches
the two Task 5 rows `test_universe_capture_decoding_refuses_malformed_frames_and_decisions` and
`test_universe_capture_json_is_evaluated_and_assessed_like_the_fixed_one`, which still PASS.
`test_universe_deferred_sells_keep_their_book_requests` is the deferred-sell regression once Step 3 is in. With a
`_needed` that takes only the decisions index-1 and index-2 (no replayed paths), AAA is asked only at slots 3-5 in its
first case, and the row FAILs with `KeyError: 'KRW-AAA'` at the `books[i][AAA]` check for slot 6; on that capture the
evaluator would end with `STRATEGY_UNIVERSE_TERMINAL_BOOK_UNAVAILABLE`. With only the lag-2 replay, the first two
cases pass (the lag-2 path also holds AAA there) and the third, where only the lag-1 path holds AAA, FAILs with a bare
`AssertionError` at its `asked` assertion, AAA being asked only at slots 3-5.

- [ ] **Step 3: Implement** (CRLF file: every new and replaced line ends in `\r\n`)

In `execution_launch/study.py`, replace the line `from collections.abc import Mapping, Sequence` with:

```python
from collections import deque
from collections.abc import Mapping, Sequence
```

Replace the line `from datetime import datetime, timedelta, timezone` with:

```python
from datetime import datetime, timedelta, timezone
from decimal import Decimal
```

Replace the line `import time` with:

```python
import time
from types import SimpleNamespace
```

Replace the line `from core.isolation import checked_target` with:

```python
from core.compliance.rules import FLAG_CLASSES, universe_top_n, verify_universe_snapshot
from core.isolation import checked_target
```

Replace the line
`from execution_launch.program import ProgramSpec, parameters_json, parse_program, program_digest` with:

```python
from execution_launch.program import (ChooserSlot, ChooserState, ProgramSpec, choose, parameters_json, parse_program,
                                      program_digest)
```

Replace the `from execution_launch.strategy import (...)` statement written in Task 4 with:

```python
from execution_launch.strategy import (MAX_FRAME_MARKETS, MAX_PRICE_CHARS, MAX_PRICE_OFFSET_MS,
                                       UNIVERSE_CAPTURE_KIND, UNIVERSE_EVALUATOR_REVISION, ForwardProtocol,
                                       Registration, StrategyEvidenceError, ValidationResult, _BENCHMARK, _HASH, _ID,
                                       _MAX_BOOKS, _UniversePath, _date, _instant, _json, _object, _plain,
                                       _universe_rules, _universe_tables, _universe_view, assess_strategy,
                                       evaluate_capture_json, evidence_digest, parse_protocol, register_protocol)
```

Replace the line `_UNIVERSE_KIND = "universe_top1_momentum"` with:

```python
_UNIVERSE_KIND = "universe_top1_momentum"
_SNAPSHOT_SWITCH = timedelta(minutes=40)   # day D's snapshot is in force from D 00:40 UTC (09:40 KST), spec section 5
_MAX_SNAPSHOT_BYTES = 32 * 1024 * 1024     # one raw snapshot file read by the capture
```

In `validate_study_plan`, replace:

```python
    _feasible(protocols[0], plan.candidates)
    return evidence_digest(plan)
```

with:

```python
    _feasible(protocols[0], plan.candidates)
    _require(plan.selection_rule != UNIVERSE_SELECTION_RULE or _universe_capture_bound(plan) <= UNIVERSE_CAPTURE_LIMIT,
             "STUDY_UNIVERSE_CAPTURE_SIZE")
    return evidence_digest(plan)
```

Directly before the line `# -- selection ---...` (the section comment after `run_capture`), insert:

```python
# -- universe capture -------------------------------------------------------------------------------------------

@dataclass(frozen=True, kw_only=True)
class UniverseArchive:
    """One candidate's universe capture, the input of strategy's forward-universe-v1 evaluator: the market index,
    one table per snapshot in force (with this candidate's top-N), the shared frames and this candidate's
    decisions."""
    registry: tuple[Registration, ...]
    source_kind: str
    markets: tuple[str, ...]
    snapshots: dict
    frames: tuple
    decisions: tuple


def universe_capture_json(archive: UniverseArchive) -> str:
    """Canonical capture.json of a universe archive; refused above MAX_CAPTURE_BYTES, the select reader's cap."""
    _require(type(archive) is UniverseArchive, "STUDY_PLAN_SCHEMA_INVALID")
    body = {"kind": UNIVERSE_CAPTURE_KIND, "registry": _plain(archive.registry), "source_kind": archive.source_kind,
            "markets": list(archive.markets), "snapshots": archive.snapshots, "frames": list(archive.frames),
            "decisions": list(archive.decisions)}
    text = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n"
    _require(len(text) <= MAX_CAPTURE_BYTES, "STUDY_CAPTURE_JSON_TOO_LARGE")
    return text


def _quiet(call):
    """call(), or None when it raises: a failed public read or parse is recorded as unavailable (spec section 14)."""
    try:
        return call()
    except Exception:
        return None


def _on_time(read, slot):
    """An ok slot read received by the slot itself."""
    return read is not None and read.ok is True and _quiet(lambda: read.received_at <= slot) is True


def _raw(read):
    """A flag or ticker read for the receipts sink: ok, and the raw answer whenever one came back."""
    if read is None:
        return None
    if read.answer is None:
        return {"ok": read.ok}
    answer = read.answer
    return {"ok": read.ok, "received_at": _plain(answer.received_utc), "server_time": _plain(answer.server_utc),
            "sha256": answer.sha256, "raw_body_b64": base64.b64encode(answer.raw_body).decode("ascii")}


def _snapshot_in_force(source, slot, rule_sha256, days, seen, record):
    """The verified universe in force at slot, or None (spec section 5): day D's snapshot from D 00:40 UTC, checked
    against the protocol's rule. Each new raw file goes to the sink once and is verified once; a day with no
    verified snapshot is read again at the next slot; several verified files of one day give the earliest."""
    day = (slot.astimezone(timezone.utc) - _SNAPSHOT_SWITCH).date()
    if day not in days:
        found = []
        for raw in _quiet(lambda: source.snapshots(day)) or ():
            if type(raw) is not bytes:
                continue
            sha = hashlib.sha256(raw).hexdigest()
            if sha not in seen:
                record({"snapshot": base64.b64encode(raw).decode("ascii"), "sha256": sha})
                seen[sha] = _quiet(lambda: verify_universe_snapshot(raw, rule_sha256))
            if seen[sha] is not None and seen[sha].day == day:
                found.append(seen[sha])
        if found:
            days[day] = min(found, key=lambda u: (u.built_at, u.snapshot_sha256))
    universe = days.get(day)
    return universe if universe is not None and universe.valid_from <= slot < universe.valid_until else None


def _needed(paths, replays, index):
    """Coins whose books slot index needs (spec section 14): every candidate's decisions index-1 and index-2 and the
    coin each of its replayed lag-1, double-cost and lag-2 paths still holds, so a sell deferred for any number of
    slots keeps its request (decision index-3 is by then the lag-2 path's held coin, or a buy that never filled);
    cash skipped, plus the KRW-BTC benchmark. Three candidates need at most 3 x (2 + 3) + 1 = _MAX_BOOKS; a larger
    set is refused, never truncated."""
    needed = {path[k] for path in paths for k in range(max(index - 2, 0), index) if path[k] is not None}
    needed |= {path.held for group in replays for path in group if path is not None and path.held is not None}
    needed.add(_BENCHMARK)
    _require(len(needed) <= _MAX_BOOKS, "STUDY_CAPTURE_BOOKS_OVER_LIMIT")
    return needed


def _price_text(value):
    """A positive Decimal as frame text, or None when it exceeds MAX_PRICE_CHARS."""
    text = _quiet(lambda: _plain(value) if type(value) is Decimal and value > 0 else None)
    return text if type(text) is str and len(text) <= MAX_PRICE_CHARS else None


def _prices(read, slot):
    """market -> (price text, signed ms offset of its trade time from slot) for prices inside the frame maxima, or
    None when the ticker read is not ok and on time."""
    if not _on_time(read, slot):
        return None
    prices = {}
    for coin, pair in (_quiet(lambda: dict(read.prices)) or {}).items():
        text = _price_text(pair[0]) if type(pair) is tuple and len(pair) == 2 else None
        offset = _quiet(lambda: (pair[1] - slot) // timedelta(milliseconds=1))
        if text is not None and type(offset) is int and abs(offset) <= MAX_PRICE_OFFSET_MS:
            prices[coin] = (text, offset)
    return prices


def _book_rows(slot, asked, books, ticks):
    """Each asked coin's [bid, ask, tick, book sha256], or "unavailable" when the book or tick read, its parse or
    that market's checks failed, or the book is off its tick."""
    from execution_accounts.instrument_terms import parse_instruments
    from execution_accounts.quotes import parse_orderbooks

    quotes = (_quiet(lambda: parse_orderbooks(books, asked, slot)) if books is not None else None) or {}
    sizes = (_quiet(lambda: parse_instruments(ticks, asked)) if ticks is not None else None) or {}
    rows = {}
    for coin in asked:
        quote, tick = quotes.get(coin), sizes.get(coin)
        fits = _quiet(lambda: type(tick) is Decimal and quote.bid % tick == 0 and quote.ask % tick == 0) is True
        texts = [_price_text(value) for value in (quote.bid, quote.ask, tick)] if fits else [None]
        rows[coin] = texts + [quote.source_sha256] if None not in texts else "unavailable"
    return rows


def _frame(slot, sampled, universe, flags, prices, rows, names, top):
    """One compact frame (spec section 14). names maps each market to its index and only grows, up to
    MAX_FRAME_MARKETS: a book or price whose coin gets no index is left out, and a flag exception that gets none
    makes the whole flag read unavailable, never truncated."""
    def at(coin):
        if coin not in names and len(names) < MAX_FRAME_MARKETS:
            names[coin] = len(names)
        return names.get(coin)

    books = []
    for coin in sorted(rows):
        index, row = at(coin), rows[coin]
        if index is not None:
            books.append([index] + row if type(row) is list else [index, row])
    exceptions = None
    if flags is not None:
        marks = {coin: kind for coin, kind in flags.items() if kind != "unflagged"}
        marks.update((coin, "absent") for coin in top if coin not in flags)
        placed = [(at(coin), FLAG_CLASSES.index(kind if kind in FLAG_CLASSES else "unknown"))
                  for coin, kind in sorted(marks.items())]
        if all(index is not None for index, _ in placed):
            exceptions = sorted([index, kind] for index, kind in placed)
    priced = None
    if exceptions is not None and prices is not None:
        priced = []
        for coin, (text, offset) in sorted(prices.items()):
            index = at(coin)
            if index is not None:
                priced.append([index, text, offset])
        priced.sort()
    return {"observed_at": _plain(slot), "sampled_at": _plain(sampled),
            "snapshot": None if universe is None else universe.snapshot_sha256,
            "flags": exceptions, "prices": priced, "books": books}


def _chooser_slot(frame, order, top_n):
    """The chooser's view of one recorded frame: no flags and no prices when the flag read was unavailable;
    otherwise the top-N unflagged unless excepted, every exception's class, and the recorded prices."""
    if frame["flags"] is None:
        return ChooserSlot(top_n=top_n, flags={}, prices={})
    flags = dict.fromkeys(top_n, "unflagged") | {order[n]: FLAG_CLASSES[k] for n, k in frame["flags"]}
    prices = {order[n]: Decimal(text) for n, text, _ in frame["prices"] or ()}
    return ChooserSlot(top_n=top_n, flags=flags, prices=prices)


def _snapshot_tables(used, top_n):
    """capture.json's snapshot tables for one candidate: every snapshot in force so far, with that candidate's top-N."""
    return {sha: {"day": u.day.isoformat(), "valid_from": _plain(u.valid_from), "valid_until": _plain(u.valid_until),
                  "top": list(universe_top_n(u, top_n))} for sha, u in used.items()}


def _replays(paths, frame, markets, tables, slot, step, index, orders):
    """One candidate's replayed evaluator paths after frame index (spec section 14): the frame is decoded by the
    evaluator's own _universe_view and each path takes the evaluator's own step, so whether a sell executed (a
    usable book, a fill above the lot and minimums) is decided by the same code in capture and evaluator. A path the
    evaluator fails, or a frame it cannot decode, is dropped: that trial fails whatever is requested later."""
    try:
        view = _universe_view(frame, markets, _universe_tables(tables), slot, step)[0]
    except StrategyEvidenceError:
        return [None] * len(paths)
    kept = []
    for path in paths:
        try:
            if path is not None:
                path.step(index, view, orders, terminal=False)
        except StrategyEvidenceError:
            path = None
        kept.append(path)
    return kept


def _universe_archive(plan, n, names, used, frames, decisions):
    snapshots = _snapshot_tables(used, plan.candidates[n].program.max_candidates)
    return UniverseArchive(registry=plan.registry, source_kind="prospective_paper_capture", markets=tuple(names),
                           snapshots=snapshots, frames=tuple(frames), decisions=tuple(decisions[n]))


def _universe_capture_bound(plan):
    """An upper bound on the largest capture.json the plan can produce (spec section 14, size), computed with the
    capture's own encoder: the envelope with one table per calendar day the window can touch, plus slots worst-case
    frames (MAX_FRAME_MARKETS coins, every one flagged and priced at maximum length, _MAX_BOOKS = 16 books) and
    decisions. About 14.9 KB a frame: 577 slots (48 hours of 5-minute bars) fit 12 MiB, 865 (72 hours) do not."""
    protocol = plan.candidates[0].protocol
    slots = (protocol.capture_end - protocol.capture_start) // timedelta(seconds=protocol.bar_seconds) + 1
    widest = max(c.program.max_candidates for c in plan.candidates)
    names = ["KRW-Z" + format(n, "011d") for n in range(MAX_FRAME_MARKETS)]
    stamp, wide = _plain(protocol.capture_start), "9" * MAX_PRICE_CHARS
    frame = {"observed_at": stamp, "sampled_at": stamp, "snapshot": "f" * 64,
             "flags": [[n, len(FLAG_CLASSES) - 1] for n in range(MAX_FRAME_MARKETS)],
             "prices": [[n, wide, -MAX_PRICE_OFFSET_MS] for n in range(MAX_FRAME_MARKETS)],
             "books": [[n, wide, wide, wide, "f" * 64] for n in range(MAX_FRAME_MARKETS - _MAX_BOOKS, MAX_FRAME_MARKETS)]}
    fraction = max(len(_plain(c.program.exposure_fraction)) for c in plan.candidates)
    decision = {"bar_index": slots, "decided_at": stamp, "history_sha256": "f" * 64, "coin": names[-1],
                "fraction": "9" * fraction}
    days = (protocol.capture_end - protocol.capture_start) // timedelta(days=1) + 2
    table = {"day": "9999-12-31", "valid_from": stamp, "valid_until": stamp, "top": names[:1] * widest}
    base = UniverseArchive(registry=plan.registry, source_kind="prospective_paper_capture", markets=tuple(names),
                           snapshots={format(n, "064x"): table for n in range(days)}, frames=(frame,),
                           decisions=(decision,))
    return (len(universe_capture_json(base)) + (slots - 1) * len(_line(frame))
            + max(slots - 2, 0) * len(_line(decision)))


def run_universe_capture(plan: StudyPlan, *, rules, source, clock: Callable[[], datetime],
                         wait_until: Callable[[datetime], bool], record: Callable[[bytes], None]) -> CaptureOutcome:
    """Drive every rotation candidate's chooser over the frozen grid from one shared set of public reads per slot.

    rules are the plan's frozen InstrumentRules: each candidate's lag-1, double-cost and lag-2 evaluator paths are
    replayed on the recorded frames under them, so a coin a path still holds keeps its book request. source has
    read_flags(), read_tickers(markets), read_books(markets), read_ticks(markets) and snapshots(day).
    Before the window a late start or a failed flag probe refuses and nothing is recorded. Inside the window an
    unavailable flag, ticker, book or tick read is recorded and only blocks buys in the evaluator; a stop, a missed
    slot, a late sample or a sink failure ends the trial for every candidate, with the reason as the last line and
    the frames so far as the archives (spec section 14). _needed's _MAX_BOOKS guard would end it too, but three
    candidates never need more than _MAX_BOOKS books.
    """
    digest = validate_study_plan(plan)
    _require(plan.selection_rule == UNIVERSE_SELECTION_RULE, "STUDY_PLAN_SCHEMA_INVALID")
    for candidate in plan.candidates:
        _universe_rules(candidate.protocol, rules)          # the evaluator's own terms check, before any read
    protocol = plan.candidates[0].protocol
    _require(_clock_value(clock) <= protocol.capture_start - _START_MARGIN, "STUDY_CAPTURE_START_MISSED")
    probe = _quiet(lambda: source.read_flags())
    _require(probe is not None and probe.ok is True, "STUDY_PREWINDOW_PROBE_FAILED")
    _record(record, {"probe": _quiet(lambda: _raw(probe))})
    step = timedelta(seconds=protocol.bar_seconds)
    delay = timedelta(seconds=protocol.minimum_fill_delay_seconds)
    programs = [c.program for c in plan.candidates]
    widest = max(p.max_candidates for p in programs)
    windows = [deque(maxlen=p.lookback_slots + 1) for p in programs]
    states = [ChooserState(held=None, hold_count=0) for _ in programs]
    paths, decisions = [[] for _ in programs], [[] for _ in programs]
    orders, runs = [[] for _ in programs], ((1, 1), (2, 1), (1, 2))   # the evaluator's lag-1, double-cost, lag-2
    replays = [[_UniversePath(c.protocol, rules, cost_multiple=cost, lag=lag) for cost, lag in runs]
               for c in plan.candidates]
    names, frames, used, days, seen = {}, [], {}, {}, {}
    slots = (protocol.capture_end - protocol.capture_start) // step + 1
    recorded, reason, chain = 0, None, ""
    try:
        for index in range(slots):
            slot = protocol.capture_start + index * step
            universe = _snapshot_in_force(source, slot, protocol.universe_rule_sha256, days, seen,
                                          lambda body: _record(record, body))
            top = () if universe is None else universe_top_n(universe, widest)
            _require(wait_until(slot - _PREFETCH_LEAD), "STUDY_CAPTURE_STOPPED")
            _require(_clock_value(clock) < slot, "STUDY_CAPTURE_SLOT_MISSED")
            flag_read = _quiet(lambda: source.read_flags())
            flags = _quiet(lambda: dict(flag_read.flags)) if _on_time(flag_read, slot) else None
            if flags is not None and len(flags) > MAX_FRAME_MARKETS:
                flags = None                                  # recorded as unavailable, never truncated
            wanted = sorted(set(universe.listed) & set(flags)) if universe is not None and flags is not None else []
            ticker_read = _quiet(lambda: source.read_tickers(wanted)) if wanted else None
            needed = _needed(paths, replays, index)
            asked = sorted(needed if flags is None else needed & set(flags))
            books = _quiet(lambda: source.read_books(asked)) if asked else None
            ticks = _quiet(lambda: source.read_ticks(asked)) if asked else None
            _require(wait_until(slot), "STUDY_CAPTURE_STOPPED")
            sampled = _clock_value(clock)
            _require(slot <= sampled and sampled + delay <= slot + step, "STUDY_CAPTURE_DECISION_TOO_LATE")
            prices = _prices(ticker_read, slot) if flags is not None else None
            rows = _book_rows(slot, asked, books, ticks) | {coin: "vanished" for coin in needed - set(asked)}
            frame = _frame(slot, sampled, universe, flags, prices, rows, names, top)
            if universe is not None:
                used[universe.snapshot_sha256] = universe
            frames.append(frame)
            chain = evidence_digest((chain, frame))
            if index < slots - 1:
                for n, program in enumerate(programs):
                    windows[n].append(_chooser_slot(frame, list(names), top[:program.max_candidates]))
                    lag = windows[n][0] if len(windows[n]) == program.lookback_slots + 1 else None
                    coin, states[n] = choose(program, states[n], windows[n][-1], lag)
                    fraction = _plain(program.exposure_fraction) if coin else "0"
                    paths[n].append(coin)
                    orders[n].append((coin, Fraction(fraction)))
                    decisions[n].append({"bar_index": index, "decided_at": _plain(sampled), "history_sha256": chain,
                                         "coin": coin, "fraction": fraction})
                    if index:                                    # the evaluator steps frames 1 onwards
                        replays[n] = _replays(replays[n], frame, list(names),
                                              _snapshot_tables(used, program.max_candidates), slot, step, index,
                                              orders[n])
            _record(record, {"slot": index, "observed_at": _plain(slot), "flags": _quiet(lambda: _raw(flag_read)),
                             "tickers": _quiet(lambda: _raw(ticker_read)), "books": _quiet(lambda: _receipt(books)),
                             "ticks": _quiet(lambda: _receipt(ticks)),
                             "decisions": [[p.strategy_id, path[-1] if index < slots - 1 else None]
                                           for p, path in zip(programs, paths)]})
            recorded += 1
    except KeyboardInterrupt:
        reason = "STUDY_CAPTURE_STOPPED"
    except ValueError as exc:
        reason = _reason(exc)
    archives = tuple(_universe_archive(plan, n, names, used, frames, decisions) for n in range(len(programs)))
    if reason is None:
        _record(record, {"end": None})
        return CaptureOutcome(plan_digest=digest, complete=True, reason=None, slots_recorded=recorded,
                              archives=archives)
    try:
        record(_line({"end": reason}))
    except Exception:
        pass                                   # the trial has already failed; the sink's failure is not hidden
    return CaptureOutcome(plan_digest=digest, complete=False, reason=reason, slots_recorded=recorded,
                          archives=archives)


```

Check the line endings:

```bash
"$PY" -B -c "b=open('execution_launch/study.py','rb').read(); assert b.count(b'\n') == b.count(b'\r\n'), 'mixed'"
```

- [ ] **Step 4: Run the tests to verify they pass**

```bash
focus launch launch_universe_study/
focus launch launch_study/
focus launch launch_guards/
```

Expected: exit 0 for each. `launch_study/test_study_reads_clock_only_in_main_and_has_no_endpoint_literal` still
PASSes: the new code reads no clock outside `main`, holds no endpoint literal, imports the account readers only
inside `_book_rows`, and the manifest equals the new `CAPTURE_FILES`.

- [ ] **Step 5: Commit**

```bash
git add execution_launch/study.py tests/launch_universe_study.py
diff <(git diff --cached --stat) <(git diff --cached --stat --ignore-cr-at-eol)
git commit -m "$(cat <<'EOF'
feat(study): universe capture with compact frames and a freeze size check

run_universe_capture reads the snapshot in force, the market flags, the
listed coins' tickers and one batch of books and ticks for the coins the
candidates' last two decisions need, the coin each candidate's replayed
lag-1, double-cost and lag-2 evaluator paths still hold (so a sell deferred
for any number of slots keeps its book) and KRW-BTC, at most 16 books;
records raw bodies to receipts.jsonl and compact frames to capture.json,
and feeds each candidate's chooser from earlier frames only; a failed read
is recorded as unavailable, a vanished coin as vanished (universe spec
section 14). Freeze refuses a universe plan whose computed worst-case
capture exceeds 12 MiB: 48 hours of 5-minute bars fit, 72 hours do not.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
)"
```

Expected: the `diff` prints nothing; the commit succeeds.

---

### Task 7: Command-line capture of a universe plan

**Files:**
- Modify: `execution_launch/study.py` (CRLF; module docstring lines 1-2, 5, 8 and 22-24 at fd85850; `_COMMANDS`
  lines 74-75 and `_arguments` lines 495-508; a new section before `def main(`; the `capture` branch of `main`, lines
  638-666 at fd85850)
- Test: `tests/launch_universe_study.py` (append)

**Interfaces:**
- Consumes: `run_universe_capture`, `universe_capture_json` (Task 6); `read_orderbooks` (Task 1),
  `read_instruments` (Task 2), `UniverseSlotSource` (PR 2), `owner.universe_dir` (PR 1).
- Produces: `python -m execution_launch.study capture --plan PLAN.json --profile PROFILE.json --out DIR` runs a
  universe plan through `run_universe_capture` with the profile's frozen instrument rules, the real public readers
  and the owner's snapshot folder, writing `receipts.jsonl` and one `<study_id>.capture.json` (or
  `.incomplete.json`) per candidate; `select` evaluates those files unchanged. `_arguments` accepts the optional
  `--profile` for `capture` only (`_OPTIONAL`); a universe plan without it, or a fixed plan with it, is
  `STUDY_ARGUMENTS_INVALID`, and the fixed capture command line is unchanged.

- [ ] **Step 1: Write the failing test**

Append to the end of `tests/launch_universe_study.py`:

```python


# -- command line --------------------------------------------------------------------------------------------------

def test_cli_universe_capture_then_select_on_the_capture_alone():
    p = uplan()
    feed = Feed(p, scripted(RULES_ROWS), flags=RULES_FLAGS, tickers_down=(5,))
    end = p.candidates[0].protocol.capture_end

    class SlotSource:
        def __init__(self, *, clock):
            assert callable(clock)

        def read_flags(self):
            return feed.read_flags()

        def read_tickers(self, markets):
            return feed.read_tickers(markets)

    def sleep(seconds):
        assert 0 < seconds <= 1.0
        feed.now[0] = feed.now[0] + timedelta(seconds=seconds)

    with tempfile.TemporaryDirectory(prefix="launch_universe_") as directory:
        root = Path(os.path.realpath(directory))
        for day, raw in SNAPSHOT_RAW.items():
            folder = root / "universe" / day.isoformat()
            folder.mkdir(parents=True)
            (folder / (hashlib.sha256(raw).hexdigest() + ".json")).write_bytes(raw)
        plan_path, profile_path, out = root / "plan.json", root / "profile.json", root / "out"
        plan_path.write_text(S.study_plan_json(p), encoding="utf-8")
        profile_path.write_text(json.dumps(profile_body(uprofile()), indent=2), encoding="utf-8")
        out.mkdir()
        with ExitStack() as stack:
            stack.enter_context(patch("execution_accounts.universe.UniverseSlotSource", SlotSource))
            stack.enter_context(patch("execution_accounts.quotes.read_orderbooks",
                                      lambda markets, *, clock: feed.read_books(markets)))
            stack.enter_context(patch("execution_accounts.instrument_terms.read_instruments",
                                      lambda markets, *, clock: feed.read_ticks(markets)))
            stack.enter_context(patch("core.compliance.owner.universe_dir",
                                      lambda day: root / "universe" / day.isoformat()))
            stack.enter_context(patch.object(S, "verify_universe_snapshot", verify))
            stack.enter_context(patch.object(S, "time", SimpleNamespace(sleep=sleep)))
            stack.enter_context(patch.object(S, "datetime", SimpleNamespace(now=lambda tz: feed.now[0])))
            bare = root / "bare"
            bare.mkdir()
            code, report, _ = L.invoke("capture", "--plan", str(plan_path), "--out", str(bare))
            assert code == 2 and report["reasons"] == ["STUDY_ARGUMENTS_INVALID"], report   # rules come from --profile
            code, report, raw = L.invoke("capture", "--plan", str(plan_path), "--profile", str(profile_path),
                                         "--out", str(out))
        assert code == 0 and report["workflow_complete"] and report["slots_recorded"] == 61, report
        assert report["reasons"] == [] and report["execution_ready"] is False and str(root) not in raw
        study_id = p.candidates[0].protocol.study_id
        assert sorted(path.name for path in out.iterdir()) == sorted(["receipts.jsonl", study_id + ".capture.json"])
        lines = (out / "receipts.jsonl").read_bytes().split(b"\n")
        assert len(lines) == 66 and lines[-1] == b"" and json.loads(lines[-2]) == {"end": None}
        assert [n for n, line in enumerate(lines[:-1]) if "snapshot" in json.loads(line)] == [1, 10]
        with patch.dict(T._EVALUATED, clear=True):
            code, report, raw = L.invoke("select", "--plan", str(plan_path), "--profile", str(profile_path),
                                         "--captures", str(out), "--now", _plain(end + timedelta(seconds=60)))
        assert code == 0 and report["evaluation"] == {study_id: "EVALUATED"}, report
        assert report["selection"]["status"] == "NO_QUALIFIED_MARKET" and report["execution_ready"] is False
        assert report["review_requests"] == []
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
focus launch launch_universe_study/test_cli_universe
```

Expected: exit 1; the row FAILs with an `AssertionError` on the first `assert code == 2 ...`: the universe plan
without `--profile` still reaches the fixed capture path, which refuses it with reasons `["STUDY_PLAN_SCHEMA_INVALID"]`
(since Task 4), not `["STUDY_ARGUMENTS_INVALID"]`.

- [ ] **Step 3: Implement** (CRLF file: every new and replaced line ends in `\r\n`)

In `execution_launch/study.py`, replace the docstring line:

```python
    python -m execution_launch.study capture --plan PLAN.json --out NEW_EMPTY_DIR
```

with (the profile is for a universe plan only):

```python
    python -m execution_launch.study capture --plan PLAN.json [--profile PROFILE.json] --out NEW_EMPTY_DIR
```

Replace the first two docstring lines:

```python
"""Prospective single-market study: a frozen candidate family, a scheduled public-orderbook capture and a frozen
selection rule. Offline unless main() is asked to capture.
```

with:

```python
"""Prospective study of one market, or of a top-1 rotation over the Upbit KRW universe: a frozen candidate family,
a scheduled public capture and a frozen selection rule. Offline unless main() is asked to capture.
```

Replace the docstring line:

```python
Freeze: K moving-average programs over one complete private profile and one template protocol become K registered
```

with (a universe plan's programs are not moving-average programs):

```python
Freeze: K candidate programs over one complete private profile and one template protocol become K registered
```

Replace the three docstring lines:

```python
Only main() reads a wall clock or constructs the E1 public quote source. Nothing here signs, arms, places an
order, reads a credential or looks up a home directory; the only writes are new exclusive files inside an explicit
empty local output directory (the writer is pinned in tests/launch_guards.py). Every refusal is one fixed code.
```

with:

```python
Only main() reads a wall clock or constructs the E1 public sources: the quote source, or for a universe plan the
flag, ticker, book and tick readers and the read-only snapshot folder core.compliance.owner.universe_dir. A universe
plan's capture also reads --profile, for its frozen instrument rules only: the capture replays each candidate's
evaluator paths on the recorded frames so a deferred sell keeps its book. Nothing here signs, arms, places an order
or reads a credential; the only writes are new exclusive files inside an explicit empty local output directory (the
writer is pinned in tests/launch_guards.py). Every refusal is one fixed code.
```

Replace:

```python
_COMMANDS = {"freeze": ("profile", "draft", "out"), "capture": ("plan", "out"),
             "select": ("plan", "profile", "captures", "now")}
```

with:

```python
_COMMANDS = {"freeze": ("profile", "draft", "out"), "capture": ("plan", "out"),
             "select": ("plan", "profile", "captures", "now")}
_OPTIONAL = {"capture": ("profile",)}     # a universe plan's capture replays the evaluator under the profile's rules
```

In `_arguments`, replace:

```python
    names = _COMMANDS.get(values[0])
    _require(names is not None and len(values) == 1 + 2 * len(names), "STUDY_ARGUMENTS_INVALID")
    output = {}
    for key, value in zip(values[1::2], values[2::2]):
        _require(key.startswith("--") and key[2:] in names and key[2:] not in output and value
                 and not value.startswith("--"), "STUDY_ARGUMENTS_INVALID")
        output[key[2:]] = value
    return values[0], output
```

with:

```python
    names = _COMMANDS.get(values[0])
    allowed = () if names is None else names + _OPTIONAL.get(values[0], ())
    _require(names is not None and len(values) % 2 == 1 and len(names) <= len(values) // 2 <= len(allowed),
             "STUDY_ARGUMENTS_INVALID")
    output = {}
    for key, value in zip(values[1::2], values[2::2]):
        _require(key.startswith("--") and key[2:] in allowed and key[2:] not in output and value
                 and not value.startswith("--"), "STUDY_ARGUMENTS_INVALID")
        output[key[2:]] = value
    _require(set(names) <= set(output), "STUDY_ARGUMENTS_INVALID")
    return values[0], output
```

Directly before the line `def main(argv: list[str] | None = None) -> int:` insert:

```python
def _snapshot_files(directory):
    """Raw snapshot files of one universe day folder: regular, link-free .json files of at most _MAX_SNAPSHOT_BYTES,
    in name order. A missing or unreadable folder is no snapshot (the capture records the slot without one)."""
    try:
        found = []
        for path in sorted(directory.iterdir()):
            if (path.suffix == ".json" and not path.is_symlink() and path.is_file()
                    and path.stat().st_size <= _MAX_SNAPSHOT_BYTES):
                with path.open("rb") as stream:
                    found.append(stream.read(_MAX_SNAPSHOT_BYTES + 1))
        return found
    except OSError:
        return []


def _universe_source(clock):
    """The capture's public reads for a universe plan (spec section 14): flags and tickers through the slot source,
    batch books and ticks through the account-free readers, and the owner's verified snapshot folder."""
    from core.compliance import owner
    from execution_accounts.instrument_terms import read_instruments
    from execution_accounts.quotes import read_orderbooks
    from execution_accounts.universe import UniverseSlotSource

    slot_source = UniverseSlotSource(clock=clock)
    return SimpleNamespace(read_flags=slot_source.read_flags, read_tickers=slot_source.read_tickers,
                           read_books=lambda markets: read_orderbooks(markets, clock=clock),
                           read_ticks=lambda markets: read_instruments(markets, clock=clock),
                           snapshots=lambda day: _snapshot_files(owner.universe_dir(day)))


```

In `main`, replace:

```python
            plan = parse_study_plan(_read_file(args["plan"], _MAX_PLAN_BYTES))
            from execution_accounts.quotes import E1UpbitQuoteSource
```

with:

```python
            plan = parse_study_plan(_read_file(args["plan"], _MAX_PLAN_BYTES))
            universe = plan.selection_rule == UNIVERSE_SELECTION_RULE
            _require(universe == ("profile" in args), "STUDY_ARGUMENTS_INVALID")    # rules for a universe plan only
            rules = (parse_profile_json(_read_file(args["profile"], MAX_CONFIG_BYTES)).instrument_rules if universe
                     else None)
            from execution_accounts.quotes import E1UpbitQuoteSource
```

and replace:

```python
            source = E1UpbitQuoteSource(symbol=plan.candidates[0].protocol.symbol, clock=clock)
            sink = _Sink(directory)
            try:
                outcome = run_capture(plan, book_source=source.read, clock=clock, wait_until=wait_until, record=sink)
            finally:
                sink.close()
            suffix = ".capture.json" if outcome.complete else ".incomplete.json"
            for candidate, archive in zip(plan.candidates, outcome.archives):
                _write_new(directory, candidate.protocol.study_id + suffix, capture_json(archive).encode("ascii"))
```

with:

```python
            source = None if universe else E1UpbitQuoteSource(symbol=plan.candidates[0].protocol.symbol, clock=clock)
            sink = _Sink(directory)
            try:
                if universe:
                    outcome = run_universe_capture(plan, rules=rules, source=_universe_source(clock), clock=clock,
                                                   wait_until=wait_until, record=sink)
                else:
                    outcome = run_capture(plan, book_source=source.read, clock=clock, wait_until=wait_until,
                                          record=sink)
            finally:
                sink.close()
            encode = universe_capture_json if universe else capture_json
            suffix = ".capture.json" if outcome.complete else ".incomplete.json"
            for candidate, archive in zip(plan.candidates, outcome.archives):
                _write_new(directory, candidate.protocol.study_id + suffix, encode(archive).encode("ascii"))
```

Check the line endings:

```bash
"$PY" -B -c "b=open('execution_launch/study.py','rb').read(); assert b.count(b'\n') == b.count(b'\r\n'), 'mixed'"
```

- [ ] **Step 4: Run the tests to verify they pass**

```bash
focus launch launch_universe_study/
focus launch launch_study/
focus launch launch_guards/
```

Expected: exit 0 for each; the fixed CLI tests (`launch_study/test_cli_...`) still PASS with the KRW-BTC source,
including their argument refusals (`launch_study.py:576-580` at fd85850: a missing `--out`, an `--extra` key and a
repeated key are still `STUDY_ARGUMENTS_INVALID`).

- [ ] **Step 5: Commit**

```bash
git add execution_launch/study.py tests/launch_universe_study.py
diff <(git diff --cached --stat) <(git diff --cached --stat --ignore-cr-at-eol)
git commit -m "$(cat <<'EOF'
feat(study): capture command runs universe plans with the public readers

study capture sends a universe plan to run_universe_capture with the
frozen instrument rules of --profile (required for a universe plan and
refused for a fixed one), the slot flag and ticker source, the batch book
and tick readers and the owner's snapshot folder, and writes universe
capture.json files that select evaluates with forward-universe-v1
(universe spec section 14). The fixed KRW-BTC path is unchanged.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
)"
```

Expected: the `diff` prints nothing; the commit succeeds.

---

### Task 8: Draft tooling carries prior attempts

**Files:**
- Modify: `tools/research/prepare_shortened_study.py` (LF; docstring lines 41-47 and body lines 65-70 at fd85850)
- Test: `tests/launch_shortened_study.py` (append), `tests/launch_universe_study.py` (append)
- Verify only: `tools/research/prepare_launch_example.py`

**Interfaces:**
- Consumes: `_draft` names with `prior_attempts`, `build_study_plan(..., prior_attempts=...)` (Task 4); the size
  check (Task 6).
- Produces: `prepare_draft` passes the draft's `prior_attempts` to the new plan and keeps them in the emitted draft
  (the key is written only when non-empty, so a draft without retries is byte-identical to today's); a universe
  draft shortens to 48 hours under the universe rule and passes the size check.

- [ ] **Step 1: Write the failing tests**

Append to the end of `tests/launch_shortened_study.py`:

```python


def test_prior_attempts_pass_through_the_new_draft_into_every_family():
    body = json.loads(draft())
    body["prior_attempts"] = ["old-48h-study.fixture-ma-1-2-a"]
    raw, plan = prepare(json.dumps(body))
    assert json.loads(raw)["prior_attempts"] == ["old-48h-study.fixture-ma-1-2-a"]
    assert all(len(c.protocol.family_members) == 4 and "old-48h-study.fixture-ma-1-2-a" in c.protocol.family_members
               for c in plan.candidates)
    assert "prior_attempts" not in json.loads(prepare()[0])
```

Append to the end of `tests/launch_universe_study.py`:

```python


# -- draft tooling -------------------------------------------------------------------------------------------------

def test_shortened_universe_draft_keeps_the_rule_and_fits_the_size_check():
    from tools.research import prepare_shortened_study as P
    raw = json.dumps({"schema_version": 1, "plan_id": "unexecuted-universe-draft", "asset": "KRW-UNIVERSE",
                      "risk_group": "crypto-krw", "template": json.loads(protocol_json(utemplate(2016))),
                      "programs": [json.loads(program_json(ROTATION))]})
    now = START - timedelta(days=1)
    draft, plan = P.prepare_draft(uprofile(), raw, now=now, capture_start=now + timedelta(minutes=10),
                                  plan_id="new-universe-48h-draft", study_id="new-universe-48h-study")
    assert plan.selection_rule == S.UNIVERSE_SELECTION_RULE
    assert plan.candidates[0].protocol.minimum_observations == 576
    assert S._universe_capture_bound(plan) <= S.UNIVERSE_CAPTURE_LIMIT
    assert "prior_attempts" not in json.loads(draft)
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
focus launch launch_shortened_study/test_prior_attempts
focus launch launch_universe_study/test_shortened_universe
```

Expected: the first exits 1 (`KeyError: 'prior_attempts'` on the emitted draft); the second exits 0 already,
because `prepare_draft` passes the template through and Tasks 4 and 6 made the plan a universe plan. It stays as the
tooling regression test for the spec's draft tooling item.

- [ ] **Step 3: Implement**

In `tools/research/prepare_shortened_study.py`, replace the docstring lines:

```python
    Only the identities, registration time, window and observation requirement
    change. All candidate programs and other template settings are retained.
    Existing build_study_plan binds current private capital, fee and rule terms,
    installed sources and the prior negative research digest as usual.
```

with:

```python
    Only the identities, registration time, window and observation requirement
    change. All candidate programs and other template settings are retained.
    Existing build_study_plan binds current private capital, fee and rule terms,
    installed sources and the prior negative research digest as usual. The
    draft's prior_attempts (earlier attempts of the same selection) are kept
    and join every protocol's family, so retries count in K.
```

Replace:

```python
    plan = build_study_plan(profile, programs, template=revised, plan_id=plan_id,
                            asset=names["asset"], risk_group=names["risk_group"])
    body = {"schema_version": 1, "plan_id": plan_id, "asset": names["asset"],
            "risk_group": names["risk_group"], "template": json.loads(protocol_json(revised)),
            "programs": [json.loads(program_json(program)) for program in programs]}
    return json.dumps(body, sort_keys=True, indent=2) + "\n", plan
```

with:

```python
    plan = build_study_plan(profile, programs, template=revised, plan_id=plan_id,
                            asset=names["asset"], risk_group=names["risk_group"],
                            prior_attempts=names["prior_attempts"])
    body = {"schema_version": 1, "plan_id": plan_id, "asset": names["asset"],
            "risk_group": names["risk_group"], "template": json.loads(protocol_json(revised)),
            "programs": [json.loads(program_json(program)) for program in programs]}
    if names["prior_attempts"]:
        body["prior_attempts"] = list(names["prior_attempts"])
    return json.dumps(body, sort_keys=True, indent=2) + "\n", plan
```

- [ ] **Step 4: Run the tests to verify they pass, and verify the example tool**

```bash
focus launch launch_shortened_study/
focus launch launch_universe_study/
focus launch launch_workflow/
```

Expected: exit 0 for each. `launch_workflow` covers `tools/research/prepare_launch_example.py`, which builds a fixed
launch example (no study draft) and needs no change in this PR.

- [ ] **Step 5: Commit**

```bash
git add tools/research/prepare_shortened_study.py tests/launch_shortened_study.py tests/launch_universe_study.py
diff <(git diff --cached --stat) <(git diff --cached --stat --ignore-cr-at-eol)
git commit -m "$(cat <<'EOF'
feat(tools): shortened study drafts carry prior attempts

prepare_draft passes the draft's prior_attempts into the new plan, so every
family counts earlier attempts, and keeps them in the emitted draft only
when present (universe spec section 14). A universe draft shortens to 48
hours under the universe rule and fits the capture size check.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
)"
```

Expected: the `diff` prints nothing; the commit succeeds.

---

### Task 9: Doc amendments

**Files:**
- Modify: `docs/launch-workflow.md` (LF; lines 158-161, 165 and after 189 at fd85850)
- Modify: `docs/remaining-market-readiness-2026-11-06.md` (LF; lines 34-35)
- Modify: `docs/upbit-quote-contract.md` (LF; lines 25-29)
- Modify: `docs/instrument-term-renewal.md` (LF; lines 20-26)
- Modify: `docs/quote-timing-diagnostics.md` (LF, Korean; append an English section)

**Interfaces:**
- Consumes: the behaviour of Tasks 1-8.
- Produces: no code. Every sentence that said the study or these readers are single-market now says what the
  universe study adds.

- [ ] **Step 1: Amend `docs/launch-workflow.md`**

Replace:

```markdown
`execution_launch.study` runs the prospective single-market study: a frozen
candidate family, a scheduled public-orderbook capture and the frozen selection
rule from the [market selection protocol](market-selection-protocol.md). It has
three commands:
```

with:

```markdown
`execution_launch.study` runs a prospective study of one fixed market, or of a
top-1 rotation over the Upbit KRW universe: a frozen candidate family, a
scheduled public capture and the frozen selection rule from the
[market selection protocol](market-selection-protocol.md). It has three
commands:
```

In the `sh` block that follows, replace the line:

```sh
python -m execution_launch.study capture --plan PLAN.json --out NEW_EMPTY_DIR
```

with (the profile is for a universe plan only):

```sh
python -m execution_launch.study capture --plan PLAN.json [--profile PROFILE.json] --out NEW_EMPTY_DIR
```

After the paragraph that ends with `` such a request and signs `review-approve` on it; no study result is ever ``
and `` `execution_ready`. `` (line 189 at fd85850), insert one blank line and:

```markdown
Universe plans (selection rule `upbit-krw-universe-top1-v1`) freeze at most
three `universe_top1_momentum` candidates bound to the signed universe rule's
sha256, and their `capture` also takes `--profile PROFILE.json` for the frozen
instrument rules. At each slot the capture reads the market flags, the listed
coins' last trades, and one batch of at most 16 books and ticks: the coins of
the candidates' last two decisions, the coin each candidate's lag-1,
double-cost and lag-2 evaluator paths still hold (the capture replays those
paths under the frozen rules, so a sell deferred for any number of slots keeps
its book), plus KRW-BTC. A failed read is recorded as unavailable and blocks
buys only, and a needed coin missing from the flag read is recorded as
vanished. `capture.json`
holds a market index, one table per snapshot in force and compact frames; the
raw snapshot, flag and ticker bodies go to `receipts.jsonl`. `freeze` refuses a
plan whose computed worst-case capture exceeds 12 MiB
(`STUDY_UNIVERSE_CAPTURE_SIZE`): with a worst-case frame of about 15 KB the
bound admits about 835 slots, so 48 hours of 5-minute bars (577 slots) fit and
72 hours (865 slots) do not. `select` replays each capture with the
`forward-universe-v1` evaluator. Earlier attempts of the same selection go in
the draft's `prior_attempts` and count in every protocol's family. The study
does not model the preparation-time odds check, the keyed order-chance refusals
or time with no armed session.
```

- [ ] **Step 2: Amend `docs/remaining-market-readiness-2026-11-06.md`**

Replace:

```markdown
[market selection](market-selection-protocol.md). No cross-market Sharpe or
"most validated assets" conclusion follows from the current single-market scope.
```

with:

```markdown
[market selection](market-selection-protocol.md). No cross-market Sharpe or
"most validated assets" conclusion follows from the fixed single-market studies.
A universe study (`forward-universe-v1`) tests one top-1 rotation rule over the
Upbit KRW universe per family member; the coin it picks at a slot is not a
separate market result.
```

- [ ] **Step 3: Amend `docs/upbit-quote-contract.md`**

Replace:

```markdown
Only the selected symbol varies. There are no free-form URLs, foreign Upbit
hosts, batches, aggregation levels, or ticker substitutions. Existing E1
allowlists gain only this exact GET and its public classification. POST, DELETE,
plural/suffixed paths, and `/v1/orderbook/instruments` remain refused. Existing
account collection and snapshot polling do not automatically call this source.
```

with:

```markdown
Only the selected symbol varies. This source sends no free-form URLs, foreign
Upbit hosts, batches, aggregation levels, or ticker substitutions. Existing E1
allowlists gain only this exact GET and its public classification. POST, DELETE,
plural/suffixed paths, and `/v1/orderbook/instruments` remain refused. Existing
account collection and snapshot polling do not automatically call this source.

The universe study capture uses a separate batch reader,
`execution_accounts.quotes.read_orderbooks(symbols, clock=...)`: the same GET
with up to sixteen distinct KRW markets joined by commas in `markets`, level 0 and
count 30, and no route or keys. `parse_orderbooks(receipt, symbols, now)` checks
the receipt as a whole (path, exact parameters, scope, digest, the 10-second
receipt age and the server clock), then applies the single-market book checks to
each market on its own, so one stale, crossed, missing or repeated market is a
refusal code for that market only; a row for a market that was not asked for
refuses the whole read. The live runner still uses `E1UpbitQuoteSource` and
`parse_orderbook`.
```

- [ ] **Step 4: Amend `docs/instrument-term-renewal.md`**

Replace:

```markdown
The signed E1 allowlist adds exactly those two GETs. `execution/upbit_inquiry.py`
retains their literal paths and constructs the exact single-market query. No
```

with:

```markdown
The signed E1 allowlist adds exactly those two GETs. `execution/upbit_inquiry.py`
retains their literal paths and constructs the exact single-market query for this
source. No
```

and after the line `of selecting E1's legacy `.env` fallback and changing the reviewed account binding.` insert
one blank line and:

```markdown
The universe study capture reads ticks with a separate account-free reader,
`execution_accounts.instrument_terms.read_instruments(symbols, clock=...)`: the
same public instruments GET with up to sixteen distinct KRW markets, through
`execution.upbit_inquiry.orderbook_instruments`. `parse_instruments(receipt,
symbols)` checks the receipt as a whole and applies the single-instrument checks
(KRW quote, native level `"0"`, a positive tick) to each market on its own; a
failing market is a refusal code for that market only. It returns a tick per
market, never `InstrumentRules`: lot, minimums, fees and the authority stay with
the keyed `E1UpbitTermsSource`, which is unchanged.
```

- [ ] **Step 5: Append to `docs/quote-timing-diagnostics.md`**

The file is Korean UTF-8 with LF endings; append an English section with Python on bytes (no Korean text needs to be
typed):

```bash
"$PY" -B -X utf8 -c "
p = 'docs/quote-timing-diagnostics.md'
b = open(p, 'rb').read()
assert b.endswith(b'\n') and b'\r' not in b
section = (b'\n## Universe study batches (2026-11-11)\n\n'
           b'The universe study capture reads up to sixteen KRW books in one public GET\n'
           b'(\`execution_accounts.quotes.read_orderbooks\`) and checks each market on its own\n'
           b'(\`parse_orderbooks\`), with the same 10-second book rule as this diagnostic. The\n'
           b'single-market diagnostic above is unchanged and does not cover batches.\n')
open(p, 'ab').write(section)
"
tail -n 7 docs/quote-timing-diagnostics.md
```

Expected: the `tail` shows the new heading and four lines, with backticks around the two names.

- [ ] **Step 6: Check and commit**

```bash
"$PY" -B -c "import sys; bad = [p for p in sys.argv[1:] if b'\r' in open(p, 'rb').read()]; print(bad); sys.exit(1 if bad else 0)" docs/launch-workflow.md docs/remaining-market-readiness-2026-11-06.md docs/upbit-quote-contract.md docs/instrument-term-renewal.md docs/quote-timing-diagnostics.md
git add docs/launch-workflow.md docs/remaining-market-readiness-2026-11-06.md docs/upbit-quote-contract.md docs/instrument-term-renewal.md docs/quote-timing-diagnostics.md
diff <(git diff --cached --stat) <(git diff --cached --stat --ignore-cr-at-eol)
git commit -m "$(cat <<'EOF'
docs: universe study, batch book and tick readers

The launch workflow, market readiness, quote contract, term renewal and
quote timing documents now describe the universe study and its batch
readers next to the single-market paths they kept (universe spec
section 18).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
)"
```

Expected: the first command prints `[]`; the `diff` prints nothing; the commit succeeds.

---

### Task 10: Guards, full suite and pull request

**Files:**
- No code change. Read-only checks, then push and open the PR.

**Interfaces:**
- Consumes: Tasks 1-9.
- Produces: the pushed branch and an open PR against `main`. Never merge.

- [ ] **Step 1: Run the guards**

```bash
focus compliance compliance_guards/
focus control control_guards/
focus accounts accounts_guards/
focus launch launch_guards/
focus execution execution_guards/
focus launch launch_study/
focus compliance compliance_tables/
```

Expected: exit 0 for each (`control_guards` includes the `renewal_boundaries` pin checks and their negative
controls).

- [ ] **Step 2: Run the full suite**

```bash
"$PY" -X utf8 -m tests.run_all
```

Expected: no FAIL row beyond any listed in Task 0 Step 3 (there were none there; any FAIL now is this PR's to fix).

- [ ] **Step 3: Confirm the branch content**

```bash
git log --oneline origin/main..HEAD
git diff --stat origin/main..HEAD
git diff --stat --ignore-cr-at-eol origin/main..HEAD
git status --short
```

Expected: nine commits (Tasks 1-9); the two `--stat` outputs are identical; `git status` lists only the untracked
`docs/superpowers` files.

- [ ] **Step 4: Push and open the PR**

```bash
git push -u origin claude/universe-pr5-study
gh pr create --base main --head claude/universe-pr5-study --title "Universe study: forward-universe-v1, capture, batch parsers, prior attempts" --body "$(cat <<'EOF'
## Summary

Upbit KRW universe stage 1, PR 5 (spec sections 14 and 18; the program kind and chooser landed in PR 4b).

- `execution_accounts/quotes.py`: `read_orderbooks` (one keyless batch GET, up to sixteen KRW books) and
  `parse_orderbooks` (receipt checked as a whole, the single-market checks and the 10-second book rule per market).
- `execution_accounts/instrument_terms.py`: `read_instruments` and `parse_instruments` (a tick per market, never
  `InstrumentRules`); the renewal initialization pin is updated after review, reviewed bodies unchanged.
- `execution_accounts/universe.py`: flag and ticker reads keep their raw `Answer` for the receipts sink.
- `execution_launch/strategy.py`: the `forward-universe-v1` evaluator over compact universe captures (two-slot
  switches, top-N, flag and book buy blocks, deferred sells, ticker marks, disclosed failures for vanished, unmarked
  and terminal-unbooked coins and an unmarkable benchmark), sharing order arithmetic, metrics and result registration
  with `forward-paper-v1`, whose results are unchanged. Each run is a `_UniversePath` stepped one decoded frame
  at a time.
- `execution_launch/study.py`: study rule `upbit-krw-universe-top1-v1`, rotation feasibility
  `(returns - L + 1) // max(m, 2)`, `prior_attempts` in every family, at most three candidates, the 12 MiB freeze
  size check (computed with the capture's own encoder: 48 hours of 5-minute bars fit, 72 hours do not, so a
  72-hour universe study is refused at freeze; the live 72-hour `UNIVERSE_WINDOW_MAX` is unchanged),
  `run_universe_capture` and the `capture` command wiring (`--profile` for a universe plan); `CAPTURE_FILES` gains
  `instrument_terms.py`, `universe.py` and `core/compliance/rules.py`, so every new plan binds a new capture digest.
  Each slot asks for the books of every candidate's last two decisions and of the coin each of its lag-1,
  double-cost and lag-2 evaluator paths still holds, replayed with the evaluator's own `_UniversePath` under the
  frozen rules, so a sell deferred for any number of slots keeps its book; at most 3 x (2 + 3) + 1 = 16 books by
  construction (`STUDY_CAPTURE_BOOKS_OVER_LIMIT` is a guard that no plan within the candidate cap reaches).
- `tools/research/prepare_shortened_study.py`: drafts carry `prior_attempts`.
- Docs: launch workflow, market readiness, quote contract, term renewal and quote timing.

## Tests added

- `tests/accounts_quotes.py`: per-market batch books, whole-read refusals, the batch GET.
- `tests/launch_instrument_refresh.py`: per-market batch instruments, whole-read refusals, the batch GET.
- `tests/accounts_universe.py`: slot reads keep the raw answer.
- `tests/launch_universe_study.py` (new): feasibility, one family member per rotation, `prior_attempts` in K, the
  candidate cap, the A, A, B, B lag-2 switch with the terminal bar, buy blocks, ticker marks, deferred sells, a
  vanished non-held coin, a coin vanished only on the lag-2 path, an unavailable terminal book and benchmark,
  decoding refusals (16 books decode, 17 do not), frame causality of book selection, the warning exit through rule
  1, a failed ticker frame, one stale book among several, sells deferred on both paths, a coin held only on the
  lag-2 path and one held only on the lag-1 path, each keeping its book request and selling at the first usable
  book, the 16-book bound and its guard, probe failure, stop, book outage and a rules mismatch, the worst-case size
  at 577 slots and a refused 72-hour window, and a CLI capture with `--profile` (refused without it) followed by
  `select` on the capture alone.
- `tests/launch_shortened_study.py`: `prior_attempts` pass through the shortened draft.

## Not verified

- Upbit's acceptance of several markets in one orderbook or instruments GET (spec section 17 measurement); the
  one-request-per-market fallback is not implemented.
- Real snapshot verification inside the capture (tests stub `verify_universe_snapshot`), real read latency of four
  public GETs inside the 5-second prefetch lead, and E1 pacing under that load.
- The time of the per-slot replay of up to nine evaluator paths (after the sample, before the next prefetch);
  spec section 17 measures it with the chooser update.
- The study still does not model the odds check, the keyed order-chance refusals or time with no armed session.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

Expected: `gh` prints the PR URL. Do not merge; the owner merges on GitHub.
