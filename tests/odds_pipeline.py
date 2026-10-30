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
    """Q24, O10: one fixture per refusal, in the reporting order (CARD_NOT_REPRODUCED has its own test below,
    MODEL_CHECK_FAILED its own in tests/odds_columns.py since Task 14), plus two that break two steps at once and
    report the earlier: stale data under an unsigned calendar (step 6 before 7) and a KRX GARCH-t leg on a KRW 1 share
    (11 before 12). Each is a refused report with no column, no flag and no probability, rendering its sentence.
    screen() is reached only by the SCREEN_BLOCKED case, with a positive float stake (O11)."""
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


def test_a_crypto_plan_gets_its_headline_column_at_base_and_2x_costs():
    """Contract 8.5 step 7: the headline no-edge column at base and 2x costs on one seed (Q34), W0 = the stake and the
    owner's floor and daily loss (O11), open and close checks (Q22), no band, l_min = the floor under floor-protected
    sizing and 0 under stop-based sizing (Q32), and every provenance key; the card renders."""
    series_obj = OF.fresh_series()
    stop_leg = dataclasses.replace(UPBIT, bracket=P.Bracket(take_profit=0.5, stop=0.2), sizing="stop_based")
    with OF.chunk(), OF.members("bootstrap"), OF.spy(simulate, "run_column") as runs:
        rep = OF.pipeline(series_obj=series_obj)
        stop = OF.pipeline(OF.plan(leg=stop_leg), series_obj=series_obj)
    assert rep.refused is None and stop.refused is None, (rep.refused, stop.refused)
    base, stress, *delisted = rep.columns                  # Task 14: a coin leg adds its delisting pair
    assert [c.key for c in delisted] == ["delist_30", "delist_100"]
    assert (base.key, stress.key, rep.headline) == ("no_edge/bootstrap/base", "no_edge/bootstrap/stress2x",
                                                     "no_edge/bootstrap/base")
    assert (base.member, base.scenario, stress.scenario, base.n, stress.n, rep.n) == (
        "bootstrap", "base", "stress2x", 2_000, 2_000, 2_000)
    assert stress.mean_cost > base.mean_cost > 0.0
    assert (rep.spread, rep.spread_kind, rep.notes, rep.hidden.status) == (None, "none", (), "pass")   # Task 14
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
    with OF.chunk(), OF.members("bootstrap"):
        default = OF.pipeline()
        twice = OF.pipeline(n_paths=4_000)
        simulate.DEFAULT_PATHS = {"moonshot": 4_000, "compounding": 2_000}
        moonshot = OF.pipeline(OF.plan(track="moonshot"))
        compounding = OF.pipeline()
    assert [c.n for c in default.columns] == [2_000] * 4 and default.n == 2_000    # Task 14: + the delisting pair
    assert [c.n for c in twice.columns] == [4_000] * 4 and twice.n == 4_000
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
    assert len(days) == 6 and [run[1]["key"] for run in runs] == [     # Task 14: three members, delisting pair
        f"no_edge/{m}/{s}" for m in ("bootstrap", "bootstrap_half", "bootstrap_double") for s in ("base", "stress2x")
    ] + ["delist_30", "delist_100"]
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
    with OF.chunk(), OF.members("bootstrap"), OF.spy(gate, "screen") as screens, \
            OF.spy(simulate, "run_column") as runs:
        rep = OF.pipeline(OF.plan(leg=OKX), series_obj=_okx_series())
    (args, _, screening), = screens
    assert screening.decision.verdict == model.ACK_REQUIRED and screening.allowed
    assert type(args[2]) is float and 0.0 < args[2] <= 4_200.0, args[2]
    assert rep.refused is None, rep.refused
    assert [run[0][0].cap_krw for run in runs] == [4_200.0] * 4         # Task 14: + the delisting pair
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
    with OF.chunk(), OF.members("bootstrap"), OF.spy(simulate, "run_column") as runs:
        long_ = OF.pipeline(OF.plan(horizon_days=60))
        short = OF.pipeline(OF.plan())
    dates = [(run[0][0].stop_entries_from, run[0][0].force_exit_from) for run in runs]
    assert dates == [(dt.date(2026, 11, 22), None)] * 4 + [(None, None)] * 4, dates     # 4 columns a plan
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
    with OF.chunk(), OF.members("bootstrap"), OF.spy(simulate, "run_column") as runs:
        long_ = OF.pipeline(OF.plan(leg=OKX, horizon_days=60), series_obj=series_obj)
        short = OF.pipeline(OF.plan(leg=OKX, horizon_days=41), series_obj=series_obj)
    long_spec, short_spec = runs[0][0][0], runs[4][0][0]        # Task 14: 4 columns a plan
    assert (long_spec.stop_entries_from, long_spec.force_exit_from) == (dt.date(2026, 11, 22), dt.date(2026, 12, 3))
    assert (short_spec.stop_entries_from, short_spec.force_exit_from) == (dt.date(2026, 11, 22), None)
    last = len(short_spec.checks.seoul) - 1
    assert short_spec.checks.seoul[last] == long_spec.checks.seoul[last] == dt.date(2026, 12, 3)
    assert runs[0][1]["seed"] == runs[4][1]["seed"]
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
    with OF.chunk(), OF.members("bootstrap"), OF.spy(simulate, "run_column") as runs:
        a = OF.pipeline(OF.plan(name="first"), ctx, series_obj)
        b = OF.pipeline(OF.plan(name="second"), ctx, series_obj)
        c = OF.pipeline(OF.plan(stake_krw=84_000.0), ctx, series_obj)
        d = OF.pipeline(OF.plan(), ctx, series_obj, comparison_id="c000002")
        one = OF.pipeline(OF.plan(leg=(UPBIT,)), ctx, series_obj)
    seeds = [run[1]["seed"] for run in runs]
    assert len(seeds) == 20 and len(set(seeds[:12])) == 1 and len(set(seeds[12:16])) == 1   # 4 columns a plan
    assert seeds[12] != seeds[0] and set(seeds[16:]) == {seeds[0]}
    assert a.plan_hash == b.plan_hash == one.plan_hash and _strip(a) == _strip(b) == _strip(one)
    for col_a, col_c in zip(a.columns, c.columns):
        for name in ("median", "p5"):
            x, y = getattr(col_c, name), 2.0 * getattr(col_a, name)
            assert abs(x - y) <= 2.0, (col_a.key, name, x, y)
    assert _strip(d) != _strip(a)


def test_simulate_is_pure_after_a_warm_up():
    """Q42: after one warm-up run (every lazy import loaded), a crypto run with open, io.open, os.open, socket
    connect and time.time patched to raise gives the same report; the GARCH-t member's fit, its pilot checks
    (scipy's quad) and its draws run inside the traps too (Task 14)."""
    def trap(*args, **kwargs):
        raise AssertionError("simulate reached a file, a socket or the clock")
    plan_obj, series_obj, ctx = OF.plan(), OF.garch_series(), OF.odds_ctx()
    inputs = OF.pipeline_inputs(plan_obj, series_obj)
    with OF.chunk(), OF.pilots(), OF.members("bootstrap", "garch_t"):
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
    assert first.refused is None and dict(first.provenance)["members"] == ("bootstrap", "garch_t")
    assert _strip(again) == _strip(first)
    assert report.render(again) == report.render(first)
