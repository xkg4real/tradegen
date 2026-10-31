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

    # P4: a reachable pilot cannot justify a baseline with no observed wins.
    reachable = dataclasses.replace(leg, bracket=BRACKET)
    real = simulate.run_column

    def no_wins(*args, **kwargs):
        col = real(*args, **kwargs)
        if kwargs["key"] == "no_edge/bootstrap/base":
            col = dataclasses.replace(col, wins=0, losses=col.wins + col.losses)
            assert col.losses > 0
        return col

    with OF.chunk(), OF.pilots(), OF.members("bootstrap"):
        simulate.run_column = no_wins
        try:
            zero = OF.pipeline(OF.plan(leg=reachable), series_obj=OF.fresh_series(vol=0.04, open_gap=0.04))
        finally:
            simulate.run_column = real
    assert zero.refused is not None and zero.refused.code == "ASSUMED_EDGE_UNREACHABLE", zero.refused
    assert zero.columns == () and zero.assumed is None
    assert _no_probability(report.render(zero).replace("(55%)", ""))


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
