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
