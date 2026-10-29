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
