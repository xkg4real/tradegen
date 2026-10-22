"""M7 package C tests: CARD-P gate v2 (R-21), evaluation conventions (R-22), timing-fragility gate (R-34) and the
gate-acceptance machinery (R-21 rule 9) on synthetic panels only (core/quant/cardp.py).

SYNTH: T-ES-01, T-DNH-01, T-ORDER-01, T-EPIS-01 (builder logic, open bear), T-EXCESS-01 (unit clauses), T-ROLE-02 (cash
clause), T-BAND-01, T-PLACEBO-01 (FR arithmetic, synthetic look-ahead control, ledger rows, noise-overlay family),
T-PLACEBO-02 (probe isolation), T-LAG-01/02 (probe clauses), T-GATE-04 (bounded redesign), I-05 (synthetic end to end).
REFDATA: I-08, T-GATE-01, T-GATE-03, T-EPIS-01 counts, T-EPIS-02, T-TROUGH-01, T-ES-02, T-RLAYER-01, T-PLACEBO-01 control
fixture, I-05 golden lag audit. OWNER: T-EXCESS-01 ECOS clause.

Hermetic: seeded synthetic series, tempfile directories for every log, no clock, no network. Nothing is written under
`config.macro_dir()`; the production `gate/acceptance_runs.jsonl` is asserted empty. No formal card is evaluated.
"""
from __future__ import annotations

import ast
import json
import os
import tempfile
from datetime import date, timedelta
from pathlib import Path

import numpy as np

import config
from core.ficc.contracts import default_registry
from core.ficc.pit import MissingInput
from core.quant import cardp as CP
from core.quant import costed as C
from core.quant import gate_stats as GS
from core.rules import governance
from tests.notrun import NotRun, require_fixture

# R-24 power block at mde80 = 0.05 (cardp_evaluate refuses a card without every L2612 field, T-POWER-02)
POWER = GS.power_line(0.05 / GS.MDE_FACTOR, sessions=2820).as_dict()

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "core"
SEED, B = 11, 200
REFDATA = ("REFDATA: KOSPI 1997-2026 official closes (KRX), French daily Mkt-RF/RF 1926-07..2026-08 files, PX2 cash "
           "fixture (FRED IRSTCI01KRM156N), QX_EX1 ledger rows and the PX1/EX1 negative-control rule scripts")


def _raises(fn, exc, needle: str = "") -> Exception:
    try:
        fn()
    except exc as e:
        assert needle in str(e), f"{exc.__name__} without {needle!r}: {e}"
        return e
    raise AssertionError(f"{exc.__name__} not raised")


def _bdays(start: date, n: int) -> list[date]:
    d = np.busday_offset(np.datetime64(start, "D"), np.arange(n), roll="forward")
    return [x.astype("datetime64[D]").astype(date) for x in d]


# --------------------------------------------------------------------------- #
# Synthetic panels (seeded)
# --------------------------------------------------------------------------- #
def regime_returns(seed: int = SEED, n_cycles: int = 6, calm: int = 400, stress: int = 70) -> np.ndarray:
    """Alternating calm (sigma 0.8%, drift +0.06%) and stress (sigma 3%, drift -0.4%) regimes: six bear markets
    deeper than 20% separated by rallies above 20%, 2,820 sessions."""
    rng = np.random.default_rng(seed)
    out = []
    for _ in range(n_cycles):
        out.append(rng.normal(0.0006, 0.008, calm))
        out.append(rng.normal(-0.004, 0.03, stress))
    return np.concatenate(out)


def vt_decided(r: np.ndarray, target: float = 0.20, window: int = 20) -> np.ndarray:
    m = C.vt_weights(r, target, window)
    return np.where(np.isfinite(m), m, 1.0)


def shift(decided: np.ndarray, L: int) -> np.ndarray:
    """Earning path at lag L: the weight that earns r_t was decided at the close of t - L (L = 1 honest)."""
    out = np.roll(decided, L)
    if L > 0:
        out[:L] = decided[0]
    elif L < 0:
        out[L:] = decided[-1]
    return out


def books_at(r: np.ndarray, decided: np.ndarray, L: int, cost_bp: float = 3.0) -> CP.Books:
    dates = _bdays(date(2001, 1, 2), r.size)
    return CP.build_books(shift(decided, L), r, cost_bp, dates)


def closes_of(r: np.ndarray) -> tuple[list[date], np.ndarray]:
    dates = _bdays(date(2001, 1, 1), r.size + 1)
    return dates, 100.0 * np.concatenate([[1.0], np.cumprod(1 + r)])


def _header(**over) -> dict:
    h = {"card_id": "SYN-PROTECT", "family_id": "R-06", "episode_rule_version": "1",
         "cash_convention": {"returns": "excess", "cash_series": "SYN_CASH", "day_count": "act_365"},
         "history_first_close": "2001-01-01", "line": "full_span"}
    h.update(over)
    return h


def _control() -> dict:
    """The synthetic look-ahead positive control: a same-day-sign rule run in the probe (L0 >> L1)."""
    r = regime_returns(seed=5, n_cycles=3)
    sign_rule = np.where(r > 0, 1.0, 0.5)
    prof = CP.timing_probe({"card_id": "LEAK", "family_id": "CTRL", "config": {"rule": "same_day_sign"}},
                           lambda L: books_at(r, sign_rule, L, 0.0), sandbox=True, B=50, seed=SEED)
    return CP.lookahead_positive_control(prof)


def _neighbours(r: np.ndarray, centre_window: int = 20, centre_target: float = 0.20) -> list[dict]:
    """The 8 Moore neighbours of the frozen vol_target axes (window x {0.5, 1, 2}, target x {0.75, 1, 1.25})."""
    out = []
    for wm in (0.5, 1, 2):
        for tm in (0.75, 1, 1.25):
            if wm == 1 and tm == 1:
                continue
            b = books_at(r, vt_decided(r, centre_target * tm, int(centre_window * wm)), 1)
            legs = CP.pc1_prime(b.on, b.S, f=1.0, B=B, seed=SEED)
            out.append({"dES_21": legs[0]["dES"], "dES_126": legs[1]["dES"], "dSR": CP.sharpe(b.on) - CP.sharpe(b.S)})
    return out


def _evaluate(r: np.ndarray, decided: np.ndarray, *, control: dict, neighbours=None, kind="continuous", f=1.0) -> CP.CardResult:
    b = books_at(r, decided, 1)
    dates, closes = closes_of(r)
    eps = CP.episodes(closes, dates, threshold=0.20)
    prof = CP.timing_profile({"card_id": "SYN", "family_id": "R-06", "config": {"rule": "vt"}},
                             lambda L: books_at(r, decided, L), B=50, seed=SEED)
    return CP.cardp_evaluate(b.on, b.off, b.S, _header(), f, SEED, B, m=b.m, dates=b.dates, on_2x=b.on_2x, eps=eps,
                             timing=prof, control=control, power=POWER, kind=kind, neighbours=neighbours)


# --------------------------------------------------------------------------- #
# T-ES-01: sign convention
# --------------------------------------------------------------------------- #
def test_es_01_sign_convention_identical_to_S_rejects():
    r = regime_returns()
    b = books_at(r, np.full(r.size, 0.8), 1)          # constant rule: on == S (no turnover, no cost)
    assert np.allclose(b.on, b.S)
    legs = CP.pc1_prime(b.on, b.S, f=1.0, B=B, seed=SEED)
    assert [leg["dES"] for leg in legs] == [0.0, 0.0] and not any(leg["pass"] for leg in legs)
    dates, closes = closes_of(r)
    eps = CP.episodes(closes, dates, threshold=0.20)
    assert len(CP.closed_in_span(eps)) >= 5 and r.size >= 882          # sufficiency passes first
    res = _evaluate(r, np.full(r.size, 0.8), control=_control())
    assert res.verdict == "REJECT" and res.reason_code == "PC1p", (res.verdict, res.reason_code)
    # halving exposure on the worst 5% of 21-session windows (a sign test, look-ahead by construction)
    r21 = CP.horizon_returns(r, 21)
    k = int(np.ceil(0.05 * r21.size))
    worst = np.argsort(r21, kind="stable")[:k] + 20
    m = np.full(r.size, 0.8)
    for e in worst:
        m[max(0, e - 20):e + 1] = 0.4
    on = C.costed_path(m, r, 0.0).net
    leg21 = CP.pc1_prime(on, CP.comparator_S(m, r), f=1.0, B=B, seed=SEED, horizons=(21,))[0]
    assert leg21["dES"] > 0 and leg21["point_pass"]
    assert CP.es(r, 0.95, 21) > 0 and CP.es(r, 0.99, 1) > CP.es(r, 0.95, 1)


test_es_01_sign_convention_identical_to_S_rejects.test_ids = ["T-ES-01"]


# --------------------------------------------------------------------------- #
# T-DNH-01, T-ORDER-01: the verdict order on injected checks
# --------------------------------------------------------------------------- #
def _checks(**over) -> dict:
    legs = [{"h": 21, "dES": 0.02, "p": 0.01}, {"h": 126, "dES": 0.04, "p": 0.02}]
    c = {"pc7": {"pass": True}, "pc1p": {"legs": legs, "two_x": [dict(x) for x in legs]},
         "pc2": {"ratio_used": 0.70}, "pc3": {"dSR": 0.05, "p_ni": 0.03, "point_2x": 0.02},
         "pc4": {"positive": 5, "max_share": 0.30}, "pc5": {"pass": True}, "pc6": {"pass": True},
         "power": {"mde80": 0.05}, "caps": {}}
    c.update(over)
    return c


def test_dnh_01_do_no_harm_cap_only_lowers():
    v = CP.line_verdict(_checks(caps={"do_no_harm": True}), 1.0)
    assert v["verdict"] == "INSUFFICIENT_DATA" and v["reason"] == "do_no_harm" and v["caps_applied"] == ["do_no_harm"]
    assert CP.line_verdict(_checks(), 1.0)["verdict"] == "PASS"                      # only dMDD < 0: no cap
    lines = CP.printed_lines(np.full(600, -0.001), np.full(600, 0.001), B=50, seed=SEED)
    assert lines["dMDD"] < 0 and lines["dCDaR95"] < 0 and lines["do_no_harm"]
    lines2 = CP.printed_lines(np.full(600, 0.001), np.full(600, 0.0005), B=50, seed=SEED)
    assert not lines2["do_no_harm"]
    # no drawdown-line value ever produces REJECT: the cap lowers a PASS/REVISE only, never below INSUFFICIENT_DATA
    for base in ({}, {"pc5": {"pass": False}}):
        v = CP.line_verdict(_checks(caps={"do_no_harm": True}, **base), 1.0)
        assert v["verdict"] == "INSUFFICIENT_DATA"
    v = CP.line_verdict(_checks(caps={"do_no_harm": True, "timing_fragile": True, "estimator_calibration": True}), 1.0)
    assert v["verdict"] == "INSUFFICIENT_DATA" and "do_no_harm" in v["caps_applied"]
    # the estimator cap lowers to REVISE only
    v = CP.line_verdict(_checks(caps={"estimator_calibration": True}), 1.0)
    assert v["verdict"] == "REVISE" and v["reason"] == "estimator_calibration"


test_dnh_01_do_no_harm_cap_only_lowers.test_ids = ["T-DNH-01"]


def test_order_01_verdict_order_and_caps():
    # 26 de-clustered onsets, discrete: PC-7 fails -> sufficiency first, even though PC-2 also fails
    c = _checks(pc7=CP.pc7("discrete", n_sessions=3000, n_episodes=6, onsets=26), pc2={"ratio_used": 0.95})
    v = CP.line_verdict(c, 1.0)
    assert (v["verdict"], v["reason"]) == ("INSUFFICIENT_DATA", "sufficiency")
    ok54 = CP.pc7("discrete", n_sessions=3000, n_episodes=6, onsets=54)
    assert ok54["pass"]
    legs_bad = [{"h": 21, "dES": -0.01, "p": 0.01}, {"h": 126, "dES": 0.04, "p": 0.02}]
    v = CP.line_verdict(_checks(pc7=ok54, pc1p={"legs": legs_bad, "two_x": legs_bad}), 1.0)
    assert (v["verdict"], v["reason"]) == ("REJECT", "PC1p")
    legs_p = [{"h": 21, "dES": 0.01, "p": 0.08}, {"h": 126, "dES": 0.04, "p": 0.02}]
    v = CP.line_verdict(_checks(pc7=ok54, pc1p={"legs": legs_p, "two_x": legs_p}), 1.5)   # 0.08 x 1.5 > 0.10
    assert (v["verdict"], v["reason"]) == ("INSUFFICIENT_DATA", "inconclusive")
    assert CP.line_verdict(_checks(pc7=ok54, pc1p={"legs": legs_p, "two_x": legs_p}), 1.0)["verdict"] == "PASS"
    # a timing-fragile card meeting a REJECT condition stays REJECT (caps only lower)
    v = CP.line_verdict(_checks(pc2={"ratio_used": 0.95}, caps={"timing_fragile": True}), 1.0)
    assert v["verdict"] == "REJECT" and v["caps_applied"] == []
    v = CP.line_verdict(_checks(caps={"timing_fragile": True}), 1.0)
    assert (v["verdict"], v["reason"]) == ("INSUFFICIENT_DATA", "timing_fragile")
    # the rest of the order: PC-3 point REJECT; PC-4 < 3 REJECT; concentration alone inconclusive; underpowered
    assert CP.line_verdict(_checks(pc3={"dSR": -0.11, "p_ni": 0.01, "point_2x": -0.11}), 1.0)["reason"] == "PC3"
    assert CP.line_verdict(_checks(pc4={"positive": 2, "max_share": 0.3}), 1.0)["verdict"] == "REJECT"
    v = CP.line_verdict(_checks(pc4={"positive": 4, "max_share": 0.6}), 1.0)
    assert (v["verdict"], v["reason"]) == ("INSUFFICIENT_DATA", "inconclusive")
    v = CP.line_verdict(_checks(pc3={"dSR": 0.0, "p_ni": 0.2, "point_2x": 0.0}, power={"mde80": 0.2}), 1.0)
    assert (v["verdict"], v["reason"]) == ("INSUFFICIENT_DATA", "underpowered")
    v = CP.line_verdict(_checks(pc3={"dSR": 0.0, "p_ni": 0.2, "point_2x": 0.0}, power={"mde80": 0.05}), 1.0)
    assert (v["verdict"], v["reason"]) == ("INSUFFICIENT_DATA", "inconclusive")
    # UNDERPOWERED never waives PC-1', PC-2 or the PC-3 point
    assert CP.line_verdict(_checks(pc2={"ratio_used": 0.95}, power={"mde80": 0.5}), 1.0)["verdict"] == "REJECT"
    assert CP.line_verdict(_checks(pc3={"dSR": -0.2, "p_ni": 0.5, "point_2x": 0}, power={"mde80": 0.5}), 1.0)["verdict"] == "REJECT"
    # REVISE sub-order: 2x legs (lengthen_holding), PC-6 (widen_grid), PC-5 (extend_history)
    two_x = [{"h": 21, "dES": -0.01, "p": 0.3}, {"h": 126, "dES": 0.04, "p": 0.02}]
    v = CP.line_verdict(_checks(pc1p={"legs": _checks()["pc1p"]["legs"], "two_x": two_x}, pc6={"pass": False}), 1.0)
    assert (v["verdict"], v["permitted_fix"]) == ("REVISE", "lengthen_holding")
    assert CP.line_verdict(_checks(pc6={"pass": False}, pc5={"pass": False}), 1.0)["permitted_fix"] == "widen_grid"
    assert CP.line_verdict(_checks(pc5={"pass": False}), 1.0)["permitted_fix"] == "extend_history"
    assert CP.line_verdict(_checks(pc6={"pass": None}), 1.0)["verdict"] == "PASS"      # no grid: n/e, not a failure
    # combine_card_verdict: worst of the gating lines; I-16's PASS iff (i)-(iv)
    assert CP.combine_card_verdict({"full_span": "PASS", "etf_era": "PASS", "floor": True, "halves": True}) == ("PASS", None)
    assert CP.combine_card_verdict({"full_span": "PASS", "etf_era": "INSUFFICIENT_DATA", "floor": True, "halves": True})[0] == "INSUFFICIENT_DATA"
    assert CP.combine_card_verdict({"full_span": "PASS", "etf_era": "PASS", "floor": False, "halves": True}) == ("INSUFFICIENT_DATA", "stability")
    assert CP.combine_card_verdict({"full_span": "REVISE", "etf_era": "REJECT"}) == ("REJECT", "etf_era")
    assert CP.combine_card_verdict({"a": "REVISE", "b": "INSUFFICIENT_DATA"})[0] == "INSUFFICIENT_DATA"
    _raises(lambda: CP.combine_card_verdict({}), CP.CardRefused, "no gating line")
    _raises(lambda: CP.line_verdict(_checks(), 0.5), CP.CardRefused, "at least 1")


test_order_01_verdict_order_and_caps.test_ids = ["T-ORDER-01"]


# --------------------------------------------------------------------------- #
# T-EPIS-01: the alternating builder, open bear, shock types, leave-one-crisis-out
# --------------------------------------------------------------------------- #
def test_epis_01_builder_on_known_drawdowns_and_open_bear():
    dates = _bdays(date(2008, 9, 1), 12)
    closes = [100, 110, 120, 100, 96, 90, 100, 108, 130, 104, 95, 97]
    eps = CP.episodes(list(zip(dates, closes)), threshold=0.20, market="KR")
    assert len(eps) == 2
    first, second = eps
    assert (first.start, first.trough, first.end, first.open) == (dates[2], dates[5], dates[7], False)
    assert abs(first.depth - (90 / 120 - 1)) < 1e-12 and first.shock_type == "GFC"
    assert second.open and second.end is None and second.start == dates[8] and second.trough == dates[10]
    assert CP.closed_in_span(eps) == [first]                       # the open bear counts toward neither PC-4 nor PC-7
    assert CP.pc7("continuous", n_sessions=3000, n_episodes=len(CP.closed_in_span(eps)))["n_episodes"] == 1
    # benefits over the returns after the peak close through the trough; open episodes get none
    r = np.diff(np.array(closes, dtype=float)) / np.array(closes[:-1], dtype=float)
    rd = dates[1:]
    on, S = 0.5 * r, 1.0 * r
    bens = CP.episode_benefits(on, S, rd, CP.closed_in_span(eps))
    assert len(bens) == 1 and bens[0] > 0
    assert CP.pc4(bens) == {"positive": 1, "n": 1, "max_share": 1.0, "pass": False}
    assert CP.pc4([0.1, 0.2, 0.3, -0.1])["pass"] and not CP.pc4([0.1, 0.2, 0.7])["pass"]   # max share 0.7 > 0.5
    # the regime path: >= 5 closed episodes of >= 20%, every depth <= -0.20, alternating by construction
    r = regime_returns()
    d, c = closes_of(r)
    eps = CP.episodes(c, d, threshold=0.20)
    closed = CP.closed_in_span(eps)
    assert len(closed) >= 5 and all(e.depth <= -0.20 for e in closed)
    assert all(a.end <= b.start for a, b in zip(closed, closed[1:]))
    assert CP.post_trough_window(on, S, rd, first) is not None
    table = CP.shock_type_table(on, S, rd, "KR")
    assert set(table["leave_one_crisis_out"]) == set(CP.SHOCK_GROUPS) and table["windows"]["Sep-2026"]["group"] is None
    assert table["windows"]["GFC"]["rule_minus_S"] is not None
    assert set(CP.cost_episodes(on, S, rd, "KR")) == {"rebound_2009", "rebound_2020", "h1_2026"}
    # refusals: vendor / provisional closes; a foreign rule name; theta rule for other markets
    _raises(lambda: CP.episodes(list(zip(dates, closes)), value_status="vendor_close"), CP.CardRefused, "refused")
    _raises(lambda: CP.episodes(list(zip(dates, closes)), rule="peak_to_trough"), CP.CardRefused, "frozen")
    assert CP.theta_for("KR") == 0.20 and CP.theta_for("US_SPX") == 0.15
    assert CP.theta_for("JP", 0.17) == 0.15 and CP.theta_for("JP", 0.19) == 0.20
    _raises(lambda: CP.theta_for("JP"), CP.CardRefused, "frozen rule")
    # no override of any date exists in the builder source (Sep-2026 is an assertion on the output, never coded)
    tree = ast.parse((CORE / "quant" / "cardp.py").read_text(encoding="utf-8"))
    fn = next(f for f in ast.walk(tree) if isinstance(f, ast.FunctionDef) and f.name == "episodes")
    body = fn.body[1:] if isinstance(fn.body[0], ast.Expr) and isinstance(fn.body[0].value, ast.Constant) else fn.body
    consts = [n.value for b in body for n in ast.walk(b) if isinstance(n, ast.Constant) and isinstance(n.value, str)]
    assert not any("2026" in c or "override" in c.lower() for c in consts), consts
    assert not any(isinstance(n, ast.Constant) and isinstance(n.value, (int, float)) and n.value > 1900 for b in body for n in ast.walk(b))


test_epis_01_builder_on_known_drawdowns_and_open_bear.test_ids = ["T-EPIS-01"]


def test_epis_01_counts_on_official_closes_refdata():
    """18 >= 20% KOSPI episodes 1997-2026 (12 troughs before 2008), 4 on 2016-26, 16 S&P at 15% 1990-2026, no Sep-2026."""
    require_fixture("krx_kospi_official_close_1997-01-03_2026-10-02.csv")
    require_fixture("yahoo_GSPC_1990_2026-10-01.csv")
    raise AssertionError("fixture listed: golden assertion not implemented")


test_epis_01_counts_on_official_closes_refdata.test_ids = ["T-EPIS-01"]


# --------------------------------------------------------------------------- #
# T-EXCESS-01 / T-ROLE-02: the cash leg by unit; the frozen ECOS clause
# --------------------------------------------------------------------------- #
def test_excess_01_cash_units_and_missing_day_refusal():
    d = [date(2024, 1, 5), date(2024, 1, 8), date(2024, 1, 9)]            # Fri, Mon, Tue
    rates = {date(2024, 1, 4): 3.0, date(2024, 1, 5): 3.5, date(2024, 1, 8): 3.5}
    leg = CP.CashLeg("BOK_CALL_RATE", "annual_rate", rates, tuple(rates))
    c = CP.daily_cash(d, leg, prev_session=date(2024, 1, 4))
    assert np.allclose(c, [0.03 * 1 / 365, 0.035 * 3 / 365, 0.035 * 1 / 365])   # latest rate dated <= t-1, x days/365
    # a closed day of the rate's own calendar carries the prior rate (Monday absent from the calendar, no value)
    leg2 = CP.CashLeg("BOK_CALL_RATE", "annual_rate", {date(2024, 1, 4): 3.0, date(2024, 1, 5): 3.5},
                      (date(2024, 1, 4), date(2024, 1, 5)))
    assert np.allclose(CP.daily_cash(d, leg2, prev_session=date(2024, 1, 4))[2], 0.035 / 365)
    # a day of the series' own calendar without a value refuses the card: never cash = 0
    leg3 = CP.CashLeg("BOK_CALL_RATE", "annual_rate", {date(2024, 1, 4): 3.0, date(2024, 1, 5): 3.5}, tuple(rates))
    _raises(lambda: CP.daily_cash(d, leg3, prev_session=date(2024, 1, 4)), CP.CardRefused, "missing cash day 2024-01-08")
    # a series that does not cover the span refuses
    _raises(lambda: CP.daily_cash(d, leg, prev_session=date(2023, 12, 1)), CP.CardRefused, "does not cover")
    # per-period series enter as published; zero-investment series get no cash term; raw only as a flag
    per = CP.CashLeg("US_RF", "per_period", {x: 0.0001 for x in d})
    r, w = np.array([0.01, -0.02, 0.005]), np.array([1.0, 0.5, 0.5])
    x = CP.excess_returns(r, d, w, per, prev_session=date(2024, 1, 4))
    assert np.allclose(x, w * (r - 0.0001))
    xa = CP.excess_returns(r, d, w, leg, prev_session=date(2024, 1, 4), cost=np.array([0, 0.0003, 0]))
    assert np.allclose(xa, w * (r - c) - np.array([0, 0.0003, 0]))
    zi = CP.CashLeg("FRENCH_MOM", "per_period", {}, zero_investment=True)
    assert np.allclose(CP.excess_returns(r, d, w, zi, prev_session=date(2024, 1, 4)), w * r)
    _raises(lambda: CP.excess_returns(r, d, w, None, prev_session=date(2024, 1, 4)), CP.CardRefused, "raw")
    assert np.allclose(CP.excess_returns(r, d, w, None, prev_session=date(2024, 1, 4), raw=True), w * r)
    _raises(lambda: CP.daily_cash(d, CP.CashLeg("X", "monthly_pct", {}), prev_session=d[0]), CP.CardRefused, "unit")
    # a header whose cash convention is not excess is refused by the evaluator
    _raises(lambda: CP._check_header(_header(cash_convention={"returns": "raw"})), CP.CardRefused, "excess")


test_excess_01_cash_units_and_missing_day_refusal.test_ids = ["T-EXCESS-01", "T-ROLE-02"]


def test_excess_01_bok_call_rate_ecos_code_is_owner_input():
    leg = CP.cash_leg_from_registry(default_registry(), "BOK_CALL_RATE", rates={})
    assert isinstance(leg, MissingInput) and leg.role == "history" and leg.detail.startswith("OWNER:")
    raise NotRun(leg.detail)


test_excess_01_bok_call_rate_ecos_code_is_owner_input.test_ids = ["T-EXCESS-01"]


def test_excess_01_px2_reproduction_refdata():
    require_fixture("px2_cash_IRSTCI01KRM156N_monthly.csv")
    raise AssertionError("fixture listed: golden assertion not implemented")


test_excess_01_px2_reproduction_refdata.test_ids = ["T-EXCESS-01"]


# --------------------------------------------------------------------------- #
# T-BAND-01: band shapes, integer floor, midpoint halves, regime lines
# --------------------------------------------------------------------------- #
def test_band_01_shapes_floor_and_midpoint():
    kr = CP.start_band("R-06_KR", history_start=date(1997, 4, 1), span_end=date(2026, 10, 2))
    assert len(kr) == 32 and kr[0] == date(1997, 5, 1) and kr[-1] == date(1999, 12, 1)
    _raises(lambda: CP.start_band("R-06_KR", history_start=date(1997, 5, 1), span_end=date(2026, 10, 2)), CP.CardRefused, "1997-04-01")
    floor = CP.stability_floor("R-06_KR", ["PASS"] * 22 + ["INSUFFICIENT_DATA"] * 10, ["PASS", "PASS"])
    assert floor["floor_pass"] and floor["min_pass"] == 22
    assert not CP.stability_floor("R-06_KR", ["PASS"] * 21 + ["INSUFFICIENT_DATA"] * 11, ["PASS", "PASS"])["floor_pass"]
    one_reject = CP.stability_floor("R-06_KR", ["PASS"] * 31 + ["REJECT"], ["PASS", "PASS"])
    assert not one_reject["floor_pass"] and one_reject["reason"] == "reject_at_start"      # even with share >= 2/3
    half = CP.stability_floor("R-06_KR", ["PASS"] * 32, ["PASS", "REJECT"])
    assert not half["floor_pass"] and half["reason"] == "reject_in_half"
    split, h1, h2 = CP.midpoint_halves(date(1997, 4, 1), date(2026, 10, 2))
    assert split == date(2012, 1, 1) and h1 == (date(1997, 4, 1), split) and h2 == (split, date(2026, 10, 2))
    dec = CP.start_band("decade_spaced", history_start=date(1926, 7, 1), span_end=date(2026, 8, 31))
    assert len(dec) == 10 and dec[0] == date(1926, 7, 1) and dec[1] == date(1930, 1, 1) and dec[-1] == date(2010, 1, 1)
    assert CP.stability_floor("decade_spaced", ["PASS"] * 8 + ["REVISE"] * 2, ["PASS", "PASS"])["floor_pass"]
    assert not CP.stability_floor("decade_spaced", ["PASS"] * 7 + ["REVISE"] * 3, ["PASS", "PASS"])["floor_pass"]
    _raises(lambda: CP.start_band("decade_spaced", history_start=date(1990, 1, 1), span_end=date(2026, 8, 31)), CP.CardRefused, "80 years")
    dflt = CP.start_band("default", history_start=date(1990, 1, 2), span_end=date(2026, 10, 1))
    assert len(dflt) == 33 and dflt[0] == date(1990, 1, 1) and dflt[-1] == date(1992, 9, 1)
    sessions = _bdays(date(1997, 4, 1), 900)
    kr_s = CP.start_band("R-06_KR", history_start=date(1997, 4, 1), span_end=date(2026, 10, 2), sessions=sessions)
    assert kr_s[0] == date(1997, 5, 1) and kr_s[1] == date(1997, 6, 2) and all(d in sessions for d in kr_s)
    lines = CP.regime_lines("KR", date(1997, 4, 1), date(2026, 10, 2), primary_oos_line="etf_era")
    gated = [x["line"] for x in lines if x["gated"]]
    assert gated == ["etf_era"] and {x["line"] for x in lines} == {"pre_etf", "etf_era", "limits_30pct", "pre_design"}
    assert next(x for x in lines if x["line"] == "pre_design")["span"] == (date(2002, 10, 14), date(2015, 12, 31))
    _raises(lambda: CP.regime_lines("KR", date(1997, 4, 1), date(2026, 10, 2), primary_oos_line="2016_plus"), CP.CardRefused, "not a regime line")
    # the stability cap inside the evaluator: a REJECT at one band start caps a PASS at INSUFFICIENT_DATA
    v = CP.line_verdict(_checks(caps={"stability": True}), 1.0)
    assert (v["verdict"], v["reason"]) == ("INSUFFICIENT_DATA", "stability")
    # rule 6: a flipped card-book convention is refused; R-31's claim may include the hard stop
    _raises(lambda: CP.check_card_book_convention({"card_books": {"hard_stop": True, "caps": False}}), CP.CardRefused, "rule 6")
    CP.check_card_book_convention({"card_books": {"hard_stop": True, "caps": False}, "claim_concerns": ["hard_stop"]})


test_band_01_shapes_floor_and_midpoint.test_ids = ["T-BAND-01"]


# --------------------------------------------------------------------------- #
# T-PLACEBO-01 / T-PLACEBO-02 / T-LAG-01 / T-LAG-02: timing profile, probe, control, ledger rows
# --------------------------------------------------------------------------- #
def test_placebo_01_fragility_arithmetic_and_synthetic_lookahead_control():
    # FR from the printed QF2 grid (L3469-3474): R-12 flagged, R-03 passes, control LP 0.282
    lf, fr, fragile = CP.fragility(0.038, 0.010)
    assert abs(fr - 0.737) < 0.002 and fragile
    assert not CP.fragility(0.314, 0.306)[2] and abs(CP.fragility(0.314, 0.306)[1] - 0.025) < 0.002
    assert CP.fragility(0.081, 0.085)[2] is False                      # R-04 flat
    lf, fr, frag = CP.fragility(-0.01, 0.02)                            # dSR[1] <= 0: FR printed n/m; the sign flip decides
    assert abs(lf + 0.03) < 1e-12 and fr is None and frag and CP.fragility(0.02, -0.01)[2]
    assert CP.fragility(0.02, 0.0) == (0.02, 1.0, True) and not CP.fragility(0.0, 0.0)[2]
    assert 0.317 - 0.035 >= CP.LP_MIN
    ctl = _control()
    assert ctl["tripped"] and ctl["LP"] >= 0.20 and ctl["L0"] > ctl["L1"]
    # every lag tried is a family-ledger row (temp copy), L <= 0 as NON-COMPLIANT
    r = regime_returns(seed=5, n_cycles=3)
    sign_rule = np.where(r > 0, 1.0, 0.5)
    rows = []
    prof = CP.timing_probe({"card_id": "LEAK", "family_id": "CTRL", "config": {"rule": "same_day_sign"}},
                           lambda L: books_at(r, sign_rule, L, 0.0), sandbox=True, B=50, seed=SEED,
                           ledger_append=lambda fid, row: rows.append((fid, row)),
                           strict_fn=lambda: books_at(r, sign_rule, 1, 0.0))
    assert [row["lag"] for _, row in rows] == [1, 2, 3, -1, 0, "strict"]
    assert all(row["timing_class"] == ("NON-COMPLIANT" if isinstance(row["lag"], int) and row["lag"] <= 0 else "COMPLIANT")
               for _, row in rows)
    assert prof["synthetic_lookahead"] and prof["lag_audit_violations"] == 0
    look = [x for x in prof["lags"] if x["L"] <= 0]
    assert len(look) == 2 and all(x["lag_audit"]["recorded_not_raised"] and x["lag_audit"]["violations"] == 1 for x in look)
    # the honest profile of a robust rule: no look-ahead rows, no LP, label robust, FR interval printed
    vt = vt_decided(regime_returns())
    hp = CP.timing_profile({"card_id": "SYN", "family_id": "R-06", "config": {"rule": "vt"}},
                           lambda L: books_at(regime_returns(), vt, L), B=50, seed=SEED)
    assert [x["L"] for x in hp["lags"]] == [1, 2, 3] and hp["LP"] is None and hp["label"] == "robust" and not hp["probe"]
    assert hp["FR_ci90"] is None or len(hp["FR_ci90"]) == 2
    _raises(lambda: CP.timing_profile({"family_id": "R-06"}, lambda L: books_at(regime_returns(), vt, L), B=50, seed=SEED,
                                      reported_dsr=hp["lags"][0]["dSR"] + 0.01), CP.CardRefused, "reported dSR")


test_placebo_01_fragility_arithmetic_and_synthetic_lookahead_control.test_ids = ["T-PLACEBO-01"]


def test_placebo_01_noise_overlay_family_passes_pc1_rarely():
    """A pure-noise overlay passes PC-1' in <= 10% of 300 circular shifts; the attempt is logged to a temp path."""
    rng = np.random.default_rng(SEED)
    r = regime_returns(seed=3, n_cycles=3)
    noise_m = rng.uniform(0.5, 1.0, r.size)
    fam = {"R-SYN": [{"card_id": "SYN-NOISE", "m": noise_m, "x_off": r, "cost_bp": 3.0, "f": 1.0, "draft_md5": "0" * 32}]}
    controls = {c: "REJECT" for c in CP.NEGATIVE_CONTROLS}
    with tempfile.TemporaryDirectory() as tmp:
        log = Path(tmp) / "gate" / "acceptance_runs.jsonl"
        res = CP.gate_acceptance_test("2.0.0", fam, controls, SEED, 30, log, run_utc="2026-10-06T00:00:00Z")
        assert res.passed and res.per_family_placebo_pass_rate["R-SYN"]["n"] == 300
        assert res.per_family_placebo_pass_rate["R-SYN"]["rate"] <= 0.10 and res.per_card_pass_counts["SYN-NOISE"] <= 2
        rows = CP.attempts(log)
        assert len(rows) == 1 and rows[0]["counts_as"] == "package_trial" and rows[0]["outcome"] == "pass"
    panel = CP.placebo_panel(noise_m, r, 3.0, 1.0, B=30, seed=SEED)
    assert panel["n"] == 20 and panel["passes"] <= 2 and panel["taus"][0] == 252 and panel["taus"][-1] == r.size - 252
    prod = config.macro_dir() / "gate" / "acceptance_runs.jsonl"
    assert not prod.exists() or prod.stat().st_size == 0, "the production attempts log must stay empty until the real attempt"


test_placebo_01_noise_overlay_family_passes_pc1_rarely.test_ids = ["T-PLACEBO-01"]


def test_placebo_01_positive_control_fixture_refdata():
    require_fixture("KR_SOX_KRW_gate_B3.csv")
    raise AssertionError("fixture listed: golden assertion not implemented")


test_placebo_01_positive_control_fixture_refdata.test_ids = ["T-PLACEBO-01"]


def _static_names(path: Path, needles) -> dict[str, list[str]]:
    hits = {}
    for py in sorted(path.rglob("*.py")):
        if "__pycache__" in py.parts:
            continue
        tree = ast.parse(py.read_text(encoding="utf-8"), filename=str(py))
        for node in ast.walk(tree):
            name = getattr(node, "id", None) or getattr(node, "attr", None)
            if isinstance(node, ast.ImportFrom) and node.module and "cardp" in node.module:
                name = "import:cardp"
            if isinstance(node, ast.Import) and any("cardp" in a.name for a in node.names):
                name = "import:cardp"
            if name in needles:
                hits.setdefault(name, []).append(py.relative_to(ROOT).as_posix())
    return hits


def test_placebo_02_probe_isolation():
    # static: timing_probe and its private runner referenced in cardp.py only; no core/engine|ficc|skills|ui import
    hits = _static_names(CORE, {"timing_probe", "_run_lagged", "_PROBE", "import:cardp"})
    assert set(hits.get("timing_probe", [])) <= {"core/quant/cardp.py"} and set(hits.get("_run_lagged", [])) <= {"core/quant/cardp.py"}
    assert all(not f.startswith(("core/engine", "core/ficc", "core/skills")) for f in hits.get("import:cardp", []))
    assert not _static_names(ROOT / "ui", {"import:cardp", "timing_probe"})
    # inside cardp.py, _run_lagged is called from timing_profile only; no verdict path reads a placebo result
    tree = ast.parse((CORE / "quant" / "cardp.py").read_text(encoding="utf-8"))
    callers = {fn.name for fn in ast.walk(tree) if isinstance(fn, ast.FunctionDef)
               for n in ast.walk(fn) if isinstance(n, ast.Call) and getattr(n.func, "id", "") == "_run_lagged"}
    assert callers == {"timing_profile"}, callers
    for fn in (f for f in ast.walk(tree) if isinstance(f, ast.FunctionDef) and f.name in ("cardp_evaluate", "line_verdict", "combine_card_verdict")):
        names = {getattr(n, "id", None) or getattr(n, "attr", None) for n in ast.walk(fn)}
        assert not any(x and ("placebo" in x or "acceptance" in x or x == "roll") for x in names), fn.name
    # runtime: the probe needs sandbox=True, a tests/ or docs/ caller and no runtime frame on the stack
    r = regime_returns(seed=5, n_cycles=2)
    vt = vt_decided(r)
    card = {"card_id": "SYN", "family_id": "R-06", "config": {"rule": "vt"}}
    _raises(lambda: CP.timing_probe(card, lambda L: books_at(r, vt, L), sandbox=False, B=20, seed=SEED), CP.TimingProbeForbidden, "sandbox")
    _raises(lambda: CP._run_lagged(lambda L: books_at(r, vt, L), 0), CP.TimingProbeForbidden, "look-ahead")
    ns = {"CP": CP, "books_at": books_at, "r": r, "vt": vt, "card": card, "SEED": SEED}
    code = compile("def abuse():\n    return CP.timing_probe(card, lambda L: books_at(r, vt, L), sandbox=True, B=20, seed=SEED)\n",
                   str(ROOT / "core" / "engine" / "_probe_abuse.py"), "exec")
    exec(code, ns)
    _raises(ns["abuse"], CP.TimingProbeForbidden, "runtime")
    code = compile("def builder():\n    return CP.timing_probe(card, lambda L: books_at(r, vt, L), sandbox=True, B=20, seed=SEED)\n",
                   str(ROOT / "core" / "quant" / "sleeves.py"), "exec")
    exec(code, ns)
    _raises(ns["builder"], CP.TimingProbeForbidden, "tests/ or docs/")
    # a card whose statistics read an L <= 0 row is refused; probe output is tagged and lands outside the production dir
    with tempfile.TemporaryDirectory() as tmp:
        old = os.environ.get("QUANTGEN_MACRO_DIR")
        os.environ["QUANTGEN_MACRO_DIR"] = str(Path(tmp) / "prod")
        try:
            prof = CP.timing_probe(card, lambda L: books_at(r, vt, L), sandbox=True, B=20, seed=SEED, out_dir=Path(tmp) / "probe")
            assert prof["synthetic_lookahead"] and prof["LP"] is not None and prof["lags"][3]["L"] == -1
            written = json.loads(Path(prof["path"]).read_text(encoding="utf-8"))
            assert written["synthetic_lookahead"] and not (Path(tmp) / "prod").exists()
            _raises(lambda: CP.timing_probe(card, lambda L: books_at(r, vt, L), sandbox=True, B=20, seed=SEED, out_dir=Path(tmp) / "prod" / "x"),
                    CP.TimingProbeForbidden, "production artifact directory")
        finally:
            if old is None:
                os.environ.pop("QUANTGEN_MACRO_DIR", None)
            else:
                os.environ["QUANTGEN_MACRO_DIR"] = old
    leaked = CP._run_lagged.__wrapped__ if hasattr(CP._run_lagged, "__wrapped__") else None
    assert leaked is None
    probe_books = CP.Books(np.zeros(3), np.zeros(3), np.zeros(3), np.ones(3), (date(2020, 1, 1),) * 3, synthetic_lookahead=True)
    _raises(lambda: CP.cardp_evaluate(probe_books.on, probe_books.off, probe_books.S, _header(), 1.0, SEED, 20, books=probe_books),
            CP.CardRefused, "synthetic_lookahead")
    # a missing or untripped positive control blocks every card run; a card without a timing profile is refused
    b = books_at(r, vt, 1)
    kw = dict(m=b.m, dates=b.dates, eps=[], power={"mde80": 0.05})
    _raises(lambda: CP.cardp_evaluate(b.on, b.off, b.S, _header(), 1.0, SEED, 20, timing={}, control=None, **kw), CP.CardRefused, "positive control")
    _raises(lambda: CP.cardp_evaluate(b.on, b.off, b.S, _header(), 1.0, SEED, 20, timing={}, control={"tripped": False}, **kw), CP.CardRefused, "blocked")
    _raises(lambda: CP.cardp_evaluate(b.on, b.off, b.S, _header(), 1.0, SEED, 20, timing=None, control={"tripped": True}, **kw), CP.CardRefused, "timing profile")
    _raises(lambda: CP.cardp_evaluate(b.on, b.off, b.S, _header(selection_factor=1.3), 1.0, SEED, 20, timing={}, control={"tripped": True}, **kw),
            CP.CardRefused, "selection_factor")
    assert not CP.lookahead_positive_control({"LP": None})["tripped"]
    assert not CP.lookahead_positive_control({"LP": 0.1, "synthetic_lookahead": True, "lags": []})["tripped"]


test_placebo_02_probe_isolation.test_ids = ["T-PLACEBO-02", "T-LAG-01", "T-LAG-02"]


# --------------------------------------------------------------------------- #
# T-GATE-04: bounded redesign and the attempts log on a synthetic failing panel
# --------------------------------------------------------------------------- #
def _periodic_family() -> dict:
    """T = 504: every tau collapses to 252, and a period-252 calendar rule realigns under the shift, so every
    placebo passes PC-1' by construction (the panel fails rule 9(a))."""
    rng = np.random.default_rng(SEED)
    half = np.concatenate([rng.normal(0.0005, 0.005, 126), rng.normal(-0.004, 0.03, 126)])
    r = np.concatenate([half, half + rng.normal(0, 0.0005, 252)])
    m = np.tile(np.concatenate([np.ones(126), np.full(126, 0.5)]), 2)
    return {"R-PER": [{"card_id": "PER-01", "m": m, "x_off": r, "cost_bp": 3.0, "f": 1.0, "draft_md5": "a" * 32}]}


def test_gate_04_second_failure_ends_evaluation_and_every_attempt_is_logged():
    fam, controls = _periodic_family(), {c: "REJECT" for c in CP.NEGATIVE_CONTROLS}
    paged = []
    with tempfile.TemporaryDirectory() as tmp:
        log, gov = Path(tmp) / "gate" / "acceptance_runs.jsonl", Path(tmp) / "governance_events.jsonl"
        kw = dict(seed=SEED, B=30, log_path=log, governance_log=gov, page_owner=paged.append)
        a1 = CP.gate_acceptance_test("2.0.0", fam, controls, run_utc="2026-10-06T01:00:00Z", **kw)
        assert not a1.passed and a1.reason == "placebo_family_excess" and a1.redesign_allowed and a1.attempt_no == 1
        assert a1.per_family_placebo_pass_rate["R-PER"]["rate"] > 0.10 and a1.per_card_pass_counts["PER-01"] > 2
        assert not gov.exists() and paged == []                                  # nothing frozen, no event yet
        good = {"diff": ["card_p_v2.pc1_prime.mean_block_sessions"], "seeds": {"placebo": 12, "controls": 12},
                "seeds_logged_utc": "2026-10-06T01:30:00Z",
                "rationale": "per-family panels showed excess false passes; negative controls unchanged"}
        # refused redesigns: no record; a diff outside the frozen-items table; a named card; seeds logged after the run; stale seeds
        _raises(lambda: CP.gate_acceptance_test("2.0.0", fam, controls, run_utc="2026-10-06T02:00:00Z", **kw), CP.AcceptanceRefused, "redesign record")
        _raises(lambda: CP.gate_acceptance_test("2.0.0", fam, controls, run_utc="2026-10-06T02:00:00Z", redesign={**good, "diff": ["costs.krx_etf"]}, **kw),
                CP.AcceptanceRefused, "frozen-items")
        _raises(lambda: CP.gate_acceptance_test("2.0.0", fam, controls, run_utc="2026-10-06T02:00:00Z",
                                                redesign={**good, "rationale": good["rationale"] + " PER-01"}, **kw), CP.AcceptanceRefused, "names a card")
        _raises(lambda: CP.gate_acceptance_test("2.0.0", fam, controls, run_utc="2026-10-06T02:00:00Z",
                                                redesign={**good, "seeds_logged_utc": "2026-10-06T02:30:00Z"}, **kw), CP.AcceptanceRefused, "before the run")
        _raises(lambda: CP.gate_acceptance_test("2.0.0", fam, controls, run_utc="2026-10-06T02:00:00Z",
                                                redesign={**good, "seeds": {"placebo": SEED, "controls": SEED}}, **kw), CP.AcceptanceRefused, "fresh")
        assert len(CP.attempts(log)) == 1                                        # refusals are not attempts
        a2 = CP.gate_acceptance_test("2.0.0", fam, controls, run_utc="2026-10-06T02:00:00Z", redesign=good, **kw)
        assert not a2.passed and a2.attempt_no == 2 and not a2.redesign_allowed
        rows = CP.attempts(log)
        assert [x["outcome"] for x in rows] == ["fail", "fail"] and rows[1]["redesign"]["seeds"] == good["seeds"]
        assert rows[1]["prev_row_md5"] is not None and rows[0]["prev_row_md5"] is None
        ev = governance.read_events(gov)
        assert len(ev) == 1 and ev[0]["kind"] == "package_redesign" and ev[0]["actor"] == "harness" and governance.verify_chain(gov).ok
        assert paged and "no card" in paged[0]
        # a third attempt is refused, also after a 2.x bump; nothing was logged for it
        _raises(lambda: CP.gate_acceptance_test("2.1.0", fam, controls, run_utc="2026-10-07T00:00:00Z", redesign=good, **kw),
                CP.AcceptanceRefused, "no_card_evaluated_under_v2")
        assert len(CP.attempts(log)) == 2
        # a hand-edited row breaks the chain and the log is refused
        lines = log.read_bytes().split(b"\n")
        lines[0] = lines[0].replace(b'"outcome":"fail"', b'"outcome":"pass"')
        log.write_bytes(b"\n".join(lines))
        _raises(lambda: CP.attempts(log), CP.AcceptanceRefused, "hash chain")
    # negative controls: a missing control fails closed; a D6 rule outside the options is refused
    with tempfile.TemporaryDirectory() as tmp:
        log = Path(tmp) / "a.jsonl"
        _raises(lambda: CP.gate_acceptance_test("2.0.0", fam, {"US_VT_5d_50bp": "REJECT"}, SEED, 30, log, run_utc="2026-10-06T00:00:00Z"),
                CP.AcceptanceRefused, "negative controls not supplied")
        _raises(lambda: CP.gate_acceptance_test("2.0.0", fam, controls, SEED, 30, log, run_utc="2026-10-06T00:00:00Z", d6_rule="fixed_margin"),
                CP.AcceptanceRefused, "D6")
        assert not log.exists()
    # D6: the lowest-placebo-false-pass rule with the tie rule; fails closed when no candidate tames every control
    tame = {c: "REJECT" for c in CP.NEGATIVE_CONTROLS}
    cands = {"professors_bootstrap_one_sided_5pct": {"placebo_false_pass_rate": 0.06, "controls": tame},
             "executives_placebo_p10_margin": {"placebo_false_pass_rate": 0.04, "controls": tame},
             "qf_blind_margin": {"placebo_false_pass_rate": 0.04, "controls": {**tame, "VT_sigma_lag_252": "PASS"}}}
    assert CP.cdar_guard_default_rule(cands) == "executives_placebo_p10_margin"
    cands["professors_bootstrap_one_sided_5pct"]["placebo_false_pass_rate"] = 0.04
    assert CP.cdar_guard_default_rule(cands) == "professors_bootstrap_one_sided_5pct"          # ties -> Professors
    _raises(lambda: CP.cdar_guard_default_rule({k: {"placebo_false_pass_rate": 0.01, "controls": {**tame, "US_VT_5d_50bp": "PASS"}} for k in cands}),
            CP.AcceptanceRefused, "no candidate")
    # a control that would pass is tamed by the recorded D6 guard; otherwise the attempt fails on the control
    noise_fam = {"R-N": [{"card_id": "N-01", "m": np.random.default_rng(1).uniform(0.5, 1, 1200), "x_off": regime_returns(seed=2, n_cycles=3)[:1200],
                          "cost_bp": 3.0, "f": 1.0}]}
    with tempfile.TemporaryDirectory() as tmp:
        bad = {**controls, "post_shock_week_0p5": "PASS"}
        res = CP.gate_acceptance_test("2.0.0", noise_fam, bad, SEED, 20, Path(tmp) / "x.jsonl", run_utc="2026-10-06T00:00:00Z")
        assert not res.passed and res.reason == "negative_control_passed" and res.cdar_guard is None
        res2 = CP.gate_acceptance_test("2.0.0", noise_fam, bad, SEED, 20, Path(tmp) / "y.jsonl", run_utc="2026-10-06T00:00:00Z",
                                       cdar_candidates=cands)
        assert res2.passed and res2.cdar_guard == "professors_bootstrap_one_sided_5pct" and res2.controls["post_shock_week_0p5"] == "REJECT"


test_gate_04_second_failure_ends_evaluation_and_every_attempt_is_logged.test_ids = ["T-GATE-04"]


# --------------------------------------------------------------------------- #
# I-05 (synthetic end to end): planted protective overlay PASSes, a noise overlay does not
# --------------------------------------------------------------------------- #
def test_i05_synthetic_end_to_end_protective_passes_noise_does_not():
    r = regime_returns()
    ctl = _control()
    assert ctl["tripped"]
    vt = vt_decided(r)
    res = _evaluate(r, vt, control=ctl, neighbours=_neighbours(r), f=1.2)
    assert res.verdict == "PASS", (res.verdict, res.reason_code, res.pc1_prime, res.pc3, res.pc4, res.pc5, res.pc6)
    assert res.verdict_at_f1 == "PASS" and res.verdict_at_f_neff == "PASS" and res.f == 1.2
    assert all(leg["pass"] for leg in res.pc1_prime["legs"]) and res.pc2["pass"] and res.pc3["pass"] and res.pc4["pass"]
    assert res.pc7["pass"] and res.pc7["n_episodes"] >= 5 and res.pc6["pass"] and not res.do_no_harm
    assert res.printed["dES99"] > 0 and res.printed["dMDD"] > 0 and set(res.printed["bands"]) == {"dMDD", "dCDaR95", "dES99"}
    assert res.timing["label"] == "robust" and res.caps_applied == () and res.permitted_fix is None
    assert res.pc3["p_form"] in ("lw_studentized", "percentile_interim") and res.pc3["block_PW"] >= 21
    assert all(leg["p"] > 0 for leg in res.pc1_prime["legs"])           # no card field holds p = 0
    assert len(res.printed["post_trough"]) == len(res.episodes) and res.printed["gjr_null_pct"] is None
    noise = np.random.default_rng(SEED).uniform(0.5, 1.0, r.size)
    res_n = _evaluate(r, noise, control=ctl)
    assert res_n.verdict != "PASS" and res_n.verdict in CP.VERDICTS, (res_n.verdict, res_n.reason_code)
    # selection factor only lowers: a large f turns the planted PASS into INSUFFICIENT_DATA, never a REJECT
    res_f = _evaluate(r, vt, control=ctl, neighbours=None, f=50.0)
    assert res_f.verdict == "INSUFFICIENT_DATA" and res_f.verdict_at_f1 == "PASS" and res_f.reason_code in ("inconclusive", "underpowered")
    # the stability cap through `band`
    b = books_at(r, vt, 1)
    dates, closes = closes_of(r)
    eps = CP.episodes(closes, dates)
    prof = CP.timing_profile({"family_id": "R-06", "config": {}}, lambda L: books_at(r, vt, L), B=50, seed=SEED)
    res_b = CP.cardp_evaluate(b.on, b.off, b.S, _header(), 1.0, SEED, B, m=b.m, dates=b.dates, on_2x=b.on_2x, eps=eps, timing=prof,
                              control=ctl, power=POWER, band={"shape": "R-06_KR", "verdicts": ["PASS"] * 31 + ["REJECT"], "halves": ["PASS", "PASS"]})
    assert res_b.verdict == "INSUFFICIENT_DATA" and res_b.reason_code == "stability" and "stability" in res_b.caps_applied
    # reproducibility: same seed, same outputs bit for bit
    legs_a = CP.pc1_prime(b.on, b.S, f=1.0, B=B, seed=SEED)
    legs_b = CP.pc1_prime(b.on, b.S, f=1.0, B=B, seed=SEED)
    assert legs_a == legs_b


test_i05_synthetic_end_to_end_protective_passes_noise_does_not.test_ids = ["I-05"]


def test_i05_full_sample_lag_audit_over_compliant_goldens_refdata():
    raise NotRun("REFDATA: every COMPLIANT golden backtest fixture of section 9.3 (KOSPI 1997-2026 official closes, "
                 "French daily files, FRED H.15 / H.10 vintages) is absent; the independent lag audit cannot run")


test_i05_full_sample_lag_audit_over_compliant_goldens_refdata.test_ids = ["I-05"]


# --------------------------------------------------------------------------- #
# Freeze-tier and post-freeze ids: refused here with their reason (never faked)
# --------------------------------------------------------------------------- #
def test_i08_acceptance_test_on_the_frozen_reference_data_refdata():
    raise NotRun(REFDATA + "; owner inputs sleeves.<market>.notional_nav and the BOK_CALL_RATE ECOS code are null; "
                 "the folder is not a git repository (no external anchor): the freeze is refused")


test_i08_acceptance_test_on_the_frozen_reference_data_refdata.test_ids = ["I-08"]


def test_gate_01_placebo_counts_and_controls_refdata():
    raise NotRun(REFDATA)


test_gate_01_placebo_counts_and_controls_refdata.test_ids = ["T-GATE-01"]


def test_gate_03_negative_controls_in_detail_refdata():
    raise NotRun(REFDATA + " (5-day dSR -0.29, 10-day -0.106, post-shock-week z 1.278 are printed, never asserted)")


test_gate_03_negative_controls_in_detail_refdata.test_ids = ["T-GATE-03"]


def test_epis_02_pc4_on_the_korea_definitive_cell_refdata():
    raise NotRun("REFDATA: KOSPI 1997-04..2026-10-02 official closes (14 of 18 positive, max share 0.174; after the freeze)")


test_epis_02_pc4_on_the_korea_definitive_cell_refdata.test_ids = ["T-EPIS-02"]


def test_trough_01_post_trough_and_cost_episodes_refdata():
    raise NotRun("REFDATA: KOSPI 1997-2026 official closes (-6.9 / -15.5 / -31.5 pp vs S; after the freeze)")


test_trough_01_post_trough_and_cost_episodes_refdata.test_ids = ["T-TROUGH-01"]


def test_es_02_korea_long_history_es_lines_refdata():
    raise NotRun("REFDATA: KOSPI 1997-2026 official closes with the R4b raw-return flag (dES99 +1.95 pp, dES95_21 +2.9 pp, "
                 "dCDaR95 +7.1 pp; after the freeze; z values in reference mode only)")


test_es_02_korea_long_history_es_lines_refdata.test_ids = ["T-ES-02"]


def test_rlayer_01_card_book_convention_refdata():
    _raises(lambda: CP.check_card_book_convention({"card_books": {"hard_stop": False, "caps": True}}), CP.CardRefused, "rule 6")
    raise NotRun("REFDATA: KOSPI 1997-2026 official closes (with_risk_layer line: 24 HALTs, MDD -56.4% vs -45.3%; after the freeze)")


test_rlayer_01_card_book_convention_refdata.test_ids = ["T-RLAYER-01"]


# --------------------------------------------------------------------------- #
# Harness invariants: no wall clock, no store writes, every statistic explicit about seeds and B
# --------------------------------------------------------------------------- #
def test_cardp_static_invariants():
    src = (CORE / "quant" / "cardp.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    calls = {ast.unparse(n.func) for n in ast.walk(tree) if isinstance(n, ast.Call)}
    assert not any(c.endswith(("datetime.now", "time.time", "date.today", "utcnow")) for c in calls), calls
    assert "GATE[" not in src and "bootstrap_B" not in src                       # never reads validate.GATE
    forbidden = ("order_cash", "place_order", "submit_order", "/v1/orders", "withdraw")
    assert not any(f in src for f in forbidden)
    assert "(M - 1)" not in src and "kish" not in src.lower()                    # no Kish trial count (P13)
    # seeds and B are parameters of every bootstrap entry point
    for name in ("pc1_prime", "pc2", "pc3_noninferiority", "printed_lines", "placebo_passes", "timing_profile", "gate_acceptance_test"):
        fn = next(f for f in ast.walk(tree) if isinstance(f, ast.FunctionDef) and f.name == name)
        args = {a.arg for a in fn.args.args + fn.args.kwonlyargs}
        assert {"B", "seed"} <= args, name
    assert CP.MEAN_BLOCK == 250 and CP.HORIZONS == (21, 126) and CP.FR_MAX == 0.5 and CP.LP_MIN == 0.20
    assert CP.PLACEBO_PER_FAMILY == 300 and CP.PLACEBO_PER_CARD == 20 and CP.PLACEBO_CARD_MAX == 2
    assert CP.GATE_CFG["package"]["status"] == "NOT_FROZEN"


def test_line_episodes_nan_fail_closed_pc3_event_log_and_one_attempts_chain():
    """(1) PC-7 / PC-4 count only the closed episodes inside the evaluated line (brief F-12, spec L5092); (2) a NaN
    statistic fails closed in line_verdict; (3) PC-3 keeps the L2620 fallback event and the real degenerate cause;
    (4) the attempts log is read through the cards hash chain (canonical bytes, ATTEMPT_ROW), as gate_package does."""
    from core.quant import cards
    r = regime_returns()
    vt = vt_decided(r)
    b = books_at(r, vt, 1)
    dates, closes = closes_of(r)
    eps = CP.episodes(closes, dates, threshold=0.20)
    cut = int(0.6 * r.size)
    prof = CP.timing_profile({"family_id": "R-06", "config": {}}, lambda L: books_at(r, vt, L), B=50, seed=SEED)
    res = CP.cardp_evaluate(b.on[cut:], b.off[cut:], b.S[cut:], _header(), 1.0, SEED, 50, m=b.m[cut:], dates=b.dates[cut:],
                            eps=eps, timing=prof, control=_control(), power=POWER)
    inside = CP.closed_in_span(eps, b.dates[cut], b.dates[-1])
    assert res.pc7["n_episodes"] == res.pc4["n"] == len(inside) < len(CP.closed_in_span(eps))
    nan = float("nan")
    assert CP.line_verdict(_checks(pc2={"ratio_used": nan}), 1.0)["verdict"] == "REJECT"
    assert CP.line_verdict(_checks(pc3={"dSR": nan, "p_ni": 0.03, "point_2x": 0.02}), 1.0)["verdict"] == "REJECT"
    a = np.random.default_rng(SEED).normal(0.0, 0.01, 600)
    p3 = CP.pc3_noninferiority(a, np.zeros(600), f=1.0, B=50, seed=SEED)
    assert p3["block_PW"] == 250 and p3["block_log"][0]["event"] == "pw_block_psi_fallback" and not p3["pass"]
    assert p3["p_form"] == "degenerate" and "zero variance" in p3["detail"]
    with tempfile.TemporaryDirectory() as tmp:
        log = Path(tmp) / "acceptance_runs.jsonl"
        cards.chain_append(log, {"attempt_no": 1, "package_version": "2.0.0", "outcome": "fail"})
        assert [x["outcome"] for x in CP.attempts(log)] == ["fail"]
        log.write_bytes(log.read_bytes().replace(b'"outcome":"fail"', b'"outcome": "fail"'))      # same row, reformatted
        _raises(lambda: CP.attempts(log), CP.AcceptanceRefused, "hash chain")
        log.write_bytes(b"")
        cards.chain_append(log, {"attempt_no": 1, "package_version": "2.0.0"})                    # no outcome field
        _raises(lambda: CP.attempts(log), CP.AcceptanceRefused, "hash chain")


test_line_episodes_nan_fail_closed_pc3_event_log_and_one_attempts_chain.test_ids = []


if __name__ == "__main__":
    from tests.macro_acceptance import run_module
    raise SystemExit(run_module(globals()))
