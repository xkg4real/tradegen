### Task 18: The CLI and the end-to-end runs (`core/oddsdata/run.py`)

**Files:**
- Create: `core/oddsdata/run.py` (LF; unsigned: `core.oddsdata.` is outside the D14 acting prefix `core.odds.`)
- Create: `tests/odds_cli.py` (LF; UTF-8, it holds "±" and "Bürgi")
- Test: `tests/odds_cli.py` (already listed in `tests/odds_acceptance.MODULES` by Task 1, so no existing file is
  edited by this task and the DRIFT RULE has nothing to apply to)

**Interfaces:**
- Consumes (CONTRACT names; every one exists once Tasks 1 to 17 are merged):
  - `core.compliance.owner.load_context(now, positions) -> model.Context` (raises only on a naive `now`; run.py
    looks it up at call time, so a test can count its calls) and `owner.log_path()`;
    `core.compliance.model.Positions(equity_krw=...)`, `model.Context.equity_krw`; `core.compliance.rules.Instrument`
    (its `section`), `rules.calendar_stream(data_dir) -> bytes`, `rules.file_sha256(raw) -> str`.
  - `core.odds.plan` (Task 5): `Plan`, `Leg`, `Bracket`, `Fraction`, `Refusal(code, sub="", slots={}, detail="")`,
    `Inputs` (fields `now`, `series`, `sessions`, `price_limits`, `calendar_sha256`, `calendar_error`, `replay`,
    `comparison_id`, `run_counter`, `comparison_plans`, `comparison_typed`, `plan_runs`), `REPLAY_SOURCE`, `MARKET`,
    `instrument(plan, ctx) -> (venue, inst)`, `plan_hash(plan)`.
  - `core.odds.simulate` (Tasks 9, 13, 14, 17): `CHUNK`, `REFIT_B` (contract 8.1), `precheck(plan, ctx,
    n_paths=None) -> Refusal | None`, `simulate(plan, ctx, inputs, *, n_paths=None) -> report.OddsReport`, and
    `context_provenance(ctx) -> dict` (Task 13: the provenance keys of a sealed context, which simulate's own refused
    cards carry; `{}` for an unsealed one). The crypto test swaps `simulate.REFIT_B` to 2 (this task's own reading,
    below). The swap reaches the refit member because both readers take the module global at call time as drafted:
    Task 9's `_run_paths` (`len(spec.fits) == REFIT_B`) and Task 14's `_garch_member` (`for b in range(REFIT_B)`;
    Task 14's Interfaces state it under "Module globals read at call time"). Neither takes it as a default argument
    or a copy made at import.
  - `core.odds.report` (Task 12): `CATALOGUE` (read by `say` at call time), `say(key, **slots)`,
    `refusal_report(plan_obj, refusal, *, index=1, count=1, provenance=...)` (plan_obj None for a plan object the
    loader refused: hash "", so render's head shows `edge.none`; an empty provenance renders no provenance lines),
    `render(rep)` (every card ends in one newline; raises `ValueError("rendered text failed the language guard:
    ...")`), `OddsReport.plan_index`, `.plan_count`, `.refused`; the catalogue keys `plan.head`, `edge.none`,
    `refused.head`, `refused.none`, `why.*`, `sub.file`, `sub.comparison`, `sub.start`, `typical.median`,
    `headline.compounding`, `headline.moonshot`, `compare.k`, `compare.r`, `compare.caption`, `prov.head`.
  - `core.oddsdata.bars` (Task 15): `load_leg(plan, inst, now, *, refetch=False) -> plan.Series`; the seams
    `_upbit_daily(market, days)` (returns `data.crypto.crypto_client.Candles`) and `_kis_daily(code, start, end)`
    (YYYYMMDD; returns `KISClient.daily` rows), looked up at call time.
  - `core.oddsdata.inputs` (Task 16): `calendar_for(now)`, `sessions(market, start, horizon_days, cal)`,
    `begin_run(comparison, plan_hashes, typed)` (ValueError, before any write, for an id it never issued or a
    malformed one; RuntimeError for a state file that does not parse), `build_inputs(plan, now, *, series,
    sessions_info, calendar_sha, replay, run)`, `state_path()`.
  - `core.oddsdata.replay.replay_s_c3() -> plan.ReplayInput` (Task 17).
  - Tests: `tests.compliance_fixtures` `temp_home`, `pubkey_at`, `full_home(home, *, venues_raw=None,
    calendar_raw=None, limits=None, cap=None)` (returns the test key), `approve(home, key, kind, raw) -> str`, `NOW`
    (Task 4); `tests.odds_fixtures` `chunk()`, `pilots()`, `ODDS_VENUES`, `series()` (Tasks 1, 5);
    `tests.macro_m1_calendars.fixture_set()` and its `.data_dir`;
    `tests.odds_acceptance._wrap` (hermetic, temp home, the four seams set to `tests.macro_acceptance._boom`).
- Produces (Task 19's real-home smoke and the E1 hand-off rely on these):
  - `core.oddsdata.run.main(argv=None, *, now: datetime | None = None) -> int`: 0 every plan reported, 2 any plan
    refused, 4 any exception (argparse errors included; `crash: <type>: <text>` on stderr, nothing on stdout);
    `--help` prints the usage and returns 0. One `owner.load_context` per distinct stake, with that stake as the
    equity (Q11; one per distinct stake rather than one per plan is this task's reading, below). Cards print in file
    order, one blank line apart and none after the last, after stdout and stderr are switched to UTF-8. Its default
    `now` is the only wall clock in `core/oddsdata`.
  - `core.oddsdata.run.load_plans(raw: bytes) -> list[plan.Plan | plan.Refusal]` (CONTRACT 14.2).
  - The exact `__main__` block `if __name__ == "__main__":\n    raise SystemExit(main())`.
  - Private helpers (leading underscore, used only here): `_SCHEMA`, `_PLAN_KEYS`, `_LEG_KEYS`, `_Bad`,
    `_no_constant`, `_no_repeats`, `_obj`, `_str`, `_num`, `_day`, `_leg`, `_plan`,
    `_inputs(p, ctx, now, begun, refetch, replayed) -> plan.Inputs`, `_run(args, now) -> tuple[int, list[str]]`,
    `_parser()`.

**Plan decisions used:** Q11 (`Positions(equity_krw=float(plan.stake_krw))`), Q12 (one comparison per invocation,
`--comparison` only an issued id, R printed), Q13 (seams faked inside the wrapper, the bars cache; every test at most
15 s), Q14 (render's own guard pass, exit 4), Q15 (the CLI and exits 0, 2, 4), Q24 (the precheck order:
PARTIAL_CHUNK, product, STATE_UNUSABLE, LIMITS_UNSET), Q25 (the plan file; `start` and `horizon_days` judged by
check_plan), Q31 (the refit member), Q36 (an unparseable state file is a crash), Q37 (the plan name never renders),
Q45 (precheck before any data or write); O12, O13, O15; R2-6 (no run-time `core.engine` check: Task 1's static guards
stay); RULINGS_ROUND3 G3-1 and G3-2 (counts and times come from the drafts; a module over its time target is
recorded with its measured time and never cut to fit).

Drafter readings recorded here (none loosens anything): `--help` exits 0, because it is not an argparse error (Q15
names errors); an empty `legs` list is UNSUPPORTED_PRODUCT sub `file`, because MULTI_LEG_UNSUPPORTED's sentence says
"more than one leg"; a number literal such as `1e400` loads as `inf` and `plan.check_plan` refuses it (sub
`numbers`), while an integer too large for a float, and a file nested too deep to decode (RecursionError), are sub
`file`; a float `horizon_days` and a `start` that is text but no exact YYYY-MM-DD load as they are, so check_plan
refuses them by their own subs `horizon` and `start` (CONTRACT 5.3, Q25), while a bool, a string or null in
`horizon_days` and a `start` that is not text are wrong JSON types (sub `file`, CONTRACT 14.2); one `replay_s_c3()`
result serves every replay plan of an invocation (same input, about 5 s saved per extra replay plan); a plan object
the loader refused is rendered from `report.refusal_report(None, refusal)` like any card whose plan has no hash, so
`render`'s guard covers it and its head shows the catalogue's `edge.none`; that card alone has no provenance lines,
because CONTRACT 14.1 loads a context only for each Plan, so none exists for it. Every other card the CLI refuses
itself (the precheck's: PARTIAL_CHUNK, the product refusals, STATE_UNUSABLE, LIMITS_UNSET; and an unknown
comparison's) passes `provenance=simulate.context_provenance(ctx)`, the provenance simulate's own refused cards
carry (spec 7.5 "with every report", CONTRACT 10.4), so Task 19's real-home STATE_UNUSABLE smoke card records the
code hash and that it is not signed (with no owner key there is no fingerprint to record).

Two readings depart from the letter of a contract text. Neither loosens a check; the executor records each as a
one-line ruling in the execution ledger when this task lands, and the plan header's "For spec rev 3.3" list carries
the first:
- One context per distinct stake, where CONTRACT 14.1 says "for each Plan: ctx = owner.load_context(...)". Within
  one invocation the moment, the positions and the compliance home are the same, so the contexts would be equal:
  `load_context` reads the owner log, the store, the snapshots and the code on disk, the precheck loop changes none
  of them, and its own snapshot write stores the same snapshot each time. It saves one `load_context` (0.6 to 2.8 s)
  per repeated stake; `test_each_plan_gets_its_own_inputs_in_one_comparison` pins the calls.
- `simulate.REFIT_B` swapped to 2 in `test_two_crypto_plans_one_comparison_one_seed` (save/restore). Q31 fixes the
  refit member at B = 20, which `odds_columns` tests, and CONTRACT 3.2 offers no swap for it. The swap saves about
  5 s on each of the test's four crypto simulations. It relies on the call-time reads named under Interfaces.

- [ ] **Step 1: Write the failing tests**

  Create `tests/odds_cli.py` with exactly this content (LF):

```python
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
    seam is called (the raising stubs stay) and with nothing written: not even the odds folder. A malformed id takes
    the same ValueError out of begin_run; the id rules are tests/odds_inputs.py's. A state file that does not parse
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
    is refused PARTIAL_CHUNK (exit 2) before anything else, and nothing is written. The three runs share one context
    (_reused_contexts)."""
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
    MULTI_LEG_UNSUPPORTED; both exit 2 and write nothing."""
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
```

- [ ] **Step 2: Run to verify it fails**

  Overlap check with the PowerShell tool (it must print nothing; otherwise wait and re-run it):

```powershell
Get-CimInstance Win32_Process -Filter "Name LIKE 'python%'" | Where-Object { $_.CommandLine -match 'run_all' } | Select-Object ProcessId,Name,CommandLine
```

  Then, from the repo root in Git Bash:

```bash
.venv/Scripts/python.exe -m tests.odds_acceptance odds_cli/
```

  Expected: a traceback and exactly one FAIL line (the aggregator turns the broken import into one entry), then the
  tail, exit code 1:

```
FAIL odds_cli/import ImportError: cannot import name 'run' from 'core.oddsdata' (C:\Users\whydi\OneDrive\Desktop\TRADEGEN\core\oddsdata\__init__.py)

0/1 passed, 1 failed, 0 not run
```

  Any other import error means an earlier task has not landed: stop and finish it first. The names are imported in
  file order, so the first missing one is named, for example `cannot import name 'inputs' from 'core.oddsdata'` (Task
  16), `cannot import name 'replay' from 'core.oddsdata'` (Task 17) or `cannot import name 'simulate' from
  'core.odds'` (Task 9). A missing `F.full_home` or `OF.ODDS_VENUES` is no import error (both are read when a test
  runs): it shows in Step 4 as `AttributeError` FAIL lines, and means Task 4 or Task 5 has not landed. Nor is a
  missing `simulate.context_provenance`: it shows in Step 4 as exit 4 with `crash: AttributeError: module
  'core.odds.simulate' has no attribute 'context_provenance'` in the precheck tests, and means Task 13 still names
  the helper `_context_provenance`.

- [ ] **Step 3: Implement**

  Create `core/oddsdata/run.py` with exactly this content (LF). It writes no file, so it needs no `checked_target`;
  its one clock read is in `main()`; its imports are the standard library, `core.compliance.model` and `owner`,
  `core.odds.plan`, `report` and `simulate`, and `core.oddsdata.bars`, `inputs` and `replay` (no `core.engine`, no
  `gate_ledger`, no `macro_artifacts`, nothing dynamic).

```python
"""The odds CLI (spec 4, 7.5 "Comparing plans"; O12, O15; Q12, Q15, Q45). Unsigned; it places no trade.

    python -m core.oddsdata.run --plan <plan.json> [--comparison <id>] [--paths N] [--refetch]

For each plan of the file: owner.load_context with the plan's stake as the equity (one context per distinct stake:
within one invocation the moment, the positions and the compliance home are the same, so the contexts would be
equal), then simulate.precheck, before any bar is loaded, any seam is called or the odds state is written. The plans
that pass form one comparison (inputs.begin_run, called once); each then gets its bars, its calendar and sessions
(KRX and US), the S_C3 replay (replay legs) and runs simulate.simulate. Every card goes through report.render, which
refuses its own banned output. Exit 0 when every plan is reported, 2 when any plan is refused (its named reason
printed), 4 on any exception ("crash: <type>: <text>" on stderr, nothing on stdout); --help prints the usage and
exits 0. It never writes the owner log. The default `now` of main() is the only wall clock in core/oddsdata."""
from __future__ import annotations

import argparse
import dataclasses
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path

from core.compliance import model, owner
from core.odds import plan, report, simulate
from core.oddsdata import bars, inputs, replay

_SCHEMA = "tradegen.odds_plan/1"
_PLAN_KEYS = frozenset({"name", "track", "stake_krw", "target_krw", "fx_krw_per_usd", "start", "horizon_days",
                        "fraction"})
_LEG_KEYS = frozenset({"venue", "symbol", "model", "bracket", "sizing", "edge_source", "assumed_p"})


class _Bad(ValueError):
    """A plan object the file format does not allow (CONTRACT 14.2)."""


def _no_constant(name: str):
    raise ValueError(f"{name} is not a JSON number")


def _no_repeats(pairs: list) -> dict:
    """A JSON object; a key given twice is refused, never silently overwritten."""
    obj = dict(pairs)
    if len(obj) != len(pairs):
        raise ValueError("a key appears twice in one object")
    return obj


def _obj(value, keys: frozenset, where: str) -> dict:
    if type(value) is not dict or set(value) != keys:
        raise _Bad(f"{where}: expected an object with exactly the keys {sorted(keys)}")
    return value


def _str(value, where: str) -> str:
    if type(value) is not str:
        raise _Bad(f"{where}: expected text")
    return value


def _num(value, where: str, *, optional: bool = False) -> float | None:
    """A JSON number as a float (an int is converted, a bool is no number); None only when `optional`."""
    if value is None and optional:
        return None
    if type(value) not in (int, float):
        raise _Bad(f"{where}: expected a number")
    try:
        return float(value)
    except OverflowError:
        raise _Bad(f"{where}: too large for a float") from None


def _day(text: str) -> date | str:
    """An exact YYYY-MM-DD as a date; any other text unchanged, for plan.check_plan to refuse (sub "start")."""
    try:
        day = date.fromisoformat(text)
    except ValueError:
        return text
    return day if day.isoformat() == text else text


def _leg(value, where: str) -> plan.Leg:
    obj = _obj(value, _LEG_KEYS, where)
    bracket = obj["bracket"]
    if bracket is not None:
        b = _obj(bracket, frozenset({"take_profit", "stop"}), f"{where}.bracket")
        bracket = plan.Bracket(take_profit=_num(b["take_profit"], f"{where}.bracket.take_profit"),
                               stop=_num(b["stop"], f"{where}.bracket.stop"))
    return plan.Leg(venue=_str(obj["venue"], f"{where}.venue"), symbol=_str(obj["symbol"], f"{where}.symbol"),
                    model=_str(obj["model"], f"{where}.model"), bracket=bracket,
                    sizing=_str(obj["sizing"], f"{where}.sizing"),
                    edge_source=_str(obj["edge_source"], f"{where}.edge_source"),
                    assumed_p=_num(obj["assumed_p"], f"{where}.assumed_p", optional=True))


def _plan(value, where: str) -> plan.Plan:
    """One plan object as a Plan whose values plan.check_plan judges. A `legs` list of one is that leg; a longer one
    stays a tuple, which check_plan refuses MULTI_LEG_UNSUPPORTED; an empty one is no readable plan. horizon_days
    stays the JSON number it is, so check_plan refuses a float (sub "horizon")."""
    many = type(value) is dict and "legs" in value
    obj = _obj(value, _PLAN_KEYS | {"legs" if many else "leg"}, where)
    if many:
        if type(obj["legs"]) is not list or not obj["legs"]:
            raise _Bad(f"{where}.legs: expected a non-empty list")
        legs = tuple(_leg(x, f"{where}.legs[{n}]") for n, x in enumerate(obj["legs"]))
        leg = legs[0] if len(legs) == 1 else legs
    else:
        leg = _leg(obj["leg"], f"{where}.leg")
    if type(obj["horizon_days"]) not in (int, float):
        raise _Bad(f"{where}.horizon_days: expected a number")
    fraction = _obj(obj["fraction"], frozenset({"kind", "value"}), f"{where}.fraction")
    return plan.Plan(name=_str(obj["name"], f"{where}.name"), track=_str(obj["track"], f"{where}.track"),
                     stake_krw=_num(obj["stake_krw"], f"{where}.stake_krw"),
                     target_krw=_num(obj["target_krw"], f"{where}.target_krw"),
                     fx_krw_per_usd=_num(obj["fx_krw_per_usd"], f"{where}.fx_krw_per_usd"),
                     start=_day(_str(obj["start"], f"{where}.start")), horizon_days=obj["horizon_days"], leg=leg,
                     fraction=plan.Fraction(kind=_str(fraction["kind"], f"{where}.fraction.kind"),
                                            value=_num(fraction["value"], f"{where}.fraction.value", optional=True)))


def load_plans(raw: bytes) -> list:
    """The plans of a plan file (CONTRACT 14.2) in file order: each a plan.Plan, or a plan.Refusal
    UNSUPPORTED_PRODUCT sub "file" for a plan object the format does not allow; one such Refusal for the whole file
    when it is not UTF-8 JSON (NaN, Infinity and repeated keys refused) holding exactly `schema`
    (tradegen.odds_plan/1) and a non-empty `plans` list. Only shapes and JSON types are checked here."""
    try:
        doc = json.loads(raw.decode("utf-8"), parse_constant=_no_constant, object_pairs_hook=_no_repeats)
        if type(doc) is not dict or set(doc) != {"schema", "plans"} or doc["schema"] != _SCHEMA:
            raise ValueError(f"expected exactly the keys schema ({_SCHEMA}) and plans")
        if type(doc["plans"]) is not list or not doc["plans"]:
            raise ValueError("plans: expected a non-empty list")
    except (ValueError, RecursionError) as exc:        # UnicodeDecodeError, JSONDecodeError; nesting too deep
        return [plan.Refusal(code="UNSUPPORTED_PRODUCT", sub="file", detail=f"plan file: {exc}")]
    out = []
    for n, value in enumerate(doc["plans"]):
        try:
            out.append(_plan(value, f"plans[{n}]"))
        except _Bad as exc:
            out.append(plan.Refusal(code="UNSUPPORTED_PRODUCT", sub="file", detail=str(exc)))
    return out


def _inputs(p: plan.Plan, ctx, now: datetime, begun: tuple, refetch: bool, replayed) -> plan.Inputs:
    """The injected data of a plan that passed the precheck: its bars, then (KRX and US) the signed calendar and
    the sessions, then (replay legs) the S_C3 replay. An unsigned calendar goes in as its error, never replaced by
    the shipped default, so simulate refuses CALENDAR_UNSIGNED (or CALENDAR_COVERAGE) by name."""
    _, inst = plan.instrument(p, ctx)
    market = plan.MARKET[(p.leg.venue, inst.section)]
    series = bars.load_leg(p, inst, now, refetch=refetch)
    cal, sha, error = (None, "", "") if market == "CRYPTO" else inputs.calendar_for(now)
    info = ((), (), (), "", error) if error else inputs.sessions(market, p.start, p.horizon_days, cal)
    return inputs.build_inputs(p, now, series=series, sessions_info=info, calendar_sha=sha,
                               replay=replayed if p.leg.edge_source == plan.REPLAY_SOURCE else None, run=begun)


def _run(args: argparse.Namespace, now: datetime) -> tuple[int, list[str]]:
    """(exit code, every plan's card in file order). A card refused here carries the context's provenance, as
    simulate's own refused cards do, except the card of a plan object the loader could not read: no context exists
    for it."""
    entries = load_plans(Path(args.plan).read_bytes())
    count, cards, refused, passing, contexts = len(entries), {}, False, [], {}
    for i, entry in enumerate(entries, start=1):
        if isinstance(entry, plan.Refusal):
            cards[i], refused = report.render(report.refusal_report(None, entry, index=i, count=count)), True
            continue
        stake = float(entry.stake_krw)
        if stake not in contexts:                                # Q11: the plan's stake is the equity
            contexts[stake] = owner.load_context(now, model.Positions(equity_krw=stake))
        ctx = contexts[stake]
        why = simulate.precheck(entry, ctx, args.paths)          # Q45: before any data, seam or state write
        if why is None:
            passing.append((i, entry, ctx))
        else:
            cards[i], refused = report.render(report.refusal_report(
                entry, why, index=i, count=count, provenance=simulate.context_provenance(ctx))), True
    if passing:
        typed = [p.leg.assumed_p for _, p, _ in passing if p.leg.edge_source == "assumed"]
        try:
            begun = inputs.begin_run(args.comparison, [plan.plan_hash(p) for _, p, _ in passing], typed)
        except ValueError as exc:                                # an id begin_run never issued; nothing written
            if args.comparison is None:
                raise
            why = plan.Refusal(code="UNSUPPORTED_PRODUCT", sub="comparison", detail=str(exc))
            for i, p, ctx in passing:
                cards[i] = report.render(report.refusal_report(p, why, index=i, count=count,
                                                               provenance=simulate.context_provenance(ctx)))
            refused = True
        else:
            replayed = None
            for i, p, ctx in passing:
                if p.leg.edge_source == plan.REPLAY_SOURCE and replayed is None:
                    replayed = replay.replay_s_c3()              # one replay (about 5 s) serves every replay plan
                rep = simulate.simulate(p, ctx, _inputs(p, ctx, now, begun, args.refetch, replayed),
                                        n_paths=args.paths)
                cards[i] = report.render(dataclasses.replace(rep, plan_index=i, plan_count=count))
                refused = refused or rep.refused is not None
    return (2 if refused else 0), [cards[i] for i in range(1, count + 1)]


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m core.oddsdata.run", exit_on_error=False,
                                     description="Print the odds of every plan in a plan file.")
    parser.add_argument("--plan", required=True, help="the plan file (schema tradegen.odds_plan/1)")
    parser.add_argument("--comparison", help="a comparison id an earlier run printed: run these plans on its seed")
    parser.add_argument("--paths", type=int, help="paths per column, a whole multiple of the chunk size")
    parser.add_argument("--refetch", action="store_true", help="download the price history again, not from the cache")
    return parser


def main(argv=None, *, now: datetime | None = None) -> int:
    """The CLI's exit code (module docstring). stdout and stderr switch to UTF-8 first, as tests/run_all.py does."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    if now is None:
        now = datetime.now(timezone.utc)
    args = None
    try:
        args = _parser().parse_args(argv)
        code, cards = _run(args, now)
        print("\n".join(cards), end="")          # every card ends in a newline
    except SystemExit as exc:              # with exit_on_error=False only --help leaves argparse this way
        if args is None and exc.code == 0:
            return 0
        print(f"crash: SystemExit: {exc.code}", file=sys.stderr)
        return 4
    except Exception as exc:               # Q15: any failure, argparse errors included, is a crash
        print(f"crash: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 4
    return code


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run to verify it passes**

  Run the overlap check of Step 2 (PowerShell tool; it must print nothing) before EACH Python command below. All run
  from the repo root in Git Bash.

  Overlap check, then the module, timed:

```bash
time .venv/Scripts/python.exe -m tests.odds_acceptance odds_cli/
```

  Expected: these twelve PASS lines (in this order), then `12/12 passed, 0 failed, 0 not run`, exit code 0:

```
PASS odds_cli/test_a_crash_exits_4_and_prints_no_card
PASS odds_cli/test_a_language_guard_hit_exits_4
PASS odds_cli/test_argument_errors_exit_4_and_help_exits_0
PASS odds_cli/test_each_plan_gets_its_own_inputs_in_one_comparison
PASS odds_cli/test_file_problems_refuse_each_plan_by_name
PASS odds_cli/test_krx_plans_need_the_signed_calendar
PASS odds_cli/test_load_plans_reads_the_file_format
PASS odds_cli/test_no_owner_key_refuses_before_any_data_or_write
PASS odds_cli/test_partial_chunk_is_refused_at_the_real_chunk
PASS odds_cli/test_the_main_block_exits_through_system_exit
PASS odds_cli/test_two_crypto_plans_one_comparison_one_seed
PASS odds_cli/test_unknown_comparison_ids_refuse_and_write_nothing
```

  The `real` time includes about 7 s of suite import. Measured in the sandbox on 2026-10-28, four runs of the twelve
  tests (drafts of Tasks 2 to 17 assembled with Task 4's fixtures and `calendar_in_force`, `-I -B`, the machine 31 to
  50% busy with other work): 9.1 to 18.9 s in all. With the machine about 50% busy the same tree took 18.6 s before
  this task's cuts and 14.4 to 16.0 s after them (one context reused across runs of one home, the KRX calendar signed
  into the home it already has, the malformed-id run left to `tests/odds_inputs.py`).
  `test_krx_plans_need_the_signed_calendar` took 2.9 to 5.3 s (one full_home, two contexts, the calendar fixture set
  and its sessions), `test_two_crypto_plans_one_comparison_one_seed` 2.2 to 5.3 s (full_home, one context, four
  simulations at REFIT_B 2), `test_each_plan_gets_its_own_inputs_in_one_comparison` 1.7 to 3.8 s,
  `test_unknown_comparison_ids_refuse_and_write_nothing` 1.1 to 2.5 s, and every other test under 0.6 s. One
  `owner.load_context` took 0.6 to 1.1 s in a signed home and 0.2 to 0.6 s in a bare one, `full_home` 0.8 to 1.5 s,
  and one crypto simulate 0.24 to 0.43 s at REFIT_B 2 and about 5 s at the real 20. On 2026-10-27 the machine was far
  busier and one `load_context` took 2.0 to 2.8 s; under that load the module can pass 20 s. Record the time under
  "Runs" in the execution ledger. A module over CONTRACT 3.4's 20 s for cli, or a test over Q13's 15 s, is G3-2's
  case: record it with its measured time and name the test. Over 40 s it is a ruling for the controller, who may
  split the module. Never shorten a test, lower a path count, swap another constant or skip a member to meet a
  budget.

  A failure here is read as follows. `test_two_crypto_plans_one_comparison_one_seed` failing on the rerun's
  assertion means something in a card depends on more than the plan and its comparison (look for a clock or a
  counter that is not the comparison's own in the provenance); failing on `c000003` means `begin_run` names a new id
  by something other than its run count (CONTRACT 12: `c{runs:06d}`); exiting 4 with `crash: ValueError: GARCH-t
  takes 1 fit, or 2 refits` means Task 14 builds its refits from a `REFIT_B` taken before the swap, and the test
  taking about 20 s longer than measured means neither Task 9 nor Task 14 reads it at call time (fix the reader,
  never the test). `test_unknown_comparison_ids_refuse_and_write_nothing` failing on the odds folder means
  `inputs.begin_run` created or wrote something before it raised: fix `begin_run` (CONTRACT 12: refuse first), never
  the test; failing on the crash line means the CLI caught begin_run's RuntimeError as a refusal (the `except` around
  it takes ValueError only, Q36). `test_each_plan_gets_its_own_inputs_in_one_comparison` failing on `equities` means
  the CLI loads a context per plan, or one for all plans, instead of one per distinct stake, or passes an equity other
  than the stake (Q11); failing on `len(memo)` (here or in the other tests) means it passes positions other than
  `model.Positions(equity_krw=stake)`. `test_no_owner_key_refuses_before_any_data_or_write` or
  `test_unknown_comparison_ids_refuse_and_write_nothing` failing on `prov.head` means the CLI builds that refusal
  card without `provenance=simulate.context_provenance(ctx)` (fix `_run`), or Task 13's helper returns `{}` for a
  sealed context (fix the helper). `test_load_plans_reads_the_file_format` failing on `loose` means the loader
  refuses a float `horizon_days` or a malformed `start` itself instead of leaving them to check_plan.
  `test_krx_plans_need_the_signed_calendar` exiting 2 with the CALENDAR_UNSIGNED sentence on its second run means
  `owner.calendar_in_force` or `inputs.calendar_for` misses an approval signed after the home was built (Tasks 4 and
  16); failing on the sha line means the card does not print the calendar sha prefix CONTRACT 10.1 asks for: fix
  `report.render`.

  Overlap check, then the odds guards, which now scan `run.py` (the clock only in `main`, the exact `__main__` block,
  no unchecked write, no forbidden or dynamic import, no raw banned word):

```bash
.venv/Scripts/python.exe -m tests.odds_acceptance odds_guards/
```

  Expected: no FAIL line and the same tail Task 1 recorded under "Runs" in the execution ledger (exit code 0). A
  failure names the file and the text: fix `run.py`, never the guard.

  Overlap check, then the whole odds suite as one Bash command with the Bash tool `timeout: 600000` (the suite takes
  about 3.3 minutes, past the 120 s default, and a killed command skips whatever is chained after it). The restore of
  the tracked results file follows `;`, so it runs whatever the suite did:

```bash
time KIS_APP_KEY='<unset>' KIS_APP_SECRET='<unset>' KIS_ACCOUNT_8='<unset>' KIS_ACCOUNT_PD='<unset>' UPBIT_ACCESS_KEY='<unset>' UPBIT_SECRET_KEY='<unset>' OKX_API_KEY='<unset>' OKX_API_SECRET='<unset>' OKX_API_PASSPHRASE='<unset>' OPENDART_API_KEY='<unset>' KRX_API_KEY='<unset>' FMP_API_KEY='<unset>' ANTHROPIC_API_KEY='<unset>' GS_CLIENT_ID='<unset>' GS_CLIENT_SECRET='<unset>' FINVIZ_API_KEY='<unset>' ALPACA_API_KEY='<unset>' ALPACA_SECRET_KEY='<unset>' FXMACRODATA_API_KEY='<unset>' .venv/Scripts/python.exe tests/run_all.py --suite odds; echo "exit $?"; git checkout -- qa/acceptance_results.json
```

  Expected: every `odds/...` row PASS, ending `287/287 passed, 0 failed, 0 not run; <path of
  qa/acceptance_results.json>` (exit code 0), in about 3.3 minutes (CONTRACT 3.4). The 287 is the drafts' count
  (G3-1), per module: guards 18, plan 25, costs 23, models 19, garch 17, simulate 18, locks 14, bold 12, report 41,
  pipeline 13, columns 14, bars 25, inputs 12, replay 24, cli 12. A run with 0 failed and another count passes: write
  its count and the reason in the ledger. Record the tail and the time under "Runs"; a total over that time is
  recorded with its time under G3-2, never cut.

  Overlap check, then the compliance suite (this task changes no compliance file; it must stay as Task 4 left it),
  as one Bash command with `timeout: 600000` and the restore after `;`:

```bash
KIS_APP_KEY='<unset>' KIS_APP_SECRET='<unset>' KIS_ACCOUNT_8='<unset>' KIS_ACCOUNT_PD='<unset>' UPBIT_ACCESS_KEY='<unset>' UPBIT_SECRET_KEY='<unset>' OKX_API_KEY='<unset>' OKX_API_SECRET='<unset>' OKX_API_PASSPHRASE='<unset>' OPENDART_API_KEY='<unset>' KRX_API_KEY='<unset>' FMP_API_KEY='<unset>' ANTHROPIC_API_KEY='<unset>' GS_CLIENT_ID='<unset>' GS_CLIENT_SECRET='<unset>' FINVIZ_API_KEY='<unset>' ALPACA_API_KEY='<unset>' ALPACA_SECRET_KEY='<unset>' FXMACRODATA_API_KEY='<unset>' .venv/Scripts/python.exe tests/run_all.py --suite compliance; echo "exit $?"; git checkout -- qa/acceptance_results.json
```

  Expected: the same tail Task 4 recorded under "Runs" (0 failed, the two REFDATA symlink rows NOT_RUN unless
  Developer Mode is on), exit code 0.

  Overlap check, then the core-wide scans (Global Constraints: every task that changes `core/`), one at a time with
  the overlap check before each:

```bash
.venv/Scripts/python.exe -m tests.macro_m0_harness
.venv/Scripts/python.exe -m tests.macro_tf_gov
.venv/Scripts/python.exe -m tests.macro_m7_ledger
.venv/Scripts/python.exe -m tests.macro_m8_forward
.venv/Scripts/python.exe -m tests.macro_m6_context
```

  Expected: each prints no FAIL line and ends with `0 failed` and exit code 0, with the passed and not-run counts Task
  1 recorded under "Runs".

  Overlap check, then the cockpit suite (test_08, test_09, test_16, test_18), as one Bash command with
  `timeout: 300000` and the restore after `;`:

```bash
KIS_APP_KEY='<unset>' KIS_APP_SECRET='<unset>' KIS_ACCOUNT_8='<unset>' KIS_ACCOUNT_PD='<unset>' UPBIT_ACCESS_KEY='<unset>' UPBIT_SECRET_KEY='<unset>' OKX_API_KEY='<unset>' OKX_API_SECRET='<unset>' OKX_API_PASSPHRASE='<unset>' OPENDART_API_KEY='<unset>' KRX_API_KEY='<unset>' FMP_API_KEY='<unset>' ANTHROPIC_API_KEY='<unset>' GS_CLIENT_ID='<unset>' GS_CLIENT_SECRET='<unset>' FINVIZ_API_KEY='<unset>' ALPACA_API_KEY='<unset>' ALPACA_SECRET_KEY='<unset>' FXMACRODATA_API_KEY='<unset>' .venv/Scripts/python.exe tests/run_all.py --suite cockpit; echo "exit $?"; git checkout -- qa/acceptance_results.json
```

  Expected: ends with `0 failed` and the counts Task 1 recorded, exit code 0.

  Then the text checks (no Python, so no overlap check; `run.py` is untracked, so plain `grep`, not `git grep`):

```bash
git status --short
grep -n -i -E "order_cash|order-cash|place_order|submit_order|create_order|replace_order|withdraw|transfer|sign_transaction|deposit_address|tttc0802u|tttc0801u|vttc0802u|private_key|seed_phrase|/v1/orders|/v1/withdraws|/v1/deposits|/api/v3/order|/sapi/v1/capital|/trading/|r18_research_log|r18_break_log|context_log/|tests\.reference|reference_mode|reference_only" core/oddsdata/run.py
grep -n -E "CANO|KIS_ACCOUNT|ACNT_PRDT_CD|0\.4 *[*x×]|__import__|import_module|importlib|runpy|exec\(|eval\(|gate_ledger|macro_artifacts|core\.engine|\.(post|put|delete|patch|request)\(" core/oddsdata/run.py
grep -n -E "datetime\.now|time\.|date\.today|utcnow" core/oddsdata/run.py
grep -c $'\r' core/oddsdata/run.py tests/odds_cli.py
```

  Expected: `git status --short` lists exactly `?? core/oddsdata/run.py`, `?? tests/odds_cli.py` and
  `?? docs/superpowers/plans/2026-10-24-odds-engine-execution-ledger.md`; the first two `grep` commands print
  nothing (exit code 1); the third prints exactly one line, `now = datetime.now(timezone.utc)` inside `main` (the
  only clock read); the CR count is `0` for both files (LF).

  Append the tails of these runs, one line each, under "Runs" in the execution ledger (LF; it stays untracked).
  Then add these two lines under "Drift rulings" there (departures from the CONTRACT, not from the merged main, so
  later drafters read the contract with them):
  - `Task 18: CONTRACT 14.1 the CLI loads one owner.load_context per distinct stake, not one per plan: within one invocation the moment, the positions and the compliance home are the same, so the contexts are equal.`
  - `Task 18: tests/odds_cli.py swaps simulate.REFIT_B to 2 in test_two_crypto_plans_one_comparison_one_seed (no CONTRACT 3.2 swap exists; Q31's B = 20 stays odds_columns' to test); Task 9's _run_paths and Task 14's _garch_member read REFIT_B at call time.`

- [ ] **Step 5: Commit**

```bash
git add core/oddsdata/run.py tests/odds_cli.py
git diff --cached --stat
git diff --cached --stat --ignore-cr-at-eol
```

  The two stat outputs must be identical (both files are new and LF). Then:

```bash
git commit -m "feat(odds): the odds CLI and its end-to-end runs" -m "Odds plan Task 18 (Q12, Q15, Q45): python -m core.oddsdata.run reads a plan file, prechecks every plan before any data or state write, runs one comparison per invocation on one seed and exits 0, 2 or 4." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

  The last `-m` is the `Co-Authored-By:` line of the model that writes the commit; this controller's is the one
  shown. Afterwards `git status --short` prints only
  `?? docs/superpowers/plans/2026-10-24-odds-engine-execution-ledger.md`.
