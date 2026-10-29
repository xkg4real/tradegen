# Odds engine: pre-flight scan (read-only)

The scan ran against main f3bedd3 (PR #3 merged), with Developer Mode on. Nothing in the repo, the index, HEAD or any
branch was changed. The only file written is this one.

The scan found no blockers. Six findings are important (P1-P6). Every anchor occurs exactly once, either in the tree
or in an earlier task's output. The only drift is in Task 19's two README cells, and the DRIFT RULE (R2-13) plus
Task 19's own fallback text cover it.

## Per-task rows

| Task | Self-consistency | Anchors checked / problems |
|---|---|---|
| 1 | Consistent. Run in a sandbox: Step 2 messages exact; 18 tests; diff 7 files / 978+ / 3- | run_all x3 and README:816: ok (CRLF; Edit tool). Line hints stale (minor) |
| 2 | Consistent. Before: 5 FAIL texts exact; after: 69/69 (Developer Mode) | tables T1/T2 and rules R1-R4: ok. Route-name grep checks 11 of 16 names (minor) |
| 3 | Consistent. RED/GREEN exact; venues sha 283c14...a042a; 70/70 | V1-V3: ok. T3 ok after Task 2 |
| 4 | Consistent. 9 failures before the change; store 36, gate 51, suite 341/341 | S1-S3, G1-G2, F1, O1: ok. R1 ok after Task 2. Brief's line-shift prose wrong (+75, not 43) |
| 5 | Consistent. 25/25 in the sandbox in 1.14 s | fixtures pilots() line: ok after Task 1. 6 mutants survive (minor) |
| 6 | Consistent. 23/23; every pin reproduced | No Edits. The names it consumes from Tasks 2, 3, 5 and the tree: ok |
| 7 | Consistent. 19/19 in about 2.5 s; 209 + 410 lines | Ledger append only: ok |
| 8 | Consistent. 17/17 in 12.9 s; R2-9 lines match | models Edit 1/2: ok after Task 7 |
| 9 | Consistent. 18/18; 31 of 42 mutants killed | odds_ctx tail: ok after Task 5. Hands two tests to Task 10, which never writes them (P1, P2) |
| 10 | Consistent. Before 0/14, after 14/14 and 18/18 | 10 Edits: ok after Task 9. Hand-off tests missing (P1, P2); clip case not reached (P3) |
| 11 | Consistent. Pure parts pass; engine relations hold in a replica | No Edits. Consumed names: ok |
| 12 | Consistent. 1 PASS / 40 FAIL before, 41/41 after; sha pins exact | report Edit 1/2: ok after Task 9. `_pct(0.0)` prints "0.0%" (P4) |
| 13 | Consistent. 13 FAIL before; refusal codes traced | simulate A/B and fixtures tail: ok after Tasks 9-10 |
| 14 | Consistent. 14 columns + 13 pipeline; odds suite 214 | 19 Edits: ok after Task 13. Margins from mock runs (minor) |
| 15 | Consistent. 25/25 in the sandbox; oddsdata guards 5/5 | No Edits. kis_client hint 273 is now 274 (minor) |
| 16 | Consistent. 10 of the 12 test bodies run and pass | No Edits. Consumed names (Tasks 1, 4, 5): ok |
| 17 | Consistent apart from O3-18 | 8 Edits plus appends: ok after Tasks 8-14. Replay x_range set inside run_column (P5) |
| 18 | Consistent. 12 tests; load_plans test runs in scratch | No Edits. Ledger appends: ok |
| 19 | Consistent once Developer Mode counts are used | README Edit 1/2: drifted, DRIFT RULE applies (327 PASS; 1055/1176, 121 not run). Step 8 roles conflict with line 43 (P6) |

## Cross-task rows

| Tasks | Shared | Produces vs consumes | Found |
|---|---|---|---|
| T1 / follow-up compliance_guards | `_suite_names`, NETWORK (26) / DYNAMIC (29), `_dynamic_*`, `_imports` | odds_guards reuses the CG names | All present; only line hints drifted |
| T1 / owner `_guards`, `code_files` | D14 closure seed and the 16 route names | Closure test and ledger rows | Agree; closure has no data layer |
| T1 / run_all + README registration | run_all:50, :57-67, :113; README:816 | odds suite added; compliance registration test reads both | Anchors unique, CRLF; both tests hold |
| T1, T2, T4 / owner-signer helper identity | 7 closure helpers | No task edits them | Identical; signer code_files equals owner's |
| T2 / follow-up rules.py | `_keys`, venue constants, TYPE_CHECKING guard | R1-R4 | Unique; `_guards` unchanged; grep 11 of 16 (minor) |
| T2, T3 / compliance_tables | shape, deposit, `_t5` helpers | T2 adds 4 tests, T3 adds 1 | 69 then 70; ok |
| T2 -> T3 | `_KRX_LADDER`, Venue odds fields | venues.yaml V1-V3 | Parses VALID; sha pin holds |
| T2, T3 -> T5, T13 | Parser, shipped venues | ODDS_VENUES, NOT_TRADABLE | VALID; consistent |
| T3 / gate pins, cli round trip | venues bytes | Gate and CLI tests | Hold |
| T4 / follow-up store, gate, fixtures, owner, rules | Fixtures, `_calendar_line`, `_calendar_approval` | S1-S3, G1-G2, F1, O1, R1 | Unique; 36 and 51; no import added |
| T4 -> T13, T16, T18 | `calendar_in_force`, `grey_rows`, `full_home`, `approve` | Patches and calls | Signatures match |
| T1-T18 -> T19 | Record, README cells | 341, 287, 1477 | Agree with Developer Mode numbers |
| T1 -> T5 -> T9 -> T13 -> T14 | tests/odds_fixtures.py (O3-20) | Appends and edits | Unique anchors; no name used early |
| T9 -> T12 | report.py | Header edit, then append | Clean; ColumnStats has 30 fields |
| T12 -> T13, T14, T17 | `build`, `flags_for`, `*_range`, CATALOGUE | 30 fields passed on every build | Clean |
| T9 -> T10 -> T13 -> T14 -> T17 | simulate.py | 18 edits, 3 appends | Unique. Replay range placement (P5) |
| T9 -> T10 -> T17 | tests/odds_simulate.py | 3 edits | Clean |
| T13 -> T14 -> T17 | tests/odds_pipeline.py | 17 edits | Clean; one stale docstring (minor) |
| T7 -> T8 -> T17 | models.py | 2 edits, 1 append | Clean; GarchParams is kw_only (minor) |
| T5 -> T9, T13, T17 | REFUSALS, check_* order | Q24 order | Clean |
| T6 -> T9 .. T17 | costs API | Every call site | Signatures match |
| T11 -> T12, T14 | bold API | Keyword calls | Clean |
| T12 CATALOGUE -> all | 193 keys, sha pin | `say` keys | All exist |
| T15 / T1 SEAMS | 4 seam names (O3-3) | `_patch_seams` | Identical |
| T15, T16 / T1 guards | Write, import, clock scans | checked_target before every write | Clean |
| T15 / T5 plan | Series, FEEDS, series_md5 | load_leg | Match |
| T15 / clients, isolation | `daily()` signatures, A0 messages | Seams, link tests | Match; hint at :274 |
| T16 / T4, T5, calendars | `calendar_in_force`, CalendarSet, Inputs | `calendar_for`, `begin_run` | Match |
| T17 / T7, T5 | `_input_md5`, `_array_md5`, ReplayInput | Replay pins | Match |
| T17 edits / T9-T14 drafts | 8 old texts | Edits 1-8 | Byte-identical |
| T17 / committed replay files | D13 md5 pins | REPLAY_PINS | All md5s recomputed and equal |
| T18 / T12-T17 | `_run` order, exit codes | CLI | Match |
| T18 / T1 clock and `__main__` guards | `main()` clock, exact `__main__` block | Guards | Clean |
| T17, T18 / config | `load_dotenv` at import | run.py import chain | Writes nothing; KEYLESS (minor) |
| T19 smoke / T18, real home | runpy, stubbed seams | exit 2, STATE_UNUSABLE | No home write; no pem |
| T19 Steps 2-6 / README, record | Cells, Total line | run_check | Developer Mode drift covered (minor) |
| T19 Steps 8-11 / G3-3 | Review, push, PR | Roles | Step 8 is the controller's (P6) |

## Count arithmetic

The counts below are for this PC (Developer Mode on).

- **Start (f3bedd3):** compliance 327 PASS. Full run 1055/1176 passed, 121 NOT_RUN (all of them macro).
- **Compliance:** 327 + 4 (T2) + 1 (T3) + 7 (T4, store) + 2 (T4, gate) = **341** (341/341). The plan's default is
  339/341 with 2 NOT_RUN, which assumes Developer Mode is off.
- **Odds:** 18 + 25 + 23 + 19 + 17 + 18 + 14 + 12 + 41 + 13 + 14 + 25 + 12 + 24 + 12 = **287**. After T14 the suite
  has 214 tests and after T17 it has 238. T10 adds no test. T14 and T17 each replace a pipeline test one for one.
- **Full run:** 1176 + 14 + 287 = 1477 rows, giving **1356/1477 passed, 121 NOT_RUN**, 0 status changes. The
  plan's default is 1354/123. G3-1 covers the difference.
- **README:** 891 lines becomes 892 (the odds row is added).
- **Catalogue and dataclass sizes:** 193 keys; OddsReport 30 fields; ColumnStats 30; PathSpec 27; provenance
  31 keys.
- **Odds time budget:** 200 s.

## Findings and suggested rulings

| Id | Task | Sev | Finding | Suggested ruling |
|---|---|---|---|---|
| P1 | 10 (from 9) | important | Task 9 hands the buy-and-hold enter-once test (after a daily-loss exit) to Task 10. Task 10 never writes it: every daily-loss case uses `_WIDE` | Task 10 adds `bracket=None` to the daily-loss test rows. Assert entries == 1 and v == 101,000 |
| P2 | 10 (from 9) | important | Task 9 hands the KRX-stock cost-side test to Task 10. Every exact charge pin in Task 10 is ETF or crypto, where buy == sell | Task 10 adds a `_hand` KRX_stock_book round trip. Pin the entry at `_rate(...,"buy")` and the exit at `_rate(...,"sell")` |
| P3 | 10 | important | The ladder case of `test_cash_never_below_zero` never pushes the sell rate above 100%. Prices absorb at 3,000, where rate x 4 = 0.675, so the fill, horizon-cost and delist clips go untested | Use prices that reach rate x stress x carry > 1 (e.g. p0 <= 2,000 on the 1,000 tick). Assert that it does. Add a `delist_h` 0.30 run |
| P4 | 12 (and 14) | important | `_pct(0.0)` gives "0.0%". The assumed card can print p0 or u as 0.0%, which breaks "no probability renders as zero" | Task 14 refuses ASSUMED_EDGE_UNREACHABLE when wins == 0. Task 12 prints u == 0 as a bound. Add `_ZERO` tests for p0 = 0 and u = 0. No catalogue key changes |
| P5 | 17 | important | `_replay_column`, inside run_column, sets the replay HIDDEN_EDGE range. O3-18 says the range is set right after run_column, never inside it | `_replay_column` returns nan. The `column()` helper in `_replay_report` sets it with `dataclasses.replace` right after run_column. The asserts at 1203-1207 stay |
| P6 | 19 | important | Step 8 (request review, choose fixes, controller pushes) sits inside the implementer's Steps 1-9, which contradicts line 43 and G3-3 | The implementer runs Steps 1-7. The controller runs Step 8. Step 9 (ledger commit, no push) comes after that. Steps 10-11 are the controller's. Nobody merges |
| P7 | 2, 3, 4, 18, 19 | minor | Expected counts assume Developer Mode is off. This PC gives 69/69, 70/70, 341/341 and 1356/1477 with 121 not run. T19's literal Step 6 commit body has the off-mode numbers | G3-1. The controller pre-states the expected values. Step 6's body is filled from Step 4 |
| P8 | 1, 4, 15, 19 | minor | Line hints are stale: compliance_guards ±3-5, sign.py:718, owner.py:795, store +75, kis_client:274, run_all:119/114 | Anchors are matched by name (R2-13). Task 1's ledger numbers are authoritative |
| P9 | 2 | minor | The route-name grep lists 11 of the 16 `_guards` names and skips the attribute stores | Widen the grep to the 16 names plus the TYPE_CHECKING, `__name__` and `__class__` stores |
| P10 | 2 | minor | The non-str key branches of `_odds_lot` and `_odds_min_order` are not pinned | Add one int-key refusal line each |
| P11 | 1 | minor | The file and network denylist misses logging.FileHandler, ET.parse, linecache, py_compile, winreg and others | Optional: add them (stricter). Otherwise record "left to review" |
| P12 | 1 | minor | Copy of compliance_acceptance (required by A.3.1 and A.15) | No change |
| P13 | 1 | minor | Step 2's "tracebacks, then lines" wording; the output actually interleaves | Read the output as interleaved |
| P14 | 3 | minor | The Consumes list omits `_t5_date` | Add it to the list |
| P15 | 3 | minor | `%B` month name depends on the locale | Optional: use a fixed English month tuple |
| P16 | 3 | minor | NOT_TRADABLE text omits the owner act (deferred) | Keep as a Deferred minor for the controller |
| P17 | 4 | minor | `_calendar_approval` copies `load_context`'s now check | Optional: share a helper |
| P18 | 4 | minor | `grey_rows` rebuilds `_screen`'s intent with no parity test | Add a parity assert against `screen()` |
| P19 | 4 | minor | `owner_key` uses one message for two failure cases | Split the message |
| P20 | 4 | minor | Fixtures now import model at module level, so a model failure takes down every wrapped test | Accepted. Record it in the ledger |
| P21 | 4 | minor | upbit / kis empty-tuple asserts have no positive control | Optional: add one |
| P22 | 4 | minor | A.3.3 "moved verbatim" is not recorded as an erratum | Add a CONTRACT 3.3 erratum ledger line |
| P23 | 5 | minor | Product refusal order is only partly pinned (6 swaps survive) | Add multi-fault cases, or ledger them as untested |
| P24 | 5 | minor | The empty-leg `file` sub runs after horizon, unlike A 5.3. Not ledgered | Add a drift ledger line |
| P25 | 5 | minor | Q24 step 7 sub order vs A 5.3 | Read Q24 as a set; add a ledger line |
| P26 | 5 | minor | `_usable`, `_real` and `_cap_ok` are copied from gate with no parity test | Add parity asserts |
| P27 | 5 | minor | Dead `sizing == "floor_safe"` clause in the replay rule | Leave it, or drop it (no test changes) |
| P28 | 5 | minor | The `plan_hash` assert restates the implementation | Harmless; keep |
| P29 | 5 | minor | `_leg` exact-type check is not pinned | Add a Leg-subclass case |
| P30 | 5 | minor | An np.float64 price is refused (`_real`) | Task 15 keeps Python floats (it already does) |
| P31 | 6 | minor | Two asserts compare literals only | Optional: drop them |
| P32 | 6 | minor | Scalar and vector cost code duplicated | No change (the scalar forms are the oracles) |
| P33 | 6 | minor | Second pin of the shipped ladder date | Accept; both pins move together |
| P34 | 7 | minor | Ledger line has no N/N tails | Append each run's tail, as Task 6 does |
| P35 | 7, 17, 18 | minor | montecarlo and replay imports reach config, which runs `load_dotenv` | Ledger note; KEYLESS covers it |
| P36 | 8 | minor | nu46 does cross 22 on the pilot stream | Reword: "on that test's stream" |
| P37 | 8 | minor | `c_quad` and `_t_mass` duplicate the quad panels | Optional: share a helper |
| P38 | 9 | minor | Six untested `>=`, cash_min and cap mutants survive, despite the "every branch" claim | Add an exact-T case, or ledger them as untested. Do not refactor `_paths` (Task 10 anchors on it) |
| P39 | 9, 14 | minor | Ledger presents the O3-18 x_range placement as a new drift ruling | The ledger line cites O3-18 |
| P40 | 9 | minor | Exact exp equality depends on the CPU's numpy kernel | Note only |
| P41 | 9, 11, 16 | minor | Measured times differ from the briefs (about 2 s, 23 s, 10 s or more) | G3-2: record them |
| P42 | 9 | minor | Small duplications in `_paths` | No refactor (Task 10 anchors on it) |
| P43 | 9 | minor | The fixture block header misstates where the imports live | Reword |
| P44 | 10 | minor | The ledger records 4 of the 6 readings of contract 8.4 | Ledger all six |
| P45 | 10 | minor | `chi` computed twice in the horizon block | No change |
| P46 | 11 | minor | The count-sum assert is always true | Keep it, with a comment |
| P47 | 11 | minor | The positive control returns 0.0 | Optional: use a reachable control |
| P48 | 11 | minor | "even-money" means fair | Reword |
| P49 | 12 | minor | `build()` fills in missing columns, flags or notes | Convert only fields that are present, so a missing field raises TypeError |
| P50 | 12 | minor | `_pct` gives 3 significant figures at a decade edge | Round first. This updates the Step 3d sha pin |
| P51 | 12 | minor | Format helpers duplicated | No change (sha pin) |
| P52 | 13 | minor | `_no_edge_pair` annotation | Cosmetic |
| P53 | 13 | minor | The purity test may flake on a lazy import | If it flakes, the controller rules; never drop the test |
| P54 | 13 | minor | CALENDAR_UNSIGNED relies on the temp home | Note |
| P55 | 13 | minor | Redundant date import | Cosmetic |
| P56 | 14 | minor | The `garch_series` docstring is wrong about nu > 100 | Reword |
| P57 | 14 | minor | ASSUMED refusal built twice | Optional: share a helper |
| P58 | 14 | minor | `at_bound` "recorded" is overclaimed | Reword: "kept in the fit" |
| P59 | 14 | minor | Quoted annotation | Cosmetic |
| P60 | 14, 17 | minor | Margins (pilots, tilt, f* = 1.0, loss share 0.07-0.13) were measured on mock trees | Record the measured values. A miss is a controller ruling, never a reseed or a looser bound |
| P61 | 15 | minor | HISTORY_DAYS, CACHE_ENV and KIS_MAX_PAGES are not pinned | Add one tuple assert |
| P62 | 15 | minor | Fail-closed cache branches untested (keys, lengths, dedupe, bool, manifest keys) | Add refusal cases |
| P63 | 15 | minor | An empty KRW=X frame silently shortens an OKX series | Stricter option: raise when a proxy is needed and the FX part is empty |
| P64 | 15, 16 | minor | Path tests walk the real ~/.tradegen (read-only) | Ledger note if one fires |
| P65 | 15 | minor | Duplication in the loaders | No change |
| P66 | 15 | minor | A redundant assert loop | Harmless |
| P67 | 15 | minor | Seam test patches the real client classes, not fake modules (A 3.1) | Ledger note |
| P68 | 16 | minor | `calendar_for` lets UnicodeDecodeError / YAMLError escape | Also catch them, as ALTERED (refuses more) |
| P69 | 16 | minor | `_number` raises OverflowError on 10**400 | Guard it as `owner._number` does |
| P70 | 16 | minor | The md5-order line is ledgered under drift rulings | Cite O3-13 instead |
| P71 | 16 | minor | Store-altered case says "no signed calendar approval" | Wording only |
| P72 | 17 | minor | Dead `oos_turnover` check after the md5 | No change |
| P73 | 17 | minor | 118-character line; `rsplit` key reliance | Cosmetic |
| P74 | 18 | minor | 7 CLI tests run without OF.chunk() (A 3.4 says all do) | Ledger line |
| P75 | 18 | minor | Two loader readings (start text, float horizon) are not ledgered | Ledger lines |
| P76 | 18 | minor | `_patched` and `_signed_home` duplicated | Optional |
| P77 | 18 | minor | Rerun equality needs the repo unchanged between calls | Note |
| P78 | 18 | minor | Docstring says "nothing written" | Reword: "no odds state written" |
| P79 | 18 | minor | `load_plans -> list` annotation | Cosmetic |
| P80 | 19 | minor | Step 5 CRLF sentence overstates | No change (the 892 check catches a bare LF) |
| P81 | 19 | minor | Owner text says the signer "refuses" a VS Code terminal | Use sign.py:24's "can be refused" |
| P82 | 19 | minor | `state_root` RuntimeError is not in the triage | Add it to Step 7's triage |
| P83 | 8 (A.7.3) | minor | GarchParams is kw_only; A.7.3 says frozen only | Task text wins; ledger as an erratum |
| P84 | 13 | minor | Docstring says the shipped rows have no effective_until | Reword |

## Refuted

| Finding | Task | Why |
|---|---|---|
| Unused `import contextlib` left in compliance_store | 4 / cross | O3-5: it stays, because the follow-up's Edit T0 anchors on it |
| A 6.3 kappa_bound first-date-per-year and the ladder check | 6 | O3-8 already rules every distinct date and every ladder |
| odds_fixtures docstring omits Task 14 | 1 | O3-20 fixes ownership, Task 14 included |
| Spec 8.o item 4 departure has no rev 3.3 bullet | 11 | O3-9 drops the clause. O3-19 lists the bullets and this one is not among them |
| O3-4 cites "README line 161" | 3 | O3-4 says "as CONTRACT 4.2 says", and 4.2 cites domestic_securities_derivatives.md#L161 |
| Shared scratch folder overwritten; repo pyc rewritten | 9 | Scan-environment note, not a plan defect (git status clean, HEAD f3bedd3) |
