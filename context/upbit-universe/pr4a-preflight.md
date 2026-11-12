# PR 4a pre-flight conflict scan (plan `docs/2026-11-11-upbit-krw-universe-pr4a-control.md` vs `tgu-premerge` @ fea6e33)

Read-only scan. P = plan line (CR stripped). Code cites are file:line at fea6e33 (origin/main 6d9bf56 + PR 2 #24 @ 8c9a311 +
PR 3 #25 @ 6eed8b8). Every Edit anchor was counted by exact text against the premerge tree, and every edit was applied in
memory in plan order (`pr4a_scan/anchors.py` -> `pr4a_scan/sim/`, 13 files, all compile). Nothing in the repo was edited,
run or committed. The full suite was not run; individual guard functions were called on the simulated files.

## Real conflicts (2) and 7 nits
| # | Where | Problem | Fix |
|---|---|---|---|
| C1 | T1 Step 1 stop rule (P150) and every later control_controller count (P284, P521, P776, P1404) | PR 3 appended **two** tests to tests/control_controller.py (`test_cancel_of_a_recorded_derived_coin_buy_needs_no_rule_or_snapshot`, `test_dispatch_refuses_a_reserved_derived_buy_once_the_universe_is_gone`; 36 at fd85850/6d9bf56/8c9a311, 38 at 6eed8b8 and fea6e33). P150 expects `tests/control_controller.py:37`, so the implementer hits "any of these differs, stop and report". P144-145 also says "PR 3's appended test" (singular). Every later count is one short. | P150: `37` -> `38`. P145: "PR 3's appended test" -> "PR 3's two appended tests". P284: `38` -> `39` and "(36 at fd85850, PR 3's one, this one)" -> "(36 at fd85850, PR 3's two, this one)". P521: `40` -> `41`. P776: `41` -> `42`. P1404: `control_controller/` `41` -> `42`. (control_session 14/15 and control_guards 14 are correct.) |
| C2 | T4 control_fixtures edit "After line 44 (`    session._PREPARED.clear()`) insert" (P1380-1384) | The quoted text occurs twice as a substring of tests/control_fixtures.py: line 44 (4 spaces) and line 54 `        session._PREPARED.clear()` (8 spaces, inside `finally`). The Edit tool matches substrings, so `old_string="    session._PREPARED.clear()"` is refused as not unique. (Line 44 is the right place; the line number is correct.) | Quote two lines as the anchor: `    capability._ISSUED.clear()\n    session._PREPARED.clear()\n    try:` (lines 43-45, unique) and insert `    universe_odds._BATCHES.clear()` after the second line. |
| N1 | P1178 code comment and P38 spec quote | `(plan.py:301)` -- the `REPLAY` check is core/odds/plan.py:302 at fea6e33. P38 quotes the spec, so only the comment matters. | Comment: `plan.py:302`, or drop the line number. |
| N2 | P115 | `model.seal_context` cited as core/compliance/model.py:230-238; PR 1 moved it to 259-267. | `model.py:259-267`. |
| N3 | T4 `_context` (universe_odds.py) | Reads `controller._account` and `controller._positions` (private Controller members) from another module. No guard forbids it; a reviewer may flag it. | Accept (same package) or add a one-line comment naming the coupling. |
| N4 | T4 `_instant` | Third copy of the aware-datetime check (controller `_instant`, session `_aware`). | Accept; reuse would need an import from controller at module load (cycle), so the copy is the cheaper choice. |
| N5 | T4 `_event_data` batch row shape (P1331-1346) | Closes the key set and the 64-hex fields but does not type-check the row's date and time strings; the only writer is `run_batch`, which writes `plain(batch)`. | Accept (journal rows are only written by the module); note it in the PR body. |
| N6 | T3 fixed-session test (P620) | Pins the fixed encoding by rebuilding it from field names, not by a constant digest, so a change to both sides would pass. | Accept; optional: pin one literal record digest. |
| N7 | T5b `notin.delist` text | docs/2026-10-23-compliance-gate-and-odds-engine-design.md:1018 still quotes the old wording. Not a test pin. | Optional doc follow-up; not this PR's file list. |

## 1. Pairs of tasks sharing a file or interface
| Pair | Shared item | Producer -> consumer | Agree? |
|---|---|---|---|
| T1 -> T2..T5 | test helpers in tests/control_session.py (after `    return plan, inputs, seed`, line 37) and tests/control_controller.py (appended) | P171-197, P215-222 -> later tests | Yes; anchors unique (1 each) |
| T1 -> PR 4e | `RiskResult.universe` from `Controller.observe` (risk.py field, controller.py:441) | index contract | Yes; risk.py surface pin moves 4d9d5fa5... -> 852ae2f2..., the hash computed from the simulated file equals the plan's |
| T2 -> PR 4e | `OrderState.side/symbol/last-event time`; kill records its reason | index contract | Yes. No test or runtime code builds `OrderState` directly; all `_view` calls go through `_fold`. Existing kill callers pass `fixture`, `lifecycle test`, `owner_requested` (coordinator.py:695); no test asserts `owner_requested` on a row written with another reason |
| T3 -> T5 | `_record` (inserted after session.py:53); T5 inserts `_symbol_ok` after `_record` | P690-695 -> P1661-1671 | Yes; `_record` end line unique (1) after T3 |
| T3 -> T5 | `PreparedSession.universe_batch_digest` (default `None`) and `_event_data` session_prepared key sets (old, old + batch) | P683-684, P737-761 -> T5 prepare/verify | Yes. Keyword builders elsewhere keep working through the default (launch_windows_owner_authority.py:270, launch_owner_ops.py:518 `PreparedSession(**body)`) |
| T4 -> T5 | `UniverseBatch`, `registered_batch`, `_BATCHES` | universe_odds.py -> session.py import (P1649) | Yes. No import cycle: controller -> session -> universe_odds; universe_odds imports controller lazily inside functions (`_fold`, `_event_data`) |
| T4 -> T5 | tests/control_universe_odds.py created by T4, edited by T5 (3 import edits, datetime import, insert after `batch_rows`, append) | P874-1065 -> P1475-1619 | Yes; every T5 anchor in the new file is unique (1) |
| T4 -> all tests | `universe_odds._BATCHES.clear()` / restore in control_fixtures | P1371-1390 | Yes after C2 |
| PR 1 -> T4/T5 | `rules.universe_top_n(universe, n)`, `model.Universe` fields, `Context.universe` (model.py:195), `owner.load_context(now, positions, *, session_id=None)` (owner.py:990), `OwnerState.head` (seq, sha), `ApprovedState.state_hash` | universe_odds `_context`, `run_batch`; session `prepare_session` | Yes. `universe_top_n` needs int n >= 1 (run_batch checks 1..64 first); `eligible` is ((market, Decimal), ...) with `KRW-` markets, and Upbit `order.symbol` is `KRW-XXX`, so `_symbol_ok` compares like with like |
| PR 2 -> T4 | `UniverseBars(market, bars=((iso date, open, close), ...), receipt_sha256=tuple)`, frozen dataclass (bars.py:335-336, 400-402) | read by attribute in `_bars_ok`, `_series` | Yes |
| PR 3 -> T1/T2/T4 | controller.py lookup callers | numstat 5 added / 5 deleted (five one-line replacements) | Yes; no cited controller line moved |
| T4 `run_batch` -> PR 4e `odds_batch` | `now` contract and the 30 s `_CLOCK_AGE` | P1239-1247 -> PR 4e P3126-3129 | **Hazard 5** (section 6) |

## 2. Per task
| Task | New tests vs code | Realistic RED (first run) | Expected counts | Created / later touched | Anchors @fea6e33 |
|---|---|---|---|---|---|
| T1 | `test_observe_returns_the_universe_of_the_context_it_loaded` traced through observe -> `_account` -> RiskResult; passes after risk.py field + controller.py:441 | `AttributeError: 'RiskResult' object has no attribute 'universe'` | control_controller 39 (plan says 38: C1) | touches risk.py, controller.py, renewal_boundaries.py:32, control_session, control_controller | all 1; Step 1 grep line 32 and numstat 5/5 match; count 38 not 37 (C1) |
| T2 | 2 tests (P375, P386) | `AttributeError: 'OrderState' object has no attribute 'side'`; `AssertionError: expected refusal` | control_controller 41 (plan 40: C1) | controller.py:58-64, 251, 255, `_view`, 851-853, 863 | all 1 |
| T3 | 2 tests (fixed session row in control_session, old/new key sets in control_controller) | `AttributeError` on `PreparedSession.universe_batch_digest`; `ValueError: invalid lifecycle event fields`; the third command already passes | control_session 15 (OK), control_controller 42 (plan 41: C1) | session.py:35, after 53, 202, 231; controller.py:149-151, 170-173 | all 1 |
| T4 | 9 tests in new tests/control_universe_odds.py, all traced to pass; row-size test stays under store.MAX_ROW_BYTES 262144 at MAX_COINS 64 | `ImportError: cannot import name 'universe_odds' from 'execution_control'` | 9 (OK), control_controller 42 (plan 41: C1), control_session 15, control_guards 14 (OK) | creates universe_odds.py and control_universe_odds.py; touches store.py:25-27, controller.py:23, 168, hex loop, 232, control_fixtures 30/40/44/55, control_acceptance MODULES 18-20 | all 1 except fixtures line 44 (C2) |
| T5 | 6 tests appended | `TypeError: prepare_session() got an unexpected keyword argument 'universe_batch'` (x5); `ImportError` for `_symbol_ok` | control_universe_odds 15 (OK) | session.py 5, 13, after 40, after `_record`, 60-61, 79, 93, 139, 167, 177, 223; control_universe_odds | all 1 |
| T5b | 1 test (`test_not_in_box_names_rotation_selection`); `_NOT_IN` renders `"- " + text` (report.py:1003), so the `"\n- " + text + "\n"` assertion holds | `AssertionError` | odds_report +1 | core/odds/report.py:424; tests/odds_report.py append | 1 |
| T6 | guards, full suite, PR | -- | 0 FAIL expected after C1/C2 are fixed | none | -- |

## 3. Global constraints
| Constraint | Result |
|---|---|
| control_guards `_problems` (imports, endpoints, effects, FORBIDDEN_CALLS) on simulated universe_odds.py, controller.py, session.py, risk.py, store.py | `[]` for each. core.odds is allowed in execution_control (control_guards.py:81); STD has collections.abc, uuid, typing |
| control_guards `_test_process_problems` on simulated control_universe_odds, control_session, control_controller, control_fixtures | `[]` for each |
| Runtime/acting graph (control_guards.py:325, launch_guards.py:334) | OK; `runtime_py()` and `repo_modules()` glob execution_control, so universe_odds.py joins both automatically |
| Repo text guards (acceptance test_08/09/18, macro_m0_harness `_offences`) on the simulated runtime files | clean (lowercase `cano` hits are `canonical`; no uppercase CANO/KIS_ACCOUNT/ACNT_PRDT_CD) |
| compliance_guards raw words / def names, odds `R.guard` on core/odds/report.py with the new `notin.delist` text | clean |
| renewal_boundaries | Only the risk.py surface changes; `problems()` reports only that until line 32 is replaced; new hash 852ae2f20707670b8f0429ec34da5cd338f1aeb5a812c83867f190dfc63b42b0 equals the plan. controller.py and session.py are not pinned |
| Driver identity | controller.py is in `_SOURCE_FILES` (driver.py:35-38) and signer sign.py:1285; the plan says so (P61-62, P1978) and spec section 12 requires a new window. No test pins a controller.py digest |
| Line endings | All 11 edited existing files have 0 CR at fea6e33; new files LF. execution_launch/study.py (CRLF) is not touched |
| Network / real home | New tests use fixtures and temp homes; `Journal(env.home/'other-control')` is valid (state_root() is TRADEGEN_HOME) |
| Commit trailers | `Claude Opus 5.5`, matching this session's attribution reminder |

## 4. Calls into PR 1, PR 2 and PR 3 code
| PR 4a call | Actual | Match |
|---|---|---|
| `rules.universe_top_n(universe, n)` (universe_odds `run_batch`) | PR 1 rules: int n >= 1, largest median first, ties by market | Yes |
| `ctx.universe.snapshot_sha256/.valid_until/.eligible` (session T5) | model.Universe fields day, rule_sha256, snapshot_sha256, built_at, valid_from, valid_until, listed, eligible | Yes |
| `owner.load_context(now, positions)` (universe_odds `_context`) | owner.py:990 `load_context(now, positions, *, session_id=None)` | Yes |
| `ctx.owner.head[1]`, `ctx.active.state_hash` | `OwnerState.head` (seq, sha), default (0, ""); `ApprovedState.state_hash` property | Yes |
| `bars[market].bars`, `.receipt_sha256` | PR 2 `UniverseBars` frozen dataclass; `daily_bars(markets, *, now, clock)` (used by PR 4e, not PR 4a) | Yes |
| controller.py lines cited by PR 4a | PR 3 changed 5 single lines; every cited line unmoved | Yes |

## 5. Moved citations (old -> new at fea6e33)
| Plan line | Cite | Now |
|---|---|---|
| P150 | `tests/control_controller.py:37` (test count) | 38 (C1) |
| P38, P1178 | `plan.py:301` | core/odds/plan.py:302 (N1) |
| P115 | `core/compliance/model.py:230-238` (`seal_context`) | 259-267 (N2) |

Unchanged (checked): controller.py 10, 23, 58-64, 148-151, 168, 170-175, 192, 197, 232-233, 251, 255, 325-328, 352, 432-441,
481, 850-863; all session.py cites; driver.py:35-38; owner.py:791; study.py:59-61; store.py:25-28, 38-42, 216;
coordinator.py:695; launch_owner_ops.py:205, :518; bars.py:335-336, 400-402; simulate.py:404; report.py:424, 787, 1053;
models.py:178, 187; capability.py:17-45; renewal_boundaries.py:32, 133, 159, 163; control_session.py 4/10/23-28/37/40-83/
86-91/97-98/117/156-162/342; control_controller.py 8/12/22-35; control_fixtures.py 30/40/44/54-55; control_acceptance.py 18-20.

## 6. Hazard 5 verdict: PR 4e's to handle; PR 4a code needs no change
- PR 4a (P1107, P1246): `_CLOCK_AGE = 30 s`; `run_batch` refuses `UNIVERSE_BATCH_CLOCK_INVALID` unless
  `0 <= first clock read - now <= 30 s`. The simulation time after that read is not bounded. Its docstring (P1240) already
  defines `now` as "the inputs' time".
- PR 4e (P3126-3129): `now = self._now()`, then `read_bars(universe_top_n(snapshot, n), now=now, clock=...)`, then
  `run_batch(..., now=now)`. `daily_bars` pages 200 candles per GET, so an old coin needs about 17 GETs (3650 days, `_MAX_PAGES` 20).
  Each GET costs at least PACE_S 0.2 s + RTT + a new TLS session (`_send` opens a new `requests.Session`), about 0.4-0.6 s.
  N=3: about 51 GETs, 15-31 s; N=4: 68 GETs, 27-41 s; N=5: 85 GETs, 34-51 s. One 429/5xx retry adds at least 2.2 s; one
  connect timeout adds about 12 s. So for N >= 3-4 the batch realistically refuses every time.
- Second effect: `_context(controller, now)` (P1249) hands the same stale `now` to `Controller._account`, which refuses
  "control clock moved backward" if any row was journaled during the bar read (now < last row utc), and needs the account
  observation `asof` within 30 s before `now`.
- Fix (PR 4e): take `now` after `read_bars` returns (`now2 = self._now()`), refuse if the Seoul date differs from the one
  used for the bars (the daily window is then the same), and pass `now2` to `run_batch`. PR 4e's test at P3008 (same `now`
  for both calls) changes with it. Optional PR 4a text-only tweak at P1239-1241: "take `now` after the bars are read".
  Spec section 17 lists the batch over N coins as a measurement item and sets no 30 s limit for the bar read, so no spec conflict.

## 7. Shared files
- (a) PR 4b plan (`...-pr4b-profile-program.md`, P4b 100-115 and task file lists) touches execution_launch/{profile, strategy,
  program, instrument_refresh, runner, driver (:166), workflow, study, study_review, review_request}.py,
  tools/research/prepare_launch_example.py, tests/{launch_profile, launch_strategy, launch_workflow,
  launch_instrument_refresh, launch_acceptance (MODULES), renewal_boundaries (:35)}.py, and creates tests/launch_program.py.
  PR 4a touches execution_control/{universe_odds (new), risk, controller, session, store}.py, core/odds/report.py,
  tests/{renewal_boundaries (:32), control_fixtures, control_session, control_controller, control_acceptance (MODULES),
  control_universe_odds (new), odds_report}.py.
  **Overlap: tests/renewal_boundaries.py only** -- PR 4a replaces line 32 (risk.py pin), PR 4b line 35 (profile.py pin).
  Lines 33-34 are unchanged between them, so git merges both in either order; PR 4b already states this (P4b 178-180).
- (b) Open PR #23 (local ref origin/claude/floor-state-check 5eddd55; not re-fetched, no network in this scan) touches the
  plan doc, tests/launch_acceptance.py (MODULES append only, `launch_floor_state_check`), tests/launch_floor_state_check.py,
  tools/floor_state_check.py. **No file in common with PR 4a.** (PR 4b shares tests/launch_acceptance.py with #23, but only
  as MODULES appends, which are exempt.)
