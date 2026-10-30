# Odds engine plan: execution ledger

The executor's record of the TRADEGEN odds engine plan (LF). Task 1 started it; every task adds its drift
rulings, deferred minors and runs here. It stays untracked until Task 19 commits it.

## Base
- Branch `odds-engine`, cut from main `f3bedd3` (Merge pull request #3 from xkg4real/compliance-followup) on 2026-10-29.
- The plan was written against main `5816d3c` (equal to `995534b` outside docs/).
- Files changed outside docs/ since `5816d3c` (`git diff --stat 5816d3c HEAD -- . ':!docs'`), where the DRIFT
  RULE can apply:

```text
 README.md                     |    4 +-
 core/compliance/alerts.py     |   10 +-
 core/compliance/kr_rules.yaml |    2 +-
 core/compliance/owner.py      |   52 +-
 core/compliance/rules.py      |   33 +-
 core/ficc/data.py             |    2 +-
 data/krx/kis_client.py        |    1 +
 qa/acceptance_results.json    | 2232 +++++++++++++++++++++--------------------
 tests/compliance_cli.py       |   25 +-
 tests/compliance_guards.py    |  134 ++-
 tests/compliance_isolation.py |   36 +
 tests/compliance_signer.py    |  103 +-
 tests/compliance_store.py     |   77 +-
 tests/compliance_tables.py    |  183 +++-
 tools/signer/sign.py          |   78 +-
 15 files changed, 1802 insertions(+), 1170 deletions(-)
```

## Merged line numbers (Task 1; cited by line in the contract as of 995534b)
- `core/compliance/owner.py`: `_module_file` 761-769; `code_files` 789-815, its glob seed 795
- `tests/compliance_tables.py`: `test_venue_shape_rules` 710-748, its `minimum_krw` line 739
- `tests/compliance_store.py`: `TABLES` 22; `NOW` .. `_full_home` 317-374; `test_code_files_is_the_import_closure` 131-151
- `tests/compliance_guards.py`: `test_suite_is_registered_in_run_all_and_readme` 554-563; `_suite_names` 547-551; `_dynamic_module` 166-170
- `core/compliance/gate.py`: `_screen` 622-651, its start check 638, `Screening.flags` 644-651
- `tests/run_all.py`: the stdout reconfigure 35, the `--suite` help 113; `README.md`: the suite list 816
- Task 4 anchors at `f37661c`, before its edits: `tests/compliance_store.py` S2 import block end with `ROOT`/`TABLES` 18-22, S3 `NOW` .. `_full_home` 317-374 (+75 from the brief's 242-299, not "about 43"), S1 the closing `with` block of `test_decision_date_is_the_asia_seoul_date_of_now` 627-630; `tests/compliance_gate.py` G1 the closing `for module, scan` loop 1383-1386; `tests/compliance_fixtures.py` F1 `store_blob`'s last three lines 147-149; `core/compliance/owner.py` O1 `_context`'s `return model.seal_context(...)` 1036-1039; `core/compliance/rules.py` R1 `_calendar_line` 1064-1081; `core/compliance/gate.py` G2 `_screening`'s `return model.Screening(...)` 659-660

## Drift rulings
- Task 1: none. The three `tests/run_all.py` old texts (the `compliance_acceptance` import line, `tests()`, the `--suite` help) and the README `--suite macro` line were each found once, unchanged by the follow-up.
- Task 2: none. The four `core/compliance/rules.py` old texts (R1 `_VENUE_OPTIONAL` at :668 with `_venue` at :671, R2 `deposits` at :314, R3 `quote_for` at :324-326 with `VenueFacts` below, R4 the deposits loop end and `return Venue(...)` at :724-726) and the two `tests/compliance_tables.py` old texts (T1 the `minimum_krw` line at :739, T2 the end of `test_deposit_entries` at :768-769 and the "Hashes and the approved state" banner) were each found once, exactly as quoted (line numbers at 418d9bb, before this task's edits).
- Task 3: none. The three `core/odds/venues.yaml` old texts (V1 the header comment at :2-4, V2 the kis `quote_by_currency` / `deposits: []` / `source:` lines at :10-12, V3 the upbit BTC deposit line and `source:` at :19-20) and the `tests/compliance_tables.py` old text (T3 the closing `for kind in _T5_SHIPPED:` loop of `test_shipped_urls_come_from_the_research` at :1533-1537, the end of the file) were each found once, exactly as quoted (line numbers at bd6a51e, before this task's edits).
- Task 4: none. The eight old texts (S1, S2, S3 in `tests/compliance_store.py`; G1 in `tests/compliance_gate.py`; F1 in `tests/compliance_fixtures.py`; O1 in `core/compliance/owner.py`; R1 in `core/compliance/rules.py`; G2 in `core/compliance/gate.py`) were each found once, exactly as quoted; the follow-up's `import ast` sits above `import contextlib` and changed nothing inside `NOW` .. `_full_home`, so F1's moved copy carries no follow-up change. Only the brief's line hints were off (S3 at 317-374, +75, not about +43).
- Task 5: none in the tree. The one old text (the `finally:` restore `models.PILOT_PATHS, sim.TILT_PILOT, models.PILOT_NODES = saved` of `pilots()` in `tests/odds_fixtures.py`, Task 1's file) was found once, as the file's last line (:37 at 07bb309), and none of the 13 names the block adds existed before it. `core/odds/plan.py` and `tests/odds_plan.py` are new.
- Task 5: CONTRACT 3.2 series(start=None) ends the walk on 2026-10-22 (the contract wrote start="2024-01-01": 600 daily bars would end on 2025-08-22, so check_data would refuse every default series as stale).
- Task 5: CONTRACT 5.3 an empty legs list or a one-item list whose item is not a Leg is UNSUPPORTED_PRODUCT sub file; MULTI_LEG_UNSUPPORTED is returned only for 2 or more items (O3-6; also a spec 7.1 departure, listed in the plan header under "For spec rev 3.3").
- Task 5: CONTRACT 5.3 the garch_t plus edge_source "assumed" rule (sub edge) runs with the range rules, on every ctx, not only on a valid ctx.active.
- Task 5: CONTRACT 5.3 on a usable ctx.active a venue and section with no FEEDS entry is sub feed, right after sub symbol, so MARKET[(venue, section)] never raises in simulate.
- Task 5 (pre-flight P24): CONTRACT 5.3 lists the empty-or-non-Leg legs rule (sub file) before the range rules; check_plan reads the leg only after sub horizon (file for a non-Plan or a non-text name, track, numbers, start, horizon, then the leg), so `leg=()` with `horizon_days=0` is sub horizon, pinned in `test_product_refusals_come_in_the_contract_order`. MULTI_LEG_UNSUPPORTED still comes before every UNSUPPORTED_PRODUCT rule.
- Task 5 (pre-flight P25): Q24 step 7 names DATA_INVALID's subs as "series, sessions, `empty`, `stale`" and CONTRACT 5.3 as "series, stale, sessions, empty"; Q24's list is read as a set, and check_data runs the contract's (and the brief's) order: series, stale, sessions, empty, then SYNTHETIC_REFUSED (stale before sessions is pinned in `test_data_invalid_sessions_and_empty`).
- Task 6: none. No existing file is edited; every name the task reads from `core/compliance/rules.py` is there unchanged at 66acd15 (`COST_BOOKS` at :72, `Instrument` with `cost_book` at :278-288, `InstrumentMap.lookup` at :295, `Venue` with Task 2's `lot`, `min_order`, `fee_extras`, `tick_ladder` at :317-320 and `quote_for`, `lot_for`, `min_order_for`, `ladder_for` at :332-356), as are Task 5's `plan.OKX_CAP_KEY`, `REPLAY_SOURCE`, `Plan`, `Leg`, `Bracket`, `fixed`, `kelly`, `bold` and `OF.ODDS_VENUES`. `core/odds/costs.py` and `tests/odds_costs.py` are new and equal the brief's text byte for byte.

- Task 19 Cloud ruling: run on authorized gpt/odds-engine with Python 3.13.16 in /workspace/.venvs/tradegen. All Task 1-18 ledger hashes are ancestors of HEAD; descriptive commit subjects differ from the Windows draft but no task is absent. Task 7's original WIP subject is superseded by its recorded completed Cloud validation; history is not rewritten.
- Task 19 baseline: use the recorded branch point f3bedd3d24c3faa3b2881e8e515613e5b13a9c59, not the stale local origin/main reference (d9f4025) or an absent local main branch. Its record is 1055/1176 PASS, zero FAIL, 121 NOT_RUN; pre-run run_check correctly reports no odds rows and README matching that baseline.
- Task 19 Cloud ruling: all runs and the Q45 smoke use isolated TRADEGEN_HOME, as the owner's Cloud instruction and AGENTS actual-home write prohibition require. No local Windows daily job or user-PC smoke is claimed. Metadata watches protect the real default homes. The smoke still invokes __main__, blocks every network touchpoint and all four data seams, and requires exit 2 STATE_UNUSABLE with provenance.
- Task 19 Cloud ruling: preserve the existing GetConsoleMode test as one NOT_RUN on Linux, identified exactly by test id and reason in run_check. No other newly skipped test receives an exception. README names the actual Cloud Python 3.13 environment. Linux JSON output is converted to CRLF without changing parsed results.

## Deferred minors
- Task 2: the parser checks only that each odds-key source is non-empty text (CONTRACT 4.1); the source form of Q17 (a repo reference, an https URL of the research corpus, or the literal UNVERIFIED: owner to confirm before approval) is checked on the shipped draft only (Task 3), so an owner-signed venues file with source: x still parses VALID. For spec rev 3.3.
- Task 2: pre-flight P9 and P10 applied (controller rulings). P9: Step 4's route-name grep also checked `f_builtins`, `__globals__`, `get_referents`, `get_referrers`, `get_objects` and an attribute store of `TYPE_CHECKING`, `__name__` or `__class__` (all 16 names and the three stores of `owner._guards`); it printed nothing, and `owner._guards` on rules.py reads `(True, False, True)` before and after the change. P10: `test_venue_shape_rules` also refuses a YAML int key under `lot: units` (`5930`) and under `min_order: quote` (`5000`), the non-str key branches of `_odds_lot` and `_odds_min_order` (two lines inside the existing test; no new test function).
- Task 1: pre-flight P11 applied (controller ruling; `_CORE_ALSO_BANNED` is a tuple of module names): `tests/odds_guards.py` `_CORE_ALSO_BANNED` also holds linecache, filecmp, configparser, py_compile, winreg, scipy.datasets, logging and xml.etree (binds core/odds only, O3-1; stricter), its comment names them, and `import logging` left the allowed sample of `test_core_odds_imports_only_the_allowlist`, since logging is now refused (the positive-control loop over `_CORE_ALSO_BANNED` covers all eight). No later task's planned core/odds code imports any of them. Any other stdlib module that opens a file by path (netrc, mailbox, mimetypes among them) stays left to review.
- Task 1: P12 no change (Appendix A requires the copies of `tests()` and `_clock_hits_in`); P13 no change (Step 2's output read as interleaved tracebacks and lines: 15 tracebacks, the 3 PASS and 15 FAIL lines exactly as briefed, `3/18 passed, 15 failed, 0 not run`).
- Task 1 fix round 1 (commit c8dcc9b, controller ruling T1-R1-1..3, `tests/odds_guards.py` only, each stricter): `_CORE_ALSO_BANNED` also holds `_pyio`, `ntpath`, `posixpath` and `genericpath` (T1-R1-1); `_clock_hits_in` follows `from M import N as A` for every module, so `from email import utils as eu` / `eu.localtime()` and `from pandas import Timestamp as T` / `T.now()` are hits (T1-R1-2); `_main_hits` also flags `match __name__:` (T1-R1-3). Still 18 test functions; odds_guards/ and `--suite odds` both 18/18 passed, 0 failed, 0 not run.
- Task 1 fix round 2 (commit 2f5d2e1, controller ruling T1-RR1-1, `tests/odds_guards.py` only, stricter): `_clock_hits_in`'s Attribute check tests the raw name and its alias (the alias map is file-wide and the last import wins), so `import time` with a nested `from email import utils as time` or `import email.utils as time` and then `time.time()` is a hit again; both shadow cases are offenders in `test_core_odds_reads_no_clock`. Still 18 test functions; odds_guards/ and `--suite odds` both 18/18 passed, 0 failed, 0 not run.
- Task 1 fix round 3 (commit 418d9bb, re-review 2 of T1-RR1-1, `tests/odds_guards.py` only, stricter): `_clock_hits_in`'s alias map keeps every name an alias is imported as (a set per name, so no later import hides an earlier one), and the Attribute check tests the raw name and each of them; `import time as t` with a nested `from email import utils as t` or `import email.utils as t` and then `t.time()`, and `import email.utils as eu` with a nested `from datetime import date as eu` and then `eu.localtime()`, are hits and offenders in `test_core_odds_reads_no_clock`. Still 18 test functions; odds_guards/ and `--suite odds` both 18/18 passed, 0 failed, 0 not run.
- Task 1 left to review (after fix round 3): `_aliases` (the write guard's map, unchanged since 68082a5) also keeps only the last import of a name, so `import shutil as sh` with a nested `import json as sh` and then `sh.rmtree(d)` is not a hit (probe: []).
- Task 1 left to review (after fix round 2): an aliased constructor call (`from pandas import Timestamp as T` / `T('now')`, `from numpy import datetime64 as d` / `d('now')`) is not a hit, since the Call check matches the names `datetime64` and `Timestamp` only; and a `match` on anything but the bare name `__name__` (`match (__name__,):`) is not a hit.
- Task 2 left to the final review's fix wave (controller ruling on review minors T2-R1-1, T2-R1-2; code correct today):
  `test_venue_shape_rules` has no case for a non-list `tick_ladder` row of length 2 (`{"a": 0, "b": 1}`), a non-str
  book key, or a missing `books` or `phi_buy`; and `odds_sources` is tested only with all four odds keys or none, never
  some (one `lot`-only venue should give `(("lot", src),)`). Each fix is one stricter line inside an existing test.
- Task 3 left to the final review's fix wave (controller ruling on review minor T3-R1-3): the E2 and crypto research
  lookups in `tests/compliance_tables.py` use `str.splitlines()`, while the KIS lookup and `_t5_ref_ok` use
  `bytes.splitlines()`; a `\x0c`, `\x1c`-`\x1e` or `\x85` added to a research file before a cited line would move the
  index off the `#L` numbering (a false FAIL; it fails closed). Fix: `read_bytes().splitlines()`, decoded per line.
- Task 3 kept as briefed (review minors T3-R1-1, T3-R1-2; a YAML comment would move the venues sha pin): the 069500
  `lot` value comes from research line 163 (the plain 1x ETF/ETN row) while the key cites `#L161`; the test pins line
  163. The kis `min_order` `{KRW: 0}` is inferred from "Min ticket: 1 share" (the research states no money minimum).
  Owner act 3 confirms both before signing.
- Task 3: pre-flight P14 (controller ruling): the brief's Consumes list omits `_t5_date` (`from datetime import date as _t5_date`, `tests/compliance_tables.py:1106`, unchanged since `5816d3c`); `test_shipped_venue_odds_values_are_the_sourced_ones` uses it as the brief's code does (`_t5_date.fromisoformat`). No code change for the list itself.
- Task 3 left to review (pre-flight P15, limit (d)): the date pin `f"As of {day.day} {day:%B %Y}."` uses `%B`, whose month name follows the process's LC_TIME locale (C, so English, unless something calls `locale.setlocale`; nothing in tests/ or core/ does). A fixed English month tuple would only avoid a false FAIL under another locale and is not stricter (it catches the same wrong dates), so the brief's text is kept verbatim.
- Task 3: TASKS asks the card's NOT_TRADABLE refusal to name the owner act (explicit fee_extras, 0 allowed, the missing lots, approve the venues file); CONTRACT 10.4 why.NOT_TRADABLE does not, so only the plan header and Task 19 carry it. For the coordinator / spec rev 3.3.
- Task 4 left to review (pre-flight P17, controller ruling): `owner._calendar_approval` repeats `load_context`'s `now` check (the isinstance test, `iso_utc`, the Asia/Seoul date, OverflowError as ValueError) instead of sharing a helper; a shared helper would be a refactor of `load_context`, not stricter, so the brief's code is kept.
- Task 4: pre-flight P18 applied (controller ruling): `test_grey_rows_names_the_in_force_grey_rows_of_the_leg` also records the intent `grey_rows` hands `gate._in_force` for six legs (okx BTC and USDT, upbit BTC, kis 005930, 069500 and SPY) and asserts its `model.intent_hash` equals `gate.screen(leg, c, 1.0).decision.intent_hash`, so `grey_rows` decides the cash buy `screen()` builds (one assert inside the existing test; scratch mutants `notional_krw=2.0` and `action="sell"` in `grey_rows` fail it).
- Task 4: pre-flight P19 applied (controller ruling; no test or later brief pins the text): `owner_key` raises `owner_key: <path> is outside the temp home <home>` and, separately, `owner_key: <path> is outside the temp dir <tempdir>`; the refusals themselves are unchanged (both AssertionError before the pem is written).
- Task 4: pre-flight P20 accepted (controller ruling): `tests/compliance_fixtures.py` now imports `core.compliance.model` (stdlib only) at module level for `NOW` and `HELD`, so a `model.py` that fails to import takes down every test that imports the fixtures, `temp_home` users included; `owner` stays imported inside each helper.
- Task 4: pre-flight P21 applied (controller ruling): the same test gives the four `()` legs (upbit BTC, kis 005930, 069500, SPY) a positive control: with every venue row signed grey they name `KR-DOMESTIC-SPOT`, `KR-KIS-KRX-SHARE`, `KR-KIS-ETP-1X` and `KR-KIS-ETP-1X`, so their `()` means no grey row matches, not a failed lookup (scratch mutants that fail the upbit or the 069500/SPY lookup fail it).
- Task 4 (pre-flight P22): CONTRACT 3.3 erratum. Appendix A.3.3 says the signed-home helpers are "moved verbatim"; Task 4 adds three test-only guards to the moved copy (stricter: `owner_key` also refuses a pem outside the temp dir, `sign` a log outside the temp dir, `approve` a state root outside its `home`), the four `full_home` keywords, and docstrings that say so. For spec rev 3.3.
- Task 4 fix round 1 (controller ruling T4-R1-1): A.4.3's 'any exception -> (log, "")' binds calendar_in_force only; _calendar_approval keeps the narrow catch so --check exits 4 on an internal error (spec 5.4). For spec rev 3.3 and the CONTRACT erratum list.
- Task 4 fix round 1 (commit 07bb309, T4-R1-1): `owner._calendar_approval` catches `(OSError, ValueError, RuntimeError)` only; `owner.calendar_in_force` re-raises the `now` check's ValueError (the read's ValueError is already ("log", "")) and returns None on any other exception. `test_calendar_in_force_is_none_without_an_ok_owner_log` adds a TypeError from a patched `owner.store_get`: it propagates out of `_calendar_approval` while `calendar_in_force(NOW)` is None; its docstring and the old "any error but the ValueError fails closed" comment now say which function does what. `rules.py`'s `_calendar_line` comment is true again and unchanged. Probe (temp home, scratch): a TypeError in `store_get("calendar", ...)` makes `rules.main(["--check", "--today", "2026-10-24"])` print `check failed: TypeError: a bug` and exit 4. Scratch mutants: the old `except Exception` and a `calendar_in_force` without its catch each fail the test.
- Task 4 fix round 1 (commit 07bb309, T4-R1-2): `test_signed_home_helpers_are_the_public_fixtures` also points `owner.PUBKEY_PATH` at a second temp home and asserts `owner_key(home)` raises AssertionError and writes no pem, so the "inside home" half of the guard is pinned (a scratch `owner_key` without it fails the test with "AssertionError not raised"). No test function added.

- Task 4 left to the final review's fix wave (controller, after fix round 1): no repo test drives `rules.main(['--check', ...])` with an internal calendar error through to exit 4; the unit pin on
  `_calendar_approval` and `main()`'s existing exit-4 path cover it today (a scratch probe printed `check failed: TypeError: a bug` and exit 4). One end-to-end case inside an existing compliance_cli test would pin it.
- Task 5: pre-flight P23 applied (controller ruling): `test_product_refusals_come_in_the_contract_order` also holds one two-fault plan per pair of neighbouring `_product` rules that can both fail (track/numbers, numbers/start, horizon/empty legs, model/sizing, sizing/fraction, fraction/bracket, bracket/edge, edge/replay, replay/venue, class/multiple, multiple/tax, and the section feed before the class on a kis venue file that lists crypto). A scratch scan that swaps each pair of neighbouring rules found 11 of the 14 swaps survive the briefed tests (the pre-flight counted 6); with these cases all 14 fail the test. The pairs that cannot both fail (the empty-legs rule and model, venue and the okx feed, symbol and the section feed) are not cases. No test function added.
- Task 5: pre-flight P26 applied (controller ruling): `_usable`, `_real` and `_cap_ok` are checked against the gate's `_usable`, `_number` and `_cap` (through a stand-in row with `cap_key` okx_equity_share) on 8 states, 16 numbers and 15 caps, with the expected True/False pattern pinned too, inside `test_state_unusable_for_a_hand_built_context_a_broken_owner_or_an_invalid_state`, `test_data_invalid_series` and `test_an_okx_leg_needs_the_okx_cap`; scratch mutants of each helper fail their test.
- Task 5: pre-flight P29 applied (controller ruling): `test_multi_leg_unsupported_for_two_or_more_legs` refuses a `Leg` subclass (`_T5Leg`) as the leg, as a one-item tuple and as a one-item list, sub file; a scratch `_leg` that uses `isinstance` fails it.
- Task 5 (pre-flight P30, controller ruling: no change): `_real` refuses a numpy scalar price (`type(np.float64(1.0)) is float` is False), so a Series built from numpy scalars is DATA_INVALID sub series; `OF.series` converts with `float()`, and Task 15's loaders keep Python floats.
- Task 5 for the final review (controller ruling on review minors T5-R1-1, T5-R1-3, T5-R1-4; no change now):
  `check_plan` never checks that the venue lists the symbol (upbit `USDC` passes; `gate.screen` blocks it later as
  `malformed: counter_symbol`, so SCREEN_BLOCKED refuses with no probability shown, but `costs.terms` and the first
  stake run before it with `lot_for`'s default step); a `venue.is_market` rule (sub symbol) would only add a refusal.
  `plan_hash`, `plan.leg` and R assume loader-built plans: a direct caller passing `leg=(leg,)` or an int where the
  loader gives a float gets a second hash for the same plan (Task 18's loader normalizes both). `Refusal` and
  `ReplayInput` are frozen but unhashable (dict and Mapping fields) and only shallowly immutable.
- Task 6 (pre-flight P31, controller ruling, limit (d)): the two asserts that compare literals only stay as briefed (dropping an assert is not stricter): `assert steps[2][1] <= 100.0 <= steps[2][2]` in `test_band_keeps_the_price_inside_across_sessions` and `assert (1_999.0 + 2_003.0) / 2 == 2_001.0` in `test_why_the_ceiling_rests_on_the_gross_mark`; each states the premise of the case next to it.
- Task 6 (pre-flight P32, controller ruling: no change): the scalar `side_bp` / `ladder_tick` / `etf_tick` and the vector `_bp` / `_ticks` duplicate one arithmetic on purpose; the scalar forms are the oracles for the vector forms (`test_kappa_equals_side_bp_element_by_element`, `_tick_of` in the band tests).
- Task 6 (pre-flight P33, controller ruling: accepted): `test_terms_from_the_fixture_venues` pins the shipped kis KRX stock ladder (`effective_from` "2026-10-02" and the rows of `core/odds/venues.yaml`) a second time, by equality with `OF.ODDS_VENUES`, beside Task 3's pin in `tests/compliance_tables.py`. If the owner signs a better-sourced `effective_from` (O3-4), both pins and the fixture's ladder date move together, in one change.
- Task 6 for the final review (controller note T5-R1-1; no change, as briefed): `costs.terms` never refuses a symbol the venue does not list. A scratch probe over every (venue, symbol) of `OF.ODDS_VENUES` whose instrument the venue's sections hold but `venue.is_market(inst, venue.quote_for(inst))` is False found three, and each gets ordinary Terms with no exception: okx USDC and okx USDT (lot 1e-8 from `default`, min_krw 1,400 from USDT 1; USDT is then bought with USDT) and upbit USDC (lot 1e-8, min_krw 5,000). Nothing in `core/odds/costs.py` raises or misprices for them; `gate.screen` refuses the leg later (SCREEN_BLOCKED), so no probability is shown. A symbol the instrument map lacks never reaches `terms` (`check_plan` sub symbol), where `inst.cost_book` would raise AttributeError on None.
- Task 6 for the final review (observation, no change): the vector `_ticks` takes `steps[searchsorted(starts, q, "right") - 1]`, which wraps to the top row for a q below the first `price_from`, while the scalar `ladder_tick` raises NotTradable there. No parsed ladder can trigger it (`rules._odds_ladder` requires the first `price_from` to be exactly 0, the ETF rows start at 0.0, and `kappa` and `band` refuse a price that is not > 0); only a hand-built `Terms` with a ladder that starts above 0 could.
- Task 6 for the final review (controller ruling on review minors T6-R1-1..3; no change now): the vector `_ticks`
  in `core/odds/costs.py` takes the top row's tick for a price below the first `price_from` (index -1), where the
  scalar `ladder_tick` raises NotTradable (unreachable: the parser requires a first `price_from` of 0; a guard on
  idx < 0 would be stricter); the bold arithmetic is written twice (vector `rule_units`, scalar
  `net_win_coefficient`) and the OKX cap rule three times (costs, `gate._cap`, `plan._cap_ok`) with no parity test
  beyond `test_first_stake`'s caps; `floor_units`' +1e-9 lot tolerance can overshoot `afford`'s stake by at most
  1e-9 of a lot (sub-won), the same class as O3-22's OKX cap overshoot.

## Runs
- Task 1: -m tests.odds_acceptance odds_guards/: 18/18 passed, 0 failed, 0 not run
- Task 1: -m tests.odds_acceptance: 18/18 passed, 0 failed, 0 not run
- Task 1: tests/run_all.py --suite odds: 18/18 passed, 0 failed, 0 not run (odds_guards: 0.37 s of tests in all, budget 5 s)
- Task 1: -m tests.compliance_acceptance compliance_guards/: 16/16 passed, 0 failed, 0 not run
- Task 1: -m tests.compliance_acceptance compliance_store/: 29/29 passed, 0 failed, 0 not run
- Task 1: -m tests.compliance_acceptance compliance_signer/test_code_files_match_owner: 1/1 passed, 0 failed, 0 not run
- Task 1: -m tests.macro_m0_harness: 11/11 passed, 0 failed, 0 not run
- Task 1: -m tests.macro_tf_gov: 20/22 passed, 0 failed, 2 not run
- Task 1: -m tests.macro_m7_ledger: 14/18 passed, 0 failed, 4 not run
- Task 1: -m tests.macro_m8_forward: 17/23 passed, 0 failed, 6 not run
- Task 1: -m tests.macro_m6_context: 14/16 passed, 0 failed, 2 not run
- Task 1: tests/run_all.py --suite cockpit: 47/47 passed, 0 failed, 0 not run
- Task 1 count note (G3-1): the commit stat reads `tests/odds_guards.py | 792 +` and `7 files changed, 980 insertions(+), 3 deletions(-)`, not 790 and 978: P11 adds one comment line and one tuple line to `_CORE_ALSO_BANNED`. Every run count above equals the brief's.
- Task 2: -m tests.compliance_acceptance compliance_tables/: 69/69 passed, 0 failed, 0 not run
- Task 2: -m tests.compliance_acceptance compliance_gate/: 49/49 passed, 0 failed, 0 not run
- Task 2: -m tests.compliance_acceptance compliance_cli/: 36/36 passed, 0 failed, 0 not run
- Task 2: -m tests.compliance_acceptance compliance_guards/: 16/16 passed, 0 failed, 0 not run
- Task 2: -m tests.compliance_acceptance compliance_store/: 29/29 passed, 0 failed, 0 not run
- Task 2: -m tests.odds_acceptance odds_guards/: 18/18 passed, 0 failed, 0 not run
- Task 2: -m tests.macro_m0_harness: 11/11 passed, 0 failed, 0 not run
- Task 2: -m tests.macro_tf_gov: 20/22 passed, 0 failed, 2 not run
- Task 2: -m tests.macro_m7_ledger: 14/18 passed, 0 failed, 4 not run
- Task 2: -m tests.macro_m8_forward: 17/23 passed, 0 failed, 6 not run
- Task 2: -m tests.macro_m6_context: 14/16 passed, 0 failed, 2 not run
- Task 2: tests/run_all.py --suite cockpit: 47/47 passed, 0 failed, 0 not run
- Task 2: tests/run_all.py --suite compliance: 331/331 passed, 0 failed, 0 not run
- Task 2 count note (G3-1): Windows Developer Mode is on, so `compliance_tables/test_calendar_sha256_refuses_a_file_symlink` (and, in the suite, `compliance_isolation/test_symlinks_are_refused`) runs and passes instead of NOT_RUN. Step 2 (RED) printed the brief's five FAIL lines in its order and `64/69 passed, 5 failed, 0 not run` (brief: 63/69, 1 not run); Step 4 printed `69/69` (brief: 68/69, 1 not run) and `--suite compliance` `331/331, 0 not run` (brief: 329/331, 2 not run). Every other count equals the brief's. `test_venue_shape_rules` took 0.41 s (brief: about 0.5 s).
- Task 3: -m tests.compliance_acceptance compliance_tables/: 70/70 passed, 0 failed, 0 not run
- Task 3: -m tests.compliance_acceptance compliance_gate/: 49/49 passed, 0 failed, 0 not run
- Task 3: -m tests.compliance_acceptance compliance_cli/: 36/36 passed, 0 failed, 0 not run
- Task 3: -m tests.compliance_acceptance compliance_guards/: 16/16 passed, 0 failed, 0 not run
- Task 3: -m tests.compliance_acceptance compliance_store/: 29/29 passed, 0 failed, 0 not run
- Task 3: -m tests.macro_m0_harness: 11/11 passed, 0 failed, 0 not run
- Task 3: -m tests.macro_tf_gov: 20/22 passed, 0 failed, 2 not run
- Task 3: -m tests.macro_m7_ledger: 14/18 passed, 0 failed, 4 not run
- Task 3: -m tests.macro_m8_forward: 17/23 passed, 0 failed, 6 not run
- Task 3: -m tests.macro_m6_context: 14/16 passed, 0 failed, 2 not run
- Task 3: tests/run_all.py --suite cockpit: 47/47 passed, 0 failed, 0 not run
- Task 3: tests/run_all.py --suite compliance: 332/332 passed, 0 failed, 0 not run
- Task 3: core/odds/venues.yaml sha256 283c143f800b7ddc6db8b1b2dd77c8624da1a3e5d4a2fe9e4ca6dbec7dfa042a
- Task 3 count note (G3-1): Windows Developer Mode is on, so `compliance_tables/test_calendar_sha256_refuses_a_file_symlink` (and, in the suite, `compliance_isolation/test_symlinks_are_refused`) runs and passes instead of NOT_RUN. Step 2 (RED) printed the brief's FAIL line (`AssertionError: ()`) and `0/1 passed, 1 failed, 0 not run`, as briefed; Step 4's `compliance_tables/` printed `70/70` (brief: 69/70, 1 not run) and `--suite compliance` `332/332, 0 not run` (brief: 330/332, 2 not run). Every other count, the venues file's 57 lines and 2,799 bytes, its sha256 and the four grep lines equal the brief's.
- Task 4: -m tests.compliance_acceptance compliance_store/ (RED, after Step 1): 29/36 passed, 7 failed, 0 not run (the brief's seven FAIL lines, word for word)
- Task 4: -m tests.compliance_acceptance compliance_gate/ (RED, after Step 1): 49/51 passed, 2 failed, 0 not run (the brief's two FAIL lines, word for word)
- Task 4: -m tests.compliance_acceptance compliance_store/: 36/36 passed, 0 failed, 0 not run
- Task 4: -m tests.compliance_acceptance compliance_gate/: 51/51 passed, 0 failed, 0 not run
- Task 4: -m tests.compliance_acceptance compliance_cli/: 36/36 passed, 0 failed, 0 not run
- Task 4: -m tests.compliance_acceptance compliance_owner/: 52/52 passed, 0 failed, 0 not run
- Task 4: -m tests.compliance_acceptance compliance_signer/: 38/38 passed, 0 failed, 0 not run
- Task 4: -m tests.compliance_acceptance compliance_guards/: 16/16 passed, 0 failed, 0 not run
- Task 4: -m tests.odds_acceptance odds_guards/: 18/18 passed, 0 failed, 0 not run
- Task 4: -m tests.macro_m0_harness: 11/11 passed, 0 failed, 0 not run
- Task 4: -m tests.macro_tf_gov: 20/22 passed, 0 failed, 2 not run
- Task 4: -m tests.macro_m7_ledger: 14/18 passed, 0 failed, 4 not run
- Task 4: -m tests.macro_m8_forward: 17/23 passed, 0 failed, 6 not run
- Task 4: -m tests.macro_m6_context: 14/16 passed, 0 failed, 2 not run
- Task 4: tests/run_all.py --suite cockpit: 47/47 passed, 0 failed, 0 not run
- Task 4: tests/run_all.py --suite compliance: 341/341 passed, 0 failed, 0 not run
- Task 4: `owner._guards` on owner.py, rules.py and gate.py reads `(False, False, True)`, `(True, False, True)` and `(False, False, True)` before and after the change; the added core lines name none of its route names (nor `TYPE_CHECKING`, `__name__` or `__class__`).
- Task 4 count note (G3-1): Windows Developer Mode is on, so `compliance_isolation/test_symlinks_are_refused` and `compliance_tables/test_calendar_sha256_refuses_a_file_symlink` run and pass in the suite: `--suite compliance` printed `341/341, 0 not run` (brief: 339/341, 2 not run). Every other count equals the brief's. P18 and P21 add asserts inside an existing test only, so no count moves.
- Task 4 fix round 1: -m tests.compliance_acceptance compliance_store/ (RED, the TypeError case before the code): 35/36 passed, 1 failed, 0 not run (`FAIL compliance_store/test_calendar_in_force_is_none_without_an_ok_owner_log AssertionError: TypeError not raised`)
- Task 4 fix round 1: -m tests.compliance_acceptance compliance_store/: 36/36 passed, 0 failed, 0 not run
- Task 4 fix round 1: -m tests.compliance_acceptance compliance_cli/: 36/36 passed, 0 failed, 0 not run
- Task 4 fix round 1: -m tests.compliance_acceptance compliance_owner/: 52/52 passed, 0 failed, 0 not run
- Task 4 fix round 1: -m tests.compliance_acceptance compliance_guards/: 16/16 passed, 0 failed, 0 not run
- Task 4 fix round 1: -m tests.compliance_acceptance compliance_signer/: 38/38 passed, 0 failed, 0 not run
- Task 4 fix round 1: -m tests.odds_acceptance odds_guards/: 18/18 passed, 0 failed, 0 not run
- Task 4 fix round 1: -m tests.macro_m0_harness 11/11, macro_tf_gov 20/22 (2 not run), macro_m7_ledger 14/18 (4 not run), macro_m8_forward 17/23 (6 not run), macro_m6_context 14/16 (2 not run); 0 failed in each
- Task 4 fix round 1: tests/run_all.py --suite cockpit: 47/47 passed, 0 failed, 0 not run
- Task 4 fix round 1: tests/run_all.py --suite compliance: 341/341 passed, 0 failed, 0 not run (run twice; the second after a test-only exception-message edit)
- Task 4 fix round 1: `owner._guards` on owner.py, rules.py and gate.py still reads `(False, False, True)`, `(True, False, True)` and `(False, False, True)`; the added lines name none of its route names. Counts as Task 4's (G3-1 Developer Mode note above); every new check sits inside an existing test function.
- Task 5: -m tests.odds_acceptance odds_plan/ (RED, after Step 1): 0/1 passed, 1 failed, 0 not run (`FAIL odds_plan/import ImportError: cannot import name 'plan' from 'core.odds' (C:\Users\whydi\OneDrive\Desktop\TRADEGEN\core\odds\__init__.py)`, as briefed, exit 1)
- Task 5: -m tests.odds_acceptance odds_plan/: 25/25 passed, 0 failed, 0 not run (1.87 s of test calls, 1.1 s of it in the first test, which parses the fixture venue file first; brief about 2 s, pre-flight sandbox 1.14 s)
- Task 5: -m tests.odds_acceptance odds_guards/: 18/18 passed, 0 failed, 0 not run
- Task 5: -m tests.compliance_acceptance compliance_guards/: 16/16 passed, 0 failed, 0 not run
- Task 5: -m tests.compliance_acceptance compliance_store/: 36/36 passed, 0 failed, 0 not run
- Task 5: -m tests.macro_m0_harness 11/11, macro_tf_gov 20/22 (2 not run), macro_m7_ledger 14/18 (4 not run), macro_m8_forward 17/23 (6 not run), macro_m6_context 14/16 (2 not run); 0 failed in each
- Task 5: tests/run_all.py --suite cockpit: 47/47 passed, 0 failed, 0 not run
- Task 5: tests/run_all.py --suite odds: 43/43 passed, 0 failed, 0 not run (18 odds_guards + 25 odds_plan; run twice, the second after a test-only line rewrap)
- Task 5: both Step 4 raw-text greps printed nothing (exit 1). `owner.code_files` now lists 12 entries: `core/__init__.py`, the six `core/compliance` files, `core/isolation.py`, `core/odds/__init__.py`, `core/odds/plan.py` and the PyYAML and cryptography RECORDs.
- Task 5 count note (G3-1): none; every count equals the brief's (25/25; odds suite 18 + 25 = 43, as the controller pre-stated). Developer Mode touches none of these runs.
- Task 6: Step 1 inputs check: `inputs ok` (exit 0)
- Task 6: -m tests.odds_acceptance odds_costs/ (RED, after Step 1): 0/1 passed, 1 failed, 0 not run (`FAIL odds_costs/import ImportError: cannot import name 'costs' from 'core.odds' (C:\Users\whydi\OneDrive\Desktop\TRADEGEN\core\odds\__init__.py)`, as briefed, exit 1)
- Task 6: -m tests.odds_acceptance odds_costs/: 23/23 passed, 0 failed, 0 not run (the brief's 23 PASS lines, exit 0)
- Task 6: -m tests.odds_acceptance odds_guards/: 18/18 passed, 0 failed, 0 not run
- Task 6: -m tests.compliance_acceptance compliance_guards/: 16/16 passed, 0 failed, 0 not run
- Task 6: -m tests.compliance_acceptance compliance_store/: 36/36 passed, 0 failed, 0 not run
- Task 6: -m tests.macro_m0_harness 11/11, macro_tf_gov 20/22 (2 not run), macro_m7_ledger 14/18 (4 not run), macro_m8_forward 17/23 (6 not run), macro_m6_context 14/16 (2 not run); 0 failed in each
- Task 6: tests/run_all.py --suite cockpit: 47/47 passed, 0 failed, 0 not run
- Task 6: tests/run_all.py --suite odds: 66/66 passed, 0 failed, 0 not run (18 odds_guards + 25 odds_plan + 23 odds_costs; run twice, the second only to read the per-module seconds from the results file before its restore)
- Task 6: both Step 4 raw-text greps printed nothing (exit 1); the line-ending check printed `LF ok`; `git status --short` listed exactly the two new files and the ledger. `owner.code_files` now lists 13 entries (Task 5's 12 plus `core/odds/costs.py`).
- Task 6 time (A.3.4 target 2 s, G3-2): odds_costs 0.84 s of test calls inside `--suite odds` (odds_plan has already parsed the fixture venue file); run alone, 2.02 s and then 1.83 s (scratch timing through the suite's own `_wrap` and `run_all.run`); in the first of those, 0.78 s went to the first test, which parses the fixture venue file first. The first alone-run is 0.02 s over the target; nothing was changed for it. In the same suite runs odds_plan took 2.60 s (Task 5's module, target 2 s; Task 5 measured 1.87 s alone): it pays the fixture parse there, recorded only.
- Task 6 count note (G3-1): none; every count equals the brief's and the controller's pre-statement (23/23; odds suite 18 + 25 + 23 = 66). Developer Mode touches none of these runs.

## Cloud Task 7 attempt — 2026-10-30 (Codex)

- Source handoff ad9e5ac, code base 1a7eaba, WIP code commit 01f17a59a282adb667ce8fa849680a344226d019; branch gpt/odds-engine. **Task 7 is NOT complete; no new LEDGER ID.**
- Drift: none. Added models.py (209 lines) and odds_models.py (410 lines), byte-identical to Task 7 Steps 1/3. LF; staged stats with and without --ignore-cr-at-eol match; both required raw-text scans pass. Reviewed Q1/Q10/Q12/Q30/Q34/Q42, A.7.1/A.7.2 and the copied originals; no source deviation found.
- P34: complete run tails below. P35: all commands inherited KEYLESS values; imports can reach config/load_dotenv, but no real data API was used. Isolated state and fixture homes only.
- Cloud adaptation: Python 3.13.16, numpy 2.3.5, pandas 2.3.3, scipy 1.18.0; serial runs. The existing cloud runner redirects only OUT outside the tracked QA record, which remains byte-identical to baseline. No thresholds, seeds, assertions or skip markers changed.
- RED: odds_models 0/1, 1 failed, expected missing-model ImportError, exit 1. GREEN: odds_models 19/19, 0 failed, 0 not run, exit 0; test-call time in odds suite 0.7514 s (6 s budget).
- Task 7 odds-guards: 18/18 passed, 0 failed, 0 not run; exit 0; process wall time 3.38 s.
- Task 7 compliance-guards: 16/16 passed, 0 failed, 0 not run; exit 0; process wall time 5.781 s.
- Task 7 compliance-store: 33/36 passed, 3 failed, 0 not run; exit 1; process wall time 18.116 s.
- Task 7 macro-m0-harness: 11/11 passed, 0 failed, 0 not run; exit 0; process wall time 6.434 s.
- Task 7 macro-tf-gov: 20/22 passed, 0 failed, 2 not run; exit 0; process wall time 29.401 s.
- Task 7 macro-m7-ledger: 14/18 passed, 0 failed, 4 not run; exit 0; process wall time 7.889 s.
- Task 7 macro-m8-forward: 17/23 passed, 0 failed, 6 not run; exit 0; process wall time 10.451 s.
- Task 7 macro-m6-context: 14/16 passed, 0 failed, 2 not run; exit 0; process wall time 4.128 s.
- Task 7 cockpit: 45/47 passed, 2 failed, 0 not run; exit 1; process wall time 5.783 s.
- Task 7 odds: 85/85 passed, 0 failed, 0 not run; exit 0; process wall time 4.98 s.
- Baseline comparison: with both new Task 7 files absent, compliance_store again gives 33/36, 3 failed. All three directly import Windows-only _winapi at tests/compliance_store.py lines 86, 117 and 455. Before Task 7 edits, cockpit was 45/47 with the same two failures and odds was 66/66.
- Catalog failures: test_03 has no primary for us-undervalued-growth-screener (9 CLI scripts); test_35 misreads ACTIVE / PARTIALLY_CLOSED and JSON in core-portfolio-weekly step 2 as answer options. Cloud catalog cb0f3aadffed6d1089db4b224162c964368baa46 is a documented compatibility pin, not the owner's exact catalog.
- G3-1 and CURRENT section 6: FAIL never counts as passed; environment differences are reported, not repaired in this task. Task 8 did not start. Preserve the implementation as WIP under AGENTS section 4 (stopping/returning); request an owner ruling on a separate Linux-test/catalog-compatibility task. Do not mark odds-7 complete until the required checks pass.
- Machine-readable evidence: context/odds-engine/cloud-validation-2026-10-30.json. Raw logs: /workspace/tradegen-session in this cloud instance.

## Cloud compatibility and Task 7 completion — 2026-10-30 (Codex)

- Owner explicitly authorized the five existing fixes and necessary follow-on work. This supersedes the prior scope blocker, not the safety constraints.
- cloud-compat-1: preserve Windows junction coverage and assert real POSIX symlinks; select documented run_pipeline.py; exclude declarative preambles from answer choices, with regressions in existing test_36. No assertions, fixed constants or skip policies weakened.
- Final code 6d27d16: the verified index is restored after connector payload truncation in intermediate d107bf3. Git tree 33433a2f1e2faccefe42f7376b6dd81e70d42b5e, CRLF preserved.
- odds-7 is now COMPLETE, with the unchanged byte-identical Task 7 implementation at 01f17a5. Plan/self-review completed.
- Completion odds-guards: 18/18 passed, 0 failed, 0 not run; exit 0; 3.723 s.
- Completion compliance-guards: 16/16 passed, 0 failed, 0 not run; exit 0; 5.981 s.
- Completion compliance-store: 36/36 passed, 0 failed, 0 not run; exit 0; 20.12 s.
- Completion macro-m0-harness: 11/11 passed, 0 failed, 0 not run; exit 0; 6.131 s.
- Completion macro-tf-gov: 20/22 passed, 0 failed, 2 not run; exit 0; 27.841 s.
- Completion macro-m7-ledger: 14/18 passed, 0 failed, 4 not run; exit 0; 7.335 s.
- Completion macro-m8-forward: 17/23 passed, 0 failed, 6 not run; exit 0; 9.994 s.
- Completion macro-m6-context: 14/16 passed, 0 failed, 2 not run; exit 0; 4.178 s.
- Completion cockpit: 47/47 passed, 0 failed, 0 not run; /workspace/tradegen-session/task-7-cockpit.json; exit 0; 5.831 s.
- Completion odds: 85/85 passed, 0 failed, 0 not run; /workspace/tradegen-session/task-7-odds.json; exit 0; 5.279 s.
- QA record unchanged; all tests KEYLESS and serial with isolated state. GPT weekly quota unavailable, threshold 95%; checkpoint each task.

## Cloud Task 8 completion — 2026-10-30T15:12:04+09:00 (Codex)

- Code: 3e33aa94081bd98722d8d3b21eb63eae26a1d96d.
- Review: Task 8 두 원문 교체와 새 테스트에 바이트 단위로 일치. 복사 함수·상수·seed·경계·NaN 거부·호출 시 상수 조회를 자체 대조. 필수 raw scans와 LF 검증 통과.
- RED: odds_garch import fails because c_quad does not yet exist (0/1); GREEN: 17/17, wall 8.375 s including runner imports.
- Drift rulings: CONTRACT 7.4 checks deterministic first; the scaled-pilot test restores the real table before deterministic evaluation to isolate statistical failure.
- P83 / CONTRACT 7.3 erratum: GarchParams uses frozen=True, kw_only=True as Task 8 requires; all callers use keywords. _half_life is omitted because no field reads it.
- P36: the design-note claim that nu46 never crosses 22 applies only to the equality test stream, not the pilot stream. No misleading comment is present in the implemented test.
- P37: optional quad-panel deduplication deferred; it adds no stricter check, so the approved copy is retained.
- R2-9 margins on the real pilot stream, OFFSET 2e-6, RATIO_FACTOR 3.0, LOG_DRIFT 0.0:
    nu56 h30 nu 5.618: clean 2.2e-12 / 2.5e-11 z 1.64; offset 2.0e-06 / 6.0e-05; ratio x3 z 8.22; log drift 0 z 2.48
    nu56 h90 nu 5.618: clean 7.6e-11 / 3.9e-10 z 2.14; offset 2.0e-06 / 1.8e-04; ratio x3 z 12.34; log drift 0 z 7.51
    nu46 h30 nu 4.604: clean 7.3e-11 / 1.9e-09 z 1.21; offset 2.0e-06 / 6.0e-05; ratio x3 z 35.67; log drift 0 z 15.42
    nu46 h90 nu 4.604: clean 2.9e-10 / 1.8e-08 z 1.25; offset 2.0e-06 / 1.8e-04; ratio x3 z 68.26; log drift 0 z 23.24
- Deferred minor: nu46 pilot numbers differ slightly from drafting values on this CPU/library build, but all clean/corrupted checks have the required margins; no tolerance, seed or assertion changed.

- Task 8 odds-guards: 18/18 passed, 0 failed, 0 not run; exit 0; wall 3.827 s.
- Task 8 compliance-guards: 16/16 passed, 0 failed, 0 not run; exit 0; wall 5.931 s.
- Task 8 compliance-store: 36/36 passed, 0 failed, 0 not run; exit 0; wall 21.635 s.
- Task 8 macro-m0-harness: 11/11 passed, 0 failed, 0 not run; exit 0; wall 6.834 s.
- Task 8 macro-tf-gov: 20/22 passed, 0 failed, 2 not run; exit 0; wall 29.198 s.
- Task 8 macro-m7-ledger: 14/18 passed, 0 failed, 4 not run; exit 0; wall 7.385 s.
- Task 8 macro-m8-forward: 17/23 passed, 0 failed, 6 not run; exit 0; wall 10.145 s.
- Task 8 macro-m6-context: 14/16 passed, 0 failed, 2 not run; exit 0; wall 4.276 s.
- Task 8 cockpit: 47/47 passed, 0 failed, 0 not run; /workspace/tradegen-session/task-8-cockpit.json; exit 0; wall 6.135 s.
- Task 8 odds: 102/102 passed, 0 failed, 0 not run; /workspace/tradegen-session/task-8-odds.json; exit 0; wall 10.447 s.

## Cloud Task 9 completion — 2026-10-30T15:14:31+09:00 (Codex)

- Code: 84f67ad467254990a1729ea2d5b5c5a54ce4e84f.
- Review: 두 core 파일은 Task 9 원문과 바이트 일치. 진입·청산 우선순위, 비용별 gross-value 보존, seed stream 및 nan 비교를 대조. P38 exact-target 사례를 기존 테스트에 추가; P43 fixture 주석 교정. 후속 anchor와 고정값은 유지.
- RED: missing report ImportError, 0/1, exit 1. GREEN: odds_simulate 18/18, wall 4.085 s with suite imports; no tolerance changed.
- P38: added an exact target case to test_reached_counts_the_liquidation_value_after_exit_costs: 21 units at 1,000, cash 21,000, close 2,000 gives exactly 63,000. Pins first passage, REACHED, terminal >= and target rung. Remaining non-target cash_min/cap mutation gaps are left for final review / Task 10 cap coverage; no claim that every branch has discriminating tests.
- P39 / O3-18: run_column keeps x_range=nan; Task 14 _column computes bootstrap hidden_range. This is the existing ruling, not newly invented drift.
- CONTRACT 10.1 amendment: compare ColumnStats with brackets=None and x_range=0.0 only when nan; finite ranges are retained. Task 13 _strip must use this idiom.
- Task 9 cannot yet exercise buy-and-hold re-entry after daily loss or KRX stock sell tax; P1/P2 hand these to Task 10. Cost dates have no observable difference in these part-1 fixtures. P3 strengthens the remaining clip coverage in Task 10.
- P40: exact exp(log(2)) depends on the CPU numpy kernel; passes here. P41: measured times retained, no test weakened to meet a budget. P42: no refactor of _paths or run_column. P43: fixture header now describes only the functions below it, whose imports are local.

- Task 9 odds-plan: 25/25 passed, 0 failed, 0 not run; exit 0; wall 3.98 s.
- Task 9 odds-guards: 18/18 passed, 0 failed, 0 not run; exit 0; wall 3.524 s.
- Task 9 compliance-guards: 16/16 passed, 0 failed, 0 not run; exit 0; wall 6.18 s.
- Task 9 compliance-store: 36/36 passed, 0 failed, 0 not run; exit 0; wall 21.121 s.
- Task 9 macro-m0-harness: 11/11 passed, 0 failed, 0 not run; exit 0; wall 6.534 s.
- Task 9 macro-tf-gov: 20/22 passed, 0 failed, 2 not run; exit 0; wall 29.504 s.
- Task 9 macro-m7-ledger: 14/18 passed, 0 failed, 4 not run; exit 0; wall 7.237 s.
- Task 9 macro-m8-forward: 17/23 passed, 0 failed, 6 not run; exit 0; wall 9.794 s.
- Task 9 macro-m6-context: 14/16 passed, 0 failed, 2 not run; exit 0; wall 4.129 s.
- Task 9 cockpit: 47/47 passed, 0 failed, 0 not run; /workspace/tradegen-session/task-9-cockpit.json; exit 0; wall 5.93 s.
- Task 9 odds: 120/120 passed, 0 failed, 0 not run; /workspace/tradegen-session/task-9-odds.json; exit 0; wall 11.501 s.

## Cloud Task 10 completion — 2026-10-30T15:17:58+09:00 (Codex)

- Code: dc060ea417716def737a430aa667c4c4078bcf28.
- Review: core는 계획의 8개 교체와 정확히 일치. P1~P3를 기존 테스트 안에서 강화하고 메모리 내 오류 7종이 실제로 실패하는지 확인. 원본 함수 복구 및 파일 무변경 확인. 후속 anchor와 고정값 유지.
- RED: odds_locks 0/14, odds_simulate 16/18 exactly as planned. GREEN locks 14/14 wall 3.386 s including runner imports.
- P1: buy-and-hold daily-loss exit has entries=1, value=101,000, no unresolved bracket. Re-entry mutant caught.
- P2: exact KRX stock round trip on a 1,000-tick ladder pins buy charge, sell charge, 20 bp tax difference, minimum cash, total cost and terminal value. Buy-as-sell and sell-as-buy mutants caught.
- P3: hand-made component prices within dated bands exercise proportional rates >1 under stress/carry; exact clipped fill, locked-horizon value/cost and 30% delisting fee, retaining nonnegative assertions. The synthetic queued-release path isolates the state machine; stochastic absorbing-band law remains separately tested unchanged. Fill clip, horizon cost clip, liquidation clip and delisting clip mutants caught. Seven intended mutations caught, original _paths restored in finally; no code file mutated.
- P44 / O3-17 / contract 8.4 readings, all six: (1) every daily-loss breach stops further trading that date regardless of exit trigger; (2) worst_gap includes queued stop fills; (3) force_exit_from independently blocks entries; (4) delisting sale pays the normal fee at discounted sale price, no fee for total writeoff; (5) band edges count all path-sessions, including done paths, share divides by n*sessions; (6) KRX recognition uses costs.band finite upper bound instead of a duplicated book list.
- P45: duplicate horizon chi calculation retained, no unrelated refactor. Deferred minor: engine permits an entry at upper band U, while live order layer limit_up_locked refuses it; approved model distinction, not changed.

- Task 10 odds-simulate: 18/18 passed, 0 failed, 0 not run; exit 0; wall 3.775 s.
- Task 10 odds-guards: 18/18 passed, 0 failed, 0 not run; exit 0; wall 3.474 s.
- Task 10 compliance-guards: 16/16 passed, 0 failed, 0 not run; exit 0; wall 6.435 s.
- Task 10 compliance-store: 36/36 passed, 0 failed, 0 not run; exit 0; wall 22.184 s.
- Task 10 macro-m0-harness: 11/11 passed, 0 failed, 0 not run; exit 0; wall 6.081 s.
- Task 10 macro-tf-gov: 20/22 passed, 0 failed, 2 not run; exit 0; wall 28.904 s.
- Task 10 macro-m7-ledger: 14/18 passed, 0 failed, 4 not run; exit 0; wall 8.49 s.
- Task 10 macro-m8-forward: 17/23 passed, 0 failed, 6 not run; exit 0; wall 11.804 s.
- Task 10 macro-m6-context: 14/16 passed, 0 failed, 2 not run; exit 0; wall 4.628 s.
- Task 10 cockpit: 47/47 passed, 0 failed, 0 not run; /workspace/tradegen-session/task-10-cockpit.json; exit 0; wall 6.032 s.
- Task 10 odds: 134/134 passed, 0 failed, 0 not run; /workspace/tradegen-session/task-10-odds.json; exit 0; wall 12.048 s.

## Cloud Task 11 completion — 2026-10-30T15:20:25+09:00 (Codex)

- Code: d7db1d2dcd25f1782c6c44be032d86916e503893.
- Review: core는 Task 11 원문과 바이트 일치. O3-9 최종 판정과 exact Fraction 계산, 99.9% CP 비교, 비용별 동적계획 검사를 대조. P46 회계 불변식 주석, P47 도달 가능한 양성 대조, P48 fair 표현 반영.
- RED: missing bold ImportError, 0/1, exit 1. GREEN: odds_bold 12/12, wall 4.881 s including suite imports.
- RULINGS_ROUND3 O3-9 directly verified: rungs=(k,k,k,0,k), mean-excess bound, one 20,000-path chunk, no second run, CP level 0.999. No reseed or changed probability threshold. Calendar interfaces fixture_set/sessions_between/regime_tags match the consumed contract.
- P46: retained count-sum assertion with an accounting-invariant comment; it does not prove a particular outcome split. P47: strengthened existing input test positive control with reachable target 63,000 and strict value>0; no count change, anchor or pin touched. P48: engine bracket description says fair bet; the separate exact even-money game terminology remains correct.
- Core import list is exactly future/fractions/math/numbers/numpy; both banned-text scans empty. LF preserved.

- Task 11 odds-guards: 18/18 passed, 0 failed, 0 not run; exit 0; wall 3.524 s.
- Task 11 compliance-guards: 16/16 passed, 0 failed, 0 not run; exit 0; wall 6.184 s.
- Task 11 compliance-store: 36/36 passed, 0 failed, 0 not run; exit 0; wall 21.676 s.
- Task 11 macro-m0-harness: 11/11 passed, 0 failed, 0 not run; exit 0; wall 6.333 s.
- Task 11 macro-tf-gov: 20/22 passed, 0 failed, 2 not run; exit 0; wall 28.145 s.
- Task 11 macro-m7-ledger: 14/18 passed, 0 failed, 4 not run; exit 0; wall 7.689 s.
- Task 11 macro-m8-forward: 17/23 passed, 0 failed, 6 not run; exit 0; wall 10.347 s.
- Task 11 macro-m6-context: 14/16 passed, 0 failed, 2 not run; exit 0; wall 5.385 s.
- Task 11 cockpit: 47/47 passed, 0 failed, 0 not run; /workspace/tradegen-session/task-11-cockpit.json; exit 0; wall 6.333 s.
- Task 11 odds: 146/146 passed, 0 failed, 0 not run; /workspace/tradegen-session/task-11-odds.json; exit 0; wall 14.559 s.

## Cloud Task 12 completion — 2026-10-30T15:24:10+09:00 (Codex)

- Code: 349d69ec7c27e5dc2a3952c9bc70e4a5a0eeabe8.
- Review: 193개 catalogue 키 및 SHA 핀 유지. 계획 전체와 diff 대조, P4/P49/P50 회귀 재현 후 수정. 기존 테스트 함수 안에서만 검증 강화하여 41개 유지.
- RED: base tests 1/41, 40 missing attributes; strengthened tests then 38/41 with three expected failures. GREEN: 41/41, wall 3.562 s.
- P4: assumed p0/u observed zeros render a count-based bound using resolved bracket count; u=0 means every bracket resolved, so the denominator is also the full bracket count. Zero/nonpositive resolved is rejected at rendering. Added p0=0/u=0/both-zero checks inside existing tests. Task 14 must refuse no-edge wins==0 as ASSUMED_EDGE_UNREACHABLE.
- P49: build converts columns/flags/notes only when supplied; omitted required fields retain TypeError. Existing test checks all three.
- P50: determine decimal places after rounding to two significant digits, fixing rollover boundaries. Added 0.00009999 -> 0.010%, 0.0009999 -> 0.10%, 0.009999 -> 1.0% cases without changing fmt_prob rules.
- P51: optional helper deduplication deferred to preserve later anchors; no thresholds, seeds, catalogue keys, or pins changed.
- Exact plan report SHA before rulings: 4bb51b738c9e434523cba74528b1abc8801adef35ff29809fdf53b41dd482006. Final report SHA after three explicit preflight fixes: 860fe600b30df402beb1f4518da68c71eee8cbc9ba2c00684f6b1fd4fb8a6bf6. 70 top-level names, LF preserved, both banned-text scans empty.

- Task 12 odds-simulate: 18/18 passed, 0 failed, 0 not run; exit 0; wall 4.026 s.
- Task 12 odds-locks: 14/14 passed, 0 failed, 0 not run; exit 0; wall 3.474 s.
- Task 12 odds-bold: 12/12 passed, 0 failed, 0 not run; exit 0; wall 4.93 s.
- Task 12 odds-guards: 18/18 passed, 0 failed, 0 not run; exit 0; wall 4.032 s.
- Task 12 compliance-guards: 16/16 passed, 0 failed, 0 not run; exit 0; wall 6.182 s.
- Task 12 compliance-store: 36/36 passed, 0 failed, 0 not run; exit 0; wall 23.082 s.
- Task 12 macro-m0-harness: 11/11 passed, 0 failed, 0 not run; exit 0; wall 6.532 s.
- Task 12 macro-tf-gov: 20/22 passed, 0 failed, 2 not run; exit 0; wall 28.85 s.
- Task 12 macro-m7-ledger: 14/18 passed, 0 failed, 4 not run; exit 0; wall 8.038 s.
- Task 12 macro-m8-forward: 17/23 passed, 0 failed, 6 not run; exit 0; wall 10.245 s.
- Task 12 macro-m6-context: 14/16 passed, 0 failed, 2 not run; exit 0; wall 4.075 s.
- Task 12 cockpit: 47/47 passed, 0 failed, 0 not run; /workspace/tradegen-session/task-12-cockpit.json; exit 0; wall 5.83 s.
- Task 12 odds: 187/187 passed, 0 failed, 0 not run; /workspace/tradegen-session/task-12-odds.json; exit 0; wall 14.507 s.

## Cloud Task 13 completion — 2026-10-30T15:27:14+09:00 (Codex)

- Code: 86443e8edcd7ab333dd5f84076035ac191e85ba4.
- Review: 세 파일을 계획 원문과 바이트 대조(P52/P55 주석·import 교정 제외). 거부 순서, 비용 적용일, OKX cap 및 규칙 날짜, 비교 seed, 순수성 검사를 통과.
- RED: 0/13, missing precheck/simulate as expected. A scratch precondition initially named a nonexistent _bootstrap_groups function; it asserted before any mutation. Corrected it to the plan's six declaration-pattern check; production/tests unchanged by that attempt. GREEN 13/13 wall 3.781 s.
- P52: _no_edge_pair return type names exactly two ColumnStats objects. P55: reused the existing date import, omitting its redundant part-3 import. P53: purity test passed unchanged after its prescribed warmup; no flake or workaround. P54: CALENDAR_UNSIGNED test uses the runner's isolated temp_home, whose owner has no key; no real home/key read.
- Contract 3.2: Task 13 adds CAL_SHA, calendar_signed(sha), spy(target, name), owner_with(**changes), fresh_series(...), weekdays(start, horizon_days), pipeline_inputs(plan_obj, series_obj, **changes), pipeline(...) to tests/odds_fixtures.py. Tasks 14 and 17 consume these names.
- All three files match exact plan contents plus P52/P55 cosmetic corrections. No anchor, pin, seed, threshold or test count changed.

- Task 13 odds-guards: 18/18 passed, 0 failed, 0 not run; exit 0; wall 3.927 s.
- Task 13 compliance-guards: 16/16 passed, 0 failed, 0 not run; exit 0; wall 5.983 s.
- Task 13 compliance-store: 36/36 passed, 0 failed, 0 not run; exit 0; wall 23.836 s.
- Task 13 macro-m0-harness: 11/11 passed, 0 failed, 0 not run; exit 0; wall 6.532 s.
- Task 13 macro-tf-gov: 20/22 passed, 0 failed, 2 not run; exit 0; wall 28.852 s.
- Task 13 macro-m7-ledger: 14/18 passed, 0 failed, 4 not run; exit 0; wall 8.242 s.
- Task 13 macro-m8-forward: 17/23 passed, 0 failed, 6 not run; exit 0; wall 10.345 s.
- Task 13 macro-m6-context: 14/16 passed, 0 failed, 2 not run; exit 0; wall 4.379 s.
- Task 13 cockpit: 47/47 passed, 0 failed, 0 not run; /workspace/tradegen-session/task-13-cockpit.json; exit 0; wall 5.885 s.
- Task 13 odds: 200/200 passed, 0 failed, 0 not run; /workspace/tradegen-session/task-13-odds.json; exit 0; wall 15.615 s.

## Cloud Task 14 completion — 2026-10-30T15:30:46+09:00 (Codex)

- Code: 5f311f485b21fd940a6db8c1adabf03fb5016b66.
- Review: 모든 계획 교체 구간 대조. 20개 refit과 21개 pilot을 유지. P4 추가 테스트는 수정 전 실패·수정 후 통과; 기준 확률 0건이면 거부. P56/P58 설명과 P59 annotation만 정리.
- RED: odds_columns 0/14, odds_pipeline 4/13, exactly the planned missing-feature failures. P4 focused RED after base implementation: 0/1, reachable pilot plus zero observed baseline wins wrongly accepted. GREEN: odds_columns 14/14 wall 8.380 s; odds_pipeline 13/13 wall 4.422 s.
- P4: _assumed refuses both no resolved brackets and wins==0; its refusal detail names both. Added a reachable-pilot/zero-baseline end-to-end check inside the existing unreachable-rate test. Refused report has no columns/assumed probability. No catalogue changes.
- P56: garch_series docstring no longer claims every refit stays below NU_NORMAL; P58 at_bound is kept in the fit, not promised as separately reported; P59 removed redundant annotation quotes. P57 optional refusal deduplication deferred, preserving Task 17 anchors.
- P60 measurements, using in-memory wrappers around real unchanged calls during the official acceptance entry point: all-member test 21 pilots, max deterministic step 8.962372944478084e-13 (limit 1e-7), summed 5.180709160279573e-12 (limit 1e-6), max statistical z 2.753403813867666 (limit 4). Refit nu range 12.589725419554885..inf.
- Assumed 0.70: full-column win 0.6963087248322147 (absolute miss 0.0036912751677853 < 0.01), theta 0.84375, baseline p0 0.4827197595792637, unresolved share 0.023039595481792602, resolved 47,916, nb 31. Real-pilot 0.60 case: theta 0.4296875, full win 0.6009005065349259, baseline p0 0.48452962545408995. No reseeding or looser bounds.
- Per-test timing: all-member 2.0502 s; no test exceeded 15 s. Raw margins/timings retained outside repository. Full 20 refits and real 20,000-path tilt/200,000-path chunk tests ran.
- O3-18 resolves the Task 9 minor: bootstrap range is set by simulate._column from spec/history alone, not run_column; direct run_column callers (delisting, assumed, replay) keep their own range value. This is the accepted contract 10.1/10.3 erratum, not a new departure.
- Contract 3.2: Task 14 adds members(*names) and garch_series(...) to tests/odds_fixtures.py. P52 exact two-element return annotation retained. Core matches plan plus P4/P58 fixes, raw scans empty, LF retained.

- Task 14 odds-simulate: 18/18 passed, 0 failed, 0 not run; exit 0; wall 3.774 s.
- Task 14 odds-locks: 14/14 passed, 0 failed, 0 not run; exit 0; wall 3.324 s.
- Task 14 odds-guards: 18/18 passed, 0 failed, 0 not run; exit 0; wall 3.825 s.
- Task 14 compliance-guards: 16/16 passed, 0 failed, 0 not run; exit 0; wall 6.138 s.
- Task 14 compliance-store: 36/36 passed, 0 failed, 0 not run; exit 0; wall 24.894 s.
- Task 14 macro-m0-harness: 11/11 passed, 0 failed, 0 not run; exit 0; wall 6.682 s.
- Task 14 macro-tf-gov: 20/22 passed, 0 failed, 2 not run; exit 0; wall 28.854 s.
- Task 14 macro-m7-ledger: 14/18 passed, 0 failed, 4 not run; exit 0; wall 7.539 s.
- Task 14 macro-m8-forward: 17/23 passed, 0 failed, 6 not run; exit 0; wall 10.144 s.
- Task 14 macro-m6-context: 14/16 passed, 0 failed, 2 not run; exit 0; wall 4.077 s.
- Task 14 cockpit: 47/47 passed, 0 failed, 0 not run; /workspace/tradegen-session/task-14-cockpit.json; exit 0; wall 5.786 s.
- Task 14 odds: 214/214 passed, 0 failed, 0 not run; /workspace/tradegen-session/task-14-odds.json; exit 0; wall 20.124 s.

## Cloud Task 15 completion — 2026-10-30T15:33:56+09:00 (Codex)

- Code: b67cd4f1c656d08c4c4d9d7a74c1183aba0f5562.
- Review: 로더 전체와 25개 테스트를 계획에 대조. P61/P62 검증 강화, P63 빈 필수 FX 거부, 추가 큰 정수 검증 오류 수정. 데이터 client는 hermetic seam으로 대체.
- RED: missing bars ImportError 0/1. Base implementation with stronger cases: 23/25; expected failures were an overflowing integer in the pinned cache and missing required historical FX silently shortening the OKX composite. GREEN 25/25 wall 2.867 s.
- P61: exact tuple (HISTORY_DAYS=3650, CACHE_ENV=TRADEGEN_ODDS_BARS_CACHE, KIS_MAX_PAGES=60) pinned in existing paging test. P62: added required/extra cache keys, mismatched source, null dates, unequal lengths, duplicate dates, boolean price, and malformed manifest shape/key/value cases inside existing tests. Matching sha does not bypass part validation.
- P63 stricter option applied: when historical OKX composition needs an FX proxy and its final part is empty, raise RuntimeError; no date loss disguised as a valid shorter series. Complete KRW-USDT history still does not request FX. Existing US-empty-series behavior retained.
- Additional numeric fix: _price catches OverflowError and returns False for an integer such as 10**400; _part_from then reports the intended bad-cache RuntimeError. Both direct validation and fail-closed behavior are stricter; no accepted malformed price.
- P64: default-path test performs only read-only path resolution and existence checks on ~/.tradegen, no wrapper watch fired. P65 loader dedup deferred; P66 harmless assertion loop retained. P67 seam-body tests replace client classes on imported modules, rather than fake modules; real constructors and APIs never run.
- Only core changes beyond exact plan are the two reproduced fixes; no pins, seeds, expected test counts or existing refusal checks weakened. LF retained.

- Task 15 odds-guards: 18/18 passed, 0 failed, 0 not run; exit 0; wall 3.829 s.
- Task 15 compliance-guards: 16/16 passed, 0 failed, 0 not run; exit 0; wall 7.338 s.
- Task 15 compliance-store: 36/36 passed, 0 failed, 0 not run; exit 0; wall 25.797 s.
- Task 15 macro-m0-harness: 11/11 passed, 0 failed, 0 not run; exit 0; wall 6.834 s.
- Task 15 macro-tf-gov: 20/22 passed, 0 failed, 2 not run; exit 0; wall 31.166 s.
- Task 15 macro-m7-ledger: 14/18 passed, 0 failed, 4 not run; exit 0; wall 8.139 s.
- Task 15 macro-m8-forward: 17/23 passed, 0 failed, 6 not run; exit 0; wall 10.548 s.
- Task 15 macro-m6-context: 14/16 passed, 0 failed, 2 not run; exit 0; wall 4.376 s.
- Task 15 cockpit: 47/47 passed, 0 failed, 0 not run; /workspace/tradegen-session/task-15-cockpit.json; exit 0; wall 6.382 s.
- Task 15 odds: 239/239 passed, 0 failed, 0 not run; /workspace/tradegen-session/task-15-odds.json; exit 0; wall 20.878 s.

## Cloud Task 16 completion — 2026-10-30T15:37:14+09:00 (Codex)

- Code: 844c82d1afc453b274df6e9461812f101cefcfbb.
- Review: 출처 함수 복사와 원본 일치, 저장 전 경로 검증, 달력 사전 적재/재해시를 대조. P68/P69 실패 3건 재현 후 수정. Linux 링크 테스트는 실제 symlink로 기존 거부 검증 유지.
- RED: missing inputs ImportError 0/1; base code plus preflight checks 9/12, three expected failures (bad-state/input huge integer OverflowError and malformed calendar UnicodeDecodeError). GREEN 12/12 wall 5.171 s.
- P68: calendar_for catches UnicodeDecodeError and yaml.YAMLError in addition to existing failures, returning the ALTERED refusal. Existing approved-fixture test corrupts the file after the owner check with invalid UTF-8 and invalid YAML; both refused, no session computation from altered bytes.
- P69: _number returns False for overflowing integer conversion. Existing tests verify 10**400 is refused in the incoming typed rates and stored comparison state, with state bytes unchanged.
- Linux adaptation: Task 16's new junction test calls the already reviewed compliance_fixtures.directory_link; no _winapi import on Linux, no skipped check, and both hard-link and directory-link refusal assertions unchanged.
- P70: calendar md5 file-id ordering cites accepted O3-13, not a fresh drift. P71: the NO_APPROVAL wording also covers owner verification refusing altered storage, while a race after that verification is ALTERED; no semantics changed. P64: real default path test only resolves/checks metadata, no write and no watch fired.
- repo_anchor/tree_hash copies and their constants untouched and equal originals on repository and synthetic roots. No extra test function, pin, threshold or seed changes. LF retained.

- Task 16 odds-bars: 25/25 passed, 0 failed, 0 not run; exit 0; wall 2.978 s.
- Task 16 odds-guards: 18/18 passed, 0 failed, 0 not run; exit 0; wall 3.674 s.
- Task 16 compliance-guards: 16/16 passed, 0 failed, 0 not run; exit 0; wall 6.332 s.
- Task 16 compliance-store: 36/36 passed, 0 failed, 0 not run; exit 0; wall 24.481 s.
- Task 16 macro-m0-harness: 11/11 passed, 0 failed, 0 not run; exit 0; wall 6.534 s.
- Task 16 macro-tf-gov: 20/22 passed, 0 failed, 2 not run; exit 0; wall 29.15 s.
- Task 16 macro-m7-ledger: 14/18 passed, 0 failed, 4 not run; exit 0; wall 8.141 s.
- Task 16 macro-m8-forward: 17/23 passed, 0 failed, 6 not run; exit 0; wall 10.897 s.
- Task 16 macro-m6-context: 14/16 passed, 0 failed, 2 not run; exit 0; wall 4.679 s.
- Task 16 cockpit: 47/47 passed, 0 failed, 0 not run; /workspace/tradegen-session/task-16-cockpit.json; exit 0; wall 6.484 s.
- Task 16 odds: 251/251 passed, 0 failed, 0 not run; /workspace/tradegen-session/task-16-odds.json; exit 0; wall 22.479 s.

## Cloud compatibility 2 — 2026-10-30T15:39:29+09:00 (Codex)

- Code: db31b443fd9e9f07da503dd55c9eb6b27d326566.
- RED: tables 69/70 (unconditional _winapi import); isolation 12/17 (five Windows-junction skips); signer 34/38 (deployment-path equality failure, two junction skips, one real GetConsoleMode skip).
- Reused compliance_fixtures.directory_link: actual junctions on Windows, actual symlinks on POSIX; unchanged checks still reject linked roots, linked entries, path escapes and writes. Seven formerly skipped link tests now execute; a file-symlink test already ran on Linux. No new test function or weakening of refusal assertions.
- Standalone tools/signer/sign.py intentionally pins the owner's Windows deployment root, while core/isolation.py derives QUANTGEN's sibling from the checkout. The old absolute equality assumed the checkout lived on that desktop. Pin both exact intended roots independently, and retain equality when that documented deployment layout applies. Existing synthetic-root refusal/parity tests remain intact. Production signer/isolation code and actual keys/homes are untouched.
- GREEN: tables 70/70; isolation 17/17; signer 37/38, zero failures. Only compliance_signer/test_stdin_terminal_check_follows_getconsolemode remains NOT_RUN: REFDATA: GetConsoleMode needs Windows. It requires a real Windows console and cannot be represented as verified on Linux. Task 18/19 must report this explicit platform difference; do not invent PASS.
- Counts, LF endings and diff reviewed. Tests only; no extra broad macro rerun needed. Full compliance suite remains required at Task 18.

## Cloud Task 17 completion — 2026-10-30T15:47:48+09:00 (Codex)

- Code: 03f865cec1022d550fe22458b631a5f36036d942.
- Review: 세 RED/GREEN cycle 완료. 고정된 3,288개 입력과 2,530개 OOS 행, 모든 digest/stat 핀 유지. P5는 progress/preflight 원문대로 호출자에서 range를 설정. 거대 정수도 예외 대신 명명된 거부.
- RED/GREEN A: missing import 0/1; base plus overflow regression 13/14; fixed 14/14 wall 16.604 s; odds_models 19/19. B: 14/19 with five missing-engine refusals; P5 direct-column range regression failed before correction; GREEN 19/19 wall 17.155 s; simulate 18/18, locks 14/14. C: 19/24 with exactly five missing card/helper failures; GREEN 24/24 wall 17.362 s.
- P5/O3-18: _replay_column returns nan range; _replay_report.column sets the range with dataclasses.replace immediately after run_column using only target, replay moves/costs and check count. Existing report range assertions unchanged; extra direct-column and spy assertions pin this separation. This corrects Task 16 next_notes/CURRENT's inaccurate 'before paths' summary. A preliminary scratch test for that mistaken interpretation was replaced after re-reading the authoritative progress.md and preflight.md; no such interpretation was committed.
- Added OverflowError to verify_replay's named rejection catch; existing edited-item test rejects 10**400 in pnl and turnover with pnl_md5/turnover_md5. Pins, seeds, thresholds, test count unchanged.
- P60 loss-stop share 0.09260217075362792 (required 0.07..0.13), X mean -9.671865866776878, SE 13.641702486369466 (abs mean < 4 SE), on the original daily-loss stream and 20,000 paths. Kelly measurements appended below.
- P72: kept the redundant turnover-length check because CONTRACT 7.5 names it. P73: 118-character annotation within 119-column style; rsplit uses only the three fixed _REPLAY_KEYS, no unnecessary cosmetic rewrite.
- O3-15: report growth uses 29 moves at a 30-day horizon, 2.9% blocks versus 2.6% IID; separate 30-move block_growth pin unchanged. report.py unchanged and all rendering anchors verified. Replays only read committed cache; no study runner/API/write.
- P60 Kelly on the pinned real replay: mu_lb 0.0007503162074761997, fstar 1.0, gprime(1) 7.961013572001992e-05 > 0, minimum centered return -0.1217990099920319 > -1. Focused original test 1/1 wall 7.285 s; no reseed.

- Task 17 odds-garch: 17/17 passed, 0 failed, 0 not run; exit 0; wall 8.341 s.
- Task 17 odds-bold: 12/12 passed, 0 failed, 0 not run; exit 0; wall 5.33 s.
- Task 17 odds-pipeline: 13/13 passed, 0 failed, 0 not run; exit 0; wall 4.427 s.
- Task 17 odds-simulate: 18/18 passed, 0 failed, 0 not run; exit 0; wall 3.728 s.
- Task 17 odds-locks: 14/14 passed, 0 failed, 0 not run; exit 0; wall 3.324 s.
- Task 17 odds-columns: 14/14 passed, 0 failed, 0 not run; exit 0; wall 8.391 s.
- Task 17 odds-report: 41/41 passed, 0 failed, 0 not run; exit 0; wall 3.426 s.
- Task 17 odds-guards: 18/18 passed, 0 failed, 0 not run; exit 0; wall 4.028 s.
- Task 17 compliance-guards: 16/16 passed, 0 failed, 0 not run; exit 0; wall 6.183 s.
- Task 17 compliance-store: 36/36 passed, 0 failed, 0 not run; exit 0; wall 24.79 s.
- Task 17 macro-m0-harness: 11/11 passed, 0 failed, 0 not run; exit 0; wall 6.581 s.
- Task 17 macro-tf-gov: 20/22 passed, 0 failed, 2 not run; exit 0; wall 28.151 s.
- Task 17 macro-m7-ledger: 14/18 passed, 0 failed, 4 not run; exit 0; wall 7.938 s.
- Task 17 macro-m8-forward: 17/23 passed, 0 failed, 6 not run; exit 0; wall 10.296 s.
- Task 17 macro-m6-context: 14/16 passed, 0 failed, 2 not run; exit 0; wall 4.125 s.
- Task 17 cockpit: 47/47 passed, 0 failed, 0 not run; /workspace/tradegen-session/task-17-cockpit.json; exit 0; wall 5.931 s.

## Cloud Task 18 completion — 2026-10-30T15:51:54+09:00 (Codex)

- Code: cd265bf4fd90f564997f0ef52e2fd42b3cce5785.
- Review: 계획과 두 신규 파일 전체 대조. P78 설명을 odds state로 한정하고 P79 반환 타입만 구체화. 실제 20 refit은 Task 14 검증 유지. CLI 데이터 요청 이전 거부와 출처 기록, 비교 상태와 오류 exit를 확인.
- RED: missing run import, 0/1 exactly as planned. GREEN CLI 12/12 wall 9.718 s; full odds 287/287 wall 43.090 s; compliance 340/341 wall 60.096 s, zero failures.
- P74: seven precheck/error tests need no OF.chunk because they simulate no paths; no reduction of any statistical check. P75: textual invalid start/float horizon survive JSON loading for the start/horizon refusals, while wrong JSON types are file refusals. Huge integer conversion and malformed JSON/nesting are file refusals.
- P76: no optional helper refactor; keeping accepted fixtures avoids unnecessary drift. P77: comparison rerun equality tested on unchanged repository bytes within one invocation. P78: comments/docstrings now say no odds state written; owner.load_context may snapshot an approved context, which is distinct from odds state. The no-key test still asserts both compliance and odds folders absent. P79: precise list[plan.Plan | plan.Refusal] annotation.
- Accepted Task 18 readings: one context per distinct stake, one frozen replay per invocation; CLI integration swaps REFIT_B to 2 while Task 14 retains all 20 real refits. Exit 0/report, 2/refusal, 4/crash; crash/guard failures print no card. No owner log changes.
- Cloud compliance difference: exact id compliance/compliance_signer/test_stdin_terminal_check_follows_getconsolemode is NOT_RUN, reason REFDATA: GetConsoleMode needs Windows. Linux has no Windows console API; retained the test and its honest NOT_RUN. The two symlink cases that were NOT_RUN in Windows baseline now pass; seven formerly skipped directory-link tests execute using actual POSIX symlinks. Task 19 run-check will name only this platform exception, never allow unrelated new skips.

- Task 18 odds-guards: 18/18 passed, 0 failed, 0 not run; exit 0; wall 3.974 s.
- Task 18 odds-full: 287/287 passed, 0 failed, 0 not run; /workspace/tradegen-session/task-18-odds-full.json; exit 0; wall 43.09 s.
- Task 18 compliance-full: 340/341 passed, 0 failed, 1 not run; /workspace/tradegen-session/task-18-compliance-full.json; exit 0; wall 60.096 s.
- Task 18 macro-m0-harness: 11/11 passed, 0 failed, 0 not run; exit 0; wall 6.534 s.
- Task 18 macro-tf-gov: 20/22 passed, 0 failed, 2 not run; exit 0; wall 28.145 s.
- Task 18 macro-m7-ledger: 14/18 passed, 0 failed, 4 not run; exit 0; wall 7.585 s.
- Task 18 macro-m8-forward: 17/23 passed, 0 failed, 6 not run; exit 0; wall 10.146 s.
- Task 18 macro-m6-context: 14/16 passed, 0 failed, 2 not run; exit 0; wall 4.227 s.
- Task 18 cockpit: 47/47 passed, 0 failed, 0 not run; /workspace/tradegen-session/task-18-cockpit.json; exit 0; wall 5.731 s.

## Cloud compatibility 3 — 2026-10-30T16:04:18+09:00 (Codex)

- Task 19 first full run at cd265bf: 1351/1477 PASS, 4 FAIL, 122 NOT_RUN; wall 374.023 s. Real default homes unchanged. Failed QA record saved outside repository and the prior committed QA bytes restored immediately.
- Two failures came from the outer sandbox refusing socket construction, before the test could exercise the existing local HTTP server or the hermetic socket guard. Both unchanged tests pass with loopback-capable network permission; their destinations are only 127.0.0.1. No market/data API call is enabled by the tests, and all 19 credential names remain KEYLESS.
- The M0 test mixed import-time cached paths with paths recomputed after clearing TRADEGEN_HOME. It now verifies cached paths under the startup root, and default resolvers separately under the default root, with QUANTGEN refusal for both. Windows case/prefix aliases remain on Windows; POSIX runs real relative and symlink aliases against every resolver/writer. No skipped assertion or actual QUANTGEN write.
- The M8 dry-run used checkout mtime after its fixed historical knowledge time, correctly making US closes invisible. The fixture now copies unchanged public cache bytes to temp storage with retrieval time 2026-10-06T22:00:00Z. Existing vol assertions pass (sigma 0.1079234399535904, weight 1.0). An added earlier-knowledge run remains fail_closed, preserving the point-in-time boundary. Repository cache bytes and timestamps unchanged.
- Code 2b9f493be9a1d7feb6cb7584c646fd9924412c8d; only tests/macro_m0_rules.py and tests/macro_m8_pipeline.py changed. Original four failures: 4/4 now PASS. Full affected modules: M0 rules 10/11, M8 pipeline 20/21, zero FAIL; each module's one existing REFDATA NOT_RUN retained. No test count changed. Self-review complete; Task 19 full run will be repeated before committing QA.

- Task 19: full run (KEYLESS) 1355/1477 passed, 0 failed, 122 not run on 2026-10-30; previous full run 1055/1176 passed, 0 failed, 121 not run; odds 287 PASS in 39.9 s; compliance 340 PASS / 1 NOT_RUN (+14 rows); status changes 1 [run initial; code 2b9f493]
  - compliance/compliance_signer/test_stdin_terminal_check_follows_getconsolemode: PASS -> NOT_RUN, REFDATA: GetConsoleMode needs Windows
  - Cloud platform ruling: GetConsoleMode requires Windows; one NOT_RUN retained, not PASS
- Task 19 README drift: baseline compliance 327 PASS and total 1055/1176 (121 NOT_RUN), not draft 325/327 or 1053/1176. This run determines every cell; odds row inserted verbatim from the plan, Cloud environment label used truthfully; all original CRLF endings retained.
- Task 19: isolated Cloud smoke (Q45; KEYLESS, hermetic, seams stubbed), initial record 13b7372: exit 2 STATE_UNUSABLE; provenance present, no seam called, zero state entries before/after. This is a Cloud fixture result, not a smoke on the owner PC.

## Cloud odds-final review wave — 2026-10-30T16:19:11+09:00 (Codex)

- Final review reproduced six failures before fixes: guards 15/18 (constructor aliases, nested match, shadowed writers), product precheck 0/1, vector tick lookup 0/1, malformed replay stats 0/1. The same existing test functions now pass; no test-count, seed, threshold or pin change.
- 99f81034e3948724e3552cdb5428cf50d34baacc: Final review: three existing guard tests reproduce the missing alias/match cases; all 18 pass with raw names and every import target retained. No exemption added.
- 5c1a1ade5ca78747f6cc7077567677f9566af3e6: Final review: Upbit USDC previously passed the product precheck. Preserve the existing refusal priorities and reject any otherwise accepted market absent from the approved venue before costs or data requests.
- 02e3c37853fa3f23e963ea4933a7b6fbf35df12b: Final review: a hand-built ladder no longer wraps a negative search index to its highest tick. Match the scalar oracle refusal; parsed valid ladders retain their exact values.
- fbb0a7888e6924aa5469d6800f7a7443b64e7dab: Final review: malformed stats mappings and unreadable stats attributes are refused by item name, as the unsigned replay boundary promises. All existing numeric pins and thresholds remain unchanged.
- 36f64916bdbb56282f3214b1247a7a318d48f62b: Final review: cover missing odds keys, malformed tick rows/book keys and a partial source map; read cited research lines by byte line boundaries to match repository #L numbering.
- 3f10ffbb070c3ea1c26acecd678081e7e5274c3d: Final review: drive an internal calendar-store TypeError through rules.main --check and require exit 4, covering the existing Task 4 fix end to end.
- c9018e213ea037019501d1e3a7daafa8633e8ad0: Final review P84: artificial flags cover every date ordering; remove the inaccurate claim that shipped rows have no effective_until.
- odds-final odds-guards: 18/18 passed, 0 failed, 0 not run; exit 0; wall 3.875 s.
- odds-final odds-plan: 25/25 passed, 0 failed, 0 not run; exit 0; wall 3.577 s.
- odds-final odds-costs: 23/23 passed, 0 failed, 0 not run; exit 0; wall 3.324 s.
- odds-final odds-replay: 24/24 passed, 0 failed, 0 not run; exit 0; wall 17.467 s.
- odds-final compliance-tables: 70/70 passed, 0 failed, 0 not run; exit 0; wall 7.338 s.
- odds-final compliance-cli: 36/36 passed, 0 failed, 0 not run; exit 0; wall 21.38 s.
- odds-final compliance-guards: 16/16 passed, 0 failed, 0 not run; exit 0; wall 6.433 s.
- odds-final compliance-store: 36/36 passed, 0 failed, 0 not run; exit 0; wall 25.843 s.
- odds-final macro-m0-harness: 11/11 passed, 0 failed, 0 not run; exit 0; wall 6.482 s.
- odds-final macro-tf-gov: 20/22 passed, 0 failed, 2 not run; exit 0; wall 28.906 s.
- odds-final macro-m7-ledger: 14/18 passed, 0 failed, 4 not run; exit 0; wall 8.144 s.
- odds-final macro-m8-forward: 17/23 passed, 0 failed, 6 not run; exit 0; wall 10.597 s.
- odds-final macro-m6-context: 14/16 passed, 0 failed, 2 not run; exit 0; wall 4.128 s.
- odds-final cockpit: 47/47 passed, 0 failed, 0 not run; /workspace/tradegen-session/odds-final-cockpit.json; exit 0; wall 5.983 s.
- Additional review resolutions: Task 1 three named limitations and Task 2 shape coverage are closed; static guards remain a supplement to source review, not proof for arbitrary Python/archive/database APIs. Task 3 source line reading now uses byte line boundaries. Task 4 calendar CLI exit 4 is exercised end to end. Task 5 market precheck rejects Upbit USDC before costs/data while preserving earlier refusal priorities. Task 6 malformed hand-built tick ladders match the scalar refusal. Replay arbitrary malformed object/stat exceptions return the named failed item.
- P80 CRLF 892-line README retained. P81 signer help says editor terminals can be refused; no real signer/owner action run. P82 state-root failure is a smoke failure requiring metadata-only diagnosis. P83 Task 8 kw_only ruling already recorded. P84 inaccurate shipped-row comment corrected.
- Accepted boundaries retained: loader canonicalizes plan hash inputs; injected/frozen data is not redesigned for deep immutability. Task 3 source citation/value lines and KIS minimum-order inference remain owner act 3 with venue SHA unchanged. Scalar/vector cost oracle and the accepted O3-22 floor tolerance remain. Task 9 cash/cap paths are covered by Task 10 hand-ledger cases. Optional P37/P42/P45/P51/P57/P65/P76 refactors remain deferred. No exhaustive mutation-coverage claim.
- This is an intermediate checkpoint: Task 19 final full run, record, smoke and Step 9 ledger commit remain. odds-final is not marked complete until they pass.
