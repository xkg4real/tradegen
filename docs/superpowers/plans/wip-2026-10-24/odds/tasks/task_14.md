### Task 14: simulate(), part 2: the columns, the spread, the pilots and the flags (`core/odds/simulate.py`)

**Files:**
- Modify: `core/odds/simulate.py` (anchors: `simulate`, the GARCH-t placeholder branch Task 13 left; `_no_edge_pair`;
  `_accepted_report`, the last function of the file; LF)
- Modify: `tests/odds_fixtures.py` (anchor: the end of `pipeline`, the last function of Task 13's block; append only;
  LF)
- Modify: `tests/odds_pipeline.py` (anchors: Task 13's placeholder test
  `test_garch_headlines_are_refused_until_their_pilot_is_built`, the run blocks and column-count assertions of
  eight Task 13 tests, and the docstring of `test_every_refusal_in_q24_order`; LF)
- Create: `tests/odds_columns.py` (LF, UTF-8, no BOM; already in `tests/odds_acceptance.MODULES` since Task 1)
- Test: `tests/odds_columns.py`, `tests/odds_pipeline.py`

All three modified files are created by this plan (Tasks 1, 5, 9, 13), never by the compliance follow-up, so the
follow-up cannot have moved their text. Every Edit below still quotes its old text exactly as Task 13's plan text
writes it and names its anchor: if an earlier task of this plan was amended at execution (for example Task 13's
`_accepted_report`), apply the DRIFT RULE of the Global Constraints: re-read the file, make the same
change to the current text, keep the earlier task's behaviour and record one ledger line under "Drift rulings".

**Interfaces:**
- Consumes:
  - Task 1: `OF.chunk()` (swaps `simulate.CHUNK`, `DEFAULT_PATHS`, `GARCH_SUB`), `OF.pilots(n=2_000, nodes=64)`
    (swaps `models.PILOT_PATHS`, `simulate.TILT_PILOT`, `models.PILOT_NODES`), both restoring the saved objects;
    the runner `.venv/Scripts/python.exe -m tests.odds_acceptance <module>/` (each test in `hermetic()` and a temp
    `TRADEGEN_HOME`).
  - Task 5 (`core.odds.plan`): `Leg`, `Bracket`, `bold()`, `Refusal(code, sub, slots, detail)`, `Series`,
    `series_md5`, `instrument(plan, ctx)`, `OKX_CAP_KEY`; fixtures `OF.plan(**changes)`, `OF.odds_ctx()`,
    `OF.series(...)`.
  - Task 6 (`core.odds.costs`): `terms(venue, inst, fx)`, `kappa(terms, prices, on, mult, *, side)`,
    `kappa_bound(terms, p_min, dates, mult)` (mult applied; the table rate for a book with no ladder; `math.inf`
    when `p_min` is not > 0 on a ladder or ETF book), `r_exit(terms)`, `DELIST_STRESS` `(0.30, 1.00)`, `SCENARIOS`.
  - Task 7 (`core.odds.models`): `rows(series) -> (m_o, m_i, r)`, `block_length(r)`, `variant_block(b, mult,
    n_rows)`, `stream(seed, chunk, name, *extra)`, `seed_sequence(seed, chunk, name, *extra)`, `STREAMS` (with
    `"tilt"` and `"refit_series"`).
  - Task 8 (`core.odds.models`): `GarchParams` (frozen, hashable: `dist, omega, alpha, beta, nu, mean_daily, n_obs,
    cond_vol_last, converged, at_bound`), `fit_garch_t(returns) -> GarchParams`, `pilot_checks(fit, horizon, seed:
    bytes) -> (bool, "" | "deterministic" | "statistical")`, `simulate_garch_series(omega, alpha, beta, nu, *, n,
    seed, dist="t")`, `_correction_table(nu, bound) -> (z, wt, grid, ratio)` (the copied 4-tuple, looked up at call
    time by `martingale_correction`), `NU_NORMAL`, `PILOT_PATHS`, `PILOT_NODES`.
  - Task 9 (`core.odds.simulate`): `MEMBERS`, `REFIT_B`, `TILT_PILOT`, `TILT_BOUND`, `TILT_ITER`, `TILT_TOL`,
    `TILT_FAIL`, `checks(market, sessions, close_only)`, `PathSpec` (contract 8.2), `run_column(spec, *, n, seed,
    key, member, scenario)` (stores `x_range = nan`, Task 9's ledger minor; `brackets = (r, d)` of chunk 0 when
    `record_brackets`), and `_run_paths(spec, *, n, chunk, seed)` returning a mapping whose `"wins"` and `"losses"`
    are per-path int arrays (take-profit and stop fills); the GARCH engine takes 1 fit or `REFIT_B` fits.
    `report.ColumnStats` fields `key, member, scenario, n, reached, reached_outcome, wins, losses, unresolved,
    trades, x_range, x_mean, brackets, mean, mean_cost, g_se`.
  - Task 10: the engine honours `limits` (bands), `daily_loss`, `stop_entries_from`, `force_exit_from`, `cap_krw`
    and `delist_h` (Q29: the sale at p (1 - h) at the first check after the first entry fill, the loss booked as
    cost, no re-entry).
  - Task 11 (`core.odds.bold`): `ceiling(w0, l_min, target)`, `structural_max(limits)`, `brackets_needed(p, p0)`
    (`math.inf` at p == p0), `bracket_reference(r, d, *, w0, l_min, target, n_checks, kappa, phi_buy, phi_sell,
    r_exit)`.
  - Task 12 (`core.odds.report`): `hidden_range(*, target, phi_buy, phi_sell, kappa_bound, m_max, n_checks)`,
    `hidden_edge(col, *, w0, target, l_min) -> HiddenEdge` (`.status`, `.range_`; "unavailable" for a nan range,
    "not_applicable" on `assumed`), `cp_two_sided`, `cp_lower`, `ceiling_cells(cols, ceiling)`, `RED_ALPHA`,
    `flags_for(...)` (contract 10.1; IMPOSSIBLE is `info`/`structural.impossible` with slots `cap` and `s`),
    `build(**fields)` (spread None exactly when spread_kind is "none"), `render(rep)` (a `notes` entry renders
    `spread.dropped` with the `member.*` and `check.*` labels; `delist_30`/`delist_100` render `column.delist` with
    `h` "30"/"100" and `cost.delist`; the `assumed` column renders `assumed.lead`, `assumed.nb` or `assumed.nbmany`
    from `rep.assumed` and its ceiling line; MODEL_CHECK_FAILED's `{check}` comes from `check.<sub>`, and
    ASSUMED_EDGE_UNREACHABLE's `{w}` from its slots), `say`, `CATALOGUE`, `fmt_end`, `fmt_ceiling`, `fmt_prob`.
  - Task 13: `simulate`/`precheck`, the helpers `_headline_spec`, `_no_edge_pair`, `_refused_report`,
    `_report_provenance`, `_grey_slots`, `_cap_text`; fixtures `OF.pipeline(plan_obj=None, ctx=None,
    series_obj=None, *, n_paths=None, **changes)`, `OF.pipeline_inputs`, `OF.fresh_series(n=600, *, end, **changes)`,
    `OF.calendar_signed(sha)`, `OF.CAL_SHA`, `OF.spy(target, name)` (a list of `(args, kwargs, result)`).
  - Repo, tests only: `core.quant.garch.simulate_garch_series` (the fixture history), `core.calendars.clocks.
    sessions_between` with `tests.macro_m1_calendars.fixture_set()` (the fixture calendar, written in a tempfile
    directory, as Task 11's test does).
- Produces (`core/odds/simulate.py`, part 4; Task 17 builds the replay card on these):
  - `_accepted_report(plan_obj, ctx, inputs, *, inst, terms, market, sessions, screening, n) -> report.OddsReport`
    rewritten (same signature as Task 13's). An accepted report now holds, in this order: `no_edge/<member>/base`
    and `/stress2x` for each member run (the headline first, then `MEMBERS` order), `delist_30` and `delist_100` on
    a share or coin leg (headline member, base), and `assumed` on an assumed leg (headline bootstrap, base, theta of
    the pilot). `rep.notes` holds `(member, check)` per dropped member; `rep.spread` and `rep.spread_kind` (Q31);
    `rep.structural_cap`/`structural_sessions` on a buy-and-hold KRX leg; `rep.hidden` on the headline (always
    set; "unavailable" for GARCH-t); `rep.assumed` = `{w, p0, u, nb, resolved, theta}`; `model_key`
    "model.garch" for a garch_t headline; provenance `members` = the members run. New refusals found here:
    MODEL_CHECK_FAILED (sub = the failed check: "fit", "deterministic" or "statistical") and
    ASSUMED_EDGE_UNREACHABLE (slot `w`, e.g. "55%").
  - Private helpers: `_BLOCK_MULT`, `_members(headline, market)`, `_garch_member(member, fit, horizon, seed) ->
    (fits, check)`, `_hidden_range(spec) -> float`, `_column(spec, *, n, seed, key, member, scenario) ->
    ColumnStats` (run_column plus the range), `_tilt_theta(spec, p, seed) -> float | None`,
    `_assumed(col, p, theta) -> dict | None`, `_spread(columns, headline, track, market) -> (spread, kind)`,
    `_reference(col, spec, *, l_min, on)`. `_no_edge_pair` now runs `_column`. ASSUMED_EDGE_UNREACHABLE's `w` slot
    is Task 13's `_cap_text(leg.assumed_p)` (0.55 -> "55%").
  - Module globals read at call time: `_garch_member` reads `REFIT_B` and `_members` reads `MEMBERS` as module
    globals when called, never as a default argument or a copy taken at import (Task 18's crypto test swaps
    `simulate.REFIT_B` to 2; `OF.members()` swaps `MEMBERS`).
- Produces (`tests/odds_fixtures.py`, Task 14 block): `members(*names)` (swaps `simulate.MEMBERS`, save/restore) and
  `garch_series(n=600, *, seed=7, end="2026-10-22", symbol="KRW-BTC", source="UPBIT")`. No `test_*` name.

**Plan decisions used:** Q10 (pilot sizes, CHUNK at the real value), Q24 step 14 (the GARCH pilot, then the tilt
pilot), Q29 (delisting), Q30 (assumed edge and the tilt pilot), Q31 (members, spread, notes, MODEL_CHECK_FAILED),
Q32 (l_min, HIDDEN_EDGE on the headline, CEILING_BREACH over every no-edge cell, the spread's counts), Q33 (bracket
reference), Q42 (purity, now with the GARCH-t member), Q44 (IMPOSSIBLE), Q46 items 1, 2 and 9; RULINGS O10;
RULINGS_ROUND2 R2-8 (every refit pilot-checked). (R2-7's unbounded range is Task 12's: `report.hidden_range` returns
inf and Task 12 tests the "unbounded" status; `_hidden_range` passes that value through and adds no case of its own.)

Design notes (read before Step 3):
- **Members.** `_members(headline, market)` is the headline (`leg.model`) and then every other `MEMBERS` entry, read
  at call time; a KRX leg runs the three block-length members only (GARCH-t has no daily band). The bootstrap member
  keeps the block b of `_headline_spec`; half and double use `models.variant_block(b, 0.5 | 2.0, n_rows)`.
- **GARCH-t fits, the headline first.** The history's returns are fitted once (`models.fit_garch_t`). garch_t needs
  that fit converged ("fit" otherwise; `at_bound` alone is recorded, not a failure) and both pilot checks at the
  horizon's session count. garch_refit draws `REFIT_B` = 20 synthetic series of the fit's length from it (stream
  `refit_series`, spawn key b), refits each, and needs every refit converged and pilot-checked (R2-8); the first
  failure drops the member with check "refit"; a history fit that did not converge drops both members with "fit".
  The members run in `_members` order, so a garch_t headline is checked first and a failure is MODEL_CHECK_FAILED
  before any refit is fitted and before any column runs (no fallback headline, no number from a failed model). A
  failed spread member is left out with its note.
- **HIDDEN_EDGE's range is fixed before the run.** Task 9's `run_column` stores `x_range = nan` (its ledger minor
  says Task 14 wires the range). `_column` computes it from the spec alone (`_hidden_range`, contract 10.3: m_max of
  the history, p_min = p0 x prod(1 - limit) on KRX or p0 e^(-n_checks m_max) otherwise, `costs.kappa_bound` over
  the horizon dates, the scenario's charges) and replaces it into the column; GARCH-t columns keep nan
  ("unavailable"). Contract 10.3 says `run_column` stores it; doing it in `_column` keeps Task 9's text untouched
  and gives the same value, since the range never depends on the paths. This departs from the contract's wording,
  so Step 4 records it as a drift ruling: a direct `run_column` call (the delisting and assumed columns here,
  Task 17's replay) keeps the value its caller gives it, and a direct `run_column` call on a bootstrap no-edge spec
  gets nan. Delisting and edge columns keep nan (Q29: unavailable there; edge columns are "not applicable").
- **The tilt pilot** (`_tilt_theta`) runs `_run_paths` on `TILT_PILOT` paths, chunk 0, with a seed of 32 bytes drawn
  from stream `tilt` of the market seed: every theta sees the same paths (common random numbers), the pilot paths
  are independent of the columns', and nothing depends on CHUNK, so the pilot runs at the real CHUNK and gives the
  same theta under `OF.chunk()`. Bisection as Q30; a win rate with no resolved bracket is nan and fails every
  comparison, so it ends in ASSUMED_EDGE_UNREACHABLE. p0, u and the resolved count come from the full headline
  no-edge base column; a column that resolved no bracket has no p0 and is refused the same way.
- **Spread.** The base no-edge cells of every member but the headline, counted as the plain sentence counts
  (REACHED outcomes on moonshot cards, first passages on compounding cards); (lowest two-sided lower bound, highest
  upper bound); kind "none" (no other member), "krx" (KRX leg), "other" (another model family ran), else "blocks".
- **Structural cap** only for a buy-and-hold KRX leg (`bold.structural_max(price_limits)`, the session count);
  bracket legs re-enter, so they are never IMPOSSIBLE (Q44, decided here). The bracket reference runs only for a
  bracket leg, from the headline column's bracket sample: `record_brackets` is set on the headline member's spec of
  a bracket leg only (its base and 2x columns keep a sample; the base one is read), never on the other members'
  specs (up to 2 x BRACKET_SAMPLE values a column), and off for the delisting, assumed and pilot runs.
- **Budgets.** A full crypto run now fits 21 GARCH-t models, builds up to 21 correction tables and runs 21 pilot
  checks. Task 13's pipeline tests are not about the spread, so they run under `OF.members("bootstrap")` (the
  headline plus its delisting pair), and the purity test under `OF.members("bootstrap", "garch_t")` with
  `OF.pilots()`. Exactly one test (`test_every_member_runs_on_a_crypto_leg`) runs all 20 refits, under
  `OF.pilots(nodes=16)`; the corruption tests and the non-converged test stop at the first refit. Check 1 is
  deterministic (the table against quadrature at each node), so 16 nodes still see a 2e-6 error. On a quiet
  machine the module takes about 16 to 18 s, within contract 3.4's 30 s for columns (about 8 s of it in
  `test_every_member_runs_on_a_crypto_leg`); a heavily loaded machine has taken 64 to 93 s (Step 4 gives the
  measured times). Two tests run the real 20,000-path tilt pilot (contract 3.4 allows a pilot test that needs it).
- **Non-converged fits.** `models.fit_garch_t` is read at call time, so a test swaps it for a wrapper that returns
  `converged=False` from a chosen call on (call 1 is the history's fit, call 1 + b refit b): the history fit
  failing drops both GARCH members with "fit" and no pilot runs; on a garch_t headline it is MODEL_CHECK_FAILED with
  sub "fit"; a refit failing drops garch_refit with "refit" before that refit's pilot check.
- **Task 13's tests that change.** A coin or share leg now has its delisting pair, so the column counts, run counts
  and run indices of eight tests change. The placeholder test is replaced by the GARCH-t headline test it promised.

- [ ] **Step 1: Write the failing tests**

  First append the Task 14 block to `tests/odds_fixtures.py` with the Edit tool. Read the file; it ends with Task
  13's `pipeline`.

  **Edit 1** (`tests/odds_fixtures.py`, anchor: the end of `pipeline`, the last function of the file (Task 13's block); LF). `old_string`:

```text
    series_obj = fresh_series() if series_obj is None else series_obj
    return simulate.simulate(plan_obj, ctx, pipeline_inputs(plan_obj, series_obj, **changes), n_paths=n_paths)
```

  `new_string`:

```text
    series_obj = fresh_series() if series_obj is None else series_obj
    return simulate.simulate(plan_obj, ctx, pipeline_inputs(plan_obj, series_obj, **changes), n_paths=n_paths)


# --------------------------------------------------------------------------- #
# Task 14: the spread members a test runs, and a heavy-tailed history for the GARCH-t members
# --------------------------------------------------------------------------- #
@_contextmanager
def members(*names: str) -> "Iterator[None]":
    """core.odds.simulate.MEMBERS swapped for `names` (save/restore): the spread members a run adds to its
    headline, which always runs. A pipeline test that is not about the spread runs members("bootstrap"), so it
    skips the GARCH-t fits and their 21 pilot checks (contract 3.4 budgets)."""
    from core.odds import simulate
    saved = simulate.MEMBERS
    simulate.MEMBERS = tuple(names)
    try:
        yield
    finally:
        simulate.MEMBERS = saved


def garch_series(n: int = 600, *, seed: int = 7, end: str = "2026-10-22", symbol: str = "KRW-BTC",
                 source: str = "UPBIT"):
    """A daily history whose log closes follow a GARCH(1,1)-t path, core.quant.garch.simulate_garch_series(1.8e-5,
    0.08, 0.90, 5.0) (daily volatility about 3%, nu 5), each open equal to the previous close, the first close
    KRW 50,000,000 and the last bar dated `end`. Its tails are heavy, so the fit and every refit have nu below
    models.NU_NORMAL and the GARCH-t members use the correction table (a normal-looking fit would not)."""
    import datetime as dt

    import numpy as np

    from core.odds import plan as P
    from core.quant import garch
    moves = garch.simulate_garch_series(1.8e-5, 0.08, 0.90, 5.0, n=n - 1, seed=seed)
    close = 50_000_000.0 * np.exp(np.concatenate(([0.0], np.cumsum(moves))))
    open_ = np.concatenate(([close[0]], close[:-1]))
    last = dt.date.fromisoformat(end)
    dates = tuple((last - dt.timedelta(days=n - 1 - i)).isoformat() for i in range(n))
    o, c = tuple(float(x) for x in open_), tuple(float(x) for x in close)
    return P.Series(symbol=symbol, source=source, dates=dates, open=o, close=c, adjustment="", status="final",
                    md5=P.series_md5(symbol, source, dates, o, c, "", "final"))
```

  Then make these Edits to `tests/odds_pipeline.py` (read it first; each `old_string` occurs exactly once):

  **Edit 2** (removed: Task 13's import block already has `import math`.)

  **Edit 3** (removed: Task 13's `_strip` already reads a nan range as 0.0.)

  **Edit 4** (`tests/odds_pipeline.py`, anchor: `test_garch_headlines_are_refused_until_their_pilot_is_built`, the whole test (Task 13's placeholder); LF). `old_string`:

```python
def test_garch_headlines_are_refused_until_their_pilot_is_built():
    """Q24 step 14 placeholder (Task 14 replaces this test with the GARCH-t headline and its pilot checks): a garch_t
    leg on a crypto venue passes every earlier step, the gate included, and is MODEL_CHECK_FAILED (sub "fit", detail
    "garch not built yet"), so no number comes from an unchecked model."""
    with OF.chunk(), OF.spy(gate, "screen") as screens:
        rep = OF.pipeline(OF.plan(leg=dataclasses.replace(UPBIT, model="garch_t")))
    assert (rep.refused.code, rep.refused.sub, rep.refused.detail) == ("MODEL_CHECK_FAILED", "fit",
                                                                       "garch not built yet")
    assert len(screens) == 1 and rep.columns == () and _no_probability(report.render(rep))
```

  `new_string`:

```python
def test_a_garch_headline_runs_its_checked_model():
    """Q24 step 14, Q31 (Task 14 replaced Task 13's placeholder): a garch_t leg on a crypto venue passes every earlier
    step, the gate included (screen sees one float stake); its fit of the history converges and passes both pilot
    checks, so it is simulated: headline no_edge/garch_t/base with that one fit and a close check per session only,
    HIDDEN_EDGE unavailable (no finite range: a bounded shock does not bound the volatility), and the card names
    GARCH-t and its close-only checks."""
    leg = dataclasses.replace(UPBIT, model="garch_t")
    series_obj = OF.garch_series()
    with OF.chunk(), OF.pilots(), OF.members("garch_t"), OF.spy(gate, "screen") as screens, \
            OF.spy(simulate, "run_column") as runs:
        rep = OF.pipeline(OF.plan(leg=leg), series_obj=series_obj)
    assert rep.refused is None, rep.refused
    assert len(screens) == 1 and type(screens[0][0][2]) is float
    assert (rep.headline, rep.model_key, rep.spread, rep.notes) == ("no_edge/garch_t/base", "model.garch", None, ())
    spec = runs[0][0][0]
    assert spec.engine == "garch" and spec.fits == (models.fit_garch_t(models.rows(series_obj)[2]),)
    assert bool(spec.checks.close.all()) and len(spec.checks.on) == 10
    assert math.isnan(rep.columns[0].x_range) and rep.hidden.status == "unavailable"
    assert [f.key for f in rep.flags if f.code in ("HIDDEN_EDGE", "CLOSE_ONLY_CHECKS")] == [
        "hidden.unavailable", "flag.closeonly"]
    text = report.render(rep)
    assert report.say("hidden.unavailable") in text and report.say("flag.closeonly") in text
    assert text.count("Model: GARCH-t fitted to the daily won returns of BTC") == 1
```

  **Edit 5** (`tests/odds_pipeline.py`, anchor: `test_a_crypto_plan_gets_its_headline_column_at_base_and_2x_costs`, its run block; LF). `old_string`:

```text
    with OF.chunk(), OF.spy(simulate, "run_column") as runs:
        rep = OF.pipeline(series_obj=series_obj)
        stop = OF.pipeline(OF.plan(leg=stop_leg), series_obj=series_obj)
    assert rep.refused is None and stop.refused is None, (rep.refused, stop.refused)
    base, stress = rep.columns
```

  `new_string`:

```text
    with OF.chunk(), OF.members("bootstrap"), OF.spy(simulate, "run_column") as runs:
        rep = OF.pipeline(series_obj=series_obj)
        stop = OF.pipeline(OF.plan(leg=stop_leg), series_obj=series_obj)
    assert rep.refused is None and stop.refused is None, (rep.refused, stop.refused)
    base, stress, *delisted = rep.columns                  # Task 14: a coin leg adds its delisting pair
    assert [c.key for c in delisted] == ["delist_30", "delist_100"]
```

  **Edit 6** (`tests/odds_pipeline.py`, anchor: `test_a_crypto_plan_gets_its_headline_column_at_base_and_2x_costs`, its spread assertion; LF). `old_string`:

```text
    assert (rep.spread, rep.spread_kind, rep.notes, rep.hidden) == (None, "none", (), None)
```

  `new_string`:

```text
    assert (rep.spread, rep.spread_kind, rep.notes, rep.hidden.status) == (None, "none", (), "pass")   # Task 14
```

  **Edit 7** (`tests/odds_pipeline.py`, anchor: `test_a_plan_with_no_path_count_runs_the_default`, its run block; LF). `old_string`:

```text
    with OF.chunk():
        default = OF.pipeline()
        twice = OF.pipeline(n_paths=4_000)
```

  `new_string`:

```text
    with OF.chunk(), OF.members("bootstrap"):
        default = OF.pipeline()
        twice = OF.pipeline(n_paths=4_000)
```

  **Edit 8** (`tests/odds_pipeline.py`, anchor: `test_a_plan_with_no_path_count_runs_the_default`, its column assertions; LF). `old_string`:

```text
    assert [c.n for c in default.columns] == [2_000, 2_000] and default.n == 2_000
    assert [c.n for c in twice.columns] == [4_000, 4_000] and twice.n == 4_000
```

  `new_string`:

```text
    assert [c.n for c in default.columns] == [2_000] * 4 and default.n == 2_000    # Task 14: + the delisting pair
    assert [c.n for c in twice.columns] == [4_000] * 4 and twice.n == 4_000
```

  **Edit 9** (`tests/odds_pipeline.py`, anchor: `test_a_krx_leg_runs_only_under_the_signed_calendar`, its run count; LF). `old_string`:

```text
    assert len(days) == 6 and len(runs) == 2
```

  `new_string`:

```text
    assert len(days) == 6 and [run[1]["key"] for run in runs] == [     # Task 14: three members, delisting pair
        f"no_edge/{m}/{s}" for m in ("bootstrap", "bootstrap_half", "bootstrap_double") for s in ("base", "stress2x")
    ] + ["delist_30", "delist_100"]
```

  **Edit 10** (`tests/odds_pipeline.py`, anchor: `test_the_okx_leg_is_ack_required_simulated_and_flagged`, its run block; LF). `old_string`:

```text
    with OF.chunk(), OF.spy(gate, "screen") as screens, OF.spy(simulate, "run_column") as runs:
        rep = OF.pipeline(OF.plan(leg=OKX), series_obj=_okx_series())
```

  `new_string`:

```text
    with OF.chunk(), OF.members("bootstrap"), OF.spy(gate, "screen") as screens, \
            OF.spy(simulate, "run_column") as runs:
        rep = OF.pipeline(OF.plan(leg=OKX), series_obj=_okx_series())
```

  **Edit 11** (`tests/odds_pipeline.py`, anchor: `test_the_okx_leg_is_ack_required_simulated_and_flagged`, its cap assertion; LF). `old_string`:

```text
    assert [run[0][0].cap_krw for run in runs] == [4_200.0, 4_200.0]
```

  `new_string`:

```text
    assert [run[0][0].cap_krw for run in runs] == [4_200.0] * 4         # Task 14: + the delisting pair
```

  **Edit 12** (`tests/odds_pipeline.py`, anchor: `test_rule_dates_come_from_the_screening_flags`, its run block and dates; LF). `old_string`:

```text
    with OF.chunk(), OF.spy(simulate, "run_column") as runs:
        long_ = OF.pipeline(OF.plan(horizon_days=60))
        short = OF.pipeline(OF.plan())
    dates = [(run[0][0].stop_entries_from, run[0][0].force_exit_from) for run in runs]
    assert dates == [(dt.date(2026, 11, 22), None)] * 2 + [(None, None)] * 2, dates
```

  `new_string`:

```text
    with OF.chunk(), OF.members("bootstrap"), OF.spy(simulate, "run_column") as runs:
        long_ = OF.pipeline(OF.plan(horizon_days=60))
        short = OF.pipeline(OF.plan())
    dates = [(run[0][0].stop_entries_from, run[0][0].force_exit_from) for run in runs]
    assert dates == [(dt.date(2026, 11, 22), None)] * 4 + [(None, None)] * 4, dates     # 4 columns a plan
```

  **Edit 13** (`tests/odds_pipeline.py`, anchor: `test_an_okx_horizon_across_auto_off_is_forced_out`, its run block; LF). `old_string`:

```text
    with OF.chunk(), OF.spy(simulate, "run_column") as runs:
        long_ = OF.pipeline(OF.plan(leg=OKX, horizon_days=60), series_obj=series_obj)
        short = OF.pipeline(OF.plan(leg=OKX, horizon_days=41), series_obj=series_obj)
    long_spec, short_spec = runs[0][0][0], runs[2][0][0]
```

  `new_string`:

```text
    with OF.chunk(), OF.members("bootstrap"), OF.spy(simulate, "run_column") as runs:
        long_ = OF.pipeline(OF.plan(leg=OKX, horizon_days=60), series_obj=series_obj)
        short = OF.pipeline(OF.plan(leg=OKX, horizon_days=41), series_obj=series_obj)
    long_spec, short_spec = runs[0][0][0], runs[4][0][0]        # Task 14: 4 columns a plan
```

  **Edit 14** (`tests/odds_pipeline.py`, anchor: `test_an_okx_horizon_across_auto_off_is_forced_out`, its seed assertion; LF). `old_string`:

```text
    assert runs[0][1]["seed"] == runs[2][1]["seed"]
```

  `new_string`:

```text
    assert runs[0][1]["seed"] == runs[4][1]["seed"]
```

  **Edit 15** (`tests/odds_pipeline.py`, anchor: `test_one_comparison_shares_its_streams`, its run block; LF). `old_string`:

```text
    with OF.chunk(), OF.spy(simulate, "run_column") as runs:
        a = OF.pipeline(OF.plan(name="first"), ctx, series_obj)
```

  `new_string`:

```text
    with OF.chunk(), OF.members("bootstrap"), OF.spy(simulate, "run_column") as runs:
        a = OF.pipeline(OF.plan(name="first"), ctx, series_obj)
```

  **Edit 16** (`tests/odds_pipeline.py`, anchor: `test_one_comparison_shares_its_streams`, its seed assertion; LF). `old_string`:

```text
    assert len(set(seeds[:6])) == 1 and seeds[6] == seeds[7] != seeds[0] and seeds[8] == seeds[0]
```

  `new_string`:

```text
    assert len(seeds) == 20 and len(set(seeds[:12])) == 1 and len(set(seeds[12:16])) == 1   # 4 columns a plan
    assert seeds[12] != seeds[0] and set(seeds[16:]) == {seeds[0]}
```

  **Edit 17** (`tests/odds_pipeline.py`, anchor: `test_simulate_is_pure_after_a_warm_up`, its docstring and run block; LF). `old_string`:

```text
    """Q42: after one warm-up run (every lazy import loaded), a crypto run with open, io.open, os.open, socket
    connect and time.time patched to raise gives the same report."""
    def trap(*args, **kwargs):
        raise AssertionError("simulate reached a file, a socket or the clock")
    plan_obj, series_obj, ctx = OF.plan(), OF.fresh_series(), OF.odds_ctx()
    inputs = OF.pipeline_inputs(plan_obj, series_obj)
    with OF.chunk():
```

  `new_string`:

```text
    """Q42: after one warm-up run (every lazy import loaded), a crypto run with open, io.open, os.open, socket
    connect and time.time patched to raise gives the same report; the GARCH-t member's fit, its pilot checks
    (scipy's quad) and its draws run inside the traps too (Task 14)."""
    def trap(*args, **kwargs):
        raise AssertionError("simulate reached a file, a socket or the clock")
    plan_obj, series_obj, ctx = OF.plan(), OF.garch_series(), OF.odds_ctx()
    inputs = OF.pipeline_inputs(plan_obj, series_obj)
    with OF.chunk(), OF.pilots(), OF.members("bootstrap", "garch_t"):
```

  **Edit 18** (`tests/odds_pipeline.py`, anchor: `test_simulate_is_pure_after_a_warm_up`, its last assertions; LF). `old_string`:

```text
    assert first.refused is None and _strip(again) == _strip(first)
```

  `new_string`:

```text
    assert first.refused is None and dict(first.provenance)["members"] == ("bootstrap", "garch_t")
    assert _strip(again) == _strip(first)
```

  **Edit 19** (`tests/odds_pipeline.py`, anchor: `test_every_refusal_in_q24_order`, its docstring; LF). `old_string`:

```text
    """Q24, O10: one fixture per refusal, in the reporting order (CARD_NOT_REPRODUCED and MODEL_CHECK_FAILED have
    their own tests below), plus two that break two steps at once and report the earlier: stale data under an unsigned
    calendar (step 6 before 7) and a KRX GARCH-t leg on a KRW 1 share (11 before 12). Each is a refused report with
    no column, no flag and no probability, rendering its sentence. screen() is reached only by the SCREEN_BLOCKED
    case, with a positive float stake (O11)."""
```

  `new_string`:

```text
    """Q24, O10: one fixture per refusal, in the reporting order (CARD_NOT_REPRODUCED has its own test below,
    MODEL_CHECK_FAILED its own in tests/odds_columns.py since Task 14), plus two that break two steps at once and
    report the earlier: stale data under an unsigned calendar (step 6 before 7) and a KRX GARCH-t leg on a KRW 1 share
    (11 before 12). Each is a refused report with no column, no flag and no probability, rendering its sentence.
    screen() is reached only by the SCREEN_BLOCKED case, with a positive float stake (O11)."""
```

  Then create `tests/odds_columns.py` (LF):

```python
"""Odds plan Task 14: simulate()'s columns (spec 7.2, 7.4, 7.5 items 8-10, 9; O10; R2-8; Q29-Q33, Q44). Every member
at base and 2x costs with the GARCH-t fits and every pilot check, the spread and its wording, a dropped member's
note (a failed check or a fit that did not converge), MODEL_CHECK_FAILED, HIDDEN_EDGE's range fixed before the run,
the ceilings and CEILING_BREACH, the delisting and assumed columns, the tilt pilot and the structural cap. Every test
runs under OF.chunk() (2,000 paths a chunk); the two real-size tests run at the real CHUNK and TILT_PILOT, as
contract 3.4 budgets them."""
from __future__ import annotations

import contextlib
import dataclasses
import datetime as dt
import math
import re

import numpy as np

from core.compliance import gate
from core.odds import bold, costs, models, report, simulate
from core.odds import plan as P
from tests import odds_fixtures as OF

UPBIT = P.Leg(venue="upbit", symbol="BTC", model="bootstrap")
STOCK = P.Leg(venue="kis", symbol="005930", model="bootstrap")
ETF = P.Leg(venue="kis", symbol="069500", model="bootstrap")
BLOCKS = ("bootstrap", "bootstrap_half", "bootstrap_double")
BRACKET = P.Bracket(take_profit=0.02, stop=0.02)


def _krx_series(symbol: str, **changes):
    """A KIS daily history of 600 bars near KRW 5,000, ending the day before the start."""
    return OF.fresh_series(**{"symbol": symbol, "source": "KIS", "price": 5_000.0, "vol": 0.005, **changes})


def _no_probability(text: str) -> bool:
    """Spec 9: no computed probability in the text: no "1 in", no "below about", no digit followed by "%"."""
    return "1 in " not in text and "below about" not in text and re.search(r"[0-9]%", text) is None


def _cells(rep) -> list:
    """The card's no-edge cells: every member at base and 2x costs (never a delisting or edge column)."""
    return [c for c in rep.columns if c.key.startswith("no_edge/")]


def _win(col) -> float:
    """A column's win rate: take-profit fills among the brackets resolved by take-profit or stop."""
    return col.wins / (col.wins + col.losses)


@contextlib.contextmanager
def _corrupted_table():
    """models._correction_table swapped for a wrapper whose ratio column is raised by 2e-6 / grid ** 2, so every
    tabulated c(sigma) is 2e-6 too high (contract 7.4's corruption, which check 1 must see); restored afterwards. The
    real table's lru cache keeps only clean values, since the wrapper adds on top of them."""
    real = models._correction_table

    def corrupted(nu, bound):
        z, wt, grid, ratio = real(nu, bound)
        return z, wt, grid, ratio + 2e-6 / grid ** 2

    models._correction_table = corrupted
    try:
        yield
    finally:
        models._correction_table = real


@contextlib.contextmanager
def _fits_converge_until(k: int):
    """models.fit_garch_t swapped for a wrapper whose fits from call k + 1 on come back with converged=False (the
    same parameters otherwise); restored afterwards. Call 1 is the history's fit, call 1 + b refit b."""
    real = models.fit_garch_t
    calls = []

    def fit(returns):
        calls.append(None)
        out = real(returns)
        return out if len(calls) <= k else dataclasses.replace(out, converged=False)

    models.fit_garch_t = fit
    try:
        yield
    finally:
        models.fit_garch_t = real


def test_every_member_runs_on_a_crypto_leg():
    """Q31 (R2-8), spec 7.5 items 8-9: a crypto bootstrap leg runs all five members at base and 2x costs on one seed,
    then its delisting pair. The half and double members use the block b' of models.variant_block; garch_t uses the
    one fit of the history and garch_refit 20 distinct refits, each refit pilot-checked (21 pilot checks, all
    passed). The spread is [lowest lower, highest upper] of the four other base cells, worded spread.other and
    printed outward; no no-edge cell breaches its ceiling at the Bonferroni level; HIDDEN_EDGE passes; the
    delisting columns print their cost words."""
    series_obj = OF.fresh_series(vol=0.05)
    plan_obj = OF.plan(target_krw=46_200.0)
    with OF.chunk(), OF.pilots(nodes=16), OF.spy(simulate, "run_column") as runs, \
            OF.spy(models, "pilot_checks") as pilots:
        rep = OF.pipeline(plan_obj, series_obj=series_obj)
    assert rep.refused is None, rep.refused
    assert [c.key for c in rep.columns] == [f"no_edge/{m}/{s}" for m in simulate.MEMBERS
                                            for s in ("base", "stress2x")] + ["delist_30", "delist_100"]
    assert len({run[1]["seed"] for run in runs}) == 1
    specs = {run[1]["key"]: run[0][0] for run in runs}
    m_o, _, r = models.rows(series_obj)
    b = models.block_length(r)
    assert [specs[f"no_edge/{m}/base"].block for m in BLOCKS] == [
        b, models.variant_block(b, 0.5, len(m_o)), models.variant_block(b, 2.0, len(m_o))]
    fit = models.fit_garch_t(r)
    garch, refit = specs["no_edge/garch_t/base"], specs["no_edge/garch_refit/base"]
    assert (garch.engine, garch.fits, refit.engine) == ("garch", (fit,), "garch")
    assert len(refit.fits) == simulate.REFIT_B == 20 and len(set(refit.fits)) == 20 and fit not in refit.fits
    assert bool(garch.checks.close.all()) and len(garch.checks.on) == plan_obj.horizon_days
    assert [args[0] for args, _, _ in pilots] == [fit, *refit.fits]
    assert {result for _, _, result in pilots} == {(True, "")}
    others = [c for c in rep.columns if c.scenario == "base" and c.key.startswith("no_edge/") and c.key != rep.headline]
    assert [c.member for c in others] == list(simulate.MEMBERS[1:])
    bounds = [report.cp_two_sided(c.reached, c.n) for c in others]     # compounding card: first passages
    lo, hi = min(x for x, _ in bounds), max(y for _, y in bounds)
    assert rep.spread == (lo, hi) and 0.0 < lo < hi, rep.spread
    assert (rep.spread_kind, rep.notes, rep.hidden.status) == ("other", (), "pass")
    assert len(_cells(rep)) == 10 and report.ceiling_cells(_cells(rep), rep.ceiling)[0] != "red"
    assert not any(f.level == "red" for f in rep.flags)
    assert dict(rep.provenance)["members"] == simulate.MEMBERS
    text = report.render(rep)
    line = next(x for x in text.splitlines() if "other models give" in x)
    assert report.fmt_end(lo, upper=False) in line and report.fmt_end(hi, upper=True) in line, line
    for h in ("30", "100"):
        assert report.say("column.delist", symbol="BTC", h=h) in text
    assert report.say("cost.delist", base=report.say("cost.fees")) in text


def test_a_corrupted_correction_table_drops_both_garch_members():
    """Q31, spec 9: with every tabulated c(sigma) 2e-6 too high, the GARCH-t member fails its deterministic check and
    the refit member its first refit's, so both are left out with their notes; the bootstrap members still run, the
    spread takes the block-length wording (spread.blocks, no KRX clause) and the card says which check failed."""
    with OF.chunk(), OF.pilots(nodes=16), _corrupted_table(), OF.spy(models, "pilot_checks") as pilots:
        rep = OF.pipeline(series_obj=OF.garch_series())
    assert rep.refused is None, rep.refused
    assert rep.notes == (("garch_t", "deterministic"), ("garch_refit", "refit")), rep.notes
    assert [result for _, _, result in pilots] == [(False, "deterministic")] * 2     # the fit, then refit 1
    assert [c.member for c in _cells(rep) if c.scenario == "base"] == list(BLOCKS)
    assert rep.spread_kind == "blocks" and dict(rep.provenance)["members"] == BLOCKS
    text = report.render(rep)
    assert "GARCH-t was left out because its deterministic check failed" in text
    assert "the GARCH-t refit was left out because its refit check failed" in text
    assert report.CATALOGUE["spread.blocks"].split("{")[0] in text and "no second model family" not in text


def test_a_corrupted_garch_headline_is_model_check_failed():
    """Q24 step 14, Q31: when the plan's own model fails its pilot check there is no fallback headline: the leg is
    refused MODEL_CHECK_FAILED with that check, before any column runs and before any refit is fitted, and the card
    prints no number."""
    leg = dataclasses.replace(UPBIT, model="garch_t")
    with OF.chunk(), OF.pilots(nodes=16), _corrupted_table(), OF.spy(gate, "screen") as screens, \
            OF.spy(simulate, "run_column") as runs, OF.spy(models, "pilot_checks") as pilots:
        rep = OF.pipeline(OF.plan(leg=leg), series_obj=OF.garch_series())
    assert (rep.refused.code, rep.refused.sub) == ("MODEL_CHECK_FAILED", "deterministic"), rep.refused
    assert rep.columns == () and runs == [] and len(screens) == 1 and len(pilots) == 1
    text = report.render(rep)
    assert report.say("why.MODEL_CHECK_FAILED", check=report.say("check.deterministic")) in text
    assert _no_probability(text), text


def test_a_fit_that_does_not_converge_drops_its_members():
    """Q31 (C4), R2-8: a history fit that did not converge drops both GARCH members with check "fit" and no pilot
    check runs on it; on a garch_t headline the same fit is MODEL_CHECK_FAILED with sub "fit" and no column. A refit
    that did not converge drops the refit member with check "refit" before that refit's pilot check, while garch_t,
    whose own fit converged, runs after its one pilot check."""
    series_obj = OF.garch_series()
    leg = dataclasses.replace(UPBIT, model="garch_t")
    with OF.chunk(), OF.pilots(nodes=16), OF.members("bootstrap", "garch_t", "garch_refit"), \
            OF.spy(models, "pilot_checks") as pilots:
        with _fits_converge_until(0):
            both = OF.pipeline(series_obj=series_obj)
        with _fits_converge_until(0):
            head = OF.pipeline(OF.plan(leg=leg), series_obj=series_obj)
        with _fits_converge_until(1):
            refit = OF.pipeline(series_obj=series_obj)
    assert both.refused is None and both.notes == (("garch_t", "fit"), ("garch_refit", "fit")), both.notes
    assert (both.spread_kind, dict(both.provenance)["members"]) == ("none", ("bootstrap",))
    assert "GARCH-t was left out because its fit check failed" in report.render(both)
    assert (head.refused.code, head.refused.sub, head.columns) == ("MODEL_CHECK_FAILED", "fit", ()), head.refused
    assert report.say("why.MODEL_CHECK_FAILED", check=report.say("check.fit")) in report.render(head)
    assert refit.refused is None and refit.notes == (("garch_refit", "refit"),), refit.notes
    assert dict(refit.provenance)["members"] == ("bootstrap", "garch_t")
    assert len(pilots) == 1 and pilots[0][2] == (True, ""), pilots      # garch_t's own; refit 1 never reaches one


def test_hidden_edge_range_is_fixed_from_the_plan_and_the_history():
    """Contract 10.3, Q32: each headline no-edge cell carries R = V_max + n_checks x C_max, fixed before the run from
    the target, the venue's charges, costs.kappa_bound at the lowest price the model can reach (crypto: p0 x
    e^(-n_checks x m_max); KRX: p0 x the product of (1 - limit) over the sessions) and the largest move of the
    history, the stress cell with doubled charges; another comparison (another seed, other paths) gets the same R;
    HIDDEN_EDGE passes on these no-edge bootstrap runs."""
    crypto_plan, etf_plan = OF.plan(target_krw=63_000.0), OF.plan(leg=ETF, target_krw=63_000.0)
    with OF.chunk(), OF.members("bootstrap"):
        crypto = OF.pipeline(crypto_plan)
        other = OF.pipeline(crypto_plan, comparison_id="c000002")
        with OF.calendar_signed(OF.CAL_SHA):
            etf = OF.pipeline(etf_plan, series_obj=_krx_series("069500"))
    ctx = OF.odds_ctx()
    for rep, plan_obj, series_obj in ((crypto, crypto_plan, OF.fresh_series()),
                                      (etf, etf_plan, _krx_series("069500"))):
        inputs = OF.pipeline_inputs(plan_obj, series_obj)
        venue, inst = P.instrument(plan_obj, ctx)
        terms = costs.terms(venue, inst, plan_obj.fx_krw_per_usd)
        m_o, m_i, _ = models.rows(series_obj)
        m_max = float(max(m_o.max(), m_i.max()))
        dates = tuple(dt.date.fromisoformat(d) for d in inputs.sessions)
        n_checks, p0 = 2 * len(dates), series_obj.close[-1]
        p_min = (p0 * float(np.prod(1.0 - np.asarray(inputs.price_limits))) if inputs.price_limits
                 else p0 * math.exp(-n_checks * m_max))
        for col in rep.columns[:2]:
            mult = costs.SCENARIOS[col.scenario]
            want = report.hidden_range(target=63_000.0, phi_buy=mult * terms.phi_buy, phi_sell=mult * terms.phi_sell,
                                       kappa_bound=costs.kappa_bound(terms, p_min, dates, mult), m_max=m_max,
                                       n_checks=n_checks)
            assert math.isfinite(want) and col.x_range == want, (rep.headline, col.scenario, col.x_range, want)
        assert rep.hidden.status == "pass" and rep.hidden.range_ == rep.columns[0].x_range
    assert [c.x_range for c in other.columns[:2]] == [c.x_range for c in crypto.columns[:2]]
    assert other.columns[0].x_mean != crypto.columns[0].x_mean


def test_the_ceiling_matches_the_sizing():
    """Q32, header "Real odds": stake KRW 42,000, target KRW 42,000,000, floor KRW 21,000. The floor-protected card
    prints "1 in 1,999" and the stop-based one "1 in 1,000" (L_min = 0: a gap can pass the stop), and simulate gives
    report.flags_for that card's own ceiling and every no-edge cell (3 members x 2 scenarios): 4 first passages in
    2,000 planted in one non-headline cell (a 95% lower bound of 6.8e-4, between the two ceilings) raise the amber
    CEILING_BREACH on the floor-protected card only."""
    floor_leg = dataclasses.replace(UPBIT, bracket=P.Bracket(take_profit=0.5, stop=0.2))
    stop_leg = dataclasses.replace(floor_leg, sizing="stop_based")
    with OF.chunk(), OF.members(*BLOCKS), OF.spy(report, "flags_for") as calls:
        floor_rep = OF.pipeline(OF.plan(leg=floor_leg))
        stop_rep = OF.pipeline(OF.plan(leg=stop_leg))
    assert (floor_rep.ceiling, stop_rep.ceiling) == (bold.ceiling(42_000.0, 21_000.0, 42_000_000.0),
                                                     bold.ceiling(42_000.0, 0.0, 42_000_000.0))
    floor_text, stop_text = report.render(floor_rep), report.render(stop_rep)
    assert report.say("ceiling.noedge", c="1 in 1,999") in floor_text and "1 in 1,000." not in floor_text
    assert report.say("ceiling.nofloor", c="1 in 1,000") in stop_text and "1 in 1,999" not in stop_text
    assert floor_rep.ceiling < report.cp_lower(4, 2_000, 0.95) < stop_rep.ceiling
    levels = []
    for (_, kwargs, _), rep in zip(calls, (floor_rep, stop_rep), strict=True):
        cells = kwargs["no_edge"]
        assert kwargs["ceiling"] == rep.ceiling and [c.key for c in cells] == [c.key for c in _cells(rep)]
        assert len(cells) == 6 and all(c.reached == 0 for c in cells)
        planted = tuple(dataclasses.replace(c, reached=4) if c.key == "no_edge/bootstrap_double/stress2x" else c
                        for c in cells)
        flags = report.flags_for(**{**kwargs, "no_edge": planted})
        levels.append([(f.level, f.key) for f in flags if f.code == "CEILING_BREACH"])
    assert levels == [[("amber", "breach.amber")], []], levels


def test_no_edge_cells_never_breach_their_ceiling_at_the_bonferroni_level():
    """Spec 8.o 3: on no-edge runs of several fixture plans (bold play on a reachable target, floor-protected and
    stop-based; a moonshot buy-and-hold; a KRX ETF bracket), no cell's first-passage count has a one-sided
    1 - 0.001/m lower bound above the card's ceiling, m its no-edge cells (3 members x 2 scenarios), so
    CEILING_BREACH never turns red. On its wild 10-day fixture (25% daily moves at the open and at the close) the
    floor-protected bold plan reaches KRW 52,500 in more than half the share its ceiling of 2/3 allows, so the check
    bites. The same cards pin the spread's kind (spread.krx and its KRX clause on the KRX leg, spread.blocks on the
    others) and Q32's counts: the moonshot spread counts REACHED outcomes. A crypto exit never locks, so there every
    REACHED outcome is a first passage; _spread is also run on planted counts that tell the two apart."""
    wild = OF.fresh_series(vol=0.25, open_gap=0.25)
    bold_leg = dataclasses.replace(UPBIT, bracket=P.Bracket(take_profit=0.5, stop=0.5))
    krx_leg = dataclasses.replace(ETF, bracket=P.Bracket(take_profit=0.3, stop=0.2))
    with OF.chunk(), OF.members(*BLOCKS):
        reps = [OF.pipeline(OF.plan(leg=bold_leg, fraction=P.bold(), target_krw=52_500.0), series_obj=wild),
                OF.pipeline(OF.plan(leg=dataclasses.replace(bold_leg, sizing="stop_based"), fraction=P.bold(),
                                    target_krw=52_500.0), series_obj=wild),
                OF.pipeline(OF.plan(track="moonshot", target_krw=50_400.0), series_obj=wild)]
        with OF.calendar_signed(OF.CAL_SHA):
            reps.append(OF.pipeline(OF.plan(leg=krx_leg, target_krw=63_000.0),
                                    series_obj=_krx_series("069500", vol=0.05)))
    for rep in reps:
        assert rep.refused is None, rep.refused
        cells = _cells(rep)
        m = len(cells)
        assert m == 6 and report.ceiling_cells(cells, rep.ceiling)[0] != "red", rep.headline
        assert all(report.cp_lower(c.reached, c.n, 1.0 - report.RED_ALPHA / m) <= rep.ceiling for c in cells)
        assert not any(f.code == "CEILING_BREACH" and f.level == "red" for f in rep.flags)
    assert max(c.reached / c.n for c in _cells(reps[0])) > 0.5 * reps[0].ceiling, reps[0].ceiling
    assert [rep.spread_kind for rep in reps] == ["blocks", "blocks", "blocks", "krx"]
    assert report.CATALOGUE["spread.krx"].split("}")[-1] in report.render(reps[3])     # "; no second model family..."
    moon = reps[2]
    bounds = [report.cp_two_sided(c.reached_outcome, c.n) for c in _cells(moon)[2::2]]  # half and double, base
    assert moon.spread == (min(x for x, _ in bounds), max(y for _, y in bounds)), moon.spread
    planted = [dataclasses.replace(c, reached_outcome=c.reached // 2) for c in _cells(moon)]
    for track, count in (("moonshot", "reached_outcome"), ("compounding", "reached")):
        bounds = [report.cp_two_sided(getattr(c, count), c.n) for c in planted[2::2]]
        want = (min(x for x, _ in bounds), max(y for _, y in bounds))
        assert simulate._spread(planted, planted[0], track, "CRYPTO") == (want, "blocks"), track


def test_an_assumed_win_rate_tilts_the_assumed_column():
    """Q30, spec 7.2 "Assumed edge": theta is bisected on the 20,000-path tilt pilot, and the assumed column (the
    headline bootstrap at base costs, tilted) wins within 0.01 of the typed 0.70. Its card leads with the typed and
    no-edge rates, prints assumed.nb with bold.brackets_needed(0.70, p0) and its ceiling line; p0, the unresolved
    share and the resolved count come from the full no-edge base column. A typed p above p0 never raises
    HIDDEN_EDGE (spec 8.o 2): the check runs on the no-edge headline and passes, though the same check on the
    assumed column itself would fail red."""
    leg = dataclasses.replace(UPBIT, bracket=BRACKET, edge_source="assumed", assumed_p=0.70)
    with OF.chunk(), OF.members("bootstrap"):
        rep = OF.pipeline(OF.plan(leg=leg, target_krw=63_000.0), series_obj=OF.fresh_series(vol=0.04, open_gap=0.04),
                          n_paths=6_000)
    assert rep.refused is None, rep.refused
    head = rep.columns[0]
    col = next((c for c in rep.columns if c.key == "assumed"), None)
    assert col is not None, [c.key for c in rep.columns]
    assert (col.member, col.scenario, col.n) == ("bootstrap", "base", 6_000)
    assert abs(_win(col) - 0.70) <= 0.01, _win(col)
    a, resolved = rep.assumed, head.wins + head.losses
    assert (a["w"], a["p0"], a["resolved"]) == (0.70, _win(head), resolved)
    assert a["u"] == head.unresolved / (resolved + head.unresolved)
    assert a["nb"] == bold.brackets_needed(0.70, _win(head)) <= resolved
    assert 0.0 < a["theta"] < simulate.TILT_BOUND
    text = report.render(rep)
    assert report.CATALOGUE["assumed.lead"].split("{")[0] in text
    assert report.say("assumed.nb", nb=f"{int(a['nb']):,}") in text
    assert report.say("assumed.ceiling", c=report.fmt_ceiling(rep.ceiling)) in text
    assert rep.hidden.status == "pass" and not any(f.level == "red" for f in rep.flags)
    as_no_edge = dataclasses.replace(col, key=rep.headline, x_range=head.x_range)
    assert report.hidden_edge(as_no_edge, w0=42_000.0, target=63_000.0, l_min=21_000.0).status == "red_gain"


def test_a_typed_rate_equal_to_the_no_edge_rate_needs_more_brackets_than_resolved():
    """Q30, catalogue assumed.nbmany: a typed rate equal to the bracket's own no-edge win rate p0 cannot be told
    apart from it by any number of brackets (bold.brackets_needed is inf), so the card prints assumed.nbmany with the
    resolved count. The headline does not depend on the typed rate (plan fields never enter a stream)."""
    bracket_leg = dataclasses.replace(UPBIT, bracket=BRACKET)
    series_obj = OF.fresh_series(vol=0.04, open_gap=0.04)
    with OF.chunk(), OF.pilots(), OF.members("bootstrap"):
        plain = OF.pipeline(OF.plan(leg=bracket_leg), series_obj=series_obj)
        p0 = _win(plain.columns[0])
        typed = dataclasses.replace(bracket_leg, edge_source="assumed", assumed_p=p0)
        rep = OF.pipeline(OF.plan(leg=typed), series_obj=series_obj)
    assert rep.refused is None, rep.refused
    assert rep.columns[0] == plain.columns[0]
    assert (rep.assumed["p0"], rep.assumed["nb"]) == (p0, math.inf)
    resolved = plain.columns[0].wins + plain.columns[0].losses
    assert report.say("assumed.nbmany", r=f"{resolved:,}") in report.render(rep)


def test_an_unreachable_typed_rate_is_refused():
    """Q30, Q24 step 14: a take-profit of 1,000x is never filled in 10 days, so every resolved bracket of this leg
    is a stop and no tilt reaches a typed 55% win rate (it lies outside [win(-8), win(8)]): the leg is refused
    ASSUMED_EDGE_UNREACHABLE after the tilt pilot and before any column runs, and the refused card prints the typed
    rate and no computed probability."""
    leg = dataclasses.replace(UPBIT, bracket=P.Bracket(take_profit=1_000.0, stop=0.02), edge_source="assumed",
                              assumed_p=0.55)
    with OF.chunk(), OF.pilots(), OF.members("bootstrap"), OF.spy(simulate, "run_column") as runs:
        rep = OF.pipeline(OF.plan(leg=leg), series_obj=OF.fresh_series(vol=0.04, open_gap=0.04))
    assert (rep.refused.code, dict(rep.refused.slots)) == ("ASSUMED_EDGE_UNREACHABLE", {"w": "55%"}), rep.refused
    assert runs == [] and rep.columns == ()
    text = report.render(rep)
    assert report.say("why.ASSUMED_EDGE_UNREACHABLE", w="55%") in text
    assert _no_probability(text.replace("(55%)", "")), text


def test_a_buy_and_hold_krx_moonshot_is_impossible():
    """Q44, spec 7.4, 8.o 4: KRX's daily band caps a buy-and-hold leg at (1 + l1)/(1 - l1) x the product of (1 + li)
    over the horizon's sessions. The fixture calendar's 30-day horizon from 2026-10-23 holds 21 KRX sessions; at
    0.30 that is about 353x, so KRW 42,000 -> KRW 42,000,000 is IMPOSSIBLE and the card's headline, plain and
    ladder-target lines print no probability. A bracket leg on the same sessions is never IMPOSSIBLE (it re-enters)
    and prints its headline probability."""
    from core.calendars import clocks
    from tests.macro_m1_calendars import fixture_set
    start = dt.date(2026, 10, 23)
    days = tuple(d.isoformat() for d in clocks.sessions_between("KR", start, start + dt.timedelta(days=29),
                                                                    cal=fixture_set()))
    limits = (0.30,) * len(days)
    cap = bold.structural_max(limits)
    hold = OF.plan(leg=ETF, track="moonshot", horizon_days=30)
    swing = OF.plan(leg=dataclasses.replace(ETF, bracket=P.Bracket(take_profit=0.5, stop=0.2)), track="moonshot",
                    horizon_days=30)
    with OF.chunk(), OF.calendar_signed(OF.CAL_SHA):
        rep, other = (OF.pipeline(p, series_obj=_krx_series("069500"), sessions=days, price_limits=limits)
                      for p in (hold, swing))
    assert rep.refused is None and other.refused is None, (rep.refused, other.refused)
    assert (len(days), days[0], days[-1], math.ceil(cap)) == (21, "2026-10-23", "2026-11-20", 353)
    assert (rep.structural_cap, rep.structural_sessions) == (cap, len(days))
    (flag,) = [f for f in rep.flags if f.code == "IMPOSSIBLE"]
    assert (flag.level, flag.key, flag.slots["s"]) == ("info", "structural.impossible", f"{len(days):,}")
    assert not any(f.code == "BELOW_RESOLUTION" for f in rep.flags)
    text = report.render(rep)
    assert report.say(flag.key, **flag.slots) in text
    assert report.say("ladder.impossible", label=report.say("ladder.target"), value="42,000,000") in text
    target_lines = [line for line in text.splitlines() if "42,000,000" in line]
    assert target_lines and all(_no_probability(line) for line in target_lines), target_lines
    assert other.structural_cap is None and not any(f.code == "IMPOSSIBLE" for f in other.flags)
    assert report.say("headline.moonshot", target="42,000,000", p=report.fmt_prob(other.columns[0].reached_outcome,
                                                                                   2_000)) in report.render(other)


def test_the_delisting_columns_of_a_share_leg():
    """Q29, spec 7.2 "Delisting stress": a share or coin leg (never a 1x ETF) runs delist_30 and delist_100 on the
    headline member at base costs: at the first check after the first entry fill the position is sold at p (1 - h),
    the h x value loss booked as cost, so the gross value stays a martingale (mean V + cost within 4 SE of the
    stake); the card prints each column with its cost words (here the securities transaction tax and the delisting
    stress loss)."""
    with OF.chunk(), OF.members("bootstrap"), OF.calendar_signed(OF.CAL_SHA), \
            OF.spy(simulate, "run_column") as runs:
        stock = OF.pipeline(OF.plan(leg=STOCK), series_obj=_krx_series("005930"))
        etf = OF.pipeline(OF.plan(leg=ETF), series_obj=_krx_series("069500"))
    keys = [c.key for c in stock.columns]
    assert keys == ["no_edge/bootstrap/base", "no_edge/bootstrap/stress2x", "delist_30", "delist_100"]
    assert [c.key for c in etf.columns] == keys[:2]
    specs = [run[0][0] for run in runs if run[1]["key"].startswith("delist")]
    assert [(s.delist_h, s.mult, s.engine, s.theta) for s in specs] == [(0.30, 1.0, "bootstrap", 0.0),
                                                                         (1.00, 1.0, "bootstrap", 0.0)]
    for col in stock.columns[2:]:
        assert (col.member, col.scenario, col.trades) == ("bootstrap", "base", stock.columns[0].trades)
        assert abs(col.mean + col.mean_cost - 42_000.0) <= 4.0 * col.g_se, (col.key, col.mean, col.mean_cost)
    assert stock.columns[3].mean_cost > stock.columns[2].mean_cost > stock.columns[0].mean_cost
    text = report.render(stock)
    for h in ("30", "100"):
        assert report.say("column.delist", symbol="005930", h=h) in text
    assert report.say("cost.delist", base=report.say("cost.tax")) in text


def test_tilt_pilot_runs_at_the_real_chunk():
    """Q30, Q10, contract 3.4: the 20,000-path tilt pilot runs through _run_paths with the real CHUNK of 200,000 in
    force (20,000 is not a multiple of it, so run_column would raise); it never calls run_column, and it finds the
    theta an assumed run under chunk() found, since its paths come from the tilt stream, never from CHUNK."""
    leg = dataclasses.replace(UPBIT, bracket=BRACKET, edge_source="assumed", assumed_p=0.6)
    with OF.chunk(), OF.members("bootstrap"), OF.spy(simulate, "run_column") as runs:
        rep = OF.pipeline(OF.plan(leg=leg), series_obj=OF.fresh_series(vol=0.04, open_gap=0.04))
    assert rep.refused is None, rep.refused
    spec, seed = runs[0][0][0], runs[0][1]["seed"]
    assert (simulate.CHUNK, simulate.TILT_PILOT) == (200_000, 20_000)
    with OF.spy(simulate, "run_column") as later, OF.spy(simulate, "_run_paths") as pilot_runs:
        theta = simulate._tilt_theta(spec, 0.6, seed)
    assert later == [] and pilot_runs and {kw["n"] for _, kw, _ in pilot_runs} == {20_000}
    assert theta == rep.assumed["theta"]


def test_full_chunk_runs_at_the_real_size():
    """Contract 3.4, Q10: one real 200,000-path chunk of a 7-day crypto buy-and-hold headline at base costs, with the
    real CHUNK in force: every path enters and is counted once, its HIDDEN_EDGE range is the one fixed from the
    spec (the same as at 2,000 paths) and passes, and the average agrees with the stake less the average cost."""
    plan_obj = OF.plan(horizon_days=7, target_krw=63_000.0)
    with OF.chunk(), OF.members("bootstrap"), OF.spy(simulate, "run_column") as runs:
        small = OF.pipeline(plan_obj)
    (spec,), kw, _ = runs[0]
    assert simulate.CHUNK == 200_000 and len(spec.checks.on) == 14
    col = simulate._column(spec, n=simulate.CHUNK, seed=kw["seed"], key=kw["key"], member=kw["member"],
                           scenario=kw["scenario"])
    assert (col.n, col.trades, col.at_floor + col.running) == (200_000, 200_000, 200_000)
    assert col.x_range == small.columns[0].x_range
    assert report.hidden_edge(col, w0=42_000.0, target=63_000.0, l_min=21_000.0).status == "pass"
    assert abs(col.mean + col.mean_cost - 42_000.0) <= 4.0 * col.g_se
```

- [ ] **Step 2: Run to verify it fails**

  Overlap check (Git Bash form; it must print nothing, otherwise wait), then the two modules:

```bash
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && .venv/Scripts/python.exe -m tests.odds_acceptance odds_columns/
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && .venv/Scripts/python.exe -m tests.odds_acceptance odds_pipeline/
```

  Expected for `odds_columns/`: 14 FAIL lines and `0/14 passed, 14 failed, 0 not run` (exit code 1).
  `test_tilt_pilot_runs_at_the_real_chunk` fails with `AttributeError: module 'core.odds.simulate' has no attribute
  '_tilt_theta'` and `test_full_chunk_runs_at_the_real_size` with `... has no attribute '_column'`;
  `test_an_unreachable_typed_rate_is_refused` with `AttributeError: 'NoneType' object has no attribute 'code'`; the
  other eleven with AssertionError (`test_a_fit_that_does_not_converge_drops_its_members` on its first `notes`
  assertion, since Task 13 runs the headline only and leaves `notes` empty), for example

```
FAIL odds_columns/test_a_corrupted_garch_headline_is_model_check_failed AssertionError: Refusal(code='MODEL_CHECK_FAILED', sub='fit', slots={}, detail='garch not built yet')
FAIL odds_columns/test_hidden_edge_range_is_fixed_from_the_plan_and_the_history AssertionError: ('no_edge/bootstrap/base', 'base', nan, ...)
```

  Expected for `odds_pipeline/`: `4/13 passed, 9 failed, 0 not run` (exit code 1). The four that pass are
  `test_partial_chunk_is_refused_at_the_real_chunk`, `test_every_refusal_in_q24_order`,
  `test_one_krx_plan_breaking_three_data_rules_reports_o10_order` and
  `test_replay_legs_are_refused_until_the_replay_is_built`; `test_an_okx_horizon_across_auto_off_is_forced_out`
  fails with `IndexError: list index out of range` (two runs a plan, not four) and the other eight with
  AssertionError (the placeholder's MODEL_CHECK_FAILED, two columns where four are expected, the purity run's
  members `('bootstrap',)`). An ImportError, a NameError in the fixtures or a TypeError from a Task 8-12 call means
  an earlier task's name differs from the contract: stop and rule.

- [ ] **Step 3: Implement**

  Check first that none of the new names exists yet and that Task 13's part is in place (Git Bash):

```bash
grep -nE "^def (_members|_garch_member|_hidden_range|_column|_tilt_theta|_assumed|_spread|_reference)\(|^_BLOCK_MULT" core/odds/simulate.py
grep -cE "^def (_headline_spec|_no_edge_pair|_accepted_report|_refused_report|_report_provenance|_grey_slots|_cap_text)\(" core/odds/simulate.py
grep -n "Task 14 replaces this branch" core/odds/simulate.py
```

  The first prints nothing; the second prints `7`; the third prints the one placeholder line. Then read
  `core/odds/simulate.py` and make these three Edits (keep LF). The last one replaces Task 13's `_accepted_report`,
  the last function of the file, with the whole part 4 block (the helpers and the new `_accepted_report`; part 4
  adds no import: `math`, `np`, `dataclasses`, `date`, `bold`, `costs`, `models`, `plan` and `report` come from
  Tasks 9 and 13).

  **Edit 20** (`core/odds/simulate.py`, anchor: `simulate`, the GARCH-t placeholder branch Task 13 left before `n = ...`; LF). `old_string`:

```text
    if not screening.allowed:
        return _refused_report(plan_obj, ctx, _screen_refusal(screening, ctx))
    if leg.model == "garch_t":                             # Task 14 replaces this branch with the GARCH-t headline
        refusal = plan.Refusal(code="MODEL_CHECK_FAILED", sub="fit", detail="garch not built yet")
        return _refused_report(plan_obj, ctx, refusal)
    n = DEFAULT_PATHS[plan_obj.track] if n_paths is None else n_paths
```

  `new_string`:

```text
    if not screening.allowed:
        return _refused_report(plan_obj, ctx, _screen_refusal(screening, ctx))
    n = DEFAULT_PATHS[plan_obj.track] if n_paths is None else n_paths     # Q24 step 14 runs in _accepted_report
```

  **Edit 21** (`core/odds/simulate.py`, anchor: `_no_edge_pair` (docstring and return statement); LF). `old_string`:

```text
    """One member's no-edge column at base and at 2x costs, on the same streams (common random numbers, Q31)."""
    return tuple(run_column(dataclasses.replace(spec, mult=mult), n=n, seed=seed, key=f"no_edge/{member}/{name}",
                            member=member, scenario=name) for name, mult in costs.SCENARIOS.items())
```

  `new_string`:

```text
    """One member's no-edge column at base and at 2x costs, on the same streams (common random numbers, Q31), each
    with its HIDDEN_EDGE range fixed from the spec (_column, Task 14)."""
    return tuple(_column(dataclasses.replace(spec, mult=mult), n=n, seed=seed, key=f"no_edge/{member}/{name}",
                         member=member, scenario=name) for name, mult in costs.SCENARIOS.items())
```

  **Edit 22** (`core/odds/simulate.py`, anchor: `_accepted_report`, the whole function (the last definition of the file, Task 13's part 3); LF). `old_string`:

```python
def _accepted_report(plan_obj, ctx, inputs, *, inst, terms, market: str, sessions: tuple[date, ...], screening,
                     n: int) -> report.OddsReport:
    """Step 7 for the headline member: the market seed (Q34), l_min per sizing (Q32), the headline no-edge column at
    base and 2x costs, the flags (rule dates, grey rows, proxy data) and report.build with the provenance keys.
    plan_index and plan_count are 1 here; the CLI numbers the plans of its file."""
    leg, series = plan_obj.leg, inputs.series
    seed = models.market_seed(models.data_hashes(series, inputs.replay), inputs.calendar_sha256,
                              inputs.comparison_id, inputs.run_counter)
    spec = _headline_spec(plan_obj, ctx, inputs, terms=terms, market=market, sessions=sessions, screening=screening)
    member = leg.model
    columns = _no_edge_pair(spec, member, n=n, seed=seed)
    stake, target = float(plan_obj.stake_krw), float(plan_obj.target_krw)
    l_min = spec.floor if leg.sizing == "floor_safe" else 0.0
    ceiling = bold.ceiling(stake, l_min, target)
    model_slots = {"symbol": leg.symbol, "first": series.dates[0], "last": series.dates[-1],
                   "rows": f"{len(series.dates):,}"}
    if spec.cap_krw is not None:
        model_slots.update(cap=_cap_text(ctx.owner.caps[plan.OKX_CAP_KEY]), capkrw=report.fmt_krw(spec.cap_krw))
    flags = report.flags_for(headline=columns[0], no_edge=columns, engine=spec.engine, hidden=None, ceiling=ceiling,
                             structural=None, target=target, stake=stake, reference=None,
                             rule_flags=screening.flags, grey=_grey_slots(plan_obj, ctx), series=series,
                             okx=leg.venue == "okx")
    return report.build(
        plan_hash=plan.plan_hash(plan_obj), plan_index=1, plan_count=1, refused=None, track=plan_obj.track,
        stake=stake, target=target, floor=spec.floor, l_min=l_min, horizon_days=plan_obj.horizon_days, n=n,
        sizing=leg.sizing, model_key="model.bootstrap", model_slots=model_slots, columns=columns,
        headline=columns[0].key, spread=None, spread_kind="none", notes=(), ceiling=ceiling, structural_cap=None,
        structural_sessions=None, tax_basis=inst.tax_basis,
        cost_words_key="cost.tax" if terms.book == "KRX_stock_book" else "cost.fees", hidden=None, flags=flags,
        assumed=None, replay=None, comparison=(inputs.comparison_plans, inputs.comparison_typed, inputs.plan_runs),
        provenance=_report_provenance(plan_obj, ctx, inputs, screening=screening, seed=seed, n=n, members=(member,)))
```

  `new_string`:

```python
# --------------------------------------------------------------------------- #
# Part 4 (Task 14): every other column of contract 8.5. The block-length members, the GARCH-t fit and the refit
# member with every pilot check (Q31, R2-8), the delisting pair (Q29), the assumed column and its tilt pilot (Q30),
# the spread (Q31), the structural cap (Q44), HIDDEN_EDGE's range fixed before the run (contract 10.3), the bracket
# reference (Q33) and every flag. Task 17 adds the replay card.
# --------------------------------------------------------------------------- #
_BLOCK_MULT = {"bootstrap": None, "bootstrap_half": 0.5, "bootstrap_double": 2.0}   # None: the block b itself


def _members(headline: str, market: str) -> tuple[str, ...]:
    """The members to run, the headline first (Q31): every MEMBERS entry, read at call time so a test can narrow
    the spread with OF.members(); KRX legs run the block-length members only (no GARCH-t: it has no daily band)."""
    others = tuple(m for m in MEMBERS if m != headline and (market != "KR" or m in _BLOCK_MULT))
    return (headline,) + others


def _garch_member(member: str, fit, horizon: int, seed: bytes) -> tuple[tuple, str]:
    """(fits, "") for a GARCH member that passed every check, else ((), the failed check). garch_t: the fit of the
    history ("fit" when it did not converge; at_bound alone is recorded, not a failure) and both pilot checks on it
    ("deterministic" or "statistical"). garch_refit: REFIT_B synthetic series drawn from that fit (stream
    "refit_series" b), each refitted, and every refit must converge and pass both pilot checks (R2-8); the first
    that does not drops the whole member with check "refit"."""
    if not fit.converged:
        return (), "fit"
    if member == "garch_t":
        ok, check = models.pilot_checks(fit, horizon, seed)
        return ((fit,), "") if ok else ((), check)
    refits = []
    for b in range(REFIT_B):
        synthetic = models.simulate_garch_series(fit.omega, fit.alpha, fit.beta, fit.nu, n=fit.n_obs,
                                                 seed=models.seed_sequence(seed, 0, "refit_series", b))
        refit = models.fit_garch_t(synthetic)
        if not (refit.converged and models.pilot_checks(refit, horizon, seed)[0]):
            return (), "refit"
        refits.append(refit)
    return tuple(refits), ""


def _hidden_range(spec: PathSpec) -> float:
    """HIDDEN_EDGE's range R of a bootstrap no-edge column (contract 10.3), fixed before the run from the plan and
    the history only: m_max the largest open or close move of the history; the lowest price the model can reach,
    p0 x prod(1 - limit) over the horizon's sessions on a KRX leg (every check of a session stays at or above its D)
    and p0 x e^(-n_checks x m_max) otherwise; the cost bound costs.kappa_bound there on both sides; and the
    scenario's charges (mult). report.hidden_range returns inf when the bound makes k_x >= 1 (R2-7)."""
    m_max = float(max(np.max(spec.m_o), np.max(spec.m_i)))
    n_checks = len(spec.checks.on)
    bands = spec.limits[np.isfinite(spec.limits)]
    p_min = (spec.p0 * float(np.prod(1.0 - bands)) if bands.size
             else spec.p0 * math.exp(-n_checks * m_max))
    kappa_bound = costs.kappa_bound(spec.terms, p_min, tuple(sorted(set(spec.checks.on))), spec.mult)
    return report.hidden_range(target=spec.target, phi_buy=spec.mult * spec.terms.phi_buy,
                               phi_sell=spec.mult * spec.terms.phi_sell, kappa_bound=kappa_bound, m_max=m_max,
                               n_checks=n_checks)


def _column(spec: PathSpec, *, n: int, seed: bytes, key: str, member: str, scenario: str) -> report.ColumnStats:
    """run_column with HIDDEN_EDGE's range set: _hidden_range for a bootstrap column, nan for GARCH-t (no finite
    range exists: a bounded shock does not bound the volatility, spec 7.5). Both come from the spec alone, never
    from the paths."""
    x_range = _hidden_range(spec) if spec.engine == "bootstrap" else math.nan
    col = run_column(spec, n=n, seed=seed, key=key, member=member, scenario=scenario)
    return dataclasses.replace(col, x_range=x_range)


def _tilt_theta(spec: PathSpec, p: float, seed: bytes) -> float | None:
    """Q30: theta of the assumed column, by bisection over [-TILT_BOUND, TILT_BOUND] on a TILT_PILOT-path pilot
    through _run_paths (TILT_PILOT need not be a multiple of CHUNK), every theta on the same paths (the pilot's
    seed is drawn from stream "tilt"); at most TILT_ITER steps, stopping when the pilot's win rate is within
    TILT_TOL of p. None (ASSUMED_EDGE_UNREACHABLE) when p lies outside [win(-8), win(8)] or the last win rate
    misses p by more than TILT_FAIL. A win is a take-profit fill among the brackets resolved by take-profit or
    stop (a locked exit is unresolved)."""
    pilot = models.stream(seed, 0, "tilt").bytes(32)

    def win(theta: float) -> float:
        out = _run_paths(dataclasses.replace(spec, theta=theta, record_brackets=False), n=TILT_PILOT, chunk=0,
                         seed=pilot)
        wins, losses = int(np.sum(out["wins"])), int(np.sum(out["losses"]))
        return wins / (wins + losses) if wins + losses else math.nan

    lo, hi = -TILT_BOUND, TILT_BOUND
    if not win(lo) <= p <= win(hi):                        # nan (no resolved bracket) fails too
        return None
    theta, w = 0.0, math.nan
    for _ in range(TILT_ITER):
        theta = 0.5 * (lo + hi)
        w = win(theta)
        if abs(w - p) <= TILT_TOL:
            break
        if w < p:
            lo = theta
        else:
            hi = theta
    return theta if abs(w - p) <= TILT_FAIL else None


def _assumed(col: report.ColumnStats, p: float, theta: float) -> dict | None:
    """The assumed card's figures (Q30): the typed rate w; p0 and the unresolved share u of the headline's full
    no-edge base column; its resolved brackets; the brackets needed to tell w from p0 (bold.brackets_needed, inf
    when equal); theta. None when that column resolved no bracket (no p0 to compare with)."""
    resolved = col.wins + col.losses
    if resolved == 0:
        return None
    p0 = col.wins / resolved
    return {"w": p, "p0": p0, "u": col.unresolved / (resolved + col.unresolved),
            "nb": bold.brackets_needed(p, p0), "resolved": float(resolved), "theta": theta}


def _spread(columns, headline: report.ColumnStats, track: str, market: str):
    """Q31, Q32: (spread, kind). The spread runs from the lowest two-sided lower bound to the highest upper bound
    of the base no-edge cells of every member but the headline (REACHED outcomes on moonshot cards, first passages
    on compounding cards); kind "none" when no other member ran, "krx" on KRX legs, "other" when another model
    family ran, else "blocks" (the block-length members only)."""
    cells = [c for c in columns if c.key.startswith("no_edge/") and c.scenario == "base" and c.key != headline.key]
    if not cells:
        return None, "none"
    bounds = [report.cp_two_sided(c.reached_outcome if track == "moonshot" else c.reached, c.n) for c in cells]
    spread = (min(lo for lo, _ in bounds), max(hi for _, hi in bounds))
    family = headline.member.split("_")[0]                 # "bootstrap" | "garch"
    if market == "KR":
        return spread, "krx"
    if any(c.member.split("_")[0] != family for c in cells):
        return spread, "other"
    return spread, "blocks"


def _reference(col: report.ColumnStats, spec: PathSpec, *, l_min: float, on: date) -> float | None:
    """Q33: bold.bracket_reference on the bracket sample of the headline no-edge base column, at the buy side's base
    rate at p0; None for a buy-and-hold leg or when no bracket was recorded. An estimate: it only ever raises the
    amber ABOVE_ESTIMATED_REFERENCE."""
    if col.brackets is None or len(col.brackets[0]) == 0:
        return None
    r, d = col.brackets
    terms = spec.terms
    kappa = float(costs.kappa(terms, np.array([spec.p0]), on, 1.0, side="buy")[0])
    return bold.bracket_reference(r, d, w0=spec.w0, l_min=l_min, target=spec.target, n_checks=len(spec.checks.on),
                                  kappa=kappa, phi_buy=terms.phi_buy, phi_sell=terms.phi_sell,
                                  r_exit=costs.r_exit(terms))


def _accepted_report(plan_obj, ctx, inputs, *, inst, terms, market: str, sessions: tuple[date, ...], screening,
                     n: int) -> report.OddsReport:
    """Step 7 (contract 8.5): the market seed (Q34) and l_min per sizing (Q32); the GARCH fits and their pilot
    checks, the headline first (a failed headline is MODEL_CHECK_FAILED, a failed spread member is left out with
    its note); the tilt pilot of an assumed leg (ASSUMED_EDGE_UNREACHABLE); then the columns: each member's no-edge
    pair on one seed, the delisting pair of a share or coin leg and the assumed column, all on the headline member;
    then the spread, the structural cap of a buy-and-hold KRX leg, HIDDEN_EDGE on the headline, the bracket
    reference, the flags and report.build. plan_index and plan_count are 1 here; the CLI numbers the plans."""
    leg, series = plan_obj.leg, inputs.series
    seed = models.market_seed(models.data_hashes(series, inputs.replay), inputs.calendar_sha256,
                              inputs.comparison_id, inputs.run_counter)
    base = _headline_spec(plan_obj, ctx, inputs, terms=terms, market=market, sessions=sessions, screening=screening)
    stake, target = float(plan_obj.stake_krw), float(plan_obj.target_krw)
    l_min = base.floor if leg.sizing == "floor_safe" else 0.0
    ceiling = bold.ceiling(stake, l_min, target)
    headline = leg.model
    specs: dict[str, PathSpec] = {}
    notes: list[tuple[str, str]] = []
    fit = None
    for member in _members(headline, market):
        if member in _BLOCK_MULT:
            mult = _BLOCK_MULT[member]
            block = base.block if mult is None else models.variant_block(base.block, mult, len(base.m_o))
            specs[member] = dataclasses.replace(base, block=block)
            continue
        if fit is None:
            fit = models.fit_garch_t(models.rows(series)[2])
        fits, check = _garch_member(member, fit, len(sessions), seed)
        if check and member == headline:
            refusal = plan.Refusal(code="MODEL_CHECK_FAILED", sub=check, detail=f"{member}: {check} check failed")
            return _refused_report(plan_obj, ctx, refusal)
        if check:
            notes.append((member, check))
            continue
        specs[member] = dataclasses.replace(base, engine="garch", fits=fits, checks=checks(market, sessions, True))
    # only the headline keeps a bracket sample (Q33 reads its base column's); no other member pays for one
    head = specs[headline] = dataclasses.replace(specs[headline], record_brackets=leg.bracket is not None)
    theta = None
    if leg.edge_source == "assumed":
        theta = _tilt_theta(head, leg.assumed_p, seed)
        if theta is None:
            refusal = plan.Refusal(code="ASSUMED_EDGE_UNREACHABLE", slots={"w": _cap_text(leg.assumed_p)},
                                   detail=f"tilt pilot cannot reach {leg.assumed_p!r}")
            return _refused_report(plan_obj, ctx, refusal)
    columns: list[report.ColumnStats] = []
    for member, spec in specs.items():
        columns += _no_edge_pair(spec, member, n=n, seed=seed)
    head_col = columns[0]
    once = dataclasses.replace(head, record_brackets=False)
    if inst.cls in ("share", "coin"):
        for h in costs.DELIST_STRESS:
            columns.append(run_column(dataclasses.replace(once, delist_h=h), n=n, seed=seed,
                                      key=f"delist_{round(100 * h)}", member=headline, scenario="base"))
    assumed = None
    if theta is not None:
        assumed = _assumed(head_col, leg.assumed_p, theta)
        if assumed is None:
            refusal = plan.Refusal(code="ASSUMED_EDGE_UNREACHABLE", slots={"w": _cap_text(leg.assumed_p)},
                                   detail="the no-edge column resolved no bracket")
            return _refused_report(plan_obj, ctx, refusal)
        columns.append(run_column(dataclasses.replace(once, theta=theta), n=n, seed=seed, key="assumed",
                                  member=headline, scenario="base"))
    spread, spread_kind = _spread(columns, head_col, plan_obj.track, market)
    structural = None
    if market == "KR" and leg.bracket is None:
        structural = (bold.structural_max(tuple(inputs.price_limits)), len(sessions))
    hidden = report.hidden_edge(head_col, w0=stake, target=target, l_min=l_min)
    reference = _reference(head_col, head, l_min=l_min, on=sessions[0])
    model_slots = {"symbol": leg.symbol, "first": series.dates[0], "last": series.dates[-1],
                   "rows": f"{len(series.dates):,}"}
    if head.cap_krw is not None:
        model_slots.update(cap=_cap_text(ctx.owner.caps[plan.OKX_CAP_KEY]), capkrw=report.fmt_krw(head.cap_krw))
    no_edge = tuple(c for c in columns if c.key.startswith("no_edge/"))
    flags = report.flags_for(headline=head_col, no_edge=no_edge, engine=head.engine, hidden=hidden, ceiling=ceiling,
                             structural=structural, target=target, stake=stake, reference=reference,
                             rule_flags=screening.flags, grey=_grey_slots(plan_obj, ctx), series=series,
                             okx=leg.venue == "okx")
    return report.build(
        plan_hash=plan.plan_hash(plan_obj), plan_index=1, plan_count=1, refused=None, track=plan_obj.track,
        stake=stake, target=target, floor=base.floor, l_min=l_min, horizon_days=plan_obj.horizon_days, n=n,
        sizing=leg.sizing, model_key="model.garch" if head.engine == "garch" else "model.bootstrap",
        model_slots=model_slots, columns=tuple(columns), headline=head_col.key, spread=spread,
        spread_kind=spread_kind, notes=tuple(notes), ceiling=ceiling,
        structural_cap=None if structural is None else structural[0],
        structural_sessions=None if structural is None else structural[1], tax_basis=inst.tax_basis,
        cost_words_key="cost.tax" if terms.book == "KRX_stock_book" else "cost.fees", hidden=hidden, flags=flags,
        assumed=assumed, replay=None, comparison=(inputs.comparison_plans, inputs.comparison_typed, inputs.plan_runs),
        provenance=_report_provenance(plan_obj, ctx, inputs, screening=screening, seed=seed, n=n,
                                      members=tuple(specs)))
```

- [ ] **Step 4: Run to verify it passes**

  Overlap check before each command, then (Bash tool `timeout: 300000` each; on a loaded machine `odds_columns/` has
  taken 93 s, as below):

```bash
.venv/Scripts/python.exe -m tests.odds_acceptance odds_columns/
.venv/Scripts/python.exe -m tests.odds_acceptance odds_pipeline/
```

  Expected: `14/14 passed, 0 failed, 0 not run` for `odds_columns/` and `13/13 passed, 0 failed, 0 not run` for
  `odds_pipeline/` (exit code 0 each). Times measured on a mock tree whose tests and part 4 are this task's text:
  odds_columns 15.9 s and 18.1 s on a quiet machine (`test_every_member_runs_on_a_crypto_leg` about 8 s for its 21
  GARCH-t fits, up to 21 correction tables, 21 pilot checks and 12 columns; every other test under 2 s), within
  CONTRACT 3.4's 30 s; odds_pipeline 2.8 s, within its 20 s. On a heavily loaded machine the same module took 64 s
  and 93 s (`test_every_member_runs_on_a_crypto_leg` 32 to 40 s, the Bonferroni test up to 17 s), so a time over
  30 s is a regression only on a quiet machine. Two tests run the real 20,000-path tilt pilot:
  `test_an_assumed_win_rate_tilts_the_assumed_column` (no `OF.pilots()`, as its docstring says) and
  `test_tilt_pilot_runs_at_the_real_chunk` (twice: in its pipeline run and directly); contract 3.4 allows a pilot
  test that needs 20,000 paths. Record each module's time under "Runs" in the execution ledger and name every test
  over 15 s; never lower `REFIT_B`, `PILOT_SE`, `PILOT_STEP_TOL`, `PILOT_SUM_TOL` or a pilot constant, shorten a
  test or skip a member to meet a budget. Then run each line below as its own command, each with the overlap check
  first and each ending with no FAIL line. Give every `-m` line the Bash tool `timeout: 300000`, the `--suite odds`
  line `timeout: 600000` and the `--suite cockpit` line `timeout: 300000` (Global Constraints, "Python and test
  runs"): `compliance_store/` alone can run past the 120 s default, the odds modules through this task have targets
  that add up to 144 s (CONTRACT 3.4), and a killed command skips whatever is chained after it. Each `--suite` line
  carries the KEYLESS prefix and restores the tracked `qa/acceptance_results.json` after `;`, whatever the run did:

```bash
.venv/Scripts/python.exe -m tests.odds_acceptance odds_guards/
.venv/Scripts/python.exe -m tests.odds_acceptance odds_simulate/
.venv/Scripts/python.exe -m tests.odds_acceptance odds_locks/
.venv/Scripts/python.exe -m tests.compliance_acceptance compliance_guards/
.venv/Scripts/python.exe -m tests.compliance_acceptance compliance_store/
KIS_APP_KEY='<unset>' KIS_APP_SECRET='<unset>' KIS_ACCOUNT_8='<unset>' KIS_ACCOUNT_PD='<unset>' UPBIT_ACCESS_KEY='<unset>' UPBIT_SECRET_KEY='<unset>' OKX_API_KEY='<unset>' OKX_API_SECRET='<unset>' OKX_API_PASSPHRASE='<unset>' OPENDART_API_KEY='<unset>' KRX_API_KEY='<unset>' FMP_API_KEY='<unset>' ANTHROPIC_API_KEY='<unset>' GS_CLIENT_ID='<unset>' GS_CLIENT_SECRET='<unset>' FINVIZ_API_KEY='<unset>' ALPACA_API_KEY='<unset>' ALPACA_SECRET_KEY='<unset>' FXMACRODATA_API_KEY='<unset>' .venv/Scripts/python.exe tests/run_all.py --suite odds; echo "exit $?"; git checkout -- qa/acceptance_results.json
.venv/Scripts/python.exe -m tests.macro_m0_harness
.venv/Scripts/python.exe -m tests.macro_tf_gov
.venv/Scripts/python.exe -m tests.macro_m7_ledger
.venv/Scripts/python.exe -m tests.macro_m8_forward
.venv/Scripts/python.exe -m tests.macro_m6_context
KIS_APP_KEY='<unset>' KIS_APP_SECRET='<unset>' KIS_ACCOUNT_8='<unset>' KIS_ACCOUNT_PD='<unset>' UPBIT_ACCESS_KEY='<unset>' UPBIT_SECRET_KEY='<unset>' OKX_API_KEY='<unset>' OKX_API_SECRET='<unset>' OKX_API_PASSPHRASE='<unset>' OPENDART_API_KEY='<unset>' KRX_API_KEY='<unset>' FMP_API_KEY='<unset>' ANTHROPIC_API_KEY='<unset>' GS_CLIENT_ID='<unset>' GS_CLIENT_SECRET='<unset>' FINVIZ_API_KEY='<unset>' ALPACA_API_KEY='<unset>' ALPACA_SECRET_KEY='<unset>' FXMACRODATA_API_KEY='<unset>' .venv/Scripts/python.exe tests/run_all.py --suite cockpit; echo "exit $?"; git checkout -- qa/acceptance_results.json
```

  `odds_guards/` passes with part 4 (it adds no import; no clock, no file I/O, no `__main__`, and
  `.bytes(32)` on a numpy Generator is not a file call); `--suite odds` exits 0 with the `odds/odds_columns/...` rows,
  ending `214/214 passed, 0 failed, 0 not run; ` and the path, then `exit 0` (guards 18, plan 25, costs 23, models 19, garch 17,
  simulate 18, locks 14, bold 12, report 41, pipeline 13, columns 14; Tasks 15 to 18 add the other 73);
  `compliance_store/` keeps `test_code_files_is_the_import_closure` green (the closure gains no file). Then
  `git status --short` shows exactly ` M core/odds/simulate.py`, ` M tests/odds_fixtures.py`,
  ` M tests/odds_pipeline.py`, `?? tests/odds_columns.py` and the untracked execution ledger. Append the tails of the
  two module runs and the suite run (its `214/214` total) to the ledger under "Runs". Under "Deferred minors" mark
  Task 9's "x_range = nan" minor as resolved by Task 14's `_column`, and add the line `contract 3.2: Task 14 adds
  members(*names) and garch_series(...) to tests/odds_fixtures.py`. Under "Drift rulings" record the line "contract
  10.3: the bootstrap range is set by simulate._column (part 4), not run_column; direct run_column calls (delisting,
  assumed, replay) keep their own value".

- [ ] **Step 5: Commit**

```bash
git add core/odds/simulate.py tests/odds_fixtures.py tests/odds_pipeline.py tests/odds_columns.py
git grep -n -i -E "order_cash|order-cash|place_order|submit_order|tttc0802u|tttc0801u|vttc0802u|private_key|seed_phrase|/v1/orders|/v1/withdraws|/v1/deposits|/api/v3/order|/sapi/v1/capital|/uapi/|r18_research_log|r18_break_log|context_log/|tests\.reference|reference_mode|reference_only" -- core/odds/simulate.py
git grep -n -E "CANO|KIS_ACCOUNT|ACNT_PRDT_CD|0\.4 *[*x]|kish|__import__|import_module|\bexec\b|\beval\b|\bopen\(" -- core/odds/simulate.py
git diff --cached --stat
git diff --cached --stat --ignore-cr-at-eol
git commit -m "feat(odds): every column, the spread, the GARCH pilots and the flags" -m "simulate part 4: block-length and GARCH-t members with every fit and refit pilot-checked, MODEL_CHECK_FAILED and ASSUMED_EDGE_UNREACHABLE, delisting and assumed columns, the spread, IMPOSSIBLE, HIDDEN_EDGE's fixed range and CEILING_BREACH over every no-edge cell." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

  Both `git grep` commands print nothing (exit code 1). The two `--stat` outputs must be identical (4 files changed,
  LF only).
