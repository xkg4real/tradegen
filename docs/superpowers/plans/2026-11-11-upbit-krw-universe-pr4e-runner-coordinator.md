# Upbit KRW universe PR 4e: runner and coordinator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run a universe launch profile end to end inside the existing runner and coordinator: a buy needs the
slot's allow-list, the snapshot in force and the session's bound odds batch; a second sell of one coin is blocked
instead of stopping the runner; the coordinator reads the slot's flags and tickers, records every slot with its
universe inputs, chooses and renews the trade coin only while flat, raises the section 7 events, queues toasts on
one background thread, shows the universe status fields, prepares a session with an odds batch, and the console and
rehearsal are wired to it. Fixed KRW-BTC profiles keep today's behaviour.

**Architecture:** `execution_launch/runner.py` gains `entry_allow` on `tick` and `run`, three universe checks that
return `blocked`, a same-coin sell guard, the pure `active`, `dust` and `flat_in` helpers, a flat re-check on a
cross-coin renewal and the batch form of `prepare_launch_session`. `execution_launch/coordinator.py` keeps the fixed
`_slot` and adds `_universe_slot` (section 7's nine steps), `_holdings` and `_universe_monitor` after each
`_publish`, `_events`, `_vanish`, `_after_tick`, `_slot_missed`, a lock-free `_disarm_locked`, `odds_batch`, the pure
helpers `held_coins`, `universe_state`, `choose_trade_coin` and `slot_allow`, and ten status fields. A new
`execution_launch/toast_queue.py` holds the toast worker; `core.compliance.alerts.toast` is its public seam.
`LiveHistory.decided_symbol` exposes the latest decision's coin. `tools/owner/launch.py` adds the `odds` command and
the status keys; `tools/owner/rehearsal.py` passes the coin at read time and wires the slot source. A coordinator is
a universe coordinator exactly when `profile.universe_rule_sha256 is not None`.

**Tech Stack:** Python 3.13 (venv at `TRADEGEN_PR9/.venv`, read-only), stdlib `collections`, `dataclasses`,
`datetime`, `decimal`, `threading`, `types`. The repo's suite runner (no pytest) through the index's `focus`
function. No new dependency.

**Spec:** [2026-11-11-upbit-krw-universe-design.md](../specs/2026-11-11-upbit-krw-universe-design.md), section 7
(terms, trade-coin choice, slot unit, events, terms failures, buy allow-list, sell guard), section 9 (console `odds`,
preparation with a batch), section 10 (book and terms read by coin, renewal with `allow_symbol_change` after the
flat check, 72-hour window bound, buy cap), section 12 (coordinator units and status fields, missed slot, window
end), section 13 (rehearsal coverage) and section 15 (coordinator toasts).

Line numbers below are fd85850. PRs 4a to 4d change several of these files first, so locate each edit by the quoted
text, not by the number.

## Global Constraints

All constraints in the index apply: [2026-11-11-upbit-krw-universe-index.md](2026-11-11-upbit-krw-universe-index.md)
(base, one branch and one PR, owner merges, public repository, no new dependency, offline tests, no signing or arming,
byte-exact line endings, never `sed -i`, commit and PR trailers).

PR-specific constraints, quoted from the spec:

- Section 7: "If the chosen coin differs from `profile.symbol`, the coordinator checks "flat in `profile.symbol`"
  before anything else. Not flat is a normal outcome: no renewal is issued and nothing is raised."
- Section 7: "A failed or stale read marks the book `unavailable` instead of refusing the slot."
- Section 7: "`record_slot`, in its own `try`. A failure is recorded in `reasons`; it never skips step 8."
- Section 7: "The events below, each in its own `try`. A failure sets a reason, a status field and a toast, and never
  aborts the unit."
- Section 7: "With no book the tick is skipped with `COORDINATOR_NO_TRADE_BOOK`; this is not a refusal, and the row
  is still recorded. A failed record skips the tick"
- Section 7: "While no coin is held, a terms read, parse or renewal failure never sets `_terms_blocked` and never
  refuses the slot. It sets the buy block `TERMS_TARGET_UNAVAILABLE`, and the row records it."
- Section 7: "For a universe profile a buy needs `profile.symbol` in `entry_allow`, and a missing `entry_allow` blocks
  every buy." "Every failure is a `blocked` result, never a runner stop. Strategy sells and `submit_exit` never look
  at the allow-list."
- Section 7: "`Runner.tick` refuses a sell (status `blocked`, `RUNNER_OUTSTANDING_ORDERS`, no stop) while a sell of
  the same symbol is in an active state."
- Section 9: "It runs on the console thread, never under the coordinator's work lock and never inside a unit, so
  slots keep running."
- Section 10: "The coordinator passes `True` only for a universe profile and only after its flat check (section 7)."
  "The coordinator refuses to construct a universe window longer than 72 hours."
- Section 12: "The coordinator then sets the sticky field `window_ended_missed_slot` and raises a red toast if a coin
  is held."
- Section 13: "Rehearsal never prepares or arms a session"
- Section 15: "the coordinator never calls it inside a unit: it queues each toast for one background thread and
  keeps the once-per-window or once-per-day dedupe itself"
- From the code: `tests/launch_coordinator.py:689-727` pins the coordinator source: ASCII only; module-level nodes
  only the docstring, imports, plain assignments, functions and classes; no name `Thread`, `sleep`, `signal`,
  `atexit`, `environ`, `compare_and_set` or `initialize_reviewed_head`; no import of `execution_accounts.quotes`,
  `execution.transport`, `execution_orders.transport` or `execution_orders.upbit`. Construction stays inert
  (`tests/launch_coordinator.py:599-604`): the toast worker starts on the first toast, never in `__init__`.
- From the code: `tests/launch_guards.py` `problems()` treats `.replace(x)` with exactly one positional argument as
  a file write. Use `dataclasses.replace` with keywords only.

## Running tests

Copied from the index (define once per shell):

```bash
PY="$HOME/OneDrive/Desktop/TRADEGEN_PR9/.venv/Scripts/python.exe"
export TRADEGEN_RUNS_DIR="${SCRATCH:?set SCRATCH to your session scratchpad directory}/runs_scratch"
focus() { "$PY" -X utf8 -c "import importlib,sys; from tests.run_all import run; s=importlib.import_module('tests.'+sys.argv[1]+'_acceptance'); rows=run([(n,f) for n,f in s.tests() if sys.argv[2] in n]); sys.exit(0 if rows and not any(r['status']=='FAIL' for r in rows) else 1)" "$@"; }
```

`focus <suite> <module>/<test_name>` runs matching tests. A failing test prints `FAIL <module>/<test> <Type>: <text>`.

## Contract notes (deviations and additions to the index's PR 4e contract)

- `Runner.run` keeps the code's parameter name `timestamps` (the contract writes `ticks`); `entry_allow` is added as
  the contract states, on `run` and `tick`.
- `Runner.refresh_instrument_rules(renewal, *, now, account=None)` and the code `RUNNER_UNIVERSE_NOT_FLAT` (spec
  section 10, "re-checks the same flat verdict"). New module functions in `runner.py`: `active(state)`,
  `dust(position, minimum)`, `flat_in(symbol, positions, states, *, asof, minimum)`.
- `prepare_launch_session(..., universe_batch=None)` and `Coordinator.prepare(..., universe_batch=None)`; the
  universe template check reuses `RUNNER_SELECTED_PLAN_SCOPE_MISMATCH`.
- `LiveHistory.decided_symbol() -> str | None`, read from PR 4d's `_state.held` (PR 4d's `PaperDecision` has no coin).
- Coordinator keywords `slot_source`, `program` (read by attribute: `kind`, `universe_rule_sha256`,
  `max_candidates`) and `toast`; constants `UNIVERSE_KIND`, `UNIVERSE_WINDOW_MAX`, `PRICE_AGE`; pure helpers
  `held_coins`, `universe_state`, `choose_trade_coin`, `slot_allow`. The 72-hour bound reuses
  `COORDINATOR_WINDOW_INVALID`.
- `_disarm_locked(*, reason, code, republish)` instead of `_disarm_locked(reason)`: `code` carries
  `COORDINATOR_UNIVERSE_DISARM`, `republish=False` inside a slot unit whose frame is already on the board.
- `Coordinator.odds_batch(template, read_bars)`, refusals `COORDINATOR_UNIVERSE_REQUIRED`, `UNIVERSE_NO_SNAPSHOT`
  (reused as a refusal) and `COORDINATOR_ODDS_BATCH_FAILED`.
- Codes `COORDINATOR_HISTORY_REFUSED` (record failure without a fixed code), `COORDINATOR_EVENT_FAILED`; event codes
  `UNIVERSE_MARKET_VANISHED`, `UNIVERSE_OTHER_COIN_WARNING`, `UNIVERSE_HELD_FLAG_UNCERTAIN`. The last is also a
  buy-block reason ("No buy at this slot"), beyond the contract's list.
- The tick's `entry_allow` is `LiveHistory.recorded_allow`, not the coordinator's own list (PR 4d: after a size
  fallback the recorded list is empty). `record_slot` also gets PR 4d's `tick_size` and `positions`.
- PR 4d contract, kept: `HISTORY_BOOK_OFF_TICK` and `HISTORY_BOOK_MARKET_MISMATCH` refuse before anything is written,
  so `_universe_slot` calls `record_slot` once more with `book=None` in the same slot. That slot is recorded without
  book fields and its tick is skipped with `COORDINATOR_NO_TRADE_BOOK`. Any other refusal, or a refusal of the
  retry, misses the slot and ends the window (Tasks 9 and 10).
- The v2 buy cap (PR 4c `within_buy_cap`) is applied to the trade coin's last terms observation only; the allow-list
  only ever matters for `profile.symbol`.
- New module `execution_launch/toast_queue.py` (`ToastQueue`). `OwnerRuntime.odds()`, console command `odds` and ten
  status keys. Rehearsal `_SlotSource`, `_QuoteSource.read(symbol=None)`, `_TermsSource.read(symbol=None)`.

## File Structure

| File | Change | Task |
|---|---|---|
| `core/compliance/alerts.py` | public `toast(title, body)` over `_toast` | 1 |
| `execution_launch/toast_queue.py` (new) | `ToastQueue`: one lazy daemon worker, FIFO, failures dropped | 1 |
| `tests/compliance_cli.py` | wrapper test | 1 |
| `tests/launch_toast_queue.py` (new) | queue tests | 1 |
| `tests/launch_guards.py` | `CLEAN` pin for the toast import | 1 |
| `tests/launch_acceptance.py` | `MODULES` entries | 1, 2, 5 |
| `execution_launch/runner.py` | allow-list, snapshot and batch checks, sell guard, flat helpers, flat re-check, batch preparation | 2, 3, 4 |
| `tests/launch_runner_universe.py` (new) | runner tests | 2, 3, 4 |
| `execution_launch/coordinator.py` | construction, status, units, events, toasts, odds, preparation | 5 to 12 |
| `execution_launch/live_history.py` | `decided_symbol` | 7 |
| `tests/launch_coordinator_universe.py` (new) | coordinator tests | 5 to 12 |
| `tools/owner/launch.py` | `odds`, batch into `prepare`, status keys | 12 |
| `tools/owner/rehearsal.py` | coin at read time, `_SlotSource`, wiring | 13 |
| `tests/launch_owner_rehearsal.py` | adapter test | 13 |

---

### Task 1: Public toast seam and the toast queue

**Files:**
- Modify: `core/compliance/alerts.py`, insert after line 226 (the end of `_toast`, `return done.returncode == 0`)
- Create: `execution_launch/toast_queue.py`
- Modify: `tests/launch_guards.py`, insert after line 388 (`"getattr(protocol, 'bar_seconds', None)",
  "getattr(history, 'record_slot', None)",`)
- Modify: `tests/launch_acceptance.py:9-15` (`MODULES`)
- Test: `tests/compliance_cli.py`, insert before line 704 (`def test_alerts_main_send_toasts_once_and_logs():`);
  `tests/launch_toast_queue.py` (new)

**Interfaces:**
- Consumes: `alerts._toast(title, body) -> bool` (`core/compliance/alerts.py:216-226`).
- Produces: `core.compliance.alerts.toast(title: str, body: str) -> bool`;
  `execution_launch.toast_queue.ToastQueue(show: Callable[[str, str], bool])` with `put(title, body) -> None`,
  private `_thread` (the running worker or `None`).

- [ ] **Step 1: Cut the branch and check the PR 4a to 4d names**

Define `PY`, `TRADEGEN_RUNS_DIR` and `focus` as "Running tests" shows. Then:

```bash
git fetch origin
git switch -c claude/universe-pr4e-runner-coordinator origin/main
grep -n "def registered_batch\|def run_batch" execution_control/universe_odds.py
grep -n "universe_batch" execution_control/session.py | head -3
grep -n "universe: Universe | None" execution_control/risk.py
grep -n "side: str | None\|symbol: str | None\|updated_at: datetime | None" execution_control/controller.py
grep -n "allow_symbol_change" execution_launch/instrument_refresh.py | head -2
grep -n "def within_buy_cap\|def read(self, symbol" execution_accounts/instrument_terms.py
grep -n "class UniverseSlotSource\|class FlagRead\|class TickerRead\|def daily_bars" execution_accounts/universe.py
grep -n "class SlotUniverse\|self.recorded_allow = \|self._universe = \|self._state = " execution_launch/live_history.py
grep -n "universe_rule_sha256" execution_launch/profile.py execution_launch/program.py | head -4
```

Expected: every command prints at least one line. The branch must contain PR 4a and PR 4d (and so PRs 1 to 4c). If
any command prints nothing, stop and report which name is missing; do not invent it.

- [ ] **Step 2: Write the failing tests**

In `tests/compliance_cli.py`, insert before `def test_alerts_main_send_toasts_once_and_logs():` (fd85850 line 704):

```python
def test_toast_wrapper_calls_the_seam_and_never_powershell_itself():
    calls = []
    with _patched(alerts, "_toast", lambda title, body: calls.append((title, body)) or True), \
            _patched(subprocess, "run", _boom):
        assert alerts.toast("TITLE-1", "BODY-2") is True
    assert calls == [("TITLE-1", "BODY-2")]
    with _patched(alerts, "_toast", lambda title, body: False):
        assert alerts.toast("t", "b") is False


```

Create `tests/launch_toast_queue.py`:

```python
"""The coordinator's toast queue (universe spec section 15): one lazy daemon worker, FIFO, never blocking put."""
from __future__ import annotations

import threading

from execution_launch.toast_queue import ToastQueue


def _join(queue):
    worker = queue._thread
    if worker is not None:
        worker.join(5)
        assert not worker.is_alive()


def test_put_returns_while_a_toast_is_showing_and_order_is_kept():
    entered, release, shown = threading.Event(), threading.Event(), []

    def show(title, body):
        shown.append((title, body))
        if len(shown) == 1:
            entered.set()
            release.wait(5)
        return True
    queue = ToastQueue(show)
    queue.put("t1", "b1")
    assert entered.wait(5)
    queue.put("t2", "b2")                       # returns although the first toast is still showing
    assert shown == [("t1", "b1")]
    release.set()
    _join(queue)
    assert shown == [("t1", "b1"), ("t2", "b2")]


def test_a_failing_toast_is_dropped_and_the_next_one_still_shows():
    shown, gate = [], threading.Event()

    def show(title, body):
        gate.wait(5)
        if title == "bad":
            raise RuntimeError("powershell missing")
        shown.append(title)
        return True
    queue = ToastQueue(show)
    queue.put("bad", "x")
    queue.put("good", "y")
    gate.set()
    _join(queue)
    assert shown == ["good"]


def test_construction_starts_no_thread_and_the_worker_ends_when_idle():
    before, shown = threading.active_count(), []
    queue = ToastQueue(lambda title, body: shown.append(title) or True)
    assert threading.active_count() == before and queue._thread is None
    queue.put("a", "b")
    _join(queue)
    assert queue._thread is None and shown == ["a"]
    queue.put("c", "d")
    _join(queue)
    assert queue._thread is None and shown == ["a", "c"]
```

In `tests/launch_acceptance.py` `MODULES` (fd85850 lines 9-15), add `"launch_toast_queue"` as the last item, after
every module PRs 4a to 4d added.

In `tests/launch_guards.py`, insert after fd85850 line 388 (inside `CLEAN`):

```python
    "from core.compliance.alerts import toast",
```

- [ ] **Step 3: Run the tests and see them fail**

```bash
focus compliance compliance_cli/test_toast_wrapper
focus launch launch_toast_queue/
focus launch launch_guards/test_launch_guard_negative_controls
```

Expected: `FAIL compliance_cli/test_toast_wrapper_calls_the_seam_and_never_powershell_itself AttributeError: module
'core.compliance.alerts' has no attribute 'toast'`; `FAIL launch_toast_queue/import ModuleNotFoundError: No module
named 'execution_launch.toast_queue'`. The `CLEAN` pin passes before and after (an import of a `core.compliance`
name is no effect); it records that spec section 15 allows it.

- [ ] **Step 4: Implement**

In `core/compliance/alerts.py`, insert after line 226:

```python


def toast(title: str, body: str) -> bool:
    """Public wrapper over the `_toast` seam for in-process callers (universe spec section 15: the coordinator's toast
    queue); True when shown. It runs PowerShell synchronously for up to 60 seconds, so callers queue it. `_toast` is
    looked up at call time, so tests that patch it still hold."""
    return _toast(title, body)
```

Create `execution_launch/toast_queue.py`:

```python
"""One background worker for coordinator toasts (universe spec section 15).

`core.compliance.alerts.toast` runs PowerShell synchronously for up to 60 seconds, so the coordinator never calls it
inside a unit: it puts each toast here and returns at once. The worker starts on the first put, shows the queued
toasts in order and ends when the queue is empty; construction starts nothing. Dedupe stays with the caller.
"""
from __future__ import annotations

from collections import deque
import threading
from typing import Callable


class ToastQueue:
    """FIFO toasts shown by at most one daemon worker; `put` never waits for a toast."""
    def __init__(self, show: Callable[[str, str], bool]) -> None:
        self._show, self._queue, self._lock, self._thread = show, deque(), threading.Lock(), None

    def put(self, title: str, body: str) -> None:
        with self._lock:
            self._queue.append((title, body))
            if self._thread is None:
                self._thread = threading.Thread(target=self._drain, name="coordinator-toasts", daemon=True)
                self._thread.start()

    def _drain(self) -> None:
        while True:
            with self._lock:
                if not self._queue:
                    self._thread = None
                    return
                title, body = self._queue.popleft()
            try:
                self._show(title, body)
            except Exception:
                pass  # ponytail: a failed toast is dropped; the status fields still carry every event
```

- [ ] **Step 5: Run the focused and module tests**

```bash
focus compliance compliance_cli/
focus launch launch_toast_queue/
focus launch launch_guards/
```

Expected: only `PASS` lines; each command exits 0.

- [ ] **Step 6: Commit**

```bash
diff <(git diff --stat) <(git diff --stat --ignore-cr-at-eol) && echo LF-OK
git add core/compliance/alerts.py execution_launch/toast_queue.py tests/compliance_cli.py \
  tests/launch_toast_queue.py tests/launch_acceptance.py tests/launch_guards.py
git commit -F - <<'EOF'
Add the public toast wrapper and the coordinator toast queue

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

Expected: `LF-OK`, then one commit.

---

### Task 2: Runner allow-list, snapshot and batch checks, and the sell guard

**Files:**
- Modify: `execution_launch/runner.py`: import after line 28; new methods after `_session` (lines 359-374);
  `tick` line 397 and inserts after lines 428, 437 and 446; `run` lines 505 and 521
- Create: `tests/launch_runner_universe.py`
- Modify: `tests/launch_acceptance.py` (`MODULES`)

**Interfaces:**
- Consumes: PR 4a `RiskResult.universe: Universe | None` (from `Controller.observe`),
  `PreparedSession.universe_batch_digest: str | None`, `registered_batch(batch_digest) -> UniverseBatch | None`
  (`.snapshot_sha256`, `.coins` of `CoinOdds` with `.market`), `OrderState.side`, `.symbol`; PR 1
  `Universe.valid_from`, `.valid_until`, `.rule_sha256`, `.snapshot_sha256`; PR 4b
  `LaunchProfile.universe_rule_sha256`.
- Produces: `Runner.tick(*, now, entry_allow: frozenset[str] | None = None)`,
  `Runner.run(timestamps, *, max_steps, should_stop=None, entry_allow=None)`; codes
  `RUNNER_UNIVERSE_ENTRY_NOT_ALLOWED`, `RUNNER_UNIVERSE_SNAPSHOT_MISMATCH`, `RUNNER_UNIVERSE_COIN_NOT_IN_BATCH`
  (all `blocked`, no stop); the sell guard returns `blocked` with `RUNNER_OUTSTANDING_ORDERS`. Test helpers
  `RULE`, `SNAPSHOT`, `BATCH`, `universe_profile`, `universe_snapshot`, `holding`, `universe_runner`,
  `reserve_reached`, used by Tasks 3 to 5.

- [ ] **Step 1: Write the failing tests**

Create `tests/launch_runner_universe.py`:

```python
"""Universe runner checks (spec sections 7, 9 and 10): the buy allow-list, the snapshot in force, the session's bound
batch, the sell guard, the flat re-check of a cross-coin renewal and preparation with a batch. Invented data,
temporary signed homes and dry adapters only; no network."""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from core.compliance import model as M
from execution_launch import runner as R
from execution_launch.profile import profile_digest
from execution_launch.runner import LaunchSession, Runner, RunnerError
from tests.control_session import selected
from tests.launch_runner import creates, runner_fixture

D = Decimal
RULE, SNAPSHOT, BATCH = "e" * 64, "5" * 64, "b" * 64
BTC, XRP = "KRW-BTC", "KRW-XRP"


def refused(call, code):
    try:
        call()
    except ValueError as exc:
        assert str(exc) == code, (str(exc), code)
        return
    raise AssertionError("expected refusal " + code)


def universe_profile(profile):
    """`profile` as a universe launch profile: the rule sha256 and IOC orders (spec section 10; PR 4b, PR 4c)."""
    return replace(profile, universe_rule_sha256=RULE, time_in_force="ioc")


def universe_snapshot(now, *, rule=RULE, valid_from=None, valid_until=None):
    """A Universe in force from an hour before `now` for one day: BTC and XRP listed and eligible, BTC first."""
    start = now - timedelta(hours=1) if valid_from is None else valid_from
    return M.Universe(day=start.astimezone(timezone.utc).date(), rule_sha256=rule, snapshot_sha256=SNAPSHOT,
                      built_at=start - timedelta(minutes=10), valid_from=start,
                      valid_until=start + timedelta(days=1) if valid_until is None else valid_until,
                      listed=(BTC, XRP), eligible=((BTC, D("900000000000")), (XRP, D("100000000000"))))


def holding(env, units="0.001"):
    """env.observation holding `units` BTC, as tests/launch_runner.py's exit tests set it."""
    return replace(env.observation,
                   positions=replace(env.observation.positions, holdings={("upbit", "BTC"): float(units)}),
                   holdings={("upbit", "fixture-account", "spot", BTC): D(units)})


@contextmanager
def universe_runner(*, bound=True, coins=(BTC, XRP), batch_snapshot=SNAPSHOT):
    """runner_fixture (prepared and armed) with a universe profile. `_assess` is pinned to the fixed profile's
    assessment, because the universe evaluator is PR 5 (PR 4b refuses forward-universe-v1 evidence); every universe
    check runs after it. With `bound`, the prepared session carries BATCH and its wrapper the universe profile's
    digest; registered_batch returns a batch over `coins` for `batch_snapshot`. controller.observe returns
    env.universe as RiskResult.universe (PR 4a). env.fixed is the fixed profile."""
    with runner_fixture() as env:
        assessment, binding = R._assess(env.profile, env.evidence, env.driver, env.review, env.now)
        env.fixed, env.profile = env.profile, universe_profile(env.profile)
        env.universe = universe_snapshot(env.now)
        launch = env.launch
        if bound:
            env.prepared = replace(env.prepared, universe_batch_digest=BATCH)
            launch = LaunchSession(prepared=env.prepared, profile_digest=profile_digest(env.profile), binding=binding)
        batch = SimpleNamespace(batch_digest=BATCH, snapshot_sha256=batch_snapshot,
                                coins=tuple(SimpleNamespace(market=coin, passed=True) for coin in coins))
        observe = env.controller.observe
        with patch.object(R, "_assess", lambda *args: (assessment, binding)), \
                patch.object(R, "registered_batch", lambda digest: batch if digest == BATCH else None), \
                patch.object(env.controller, "observe",
                             lambda *, now: replace(observe(now=now), universe=env.universe)):
            env.runner = Runner(profile=env.profile, quote_provider=lambda now: env.quote,
                account_provider=env.controller.account_provider, evidence=env.evidence, driver=env.driver,
                implementation_verifier=env.review, mode="rehearsal", controller=env.controller,
                launch_session=launch, isolated_state_root=env.home)
            yield env


def reserve_reached(env):
    """Stand-in for Controller.reserve: a buy that gets here passed every runner check. The hand-made bound session
    is not in the session registry, so the real reserve and dispatch are not exercised for universe buys."""
    def reserve(order, rules, *, session_id, now):
        raise RunnerError("FIXTURE_RESERVE_REACHED")
    return patch.object(env.controller, "reserve", reserve)


def test_a_universe_buy_needs_the_coin_in_a_frozenset_allow_list():
    with universe_runner() as env, reserve_reached(env):
        for allow in (None, frozenset(), frozenset({XRP}), {BTC}):
            result = env.runner.tick(now=env.now, entry_allow=allow)
            assert (result.status, result.reasons) == ("blocked", ("RUNNER_UNIVERSE_ENTRY_NOT_ALLOWED",)), (allow, result)
        result = env.runner.tick(now=env.now, entry_allow=frozenset({BTC}))
        assert (result.status, result.reasons) == ("blocked", ("FIXTURE_RESERVE_REACHED",)), result
        assert not env.runner.stopped and creates(env) == []


def test_a_universe_buy_needs_the_snapshot_in_force_under_the_profile_rule():
    with universe_runner() as env, reserve_reached(env):
        for snapshot in (None, universe_snapshot(env.now, valid_until=env.now),
                         universe_snapshot(env.now, valid_from=env.now + timedelta(seconds=1)),
                         universe_snapshot(env.now, rule="f" * 64)):
            env.universe = snapshot
            result = env.runner.tick(now=env.now, entry_allow=frozenset({BTC}))
            assert (result.status, result.reasons) == ("blocked", ("RUNNER_UNIVERSE_SNAPSHOT_MISMATCH",)), result
        assert not env.runner.stopped and creates(env) == []


def test_a_universe_buy_needs_the_bound_batch_of_this_snapshot_and_coin():
    for coins, batch_snapshot, code in (((BTC, XRP), "6" * 64, "RUNNER_UNIVERSE_SNAPSHOT_MISMATCH"),
                                        ((XRP,), SNAPSHOT, "RUNNER_UNIVERSE_COIN_NOT_IN_BATCH")):
        with universe_runner(coins=coins, batch_snapshot=batch_snapshot) as env, reserve_reached(env):
            result = env.runner.tick(now=env.now, entry_allow=frozenset({BTC}))
            assert (result.status, result.reasons) == ("blocked", (code,)), result
            assert not env.runner.stopped
    with universe_runner() as env, reserve_reached(env), patch.object(R, "registered_batch", lambda digest: None):
        result = env.runner.tick(now=env.now, entry_allow=frozenset({BTC}))
        assert (result.status, result.reasons) == ("blocked", ("RUNNER_UNIVERSE_SNAPSHOT_MISMATCH",)), result


def test_universe_sells_and_explicit_exits_never_look_at_the_allow_list_or_snapshot():
    for explicit in (False, True):
        with universe_runner(bound=False) as env:
            env.universe = None
            env.observation = holding(env)
            exit_signal = replace(env.signal, action="exit")
            if explicit:
                env.runner.submit_exit(exit_signal, now=env.now)
            else:
                env.signal = exit_signal
                result = env.runner.tick(now=env.now)
                assert result.status == "submitted", result
            assert len(creates(env)) == 1 and not env.runner.stopped


def test_a_fixed_profile_ignores_entry_allow():
    with runner_fixture() as env:
        result = env.runner.tick(now=env.now, entry_allow=frozenset())
        assert result.status == "submitted" and len(creates(env)) == 1, result


def test_a_second_sell_of_the_same_coin_is_blocked_while_one_is_active():
    with runner_fixture() as env:
        env.observation = holding(env)
        env.signal = replace(env.signal, action="exit")
        first = env.runner.tick(now=env.now)
        assert first.status == "submitted" and first.order_status == "ACKNOWLEDGED", first
        env.signal = replace(env.signal, signal_id="fixed-second-exit")
        second = env.runner.tick(now=env.now)
        assert (second.status, second.reasons) == ("blocked", ("RUNNER_OUTSTANDING_ORDERS",)), second
        assert not env.runner.stopped and len(creates(env)) == 1
```

In `tests/launch_acceptance.py` `MODULES`, add `"launch_runner_universe"` after `"launch_toast_queue"`.

- [ ] **Step 2: Run the tests and see them fail**

```bash
focus launch launch_runner_universe/
```

Expected: the four universe tests `FAIL ... AttributeError: <module 'execution_launch.runner' ...> does not have
the attribute 'registered_batch'`; `FAIL launch_runner_universe/test_a_fixed_profile_ignores_entry_allow
TypeError: Runner.tick() got an unexpected keyword argument 'entry_allow'`;
`FAIL launch_runner_universe/test_a_second_sell_of_the_same_coin_is_blocked_while_one_is_active AssertionError`
(today the second sell reaches `reserve`, which refuses, and the runner stops with `RUNNER_DEPENDENCY_REFUSED`).

- [ ] **Step 3: Implement**

In `execution_launch/runner.py`, after line 28 (`from execution_control.session import PreparedSession,
prepare_session`), add:

```python
from execution_control.universe_odds import registered_batch
```

After `_session` (lines 359-374, ending `return p.session_id  # E2 verifies ...`), insert:

```python

    def _universe_reasons(self, entry_allow, universe, now):
        """Spec section 7: a universe buy needs `profile.symbol` in this slot's allow-list (a missing list blocks every
        buy) and the snapshot in force under the profile's rule. Each failure is a blocked reason, never a stop."""
        reasons = ()
        if type(entry_allow) is not frozenset or self.profile.symbol not in entry_allow:
            reasons += ('RUNNER_UNIVERSE_ENTRY_NOT_ALLOWED',)
        if (universe is None or not universe.valid_from <= now < universe.valid_until
                or universe.rule_sha256 != self.profile.universe_rule_sha256):
            reasons += ('RUNNER_UNIVERSE_SNAPSHOT_MISMATCH',)
        return reasons

    def _universe_batch(self, universe):
        """Spec section 9: the snapshot in force is the bound batch's and the trade coin is one of its coins. Runs
        after _session, so the launch session is the actual prepared one."""
        bound = self.launch_session.prepared.universe_batch_digest
        batch = registered_batch(bound) if type(bound) is str else None
        _require(batch is not None and batch.snapshot_sha256 == universe.snapshot_sha256,
                 'RUNNER_UNIVERSE_SNAPSHOT_MISMATCH')
        _require(self.profile.symbol in {coin.market for coin in batch.coins}, 'RUNNER_UNIVERSE_COIN_NOT_IN_BATCH')
```

Replace line 397:

```python
    def tick(self, *, now) -> TickResult:
```

with:

```python
    def tick(self, *, now, entry_allow=None) -> TickResult:
```

After line 428 (`reasons += ('RUNNER_RISK_BLOCKS_ENTRY',)`), insert at the same indentation as line 427:

```python
            universe_buy = order.side == 'buy' and self.profile.universe_rule_sha256 is not None
            if universe_buy:
                reasons += self._universe_reasons(entry_allow, risk.universe, now)
```

After line 437 (`session_id = self._session(binding, now) if order.side == 'buy' else self._exit_session_id()`),
insert:

```python
            if universe_buy:
                self._universe_batch(risk.universe)
```

After line 446 (the `return TickResult(...)` of the buy `RUNNER_OUTSTANDING_ORDERS` check), insert:

```python
            if order.side == 'sell' and any(s.status in _ACTIVE and s.side == 'sell' and s.symbol == order.symbol
                                            for s in states):
                # Spec section 7: a second sell of one coin is blocked, never a reserve refusal that stops the runner.
                return TickResult(mode=self.mode, status='blocked', reasons=('RUNNER_OUTSTANDING_ORDERS',),
                    client_id=order.client_id, reconciled_orders=reconciled)
```

Replace line 505:

```python
    def run(self, timestamps, *, max_steps, should_stop=None) -> tuple[TickResult, ...]:
```

with:

```python
    def run(self, timestamps, *, max_steps, should_stop=None, entry_allow=None) -> tuple[TickResult, ...]:
```

Replace line 521:

```python
            results.append(self.tick(now=now))
```

with:

```python
            results.append(self.tick(now=now, entry_allow=entry_allow))
```

- [ ] **Step 4: Run the focused and module tests**

```bash
focus launch launch_runner_universe/
focus launch launch_runner/
focus launch launch_coordinator/
```

Expected: only `PASS` lines; each command exits 0.

- [ ] **Step 5: Commit**

```bash
diff <(git diff --stat) <(git diff --stat --ignore-cr-at-eol) && echo LF-OK
git add execution_launch/runner.py tests/launch_runner_universe.py tests/launch_acceptance.py
git commit -F - <<'EOF'
Check the universe allow-list, snapshot and batch on runner buys and block a second sell

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

---

### Task 3: Flat helpers and the flat re-check of a cross-coin renewal

**Files:**
- Modify: `execution_launch/runner.py`: import after line 22; constant after line 35; functions after `_positive`
  (lines 53-54); `refresh_instrument_rules` lines 286 and 298
- Test: `tests/launch_runner_universe.py` (append)

**Interfaces:**
- Consumes: PR 4a `OrderState.symbol`, `.updated_at`; `execution_accounts.model.AccountEvidence` (`.positions`,
  `.observed_at`), `Position` (`.symbol`, `.units`, `.price`); PR 4c `renew_profile(..., allow_symbol_change=)`.
- Produces: `active(state) -> bool`, `dust(position, minimum) -> bool`,
  `flat_in(symbol, positions, states, *, asof, minimum) -> bool`;
  `Runner.refresh_instrument_rules(renewal, *, now, account=None)`; code `RUNNER_UNIVERSE_NOT_FLAT`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/launch_runner_universe.py`:

```python


def test_dust_and_flat_in_follow_spec_section_7():
    from execution_accounts.model import Position
    from execution_control.controller import OrderState
    at, five = datetime(2026, 11, 11, tzinfo=timezone.utc), D("5000")

    def held(symbol, units, price):
        return Position(market="spot", symbol=symbol, base_currency=symbol[4:], quote_currency="KRW",
                        units=D(units), price=D(price), asof=at)

    def state(status, symbol, updated):
        return OrderState(client_id="c", status=status, order_digest="d" * 64, side="sell", symbol=symbol,
                          updated_at=updated)
    assert R.dust(held(BTC, "0.00004", "100000000"), five) and not R.dust(held(BTC, "0.00005", "100000000"), five)
    assert R.dust(held(XRP, "1000", "0"), five)                 # unlisted: marked 0, always dust
    positions = (held(BTC, "0.00004", "100000000"), held(XRP, "10", "1000"))
    earlier, later = at - timedelta(seconds=1), at + timedelta(seconds=1)
    assert R.flat_in(BTC, positions, (), asof=at, minimum=five)
    assert not R.flat_in(XRP, positions, (), asof=at, minimum=five)
    assert R.flat_in(BTC, positions, (state("FILLED", BTC, earlier), state("ACKNOWLEDGED", XRP, earlier)),
                     asof=at, minimum=five)
    for states in ((state("ACKNOWLEDGED", BTC, earlier),), (state("DISPATCHING", BTC, earlier),),
                   (state("PARTIAL", None, earlier),), (state("FILLED", BTC, at),), (state("CANCELED", BTC, later),)):
        assert not R.flat_in(BTC, positions, states, asof=at, minimum=five), states
    assert R.active(state("CANCEL_REQUESTED", BTC, at)) and not R.active(state("FILLED", BTC, at))


def test_a_renewal_to_another_coin_needs_a_flat_account():
    from tests.accounts_provider import bundle
    with universe_runner(bound=False) as env:
        env.runner.launch_session = None
        xrp = replace(env.profile, symbol=XRP, instrument_rules=replace(env.profile.instrument_rules, symbol=XRP))
        held = bundle(env.now, units=D("0.001"), price=D("100000000")).accounts[0]
        flat = bundle(env.now, units=D("0.00001"), price=D("100000000")).accounts[0]    # 1,000 KRW: dust
        with patch.object(R, "validate_renewal", lambda renewal, *, previous_profile, now: renewal.profile):
            same = env.profile
            assert env.runner.refresh_instrument_rules(SimpleNamespace(profile=same), now=env.now) is same
            for account in (None, held):
                refused(lambda: env.runner.refresh_instrument_rules(SimpleNamespace(profile=xrp), now=env.now,
                                                                    account=account), "RUNNER_UNIVERSE_NOT_FLAT")
                assert env.runner.profile.symbol == BTC
            assert env.runner.refresh_instrument_rules(SimpleNamespace(profile=xrp), now=env.now, account=flat) is xrp
            assert env.runner.profile is xrp


def test_the_session_rules_binding_holds_across_a_switch():
    """Spec section 19: Runner._session checks rules_binding_matches(prepared.rules_digest, current rules) on every
    tick, so a session prepared under one coin's rules must still match after renewals to another coin and back."""
    from execution_control.model import rules_digest
    from execution_launch import instrument_refresh as IR
    from tests.launch_instrument_refresh import registries, universe_authority, universe_observed
    from tests.launch_instrument_refresh import universe_profile as refresh_profile
    with registries():
        auth = universe_authority()
        p = refresh_profile(auth)
        bound = rules_digest(p.instrument_rules)
        o = universe_observed("KRW-ETH", auth=auth, tick="5")
        r = IR.renew_profile(p, o, now=o.checked_at, allow_symbol_change=True)
        assert IR.rules_binding_matches(bound, r.profile.instrument_rules, account_scope=p.account_scope,
                                        now=o.checked_at)
        back = universe_observed(BTC, o.checked_at + timedelta(seconds=10), auth=auth)
        again = IR.renew_profile(r.profile, back, now=back.checked_at, allow_symbol_change=True)
        assert IR.rules_binding_matches(bound, again.profile.instrument_rules, account_scope=p.account_scope,
                                        now=back.checked_at)
```

- [ ] **Step 2: Run the tests and see them fail**

```bash
focus launch launch_runner_universe/test_dust
focus launch launch_runner_universe/test_a_renewal
focus launch launch_runner_universe/test_the_session_rules
```

Expected: `FAIL ... AttributeError: module 'execution_launch.runner' has no attribute 'dust'` and `FAIL ...
TypeError: Runner.refresh_instrument_rules() got an unexpected keyword argument 'account'`.
`test_the_session_rules_binding_holds_across_a_switch` already passes: it pins PR 4c's renewal chain
(`original_rule_digests`), which the runner's per-tick session check depends on after a switch; it must stay green.

- [ ] **Step 3: Implement**

In `execution_launch/runner.py`, after line 22 (`from core.isolation import checked_target, state_root`), add:

```python
from execution_accounts.model import AccountEvidence
```

After line 35 (`_ACTIVE = frozenset({...})`), add:

```python
_LIVE = _ACTIVE | {'DISPATCHING'}   # Controller._view shows DISPATCHING as UNKNOWN; a raw status counts too
```

After `_positive` (lines 53-54), insert:

```python


def active(state) -> bool:
    """An order state the controller still tracks as live (spec section 7, "flat in X")."""
    return state.status in _LIVE


def dust(position, minimum) -> bool:
    """A holding worth less than `minimum` at its mark; an unlisted coin (mark 0) is always dust (spec section 7)."""
    return position.units * position.price < minimum


def flat_in(symbol, positions, states, *, asof, minimum) -> bool:
    """Spec section 7: no non-dust holding of `symbol` in the frame's positions, no live order in it (or in an
    unknown symbol), and no order in it updated at or after the frame's account time `asof`, so a fill the frame has
    not seen yet still counts."""
    return (not any(p.symbol == symbol and not dust(p, minimum) for p in positions)
            and not any((active(s) and s.symbol in (symbol, None))
                        or (s.symbol == symbol and s.updated_at is not None and s.updated_at >= asof)
                        for s in states))
```

Replace line 286:

```python
    def refresh_instrument_rules(self, renewal, *, now):
```

with:

```python
    def refresh_instrument_rules(self, renewal, *, now, account=None):
```

After line 298 (`current = validate_renewal(renewal, previous_profile=self.profile, now=now)`), insert:

```python
            if current.symbol != self.profile.symbol:
                # Spec section 10: a renewal to another coin re-checks the coordinator's flat verdict on its frame.
                _require(type(account) is AccountEvidence and type(self.controller) is Controller
                         and flat_in(self.profile.symbol, account.positions, self.controller.states(),
                                     asof=account.observed_at,
                                     minimum=self.profile.instrument_rules.min_notional_krw),
                         'RUNNER_UNIVERSE_NOT_FLAT')
```

- [ ] **Step 4: Run the focused and module tests**

```bash
focus launch launch_runner_universe/
focus launch launch_runner/
focus launch launch_instrument_refresh/
focus launch launch_owner_ops/
```

Expected: only `PASS` lines; each command exits 0.

- [ ] **Step 5: Commit**

```bash
diff <(git diff --stat) <(git diff --stat --ignore-cr-at-eol) && echo LF-OK
git add execution_launch/runner.py tests/launch_runner_universe.py
git commit -F - <<'EOF'
Add the flat-in helpers and re-check flatness on a cross-coin renewal

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

---

### Task 4: Preparation with an odds batch

**Files:**
- Modify: `execution_launch/runner.py`: `prepare_launch_session` lines 187, 203-204 and 233
- Test: `tests/launch_runner_universe.py` (append)

**Interfaces:**
- Consumes: PR 4a `prepare_session(..., universe_batch: UniverseBatch | None = None)` (its own checks:
  `SESSION_UNIVERSE_BATCH_UNREGISTERED`, `..._STALE`, `..._TEMPLATE_INVALID`, `..._FAILED`, the expiry cap);
  `UniverseBatch.coins[*].market` (`KRW-<base>`).
- Produces: `prepare_launch_session(..., expires_at=None, universe_batch=None) -> LaunchSession`. For a universe
  profile the batch is required and the template's leg must be `upbit` with `KRW-<leg.symbol>` among the batch's
  coins; for a fixed profile the batch must be `None` and the old check stays. Both refuse
  `RUNNER_SELECTED_PLAN_SCOPE_MISMATCH`.

- [ ] **Step 1: Write the failing test**

Append to `tests/launch_runner_universe.py`:

```python


def test_universe_preparation_needs_a_batch_holding_the_template_coin():
    with universe_runner(bound=False) as env:
        plan, inputs, seed = selected(env.now)
        seen = []

        def prepare(**kwargs):
            seen.append(kwargs["universe_batch"])
            return env.prepared
        batch = SimpleNamespace(coins=(SimpleNamespace(market="KRW-" + plan.leg.symbol),))
        other = SimpleNamespace(coins=(SimpleNamespace(market=XRP),))

        def call(profile, universe_batch):
            return R.prepare_launch_session(profile=profile, evidence=env.evidence, driver=env.driver,
                implementation_verifier=env.review, journal=env.journal, selected_plan=plan, inputs=inputs,
                positions=env.observation.positions, now=env.now, selection_seed_hex=seed, clock=lambda: env.now,
                positions_asof=env.observation.asof, universe_batch=universe_batch)
        with patch.object(R, "prepare_session", prepare):
            for profile, value in ((env.profile, None), (env.profile, other), (env.fixed, batch)):
                refused(lambda: call(profile, value), "RUNNER_SELECTED_PLAN_SCOPE_MISMATCH")
            assert seen == []
            assert call(env.profile, batch).prepared is env.prepared
            assert call(env.fixed, None).prepared is env.prepared
        assert seen == [batch, None]
```

- [ ] **Step 2: Run the test and see it fail**

```bash
focus launch launch_runner_universe/test_universe_preparation
```

Expected: `FAIL ... TypeError: prepare_launch_session() got an unexpected keyword argument 'universe_batch'`.

- [ ] **Step 3: Implement**

In `execution_launch/runner.py`, replace line 187:

```python
                           selection_seed_hex, clock, positions_asof, expires_at=None) -> LaunchSession:
```

with:

```python
                           selection_seed_hex, clock, positions_asof, expires_at=None,
                           universe_batch=None) -> LaunchSession:
```

Replace lines 203-204:

```python
    _require((selected_plan.leg.venue, selected_plan.leg.symbol) == (profile.venue, symbol),
             'RUNNER_SELECTED_PLAN_SCOPE_MISMATCH')
```

with:

```python
    if profile.universe_rule_sha256 is None:
        scoped = universe_batch is None and (selected_plan.leg.venue, selected_plan.leg.symbol) == (profile.venue, symbol)
    else:
        # Spec section 9: the template's leg is upbit and its coin one of the batch's N coins, not the profile's coin.
        scoped = (universe_batch is not None and selected_plan.leg.venue == 'upbit'
                  and 'KRW-' + selected_plan.leg.symbol in {coin.market for coin in universe_batch.coins})
    _require(scoped, 'RUNNER_SELECTED_PLAN_SCOPE_MISMATCH')
```

Replace line 233:

```python
        market=profile.market, quote_currency=profile.quote_currency, expires_at=expires_at,
```

with:

```python
        market=profile.market, quote_currency=profile.quote_currency, expires_at=expires_at,
        universe_batch=universe_batch,
```

- [ ] **Step 4: Run the focused and module tests**

```bash
focus launch launch_runner_universe/
focus launch launch_runner/
focus control control_session/
```

Expected: only `PASS` lines; each command exits 0.

- [ ] **Step 5: Commit**

```bash
diff <(git diff --stat) <(git diff --stat --ignore-cr-at-eol) && echo LF-OK
git add execution_launch/runner.py tests/launch_runner_universe.py
git commit -F - <<'EOF'
Prepare a universe launch session with its odds batch

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

---

### Task 5: Universe coordinator construction, status fields, toasts and the disarm split

**Files:**
- Modify: `execution_launch/coordinator.py`: imports at lines 43, 49 and between 68 and 69; constants after line
  84; `CoordinatorStatus` after line 232; `__init__` lines 280, 285, after 290, after 300, after 350; new methods
  after `_refused` (lines 363-372); `disarm` lines 678-708
- Create: `tests/launch_coordinator_universe.py`
- Modify: `tests/launch_acceptance.py` (`MODULES`)

**Interfaces:**
- Consumes: Task 1 `ToastQueue`, `alerts.toast`; PR 4b `ProgramSpec.kind`, `.universe_rule_sha256`,
  `.max_candidates`; PR 4a `Controller.kill(session_id, *, reason, now)` recording `reason`; PR 2 `FlagRead`,
  `TickerRead` (tests).
- Produces: `UNIVERSE_KIND = "universe_top1_momentum"`, `UNIVERSE_WINDOW_MAX = timedelta(hours=72)`;
  `Coordinator(..., slot_source=None, program=None, toast=alerts.toast)`; `CoordinatorStatus` fields `held_symbol`,
  `trade_symbol`, `snapshot_day`, `snapshot_sha256`, `universe_state`, `held_flag` (all `None`), `allow_count: int
  = 0`, `buy_block_reasons: tuple = ()`, `disarm_failed: bool = False`, `window_ended_missed_slot: bool = False`;
  `_toast_once(key, level, body)`, `_holding()`, `_disarm_locked(*, reason, code, republish) -> DisarmResult`.
  Test helpers used by Tasks 6 to 12.

- [ ] **Step 1: Write the failing tests**

Create `tests/launch_coordinator_universe.py`:

```python
"""Universe coordinator (spec sections 7, 9, 10, 12 and 15): construction, trade-coin choice and renewal, the slot
unit, events, toasts, status and the console odds step, over tests/launch_coordinator.py's fixture with a universe
profile and doubles for the slot reads, terms, history and toasts. Offline; temporary state only."""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import json
import threading
from types import MappingProxyType, SimpleNamespace
from unittest.mock import patch

from execution_accounts.model import Position
from execution_accounts.universe import FlagRead, TickerRead
from execution_launch import coordinator as C
from execution_launch import runner as R
from execution_launch.coordinator import CoordinatorError
from execution_launch.driver import DeploymentWindow
from execution_launch.toast_queue import ToastQueue
from tests.control_session import selected
from tests.launch_coordinator import HOLD, PRICE, Books, build, fixture, refused, seconds
from tests.launch_runner_universe import RULE, SNAPSHOT, universe_profile, universe_snapshot

D = Decimal
BTC, XRP, ETH = "KRW-BTC", "KRW-XRP", "KRW-ETH"
RED = "TRADEGEN universe red"


class FixtureRefusal(ValueError):
    """A fixed-code refusal from a double (a ValueError subclass, so the coordinator's _code passes the code)."""


class SlotSource:
    """UniverseSlotSource double: the flag read lists `flags` (BTC and XRP unflagged unless changed); `fail` names
    the reads that return ok=False; prices trade `age` before the read; `calls` records each read."""
    def __init__(self, fake):
        self.fake, self.fail, self.calls, self.age = fake, set(), [], timedelta(0)
        self.flags = {BTC: "unflagged", XRP: "unflagged"}

    def read_flags(self):
        self.calls.append("flags")
        if "flags" in self.fail:
            return FlagRead(ok=False, received_at=None, sha256=None, flags=MappingProxyType({}))
        return FlagRead(ok=True, received_at=self.fake.now, sha256="f" * 64, flags=MappingProxyType(dict(self.flags)))

    def read_tickers(self, markets):
        self.calls.append(("tickers", tuple(markets)))
        if "tickers" in self.fail:
            return TickerRead(ok=False, received_at=None, sha256=None, prices=MappingProxyType({}))
        traded = self.fake.now - self.age
        return TickerRead(ok=True, received_at=self.fake.now, sha256="7" * 64,
                          prices=MappingProxyType({market: (PRICE, traded) for market in markets}))


class UniverseBooks(Books):
    """Books whose read names the trade coin (spec section 10); `symbols` records each name, `fail` raises."""
    def __init__(self, fake):
        super().__init__(fake)
        self.symbols, self.fail = [], False

    def read(self, symbol=None):
        self.symbols.append(symbol)
        if self.fail:
            raise RuntimeError("BOOK-SECRET-1")
        return super().read()


class Terms:
    """Terms source double: read(symbol) records the name; the observation names the coin and whether it is within
    its buy cap (renewals(env) patches renew_profile and within_buy_cap to read these); `fail` raises."""
    def __init__(self):
        self.reads, self.fail, self.within = [], None, True

    def read(self, symbol=None):
        self.reads.append(symbol)
        if self.fail is not None:
            raise self.fail
        return SimpleNamespace(symbol=symbol, within=self.within)


class History:
    """Universe LiveHistory double: record_slot keeps its keywords and sets recorded_allow; decided_symbol returns
    `decided`; `fail` raises."""
    def __init__(self):
        self.rows, self.fail, self.decided, self.recorded_allow = [], None, None, None

    def record_slot(self, book, account, **options):
        if self.fail is not None:
            raise self.fail
        self.rows.append((book, options))
        self.recorded_allow = options["universe"].allow
        return "a" * 64

    def decided_symbol(self):
        return self.decided


class Recorder:
    """A synchronous stand-in for the coordinator's ToastQueue."""
    def __init__(self):
        self.puts = []

    def put(self, title, body):
        self.puts.append((title, body))


def program(**changes):
    """The reviewed program fields the coordinator reads (PR 4b's ProgramSpec v2 carries them)."""
    return SimpleNamespace(**({"kind": C.UNIVERSE_KIND, "universe_rule_sha256": RULE, "max_candidates": 2} | changes))


def position(symbol, units, price, at):
    return Position(market="spot", symbol=symbol, base_currency=symbol[4:], quote_currency="KRW", units=D(units),
                    price=D(price), asof=at)


@contextmanager
def universe_fixture():
    """tests/launch_coordinator.fixture with a universe profile and the doubles above; the driver decides HOLD.
    `_assess` is pinned to the fixed profile's assessment because the universe evaluator is PR 5 (PR 4b refuses
    forward-universe-v1 evidence); every universe check runs after it."""
    with fixture() as env:
        assessment, binding = R._assess(env.profile, env.evidence, env.driver, env.review, env.t0)
        env.fixed_profile, env.profile = env.profile, universe_profile(env.profile)
        env.universe, env.signal[0] = universe_snapshot(env.t0), HOLD
        env.slots, env.books, env.terms = SlotSource(env.fake), UniverseBooks(env.fake), Terms()
        env.history, env.toasts = History(), Recorder()
        with patch.object(R, "_assess", lambda *args: (assessment, binding)):
            yield env


def build_universe(env, **changes):
    """build() with the universe profile and doubles. After checking that construction started no toast worker, the
    queue is swapped for env.toasts; controller.observe carries env.universe as RiskResult.universe (PR 4a)."""
    options = {"profile": env.profile, "slot_source": env.slots, "program": program(), "terms_source": env.terms,
               "history": env.history, "toast": lambda title, body: True}
    c = build(env, **(options | changes))
    assert type(c._toasts) is ToastQueue and c._toasts._thread is None
    c._toasts = env.toasts
    observe = c._controller.observe
    c._controller.observe = lambda *, now: replace(observe(now=now), universe=env.universe)
    return c


@contextmanager
def renewals(env):
    """renew_profile issues a renewal to the observation's coin (only fields the universe contract digest leaves out
    change), validate_renewal accepts it and within_buy_cap reads the double's flag. env.renewed records
    (symbol, allow_symbol_change). create=True: the coordinator imports within_buy_cap only from Task 9 on."""
    env.renewed = []

    def renew(profile, observation, *, now, allow_symbol_change=False):
        symbol = observation.symbol or profile.symbol
        env.renewed.append((symbol, allow_symbol_change))
        rules = replace(profile.instrument_rules, symbol=symbol, asof=now)
        return SimpleNamespace(profile=replace(profile, symbol=symbol, instrument_rules=rules))
    with patch.object(C, "renew_profile", renew), \
            patch.object(C, "within_buy_cap", lambda observation: observation.within, create=True), \
            patch.object(R, "validate_renewal", lambda renewal, *, previous_profile, now: renewal.profile):
        yield env


def reframe(c, positions):
    """Every later _publish keeps the real provider observation, but the frame the coordinator reads
    (`_latest_frame.accounts[0]`) holds `positions`."""
    publish = c._publish

    def wrapped(previous, now, book):
        observation = publish(previous, now, book)
        frame = c._latest_frame
        c._latest_frame = SimpleNamespace(interval=frame.interval,
                                          accounts=(replace(frame.accounts[0], positions=tuple(positions)),))
        return observation
    c._publish = wrapped


def run_slot(env, c, slot):
    """One slot unit outside run(): the clock at the prefetch lead, then _slot."""
    env.fake.now = slot - seconds(3)
    c._slot(slot)


def allow_seen(c):
    """The entry_allow of every Runner.run call."""
    seen, run = [], c._runner.run

    def wrapped(timestamps, **options):
        seen.append(options.get("entry_allow"))
        return run(timestamps, **options)
    c._runner.run = wrapped
    return seen


def stub_kill(c, recorded):
    """A prepared-session stand-in and a Controller.kill recorder returning `recorded` (PR 4a tests the real kill)."""
    kills = []
    c._launch = SimpleNamespace(prepared=SimpleNamespace(session_id="Lfixture-universe"))
    c._controller.kill = lambda session_id, *, reason, now: kills.append(reason) or recorded
    return kills


def test_universe_construction_is_inert_and_status_starts_empty():
    with universe_fixture() as env:
        before = threading.active_count()
        c = build_universe(env)
        assert threading.active_count() == before and env.producer.prefetches == [] and env.slots.calls == []
        s = c.status()
        assert (s.held_symbol, s.trade_symbol, s.snapshot_day, s.snapshot_sha256, s.universe_state, s.held_flag,
                s.allow_count, s.buy_block_reasons, s.disarm_failed, s.window_ended_missed_slot) == (
                    None, None, None, None, None, None, 0, (), False, False)
        assert c._holding()                         # no frame read yet: fail closed


def test_a_universe_coordinator_needs_its_slot_source_program_terms_and_history():
    with universe_fixture() as env:
        for changes in ({"slot_source": None}, {"slot_source": SimpleNamespace(read_flags=lambda: None)},
                        {"program": None}, {"program": program(kind="fixed")},
                        {"program": program(universe_rule_sha256="f" * 64)}, {"program": program(max_candidates=0)},
                        {"program": program(max_candidates=True)}, {"terms_source": None},
                        {"history": SimpleNamespace(record_slot=lambda *args, **kwargs: None)}, {"toast": None}):
            refused(lambda: build_universe(env, **changes), "COORDINATOR_INTEGRATIONS_REQUIRED")


def test_a_universe_window_is_at_most_72_hours():
    with universe_fixture() as env:
        def code(profile, hours):
            window = DeploymentWindow(deployment_id="coord-universe", start=env.window.start,
                                      end=env.window.start + timedelta(hours=hours))
            try:
                build_universe(env, profile=profile, window=window, monitor_until=window.end)
            except CoordinatorError as exc:
                return str(exc)
            return None
        assert code(env.profile, 73) == "COORDINATOR_WINDOW_INVALID"
        assert code(env.profile, 72) != "COORDINATOR_WINDOW_INVALID"     # other checks may still refuse it
        with patch.object(C, "UNIVERSE_WINDOW_MAX", timedelta(hours=1)):
            assert code(env.fixed_profile, 2) != "COORDINATOR_WINDOW_INVALID"


def test_disarm_locked_runs_under_the_held_lock_and_the_owner_disarm_still_republishes():
    with universe_fixture() as env:
        c = build_universe(env)
        c.bootstrap()
        kills, published = stub_kill(c, True), []
        publish = c._board.publish
        c._board.publish = lambda frame, book: published.append(frame) or publish(frame, book)
        with c._work:
            result = c._disarm_locked(reason="market_vanished", code="COORDINATOR_UNIVERSE_DISARM", republish=False)
        assert result.session_prepared and result.owner_disarm_recorded and published == []
        assert kills == ["market_vanished"] and c.status().reasons == ("COORDINATOR_UNIVERSE_DISARM",)
        c.disarm(timeout=0)
        assert kills == ["market_vanished", "owner_requested"] and published == [c._latest_frame]
        assert c.status().reasons == ("COORDINATOR_OWNER_DISARM_RECORDED",) and c.status().strategy_stopped


def test_toasts_are_queued_once_per_key_and_never_wait_for_the_toast():
    with universe_fixture() as env:
        c = build_universe(env)
        c._toast_once("extra:2026-11-11", "red", "body-1")
        c._toast_once("extra:2026-11-11", "red", "body-2")
        c._toast_once("held-flag:2026-11-11", "amber", "body-3")
        assert env.toasts.puts == [(RED, "body-1"), ("TRADEGEN universe amber", "body-3")]
        shown, release = [], threading.Event()
        c._toasts = ToastQueue(lambda title, body: release.wait(5) and shown.append(title))
        c._toast_once("missed", "red", "body-4")    # returns while the toast is still showing
        worker = c._toasts._thread
        assert shown == [] and worker.is_alive()
        release.set()
        worker.join(5)
        assert shown == [RED]
```

In `tests/launch_acceptance.py` `MODULES`, add `"launch_coordinator_universe"` after `"launch_runner_universe"`.

- [ ] **Step 2: Run the tests and see them fail**

```bash
focus launch launch_coordinator_universe/
```

Expected: every test `FAIL`s, the construction ones with `TypeError: Coordinator.__init__() got an unexpected
keyword argument 'slot_source'` and the window test with `AttributeError: ... does not have the attribute
'UNIVERSE_WINDOW_MAX'` or the same `TypeError`.

- [ ] **Step 3: Implement**

In `execution_launch/coordinator.py`:

Replace line 43 (`from datetime import datetime, time, timedelta`) with:

```python
from datetime import date, datetime, time, timedelta
```

Before line 49 (`from core.compliance.model import KST`), add:

```python
from core.compliance.alerts import toast
```

Between line 68 (`from execution_launch.strategy import ...`) and line 69 (`from execution_launch.workflow import
...`), add:

```python
from execution_launch.toast_queue import ToastQueue
```

After line 84 (`_KNOBS = {...}`), add:

```python
UNIVERSE_KIND = "universe_top1_momentum"  # the reviewed program kind of a universe profile (PR 4b)
UNIVERSE_WINDOW_MAX = timedelta(hours=72)  # spec section 10: the never-pruned renewal registry bounds the window
```

In `CoordinatorStatus`, after line 232 (`reasons: tuple[str, ...] = ()  # the last slot tick's reasons, ...`), add:

```python
    held_symbol: str | None = None      # universe: the largest held coin of the last published frame
    trade_symbol: str | None = None     # universe: profile.symbol, the coin whose rules are current
    snapshot_day: date | None = None    # universe: the snapshot of the last monitor
    snapshot_sha256: str | None = None
    universe_state: str | None = None   # universe: in_force, no_snapshot or rule_mismatch
    held_flag: str | None = None        # universe: the held coin's class in the last slot's flag read
    allow_count: int = 0                # universe: the size of the last slot's buy allow-list
    buy_block_reasons: tuple[str, ...] = ()
    disarm_failed: bool = False         # sticky: the universe disarm recorded no system disarm
    window_ended_missed_slot: bool = False  # sticky: a slot the history did not record ended the window
```

In `__init__`, replace line 280:

```python
                 wait: Callable[[threading.Event, float], bool] = threading.Event.wait) -> None:
```

with:

```python
                 wait: Callable[[threading.Event, float], bool] = threading.Event.wait,
                 slot_source: object | None = None, program: object | None = None,
                 toast: Callable[[str, str], bool] = toast) -> None:
```

Replace line 285:

```python
                 and all(callable(f) for f in (clock, wait, account_source, implementation_verifier))
```

with:

```python
                 and all(callable(f) for f in (clock, wait, account_source, implementation_verifier, toast))
```

After line 290 (`"COORDINATOR_INTEGRATIONS_REQUIRED")`), insert:

```python
        universe = profile.universe_rule_sha256 is not None    # spec section 10: a universe launch profile
        _require(not universe or (callable(getattr(slot_source, "read_flags", None))
                                  and callable(getattr(slot_source, "read_tickers", None))
                                  and terms_source is not None
                                  and callable(getattr(history, "decided_symbol", None))
                                  and getattr(program, "kind", None) == UNIVERSE_KIND
                                  and getattr(program, "universe_rule_sha256", None) == profile.universe_rule_sha256
                                  and type(getattr(program, "max_candidates", None)) is int
                                  and program.max_candidates >= 1),
                 "COORDINATOR_INTEGRATIONS_REQUIRED")
```

After line 300 (the `"COORDINATOR_WINDOW_INVALID")` that closes the span check), insert:

```python
        _require(not universe or span <= UNIVERSE_WINDOW_MAX, "COORDINATOR_WINDOW_INVALID")
```

After line 350 (`self._status = CoordinatorStatus()`), insert:

```python
        self._universe, self._slot_source, self._program = universe, slot_source, program
        self._toasts, self._toasted = ToastQueue(toast), set()        # spec section 15: queued, deduped here
        self._snapshot, self._held, self._extra = None, None, False   # _held None: no frame read yet
        self._vanished, self._disarmed, self._terms_unavailable = False, False, False
        self._remainder_ticks, self._remainder = 0, False
```

After `_refused` (lines 363-372), insert:

```python

    def _toast_once(self, key, level, body) -> None:
        """Queue one coordinator toast (spec section 15) unless `key` was already toasted in this window; keys carry
        the Seoul date where the dedupe is once per day."""
        if key not in self._toasted:
            self._toasted.add(key)
            self._toasts.put("TRADEGEN universe " + level, body)

    def _holding(self) -> bool:
        """True while a coin is held or the holdings are not known yet (no frame read): exits need fresh rules."""
        return self._held is None or bool(self._held)
```

Replace lines 678-708 of `disarm` (from `try:` after the pending return through `self._work.release()`):

```python
        try:
            launch = self._launch
            ...
        finally:
            self._board.clear()
            self._update(in_flight="")
            self._work.release()
```

with:

```python
        try:
            return self._disarm_locked(reason="owner_requested", code=None, republish=True)
        finally:
            self._board.clear()
            self._update(in_flight="")
            self._work.release()

    def _disarm_locked(self, *, reason, code, republish) -> DisarmResult:
        """The durable kill under a work lock the caller holds (spec section 7). `republish` re-publishes the last
        genuine frame for the owner's disarm; the universe disarm runs inside a slot unit right after its own
        _publish, so the board already holds that unit's frame. `code` replaces the owner codes in `reasons`."""
        try:
            launch = self._launch
            if launch is None:
                self._update(new_entry_blocked=True)
                return DisarmResult(session_prepared=False, journal_kill_written=False,
                                    owner_disarm_recorded=False)
            clock_valid = True
            try:
                now = self._time()
            except Exception:
                clock_valid = False
                now = self._last_time
                if now is None:
                    from datetime import timezone
                    now = datetime(1970, 1, 1, tzinfo=timezone.utc)
            if republish and clock_valid and self._latest_frame is not None:
                self._board.publish(self._latest_frame, None)
            owner_recorded = self._controller.kill(launch.prepared.session_id, reason=reason, now=now)
            self._update(new_entry_blocked=True, orders=self._controller.states(),
                reasons=(code or ("COORDINATOR_OWNER_DISARM_RECORDED" if owner_recorded
                                  else "COORDINATOR_DISARM_JOURNAL_ONLY"),))
            return DisarmResult(session_prepared=True, journal_kill_written=True,
                                owner_disarm_recorded=owner_recorded)
        except Exception as exc:
            self._update(new_entry_blocked=True, reasons=("COORDINATOR_DISARM_RECORD_REFUSED",))
            raise CoordinatorError(_code(exc, "COORDINATOR_DISARM_RECORD_REFUSED")) from None
```

The body moved into `_disarm_locked` is fd85850 lines 679-704 with three changes: the publish also requires
`republish`, the kill passes `reason=reason`, and `reasons` takes `code` first. Lines 672-677 of `disarm`
(timeout check, `self.stop()`, the timed acquire and the pending result) stay.

- [ ] **Step 4: Run the focused and module tests**

```bash
focus launch launch_coordinator_universe/
focus launch launch_coordinator/
focus launch launch_owner_ops/
```

Expected: only `PASS` lines; each command exits 0 (`test_coordinator_source_static_contract` still passes: the new
module-level lines are imports and plain assignments).

- [ ] **Step 5: Commit**

```bash
diff <(git diff --stat) <(git diff --stat --ignore-cr-at-eol) && echo LF-OK
git add execution_launch/coordinator.py tests/launch_coordinator_universe.py tests/launch_acceptance.py
git commit -F - <<'EOF'
Construct a universe coordinator with status fields, queued toasts and a lock-free disarm

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

---

### Task 6: Book and terms by coin, held coins, the terms-failure split and the snapshot

**Files:**
- Modify: `execution_launch/coordinator.py`: runner import lines 66-67; helpers after `history_head_name`
  (lines 116-118); `_read_book` line 411; `_refresh_terms` lines 439-461; `_maybe_refresh_terms` lines 463-470;
  new `_holdings` after it; `_monitor` lines 487-496
- Test: `tests/launch_coordinator_universe.py` (append)

**Interfaces:**
- Consumes: Task 3 `dust`; Task 5 attributes; PR 4c `E1UpbitTermsSource.read(symbol)`,
  `renew_profile(profile, observation, *, now, allow_symbol_change=False)`, `TERMS_MARKET_INACTIVE`; PR 4a
  `RiskResult.universe`; Task 3 `Runner.refresh_instrument_rules(..., account=)`.
- Produces: `held_coins(account, minimum) -> tuple[str, ...]`, `universe_state(snapshot, rule_sha256, at) -> str`;
  `_refresh_terms(symbol=None)`; `_holdings(now)`; the monitor sets `_snapshot` and three status fields; a universe
  book read is `quote_source.read(profile.symbol)`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/launch_coordinator_universe.py`:

```python


def test_book_and_terms_reads_name_the_trade_coin():
    with universe_fixture() as env, renewals(env):
        c = build_universe(env)
        c.bootstrap()
        assert c._read_book() is not None and env.books.symbols == [BTC]
        c.refresh_instrument_rules()
        assert env.terms.reads == [BTC] and env.renewed == [(BTC, False)]


def test_monitors_track_held_coins_extra_holdings_and_the_snapshot():
    with universe_fixture() as env:
        c = build_universe(env)
        c.bootstrap()
        s = c.status()
        assert (s.held_symbol, s.trade_symbol, c._held, c._extra) == (BTC, BTC, (BTC,), False)
        assert (s.snapshot_day, s.snapshot_sha256, s.universe_state) == (env.universe.day, SNAPSHOT, "in_force")
        reframe(c, [position(BTC, "0.001", PRICE, env.fake.now), position(XRP, "100", "1000", env.fake.now)])
        env.universe = None
        env.fake.now += seconds(20)
        c._monitor("monitor")
        s = c.status()
        assert c._held == (BTC, XRP) and c._extra and (s.universe_state, s.snapshot_day) == ("no_snapshot", None)
        assert [title for title, _ in env.toasts.puts] == [RED] and any(k.startswith("extra:") for k in c._toasted)
        env.fake.now += seconds(20)
        c._monitor("monitor")
        assert len(env.toasts.puts) == 1                 # once per day


def test_held_coins_and_universe_state_are_pure():
    at = datetime(2026, 11, 11, 1, 0, tzinfo=timezone.utc)
    account = SimpleNamespace(positions=(position(XRP, "100", "1000", at), position(BTC, "0.001", PRICE, at),
                                         position(ETH, "1", "0", at), position("KRW-SOL", "0.01", "100000", at)))
    assert C.held_coins(account, D("5000")) == (BTC, XRP)          # equal values: by symbol; unlisted and dust out
    snapshot = universe_snapshot(at)
    assert C.universe_state(snapshot, RULE, at) == "in_force"
    assert C.universe_state(snapshot, "f" * 64, at) == "rule_mismatch"
    assert C.universe_state(None, RULE, at) == "no_snapshot"
    assert C.universe_state(snapshot, RULE, snapshot.valid_until) == "no_snapshot"


def test_terms_failures_block_slots_only_while_a_coin_is_held():
    with universe_fixture() as env, renewals(env):
        c = build_universe(env)
        env.terms.fail = FixtureRefusal("TERMS_INQUIRY_FAILED")
        refused(c.refresh_instrument_rules, "TERMS_INQUIRY_FAILED")
        assert c._terms_blocked                          # no frame read yet: fail closed
    with universe_fixture() as env, renewals(env):
        c = build_universe(env)
        c.bootstrap()                                    # BTC held
        env.terms.fail = FixtureRefusal("TERMS_INQUIRY_FAILED")
        refused(c.refresh_instrument_rules, "TERMS_INQUIRY_FAILED")
        assert c._terms_blocked and not c._terms_unavailable and not c._vanished
        env.terms.fail = FixtureRefusal("TERMS_MARKET_INACTIVE")
        refused(c.refresh_instrument_rules, "TERMS_MARKET_INACTIVE")
        assert c._vanished                               # the vanish event of the next slot unit
    with universe_fixture() as env, renewals(env):
        c = build_universe(env)
        reframe(c, [])
        c.bootstrap()                                    # nothing held
        env.terms.fail = FixtureRefusal("TERMS_INQUIRY_FAILED")
        refused(c.refresh_instrument_rules, "TERMS_INQUIRY_FAILED")
        assert not c._terms_blocked and c._terms_unavailable
        env.fake.now += seconds(20)
        c._monitor("monitor")                            # retried at the next monitor, still failing
        assert c.status().new_entry_blocked and c.status().instrument_source == "TERMS_INQUIRY_FAILED"
        env.terms.fail = None
        env.fake.now += seconds(20)
        c._monitor("monitor")
        assert not c._terms_unavailable and env.terms.reads == [BTC, BTC, BTC]


def test_a_previously_held_coin_marked_unlisted_latches_the_vanish_event():
    with universe_fixture() as env:
        c = build_universe(env)
        c.bootstrap()
        assert c._held == (BTC,) and not c._vanished
        reframe(c, [position(BTC, "0.001", "0", env.fake.now)])
        env.fake.now += seconds(20)
        c._monitor("monitor")
        assert c._held == () and c._vanished and c.status().held_symbol is None
```

- [ ] **Step 2: Run the tests and see them fail**

```bash
focus launch launch_coordinator_universe/
```

Expected: the Task 5 tests pass; `FAIL launch_coordinator_universe/test_book_and_terms_reads_name_the_trade_coin
AssertionError` (the read named no coin), `FAIL .../test_held_coins_and_universe_state_are_pure AttributeError:
module 'execution_launch.coordinator' has no attribute 'held_coins'`, and `AssertionError` for the other three.

- [ ] **Step 3: Implement**

In `execution_launch/coordinator.py`, replace lines 66-67:

```python
from execution_launch.runner import (EvidencePackage, LaunchSession, Runner, StrategyDriver, TickResult,
                                     prepare_launch_session)
```

with:

```python
from execution_launch.runner import (EvidencePackage, LaunchSession, Runner, StrategyDriver, TickResult, dust,
                                     prepare_launch_session)
```

After `history_head_name` (lines 116-118), insert:

```python


def held_coins(account, minimum) -> tuple[str, ...]:
    """The held coins of one account capture (spec section 7): non-dust holdings, the largest value at its mark
    first, equal values by symbol."""
    held = [p for p in account.positions if not dust(p, minimum)]
    return tuple(p.symbol for p in sorted(held, key=lambda p: (-(p.units * p.price), p.symbol)))


def universe_state(snapshot, rule_sha256, at) -> str:
    """The status word for a snapshot at `at`: no_snapshot (none, or not in force), rule_mismatch or in_force."""
    if snapshot is None or not snapshot.valid_from <= at < snapshot.valid_until:
        return "no_snapshot"
    return "in_force" if snapshot.rule_sha256 == rule_sha256 else "rule_mismatch"
```

Replace line 411 (`return self._quote_source.read()` in `_read_book`) with:

```python
            return self._quote_source.read(self._profile.symbol) if self._universe else self._quote_source.read()
```

Replace lines 439-461 (`_refresh_terms`) with:

```python
    def _refresh_terms(self, symbol=None):
        """Called under the work lock, before account/quote timing for a unit. A universe profile reads the terms of
        `symbol` (another coin, after _universe_monitor's flat check) or of its trade coin (spec section 10)."""
        _require(self._terms_source is not None, "COORDINATOR_TERMS_SOURCE_REQUIRED")
        try:
            if self._pending_terms is None:
                target = symbol or self._profile.symbol
                observation = self._terms_source.read(target) if self._universe else self._terms_source.read()
                now = self._time()             # actual receipt completes before the clock is chosen
                self._pending_terms = renew_profile(self._profile, observation, now=now,
                                                    allow_symbol_change=target != self._profile.symbol)
            else:
                now = self._time()             # retry the issued object; never fork from the old snapshot
            renewal = self._pending_terms
            frame = self._latest_frame
            self._runner.refresh_instrument_rules(renewal, now=now,
                                                  account=None if frame is None else frame.accounts[0])
            self._profile = renewal.profile
            self._pending_terms = None
            self._launch = self._runner.launch_session  # same actual PreparedSession, updated wrapper only
            self._terms_blocked = self._terms_unavailable = False
            self._update(instrument_source="", instrument_asof=self._profile.instrument_rules.asof)
            return self._profile.instrument_rules.asof
        except Exception as exc:
            code = _code(exc, "COORDINATOR_TERMS_SOURCE_FAILED")
            if not self._universe or self._held is None or (self._held and code != "TERMS_MARKET_INACTIVE"):
                self._terms_blocked = True     # a held (or not yet known) coin needs fresh rules for its exits
            elif self._held:
                self._vanished = True          # spec section 7: the held coin's market is inactive
            else:
                self._terms_unavailable = True  # no coin held: buys blocked only (TERMS_TARGET_UNAVAILABLE)
            self._update(instrument_source=code, new_entry_blocked=True)
            raise CoordinatorError(code) from None
```

Replace lines 468-469:

```python
        if (self._terms_blocked or rules is None or rules.asof > now
                or now - rules.asof >= TERMS_REFRESH_AGE):
```

with:

```python
        if (self._terms_blocked or self._terms_unavailable or self._pending_terms is not None or rules is None
                or rules.asof > now or now - rules.asof >= TERMS_REFRESH_AGE):
```

After `_maybe_refresh_terms` (ending line 470, `self._refresh_terms()`), insert:

```python

    def _holdings(self, now) -> None:
        """After each universe _publish (spec section 7): the held coins of the new frame, the vanish latch (a coin
        held in the previous frame now marked unlisted at 0), the extra-holding block and its toast, and the
        unsellable-remainder reset once the trade coin is no longer held."""
        account = self._latest_frame.accounts[0]
        held = held_coins(account, self._profile.instrument_rules.min_notional_krw)
        if any(p.symbol in (self._held or ()) and p.price == 0 for p in account.positions):
            self._vanished = True
        self._held, self._extra = held, len(held) > 1
        if self._extra:
            self._toast_once("extra:" + now.astimezone(KST).date().isoformat(), "red",
                             "Two or more coins are held. Buys are blocked. Sell the extra coin in the Upbit app.")
        if self._profile.symbol not in held:
            self._remainder_ticks, self._remainder = 0, False
        self._update(held_symbol=held[0] if held else None, trade_symbol=self._profile.symbol)
```

Replace lines 487-496 in `_monitor`:

```python
                now = self._time()
                self._publish(previous, now, None)
                stage = "control"
                self._update(in_flight="control")
                risk = self._controller.observe(now=now)
                self._ready = True
                reconcile_orders(self._runner, now)
                self._update(new_entry_blocked=risk.new_entry_blocked or self._terms_blocked, risk_reasons=risk.reasons,
                             recovery_status=risk.recovery_status, recovery_deadline=risk.recovery_deadline,
                             orders=self._controller.states())
```

with:

```python
                now = self._time()
                self._publish(previous, now, None)
                if self._universe:
                    self._holdings(now)
                stage = "control"
                self._update(in_flight="control")
                risk = self._controller.observe(now=now)
                self._ready = True
                reconcile_orders(self._runner, now)
                if self._universe:
                    self._snapshot = risk.universe
                    self._update(snapshot_day=None if risk.universe is None else risk.universe.day,
                                 snapshot_sha256=None if risk.universe is None else risk.universe.snapshot_sha256,
                                 universe_state=universe_state(risk.universe, self._profile.universe_rule_sha256, now))
                self._update(new_entry_blocked=risk.new_entry_blocked or self._terms_blocked or self._terms_unavailable,
                             risk_reasons=risk.reasons, recovery_status=risk.recovery_status,
                             recovery_deadline=risk.recovery_deadline, orders=self._controller.states())
```

- [ ] **Step 4: Run the focused and module tests**

```bash
focus launch launch_coordinator_universe/
focus launch launch_coordinator/
focus launch launch_owner_ops/
focus launch launch_instrument_refresh/
```

Expected: only `PASS` lines; each command exits 0. Fixed profiles keep `read()` and `allow_symbol_change=False`.

- [ ] **Step 5: Commit**

```bash
diff <(git diff --stat) <(git diff --stat --ignore-cr-at-eol) && echo LF-OK
git add execution_launch/coordinator.py tests/launch_coordinator_universe.py
git commit -F - <<'EOF'
Read the trade coin's book and terms, track held coins and split terms failures by holding

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

---

### Task 7: Trade-coin choice and renewal while flat

**Files:**
- Modify: `execution_launch/coordinator.py`: runner import (as Task 6 left it); `choose_trade_coin` after
  `universe_state`; `_universe_monitor` after `_holdings`; one call in `_monitor`
- Modify: `execution_launch/live_history.py`: insert before `def _provide(self, observation):` (fd85850 line 477)
- Test: `tests/launch_coordinator_universe.py` (append)

**Interfaces:**
- Consumes: Task 3 `active`, `flat_in`; PR 4d `LiveHistory._universe`, `._state` (`ChooserState.held`),
  `._slots[-1].decision` (`None` at the window end).
- Produces: `choose_trade_coin(held, current, decided, flat) -> str`; `_universe_monitor(now)`;
  `LiveHistory.decided_symbol() -> str | None`; toast key `window-end`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/launch_coordinator_universe.py`:

```python


def test_choose_trade_coin_follows_rules_1_to_3():
    assert C.choose_trade_coin((XRP,), BTC, None, False) == XRP
    assert C.choose_trade_coin((XRP, BTC), BTC, None, True) == BTC
    assert C.choose_trade_coin((XRP, ETH), BTC, BTC, True) == XRP
    assert C.choose_trade_coin((), BTC, XRP, True) == XRP
    assert C.choose_trade_coin((), BTC, XRP, False) == BTC
    assert C.choose_trade_coin((), BTC, None, True) == BTC


def test_a_flat_account_renews_to_the_decided_coin_and_dust_does_not_count():
    with universe_fixture() as env, renewals(env):
        c = build_universe(env)
        reframe(c, [position(BTC, "0.00001", PRICE, env.fake.now)])       # 1,000 KRW of BTC: dust
        env.history.decided = XRP
        c.bootstrap()
        assert env.terms.reads == [XRP] and env.renewed == [(XRP, True)]
        assert c._profile.symbol == XRP and c._runner.profile.symbol == XRP and c.status().trade_symbol == XRP
        c._read_book()
        assert env.books.symbols == [XRP]


def test_an_uncertain_sell_in_the_trade_coin_holds_the_switch_while_the_trade_coin_keeps_renewing():
    """Spec section 19: no symbol change while an IOC sell in A is uncertain with zero A balance; not flat is a
    normal outcome; A keeps renewing; once no order in A is live the next monitor renews to B."""
    from execution_control.controller import OrderState
    with universe_fixture() as env, renewals(env):
        c = build_universe(env)
        reframe(c, [])                                   # zero BTC balance in the frame
        env.history.decided = XRP
        uncertain = OrderState(client_id="fixture-ioc-sell", status="UNKNOWN", order_digest="d" * 64,
                               side="sell", symbol=BTC, updated_at=env.t0)
        reconciled = []
        c._controller.states = lambda: (uncertain,)
        c._controller.reconcile = lambda client_id, *, now: reconciled.append(client_id)
        c.bootstrap()
        s = c.status()
        assert reconciled == ["fixture-ioc-sell"] and s.universe_state == "in_force"   # the monitor ran through
        assert env.terms.reads == [] and env.renewed == [] and c._profile.symbol == BTC
        assert (s.instrument_source, s.account_source, s.reasons) == ("", "", ())
        c.refresh_instrument_rules()                     # A keeps renewing
        assert env.terms.reads == [BTC] and env.renewed == [(BTC, False)] and c._profile.symbol == BTC
        c._controller.states = lambda: ()                # no order in BTC any more
        env.fake.now += seconds(20)
        c._monitor("monitor")
        assert env.terms.reads == [BTC, XRP] and env.renewed == [(BTC, False), (XRP, True)]
        assert c._profile.symbol == XRP


def test_a_restart_holding_another_coin_renews_to_it():
    with universe_fixture() as env, renewals(env):
        c = build_universe(env)
        reframe(c, [position(XRP, "100", "1000", env.fake.now)])
        c.bootstrap()
        assert c._held == (XRP,) and env.renewed == [(XRP, True)] and c._profile.symbol == XRP
        assert c.status().held_symbol == XRP


def test_a_failed_cross_coin_renewal_blocks_buys_and_is_retried():
    with universe_fixture() as env, renewals(env):
        c = build_universe(env)
        reframe(c, [])
        env.history.decided = XRP
        env.terms.fail = FixtureRefusal("TERMS_INQUIRY_FAILED")
        c.bootstrap()
        assert c._terms_unavailable and not c._terms_blocked and c._profile.symbol == BTC
        assert c.status().instrument_source == "TERMS_INQUIRY_FAILED" and c.status().new_entry_blocked
        env.terms.fail = None
        env.fake.now += seconds(20)
        c._monitor("monitor")                    # the trade coin's terms first, then the switch again
        assert env.terms.reads == [XRP, BTC, XRP] and env.renewed == [(BTC, False), (XRP, True)]
        assert c._profile.symbol == XRP and not c._terms_unavailable
    with universe_fixture() as env, renewals(env):
        c = build_universe(env)
        reframe(c, [])
        env.history.decided = XRP
        calls = []

        def validate(renewal, *, previous_profile, now):
            calls.append(renewal.profile.symbol)
            if len(calls) == 1:
                raise FixtureRefusal("RENEWAL_HEAD_CHANGED")
            return renewal.profile
        with patch.object(R, "validate_renewal", validate):
            c.bootstrap()
            assert c._pending_terms is not None and c._terms_unavailable and c._profile.symbol == BTC
            env.fake.now += seconds(20)
            c._monitor("monitor")                # the issued renewal is retried, never re-read
        assert calls == [XRP, XRP] and env.terms.reads == [XRP] and c._profile.symbol == XRP
        assert c._pending_terms is None and not c._terms_unavailable


def test_a_coin_held_after_the_window_end_raises_one_toast():
    with universe_fixture() as env:
        c = build_universe(env)
        env.fake.now = env.window.end + seconds(11)
        c.bootstrap()
        env.fake.now += seconds(20)
        c._monitor("monitor")
        assert [title for title, _ in env.toasts.puts] == [RED] and c._toasted == {"window-end"}


def test_decided_symbol_is_the_latest_decision_coin():
    from execution_launch.live_history import LiveHistory
    from execution_launch.program import ChooserState
    h = object.__new__(LiveHistory)
    h._universe, h._slots, h._state = True, (), ChooserState(held=None, hold_count=0)
    assert h.decided_symbol() is None
    h._slots, h._state = (SimpleNamespace(decision=object()),), ChooserState(held=XRP, hold_count=1)
    assert h.decided_symbol() == XRP
    h._slots += (SimpleNamespace(decision=None),)              # the window-end slot decides nothing
    assert h.decided_symbol() is None
    h._universe, h._slots = False, (SimpleNamespace(decision=object()),)
    assert h.decided_symbol() is None
```

- [ ] **Step 2: Run the tests and see them fail**

```bash
focus launch launch_coordinator_universe/
```

Expected: earlier tests pass; `FAIL .../test_choose_trade_coin_follows_rules_1_to_3 AttributeError: module
'execution_launch.coordinator' has no attribute 'choose_trade_coin'`; `FAIL .../test_decided_symbol_is_the_latest_
decision_coin AttributeError: 'LiveHistory' object has no attribute 'decided_symbol'`; `AssertionError` for the
others (in `test_an_uncertain_sell_...` the last monitor issues no renewal yet).

- [ ] **Step 3: Implement**

In `execution_launch/live_history.py`, insert before `def _provide(self, observation):` (fd85850 line 477; after
PR 4d it follows the universe recording methods):

```python
    def decided_symbol(self) -> str | None:
        """The coin the latest recorded decision targets (spec section 7, rule 3): None for cash, for the window-end
        slot (no decision), before any slot and for a fixed window. Before a slot's record_slot it is the decision
        that slot's tick acts on; after it, the one the next tick acts on."""
        with _LOCK:
            if not self._universe or not self._slots or self._slots[-1].decision is None:
                return None
            return self._state.held

```

In `execution_launch/coordinator.py`, replace the runner import (as Task 6 left it):

```python
from execution_launch.runner import (EvidencePackage, LaunchSession, Runner, StrategyDriver, TickResult, dust,
                                     prepare_launch_session)
```

with:

```python
from execution_launch.runner import (EvidencePackage, LaunchSession, Runner, StrategyDriver, TickResult, active,
                                     dust, flat_in, prepare_launch_session)
```

After `universe_state` (Task 6), insert:

```python


def choose_trade_coin(held, current, decided, flat) -> str:
    """Spec section 7, rules 1 to 3: the one held coin; with two or more, the trade coin if held, else the largest
    (the caller blocks buys); with none, the decided coin while flat in the trade coin, else the trade coin."""
    if len(held) == 1:
        return held[0]
    if held:
        return current if current in held else held[0]
    return decided if decided is not None and flat else current
```

After `_holdings` (Task 6), insert:

```python

    def _universe_monitor(self, now) -> None:
        """Spec section 7, in each monitor unit after _publish and the observe: choose the trade coin; for another
        coin, renew only while flat in the trade coin with no renewal pending (not flat is a normal outcome). Also
        the remainder-after-window-end toast (spec section 12)."""
        account, current = self._latest_frame.accounts[0], self._profile.symbol
        states = self._controller.states()
        flat = flat_in(current, account.positions, states, asof=account.observed_at,
                       minimum=self._profile.instrument_rules.min_notional_krw)
        choice = choose_trade_coin(self._held, current, self._history.decided_symbol(), flat)
        if not self._vanished and choice != current and flat and self._pending_terms is None:
            try:
                self._refresh_terms(choice)
            except CoordinatorError:
                pass                    # buys stay blocked (TERMS_TARGET_UNAVAILABLE); retried at the next monitor
        if now > self._window.end + SLOT_WINDOW and self._held and not any(active(s) for s in states):
            self._toast_once("window-end", "red",
                             "A coin is still held after the window end. Use submit_exit or the Upbit app.")
        self._update(trade_symbol=self._profile.symbol)
```

In `_monitor`, inside the `if self._universe:` block that Task 6 added after `reconcile_orders(self._runner, now)`,
add after its `self._update(snapshot_day=..., ...)` call:

```python
                    self._universe_monitor(now)
```

- [ ] **Step 4: Run the focused and module tests**

```bash
focus launch launch_coordinator_universe/
focus launch launch_coordinator/
focus launch launch_live_history/
focus launch launch_universe_history/
```

Expected: only `PASS` lines; each command exits 0.

- [ ] **Step 5: Commit**

```bash
diff <(git diff --stat) <(git diff --stat --ignore-cr-at-eol) && echo LF-OK
git add execution_launch/coordinator.py execution_launch/live_history.py tests/launch_coordinator_universe.py
git commit -F - <<'EOF'
Choose the trade coin after each monitor and renew to another coin only while flat

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

---

### Task 8: Events, the universe disarm and the remainder counter

**Files:**
- Modify: `execution_launch/coordinator.py`: new methods after `_universe_monitor` (Task 7)
- Test: `tests/launch_coordinator_universe.py` (append)

**Interfaces:**
- Consumes: Task 5 `_disarm_locked`, `_toast_once`; Task 6 `_held`, `_vanished`; PR 2 `FlagRead.ok`, `.flags`.
- Produces: `_events(flags, account, day) -> list[tuple[str, Callable]]` with codes `UNIVERSE_MARKET_VANISHED`,
  `UNIVERSE_OTHER_COIN_WARNING`, `UNIVERSE_HELD_FLAG_UNCERTAIN` (table order); `_vanish() -> tuple[str, ...]`
  (`("COORDINATOR_UNIVERSE_DISARM",)` the first time, `()` after); `_after_tick(last, acted, day)`; toast keys
  `vanished`, `disarm-failed`, `warning:<coin>:<day>`, `held-flag:<day>`, `remainder:<day>`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/launch_coordinator_universe.py`:

```python


def test_events_list_vanish_warning_and_an_uncertain_held_flag_in_table_order():
    with universe_fixture() as env:
        c = build_universe(env)
        at = env.fake.now
        account = SimpleNamespace(positions=(position(BTC, "0.001", PRICE, at), position(ETH, "0.0001", "1000", at),
                                             position(XRP, "0", "1000", at)))
        c._held = (BTC,)
        flags = FlagRead(ok=True, received_at=at, sha256="f" * 64,
                         flags=MappingProxyType({ETH: "warning", XRP: "warning"}))
        events = c._events(flags, account, "2026-11-11")
        assert [code for code, _ in events] == ["UNIVERSE_OTHER_COIN_WARNING", "UNIVERSE_HELD_FLAG_UNCERTAIN"]
        for _ in range(2):
            for _, action in events:
                action()
        assert c._toasted == {"warning:KRW-ETH:2026-11-11", "held-flag:2026-11-11"} and len(env.toasts.puts) == 2
        c._vanished = True
        failed = FlagRead(ok=False, received_at=None, sha256=None, flags=MappingProxyType({}))
        assert [code for code, _ in c._events(failed, account, "2026-11-11")] == ["UNIVERSE_MARKET_VANISHED"]


def test_vanish_stops_and_disarms_once_and_a_failed_kill_is_sticky():
    for recorded, failure in ((True, None), (False, None), (None, FixtureRefusal("FIXTURE_KILL_FAILED"))):
        with universe_fixture() as env:
            c = build_universe(env)
            c.bootstrap()
            kills = stub_kill(c, recorded)
            if failure is not None:
                def kill(session_id, *, reason, now):
                    kills.append(reason)
                    raise failure
                c._controller.kill = kill
            with c._work:
                assert c._vanish() == ("COORDINATOR_UNIVERSE_DISARM",)
                assert c._vanish() == ()
            assert kills == ["market_vanished"] and c.status().strategy_stopped
            assert c.status().disarm_failed is (recorded is not True)
            assert c._toasted == ({"vanished"} if recorded is True else {"disarm-failed"})


def test_the_remainder_block_needs_two_hold_ticks_in_a_row_while_the_trade_coin_is_held():
    with universe_fixture() as env:
        c = build_universe(env)
        c._held = (BTC,)
        hold, submitted = SimpleNamespace(status="hold"), SimpleNamespace(status="submitted")
        c._after_tick(hold, None, "d1")
        c._after_tick(submitted, None, "d1")
        c._after_tick(hold, BTC, "d1")             # the decision is the trade coin itself
        c._after_tick(hold, XRP, "d1")
        assert not c._remainder and c._remainder_ticks == 1
        c._after_tick(hold, None, "d1")
        assert c._remainder and c._toasted == {"remainder:d1"}
        c._after_tick(hold, None, "d1")
        assert len(env.toasts.puts) == 1
```

- [ ] **Step 2: Run the tests and see them fail**

```bash
focus launch launch_coordinator_universe/test_events
focus launch launch_coordinator_universe/test_vanish
focus launch launch_coordinator_universe/test_the_remainder
```

Expected: `FAIL ... AttributeError: 'Coordinator' object has no attribute '_events'` (and `_vanish`,
`_after_tick`).

- [ ] **Step 3: Implement**

In `execution_launch/coordinator.py`, after `_universe_monitor`, insert:

```python

    def _events(self, flags, account, day) -> list:
        """Spec section 7, step 8: the (code, action) pairs this slot raises, in the table's order. Codes are
        recorded with the slot; the actions run after record_slot, each in its own try."""
        events = []
        if self._vanished:
            events.append(("UNIVERSE_MARKET_VANISHED", self._vanish))
        held = set(self._held or ())
        if flags.ok:
            warned = [p.symbol for p in account.positions
                      if p.symbol not in held and p.units > 0 and flags.flags.get(p.symbol) == "warning"]
            if warned:
                def warn():
                    for coin in warned:
                        self._toast_once("warning:" + coin + ":" + day, "red", coin + " is a warning coin. Clear it "
                                         "while it still trades: top it up above 5,000 KRW and sell it in the Upbit app.")
                events.append(("UNIVERSE_OTHER_COIN_WARNING", warn))
            if any(flags.flags.get(coin, "absent") in ("unknown", "absent") for coin in held):
                events.append(("UNIVERSE_HELD_FLAG_UNCERTAIN", lambda: self._toast_once(
                    "held-flag:" + day, "amber", "The held coin's flag is unknown or absent. No buy at this slot.")))
        return events

    def _vanish(self) -> tuple[str, ...]:
        """The vanish event (spec section 7): stop, then the lock-free disarm with reason market_vanished, once per
        window. A kill that records no system disarm counts as failed: sticky disarm_failed and a red toast."""
        if self._disarmed:
            return ()
        self._disarmed = True
        self.stop()
        try:
            result = self._disarm_locked(reason="market_vanished", code="COORDINATOR_UNIVERSE_DISARM",
                                         republish=False)
            failed = result.session_prepared and not result.owner_disarm_recorded
        except CoordinatorError:
            failed = True
        if failed:
            self._update(disarm_failed=True)
            self._toast_once("disarm-failed", "red", "The universe disarm did not complete. Disarm the session by "
                             "hand and handle the coin in the Upbit app.")
        else:
            self._toast_once("vanished", "red", "The held coin left the Upbit KRW market. The strategy is stopped "
                             "and the session disarmed. Handle the coin in the Upbit app.")
        return ("COORDINATOR_UNIVERSE_DISARM",)

    def _after_tick(self, last, acted, day) -> None:
        """The unsellable-remainder event (spec section 7): the trade coin held, the decision the tick acted on
        another coin or cash, and a hold result (the whole sell under the minimum at its limit price), two ticks in a
        row. The block stays until the trade coin is no longer held (_holdings)."""
        if (last is not None and last.status == "hold" and acted != self._profile.symbol
                and self._profile.symbol in (self._held or ())):
            self._remainder_ticks += 1
        else:
            self._remainder_ticks = 0
        if self._remainder_ticks >= 2 and not self._remainder:
            self._remainder = True
            self._toast_once("remainder:" + day, "red", "The held coin's remainder is below the Upbit minimum. "
                             "Buys are blocked. Top it up and sell it in the Upbit app.")
```

- [ ] **Step 4: Run the focused and module tests**

```bash
focus launch launch_coordinator_universe/
focus launch launch_coordinator/test_coordinator_source_static_contract
```

Expected: only `PASS` lines; each command exits 0.

- [ ] **Step 5: Commit**

```bash
diff <(git diff --stat) <(git diff --stat --ignore-cr-at-eol) && echo LF-OK
git add execution_launch/coordinator.py tests/launch_coordinator_universe.py
git commit -F - <<'EOF'
Add the universe events, the vanish disarm and the remainder counter

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

---

### Task 9: The universe slot unit and the allow-list

**Files:**
- Modify: `execution_launch/coordinator.py`: imports after line 46, after line 49, after line 52 and line 60;
  `PRICE_AGE` after the Task 5 constants; `slot_allow` after `choose_trade_coin`; `__init__` (Task 5 block);
  `_refresh_terms` (Task 6); `_slot` before line 506; `_universe_slot` and `_slot_missed` after `_slot` (lines
  503-545)
- Test: `tests/launch_coordinator_universe.py` (append)

**Interfaces:**
- Consumes: PR 1 `rules.universe_top_n(universe, n)`; PR 2 `UniverseSlotSource.read_flags() -> FlagRead`,
  `.read_tickers(markets) -> TickerRead` (never raising), `TickerRead(ok, received_at, sha256, prices)`; PR 4c
  `within_buy_cap(observation) -> bool`; PR 4d `SlotUniverse(snapshot, flags, tickers, allow, reasons, events)`,
  `LiveHistory.record_slot(book, account, *, trade_symbol, universe, tick_size, positions)` (`book` may be `None`;
  `HISTORY_BOOK_OFF_TICK` and `HISTORY_BOOK_MARKET_MISMATCH` refuse before any write, so the slot retries with
  `book=None`), `LiveHistory.recorded_allow`.
- Produces: `PRICE_AGE = timedelta(seconds=60)`;
  `slot_allow(*, snapshot, rule_sha256, n, flags, tickers, slot, blocks=()) -> tuple[frozenset[str], tuple[str, ...]]`;
  `_universe_slot(slot)`; `_slot_missed()`; buy-block reasons `UNIVERSE_EXTRA_HOLDING`,
  `UNIVERSE_REMAINDER_UNSELLABLE`, `TERMS_TARGET_UNAVAILABLE`, `UNIVERSE_NO_SNAPSHOT`, `UNIVERSE_RULE_MISMATCH`,
  `UNIVERSE_FLAGS_UNAVAILABLE`, `UNIVERSE_TICKERS_UNAVAILABLE`; `COORDINATOR_NO_TRADE_BOOK`,
  `COORDINATOR_HISTORY_REFUSED`; toast key `missed`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/launch_coordinator_universe.py`:

```python


def test_a_slot_records_its_universe_inputs_and_ticks_with_the_recorded_allow_list():
    for flag_map, markets, allow in (({BTC: "unflagged", XRP: "unflagged"}, (BTC, XRP), {BTC, XRP}),
                                     ({BTC: "unflagged", XRP: "caution"}, (BTC, XRP), {BTC}),
                                     ({BTC: "unflagged"}, (BTC,), {BTC})):
        with universe_fixture() as env:
            c = build_universe(env)
            c.bootstrap()
            env.slots.flags = flag_map
            seen = allow_seen(c)
            run_slot(env, c, env.window.start)
            assert env.slots.calls == ["flags", ("tickers", markets)] and env.books.symbols == [BTC]
            (book, options), = env.history.rows
            u = options["universe"]
            assert book is not None and options["trade_symbol"] == BTC
            assert options["tick_size"] == env.profile.instrument_rules.tick_size
            assert options["positions"] == c._latest_frame.accounts[0].positions
            assert u.snapshot is env.universe and u.allow == frozenset(allow) and u.reasons == () and u.events == ()
            s = c.status()
            assert (s.allow_count, s.buy_block_reasons, s.held_flag) == (len(allow), (), "unflagged")
            assert s.last_tick.status == "hold" and s.reasons == () and seen == [frozenset(allow)]


def test_a_stale_ticker_price_leaves_the_coin_out():
    with universe_fixture() as env:
        c = build_universe(env)
        c.bootstrap()
        env.slots.age = seconds(120)
        run_slot(env, c, env.window.start)
        assert env.history.rows[0][1]["universe"].allow == frozenset()


def test_a_failed_flag_or_ticker_read_blocks_buys_only():
    for failed, calls, reasons in (({"flags"}, ["flags"],
                                    ("UNIVERSE_FLAGS_UNAVAILABLE", "UNIVERSE_TICKERS_UNAVAILABLE")),
                                   ({"tickers"}, ["flags", ("tickers", (BTC, XRP))],
                                    ("UNIVERSE_TICKERS_UNAVAILABLE",))):
        with universe_fixture() as env:
            c = build_universe(env)
            c.bootstrap()
            env.slots.fail = failed
            seen = allow_seen(c)
            run_slot(env, c, env.window.start)
            u = env.history.rows[0][1]["universe"]
            assert env.slots.calls == calls and u.allow == frozenset() and u.reasons == reasons
            assert type(u.tickers) is TickerRead and not u.tickers.ok
            s = c.status()
            assert seen == [frozenset()] and s.last_tick.status == "hold" and s.buy_block_reasons == reasons
            assert not s.window_ended_missed_slot


def test_no_trade_book_records_the_slot_and_skips_the_tick():
    with universe_fixture() as env:
        c = build_universe(env)
        c.bootstrap()
        env.books.fail = True
        seen = allow_seen(c)
        run_slot(env, c, env.window.start)
        (book, options), = env.history.rows
        s = c.status()
        assert book is None and seen == [] and s.last_tick is None
        assert s.reasons == ("COORDINATOR_NO_TRADE_BOOK",) and not s.window_ended_missed_slot
        assert "BOOK-SECRET" not in repr(s)


def test_a_failed_record_skips_the_tick_and_ends_the_window():
    with universe_fixture() as env:
        c = build_universe(env)
        c.bootstrap()
        env.history.fail = FixtureRefusal("HISTORY_INPUT_REQUIRED")
        seen = allow_seen(c)
        run_slot(env, c, env.window.start)
        s = c.status()
        assert seen == [] and s.last_tick is None and s.window_ended_missed_slot and not c._runner.stopped
        assert s.reasons == ("HISTORY_INPUT_REQUIRED",) and c._toasted == {"missed"}


def test_an_off_tick_or_wrong_market_book_is_recorded_without_the_book_and_skips_the_tick():
    """PR 4d contract: these two refusals write nothing, so the slot is recorded again with book=None."""
    for code in ("HISTORY_BOOK_OFF_TICK", "HISTORY_BOOK_MARKET_MISMATCH"):
        with universe_fixture() as env:
            c = build_universe(env)
            c.bootstrap()
            record, books = env.history.record_slot, []

            def refusing(book, account, **options):
                books.append(book)
                if book is not None:
                    raise FixtureRefusal(code)
                return record(book, account, **options)
            env.history.record_slot = refusing
            seen = allow_seen(c)
            run_slot(env, c, env.window.start)
            (book, _), = env.history.rows
            s = c.status()
            assert books[0] is not None and books[1:] == [None] and book is None and seen == []
            assert s.reasons == ("COORDINATOR_NO_TRADE_BOOK",) and s.last_tick is None
            assert not s.window_ended_missed_slot and not c._runner.stopped
    with universe_fixture() as env:
        c = build_universe(env)
        c.bootstrap()
        env.history.fail = FixtureRefusal("HISTORY_BOOK_OFF_TICK")     # the retry is refused too: the slot is missed
        run_slot(env, c, env.window.start)
        s = c.status()
        assert env.history.rows == [] and s.window_ended_missed_slot and s.reasons == ("HISTORY_BOOK_OFF_TICK",)


def test_terms_blocked_refuses_the_slot_only_while_a_coin_is_held():
    for positions, recorded in ((None, False), ([], True)):
        with universe_fixture() as env:
            c = build_universe(env)
            if positions is not None:
                reframe(c, positions)
            c.bootstrap()
            c._terms_blocked = True
            run_slot(env, c, env.window.start)
            s = c.status()
            if recorded:
                assert env.history.rows[0][1]["universe"].reasons == ("TERMS_TARGET_UNAVAILABLE",)
                assert s.last_tick.status == "hold" and not s.window_ended_missed_slot
            else:
                assert env.history.rows == [] and s.reasons == ("COORDINATOR_CURRENT_TERMS_REQUIRED",)
                assert s.window_ended_missed_slot and env.slots.calls == []


def test_an_extra_holding_blocks_buys():
    with universe_fixture() as env:
        c = build_universe(env)
        reframe(c, [position(BTC, "0.001", PRICE, env.fake.now), position(XRP, "100", "1000", env.fake.now)])
        c.bootstrap()
        seen = allow_seen(c)
        run_slot(env, c, env.window.start)
        u = env.history.rows[0][1]["universe"]
        assert u.allow == frozenset() and u.reasons == ("UNIVERSE_EXTRA_HOLDING",) and seen == [frozenset()]
        assert c.status().last_tick.status == "hold" and not c._runner.stopped


def test_a_trade_coin_below_its_buy_cap_is_left_out_of_the_allow_list():
    with universe_fixture() as env, renewals(env):
        c = build_universe(env)
        c.bootstrap()
        env.terms.within = False
        c.refresh_instrument_rules()
        run_slot(env, c, env.window.start)
        assert env.history.rows[0][1]["universe"].allow == frozenset({XRP})


def test_after_a_partial_sell_leaves_dust_the_next_slot_reads_and_allows_the_new_coin():
    """Spec section 19: a partial IOC sell leaves under 5,000 KRW of A, the monitor renews to B, and the next slot
    reads B's book, records B as the trade coin and allows B. The buy itself is not run here (the book double is a
    KRW-BTC book; runner buys are tested up to Controller.reserve in tests/launch_runner_universe.py)."""
    with universe_fixture() as env, renewals(env):
        c = build_universe(env)
        reframe(c, [position(BTC, "0.00001", PRICE, env.fake.now)])       # 1,000 KRW of BTC left: dust
        env.history.decided = XRP
        c.bootstrap()
        assert c._profile.symbol == XRP
        run_slot(env, c, env.window.start)
        (_, options), = env.history.rows
        assert env.books.symbols == [XRP] and options["trade_symbol"] == XRP
        assert options["universe"].allow == frozenset({BTC, XRP})


def test_slot_allow_is_the_unflagged_priced_top_n_or_empty_with_reasons():
    at = datetime(2026, 11, 11, 1, 0, tzinfo=timezone.utc)
    snapshot = universe_snapshot(at)
    flags = FlagRead(ok=True, received_at=at, sha256="f" * 64,
                     flags=MappingProxyType({BTC: "unflagged", XRP: "unflagged"}))
    prices = TickerRead(ok=True, received_at=at, sha256="7" * 64,
                        prices=MappingProxyType({BTC: (PRICE, at - seconds(60)), XRP: (D(1000), at - seconds(61))}))
    common = dict(snapshot=snapshot, rule_sha256=RULE, flags=flags, tickers=prices, slot=at)
    assert C.slot_allow(n=2, **common) == (frozenset({BTC}), ())
    assert C.slot_allow(n=1, **(common | {"tickers": replace(prices, prices=MappingProxyType(
        {XRP: (D(1000), at)}))})) == (frozenset(), ())
    no_flags = FlagRead(ok=False, received_at=None, sha256=None, flags=MappingProxyType({}))
    no_prices = TickerRead(ok=False, received_at=None, sha256=None, prices=MappingProxyType({}))
    assert C.slot_allow(snapshot=None, rule_sha256=RULE, n=2, flags=no_flags, tickers=no_prices, slot=at,
                        blocks=("UNIVERSE_EXTRA_HOLDING",)) == (frozenset(), (
        "UNIVERSE_EXTRA_HOLDING", "UNIVERSE_NO_SNAPSHOT", "UNIVERSE_FLAGS_UNAVAILABLE", "UNIVERSE_TICKERS_UNAVAILABLE"))
    assert C.slot_allow(n=2, **(common | {"rule_sha256": "f" * 64})) == (frozenset(), ("UNIVERSE_RULE_MISMATCH",))
```

- [ ] **Step 2: Run the tests and see them fail**

```bash
focus launch launch_coordinator_universe/
```

Expected: earlier tests pass; `FAIL .../test_slot_allow_is_the_unflagged_priced_top_n_or_empty_with_reasons
AttributeError: module 'execution_launch.coordinator' has no attribute 'slot_allow'`; the slot tests fail with
`AssertionError`, `IndexError` or `ValueError` (the fixed `_slot` runs: no flag read, and the double's
`record_slot` refuses a call without the universe keywords, so no row is recorded).

- [ ] **Step 3: Implement**

In `execution_launch/coordinator.py`:

After line 46 (`import threading`), add:

```python
from types import MappingProxyType
```

After line 49 (`from core.compliance.model import KST`), add:

```python
from core.compliance.rules import universe_top_n
```

After line 52 (`from execution_accounts.baseline_store import CheckpointStore`), add:

```python
from execution_accounts.instrument_terms import within_buy_cap
from execution_accounts.universe import TickerRead
```

(`execution_accounts.universe` imports only `Answer` and `inquiry_clock` from the transport, as `instrument_terms`
already does; the static contract pins only the coordinator's own import lines.)

Replace line 60 (`from execution_launch.live_history import HistoryChain, LiveHistory`) with:

```python
from execution_launch.live_history import HistoryChain, LiveHistory, SlotUniverse
```

After `UNIVERSE_WINDOW_MAX = ...` (Task 5), add:

```python
PRICE_AGE = timedelta(seconds=60)         # a ticker price is defined within 60 s of the slot (PR 4d PRICE_WINDOW_MS)
```

After `choose_trade_coin` (Task 7), insert:

```python


def slot_allow(*, snapshot, rule_sha256, n, flags, tickers, slot, blocks=()) -> tuple[frozenset, tuple[str, ...]]:
    """Spec section 7: the slot's buy allow-list and buy-block reasons. The list is the top-N of the snapshot in force
    that are unflagged in this slot's flag read and priced within PRICE_AGE of the slot in its ticker read; it is
    empty when any reason is set."""
    reasons = tuple(blocks)
    state = universe_state(snapshot, rule_sha256, slot)
    if state != "in_force":
        reasons += ("UNIVERSE_NO_SNAPSHOT" if state == "no_snapshot" else "UNIVERSE_RULE_MISMATCH",)
    if not flags.ok:
        reasons += ("UNIVERSE_FLAGS_UNAVAILABLE",)
    if not tickers.ok:
        reasons += ("UNIVERSE_TICKERS_UNAVAILABLE",)
    if reasons:
        return frozenset(), reasons
    return frozenset(m for m in universe_top_n(snapshot, n) if flags.flags.get(m) == "unflagged"
                     and m in tickers.prices and abs(tickers.prices[m][1] - slot) <= PRICE_AGE), ()
```

In `__init__`, after the Task 5 line `self._remainder_ticks, self._remainder = 0, False`, add:

```python
        self._within_cap = True                 # PR 4c: the trade coin's last terms read is within its v2 buy cap
```

In `_refresh_terms` (as Task 6 left it), after the line
`observation = self._terms_source.read(target) if self._universe else self._terms_source.read()`, add:

```python
                if self._universe:
                    # ponytail: follows the last read even if its renewal fails; buys are blocked while one is pending
                    self._within_cap = within_buy_cap(observation)
```

In `_slot`, before line 506 (`with self._work:`), insert:

```python
        if self._universe:
            return self._universe_slot(slot)
```

After `_slot` (ending line 545, `self._update(in_flight="")`), insert:

```python

    def _universe_slot(self, slot) -> None:
        """Spec section 7's slot unit for a universe profile: the gate, the trade coin's book at the prefetch lead
        (None when unavailable, never a refusal), the account prefetch, the flag and ticker reads, the sample,
        _publish, record_slot in its own try, then one tick with the recorded allow-list, only when the slot is
        recorded, the strategy is not stopping and the book is available."""
        with self._work:
            stage, recorded = "gate", False
            try:
                _require(self._ready, "COORDINATOR_STARTUP_RECONCILE_REQUIRED")
                _require(not (self._terms_blocked and self._holding()), "COORDINATOR_CURRENT_TERMS_REQUIRED")
                stage = "account"
                previous = self._load_previous()
                try:
                    book = self._read_book()
                except CoordinatorError:
                    book = None                              # step 2: unavailable, never a refusal
                if self._stopping.is_set():
                    return
                self._prefetch(previous)
                if self._stopping.is_set():
                    return
                flags = self._slot_source.read_flags()
                in_force = universe_state(self._snapshot, self._profile.universe_rule_sha256, slot) == "in_force"
                markets = tuple(m for m in self._snapshot.listed if m in flags.flags) if flags.ok and in_force else ()
                if markets:
                    tickers = self._slot_source.read_tickers(markets)
                else:                                        # no ticker read (step 5)
                    tickers = TickerRead(ok=False, received_at=None, sha256=None, prices=MappingProxyType({}))
                stage = "quote"
                self._await(slot)
                if self._stopping.is_set():
                    return
                now = self._time()
                _require(slot <= now <= slot + SLOT_WINDOW, "COORDINATOR_SLOT_WINDOW_MISSED")
                if book is not None:
                    try:
                        sample_prefetched_book(book, slot=slot, sampled_at=now)
                    except Exception:
                        book = None                          # a stale book is unavailable, never a refusal
                stage = "account"
                observation = self._publish(previous, now, book)
                self._holdings(now)
                stage = "control"
                blocks = ()
                if self._extra:
                    blocks += ("UNIVERSE_EXTRA_HOLDING",)
                if self._remainder:
                    blocks += ("UNIVERSE_REMAINDER_UNSELLABLE",)
                if self._terms_unavailable or self._terms_blocked or self._pending_terms is not None:
                    blocks += ("TERMS_TARGET_UNAVAILABLE",)
                allow, reasons = slot_allow(snapshot=self._snapshot, rule_sha256=self._profile.universe_rule_sha256,
                                            n=self._program.max_candidates, flags=flags, tickers=tickers, slot=slot,
                                            blocks=blocks)
                if not self._within_cap:
                    allow -= {self._profile.symbol}
                held = self._held[0] if self._held else None
                self._update(in_flight="history", allow_count=len(allow), buy_block_reasons=reasons,
                             held_flag=flags.flags.get(held, "absent") if flags.ok and held else None)
                options = dict(trade_symbol=self._profile.symbol,
                               universe=SlotUniverse(snapshot=self._snapshot, flags=flags, tickers=tickers,
                                                     allow=allow, reasons=reasons, events=()),
                               tick_size=self._profile.instrument_rules.tick_size,
                               positions=self._latest_frame.accounts[0].positions)
                try:
                    try:
                        self._history.record_slot(book, observation, **options)
                    except Exception as exc:
                        if book is None or _code(exc, "") not in ("HISTORY_BOOK_OFF_TICK",
                                                                  "HISTORY_BOOK_MARKET_MISMATCH"):
                            raise
                        book = None                          # PR 4d: refused before any write; record without it
                        self._history.record_slot(None, observation, **options)
                    recorded = True
                except Exception as exc:
                    reasons += (_code(exc, "COORDINATOR_HISTORY_REFUSED"),)
                    self._slot_missed()
                if not recorded or self._stopping.is_set():
                    self._update(reasons=reasons)
                    return
                if book is None:
                    self._update(reasons=reasons + ("COORDINATOR_NO_TRADE_BOOK",))
                    return
                tick = self._time()
                _require(tick <= slot + SLOT_WINDOW, "COORDINATOR_SLOT_WINDOW_MISSED")
                self._update(in_flight="control")
                results = self._runner.run((tick,), max_steps=1, should_stop=self._stopping.is_set,
                                           entry_allow=self._history.recorded_allow)
                last = results[0] if results else None
                self._update(last_tick=last, orders=self._controller.states(),
                             reasons=reasons + (() if last is None else last.reasons))
            except Exception as exc:
                self._refused(stage, _code(exc, "COORDINATOR_DEPENDENCY_REFUSED"), slot=True)
                if not recorded:
                    self._slot_missed()
            finally:
                self._board.clear()
                self._update(in_flight="")

    def _slot_missed(self) -> None:
        """Spec section 12: a slot the history did not record ends the window. Sticky status and, while a coin is
        held, one red toast."""
        self._update(window_ended_missed_slot=True)
        if self._held:
            self._toast_once("missed", "red", "A missed slot ended the window while a coin is held. Use submit_exit "
                             "or the Upbit app.")
```

- [ ] **Step 4: Run the focused and module tests**

```bash
focus launch launch_coordinator_universe/
focus launch launch_coordinator/
focus launch launch_owner_ops/
```

Expected: only `PASS` lines; each command exits 0. Fixed profiles still run `_slot` unchanged.

- [ ] **Step 5: Commit**

```bash
diff <(git diff --stat) <(git diff --stat --ignore-cr-at-eol) && echo LF-OK
git add execution_launch/coordinator.py tests/launch_coordinator_universe.py
git commit -F - <<'EOF'
Run the universe slot unit with flag and ticker reads and the recorded allow-list

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

---

### Task 10: Events inside the slot unit

**Files:**
- Modify: `execution_launch/coordinator.py`: `_universe_slot` (Task 9), from `stage = "control"` through the last
  `self._update(last_tick=...)` of its `try` body
- Test: `tests/launch_coordinator_universe.py` (append)

**Interfaces:**
- Consumes: Task 8 `_events`, `_after_tick`; Task 7 `history.decided_symbol()` (before `record_slot` it is the
  decision this slot's tick acts on).
- Produces: the slot records the event codes in `SlotUniverse.events`, runs each action after the record in its own
  `try` (`COORDINATOR_EVENT_FAILED` and toast key `event-failed:<code>:<day>` on failure), adds the buy-block reason
  `UNIVERSE_HELD_FLAG_UNCERTAIN`, and feeds `_after_tick`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/launch_coordinator_universe.py`:

```python


def test_a_vanished_held_coin_disarms_once_after_the_record_and_skips_the_tick():
    with universe_fixture() as env:
        c = build_universe(env)
        c.bootstrap()
        kills = stub_kill(c, True)
        reframe(c, [position(BTC, "0.001", "0", env.fake.now)])
        seen = allow_seen(c)
        run_slot(env, c, env.window.start)
        (_, options), = env.history.rows
        assert options["universe"].events == ("UNIVERSE_MARKET_VANISHED",)
        assert kills == ["market_vanished"] and seen == [] and c.status().strategy_stopped and c._disarmed
        assert c.status().reasons == ("COORDINATOR_UNIVERSE_DISARM",) and c._toasted == {"vanished"}


def test_a_failed_universe_disarm_is_sticky_and_the_row_is_still_recorded():
    """A kill that records no system disarm, and (spec section 19) Controller.kill raising inside _disarm_locked."""
    for raising in (False, True):
        with universe_fixture() as env:
            c = build_universe(env)
            c.bootstrap()
            kills = stub_kill(c, False)
            if raising:
                def kill(session_id, *, reason, now):
                    kills.append(reason)
                    raise FixtureRefusal("FIXTURE_KILL_FAILED")
                c._controller.kill = kill
            reframe(c, [position(BTC, "0.001", "0", env.fake.now)])
            run_slot(env, c, env.window.start)
            s = c.status()
            assert len(env.history.rows) == 1 and kills == ["market_vanished"] and s.strategy_stopped
            assert s.disarm_failed and c._toasted == {"disarm-failed"} and env.toasts.puts[0][0] == RED
            assert s.reasons == ("COORDINATOR_UNIVERSE_DISARM",) and s.last_tick is None


def test_a_slow_toast_never_delays_the_slot():
    with universe_fixture() as env:
        c = build_universe(env)
        reframe(c, [position(BTC, "0.001", PRICE, env.fake.now), position(XRP, "100", "1000", env.fake.now)])
        release, shown = threading.Event(), []
        c._toasts = ToastQueue(lambda title, body: release.wait(5) and shown.append(title))
        c.bootstrap()                                    # queues the extra-holding toast; the worker blocks in it
        worker = c._toasts._thread
        run_slot(env, c, env.window.start)
        assert len(env.history.rows) == 1 and c.status().last_tick.status == "hold"
        assert shown == [] and worker.is_alive()
        release.set()
        worker.join(5)
        assert shown == [RED]


def test_a_failing_event_sets_a_reason_and_a_toast_and_the_tick_still_runs():
    with universe_fixture() as env:
        c = build_universe(env)
        c.bootstrap()
        env.slots.flags = {BTC: "unflagged", XRP: "unflagged", ETH: "warning"}
        reframe(c, [position(BTC, "0.001", PRICE, env.fake.now), position(ETH, "0.0001", "1000", env.fake.now)])
        toast_once = c._toast_once

        def failing(key, level, body):
            if key.startswith("warning:"):
                raise RuntimeError("TOAST-SECRET-1")
            toast_once(key, level, body)
        c._toast_once = failing
        run_slot(env, c, env.window.start)
        s = c.status()
        assert env.history.rows[0][1]["universe"].events == ("UNIVERSE_OTHER_COIN_WARNING",)
        assert s.reasons == ("COORDINATOR_EVENT_FAILED",) and s.last_tick.status == "hold"
        assert [k for k in c._toasted if k.startswith("event-failed:UNIVERSE_OTHER_COIN_WARNING:")]
        assert "TOAST-SECRET" not in repr(s)


def test_an_uncertain_held_flag_blocks_buys_and_forces_no_sale():
    for flag_map, held_flag in (({XRP: "unflagged"}, "absent"), ({BTC: "unknown", XRP: "unflagged"}, "unknown")):
        with universe_fixture() as env:
            c = build_universe(env)
            c.bootstrap()
            env.slots.flags = flag_map
            seen = allow_seen(c)
            run_slot(env, c, env.window.start)
            u = env.history.rows[0][1]["universe"]
            assert u.events == ("UNIVERSE_HELD_FLAG_UNCERTAIN",) and u.allow == frozenset()
            assert u.reasons == ("UNIVERSE_HELD_FLAG_UNCERTAIN",) and seen == [frozenset()]
            assert c.status().held_flag == held_flag and env.adapter.requests == []
            assert [k for k in c._toasted if k.startswith("held-flag:")]


def test_two_hold_ticks_on_another_decision_set_the_remainder_block():
    with universe_fixture() as env:
        c = build_universe(env)
        c.bootstrap()
        env.history.decided = XRP                 # each tick acts on a decision for another coin and holds
        for k in range(3):
            run_slot(env, c, env.window.start + seconds(60 * k))
        reasons = [options["universe"].reasons for _, options in env.history.rows]
        assert reasons == [(), (), ("UNIVERSE_REMAINDER_UNSELLABLE",)]
        assert c._remainder and [k for k in c._toasted if k.startswith("remainder:")]


def test_a_failed_record_still_runs_the_events():
    with universe_fixture() as env:
        c = build_universe(env)
        c.bootstrap()
        kills = stub_kill(c, True)
        env.history.fail = FixtureRefusal("HISTORY_INPUT_REQUIRED")
        reframe(c, [position(BTC, "0.001", "0", env.fake.now)])
        run_slot(env, c, env.window.start)
        s = c.status()
        assert kills == ["market_vanished"] and env.history.rows == [] and s.window_ended_missed_slot
        assert s.reasons == ("HISTORY_INPUT_REQUIRED", "COORDINATOR_UNIVERSE_DISARM")
```

- [ ] **Step 2: Run the tests and see them fail**

```bash
focus launch launch_coordinator_universe/
```

Expected: earlier tests pass; six of the seven new tests `FAIL` with `AssertionError` (no event code is recorded
and no action runs). `test_a_slow_toast_never_delays_the_slot` already passes (the queue and the extra-holding toast
are Tasks 1, 5 and 6); it stays as the section 19 pin with the events running in the slot.

- [ ] **Step 3: Implement**

In `_universe_slot`, replace the block from `stage = "control"` (the one after `self._holdings(now)`) through
`self._update(last_tick=last, orders=self._controller.states(), reasons=reasons + (() if last is None else
last.reasons))` with:

```python
                stage = "control"
                day = now.astimezone(KST).date().isoformat()
                events = self._events(flags, self._latest_frame.accounts[0], day)
                codes = tuple(code for code, _ in events)
                blocks = ()
                if self._extra:
                    blocks += ("UNIVERSE_EXTRA_HOLDING",)
                if self._remainder:
                    blocks += ("UNIVERSE_REMAINDER_UNSELLABLE",)
                if self._terms_unavailable or self._terms_blocked or self._pending_terms is not None:
                    blocks += ("TERMS_TARGET_UNAVAILABLE",)
                if "UNIVERSE_HELD_FLAG_UNCERTAIN" in codes:
                    blocks += ("UNIVERSE_HELD_FLAG_UNCERTAIN",)         # spec section 7: no buy at this slot
                allow, reasons = slot_allow(snapshot=self._snapshot, rule_sha256=self._profile.universe_rule_sha256,
                                            n=self._program.max_candidates, flags=flags, tickers=tickers, slot=slot,
                                            blocks=blocks)
                if not self._within_cap:
                    allow -= {self._profile.symbol}
                held = self._held[0] if self._held else None
                self._update(in_flight="history", allow_count=len(allow), buy_block_reasons=reasons,
                             held_flag=flags.flags.get(held, "absent") if flags.ok and held else None)
                acted = self._history.decided_symbol()       # before the record: the decision this tick acts on
                options = dict(trade_symbol=self._profile.symbol,
                               universe=SlotUniverse(snapshot=self._snapshot, flags=flags, tickers=tickers,
                                                     allow=allow, reasons=reasons, events=codes),
                               tick_size=self._profile.instrument_rules.tick_size,
                               positions=self._latest_frame.accounts[0].positions)
                try:
                    try:
                        self._history.record_slot(book, observation, **options)
                    except Exception as exc:
                        if book is None or _code(exc, "") not in ("HISTORY_BOOK_OFF_TICK",
                                                                  "HISTORY_BOOK_MARKET_MISMATCH"):
                            raise
                        book = None                          # PR 4d: refused before any write; record without it
                        self._history.record_slot(None, observation, **options)
                    recorded = True
                except Exception as exc:
                    reasons += (_code(exc, "COORDINATOR_HISTORY_REFUSED"),)
                    self._slot_missed()
                for code, action in events:                  # step 8: each event in its own try
                    try:
                        reasons += action() or ()
                    except Exception:
                        reasons += ("COORDINATOR_EVENT_FAILED",)
                        self._toast_once("event-failed:" + code + ":" + day, "red",
                                         code + " did not complete. Check the console status.")
                if not recorded or self._stopping.is_set():
                    self._update(reasons=reasons)
                    return
                if book is None:
                    self._update(reasons=reasons + ("COORDINATOR_NO_TRADE_BOOK",))
                    return
                tick = self._time()
                _require(tick <= slot + SLOT_WINDOW, "COORDINATOR_SLOT_WINDOW_MISSED")
                self._update(in_flight="control")
                results = self._runner.run((tick,), max_steps=1, should_stop=self._stopping.is_set,
                                           entry_allow=self._history.recorded_allow)
                last = results[0] if results else None
                self._after_tick(last, acted, day)
                self._update(last_tick=last, orders=self._controller.states(),
                             reasons=reasons + (() if last is None else last.reasons))
```

- [ ] **Step 4: Run the focused and module tests**

```bash
focus launch launch_coordinator_universe/
focus launch launch_coordinator/
```

Expected: only `PASS` lines; each command exits 0.

- [ ] **Step 5: Commit**

```bash
diff <(git diff --stat) <(git diff --stat --ignore-cr-at-eol) && echo LF-OK
git add execution_launch/coordinator.py tests/launch_coordinator_universe.py
git commit -F - <<'EOF'
Raise the universe events after each slot record and track the unsellable remainder

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

---

### Task 11: A gap that misses slots ends the window visibly

**Files:**
- Modify: `execution_launch/coordinator.py`: `_gap` lines 570-572
- Test: `tests/launch_coordinator_universe.py` (append)

**Interfaces:**
- Consumes: `CancellableTimer.missed` (`coordinator.py:207-208`); Task 9 `_slot_missed`.
- Produces: a universe gap with missed slots sets `window_ended_missed_slot` and the `missed` toast.

- [ ] **Step 1: Write the failing test**

Append to `tests/launch_coordinator_universe.py`:

```python


def test_a_suspend_that_misses_slots_sets_the_sticky_field_and_one_toast():
    with universe_fixture() as env:
        c = build_universe(env)
        env.fake.at(env.t0 + seconds(50), lambda: setattr(env.fake, "now", env.fake.now + seconds(120)))
        status = c.run()
        assert status.missed_slots == 2 and status.window_ended_missed_slot and "missed" in c._toasted
    with universe_fixture() as env:
        c = build_universe(env)
        status = c.run()
        assert status.missed_slots == 0 and not status.window_ended_missed_slot and len(env.history.rows) == 3
        assert "missed" not in c._toasted
```

- [ ] **Step 2: Run the test and see it fail**

```bash
focus launch launch_coordinator_universe/test_a_suspend
```

Expected: `FAIL ... AssertionError` (the missed slots never reach `_universe_slot`, so nothing sets the field).

- [ ] **Step 3: Implement**

In `_gap`, after line 572 (`self._monitor("gap")`), insert at the same indentation:

```python
            if self._universe and missed["slot"] and not self._stopping.is_set():
                self._slot_missed()          # spec section 12: a missed slot ends the history window
```

- [ ] **Step 4: Run the focused and module tests**

```bash
focus launch launch_coordinator_universe/
focus launch launch_coordinator/
```

Expected: only `PASS` lines; each command exits 0.

- [ ] **Step 5: Commit**

```bash
diff <(git diff --stat) <(git diff --stat --ignore-cr-at-eol) && echo LF-OK
git add execution_launch/coordinator.py tests/launch_coordinator_universe.py
git commit -F - <<'EOF'
Mark the window ended when a gap misses universe slots

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

---

### Task 12: The odds batch, preparation with a batch and the console

**Files:**
- Modify: `execution_launch/coordinator.py`: import after line 56; `prepare` lines 710 and 729; new `odds_batch`
  after `prepare` (ending line 735)
- Modify: `tools/owner/launch.py`: import after line 33; `__init__` after line 190; `status` lines 205-216;
  `prepare` lines 226-227; new `odds` after `prepare` (ending line 231); `command` lines 257-262
- Test: `tests/launch_coordinator_universe.py` (append)

**Interfaces:**
- Consumes: PR 4a `run_batch(controller, template, bars, *, n, now, clock) -> UniverseBatch` (`.batch_digest`,
  `.coins[*].passed`); PR 2 `daily_bars(markets, *, now, clock)`; PR 1 `universe_top_n`; Task 4.
- Produces: `Coordinator.odds_batch(template, read_bars)`; `Coordinator.prepare(..., universe_batch=None)`;
  `OwnerRuntime.odds() -> dict`; console command `odds`; status keys `held_symbol`, `trade_symbol`, `snapshot_day`
  (ISO date or `None`), `snapshot_sha256`, `universe_state`, `held_flag`, `allow_count`, `buy_block_reasons` (list),
  `disarm_failed`, `window_ended_missed_slot`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/launch_coordinator_universe.py`:

```python


def test_the_odds_batch_runs_off_the_work_lock_over_the_snapshot_top_n():
    with universe_fixture() as env:
        c = build_universe(env)
        c.bootstrap()
        seen, result = [], []

        def read_bars(markets, *, now, clock):
            seen.append(("bars", markets, now))
            return {"bars": markets}

        def run_batch(controller, template, bars, *, n, now, clock):
            seen.append(("batch", controller is c._controller, template, bars, n, now))
            return "BATCH"
        with patch.object(C, "run_batch", run_batch), c._work:
            worker = threading.Thread(target=lambda: result.append(c.odds_batch("TEMPLATE", read_bars)))
            worker.start()
            worker.join(5)
        now = seen[0][2]
        assert result == ["BATCH"]
        assert seen == [("bars", (BTC, XRP), now), ("batch", True, "TEMPLATE", {"bars": (BTC, XRP)}, 2, now)]

        def broken(markets, *, now, clock):
            raise RuntimeError("CANDLE-SECRET-1")
        refused(lambda: c.odds_batch("TEMPLATE", broken), "COORDINATOR_ODDS_BATCH_FAILED")
    with universe_fixture() as env:
        refused(lambda: build_universe(env).odds_batch("TEMPLATE", None), "UNIVERSE_NO_SNAPSHOT")
    with fixture() as env:
        refused(lambda: build(env).odds_batch("TEMPLATE", None), "COORDINATOR_UNIVERSE_REQUIRED")


def test_prepare_passes_the_batch_to_prepare_launch_session():
    with universe_fixture() as env:
        c = build_universe(env)
        c.bootstrap()
        seen = []

        def prepare(**kwargs):
            seen.append(kwargs["universe_batch"])
            raise FixtureRefusal("FIXTURE_PREPARE_REACHED")
        plan, inputs, seed = selected(env.fake.now)
        with patch.object(C, "prepare_launch_session", prepare):
            refused(lambda: c.prepare(selected_plan=plan, inputs=inputs, selection_seed_hex=seed,
                                      universe_batch="BATCH"), "FIXTURE_PREPARE_REACHED")
            refused(lambda: c.prepare(selected_plan=plan, inputs=inputs, selection_seed_hex=seed),
                    "FIXTURE_PREPARE_REACHED")
        assert seen == ["BATCH", None]


def test_the_console_odds_command_keeps_the_batch_for_prepare_and_status_shows_universe_fields():
    from tools.owner import launch as O
    with universe_fixture() as env:
        c = build_universe(env)
        c.bootstrap()
        batch = SimpleNamespace(batch_digest="b" * 64, coins=(SimpleNamespace(market=BTC, passed=True),
                                                             SimpleNamespace(market=XRP, passed=False)))
        calls = []
        plan, inputs, seed = selected(env.fake.now)
        runtime = O.OwnerRuntime(c, preparation_provider=lambda: O.PreparationInputs(
            selected_plan=plan, inputs=inputs, selection_seed_hex=seed))
        prepared = SimpleNamespace(session_id="Lfixture-universe", prepared_at=env.fake.now, expires_at=env.fake.now,
                                   record_digest="c" * 64)
        with patch.object(c, "odds_batch", lambda template, read_bars: calls.append((template, read_bars)) or batch), \
                patch.object(c, "prepare", lambda **kwargs: calls.append(kwargs["universe_batch"]) or prepared):
            assert runtime.command("odds") == {"command": "odds", "batch_digest": "b" * 64, "coins": 2,
                                               "passed": 1, "execution_ready": False}
            assert calls == [(plan, O.daily_bars)]
            assert runtime.command("prepare")["session_id"] == "Lfixture-universe" and calls[-1] is batch
        status = runtime.status()
        assert (status["held_symbol"], status["trade_symbol"], status["universe_state"], status["held_flag"]) == (
            BTC, BTC, "in_force", None)
        assert (status["snapshot_day"], status["snapshot_sha256"]) == (env.universe.day.isoformat(), SNAPSHOT)
        assert (status["allow_count"], status["buy_block_reasons"], status["disarm_failed"],
                status["window_ended_missed_slot"]) == (0, [], False, False)
        assert json.loads(json.dumps(status)) == status
```

- [ ] **Step 2: Run the tests and see them fail**

```bash
focus launch launch_coordinator_universe/test_the_odds
focus launch launch_coordinator_universe/test_prepare_passes
focus launch launch_coordinator_universe/test_the_console
```

Expected: `FAIL ... AttributeError: <module 'execution_launch.coordinator' ...> does not have the attribute
'run_batch'`; `FAIL ... TypeError: Coordinator.prepare() got an unexpected keyword argument 'universe_batch'`;
`FAIL ... AttributeError: <execution_launch.coordinator.Coordinator object at ...> does not have the attribute
'odds_batch'` (the console test patches `odds_batch` before it sends `odds`).

- [ ] **Step 3: Implement**

In `execution_launch/coordinator.py`, after line 56 (`from execution_control.store import Journal, JournalError`),
add:

```python
from execution_control.universe_odds import run_batch
```

Replace line 710:

```python
    def prepare(self, *, selected_plan, inputs, selection_seed_hex: str, expires_at: datetime | None = None):
```

with:

```python
    def prepare(self, *, selected_plan, inputs, selection_seed_hex: str, expires_at: datetime | None = None,
                universe_batch=None):
```

Replace line 729:

```python
                    selection_seed_hex=selection_seed_hex, expires_at=expires_at,
```

with:

```python
                    selection_seed_hex=selection_seed_hex, expires_at=expires_at, universe_batch=universe_batch,
```

After `prepare` (ending line 735, `return launch.prepared`), insert:

```python

    def odds_batch(self, template, read_bars):
        """Spec section 9: the per-coin odds batch on the caller's (console) thread, never under the work lock and
        never inside a unit. `read_bars(markets, now=, clock=)` reads the daily bars of the top-N of the last
        monitor's snapshot; run_batch reloads the snapshot in force from its own context and journals the batch."""
        _require(self._universe, "COORDINATOR_UNIVERSE_REQUIRED")
        snapshot = self._snapshot
        _require(snapshot is not None, "UNIVERSE_NO_SNAPSHOT")
        try:
            now = self._now()
            n = self._program.max_candidates
            bars = read_bars(universe_top_n(snapshot, n), now=now, clock=self._clock)
            return run_batch(self._controller, template, bars, n=n, now=now, clock=self._clock)
        except Exception as exc:
            raise CoordinatorError(_code(exc, "COORDINATOR_ODDS_BATCH_FAILED")) from None
```

In `tools/owner/launch.py`, after line 33 (`from execution_accounts.baseline_store import CheckpointStore`), add:

```python
from execution_accounts.universe import daily_bars
```

After line 190 (`self._lock, self._thread, self._failure = Lock(), None, ""`), add:

```python
        self._batch = None              # the last `odds` batch, consumed by prepare (spec section 9)
```

In `status`, replace lines 215-216:

```python
                "reasons": list(status.reasons), "risk_reasons": list(status.risk_reasons),
                "worker_failure": failure, "execution_ready": False}
```

with:

```python
                "reasons": list(status.reasons), "risk_reasons": list(status.risk_reasons),
                "held_symbol": status.held_symbol, "trade_symbol": status.trade_symbol,
                "snapshot_day": None if status.snapshot_day is None else status.snapshot_day.isoformat(),
                "snapshot_sha256": status.snapshot_sha256, "universe_state": status.universe_state,
                "held_flag": status.held_flag, "allow_count": status.allow_count,
                "buy_block_reasons": list(status.buy_block_reasons), "disarm_failed": status.disarm_failed,
                "window_ended_missed_slot": status.window_ended_missed_slot,
                "worker_failure": failure, "execution_ready": False}
```

In `prepare`, replace lines 226-227:

```python
        prepared = self._coordinator.prepare(selected_plan=value.selected_plan, inputs=value.inputs,
            selection_seed_hex=value.selection_seed_hex, expires_at=value.expires_at)
```

with:

```python
        with self._lock:
            batch = self._batch
        prepared = self._coordinator.prepare(selected_plan=value.selected_plan, inputs=value.inputs,
            selection_seed_hex=value.selection_seed_hex, expires_at=value.expires_at, universe_batch=batch)
```

After `prepare` (ending line 231, `"execution_ready": False}`), insert:

```python

    def odds(self) -> dict:
        """Spec section 9: the per-coin odds batch for the planner's current template, on this console thread. The
        batch is kept for the next prepare; nothing is signed or armed."""
        _require(self._preparation_provider is not None, "OWNER_CURRENT_PREPARATION_INPUTS_REQUIRED")
        value = self._preparation_provider()
        _require(type(value) is PreparationInputs, "OWNER_CURRENT_PREPARATION_INPUTS_REQUIRED")
        batch = self._coordinator.odds_batch(value.selected_plan, daily_bars)
        with self._lock:
            self._batch = batch
        return {"command": "odds", "batch_digest": batch.batch_digest, "coins": len(batch.coins),
                "passed": sum(coin.passed is True for coin in batch.coins), "execution_ready": False}
```

Replace lines 257-262 of `command`:

```python
        _require(type(name) is str and name in {"status", "bootstrap", "prepare", "run", "stop", "disarm", "close",
                                              "refresh-terms"},
                 "OWNER_COMMAND_INVALID")
        methods = {"status": self.status, "bootstrap": self.bootstrap, "prepare": self.prepare,
                   "run": self.start, "stop": self.stop, "disarm": self.disarm, "close": self.close,
                   "refresh-terms": self.refresh_terms}
```

with:

```python
        _require(type(name) is str and name in {"status", "bootstrap", "odds", "prepare", "run", "stop", "disarm",
                                              "close", "refresh-terms"},
                 "OWNER_COMMAND_INVALID")
        methods = {"status": self.status, "bootstrap": self.bootstrap, "odds": self.odds, "prepare": self.prepare,
                   "run": self.start, "stop": self.stop, "disarm": self.disarm, "close": self.close,
                   "refresh-terms": self.refresh_terms}
```

- [ ] **Step 4: Run the focused and module tests**

```bash
focus launch launch_coordinator_universe/
focus launch launch_owner_ops/
focus launch launch_coordinator/
focus launch owner_guards/
focus launch launch_guards/
```

Expected: only `PASS` lines; each command exits 0.

- [ ] **Step 5: Commit**

```bash
diff <(git diff --stat) <(git diff --stat --ignore-cr-at-eol) && echo LF-OK
git add execution_launch/coordinator.py tools/owner/launch.py tests/launch_coordinator_universe.py
git commit -F - <<'EOF'
Run the odds batch from the console and prepare a universe session with it

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

---

### Task 13: Rehearsal adapters and wiring

**Files:**
- Modify: `tools/owner/rehearsal.py`: line 20; import between lines 35 and 36; `_QuoteSource.read` lines 283-288;
  `_TermsSource.read` lines 296-301; new `_SlotSource` after line 301; `Coordinator(...)` lines 368-373
- Test: `tests/launch_owner_rehearsal.py`, append after line 471 (end of file)

**Interfaces:**
- Consumes: PR 2 `UniverseSlotSource(clock=...)`; PR 4c `E1UpbitTermsSource.read(symbol=None)`;
  `E1UpbitQuoteSource` (frozen dataclass with `symbol`, `clock`, `route`); `Composition.program`
  (`coordinator.py:749-759`); Task 5 `Coordinator(slot_source=, program=)`.
- Produces: `_QuoteSource.read(symbol=None)`, `_TermsSource.read(symbol=None)`, `_SlotSource(source, guard)` with
  guarded `read_flags()` and `read_tickers(markets)`; a universe profile's coordinator gets the slot source and the
  program. Rehearsal still passes no preparation provider, so `odds` and `prepare` refuse
  `OWNER_CURRENT_PREPARATION_INPUTS_REQUIRED` (spec section 13).

- [ ] **Step 1: Write the failing test**

Append to `tests/launch_owner_rehearsal.py`:

```python


def test_universe_adapters_name_the_coin_and_guard_every_read():
    from execution_accounts.instrument_terms import E1UpbitTermsSource
    from execution_accounts.quotes import E1UpbitQuoteSource
    from execution_accounts.universe import UniverseSlotSource
    seen, checks = [], []
    guard = object.__new__(R._ReadGuard)
    guard.time_check = lambda: checks.append(1)
    guard.transport_check = lambda stage: None
    clock = lambda: datetime(2026, 11, 11, tzinfo=timezone.utc)
    with patch.object(E1UpbitQuoteSource, "read", lambda self: seen.append(("book", self.symbol))), \
            patch.object(E1UpbitTermsSource, "read", lambda self, symbol=None: seen.append(("terms", symbol))), \
            patch.object(UniverseSlotSource, "read_flags", lambda self: seen.append(("flags",))), \
            patch.object(UniverseSlotSource, "read_tickers", lambda self, markets: seen.append(("tickers", markets))):
        quotes = R._QuoteSource(E1UpbitQuoteSource(symbol="KRW-BTC", clock=clock), guard)
        terms = R._TermsSource(object.__new__(E1UpbitTermsSource), guard)
        slots = R._SlotSource(UniverseSlotSource(clock=clock), guard)
        quotes.read()
        quotes.read("KRW-XRP")
        terms.read()
        terms.read("KRW-XRP")
        slots.read_flags()
        slots.read_tickers(("KRW-BTC",))
    assert seen == [("book", "KRW-BTC"), ("book", "KRW-XRP"), ("terms", None), ("terms", "KRW-XRP"), ("flags",),
                    ("tickers", ("KRW-BTC",))]
    assert len(checks) == 12                     # a time check before and after every read
    refused(lambda: R._SlotSource(object(), guard), "REHEARSAL_FIXED_SOURCE_REQUIRED")
```

- [ ] **Step 2: Run the test and see it fail**

```bash
focus launch launch_owner_rehearsal/test_universe_adapters
```

Expected: `FAIL ... AttributeError: module 'tools.owner.rehearsal' has no attribute '_SlotSource'` (the three
adapters are built before the first read).

- [ ] **Step 3: Implement**

In `tools/owner/rehearsal.py`, replace line 20 (`from dataclasses import dataclass, fields`) with:

```python
from dataclasses import dataclass, fields, replace
```

Between line 35 (`from execution_accounts.quotes import E1UpbitQuoteSource`) and line 36
(`from execution_accounts.upbit_collector import E1UpbitSource`), add:

```python
from execution_accounts.universe import UniverseSlotSource
```

Replace lines 283-288 (`_QuoteSource.read`) with:

```python
    def read(self, symbol=None):
        source = self._source if symbol is None else replace(self._source, symbol=symbol)  # spec section 10
        self._guard.time_check()
        with inquiry_guard(self._guard.transport_check):
            result = source.read()
        self._guard.time_check()
        return result
```

Replace lines 296-301 (`_TermsSource.read`) with:

```python
    def read(self, symbol=None):
        self._guard.time_check()
        with inquiry_guard(self._guard.transport_check):
            result = self._source.read() if symbol is None else self._source.read(symbol)
        self._guard.time_check()
        return result
```

After line 301 (the end of `_TermsSource`), insert:

```python


class _SlotSource:
    """The per-slot flag and ticker reads (spec section 7, steps 4 and 5) under the same read guard."""
    def __init__(self, source: UniverseSlotSource, guard: _ReadGuard):
        _need(type(source) is UniverseSlotSource and type(guard) is _ReadGuard, "REHEARSAL_FIXED_SOURCE_REQUIRED")
        self._source, self._guard = source, guard

    def read_flags(self):
        self._guard.time_check()
        with inquiry_guard(self._guard.transport_check):
            result = self._source.read_flags()
        self._guard.time_check()
        return result

    def read_tickers(self, markets):
        self._guard.time_check()
        with inquiry_guard(self._guard.transport_check):
            result = self._source.read_tickers(markets)
        self._guard.time_check()
        return result
```

Replace lines 368-373:

```python
    coordinator = Coordinator(mode="rehearsal", profile=comp.profile, evidence=comp.evidence, driver=comp.driver,
        implementation_verifier=comp.verifiers.implementation, adapters={"upbit": DryRunAdapter(upbit)},
        account_source=intervals, account_prefetch=prefetch, trusted_head=head,
        quote_source=_QuoteSource(E1UpbitQuoteSource(symbol=comp.profile.symbol, clock=clock), guard),
        window=window, bar_seconds=comp.protocol.bar_seconds, monitor_until=until, clock=clock,
        history=comp.history, terms_source=terms)
```

with:

```python
    universe = comp.profile.universe_rule_sha256 is not None
    coordinator = Coordinator(mode="rehearsal", profile=comp.profile, evidence=comp.evidence, driver=comp.driver,
        implementation_verifier=comp.verifiers.implementation, adapters={"upbit": DryRunAdapter(upbit)},
        account_source=intervals, account_prefetch=prefetch, trusted_head=head,
        quote_source=_QuoteSource(E1UpbitQuoteSource(symbol=comp.profile.symbol, clock=clock), guard),
        window=window, bar_seconds=comp.protocol.bar_seconds, monitor_until=until, clock=clock,
        history=comp.history, terms_source=terms,
        slot_source=_SlotSource(UniverseSlotSource(clock=clock), guard) if universe else None,
        program=comp.program if universe else None)
```

- [ ] **Step 4: Run the focused and module tests**

```bash
focus launch launch_owner_rehearsal/
focus launch owner_guards/
focus launch launch_guards/
```

Expected: only `PASS` lines; each command exits 0.

- [ ] **Step 5: Commit**

```bash
diff <(git diff --stat) <(git diff --stat --ignore-cr-at-eol) && echo LF-OK
git add tools/owner/rehearsal.py tests/launch_owner_rehearsal.py
git commit -F - <<'EOF'
Pass the trade coin to rehearsal reads and wire the guarded slot source

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

---

### Task 14: Guards, full suite and the pull request

**Files:**
- No file changes. Reads the 13 commits of Tasks 1 to 13.

**Interfaces:**
- Consumes: the commits of Tasks 1 to 13.
- Produces: branch `claude/universe-pr4e-runner-coordinator` pushed to `origin` and one open pull request against
  `main`. The owner merges it; never merge with tools.

- [ ] **Step 1: Run the guard modules**

```bash
focus compliance compliance_guards/
focus compliance compliance_cli/
focus control control_guards/
focus accounts accounts_guards/
focus launch launch_guards/
focus launch owner_guards/
focus execution execution_guards/
```

Expected: only `PASS` lines, each command exits 0. `control_guards` runs the `tests/renewal_boundaries.py` checks;
this PR edits no pinned file. If a guard fails, stop and report; never regenerate a pin.

- [ ] **Step 2: Run the launch suite, then the full suite**

```bash
focus launch launch_
"$PY" -X utf8 -m tests.run_all
git restore qa/acceptance_results.json
```

Expected: `focus launch launch_` exits 0. The full run's last line reads `<n>/<m> passed, 0 failed, <k> not run;
...qa/acceptance_results.json`; the `git restore` keeps the rewritten results file out of this PR. If a test fails,
run it with `focus` in a separate worktree of `origin/main` (`git worktree add ../tgu-main origin/main`). A test
that fails there too is pre-existing: list it in the PR body under "Not verified" and do not fix it here. A test
that fails only on this branch is a defect of this PR: fix it in a new task before opening the PR.

- [ ] **Step 3: Check the branch**

```bash
git status --short
git log --oneline origin/main..HEAD
diff <(git diff --stat origin/main..HEAD) <(git diff --stat --ignore-cr-at-eol origin/main..HEAD) && echo LF-OK
git diff --stat origin/main..HEAD
```

Expected: no tracked change pending (untracked spec and plan documents may show as `??`); 13 commits; `LF-OK`;
exactly these 14 files: `core/compliance/alerts.py`, `execution_launch/coordinator.py`,
`execution_launch/live_history.py`, `execution_launch/runner.py`, `execution_launch/toast_queue.py`,
`tests/compliance_cli.py`, `tests/launch_acceptance.py`, `tests/launch_coordinator_universe.py`,
`tests/launch_guards.py`, `tests/launch_owner_rehearsal.py`, `tests/launch_runner_universe.py`,
`tests/launch_toast_queue.py`, `tools/owner/launch.py`, `tools/owner/rehearsal.py`.

- [ ] **Step 4: Push and open the pull request**

```bash
git push -u origin claude/universe-pr4e-runner-coordinator
gh pr create --repo xkg4real/tradegen --base main --head claude/universe-pr4e-runner-coordinator \
  --title "Universe runner and coordinator" --body-file - <<'EOF'
## Summary

- Runner: a universe buy needs `profile.symbol` in the slot's `entry_allow` (a frozenset; missing blocks every
  buy), the snapshot in force under the profile's rule, the session's bound odds batch for that snapshot and the
  coin among its coins. Each failure is `blocked`, never a stop. Sells and `submit_exit` never look at them. A second
  sell of one coin while one is active is `blocked` with `RUNNER_OUTSTANDING_ORDERS` instead of stopping the runner.
- Runner: `active`, `dust` and `flat_in`; a renewal to another coin re-checks the flat verdict
  (`RUNNER_UNIVERSE_NOT_FLAT`); `prepare_launch_session` takes the odds batch and checks the template coin in it.
- Coordinator: universe construction (slot source, program, terms source, deciding history; window at most 72
  hours); the book and terms read the trade coin; each monitor tracks held coins, extra holdings, the snapshot and
  vanished coins, then chooses the trade coin and renews to another coin only while flat; terms failures block
  slots only while a coin is held.
- Coordinator slot unit (spec section 7): book unavailable instead of a refusal, flag and ticker reads, the
  allow-list, `record_slot` with the universe inputs in its own `try`, the events after it each in its own `try`
  (vanish disarm through the new lock-free `_disarm_locked`, warning coins, an uncertain held flag), then one tick
  with the recorded allow-list only when recorded, not stopping and the book is there (`COORDINATOR_NO_TRADE_BOOK`
  otherwise). Unsellable remainder after two hold ticks; a missed slot sets `window_ended_missed_slot`.
- Toasts go through `core.compliance.alerts.toast` on one lazy daemon worker (`execution_launch/toast_queue.py`),
  deduped per window or per day. Ten new status fields, also in the console status.
- Console `odds` runs the batch off the work lock and keeps it for `prepare`. Rehearsal passes the coin at read
  time and wires the guarded slot source; it still never prepares or arms.
- Fixed KRW-BTC profiles keep today's slot unit and digests.

Spec: `docs/superpowers/specs/2026-11-11-upbit-krw-universe-design.md`, sections 7, 9, 10, 12, 13 and 15. Plan:
`docs/superpowers/plans/2026-11-11-upbit-krw-universe-pr4e-runner-coordinator.md`.

## Tests added

- `tests/launch_runner_universe.py` (new): allow-list, snapshot and batch checks; sells and explicit exits; the sell
  guard; `dust` and `flat_in`; the flat re-check; the session rules binding across a switch; preparation with a
  batch.
- `tests/launch_coordinator_universe.py` (new): inert construction and refusals; the 72-hour bound; the disarm split;
  toast dedupe and a slow toast; reads by coin; held coins, extra holdings and the snapshot; the terms-failure
  split; trade-coin rules, renewal while flat, an uncertain IOC sell in A that holds the switch while A keeps
  renewing, restart holding another coin, retried renewals; the slot unit (records, allow-lists, failed reads, no
  book, an off-tick or wrong-market book recorded again without it, failed record, terms gate, extra holding, buy
  cap, the next slot after a switch); the events in the slot (vanish, failed and raising disarm, failing event,
  uncertain flag, remainder, failed record); a suspend that misses slots; the odds batch off the lock, preparation
  with a batch and the console.
- `tests/launch_toast_queue.py` (new), `tests/compliance_cli.py` (wrapper), `tests/launch_owner_rehearsal.py`
  (adapters), `tests/launch_guards.py` (`CLEAN` pin).

Guards (`compliance_guards`, `control_guards` with the renewal boundaries, `accounts_guards`, `launch_guards`,
`owner_guards`, `execution_guards`) and the full suite pass.

## Effect on deployments

- `execution_launch/runner.py` is part of the fixed driver identity and every edited file is in the compliance code
  hash. After merge: code-approve on the merged head, a new strategy review for the new identity, a new history
  window and a new protocol (spec section 12).
- Nothing here signs, arms or sends a live order. The owner adds `universe_rule` to `venues.yaml` and signs it after
  code-approve (spec section 16).

## Not verified

- Coordinator tests pin `Runner._assess` to the fixed profile's assessment, because PR 4b refuses universe evidence
  until PR 5's evaluator exists, and use doubles for LiveHistory, the slot reads and the terms source.
- A universe rehearsal end to end through `build_rehearsal` (it needs a v2 terms audit); only the adapters are
  tested.
- A real prepared universe session through `verify_session` and the dry adapter; universe buys are tested up to
  `Controller.reserve`. After a switch the coordinator test checks the next slot's book read, trade coin and
  allow-list, not the buy of the new coin itself.
- The uncertain IOC sell is a stubbed `Controller.states` row with a stubbed `reconcile`; "a later A fill can still
  be sold" relies on the runner sell tests, not on a coordinator run.
- The timing of the flag and ticker reads inside the prefetch lead and the odds batch's runtime (spec section 17).

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
```

Expected: the command prints the new pull request URL. Do not merge; the owner merges.

---

## Spec coverage

| Spec item | Task |
|---|---|
| 7: terms (mark, dust, held coin, trade coin, flat in X) | 3, 6 |
| 7: choosing the trade coin, renewal only while flat, not flat is normal | 7 |
| 7: slot unit steps 1 to 9 | 9, 10 |
| 7 step 7 with the PR 4d contract: an off-tick or wrong-market book is recorded again without it | 9, 10 |
| 19: uncertain IOC sell in A holds the switch, A keeps renewing; rules binding across a switch | 7, 3 |
| 19: a partial sell leaves dust, renewal to B, the next slot reads and allows B (buy itself not run) | 7, 9 |
| 19: record failure and extra holding never stop the runner; a raising kill sets `disarm_failed` | 9, 10 |
| 7: events (vanish, warning coins, uncertain held flag, remainder) | 8, 10 |
| 7: `disarm` split, `COORDINATOR_UNIVERSE_DISARM`, sticky `disarm_failed` | 5, 8 |
| 7: terms failures held versus not held, pending renewal blocks buys | 6, 7, 9 |
| 7: buy allow-list in the coordinator and the runner checks | 2, 9 |
| 7: sell guard | 2 |
| 9: console `odds`, off the work lock | 12 |
| 9: preparation with a batch, runner template check | 4, 12 |
| 9: runner checks of the bound snapshot and coin set | 2 |
| 10: book and terms read by coin, `allow_symbol_change` after the flat check, runner flat re-check | 3, 6, 7 |
| 10: 72-hour window bound | 5 |
| 10: v2 buy cap leaves the coin out of the allow-list | 9 |
| 12: coordinator units, status fields, missed slot, window-end remainder toast | 5 to 11 |
| 13: rehearsal wiring (reads by coin, slot source; no preparation) | 13 |
| 15: coordinator toasts through `alerts.toast` on one background worker | 1, 5 |

## Not in this plan

- E1 poll alerts and `parse_term_receipts` codes: PR 4c. `Controller.kill` recording the reason: PR 4a.
- The universe study, evaluator `forward-universe-v1` and the section 17 measurements: PR 5 and the owner's PC.
