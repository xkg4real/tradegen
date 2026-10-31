"""The D13 replay of S_C3 from the committed study cache (odds plan Task 17; spec 7.2 "replay"; O9, Q9).

Unsigned: it reads the cached Upbit KRW-BTC closes and the S_C3 card, re-runs the study's own three steps
(`strategies.pnl_matrix`, `validate.walk_forward`, `validate.score_strategy`) and returns plain data. The signed core
(`core.odds.models.verify_replay`) checks every input, digest and statistic against its pins; any mismatch is
CARD_NOT_REPRODUCED. No network, no write, no clock; the study runner `docs/asset_expansion_study.py` is never
imported, and no live pull is made (the cache's last row was a running price, O9).
"""
from __future__ import annotations

import csv
import functools
import hashlib
import json
from pathlib import Path

import numpy as np

from core.odds import plan
from core.quant import strategies, validate

REPO = Path(__file__).resolve().parents[2]
CACHE = REPO / "docs/asset_expansion/cache/upbit_KRW-BTC.csv"
CARD = REPO / "docs/asset_expansion/cards/S_C3_crypto_trend_krwbtc.json"
RESULTS = REPO / "docs/asset_expansion/results.csv"
LOOKBACKS = (7, 14, 21, 28)
MAS = (10, 20, 50, 100, 200)
DOMAIN = {"hysteresis": (0.0, 0.889)}
_SYMBOL = "KRW-BTC"
_SOURCE = "UPBIT"
_HEADER = ["", "upbit_KRW-BTC"]


def replay_s_c3(*, lookbacks=LOOKBACKS, mas=MAS, embargo: int | None = None) -> plan.ReplayInput:
    """Replay S_C3 on the cached closes with the card's own grid, cost, protocol, trials, seed and embargo.
    `lookbacks`, `mas` and `embargo` exist so a test can change one constant and watch the core refuse it; the CLI
    never passes them. About 5 s (score_strategy's CSCV is most of it)."""
    with CACHE.open(encoding="utf-8", newline="") as fh:
        rows = list(csv.reader(fh))
    if not rows or rows[0] != _HEADER:
        raise ValueError(f"replay: {CACHE.name} starts with {rows[:1]}, expected {_HEADER}")
    dates = tuple(r[0] for r in rows[1:])
    close = tuple(float(r[1]) for r in rows[1:])
    card_bytes = CARD.read_bytes()
    card = json.loads(card_bytes)
    rules, protocol, grid = card["rules"], card["protocol"], card["rules"]["grid"]
    used_embargo = rules["embargo"] if embargo is None else embargo
    fn = functools.partial(strategies.crypto_trend, lookbacks=tuple(lookbacks), mas=tuple(mas))
    px = np.asarray(close, dtype=float)[:, None]
    m, m_stress, turnover = strategies.pnl_matrix(px, fn, grid, cost_bps=rules["cost_bps_per_side"])
    wf = validate.walk_forward(m, dates[1:], turnover=turnover, pnl_stress=m_stress, w_is=protocol["w_is"],
                               w_oos=protocol["w_oos"], min_is=protocol["min_is"], embargo=used_embargo)
    simple = dict(zip(dates[1:], px[1:, 0] / px[:-1, 0] - 1.0))      # buy-and-hold, as the study's benchmark
    bench = np.array([simple[d] for d in wf.dates])
    sc = validate.score_strategy(wf, grid=grid, full_pnl=m, n_trials=card["trials"]["N_total"], bench_daily=bench,
                                 seed=card["seed"], domain=DOMAIN)
    return plan.ReplayInput(
        card_id=card["card_id"], input_symbol=_SYMBOL, input_source=_SOURCE, input_dates=dates, input_close=close,
        oos_dates=tuple(wf.dates), oos_pnl=tuple(float(x) for x in wf.pnl),
        oos_turnover=tuple(float(x) for x in wf.turnover),
        lookbacks=tuple(int(k) for k in lookbacks), mas=tuple(int(k) for k in mas),
        grid=tuple(float(g["hysteresis"]) for g in grid), cost_bps_per_side=float(rules["cost_bps_per_side"]),
        embargo=int(used_embargo), n_trials=int(card["trials"]["N_total"]), seed=int(card["seed"]),
        domain=tuple(float(x) for x in DOMAIN["hysteresis"]),
        protocol=dict(protocol), gate_protocol={k: validate.GATE[k] for k in protocol},
        stats={"sr_oos": float(sc.sr_oos), "bench_sr": float(sc.bench_sr), "haircut_sr": float(sc.haircut_sr),
               "bench_diff": float(sc.bench_diff), "bench_ci": tuple(float(x) for x in sc.bench_ci),
               "decision": sc.decision, "chosen_last": float(grid[wf.chosen[-1]]["hysteresis"]),
               "n_sessions": int(sc.n_sessions), "n_trades": int(sc.n_trades)},
        results_md5=hashlib.md5(RESULTS.read_bytes()).hexdigest(), card_md5=hashlib.md5(card_bytes).hexdigest())
