"""Acceptance checks for the paper_live harness fixes of 2026-10-18 (after live paper Runs 1 and 2).

No network: every check builds synthetic 1-minute closes in memory and an Engine on a temp
directory. Each test names the fix it defends:
  * costs come from QUANTGEN's own table and tick floor, and a venue it cannot cost is refused;
  * one cost gate in Engine._open, per account, off unless the account declares gate_mult;
  * the 5-minute C3 trend account is no longer a live account.
"""
from __future__ import annotations

import json
import math
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

from paper_live import config as C
from paper_live import engine as E
from paper_live import grid as G

NOW = pd.Timestamp("2026-10-07 14:00", tz="UTC")


def _closes(prices: dict[str, float], age_min: float = 1.0) -> dict[str, pd.Series]:
    ix = pd.date_range(NOW - pd.Timedelta(minutes=90 + age_min), NOW - pd.Timedelta(minutes=age_min), freq="1min")
    return {t: pd.Series(px, index=ix) for t, px in prices.items()}


def _engine(tmp: str, sigmas: dict | None = None) -> E.Engine:
    model = E.Model(coef={g: [0.0, 0.0, 0.0] for g in C.GROUPS})
    return E.Engine(model, sigmas or {}, Path(tmp))


def _acc(gate_mult=None, name="T") -> E.Account:
    return E.make_account(dict(name=name, rules="lazyowen", costs="COST_CLASS_BP", prob="naive", gate_mult=gate_mult))


def _decisions(tmp: str) -> list[dict]:
    p = Path(tmp) / "decisions.jsonl"
    return [json.loads(x) for x in p.read_text().splitlines()] if p.exists() else []


def _open(eng, acc, key, closes, *, p, sigma_h, direction=+1, notional=50.0):
    return eng._open(acc, key, direction, notional, None, closes, NOW, p, sigma_h, "plan", "test")


def test_01_cost_table_is_quantgens():
    from core.quant.validate import COST_BP_PER_SIDE
    for k, v in C.COST_CLASS_BP.items():
        assert v == COST_BP_PER_SIDE[k], f"{k}: harness {v} bp, QUANTGEN {COST_BP_PER_SIDE[k]} bp"


def test_02_lse_is_refused_not_charged_a_proxy_rate():
    with tempfile.TemporaryDirectory() as tmp:
        eng, acc = _engine(tmp), _acc()
        ok = _open(eng, acc, "SHEL.L", _closes({"SHEL.L": 2600.0, "GBPUSD=X": 1.33}), p=0.9, sigma_h=0.01)
        assert not ok and not acc.positions and acc.costs_paid == 0.0
        assert [d["verdict"] for d in _decisions(tmp)] == ["no_cost_row"]


def test_03_krx_etf_pays_the_tick_floor_at_the_traded_price():
    """A KOSDAQ150 short trades the ~2,290 KRW inverse ETF: half a 5 KRW tick is ~11 bp, not the 3 bp row."""
    saved = (C.UNIVERSE, C.COST_CLASS_BP)
    C.UNIVERSE = {**C.UNIVERSE, "229200.KS": dict(group="equity", venue="FX", cost="krx_etf", short="251340.KS", name="t")}
    C.COST_CLASS_BP = {**C.COST_CLASS_BP, "krx_etf": 3.0}
    try:
        acc = _acc()
        assert E.Engine._bp(acc, C.UNIVERSE["229200.KS"], 102_000.0) == 3.0, "the floor only raises"
        with tempfile.TemporaryDirectory() as tmp:
            eng = _engine(tmp)
            assert _open(eng, acc, "229200.KS", _closes({"229200.KS": 13_000.0, "251340.KS": 2_290.0}),
                         p=0.2, sigma_h=0.01, direction=-1)
            pos = acc.positions["229200.KS"]
            assert pos.traded == "251340.KS"
            assert math.isclose(pos.cost_bp, 1.4 + 0.5 * 5 / 2_290 * 1e4), pos.cost_bp
    finally:
        C.UNIVERSE, C.COST_CLASS_BP = saved


def test_04_gate_refuses_a_move_that_cannot_pay_twice_the_round_trip():
    # ES=F round trip 10 bp; p=0.6 -> 0.2 x 0.30% x 0.798 = 4.8 bp expected, needs > 20 bp at 2x
    with tempfile.TemporaryDirectory() as tmp:
        eng, acc = _engine(tmp), _acc(gate_mult=2.0)
        assert not _open(eng, acc, "ES=F", _closes({"ES=F": 6700.0}), p=0.6, sigma_h=0.003)
        (d,) = _decisions(tmp)
        assert d["verdict"] == "cost_gate" and d["rt_cost_bp"] == 10.0 and math.isclose(d["exp_move_bp"], 4.79, abs_tol=0.01)
        # p=0.95 -> 0.9 x 0.40% x 0.798 = 28.7 bp clears 20 bp
        assert _open(eng, acc, "ES=F", _closes({"ES=F": 6700.0}), p=0.95, sigma_h=0.004)


def test_05_gate_is_off_unless_the_account_declares_it():
    with tempfile.TemporaryDirectory() as tmp:
        eng, acc = _engine(tmp), _acc(gate_mult=None)
        assert _open(eng, acc, "ES=F", _closes({"ES=F": 6700.0}), p=0.6, sigma_h=0.003)
    names = {a["name"]: a.get("gate_mult") for a in C.ACCOUNTS}
    assert names["LAZYOWEN-NAIVE"] is None and names["LAZYOWEN-CAL"] is None and names["QG-CORE"] is None
    assert names["LAZYOWEN-NAIVE-G1"] == 1.0 and names["LAZYOWEN-NAIVE-G2"] == 2.0


def test_06_no_probability_means_the_perfect_forecast_bound_on_the_daily_sigma():
    """Trend rows carry p=NaN and may lack sigma_h: sigma comes from the daily fit, conviction is 1.
    ES=F at 15% a year: 60-minute sigma 0.197%, expected move 15.7 bp -> passes 1x (10 bp), fails 2x (20 bp)."""
    sig = {"ES=F": dict(sigma_ann=0.15)}
    for mult, want in ((1.0, True), (2.0, False)):
        with tempfile.TemporaryDirectory() as tmp:
            eng = _engine(tmp, sig)
            assert _open(eng, _acc(gate_mult=mult), "ES=F", _closes({"ES=F": 6700.0}),
                         p=float("nan"), sigma_h=float("nan")) is want
    assert math.isclose(E.expected_move(float("nan"), E.sigma_h_from_ann(0.15, "CME")) * 1e4, 15.7, abs_tol=0.1)


def test_07_five_minute_trend_is_not_a_live_account():
    assert all(a["rules"] != "trend" for a in C.ACCOUNTS)
    with tempfile.TemporaryDirectory() as tmp:
        assert list(_engine(tmp).accounts) == [a["name"] for a in C.ACCOUNTS]
    assert {"TREND-b5-h0.2-G1", "TREND-b5-h0.2-G2"} <= {g["name"] for g in G.GRID}, "the grid keeps measuring C3"


def test_08_a_state_file_from_another_config_is_not_resumed():
    """Run 1/Run 2 state.json files (QG-TREND, no gate_mult) must not silently undo these fixes."""
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / "state.json").write_text(json.dumps(dict(sha="ffbdfc4d489bcaf2", accounts={})))
        try:
            _engine(tmp)
        except SystemExit as e:
            assert "fresh directory" in str(e)
        else:
            raise AssertionError("an old-config state.json was resumed")
        eng = _engine(tempfile.mkdtemp(dir=tmp))
        eng._save_state()
        assert list(E.Engine(eng.model, {}, eng.out).accounts) == [a["name"] for a in C.ACCOUNTS], "own state resumes"


def test_09_snapshots_round_trip_exactly_and_refuse_a_changed_file():
    saved = E.DATA
    with tempfile.TemporaryDirectory() as tmp:
        E.DATA = Path(tmp)
        try:
            ix = pd.date_range("2026-10-07 11:00", periods=5, freq="5min", tz="UTC")
            bars = {"ES=F": pd.Series([6700.25, 6701.1, 0.1 + 0.2, 6699.5, 6700.0], index=ix),
                    "GC=F": pd.Series([4012.3, 4013.7], index=ix[1:3])}
            E.save_bars(bars, "t")
            got = E.download(["ES=F", "GC=F"], interval="5m", period="60d", snapshot="t")   # no network: frozen copy
            assert all(got[k].index.equals(v.index) and (got[k].values == v.values).all() for k, v in bars.items())
            gz = Path(tmp, "t.csv.gz")
            gz.write_bytes(gz.read_bytes() + b"x")
            try:
                E.load_bars("t")
            except RuntimeError:
                pass
            else:
                raise AssertionError("a changed snapshot was read")
        finally:
            E.DATA = saved


def test_09b_only_a_complete_pull_is_frozen_and_a_short_snapshot_is_refused():
    import sys
    import types
    ix = pd.date_range("2026-10-07 11:00", periods=3, freq="5min", tz="UTC")
    frame = pd.concat({"ES=F": pd.DataFrame({"Close": [1.0, 2.0, 3.0]}, index=ix)}, axis=1)   # GC=F failed
    saved = E.DATA, sys.modules.get("yfinance")
    with tempfile.TemporaryDirectory() as tmp:
        E.DATA = Path(tmp)
        sys.modules["yfinance"] = types.SimpleNamespace(download=lambda *a, **k: frame)
        try:
            got = E.download(["ES=F", "GC=F"], interval="5m", period="60d", snapshot="t")
            assert list(got) == ["ES=F"] and not Path(tmp, "t.csv.gz").exists(), "an incomplete pull was frozen"
            E.save_bars(got, "t")
            try:
                E.download(["ES=F", "GC=F"], interval="5m", period="60d", snapshot="t")
            except RuntimeError as e:
                assert "GC=F" in str(e)
            else:
                raise AssertionError("a snapshot missing a requested ticker was served")
        finally:
            E.DATA = saved[0]
            if saved[1] is None:
                sys.modules.pop("yfinance", None)
            else:
                sys.modules["yfinance"] = saved[1]


def test_10_post_session_prices_are_fetched_by_the_window_dates():
    seen = {}
    saved = E.download
    E.download = lambda tickers, **kw: seen.update(kw) or {"ES=F": pd.Series([1.0], index=[NOW])}
    try:
        px = E.window_closes()
    finally:
        E.download = saved
    assert "period" not in seen and seen["start"] < C.WINDOW_START_UTC.date() and C.WINDOW_END_UTC.date() < seen["end"]
    assert px["ES=F"].index[0] == NOW + pd.Timedelta(minutes=1), "stamped at bar end, like live_closes"


def test_11_session_hours_follow_local_clocks_and_holidays():
    T = lambda s: pd.Timestamp(s, tz="UTC")
    hm = lambda v, s: tuple(x.strftime("%H:%M") for x in E.session_bounds(v, T(s)))
    assert hm("LSE", "2026-10-07 12:00") == ("07:00", "15:30") and hm("US", "2026-10-07 12:00") == ("13:30", "20:00"), \
        "the recorded runs' hours are unchanged"
    assert hm("LSE", "2026-10-26 12:00") == ("08:00", "16:30"), "UK clocks went back on 2026-10-25"
    assert hm("US", "2026-11-02 15:00") == ("14:30", "21:00"), "US clocks went back on 2026-11-01"
    assert E.minutes_to_close("US", T("2026-11-26 15:00")) == -1.0, "Thanksgiving"
    assert hm("US", "2026-11-27 15:00") == ("14:30", "18:00"), "half day"
    assert E.minutes_to_close("KRX", T("2026-10-09 02:00")) == -1.0, "Hangul Day"
    assert hm("KRX", "2026-10-12 02:00") == ("00:00", "06:30")


def test_12_same_day_replay_uses_the_code_each_run_ran():
    from paper_live import sameday as S
    for name, spec in S.RUNS.items():
        for k in ("config", "engine"):
            assert S._sha(S.HERE / spec[k]) == spec[f"{k}_sha"], f"{name}: archived {k} changed"
    live = [dict(account="A", key="ES=F", direction=1, entry_time="2026-10-07 12:00+00:00"),
            dict(account="A", key="ES=F", direction=1, entry_time="2026-10-07 13:00+00:00")]
    rep = [dict(account="A", key="ES=F", direction=1, entry_time="2026-10-07 12:10+00:00"),
           dict(account="A", key="ES=F", direction=-1, entry_time="2026-10-07 13:00+00:00")]
    assert S.entries_matched(live, rep) == 1, "same account, key and direction within 15 minutes, used once"


def test_13_the_power_line_uses_quantgens_convention():
    from core.quant.gate_stats import MDE_FACTOR
    from paper_live import power as PW
    x = np.array([0.4, -0.2, 0.1, -0.5, 0.3, 0.0, -0.1, 0.2] * 5)
    pl = PW.power_line(x)
    assert math.isclose(pl["mde80_usd"], MDE_FACTOR * x.std(ddof=1) / math.sqrt(len(x)))
    assert pl["sessions_for_0p50"] == math.ceil((MDE_FACTOR * x.std(ddof=1) / 0.5) ** 2)
    assert pl["sessions_for_sr1"] == 1137, "an annual Sharpe of 1 needs (2.1232^2 x 252) sessions whatever the noise"
    assert PW.power_line(np.zeros(30))["mde80_usd"] is None


def test_14_every_account_is_one_trial_in_its_family_ledger():
    from core.quant import gate_ledger as GL
    with tempfile.TemporaryDirectory() as tmp:
        first = E.register_trials(C.ACCOUNTS, span=("2026-10-21", "2026-11-04"), script="t", ledger_dir=tmp)
        again = E.register_trials(C.ACCOUNTS, span=("2026-10-21", "2026-11-18"), script="t", ledger_dir=tmp)
        assert all(r.appended for r in first) and not any(r.appended for r in again), "a re-run is the same trial"
        fams = {E.RULE_FAMILY[a["rules"]] for a in C.ACCOUNTS}
        assert {p.stem for p in Path(tmp).glob("*.jsonl")} == fams
        assert GL.family_ledger("LAZYOWEN", Path(tmp)).n_raw == 4, "CAL, NAIVE, G1 and G2 are four configurations"
        assert all(GL.family_ledger(f, Path(tmp)).verify_chain() for f in fams)


def _days_csv(path: Path, days, diff):
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"day": days, "LAZYOWEN-NAIVE|pnl": [-3.0] * len(days),
                  "LAZYOWEN-NAIVE-G2|pnl": [-3.0 + d for d in diff]}).to_csv(path, index=False)


def _frozen():
    from paper_live import verdict as VD
    return dict(hypotheses=VD._norm(C.HYPOTHESES), digests={a["name"]: E.rule_digest(a) for a in C.ACCOUNTS})


def _holdout(out: Path, frozen, days, diff, digests=None):
    _days_csv(out / "replay_holdout" / "days.csv", days, diff)
    (out / "replay_holdout" / "summary.json").write_text(json.dumps(dict(rule_digest=digests or frozen["digests"])))


def test_15_the_gate_test_uses_exactly_the_planned_holdout_sessions():
    from paper_live import verdict as VD
    fz = _frozen()
    expected = VD.holdout_sessions(fz)
    n = C.HYPOTHESES["H2_cost_gate"]["sessions"]
    assert len(expected) == n and expected[0] > C.HYPOTHESES["frozen"]
    late = pd.Timestamp(expected[-1]).date() + pd.Timedelta(days=3)
    days = ["2026-10-19", "2026-10-20"] + expected + [str((pd.Timestamp(expected[-1]) + pd.offsets.BDay(1)).date())]
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp)
        diff = [-9.0, -9.0] + [2.0 + 0.1 * (i % 3) for i in range(n)] + [-500.0]   # only the planned ones count
        _holdout(out, fz, days, diff)
        v = VD.h2_cost_gate(out, fz, today=late)
        assert v["status"] == "confirmed" and v["sessions"] == n and v["days"] == [expected[0], expected[-1]], v
        gap = [d for d in days if d != expected[2]]                      # a missing session is not replaced
        _holdout(out, fz, gap, [x for d, x in zip(days, diff) if d != expected[2]])
        assert VD.h2_cost_gate(out, fz, today=late)["status"] == "incomplete"
        assert VD.h2_cost_gate(out, fz, today=pd.Timestamp(expected[1]).date())["status"] == "pending"
        _holdout(out, fz, days, diff, digests={**fz["digests"], "LAZYOWEN-NAIVE-G2": "changed"})
        assert VD.h2_cost_gate(out, fz, today=late)["status"].startswith("invalid")
        _holdout(out, fz, days, [-9.0, -9.0] + [0.5, -0.5] * (n // 2) + [9.0])   # no effect: not confirmed
        assert VD.h2_cost_gate(out, fz, today=late)["status"] == "not confirmed"


def test_16_fidelity_rule_run_match_and_exploratory_label():
    from paper_live import verdict as VD
    fz = _frozen()
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp)
        for d in ("replay_sameday", "live", "replay"):
            (out / d).mkdir()
        acc = lambda gap, lt, rt: dict(gap_net=gap, live=dict(trades=lt), replay=dict(trades=rt))  # noqa: E731
        summ = dict(run="t", first_tick="2026-11-04 01:19:41+00:00",
                    accounts={"A": acc(0.3, 10, 9), "IDLE": acc(-0.06, 1, 0), "OFF": acc(0.0, 0, 0)})
        (out / "replay_sameday" / "summary.json").write_text(json.dumps(summ))
        pd.DataFrame({"A|pnl": [0.0, 2.0, -2.0, 1.0], "IDLE|pnl": [0.0, 0.0, 0.0, -0.06]}).to_csv(
            out / "replay" / "days.csv", index=False)
        (out / "replay" / "summary.json").write_text(json.dumps(dict(last="2026-11-03")))
        pre = dict(config_sha="x", window=["2026-11-04 01:20:00+00:00", "2026-11-04 06:20:00+00:00"])
        (out / "live" / "PREREG.json").write_text(json.dumps(pre))
        v = VD.h1_fidelity(out, fz)
        assert v["status"].startswith("exploratory: holds") and set(v["accounts"]) == {"A", "IDLE"}, v
        assert v["accounts"]["IDLE"]["holds"], "one small trade by a near-idle account is inside the $ floor"
        (out / "live" / "PREREG.json").write_text(json.dumps(dict(pre, hypotheses=C.HYPOTHESES)))
        assert VD.h1_fidelity(out, fz)["status"] == "holds"
        (out / "live" / "PREREG.json").write_text(json.dumps(dict(pre, window=["2026-11-05 01:20:00+00:00", ""],
                                                                  hypotheses=C.HYPOTHESES)))
        assert VD.h1_fidelity(out, fz)["status"] == "no same-day replay for this run", "another run's summary"
        (out / "live" / "PREREG.json").write_text(json.dumps(dict(pre, hypotheses=C.HYPOTHESES)))
        (out / "replay" / "summary.json").write_text(json.dumps(dict(last="2026-10-06")))
        assert VD.h1_fidelity(out, fz)["status"].startswith("undefined"), "an older run's replay sd is not this run's"


def test_19_a_late_freeze_is_refused():
    from paper_live import verdict as VD
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp)
        (out / "live").mkdir()
        (out / "live" / "sigmas.json").write_text(json.dumps({"ES=F": {"sigma_ann": 0.15}}))
        late = pd.Timestamp(C.HYPOTHESES["frozen"], tz="UTC") + pd.Timedelta(days=1, hours=9)
        try:
            VD.freeze(out, now=late)
        except SystemExit as e:
            assert "too late" in str(e) and not (out / VD.FROZEN_FILE).exists()
        else:
            raise AssertionError("a record frozen after the holdout began was written")
        rec = VD.freeze(out, now=pd.Timestamp(C.HYPOTHESES["frozen"] + " 08:00", tz="UTC"))
        assert rec["sigmas"]["ES=F"]["sigma_ann"] == 0.15 and (out / "frozen_rule" / "engine.py").exists()
        assert VD.freeze(out, now=late)["frozen_utc"] == rec["frozen_utc"], "an identical re-freeze is a no-op"


def test_17_strategy_lab_registers_real_runs_only():
    import ui.strategy_lab_page as SL
    from core.quant import gate_ledger as GL
    with tempfile.TemporaryDirectory() as tmp:
        grid = [{"lookback": 126}, {"lookback": 252}, {"lookback": 210}]
        span = ["2020-01-02", "2025-01-02"]
        assert SL.register_trials("trend_switch", ["AAA"], grid, 50.0, span, ["SYNTHETIC"], ledger_dir=tmp) is None
        assert not list(Path(tmp).iterdir())
        n = SL.register_trials("trend_switch", ["SPY", "TLT"], grid, 50.0, span, ["YFINANCE"] * 2, ledger_dir=tmp)
        again = SL.register_trials("trend_switch", ["tlt", "spy"], grid, 50.0, span, ["YFINANCE"] * 2, ledger_dir=tmp)
        assert n == again == 3, "case and order of symbols are not new configurations"
        assert {r["market"] for r in GL.family_ledger("E1", Path(tmp)).rows()} == {"US"}


def test_18_concurrent_registrations_keep_the_ledger_chain():
    import threading
    from core.quant import gate_ledger as GL
    with tempfile.TemporaryDirectory() as tmp:
        led = GL.family_ledger("T", Path(tmp))
        row = lambda i, k: dict(rule="T", params={"i": i, "k": k}, timing_class="COMPLIANT",  # noqa: E731
                                span=["2026-01-02", "2026-02-02"], market="US", run_utc="2026-10-20T00:00:00Z",
                                phase="research", script="t")
        ts = [threading.Thread(target=lambda i=i: [GL.register_trial(led, row(i, k)) for k in range(10)])
              for i in range(5)]
        [t.start() for t in ts]
        [t.join() for t in ts]
        assert led.verify_chain() and led.n_raw == 50, "a double-clicked Run must not break the hash chain"


def test_20_outcomes_name_the_worst_asset_across_accounts():
    """Run 1's report named Shell, the worst asset within one account; across accounts it was ISF.L."""
    from paper_live import analyze as A
    row = lambda acc, key, net, cost: dict(account=acc, key=key, name=key, traded=key, direction=1, notional=100.0,  # noqa: E731
                                           hold_min=30.0, pnl_gross=net + cost, cost=cost, pnl_net=net,
                                           exit_reason="x", mae_usd=net - 0.1, risk_usd_1sigma=0.2)
    tdf = pd.DataFrame([row("TREND", "SHEL.L", -3.03, 2.5), row("TREND", "ISF.L", -2.93, 2.5),
                        row("NAIVE", "ISF.L", -0.59, 0.6), row("CORE", "ZB=F", 0.31, 0.1)])
    edf = pd.DataFrame(dict(account=["TREND", "TREND", "NAIVE", "CORE"], n_pos=[2, 6, 5, 7]))
    o = A.outcomes(tdf, edf)
    assert o["worst_assets_all_accounts"][0]["key"] == "ISF.L" and math.isclose(o["worst_assets_all_accounts"][0]["net"], -3.52)
    assert o["worst_asset_by_account"]["TREND"]["key"] == "SHEL.L" and o["best_trades"][0]["key"] == "ZB=F"
    assert o["max_positions"] == {"CORE": 7, "NAIVE": 5, "TREND": 6}


def tests():
    return sorted((n, v) for n, v in globals().items()
                  if n.startswith("test_") and callable(v))


if __name__ == "__main__":
    for n, f in tests():
        f()
        print("PASS", n)
