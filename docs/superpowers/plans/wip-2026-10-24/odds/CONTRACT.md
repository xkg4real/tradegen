# Odds plan: interface contract (binding for every task drafter)

Repo: `C:\Users\whydi\OneDrive\Desktop\TRADEGEN` (git). The odds plan starts on branch `odds-engine`, cut from `main`
after the compliance follow-up plan (branch `compliance-followup`, cut from main's HEAD at execution time,
RULINGS_ROUND2 R2-11) has merged (RULINGS "Order of the plans").
Spec: `docs/superpowers/specs/2026-10-23-compliance-gate-and-odds-engine-design.md` rev 3.2. The rulings in
`scratchpad/odds_plan/RULINGS.md` (O1 to O15) override it where they say so, and
`scratchpad/odds_plan/RULINGS_ROUND2.md` (R2-1 to R2-9 and R2-13 for this plan; R2-10 to R2-12 bind the follow-up)
amends them and wins where they disagree. `scratchpad/odds_plan/RULINGS_ROUND3.md` (2026-10-28: G3-1 to G3-5 for both
plans, O3-1 to O3-22 for this one) rules the task drafters' open issues and wins over every task text; this contract
follows it where O3-6, O3-9, O3-15, O3-18, O3-19 and O3-20 say so. Every departure is listed in section 1 (Q46) and in
the plan header under "For spec rev 3.3" (R2-3, O3-19), so it can be folded into spec rev 3.3.
Repo facts: `scratchpad/odds_plan/map/DIGEST.md` and the per-area maps beside it. Compliance plan:
`docs/superpowers/plans/2026-10-23-compliance-gate.md` (header P1 to P39, Appendix A); its execution ledger
`docs/superpowers/plans/2026-10-23-compliance-gate-execution-ledger.md`.

Everything below is fixed. A task that needs a name not listed here defines it inside its own module as a private
helper (leading underscore) and names it in its Interfaces block. Never rename anything here. Where a number below was
checked by direct computation, section 16 gives the check.

Line references into existing files (`owner.py:739-747` `_module_file`, `owner.py:773` the `code_files` glob seed,
`tests/compliance_tables.py:633` the `minimum_krw` line of `test_venue_shape_rules`, `tests/compliance_store.py:21`
`TABLES` and `:242-299` the signed-home helpers `NOW` .. `_full_home`, `tests/compliance_guards.py:483-489` the
registration check, `gate.py:633-651` the start check and `Screening.flags`) are **as of main 995534b**; the plan is
written against main `5816d3c`, which equals `995534b` outside docs/. The follow-up plan edits `rules.py`, `owner.py`,
`tests/compliance_tables.py`, `tests/compliance_store.py` and `tests/compliance_guards.py` (among others) first, so
every task cites the name, Task 1 re-greps each name on the merged main and records the new line numbers in the
execution ledger, and every Edit of an existing file follows the DRIFT RULE of section 0 (R2-13).

## 0. Global rules (every task obeys these; the plan copies them into "Global Constraints")

**Hard rules from the owner's brief**
- Never arm the system, place a live order, or enter credentials or keys. Never edit anything under
  `C:\Users\whydi\OneDrive\Desktop\QUANTGEN`. Never write under `~/.nextgen`. Never run anything while QUANTGEN's test
  suite runs. Never delete `grokteam/PREREG_book.json` or `grokteam/out/frozen_book/`.
- Claude never runs `tools/signer/sign.py` with a real key, never asks for or handles the owner's passphrase, and never
  writes to the real `~/.tradegen/compliance/owner.jsonl`. Tests build owner logs only inside a temporary
  `TRADEGEN_HOME`, signed with the fixed test key (`tests.compliance_fixtures.test_key()`).
- No odds test and no task step calls a network function for real. Every data seam is faked inside the test.
- Real odds only: no output may present a probability for a refused run, and no text may round a probability to zero.
  This is not legal or investment advice; TRADEGEN and its author are not licensed advisors.

**Python and test runs**
- Interpreter: `.venv/Scripts/python.exe` (Python 3.13.14). Never `pip install` anything; this plan adds no
  dependency (numpy 2.3.5, scipy 1.18.0, yfinance 1.4.1 are already pinned in `constraints.txt`).
- No pytest. A test is a zero-argument `test_*` function that raises on failure.
- Overlap check: run it before every test command. It must print nothing; otherwise wait. QUANTGEN's Store Python
  runs as `python3.13.exe` with no `python.exe` beside it, so only a `python*` name filter sees it. The odds Monte
  Carlo is CPU-heavy: never run two suites at once.
  - PowerShell tool:
    `Get-CimInstance Win32_Process -Filter "Name LIKE 'python%'" | Where-Object { $_.CommandLine -match 'run_all' } | Select-Object ProcessId,Name,CommandLine`
  - Git Bash prefix (the PowerShell script in single quotes, so Bash leaves `$_` alone):
    `test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && <command>`
- One test or module: `.venv/Scripts/python.exe -m tests.odds_acceptance <module>/<test>` (or `<module>/`). It
  imports every suite (about 7 s) and never writes `qa/acceptance_results.json`. Expected PASS tail:
  `N/N passed, 0 failed, 0 not run`.
- One suite: `.venv/Scripts/python.exe tests/run_all.py --suite odds` (or `--suite compliance`). This rewrites the
  TRACKED CRLF file `qa/acceptance_results.json`; restore it with `git checkout -- qa/acceptance_results.json` after
  every `--suite` run. Only the final task commits it.
- After every task that touches `core/compliance`, `core/odds` or `tests/compliance_*`, also run
  `.venv/Scripts/python.exe -m tests.compliance_acceptance compliance_guards/` and `... compliance_store/`.
- After every task that adds or changes code under `core/`, run the core-wide scans: `.venv/Scripts/python.exe -m
  tests.macro_m0_harness` (T-RO-01), `-m tests.macro_tf_gov` (T-TF-GOV-06), `-m tests.macro_m7_ledger` (the Kish
  scan), `-m tests.macro_m8_forward` (T-TREND-04), `-m tests.macro_m6_context` (the r18 names) and `--suite cockpit`
  (test_08, test_09, test_16, test_18; restore `qa/acceptance_results.json` afterwards). Each must end with no FAIL.

**Files, line endings and commits**
- New files are UTF-8 with no BOM and LF endings.
- These files are CRLF and stay CRLF: `tests/run_all.py`, `README.md`, `config.py`, `requirements.txt`,
  `pyproject.toml`, `core/quant/history.py`, `grokteam/book.py`, `grokteam/selfcheck.py`, `qa/acceptance_results.json`
  and the `docs/asset_expansion/cache/*.csv` files. `constraints.txt` is mixed (line 1 LF, the rest CRLF); this plan
  does not edit it. LF files this plan edits: `core/compliance/rules.py`, `owner.py`, `gate.py`,
  `core/odds/venues.yaml`, `tests/compliance_tables.py`, `tests/compliance_store.py`, `tests/compliance_gate.py`,
  `tests/compliance_fixtures.py`, `tests/compliance_cli.py`. No `tests/macro_*.py` file is edited (O13): the odds
  twins of the state-path test live in `tests/odds_bars.py` and `tests/odds_inputs.py`.
- Edit existing files only with the Edit tool. Never `sed -i` (it strips CRLF here).
- Before every commit, `git diff --cached --stat` must equal `git diff --cached --stat --ignore-cr-at-eol`.
- Commit once per task with the repo-local identity. End each commit message with the `Co-Authored-By:` line of the
  model that wrote the commit (ledger ruling, 2026-10-24); for this controller that line is
  `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Branch `odds-engine`, which Task 1 creates from main's HEAD once the follow-up has merged.
- **DRIFT RULE (RULINGS_ROUND2 R2-13).** This plan is written against main `5816d3c` (equal to `995534b` outside
  docs/) and executes after the compliance follow-up merges. The follow-up changes `core/compliance/rules.py`,
  `owner.py`, `alerts.py`, `kr_rules.yaml`, `tests/compliance_guards.py`, `tests/compliance_tables.py`,
  `tests/compliance_store.py`, `tests/compliance_signer.py`, `tests/compliance_cli.py`, `tests/compliance_isolation.py`,
  `tools/signer/sign.py`, `data/krx/kis_client.py`, `core/ficc/data.py` and `README.md` (followup CONTRACT section 12).
  Of these, this plan edits `rules.py` (Tasks 2, 4), `owner.py` (Task 4), `tests/compliance_tables.py` (Tasks 2, 3),
  `tests/compliance_store.py` (Task 4), `tests/compliance_cli.py` (Task 4, only for an import fix) and `README.md`
  (Tasks 1, 19), and it reuses `tests/compliance_guards.py` helpers by name (section 15).
  - Every Edit of an existing file is an exact old-text/new-text pair quoted from `5816d3c` and names its anchor: the
    function, constant, test, YAML row or table row it sits in. A line number only helps find the anchor.
  - Before each Edit, re-read the file. If the quoted old text differs only because an earlier plan changed it, apply
    the same change to the current text, keep the earlier plan's behaviour, and record a one-line ruling in the
    execution ledger. If the change no longer makes sense, stop and rule before editing.
  - The same holds for every reused name (`_walk`, `_imports`, `_raw_hits`, `_dynamic_hits`, `_dynamic_module`,
    `CLOCKS`, `NETWORK_MODULES`, `DYNAMIC_MODULES`, `FORBIDDEN_MODULES`, `temp_home`, `ctx`): if an earlier plan
    renamed one, use the new name and record it. The follow-up renames none of them (followup CONTRACT section 12).
- Execution ledger: `docs/superpowers/plans/2026-10-24-odds-engine-execution-ledger.md` (LF). Task 1 starts it with the
  branch, the main it was cut from, the list `git diff --stat 5816d3c HEAD -- . ':!docs'` prints (the files earlier
  plans changed, where drift can occur), the re-grepped line numbers, and empty "Drift rulings", "Deferred minors"
  and "Runs" sections. It stays untracked until Task 19 commits it, so a `git status --short` check in any task allows
  exactly that one `??` line.

**Guards that bind `core/odds/*.py` and `core/oddsdata/*.py`** (raw text includes docstrings, comments and the
sentence catalogue)
- Never write upper-case `CANO` (so never `CANONICAL`; write `canonical` in lower case), `KIS_ACCOUNT` or
  `ACNT_PRDT_CD` (test_09, compliance raw guard, T-RO-01).
- Never write `order_cash`, `order-cash`, `place_order`, `submit_order`, `TTTC0802U`, `TTTC0801U`, `VTTC0802U`
  (test_08; this also forbids `replace_order`), nor `r18_research_log`, `r18_break_log`, `context_log/`,
  `tests.reference`, `reference_mode`, `reference_only=True`.
- Never write `private_key` or `seed_phrase` in any form, in any file under `core/`. Name random streams "seed" or
  "stream".
- Never write the strings `/v1/orders`, `/v1/withdraws`, `/v1/deposits/generate_coin_address`, `/api/v3/order`,
  `/sapi/v1/capital/withdraw`, `/sapi/v1/capital/deposit`, or any `/uapi/.../trading/` path (T-RO-01).
- Never define, and never call, a function named `transfer`, `withdraw`, `deposit_address`, or any other
  FORBIDDEN_CALLS name of `tests/macro_m0_harness.py` (`place_order`, `create_order`, `withdraw_coin`,
  `sign_transaction`, ...).
- Never import, in any form: `core.engine.orders` (and, in `core/oddsdata`, any `core.engine` module, since
  `core/engine/__init__.py` imports orders), `core.quant.forward_sim`, `core.quant.refusal`, `core.ficc.context_log`,
  `core.ficc.macro`, `core.ficc.flows_log`, `core.skills.macro_daily`, `docs.asset_expansion_study` or
  `asset_expansion_study`; nor the order-client tops of T-RO-01 (`ccxt`, `web3`, `pyupbit`, `binance`, `okx`, `bybit`,
  `bitcoin`, ...). In `core/oddsdata` also never `core.quant.gate_ledger` or `core.ficc.macro_artifacts`: their
  provenance helpers `repo_anchor` and `tree_hash` are copied into `core/oddsdata/inputs.py` (RULINGS_ROUND2 R2-6).
- No star import, `__import__`, `import_module`, `exec_module`, `load_module`, and no Name or Attribute `exec` or `eval`
  (so no `DataFrame.eval`); no import of `importlib.util`, `importlib.machinery`, `runpy`, `pkgutil`, `zipimport`,
  `pydoc`, `timeit`, `code`, `cProfile`, nor of any module the follow-up's F1 and RULINGS_ROUND2 R2-10 added to
  `DYNAMIC_MODULES` (`profile`, `pdb`, `bdb`, `trace`, `doctest`, `unittest`, `logging.config`, `pickle`, `_pickle`,
  `shelve`, `marshal`, `site`, `ensurepip`, `venv`, `tkinter`, `_tkinter`, `turtle`, `turtledemo`, `idlelib`,
  `pstats`, `tracemalloc`, every `importlib` submodule except `importlib.metadata`, and no attribute of the name
  `importlib` other than `metadata`), and no bare Name `compile` (`re.compile` stays legal). `importlib.metadata` is
  allowed (provenance versions); `faulthandler` stays allowed.
- Write `1.0 - LIVE_SHARPE_MULTIPLIER` for the 40% cut. Never a literal `0.4` next to `*`, `x` or `×` (T-TF-GOV-06),
  never `X/(1+(X-1)*Y)` shapes or `kish*` names (the Kish scan).
- **The O1 import allowlist for `core/odds/*.py`** (enforced by `tests/odds_guards.py`): the standard library minus
  the compliance `NETWORK_MODULES` and `DYNAMIC_MODULES` (read from `tests/compliance_guards.py` at test time; a
  target's `DYNAMIC_MODULES` membership is tested with `compliance_guards._dynamic_module`, never a raw prefix match,
  because the merged list holds the entry `importlib`) and minus
  the file-I/O modules `io`, `os`, `pathlib`, `shutil`, `tempfile`, `glob`, `fileinput`, `mmap`, `sqlite3`, `dbm`,
  `csv`, `zipfile`, `tarfile`, `gzip`, `bz2`, `lzma`; plus `numpy`, `scipy`, `core.isolation`, `core.compliance.<mod>`
  for an existing module file (`model`, `rules`, `gate`, `owner`), and `core.odds.<mod>` for an existing module file.
  Nothing else from the repo: not `config`, not `data.*`, not `core.quant.*`, not `core.calendars.*`, not
  `core.engine.*`, not `core.ficc.*`, not `core.oddsdata.*`, not `yfinance`, not `pandas`.
- `core/odds/*.py`: no wall-clock call (the compliance `CLOCKS` set: `datetime.now/utcnow/today`, `date.today`, every
  `time.*` reader, `from time import ...`); no `if __name__ == "__main__"` block (either operand order); no file I/O
  (no `open(...)`, no attribute call `.open`, `.read_text`, `.read_bytes`, `.write_text`, `.write_bytes`, `.mkdir`,
  `.unlink`, `.rename`, `.replace` on a Name `os`, `.load`, `.save`, `.savez`, `.savez_compressed`, `.loadtxt`,
  `.savetxt`, `.genfromtxt`, `.fromfile`, `.tofile`, `.memmap`); no package re-export import (`import core.odds`,
  `import core.compliance`, or `from core.<pkg> import <name>` where `<name>` is not a module file of that package).
  Every table reaches the core only through the sealed `Context` that `core.compliance.owner.load_context` builds.
  The only I/O the core reaches is through `core.compliance.owner.calendar_in_force` (Q19).
- `core/oddsdata/*.py`: the wall clock only inside `core/oddsdata/run.py`'s `main()`; the only `__main__` block is
  `run.py`'s, exactly `if __name__ == "__main__":\n    raise SystemExit(main())`; every file write (`open` with a mode
  holding `w`, `a`, `x` or `+`, `.write_text`, `.write_bytes`, `.mkdir`, `os.replace`, `os.rename`) is preceded in
  the same function by a call to `checked_target` (`core.isolation.checked_target`).
- `core/odds/__init__.py` and `core/oddsdata/__init__.py` are 0 bytes. No subfolder of `core/odds` holds a `.py` file
  (a subfolder escapes the D14 seeds, `core/compliance/owner.py:773`). The sentence catalogue is Python constants in
  `core/odds/report.py`.
- Every text open passes `encoding="utf-8"` (or uses bytes). JSON written to disk uses
  `core.compliance.model.canonical_json`. The CLI reconfigures stdout to UTF-8 like `tests/run_all.py:35-39`.

**The signed closure and re-signing**
- `core/odds/*.py` joins the D14 code hash automatically (`owner.py:773`). No owner key and no signature exist yet
  (owner act 1 is not done), so no task costs a re-sign today. Once the owner signs `code_approved`, every later change
  to any file of the closure needs a fresh owner signature before new exposure is allowed again.
- Third-party code is never hashed (`owner.py:739-747`): a numpy or scipy upgrade changes behaviour without a re-sign.
  Every report records the numpy, scipy and cryptography versions, and the card states this limit (O1, O14).

## 1. Plan decisions

Each task that implements one cites it as "Plan decision Q<n>". Source: OWNER (decided by the owner in chat on
2026-10-24), CONTROLLER (RULINGS.md, decided on the DIGEST evidence), or DRAFTER (made here because spec and rulings
are silent; each one only adds a refusal or fixes a reading, and none loosens anything). A decision that
RULINGS_ROUND2.md amends or accepts names its R2 item.

- **Q1 Layout: everything injected (O1, OWNER).** The signed core `core/odds/` holds only `__init__.py` (0 bytes),
  `plan.py`, `costs.py`, `models.py`, `simulate.py`, `bold.py`, `report.py` and `venues.yaml`. `bars.py` moves out to
  the unsigned sibling `core/oddsdata/` (spec 4 departure), which also holds `replay.py`, `inputs.py`, `run.py` and a
  0-byte `__init__.py`; `core.oddsdata.` does not match the acting prefix `core.odds.`. The core imports only the O1
  allowlist (section 0). What the core needs from the repo is either COPIED with an equality test in `tests/`
  (section 6, 7: the GARCH-t fit, simulation and correction table; `Z_BOUND` 22; `LIVE_SHARPE_MULTIPLIER` 0.60;
  `DELIST_STRESS` (0.30, 1.00); `LIMIT_DOWN_CARRY_COST_MULTIPLIER` 2.0 read from `core/engine/orders.py` by AST; the
  four book table rates, the tick-floor formula, `COMMISSION_BP` 1.4, the KRX ETF tick table and `SELL_TAX_BP` (the
  KRX stock sell tax inside the floor and its years' date validity, R2-1); the stationary
  Politis-White block length; `validate.sharpe`), or COMPUTED by `core/oddsdata` and PASSED IN as plain data with its
  hash (bars, session dates, dated KRX price limits, the calendar sha, version and file md5s, the S_C3 replay output,
  `repo_anchor`, `tree_hash`; the last two from copies of `gate_ledger.repo_anchor` and `macro_artifacts.tree_hash` in
  `core/oddsdata/inputs.py`, each with an equality test, RULINGS_ROUND2 R2-6). The core recomputes every hash it can
  from the passed arrays and states the rest as a
  limit on the card (Q39, O14). The D14 closure stays exactly `core/__init__.py`, `core/isolation.py`,
  `core/compliance/*.py`, `core/odds/*.py`; a new test asserts it holds no file under `core/oddsdata/`, `data/`,
  `config.py`, `core/quant/`, `core/calendars/`, `core/engine/`.
- **Q2 Odds-own guards (O2, CONTROLLER).** New `tests/odds_guards.py` (section 15) with a positive control per guard.
  The compliance guards keep their scopes (they already scan `core/odds` for raw words, forbidden and dynamic imports).
  No HTTP-verb check is needed in `core/odds`: the allowlist already excludes every HTTP client, so `np.delete` and
  `np.put` stay legal.
- **Q3 Compliance-side prerequisites first (O3, CONTROLLER).** Tasks 2 to 4 extend `rules.py` (venue odds keys, Q17),
  `venues.yaml` (sourced values only, Q18), add `owner.calendar_in_force` (Q19) and `gate.grey_rows` (Q20), and move
  the signed-home test helpers into `tests/compliance_fixtures.py` (Q21). They change the code hash and the venues
  sha; no approval exists yet, so nothing is re-signed.
- **Q4 Plan types (O4, CONTROLLER).** `Bracket`, `Leg`, `Plan`, `Fraction` as spec 7.1, kw_only frozen dataclasses
  with whitelist validation in `plan.check_plan` and named refusals. The name `Fraction` stays; `bold.py` imports
  `fractions` as a module and writes `fractions.Fraction`. Whitelist: venue in {kis, upbit, okx}; class `share` (KRX
  and US), `etp_1x` (multiple exactly +1.0), `coin`; cash, long, single leg; instrument facts from the APPROVED map in
  `ctx.active` (never the draft file).
- **Q5 Rule dates in the horizon (O5; review_by OWNER, the rest CONTROLLER).** From the Asia/Seoul date of any
  `review_by` flag of `Screening.flags`, the simulated plan opens no new position (no entry, no re-entry) but keeps and
  may close what it holds; the card prints RULE_CHANGE_IN_HORIZON with the date and "new entries stop then unless the
  owner re-approves". At the first check on or after an `auto_off` or `effective_until` flag date, a forced exit, and
  no new entry after it (spec 6.3 as written). Flags come from `gate.py:643-651`.
- **Q6 Calendar (O6, CONTROLLER).** KRX and US legs are refused `CALENDAR_UNSIGNED` unless
  `owner.calendar_in_force(inputs.now)` returns a sha AND `inputs.calendar_sha256` equals it (the unsigned side
  computes it with `rules.calendar_sha256` over the stored copy). A horizon past the calendar's coverage
  (CalendarCoverageError) is refused `CALENDAR_COVERAGE` (new reason; stricter). Crypto legs need no calendar.
  Half-open horizon `[start, start + horizon_days)`. A US session with New York date d has the Asia/Seoul close date
  d + 1 (fixed rule, verified for EST, EDT and early closes). US KRW prices: open_KRW = open_USD x FX(d - 1),
  close_KRW = close_USD x FX(d), FX = Yahoo `KRW=X` (exact ticker, inside the series hash; FX(x) per Q35). Finality:
  crypto bar d final at 00:00Z of d + 1; KRX at 15:40 KST on d; US at 16:10 America/New_York on d (fixed instants; no
  `data/macro` read).
- **Q7 Venues and feeds (O7, OWNER).** Upbit: its own `KRW-<symbol>` daily candles. OKX BTC/USDT: Binance BTCUSDT x
  Upbit KRW-USDT, with KRW=X before Upbit listed KRW-USDT (the first KRW-USDT candle date, found at run time),
  flagged PROXY_DATA with the dates. KIS: KRX shares and 1x ETFs from KIS daily rows (paged, 100 per call, rows with an
  open or close that is None or <= 0 dropped); US shares and 1x ETFs from yfinance (`auto_adjust=True`, explicit
  start and end) through `bars._yf_download`. Refused: OKX BTC/USDC (an OKX leg always quotes `default_quote` USDT),
  bithumb, coinone, korbit (UNSUPPORTED_PRODUCT, sub `venue`), any OKX symbol other than BTC (UNSUPPORTED_PRODUCT,
  sub `feed`), and any venue or symbol without a signed minimum, lot or fixed charge (NOT_TRADABLE).
- **Q8 SPECIAL_REGIME (O8, OWNER).** A KRX leg whose series holds fewer than 60 bars dated before the start is refused
  SPECIAL_REGIME (each KIS daily row is one KRX session of that symbol; gaps only make the count smaller, so the rule
  errs towards refusing). Resets and other special reference-price regimes are listed under "not in these numbers".
- **Q9 The D13 replay (O9, CONTROLLER).** `core/oddsdata/replay.py` replays S_C3 from the committed cache
  `docs/asset_expansion/cache/upbit_KRW-BTC.csv` (read with `csv`; never importing the study runner), returning
  plain data (section 13). The core pins every card input and protocol value, the exact digests and the statistics
  (section 7.5); any mismatch is CARD_NOT_REPRODUCED. No live pull. Kelly's mu_lb: stationary block bootstrap with
  geometric blocks of mean exactly 10, B = 2,000, stream `kelly` of the market seed. The TESTED_REPLAY column
  resamples the OOS net returns in stationary blocks of mean 10 (the card's block, not a fresh pw_block) with the
  mean scaled by `LIVE_SHARPE_MULTIPLIER`. Kelly f* = argmax over [0, 1] of mean ln(1 + f R_cons), decided at the
  boundaries by the sign of the derivative, then bisection; f* = 0 when mu_lb <= 0.
- **Q10 Models, statistics, simulator (O10, CONTROLLER).** pw_block: the copied stationary pw_block;
  b = max(1, pw(r), pw(r^2)); variants b' = max(1, math.floor(mult x b + 0.5)) capped at the history length (O10's
  "round" read as round half up; Python's `round` rounds half to even, so `round(0.5 x 5)` is 2, and the contract
  never uses it here). New vectorised Politis-Romano index generator (section 7.2). Band rounding per edge: D rounds UP
  to the tick valid at D's own price level, U rounds DOWN to the tick valid at U's level, then D <= reference <= U
  (Q41). GARCH pilot: 20,000 paths from stream `pilot`; check 1 (deterministic, <= 512 quantile nodes, 1e-7 per step,
  1e-6 summed over the horizon per path, c_quad by `scipy.integrate.quad`); check 2 (statistical, 4 SE at every step;
  it sees a per-step drift error dc only above about 4 sigma / sqrt(N h), about 3e-5 at sigma 0.01, N 20,000, h 90);
  the corruption test monkeypatches the copied correction table in `core/odds/models.py` with magnitudes sized to
  those limits (section 7.4). Empirical Bernstein: ddof = 1, R the full range. CHUNK is a module constant 200,000
  that tests swap (to 2,000) with save/restore, together with `DEFAULT_PATHS` and `GARCH_SUB` (section 3.2); one test
  runs at the real value, and the "multiple of CHUNK" refusal is tested at the real value. Refusal order: Q24.
- **Q11 Stakes, equity, costs (O11, CONTROLLER).** `Positions(equity_krw=float(plan.stake_krw))`. Every simulated OKX
  entry is capped at `ctx.owner.caps["okx_equity_share"] x stake_krw`, stated on the card; an OKX leg whose cap is not
  a number in (0, 1] is refused LIMITS_UNSET in the precheck (Q24), so `first_stake` never reads a missing cap.
  `screen` gets `float(first_stake)`; a zero stake never reaches it (STUCK_AT_START first). kappa per fill and side
  (section 6.3): KRX_ETF_line by the copied `cost_per_side` logic; KRX_stock_book, as O11 is amended by RULINGS_ROUND2
  R2-1 (copy the repo's behaviour faithfully), `max(35 bp, tick_floor_bp(price, ladder_tick(price),
  tax_bp=SELL_TAX_BP[fill year] if side == "sell" else 0.0))` with the signed venues ladder, exactly as
  `instruments.cost_per_side` puts the tax inside the floor (so a sell below about 368 KRW pays more than 35 bp: at
  200 KRW, 46.4 bp on the sell and 35 bp on the buy); US_shares_KIS 50 bp and crypto_venue 10 bp exactly, with no tick
  floor until a ladder for the book is signed in venues.yaml. Never a separate sell tax on top. Date validity is
  copied exactly as the original raises it: a KRX_ETF_line fill before the copied ETF table's first date, a
  KRX_stock_book sell in a year missing from the copied `SELL_TAX_BP` ({2026: 20.0} today; instruments
  `_sell_tax_bp`) and a KRX_stock_book fill before the signed ladder's `effective_from` raise the local NotTradable.
  Every check of a KRX stock leg can hold a sell, so `costs.check_validity` refuses a horizon with any session date in
  a missing year, or before `effective_from`, before any path is simulated, and the leg is NOT_TRADABLE (stricter than
  O11 as first written). Missing minimum, lot or fixed charges: NOT_TRADABLE (a replay leg needs no fixed charges,
  Q25, R2-5); an explicit signed 0 is allowed.
- **Q12 Seeds and persisted odds state (O12, CONTROLLER).** Market seed per spec 7.3 with the byte layout of Q34;
  streams `SeedSequence(int.from_bytes(seed, "big"), spawn_key=(chunk, stream_id, ...))`. The comparison id, run
  counter and the K plans / J typed win rates persist in `core.isolation.state_root()/odds/state.json`, written by
  `core/oddsdata/inputs.py` with `checked_target` and an atomic replace; the core receives them as inputs. A comparison
  is one CLI invocation, or one explicit `--comparison` id across invocations. The run counter that enters the seed is
  the comparison's own, fixed when `begin_run` creates the comparison (`comparisons[cid]["run"]`) and reused by every
  later invocation of that id, so every plan of one comparison shares every stream (spec 7.3) and rerunning a plan in
  its comparison reproduces its numbers exactly. `--comparison` accepts only an id `begin_run` issued earlier (an
  unknown id is UNSUPPORTED_PRODUCT sub `comparison`), so the owner never chooses the seed; a fresh seed comes only
  from a new comparison. Every card prints R, the number of comparisons whose plans include this plan hash (the seeds
  it has been simulated on), beside K (`compare.r`).
- **Q13 Cache, seams, harness (O13, CONTROLLER).** Bars cache under `state_root()/"odds"/"bars"` (call time), the
  grokteam `write_cached` pattern, keyed by (source, symbol, start, end), pinned by window and sha256, `--refetch`
  bypasses the read, env `TRADEGEN_ODDS_BARS_CACHE=0` disables it (never `FICC_CACHE_TTL_SECONDS`). yfinance:
  `yfinance.set_tz_cache_location(str(state_root()/"odds"/"yfinance"))` inside the seam, before the download. Seams
  `_kis_daily`, `_upbit_daily`, `_binance_daily`, `_yf_download` are module-level functions of `core/oddsdata/bars.py`
  that import their client inside and are looked up at call time; `tests/odds_acceptance._wrap` patches them to raise
  (save/restore) and keeps the real functions in `REAL_SEAMS`, so a seam-body test calls the real body against a
  fake client module installed in `sys.modules` (yfinance's curl_cffi session bypasses the socket patch, so the real
  `yfinance` must never be reached in a test); one probe test proves an unpatched call is refused, and an AST test
  proves the functions of `bars.py` that import `data.*` or `yfinance` are exactly `SEAMS`. Suite `tests/odds_acceptance.py` mirrors
  `compliance_acceptance.py`; registered in `tests/run_all.py` and README (both CRLF). The follow-up's F7 already
  loosened the registration literal (`tests/compliance_guards.py:483-489`), so this plan only adds "odds" to the help
  text and the README list. Test files are `tests/odds_*.py`; fixtures in code (no `tests/fixtures/odds/` is needed).
  Budget: the odds suite about 3 minutes, every test at most 15 s, most under 2 s.
- **Q14 Report (O14, CONTROLLER).** Everything spec 7.5 lists, from one catalogue in `report.py` (section 10). The
  language guard bans the whole words of spec 7.5, case-insensitive, hyphen parts included, so `floor-safe` (which
  holds `safe`) never renders: the sizing label is "Floor-protected sizing". Rendered text never holds an underscore,
  so no internal name renders; `render` runs `guard` over its own output and raises on any hit (exit 4: fail closed).
  Provenance lines render only hashes (16-hex prefixes), versions, dates, counts and catalogue labels: never a calendar
  file id, a member, model or edge-source key, or `CARD_ID` (section 10.1). The card states the limits of "everything
  injected" honestly (`limits.injected`): unsigned code loads the prices, the session list and the replay; the core
  records their hashes but cannot check them against a signed source; only the calendar set's sha is matched to the
  signed approval; numpy and scipy are outside the hash.
- **Q15 CLI (O15, CONTROLLER).** `python -m core.oddsdata.run --plan <plan.json> [--comparison <id>] [--paths N]
  [--refetch]` (section 14). Exit 0 every plan reported, 2 at least one plan refused (its named reason printed), 4 a
  crash (any exception, argparse errors included). It never writes the owner log.
- **Q16 Order of the plans (RULINGS "Order", CONTROLLER, DQ26).** The follow-up runs first; this plan branches from
  main after it merges. Neither plan waits for GPT's check after 2026-10-30 14:40; a valid finding that touches built
  code becomes a new task with its own failing test. Both plans state that once the owner signs `code_approved`, any
  later closure change needs a fresh signature.
- **Q17 Venue odds keys (DRAFTER, fills O3).** Four optional keys per venue in schema `tradegen.venues/1`, each a
  mapping with a mandatory non-empty `source` (a repo reference or an https URL of the research corpus, or the literal
  `UNVERIFIED: owner to confirm before approval`): `lot: {source, units: {<symbol>|default: step > 0}}`,
  `min_order: {source, quote: {<settlement asset>: amount >= 0}}`, `fee_extras: {source, phi_buy: >= 0, phi_sell: >= 0}`
  (KRW; this is `check_extras`: a negative extra is INVALID), `tick_ladder: {source, effective_from: "YYYY-MM-DD",
  books: {<cost book>: [[price_from, tick], ...]}}`. Strict types: finite numbers, no bools; ladders start at
  price_from 0 and strictly increase; ticks > 0; a ladder book must be the cost book of a symbol in the venue's
  sections and must not be `KRX_ETF_line` (its ladder is the copied instruments table). The parsed `Venue` gains four
  hashable defaulted fields and three lookups (section 4.1). Top-level keys stay {schema, venues}.
- **Q18 Shipped venue values (DRAFTER, O3).** Only researched values (section 4.2): kis `lot` 1 for 005930 and 069500
  (research table rows L161 "1 share" for KOSPI/KOSDAQ stocks and L163 "1 unit" for plain 1x ETFs; L159 is only the
  header row), kis `min_order {KRW: 0}` (the same rows: the minimum is one lot), the KRX
  stock ladder from the KRX tick page (`effective_from: "2026-10-02"`, the date the research gives), upbit
  `min_order {KRW: 5000}` (Upbit docs). No `fee_extras` anywhere and no Upbit, OKX or US lot: no research source gives
  them, so EVERY leg is NOT_TRADABLE in the shipped draft until the owner adds explicit values (an explicit 0
  included) and signs the venues file (the replay leg needs only the Upbit lot beside the shipped minimum, R2-5). No
  deposit network is added (an owner act).
- **Q19 `owner.calendar_in_force(now)` (DRAFTER, O3, O6).** Returns the sha256 of the latest `approved {kind:
  calendar}` entry stamped at or before `now`, only when the owner state at `now` is OK (verified log, repo public key,
  no KEY CHANGED) and the stored copy is intact (`store_get` not None); otherwise None. ValueError on a naive or
  out-of-range `now`, like `load_context`; every other failure is None. `rules._calendar_line` keeps its four exact
  lines by calling the shared private `owner._calendar_approval(now) -> tuple[str, str]`. Departure from O3's wording
  ("refactor `_calendar_line` to call it", recorded for rev 3.3): `_calendar_line` needs four outcomes and
  `calendar_in_force` returns two, so both call `_calendar_approval`; a test pins that `calendar_in_force(now)` is the
  sha exactly when `_calendar_approval(now)[0] == "ok"`, on every case of Task 4.
- **Q20 `gate.grey_rows(plan, ctx)` (DRAFTER, O3).** The ids of the in-force venue rows with `treatment == "grey"` that
  match the plan's leg decided as a cash buy on `ctx.date` (the same synthetic intent `screen` builds), sorted; `()` for
  an unsealed context, an unusable state, an unknown venue or symbol, or any exception. Pure; never raises.
- **Q21 Signed-home fixtures (DRAFTER, O3).** `tests/compliance_fixtures.py` gains the public `NOW`, `HELD`,
  `TABLES`, `pubkey_at`, `owner_key`, `sign`, `approve`, `other_code` and `full_home` (section 3.3);
  `tests/compliance_store.py` imports them back under its old private names, so its tests are unchanged.
  `full_home` gains `venues_raw`, `calendar_raw`, `limits` and `cap` keywords for the odds suite.
- **Q22 Sessions and check points (DRAFTER, O6).** A horizon holds every session whose own market date d is in
  `[start, start + horizon_days)`: KRX and US dates from the signed calendar (`sessions_between(m, start,
  start + H - 1)`), crypto every calendar date. Check points: the two-point bootstrap checks the open, then the close,
  of each session; GARCH-t and the replay check the close only. Asia/Seoul date of a check: KRX open d, close d; US
  open d, close d + 1; crypto open d, close d + 1. `on=` for a cost quote is the session's own date d. The first check
  of a bootstrap run is the open of the first session, moved from the last historical close.
- **Q23 Bounds (DRAFTER).** `1 <= horizon_days <= 366` (`MAX_HORIZON_DAYS`; UNSUPPORTED_PRODUCT sub `horizon`). The
  loader asks for the 3,650 calendar days before the start (`HISTORY_DAYS`). A series with fewer than 250 bars before
  the start is refused SHORT_HISTORY (new reason; pw_block needs 20 and the GARCH fit 100).
- **Q24 Refusal codes and order (DRAFTER, fills O10/DQ32).** Codes (exact strings, `plan.REFUSALS`):
  `PARTIAL_CHUNK`, `UNSUPPORTED_PRODUCT`, `MULTI_LEG_UNSUPPORTED`, `STATE_UNUSABLE`, `LIMITS_UNSET`,
  `CALENDAR_UNSIGNED`, `CALENDAR_COVERAGE`, `DATA_INVALID`, `SYNTHETIC_REFUSED`, `NOT_TRADABLE`, `SPECIAL_REGIME`,
  `SHORT_HISTORY`, `CARD_NOT_REPRODUCED`, `MODEL_NOT_FOR_LIMITED_VENUE`, `COST_DOMINATED`, `STUCK_AT_START`,
  `SCREEN_BLOCKED`, `ASSUMED_EDGE_UNREACHABLE`, `MODEL_CHECK_FAILED`. New beyond the spec: PARTIAL_CHUNK (spec "a
  partial chunk is refused"), STATE_UNUSABLE (no usable owner state, or code changed since it was signed),
  CALENDAR_COVERAGE, DATA_INVALID, SHORT_HISTORY, COST_DOMINATED (spec: "A book where 4 kappa >= 1 is refused", "bold
  is refused ... net coefficient <= 0"), SCREEN_BLOCKED (a gate BLOCK), ASSUMED_EDGE_UNREACHABLE (spec: "A p the tilt
  cannot reach is refused"), MODEL_CHECK_FAILED (the plan's own model, its headline, failed a pilot check or did not
  converge; spec 9 leaves out only spread members, and the headline cannot be left out). Order (the first one found
  is reported):
  1. PARTIAL_CHUNK;
  2. product: UNSUPPORTED_PRODUCT (sub `start` when `plan.start != ctx.date`, the gate's own rule at `gate.py:633-634`),
     MULTI_LEG_UNSUPPORTED (two or more legs; an empty legs list or a non-Leg item is UNSUPPORTED_PRODUCT sub `file`,
     O3-6); the class and multiple checks only when `ctx.active` is usable;
  3. STATE_UNUSABLE (sub `code` when `ctx.code_signed` is false: `screen` would BLOCK it anyway, and the precheck
     then refuses before any data load);
  4. LIMITS_UNSET (both limit keys; for an OKX leg also the OKX cap);
  5. DATA_INVALID sub `now` (`inputs.now` naive, or its Asia/Seoul date not `ctx.date`; checked first because
     `calendar_in_force` raises on a naive `now`);
  6. CALENDAR_UNSIGNED, CALENDAR_COVERAGE;
  7. DATA_INVALID (series, sessions, `empty`, `stale`), SYNTHETIC_REFUSED (`plan.check_data`);
  8. NOT_TRADABLE (`costs.terms`, then `costs.check_validity` over the horizon dates);
  9. SPECIAL_REGIME, SHORT_HISTORY (`plan.check_history`);
  10. CARD_NOT_REPRODUCED;
  11. MODEL_NOT_FOR_LIMITED_VENUE;
  12. COST_DOMINATED, STUCK_AT_START;
  13. SCREEN_BLOCKED;
  14. ASSUMED_EDGE_UNREACHABLE and MODEL_CHECK_FAILED, found only while the pilots run (the GARCH pilot first, then
      the tilt pilot).
  This keeps O10's order (data refusals SYNTHETIC_REFUSED, NOT_TRADABLE, SPECIAL_REGIME); step 5 before the calendar
  step is the one addition. A refused report carries no probability.
- **Q25 Plan details (DRAFTER, O4).** `Bracket(take_profit, stop)` as fractions: 0 < take_profit <= 1000, 0 < stop
  < 1. `Fraction(kind, value)` with `fixed(f)` (0 < f <= 1), `kelly(c)` (0 < c <= 0.5; replay legs only), `bold()`
  (bracket legs only, not replay). `stop_based` needs a bracket; `assumed` needs a bracket, the bootstrap model and
  0 < assumed_p < 1, and `assumed_p` is None otherwise; a replay leg is upbit BTC, no bracket, bootstrap, floor_safe,
  kelly or fixed. `track` in {moonshot, compounding} (sub `track`); stake_krw > 0, target_krw > stake_krw,
  fx_krw_per_usd > 0, all finite floats (sub `numbers`); `type(name) is str` (sub `file`); `type(start) is date` and
  `start == ctx.date` (sub `start`); `type(horizon_days) is int` (sub `horizon`). `tax_basis == "unsupported"` is
  refused. A replay leg needs only the signed upbit `lot` and `min_order` (`costs.terms(..., replay=True)`), never
  `fee_extras` (RULINGS_ROUND2 R2-5: the card's 10 bp already includes fees and Upbit has no fixed fee), which is spec
  7.2's "only whole-unit rounding and the KRW 5,000 Upbit minimum are added"; bracket and buy-and-hold legs still need
  signed `fee_extras`. The plan file format is section 14.2.
- **Q26 Simulator state machine (DRAFTER).** Section 8.4 fixes it: the exit priority (target, take-profit, stop,
  daily loss, rule date), the limit-down lock (a check at the session's D that would exit queues the exit until the
  first check strictly above `d_lock`, the D of the session where it locked, spec 7.2, at a flat 2x exit charge; new
  triggers use the current session's D), one fill per path per check, re-entry only for
  bracket legs and only at a later check, no entry at the last check, the daily-loss reference (the liquidation value
  carried into the Asia/Seoul date), AT_FLOOR (an exit fill leaves cash <= L, or an entry finds the largest affordable
  stake below the venue minimum), REACHED (moonshot: an executable exit at liquidation value >= T, or cash >= T after
  a fill), first passage for both tracks.
- **Q27 Cost ledger (DRAFTER, spec 7.1).** Per fill: proportional kappa x notional plus the fixed phi; the stress
  scenario doubles both; a locked exit doubles the exit charge again (flat, never compounding); R_exit = 4 x phi_sell
  reserved in every scenario; the proportional exit term is clipped at the position value, so cash never goes below 0.
  Liquidation value V = cash + units x p x max(0, 1 - kappa_s chi) - phi_sell' chi [units > 0], chi the carry
  multiplier when locked, else 1.
- **Q28 Affordability and stakes (DRAFTER, spec 7.1).** Section 6.5: price-dependent kappa at the entry price (and at
  the stop price for stop_based); lot rounding with a 1e-9 tolerance; minimum stake = max(one lot, the signed
  minimum in KRW) at the current price; a rule stake below the minimum is no bet (the path stays flat), while a
  largest affordable stake below the minimum is AT_FLOOR; bold uses kappa_w = max(kappa_b(p), kappa_s(p(1 + u))) and
  makes no bet once W >= T.
- **Q29 Delisting stress (DRAFTER, spec 7.2).** Share and coin legs only. At the first check after the first entry
  fill, the position is sold at p x (1 - h) with the normal exit charge (for h = 1.00: written off, no exit charge);
  the h x value loss is booked in the ledger as the delisting stress loss; the path never re-enters. Run on the headline
  member at base costs only. HIDDEN_EDGE is unavailable there.
- **Q30 Assumed edge (DRAFTER, spec 7.2).** Tilt q' = q e^theta / (q e^theta + 1 - q) at every check. theta by
  bisection on a 20,000-path pilot (stream `tilt`, common random numbers for every theta; run through the private
  `simulate._run_paths`, which takes any path count, never through `run_column`) over [-8, 8], 30 iterations,
  stopping when |win - p| <= 0.002; refused ASSUMED_EDGE_UNREACHABLE when p lies outside [win(-8), win(8)] or the final
  |win - p| > 0.01. A win is a take-profit fill before the stop among brackets resolved by take-profit or stop (a
  locked exit is unresolved). p0 and the unresolved share come from the full no-edge base column. Base costs only.
- **Q31 Columns and spread (DRAFTER, spec 7.5 items 8-9).** Members: `bootstrap` (b), `bootstrap_half` (0.5 b),
  `bootstrap_double` (2 b); for US and crypto legs also `garch_t` and `garch_refit` (B = 20 synthetic series from the
  fit, refitted; 20 groups of CHUNK/20 paths per chunk, group g using refit g; any failed refit drops the member). The
  headline is `leg.model`. Every member runs the no-edge column at base and at 2x costs (common random numbers: the
  same streams), so m = 2 x (members run). GARCH draws in sub-chunks of `GARCH_SUB` paths (`range(0, CHUNK,
  GARCH_SUB)`, sub index = start // GARCH_SUB as the spawn_key third element). A member whose fit does not converge
  (`GarchParams.converged` false; check `fit`; `at_bound` alone is recorded, not a failure) or whose pilot check fails
  is left out, with a note naming the check. `garch_refit` pilot-checks every one of its REFIT_B refits (an accepted
  plan decision, RULINGS_ROUND2 R2-8); a refit that fails its fit or its pilot drops the whole member with check
  `refit`. When the headline member itself is left out,
  the plan is refused MODEL_CHECK_FAILED (never a fallback headline, never numbers from a failed model). The spread's
  wording follows the members actually run: `spread.other` when another model family ran, `spread.krx` on KRX legs,
  `spread.blocks` (block-length wording without the KRX clause) when every other family was dropped, `spread.none`
  when no member besides the headline ran; each dropped member adds its `spread.dropped` note.
- **Q32 Flags and statistics (DRAFTER, spec 7.5).**
  - **L_min.** `l_min = ctx.owner.limits["total_loss_floor_krw"]` when `leg.sizing == "floor_safe"`, else 0.0 (spec 3
    and 7.4: under stop-based sizing a gap can pass the stop). Replay legs are floor_safe and their sleeve is cut by
    the floor-protected rule (Q38), so l_min = L there too. `OddsReport.l_min`, `ceiling()`, `hidden_edge()`,
    `bracket_reference()` and CEILING_BREACH all take this value. Stop-based cards print the ceiling without "that
    keeps this floor" (`ceiling.nofloor`, `ceiling.edgenf`).
  - **Why the ceiling holds.** With no real edge the gross mark M = cash + units x p (before exit charges) is a
    supermartingale (prices are martingales and every charge only subtracts), M >= L_min under floor-protected sizing
    (cash after any entry is >= L + R_exit), and the liquidation value V <= M. So P(V ever >= T) <= P(M ever >= T) <=
    (W0 - L_min)/(T - L_min) by Ville's inequality. V itself need not be a supermartingale where kappa depends on the
    price through a tick floor (a KRX ETF unit at 2,001 moving to 1,999 or 2,003 has E[V] 1.00 KRW above V), so the
    proof never rests on V (header "Real odds").
  - **HIDDEN_EDGE** on the headline no-edge base cell of bootstrap legs and on `replay_no_edge/base` of replay legs,
    with X = G_tau - W0 (gross value: cash + units x p (or the sleeve) + costs booked, tau the first of first passage,
    AT_FLOOR, horizon) and the range R of section 10.3, fixed before the run from the plan and the history; every fill
    and every delisting sale leaves G unchanged, so E[G_tau] = W0 exactly under no edge. G is a martingale under ANY
    martingale model, including one with the wrong volatility, block length or tails, so HIDDEN_EDGE detects drift (a
    simulator error that makes or loses money without an edge) and nothing about whether the model is right; its
    sentence says so. Unavailable when the range is not finite (section 10.3).
  - **CEILING_BREACH** over every no-edge cell (members x scenarios; replay: base and stress2x), on first-passage
    counts (`ColumnStats.reached`), compared on exact values.
  - **Plain sentence and spread** count `reached_outcome` on moonshot cards and `reached` on compounding cards. The
    spread is the range over the base no-edge cells of every member except the headline: from the highest two-sided
    upper bound to the lowest lower bound, a lower bound of 0 printing "below about 3 in n".
  - **Average line** agrees when |mean - (W0 - mean_cost)| <= 2 x g_se, with g_se = std(V_term + cost_term, ddof 1) /
    sqrt(n), the standard error of the statistic mean(V + C) - W0 actually tested (`ColumnStats.g_se`; the printed
    "± {se}" is `mean_se`, the standard error of the terminal value).
  - **Rounding: no claim is rounded in its own favour** (section 10.2). Point estimates round to the nearest 2
    significant figures with "about". Interval ends round outward: an upper bound's probability up (its "1 in N"
    takes N rounded down at 2 significant figures, a percentage the ceiling at 0.1%), a lower bound's probability down
    (N rounded up, the floor at 0.1%); so the printed interval always contains the Clopper-Pearson interval (the spec's
    k = 63 example prints unchanged: "between 1 in 12,000 and 1 in 21,000"). The ceiling, an upper bound, prints as
    "1 in floor(1/c)" below 1% and as "a {ceil(1000 c)/10}% chance" from 1% (so a compounding ceiling of 0.6667 prints
    "a 66.7% chance", never "1 in 1"). The HIDDEN_EDGE blind spot b/(T - L_min) is an upper bound of what it misses
    and prints the same way ("1 in floor((T - L_min)/b)", recorded as a departure from spec 7.5's ceil). The breach
    sentences print the lower bound and the ceiling rounded so that their printed order matches the exact comparison
    (section 10.2 `fmt_order`); the IMPOSSIBLE cap prints as ceil(cap).
  - **A no-edge figure above its ceiling.** When a no-edge cell's point estimate k/n is above its ceiling and no
    breach flag fires (the excess is counting noise), its probability slots print `cap.p` ("at most {c}, the ceiling;
    the simulated {k} in {n} is above it only through counting noise") in place of the point estimate.
  - **The bug-check clause** of the plain sentence is chosen by comparison: `bugs.coarser` (the spec's "the bug checks
    are coarser than these ranges") when HIDDEN_EDGE did not pass or its blind spot b/(T - L_min) exceeds the width of
    the headline's two-sided interval; else `bugs.finer` ("the bug check's resolution is printed below").
- **Q33 Bracket reference (DRAFTER, spec 7.4).** A duration-aware dynamic programme over (wealth, checks left) on the
  binned joint law of a bracket's (net return per unit stake, duration) from the headline no-edge column (section 9.1).
  An estimate; it only raises the amber ABOVE_ESTIMATED_REFERENCE.
- **Q34 Seed bytes (DRAFTER, O12).** `seed = sha256(b"tradegen-odds/seed/1\x00" + "\x00".join(sorted(data_hashes))
  .encode("ascii") + b"\x00" + calendar_digest.encode("ascii") + b"\x00" + comparison_id.encode("utf-8") + b"\x00" +
  run_counter.to_bytes(8, "big")).digest()`, where `run_counter` is the comparison's own creation counter
  (`Inputs.run_counter`, Q12), the same on every invocation of that comparison. Stream ids in `models.STREAMS`. Plan
  fields never enter the seed, so plans on the same data in one comparison share every stream.
- **Q35 KRW series composition (DRAFTER, O6, O7).** FX(x) = the close of the last KRW=X bar dated on or before x; a
  row with no such bar is dropped. An FX bar x is final at 00:00Z of x + 2 (its close instant is unknown, DIGEST open
  question 1; a day of margin). OKX: open_KRW = BTCUSDT open x KRW-USDT open, close_KRW = BTCUSDT close x KRW-USDT
  close on the same UTC date; dates before the first KRW-USDT candle use FX(d - 1) and FX(d) instead and are recorded
  as `proxy_dates`. Rows whose open or close is not a finite number > 0 are dropped. Source labels and component md5s:
  section 11.4.
- **Q36 Cache and state files (DRAFTER, O12, O13).** Formats in section 11.5 and at the end of section 12. A cache file that disagrees
  with its manifest line, or a state file that does not parse, fails closed (exit 4); the owner deletes it.
- **Q37 Report rendering (DRAFTER, O14).** The plan name never renders (free text); plans print as "Plan k of K" and
  the plan hash prefix. Refusal details are internal; the card renders the catalogue sentence of the code with
  number, date, symbol and row-id slots only. Cost words follow the book: `KRX_stock_book` "fees and the securities
  transaction tax", every other book "fees" (KRX ETFs pay no transaction tax, `instruments.py:20`).
- **Q38 Replay columns and engine (DRAFTER, O9).** With c_t = cost_bps x 1e-4 x turnover_t (the card's own cost on
  each OOS day), G_t = R_t + c_t (gross) and g_t = G_t - mean(G):
  - **No-edge replay columns** (`replay_no_edge/base` and `replay_no_edge/stress2x`, c doubled) are a two-point
    kernel on the replay's own magnitudes: each day the sleeve becomes `sleeve x (1 + eps x a[idx] - c[idx])` with
    a = |g|, idx from stationary blocks of mean 10 and eps = +1 or -1 with probability 1/2 from the independent stream
    `replay_sign`; c x sleeve is booked as cost. Blocks keep the volatility clustering and the link between a day's
    move and its cost, and the fair sign makes the gross value an exact conditional martingale. A demeaned block
    bootstrap of g is NOT a no-edge column (spec 7.2's trap): on the real S_C3 series g has autocorrelation 0.07 at
    lag 1, so given the current row the next move is predictable (E[g_next | row i] = 0.9 g_{i+1}) and plain holding
    gains 0.27% gross in 30 days (section 16.1). Max |g| = 0.1690 and max c = 0.001, so the sleeve never goes below
    0 (`replay_returns` asserts max a + 2 max c < 1).
  - **TESTED_REPLAY** moves the sleeve by R1_t = R_t - mean(R) + LIVE_SHARPE_MULTIPLIER x mean(R) (net, no separate
    cost), resampled in stationary blocks of mean 10. Blocks keep the strategy's streaks, so the column's average
    h-move growth is above the independent-days value (1 + mean R1)^h. The sleeve enters at the first close and moves
    at the later ones, so a 30-day horizon has h = checks - 1 = 29 moves: 2.889% against 2.613% ("2.9%" against
    "2.6%", RULINGS_ROUND3 O3-15). The card prints both (`replay.growth`, from `models.block_growth`, exact), so "40%
    of its average return removed" is never read against the wrong baseline. The earlier 2.99% against 2.70% is h =
    30, a column no engine runs; `block_growth(R1, 10, 30) = 1.029918` stays a separate pin.
  - **The replay engine** holds a sleeve s = the rule stake (kelly or fixed) sized by `costs.rule_units` with sizing
    `floor_safe`, `mult = 0.0` and the replay terms of `costs.terms(..., replay=True)` (phi_buy = phi_sell = 0, no
    `fee_extras` read, R2-5; so kappa = phi = R_exit = 0 and s <= cash - L: L_min = L), checks at the close only,
    rounds s to whole lots of BTC at the leg's last close at entry, needs the signed Upbit lot and minimum, adds no
    kappa and no phi, and follows the daily loss, rule dates, REACHED, AT_FLOOR and re-entry
    rules of Q26 (re-entry after a daily-loss stop at the next check, with the same rule).
  - **The replay card** has headline `replay_no_edge/base`; its no-edge cells (base, stress2x) run CEILING_BREACH
    (m = 2) and HIDDEN_EDGE runs on the base cell; the TESTED_REPLAY column prints `ceiling.edge` below it. No spread
    and no delisting columns.
- **Q39 Injected-data checks in the core (DRAFTER, O1).** DATA_INVALID unless: `inputs.now` is aware and its
  Asia/Seoul date equals `ctx.date` (sub `now`, checked before the calendar step, Q24); the series arrays have one
  length >= 2, finite values > 0, strictly increasing ISO dates all before `plan.start`, and `series.md5` equals the
  md5 the core recomputes (sub `series`); the last bar is at most `STALE_DAYS` calendar days before the start (3 for
  crypto, 14 for KRX and US, which covers the longest KRX holiday closures; an accepted plan decision, RULINGS_ROUND2
  R2-8; sub `stale`: a halted or delisted symbol is never simulated from an old price); `sessions` are strictly increasing ISO dates inside `[start, start + H)` (sub
  `sessions`) and at least one (sub `empty`: a KRX or US horizon with no session, such as one day on a Saturday); KRX
  legs carry one price limit per session with 0 < limit < 1, other legs none (sub `sessions`); `calendar_sha256` is
  64 hex (KRX/US) or "" (crypto) (sub `sessions`). Unsigned code still produces the data; the card says so.
- **Q40 Test harness (DRAFTER, O13).** Section 3: MODULES, `_wrap` (hermetic, temp home, seam patches with the real
  functions kept in `REAL_SEAMS`, real-home and repo-file watches), `chunk()` (CHUNK, DEFAULT_PATHS, GARCH_SUB) and
  `pilots()` (PILOT_PATHS, TILT_PILOT, PILOT_NODES) swaps, budgets.
- **Q41 Band edges at the ETF reference 2,005 (DRAFTER, O10).** Under O10's rule the lower edge of a 30% band is
  ceil(1,403.5 / 1) x 1 = **1,404** (1,403.5 is below 2,000, so its tick is 1) and the upper edge floor(2,606.5 / 5) x 5
  = 2,605. RULINGS_ROUND2 R2-2 keeps O10's per-edge rule and fixes O10's stray parenthetical "(lower edge 1,405)",
  which is the one-tick value `orders.limit_prices` would give with the reference's tick 5; the test asserts 1,404.
  The order layer's `core/engine/orders.limit_prices` (one tick for both edges) is not changed. The final task's
  hand-off carries the difference to E3 (live order adapters), not E1: E3 takes band edges from the venue's own quoted
  limit prices and never computes them.
- **Q42 Purity (DRAFTER).** `plan`, `costs`, `models`, `bold` and `report` make no I/O and read no clock; `simulate`
  reaches I/O only through `owner.calendar_in_force` for KRX and US legs. The cryptography version is passed in
  (`Provenance.cryptography`), because `importlib.metadata` reads files; numpy and scipy versions are module
  attributes. A test runs a crypto `simulate()` once to load every lazy import, then again with `builtins.open`,
  `io.open`, `os.open`, `socket.socket.connect` and `time.time` patched to raise, and gets the same report.
- **Q43 COST_DOMINATED flag (DRAFTER).** Besides the refusal of Q24, an amber flag when the headline no-edge column's
  average cost is at least `COST_DOMINATED_SHARE = 0.10` of the stake, with the figure printed.
- **Q44 IMPOSSIBLE (DRAFTER, spec 7.4).** Buy-and-hold KRX legs only: cap = (1 + l1)/(1 - l1) x prod over sessions
  2..n of (1 + li), with li the dated price limit of session i; IMPOSSIBLE when target_krw > stake_krw x cap. Then the
  card prints no probability for the target (spec 7.4 "and no probability"; spec 7.5 item 7, structural zeros worded
  as such): the headline P(target), the plain sentence, the target's spread and BELOW_RESOLUTION are replaced by
  `structural.impossible`, and every ladder rung above stake x cap renders `ladder.impossible`. The same suppression,
  with `structural.notrade`, applies when the headline column made no trade (`trades == 0`). Bracket legs are never
  flagged IMPOSSIBLE (decided in `simulate`, so its test lives in the columns task).
- **Q45 Precheck before any data (DRAFTER, O15).** `simulate.precheck(plan, ctx, n_paths)` runs the refusals up to and
  including LIMITS_UNSET (the start date, unsigned code and the OKX cap included). The CLI calls it before loading any
  bar, writing the state file or calling a seam, so a run against the real home before owner act 1 refuses
  STATE_UNUSABLE with no network call and no write.
- **Q46 Departures from spec text adopted on review (DRAFTER, for rev 3.3; accepted as plan decisions by
  RULINGS_ROUND2 R2-3 and listed in the plan header under "For spec rev 3.3").** Each makes a printed claim true where
  the spec's fixed text could be false, or makes a check stricter:
  1. HIDDEN_EDGE's resolution prints "1 in floor((T - L_min)/b)" (spec 7.5: ceil, which shows a smaller blind spot
     than the true one) and its pass sentence says it detects simulator drift only, not model error (`hidden.pass`).
  2. The plain sentence's "the bug checks are coarser than these ranges" prints only when true (Q32).
  3. The ceiling prints as a percentage from 1% (Q32), and without "that keeps this floor" on stop-based cards.
  4. The replay card's no-edge columns are a fair-sign two-point kernel on the replay's own block-resampled
     magnitudes, with a 2x cost column, CEILING_BREACH and HIDDEN_EDGE (Q38; spec 7.5 runs HIDDEN_EDGE "only on
     two-point bootstrap legs", and this column is one).
  5. Red flags render right after the plan head, before any number (section 10.4 render order).
  6. `compare.fresh` says the fresh-seed rerun belongs to execution and is not built yet (spec 7.5 "Before arming,
     the plan is re-run on a fresh market seed" is not implemented by this plan; the hand-off carries it to E2, the
     execution core that arms, RULINGS_ROUND2 R2-4).
  7. Withdrawn by RULINGS_ROUND2 R2-5: a replay leg needs only the signed Upbit lot and minimum, as spec 7.2 says
     (Q25); the number is kept so later references stay valid.
  8. MODEL_CHECK_FAILED, the start-date, unsigned-code and OKX-cap prechecks, and DATA_INVALID's `stale` and `empty`
     subs (Q24, Q39; `STALE_DAYS` accepted by R2-8) are new refusals.
  9. HIDDEN_EDGE on a bootstrap leg whose range fixed in advance is not finite (k_x >= 1, section 10.3) prints
     "unavailable for this plan (no finite range)" (`hidden.unbounded`); spec 7.5 names only GARCH-t as unavailable.
     Accepted as conservative (R2-7).

### 1.1 DIGEST design questions and the decision that answers each

| DQ | Answered by | DQ | Answered by | DQ | Answered by | DQ | Answered by |
|---|---|---|---|---|---|---|---|
| DQ1 | Q1 | DQ9 | Q11, Q27 | DQ17 | Q7 | DQ25 | Q13 |
| DQ2 | Q1, Q13 | DQ10 | Q1 (passed in) | DQ18 | Q13 | DQ26 | Q16 |
| DQ3 | Q13, Q40 | DQ11 | Q10 | DQ19 | Q13, Q14 | DQ27 | Q6 |
| DQ4 | Q3, Q6, Q19 | DQ12 | Q10, section 7.4 | DQ20 | Q2 | DQ28 | Q10, Q41 |
| DQ5 | Q3, Q20 | DQ13 | Q9 | DQ21 | Q8 | DQ29 | Q9, Q38 |
| DQ6 | Q5 | DQ14 | Q10, Q40 | DQ22 | Q12, Q36 | DQ30 | Q11, Q17, Q18 |
| DQ7 | Q11 | DQ15 | Q13, Q36 | DQ23 | Q4 | DQ31 | Q10 |
| DQ8 | Q3, Q17 | DQ16 | Q6, Q22, Q35 | DQ24 | Q3, Q21 | DQ32 | Q24 |

DIGEST open questions: 1 (KRW=X close instant) Q35; 2 (FX open print) Q6 and the card's FX line; 3 (KRW-USDT listing)
Q7, found from the data; 4 (owner rulings) O1, O5, O7, O8; 5 (numpy/scipy RECORDs) stays outside the hash, stated;
6 (`python -m` and T-CTX-01) `core.oddsdata` is not acting, the CLI lives there; 7 (injected CalendarSet) the core
never receives a CalendarSet, only dates, limits and hashes; 8 (macro store close times) not used (Q6 fixed
instants), though `CalendarSet` still reads `data/macro` for KRX Saturdays, stated as a limit; 13 not re-measured;
14 the odds tests use `fixture_set()` with its default config.

## 2. Files

| Path | Status | Line ends | Signed (D14) | Task(s) |
|---|---|---|---|---|
| `core/odds/__init__.py` | create, 0 bytes | - | yes | 1 |
| `core/odds/plan.py` | create | LF | yes | 5 |
| `core/odds/costs.py` | create | LF | yes | 6 |
| `core/odds/models.py` | create, extend | LF | yes | 7, 8, 17 |
| `core/odds/simulate.py` | create, extend | LF | yes | 9, 10, 13, 14, 17 |
| `core/odds/bold.py` | create | LF | yes | 11 |
| `core/odds/report.py` | create (ColumnStats, LADDER, COST_DOMINATED_SHARE only), extend | LF | yes | 9, 12 (O3-20) |
| `core/odds/venues.yaml` | modify | LF | data (venues approval) | 3 |
| `core/oddsdata/__init__.py` | create, 0 bytes | - | no | 1 |
| `core/oddsdata/bars.py` | create | LF | no | 15 |
| `core/oddsdata/inputs.py` | create | LF | no | 16 |
| `core/oddsdata/replay.py` | create | LF | no | 17 |
| `core/oddsdata/run.py` | create | LF | no | 18 |
| `core/compliance/rules.py` | modify | LF | yes | 2, 4 |
| `core/compliance/owner.py` | modify | LF | yes | 4 |
| `core/compliance/gate.py` | modify | LF | yes | 4 |
| `tests/odds_acceptance.py` | create | LF | - | 1 |
| `tests/odds_fixtures.py` | create, extend | LF | - | 1, 5, 9, 13, 14 (O3-20) |
| `tests/odds_guards.py` | create | LF | - | 1 |
| `tests/odds_simulate.py` | create, extend | LF | - | 9, 10, 17 (O3-20) |
| `tests/odds_pipeline.py` | create, extend | LF | - | 13, 14, 17 (O3-20) |
| `tests/odds_plan.py` ... `tests/odds_cli.py` (MODULES) | create | LF | - | 5 to 18 |
| `tests/compliance_tables.py` | modify | LF | - | 2, 3 |
| `tests/compliance_fixtures.py` | modify | LF | - | 4 |
| `tests/compliance_store.py` | modify | LF | - | 4 |
| `tests/compliance_gate.py` | modify (append) | LF | - | 4 |
| `tests/compliance_cli.py` | unchanged unless a calendar-line test needs an import fix | LF | - | 4 |
| `tests/run_all.py` | modify | CRLF | - | 1 |
| `README.md` | modify | CRLF | - | 1, 19 |
| `qa/acceptance_results.json` | modify (full run only) | CRLF | - | 19 |
| `docs/superpowers/plans/2026-10-24-odds-engine-execution-ledger.md` | create (untracked until Task 19) | LF | - | 1 (starts), every task (drift rulings), 19 (commits) |

`tests/fixtures/odds/` is not created. No file under `data/`, `core/quant/`, `core/calendars/`, `core/engine/`,
`config.py`, `docs/` (except this plan's execution ledger) or `tools/` changes, and no `tests/macro_*.py` file changes
(the odds twins of
`macro_m0_rules.test_every_state_path_stays_out_of_quantgen` live in `tests/odds_bars.py` and `tests/odds_inputs.py`,
so a broken `core.oddsdata` import never breaks the macro suite).

## 3. Test harness

### 3.1 `tests/odds_acceptance.py` (Task 1)
Copies `tests/compliance_acceptance.py` (same `tests()` and `_main` shape, same `__main__` block). Top-level imports:
`functools`, `importlib`, `os`, `sys`, `pathlib.Path`, `typing.Callable`, `from tests.macro_acceptance import hermetic`
and nothing that can fail (never `core.odds.*`, `core.oddsdata.*` or numpy at top level).
```python
TESTS = Path(__file__).resolve().parent
MODULES = ("odds_guards", "odds_plan", "odds_costs", "odds_models", "odds_garch", "odds_simulate", "odds_locks",
           "odds_bold", "odds_report", "odds_pipeline", "odds_columns", "odds_bars", "odds_inputs", "odds_replay",
           "odds_cli")
_REAL_HOMES = (Path.home() / ".tradegen" / "odds", Path.home() / ".tradegen" / "compliance")   # fixed at import
_REPO_FILES = ("core/odds/venues.yaml", "docs/asset_expansion/cache/upbit_KRW-BTC.csv",
               "docs/asset_expansion/cards/S_C3_crypto_trend_krwbtc.json", "docs/asset_expansion/results.csv")
SEAMS = ("_kis_daily", "_upbit_daily", "_binance_daily", "_yf_download")
REAL_SEAMS: dict[str, Callable] = {}    # the real seam functions, filled from vars(bars) the first time _wrap patches
def _real_listing() -> tuple            # (root index, relative path, size, mtime_ns) under every _REAL_HOMES entry
def _repo_listing() -> tuple            # (path, size, mtime_ns) of every _REPO_FILES entry
def _wrap(fn) -> Callable[[], None]
def tests() -> list[tuple[str, Callable[[], None]]]
def _main(argv: list[str]) -> int
```
`_wrap(fn)()`: takes both listings; runs `fn()` inside `with hermetic(), temp_home():` (temp_home from
`tests.compliance_fixtures`, imported inside); inside that block, when `TESTS.parent / "core/oddsdata/bars.py"` is a
file, imports `core.oddsdata.bars`, records each real SEAMS function in `REAL_SEAMS` (only when not yet recorded and
not `_boom`), and sets each SEAMS name to `tests.macro_acceptance._boom`, saving `vars(bars).get(name, _MISSING)`
first and restoring in reverse order in `finally` (delattr when it was missing). Afterwards it raises
`AssertionError("the test touched the real ~/.tradegen/odds or compliance: ...")` or `AssertionError("the test changed
a repo file it may only read: ...")` naming the first five differences. Fakes a test installs nest inside the raising
patch; restoring puts the raising stub back. A seam-body test (Task 15) installs a fake `sys.modules["yfinance"]` (or a
fake `data.krx.kis_client` / `data.crypto.crypto_client`) with save/restore and calls
`tests.odds_acceptance.REAL_SEAMS["_yf_download"](...)`; it never reloads `bars` (a reload would leave the seams
unpatched for the rest of the test).

### 3.2 `tests/odds_fixtures.py` (Task 1 creates; Tasks 5, 9, 13, 14 extend, O3-20). Not in MODULES. No `test_*` names.
```python
@contextlib.contextmanager
def chunk(n: int = 2_000) -> Iterator[None]        # swaps core.odds.simulate.CHUNK = n, DEFAULT_PATHS = {track: n for
    # each track} and GARCH_SUB = min(GARCH_SUB, n), restoring all three in finally; so a pipeline or CLI test that
    # passes no path count runs one small chunk (CLI tests also pass --paths 2000 explicitly)
@contextlib.contextmanager
def pilots(n: int = 2_000, nodes: int = 64) -> Iterator[None]   # swaps models.PILOT_PATHS, simulate.TILT_PILOT
    # and models.PILOT_NODES (save/restore); the GARCH pilot tests of Task 8 run without it, at 20,000 and 512
ODDS_VENUES: bytes                                  # Task 5: a complete fixture venues.yaml (kis, upbit, okx) with
    # every odds key: kis lot 1 for 005930/069500, min_order {KRW: 0, USD: 0}, fee_extras {phi_buy: 0, phi_sell: 0},
    # tick_ladder {KRX_stock_book: the KRX ladder}; kis US lot `default: 1` (fixture only); upbit lot {default: 1e-8},
    # min_order {KRW: 5000}, fee_extras 0/0; okx lot {default: 1e-8}, min_order {USDT: 1}, fee_extras 0/0. Every
    # source is "UNVERIFIED: owner to confirm before approval". It parses VALID against the shipped instrument map.
def venues_with(**changes) -> bytes                # Task 5: ODDS_VENUES with one venue's odds keys replaced
def series(*, symbol="KRW-BTC", source="UPBIT", n=600, seed=1, start=None, vol=0.02, open_gap=0.0,
           price=50_000_000.0, step_days=1) -> plan.Series      # Task 5: a synthetic random walk with md5 filled;
    # start=None (O3-6) ends the walk on 2026-10-22, the day before plan()'s start; an explicit start sets the first
    # date
def plan(**changes) -> plan.Plan                   # Task 5: default compounding upbit BTC buy-and-hold, stake 42,000,
    # target 42,000,000, fx 1,400.0, start 2026-10-23 (F.ctx's date), horizon 10, model bootstrap, fixed(1.0)
def odds_ctx(**overrides) -> model.Context         # Task 5: F.ctx(active=F.approved(venues=ODDS_VENUES),
    # equity_krw=42_000.0, owner limits {total_loss_floor_krw: 21_000.0, daily_loss_krw: 5_000.0}, cap 0.10)
def inputs(plan, series, **changes) -> plan.Inputs # Task 9: now 2026-10-23 09:00 KST, crypto sessions of the horizon,
    # no calendar, comparison "c000001", counter 1, k 1, j 0, plan_runs 1, provenance ("git:" + "0" * 40, "f" * 64,
    # "49.0.0")
def even_rows(m: float, n: int = 400) -> plan.Series   # Task 9: open = previous close and |ln(close/open)| = m
@contextlib.contextmanager
def calendar_signed(sha: str) -> Iterator[None]   # Task 13: swaps core.compliance.owner.calendar_in_force for
                                                  # `lambda now: sha` (save/restore); unit tests of later KRX steps only
# Task 13 also adds (O3-20): CAL_SHA, spy(target, name), owner_with(**changes), fresh_series(n=600, *, end=...),
#   weekdays(start, horizon_days), pipeline_inputs(plan_obj, series_obj, **changes), pipeline(...);
# Task 14 adds: members(*names) (swaps simulate.MEMBERS) and garch_series(n=600, *, seed=7, end=..., ...).
# Task 13 and Task 14 give the exact signatures.
```
Dates: every fixture built on `F.ctx` (date 2026-10-23) uses start 2026-10-23; every CLI plan file and every
`full_home` test runs at `F.NOW` (2026-10-24 09:00 KST, a Saturday, so the first KRX session is 2026-10-26) and uses
start `"2026-10-24"`, because `screen` refuses a start other than `ctx.date` and the `limit_set` and `cap_set` that
`full_home` stamps at 2026-10-23T00:00Z count only from 2026-10-24 (D12).

### 3.3 Compliance fixtures moved (Task 4, Q21)
Moved verbatim from `tests/compliance_store.py` (`TABLES` at :21 and the helpers `NOW` .. `_full_home` at :242-299,
as of 995534b) into `tests/compliance_fixtures.py`, renamed public:
```python
TABLES = ("rules", "instruments", "venues")
NOW = datetime.datetime(2026, 10, 24, 9, 0, tzinfo=model.KST)
HELD = model.Positions(equity_krw=1_000_000.0, holdings={("upbit", "BTC"): 0.01})
@contextlib.contextmanager
def pubkey_at(path: Path)                           # was _pubkey_at
def owner_key(home: Path)                           # was _owner_key
def sign(key, kind: str, data: dict, utc: str = "2026-10-23T00:00:00Z") -> tuple[int, str]   # was _sign
def approve(home: Path, key, kind: str, raw: bytes) -> str                                    # was _approve
def other_code(key, utc: str = "2026-10-23T00:00:00Z") -> None                                # was _other_code
def full_home(home: Path, *, rules_raw: bytes | None = None, venues_raw: bytes | None = None,
              calendar_raw: bytes | None = None, limits: dict | None = None, cap: float | None = None)   # was _full_home
```
`full_home` keeps the old behaviour by default and, when given, approves `venues_raw` instead of the shipped venues,
approves `calendar_raw` as kind `calendar` (a `rules.calendar_stream` blob), and signs `limit_set` (`limits`) and
`cap_set {key: okx_equity_share, value: cap}`, all stamped `2026-10-23T00:00:00Z` (so in force on NOW's date, D12).
`compliance_store.py` then reads `from tests.compliance_fixtures import NOW, HELD, TABLES` and binds `_pubkey_at =
F.pubkey_at` etc., so no test body changes. Never `from tests.compliance_fixtures import test_key`.

### 3.4 Budgets
Every simulate, pipeline and CLI test runs under `OF.chunk()` (2,000 paths per chunk, and `DEFAULT_PATHS` 2,000)
unless it tests CHUNK itself; pilots under `OF.pilots()` unless a pilot test needs 20,000 paths and 512 nodes. Exactly
one test (`odds_columns/test_full_chunk_runs_at_the_real_size`) runs one real 200,000-path chunk (a 7-day crypto
buy-and-hold), and one (`odds_columns/test_tilt_pilot_runs_at_the_real_chunk`) runs the 20,000-path tilt pilot with
the real CHUNK in force. The PARTIAL_CHUNK test runs at the real CHUNK and refuses before simulating. Per-module
targets: guards 5 s, plan 2 s, costs 2 s, models 6 s, garch 25 s, simulate 18 s, locks 12 s, bold 12 s, report 12 s,
pipeline 20 s, columns 30 s, bars 4 s, inputs 12 s, replay 20 s, cli 20 s (about 3.3 minutes in all, O13's "about 3
minutes"). Task 11's engine-run test runs one 20,000-path chunk (`OF.chunk(20_000)`, O3-9 T11-3). A module over its
target is recorded in the ledger with its measured time; no test is weakened or dropped to fit (RULINGS_ROUND3 G3-2).

## 4. Compliance-side prerequisites (Tasks 2-4)

### 4.1 `core/compliance/rules.py` venue keys (Task 2, Q17)
```python
_VENUE_OPTIONAL = frozenset({"markets", "quote_by_currency", "default_quote", "deposits",
                             "lot", "min_order", "fee_extras", "tick_ladder"})
_LADDER_BOOKS = frozenset({"KRX_stock_book", "US_shares_KIS", "crypto_venue"})   # KRX_ETF_line: instruments.py's
@dataclass(frozen=True, kw_only=True)
class Venue:                                     # existing fields unchanged, then:
    lot: tuple[tuple[str, float], ...] = ()      # sorted (symbol or "default", units step > 0)
    min_order: tuple[tuple[str, float], ...] = ()    # sorted (settlement asset, minimum in quote units >= 0)
    fee_extras: tuple[float, float] | None = None    # (phi_buy, phi_sell) in KRW, each >= 0; None = absent
    tick_ladder: tuple[tuple[str, str, tuple[tuple[float, float], ...]], ...] = ()
        # sorted (cost book, effective_from ISO date, ((price_from, tick), ...)) in the book's quote currency
    odds_sources: tuple[tuple[str, str], ...] = ()   # sorted (key, source) for each odds key present
    def lot_for(self, symbol: str) -> float | None          # the symbol's step, else "default", else None
    def min_order_for(self, quote: str) -> float | None
    def ladder_for(self, book: str) -> tuple[str, tuple[tuple[float, float], ...]] | None
```
Parser helpers (private, each raising `Invalid` naming `venues: <id>: <key>...`): `_odds_lot`, `_odds_min_order`,
`_check_extras` (the spec's check_extras), `_odds_ladder`, `_odds_number(value, where, *, positive: bool) -> float`
(finite, not bool; > 0 or >= 0). Rules: each key is a mapping with exactly its keys (`lot: {source, units}`,
`min_order: {source, quote}`, `fee_extras: {source, phi_buy, phi_sell}`, `tick_ladder: {source, effective_from,
books}`); `source` non-empty text; `units` keys are symbols listed in the venue's sections or the literal `default`;
`quote` keys are settlement assets of the venue; ladder rows `[price_from, tick]`, first `price_from` exactly 0,
strictly increasing, tick > 0; `effective_from` via `parse_date`; a ladder book in `_LADDER_BOOKS` and the cost book of
at least one instrument in the venue's sections. Exact refusal texts are fixed by Task 2's tests, e.g.
`venues: upbit: lot: units: 'btc' is not a symbol of sections ['crypto']`,
`venues: upbit: fee_extras: phi_sell: expected a finite number >= 0, got -1`,
`venues: kis: tick_ladder: books: KRX_ETF_line: its ladder is core/quant/instruments.py's`.
`tests/compliance_tables.py`: the `minimum_krw` line at :633 stays (an unknown key is still refused) and is joined by
one refusal line per rule above; a valid fixture with all four keys parses to the exact tuples; the gate's byte pins
(`tests/compliance_gate.py:336-340, :695-697, :998-1000`) and `test_shipped_venue_facts_p22` stay green unchanged.
`lot_for`, `min_order_for` and `ladder_for` are pure tuple lookups: no `parse_date` call, no file, clock or zone name,
no new import in `rules.py`, because `tests/compliance_gate.py::test_gate_call_graph_has_no_clock_zone_file_or_socket`
AST-scans the rules classes the gate reaches (`Venue` included) for the `_T9_FORBIDDEN` names, and
`test_purity_no_file_clock_zone_or_network` traps `rules.date`, `rules.Path` and `rules.os` during screen and decide.
Both stay green unchanged.

### 4.2 `core/odds/venues.yaml` (Task 3, Q18)
Added lines plus one comment edit (no `tag_required` text; `okx:` stays at two-space indent; the upbit `markets`
line keeps its exact flow form). The comment edit replaces, in header lines 2-3, exactly the clause "the odds plan
adds lots, minimums and ticks later, which changes this file's sha256 and needs a new approval." with "the odds plan
added the sourced lots, minimums and the KRX stock tick ladder; every other odds value is absent until the owner adds
it, so those legs are not tradable, and this file's sha256 changed, so it needs a new approval." Line 4 ("A venue
with no deposit entry for a coin credits none, so a withdrawal there fails closed.") stays unchanged. Under `kis:`
after `deposits: []` (L161 is the table row of KOSPI/KOSDAQ cash stocks, "1 share"; L163, the plain 1x ETF row, says
"1 unit", the same one-lot rule; the shipped-file test asserts both lines hold those words):
```yaml
    lot: {source: "research_notes/Korean resident trading venue legality/domestic_securities_derivatives.md#L161", units: {"005930": 1, "069500": 1}}
    min_order: {source: "research_notes/Korean resident trading venue legality/domestic_securities_derivatives.md#L161", quote: {KRW: 0}}
    tick_ladder:
      source: "https://global.krx.co.kr/contents/GLB/06/0602/0602010201/GLB0602010201T3.jsp"
      effective_from: "2026-10-02"
      books: {KRX_stock_book: [[0, 1], [2000, 5], [5000, 10], [20000, 50], [50000, 100], [200000, 500], [500000, 1000]]}
```
Under `upbit:` after its `deposits` block:
```yaml
    min_order: {source: "https://docs.upbit.com/kr/docs/krw-market-info", quote: {KRW: 5000}}
```
New shipped-file test in `tests/compliance_tables.py`: the parsed kis and upbit odds fields equal exactly these
tuples; every other venue has none; no venue has `fee_extras`; every odds source passes `_t5_ref_ok` or is the
UNVERIFIED literal; `test_shipped_urls_come_from_the_research` covers the two new URLs (both appear in the corpus:
`research_notes/.../crypto_domestic_and_overseas_verification.md:21` and the techfund `E2_nyse_microstructure_execution.md:316`).
Because `_t5_ref_ok` only checks that an `#L<n>` line exists, the test also asserts that line 161 of the cited file
starts with `| KOSPI/KOSDAQ cash stocks` and holds `| 1 share |`, and line 163 starts with `| Plain 1x ETF/ETN` and
holds `| 1 unit |`, so a wrong anchor fails.

### 4.3 `core/compliance/owner.py` (Task 4, Q19)
```python
def _calendar_approval(now: _dt.datetime) -> tuple[str, str]
    # ("log", "") owner state not OK at now (no key, cryptography missing, broken log, KEY CHANGED, unreadable);
    # ("none", "") no calendar approval stamped at or before now; ("store", sha) the stored copy is missing or altered;
    # ("ok", sha). Uses _owner_now(now.astimezone(model.KST).date(), model.iso_utc(now), None), then
    # in_force(_up_to(check, now_utc)).get("calendar", ("", 0))[0] and store_get("calendar", sha). Any exception other
    # than the ValueError below -> ("log", "").
def calendar_in_force(now: _dt.datetime) -> str | None
    # the sha when _calendar_approval(now)[0] == "ok", else None. ValueError for a non-datetime, naive or
    # out-of-range now (the same checks as load_context).
```
`rules._calendar_line(ctx, root, moment)` keeps `if not ctx.owner.ok: return "calendar: not checked (owner log not
usable)"`, then maps `owner._calendar_approval(moment)`: "log" -> the same not-checked line; "none" -> the
NO_CALENDAR line; "store" -> `f"calendar: the signed version {sha[:16]} is missing or altered in the store"`; "ok" ->
the existing draft comparison. Every `tests/compliance_cli.py` calendar assertion stays green unchanged. A test pins
`calendar_in_force(now) == sha` exactly when `_calendar_approval(now) == ("ok", sha)`, and None otherwise, on every
case of Task 4 (Q19's recorded departure from O3's wording).

### 4.4 `core/compliance/gate.py` (Task 4, Q20)
```python
def grey_rows(plan, ctx) -> tuple[str, ...]
    # sorted ids of rows r with r.treatment == "grey" in _in_force(state, intent, inst.cls, ctx.date), where state,
    # venue, inst and intent are built exactly as _screen builds them (quantity 1.0, notional 1.0); () when the context
    # is unsealed, owner not ok, state unusable, venue or symbol unknown, or on any exception. Never raises.
```
Tests appended to `tests/compliance_gate.py`: an OKX BTC leg gives `("KR-OKX-SPOT",)`; upbit BTC and kis 005930 give
`()`; an unsealed context and a broken owner give `()`; a malformed plan gives `()`. `grey_rows` adds no import to
`gate.py` (its imports must stay inside the fixed set of `test_gate_call_graph_has_no_clock_zone_file_or_socket`),
uses none of the `_T9_FORBIDDEN` names, and its docstring and comments never contain the words `datetime` or
`ZoneInfo` (that test asserts neither appears anywhere in `gate.py`'s source); that test and
`test_purity_no_file_clock_zone_or_network` stay green unchanged.

## 5. `core/odds/plan.py` (Task 5)

### 5.1 Constants
```python
REFUSALS = ("PARTIAL_CHUNK", "UNSUPPORTED_PRODUCT", "MULTI_LEG_UNSUPPORTED", "STATE_UNUSABLE", "LIMITS_UNSET",
            "CALENDAR_UNSIGNED", "CALENDAR_COVERAGE", "DATA_INVALID", "SYNTHETIC_REFUSED", "NOT_TRADABLE",
            "SPECIAL_REGIME", "SHORT_HISTORY", "CARD_NOT_REPRODUCED", "MODEL_NOT_FOR_LIMITED_VENUE", "COST_DOMINATED",
            "STUCK_AT_START", "SCREEN_BLOCKED", "ASSUMED_EDGE_UNREACHABLE", "MODEL_CHECK_FAILED")
            # the codes; their reporting order is Q24's numbered list (DATA_INVALID sub "now" comes before CALENDAR_*)
VENUES_OK = ("kis", "upbit", "okx")
CLASSES_OK = ("share", "etp_1x", "coin")
TRACKS = ("moonshot", "compounding")
MODELS = ("bootstrap", "garch_t")
SIZINGS = ("floor_safe", "stop_based")
REPLAY_SOURCE = "replay:S_C3_crypto_trend_krwbtc"
EDGE_SOURCES = ("none", "assumed", REPLAY_SOURCE)
FRACTION_KINDS = ("fixed", "kelly", "bold")
TAX_BASES_OK = ("krx_small_holder_exempt", "overseas_22pct_over_2.5m", "crypto_22pct_from_2027")
MAX_HORIZON_DAYS = 366
MIN_BARS = 250
SPECIAL_REGIME_BARS = 60
STALE_DAYS = {"CRYPTO": 3, "KR": 14, "US": 14}     # Q39: the last bar at most this many calendar days before start
LIMIT_KEYS = ("total_loss_floor_krw", "daily_loss_krw")
OKX_CAP_KEY = "okx_equity_share"
FEEDS = {("kis", "krx"): "kis_daily", ("kis", "us"): "yfinance", ("upbit", "crypto"): "upbit_daily",
         ("okx", "crypto"): "binance_x_upbit_usdt"}    # okx: symbol BTC only
MARKET = {("kis", "krx"): "KR", ("kis", "us"): "US", ("upbit", "crypto"): "CRYPTO", ("okx", "crypto"): "CRYPTO"}
```

### 5.2 Types (all `@dataclass(frozen=True, kw_only=True)`)
```python
class Bracket:  take_profit: float; stop: float
class Fraction: kind: str; value: float | None = None
def fixed(f: float) -> Fraction                      # Fraction(kind="fixed", value=float(f)) (validated by check_plan)
def kelly(c: float) -> Fraction
def bold() -> Fraction
class Leg:
    venue: str; symbol: str; model: str
    bracket: Bracket | None = None; sizing: str = "floor_safe"; edge_source: str = "none"; assumed_p: float | None = None
class Plan:
    name: str; track: str; stake_krw: float; target_krw: float; fx_krw_per_usd: float
    start: date; horizon_days: int; leg: Leg; fraction: Fraction
class Refusal:
    code: str                  # one of REFUSALS
    sub: str = ""              # a catalogue sub-reason key suffix (UNSUPPORTED_PRODUCT, SCREEN_BLOCKED) or ""
    slots: Mapping[str, str] = field(default_factory=dict)   # render slots: numbers, dates, symbols, row ids only
    detail: str = ""           # internal text for logs and tests; never rendered
class Series:
    symbol: str; source: str
    dates: tuple[str, ...]; open: tuple[float, ...]; close: tuple[float, ...]   # KRW
    adjustment: str; status: str; md5: str
    components: tuple[tuple[str, str], ...] = ()      # (label, md5) of each downloaded part (section 11.4)
    proxy_dates: tuple[str, str] | None = None        # first and last date priced through the FX fallback
class Provenance:  repo_anchor: str; tree_hash: str; cryptography: str   # the last via importlib.metadata in
                                                                           # oddsdata ("absent" when missing); the core
                                                                           # reads numpy/scipy __version__ itself (no I/O)
class ReplayInput:                                    # filled by core/oddsdata/replay.py (section 13)
    card_id: str; input_symbol: str; input_source: str
    input_dates: tuple[str, ...]; input_close: tuple[float, ...]
    oos_dates: tuple[str, ...]; oos_pnl: tuple[float, ...]; oos_turnover: tuple[float, ...]
    lookbacks: tuple[int, ...]; mas: tuple[int, ...]; grid: tuple[float, ...]
    cost_bps_per_side: float; embargo: int; n_trials: int; seed: int; domain: tuple[float, float]
    protocol: Mapping[str, float]; gate_protocol: Mapping[str, float]
    stats: Mapping[str, object]      # sr_oos, bench_sr, haircut_sr, bench_diff, bench_ci (2-tuple), decision,
                                     # chosen_last (hysteresis float), n_sessions, n_trades
    results_md5: str; card_md5: str
class Inputs:
    now: datetime                    # aware; the moment load_context saw
    series: Series
    sessions: tuple[str, ...]        # the horizon's session dates (each market's own date), ISO
    price_limits: tuple[float, ...]  # KRX: one per session; other legs: ()
    calendar_sha256: str             # KRX/US: rules.calendar_sha256 of the set used; crypto: ""
    calendar_version: str; calendar_md5s: tuple[tuple[str, str], ...]     # (file id, md5)
    calendar_error: str              # "" | "unsigned: <text>" | "coverage: <text>"
    replay: ReplayInput | None
    comparison_id: str; run_counter: int; comparison_plans: int; comparison_typed: int    # K and J, this plan included
        # run_counter: the comparison's own counter, fixed when begin_run created it (Q12, Q34)
    plan_runs: int                   # R: comparisons whose plans include this plan hash, this one included (Q12)
    provenance: Provenance
```

### 5.3 Functions
```python
def series_md5(symbol, source, dates, open_, close, adjustment, status) -> str
    # hashlib.md5(model.canonical_json({"symbol": symbol, "source": source, "dates": list(dates), "open": list(open_),
    #   "close": list(close), "adjustment": adjustment, "status": status}).encode("utf-8")).hexdigest()  (spec 7.2)
def plan_hash(plan: Plan) -> str     # model.sha256_hex(model.canonical_json(dataclasses.replace(plan, name="")))
def instrument(plan: Plan, ctx) -> tuple[rules.Venue | None, rules.Instrument | None]
    # (ctx.active.venues.venues.get(venue), ctx.active.instruments.lookup(venue.sections, symbol)) when ctx.active is
    # valid; else (None, None)
def section(plan: Plan, ctx) -> str | None     # the instrument's section ("krx" | "us" | "crypto")
def check_plan(plan, ctx) -> Refusal | None    # the product refusals of Q24, in this order:
    # leg a list or tuple: MULTI_LEG_UNSUPPORTED for two or more items; UNSUPPORTED_PRODUCT sub "file" when it is
    #   empty or an item is not a Leg; exactly one Leg: that leg is checked (RULINGS_ROUND3 O3-6);
    # types and ranges (Q25) -> UNSUPPORTED_PRODUCT sub "file" (name) | "track" | "numbers" | "start" (not a date, or
    #   start != ctx.date) | "horizon" | "model" | "sizing" | "fraction" | "bracket" | "edge" | "replay";
    # venue not in VENUES_OK -> sub "venue"; okx symbol != "BTC" -> sub "feed";
    # when ctx.active is valid: symbol not in the approved map for the venue's sections -> sub "symbol";
    #   inst.cls not in CLASSES_OK -> sub "class"; inst.multiple != 1.0 -> sub "multiple"; tax basis outside
    #   TAX_BASES_OK -> sub "tax"; garch_t with edge_source "assumed" -> sub "edge".
def check_state(plan, ctx) -> Refusal | None
    # STATE_UNUSABLE unless model.is_sealed(ctx) and ctx.owner.ok and ctx.active.valid (detail: the owner or active
    # reason); STATE_UNUSABLE sub "code" unless ctx.code_signed; LIMITS_UNSET unless set(LIMIT_KEYS) <=
    # set(ctx.owner.limits) (L = 0 is a set value); for an okx leg also LIMITS_UNSET (sub "cap") unless
    # ctx.owner.caps.get(OKX_CAP_KEY) is a finite number in (0, 1] (the gate's own `_cap` rule)
def check_data(plan, ctx, inputs, market: str) -> Refusal | None      # Q39 DATA_INVALID (subs "series", "stale",
    # "sessions", "empty"; sub "now" is checked by simulate before the calendar step, Q24), then SYNTHETIC_REFUSED
    # (series.status == "SYNTHETIC" or series.source == "SYNTHETIC")
def check_history(plan, inputs, market: str) -> Refusal | None      # for KR: fewer than SPECIAL_REGIME_BARS bars
    # -> SPECIAL_REGIME; then, every market, fewer than MIN_BARS bars -> SHORT_HISTORY. simulate calls check_data,
    # then costs.terms and costs.check_validity (NOT_TRADABLE), then check_history, so the order is O10's.
def check_now(ctx, now) -> Refusal | None      # DATA_INVALID sub "now" unless now is an aware datetime whose
    # Asia/Seoul date is ctx.date
```

## 6. `core/odds/costs.py` (Task 6)

### 6.1 Copied constants (each pinned by a test in `tests/odds_costs.py`)
```python
COMMISSION_BP = 1.4                       # == core.quant.instruments.COMMISSION_BP
TABLE_BP = {"KRX_ETF_line": 3.0, "KRX_stock_book": 35.0, "US_shares_KIS": 50.0, "crypto_venue": 10.0}
    # == validate.COST_BP_PER_SIDE[instruments.INSTRUMENT_BOOKS[book].cost_class] for each key
ETF_TICKS = ((date(2023, 12, 11), ((2000.0, 1.0), (math.inf, 5.0))),)   # == instruments.TICK_TABLES["KRX_ETF"]
SELL_TAX_BP = {2026: 20.0}                # == instruments.SELL_TAX_BP: the KRX stock sell tax in bp per year, added
                                          #    inside the tick floor on a sell (R2-1); a sell in a missing year raises
                                          #    NotTradable, as instruments._sell_tax_bp does
COST_STRESS = 2.0                         # == validate.GATE["cost_stress"]
LIMIT_DOWN_CARRY_COST_MULTIPLIER = 2.0    # == the module-level assign in core/engine/orders.py (ast.literal_eval;
                                          #    the test never imports orders)
DELIST_STRESS = (0.30, 1.00)              # == core.quant.tf_books.DELIST_STRESS
SCENARIOS = {"base": 1.0, "stress2x": COST_STRESS}
class NotTradable(ValueError)             # local; never the instruments class
```

### 6.2 Venue terms
```python
@dataclass(frozen=True, kw_only=True)
class Terms:
    venue: str; symbol: str; book: str; quote: str
    lot: float; min_quote: float; min_krw: float          # min_krw = min_quote x quote_krw
    phi_buy: float; phi_sell: float                       # KRW, base scenario
    ladder: tuple[tuple[float, float], ...] | None; ladder_from: date | None
    quote_krw: float                                      # 1.0 for KRW; plan.fx_krw_per_usd for USD, USDT, USDC
def terms(venue: rules.Venue, inst: rules.Instrument, fx_krw_per_usd: float, *, replay: bool = False) -> Terms
    # quote = venue.quote_for(inst); NotTradable (-> NOT_TRADABLE) when venue.lot_for(symbol) or
    # venue.min_order_for(quote) is None, when venue.fee_extras is None (unless replay), when inst.cost_book is not a
    # TABLE_BP key, or when the book is KRX_stock_book and venue.ladder_for("KRX_stock_book") is None.
    # replay=True (a replay leg, RULINGS_ROUND2 R2-5): fee_extras is never read and phi_buy = phi_sell = 0.0 (the
    # card's 10 bp already includes fees; Upbit has no fixed fee); lot and min_order are still required
```

### 6.3 Per-side rate
```python
def etf_tick(price: float, on: date) -> float          # instruments.tick_size("KRX_ETF", price, on), copied; NotTradable
def ladder_tick(ladder, price: float) -> float         # tick of the last row with price_from <= price
def tick_floor_bp(price: float, tick: float, *, commission_bp: float = COMMISSION_BP, tax_bp: float = 0.0) -> float
    # copied: ValueError unless price finite > 0 and tick finite >= 0; commission_bp + 0.5 * tick / price * 1e4 + tax_bp
def side_bp(terms: Terms, price: float, on: date, *, side: str) -> float     # side "buy" | "sell", else ValueError
    # KRX_ETF_line: max(3.0, tick_floor_bp(price, etf_tick(price, on)))  [== instruments.cost_per_side("KRX_ETF_line",
    #   price, on=on, side=side).bp; ETFs pay no sell tax, so both sides agree]
    # KRX_stock_book (O11 as amended by R2-1): NotTradable when on < ladder_from, or for a sell when on.year is not a
    #   SELL_TAX_BP key; tax = SELL_TAX_BP[on.year] if side == "sell" else 0.0;
    #   max(35.0, tick_floor_bp(price, ladder_tick(ladder, price), tax_bp=tax))  [== instruments.cost_per_side(
    #   "KRX_stock_book", price, on=on, side=side).bp with the venues ladder as its tick table, tested]
    # US_shares_KIS, crypto_venue: TABLE_BP[book] when terms.ladder is None, else max(table,
    #   tick_floor_bp(price / terms.quote_krw, ladder_tick(ladder, price / terms.quote_krw))); the same on both sides
def kappa(terms: Terms, prices: np.ndarray, on: date, mult: float, *, side: str) -> np.ndarray
    # side_bp x 1e-4 x mult, per path (mult is applied here, once); vectorised: the tick of each price comes from
    # np.searchsorted over the ladder (or ETF table) price bounds; equal to side_bp element by element on both sides
    # (tested). Entries use side "buy"; every exit, the liquidation value V and every exit bound use side "sell"
def check_validity(terms: Terms, dates: tuple[date, ...]) -> None
    # NotTradable (-> NOT_TRADABLE) when any date is before ETF_TICKS[0][0] (KRX_ETF_line), or before ladder_from or
    # in a year missing from SELL_TAX_BP (KRX_stock_book: every check can hold a sell, R2-1); the copy of the
    # original's date validity (O11); simulate runs it over every horizon session date before any path is drawn
def kappa_bound(terms: Terms, p_min: float, dates: tuple[date, ...], mult: float) -> float
    # the largest rate (x 1e-4 x mult) on either side at any price >= p_min on any of `dates`: within one ladder (or
    # ETF table) row the tick is fixed and the rate falls as the price rises, so it is the maximum, over both sides and
    # over the first date of each calendar year in `dates` (the sell tax changes only by year), of side_bp(p_min) and
    # side_bp(row start) for every row starting above p_min; the table rate for a book with no ladder. Used for
    # HIDDEN_EDGE's range (section 10.3).
```
Both sides pay the same rate except a KRX stock sell, whose tick floor holds that year's sell tax inside the max
(R2-1; it binds only below about 368 KRW, 367 KRW being the last whole price above 35 bp; a buy's floor binds below
about 149 KRW). No separate sell tax is ever added on top. The sell side is never below the buy side.

### 6.4 Bands (Q10, Q41)
```python
def band(ref: np.ndarray, limit: float, terms: Terms, on: date) -> tuple[np.ndarray, np.ndarray]
    # KRX legs: d = ref * (1 - limit), u = ref * (1 + limit); D = ceil(d / tick(d) - 1e-9) * tick(d),
    # U = floor(u / tick(u) + 1e-9) * tick(u), tick = etf_tick (KRX_ETF_line) or ladder_tick (KRX_stock_book) at that
    # edge's own value; then D = minimum(D, ref), U = maximum(U, ref). Other legs: (zeros, +inf).
```

### 6.5 Affordability and stakes (Q11, Q27, Q28)
```python
def r_exit(terms: Terms) -> float     # COST_STRESS * LIMIT_DOWN_CARRY_COST_MULTIPLIER * terms.phi_sell  (= 4 phi_sell)
def afford(cash, floor, p, *, terms, on, mult, sizing, stop) -> np.ndarray
    # kb = kappa(p, side="buy"), phib = mult * phi_buy, phis = mult * phi_sell, R = r_exit(terms)
    # always:      (cash - phib - R) / (1 + kb)
    # floor_safe:  min(always, (cash - floor - phib - R) / (1 + kb))
    # stop_based:  min(always, (cash - floor - phib - phis) / (stop + kb + ks * (1 - stop))),
    #              ks = kappa(p * (1 - stop), side="sell")
    # clipped at 0 (every kappa here at `on` with `mult`)
def floor_units(stake, p, lot) -> np.ndarray   # np.floor(stake / (p * lot) + 1e-9) * lot
def ceil_units(stake, p, lot) -> np.ndarray    # np.ceil(stake / (p * lot) - 1e-9) * lot
def min_units(p, terms) -> np.ndarray          # ceil_units(max(terms.min_krw, terms.lot * p), p, lot): smallest bet
def rule_units(fraction, cash, p, *, terms, on, mult, target, w0, take_profit, stop, sizing, floor, fstar, cap_krw)
    -> tuple[np.ndarray, np.ndarray]            # (units to buy, at_floor mask)
    # a = afford(...), capped at cap_krw (OKX only); m = min_units(p) * p; at_floor = a < m
    # fixed(f): s = min(f * cash, a); kelly(c): s = min(c * fstar * cash, a)
    # bold: c_w = take_profit - kw * (2 + take_profit),
    #   kw = max(kappa(p, side="buy"), kappa(p * (1 + take_profit), side="sell"));
    #   s_reach = (target - cash + phib + phis) / c_w; s = min(ceil_units(max(s_reach, m)) * p, floor_units(a) * p);
    #   no bet where c_w <= 0 or cash >= target
    # units = floor_units(s); no bet (units 0) where units * p < m; at_floor rows buy nothing
def net_win_coefficient(terms, p0, on, take_profit, mult) -> float    # take_profit - kw * (2 + take_profit), kw as
    # in bold above at p0 (buy at p0, sell at p0 (1 + take_profit))
def first_stake(plan, terms, ctx, p0, on, *, fstar: float | None = None) -> float
    # the base-scenario rule stake at W0 = plan.stake_krw and p0 (the series' last close), with L =
    # ctx.owner.limits["total_loss_floor_krw"] and, for an okx leg, cap_krw = ctx.owner.caps.get(OKX_CAP_KEY) x W0
    # (check_state has already refused a missing cap; `.get` keeps a direct caller from a KeyError), as units * p0;
    # 0.0 when no bet or at_floor; the value screen() receives (as float) when > 0. Kelly legs pass the replay's f*;
    # replay legs pass the zero-charge terms of terms(..., replay=True) and mult 0.0 (Q38, R2-5).
def cost_refusal(plan, terms, p0, on) -> str | None   # "4kappa" when 4 * kappa(p0, mult 1, side="sell") >= 1 (the sell
    # side is never below the buy side); "bold" when a bold plan's net_win_coefficient <= 0 under base or stress2x;
    # else None  (both -> COST_DOMINATED)
```

## 7. `core/odds/models.py` (Tasks 7, 8, 17)

### 7.1 Copied constants and pieces
```python
LIVE_SHARPE_MULTIPLIER = 0.60          # == core.quant.gate_stats.LIVE_SHARPE_MULTIPLIER
Z_BOUND = 22                           # == core.quant.garch.Z_BOUND
TRADING_DAYS = 252                     # == core.quant.garch.TRADING_DAYS == core.quant.validate.TRADING_DAYS
NU_NORMAL = 100.0                      # == garch.NU_NORMAL
def _optimal_block_length(x) -> tuple[float, float]   # copy of gate_stats.optimal_block_length (bit-exact)
def pw_block(x) -> float               # == gate_stats.pw_block(x, kind="stationary") on a grid of series
def sharpe(daily) -> float             # copy of validate.sharpe
```

### 7.2 The two-point bootstrap (Task 7)
```python
def rows(series: plan.Series) -> tuple[np.ndarray, np.ndarray, np.ndarray]
    # (m_o, m_i, r) for t = 1..n-1: m_o = |ln(open_t / close_{t-1})|, m_i = |ln(close_t / open_t)|,
    # r = ln(close_t / close_{t-1})
def block_length(r: np.ndarray) -> float               # max(1.0, pw_block(r), pw_block(r * r))
def variant_block(b: float, mult: float, n_rows: int) -> float
    # float(min(max(1, math.floor(mult * b + 0.5)), n_rows))   (half up: b = 5, mult 0.5 gives 3; never round())
def indices(rng: np.random.Generator, n_rows: int, n_paths: int, block: float)  -> Iterator[np.ndarray]
    # an endless generator; step 0: rng.integers(0, n_rows, n_paths); each later step: restart = rng.random(n_paths)
    # < 1 / block, fresh = rng.integers(0, n_rows, n_paths) (both always drawn, in this order), then
    # where(restart, fresh, (prev + 1) % n_rows). Mean block exactly `block` (Politis-Romano).
def tilt(q: np.ndarray, theta: float) -> np.ndarray     # q e^theta / (q e^theta + 1 - q); theta 0 returns q
def kernel(p, m, d_edge, u_edge, u, theta: float = 0.0) -> np.ndarray
    # x_u = min(p e^m, U), x_d = max(p e^-m, D); q = (p - x_d) / (x_u - x_d) where x_u > x_d, else 0 (x_u = x_d = p);
    # next = where(u < tilt(q, theta), x_u, x_d). With theta 0: q x_u + (1 - q) x_d == p to 1e-12 relative.
STREAMS = {"index": 1, "sign": 2, "garch": 3, "pilot": 4, "tilt": 5, "kelly": 6, "refit": 7, "replay": 8,
           "refit_series": 9, "replay_sign": 10}
SEED_TAG = b"tradegen-odds/seed/1\x00"
def data_hashes(series: plan.Series, replay: plan.ReplayInput | None) -> tuple[str, ...]
    # (series.md5, every component md5) plus, for a replay leg, the pinned input md5 and pnl md5; sorted
def market_seed(data_hashes, calendar_digest: str, comparison_id: str, run_counter: int) -> bytes   # Q34, 32 bytes
def seed_sequence(seed: bytes, chunk: int, name: str, *extra: int) -> np.random.SeedSequence
    # np.random.SeedSequence(int.from_bytes(seed, "big"), spawn_key=(chunk, STREAMS[name], *extra))
def stream(seed: bytes, chunk: int, name: str, *extra: int) -> np.random.Generator
    # np.random.default_rng(seed_sequence(...)) (PCG64); default_rng passes a SeedSequence through, so the copied
    # GARCH code, which calls default_rng(seed), takes seed_sequence(...) directly
```

### 7.3 GARCH-t copy (Task 8)
```python
@dataclass(frozen=True)
class GarchParams:
    dist: str; omega: float; alpha: float; beta: float; nu: float; mean_daily: float; n_obs: int
    cond_vol_last: float; converged: bool; at_bound: tuple[str, ...]
def fit_garch_t(returns: np.ndarray) -> GarchParams
    # the copied _variance_path, _t_const, _loglik, _fit, _fit_t, _half_life path of garch.fit_garch(returns,
    # dist="t", profile=False), without _covariance and the note; equality test: every GarchParams field equals the
    # GarchFit field of garch.fit_garch(r, profile=False) exactly. ValueError under 100 observations (copied _MIN_OBS).
def t_density(z, nu) ; _t_scale(nu) ; _draw_z(rng, nu, dist, size, bound=Z_BOUND) ; _log_mgf(sig, z, wt)
@lru_cache(maxsize=32)
def _correction_table(nu: float, bound: float)          # copied; martingale_correction looks it up at call time
def martingale_correction(sigma_daily, nu, dist, bound=Z_BOUND) -> np.ndarray   # copied
def simulate_garch(fit: GarchParams, *, n_paths: int, horizon: int, seed) -> tuple[np.ndarray, np.ndarray]
    # the copied simulate_returns body with rate_daily=0.0 and bound=Z_BOUND, also returning sigma (n_paths, horizon);
    # ret equals garch.simulate_returns(<GarchFit of the same fit>, n_paths=..., horizon=..., seed=same SeedSequence,
    # rate_daily=0.0, bound=garch.Z_BOUND)[0] exactly
def simulate_garch_series(omega, alpha, beta, nu, *, n: int, seed, dist: str = "t") -> np.ndarray   # copied
```

### 7.4 GARCH pilot checks (Task 8, Q10)
```python
PILOT_PATHS = 20_000; PILOT_NODES = 512; PILOT_STEP_TOL = 1e-7; PILOT_SUM_TOL = 1e-6; PILOT_SE = 4.0
def c_quad(sigma: float, nu: float, bound: float = Z_BOUND) -> float
    # ln(sum of quad(exp(sigma z) t_density(z, nu)) / sum of quad(t_density(z, nu))) over the panels (-bound, -1),
    # (-1, 1), (1, bound), limit=400; for dist normal or nu > NU_NORMAL: sigma ** 2 / 2
def pilot_checks(fit: GarchParams, horizon: int, seed: bytes) -> tuple[bool, str]
    # pilot = simulate_garch(fit, n_paths=PILOT_PATHS, horizon, seed=seed_sequence(seed, 0, "pilot"));
    # check 1: nodes = unique(quantile(sigma.ravel(), linspace(0, 1, PILOT_NODES))); err = |c_quad - table| per node;
    #   each pilot sigma takes its nearest node's err; fail "deterministic" when max |expm1(c_quad - c_table)| >
    #   PILOT_STEP_TOL or max over paths of the summed err over the horizon > PILOT_SUM_TOL;
    # check 2: e = exp(cumsum(ret, axis=1)); for every step h: |mean(e[:, h]) - 1| <= PILOT_SE * std(e[:, h], ddof=1) /
    #   sqrt(PILOT_PATHS), else fail "statistical". Returns (True, "") or (False, "deterministic" | "statistical").
```
Corruption test (magnitudes sized to what each check can see; the ratio column holds c / sigma^2, so adding a
constant to the ratio moves c by only that constant x sigma^2, about 1e-10 per step at sigma 0.01, which no check can
see): replace `core.odds.models._correction_table` with a wrapper that returns the ratio column plus `2e-6 /
grid ** 2` (c + 2e-6 at every node), clear the lru cache, assert check 1 fails with "deterministic" (measured: max
|expm1| 2.0e-6 > 1e-7 on the fixture fit at 30 and 90 steps); a wrapper returning the ratio x 3 fails check 2 with
"statistical" at 90 steps (measured max z 13.9 at 90 steps and 7.4 at 30, on the 20,000-path pilot of the fixture fit
`garch.simulate_garch_series(2e-6, 0.08, 0.90, 6.0, n=1500, seed=1)`); restore in `finally`. Zero LOG drift
(`drift_daily=0.0`) is asserted to fail check 2 at 90 steps only (measured z 6.2 at 90 and 3.8 at 30, which passes).
These margins were measured on sandbox streams. RULINGS_ROUND2 R2-9: the implementer confirms each one on the real
"pilot" stream (the draws `pilot_checks` makes from `seed_sequence(seed, 0, "pilot")` with the test's fixed seed; the
zero-drift returns come from `garch.simulate_returns` on that same SeedSequence) and records the measured values in
the execution ledger. If a corrupted run's check-2 z falls under 4 SE (`PILOT_SE`), the implementer raises that
corruption's factor (the ratio multiplier above 3; for the zero-drift control, a constant log drift `drift_daily = d`
with d > 0 in place of 0) and records the new factor; it never lowers `PILOT_SE`, `PILOT_STEP_TOL` or
`PILOT_SUM_TOL` and never drops a corruption assertion.
The clean table passes both (check 1 step 4.9e-12, check 2 max z 2.4 at 30 and 1.9 at 90). Quad costs about 1.5 to
6 ms per sigma node, so one 512-node check 1 takes about 1 to 3 s.

### 7.5 D13 pins, verification, Kelly (Task 17)
```python
CARD_ID = "S_C3_crypto_trend_krwbtc"
REPLAY_PINS = {
    "input_symbol": "KRW-BTC", "input_source": "UPBIT", "n_input": 3288,
    "input_first": "2017-09-25", "input_last": "2026-09-25",
    "input_md5": "18ec83bdfe158efe4d648caf45ff849f",   # md5 of canonical_json({"symbol", "source", "dates", "close"})
    "lookbacks": (7, 14, 21, 28), "mas": (10, 20, 50, 100, 200), "grid": (0.0, 0.222, 0.444, 0.667, 0.889),
    "cost_bps_per_side": 10.0, "embargo": 1, "n_trials": 11, "seed": 11, "domain": (0.0, 0.889),
    "protocol": {"w_is": 756, "w_oos": 126, "min_is": 504, "ci_level": 0.9, "bootstrap_B": 2000, "block": 10},
    "n_oos": 2530, "oos_first": "2019-10-23", "oos_last": "2026-09-25",
    "pnl_md5": "bbdcf17ca9462567fe351c54644bef0c",     # md5 of np.ascontiguousarray(oos_pnl, dtype="<f8").tobytes()
    "turnover_md5": "2d4edeb2f042c87fd1750d9c68e275f7",   # the same bytes md5 of oos_turnover (values 0 or 1)
    "results_md5": "ca757e25f508b588cb2f361719ec83cd", "card_md5": "40b1e7bfadf6d16246e0012495064704",
    "sr_oos": 1.216, "sr_tol": 0.02, "decision": "PASS", "chosen_last": 0.667,
    "bench_sr": 0.788830441182887, "bench_diff": 0.4271945783845257,
    "bench_ci": (0.03344352887529298, 0.8346050647267628), "haircut_sr": 0.7296150117404476,
    "n_trades": 138, "n_sessions": 2530}                # the card's own stats (docs/asset_expansion/cards/S_C3_...json)
def verify_replay(rep: plan.ReplayInput) -> str | None
    # None when reproduced; else the first failing item's name, checked in this order: card_id, inputs (input symbol,
    # source, count, first and last date, lookbacks, mas, grid, cost, embargo, n_trials, seed, domain, protocol ==
    # gate_protocol == pinned), digests (input md5 recomputed from input_dates/input_close, pnl md5 recomputed from
    # oos_pnl, turnover md5 recomputed from oos_turnover, results_md5, card_md5), shape (n_oos, first/last OOS date,
    # len(oos_turnover) == len(oos_pnl)), stats (sharpe(oos_pnl) == stats["sr_oos"] and |stats["sr_oos"] - 1.216| <=
    # 0.02, decision PASS, chosen_last 0.667, haircut_sr == LIVE_SHARPE_MULTIPLIER * sr_oos within 1e-12; bench_sr,
    # bench_diff, bench_ci, haircut_sr, n_trades and n_sessions EXACTLY equal to the pins; and bench_sr recomputed in
    # the core: b_t = close_t / close_{t-1} - 1 over consecutive input dates, taken on oos_dates, sharpe(b) ==
    # pins["bench_sr"] exactly, measured equal). results_md5 and card_md5 are md5s of file bytes that unsigned code
    # read: the core compares them with the pins but cannot see the bytes (stated in `limits.injected`).
KELLY_B = 2_000; KELLY_BLOCK = 10.0; KELLY_Q = 0.05
def mu_lb(r: np.ndarray, rng: np.random.Generator) -> float
    # B = KELLY_B rows of indices(rng, len(r), KELLY_B, KELLY_BLOCK) taken for len(r) steps; the 5th percentile
    # (np.quantile(..., 0.05)) of the B resampled means
def kelly_fstar(r: np.ndarray, lb: float) -> float
    # 0.0 when lb <= 0; rc = r - mean(r) + LIVE_SHARPE_MULTIPLIER * lb; g'(f) = mean(rc / (1 + f rc));
    # f_hi = 1.0 if min(rc) > -1 else 0.999 / max(-rc); f* = f_hi when g'(f_hi) >= 0; else 60 bisection steps of g'
    # on [0, f_hi]; the result is always in [0, 1]
def replay_returns(rep) -> tuple[np.ndarray, np.ndarray, np.ndarray]
    # (a, c, R1), Q38: c = cost_bps_per_side * 1e-4 * oos_turnover; G = oos_pnl + c; a = |G - mean(G)| (the no-edge
    # magnitudes, signed by the replay_sign stream); R1 = oos_pnl - mean(oos_pnl) + LIVE_SHARPE_MULTIPLIER *
    # mean(oos_pnl). ValueError unless max(a) + 2 * max(c) < 1 (so the stress2x sleeve never goes below 0).
def block_growth(r: np.ndarray, block: float, h: int) -> float
    # exact E[prod over h steps of (1 + r[I_t])] under the stationary bootstrap of models.indices (I_0 uniform; each
    # later step continues to (I + 1) mod n with probability 1 - 1/block, else restarts uniformly): v = 1 + r; repeat
    # h - 1 times: v = (1 + r) * ((1 - 1/block) * np.roll(v, -1) + (1/block) * v.mean()); return v.mean(). O(h n).
    # On the real R1 at h 30 and block 10: 1.029918 (a Monte Carlo of 200,000 paths gives 1.02967 +/- 0.00031).
```

## 8. `core/odds/simulate.py` (Tasks 9, 10, 13, 14, 17)

### 8.1 Constants
```python
CHUNK = 200_000
DEFAULT_PATHS = {"moonshot": 1_000_000, "compounding": 200_000}
GARCH_SUB = 20_000
REFIT_B = 20
TILT_PILOT = 20_000; TILT_BOUND = 8.0; TILT_ITER = 30; TILT_TOL = 0.002; TILT_FAIL = 0.01
BRACKET_SAMPLE = 50_000
MEMBERS = ("bootstrap", "bootstrap_half", "bootstrap_double", "garch_t", "garch_refit")
# LADDER and COST_DOMINATED_SHARE live in report.py (section 10.1); simulate reads report.LADDER and
# report.COST_DOMINATED_SHARE, because simulate imports report and never the reverse.
```

### 8.2 Engine input and output
```python
@dataclass(frozen=True, kw_only=True)
class Checks:
    session: np.ndarray           # int, session index of each check
    close: np.ndarray             # bool, True at a close check
    seoul: tuple[date, ...]       # Asia/Seoul date of each check (Q22)
    on: tuple[date, ...]          # the session's own date (cost quotes)
def checks(market: str, sessions: tuple[date, ...], close_only: bool) -> Checks
@dataclass(frozen=True, kw_only=True)
class PathSpec:
    track: str; w0: float; target: float; floor: float; daily_loss: float; p0: float
    engine: str                   # "bootstrap" | "garch" | "replay"
    m_o: np.ndarray | None; m_i: np.ndarray | None; block: float          # bootstrap rows and mean block
    fits: tuple[models.GarchParams, ...] = ()                             # 1 fit, or REFIT_B refits
    replay_move: np.ndarray | None = None         # replay: a = |g| (no-edge, signed by replay_sign) or R1 (tested)
    replay_cost: np.ndarray | None = None         # replay no-edge: c per OOS day (x 2 on stress2x); tested: None
    checks: Checks; limits: np.ndarray            # per session; nan = no band
    terms: costs.Terms; mult: float               # 1.0 base, 2.0 stress
    bracket: plan.Bracket | None; sizing: str; fraction: plan.Fraction; fstar: float | None
    cap_krw: float | None                         # OKX per-entry cap, else None
    stop_entries_from: date | None; force_exit_from: date | None          # Q5
    delist_h: float | None; theta: float = 0.0; record_brackets: bool = False
# ColumnStats is report.ColumnStats (section 10.1): simulate imports report, never the reverse.
def run_column(spec: PathSpec, *, n: int, seed: bytes, key: str, member: str, scenario: str) -> report.ColumnStats
    # n must be a positive multiple of CHUNK (ValueError otherwise; simulate() refuses first); runs
    # _run_paths(spec, n=CHUNK, chunk=c, seed=seed) for c in range(n // CHUNK) and merges the chunks into ColumnStats
def _run_paths(spec: PathSpec, *, n: int, chunk: int, seed: bytes)        # private; any n >= 1
    # the state machine of 8.4 over n paths of chunk index `chunk`; returns the per-path arrays ColumnStats needs.
    # Draws: stream(seed, chunk, "index") and stream(seed, chunk, "sign") (bootstrap); stream(seed, chunk, "garch",
    # start // GARCH_SUB) for each slice start in range(0, n, GARCH_SUB) (garch, one fit); stream(seed, chunk,
    # "refit", g) for refit group g (garch, REFIT_B fits, n // REFIT_B paths each; n a multiple of REFIT_B); the last
    # GARCH slice holds n - start paths when shorter; stream(seed, chunk, "replay") and stream(seed, chunk,
    # "replay_sign") (replay). The tilt pilot calls it directly with n = TILT_PILOT, which need not be a multiple of
    # CHUNK (the GARCH pilot is models.pilot_checks and never runs the engine).
```

### 8.3 Per-check move
- bootstrap: at the open check of session s, `idx` advances one step of `models.indices` (step 0 at s = 0); the move
  uses `m_o[idx]` at the open and `m_i[idx]` at the close; `u = sign_rng.random(P)` at every check;
  `p = models.kernel(p, m, D, U, u, spec.theta)`. At each open check the band is `costs.band(ref, limit_s, terms,
  on_s)` with `ref` = the previous check's price (the previous close; p0 for session 0); between the open and the close
  of a session the band stays. Non-KRX legs: D = 0, U = inf.
- garch: one close check per session, `p = p * exp(ret[:, s])`, no band.
- replay: one close check per day; idx advances one step of `models.indices(stream(seed, c, "replay"),
  len(replay_move), P, 10.0)` per day. On the no-edge columns, `eps = where(stream(seed, c, "replay_sign").random(P)
  < 0.5, 1.0, -1.0)` is drawn at every check and a held sleeve becomes `sleeve * (1 + eps * replay_move[idx] -
  replay_cost[idx])`, with `replay_cost[idx] * sleeve` (of the sleeve before the move) booked as cost; on the tested
  column it becomes `sleeve * (1 + replay_move[idx])`.

### 8.4 State machine (per path, vectorised; Q26, Q27)
State: `cash`, `units`, `entry`, `tp`, `sl` (bracket prices), `locked` (bool), `d_lock` (the D of the session where
the lock started; 0 when unlocked), `costs` (booked KRW), `done`,
`outcome` (0 running, 1 reached, 2 at_floor), `entered` (ever), `fp` (first passage seen), `x_set`, `x`,
`day_stop`, `day_ref` (W0 at start), `delisted`, `after_entry` (the check index of the first entry fill).
At each check j (Seoul date `d_j`; `filled = False` for every path at the start of the check):
1. Move the price (8.3). If `d_j` differs from the previous check's date: `day_ref = V_prev` (each path's liquidation
   value at the end of the previous check), `day_stop = False`.
2. `chi = 2 where locked else 1`; `ks = costs.kappa(terms, p, on_j, mult, side="sell")` (`on_j = checks.on[j]`;
   mult is applied inside kappa, once); `V = cash + units * p * max(0, 1 - ks * chi) - phi_sell * mult * chi *
   (units > 0)`.
3. First passage: `new = ~done & ~fp & (V >= T)`; `fp |= new`; where `new & ~x_set`: `x = cash + units * p + costs -
   W0`, `x_set = True`.
4. Exits, for `~done & (units > 0)`; a new trigger is executable when `p > D` (the current session's D; D = 0 for
   non-KRX), a queued exit only when `p > d_lock` (spec 7.2: "the first check strictly above that session's D"; so
   after a close locked at D_s, a next open in (D_{s+1}, D_s] keeps the lock although it is above the new D):
   - queued: `locked & (p > d_lock)` -> fill at p with chi = 2, then `locked = False`, `d_lock = 0` (unresolved; a
     moonshot path is REACHED when the cash after it is >= T);
   - delisting (delist columns): `j == after_entry + 1` -> sale at p (1 - h) (Q29), `delisted = True`;
   - new triggers on unlocked longs, at every check (the last included), in priority order: target (moonshot and
     V >= T), take-profit (p >= tp), stop (p <= sl), daily loss (day_ref - V >= daily_loss; also sets `day_stop`),
     rule (d_j >= force_exit_from); the first that holds names the exit;
   - a triggered exit fills at p when executable (chi = 1), else `locked = True`, `d_lock = D` and no fill (the lock
     reason is recorded; it counts as unresolved);
   - a fill: `charge = units * p * min(1, ks * chi) + phi_sell * mult * chi`; `cash += units * p - charge`;
     `costs += charge`; `units = 0`; `filled = True` for this check; take-profit and stop fills count as wins and
     losses only when not locked; `worst_gap = max(worst_gap, (sl - p) / entry)` for stop fills below the stop.
   - after the fills: `cash >= T` on a moonshot path -> outcome reached, done; `cash <= floor` -> outcome at_floor,
     done (stop-based overshoot kept); both set `x` when not yet set.
5. Entries, for `~done & (units == 0) & ~locked & ~filled & ~day_stop & ~delisted & (j < last)` and `d_j <
   stop_entries_from` (when set), and (bracket legs, or not `entered`): `costs.rule_units(...)` at p with W = cash;
   `at_floor` rows -> outcome at_floor, done, `x` set; rows with units > 0 buy at p:
   `charge = units * p * kb + phi_buy * mult` with `kb = costs.kappa(terms, p, on_j, mult, side="buy")`;
   `cash -= units * p + charge`; `costs += charge`; `entry = p`;
   `tp = p (1 + take_profit)`, `sl = p (1 - stop)`; `entered = True`; `after_entry = j` on the first entry.
6. `V_prev = V` recomputed after the fills and entries.
At the horizon: live paths are running at V (locked ones valued with chi = 2: LOCKED_AT_HORIZON); `x` is set from
`cash + units * p + costs - W0` where still unset; terminal costs add the liquidation charge of open positions.
The replay engine uses steps 1-6 with the sleeve in place of `units * p`, no kappa and no phi.

### 8.5 The pipeline
```python
def precheck(plan, ctx, n_paths: int | None = None) -> plan.Refusal | None
    # PARTIAL_CHUNK (n_paths given and not a positive multiple of CHUNK), check_plan (start == ctx.date included),
    # check_state(plan, ctx) (unsigned code and the OKX cap included) (Q24, Q45)
def simulate(plan, ctx, inputs: plan.Inputs, *, n_paths: int | None = None) -> report.OddsReport
    # 1. precheck;
    # 2. plan.check_now(ctx, inputs.now) -> DATA_INVALID sub "now"; then KRX/US: inputs.calendar_error "coverage: ..."
    #    -> CALENDAR_COVERAGE, else CALENDAR_UNSIGNED unless sha = owner.calendar_in_force(inputs.now) is a str equal
    #    to inputs.calendar_sha256 and calendar_error == "";
    # 3. check_data (DATA_INVALID, SYNTHETIC_REFUSED); costs.terms (replay=True for a replay leg, R2-5) and
    #    costs.check_validity over the horizon session dates (costs.NotTradable -> NOT_TRADABLE); check_history
    #    (SPECIAL_REGIME, SHORT_HISTORY); replay legs:
    #    verify_replay -> CARD_NOT_REPRODUCED (until the replay task lands, every replay leg is refused
    #    CARD_NOT_REPRODUCED with detail "replay not built yet");
    # 4. garch_t on a KRX leg -> MODEL_NOT_FOR_LIMITED_VENUE; 5. costs.cost_refusal -> COST_DOMINATED; first stake <= 0
    #    -> STUCK_AT_START; 6. screening = gate.screen(plan, ctx, float(first)); not screening.allowed -> SCREEN_BLOCKED
    #    (sub from reasons[0]); 7. seed = market_seed(data_hashes(series, replay), inputs.calendar_sha256,
    #    inputs.comparison_id, inputs.run_counter); stop_entries_from = the earliest date of screening.flags (any
    #    field), force_exit_from = the earliest auto_off or effective_until flag date (None when absent);
    #    l_min = L when leg.sizing == "floor_safe" else 0.0 (Q32); the GARCH fits and pilots (a failed headline ->
    #    MODEL_CHECK_FAILED); columns (Q29-Q31, Q38); the tilt pilot (ASSUMED_EDGE_UNREACHABLE); report.build(...).
    # n = n_paths or DEFAULT_PATHS[plan.track]. Returns a refused OddsReport for every refusal; raises only on bugs.
```
Columns built by `simulate`: `no_edge/<member>/base` and `no_edge/<member>/stress2x` for each member run; for share
and coin legs `delist_30` and `delist_100` (headline member, base); for assumed legs `assumed` (headline bootstrap,
base, theta from the pilot); for replay legs `replay_no_edge/base`, `replay_no_edge/stress2x` and `tested_replay/base`
only (no spread, no delisting). Headline = `no_edge/<leg.model or "bootstrap">/base`, and `replay_no_edge/base` for
replay legs. HIDDEN_EDGE runs on the headline when it is a bootstrap or replay no-edge column (Q32); CEILING_BREACH
covers every `no_edge/*` and `replay_no_edge/*` cell.

## 9. `core/odds/bold.py` (Task 11)
```python
def ceiling(w0: float, l_min: float, target: float) -> float        # (w0 - l_min) / (target - l_min)
def ceiling_one_in(w0, l_min, target) -> int                         # floor((target - l_min) / (w0 - l_min)); the
    # "1 in N" of a ceiling below 1% (report.fmt_ceiling prints a percentage from 1%); l_min per Q32 (L or 0)
def brackets_needed(p: float, p0: float) -> float
    # spec 7.2: ceil(((1.645 sqrt(p0 (1 - p0)) + 0.842 sqrt(p (1 - p))) / |p - p0|) ** 2), one-sided in the direction
    # of the typed rate; math.inf when p == p0. 617 at (0.55, 0.50), 153 at (0.60, 0.50). The card prints
    # `assumed.nbmany` instead of a number when the result exceeds the resolved no-edge brackets of the run.
def structural_max(limits: tuple[float, ...]) -> float               # (1 + l1)/(1 - l1) * prod(1 + li, i >= 2)
def bold_even(x: "fractions.Fraction", p: "fractions.Fraction") -> "fractions.Fraction"
    # exact P(reach 1 from x) under bold play at even money (Dubins-Savage): walk the doubling orbit of x
    # (x < 1/2: f = p f(2x); x > 1/2: f = p + (1 - p) f(2x - 1); f(1/2) = p; f(0) = 0; f(1) = 1) until 1/2 or a repeat,
    # then solve the linear cycle exactly
def bracket_reference(r: np.ndarray, d: np.ndarray, *, w0, l_min, target, n_checks, kappa, phi_buy, phi_sell, r_exit)
    -> float      # Q33, section 9.1
```
### 9.1 bracket_reference
r: net return per unit stake of each recorded bracket (exit proceeds net of the proportional exit charge minus the
stake and its proportional entry charge, over the stake); d: checks from entry to exit fill (>= 1). Bins: r into 32
equal-count bins (bin value = mean r), d into 4 equal-count bins (bin value = ceil(mean d)), joint weights by count
(cells with weight 0 dropped). Grid: 129 wealth nodes `linspace(l_min, target, 129)`. `V[0] = (w >= target)`;
for t = 1..n_checks: `V[t](w) = max((w >= target), V[t-1](w), max over k in 1..16 of sum over cells of weight *
interp(w + s_k r_c - phi_buy - phi_sell, grid, V[max(t - d_c, 0)]))` with `s_k = (k / 16) * max(0, w - l_min -
phi_buy - r_exit) / (1 + kappa)` (`kappa`: the buy side's base rate at p0, `costs.kappa(..., side="buy")`; the exit
side's charges are already inside r), interpolation clamped at the grid ends (below l_min reads V(l_min) = 0 unless
l_min >= target). Returns `V[n_checks](w0)`. It never drives a red flag.

## 10. `core/odds/report.py` (Tasks 9, 12; Tasks 13, 14, 17 and 18 only call it, O3-20)

### 10.1 Types
```python
LADDER = (1.10, 1.25, 2.0, 10.0)                  # x W0; then the target (simulate reads report.LADDER)
COST_DOMINATED_SHARE = 0.10                       # Q43 (simulate reads report.COST_DOMINATED_SHARE)
@dataclass(frozen=True, kw_only=True)
class ColumnStats:
    key: str; member: str; scenario: str; n: int
    reached: int                  # first passage: liquidation value >= T at some check (the ceiling's quantity)
    reached_outcome: int          # moonshot REACHED outcomes (<= reached: a locked exit can miss T); 0 for compounding
    ended_at_or_above: int        # terminal value >= T
    at_floor: int; running: int; locked_at_horizon: int
    rungs: tuple[int, ...]        # counts of terminal value >= LADDER[i] x W0, then >= T
    median: float; p5: float; mean: float; mean_se: float; mean_cost: float
    g_se: float                   # std(V_term + cost_term, ddof 1) / sqrt(n): the SE of the average-line statistic
    kept_lo: float | None; kept_hi: float | None             # min and max terminal value of AT_FLOOR paths
    x_mean: float; x_var: float; x_range: float              # HIDDEN_EDGE sample (ddof 1) and R (section 10.3,
                                                              # fixed before the run; nan for garch, inf unbounded)
    wins: int; losses: int; unresolved: int
    brackets: tuple[np.ndarray, np.ndarray] | None = field(default=None, compare=False, repr=False)
        # (r, d) of up to BRACKET_SAMPLE brackets of chunk 0; outside ==, repr and every hash (arrays compare
        # element-wise); a test comparing two columns uses (erratum, O3-18; Tasks 9, 13; nan != nan)
        # dataclasses.replace(col, brackets=None, x_range=0.0 if math.isnan(col.x_range) else col.x_range)
    band_edge_share: float; band_edge_sessions: int; worst_gap: float; trades: int
        # band_edge_sessions: simulated sessions that opened at a band edge; trades: paths with an entry fill
@dataclass(frozen=True, kw_only=True)
class HiddenEdge:
    status: str      # "pass" | "red_gain" | "red_loss" | "unavailable" (GARCH-t) | "unbounded" (k_x >= 1, 10.3)
                     # | "not_applicable"
    mean: float; bound: float; range_: float; n: int
@dataclass(frozen=True, kw_only=True)
class Flag:
    code: str; level: str; key: str; slots: Mapping[str, str]    # level "red" | "amber" | "info"
@dataclass(frozen=True, kw_only=True)
class OddsReport:
    plan_hash: str; plan_index: int; plan_count: int
    refused: plan.Refusal | None
    track: str; stake: float; target: float; floor: float; l_min: float; horizon_days: int; n: int
        # l_min = floor under floor_safe sizing (replay legs included), else 0.0 (Q32)
    sizing: str                                        # "floor_safe" | "stop_based": picks the ceiling wording
    model_key: str; model_slots: Mapping[str, str]
    columns: tuple[ColumnStats, ...]                   # () when refused
    headline: str                                      # column key
    spread: tuple[float, float] | None
    spread_kind: str                                   # "other" | "krx" | "blocks" | "none" (Q31); dropped in notes
    notes: tuple[tuple[str, str], ...]                 # (member, failed check: "deterministic" | "statistical" |
                                                       #  "fit" | "refit")
    ceiling: float                                     # bold.ceiling(stake, l_min, target)
    structural_cap: float | None; structural_sessions: int | None
    tax_basis: str; cost_words_key: str
    hidden: HiddenEdge | None
    flags: tuple[Flag, ...]
    assumed: Mapping[str, float] | None                # w, p0, u, nb (math.inf allowed), resolved, theta
    replay: Mapping[str, float] | None                 # y0, y1, cut, bench_sr, haircut_sr, diff, ci_lo, ci_hi, fstar,
                                                       # h, growth, growth_iid (block_growth and (1 + mean R1)^h - 1)
    comparison: tuple[int, int, int]                   # (K, J, R)
    provenance: Mapping[str, object]
def build(**fields) -> OddsReport
def refusal_report(plan_obj, refusal: plan.Refusal, *, index: int = 1, count: int = 1,
                   provenance: Mapping[str, object] = MappingProxyType({})) -> OddsReport
def flags_for(*, headline: ColumnStats, no_edge: tuple[ColumnStats, ...], engine: str, hidden: HiddenEdge | None,
              ceiling: float, structural: tuple[float, int] | None, target: float, stake: float,
              reference: float | None, rule_flags: tuple, grey: tuple[tuple[str, str, str], ...],
              series: plan.Series, okx: bool) -> tuple[Flag, ...]
    # rule_flags = Screening.flags; grey = (row id, cap text, auto_off ISO) per gate.grey_rows id. Emits, in order:
    # HIDDEN_EDGE (red hidden.gain | hidden.loss; info hidden.pass | hidden.coarse | hidden.unavailable |
    #   hidden.unbounded; on bootstrap and replay cards; hidden.na under every edge column);
    # CEILING_BREACH (red breach.red | amber breach.amber, from ceiling_cells(no_edge, ceiling));
    # ABOVE_ESTIMATED_REFERENCE (amber flag.reference, when reference is not None and the two-sided lower bound of
    #   the headline's plain count / n is above it; the plain count is reached_outcome on moonshot cards and reached
    #   on compounding cards, Q32); IMPOSSIBLE (info structural.impossible, when structural is set and target > stake
    #   * cap); BELOW_RESOLUTION (info, key "", when the plain count is 0 and neither IMPOSSIBLE nor no-trade
    #   applies: plain.none carries it);
    # GREY_LEG (amber flag.grey per grey row); PROXY_DATA (info flag.proxy when okx, plus flag.proxyfx when
    #   series.proxy_dates); CHECKS_AT_OPEN_CLOSE (info flag.openclose, bootstrap) or CLOSE_ONLY_CHECKS (info
    #   flag.closeonly, garch and replay); BAND_EDGE_SESSIONS (info flag.bandedge, headline.band_edge_sessions > 0);
    #   LIMIT_GAP (info flag.gap, headline.worst_gap > 0); LOCKED_AT_HORIZON (info flag.locked,
    #   headline.locked_at_horizon > 0); COST_DOMINATED (amber flag.cost, headline.mean_cost >= COST_DOMINATED_SHARE x
    #   stake); RULE_CHANGE_IN_HORIZON (amber rule.review per review_by flag, rule.end per auto_off or effective_until
    #   flag). NOT_TRADABLE, STUCK_AT_START and SPECIAL_REGIME only ever appear as refusals.
def render(rep: OddsReport) -> str
    # the text of section 10.4's render order; then hits = guard(text); a hit raises ValueError("rendered text failed
    # the language guard: ...") (the CLI turns it into exit 4), so no report ever prints a banned word or internal name
```
Provenance keys (stored as data): `rules_sha`, `instruments_sha`, `venues_sha`, `state_hash`, `owner_seq`,
`owner_row`, `code_hash`, `code_signed`, `fingerprint`, `decision_id`, `screening_hash`, `series_md5`, `components`,
`proxy_dates`, `calendar_sha`, `calendar_version`, `calendar_md5s`, `model`, `members`, `seed_hex`, `n`, `chunk`,
`numpy`, `scipy`, `cryptography` (from `Provenance.cryptography`), `edge_source`, `repo_anchor`, `tree_hash`,
`comparison_id`, `run_counter`, `plan_hash`. **Rendering rule:** a `prov.*` line prints only hashes (their first 16
hex characters), versions, ISO dates, counts, `repo_anchor`, the comparison id (always `c` and six digits, Q12) and
catalogue labels. The calendar line prints the version, the sha prefix and the md5 prefixes in file order, never a
file id (`holidays_KRX`, `kr_sessions` and `kr_regime_tags` hold underscores); `model`, `members` and `edge_source`
render through `label.*`, `member.*` and `edge.*` keys; `CARD_ID` never renders (the card text says "S_C3").

### 10.2 Statistics and number formats
```python
CP_LEVEL = 0.95; DELTA = 1e-4; RED_ALPHA = 0.001
def cp_two_sided(k: int, n: int, level: float = CP_LEVEL) -> tuple[float, float]
    # k > 0: (beta.ppf((1 - level) / 2, k, n - k + 1), beta.ppf((1 + level) / 2, k + 1, n - k)) with hi = 1 at k = n;
    # k = 0: (0.0, beta.ppf(level, 1, n)) (the one-sided bound; 2.9957e-06 at n = 1e6)
def cp_lower(k: int, n: int, level: float) -> float     # 0 at k = 0, else beta.ppf(1 - level, k, n - k + 1)
def bernstein(v: float, r: float, n: int, delta: float = DELTA) -> float
    # sqrt(2 v ln(4/delta) / n) + 7 r ln(4/delta) / (3 (n - 1)); v the ddof-1 sample variance
def hidden_edge(col, *, w0, target, l_min) -> HiddenEdge
    # "unavailable" when col.x_range is nan (GARCH-t); "unbounded" when it is inf; else red when |col.x_mean| >
    # b = bernstein(col.x_var, col.x_range, col.n): red_gain for a positive mean, red_loss for a negative one; else
    # "pass". The pass sentence states b, b / w0 and the blind spot b / (target - l_min) (fmt_blind; hidden.coarse
    # when b >= target - l_min).
def ceiling_cells(cols, ceiling) -> tuple[str, float]           # ("" | "amber" | "red", the worst lower bound)
    # amber when cp_lower(k, n, 0.95) > ceiling for some no-edge cell; red when cp_lower(k, n, 1 - RED_ALPHA / m) >
    # ceiling, m = number of no-edge cells (members x 2 scenarios, or the replay's 2; delisting and edge columns
    # excluded); compared on exact floats
def fmt_krw(x) -> str          # f"{round(x):,}"
def _sf2(x: float, up: bool) -> int   # x to 2 significant figures, rounded up or down (12,406 -> 12,000 down;
                                      # 20,656 -> 21,000 up)
def fmt_prob(k, n) -> str      # the point estimate, nearest: k = 0: "below about 3 in {n:,}"; p >= 0.01:
    # f"about {100 p:.1f}%" ("above 99.9%" when it would round to 100.0 with k < n); else "about 1 in {N:,}", N =
    # 1/p to the nearest 2 significant figures
def fmt_end(p: float, *, upper: bool) -> str   # an interval end, rounded OUTWARD (Q32): p >= 0.01: upper
    # f"{ceil(1000 p) / 10:.1f}%", lower f"{floor(1000 p) / 10:.1f}%"; else f"1 in {_sf2(1 / p, up=not upper):,}";
    # a lower end of 0 never reaches it (k = 0 prints fmt_prob's "below about 3 in n"). The printed interval
    # always contains the Clopper-Pearson interval (tested for every k in 1..1000 at n = 2e5 and 1e6)
def fmt_ceiling(c: float) -> str      # an upper bound: c < 0.01: f"1 in {floor(1 / c):,}" (1 in 1,000; 1 in 1,999);
    # else f"a {ceil(1000 c) / 10:.1f}% chance" (c 0.6667 -> "a 66.7% chance"; c 0.3333 -> "a 33.4% chance")
def fmt_blind(x: float) -> str        # the HIDDEN_EDGE blind spot b / (T - L_min), an upper bound: x < 0.01:
    # f"1 in {floor(1 / x):,}"; else f"{ceil(1000 x) / 10:.1f} percentage points"
def fmt_order(lb: float, c: float) -> tuple[str, str]   # breach slots, lb > c: rounded so the printed order matches
    # the comparison (an alarm is never hidden by rounding): lb < 0.01: (f"1 in {floor(10 / lb) / 10:,.1f}",
    # f"1 in {ceil(10 / c) / 10:,.1f}"); else (f"{ceil(10_000 lb) / 100:.2f}%", f"{floor(10_000 c) / 100:.2f}%")
```
**Target probability slots.** For a no-edge column whose point estimate k/n is above `rep.ceiling` while
`ceiling_cells` raised nothing, every slot that would print that column's point estimate prints `cap.p` instead
(Q32). Interval ends always print through `fmt_end`, spread ends through `fmt_end` (the lowest lower end with
`upper=False`, the highest upper end with `upper=True`).

### 10.3 HIDDEN_EDGE range (fixed before the run)
Bootstrap columns: `x_range = V_max + n_checks x C_max` with
- `V_max = ((T + CARRY x phi_sell') / (1 - k_x)) x e^m_max`, `CARRY = LIMIT_DOWN_CARRY_COST_MULTIPLIER`: before tau
  V < T, cash >= 0 and chi <= CARRY give cash + units x p < (T + CARRY x phi_sell') / (1 - k_x), and one more check
  moves the price by at most e^m_max;
- `k_x = CARRY x costs.kappa_bound(terms, p_min, horizon session dates, mult)` (both sides, so a KRX stock sell's tax
  inside the floor is covered, R2-1), a bound fixed in advance (never a sample
  maximum): `p_min = p0 x prod over the horizon sessions of (1 - limit_s)` on KRX legs (every check of a session stays
  at or above that session's D >= ref x (1 - limit)), and `p0 x exp(-n_checks x m_max)` otherwise; a book with no
  ladder has its constant table rate;
- `C_max = k_x x V_max + CARRY x max(phi_buy', phi_sell')` (primes: scenario-scaled), the most one fill can charge;
- `m_max` the largest m_o or m_i of the history, `n_checks` the column's check count.
When `k_x >= 1` (a tick-floor rate of 50% or more at the lowest reachable price, possible on long KRX horizons) the
range is not finite: `x_range = inf` and HIDDEN_EDGE reports "unbounded" (`hidden.unbounded`, which prints
"unavailable for this plan (no finite range)"; accepted as conservative, RULINGS_ROUND2 R2-7, Q46 item 9).
Replay no-edge columns: `V_max = T x (1 + max a)`, `C_max = mult x max c x V_max`, `x_range = V_max + n_checks x
C_max` (no kappa and no phi; before tau cash + sleeve < T). A unit test plants a kappa bound with k_x just under 1
(finite range) and at 1 (unbounded).
`def hidden_range(*, target, phi_buy, phi_sell, kappa_bound, m_max, n_checks, carry=CARRY) -> float` (bootstrap)
and `def replay_range(*, target, a_max, c_max, n_checks) -> float` (replay) compute it; `simulate._column` sets the
value in `ColumnStats.x_range` right after `run_column` (Task 14; nan for garch), not `run_column` itself (erratum,
RULINGS_ROUND3 O3-18). Task 14 wires `hidden_range` into bootstrap columns before `hidden_edge(headline)` runs, so
a bootstrap card never prints the GARCH-t sentence (O3-11). Resolution printed: the bound b in KRW, as % of the stake, and the blind spot
`fmt_blind(b / (T - L_min))`, which is "1 in floor((T - L_min) / b)" below 1% (Q46: never the spec's ceil).

### 10.4 The sentence catalogue (`CATALOGUE: Mapping[str, str]`, exact texts; slots in braces)
193 keys: the 191 below plus `label.yes` and `label.no` (erratum, RULINGS_ROUND3 O3-10 and O3-19, Task 12 D4).
Task 12 pins the sha256 of the whole catalogue, so any changed character fails it.
Model and sizing:
- `model.bootstrap` "Model: a two-point bootstrap of the daily moves of {symbol} in won, {first} to {last} ({rows} sessions), in which nobody has an edge. Price checks at the open and the close only."
- `model.garch` "Model: GARCH-t fitted to the daily won returns of {symbol}, {first} to {last} ({rows} sessions), in which nobody has an edge. Price checks at the close only."
- `model.replay` "Model: the tested strategy's own out-of-sample daily results, {first} to {last} ({rows} sessions), resampled in blocks of about {block} days. Price checks at the close only."
- `sizing.floor` "Floor-protected sizing: your floor of KRW {floor} holds even if this position goes to zero."
- `sizing.stop` "Stop-based sizing: a gap past the stop can take you below your floor of KRW {floor}."
- `okx.cap` "Each simulated OKX entry is capped at {cap} of this plan's stake (KRW {capkrw}), the cap the gate applies."
- `fx.us` "US prices are turned into won with Yahoo's KRW=X rate: the open with the previous day's close and the close with the same day's close."
- `kelly.label` "This stake aims at long-run growth, not at reaching your target."
- `period.month` / `period.months` "month" / "months"; `period.day` / `period.days` "{h}-day period" / "{h}-day periods".
Typical result and average:
- `typical.median` "The middle {one} ends with KRW {median}."
- `typical.floor` "In {p} of {many} you end at your floor, keeping between KRW {lo} and KRW {hi}, and can no longer trade."
- `typical.nofloor` "No simulated {one} ended at your floor."
- `average.agrees` "Averaged over all simulated {many}: about KRW {expected} ({costwords} average KRW {cost}; the simulation's own average, KRW {mean} ± {se}, agrees). That average includes rare jackpots and is not what usually happens."
- `average.differs` "The simulation's own average, KRW {mean} ± {se}, does not match your stake minus the average {costwords} (KRW {expected}); see the bug check below."
- `average.gain` "Averaged over all simulated {many}: an average gain of KRW {gain}, only if the edge in this column is real."
- `average.loss` "Averaged over all simulated {many}: an average loss of KRW {loss}, even with the edge in this column."
- `cost.fees` "fees"; `cost.tax` "fees and the securities transaction tax"; `cost.delist` "{base} and the delisting stress loss".
Headline, ladder, plain sentence, precision (every probability slot is filled by section 10.2's formatters: a point
estimate by `fmt_prob` or, above the ceiling, `cap.p`; interval and spread ends by `fmt_end`, outward):
- `headline.moonshot` "Chance of reaching KRW {target} before income tax: {p}."
- `headline.compounding` "Was worth KRW {target} at some price check in {k} of {n} made-up {many} ({pk}); ended at or above it in {k2} ({pk2})."
- `headline.floor` "Chance of ending at your floor: {p}."
- `ladder.head` "Ended at or above:"; `ladder.rung` "{label} (KRW {value}): {p}"; `ladder.impossible` "{label} (KRW {value}): IMPOSSIBLE for this buy-and-hold plan"; labels `ladder.p10` "+10%", `ladder.p25` "+25%", `ladder.x2` "2 times your stake", `ladder.x10` "10 times your stake", `ladder.target` "your target"; `ladder.spread` "Middle result KRW {median}; 5th percentile KRW {p5}."
- `plain.hit` "In {n} made-up {many} (from a model in which nobody has an edge, not real history), this plan reached KRW {target} before income tax in {k}, {about} (counting noise alone: between {hi} and {lo}; {spread}; {bugs}, and nothing here covers the model being wrong)."
- `plain.none` "In {n} made-up {many} (from a model in which nobody has an edge, not real history), this plan never reached KRW {target} before income tax (below resolution: under about 3 in {n}; {spread}; {bugs}, and nothing here covers the model being wrong)."
- `bugs.coarser` "the bug checks are coarser than these ranges"; `bugs.finer` "the bug check's resolution is printed below" (Q32 picks one).
- `cap.p` "at most {c}, the ceiling (the simulated {k} in {n} is above it only through counting noise)"
- `spread.other` "other models give {a} to {b}"; `spread.krx` "the same model with other block lengths gives {a} to {b}; no second model family is available for KRX"; `spread.blocks` "the same model with other block lengths gives {a} to {b}"; `spread.none` "no other model could be run here"; `spread.dropped` "{member} was left out because its {check} check failed"; members `member.bootstrap` "the two-point bootstrap", `member.half` "the bootstrap at half the block length", `member.double` "the bootstrap at twice the block length", `member.garch` "GARCH-t", `member.refit` "the GARCH-t refit"; checks `check.deterministic` "deterministic", `check.statistical` "statistical", `check.fit` "fit", `check.refit` "refit".
- `structural.impossible` "IMPOSSIBLE for this buy-and-hold plan: KRX's daily band allows at most {cap}× in these {s} sessions."
- `structural.notrade` "No simulated {one} made a trade, so these numbers describe holding cash."
  (Q44: when either applies, it replaces the headline P(target), the plain sentence, the target's spread and
  BELOW_RESOLUTION; no other line prints a probability of the target.)
Tax, ceiling, base rates (the `{c}` slots are `fmt_ceiling`: "1 in 1,999" below 1%, "a 66.7% chance" from 1%):
- `tax.krx` "Tax: this KRX holding is treated as a small holder's, so its gains pay no capital gains tax here; any securities transaction tax is inside the costs."
- `tax.overseas` "Tax: overseas share gains above KRW 2.5 million a year are taxed at 22%. Not simulated: these numbers are before income tax."
- `tax.crypto` "Tax: crypto gains are due to be taxed at 22% from 2027 (unless postponed again). Not simulated: these numbers are before income tax."
- `ceiling.noedge` "No plan without a real edge that keeps this floor can beat {c}." (floor-protected sizing)
- `ceiling.nofloor` "No plan without a real edge can beat {c}." (stop-based sizing: L_min = 0)
- `ceiling.edge` "Without the edge assumed here, no plan that keeps this floor can beat {c}."; `ceiling.edgenf` "Without the edge assumed here, no plan can beat {c}." (printed under the TESTED_REPLAY column; the assumed column prints `assumed.ceiling`)
- `research.estimate` "The research found no measured chance of this account growing 1,000 times in a month. Its reasoned estimates: 0.01% or less in general, roughly 0.01% to 0.03% for long far-out-of-the-money US options, and below 0.01% for domestic crypto spot."
- `baserate.kalshi` "Kalshi takers lost about 32% of the amount staked and makers about 10% (Bürgi, Deng and Whelan working paper, 2025-26; not re-verified)."
- `baserate.esma` "74-89% of EU retail CFD accounts lose money (national regulators' data, ESMA, 27 March 2018)."
- `baserate.sebi` "87.7% of Indian retail equity-derivatives traders lost in FY26 (SEBI)."
- `baserate.krderiv` "Korean retail lost about KRW 458 billion a year on overseas derivatives, 2020 to H1 2025, with no profitable year."
- `baserate.kr2020` "In a 2020 study of 204,004 Korean retail accounts, 46% lost money, and 62% of new investors did."
Columns:
- `column.stress` "With costs doubled:"; `column.delist` "If {symbol} were delisted right after you buy, losing {h}% of its value:"
- `assumed.lead` "These numbers are only as true as the win rate you typed ({w}). This bracket's no-edge win rate is {p0} ({u} of brackets end unresolved)."
- `assumed.nb` "Telling them apart would take about {nb} recorded brackets." (nb = `bold.brackets_needed`, when it is at most the resolved no-edge brackets of the run); `assumed.nbmany` "Telling them apart would take more recorded brackets than the {r} this simulation resolved." (otherwise, p == p0 included)
- `assumed.ceiling` "Without the edge you typed, no plan that keeps this floor can beat {c}."; `assumed.ceilingnf` "Without the edge you typed, no plan can beat {c}." (for floor-protected sizing the three lines render spec 7.5's text exactly)
- `replay.lead` "This replays a tested bitcoin trend strategy (S_C3) on its own {y0}–{y1} out-of-sample results, with {cut}% of its average return removed. Most of that return came from bitcoin rising in those years, which the no-edge column leaves out: just holding bitcoin then had a Sharpe ratio of {bench}, against {cutsr} for this replay after the cut. Its tested advantage over holding bitcoin was {diff} Sharpe (90% range {lo} to {hi}). Backtest edges often shrink or vanish in live trading; read this as the hopeful case."
  (The literal "S_C3" is the card's public id and the one allowed underscore token; `guard` exempts exactly "S_C3".)
- `replay.growth` "Resampled in blocks that keep its streaks, this column's average growth over {h} days is {g}, against {g0} if its days were independent." (Q38; h = checks - 1, so 29 on a 30-day horizon, O3-15; g from `models.block_growth`, g0 = (1 + mean R1)^h - 1, both `f"{100 x:.1f}%"`)
- `replay.noedge` "No-edge column: the same strategy's daily moves, each given a fair coin for its direction, with its costs kept."
Flags:
- `hidden.gain` "BUG CHECK FAILED: this plan makes money without any edge (average KRW {x}, limit KRW {b}). Do not use these numbers."
- `hidden.loss` "BUG CHECK FAILED: this plan loses more than its costs explain (average KRW {x}, limit KRW {b}). Do not use these numbers."
- `hidden.pass` "Bug check passed with a resolution of KRW {b} ({pct} of your stake): it would not notice a hidden edge (a simulator error that makes money without an edge) that raised the chance of the target by up to {m}. It does not test whether the model itself is right." (m = `fmt_blind(b / (T - L_min))`)
- `hidden.coarse` "Bug check passed, but its resolution (KRW {b}, {pct} of your stake) is too coarse to say anything about the chance of the target. It does not test whether the model itself is right."
- `hidden.unavailable` "The bug check is unavailable for GARCH-t: a bounded shock does not bound the volatility, so no finite range exists."
- `hidden.unbounded` "The bug check is unavailable for this plan (no finite range): at the lowest price this model can reach, the cost rate has no useful bound." (R2-7)
- `hidden.na` "The bug check does not apply to edge columns."
- `breach.amber` "Preliminary evidence, about 5% false-alarm rate per check: rerun with more paths. A no-edge result's lower bound, {lb}, is above the ceiling of {c}." (lb and c from `fmt_order`)
- `breach.red` "Do not use these numbers: a no-edge result beats the ceiling of {c} beyond counting noise ({lb}), so the model or the simulator has a bug."
- `flag.reference` "Above the estimated reference: this plan's chance of the target is above what this bracket's simulated outcomes could reach with any stake ({ref}). The reference is an estimate, not a bound."
- `flag.grey` "OKX is a grey venue (rule {row}): each armed session needs your acknowledgement of its warning, everything you hold there is capped at {cap} of your equity, and the gate turns it off on {off}."
- `flag.proxy` "Prices for this leg are a stand-in: Binance BTCUSDT times Upbit KRW-USDT, because OKX's own prices are not loaded."
- `flag.proxyfx` "From {d0} to {d1}, before Upbit listed KRW-USDT, Yahoo's KRW=X rate stands in for it."
- `flag.openclose` "Price checks at the open and the close only: a stop can fill well below its level after a gap."
- `flag.closeonly` "Price checks at the close only."
- `flag.bandedge` "{count} simulated sessions ({share} of all) opened at a KRX daily limit and stayed there until the close."
- `flag.gap` "The worst stop fill was {gap} below its stop level."
- `flag.locked` "In {p} of {many} the position was still locked at the lower daily limit at the end, valued at the locked price less the doubled exit charge."
- `flag.cost` "Costs average KRW {cost}, {pct} of your stake."
- `rule.review` "From {date} this plan opens no new position unless you re-approve rule {row}; it keeps and may close what it holds."
- `rule.end` "On {date} rule {row} ends ({what}), so the plan closes its position at the first price check on or after that date and opens no new one."; `rule.auto` "the gate turns this venue off"; `rule.until` "the rule expires".
Refusals (`refused.head` "Refused: {why}" then `refused.none` "No numbers are shown for a refused plan."):
- `why.PARTIAL_CHUNK` "the path count must be a whole multiple of {chunk}."
- `why.UNSUPPORTED_PRODUCT` "this plan uses something the odds engine does not support: {what}." with `sub.venue` "only KIS, Upbit and OKX legs", `sub.feed` "only BTC on OKX, the one OKX market with a price feed", `sub.symbol` "a symbol the signed instrument map lists for this venue", `sub.class` "only shares, 1x ETFs and coins", `sub.multiple` "only products that move one for one with their underlying", `sub.tax` "a tax basis the engine can describe", `sub.horizon` "a horizon of 1 to 366 days", `sub.start` "a plan that starts today (the Asia/Seoul date)", `sub.track` "a moonshot or compounding track", `sub.numbers` "a positive stake, a target above the stake and a positive won-dollar rate", `sub.model` "the two-point bootstrap or GARCH-t", `sub.sizing` "stop-based sizing only with a bracket", `sub.fraction` "Kelly only on the tested-strategy replay, bold play only with a bracket", `sub.bracket` "a take-profit above 0 and a stop between 0 and 100%", `sub.edge` "a typed win rate between 0 and 1, with a bracket and the two-point bootstrap", `sub.replay` "the tested-strategy replay only as an Upbit bitcoin holding", `sub.file` "a plan file the engine can read", `sub.comparison` "a comparison id this engine issued earlier".
- `why.MULTI_LEG_UNSUPPORTED` "this plan has more than one leg; only single-leg plans are supported."
- `why.STATE_UNUSABLE` "the signed owner state is not usable (no owner key yet, a broken owner log, unapproved tables, or code changed since you signed it), so nothing new is allowed."
- `why.LIMITS_UNSET` "your total-loss floor and daily loss limit are not both set, or an OKX leg has no OKX cap. Limits you set take effect from the next day."
- `why.CALENDAR_UNSIGNED` "KRX and US plans need the calendar set you signed; it is missing or does not match. Only crypto plans run until then."
- `why.CALENDAR_COVERAGE` "this horizon runs past the end of the signed calendar."
- `why.DATA_INVALID` "the data given to the engine did not pass its checks: {what}." with `data.now` "the run's clock reading is not today's", `data.series` "the price history", `data.sessions` "the session list", `data.empty` "the horizon holds no trading session of this market", `data.stale` "the last price is more than {days} days before the start".
- `why.SYNTHETIC_REFUSED` "the price history is made-up data, not market prices."
- `why.NOT_TRADABLE` "{venue} {symbol} cannot be costed or sized from the signed venue table: a minimum order, lot size or fixed charge is missing, or a date in the horizon is outside a signed tick or tax table."
- `why.SPECIAL_REGIME` "{symbol} has fewer than 60 KRX sessions of history before the start, so it may still be in a special reference-price regime."
- `why.SHORT_HISTORY` "{symbol} has fewer than 250 daily bars of history before the start."
- `why.CARD_NOT_REPRODUCED` "the tested strategy did not reproduce its validated card, so its column cannot be shown."
- `why.MODEL_NOT_FOR_LIMITED_VENUE` "GARCH-t is not available for a KRX leg, whose daily band that model does not include."
- `why.MODEL_CHECK_FAILED` "the chosen model failed its {check} check, so no numbers are shown."
- `why.COST_DOMINATED` "costs take the whole win of this bracket, or a single exit could cost the whole position."
- `why.STUCK_AT_START` "can't open: no first stake is affordable after your floor, the reserved exit charge and lot rounding; the largest stake is below the venue minimum."
- `why.SCREEN_BLOCKED` "the compliance gate blocks this leg: {what}." with `screen.row` "rule {row}", `screen.unsigned` "the current code is not signed yet", `screen.other` "see the gate's own check".
- `why.ASSUMED_EDGE_UNREACHABLE` "the win rate you typed ({w}) cannot be reached by tilting this bracket's moves."
Closing boxes:
- `notin.title` "Not in these numbers:"; items `notin.tax` "income tax (estimated, not simulated)", `notin.fx` "won-dollar moves beyond the historical range in the data, and the timing of the KRW=X rate", `notin.upbit` "Upbit withdrawal holds after a KRW deposit, and the Upbit-to-OKX route closing without notice", `notin.freeze` "exchange freezes or failure", `notin.delist` "delistings and Upbit warnings (survivorship)", `notin.krx` "KRX halts, VI auctions, designations, resets and other special reference-price regimes", `notin.intraday` "intraday moves", `notin.unfilled` "unfilled orders beyond what is modelled", `notin.broker` "broker refusals", `notin.hacked` "hacked or locked accounts", `notin.rules` "rule changes"; `notin.close` "Most of these make the real result worse; none makes a no-edge plan better."
- `limits.injected` "How these numbers were made: unsigned loading code supplies the price history, the session list and the replay. This report records their hashes but cannot check them against any signed source. The calendar files used carry the hash you signed; the session dates taken from them, and the KRX Saturday rule read from data/macro, are not re-checked here. The replay matches its pinned results; the card and results-file hashes it reports come from unsigned code. NumPy and SciPy are outside the signed code hash."
- `compare.caption` "With no real edge, a higher chance of the target generally comes from putting more of your stake at risk, sooner. Check P(at your floor) beside it. Higher here means riskier, not better." (moonshot only)
- `compare.k` "You compared {k} plans (and tried {j} typed win rates) in this session. The highest-looking figure is the luckiest of {k}."
- `compare.r` "This plan has been run in {r} comparisons, each on its own market seed; the highest-looking of its figures is the luckiest of {r}."
- `compare.fresh` "Before arming, this plan must be run again on a fresh market seed; that rerun belongs to execution and is not built yet." (R2-4: not built by this plan; the hand-off gives it to E2, which arms)
- `plan.head` "Plan {i} of {k} ({hash})"
- `prov.head` "Recorded with this report:"; `prov.line` "{label}: {value}"; labels `prov.code` "code hash", `prov.signed` "code signed", `prov.owner` "owner log entry", `prov.key` "key fingerprint", `prov.tables` "tables in force", `prov.data` "price history", `prov.calendar` "calendar", `prov.seed` "market seed", `prov.paths` "paths and chunk", `prov.versions` "NumPy, SciPy, cryptography", `prov.repo` "repository", `prov.tree` "tree hash", `prov.comparison` "comparison and run", `prov.model` "model and members", `prov.edge` "edge source"; value labels `label.bootstrap` "two-point bootstrap", `label.garch` "GARCH-t", `label.replay` "tested-strategy replay", `edge.none` "none", `edge.assumed` "a typed win rate", `edge.replay` "the S_C3 replay"; and (erratum, O3-10, Task 12 D4) `label.yes` "yes", `label.no` "no", the `prov.signed` value of the `code_signed` bool.
- `footer` "These numbers describe rules you wrote, run in a model. They are not advice, and TRADEGEN does not recommend any plan. A higher chance of reaching the target does not make a plan better."
```python
BANNED_WORDS = ("best", "optimal", "recommended", "safe", "guaranteed", "sure", "ideal", "risk-free", "low-risk",
                "proven", "should")
BANNED_PHRASES = ("worth trying", "good chance", "likely to reach")
def say(key: str, **slots) -> str          # CATALOGUE[key].format(**slots); KeyError on an unknown key or slot
def guard(text: str) -> list[str]
    # hits: a banned whole word (tokens re.findall(r"[a-z0-9]+(?:-[a-z0-9]+)*", text.lower()), each hyphenated token
    # also checked part by part), a banned phrase (whitespace-normalised, case-insensitive), any "_" outside the token
    # "S_C3", any "{" or "}"
```
Render order (`render`): plan head; red flags (HIDDEN_EDGE failed, CEILING_BREACH red: "Do not use these numbers"
comes before any number, Q46); model (on a replay card `replay.noedge` right after it: erratum, O3-19, Task 12 D5);
sizing; OKX cap; FX; Kelly label; typical (median, floor); average; headline
pair; ladder; plain sentence (or `structural.*`, Q44); tax; ceiling; research estimate; five base rates; the other
columns (stress 2x, delisting, assumed, replay), each with its typical, floor and average lines, and the edge
columns with their ceiling line; amber flags, then info flags; not in these numbers; limits; comparison lines (K
note, R note, caption, fresh-seed line); footer; provenance. A refused report renders plan head, refused.head,
refused.none, footer and provenance only. `render` then runs `guard` over the whole text and raises on any hit.

## 11. `core/oddsdata/bars.py` (Task 15)
### 11.1 Seams (module level, each importing its client inside; looked up at call time)
```python
def _kis_daily(code: str, start: str, end: str) -> list[dict]
    # from data.krx import kis_client; return kis_client.KISClient().daily(code, start=start, end=end, adjusted=True)
def _upbit_daily(market: str, days: int)        # from data.crypto import crypto_client; UpbitPublic().daily(market, days=days)
def _binance_daily(symbol: str, days: int)      # crypto_client.BinancePublic().daily(symbol, days=days)
def _yf_download(tickers: list[str], start: str, end: str)
    # import yfinance; d = _yf_dir(); yfinance.set_tz_cache_location(str(d)); return yfinance.download(tickers,
    # start=start, end=end, auto_adjust=True, progress=False, threads=False, multi_level_index=True)
```
### 11.2 Constants and paths
```python
HISTORY_DAYS = 3650; KIS_PAGE = 100; KIS_MAX_PAGES = 60; FX_TICKER = "KRW=X"
ET = zoneinfo.ZoneInfo("America/New_York")      # built once at import; KST is core.compliance.model.KST
CACHE_ENV = "TRADEGEN_ODDS_BARS_CACHE"
def odds_dir() -> Path       # core.isolation.state_root() / "odds"   (call time)
def cache_dir() -> Path      # odds_dir() / "bars"
def _yf_dir() -> Path        # checked_target(odds_dir() / "yfinance", "odds yfinance cache", within=odds_dir()),
                             # then mkdir(parents=True, exist_ok=True)
```
### 11.3 Finality (Q6, Q35)
`final_crypto(d, now)`: now >= datetime(d+1, 00:00, UTC); `final_krx(d, now)`: now >= datetime(d, 15:40, KST);
`final_us(d, now)`: now >= datetime(d, 16:10, ET); `final_fx(x, now)`: now >= datetime(x+2, 00:00, UTC).
### 11.4 Loaders
```python
@dataclass(frozen=True, kw_only=True)
class Part: symbol: str; source: str; dates: tuple[str, ...]; open: tuple[float, ...]; close: tuple[float, ...]
            adjustment: str; status: str = "final"
def part_md5(part: Part) -> str      # plan.series_md5 over the part's fields
def kis_part(code, start: date, end: date, now) -> Part        # paged backwards; source "KIS", adjustment "split"
def upbit_part(market, start, end, now) -> Part                # source "UPBIT", adjustment ""
def binance_part(symbol, start, end, now) -> Part              # source "BINANCE", adjustment ""
def yahoo_part(ticker, start, end, now) -> Part                # source "YAHOO", adjustment "" for KRW=X else "total"
def load_leg(plan, inst: rules.Instrument, now, *, refetch: bool = False) -> plan.Series
    # window [plan.start - HISTORY_DAYS days, plan.start); kis/krx: kis_part -> symbol code, source "KIS";
    # upbit: upbit_part("KRW-" + symbol) -> symbol "KRW-<symbol>", source "UPBIT";
    # kis/us: yahoo_part(symbol) and yahoo_part("KRW=X") -> symbol, source "YAHOO:<sym>*YAHOO:KRW=X", adjustment "total";
    # okx BTC: binance_part("BTCUSDT"), upbit_part("KRW-USDT"), yahoo_part("KRW=X") -> symbol "BTC",
    #   source "BINANCE:BTCUSDT*UPBIT:KRW-USDT", proxy_dates per Q35; components = ((label, part_md5), ...) with labels
    #   "KIS:<code>", "UPBIT:<market>", "BINANCE:<symbol>", "YAHOO:<ticker>"; md5 = plan.series_md5(...)
```
Rows dropped: dates outside the window, non-final dates, open or close None, not finite, or <= 0.
### 11.5 Cache (Q13, Q36)
File `cache_dir()/f"{source}_{safe(symbol)}_{start}_{end}.json"` (safe: characters outside `[A-Za-z0-9.=-]` become `_`),
bytes `canonical_json({**part fields, "fetched_utc": iso_utc(now)}).encode() + b"\n"`; `MANIFEST.jsonl` lines
`canonical_json({"file": name, "sha256": sha})` + "\n"; the last line for a name wins. `read_cached(...)`: None when
the env switch is "0", the file or its manifest line is missing; RuntimeError when the sha differs. `write_cached`:
the grokteam pattern (checked_target on the file, its `.tmp` and the manifest, each `within=cache_dir()`; mkdir;
write the tmp; `os.replace`; append the manifest line). `refetch=True` skips the read.

## 12. `core/oddsdata/inputs.py` (Task 16)
```python
def calendar_for(now) -> tuple["CalendarSet | None", str, str]
    # (cal, sha, error): sha = owner.calendar_in_force(now); None -> (None, "", "unsigned: no signed calendar approval");
    # dir = owner.store_dir() / "calendar" / sha; rules.calendar_sha256(dir) != sha (or it raises) -> (None, "",
    # "unsigned: the stored calendar set does not hash to its approval"); else (CalendarSet(dir), sha, "")
def sessions(market: str, start: date, horizon_days: int, cal) -> tuple[tuple[str, ...], tuple[float, ...],
                                                                      tuple[tuple[str, str], ...], str, str]
    # (dates, limits, md5s, version, error); CRYPTO: every date of [start, start + H), no calendar; KR:
    # clocks.sessions_between("KR", start, start + H - 1, cal=cal), limits regime.regime_tags("KR", d, cal=cal)
    # ["price_limit"] each, md5s of kr_sessions, holidays_KRX, kr_regime_tags; US: sessions_between("US", ...), no
    # limits, md5s of holidays_NYSE; CalendarUnsigned -> error "unsigned: <text>", CalendarCoverageError -> "coverage:
    # <text>" (dates empty). Always cal=; never core.calendars.default() (clocks.py and regime.py bind `default` by
    # name at import, so the test patches store.default, clocks.default and regime.default together).
REPO = Path(__file__).resolve().parents[2]
UNVERSIONED = "UNVERSIONED"                                  # == core.quant.gate_ledger.UNVERSIONED
TREE_GLOBS = ("core/**/*.py", "data/macro/**/*", "config.py")  # == core.ficc.macro_artifacts.TREE_GLOBS
def repo_anchor(root: Path = REPO) -> str    # copy of gate_ledger.repo_anchor (R2-6): "git:<40 hex>" of .git/HEAD,
    # following one "ref:" line, else UNVERSIONED; OSError -> UNVERSIONED
def tree_hash(root: Path = REPO) -> str      # copy of macro_artifacts.tree_hash (R2-6): sha256 over the sorted
    # relative paths + b"\0" + bytes + b"\0" of every TREE_GLOBS file
def provenance() -> plan.Provenance        # (repo_anchor(), tree_hash(),
                                           #  importlib.metadata.version("cryptography") or "absent")
    # RULINGS_ROUND2 R2-6: core/oddsdata imports neither core.quant.gate_ledger nor core.ficc.macro_artifacts (an odds
    # guard, section 15, enforces it); equality tests in tests/odds_inputs.py pin both copies and the two constants
    # against the originals, on the repo root and on synthetic temp roots. No run-time sys.modules check is needed.
STATE_SCHEMA = "tradegen.odds_state/1"
CID_RE = r"c[0-9]{6}"
def state_path() -> Path                   # core.isolation.state_root() / "odds" / "state.json"
def begin_run(comparison: str | None, plan_hashes: list[str], typed: list[float]) -> tuple[str, int, int, int,
                                                                                          dict[str, int]]
    # reads the state (missing -> {"schema", "runs": 0, "comparisons": {}}; unparseable or wrong schema ->
    # RuntimeError); runs += 1 on every call. comparison None: cid = f"c{runs:06d}", created with "run": runs.
    # An explicit comparison must fullmatch CID_RE AND already be in comparisons (ValueError otherwise; the CLI
    # refuses every plan UNSUPPORTED_PRODUCT sub "comparison"); its stored "run" is reused unchanged, so the seed of
    # every plan in it is the same on every invocation (Q12, Q34). Adds the plan hashes and typed rates to
    # comparisons[cid] (sorted, unique); writes it back atomically (checked_target on state.json and state.json.tmp
    # within the odds dir; mkdir; os.replace); returns (cid, comparisons[cid]["run"], K = len(plans), J =
    # len(typed), R) with R[h] = the number of comparisons whose "plans" hold h, for each h in plan_hashes
def build_inputs(plan, now, *, series, sessions_info, calendar_sha: str, replay, run) -> plan.Inputs
    # sessions_info = the 5-tuple of sessions(); run = the 5-tuple of begin_run() (plan_runs = R[plan_hash(plan)]);
    # fills plan.Inputs exactly
```
State file: `canonical_json({"schema": STATE_SCHEMA, "runs": int, "comparisons": {cid: {"run": int, "plans": [hash,
...], "typed": [p, ...]}}})` + "\n". A state file of the earlier layout (a comparison without "run") does not exist
yet (nothing has run), so there is no migration: a comparison without "run" is a wrong-schema file (RuntimeError).

## 13. `core/oddsdata/replay.py` (Task 17)
```python
CACHE = REPO / "docs/asset_expansion/cache/upbit_KRW-BTC.csv"; CARD = REPO / "docs/asset_expansion/cards/S_C3_crypto_trend_krwbtc.json"
RESULTS = REPO / "docs/asset_expansion/results.csv"         # REPO = Path(__file__).resolve().parents[2]
LOOKBACKS = (7, 14, 21, 28); MAS = (10, 20, 50, 100, 200); DOMAIN = {"hysteresis": (0.0, 0.889)}
def replay_s_c3(*, lookbacks=LOOKBACKS, mas=MAS, embargo: int | None = None) -> plan.ReplayInput
    # csv.reader over CACHE (utf-8, newline=""): header ['', 'upbit_KRW-BTC'], rows (date, close); card = json.loads(
    # CARD.read_bytes()); M, Ms, Tv = strategies.pnl_matrix(px[:, None], fn, card["rules"]["grid"],
    # cost_bps=card["rules"]["cost_bps_per_side"]) with fn wrapping crypto_trend(lookbacks, mas); wf =
    # validate.walk_forward(M, dates[1:], turnover=Tv, pnl_stress=Ms, w_is, w_oos, min_is from card["protocol"],
    # embargo=card["rules"]["embargo"] unless given); bench = simple buy-and-hold returns mapped onto wf.dates;
    # sc = validate.score_strategy(wf, grid=grid, full_pnl=M, n_trials=card["trials"]["N_total"], bench_daily=bench,
    # seed=card["seed"], domain=DOMAIN); returns ReplayInput with gate_protocol {k: validate.GATE[k] for k in
    # card["protocol"]}, stats from sc and grid[wf.chosen[-1]]["hysteresis"], results_md5 and card_md5 of the file
    # bytes. Never imports docs/asset_expansion_study.py. About 5 s.
```

## 14. `core/oddsdata/run.py` (Task 18)
### 14.1 CLI
```python
def main(argv=None, *, now: datetime | None = None) -> int
    # now = now or datetime.now(timezone.utc)   (the only wall clock in core/oddsdata)
    # argparse(exit_on_error=False): --plan PATH (required), --comparison ID, --paths N, --refetch; errors -> 4
    # load_plans(bytes) -> [Plan | Refusal]; for each Plan: ctx = owner.load_context(now,
    # model.Positions(equity_krw=float(plan.stake_krw))); refusal = simulate.precheck(plan, ctx, paths) -> print the
    # refused report, continue; then one begin_run for the passing plans (a ValueError for an unknown --comparison
    # id refuses each of them UNSUPPORTED_PRODUCT sub "comparison", exit 2, nothing written); per plan: inst lookup,
    # bars.load_leg, inputs.calendar_for (KRX/US), inputs.sessions, replay (replay legs), simulate.simulate; print
    # report.render (which raises on a language-guard hit: exit 4)
    # Exit 0 every plan reported, 2 any refused, 4 on any exception (message "crash: <type>: <text>" on stderr)
if __name__ == "__main__":
    raise SystemExit(main())
```
### 14.2 Plan file
`{"schema": "tradegen.odds_plan/1", "plans": [<plan>, ...]}`; a plan object has exactly `name`, `track`, `stake_krw`,
`target_krw`, `fx_krw_per_usd`, `start` ("YYYY-MM-DD"), `horizon_days`, `leg` (or `legs`, a list: MULTI_LEG_UNSUPPORTED
for two or more legs, UNSUPPORTED_PRODUCT sub `file` when it is empty or an item is not a leg object; a one-item list
builds `Plan(leg=<Leg>)`, O3-6), `fraction` ({"kind": "fixed" | "kelly" | "bold", "value": number | null}); a leg
object has `venue`, `symbol`, `model`, `bracket` ({"take_profit", "stop"} or null), `sizing`, `edge_source`,
`assumed_p`. Numbers: int or float, never bool; `load_plans` turns JSON ints for `stake_krw`, `target_krw` and
`fx_krw_per_usd` into floats (O3-6). Anything else (bad JSON, unknown or missing keys, wrong types) ->
UNSUPPORTED_PRODUCT sub `file` for that plan (the whole file when it does not parse).

## 15. `tests/odds_guards.py` (Task 1)
Checkers `(rel, source) -> [hit, ...]`, each with a synthetic positive control, reusing `tests.compliance_guards`
helpers (`_walk`, `_imports`, `CLOCKS`, `NETWORK_MODULES`, `DYNAMIC_MODULES`, `_dynamic_module`,
`FORBIDDEN_MODULES`; the follow-up's merged lists, read at test time with no entry count pinned, so R2-10's `pstats`
and `tracemalloc` bind `core/odds` with no odds change; names under the DRIFT RULE of section 0):
`_core_import_hits` (O1 allowlist; DYNAMIC_MODULES membership through `CG._dynamic_module`), `_core_io_hits` (calls
and modules of section 0), `_clock_hits_in(rel, src, allowed=())`, `_main_hits(rel, src, allowed=())`,
`_reexport_hits`, `_data_import_hits` (oddsdata: FORBIDDEN_MODULES, any `core.engine` module,
`docs.asset_expansion_study` and `asset_expansion_study`, `core.quant.gate_ledger` and `core.ficc.macro_artifacts`
(R2-6), plus `CG._dynamic_hits`), `_unchecked_write_hits` (oddsdata). Tests: `test_core_odds_imports_only_the_allowlist`,
`test_core_odds_reads_no_clock`, `test_core_odds_has_no_main_block`, `test_core_odds_does_no_file_io`,
`test_core_odds_imports_no_package_reexport`, `test_core_odds_is_flat`, `test_package_inits_are_empty`,
`test_oddsdata_raw_words` (`CG._raw_hits` over `core/oddsdata`), `test_oddsdata_never_imports_orders_or_the_study`
(its positive controls include `from core.quant import gate_ledger`, `import core.ficc.macro_artifacts` and `from
core.ficc.macro_artifacts import tree_hash` under `XD`),
`test_oddsdata_clock_only_in_run_main`, `test_oddsdata_writes_only_checked_targets`,
`test_code_closure_holds_no_data_layer` (O1), `test_suite_is_registered_in_run_all_and_readme` (odds twin: `select(...,
suite="odds")` finds `odds/odds_guards/`, and "odds" appears in the help text and README:816 list), and three harness
self-tests mirroring compliance's (hermetic plus temp home armed and seams patched, a real-home change flagged, a
missing or broken module handled and an empty run exits 1). Synthetic offenders are checked under `X =
"core/odds/x.py"` and `XD = "core/oddsdata/x.py"`.

## 16. Numbers verified for this contract (sandbox, `.venv/Scripts/python.exe -I`, 2026-10-24)
- `bold_even(1/1000, p)`: 0.1000% (p 0.50), 0.0816% (0.49), 0.0346% (0.45), 0.0106% (0.40); floor at half the stake,
  x = 21,000/41,979,000 = 1/1999: 0.0400% at p 0.49. Ceilings: 1 in 1,000 and 1 in 1,999.
- `instruments.tick_floor_bp(2005, 5)` = 13.868827930174565; `cost_per_side("KRX_ETF_line", 2005.0, on=2026-11-02)`
  gives bp 13.8688 (source tick_floor) on both sides; tick at 1,999.99 is 1, at 2,000 is 5.
- ETF band at ref 2,005, 30%: raw 1,403.5 / 2,606.5 -> D 1,404 (own tick 1; 1,405 with the reference tick 5), U 2,605.
- Clopper-Pearson: k = 0, n = 1e6, one-sided 95% upper 2.9957277863525433e-06 (`beta.ppf`; 1 - 0.05^(1/n) agrees);
  k = 63: (4.8411e-05, 8.0604e-05) = 1 in 20,656 to 1 in 12,406, point 1 in 15,873 -> "about 1 in 16,000 (between 1 in
  12,000 and 1 in 21,000)"; `binomtest(...).proportion_ci(method="exact")` equals.
- Bracket counts: 616.42 -> 617 (55% vs 50%), 152.52 -> 153 (60%); Kelly at 52.5% even money: 5,523.9 bets.
- Bernstein hand values: v 1, R 10, n 1e6, delta 1e-4 -> 0.004850869883696696; v 0.25, R 1, n 2,000, delta 0.05 ->
  0.038213360783937035.
- KRX cap (1.3/0.7) x 1.3^(n-1): 95.0595 at 16 sessions, 458.834 at 22, 1,008.06 at 25. Re-run here on the shipped
  `holidays_KRX.yaml` (29 closed rows, 2026-01-01..2027-12-31): every half-open 30-day window from 2026-01-01 to
  2027-12-02 (701 starts) holds 16 to 22 sessions; 246 sessions in 2026 and 247 in 2027.
- Correction-table error |c_quad - c_table| over sigma 0.003-0.2: max 1.24e-08 (nu 2.51), 1.04e-08 (nu 2.76), 1.41e-09
  (nu 4.6), all at sigma 0.2; quad costs about 6 ms per sigma.
- S_C3 from the cache: 3,288 rows 2017-09-25..2026-09-25, file md5 de7eaec6f45d0dc12b2950f50433b89d (CRLF, 75,588
  bytes); input canonical md5 18ec83bdfe158efe4d648caf45ff849f; GATE equals the card protocol; sr_oos, bench_sr,
  haircut_sr, bench_diff, bench_ci, n_sessions 2,530 and n_trades 138 equal the card exactly; PASS; chosen 0.667;
  pnl bytes md5 bbdcf17ca9462567fe351c54644bef0c; OOS 2019-10-23..2026-09-25, mean 0.0014832; embargo 0 gives
  1.2172 PASS (inside the tolerance, so the input pins are needed); card md5 40b1e7bfadf6d16246e0012495064704;
  results.csv md5 ca757e25f508b588cb2f361719ec83cd; 4.6 s.

### 16.1 Added on review (sandbox `scratchpad/odds_plan/sandbox_revise_odds/`, 2026-10-24)
- Replay facts (`replay_facts.py`): `oos_turnover` bytes md5 2d4edeb2f042c87fd1750d9c68e275f7 (values 0 and 1);
  `validate.sharpe` of the buy-and-hold returns on the OOS dates equals the card's bench_sr 0.788830441182887 exactly;
  max |g| 0.16899731, max c 0.001. Exact block growth (block 10): the demeaned gross g of the earlier Q38 gives
  E[prod(1 + g)] - 1 = +0.2745% over 30 days and +4.10% over 365 (the trap, measured by the critic at 13 SE on 400,000
  paths), R1 2.9918% over 30 days against 2.7045% for independent days (Monte Carlo 2.967% +/- 0.031%), R 4.84%.
  The card's growth line uses the 29 moves a 30-day replay column makes (h = checks - 1; RULINGS_ROUND3 O3-15, Task
  17): `block_growth(R1, 10, 29) - 1` = 2.889% against `(1 + mean R1)^29 - 1` = 2.613%, printed "2.9%" against
  "2.6%"; the h = 30 value 1.029918 stays the separate `block_growth` pin.
- GARCH corruption (`garch_fix.py`, the contract's fixture fit nu 5.618, and a BTC-like fit nu 5.63): c + 2e-6 per
  node fails check 1 everywhere (max |expm1| 2.0e-6); ratio x 3 fails check 2 (max z 7.4 at 30 steps, 13.9 at 90;
  BTC-like 22.1 and 41.7); zero log drift fails check 2 at 90 steps (6.2; BTC-like 18.6) but not at 30 on the fixture
  (3.8); the clean table passes (check 1 4.9e-12, check 2 max z 2.4 and 1.9).
- Formats (`fmt_check.py`): the outward `fmt_end` never narrows a Clopper-Pearson interval for k in 1..1000 at n = 2e5
  and 1e6 (0 of 2,000); k = 63, n = 1e6 prints "1 in 12,000" to "1 in 21,000"; k = 4,700, n = 2e5 prints 2.2% to 2.5%
  for (2.284%, 2.417%). `fmt_ceiling`: 66.7% (L 21,000, T 52,500; and L 0, T 63,000), 33.4% (T 84,000), 1 in 1,000,
  1 in 1,999, 1.0% (T 4.2 million). `brackets_needed`: 617 (0.55), 153 (0.60), 617 (0.45, two directions alike), inf
  at p = p0, 1,546,291 at 0.501. `fmt_order` at lb 1/1,998.5 and c 1/1,999: "1 in 1,998.5" and "1 in 1,999.0".
- Bold engine (critic's `bold_engine.py`, zero costs, m = 0.5): with a KRW 5,000 minimum P(T) = 5.169% (CI 5.101% to
  5.239%) against the ceiling 6.667%, inside the exact fair-game bracket (W0 - L - min)/(T - L - min) <= P <= (W0 -
  L)/(T - L); with a 1 KRW minimum 6.607% (CI 6.530% to 6.684%) contains it. So the engine test runs with no minimum.
  Engine-run test (RULINGS_ROUND3 O3-9, Task 11): one run, one chunk of 20,000 paths through `OF.chunk(20_000)`
  (T11-3), on `costs.Terms` built directly with every 6.2 field (T11-2). It asserts `col.rungs == (k, k, k, 0, k)`,
  `-1e-6 <= excess <= 0.01` with `excess = col.mean - (k T + (n - k) L) / n`, and that the 99.9% Clopper-Pearson
  interval of k contains the ceiling; there is no second short run. "Leaves no path running" and "some path ends
  within KRW 1 of T" are dropped: a lot of 1e-12 BTC with a KRW 0 minimum never reaches the floor (measured: 0
  AT_FLOOR, 18,692 RUNNING, 1,308 REACHED over 366 days). A failure is a ruling, never a reseed.
- Weekdays: 2026-10-23 Friday, 2026-10-24 Saturday, 2026-12-03 Thursday.

### 16.2 Added for RULINGS_ROUND2 (sandbox `scratchpad/odds_plan/odds/sandbox_round2fold/`, 2026-10-25, `-I -B`)
- KRX stock floor (R2-1, `krx_stock_tax.py`): with the venues ladder swapped in as a test-local tick table
  (`instruments.TICK_TABLES[<key>]` and `INSTRUMENT_BOOKS["KRX_stock_book"] = dataclasses.replace(book,
  tick_table=<key>)`, both restored in `finally`; the book is a frozen dataclass, tick_table None, tax_side "sell"),
  `instruments.cost_per_side("KRX_stock_book", p, on=d, side=s).bp` equals `max(35, tick_floor_bp(p, ladder_tick(p),
  tax_bp=SELL_TAX_BP[d.year] if s == "sell" else 0))` on 156 grid points (26 prices from 1 to 1e6, three 2026 dates,
  both sides), max difference 0.0. At 200 KRW: sell 46.4 bp, buy 35.0 bp. The sell floor is above 35 bp up to 367 KRW,
  the buy floor up to 148 KRW. A 2027 buy gives 35.0; a 2027 sell raises "stock sell tax for 2027 is an owner input";
  a 2026-10-01 fill raises (before the ladder's 2026-10-02). `kappa_bound` over both sides: 35.0 bp at p_min 1,000,
  71.4 bp at p_min 100 (the sell at 100 KRW).
- Provenance copies (R2-6, `prov_copy.py`): the copied `repo_anchor` and `tree_hash` equal `gate_ledger.repo_anchor()`
  and `macro_artifacts.tree_hash()` on the repo (git:5816d3c5..., tree 4d6ad4e557d909ad...) and on a synthetic temp
  root (no .git, a `ref:` HEAD, a detached sha, a non-hex HEAD; a small core/data/config tree); `UNVERSIONED` and
  `TREE_GLOBS` equal the originals.
