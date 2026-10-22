"""Parameter-sensitivity grid on the replay sessions (robustness description only -- NOT used to
change the live run). All variants run inside one replay pass, so they see identical signals.

Variants:
  TREND  bar in {5, 15, 30} min x hysteresis in {0.2, 0.4}       (C3 rule; base = 5 min / 0.2)
  LZ-NAIVE kappa in {0.25, 0.5, 1.0} at 8 pp; edge in {5, 11} pp at kappa 0.5
  LZ-CAL edge in {2, 5} pp                                       (base 8 pp never trades)
  TACT-NOGATE: QG-TACTICAL without the cost gate                 (what the calibrated p does gross)
  TREND-b5-h0.2-G1/G2: the base C3 rule behind the shared cost gate at 1x / 2x
  (variants with gate_mult inherit Engine._open's gate; the others run without it)
Cost sensitivity is computed per trade: net at 2x QUANTGEN costs and at LOWCOST_BP.

    python -m paper_live.grid
"""
from __future__ import annotations

import json
import math
import time

import numpy as np
import pandas as pd

from paper_live import config as C
from paper_live import engine as E
from paper_live import replay as R

GRID = []
for bar in (5, 15, 30):
    for h in (0.2, 0.4):
        GRID.append(dict(name=f"TREND-b{bar}-h{h}", rules="trend", costs="COST_CLASS_BP", prob="cal", bar=bar, hyst=h))
for k in (0.25, 0.5, 1.0):
    GRID.append(dict(name=f"LZNAIVE-k{k}-e8", rules="lazyowen", costs="COST_CLASS_BP", prob="naive", kappa=k, L=dict(edge_pp=0.08)))
for e in (0.05, 0.11):
    GRID.append(dict(name=f"LZNAIVE-k0.5-e{int(e * 100)}", rules="lazyowen", costs="COST_CLASS_BP", prob="naive", kappa=0.5, L=dict(edge_pp=e)))
for e in (0.02, 0.05):
    GRID.append(dict(name=f"LZCAL-e{int(e * 100)}", rules="lazyowen", costs="COST_CLASS_BP", prob="cal", L=dict(edge_pp=e)))
GRID.append(dict(name="TACT-NOGATE", rules="quantgen", costs="COST_CLASS_BP", prob="cal", Q=dict(cost_gate_mult=0.0)))
# 2026-10-18: QG-TREND left the live accounts; its rule is measured here, ungated and with the shared gate
for m in (1.0, 2.0):
    GRID.append(dict(name=f"TREND-b5-h0.2-G{m:.0f}", rules="trend", costs="COST_CLASS_BP", prob="cal", bar=5, hyst=0.2, gate_mult=m))

BASE_L, BASE_Q = dict(C.L), dict(C.Q)
# institutional-cost sensitivity; KRX stocks keep the 0.20% sell tax (~10 bp a side averaged)
LOW = {**C.LOWCOST_BP, "krx_etf": 1.0, "krx_stock": 11.0}


def trend_tables(closes, bar, hyst):
    from core.quant import strategies as S

    tabs = {}
    for key in C.UNIVERSE:
        s = closes.get(key)
        if s is None:
            continue
        sb = s.resample(f"{bar}min", label="right", closed="right").last().dropna()
        px = sb.to_numpy(float)
        on = np.asarray(S.crypto_trend(px, hysteresis=hyst)).reshape(len(px), -1)[:, 0]
        votes = [np.sign(sb - sb.shift(k)) for k in (7, 14, 21, 28)]
        votes += [np.sign(sb - sb.rolling(n).mean()) for n in (10, 20, 50, 100, 200)]
        tabs[key] = pd.DataFrame(dict(on=on, vote=pd.concat(votes, axis=1).mean(axis=1).to_numpy()), index=sb.index)
    return tabs


class GridEngine(R.ReplayEngine):
    def __init__(self, model, sigmas, ttabs, day, sink):
        self.ttabs = ttabs
        super().__init__(model, sigmas, {}, day, sink)
        self.accounts = {g["name"]: E.make_account(g) for g in GRID}
        self.last_decision = {g["name"]: None for g in GRID}
        self.params = {g["name"]: g for g in GRID}

    def signals(self, closes, now):
        sig = E.Engine.signals(self, closes, now)
        for key, row in sig.items():
            if "bars_last_hour" in row:
                row["bars_last_hour"] *= 5
            if row.get("ok"):
                for k in (0.25, 0.5, 1.0):
                    row[f"p_naive_{k}"] = float(np.clip(0.5 * (1 + math.erf(k * row["z60"] / math.sqrt(2))), *C.P_CLIP))
            for (bar, h), tabs in self.ttabs.items():
                tab = tabs.get(key)
                if tab is None:
                    continue
                tab = tab[tab.index <= now]
                ok = len(tab) >= C.TREND["min_bars"]
                row[f"tr_{bar}_{h}"] = (ok, float(tab.on.iloc[-1]) if ok else 0.0, float(tab.vote.iloc[-1]) if ok else 0.0)
        return sig

    def step_trend(self, acc, sig, closes, now, final=False):
        g = self.params[acc.name]
        sig2 = {}
        for k, v in sig.items():
            ok, on, vote = v.get(f"tr_{g['bar']}_{g['hyst']}", (False, 0.0, 0.0))
            sig2[k] = dict(v, trend_ok=ok, trend_on=on, trend_vote=vote)
        return super().step_trend(acc, sig2, closes, now, final)

    def step_lazyowen(self, acc, sig, closes, now, final=False):
        g = self.params[acc.name]
        if acc.prob == "naive":
            sig = {k: (dict(v, p_naive=v[f"p_naive_{g['kappa']}"]) if v.get("ok") else v) for k, v in sig.items()}
        E.C.L = {**BASE_L, **g.get("L", {})}
        try:
            return super().step_lazyowen(acc, sig, closes, now, final)
        finally:
            E.C.L = BASE_L

    def step_quantgen(self, acc, sig, closes, now, final=False):
        g = self.params[acc.name]
        E.C.Q = {**BASE_Q, **g.get("Q", {})}
        try:
            return super().step_quantgen(acc, sig, closes, now, final)
        finally:
            E.C.Q = BASE_Q


def main():
    t0 = time.time()
    out = E.OUT / "grid"
    out.mkdir(parents=True, exist_ok=True)
    E.trend_state = lambda s1: {}
    closes = R.load()
    ttabs = {(b, h): trend_tables(closes, b, h) for b in (5, 15, 30) for h in (0.2, 0.4)}
    sigmas = json.loads((E.OUT / "live" / "sigmas.json").read_text())
    model = E.Model.load(E.OUT / "model_train_only.json")
    es = closes[R.ANCHOR]
    days = sorted({d for d in es.index.normalize().date if pd.Timestamp(d).weekday() < 5})
    first = max(s.index[0] for s in closes.values()).date()   # every series must have history
    days = [d for d in days if first < d < C.WINDOW_START_UTC.date()]
    sink, rows = {}, []
    for d in days:
        day0 = pd.Timestamp(d, tz="UTC")
        lo, hi = day0 + R.WS - pd.Timedelta(days=6), day0 + R.WE + pd.Timedelta(minutes=8)
        cd = {t: s[(s.index > lo) & (s.index <= hi)] for t, s in closes.items()}
        if len(cd.get(R.ANCHOR, [])) == 0 or cd[R.ANCHOR].index[-1] < day0 + R.WE - pd.Timedelta(minutes=42):
            continue
        eng = GridEngine(model, sigmas, ttabs, d, sink)
        for now in pd.date_range(day0 + R.WS + pd.Timedelta(minutes=3), day0 + R.WE - pd.Timedelta(minutes=2), freq="5min"):
            eng.step(now, cd)
        eng.step(day0 + R.WE, cd, final=True)
        row = dict(day=str(d))
        for name, acc in eng.accounts.items():
            tr = [t for t in sink.get("trades.jsonl", []) if t["day"] == str(d) and t["account"] == name]
            gross = sum(t["pnl_gross"] for t in tr)
            costs = acc.costs_paid
            # priced on traded value (entry + exit value, as Engine._close), so a tick-floored fill is not rescaled
            low = sum((t["notional"] + abs(t["notional"] * (1 + t["ret_traded"]))) * LOW[C.UNIVERSE[t["key"]]["cost"]] * 1e-4
                      for t in tr)
            row.update({f"{name}|pnl": acc.cash - C.START_EQUITY, f"{name}|gross": gross, f"{name}|costs": costs,
                        f"{name}|net2x": gross - 2 * costs, f"{name}|netlow": gross - low, f"{name}|trades": len(tr)})
        rows.append(row)
        print(d, round(time.time() - t0), "s", flush=True)
    df = pd.DataFrame(rows)
    df.to_csv(out / "days.csv", index=False)
    summ = dict(n_days=int(len(df)), seconds=round(time.time() - t0, 1), variants={})
    for g in GRID:
        n = g["name"]
        def st(col):
            x = df[f"{n}|{col}"].to_numpy(float)
            sd = x.std(ddof=1)
            return dict(mean=float(x.mean()), t=float(x.mean() / (sd / math.sqrt(len(x)))) if sd > 0 else None,
                        win=float((x > 0).mean()))
        summ["variants"][n] = dict(net=st("pnl"), gross=st("gross"), net_2x_cost=st("net2x"), net_lowcost=st("netlow"),
                                   trades_per_day=float(df[f"{n}|trades"].mean()), costs_per_day=float(df[f"{n}|costs"].mean()))
    (out / "summary.json").write_text(json.dumps(summ, indent=1))
    for n, v in summ["variants"].items():
        print(f"{n:18s} net {v['net']['mean']:+7.2f} (t {v['net']['t'] if v['net']['t'] is None else round(v['net']['t'], 1)}) "
              f"gross {v['gross']['mean']:+6.2f} (t {v['gross']['t'] if v['gross']['t'] is None else round(v['gross']['t'], 1)}) "
              f"lowcost {v['net_lowcost']['mean']:+6.2f} 2x {v['net_2x_cost']['mean']:+7.2f} trades/d {v['trades_per_day']:.1f}")


if __name__ == "__main__":
    main()
