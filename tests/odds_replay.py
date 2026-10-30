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
    for field, reason in (("oos_pnl", "pnl_md5"), ("oos_turnover", "turnover_md5")):
        values = (10**400,) + getattr(rep, field)[1:]
        assert models.verify_replay(dataclasses.replace(rep, **{field: values})) == reason


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

            assert math.isnan(col.x_range)  # O3-18/P5: range metadata belongs to the report caller


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
        assert math.isnan(_out.x_range)  # only the caller adds range metadata (O3-18/P5)
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
