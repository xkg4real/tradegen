# TRADEGEN odds engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the odds half of the approved spec. It covers:
- the plan types and their whitelist (single-leg, cash, 1x, long-only: KRX shares and 1x ETFs, US shares and 1x ETFs,
  crypto spot on KIS, Upbit and OKX);
- the cost ledger with the per-fill tick floor, floor-protected and stop-based affordability, and the fixed, Kelly and
  bold stakes;
- the no-edge two-point bootstrap and GARCH-t models, the assumed-edge tilt, and the exact replay of the validated
  S_C3 strategy (D13);
- the vectorised, chunked simulator with limit-down locks, daily-loss stops, rule dates and the outcome ladder (D4);
- the analytic references (the ceiling, the KRX structural maximum, bold play), the bug checks (HIDDEN_EDGE,
  CEILING_BREACH) and the honest-language report;
- the unsigned loaders, the calendar and session inputs, the persisted comparison state and the CLI.

No order is placed and no money moves. The engine prints the chance of each outcome; it never recommends a plan.

**Real odds, stated first.** With no real edge, the gross value (cash plus holdings at the price, before exit charges)
is a supermartingale that never falls below L_min, and the liquidation value is never above it; so no plan without a
real edge that keeps this floor can beat (W0 - L_min)/(T - L_min). L_min is the floor L under floor-protected sizing
and 0 under stop-based sizing, where a gap can pass the stop. For KRW 42,000 -> KRW 42,000,000 that is 1 in 1,000 with
no protected floor, and 1 in 1,999 with the floor at half the stake (the spec rounds it to 1 in 2,000). The ceiling is
a bound, not a forecast: the research's own estimate is 0.01% (1 in 10,000) or less in general and below 0.01% for
domestic crypto spot, and a buy-and-hold KRX plan cannot reach 1,000x in a month at all (the daily band caps 30 days
at about 95x to 459x). The typical (median) moonshot month ends at the floor. Every card prints its ceiling in
exactly these words: "No plan without a real edge that keeps this floor can beat 1 in N." (a percentage when the
bound is 1% or more, and without "that keeps this floor" under stop-based sizing).

**Architecture:** "Everything injected" (O1, owner ruling 2026-10-24). The signed core `core/odds/` (plan, costs,
models, simulate, bold, report, plus `venues.yaml` as data) imports only the standard library, numpy, scipy,
`core.isolation`, `core.compliance.*` and `core.odds.*`, so its D14 code closure stays small and reviewable. Whatever
it needs from the rest of the repo is either copied into it with an equality test against the original (the GARCH-t
fit and simulation, the correction table, the block length, the cost table and tick floor with the KRX stock sell tax
inside it, the live multiplier, the delisting stress, the carry multiplier) or computed by the unsigned sibling
`core/oddsdata/` (bars, sessions, price
limits, calendar hashes, the S_C3 replay, provenance strings, the comparison state, the CLI) and passed in as plain
data with its hash, which the core recomputes and checks. The core gets its `Context` only from
`owner.load_context`, screens every plan with `gate.screen` before simulating, and refuses with a named reason
whatever it cannot price honestly.

**Tech Stack:**
- Python 3.13.14 in `.venv`; numpy 2.3.5 and scipy 1.18.0 (already pinned; outside the signed hash, stated on every
  card); yfinance 1.4.1 in the unsigned loader only;
- the compliance package (`core/compliance`) as built, plus three helpers added here (`owner.calendar_in_force`,
  `gate.grey_rows`, the venue odds keys of `rules.py`);
- the stdlib `fractions` (exact bold play), `zoneinfo` with `tzdata` 2026.2;
- the repo's own runner `tests/run_all.py`. There is no pytest.

**Spec:** `docs/superpowers/specs/2026-10-23-compliance-gate-and-odds-engine-design.md` (rev 3.2). The owner's rulings
of 2026-10-24 (O1 to O15) override it where they say so, as amended by the controller's round-2 rulings (R2-1 to R2-9
and R2-13 for this plan), which win where they disagree. Every departure is a plan decision below, is listed under
"For spec rev 3.3" (R2-3), and is folded into rev 3.3 at GPT's checkpoint after 2026-10-30 14:40. This plan does not
wait for that check: a valid finding that touches built code becomes a new task with its own failing test.

> This is research and software design, not legal or investment advice; TRADEGEN and its author are not licensed
> advisors. The odds it prints describe rules the owner wrote, run in a model; a higher chance of reaching the target
> does not make a plan better.

## For spec rev 3.3

The controller accepted these departures from rev 3.2 as plan decisions (R2-3). Each one makes a check stricter or
makes a printed claim true where the spec's fixed text could be false. They are listed here so the owner and GPT's
check after 2026-10-30 14:40 see them; Task 19 folds them into rev 3.3.
- 4 "Layout": `bars.py` moves to the unsigned sibling `core/oddsdata/`. The signed core copies what it runs from the
  repo, each copy with an equality test, and takes the rest as passed-in data whose hashes it recomputes where it
  can. `repo_anchor` and `tree_hash` come from copies in `core/oddsdata/inputs.py`, with equality tests (Q1, O1, R2-6).
- 4 "Calendars", 6.3: a horizon past the signed calendar's end is refused CALENDAR_COVERAGE (Q6).
- 7.2 and 9, refusals: new codes PARTIAL_CHUNK, STATE_UNUSABLE (with sub `code` for unsigned code), CALENDAR_COVERAGE,
  DATA_INVALID (subs `now`, `series`, `sessions`, `empty`, `stale`; STALE_DAYS 3 for crypto, 14 for KRX and US),
  SHORT_HISTORY, COST_DOMINATED, SCREEN_BLOCKED, ASSUMED_EDGE_UNREACHABLE and MODEL_CHECK_FAILED; and prechecks for the
  start date and the OKX cap (Q24, Q39, Q46 item 8; STALE_DAYS accepted by R2-8).
- 7.5 HIDDEN_EDGE: the resolution prints "1 in floor((T - L_min)/b)", never the spec's ceil, and the pass sentence
  says the check detects simulator drift only, not model error (Q46 item 1). A bootstrap leg whose range, fixed before
  the run, is not finite prints "unavailable for this plan (no finite range)" (Q46 item 9, R2-7).
- 7.5 plain sentence: "the bug checks are coarser than these ranges" prints only when it is true (Q46 item 2).
- 7.5 ceiling: printed as a percentage from 1%, and without "that keeps this floor" under stop-based sizing (Q46
  item 3).
- 7.5 replay card: its no-edge columns are a fair-sign two-point kernel on the replay's own block-resampled moves, with
  a 2x-cost column, CEILING_BREACH and HIDDEN_EDGE (Q46 item 4).
- 7.5 render order: red flags come right after the plan head, before any number (Q46 item 5).
- 7.5 "Before arming, the plan is re-run on a fresh market seed": not built here; `compare.fresh` says so, and the
  hand-off gives it to E2 (Q46 item 6, R2-4).
- 9 spread members: `garch_refit` pilot-checks each of its 20 refits and is dropped if any fails (Q31, R2-8).
- O3's wording, not the spec: `calendar_in_force` and `_calendar_line` share `_calendar_approval` (Q19).
Two changes are not departures. The KRX stock sell floor now follows spec 4 "Costs" literally: the tax sits inside
`cost_per_side`'s floor (R2-1). A replay leg needs only the signed lot and minimum, as spec 7.2 says (R2-5, so Q46
item 7 is withdrawn).

## Global Constraints

Every task's requirements include this section. Values are copied from the spec, the rulings and the verified repo
map.

**Hard rules from the owner's brief**
- Never arm the system, place a live order, or enter credentials or keys.
- Never edit anything under `C:\Users\whydi\OneDrive\Desktop\QUANTGEN`. Never write under `~/.nextgen`. Never run
  anything while QUANTGEN's test suite runs.
- Never delete `grokteam/PREREG_book.json` or `grokteam/out/frozen_book/`.
- No odds test and no task step calls a network function for real: every data seam is faked inside the test.
- Real odds only: no output presents a probability for a refused run, and no probability renders as zero.

**Signing and the owner log**
- Claude never runs `tools/signer/sign.py` with a real key, never asks for or handles the owner's passphrase, and never
  writes to the real `~/.tradegen/compliance/owner.jsonl`.
- Tests build owner logs only inside a temporary `TRADEGEN_HOME`, signed with the fixed test key.
- No owner key and no signature exist yet (owner act 1 is not done), so no task costs a re-sign today. Once the owner
  signs `code_approved`, any later change to the signed closure needs a fresh signature before new exposure is
  allowed again. numpy and scipy are outside the hash: an upgrade changes behaviour without a re-sign.

**Python and test runs**
- Interpreter: `.venv/Scripts/python.exe` (Python 3.13.14). Never `pip install` anything; this plan adds no dependency.
- A test is a zero-argument `test_*` function that raises on failure. There is no pytest.
- Overlap check: run it before every test command. It must print nothing; otherwise wait. QUANTGEN's Store Python
  runs as `python3.13.exe` with no `python.exe` beside it, so only a `python*` name filter sees it. Never run two
  suites at once (the odds Monte Carlo is CPU-heavy).
  - PowerShell tool:
    `Get-CimInstance Win32_Process -Filter "Name LIKE 'python%'" | Where-Object { $_.CommandLine -match 'run_all' } | Select-Object ProcessId,Name,CommandLine`
  - Git Bash prefix. The PowerShell script is in single quotes, so Bash leaves `$_` alone:
    `test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && <command>`
- One test or module: `.venv/Scripts/python.exe -m tests.odds_acceptance <module>/<test>`. This does not write
  `qa/acceptance_results.json`.
- One suite: `.venv/Scripts/python.exe tests/run_all.py --suite odds` (or `compliance`, `cockpit`). This rewrites the
  tracked `qa/acceptance_results.json`. Restore it with `git checkout -- qa/acceptance_results.json` afterwards. Only
  Task 19 commits that file.
- After every task that touches `core/compliance`, `core/odds` or `tests/compliance_*`: also
  `-m tests.compliance_acceptance compliance_guards/` and `compliance_store/`.
- After every task that changes `core/`: the core-wide scans `-m tests.macro_m0_harness`, `-m tests.macro_tf_gov`,
  `-m tests.macro_m7_ledger`, `-m tests.macro_m8_forward`, `-m tests.macro_m6_context` and `--suite cockpit`.

**Files, line endings and commits**
- New files are UTF-8 with no BOM and LF endings.
- These files are CRLF and must stay CRLF: `tests/run_all.py`, `README.md`, `config.py`, `requirements.txt`,
  `pyproject.toml`, `core/quant/history.py`, `grokteam/book.py`, `grokteam/selfcheck.py`, `qa/acceptance_results.json`
  and the `docs/asset_expansion/cache/*.csv` files. `constraints.txt` is mixed and is not edited by this plan.
- Edit every existing file only with the Edit tool, never `sed -i`. No `tests/macro_*.py` file is edited.
- Line numbers cited into existing files are as of main 995534b; the follow-up plan moves some of them, so each task
  finds its anchor by name and Task 1 records the merged line numbers in the execution ledger.
- Before every commit, `git diff --cached --stat` must equal `git diff --cached --stat --ignore-cr-at-eol`.
- Work on branch `odds-engine`, which Task 1 creates from main's HEAD after the compliance follow-up has merged.
  Commit once per task. End each commit message with the `Co-Authored-By:` line of the model that wrote the commit;
  this controller's is `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Execution ledger: `docs/superpowers/plans/2026-10-24-odds-engine-execution-ledger.md` (LF). Task 1 starts it; it
  holds the merged line numbers, every drift ruling, the R2-9 margins and the runs. It stays untracked until Task 19
  commits it, so a `git status --short` check allows exactly that one `??` line.

**Drift rule (R2-13).** This plan is written against main `5816d3c`, which equals `995534b` outside docs/. It runs
second, after the compliance follow-up merges. The follow-up changes `core/compliance/rules.py`, `owner.py`,
`alerts.py`, `kr_rules.yaml`, `tests/compliance_guards.py`, `tests/compliance_tables.py`, `tests/compliance_store.py`,
`tests/compliance_signer.py`, `tests/compliance_cli.py`, `tests/compliance_isolation.py`, `tools/signer/sign.py`,
`data/krx/kis_client.py`, `core/ficc/data.py` and `README.md`. Of these, this plan edits `rules.py`, `owner.py`,
`tests/compliance_tables.py`, `tests/compliance_store.py`, `README.md` and, only for an import fix,
`tests/compliance_cli.py`.
- Every Edit of an existing file quotes its old text exactly from `5816d3c` and names its anchor: the function,
  constant, test, YAML row or table row it sits in. A cited line number only helps find the anchor.
- Re-read the file before each Edit. If the quoted old text differs only because an earlier plan changed it, apply
  the same change to the current text, keep the earlier behaviour, and record a one-line ruling in the execution
  ledger. If the change no longer makes sense, stop and rule.
- The same holds for the `tests.compliance_guards` and `tests.compliance_fixtures` names this plan reuses. The
  follow-up renames none of them.
- Task 1 records `git diff --stat 5816d3c HEAD -- . ':!docs'` in the ledger, so the files where drift can occur are
  known before any Edit.

**Guards on `core/**/*.py`.** They scan raw text, so docstrings, comments and the sentence catalogue count.
- Never write upper-case `CANO` (so never `CANONICAL`), `KIS_ACCOUNT` or `ACNT_PRDT_CD`.
- Never write `order_cash`, `order-cash`, `place_order`, `submit_order`, `TTTC0802U`, `TTTC0801U`, `VTTC0802U`,
  `r18_research_log`, `r18_break_log`, `context_log/`, `tests.reference`, `reference_mode` or `reference_only=True`.
- Never write `private_key` or `seed_phrase` in any form. Name random streams "seed" or "stream".
- Never write an order, withdraw or deposit endpoint path (`/v1/orders`, `/api/v3/order`, `/sapi/v1/capital/...`) or
  a `/uapi/.../trading/` path.
- Never call, and never define, a function named `transfer`, `withdraw`, `deposit_address` or any other T-RO-01
  forbidden call name.
- Never import `core.engine.orders` in any form (in `core/oddsdata`, no `core.engine` module at all),
  `core.quant.forward_sim`, `core.quant.refusal`, `core.ficc.context_log`, `core.ficc.macro`, `core.ficc.flows_log`,
  `core.skills.macro_daily`, `docs.asset_expansion_study` or an order-client package. `core/oddsdata` also never
  imports `core.quant.gate_ledger` or `core.ficc.macro_artifacts`: their `repo_anchor` and `tree_hash` are copied into
  `core/oddsdata/inputs.py` with equality tests (R2-6).
- No star or dynamic import, no Name or Attribute `exec` or `eval`, no bare `compile`, and none of the compliance
  `DYNAMIC_MODULES` (with the follow-up's F1 and R2-10 additions, `pstats` and `tracemalloc` included; no attribute of
  the name `importlib` other than `metadata`). `importlib.metadata` is allowed, and so is `faulthandler`.
- Write the 40% cut as `1.0 - LIVE_SHARPE_MULTIPLIER`, never a literal `0.4` beside `*`, `x` or `×`.
- `core/odds/*.py` may import only the standard library (minus the network, dynamic and file-I/O modules), `numpy`,
  `scipy`, `core.isolation`, concrete `core.compliance` modules and concrete `core.odds` modules. No clock, no
  `__main__` block, no file I/O, no package re-export import, no subfolder. Its only I/O is through
  `owner.calendar_in_force`.
- `core/oddsdata/*.py`: the wall clock only in `run.py`'s `main()`; the only `__main__` block is `run.py`'s
  `raise SystemExit(main())`; every file write is preceded in the same function by `core.isolation.checked_target`.
- `core/odds/__init__.py` and `core/oddsdata/__init__.py` are 0 bytes. The sentence catalogue is Python constants in
  `core/odds/report.py`; rendered text holds no banned word of spec 7.5 (hyphen parts included, so never
  "floor-safe") and no underscore except the card id "S_C3".

**Writes and encodings**
- Every file the odds code writes (bars cache, its tmp and manifest, the yfinance cache folder, `state.json` and its
  tmp) goes through `core.isolation.checked_target()` immediately before it is opened, under
  `core.isolation.state_root()/"odds"`.
- Every text open passes `encoding="utf-8"`. JSON on disk is `core.compliance.model.canonical_json`. The CLI writes
  UTF-8 to stdout.

**Values copied verbatim from the spec and the rulings**
- CHUNK = 200,000; defaults 1,000,000 paths (moonshot) and 200,000 (compounding); a partial chunk is refused.
- Tick floor: max(table rate, 1.4 + 0.5 x tick/price x 1e4) bp per side; table rates 3 (KRX ETF), 35 (KRX stock,
  sell tax included), 50 (US), 10 (crypto); the 2,005-KRW ETF fill costs 13.8688 bp per side. On a KRX stock sell the
  floor also holds that year's `SELL_TAX_BP` (20 bp in 2026) inside the max, exactly as `instruments.cost_per_side`
  does (R2-1): 46.4 bp on a 200-KRW sell. Never a separate tax on top. A sell year missing from `SELL_TAX_BP` makes
  the leg NOT_TRADABLE.
- Stress doubles kappa and phi; a limit-down carry doubles the exit charge again (flat); R_exit = 4 x phi_sell.
- `LIVE_SHARPE_MULTIPLIER` 0.60, `Z_BOUND` 22, `DELIST_STRESS` (0.30, 1.00), `LIMIT_DOWN_CARRY_COST_MULTIPLIER` 2.0.
- HIDDEN_EDGE delta = 1e-4, its range fixed before the run; CEILING_BREACH amber at the one-sided 95% bound, red at
  1 - 0.001/m; L_min = L under floor-protected sizing, else 0.
- GARCH pilot: 20,000 paths; 1e-7 per step and 1e-6 summed over the horizon; 4 SE at every step. Its corruption test
  shifts c by 2e-6 per node (check 1) and triples the ratio (check 2 at 90 steps). The implementer confirms each
  margin on the real "pilot" stream and records it in the ledger. A check-2 margin under 4 SE raises the corruption
  factor; the thresholds are never lowered (R2-9).
- D13 pins: lookbacks (7, 14, 21, 28), mas (10, 20, 50, 100, 200), embargo 1, cost 10 bp, 11 trials, seed 11, domain
  (0.0, 0.889), OOS Sharpe 1.216 +/- 0.02, PASS, chosen hysteresis 0.667, pnl md5 bbdcf17ca9462567fe351c54644bef0c,
  turnover md5 2d4edeb2f042c87fd1750d9c68e275f7, input md5 18ec83bdfe158efe4d648caf45ff849f, results md5
  ca757e25f508b588cb2f361719ec83cd; the card's bench_sr 0.788830441182887, bench_diff 0.4271945783845257, bench_ci
  (0.03344352887529298, 0.8346050647267628), haircut_sr 0.7296150117404476, 138 trades, 2,530 sessions, exactly.
- Number formats: point estimates to the nearest 2 significant figures with "about"; interval ends outward; the
  ceiling and the bug check's blind spot rounded up, never down.
- Kelly: mu_lb from B = 2,000 stationary resamples with mean block 10; f* in [0, 1]; f* = 0 when mu_lb <= 0.
- SPECIAL_REGIME below 60 KRX sessions of history; Upbit minimum KRW 5,000; the KRX stock tick ladder of the KRX page.

## Decisions this plan makes

The tasks cite these as Q1 to Q46. Q1 to Q16 restate the rulings of 2026-10-24 (OWNER or CONTROLLER); Q17 to Q46 are
drafter decisions where spec and rulings are silent, and Q46 lists the departures from spec text adopted on review.
A decision the round-2 rulings amend or accept names its R2 item. None of them loosens anything: R2-1 removed the one
place where a ruling charged less than the repo's own cost function. GPT's checkpoint reads this list together with
the spec. The full text of each, and the map from the DIGEST's design questions DQ1 to DQ32 to the decision that
answers it, is in Appendix A section 1 (the interface contract).

- Q1 (OWNER, O1) Everything injected: signed core `core/odds/{plan,costs,models,simulate,bold,report}.py` plus
  `venues.yaml`; unsigned `core/oddsdata/{bars,replay,inputs,run}.py`; copies with equality tests (the provenance
  helpers `repo_anchor` and `tree_hash` copied into `inputs.py`, R2-6); passed-in data with recomputed hashes; the
  closure holds no data layer; no subfolders.
- Q2 (CONTROLLER, O2) Odds-own guards in `tests/odds_guards.py`, each with a positive control.
- Q3 (CONTROLLER, O3) The compliance-side prerequisites are Tasks 2 to 4.
- Q4 (CONTROLLER, O4) `Bracket`, `Leg`, `Plan`, `Fraction` as spec 7.1; facts from the approved map.
- Q5 (OWNER review_by; CONTROLLER, O5) review_by stops new entries from its date; auto_off and effective_until force
  an exit at the first check on or after the date.
- Q6 (CONTROLLER, O6) CALENDAR_UNSIGNED unless the in-force signed calendar sha equals the passed one;
  CALENDAR_COVERAGE past 2027-12-31; US close on Seoul d + 1; KRW=X; fixed finality instants.
- Q7 (OWNER, O7) Feeds: Upbit candles; OKX = Binance BTCUSDT x Upbit KRW-USDT with a KRW=X fallback (PROXY_DATA);
  KIS daily rows; yfinance through `_yf_download`; other venues refused.
- Q8 (OWNER, O8) SPECIAL_REGIME below 60 KRX bars of history.
- Q9 (CONTROLLER, O9) The D13 replay from the committed cache, exact pins, mu_lb and Kelly as ruled.
- Q10 (CONTROLLER, O10) pw_block copy (variants rounded half up), the vectorised generator, per-edge band rounding,
  the GARCH pilot and a corruption test sized to what each check can see, ddof 1, CHUNK swapped in tests.
- Q11 (CONTROLLER, O11 as amended by R2-1) W = the stake; the OKX cap per entry (an unset cap refused in the
  precheck); kappa per book and side, the KRX stock sell tax inside the floor exactly as `instruments.cost_per_side`
  (equality test, a 2027 sell included); the copied date validity (KRX stock sells only in signed tax years, else
  NOT_TRADABLE); NOT_TRADABLE for missing terms (a replay leg needs no fixed charges, R2-5).
- Q12 (CONTROLLER, O12) The seed and the persisted comparison state; a comparison keeps its run counter, so its
  plans share every stream and reruns reproduce; `--comparison` takes only issued ids; each card prints R, the
  seeds the plan has been run on.
- Q13 (CONTROLLER, O13) The bars cache, the seams, the suite and its budget.
- Q14 (CONTROLLER, O14) One catalogue; the language guard, which `render` also runs on its own output; provenance
  rendered as hashes, versions, dates, counts and labels only; the stated limits of everything injected, worded so
  they claim no check the core does not run.
- Q15 (CONTROLLER, O15) The CLI and its exit codes 0, 2 and 4.
- Q16 (CONTROLLER, DQ26) The follow-up runs first; neither plan waits for GPT.
- Q17 Venue odds keys `lot`, `min_order`, `fee_extras` (check_extras), `tick_ladder`, each with its own source.
- Q18 Shipped values: only researched ones (KRX lot 1, KRX minimum one lot, the KRX stock ladder, Upbit KRW 5,000);
  no fixed charges are researched, so every leg is NOT_TRADABLE until the owner signs explicit values.
- Q19 `owner.calendar_in_force(now)`: the latest approved calendar sha at `now`, only with an OK owner state and an
  intact stored copy; it and `_calendar_line` share `_calendar_approval` (a recorded departure from O3's wording).
- Q20 `gate.grey_rows(plan, ctx)`: the in-force grey row ids of the leg, pure, never raising.
- Q21 The signed-home helpers become public compliance fixtures.
- Q22 A horizon holds the sessions whose own date is in [start, start + H); open and close checks; their Seoul dates.
- Q23 Horizon 1 to 366 days; 3,650 days of history; SHORT_HISTORY below 250 bars.
- Q24 Nineteen named refusal codes and their fixed order (O10's order kept; the start date, unsigned code and the
  OKX cap in the precheck; the clock reading checked before the calendar).
- Q25 Field ranges of the plan types and the plan file; the plan starts on the Asia/Seoul date of the run.
- Q26 The simulator's state machine (exit priority, locks released only above the locking session's D, one fill per
  check, re-entry, daily loss, AT_FLOOR, REACHED, first passage).
- Q27 The cost ledger per fill (clipped proportional exit charge, so cash never goes below 0).
- Q28 Affordability and the fixed, Kelly and bold stakes with lot rounding.
- Q29 Delisting stress: a sale at p(1 - h) at the first check after the first entry; no re-entry.
- Q30 The assumed-edge tilt by bisection on a 20,000-path pilot; ASSUMED_EDGE_UNREACHABLE.
- Q31 Columns and spread members; GARCH sub-chunks; the refit member, each refit pilot-checked (accepted, R2-8); a
  failed headline model is MODEL_CHECK_FAILED; the spread wording follows the members actually run.
- Q32 L_min per sizing; why the ceiling holds (the gross mark, not the liquidation value); HIDDEN_EDGE (drift only,
  its range fixed in advance), CEILING_BREACH, the spread and the average line (the SE of the tested statistic);
  numbers never rounded in their own favour (outward interval ends, the ceiling as a percentage from 1%).
- Q33 The bracket reference as a duration-aware dynamic programme (an estimate; amber only).
- Q34 The seed's exact bytes and stream ids.
- Q35 KRW series composition, the FX join and FX finality.
- Q36 Cache and state file formats; both fail closed.
- Q37 Rendering: no plan name, no internal name, book-based cost words.
- Q38 The replay's no-edge columns (a fair-sign two-point kernel on the replay's own block-resampled moves, base and
  2x costs) and tested column (with its block growth printed), and its floor-protected engine.
- Q39 The checks the core runs on injected data (DATA_INVALID, a stale last price and an empty horizon included;
  STALE_DAYS 3 for crypto and 14 for KRX and US, accepted by R2-8).
- Q40 The test harness and its swaps.
- Q41 The ETF band at reference 2,005 is [1,404, 2,605] under O10's per-edge rule (R2-2 fixed the ruling's stray
  "1,405"); `orders.limit_prices` is not changed, and the hand-off tells E3 to take band edges from the venue's own
  quoted limit prices, never to compute them.
- Q42 Purity of the core; the cryptography version passed in.
- Q43 The COST_DOMINATED flag at an average cost of 10% of the stake.
- Q44 IMPOSSIBLE for buy-and-hold KRX legs with dated limits, with no probability of the target printed.
- Q45 The precheck runs before any data load, so a real-home run before owner act 1 refuses without network or writes.
- Q46 Departures from spec text adopted on review and accepted by R2-3, for rev 3.3 (the HIDDEN_EDGE resolution and
  wording, the bug-check clause, the ceiling format, the replay no-edge column, red flags first, the fresh-seed line
  handed to E2, new refusals, HIDDEN_EDGE unavailable with no finite range; item 7 withdrawn by R2-5). The list above
  under "For spec rev 3.3" spells them out.

## File map

| Path | Status | Task(s) | Responsibility |
|---|---|---|---|
| `core/odds/__init__.py` | create (0 bytes) | 1 | package marker; must stay empty |
| `core/odds/plan.py` | create | 5 | plan types, injected-input types, refusal codes, product, state and data checks |
| `core/odds/costs.py` | create | 6 | copied cost table and tick floor, venue terms, bands, affordability, stakes |
| `core/odds/models.py` | create | 7, 8, 17 | block length, index generator, two-point kernel, seeds, GARCH-t copy and pilot, D13 pins, Kelly, block growth |
| `core/odds/simulate.py` | create | 9, 10, 13, 14, 17 | the path engine, the pipeline, the columns and the spread |
| `core/odds/bold.py` | create | 11 | ceiling, structural maximum, bracket reference, brackets needed, exact bold play |
| `core/odds/report.py` | create | 9, 12, 13, 14, 17 | column stats, statistics and number formats, flags, the sentence catalogue, rendering, the language guard |
| `core/odds/venues.yaml` | modify | 3 | the sourced lots, minimums and KRX stock ladder (draft; needs the owner's approval) |
| `core/oddsdata/__init__.py` | create (0 bytes) | 1 | package marker |
| `core/oddsdata/bars.py` | create | 15 | data seams, loaders, finality, KRW composition, the bars cache |
| `core/oddsdata/inputs.py` | create | 16 | calendar from the store, sessions and limits, provenance (copied `repo_anchor` and `tree_hash`, R2-6), comparison state |
| `core/oddsdata/replay.py` | create | 17 | the S_C3 replay from the committed cache |
| `core/oddsdata/run.py` | create | 18 | the CLI (the only wall clock) |
| `core/compliance/rules.py` | modify | 2, 4 | venue odds keys; the calendar line on the shared helper |
| `core/compliance/owner.py` | modify | 4 | `calendar_in_force` |
| `core/compliance/gate.py` | modify | 4 | `grey_rows` |
| `tests/odds_acceptance.py` | create | 1 | suite aggregator, wrapper, seams and `REAL_SEAMS`, watches, `-m` runner |
| `tests/odds_fixtures.py` | create | 1, 5, 9, 13 | swaps, fixture venues, series, plans, contexts, inputs |
| `tests/odds_guards.py` | create | 1 | odds-own static guards, closure test, registration, harness self-tests |
| `tests/odds_plan.py`, `odds_costs.py`, `odds_models.py`, `odds_garch.py`, `odds_simulate.py`, `odds_locks.py`, `odds_bold.py`, `odds_report.py`, `odds_pipeline.py`, `odds_columns.py`, `odds_bars.py`, `odds_inputs.py`, `odds_replay.py`, `odds_cli.py` | create | 5 to 18 | one test module per task |
| `tests/compliance_tables.py`, `tests/compliance_gate.py`, `tests/compliance_fixtures.py`, `tests/compliance_store.py` | modify | 2, 3, 4 | compliance-side tests and the moved fixtures |
| `tests/run_all.py`, `README.md` | modify | 1, 19 | register the `odds` suite; record the full run |
| `docs/superpowers/plans/2026-10-24-odds-engine-execution-ledger.md` | create (untracked until Task 19) | 1, every task, 19 | merged line numbers, drift rulings (R2-13), R2-9 margins, runs |

No `tests/macro_*.py` file changes: the odds twins of the macro state-path test live in `tests/odds_bars.py` and
`tests/odds_inputs.py`.

## Owner gates during execution

1. None inside the plan: no download, no install, no signature and no scheduled task is needed.
2. **After this plan: the owner acts of spec section 11 that the odds engine needs.** Until they are done, every odds
   run is refused (STATE_UNUSABLE, LIMITS_UNSET, CALENDAR_UNSIGNED or NOT_TRADABLE); that is the designed safe
   default, not a fault:
   - set up the signer and sign the code hash (owner acts 1 and 2);
   - add explicit fixed charges (`fee_extras`, 0 allowed) and the missing lots to `core/odds/venues.yaml`, then
     approve the venues file with the rules table and the instrument map (owner act 3); the S_C3 replay leg needs
     only the Upbit lot beside the shipped Upbit minimum (R2-5);
   - sign the calendar set (owner act 4; only crypto plans run until then);
   - set `total_loss_floor_krw`, `daily_loss_krw` and `okx_equity_share` (owner act 5; they take effect from the next
     Asia/Seoul day).

---
