"""Self-checks of the GROKTEAM BOOK desk's money logic. No network: synthetic bars, quotes and ledgers in temp dirs.

    python -m grokteam.selfcheck            # also run by tests/run_all.py as the "grokteam" suite

Each check names what it defends: the fee and payoff arithmetic, SIZE (half Kelly, 6% cap, $50 floor), the
digital probability, no look-ahead in the hourly bars or the quotes, each account's entry rule, the cluster t,
the verdict rules, the sha-checked cache and the trial-ledger rows.
"""
from __future__ import annotations

import json
import math
import re
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

from grokteam import book as B

T = 1_792_515_600                    # a top-of-hour close (2026-10-20 18:00 UTC)
DEC = T - B.RULES["decision_s"]


def _row(ticker="K1", strike=100.0, y=1, p=0.5, ask=0.5, bid=0.49, f_ask=None, f_bid=None, f_vol=1e6):
    return dict(ticker=ticker, strike=strike, y=y, p_raw=p, p_cal=p, ask=ask, bid=bid,
                f_ask=ask if f_ask is None else f_ask, f_bid=bid if f_bid is None else f_bid, f_vol=f_vol)


def test_fee_and_payoff():
    assert B.fee(120, 0.50) == 2.10                            # 0.07 x 120 x 0.25
    assert B.fee(64, 0.93) == 0.30                             # 0.2916 rounded up to the cent
    assert B.fee(1, 0.50) == 0.02 and B.fee(0, 0.5) == 0.0
    c, pnl, prem = B.buy(60, 0.93, True, 1e9)
    assert c == 64 and abs(pnl - 4.18) < 1e-9 and abs(prem - 59.82) < 1e-9
    c, pnl, prem = B.buy(60, 0.93, False, 1e9)
    assert c == 64 and abs(pnl + 59.82) < 1e-9
    assert B.buy(60, 0.93, True, 10)[0] == 10                  # at most the fill candle's volume
    c, pnl, prem = B.buy(60, 0.50, True, 1e9)                  # the fee is paid out of the dollars staked
    assert c == 115 and prem <= 60 and abs(prem - 59.52) < 1e-9


def test_size_half_kelly_cap_and_floor():
    g, f = B.ACCOUNTS["PRED-GATED"], B.ACCOUNTS["PRED-FLB"]
    assert B.stake(g, dict(p=0.95, m=0.93), 1000.0) == 60.0     # half Kelly 142.86, capped at 6%
    assert abs(B.stake(g, dict(p=0.5, m=0.40), 1000.0) - 60.0) < 1e-9
    assert B.stake(g, dict(p=0.935, m=0.93), 1000.0) == 0.0     # half Kelly $35.7 < $50 minimum
    assert B.stake(g, dict(p=0.99, m=0.93), 833.0) == 0.0       # 6% of $833 < $50: halted
    assert B.stake(f, dict(p=math.nan, m=0.93), 1000.0) == 60.0 and B.stake(f, dict(p=math.nan, m=0.93), 833.0) == 0.0


def test_digital_probability():
    assert abs(B.p_above(100, 100, 0.01, 4.0) - 0.5) < 1e-12
    ps = [B.p_above(k, 100, 0.01, 4.0) for k in (98, 99, 100, 101, 102)]
    assert all(a > b for a, b in zip(ps, ps[1:]))
    assert abs(B.p_above(101, 100, 0.01, math.inf) - 0.15998) < 1e-3          # normal: P(z > 0.995)
    # a unit-variance t has thinner shoulders and fatter tails than the normal at the same sigma
    assert B.p_above(101, 100, 0.01, 3.5) < B.p_above(101, 100, 0.01, math.inf) < 0.5
    assert B.p_above(104, 100, 0.01, 3.5) > B.p_above(104, 100, 0.01, math.inf)


def _bars(n=2200, seed=3):
    rng = np.random.default_rng(seed)
    o = np.arange(DEC - DEC % 3600 - 3600 * n, DEC - DEC % 3600, 3600, dtype=np.int64)   # last bar closes at DEC's hour
    season = 1 + 0.8 * np.sin((o % 86400) / 86400 * 2 * np.pi)
    r = np.zeros(o.size)
    s2 = 1e-5
    for i in range(1, o.size):                                # a GARCH(1,1) with a daily cycle
        s2 = 2e-7 + 0.08 * r[i - 1] ** 2 / season[i - 1] ** 2 + 0.9 * s2
        r[i] = math.sqrt(s2) * season[i] * rng.standard_t(6) / math.sqrt(1.5)
    return o, 80000 * np.exp(np.cumsum(r))


def test_model_sees_only_closed_bars():
    o, c = _bars()
    ok, sig, nu, why = B.model_at(DEC, T, o, c)
    assert ok and 0 < sig < 0.05 and nu > 2, why
    # the bar the decision sits in (closing at T) and anything later must not move the forecast
    o2 = np.append(o, [o[-1] + 3600, o[-1] + 7200])
    c2 = np.append(c, [c[-1] * 1.5, c[-1] * 0.5])
    assert B.model_at(DEC, T, o2, c2)[:3] == (ok, sig, nu)
    # a missing last closed bar is not papered over
    assert B.model_at(DEC, T, o[:-1], c[:-1])[0] is False


def test_stationarity_warning_is_not_a_skip():
    import dataclasses
    o, c = _bars()
    real = B.G.fit_garch
    try:
        B.G.fit_garch = lambda *a, **k: dataclasses.replace(real(*a, **k), at_bound=("stationarity",))
        assert B.model_at(DEC, T, o, c)[0] is True             # alpha + beta > 0.995 is a warning
        B.G.fit_garch = lambda *a, **k: dataclasses.replace(real(*a, **k), at_bound=("stationarity",), converged=False)
        assert B.model_at(DEC, T, o, c)[0] is True             # stopped on the penalty wall: used
        B.G.fit_garch = lambda *a, **k: dataclasses.replace(real(*a, **k), at_bound=(), converged=False)
        assert B.model_at(DEC, T, o, c)[0] is False            # any other non-convergence is a skip
        B.G.fit_garch = lambda *a, **k: dataclasses.replace(real(*a, **k), at_bound=("beta",))
        assert B.model_at(DEC, T, o, c)[0] is False            # a parameter bound is a skip
    finally:
        B.G.fit_garch = real


def test_strike_table_reads_decision_and_fill_candles_only():
    tmp = Path(tempfile.mkdtemp(prefix="grokteam_"))
    keep = (B.DATA, B.hourly_bars, B.model_at)
    try:
        B.DATA = tmp
        B.hourly_bars = lambda need: (np.array([0]), np.array([1.0]))
        B.model_at = lambda dec, close, bo, bc: (True, 0.002, 5.0, "")
        cand = {str(DEC - 60): [0.10, 0.08, 5.0], str(DEC): [0.60, 0.58, 7.0], str(DEC + 60): [0.62, 0.59, 9.0],
                str(DEC + 120): [0.99, 0.98, 99.0]}
        old = {str(DEC - 300): [0.70, 0.69, 0.0], str(DEC + 60): [0.71, 0.70, 3.0]}      # no candle at DEC
        stale = {str(DEC - 1860): [0.70, 0.69, 0.0]}                                     # beyond 30 min
        recs = [dict(event=f"E{i}", close_s=T - 3600 * (30 - i), decision_s=DEC - 3600 * (30 - i), spot=80000.0,
                     expiration_value=80080.0, binance_vwap_close=80000.0, settled_s=T - 3600 * (30 - i) + 120,
                     strikes=[]) for i in range(30)]
        recs.append(dict(event="E30", close_s=T, decision_s=DEC, spot=80000.0, expiration_value=80080.0,
                         binance_vwap_close=80000.0, settled_s=T + 120,
                         strikes=[dict(ticker="X", strike=80100.0, result="no", candles=cand),
                                  dict(ticker="Y", strike=80000.0, result="yes", candles=old),
                                  dict(ticker="Z", strike=79900.0, result="yes", candles=stale)]))
        ev, st = B.strike_table(recs, None)
        r = st.iloc[0]
        assert (r["ask"], r["bid"], r["f_ask"], r["f_bid"], r["f_vol"]) == (0.60, 0.58, 0.62, 0.59, 9.0)
        y, z = st.iloc[1], st.iloc[2]
        assert (y["ask"], y["bid"], y["quote_age_s"]) == (0.70, 0.69, 300)          # last quote within 30 min
        assert math.isnan(z["ask"]) and z["f_vol"] == 0.0                          # too old, and no fill candle
        e = ev.set_index("event").loc["E30"]
        assert abs(e["basis"] - 0.001) < 1e-12 and abs(e["S"] - 80080.0) < 1e-6   # BRTI 0.1% over Binance
        assert abs(r["p_raw"] - B.p_above(80100.0, 80080.0, 0.002, 5.0)) < 1e-12
        assert ev.set_index("event").loc["E0", "model_ok"] == False           # noqa: E712  no basis yet
    finally:
        B.DATA, B.hourly_bars, B.model_at = keep


def test_entry_rules():
    rows = pd.DataFrame([_row("A", p=0.97, ask=0.93, bid=0.92), _row("B", p=0.90, ask=0.85, bid=0.84),
                         _row("C", p=0.30, ask=0.50, bid=0.40), _row("D", p=0.50, ask=0.935, bid=0.93)])
    g, l8, fl = (B.ACCOUNTS[k] for k in ("PRED-GATED", "PRED-LIT8", "PRED-FLB"))
    # GATED: A yes (edge 0.04 > 2 x fee 0.0091), B yes (0.05 > 0.0179); C fails the spread, D the edge
    bet = B.choose(g, B.candidates(g, rows))
    assert (bet["ticker"], bet["side"]) == ("B", "yes")
    # LIT8: only C's NO side clears 8 points (bid 0.40 - p 0.30 = 0.10), and its price 0.60 is inside the band
    bet = B.choose(l8, B.candidates(l8, rows))
    assert (bet["ticker"], bet["side"], round(bet["m"], 2)) == ("C", "no", 0.6)
    # FLB: the price nearest 93c within [0.90, 0.95] and spread <= 3c, model-free
    bet = B.choose(fl, B.candidates(fl, rows))
    assert bet["ticker"] == "A" and bet["m"] == 0.93
    # a NaN probability never trades
    assert B.candidates(g, pd.DataFrame([_row("A", p=math.nan, ask=0.85, bid=0.84)])) == []


def test_accounts_settle_and_path():
    rows = []
    for i, y in enumerate((1, 1, 0)):
        rows.append(dict(_row(f"K{i}", y=y, p=math.nan, ask=0.93, bid=0.92), event=f"E{i}", close_s=T + 3600 * i,
                         window="eval", p_cal=math.nan))
    rows.append(dict(_row("S", y=1, p=math.nan, ask=0.93, bid=0.92), event=next(iter(B.SEEN)), close_s=T + 3600 * 9,
                     window="eval", p_cal=math.nan))
    bets = B.run_accounts(pd.DataFrame(rows))
    f = bets[bets["account"] == "PRED-FLB"]
    assert list(f["event"]) == ["E0", "E1", "E2"]               # a seen event never counts
    assert np.allclose(f["pnl"], [4.18, 4.18, -59.82]) and np.allclose(f["equity"], [1004.18, 1008.36, 948.54])
    assert (bets["account"] != "PRED-GATED").all()              # no calibrated p, no model bet


def test_block_t():
    close = T + 86400 * np.arange(40)
    r = np.where(np.arange(40) % 2 == 0, 0.03, -0.01)
    s = B.block_t(r, close, int(close[0]))
    assert s["n"] == 40 and abs(s["mean"] - 0.01) < 1e-12 and s["G"] == 8
    assert s["lo"] < s["mean"] < s["hi"] and 0 < s["p"] < 0.05
    assert B.block_t([], [], 0)["n"] == 0


def test_verdict_rules():
    base = dict(ret_n=5000, ret_hi=0.02, ret_lo=0.005, holm_p=0.01, ret_stress_mean=0.004, n_star=4000,
                vs_coin=dict(p=0.01), vs_flb=dict(p=0.05))
    W = lambda **kw: dict(model_skip_rate=0.03, skill_cal=dict(passed=True), skill_raw=dict(passed=True),  # noqa: E731
                          accounts={"PRED-GATED": dict(base, **kw)})
    assert B.verdict("PRED-GATED", W()) == "PAPER-CANDIDATE"
    assert B.verdict("PRED-GATED", W(ret_n=600)) == "PAPER-CANDIDATE"     # n below N* is reported, not gated
    assert B.verdict("PRED-GATED", W(vs_flb=dict(p=0.2))) == "INCONCLUSIVE"
    assert B.verdict("PRED-GATED", W(ret_hi=-0.001)) == "REJECT"
    w = W(); w["skill_cal"] = dict(passed=False)
    assert B.verdict("PRED-GATED", w) == "REJECT"
    w = W(); w["model_skip_rate"] = 0.06
    assert B.verdict("PRED-GATED", w) == "INVALID"
    w = W(ret_n=0); w["model_skip_rate"] = 1.0
    assert B.verdict("PRED-GATED", w) == "INVALID"            # a model that never ran is not 'no bets'


def test_skill_one_sided_direction():
    rng = np.random.default_rng(9)
    rows = []
    for e in range(60):
        for k in range(4):
            p = rng.uniform(0.1, 0.9)
            y = int(rng.uniform() < p)
            rows.append(dict(event=f"E{e}", scored=True, y=y, mid=p, p_raw=float(np.clip(p + rng.normal(0, 0.25), 0.01, 0.99))))
    s = B.skill(pd.DataFrame(rows), "p_raw")                    # a noisier model than the market
    assert s["dm_t"] > 0 and s["p_one_sided"] > 0.5 and not s["passed"]


def test_tradegen_copy_is_permanently_blinded():
    # TRADEGEN's copy never takes the look (QUANTGEN holds the record): forward events are dropped at any date,
    # and the freeze record and its byte copies stay in place (deleting them would remove the gate's anchor)
    fz = B.ts(B.FROZEN_UTC)
    assert B.ts(json.loads(B.PREREG.read_text(encoding="utf-8"))["frozen_utc"]) == fz
    assert (B.PREREG.parent / "frozen_book" / "grokteam" / "book.py").is_file()
    recs = [dict(event="A", decision_s=fz - 10), dict(event="B", decision_s=fz + 10)]
    for freeze in (fz, fz + 86400 * 365):                      # a later freeze time can never widen the cut
        kept, status = B.forward_gate(recs, freeze)
        assert [r["event"] for r in kept] == ["A"] and status.startswith("blinded permanently")
    assert B.FREEZE_BY <= B.FROZEN_UTC[:10]                     # prereg.freeze() refuses: no re-freeze here, ever

    class Stop(Exception):
        pass
    d = B.RULES["decision_s"]
    pre, post = dict(event="A", close_s=fz + d - 10), dict(event="B", close_s=fz + d + 10)
    iso = lambda s: B.datetime.fromtimestamp(s, B.timezone.utc).isoformat()       # noqa: E731
    tmp = Path(tempfile.mkdtemp(prefix="grokteam_blind_"))
    asked = []

    def fetch(evs):                                             # every call recorded, so a second fetch is seen too
        asked.extend(e["event"] for e in evs)
        return [], []

    def stop(*a, **k):
        raise Stop

    keep = (B.DATA, B.OUT, B.kalshi, B.settled_events, B.fetch_all, B.strike_table, B.register_trials)
    try:
        B.DATA, B.OUT = tmp / "data", tmp / "out"
        B.kalshi = lambda path, **kw: dict(events=[dict(event_ticker=e["event"], strike_date=iso(e["close_s"]))
                                                   for e in (pre, post)])
        assert [e["event"] for e in B.settled_events(fz + 86400)] == ["A"]          # the listing itself is cut
        B.write_cached(B.DATA / "kalshi" / "events.json.gz", dict(listed_s=2**40, events=[pre, post]))
        B._MANIFESTS.clear()
        assert [e["event"] for e in B.settled_events(fz + 86400)] == ["A"]          # so is an older cache
        B.settled_events = lambda until: [pre, post]           # main must cut again even if the listing leaked
        B.fetch_all, B.strike_table, B.register_trials = fetch, stop, stop
        try:
            B.main(["--limit", "10", "--end", "2027-06-01"])    # long after FORWARD_END
        except Stop:
            pass
        except SystemExit as exc:
            raise AssertionError(f"book.main exited: {exc}")
    finally:
        B.DATA, B.OUT, B.kalshi, B.settled_events, B.fetch_all, B.strike_table, B.register_trials = keep
        B._MANIFESTS.clear()
    assert asked == ["A"], asked                                # a forward event is never even fetched


def test_calibration_recovers_identity():
    rng = np.random.default_rng(5)
    p = rng.uniform(0.02, 0.98, 20000)
    y = rng.uniform(size=p.size) < p
    c = B.fit_calibration(p, y)
    assert abs(c["a"]) < 0.08 and abs(c["b"] - 1) < 0.08
    assert np.allclose(B.calibrate([0.2, 0.5], dict(a=0.0, b=1.0)), [0.2, 0.5])


def test_cache_is_sha_checked():
    tmp = Path(tempfile.mkdtemp(prefix="grokteam_"))
    p = tmp / "x.json.gz"
    B.write_cached(p, {"a": 1})
    B._MANIFESTS.clear()
    assert B.read_cached(p) == {"a": 1} and B.read_cached(tmp / "missing.json.gz") is None
    raw = bytearray(p.read_bytes())
    raw[-1] ^= 0xFF                                            # flip the last byte (gzip's size field)
    p.write_bytes(bytes(raw))
    B._MANIFESTS.clear()
    try:
        B.read_cached(p)
        raise AssertionError("an altered cache file was read")
    except RuntimeError:
        pass


def test_ledger_rows_new_family_only():
    from core.quant import gate_ledger as GL
    tmp = Path(tempfile.mkdtemp(prefix="ledger_"))
    first = B.register_trials(ledger_dir=tmp)
    again = B.register_trials(ledger_dir=tmp)
    assert [r.appended for r in first] == [True] * 3 and [r.appended for r in again] == [False] * 3
    assert sorted(p.name for p in tmp.glob("*.jsonl")) == [f"{B.FAMILY}.jsonl"]
    assert GL.family_ledger(B.FAMILY, tmp).verify_chain().ok
    assert len({r.row["config_id"] for r in first}) == 3


def test_version_pin_ignores_python_patch():
    from grokteam import prereg as P
    v = P.versions()
    assert P._same_versions(dict(v, python=v["python"].rsplit(".", 1)[0] + ".999"), v)   # Store auto-update
    assert not P._same_versions(dict(v, numpy="0.0.1"), v) and not P._same_versions(None, v)


def test_no_paper_live_import():
    # paper_live.engine silences every warning at import and is frozen until the H2 readout
    for p in Path(B.__file__).parent.glob("*.py"):
        assert not re.search(r"^\s*(from|import)\s+paper_live", p.read_text(encoding="utf-8"), re.M), p.name


def tests():
    return sorted((n, v) for n, v in globals().items() if n.startswith("test_") and callable(v))


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    bad = 0
    for n, f in tests():
        try:
            f()
            print(f"PASS {n}")
        except Exception as exc:
            bad += 1
            print(f"FAIL {n}: {type(exc).__name__}: {exc}")
    print(f"{len(tests()) - bad}/{len(tests())} passed")
    raise SystemExit(1 if bad else 0)
