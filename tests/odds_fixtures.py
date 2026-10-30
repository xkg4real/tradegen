"""Fixtures for the odds suite (odds plan, contract section 3.2). Task 1 adds the CHUNK and pilot swaps; Tasks 5, 9
and 13 add the venue, series, plan, context and input fixtures. Not in MODULES, and no name here starts with test_.
Each swap imports its modules when entered, so this file imports nothing from core/odds at load."""
from __future__ import annotations

import contextlib
import importlib
from typing import Iterator


@contextlib.contextmanager
def chunk(n: int = 2_000) -> Iterator[None]:
    """core.odds.simulate runs n paths per chunk: CHUNK = n, every DEFAULT_PATHS track = n and GARCH_SUB =
    min(GARCH_SUB, n), all three put back in finally; so a pipeline or CLI test that passes no path count runs one
    small chunk. import_module reads sys.modules, so the swap reaches the module that is loaded there."""
    sim = importlib.import_module("core.odds.simulate")
    saved = sim.CHUNK, sim.DEFAULT_PATHS, sim.GARCH_SUB
    sim.CHUNK, sim.DEFAULT_PATHS, sim.GARCH_SUB = n, {track: n for track in saved[1]}, min(saved[2], n)
    try:
        yield
    finally:
        sim.CHUNK, sim.DEFAULT_PATHS, sim.GARCH_SUB = saved


@contextlib.contextmanager
def pilots(n: int = 2_000, nodes: int = 64) -> Iterator[None]:
    """The GARCH pilot and the tilt pilot run n paths and check 1 uses `nodes` quantile nodes: models.PILOT_PATHS,
    simulate.TILT_PILOT and models.PILOT_NODES, all three put back in finally. Task 8's pilot tests run without it,
    at 20,000 paths and 512 nodes."""
    models = importlib.import_module("core.odds.models")
    sim = importlib.import_module("core.odds.simulate")
    saved = models.PILOT_PATHS, sim.TILT_PILOT, models.PILOT_NODES
    models.PILOT_PATHS, sim.TILT_PILOT, models.PILOT_NODES = n, n, nodes
    try:
        yield
    finally:
        models.PILOT_PATHS, sim.TILT_PILOT, models.PILOT_NODES = saved


# --------------------------------------------------------------------------- #
# Task 5: fixture venues, series, plans and contexts (contract 3.2). Each function imports core.odds when called,
# so this module still imports where core/odds/plan.py does not exist.
# --------------------------------------------------------------------------- #
import copy as _copy  # noqa: E402
import dataclasses as _dataclasses  # noqa: E402
import datetime as _dt  # noqa: E402

import yaml as _yaml  # noqa: E402

_UNVERIFIED = "UNVERIFIED: owner to confirm before approval"
_ODDS_KEYS = ("lot", "min_order", "fee_extras", "tick_ladder")
_LEG_FIELDS = ("venue", "symbol", "model", "bracket", "sizing", "edge_source", "assumed_p")
_KRX_LADDER = [[0, 1], [2000, 5], [5000, 10], [20000, 50], [50000, 100], [200000, 500], [500000, 1000]]


def _zero_extras() -> dict:
    return {"source": _UNVERIFIED, "phi_buy": 0, "phi_sell": 0}


_ODDS_DOC = {"schema": "tradegen.venues/1", "venues": {
    "kis": {"sections": ["krx", "us"], "settlement": ["KRW", "USD"], "quote_by_currency": True, "deposits": [],
            "source": _UNVERIFIED,
            "lot": {"source": _UNVERIFIED, "units": {"005930": 1, "069500": 1, "default": 1}},
            "min_order": {"source": _UNVERIFIED, "quote": {"KRW": 0, "USD": 0}},
            "fee_extras": _zero_extras(),
            "tick_ladder": {"source": _UNVERIFIED, "effective_from": "2026-10-02",
                            "books": {"KRX_stock_book": _KRX_LADDER}}},
    "upbit": {"sections": ["crypto"], "settlement": ["KRW"], "markets": [["BTC", "KRW"], ["USDT", "KRW"]],
              "default_quote": "KRW", "deposits": [{"symbol": "BTC", "network": "bitcoin", "tag_required": False}],
              "source": _UNVERIFIED,
              "lot": {"source": _UNVERIFIED, "units": {"default": 1e-8}},
              "min_order": {"source": _UNVERIFIED, "quote": {"KRW": 5000}},
              "fee_extras": _zero_extras()},
    "okx": {"sections": ["crypto"], "settlement": ["USDT", "USDC"], "markets": [["BTC", "USDT"], ["BTC", "USDC"]],
            "default_quote": "USDT", "deposits": [{"symbol": "BTC", "network": "bitcoin", "tag_required": False}],
            "source": _UNVERIFIED,
            "lot": {"source": _UNVERIFIED, "units": {"default": 1e-8}},
            "min_order": {"source": _UNVERIFIED, "quote": {"USDT": 1}},
            "fee_extras": _zero_extras()}}}


class _NoAliases(_yaml.SafeDumper):
    """A dumper that never writes &anchors or *aliases (the strict loader refuses both)."""

    def ignore_aliases(self, data) -> bool:
        return True


def _dump(doc: dict) -> bytes:
    return _yaml.dump(doc, Dumper=_NoAliases, sort_keys=False, default_flow_style=None, allow_unicode=True,
                      width=1000).encode("utf-8")


ODDS_VENUES: bytes = _dump(_ODDS_DOC)


def venues_with(**changes) -> bytes:
    """ODDS_VENUES with odds keys replaced, per venue: venues_with(upbit={"fee_extras": None, "lot": {"units":
    {"BTC": 1e-4}}}). A mapping replaces the whole key (its "source" defaults to the UNVERIFIED literal); None
    removes the key. Only kis, upbit and okx and the four odds keys can be named (KeyError otherwise)."""
    doc = _copy.deepcopy(_ODDS_DOC)
    for vid, keys in changes.items():
        entry = doc["venues"][vid]
        for key, value in keys.items():
            if key not in _ODDS_KEYS:
                raise KeyError(f"venues_with: {key!r} is not an odds key {_ODDS_KEYS}")
            if value is None:
                entry.pop(key, None)
            else:
                entry[key] = {"source": _UNVERIFIED, **_copy.deepcopy(value)}
    return _dump(doc)


def series(*, symbol="KRW-BTC", source="UPBIT", n=600, seed=1, start=None, vol=0.02, open_gap=0.0,
           price=50_000_000.0, step_days=1):
    """A synthetic random walk as a plan.Series (adjustment "", status "final") with its md5 filled: close-to-close
    log moves N(0, vol); each open is the previous close times exp(open_gap x N(0, 1)), the first one `price`.
    `start` (ISO) is the first date; None ends the series on 2026-10-22, the day before plan()'s start."""
    import numpy as np
    from core.odds import plan as P
    first = (_dt.date(2026, 10, 22) - _dt.timedelta(days=(n - 1) * step_days) if start is None
             else _dt.date.fromisoformat(start))
    dates = tuple((first + _dt.timedelta(days=i * step_days)).isoformat() for i in range(n))
    z = np.random.default_rng(seed).standard_normal((2, n))
    close = price * np.exp(np.cumsum(vol * z[0]))
    open_ = np.concatenate(([price], close[:-1])) * np.exp(open_gap * z[1])
    o, c = tuple(float(x) for x in open_), tuple(float(x) for x in close)
    return P.Series(symbol=symbol, source=source, dates=dates, open=o, close=c, adjustment="", status="final",
                    md5=P.series_md5(symbol, source, dates, o, c, "", "final"))


def plan(**changes):
    """The default plan (contract 3.2): compounding Upbit BTC buy-and-hold, stake KRW 42,000, target KRW 42,000,000,
    fx 1,400.0, start 2026-10-23 (F.ctx's date), horizon 10, bootstrap, fixed(1.0). A Leg field (venue, symbol,
    model, bracket, sizing, edge_source, assumed_p) changes the leg, `leg=` replaces it, any other key changes the
    plan; stake_krw, target_krw and fx_krw_per_usd given as an int become a float."""
    from core.odds import plan as P
    leg_changes = {k: changes.pop(k) for k in _LEG_FIELDS if k in changes}
    leg = changes.pop("leg", P.Leg(venue="upbit", symbol="BTC", model="bootstrap"))
    if leg_changes:
        leg = _dataclasses.replace(leg, **leg_changes)
    fields = dict(name="fixture plan", track="compounding", stake_krw=42_000.0, target_krw=42_000_000.0,
                  fx_krw_per_usd=1_400.0, start=_dt.date(2026, 10, 23), horizon_days=10, fraction=P.fixed(1.0))
    fields.update(changes)
    for key in ("stake_krw", "target_krw", "fx_krw_per_usd"):
        if type(fields[key]) is int:
            fields[key] = float(fields[key])
    return P.Plan(leg=leg, **fields)


def odds_ctx(**overrides):
    """F.ctx with ODDS_VENUES approved and equity KRW 42,000; F.ctx's owner (floor KRW 21,000, daily loss KRW 5,000,
    OKX cap 0.10), signed code and date 2026-10-23 otherwise. Any field can be overridden."""
    from tests import compliance_fixtures as F
    fields = {"active": F.approved(venues=ODDS_VENUES), "equity_krw": 42_000.0}
    fields.update(overrides)
    return F.ctx(**fields)


# --------------------------------------------------------------------------- #
# Task 9: engine inputs (contract 3.2). Each function below imports its dependencies locally.
# --------------------------------------------------------------------------- #
def inputs(plan, series, **changes):
    """plan.Inputs for `plan` on `series`: now 2026-10-23 09:00 KST, the crypto sessions of the horizon (every date
    of [plan.start, plan.start + plan.horizon_days)), no calendar, comparison "c000001" with run counter 1, K 1,
    J 0, R 1, and the provenance ("git:" + "0" * 40, "f" * 64, "49.0.0"). Any field can be changed by keyword."""
    import datetime

    from core.compliance import model
    from core.odds import plan as P
    fields = dict(now=datetime.datetime(2026, 10, 23, 9, 0, tzinfo=model.KST), series=series,
                  sessions=tuple((plan.start + datetime.timedelta(days=i)).isoformat()
                                 for i in range(plan.horizon_days)),
                  price_limits=(), calendar_sha256="", calendar_version="", calendar_md5s=(), calendar_error="",
                  replay=None, comparison_id="c000001", run_counter=1, comparison_plans=1, comparison_typed=0,
                  plan_runs=1, provenance=P.Provenance(repo_anchor="git:" + "0" * 40, tree_hash="f" * 64,
                                                      cryptography="49.0.0"))
    fields.update(changes)
    return P.Inputs(**fields)


def even_rows(m: float, n: int = 400):
    """n daily KRW-BTC bars ending 2026-10-22 that alternate between two prices: each open is the previous close
    and each close is the other price, so every overnight move m_o is 0 and every intraday move m_i is m, or a few
    ulps above it. The upper price is nudged up until exp(m_i) >= exp(m) and exp(-m_i) <= exp(-m) on every row, so
    a bracket with take_profit e^m - 1 and stop 1 - e^-m fills at every close: an even-money bet."""
    import datetime
    import math

    import numpy as np

    from core.odds import plan as P
    lo = 50_000_000.0
    hi = lo * math.exp(m)
    while True:
        o = np.array([lo if i % 2 == 0 else hi for i in range(n)])
        c = np.array([hi if i % 2 == 0 else lo for i in range(n)])
        m_i = np.abs(np.log(c[1:] / o[1:]))
        if (np.exp(m_i) >= math.exp(m)).all() and (np.exp(-m_i) <= math.exp(-m)).all():
            break
        hi = math.nextafter(hi, math.inf)
    first = datetime.date(2026, 10, 22) - datetime.timedelta(days=n - 1)
    dates = tuple((first + datetime.timedelta(days=i)).isoformat() for i in range(n))
    opens, closes = tuple(float(x) for x in o), tuple(float(x) for x in c)
    return P.Series(symbol="KRW-BTC", source="UPBIT", dates=dates, open=opens, close=closes, adjustment="",
                    status="final", md5=P.series_md5("KRW-BTC", "UPBIT", dates, opens, closes, "", "final"))


# --------------------------------------------------------------------------- #
# Task 13: pipeline runs on fixture contexts and inputs, the signed-calendar swap and call spies (contract 3.2)
# --------------------------------------------------------------------------- #
from contextlib import contextmanager as _contextmanager  # noqa: E402

CAL_SHA = "ab" * 32           # the calendar sha of every KRX fixture input; calendar_signed(CAL_SHA) signs it


@_contextmanager
def calendar_signed(sha: str) -> Iterator[None]:
    """core.compliance.owner.calendar_in_force swapped for `lambda now: sha` (save/restore), so a KRX or US leg whose
    inputs carry `sha` passes the calendar step. For the KRX steps after that step only: the CALENDAR_UNSIGNED and
    CALENDAR_COVERAGE tests use the real function (no key in the temp home); Task 18 signs a calendar end to end."""
    from core.compliance import owner
    saved = owner.calendar_in_force
    owner.calendar_in_force = lambda now: sha
    try:
        yield
    finally:
        owner.calendar_in_force = saved


@_contextmanager
def spy(target, name: str) -> Iterator[list]:
    """target.<name> wrapped so that every call is recorded as (args, kwargs, result) in the yielded list; the real
    attribute comes back afterwards."""
    real = getattr(target, name)
    calls: list = []

    def recorded(*args, **kwargs):
        result = real(*args, **kwargs)
        calls.append((args, kwargs, result))
        return result

    setattr(target, name, recorded)
    try:
        yield calls
    finally:
        setattr(target, name, real)


def owner_with(**changes):
    """F.ctx's owner state (floor KRW 21,000, daily loss KRW 5,000, OKX cap 0.10, OK) with fields replaced."""
    import dataclasses
    from tests import compliance_fixtures as F
    return dataclasses.replace(F.ctx().owner, **changes)


def fresh_series(n: int = 600, *, end: str = "2026-10-22", **changes):
    """series() of n daily bars whose last bar is `end` (by default the day before the fixture start, so the stale
    check passes); `changes` go to series(), never `start` or `step_days`."""
    import datetime as dt
    first = dt.date.fromisoformat(end) - dt.timedelta(days=n - 1)
    return series(n=n, start=first.isoformat(), **changes)


def weekdays(start, horizon_days: int) -> tuple[str, ...]:
    """Fixture KRX sessions: the weekdays of [start, start + horizon_days). Holidays are ignored: the core checks the
    session list's shape and the calendar sha, never the dates against a calendar."""
    import datetime as dt
    days = (start + dt.timedelta(days=i) for i in range(horizon_days))
    return tuple(d.isoformat() for d in days if d.weekday() < 5)


def pipeline_inputs(plan_obj, series_obj, **changes):
    """inputs() for a fixture leg, its clock reading at 09:00 KST on the plan's start: a crypto leg gets every date of
    the horizon, a KRX leg (kis and a six-digit code) the weekdays with one 0.30 limit each and CAL_SHA. `changes`
    override any Inputs field (a US leg passes its sessions and sha here)."""
    import datetime as dt
    from core.compliance import model
    start, horizon = plan_obj.start, plan_obj.horizon_days
    leg = plan_obj.leg[0] if isinstance(plan_obj.leg, (list, tuple)) else plan_obj.leg
    fields = {"now": dt.datetime(start.year, start.month, start.day, 9, 0, tzinfo=model.KST)}
    if leg.venue == "kis" and leg.symbol.isdigit():
        days = weekdays(start, horizon)
        fields.update(sessions=days, price_limits=(0.30,) * len(days), calendar_sha256=CAL_SHA)
    else:
        fields["sessions"] = tuple((start + dt.timedelta(days=i)).isoformat() for i in range(horizon))
    fields.update(changes)
    return inputs(plan_obj, series_obj, **fields)


def pipeline(plan_obj=None, ctx=None, series_obj=None, *, n_paths=None, **changes):
    """simulate.simulate on a fixture plan (default plan()), context (odds_ctx()) and series (fresh_series()), with
    pipeline_inputs(plan, series, **changes)."""
    from core.odds import simulate
    plan_obj = plan() if plan_obj is None else plan_obj
    ctx = odds_ctx() if ctx is None else ctx
    series_obj = fresh_series() if series_obj is None else series_obj
    return simulate.simulate(plan_obj, ctx, pipeline_inputs(plan_obj, series_obj, **changes), n_paths=n_paths)
