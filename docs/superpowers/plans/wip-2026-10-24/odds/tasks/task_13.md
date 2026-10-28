### Task 13: simulate(), part 1: the pipeline, the refusals and one headline column (`core/odds/simulate.py`)

**Files:**
- Modify: `core/odds/simulate.py` (anchors: the module docstring, its last line `Pure: no clock, no file, no
  network.` (Task 9's, kept by Task 10); the end of the file, after the last definition Task 10 left (append); LF)
- Modify: `tests/odds_fixtures.py` (anchor: the end of the file, after Task 9's `even_rows`; append only; LF)
- Create: `tests/odds_pipeline.py` (LF, UTF-8, no BOM)
- Test: `tests/odds_pipeline.py`

Neither modified file is touched by the compliance follow-up (both are created by this plan), so the follow-up
cannot have moved their text. If an earlier task of this plan was amended at execution and the docstring line
differs, apply the DRIFT RULE of the Global Constraints (one ledger line under "Drift rulings").
`tests/odds_pipeline.py` is already in `tests/odds_acceptance.MODULES` (Task 1).

**Interfaces:**
- Consumes:
  - Task 1: `tests/odds_fixtures.chunk()` (swaps `simulate.CHUNK`, `DEFAULT_PATHS` and `GARCH_SUB`, restoring the
    saved objects); the runner `-m tests.odds_acceptance` (each test inside `hermetic()` and a temp
    `TRADEGEN_HOME`).
  - Task 4: `core.compliance.owner.calendar_in_force(now) -> str | None` (ValueError on a naive `now`; None with no
    owner key, as in a temp home); `core.compliance.gate.grey_rows(plan, ctx) -> tuple[str, ...]`. As built:
    `gate.screen(plan, ctx, first_stake_krw: float) -> model.Screening` (`.allowed`, `.flags` =
    `((date, "review_by" | "auto_off" | "effective_until", row_id), ...)` sorted, `.decision.verdict`,
    `.decision.reasons`, `.decision.decision_id`, `.screening_hash`); `model.is_sealed`, `model.KST`,
    `model.ACK_REQUIRED`; `rules.Row.id`, `.cap_key`, `.auto_off` (a grey row always has both); `ctx.active.rules.rows`,
    `ctx.active.hashes`, `ctx.active.state_hash`, `ctx.owner.head`, `.limits`, `.caps`, `.fingerprint`,
    `ctx.code_hash`, `ctx.code_signed`; fixtures `F.ctx(**overrides)`, `F.approved(rules=None, instruments=None,
    venues=None)`.
  - Task 5 (`core.odds.plan`): `Refusal`, `Inputs`, `Leg`, `Bracket`, `bold()`, `REPLAY_SOURCE`, `MARKET`,
    `OKX_CAP_KEY`, `instrument(plan, ctx)`, `check_plan(plan, ctx)`, `check_state(plan, ctx)`, `check_now(ctx, now)`,
    `check_data(plan, ctx, inputs, market)`, `check_history(plan, inputs, market)`, `plan_hash(plan)`,
    `series_md5(...)`; fixtures `OF.plan(**changes)`, `OF.odds_ctx(**overrides)`, `OF.series(*, symbol, source, n,
    seed, start, vol, open_gap, price, step_days)`, `OF.venues_with(**changes)` (called as
    `venues_with(upbit={"fee_extras": None})`: a mapping per venue, None removes that odds key).
  - Task 6 (`core.odds.costs`): `terms(venue, inst, fx_krw_per_usd, *, replay=False) -> Terms` (`.book`),
    `check_validity(terms, dates)`, `NotTradable`, `cost_refusal(plan, terms, p0, on) -> str | None`,
    `first_stake(plan, terms, ctx, p0, on, *, fstar=None) -> float`, `SCENARIOS` (`{"base": 1.0, "stress2x": 2.0}`,
    in that order).
  - Task 7 (`core.odds.models`): `rows(series) -> (m_o, m_i, r)`, `block_length(r)`, `data_hashes(series, replay)`,
    `market_seed(data_hashes, calendar_digest, comparison_id, run_counter) -> bytes`.
  - Tasks 9-10 (`core.odds.simulate`): `CHUNK`, `DEFAULT_PATHS`, `checks(market, sessions, close_only) -> Checks`
    (`.on`, `.seoul`; open then close of each session for the bootstrap, Q22), `PathSpec` (every field of contract
    8.2), `run_column(spec, *, n, seed, key, member, scenario) -> report.ColumnStats`, with the engine honouring
    `limits`, `daily_loss`, `cap_krw`, `stop_entries_from` and `force_exit_from` (Task 10); `report.ColumnStats`;
    fixture `OF.inputs(plan, series, **changes)` (defaults: comparison `c000001`, run counter 1, K 1, J 0, R 1,
    provenance `("git:" + "0" * 40, "f" * 64, "49.0.0")`).
  - Task 11: `bold.ceiling(w0, l_min, target) -> float`.
  - Task 12 (`core.odds.report`): `build(**fields) -> OddsReport`, `refusal_report(plan_obj, refusal, *, index=1,
    count=1, provenance=...)`, `flags_for(*, headline, no_edge, engine, hidden, ceiling, structural, target, stake,
    reference, rule_flags, grey, series, okx)` (contract 10.1), `render(rep)`, `say(key, **slots)`, `CATALOGUE`,
    `fmt_krw(x)`, `Flag` (`.code`, `.level`, `.key`, `.slots`), every `OddsReport` field.
- Produces (`core/odds/simulate.py`, part 3):
  - `precheck(plan_obj, ctx, n_paths: int | None = None) -> plan.Refusal | None` and
    `simulate(plan_obj, ctx, inputs: plan.Inputs, *, n_paths: int | None = None) -> report.OddsReport`: contract
    8.5's `precheck(plan, ctx, n_paths)` and `simulate(plan, ctx, inputs, *, n_paths)`. The first parameter is
    named `plan_obj` because the module imports `plan`; every caller passes it positionally (Task 18 does).
  - Refusals as built here: PARTIAL_CHUNK with slot `chunk` (`f"{CHUNK:,}"`); NOT_TRADABLE with slots `venue`
    (`KIS`, `Upbit`, `OKX`) and `symbol`; COST_DOMINATED with detail `"4kappa"` or `"bold"`; STUCK_AT_START;
    SCREEN_BLOCKED with sub `row` (slot `row`), `unsigned` or `other`; CALENDAR_UNSIGNED and CALENDAR_COVERAGE;
    the rest come from `plan.check_*` unchanged.
  - Two placeholder branches, each replaced later together with its test:
    - Task 17 replaces
      `    if refusal is None and replay:                         # Task 17 replaces this branch with models.verify_replay`
      and the line after it, and the test `test_replay_legs_are_refused_until_the_replay_is_built`;
    - Task 14 replaces
      `    if leg.model == "garch_t":                             # Task 14 replaces this branch with the GARCH-t headline`
      and the two lines after it, and the test `test_garch_headlines_are_refused_until_their_pilot_is_built`.
  - `context_provenance(ctx) -> dict`, public because Task 18 passes `provenance=simulate.context_provenance(ctx)`
    to the cards the CLI refuses itself (its precheck and unknown-comparison refusals; the loader's card has no
    context): the nine context keys of contract 10.1 (`rules_sha`, `instruments_sha`, `venues_sha`, `state_hash`,
    `owner_seq`, `owner_row`, `code_hash`, `code_signed`, `fingerprint`) for a sealed context, else `{}`.
    `_report_provenance` and `_refused_report` call it.
  - Private helpers Tasks 14 and 17 reuse instead of rewriting:
    `_headline_spec(plan_obj, ctx, inputs, *, terms, market, sessions, screening) -> PathSpec` (the headline member
    at base costs; every other column is `dataclasses.replace` of it);
    `_no_edge_pair(spec, member, *, n, seed) -> tuple[ColumnStats, ColumnStats]` (keys `no_edge/<member>/base` and
    `no_edge/<member>/stress2x`, on one seed);
    `_accepted_report(plan_obj, ctx, inputs, *, inst, terms, market, sessions, screening, n) -> OddsReport`;
    `_refused_report(plan_obj, ctx, refusal) -> OddsReport`;
    `_report_provenance(plan_obj, ctx, inputs, *, screening, seed, n, members) -> dict` (all 31 keys of contract
    10.1); `_grey_slots(plan_obj, ctx) -> tuple[tuple[str, str, str], ...]`; `_cap_text(x) -> str` (`0.1` ->
    `"10%"`); `_calendar_refusal(market, inputs)`; `_screen_refusal(screening, ctx)`; `_VENUE_NAMES`.
  - The accepted report as built here: columns `no_edge/bootstrap/base` (the headline) and
    `no_edge/bootstrap/stress2x`; `spread=None`, `spread_kind="none"`, `notes=()`, `hidden=None`,
    `structural_cap=None`, `assumed=None`, `replay=None` (Task 14 and Task 17 fill them); `model_key
    "model.bootstrap"`; `model_slots` `{symbol, first, last, rows}` plus `cap` and `capkrw` on an OKX leg;
    `floor` = L; `l_min` = L under floor-protected sizing, else 0.0; `comparison` = (K, J, R); `plan_index` =
    `plan_count` = 1 (the CLI numbers the plans of its file).
- Produces (`tests/odds_fixtures.py`, Task 13 block): `CAL_SHA` (`"ab" * 32`), `calendar_signed(sha)`,
  `spy(target, name)` (yields a list of `(args, kwargs, result)`), `owner_with(**changes)`,
  `fresh_series(n=600, *, end="2026-10-22", **changes)`, `weekdays(start, horizon_days)`,
  `pipeline_inputs(plan_obj, series_obj, **changes)`, `pipeline(plan_obj=None, ctx=None, series_obj=None, *,
  n_paths=None, **changes)`, and the alias `_contextmanager` (Task 14's `members` is decorated with it). No `test_*`
  name. Contract 3.2 lists all eight public names under Task 13, and Step 4 records them in the execution ledger, as
  Task 14 does its own. Tasks 14 and 17 call `fresh_series`, `pipeline_inputs` and `pipeline`; Task 14 also
  `CAL_SHA`, `calendar_signed` and `spy`.

**Plan decisions used:** Q5 (rule dates from `Screening.flags`), Q6 (the calendar step), Q11 (W0 = the stake, the
OKX cap per entry, a float stake to `screen`, never zero), Q12 and Q34 (one seed per comparison; plan fields never
enter it), Q22 (sessions and check points), Q24 (the refusal order), Q25 (replay terms), Q31 (base and 2x costs on
common random numbers), Q32 (`l_min` per sizing), Q37 (cost words), Q39 (the injected-data checks), Q42 (purity),
Q45 (the precheck); RULINGS O5, O6, O10, O11; RULINGS_ROUND2 R2-1 (a 2027 KRX stock sell is NOT_TRADABLE end to
end), R2-5 (replay terms in the pipeline).

Design notes (read before Step 3):
- Q24's order is a straight line of early returns: `precheck` (steps 1-4), then `check_now` (step 5) before the
  calendar step (6), because the real `calendar_in_force` raises on a naive `now`; then `check_data` (7),
  `costs.terms` and `costs.check_validity` over every horizon session date (8), `check_history` (9), the replay
  placeholder (10), MODEL_NOT_FOR_LIMITED_VENUE (11), `cost_refusal` and `first_stake` (12), `screen` (13), and the
  GARCH-t placeholder (14, where Task 14's pilot finds MODEL_CHECK_FAILED). Every refusal is `report.refusal_report`
  with the context's provenance: no column, no flag, no probability.
- The calendar step: a `coverage: ...` error from the unsigned side is CALENDAR_COVERAGE; any other error, a missing
  signed calendar or a sha other than `inputs.calendar_sha256` is CALENDAR_UNSIGNED. `calendar_in_force` is not
  called for a crypto leg, so a crypto run does no I/O at all (Q42).
- `check_plan` lets a list or tuple of exactly one Leg through, but `screen` reads `plan.leg.venue` and would block
  a tuple as `malformed: venue`; so `simulate` replaces such a leg by the Leg itself right after the precheck.
- The GARCH-t headline is a placeholder here. TASKS gives the GARCH fits and their pilot checks to Task 14, and a
  headline may never print numbers from an unchecked model (Q31), so a `garch_t` leg on a crypto or US venue passes
  every earlier step, the gate included, and is refused MODEL_CHECK_FAILED (sub `fit`, detail
  `"garch not built yet"`) until Task 14 replaces that branch and its test. A `garch_t` KRX leg is
  MODEL_NOT_FOR_LIMITED_VENUE for good.
- `report.flags_for` is called with `hidden=None`, `structural=None` and `reference=None`, and `no_edge` holds the two
  headline cells: the rule-date, grey-row, proxy, check-point, band, gap, lock and cost flags all come out already;
  Task 14 passes HIDDEN_EDGE, IMPOSSIBLE, the bracket reference and every no-edge cell.
- SCREEN_BLOCKED's sub is read from the gate's first reason: `unsigned code` -> `unsigned`; a reason that ends with a
  row id of the table (`stale: review by 2026-11-22 passed (KR-DOMESTIC-SPOT)`, `cap exceeded: KR-OKX-SPOT`,
  `auto_off 2026-12-03: KR-OKX-SPOT`, ...) -> `row` with that id; anything else (`floor: ...`, `malformed: ...`) ->
  `other`.
- The part is appended with its own import block marked `# noqa: E402`, the repo's pattern for a file several tasks
  extend (`tests/compliance_fixtures.py`), so it does not depend on the exact import line Task 9 wrote; importing a
  module a second time is a no-op.
- Task 9's `run_column` stores `x_range = nan` in every column until Task 14 wires the range, and dataclass `==`
  compares field by field on Python 3.13, so nan never equals nan: `_strip` reads a nan range as 0.0 (with
  `import math`) from the start, so Task 14 edits neither the import block nor `_strip`.
- The OKX horizon test relies on common random numbers across horizons: the engine draws its numbers check by check,
  so the first k checks of a 60-day run equal those of a 41-day run on the same seed (contract 8.2-8.3). The forced
  exit at the close of the 2026-12-02 session (Seoul date 2026-12-03) then leaves exactly the 41-day plan's
  terminal values: an exit fill books `units * p * ks + phi`, which is the liquidation charge the 41-day plan books
  at its horizon.

- [ ] **Step 1: Write the failing tests**

  First append the Task 13 block to `tests/odds_fixtures.py`. Read the file; it ends with Task 9's `even_rows`. Use
  the Edit tool with `old_string` = the file's last non-empty line exactly as it stands and `new_string` = that same
  line followed by two empty lines and the block below (`new_string` ends with the block's last line, so the file's
  single final newline stays). Keep LF.

```python
# --------------------------------------------------------------------------- #
# Task 13: pipeline runs on fixture contexts and inputs, the signed-calendar swap and call spies (contract 3.2)
# --------------------------------------------------------------------------- #
from contextlib import contextmanager as _contextmanager  # noqa: E402

CAL_SHA = "ab" * 32           # the calendar sha of every KRX fixture input; calendar_signed(CAL_SHA) signs it


@_contextmanager
def calendar_signed(sha: str) -> Iterator[None]:
    """core.compliance.owner.calendar_in_force swapped for `lambda now: sha` (save/restore), so a KRX or US leg whose
    inputs carry `sha` passes the calendar step. For the KRX steps after that step only: the CALENDAR_UNSIGNED and
    CALENDAR_COVERAGE tests use the real function (no key in the temp home); Task 18 signs a calendar end to end."""
    from core.compliance import owner
    saved = owner.calendar_in_force
    owner.calendar_in_force = lambda now: sha
    try:
        yield
    finally:
        owner.calendar_in_force = saved


@_contextmanager
def spy(target, name: str) -> Iterator[list]:
    """target.<name> wrapped so that every call is recorded as (args, kwargs, result) in the yielded list; the real
    attribute comes back afterwards."""
    real = getattr(target, name)
    calls: list = []

    def recorded(*args, **kwargs):
        result = real(*args, **kwargs)
        calls.append((args, kwargs, result))
        return result

    setattr(target, name, recorded)
    try:
        yield calls
    finally:
        setattr(target, name, real)


def owner_with(**changes):
    """F.ctx's owner state (floor KRW 21,000, daily loss KRW 5,000, OKX cap 0.10, OK) with fields replaced."""
    import dataclasses
    from tests import compliance_fixtures as F
    return dataclasses.replace(F.ctx().owner, **changes)


def fresh_series(n: int = 600, *, end: str = "2026-10-22", **changes):
    """series() of n daily bars whose last bar is `end` (by default the day before the fixture start, so the stale
    check passes); `changes` go to series(), never `start` or `step_days`."""
    import datetime as dt
    first = dt.date.fromisoformat(end) - dt.timedelta(days=n - 1)
    return series(n=n, start=first.isoformat(), **changes)


def weekdays(start, horizon_days: int) -> tuple[str, ...]:
    """Fixture KRX sessions: the weekdays of [start, start + horizon_days). Holidays are ignored: the core checks the
    session list's shape and the calendar sha, never the dates against a calendar."""
    import datetime as dt
    days = (start + dt.timedelta(days=i) for i in range(horizon_days))
    return tuple(d.isoformat() for d in days if d.weekday() < 5)


def pipeline_inputs(plan_obj, series_obj, **changes):
    """inputs() for a fixture leg, its clock reading at 09:00 KST on the plan's start: a crypto leg gets every date of
    the horizon, a KRX leg (kis and a six-digit code) the weekdays with one 0.30 limit each and CAL_SHA. `changes`
    override any Inputs field (a US leg passes its sessions and sha here)."""
    import datetime as dt
    from core.compliance import model
    start, horizon = plan_obj.start, plan_obj.horizon_days
    leg = plan_obj.leg[0] if isinstance(plan_obj.leg, (list, tuple)) else plan_obj.leg
    fields = {"now": dt.datetime(start.year, start.month, start.day, 9, 0, tzinfo=model.KST)}
    if leg.venue == "kis" and leg.symbol.isdigit():
        days = weekdays(start, horizon)
        fields.update(sessions=days, price_limits=(0.30,) * len(days), calendar_sha256=CAL_SHA)
    else:
        fields["sessions"] = tuple((start + dt.timedelta(days=i)).isoformat() for i in range(horizon))
    fields.update(changes)
    return inputs(plan_obj, series_obj, **fields)


def pipeline(plan_obj=None, ctx=None, series_obj=None, *, n_paths=None, **changes):
    """simulate.simulate on a fixture plan (default plan()), context (odds_ctx()) and series (fresh_series()), with
    pipeline_inputs(plan, series, **changes)."""
    from core.odds import simulate
    plan_obj = plan() if plan_obj is None else plan_obj
    ctx = odds_ctx() if ctx is None else ctx
    series_obj = fresh_series() if series_obj is None else series_obj
    return simulate.simulate(plan_obj, ctx, pipeline_inputs(plan_obj, series_obj, **changes), n_paths=n_paths)
```

  Then create `tests/odds_pipeline.py` (LF):

```python
"""Odds plan Task 13: simulate()'s pipeline (spec 4 "How data flows", 6.3, 7.1, 9). Every refusal of Q24 in its
order, each a refused report with no probability; the headline no-edge column at base and 2x costs; the rule dates
and the OKX cap from the gate; shared streams in one comparison; purity (Q5, Q6, Q11, Q24, Q42, Q45; R2-1, R2-5).
Every test runs under OF.chunk() (2,000 paths) except the PARTIAL_CHUNK test, which runs at the real CHUNK and is
refused before any data is read."""
from __future__ import annotations

import builtins
import dataclasses
import datetime as dt
import io
import math
import os
import re
import socket
import time

import numpy as np

from core.compliance import gate, model
from core.odds import bold, costs, models, report, simulate
from core.odds import plan as P
from tests import compliance_fixtures as F
from tests import odds_fixtures as OF

UPBIT = P.Leg(venue="upbit", symbol="BTC", model="bootstrap")
OKX = P.Leg(venue="okx", symbol="BTC", model="bootstrap")
STOCK = P.Leg(venue="kis", symbol="005930", model="bootstrap")
ETF = P.Leg(venue="kis", symbol="069500", model="bootstrap")
REPLAY = P.Leg(venue="upbit", symbol="BTC", model="bootstrap", edge_source=P.REPLAY_SOURCE)
PROVENANCE_KEYS = ("rules_sha", "instruments_sha", "venues_sha", "state_hash", "owner_seq", "owner_row", "code_hash",
                   "code_signed", "fingerprint", "decision_id", "screening_hash", "series_md5", "components",
                   "proxy_dates", "calendar_sha", "calendar_version", "calendar_md5s", "model", "members",
                   "seed_hex", "n", "chunk", "numpy", "scipy", "cryptography", "edge_source", "repo_anchor",
                   "tree_hash", "comparison_id", "run_counter", "plan_hash")


def _krx_series(**changes):
    """A KIS daily history of 600 bars (005930 by default) near KRW 5,000, ending the day before the start."""
    return OF.fresh_series(**{"symbol": "005930", "source": "KIS", "price": 5_000.0, "vol": 0.005, **changes})


def _okx_series():
    """The OKX composite (Binance BTCUSDT x Upbit KRW-USDT), its first 30 dates priced through KRW=X."""
    s = OF.fresh_series(symbol="BTC", source="BINANCE:BTCUSDT*UPBIT:KRW-USDT")
    return dataclasses.replace(s, proxy_dates=(s.dates[0], s.dates[29]))


def _synthetic(s):
    """The same series marked SYNTHETIC, its md5 recomputed so only SYNTHETIC_REFUSED applies."""
    return dataclasses.replace(s, status="SYNTHETIC", md5=P.series_md5(s.symbol, s.source, s.dates, s.open, s.close,
                                                                     s.adjustment, "SYNTHETIC"))


def _signed(thunk):
    """thunk() with the fixture calendar signed (a KRX step after the calendar step)."""
    with OF.calendar_signed(OF.CAL_SHA):
        return thunk()


def _no_probability(text: str) -> bool:
    """Spec 9: no computed probability in the text: no "1 in", no "below about", no digit followed by "%"."""
    return "1 in " not in text and "below about" not in text and re.search(r"[0-9]%", text) is None


def _why_fragment(code: str) -> str:
    """The longest literal piece of why.<code>, which the refused card prints whatever its slots."""
    return max(re.split(r"\{[a-z]+\}", report.CATALOGUE["why." + code]), key=len)


def _strip(rep) -> tuple:
    """The report's columns without their bracket samples (arrays compare element-wise; contract 10.1), a nan
    HIDDEN_EDGE range (GARCH-t and delisting columns) read as 0.0: nan never equals nan, so two equal columns would
    otherwise compare unequal."""
    return tuple(dataclasses.replace(col, brackets=None, x_range=0.0 if math.isnan(col.x_range) else col.x_range)
                 for col in rep.columns)


def test_partial_chunk_is_refused_at_the_real_chunk():
    """Spec 8.o 8, Q10, Q45: at the real CHUNK of 200,000 a path count that is not a positive multiple of it is
    PARTIAL_CHUNK in precheck, before the product checks, and simulate refuses it without reading its inputs."""
    assert simulate.CHUNK == 200_000
    plan_obj, ctx = OF.plan(), OF.odds_ctx()
    for n in (1_000, 300_000, 0, -200_000, True, 200_000.0):
        ref = simulate.precheck(plan_obj, ctx, n)
        assert (ref.code, dict(ref.slots)) == ("PARTIAL_CHUNK", {"chunk": "200,000"}), n
        rep = simulate.simulate(plan_obj, ctx, None, n_paths=n)          # None: no input is ever read
        assert rep.refused.code == "PARTIAL_CHUNK" and rep.columns == (), n
    assert simulate.precheck(plan_obj, ctx, 200_000) is None and simulate.precheck(plan_obj, ctx) is None
    assert simulate.precheck(OF.plan(leg=(UPBIT, UPBIT)), ctx, 1_000).code == "PARTIAL_CHUNK"
    assert simulate.precheck(OF.plan(leg=(UPBIT, UPBIT)), ctx, 200_000).code == "MULTI_LEG_UNSUPPORTED"


def test_every_refusal_in_q24_order():
    """Q24, O10: one fixture per refusal, in the reporting order (CARD_NOT_REPRODUCED and MODEL_CHECK_FAILED have
    their own tests below), plus two that break two steps at once and report the earlier: stale data under an unsigned
    calendar (step 6 before 7) and a KRX GARCH-t leg on a KRW 1 share (11 before 12). Each is a refused report with
    no column, no flag and no probability, rendering its sentence. screen() is reached only by the SCREEN_BLOCKED
    case, with a positive float stake (O11)."""
    later = dt.date(2026, 11, 23)
    saturday = dt.date(2026, 10, 24)
    bold_leg = dataclasses.replace(UPBIT, bracket=P.Bracket(take_profit=0.001, stop=0.05))
    cases = [
        ("PARTIAL_CHUNK", "", None, lambda: OF.pipeline(n_paths=1_000)),
        ("UNSUPPORTED_PRODUCT", "start", None, lambda: OF.pipeline(OF.plan(start=saturday))),
        ("MULTI_LEG_UNSUPPORTED", "", None, lambda: OF.pipeline(OF.plan(leg=(UPBIT, UPBIT)))),
        ("STATE_UNUSABLE", "code", None, lambda: OF.pipeline(ctx=OF.odds_ctx(code_signed=False))),
        ("LIMITS_UNSET", "", None, lambda: OF.pipeline(
            ctx=OF.odds_ctx(owner=OF.owner_with(limits={"daily_loss_krw": 5_000.0})))),
        ("LIMITS_UNSET", "cap", None, lambda: OF.pipeline(
            OF.plan(leg=OKX), OF.odds_ctx(owner=OF.owner_with(caps={})), _okx_series())),
        ("DATA_INVALID", "now", None, lambda: OF.pipeline(                 # naive: calendar_in_force would raise
            OF.plan(leg=ETF), series_obj=_krx_series(symbol="069500"), now=dt.datetime(2026, 10, 23, 9, 0))),
        ("CALENDAR_UNSIGNED", "", None, lambda: OF.pipeline(                # the real function: no key, no approval
            OF.plan(leg=ETF), series_obj=_krx_series(symbol="069500"))),
        ("CALENDAR_UNSIGNED", "", None, lambda: OF.pipeline(                # step 6 before 7: stale data as well
            OF.plan(leg=ETF), series_obj=_krx_series(symbol="069500", end="2026-10-01"))),
        ("CALENDAR_COVERAGE", "", None, lambda: OF.pipeline(
            OF.plan(leg=ETF), series_obj=_krx_series(symbol="069500"),
            calendar_error="coverage: the horizon runs past 2027-12-31")),
        ("DATA_INVALID", "stale", None, lambda: OF.pipeline(series_obj=OF.fresh_series(end="2026-10-19"))),
        ("DATA_INVALID", "empty", None, lambda: _signed(lambda: OF.pipeline(   # one Saturday: no KRX session
            OF.plan(leg=ETF, start=saturday, horizon_days=1), OF.odds_ctx(date=saturday),
            _krx_series(symbol="069500", end="2026-10-23")))),
        ("SYNTHETIC_REFUSED", "", None, lambda: OF.pipeline(series_obj=_synthetic(OF.fresh_series()))),
        ("NOT_TRADABLE", "", None, lambda: OF.pipeline(ctx=OF.odds_ctx(active=F.approved()))),   # shipped venues
        ("NOT_TRADABLE", "", "2027", lambda: _signed(lambda: OF.pipeline(      # R2-1: a 2027 sell has no signed tax
            OF.plan(leg=STOCK, horizon_days=366), series_obj=_krx_series()))),
        ("SPECIAL_REGIME", "", None, lambda: _signed(lambda: OF.pipeline(
            OF.plan(leg=ETF), series_obj=_krx_series(symbol="069500", n=59)))),
        ("SHORT_HISTORY", "", None, lambda: OF.pipeline(series_obj=OF.fresh_series(n=249))),
        ("MODEL_NOT_FOR_LIMITED_VENUE", "", None, lambda: _signed(lambda: OF.pipeline(
            OF.plan(leg=dataclasses.replace(ETF, model="garch_t")), series_obj=_krx_series(symbol="069500")))),
        ("MODEL_NOT_FOR_LIMITED_VENUE", "", None, lambda: _signed(lambda: OF.pipeline(   # 11 before 12: KRW 1 too
            OF.plan(leg=dataclasses.replace(STOCK, model="garch_t")), series_obj=_krx_series(price=1.0, vol=0.001)))),
        ("COST_DOMINATED", "", "4kappa", lambda: _signed(lambda: OF.pipeline(   # a KRW 1 share: half a tick is 50%
            OF.plan(leg=STOCK), series_obj=_krx_series(price=1.0, vol=0.001)))),
        ("COST_DOMINATED", "", "bold", lambda: OF.pipeline(OF.plan(leg=bold_leg, fraction=P.bold()))),
        ("STUCK_AT_START", "", None, lambda: OF.pipeline(ctx=OF.odds_ctx(owner=OF.owner_with(
            limits={"total_loss_floor_krw": 41_000.0, "daily_loss_krw": 5_000.0})))),
        ("SCREEN_BLOCKED", "row", None, lambda: OF.pipeline(                 # review_by 2026-11-22 has passed
            OF.plan(start=later), OF.odds_ctx(date=later), OF.fresh_series(end="2026-11-22"))),
    ]
    with OF.chunk(), OF.spy(gate, "screen") as screens:
        for code, sub, detail, thunk in cases:
            rep = thunk()
            ref = rep.refused
            assert ref is not None and (ref.code, ref.sub) == (code, sub), (code, sub, ref)
            assert detail is None or detail in ref.detail, (code, ref.detail)
            assert rep.columns == () and rep.flags == () and rep.hidden is None and rep.spread is None, code
            text = report.render(rep)
            assert _no_probability(text) and report.say("refused.none") in text, (code, text)
            assert _why_fragment(code) in text, (code, text)
            if code == "NOT_TRADABLE":
                assert f"{ref.slots['venue']} {ref.slots['symbol']} cannot be costed" in text, text
            if code == "SCREEN_BLOCKED":
                assert dict(ref.slots) == {"row": "KR-DOMESTIC-SPOT"} and "rule KR-DOMESTIC-SPOT" in text, text
    assert len(screens) == 1, screens
    stake = screens[0][0][2]
    assert type(stake) is float and stake > 0.0, stake


def test_one_krx_plan_breaking_three_data_rules_reports_o10_order():
    """O10's data order (Q24 steps 7-9): a KRX stock plan with a made-up 59-bar history and a 366-day horizon that
    reaches 2027 breaks SYNTHETIC_REFUSED, NOT_TRADABLE (R2-1: a 2027 sell has no signed tax) and SPECIAL_REGIME; it
    reports SYNTHETIC_REFUSED, then NOT_TRADABLE once the data are real, then SPECIAL_REGIME once the horizon ends in
    2026."""
    real = _krx_series(n=59)
    with OF.chunk(), OF.calendar_signed(OF.CAL_SHA):
        codes = [OF.pipeline(OF.plan(leg=STOCK, horizon_days=h), series_obj=s).refused.code
                 for s, h in ((_synthetic(real), 366), (real, 366), (real, 10))]
    assert codes == ["SYNTHETIC_REFUSED", "NOT_TRADABLE", "SPECIAL_REGIME"], codes


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


def test_garch_headlines_are_refused_until_their_pilot_is_built():
    """Q24 step 14 placeholder (Task 14 replaces this test with the GARCH-t headline and its pilot checks): a garch_t
    leg on a crypto venue passes every earlier step, the gate included, and is MODEL_CHECK_FAILED (sub "fit", detail
    "garch not built yet"), so no number comes from an unchecked model."""
    with OF.chunk(), OF.spy(gate, "screen") as screens:
        rep = OF.pipeline(OF.plan(leg=dataclasses.replace(UPBIT, model="garch_t")))
    assert (rep.refused.code, rep.refused.sub, rep.refused.detail) == ("MODEL_CHECK_FAILED", "fit",
                                                                       "garch not built yet")
    assert len(screens) == 1 and rep.columns == () and _no_probability(report.render(rep))


def test_a_crypto_plan_gets_its_headline_column_at_base_and_2x_costs():
    """Contract 8.5 step 7: the headline no-edge column at base and 2x costs on one seed (Q34), W0 = the stake and the
    owner's floor and daily loss (O11), open and close checks (Q22), no band, l_min = the floor under floor-protected
    sizing and 0 under stop-based sizing (Q32), and every provenance key; the card renders."""
    series_obj = OF.fresh_series()
    stop_leg = dataclasses.replace(UPBIT, bracket=P.Bracket(take_profit=0.5, stop=0.2), sizing="stop_based")
    with OF.chunk(), OF.spy(simulate, "run_column") as runs:
        rep = OF.pipeline(series_obj=series_obj)
        stop = OF.pipeline(OF.plan(leg=stop_leg), series_obj=series_obj)
    assert rep.refused is None and stop.refused is None, (rep.refused, stop.refused)
    base, stress = rep.columns
    assert (base.key, stress.key, rep.headline) == ("no_edge/bootstrap/base", "no_edge/bootstrap/stress2x",
                                                     "no_edge/bootstrap/base")
    assert (base.member, base.scenario, stress.scenario, base.n, stress.n, rep.n) == (
        "bootstrap", "base", "stress2x", 2_000, 2_000, 2_000)
    assert stress.mean_cost > base.mean_cost > 0.0
    assert (rep.spread, rep.spread_kind, rep.notes, rep.hidden) == (None, "none", (), None)
    assert (rep.model_key, dict(rep.model_slots)) == ("model.bootstrap", {
        "symbol": "BTC", "first": series_obj.dates[0], "last": "2026-10-22", "rows": "600"})
    assert (rep.floor, rep.l_min, rep.sizing, rep.ceiling) == (21_000.0, 21_000.0, "floor_safe",
                                                               bold.ceiling(42_000.0, 21_000.0, 42_000_000.0))
    assert (stop.l_min, stop.sizing, stop.ceiling) == (0.0, "stop_based", bold.ceiling(42_000.0, 0.0, 42_000_000.0))
    assert (rep.tax_basis, rep.cost_words_key, rep.comparison) == ("crypto_22pct_from_2027", "cost.fees", (1, 0, 1))
    (spec_b,), kw_b, _ = runs[0]
    (spec_s,), kw_s, _ = runs[1]
    seed = models.market_seed(models.data_hashes(series_obj, None), "", "c000001", 1)
    assert kw_b["seed"] == kw_s["seed"] == seed and (spec_b.mult, spec_s.mult) == (1.0, 2.0)
    m_o, m_i, r = models.rows(series_obj)
    assert (spec_b.engine, spec_b.block, spec_b.p0) == ("bootstrap", models.block_length(r), series_obj.close[-1])
    assert np.array_equal(spec_b.m_o, m_o) and np.array_equal(spec_b.m_i, m_i)       # opens, then closes (Q22)
    assert (spec_b.w0, spec_b.target, spec_b.floor, spec_b.daily_loss) == (42_000.0, 42_000_000.0, 21_000.0, 5_000.0)
    assert (spec_b.cap_krw, spec_b.stop_entries_from, spec_b.force_exit_from, spec_b.fstar) == (None, None, None, None)
    assert len(spec_b.checks.on) == 20 and spec_b.limits.shape == (10,) and bool(np.isnan(spec_b.limits).all())
    prov = dict(rep.provenance)
    assert sorted(prov) == sorted(PROVENANCE_KEYS)
    assert (prov["seed_hex"], prov["series_md5"], prov["code_hash"], prov["members"], prov["n"]) == (
        seed.hex(), series_obj.md5, "c" * 64, ("bootstrap",), 2_000)
    assert (prov["plan_hash"], prov["chunk"], prov["comparison_id"], prov["calendar_sha"]) == (
        rep.plan_hash, 2_000, "c000001", "")
    text = report.render(rep)
    assert report.say("column.stress") in text and "Plan 1 of 1" in text


def test_a_plan_with_no_path_count_runs_the_default():
    """Contract 8.5: n = n_paths, or DEFAULT_PATHS[track] when it is None (2,000 under chunk(); set per track here,
    and chunk() restores it); a multiple of CHUNK runs as that many chunks."""
    with OF.chunk():
        default = OF.pipeline()
        twice = OF.pipeline(n_paths=4_000)
        simulate.DEFAULT_PATHS = {"moonshot": 4_000, "compounding": 2_000}
        moonshot = OF.pipeline(OF.plan(track="moonshot"))
        compounding = OF.pipeline()
    assert [c.n for c in default.columns] == [2_000, 2_000] and default.n == 2_000
    assert [c.n for c in twice.columns] == [4_000, 4_000] and twice.n == 4_000
    assert (moonshot.n, compounding.n) == (4_000, 2_000)
    assert simulate.DEFAULT_PATHS == {"moonshot": 1_000_000, "compounding": 200_000}


def test_a_krx_leg_runs_only_under_the_signed_calendar():
    """Q6 (O6): a KRX stock leg simulates when the calendar signed at inputs.now is the set its sessions came from;
    its spec carries one 0.30 limit per session and an open and a close check of each, its cost words name the
    transaction tax (Q37) and its provenance the calendar sha. A different signed sha, or an error reported by the
    unsigned side, is CALENDAR_UNSIGNED."""
    plan_obj, series_obj = OF.plan(leg=STOCK), _krx_series()
    days = OF.weekdays(plan_obj.start, plan_obj.horizon_days)
    with OF.chunk(), OF.spy(simulate, "run_column") as runs:
        with OF.calendar_signed(OF.CAL_SHA):
            rep = OF.pipeline(plan_obj, series_obj=series_obj)
            unsigned = OF.pipeline(plan_obj, series_obj=series_obj,
                                   calendar_error="unsigned: no signed calendar approval")
        with OF.calendar_signed("cd" * 32):
            other = OF.pipeline(plan_obj, series_obj=series_obj)
    assert rep.refused is None, rep.refused
    assert len(days) == 6 and len(runs) == 2
    spec = runs[0][0][0]
    assert spec.limits.tolist() == [0.30] * 6 and len(spec.checks.on) == 12
    assert spec.checks.on[::2] == tuple(dt.date.fromisoformat(d) for d in days)
    assert (rep.cost_words_key, rep.tax_basis) == ("cost.tax", "krx_small_holder_exempt")
    assert dict(rep.provenance)["calendar_sha"] == OF.CAL_SHA
    assert unsigned.refused.code == other.refused.code == "CALENDAR_UNSIGNED"


def test_the_okx_leg_is_ack_required_simulated_and_flagged():
    """O11, Q20: an OKX BTC leg is ACK_REQUIRED at the gate and still simulated; every simulated entry is capped at
    cap x stake = KRW 4,200 and the card says so; it is flagged GREY_LEG (KR-OKX-SPOT, 10%, off 2026-12-03) and
    PROXY_DATA (the composite feed and its KRW=X dates)."""
    with OF.chunk(), OF.spy(gate, "screen") as screens, OF.spy(simulate, "run_column") as runs:
        rep = OF.pipeline(OF.plan(leg=OKX), series_obj=_okx_series())
    (args, _, screening), = screens
    assert screening.decision.verdict == model.ACK_REQUIRED and screening.allowed
    assert type(args[2]) is float and 0.0 < args[2] <= 4_200.0, args[2]
    assert rep.refused is None, rep.refused
    assert [run[0][0].cap_krw for run in runs] == [4_200.0, 4_200.0]
    grey = [(f.level, f.key, dict(f.slots)) for f in rep.flags if f.code == "GREY_LEG"]
    assert grey == [("amber", "flag.grey", {"row": "KR-OKX-SPOT", "cap": "10%", "off": "2026-12-03"})], grey
    assert [f.key for f in rep.flags if f.code == "PROXY_DATA"] == ["flag.proxy", "flag.proxyfx"]
    assert (rep.model_slots["cap"], rep.model_slots["capkrw"]) == ("10%", "4,200")
    text = report.render(rep)
    for line in (report.say("okx.cap", cap="10%", capkrw="4,200"), report.say("flag.proxy"),
                 report.say("flag.grey", row="KR-OKX-SPOT", cap="10%", off="2026-12-03")):
        assert line in text, line


def test_rule_dates_come_from_the_screening_flags():
    """Q5 (O5): a 60-day Upbit plan holds KR-DOMESTIC-SPOT's review_by 2026-11-22: entries stop from that date, with
    no forced exit, and the card prints RULE_CHANGE_IN_HORIZON; a 10-day plan has no rule date. Contract 8.5 step 7
    on made-up flags (the shipped rows have no effective_until, and their review_by comes before auto_off): entries
    stop from the earliest flag of any field, and the forced exit comes from the earliest auto_off or
    effective_until, so a bracket leg never re-enters after it."""
    with OF.chunk(), OF.spy(simulate, "run_column") as runs:
        long_ = OF.pipeline(OF.plan(horizon_days=60))
        short = OF.pipeline(OF.plan())
    dates = [(run[0][0].stop_entries_from, run[0][0].force_exit_from) for run in runs]
    assert dates == [(dt.date(2026, 11, 22), None)] * 2 + [(None, None)] * 2, dates
    rule = [(f.level, f.key, dict(f.slots)) for f in long_.flags if f.code == "RULE_CHANGE_IN_HORIZON"]
    assert rule == [("amber", "rule.review", {"date": "2026-11-22", "row": "KR-DOMESTIC-SPOT"})], rule
    assert not any(f.code == "RULE_CHANGE_IN_HORIZON" for f in short.flags)
    assert report.say("rule.review", date="2026-11-22", row="KR-DOMESTIC-SPOT") in report.render(long_)
    plan_obj, ctx = OF.plan(horizon_days=60), OF.odds_ctx()
    inputs = OF.pipeline_inputs(plan_obj, OF.fresh_series())
    terms = costs.terms(*P.instrument(plan_obj, ctx), plan_obj.fx_krw_per_usd)
    sessions = tuple(dt.date.fromisoformat(d) for d in inputs.sessions)
    screening = gate.screen(plan_obj, ctx, 42_000.0)
    d1, d2, d3 = dt.date(2026, 11, 2), dt.date(2026, 11, 5), dt.date(2026, 11, 22)
    for flags, want in ((((d1, "effective_until", "R1"), (d3, "review_by", "R2")), (d1, d1)),
                        (((d2, "auto_off", "R1"),), (d2, d2)),
                        (((d1, "review_by", "R2"), (d2, "auto_off", "R1")), (d1, d2))):
        spec = simulate._headline_spec(plan_obj, ctx, inputs, terms=terms, market="CRYPTO", sessions=sessions,
                                       screening=dataclasses.replace(screening, flags=flags))
        assert (spec.stop_entries_from, spec.force_exit_from) == want, (flags, spec.stop_entries_from)


def test_an_okx_horizon_across_auto_off_is_forced_out():
    """O5 end to end: a 60-day OKX plan holds KR-OKX-SPOT's review_by 2026-11-22 and auto_off 2026-12-03, so entries
    stop from 2026-11-22 and the position is closed at the first check on or after 2026-12-03, the close of the
    2026-12-02 session (Seoul date 2026-12-03, Q22). Its terminal values then equal those of a 41-day plan on the same
    streams, whose last check is that close and whose horizon holds no auto_off; the card prints rule.end with
    rule.auto."""
    series_obj = _okx_series()
    with OF.chunk(), OF.spy(simulate, "run_column") as runs:
        long_ = OF.pipeline(OF.plan(leg=OKX, horizon_days=60), series_obj=series_obj)
        short = OF.pipeline(OF.plan(leg=OKX, horizon_days=41), series_obj=series_obj)
    long_spec, short_spec = runs[0][0][0], runs[2][0][0]
    assert (long_spec.stop_entries_from, long_spec.force_exit_from) == (dt.date(2026, 11, 22), dt.date(2026, 12, 3))
    assert (short_spec.stop_entries_from, short_spec.force_exit_from) == (dt.date(2026, 11, 22), None)
    last = len(short_spec.checks.seoul) - 1
    assert short_spec.checks.seoul[last] == long_spec.checks.seoul[last] == dt.date(2026, 12, 3)
    assert runs[0][1]["seed"] == runs[2][1]["seed"]
    for a, b in zip(long_.columns, short.columns):
        assert a.trades == b.trades > 0 and (a.at_floor, a.reached) == (b.at_floor, b.reached), a.key
        for name in ("median", "p5", "mean", "mean_cost"):
            x, y = getattr(a, name), getattr(b, name)
            assert abs(x - y) <= 1e-9 * abs(y), (a.key, name, x, y)
    ends = [(f.key, dict(f.slots)) for f in long_.flags if f.code == "RULE_CHANGE_IN_HORIZON"]
    assert ends == [("rule.review", {"date": "2026-11-22", "row": "KR-OKX-SPOT"}),
                    ("rule.end", {"date": "2026-12-03", "row": "KR-OKX-SPOT", "what": report.say("rule.auto")})], ends
    text = report.render(long_)
    assert report.say("rule.end", date="2026-12-03", row="KR-OKX-SPOT", what=report.say("rule.auto")) in text


def test_one_comparison_shares_its_streams():
    """Spec 8.o 8, Q34: plans on the same data in one comparison share every stream. Two plans that differ only in
    name have one plan hash and equal headline columns; a plan with twice the stake runs on the same paths (with no
    floor and no daily loss its terminal values double to within a lot); another comparison id gives another seed."""
    ctx = OF.odds_ctx(owner=OF.owner_with(limits={"total_loss_floor_krw": 0.0, "daily_loss_krw": 1e9}))
    series_obj = OF.fresh_series()
    with OF.chunk(), OF.spy(simulate, "run_column") as runs:
        a = OF.pipeline(OF.plan(name="first"), ctx, series_obj)
        b = OF.pipeline(OF.plan(name="second"), ctx, series_obj)
        c = OF.pipeline(OF.plan(stake_krw=84_000.0), ctx, series_obj)
        d = OF.pipeline(OF.plan(), ctx, series_obj, comparison_id="c000002")
        one = OF.pipeline(OF.plan(leg=(UPBIT,)), ctx, series_obj)
    seeds = [run[1]["seed"] for run in runs]
    assert len(set(seeds[:6])) == 1 and seeds[6] == seeds[7] != seeds[0] and seeds[8] == seeds[0]
    assert a.plan_hash == b.plan_hash == one.plan_hash and _strip(a) == _strip(b) == _strip(one)
    for col_a, col_c in zip(a.columns, c.columns):
        for name in ("median", "p5"):
            x, y = getattr(col_c, name), 2.0 * getattr(col_a, name)
            assert abs(x - y) <= 2.0, (col_a.key, name, x, y)
    assert _strip(d) != _strip(a)


def test_simulate_is_pure_after_a_warm_up():
    """Q42: after one warm-up run (every lazy import loaded), a crypto run with open, io.open, os.open, socket
    connect and time.time patched to raise gives the same report."""
    def trap(*args, **kwargs):
        raise AssertionError("simulate reached a file, a socket or the clock")
    plan_obj, series_obj, ctx = OF.plan(), OF.fresh_series(), OF.odds_ctx()
    inputs = OF.pipeline_inputs(plan_obj, series_obj)
    with OF.chunk():
        first = simulate.simulate(plan_obj, ctx, inputs)
        saved = [(builtins, "open", builtins.open), (io, "open", io.open), (os, "open", os.open),
                 (socket.socket, "connect", socket.socket.connect), (time, "time", time.time)]
        try:                                               # inside try: a failed setattr still restores every entry
            for target, name, _ in saved:
                setattr(target, name, trap)
            again = simulate.simulate(plan_obj, ctx, inputs)
        finally:
            for target, name, real in reversed(saved):
                setattr(target, name, real)
    assert first.refused is None and _strip(again) == _strip(first)
    assert report.render(again) == report.render(first)
```

- [ ] **Step 2: Run to verify it fails**

  Overlap check (Git Bash form; it must print nothing, otherwise wait), then the module:

```bash
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && .venv/Scripts/python.exe -m tests.odds_acceptance odds_pipeline/
```

  Expected: 13 FAIL lines after their tracebacks; `odds_pipeline/test_partial_chunk_is_refused_at_the_real_chunk`
  fails with `AttributeError: module 'core.odds.simulate' has no attribute 'precheck'` and the other 12 with
  `AttributeError: module 'core.odds.simulate' has no attribute 'simulate'`, for example

```
FAIL odds_pipeline/test_every_refusal_in_q24_order AttributeError: module 'core.odds.simulate' has no attribute 'simulate'
```

  and the summary `0/13 passed, 13 failed, 0 not run` (exit code 1). Any other failure (an import error of the
  module, a NameError in the fixtures) means an earlier task's name differs from the contract: stop and rule.

- [ ] **Step 3: Implement**

  Check first that none of the new names exists yet and that Task 9's names do (Git Bash):

```bash
grep -nE "^(def (precheck|simulate|_calendar_refusal|_screen_refusal|_cap_text|_grey_slots|_headline_spec|_no_edge_pair|context_provenance|_report_provenance|_refused_report|_accepted_report)\(|_VENUE_NAMES)" core/odds/simulate.py
grep -cE "^(CHUNK|DEFAULT_PATHS) = |^def (checks|run_column)\(|^class (Checks|PathSpec)\b" core/odds/simulate.py
```

  The first prints nothing; the second prints `6`. Then read `core/odds/simulate.py` and make two Edits. Keep LF.

  **Edit A** (anchor: the module docstring, its last line, as Task 9 wrote it and Task 10 kept it; it occurs once in
  the file). Part 3 reaches I/O through `owner.calendar_in_force` for KRX and US legs, so the purity claim names that
  step. `old_string`:

```text
Pure: no clock, no file, no network.
```

  `new_string`:

```text
Pure except `simulate`'s calendar step, which reads the signed calendar through owner.calendar_in_force for KRX and
US legs (Q42); no clock, no network.
```

  **Edit B** (anchor: the end of the file, after the last definition Task 10 left): append the block below with
  `old_string` = the file's last non-empty line as it stands and `new_string` = that line followed by two empty lines
  and the block (`new_string` ends with the block's last line, so the file's single final newline stays).

```python
# --------------------------------------------------------------------------- #
# Part 3 (Task 13): the pipeline of contract 8.5. precheck, every refusal of Q24 in its order, the headline no-edge
# column at base and 2x costs, the rule dates and the OKX cap from the gate, and the report. Task 14 adds the other
# columns and the GARCH-t headline, Task 17 the replay.
# --------------------------------------------------------------------------- #
import dataclasses  # noqa: E402
from datetime import date  # noqa: E402

import numpy as np  # noqa: E402
import scipy  # noqa: E402

from core.compliance import gate, model, owner  # noqa: E402
from core.odds import bold, costs, models, plan, report  # noqa: E402

_VENUE_NAMES = {"kis": "KIS", "upbit": "Upbit", "okx": "OKX"}      # the {venue} slot of why.NOT_TRADABLE


def precheck(plan_obj, ctx, n_paths: int | None = None) -> plan.Refusal | None:
    """Q24 steps 1-4, before any data is loaded (Q45): PARTIAL_CHUNK when n_paths is given and is not a positive
    multiple of CHUNK; then plan.check_plan (the start date included) and plan.check_state (unsigned code, both limits
    and the OKX cap included). Never raises on a malformed plan."""
    if n_paths is not None and (type(n_paths) is not int or n_paths <= 0 or n_paths % CHUNK):
        return plan.Refusal(code="PARTIAL_CHUNK", slots={"chunk": f"{CHUNK:,}"}, detail=f"n_paths {n_paths!r}")
    return plan.check_plan(plan_obj, ctx) or plan.check_state(plan_obj, ctx)


def simulate(plan_obj, ctx, inputs: plan.Inputs, *, n_paths: int | None = None) -> report.OddsReport:
    """The odds of one plan (contract 8.5): the refusals of Q24 in their order, each a refused report with no
    probability, then the columns and the report; n = n_paths, or DEFAULT_PATHS[track] when it is None. The only
    I/O is owner.calendar_in_force for KRX and US legs (Q42). Raises only on a bug."""
    refusal = precheck(plan_obj, ctx, n_paths)
    if refusal is not None:
        return _refused_report(plan_obj, ctx, refusal)
    if isinstance(plan_obj.leg, (list, tuple)):            # check_plan let exactly one Leg through; screen needs it
        plan_obj = dataclasses.replace(plan_obj, leg=plan_obj.leg[0])
    leg = plan_obj.leg
    venue, inst = plan.instrument(plan_obj, ctx)
    market = plan.MARKET[(leg.venue, inst.section)]
    refusal = (plan.check_now(ctx, inputs.now) or _calendar_refusal(market, inputs)
               or plan.check_data(plan_obj, ctx, inputs, market))
    if refusal is not None:
        return _refused_report(plan_obj, ctx, refusal)
    replay = leg.edge_source == plan.REPLAY_SOURCE
    sessions = tuple(date.fromisoformat(d) for d in inputs.sessions)
    try:
        terms = costs.terms(venue, inst, plan_obj.fx_krw_per_usd, replay=replay)
        costs.check_validity(terms, sessions)
    except costs.NotTradable as exc:
        refusal = plan.Refusal(code="NOT_TRADABLE", slots={"venue": _VENUE_NAMES[leg.venue], "symbol": leg.symbol},
                               detail=str(exc))
        return _refused_report(plan_obj, ctx, refusal)
    refusal = plan.check_history(plan_obj, inputs, market)
    if refusal is None and replay:                         # Task 17 replaces this branch with models.verify_replay
        refusal = plan.Refusal(code="CARD_NOT_REPRODUCED", detail="replay not built yet")
    if refusal is None and leg.model == "garch_t" and market == "KR":
        refusal = plan.Refusal(code="MODEL_NOT_FOR_LIMITED_VENUE", detail="GARCH-t has no KRX daily band")
    if refusal is not None:
        return _refused_report(plan_obj, ctx, refusal)
    p0, first_day = float(inputs.series.close[-1]), sessions[0]
    why = costs.cost_refusal(plan_obj, terms, p0, first_day)
    if why is not None:
        return _refused_report(plan_obj, ctx, plan.Refusal(code="COST_DOMINATED", detail=why))
    first = costs.first_stake(plan_obj, terms, ctx, p0, first_day)
    if first <= 0.0:                                       # never screen a zero stake (O11)
        refusal = plan.Refusal(code="STUCK_AT_START", detail=f"first stake {first!r} at {p0!r}")
        return _refused_report(plan_obj, ctx, refusal)
    screening = gate.screen(plan_obj, ctx, float(first))
    if not screening.allowed:
        return _refused_report(plan_obj, ctx, _screen_refusal(screening, ctx))
    if leg.model == "garch_t":                             # Task 14 replaces this branch with the GARCH-t headline
        refusal = plan.Refusal(code="MODEL_CHECK_FAILED", sub="fit", detail="garch not built yet")
        return _refused_report(plan_obj, ctx, refusal)
    n = DEFAULT_PATHS[plan_obj.track] if n_paths is None else n_paths
    return _accepted_report(plan_obj, ctx, inputs, inst=inst, terms=terms, market=market, sessions=sessions,
                            screening=screening, n=n)


def _calendar_refusal(market: str, inputs) -> plan.Refusal | None:
    """Q24 step 6 (Q6), KRX and US legs only: CALENDAR_COVERAGE on a "coverage: ..." error of the unsigned side;
    else CALENDAR_UNSIGNED unless it reported no error and the calendar signed at inputs.now is exactly the set the
    sessions came from. owner.calendar_in_force is the core's only I/O (Q42)."""
    if market not in ("KR", "US"):
        return None
    error = inputs.calendar_error
    if type(error) is str and error.startswith("coverage:"):
        return plan.Refusal(code="CALENDAR_COVERAGE", detail=error)
    if error != "":
        return plan.Refusal(code="CALENDAR_UNSIGNED", detail=str(error))
    sha = owner.calendar_in_force(inputs.now)
    if type(sha) is not str or sha != inputs.calendar_sha256:
        return plan.Refusal(code="CALENDAR_UNSIGNED",
                            detail=f"signed {sha!r}, sessions from {inputs.calendar_sha256!r}")
    return None


def _screen_refusal(screening, ctx) -> plan.Refusal:
    """SCREEN_BLOCKED with the sub of the gate's first reason: "unsigned" for unsigned code; "row" with the row id
    when the reason names a row of the table ("stale: review by <date> passed (<id>)", "<what>: <id>"); else
    "other"."""
    reasons = screening.decision.reasons
    first, detail = (reasons[0] if reasons else ""), "; ".join(reasons)
    if first == "unsigned code":
        return plan.Refusal(code="SCREEN_BLOCKED", sub="unsigned", detail=detail)
    row = first[first.rfind("(") + 1:-1] if first.endswith(")") else first.rpartition(": ")[2]
    if row in {r.id for r in ctx.active.rules.rows}:
        return plan.Refusal(code="SCREEN_BLOCKED", sub="row", slots={"row": row}, detail=detail)
    return plan.Refusal(code="SCREEN_BLOCKED", sub="other", detail=detail)


def _cap_text(x: float) -> str:
    """A cap as the card prints it: 0.1 -> "10%"."""
    return f"{100.0 * x:g}%"


def _grey_slots(plan_obj, ctx) -> tuple[tuple[str, str, str], ...]:
    """(row id, cap, auto-off date) of each in-force grey row of the leg (gate.grey_rows), for GREY_LEG. The gate
    has already refused a grey row whose cap is unset ("cap unset"), so every cap here is set."""
    rows = {row.id: row for row in ctx.active.rules.rows}
    return tuple((rid, _cap_text(ctx.owner.caps[rows[rid].cap_key]), rows[rid].auto_off.isoformat())
                 for rid in gate.grey_rows(plan_obj, ctx))


def _headline_spec(plan_obj, ctx, inputs, *, terms, market: str, sessions: tuple[date, ...], screening) -> PathSpec:
    """The headline member's PathSpec at base costs: the bootstrap rows and block of the history, open and close
    checks (Q22), the KRX limits per session, W0 = the stake (O11), the OKX per-entry cap, and the rule dates of
    Screening.flags (Q5): entries stop from the earliest flag date, and a forced exit comes at the first check on or
    after the earliest auto_off or effective_until. Every other column is dataclasses.replace of it."""
    leg, limits, flags = plan_obj.leg, ctx.owner.limits, screening.flags
    m_o, m_i, r = models.rows(inputs.series)
    return PathSpec(
        track=plan_obj.track, w0=float(plan_obj.stake_krw), target=float(plan_obj.target_krw),
        floor=float(limits["total_loss_floor_krw"]), daily_loss=float(limits["daily_loss_krw"]),
        p0=float(inputs.series.close[-1]), engine="bootstrap", m_o=m_o, m_i=m_i, block=models.block_length(r),
        checks=checks(market, sessions, False),
        limits=(np.asarray(inputs.price_limits, dtype=float) if market == "KR"
                else np.full(len(sessions), np.nan)),
        terms=terms, mult=costs.SCENARIOS["base"], bracket=leg.bracket, sizing=leg.sizing,
        fraction=plan_obj.fraction, fstar=None,
        cap_krw=(ctx.owner.caps[plan.OKX_CAP_KEY] * float(plan_obj.stake_krw) if leg.venue == "okx" else None),
        stop_entries_from=min((d for d, _, _ in flags), default=None),
        force_exit_from=min((d for d, what, _ in flags if what in ("auto_off", "effective_until")), default=None),
        delist_h=None)


def _no_edge_pair(spec: PathSpec, member: str, *, n: int, seed: bytes) -> tuple[report.ColumnStats, ...]:
    """One member's no-edge column at base and at 2x costs, on the same streams (common random numbers, Q31)."""
    return tuple(run_column(dataclasses.replace(spec, mult=mult), n=n, seed=seed, key=f"no_edge/{member}/{name}",
                            member=member, scenario=name) for name, mult in costs.SCENARIOS.items())


def context_provenance(ctx) -> dict:
    """The provenance keys a sealed context gives (its tables, owner head, key fingerprint and code hash), else {}.
    Every report of this module carries them, and so do the cards the CLI refuses itself (Task 18)."""
    if not model.is_sealed(ctx):
        return {}
    active, head = ctx.active, ctx.owner.head
    hashes = dict(getattr(active, "hashes", {}) or {})
    return {"rules_sha": hashes.get("rules", ""), "instruments_sha": hashes.get("instruments", ""),
            "venues_sha": hashes.get("venues", ""), "state_hash": active.state_hash, "owner_seq": head[0],
            "owner_row": head[1], "code_hash": ctx.code_hash, "code_signed": ctx.code_signed,
            "fingerprint": ctx.owner.fingerprint}


def _report_provenance(plan_obj, ctx, inputs, *, screening, seed: bytes, n: int, members: tuple[str, ...]) -> dict:
    """Every provenance key of contract 10.1, stored as data (render prints hashes as 16-hex prefixes)."""
    series, leg, prov = inputs.series, plan_obj.leg, inputs.provenance
    return {**context_provenance(ctx), "decision_id": screening.decision.decision_id,
            "screening_hash": screening.screening_hash, "series_md5": series.md5, "components": series.components,
            "proxy_dates": series.proxy_dates, "calendar_sha": inputs.calendar_sha256,
            "calendar_version": inputs.calendar_version, "calendar_md5s": inputs.calendar_md5s, "model": leg.model,
            "members": members, "seed_hex": seed.hex(), "n": n, "chunk": CHUNK, "numpy": np.__version__,
            "scipy": scipy.__version__, "cryptography": prov.cryptography, "edge_source": leg.edge_source,
            "repo_anchor": prov.repo_anchor, "tree_hash": prov.tree_hash, "comparison_id": inputs.comparison_id,
            "run_counter": inputs.run_counter, "plan_hash": plan.plan_hash(plan_obj)}


def _refused_report(plan_obj, ctx, refusal: plan.Refusal) -> report.OddsReport:
    """A refused report: the refusal and the context's provenance; no column, no flag, no probability."""
    return report.refusal_report(plan_obj, refusal, provenance=context_provenance(ctx))


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

- [ ] **Step 4: Run to verify it passes**

  Overlap check and the module (Git Bash form, as in Step 2):

```bash
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && .venv/Scripts/python.exe -m tests.odds_acceptance odds_pipeline/
```

  Expected: 13 PASS lines and `13/13 passed, 0 failed, 0 not run`, within 20 s. Then run each line below as its own
  command, each ending with no FAIL line (the cockpit line rewrites the tracked `qa/acceptance_results.json`; give
  it the Bash tool `timeout: 300000`, and restore the file with the last line whatever the result):

```bash
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && .venv/Scripts/python.exe -m tests.odds_acceptance odds_guards/
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && .venv/Scripts/python.exe -m tests.compliance_acceptance compliance_guards/
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && .venv/Scripts/python.exe -m tests.compliance_acceptance compliance_store/
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && .venv/Scripts/python.exe -m tests.macro_m0_harness
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && .venv/Scripts/python.exe -m tests.macro_tf_gov
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && .venv/Scripts/python.exe -m tests.macro_m7_ledger
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && .venv/Scripts/python.exe -m tests.macro_m8_forward
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && .venv/Scripts/python.exe -m tests.macro_m6_context
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && KIS_APP_KEY='<unset>' KIS_APP_SECRET='<unset>' KIS_ACCOUNT_8='<unset>' KIS_ACCOUNT_PD='<unset>' UPBIT_ACCESS_KEY='<unset>' UPBIT_SECRET_KEY='<unset>' OKX_API_KEY='<unset>' OKX_API_SECRET='<unset>' OKX_API_PASSPHRASE='<unset>' OPENDART_API_KEY='<unset>' KRX_API_KEY='<unset>' FMP_API_KEY='<unset>' ANTHROPIC_API_KEY='<unset>' GS_CLIENT_ID='<unset>' GS_CLIENT_SECRET='<unset>' FINVIZ_API_KEY='<unset>' ALPACA_API_KEY='<unset>' ALPACA_SECRET_KEY='<unset>' FXMACRODATA_API_KEY='<unset>' .venv/Scripts/python.exe tests/run_all.py --suite cockpit; echo "exit $?"; git checkout -- qa/acceptance_results.json
```

  `odds_guards/` passes with the new part (its imports are numpy, scipy, `core.compliance.{gate, model, owner}` and
  `core.odds.{bold, costs, models, plan, report}`; no clock, no file I/O, no `__main__`); `compliance_store/` keeps
  `test_code_files_is_the_import_closure` green (the closure gains no new file).

  Then add one line under "Deferred minors" of the execution ledger (untracked, LF):
  `contract 3.2: Task 13 adds CAL_SHA, calendar_signed(sha), spy(target, name), owner_with(**changes),
  fresh_series(...), weekdays(start, horizon_days), pipeline_inputs(plan_obj, series_obj, **changes) and
  pipeline(...) to tests/odds_fixtures.py (Tasks 14 and 17 call them by name).` `git status --short` then shows only
  the three files of this task and the untracked execution ledger.

- [ ] **Step 5: Commit**

```bash
git add core/odds/simulate.py tests/odds_fixtures.py tests/odds_pipeline.py
git diff --cached --stat
git diff --cached --stat --ignore-cr-at-eol
git commit -m "feat(odds): simulate pipeline with Q24 refusals and the headline column" -m "precheck and simulate through step 7: every refusal in order, the headline no-edge column at base and 2x costs, rule dates, the OKX cap and the provenance keys; replay and GARCH-t headlines refused until Tasks 17 and 14." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

  The two `--stat` outputs must be identical (3 files changed, LF only).
