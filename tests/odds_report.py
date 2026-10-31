"""Odds plan Task 12: the report (spec 7.5; contract section 10; O14; R2-4, R2-7; Q14, Q32, Q37, Q43, Q44, Q46).

Every report here is built by hand from ColumnStats, so no path is simulated: the statistics, the number formats,
the flags, the render order, the language guard and the refusal cards are tested on exact inputs."""
from __future__ import annotations

import dataclasses
import hashlib
import json
import math
import re
from datetime import date
from types import MappingProxyType

import numpy as np
import scipy
from scipy import stats

from core.odds import bold, costs, plan
from core.odds import report as R

W0, T, L = 42_000.0, 42_000_000.0, 21_000.0
CEIL = (W0 - L) / (T - L)                 # bold.ceiling under floor-protected sizing: 1 in 1,999
STOP_CEIL = W0 / T                        # L_min = 0 under stop-based sizing: 1 in 1,000
N = 20_000
_PROB = re.compile(r"1 in |below about|\d\s?%")
_ZERO = re.compile(r"(?<![\d.,])0(?:\.0+)?%|\b1 in 0\b|\babout 0\b")
_CATALOGUE_SHA256 = "61653f4c829c46bede0996726c64dd2c8320c65c81ce9d723a9053d26f630e98"
_REPLAY = {"y0": 2019.0, "y1": 2026.0, "cut": 1.0 - 0.60, "bench_sr": 0.788830441182887,
           "haircut_sr": 0.7296150117404476, "diff": 0.4271945783845257, "ci_lo": 0.03344352887529298,
           "ci_hi": 0.8346050647267628, "fstar": 1.0, "h": 29.0, "growth": 0.02889, "growth_iid": 0.02613}
_ASSUMED = {"w": 0.55, "p0": 0.4987, "u": 0.0213, "nb": 617.0, "resolved": 5_000.0, "theta": 0.21}
_REFUSALS = (
    ("PARTIAL_CHUNK", "", {"chunk": "200,000"}),
    *(("UNSUPPORTED_PRODUCT", sub, {}) for sub in (
        "venue", "feed", "symbol", "class", "multiple", "tax", "horizon", "start", "track", "numbers", "model",
        "sizing", "fraction", "bracket", "edge", "replay", "file", "comparison")),
    ("MULTI_LEG_UNSUPPORTED", "", {}), ("STATE_UNUSABLE", "", {}), ("STATE_UNUSABLE", "code", {}),
    ("LIMITS_UNSET", "", {}), ("LIMITS_UNSET", "cap", {}), ("CALENDAR_UNSIGNED", "", {}),
    ("CALENDAR_COVERAGE", "", {}),
    *(("DATA_INVALID", sub, {"days": "3"} if sub == "stale" else {}) for sub in (
        "now", "series", "sessions", "empty", "stale")),
    ("SYNTHETIC_REFUSED", "", {}), ("NOT_TRADABLE", "", {"venue": "upbit", "symbol": "BTC"}),
    ("SPECIAL_REGIME", "", {"symbol": "005930"}), ("SHORT_HISTORY", "", {"symbol": "KRW-BTC"}),
    ("CARD_NOT_REPRODUCED", "", {}), ("MODEL_NOT_FOR_LIMITED_VENUE", "", {}), ("COST_DOMINATED", "", {}),
    ("STUCK_AT_START", "", {}),
    *(("SCREEN_BLOCKED", sub, {"row": "KR-OKX-SPOT"} if sub == "row" else {}) for sub in (
        "row", "unsigned", "other")),
    ("ASSUMED_EDGE_UNREACHABLE", "", {"w": "55.0%"}),
    *(("MODEL_CHECK_FAILED", check, {}) for check in ("deterministic", "statistical", "fit")),
    ("MODEL_CHECK_FAILED", "", {"check": "refit"}),
)


def _col(**changes) -> R.ColumnStats:
    """A moonshot no-edge base column of N paths: 4 first passages, three quarters at the floor."""
    fields = dict(key="no_edge/bootstrap/base", member="bootstrap", scenario="base", n=N, reached=4,
                  reached_outcome=4, ended_at_or_above=3, at_floor=15_000, running=4_996, locked_at_horizon=0,
                  rungs=(900, 400, 120, 20, 3), median=21_000.0, p5=21_000.0, mean=41_950.0, mean_se=60.0,
                  mean_cost=50.0, g_se=60.0, kept_lo=21_000.0, kept_hi=21_420.0, x_mean=0.5, x_var=4.0e6,
                  x_range=6.0e6, wins=0, losses=0, unresolved=0, band_edge_share=0.0, band_edge_sessions=0,
                  worst_gap=0.0, trades=N)
    fields.update(changes)
    return R.ColumnStats(**fields)


def _series(proxy_dates=None) -> plan.Series:
    return plan.Series(symbol="KRW-BTC", source="UPBIT", dates=("2026-10-22",), open=(1.0,), close=(1.0,),
                       adjustment="none", status="FINAL", md5="0" * 32, proxy_dates=proxy_dates)


def _prov(**changes) -> dict:
    """Every provenance key of contract 10.1, with labels that hold underscores where the real ones do."""
    prov = {"rules_sha": "1" * 64, "instruments_sha": "2" * 64, "venues_sha": "3" * 64, "state_hash": "4" * 64,
            "owner_seq": 7, "owner_row": "5" * 64, "code_hash": "6" * 64, "code_signed": True,
            "fingerprint": "SHA256:" + "7" * 64, "decision_id": "8" * 64, "screening_hash": "9" * 64,
            "series_md5": "a" * 32, "components": (("upbit_daily KRW-BTC", "b" * 32),), "proxy_dates": None,
            "calendar_sha": "", "calendar_version": "", "calendar_md5s": (), "model": "bootstrap",
            "members": ("bootstrap", "bootstrap_half", "bootstrap_double"), "seed_hex": "c" * 64, "n": N,
            "chunk": 2_000, "numpy": np.__version__, "scipy": scipy.__version__, "cryptography": "49.0.0",
            "edge_source": "none", "repo_anchor": "git:" + "d" * 40, "tree_hash": "e" * 64,
            "comparison_id": "c000001", "run_counter": 1, "plan_hash": "ab" * 32}
    prov.update(changes)
    return prov


def _flags(col: R.ColumnStats, **changes) -> tuple:
    fields = dict(headline=col, no_edge=(col,), engine="bootstrap",
                  hidden=R.hidden_edge(col, w0=W0, target=T, l_min=L), ceiling=CEIL, structural=None, target=T,
                  stake=W0, reference=None, rule_flags=(), grey=(), series=_series(), okx=False)
    fields.update(changes)
    return R.flags_for(**fields)


def _rep(*cols: R.ColumnStats, **changes) -> R.OddsReport:
    """A floor-protected moonshot upbit card built by report.build; the flags follow the headline unless given."""
    cols = cols or (_col(), _col(key="no_edge/bootstrap/stress2x", scenario="stress2x", mean=41_900.0,
                                 mean_cost=100.0))
    head = cols[0]
    fields = dict(plan_hash="ab" * 32, plan_index=1, plan_count=2, refused=None, track="moonshot", stake=W0,
                  target=T, floor=L, l_min=L, horizon_days=30, n=head.n, sizing="floor_safe",
                  model_key="model.bootstrap",
                  model_slots={"symbol": "KRW-BTC", "first": "2016-10-24", "last": "2026-10-22", "rows": "3,650"},
                  columns=cols, headline=head.key, spread=(1.0e-5, 6.0e-4), spread_kind="other", notes=(),
                  ceiling=CEIL, structural_cap=None, structural_sessions=None, tax_basis="crypto_22pct_from_2027",
                  cost_words_key="cost.fees", hidden=R.hidden_edge(head, w0=W0, target=T, l_min=L),
                  flags=_flags(head), assumed=None, replay=None, comparison=(2, 1, 3), provenance=_prov())
    fields.update(changes)
    return R.build(**fields)


def _impossible_rep(cap: float = 95.0595, sessions: int = 16) -> R.OddsReport:
    col = _col(reached=0, reached_outcome=0, ended_at_or_above=0, rungs=(900, 400, 120, 20, 0))
    return _rep(col, structural_cap=cap, structural_sessions=sessions, flags=_flags(col, structural=(cap, sessions)),
                tax_basis="krx_small_holder_exempt", cost_words_key="cost.tax", spread_kind="krx",
                model_slots={"symbol": "069500", "first": "2016-10-24", "last": "2026-10-23", "rows": "2,450"})


def _idle_rep() -> R.OddsReport:
    idle = _col(trades=0, reached=0, reached_outcome=0, ended_at_or_above=0, rungs=(0, 0, 0, 0, 0), at_floor=0,
                running=N, median=W0, p5=W0, mean=W0, mean_cost=0.0, kept_lo=None, kept_hi=None)
    return _rep(idle)


def _assumed_rep(sizing: str = "floor_safe", **assumed) -> R.OddsReport:
    head, edge = _col(), _col(key="assumed", mean=40_000.0, x_range=math.nan)
    if sizing == "floor_safe":
        return _rep(head, edge, assumed={**_ASSUMED, **assumed})
    return _rep(head, edge, assumed={**_ASSUMED, **assumed}, sizing="stop_based", l_min=0.0, ceiling=STOP_CEIL,
                flags=_flags(head, ceiling=STOP_CEIL))


def _replay_rep(**replay) -> R.OddsReport:
    base = _col(key="replay_no_edge/base", member="replay",
                x_range=R.replay_range(target=T, a_max=0.16899731, c_max=0.001, n_checks=30))
    stress = _col(key="replay_no_edge/stress2x", member="replay", scenario="stress2x", mean=41_900.0,
                  mean_cost=100.0)
    tested = _col(key="tested_replay/base", member="replay", mean=44_100.0, x_range=math.nan)
    hidden = R.hidden_edge(base, w0=W0, target=T, l_min=L)
    return _rep(base, stress, tested, model_key="model.replay",
                model_slots={"first": "2019-10-23", "last": "2026-09-25", "rows": "2,530", "block": "10"},
                spread=None, spread_kind="none", hidden=hidden,
                flags=_flags(base, no_edge=(base, stress), engine="replay", hidden=hidden),
                replay={**_REPLAY, **replay}, provenance=_prov(model="replay", members=(),
                                                               edge_source=plan.REPLAY_SOURCE))


def _okx_rep() -> R.OddsReport:
    col = _col(band_edge_sessions=12, band_edge_share=0.0123, worst_gap=0.0456, locked_at_horizon=40,
               mean_cost=4_200.0, mean=37_800.0)
    rule = ((date(2026, 11, 22), "review_by", "KR-OKX-SPOT"), (date(2026, 12, 3), "auto_off", "KR-OKX-SPOT"),
            (date(2026, 12, 5), "effective_until", "KR-OKX-SPOT"))
    flags = _flags(col, reference=1e-6, rule_flags=rule, grey=(("KR-OKX-SPOT", "10.0%", "2026-12-03"),),
                   series=_series(("2021-01-01", "2021-03-04")), okx=True)
    return _rep(col, flags=flags, model_slots={"symbol": "BTC-USDT", "first": "2016-10-24", "last": "2026-10-22",
                                               "rows": "3,650", "cap": "10.0%", "capkrw": "4,200"})


def _refused(code: str, sub: str = "", slots=None, plan_obj=None) -> R.OddsReport:
    return R.refusal_report(plan_obj, plan.Refusal(code=code, sub=sub, slots=slots or {}, detail="internal detail_x"),
                            provenance=_prov())


def _fixture_reports() -> list[R.OddsReport]:
    return [_rep(), _rep(track="compounding"), _rep(horizon_days=10), _impossible_rep(), _idle_rep(),
            _assumed_rep(), _assumed_rep("stop_based"), _replay_rep(), _replay_rep(fstar=math.nan), _okx_rep(),
            _rep(_col(n=10**6, reached=0, reached_outcome=0, ended_at_or_above=0, rungs=(9, 8, 7, 6, 0),
                      at_floor=750_000, running=250_000)),
            _refused("SCREEN_BLOCKED", "row", {"row": "KR-OKX-SPOT"}), _refused("STATE_UNUSABLE", "code")]


def _printed(text: str) -> float:
    """The probability a printed interval end states."""
    if text.startswith("1 in "):
        return 1.0 / float(text[5:].replace(",", ""))
    assert text.endswith("%"), text
    return float(text[:-1]) / 100.0


def _raises(call, exc=ValueError) -> str:
    try:
        call()
    except exc as e:
        return str(e)
    raise AssertionError(f"expected {exc.__name__}")


# --------------------------------------------------------------------------- #
# Types and constants
# --------------------------------------------------------------------------- #
def test_column_stats_fields_are_the_contract_list():
    names = [f.name for f in dataclasses.fields(R.ColumnStats)]
    assert names == ["key", "member", "scenario", "n", "reached", "reached_outcome", "ended_at_or_above",
                     "at_floor", "running", "locked_at_horizon", "rungs", "median", "p5", "mean", "mean_se",
                     "mean_cost", "g_se", "kept_lo", "kept_hi", "x_mean", "x_var", "x_range", "wins", "losses",
                     "unresolved", "brackets", "band_edge_share", "band_edge_sessions", "worst_gap", "trades"], names
    brackets = next(f for f in dataclasses.fields(R.ColumnStats) if f.name == "brackets")
    assert brackets.default is None and brackets.compare is False and brackets.repr is False
    with_arrays = _col(brackets=(np.zeros(3), np.ones(3)))
    assert with_arrays == _col() and dataclasses.replace(with_arrays, brackets=None) == _col()


def test_report_types_and_constants_are_the_contract_ones():
    assert [f.name for f in dataclasses.fields(R.HiddenEdge)] == ["status", "mean", "bound", "range_", "n"]
    assert [f.name for f in dataclasses.fields(R.Flag)] == ["code", "level", "key", "slots"]
    assert [f.name for f in dataclasses.fields(R.OddsReport)] == [
        "plan_hash", "plan_index", "plan_count", "refused", "track", "stake", "target", "floor", "l_min",
        "horizon_days", "n", "sizing", "model_key", "model_slots", "columns", "headline", "spread", "spread_kind",
        "notes", "ceiling", "structural_cap", "structural_sessions", "tax_basis", "cost_words_key", "hidden",
        "flags", "assumed", "replay", "comparison", "provenance"]
    assert (R.CP_LEVEL, R.DELTA, R.RED_ALPHA) == (0.95, 1e-4, 0.001)
    assert R.CARRY == costs.LIMIT_DOWN_CARRY_COST_MULTIPLIER == 2.0
    assert R.LADDER == (1.10, 1.25, 2.0, 10.0) and R.COST_DOMINATED_SHARE == 0.10
    assert R.BANNED_WORDS == ("best", "optimal", "recommended", "safe", "guaranteed", "sure", "ideal", "risk-free",
                              "low-risk", "proven", "should")
    assert R.BANNED_PHRASES == ("worth trying", "good chance", "likely to reach")


# --------------------------------------------------------------------------- #
# Statistics
# --------------------------------------------------------------------------- #
def test_clopper_pearson_at_zero_and_at_63():
    lo, hi = R.cp_two_sided(0, 10**6)
    assert lo == 0.0 and abs(hi - 2.9957277863525433e-06) < 1e-18, hi
    assert abs(hi - (1.0 - 0.05 ** (1.0 / 10**6))) < 1e-12
    assert R.fmt_prob(0, 10**6) == "below about 3 in 1,000,000"
    none = _col(n=10**6, reached=0, reached_outcome=0, ended_at_or_above=0, rungs=(9, 8, 7, 6, 0), at_floor=750_000,
                running=250_000)
    text = R.render(_rep(none))
    assert "this plan never reached KRW 42,000,000 before income tax (below resolution: under about 3 in 1,000,000;" \
        in text
    lo, hi = R.cp_two_sided(63, 10**6)
    assert abs(lo - 4.8411e-05) < 1e-9 and abs(hi - 8.0604e-05) < 1e-9, (lo, hi)
    lo, hi = R.cp_two_sided(5, 5)
    assert math.isclose(lo, float(stats.beta.ppf(0.025, 5, 1)), rel_tol=1e-12) and hi == 1.0
    _raises(lambda: R.cp_two_sided(3, 2))


def test_clopper_pearson_matches_scipy_binomtest():
    for n in (1, 7, 2_000, 200_000):
        for k in sorted(k for k in {1, 2, 3, n // 2, n - 1, n} if 1 <= k <= n):
            ci = stats.binomtest(k, n).proportion_ci(confidence_level=0.95, method="exact")
            lo, hi = R.cp_two_sided(k, n)
            assert math.isclose(lo, ci.low, rel_tol=1e-9, abs_tol=1e-15), (k, n, lo, ci.low)
            assert math.isclose(hi, ci.high, rel_tol=1e-9, abs_tol=1e-15), (k, n, hi, ci.high)


def test_cp_lower_is_the_one_sided_bound():
    assert R.cp_lower(0, 100, 0.95) == 0.0
    for k, n, level in ((1, 100, 0.95), (63, 10**6, 0.95), (63, 10**6, 1.0 - 0.001 / 6)):
        assert R.cp_lower(k, n, level) == float(stats.beta.ppf(1.0 - level, k, n - k + 1))
    assert R.cp_lower(63, 10**6, 1.0 - 0.001 / 6) < R.cp_two_sided(63, 10**6)[0] < R.cp_lower(63, 10**6, 0.95)


def test_bernstein_hand_values():
    assert abs(R.bernstein(1.0, 10.0, 10**6, 1e-4) - 0.004850869883696696) < 1e-15
    assert abs(R.bernstein(0.25, 1.0, 2_000, 0.05) - 0.038213360783937035) < 1e-15
    assert R.bernstein(1.0, 10.0, 10**6) == R.bernstein(1.0, 10.0, 10**6, R.DELTA)


def test_bernstein_false_alarm_rate_at_delta_005_is_at_most_005():
    """2,000 replications of a bounded, skewed, mean-zero X (range 10), each judged by hidden_edge itself at
    delta_test 0.05 (report.DELTA swapped and restored): the alarm rate's upper bound <= 0.05."""
    rng = np.random.default_rng(20261024)
    reps, n = 2_000, 1_000
    x = np.where(rng.random((reps, n)) < 0.1, 9.0, -1.0)
    cols = [_col(n=n, x_mean=float(m), x_var=float(v), x_range=10.0)
            for m, v in zip(x.mean(axis=1), x.var(axis=1, ddof=1))]
    saved = R.DELTA
    try:
        R.DELTA = 0.05
        verdicts = [R.hidden_edge(col, w0=W0, target=T, l_min=L) for col in cols]
    finally:
        R.DELTA = saved
    assert verdicts[0].bound == R.bernstein(cols[0].x_var, 10.0, n, delta=0.05)
    assert R.hidden_edge(cols[0], w0=W0, target=T, l_min=L).bound == R.bernstein(cols[0].x_var, 10.0, n)
    alarms = sum(v.status != "pass" for v in verdicts)
    assert R.cp_two_sided(alarms, reps)[1] <= 0.05, alarms


def test_a_planted_edge_of_twice_the_bound_is_red_with_both_wordings():
    rng = np.random.default_rng(7)
    x = np.where(rng.random(200_000) < 0.1, 9.0, -1.0)
    v, n = float(x.var(ddof=1)), int(x.size)
    b = R.bernstein(v, 10.0, n)
    clean = _col(n=n, x_mean=float(x.mean()), x_var=v, x_range=10.0)
    assert R.hidden_edge(clean, w0=W0, target=T, l_min=L).status == "pass"
    for shift, status, key, words in ((2.0 * b, "red_gain", "hidden.gain", "makes money without any edge"),
                                      (-2.0 * b, "red_loss", "hidden.loss", "loses more than its costs explain")):
        col = _col(n=n, x_mean=float(x.mean()) + shift, x_var=v, x_range=10.0)
        hidden = R.hidden_edge(col, w0=W0, target=T, l_min=L)
        assert hidden.status == status and hidden.bound == b and hidden.n == n, hidden
        flags = _flags(col, hidden=hidden)
        assert (flags[0].code, flags[0].level, flags[0].key) == ("HIDDEN_EDGE", "red", key), flags[0]
        text = R.render(_rep(col, hidden=hidden, flags=flags))
        assert f"BUG CHECK FAILED: this plan {words}" in text and "Do not use these numbers." in text


# --------------------------------------------------------------------------- #
# HIDDEN_EDGE range and wording
# --------------------------------------------------------------------------- #
def test_hidden_range_hand_value_carries_phi_sell_in_the_numerator():
    # k_x = 2 x 0.01; V_max = (1,000 + 2 x 5) / 0.98 x e^0.1; C_max = k_x V_max + 2 x max(3, 5); R = V_max + 10 C_max
    r = R.hidden_range(target=1_000.0, phi_buy=3.0, phi_sell=5.0, kappa_bound=0.01, m_max=0.1, n_checks=10)
    assert math.isclose(r, 1466.803217048658, rel_tol=1e-12), r
    one = R.hidden_range(target=1_000.0, phi_buy=3.0, phi_sell=5.0, kappa_bound=0.01, m_max=0.1, n_checks=10,
                         carry=1.0)
    assert math.isclose(one, 1284.1075251844732, rel_tol=1e-12), one
    assert math.isclose(R.replay_range(target=T, a_max=0.16899731, c_max=0.001, n_checks=30), 50570823.6306,
                        rel_tol=1e-12)


def test_hidden_range_is_unbounded_at_k_x_one_and_says_so():
    just = R.hidden_range(target=T, phi_buy=0.0, phi_sell=0.0, kappa_bound=0.4999, m_max=0.05, n_checks=60)
    assert math.isfinite(just) and just > T
    assert R.hidden_range(target=T, phi_buy=0.0, phi_sell=0.0, kappa_bound=0.5, m_max=0.05, n_checks=60) == math.inf
    col = _col(x_range=math.inf)
    hidden = R.hidden_edge(col, w0=W0, target=T, l_min=L)
    assert hidden.status == "unbounded" and hidden.bound == math.inf
    flags = _flags(col, hidden=hidden)
    assert [(f.level, f.key) for f in flags if f.code == "HIDDEN_EDGE"] == [("info", "hidden.unbounded")]
    text = R.render(_rep(col, hidden=hidden, flags=flags))
    assert "The bug check is unavailable for this plan (no finite range):" in text
    assert "the bug checks are coarser than these ranges" in text


def test_hidden_edge_is_unavailable_for_garch_and_does_not_apply_to_edge_columns():
    garch = _col(key="no_edge/garch_t/base", member="garch_t", x_range=math.nan)
    hidden = R.hidden_edge(garch, w0=W0, target=T, l_min=L)
    assert hidden.status == "unavailable" and math.isnan(hidden.bound)
    flags = _flags(garch, hidden=hidden, engine="garch")
    assert [f.code for f in flags if f.code.startswith("CHECKS") or f.code.startswith("CLOSE")] == \
        ["CLOSE_ONLY_CHECKS"]
    text = R.render(_rep(garch, hidden=hidden, flags=flags, model_key="model.garch"))
    assert "The bug check is unavailable for GARCH-t: a bounded shock does not bound the volatility" in text
    assert "Model: GARCH-t fitted to the daily won returns of KRW-BTC" in text
    loud = dict(x_mean=1e9, x_var=1.0, x_range=10.0)                     # red on any no-edge column
    assert R.hidden_edge(_col(**loud), w0=W0, target=T, l_min=L).status == "red_gain"
    for key in ("assumed", "tested_replay/base"):
        assert R.hidden_edge(_col(key=key, **loud), w0=W0, target=T, l_min=L).status == "not_applicable"
    assert R.render(_assumed_rep()).count("The bug check does not apply to edge columns.") == 1
    assert R.render(_replay_rep()).count("The bug check does not apply to edge columns.") == 1
    _raises(lambda: R.hidden_edge(_col(), w0=W0, target=L, l_min=L))


def test_the_pass_sentence_prints_the_blind_spot_rounded_down_and_the_model_disclaimer():
    hidden = R.HiddenEdge(status="pass", mean=0.0, bound=8_000.3, range_=1.0e9, n=N)
    flags = _flags(_col(), hidden=hidden)
    flag = next(f for f in flags if f.code == "HIDDEN_EDGE")
    assert (flag.level, flag.key) == ("info", "hidden.pass")
    assert dict(flag.slots) == {"b": "8,000", "pct": "19.1%", "m": "1 in 5,247"}, dict(flag.slots)
    assert R.fmt_blind(8_000.3 / 41_979_000.0) == "1 in 5,247" and R.fmt_blind(0.0234) == "2.4 percentage points"
    text = R.render(_rep(hidden=hidden, flags=flags))
    assert "raised the chance of the target by up to 1 in 5,247. It does not test whether the model itself is right." \
        in text and "5,248" not in text
    coarse = R.HiddenEdge(status="pass", mean=0.0, bound=5.0e7, range_=1.0e12, n=N)
    flags = _flags(_col(), hidden=coarse)
    assert [f.key for f in flags if f.code == "HIDDEN_EDGE"] == ["hidden.coarse"]
    text = R.render(_rep(hidden=coarse, flags=flags))
    assert "is too coarse to say anything about the chance of the target. It does not test whether the model" in text
    edge = R.HiddenEdge(status="pass", mean=0.0, bound=41_979_000.0, range_=1.0e12, n=N)     # b == T - L_min exactly
    assert [f.key for f in _flags(_col(), hidden=edge) if f.code == "HIDDEN_EDGE"] == ["hidden.coarse"]


# --------------------------------------------------------------------------- #
# Number formats
# --------------------------------------------------------------------------- #
def test_fmt_end_never_narrows_the_clopper_pearson_interval():
    formats = set()
    for n in (20_000, 200_000, 1_000_000):
        for k in range(1, 1_001):
            lo, hi = R.cp_two_sided(k, n)
            low, high = R.fmt_end(lo, upper=False), R.fmt_end(hi, upper=True)
            assert _printed(low) <= lo and _printed(high) >= hi, (k, n, low, high, lo, hi)
            formats |= {low.endswith("%"), high.endswith("%")}
    assert formats == {True, False}
    lo, hi = R.cp_two_sided(4_700, 200_000)
    assert (R.fmt_end(lo, upper=False), R.fmt_end(hi, upper=True)) == ("2.2%", "2.5%")
    _raises(lambda: R.fmt_end(0.0, upper=False))


def test_k63_renders_the_spec_example():
    assert R.fmt_prob(63, 10**6) == "about 1 in 16,000"
    col = _col(n=10**6, reached=63, reached_outcome=63, ended_at_or_above=50, rungs=(9_000, 5_000, 1_000, 200, 50),
               at_floor=750_000, running=249_937)
    text = R.render(_rep(col))
    assert "this plan reached KRW 42,000,000 before income tax in 63, about 1 in 16,000 (counting noise alone: " \
        "between 1 in 12,000 and 1 in 21,000;" in text


def test_spread_ends_are_outward_and_a_k0_member_prints_below_about():
    lo2, hi9 = R.cp_two_sided(2, N)[0], R.cp_two_sided(9, N)[1]
    a, b = R.fmt_end(hi9, upper=True), R.fmt_end(lo2, upper=False)
    assert _printed(a) >= hi9 and _printed(b) <= lo2
    assert f"; other models give {a} to {b};" in R.render(_rep(spread=(lo2, hi9)))
    text = R.render(_rep(spread=(0.0, hi9), spread_kind="krx"))
    assert f"; the same model with other block lengths gives {a} to below about 3 in 20,000; no second model " \
        "family is available for KRX;" in text
    text = R.render(_rep(spread=(lo2, hi9), spread_kind="blocks",
                         notes=(("garch_t", "deterministic"), ("garch_refit", "refit"))))
    assert f"; the same model with other block lengths gives {a} to {b}; GARCH-t was left out because its " \
        "deterministic check failed; the GARCH-t refit was left out because its refit check failed;" in text
    text = R.render(_rep(spread=None, spread_kind="none", notes=(("bootstrap_half", "statistical"),)))
    assert "; no other model could be run here; the bootstrap at half the block length was left out because its " \
        "statistical check failed;" in text


def test_fmt_ceiling_is_an_upper_bound_in_both_formats():
    assert R.fmt_ceiling(0.6667) == "a 66.7% chance"
    assert R.fmt_ceiling(1.0 / 3.0) == "a 33.4% chance"
    assert R.fmt_ceiling(5.0025e-4) == "1 in 1,999"
    assert R.fmt_ceiling(CEIL) == "1 in 1,999" and R.fmt_ceiling(STOP_CEIL) == "1 in 1,000"
    assert R.fmt_ceiling(0.01) == "a 1.0% chance"
    assert R.fmt_ceiling(1.0 / 1999.6) == "1 in 1,999"           # floor, never round: 1 in 2,000 would understate it


def test_the_ceiling_prints_the_exact_one_in_n():
    """A card's "1 in N" is bold.ceiling_one_in, exact: floor(1 / c) of the float ceiling gives 104 for 1 in 105
    and 2,126 for 1 in 2,125 (a smaller chance than the bound)."""
    target = 105 * W0
    ceiling = bold.ceiling(W0, 0.0, target)
    assert R.fmt_ceiling(ceiling) == "1 in 104" and bold.ceiling_one_in(W0, 0.0, target) == 105
    for k, p in ((4, "about 1 in 5,000."), (200, "at most 1 in 105, the ceiling (the simulated 200 in 20,000 is")):
        col = _col(reached=k, reached_outcome=k)
        hidden = R.hidden_edge(col, w0=W0, target=target, l_min=0.0)
        flags = _flags(col, ceiling=ceiling, target=target, hidden=hidden)
        assert not any(f.code == "CEILING_BREACH" for f in flags), k
        text = R.render(_rep(col, sizing="stop_based", l_min=0.0, target=target, ceiling=ceiling, hidden=hidden,
                             flags=flags))
        assert "No plan without a real edge can beat 1 in 105." in text and "1 in 104" not in text
        assert f"Chance of reaching KRW 4,410,000 before income tax: {p}" in text
    target, low = 89_276_487.5, 7.3
    ceiling = bold.ceiling(W0, low, target)
    assert R.fmt_ceiling(ceiling) == "1 in 2,126" and bold.ceiling_one_in(W0, low, target) == 2_125
    hidden = R.hidden_edge(_col(), w0=W0, target=target, l_min=low)
    text = R.render(_rep(floor=low, l_min=low, target=target, ceiling=ceiling, hidden=hidden,
                         flags=_flags(_col(), ceiling=ceiling, target=target, hidden=hidden)))
    assert "No plan without a real edge that keeps this floor can beat 1 in 2,125." in text and "2,126" not in text


def test_fmt_order_keeps_the_printed_order_of_a_breach():
    assert R.fmt_order(1.0 / 1998.5, 1.0 / 1999.0) == ("1 in 1,998.5", "1 in 1,999.0")
    assert R.fmt_order(0.020001, 0.02) == ("2.01%", "2.00%")
    assert R.fmt_order(0.02, 4.2e-5) == ("1 in 50.0", "1 in 23,809.6")       # the ceiling picks the format
    rng = np.random.default_rng(3)
    for c in rng.uniform(1e-5, 0.2, 500):
        lb = float(c) * (1.0 + float(rng.uniform(1e-9, 1e-3)))
        shown_lb, shown_c = R.fmt_order(lb, float(c))
        assert _printed(shown_lb) > _printed(shown_c), (lb, c, shown_lb, shown_c)
    for lb, c in zip(rng.uniform(0.01, 0.9, 500), rng.uniform(1e-7, 0.01, 500)):    # a far target: lb >= 1% > c
        shown_lb, shown_c = R.fmt_order(float(lb), float(c))
        assert _printed(shown_lb) > _printed(shown_c) and not _ZERO.search(shown_lb + " " + shown_c), (lb, c)


def test_point_estimates_round_to_two_figures_and_never_to_zero():
    assert R._sf2(12_406.38, up=False) == 12_000 and R._sf2(20_656.35, up=True) == 21_000
    assert R._sf2(99.5, up=True) == 100 and R._sf2(99.5, up=False) == 99
    assert R.fmt_prob(1, 10**6) == "about 1 in 1,000,000" and R.fmt_prob(3, N) == "about 1 in 6,700"
    assert R.fmt_prob(4_800, 200_000) == "about 2.4%"
    assert R.fmt_prob(9_999, 10_000) == "above 99.9%" and R.fmt_prob(10_000, 10_000) == "about 100.0%"
    assert R.fmt_krw(41_950.4) == "41,950" and R.fmt_krw(np.float64(-1_234.6)) == "-1,235"
    for n in (1, 2_000, 10**6):
        for k in (0, 1, n // 2, n):
            assert not _ZERO.search(R.fmt_prob(k, n)), (k, n)
    for p in (1e-9, 0.0099, 0.01, 0.5, 1.0):
        for upper in (True, False):
            assert not _ZERO.search(R.fmt_end(p, upper=upper)), (p, upper)


def test_a_no_edge_estimate_above_the_ceiling_without_a_breach_prints_cap_p():
    col = _col(reached=12, reached_outcome=12, ended_at_or_above=11, rungs=(900, 400, 120, 20, 11))
    assert 12 / N > CEIL and R.ceiling_cells((col,), CEIL)[0] == ""        # counting noise, no breach
    text = R.render(_rep(col))
    cap = "at most 1 in 1,999, the ceiling (the simulated 12 in 20,000 is above it only through counting noise)"
    assert f"Chance of reaching KRW 42,000,000 before income tax: {cap}." in text
    assert f"before income tax in 12, {cap} (counting noise alone:" in text
    assert "your target (KRW 42,000,000): at most 1 in 1,999, the ceiling (the simulated 11 in 20,000 is above it" \
        in text
    assert "about 1 in 1,700" not in text and "about 1 in 1,800" not in text
    level = _col(reached=20, reached_outcome=20)                  # k / n equals the ceiling: not above it
    assert 20 / N == STOP_CEIL and R.ceiling_cells((level,), STOP_CEIL)[0] == ""
    text = R.render(_rep(level, sizing="stop_based", l_min=0.0, ceiling=STOP_CEIL,
                         flags=_flags(level, ceiling=STOP_CEIL)))
    assert "Chance of reaching KRW 42,000,000 before income tax: about 1 in 1,000." in text and "at most" not in text


def test_the_bug_check_clause_is_chosen_by_comparison():
    col = _col()
    lo, hi = R.cp_two_sided(col.reached_outcome, col.n)
    finer = R.HiddenEdge(status="pass", mean=0.0, bound=0.5 * (hi - lo) * (T - L), range_=1.0e9, n=N)
    coarser = R.HiddenEdge(status="pass", mean=0.0, bound=2.0 * (hi - lo) * (T - L), range_=1.0e9, n=N)
    text = R.render(_rep(col, hidden=finer, flags=_flags(col, hidden=finer)))
    assert "; the bug check's resolution is printed below, and nothing here covers the model being wrong)" in text
    for hidden in (coarser, None, R.HiddenEdge(status="unavailable", mean=0.0, bound=math.nan, range_=math.nan, n=N)):
        text = R.render(_rep(col, hidden=hidden, flags=_flags(col, hidden=hidden)))
        assert "; the bug checks are coarser than these ranges, and nothing here covers the model being wrong)" \
            in text and "resolution is printed below" not in text


# --------------------------------------------------------------------------- #
# Flags and the card
# --------------------------------------------------------------------------- #
def test_ceiling_breach_amber_and_red_with_m_cells():
    n = 200_000
    quiet = tuple(_col(n=n, reached=200, key=f"no_edge/bootstrap/base{i}") for i in range(9))
    assert R.ceiling_cells((_col(n=n, reached=230),), STOP_CEIL)[0] == "amber"
    assert R.ceiling_cells((_col(n=n, reached=250),), STOP_CEIL) == ("red", R.cp_lower(250, n, 1.0 - 0.001))
    assert R.ceiling_cells((_col(n=n, reached=250), *quiet), STOP_CEIL) == ("amber", R.cp_lower(250, n, 0.95))
    assert R.ceiling_cells((_col(n=n, reached=260), *quiet), STOP_CEIL)[0] == "red"
    assert R.ceiling_cells(quiet, STOP_CEIL) == ("", R.cp_lower(200, n, 0.95))
    assert R.ceiling_cells((), STOP_CEIL) == ("", 0.0)
    for k, level, key, text in ((230, "amber", "breach.amber", "Preliminary evidence, about 5% false-alarm rate"),
                                (250, "red", "breach.red", "Do not use these numbers: a no-edge result beats the "
                                                           "ceiling of 1 in 1,000.0 beyond counting noise")):
        col = _col(n=n, reached=k, reached_outcome=k)
        flags = _flags(col, ceiling=STOP_CEIL)
        breach = [f for f in flags if f.code == "CEILING_BREACH"]
        assert [(f.level, f.key) for f in breach] == [(level, key)], breach
        rendered = R.render(_rep(col, sizing="stop_based", l_min=0.0, ceiling=STOP_CEIL, flags=flags))
        assert text in rendered
        assert "Chance of reaching KRW 42,000,000 before income tax: about" in rendered     # no cap.p after a breach


def test_the_average_line_follows_the_two_g_se_rule():
    agrees = _col(mean=W0 - 50.0 + 1.99 * 60.0, g_se=60.0, mean_se=55.0)     # outside 2 x mean_se, inside 2 x g_se
    text = R.render(_rep(agrees))
    assert "Averaged over all simulated months: about KRW 41,950 (fees average KRW 50; the simulation's own " \
        "average, KRW 42,069 ± 55, agrees). That average includes rare jackpots and is not what usually " \
        "happens." in text
    differs = _col(mean=W0 - 50.0 + 2.01 * 60.0, g_se=60.0, mean_se=55.0)
    text = R.render(_rep(differs))
    assert "The simulation's own average, KRW 42,071 ± 55, does not match your stake minus the average fees " \
        "(KRW 41,950); see the bug check below." in text
    assert "an average gain of KRW 2,100, only if the edge in this column is real." in R.render(_replay_rep())
    assert "an average loss of KRW 2,000, even with the edge in this column." in R.render(_assumed_rep())


def test_typical_result_first_and_red_flags_before_any_number():
    n = 200_000
    col = _col(n=n, reached=250, reached_outcome=250, x_mean=1.0e6)
    hidden = R.hidden_edge(col, w0=W0, target=T, l_min=0.0)
    assert hidden.status == "red_gain"
    flags = _flags(col, ceiling=STOP_CEIL, hidden=hidden)
    lines = R.render(_rep(col, sizing="stop_based", l_min=0.0, ceiling=STOP_CEIL, hidden=hidden,
                          flags=flags)).splitlines()
    assert lines[0] == "Plan 1 of 2 (abababababababab)"
    assert lines[1].startswith("BUG CHECK FAILED: this plan makes money without any edge")
    assert lines[2].startswith("Do not use these numbers: a no-edge result beats the ceiling")
    assert lines[3].startswith("Model: a two-point bootstrap") and lines[4].startswith("Stop-based sizing")

    def at(prefix: str) -> int:
        return next(i for i, line in enumerate(lines) if line.startswith(prefix))
    order = [at("The middle month ends with"), at("In about 7.5% of months you end at your floor"),
             at("Averaged over all simulated months: about"), at("Chance of reaching"),
             at("Chance of ending at your floor"), at("Ended at or above:"), at("In 200,000 made-up months"),
             at("Tax:"), at("No plan without")]
    assert order == sorted(order), order


def test_the_compounding_headline_and_the_period_words():
    col = _col(reached_outcome=0, reached=4, ended_at_or_above=3)
    text = R.render(_rep(col, track="compounding"))
    assert "Was worth KRW 42,000,000 at some price check in 4 of 20,000 made-up months (about 1 in 5,000); ended " \
        "at or above it in 3 (about 1 in 6,700)." in text
    assert "this plan reached KRW 42,000,000 before income tax in 4, about 1 in 5,000" in text
    assert "Ended at or above:\n+10% (KRW 46,200): about 4.5%" in text
    locked = _col(reached=5, reached_outcome=3)                   # a locked exit missed T on two moonshot paths
    text = R.render(_rep(locked))
    assert "before income tax: about 1 in 6,700." in text and "before income tax in 3, about 1 in 6,700" in text
    assert "before income tax in 5, about 1 in 4,000" in R.render(_rep(locked, track="compounding"))
    text = R.render(_rep(horizon_days=10))
    assert "The middle 10-day period ends with KRW 21,000." in text and "In 20,000 made-up 10-day periods" in text


def test_tax_ceiling_research_base_rates_boxes_limits_and_footer_are_present():
    text = R.render(_rep())
    for key in ("tax.crypto", "research.estimate", "baserate.kalshi", "baserate.esma", "baserate.sebi",
                "baserate.krderiv", "baserate.kr2020", "notin.title", "notin.close", "limits.injected", "footer"):
        assert R.say(key) in text, key
    for key in R._NOT_IN:
        assert "\n- " + R.say(key) + "\n" in text, key
    for dated in ("2025-26", "27 March 2018", "FY26", "2020 to H1 2025", "In a 2020 study of 204,004"):
        assert dated in text, dated
    assert "No plan without a real edge that keeps this floor can beat 1 in 1,999." in text
    assert "Floor-protected sizing: your floor of KRW 21,000 holds even if this position goes to zero." in text
    assert "NumPy and SciPy are outside the signed code hash." in text and "data/macro" in text
    stop = R.render(_rep(sizing="stop_based", l_min=0.0, ceiling=STOP_CEIL, flags=_flags(_col(), ceiling=STOP_CEIL)))
    assert "No plan without a real edge can beat 1 in 1,000." in stop
    assert "Stop-based sizing: a gap past the stop can take you below your floor of KRW 21,000." in stop
    krx = R.render(_rep(tax_basis="krx_small_holder_exempt", cost_words_key="cost.tax"))
    assert R.say("tax.krx") in krx and "(fees and the securities transaction tax average KRW 50;" in krx
    us = R.render(_rep(tax_basis="overseas_22pct_over_2.5m"))
    assert R.say("tax.overseas") in us and R.say("fx.us") in us and R.say("fx.us") not in text


def test_impossible_and_no_trade_print_no_probability_of_the_target():
    rep = _impossible_rep()
    assert [f.code for f in rep.flags if f.code in ("IMPOSSIBLE", "BELOW_RESOLUTION")] == ["IMPOSSIBLE"]
    lines = R.render(rep).splitlines()
    sentence = "IMPOSSIBLE for this buy-and-hold plan: KRX's daily band allows at most 96× in these 16 sessions."
    assert lines.count(sentence) == 1
    assert not any(line.startswith(("Chance of reaching", "In 20,000 made-up")) for line in lines)
    target = next(line for line in lines if line.startswith("your target (KRW"))
    assert target == "your target (KRW 42,000,000): IMPOSSIBLE for this buy-and-hold plan"
    assert not _PROB.search(sentence) and not _PROB.search(target)

    def at(rows: list[str], prefix: str) -> int:
        return next(i for i, line in enumerate(rows) if line.startswith(prefix))
    # in the plain sentence's place: after the floor line and the ladder, right before the tax line
    assert at(lines, "Chance of ending at your floor") < at(lines, "Ended at or above:") < at(lines, "Middle result")
    assert lines.index(sentence) == at(lines, "Middle result") + 1 == at(lines, "Tax:") - 1
    assert "10 times your stake (KRW 420,000): about 1 in 1,000" in lines        # 10x is inside the 95x cap
    low = R.render(_impossible_rep(cap=5.0, sessions=3)).splitlines()
    assert "10 times your stake (KRW 420,000): IMPOSSIBLE for this buy-and-hold plan" in low
    assert "2 times your stake (KRW 84,000): about 1 in 170" in low
    idle = _idle_rep()
    assert not any(f.code in ("IMPOSSIBLE", "BELOW_RESOLUTION") for f in idle.flags)
    lines = R.render(idle).splitlines()
    notrade = "No simulated month made a trade, so these numbers describe holding cash."
    assert lines.count(notrade) == 1
    assert lines.index(notrade) == at(lines, "Middle result") + 1 == at(lines, "Tax:") - 1
    assert not any(line.startswith(("Chance of reaching", "In 20,000 made-up", "your target (KRW",
                                    "Ended at or above")) for line in lines)
    assert "No simulated month ended at your floor." in lines


def test_below_resolution_rides_on_the_plain_sentence():
    col = _col(reached=0, reached_outcome=0, ended_at_or_above=0, rungs=(900, 400, 120, 20, 0))
    flags = _flags(col)
    below = [f for f in flags if f.code == "BELOW_RESOLUTION"]
    assert [(f.level, f.key) for f in below] == [("info", "")]
    text = R.render(_rep(col, flags=flags))
    assert "this plan never reached KRW 42,000,000 before income tax (below resolution: under about 3 in 20,000;" \
        in text
    assert "Chance of reaching KRW 42,000,000 before income tax: below about 3 in 20,000." in text
    # flags_for counts first passages: 3 paths touched T but every exit missed it, so the plain sentence (moonshot
    # outcomes) prints plain.none while BELOW_RESOLUTION, which never prints, stays off
    touched = _col(reached=3, reached_outcome=0, ended_at_or_above=0, rungs=(900, 400, 120, 20, 0))
    assert not any(f.code == "BELOW_RESOLUTION" for f in _flags(touched))
    text = R.render(_rep(touched, flags=_flags(touched)))
    assert "this plan never reached KRW 42,000,000 before income tax (below resolution: under about 3 in 20,000;" \
        in text


def test_no_probability_slot_renders_as_zero():
    for rep in [*_fixture_reports(), _assumed_rep(p0=0.0), _assumed_rep(u=0.0), _assumed_rep(p0=0.0, u=0.0)]:
        text = R.render(rep)
        assert not _ZERO.search(text), _ZERO.search(text)


def test_the_comparison_lines():
    text = R.render(_rep(comparison=(3, 2, 4)))
    lines = ("You compared 3 plans (and tried 2 typed win rates) in this session. The highest-looking figure is the "
             "luckiest of 3.",
             "This plan has been run in 4 comparisons, each on its own market seed; the highest-looking of its "
             "figures is the luckiest of 4.",
             R.say("compare.caption"),
             "Before arming, this plan must be run again on a fresh market seed; that rerun belongs to execution and "
             "is not built yet.",
             R.say("footer"))
    where = [text.index(line) for line in lines]
    assert where == sorted(where), where
    assert R.say("compare.caption") not in R.render(_rep(track="compounding"))


def test_flags_for_emits_each_flag_in_the_contract_order():
    rep = _okx_rep()
    assert [(f.code, f.level, f.key) for f in rep.flags] == [
        ("HIDDEN_EDGE", "info", "hidden.pass"), ("ABOVE_ESTIMATED_REFERENCE", "amber", "flag.reference"),
        ("GREY_LEG", "amber", "flag.grey"), ("PROXY_DATA", "info", "flag.proxy"),
        ("PROXY_DATA", "info", "flag.proxyfx"), ("CHECKS_AT_OPEN_CLOSE", "info", "flag.openclose"),
        ("BAND_EDGE_SESSIONS", "info", "flag.bandedge"), ("LIMIT_GAP", "info", "flag.gap"),
        ("LOCKED_AT_HORIZON", "info", "flag.locked"), ("COST_DOMINATED", "amber", "flag.cost"),
        ("RULE_CHANGE_IN_HORIZON", "amber", "rule.review"), ("RULE_CHANGE_IN_HORIZON", "amber", "rule.end"),
        ("RULE_CHANGE_IN_HORIZON", "amber", "rule.end")]
    text = R.render(rep)
    expected = (
        "Each simulated OKX entry is capped at 10.0% of this plan's stake (KRW 4,200), the cap the gate applies.",
        "Above the estimated reference: this plan's chance of the target is above what this bracket's simulated "
        "outcomes could reach with any stake (about 1 in 1,000,000).",
        "OKX is a grey venue (rule KR-OKX-SPOT): each armed session needs your acknowledgement of its warning, "
        "everything you hold there is capped at 10.0% of your equity, and the gate turns it off on 2026-12-03.",
        "Costs average KRW 4,200, 10.0% of your stake.",
        "From 2026-11-22 this plan opens no new position unless you re-approve rule KR-OKX-SPOT; it keeps and may "
        "close what it holds.",
        "On 2026-12-03 rule KR-OKX-SPOT ends (the gate turns this venue off), so the plan closes its position at the "
        "first price check on or after that date and opens no new one.",
        "On 2026-12-05 rule KR-OKX-SPOT ends (the rule expires), so the plan closes",
        "Prices for this leg are a stand-in: Binance BTCUSDT times Upbit KRW-USDT",
        "From 2021-01-01 to 2021-03-04, before Upbit listed KRW-USDT, Yahoo's KRW=X rate stands in for it.",
        "12 simulated sessions (1.3% of all) opened at a KRX daily limit and stayed there until the close.",
        "The worst stop fill was 4.6% below its stop level.",
        "In about 1 in 500 of months the position was still locked at the lower daily limit at the end",
        "Bug check passed with a resolution of KRW")
    where = [text.index(line) for line in expected]
    assert where[1:4] == sorted(where[1:4]) and max(where[1:7]) < min(where[7:]), where      # amber, then info
    plain = _flags(_col(), engine="replay")
    assert "CLOSE_ONLY_CHECKS" in [f.code for f in plain] and "CHECKS_AT_OPEN_CLOSE" not in [f.code for f in plain]
    assert not any(f.code == "ABOVE_ESTIMATED_REFERENCE" for f in _flags(_col(), reference=0.0))
    assert not any(f.code == "ABOVE_ESTIMATED_REFERENCE" for f in _flags(_col(), reference=0.5))
    # the two-sided lower bound is compared, not the point: 4 in 20,000 has 5.4e-5 < 1e-4 < 2e-4
    assert not any(f.code == "ABOVE_ESTIMATED_REFERENCE" for f in _flags(_col(), reference=1e-4))
    # first passages are counted (no track argument): 8 passages bound 1.7e-4 > 1e-4 though 4 outcomes bound 5.4e-5
    locked = _col(reached=8, reached_outcome=4)
    assert [f.key for f in _flags(locked, reference=1e-4) if f.code == "ABOVE_ESTIMATED_REFERENCE"] == \
        ["flag.reference"]
    assert not any(f.code == "COST_DOMINATED" for f in _flags(_col(mean_cost=4_199.0)))


def test_the_stress_and_delisting_columns():
    head = _col()
    stress = _col(key="no_edge/bootstrap/stress2x", scenario="stress2x", mean=41_900.0, mean_cost=100.0)
    other = _col(key="no_edge/bootstrap_half/stress2x", member="bootstrap_half", scenario="stress2x")
    d30 = _col(key="delist_30", mean=29_500.0, mean_cost=12_500.0)
    text = R.render(_rep(head, stress, other, d30))
    assert text.count("With costs doubled:") == 1
    assert "With costs doubled:\nThe middle month ends with KRW 21,000." in text
    assert "(fees average KRW 100; the simulation's own average, KRW 41,900 ± 60, agrees)" in text
    assert "If KRW-BTC were delisted right after you buy, losing 30% of its value:" in text
    assert "(fees and the delisting stress loss average KRW 12,500;" in text


def test_the_assumed_column_lines():
    text = R.render(_assumed_rep())
    assert "These numbers are only as true as the win rate you typed (55.0%). This bracket's no-edge win rate is " \
        "49.9% (2.1% of brackets end unresolved)." in text
    assert "Telling them apart would take about 617 recorded brackets." in text
    assert "Without the edge you typed, no plan that keeps this floor can beat 1 in 1,999." in text
    paragraph = (R.say("assumed.lead", w="55.0%", p0="49.9%", u="2.1%"), R.say("assumed.nb", nb="617"),
                 R.say("assumed.ceiling", c="1 in 1,999"), "The middle month ends with KRW 21,000.")
    assert "\n" + "\n".join(paragraph) + "\n" in text           # spec 7.5's three sentences unbroken, then typical
    assert [R._pct(x) for x in (0.0003, 0.0005, 0.0008, 0.0014, 0.0099, 0.0213, 0.55)] == [
        "0.030%", "0.050%", "0.080%", "0.14%", "0.99%", "2.1%", "55.0%"]
    # P50: round before choosing decimal places when two figures cross a decade.
    assert [R._pct(x) for x in (0.00009999, 0.0009999, 0.009999)] == ["0.010%", "0.10%", "1.0%"]
    # P4: no observed wins or unresolved brackets is a bound from the sample count.
    zero = R.render(_assumed_rep(p0=0.0, u=0.0, resolved=7_000.0))
    assert "no-edge win rate is below about 3 in 7,000 (below about 3 in 7,000 of brackets end unresolved)" in zero
    _raises(lambda: R.render(_assumed_rep(p0=0.0, resolved=0.0)))
    small = R.render(_assumed_rep(w=0.0008, p0=0.0005))
    assert "the win rate you typed (0.080%). This bracket's no-edge win rate is 0.050% (2.1% of brackets" in small
    many = R.render(_assumed_rep(nb=math.inf))
    assert "Telling them apart would take more recorded brackets than the 5,000 this simulation resolved." in many
    assert "Without the edge you typed, no plan can beat 1 in 1,000." in R.render(_assumed_rep("stop_based"))


def test_the_replay_card_lines():
    text = R.render(_replay_rep())
    for part in ("Model: the tested strategy's own out-of-sample daily results, 2019-10-23 to 2026-09-25 (2,530 "
                 "sessions), resampled in blocks of about 10 days.",
                 R.say("replay.noedge"), R.say("kelly.label"),
                 "on its own 2019–2026 out-of-sample results, with 40% of its average return removed.",
                 "had a Sharpe ratio of 0.79, against 0.73 for this replay after the cut.",
                 "was +0.43 Sharpe (90% range +0.03 to +0.83).",
                 "this column's average growth over 29 days is 2.9%, against 2.6% if its days were independent.",
                 "Without the edge assumed here, no plan that keeps this floor can beat 1 in 1,999.",
                 "; no other model could be run here;", "Price checks at the close only.\n"):
        assert part in text, part
    lines = text.splitlines()
    assert lines.index(R.say("replay.noedge")) == lines.index(next(x for x in lines if x.startswith("Model:"))) + 1
    assert R.say("kelly.label") not in R.render(_replay_rep(fstar=math.nan))


# --------------------------------------------------------------------------- #
# The language guard
# --------------------------------------------------------------------------- #
def test_guard_positive_controls_and_rules():
    for bad in ("the best plan", "floor-safe sizing", "a good chance", "plan_hash", "Risk-Free", "a LOW-RISK bet",
                "you Should", "worth   trying", "likely\nto reach", "{x}", "a } b", "xS_C3", "OPTIMAL"):
        assert R.guard(bad), bad
    assert R.guard("the S_C3 replay (S_C3)") == []
    assert R.guard("Floor-protected sizing: measured, recommend, ensure, pressure, safety-net") == []


def test_the_catalogue_is_the_contract_text_and_every_template_passes_the_guard():
    blob = json.dumps(dict(R.CATALOGUE), sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    assert hashlib.sha256(blob).hexdigest() == _CATALOGUE_SHA256
    assert len(R.CATALOGUE) == 193 and isinstance(R.CATALOGUE, MappingProxyType)
    for key, template in R.CATALOGUE.items():
        filled = R.say(key, **{name: "1" for name in re.findall(r"\{([a-z0-9]+)\}", template)})
        assert R.guard(filled) == [], (key, R.guard(filled))
    _raises(lambda: R.say("no.such.key"), KeyError)
    _raises(lambda: R.say("plan.head", i="1"), KeyError)


def test_rendered_reports_and_the_krx_provenance_pass_the_guard():
    md5s = (("holidays_KRX", "1a" * 16), ("kr_regime_tags", "2b" * 16), ("kr_sessions", "3c" * 16))
    prov = _prov(calendar_sha="4d" * 32, calendar_version="1.0.0-fixture", calendar_md5s=md5s,
                 members=("bootstrap", "bootstrap_half", "garch_refit"), edge_source=plan.REPLAY_SOURCE,
                 model="bootstrap", proxy_dates=("2021-01-01", "2021-03-04"))
    text = R.render(_rep(provenance=prov, tax_basis="krx_small_holder_exempt", cost_words_key="cost.tax",
                         spread_kind="krx"))
    assert R.guard(text) == []
    for internal in ("holidays", "kr_sessions", "regime_tags", "bootstrap_half", "garch_refit", "crypto_trend",
                     "upbit_daily", "floor_safe", "plan_hash", "replay:", "decision", "8888888888888888",
                     "9999999999999999"):
        assert internal not in text, internal
    for line in ("Recorded with this report:", "code hash: 6666666666666666", "code signed: yes",
                 "owner log entry: 7 / 5555555555555555", "key fingerprint: 7777777777777777",
                 "tables in force: 1111111111111111 / 2222222222222222 / 3333333333333333 / 4444444444444444",
                 "price history: aaaaaaaaaaaaaaaa / bbbbbbbbbbbbbbbb / 2021-01-01 / 2021-03-04",
                 "calendar: 1.0.0-fixture / 4d4d4d4d4d4d4d4d / 1a1a1a1a1a1a1a1a, 2b2b2b2b2b2b2b2b, 3c3c3c3c3c3c3c3c",
                 "market seed: cccccccccccccccc", "paths and chunk: 20,000 / 2,000",
                 f"NumPy, SciPy, cryptography: {np.__version__} / {scipy.__version__} / 49.0.0",
                 "repository: git:" + "d" * 40, "tree hash: eeeeeeeeeeeeeeee", "comparison and run: c000001 / 1",
                 "model and members: two-point bootstrap / the two-point bootstrap, the bootstrap at half the block "
                 "length, the GARCH-t refit", "edge source: the S_C3 replay"):
        assert "\n" + line + "\n" in text, line
    unsigned = R.render(_rep(provenance=_prov(code_signed=False)))
    assert "\ncode signed: no\n" in unsigned
    for rep in _fixture_reports():
        assert R.guard(R.render(rep)) == []


def test_a_banned_slot_value_or_catalogue_text_makes_render_raise():
    slots = {"first": "2016-10-24", "last": "2026-10-22", "rows": "3,650"}
    for bad in (_rep(model_slots={**slots, "symbol": "BEST"}), _rep(model_slots={**slots, "symbol": "KRW_BTC"}),
                _rep(plan_hash="{oops}"), _refused("SHORT_HISTORY", slots={"symbol": "SAFE"})):
        assert "rendered text failed the language guard" in _raises(lambda: R.render(bad))
    saved = R.CATALOGUE
    try:
        R.CATALOGUE = MappingProxyType({**saved, "footer": "This is the optimal plan."})
        assert "rendered text failed the language guard" in _raises(lambda: R.render(_rep()))
    finally:
        R.CATALOGUE = saved
    assert R.render(_rep())


# --------------------------------------------------------------------------- #
# Refusals
# --------------------------------------------------------------------------- #
def test_a_refused_report_renders_no_computed_probability():
    codes = set()
    for code, sub, slots in _REFUSALS:
        rep = _refused(code, sub, slots)
        assert rep.columns == () and rep.flags == () and rep.hidden is None and rep.spread is None
        assert rep.refused.code == code and math.isnan(rep.ceiling) and rep.n == 0
        text = R.render(rep)
        lines = text.splitlines()
        assert lines[0] == "Plan 1 of 1 (none)" and lines[1].startswith("Refused: ") and "{" not in lines[1]
        assert lines[2] == R.say("refused.none") and lines[3] == R.say("footer") and lines[4] == R.say("prov.head")
        assert "detail" not in text
        scrubbed = text.replace(R.say("sub.bracket"), "").replace("(55.0%)", "")
        assert not _PROB.search(scrubbed), (code, sub, scrubbed)
        codes.add(code)
    assert codes == set(plan.REFUSALS)
    assert "Refused: the chosen model failed its refit check, so no numbers are shown." in R.render(
        _refused("MODEL_CHECK_FAILED", "", {"check": "refit"}))
    assert "Refused: the data given to the engine did not pass its checks: the last price is more than 3 days " \
        "before the start." in R.render(_refused("DATA_INVALID", "stale", {"days": "3"}))
    assert "Refused: upbit BTC cannot be costed or sized from the signed venue table:" in R.render(
        _refused("NOT_TRADABLE", "", {"venue": "upbit", "symbol": "BTC"}))


def test_the_plan_name_never_renders():
    p = plan.Plan(name="my best plan_v2", track="moonshot", stake_krw=W0, target_krw=T, fx_krw_per_usd=1_400.0,
                  start=date(2026, 10, 23), horizon_days=30, leg=plan.Leg(venue="upbit", symbol="BTC",
                                                                          model="bootstrap"),
                  fraction=plan.fixed(1.0))
    rep = R.refusal_report(p, plan.Refusal(code="SCREEN_BLOCKED", sub="row", slots={"row": "KR-OKX-SPOT"}),
                           index=2, count=3)
    text = R.render(rep)
    assert "best" not in text and "v2" not in text and rep.plan_hash == plan.plan_hash(p)
    assert text.splitlines()[:2] == [f"Plan 2 of 3 ({plan.plan_hash(p)[:16]})",
                                     "Refused: the compliance gate blocks this leg: rule KR-OKX-SPOT."]
    nan_plan = dataclasses.replace(p, stake_krw=math.nan)
    assert R.refusal_report(nan_plan, plan.Refusal(code="UNSUPPORTED_PRODUCT", sub="numbers")).plan_hash == ""


def test_build_freezes_mappings_and_refuses_inconsistent_reports():
    rep = _rep()
    assert isinstance(rep.provenance, MappingProxyType) and isinstance(rep.model_slots, MappingProxyType)
    assert isinstance(rep.columns, tuple) and rep.headline == "no_edge/bootstrap/base"
    for bad in (dict(headline="no_edge/garch_t/base"), dict(spread=None), dict(spread_kind="wide"),
                dict(spread=(0.0, 1e-4), spread_kind="none")):
        _raises(lambda bad=bad: _rep(**bad))
    _raises(lambda: _rep(_col(), _col()))
    refused = _refused("STUCK_AT_START")
    fields = {f.name: getattr(refused, f.name) for f in dataclasses.fields(refused)}
    _raises(lambda: R.build(**{**fields, "columns": (_col(),)}))
    _raises(lambda: R.build(**{**fields, "flags": _flags(_col())}))
    _raises(lambda: R.build(**{k: v for k, v in fields.items() if k != "provenance"}), TypeError)
    for missing in ("columns", "flags", "notes"):
        _raises(lambda missing=missing: R.build(**{k: v for k, v in fields.items() if k != missing}), TypeError)
