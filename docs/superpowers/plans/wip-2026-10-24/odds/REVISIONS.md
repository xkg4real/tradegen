# Odds drafts: revisions after the critic round (2026-10-24)

Each issue was checked against the repo (main 995534b), the spec rev 3.2 and RULINGS.md before editing. Own checks
are in `scratchpad/odds_plan/sandbox_revise_odds/` (`replay_facts.py`, `garch_fix.py`, `fmt_check.py`); their
numbers are in CONTRACT 16.1. Tasks were renumbered: old 9 split into 9 and 10, old 12 into 13 and 14, so old
10, 11, 13, 14, 15, 16, 17 are now 11, 12, 15, 16, 17, 18, 19 (19 tasks).

## Critic 1: mathematics and statistics

| # | Issue | Verdict | Reason |
|---|---|---|---|
| M1 | No-edge replay column is a demeaned block bootstrap (blocker) | fixed | Re-measured: E[prod(1+g)] - 1 = +0.27% in 30 days exactly (block_growth); Q38, 7.5, 8.3 now use a fair-sign two-point kernel on block-resampled |g| (stream `replay_sign`), HIDDEN_EDGE with `replay_range`, Task 17 martingale test plus negative control. |
| M2 | L_min per sizing never defined | fixed | Q32 and 8.5: l_min = L under floor_safe, else 0; replay sleeve sized floor-protected (Q38); stop-based wording `ceiling.nofloor`; Task 14 tests 1 in 1,000 vs 1 in 1,999 and the matching CEILING_BREACH. |
| M3 | Ceiling floor(N) prints "1 in 1" on compounding cards | fixed | `fmt_ceiling`: "1 in floor(1/c)" below 1%, "a ceil(1000c)/10 % chance" from 1%; used by every ceiling slot; numbers verified. |
| M4 | CP interval ends rounded symmetrically narrow the interval | fixed | `fmt_end` rounds outward; 0 of 2,000 intervals narrowed (k 1..1000, n 2e5 and 1e6); k = 63 still prints the spec text; Task 12 test. |
| M5 | Seed shopping; comparisons do not share a seed | fixed | Comparison keeps its creation run counter (`comparisons[cid]["run"]`), `--comparison` only for issued ids, R printed (`compare.r`), above-ceiling point estimates print `cap.p`. |
| M6 | GARCH corruption magnitudes cannot fail the checks | fixed | Verified: ratio + 1e-6 moves c by ~1e-10; now c + 2e-6 per node (check 1 fails, 2.0e-6) and ratio x 3 (check 2 z 13.9 at 90 steps); zero drift asserted at 90 steps only (3.8 at 30). |
| M7 | Bold engine test cannot reach the ceiling with the KRW 5,000 minimum | fixed | Optional-stopping argument confirmed; Task 11 runs with lot 1e-12, minimum 0, zero costs, no daily loss, 20,000 paths, no path left running. |
| M8 | HIDDEN_EDGE resolution overclaims and rounds in its favour | fixed | `hidden.pass` says it detects simulator drift only; blind spot printed as 1 in floor((T - L_min)/b) via `fmt_blind`; `hidden.coarse` when b >= T - L_min; Q46 records the spec departure. |
| M9 | x_range not a guaranteed bound (CARRY phi, sample kappa_max, k_x >= 1) | fixed | 10.3: numerator T + CARRY phi', `costs.kappa_bound` at an a-priori p_min (band floor on KRX), status "unbounded" when k_x >= 1; ColumnStats.kappa_max removed. |
| M10 | Header calls liquidation wealth a supermartingale | fixed | Tick-boundary example re-computed (+1.00 KRW); header and Q32 now argue through the gross mark M; documentation test in Task 6. |
| M11 | Average-line SE uses V only | fixed | `ColumnStats.g_se` = std(V + C)/sqrt n drives the 2 SE rule; printed ± stays mean_se; Task 9 test. |
| M12 | Lock release: Q26 (lock session's D) vs 8.4 (current D) | fixed | Spec 7.2 says "that session's D": 8.4 stores `d_lock`, releases at p > d_lock, new triggers use current D; Task 10 tests the (0.7 D_s, D_s] case. |
| M13 | Bracket count nb undefined at p = p0 | fixed | `bold.brackets_needed` (abs difference, inf at p0, 617/153 tested); `assumed.nbmany` when it exceeds the resolved brackets. |
| M14 | variant_block depends on round()'s half-to-even | fixed | math.floor(mult x b + 0.5); Task 7 tests b = 5 -> 3. |
| M15 | "the bug checks are coarser" is not always true | fixed | `{bugs}` slot: `bugs.coarser` or `bugs.finer` chosen by b/(T - L_min) against the interval width (Q32). |
| M16 | Tested replay "40% removed" read against an iid baseline | fixed | Exact `models.block_growth` (2.99% vs 2.70% at 30 days, matches Monte Carlo); `replay.growth` prints both; Task 17 pins it. |
| M17 | spread "other models" when only block variants remain | fixed | spread_kind "blocks" with `spread.blocks` plus `spread.dropped`; Task 14 test with both GARCH members dropped. |
| M18 | Breach sentences can look self-contradictory | fixed | `fmt_order` rounds lb's N down and the ceiling's N up (0.1 precision, or 0.01% percentages) so the printed order matches. |

## Critic 2: repo fit

| # | Issue | Verdict | Reason |
|---|---|---|---|
| R1 | GARCH corruption magnitudes (blocker) | fixed | Same as M6, with the measured values in 7.4 and 16.1. |
| R2 | `_wrap` hides the real seam bodies; set_tz_cache_location untestable | fixed | `REAL_SEAMS` dict in odds_acceptance; seam-body test with a fake `sys.modules["yfinance"]`, never a reload; AST test that the data-importing functions are exactly SEAMS. |
| R3 | chunk() swaps only CHUNK (DEFAULT_PATHS, GARCH_SUB, tilt pilot) | fixed | chunk() also swaps DEFAULT_PATHS and GARCH_SUB; slices range(0, n, GARCH_SUB); tilt pilot via private `_run_paths`; real-CHUNK tilt test; each refit pilot-checked, pilots() also swaps PILOT_NODES. |
| R4 | LADDER / COST_DOMINATED_SHARE in simulate, needed by report | fixed | Moved to report.py; simulate reads report.LADDER. |
| R5 | first_stake KeyError on an unset OKX cap | fixed | check_state(plan, ctx) refuses LIMITS_UNSET for an okx leg without a cap in (0, 1] (gate's `_cap` rule, owner.py:150); first_stake uses .get. |
| R6 | calendar_in_force raises on a naive now before check_inputs | fixed | `plan.check_now` runs first in step 2 (DATA_INVALID sub "now"); Q24 records the one-step addition. |
| R7 | NOT_TRADABLE vs SPECIAL_REGIME order conflict | fixed | check_inputs split into check_data / check_history with terms and check_validity between, matching O10. |
| R8 | Patching store.default is vacuous | fixed | Verified clocks.py:22 and regime.py:19 bind `default` by name; Task 16 patches all three. |
| R9 | Provenance values with underscores break the guard | fixed | 10.1 rendering rule (hash prefixes, versions, counts, labels; no file ids, member keys or CARD_ID); new label keys; Task 12 KRX provenance test. |
| R10 | ColumnStats holds arrays, == raises | fixed | `brackets` is field(compare=False, repr=False); equality tests use dataclasses.replace. |
| R11 | Gate purity tests missing from stay-green lists | fixed | Verified compliance_gate.py:1298 and :1358 (imports set, "datetime"/"ZoneInfo" scan); named in 4.1, 4.4 and Tasks 2, 4. |
| R12 | macro_m0_rules edit breaks O13's intent and the LF list | fixed | No macro_* edit; odds twins of the state-path test in odds_bars and odds_inputs; file maps updated. |
| R13 | `#L159` anchors the header row | fixed | Verified L161 stocks "1 share", L163 ETF "1 unit"; cite #L161 and assert both lines' text (since _t5_ref_ok only checks existence). |
| R14 | Header-comment edit misdescribed | fixed | Verified venues.yaml:1-4; 4.2 quotes the exact replaced clause and keeps line 4. |
| R15 | CLI tests need start 2026-10-24 | fixed | Verified gate.py start check and D12; 3.2 and Task 18 state the dates (2026-10-24 is a Saturday); precheck also refuses a wrong start (C2). |
| R16 | Line references go stale after the follow-up | fixed | CONTRACT header and Global Constraints say "as of 995534b", cite by name; Task 1 re-greps and records. |
| R17 | Hard-link test hits scan_links first | fixed | Task 15 calls bars.cache_dir() before linking and asserts checked_target's message. |

## Critic 3: spec, rulings and coverage

| # | Issue | Verdict | Reason |
|---|---|---|---|
| C1 | Refusal order contradicted by call order | fixed | Same as R7. |
| C2 | No refusal for plan.start != ctx.date | fixed | check_plan sub "start" in the precheck (gate.py:633-634 rule), before any data load; Tasks 5, 13. |
| C3 | Unset OKX cap crashes | fixed | Same as R5. |
| C4 | Dropped headline member undefined | fixed | New MODEL_CHECK_FAILED; non-converged fit drops with check "fit" (at_bound alone recorded; the fixture fit has at_bound ()); Task 14 tests both branches. |
| C5 | IMPOSSIBLE card still prints probability-like lines | fixed | Q44 suppression (plain, spread, BELOW_RESOLUTION; same for no trades); bracket-KRX test moved to Task 14; card-level test. |
| C6 | Replay card statistics not pinned | fixed | REPLAY_PINS gain the card stats and turnover md5 2d4edeb2... (computed); core recomputes bench_sr (equal exactly); limits line names the unsigned md5s. |
| C7 | Comparisons do not share a seed | fixed | Same as M5. |
| C8 | limits.injected overclaims | fixed | Reworded per evidence: hashes recorded but not checkable, only the calendar sha matched, data/macro Saturdays not re-checked. |
| C9 | O11 lowers the KRX stock cost and drops date validity | partly | Ruling kept (tax 0 inside the floor) and raised as an open issue; date validity is O11's own requirement, so it is now copied (`STOCK_SELL_YEARS`, `check_validity`). |
| C10 | Bracket-count formula has no interface | fixed | Same as M13. |
| C11 | Tasks 9 and 12 too big | fixed | Split into 9/10 and 13/14, every reference renumbered. |
| C12 | Header real odds omits the research estimate and KRX cap | fixed | Added 0.01% or less, below 0.01% for crypto spot, 95x to 459x KRX cap, "a bound, not a forecast". |
| C13 | Q41 1,404 vs orders 1,405 | partly | Kept as the existing open issue; Task 19's hand-off now carries the cross-layer difference to E1. |
| C14 | O3 calendar refactor departure unrecorded | fixed | Recorded in Q19 and 4.3 with an equality test. |
| C15 | Catalogue drifts from spec wording | fixed | "at most {cap}×", "(below resolution: under about 3 in n", "can't open:", band-edge session count printed. |
| C16 | Replay card under-specified | fixed | Headline replay_no_edge/base, ceiling.edge under the tested column, HIDDEN_EDGE runs (M1), stress2x column, both cells in ceiling_cells. |
| C17 | Provenance can break the guard; guard only in tests | fixed | Same as R9, plus `render` runs guard and raises (exit 4); Task 18 test. |
| C18 | "no digit-percent" test fails on fixed refusal text | fixed | Task 12 test reworded to computed probabilities only. |
| C19 | Pipeline task needs the replay before it exists | fixed | Task 13 refuses replay legs CARD_NOT_REPRODUCED ("replay not built yet"); Task 17 replaces it. |
| C20 | O5 "test both" and OKX auto_off end to end | fixed | Task 10 tests auto_off and effective_until separately; Task 13 crosses 2026-12-03 (a Thursday) with rule.end and rule.auto. |
| C21 | No spread, refit or dropped-member tests | fixed | Task 14 tests the spread bounds, 20 distinct refits and the dropped note. |
| C22 | Two roundings favour the result | fixed | Same as M4 and M8. |
| C23 | inputs.now checked after the calendar | fixed | Same as R6. |
| C24 | Missing refusals: stale, empty horizon, unsigned code | fixed | DATA_INVALID subs "stale" (STALE_DAYS 3 crypto, 14 KRX/US) and "empty"; STATE_UNUSABLE sub "code" in the precheck (ctx.code_signed exists; full_home signs the code). |
| C25 | Fresh-seed promise not implemented | fixed | compare.fresh reworded (execution's step, not built); carried in Task 19's hand-off; Q46.6. |
| C26 | Red flags render after the numbers | fixed | Render order puts red flags right after the plan head (Q46.5). |
| C27 | Coverage tables lack spec 9/10 rows; 100->70->100 credited wrongly | fixed | New spec 9/10 table; 100 -> 70 -> 100 credited to Task 6; engine band containment test in Task 10. |
| C28 | tree_hash/strategies closures reach core.engine.orders | partly | Verified the only path is a lazy import inside a risk_layer function (risk_layer.py:551) that tree_hash never calls; O1 allows macro_artifacts, so no copy; Task 18 adds a fresh-subprocess sys.modules check. |
| C29 | Missing subs for track/start/name; replay needs fee_extras | partly | Subs added (track, start, file); the replay's fee_extras requirement is kept because O11 names all three terms for every leg, recorded as Q46.7. |

## Round 2: RULINGS_ROUND2.md folded in (2026-10-25)

Every ruling that concerns this plan (R2-1 to R2-9, R2-13, and R2-10/R2-11 where they touch it) was folded into
CONTRACT.md, TASKS.md and header.md in place. Numbering is unchanged: still Q1 to Q46 and Tasks 1 to 19; Q46 item 7
is kept as "withdrawn" so references stay valid, and item 9 is new. Checks are in
`scratchpad/odds_plan/odds/sandbox_round2fold/` (`krx_stock_tax.py`, `prov_copy.py`, run with `-I -B`; numbers in
CONTRACT 16.2). Nothing under the repo was written.

| Ruling | Change | Where |
|---|---|---|
| R2-1 KRX stock sell tax | O11's "tax 0 inside the floor" replaced by the repo's rule: `side_bp(..., side=)` gives `max(35, tick_floor_bp(p, ladder_tick(p), tax_bp=SELL_TAX_BP[year] if sell else 0))`. `STOCK_SELL_YEARS` became a copy of `SELL_TAX_BP` (dict equality). `kappa` takes `side=`, used as buy at entries and sell at exits, V, the stop bound and bold's win side. `cost_refusal` uses the sell side. `kappa_bound` now covers both sides and every tax year of the horizon dates, so HIDDEN_EDGE's range stays a bound. The open issue is removed everywhere. New equality test against `instruments.cost_per_side` with the venues ladder swapped in as a test-local tick table, 2027 sell included (verified exact on 156 points; 46.4 bp sell at 200 KRW). | CONTRACT 0 (Q1 list), Q11, 6.1, 6.3, 6.5, 8.4, 9.1, 10.3, 16.2; TASKS 6, 13, coverage; header GC values, Q11, Architecture, decisions intro |
| R2-2 band edge | Q41 now cites R2-2 for 1,404 and the stray "1,405". `orders.limit_prices` is not changed. The hand-off goes to E3 (take venue-quoted edges, never compute them), not E1. | CONTRACT Q41; TASKS 6, 19, coverage; header Q41 |
| R2-3 departures | New header section "For spec rev 3.3" lists every departure (Q46 items, the layout, new refusals, Q19), plus the two items that are no longer departures (R2-1, R2-5). Q46 says it was accepted by R2-3. | header (new section, Spec paragraph, Q46); CONTRACT top, Q46; TASKS 19 |
| R2-4 fresh seed | Q46 item 6, `compare.fresh` note and the hand-off give the rerun to E2. The text of `compare.fresh` is unchanged (it already says the rerun is not built). | CONTRACT Q46, 10.4; TASKS 12, 19, spec-10 coverage row; header list |
| R2-5 replay terms | `costs.terms(..., replay=True)` needs only `lot` and `min_order`, never reads `fee_extras`, and gives phi 0. Q25, Q38 and `first_stake` use it. Q46 item 7 is withdrawn. Tests: Task 6 (terms), Task 13 (no NOT_TRADABLE for a replay leg without fee_extras), Task 17 (it runs; buy-and-hold on the same venues is NOT_TRADABLE). This reverses the C29 "kept" verdict. | CONTRACT Q11, Q18, Q25, Q38, Q46, 6.2, 6.5, 8.5; TASKS 3, 6, 13, 17, 19; header owner gates, Q11 |
| R2-6 provenance | `repo_anchor`, `tree_hash`, `UNVERSIONED` and `TREE_GLOBS` are copied into `core/oddsdata/inputs.py`, with equality tests on the repo and on synthetic roots (verified). `core/oddsdata` may not import `gate_ledger` or `macro_artifacts`; an odds guard enforces this with positive controls. The run-time `sys.modules` check of Task 18 is dropped, and O1 no longer credits Task 18. This reverses the C28 "no copy" verdict. | CONTRACT 0, Q1, 12, 15, 16.2; TASKS 1, 16, 18, O1 row; header GC, Q1, file map |
| R2-7 unbounded | The `hidden.unbounded` text now holds "unavailable for this plan (no finite range)". It is Q46 item 9 and has a Task 12 assertion. | CONTRACT Q46, 10.3, 10.4; TASKS 12, spec-10 row; header list |
| R2-8 accepted | STALE_DAYS (Q39) and the per-refit pilot checks (Q31) are marked as accepted plan decisions. | CONTRACT Q31, Q39, Q46 item 8; TASKS 5, 14; header Q31, Q39, list |
| R2-9 GARCH margins | The implementer confirms every corruption margin on the real "pilot" stream and records it in the ledger. A check-2 z under 4 SE raises the factor: the ratio multiplier above 3, or a log drift d > 0 in place of zero drift. The thresholds are never lowered and no assertion is dropped. | CONTRACT 7.4; TASKS 8; header GC values |
| R2-10 (follow-up) | The prose DYNAMIC_MODULES list gains `pstats` and `tracemalloc`, the importlib attribute rule, and the note that `faulthandler` stays allowed. The allowlist tests DYNAMIC_MODULES membership with `CG._dynamic_module` (the merged list holds `importlib`). Task 1's precondition checks both. | CONTRACT 0, 15; TASKS 1; header GC |
| R2-11 (follow-up) | The follow-up branches from main's HEAD, not from `995534b`. This plan branches from main's HEAD after the follow-up merges. | CONTRACT top, 0; header GC |
| R2-13 DRIFT RULE | Added to CONTRACT section 0 and to the header's Global Constraints (its own block). It lists the files the follow-up changes and the ones this plan edits, the anchored old/new rule quoted from `5816d3c`, re-read before each Edit, the same change on drift, one ledger line each, stop and rule when the change no longer makes sense, and the same rule for reused helper names. New execution ledger `docs/superpowers/plans/2026-10-24-odds-engine-execution-ledger.md`: Task 1 starts it with `git diff --stat 5816d3c HEAD -- . ':!docs'` and the merged line numbers; Task 19 commits it. Per-task drift anchors were added to Tasks 1 to 4 and 19. | CONTRACT top, 0, 2 (file table, docs/ exception); TASKS legend, 1-4, 19, coverage; header GC, file map |

Incidental fixes, made while touching the same lines:
- CONTRACT 8.4 step 2 read `ks = kappa(p) * mult`, but `kappa` already multiplies by `mult`. It now calls
  `costs.kappa(terms, p, on_j, mult, side="sell")` explicitly, with mult applied once, and step 5 defines `kb` the
  same way.
- Task 19's hand-off is split by sub-project, following the E1 spec section 1:
  - E1: the interfaces it inherits and live balances.
  - E2: the zero-stake rule, the OKX cap, the daily-loss and floor halts, and the fresh-seed rerun.
  - E3: the band edges.
- A new coverage table "RULINGS_ROUND2 item | Tasks" was added, and the task headings carry their R2 items.
