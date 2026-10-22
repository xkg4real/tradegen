"""Apply the pre-registered hypotheses to the evidence on disk, from their frozen copy, mechanically.

    python -m paper_live.verdict --freeze    # once, before the first holdout session: out*/HYPOTHESES_frozen.json
    python -m paper_live.verdict             # PAPER_PROFILE selects base/krx; writes out*/verdict.json

The frozen file holds config.HYPOTHESES and each account's rule digest (engine.rule_digest: its effective
settings plus engine.py). Every threshold below comes from it; the run refuses if config.HYPOTHESES has changed
since, and H2 is invalid if the holdout replay ran a different rule than the one frozen.

H1 fidelity   out*/replay_sameday/summary.json for the run whose PREREG.json is in out*/live: |live - same-day
              replay| per account that traded, against max(0.5 x the run's replay session sd, the $ floor).
              Exploratory when that PREREG predates the hypotheses (Runs 1 and 2).
H2 cost gate  out*/replay_holdout (REPLAY_HOLDOUT=1 python -m paper_live.replay): exactly the first `sessions`
              exchange sessions after `frozen`; a missing one makes it incomplete, it never shifts the sample.
H3 edge       power lines only.
"""
from __future__ import annotations

import json
import sys
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import scipy.stats as sps

from core.quant.validate import newey_west_t
from paper_live import config as C
from paper_live import power

GATED, BASE = "LAZYOWEN-NAIVE-G2", "LAZYOWEN-NAIVE"
FROZEN_FILE = "HYPOTHESES_frozen.json"


def _norm(x):
    return json.loads(json.dumps(x, sort_keys=True, default=str))


def freeze(out: Path, now: pd.Timestamp | None = None) -> dict:
    """Write the hypotheses, the rule digests and the live sigmas the gate uses once, and byte copies of
    engine.py and config.py to out*/frozen_rule/; an identical re-freeze is a no-op, a different one refused,
    and nothing is frozen after the `frozen` date (holdout sessions may already have been seen)."""
    import shutil
    from paper_live import engine as E

    rec = dict(profile=C.PROFILE, hypotheses=_norm(C.HYPOTHESES),
               digests={a["name"]: E.rule_digest(a) for a in C.ACCOUNTS},
               sigmas=json.loads((out / "live" / "sigmas.json").read_text()))
    p = out / FROZEN_FILE
    if p.exists():
        old = json.loads(p.read_text())
        if {k: old.get(k) for k in rec} != rec:
            raise SystemExit(f"{p} already holds different hypotheses or rules; a frozen record is not rewritten")
        return old
    now = now if now is not None else pd.Timestamp.now(tz="UTC")
    if now.date().isoformat() > C.HYPOTHESES["frozen"]:
        raise SystemExit(f"too late to freeze: it is after {C.HYPOTHESES['frozen']}, and holdout sessions may "
                         f"already have been seen")
    rec["frozen_utc"] = now.isoformat(timespec="seconds")
    rule = out / "frozen_rule"
    rule.mkdir(parents=True, exist_ok=True)
    for f in ("engine.py", "config.py"):
        shutil.copy2(Path(E.__file__).parent / f, rule / f)
    p.write_text(json.dumps(rec, indent=1))
    return rec


def holdout_sessions(frozen: dict) -> list[str]:
    """The first `sessions` trading days after `frozen` on the anchor venue's exchange calendar (US for the
    base profile's CME anchor), weekends and holidays skipped."""
    from core import calendars
    venue = C.UNIVERSE[next(iter(C.UNIVERSE))]["venue"]
    market = C.MARKET_FOR_VENUE.get(venue, "US")
    H = frozen["hypotheses"]
    d, out = date.fromisoformat(H["frozen"]), []
    while len(out) < H["H2_cost_gate"]["sessions"]:
        d += timedelta(days=1)
        if d.weekday() < 5 and calendars.is_trading_day(market, d) is not False:
            out.append(d.isoformat())
    return out


def h1_fidelity(out: Path, frozen: dict) -> dict:
    H = frozen["hypotheses"]["H1_fidelity"]
    p = out / "replay_sameday" / "summary.json"
    pre_p = out / "live" / "PREREG.json"
    if not p.exists() or not pre_p.exists():
        return dict(status="no same-day replay", how="python -m paper_live.sameday")
    summ, pre = json.loads(p.read_text()), json.loads(pre_p.read_text())
    if str(summ.get("first_tick", ""))[:10] != str(pre["window"][0])[:10]:
        return dict(status="no same-day replay for this run", run=summ.get("run"))
    rs = json.loads((out / "replay" / "summary.json").read_text())
    gap_days = (date.fromisoformat(str(pre["window"][0])[:10]) - date.fromisoformat(str(rs["last"])[:10])).days
    if not 0 < gap_days <= 10:          # the sd must come from this run's own pre-window replay
        return dict(status="undefined: out*/replay is not this run's pre-window replay", run=summ.get("run"),
                    replay_last=rs["last"])
    rd = pd.read_csv(out / "replay" / "days.csv")
    accounts, undefined = {}, []
    for n, a in summ["accounts"].items():
        if a["live"]["trades"] == 0 and a["replay"]["trades"] == 0:
            continue                                   # the rule covers accounts that traded
        if f"{n}|pnl" not in rd:
            undefined.append(n)
            continue
        sd = float(rd[f"{n}|pnl"].std(ddof=1))
        limit = max(0.5 * sd if sd > 0 else 0.0, H["gap_floor_usd"])
        accounts[n] = dict(gap=a["gap_net"], replay_sd=sd, gap_in_sd=abs(a["gap_net"]) / sd if sd > 0 else None,
                           limit=limit, holds=bool(abs(a["gap_net"]) <= limit))
    if undefined:
        status = f"undefined: no replay sd for {', '.join(undefined)}"
    elif not accounts:
        status = "untestable: no account traded"
    else:
        status = "holds" if all(v["holds"] for v in accounts.values()) else "fails"
    if "hypotheses" not in pre:
        status = f"exploratory: {status} (run predates the hypotheses)"
    return dict(status=status, run=summ.get("run"), accounts=accounts)


def h2_cost_gate(out: Path, frozen: dict, today: date | None = None) -> dict:
    H = frozen["hypotheses"]
    expected = holdout_sessions(frozen)
    today = today or pd.Timestamp.now(tz="UTC").date()
    p = out / "replay_holdout" / "days.csv"
    df = pd.read_csv(p) if p.exists() else pd.DataFrame(columns=["day"])
    have = set(df.day.astype(str))
    missing = [d for d in expected if d not in have]
    if missing:
        return dict(status="pending" if today <= date.fromisoformat(expected[-1]) else "incomplete",
                    sessions=len(expected) - len(missing),
                    planned=len(expected), missing=missing, expected=expected,
                    how="REPLAY_HOLDOUT=1 python -m paper_live.replay after the last expected session")
    summ = json.loads((out / "replay_holdout" / "summary.json").read_text())
    ran = summ.get("rule_digest", {})
    if any(ran.get(n) != frozen["digests"].get(n) for n in (GATED, BASE)):
        return dict(status="invalid: the holdout replay ran a different rule than the one frozen",
                    frozen={n: frozen["digests"].get(n) for n in (GATED, BASE)}, ran={n: ran.get(n) for n in (GATED, BASE)})
    df = df[df.day.astype(str).isin(expected)].sort_values("day")
    d = (df[f"{GATED}|pnl"] - df[f"{BASE}|pnl"]).to_numpy(float)
    r = sps.ttest_1samp(d, 0.0, alternative="greater")
    pval = float(r.pvalue)
    return dict(status="confirmed" if pval <= H["alpha_one_sided"] else "not confirmed", sessions=len(d),
                days=[expected[0], expected[-1]], mean_diff=float(d.mean()), t=float(r.statistic), p_one_sided=pval,
                t_nw5_reported=newey_west_t(d, 5), gated_won=int((d > 0).sum()), snapshot=summ.get("snapshot"))


def h3_edge(out: Path) -> dict:
    p = out / "replay" / "days.csv"
    if not p.exists():
        return dict(status="no replay")
    df = pd.read_csv(p)
    lines = power.lines(df, sorted({c.split("|")[0] for c in df.columns if c.endswith("|gross")}))
    return dict(status="power line only (pre-registered: no edge test)", power=lines,
                plain=[power.describe(n, pl) for n, pl in lines.items()])


def main():
    from paper_live import engine as E

    if "--freeze" in sys.argv:
        rec = freeze(E.OUT)
        print(f"frozen {E.OUT / FROZEN_FILE} at {rec['frozen_utc']}: {len(rec['digests'])} rule digests")
        return
    p = E.OUT / FROZEN_FILE
    if not p.exists():
        raise SystemExit(f"no {p}: freeze the hypotheses first (python -m paper_live.verdict --freeze)")
    frozen = json.loads(p.read_text())
    if frozen["frozen_utc"][:10] > frozen["hypotheses"]["frozen"]:
        raise SystemExit("the frozen record was written after the date it claims; it is not a pre-registration")
    if _norm(C.HYPOTHESES) != frozen["hypotheses"]:
        raise SystemExit("config.HYPOTHESES has changed since the freeze; the frozen copy is the pre-registration")
    v = dict(profile=C.PROFILE, frozen_file=str(p), H1=h1_fidelity(E.OUT, frozen), H2=h2_cost_gate(E.OUT, frozen),
             H3=h3_edge(E.OUT))
    (E.OUT / "verdict.json").write_text(json.dumps(v, indent=1, default=str))
    print(f"H1 fidelity: {v['H1']['status']}")
    for n, a in v["H1"].get("accounts", {}).items():
        print(f"   {n}: gap {a['gap']:+.2f}, limit ${a['limit']:.2f}{'' if a['holds'] else '  FAILS'}")
    h2 = v["H2"]
    print(f"H2 cost gate ({C.PROFILE}): {h2['status']}"
          + (f" ({h2['sessions']} of {h2['planned']} sessions)" if "planned" in h2 else "")
          + (f"; mean {h2['mean_diff']:+.2f} a session, p {h2['p_one_sided']:.3f}" if "p_one_sided" in h2 else ""))
    print(f"H3 edge: {v['H3']['status']}")
    for line in v["H3"].get("plain", []):
        print("   " + line)


if __name__ == "__main__":
    main()
