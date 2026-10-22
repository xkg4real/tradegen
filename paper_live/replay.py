"""Replay backtest: the live accounts (config.ACCOUNTS) on every recent session, same clock window.

Each session starts fresh $500 accounts and flattens at window end, so the output is a
distribution of 5-hour session P&Ls to place the live result in. Bars are 5-minute Yahoo bars
re-stamped at bar end plus the live feed delay of their venue (CME 10 min, LSE 16 min, FX/US 1 min),
so fills see what the live loop would have seen. The logistic uses model_train_only.json, so its
accounts (QG-TACTICAL, LAZYOWEN-CAL) are out-of-sample only on the last CALIB_TEST_DAYS sessions.
Known deviations from live: 5-minute instead of 1-minute closes; the live run's GARCH sigma is used on
every past day (sizing, stops and the cost gate); the C3 trend state is computed once over the full history.

    python -m paper_live.replay
"""
from __future__ import annotations

import json
import time

import numpy as np
import pandas as pd

from paper_live import config as C
from paper_live import engine as E

DELAY_MIN = {"CME": 10, "LSE": 16, "FX": 1, "US": 1, "KRX": 20}
WS = pd.Timedelta(hours=C.WINDOW_START_UTC.hour, minutes=C.WINDOW_START_UTC.minute)
WE = pd.Timedelta(hours=C.WINDOW_END_UTC.hour, minutes=C.WINDOW_END_UTC.minute)
ANCHOR = next(iter(C.UNIVERSE))   # a day counts only if its first instrument traded through the window

OUTR = E.OUT / "replay"


def venue(t: str) -> str:
    if t in C.UNIVERSE:
        return C.UNIVERSE[t]["venue"]
    if t in C.INVERSE_ETFS:
        return "KRX" if t.endswith(".KS") else "US"
    return "FX"


def load(snapshot: str | None = None) -> dict[str, pd.Series]:
    raw = E.download(E.all_tickers(), period="60d", interval="5m", snapshot=snapshot or f"replay_5m_60d_{E.run_tag()}")
    out = {}
    for t, s in raw.items():
        s = s.copy()
        s.index = s.index + pd.Timedelta(minutes=5 + DELAY_MIN[venue(t)])
        out[t] = s
    return out


def trend_table(closes: dict[str, pd.Series]) -> dict[str, pd.DataFrame]:
    from core.quant import strategies as S

    tabs = {}
    for key in C.UNIVERSE:
        s = closes.get(key)
        if s is None:
            continue
        s5 = E.five_min(s)
        px = s5.to_numpy(float)
        on = np.asarray(S.crypto_trend(px)).reshape(len(px), -1)[:, 0]
        votes = [np.sign(s5 - s5.shift(k)) for k in (7, 14, 21, 28)]
        votes += [np.sign(s5 - s5.rolling(n).mean()) for n in (10, 20, 50, 100, 200)]
        vote = pd.concat(votes, axis=1).mean(axis=1)
        tabs[key] = pd.DataFrame(dict(on=on, vote=vote.to_numpy(), n=np.arange(1, len(px) + 1)), index=s5.index)
    return tabs


class ReplayEngine(E.Engine):
    def __init__(self, model, sigmas, trend_tabs, day, sink):
        self.trend_tabs, self.day, self.sink = trend_tabs, str(day), sink
        super().__init__(model, sigmas, OUTR / "_scratch", mode="replay")
        self.accounts = {a["name"]: E.make_account(a) for a in C.ACCOUNTS}
        self.last_decision = {a["name"]: None for a in C.ACCOUNTS}

    def _append(self, name, row):
        if name in ("fills.jsonl", "trades.jsonl", "equity.jsonl"):
            self.sink.setdefault(name, []).append(dict(row, day=self.day))
        elif name == "decisions.jsonl" and row.get("verdict") == "CANDIDATE":
            self.sink.setdefault(name, []).append(dict(row, day=self.day))

    def _save_state(self):
        pass

    def signals(self, closes, now):
        sig = super().signals(closes, now)
        for key, row in sig.items():
            if "bars_last_hour" in row:          # 5-minute replay bars -> 1-minute-equivalent print count
                row["bars_last_hour"] *= 5
            tab = self.trend_tabs.get(key)
            if tab is None:
                continue
            tab = tab[tab.index <= now]
            if len(tab) < C.TREND["min_bars"]:
                row.update(trend_ok=False)
                continue
            row.update(trend_ok=True, trend_on=float(tab.on.iloc[-1]), trend_vote=float(tab.vote.iloc[-1]))
        return sig


def bench(closes, day0: pd.Timestamp, end: pd.Timestamp) -> dict:
    """Buy-and-hold benchmarks over the same window (no costs)."""
    out = {}
    rets = {}
    for key in C.UNIVERSE:
        s = closes.get(key)
        if s is None:
            continue
        o, c = E.session_bounds(venue(key), day0)
        start = max(day0 + WS + pd.Timedelta(minutes=3), o)
        a = s[(s.index >= start) & (s.index <= end)]
        if len(a) < 3:
            continue
        r = a.iloc[-1] / a.iloc[0] - 1
        if C.UNIVERSE[key].get("usd_base"):
            r = 1 - a.iloc[0] / a.iloc[-1]
        rets[key] = float(r)
    out["EW_ALL_BH"] = float(np.mean(list(rets.values()))) if rets else float("nan")
    out["SPY_BH"] = rets.get("SPY", float("nan"))
    out["ES_BH"] = rets.get("ES=F", float("nan"))
    out["per_asset"] = rets
    return out


def main():
    """REPLAY_HOLDOUT=1 replays the sessions after HYPOTHESES['frozen'] instead (a fresh pull, frozen as
    holdout_5m_60d_<today>), into out*/replay_holdout/ for verdict.py's H2 test.

    TRADEGEN copy: refused. The H2 holdout is QUANTGEN's pre-registered one look (readout about 2026-11-03, from
    its tag); replaying it here would be an early second look at the same sessions."""
    import os
    t0 = time.time()
    holdout = bool(os.environ.get("REPLAY_HOLDOUT"))
    if holdout:
        raise SystemExit("REPLAY_HOLDOUT refused in TRADEGEN: the H2 holdout readout is QUANTGEN's one look")
    out_dir = E.OUT / "replay_holdout" if holdout else OUTR
    out_dir.mkdir(parents=True, exist_ok=True)
    OUTR.mkdir(parents=True, exist_ok=True)
    E.trend_state = lambda s1: {}          # replaced by the precomputed table in ReplayEngine.signals
    frozen_rec = None
    if holdout:
        if os.environ.get("REPLAY_LAST"):
            raise SystemExit("REPLAY_LAST would drop holdout sessions; the pre-registered sample is fixed")
        fp = E.OUT / "HYPOTHESES_frozen.json"
        if not fp.exists():
            raise SystemExit(f"no {fp}: the hypotheses were never frozen, so there is no holdout to replay")
        frozen_rec = json.loads(fp.read_text())
        changed = [a["name"] for a in C.ACCOUNTS
                   if a["name"] in frozen_rec["digests"] and E.rule_digest(a) != frozen_rec["digests"][a["name"]]]
        if changed:   # replaying would overwrite a valid result with an invalid one
            raise SystemExit(f"{changed} differ from the frozen rule; restore paper_live/engine.py and config.py "
                             f"from {E.OUT / 'frozen_rule'} before the holdout replay")
    snap = f"holdout_5m_60d_{pd.Timestamp.now(tz='UTC'):%Y%m%d}" if holdout else None
    closes = load(snap)
    tabs = trend_table(closes)
    sig_path = E.OUT / "live" / "sigmas.json"
    sigmas = frozen_rec["sigmas"] if holdout else json.loads(sig_path.read_text())   # the gate's sigma is frozen
    model = E.Model.load(E.OUT / "model_train_only.json")
    cal = json.loads((E.OUT / "calibration.json").read_text())
    test_from = pd.Timestamp(cal["test_dates"].split("..")[0]).date()
    es = closes[ANCHOR]
    days = sorted({d for d in es.index.normalize().date if pd.Timestamp(d).weekday() < 5})
    first = max(s.index[0] for s in closes.values()).date()   # every series must have history
    frozen = pd.Timestamp(C.HYPOTHESES["frozen"]).date()
    days = [d for d in days if first < d and (d > frozen if holdout else d < C.WINDOW_START_UTC.date())]
    if holdout:
        if first > frozen - pd.Timedelta(days=6):
            raise SystemExit(f"this pull starts {first}: it lacks the 6-day lookback of the first holdout session "
                             f"after {frozen} (Yahoo keeps ~60 days of 5-minute bars)")
        saved = pd.Timestamp(json.loads((E.DATA / "MANIFEST.json").read_text())[snap]["saved_utc"])             if (E.DATA / f"{snap}.csv.gz").exists() else pd.Timestamp.now(tz="UTC")
        # a session counts only if its delayed bars were all out when the pull was frozen
        days = [d for d in days if pd.Timestamp(d, tz="UTC") + WE + pd.Timedelta(minutes=30) <= saved]
    if os.environ.get("REPLAY_LAST"):
        days = days[-int(os.environ["REPLAY_LAST"]):]
    if not days:
        print(f"no sessions to replay{' after ' + str(frozen) if holdout else ''}")
        return
    E.register_trials(C.ACCOUNTS, span=("2026-07-01", "9999-12-31"), script="paper_live/replay.py")   # one span at every site
    sink, rows = {}, []
    for d in days:
        day0 = pd.Timestamp(d, tz="UTC")
        lo, hi = day0 + WS - pd.Timedelta(days=6), day0 + WE + pd.Timedelta(minutes=8)
        cd = {t: s[(s.index > lo) & (s.index <= hi)] for t, s in closes.items()}
        if len(cd.get(ANCHOR, [])) == 0 or cd[ANCHOR].index[-1] < day0 + WE - pd.Timedelta(minutes=42):
            continue
        eng = ReplayEngine(model, sigmas, tabs, d, sink)
        times = pd.date_range(day0 + WS + pd.Timedelta(minutes=3), day0 + WE - pd.Timedelta(minutes=2), freq="5min")
        for now in times:
            eng.step(now, cd)
        end = day0 + WE
        eng.step(end, cd, final=True)
        b = bench(cd, day0, end)
        row = dict(day=str(d), oos_logit=d >= test_from, **{k: v for k, v in b.items() if k != "per_asset"})
        for name, acc in eng.accounts.items():
            tr = [t for t in sink.get("trades.jsonl", []) if t["day"] == str(d) and t["account"] == name]
            row[f"{name}|pnl"] = acc.cash - C.START_EQUITY
            row[f"{name}|gross"] = sum(t["pnl_gross"] for t in tr)
            row[f"{name}|costs"] = acc.costs_paid
            row[f"{name}|trades"] = len(tr)
            row[f"{name}|halted"] = acc.halted
            assert not acc.positions, f"{name} not flat on {d}"
        rows.append(row)
        print(d, {k.split('|')[0]: round(v, 2) for k, v in row.items() if k.endswith('|pnl')}, flush=True)
    df = pd.DataFrame(rows)
    df.to_csv(out_dir / "days.csv", index=False)
    for name in ("trades.jsonl", "fills.jsonl"):
        with open(out_dir / name, "w", encoding="utf-8") as f:
            for r in sink.get(name, []):
                f.write(json.dumps(r, default=str) + "\n")
    summ = dict(n_days=int(len(df)), first=str(df.day.min()), last=str(df.day.max()), test_from=str(test_from),
                seconds=round(time.time() - t0, 1), sha=E.config_sha(), holdout=holdout,
                hypotheses_frozen=C.HYPOTHESES["frozen"], snapshot=snap,
                rule_digest={a["name"]: E.rule_digest(a) for a in C.ACCOUNTS}, accounts={})
    for a in C.ACCOUNTS:
        n = a["name"]
        for subset, m in (("all", np.ones(len(df), bool)), ("oos_logit", df.oos_logit.to_numpy())):
            x = df.loc[m, f"{n}|pnl"].to_numpy()
            if len(x) == 0:
                continue
            summ["accounts"].setdefault(n, {})[subset] = dict(
                days=int(len(x)), mean=float(x.mean()), median=float(np.median(x)), sd=float(x.std(ddof=1)) if len(x) > 1 else None,
                t=float(x.mean() / (x.std(ddof=1) / np.sqrt(len(x)))) if len(x) > 2 and x.std() > 0 else None,
                win_days=float((x > 0).mean()), flat_days=float((x == 0).mean()), worst=float(x.min()), best=float(x.max()),
                trades_per_day=float(df.loc[m, f"{n}|trades"].mean()), costs_per_day=float(df.loc[m, f"{n}|costs"].mean()),
                gross_per_day=float(df.loc[m, f"{n}|gross"].mean()))
    for bname in ("EW_ALL_BH", "SPY_BH", "ES_BH"):
        x = df[bname].dropna().to_numpy() * C.START_EQUITY
        if len(x) < 2:
            continue  # e.g. no SPY in the KRX universe
        summ.setdefault("benchmarks_usd_on_500", {})[bname] = dict(mean=float(x.mean()), sd=float(x.std(ddof=1)), worst=float(x.min()), best=float(x.max()))
    from paper_live import power
    summ["power"] = power.lines(df, [a["name"] for a in C.ACCOUNTS])
    for n, pl in summ["power"].items():
        print(power.describe(n, pl))
    (out_dir / "summary.json").write_text(json.dumps(summ, indent=1, default=str))
    print(json.dumps(summ, indent=1, default=str))


if __name__ == "__main__":
    main()
