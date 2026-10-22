"""Same-day replay: each live run's own code, replayed on that run's own day, against its live ledger.

The run reports place the live result in a replay distribution that leaves the live day out, so nothing
checked that the replay engine reproduces what live did. This replays the live day itself at the live tick
times, with the code that ran (rebuilt from the archived copies and checked against the hashes in run.log),
the frozen model and sigmas from PREREG.json/sigmas.json, and the frozen 5-minute bars. The gap per account,
live minus replay, is the replay's implementation shortfall: how far its 5-minute bars, feed-delay model and
fills sit from the 1-minute live loop.

    python -m paper_live.sameday            # writes out/replay_sameday and out_krx/replay_sameday

Known differences that stay: Run 1's first 15 minutes ran the pre-patch engine (AMENDMENTS.md); the replay
runs the patched one throughout.
"""
from __future__ import annotations

import hashlib
import json
import os
import pickle
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
BAK = "out/backup_pre_fix1_2026-10-18"
RUNS = {
    "run1": dict(profile="base", out="out", config="out/config_pre_krx.py.bak", engine="out/engine_pre_krx.py.bak",
                 replay=f"{BAK}/replay.py", config_sha="ffbdfc4d489bcaf2", engine_sha="1a47be9b1110a5b9"),
    "run2": dict(profile="krx", out="out_krx", config=f"{BAK}/config.py", engine=f"{BAK}/engine.py",
                 replay=f"{BAK}/replay.py", config_sha="fd50c3194378dc74", engine_sha="cb966c27356dd10f"),
}


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16]


def worker(job: Path):
    """Runs inside the rebuilt package (sys.path[0] = its parent): imports only the archived code."""
    spec = json.loads(job.read_text())
    sys.path[:0] = [spec["pkg_root"], str(ROOT)]
    import pandas as pd
    from paper_live import config as C, engine as E, replay as R

    assert Path(E.__file__).resolve().parent == Path(spec["pkg_root"], "paper_live").resolve(), E.__file__
    assert E.config_sha() == spec["config_sha"], "rebuilt config differs from the run's"
    bars = pickle.loads(Path(spec["bars"]).read_bytes())
    E.download = lambda tickers, **kw: {t: bars[t] for t in tickers if t in bars}
    E.trend_state = lambda s1: {}
    R.OUTR = Path(spec["out_dir"])
    live = Path(spec["live_dir"])
    closes = R.load()
    tabs = R.trend_table(closes)
    model = E.Model(coef=json.loads((live / "PREREG.json").read_text())["model"]["coef"])
    sigmas = json.loads((live / "sigmas.json").read_text())
    ticks = sorted({pd.Timestamp(json.loads(l)["t"]) for l in open(live / "equity.jsonl", encoding="utf-8")})
    day = ticks[0].normalize()
    lo, hi = day + R.WS - pd.Timedelta(days=6), ticks[-1] + pd.Timedelta(minutes=8)
    cd = {t: s[(s.index > lo) & (s.index <= hi)] for t, s in closes.items()}
    sink: dict = {}
    eng = R.ReplayEngine(model, sigmas, tabs, day.date(), sink)
    for now in ticks[:-1]:
        eng.step(now, cd)
    eng.step(ticks[-1], cd, final=True)
    res = {}
    for name, acc in eng.accounts.items():
        tr = [t for t in sink.get("trades.jsonl", []) if t["account"] == name]
        res[name] = dict(net=acc.cash - C.START_EQUITY, gross=sum(t["pnl_gross"] for t in tr), costs=acc.costs_paid,
                         trades=len(tr), open_left=len(acc.positions))
    for name in ("trades.jsonl", "fills.jsonl"):
        with open(R.OUTR / name, "w", encoding="utf-8") as f:
            for r in sink.get(name, []):
                f.write(json.dumps(r, default=str) + "\n")
    Path(spec["result"]).write_text(json.dumps(dict(accounts=res, ticks=len(ticks), first_tick=str(ticks[0]),
                                                    last_tick=str(ticks[-1])), default=str))


def entries_matched(live_trades: list, replay_trades: list, tol_min: float = 15.0) -> int:
    """Live entries with a replay entry on the same account, key and direction within tol_min minutes."""
    import pandas as pd

    pool = [(t["account"], t["key"], t["direction"], pd.Timestamp(t["entry_time"])) for t in replay_trades]
    n = 0
    for t in live_trades:
        a, k, d, e = t["account"], t["key"], t["direction"], pd.Timestamp(t["entry_time"])
        hit = next((p for p in pool if p[:3] == (a, k, d) and abs((p[3] - e).total_seconds()) <= tol_min * 60), None)
        if hit:
            pool.remove(hit)
            n += 1
    return n


def run(name: str) -> dict:
    spec = RUNS[name]
    for k in ("config", "engine"):
        got = _sha(HERE / spec[k])
        assert got == spec[f"{k}_sha"], f"{name}: archived {k} hashes to {got}, run.log says {spec[f'{k}_sha']}"
    out = HERE / spec["out"]
    live, out_dir = out / "live", out / "replay_sameday"
    out_dir.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, PAPER_PROFILE=spec["profile"])
    with tempfile.TemporaryDirectory() as tmp:
        pkg = Path(tmp, "paper_live")
        pkg.mkdir()
        (pkg / "__init__.py").write_text("")
        for k in ("config", "engine", "replay"):
            shutil.copy(HERE / spec[k], pkg / f"{k}.py")
        # the frozen bars, read through the current engine (sha-checked) for the archived code to use; replay and
        # grid may have frozen them mid-session, when most of the live day was not yet out
        window = json.loads((live / "PREREG.json").read_text())["window"]
        bars_name = f"replay_5m_60d_{window[0][:10].replace('-', '')}"
        saved = json.loads((out / "data" / "MANIFEST.json").read_text())[bars_name]["saved_utc"]
        if datetime.fromisoformat(saved) < datetime.fromisoformat(window[1]) + timedelta(minutes=30):
            raise SystemExit(f"{name}: {bars_name} was frozen at {saved}, before the live day's bars were all out "
                             f"(window end {window[1]} + 30 min); delete it and pull again after the session")
        load = subprocess.run([sys.executable, "-c", (
            "import pickle,sys; from paper_live import engine as E; "
            f"open(sys.argv[1],'wb').write(pickle.dumps(E.load_bars({bars_name!r})))"), str(Path(tmp, "bars.pkl"))],
            cwd=ROOT, env=env, check=True)
        job = Path(tmp, "job.json")
        job.write_text(json.dumps(dict(pkg_root=tmp, config_sha=spec["config_sha"], bars=str(Path(tmp, "bars.pkl")),
                                       out_dir=str(out_dir), live_dir=str(live), result=str(Path(tmp, "res.json")))))
        subprocess.run([sys.executable, str(HERE / "sameday.py"), "--worker", str(job)], cwd=tmp, env=env, check=True)
        rep = json.loads(Path(tmp, "res.json").read_text())
    an = json.loads((out / "analysis" / "summary.json").read_text())["accounts"]
    live_tr = [json.loads(l) for l in open(live / "trades.jsonl", encoding="utf-8")]
    rep_tr = [json.loads(l) for l in open(out_dir / "trades.jsonl", encoding="utf-8")]
    accounts = {}
    for n, r in rep["accounts"].items():
        lv = an[n]
        lt = [t for t in live_tr if t["account"] == n]
        accounts[n] = dict(
            live=dict(net=lv["net_pnl"], gross=lv["gross_pnl_closed"], costs=lv["costs"], trades=lv["closed_trades"]),
            replay=r, gap_net=lv["net_pnl"] - r["net"], gap_gross=lv["gross_pnl_closed"] - r["gross"],
            entries_matched=entries_matched(lt, [t for t in rep_tr if t["account"] == n]), live_entries=len(lt))
    summ = dict(run=name, profile=spec["profile"], code=dict(config_sha=spec["config_sha"], engine_sha=spec["engine_sha"]),
                bars=bars_name, ticks=rep["ticks"], first_tick=rep["first_tick"], last_tick=rep["last_tick"],
                accounts=accounts, note="gap = live - replay; entries matched on account, key and direction within 15 min")
    (out_dir / "summary.json").write_text(json.dumps(summ, indent=1, default=str))
    return summ


def main():
    for name in RUNS:
        s = run(name)
        print(f"\n{name} ({s['profile']}), {s['ticks']} live ticks {s['first_tick'][11:16]}-{s['last_tick'][11:16]} UTC")
        print(f"{'account':16s} {'live net':>9s} {'replay':>8s} {'gap':>7s} {'live gross':>10s} {'replay':>8s} "
              f"{'trades L/R':>10s} {'matched':>8s}")
        for n, a in s["accounts"].items():
            print(f"{n:16s} {a['live']['net']:+9.2f} {a['replay']['net']:+8.2f} {a['gap_net']:+7.2f} "
                  f"{a['live']['gross']:+10.2f} {a['replay']['gross']:+8.2f} "
                  f"{a['live']['trades']:>4d}/{a['replay']['trades']:<4d} {a['entries_matched']:>4d}/{a['live_entries']}")


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--worker":
        worker(Path(sys.argv[2]))
    else:
        main()
