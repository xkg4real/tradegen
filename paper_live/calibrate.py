"""Fit the shared intraday probability model on ~60 days of 5-minute bars and score it out of sample.

Train = all sessions except the last CALIB_TEST_DAYS; test = those last sessions (never seen in the fit).
The live model is then refit on the full history (pre-registered). Writes out/model.json and
out/calibration.json.  Run from the QUANTGEN root:  python -m paper_live.calibrate
"""
from __future__ import annotations

import json
import math
import time

import numpy as np
import pandas as pd

from paper_live import config as C
from paper_live.engine import OUT, Model, config_sha, download, ewma_sigma5, fit_logit, run_tag, sigmoid


def panel() -> pd.DataFrame:
    raw = download(list(C.UNIVERSE), period="60d", interval="5m", snapshot=f"calibrate_5m_60d_{run_tag()}")
    rows = []
    for key, s in raw.items():
        s = s.copy()
        s.index = s.index + pd.Timedelta(minutes=5)          # stamp at bar END
        sig = ewma_sigma5(s)
        idx = s.index
        def shifted(mins):
            return s.reindex(idx + pd.Timedelta(minutes=mins), method="ffill",
                             tolerance=pd.Timedelta(minutes=10)).to_numpy()
        p0 = s.to_numpy()
        p60b, p15b, p60f = shifted(-60), shifted(-15), shifted(60)
        df = pd.DataFrame(dict(t=idx, key=key, group=C.UNIVERSE[key]["group"], px=p0, sigma5=sig.to_numpy()))
        with np.errstate(all="ignore"):
            df["z60"] = np.clip(np.log(p0 / p60b) / (df.sigma5 * math.sqrt(12)), -4, 4)
            df["z15"] = np.clip(np.log(p0 / p15b) / (df.sigma5 * math.sqrt(3)), -4, 4)
            df["fwd"] = np.log(p60f / p0)
        rows.append(df)
    d = pd.concat(rows, ignore_index=True).replace([np.inf, -np.inf], np.nan).dropna()
    d = d[d.fwd != 0]
    d["y"] = (d.fwd > 0).astype(float)
    d["date"] = d.t.dt.date
    d["in_window_hours"] = d.t.dt.hour.between(11, 16)
    return d


def auc(y, p):
    order = np.argsort(p)
    r = np.empty(len(p))
    r[order] = np.arange(1, len(p) + 1)
    n1 = y.sum(); n0 = len(y) - n1
    return float((r[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)) if n1 and n0 else float("nan")


def score(d: pd.DataFrame, coef: dict) -> dict:
    out = {}
    for g, b in coef.items():
        x = d[d.group == g]
        if len(x) == 0:
            continue
        p = np.clip(sigmoid(b[0] + b[1] * x.z60 + b[2] * x.z15), *C.P_CLIP).to_numpy()
        y = x.y.to_numpy()
        # non-overlapping hourly sample for honest error bars on the trigger subsets
        hourly = x.t.dt.minute.to_numpy() == 0
        res = dict(n=int(len(x)), auc=auc(y, p), brier=float(np.mean((p - y) ** 2)), brier_coinflip=0.25,
                   mean_p=float(p.mean()), base_rate=float(y.mean()))
        for thr in (0.02, 0.08):
            m = np.abs(p - 0.5) >= thr
            mh = m & hourly
            side = np.sign(p - 0.5)
            pnl = side * x.fwd.to_numpy()
            res[f"trig{int(thr * 100)}pp"] = dict(
                n=int(m.sum()), n_hourly=int(mh.sum()),
                hit=float((pnl[m] > 0).mean()) if m.any() else None,
                mean_bp=float(pnl[m].mean() * 1e4) if m.any() else None,
                se_bp_hourly=float(pnl[mh].std(ddof=1) / math.sqrt(mh.sum()) * 1e4) if mh.sum() > 2 else None,
                mean_bp_hourly=float(pnl[mh].mean() * 1e4) if mh.any() else None)
        out[g] = res
    return out


def main():
    t0 = time.time()
    d = panel()
    dates = sorted(d.date.unique())
    test_dates = set(dates[-C.CALIB_TEST_DAYS:])
    tr, te = d[~d.date.isin(test_dates)], d[d.date.isin(test_dates)]
    coef_train, coef_full, se_full = {}, {}, {}
    for g in C.GROUPS:
        x = tr[tr.group == g]
        b, _ = fit_logit(x[["z60", "z15"]].to_numpy(), x.y.to_numpy(), intercept=False)
        coef_train[g] = [0.0] + [float(v) for v in b[1:]]
        x = d[d.group == g]
        b, se = fit_logit(x[["z60", "z15"]].to_numpy(), x.y.to_numpy(), intercept=False)
        coef_full[g] = [0.0] + [float(v) for v in b[1:]]
        se_full[g] = [0.0] + [float(v) for v in se[1:]]
    rep = dict(
        sha=config_sha(), built_utc=pd.Timestamp.now(tz="UTC").isoformat(), seconds=round(time.time() - t0, 1),
        n_rows=int(len(d)), first=str(dates[0]), last=str(dates[-1]),
        train_dates=f"{dates[0]}..{dates[-C.CALIB_TEST_DAYS - 1]}", test_dates=f"{min(test_dates)}..{max(test_dates)}",
        note=("SEs are naive (overlapping 60m targets on a 5m grid inflate t-stats ~3.5x); "
              "use the hourly non-overlapping se for the trigger subsets"),
        coef_train=coef_train, coef_full=coef_full, se_full_naive=se_full,
        oos_test=score(te, coef_train), oos_test_window_hours=score(te[te.in_window_hours], coef_train),
        in_sample_train=score(tr, coef_train),
    )
    (OUT / "calibration.json").write_text(json.dumps(rep, indent=1, default=str))
    Model(coef_full).save(OUT / "model.json", dict(sha=config_sha(), fitted_on=f"{dates[0]}..{dates[-1]}"))
    Model(coef_train).save(OUT / "model_train_only.json", dict(sha=config_sha(), fitted_on=rep["train_dates"]))
    print(json.dumps({k: rep[k] for k in ("n_rows", "train_dates", "test_dates", "coef_full", "se_full_naive")}, indent=1))
    for g, r in rep["oos_test"].items():
        print(g, "OOS auc=%.3f brier=%.4f" % (r["auc"], r["brier"]), "trig2:", r["trig2pp"], "trig8:", r["trig8pp"])


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    main()
