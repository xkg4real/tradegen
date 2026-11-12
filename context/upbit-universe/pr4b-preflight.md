# PR 4b pre-flight conflict scan (plan `docs/2026-11-11-upbit-krw-universe-pr4b-profile-program.md` vs tgu-premerge)

Base: tgu-premerge HEAD fea6e33 = origin/main 6d9bf56 + PR 2 (#24 @ 8c9a311) + PR 3 (#25 @ 6eed8b8); tree clean before
and after. P = plan line. Method: all 38 quoted Edit anchors were counted by exact bytes in `git show HEAD:<path>`
(plan CR stripped; `execution_launch/study.py` anchors re-expanded to CRLF). Then the plan was applied in memory, step
by step (each replace asserted to match exactly once in the already-patched text; appends with two blank lines; no
file written to the repo), and an import hook served the patched modules. Executed per stage: the plan's new tests
and every existing test in `launch_profile`, `launch_strategy`, `launch_program`, `launch_capture`,
`launch_review_request`, 16 pure tests of `launch_instrument_refresh`; the new `launch_workflow` test;
`renewal_boundaries.problems` + `check_negative_controls` on the patched source map; `launch_guards.problems` and
`read_text_without_encoding` on all 10 patched `execution_launch` files; the Task 5 AST scan over patched sources.
Not executed (they write temp homes or journals): `launch_study`, `launch_shortened_study`, `launch_driver`,
`launch_runner`, `launch_coordinator`, `launch_live_history`, `launch_study_review`, the other 11 `launch_workflow`
tests and 6 runner/temp-home tests of `launch_instrument_refresh`; reasoned below. Scratch tools: `pr4b_anchors.py`,
`pr4b_sim.py`, `pr4b_merge/` (3-way merge check only).

## Real conflicts: 0 at tgu-premerge (1 conditional anchor break, N1)
| # | Where | Problem | Fix |
|---|---|---|---|
| - | - | None found. Every anchor matches once at its cited line; every RED and GREEN expectation reproduces (texts below); all pinned digests equal today's values; no existing test or guard pin breaks. | - |

## Nits
| # | Where | Problem | Fix |
|---|---|---|---|
| N1 (conditional) | T3 S1 MODULES edit (P903-929) | Two cases only: line 16 `"launch_universe_store")` (PR 2 merged) or line 15 (not merged). Open PR #23 rewrites the same last MODULES line (adds `"launch_floor_state_check"`, diff vs 6d9bf56), and it conflicts with PR 2 there too. If #23 merges before 4b, the grep finds `launch_universe_store` but neither quoted line matches, so the executor must stop (implementer rule). | Add a third case, or say: "append `, "launch_program"` before the closing `)` of the last MODULES line, whatever it holds" (MODULES appends are exempt from the one-PR-per-file rule). |
| N2 | T2 S2 (P583-584), T4 S2 (P1313-1314) | Python 3.13's ImportError text ends with ` (<checkout>\execution_launch\strategy.py)` / `...\program.py)`; the plan's expected row omits that suffix. | Say "starts with". |
| N3 | T3 S3 `_OMIT` comment (P976) | Says `strategy._object` treats the field as absent; `_object` never sees a `ProgramSpec` (`parse_program` has its own two-set rule, P1106). | Reword: "`strategy._plain` leaves it out while None; `parse_program` accepts v1 keys or v1 plus all five". |
| N4 | T5 S1 AST scan (P1452-1463) | Counts only bare-name calls `rule_terms_digest(...)` / `economic_rules_digest(...)`; a module-qualified call or a new alias would escape. None exist today (12 calls, all bare). | Optional: also match `ast.Attribute` calls with those attrs. |
| N5 | T3 S5 (P1149-1150) | The `--stat` pair does not cover the new untracked `tests/launch_program.py` (first commit of that file); T4 S5 covers it later. | Optional: compare `git diff --cached --stat` with `--ignore-cr-at-eol` after `git add`. |
| N6 | T3 S3 `_validate` (P1040-1050) | Stricter than spec 14: L >= 1 and L, m, N <= 4096 (spec only says m >= 1, N >= 1, margin >= 0). Not a conflict. Nothing pairs program kind with protocol revision yet (a trend program can sit under a `forward-universe-v1` protocol and vice versa); harmless in 4b because `run_paper_validation` refuses the universe revision and `target_fraction` refuses the rotation kind, so no evidence or session can form. | Name the bounds in the PR body; PR 5 adds the kind/revision pairing. |
| N7 | T4 S3 `choose` (P1363-1370) | Shape check is shallow: `top_n` element types, flag values, price keys and `held` format are not validated; `ChooserSlot` is frozen but holds caller dicts (unhashable, mutable). Matches the index contract ("state or slot shape"); PR 4d builds the slots. | Info only. |

## 1. Pairs of tasks sharing a file or interface
| Pair | Shared item | Producer -> consumer | Agree? |
|---|---|---|---|
| T1 -> T2 | `rule_terms_digest(rules, *, universe_rule_sha256=None)` | profile P362 -> `strategy._rule_terms` via the existing alias `economic_rules_digest` (strategy.py:23), P643-645 | Yes |
| T1 -> T5 | `LaunchProfile.universe_rule_sha256`, kw selector, universe contract digest | P288, P362, P384 -> 11 call sites, `_bound_profile` P1588-1603, 3 tests | Yes (all PASS in memory) |
| T1 tests -> T5 tests, PR 4c | `RULE`, `Path`, `fixture_profile` in tests/launch_profile.py | P203 -> P1452 (uses `Path`, imported at line 6); 4c plan P177 `from tests.launch_profile import RULE, fixture_profile` | Yes |
| T1 S4 -> T1 S6 | profile.py initialization surface | Step 4 code -> pin P452 | Yes: `_surface` of patched file = `74a77330...0c32` exactly; problems() before the pin = exactly `['execution_launch/profile.py: initialization surface changed']`; after: `[]`, negative controls pass |
| T2 internal | `_rule_terms(rules, universe_rule_sha256)` now 2 required args | P643 -> only caller strategy.py:288, edited in the same step (P706-708) | Yes: no other caller in repo or tests |
| T2 -> T3 | `{"omit_none": True}` metadata read by `strategy._plain` | P628-629 -> ProgramSpec fields P1004-1008 | Yes: `sorted(_plain(TREND))` is the six v1 keys. `_object` not involved (N3) |
| T2 -> T5 | `ForwardProtocol.universe_rule_sha256`, `UNIVERSE_EVALUATOR_REVISION` | P662, P610 -> `_bound_profile` P1592-1596, workflow test P1471-1475 | Yes |
| T3 -> T4 | `_validate`, `_UNIVERSE`, `_decimal(positive=True)`, `Fraction` (program.py:11, already imported), test helpers `rotation`, `rejected`, `TREND`; import lines | P1030-1055, test P807-842 -> P1192 (test lines 7-8, 1 match after T3), P1318 (program line 9 as changed by T3, 1 match; 0 at HEAD as expected) | Yes |
| T3 -> launch_guards | `launch_program` in MODULES | P915 -> `test_launch_suite_is_complete_registered_and_import_errors_fail` | Yes (N1 if #23 lands first) |
| plan <-> index | 4b interface contract (idx P194-207) and deviation (idx P86-88) | plan P155-165, P492-503, P790-801, P1177-1188 | Yes: names, types, `ChooserSlot` flag/price reading, `choose` signature; kind + chooser (T3, T4), revision and `_protocol` (T2), example selector (T5) all in 4b; PR 5 plan P160 says "Verify only" for the example tool |
| 4b -> 4d | lag `ChooserSlot(top_n=(), flags={}, prices=...)` (4d P402) | `choose` checks lag `top_n` is a tuple and `flags`/`prices` are Mappings, never reads lag top_n/flags | Yes |
| 4b -> 5 | 5 P263 greps `^def _rule_terms(rules, universe_rule_sha256)` and `omit_none` | P643, P628 | Yes |

## 2. Per task
| Task | New tests vs code | Expected RED / GREEN (reproduced) | Created / later touched | Anchors at tgu-premerge |
|---|---|---|---|---|
| T1 | 3 tests. Pins `5aebfdf4...`, `96895573...`, `3786c812...` equal the pre-change values (computed on HEAD), so fixed digests are byte-identical. `rejected` uses `exc.code`; `_text` returns its value (profile.py:117-120), so P379 works; value 7 gives PROFILE_TEXT_INVALID. `lot_size` 0.1 with `min_quantity` 0.01 is accepted by InstrumentRules (test PASS) | S3: exactly the 3 rows of P265-267. S5: launch_profile 17/17 PASS. S6: renewal rows and the one-liner exactly as P422-427 | none created; launch_profile touched again by T5 | P185 L4-5, P271 L91-95, P294 L166-167, P310 L261-262, P326 L283-310, P443 L35: each 1 |
| T2 | 3 tests; universe round trip, refusals in the order of `_protocol` (scope -> symbol; revision/selector mismatch -> EVALUATOR_UNSUPPORTED; `'e'*63` -> DIGEST_INVALID); absent key -> EVALUATOR_UNSUPPORTED; explicit null -> JSON_SCHEMA_INVALID (`parse_protocol` calls `_object` first, strategy.py:587). Pins `8d008761...`, `28ea85cb...` equal pre-change values | S2: rows as P583-584 (N2 suffix). S4: launch_strategy 19/19, launch_capture 14/14. launch_study, launch_shortened_study not run: fixed protocols keep identical `_plain` output and `_object` only relaxes an omit_none key | none | 10 anchors (L12, 27, 65-67, 92-94, 127-128, 135, 144-145, 288-289, 418-419, 567-569): each 1, at the cited lines |
| T3 | 3 tests traced and run; `set(body) in (frozenset, frozenset)` compares by equality; trend + universe keys -> UNIVERSE_PARAMETERS_INVALID; `'"0.01"'` occurs once. Pins `19aefe2e...`, `277aa374...`, `965a0081...` PASS before and after the code change | S2: 1 PASS + 2 FAIL TypeError exactly as P937-940. S4 (program part): 3/3. Driver, workflow, study modules use the on-disk artifact at run time | creates tests/launch_program.py (LF); T4 edits it | P944 L9, P956 L18-21, P979 L33-40, P1011 L50-60, P1057 L70-76, P1090 L111-117, P1118 L135-136: each 1; MODULES P906 L16: 1; P918 (PR 2 not merged) L15: 0, expected |
| T4 | 10 tests, one per rule 1-8 plus path and refusals; every assert traced and run. Exact Fractions, decimal-context independent | S2: one row `launch_program/import ImportError: cannot import name 'ChooserSlot' ...` (N2). S4: 13/13 PASS, as P1405 | none | test L7-8: 1 (after T3); program L9: 1 (after T3); append after Task 3's last line |
| T5 | 3 tests. AST scan over patched sources: 12 calls, 0 without selector. `profile` is in scope at every site (example tool line 53). Renewal test: universe form drops tick, so tick 5 -> 1 renews and contract is stable; fee change refused before any registry write | S2: AST AssertionError listing 11 (starts driver 166, instrument_refresh 75 x2, ...), WorkflowError, RenewalError exactly as P1520-1524. S4: new tests PASS; instrument_refresh 16 existing pure tests PASS; renewal problems() `[]` after the `_renew_profile` edit (not in CALLS, surface unchanged) | none | P1528 L75-76, P1544 L150-151, P1559 L166, P1571 L173-181, P1606 L207-208, P1624 L247 (CRLF), P1637 L479 (CRLF), P1650 L87, P1663 L242, P1675 L70: each 1 |
| T6 | Guards: `launch_guards.problems` `[]` and no encoding-less reads for all 10 patched execution_launch files; launch_study static test holds (edits ASCII, inside functions; study.py stays CRLF); PINNED_WRITES untouched | 5 commits, 18 files: count matches Tasks 1-5 | - | - |

## 3. Existing tests and pins vs the plan's changes (item 4)
| Item | Result |
|---|---|
| `tests/renewal_boundaries.py` | profile.py pin updated by the plan (verified value). instrument_refresh.py surface unchanged. CALLS for `profile_body`, `profile_contract_digest`, `_validate_profile` unchanged: no new call; `del body[...]` is a Subscript delete, not an Attribute store; loop name `name` is not trusted |
| Literal 64-hex pins in tests | Only renewal_boundaries (16), compliance_model:178, execution_checks:154, odds_report:28, macro fixtures: none hash a file 4b edits |
| Digests over edited files, computed at test time | program.py artifact (launch_driver:77, launch_review_auth:38, launch_coordinator:1109, launch_workflow:172-185, launch_study:407-418, launch_study_review:74), CAPTURE_FILES manifest (launch_study:743), driver/review sources (compliance_signer:1235; sign.py:1283-1285 `_REVIEW_SOURCES` = the same 8 files as driver.py:35-38): recomputed, still pass |
| Monkeypatches | launch_driver:321 patches `driver.profile_contract_digest` with a one-arg lambda: signature unchanged. Nothing patches `rule_terms_digest` or `_rule_terms` |
| Field loops / asdict | launch_shortened_study:41 loops `fields(ForwardProtocol)`: None == None. No `asdict` or `capability.digest` over LaunchProfile, ForwardProtocol or ProgramSpec anywhere; `paper_capture._plain/_object` handle only their own types |
| `profile_body` consumers | launch_cli:42 template, deployment.py:270, the example tool, docs/launch-profile.example.json: key dropped while None, bytes unchanged |
| Plan's digest statements (P79-94) | Correct: fixed digests unchanged (pins equal HEAD values); real deployments change through `program_digest` over program.py, `capture_source_code_sha256` (study.py:59-61), driver identity and review sources (driver.py:35-38, sign.py:1283), compliance code hash (owner.py:789-798). workflow, instrument_refresh, review_request, study_review are only in the code hash |

## 4. Interfaces from earlier PRs
| Assumed | Actual at tgu-premerge | Match |
|---|---|---|
| PR 1 names | none used (tests use the literal `sha256(b"fixture-universe-rule")`; no `rules.UniverseRule`, `universe_rule_sha256`, `universe_top_n`, `model.Universe`) | Yes |
| `profile_digest(profile)`, `profile_contract_digest(profile)` | profile.py:277, :299, one positional arg | Yes |
| PR 0 driver pin | commits f87d765, 76b89f3 change driver.py away from line 166 (`_identity`); anchor at 166 | Yes |
| PR 2 | launch_acceptance line 16 = `"launch_universe_store")`; renewal_boundaries:25 changed | Yes (as P177-178) |
| PR 3 | profile.py changed only inside `preflight_profile` (old 413-414, now one line using `compliance.context_hash`); surface still `86a4935b...` | Yes (as P179-180) |

## 5. Moved citations
None. All 38 anchors sit at the cited lines. Other cites re-mapped by content and unchanged: strategy.py:172, 587,
600; session.py:172-180; controller.py:151, 170-171; study.py:59-61, 63; workflow.py:232; coordinator.py:804;
driver.py:35-38; owner.py:789-798 (`code_files`, same line at fd85850); compliance_guards.py:583-584;
compliance_signer.py:950; launch_owner_ops.py:239-240; end-of-file lines launch_profile 246, launch_strategy 288,
launch_workflow 323, launch_instrument_refresh 419, program.py 143. Only MODULES moved (15 -> 16), and the plan already
cites both.

## 6. Shared files and parallel verdict
| Plan / PR | Files |
|---|---|
| 4b (18) | execution_launch/{driver, instrument_refresh, profile, program, review_request, runner, strategy, study, study_review, workflow}.py; tests/{launch_acceptance, launch_instrument_refresh, launch_profile, launch_program (new), launch_strategy, launch_workflow, renewal_boundaries}.py; tools/research/prepare_launch_example.py |
| 4a (13) | core/odds/report.py; execution_control/{controller, risk, session, store, universe_odds (new)}.py; tests/{control_acceptance, control_controller, control_fixtures, control_session, control_universe_odds (new), odds_report, renewal_boundaries}.py |
| #23 (4) | docs/superpowers/plans/2026-11-11-floor-state-check.md, tests/launch_acceptance.py, tests/launch_floor_state_check.py, tools/floor_state_check.py |

- 4a vs 4b: one shared file, `tests/renewal_boundaries.py` (4a line 32 risk.py pin, 4b line 35 profile.py pin; a
  scratch 3-way merge of both edits gives 0 conflicts). No shared code file, no interface either way (4a needs PR 3,
  4b needs PR 0/1), and each plan already expects the other may have replaced its own line. Verdict: implement in
  parallel, but the PRs are sequential under the one-open-PR-per-file rule (that file is not a MODULES append): open
  the second after the first merges; its rebase is clean and no anchor or expected output changes.
- #23 vs 4b: only `tests/launch_acceptance.py` (MODULES append, exempt), so parallel is allowed; but see N1 for the
  anchor. `tools/floor_state_check.py` imports `execution_launch.workflow` (`MAX_CONFIG_BYTES`, `read_file`), which
  4b does not touch; the new tool parses and has no `rule_terms_digest` call, so 4b's AST scan is unaffected.

## 7. Spec and index
- Spec 10, 12, 14 bullets assigned to 4b are all covered; `PreparedSession`/controller parts left to 4a as the plan
  says. Omit-when-None, closed-key "old or old plus new", contract and rule-terms forms, every computing site,
  `_bound_profile`, KRW-BTC benchmark symbol, chooser rules 1-8 and the hold count all match the spec text. No spec
  conflict; N6 bounds are stricter than the spec, not contrary.
- Index deviation (kind and chooser from PR 5 to 4b, with `UNIVERSE_EVALUATOR_REVISION`, `_protocol` acceptance and
  the example selector) is carried consistently: T2, T3, T4, T5, the PR body, and `run_paper_validation` refuses the
  universe revision until PR 5's evaluator.
- Commit trailer `Claude Opus 5.5` matches this session's attribution; PR body ends with the required line.
