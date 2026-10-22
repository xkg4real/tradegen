"""Sprint 7 package B tests: tech-fund screens, panel hygiene, books, bands, caps, composite
(core/quant/tf_screens.py, core/quant/tf_books.py).

Test ids: T-TF-UNIV-01, T-TF-SCR-02, T-TF-CA-01 are the QA-named tests (tf_chairs_qa D.3, expectations verbatim);
every other T-TF-* id here is reconstructed (tf_chairs_qa F-19). Synthetic panels are seeded (11). Lab numbers are
reference constants read from the research bundle (or package A's data/techfund copy) by file and line; the KRX
all-stock panel is absent, so its runs are NOT_RUN (REFDATA). Hermetic: nothing is written anywhere.
"""
from __future__ import annotations

import ast
import csv
import math
from datetime import date, timedelta
from pathlib import Path

import numpy as np

from core.quant import tf_books as B
from core.quant import tf_screens as S
from core.quant.sleeves import vol_scale_from_returns
from core.quant.validate import newey_west_t
from tests.notrun import NotRun

ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / "QUANTGEN_techfund_research_bundle" / "QUANTGEN_techfund_research"
KRX_PANEL_PATHS = (ROOT / "data" / "techfund" / "marcap", Path("/home/claude/data_raw/marcap/data"))


def _raises(fn, exc=Exception, needle=""):
    try:
        fn()
    except exc as e:
        assert needle.lower() in str(e).lower(), (needle, str(e))
        return e
    raise AssertionError(f"expected {exc.__name__} containing {needle!r}")


def _lab(rel: str) -> Path:
    """Package A's shipped copy data/techfund/<name> first, else the bundle's datalab/results/<rel>."""
    for p in (ROOT / "data" / "techfund" / Path(rel).name, BUNDLE / "datalab" / "results" / rel):
        if p.is_file():
            return p
    raise NotRun(f"REFDATA: {rel} (neither data/techfund nor the research bundle holds it)")


def _csv_line(path: Path, line: int) -> dict:
    """Row at a 1-based file line (header = line 1), as the golden-value `line` column counts."""
    lines = path.read_text(encoding="utf-8").splitlines()
    header = next(csv.reader([lines[0]]))
    return dict(zip(header, next(csv.reader([lines[line - 1]]))))


def _goldens() -> dict[str, dict]:
    with _lab("r3/r3_golden_values.csv").open(encoding="utf-8", newline="") as fh:
        return {r["gv_id"]: r for r in csv.DictReader(fh)}


def _sessions(start: date, n: int) -> tuple:
    out, d = [], start
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d)
        d += timedelta(days=1)
    return tuple(out)


def _arrays(T: int = 300, N: int = 16, seed: int = 11, start: date = date(2024, 1, 2)) -> dict:
    rng = np.random.default_rng(seed)
    ret = rng.normal(0.0004, 0.02, (T, N)).astype(np.float32)
    close = (5000.0 * np.exp(np.cumsum(ret, axis=0))).astype(np.float32)
    volume = rng.uniform(1e5, 1e6, (T, N))
    shares = np.tile(rng.uniform(1e6, 1e8, N), (T, 1))
    return {"dates": _sessions(start, T), "codes": tuple(f"{i:05d}0" for i in range(N)), "close": close,
            "high": (close * 1.01).astype(np.float32), "low": (close * 0.99).astype(np.float32), "ret": ret,
            "volume": volume, "amount": (close * volume).astype(np.float32),
            "marcap": (close * shares).astype(np.float32), "shares": shares,
            "market": np.tile(np.where(np.arange(N) % 2 == 0, 1, 2).astype(np.int8), (T, 1)),
            "name_cls": np.zeros((T, N), np.int8), "exists": np.ones((T, N), bool)}


# --------------------------------------------------------------------------- #
# T-TF-UNIV-01: codes, classifier, eligibility (INV-3), ALL / LARGE, RX-05
# --------------------------------------------------------------------------- #
def test_univ_01_codes_and_the_five_class_classifier():
    assert S.pad_code("5930") == S.pad_code(5930) == "005930" and S.is_common("5930") and not S.is_common("005935")
    cases = {"메리츠화재": "", "블리츠웨이": "", "두산인프라코어": "", "인터리츠": "", "삼성전자": "",
             "맥쿼리센트럴": "REIT", "교보메리츠": "REIT", "케이탑리츠": "REIT", "바다로3호": "FUND", "박현주1호": "FUND",
             "맥쿼리인프라": "INFRA_FUND", "삼성 스팩 1호": "SPAC", "미래에셋 레버리지 ETN": "DR_ETN"}
    got = {n: S.classify_name(n) for n in cases}
    assert got == cases, got
    rows = []
    for d in (date(1999, 1, 4), date(1999, 1, 5)):
        for code, market, name in (("5930", "KOSPI", "삼성전자"), ("5935", "KOSPI", "삼성전자우"),
                                   ("12340", "KONEX", "코넥스"), ("35720", "KOSDAQ GLOBAL", "카카오")):
            rows.append({"Date": d, "Code": code, "Name": name, "Market": market, "Close": 10000, "High": 10100,
                         "Low": 0, "Volume": 10, "Amount": 1e5, "Marcap": 1e11, "Stocks": 1e7, "ChangesRatio": 1.0})
    P = S.build_panel(rows)
    assert P.codes == ("005930", "035720"), P.codes          # '5930' padded; preferred and KONEX dropped
    assert P.market[0].tolist() == [1, 2] and P.low[0, 0] == P.close[0, 0] and P.close.dtype == np.float32
    assert abs(float(P.ret[0, 0]) - 0.01) < 1e-7


test_univ_01_codes_and_the_five_class_classifier.test_ids = ["T-TF-UNIV-01"]


def test_univ_01_each_condition_excludes_a_constructed_name_on_t_minus_1():
    a = _arrays(N=16)
    T = len(a["dates"])
    t, s = T - 1, T - 2
    a["codes"] = tuple("000015" if j == 1 else c for j, c in enumerate(a["codes"]))   # not a common share
    a["close"][s, 2] = 900                                                               # price < 1,000
    for j, cls in ((3, "SPAC"), (4, "REIT"), (5, "FUND")):
        a["name_cls"][s, j] = S.NAME_CLASSES.index(cls)
    a["volume"][s - 200:s - 140, 6] = 0                                                  # 192 valid days < 200
    a["amount"][s - 3:s - 1, 7] = 0                                                      # Amount > 0 on 3 of 5
    a["volume"][s, 8] = 0                                                                # not traded on s
    bnc = np.zeros((T, 16), bool)
    bnc[s - 10, 9] = True                                                                # beyond-limit, no CA
    a["exists"][s, 10] = False
    a["marcap"][s, 11] = 0
    a["market"][:, 12] = 0                                                               # not KOSPI / KOSDAQ
    a["close"][t, 14] = 900                                                              # only on t
    a["name_cls"][t, 15] = S.NAME_CLASSES.index("SPAC")                                  # only on t
    P = S.Panel(**a, beyond_nonca=bnc)
    lagged = S.eligible(P, t)                                                            # INV-3: rows <= t-1
    assert np.flatnonzero(lagged).tolist() == [0, 13, 14, 15], np.flatnonzero(lagged)
    lab = S.eligible(P, t, as_of="close_t")                                              # lab: rows <= t
    assert lab[0] and lab[13] and not lab[14] and not lab[15] and lab[2] and lab[8]
    _raises(lambda: S.eligible(P, t, as_of="t"), ValueError, "as_of")
    assert not S.eligible(P, 250).any()                                                  # < 252 rows of history


test_univ_01_each_condition_excludes_a_constructed_name_on_t_minus_1.test_ids = ["T-TF-UNIV-01"]


def test_univ_01_all_large_and_rx05():
    a = _arrays(N=40, seed=12)
    T = len(a["dates"])
    t, s = T - 1, T - 2
    P = S.Panel(**a)
    elig = S.eligible(P, t)
    mc = P.marcap[s].astype(np.float64)
    cut = np.quantile(mc[elig], 0.20)
    ALL = S.universe_all(P, t)
    assert np.array_equal(ALL, elig & (mc >= cut)) and 0 < ALL.sum() < elig.sum()
    large = S.universe_large(P, t, n=5)
    assert set(np.flatnonzero(large)) == set(np.argsort(-mc)[:5])
    # RX-05: cap >= 100bn or top-n at the prior month-end; ADV20 >= 1bn; listed 60 sessions; no admin designation
    a = _arrays(N=6, seed=13)
    a["marcap"][:] = 2e11
    a["marcap"][:, 1] = 5e10                                           # small cap, not in the top 1 -> out
    a["amount"][:] = 2e9
    a["amount"][:, 2] = 5e8                                            # ADV20 < 1bn -> out
    a["exists"][:T - 256, 3] = False                                   # listed 255 sessions (>= 200 valid days)
    a["ret"][:T - 256, 3] = np.nan
    adm = np.zeros(a["close"].shape, bool)
    adm[s, 4] = True                                                   # administrative designation -> out
    P = S.Panel(**a, admin=adm)
    assert S.eligible(P, t).all()
    rx = S.eligible(P, t, rx05=True, top_n=1)
    assert np.flatnonzero(rx).tolist() == [0, 3, 5], np.flatnonzero(rx)
    assert np.flatnonzero(S.eligible(P, t, rx05=True, top_n=1, min_listed=260)).tolist() == [0, 5]
    a2 = dict(a)
    a2["marcap"] = a["marcap"].copy()
    a2["marcap"][:, 1] = 9e11                                          # now the largest: top 1 at the month-end
    assert np.flatnonzero(S.eligible(S.Panel(**a2), t, rx05=True, top_n=1, cap_min=1e12)).tolist() == [1]


test_univ_01_all_large_and_rx05.test_ids = ["T-TF-UNIV-01"]


# --------------------------------------------------------------------------- #
# T-TF-CA-01: share-count changes, split-like days, DIL_LIT / DIL_NI, |dln shares| > 1%
# --------------------------------------------------------------------------- #
def _ca_panel():
    T, N = 300, 4
    a = _arrays(T=T, N=N, seed=21)
    a["close"][:] = 10000
    a["ret"][:] = 0
    a["shares"] = np.full((T, N), 1e6)
    a["shares"][100:, 0] *= 1.2
    a["close"][100:, 0] = 9500                         # 20% rights issue, close -5% -> not split-like
    a["shares"][120:, 1] *= 0.2
    a["close"][120:, 1] = 47500                        # 5:1 reverse split, close x 4.75 -> |s p - 1| = 0.05
    a["shares"][10:, 2] *= 1.5                         # outside the 252-session window at t = 299
    a["shares"][200:, 2] *= 1.03
    a["shares"][250:, 2] *= 1.05
    a["shares"][150:, 3] *= 1.0005                     # |s - 1| <= 0.001: not a change day
    a["shares"][160:, 3] *= 1.005                      # change day, |dln| < 1%
    return S.Panel(**a)


def test_ca_01_split_like_rule_and_dil_lit():
    P = _ca_panel()
    terms = S.share_change_terms(P)
    assert not terms["split_like"][100, 0] and terms["split_like"][120, 1]
    assert not terms["change"][150, 3] and terms["change"][160, 3]
    dil = S.dilution_at(P, 299, terms=terms)
    lit = dil["DIL_LIT"]
    assert lit.dtype == np.float32
    expect = np.array([0.2, 0.0, 1.03 * 1.05 - 1, 1.0005 * 1.005 / 1.0005 - 1], dtype=np.float32)
    assert np.allclose(lit, expect, atol=1e-7), lit
    # DIL_LIT matches exp(sum ln s) - 1 over the non-split-like change days of t-251..t
    s = terms["s"][48:300, 2]
    keep = np.abs(s - 1) > 0.001
    assert abs(float(lit[2]) - math.expm1(np.log(s[keep]).sum())) < 1e-7
    # net issuance: the reverse split is undone by the KRX base-price adjustment factor (r = 0 on that day)
    assert abs(float(dil["DIL_NI"][1]) - (0.2 * 4.75 - 1)) < 1e-6
    assert S.dilution_flag(lit).tolist() == [True, False, False, False]
    ca = S.corporate_action_flag(P)
    assert ca[100, 0] and ca[120, 1] and ca[200, 2] and ca[250, 2] and not ca[160, 3] and not ca[150, 3]
    assert ca.sum() == 5 and not ca[0].any()


test_ca_01_split_like_rule_and_dil_lit.test_ids = ["T-TF-CA-01"]


# --------------------------------------------------------------------------- #
# T-TF-SCR-02: DIL_LIT float32 tie at 10.0% is flagged
# --------------------------------------------------------------------------- #
def test_scr_02_dil_lit_float32_tie_rule():
    assert S.dilution_flag([0.11, 0.099, np.nan]).tolist() == [True, False, False]
    a = _arrays(T=300, N=2, seed=22)
    a["shares"] = np.full((300, 2), 1e6)
    a["shares"][200:, 0] = 1.1e6                       # a 10.0% increase (s = 1.1)
    a["close"][:] = 10000
    P = S.Panel(**a)
    lit = S.dilution_at(P, 299)["DIL_LIT"]
    assert lit[0] == np.float32(0.1) and lit[1] == 0
    assert S.dilution_flag(lit).tolist() == [True, False]
    assert S.dilution_flag(np.float64(0.1) - 1e-12)                  # rounds to float32 0.1: inside the inclusive cut
    assert not (np.array([0.1], np.float32) > 0.10)[0]                # why the promotion is explicit (numpy >= 2)
    U = np.ones(2, bool)
    feat = {k: np.array([1.0, 2.0], np.float32) for k in ("TURN_1M", "VOL_3M", "MAX_1M")}
    assert S.screen_flags(feat, U, 0, dil_lit=lit)["F6"].tolist() == [True, False]


test_scr_02_dil_lit_float32_tie_rule.test_ids = ["T-TF-SCR-02"]


# --------------------------------------------------------------------------- #
# T-TF-SCR-01: F4 ordinal cut floor(0.10 n), ranking primitives, F1..F8, book-type weights
# --------------------------------------------------------------------------- #
def test_scr_01_f4_cut_size_and_ordinal_stability():
    rng = np.random.default_rng(11)
    for n in (25, 30, 47, 99, 100, 101, 250, 999):
        v, m, tr = rng.normal(size=(3, n))
        f4 = S.p6_composite(v, m, tr, np.ones(n, bool))
        assert f4.sum() == n // 10, (n, f4.sum())
    n = 100
    v, m, tr = rng.random((3, n))
    v[:10] += 10
    m[:10] += 10
    tr[:10] += 10                                       # names 0..9: highest vol, MAX and turnover
    U = np.ones(n, bool)
    assert np.flatnonzero(S.p6_composite(v, m, tr, U)).tolist() == list(range(10))
    x = rng.normal(size=n)                              # distinct composites: the set does not depend on column order
    perm = rng.permutation(n)
    f = S.p6_composite(x, x, x, U)
    fp = S.p6_composite(x[perm], x[perm], x[perm], U)
    assert set(perm[fp]) == set(np.flatnonzero(f)) == set(np.argsort(-x)[:10])
    tied = np.ones(n)                                   # all tied: count still floor(0.1 n), stable order = first 10
    ft = S.p6_composite(tied, tied, tied, U)
    assert ft.sum() == 10 and np.flatnonzero(ft).tolist() == list(range(10))
    assert np.array_equal(ft, S.p6_composite(tied, tied, tied, U))
    U2 = U.copy()
    U2[:50] = False
    v2 = v.copy()
    v2[60] = np.nan                                     # not finite -> outside the composite
    f2 = S.p6_composite(v2, m, tr, U2)
    assert f2.sum() == 49 // 10 and not f2[:50].any() and not f2[60]


test_scr_01_f4_cut_size_and_ordinal_stability.test_ids = ["T-TF-SCR-01"]


def test_scr_01_quantile_groups_top_frac_and_flags():
    rng = np.random.default_rng(11)
    x = rng.normal(size=100)
    U = np.ones(100, bool)
    g = S.quantile_groups(x, U, 5, 0)
    assert np.bincount(g, minlength=6)[1:].tolist() == [20] * 5 and g[np.argmax(x)] == 5 and g[np.argmin(x)] == 1
    assert np.array_equal(S.top_frac(x, U, 0.20), g == 5)
    assert not S.quantile_groups(x[:24], U[:24], 5).any() and not S.top_frac(x[:24], U[:24], 0.2).any()
    ties = np.r_[np.zeros(60), rng.normal(size=40)]      # a 60-name tie block would empty groups: seeded fallback
    gt = S.quantile_groups(ties, U, 5, 7)
    assert np.bincount(gt, minlength=6)[1:].min() >= 10 and np.array_equal(gt, S.quantile_groups(ties, U, 5, 7))
    feat = {k: rng.normal(size=100).astype(np.float32) for k in ("TURN_1M", "VOL_3M", "MAX_1M")}
    U3 = U.copy()
    U3[::4] = False
    f5 = rng.random(100) < 0.05
    dil = np.where(rng.random(100) < 0.1, 0.2, 0.0)
    fl = S.screen_flags(feat, U3, 3, dil_lit=dil, f5=f5)
    assert set(fl) == {"F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8"}
    assert all(not (f & ~U3).any() for f in fl.values())
    assert np.array_equal(fl["F7"], fl["F1"] | fl["F2"] | fl["F3"])
    assert np.array_equal(fl["F8"], fl["F4"] | fl["F5"] | fl["F6"])
    assert fl["F4"].sum() == U3.sum() // 10 and fl["F1"].sum() == U3.sum() // 5
    assert set(S.screen_flags(feat, U3, 3)) == {"F1", "F2", "F3", "F4", "F7"}
    assert {b: S.screen_mask(fl["F4"], b)[1] for b in S.SCREEN_WEIGHT} == {"EW": 3, "small_mid": 3, "capped_CW": 1,
                                                                            "top200": 0}
    assert np.array_equal(S.screen_mask(fl["F4"], "EW")[0], fl["F4"]) and not S.screen_mask(fl["F4"], "top200")[0].any()
    _raises(lambda: S.screen_mask(fl["F4"], "VW"), ValueError, "book_type")
    assert {b: S.SCREEN_WEIGHT[B.BASE_BOOK_TYPE[b]] for b in B.BASES} == {"B1": 3, "B2": 1, "B3": 0, "B4": 3}


test_scr_01_quantile_groups_top_frac_and_flags.test_ids = ["T-TF-SCR-01"]


def test_scr_01_features_and_attention_fade_on_a_synthetic_panel():
    a = _arrays(T=300, N=6, seed=31)
    a["volume"][:] = 1e5
    a["ret"][:, 0] *= 0.1                                      # quiet column: the spike is its 1-month MAX
    a["ret"][280, 0], a["volume"][280, 0] = 0.06, 6e5         # volume spike with r >= 5%
    a["close"][285, 1] = a["high"][285, 1]
    a["ret"][285, 1] = 0.30                                    # locked limit-up by E7's 29.5% rule (2025 date)
    P = S.Panel(**a, cr=a["ret"].copy())
    ev = S.attention_fade_events(P)
    assert ev[280, 0] and ev[285, 1]
    f5 = S.f5_flag(ev, P.exists[299], 299)
    assert f5[0] and f5[1] and not S.f5_flag(ev, P.exists[299], 299, window=10)[0]
    ft = S.features_at(P, 299)
    assert all(v.dtype == np.float32 for v in ft.values())
    r = P.ret[237:300, 2].astype(np.float64)
    assert abs(float(ft["VOL_3M"][2]) - r.std(ddof=1)) < 1e-6
    assert abs(float(ft["MAX_1M"][0]) - 0.06) < 1e-7
    cl = P.cumlog
    assert abs(float(ft["MOM_12_1"][3]) - math.expm1(cl[278, 3] - cl[47, 3])) < 1e-5
    assert abs(float(ft["REV_1M"][3]) - math.expm1(cl[299, 3] - cl[278, 3])) < 1e-5
    turn = (P.amount[279:300, 4].astype(np.float64) / P.marcap[279:300, 4]).mean()
    assert abs(float(ft["TURN_1M"][4]) / turn - 1) < 1e-5


test_scr_01_features_and_attention_fade_on_a_synthetic_panel.test_ids = ["T-TF-SCR-01"]


# --------------------------------------------------------------------------- #
# T-TF-LOCK-01: limit-lock detection at each KRX limit era
# --------------------------------------------------------------------------- #
ERAS = ((S.KOSPI, date(1996, 1, 3), 6), (S.KOSPI, date(1996, 11, 25), 8), (S.KOSPI, date(1998, 6, 1), 12),
        (S.KOSPI, date(2005, 1, 4), 15), (S.KOSPI, date(2016, 1, 4), 30), (S.KOSDAQ, date(1997, 1, 3), 8),
        (S.KOSDAQ, date(1999, 1, 4), 12), (S.KOSDAQ, date(2006, 1, 2), 15), (S.KOSDAQ, date(2026, 6, 23), 30))


def _lock_panel(eras, cr_pp=None, *, cr_fixed=None, side: str = "up", cc: int = 0, volume: float = 1.0):
    """One column per (market, date, L) era row; on its date the column closes at its high (up) or low (down) with
    |r| = L - cr_pp (or cr_fixed) percent; every other cell has r = 0."""
    n = len(eras)
    dates = tuple(sorted({d for _, d, _ in eras}))
    T = len(dates)
    close = np.full((T, n), 10000.0, np.float32)
    hi = close * (1.0 if side == "up" else 1.05)
    lo = close * (0.95 if side == "up" else 1.0)
    cr = np.zeros((T, n), np.float32)
    market = np.zeros((T, n), np.int8)
    for j, (m, d, L) in enumerate(eras):
        pp = cr_fixed if cr_fixed is not None else L - cr_pp
        cr[dates.index(d), j] = pp / 100.0 * (1 if side == "up" else -1)
        market[:, j] = m
    a = {"dates": dates, "codes": tuple(f"{j:05d}0" for j in range(n)), "close": close, "high": hi.astype(np.float32),
         "low": lo.astype(np.float32), "ret": cr, "volume": np.full((T, n), volume), "amount": close.copy(),
         "marcap": close.copy(), "shares": np.ones((T, n)), "market": market, "name_cls": np.zeros((T, n), np.int8),
         "exists": np.ones((T, n), bool)}
    return S.Panel(**a, cr=cr, change_code=np.full((T, n), cc, np.int8)), dates


def test_lock_01_limit_lock_at_each_krx_limit_era():
    for m, d, L in ERAS:
        assert S.lab_price_limit(m, d) == L / 100.0, (m, d)
    assert S.lab_price_limit(S.KOSPI, date(1996, 11, 22)) == 0.06 and S.lab_price_limit(S.KOSDAQ, date(1998, 5, 22)) == 0.08

    def cells(dates):
        return [(dates.index(d), j) for j, (_, d, _) in enumerate(ERAS)]

    for side, which in (("up", 0), ("down", 1)):
        Pin, dates = _lock_panel(ERAS, 0.4, side=side)       # |r| = L - 0.4 pp >= L - 0.5 pp: locked
        Pout, _ = _lock_panel(ERAS, 0.6, side=side)          # L - 0.6 pp: not locked
        masks = S.limit_lock_mask(Pin)
        assert all(masks[which][i, j] for i, j in cells(dates)) and masks[which].sum() == len(ERAS), side
        assert not masks[1 - which].any() and not any(S.limit_lock_mask(Pout)[w].any() for w in (0, 1)), side
    Pcc, dates = _lock_panel(ERAS, cr_fixed=5.0, cc=4)      # +5% close at the high with the old ChangeCode 4
    assert all(S.limit_lock_mask(Pcc)[0][i, j] for i, j in cells(dates))
    Pv, _ = _lock_panel(ERAS, 0.4, volume=0.0)               # not traded: never a locked close
    assert not S.limit_lock_mask(Pv)[0].any()
    # era switch on 1996-11-25: a +5.6% close at the high is locked under the 6% limit, not under the 8% limit
    sw, dates = _lock_panel(((S.KOSPI, date(1996, 11, 22), 6), (S.KOSPI, date(1996, 11, 25), 8)), cr_fixed=5.6)
    lu = S.limit_lock_mask(sw)[0]
    assert lu[0, 0] and not lu[1, 1]


test_lock_01_limit_lock_at_each_krx_limit_era.test_ids = ["T-TF-LOCK-01"]


def test_lock_01_regime_tag_source_and_audit():
    seen = []

    def tags(market, d):
        seen.append((market, d))
        return {"price_limit": 0.15 if d < date(2015, 6, 15) else 0.30}

    lim = S.regime_price_limit(tags)
    assert lim(S.KOSPI, date(2016, 1, 4)) == 0.30 and seen == [("KR", date(2016, 1, 4))]
    assert lim(S.KOSDAQ, date(1997, 1, 3)) == 0.08 and len(seen) == 1     # KR tag file: KOSPI schedule only
    _raises(lambda: S.regime_price_limit(lambda m, d: {"price_limit": None})(S.KOSPI, date(1994, 1, 3)), ValueError, "null")
    Pin, dates = _lock_panel(ERAS, 0.4)
    via_tags = S.limit_lock_mask(Pin, limit_of=lim)[0]
    j = [k for k, (m, d, L) in enumerate(ERAS) if m == S.KOSPI and d >= date(1998, 12, 7)]
    assert all(via_tags[dates.index(ERAS[k][1]), k] for k in j)
    prev = np.array([1, 1, 1, 0, 0, 0], bool)
    mem = np.array([1, 0, 0, 1, 1, 0], bool)
    lu = np.array([0, 0, 0, 1, 0, 0], bool)
    ld = np.array([0, 1, 0, 0, 0, 0], bool)
    assert S.limit_lock_audit(prev, mem, lu, ld) == (0.5, 0.5)


test_lock_01_regime_tag_source_and_audit.test_ids = ["T-TF-LOCK-01"]


# --------------------------------------------------------------------------- #
# T-TF-BAND-01: buy/hold bands, one-way turnover limits, capacity
# --------------------------------------------------------------------------- #
def test_band_01_hysteresis_turnover_and_capacity():
    score = np.arange(100, dtype=float)                 # pct = (rank - 0.5)/100: name i at (i + 0.5)/100
    U = np.ones(100, bool)
    held = np.zeros(100, bool)
    first = B.band_select(score, U, held)
    assert np.flatnonzero(first).tolist() == list(range(80, 100))       # enter in the top 20%
    held = np.zeros(100, bool)
    held[[65, 55, 90]] = True
    nxt = B.band_select(score, U, held)
    assert nxt[65] and not nxt[55] and nxt[90] and not nxt[70]           # held kept in top 40%; 70 not entered
    assert nxt.sum() == 21
    _raises(lambda: B.band_select(score, U, held, enter=0.5, exit=0.4), ValueError, "band")
    w0 = np.r_[np.full(10, 0.1), np.zeros(10)]
    w1 = np.r_[np.zeros(10), np.full(10, 0.1)]
    assert math.isclose(B.turnover_one_way(w0, w1), 1.0)
    ok = B.turnover_limit(w0, 0.75 * w0 + 0.25 * w1)
    hi = B.turnover_limit(w0, 0.6 * w0 + 0.4 * w1)
    cl = B.turnover_limit(w0, w1)
    assert ok.status == "ok" and abs(ok.one_way - 0.25) < 1e-12
    assert hi.status == "above_target" and abs(hi.one_way - 0.40) < 1e-12
    assert cl.status == "clipped_to_hard" and abs(cl.one_way - 0.50) < 1e-12 and abs(cl.weights.sum() - 1) < 1e-12
    assert np.allclose(cl.weights, 0.5 * w0 + 0.5 * w1)
    cap = B.capacity_check([0.05, 0.05, 0.05], 1e9, [5e9, 4e9, np.nan])
    assert cap.tolist() == [True, False, False] and B.CAPACITY_SHARE == 0.01


test_band_01_hysteresis_turnover_and_capacity.test_ids = ["T-TF-BAND-01"]


# --------------------------------------------------------------------------- #
# T-TF-RISK-01: cap_weights and the RX-10 caps; pair-cap proposal (display only)
# --------------------------------------------------------------------------- #
def test_risk_01_cap_weights_respect_every_cap():
    rng = np.random.default_rng(11)
    base = rng.lognormal(0, 1.5, 60)
    w = B.cap_weights(base, 0.05)
    assert abs(w.sum() - 1) < 1e-12 and w.max() <= 0.05 + 1e-12 and w.min() > 0
    free = w < 0.05 - 1e-12
    ratio = w[free] / base[free]
    assert np.allclose(ratio, ratio[0])                                    # pro rata among uncapped names
    assert np.allclose(B.cap_weights(base[:10], 0.05), 0.1)                # < 20 names: lab equal weights
    vw = B.weights(np.arange(60), "VWcap5", base)
    assert vw.max() <= 0.05 + 1e-12 and np.allclose(B.weights(np.arange(3), "EW", base), 1 / 3)
    _raises(lambda: B.weights(np.arange(3), "XX", base), ValueError, "rule")
    sectors = np.array(list("ABCDE") * 12)
    bench = {"A": 0.30, "B": 0.30, "C": 0.20, "D": 0.10, "E": 0.10}
    semis = np.zeros(60, bool)
    semis[:12] = True
    skew = base.copy()
    skew[sectors == "D"] *= 20                                             # D far above bench + 10 pp
    capped = B.apply_caps(skew, single=0.05, groups=B.sector_groups(sectors, bench) + [(semis, 0.50)])
    assert abs(capped.sum() - 1) < 1e-9 and capped.max() <= 0.05 + 1e-12
    for s_, b in bench.items():
        assert capped[sectors == s_].sum() <= b + 0.10 + 1e-9, s_
    assert capped[semis].sum() <= 0.50 + 1e-9 and capped[sectors == "D"].sum() > 0.19
    _raises(lambda: B.apply_caps(np.ones(10), single=0.05), ValueError, "infeasible")
    _raises(lambda: B.apply_caps(np.ones(40), single=0.05, groups=[(np.arange(40) < 30, 0.10)]), ValueError, "infeasible")


test_risk_01_cap_weights_respect_every_cap.test_ids = ["T-TF-RISK-01"]


def test_risk_01_pair_cap_is_a_display_proposal():
    line = B.pair_cap_proposal(0.53, 0.537062, "market")
    assert line["triggered"] and line["would_bind"] and abs(line["excess"] - 0.18) < 1e-12 and line["acting"] is False
    assert "pending owner" in line["status"] and "msci_25_50" in line["status"]
    assert not B.pair_cap_proposal(0.53, 0.44, "ETF")["triggered"]
    sel = B.pair_cap_proposal(0.53, 0.60, "selection")
    assert not sel["applies"] and not sel["would_bind"] and sel["excess"] == 0.0
    assert B.RISK1_PROPOSAL["semis_max"] == 0.50 and B.RISK1_PROPOSAL["single_name"] == 0.05


test_risk_01_pair_cap_is_a_display_proposal.test_ids = ["T-TF-RISK-01"]


# --------------------------------------------------------------------------- #
# T-TF-BOOK-01: book engine (rebalance / hold, stuck, delisting stress, turnover), base books
# --------------------------------------------------------------------------- #
def _value_path(w, R, alive_haircut):
    """Independent day-by-day value path of a buy-and-hold book: a name that stops existing is cash after the
    haircut; returns daily book returns."""
    v = np.array(w, float)
    out = []
    for r, (alive, h) in zip(R, alive_haircut):
        prev = v.sum()
        v = np.where(alive, v * (1 + r), v * (1 - h))
        out.append(v.sum() / prev - 1)
    return np.array(out), v / v.sum()


def test_book_01_rebalance_hold_stuck_and_delisting_stress():
    T, N = 11, 4
    R = np.tile(np.array([0.01, -0.01, 0.005, 0.0]), (T, 1))
    E = np.ones((T, N), bool)
    TR = np.ones((T, N), bool)
    TR[5, 1] = False                                          # name 1 held and halted at the second formation
    specs = [("bk", lambda k: ([0, 1], np.array([0.5, 0.5])) if k == 0 else ([0, 2], np.array([0.5, 0.5])))]
    out = B.run_books(R, E, TR, [0, 5, 10], specs)["bk"]
    d0, v5 = _value_path([0.5, 0.5, 0, 0], R[1:6], [(np.ones(N, bool), 0.0)] * 5)
    assert np.allclose(out["daily"][1:6], d0) and out["to"][0] == 1.0 and out["nstuck"][1] == 1
    stuck = v5[1]
    w_new = np.array([(1 - stuck) / 2, stuck, (1 - stuck) / 2, 0])
    assert abs(out["to"][1] - (abs(w_new[0] - v5[0]) + w_new[2])) < 1e-12   # the stuck name is not traded
    d1, _ = _value_path(w_new, R[6:11], [(np.ones(N, bool), 0.0)] * 5)
    assert np.allclose(out["daily"][6:11], d1) and np.isnan(out["daily"][0])
    # delisting inside the period: frozen as cash (0%), or after the -30% / -100% stress; the frozen value is
    # not sold at the next rebalance (buy side only)
    E2 = E.copy()
    E2[3:, 0] = False
    TR2 = np.ones((T, N), bool)
    specs2 = [("bk", lambda k: ([0, 1], np.array([0.5, 0.5])) if k == 0 else ([1, 2], np.array([0.5, 0.5])))]
    for h in (0.0,) + B.DELIST_STRESS:
        o = B.run_books(R, E2, TR2, [0, 5, 10], specs2, delist_haircut=h)["bk"]
        dd, vv = _value_path([0.5, 0.5, 0, 0], R[1:6], [(E2[d], h if d == 3 else 0.0) for d in range(1, 6)])
        assert np.allclose(o["daily"][1:6], dd), h
        assert abs(o["to"][1] - (abs(0.5 - vv[1]) + 0.5)) < 1e-12, h
    loss = B.growth(R, E2, 0, 5, 1.0)[:, 0]
    assert loss[1] > 0 and (loss[2:] == 0).all()
    _raises(lambda: B.growth(R, E2, 0, 5, 1.5), ValueError, "haircut")


test_book_01_rebalance_hold_stuck_and_delisting_stress.test_ids = ["T-TF-BOOK-01"]


def test_book_01_delisted_value_is_redeployed_buy_side_only():
    T, N = 11, 3
    R = np.zeros((T, N))
    E = np.ones((T, N), bool)
    E[3:, 0] = False                                          # name 0 leaves in period 0; its value is cash
    TR = E.copy()
    specs = [("bk", lambda k: ([0, 1], np.array([0.5, 0.5])) if k == 0 else ([1, 2], np.array([0.5, 0.5])))]
    o = B.run_books(R, E, TR, [0, 5, 10], specs)["bk"]
    assert abs(o["to"][1] - 0.5) < 1e-12                      # buy 0.5 of name 2; the frozen cash is not a sale


test_book_01_delisted_value_is_redeployed_buy_side_only.test_ids = ["T-TF-BOOK-01"]


def test_book_01_base_and_filtered_books():
    rng = np.random.default_rng(11)
    n = 50
    ua = np.ones(n, bool)
    ua[:5] = False
    large = np.zeros(n, bool)
    large[np.argsort(-np.arange(n))[:10]] = True
    mom = rng.normal(size=n)
    masks = B.base_member_masks(3, ua, large, mom)
    assert np.array_equal(masks["B4"], S.quantile_groups(mom, ua, 5, 3) == 5) and masks["B4"].sum() == 9
    mcap = rng.lognormal(0, 1, n)
    flag = np.zeros(n, bool)
    flag[10:15] = True
    idx, w, susp = B.book_weights(masks["B1"], "EW", mcap, flag)
    assert not susp and set(idx) == set(range(5, 50)) - set(range(10, 15)) and np.allclose(w, 1 / 40)
    idx2, w2, susp2 = B.book_weights(masks["B3"], "VWcap5", mcap, large)       # filter empties the book: suspended
    assert susp2 and set(idx2) == set(np.flatnonzero(large)) and abs(w2.sum() - 1) < 1e-12
    assert B.BASE_RULE == {"B1": "EW", "B2": "VWcap5", "B3": "VWcap5", "B4": "EW"}


test_book_01_base_and_filtered_books.test_ids = ["T-TF-BOOK-01"]


def test_book_01_end_to_end_on_a_seeded_panel():
    """Universe -> features -> F4 / F6 -> B1 and B1 ex F4 -> both bases of the paired difference (smoke)."""
    a = _arrays(T=420, N=80, seed=41)
    P = S.Panel(**a)
    me = [i for i in range(P.T - 1) if P.dates[i + 1].month != P.dates[i].month and i >= 252]
    assert len(me) >= 5
    terms = S.share_change_terms(P)
    mem = {}
    for k, t in enumerate(me):
        U = S.universe_all(P, t)
        fl = S.screen_flags(S.features_at(P, t), U, k, dil_lit=S.dilution_at(P, t, terms=terms)["DIL_LIT"])
        assert fl["F4"].sum() == int(U.sum()) // 10
        mem[k] = (B.book_weights(U, "EW", P.marcap[t]), B.book_weights(U, "EW", P.marcap[t], fl["F4"]))
    TR = P.volume > 0
    books = B.run_books(P.ret, P.exists, TR, me, [("B1", lambda k: mem[k][0][:2]), ("B1_F4", lambda k: mem[k][1][:2])])
    starts, ends = B.periods(me, P.T)
    c = B.COST_PER_SIDE["net35"]
    nets = {nm: B.daily_net(books[nm]["daily"], books[nm]["to"], starts, c) for nm in books}
    st = B.daily_stats(B.diff_series(nets["B1_F4"], nets["B1"]))
    assert st["n"] == ends[-1] - starts[0] and math.isfinite(st["ir"])
    per, _, _ = B.lab_diff_series(books["B1_F4"], books["B1"], starts, ends, c)
    ms = B.monthly_stats(per)
    assert ms["n"] == len(me) and math.isfinite(ms["ann"])


test_book_01_end_to_end_on_a_seeded_panel.test_ids = ["T-TF-BOOK-01"]


def test_book_01_tf_modules_are_pure_library_code():
    """No clock, no file or network I/O, no engine import, and no stop-loss parameter (INV-5) in the two modules."""
    for name in ("tf_screens.py", "tf_books.py"):
        src = (ROOT / "core" / "quant" / name).read_text(encoding="utf-8")
        tree = ast.parse(src)
        calls = {ast.unparse(n.func) for n in ast.walk(tree) if isinstance(n, ast.Call)}
        assert not {c for c in calls if c.endswith(("datetime.now", "time.time", "date.today", "open"))}, (name, calls)
        mods = {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
        assert not {m for m in mods if m and (m == "data" or m.startswith(("core.engine", "data.", "requests")))}, mods
        args = {a.arg for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) for a in n.args.args + n.args.kwonlyargs}
        assert not {a for a in args if "stop" in a}, args


test_book_01_tf_modules_are_pure_library_code.test_ids = ["T-TF-BOOK-01"]


# --------------------------------------------------------------------------- #
# T-TF-SER-01: daily-basis and monthly-basis series
# --------------------------------------------------------------------------- #
def test_ser_01_daily_basis_ir_and_cost_timing():
    rng = np.random.default_rng(11)
    a, b = rng.normal(0.0003, 0.01, 500), rng.normal(0.0001, 0.01, 500)
    b[7] = np.nan
    d = B.diff_series(a, b)
    assert d.size == 499
    st = B.daily_stats(d)
    assert abs(st["ann"] - d.mean() * 252) < 1e-15 and abs(st["te"] - d.std(ddof=1) * math.sqrt(252)) < 1e-15
    assert abs(st["ir"] - d.mean() / d.std(ddof=1) * math.sqrt(252)) < 1e-12
    gross = np.full(10, 0.001)
    net = B.daily_net(gross, np.array([1.0, 0.4]), [1, 6], 0.0035)
    assert math.isclose(net[1], 0.001 - 0.0035) and math.isclose(net[6], 0.001 - 0.0014)
    assert (net[[0, 2, 3, 4, 5, 7, 8, 9]] == 0.001).all()
    assert math.isnan(B.daily_stats([0.1])["ir"])


test_ser_01_daily_basis_ir_and_cost_timing.test_ids = ["T-TF-SER-01"]


def test_ser_01_monthly_basis_series_reproduces_the_lab_form():
    rng = np.random.default_rng(12)
    T = 31
    starts, ends = B.periods([0, 10, 20, 30], T)
    assert starts.tolist() == [1, 11, 21, 31] and ends.tolist() == [11, 21, 31, 31]
    L = {"daily": np.r_[np.nan, rng.normal(0.001, 0.01, T - 1)], "to": np.array([1.0, 0.3, 0.2, np.nan])}
    Bk = {"daily": np.r_[np.nan, rng.normal(0.0005, 0.01, T - 1)], "to": np.array([1.0, 0.1, 0.1, np.nan])}
    per, daily, _ = B.series(L, starts, ends, c=0.0035)
    for k in range(3):
        s, e = starts[k], ends[k]
        assert abs(per[k] - (np.prod(1 + L["daily"][s:e]) - 1 - 0.0035 * L["to"][k])) < 1e-12
        assert abs(np.prod(1 + daily[s:e]) - 1 - per[k]) < 1e-12           # daily compounds to the period return
    pd_, _, _ = B.lab_diff_series(L, Bk, starts, ends, 0.0035)
    s, e = starts[1], ends[1]
    want = (np.prod(1 + L["daily"][s:e]) - 0.0035 * 0.3) - (np.prod(1 + Bk["daily"][s:e]) - 1 - 0.0035 * 0.1) - 1
    assert abs(pd_[1] - want) < 1e-12
    ls, _, to = B.series(L, starts, ends, S=Bk, c=0.0035)
    assert abs(to[1] - 0.4) < 1e-12
    x = rng.normal(0.003, 0.01, 120)
    ms = B.monthly_stats(x)
    assert abs(ms["ann"] - x.mean() * 12) < 1e-15 and abs(ms["ir"] - x.mean() / x.std(ddof=1) * math.sqrt(12)) < 1e-12
    assert ms["nw_t"] == newey_west_t(x, 6)


test_ser_01_monthly_basis_series_reproduces_the_lab_form.test_ids = ["T-TF-SER-01"]


# --------------------------------------------------------------------------- #
# T-TF-BE-01: break-even from the lab key numbers (GV-189..196) and the screen form (GV-105..116)
# --------------------------------------------------------------------------- #
def test_be_01_break_even_recomputed_from_lab_rows():
    gv = _goldens()
    key = _lab("kr/kr_key_numbers.csv")
    for i in range(189, 197):
        row = gv[f"GV-{i:03d}"]
        src = _csv_line(key, int(row["line"]))
        be = B.break_even_bps(float(src["ls_gross_ann"]), float(src["ls_turnover_yr"]))
        assert abs(be - float(row["raw"])) < 1e-6, (row["gv_id"], be, row["raw"])
        assert abs(be - float(row["value"])) < 0.05 + 1e-9, (row["gv_id"], be)   # printed precision
    summ = _lab("r2_kr/r2_kr_excl_summary.csv")
    for i in range(105, 117):
        row = gv[f"GV-{i:03d}"]
        gross_line, net_line = (int(x) for x in row["line"].split(";"))
        g, n = _csv_line(summ, gross_line), _csv_line(summ, net_line)
        assert g["cost"] == "gross" and n["cost"] == "net35" and (g["base"], g["filter"]) == (n["base"], n["filter"])
        be = B.break_even_bps(float(g["ann_diff"]), float(n["turnover_filtered"]) - float(n["turnover_unfiltered"]))
        assert abs(be - float(row["raw"])) < 1e-6, (row["gv_id"], be, row["raw"])
    assert round(B.break_even_bps(0.199254, 159.462), 1) == 12.5
    _raises(lambda: B.break_even_bps(0.1, 0.0), ValueError, "turnover")


test_be_01_break_even_recomputed_from_lab_rows.test_ids = ["T-TF-BE-01"]


# --------------------------------------------------------------------------- #
# T-TF-GOLD-01 / -02: screen reference constants; pair share from the lab columns
# --------------------------------------------------------------------------- #
def test_gold_01_screen_constants_pinned_with_their_basis():
    gv = _goldens()
    ref = B.SCREEN_REFERENCE
    pins = {("SCR-1", "monthly"): ("GV-002", "GV-004", 11, "F4"), ("SCR-2", "monthly"): ("GV-015", "GV-017", 17, "F6")}
    summ = _lab("r2_kr/r2_kr_excl_summary.csv")
    for (card, basis), (g_ann, g_ir, line, filt) in pins.items():
        r = ref[(card, "B1", basis)]
        assert r["ann_diff"] == float(gv[g_ann]["raw"]) and r["ir"] == float(gv[g_ir]["raw"]), card
        assert gv[g_ann]["gross_net"] == "net 35 bp/side" and gv[g_ann]["line"] == str(line)
        src = _csv_line(summ, line)
        assert (src["base"], src["filter"], src["cost"]) == ("B1", filt, "net35")
        assert float(src["ann_diff"]) == r["ann_diff"] and float(src["ir"]) == r["ir"] and "monthly" in r["basis"]
    assert (gv["GV-002"]["value"], gv["GV-004"]["value"], gv["GV-015"]["value"], gv["GV-017"]["value"]) == (
        "+3.08%", "1.53", "+2.34%", "0.65")
    qa = BUNDLE / "qa" / "QA_recomputation.md"
    if not qa.is_file():
        raise NotRun("REFDATA: qa/QA_recomputation.md (daily-basis screen constants)")
    lines = qa.read_text(encoding="utf-8").splitlines()
    for card, ln, ann, ir in (("SCR-1", 63, "+3.12", "1.64"), ("SCR-2", 64, "+2.48", "1.03")):
        r = ref[(card, "B1", "daily")]
        assert r["source"].startswith(f"qa/QA_recomputation.md:{ln}") and "daily" in r["basis"]
        assert f"{card} B1/F{'4' if card == 'SCR-1' else '6'}, daily basis" in lines[ln - 1]
        assert ann in lines[ln - 1] and ir in lines[ln - 1], lines[ln - 1]
        assert abs(r["ann_diff"] * 100 - float(ann)) < 1e-9 and r["ir"] == float(ir)
    # the bases are not interchangeable: the monthly and daily rows of one screen differ beyond the IR band
    assert abs(ref[("SCR-1", "B1", "daily")]["ir"] - ref[("SCR-1", "B1", "monthly")]["ir"]) > 0.02
    assert abs(ref[("SCR-2", "B1", "daily")]["ir"] - ref[("SCR-2", "B1", "monthly")]["ir"]) > 0.02


test_gold_01_screen_constants_pinned_with_their_basis.test_ids = ["T-TF-GOLD-01"]


def test_gold_02_pair_share_recomputed_from_the_lab_columns():
    snap = _lab("r3/r3_pair_share.csv")
    with snap.open(encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    for r in rows:
        got = S.pair_share_from_totals(*(float(r[k]) for k in ("samsung_common_krw", "samsung_pref_krw", "skhynix_krw",
                                                                "kospi_all_lines_krw", "kospi_common_only_krw")))
        for k, v in got.items():
            assert abs(v - float(r[k])) < 1e-12, (r["date"], k)
    last = {r["date"]: r for r in rows}["2026-09-29"]
    cr07 = float(last["CR07_pair_incl_pref_over_all_lines"])
    assert round(cr07, 6) == 0.537062 and cr07 == float(_goldens()["GV-231"]["raw"])
    with _lab("r3/r3_pair_share_2026_daily.csv").open(encoding="utf-8", newline="") as fh:
        daily = list(csv.DictReader(fh))
    dates = [r["Date"] for r in daily]
    sm = S.pair_share_summary(dates, [float(r["cr07_pair_share"]) for r in daily])
    assert (sm["first_above"], round(sm["first_share"], 6), sm["peak_date"], round(sm["peak_share"], 6),
            sm["n_above"], sm["n"]) == ("2026-05-06", 0.470159, "2026-06-25", 0.596875, 99, 181), sm
    alt = S.pair_share_summary(dates, [float(r["alt_pair_common_over_all_lines"]) for r in daily])
    assert (alt["first_above"], round(alt["peak_share"], 6), alt["n_above"]) == ("2026-05-07", 0.571082, 98)
    mc = {5930: 60.0, "005935": 5.0, "660": 30.0, "005380": 5.0, "035725": 2.0}   # int and short codes are padded
    ps = S.pair_share_kospi(mc)
    assert abs(ps["CR07_pair_incl_pref_over_all_lines"] - 95 / 102) < 1e-15
    assert abs(ps["alt_pair_common_over_common_only"] - 90 / 95) < 1e-15
    _raises(lambda: S.pair_share_kospi({"005930": 1.0}), ValueError, "000660")


test_gold_02_pair_share_recomputed_from_the_lab_columns.test_ids = ["T-TF-GOLD-02"]


# --------------------------------------------------------------------------- #
# T-TF-ML-01: L0 equal-weight z-score composite with signs fixed in advance
# --------------------------------------------------------------------------- #
def test_ml_01_l0_composite_structure():
    rng = np.random.default_rng(11)
    n = 50
    f = {"MOM_12_7": rng.normal(size=n), "VOL_3M": rng.normal(2, 3, n), "REV_1M": rng.normal(size=n)}
    signs = {"MOM_12_7": 1, "VOL_3M": -1, "REV_1M": -1}
    U = np.ones(n, bool)
    U[:5] = False
    c = S.l0_composite(f, signs, U)
    z = {k: (v[U] - v[U].mean()) / v[U].std() for k, v in f.items()}
    assert np.allclose(c[U], (z["MOM_12_7"] - z["VOL_3M"] - z["REV_1M"]) / 3) and np.isnan(c[:5]).all()
    flip = S.l0_composite(f, {**signs, "VOL_3M": 1}, U)
    assert np.allclose(flip[U] - c[U], 2 * z["VOL_3M"] / 3)
    f2 = dict(f)
    f2["REV_1M"] = f["REV_1M"].copy()
    f2["REV_1M"][7] = np.nan
    assert np.isnan(S.l0_composite(f2, signs, U)[7])
    _raises(lambda: S.l0_composite(f, {"MOM_12_7": 1, "VOL_3M": -1}, U), ValueError, "fixed in advance")
    _raises(lambda: S.l0_composite(f, {**signs, "REV_1M": 0.5}, U), ValueError, "-1 or +1")


test_ml_01_l0_composite_structure.test_ids = ["T-TF-ML-01"]


# --------------------------------------------------------------------------- #
# T-TF-FS-02 / T-TF-FS-05: FORWARD-SIM builders
# --------------------------------------------------------------------------- #
def test_fs_02_constrained_momentum_is_forward_sim_only():
    rng = np.random.default_rng(11)
    n = 200
    mom = rng.normal(size=n)
    U = np.ones(n, bool)
    f4 = S.p6_composite(*rng.random((3, n)), U)
    vs, sigma, status = vol_scale_from_returns(rng.normal(0, 0.02, 300))          # R-03 kernel (sleeves)
    assert status == "ok" and 0 < vs < 1

    class VS:                                                                      # VSResult shape: `.value`
        value = vs
    book = B.fs2_momentum_book(mom, U, f4, 0, vs=VS())
    q5 = S.quantile_groups(mom, U, 5, 0) == 5
    assert set(book["members"]) == set(np.flatnonzero(q5 & ~f4)) and not f4[book["members"]].any()
    assert book["book"] == "forward_sim:FS-2" and book["acting"] is False and book["status"] == "FORWARD_SIM"
    assert (book["weights"] >= 0).all() and book["weights"].max() <= 0.05 * vs + 1e-15
    assert abs(book["weights"].sum() - min(1.0, 0.05 * len(book["members"])) * vs) < 1e-12
    assert abs(book["cash"] + book["weights"].sum() - 1) < 1e-12
    small = B.fs2_momentum_book(mom[:30], U[:30], np.zeros(30, bool), 0, vs=1.0)   # 6 names: 5% each, rest cash
    assert np.allclose(small["weights"], 0.05) and abs(small["cash"] - 0.70) < 1e-12
    _raises(lambda: B.fs2_momentum_book(mom, U, None, 0, vs=1.0), ValueError, "SCR-3")
    _raises(lambda: B.fs2_momentum_book(mom, U, f4, 0, vs=1.2), ValueError, "outside")
    from core.ficc.pit import MissingInput
    miss = MissingInput("MOM_PAPER_LS_SERIES:KR", "missing", "acting_exposure", ("specification:KR",))
    _raises(lambda: B.fs2_momentum_book(mom, U, f4, 0, vs=miss), ValueError, "fail closed")


test_fs_02_constrained_momentum_is_forward_sim_only.test_ids = ["T-TF-FS-02"]


def test_fs_05_reversal_guard_excludes_last_months_top_decile():
    rng = np.random.default_rng(11)
    rev = rng.normal(size=100)
    U = np.ones(100, bool)
    g = S.reversal_guard(rev, U)
    assert g.sum() == 10 and set(np.flatnonzero(g)) == set(np.argsort(-rev)[:10])
    idx, _, susp = B.book_weights(U, "EW", np.ones(100), g)
    assert not susp and len(idx) == 90 and not g[idx].any()


test_fs_05_reversal_guard_excludes_last_months_top_decile.test_ids = ["T-TF-FS-05"]


# --------------------------------------------------------------------------- #
# T-TF-IDX-01 / -02: rebuilt KOSPI definition (synthetic) and the QA check values (REFDATA)
# --------------------------------------------------------------------------- #
def test_idx_01_rebuilt_kospi_definition():
    T = 4
    dates = (date(2007, 10, 30), date(2007, 10, 31), date(2007, 11, 1), date(2007, 11, 2))
    codes = ("000010", "000020", "000030", "000035", "000040", "000050")
    ret = np.array([[0.0] * 6,
                    [0.01, 0.02, -0.01, 0.50, 0.30, 0.04],
                    [0.02, np.nan, 0.03, 0.50, 0.30, -0.02],
                    [0.01, 0.01, 0.01, 0.50, 0.30, 0.05]], np.float32)
    mcap = np.array([[100, 200, 300, 50, 400, 100]] * 4, np.float32)
    market = np.array([[1, 1, 1, 1, 2, 1]] * 4, np.int8)         # 000040 is KOSDAQ; 000035 a KOSPI preferred line
    exists = np.ones((T, 6), bool)
    exists[0, 5] = False                                          # 000050 listed from 10-31: excluded on 10-31 only
    exists[3, 2] = False                                          # 000030 gone on 11-02
    vol = np.ones((T, 6))
    vol[2, 0] = 0                                                 # zero-volume day still counts (finite r)
    ncls = np.zeros((T, 6), np.int8)
    ncls[:, 1] = S.NAME_CLASSES.index("REIT")                     # any name class counts
    a = {"dates": dates, "codes": codes, "close": np.full((T, 6), 1000, np.float32), "high": np.full((T, 6), 1000, np.float32),
         "low": np.full((T, 6), 1000, np.float32), "ret": ret, "volume": vol, "amount": np.ones((T, 6), np.float32),
         "marcap": mcap, "shares": np.ones((T, 6)), "market": market, "name_cls": ncls, "exists": exists}
    P = S.Panel(**a)
    r, lvl = S.rebuilt_kospi(P)
    assert math.isnan(r[0])
    assert abs(r[1] - (100 * 0.01 + 200 * 0.02 + 300 * -0.01) / 600) < 1e-9
    assert abs(r[2] - (100 * 0.02 + 300 * 0.03 + 100 * -0.02) / 500) < 1e-9       # NaN r drops 000020
    assert abs(r[3] - (100 * 0.01 + 200 * 0.01 + 100 * 0.05) / 400) < 1e-9        # 000030 gone at d
    assert abs(lvl[1] - 2064.85) < 1e-9 and abs(lvl[3] / lvl[2] - 1 - r[3]) < 1e-12
    _raises(lambda: S.rebuilt_kospi(S.Panel(**{**a, "dates": tuple(d + timedelta(days=400) for d in dates)})),
            ValueError, "base date")


test_idx_01_rebuilt_kospi_definition.test_ids = ["T-TF-IDX-01"]


def test_idx_02_rebuilt_kospi_check_values_need_the_krx_panel():
    chk = S.REBUILT_KOSPI_CHECK
    official = {date(2020, 3, 19): 1457.64, date(2026, 6, 22): 9114.55, date(2026, 7, 30): 5593.56}
    assert chk == {date(2020, 3, 19): 1457.46, date(2026, 6, 22): 9120.19, date(2026, 7, 30): 5599.30}
    assert all(0.9987 <= chk[d] / official[d] <= 1.0023 for d in chk)            # OQ-07 range
    if not any(p.exists() for p in KRX_PANEL_PATHS):
        raise NotRun("REFDATA: KRX marcap panel (rebuilt KOSPI 1,457.46 / 9,120.19 / 5,599.30 need the all-stock file)")
    raise NotRun("REFDATA: KRX marcap panel present but no reviewed loader for it yet (rebuilt-KOSPI check values)")


test_idx_02_rebuilt_kospi_check_values_need_the_krx_panel.test_ids = ["T-TF-IDX-02"]


def test_krx_01_screen_card_runs_need_the_krx_panel():
    """SCR-1 / SCR-2 / SCR-3 and FS-2 / FS-5 card runs (CARD-O vs the unscreened book, rulings 3.8) are NOT_RUN."""
    assert B.SCREEN_REFERENCE[("SCR-1", "B1", "monthly")]["ann_diff"] == 0.0307644
    raise NotRun("REFDATA: KRX marcap panel (all-stock daily panel 1995-2026; SCR-1/SCR-2/SCR-3 cards and the "
                 "FS-2/FS-5 cells cannot run on this machine)")


test_krx_01_screen_card_runs_need_the_krx_panel.test_ids = ["T-TF-KRX-01"]


if __name__ == "__main__":
    from tests.macro_acceptance import run_module
    raise SystemExit(run_module(globals()))
