# Odds plan: task list (scope of each task; the drafter writes the full task text)

Spec section numbers refer to the rev 3.2 spec. "8.oN" means spec section 8, odds list item N (1 martingale law,
2 HIDDEN_EDGE, 3 exact values, 4 mechanics, 5 ledger, 6 refusals, 7 the D13 replay, 8 seeds, 9 report). "O<n>" is a
RULINGS item, "R2-<n>" a RULINGS_ROUND2 item (it amends RULINGS and wins where they disagree), "Q<n>" a contract
decision (CONTRACT.md section 1). Every task runs the QUANTGEN overlap check before each test command, restores
`qa/acceptance_results.json` after each `--suite` run, checks `git diff --cached --stat` against
`--ignore-cr-at-eol` before committing, and commits once with the writing model's `Co-Authored-By:` line. Every task
that changes `core/` also runs the core-wide scans of CONTRACT section 0. Line numbers cited into existing files are
as of main 995534b; the plan is written against main 5816d3c (equal to 995534b outside docs/), so every Edit of an
existing file is an exact old-text/new-text pair quoted from 5816d3c that names its anchor (function, constant, test,
YAML row or table row), applied under the DRIFT RULE of CONTRACT section 0 (R2-13): re-read before each Edit; if the
old text differs only because the follow-up changed it, make the same change to the current text, keep the
follow-up's behaviour and record a one-line ruling in the execution ledger; if the change no longer makes sense, stop
and rule.

## Task 1: Branch, packages, odds suite, odds guards, registration (O1, O2, O13; R2-6, R2-10, R2-13; Q1, Q2, Q13, Q40)
- Precondition check, then `git switch -c odds-engine` from main's HEAD: `main` holds the follow-up merge, and
  `tests/compliance_guards.py` no longer asserts the literal "paper, grokteam or compliance" (F7) and defines
  `_dynamic_module` with `pstats` and `tracemalloc` in `DYNAMIC_MODULES` (R2-10). If any fails, stop and report.
- Start the execution ledger `docs/superpowers/plans/2026-10-24-odds-engine-execution-ledger.md` (CONTRACT section 0;
  untracked until Task 19): the branch, the main HEAD it was cut from, the list `git diff --stat 5816d3c HEAD -- .
  ':!docs'` prints (the files the follow-up changed, where the DRIFT RULE can apply), and empty "Drift rulings",
  "Deferred minors" and "Runs" sections. Re-grep every name CONTRACT's header cites by line (`owner._module_file`, the
  `code_files` glob seed, the `minimum_krw` line of `test_venue_shape_rules`, `TABLES` and `NOW` .. `_full_home` in
  `compliance_store`, the registration check in `compliance_guards`, the start check and `Screening.flags` in
  `gate.py`) on the merged main and record the new line numbers in the ledger.
- Create `core/odds/__init__.py` and `core/oddsdata/__init__.py`, both 0 bytes.
- Create `tests/odds_acceptance.py` (CONTRACT 3.1: MODULES, `_wrap` with hermetic, temp home, the four seam patches
  once `core/oddsdata/bars.py` exists with the real functions kept in `REAL_SEAMS`, the real-home watch of
  `~/.tradegen/odds` and `~/.tradegen/compliance`, the repo-file watch of venues.yaml, the S_C3 cache, card and
  results.csv; `tests()`, `_main`, `__main__`).
- Create `tests/odds_fixtures.py` with `chunk()` (CHUNK, DEFAULT_PATHS, GARCH_SUB) and `pilots()` (PILOT_PATHS,
  TILT_PILOT, PILOT_NODES) only (CONTRACT 3.2; later tasks extend it; both import their modules when entered).
- Create `tests/odds_guards.py` (CONTRACT 15): the O1 allowlist over `core/odds/*.py` (the merged compliance lists
  read at test time, `DYNAMIC_MODULES` membership through `CG._dynamic_module`, so R2-10's `pstats` and `tracemalloc`
  bind with no odds change); no clock, no `__main__`, no file I/O, no package re-export, no subfolder `.py` in
  `core/odds`; empty inits; `core/oddsdata` raw words, forbidden imports (orders in every form, any `core.engine`,
  forward_sim, refusal, context-log modules, the study runner, `core.quant.gate_ledger` and
  `core.ficc.macro_artifacts` (R2-6), dynamic imports), the clock only in `run.py`'s `main()`, every write preceded by
  `checked_target`; the D14
  closure holds no file under `core/oddsdata/`, `data/`, `config.py`, `core/quant/`, `core/calendars/`, `core/engine/`
  (O1); the odds registration twin; the three harness self-tests. Each checker has a positive control (a synthetic
  offender under `core/odds/x.py` or `core/oddsdata/x.py`).
- Register the suite in `tests/run_all.py` (CRLF; Edit tool): the import after the compliance line, the `odds/` prefix
  in `tests()`, and the `--suite` help text "..., grokteam, compliance or odds"; the same list in `README.md:816`
  (CRLF; the follow-up edits other README lines, so this Edit names its anchor, the suite-list line, under the DRIFT
  RULE). The README table row waits for Task 19.
- Covers 8.o: setup ("Existing guards stay in force"). RULINGS: O1 (closure test, flat core, inits), O2, O13 (suite,
  wrapper, registration, budgets); R2-6 (the oddsdata import ban, with positive controls), R2-10, R2-13 (ledger,
  drift list).
- Verify: `-m tests.odds_acceptance` all PASS; `--suite odds` exit 0 with `odds/odds_guards/...` rows (restore the
  results file); `-m tests.compliance_acceptance compliance_guards/` and `compliance_store/` PASS (the closure now holds
  `core/odds/__init__.py`, which `test_code_files_is_the_import_closure` expects); `--suite cockpit` PASS.

## Task 2: The venues parser learns the odds keys (spec 5.1 "Venue facts", 7.2 "Costs, minimums"; O3, O11; R2-13; Q17)
- `core/compliance/rules.py`: `_VENUE_OPTIONAL` gains `lot`, `min_order`, `fee_extras`, `tick_ladder`; `Venue` gains
  the hashable defaulted fields `lot`, `min_order`, `fee_extras`, `tick_ladder`, `odds_sources` and the pure lookups
  `lot_for`, `min_order_for`, `ladder_for` (CONTRACT 4.1: no `parse_date` call, no file, clock or zone name, no new
  import); private `_odds_lot`, `_odds_min_order`, `_check_extras`, `_odds_ladder`, `_odds_number`. Strict types,
  finite values, `fee_extras` >= 0 (`check_extras` lives in the parser), ladders from 0 and strictly increasing,
  ladder books outside `KRX_ETF_line`, a mandatory `source` per key.
- Drift (R2-13): the follow-up changes both files of this task (`rules.py` moves `_VENUE_OPTIONAL` down about 31 lines
  and edits `_row`; `tests/compliance_tables.py` gains tests and rewrites assertions). Anchors: the constant
  `_VENUE_OPTIONAL`, the class `Venue`, the parser `_venue(vid, entry, instruments)` that reads it, and the test
  `test_venue_shape_rules` (its `minimum_krw` line); each Edit quotes its old text from 5816d3c.
- `tests/compliance_tables.py`: the `minimum_krw` line of `test_venue_shape_rules` (:633) stays (an unknown key is
  still refused) and gains one refusal line per rule; a valid fixture venue file with all four keys parses to exact
  tuples; `lot_for` falls back to `default`; `test_valid_fixture_venues_parse`'s `rules.Venue(...)` equality still
  holds (defaults).
- Stay green unchanged: every byte pin (`tests/compliance_gate.py:336-340, :695-697, :998-1000`; the shipped bytes do
  not change in this task), `test_shipped_venue_facts_p22`, and the two gate purity tests that scan what this task
  touches: `test_gate_call_graph_has_no_clock_zone_file_or_socket` (it AST-scans the rules classes the gate reaches,
  `Venue` included, for the `_T9_FORBIDDEN` names) and `test_purity_no_file_clock_zone_or_network` (it traps
  `rules.date`, `rules.Path` and `rules.os` during screen and decide).
- Covers 8.o: 5 (groundwork: extras may only raise costs). RULINGS: O3 (parser), O11 (missing values make a leg not
  tradable; an explicit 0 parses); R2-13 (both edited files drift).
- Verify: `-m tests.compliance_acceptance compliance_tables/` and `compliance_gate/` PASS; `--suite compliance` exit 0.

## Task 3: Sourced odds values in the shipped venues.yaml (spec 5.1, 7.2; O3; R2-5, R2-13; Q18)
- `core/odds/venues.yaml` (LF): the added lines of CONTRACT 4.2 (kis `lot` 1 for 005930 and 069500 and kis
  `min_order {KRW: 0}`, both citing `#L161`; the KRX stock `tick_ladder` with `effective_from: "2026-10-02"`; upbit
  `min_order {KRW: 5000}`) and the one comment edit, which replaces exactly the header clause "the odds plan adds lots,
  minimums and ticks later, which changes this file's sha256 and needs a new approval." and keeps line 4. No
  `fee_extras`, no Upbit, OKX or US lot, no deposit network.
- `tests/compliance_tables.py`: a shipped-file test pinning the parsed odds fields exactly, no `fee_extras` on any
  venue, every odds source passing `_t5_ref_ok` or an https URL of the corpus, and the research file's line 161
  starting `| KOSPI/KOSDAQ cash stocks` with `| 1 share |` and line 163 starting `| Plain 1x ETF/ETN` with `| 1 unit |`
  (`_t5_ref_ok` alone only checks that the line exists); the URL test already scans the file.
- State in the task (and later on the card's refusal) that every leg is NOT_TRADABLE in the shipped draft until the
  owner adds explicit fixed charges (0 allowed) and the missing lots, and signs the venues file (the replay leg needs
  only the Upbit lot beside the shipped Upbit minimum, R2-5).
- Drift (R2-13): the new shipped-file test is appended to `tests/compliance_tables.py`, which the follow-up changed;
  its anchor is the test it follows (named in the task), quoted from 5816d3c.
- Covers 8.o: 5 (tick floor inputs), 6 (NOT_TRADABLE groundwork). RULINGS: O3 (sourced values only), O11; R2-5 (the
  replay leg's lot), R2-13 (`tests/compliance_tables.py` drifts).
- Verify: `--suite compliance` exit 0, including the three byte pins, the shape pins and the research-URL test.

## Task 4: Compliance helpers for the odds engine (spec 4, 6.3, 11; O3, O6; R2-13; Q19, Q20, Q21)
- `core/compliance/owner.py`: `_calendar_approval(now)` and public `calendar_in_force(now)` (CONTRACT 4.3).
- `core/compliance/rules.py`: `_calendar_line` maps `owner._calendar_approval(moment)` onto its four existing lines.
- `core/compliance/gate.py`: public pure `grey_rows(plan, ctx)` (CONTRACT 4.4): no new import, none of the
  `_T9_FORBIDDEN` names, and the words `datetime` and `ZoneInfo` nowhere in its docstring or comments.
- `tests/compliance_fixtures.py`: the moved public `TABLES`, `NOW`, `HELD`, `pubkey_at`, `owner_key`, `sign`,
  `approve`, `other_code`, `full_home` with the new `venues_raw`, `calendar_raw`, `limits`, `cap` keywords
  (CONTRACT 3.3); `tests/compliance_store.py` binds its old private names to them, so no test body changes.
- Drift (R2-13): the follow-up changes `owner.py` (`_guards`, `_skipped`, `_import_nodes`, `_repo_imports`),
  `rules.py` and `tests/compliance_store.py` (its synthetic tree; the signed-home helpers move down about 20 to 30
  lines). Anchors, by name: `owner._owner_now` and `owner.load_context` (the new functions reuse their checks; the
  task quotes its insertion point), `rules._calendar_line`, the constant `TABLES` and the helpers `NOW` .. `_full_home`
  of `compliance_store`; the moved helpers are copied from the merged file, keeping any follow-up change inside them.
  `gate.py` is not changed by the follow-up.
- Tests: in `tests/compliance_store.py`, `calendar_in_force` is None with no key, with a broken log, with no calendar
  approval, after the stored copy is altered, and for an approval stamped after `now`; it returns the sha in a full
  home with `calendar_raw` = `rules.calendar_stream(fixture_set().data_dir)`; ValueError on a naive `now`; on every
  one of these cases `calendar_in_force(now)` is the sha exactly when `_calendar_approval(now) == ("ok", sha)` (Q19's
  recorded departure from O3's wording). In `tests/compliance_gate.py`, the `grey_rows` cases of CONTRACT 4.4. The
  existing calendar-line tests of `tests/compliance_cli.py`, `test_gate_call_graph_has_no_clock_zone_file_or_socket`
  and `test_purity_no_file_clock_zone_or_network` stay green unchanged.
- Covers 8.o: 6 (CALENDAR_UNSIGNED groundwork: files lacking a signed owner approval). RULINGS: O3 (calendar_in_force,
  grey_rows, fixtures), O6 (the signed calendar sha); R2-13 (`owner.py`, `rules.py`, `compliance_store.py` drift).
- Verify: `--suite compliance` exit 0; `-m tests.compliance_acceptance compliance_cli/` PASS.

## Task 5: Plan types, injected inputs and the product, state and data checks (spec 7.1, 7.2 "Data rules"; O4, O7, O8; R2-8; Q4, Q7, Q8, Q23, Q24, Q25, Q39)
- `core/odds/plan.py` (CONTRACT 5): every constant (`STALE_DAYS` included), `Bracket`, `Fraction` with `fixed`,
  `kelly`, `bold`, `Leg`, `Plan`, `Refusal`, `Series`, `Provenance`, `ReplayInput`, `Inputs` (with `plan_runs`);
  `series_md5`, `plan_hash`, `instrument`, `section`, `check_plan`, `check_state(plan, ctx)`, `check_now`,
  `check_data`, `check_history`.
- `tests/odds_fixtures.py`: `ODDS_VENUES`, `venues_with`, `series`, `plan`, `odds_ctx`.
- `tests/odds_plan.py`: the whitelist (kis 005930, 069500, AAPL, SPY; upbit BTC, USDT; okx BTC pass; bithumb, coinone,
  korbit, gopax venues, okx USDT, TQQQ, 252670, SH, IBIT, BITO, a fixture option each refused with its sub-reason);
  MULTI_LEG_UNSUPPORTED for a tuple of two legs; every range rule of Q25 with its sub (`file` for a non-text name,
  `track`, `numbers`, `start` for a non-date start and for a start other than `ctx.date`, `horizon`); the instrument
  comes from `ctx.active`, never the draft (a draft-only symbol is refused); STATE_UNUSABLE for a hand-built context,
  a broken owner and an invalid active state, and sub `code` for `F.ctx(code_signed=False)`; LIMITS_UNSET when either
  limit key is missing, while a floor of 0 counts as set; LIMITS_UNSET sub `cap` for an okx leg whose context has the
  limits but no `okx_equity_share` cap (no KeyError anywhere); `check_now` refuses a naive `now` and one whose Seoul
  date is not `ctx.date`; every DATA_INVALID rule of Q39 with its sub (`series`, `stale` at 4 days for crypto and
  15 for KRX but not at 3 and 14, `sessions`, `empty`); SYNTHETIC_REFUSED; SPECIAL_REGIME at 59 KRX bars and not at
  60; SHORT_HISTORY at 249 bars; `series_md5` equals a hand-built canonical JSON md5; `plan_hash` ignores the name.
- Covers 8.o: 6 (UNSUPPORTED_PRODUCT, MULTI_LEG_UNSUPPORTED, LIMITS_UNSET, SYNTHETIC_REFUSED), 8 (renaming changes
  nothing, at the plan hash). RULINGS: O4, O7 (refused venues and feeds), O8, O10 (refusal order, part), O13 (fixtures);
  R2-8 (STALE_DAYS 3 and 14 accepted).
- Verify: `-m tests.odds_acceptance odds_plan/` and `odds_guards/` PASS; compliance guards and store PASS.

## Task 6: Costs, venue terms, bands, affordability and stakes (spec 4 "Costs", 7.1, 7.2 "Bands"; O10, O11; R2-1, R2-2, R2-5; Q11, Q27, Q28, Q41)
- `core/odds/costs.py` (CONTRACT 6): the copied constants (`COMMISSION_BP`, `TABLE_BP`, `ETF_TICKS`,
  `SELL_TAX_BP`, `COST_STRESS`, `LIMIT_DOWN_CARRY_COST_MULTIPLIER`, `DELIST_STRESS`), `NotTradable`, `Terms`,
  `terms` (with `replay=`), `etf_tick`, `ladder_tick`, `tick_floor_bp`, `side_bp` and `kappa` (both with `side=`),
  `check_validity`, `kappa_bound` (over both sides and the horizon dates), `band`, `r_exit`, `afford`,
  `floor_units`, `ceil_units`, `min_units`, `rule_units`, `net_win_coefficient`, `first_stake`, `cost_refusal`.
- `tests/odds_costs.py`: equality of every copy (`instruments.COMMISSION_BP`, `validate.COST_BP_PER_SIDE` per book,
  `instruments.TICK_TABLES["KRX_ETF"]`, `instruments.SELL_TAX_BP` (the dict, exactly), `validate.GATE["cost_stress"]`,
  `tf_books.DELIST_STRESS`, the orders constant by `ast.literal_eval` without importing orders); `side_bp` equals
  `instruments.cost_per_side("KRX_ETF_line", p, on=d, side=s).bp` on a price grid (1 to 1e6) and dates from
  2023-12-11, both sides, and both raise before that date; the 2,005-KRW ETF fill costs >= 13.8 bp (13.8688) on both
  sides in 2026; the KRX stock floor (R2-1): `side_bp(stock_terms, p, d, side=s)` equals
  `instruments.cost_per_side("KRX_stock_book", p, on=d, side=s).bp` with the venues ladder swapped in as a test-local
  tick table (`instruments.TICK_TABLES[<key>]` in the original's row form, effective from the ladder's
  `effective_from`, and `instruments.INSTRUMENT_BOOKS["KRX_stock_book"] = dataclasses.replace(book,
  tick_table=<key>)`, both restored in `finally`; never a permanent change, which T-COST-02 forbids) on a grid of
  prices (1 to 1e6, the row starts and 148, 149, 367, 368 included), 2026 dates and both sides, and on a 2027 date: a
  2027 buy equal on both, a 2027 sell raising `costs.NotTradable` exactly where the original raises
  `instruments.NotTradable` (CONTRACT 16.2: 46.4 bp sell and 35 bp buy at 200 KRW); US 50 bp and crypto 10 bp with no
  floor until a ladder is signed; no separate sell tax on top anywhere; `kappa` equals `side_bp` element by element on
  both sides; `check_validity` raises for a KRX ETF date before 2023-12-11, a KRX stock date in 2027 (like
  `instruments._sell_tax_bp`, so the leg is NOT_TRADABLE), and a date before the ladder's `effective_from`, and passes
  a 2026 horizon; `kappa_bound` equals the brute-force maximum of `side_bp` over both sides and a fine price grid above
  p_min on both ladders (the maximum sits at p_min or at a row start, e.g. 2,000 on the ETF table; on the stock ladder
  it is the sell side's, 71.4 bp at p_min 100 against 51.4 bp for the buy); `terms` raises for a missing lot, minimum,
  `fee_extras` or KRX stock ladder, and accepts explicit zeros; `terms(..., replay=True)` accepts an upbit venue with
  no `fee_extras` (phi_buy = phi_sell = 0.0) and still raises for a missing lot or minimum (R2-5); the
  band at ref 2,005 is [1,404, 2,605] (Q41, R2-2); bands keep a price inside them across sessions, including 100 -> 70 ->
  at most 91 on the stock ladder and back up to 100 within the following bands (spec 8.o1 "100 -> 70 -> 100"); D <= ref
  <= U on random refs and limits; the always, floor-safe and stop-based bounds on random inputs under both scenarios
  plus the carry (cash after the worst exit >= 0; floor-safe cash after a total loss >= L); lot rounding up and down;
  a stake below the minimum is no bet while an affordable stake below it is at_floor; bold's reaching stake rounds up
  when affordable and is cut to the affordable stake otherwise; `first_stake` on an okx leg reads the cap with `.get`;
  `cost_refusal` returns "4kappa" and "bold" in their cases; a documentation test of Q32's "why the ceiling holds":
  a KRX ETF unit at 2,001 moving to 1,999 or 2,003 with probability 1/2 each keeps E[p] = p, while the liquidation
  value per unit (p less one side's charge) rises in expectation by 1.00 KRW (1,998.22 -> 1,999.22), so the ceiling's
  proof rests on the gross mark, never on V.
- Covers 8.o: 1 (band containment, 100 -> 70 -> 100), 4 (bold's reaching stake rounds up when affordable), 5 (always
  rule >= 0 under 2x stress plus carry, floor-safe >= L, bold refused when the net coefficient <= 0, the 2,005-KRW tick
  floor, no separate sell tax). RULINGS: O1 (copies with equality tests), O10 (band rounding per edge), O11 (date
  validity copied); R2-1 (the KRX stock sell tax inside the floor, equal to the original), R2-2 (1,404), R2-5 (replay
  terms).
- Verify: `-m tests.odds_acceptance odds_costs/` PASS; guards, compliance guards and store PASS; core-wide scans.

## Task 7: The two-point bootstrap, block lengths, the index generator and the seeds (spec 7.2, 7.3; O10, O12; Q10, Q34)
- `core/odds/models.py` part 1 (CONTRACT 7.1, 7.2): `LIVE_SHARPE_MULTIPLIER`, `Z_BOUND`, `TRADING_DAYS`, `NU_NORMAL`,
  `_optimal_block_length`, `pw_block`, `sharpe`, `rows`, `block_length`, `variant_block`, `indices`, `tilt`, `kernel`,
  `STREAMS` (with `replay_sign`), `SEED_TAG`, `data_hashes`, `market_seed`, `seed_sequence`, `stream`.
- `tests/odds_models.py`: `pw_block` equals `gate_stats.pw_block(x, kind="stationary")` exactly on AR(1), white-noise
  and heavy-tailed series of 20 to 3,000 points; `block_length` floors at 1 (white noise); variants round half up
  (`variant_block(5, 0.5, n)` is 3.0, `variant_block(3, 0.5, n)` is 2.0, `variant_block(1, 0.5, n)` is 1.0) and cap at
  the history length; the generator's mean block is within 3 SE of `block` and every row is uniform; E[next | p] = p
  to 1e-12 relative on random p, m and bands, the tick-clamped edges included; prices stay inside [D, U]; a price at
  an edge stays there; `tilt(q, 0) == q` and is increasing in theta; `sharpe` equals `validate.sharpe`;
  `market_seed` follows the Q34 bytes exactly (a hand-built hash), ignores plan fields and changes with each input;
  `stream` passes a SeedSequence through `default_rng`; two streams with different chunk or name differ.
  Two test-only references show the traps of spec 7.2 fail the martingale check: `core.quant.montecarlo` with
  `drift="zero"` (terminal mean above 1 by more than 4 SE on a fixture) and a rev-1 per-row demeaned block bootstrap
  with a stop rule on an AR(1) fixture (a mean payoff away from 0 by more than 4 SE).
- Covers 8.o: 1 (E[next | p] = p to 1e-12, prices inside the band, drift="zero" and per-row demeaning fail), 8
  (streams shared, renaming changes nothing). RULINGS: O1 (pw_block, LIVE_SHARPE_MULTIPLIER, Z_BOUND copies), O10
  (block lengths, generator), O12 (seed).
- Verify: `-m tests.odds_acceptance odds_models/` PASS; guards; core-wide scans.

## Task 8: The GARCH-t copy and its pilot checks (spec 7.2 "GarchT"; O1, O10; R2-9; Q10, Q31)
- `core/odds/models.py` part 2 (CONTRACT 7.3, 7.4): `GarchParams`, `fit_garch_t`, the copied likelihood and fit
  helpers, `t_density`, `_t_scale`, `_draw_z`, `_log_mgf`, `_correction_table`, `martingale_correction`,
  `simulate_garch`, `simulate_garch_series`, `PILOT_*` constants, `c_quad`, `pilot_checks`.
- `tests/odds_garch.py`: `fit_garch_t` equals `garch.fit_garch(r, profile=False)` field by field on a fixture series
  (`garch.simulate_garch_series(2e-6, 0.08, 0.90, 6.0, n=1500, seed=1)`, nu about 5.6) and on a near-normal one;
  `simulate_garch`'s returns equal `garch.simulate_returns(..., rate_daily=0.0, bound=garch.Z_BOUND)[0]` exactly for
  the same SeedSequence; `martingale_correction` and `_correction_table` equal garch's; both pilot checks pass on
  fixture fits (nu about 4.6 and about 5.6) at 30 and 90 steps, with 20,000 paths and 512 nodes (no `pilots()` swap);
  the corruption test of CONTRACT 7.4: the ratio column plus `2e-6 / grid ** 2` (c + 2e-6 at every node) fails check
  1 with "deterministic" at 30 and 90 steps, the ratio x 3 fails check 2 with "statistical" at 90 steps
  (monkeypatch `core.odds.models._correction_table`, clear the lru cache, restore in `finally`); zero LOG drift
  (`garch.simulate_returns(..., drift_daily=0.0)` fed to check 2) fails at 90 steps (it is not asserted at 30, where
  the fixture's z is 3.8); the contract states the detectable drift, about 4 sigma / sqrt(N h) per step; fewer than
  100 returns raises ValueError.
- R2-9: the margins above are sandbox numbers. The implementer runs each corruption on the real "pilot" stream (the
  draws `pilot_checks` makes from `seed_sequence(seed, 0, "pilot")` with the test's fixed seed; the zero-drift returns
  from `garch.simulate_returns` on the same SeedSequence) and records every measured margin in the execution ledger.
  A check-2 z under 4 SE raises that corruption's factor (the ratio multiplier above 3, or a log drift d > 0 in place
  of the zero drift), recorded there; `PILOT_SE`, `PILOT_STEP_TOL` and `PILOT_SUM_TOL` are never lowered and no
  corruption assertion is dropped.
- Covers 8.o: 1 (both GARCH pilot checks pass on fixture fits and fail on a corrupted correction table; a stop, a
  bracket and buy-and-hold have mean payoff 0 under GARCH-t is Task 9's). RULINGS: O1 (the GARCH-t copy with its
  equality tests), O10 (pilot sizes, nodes, thresholds, corruption test); R2-9 (margins confirmed on the real
  stream).
- Verify: `-m tests.odds_acceptance odds_garch/` PASS within 25 s; guards; core-wide scans.

## Task 9: The path engine, part 1: moves, entries, exits, ledger and outcomes (spec 7.1 "Rounding and re-entry", 7.3; O10, O11; Q22, Q26, Q27, Q28)
- `core/odds/simulate.py` part 1 (CONTRACT 8.1-8.4): the constants, `Checks`, `checks`, `PathSpec`, `run_column` and
  the private `_run_paths` for the bootstrap and garch engines: the moves of 8.3, the entries and the target,
  take-profit and stop exits of 8.4, the ledger, REACHED, AT_FLOOR, RUNNING and first passage, re-entry (locks, daily
  loss, rule dates, delisting and the OKX cap are Task 10's; the replay engine is Task 17's).
  `core/odds/report.py` is created here with `LADDER`, `COST_DOMINATED_SHARE` and `ColumnStats` only (Task 12 adds the
  rest); `ColumnStats.brackets` is `field(default=None, compare=False, repr=False)`.
- `tests/odds_fixtures.py`: `inputs`, `even_rows`.
- `tests/odds_simulate.py` (all under `OF.chunk()`): a stop, a bracket and buy-and-hold have mean payoff 0 before costs
  (gross X within 4 SE) under the bootstrap and under GARCH-t; AT_FLOOR under floor-safe sizing keeps between L and
  L + X with X <= the minimum stake plus phi_buy plus R_exit; re-entry happens at the next check point, never at the
  exit's own check; buy-and-hold never re-enters; no entry at the last check; REACHED is measured after the in-rate
  exit costs (a path at V just below T is not reached); a moonshot path stops at REACHED while a compounding path
  continues and counts its first passage; cash never goes below 0 under 2x stress on adversarial fixtures (the carry
  is Task 10's); floor-safe paths never end below L; `g_se` is the SE of V_term + cost_term, not of V_term (a fixture
  whose cost varies with V shows the two differ); `run_column` raises ValueError for n not a multiple of CHUNK while
  `_run_paths` takes any n (n = 2,100 under `chunk()`); n checks per column; common random numbers: the same seed
  gives the same paths for every column and scenario; two ColumnStats compare equal through
  `dataclasses.replace(col, brackets=None)` and `==` never touches the arrays.
- Covers 8.o: 1 (mean payoff 0 for stop, bracket and buy-and-hold under every model), 4 (AT_FLOOR keeps L to L+X,
  re-entry at the next check, REACHED after the in-rate costs), 5 (always rule and floor-safe in the engine), 8
  (shared streams). RULINGS: O10 (CHUNK swap).
- Verify: `-m tests.odds_acceptance odds_simulate/` PASS within 18 s; guards; core-wide scans.

## Task 10: The path engine, part 2: locks, daily loss, rule dates, delisting and the OKX cap (spec 7.2 "Bands", "Band edges", "Limit-down locks", "Delisting stress", 7.3; O5, O11; Q5, Q26, Q29)
- `core/odds/simulate.py` part 2 (CONTRACT 8.3-8.4): the KRX band per session at each open check, band-edge
  sessions, the limit-down lock with `d_lock` (a queued exit fills only at a check strictly above the D of the
  session where it locked; new triggers use the current D), the flat 2x locked exit charge, LOCKED_AT_HORIZON, the
  daily-loss reference and stop, `stop_entries_from` and `force_exit_from`, the delisting columns, the OKX per-entry
  cap, `worst_gap`, `band_edge_share` and `band_edge_sessions`.
- `tests/odds_locks.py` (all under `OF.chunk()`): a limit-down lock persists across checks and sessions and fills at a
  flat 2x exit charge at the first check strictly above `d_lock`; after a close locked at D_s, a next open in
  (0.7 D_s, D_s] (above the new session's D) keeps the lock; LOCKED_AT_HORIZON values a still-locked position at the
  locked price less the carried charge; simulated KRX prices stay inside each session's band across sessions, and a
  session opening at an edge stays there and is counted in `band_edge_sessions`; cash never goes below 0 under 2x
  stress plus carry on adversarial fixtures; the daily loss stops trading until the next Asia/Seoul date, measured
  from the value carried into the day; an `auto_off` date and an `effective_until` date each force an exit at the
  first check on or after it (a non-session date moves to the next check) and no entry after it, tested separately
  (O5 "Test both"); from a `review_by` date no entry or re-entry happens while the position is kept and may close;
  the OKX per-entry cap holds; the delisting columns sell at p(1 - h) at the first check after the first entry, book
  the loss, and never re-enter; a stop fill below the stop records `worst_gap`.
- Covers 8.o: 1 (prices stay in the band across sessions, engine level), 4 (lock at flat 2x, LOCKED_AT_HORIZON,
  forced exit at a rule date), 5 (always rule under 2x stress plus carry). RULINGS: O5, O11 (OKX cap per entry).
- Verify: `-m tests.odds_acceptance odds_locks/` PASS within 12 s; guards; core-wide scans.

## Task 11: References: ceiling, structural maximum, bracket reference, brackets needed, bold_even (spec 3, 7.2, 7.4; Q32, Q33, Q44)
- `core/odds/bold.py` (CONTRACT 9): `ceiling`, `ceiling_one_in`, `structural_max`, `brackets_needed`, `bold_even`,
  `bracket_reference`.
- `tests/odds_bold.py`: `bold_even` gives exactly 0.1000%, 0.0816%, 0.0346%, 0.0106% at x = 1/1000 and 0.0400% at
  x = 1/1999, p = 0.49 (4 decimals of a percent), and f(x) = x at p = 1/2 for random dyadic and non-dyadic x; an
  even-money Bernoulli simulation of `costs.rule_units`' bold stake (20,000 paths, x = 1/8, p = 0.45) matches
  `bold_even` within its Clopper-Pearson interval; an engine run (`run_column`, crypto fixture `even_rows(0.5)`,
  venues `venues_with(upbit lot {default: 1e-12}, min_order {KRW: 0}, fee_extras 0/0)`, `costs.TABLE_BP
  ["crypto_venue"]` swapped to 0.0 with save/restore, daily loss limit 1e9, stake 42,000, floor 21,000, target 336,000,
  take_profit e^0.5 - 1, stop 1 - e^-0.5, bold, floor-safe, horizon 366 days, 20,000 paths) leaves no path running,
  and its Clopper-Pearson interval of P(T) contains the ceiling 1/15 (with the KRW 5,000 minimum P(T) sits near
  5.17%, below the ceiling, because a floor-protected loss never lands exactly on L: CONTRACT 16.1), and some path
  ends within KRW 1 of T; `ceiling_one_in` gives 1,000 and 1,999; `brackets_needed` gives 617 at (0.55, 0.50), 153 at
  (0.60, 0.50), the same 617 at (0.45, 0.50) and math.inf at p = p0; `structural_max` is 95.06 at 16 sessions of 0.30
  and 458.83 at 22, above 1,000 from 25, and below 1,000 for every n of the fixture calendar's 30-day horizons computed
  from `fixture_set()` sessions (16 <= n <= 22); `bracket_reference` is 0 for a target out of reach, 1 when the start
  is at the target, never above the fair-game ceiling on a martingale bracket law (within its grid error), and runs in
  under 3 s for 60 checks.
- Covers 8.o: 3 (bold_even values, simulated bold play matches), 4 (the structural cap from the fixture calendar, a
  path reaches T exactly in the even-money fixture; the IMPOSSIBLE card and the bracket KRX leg are Task 14's).
  RULINGS: none directly (spec 7.4; Q33's DP).
- Verify: `-m tests.odds_acceptance odds_bold/` PASS within 12 s; guards; core-wide scans.

## Task 12: The report: catalogue, statistics, number formats, flags, rendering, language guard (spec 7.5; O14; R2-4, R2-7; Q14, Q32, Q37, Q43, Q44, Q46)
- `core/odds/report.py` (CONTRACT 10): `ColumnStats` (from Task 9), `HiddenEdge`, `Flag`, `OddsReport`, `build`,
  `refusal_report`, `flags_for`, `render` (with its own `guard` pass), `CP_LEVEL`, `DELTA`, `RED_ALPHA`,
  `cp_two_sided`, `cp_lower`, `bernstein`, `hidden_edge`, `hidden_range`, `replay_range`, `ceiling_cells`, `fmt_krw`,
  `_sf2`, `fmt_prob`, `fmt_end`, `fmt_ceiling`, `fmt_blind`, `fmt_order`, `CATALOGUE` (every key of CONTRACT 10.4,
  exact text), `BANNED_WORDS`, `BANNED_PHRASES`, `say`, `guard`.
- `tests/odds_report.py`:
  - statistics: Clopper-Pearson at k = 0, n = 1e6 gives 2.9957e-06 and its sentence "under about 3 in 1,000,000";
    parity with `scipy.stats.binomtest(...).proportion_ci(method="exact")`; the empirical Bernstein bound equals the
    hand values of CONTRACT 16; on synthetic bounded X at delta_test = 0.05 with 2,000 replications the
    Clopper-Pearson upper bound of the alarm rate is <= 0.05; a planted edge of twice b_delta is flagged red with the
    gain wording, and a planted loss with the loss wording;
  - HIDDEN_EDGE range and wording: `hidden_range` uses CARRY x phi_sell' in its numerator (a hand value);
    k_x just under 1 gives a finite range and k_x = 1 gives inf, which renders `hidden.unbounded`, whose text holds
    "unavailable for this plan (no finite range)" (R2-7); GARCH-t renders
    "unavailable" and edge columns "does not apply"; the pass sentence prints the blind spot as "1 in floor((T -
    L_min)/b)" (b = 8,000.3 against T - L_min 41,979,000 prints 1 in 5,247, never 5,248) and says it does not test
    the model; b >= T - L_min renders `hidden.coarse`;
  - number formats: for every k in 1..1000 at n = 2e5 and n = 1e6 the interval printed by `fmt_end` contains the
    Clopper-Pearson interval, in both formats; k = 63 renders "about 1 in 16,000 (counting noise alone: between 1 in
    12,000 and 1 in 21,000"; spread ends are outward; `fmt_ceiling` prints "a 66.7% chance" at 0.6667, "a 33.4%
    chance" at 1/3 and "1 in 1,999" at 5.0025e-4; `fmt_order` keeps the printed order of a lower bound just above the
    ceiling ("1 in 1,998.5" against "1 in 1,999.0"); a no-edge point estimate above the ceiling with no breach prints
    `cap.p`; the bug-check clause is `bugs.finer` when b/(T - L_min) is below the headline interval's width and
    `bugs.coarser` otherwise;
  - flags and card: the CEILING_BREACH amber and red levels with m cells; the average line follows the 2 x g_se rule
    (agrees, differs, gain, loss); the typical result comes first among the numbers, and red flags come right after
    the plan head, before any number; the compounding headline wording; tax, ceiling (floor-protected and stop-based
    wordings), research estimate, the five base rates with their dates, the not-in-these-numbers box, the reworded
    limits line and the footer are present; a built report with IMPOSSIBLE set, and one with `trades == 0`, renders
    the structural sentence and no "1 in", "below about" or digit-percent on its headline, plain and ladder-target
    lines; a k = 0 spread member renders "below about 3 in n"; no probability slot renders as zero; the K note, the R
    note, the fresh-seed line and the moonshot caption are present;
  - guard: every catalogue template, filled with sample slots, and every rendered fixture report pass `guard` (no
    banned word, no hyphen part `safe`, no underscore except S_C3, no braces), with positive controls ("the best
    plan", "floor-safe sizing", "a good chance", "plan_hash"); a KRX fixture report's provenance (calendar md5s from
    files named `holidays_KRX`, `kr_sessions`, `kr_regime_tags`; members `bootstrap_half`, `garch_refit`; edge
    source `replay:S_C3_crypto_trend_krwbtc`) renders and passes `guard`; a slot value holding a banned word makes
    `render` raise ValueError;
  - refusals: a refused report renders no computed probability: no "1 in", no "below about", and no digit-percent
    except inside the fixed `sub.bracket` text and a typed rate's slot.
- Covers 8.o: 2 (bound tested at delta_test 0.05 with 2,000 replications, hand values at 1e-4, planted 2 b flagged,
  unavailable for GARCH-t, not applicable to edge columns), 9 (every report item). RULINGS: O14; R2-4 (the
  fresh-seed line says the rerun is not built), R2-7 (the unbounded wording).
- Verify: `-m tests.odds_acceptance odds_report/` PASS within 12 s; guards; core-wide scans (the catalogue is raw text
  under `core/`: no `CANO`, no forbidden words).

## Task 13: simulate(), part 1: the pipeline, the refusals and one headline column (spec 4 "How data flows", 6.3, 7.1, 9; O5, O6, O10, O11; R2-1, R2-5; Q5, Q6, Q24, Q42, Q45)
- `core/odds/simulate.py` part 3 (CONTRACT 8.5): `precheck` and `simulate` through step 7 with the headline no-edge
  column at base and 2x costs only (Task 14 adds every other column): the refusal order of Q24 (`check_now` before
  the calendar step, the calendar check through `owner.calendar_in_force`, `check_data`, `costs.terms`,
  `costs.check_validity` over the horizon dates, `check_history`, `cost_refusal`, `first_stake`, `gate.screen(plan,
  ctx, float(first))`), `gate.grey_rows`, the rule dates from `Screening.flags`, the OKX cap from `ctx.owner.caps`,
  `l_min` per sizing, and `report.build` with the provenance keys. Replay legs are refused CARD_NOT_REPRODUCED with
  detail "replay not built yet" until Task 17 replaces that branch and its test.
- `tests/odds_fixtures.py`: helpers for a pipeline run on a fixture context and fixture inputs, and
  `calendar_signed(sha)` (CONTRACT 3.2). KRX steps after the calendar step run under it; the CALENDAR_UNSIGNED and
  CALENDAR_COVERAGE tests use the real function (no key in the temp home), and Task 18 covers the signed calendar end
  to end.
- `tests/odds_pipeline.py` (under `OF.chunk()`): every refusal in Q24 order on one fixture each: PARTIAL_CHUNK at the
  real CHUNK, UNSUPPORTED_PRODUCT (sub `start` for a start other than `ctx.date`), MULTI_LEG_UNSUPPORTED,
  STATE_UNUSABLE (sub `code` for unsigned code), LIMITS_UNSET (and sub `cap` for an okx leg with the limits but no cap:
  a named refusal, never a crash), DATA_INVALID sub `now` for a naive `inputs.now` on a KRX leg (a refusal, not a
  ValueError from `calendar_in_force`), CALENDAR_UNSIGNED (a KRX leg under the fixture context, where no calendar is
  signed), CALENDAR_COVERAGE (calendar_error "coverage: ..."), DATA_INVALID (`stale`, `empty`), SYNTHETIC_REFUSED,
  NOT_TRADABLE (the shipped venues: no fee_extras; and a KRX stock leg whose 366-day horizon reaches 2027, refused by
  `check_validity` because a 2027 sell has no signed tax, R2-1; while a replay leg on venues with the upbit lot and
  minimum but no fee_extras is not NOT_TRADABLE and reaches the placeholder, R2-5), SPECIAL_REGIME, SHORT_HISTORY,
  CARD_NOT_REPRODUCED (the placeholder), MODEL_NOT_FOR_LIMITED_VENUE,
  COST_DOMINATED (4 kappa >= 1 and bold), STUCK_AT_START (a floor next to the stake), SCREEN_BLOCKED (a stale row,
  with `screen` never sent a zero stake); one KRX plan that breaks SYNTHETIC_REFUSED, NOT_TRADABLE and
  SPECIAL_REGIME at once reports SYNTHETIC_REFUSED, and with synthetic data fixed reports NOT_TRADABLE (O10's order);
  a refused report has no probability; the OKX leg is ACK_REQUIRED, simulated, and flagged GREY_LEG and PROXY_DATA;
  RULE_CHANGE_IN_HORIZON from a 60-day plan (review_by 2026-11-22/23 inside it); an OKX plan whose horizon crosses
  2026-12-03 is forced out at the first check on or after that date and its card prints `rule.end` with `rule.auto`
  (O5 end to end); plans in one comparison share streams (equal headline columns, compared through
  `dataclasses.replace(col, brackets=None)`, for two plans that differ only in name, and common paths across stake
  sizes); a plan with no `n_paths` runs `DEFAULT_PATHS` (2,000 under `chunk()`); purity (Q42: a crypto run under the
  open, socket and clock traps after a warm-up run gives the same report).
- Covers 8.o: 6 (UNSUPPORTED_PRODUCT, MULTI_LEG_UNSUPPORTED, LIMITS_UNSET, CALENDAR_UNSIGNED,
  MODEL_NOT_FOR_LIMITED_VENUE, SYNTHETIC_REFUSED, NOT_TRADABLE, STUCK_AT_START end to end in simulate), 8 (one
  comparison shares streams, renaming changes nothing, a partial chunk is refused). RULINGS: O5, O6 (CALENDAR_UNSIGNED,
  CALENDAR_COVERAGE), O10 (refusal order, CHUNK at the real value), O11 (float stake to screen, never zero; OKX cap);
  R2-1 (the 2027 KRX stock refusal end to end), R2-5 (replay terms in the pipeline).
- Verify: `-m tests.odds_acceptance odds_pipeline/` PASS within 20 s; guards, compliance guards and store; core-wide
  scans.

## Task 14: simulate(), part 2: the columns, the spread, the pilots and the flags (spec 7.2, 7.4, 7.5 items 8-10, 9; O10; R2-8; Q29, Q30, Q31, Q32, Q44)
- `core/odds/simulate.py` part 4 (CONTRACT 8.5): every other column: the bootstrap half and double members, the
  `garch_t` and `garch_refit` members (US and crypto legs; the GARCH fits, `pilot_checks` on the base fit and on each
  of the 20 refits; a non-converged fit or a failed check drops the member with its note; a failed headline is
  MODEL_CHECK_FAILED), each at base and 2x costs; the delisting 0.30 and 1.00 columns; the assumed column with the tilt
  bisection on the pilot through `_run_paths` (Q30; ASSUMED_EDGE_UNREACHABLE); the spread and its wording; the
  structural cap; `report.flags_for` with every flag; CEILING_BREACH over every no-edge cell; HIDDEN_EDGE on the
  headline with its range fixed from the plan and the history.
- `tests/odds_columns.py` (under `OF.chunk()` and `OF.pilots()` unless stated): the ceilings are never breached at the
  Bonferroni level on no-edge runs of several fixture plans; a stop-based plan's card prints "1 in 1,000" and the
  floor-protected one "1 in 1,999" (stake 42,000, target 42,000,000, floor 21,000), and CEILING_BREACH uses the
  matching ceiling (a planted count between the two ceilings raises amber only for the floor-protected card);
  HIDDEN_EDGE passes on no-edge bootstrap runs and is unavailable for a garch_t leg; a typed p above p0 does not raise
  HIDDEN_EDGE; the assumed column's win rate is within 0.01 of the typed p, and its card prints `assumed.nb` with
  `brackets_needed` (or `assumed.nbmany` when that exceeds the resolved brackets); the spread equals [min lower, max
  upper] of the non-headline base members, printed outward; the refit member uses 20 distinct fits; a corrupted
  correction table on a crypto bootstrap leg drops both GARCH members, sets the spread wording to `spread.blocks` and
  prints "GARCH-t was left out because its deterministic check failed"; the same corruption on a `garch_t` headline
  refuses MODEL_CHECK_FAILED with no number; under `calendar_signed`, a buy-and-hold KRX 1,000x card is IMPOSSIBLE and
  its headline, plain and ladder-target lines hold no "1 in", no "below about" and no digit-percent, while a bracket
  KRX leg is not IMPOSSIBLE; the delisting and assumed columns render with their cost words and ceiling lines;
  `test_tilt_pilot_runs_at_the_real_chunk` (the 20,000-path tilt pilot with the real CHUNK in force, no ValueError);
  `test_full_chunk_runs_at_the_real_size` (one 200,000-path chunk, 7-day crypto buy-and-hold).
- Covers 8.o: 2 (typed p > p0 does not raise HIDDEN_EDGE; pipeline integration), 3 (ceilings never breached at the
  Bonferroni level), 4 (IMPOSSIBLE with N from the fixture calendar, a bracket KRX leg not IMPOSSIBLE), 9 (the spread,
  the dropped member's note). RULINGS: O10 (pilots, CHUNK at the real value); R2-8 (every refit pilot-checked).
- Verify: `-m tests.odds_acceptance odds_columns/` PASS within 30 s; `--suite odds` exit 0; guards, compliance guards
  and store; core-wide scans.

## Task 15: Bars loading in the unsigned package (spec 4 "Bars", 7.2 "Price series", "Data rules"; O1, O6, O7, O13; Q6, Q7, Q13, Q35, Q36)
- `core/oddsdata/bars.py` (CONTRACT 11): the four seams, the constants and paths, the finality rules, `Part`,
  `part_md5`, `kis_part` (paged backwards, 100 rows a call, at most 60 pages), `upbit_part`, `binance_part`,
  `yahoo_part` (MultiIndex parsing), `load_leg` (KRX, Upbit, US x KRW=X, OKX composite with proxy dates), the cache
  (`read_cached`, `write_cached`, the env switch, `refetch`).
- `tests/odds_bars.py`: the probe test (each of the four seams raises `HermeticViolation` inside the odds wrapper, so an
  unpatched seam is refused); an AST test that the functions of `bars.py` importing `data.*` or `yfinance` are exactly
  `SEAMS`; fakes nested inside the wrapper's patch, restored afterwards: KIS paging stops at the window start and drops
  None, zero and negative rows; Upbit and Binance candles filtered to the window and to final bars (00:00Z of d + 1);
  a KRX bar dated today is dropped before 15:40 KST and kept after; a US bar before 16:10 ET is dropped; an FX bar is
  final only from 00:00Z of x + 2; US KRW prices use FX(d - 1) for the open and FX(d) for the close, with the Seoul
  close date d + 1 checked for EST and EDT days; the OKX composite uses KRW-USDT where it exists and KRW=X before it,
  recording `proxy_dates`; source labels, components and `series_md5` exact; a seam-body test installs a fake
  `sys.modules["yfinance"]` (save/restore) and calls `tests.odds_acceptance.REAL_SEAMS["_yf_download"]`, which calls
  `set_tz_cache_location` with the temp home's `odds/yfinance` before `download` (never a reload of `bars`); the cache
  round-trips, is keyed by window, refuses a file that disagrees with its manifest, is skipped under
  `TRADEGEN_ODDS_BARS_CACHE=0` and on `refetch`, and writes only through `checked_target`: the test calls
  `bars.cache_dir()` first (so `state_root()`'s link scan is memoised clean), then hard-links a cache file, then
  asserts the `checked_target` message "writing it would change another file"; the odds twin of the macro state-path
  test (TRADEGEN_HOME popped: `bars.cache_dir()` and `bars.odds_dir() / "yfinance"` resolve under `~/.tradegen`, and
  nothing is created); importing `core.oddsdata.bars` imports no data client, config or yfinance (a fresh-subprocess
  `sys.modules` check).
- Covers 8.o: 6 (SYNTHETIC_REFUSED is never produced by the loader; provisional last bars dropped). RULINGS: O1
  (unsigned loading), O6 (finality, US dating, FX), O7 (feeds per venue), O13 (seams, cache, yfinance tz cache).
- Verify: `-m tests.odds_acceptance odds_bars/` PASS; odds guards (writes, clock, imports) PASS; core-wide scans.

## Task 16: Calendar, sessions, provenance and the persisted odds state (spec 4 "Calendars", "Provenance", 7.3 "Seeds"; O1, O6, O12; R2-6; Q6, Q12, Q22, Q34, Q36)
- `core/oddsdata/inputs.py` (CONTRACT 12): `calendar_for`, `sessions`, `REPO`, `UNVERSIONED`, `TREE_GLOBS`,
  `repo_anchor`, `tree_hash` (the R2-6 copies), `provenance`, `STATE_SCHEMA`, `CID_RE`, `state_path`, `begin_run`,
  `build_inputs`. It imports neither `core.quant.gate_ledger` nor `core.ficc.macro_artifacts`.
- `tests/odds_inputs.py`: the three CALENDAR cases (the shipped drafts, never approved: `calendar_for` gives None and
  "unsigned"; `fixture_set()` signed by TEST-FIXTURE but with no owner approval: None; `fixture_set()` approved in a
  full temp home: a CalendarSet over the store and its sha, equal to `owner.calendar_in_force(F.NOW)`); a store copy
  altered after approval is refused; KRX sessions of a 30-day horizon from 2026-10-24 on the approved fixture set with
  price limits 0.30 and the three md5s; US sessions with Seoul close dates d + 1; crypto every date; a horizon past
  2027-12-31 gives "coverage: ..."; `core.calendars.store.default`, `core.calendars.clocks.default` and
  `core.calendars.regime.default` all patched to raise (each saved and restored) are never called; `provenance()`
  returns `git:<40 hex>` or UNVERSIONED, a 64-hex tree hash and the cryptography version; the R2-6 equality tests
  (the test imports the originals; the module under test never does): `inputs.repo_anchor()` equals
  `gate_ledger.repo_anchor()` and `inputs.tree_hash()` equals `macro_artifacts.tree_hash()` on the repo, both equal
  the originals on synthetic temp roots (no `.git`, a `ref:` HEAD, a detached sha, a non-hex HEAD; a small core,
  data/macro and config.py tree), and `UNVERSIONED` and `TREE_GLOBS` equal the originals' (CONTRACT 16.2); `begin_run` numbers new
  comparisons `c000001`, `c000002`, increments `runs` on every call, keeps each comparison's own `run` when the same id
  is passed again (so two invocations with one id return the same run counter and give the same market seed),
  accumulates K and J under that id, refuses an id it never issued and a malformed id with ValueError, returns R per
  plan hash (a plan in two comparisons has R = 2), fails closed on an unparseable state file or a comparison without
  "run", and writes atomically through `checked_target`; `build_inputs` fills every field (`plan_runs` included); the
  odds twin of the macro state-path test (TRADEGEN_HOME popped: `inputs.state_path()` resolves under `~/.tradegen`,
  nothing created).
- Covers 8.o: 6 (CALENDAR_UNSIGNED: unsigned files, or files lacking a signed owner approval), 8 (a new comparison gives
  a fresh seed; a comparison id groups plans and keeps their shared seed). RULINGS: O1 (passed-in calendar data and
  provenance), O6, O12; R2-6 (the provenance helpers copied, with equality tests).
- Verify: `-m tests.odds_acceptance odds_inputs/` PASS; guards; core-wide scans.

## Task 17: The D13 replay, Kelly and the replay card (spec 7.1 "kelly", 7.2 "replay", 7.5 item 9; D13; O9; R2-5; Q9, Q32, Q38)
- `core/oddsdata/replay.py` (CONTRACT 13): `replay_s_c3`.
- `core/odds/models.py` part 3 (CONTRACT 7.5): `CARD_ID`, `REPLAY_PINS` (the card stats and the turnover md5
  included), `verify_replay` (with the core's own bench_sr recompute), `KELLY_*`, `mu_lb`, `kelly_fstar`,
  `replay_returns` (a, c, R1), `block_growth`.
- `core/odds/simulate.py` part 5: the replay engine in `_run_paths` (the fair-sign no-edge move with the
  `replay_sign` stream, c booked; the tested move R1; the floor-protected sleeve through `costs.rule_units` with
  the zero-charge terms of `costs.terms(..., replay=True)` and `mult = 0.0`), and the replay branch of `simulate` (`replay_no_edge/base`,
  `replay_no_edge/stress2x`, `tested_replay/base`; HIDDEN_EDGE with `replay_range` on the base cell; CEILING_BREACH
  with m = 2; CARD_NOT_REPRODUCED), replacing Task 13's placeholder refusal and its test.
- `core/odds/report.py`: the replay card lines (`replay.lead`, `replay.growth`, `replay.noedge`, `kelly.label`,
  `model.replay`, `ceiling.edge` under the tested column).
- `tests/odds_replay.py`: the replay is deterministic on the committed cache (two runs give the same ReplayInput) and
  `verify_replay` accepts it (every pin of CONTRACT 7.5 and 16); lookbacks 28 -> 30 is refused (stats and digest);
  embargo 1 -> 0 is refused by the exact-input pin although its Sharpe 1.2172 is inside the tolerance; each digest,
  protocol value and statistic (bench_sr, bench_diff, bench_ci, haircut_sr, n_trades, n_sessions, the turnover md5
  included) edited in a copy of the ReplayInput is refused naming that item; the core's bench_sr recompute equals the
  pin exactly; the study runner is never imported (an AST scan of `core/odds` and `core/oddsdata`, and
  `docs.asset_expansion_study` and `asset_expansion_study` absent from `sys.modules` after a replay); Kelly is 0 when
  mu_lb <= 0 (a demeaned series) and f* stays within [0, 1] on random series, including one with a return below -1
  after the shift; on the real replay f* is 1 (the upper boundary, decided by the derivative sign); `block_growth`
  matches a 200,000-path Monte Carlo of the same generator within 4 SE and gives 1.029918 on R1 at h 30; the
  no-edge replay column is a martingale: X = G_tau - W0 has mean 0 within 4 SE under fixed(1.0) buy-and-hold and
  under a daily-loss limit tight enough to fire on a tenth of the days; negative control: a test-only numpy
  reference of the earlier construction (the demeaned gross g resampled in blocks of mean 10, 100,000 paths, 30
  days, exit after a day below -3% and re-enter the next day) has a mean gross value above 1 by more than 4 SE on the
  real series; the sleeve never exceeds cash - L at entry; the card's text renders 0.79, 0.73, +0.43, +0.03 to +0.83,
  "40%", the growth line "3.0%" against "2.7%" at 30 days, and the ceiling line under the tested column; a replay leg
  runs on venues whose upbit entry has `lot` and `min_order` but no `fee_extras` (R2-5), while a buy-and-hold upbit
  leg on the same venues is NOT_TRADABLE, and a replay leg on venues without the upbit lot is NOT_TRADABLE. Budget:
  three replays at about 5 s each.
- Covers 8.o: 1 (the replay's no-edge column is a martingale; the demeaned block trap fails), 2 (HIDDEN_EDGE on the
  replay no-edge column), 6 (CARD_NOT_REPRODUCED), 7 (deterministic on the fixture closes, pinned constants
  reproduce, a changed constant refused, never imports the study runner, Kelly 0 when mu_lb <= 0, f* within [0, 1]).
  RULINGS: O9; R2-5 (the replay leg needs only the lot and minimum).
- Verify: `-m tests.odds_acceptance odds_replay/` PASS within 20 s; guards (oddsdata imports); core-wide scans.

## Task 18: The CLI and the end-to-end runs (spec 4, 7.5 "Comparing plans"; O15; R2-6; Q12, Q15, Q45)
- `core/oddsdata/run.py` (CONTRACT 14): `main(argv=None, *, now=None)`, `load_plans`, the exact `__main__` block.
- `tests/odds_cli.py`, in full temp homes (`F.full_home(home, venues_raw=OF.ODDS_VENUES, limits=..., cap=0.10)`, now =
  `F.NOW`, every plan file with start `"2026-10-24"`, every run with `--paths 2000` under `OF.chunk()` and
  `OF.pilots()`, the seams faked): a crypto plan file with two plans prints two reports, typical result first, the K
  note "You compared 2 plans", exit 0; rerunning that file with `--comparison` set to the issued id prints identical
  numbers (one seed per comparison), while a fresh run gives a new comparison and the R note "run in 2 comparisons";
  an unknown `--comparison` id exits 2 with UNSUPPORTED_PRODUCT and writes no state; a KRX plan exits 2 with the
  CALENDAR_UNSIGNED sentence without a calendar approval and exits 0 once `calendar_raw` approves `fixture_set()`; a bad
  JSON file, an unknown key and a `legs` list of two each exit 2 with UNSUPPORTED_PRODUCT or MULTI_LEG_UNSUPPORTED; an
  injected exception exits 4 with "crash:" on stderr; a language-guard hit planted in the catalogue (save/restore)
  exits 4; argparse errors exit 4; `--paths 1000` exits 2 with PARTIAL_CHUNK (real CHUNK); the precheck refuses
  STATE_UNUSABLE in a home with no owner key before any seam is called and before `state.json` is written; the CLI
  never writes `owner.jsonl` (its bytes are unchanged);
  `runpy.run_module("core.oddsdata.run", run_name="__main__")` with `--help` exits through SystemExit; stdout is UTF-8.
  No run-time `sys.modules` check of `core.engine` (dropped by R2-6: `core/oddsdata` imports neither provenance
  module; Task 1's static guards, no `core.engine` import in any form and no `gate_ledger` or `macro_artifacts`
  import in `core/oddsdata`, stay).
- Covers 8.o: 6 (refusals end to end, CALENDAR_UNSIGNED through load_context), 8 (one comparison, one seed; a new
  comparison, a fresh seed), 9 (K and R notes, caption, rendered order). RULINGS: O15, O12 (state written by the
  unsigned side), O13; R2-6 (the run-time `core.engine` check dropped).
- Verify: `-m tests.odds_acceptance odds_cli/` PASS within 20 s; `--suite odds` exit 0 within about 3.3 minutes;
  `--suite compliance` exit 0; guards; core-wide scans.

## Task 19 (written by the coordinator): full run, records and the hand-off to execution (E1, E2, E3)
- Check no PENDING NOT_RUN is left in the odds suite; run the full suite with the overlap guard; expected tail
  `<old passed + compliance delta + O>/<old total + compliance delta + T> passed, 0 failed, <old not run> not run`.
- `README.md` (CRLF, Edit tool): update the compliance row's count (Tasks 2-4 added tests), insert the `odds` row after
  it, and replace the Total line; keep the anchors `macro_ui_components` checks. The follow-up already changed the
  compliance row and the Total line, so quote them from the merged file (DRIFT RULE, R2-13).
- Commit `README.md` and `qa/acceptance_results.json` from the full run only; then commit the execution ledger (the
  merged line numbers, every drift ruling, the R2-9 margins, the runs) as its own docs commit.
- Real-home smoke without network: with no owner key, `python -m core.oddsdata.run --plan <a temp crypto plan>`
  exits 2 with STATE_UNUSABLE, calls no seam and writes nothing under `~/.tradegen` (Q45); show the owner the output
  and say plainly that every odds run stays refused until owner acts 1 to 6, and that every leg is NOT_TRADABLE until
  the venues file carries signed fixed charges and lots (the replay leg needs only the Upbit lot, R2-5).
- Hand-off notes for execution, built as E1, E2, E3 in that order (E1 spec section 1):
  - E1 (account inquiry, the design that follows): the interfaces it inherits (`load_context`, `screen`, `grey_rows`,
    `calendar_in_force`, `OddsReport`, the refusal codes); live balances replace `Positions(equity_krw=stake)`.
  - E2 (execution core, which arms): never a zero stake to `screen`; the OKX cap applied per entry; the daily-loss and
    floor halts; the rerun on a fresh market seed before arming, which `compare.fresh` says this plan does not build
    (R2-4).
  - E3 (live order adapters): band edges come from the venue's own quoted limit prices and are never computed; the
    odds band (per-edge rule, 1,404 at ETF reference 2,005) and `orders.limit_prices` (one tick for both edges, 1,405)
    differ by one tick there, and this plan changes neither (Q41, R2-2).
  - No open issue of this plan's own is left: R2-1 settled the KRX stock tax inside the floor (it now equals
    `instruments.cost_per_side`) and R2-2 the band edge.
  - The owner acts: sign the code hash, approve the venues file with fixed charges and lots (0 allowed), approve the
    calendar set, set the limits and cap.
- Fold this plan's departures (the header's "For spec rev 3.3" list: Q1, Q6, Q17 to Q46, accepted by R2-3) into spec
  rev 3.3 at GPT's checkpoint after 2026-10-30 14:40.
- Covers: every 8.o item in the full run; RULINGS O1-O15 and RULINGS_ROUND2 R2-1 to R2-9 and R2-13 recorded.

## Coverage

| Spec 8 odds item | Tasks |
|---|---|
| 1 Martingale law (1e-12, bands, 100 -> 70 -> 100, mean payoff 0 for stop, bracket, buy-and-hold under every model, drift="zero" and per-row demeaning fail, GARCH pilot pass and corruption fail; the replay's no-edge column a martingale) | 6, 7, 8, 9, 10, 17 |
| 2 HIDDEN_EDGE (delta_test 0.05 with 2,000 replications, hand values, planted 2 b, unavailable GARCH-t, not applicable to edge columns, typed p > p0) | 12, 14, 17 |
| 3 Exact values (bold_even, simulated bold play, ceilings never breached at the Bonferroni level) | 11, 14 |
| 4 Mechanics (IMPOSSIBLE with N from the fixture calendar, bracket KRX not IMPOSSIBLE, lock at flat 2x, LOCKED_AT_HORIZON, AT_FLOOR L to L+X, bold rounds up and reaches T exactly, re-entry at the next check, forced exit at a rule date, REACHED after in-rate costs) | 6, 9, 10, 11, 14 |
| 5 Ledger (always >= 0 under 2x stress plus carry, floor-safe >= L, bold refused at net coefficient <= 0, 2,005-KRW tick floor >= 13.8 bp, no separate sell tax; the KRX stock sell tax only inside the floor, as the repo's cost function, R2-1) | 2, 6, 9, 10 |
| 6 Refusals (UNSUPPORTED_PRODUCT, MULTI_LEG_UNSUPPORTED, LIMITS_UNSET, CALENDAR_UNSIGNED, MODEL_NOT_FOR_LIMITED_VENUE, SYNTHETIC_REFUSED, NOT_TRADABLE, STUCK_AT_START, CARD_NOT_REPRODUCED) | 3, 4, 5, 13, 15, 16, 17, 18 |
| 7 D13 replay (deterministic, pinned constants reproduce, changed constant refused, no study runner, Kelly 0 at mu_lb <= 0, f* in [0, 1]) | 17 |
| 8 Seeds (one comparison shares streams, renaming changes nothing, partial chunk refused) | 5, 7, 9, 13, 16, 18 |
| 9 Report (typical first, average rule, compounding wording, tax, base rates with dates, footer, not-in box, structural zeros, k = 0 spread member, no banned word, K note and caption) | 12, 14, 17, 18 |
| Existing guards stay in force (test_08, test_09, T-RO-01, T-CTX-01) | 1, every core task (core-wide scans), 19 |

| Spec 9 and 10 row | Tasks |
|---|---|
| 9 Odds refuses with named reasons and never prints a probability from a refused run | 5, 12, 13, 18 |
| 9 A model that fails a pilot check is left out of the spread, with the check named (a failed headline is MODEL_CHECK_FAILED) | 8, 14 |
| 10 No-edge martingale | 7, 9, 17 |
| 10 HIDDEN_EDGE (red wordings, "how large an error it could miss", unavailable for GARCH-t and, R2-7, for a plan with no finite range) | 12, 14, 17 |
| 10 Ceiling ("No plan without a real edge that keeps this floor can beat 1 in N") and CEILING_BREACH | 11, 12, 14 |
| 10 IMPOSSIBLE ("at most N× in these S sessions", no probability) | 11, 12, 14 |
| 10 Typical result first; at your floor (L to L+X) | 9, 12 |
| 10 Precision and model spread (KRX: block-length variants only) | 12, 14 |
| 10 Open/close checks | 9, 12 |
| 10 Floor-protected sizing ("your floor holds even if this position goes to zero") | 6, 9, 12 |
| 10 2x costs and the tick floor (a second column; never below the repo's floor) | 6, 13, 14, 17 |
| 10 Minimum tickets ("Can't open", STUCK_AT_START, or AT_FLOOR) | 6, 9, 13 |
| 10 LIMIT_GAP / LOCKED_AT_HORIZON / BAND_EDGE_SESSIONS (the worst overshoot, still locked, capped-session count) | 10, 12 |
| 10 Typed win rate (about N recorded brackets; never in the headline) | 11, 14 |
| 10 Tested-strategy replay | 17 |
| 10 Winner's curse (K plans; R seeds; the fresh-seed confirmation handed to E2, R2-4) | 12, 16, 18, 19 |
| 10 Stale rules and the OKX cap, acknowledgement and auto-off | 4, 10, 13 |
| 10 Signed state and code (D14; unsigned code refused in the precheck) | 1, 5, 13 |
| 10 Language guard (the build fails; `render` refuses its own banned output) | 12, 18 |

| RULINGS item | Tasks |
|---|---|
| Order of the plans (DQ26) | 1 (precondition), 19 |
| O1 Layout: everything injected | 1, 5, 6, 7, 8, 15, 16, 17 |
| O2 Odds-own guards | 1 |
| O3 Compliance-side prerequisites | 2, 3, 4 |
| O4 Plan types | 5 |
| O5 review_by and rule dates | 10, 13 |
| O6 Calendar | 4, 13, 15, 16 |
| O7 Venues and feeds | 5, 15 |
| O8 SPECIAL_REGIME | 5, 13 |
| O9 The D13 replay | 17 |
| O10 Models, statistics, simulator | 6, 7, 8, 9, 13, 14 |
| O11 Stakes, equity, costs | 2, 3, 6, 10, 13 |
| O12 Seeds and persisted odds state | 7, 16, 18 |
| O13 Cache, seams, harness | 1, 5, 15, 18 |
| O14 Report | 12, 17 |
| O15 CLI | 18, 19 |

| RULINGS_ROUND2 item | Tasks |
|---|---|
| R2-1 KRX stock sell tax inside the floor, equal to `instruments.cost_per_side` (O11 amended); a sell year missing from `SELL_TAX_BP` is NOT_TRADABLE | 6, 13 |
| R2-2 Band lower edge 1,404 at ETF ref 2,005; `orders.limit_prices` unchanged; E3 takes venue-quoted edges | 6, 19 |
| R2-3 Spec departures (Q46) accepted, listed under "For spec rev 3.3" | plan header, 19 |
| R2-4 Fresh-seed rerun not built; `compare.fresh` says so; handed to E2 | 12, 19 |
| R2-5 A replay leg needs only `lot` and `min_order`; other legs still need `fee_extras` | 3, 6, 13, 17 |
| R2-6 `repo_anchor` and `tree_hash` copied into `inputs.py`; oddsdata imports neither module; no run-time `sys.modules` check | 1, 16, 18 |
| R2-7 HIDDEN_EDGE with no finite range prints "unavailable for this plan (no finite range)" | 12 |
| R2-8 STALE_DAYS 3 / 14 and the per-refit pilot checks accepted | 5, 14 |
| R2-9 GARCH corruption margins confirmed on the real "pilot" stream; factors only raised | 8 |
| R2-10 `pstats` and `tracemalloc` in DYNAMIC_MODULES bind `core/odds` through the merged lists | 1 |
| R2-11 The follow-up branches from main's HEAD; this plan branches after it merges | 1 (precondition) |
| R2-13 DRIFT RULE: anchored old/new Edits, re-read, same change on drift, one ledger line each | 1 (ledger, drift list), 2, 3, 4, 19 (every Edit of an existing file; the ledger commit) |
