"""Build the session report page from out/analysis, out/replay, out/grid and narrative.json.

    python -m paper_live.report [--out PATH]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path

import pandas as pd

from paper_live import config as C
from paper_live import engine as E

HERE = Path(__file__).resolve().parent
OUT = E.OUT
AN_DIR = os.environ.get("ANALYSIS_DIR", "analysis")   # analysis_v2: the corrected analysis of 2026-10-20
KST0 = pd.Timestamp("2026-10-07 00:00", tz="Asia/Seoul")
VENUE_LABEL = {"US": "NYSE/Nasdaq ETF", "LSE": "LSE", "CME": "CME futures", "FX": "FX spot"}
SESSION_MIN = {"US": 390, "LSE": 510}
META = {
    "QG-TREND": dict(slot=1, short="QG-TREND", label="QG-TREND · C3 trend rule",
                     desc="QUANTGEN's only gate-passing rule family, moved to 5-minute bars; long/flat, GARCH-t sized"),
    "QG-TACTICAL": dict(slot=5, short="QG-TACTICAL", label="QG-TACTICAL · probability + cost gate",
                        desc="Calibrated 60-minute up/down probability; trades only if the expected move beats round-trip cost",
                        why_none="Its cost gate refused every candidate: the expected 60-minute move never exceeded the round-trip cost."),
    "QG-CORE": dict(slot=3, short="QG-CORE", label="QG-CORE · risk-budgeted basket",
                    desc="Inverse GARCH-t volatility weights on seven futures; no timing, held to the close"),
    "LAZYOWEN-CAL": dict(slot=4, short="LZ-CAL", label="LAZYOWEN-CAL · guide rules, calibrated p",
                         desc="The guide's 8 pp edge, half-Kelly 6% cap, 5 positions, fed QUANTGEN's calibrated probability",
                         why_none="The calibrated probability never differed from 50% by the 8 percentage points the guide requires."),
    "LAZYOWEN-NAIVE": dict(slot=2, short="LZ-NAIVE", label="LAZYOWEN-NAIVE · guide rules, opinion p",
                           desc="The same rules fed an overconfident momentum 'opinion', standing in for Grok's self-rated probability"),
}
ORDER = ["QG-TREND", "QG-TACTICAL", "QG-CORE", "LAZYOWEN-CAL", "LAZYOWEN-NAIVE"]


def kst_min(ts) -> float:
    t = pd.Timestamp(ts)
    t = t.tz_localize("UTC") if t.tzinfo is None else t
    return (t.tz_convert("Asia/Seoul") - KST0).total_seconds() / 60.0


def hm(ts) -> str:
    return pd.Timestamp(ts).tz_convert("Asia/Seoul").strftime("%H:%M")


def build() -> dict:
    an = json.loads((OUT / AN_DIR / "summary.json").read_text())
    paths = json.loads((OUT / AN_DIR / "equity_paths.json").read_text())
    sig = json.loads((OUT / "live" / "sigmas.json").read_text())
    tpath = OUT / AN_DIR / "trades.csv"
    tdf = pd.read_csv(tpath) if tpath.exists() and tpath.stat().st_size > 5 else pd.DataFrame()
    nar = json.loads((HERE / "narrative.json").read_text(encoding="utf-8"))
    rd = pd.read_csv(OUT / "replay" / "days.csv")
    rs = json.loads((OUT / "replay" / "summary.json").read_text())
    gs = json.loads((OUT / "grid" / "summary.json").read_text())
    cal = json.loads((OUT / "calibration.json").read_text())

    accounts = []
    for n in ORDER:
        a = an["accounts"][n]
        r = rs["accounts"][n]["all"]
        accounts.append(dict(id=n, **META[n], net=a["net_pnl"], final=a["final_equity"], gross=a["gross_pnl_closed"],
                             costs=a["costs"], trades=a["closed_trades"], win_rate=a["win_rate"], maxdd=a["max_drawdown"],
                             peak_gross=a["peak_gross"], replay_pct=an.get("replay_percentile", {}).get(n),
                             replay_mean=r["mean"], replay_sd=r["sd"] or 0.0))

    trades, by_asset, risky = [], {}, []
    for _, t in tdf.iterrows():
        meta = C.UNIVERSE[t.key]
        venue = meta["venue"]
        if t.traded != t.key:
            route = f"short via {t.traded} (1x inverse ETF)"
        elif t.direction > 0:
            route = "long" + (" (synthetic notional)" if venue in ("CME", "FX") else "")
        else:
            route = "short (synthetic notional)"
        sig_h = sig[t.key]["sigma_ann"] / math.sqrt(252) * math.sqrt(60 / SESSION_MIN.get(venue, 1380))
        row = dict(account=t.account, key=t.key, name=meta["name"], venue=VENUE_LABEL[venue], route=route,
                   notional=float(t.notional), entry_kst=hm(t.entry_time), exit_kst=hm(t.exit_time), hold=float(t.hold_min),
                   entry_px=float(t.entry_px), exit_px=float(t.exit_px), pnl_net=float(t.pnl_net), pnl_gross=float(t.pnl_gross),
                   cost=float(t.cost), reason=str(t.exit_reason).replace("_", " "),
                   mae_usd=None if pd.isna(t.get("mae_usd")) else float(t.mae_usd),
                   mfe_usd=None if pd.isna(t.get("mfe_usd")) else float(t.mfe_usd))
        trades.append(row)
        k = (t.account, t.key)
        b = by_asset.setdefault(k, dict(account=t.account, key=t.key, name=meta["name"], venue=VENUE_LABEL[venue],
                                        net=0.0, gross=0.0, cost=0.0, trades=0))
        b["net"] += row["pnl_net"]; b["gross"] += row["pnl_gross"]; b["cost"] += row["cost"]; b["trades"] += 1
        why = []
        if venue in ("LSE", "US"):
            # the per-side rate this trade paid, doubled (exit leg is charged on exit value; LSE: 50 bp proxy in Run 1)
            rt_bp = 2e4 * float(t.cost) / (float(t.notional) * (1 + abs(1 + float(t.ret_traded))))
            why.append(f"the {rt_bp:.0f} bp round trip is {rt_bp * 1e-4 / sig_h:.1f}× its 1σ hourly move")
        if sig[t.key]["sigma_ann"] > 0.25:
            why.append(f"high-volatility instrument (GARCH-t σ {sig[t.key]['sigma_ann']:.0%})")
        if venue in ("LSE", "CME"):
            why.append(f"priced on a {'~16' if venue == 'LSE' else '~10'}-minute delayed quote")
        if t.traded != t.key:
            why.append("inverse ETF tracks the index daily, not intraday")
        if not math.isnan(t.entry_p) and abs(t.entry_p - 0.5) > 0.25:
            why.append(f"entered on a {t.entry_p:.0%} 'opinion' probability the model could not justify")
        risky.append(dict(row, risk=float(t.notional * sig_h), why="; ".join(why) or "within normal bounds"))
    risky.sort(key=lambda r: -r["risk"])

    eq = {}
    for n in ORDER + ["EW_ALL_BH"]:
        eq[n] = [[round(kst_min(t), 2), round(v, 4)] for t, v in paths.get(n, [])]

    ws, we = kst_min(C.WINDOW_START_UTC), kst_min(C.WINDOW_END_UTC)
    clock = dict(start=ws, end=we,
                 rows=[dict(name="LSE", color="var(--s3)", spans=[[ws, kst_min("2026-10-07 15:30Z"), "LSE cash session to 00:30 KST"]]),
                       dict(name="NYSE", color="var(--s1)", spans=[[kst_min("2026-10-07 13:30Z"), we, "NYSE opens 22:30 KST"]]),
                       dict(name="CME", color="var(--s5)", spans=[[ws, we, "CME Globex futures, ~10 min delayed feed"]]),
                       dict(name="FX", color="var(--s4)", spans=[[ws, we, "FX spot, near real time"]])],
                 ticks=[[m, f"{int(m // 60) % 24:02d}:00"] for m in range(int(math.ceil(ws / 60) * 60), int(we) + 1, 60)],
                 marks=[[kst_min(an["first_tick"]), "Live start " + hm(an["first_tick"]), "live"],
                        [kst_min("2026-10-07 12:17:06Z"), "Patched restart 21:17", "amend"],
                        [we, "Forced flatten 01:42", "end"]])

    days = rd.day.tolist()
    replay = dict(days=days, acct={n: [round(v, 3) for v in rd[f"{n}|pnl"]] for n in ORDER})
    base = {"TREND-b5-h0.2", "LZNAIVE-k0.5-e8"}
    grid = [dict(name=n, base=n in base, trades=v["trades_per_day"], net=v["net"]["mean"], gross=v["gross"]["mean"],
                 gross_t=v["gross"]["t"], lowcost=v["net_lowcost"]["mean"], net2x=v["net_2x_cost"]["mean"], win=v["net"]["win"])
            for n, v in gs["variants"].items()]
    calib = {g: dict(auc=r["auc"], brier=r["brier"], n2=r["trig2pp"]["n"], hit2=r["trig2pp"]["hit"],
                     bp2=r["trig2pp"]["mean_bp"], n8=r["trig8pp"]["n"]) for g, r in cal["oos_test"].items()}
    variance = []
    for acc in accounts:
        r = rs["accounts"][acc["id"]]["all"]
        bt, bc, bg, bn = r["trades_per_day"], r["costs_per_day"], r["gross_per_day"], r["mean"]
        at, ac, ag, an_ = acc["trades"], acc["costs"], acc["gross"], acc["net"]
        bcpt = bc / bt if bt else 0.0
        acpt = ac / at if at else 0.0
        vol = -(at - bt) * bcpt                      # more trades at the expected cost per trade: unfavourable
        rate = -(acpt - bcpt) * at                   # dearer venue mix per trade: unfavourable
        edge = ag - bg                               # market / signal outcome vs the replay average
        resid = an_ - (bn + edge + vol + rate)       # open marks, cost on open legs, rounding
        variance.append(dict(id=acc["id"], budget=bn, actual=an_, edge=edge, volume=vol, rate=rate, resid=resid,
                             bt=bt, at=at, bcpt=bcpt, acpt=acpt))
    venues = ["CME futures", "FX spot", "LSE", "NYSE/Nasdaq ETF"]
    inc = {}
    for acc in accounts:
        tr = [t for t in trades if t["account"] == acc["id"]]
        g = {v: sum(t["pnl_gross"] for t in tr if t["venue"] == v) for v in venues}
        c = {v: sum(t["cost"] for t in tr if t["venue"] == v) for v in venues}
        inc[acc["id"]] = dict(gross=g, cost=c, gross_total=sum(g.values()), cost_total=sum(c.values()),
                              net=acc["net"], expected=acc["replay_mean"], closing_cash=acc["final"])
    import re   # the engine the run used, from its own log (the file may have changed since)
    started = re.findall(r"engine_sha=(\w+)", (OUT / "live" / "run.log").read_text(encoding="utf-8"))
    eng_sha = started[-1] if started else hashlib.sha256((HERE / "engine.py").read_bytes()).hexdigest()[:16]
    meta = dict(line=[f"live {hm(an['first_tick'])} → {hm(an['last_tick'])} KST · {an['ticks']} marks",
                      f"config {an['sha']} · engine {eng_sha}",
                      "yfinance 1-minute bars · CME ~10 min and LSE ~16 min delayed · fills at the last observed close",
                      "QUANTGEN costs per side: US ETFs 50 bp · LSE 50 bp as a proxy (QUANTGEN has no LSE row) · "
                      "futures 5 bp · FX 10 bp"])
    return dict(meta=meta, clock=clock, accounts=accounts, equity=eq, trades=trades, by_asset=list(by_asset.values()),
                risky=risky[:8], replay=replay, variance=variance, income=dict(venues=venues, acct=inc), grid=grid, calib=calib, controls=an["controls"],
                bench=dict(EW=an["benchmarks"]["EW_ALL_BH_ret"], SPY=an["benchmarks"]["SPY_BH_ret"],
                           n=len(an["benchmarks"]["per_asset"])), narrative=nar)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(OUT / "report" / "QUANTGEN_Paper_Run.html"))
    a = ap.parse_args()
    data = build()
    html = (HERE / "report_template.html").read_text(encoding="utf-8")
    html = html.replace("__DATA__", json.dumps(data, ensure_ascii=False, default=str).replace("</", "<\\/"))
    p = Path(a.out)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(html, encoding="utf-8")
    print("wrote", p, len(html) // 1024, "KB")


if __name__ == "__main__":
    main()
