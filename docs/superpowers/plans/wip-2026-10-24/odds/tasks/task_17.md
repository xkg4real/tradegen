### Task 17: The D13 replay, Kelly and the replay card (`core/oddsdata/replay.py`, `core/odds/models.py`, `core/odds/simulate.py`)

**Files:**
- Create: `core/oddsdata/replay.py` (LF, UTF-8, no BOM; unsigned: outside the D14 seeds)
- Modify: `core/odds/models.py` (anchor: the end of the file, after the last definition Task 8 left; append only; LF,
  kept)
- Modify: `core/odds/simulate.py` (anchors: the def line of `_run_paths` and the def line of `run_column` (Task 9);
  the module docstring's "Not simulated yet" sentence (Task 9, as Task 10 rewrote it); inside `simulate` (Task 13)
  the step-10 placeholder branch, the `costs.first_stake` call and the final `return _accepted_report(` statement;
  the end of the file (two appended blocks); LF, kept)
- Modify: `tests/odds_simulate.py` (created by Task 9, edited by Task 10 and this task; anchor: the `cases` tuple of
  Task 9's `test_rules_this_engine_does_not_simulate_fail_closed`, its `engine="replay"` entry; LF, kept)
- Modify: `tests/odds_pipeline.py` (created by Task 13, edited by Task 14 and this task; anchor: Task 13's test
  `test_replay_legs_are_refused_until_the_replay_is_built`, which Task 14 does not edit, replaced whole; LF, kept)
- Checked, not edited: `core/odds/report.py` (Task 12 already renders every replay card line; Step C3 checks it)
- Test: `tests/odds_replay.py` (create; LF; `odds_replay` is already in `tests/odds_acceptance.MODULES`, Task 1)

None of these files is touched by the compliance follow-up (each is created by this plan), so the follow-up's DRIFT
RULE cannot apply. Every old text below is quoted from the current drafts of Tasks 9, 10, 13 and 14; the same rule
holds for them: re-read the file before each Edit, and if an earlier task's review changed the quoted text only in
ways that keep its meaning (a comment, a wrapped line, an extra keyword argument), make the same change to the
current text, keep the earlier task's behaviour, and record a one-line ruling under "Drift rulings" in the execution
ledger `docs/superpowers/plans/2026-10-24-odds-engine-execution-ledger.md`. If an anchor is gone or the change no
longer makes sense, stop and rule.

**Interfaces:**
- Consumes:
  - Task 5 (`core.odds.plan`): `ReplayInput` (fields of CONTRACT 5.2), `Inputs` (`replay`, `series`, `sessions`,
    `calendar_sha256`, `comparison_id`, `run_counter`, `comparison_plans`, `comparison_typed`, `plan_runs`), `Plan`,
    `Leg`, `Refusal`, `Series`, `fixed(f)`, `kelly(c)`, `REPLAY_SOURCE` (`"replay:S_C3_crypto_trend_krwbtc"`),
    `plan_hash(plan)`.
  - Task 6 (`core.odds.costs`): `Terms` (fields of CONTRACT 6.2), `COST_STRESS` (2.0), `rule_units(fraction, cash, p,
    *, terms, on, mult, target, w0, take_profit, stop, sizing, floor, fstar, cap_krw) -> (units, at_floor)` (a kelly
    stake needs `fstar`; ValueError otherwise), `first_stake(plan, terms, ctx, p0, on, *, fstar=None)` (sizes a
    replay leg at mult 0.0, R2-5).
  - Task 7 (`core.odds.models`): `LIVE_SHARPE_MULTIPLIER`, `sharpe(daily)`, `indices(rng, n_rows, n_paths, block)`
    (endless; ValueError for a block that is not a finite number >= 1), `data_hashes(series, replay)`,
    `market_seed(...)`, `stream(seed, chunk, name, *extra)` (`STREAMS` holds `"kelly"`, `"replay"` and
    `"replay_sign"`), and the private digests `_input_md5(rep)` (md5 of the canonical JSON {symbol, source, dates,
    close}) and `_array_md5(values)` (md5 of the `"<f8"` bytes). The import block holds `hashlib`, `numpy as np` and
    `from core.compliance import model`; `core.odds.plan` is imported for annotations only, which is all part 3 uses.
  - Task 9 (`core.odds.simulate`): `CHUNK`, `PathSpec` (the replay fields `replay_move`, `replay_cost`; `engine`
    "replay"), `checks(market, sessions, close_only) -> Checks`, `run_column(spec, *, n, seed, key, member,
    scenario)`, `_run_paths(spec, *, n, chunk, seed)`, and the fail-closed `_check_spec` (`engine 'replay' is not
    simulated`, which this task routes around and does not change).
  - Task 11: `bold.ceiling(w0, l_min, target)`.
  - Task 12 (`core.odds.report`): `ColumnStats` (CONTRACT 10.1), `LADDER`, `replay_range(*, target, a_max, c_max,
    n_checks)`, `hidden_edge(col, *, w0, target, l_min)` (`not_applicable` for a `tested_replay` key),
    `ceiling_cells(cols, ceiling)`, `flags_for(*, headline, no_edge, engine, hidden, ceiling, structural, target,
    stake, reference, rule_flags, grey, series, okx)`, `build(**fields)`, `render(rep)`, `say(key, **slots)`, and
    the replay card's rendering: `_replay_lines`, the `tested_replay/base` branch of `_column_lines`, and `_card`'s
    `replay.noedge` (after the model line) and `kelly.label` (when `replay["fstar"]` is finite).
  - Task 13 (`core.odds.simulate`, `simulate()` and its helpers): the local `replay` (`leg.edge_source ==
    plan.REPLAY_SOURCE`), `_headline_spec(plan_obj, ctx, inputs, *, terms, market, sessions, screening) ->
    PathSpec`, `_grey_slots(plan_obj, ctx)`, `_report_provenance(plan_obj, ctx, inputs, *, screening, seed, n,
    members)`, `_accepted_report(...)`, `_refused_report(...)`; the fixtures `OF.pipeline(plan_obj=None, ctx=None,
    series_obj=None, *, n_paths=None, **changes)`, `OF.pipeline_inputs(plan_obj, series_obj, **changes)`,
    `OF.fresh_series(n=600, *, end="2026-10-22", **changes)`, `OF.spy(target, name)` (a context manager yielding
    the list of `(args, kwargs, result)` of every call); and the test module's names `REPLAY`, `F`, `OF`,
    `report`, `_no_probability`.
  - Tasks 1 and 5 (`tests/odds_fixtures.py`): `chunk()`, `plan(**changes)`, `odds_ctx(**overrides)`,
    `venues_with(**changes)` (a `None` value removes that odds key from the venue); `tests.compliance_fixtures`:
    `approved(venues=...)`, `temp_home()`; `tests.compliance_guards._imports(rel, tree)`.
  - The repo, read only, from the unsigned side: `core.quant.strategies.crypto_trend`, `.pnl_matrix`;
    `core.quant.validate.walk_forward`, `.score_strategy`, `.GATE`; the committed files
    `docs/asset_expansion/cache/upbit_KRW-BTC.csv` (CRLF, 3,288 rows), `docs/asset_expansion/cards/
    S_C3_crypto_trend_krwbtc.json`, `docs/asset_expansion/results.csv`.
- Produces:
  - `core/oddsdata/replay.py` (CONTRACT 13): `REPO`, `CACHE`, `CARD`, `RESULTS`, `LOOKBACKS`, `MAS`, `DOMAIN`,
    `replay_s_c3(*, lookbacks=LOOKBACKS, mas=MAS, embargo: int | None = None) -> plan.ReplayInput`, and the private
    `_SYMBOL = "KRW-BTC"`, `_SOURCE = "UPBIT"`, `_HEADER`. Task 18's CLI calls `replay_s_c3()` for a replay leg and
    passes the result as `Inputs.replay`.
  - `core/odds/models.py` part 3 (CONTRACT 7.5): `CARD_ID`, `REPLAY_PINS`, `KELLY_B`, `KELLY_BLOCK`, `KELLY_Q`,
    `verify_replay(rep) -> str | None` (None, or the first failing item's name: `card_id`, `input_symbol`,
    `input_source`, `n_input`, `input_first`, `input_last`, `lookbacks`, `mas`, `grid`, `cost_bps_per_side`,
    `embargo`, `n_trials`, `seed`, `domain`, `protocol`, `gate_protocol`, `input_md5`, `pnl_md5`, `turnover_md5`,
    `results_md5`, `card_md5`, `n_oos`, `oos_first`, `oos_last`, `oos_turnover`, `sr_oos`, `decision`,
    `chosen_last`, `haircut_rule`, `haircut_sr`, `bench_sr`, `bench_diff`, `bench_ci`, `n_trades`, `n_sessions`,
    `bench_recompute`; never raises, whatever object it is passed: one that is not a ReplayInput gives `card_id`;
    `oos_turnover` is kept because CONTRACT 7.5 lists it, though `turnover_md5` already refuses any length change),
    `_bench_sr(rep) -> float`, `mu_lb(r, rng) -> float`, `kelly_fstar(r, lb) -> float`, `replay_returns(rep) -> (a,
    c, r1)` (ValueError "replay: a daily move could empty the sleeve ..."), `block_growth(r, block, h) -> float` (h
    >= 0; 1.0 at h = 0).
  - `core/odds/simulate.py` part 5a: `_check_replay_spec(spec)`, `_run_replay(spec, *, n, chunk, seed) -> dict` (keys
    `v`, `cost`, `x`, `outcome`, `fp`, `entered`, `stops`, `held`, `slack`), `_replay_column(spec, *, n, seed, key,
    member, scenario) -> report.ColumnStats`; `run_column` and `_run_paths` become dispatchers in front of Task 9's
    bodies, renamed `_price_column` and `_run_price_paths`. Part 5b: the private `_REPLAY_KEYS =
    ("replay_no_edge/base", "replay_no_edge/stress2x", "tested_replay/base")`, `_replay_refusal(inputs) ->
    plan.Refusal | None` (detail `"replay: missing"` or `"replay: <item>"`), `_replay_fstar(plan_obj, inputs) -> float
    | None`, `_replay_report(plan_obj, ctx, inputs, *, inst, terms, market, sessions, screening, n, fstar) ->
    report.OddsReport`. The replay card's report: `headline == "replay_no_edge/base"`, `columns` in `_REPLAY_KEYS`
    order, `spread None`, `spread_kind "none"`, `model_key "model.replay"`, `model_slots {first, last, rows, block}`,
    `replay {y0, y1, cut, bench_sr, haircut_sr, diff, ci_lo, ci_hi, fstar (nan for a fixed stake), h, growth,
    growth_iid}` with h the number of daily moves a held sleeve makes (the checks less one: 29 on a 30-day horizon),
    provenance `model "replay"`, `members ()`.
  - `tests/odds_replay.py`: 24 tests (14 + 5 + 5 over three cycles) and the helpers `_real`, `_replay_plan`, `_spec`,
    `_card`, `_no_fee_ctx`, `_study_imports`; `tests/odds_pipeline.py`'s
    `test_replay_legs_are_checked_against_their_card_at_step_10` replaces Task 13's placeholder test.

**Plan decisions used:** Q9 (O9: the replay from the committed cache with csv, never the study runner; every input,
protocol value, digest and statistic pinned; CARD_NOT_REPRODUCED on any mismatch; mu_lb from stationary blocks of mean
10, B = 2,000, stream `kelly`; f* by the derivative sign at the boundary, then bisection; f* = 0 when mu_lb <= 0),
Q38 (the fair-sign no-edge kernel on the replay's own block-resampled magnitudes at base and 2x costs, the tested
column R1 in blocks of mean 10, the floor-protected sleeve at mult 0.0, the replay card's flags), Q32 (L_min = L on a
replay leg; HIDDEN_EDGE on `replay_no_edge/base` with the range fixed before the run; CEILING_BREACH over the two
no-edge cells), Q25 and R2-5 (a replay leg needs only the signed Upbit lot and minimum), Q24 (CARD_NOT_REPRODUCED is
step 10), Q26 (daily loss, rule dates, REACHED, AT_FLOOR, re-entry at a later check), Q34 (the market seed),
Q46 item 4 (the replay no-edge column is a departure accepted by R2-3), Q42 (no I/O or clock in the core).

What this task does and why (read before Step A1):
- **The replay (unsigned).** `replay_s_c3` reads the committed Upbit cache with `csv` (3,288 closes, 2017-09-25 to
  2026-09-25) and the S_C3 card with `json`, and re-runs the study's three steps exactly as `strategy_card` of
  `docs/asset_expansion_study.py` runs them: `strategies.pnl_matrix(closes, crypto_trend(lookbacks, mas), card grid,
  cost 10 bp)`,
  `validate.walk_forward(..., embargo=1)` with the card's protocol, and `validate.score_strategy(..., n_trials=11,
  seed=11, domain={"hysteresis": (0.0, 0.889)})` against buy-and-hold on the OOS dates. It never imports the study
  runner, makes no live pull (O9: the cache's last row was a running price) and writes nothing. `lookbacks`, `mas` and
  `embargo` exist only so a test can change one constant and watch the core refuse it; the CLI never passes them.
- **The pins (signed).** `verify_replay` checks, in this order, the card id, every input and protocol value
  (`protocol == gate_protocol ==` the pins, so the study's QUICK `bootstrap_B` 300 is refused), the digests it can
  recompute from the passed arrays (input, pnl, turnover) and the two file md5s it cannot (results, card: compared
  only; `limits.injected` says so), the shape, the statistics (the OOS Sharpe recomputed by the core equals the
  passed one and lies within 1.216 +/- 0.02, PASS, chosen hysteresis 0.667, haircut = 0.6 x Sharpe within 1e-12,
  and bench_sr, bench_diff, bench_ci, haircut_sr, n_trades, n_sessions exactly equal to the card's), and last the
  core's own buy-and-hold Sharpe from the passed closes (equal to the pin exactly). The tolerance alone would pass
  embargo 0 (its Sharpe is 1.2172), so the input pins are what refuse it (O9).
- **Kelly.** `mu_lb` is the 5th percentile of 2,000 stationary-bootstrap means (mean block 10, Task 7's generator);
  `kelly_fstar` maximises mean ln(1 + f rc) over [0, 1] with rc = r - mean(r) + 0.6 mu_lb. On the real replay g'(1) > 0,
  so f* is exactly 1.0, decided at the boundary (O9); a demeaned series has mu_lb < 0 and f* = 0.
- **The no-edge replay columns.** Each day a held sleeve becomes sleeve x (1 + eps a - c) with a = |G - mean G|
  (G = pnl + c, the card's own cost c = 10 bp x turnover), the row from stationary blocks of mean 10 and a fair sign
  eps from the separate stream `replay_sign`; c x the sleeve is booked as cost. So cash + sleeve + costs is an exact
  martingale at every check, under any stopping rule. The earlier construction (a demeaned block bootstrap of g) is
  not: g has autocorrelation 0.07, so a stop rule harvests it; the negative-control test shows its gain at about 11
  standard errors. The tested column moves the sleeve by R1 = pnl - mean + 0.6 mean in the same blocks. Max a is
  0.169 and max c 0.001, so no sleeve can reach 0 (`replay_returns` checks it, and min R1 > -1 for the tested column).
- **The replay engine.** Close checks only, one per crypto day; the sleeve is the rule stake of `costs.rule_units` at
  mult 0.0 with the zero-charge replay terms (so it never exceeds cash - L, and L_min = L), rounded down to whole
  1e-8 BTC lots at the leg's last close; exits in priority target (moonshot), daily loss, rule date; re-entry after a
  daily-loss stop at the next check by the same rule; no entry at the last check or from the first rule date on.
  `_run_paths` and `run_column` become two-line dispatchers in front of Task 9's bodies, so Task 9's fail-closed
  `_check_spec` stays exactly as Task 10 left it (Tasks 9 and 10 say the same: this task routes engine "replay"
  around it and leaves the clause unchanged) and only the text of its `engine="replay"` test case changes.
- **The replay card.** `simulate()` keeps Task 13's refusal order: the placeholder at step 10 becomes the real check,
  Kelly's f* is computed only after it passes (the first stake needs it; the seed it uses is step 7's, built from
  the same inputs), and after the gate a replay leg returns `_replay_report`, which reuses Task 13's `_headline_spec`
  (stake, owner limits, p0, rule dates), `_grey_slots` and `_report_provenance`, and never reaches Task 14's GARCH
  fits, spread members, delisting or assumed columns.
- **The report.** Task 12 already renders the replay card (`replay.noedge` after the model line, `kelly.label` for a
  Kelly stake, then `replay.lead`, `replay.growth`, the edge-column average, `ceiling.edge` and `hidden.na` at the head
  and foot of the tested column), so `report.py` is not edited; `test_the_replay_card_renders_its_lines_in_order`
  pins the rendered text: 0.79, 0.73, +0.43, +0.03 to +0.83, 40%, "2.9%" against "2.6%" over 29 days, and the
  ceiling line "1 in 1,999" under the tested column.
- **29 moves on a 30-day horizon (the 29-move reading, accepted in place of the earlier 30-day figures; CONTRACT Q38
  and 16.1 and TASKS Task 17 state it, and the plan header's "For spec rev 3.3" list carries it as a departure).**
  Entries follow the move at each check (CONTRACT 8.4 step 5) and the replay checks closes only, so the sleeve
  enters at the first close and moves at the 29 later ones (`out["held"] == 29`, pinned by the reference test of
  Cycle B). The growth line therefore prints the column the engine runs: `block_growth(R1, 10, 29) - 1` = 2.889%
  against `(1 + mean R1)^29 - 1` = 2.613% ("2.9%" against "2.6%" over 29 days). The earlier "2.99% against 2.70% at
  H = 30" is `block_growth` at h 30, a column no engine runs, and it errs in the strategy's favour; its value
  1.029918 stays the separate `block_growth` pin of
  `test_block_growth_is_exact_and_matches_a_monte_carlo_of_the_same_generator`. Entering before the first move
  instead would change 8.4 for every engine, so it is not done. If an executor finds CONTRACT Q38 or 16.1 still
  printing the 30-day figures, this task's text holds (it is what the engine runs): one ledger line, no change to
  `_replay_report` or its tests.
- **Budget.** A replay takes about 4.6 s unloaded (score_strategy's CSCV is most of it). `_real()` keeps the first
  one, and the embargo test scores its Sharpe through the replay's own `pnl_matrix` and `walk_forward` without the
  CSCV. Task 1's runner takes a module's tests in sorted name order (`sorted(vars(module).items())`), so the whole
  module runs exactly three replays: the first `_real()` inside `test_a_replay_leg_needs_only_the_upbit_lot_and_minimum`
  (sorted first), then the determinism twin and the lookbacks 30 one; about 17 s in all unloaded. Run alone
  (`odds_replay/<test name>`), `test_replay_is_deterministic_on_the_committed_cache` and
  `test_lookbacks_28_to_30_is_refused_by_its_input_its_digest_and_its_stats` each run two replays (about 10 s
  unloaded; 23.7 s was measured with parallel agents loading the CPU). A loaded machine that goes over the 15 s
  per-test or 20 s module budget (Q13, CONTRACT 3.4) is not a failure: record the time in the ledger's "Runs"
  (RULINGS_ROUND3 G3-2).
- **Code hash.** `models.py` and `simulate.py` are D14 closure files, so the code hash moves. No `code_approved`
  exists yet (owner act 2 is not done), so nothing is re-signed now; once the owner signs, any later closure change
  needs a fresh signature before new exposure is allowed again. `core/oddsdata/replay.py` is unsigned (O1).

Overlap check (Global Constraints): before EVERY Python command below, run the Git Bash prefix

```bash
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && <command>
```

  It must print nothing (otherwise wait for QUANTGEN's suite to finish). All commands run from the repo root in Git
  Bash.

#### Cycle A: the replay and the core's pins, Kelly and block growth

- [ ] **Step A1: Write the failing tests**

  Create `tests/odds_replay.py` (LF, UTF-8, no BOM) with exactly this content (the header holds every helper of the
  module; Cycles B and C only append tests):

```python
"""Odds suite: the D13 replay, Kelly and the replay card (odds plan Task 17; spec 7.1 "kelly", 7.2 "replay", 7.5
item 9, 8.o items 1, 2, 6 and 7; O9; R2-5; Q9, Q32, Q38).

A replay of the committed cache takes about 5 s, so `_real()` keeps the first one for every test that only reads
it. In the runner's sorted order the module runs exactly three replays (the first inside
test_a_replay_leg_needs_only_the_upbit_lot_and_minimum, then the determinism twin and the lookbacks 30 one); run
alone, the determinism and lookbacks tests run two each. Engine and card tests run under `OF.chunk()` (2,000 paths
per chunk)."""
from __future__ import annotations

import ast
import dataclasses
import datetime
import functools
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np

from core.odds import costs, models, plan, report, simulate
from core.oddsdata import replay as RP
from tests import compliance_fixtures as F
from tests import compliance_guards as CG
from tests import odds_fixtures as OF

ROOT = Path(__file__).resolve().parents[1]
PINS = models.REPLAY_PINS
SEED = b"\x07" * 32
SESSIONS = tuple(datetime.date(2026, 10, 23) + datetime.timedelta(days=i) for i in range(30))
UPBIT = costs.Terms(venue="upbit", symbol="BTC", book="crypto_venue", quote="KRW", lot=1e-8, min_quote=5000.0,
                    min_krw=5000.0, phi_buy=0.0, phi_sell=0.0, ladder=None, ladder_from=None, quote_krw=1.0)
STUDY = ("docs.asset_expansion_study", "asset_expansion_study")


@functools.lru_cache(maxsize=1)
def _real() -> plan.ReplayInput:
    """The replay of the committed cache, run once per process (treat it as frozen: edit copies only)."""
    return RP.replay_s_c3()


def _replay_plan(fraction: plan.Fraction | None = None) -> plan.Plan:
    """The replay leg (Q25): Upbit BTC, model field bootstrap, floor-protected, no bracket, 30 days, kelly(0.5)."""
    leg = plan.Leg(venue="upbit", symbol="BTC", model="bootstrap", edge_source=plan.REPLAY_SOURCE)
    return OF.plan(leg=leg, fraction=fraction or plan.kelly(0.5), horizon_days=30)


def _spec(*, track: str = "compounding", target: float = 45_000.0, daily_loss: float = 1e12,
          fraction: plan.Fraction | None = None, tested: bool = False, stress: bool = False) -> simulate.PathSpec:
    """A replay PathSpec on the real replay's moves (Q38): W0 42,000, floor 21,000, p0 50,000,000, 30 daily close
    checks from 2026-10-23, the zero-charge Upbit terms, mult 0.0, the card's block 10."""
    a, c, r1 = models.replay_returns(_real())
    move, cost = (r1, None) if tested else (a, costs.COST_STRESS * c if stress else c)
    return simulate.PathSpec(
        track=track, w0=42_000.0, target=target, floor=21_000.0, daily_loss=daily_loss, p0=50_000_000.0,
        engine="replay", m_o=None, m_i=None, block=10.0, replay_move=move, replay_cost=cost,
        checks=simulate.checks("CRYPTO", SESSIONS, True), limits=np.full(len(SESSIONS), np.nan), terms=UPBIT,
        mult=0.0, bracket=None, sizing="floor_safe", fraction=fraction or plan.fixed(1.0), fstar=None, cap_krw=None,
        stop_entries_from=None, force_exit_from=None, delist_h=None)


def _card(ctx=None, fraction: plan.Fraction | None = None, **changes) -> report.OddsReport:
    """simulate() on the replay plan through OF.pipeline under OF.chunk() (OF.odds_ctx() unless a context is given);
    the inputs carry the real replay unless `changes` replace it (replay=None, or an edited copy)."""
    with OF.chunk():
        return OF.pipeline(_replay_plan(fraction), ctx, **{"replay": _real(), **changes})


def _no_fee_ctx(*drop: str):
    """OF.odds_ctx on venues whose upbit entry has no fee_extras, and none of `drop` either (R2-5)."""
    raw = OF.venues_with(upbit={key: None for key in ("fee_extras", *drop)})
    return OF.odds_ctx(active=F.approved(venues=raw))


# --------------------------------------------------------------------------- #
# The pins, the replay and verify_replay (8.o item 7; Q9)
# --------------------------------------------------------------------------- #
def test_replay_pins_are_the_card_files_and_the_contract_values():
    card_bytes = (ROOT / "docs/asset_expansion/cards/S_C3_crypto_trend_krwbtc.json").read_bytes()
    card = json.loads(card_bytes)
    st = card["stats"]
    assert models.CARD_ID == card["card_id"] and plan.REPLAY_SOURCE == "replay:" + models.CARD_ID
    for key in ("bench_sr", "bench_diff", "haircut_sr", "n_trades", "n_sessions"):
        assert PINS[key] == st[key], key
    assert PINS["bench_ci"] == tuple(st["bench_ci"]) and st["decision"] == PINS["decision"] == "PASS"
    assert st["chosen_last"] == {"hysteresis": PINS["chosen_last"]} and abs(st["sr_oos"] - 1.216) <= PINS["sr_tol"]
    assert PINS["grid"] == tuple(g["hysteresis"] for g in card["rules"]["grid"])
    rules = card["rules"]
    assert (PINS["cost_bps_per_side"], PINS["embargo"]) == (rules["cost_bps_per_side"], rules["embargo"])
    assert (PINS["n_trials"], PINS["seed"]) == (card["trials"]["N_total"], card["seed"])
    assert PINS["protocol"] == card["protocol"]
    assert (PINS["input_first"], PINS["input_last"], PINS["n_input"]) == (card["data"]["start"], card["data"]["end"],
                                                                         card["data"]["sessions"])
    assert PINS["card_md5"] == hashlib.md5(card_bytes).hexdigest() == "40b1e7bfadf6d16246e0012495064704"
    results = (ROOT / "docs/asset_expansion/results.csv").read_bytes()
    assert PINS["results_md5"] == card["results_md5"] == hashlib.md5(results).hexdigest()
    cache = (ROOT / "docs/asset_expansion/cache/upbit_KRW-BTC.csv").read_bytes()
    assert hashlib.md5(cache).hexdigest() == "de7eaec6f45d0dc12b2950f50433b89d" and len(cache) == 75_588
    assert (PINS["input_md5"], PINS["pnl_md5"], PINS["turnover_md5"]) == (
        "18ec83bdfe158efe4d648caf45ff849f", "bbdcf17ca9462567fe351c54644bef0c", "2d4edeb2f042c87fd1750d9c68e275f7")
    assert (PINS["lookbacks"], PINS["mas"]) == (RP.LOOKBACKS, RP.MAS) == ((7, 14, 21, 28), (10, 20, 50, 100, 200))
    assert PINS["domain"] == RP.DOMAIN["hysteresis"] == (0.0, 0.889)
    assert (PINS["n_oos"], PINS["oos_first"], PINS["oos_last"]) == (2530, "2019-10-23", "2026-09-25")


def test_replay_is_deterministic_on_the_committed_cache():
    assert RP.replay_s_c3() == _real()              # two runs give the same ReplayInput, field by field


def test_verify_replay_accepts_the_real_replay_and_every_pin_holds():
    rep = _real()
    assert models.verify_replay(rep) is None
    assert models._input_md5(rep) == PINS["input_md5"]
    assert models._array_md5(rep.oos_pnl) == PINS["pnl_md5"]
    assert models._array_md5(rep.oos_turnover) == PINS["turnover_md5"]
    assert (rep.results_md5, rep.card_md5) == (PINS["results_md5"], PINS["card_md5"])
    assert (len(rep.input_dates), rep.input_dates[0], rep.input_dates[-1]) == (3288, "2017-09-25", "2026-09-25")
    assert (len(rep.oos_dates), rep.oos_dates[0], rep.oos_dates[-1]) == (2530, "2019-10-23", "2026-09-25")
    assert set(rep.oos_turnover) == {0.0, 1.0} and rep.protocol == rep.gate_protocol == PINS["protocol"]
    assert models.sharpe(rep.oos_pnl) == rep.stats["sr_oos"] == 1.2160250195674127
    for key in ("bench_sr", "bench_diff", "haircut_sr", "n_trades", "n_sessions", "decision", "chosen_last"):
        assert rep.stats[key] == PINS[key], key
    assert tuple(rep.stats["bench_ci"]) == PINS["bench_ci"]


def test_lookbacks_28_to_30_is_refused_by_its_input_its_digest_and_its_stats():
    rep, real = RP.replay_s_c3(lookbacks=(7, 14, 21, 30)), _real()
    assert rep.stats["sr_oos"] != real.stats["sr_oos"] and models._array_md5(rep.oos_pnl) != PINS["pnl_md5"]
    assert models.verify_replay(rep) == "lookbacks"
    relabelled = dataclasses.replace(rep, lookbacks=PINS["lookbacks"])
    assert models.verify_replay(relabelled) == "pnl_md5"                 # the digest catches the changed rule
    borrowed = dataclasses.replace(relabelled, oos_dates=real.oos_dates, oos_pnl=real.oos_pnl,
                                   oos_turnover=real.oos_turnover)
    assert models.verify_replay(borrowed) == "sr_oos"                    # and the statistics do too


def test_embargo_zero_is_refused_by_the_input_pin_although_its_sharpe_is_inside_the_tolerance():
    from core.quant import strategies, validate     # the replay's own steps, scored by Sharpe only (no CSCV)
    real = _real()
    px = np.asarray(real.input_close, dtype=float)[:, None]
    fn = functools.partial(strategies.crypto_trend, lookbacks=real.lookbacks, mas=real.mas)
    grid = [{"hysteresis": h} for h in real.grid]
    m, m_stress, turnover = strategies.pnl_matrix(px, fn, grid, cost_bps=real.cost_bps_per_side)

    def sr(embargo: int) -> float:
        wf = validate.walk_forward(m, real.input_dates[1:], turnover=turnover, pnl_stress=m_stress,
                                   w_is=real.protocol["w_is"], w_oos=real.protocol["w_oos"],
                                   min_is=real.protocol["min_is"], embargo=embargo)
        return validate.sharpe(wf.pnl)

    assert sr(1) == real.stats["sr_oos"]                                 # the same steps as the replay
    assert round(sr(0), 4) == 1.2172 and abs(sr(0) - PINS["sr_oos"]) <= PINS["sr_tol"]   # inside the tolerance
    assert models.verify_replay(dataclasses.replace(real, embargo=0)) == "embargo"       # so the input pin refuses


def test_each_edited_item_is_refused_by_name():
    rep = _real()
    st, close, pnl, turn = dict(rep.stats), list(rep.input_close), list(rep.oos_pnl), list(rep.oos_turnover)
    close[100] += 1.0
    pnl[7] += 1e-12
    turn[3] = 1.0 - turn[3]
    cases = {
        "card_id": {"card_id": "S_C3_crypto_trend_btcusd"}, "input_symbol": {"input_symbol": "KRW-ETH"},
        "input_source": {"input_source": "BINANCE"},
        "n_input": {"input_dates": rep.input_dates[:-1], "input_close": rep.input_close[:-1]},
        "input_first": {"input_dates": ("2017-09-24",) + rep.input_dates[1:]},
        "input_last": {"input_dates": rep.input_dates[:-1] + ("2026-09-26",)},
        "lookbacks": {"lookbacks": (7, 14, 21, 30)}, "mas": {"mas": (10, 20, 50, 100, 201)},
        "grid": {"grid": (0.0, 0.222, 0.444, 0.667, 0.888)}, "cost_bps_per_side": {"cost_bps_per_side": 20.0},
        "embargo": {"embargo": 0}, "n_trials": {"n_trials": 5}, "seed": {"seed": 12}, "domain": {"domain": (0.0, 1.0)},
        "protocol": {"protocol": {**rep.protocol, "block": 20}},
        "gate_protocol": {"gate_protocol": {**rep.gate_protocol, "bootstrap_B": 300}},
        "input_md5": {"input_close": tuple(close)}, "pnl_md5": {"oos_pnl": tuple(pnl)},
        "turnover_md5": {"oos_turnover": tuple(turn)}, "results_md5": {"results_md5": "0" * 32},
        "card_md5": {"card_md5": "f" * 32}, "n_oos": {"oos_dates": rep.oos_dates[:-1]},
        "oos_first": {"oos_dates": ("2019-10-22",) + rep.oos_dates[1:]},
        "oos_last": {"oos_dates": rep.oos_dates[:-1] + ("2026-09-26",)},
        "sr_oos": {"stats": {**st, "sr_oos": math.nextafter(st["sr_oos"], math.inf)}},
        "decision": {"stats": {**st, "decision": "REVISE"}},
        "chosen_last": {"stats": {**st, "chosen_last": 0.444}},
        "haircut_rule": {"stats": {**st, "haircut_sr": st["haircut_sr"] + 1e-9}},
        "haircut_sr": {"stats": {**st, "haircut_sr": math.nextafter(st["haircut_sr"], math.inf)}},
        "bench_sr": {"stats": {**st, "bench_sr": math.nextafter(st["bench_sr"], math.inf)}},
        "bench_diff": {"stats": {**st, "bench_diff": math.nextafter(st["bench_diff"], math.inf)}},
        "bench_ci": {"stats": {**st, "bench_ci": (st["bench_ci"][0], math.nextafter(st["bench_ci"][1], math.inf))}},
        "n_trades": {"stats": {**st, "n_trades": 139}}, "n_sessions": {"stats": {**st, "n_sessions": 2529}},
        "bench_recompute": {"oos_dates": rep.oos_dates[:5] + (rep.input_dates[600],) + rep.oos_dates[6:]},
    }
    for name, changes in cases.items():
        assert models.verify_replay(dataclasses.replace(rep, **changes)) == name, name
    missing = {k: v for k, v in st.items() if k != "bench_ci"}
    assert models.verify_replay(dataclasses.replace(rep, stats=missing)) == "bench_ci"      # never a KeyError
    assert models.verify_replay(dataclasses.replace(rep, input_dates=(), input_close=())) == "n_input"
    assert models.verify_replay(object()) == "card_id"                  # nor an AttributeError


def test_the_core_recomputes_bench_sr_exactly():
    from core.quant import validate
    rep = _real()
    assert models._bench_sr(rep) == PINS["bench_sr"] == rep.stats["bench_sr"]
    close = np.asarray(rep.input_close, dtype=float)
    simple = dict(zip(rep.input_dates[1:], close[1:] / close[:-1] - 1.0))
    assert validate.sharpe(np.array([simple[d] for d in rep.oos_dates])) == PINS["bench_sr"]
    edited = list(rep.input_close)
    edited[rep.input_dates.index(rep.oos_dates[5])] *= 1.01             # one close inside the OOS window
    assert models._bench_sr(dataclasses.replace(rep, input_close=tuple(edited))) != PINS["bench_sr"]


def _study_imports(rel: str, src: str) -> list[str]:
    """Every import in `src` that names the study runner, in any form."""
    hits = []
    for node, module, names, _funcs in CG._imports(rel, ast.parse(src)):
        targets = [module] + [f"{module}.{n}" for n in names]
        if any(t == s or t.startswith(s + ".") for t in targets for s in STUDY):
            hits.append(f"{rel}:{node.lineno}: {module}")
    return hits


def test_the_study_runner_is_never_imported():
    for bad in ("import docs.asset_expansion_study", "from docs import asset_expansion_study",
                "from docs.asset_expansion_study import run_crypto_trend", "import asset_expansion_study as s"):
        assert _study_imports("core/oddsdata/x.py", bad), bad                # positive controls
    hits = []
    for pkg in ("core/odds", "core/oddsdata"):
        for path in sorted((ROOT / pkg).glob("*.py")):
            hits += _study_imports(f"{pkg}/{path.name}", path.read_text(encoding="utf-8"))
    assert hits == [], hits
    _real()
    assert not [name for name in STUDY if name in sys.modules]


# --------------------------------------------------------------------------- #
# Kelly (8.o item 7; Q9)
# --------------------------------------------------------------------------- #
def test_kelly_is_zero_when_mu_lb_is_not_positive():
    r = np.asarray(_real().oos_pnl, dtype=float)
    demeaned = r - r.mean()
    lb = models.mu_lb(demeaned, models.stream(SEED, 0, "kelly"))
    assert lb < 0.0 and models.kelly_fstar(demeaned, lb) == 0.0
    for lb in (0.0, -1e-6, math.nan):
        assert models.kelly_fstar(r, lb) == 0.0


def test_kelly_fstar_stays_in_the_unit_interval_and_maximises_the_log_growth():
    rng = np.random.default_rng(17)
    cases = [(rng.normal(rng.uniform(-0.01, 0.01), rng.uniform(0.001, 0.3), int(rng.integers(50, 500))),
              float(rng.uniform(1e-5, 0.02))) for _ in range(200)]
    planted = rng.normal(0.002, 0.02, 300)
    planted[10] = -1.5                                                   # below -1 after the shift
    cases.append((planted, 0.001))
    shifted_below = 0
    for r, lb in cases:
        f = models.kelly_fstar(r, lb)
        rc = r - r.mean() + models.LIVE_SHARPE_MULTIPLIER * lb
        shifted_below += bool(rc.min() <= -1.0)
        f_hi = 1.0 if rc.min() > -1.0 else 0.999 / float(np.max(-rc))
        assert 0.0 <= f <= f_hi <= 1.0 and np.all(1.0 + f * rc > 0.0)
        grid = np.linspace(0.0, f_hi, 201)
        best = max(float(np.mean(np.log1p(g * rc))) for g in grid)
        assert float(np.mean(np.log1p(f * rc))) >= best - 1e-12
    assert shifted_below >= 1


def test_kelly_fstar_on_the_real_replay_is_one_at_the_upper_boundary():
    r = np.asarray(_real().oos_pnl, dtype=float)
    seed = models.market_seed(models.data_hashes(OF.fresh_series(), _real()), "", "c000001", 1)
    lb = models.mu_lb(r, models.stream(seed, 0, "kelly"))
    assert lb == models.mu_lb(r, models.stream(seed, 0, "kelly")) and 0.0 < lb < r.mean()
    rc = r - r.mean() + models.LIVE_SHARPE_MULTIPLIER * lb
    assert rc.min() > -1.0 and float(np.mean(rc / (1.0 + rc))) > 0.0     # g'(1) > 0: the boundary decides
    assert models.kelly_fstar(r, lb) == 1.0


# --------------------------------------------------------------------------- #
# The replay's moves, their exact block growth and the trap they avoid (8.o item 1; Q38)
# --------------------------------------------------------------------------- #
def test_replay_returns_bound_every_sleeve():
    rep = _real()
    a, c, r1 = models.replay_returns(rep)
    pnl = np.asarray(rep.oos_pnl)
    assert set(np.unique(c)) == {0.0, 0.001} and round(float(a.max()), 6) == 0.168997
    assert float(a.max()) + 2.0 * float(c.max()) < 1.0 and float(r1.min()) > -1.0
    assert abs(r1.mean() - models.LIVE_SHARPE_MULTIPLIER * pnl.mean()) < 1e-15
    planted = list(rep.oos_pnl)
    planted[0] = 1.5
    try:
        models.replay_returns(dataclasses.replace(rep, oos_pnl=tuple(planted)))
    except ValueError as exc:
        assert "could empty the sleeve" in str(exc)
    else:
        raise AssertionError("a move of 150% was accepted")


def test_block_growth_is_exact_and_matches_a_monte_carlo_of_the_same_generator():
    r1 = models.replay_returns(_real())[2]
    exact = models.block_growth(r1, 10.0, 30)
    assert round(exact, 6) == 1.029918 and round((1.0 + r1.mean()) ** 30, 4) == 1.0270
    assert abs(models.block_growth(r1, 1.0, 30) / (1.0 + r1.mean()) ** 30 - 1.0) < 1e-12   # block 1: iid days
    assert models.block_growth(r1, 10.0, 0) == 1.0                      # no move, no growth
    paths = 200_000
    rows = models.indices(models.stream(SEED, 0, "replay"), r1.size, paths, 10.0)
    value = np.ones(paths)
    for _ in range(30):
        value *= 1.0 + r1[next(rows)]
    se = float(value.std(ddof=1)) / math.sqrt(paths)
    assert abs(float(value.mean()) - exact) <= 4.0 * se, (value.mean(), exact, se)


def test_negative_control_a_demeaned_block_bootstrap_with_a_stop_gains_without_an_edge():
    """The earlier construction (spec 7.2's trap): the demeaned gross g resampled in blocks of mean 10 keeps the
    series' autocorrelation, so a rule that exits after a day below -3% and re-enters the next day gains."""
    rep = _real()
    c = rep.cost_bps_per_side * 1e-4 * np.asarray(rep.oos_turnover)
    g = np.asarray(rep.oos_pnl) + c
    g = g - g.mean()
    paths = 100_000
    rows = models.indices(models.stream(SEED, 0, "replay"), g.size, paths, 10.0)
    value, hold = np.ones(paths), np.ones(paths, dtype=bool)
    for _ in range(30):
        step = g[next(rows)]
        value = np.where(hold, value * (1.0 + step), value)
        hold = ~(hold & (step < -0.03))
    se = float(value.std(ddof=1)) / math.sqrt(paths)
    assert float(value.mean()) - 1.0 > 4.0 * se, (value.mean(), se)
```

- [ ] **Step A2: Run to verify it fails**

```bash
.venv/Scripts/python.exe -m tests.odds_acceptance odds_replay/
```

  Expected: one FAIL line after its traceback,

```
FAIL odds_replay/import ImportError: cannot import name 'replay' from 'core.oddsdata' (...\core\oddsdata\__init__.py)
```

  and `0/1 passed, 1 failed, 0 not run` (exit code 1). Any other error (for example a NameError in a fixture, or an
  import error of `core.odds`) means an earlier task's name differs from the contract: stop and rule.

- [ ] **Step A3: Implement**

  A3a. Check that none of part 3's names exists yet and that Task 7's do:

```bash
grep -nE "^(CARD_ID|REPLAY_PINS|KELLY_B|KELLY_BLOCK|KELLY_Q) = |^def (verify_replay|mu_lb|kelly_fstar|replay_returns|block_growth|_bench_sr)\(" core/odds/models.py
grep -cE "^def (_input_md5|_array_md5|indices|sharpe|market_seed|data_hashes|stream)\(|^LIVE_SHARPE_MULTIPLIER = " core/odds/models.py
grep -cE "^import hashlib$|^import numpy as np$|^from core\.compliance import model$" core/odds/models.py
ls core/oddsdata/replay.py
```

  The first prints nothing; the second prints `8`; the third prints `3`; `ls` reports no such file. If Task 7 named
  its digests differently, use its names in part 3 and in the tests (DRIFT RULE, one ledger line).

  A3b. Create `core/oddsdata/replay.py` (LF, UTF-8, no BOM):

```python
"""The D13 replay of S_C3 from the committed study cache (odds plan Task 17; spec 7.2 "replay"; O9, Q9).

Unsigned: it reads the cached Upbit KRW-BTC closes and the S_C3 card, re-runs the study's own three steps
(`strategies.pnl_matrix`, `validate.walk_forward`, `validate.score_strategy`) and returns plain data. The signed core
(`core.odds.models.verify_replay`) checks every input, digest and statistic against its pins; any mismatch is
CARD_NOT_REPRODUCED. No network, no write, no clock; the study runner `docs/asset_expansion_study.py` is never
imported, and no live pull is made (the cache's last row was a running price, O9).
"""
from __future__ import annotations

import csv
import functools
import hashlib
import json
from pathlib import Path

import numpy as np

from core.odds import plan
from core.quant import strategies, validate

REPO = Path(__file__).resolve().parents[2]
CACHE = REPO / "docs/asset_expansion/cache/upbit_KRW-BTC.csv"
CARD = REPO / "docs/asset_expansion/cards/S_C3_crypto_trend_krwbtc.json"
RESULTS = REPO / "docs/asset_expansion/results.csv"
LOOKBACKS = (7, 14, 21, 28)
MAS = (10, 20, 50, 100, 200)
DOMAIN = {"hysteresis": (0.0, 0.889)}
_SYMBOL = "KRW-BTC"
_SOURCE = "UPBIT"
_HEADER = ["", "upbit_KRW-BTC"]


def replay_s_c3(*, lookbacks=LOOKBACKS, mas=MAS, embargo: int | None = None) -> plan.ReplayInput:
    """Replay S_C3 on the cached closes with the card's own grid, cost, protocol, trials, seed and embargo.
    `lookbacks`, `mas` and `embargo` exist so a test can change one constant and watch the core refuse it; the CLI
    never passes them. About 5 s (score_strategy's CSCV is most of it)."""
    with CACHE.open(encoding="utf-8", newline="") as fh:
        rows = list(csv.reader(fh))
    if not rows or rows[0] != _HEADER:
        raise ValueError(f"replay: {CACHE.name} starts with {rows[:1]}, expected {_HEADER}")
    dates = tuple(r[0] for r in rows[1:])
    close = tuple(float(r[1]) for r in rows[1:])
    card_bytes = CARD.read_bytes()
    card = json.loads(card_bytes)
    rules, protocol, grid = card["rules"], card["protocol"], card["rules"]["grid"]
    used_embargo = rules["embargo"] if embargo is None else embargo
    fn = functools.partial(strategies.crypto_trend, lookbacks=tuple(lookbacks), mas=tuple(mas))
    px = np.asarray(close, dtype=float)[:, None]
    m, m_stress, turnover = strategies.pnl_matrix(px, fn, grid, cost_bps=rules["cost_bps_per_side"])
    wf = validate.walk_forward(m, dates[1:], turnover=turnover, pnl_stress=m_stress, w_is=protocol["w_is"],
                               w_oos=protocol["w_oos"], min_is=protocol["min_is"], embargo=used_embargo)
    simple = dict(zip(dates[1:], px[1:, 0] / px[:-1, 0] - 1.0))      # buy-and-hold, as the study's benchmark
    bench = np.array([simple[d] for d in wf.dates])
    sc = validate.score_strategy(wf, grid=grid, full_pnl=m, n_trials=card["trials"]["N_total"], bench_daily=bench,
                                 seed=card["seed"], domain=DOMAIN)
    return plan.ReplayInput(
        card_id=card["card_id"], input_symbol=_SYMBOL, input_source=_SOURCE, input_dates=dates, input_close=close,
        oos_dates=tuple(wf.dates), oos_pnl=tuple(float(x) for x in wf.pnl),
        oos_turnover=tuple(float(x) for x in wf.turnover),
        lookbacks=tuple(int(k) for k in lookbacks), mas=tuple(int(k) for k in mas),
        grid=tuple(float(g["hysteresis"]) for g in grid), cost_bps_per_side=float(rules["cost_bps_per_side"]),
        embargo=int(used_embargo), n_trials=int(card["trials"]["N_total"]), seed=int(card["seed"]),
        domain=tuple(float(x) for x in DOMAIN["hysteresis"]),
        protocol=dict(protocol), gate_protocol={k: validate.GATE[k] for k in protocol},
        stats={"sr_oos": float(sc.sr_oos), "bench_sr": float(sc.bench_sr), "haircut_sr": float(sc.haircut_sr),
               "bench_diff": float(sc.bench_diff), "bench_ci": tuple(float(x) for x in sc.bench_ci),
               "decision": sc.decision, "chosen_last": float(grid[wf.chosen[-1]]["hysteresis"]),
               "n_sessions": int(sc.n_sessions), "n_trades": int(sc.n_trades)},
        results_md5=hashlib.md5(RESULTS.read_bytes()).hexdigest(), card_md5=hashlib.md5(card_bytes).hexdigest())
```

  A3c. Append part 3 to `core/odds/models.py` with the Edit tool: `old_string` is the file's last non-empty line
  exactly as it stands (Task 8's last line; add the lines above it until it is unique), `new_string` is that same
  text followed by two empty lines and the block below. Keep LF. The block adds no import.

```python
# --------------------------------------------------------------------------- #
# Part 3 (Task 17): the D13 pins and their check, Kelly, the replay's moves and their block growth (Q9, Q38)
# --------------------------------------------------------------------------- #
CARD_ID = "S_C3_crypto_trend_krwbtc"
REPLAY_PINS = {
    "input_symbol": "KRW-BTC", "input_source": "UPBIT", "n_input": 3288,
    "input_first": "2017-09-25", "input_last": "2026-09-25",
    "input_md5": "18ec83bdfe158efe4d648caf45ff849f",     # md5 of canonical_json({"symbol", "source", "dates", "close"})
    "lookbacks": (7, 14, 21, 28), "mas": (10, 20, 50, 100, 200), "grid": (0.0, 0.222, 0.444, 0.667, 0.889),
    "cost_bps_per_side": 10.0, "embargo": 1, "n_trials": 11, "seed": 11, "domain": (0.0, 0.889),
    "protocol": {"w_is": 756, "w_oos": 126, "min_is": 504, "ci_level": 0.9, "bootstrap_B": 2000, "block": 10},
    "n_oos": 2530, "oos_first": "2019-10-23", "oos_last": "2026-09-25",
    "pnl_md5": "bbdcf17ca9462567fe351c54644bef0c",       # md5 of np.ascontiguousarray(oos_pnl, dtype="<f8").tobytes()
    "turnover_md5": "2d4edeb2f042c87fd1750d9c68e275f7",  # the same bytes md5 of oos_turnover (values 0 or 1)
    "results_md5": "ca757e25f508b588cb2f361719ec83cd", "card_md5": "40b1e7bfadf6d16246e0012495064704",
    "sr_oos": 1.216, "sr_tol": 0.02, "decision": "PASS", "chosen_last": 0.667,
    "bench_sr": 0.788830441182887, "bench_diff": 0.4271945783845257,
    "bench_ci": (0.03344352887529298, 0.8346050647267628), "haircut_sr": 0.7296150117404476,
    "n_trades": 138, "n_sessions": 2530}                  # the card's own stats (cards/S_C3_crypto_trend_krwbtc.json)
KELLY_B = 2_000
KELLY_BLOCK = 10.0
KELLY_Q = 0.05


def _bench_sr(rep: plan.ReplayInput) -> float:
    """The core's own buy-and-hold Sharpe: simple close-to-close returns over consecutive input dates, taken on the
    out-of-sample dates (the card's bench_sr, recomputed from the passed closes)."""
    close = np.asarray(rep.input_close, dtype=float)
    simple = dict(zip(rep.input_dates[1:], close[1:] / close[:-1] - 1.0))
    return sharpe(np.array([simple[d] for d in rep.oos_dates]))


def verify_replay(rep: plan.ReplayInput) -> str | None:
    """None when the passed replay reproduces the validated card; else the name of the first item that does not, in
    the order: card id, inputs and protocol, digests, shape, statistics, the core's own bench_sr. Never raises: the
    replay comes from unsigned code, so any other object fails its first item. The results and card md5s are of
    file bytes unsigned code read: they are compared with the pins, never recomputed here."""
    pins, st = REPLAY_PINS, getattr(rep, "stats", None)
    checks = (
        ("card_id", lambda: rep.card_id == CARD_ID),
        ("input_symbol", lambda: rep.input_symbol == pins["input_symbol"]),
        ("input_source", lambda: rep.input_source == pins["input_source"]),
        ("n_input", lambda: len(rep.input_dates) == len(rep.input_close) == pins["n_input"]),
        ("input_first", lambda: rep.input_dates[0] == pins["input_first"]),
        ("input_last", lambda: rep.input_dates[-1] == pins["input_last"]),
        ("lookbacks", lambda: tuple(rep.lookbacks) == pins["lookbacks"]),
        ("mas", lambda: tuple(rep.mas) == pins["mas"]),
        ("grid", lambda: tuple(rep.grid) == pins["grid"]),
        ("cost_bps_per_side", lambda: rep.cost_bps_per_side == pins["cost_bps_per_side"]),
        ("embargo", lambda: rep.embargo == pins["embargo"]),
        ("n_trials", lambda: rep.n_trials == pins["n_trials"]),
        ("seed", lambda: rep.seed == pins["seed"]),
        ("domain", lambda: tuple(rep.domain) == pins["domain"]),
        ("protocol", lambda: dict(rep.protocol) == pins["protocol"]),
        ("gate_protocol", lambda: dict(rep.gate_protocol) == pins["protocol"]),
        ("input_md5", lambda: _input_md5(rep) == pins["input_md5"]),
        ("pnl_md5", lambda: _array_md5(rep.oos_pnl) == pins["pnl_md5"]),
        ("turnover_md5", lambda: _array_md5(rep.oos_turnover) == pins["turnover_md5"]),
        ("results_md5", lambda: rep.results_md5 == pins["results_md5"]),
        ("card_md5", lambda: rep.card_md5 == pins["card_md5"]),
        ("n_oos", lambda: len(rep.oos_dates) == len(rep.oos_pnl) == pins["n_oos"]),
        ("oos_first", lambda: rep.oos_dates[0] == pins["oos_first"]),
        ("oos_last", lambda: rep.oos_dates[-1] == pins["oos_last"]),
        ("oos_turnover", lambda: len(rep.oos_turnover) == len(rep.oos_pnl)),   # 7.5; turnover_md5 fires first
        ("sr_oos", lambda: sharpe(rep.oos_pnl) == st["sr_oos"]
         and abs(st["sr_oos"] - pins["sr_oos"]) <= pins["sr_tol"]),
        ("decision", lambda: st["decision"] == pins["decision"]),
        ("chosen_last", lambda: st["chosen_last"] == pins["chosen_last"]),
        ("haircut_rule", lambda: abs(st["haircut_sr"] - LIVE_SHARPE_MULTIPLIER * st["sr_oos"]) <= 1e-12),
        ("haircut_sr", lambda: st["haircut_sr"] == pins["haircut_sr"]),
        ("bench_sr", lambda: st["bench_sr"] == pins["bench_sr"]),
        ("bench_diff", lambda: st["bench_diff"] == pins["bench_diff"]),
        ("bench_ci", lambda: tuple(st["bench_ci"]) == pins["bench_ci"]),
        ("n_trades", lambda: st["n_trades"] == pins["n_trades"]),
        ("n_sessions", lambda: st["n_sessions"] == pins["n_sessions"]),
        ("bench_recompute", lambda: _bench_sr(rep) == pins["bench_sr"]),
    )
    for name, ok in checks:
        try:
            if not ok():
                return name
        except (AttributeError, KeyError, IndexError, TypeError, ValueError):
            return name
    return None


def mu_lb(r: np.ndarray, rng: np.random.Generator) -> float:
    """Kelly's mu_lb: the KELLY_Q quantile of KELLY_B stationary-bootstrap means of r (mean block KELLY_BLOCK)."""
    r = np.asarray(r, dtype=float)
    gen = indices(rng, r.size, KELLY_B, KELLY_BLOCK)
    total = np.zeros(KELLY_B)
    for _ in range(r.size):
        total += r[next(gen)]
    return float(np.quantile(total / r.size, KELLY_Q))


def kelly_fstar(r: np.ndarray, lb: float) -> float:
    """argmax over [0, 1] of mean ln(1 + f rc), rc = r - mean(r) + LIVE_SHARPE_MULTIPLIER lb (spec 7.1); 0.0 when
    lb <= 0. The log is concave, so the upper end is decided by the sign of the derivative there and an interior
    maximum by 60 bisection steps; the upper end is 0.999 / max(-rc) when some rc is at or below -1."""
    if not lb > 0.0:
        return 0.0
    r = np.asarray(r, dtype=float)
    rc = r - r.mean() + LIVE_SHARPE_MULTIPLIER * lb

    def slope(f: float) -> float:
        return float(np.mean(rc / (1.0 + f * rc)))

    f_hi = 1.0 if float(rc.min()) > -1.0 else 0.999 / float(np.max(-rc))
    if slope(f_hi) >= 0.0:
        return f_hi
    lo, hi = 0.0, f_hi
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if slope(mid) >= 0.0:
            lo = mid
        else:
            hi = mid
    return lo


def replay_returns(rep: plan.ReplayInput) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(a, c, R1) of Q38: the no-edge magnitudes |G - mean G| with G = pnl + c (signed later by the replay_sign
    stream), the card's own cost c on each out-of-sample day, and the tested returns with their mean scaled by
    LIVE_SHARPE_MULTIPLIER. ValueError unless max a + 2 max c < 1 and min R1 > -1, so no sleeve goes below 0."""
    pnl = np.asarray(rep.oos_pnl, dtype=float)
    c = rep.cost_bps_per_side * 1e-4 * np.asarray(rep.oos_turnover, dtype=float)
    gross = pnl + c
    a = np.abs(gross - gross.mean())
    r1 = pnl - pnl.mean() + LIVE_SHARPE_MULTIPLIER * pnl.mean()
    if not (float(a.max()) + 2.0 * float(c.max()) < 1.0 and float(r1.min()) > -1.0):
        raise ValueError(f"replay: a daily move could empty the sleeve (max a {a.max():.4f}, max c {c.max():.4f}, "
                         f"min R1 {r1.min():.4f})")
    return a, c, r1


def block_growth(r: np.ndarray, block: float, h: int) -> float:
    """Exact E[prod over h steps of (1 + r[I_t])] under the stationary bootstrap of `indices` (I_0 uniform; each
    later step moves to (I + 1) mod n with probability 1 - 1/block, else restarts uniformly), in O(h n); 1.0 for
    h = 0 (a sleeve that never moves)."""
    if h == 0:
        return 1.0
    r = np.asarray(r, dtype=float)
    v = 1.0 + r
    for _ in range(h - 1):
        v = (1.0 + r) * ((1.0 - 1.0 / block) * np.roll(v, -1) + (1.0 / block) * v.mean())
    return float(v.mean())
```

- [ ] **Step A4: Run to verify it passes**

```bash
.venv/Scripts/python.exe -m tests.odds_acceptance odds_replay/
```

  Expected: 14 PASS lines and `14/14 passed, 0 failed, 0 not run`. Then `-m tests.odds_acceptance odds_models/` (Task
  7's tests, unchanged) ends with no FAIL line.

#### Cycle B: the replay engine

- [ ] **Step B1: Write the failing tests**

  Append to `tests/odds_replay.py` with the Edit tool: `old_string` is the file's last line,
  `    assert float(value.mean()) - 1.0 > 4.0 * se, (value.mean(), se)`, and `new_string` is that same line followed by
  two empty lines and the block below:

```python
# --------------------------------------------------------------------------- #
# The replay engine: the no-edge columns are martingales (8.o item 1; Q32, Q38)
# --------------------------------------------------------------------------- #
def test_the_no_edge_replay_columns_are_martingales_under_buy_and_hold():
    with OF.chunk():
        for stress in (False, True):
            col = simulate.run_column(_spec(stress=stress), n=10 * simulate.CHUNK, seed=SEED, key="k", member="replay",
                                      scenario="stress2x" if stress else "base")
            se = math.sqrt(col.x_var / col.n)
            assert col.reached > 0 and abs(col.x_mean) <= 4.0 * se, (stress, col.x_mean, se)
            assert abs(col.mean + col.mean_cost - 42_000.0) <= 4.0 * col.g_se
            assert col.trades == col.n and col.at_floor == 0 and col.mean_cost > 0.0


def test_the_no_edge_replay_column_is_a_martingale_under_a_daily_loss_limit_that_fires():
    out = simulate._run_paths(_spec(track="moonshot", daily_loss=350.0), n=20_000, chunk=0, seed=SEED)
    share = out["stops"].sum() / out["held"].sum()
    assert 0.07 <= share <= 0.13, share                                 # it fires on about a tenth of the days
    x = out["x"]
    se = float(x.std(ddof=1)) / math.sqrt(x.size)
    assert abs(float(x.mean())) <= 4.0 * se, (x.mean(), se)
    assert (out["outcome"] == 1).any() and (out["stops"] > 1).any()    # REACHED exits and re-entries both happen


def test_the_replay_engine_matches_a_reference_replay_of_its_own_streams():
    """CONTRACT 8.2 to 8.4 with one entry and no exit: chunk c draws its rows from stream(seed, c, "replay") and the
    no-edge signs from stream(seed, c, "replay_sign"); the rule stake enters after check 0's draw and moves at the 29
    later checks; each cost is booked on the sleeve before its move; X is taken at the first passage over T."""
    for tested in (False, True):
        spec, n, v = _spec(tested=tested), 500, {}
        move, cost = spec.replay_move, spec.replay_cost
        units, _ = costs.rule_units(spec.fraction, np.full(n, spec.w0), np.full(n, spec.p0), terms=spec.terms,
                                    on=spec.checks.on[0], mult=spec.mult, target=spec.target, w0=spec.w0,
                                    take_profit=None, stop=None, sizing=spec.sizing, floor=spec.floor,
                                    fstar=spec.fstar, cap_krw=spec.cap_krw)
        stake = units * spec.p0
        for chunk in (0, 1):
            out = simulate._run_paths(spec, n=n, chunk=chunk, seed=SEED)
            rows = models.indices(models.stream(SEED, chunk, "replay"), move.size, n, spec.block)
            signs = models.stream(SEED, chunk, "replay_sign")
            sleeve, booked, x, seen = stake.copy(), np.zeros(n), np.zeros(n), np.zeros(n, dtype=bool)
            for j in range(len(spec.checks.seoul)):
                idx = next(rows)
                eps = None if tested else np.where(signs.random(n) < 0.5, 1.0, -1.0)   # drawn at every check
                if j == 0:
                    continue                                             # the entry follows check 0's move
                if tested:
                    sleeve = sleeve * (1.0 + move[idx])
                else:
                    booked = booked + cost[idx] * sleeve
                    sleeve = sleeve * (1.0 + eps * move[idx] - cost[idx])
                new = ~seen & (spec.w0 - stake + sleeve >= spec.target)
                x, seen = np.where(new, sleeve - stake + booked, x), seen | new
            x = np.where(seen, x, sleeve - stake + booked)
            assert np.allclose(out["v"], spec.w0 - stake + sleeve, rtol=0.0, atol=1e-6), (tested, chunk)
            assert np.allclose(out["cost"], booked, rtol=0.0, atol=1e-9) and (out["held"] == 29).all()
            assert np.allclose(out["x"], x, rtol=0.0, atol=1e-6) and 0 < int(seen.sum()) < n, (tested, chunk)
            v[chunk] = out["v"]
        assert not np.array_equal(v[0], v[1])                            # each chunk has its own draws


def test_the_sleeve_never_exceeds_cash_minus_the_floor_at_entry():
    for fraction, fstar in ((plan.fixed(1.0), None), (plan.kelly(0.5), 1.0)):
        spec = dataclasses.replace(_spec(daily_loss=350.0, fraction=fraction), fstar=fstar)
        out = simulate._run_paths(spec, n=2_000, chunk=0, seed=SEED)
        assert out["entered"].all() and float(out["slack"].min()) >= -1e-6
        assert (out["stops"] > 1).any()                  # a second stop needs a re-entry sized by the same rule
    tested = simulate._run_paths(_spec(tested=True), n=2_000, chunk=0, seed=SEED)
    assert float(tested["cost"].max()) == 0.0 and float(tested["v"].min()) >= 21_000.0


def test_the_replay_engine_follows_the_rule_dates():
    spec = _spec(daily_loss=350.0)
    day10 = spec.checks.seoul[10]
    forced = simulate._run_paths(dataclasses.replace(spec, stop_entries_from=day10, force_exit_from=day10),
                                 n=2_000, chunk=0, seed=SEED)
    assert int(forced["held"].max()) == 10                               # out at check 10, never back in
    shut = simulate._run_paths(dataclasses.replace(spec, stop_entries_from=spec.checks.seoul[0]), n=2_000, chunk=0,
                               seed=SEED)
    assert not shut["entered"].any() and (shut["v"] == 42_000.0).all()   # no entry from the review date on
    one = dataclasses.replace(spec, checks=simulate.checks("CRYPTO", SESSIONS[:1], True), limits=np.full(1, np.nan))
    last = simulate._run_paths(one, n=100, chunk=0, seed=SEED)
    assert not last["entered"].any() and (last["v"] == 42_000.0).all()   # no entry at the last check (Q26)
```

- [ ] **Step B2: Run to verify it fails**

```bash
.venv/Scripts/python.exe -m tests.odds_acceptance odds_replay/
```

  Expected: the 14 Cycle A tests PASS and the 5 new ones FAIL with Task 9's fail-closed refusal, for example

```
FAIL odds_replay/test_the_replay_engine_follows_the_rule_dates ValueError: engine 'replay' is not simulated
```

  and `14/19 passed, 5 failed, 0 not run`.

- [ ] **Step B3: Implement**

  B3a. Check the anchors (Task 9's two def lines, one each) and that no new name exists yet:

```bash
grep -nE "^def (_run_paths|run_column)\(" core/odds/simulate.py
grep -nE "^def (_run_replay|_replay_column|_check_replay_spec|_run_price_paths|_price_column)\(" core/odds/simulate.py
grep -n "engine 'replay'" tests/odds_simulate.py
```

  The first prints two lines, the second nothing, the third one line (the `cases` entry).

  B3b. Edit 1 (anchor: the def line of `_run_paths`, Task 9; Task 10 keeps it). Old text, exactly this one line:

```text
def _run_paths(spec: PathSpec, *, n: int, chunk: int, seed: bytes) -> dict[str, np.ndarray]:
```

  New text (a dispatcher, then the same def line renamed; Task 9's docstring and body below it, as Task 10 left
  them, now belong to `_run_price_paths`, unchanged):

```text
def _run_paths(spec: PathSpec, *, n: int, chunk: int, seed: bytes) -> dict[str, np.ndarray]:
    """Any n >= 1 paths of chunk `chunk`: the replay engine for engine "replay" (Task 17), the price paths below
    otherwise."""
    if spec.engine == "replay":
        return _run_replay(spec, n=n, chunk=chunk, seed=seed)
    return _run_price_paths(spec, n=n, chunk=chunk, seed=seed)


def _run_price_paths(spec: PathSpec, *, n: int, chunk: int, seed: bytes) -> dict[str, np.ndarray]:
```

  B3c. Edit 2 (anchor: the def line of `run_column`, Task 9). Old text, exactly this one line:

```text
def run_column(spec: PathSpec, *, n: int, seed: bytes, key: str, member: str, scenario: str) -> report.ColumnStats:
```

  New text (the renamed def line is 118 characters; Task 9's docstring and body stay below it):

```text
def run_column(spec: PathSpec, *, n: int, seed: bytes, key: str, member: str, scenario: str) -> report.ColumnStats:
    """One column: the replay merge for engine "replay" (Task 17), the price-path merge below otherwise."""
    if spec.engine == "replay":
        return _replay_column(spec, n=n, seed=seed, key=key, member=member, scenario=scenario)
    return _price_column(spec, n=n, seed=seed, key=key, member=member, scenario=scenario)


def _price_column(spec: PathSpec, *, n: int, seed: bytes, key: str, member: str, scenario: str) -> report.ColumnStats:
```

  Every caller keeps its call: Task 9's `_price_column` calls `_run_paths`, which now routes engine "replay" to the
  replay engine and every other engine to `_run_price_paths`; Task 14's tilt pilot calls `_run_paths` directly.

  B3d. Edit 3 (anchor: the module docstring of `core/odds/simulate.py`, its "Not simulated yet" sentence, as Task 10
  rewrote it). Old text, exactly (Task 10's draft wording):

```text
an exit, and a delisting column sells at p (1 - h) at the first check after the first entry (Q29). Not simulated
yet, and refused with ValueError by `_check_spec` rather than priced without it: the replay engine.
```

  New text:

```text
an exit, and a delisting column sells at p (1 - h) at the first check after the first entry (Q29). A replay
column (engine "replay", Task 17) moves a sleeve by the D13 replay's own days instead of a price (`_run_replay`).
```

  If Task 10's final wording differs, delete only the words that call the replay engine "not simulated" and add the
  new sentence after the docstring's last rule (one ledger line).

  B3e. Append part 5a at the end of `core/odds/simulate.py` with the Edit tool: `old_string` is the file's last
  non-empty line as it stands (the end of Task 14's last definition), `new_string` that line followed by two empty
  lines and the block below. It adds no import (`math`, `np`, `costs`, `models`, `report` are imported at the top by
  Task 9). Keep LF.

```python
# --------------------------------------------------------------------------- #
# Part 5a (Task 17): the D13 replay engine (Q38)
# --------------------------------------------------------------------------- #
def _check_replay_spec(spec: PathSpec) -> None:
    """ValueError for a replay spec this engine cannot price faithfully (Q38: the replay's own daily moves, close
    checks only, and no band, bracket, delisting column or OKX cap on an Upbit replay leg)."""
    if spec.replay_move is None:
        raise ValueError("the replay engine needs the replay's daily moves")
    if not len(spec.checks.close) or not spec.checks.close.all():
        raise ValueError("the replay checks each day's close only")
    if (np.isfinite(np.asarray(spec.limits, dtype=float)).any() or spec.bracket is not None
            or spec.delist_h is not None or spec.cap_krw is not None):
        raise ValueError("a replay leg has no band, bracket, delisting column or OKX cap")


def _run_replay(spec: PathSpec, *, n: int, chunk: int, seed: bytes) -> dict[str, np.ndarray]:
    """The replay engine (CONTRACT 8.3, 8.4; Q38) over n >= 1 paths of chunk `chunk`.

    A sleeve of KRW stands in for units x price: the rule stake of `costs.rule_units` under the zero-charge replay
    terms and spec.mult (0.0), so it never exceeds cash - L, rounded down to whole lots at p0, the leg's last close.
    At each close check the row index advances one step of the stationary bootstrap (stream "replay", mean block
    spec.block). A no-edge column (spec.replay_cost set) moves a held sleeve to sleeve x (1 + eps a - c), eps a fair
    sign from stream "replay_sign", and books c x the sleeve before the move as cost, so cash + sleeve + costs is a
    martingale; the tested column moves it to sleeve x (1 + R1). Exits, in priority: target (moonshot), daily loss,
    rule date; no kappa and no phi. A flat path re-enters at a later check by the same rule (Q38), never at the last
    check and never on or after spec.stop_entries_from. Returns the per-path arrays `_replay_column` merges, plus
    "stops" (daily-loss exits), "held" (checks that moved a held sleeve) and "slack" (the least cash - L right after
    an entry; inf for a path that never entered)."""
    _check_replay_spec(spec)
    if n < 1:
        raise ValueError(f"n = {n} paths: need at least one")
    move = np.asarray(spec.replay_move, dtype=float)
    cost = None if spec.replay_cost is None else np.asarray(spec.replay_cost, dtype=float)
    rows = models.indices(models.stream(seed, chunk, "replay"), move.size, n, spec.block)
    signs = None if cost is None else models.stream(seed, chunk, "replay_sign")
    seoul, on = spec.checks.seoul, spec.checks.on
    last, moonshot = len(seoul) - 1, spec.track == "moonshot"
    never = np.zeros(n, dtype=bool)
    price = np.full(n, spec.p0)
    cash = np.full(n, spec.w0)
    sleeve = np.zeros(n)
    booked = np.zeros(n)
    held = np.zeros(n, dtype=bool)
    done = np.zeros(n, dtype=bool)
    outcome = np.zeros(n, dtype=np.int8)                  # 0 running, 1 reached, 2 at_floor
    fp = np.zeros(n, dtype=bool)
    x = np.zeros(n)
    x_set = np.zeros(n, dtype=bool)
    entered = np.zeros(n, dtype=bool)
    day_stop = np.zeros(n, dtype=bool)
    day_ref = np.full(n, spec.w0)
    v_prev = np.full(n, spec.w0)
    stops = np.zeros(n, dtype=np.int64)
    held_checks = np.zeros(n, dtype=np.int64)
    slack = np.full(n, np.inf)
    for j, day in enumerate(seoul):
        idx = next(rows)
        held_checks += held
        if cost is None:
            sleeve = np.where(held, sleeve * (1.0 + move[idx]), 0.0)
        else:
            eps = np.where(signs.random(n) < 0.5, 1.0, -1.0)
            booked = booked + np.where(held, cost[idx] * sleeve, 0.0)
            sleeve = np.where(held, sleeve * (1.0 + eps * move[idx] - cost[idx]), 0.0)
        if j == 0 or day != seoul[j - 1]:
            day_ref, day_stop = v_prev, np.zeros(n, dtype=bool)
        v = cash + sleeve
        new = ~done & ~fp & (v >= spec.target)
        fp |= new
        x = np.where(new & ~x_set, cash + sleeve + booked - spec.w0, x)
        x_set |= new
        live = ~done & held
        hit_target = live & (v >= spec.target) if moonshot else never
        hit_loss = live & ~hit_target & (day_ref - v >= spec.daily_loss)
        hit_rule = live & (spec.force_exit_from is not None and day >= spec.force_exit_from)
        filled = hit_target | hit_loss | hit_rule
        stops += hit_loss
        day_stop |= hit_loss
        cash = np.where(filled, cash + sleeve, cash)
        sleeve = np.where(filled, 0.0, sleeve)
        held &= ~filled
        reached = filled & (cash >= spec.target) if moonshot else never
        floored = filled & ~reached & (cash <= spec.floor)
        outcome[reached] = 1
        outcome[floored] = 2
        done |= reached | floored
        x = np.where((reached | floored) & ~x_set, cash + sleeve + booked - spec.w0, x)
        x_set |= reached | floored
        can = ~done & ~held & ~filled & ~day_stop
        if j == last or (spec.stop_entries_from is not None and day >= spec.stop_entries_from):
            can = never
        if can.any():
            units, at_floor = costs.rule_units(
                spec.fraction, cash, price, terms=spec.terms, on=on[j], mult=spec.mult, target=spec.target,
                w0=spec.w0, take_profit=None, stop=None, sizing=spec.sizing, floor=spec.floor, fstar=spec.fstar,
                cap_krw=spec.cap_krw)
            stuck = can & at_floor
            outcome[stuck] = 2
            done |= stuck
            x = np.where(stuck & ~x_set, cash + sleeve + booked - spec.w0, x)
            x_set |= stuck
            buy = can & ~at_floor & (units > 0.0)
            stake = units * price
            cash = np.where(buy, cash - stake, cash)
            sleeve = np.where(buy, stake, sleeve)
            held |= buy
            entered |= buy
            slack = np.where(buy, np.minimum(slack, cash - spec.floor), slack)
        v_prev = cash + sleeve
    x = np.where(x_set, x, cash + sleeve + booked - spec.w0)
    return {"v": cash + sleeve, "cost": booked, "x": x, "outcome": outcome, "fp": fp, "entered": entered,
            "stops": stops, "held": held_checks, "slack": slack}


def _replay_column(spec: PathSpec, *, n: int, seed: bytes, key: str, member: str, scenario: str
                   ) -> report.ColumnStats:
    """run_column for engine "replay": _run_paths(spec, n=CHUNK, chunk=c, seed=seed) for c in range(n // CHUNK),
    merged. A replay column has no lock, band, bracket or delisting. Its HIDDEN_EDGE range is replay_range's, fixed
    before the run, on the no-edge columns; the tested column is an edge column, so its range is nan."""
    if n <= 0 or n % CHUNK:
        raise ValueError(f"n = {n} paths is not a positive multiple of CHUNK = {CHUNK}")
    parts = [_run_paths(spec, n=CHUNK, chunk=c, seed=seed) for c in range(n // CHUNK)]
    v, cost, x, outcome, fp, entered = (np.concatenate([part[name] for part in parts])
                                        for name in ("v", "cost", "x", "outcome", "fp", "entered"))
    kept = v[outcome == 2]
    x_range = math.nan if spec.replay_cost is None else report.replay_range(
        target=spec.target, a_max=float(np.max(spec.replay_move)), c_max=float(np.max(spec.replay_cost)),
        n_checks=len(spec.checks.seoul))
    return report.ColumnStats(
        key=key, member=member, scenario=scenario, n=n, reached=int(fp.sum()),
        reached_outcome=int((outcome == 1).sum()), ended_at_or_above=int((v >= spec.target).sum()),
        at_floor=int((outcome == 2).sum()), running=int((outcome == 0).sum()), locked_at_horizon=0,
        rungs=tuple(int((v >= rung * spec.w0).sum()) for rung in report.LADDER) + (int((v >= spec.target).sum()),),
        median=float(np.median(v)), p5=float(np.quantile(v, 0.05)), mean=float(v.mean()),
        mean_se=float(v.std(ddof=1)) / math.sqrt(n), mean_cost=float(cost.mean()),
        g_se=float((v + cost).std(ddof=1)) / math.sqrt(n),
        kept_lo=float(kept.min()) if kept.size else None, kept_hi=float(kept.max()) if kept.size else None,
        x_mean=float(x.mean()), x_var=float(x.var(ddof=1)), x_range=x_range, wins=0, losses=0, unresolved=0,
        band_edge_share=0.0, band_edge_sessions=0, worst_gap=0.0, trades=int(entered.sum()))
```

  B3f. Edit 4 (anchor: `tests/odds_simulate.py`, Task 9's `test_rules_this_engine_does_not_simulate_fail_closed`,
  the first line of its `cases = (` statement, which holds the `engine="replay"` entry). Old text, exactly (the
  line's text after its four-space indent and `cases = (`):

```text
(_spec(limits=np.full(30, 0.30)), "any other leg nan"), (_spec(engine="replay"), "engine 'replay'"),
```

  New text (the replay entry moves to its own line, indented 13 spaces like the tuple's other lines, so no line
  passes 119 characters):

```text
(_spec(limits=np.full(30, 0.30)), "any other leg nan"),
             (_spec(engine="replay"), "the replay's daily moves"),
```

  Task 9's `_spec` is a bootstrap spec, so with its engine set to "replay" it has no `replay_move`, and both
  `_run_paths` and `run_column` now refuse it through `_check_replay_spec` (`the replay engine needs the replay's daily
  moves`): still a ValueError, never a priced column.

- [ ] **Step B4: Run to verify it passes**

```bash
.venv/Scripts/python.exe -m tests.odds_acceptance odds_replay/
.venv/Scripts/python.exe -m tests.odds_acceptance odds_simulate/
.venv/Scripts/python.exe -m tests.odds_acceptance odds_locks/
```

  Expected: `19/19 passed, 0 failed, 0 not run` for `odds_replay/`; `odds_simulate/` and `odds_locks/` end with every
  test PASS and `0 failed` (their counts are unchanged from Tasks 9 and 10).

#### Cycle C: simulate() and the replay card

- [ ] **Step C1: Write the failing tests**

  Append to `tests/odds_replay.py` with the Edit tool: `old_string` is the file's last line,
  `    assert not last["entered"].any() and (last["v"] == 42_000.0).all()   # no entry at the last check (Q26)`, and
  `new_string` is that line followed by two empty lines and the block below:

```python
# --------------------------------------------------------------------------- #
# The replay card (8.o items 2, 6, 7 and 9; Q32, Q38; R2-5)
# --------------------------------------------------------------------------- #
def test_the_replay_card_renders_its_lines_in_order():
    rep = _card()
    assert rep.refused is None, rep.refused
    assert rep.headline == "replay_no_edge/base" and rep.spread is None
    assert tuple(col.key for col in rep.columns) == simulate._REPLAY_KEYS
    assert rep.replay["fstar"] == 1.0 and rep.l_min == 21_000.0 and rep.model_key == "model.replay"
    r1 = models.replay_returns(_real())[2]                             # 30 checks: the sleeve moves at 29 of them
    assert rep.replay["h"] == 29.0 and rep.replay["growth"] == models.block_growth(r1, 10.0, 29) - 1.0
    assert rep.replay["growth_iid"] == (1.0 + float(r1.mean())) ** 29 - 1.0
    text = report.render(rep)
    model_line = report.say("model.replay", first="2019-10-23", last="2026-09-25", rows="2,530", block="10")
    growth = report.say("replay.growth", h="29", g="2.9%", g0="2.6%")
    lead = report.say("replay.lead", y0="2019", y1="2026", cut="40", bench="0.79", cutsr="0.73", diff="+0.43",
                      lo="+0.03", hi="+0.83")                        # the spec 7.5 item 9 text, exactly
    edge = "Without the edge assumed here, no plan that keeps this floor can beat 1 in 1,999."
    order = [model_line, report.say("replay.noedge"), report.say("kelly.label"), report.say("column.stress"), lead,
             growth, "only if the edge in this column is real", edge, report.say("footer")]
    at = [text.find(part) for part in order]
    assert -1 not in at and at == sorted(at), list(zip(order, at))
    for once in (lead, growth, report.say("kelly.label"), report.say("replay.noedge"), edge):
        assert text.count(once) == 1, once
    fixed = report.render(_card(fraction=plan.fixed(0.5)))
    assert report.say("kelly.label") not in fixed and growth in fixed


def test_hidden_edge_and_the_ceiling_check_cover_the_two_no_edge_replay_cells():
    with (OF.spy(report, "hidden_edge") as hidden, OF.spy(report, "ceiling_cells") as cells,
          OF.spy(simulate, "run_column") as runs):
        rep = _card()
    assert rep.refused is None, rep.refused
    assert [args[0].key for args, _kw, _out in hidden] == ["replay_no_edge/base"] and rep.hidden.status == "pass"
    cell_keys = {tuple(col.key for col in args[0]) for args, _kw, _out in cells}
    assert cell_keys == {("replay_no_edge/base", "replay_no_edge/stress2x")}                     # m = 2
    a, c, r1 = models.replay_returns(_real())
    assert [kw["key"] for _args, kw, _out in runs] == list(simulate._REPLAY_KEYS)
    for (args, _kw, _out), move, cost in zip(runs, (a, a, r1), (c, costs.COST_STRESS * c, None)):
        spec = args[0]                                                 # the tested column moves by R1, cost-free
        assert spec.engine == "replay" and spec.mult == 0.0 and np.array_equal(spec.replay_move, move)
        assert (spec.replay_cost is None) if cost is None else np.array_equal(spec.replay_cost, cost)
    base, stress, tested = rep.columns
    assert base.x_range == report.replay_range(target=42_000_000.0, a_max=float(a.max()), c_max=float(c.max()),
                                               n_checks=30)
    assert stress.x_range == report.replay_range(target=42_000_000.0, a_max=float(a.max()),
                                                 c_max=2.0 * float(c.max()), n_checks=30)
    assert math.isnan(tested.x_range) and not [f for f in rep.flags if f.code == "CEILING_BREACH"]


def test_a_replay_leg_needs_only_the_upbit_lot_and_minimum():
    rep = _card(ctx=_no_fee_ctx())                                     # upbit: lot and min_order, no fee_extras
    assert rep.refused is None, rep.refused
    assert tuple(col.key for col in rep.columns) == simulate._REPLAY_KEYS
    with OF.chunk():
        held = OF.pipeline(OF.plan(horizon_days=30), _no_fee_ctx())
    assert held.refused is not None and held.refused.code == "NOT_TRADABLE"     # buy-and-hold needs fee_extras
    no_lot = _card(ctx=_no_fee_ctx("lot"))
    assert no_lot.refused is not None and no_lot.refused.code == "NOT_TRADABLE"   # the replay still needs the lot


def test_a_replay_that_does_not_reproduce_its_card_is_refused():
    for replay, detail in ((dataclasses.replace(_real(), embargo=0), "replay: embargo"), (None, "replay: missing")):
        rep = _card(replay=replay)
        assert rep.refused is not None and rep.columns == (), detail
        assert (rep.refused.code, rep.refused.detail) == ("CARD_NOT_REPRODUCED", detail), rep.refused
        assert "1 in" not in report.render(rep)


def test_simulate_takes_kelly_fstar_from_the_verified_replay():
    p = _replay_plan()
    seed = models.market_seed(models.data_hashes(OF.fresh_series(), _real()), "", "c000001", 1)
    r = np.asarray(_real().oos_pnl, dtype=float)
    expected = models.kelly_fstar(r, models.mu_lb(r, models.stream(seed, 0, "kelly")))
    assert simulate._replay_fstar(p, OF.pipeline_inputs(p, OF.fresh_series(), replay=_real())) == expected == 1.0
    fixed = _replay_plan(plan.fixed(0.5))
    assert simulate._replay_fstar(fixed, OF.pipeline_inputs(fixed, OF.fresh_series())) is None   # reads no replay
    assert math.isnan(_card(fraction=plan.fixed(0.5)).replay["fstar"])
```

- [ ] **Step C2: Run to verify it fails**

```bash
.venv/Scripts/python.exe -m tests.odds_acceptance odds_replay/
```

  Expected: the 19 earlier tests PASS; four new ones FAIL on Task 13's placeholder and one on the missing helper:

```
FAIL odds_replay/test_the_replay_card_renders_its_lines_in_order AssertionError: Refusal(code='CARD_NOT_REPRODUCED', sub='', slots={}, detail='replay not built yet')
FAIL odds_replay/test_simulate_takes_kelly_fstar_from_the_verified_replay AttributeError: module 'core.odds.simulate' has no attribute '_replay_fstar'
```

  (`test_a_replay_leg_needs_only_the_upbit_lot_and_minimum`, `test_a_replay_that_does_not_reproduce_its_card_is_refused`
  and `test_hidden_edge_and_the_ceiling_check_cover_the_two_no_edge_replay_cells` fail with the same placeholder
  Refusal), and `19/24 passed, 5 failed, 0 not run`.

- [ ] **Step C3: Implement**

  C3a. Check the anchors and Task 12's rendering:

```bash
grep -n "replay not built yet" core/odds/simulate.py tests/odds_pipeline.py
grep -n "first = costs.first_stake(plan_obj, terms, ctx, p0, first_day)" core/odds/simulate.py
grep -n "    return _accepted_report(plan_obj, ctx, inputs, inst=inst, terms=terms, market=market, sessions=sessions," core/odds/simulate.py
grep -cE "^def (_headline_spec|_grey_slots|_report_provenance|_accepted_report)\(" core/odds/simulate.py
grep -nE "^(import dataclasses|from core\.odds import bold, costs, models, plan, report)" core/odds/simulate.py
grep -nE "^def _replay_lines\(|\"replay\.noedge\"|\"kelly\.label\"|\"tested_replay/base\"" core/odds/report.py
```

  Expected: the placeholder once in `simulate.py` and twice in `tests/odds_pipeline.py` (the test's docstring and its
  `placeholder` tuple); the `first_stake` call once; the `return _accepted_report(` line once; `4`; the two import
  lines of Task 13's part (each may carry `# noqa: E402`); and in `report.py` the def `_replay_lines` plus the strings
  `"replay.noedge"`, `"kelly.label"` and `"tested_replay/base"` in `_card` and `_column_lines`. If `report.py` lacks
  any of them, Task 12 did not build the replay card's lines: stop and rule (the coordinator decides which task adds
  them; `test_the_replay_card_renders_its_lines_in_order` states what they must render). If Task 14 moved its GARCH
  fits or pilots out of `_accepted_report` into `simulate` above the `return _accepted_report(` statement, put Edit 7's
  replay branch above them instead (still after the SCREEN_BLOCKED return), so a replay leg never fits a model (one
  ledger line).

  C3b. Edit 5 (anchor: `simulate`, Q24 step 10, Task 13's placeholder branch). Old text, exactly:

```python
    if refusal is None and replay:                         # Task 17 replaces this branch with models.verify_replay
        refusal = plan.Refusal(code="CARD_NOT_REPRODUCED", detail="replay not built yet")
```

  New text:

```python
    if refusal is None and replay:                         # Q24 step 10: the replay must reproduce its card
        refusal = _replay_refusal(inputs)
```

  C3c. Edit 6 (anchor: `simulate`, Q24 step 12, the first-stake call). Old text, exactly:

```python
    first = costs.first_stake(plan_obj, terms, ctx, p0, first_day)
```

  New text (f* only after the replay passed step 10; `_replay_fstar` returns None for a fixed stake and for every
  other leg the conditional gives None, which is `first_stake`'s default):

```python
    fstar = _replay_fstar(plan_obj, inputs) if replay else None      # Kelly's f* on the verified replay (Q9)
    first = costs.first_stake(plan_obj, terms, ctx, p0, first_day, fstar=fstar)
```

  C3d. Edit 7 (anchor: `simulate`, step 7, the final `return _accepted_report(` statement; Task 14's comment on the
  `n = ...` line above it stays as it is). Old text, exactly:

```text
    return _accepted_report(plan_obj, ctx, inputs, inst=inst, terms=terms, market=market, sessions=sessions,
                            screening=screening, n=n)
```

  New text:

```text
    if replay:                                             # the replay card: its own three columns (Q38)
        return _replay_report(plan_obj, ctx, inputs, inst=inst, terms=terms, market=market, sessions=sessions,
                              screening=screening, n=n, fstar=fstar)
    return _accepted_report(plan_obj, ctx, inputs, inst=inst, terms=terms, market=market, sessions=sessions,
                            screening=screening, n=n)
```

  C3e. Append part 5b at the end of `core/odds/simulate.py` (after part 5a) with the Edit tool, as in B3e. It adds no
  import (`dataclasses`, `date`, `math`, `np`, `bold`, `costs`, `models`, `plan`, `report` are already imported by
  Tasks 9 and 13).

```python
# --------------------------------------------------------------------------- #
# Part 5b (Task 17): the replay card in simulate() (Q9, Q38)
# --------------------------------------------------------------------------- #
_REPLAY_KEYS = ("replay_no_edge/base", "replay_no_edge/stress2x", "tested_replay/base")


def _replay_refusal(inputs: plan.Inputs) -> plan.Refusal | None:
    """Q24 step 10: CARD_NOT_REPRODUCED unless the passed replay reproduces every pin (models.verify_replay); the
    detail names the first item that does not ("replay: missing" without a replay)."""
    if inputs.replay is None:
        return plan.Refusal(code="CARD_NOT_REPRODUCED", detail="replay: missing")
    bad = models.verify_replay(inputs.replay)
    return None if bad is None else plan.Refusal(code="CARD_NOT_REPRODUCED", detail=f"replay: {bad}")


def _replay_fstar(plan_obj, inputs: plan.Inputs) -> float | None:
    """Kelly's f* on the verified replay (Q9): mu_lb from stream "kelly", chunk 0, of the market seed, which the
    first stake needs before step 7 builds the same seed from the same inputs; None for a fixed stake."""
    if plan_obj.fraction.kind != "kelly":
        return None
    seed = models.market_seed(models.data_hashes(inputs.series, inputs.replay), inputs.calendar_sha256,
                              inputs.comparison_id, inputs.run_counter)
    r = np.asarray(inputs.replay.oos_pnl, dtype=float)
    return models.kelly_fstar(r, models.mu_lb(r, models.stream(seed, 0, "kelly")))


def _replay_report(plan_obj, ctx, inputs, *, inst, terms, market: str, sessions: tuple[date, ...], screening,
                   n: int, fstar: float | None) -> report.OddsReport:
    """Step 7 for a replay leg (Q38): the market seed (Q34); the headline spec's stake, owner limits, p0 and rule
    dates with the replay engine, close checks, the card's block and mult 0.0; the three replay columns on one seed
    (common random numbers); HIDDEN_EDGE on the base cell and CEILING_BREACH over the two no-edge cells (m = 2); no
    spread, structural cap, delisting or assumed column; the figures of the replay lines; report.build with every
    provenance key (model "replay", no spread member)."""
    leg, rep, series = plan_obj.leg, inputs.replay, inputs.series
    seed = models.market_seed(models.data_hashes(series, rep), inputs.calendar_sha256, inputs.comparison_id,
                              inputs.run_counter)
    a, c, r1 = models.replay_returns(rep)
    block = float(models.REPLAY_PINS["protocol"]["block"])
    spec = dataclasses.replace(
        _headline_spec(plan_obj, ctx, inputs, terms=terms, market=market, sessions=sessions, screening=screening),
        engine="replay", m_o=None, m_i=None, block=block, checks=checks(market, sessions, True), mult=0.0,
        fstar=fstar)

    def column(key: str, move: np.ndarray, cost: np.ndarray | None) -> report.ColumnStats:
        return run_column(dataclasses.replace(spec, replay_move=move, replay_cost=cost), n=n, seed=seed, key=key,
                          member="replay", scenario=key.rsplit("/", 1)[1])

    base = column(_REPLAY_KEYS[0], a, c)
    stress = column(_REPLAY_KEYS[1], a, costs.COST_STRESS * c)
    tested = column(_REPLAY_KEYS[2], r1, None)
    stake, target = float(plan_obj.stake_krw), float(plan_obj.target_krw)
    l_min = spec.floor if leg.sizing == "floor_safe" else 0.0
    ceiling = bold.ceiling(stake, l_min, target)
    hidden = report.hidden_edge(base, w0=stake, target=target, l_min=l_min)
    flags = report.flags_for(headline=base, no_edge=(base, stress), engine="replay", hidden=hidden, ceiling=ceiling,
                             structural=None, target=target, stake=stake, reference=None,
                             rule_flags=screening.flags, grey=_grey_slots(plan_obj, ctx), series=series, okx=False)
    moves, st = len(spec.checks.seoul) - 1, rep.stats    # an entry follows its check's move (8.4 step 5)
    figures = {"y0": float(rep.oos_dates[0][:4]), "y1": float(rep.oos_dates[-1][:4]),
               "cut": 1.0 - models.LIVE_SHARPE_MULTIPLIER, "bench_sr": float(st["bench_sr"]),
               "haircut_sr": float(st["haircut_sr"]), "diff": float(st["bench_diff"]),
               "ci_lo": float(st["bench_ci"][0]), "ci_hi": float(st["bench_ci"][1]),
               "fstar": math.nan if fstar is None else float(fstar), "h": float(moves),
               "growth": models.block_growth(r1, block, moves) - 1.0,
               "growth_iid": (1.0 + float(r1.mean())) ** moves - 1.0}
    provenance = _report_provenance(plan_obj, ctx, inputs, screening=screening, seed=seed, n=n, members=())
    return report.build(
        plan_hash=plan.plan_hash(plan_obj), plan_index=1, plan_count=1, refused=None, track=plan_obj.track,
        stake=stake, target=target, floor=spec.floor, l_min=l_min, horizon_days=plan_obj.horizon_days, n=n,
        sizing=leg.sizing, model_key="model.replay",
        model_slots={"first": rep.oos_dates[0], "last": rep.oos_dates[-1], "rows": f"{len(rep.oos_dates):,}",
                     "block": f"{block:g}"},
        columns=(base, stress, tested), headline=base.key, spread=None, spread_kind="none", notes=(), ceiling=ceiling,
        structural_cap=None, structural_sessions=None, tax_basis=inst.tax_basis, cost_words_key="cost.fees",
        hidden=hidden, flags=flags, assumed=None, replay=figures,
        comparison=(inputs.comparison_plans, inputs.comparison_typed, inputs.plan_runs),
        provenance={**provenance, "model": "replay"})
```

  C3f. Edit 8 (anchor: `tests/odds_pipeline.py`, Task 13's placeholder test, replaced whole). Old text, exactly:

```python
def test_replay_legs_are_refused_until_the_replay_is_built():
    """Q24 step 10 placeholder (Task 17 replaces this test with the real replay): a replay leg is CARD_NOT_REPRODUCED
    with detail "replay not built yet". R2-5: its terms need the Upbit lot and minimum but no fee_extras, so on venues
    without fee_extras it still reaches that step, while a buy-and-hold leg there, and a replay leg on venues without
    the Upbit lot, are NOT_TRADABLE."""
    no_extras = OF.odds_ctx(active=F.approved(venues=OF.venues_with(upbit={"fee_extras": None})))
    no_lot = OF.odds_ctx(active=F.approved(venues=OF.venues_with(upbit={"lot": None})))
    with OF.chunk():
        reps = [OF.pipeline(OF.plan(leg=REPLAY)), OF.pipeline(OF.plan(leg=REPLAY), no_extras),
                OF.pipeline(OF.plan(), no_extras), OF.pipeline(OF.plan(leg=REPLAY), no_lot)]
    placeholder = ("CARD_NOT_REPRODUCED", "replay not built yet")
    assert [(r.refused.code, r.refused.detail) for r in reps[:2]] == [placeholder, placeholder]
    assert [r.refused.code for r in reps[2:]] == ["NOT_TRADABLE", "NOT_TRADABLE"]
    assert all(_no_probability(report.render(r)) for r in reps)
```

  New text (Q24 order and R2-5 at the pipeline level, now on the real check; the replay card itself is
  `tests/odds_replay.py`'s):

```python
def test_replay_legs_are_checked_against_their_card_at_step_10():
    """Q24 step 10 (Task 17 replaced Task 13's placeholder): a replay leg whose inputs carry no replay is
    CARD_NOT_REPRODUCED with detail "replay: missing". R2-5: its terms need the Upbit lot and minimum but no
    fee_extras, so on venues without fee_extras it still reaches that step, while a buy-and-hold leg there, and a
    replay leg on venues without the Upbit lot, are NOT_TRADABLE. The real replay's card is tests/odds_replay.py's."""
    no_extras = OF.odds_ctx(active=F.approved(venues=OF.venues_with(upbit={"fee_extras": None})))
    no_lot = OF.odds_ctx(active=F.approved(venues=OF.venues_with(upbit={"lot": None})))
    with OF.chunk():
        reps = [OF.pipeline(OF.plan(leg=REPLAY)), OF.pipeline(OF.plan(leg=REPLAY), no_extras),
                OF.pipeline(OF.plan(), no_extras), OF.pipeline(OF.plan(leg=REPLAY), no_lot)]
    missing = ("CARD_NOT_REPRODUCED", "replay: missing")
    assert [(r.refused.code, r.refused.detail) for r in reps[:2]] == [missing, missing]
    assert [r.refused.code for r in reps[2:]] == ["NOT_TRADABLE", "NOT_TRADABLE"]
    assert all(_no_probability(report.render(r)) for r in reps)
```

- [ ] **Step C4: Run to verify it passes**

```bash
.venv/Scripts/python.exe -m tests.odds_acceptance odds_replay/
```

  Expected: 24 PASS lines and `24/24 passed, 0 failed, 0 not run`, within about 20 s unloaded (three replays). Then,
  each with the overlap check first and each ending with no FAIL line (`odds_garch/` because part 3 is appended to
  `models.py`, whose GARCH part Task 8's tests exercise; `odds_bold/` because Task 11's engine test calls
  `simulate.run_column`, now a dispatcher, and it ends with the count Task 11 recorded, `12/12 passed, 0 failed, 0
  not run`):

```bash
.venv/Scripts/python.exe -m tests.odds_acceptance odds_garch/
.venv/Scripts/python.exe -m tests.odds_acceptance odds_bold/
.venv/Scripts/python.exe -m tests.odds_acceptance odds_pipeline/
.venv/Scripts/python.exe -m tests.odds_acceptance odds_simulate/
.venv/Scripts/python.exe -m tests.odds_acceptance odds_locks/
.venv/Scripts/python.exe -m tests.odds_acceptance odds_columns/
.venv/Scripts/python.exe -m tests.odds_acceptance odds_report/
.venv/Scripts/python.exe -m tests.odds_acceptance odds_guards/
.venv/Scripts/python.exe -m tests.compliance_acceptance compliance_guards/
.venv/Scripts/python.exe -m tests.compliance_acceptance compliance_store/
.venv/Scripts/python.exe -m tests.macro_m0_harness
.venv/Scripts/python.exe -m tests.macro_tf_gov
.venv/Scripts/python.exe -m tests.macro_m7_ledger
.venv/Scripts/python.exe -m tests.macro_m8_forward
.venv/Scripts/python.exe -m tests.macro_m6_context
KIS_APP_KEY='<unset>' KIS_APP_SECRET='<unset>' KIS_ACCOUNT_8='<unset>' KIS_ACCOUNT_PD='<unset>' UPBIT_ACCESS_KEY='<unset>' UPBIT_SECRET_KEY='<unset>' OKX_API_KEY='<unset>' OKX_API_SECRET='<unset>' OKX_API_PASSPHRASE='<unset>' OPENDART_API_KEY='<unset>' KRX_API_KEY='<unset>' FMP_API_KEY='<unset>' ANTHROPIC_API_KEY='<unset>' GS_CLIENT_ID='<unset>' GS_CLIENT_SECRET='<unset>' FINVIZ_API_KEY='<unset>' ALPACA_API_KEY='<unset>' ALPACA_SECRET_KEY='<unset>' FXMACRODATA_API_KEY='<unset>' .venv/Scripts/python.exe tests/run_all.py --suite cockpit; echo "exit $?"; git checkout -- qa/acceptance_results.json
```

  `odds_pipeline/` keeps the count Tasks 13 and 14 recorded (13 tests,
  `test_replay_legs_are_checked_against_their_card_at_step_10` in place of the placeholder test). This task does not
  run `--suite odds` and records no suite total: Task 18 Step 4 states the odds total from the drafts.
  `odds_guards/` passes with the new code: `core/oddsdata/replay.py` imports `csv`, `functools`, `hashlib`, `json`,
  `pathlib`, numpy, `core.odds.plan`, `core.quant.strategies` and `core.quant.validate` (no `core.engine`, no study
  runner, no `gate_ledger` or `macro_artifacts`, no clock, no write, no `__main__`), and the core parts add no
  import, no clock, no file call and none of the guarded words (the 40% cut is written
  `1.0 - models.LIVE_SHARPE_MULTIPLIER`). Record in the ledger's "Runs" the `odds_replay/` count and time; under
  "Drift rulings" any anchor that had moved; and the line "Task 17: report.py unchanged, Task 12 renders the replay
  card (checked in C3a)". `git status --short` shows the six task files and the ledger's one `??` line, nothing else
  (`qa/acceptance_results.json` restored).

- [ ] **Step 5: Commit**

```bash
git add core/oddsdata/replay.py core/odds/models.py core/odds/simulate.py tests/odds_replay.py tests/odds_simulate.py tests/odds_pipeline.py
git diff --cached --stat
git diff --cached --stat --ignore-cr-at-eol
git commit -m "feat(odds): the D13 replay, Kelly and the replay card" -m "replay_s_c3 re-runs S_C3 from the committed cache; the core pins its inputs, digests and stats (CARD_NOT_REPRODUCED), sizes Kelly from mu_lb, and runs the fair-sign no-edge, 2x-cost and tested replay columns." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

  The two `--stat` outputs must be identical (6 files changed, LF only).
