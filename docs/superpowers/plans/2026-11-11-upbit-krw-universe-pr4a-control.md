# Upbit KRW universe PR 4a: execution_control Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give `execution_control` everything the universe runner and coordinator (PR 4e) need from it: the snapshot
seen by `Controller.observe`, order side, symbol and last-event time on `OrderState`, a recorded kill reason, a
per-coin odds batch journaled as an inert `universe_odds_batch` row, and a prepared session that binds that batch and
verifies a universe order against it, while fixed KRW-BTC sessions keep today's identity byte for byte.

**Architecture:** `RiskResult` gains `universe`, set by `Controller.observe` from the context it loaded.
`OrderState` gains `side`, `symbol` and `updated_at`, read from the folded journal. `Controller.kill` journals the
caller's reason. A new module `execution_control/universe_odds.py` runs the template plan once per top-N coin of the
snapshot in force (`simulate` with a fresh comparison id per coin), journals one closed-shape row and keeps the
result in an in-process identity registry like `session._PREPARED`. `prepare_session` takes the batch, checks it
inside the unchanged 30-second window, caps the expiry and binds `universe_batch_digest`, which is left out of every
encoding when `None`. `verify_session` checks a universe order's coin against the batch and the snapshot in force.

**Tech Stack:** Python 3.13 (venv at `TRADEGEN_PR9/.venv`, read-only), stdlib only. Tests use the repo's suite
runner (no pytest) through the index's `focus` function.

**Spec:** [2026-11-11-upbit-krw-universe-design.md](../specs/2026-11-11-upbit-krw-universe-design.md), sections 6,
7 (kill reason, `OrderState` fields), 9, 10 (the `PreparedSession` encoding rule) and 19 (the odds and session
tests).

**Needs:** PR 3 merged (and PR 1 through it). This plan uses PR 1's `core.compliance.model.Universe` and
`core.compliance.rules.universe_top_n`, and PR 3's `Context.universe` and
`owner.load_context(now, positions, *, session_id=None)`.

## Global Constraints

All constraints in the index apply: [2026-11-11-upbit-krw-universe-index.md](2026-11-11-upbit-krw-universe-index.md)
(Global constraints, Running tests, Interface contract, Task conventions).

Constraints specific to this PR, verbatim from the spec and the index:

- Spec section 9: "It imports only `core.odds`, `core.compliance` and `execution_control`, holds no `/v1/` literal,
  and stays inside `tests/control_guards.py`."
- Spec section 9: "The template plan must not use the BTC-only replay edge (`plan.py:301`)."
- Spec section 9: "require every one of the N coins to have passed; otherwise refuse. The remedy is a new study with
  a smaller N or another rule, never an ad hoc set;"
- Spec section 9: "Every other check is unchanged. One session lasts at most until the next 09:40 KST or Seoul
  midnight; the stake cap and every other session limit are unchanged. Arming stays the owner's act."
- Spec section 9: "`session.py:218`, `runner.py:304` and `runner.py:367` stay unchanged."
- Spec section 10: "Every new field (on `LaunchProfile`, `ForwardProtocol`, `ProgramSpec` and `PreparedSession`)
  defaults to `None` and is left out of its canonical encoding when `None`: [...] and the session's `fields` and
  `digest(fields)` (`session.py:172-180`). Each closed-key parser accepts the old key set or the old set plus the new
  keys: [...] the `session_prepared` shape in `controller._event_data` (`controller.py:151`, `170-171`). Fixed
  profiles, protocols, programs and sessions therefore keep today's digests byte for byte, and existing journal rows
  still fold."
- Spec section 7: "`Controller.kill` records the given reason instead of the fixed `owner_requested`
  (`clock_ambiguous` stays when the clock check fails; kill then returns `False` with no owner-log row, which counts
  as a failed disarm)"
- Index: "`execution_control` imports only stdlib, `core.isolation`, `core.compliance`, `core.odds`,
  `execution.snapshot`, `execution.positions`, `execution_control`, `execution_orders`, and the two pinned
  `execution_launch.instrument_refresh` names in `controller.py` and `session.py` [...]. No `/v1/` literal."
- Index: "the pins in `tests/execution_guards.py` and `tests/renewal_boundaries.py` are updated by hand after review,
  never regenerated."

## Identity change and deployments

- `execution_control/controller.py` is in the fixed driver identity (`_SOURCE_FILES`,
  `execution_launch/driver.py:35-38`). After merge a history window bound under the old identity refuses
  `HISTORY_IDENTITY_CHANGED` at restart, before any tick; a new window and a new strategy review are needed.
- Every changed runtime file is inside the compliance code hash (`core/compliance/owner.py:791`), so code-approve
  runs on the merged head. Both are owner acts.
- Unchanged: a fixed session's id, record digest and journal row (Task 3 pins them), profile, contract and protocol
  digests, and the study capture source hash (`CAPTURE_FILES`, `execution_launch/study.py:59-61`, lists no
  `execution_control` file).
- One-way: once a journal holds a `universe_odds_batch` row or a `session_prepared` row with
  `universe_batch_digest`, code from before this PR refuses that journal (`store.py:216` checks `EVENT_KINDS`;
  `_event_data` checks the closed key set). Nothing in this PR writes either row outside tests.

## File Structure

- Create `execution_control/universe_odds.py`: `CoinOdds`, `UniverseBatch`, `run_batch`, `registered_batch`,
  `UniverseOddsError`, `MAX_COINS` and the identity registry `_BATCHES`.
- Modify `execution_control/risk.py`: `RiskResult.universe` (a type-only import of `Universe`).
- Modify `execution_control/controller.py`: `OrderState` fields, `_fold` (order event time, inert batch kind),
  `_view`, `_event_data` (session shapes, batch shape), `observe`, `kill`.
- Modify `execution_control/session.py`: `PreparedSession.universe_batch_digest`, `_record`, `_symbol_ok`, the
  universe form of `prepare_session` and `verify_session`.
- Modify `execution_control/store.py`: `EVENT_KINDS` gains `"universe_odds_batch"`.
- Modify `tests/renewal_boundaries.py`: the reviewed `execution_control/risk.py` initialization pin.
- Modify `tests/control_fixtures.py`: `isolated()` saves, clears and restores `universe_odds._BATCHES`.
- Modify `tests/control_session.py`: the `universe_snapshot` and `universe_context` helpers, the fixed-session
  encoding test and two existing digest expressions.
- Modify `tests/control_controller.py`: observe, `OrderState`, kill and `_event_data` tests.
- Create `tests/control_universe_odds.py` and add it to `MODULES` in `tests/control_acceptance.py`.

No doc is changed; the spec, index and plan files are not committed by this plan. Line numbers below are at
fd85850. PR 3 replaces five single lines of `execution_control/controller.py` one for one (513, 519, 584, 641 and
754, its gate lookup callers) and appends one test to `tests/control_controller.py`. No line is added or removed in
controller.py, so every range this plan cites there, `kill` (850-870) included, keeps its fd85850 number; still match
each edit by the quoted text. PR 2 (and possibly PR 4b) replace single lines of `tests/renewal_boundaries.py` other
than line 32.

---

### Task 1: `RiskResult.universe` from `Controller.observe`, test helpers, renewal pin

**Files:**
- Modify: `execution_control/risk.py:14-15` (imports), insert after `execution_control/risk.py:101`
- Modify: `execution_control/controller.py:441`
- Modify: `tests/renewal_boundaries.py:32`
- Modify: `tests/control_session.py:4`, insert after `tests/control_session.py:37`
- Modify: `tests/control_controller.py:12`, append to the end of `tests/control_controller.py`
- Test: `tests/control_controller.py`

**Interfaces:**
- Consumes:
  - PR 1: `core.compliance.model.Universe(day, rule_sha256, snapshot_sha256, built_at, valid_from, valid_until,
    listed, eligible)`.
  - PR 3: `Context.universe: Universe | None`; `owner.load_context(now, positions, *, session_id=None)`.
  - fd85850: `RiskResult` (`execution_control/risk.py:86-101`, frozen, keyword-only); `Controller.observe(*, now)`
    (`controller.py:432-441`); `model.seal_context(**fields)` (`core/compliance/model.py:230-238`, tests only);
    `signed_control(*, prepare=True, arm=True, ...)` (`tests/control_session.py:40-83`); `_surface(source)`,
    `problems(sources)`, `source_map(root)` (`tests/renewal_boundaries.py:133-175`).
- Produces:
  - `RiskResult.universe: Universe | None = None` (index contract). `risk.evaluate` never sets it; `observe` returns
    `ctx.universe` of the context it loaded inside its journal transaction.
  - Test helpers in `tests/control_session.py`: `universe_snapshot(now, *, eligible=(('KRW-BTC',
    D('900000000000')),), sha='5'*64, valid_until=None) -> Universe` and the context manager
    `universe_context(**changes)`, which patches `owner.load_context` to re-seal the real context with each change
    (a value, or a function of the real context). Tasks 2 to 5 use them.
  - `tests/renewal_boundaries.py` pin for `execution_control/risk.py`:
    `852ae2f20707670b8f0429ec34da5cd338f1aeb5a812c83867f190dfc63b42b0`.

- [ ] **Step 1: Cut the branch and confirm the base**

Define `PY`, `TRADEGEN_RUNS_DIR` and `focus` in this shell exactly as the index's "Running tests" section shows;
every later step uses them. Then:

```bash
git fetch origin
git switch -c claude/universe-pr4a-control origin/main
git log --oneline fd85850..origin/main
git diff --stat fd85850 origin/main -- execution_control tests/control_session.py tests/control_controller.py \
  tests/control_fixtures.py tests/control_acceptance.py tests/renewal_boundaries.py
git diff --numstat fd85850 origin/main -- execution_control/controller.py
grep -n "execution_control/risk.py" tests/renewal_boundaries.py
grep -c "^def test_" tests/control_controller.py tests/control_session.py
"$PY" -X utf8 -c "import dataclasses, inspect; from core.compliance import model, owner, rules; print(inspect.signature(owner.load_context)); print('universe' in {f.name for f in dataclasses.fields(model.Context)}, callable(rules.universe_top_n), model.Universe.__name__)"
```

Expected: the log lists the merged PR 1 and PR 3 (and any other merged PR). The diff stat lists at most
`execution_control/controller.py` (PR 3's lookup callers), `tests/control_controller.py` (PR 3's appended test) and
`tests/renewal_boundaries.py` (PR 2, possibly PR 4b). The numstat prints 5 added and 5 deleted lines for
`execution_control/controller.py` (five one-line replacements, so every cited controller line is unmoved). The first
grep line is `32:    "execution_control/risk.py": "4d9d5fa5c362d51ba7c0c5b77923ed05d1fee64333498245127d4a8a44969f84",`,
as at fd85850. The counts are `tests/control_controller.py:37` and `tests/control_session.py:14`.
The last command prints a signature with `now`, `positions` and keyword `session_id`, then `True True Universe`. If
PR 1 or PR 3 is not merged, or any of these differs, stop and report: every cited range must be re-checked first.

- [ ] **Step 2: Write the test helpers and the failing test**

In `tests/control_session.py`, replace line 4:

```python
from datetime import timedelta
```

with:

```python
from datetime import datetime, time, timedelta, timezone
```

Insert after line 37 (the `return plan, inputs, seed` line that ends `selected`):

```python


def universe_snapshot(now, *, eligible=(('KRW-BTC', D('900000000000')),), sha='5'*64, valid_until=None):
    """A Universe as PR 3's load_context returns it: built for the UTC day before `now`, in force from that day's
    00:40 UTC (09:40 KST) until the next day's 00:40 UTC, or until `valid_until`."""
    day = now.astimezone(timezone.utc).date() - timedelta(days=1)
    start = datetime.combine(day, time(0, 40), tzinfo=timezone.utc)
    return M.Universe(day=day, rule_sha256='7'*64, snapshot_sha256=sha, built_at=start - timedelta(minutes=10),
                      valid_from=start, valid_until=valid_until or start + timedelta(days=1),
                      listed=tuple(sorted(market for market, _ in eligible)), eligible=tuple(sorted(eligible)))


@contextmanager
def universe_context(**changes):
    """Patch owner.load_context to return the real sealed context re-sealed with `changes`; each value is either
    the new field value or a function of the real context (for example universe=lambda ctx: env.universe)."""
    from dataclasses import fields
    from unittest.mock import patch
    real = owner.load_context

    def load(now, positions, **kwargs):
        ctx = real(now, positions, **kwargs)
        body = {f.name: getattr(ctx, f.name) for f in fields(M.Context) if f.name != 'ctx_hash'}
        body.update({name: value(ctx) if callable(value) else value for name, value in changes.items()})
        return M.seal_context(**body)
    with patch.object(owner, 'load_context', load):
        yield
```

In `tests/control_controller.py`, replace line 12:

```python
from tests.control_session import signed_control, refused
```

with:

```python
from tests.control_session import signed_control, refused, universe_context, universe_snapshot
```

Append to the end of the file (after PR 3's appended test):

```python


def test_observe_returns_the_universe_of_the_context_it_loaded():
    with signed_control() as env:
        assert env.controller.observe(now=env.now).universe is None
        snap = universe_snapshot(env.now)
        with universe_context(universe=snap):
            assert env.controller.observe(now=env.now).universe is snap
```

- [ ] **Step 3: Run it and see it fail**

```bash
focus control control_controller/test_observe_returns
```

Expected: `FAIL control_controller/test_observe_returns_the_universe_of_the_context_it_loaded AttributeError:
'RiskResult' object has no attribute 'universe'`.

- [ ] **Step 4: Write the implementation**

In `execution_control/risk.py`, replace lines 14-15:

```python
import re
from zoneinfo import ZoneInfo
```

with:

```python
import re
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

if TYPE_CHECKING:
    from core.compliance.model import Universe
```

Insert after line 101 (`    recovery_status: str | None = None`, the last `RiskResult` field):

```python
    universe: Universe | None = None  # Controller.observe: ctx.universe of the context it loaded
```

`risk.py` keeps `from __future__ import annotations` (line 9), so the annotation is never evaluated at run time.

In `execution_control/controller.py`, replace line 441:

```python
            return self._snapshot_risk(tx, obs, now, orders, ctx)
```

with:

```python
            # Runner and coordinator buy checks use the snapshot this observation saw (spec section 6).
            return replace(self._snapshot_risk(tx, obs, now, orders, ctx), universe=ctx.universe)
```

`replace` is already imported (`controller.py:10`).

- [ ] **Step 5: Run the focused test and the module's tests**

```bash
focus control control_controller/test_observe_returns
focus control control_controller/
```

Expected: `PASS`; the second command prints 38 `PASS control_controller/...` lines (36 at fd85850, PR 3's one, this
one) and exits 0.

- [ ] **Step 6: Review the risk.py surface and update its pin by hand**

```bash
focus control control_guards/test_renewal_validation
git diff execution_control/risk.py
"$PY" -X utf8 -c "from pathlib import Path; from tests.renewal_boundaries import _surface, problems, source_map; print(problems(source_map(Path('.')))); print(_surface(Path('execution_control/risk.py').read_text(encoding='utf-8')))"
```

Expected: `FAIL control_guards/test_renewal_validation_has_only_reviewed_pure_calls_and_import_surfaces
AssertionError`; the diff shows only the 4 import lines and the one field line above; the script prints
`['execution_control/risk.py: initialization surface changed']` and then
`852ae2f20707670b8f0429ec34da5cd338f1aeb5a812c83867f190dfc63b42b0`. If the diff shows anything else or the hash
differs, stop and report; never paste a hash you have not reviewed.

In `tests/renewal_boundaries.py`, replace line 32:

```python
    "execution_control/risk.py": "4d9d5fa5c362d51ba7c0c5b77923ed05d1fee64333498245127d4a8a44969f84",
```

with:

```python
    "execution_control/risk.py": "852ae2f20707670b8f0429ec34da5cd338f1aeb5a812c83867f190dfc63b42b0",
```

```bash
focus control control_guards/
```

Expected: 14 `PASS control_guards/...` lines, exit 0.

- [ ] **Step 7: Commit**

```bash
diff <(git diff --stat) <(git diff --stat --ignore-cr-at-eol) && echo LF-OK
git add execution_control/risk.py execution_control/controller.py tests/renewal_boundaries.py \
  tests/control_session.py tests/control_controller.py
git commit -F - <<'EOF'
Return the snapshot in force from Controller.observe

RiskResult gains universe, which observe sets from the context it
loaded, so the runner's and coordinator's buy checks see the same
snapshot as the controller (spec section 6). risk.evaluate leaves it
None. The risk.py initialization pin in renewal_boundaries is updated
by hand after reviewing the surface: one type-only import and one
defaulted field.

Tests gain universe_snapshot and universe_context, which inject PR 3's
Context.universe into a real sealed context.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

Expected: `LF-OK`, then one commit with exactly these five files.

---

### Task 2: `OrderState` side, symbol and last-event time; kill records its reason

**Files:**
- Modify: `execution_control/controller.py:58-64` (`OrderState`), `:251` and after `:255` (`_fold`), `:325-328`
  (`_view`), `:850-863` (`kill`)
- Modify: append to `tests/control_controller.py`
- Test: `tests/control_controller.py`

**Interfaces:**
- Consumes: `Order.side`, `Order.symbol` (`execution_control/model.py`); the journal row time `row['utc']` that
  `_fold` already parses (`controller.py:197`); `owner.append_system_entry` (unchanged); test helpers `reserve(env)`,
  `snapshot(env, **changes)`, `refused(call)` (`tests/control_controller.py:22-35`, `tests/control_session.py:23-28`).
- Produces (index contract):
  - `OrderState.side: str | None = None`, `OrderState.symbol: str | None = None`,
    `OrderState.updated_at: datetime | None = None`. Every view built by `_view` sets all three: `side` and `symbol`
    from the journaled order, `updated_at` as the journal time of the order's last event. Rows written before this
    PR fold the same way, so old orders get them too.
  - `Controller.kill(session_id, *, reason, now)`: the `kill` row records `reason` when the clock check passes and
    `clock_ambiguous` otherwise (then `False`, no owner-log row, as today). Addition: a `reason` that is not a
    non-blank `str` raises `ValueError('kill reason required')` before any row. The owner-log `system_disarm` reason
    stays `execution control kill`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/control_controller.py`:

```python


def test_order_state_carries_side_symbol_and_last_event_time():
    with signed_control() as env:
        state = reserve(env)
        assert (state.side, state.symbol, state.updated_at) == ('buy', 'KRW-BTC', env.now)
        later = env.now + timedelta(seconds=5)
        snapshot(env, asof=later, server_time=later, risk=replace(env.observation.risk, asof=later))
        sent = env.controller.dispatch(env.order.client_id, now=later)
        assert (sent.status, sent.side, sent.symbol, sent.updated_at) == ('ACKNOWLEDGED', 'buy', 'KRW-BTC', later)
        assert env.controller.states() == (sent,)


def test_kill_records_the_given_reason_or_clock_ambiguous():
    with signed_control() as env:
        assert env.controller.kill(env.session_id, reason='market_vanished', now=env.now) is True
        snapshot(env, server_time=env.now + timedelta(seconds=61))
        assert env.controller.kill('second', reason='market_vanished', now=env.now) is False
        for bad in ('', '  ', None, 7):
            refused(lambda: env.controller.kill('third', reason=bad, now=env.now))
        with env.journal.transaction() as tx:
            kills = [row['data'] for row in tx.events if row['kind'] == 'kill']
        assert kills == [{'session_id': env.session_id, 'reason': 'market_vanished'},
                         {'session_id': 'second', 'reason': 'clock_ambiguous'}]
```

- [ ] **Step 2: Run them and see them fail**

```bash
focus control control_controller/test_order_state_carries
focus control control_controller/test_kill_records
```

Expected:
- `FAIL control_controller/test_order_state_carries_side_symbol_and_last_event_time AttributeError: 'OrderState'
  object has no attribute 'side'`.
- `FAIL control_controller/test_kill_records_the_given_reason_or_clock_ambiguous AssertionError: expected refusal`
  (today a blank reason is journaled as `clock_ambiguous`).

- [ ] **Step 3: Write the implementation**

In `execution_control/controller.py`, replace lines 58-64:

```python
@dataclass(frozen=True, kw_only=True)
class OrderState:
    client_id: str
    status: str
    order_digest: str
    venue_order_id: str = ''
    filled_quantity: Decimal = Decimal(0)
```

with:

```python
@dataclass(frozen=True, kw_only=True)
class OrderState:
    client_id: str
    status: str
    order_digest: str
    venue_order_id: str = ''
    filled_quantity: Decimal = Decimal(0)
    side: str | None = None             # the journaled order's side
    symbol: str | None = None           # the journaled order's venue symbol, e.g. 'KRW-BTC'
    updated_at: datetime | None = None  # journal time of the order's last event
```

In `_fold`, replace line 251:

```python
                                   permit_digest=data['permit_digest'])
```

with:

```python
                                   permit_digest=data['permit_digest'], updated_at=now)
```

and after line 255 (`            rec = orders[key]; state = rec['status']`) insert:

```python
            rec['updated_at'] = now
```

Replace `_view` (lines 325-328):

```python
def _view(rec):
    state = 'UNKNOWN' if rec['status'] == 'DISPATCHING' else rec['status']
    return OrderState(client_id=rec['order'].client_id, status=state, order_digest=rec['digest'],
                      venue_order_id=rec['venue_order_id'], filled_quantity=rec['filled'])
```

with:

```python
def _view(rec):
    state = 'UNKNOWN' if rec['status'] == 'DISPATCHING' else rec['status']
    return OrderState(client_id=rec['order'].client_id, status=state, order_digest=rec['digest'],
                      venue_order_id=rec['venue_order_id'], filled_quantity=rec['filled'],
                      side=rec['order'].side, symbol=rec['order'].symbol, updated_at=rec['updated_at'])
```

In `kill`, replace lines 851-853:

```python
        if type(session_id) is not str or not session_id.strip():
            raise ValueError('session identity required')
        _instant(now)
```

with:

```python
        if type(session_id) is not str or not session_id.strip():
            raise ValueError('session identity required')
        if type(reason) is not str or not reason.strip():
            raise ValueError('kill reason required')
        _instant(now)
```

and replace line 863:

```python
            tx.append('kill',{'session_id':session_id,'reason':'owner_requested' if clock_ok else 'clock_ambiguous'},now=stamp)
```

with:

```python
            # Spec section 7: the caller's reason (the coordinator passes owner_requested or market_vanished).
            tx.append('kill',{'session_id':session_id,'reason':reason if clock_ok else 'clock_ambiguous'},now=stamp)
```

- [ ] **Step 4: Run the focused tests and the modules that use kill and states**

```bash
focus control control_controller/test_order_state_carries
focus control control_controller/test_kill_records
focus control control_controller/
focus control orders_lifecycle/
focus control control_continuous_guard_commit/
focus launch launch_coordinator/
focus launch launch_owner_ops/
```

Expected: every line `PASS`; `control_controller/` prints 40 `PASS` lines (`execution_launch/coordinator.py:695`
calls `kill` with `owner_requested` and hands `states()` on). Existing callers pass `fixture`,
`lifecycle test` and `owner_requested`, all non-blank, and `tests/launch_owner_ops.py:205` still sees
`clock_ambiguous`.

- [ ] **Step 5: Commit**

```bash
diff <(git diff --stat) <(git diff --stat --ignore-cr-at-eol) && echo LF-OK
git add execution_control/controller.py tests/control_controller.py
git commit -F - <<'EOF'
Add side, symbol and last-event time to OrderState; record kill reasons

OrderState views carry the journaled order's side and symbol and the
journal time of its last event, for the runner's sell guard (spec
section 7). Controller.kill journals the caller's reason when the
clock check passes and clock_ambiguous otherwise, and refuses a blank
reason before writing anything.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

Expected: `LF-OK`, then one commit with exactly these two files.

---

### Task 3: `PreparedSession.universe_batch_digest` and the unchanged fixed encoding

**Files:**
- Modify: `execution_control/session.py:35` (field after), after `:53` (`_record`), `:202`, `:231`
- Modify: `execution_control/controller.py:149-151`, `:170-173`
- Modify: `tests/control_session.py:10`, `:97-98`, `:117`, append after `:342`
- Modify: `tests/control_controller.py:8`, append to the end
- Test: `tests/control_session.py`, `tests/control_controller.py`

**Interfaces:**
- Consumes: `PreparedSession` (`session.py:16-35`), `prepare_session`'s `fields` and `digest(fields)`
  (`session.py:172-183`), `verify_session` (`session.py:198-232`), `_event_data` (`controller.py:148-175`),
  `capability.digest` and `plain` (`execution_control/capability.py:17-45`).
- Produces:
  - `PreparedSession.universe_batch_digest: str | None = None` (index contract). `None` for a fixed session; then
    it is not in `fields`, not in `digest(fields)` (session id suffix and record digest) and not in the journal row.
  - `session._record(prepared) -> dict`: `vars(prepared)` without `universe_batch_digest` while it is `None`.
    `verify_session` recomputes digests and compares the journal row through it.
  - `_event_data('session_prepared', data)` accepts exactly the old 18-key set or the old set plus
    `universe_batch_digest` (64 lowercase hex).
  - `FIXED_SESSION_FIELDS` in `tests/control_session.py`: the 16 bound field names of fd85850, in order.

- [ ] **Step 1: Write the failing tests and keep two existing digest expressions exact**

In `tests/control_session.py`, replace line 10:

```python
from execution_control.capability import digest
```

with:

```python
from execution_control.capability import digest, plain
```

Replace lines 97-98:

```python
        assert env.prepared.session_id.endswith(digest({k:v for k,v in vars(env.prepared).items()
                                                     if k not in ('session_id','record_digest')}))
```

with:

```python
        assert env.prepared.session_id.endswith(digest({k:v for k,v in vars(env.prepared).items()
                                                     if k not in ('session_id','record_digest','universe_batch_digest')}))
```

Replace line 117:

```python
        fields={k:v for k,v in vars(env.prepared).items() if k!='record_digest'}
```

with:

```python
        fields={k:v for k,v in vars(env.prepared).items() if k not in ('record_digest','universe_batch_digest')}
```

Append after line 342:

```python


FIXED_SESSION_FIELDS = ('plan_hash', 'input_digest', 'policy_digest', 'rules_digest', 'code_hash', 'state_hash',
                        'seed_hex', 'selection_seed_hex', 'venue', 'symbol', 'account_scope', 'market',
                        'quote_currency', 'stake_krw', 'prepared_at', 'expires_at')   # bound fields at fd85850


def test_fixed_session_keeps_its_pre_universe_identity_record_and_row():
    with signed_control() as env:
        prepared = env.prepared
        assert prepared.universe_batch_digest is None
        bound = {key: getattr(prepared, key) for key in FIXED_SESSION_FIELDS}
        assert prepared.session_id == 'fixture-' + digest(bound)
        assert prepared.record_digest == digest(dict(bound, session_id=prepared.session_id))
        with env.journal.transaction() as tx:
            rows = [row['data'] for row in tx.events if row['kind'] == 'session_prepared']
        assert rows == [plain(dict(bound, session_id=prepared.session_id, record_digest=prepared.record_digest))]
        assert env.controller.states() == ()          # a row with the pre-change key set still folds
        verification(env)
```

In `tests/control_controller.py`, replace line 8:

```python
from execution_control.controller import Controller, _fold
```

with:

```python
from execution_control.controller import Controller, _event_data, _fold
```

Append to the end of `tests/control_controller.py`:

```python


def test_session_prepared_rows_accept_the_old_and_the_old_plus_batch_key_sets():
    with signed_control() as env:
        with env.journal.transaction() as tx:
            old = [row['data'] for row in tx.events if row['kind'] == 'session_prepared'][0]
    _event_data('session_prepared', old)
    _event_data('session_prepared', old | {'universe_batch_digest': 'c'*64})
    for bad in (old | {'universe_batch_digest': 'C'*64}, old | {'universe_batch_digest': None},
                old | {'other': 'c'*64}, {k: v for k, v in old.items() if k != 'symbol'}):
        refused(lambda: _event_data('session_prepared', bad))
```

- [ ] **Step 2: Run them and see them fail**

```bash
focus control control_session/test_fixed_session_keeps
focus control control_controller/test_session_prepared_rows
focus control control_session/test_real_fresh_odds
```

Expected:
- `FAIL control_session/test_fixed_session_keeps_its_pre_universe_identity_record_and_row AttributeError:
  'PreparedSession' object has no attribute 'universe_batch_digest'`.
- `FAIL control_controller/test_session_prepared_rows_accept_the_old_and_the_old_plus_batch_key_sets ValueError:
  invalid lifecycle event fields`.
- `PASS control_session/test_real_fresh_odds_preparation_and_signed_arm_bind_content` (the widened exclusion is a
  no-op before the field exists).

- [ ] **Step 3: Write the implementation**

In `execution_control/session.py`, insert after line 35 (`    record_digest: str`):

```python
    # Spec section 10: None for a fixed session, and then left out of fields, digest(fields) and the journal row.
    universe_batch_digest: str | None = None
```

Insert after line 53 (`    return type(value) is datetime and value.utcoffset() is not None`, the end of `_aware`):

```python


def _record(prepared):
    """vars(prepared) in its canonical encoding: universe_batch_digest only when a batch was bound."""
    return {key: value for key, value in vars(prepared).items()
            if key != "universe_batch_digest" or value is not None}
```

In `verify_session`, replace line 202:

```python
    fields = {key: value for key, value in vars(prepared).items() if key != "record_digest"}
```

with:

```python
    record = _record(prepared)
    fields = {key: value for key, value in record.items() if key != "record_digest"}
```

and replace line 231:

```python
    if len(found) != 1 or found[0]["data"] != plain(prepared):
```

with:

```python
    if len(found) != 1 or found[0]["data"] != plain(record):
```

`prepare_session` needs no change in this task: its `fields` dict never holds the new key, and
`PreparedSession(**fields, record_digest=digest(fields))` leaves it `None`.

In `execution_control/controller.py`, replace lines 149-151:

```python
    pair = {'client_id', 'order_digest'}
    shapes = {
        'session_prepared': {f.name for f in fields(PreparedSession)},
```

with:

```python
    pair = {'client_id', 'order_digest'}
    # Spec section 10: a fixed session's row keeps the old key set; a universe session adds universe_batch_digest.
    prepared = {f.name for f in fields(PreparedSession)} - {'universe_batch_digest'}
    shapes = {
        'session_prepared': prepared,
```

Replace lines 170-173:

```python
    if type(data) is not dict or kind not in shapes or set(data) != shapes[kind]:
        raise ValueError('invalid lifecycle event fields')
    for key in ('order_digest', 'request_digest', 'permit_digest', 'fill_digest', 'fill_key', 'policy_digest',
                'plan_hash','input_digest','rules_digest','code_hash','state_hash','seed_hex','selection_seed_hex','record_digest'):
```

with:

```python
    allowed = [shapes.get(kind)] + ([prepared | {'universe_batch_digest'}] if kind == 'session_prepared' else [])
    if type(data) is not dict or kind not in shapes or set(data) not in allowed:
        raise ValueError('invalid lifecycle event fields')
    for key in ('order_digest', 'request_digest', 'permit_digest', 'fill_digest', 'fill_key', 'policy_digest',
                'plan_hash','input_digest','rules_digest','code_hash','state_hash','seed_hex','selection_seed_hex','record_digest',
                'universe_batch_digest'):
```

- [ ] **Step 4: Run the focused tests and the modules that prepare or verify sessions**

```bash
focus control control_session/test_fixed_session_keeps
focus control control_controller/test_session_prepared_rows
focus control control_session/
focus control control_controller/
focus control orders_lifecycle/
focus launch launch_runner/
focus launch launch_owner_ops/
```

Expected: every line `PASS`; `control_session/` prints 15 `PASS` lines and `control_controller/` 41.
`tests/launch_owner_ops.py:518` rebuilds `PreparedSession(**body)` from an old row; the defaulted field keeps it
working.

- [ ] **Step 5: Commit**

```bash
diff <(git diff --stat) <(git diff --stat --ignore-cr-at-eol) && echo LF-OK
git add execution_control/session.py execution_control/controller.py tests/control_session.py \
  tests/control_controller.py
git commit -F - <<'EOF'
Add PreparedSession.universe_batch_digest, left out of fixed encodings

The field defaults to None and is then left out of the session id, the
record digest and the journal row, so a fixed KRW-BTC session keeps
today's identity byte for byte (spec section 10). verify_session
compares through the same encoding. The session_prepared row shape
accepts the old key set or the old set plus universe_batch_digest, so
existing journals still fold.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

Expected: `LF-OK`, then one commit with exactly these four files.

---

### Task 4: The per-coin odds batch and its inert journal kind

**Files:**
- Create: `execution_control/universe_odds.py`
- Modify: `execution_control/store.py:25-27`
- Modify: `execution_control/controller.py:23` (import after), `:168` (shape after), `:172-175` (hex keys and the
  coin check, as left by Task 3), `:232` (`_fold`)
- Modify: `tests/control_fixtures.py:30`, `:40`, `:44`, `:54-55`
- Modify: `tests/control_acceptance.py:18-20`
- Create: `tests/control_universe_odds.py`
- Test: `tests/control_universe_odds.py`

**Interfaces:**
- Consumes:
  - PR 1: `rules.universe_top_n(universe: Universe, n: int) -> tuple[str, ...]` (largest median first, ties by
    market); `Universe.rule_sha256`, `snapshot_sha256`, `eligible`.
  - PR 3: `Context.universe`; `owner.load_context(now, positions)`.
  - PR 2 shape, read by attribute only (`execution_control` may not import `execution_accounts`): `UniverseBars`
    with `market: str`, `bars: tuple` of `(ISO date, open, close)` rows as `load_leg`'s `upbit_daily` path yields
    them (`core/oddsdata/bars.py:335-336`, `400-402`), `receipt_sha256: tuple[str, ...]`.
  - fd85850: `simulate.simulate(plan, ctx, inputs)` (`core/odds/simulate.py:404`); `report.render(rep) -> str`
    (`core/odds/report.py:1053`, raises `ValueError` on a language-guard hit); `models.data_hashes`,
    `models.market_seed` (`core/odds/models.py:178`, `187`); `plan.Plan`, `Leg`, `Series`, `Inputs`, `Provenance`,
    `series_md5`, `plan_hash`, `REPLAY_SOURCE`, `MAX_HORIZON_DAYS` (`core/odds/plan.py`); `capability.digest`,
    `plain`; `store.guard_pending` (`store.py:38-42`); `controller._fold`, `_event_data`, `Controller._account`,
    `Controller._positions` (`controller.py:192`, `148`, `352`, `481`).
- Produces (index contract unless marked):
  - `CoinOdds(market, plan_hash, seed_hex, inputs_digest, report_digest, passed)` and
    `UniverseBatch(batch_digest, seoul_date, template_plan_hash, code_hash, state_hash, owner_head, rule_sha256,
    snapshot_sha256, n, coins, started_at, finished_at, prior_batches)`, frozen and keyword-only.
  - `run_batch(controller, template, bars, *, n, now, clock) -> UniverseBatch`.
  - `registered_batch(batch_digest) -> UniverseBatch | None`.
  - Addition: `UniverseOddsError(ValueError)` with codes `UNIVERSE_BATCH_CLOCK_INVALID`, `UNIVERSE_BATCH_N_INVALID`,
    `UNIVERSE_BATCH_TEMPLATE_INVALID`, `UNIVERSE_BATCH_STATE_UNUSABLE`, `UNIVERSE_BATCH_SESSION_ARMED`,
    `UNIVERSE_BATCH_NO_SNAPSHOT`, `UNIVERSE_BATCH_BARS_MISSING`, `UNIVERSE_BATCH_GUARD_PENDING`; `MAX_COINS = 64`;
    private `_BATCHES: dict[int, tuple[UniverseBatch, str]]`.
  - Field meanings: `owner_head` is `ctx.owner.head[1]` (the last owner-log row sha256); `inputs_digest` is
    `digest(list(receipt_sha256))`; `report_digest` is the sha256 of `report.render(report)` as UTF-8;
    `template_plan_hash` is `plan_hash(replace(template, start=seoul_date))`; a coin's `plan_hash` is that of
    `replace(template, start=seoul_date, leg=replace(template.leg, symbol=<coin>))`. A coin passes when the report
    is not refused, has no red flag, its plan hash is that plan's hash and (addition) its `seed_hex` is the recorded
    seed.
  - `coins` holds one entry per market of `rules.universe_top_n(ctx.universe, n)`, in that order, so it has
    `min(n, len(universe.eligible))` entries and can be shorter than `n`; `n` records the request. `_event_data`
    refuses an empty `coins` or more than `n` entries. Consumers must read the N coins from `coins`, never from `n`.
  - `store.EVENT_KINDS` gains `"universe_odds_batch"`; `_event_data` gives it the closed shape of `UniverseBatch`
    with a closed `CoinOdds` shape per coin; `_fold` skips it like `session_prepared`.
  - `tests/control_fixtures.isolated()` clears `universe_odds._BATCHES` for each test and restores it after.

- [ ] **Step 1: Write the failing tests**

In `tests/control_acceptance.py`, replace lines 18-20:

```python
MODULES = ("control_guards", "control_model", "control_store", "control_risk", "control_session",
           "control_controller", "orders_codecs", "orders_transport", "orders_lifecycle",
           "control_continuous_guard", "control_continuous_guard_commit")
```

with:

```python
MODULES = ("control_guards", "control_model", "control_store", "control_risk", "control_session",
           "control_controller", "orders_codecs", "orders_transport", "orders_lifecycle",
           "control_continuous_guard", "control_continuous_guard_commit", "control_universe_odds")
```

Create `tests/control_universe_odds.py`:

```python
"""Universe odds batches and universe session preparation, in test-signed temporary homes only."""
import ast
from contextlib import contextmanager
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from core.compliance import model as M
from core.odds import plan as odds_plan
from execution_control import universe_odds as U
from execution_control.capability import digest, plain
from execution_control.controller import _event_data, _fold
from execution_control.store import MAX_ROW_BYTES
from execution_launch.continuous_guard_commit import _PREPARE_KEYS
from tests import compliance_fixtures as F, odds_fixtures as OF
from tests.control_session import (_fixed_refusal, refused, selected, signed_control, universe_context,
                                   universe_snapshot)

D = Decimal
ROOT = Path(__file__).resolve().parents[1]
BTC, ETH, XRP = 'KRW-BTC', 'KRW-ETH', 'KRW-XRP'
PREPARE_ROW = {key: 'a'*64 for key in _PREPARE_KEYS} | {'path_start': 'x', 'path_end': 'x', 'halt_required': False,
                                                        'required_records': []}


def coin_bars(market, *, n=600):
    """What PR 2's daily_bars returns for one market: final (ISO date, open, close) rows ending the day before the
    fixture start, and the sha256 of each candle receipt."""
    series = OF.fresh_series(n, end='2026-10-23', symbol=market)
    return SimpleNamespace(market=market, bars=tuple(zip(series.dates, series.open, series.close)),
                           receipt_sha256=(hashlib.sha256(market.encode('ascii')).hexdigest(),))


@contextmanager
def universe_env(eligible=((BTC, D('900000000000')),)):
    """A signed, unarmed control home whose load_context returns env.universe as the snapshot in force."""
    with signed_control(prepare=False, arm=False) as env:
        env.universe = universe_snapshot(env.now, eligible=eligible)
        env.bars = {market: coin_bars(market) for market, _ in eligible}
        with universe_context(universe=lambda ctx: env.universe):
            yield env


def batch(env, n=1):
    return U.run_batch(env.controller, selected(env.now)[0], env.bars, n=n, now=env.now, clock=lambda: env.now)


def batch_rows(env):
    with env.journal.transaction() as tx:
        return [row['data'] for row in tx.events if row['kind'] == 'universe_odds_batch']


def test_batch_simulates_exactly_the_top_n_and_journals_one_closed_row():
    eligible = ((ETH, D('500000000000')), (BTC, D('900000000000')), (XRP, D('100000000000')))
    with universe_env(eligible) as env:
        env.bars[ETH] = coin_bars(ETH, n=100)       # refused either way: not mapped, or fewer than 250 bars
        result = batch(env, n=2)
        template = selected(env.now)[0]
        assert [(coin.market, coin.passed) for coin in result.coins] == [(BTC, True), (ETH, False)]
        assert result.coins[0].plan_hash == odds_plan.plan_hash(template) == result.template_plan_hash
        assert result.coins[1].plan_hash == odds_plan.plan_hash(replace(template,
                                                                         leg=replace(template.leg, symbol='ETH')))
        assert result.coins[0].inputs_digest == digest(list(env.bars[BTC].receipt_sha256))
        assert result.coins[0].seed_hex != result.coins[1].seed_hex
        assert (result.seoul_date, result.n, result.prior_batches) == (env.now.astimezone(M.KST).date(), 2, 0)
        assert (result.rule_sha256, result.snapshot_sha256) == (env.universe.rule_sha256,
                                                                env.universe.snapshot_sha256)
        assert result.started_at == result.finished_at == env.now
        assert result.batch_digest == digest({k: v for k, v in plain(result).items() if k != 'batch_digest'})
        assert batch_rows(env) == [plain(result)] and U.registered_batch(result.batch_digest) is result


def test_prior_batches_count_earlier_batches_of_the_same_snapshot_and_day():
    with universe_env() as env:
        first, second = batch(env), batch(env)
        assert (first.prior_batches, second.prior_batches) == (0, 1)
        assert first.batch_digest != second.batch_digest and first.coins[0].seed_hex != second.coins[0].seed_hex
        env.universe = replace(env.universe, snapshot_sha256='6'*64)
        assert batch(env).prior_batches == 0 and len(batch_rows(env)) == 3


def test_registry_returns_only_the_issued_unchanged_batch():
    with universe_env() as env:
        result = batch(env)
        assert U.registered_batch(result.batch_digest) is result
        assert U.registered_batch('0'*64) is None and U.registered_batch(None) is None
        object.__setattr__(result, 'prior_batches', 5)
        assert U.registered_batch(result.batch_digest) is None


def test_batch_row_folds_as_an_inert_event():
    with universe_env() as env:
        batch(env)
        with env.journal.transaction() as tx:
            assert [row['kind'] for row in tx.events] == ['universe_odds_batch']
            orders, killed, halted, last = _fold(tx.events)
        assert (orders, killed, halted, last) == ({}, set(), False, env.now)
        assert env.controller.states() == ()
        assert env.controller.observe(now=env.now).universe is env.universe


def test_event_data_closes_the_batch_row_shape():
    with universe_env() as env:
        row = plain(batch(env))
    _event_data('universe_odds_batch', row)
    coin = row['coins'][0]
    for bad in (row | {'extra': 1}, {k: v for k, v in row.items() if k != 'n'}, row | {'owner_head': ''},
                row | {'coins': []}, row | {'n': 0}, row | {'prior_batches': -1},
                row | {'coins': [coin | {'passed': 'yes'}]}, row | {'coins': [coin | {'seed_hex': 'G'*64}]},
                row | {'coins': [{k: v for k, v in coin.items() if k != 'market'}]}):
        refused(lambda: _event_data('universe_odds_batch', bad))


def test_batch_refusals_happen_before_any_simulation_or_row():
    def simulated(*args, **kwargs):
        raise AssertionError('simulated before a refusal')
    with universe_env() as env, patch.object(U.simulate, 'simulate', simulated):
        template = selected(env.now)[0]

        def run(code, template=template, bars=None, **changes):
            args = dict(n=1, now=env.now, clock=lambda: env.now) | changes
            _fixed_refusal(lambda: U.run_batch(env.controller, template, env.bars if bars is None else bars,
                                               **args), code)
        for n in (0, U.MAX_COINS + 1, True, 1.0):
            run('UNIVERSE_BATCH_N_INVALID', n=n)
        for clock in (lambda: env.now + timedelta(seconds=31), lambda: env.now - timedelta(seconds=1), None):
            run('UNIVERSE_BATCH_CLOCK_INVALID', clock=clock)
        for leg in (replace(template.leg, edge_source=odds_plan.REPLAY_SOURCE), replace(template.leg, venue='okx')):
            run('UNIVERSE_BATCH_TEMPLATE_INVALID', template=replace(template, leg=leg))
        run('UNIVERSE_BATCH_BARS_MISSING', bars={})
        for changes in ({'market': ETH}, {'receipt_sha256': ()}, {'receipt_sha256': ('A'*64,)}, {'bars': ()},
                        {'bars': (('2026-10-22', 'x', 1.0),)}):
            run('UNIVERSE_BATCH_BARS_MISSING', bars={BTC: SimpleNamespace(**(vars(env.bars[BTC]) | changes))})
        with universe_context(code_signed=False):
            run('UNIVERSE_BATCH_STATE_UNUSABLE')
        observation, stale = env.observation, env.now - timedelta(seconds=31)
        env.observation = replace(observation, asof=stale, risk=replace(observation.risk, asof=stale))
        run('UNIVERSE_BATCH_STATE_UNUSABLE')
        env.observation = observation
        for universe in (None, universe_snapshot(env.now, eligible=())):
            env.universe = universe
            run('UNIVERSE_BATCH_NO_SNAPSHOT')
        env.universe = universe_snapshot(env.now)
        F.sign(env.key, 'session_armed', {'session_id': 'armed-elsewhere'}, M.iso_utc(env.now))
        run('UNIVERSE_BATCH_SESSION_ARMED')
        assert batch_rows(env) == [] and U._BATCHES == {}


def test_batch_refuses_inside_a_pending_guard_transaction():
    with universe_env() as env:
        with env.journal.transaction() as tx:
            tx.append('continuous_guard_prepare', PREPARE_ROW, now=env.now)
        _fixed_refusal(lambda: batch(env), 'UNIVERSE_BATCH_GUARD_PENDING')
        with env.journal.transaction() as tx:
            assert [row['kind'] for row in tx.events] == ['continuous_guard_prepare']
        assert U._BATCHES == {}


def test_largest_batch_row_fits_one_journal_row_and_folds():
    coin = U.CoinOdds(market='KRW-A' + 'Z'*11, plan_hash='a'*64, seed_hex='b'*64, inputs_digest='c'*64,
                      report_digest='d'*64, passed=True)
    largest = U.UniverseBatch(batch_digest='e'*64, seoul_date=F.NOW.astimezone(M.KST).date(),
                              template_plan_hash='f'*64, code_hash='1'*64, state_hash='2'*64, owner_head='3'*64,
                              rule_sha256='4'*64, snapshot_sha256='5'*64, n=U.MAX_COINS,
                              coins=(coin,) * U.MAX_COINS, started_at=F.NOW, finished_at=F.NOW,
                              prior_batches=2**62)
    row = plain(largest)
    _event_data('universe_odds_batch', row)
    assert len(json.dumps(row)) * 4 < MAX_ROW_BYTES
    with signed_control(prepare=False, arm=False) as env:
        with env.journal.transaction() as tx:
            tx.append('universe_odds_batch', row, now=env.now)
        assert env.controller.states() == ()


def test_universe_odds_imports_only_odds_compliance_and_control():
    source = (ROOT / 'execution_control' / 'universe_odds.py').read_text(encoding='utf-8')
    std = {'__future__', 'collections.abc', 'dataclasses', 'datetime', 'decimal', 'hashlib', 're', 'uuid'}
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.ImportFrom):
            assert node.level == 0
        names = ([alias.name for alias in node.names] if isinstance(node, ast.Import)
                 else [node.module or ''] if isinstance(node, ast.ImportFrom) else [])
        for name in names:
            assert (name in std or name in ('core.odds', 'core.compliance', 'execution_control')
                    or name.startswith(('core.odds.', 'core.compliance.', 'execution_control.'))), name
    assert '/v1/' not in source and 'oddsdata' not in source
```

- [ ] **Step 2: Run the module and see it fail**

```bash
focus control control_universe_odds/
```

Expected: `FAIL control_universe_odds/import ImportError: cannot import name 'universe_odds' from 'execution_control'`
followed by the path of `execution_control/__init__.py` in parentheses (`from package import name` raises
`ImportError`, not `ModuleNotFoundError`, when the package exists).

- [ ] **Step 3: Write the implementation**

Create `execution_control/universe_odds.py`:

```python
"""Per-coin fresh odds for the top-N coins of the Upbit KRW universe snapshot in force (spec section 9).

One batch simulates the reviewed template plan once per coin with a fresh comparison seed, journals one inert
``universe_odds_batch`` control row and registers the result in this process by identity, like
``session._PREPARED``. It never prepares, signs or arms a session and reads no exchange: the caller supplies the
plain final daily bars and their receipt digests. Only an object returned here can be bound by prepare_session.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, fields, replace
from datetime import date, datetime, timedelta
from decimal import Inexact, localcontext
import hashlib
import re
from uuid import uuid4

from core.compliance import model, owner, rules
from core.odds import models, plan as odds_plan, report, simulate
from execution_control.capability import digest, plain
from execution_control.store import guard_pending

# ponytail: a fixed cap keeps one batch row far under store.MAX_ROW_BYTES; raise it together with the row-size test.
MAX_COINS = 64
_CLOCK_AGE = timedelta(seconds=30)
_HEX = re.compile(r"[0-9a-f]{64}")


@dataclass(frozen=True, kw_only=True)
class CoinOdds:
    market: str              # "KRW-<coin>"
    plan_hash: str           # the template with this coin and the batch's Seoul date as its start
    seed_hex: str            # the market seed of this coin's fresh comparison
    inputs_digest: str       # digest of the coin's candle receipt sha256 list
    report_digest: str       # sha256 of the rendered card
    passed: bool


@dataclass(frozen=True, kw_only=True)
class UniverseBatch:
    batch_digest: str        # digest of every other field
    seoul_date: date
    template_plan_hash: str
    code_hash: str
    state_hash: str
    owner_head: str          # sha256 of the last owner-log row
    rule_sha256: str
    snapshot_sha256: str
    n: int
    coins: tuple[CoinOdds, ...]
    started_at: datetime
    finished_at: datetime
    prior_batches: int       # batches already journaled for this snapshot and Seoul date


_BATCHES: dict[int, tuple[UniverseBatch, str]] = {}


class UniverseOddsError(ValueError):
    """Fixed refusal codes; no planner or provider text is exposed."""


def _require(condition, code):
    if not condition:
        raise UniverseOddsError(code)


def _body(batch):
    return {f.name: getattr(batch, f.name) for f in fields(UniverseBatch) if f.name != "batch_digest"}


def registered_batch(batch_digest):
    """The batch this process issued under `batch_digest`, unchanged since; else None."""
    for batch, recorded in _BATCHES.values():
        if recorded == batch_digest == batch.batch_digest == digest(_body(batch)):
            return batch
    return None


def _instant(value):
    return type(value) is datetime and value.utcoffset() is not None


def _read(clock):
    try:
        stamp = clock()
    except Exception:
        raise UniverseOddsError("UNIVERSE_BATCH_CLOCK_INVALID") from None
    _require(_instant(stamp), "UNIVERSE_BATCH_CLOCK_INVALID")
    return stamp


def _template_ok(template):
    leg = getattr(template, "leg", None)
    return (type(template) is odds_plan.Plan and type(leg) is odds_plan.Leg and leg.venue == "upbit"
            and leg.edge_source != odds_plan.REPLAY_SOURCE      # the replay edge is a KRW-BTC card (plan.py:301)
            and type(template.horizon_days) is int and 1 <= template.horizon_days <= odds_plan.MAX_HORIZON_DAYS)


def _bars_ok(market, item):
    receipts = getattr(item, "receipt_sha256", None)
    return (getattr(item, "market", None) == market and type(getattr(item, "bars", None)) is tuple
            and len(item.bars) > 0 and type(receipts) is tuple and len(receipts) > 0
            and all(type(value) is str and _HEX.fullmatch(value) for value in receipts))


def _series(market, rows):
    """The plan.Series that load_leg's upbit_daily path builds from the same final rows (bars.py:400-402), without
    part components: the receipts are bound through inputs_digest instead."""
    dates = tuple(str(day) for day, _, _ in rows)
    opens = tuple(float(value) for _, value, _ in rows)
    closes = tuple(float(value) for _, _, value in rows)
    return odds_plan.Series(symbol=market, source="UPBIT", dates=dates, open=opens, close=closes, adjustment="",
                            status="final",
                            md5=odds_plan.series_md5(market, "UPBIT", dates, opens, closes, "", "final"))


def _context(controller, now):
    """The owner context at `now` over the journal's positions, loaded as Controller.observe loads it."""
    from execution_control.controller import _fold  # controller imports this module (session too, after Task 5)
    with localcontext() as numeric:
        numeric.prec = 2048
        numeric.traps[Inexact] = True
        with controller.journal.transaction() as tx:
            orders = _fold(tx.events)[0]
            try:
                positions = controller._positions(controller._account(now, tx.events), orders)
            except ValueError:
                raise UniverseOddsError("UNIVERSE_BATCH_STATE_UNUSABLE") from None
            return owner.load_context(now, positions)


def _coin(template, ctx, now, market, series, receipts):
    coin_plan = replace(template, start=now.astimezone(model.KST).date(),
                        leg=replace(template.leg, symbol=market.split("-", 1)[1]))
    inputs = odds_plan.Inputs(
        now=now, series=series,
        sessions=tuple((coin_plan.start + timedelta(days=i)).isoformat() for i in range(coin_plan.horizon_days)),
        price_limits=(), calendar_sha256="", calendar_version="", calendar_md5s=(), calendar_error="", replay=None,
        comparison_id=uuid4().hex, run_counter=1, comparison_plans=1,
        comparison_typed=int(coin_plan.leg.edge_source == "assumed"), plan_runs=1,
        # No repository read here: the signed code hash stands in for the tree hash.
        provenance=odds_plan.Provenance(repo_anchor="UNVERSIONED", tree_hash=ctx.code_hash, cryptography="unrecorded"))
    seed = models.market_seed(models.data_hashes(series, None), "", inputs.comparison_id, 1).hex()
    result = simulate.simulate(coin_plan, ctx, inputs)
    plan_hash = odds_plan.plan_hash(coin_plan)
    return CoinOdds(market=market, plan_hash=plan_hash, seed_hex=seed, inputs_digest=digest(list(receipts)),
                    report_digest=hashlib.sha256(report.render(result).encode("utf-8")).hexdigest(),
                    passed=(result.refused is None and not any(flag.level == "red" for flag in result.flags)
                            and result.plan_hash == plan_hash and result.provenance.get("seed_hex") == seed))


def run_batch(controller, template, bars, *, n, now, clock):
    """Simulate `template` once per top-N coin of the snapshot in force and journal one batch row (spec section 9).

    `bars` maps each market to PR 2's UniverseBars, read by attribute: `market`, `bars` as (ISO date, open, close)
    rows and `receipt_sha256`. `now` is the inputs' time; the first `clock` read must lie within 30 seconds after
    it. Refuses while any session is armed, with no snapshot in force, or inside a pending continuous-guard
    transaction. A refusal writes nothing and registers nothing.
    """
    from execution_control.controller import _event_data
    _require(callable(clock) and _instant(now), "UNIVERSE_BATCH_CLOCK_INVALID")
    started = _read(clock)
    _require(timedelta(0) <= started - now <= _CLOCK_AGE, "UNIVERSE_BATCH_CLOCK_INVALID")
    _require(type(n) is int and 1 <= n <= MAX_COINS, "UNIVERSE_BATCH_N_INVALID")
    _require(_template_ok(template), "UNIVERSE_BATCH_TEMPLATE_INVALID")
    ctx = _context(controller, now)
    _require(model.is_sealed(ctx) and ctx.owner.ok and ctx.code_signed and ctx.active.valid,
             "UNIVERSE_BATCH_STATE_UNUSABLE")
    _require(not ctx.session.armed and not ctx.owner.armed_sessions, "UNIVERSE_BATCH_SESSION_ARMED")
    universe = ctx.universe
    markets = rules.universe_top_n(universe, n) if universe is not None else ()
    _require(len(markets) > 0, "UNIVERSE_BATCH_NO_SNAPSHOT")
    _require(isinstance(bars, Mapping) and all(_bars_ok(market, bars.get(market)) for market in markets),
             "UNIVERSE_BATCH_BARS_MISSING")
    try:
        series = {market: _series(market, bars[market].bars) for market in markets}
    except (TypeError, ValueError):
        raise UniverseOddsError("UNIVERSE_BATCH_BARS_MISSING") from None
    coins = tuple(_coin(template, ctx, now, market, series[market], bars[market].receipt_sha256)
                  for market in markets)
    day = now.astimezone(model.KST).date()
    with controller.journal.transaction() as tx:
        events = tx.events
        # A row inside a pending guard transaction would leave it unresumable.
        _require(not guard_pending(events), "UNIVERSE_BATCH_GUARD_PENDING")
        finished = _read(clock)
        _require(started <= finished and finished.astimezone(model.KST).date() == day
                 and (not events or datetime.fromisoformat(events[-1]["utc"]) <= finished),
                 "UNIVERSE_BATCH_CLOCK_INVALID")
        body = dict(seoul_date=day, template_plan_hash=odds_plan.plan_hash(replace(template, start=day)),
                    code_hash=ctx.code_hash, state_hash=ctx.active.state_hash, owner_head=ctx.owner.head[1],
                    rule_sha256=universe.rule_sha256, snapshot_sha256=universe.snapshot_sha256, n=n, coins=coins,
                    started_at=started, finished_at=finished,
                    prior_batches=sum(1 for row in events if row["kind"] == "universe_odds_batch"
                                      and row["data"]["snapshot_sha256"] == universe.snapshot_sha256
                                      and row["data"]["seoul_date"] == day.isoformat()))
        batch = UniverseBatch(batch_digest=digest(body), **body)
        payload = plain(batch)
        _event_data("universe_odds_batch", payload)   # never write a row the controller could not fold
        tx.append("universe_odds_batch", payload, now=finished)
    _BATCHES[id(batch)] = (batch, batch.batch_digest)
    return batch
```

In `execution_control/store.py`, replace lines 25-27:

```python
EVENT_KINDS = frozenset({"session_prepared", "reserved", "dispatching", "acknowledged", "rejected", "unknown",
                       "expired", "cancelled_local", "cancel_requested", "reconciled", "fill", "risk_snapshot",
                       "kill", "halt", "continuous_guard_prepare", "continuous_guard_complete"})
```

with:

```python
EVENT_KINDS = frozenset({"session_prepared", "reserved", "dispatching", "acknowledged", "rejected", "unknown",
                       "expired", "cancelled_local", "cancel_requested", "reconciled", "fill", "risk_snapshot",
                       "kill", "halt", "continuous_guard_prepare", "continuous_guard_complete",
                       "universe_odds_batch"})
```

In `execution_control/controller.py`, after line 23 (`from execution_control.store import guard_pending`) insert:

```python
from execution_control.universe_odds import CoinOdds, UniverseBatch
```

After line 168 (`        'continuous_guard_complete': {'transaction_id'},`) insert:

```python
        # Odds batches (spec section 9) are audit rows; prepare_session matches them by content.
        'universe_odds_batch': {f.name for f in fields(UniverseBatch)},
```

Replace the hex-key loop as left by Task 3:

```python
    for key in ('order_digest', 'request_digest', 'permit_digest', 'fill_digest', 'fill_key', 'policy_digest',
                'plan_hash','input_digest','rules_digest','code_hash','state_hash','seed_hex','selection_seed_hex','record_digest',
                'universe_batch_digest'):
        if key in data and (type(data[key]) is not str or re.fullmatch('[0-9a-f]{64}', data[key]) is None):
            raise ValueError('invalid lifecycle digest')
```

with:

```python
    for key in ('order_digest', 'request_digest', 'permit_digest', 'fill_digest', 'fill_key', 'policy_digest',
                'plan_hash','input_digest','rules_digest','code_hash','state_hash','seed_hex','selection_seed_hex','record_digest',
                'universe_batch_digest', 'batch_digest', 'template_plan_hash', 'owner_head', 'rule_sha256',
                'snapshot_sha256'):
        if key in data and (type(data[key]) is not str or re.fullmatch('[0-9a-f]{64}', data[key]) is None):
            raise ValueError('invalid lifecycle digest')
    if kind == 'universe_odds_batch':
        coins, names = data['coins'], {f.name for f in fields(CoinOdds)}
        if (type(coins) is not list or not coins or type(data['n']) is not int or len(coins) > data['n']
                or type(data['prior_batches']) is not int or data['prior_batches'] < 0
                or any(type(coin) is not dict or set(coin) != names or type(coin['market']) is not str
                       or type(coin['passed']) is not bool
                       or any(type(coin[key]) is not str or re.fullmatch('[0-9a-f]{64}', coin[key]) is None
                              for key in ('plan_hash', 'seed_hex', 'inputs_digest', 'report_digest'))
                       for coin in coins)):
            raise ValueError('invalid lifecycle event fields')
```

In `_fold`, replace the inert-kind line (fd85850 line 232):

```python
        elif kind in ('session_prepared', 'continuous_guard_prepare', 'continuous_guard_complete'):
```

with:

```python
        elif kind in ('session_prepared', 'continuous_guard_prepare', 'continuous_guard_complete',
                      'universe_odds_batch'):
```

In `tests/control_fixtures.py`, replace line 30:

```python
    from execution_control import capability, session
```

with:

```python
    from execution_control import capability, session, universe_odds
```

After line 40 (`    saved_sessions = dict(session._PREPARED)`) insert:

```python
    saved_batches = dict(universe_odds._BATCHES)
```

After line 44 (`    session._PREPARED.clear()`) insert:

```python
    universe_odds._BATCHES.clear()
```

After line 55 (`        session._PREPARED.update(saved_sessions)`) insert:

```python
        universe_odds._BATCHES.clear()
        universe_odds._BATCHES.update(saved_batches)
```

- [ ] **Step 4: Run the module, its neighbours and the guards**

```bash
focus control control_universe_odds/
focus control control_controller/
focus control control_session/
focus control control_store/
focus control control_continuous_guard_commit/
focus control control_guards/
```

Expected: every line `PASS`; `control_universe_odds/` prints 9 `PASS` lines, `control_controller/` 41,
`control_session/` 15, `control_guards/` 14 (the new file obeys the import, endpoint and effect checks, and the
new module is registered in `MODULES`).

- [ ] **Step 5: Commit**

```bash
diff <(git diff --stat) <(git diff --stat --ignore-cr-at-eol) && echo LF-OK
"$PY" -X utf8 -c "import sys; bad=[p for p in sys.argv[1:] if b'\r' in open(p,'rb').read()]; print(bad or 'NO-CR'); sys.exit(bool(bad))" execution_control/universe_odds.py tests/control_universe_odds.py
git add execution_control/universe_odds.py execution_control/store.py execution_control/controller.py \
  tests/control_fixtures.py tests/control_acceptance.py tests/control_universe_odds.py
git commit -F - <<'EOF'
Run per-coin universe odds as one journaled, registered batch

run_batch loads its own context, refuses while a session is armed,
with no snapshot in force or inside a pending guard transaction, and
simulates the template once per top-N coin of the snapshot with a
fresh comparison seed (spec section 9). It journals one
universe_odds_batch row with a closed shape, which _fold skips as
inert, and registers the result by identity for prepare_session.
The template may not use the BTC-only replay edge. The module imports
only core.odds, core.compliance and execution_control.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

Expected: `LF-OK`, then `NO-CR` (the stat check cannot see CR bytes in a file git does not track yet), then one
commit with exactly these six files. If the CR check lists a file, rewrite it with LF endings before `git add`.

---

### Task 5: Universe session preparation and verification

**Files:**
- Modify: `execution_control/session.py:5`, after `:13`, after `:40`, after `_record` (Task 3), `:60-61`, `:79`
  (docstring end), after `:93`, after `:139`, after `:167`, after `:177`, `:223`
- Modify: `tests/control_universe_odds.py` (imports and appended tests)
- Test: `tests/control_universe_odds.py`

**Interfaces:**
- Consumes: Task 4's `UniverseBatch`, `CoinOdds`, `registered_batch`; Task 3's `_record`; PR 3's `ctx.universe`
  (`snapshot_sha256`, `valid_until`, `eligible`); `ctx.owner.head`, `ctx.active.state_hash`, `ctx.code_hash`;
  `odds_plan.plan_hash`; test helpers `_preparation_args(env, **overrides)` and `verification(env, ...)`
  (`tests/control_session.py:156-162`, `86-91`).
- Produces (index contract unless marked):
  - `prepare_session(..., universe_batch: UniverseBatch | None = None)`. With `None` every step is today's.
  - Refusals, all `PreparationError` (a `ValueError`) with the code as its text:
    - `SESSION_UNIVERSE_BATCH_UNREGISTERED`: not the registered object for its digest (checked before any
      simulation), or the journal does not hold exactly one `universe_odds_batch` row equal to `plain(batch)`
      (checked under the journal lock).
    - `SESSION_UNIVERSE_BATCH_STALE`: no snapshot in force, or the batch's `code_hash`, `state_hash`, `owner_head`,
      `snapshot_sha256` or `seoul_date` differs from the context and date of the preparation.
    - `SESSION_UNIVERSE_TEMPLATE_INVALID`: `selected_plan.leg.venue` is not `upbit`, `KRW-<symbol>` is not one of
      the batch's coins, or (addition) `plan_hash(selected_plan)` differs from that coin's `plan_hash`, so the plan
      is exactly the batch's template for that coin and date.
    - `SESSION_UNIVERSE_BATCH_FAILED`: any coin did not pass.
  - The expiry is capped at the earlier of `ctx.universe.valid_until` and the next Seoul midnight after
    `seoul_date`, each less 60 seconds (`_UNIVERSE_MARGIN`); a cap already past refuses
    `SESSION_PREPARATION_EXPIRED`.
  - `universe_batch_digest = batch.batch_digest` enters the session id, the record digest and the journal row.
  - `session._symbol_ok(prepared, order, symbol, ctx) -> bool` (private): a fixed session compares
    `prepared.symbol`; a universe session needs the registered batch, a snapshot in force with the batch's
    `snapshot_sha256`, and `order.symbol` among the batch's coins and in `ctx.universe.eligible`.
    `verify_session` uses it in place of `prepared.symbol != symbol`; every other check is unchanged.

- [ ] **Step 1: Write the failing tests**

In `tests/control_universe_odds.py`, replace the import lines:

```python
from execution_control import universe_odds as U
```

```python
from execution_control.store import MAX_ROW_BYTES
```

```python
from tests.control_session import (_fixed_refusal, refused, selected, signed_control, universe_context,
                                   universe_snapshot)
```

with, respectively:

```python
from execution_control import session as S, universe_odds as U
from execution_control.session import prepare_session
```

```python
from execution_control.store import MAX_ROW_BYTES, Journal
```

```python
from tests.control_session import (_fixed_refusal, _preparation_args, refused, selected, signed_control,
                                   universe_context, universe_snapshot, verification)
```

and replace `from datetime import timedelta` with `from datetime import datetime, timedelta, timezone`.

After `batch_rows` insert:

```python


def prepare(env, result, **overrides):
    return prepare_session(**_preparation_args(env, universe_batch=result, **overrides))


def prepared_rows(env):
    with env.journal.transaction() as tx:
        return [row['data'] for row in tx.events if row['kind'] == 'session_prepared']
```

Append to the end of the file:

```python


def test_universe_session_binds_the_batch_and_verification_follows_the_snapshot():
    with universe_env() as env:
        result = batch(env)
        prepared = prepare(env, result)
        assert prepared.universe_batch_digest == result.batch_digest
        record = {k: v for k, v in vars(prepared).items() if k != 'record_digest'}
        assert prepared.session_id == 'freshness-' + digest({k: v for k, v in record.items() if k != 'session_id'})
        assert prepared.record_digest == digest(record)
        rows = prepared_rows(env)
        assert rows == [plain(prepared)] and rows[0]['universe_batch_digest'] == result.batch_digest
        env.prepared, env.session_id = prepared, prepared.session_id
        F.sign(env.key, 'session_armed', {'session_id': env.session_id}, M.iso_utc(env.now))
        verification(env)
        reserved = env.controller.reserve(env.order, env.rules, session_id=env.session_id, now=env.now)
        assert reserved.status == 'RESERVED'
        env.universe = replace(env.universe, snapshot_sha256='6'*64)
        refused(lambda: verification(env))


def test_universe_session_refuses_unregistered_or_tampered_batches():
    with universe_env() as env:
        result = batch(env)
        before = dict(S._PREPARED)
        for candidate in (replace(result), plain(result)):
            _fixed_refusal(lambda: prepare(env, candidate), 'SESSION_UNIVERSE_BATCH_UNREGISTERED')
        _fixed_refusal(lambda: prepare(env, result, journal=Journal(env.home / 'other-control')),
                       'SESSION_UNIVERSE_BATCH_UNREGISTERED')
        object.__setattr__(result, 'n', 2)
        _fixed_refusal(lambda: prepare(env, result), 'SESSION_UNIVERSE_BATCH_UNREGISTERED')
        assert S._PREPARED == before and prepared_rows(env) == []


def test_universe_session_refuses_a_stale_batch():
    with universe_env() as env:
        result = batch(env)
        for changes in ({'code_hash': '0'*64},
                        {'active': lambda ctx: replace(ctx.active, seq=ctx.active.seq + 1)},
                        {'owner': lambda ctx: replace(ctx.owner, head=(ctx.owner.head[0] + 1, 'f'*64))},
                        {'universe': lambda ctx: replace(ctx.universe, snapshot_sha256='6'*64)},
                        {'universe': None}):
            with universe_context(**changes):
                _fixed_refusal(lambda: prepare(env, result), 'SESSION_UNIVERSE_BATCH_STALE')
        env.now += timedelta(days=1)
        env.observation = replace(env.observation, asof=env.now, server_time=env.now,
                                  risk=replace(env.observation.risk, asof=env.now))
        env.rules = replace(env.rules, asof=env.now)
        _fixed_refusal(lambda: prepare(env, result), 'SESSION_UNIVERSE_BATCH_STALE')
        assert prepared_rows(env) == []


def test_universe_session_refuses_a_failed_coin_or_another_template():
    with universe_env(((BTC, D('900000000000')), (ETH, D('500000000000')))) as env:
        env.bars[ETH] = coin_bars(ETH, n=100)
        failed = batch(env, n=2)
        _fixed_refusal(lambda: prepare(env, failed), 'SESSION_UNIVERSE_BATCH_FAILED')
        result = batch(env, n=1)
        plan = selected(env.now)[0]
        for other in (replace(plan, stake_krw=41_000.0), replace(plan, leg=replace(plan.leg, symbol='ETH'))):
            _fixed_refusal(lambda: prepare(env, result, selected_plan=other), 'SESSION_UNIVERSE_TEMPLATE_INVALID')
        refused(lambda: prepare(env, result, selection_seed_hex='0'*64))      # the selection-seed check stays
        assert prepared_rows(env) == []


def test_universe_session_caps_expiry_at_snapshot_end_and_seoul_midnight():
    with universe_env() as env:
        result = batch(env)
        # env.now is 09:00 KST; a UTC snapshot end must not turn the KST expiry into a UTC one.
        env.universe = replace(env.universe, valid_until=(env.now + timedelta(minutes=10)).astimezone(timezone.utc))
        capped = prepare(env, result)
        assert capped.expires_at == env.now + timedelta(minutes=9)
        assert capped.expires_at.utcoffset() == env.now.utcoffset() == timedelta(hours=9)
        env.universe = replace(env.universe, valid_until=env.now + timedelta(days=2))
        late = prepare(env, result, session_id='late', expires_at=env.now + timedelta(hours=23))
        assert late.expires_at == datetime(2026, 10, 25, tzinfo=M.KST) - timedelta(seconds=60)
        env.universe = replace(env.universe, valid_until=env.now + timedelta(seconds=30))
        _fixed_refusal(lambda: prepare(env, result, session_id='gone'), 'SESSION_PREPARATION_EXPIRED')


def test_universe_session_symbol_needs_a_batch_coin_eligible_in_the_same_snapshot():
    from execution_control.session import _symbol_ok
    with universe_env(((BTC, D('900000000000')), (ETH, D('500000000000')))) as env:
        result = batch(env, n=1)
        prepared = SimpleNamespace(universe_batch_digest=result.batch_digest, symbol='BTC')
        current = SimpleNamespace(universe=env.universe)

        def order(market):
            return SimpleNamespace(symbol=market)
        assert _symbol_ok(prepared, order(BTC), 'BTC', current)
        assert not _symbol_ok(prepared, order(ETH), 'ETH', current)          # eligible, but outside the N
        for universe in (replace(env.universe, eligible=((ETH, D('500000000000')),)),   # no longer eligible
                         replace(env.universe, snapshot_sha256='6'*64), None):
            assert not _symbol_ok(prepared, order(BTC), 'BTC', SimpleNamespace(universe=universe))
        unregistered = SimpleNamespace(universe_batch_digest='0'*64, symbol='BTC')
        assert not _symbol_ok(unregistered, order(BTC), 'BTC', current)
        fixed = SimpleNamespace(universe_batch_digest=None, symbol='BTC')
        assert _symbol_ok(fixed, order(BTC), 'BTC', None) and not _symbol_ok(fixed, order(ETH), 'ETH', None)
```

- [ ] **Step 2: Run them and see them fail**

```bash
focus control control_universe_odds/test_universe_session_
```

Expected: six `FAIL` lines. The five preparation tests fail with `TypeError: prepare_session() got an unexpected
keyword argument 'universe_batch'`; `test_universe_session_symbol_needs_a_batch_coin_eligible_in_the_same_snapshot`
fails with `ImportError: cannot import name '_symbol_ok' from 'execution_control.session'`.

- [ ] **Step 3: Write the implementation**

In `execution_control/session.py`, replace line 5:

```python
from datetime import datetime, timedelta
```

with:

```python
from datetime import datetime, time, timedelta
```

After line 13 (`from execution_control.store import guard_pending`) insert:

```python
from execution_control.universe_odds import UniverseBatch, registered_batch
```

After line 40 (`_RULES_AGE = timedelta(minutes=5)`) insert:

```python
_UNIVERSE_MARGIN = timedelta(seconds=60)  # the runner's expiry check then blocks buys before the controller refuses
```

After `_record` (added in Task 3) insert:

```python


def _symbol_ok(prepared, order, symbol, ctx) -> bool:
    """A fixed session trades its prepared symbol. A universe session (spec section 9) trades one of its batch's
    N coins that is eligible in the snapshot in force, and that snapshot must be the batch's."""
    if prepared.universe_batch_digest is None:
        return prepared.symbol == symbol
    batch, universe = registered_batch(prepared.universe_batch_digest), ctx.universe
    return (batch is not None and universe is not None and universe.snapshot_sha256 == batch.snapshot_sha256
            and order.symbol in {coin.market for coin in batch.coins}
            and order.symbol in {market for market, _ in universe.eligible})
```

Replace lines 60-61 (the end of the `prepare_session` signature):

```python
                    clock, positions_asof: datetime, completion_check=None,
                    expires_at: datetime | None = None) -> PreparedSession:
```

with:

```python
                    clock, positions_asof: datetime, completion_check=None,
                    expires_at: datetime | None = None,
                    universe_batch: UniverseBatch | None = None) -> PreparedSession:
```

Before the docstring's closing line 79 (`    """`) insert:

```python

    ``universe_batch`` (spec section 9) must be the object run_batch registered in this process and journaled.
    Its code hash, state hash, owner head, snapshot and Seoul date must be current, every coin must have passed,
    and ``selected_plan`` must be that batch's plan for one of its coins. The expiry is capped 60 seconds before
    the snapshot's end and before the next Seoul midnight, and the batch digest is bound into the session.
```

After line 93 (`        raise ValueError("session input date mismatch")`) insert:

```python
    _require(universe_batch is None or (type(universe_batch) is UniverseBatch
             and registered_batch(universe_batch.batch_digest) is universe_batch),
             "SESSION_UNIVERSE_BATCH_UNREGISTERED")
```

After line 139 (`        raise ValueError("prepare before owner session arming")`) insert:

```python
    if universe_batch is not None:
        universe = ctx.universe
        _require(universe is not None
                 and (universe_batch.code_hash, universe_batch.state_hash, universe_batch.owner_head,
                      universe_batch.snapshot_sha256, universe_batch.seoul_date)
                 == (ctx.code_hash, ctx.active.state_hash, ctx.owner.head[1], universe.snapshot_sha256,
                     now.astimezone(model.KST).date()),
                 "SESSION_UNIVERSE_BATCH_STALE")
        coin = next((c for c in universe_batch.coins if c.market == f"KRW-{selected_plan.leg.symbol}"), None)
        _require(selected_plan.leg.venue == "upbit" and coin is not None
                 and coin.plan_hash == odds_plan.plan_hash(selected_plan), "SESSION_UNIVERSE_TEMPLATE_INVALID")
        _require(all(c.passed for c in universe_batch.coins), "SESSION_UNIVERSE_BATCH_FAILED")
        midnight = datetime.combine(universe_batch.seoul_date + timedelta(days=1), time(0), tzinfo=model.KST)
        end = min(end, universe.valid_until - _UNIVERSE_MARGIN, midnight - _UNIVERSE_MARGIN).astimezone(end.tzinfo)
        current_time()  # the capped expiry may already have passed
```

`current_time` reads `end` from the enclosing scope at call time, so every later check uses the capped value and the
record's `expires_at=end` is the capped one. `min` returns whichever operand is earliest, with that operand's offset
(UTC for a real `valid_until`, KST for `midnight`); `.astimezone(end.tzinfo)` keeps the uncapped expiry's offset, so
the journal's `isoformat()` encoding of `expires_at` does not change offset only because the cap applied. The expiry
test checks this with a 09:00 KST `now` and a UTC `valid_until`.

After line 167 (`        _require(not guard_pending(events), "SESSION_PREPARATION_GUARD_PENDING")`) insert:

```python
        if universe_batch is not None:
            batches = [row["data"] for row in events if row["kind"] == "universe_odds_batch"
                       and row["data"].get("batch_digest") == universe_batch.batch_digest]
            _require(batches == [plain(universe_batch)], "SESSION_UNIVERSE_BATCH_UNREGISTERED")
```

After line 177 (`                      stake_krw=str(selected_plan.stake_krw), prepared_at=committed_at, expires_at=end)`)
insert:

```python
        if universe_batch is not None:
            fields["universe_batch_digest"] = universe_batch.batch_digest
```

In `verify_session`, replace line 223:

```python
            or prepared.venue != order.venue or prepared.symbol != symbol
```

with:

```python
            or prepared.venue != order.venue or not _symbol_ok(prepared, order, symbol, ctx)
```

- [ ] **Step 4: Run the focused tests, the module and every module that prepares or verifies sessions**

```bash
focus control control_universe_odds/test_universe_session_
focus control control_universe_odds/
focus control control_session/
focus control control_controller/
focus control orders_lifecycle/
focus control control_continuous_guard_commit/
focus control control_guards/
focus launch launch_runner/
focus launch launch_owner_ops/
focus launch launch_instrument_refresh/
focus launch launch_windows_owner_authority/
```

Expected: every line `PASS`; `control_universe_odds/` prints 15 `PASS` lines.

- [ ] **Step 5: Commit**

```bash
diff <(git diff --stat) <(git diff --stat --ignore-cr-at-eol) && echo LF-OK
git add execution_control/session.py tests/control_universe_odds.py
git commit -F - <<'EOF'
Bind a universe odds batch into session preparation and verification

prepare_session takes the registered batch and, inside the unchanged
30-second window, requires it to be journaled, current (code, state,
owner head, snapshot, Seoul date), all-passed and made for the
selected plan's coin. It caps the expiry 60 seconds before the
snapshot's end and the next Seoul midnight and binds
universe_batch_digest into the session (spec section 9).
verify_session checks a universe order's coin against the batch's N
coins and the snapshot in force; every other check is unchanged.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

Expected: `LF-OK`, then one commit with exactly these two files.

---

### Task 5b: The odds card names rotation selection

**Files:**
- Modify: `core/odds/report.py:424`
- Test: `tests/odds_report.py` (append one test)

**Interfaces:**
- Consumes: nothing new.
- Produces: the `notin.delist` text of the odds card also names rotation selection (spec section 9, last
  paragraph). No name changes.

- [ ] **Step 1: Write the failing test**

Append to `tests/odds_report.py` (it already imports `from core.odds import report as R` and defines `_rep`):

```python
def test_not_in_box_names_rotation_selection():
    """Universe spec section 9: delistings, Upbit warnings and rotation selection are not modelled."""
    text = R.say("notin.delist")
    assert "delistings and Upbit warnings" in text and "rotation" in text
    assert "\n- " + text + "\n" in R.render(_rep())
```

- [ ] **Step 2: Run it and see it fail**

```bash
focus odds odds_report/test_not_in_box_names_rotation_selection
```

Expected: FAIL with `AssertionError` (the current text has no "rotation").

- [ ] **Step 3: Change the card text**

In `core/odds/report.py`, replace line 424:

```python
    "notin.delist": "delistings and Upbit warnings (survivorship)",
```

with:

```python
    "notin.delist": "delistings and Upbit warnings (survivorship), and how a rotation strategy picks its coin",
```

- [ ] **Step 4: Run the module**

```bash
focus odds odds_report/
```

Expected: every row PASS. `test_tax_ceiling_research_base_rates_boxes_limits_and_footer_are_present` iterates
`R._NOT_IN`, so it also covers the new text.

- [ ] **Step 5: Commit**

```bash
git add core/odds/report.py tests/odds_report.py
diff <(git diff --cached --stat) <(git diff --cached --stat --ignore-cr-at-eol) && echo LF-OK
git commit -F - <<'EOF'
Say on the odds card that rotation selection is not modelled

The "Not in these numbers" box already names delistings and Upbit
warnings. A universe session picks its coin by rotation, which the
per-coin odds do not model either (universe spec section 9).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

Expected: `LF-OK`, then one commit with exactly these two files.

---

### Task 6: Guards, full suite and the pull request

**Files:**
- No file changes. Reads the commits of Tasks 1 to 5b.

**Interfaces:**
- Consumes: the six commits of Tasks 1 to 5b.
- Produces: branch `claude/universe-pr4a-control` pushed to `origin` and one open pull request against `main`. The
  owner merges it; PR 4e is cut from `main` after PR 4a and PR 4d merged.

- [ ] **Step 1: Run the guard modules**

```bash
focus compliance compliance_guards/
focus control control_guards/
focus accounts accounts_guards/
focus launch launch_guards/
focus execution execution_guards/
```

Expected: only `PASS` lines, each command exits 0. `control_guards` runs the `tests/renewal_boundaries.py` checks
with the pin reviewed in Task 1; if any guard fails, stop and report, never regenerate a pin.

- [ ] **Step 2: Run the full suite**

```bash
"$PY" -X utf8 -m tests.run_all
```

Expected: the last line reads `<n>/<m> passed, 0 failed, <k> not run; ...qa/acceptance_results.json`
(`qa/acceptance_results.json` is gitignored). If a test fails, run the same test with `focus` in a separate worktree
of `origin/main` (`git worktree add ../tgu-main origin/main`). A test that fails there too is pre-existing: list it
in the PR body under "Not verified" and do not fix it in this PR. A test that fails only on this branch is a defect
of this PR: fix it in a new task before opening the PR.

- [ ] **Step 3: Check the branch**

```bash
git status --short
git log --oneline origin/main..HEAD
diff <(git diff --stat origin/main..HEAD) <(git diff --stat --ignore-cr-at-eol origin/main..HEAD) && echo LF-OK
"$PY" -X utf8 -c "import sys; bad=[p for p in sys.argv[1:] if b'\r' in open(p,'rb').read()]; print(bad or 'NO-CR'); sys.exit(bool(bad))" $(git diff --name-only origin/main..HEAD)
git diff --stat origin/main..HEAD
```

Expected: no tracked change pending (untracked spec and plan documents may be listed with `??`); six commits;
`LF-OK`; `NO-CR` (no committed file holds a CR byte, new files included); exactly these files changed: `core/odds/report.py`, `execution_control/controller.py`, `execution_control/risk.py`,
`execution_control/session.py`, `execution_control/store.py`, `execution_control/universe_odds.py`,
`tests/control_acceptance.py`, `tests/control_controller.py`, `tests/control_fixtures.py`,
`tests/control_session.py`, `tests/control_universe_odds.py`, `tests/odds_report.py`,
`tests/renewal_boundaries.py`.

- [ ] **Step 4: Push and open the pull request**

```bash
git push -u origin claude/universe-pr4a-control
gh pr create --repo xkg4real/tradegen --base main --head claude/universe-pr4a-control \
  --title "Universe odds batch and session binding in execution_control (PR 4a)" --body-file - <<'EOF'
## Summary

- `Controller.observe` returns `RiskResult.universe`, the snapshot of the context it loaded (spec section 6).
- `OrderState` carries the order's `side`, `symbol` and `updated_at` (journal time of its last event).
  `Controller.kill` journals the caller's reason when the clock check passes, `clock_ambiguous` otherwise, and
  refuses a blank reason (spec section 7).
- New `execution_control/universe_odds.py`: `run_batch` simulates the template plan once per top-N coin of the
  snapshot in force with a fresh comparison seed, refuses while a session is armed, with no snapshot or inside a
  pending guard transaction, journals one inert `universe_odds_batch` row and registers the result by identity.
  The template may not use the BTC-only replay edge (spec section 9).
- `prepare_session(..., universe_batch=...)` requires the registered, journaled, current, all-passed batch made for
  the selected plan's coin, caps the expiry 60 seconds before the snapshot's end and the next Seoul midnight, and
  binds `universe_batch_digest`. `verify_session` checks a universe order's coin against the batch's N coins and the
  snapshot in force (spec section 9).
- `universe_batch_digest` is left out of every encoding when `None`: fixed KRW-BTC sessions keep their id, record
  digest and journal row byte for byte, and existing journals still fold (spec section 10).
- The odds card's "Not in these numbers" box also says how a rotation strategy picks its coin is not modelled
  (spec section 9).
- The `execution_control/risk.py` initialization pin in `tests/renewal_boundaries.py` was updated by hand after
  review: one type-only import and one defaulted field.

Spec: `docs/superpowers/specs/2026-11-11-upbit-krw-universe-design.md`, sections 6, 7, 9, 10 and 19.

## Tests added

- `tests/control_universe_odds.py` (new, in `MODULES`): top-N selection with a failed coin, the closed row and its
  digest, `prior_batches`, the registry against copies and tampering, the row folding as inert, the closed row
  shape, every batch refusal before any simulation or row, the pending guard refusal, the largest row size, the
  import surface; universe preparation binding and verification after a snapshot change, unregistered, tampered and
  unjournaled batches, stale code, state, owner head, snapshot and date, a failed coin, another template, the
  selection-seed check, both expiry caps, and the coin check outside the N, not eligible and on another snapshot.
- `tests/control_controller.py`: observe returns the universe; `OrderState` fields after reserve and dispatch; kill
  reasons; old and old plus new `session_prepared` key sets.
- `tests/control_session.py`: a fixed session's pre-universe id, record digest and row, folding unchanged.
- `tests/odds_report.py`: the not-in box names rotation selection.

Guards (`compliance_guards`, `control_guards` with the renewal boundaries, `accounts_guards`, `launch_guards`,
`execution_guards`) and the full suite pass.

## Effect on deployments

- `execution_control/controller.py` is part of the fixed driver identity and every changed file is in the compliance
  code hash: after merge, code-approve on the merged head, a new strategy review and a new history window.
- A journal that holds a `universe_odds_batch` row or a `session_prepared` row with `universe_batch_digest` is
  refused by older code. Nothing outside tests writes either row until PR 4e wires the console `odds` command.

## Not verified

- PR 2's real `daily_bars` output is not used: the tests feed bars of the documented shape.
- Nothing calls `run_batch` or passes `universe_batch` outside tests; the console `odds` command,
  `Coordinator.prepare`, `prepare_launch_session` and the runner checks are PR 4e.
- Simulation time for N coins on the owner's PC is not measured.
- No rehearsal and no run on the owner's PC.

This is software design, not legal, tax or investment advice.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
```

Expected: `gh` prints the pull request URL. Do not merge; the owner merges on GitHub.
