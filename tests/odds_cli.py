"""Odds plan Task 18: the CLI and the end-to-end runs (spec 4, 7.3, 7.5 "Comparing plans"; O12, O13, O15; R2-6;
Q11, Q12, Q14, Q15, Q24, Q36, Q37, Q45). Every test runs inside tests.odds_acceptance's wrapper: hermetic, a temp
TRADEGEN_HOME and the four bars seams patched to raise, so a seam this file does not fake is refused (a run that
reached one would exit 4). Signed homes come from tests.compliance_fixtures.full_home with the fixed test key, at
F.NOW (2026-10-24 09:00 KST, a Saturday); every plan starts that day, because screen refuses any other start. Every
run that reaches simulate passes --paths 2000 under OF.chunk() and OF.pilots(); the runs refused before simulate (no
owner key, a bad file, an unknown comparison, a crash, a guard hit, argument errors) simulate no path, so they pass no
--paths and need neither swap. The crypto plans have a 1-day horizon (every GARCH pilot path then has one sigma, so
check 1 evaluates one node) and a 260-bar history, and the crypto test swaps simulate.REFIT_B to 2 (the 20 refits
are odds_columns' to test). The time goes to owner.load_context (0.6 to 2.8 s in a signed home), full_home and the
GARCH-t fits, so the CLI loads one context per distinct stake, _reused_contexts reuses a context across runs between
which nothing under the home's compliance folder changes, and the KRX test signs its calendar into the home it
already has. Warnings are recorded, never printed, so a run's stderr holds only the CLI's own lines."""
from __future__ import annotations

import contextlib
import io
import json
import math
import random
import runpy
import sys
import types
import warnings
from datetime import date, timedelta
from pathlib import Path

from core.compliance import owner, rules
from core.odds import plan, report, simulate
from core.oddsdata import bars, inputs, replay, run
from tests import compliance_fixtures as F
from tests import odds_fixtures as OF
from tests.macro_m1_calendars import fixture_set

TODAY = "2026-10-24"                                   # F.NOW's Asia/Seoul date
LIMITS = {"total_loss_floor_krw": 21_000.0, "daily_loss_krw": 5_000.0}


def _walk(n: int, last: date, price: float, vol: float, seed: int, *, weekdays: bool, whole: bool):
    """(ISO dates, opens, closes) of a seeded random walk of n daily bars ending on `last` (weekdays only for KRX):
    each open is the previous close times a small gap, each close the open times the day's move."""
    days, d = [], last
    while len(days) < n:
        if not weekdays or d.weekday() < 5:
            days.append(d)
        d -= timedelta(days=1)
    days.reverse()
    rng, prev, opens, closes = random.Random(seed), price, [], []
    for _ in days:
        o = prev * math.exp(rng.gauss(0.0, vol / 4.0))
        c = o * math.exp(rng.gauss(0.0, vol))
        opens.append(float(round(o)) if whole else round(o, 2))
        closes.append(float(round(c)) if whole else round(c, 2))
        prev = c
    return [x.isoformat() for x in days], opens, closes


# Upbit KRW-BTC: 261 candles ending today, whose candle is still open at F.NOW and is dropped by the loader, which
# leaves 260 final bars (MIN_BARS is 250). KRX 069500: 300 weekday rows ending Friday 2026-10-23, near KRW 2,000.
_CRYPTO = _walk(261, date(2026, 10, 24), 50_000_000.0, 0.03, 7, weekdays=False, whole=False)
_KRX = _walk(300, date(2026, 10, 23), 2_000.0, 0.015, 11, weekdays=True, whole=True)


def _fake_upbit(market, days):
    """bars._upbit_daily's fake: the last `days` candles, in UpbitPublic.daily's Candles shape."""
    from data.crypto import crypto_client
    dates, opens, closes = (tuple(x[-int(days):]) for x in _CRYPTO)
    return crypto_client.Candles(symbol=market, dates=dates, open=opens, close=closes,
                                 high=tuple(map(max, opens, closes)), low=tuple(map(min, opens, closes)),
                                 source="UPBIT", note="odds_cli fake")


def _fake_kis(code, start, end):
    """bars._kis_daily's fake: KISClient.daily rows dated in [start, end] (YYYYMMDD), at most the last 100, as one
    KIS call returns them."""
    lo, hi = str(start).replace("-", ""), str(end).replace("-", "")
    rows = [{"date": d, "open": o, "high": max(o, c), "low": min(o, c), "close": c, "volume": 1_000.0, "source": "KIS"}
            for d, o, c in zip(*_KRX) if lo <= d.replace("-", "") <= hi]
    return rows[-100:]


@contextlib.contextmanager
def _patched(obj, name: str, value):
    saved = getattr(obj, name)
    setattr(obj, name, value)
    try:
        yield value
    finally:
        setattr(obj, name, saved)


@contextlib.contextmanager
def _seams(**fakes):
    """bars seams replaced by fakes inside the wrapper's raising stubs, which come back afterwards."""
    with contextlib.ExitStack() as stack:
        for name, fake in fakes.items():
            stack.enter_context(_patched(bars, name, fake))
        yield


@contextlib.contextmanager
def _signed_home():
    """A temp home that load_context accepts at F.NOW: the test key, the fixture venues (every odds key, zero fixed
    charges), the shipped rules and instrument map, the current code hash, LIMITS and the OKX cap signed."""
    with F.temp_home() as home, F.pubkey_at(home / "owner_pubkey.pem"):
        F.full_home(home, venues_raw=OF.ODDS_VENUES, limits=dict(LIMITS), cap=0.10)
        yield home


@contextlib.contextmanager
def _bare_home():
    """A temp home before owner act 1: no owner key, so load_context's owner state is BROKEN."""
    with F.temp_home() as home, F.pubkey_at(home / "absent.pem"):
        yield home


@contextlib.contextmanager
def _reused_contexts(calls: list | None = None):
    """owner.load_context memoised per (now, positions) for the block, then restored; `calls`, when given, gets the
    equity of every call the CLI makes, reused or not. Only for runs between which nothing under the home's
    compliance folder changes, so a fresh call would return an equal context. Yields the memo: one entry per real
    call."""
    real, memo = owner.load_context, {}

    def load(now, positions):
        if calls is not None:
            calls.append(positions.equity_krw)
        key = (now, repr(positions))
        if key not in memo:
            memo[key] = real(now, positions)
        return memo[key]

    with _patched(owner, "load_context", load):
        yield memo


def _leg(**changes) -> dict:
    return {"venue": "upbit", "symbol": "BTC", "model": "bootstrap", "bracket": None, "sizing": "floor_safe",
            "edge_source": "none", "assumed_p": None, **changes}


def _plan(leg: dict | None = None, **changes) -> dict:
    """A plan object of CONTRACT 14.2: by default a 1-day Upbit BTC buy-and-hold, compounding, KRW 42,000 to 46,200,
    fixed(1.0), floor-protected."""
    return {"name": "p", "track": "compounding", "stake_krw": 42_000, "target_krw": 46_200, "fx_krw_per_usd": 1_400.0,
            "start": TODAY, "horizon_days": 1, "leg": leg if leg is not None else _leg(),
            "fraction": {"kind": "fixed", "value": 1.0}, **changes}


def _doc(*plans) -> bytes:
    return json.dumps({"schema": "tradegen.odds_plan/1", "plans": list(plans)}).encode("utf-8")


def _file(home: Path, *plans, name: str = "plan.json") -> str:
    path = home / name
    path.write_bytes(_doc(*plans))
    return str(path)


def _main(argv, stdout) -> tuple[int, str]:
    """(exit code, stderr) of run.main(argv) at F.NOW with `stdout` as sys.stdout. Warnings are recorded, never
    printed (scipy's optimizer may warn during a GARCH-t fit), so stderr holds only the CLI's own lines."""
    err = io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(err), warnings.catch_warnings(record=True):
        warnings.simplefilter("always")
        code = run.main(list(argv), now=F.NOW)
    return code, err.getvalue()


def _cli(*argv: str) -> tuple[int, str, str]:
    """(exit code, stdout, stderr) of run.main(argv) at F.NOW."""
    out = io.StringIO()
    code, err = _main(argv, out)
    return code, out.getvalue(), err


def _cli_ascii(*argv: str) -> tuple[int, str, str]:
    """_cli with stdout an ASCII text stream: unless main switches it to UTF-8, printing a card fails (exit 4)."""
    raw = io.BytesIO()
    stream = io.TextIOWrapper(raw, encoding="ascii", newline="\n")
    code, err = _main(argv, stream)
    stream.flush()
    return code, raw.getvalue().decode("utf-8"), err


def _lead(key: str) -> str:
    """A catalogue sentence's fixed text before its first slot."""
    return report.CATALOGUE[key].split("{")[0]


def test_load_plans_reads_the_file_format():
    """CONTRACT 14.2: plan objects become plan.Plan values (every number a float, horizon_days as given) for
    check_plan to judge; what the format does not allow is UNSUPPORTED_PRODUCT sub "file", for the whole file when it
    does not parse and for that plan alone otherwise. A float horizon_days and a start that is text but no exact
    YYYY-MM-DD load as they are, so check_plan refuses them by their own subs (CONTRACT 5.3, Q25)."""
    good = _plan(name="a", leg=_leg(bracket={"take_profit": 0.2, "stop": 0.1}, edge_source="assumed", assumed_p=0.55))
    [p] = run.load_plans(_doc(good))
    assert p == plan.Plan(name="a", track="compounding", stake_krw=42_000.0, target_krw=46_200.0,
                          fx_krw_per_usd=1_400.0, start=date(2026, 10, 24), horizon_days=1,
                          leg=plan.Leg(venue="upbit", symbol="BTC", model="bootstrap",
                                       bracket=plan.Bracket(take_profit=0.2, stop=0.1), sizing="floor_safe",
                                       edge_source="assumed", assumed_p=0.55),
                          fraction=plan.Fraction(kind="fixed", value=1.0)), p
    assert type(p.stake_krw) is float and type(p.target_krw) is float and type(p.horizon_days) is int
    other = {k: v for k, v in good.items() if k != "leg"}
    one, two = run.load_plans(_doc({**other, "legs": [good["leg"]]}, {**other, "legs": [good["leg"], _leg()]}))
    assert one == p, one                                    # a legs list of one is that leg
    assert two.leg == (p.leg, plan.Leg(venue="upbit", symbol="BTC", model="bootstrap")), two   # MULTI_LEG later
    odd = {**good, "track": "x", "stake_krw": -5, "horizon_days": 0, "leg": _leg(venue="bithumb")}
    [odd] = run.load_plans(_doc(odd))                       # values are check_plan's to judge, not the file's
    assert (odd.track, odd.stake_krw, odd.horizon_days, odd.leg.venue) == ("x", -5.0, 0, "bithumb"), odd
    [big] = run.load_plans(_doc(good).replace(b'"stake_krw": 42000', b'"stake_krw": 1e400'))
    assert math.isinf(big.stake_krw), big                   # check_plan refuses it (sub "numbers")
    loose = run.load_plans(_doc({**good, "horizon_days": 1.0}, {**good, "start": "20261024"},
                                {**good, "start": "2026-02-30"}))
    assert [(x.horizon_days, x.start) for x in loose] == [(1.0, date(2026, 10, 24)), (1, "20261024"),
                                                          (1, "2026-02-30")], loose
    assert type(loose[0].horizon_days) is float, loose[0]
    today = types.SimpleNamespace(date=date(2026, 10, 24))   # check_plan reads only ctx.date before these rules
    assert [(r.code, r.sub) for r in (plan.check_plan(x, today) for x in loose)] == [
        ("UNSUPPORTED_PRODUCT", "horizon"), ("UNSUPPORTED_PRODUCT", "start"), ("UNSUPPORTED_PRODUCT", "start")]

    def refused(item, where) -> None:
        assert isinstance(item, plan.Refusal), (where, item)
        assert (item.code, item.sub) == ("UNSUPPORTED_PRODUCT", "file"), (where, item)

    for raw in (b'{"schema": "tradegen.odds_plan/1", "plans": [',
                b'{"schema": "tradegen.odds_plan/1", "plans": ' + b"[" * 100_000 + b"]" * 100_000 + b"}",
                b"\xff\xfe",
                b'{"schema": "tradegen.odds_plan/1", "plans": [{"stake_krw": NaN}]}',
                b'{"schema": "tradegen.odds_plan/1", "schema": "tradegen.odds_plan/1", "plans": []}',
                b"\xef\xbb\xbf" + _doc(good),
                json.dumps({"schema": "tradegen.odds_plan/2", "plans": [good]}).encode("utf-8"),
                json.dumps({"schema": "tradegen.odds_plan/1"}).encode("utf-8"),
                json.dumps({"schema": "tradegen.odds_plan/1", "plans": [good], "note": 1}).encode("utf-8"),
                json.dumps({"schema": "tradegen.odds_plan/1", "plans": []}).encode("utf-8"),
                json.dumps({"schema": "tradegen.odds_plan/1", "plans": {"a": good}}).encode("utf-8"),
                json.dumps([good]).encode("utf-8")):
        out = run.load_plans(raw)
        assert len(out) == 1, (raw, out)
        refused(out[0], raw)
    for bad in ({**good, "colour": "red"}, {k: v for k, v in good.items() if k != "track"},
                {**good, "legs": [good["leg"]]}, {**other, "legs": []}, {**other, "legs": good["leg"]},
                {**good, "stake_krw": True}, {**good, "stake_krw": "42000"}, {**good, "stake_krw": 10 ** 400},
                {**good, "horizon_days": True}, {**good, "horizon_days": "1"}, {**good, "start": 20261024},
                {**good, "start": None}, {**good, "name": 7},
                {**good, "leg": {**good["leg"], "extra": 1}}, {**good, "leg": {**good["leg"], "venue": None}},
                {**good, "leg": {**good["leg"], "bracket": {"take_profit": 0.2}}},
                {**good, "leg": {**good["leg"], "assumed_p": "0.55"}},
                {**good, "fraction": {"kind": "fixed", "value": "1"}}, {**good, "fraction": {"kind": "fixed"}},
                "not an object"):
        out = run.load_plans(_doc(bad, good))
        assert len(out) == 2 and out[1] == p, (bad, out)    # the other plan of the file still loads
        refused(out[0], bad)


def test_two_crypto_plans_one_comparison_one_seed():
    """Spec 7.3, 7.5 "Comparing plans", Q12, Q15, Q37 (8.o items 8 and 9): one invocation with two plans is one
    comparison (state.json c000001) and prints both cards in file order, one blank line apart, each with its typical
    result before its headline, the K note (2 plans), the R note (1 comparison) and, on the moonshot card only, the
    caption; no plan name renders; stdout is UTF-8 even when it was ASCII. Rerunning the moonshot plan alone with
    the issued id reproduces every line of its card but the head's numbering (Q12: one seed per comparison, and K
    stays the comparison's 2 plans). Run alone without an id it is a fresh comparison: c000003 (begin_run names a new
    id by its run count, and the rerun was run 2) on run counter 3, K = 1 and R = 2 comparisons that hold it; the
    seed's dependence on the counter is tests/odds_models.py's. The one context is loaded once and reused by all
    three runs (_reused_contexts), so the rerun checks everything after load_context. simulate.REFIT_B is 2 here
    (module docstring). The owner log is never written."""
    first = _plan(name="zqalphaplan")
    second = _plan(name="zqbetaplan", track="moonshot", target_krw=42_000_000)
    with _signed_home() as home, _reused_contexts() as memo, OF.chunk(), OF.pilots(), \
            _patched(simulate, "REFIT_B", 2), _seams(_upbit_daily=_fake_upbit):
        log = owner.log_path().read_bytes()
        both = _file(home, first, second)
        code, out, err = _cli_ascii("--plan", both, "--paths", "2000")
        assert code == 0 and err == "", (code, err, out[:900])
        assert "Bürgi" in out and "±" in out, "the base rates and the average line print as UTF-8"
        assert "zqalphaplan" not in out and "zqbetaplan" not in out, "a plan name rendered (Q37)"
        assert out.startswith("Plan 1 of 2 (") and out.count("Plan 2 of 2 (") == 1, out[:300]
        cut = out.index("Plan 2 of 2 (")
        card1, card2 = out[:cut], out[cut:]
        assert card1.endswith("\n\n") and not card1.endswith("\n\n\n"), "one blank line between cards"
        assert card2.endswith("\n") and not card2.endswith("\n\n"), "no blank line after the last card"
        for card, head in ((card1, "headline.compounding"), (card2, "headline.moonshot")):
            assert _lead("refused.head") not in card, card[:900]
            assert 0 <= card.index(_lead("typical.median")) < card.index(_lead(head)), card[:1500]
            assert report.say("compare.k", k=2, j=0) in card and report.say("compare.r", r=1) in card, card
            assert "c000001" in card, card
        assert report.say("compare.caption") in card2 and report.say("compare.caption") not in card1
        hashes = sorted(plan.plan_hash(p) for p in run.load_plans(Path(both).read_bytes()))
        state = json.loads(inputs.state_path().read_bytes())
        assert state["runs"] == 1, state
        assert state["comparisons"] == {"c000001": {"run": 1, "plans": hashes, "typed": []}}, state

        alone = _file(home, second, name="again.json")
        code, again, err = _cli("--plan", alone, "--paths", "2000", "--comparison", "c000001")
        assert code == 0 and err == "", (code, err, again[:900])
        head, _, body = card2.partition("\n")
        assert again == head.replace("Plan 2 of 2 (", "Plan 1 of 1 (", 1) + "\n" + body, (
            "a rerun in its comparison must reproduce every number and every hash")
        assert json.loads(inputs.state_path().read_bytes()) == {**state, "runs": 2}

        code, fresh, err = _cli("--plan", alone, "--paths", "2000")
        assert code == 0 and err == "" and fresh.startswith("Plan 1 of 1 ("), (code, err, fresh[:900])
        assert "c000003" in fresh and "c000001" not in fresh, fresh
        assert report.say("compare.k", k=1, j=0) in fresh and report.say("compare.r", r=2) in fresh, fresh
        [moon] = run.load_plans(_doc(second))
        assert json.loads(inputs.state_path().read_bytes()) == {**state, "runs": 3, "comparisons": {
            **state["comparisons"], "c000003": {"run": 3, "plans": [plan.plan_hash(moon)], "typed": []}}}
        assert len(memo) == 1, memo
        assert owner.log_path().read_bytes() == log, "the CLI wrote the owner log"


def test_krx_plans_need_the_signed_calendar():
    """Q6, Q24 step 6, 8.o item 6 (CALENDAR_UNSIGNED through load_context): a KRX plan in a full home with no
    calendar approval exits 2 with the CALENDAR_UNSIGNED sentence; once tests.macro_m1_calendars.fixture_set() is
    approved as the calendar in that same home (F.approve, as full_home's calendar_raw does it, stamped 2026-10-23,
    so in force at F.NOW) it runs to a card (exit 0) on that calendar, whose sha prefix the card records. Each run
    loads its own context: the approval changes the home. The CLI never writes the owner log."""
    krx = _plan(name="krx", horizon_days=10, leg=_leg(venue="kis", symbol="069500"))
    unsigned = report.say("why.CALENDAR_UNSIGNED")
    calendar = rules.calendar_stream(fixture_set().data_dir)
    with F.temp_home() as home, F.pubkey_at(home / "owner_pubkey.pem"), OF.chunk(), OF.pilots(), \
            _seams(_kis_daily=_fake_kis):
        key = F.full_home(home, venues_raw=OF.ODDS_VENUES, limits=dict(LIMITS), cap=0.10)
        path, log = _file(home, krx), owner.log_path().read_bytes()
        code, out, err = _cli("--plan", path, "--paths", "2000")
        assert code == 2 and err == "" and unsigned in out, (code, err, out[:900])
        assert owner.log_path().read_bytes() == log, "the CLI wrote the owner log"
        F.approve(home, key, "calendar", calendar)
        log = owner.log_path().read_bytes()
        code, out, err = _cli("--plan", path, "--paths", "2000")
        assert code == 0 and err == "", (code, err, out[:900])
        assert unsigned not in out and _lead("refused.head") not in out, out[:900]
        assert rules.file_sha256(calendar)[:16] in out, "the card records the signed calendar's sha"
        assert owner.log_path().read_bytes() == log, "the CLI wrote the owner log"


def test_unknown_comparison_ids_refuse_and_write_nothing():
    """Q12, Q36: --comparison takes only an id begin_run issued. An unknown id refuses every plan that passed the
    precheck UNSUPPORTED_PRODUCT sub "comparison" (exit 2), on a card with the context's provenance lines, before any
    seam is called (the raising stubs stay) and with no odds state written: not even the odds folder. A malformed
    id takes the same ValueError out of begin_run; the id rules are tests/odds_inputs.py's. A state file that does not parse
    is a crash, never a comparison refusal: exit 4, no card, and the file stays as it was for the owner to delete.
    Both runs share one context (_reused_contexts)."""
    why = report.say("why.UNSUPPORTED_PRODUCT", what=report.say("sub.comparison"))
    with _signed_home() as home, _reused_contexts() as memo:
        path = _file(home, _plan())
        code, out, err = _cli("--plan", path, "--comparison", "c000009")
        assert code == 2 and err == "" and why in out and report.say("prov.head") in out, (code, err, out[:900])
        assert not (home / "odds").exists(), sorted((home / "odds").rglob("*"))
        inputs.state_path().parent.mkdir(parents=True, exist_ok=True)
        inputs.state_path().write_bytes(b"{")
        code, out, err = _cli("--plan", path, "--comparison", "c000001")
        assert code == 4 and out == "" and err.startswith("crash: RuntimeError: "), (code, out, err)
        assert inputs.state_path().read_bytes() == b"{", "the crash rewrote the state file"
        assert len(memo) == 1, memo


def test_each_plan_gets_its_own_inputs_in_one_comparison():
    """CONTRACT 14.1, Q11, with bars.load_leg, replay.replay_s_c3 and simulate.simulate replaced by recorders (no
    Monte Carlo) and every owner.load_context call recorded: a plan the precheck refuses stays out of the comparison;
    one begin_run gives the other three one comparison (K = 3, J = 1 typed win rate); each gets the run's moment, its
    crypto session, its series, the --refetch flag, the path count and a context whose equity is its own stake (one
    load_context call per distinct stake in each invocation); one replay serves both replay legs and the plain leg
    gets none; the cards are numbered in file order. The typed plan run again alone is a fresh comparison: c000002 on
    run counter 2 (so a new market seed), K = 1, and R = 2 comparisons that hold the plan. The second invocation's
    call reuses the first's context (_reused_contexts): two real loads for the three calls."""
    series, sentinel, loads, replays, seen, equities = OF.series(), object(), [], [], [], []

    def load(p, inst, now, *, refetch=False):
        loads.append((p.name, isinstance(inst, rules.Instrument), now, refetch))
        return series

    def replayed(**_k):
        replays.append(1)
        return sentinel

    def simulated(p, ctx, inp, *, n_paths=None):
        seen.append((p.name, ctx.equity_krw, inp, n_paths))
        return report.refusal_report(p, plan.Refusal(code="CARD_NOT_REPRODUCED", detail="odds_cli wiring test"))

    replay_leg = _leg(edge_source=plan.REPLAY_SOURCE)
    typed = _plan(name="typed", stake_krw=50_000, target_krw=55_000,
                  leg=_leg(bracket={"take_profit": 0.2, "stop": 0.1}, edge_source="assumed", assumed_p=0.55))
    plans = (_plan(name="r1", leg=replay_leg),
             _plan(name="r2", leg=replay_leg, fraction={"kind": "kelly", "value": 0.5}),
             typed, _plan(name="late", start="2026-10-23"))
    with _signed_home() as home, OF.chunk(), _reused_contexts(equities) as memo, \
            _patched(bars, "load_leg", load), _patched(replay, "replay_s_c3", replayed), \
            _patched(simulate, "simulate", simulated):
        path = _file(home, *plans)
        code, out, err = _cli("--plan", path, "--paths", "2000", "--refetch")
        state = json.loads(inputs.state_path().read_bytes())
        hashes = sorted(plan.plan_hash(p) for p in run.load_plans(Path(path).read_bytes())[:3])
        again = _cli("--plan", _file(home, typed, name="typed.json"), "--paths", "2000")
        later = json.loads(inputs.state_path().read_bytes())
    assert code == 2 and err == "", (code, err, out[:900])
    assert equities == [42_000.0, 50_000.0, 50_000.0], equities    # r1's (r2 and late reuse it), typed's, typed's
    assert len(memo) == 2, memo
    assert [(name, equity) for name, equity, _, _ in seen] == [("r1", 42_000.0), ("r2", 42_000.0),
                                                               ("typed", 50_000.0), ("typed", 50_000.0)], seen
    assert len(replays) == 1, replays
    assert loads == [(name, True, F.NOW, True) for name in ("r1", "r2", "typed")] + [
        ("typed", True, F.NOW, False)], loads                      # --refetch on the first run only
    for name, _, inp, n_paths in seen:
        assert n_paths == 2000 and inp.now == F.NOW and inp.series is series, name
        assert (inp.sessions, inp.price_limits, inp.calendar_sha256, inp.calendar_error) == ((TODAY,), (), "", ""), name
        assert (inp.replay is sentinel) == (name != "typed"), name
    for _, _, inp, _ in seen[:3]:
        assert (inp.comparison_id, inp.run_counter, inp.comparison_plans, inp.comparison_typed,
                inp.plan_runs) == ("c000001", 1, 3, 1, 1), inp
    assert state == {"schema": "tradegen.odds_state/1", "runs": 1,
                     "comparisons": {"c000001": {"run": 1, "plans": hashes, "typed": [0.55]}}}, state
    heads = [out.index(f"Plan {i} of 4 (") for i in range(1, 5)]
    assert heads[0] == 0 and heads == sorted(heads), heads
    assert out.count(report.say("why.CARD_NOT_REPRODUCED")) == 3, out
    assert report.say("why.UNSUPPORTED_PRODUCT", what=report.say("sub.start")) in out[heads[3]:], out
    inp = seen[3][2]
    assert again[0] == 2 and again[2] == "" and again[1].startswith("Plan 1 of 1 ("), again
    assert (inp.comparison_id, inp.run_counter, inp.comparison_plans, inp.comparison_typed,
            inp.plan_runs) == ("c000002", 2, 1, 1, 2), inp
    [typed_hash] = [plan.plan_hash(p) for p in run.load_plans(_doc(typed))]
    assert later == {**state, "runs": 2, "comparisons": {**state["comparisons"], "c000002": {
        "run": 2, "plans": [typed_hash], "typed": [0.55]}}}, later


def test_no_owner_key_refuses_before_any_data_or_write():
    """Q45, O15: before owner act 1 every plan is refused STATE_UNUSABLE by the precheck (exit 2), each card with the
    context's provenance lines (simulate.context_provenance; spec 7.5, CONTRACT 10.4): no seam is called (the raising
    stubs stay in place) and nothing is written under the home, neither odds state nor compliance files. Task 19
    repeats this on the real home."""
    with _bare_home() as home:
        path = _file(home, _plan(), _plan(name="krx", horizon_days=10, leg=_leg(venue="kis", symbol="069500")))
        code, out, err = _cli("--plan", path)
        assert code == 2 and err == "", (code, err, out[:600])
        assert out.count(report.say("why.STATE_UNUSABLE")) == 2, out
        assert out.count(report.say("prov.head")) == 2, out
        assert not (home / "odds").exists() and not (home / "compliance").exists(), sorted(home.iterdir())


def test_partial_chunk_is_refused_at_the_real_chunk():
    """Q24 step 1 at the real CHUNK (no chunk() swap): a path count that is not a positive whole multiple of 200,000
    is refused PARTIAL_CHUNK (exit 2) before anything else, and no odds state is written. The three runs share
    one context (_reused_contexts)."""
    assert simulate.CHUNK == 200_000
    with _bare_home() as home, _reused_contexts():
        path = _file(home, _plan())
        for n in ("1000", "0", "-200000"):
            code, out, err = _cli("--plan", path, "--paths", n)
            assert code == 2 and err == "" and _lead("why.PARTIAL_CHUNK") in out, (n, code, err, out[:600])
        assert not (home / "odds").exists()


def test_file_problems_refuse_each_plan_by_name():
    """CONTRACT 14.2 end to end: a file that is not JSON prints one refused card, rendered like any card whose plan
    has no hash ("(none)" in its head); in a file whose first plan has an unknown key and whose second has a legs
    list of two, the first card says UNSUPPORTED_PRODUCT (a plan file the engine can read) and the second
    MULTI_LEG_UNSUPPORTED; both exit 2 and write no odds state."""
    file_why = report.say("why.UNSUPPORTED_PRODUCT", what=report.say("sub.file"))
    no_hash = report.say("plan.head", i="1", k="1", hash=report.say("edge.none"))
    with _bare_home() as home:
        bad = home / "bad.json"
        bad.write_bytes(b'{"schema": "tradegen.odds_plan/1", "plans": [')
        code, out, err = _cli("--plan", str(bad))
        assert code == 2 and err == "" and out.startswith(no_hash + "\n") and file_why in out, (code, err, out)
        two_legs = {k: v for k, v in _plan(name="two").items() if k != "leg"} | {"legs": [_leg(), _leg(symbol="ETH")]}
        code, out, err = _cli("--plan", _file(home, _plan(colour="red"), two_legs))
        assert code == 2 and err == "" and out.startswith("Plan 1 of 2 ("), (code, err, out)
        cut = out.index("Plan 2 of 2 (")
        assert file_why in out[:cut] and report.say("why.MULTI_LEG_UNSUPPORTED") in out[cut:], out
        assert file_why not in out[cut:], out
        assert not (home / "odds").exists()


def test_a_crash_exits_4_and_prints_no_card():
    """Q15: any exception is exit 4, with "crash: <type>: <text>" on stderr and nothing on stdout."""
    def planted(*_a, **_k):
        raise RuntimeError("planted failure")

    with _bare_home() as home, _patched(simulate, "precheck", planted):
        code, out, err = _cli("--plan", _file(home, _plan()))
    assert (code, out, err) == (4, "", "crash: RuntimeError: planted failure\n"), (code, out, err)


def test_a_language_guard_hit_exits_4():
    """Q14: render runs report.guard over its own output and raises on a hit, on every card the CLI prints (the card
    of a plan object the loader could not read included); the CLI turns that ValueError into exit 4 and prints no
    card. The banned word is planted in a copy of the catalogue swapped in as report.CATALOGUE (restored
    afterwards)."""
    planted = {**report.CATALOGUE, "refused.none": report.CATALOGUE["refused.none"] + " This is the best plan."}
    with _bare_home() as home, _patched(report, "CATALOGUE", planted):
        bad = home / "bad.json"
        bad.write_bytes(b"[")
        for path in (_file(home, _plan()), str(bad)):          # a STATE_UNUSABLE card, then the loader's
            code, out, err = _cli("--plan", path)
            assert code == 4 and out == "", (path, code, out, err)
            assert err.startswith("crash: ValueError: rendered text failed the language guard"), (path, err)


def test_argument_errors_exit_4_and_help_exits_0():
    """Q15: argparse errors (exit_on_error=False raises them) and a plan file that cannot be opened are crashes,
    exit 4; --help prints the usage and exits 0. Nothing is written."""
    with _bare_home() as home:
        path = _file(home, _plan())
        for argv in ((), ("--plan",), ("--plan", path, "--paths", "two"), ("--plan", path, "--bogus")):
            code, out, err = _cli(*argv)
            assert code == 4 and out == "" and err.startswith("crash: ArgumentError: "), (argv, code, out, err)
        code, out, err = _cli("--plan", str(home / "missing.json"))
        assert code == 4 and out == "" and err.startswith("crash: FileNotFoundError: "), (code, out, err)
        code, out, err = _cli("--help")
        assert code == 0 and err == "" and out.startswith("usage: python -m core.oddsdata.run"), (code, out, err)
        assert not (home / "odds").exists()


def test_the_main_block_exits_through_system_exit():
    """CONTRACT 14.1: `python -m core.oddsdata.run` is `raise SystemExit(main())`: run here with runpy, --help exits
    0 with the usage on stdout and an argparse error exits 4 with the crash line on stderr. sys.argv is restored."""
    saved = sys.argv
    try:
        for argv, want, stream in ((["--help"], 0, "usage: python -m core.oddsdata.run"),
                                   (["--bogus"], 4, "crash: ArgumentError: ")):
            sys.argv = ["run.py", *argv]
            out, err = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err), warnings.catch_warnings():
                warnings.simplefilter("ignore", RuntimeWarning)       # runpy: the module is already in sys.modules
                try:
                    runpy.run_module("core.oddsdata.run", run_name="__main__")
                except SystemExit as exc:
                    code = exc.code
                else:
                    raise AssertionError(f"{argv}: the __main__ block returned without SystemExit")
            text = out.getvalue() if want == 0 else err.getvalue()
            assert code == want and text.startswith(stream), (argv, code, out.getvalue(), err.getvalue())
    finally:
        sys.argv = saved
