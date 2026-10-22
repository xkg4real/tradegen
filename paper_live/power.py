"""Power line for session P&L: the smallest effect a set of sessions could have detected.

"No edge" means nothing without it. Two five-hour sessions have about a 9-13% chance of detecting even a
large edge; the replays bound how large an edge could have been missed. Same convention as QUANTGEN's cards
(core.quant.gate_stats): one-sided alpha 0.10 at 80% power, MDE = 2.1232 x SE.

    python -m paper_live.power      # power lines for the frozen replay and grid days.csv -> out*/power.json
"""
from __future__ import annotations

import json
import math

import numpy as np
import pandas as pd
import scipy.stats as sps

from core.quant.gate_stats import MDE_FACTOR
from core.quant.validate import TRADING_DAYS, newey_west_t

EDGE_USD = 0.50          # a reference gross edge per session on $500 (10 bp a session, about 25% a year)


def power_line(x) -> dict:
    """Per-session P&L series -> mean, sd, iid and Newey-West t, the $ edge detectable at 80% power, and the
    sessions needed for a $0.50 edge and for an annual Sharpe of 1."""
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    n = int(x.size)
    sd = float(x.std(ddof=1)) if n > 1 else float("nan")
    ok = n > 1 and sd > 0
    return dict(
        n=n, mean=float(x.mean()) if n else float("nan"), sd=sd,
        t=float(x.mean() / (sd / math.sqrt(n))) if ok else None,
        t_nw5=newey_west_t(x, 5) if ok else None,
        mde80_usd=float(MDE_FACTOR * sd / math.sqrt(n)) if ok else None,
        sessions_for_0p50=max(2, int(math.ceil((MDE_FACTOR * sd / EDGE_USD) ** 2))) if ok else None,
        upper90_usd=float(x.mean() + sps.t.ppf(0.90, n - 1) * sd / math.sqrt(n)) if ok else None,
        sessions_for_sr1=int(math.ceil(MDE_FACTOR ** 2 * TRADING_DAYS)),
    )


def lines(df: pd.DataFrame, names) -> dict:
    """Gross and net power lines for every `name|gross` / `name|pnl` column pair in a replay or grid days.csv."""
    return {n: dict(gross=power_line(df[f"{n}|gross"]), net=power_line(df[f"{n}|pnl"]))
            for n in names if f"{n}|gross" in df and f"{n}|pnl" in df}


def describe(name: str, pl: dict) -> str:
    g = pl["gross"]
    if g["mde80_usd"] is None:
        return f"{name}: no gross variation over {g['n']} sessions (it barely traded)"
    return (f"{name}: over {g['n']} sessions a gross edge of ${g['mde80_usd']:.2f} a session would have been "
            f"detected with 80% power (one-sided alpha 0.10); the upper 90% bound on the gross mean is "
            f"${g['upper90_usd']:+.2f}; a $0.50 edge needs {g['sessions_for_0p50']} sessions, an annual Sharpe of 1 "
            f"about {g['sessions_for_sr1']:,}")


def main():
    from paper_live import engine as E

    out = {}
    for kind in ("replay", "grid"):
        p = E.OUT / kind / "days.csv"
        if not p.exists():
            continue
        df = pd.read_csv(p)
        names = sorted({c.split("|")[0] for c in df.columns if "|" in c})
        out[kind] = lines(df, names)
        for n, pl in out[kind].items():
            print(f"[{kind}] {describe(n, pl)}")
    (E.OUT / "power.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
