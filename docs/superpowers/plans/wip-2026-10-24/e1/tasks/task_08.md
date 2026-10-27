### Task 8: Live positions (`execution/positions.py`)

**Files:**
- Create: `execution/positions.py` (LF, UTF-8, no BOM)
- Create: `tests/execution_positions.py` (LF, UTF-8, no BOM)
- Test: `tests/execution_positions.py`

No existing file is edited, so this task has no DRIFT RULE anchor. `tests/execution_acceptance.py` (Task 1) already
lists `"execution_positions"` in MODULES and skips the module until this task creates it; the guards of
`tests/execution_guards.py` (Tasks 1 and 2) start scanning `execution/positions.py` the moment it exists.

**Interfaces:**
- Consumes:
  - Task 4 (`execution.snapshot`, contract section 8): `VENUES = ("kis", "upbit", "okx")`,
    `STALE_AFTER = timedelta(minutes=15)`; `Snapshot` (fields read here: `.utc` (str, `model.iso_utc` form), `.ok`,
    `.holdings` (`Mapping[str, Holding]`), `.cash` (`Mapping[str, float]`, fiat only, E16), `.prices_krw`
    (`Mapping[str, float]`)); `Holding(units, locked=0.0, avg_cost=None)` (`units` is the total held, locked
    included); tests only: `failed(venue, utc, error, *, flags=frozenset(), server_utc=None, clock_offset_s=None)`,
    `dump(snap) -> bytes`, `load(obj: dict) -> Snapshot`.
  - Task 4 (`tests/execution_fixtures.py`, contract 3.2): `NOW` (2026-10-24 00:00:00 UTC) and
    `snap(venue, **fields) -> Snapshot` (an ok snapshot stamped `model.iso_utc(NOW)`, every field overridable). Every
    test here passes `holdings`, `cash` and `prices_krw` explicitly, so nothing else of `snap`'s defaults matters.
  - `core.compliance.model` (repo, unchanged by E1 until Task 9): `Positions(equity_krw, holdings={}, shorts={},
    exposure={})`, `Exposure(held_krw, reservations={}, promised_sell_units={})`, `iso_utc(moment)`.
  - `core.compliance.owner._positions_problem(positions) -> str` (repo, owner.py `_positions_problem`; tests only):
    `""` for finite amounts >= 0 with `equity_krw > 0`.
- Produces (`execution/positions.py`, contract section 12):
  - `venue_value_krw(snap: Snapshot) -> float | None`: cash at `prices_krw` (KRW cash at 1.0, whatever
    `prices_krw` says about "KRW") plus each holding's `units` at `prices_krw[symbol]`; None as soon as a cash
    currency other than KRW or a held symbol has no price. A price for a symbol that is not held is ignored.
  - `live_positions(snapshots: Mapping[str, Snapshot], now: datetime) -> model.Positions | None`: None unless every
    venue of `VENUES` is present, `ok is True`, stamped with `0 <= now - utc <= STALE_AFTER` (exactly 15 minutes old
    counts; 15 minutes 1 second old, or any stamp after `now`, does not) and valued (not None, >= 0). Otherwise
    `Positions(equity_krw=<sum of the three
    values>, holdings={(venue, symbol): units for every holding of the three}, shorts={}, exposure={venue:
    Exposure(held_krw=<that venue's value>)})`; `reservations` and `promised_sell_units` stay empty (E2 adds them).
    Keys other than the three venues are ignored. Pure: it reads no clock (the caller passes `now`, E11), no file and
    no network.
  - Private helper (this module only): `_fresh(snap: Snapshot, now: datetime) -> bool`, the 15-minute rule; a `utc`
    that does not parse with `datetime.fromisoformat`, or parses without an offset, is not fresh (fail closed).
  - Later users: Task 11 (`checks.run_checks` FLOOR, DAILY_LOSS and OKX_CAP read `live.equity_krw` and
    `live.exposure["okx"].held_krw`; `checks.not_set(new, owner, limits, live)`; `checks.day_start(rows, now)` builds
    snapshots back from today's inquiry file with `snapshot.load` and calls `live_positions`, E34) and Task 12
    (`poll_once` step 5: `live = positions.live_positions(new, now)`).

**Plan decisions used:** E17 (positions fail closed), E16 (cash is settled fiat; coins, OKX USDT and USDC included,
are holdings), E4 (snapshots as records), E11 (no wall clock outside `poll.main`), E2 (imports: stdlib,
`core.compliance`, `execution.*`), E34 (the day start is rebuilt from read-back snapshots), E24 (live positions are
never passed to `load_context` in E1; the shape test below keeps them gate-ready for E2).

- [ ] **Step 1: Write the failing test(s)**

  First confirm the inputs. Overlap check with the PowerShell tool (it must print nothing; otherwise wait and run it
  again):

```powershell
Get-CimInstance Win32_Process -Filter "Name LIKE 'python%'" | Where-Object { $_.CommandLine -match 'run_all' } | Select-Object ProcessId,Name,CommandLine
```

  Then from the repo root in Git Bash:

```bash
test ! -e execution/positions.py && test ! -e tests/execution_positions.py && grep -c '"execution_positions"' tests/execution_acceptance.py
.venv/Scripts/python.exe -c "from execution import snapshot as S; from tests import execution_fixtures as EF; s = EF.snap('upbit', utc='2026-10-24T00:00:00Z', holdings={'BTC': S.Holding(units=1.0)}, cash={'KRW': 1.0}, prices_krw={'BTC': 2.0}); print(S.VENUES, S.STALE_AFTER, s.ok, s.utc, sorted(s.holdings), S.failed('kis', s.utc, 'kis: x').ok)"
```

  Expected: `1`, then `('kis', 'upbit', 'okx') 0:15:00 True 2026-10-24T00:00:00Z ['BTC'] False`. Any other answer
  (a file already there, a missing MODULES entry, a Task 4 name or `snap` override that does not work) is a drift
  ruling: stop and rule, and record the ruling in the execution ledger, before going on.

  Create `tests/execution_positions.py` with exactly this content:

```python
"""Live positions (E1 Task 8; contract section 12; E17): three venue snapshots -> model.Positions, fail closed.

Pure: no network, no clock, no file. Every snapshot is built in memory with `EF.snap`, its holdings, cash and prices
always given in full, at the prices the venue parsers derive from the contract 3.2 fixtures (spec 6).
"""
from __future__ import annotations

import json
import math
from datetime import timedelta

from core.compliance import model, owner
from execution import positions
from execution import snapshot as S
from tests import execution_fixtures as EF

# Spec 6 prices from the 3.2 fixtures: KIS 005930 at prpr 61000; KIS AAPL at now_pric2 210 times frst_bltn_exrt
# 1390.50, and USD cash at 1390.50; Upbit BTC at its KRW-BTC ticker 100,000,000; OKX BTC at OKX BTC-USDT 70000 times
# Upbit KRW-USDT 1400; OKX USDT and USDC at Upbit KRW-USDT 1400. The 3 USDC on OKX are added here (the fixtures hold
# none) so the test sees USDC counted.
USD_KRW = 1390.5
USDT_KRW = 1400.0
KIS_KRW = 20000.0 + 5.0 * USD_KRW + 1.0 * 61000.0 + 1.0 * (210.0 * USD_KRW)       # 379,957.5
UPBIT_KRW = 20000.0 + 0.0001 * 100000000.0                                          # 30,000
OKX_KRW = 10.0 * USDT_KRW + 3.0 * USDT_KRW + 0.0001 * (70000.0 * USDT_KRW)         # 28,000


def _kis(**changes) -> S.Snapshot:
    fields = {"holdings": {"005930": S.Holding(units=1.0, locked=0.0, avg_cost=60000.0),
                           "AAPL": S.Holding(units=1.0, locked=0.0, avg_cost=200.0)},
              "cash": {"KRW": 20000.0, "USD": 5.0},
              "prices_krw": {"005930": 61000.0, "AAPL": 210.0 * USD_KRW, "USD": USD_KRW}}
    return EF.snap("kis", **(fields | changes))


def _upbit(**changes) -> S.Snapshot:
    fields = {"holdings": {"BTC": S.Holding(units=0.0001, locked=0.0, avg_cost=100000000.0)},
              "cash": {"KRW": 20000.0},
              "prices_krw": {"BTC": 100000000.0, "USDT": USDT_KRW}}
    return EF.snap("upbit", **(fields | changes))


def _okx(**changes) -> S.Snapshot:
    fields = {"holdings": {"USDT": S.Holding(units=10.0), "USDC": S.Holding(units=3.0),
                           "BTC": S.Holding(units=0.0001)},
              "cash": {},
              "prices_krw": {"USDT": USDT_KRW, "USDC": USDT_KRW, "BTC": 70000.0 * USDT_KRW}}
    return EF.snap("okx", **(fields | changes))


def _three(**venues) -> dict:
    """The three fixture snapshots keyed by venue; a keyword replaces that venue's snapshot."""
    return {"kis": _kis(), "upbit": _upbit(), "okx": _okx()} | venues


def _close(a: float, b: float) -> bool:
    return math.isclose(a, b, rel_tol=1e-12, abs_tol=1e-9)


def _stamped(make, moment) -> S.Snapshot:
    return make(utc=model.iso_utc(moment))


def _drop(mapping, key) -> dict:
    return {k: v for k, v in mapping.items() if k != key}


def test_venue_value_prices_cash_and_holdings():
    assert _close(positions.venue_value_krw(_kis()), KIS_KRW), positions.venue_value_krw(_kis())
    assert _close(positions.venue_value_krw(_upbit()), UPBIT_KRW)
    assert _close(positions.venue_value_krw(_okx()), OKX_KRW)
    # KRW cash is valued at 1.0 with no "KRW" price; a held "KRW" price never changes that
    assert positions.venue_value_krw(_upbit(holdings={}, prices_krw={})) == 20000.0
    assert positions.venue_value_krw(_upbit(holdings={}, prices_krw={"KRW": 2.0})) == 20000.0
    assert positions.venue_value_krw(_okx(holdings={}, prices_krw={})) == 0.0
    # a price for a symbol that is not held is not counted
    assert _close(positions.venue_value_krw(_okx(prices_krw=dict(_okx().prices_krw, ETH=5000000.0))), OKX_KRW)


def test_venue_value_is_none_for_an_unpriced_symbol_or_currency():
    assert positions.venue_value_krw(_kis(prices_krw=_drop(_kis().prices_krw, "AAPL"))) is None
    assert positions.venue_value_krw(_kis(prices_krw=_drop(_kis().prices_krw, "USD"))) is None
    assert positions.venue_value_krw(_upbit(prices_krw={"USDT": USDT_KRW})) is None
    assert positions.venue_value_krw(_okx(prices_krw={})) is None          # Upbit failed: OKX has no usdt_krw


def test_equity_is_the_sum_of_the_three_venue_values():
    live = positions.live_positions(_three(), EF.NOW)
    assert isinstance(live, model.Positions), live
    assert _close(live.equity_krw, KIS_KRW + UPBIT_KRW + OKX_KRW), live.equity_krw
    assert _close(live.equity_krw, sum(positions.venue_value_krw(s) for s in _three().values()))


def test_held_krw_per_venue_includes_okx_usdt_and_usdc_and_nothing_is_reserved():
    live = positions.live_positions(_three(), EF.NOW)
    assert set(live.exposure) == {"kis", "upbit", "okx"}, live.exposure
    for venue, want in (("kis", KIS_KRW), ("upbit", UPBIT_KRW), ("okx", OKX_KRW)):
        exposure = live.exposure[venue]
        assert isinstance(exposure, model.Exposure), exposure
        assert _close(exposure.held_krw, want), (venue, exposure.held_krw)
        assert dict(exposure.reservations) == {} and dict(exposure.promised_sell_units) == {}, exposure
    assert _close(live.exposure["okx"].held_krw - 0.0001 * 70000.0 * USDT_KRW, 13.0 * USDT_KRW)
    assert dict(live.shorts) == {}, live.shorts


def test_holdings_are_keyed_by_venue_and_symbol():
    live = positions.live_positions(_three(), EF.NOW)
    assert dict(live.holdings) == {("kis", "005930"): 1.0, ("kis", "AAPL"): 1.0, ("upbit", "BTC"): 0.0001,
                                   ("okx", "USDT"): 10.0, ("okx", "USDC"): 3.0, ("okx", "BTC"): 0.0001}, live.holdings
    # locked units are part of units (Holding.units is the total held); cash currencies are not holdings
    locked_btc = _upbit(holdings={"BTC": S.Holding(units=0.0003, locked=0.0002)})
    locked = positions.live_positions(_three(upbit=locked_btc), EF.NOW)
    assert locked.holdings[("upbit", "BTC")] == 0.0003, locked.holdings
    assert _close(locked.exposure["upbit"].held_krw, 20000.0 + 0.0003 * 100000000.0), locked.exposure
    assert not {k for k in live.holdings if k[1] in ("KRW", "USD")}, live.holdings


def test_a_missing_or_failed_venue_gives_none():
    assert positions.live_positions({}, EF.NOW) is None
    for venue in S.VENUES:
        assert positions.live_positions(_drop(_three(), venue), EF.NOW) is None, venue
        down = S.failed(venue, model.iso_utc(EF.NOW), f"{venue}: test")
        assert positions.live_positions(_three(**{venue: down}), EF.NOW) is None, venue
    # an extra key is ignored; the three venues decide
    assert positions.live_positions(_three() | {"binance": _upbit()}, EF.NOW) == positions.live_positions(
        _three(), EF.NOW)


def test_a_stale_or_future_snapshot_gives_none_and_15_minutes_still_counts():
    makers = {"kis": _kis, "upbit": _upbit, "okx": _okx}
    for venue, make in makers.items():
        edge = _stamped(make, EF.NOW - timedelta(minutes=15))
        stale = _stamped(make, EF.NOW - timedelta(minutes=15, seconds=1))
        future = _stamped(make, EF.NOW + timedelta(seconds=1))
        assert positions.live_positions(_three(**{venue: edge}), EF.NOW) is not None, venue
        assert positions.live_positions(_three(**{venue: stale}), EF.NOW) is None, venue
        assert positions.live_positions(_three(**{venue: future}), EF.NOW) is None, venue
    # the same rule seen from `now`: all three stamped at NOW
    assert positions.live_positions(_three(), EF.NOW + timedelta(minutes=15)) is not None
    assert positions.live_positions(_three(), EF.NOW + timedelta(minutes=15, seconds=1)) is None
    assert positions.live_positions(_three(), EF.NOW - timedelta(seconds=1)) is None


def test_an_unreadable_or_offset_less_stamp_gives_none():
    for utc in ("", "not a time", "2026-10-24T00:00:00"):
        assert positions.live_positions(_three(upbit=_upbit(utc=utc)), EF.NOW) is None, utc


def test_an_unpriced_holding_or_currency_gives_none():
    eth = dict(_okx().holdings, ETH=S.Holding(units=0.01))                 # OKX prices BTC, USDT and USDC only
    for case in (_three(kis=_kis(prices_krw=_drop(_kis().prices_krw, "AAPL"))),
                 _three(kis=_kis(prices_krw=_drop(_kis().prices_krw, "USD"))),
                 _three(upbit=_upbit(prices_krw={"USDT": USDT_KRW})), _three(okx=_okx(holdings=eth)),
                 _three(okx=_okx(prices_krw={}))):
        assert positions.live_positions(case, EF.NOW) is None, case


def test_a_negative_venue_value_gives_none_and_zero_counts():
    assert positions.live_positions(_three(upbit=_upbit(holdings={}, cash={"KRW": -1.0})), EF.NOW) is None
    # a negative line inside a venue worth more than 0 still counts: the rule is the venue's value
    owed = positions.live_positions(_three(kis=_kis(cash={"KRW": -1000.0, "USD": 5.0})), EF.NOW)
    assert owed is not None and _close(owed.exposure["kis"].held_krw, KIS_KRW - 21000.0), owed
    empty = positions.live_positions(_three(okx=_okx(holdings={}, prices_krw={})), EF.NOW)
    assert empty is not None and empty.exposure["okx"].held_krw == 0.0, empty
    assert not {k for k in empty.holdings if k[0] == "okx"}, empty.holdings


def test_snapshots_read_back_from_the_inquiry_log_give_the_same_positions():
    back = {venue: S.load(json.loads(S.dump(snap))) for venue, snap in _three().items()}
    assert positions.live_positions(back, EF.NOW) == positions.live_positions(_three(), EF.NOW)


def test_live_positions_pass_the_gate_positions_check():
    live = positions.live_positions(_three(), EF.NOW)
    assert owner._positions_problem(live) == "", owner._positions_problem(live)
```

- [ ] **Step 2: Run to verify it fails**

  Overlap check with the PowerShell tool (the block of Step 1; it must print nothing). Then from the repo root in
  Git Bash:

```bash
.venv/Scripts/python.exe -m tests.execution_acceptance execution_positions/
```

  Expected: a traceback, then

```
FAIL execution_positions/import ImportError: cannot import name 'positions' from 'execution' (C:\Users\whydi\OneDrive\Desktop\TRADEGEN\execution\__init__.py)

0/1 passed, 1 failed, 0 not run
```

  and exit code 1 (the aggregator turns the module's failed import into its one `execution_positions/import` entry).

- [ ] **Step 3: Implement**

  Create `execution/positions.py` with exactly this content (no `getattr`, no clock, no `open`, no attribute
  assignment: the guards of contract 0.5 scan it):

```python
"""Live positions (E1 spec 6 "Positions (P19)"; plan decision E17): the latest snapshot of each venue ->
model.Positions, or None.

Pure: no clock (the caller passes `now`), no file, no network. Fail closed: one missing, failed, stale or unpriced
venue, or one worth less than nothing, gives None for the whole set, never partial positions. Every price is the
venue snapshot's own `prices_krw` (spec 6): KIS domestic at `prpr`, KIS overseas at `now_pric2` times the
inquire-present-balance rate, Upbit at its ticker, OKX BTC at OKX BTC-USDT times Upbit KRW-USDT, OKX USDT and USDC
at Upbit KRW-USDT.
"""
from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timedelta

from core.compliance import model
from execution.snapshot import STALE_AFTER, VENUES, Snapshot


def venue_value_krw(snap: Snapshot) -> float | None:
    """Cash plus holdings at `snap.prices_krw` (KRW cash at 1.0); None when a currency or symbol has no price."""
    total = 0.0
    for currency, amount in snap.cash.items():
        price = 1.0 if currency == "KRW" else snap.prices_krw.get(currency)
        if price is None:
            return None
        total += amount * price
    for symbol, holding in snap.holdings.items():
        price = snap.prices_krw.get(symbol)
        if price is None:
            return None
        total += holding.units * price
    return total


def _fresh(snap: Snapshot, now: datetime) -> bool:
    """0 <= now - snap.utc <= STALE_AFTER; a stamp that does not parse or has no offset is not fresh."""
    try:
        stamp = datetime.fromisoformat(snap.utc)
    except (TypeError, ValueError):
        return False
    return stamp.utcoffset() is not None and timedelta(0) <= now - stamp <= STALE_AFTER


def live_positions(snapshots: Mapping[str, Snapshot], now: datetime) -> model.Positions | None:
    """model.Positions from one ok, fresh, fully priced snapshot per venue of VENUES, none worth less than 0; else
    None (E17). `reservations` and `promised_sell_units` stay empty (E2 adds them)."""
    values = {}
    for venue in VENUES:
        snap = snapshots.get(venue)
        if snap is None or snap.ok is not True or not _fresh(snap, now):
            return None
        value = venue_value_krw(snap)
        if value is None or value < 0:
            return None
        values[venue] = value
    return model.Positions(
        equity_krw=sum(values.values()),
        holdings={(venue, symbol): holding.units
                  for venue in VENUES for symbol, holding in snapshots[venue].holdings.items()},
        shorts={},
        exposure={venue: model.Exposure(held_krw=value) for venue, value in values.items()})
```

- [ ] **Step 4: Run to verify it passes**

  Run the overlap check of Step 1 (PowerShell tool; it must print nothing) before EACH of the three Python commands
  below. All run from the repo root in Git Bash.

  Overlap check, then:

```bash
.venv/Scripts/python.exe -m tests.execution_acceptance execution_positions/
```

  Expected: these 12 lines, in this order, then `12/12 passed, 0 failed, 0 not run` (exit code 0):

```
PASS execution_positions/test_a_missing_or_failed_venue_gives_none
PASS execution_positions/test_a_negative_venue_value_gives_none_and_zero_counts
PASS execution_positions/test_a_stale_or_future_snapshot_gives_none_and_15_minutes_still_counts
PASS execution_positions/test_an_unpriced_holding_or_currency_gives_none
PASS execution_positions/test_an_unreadable_or_offset_less_stamp_gives_none
PASS execution_positions/test_equity_is_the_sum_of_the_three_venue_values
PASS execution_positions/test_held_krw_per_venue_includes_okx_usdt_and_usdc_and_nothing_is_reserved
PASS execution_positions/test_holdings_are_keyed_by_venue_and_symbol
PASS execution_positions/test_live_positions_pass_the_gate_positions_check
PASS execution_positions/test_snapshots_read_back_from_the_inquiry_log_give_the_same_positions
PASS execution_positions/test_venue_value_is_none_for_an_unpriced_symbol_or_currency
PASS execution_positions/test_venue_value_prices_cash_and_holdings
```

  Overlap check, then the static guards, whose scans now include `execution/positions.py` (import allowlist, clock,
  writes, verbs, the transport-only path, raw bans):

```bash
.venv/Scripts/python.exe -m tests.execution_acceptance execution_guards/
```

  Expected: every line `PASS`, ending `N/N passed, 0 failed, 0 not run` (exit code 0), with N the count Task 7's
  last run of `execution_guards/` printed (this task adds no guard test). A failure names the offending file and
  text: fix `execution/positions.py`, never the guard.

  Overlap check, then the repo-wide read-only guards over the widened `runtime_py()` (T-RO-01, test_08, test_09;
  this calls the test functions directly, starts no `tests/run_all.py` and writes nothing):

```bash
.venv/Scripts/python.exe -c "from tests.macro_m0_harness import test_t_ro_01_no_order_cancel_withdrawal_or_transfer_path as t, test_t_ro_01_orders_module_reached_only_through_the_engine as u; from tests.acceptance import test_08_no_broker_order_path as t8, test_09_no_account_credentials_requested as t9; t(); u(); t8(); t9(); print('T-RO-01 ok')"
```

  Expected: `T-RO-01 ok` (exit code 0).

  Then the raw-text checks (git only, no overlap check needed):

```bash
git grep --untracked -n -i -E "order_cash|order-cash|place_order|submit_order|tttc0802u|tttc0801u|vttc0802u|private_key|seed_phrase|/v1/|/uapi/|/api/v|append_system_entry|system_halt|system_disarm|x-simulated-trading|openapivts|context_log/|reference_mode|0\.4 \*" -- execution/positions.py tests/execution_positions.py
git grep --untracked -n -E "CANO|KIS_ACCOUNT|ACNT_PRDT_CD|datetime\.now|date\.today|time\.time|monotonic|open\(" -- execution/positions.py tests/execution_positions.py
```

  Expected: both print nothing (exit code 1).

- [ ] **Step 5: Commit**

```bash
git add execution/positions.py tests/execution_positions.py
git diff --cached --stat
git diff --cached --stat --ignore-cr-at-eol
```

  The two stat outputs must be identical (both files are new and LF). Then, with the trailer naming the model that
  writes the commit (for example `Claude Opus 5.5` or `Claude Sonnet 5.5`):

```bash
git commit -m "feat(execution): live positions from the three venue snapshots, fail closed" -m "Task 8: execution/positions.py (venue_value_krw, live_positions; spec 6 P19, E17) and tests/execution_positions.py." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
