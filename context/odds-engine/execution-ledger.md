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

## Drift rulings
- Task 1: none. The three `tests/run_all.py` old texts (the `compliance_acceptance` import line, `tests()`, the `--suite` help) and the README `--suite macro` line were each found once, unchanged by the follow-up.
- Task 2: none. The four `core/compliance/rules.py` old texts (R1 `_VENUE_OPTIONAL` at :668 with `_venue` at :671, R2 `deposits` at :314, R3 `quote_for` at :324-326 with `VenueFacts` below, R4 the deposits loop end and `return Venue(...)` at :724-726) and the two `tests/compliance_tables.py` old texts (T1 the `minimum_krw` line at :739, T2 the end of `test_deposit_entries` at :768-769 and the "Hashes and the approved state" banner) were each found once, exactly as quoted (line numbers at 418d9bb, before this task's edits).
- Task 3: none. The three `core/odds/venues.yaml` old texts (V1 the header comment at :2-4, V2 the kis `quote_by_currency` / `deposits: []` / `source:` lines at :10-12, V3 the upbit BTC deposit line and `source:` at :19-20) and the `tests/compliance_tables.py` old text (T3 the closing `for kind in _T5_SHIPPED:` loop of `test_shipped_urls_come_from_the_research` at :1533-1537, the end of the file) were each found once, exactly as quoted (line numbers at bd6a51e, before this task's edits).

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
