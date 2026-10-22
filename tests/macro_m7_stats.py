"""M7 package A tests: the R-24 statistics and power harness (TASK-M7-06, TASK-M7-07; core/quant/gate_stats.py).

Spec tests: T-SE-01, T-POWER-01, T-POWER-02, T-UNDERPOW-01, T-PZERO-01, T-PBO-01, T-DSR-01, T-DSR-02 and the
bootstrap half of T-REPRO-01b. Every numeric clause that needs reference data (French Mom F10, U1, KOSPI F13) is
NOT_RUN naming its fixture; the SYNTH clauses run on seeded synthetic panels only (seed 11; small B). Nothing here
reads a card result, writes a file or touches the real macro_dir; gate/acceptance_runs.jsonl stays empty.
"""
from __future__ import annotations

import ast
import json
import math
from pathlib import Path

import numpy as np
from scipy import stats as sps

from core.quant import gate_stats as GS
from core.quant import validate as V
from tests.macro_m2_costed import _refdata
from tests.notrun import NotRun

ROOT = Path(__file__).resolve().parents[1]
STORE = ROOT / "data" / "macro" / "rules_v2.0.0.json"
SEED = 11


def _raises(fn, exc, needle: str = "") -> None:
    try:
        fn()
    except exc as e:
        assert needle in str(e), f"{exc.__name__} without {needle!r}: {e}"
        return
    raise AssertionError(f"{exc.__name__} not raised")


def _ar1(rng, T: int, phi: float, sd: float, mean: float = 0.0) -> np.ndarray:
    e = rng.normal(0.0, sd, T)
    x = np.empty(T)
    x[0] = e[0]
    for t in range(1, T):
        x[t] = phi * x[t - 1] + e[t]
    return x + mean


def _clustered_books(rng, T: int = 3000):
    """A GARCH-like market path and a 0.5x de-risked copy above 20% vol: paired books with vol clustering."""
    e = rng.standard_normal(T)
    s2 = np.empty(T)
    s2[0] = 1e-4
    for t in range(1, T):
        s2[t] = 2e-6 + 0.08 * e[t - 1] ** 2 * s2[t - 1] + 0.90 * s2[t - 1]
    x = np.sqrt(s2) * e + 0.0003
    return x, np.where(np.sqrt(s2 * 252) > 0.20, 0.5, 1.0) * x


# --------------------------------------------------------------------------- #
# T-SE-01: the SE ladder (SYNTH clauses; the R-03 numbers are REFDATA)
# --------------------------------------------------------------------------- #
def test_se01_hac_white_noise_and_ar_ladder():
    """White noise: the LW-HAC SE (QS, Andrews) sits within 5% of the iid long-run form sqrt((2 + (SR_a^2 + SR_b^2)/2)/T)
    and the Bartlett NW10 line is printed beside it; AR(1) psi: the QS LRV is within 10% of var x (1+phi)/(1-phi);
    on books with an autocorrelated mean the ladder rises with the block length, se_plateau is the maximum of every
    entry (HAC included) and T/b is printed."""
    rng = np.random.default_rng(SEED)
    T = 20000
    a, b = rng.normal(0.0004, 0.01, T), rng.normal(0.0002, 0.01, T)
    hac = GS.lw_hac_se(a, b)
    sr_a, sr_b = V.sharpe(a) / math.sqrt(252), V.sharpe(b) / math.sqrt(252)
    iid = math.sqrt((2.0 + 0.5 * (sr_a ** 2 + sr_b ** 2)) / T) * math.sqrt(252)
    assert abs(hac.se / iid - 1.0) < 0.05 and abs(hac.se_nw10 / iid - 1.0) < 0.05, (hac.se, hac.se_nw10, iid)
    assert hac.T == T and abs(hac.psi.sum()) < 1e-6 * np.abs(hac.psi).sum()           # psi sums to zero
    psi = _ar1(rng, 50000, 0.5, 1.0)
    psi -= psi.mean()
    lrv, bw = GS.lrv_qs_andrews(psi)
    assert abs(lrv / psi.var() - 3.0) < 0.3 and bw > 5, (lrv / psi.var(), bw)
    assert GS.lrv_bartlett(psi, 10) / psi.var() > 2.0                                  # NW10 captures most of it
    a2 = _ar1(rng, 8000, 0.6, 0.01, 0.0005)
    b2 = rng.normal(0.0002, 0.01, 8000)
    lad = GS.se_ladder(a2, b2, B=300, seed=SEED)
    sb = lad["se_by_block"]
    assert set(sb) == set(GS.SE_LADDER_BLOCKS) == {10, 21, 63, 126, 250}
    assert sb[250] > sb[21] > sb[10] and lad["se_hac"] > sb[10], sb
    assert lad["se_plateau"] == max([lad["se_hac"]] + list(sb.values())) and lad["se_blk250"] == sb[250]
    assert lad["n_blocks"] == {k: math.ceil(8000 / k) for k in sb} and lad["T"] == 8000
    assert set(lad["curve"]) == {"hac", "nw10", "10", "21", "63", "126", "250"}
    # white noise: every ladder entry within 15% of the iid form (long blocks lose a little, the plateau covers it)
    lad0 = GS.se_ladder(a, b, B=200, seed=SEED)
    assert all(abs(v / iid - 1.0) < 0.15 for v in lad0["se_by_block"].values()), lad0["se_by_block"]


test_se01_hac_white_noise_and_ar_ladder.test_ids = ["T-SE-01"]


def test_se01_r03_french_refdata():
    """R-03 vs unscaled at 50 bp: LW-HAC 0.072, 250-block 0.091 (+/- 0.005); z 3.81 -> 3.0 still above 2.50 (L2633):
    needs the French daily momentum file (F10)."""
    _refdata("F10")
    raise NotRun("REFDATA: F10 present but the R-03 paper L/S book builder (sleeves.paper_ls_returns on the French file) "
                 "is wired by the M7 integration; the SE ladder is asserted there")


test_se01_r03_french_refdata.test_ids = ["T-SE-01"]


# --------------------------------------------------------------------------- #
# Block rule: Politis-White on psi, floor 21, fallback 250, PC-3's second leg at 10
# --------------------------------------------------------------------------- #
def test_block_rule_pw_psi_floor_fallback_pc3():
    """PW(psi) on white-noise books is floored at 21; on books whose psi is autocorrelated it exceeds 21 (and never
    reads d or d^2: the floor 21 differs from costed's max(10, PW(d), PW(d^2))); a degenerate pair (zero variance)
    falls back to 250 and logs the event; pc3_blocks reports both legs with pc3_also_block_10 True."""
    rng = np.random.default_rng(SEED)
    a, b = rng.normal(0.0004, 0.01, 4000), rng.normal(0.0002, 0.01, 4000)
    log = []
    assert GS.pw_block_psi(a, b, log=log) == 21 == GS.BLOCK_FLOOR and log == []
    assert math.ceil(GS.pw_block(GS.influence_function_dsr(a, b))) < 21        # the floor binds
    a2 = _ar1(rng, 8000, 0.6, 0.01, 0.0005)
    b2 = rng.normal(0.0002, 0.01, 8000)
    pw = GS.pw_block_psi(a2, b2, log=log)
    assert pw > 21 and pw == math.ceil(GS.pw_block(GS.influence_function_dsr(a2, b2))) and log == []
    assert pw != GS.pw_block_floor(a2 - b2)                                      # psi, not d / d^2
    flat = GS.pw_block_psi(np.full(100, 0.001), np.full(100, 0.002), log=log)
    assert flat == 250 == GS.BLOCK_FALLBACK and log[-1]["event"] == "pw_block_psi_fallback" and log[-1]["block"] == 250
    legs = GS.pc3_blocks(a2, b2)
    assert legs == {"block_10": 10, "block_pw": pw, "pc3_also_block_10": True}
    assert GS.STATS["block"] == {"rule": "politis_white_on_influence_function", "floor_sessions": 21, "pc3_also_block_10": True}
    # a 1-row shorter book is refused; a resample block above T is refused
    _raises(lambda: GS.lw_hac_se(a[:-1], b), ValueError, "differ in length")
    _raises(lambda: GS.lw_studentized_boot(a, b, block=5000, B=10), ValueError, "block")


# --------------------------------------------------------------------------- #
# T-POWER-01 / T-POWER-02: the power line
# --------------------------------------------------------------------------- #
def test_power01_arithmetic_synth():
    """The L2573-2575 arithmetic on the fixture SEs: 0.061 -> MDE80 0.1295; 0.130 -> 0.2760; PC-3 power at a true 0
    with delta 0.10 at SE 0.130 = Phi(0.10/0.130 - 1.2816) = 0.3042; 10.4 years at SE 0.130 -> 316.9 years to detect
    +0.05 (inside G-PWR-01's 319-330 only with the NW10 0.132: the brief's 10.4 y x (2.1232 x 0.130/0.05)^2);
    36 years at 0.061 -> 241.5 (inside 241-246); power at +0.05 / +0.10 is Phi(D/SE - 1.2816); both are UNDERPOWERED
    (MDE80 > 0.10); a ladder dict feeds the same line and carries the curve."""
    us = GS.power_line(0.061, sessions=36 * 252, card_class="CARD-P")
    assert abs(us.mde80 - 0.1295) < 5e-4 and abs(us.years_to_detect_0p05 - 241.5) < 0.5 and us.underpowered
    assert abs(us.power_at_0p05 - sps.norm.cdf(0.05 / 0.061 - 1.2816)) < 1e-12
    assert abs(us.power_at_0p10 - sps.norm.cdf(0.10 / 0.061 - 1.2816)) < 1e-12
    kr = GS.power_line(0.130, sessions=int(10.4 * 252), card_class="CARD-P")
    assert abs(kr.mde80 - 0.2760) < 5e-4 and abs(kr.pc3_power_at_0 - 0.3042) < 5e-4, (kr.mde80, kr.pc3_power_at_0)
    assert abs(kr.years_to_detect_0p05 - 316.9) < 0.5 and kr.underpowered and abs(kr.t_years - 10.4) < 0.01
    assert kr.years_to_detect_0p05_power50 < kr.years_to_detect_0p05                  # 50% power needs fewer years
    small = GS.power_line(0.040, sessions=252 * 20, card_class="CARD-O")
    assert not small.underpowered and small.pc3_power_at_0 is None and abs(small.mde80 - 0.084928) < 1e-6
    assert GS.MDE_FACTOR == 2.1232 and GS.Z_ALPHA == 1.2816 and GS.STATS["power"]["mde_factor"] == 2.1232
    rng = np.random.default_rng(SEED)
    x, y = _clustered_books(rng, 2500)
    lad = GS.se_ladder(x, y, B=200, seed=SEED)
    pl = GS.power_line(lad, sessions=2500)
    assert pl.se_hac == lad["se_hac"] and pl.se_plateau == lad["se_plateau"] and pl.se_blk250 == lad["se_by_block"][250]
    assert pl.se_curve == lad["curve"] and abs(pl.mde80 - 2.1232 * lad["se_plateau"]) < 1e-12
    d = pl.as_dict()
    assert set(d) == set(GS.POWER_FIELDS) | {"underpowered"} and d["se_curve"]["250"] == lad["se_by_block"][250]
    _raises(lambda: GS.power_line(0.1, sessions=100, card_class="CARD-X"), GS.StatsRefused, "card_class")
    _raises(lambda: GS.power_line(0.0, sessions=100), ValueError, "se_plateau")


test_power01_arithmetic_synth.test_ids = ["T-POWER-01"]


def test_power01_fixture_ses_refdata():
    """SE(delta_SR) 0.061 +/- 0.005 (US VT15 vs S, 50 bp, 1990-2026, U1) and 0.130 +/- 0.01 (KOSPI VT20 vs S, 3 bp,
    2016-26, F13); years 241-246 / 319-330 restated to a point; PC-3 power at a true 0 0.30 +/- 0.02 (L2628)."""
    _refdata("U1", "F13")
    raise NotRun("REFDATA: U1 and F13 present but the VT15 / VT20 card books come from the M7 integration (costed.vt_weights "
                 "+ same_exposure_static on the frozen fixtures); the ladder is asserted there")


test_power01_fixture_ses_refdata.test_ids = ["T-POWER-01"]


def test_power02_power_block_required():
    """Every card prints SE (HAC and 250-block), MDE80 and power; a card without them is refused (L2619, L2629)."""
    pl = GS.power_line(0.07, sessions=5000)
    GS.check_power_block(pl)
    GS.check_power_block(pl.as_dict())
    for missing in GS.POWER_FIELDS:
        d = pl.as_dict()
        del d[missing]
        _raises(lambda d=d: GS.check_power_block(d), GS.PowerBlockMissing, missing)
    _raises(lambda: GS.check_power_block(None), GS.PowerBlockMissing, "no power block")
    bad = pl.as_dict()
    bad["se_hac"] = float("nan")
    _raises(lambda: GS.check_power_block(bad), GS.PowerBlockMissing, "se_hac")
    assert issubclass(GS.PowerBlockMissing, GS.StatsRefused) and issubclass(GS.StatsRefused, ValueError)


test_power02_power_block_required.test_ids = ["T-POWER-02"]


# --------------------------------------------------------------------------- #
# T-UNDERPOW-01: the UNDERPOWERED code converts only a failed step-5 or PC-3 p-value
# --------------------------------------------------------------------------- #
def test_underpow01_scope():
    """With MDE80 > 0.10 a failed PC-3 (or step-5) p-value -> INSUFFICIENT_DATA `underpowered`; with MDE80 <= 0.10 the
    reason is `inconclusive`; a passed check converts nothing; PC-1', PC-2, the PC-3 point and step 3 raise (L2576,
    L2622), so their REJECT / INSUFFICIENT paths can never be waived here."""
    weak = GS.power_line(0.130, sessions=2620)            # MDE80 0.276
    strong = GS.power_line(0.030, sessions=9000)          # MDE80 0.064
    assert GS.apply_underpowered("pc3_p_value", True, weak) == ("INSUFFICIENT_DATA", "underpowered")
    assert GS.apply_underpowered("step5_p_value", True, weak.as_dict()) == ("INSUFFICIENT_DATA", "underpowered")
    assert GS.apply_underpowered("pc3_p_value", True, strong) == ("INSUFFICIENT_DATA", "inconclusive")
    assert GS.apply_underpowered("pc3_p_value", False, weak) == (None, None)
    for check in ("pc1_prime", "pc2", "pc3_point", "step3", "PC3", "pc3"):
        _raises(lambda c=check: GS.apply_underpowered(c, True, weak), GS.StatsRefused, "UNDERPOWERED applies only")
    assert tuple(GS.STATS["underpowered"]["converts"]) == GS.UNDERPOWERED_CONVERTS == ("step5_p_value", "pc3_p_value")
    assert GS.STATS["underpowered"]["mde80_gt"] == GS.MDE80_UNDERPOWERED == 0.10
    # the boundary: MDE80 exactly 0.10 is not underpowered (strict >)
    edge = GS.power_line(0.10 / 2.1232, sessions=1000)
    assert abs(edge.mde80 - 0.10) < 1e-12 and not edge.underpowered


test_underpow01_scope.test_ids = ["T-UNDERPOW-01"]


# --------------------------------------------------------------------------- #
# T-PZERO-01: a resample count of 0 prints "< 1/B"
# --------------------------------------------------------------------------- #
def test_pzero01_count_zero_prints_floor():
    """A huge edge gives a resample count of 0: `p_lw` is the string "< 1/B", `count` 0, `p_numeric` compares it as
    1/B; the analytic p never underflows to 0.0; a non-zero count is the float count/B (L2567, L2631)."""
    rng = np.random.default_rng(SEED)
    b = rng.normal(0.0002, 0.01, 2000)
    big = rng.normal(0.0002, 0.01, 2000) + 0.01
    r = GS.lw_studentized_boot(big, b, block=21, B=500, seed=SEED)
    assert r["p_lw"] == GS.P_FLOOR == "< 1/B" == GS.STATS["bootstrap"]["p_zero_print"] and r["count"] == 0
    assert GS.p_numeric(r["p_lw"], 500) == 1.0 / 500 and r["p_hac"] > 0.0 and r["t_obs"] > 10
    assert GS.pstr(0, 2000) == "< 1/B" and GS.pstr(7, 2000) == 0.0035 and GS.p_numeric(0.0035, 2000) == 0.0035
    _raises(lambda: GS.pstr(-1, 2000), ValueError, "pstr")
    assert GS.harvey_liu_haircut(60.0, 1)["p1"] > 0.0                       # the analytic floor everywhere
    assert json.dumps({"p_lw": r["p_lw"], "p_hac": r["p_hac"]})            # card-serialisable, no numeric 0
    assert 0.0 not in (r["p_hac"], GS.p_numeric(r["p_lw"], 500))


test_pzero01_count_zero_prints_floor.test_ids = ["T-PZERO-01"]


# --------------------------------------------------------------------------- #
# T-PBO-01: PBO on the card's own objective
# --------------------------------------------------------------------------- #
def test_pbo01_noise_control_200_panels_and_objectives():
    """QF3's noise recipe (first draw of default_rng(11), normal(0, 0.01, (2600, 10)) truncated to 2,592 rows, 16
    blocks, Sharpe ddof 1): PBO 0.536 +/- 0.001, bit-equal to validate.pbo_cscv's rank convention (0.535897 = 6,897
    of 12,870); over 200 panels from SeedSequence(11)'s children the mean is 0.4998 +/- 0.005 (inside [0.45, 0.55]);
    fewer than 10 configurations: "PBO not run (n < 10)", never imputed; the CARD-P objective (block-wise dES95 of
    21-session windows, windows never spanning a join) runs on a synthetic panel; a config set that contains the
    comparator itself never "loses"; pbo_null(seed 11) reproduces the control."""
    panel = np.random.default_rng(11).normal(0.0, 0.01, size=(2600, 10))[:2592]
    r = GS.pbo_on_claim(panel, np.zeros(2592), objective="sharpe", S=16)
    ref = V.pbo_cscv(panel, S=16)
    assert r["n_splits"] == 12870 == ref["n_splits"] and abs(r["pbo"] - 0.536) <= 0.001
    assert abs(r["pbo"] - ref["pbo"]) < 1e-12 and abs(r["pbo"] - 6897 / 12870) < 1e-12, (r["pbo"], ref["pbo"])
    assert abs(r["slope"] - ref["slope"]) < 1e-9 and r["n_configs"] == 10 and r["S"] == 16
    assert r["winner_loses_share"] == ref["prob_loss"]                         # comparator 0: the same share
    assert abs(GS.pbo_null(10, 2592, S=16, seed=11) - r["pbo"]) < 1e-12
    vals = [GS.pbo_on_claim(np.random.default_rng(ss).normal(0.0, 0.01, (2600, 10))[:2592], np.zeros(2592), S=16)["pbo"]
            for ss in GS.spawn_seeds(11, 200)]
    mean = float(np.mean(vals))
    assert abs(mean - 0.4998) <= 0.005 and 0.45 <= mean <= 0.55, (mean, float(np.std(vals)))
    assert 0.15 < float(np.std(vals)) < 0.30                                   # a single panel is never asserted on [0.4, 0.6]
    small = GS.pbo_on_claim(panel[:, :9], np.zeros(2592), S=16)
    assert small["pbo"] is None and small["note"] == "PBO not run (n < 10)" and "9 configurations" in small["reason"]
    assert GS.STATS["pbo"]["min_configs"] == GS.PBO_MIN_CONFIGS == 10 and GS.STATS["pbo"]["cscv_blocks"] == 16
    rng = np.random.default_rng(SEED)
    M = rng.normal(0.0, 0.01, (1200, 12))
    c = rng.normal(0.0, 0.01, 1200)
    es = GS.pbo_on_claim(M, c, objective="des95_21", S=16)
    assert es["objective"] == "des95_21" and 0.0 <= es["pbo"] <= 1.0 and es["n_splits"] == 12870
    assert isinstance(es["winner_loses"], bool) and es["winner_loses"] == (es["winner_loses_share"] > 0.10)
    # the comparator inside the set: its objective is 0 in every split, so "the winner loses" needs another column
    with_c = GS.pbo_on_claim(np.column_stack([np.zeros((400, 11)) + rng.normal(0, 1e-5, (400, 11)), c[:400]]), c[:400], S=8)
    assert with_c["n_splits"] == 70 and with_c["winner_loses_share"] <= 1.0
    # a callable objective (the generic path) agrees with the Sharpe fast path on the ranks
    gen = GS.pbo_on_claim(panel[:400], np.zeros(400), S=8, objective=lambda m, cc: V._col_sharpe(m) - V.sharpe(cc) if cc.std() > 0 else V._col_sharpe(m))
    fast = GS.pbo_on_claim(panel[:400], np.zeros(400), S=8)
    assert abs(gen["pbo"] - fast["pbo"]) < 1e-12 and gen["n_splits"] == 70
    _raises(lambda: GS.pbo_on_claim(panel, np.zeros(2592), objective="mdd", S=16), ValueError, "objective")
    _raises(lambda: GS.pbo_on_claim(panel[:20], np.zeros(20), S=16), ValueError, "T >= 2 S")


test_pbo01_noise_control_200_panels_and_objectives.test_ids = ["T-PBO-01"]


def test_pbo01_kospi_vt_grid_refdata():
    """The KOSPI VT grid's Sharpe-objective PBO (0.28) is printed and the protective-objective value is the one the
    step uses (L2632): needs the KOSPI closes (F13) and the frozen PC-6 grid books."""
    _refdata("F13")
    raise NotRun("REFDATA: F13 present but the PC-6 grid books (gate.card_p_v2.pc6_axes x costed.vt_weights) are built by cardp")


test_pbo01_kospi_vt_grid_refdata.test_ids = ["T-PBO-01"]


# --------------------------------------------------------------------------- #
# T-DSR-01 / T-DSR-02: PSR / DSR with declared units
# --------------------------------------------------------------------------- #
def test_dsr01_bldp_psr_units():
    """BLdP's example through the unit-declared PSR with the L2522 mapping: delta_SR = 2.5/sqrt(250) per period,
    T 1,250, SE_obs = sqrt((1 + 3 SR + 9/4 SR^2)/(T - 1)) (skew -3, kurtosis 10 in the BLdP form), hurdle
    sqrt(0.5/250) x e(N) with validate.expected_max_sharpe: 0.9505 at N 46, 0.9004 at N 100 (0.950502 / 0.900397)."""
    sr, T = 2.5 / math.sqrt(250), 1250
    got = {}
    for n, want in ((46, 0.9505), (100, 0.9004)):
        hurdle = math.sqrt(0.5 / 250) * V.expected_max_sharpe(n, 1.0)
        got[n] = GS.psr(GS.Sharpe(sr, "daily"), T, units="daily", sr0=hurdle, skew=-3.0, kurt=10.0)
        assert abs(got[n] - want) <= 5e-5, (n, got[n], want)
        assert got[n] == GS.psr(sr, T, units="daily", sr0=hurdle, skew=-3.0, kurt=10.0)   # a bare float is per-period
    assert abs(got[46] - 0.950502) < 1e-6 and abs(got[100] - 0.900397) < 1e-6
    # the same mapping through the explicit BLdP SE, as the F30 fixture test does
    se_obs = math.sqrt((1 + 3 * sr + 9 / 4 * sr ** 2) / (T - 1))
    assert abs(sps.norm.cdf((sr - math.sqrt(0.5 / 250) * V.expected_max_sharpe(46, 1.0)) / se_obs) - got[46]) < 1e-12


test_dsr01_bldp_psr_units.test_ids = ["T-DSR-01"]


def test_dsr02_units_daily_monthly_and_refusal():
    """`units in {daily, monthly}`; the same synthetic card's DSR vs 0 on daily and on monthly data (21-session
    compounded) agrees within 0.1 through validate.deflated_sharpe; an annualised Sharpe passed with a daily T
    raises; an unknown unit raises; a bare float is read as per-period in the declared unit."""
    rng = np.random.default_rng(SEED)
    T = 252 * 30
    d = rng.normal(0.7 / math.sqrt(252) * 0.01, 0.01, T)
    m = np.prod(1.0 + d[: T // 21 * 21].reshape(-1, 21), axis=1) - 1.0
    for n_trials, sd in ((10, 0.3), (50, 0.5), (1, 0.0)):
        dd = GS.dsr_vs_zero(d, units="daily", n_trials=n_trials, sr_sd_annual=sd)
        mm = GS.dsr_vs_zero(m, units="monthly", n_trials=n_trials, sr_sd_annual=sd)
        assert abs(dd - mm) < 0.1, (n_trials, sd, dd, mm)
    assert GS.dsr_vs_zero(d, units="daily", n_trials=10, sr_sd_annual=0.3) == V.deflated_sharpe(d, n_trials=10, sr_sd_daily=0.3 / math.sqrt(252))
    _raises(lambda: GS.psr(GS.Sharpe(0.67, "annual"), T, units="daily"), GS.StatsRefused, "annual Sharpe ratio was passed with a daily T")
    _raises(lambda: GS.psr(GS.Sharpe(0.2, "monthly"), T, units="daily"), GS.StatsRefused, "one declared unit")
    _raises(lambda: GS.psr(0.04, T, units="annual"), GS.StatsRefused, "units must be one of")
    _raises(lambda: GS.dsr_vs_zero(d, units="weekly", n_trials=1, sr_sd_annual=0.0), GS.StatsRefused, "units")
    _raises(lambda: GS.Sharpe(0.1, "yearly"), GS.StatsRefused, "Sharpe.units")
    assert GS.PERIODS == {"daily": 252, "monthly": 12}
    p_d = GS.psr(GS.Sharpe(V.sharpe(d) / math.sqrt(252), "daily"), d.size, units="daily")
    p_m = GS.psr(GS.Sharpe(V.sharpe(m) / math.sqrt(252) * math.sqrt(252 / 12), "monthly"), m.size, units="monthly")
    assert abs(p_d - p_m) < 0.1 and 0.9 < p_d <= 1.0, (p_d, p_m)


test_dsr02_units_daily_monthly_and_refusal.test_ids = ["T-DSR-02"]


# --------------------------------------------------------------------------- #
# The studentized bootstrap: null-centred t*, determinism under the seed (bootstrap half of T-REPRO-01b)
# --------------------------------------------------------------------------- #
def test_lw_boot_null_centred_and_deterministic():
    """`t_obs = (dSR - null)/se_hac`; `t* = (dSR* - dSR)/se*` is centred at the sample, so a lower null (PC-3's -delta)
    raises t_obs and lowers p; the same seed, B and block give an identical result (relative 1e-12 trivially); another
    seed changes the count, not dSR or se; the studentized CI brackets dSR; the output keys are the L2613 set; on a
    pair with no edge the p-value is far from both tails; the HAC p is printed beside the bootstrap p."""
    rng = np.random.default_rng(SEED)
    x, y = _clustered_books(rng, 3000)
    r = GS.lw_studentized_boot(x, y, block=21, B=400, seed=SEED)
    again = GS.lw_studentized_boot(x, y, block=21, B=400, seed=SEED)
    assert r == again
    other = GS.lw_studentized_boot(x, y, block=21, B=400, seed=SEED + 1)
    assert other["dSR"] == r["dSR"] and other["se"] == r["se"] and other["count"] != r["count"]
    assert {"dSR", "se", "se_nw10", "t_obs", "p_lw", "count", "p_hac", "block", "n_blocks", "B", "seed", "null", "ci", "level"} <= set(r)
    assert r["block"] == 21 and r["n_blocks"] == math.ceil(3000 / 21) and r["B"] == 400 and r["null"] == 0.0
    assert r["ci"][0] < r["dSR"] < r["ci"][1] and abs(r["dSR"] - GS.delta_sr(x, y)) < 1e-12
    assert abs(r["t_obs"] - r["dSR"] / r["se"]) < 1e-12 and abs(r["p_hac"] - sps.norm.sf(r["t_obs"])) < 1e-12
    assert 0.05 < GS.p_numeric(r["p_lw"], 400) < 0.95 and 0.05 < r["p_hac"] < 0.95
    ni = GS.lw_studentized_boot(x, y, block=21, B=400, seed=SEED, null=-0.10)
    assert ni["t_obs"] > r["t_obs"] and GS.p_numeric(ni["p_lw"], 400) <= GS.p_numeric(r["p_lw"], 400) and ni["p_hac"] < r["p_hac"]
    assert abs(ni["t_obs"] - (r["dSR"] + 0.10) / r["se"]) < 1e-12
    # spawned child seeds are deterministic and distinct
    kids = GS.spawn_seeds(11, 3)
    assert [k.generate_state(1)[0] for k in kids] == [k.generate_state(1)[0] for k in GS.spawn_seeds(11, 3)]
    assert len({int(k.generate_state(1)[0]) for k in kids}) == 3
    assert GS.STATS["bootstrap"]["resamples"] == GS.B_DEFAULT == 2000 and GS.STATS["bootstrap"]["seed"] == GS.SEED_STUDY == 11


test_lw_boot_null_centred_and_deterministic.test_ids = ["T-REPRO-01b"]


# --------------------------------------------------------------------------- #
# Printed lines: BY q, Harvey-Liu, Lo-adjusted Sharpe, the class helper
# --------------------------------------------------------------------------- #
def test_printed_lines_by_hl_lo_and_verdict_class():
    rng = np.random.default_rng(SEED)
    p = np.array([0.01, 0.04, 0.03, 0.5, 0.2])
    q = GS.by_qvalue(p)
    c_m = sum(1.0 / k for k in range(1, 6))
    assert np.all(q >= p) and np.all(q <= 1.0) and abs(q[0] - min(1.0, 0.01 * 5 * c_m / 1)) < 1e-12
    assert q[1] == q[2] and q[3] == 1.0 and GS.by_qvalue([]).size == 0           # step-up monotonicity, cap at 1
    _raises(lambda: GS.by_qvalue([0.5, 1.5]), ValueError, "[0, 1]")
    hl1 = GS.harvey_liu_haircut(3.0, 1)
    assert abs(hl1["haircut"]) < 1e-9 and hl1["live_sharpe_multiplier"] == 0.60 == GS.STATS["live_sharpe_multiplier"]
    hl120 = GS.harvey_liu_haircut(3.0, 120)
    assert 0.5 < hl120["haircut"] < 0.8 and hl120["p_adj"] == min(1.0, 120 * hl120["p1"]) and hl120["sharpe_multiplier"] == 1 - hl120["haircut"]
    assert GS.harvey_liu_haircut(0.5, 50)["haircut"] == 1.0 and GS.harvey_liu_haircut(-1.0, 1)["haircut"] == 1.0
    assert abs(GS.sharpe_z(0.6723, 9233) - 0.6723 * math.sqrt(9233 / 252)) < 1e-12
    _raises(lambda: GS.harvey_liu_haircut(2.0, 0), ValueError, "M")
    b = rng.normal(0.0002, 0.01, 8000)
    a = _ar1(rng, 8000, 0.6, 0.01, 0.0005)
    lo_iid, lo_ar, lo_all = GS.lo_adjusted_sr(b, 20), GS.lo_adjusted_sr(a, 20), GS.lo_adjusted_sr(a, 10 ** 6)
    assert abs(lo_iid["eta_ratio"] - 1.0) < 0.05 and lo_ar["eta_ratio"] < 0.7 and lo_all["lags"] == 251
    assert abs(lo_iid["lo_sr"] - lo_iid["sr_annual_iid"] * lo_iid["eta_ratio"]) < 1e-12 and lo_iid["se_lo"] == V.lo_se(b)
    assert abs(GS.lo_adjusted_sr(b, 0)["eta_ratio"] - 1.0) < 1e-12 and GS.STATS["lo_adjusted_sr"]["gated"] is False
    both = GS.verdict_class(0.103, 0.10, 0.01, at_or_above="INSUFFICIENT_DATA", below="PASS")
    assert both == frozenset({"INSUFFICIENT_DATA", "PASS"})
    assert GS.verdict_class(0.2, 0.10, 0.01, at_or_above="INSUFFICIENT_DATA", below="PASS") == frozenset({"INSUFFICIENT_DATA"})
    assert GS.verdict_class(-0.2, -0.10, 0.01, at_or_above="PASS", below="REJECT") == frozenset({"REJECT"})


# --------------------------------------------------------------------------- #
# The module mirrors the shipped gate.stats block and stays a pure, clock-free leaf
# --------------------------------------------------------------------------- #
def test_stats_mirrors_store_and_module_is_a_pure_leaf():
    """STATS equals the shipped `gate.stats`; no `GATE[`, wall clock, data read or rules-store import in gate_stats;
    every M2 name the costed engine imports is still there."""
    store = json.loads(STORE.read_text(encoding="utf-8"))["gate"]["stats"]
    assert store == GS.STATS, "gate_stats.STATS drifted from data/macro/rules_v2.0.0.json gate.stats"
    src = Path(GS.__file__).read_text(encoding="utf-8")
    tree = ast.parse(src)
    calls = {ast.unparse(n.func) for n in ast.walk(tree) if isinstance(n, ast.Call)}
    forbidden = {"datetime.now", "datetime.utcnow", "time.time", "date.today", "pit_value", "read_csv", "load_history"}
    assert not (calls & forbidden), calls & forbidden
    assert "GATE[" not in src and "GATE.get" not in src
    imports = {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)} | {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    assert not any(m and ("rules" in m or "pit" in m or "ficc" in m) for m in imports), imports
    for name in ("optimal_block_length", "pw_block", "pw_block_floor", "block_indices", "row_sharpes", "PC3_BLOCK_FLOOR", "BLOCK_KINDS"):
        assert hasattr(GS, name)
    # seeds and B are explicit everywhere: no R-24 function defaults to a value read at run time
    for fn in (GS.lw_studentized_boot, GS.se_ladder):
        defaults = {k: v.default for k, v in __import__("inspect").signature(fn).parameters.items() if v.default is not v.empty}
        assert defaults.get("B") == 2000 and defaults.get("seed") == 11


if __name__ == "__main__":
    from tests.macro_acceptance import run_module
    raise SystemExit(run_module(globals()))
