"""Sprint 7 package C tests: the tech-fund governance amendments GOV-1..GOV-11 (core/quant/tf_gov.py), the tech-fund
card runner and the CRY-1 controls of card C3 (docs/techfund_study.py), and the INV-1 / INV-5 assertions.

Hermetic: GOV statistics run on seeded synthetic panels; the CRY-1 study reads only the local vendor caches
(docs/asset_expansion/cache) and writes only to temp directories; the KRX card runs are NOT_RUN (REFDATA: the KRX
all-stock panel). Lab numbers are pinned reference constants (file + line), cross-checked against data/techfund or the
research bundle when present. Nothing here writes under ~/.nextgen, into the repo or into docs/asset_expansion/cards.
"""
from __future__ import annotations

import ast
import csv
import hashlib
import inspect
import io
import json
import re
import tempfile
import time
from contextlib import redirect_stdout
from datetime import date, timedelta
from pathlib import Path

import numpy as np

from core.quant import costed as C
from core.quant import gate_stats as GS
from core.quant import strategies as S
from core.quant import tf_gov as TG
from core.quant import validate as V
from tests.notrun import NotRun

ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / "QUANTGEN_techfund_research_bundle" / "QUANTGEN_techfund_research"
SEED = 11
RUN_UTC = "2026-10-07T00:00:00Z"
CRY1_FILES = ("cry1_cut_time.json", "cry1_eth_replication.json", "cry1_split_2024-01-10.json", "cry1_volscaled_control.json")


def _raises(fn, exc, needle: str = "") -> None:
    try:
        fn()
    except exc as e:
        assert needle in str(e), f"{exc.__name__} without {needle!r}: {e}"
        return
    raise AssertionError(f"{exc.__name__} not raised")


def _business_days(start: date, n: int) -> list[date]:
    out, d = [], start
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d)
        d += timedelta(days=1)
    return out


def _lab_line(rel: str, line: int) -> dict | None:
    """Row `line` (1-based, header = 1) of a lab CSV from data/techfund or the bundle; None when neither holds it."""
    for p in (ROOT / "data" / "techfund" / Path(rel).name, BUNDLE / "datalab" / "results" / rel):
        if p.is_file():
            with p.open(encoding="utf-8", newline="") as fh:
                rows = list(csv.DictReader(fh))
            return rows[line - 2]
    return None


def _md5_tree(d: Path) -> dict[str, str]:
    return {p.relative_to(d).as_posix(): hashlib.md5(p.read_bytes()).hexdigest() for p in sorted(d.rglob("*")) if p.is_file()}


def _row(**params) -> dict:
    return {"rule": "TF-TEST", "params": params, "timing_class": "COMPLIANT", "span": ["2017-01-01", "2026-09-25"],
            "market": "CRYPTO", "run_utc": RUN_UTC, "phase": "research", "script": "tests/macro_tf_gov.py"}


# --------------------------------------------------------------------------- #
# GOV-1 primary statistic
# --------------------------------------------------------------------------- #
def test_gov1_primary_statistic_long_only_vs_ew_capped_reported_sign_split_revise():
    rng = np.random.default_rng(SEED)
    T = 1500
    ew, cw, cwx = (rng.normal(0.0003, 0.01, T) for _ in range(3))
    lo = ew + 0.0004 + rng.normal(0, 0.002, T)
    capped = lo + 0.0003 + rng.normal(0, 0.002, T)            # the capped VW book beats the long-only book
    out = TG.primary_statistic(lo, {"EW": ew, "capped_CW": capped, "CW": cw, "CW_ex_pair": cwx})
    assert out["primary"] == "long_only_net_excess_vs_EW"
    assert set(out["vs"]) == {"EW", "capped_CW", "CW", "CW_ex_pair"}                       # every declared benchmark printed
    assert abs(out["vs"]["EW"]["ann"] - np.mean(lo - ew) * 252) < 1e-12
    assert out["vs"]["EW"]["ann"] > 0 > out["vs"]["capped_CW"]["ann"]
    assert out["sign_split_ew_capped"] and out["verdict_cap"] == "REVISE"
    same = TG.primary_statistic(lo, {"EW": ew, "capped_CW": ew - 0.0001})
    assert not same["sign_split_ew_capped"] and same["verdict_cap"] is None
    long_leg, short_leg = rng.normal(0.0004, 0.01, T), rng.normal(-0.0002, 0.01, T)
    ls = long_leg - short_leg
    diag = TG.primary_statistic(lo, {"EW": ew, "capped_CW": capped}, long_short=ls, short_leg=short_leg)
    assert diag["long_short"]["role"] == "diagnostic only"
    assert abs(diag["short_leg_share"] - np.mean(-short_leg) / np.mean(ls)) < 1e-12
    _raises(lambda: TG.primary_statistic(lo, {"EW": ew}), TG.GovRefused, "capped_CW")
    assert TG.BENCHMARK_SET_KRX == ("EW", "CW", "CW_ex_pair", "capped_CW")


test_gov1_primary_statistic_long_only_vs_ew_capped_reported_sign_split_revise.test_ids = ["T-TF-GOV-01"]


# --------------------------------------------------------------------------- #
# GOV-2 multiplicity: SPA size / power, BH / Holm, family gate, trial registry
# --------------------------------------------------------------------------- #
def test_gov2_spa_size_on_pure_noise_rule_families():
    """200 seeded panels of 5 noise rules (E[d] = 0 for every rule): the consistent SPA rejects at 5% within the
    Monte-Carlo band. MC SE at 200 panels is 1.5 pp; the band [1%, 10%] also admits the known finite-sample liberal
    bias of the studentised SPA (the stationary-bootstrap kernel variance is biased down by about 2 x block / T)."""
    pc, rc = [], []
    for i in range(200):
        r = np.random.default_rng([SEED, i])
        b = r.normal(0, 0.01, 400)
        rules = b[:, None] + r.normal(0, 0.005, (400, 5))
        s = TG.spa_test(-b, -rules, B=199, block=TG.SPA_BLOCK, seed=i)
        assert 0.0 <= s["p_lower"] <= s["p_consistent"] <= s["p_upper"] <= 1.0
        pc.append(s["p_consistent"])
        rc.append(s["p_rc"])
    size, size_rc = float(np.mean(np.array(pc) <= 0.05)), float(np.mean(np.array(rc) <= 0.05))
    assert 0.01 <= size <= 0.10, size
    assert 0.01 <= size_rc <= 0.10, size_rc


test_gov2_spa_size_on_pure_noise_rule_families.test_ids = ["T-TF-GOV-02"]


def test_gov2_spa_power_on_a_planted_rule_and_family_gate():
    hits, best = 0, []
    for i in range(10):
        r = np.random.default_rng([SEED + 1, i])
        b = r.normal(0, 0.01, 400)
        rules = b[:, None] + r.normal(0, 0.005, (400, 5))
        rules[:, 3] += 0.001                                    # t about 4 on 400 sessions
        s = TG.spa_test(-b, -rules, B=199, seed=i)
        hits += s["p_consistent"] <= TG.FAMILY_SPA_P_MAX
        best.append(s["best"])
        assert s["rule_p"][3] == min(s["rule_p"])
    assert hits >= 9 and best.count(3) >= 9, (hits, best)
    # family gate: SPA fails -> nothing carried forward; SPA passes -> BH survivors with persistence >= 60%
    rules = {"A": {"p": 0.001, "window_excess": [1, 1, 1, -1, 1, 1, -1, 1, 1, -1]},      # 0.70
             "B": {"p": 0.002, "window_excess": [1, -1, 1, -1, 1, -1, 1, -1, 1, -1]},    # 0.50
             "C": {"p": 0.600, "window_excess": [1] * 10},                              # BH fails
             "D": {"p": 0.004, "window_excess": [1, 1, 1, 1, 1, 1, -1, -1, -1, -1]}}    # exactly 0.60
    shut = TG.family_gate({"spa": 0.20, "rules": rules})
    assert not shut["family_pass"] and shut["survivors"] == [] and "REJECTED" in shut["reason"]
    gate = TG.family_gate({"spa": {"p_consistent": 0.01}, "rules": rules})
    assert gate["family_pass"] and gate["survivors"] == ["A", "D"], gate
    assert gate["persistence"]["D"] == 0.6


test_gov2_spa_power_on_a_planted_rule_and_family_gate.test_ids = ["T-TF-GOV-02"]


def test_gov2_bh_fdr_and_holm_on_known_p_vectors():
    bh = TG.bh_fdr([0.01, 0.04, 0.03, 0.005])
    assert np.allclose(bh["adjusted"], [0.02, 0.04, 0.04, 0.02]) and bh["rejected"].all()
    bh = TG.bh_fdr([0.01, 0.2, 0.03, 0.5], q=0.10)
    assert np.allclose(bh["adjusted"], [0.04, 0.2 * 4 / 3, 0.06, 0.5]) and list(bh["rejected"]) == [True, False, True, False]
    assert np.allclose(TG.holm([0.01, 0.04, 0.03, 0.005]), [0.03, 0.06, 0.06, 0.02])
    assert TG.holm is GS.holm_adjusted                          # one Holm in the tree
    _raises(lambda: TG.bh_fdr([0.1, 1.2]), TG.GovRefused, "[0, 1]")
    assert TG.FDR_Q == 0.10


test_gov2_bh_fdr_and_holm_on_known_p_vectors.test_ids = ["T-TF-GOV-02"]


def test_gov2_trial_registry_append_only_global_n_and_composite_count():
    with tempfile.TemporaryDirectory() as tmp:
        reg = TG.trial_registry(Path(tmp) / "ledgers")
        assert reg.n_rows == 0 and reg.global_n() == 0
        assert reg.register("C3", _row(x=1)).appended
        assert not reg.register("C3", _row(x=1)).appended                       # the same configuration is the same trial
        reg.register("SCR", _row(x=2))
        reg.register("SCR", _row(composite_k=2, composite_n=5))                # a 2-of-5 composite counts 5^2
        assert reg.n_rows == 3 and reg.global_n() == 1 + 1 + 25
        assert TG.composite_count(5, 2) == 25
        _raises(lambda: TG.composite_count(2, 3), TG.GovRefused, "k <= n")
        p = Path(tmp) / "ledgers" / "SCR.jsonl"
        p.write_bytes(p.read_bytes().replace(b'"x":2', b'"x":3'))              # a hand edit breaks the chain
        _raises(reg.global_n, ValueError, "chain broken")


test_gov2_trial_registry_append_only_global_n_and_composite_count.test_ids = ["T-TF-GOV-02"]


# --------------------------------------------------------------------------- #
# GOV-3 attribution block and the Ledoit-Wolf Sharpe test
# --------------------------------------------------------------------------- #
def test_gov3_attribution_recovers_beta_alpha_and_labels_a_factor_tilt():
    rng = np.random.default_rng(SEED)
    T = 5000
    m = rng.normal(0.0004, 0.01, T)
    f = rng.normal(0.0006, 0.006, T)                            # a priced factor the market does not span
    tilt = 0.8 * m + 0.6 * f + rng.normal(0, 0.004, T)
    a = TG.attribution_block(tilt, {"MKT": m, "F": f}, m)
    assert abs(a["beta"] - 0.8) < 0.03 and abs(a["factor_loadings"]["F"] - 0.6) < 0.03
    assert abs(a["jensen_alpha"] - (tilt.mean() - a["beta"] * m.mean()) * 252) < 1e-10   # Jensen alpha on the beta-matched benchmark
    assert abs(a["jensen_alpha"] - 0.6 * 0.0006 * 252) < 0.07           # = the factor premium carried (3 SE)
    assert a["nw_t"] >= 2.0 and a["factor_alpha_t"] < 2.0 and a["factor_tilt"] and a["label"] == "factor tilt"
    alpha = tilt + 0.0003
    b = TG.attribution_block(alpha, {"MKT": m, "F": f}, m)
    assert abs(b["factor_alpha"] - 0.0003 * 252) < 0.045 and b["factor_alpha_t"] >= 2.0
    assert b["factor_tilt"] is False and b["label"] == "alpha"
    noise = 0.8 * m + rng.normal(0, 0.004, T)
    c = TG.attribution_block(noise, None, m)
    assert c["factor_tilt"] is None and c["label"] == "no alpha (CAPM only)" and c["nulls"]["factor_alpha"].startswith("REFDATA:")
    assert c["threshold_t"] == TG.FACTOR_TILT_T == 2.0 and "proposal" in c["threshold_status"]
    assert TG.FACTOR_SETS["KR"] == ("MKT", "SMB", "HML", "RMWq", "CMA", "UMD", "SEMI")
    # Ledoit-Wolf studentised Sharpe-difference test at the GOV-4 block
    x = rng.normal(0.001, 0.01, 2000)
    y = 0.5 * x + rng.normal(0.0, 0.009, 2000)
    lw = TG.ledoit_wolf_sharpe_test(x, y, B=499, seed=SEED)
    assert lw["block"] == TG.pw_block_dd2(x - y) and lw["dSR"] > 0 and lw["p"] < 0.10
    worse = TG.ledoit_wolf_sharpe_test(y, x, B=499, seed=SEED)          # one-sided: the worse book never rejects
    assert worse["dSR"] < 0 and worse["p"] > 0.5


test_gov3_attribution_recovers_beta_alpha_and_labels_a_factor_tilt.test_ids = ["T-TF-GOV-03"]


# --------------------------------------------------------------------------- #
# GOV-4 block length
# --------------------------------------------------------------------------- #
def test_gov4_pw_block_dd2_floors_at_10_and_twice_the_holding_period():
    rng = np.random.default_rng(SEED)
    wn = rng.normal(0, 0.01, 3000)
    assert TG.pw_block_dd2(wn) == 10                            # white noise: the 10-session floor
    assert TG.pw_block_dd2(wn, holding=21) == 42                # 2 x holding period
    e = rng.normal(0, 0.01, 3000)
    ar = np.empty(3000)
    ar[0] = e[0]
    for t in range(1, 3000):
        ar[t] = 0.9 * ar[t - 1] + e[t]
    want = max(10, int(np.ceil(GS.pw_block(ar))), int(np.ceil(GS.pw_block(ar * ar))))
    assert TG.pw_block_dd2(ar) == want > 10
    assert TG.pw_block_dd2(ar, holding=5) == max(want, 10)
    _raises(lambda: TG.pw_block_dd2(wn, holding=0), TG.GovRefused, "holding")
    assert TG.BLOCK_FLOOR == 10 == GS.PC3_BLOCK_FLOOR


test_gov4_pw_block_dd2_floors_at_10_and_twice_the_holding_period.test_ids = ["T-TF-GOV-04"]


# --------------------------------------------------------------------------- #
# GOV-5 minimum track record; GOV-6 step 8 / step 9
# --------------------------------------------------------------------------- #
def test_gov5_min_track_record_line_against_the_history():
    a = TG.min_track_record_line(0.5, 2520)
    assert abs(a["min_trl_sessions"] - 252 * (1.6448536269514722 / 0.5) ** 2) < 1e-6 and a["exceeds_history"]
    assert not TG.min_track_record_line(1.0, 2520)["exceeds_history"]
    neg = TG.min_track_record_line(-0.1, 2520)
    assert neg["min_trl_sessions"] is None and neg["exceeds_history"]


test_gov5_min_track_record_line_against_the_history.test_ids = ["T-TF-GOV-05"]


_MULT_04 = re.compile(r"(?<![\d.])0\.40?\s*(\*|x\b|×)|(\*|×|\bx)\s*0\.40?(?![\d])")
_LIVE_WORDS = re.compile(r"haircut|expected[ _]live|live[ _]sharpe|step[ _]?9|\bg9\b", re.I)
_OPERAND = re.compile(r"oos|sharpe|haircut|live|ann_diff|\bsr\w*|\bir\b", re.I)


def _live_04_hits(src: str, label: str) -> list[str]:
    """A 0.4 multiplier on a step-9 / haircut / expected-live line, or 0.4 x (an OOS / Sharpe / IR operand)."""
    hits = [f"{label}:{i}" for i, line in enumerate(src.splitlines(), 1) if _LIVE_WORDS.search(line) and _MULT_04.search(line)]
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return hits
    for n in ast.walk(tree):
        if isinstance(n, ast.BinOp) and isinstance(n.op, ast.Mult):
            for k, other in ((n.left, n.right), (n.right, n.left)):
                if isinstance(k, ast.Constant) and k.value in (0.4, 0.40) and _OPERAND.search(ast.unparse(other)):
                    hits.append(f"{label}:{n.lineno} {ast.unparse(n)}")
    return hits


def test_gov6_expected_live_is_0p6_x_oos_and_no_0p4_multiplier_exists():
    assert TG.LIVE_MULTIPLIER == 0.6 == GS.LIVE_SHARPE_MULTIPLIER == V.GATE["haircut"]
    line = TG.expected_live(3.08)
    assert abs(line["expected_live"] - 1.848) < 1e-12 and "0.6 x OOS" in line["line"]      # GV-523 arithmetic, not 1.23
    assert _live_04_hits("expected_live = 0.4 * oos\n", "probe") and _live_04_hits("g9 = 0.4 * ann_diff  # step 9\n", "probe")
    assert not _live_04_hits("turnover = 0.4 * equity\n", "probe")
    hits = []
    for base in ("core", "docs", "ui"):
        for p in sorted((ROOT / base).rglob("*.py")):
            if "__pycache__" not in p.parts:
                hits += _live_04_hits(p.read_text(encoding="utf-8", errors="replace"), p.relative_to(ROOT).as_posix())
    for p in sorted((ROOT / "docs" / "techfund").glob("*.json")):
        hits += [f"{p.name}:{i}" for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1)
                 if _LIVE_WORDS.search(line) and _MULT_04.search(line)]
    assert not hits, hits
    # step 8 kept + 2-of-3 subperiods, reported
    days = _business_days(date(1996, 1, 2), 30 * 252)
    x = np.where(np.array([d.year for d in days]) < 2006, -0.0004, 0.0006)
    st = TG.step8_subperiods(x, days, TG.SUBPERIODS_KRX)
    assert [r["name"] for r in st["subperiods"]] == ["1996-2005", "2006-2015", "2016-2026"]
    assert [r["compounded"] > 0 for r in st["subperiods"]] == [False, True, True] and st["two_of_three"] is True
    assert st["step8_pass"] and "reported" in st["status"] and "23.8%" in st["standalone_note"]
    short = TG.step8_subperiods(x[-500:], days[-500:])          # default: equal calendar thirds of the span
    assert len(short["subperiods"]) == 3 and sum(r["sessions"] for r in short["subperiods"]) == 500
    assert TG.step8_subperiods(x[-500:], days[-500:], TG.SUBPERIODS_KRX)["two_of_three"] is None


test_gov6_expected_live_is_0p6_x_oos_and_no_0p4_multiplier_exists.test_ids = ["T-TF-GOV-06"]


# --------------------------------------------------------------------------- #
# GOV-7 break-even pre-gate screen (reference constants)
# --------------------------------------------------------------------------- #
def test_gov7_break_even_screen_on_the_reference_constants():
    rev, mom, f4 = (TG.REFERENCE[k] for k in ("REV_1W_EW_LS", "MOM_12_1_EW_LS", "SCR1_F4_B1"))
    r = TG.break_even_screen(rev["gross_ann"], rev["turnover_yr"], 35.0)
    assert r["verdict"] == "REJECT" and abs(r["break_even_bp"] - 12.5) < 0.05 and r["stage"] == "pre-gate"
    m = TG.break_even_screen(mom["gross_ann"], mom["turnover_yr"], 35.0)
    assert m["verdict"] == "REJECT" and abs(m["break_even_bp"] - 63.7) < 0.05 and m["threshold_bp"] == 70.0
    s = TG.break_even_screen(f4["gross_ann"], f4["turnover_filtered"] - f4["turnover_unfiltered"], 35.0)
    assert s["verdict"] == "PROCEED" and abs(s["break_even_bp"] - 380.2) < 0.05
    assert TG.break_even_screen(0.007, 1.0, 35.0)["verdict"] == "PROCEED"           # exactly 2 x cost proceeds
    for key, col_g, col_t in (("REV_1W_EW_LS", "ls_gross_ann", "ls_turnover_yr"), ("MOM_12_1_EW_LS", "ls_gross_ann", "ls_turnover_yr")):
        ref = TG.REFERENCE[key]
        row = _lab_line("kr/kr_key_numbers.csv", ref["line"])
        if row is not None:                                      # cross-check the pinned constant against its file + line
            assert float(row[col_g]) == ref["gross_ann"] and float(row[col_t]) == ref["turnover_yr"], (key, row)
    row = _lab_line("r2_kr/r2_kr_excl_summary.csv", f4["line"])
    if row is not None:
        assert (row["base"], row["filter"], row["cost"]) == ("B1", "F4", "gross") and float(row["ann_diff"]) == f4["gross_ann"]


test_gov7_break_even_screen_on_the_reference_constants.test_ids = ["T-TF-GOV-07"]


# --------------------------------------------------------------------------- #
# GOV-8 planning haircuts
# --------------------------------------------------------------------------- #
def test_gov8_planning_haircuts_are_a_labelled_proposal_beside_the_council_values():
    council = json.loads((ROOT / "data" / "macro" / "rules_v2.0.0.json").read_text(encoding="utf-8"))["prior_haircuts"]
    out = TG.planning_haircuts(council)
    assert out["proposal"] == {"in_sample": 0.5, "post_publication": 0.3, "drift_like": 0.75}
    assert out["council_prior_haircuts"] == council and out["governs"] == "council" and "PROPOSAL" in out["label"]
    assert council == {"value": 0.49, "momentum": 0.23, "carry": 0.25, "defensive": 0.0, "multifactor": 0.18}   # untouched (D-16)


test_gov8_planning_haircuts_are_a_labelled_proposal_beside_the_council_values.test_ids = ["T-TF-GOV-08"]


# --------------------------------------------------------------------------- #
# GOV-9 stress table
# --------------------------------------------------------------------------- #
def test_gov9_stress_table_windows_and_worst_rolling_relative_loss():
    names = [w[0] for w in TG.STRESS_WINDOWS]
    assert ("2026-06-22..07-30 crash", "2026-06-22", "2026-07-30") in TG.STRESS_WINDOWS and len(names) == 8
    days = _business_days(date(2026, 1, 2), 180)
    x, b = np.full(180, 0.01), np.full(180, 0.005)
    out = TG.stress_table(x, days, benchmark=b)
    crash = next(r for r in out["windows"] if r["name"] == "2026-06-22..07-30 crash")
    n = sum(1 for d in days if date(2026, 6, 22) < d <= date(2026, 7, 30))      # start_close < d <= end_close
    assert crash["sessions"] == n == 28
    assert abs(crash["book"] - (1.01 ** n - 1)) < 1e-12 and abs(crash["relative"] - ((1.01 / 1.005) ** n - 1)) < 1e-12
    gfc = next(r for r in out["windows"] if r["name"].startswith("2008"))
    assert gfc["sessions"] == 0 and gfc["book"] is None
    rng = np.random.default_rng(SEED)
    y = rng.normal(0.0, 0.01, 180)
    y[40:61] = -0.02
    w = TG.stress_table(y, days)["worst_rolling_relative"]
    assert set(w) == {"21", "63", "25"} and out["reporting_only"]
    for k in (21, 63, 25):
        brute = min(np.prod(1 + y[i:i + k]) - 1 for i in range(180 - k + 1))
        assert abs(w[str(k)] - brute) < 1e-12, k
    assert TG.stress_table(y[:20], days[:20])["worst_rolling_relative"]["21"] is None


test_gov9_stress_table_windows_and_worst_rolling_relative_loss.test_ids = ["T-TF-GOV-09"]


# --------------------------------------------------------------------------- #
# GOV-10 contamination log and incubation (no back-fill)
# --------------------------------------------------------------------------- #
def _rec(sessions, lag_days=0):
    return [{"session": str(s), "recorded_utc": f"{s + timedelta(days=lag_days)}T07:00:00Z"} for s in sessions]


def test_gov10_incubation_counts_from_the_first_recorded_session_never_backfilled():
    live = _business_days(date(2026, 10, 1), 300)
    inc = TG.incubation(_rec(live))
    assert inc["first_recorded_session"] == "2026-10-01" and inc["sessions"] == 300 and inc["complete"]
    assert TG.incubation(_rec(live[:251]))["complete"] is False                 # 252 needed
    early = _business_days(date(2026, 9, 21), 8)                                # before the 2026-10-01 clock
    assert TG.incubation(_rec(early + live[:10]))["sessions"] == 10
    late = [{"session": str(s), "recorded_utc": "2026-12-01T07:00:00Z"} for s in live[:30]]   # back-filled history
    b = TG.incubation({"rows": late + _rec(live[30:])})
    assert b["first_recorded_session"] == str(live[30]) and b["sessions"] == 270
    assert sum(e["reason"].startswith("back-filled") for e in b["excluded"]) == 30
    prepend = _rec(live[10:20]) + _rec(live[:10])                               # rows for sessions before the first recorded
    p = TG.incubation(prepend)
    assert p["first_recorded_session"] == str(live[10]) and p["sessions"] == 10
    ahead = TG.incubation([{"session": str(live[5]), "recorded_utc": f"{live[4]}T07:00:00Z"}])
    assert ahead["sessions"] == 0 and ahead["excluded"][0]["reason"] == "recorded before its session"


test_gov10_incubation_counts_from_the_first_recorded_session_never_backfilled.test_ids = ["T-TF-GOV-10"]


def test_gov10_contamination_log_append_only_and_overlap():
    from core.quant.cards import CardRefused
    with tempfile.TemporaryDirectory() as tmp:
        log = TG.contamination_log(Path(tmp) / "contamination_log.jsonl")
        assert log.seed(RUN_UTC) == len(TG.CONTAMINATED_1996_2026) == 13 and log.seed(RUN_UTC) == 0
        assert log.contaminated("MOM_12_1", "2020-01-01", "2020-12-31")
        assert not log.contaminated("MOM_12_1", "2026-10-01", "2027-06-30")    # the incubation window is clean
        assert not log.contaminated("SCR_NEW", "1996-01-01", "2026-09-30")
        log.append("SCR_NEW", "2001-01-01", "2010-12-31", "lab re-run", RUN_UTC)
        assert log.contaminated("SCR_NEW", "2010-12-31", "2011-06-30")
        _raises(lambda: log.append("X", "2010-01-01", "2009-01-01", "lab", RUN_UTC), TG.GovRefused, "start <= end")
        p = Path(tmp) / "contamination_log.jsonl"
        p.write_bytes(p.read_bytes().replace(b"MOM_6_1", b"MOM_6_2"))
        _raises(log.rows, CardRefused, "chain broken")


test_gov10_contamination_log_append_only_and_overlap.test_ids = ["T-TF-GOV-10"]


# --------------------------------------------------------------------------- #
# GOV-11 S_beta comparator
# --------------------------------------------------------------------------- #
def test_gov11_s_beta_book_and_the_prior_252_session_beta_window():
    rng = np.random.default_rng(SEED)
    m = rng.normal(0.0004, 0.01, 600)
    book = np.where(np.arange(600) < 400, 0.5 * m, 2.0 * m) + rng.normal(0, 0.002, 600)
    b = TG.beta_hat(book, m, 400)
    assert abs(b - 0.5) < 0.05                                   # rows 148..399 only
    assert inspect.signature(TG.beta_hat).parameters["window"].default == TG.BETA_WINDOW == 252
    for i, changes in ((147, False), (148, True), (399, True), (400, False), (500, False)):
        bk = book.copy()
        bk[i] += 0.05
        assert (TG.beta_hat(bk, m, 400) != b) is changes, i
    _raises(lambda: TG.beta_hat(book, m, 251), TG.GovRefused, "252 sessions")
    cash = np.full(600, 0.0001)
    s = TG.s_beta_book(m, cash, b)
    assert np.allclose(s, b * m + (1 - b) * cash)
    assert np.allclose(TG.s_beta_book(m, 0.0001, 0.6), 0.6 * m + 0.4 * 0.0001)
    for bad in (1.2, -0.1, float("nan")):
        _raises(lambda bad=bad: TG.s_beta_book(m, cash, bad), TG.GovRefused, "outside [0, 1]")


test_gov11_s_beta_book_and_the_prior_252_session_beta_window.test_ids = ["T-TF-GOV-11"]


# --------------------------------------------------------------------------- #
# INV-1 / INV-5
# --------------------------------------------------------------------------- #
def test_inv1_decide_at_close_fill_at_official_close_on_the_costed_engine():
    from core.engine import orders as O
    rng = np.random.default_rng(SEED)
    P = 100 * np.cumprod(1 + rng.normal(0.0003, 0.01, 300))
    r = np.concatenate([[0.0], P[1:] / P[:-1] - 1])             # r[t] = close t-1 -> close t
    w = np.clip(rng.normal(0.6, 0.3, 300), 0, 1)                 # decided at the close of t
    we = C.earning_weights(w)
    assert np.isnan(we[0]) and np.array_equal(we[1:], w[:-1])    # a weight decided at close t earns from t+1
    path = C.costed_path(we, r, 0.0)
    assert np.allclose(path.gross[1:], w[:-1] * r[1:])           # filled at the official close of t
    pnl, _ = S.simulate(P[:, None], w[:, None], cost_bps=0.0)    # the legacy engine holds row t over t -> t+1
    assert np.allclose(pnl, path.gross[1:])
    line = TG.inv1_bound_line(w, r, 3.0)
    assert np.allclose(line["bound_close_t1"], C.costed_path(C.earning_weights(we), r, 3.0).net)
    assert np.allclose(line["primary_close_t"], C.costed_path(we, r, 3.0).net) and "reported, not gated" in line["line"]
    model = O.fill_model("KRX")
    assert model.fill == "official_close" and {"NXT", "after_hours"} <= set(O.REFUSED_PRINT_SOURCES)


test_inv1_decide_at_close_fill_at_official_close_on_the_costed_engine.test_ids = ["T-TF-INV-01"]


_STOP_NEEDLES = ("stop_loss", "stoploss", "stop_price", "trailing_stop", "stop_out", "stop_pct", "stop_level", "hard_stop")
_STOP_ALLOWED = {"expiry_day_stop_local"}                        # futures trading cut-off time (R-26 rule 5), not a stop-loss


def _stop_hits(src: str, label: str) -> list[str]:
    tree = ast.parse(src)
    hits = [f"{label}: needle {n}" for n in _STOP_NEEDLES if n in src.lower()]
    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            args = n.args.posonlyargs + n.args.args + n.args.kwonlyargs
            hits += [f"{label}:{n.lineno} {n.name}({a.arg})" for a in args if "stop" in a.arg.lower() and a.arg not in _STOP_ALLOWED]
        if isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name) and "stop" in n.target.id.lower() \
                and n.target.id not in _STOP_ALLOWED:
            hits.append(f"{label}:{n.lineno} field {n.target.id}")
    return hits


def test_inv5_no_name_level_stop_path_in_tf_books_or_the_fill_model():
    assert _stop_hits("def book(w, *, stop_loss=0.15):\n    return w\n", "probe")              # positive controls
    assert _stop_hits("class B:\n    trail_stop: float = 0.1\n", "probe")
    orders = (ROOT / "core" / "engine" / "orders.py").read_text(encoding="utf-8")
    fill = orders[orders.index("# R-27 simulated fill model"):]
    hits = _stop_hits(fill, "core/engine/orders.py (fill model)")
    from core.engine import orders as O
    assert not any("stop" in r for r in O.NONFILL_REASONS) and not any("stop" in s for s in O.CARRY_LABELS)
    books = ROOT / "core" / "quant" / "tf_books.py"
    if not books.is_file():
        assert not hits, hits
        raise NotRun("PENDING: core/quant/tf_books.py (package B) is not in the tree; the fill model scanned clean")
    hits += _stop_hits(books.read_text(encoding="utf-8"), "core/quant/tf_books.py")
    assert not hits, hits


test_inv5_no_name_level_stop_path_in_tf_books_or_the_fill_model.test_ids = ["T-TF-INV-05"]


# --------------------------------------------------------------------------- #
# The tech-fund card runner: KRX cards refused, drafts with typed nulls
# --------------------------------------------------------------------------- #
def _null_paths(o, path="") -> set[str]:
    if isinstance(o, dict):
        out = set()
        for k, v in o.items():
            out |= _null_paths(v, f"{path}.{k}" if path else k)
        return out
    return {path} if o is None else set()


def test_krx_cards_refuse_without_the_panel_and_drafts_carry_typed_nulls():
    import docs.techfund_study as TS
    assert list(TS.DRAFTS) == ["SCR-1", "SCR-2", "FS-1", "FS-2", "FS-3", "FS-4", "FS-5"]
    for cid in TS.DRAFTS:
        try:
            TS.run_card(cid)
        except TS.CardRefused as exc:
            reason = exc.reason
        else:
            raise AssertionError(f"{cid} ran")
        assert reason.startswith(("REFDATA:", "PENDING:")), reason
        d = TS.draft(cid)
        assert d["run_status"] == "NOT_RUN" and d["verdict"] is None and d["blocked_by"] == reason
        body = {k: v for k, v in d.items() if k not in ("nulls", "lab_reference", "what_would_change_it")}
        assert _null_paths(body) == set(d["nulls"]), cid                      # every null is typed, no untyped null
        assert all(v.startswith(("REFDATA:", "OWNER:", "PENDING:")) for v in d["nulls"].values()), cid
        assert d["nulls"]["verdict"] == reason and "proposal" in d["proposal_status"]
        assert d["evaluation"]["step9"].startswith("expected live = 0.6 x OOS")
    for cid in ("SCR-1", "SCR-2"):
        d = TS.draft(cid)
        assert d["class"] == "CARD-O" and d["primary_statistic"] == "long_only_net_excess"
        assert d["benchmarks"] == ["EW", "CW", "CW_ex_pair", "capped_CW"] and "KRX all-stock daily panel" in d["blocked_by"]
        assert d["cost_detail"]["per_side_bp"] == 35.0 and d["costs"]["per_side"] == "read_from_gate" and d["break_even"]["pre_gate_screen"].startswith("REJECT if < 2 x 35 bp")
    assert all(TS.draft(c)["build_status"] == "FORWARD_SIM" and TS.draft(c)["book"] == f"forward_sim:{c}" for c in TS.DRAFTS if c.startswith("FS-"))
    assert "KOSPI" in TS.refusal("FS-1") and TS.refusal("FS-4").startswith("PENDING:")
    with tempfile.TemporaryDirectory() as tmp:
        paths = TS.write_drafts(Path(tmp))
        assert sorted(p.name for p in paths) == sorted(f"{c}.draft.json" for c in TS.DRAFTS)
        for p in paths:
            assert json.loads(p.read_text(encoding="utf-8")) == TS.draft(p.name.split(".")[0])
    for p in sorted((ROOT / "docs" / "techfund").glob("*.draft.json")):        # the shipped drafts are in sync
        assert json.loads(p.read_text(encoding="utf-8")) == TS.draft(p.name.split(".")[0]), p.name
    buf = io.StringIO()
    with redirect_stdout(buf):
        assert TS.main(["--run", "SCR-1"]) == 2
    assert "run refused: SCR-1: REFDATA:" in buf.getvalue()


test_krx_cards_refuse_without_the_panel_and_drafts_carry_typed_nulls.test_ids = ["T-TF-CARD-01"]


def test_krx_tech_fund_card_formal_runs_need_the_krx_panel():
    import docs.techfund_study as TS
    raise NotRun(TS.refusal("SCR-1"))


test_krx_tech_fund_card_formal_runs_need_the_krx_panel.test_ids = ["T-TF-CARD-01"]


# --------------------------------------------------------------------------- #
# CRY-1: the C3 controls run offline end to end on the local caches
# --------------------------------------------------------------------------- #
def test_cry1_study_runs_offline_end_to_end_on_the_local_caches():
    import docs.techfund_study as TS
    for name in TS.SERIES:
        if not (TS.CACHE / f"{name}.csv").is_file():
            raise NotRun(f"REFDATA: docs/asset_expansion/cache/{name}.csv (local vendor cache) absent")
    cards_dir = ROOT / "docs" / "asset_expansion" / "cards"
    before = _md5_tree(cards_dir)
    card = json.loads(TS.C3_CARD.read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory() as tmp:
        reg_dir, out = Path(tmp) / "ledgers", Path(tmp) / "out"
        t0 = time.perf_counter()
        res = TS.run_cry1(out_dir=out, registry_dir=reg_dir, run_utc=RUN_UTC, seed=SEED)
        assert time.perf_counter() - t0 < 180.0
        reg = TG.trial_registry(reg_dir)
        assert reg.n_rows == 3 and reg.global_n() == 3                          # exactly the three extra trials of C3
        assert sorted(p.name for p in out.glob("*.json")) == sorted(CRY1_FILES) == sorted(res)
        for f in CRY1_FILES:
            j = json.loads((out / f).read_text(encoding="utf-8"))
            assert j["label"] == "vendor data, labelled trial, not a formal card run" and j["run_mode"] == "labelled_trial"
            assert j["seed"] == SEED and j["B"] == 2000 and j["cost_bp_per_side"] == 10.0 and j["item"] == "CRY-1"
            t = j["trials"]
            assert (t["card_N_total"], t["extra_trials"], t["N_after_cry1"], t["registered_rows_appended"]) == (11, 3, 14, 3)
            assert "16 trading cards" in j["bonferroni_note"] and j["c3_verdict"].startswith("PASS, unchanged")
        ctrl = json.loads((out / "cry1_volscaled_control.json").read_text(encoding="utf-8"))["results"]
        repro = ctrl["upbit_KRW-BTC"]["c3_reproduction"]                       # the wiring reproduces card C3 (KRW-BTC)
        assert repro["decision"] == card["decision"] == "PASS"
        assert abs(repro["sr_oos"] - card["stats"]["sr_oos"]) < 1e-9 and repro["bench_p"] == card["stats"]["bench_p"]
        for name in TS.BTC_SERIES:
            vs = ctrl[name]["c3_vs_control"]
            assert vs["benchmark"] == "vol_scaled_long_only_control" and vs["n_trials"] == 14
            assert vs["decision"] in V.DECISIONS and vs["gov"]["gov4"]["decision"] in V.DECISIONS
            assert vs["gov"]["gov4"]["block_step5"] >= 10 and vs["gov"]["step9"]["multiplier"] == 0.6
            assert 0 < ctrl[name]["control"]["avg_exposure"] <= 1.0
        split = json.loads((out / "cry1_split_2024-01-10.json").read_text(encoding="utf-8"))["results"]
        for name in TS.BTC_SERIES:
            s = split[name]
            assert s["pre"]["end"] < "2024-01-10" <= s["post"]["start"]
            assert s["post_dsr_le_0"] == (s["post"]["dSR"] <= 0)
        eth = json.loads((out / "cry1_eth_replication.json").read_text(encoding="utf-8"))["results"]["binance_ETHUSDT"]
        assert eth["decision"] in V.DECISIONS and eth["n_trials"] == 14 and eth["benchmark"] == "buy_and_hold"
        cut = json.loads((out / "cry1_cut_time.json").read_text(encoding="utf-8"))
        assert cut["status"] == "NOT_RUN" and cut["reason"].startswith("REFDATA:") and "intraday" in cut["reason"]
    assert _md5_tree(cards_dir) == before                                       # docs/asset_expansion/cards untouched


test_cry1_study_runs_offline_end_to_end_on_the_local_caches.test_ids = ["T-TF-CRY-01"]


def test_cry1_cut_time_sensitivity_needs_intraday_candles():
    import docs.techfund_study as TS
    intraday = [p.name for p in TS.CACHE.glob("*.csv") if re.search(r"(1h|1m|5m|15m|hour|intraday)", p.name, re.I)]
    if not intraday:
        raise NotRun("REFDATA: intraday BTC candles absent from docs/asset_expansion/cache (daily closes only); the "
                     "00:00 UTC / 00:00 KST / 21:00 UTC cut-time test of CRY-1 is not run (D-24: not counted as a trial)")
    raise AssertionError(f"intraday candles {intraday} are present: write the cut-time test before counting a fourth trial")


test_cry1_cut_time_sensitivity_needs_intraday_candles.test_ids = ["T-TF-CRY-01"]


# --------------------------------------------------------------------------- #
# Rulings scan
# --------------------------------------------------------------------------- #
def test_tf_gov_and_runner_rulings_scan_no_clock_no_gate_read_no_new_dependency():
    import sys
    forbidden = {"datetime.now", "datetime.utcnow", "time.time", "date.today", "datetime.today"}
    std = set(sys.stdlib_module_names)
    for rel in ("core/quant/tf_gov.py", "docs/techfund_study.py"):
        src = (ROOT / rel).read_text(encoding="utf-8")
        tree = ast.parse(src)
        main = next((n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "main"), None)
        allowed = range(main.lineno, main.end_lineno + 1) if (main and rel.startswith("docs/")) else range(0)
        hits = [(ast.unparse(n.func), n.lineno) for n in ast.walk(tree) if isinstance(n, ast.Call) and ast.unparse(n.func) in forbidden]
        assert all(ln in allowed for _, ln in hits), (rel, hits)
        mods = {n.module.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module} | \
               {a.name.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
        assert not {m for m in mods if m not in std and m not in {"numpy", "scipy", "pandas", "core", "config"}}, (rel, mods)
        assert "arch" not in mods
    gov = (ROOT / "core/quant/tf_gov.py").read_text(encoding="utf-8")
    assert "GATE[" not in gov and "GATE.get" not in gov and "config" not in {n.module for n in ast.walk(ast.parse(gov)) if isinstance(n, ast.ImportFrom)}
    study = (ROOT / "docs/techfund_study.py").read_text(encoding="utf-8")
    assert "asset_expansion_study" not in study                 # the legacy runner (mkdir at import) is never imported


test_tf_gov_and_runner_rulings_scan_no_clock_no_gate_read_no_new_dependency.test_ids = ["T-TF-SCAN-01"]


if __name__ == "__main__":
    from tests.macro_acceptance import run_module
    raise SystemExit(run_module(globals()))
