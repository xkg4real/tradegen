# Rulings for the odds plan and the compliance follow-up plan (2026-10-24)

Binding inputs for the contract drafters. "Owner" = decided by the owner in chat on 2026-10-24. "Controller" = decided
by the controller (Claude) on the evidence in `map/DIGEST.md`; a drafter may raise a concrete objection with evidence,
but must not silently change one. Spec = `docs/superpowers/specs/2026-10-23-compliance-gate-and-odds-engine-design.md`
rev 3.2. Every departure from the spec below is recorded so it can be folded into spec rev 3.3.

## Order of the plans (controller, DQ26)
1. The compliance follow-up plan runs first (branch `compliance-followup` from main 995534b).
2. The odds plan runs second (branch `odds-engine`, from main after the follow-up merges).
3. No owner key or signature exists yet (owner act 1 is not done), so neither plan costs a re-sign now. Both plans say
   so, and say that once the owner signs `code_approved`, any later change to the closure needs a fresh signature.
4. GPT's final check after 2026-10-30 14:40 may add spec rev 3.3 findings. Neither plan waits for it; a valid finding
   that touches built code becomes a new task with its own failing test.

## Odds plan

### O1 Layout: "everything injected" (OWNER)
- The signed odds core is `core/odds/` and contains ONLY: `__init__.py` (0 bytes), `plan.py`, `costs.py`, `models.py`,
  `simulate.py`, `bold.py`, `report.py` (and `venues.yaml`, data). Spec 4 put `bars.py` here; it moves out (below).
- The signed core may import ONLY: the standard library, `numpy`, `scipy`, `core.isolation`, `core.compliance.*`
  (model, rules, gate, owner as needed), and `core.odds.*`. Nothing else from the repo: not `config`, not `data.*`, not
  `core.quant.*` (garch included), not `core.calendars.*`, not `core.engine.*`, not `core.ficc.*`, not `yfinance`.
  Third-party imports are not hashed (owner.py:739-747), so numpy/scipy add no files; say so plainly as a stated limit
  (a numpy or scipy upgrade changes behaviour without a re-sign).
- Everything the core needs from the repo is either COPIED into the core with an equality test in `tests/` (tests may
  import anything), or COMPUTED by unsigned code and PASSED IN as plain data with its hash:
  - copied: the GARCH-t pieces the core runs (fit, simulate, the martingale correction table) from `core/quant/garch.py`;
    `Z_BOUND` (22); `LIVE_SHARPE_MULTIPLIER` (0.60, gate_stats.py:149); `DELIST_STRESS` (0.30, 1.00; tf_books);
    `LIMIT_DOWN_CARRY_COST_MULTIPLIER` (2.0; read from core/engine/orders.py by AST in the test, never imported);
    the per-book table rates and the tick-floor formula and the KRX ETF tick table from core/quant/instruments.py
    (`cost_per_side`, `tick_floor_bp`, `TICK_TABLES` as needed); the Politis-White block length (`pw_block`, kind
    "stationary") from gate_stats.py. Each copy carries an equality test against the original (same outputs on a grid
    of inputs, or the same constant), so drift in either breaks the suite.
  - passed in (computed by the unsigned package below): bar series (dates, open, close, flags), the session dates and
    the dated KRX price_limit per session, the calendar version and file md5s, the S_C3 replay output, and the
    provenance strings (repo_anchor, tree_hash).
- The unsigned companion package is `core/oddsdata/` (a sibling, NOT inside core/odds, so it is outside the D14 seeds;
  `core.oddsdata.` does not match the acting prefix `core.odds.`). It holds: `bars.py` (loaders, seams, cache),
  `replay.py` (the D13 S_C3 replay), `inputs.py` (sessions, price limits, calendar md5s, provenance), and the CLI
  `run.py` (the only place with a wall clock and the only `__main__`). It may import the data clients, config,
  core.quant, core.calendars, gate_ledger, macro_artifacts. It must never import core.engine.orders (any form),
  core.quant.forward_sim, core.quant.refusal or the context-log modules, and never docs/asset_expansion_study.py.
  It gets its own `__init__.py` (0 bytes).
- The signed core verifies what it can of injected data: shapes, finiteness, positive prices, strictly increasing
  dates, the stated hashes recomputed inside the core from the passed arrays (md5 of canonical JSON per spec 7.2), and
  for the replay: the exact pinned digests and statistics of the validated card (O9). The calendar's session list is
  computed by unsigned code; the core checks the calendar set's sha against the in-force signed approval (O6) and
  records the md5s. State this limit honestly in the plan and in the card's provenance.
- The D14 closure test (`tests/compliance_store.py:137-140`) keeps its intent: the in-repo closure is still exactly
  `core/__init__.py`, `core/isolation.py`, `core/compliance/*.py`, `core/odds/*.py`. Add a test that the closure contains
  no file under `core/oddsdata/`, `data/`, `config.py`, `core/quant/`, `core/calendars/`, `core/engine/`.
- No subfolders under core/odds (a subfolder escapes the D14 seeds, owner.py:773 is non-recursive).

### O2 Odds-own guards (controller, DQ20)
- New `tests/odds_guards.py` with positive controls (a synthetic offender each guard must catch), scanning
  `core/odds/*.py`: the import allowlist of O1 (stdlib minus the compliance NETWORK_MODULES and DYNAMIC_MODULES,
  numpy, scipy, core.isolation, core.compliance.*, core.odds.*; this already excludes every HTTP client, so no
  HTTP-verb check is needed and `np.delete`/`np.put` stay legal); no wall-clock call (same CLOCKS set as
  compliance_guards); no `__main__` block; no file I/O at all (no `open`, `io.open`, `os.open`, `os.replace`,
  `Path.open/read_text/read_bytes/write_text/write_bytes`): venues.yaml and every table reach the core only through
  the sealed Context built by `core.compliance.owner.load_context`; no package re-export imports (import concrete
  submodules only).
- `core/oddsdata/*.py`: no `core.engine.orders` import in any form, no forward_sim/refusal/context-log import, no import
  of `docs.asset_expansion_study`, the wall clock only inside `run.py`'s `main()`; every file write goes through
  `core.isolation.checked_target` (AST check: every `open(..., "w"/"a"/"x"...)`, `write_text`, `write_bytes`,
  `os.replace` target in oddsdata is preceded by checked_target in the same function).
- Leave the compliance guards' scopes alone (they already scan core/odds for raw words, forbidden and dynamic imports).

### O3 Compliance-side prerequisites, done in the odds plan's first tasks (controller, DQ4, DQ5, DQ8, DQ24)
- `core/compliance/rules.py`: extend the venues parser (`_VENUE_OPTIONAL`, `Venue` with defaulted fields, top-level
  keys unchanged unless needed) for the odds keys: `lot` (units step per symbol or default), `min_order` (per quote
  currency, in quote units), `fee_extras` {phi_buy, phi_sell} in KRW (each >= 0: this is `check_extras`, it lives in the
  parser so a negative extra makes the table INVALID), `tick_ladder` (KRX stock: list of [price_from, tick]); strict
  types, every value finite and >= 0, ladders strictly increasing. Update `tests/compliance_tables.py` (the
  `minimum_krw` refusal test at :633 changes to test the new exact key names and an unknown key still refused) and keep
  every byte pin in `tests/compliance_gate.py` (:336-340, :695-697, :998-1000) and the shape pins true.
- Then extend `core/odds/venues.yaml` with ONLY values that have a research source (Upbit KRW 5,000 minimum; the KRX
  stock tick ladder from research_notes E2_nyse_microstructure_execution.md:304-316 with its KRX URL; the KRX ETF tick
  already in instruments). Everything without a source stays absent, which makes that venue/symbol NOT_TRADABLE
  (DQ30). Do NOT add any deposit network (OKX USDT/USDC stays an owner act). The file's sha changes; it needs the
  owner's approval like any table (none exists yet).
- `core/compliance/owner.py`: add a public `calendar_in_force(now) -> str | None` (the sha256 of the in-force signed
  calendar approval, or None), built on the same logic `rules._calendar_line` uses; refactor `_calendar_line` to call
  it. Pure-ish (reads the log like load_context). Tests in tests/compliance_owner.py or compliance_store.py.
- `core/compliance/gate.py`: add a public pure `grey_rows(plan, ctx) -> tuple[str, ...]` (ids of in-force grey rows
  matching the plan's leg as a buy) so GREY_LEG never needs gate privates.
- `tests/compliance_fixtures.py`: move the signed-home helpers (`_pubkey_at/_owner_key/_sign/_approve/_full_home/NOW/
  HELD` from tests/compliance_store.py:242-299) into public fixtures; compliance_store imports them back. Tests only.

### O4 Plan types (controller, DQ23, spec 7.1)
- `plan.py`: `Bracket`, `Leg`, `Plan`, `Fraction` exactly as spec 7.1, kw_only frozen dataclasses with whitelist
  validation and named refusals. Keep the name `Fraction`; bold.py imports `fractions` as a module and writes
  `fractions.Fraction`.
- Whitelist: venue in {kis, upbit, okx} (O7); class share (KRX and US), etp_1x (multiple exactly +1), coin; cash; long;
  single leg. Instrument facts come from the APPROVED instrument map in the Context (never the draft file). Everything
  else is UNSUPPORTED_PRODUCT (with the sub-reason) or MULTI_LEG_UNSUPPORTED.

### O5 review_by and rule dates (OWNER for review_by; controller for the rest; DQ6)
- review_by inside the horizon: from that Asia/Seoul date on, the simulated plan opens no new position (no entry, no
  re-entry) but keeps and may close what it holds; the card prints RULE_CHANGE_IN_HORIZON with the date and the
  sentence that new entries stop then unless the owner re-approves.
- auto_off and effective_until inside the horizon: spec as written (a forced exit at the first check on or after that
  date, and no new entries after it). Test both.
- These dates come from `Screening.flags` (gate.py:643-651).

### O6 Calendar (controller, DQ4, DQ16, DQ27)
- simulate refuses KRX and US legs with CALENDAR_UNSIGNED unless `owner.calendar_in_force(now)` returns a sha AND the
  passed calendar input carries the same sha (computed by unsigned oddsdata with `rules.calendar_sha256`). Crypto legs
  need no calendar.
- A horizon past the calendar's coverage (CalendarCoverageError, after 2027-12-31) is refused with a new named reason
  `CALENDAR_COVERAGE` (stricter; the spec named none).
- Sessions: half-open horizon [start, start + horizon_days); KRX and US move on the passed session dates; crypto daily.
- US bars: the Asia/Seoul date of a US session d is d + 1 day (fixed rule; every US close falls on Seoul D+1, verified
  offline for EST, EDT and early closes). KRW price of a US leg: open_KRW = open_USD x FXclose(d-1), close_KRW =
  close_USD x FXclose(d), with FX = Yahoo "KRW=X" (pin this exact ticker; it is in the series hash). The card lists
  the FX timing approximation under "not in these numbers".
- Finality: drop a last bar that is not final: crypto day d is final at 00:00Z of d+1; KRX at 15:40 KST; US at 16:10
  ET. Fixed instants, no data/macro rules store read.

### O7 Venues and feeds (OWNER, DQ17)
- Upbit: its own KRW-* daily candles (UpbitPublic().daily).
- OKX BTC/USDT: Binance BTCUSDT x Upbit KRW-USDT, falling back to KRW=X before Upbit listed KRW-USDT (found at run time
  from the data and recorded); flagged PROXY_DATA with the dates.
- Refused: OKX BTC/USDC, bithumb, coinone, korbit, and any venue without its own feed and signed minimum (NOT_TRADABLE
  or UNSUPPORTED_PRODUCT with a named sub-reason).
- KIS: KRX shares and 1x ETFs from KIS daily rows (paged, 100 per call, opens/closes <= 0 or None dropped); US shares
  and 1x ETFs from yfinance (auto_adjust=True, explicit start/end) through the seam `bars._yf_download`.

### O8 SPECIAL_REGIME (OWNER, DQ21)
- Refuse a KRX leg with SPECIAL_REGIME when the symbol's first available bar is fewer than 60 KRX sessions before the
  plan's start. Resets and other special reference-price regimes are listed under "not in these numbers".

### O9 The D13 replay (controller, DQ13, DQ29)
- `core/oddsdata/replay.py` replays S_C3 from the committed cache `docs/asset_expansion/cache/upbit_KRW-BTC.csv` (read
  with csv; never import docs/asset_expansion_study.py): strategies.pnl_matrix -> validate.walk_forward(dates[1:],
  embargo=1) -> score_strategy(n_trials=11, seed=11, domain={"hysteresis": (0.0, 0.889)}, bench=buy-and-hold on
  wf.dates). It returns plain data: the OOS net daily returns, dates, the statistics, the exact inputs/protocol it
  used, and digests (input canonical (dates, closes) md5; replayed pnl md5 = bbdcf17ca9462567fe351c54644bef0c;
  results.csv md5 ca757e25...).
- The signed core (models.py) pins every card input and protocol value (lookbacks (7,14,21,28), mas (10,20,50,100,
  200), embargo 1, cost_bps_per_side 10, n_trials 11, seed 11, the hysteresis domain, validate.GATE == card.protocol
  as passed) AND the exact digests AND the statistics (OOS Sharpe 1.216 +/- 0.02, PASS, final chosen hysteresis
  0.667). Any mismatch is CARD_NOT_REPRODUCED. The +/-0.02 tolerance alone does not catch embargo 1->0 (1.2172), so the
  exact-input pins are mandatory.
- A live pull is NOT part of the replay (the cache's 2026-09-25 row was a running price). Optional later.
- mu_lb: stationary block bootstrap (geometric blocks with mean exactly 10), B = 2,000, seed stream "kelly" from the
  market seed. The TESTED_REPLAY column resamples the OOS net returns in stationary blocks with mean 10, mean scaled by
  LIVE_SHARPE_MULTIPLIER (write `1 - LIVE_SHARPE_MULTIPLIER` nowhere near the word Sharpe on one line with "0.4 *": a
  core-wide guard T-TF-GOV-06 scans for "0.4 *" on live/haircut/Sharpe lines).
- Kelly: f* = argmax over [0, 1] of mean ln(1 + f R_cons); decide boundaries by the derivative sign (on the real replay
  f* sits at the upper bound 1); f* = 0 when mu_lb <= 0.

### O10 Models, statistics, simulator (controller, DQ11, DQ12, DQ14, DQ28, DQ31)
- pw_block: the copied stationary pw_block; b = max(pw(r), pw(r^2)), floored at 1; sensitivity b' = max(1,
  round(mult x b)), capped at the history length.
- The stationary bootstrap index generator is new, vectorised (CHUNK x H draws from N rows), Politis-Romano.
- Band rounding per edge: D rounds UP to the tick valid at D's price level, U rounds DOWN to the tick valid at U's
  level, then clamp D <= reference <= U. Test the ETF ref 2,005 case (lower edge 1,405).
- GARCH pilot: 20,000 pilot paths from the stream "pilot"; check 1 (deterministic): for the distinct sigma values on
  the pilot paths, binned to at most 512 quantile nodes, |exp(c_quad - c_table) - 1| <= 1e-7 per step and the sum over
  the horizon of |c_quad - c_table| <= 1e-6 (the compounded check), c_quad by scipy.integrate.quad; check 2
  (statistical): for every step h, |mean over paths of exp(cumulative r up to h) - 1| <= 4 SE_h. Corruption test:
  monkeypatch the copied correction table in core/odds/models.py.
- Empirical Bernstein: sample variance with ddof = 1 (Maurer-Pontil), R is the full range (both tails), pinned against
  hand values in a unit test.
- CHUNK is a module constant (200,000); tests swap it with save/restore (to e.g. 2,000) and one full-size test runs at
  the real value; the "multiple of CHUNK" refusal is tested at the real value.
- Refusal order (DQ32): product checks (plan.py) -> owner state and LIMITS_UNSET -> CALENDAR_UNSIGNED /
  CALENDAR_COVERAGE -> data refusals (SYNTHETIC_REFUSED, NOT_TRADABLE, SPECIAL_REGIME) -> model eligibility
  (MODEL_NOT_FOR_LIMITED_VENUE) -> sizing (STUCK_AT_START) -> screen (gate BLOCK). The first refusal is reported; the
  card never prints a probability for a refused run.

### O11 Stakes, equity, costs (controller, DQ7, DQ9, DQ30)
- `Positions(equity_krw=W)` with W = the plan's stake (the simulation does not know the owner's other equity); every
  simulated OKX entry is capped at `ctx.owner.caps["okx_equity_share"] x W` (the cap the gate would apply), stated on
  the card. Pass `float(stake)` to screen (a numpy float is malformed); never screen a zero stake: STUCK_AT_START first.
- kappa per fill: KRX ETF books via the copied cost_per_side logic (per-fill tick floor; 2,005 KRW -> >= 13.8688 bp);
  KRX_stock_book: max(35 bp table, copied tick_floor_bp with the signed venues ladder, tax 0 inside the floor because the
  table rate already includes the sell tax); US_shares_KIS and crypto_venue: the copied table rate exactly as
  core/quant/instruments.py has it (the map read 35 / 3 / 50 / 10 bp for KRX_stock_book / KRX_ETF_line /
  US_shares_KIS / crypto_venue at price=None; the drafter re-reads instruments.py and copies the real values and their
  date validity), with NO tick floor until a tick is signed in venues.yaml. Never add a separate sell tax. A fill dated outside the copied table's
  validity raises inside the copy exactly as the original does (NotTradable) and becomes NOT_TRADABLE.
- Missing minimum, lot or fee extras for a venue/symbol: NOT_TRADABLE. An explicit signed 0 is allowed.

### O12 Seeds and persisted odds state (controller, DQ22)
- Market seed = sha256(data hashes || calendar digest || comparison id || run counter) per spec 7.3; streams are
  SeedSequence(int.from_bytes(seed, "big"), spawn_key=(chunk, stream_id)).
- The comparison id and run counter, and the K plans / J typed win rates counts, persist in a small JSON under
  `core.isolation.state_root()/odds/` written by `core/oddsdata/` (the unsigned side) with checked_target and an
  atomic replace; the signed core receives them as inputs. A comparison = one CLI invocation (or one explicit
  `--comparison` id).

### O13 Cache, seams, harness (controller, DQ2, DQ3, DQ14, DQ15, DQ18, DQ19, DQ24, DQ25)
- Bars cache under `core.isolation.state_root()/"odds"/"bars"`, computed at call time; files written with the
  grokteam write_cached pattern (checked_target on the file, its .tmp and MANIFEST.jsonl; os.replace; sha256 line);
  keyed by (source, symbol, start, end); pinned by window and hash; refetch on request; its own switch (env
  `TRADEGEN_ODDS_BARS_CACHE=0` disables), not FICC_CACHE_TTL_SECONDS.
- yfinance: call `yfinance.set_tz_cache_location(<state_root>/odds/yfinance)` before first use, inside the seam.
- Seams: module-level functions in core/oddsdata/bars.py (`_kis_daily`, `_upbit_daily`, `_binance_daily`,
  `_yf_download`), each importing its client inside, looked up at call time. The odds suite patches them in
  `tests/odds_acceptance._wrap` (odds-local, save/restore, `_boom` refusal), not in macro_acceptance._touchpoints; add
  one odds probe test proving an unpatched seam call is refused under the suite.
- Suite: `tests/odds_acceptance.py` mirrors compliance_acceptance.py (MODULES tuple, `_wrap` with hermetic() and
  temp_home()). Register in tests/run_all.py (CRLF) and README (CRLF). The brittle literal at
  tests/compliance_guards.py:488-489 is loosened by the follow-up plan (F7), so the odds plan only adds "odds" to the
  help text and README list.
- Test files are `tests/odds_*.py` (never `macro_*`), fixtures in code or under a new `tests/fixtures/odds/`. The S_C3
  cache file is committed already and is the replay fixture.
- `core/odds/__init__.py` and `core/oddsdata/__init__.py` are 0 bytes. The sentence catalogue is constants in report.py.
- Test budget: the odds suite should finish in about 3 minutes; state per-test budgets; the full suite gains that.

### O14 Report (spec 7.5, controller)
- Everything spec 7.5 lists, from one catalogue in report.py with numeric slots; the language guard bans the whole
  words of spec 7.5 (case-insensitive, whole-word; note "floor-safe" contains "safe": the catalogue must not contain
  the token "safe" as a whole word, so the sizing label renders as "floor-protected sizing" or similar, and the guard
  treats "floor-safe" only as an internal name that never renders). Internal names never render.
- The card prints the stated limits of "everything injected": unsigned data loading, the calendar session list from
  unsigned code checked by sha, numpy/scipy outside the hash.

### O15 CLI (controller)
- `python -m core.oddsdata.run --plan <plan.json> [--comparison <id>] [--paths N]`: loads context (load_context with
  Positions(equity_krw=stake)), loads bars and inputs, runs simulate, prints the rendered report text (UTF-8 stdout).
  Exit 0 report, 2 refused (prints the named reason), 4 crash. It never writes the owner log.

## Compliance follow-up plan

Scope (controller rulings on the parked/deferred items in `map/followup.md`):
- F1 Guards (tests/compliance_guards.py only): replace "xml.dom.pulldom", "xml.dom.expatbuilder" with "xml.dom" in
  NETWORK_MODULES; move `from xml.dom import minidom` from the negative control to the positive list; rewrite the
  docstring; add to DYNAMIC_MODULES: profile, pdb, bdb, trace, doctest, unittest, logging.config, pickle, _pickle,
  shelve, marshal, site, ensurepip, venv, tkinter, _tkinter, turtle, turtledemo, idlelib; add to NETWORK_MODULES:
  antigravity, ctypes, _ctypes, _ssl, _overlapped; ban every importlib submodule except importlib.metadata; ban the
  bare Name `compile` (not attributes, so re.compile stays legal). Keep negative controls (logging, xml.etree,
  importlib.metadata, subprocess). Document pstats, tracemalloc, faulthandler as not needing a ban. Every new entry gets
  a positive control. Re-check core/compliance and core/odds still pass.
- F2 Loader (core/compliance/rules.py `_row` + tests/compliance_tables.py): the D15 content rule (an allow, gated or grey
  row may not match financing credit or margin, nor action lend or borrow); the D16-by-content companion (a non-blocking
  row whose action includes sell_short, or whose class or asset includes etp_leveraged, etp_single_stock,
  krx_derivative or elw, needs requires.live); a row citing D15 must be blocking; loader bounds (review_by not before
  the row's last_reviewed; max_leverage <= 10; the {cap} slot only in grey warnings); exact pins of
  (match, requires_owner, requires_live, treatment) for all 15 shipped non-blocking rows. The shipped table must stay
  VALID and byte-identical.
- F3 KR-KIS-KRX-DERIV reason text: mention broker approval (kr_rules.yaml:204). This changes the table sha (no approval
  exists yet).
- F4 D14 closure scan hardening: `_skipped` in owner.py and its copy in tools/signer/sign.py: count a guard as skipped
  only if `typing` is bound exactly once by an import and `__name__` is never rebound in the module; identical in both
  files; test_code_files_match_owner keeps them in step.
- F5 Signer ancestor walk fails closed when a parent pid has exited or the walk ends before the root (repo copy only;
  the plan hands updating the owner's own copy to the owner as an owner act: read the diff, re-hash, re-record).
- F6 alerts.py records a key fingerprint only from a summary whose code is 0, 1 or 2 (never from 3 or 4); test.
- F7 tests/compliance_guards.py:483-489: replace the literal "paper, grokteam or compliance" check with a check that
  "compliance" appears in the run_all.py --suite help list and in README's suite list (so adding suites never breaks
  it).
- F8 Data-layer minors from A0: the KIS token is POSTed before checked_target can refuse its write (kis_client.py:181 vs
  :195; ledger:81): compute the checked target before the POST; ficc `_cache_put` sets `_MEM` before checked_target
  (data.py:273-274; ledger:82): check first. Tests in the existing isolation tests.
- Not in scope (documented in the plan): H2 (moves to E2, the halt writer, with a trusted clock); T2 (a documented limit:
  it needs the owner's own key and a backdated clock); snapshot cross-check (within spec 6.4's stated limits); every
  other item on the execution carry list (ledger:239, :244, :155).
- Final task: full suite run, README count row (CRLF), ledger file `docs/superpowers/plans/2026-10-24-compliance-followup-execution-ledger.md` is written by the executor later, not by the plan.
