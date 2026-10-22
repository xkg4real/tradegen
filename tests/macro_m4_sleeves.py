"""M4 package C tests: factor sleeves (core/quant/sleeves.py, optimize.inverse_vol_weights, signals.SignalComponent.family).

Spec tests: T-R03-01 (sleeve-scale and years clauses; synthetic series and the tech-fund r2_kr CSVs as hermetic
cross-checks), T-PRIOR-01 (admissibility, base weights, K/(K-1) re-weight, tilt refusal, mapping clause -> OWNER),
T-BASIS-01 (M4 runtime clause for L/S sleeves), T-COST-01 (both-legs clause), G-MOM-01..08, G-INTL-01, G-BOOK-01,
G-YRS-01 (REFDATA: Ken French daily files are not on this machine).
Hermetic: every PIT store lives in a tempfile directory; decision and knowledge instants are pinned; nothing is
written under ~/.nextgen; the shipped rules store is read only.
"""
from __future__ import annotations

import csv
import math
import tempfile
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import numpy as np

from core.ficc import pit as P
from core.quant import optimize as O
from core.quant import sleeves as S
from core.quant import strategies as ST
from core.quant.signals import SignalComponent
from core.rules import governance as G
from core.rules.macro_rules import MacroRefusal, load_store
from tests.macro_m1_pit import CLK, REG, U, _kospi
from tests.notrun import NotRun, require_fixture

ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / "QUANTGEN_techfund_research_bundle" / "QUANTGEN_techfund_research" / "datalab" / "results" / "r2_kr"
# D.1 generator outputs (docs/macro_fixtures.REFERENCE_FILES): F10 Mom daily, F10 5-factor 2x3 daily (Mkt-RF, RF, RMW),
# F11 monthly F-F factors; F10 regional Mom (JP, EU, APxJ, Dev ex US) and ST_Rev daily.
FRENCH = ("french_daily_mom_1990-01-02_2026-08-31.csv", "french_daily_5f_2x3.csv", "french_monthly_ff_1926-07_2026-08.csv")
REGIONAL = ("french_daily_regional_mom.csv",)
DEC = U(2026, 10, 1, 20, 0, 30)          # NYSE close + 30 s
KNOW = U(2026, 10, 1, 21, 0)


def _raises(fn, exc=Exception, needle=""):
    try:
        fn()
    except exc as e:
        assert needle.lower() in str(e).lower(), (needle, str(e))
        return e
    raise AssertionError(f"expected {exc.__name__} containing {needle!r}")


def _sessions(n: int, end: date = date(2026, 10, 1)) -> list[date]:
    out, d = [], end
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d)
        d -= timedelta(days=1)
    return out[::-1]


def _store():
    return P.PITStore(Path(tempfile.mkdtemp(prefix="m4sleeves_")) / "store", registry=REG, clocks=CLK)


def _derived(sid, d, value, *, status="official_close", synthetic=False, avail=None, retrieved=None):
    avail = avail or U(d.year, d.month, d.day, 20, 0, 30)
    return P.make_row(series_id=sid, value=float(value), obs_date=d, session_date=d, obs_utc=avail, obs_kind="derived",
                      value_status=status, available_at_utc=avail, available_at_source="calendar_bound",
                      retrieved_at_utc=retrieved or avail, vintage=None, source="derived", channel=None,
                      provider_mode="explicit", synthetic=synthetic)


def _paper_store(returns, *, synthetic_tail=0):
    days = _sessions(len(returns))
    store = _store()
    rows = [_derived("MOM_PAPER_LS_SERIES", d, r, synthetic=(i >= len(returns) - synthetic_tail))
            for i, (d, r) in enumerate(zip(days, returns))]
    store.append(rows)
    return store


def _sleeves():
    return [
        S.Sleeve("KR", "momentum", "long_short", {"005930": 0.5, "000660": 0.5, "035420": -0.5, "051910": -0.5}, variant="12-7_residual"),
        S.Sleeve("KR", "reversal", "long_short", {"005930": -0.5, "000660": 0.5, "035420": 0.5, "051910": -0.5}),
        S.Sleeve("KR", "flow", "long_only", {"005930": 0.7, "000660": 0.3}, benchmark={"005930": 0.5, "000660": 0.5}),
        S.Sleeve("KR", "ts_trend", "long_only", {"069500": 1.0}, variant="KOSPI"),
        S.Sleeve("US", "momentum", "long_only", {"XLK": 0.5, "XLE": 0.5}, benchmark={"XLK": 1 / 3, "XLE": 1 / 3, "XLU": 1 / 3}),
        S.Sleeve("US", "reversal", "long_short", {"XLK": -1.0, "XLU": 1.0}),
        S.Sleeve("US", "ts_trend", "long_only", {"SPY": 1.0}),
    ]


IV = {"KR": 1 / 3, "US": 2 / 3}


# --------------------------------------------------------------------------- #
# T-R03-01: sleeve-scale clause on synthetic series and the tech-fund rows
# --------------------------------------------------------------------------- #
def test_r03_01_vs_formula_synthetic():
    r = np.array([0.01, -0.01] * 63)
    vs, sig, st = S.vol_scale_from_returns(r)
    assert st == "ok" and abs(sig - 0.159379) < 1e-6 and abs(vs - 0.752923) < 1e-6
    vs3, _, _ = S.vol_scale_from_returns(r, revision=3)
    assert abs(vs3 - 0.566893) < 1e-6
    vs, sig, st = S.vol_scale_from_returns(np.array([0.005, -0.005] * 63))
    assert st == "ok" and abs(sig - 0.079689) < 1e-6 and vs == 1.0
    assert S.vol_scale_from_returns(r[:125]) == (None, None, "insufficient_history")
    assert S.vol_scale_from_returns(np.concatenate([r[:125], [np.nan]]))[2] == "insufficient_history"   # excluded days dropped
    assert S.vol_scale_from_returns(np.zeros(126))[2] == "degenerate_sigma"
    _raises(lambda: S.vol_scale_from_returns(r, cap=2.0), MacroRefusal, "cap")        # cap-2 lives in tests/reference only
    _raises(lambda: S.vol_scale_from_returns(r, revision=4), ValueError, "revision")
    # revision 2: expanding median of sigma126 over the same series, >= 252 sigma observations
    rng = np.random.default_rng(11)
    long = rng.normal(0, 0.012, 600)
    assert S.vol_scale_from_returns(long[:300], revision=2)[2] == "insufficient_history"      # 175 sigma obs < 252
    vs2, sig2, st2 = S.vol_scale_from_returns(long, revision=2)
    sig_series = S.sigma126_series(long)
    want = min(1.0, float(np.median(sig_series[np.isfinite(sig_series)])) / sig2)
    assert st2 == "ok" and abs(vs2 - want) < 1e-12 and 0.0 <= vs2 <= 1.0
    # every revision stays in [0, 1] on a calm series (cap binds) and on a wild one
    for rev in (1, 2, 3):
        for scale in (0.002, 0.05):
            v, _, s = S.vol_scale_from_returns(long * scale / 0.012, revision=rev)
            assert s == "ok" and 0.0 <= v <= 1.0
    # day-one sanity value (L6300): sigma126 23.9% -> 0.50
    assert abs(min(1.0, 0.12 / 0.239) - 0.502) < 1e-3


test_r03_01_vs_formula_synthetic.test_ids = ["T-R03-01"]


def test_r03_01_vs_reproduces_techfund_rows():
    """`min(1, 0.12/sigma126)` reproduces s_on_2026_06_22 of the local r2_kr crash-exposure table (L/S rows)."""
    path = BUNDLE / "r2_kr_crash_exposure_2026.csv"
    if not path.is_file():
        raise NotRun("REFDATA: datalab/results/r2_kr/r2_kr_crash_exposure_2026.csv absent")
    with path.open(encoding="utf-8-sig", newline="") as fh:
        rows = [r for r in csv.DictReader(fh) if r["control"].startswith("VS (own vol") and r["sigma126_on_2026_06_22"]]
    checked = 0
    for r in rows:
        sigma, want = float(r["sigma126_on_2026_06_22"]), float(r["s_on_2026_06_22"])
        assert abs(min(1.0, 0.12 / sigma) - want) < 1e-5, (r["sleeve"], sigma, want)
        checked += 1
    assert checked >= 4
    want = {0.216946: 0.553134, 0.438216: 0.273837, 0.341929: 0.350950, 0.589982: 0.203396}
    for sigma, s in want.items():
        assert abs(min(1.0, 0.12 / sigma) - s) < 1e-5


test_r03_01_vs_reproduces_techfund_rows.test_ids = ["T-R03-01"]


def test_r03_01_sleeve_vol_scale_acting_read():
    """Warm-up / MissingInput mapping as R-06 (L1518, L1111), fail-closed on degenerate sigma, reads only through pit."""
    rng = np.random.default_rng(11)
    r = rng.normal(0, 0.239 / math.sqrt(252), 200)
    store = _paper_store(r)
    res = S.sleeve_vol_scale(store, REG, "US", "momentum", DEC, KNOW, 1)
    assert isinstance(res, S.VSResult) and res.status == "ok" and res.exposure_basis == "active"
    want, sig, _ = S.vol_scale_from_returns(r)
    assert abs(res.value - want) < 1e-12 and abs(res.sigma126_ann - sig) < 1e-12
    assert res.reasons[0].startswith("VS: sigma126 ") and "min(1, 0.12/" in res.reasons[0]
    assert res.inputs[0].series_id == "MOM_PAPER_LS_SERIES" and res.inputs[0].role == "acting_exposure"
    assert res.card["card_id"] == "MACRO-R03-US-MOM" and res.card["verdict"] == "NOT_RUN" and res.n_valid == 200
    from core.quant import risk_layer as RL
    assert RL.VSResult is S.VSResult                              # one home (S3 integration ruling); no adapter
    for rev in (2, 3):
        out = S.sleeve_vol_scale(store, REG, "US", "momentum", DEC, KNOW, rev)
        assert isinstance(out, S.VSResult) and out.revision == rev and 0.0 <= out.value <= 1.0
    # knowledge instant before the rows were retrieved: nothing visible -> MissingInput(missing)
    miss = S.sleeve_vol_scale(store, REG, "US", "momentum", DEC, U(2025, 1, 1), 1)
    assert isinstance(miss, P.MissingInput) and miss.reason == "missing" and miss.role == "acting_exposure"
    # fewer than 126 valid returns: warm-up before the first ARMED decision, MissingInput afterwards
    short = _paper_store(r[:100])
    warm = S.sleeve_vol_scale(short, REG, "US", "momentum", DEC, KNOW, 1, armed=False)
    assert isinstance(warm, S.VSResult) and warm.value == 1.0 and warm.status == "warmup" and warm.sigma126_ann is None
    armed = S.sleeve_vol_scale(short, REG, "US", "momentum", DEC, KNOW, 1, armed=True)
    assert isinstance(armed, P.MissingInput) and armed.reason == "missing" and "insufficient_history" in armed.detail
    assert armed.books == ("specification:US",)
    # synthetic rows never feed the window; a synthetic latest row is synthetic_rejected (P5)
    syn = _paper_store(r, synthetic_tail=1)
    rej = S.sleeve_vol_scale(syn, REG, "US", "momentum", DEC, KNOW, 1, armed=True)
    assert isinstance(rej, P.MissingInput) and rej.reason == "synthetic_rejected"
    # degenerate sigma with >= 126 observations fails closed even before ARMED (F-06)
    flat = _paper_store(np.zeros(130))
    deg = S.sleeve_vol_scale(flat, REG, "US", "momentum", DEC, KNOW, 1, armed=False)
    assert isinstance(deg, P.MissingInput) and "degenerate" in deg.detail
    # families other than momentum: fixed 1.0 (R-05), no read
    fixed = S.sleeve_vol_scale(store, REG, "US", "reversal", DEC, KNOW, 1)
    assert fixed.value == 1.0 and fixed.status == "fixed_1.0"
    # the derived writer stopped: a head row older than the decided session fails closed as stale (P18; L3797)
    old = _paper_store(r)
    late = S.sleeve_vol_scale(old, REG, "US", "momentum", DEC + timedelta(days=1), KNOW + timedelta(days=1), 1)
    assert isinstance(late, P.MissingInput) and late.reason == "stale" and late.books == ("specification:US",)
    none = S.sleeve_vol_scale(store, REG, "KR", "momentum", DEC, KNOW, 1)
    assert isinstance(none, P.MissingInput) and "no registered paper" in none.detail
    _raises(lambda: S.sleeve_vol_scale(store, REG, "US", "carry", DEC, KNOW, 1), MacroRefusal, "family")


test_r03_01_sleeve_vol_scale_acting_read.test_ids = ["T-R03-01"]


def test_r03_01_years_line_and_ledger_row_synthetic():
    """Years line mechanics (L1526): identical years = vs 1.0 all year; the French-fixture counts are REFDATA."""
    days = [date(2000, 1, 1) + timedelta(days=i) for i in range(365 * 4)]
    rng = np.random.default_rng(11)
    r = rng.normal(0.0004, 0.01, len(days))
    w = np.ones(len(days))
    w[[d.year in (2001, 2003) for d in days]] = 0.5
    line = S.years_line(days, r, w * r, w)
    assert line["n_years"] == 4 and line["identical"] == 2 and line["differing"] == 2
    assert line["higher"] == 0 and 0.0 <= line["positive_share"] <= 1.0      # a constant scale leaves Sharpe unchanged
    assert not hasattr(S, "ledger_row")              # R-03 rows register through gate_ledger.register_trial only (R-23)


test_r03_01_years_line_and_ledger_row_synthetic.test_ids = ["T-R03-01"]


def test_r03_01_french_fixture_refdata():
    require_fixture(FRENCH[0])
    raise AssertionError("fixture listed: golden assertion not implemented")


test_r03_01_french_fixture_refdata.test_ids = ["T-R03-01", "G-YRS-01"]


# --------------------------------------------------------------------------- #
# R-04 dm_gate: kernel on the tech-fund sample, acting read, specification book only
# --------------------------------------------------------------------------- #
def test_dm_kernel_reproduces_techfund_sample():
    path = BUNDLE / "r2_kr_dm_gate_sample.csv"
    if not path.is_file():
        raise NotRun("REFDATA: datalab/results/r2_kr/r2_kr_dm_gate_sample.csv absent")
    with path.open(encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == 377
    n_half, mism = 0, 0
    for r in rows:
        f = lambda k: float(r[k]) if r[k] not in ("", None) else None     # noqa: E731
        dm, bear, hivol = S.dm_from_inputs(f("r24"), f("sig_mkt"), f("q23"))
        want = float(r["dm"])
        mism += dm != want
        n_half += dm == 0.5
        if r["r24"] and r["q23"]:
            assert bear == (r["bear"] == "True") and hivol == (r["hivol"] == "True"), r
    assert mism == 0 and n_half == 36
    assert S.dm_from_inputs(-0.1, 0.3, 0.2) == (0.5, True, True)
    assert S.dm_from_inputs(0.0, 0.3, 0.2)[0] == 1.0 and S.dm_from_inputs(-0.1, 0.2, 0.2)[0] == 1.0   # strict comparisons
    assert S.dm_from_inputs(0.397, 0.143, 0.174) == (1.0, False, False)                                 # day-one values (L6301)


test_dm_kernel_reproduces_techfund_sample.test_ids = []


def test_dm_gate_acting_read_and_refusals():
    days = _sessions(300)
    rng = np.random.default_rng(11)
    vol = np.abs(rng.normal(0.18, 0.04, 300))
    vol[-1] = 0.40                                     # above its expanding 2/3 quantile
    store = _store()
    store.append([_derived("DM_MKT_VOL_126", d, v) for d, v in zip(days, vol)])
    store.append([_derived("DM_MKT_RET_24M", date(2026, 9, 30), -0.12)])
    m = S.dm_gate(store, REG, "US", DEC, KNOW)
    assert isinstance(m, S.Multiplier) and m.value == 0.5 and m.flags["dm_bear_state"] is True and m.status == "ok"
    assert m.exposure_basis == "active" and m.applies_to == "momentum" and m.book == "specification"
    assert m.card["disposition"] == "SPECIFICATION_ONLY" and m.card["label"] == "step 3 FAIL (indicative)"
    assert abs(m.flags["q23"] - float(np.quantile(vol, 2 / 3))) < 1e-12 and "specification book only" in m.reasons[0]
    bull = _store()
    bull.append([_derived("DM_MKT_VOL_126", d, v) for d, v in zip(days, vol)])
    bull.append([_derived("DM_MKT_RET_24M", date(2026, 9, 30), 0.397)])
    b = S.dm_gate(bull, REG, "US", DEC, KNOW)
    assert b.value == 1.0 and b.flags["dm_bear_state"] is False
    assert b.reasons[0] == "DM: 24m market return +39.7% >= 0 -> 1.0 (specification book only)"
    # fewer than 252 sigma observations: warm-up 1.0 before ARMED, MissingInput afterwards (F-12)
    short = _store()
    short.append([_derived("DM_MKT_VOL_126", d, v) for d, v in zip(days[-200:], vol[-200:])])
    short.append([_derived("DM_MKT_RET_24M", date(2026, 9, 30), -0.12)])
    w = S.dm_gate(short, REG, "US", DEC, KNOW, armed=False)
    assert w.value == 1.0 and w.status == "warmup"
    a = S.dm_gate(short, REG, "US", DEC, KNOW, armed=True)
    assert isinstance(a, P.MissingInput) and a.reason == "missing" and a.books == ("specification:US",)
    # a missing input fails closed by name; a non-specification book is refused (item 22)
    noret = _store()
    noret.append([_derived("DM_MKT_VOL_126", d, v) for d, v in zip(days, vol)])
    miss = S.dm_gate(noret, REG, "US", DEC, KNOW)
    assert isinstance(miss, P.MissingInput) and miss.series_id == "DM_MKT_RET_24M"
    # stale inputs fail closed: sigma126 not dated t, or the 24m return older than the last month-end's month
    late = S.dm_gate(store, REG, "US", DEC + timedelta(days=1), KNOW + timedelta(days=1))
    assert isinstance(late, P.MissingInput) and late.reason == "stale" and late.series_id == "DM_MKT_VOL_126"
    july = _store()
    july.append([_derived("DM_MKT_VOL_126", d, v) for d, v in zip(days, vol)])
    july.append([_derived("DM_MKT_RET_24M", date(2026, 7, 31), -0.12)])
    old = S.dm_gate(july, REG, "US", DEC, KNOW)
    assert isinstance(old, P.MissingInput) and old.reason == "stale" and old.series_id == "DM_MKT_RET_24M"
    _raises(lambda: S.dm_gate(store, REG, "US", DEC, KNOW, book="recommended"), MacroRefusal, "specification book only")
    assert isinstance(S.dm_gate(store, REG, "KR", DEC, KNOW), P.MissingInput)
    _raises(lambda: S.Multiplier("R-04-DM", 0.25, "active", "momentum"), ValueError, "outside")       # floor 0.5
    _raises(lambda: S.Multiplier("X", 1.5, "active", "momentum"), ValueError, "outside")              # cap 1.0


test_dm_gate_acting_read_and_refusals.test_ids = []


# --------------------------------------------------------------------------- #
# T-PRIOR-01
# --------------------------------------------------------------------------- #
def test_prior_01_admissibility_and_base_weights():
    sleeves = _sleeves()
    base = S.base_weights(None, DEC, sleeves=sleeves, iv=IV, book="specification")
    assert base.admissible == {"KR": ("momentum", "reversal", "flow", "ts_trend"), "US": ("momentum", "reversal", "ts_trend")}
    for f in ("momentum", "reversal", "flow", "ts_trend"):
        assert abs(base.weights[("KR", f)] - 1 / 12) < 1e-12
    for f in ("momentum", "reversal", "ts_trend"):
        assert abs(base.weights[("US", f)] - 2 / 9) < 1e-12
    assert abs(sum(base.iv.values()) - 1.0) < 1e-12 and all(0.0 <= w <= 1.0 for w in base.weights.values())
    for m in ("KR", "US"):
        assert abs(sum(w for (mm, _), w in base.weights.items() if mm == m) - IV[m]) < 1e-12
    # stored priors: Korea reversal 1 UNVERIFIED; US momentum lower bound 1 with the conditional text printed
    assert S.PRIORS[("KR", "reversal")].lo == 1 and S.PRIORS[("KR", "reversal")].flag == "UNVERIFIED"
    assert S.prior_value("US", "momentum") == 1 and "2 if vol-scaled" in S.PRIORS[("US", "momentum")].text
    # a range prior resolves to its lower bound; an unregistered prior is inadmissible; NOT_RUN stays admissible
    assert not S.is_admissible("EU", "ts_trend") and S.PRIORS[("EU", "ts_trend")].printed == "0-1"
    assert S.is_admissible("EU", "ts_trend", variant="DAX") and not S.is_admissible("EU", "ts_trend", variant="STOXX50")
    assert not S.is_admissible("US", "quality") and not S.is_admissible("US", "flow") and not S.is_admissible("EM", "ts_trend")
    assert not S.is_admissible("KR", "momentum") and S.is_admissible("KR", "momentum", variant="12-7_residual")
    assert S.is_admissible("US", "momentum", "NOT_RUN") and S.is_admissible("US", "momentum", "INSUFFICIENT_DATA")
    assert not S.is_admissible("US", "momentum", "REJECT")
    _raises(lambda: S.is_admissible("US", "momentum", "MAYBE"), MacroRefusal, "verdict")
    _raises(lambda: S.is_admissible("KR", "momentum", variant="12-99"), MacroRefusal, "variant")
    # a family with no sleeve carries no budget; the market stays in the IV span (F-05)
    only = S.base_weights(None, DEC, sleeves=[s for s in sleeves if s.key != ("US", "momentum")], iv=IV)
    assert ("US", "momentum") not in only.weights and only.admissible["US"] == ("reversal", "ts_trend")
    assert abs(only.weights[("US", "reversal")] - 1 / 3) < 1e-12
    # recommended book: ts_trend keeps its K slot at zero budget until its own PASS (F-04)
    rec = S.base_weights(None, DEC, sleeves=sleeves, iv=IV, book="recommended")
    assert rec.weights[("US", "ts_trend")] == 0.0 and abs(rec.weights[("US", "momentum")] - 2 / 9) < 1e-12
    pas = S.base_weights(None, DEC, sleeves=sleeves, iv=IV, book="recommended", cards={("US", "ts_trend"): {"verdict": "PASS"}})
    assert abs(pas.weights[("US", "ts_trend")] - 2 / 9) < 1e-12
    _raises(lambda: S.base_weights(None, DEC, sleeves=sleeves, iv=IV, book="forward_sim"), MacroRefusal, "book")
    # IV fail-closed: previous base weights carried, flagged; none -> no budget
    missing = P.MissingInput("KOSPI_OFFICIAL_CLOSE", "stale", "acting_exposure", ("specification:KR",))
    carried = S.base_weights(None, DEC, sleeves=sleeves, iv=missing, previous=base)
    assert carried.fail_closed and carried.weights == base.weights and carried.status == "stale"
    empty = S.base_weights(None, DEC, sleeves=sleeves, iv=missing)
    assert empty.fail_closed and empty.weights == {}


test_prior_01_admissibility_and_base_weights.test_ids = ["T-PRIOR-01"]


def test_prior_01_reject_reweight_logged_once():
    sleeves = _sleeves()
    base = S.base_weights(None, DEC, sleeves=sleeves, iv=IV)
    log = Path(tempfile.mkdtemp(prefix="m4gov_")) / "governance_events.jsonl"
    cards = {("US", "momentum"): {"verdict": "REJECT"}}
    nxt = S.base_weights(None, DEC + timedelta(days=1), sleeves=sleeves, iv=IV, cards=cards, previous=base, governance_log=log)
    assert nxt.weights[("US", "momentum")] == 0.0 and abs(nxt.weights[("US", "reversal")] - 1 / 3) < 1e-12
    assert abs(nxt.weights[("US", "reversal")] / base.weights[("US", "reversal")] - 1.5) < 1e-12      # K/(K-1) = 3/2
    assert nxt.weights[("KR", "momentum")] == base.weights[("KR", "momentum")]                        # other markets untouched
    events = G.read_events(log)
    assert len(events) == 1 and len(nxt.events) == 1 and G.verify_chain(log)
    ev = events[0]
    assert ev["kind"] == "admissibility_reweight" and ev["rule_id"] == "R-15" and ev["actor"] == "runtime"
    assert ev["key"] == "base_weights.US" and ev["book_id"] == "specification:US" and "K 3 -> 2" in ev["reason"]
    assert abs(ev["old"]["reversal"] - 2 / 9) < 1e-12 and abs(ev["new"]["reversal"] - 1 / 3) < 1e-12
    assert any("x 3/2" in line for line in nxt.printed)
    # the decision after: nothing changed, no second event
    again = S.base_weights(None, DEC + timedelta(days=2), sleeves=sleeves, iv=IV, cards=cards, previous=nxt, governance_log=log)
    assert again.events == () and len(G.read_events(log)) == 1
    # tilts: refused without a PASSed family card; accepted with one; never above 1.0
    rep = S.check_tilts([{"market": "US", "family": "momentum", "family_card_id": "MACRO-R03-US-MOM", "value": 0.9}], cards)
    assert not rep.ok and "REJECT, not PASS" in rep.errors[0].message
    rep = S.check_tilts([{"market": "US", "family": "momentum", "family_card_id": "MACRO-R03-US-MOM"}], {})
    assert not rep.ok and "NOT_RUN" in rep.errors[0].message
    ok = S.check_tilts([{"market": "US", "family": "reversal", "family_card_id": "C", "value": 0.9}], {"C": {"verdict": "PASS"}})
    assert ok.ok
    bad = S.check_tilts([{"market": "US", "family": "reversal", "family_card_id": "C", "value": 1.2}], {"C": {"verdict": "PASS"}})
    assert not bad.ok and "1.0" in bad.errors[0].message
    assert load_store().get("base_weights.tilt_requires_family_card_pass") is True


test_prior_01_reject_reweight_logged_once.test_ids = ["T-PRIOR-01"]


def test_prior_01_mapping_clause_owner():
    """BL-G07: the six composite components stay untagged until the owner or council confirm the proposal."""
    assert set(S.FAMILY_TAGS) == {"trend50", "trend200", "momentum", "rsi", "macd", "vol"}
    assert all(v == "" for v in S.FAMILY_TAGS.values()) and S.PROPOSED_TAGS["rsi"] == "reversal"
    comps = (SignalComponent("rsi", "RSI (14)", 10.0, 0.15, "r"), SignalComponent("vol", "Volatility regime", 0.0, 0.1, "r"))
    assert all(S.family_of(c) == "" for c in comps) and all(c.family == "" for c in S.tag_components(comps))
    tagged = S.tag_components(comps, S.PROPOSED_TAGS)
    assert tagged[0].family == "reversal" and tagged[1].family == ""
    _raises(lambda: S.tag_components(comps, {"rsi": "carry"}), MacroRefusal, "family tag")
    _raises(lambda: S.family_of(replace(comps[0], family="value")), MacroRefusal, "family tag")
    if S.TAG_STATUS != "confirmed":
        raise NotRun("OWNER: BL-G07 family mapping of the six composite components is proposed, not confirmed "
                     "(T-PRIOR-01 'runs on the confirmed mapping'); flow and quality priors unregistered outside Korea flow")


test_prior_01_mapping_clause_owner.test_ids = ["T-PRIOR-01"]


# --------------------------------------------------------------------------- #
# T-BASIS-01 (M4 runtime clause) and T-COST-01 (both-legs clause)
# --------------------------------------------------------------------------- #
def _vs(market, value, status="ok"):
    return S.VSResult("R-03", market, "momentum", 1, 0.2, 0.12, value, status, applies_to="momentum")


def _dm(value):
    return S.Multiplier("R-04-DM", value, "active", "momentum", card=dict(S.R04_CARD))


def test_basis_01_vt_never_on_ls_sleeves():
    sleeves = _sleeves()
    base = S.base_weights(None, DEC, sleeves=sleeves, iv=IV)
    book = S.build_specification_book(sleeves, base, {("US", "momentum"): _vs("US", 0.8), ("KR", "momentum"): _vs("KR", 0.6)},
                                      {"US": _dm(0.5)}, decision_utc=DEC)
    full = S.apply_market_gross(book, 1.0)
    half = S.apply_market_gross(book, 0.5)
    by = lambda b: {(w.market, w.family): w for w in b.sleeves}       # noqa: E731
    for key in (("KR", "momentum"), ("KR", "reversal"), ("US", "reversal")):
        assert by(full)[key].weights == by(half)[key].weights == by(book)[key].weights      # L/S: identical under vt
        assert by(book)[key].kind == "long_short"
    assert by(full)[("US", "ts_trend")].weights == by(half)[("US", "ts_trend")].weights          # ts_trend: exempt
    for key in (("KR", "flow"), ("US", "momentum")):
        for i, w in by(full)[key].weights.items():
            assert abs(by(half)[key].weights[i] - 0.5 * w) < 1e-15                            # long book: x gross
    assert "R-06-VT" in by(half)[("KR", "flow")].binding and by(half)[("KR", "flow")].binding == by(book)[("KR", "flow")].binding + ("R-06-VT",)
    # ladder / post_rearm_cap records enter min() like the scalar arguments; a total-basis vs is refused (never dropped)
    lb = S.Sleeve("US", "momentum", "long_only", {"XLK": 1.0}, base_weight=1.0)
    vt8 = S.Multiplier("R-06-VT", 0.8, "total", "market_gross", factor="vt")
    g = S.apply_overlays(lb, [vt8, S.Multiplier("L", 0.5, "total", "market_gross", factor="ladder")], "total")
    assert abs(g.factor - 0.4) < 1e-15 and "ladder" in g.binding
    g = S.apply_overlays(lb, [vt8, S.Multiplier("C", 0.5, "total", "market_gross", factor="post_rearm_cap")], "total")
    assert abs(g.factor - 0.4) < 1e-15 and "post_rearm_cap" in g.binding
    _raises(lambda: S.apply_overlays(lb, [S.Multiplier("V", 0.5, "total", "market_gross", factor="vs")], "total"), MacroRefusal, "vs")
    # every multiplier carries exposure_basis; the refusals
    _raises(lambda: S.Multiplier("X", 0.8, None, "momentum"), MacroRefusal, "exposure_basis")
    _raises(lambda: S.Multiplier("X", 0.8, "gross", "momentum"), MacroRefusal, "exposure_basis")
    _raises(lambda: S.VSResult("R-03", "US", "momentum", 1, 0.2, 0.12, 0.8, "ok", exposure_basis="net"), MacroRefusal, "P8")
    ls = replace(sleeves[0], base_weight=0.1)
    vt = S.Multiplier("R-06-VT", 0.5, "total", "market_gross", factor="vt")
    _raises(lambda: S.apply_overlays(ls, [vt], "active"), MacroRefusal, "never applied to a family sleeve")
    total_overlay = S.Multiplier("R-28", 0.8, "total", "market_gross")
    _raises(lambda: S.apply_overlays(ls, [total_overlay], "active"), MacroRefusal, "total-basis")
    _raises(lambda: S.Multiplier("R-06-VT", 0.5, "total", "momentum", factor="vt"), MacroRefusal, "market_gross only")
    _raises(lambda: S.Multiplier("X", 0.8, "active", "ts_trend"), MacroRefusal, "ts_trend")
    tt = replace(sleeves[3], base_weight=0.1)
    _raises(lambda: S.apply_overlays(tt, [_vs("KR", 0.8)], "active"), MacroRefusal, "ts_trend")
    _raises(lambda: S.apply_overlays(ls, [_dm(0.8)], "total"), MacroRefusal, "long book only")
    lo = replace(sleeves[2], base_weight=1.0)
    _raises(lambda: S.apply_overlays(lo, [_dm(0.8)], "total"), MacroRefusal, "never scales the market gross")
    _raises(lambda: S.apply_overlays(lo, [vt], "gross"), MacroRefusal, "basis")
    # market level: composed = vt x min(1, overlays, ladder, cap) >= 0.5 vt; concentration bound after; binding logged
    g = S.apply_overlays(lo, [vt, total_overlay], "total", ladder=0.5, concentration_bound=0.2)
    assert abs(g.factor - 0.2) < 1e-15 and g.binding == ("R-06-VT", "ladder", "concentration_bound")   # 0.8 does not bind
    g = S.apply_overlays(lo, [S.Multiplier("R-06-VT", 0.8, "total", "market_gross", factor="vt"),
                             S.Multiplier("R-28", 0.75, "total", "market_gross"), S.Multiplier("R-29", 0.5, "total", "market_gross")], "total")
    assert abs(g.factor - 0.4) < 1e-15 and g.binding == ("R-06-VT", "R-29")           # 0.75 and 0.5 compose to 0.5, never 0.375


test_basis_01_vt_never_on_ls_sleeves.test_ids = ["T-BASIS-01"]


def test_cost_01_both_legs_for_ls_sleeves():
    rng = np.random.default_rng(11)
    r1, r2 = rng.normal(0, 0.01, 12), rng.normal(0, 0.01, 12)
    w = np.array([1.0] * 4 + [0.7] * 4 + [1.0] * 4)
    c = 0.005
    net = S.overlay_net_returns(r1 - r2, w, c, legs=2)
    assert math.isnan(net[0]) and net[1] == w[0] * (r1 - r2)[1]                          # initial entry not charged
    assert abs((w[4] * (r1 - r2)[5] - net[5]) - c * 2 * 0.3) < 1e-15                    # the day the new weight earns
    assert abs((w[8] * (r1 - r2)[9] - net[9]) - c * 2 * 0.3) < 1e-15
    assert all(abs(net[t] - w[t - 1] * (r1 - r2)[t]) < 1e-15 for t in (2, 3, 4, 6, 7, 8, 10, 11))
    lo = S.overlay_net_returns(r1, w, c, legs=1)
    assert abs((w[4] * r1[5] - lo[5]) - c * 0.3) < 1e-15                                  # long-only: one leg
    # the same charges fall out of strategies.simulate on a +w / -w two-column panel (turnover = sum |dw| per leg)
    p1, p2 = np.cumprod(np.concatenate([[1.0], 1 + r1[1:]])), np.cumprod(np.concatenate([[1.0], 1 + r2[1:]]))
    pnl, to = ST.simulate(np.column_stack([p1, p2]), np.column_stack([w, -w]), cost_bps=c * 1e4)
    assert np.allclose(pnl[1:], net[2:]) and abs(to[4] - 0.6) < 1e-15                     # pnl[t] earns r[t+1]
    _raises(lambda: S.overlay_net_returns(r1, w[:5], c), ValueError, "differ")


test_cost_01_both_legs_for_ls_sleeves.test_ids = ["T-COST-01"]


# --------------------------------------------------------------------------- #
# R-05, the two books, no renormalisation, sign / creation
# --------------------------------------------------------------------------- #
def test_r05_reversal_quality_flow_fixed_one():
    store = load_store()
    assert store.get("families.reversal.calm_state_downweight") == "not_adopted"
    assert store.get("owner_decisions.D3.key") == "families.reversal.calm_state_downweight"
    for fam in ("reversal", "quality", "flow"):
        assert store.get(f"families.{fam}.overlay") == "fixed_1.0"
        rep = S.check_fixed_family({"rule_id": "X-CALM", "applies_to": fam, "factor": "overlay"}, store)
        assert not rep.ok and "fixed 1.0" in rep.errors[0].message
    rep = S.check_fixed_family({"rule_id": "QF5-M10", "applies_to": "reversal", "factor": "overlay"}, store)
    assert "not_adopted" in rep.errors[0].message and "D3" in rep.errors[0].message
    assert S.check_fixed_family({"rule_id": "R-04-DM", "applies_to": "momentum", "factor": "overlay"}, store).ok
    assert store.get("families.reversal.intraday_leg") is False
    sleeves = _sleeves()
    base = S.base_weights(None, DEC, sleeves=sleeves, iv=IV)
    for dm_v, vs_v in ((0.5, 0.3), (1.0, 1.0)):                       # any flag state
        book = S.build_specification_book(sleeves, base, {("US", "momentum"): _vs("US", vs_v)}, {"US": _dm(dm_v)}, decision_utc=DEC)
        for w in book.sleeves:
            if w.family in S.FIXED_ONE:
                assert w.multipliers == () and w.vs == 1.0 and w.overlay_min == 1.0 and w.factor == 1.0
                assert "R-05" in w.label
    rev = replace(sleeves[1], base_weight=0.1)
    _raises(lambda: S.apply_overlays(rev, [S.Multiplier("X", 0.8, "active", "reversal")], "active"), MacroRefusal, "R-05")
    _raises(lambda: S.apply_overlays(rev, [S.Multiplier("X", 1.0, "active", "reversal")], "active"), MacroRefusal, "R-05")
    _raises(lambda: S.build_specification_book(sleeves, base, {("US", "reversal"): _vs("US", 0.8)}, {}, decision_utc=DEC),
            MacroRefusal, "momentum only")


test_r05_reversal_quality_flow_fixed_one.test_ids = []


def test_books_recommended_not_run_and_specification_stack():
    sleeves = _sleeves()
    spec_base = S.base_weights(None, DEC, sleeves=sleeves, iv=IV, book="specification")
    rec_base = S.base_weights(None, DEC, sleeves=sleeves, iv=IV, book="recommended")
    vs = {("US", "momentum"): _vs("US", 0.8), ("KR", "momentum"): _vs("KR", 0.6)}
    spec = S.build_specification_book(sleeves, spec_base, vs, {"US": _dm(0.5)}, decision_utc=DEC)
    rec = S.build_recommended_book(sleeves, rec_base, vs, decision_utc=DEC)
    by = lambda b: {(w.market, w.family): w for w in b.sleeves}       # noqa: E731
    us = by(spec)[("US", "momentum")]
    assert abs(us.factor - 0.4) < 1e-15 and us.binding == ("R-03", "R-04-DM") and "step 3 FAIL" in us.label
    assert "indicative PASS; step 3 borderline" in us.label and "NOT_RUN" in us.label
    kr = by(spec)[("KR", "momentum")]
    assert abs(kr.factor - 0.6) < 1e-15 and abs(kr.weights["005930"] - (1 / 12) * 0.6 * 0.5) < 1e-15     # L/S: toward zero
    assert abs(kr.weights["035420"] + (1 / 12) * 0.6 * 0.5) < 1e-15 and kr.binding == ("R-03",)
    # long-only momentum (US): freed active budget moves toward the benchmark, not to cash
    wb, ws, b = sleeves[4].benchmark, sleeves[4].weights, 2 / 9
    for i in ("XLK", "XLE", "XLU"):
        assert abs(us.weights[i] - b * (wb[i] + 0.4 * (ws.get(i, 0.0) - wb[i]))) < 1e-15
    assert abs(sum(us.weights.values()) - b) < 1e-15                                        # the budget stays invested
    # recommended: every card NOT_RUN -> vs enters as 1.0 (status not_run), dm absent, ts_trend zero budget
    r_us = by(rec)[("US", "momentum")]
    assert r_us.factor == 1.0 and r_us.multipliers[0].value == 1.0 and r_us.multipliers[0].status == "not_run"
    assert "not_run: enters as 1.0" in r_us.label and r_us.binding == ()
    assert all(v == 0.0 for v in by(rec)[("US", "ts_trend")].weights.values())
    assert by(spec)[("US", "ts_trend")].weights["SPY"] == 2 / 9 and by(spec)[("US", "ts_trend")].multipliers == ()
    assert rec.book_ids == ("recommended:KR", "recommended:US") and spec.book_ids == ("specification:KR", "specification:US")
    # the recommended builder refuses R-04 and any specification-only / forward-sim / refusal factor
    _raises(lambda: S.build_recommended_book(sleeves, rec_base, vs, decision_utc=DEC, multipliers=[_dm(0.5)]), MacroRefusal, "item 22")
    for disp in ("FORWARD_SIM", "REFUSAL_BOOK"):
        m = S.Multiplier("R-28", 0.8, "active", "momentum", book="recommended", card={"disposition": disp, "verdict": "PASS"})
        _raises(lambda m=m: S.build_recommended_book(sleeves, rec_base, vs, decision_utc=DEC, multipliers=[m]), MacroRefusal, disp)
    # a recommended-bound overlay acts only on a PASS card or as an INVARIANT_STEP (L885, L3768); else 1.0, not_run
    for card in ({"verdict": "NOT_RUN", "disposition": "DESCRIPTIVE"}, {"verdict": "REJECT", "disposition": "RECOMMENDATION"}, {}):
        m = S.Multiplier("R-90-X", 0.5, "active", "momentum", book="recommended", card=card)
        w = by(S.build_recommended_book(sleeves, rec_base, vs, decision_utc=DEC, multipliers=[m]))[("US", "momentum")]
        assert w.factor == 1.0 and w.multipliers[-1].value == 1.0 and w.multipliers[-1].status == "not_run" and w.binding == ()
    inv = S.Multiplier("R-90-X", 0.5, "active", "momentum", book="recommended", card={"verdict": "NOT_RUN", "disposition": "INVARIANT_STEP"})
    assert by(S.build_recommended_book(sleeves, rec_base, vs, decision_utc=DEC, multipliers=[inv]))[("US", "momentum")].factor == 0.5
    # the market-gross step keeps the same gate on a recommended book: a FORWARD-SIM factor raises, a NOT_RUN one is 1.0
    fwd = S.Multiplier("R-28", 0.5, "total", "market_gross", book="forward_sim:R-28")
    _raises(lambda: S.apply_market_gross(rec, 0.7, overlays=[fwd]), MacroRefusal, "never reaches")
    nr = S.Multiplier("R-90-T", 0.5, "total", "market_gross", book="recommended", card={"verdict": "NOT_RUN"})
    assert S.apply_market_gross(rec, 1.0, overlays=[nr]).weights == S.apply_market_gross(rec, 1.0).weights
    ins = replace(_vs("US", 0.8), card={**S.R03_CARD, "build_status_on_pass": "BUILD_AS_INSURANCE"})
    _raises(lambda: S.build_recommended_book(sleeves, rec_base, {("US", "momentum"): ins}, decision_utc=DEC), MacroRefusal, "BUILD_AS_INSURANCE")
    # a PASS card with disposition RECOMMENDATION acts in the recommended book
    pas = replace(_vs("US", 0.8), card={**S.R03_CARD, "verdict": "PASS", "disposition": "RECOMMENDATION"})
    r2 = S.build_recommended_book(sleeves, rec_base, {("US", "momentum"): pas}, decision_utc=DEC)
    assert abs(by(r2)[("US", "momentum")].factor - 0.8) < 1e-15
    # base weights of the wrong book are refused
    _raises(lambda: S.build_specification_book(sleeves, rec_base, vs, {}, decision_utc=DEC), MacroRefusal, "recommended book")
    _raises(lambda: S.build_recommended_book(sleeves, spec_base, vs, decision_utc=DEC), MacroRefusal, "specification book")
    # fail-closed: a MissingInput carries the previous sleeve weights, flagged; without a previous state no budget
    miss = P.MissingInput("MOM_PAPER_LS_SERIES", "stale", "acting_exposure", ("specification:US",), "late")
    fc = S.build_specification_book(sleeves, spec_base, {("US", "momentum"): miss}, {"US": _dm(0.5)}, decision_utc=DEC, previous=spec)
    assert fc.fail_closed and by(fc)[("US", "momentum")].weights == us.weights and "fail_closed" in by(fc)[("US", "momentum")].label
    fc0 = S.build_specification_book(sleeves, spec_base, {("US", "momentum"): miss}, {"US": _dm(0.5)}, decision_utc=DEC)
    assert fc0.fail_closed and all(v == 0.0 for v in by(fc0)[("US", "momentum")].weights.values())
    rec_fc = S.build_recommended_book(sleeves, rec_base, {("US", "momentum"): miss}, decision_utc=DEC)
    assert not rec_fc.fail_closed and by(rec_fc)[("US", "momentum")].factor == 1.0      # a spec-book input never reaches it


test_books_recommended_not_run_and_specification_stack.test_ids = []


def test_no_renormalisation_and_sign_preserved():
    rng = np.random.default_rng(11)
    sleeves = _sleeves()
    base = S.base_weights(None, DEC, sleeves=sleeves, iv=IV)
    ref = S.build_specification_book(sleeves, base, {("US", "momentum"): _vs("US", 1.0), ("KR", "momentum"): _vs("KR", 1.0)},
                                     {"US": _dm(1.0)}, decision_utc=DEC)
    by = lambda b: {(w.market, w.family): w for w in b.sleeves}       # noqa: E731
    for _ in range(25):
        vs_us, vs_kr, dm_us = rng.uniform(0, 1), rng.uniform(0, 1), rng.choice([0.5, 1.0])
        book = S.build_specification_book(sleeves, base, {("US", "momentum"): _vs("US", vs_us), ("KR", "momentum"): _vs("KR", vs_kr)},
                                          {"US": _dm(dm_us)}, decision_utc=DEC)
        for key, w in by(book).items():
            r = by(ref)[key]
            if key[1] != "momentum":
                assert w.weights == r.weights                                   # no other (m', f') budget moves
            for i, x in w.weights.items():
                assert set(w.weights) <= set(sleeves[[s.key for s in sleeves].index(key)].weights) | set(
                    sleeves[[s.key for s in sleeves].index(key)].benchmark or {})
                if w.kind == "long_short":
                    assert abs(x) <= abs(r.weights[i]) + 1e-15 and S._sign(x) in (S._sign(r.weights[i]), 0)   # toward zero, no flip
                else:
                    assert x >= -1e-15
            if key[1] == "momentum":
                assert w.factor <= r.factor + 1e-15                              # never raises its own budget
        gross = lambda b, m: sum(abs(x) for w in b.sleeves if w.market == m for x in w.weights.values())   # noqa: E731
        assert gross(book, "KR") <= gross(ref, "KR") + 1e-12 and gross(book, "US") <= gross(ref, "US") + 1e-12


test_no_renormalisation_and_sign_preserved.test_ids = []


# --------------------------------------------------------------------------- #
# inverse_vol_weights: kernels and the PIT path
# --------------------------------------------------------------------------- #
def test_inverse_vol_weights_kernels_and_pit_path():
    assert O.inverse_vol_from_sigmas({"KR": 0.04, "US": 0.02}) == {"KR": 1 / 3, "US": 2 / 3}
    assert O.inverse_vol_from_sigmas({"KR": 0.04}) == {"KR": 1.0} and O.inverse_vol_from_sigmas({}) == {}
    _raises(lambda: O.inverse_vol_from_sigmas({"KR": 0.0}), ValueError, "sigma")
    rng = np.random.default_rng(11)
    weekly = {"KR": rng.normal(0, 0.04, 200), "US": rng.normal(0, 0.02, 200)}
    iv = O.inverse_vol_weights(["KR", "US"], DEC, weekly=weekly)
    assert abs(sum(iv.values()) - 1.0) < 1e-12 and iv["US"] > iv["KR"]
    s_kr = O.ewma_sigma(weekly["KR"], 0.97)
    assert abs(iv["KR"] - (1 / s_kr) / (1 / s_kr + 1 / O.ewma_sigma(weekly["US"], 0.97))) < 1e-12
    assert O.inverse_vol_weights([], DEC) == {}
    _raises(lambda: O.inverse_vol_weights(["KR"], DEC, cov="ledoit_wolf_156w", weekly=weekly), ValueError, "acting line")
    _raises(lambda: O.inverse_vol_weights(["KR"], DEC), ValueError, "store")
    lw, line = O.ledoit_wolf_line(weekly)
    assert abs(sum(lw.values()) - 1.0) < 1e-12 and line.startswith("LW-156w (printed, not acting)")
    cov = O.ledoit_wolf_cov(np.column_stack([weekly["KR"], weekly["US"]])[-156:])
    assert cov.shape == (2, 2) and cov[0, 0] > cov[1, 1] > 0
    # weekly returns: last observation of each ISO week
    days = _sessions(15, date(2026, 10, 2))
    px = np.linspace(100, 114, 15)
    wk = O.weekly_returns(days, px)
    assert wk.size == 2 and abs(wk[-1] - (114 / px[9] - 1)) < 1e-12
    # PIT path: 60 weeks of KRX official closes -> {KR: 1.0}; a short history or an absent series fails closed by name
    store = _store()
    sess = _sessions(300, date(2026, 10, 2))
    rows = []
    for i, d in enumerate(sess):
        at = U(d.year, d.month, d.day, 6, 30, 30)
        rows.append(_kospi(3000.0 * math.exp(0.0003 * i + 0.01 * math.sin(i)), obs_date=d, status="official_close",
                           obs_utc=at, available=at, retrieved=at + timedelta(minutes=10), source="KRX"))
    store.append(rows)
    dec = U(2026, 10, 2, 6, 30, 30)
    iv = O.inverse_vol_weights(["KR"], dec, store=store, knowledge_utc=U(2026, 10, 2, 7))
    assert iv == {"KR": 1.0}
    miss = O.inverse_vol_weights(["KR", "US"], dec, store=store, knowledge_utc=U(2026, 10, 2, 7))
    assert isinstance(miss, P.MissingInput) and miss.series_id == "SPX_OFFICIAL_CLOSE"     # no acting binding / no rows
    early = O.inverse_vol_weights(["KR"], U(2026, 3, 2, 6, 30, 30), store=store, knowledge_utc=U(2026, 3, 2, 7))
    assert isinstance(early, P.MissingInput) and "weekly returns" in early.detail
    assert isinstance(O.inverse_vol_weights(["HK", "FX"], dec, store=store, knowledge_utc=U(2026, 10, 2, 7)), P.MissingInput)
    # base_weights through the same path
    kr_only = [s for s in _sleeves() if s.market == "KR"]
    base = S.base_weights(store, dec, U(2026, 10, 2, 7), sleeves=kr_only)
    assert base.iv == {"KR": 1.0} and abs(base.weights[("KR", "momentum")] - 0.25) < 1e-12


test_inverse_vol_weights_kernels_and_pit_path.test_ids = ["T-PRIOR-01"]


# --------------------------------------------------------------------------- #
# Goldens on the Ken French daily files (REFDATA on this machine)
# --------------------------------------------------------------------------- #
def test_g_mom_01_02_08_french_mom_daily():
    require_fixture(FRENCH[0])
    raise AssertionError("fixture listed: golden assertion not implemented")


test_g_mom_01_02_08_french_mom_daily.test_ids = ["G-MOM-01", "G-MOM-02", "G-MOM-08"]


def test_g_mom_03_04_05_06_french_mom_and_market():
    for f in FRENCH:
        require_fixture(f)
    raise AssertionError("fixture listed: golden assertion not implemented")


test_g_mom_03_04_05_06_french_mom_and_market.test_ids = ["G-MOM-03", "G-MOM-04", "G-MOM-05", "G-MOM-06"]


def test_g_mom_07_reference_mode():
    raise NotRun("REFDATA: French Mom daily files absent; reference mode (cap 2, DM 0x) lives in tests/reference "
                 "(package D, TASK-M2-07) and is never importable from core/")


test_g_mom_07_reference_mode.test_ids = ["G-MOM-07"]


def test_g_intl_01_regional_wml():
    for f in REGIONAL:
        require_fixture(f)
    raise AssertionError("fixture listed: golden assertion not implemented")


test_g_intl_01_regional_wml.test_ids = ["G-INTL-01"]


def test_g_book_01_mom_strev_rmw():
    for f in (FRENCH[0], "french_daily_strev.csv", "french_daily_5f_2x3.csv"):
        require_fixture(f)
    raise AssertionError("fixture listed: golden assertion not implemented")


test_g_book_01_mom_strev_rmw.test_ids = ["G-BOOK-01"]


if __name__ == "__main__":
    from tests.macro_acceptance import run_module
    raise SystemExit(run_module(globals()))
