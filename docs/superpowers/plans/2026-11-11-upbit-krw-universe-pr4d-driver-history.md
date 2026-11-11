# Upbit KRW universe PR 4d: Universe driver, history row v2 and the chooser in LiveHistory Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let the fixed driver tick a universe window whose trade coin changes between slots, with LiveHistory
recording history row v2 for the coin the coordinator chose and running the section 14 chooser incrementally, while
fixed KRW-BTC windows keep today's frames and rows byte for byte.

**Architecture:** `execution_launch/driver.py` gains a `UniverseBar` (each bar carries its own coin and tick, and no
book fields when the book was unavailable), a `ChooserInputs` record and `chooser_decision`, two `HistoryFrame` fields
left out of the digest while `None`, an `ioc` construction rule for universe protocols, and per-tick checks that use
`observation.profile.symbol` and each bar's own tick. `execution_launch/live_history.py` takes the trade coin, its
tick, a `SlotUniverse` and the account positions in `record_slot`, writes one v2 row per slot (falling back to
`unavailable` flag and ticker parts over the 256 KiB cap), runs `program.choose` at recording and at replay over the
last L+1 price vectors, h and the hold count, and hands the driver the prior decision's inputs only. A window is a
universe window exactly when its protocol has `universe_rule_sha256`; every fixed path stays as it is.

**Tech Stack:** Python 3.13 (venv at `TRADEGEN_PR9/.venv`, read-only), stdlib `dataclasses`, `decimal`, `fractions`,
`hashlib`, `json`. The repo's suite runner (no pytest) through the index's `focus` function. No new dependency.

**Spec:** [2026-11-11-upbit-krw-universe-design.md](../specs/2026-11-11-upbit-krw-universe-design.md), section 12
(universe driver, history row v2, LiveHistory follows the trade coin, the chooser runs in LiveHistory, raw bodies),
section 14 (price definition and encoding) and section 19 ("driver and history" tests).

## Global Constraints

All constraints in the index apply: [2026-11-11-upbit-krw-universe-index.md](2026-11-11-upbit-krw-universe-index.md)
(Global constraints, Running tests, Interface contract, Task conventions).

Constraints specific to this PR, verbatim from the spec and the index:

- Spec section 12: "A universe protocol's `symbol` is the benchmark `KRW-BTC`, never a trading pin, and a universe
  launch profile starts with that symbol, so the construction check (`driver.py:162-163`) keeps comparing them (with
  `ioc`). Every per-tick site that compares a traded symbol with `protocol.symbol` uses `observation.profile.symbol`
  instead: the quote anchor (`driver.py:271`) and the holding key (`303`). Holdings of other coins are not a driver
  error."
- Spec section 12: "The target for `profile.symbol` is the decided fraction when the prior decision names that coin,
  otherwise 0; at the window end it is 0. A switch therefore happens on its own: the trade coin is sold, the
  coordinator renews to the new coin once the account is flat, and the next slot buys it. It takes two slots."
- Spec section 12: "The prior-decision check recomputes that one decision from the chooser inputs the frame carries
  (below), not the whole history."
- Spec section 12: "Each bar's price and tick checks use that bar's own symbol and tick. A bar whose book was
  `unavailable` has no price check and is never a quote anchor."
- Spec section 12, verbatim:

  > **History row v2** (one row per slot, under the 256 KiB row cap):
  >   - the account anchor: per holding (symbol, units, mark, mark time, unlisted, dust);
  >   - the trade coin and its book receipt, or `unavailable`;
  >   - the snapshot in force: day, sha256 and the top-N list, or `unavailable`;
  >   - the flag read: the coins that are not `unflagged` with their class, the sha256 of the raw body, or `unavailable`;
  >   - the ticker read: per listed coin (market index, trade price and trade-time offset, in the section 14 encoding),
  >     the sha256 of the raw body, or `unavailable`;
  >   - the allow-list, the buy-block reasons and the events;
  >   - the chooser's decision (coin or cash, fraction) and its state (held decision h, hold count).
  >
  > If a row would exceed the cap, the flag and ticker parts are recorded as `unavailable` instead, and that slot has
  > no buys. A row is never refused for size.

- Spec section 12: "**LiveHistory follows the trade coin.** `record_slot` takes the trade coin from the coordinator.
  `_anchor` (`live_history.py:306-307`) reads that coin's units, not the construction-time `self._profile.symbol`
  (LiveHistory is built once, `coordinator.py:802`), and `_derive` (`325`) and `_replay` (`409`) check each row's book
  against that row's recorded trade coin, not `protocol.symbol`."
- Spec section 12: "**The chooser runs in LiveHistory.** `_derive` runs the section 14 chooser at `record_slot` and at
  restart replay, incrementally: it keeps the last L+1 price vectors, h and the hold count. The `HistoryFrame` given to
  the driver carries bars with symbol, tick, book fields and a `universe_sha256` (the digest of that slot's universe
  record), plus the chooser inputs of the prior decision only (flags and top-N at k-1, prices at k-1 and k-1-L, h and
  the hold count before it)."
- Spec section 12: "**Raw bodies.** Live slots keep the parsed values above and the sha256 of each raw `market/all`
  and ticker body, not the bodies. Replay and the verifier use only the hash-chained rows."
- Spec section 12: "The driver identity hashes `driver.py`, `program.py`, `strategy.py`, `runner.py`, `profile.py` and
  three `execution_control` files, including `controller.py`. These changes make a new identity, so a new history
  window (GENESIS), a new protocol and a new review are needed. Any in-flight KRW-BTC study or window finishes first."
- Spec section 14 (prices): "`price_X(j)` is the `trade_price` from slot j's ticker read, defined only if X's trade
  time is within 60 seconds of slot j."
- Spec section 14 (prices): "A slot whose flag read or ticker read is `unavailable` gives no prices at all."
- Spec section 14 (study frame encoding, which history row v2 refers to as "the section 14 encoding"): "a price as a
  decimal string of at most 16 characters, and a trade time as a signed millisecond offset from the slot within
  60,000."
- Spec section 14 (same list): "a coin whose price or trade time falls outside these maxima has no price at that
  slot."
- Spec section 7: "*Dust*: a holding worth less than the signed Upbit minimum order (5,000 KRW) at its mark. An
  unlisted holding is always dust".
- Spec section 19, driver and history, verbatim: "the two-slot switch; a crash with a restart before the next slot; a
  crash that misses a slot ends the window and sets the status field; the prior-decision check from carried inputs;
  per-bar tick checks; the row size fallback; the 72-hour bound;". This PR plans the two-slot switch, the restart
  before the next slot (Task 4, which also checks that a missed slot is never recorded), the prior-decision check,
  the per-bar tick checks and the row size fallback. The status field and the 72-hour bound are coordinator work
  (PR 4e). The assignment adds: restart replay reproduces the chooser state, and fixed-window frames and rows
  byte-identical to today.
- Index: "Fixed-symbol (KRW-BTC) profiles, protocols, programs and sessions keep today's digests byte for byte. Every
  new dataclass field defaults to `None` and is left out of its canonical encoding when `None`".
- Index order: this PR is cut from `main` after PR 2 and PR 4c are merged (so PR 0, PR 1, PR 2, PR 4b and PR 4c are
  in `main`). The owner merges; never merge with tools.

## File Structure

- Modify `execution_launch/driver.py`: the fixed driver adapter. New `UniverseBar`, `ChooserInputs` and
  `chooser_decision`; `HistoryFrame.universe_sha256` and `HistoryFrame.chooser_inputs`; the construction scope rule
  (`ioc` and the rule sha256 for universe protocols); the per-tick universe checks in `_validate_frame`.
- Modify `execution_launch/live_history.py`: the durable history. `SlotUniverse`; `record_slot` keywords; history row
  v2 writing with the size fallback; the incremental chooser; frames carrying the universe digest and the prior
  decision's inputs; replay of v2 rows; `recorded_allow`.
- Create `tests/launch_universe_history.py`: universe fixtures (program, profile, protocol, snapshot, reads, books,
  accounts) and the section 19 driver and history tests.
- Modify `tests/launch_live_history.py`: the fixed-window golden test and the fixed refusal of universe inputs.
- Modify `tests/launch_acceptance.py`: add `launch_universe_history` to `MODULES`.

No other file changes. The coordinator still calls `record_slot(book, observation)` (`coordinator.py:533`); PR 4e
wires the universe keywords, the trade-coin choice and `recorded_allow` as the runner's `entry_allow`.

## Contract notes (deviations and additions to the index's PR 4d contract)

- Bar type: the index allows "`PaperBar` (or the bar type LiveHistory emits)". LiveHistory emits a new
  `UniverseBar` for universe windows; `PaperBar` is unchanged. Adding fields to `PaperBar` would change the exact-key
  parsers `strategy._object(item, PaperBar)` (`strategy.py:567-569`, `614-620`) and `paper_capture.py`'s own `_plain`
  and parser (`paper_capture.py:277-291`, about `349`), which are capture code (`CAPTURE_FILES`). On a `UniverseBar`,
  `symbol` and `tick_size` are always set; `bid`, `ask`, `mark` and `source_sha256` are `None` when the book was
  unavailable.
- `HistoryFrame.chooser_inputs` has the new type `ChooserInputs` (driver.py). The driver recomputes the prior
  decision with the new public `chooser_decision(program, inputs)`, which LiveHistory also uses, so recording,
  replay and the tick share one path.
- `HistoryFrame.universe_sha256` is frame-level, as the contract states: `evidence_digest` of the current slot's
  stored universe record.
- `record_slot` adds two keywords beyond the contract: `tick_size: Decimal | None = None` (the trade coin's current
  tick, which each bar must carry) and `positions: tuple[Position, ...] = ()` (the account capture's positions, the
  only source of the per-holding mark and mark time). For a universe window `book` may be `None` (book unavailable).
- `LiveHistory.recorded_allow: frozenset[str] | None` (new): the allow-list the last v2 row recorded. After a size
  fallback it is empty, so PR 4e must pass it as `entry_allow`, not its own list. New reason code
  `SIZE_FALLBACK = "HISTORY_ROW_SIZE_FALLBACK"` is appended to the row's reasons.
- Ticker prices are recorded as `[market, price text, offset ms]`, by market name instead of a market index, because
  replay reads only the rows and a row does not hold the snapshot's market list. The section 14 maxima (16
  characters, 60,000 ms) apply. The 320-market read cap (`MAX_FRAME_MARKETS`, PR 5) is not applied here; the size
  fallback bounds the row.
- Holdings: `unlisted` is `price == 0` (spec section 11 marks an unlisted coin at 0); `dust` is
  `unlisted or units * price < profile.instrument_rules.min_notional_krw` of the construction profile (the signed
  minimum, pinned by the universe contract digest). PR 4c's `Position.unlisted` marker agrees with `price == 0`,
  because its provider accepts price 0 only with `unlisted=True`; the row derives the flag from the price so that
  replay can re-derive it from the stored values alone.
- New refusal codes: `FIXED_DRIVER_CHOOSER_INPUTS_REQUIRED`, `FIXED_DRIVER_BOOK_UNAVAILABLE`, `HISTORY_BOOK_OFF_TICK`
  (LiveHistory refuses a book that is not on the recorded tick, because the driver re-checks every bar on every later
  tick and one off-tick bar would block the rest of the window; the caller can record that slot without a book).
- PR 4e contract: `HISTORY_BOOK_OFF_TICK` and `HISTORY_BOOK_MARKET_MISMATCH` refuse before anything is written, so
  the coordinator's step 7 calls `record_slot` again with `book=None` inside the same slot window; otherwise the slot
  is missed and the window ends.
- PR 4e contract: the driver and LiveHistory are constructed from the launch profile, whose symbol is the `KRW-BTC`
  benchmark, also when the coordinator composes them again at a restart after a renewal to another coin. A profile
  renewed to another coin refuses `FIXED_DRIVER_SCOPE_MISMATCH` at construction; renewed profiles reach the driver
  only through `DecisionInput.profile`.
- A flag read that is available keeps its classes when only the ticker read failed (spec section 14 drops prices
  only), so rule 1 (h is `warning`) still applies, as PR 4b's `ChooserSlot` docstring says.
- A window's chooser starts at `ChooserState(held=None, hold_count=0)` (PR 4b contract notes). At the window-end slot
  no decision is made and the row's `decision` is `null`.

---

### Task 1: Universe bar, chooser inputs and frame fields

**Files:**
- Modify: `execution_launch/driver.py:26-27` (program import), insert before `:88` (new classes), `:88-100`
  (`HistoryFrame`), insert after `:181` (`chooser_decision`)
- Create: `tests/launch_universe_history.py`
- Modify: `tests/launch_live_history.py` (append after the last test, line 514 at fd85850)
- Modify: `tests/launch_acceptance.py:15` (`MODULES`, as changed by PR 2 and PR 4b)

**Interfaces:**
- Consumes (PR 4b): `ChooserState(held: str | None, hold_count: int)`, `ChooserSlot(top_n: tuple[str, ...],
  flags: Mapping[str, str], prices: Mapping[str, Decimal])`, `choose(spec, state, now_slot, lag_slot) ->
  tuple[str | None, ChooserState]` in `execution_launch/program.py`; the `{"omit_none": True}` field metadata that
  `strategy._plain` leaves out while `None`; `ProgramSpec` schema 2 kind `universe_top1_momentum`;
  `UNIVERSE_EVALUATOR_REVISION`; `LaunchProfile.universe_rule_sha256`; `ForwardProtocol.universe_rule_sha256`;
  `rule_terms_digest(rules, *, universe_rule_sha256=None)`.
- Produces (`execution_launch/driver.py`):
  - `@dataclass(frozen=True, kw_only=True) class UniverseBar: observed_at: datetime; received_at: datetime;
    symbol: str; tick_size: Decimal; bid: Decimal | None; ask: Decimal | None; mark: Decimal | None;
    source_sha256: str | None`.
  - `@dataclass(frozen=True, kw_only=True) class ChooserInputs: held: str | None; hold_count: int;
    top_n: tuple[str, ...]; flags: tuple[tuple[str, str], ...]; prices: tuple[tuple[str, Decimal], ...];
    lag_prices: tuple[tuple[str, Decimal], ...] | None` (pairs sorted by market).
  - `HistoryFrame.universe_sha256: str | None = None` and `HistoryFrame.chooser_inputs: ChooserInputs | None = None`,
    both with metadata `{"omit_none": True}`; `history_frame_digest` is unchanged.
  - `chooser_decision(program: ProgramSpec, inputs: ChooserInputs) -> tuple[str | None, ChooserState]`; refuses
    `FIXED_DRIVER_CHOOSER_INPUTS_REQUIRED` for a wrong shape or any chooser refusal.
  - Test helpers in `tests/launch_universe_history.py`: `D`, `RULE`, `BTC`, `ETH`, `XRP`, `universe_env()`,
    `inputs(**changes)`.

- [ ] **Step 1: Start the branch and check the prerequisites**

```bash
git fetch origin
git switch -c claude/universe-pr4d-driver-history origin/main
git log --oneline -12
grep -n "def choose\|^class ChooserState\|^class ChooserSlot" execution_launch/program.py
grep -n "^class FlagRead\|^class TickerRead" execution_accounts/universe.py
grep -n "^UNIVERSE_MARKET\|^def universe_top_n" core/compliance/rules.py
grep -n "^class Universe" core/compliance/model.py
grep -n "UNIVERSE_EVALUATOR_REVISION =\|omit_none" execution_launch/strategy.py
grep -n "ioc" execution_control/model.py
grep -n "unlisted" execution_accounts/model.py
grep -n "profile_contract_digest(profile) == identity.profile_contract_digest" execution_launch/driver.py
```

Expected: the log shows the merges of PR 0, PR 1, PR 2, PR 4b and PR 4c, and every `grep` prints at least one line.
If one is missing, stop and report; this PR is ordered after all five. Then define the test runner once in this
shell, exactly as the index states:

```bash
PY="$HOME/OneDrive/Desktop/TRADEGEN_PR9/.venv/Scripts/python.exe"
export TRADEGEN_RUNS_DIR="${SCRATCH:?set SCRATCH to your session scratchpad directory}/runs_scratch"
focus() { "$PY" -X utf8 -c "import importlib,sys; from tests.run_all import run; s=importlib.import_module('tests.'+sys.argv[1]+'_acceptance'); rows=run([(n,f) for n,f in s.tests() if sys.argv[2] in n]); sys.exit(0 if rows and not any(r['status']=='FAIL' for r in rows) else 1)" "$@"; }
```

- [ ] **Step 2: Write the failing tests**

Create `tests/launch_universe_history.py` (LF line endings):

```python
"""Universe windows of the fixed driver and LiveHistory (spec section 12): invented books, flag and ticker reads,
snapshots and account anchors over a temporary state root and head root; no network, credentials or real home."""
from dataclasses import replace
from decimal import Decimal
import hashlib
from types import SimpleNamespace

from execution_launch.driver import ChooserInputs, chooser_decision
from execution_launch.profile import profile_contract_digest, rule_terms_digest
from execution_launch.program import ChooserState, ProgramSpec, program_digest
from execution_launch.strategy import UNIVERSE_EVALUATOR_REVISION
from tests import launch_driver as LD
from tests import launch_live_history as LH

D = Decimal
RULE = hashlib.sha256(b"fixture-universe-rule").hexdigest()
BTC, ETH, XRP = "KRW-BTC", "KRW-ETH", "KRW-XRP"


def universe_env():
    """LD.fixture() as a universe deployment: the rotation program (L=1, m=1, margin 0, N=2), an IOC profile with
    the rule, and a protocol whose symbol stays the benchmark KRW-BTC."""
    e = LD.fixture()
    program = ProgramSpec(schema_version=2, strategy_id=e.program.strategy_id, kind="universe_top1_momentum",
                          fast_window=0, slow_window=0, exposure_fraction=D("0.5"), lookback_slots=1,
                          min_hold_slots=1, switch_margin=D(0), max_candidates=2, universe_rule_sha256=RULE)
    code = program_digest(program, e.artifact)
    profile = replace(e.profile, strategy_code_sha256=code, time_in_force="ioc", universe_rule_sha256=RULE)
    protocol = replace(e.protocol, strategy_code_sha256=code, evaluator_revision=UNIVERSE_EVALUATOR_REVISION,
                       universe_rule_sha256=RULE, profile_contract_digest=profile_contract_digest(profile),
                       rule_terms_digest=rule_terms_digest(profile.instrument_rules, universe_rule_sha256=RULE))
    return SimpleNamespace(program=program, protocol=protocol, profile=profile, artifact=e.artifact,
                           window=replace(e.window, deployment_id="invented-universe-deployment"),
                           provider=e.provider, verifier=e.verifier)


def inputs(**changes):
    """The inputs of a decision with BTC held for two decisions and ETH well ahead over one slot."""
    values = dict(held=BTC, hold_count=2, top_n=(BTC, ETH), flags=((BTC, "unflagged"), (ETH, "unflagged")),
                  prices=((BTC, D(122)), (ETH, D(130))), lag_prices=((BTC, D(121)), (ETH, D(106))))
    return ChooserInputs(**(values | changes))


def test_chooser_decision_recomputes_one_decision_from_its_inputs():
    program = universe_env().program
    assert chooser_decision(program, inputs()) == (ETH, ChooserState(held=ETH, hold_count=1))
    assert chooser_decision(program, inputs(held=None, hold_count=0, lag_prices=None)) == (
        None, ChooserState(held=None, hold_count=1))
    assert chooser_decision(program, inputs(flags=((BTC, "warning"), (ETH, "unflagged")))) == (
        None, ChooserState(held=None, hold_count=1))
    for bad in (None, {"held": BTC}, inputs(top_n=[BTC, ETH]), inputs(flags=((BTC,),)),
                inputs(prices=((BTC, 122),)), inputs(top_n=(BTC, ETH, XRP))):
        LH.refused(lambda: chooser_decision(program, bad), "FIXED_DRIVER_CHOOSER_INPUTS_REQUIRED")
```

Append to the end of `tests/launch_live_history.py` (two blank lines before the first new line). `hashlib`,
`_canonical` and `history_frame_digest` are already imported there (lines 7, 21, 23 at fd85850):

```python
# Computed at fd85850 (before universe windows) from build() and record() of slots 0-4, frame at slot 4 + 2 s.
FIXED_FRAME_SHA256 = "59a151ab1b66133c71c030384df91a391178417f9249ec8a34a00558d4e16587"
FIXED_SLOT_DATA_SHA256 = "1354351db76d3a43b7e7ed508ae77fd98e3c22698cc70fefa1168c2b80c8bde8"


def test_fixed_window_frames_and_rows_are_byte_identical_to_fd85850():
    with head_root() as hroot:
        env = build(hroot)
        for i in range(5):
            record(env, i)
        frame = env.h.provider(obs(env, env.T(4) + seconds(2)))
        assert frame.universe_sha256 is None and frame.chooser_inputs is None
        assert history_frame_digest(frame) == FIXED_FRAME_SHA256
        data = [row["data"] for row in rows(env)[1:]]
        assert all(set(item) == {"index", "receipt", "anchor"} for item in data)
        assert hashlib.sha256(b"".join(_canonical(item) for item in data)).hexdigest() == FIXED_SLOT_DATA_SHA256
```

In `tests/launch_acceptance.py`, add `"launch_universe_history"` as the last entry of `MODULES`. After PR 2 and PR 4b
the tuple's last line (line 15 at fd85850) reads, in the order those PRs merged:

```python
           "launch_instrument_refresh", "launch_owner_ops", "owner_guards", "launch_owner_rehearsal",
           "launch_universe_store", "launch_program")
```

Replace it with:

```python
           "launch_instrument_refresh", "launch_owner_ops", "owner_guards", "launch_owner_rehearsal",
           "launch_universe_store", "launch_program", "launch_universe_history")
```

If the merged tuple differs, keep every entry it has and add `"launch_universe_history"` before the closing
parenthesis.

- [ ] **Step 3: Run the tests to verify they fail**

```bash
focus launch launch_universe_history/
focus launch launch_live_history/test_fixed_window_frames
```

Expected:
`FAIL launch_universe_history/import ImportError: cannot import name 'ChooserInputs' from 'execution_launch.driver'`
and
`FAIL launch_live_history/test_fixed_window_frames_and_rows_are_byte_identical_to_fd85850 AttributeError: 'HistoryFrame' object has no attribute 'universe_sha256'`.

- [ ] **Step 4: Write the implementation**

In `execution_launch/driver.py`, replace lines 26-27:

```python
from execution_launch.program import (ProgramSpec, parameters_json,
    program_digest, target_fraction)
```

with:

```python
from execution_launch.program import (ChooserSlot, ChooserState, ProgramSpec, choose,
    parameters_json, program_digest, target_fraction)
```

Insert before line 88 (`@dataclass(frozen=True, kw_only=True)` of `HistoryFrame`), after `AccountAnchor`:

```python
@dataclass(frozen=True, kw_only=True)
class UniverseBar:
    """One slot of a universe window (spec section 12): the trade coin the coordinator chose and its tick, with
    that coin's book, or no book fields (None) when its book was unavailable. A bar without a book has no price
    check and never anchors a quote."""
    observed_at: datetime
    received_at: datetime
    symbol: str
    tick_size: Decimal
    bid: Decimal | None
    ask: Decimal | None
    mark: Decimal | None
    source_sha256: str | None


@dataclass(frozen=True, kw_only=True)
class ChooserInputs:
    """Everything one universe decision reads (spec sections 12 and 14): the chooser state before it, the slot's
    top-N, flag classes and defined prices, and the defined prices lookback_slots earlier (None before that slot
    exists). Pairs are sorted by market."""
    held: str | None
    hold_count: int
    top_n: tuple[str, ...]
    flags: tuple[tuple[str, str], ...]
    prices: tuple[tuple[str, Decimal], ...]
    lag_prices: tuple[tuple[str, Decimal], ...] | None


```

Replace lines 98-100 (inside `HistoryFrame`):

```python
    bars: tuple[PaperBar, ...]
    prior_decision: PaperDecision | None
    anchor: AccountAnchor
```

with:

```python
    bars: tuple[PaperBar | UniverseBar, ...]
    prior_decision: PaperDecision | None
    anchor: AccountAnchor
    # Universe windows only: the digest of the current slot's universe record and the prior decision's inputs.
    # strategy._plain leaves both out while None, so a fixed frame keeps today's digest byte for byte.
    universe_sha256: str | None = field(default=None, metadata={"omit_none": True})
    chooser_inputs: ChooserInputs | None = field(default=None, metadata={"omit_none": True})
```

Insert after line 181 (the end of `history_frame_digest`), with two blank lines on each side:

```python
def chooser_decision(program: ProgramSpec, inputs: ChooserInputs) -> tuple[str | None, ChooserState]:
    """Recompute one universe decision from its carried inputs only (spec section 12), never the whole history."""
    _require(type(inputs) is ChooserInputs and type(inputs.top_n) is tuple and type(inputs.flags) is tuple
             and type(inputs.prices) is tuple and (inputs.lag_prices is None or type(inputs.lag_prices) is tuple),
             "FIXED_DRIVER_CHOOSER_INPUTS_REQUIRED")
    try:
        lag = None if inputs.lag_prices is None else ChooserSlot(top_n=(), flags={}, prices=dict(inputs.lag_prices))
        return choose(program, ChooserState(held=inputs.held, hold_count=inputs.hold_count),
                      ChooserSlot(top_n=inputs.top_n, flags=dict(inputs.flags), prices=dict(inputs.prices)), lag)
    except (TypeError, ValueError):
        raise FixedDriverError("FIXED_DRIVER_CHOOSER_INPUTS_REQUIRED") from None
```

`field` is already imported (`driver.py:11`). `choose` raises `ProgramError`, a `ValueError`.

- [ ] **Step 5: Run the focused tests and the module tests**

```bash
focus launch launch_universe_history/
focus launch launch_live_history/
focus launch launch_driver/
```

Expected: only `PASS` lines; each command exits 0.

- [ ] **Step 6: Commit**

```bash
git add execution_launch/driver.py tests/launch_universe_history.py tests/launch_live_history.py tests/launch_acceptance.py
diff <(git diff --cached --stat) <(git diff --cached --stat --ignore-cr-at-eol) && echo LF-OK
"$PY" -X utf8 -c "import sys; bad = [p for p in sys.argv[1:] if b'\r' in open(p, 'rb').read()]; print(bad); sys.exit(1 if bad else 0)" execution_launch/driver.py tests/launch_universe_history.py tests/launch_live_history.py tests/launch_acceptance.py
git commit -F - <<'EOF'
Add universe bars, chooser inputs and frame fields to the fixed driver

UniverseBar carries each slot's trade coin and tick, with no book fields when
the book was unavailable. ChooserInputs and chooser_decision recompute one
universe decision from carried inputs. HistoryFrame gains universe_sha256 and
chooser_inputs, left out of the digest while None, and a golden test pins the
fixed-window frame and rows to their fd85850 digests (spec section 12).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

Expected: `LF-OK`, then `[]` (no staged file holds a CR byte; `git diff --stat` alone misses a file written whole
with CRLF), then one commit.

---

### Task 2: Universe construction rule and history row v2 recording

**Files:**
- Modify: `execution_launch/driver.py:162-165` (`_identity` scope check)
- Modify: `execution_launch/live_history.py:22-25` (docstring), `:28-63` (imports and constants), insert after
  `:166` (module helpers), insert before `:213` (`SlotUniverse`), `:213-220` (`_Slot`), `:239-243` (`__init__`),
  `:298` and `:305-308` (`_anchor`), `:318-323` (`_slot_at`, `_derive`), insert after `:335` (universe methods),
  `:337-341` (`_frame`), `:462-475` (`record_slot`, `_record_universe`)
- Modify: `tests/launch_universe_history.py` (import block from Task 1, new helpers and tests appended)
- Modify: `tests/launch_live_history.py` (append one test)

**Interfaces:**
- Consumes: Task 1 (`UniverseBar`, `ChooserInputs`, `chooser_decision`, the frame fields, `universe_env`);
  PR 1 `core.compliance.model.Universe` (`day`, `rule_sha256`, `snapshot_sha256`, `valid_from`, `valid_until`,
  `listed`, `eligible`), `core.compliance.rules.UNIVERSE_MARKET`, `universe_top_n(universe, n)`; PR 2
  `execution_accounts.universe.FlagRead(ok, received_at, sha256, flags)` and `TickerRead(ok, received_at, sha256,
  prices: Mapping[str, tuple[Decimal, datetime]])`; PR 4b `ChooserState`; `execution_accounts.model.Position`
  (`symbol`, `units`, `price`, `asof`, and PR 4c's `unlisted: bool | None = None`); PR 4c `ioc` for Upbit in
  `validate_order`.
- Produces (`execution_launch/live_history.py`):
  - `@dataclass(frozen=True) class SlotUniverse: snapshot: Universe | None; flags: FlagRead; tickers: TickerRead;
    allow: frozenset[str]; reasons: tuple[str, ...]; events: tuple[str, ...]`.
  - `LiveHistory.record_slot(book, account, *, trade_symbol: str | None = None, universe: SlotUniverse | None = None,
    tick_size: Decimal | None = None, positions: tuple[Position, ...] = ()) -> str`. A fixed window refuses any of
    the keywords (`HISTORY_INPUT_REQUIRED`); a universe window requires the first three and accepts `book=None`.
  - `LiveHistory.recorded_allow: frozenset[str] | None`; `SIZE_FALLBACK = "HISTORY_ROW_SIZE_FALLBACK"`;
    `PRICE_WINDOW_MS = 60_000`; `MAX_PRICE_TEXT = 16`; `_START = ChooserState(held=None, hold_count=0)`.
  - Row v2 `data` keys: `index`, `trade_symbol`, `tick_size` (canonical text), `receipt` (receipt body or
    `"unavailable"`), `anchor`, `holdings` (sorted `[symbol, units, mark, mark_time, unlisted, dust]`), `universe`
    (`snapshot`: `{"day", "sha256", "top_n"}` or `"unavailable"`; `flags`: `{"sha256", "exceptions": [[market,
    class]]}` or `"unavailable"`; `tickers`: `{"sha256", "prices": [[market, price_text, offset_ms]]}` or
    `"unavailable"`; `allow`, `reasons`, `events` lists), `decision` (`{"coin", "target_fraction", "held",
    "hold_count"}` or `null` at the window end).
  - Methods used by Task 4: `LiveHistory._derive_universe(index, book, anchor, sampled_at, chain, prices, state,
    symbol, tick, record) -> (bar, decision, chain, prices, state, inputs, choice)` and
    `LiveHistory._holding(symbol, units, price, asof) -> list`; module helpers `_sha256(value) -> bool`,
    `_markets(value) -> bool`, `_price_text(price) -> str | None`, `_chooser_parts(record)`.
  - Refusal `HISTORY_BOOK_OFF_TICK`.
- Produces (`execution_launch/driver.py`): a universe protocol needs an `ioc` profile with its symbol, the same
  `universe_rule_sha256` on profile, program and protocol, and program kind `universe_top1_momentum`; a fixed one
  keeps `gtc`; otherwise `FIXED_DRIVER_SCOPE_MISMATCH`.
- Test helpers (`tests/launch_universe_history.py`): `NAME`, `SWITCH`, `ALL_UNFLAGGED`, `pairs(prices)`,
  `snapshot(env, listed=...)`, `reads(env, i, prices, *, snap=None, flags=None, allow=...)`, `down(env, i)`,
  `book(env, i, symbol=BTC, bid=None, ask=None)`, `account(env, i, *, cash=..., holdings=None)`, `ubuild(hroot,
  name=NAME, end=None)`, `record(env, i, prices, *, symbol, booked, tick, bid, ask, cash, holdings, positions,
  slot_universe)`, `tick(env, i, *, symbol, tick_size, bid, ask, cash, holdings, driver)`, `substitute(env, frame)`.

- [ ] **Step 1: Write the failing tests**

In `tests/launch_universe_history.py`, replace the Task 1 import block:

```python
from dataclasses import replace
from decimal import Decimal
import hashlib
from types import SimpleNamespace

from execution_launch.driver import ChooserInputs, chooser_decision
from execution_launch.profile import profile_contract_digest, rule_terms_digest
from execution_launch.program import ChooserState, ProgramSpec, program_digest
from execution_launch.strategy import UNIVERSE_EVALUATOR_REVISION
from tests import launch_driver as LD
from tests import launch_live_history as LH
```

with:

```python
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
import hashlib
from types import SimpleNamespace
from unittest.mock import patch

from core.compliance import model as M
from core.compliance.model import Universe
from execution_accounts.collector import SourceReceipt
from execution_accounts.model import Position
from execution_accounts.quotes import parse_orderbook, to_runner_quote
from execution_accounts.universe import FlagRead, TickerRead
from execution_control.controller import AccountObservation
from execution_control.risk import RiskObservation
from execution_control.store import GENESIS, MAX_ROW_BYTES, _utc
from execution_launch.baseline_head import BaselineHead
from execution_launch.driver import ChooserInputs, UniverseBar, chooser_decision, describe_fixed_driver
from execution_launch.live_history import SIZE_FALLBACK, SlotUniverse
from execution_launch.profile import profile_contract_digest, rule_terms_digest
from execution_launch.program import ChooserState, ProgramSpec, program_digest
from execution_launch.runner import DecisionInput
from execution_launch.strategy import UNIVERSE_EVALUATOR_REVISION, evidence_digest
from tests import launch_driver as LD
from tests import launch_live_history as LH
from tests.launch_baseline_head import head_root
```

Append to the end of `tests/launch_universe_history.py` (two blank lines before the first new line):

```python
NAME = "universe-history"
# Under universe_env's program and the top-2 (BTC, ETH) these give the decisions cash, BTC, BTC, ETH, ETH, ETH.
SWITCH = ({BTC: D(100), ETH: D(100), XRP: D(100)}, {BTC: D(110), ETH: D(105), XRP: D(200)},
          {BTC: D(121), ETH: D(106), XRP: D(200)}, {BTC: D(122), ETH: D(130), XRP: D(200)},
          {BTC: D(122), ETH: D(131), XRP: D(200)}, {BTC: D(122), ETH: D(132), XRP: D(200)})
ALL_UNFLAGGED = ((BTC, "unflagged"), (ETH, "unflagged"), (XRP, "unflagged"))


def pairs(prices):
    return tuple(sorted(prices.items()))


def snapshot(env, listed=(BTC, ETH, XRP)):
    """An invented snapshot in force over the whole window; its top-2 is (BTC, ETH)."""
    start = env.window.start
    return Universe(day=start.date(), rule_sha256=RULE, snapshot_sha256="e" * 64, built_at=start - timedelta(hours=1),
                    valid_from=start - timedelta(hours=1), valid_until=start + timedelta(days=1),
                    listed=tuple(sorted(listed)), eligible=((BTC, D(3000)), (ETH, D(2000))))


def reads(env, i, prices, *, snap=None, flags=None, allow=frozenset({BTC, ETH})):
    """Slot i's universe inputs: the window's snapshot, every priced market unflagged unless `flags` says
    otherwise, each trade 2 s before the slot, invented raw-body digests."""
    slot = env.T(i)
    return SlotUniverse(snapshot=snapshot(env) if snap is None else snap,
                        flags=FlagRead(ok=True, received_at=slot, sha256="1" * 64,
                                       flags={market: "unflagged" for market in prices} | (flags or {})),
                        tickers=TickerRead(ok=True, received_at=slot, sha256="2" * 64,
                                           prices={market: (price, slot - LH.seconds(2))
                                                   for market, price in prices.items()}),
                        allow=allow, reasons=(), events=())


def down(env, i):
    """Slot i with every universe read unavailable: no snapshot, failed flag and ticker reads, nothing allowed."""
    return SlotUniverse(snapshot=None, flags=FlagRead(ok=False, received_at=None, sha256=None, flags={}),
                        tickers=TickerRead(ok=False, received_at=None, sha256=None, prices={}),
                        allow=frozenset(), reasons=("UNIVERSE_NO_SNAPSHOT",), events=())


def book(env, i, symbol=BTC, bid=None, ask=None):
    """LH.book_at's invented single-level book for any coin and price; the body text keeps exact decimals."""
    slot, when = env.T(i), env.T(i) - LH.seconds(1)
    bid, ask = (D(100 + i) if bid is None else bid), (D(102 + i) if ask is None else ask)
    raw = ('[{"market": "%s", "level": 0, "timestamp": %d, "total_ask_size": 3, "total_bid_size": 4, '
           '"orderbook_units": [{"ask_price": %s, "bid_price": %s, "ask_size": 3, "bid_size": 4}]}]'
           % (symbol, LH.ms(slot - LH.seconds(2)), ask, bid)).encode()
    receipt = SourceReceipt(path="/v1/orderbook", params=(("markets", symbol), ("level", "0"), ("count", "30")),
                            account_scope="public-upbit-orderbook", received_at=when, server_time=when,
                            raw_body=raw, sha256=hashlib.sha256(raw).hexdigest())
    return parse_orderbook(receipt, symbol=symbol, now=when)


def account(env, i, *, cash=D(10000), holdings=None):
    """The account 1 s before slot i: settled cash and `holdings` (coin to units), each unit worth 101 KRW."""
    profile, asof, held = env.profile, env.T(i) - LH.seconds(1), holdings or {}
    key = (profile.venue, profile.account_scope)
    inventory = sum((units * D(101) for units in held.values()), D(0))
    equity = cash + inventory
    return AccountObservation(positions=M.Positions(equity_krw=float(equity), holdings={}, exposure={}),
        account_scopes={profile.venue: profile.account_scope}, settled_cash_krw={key: cash},
        holdings={(*key, profile.market, coin): units for coin, units in held.items()},
        held_exposure_krw={key: equity}, inventory_exposure_krw={key: inventory},
        quote_currency_by_account={key: "KRW"}, quote_rates_krw={(*key, "KRW"): D(1)},
        risk=RiskObservation(equity=equity, prior_high_watermark=equity, day_start_equity=equity,
            current_day_realized_net_profit=D(0), prior_day_realized_net_profit=D(10),
            observed_daily_loss=D(0), approved_effective_floor=None, is_first_trading_day=False, asof=asof),
        asof=asof, server_time=asof, no_credit=True)


def ubuild(hroot, name=NAME, end=None):
    """A bound universe LiveHistory and its fixed driver over the temporary roots (LH.build's shape); `end`
    shortens the window to that many minutes after its start."""
    e = universe_env()
    if end is not None:
        e.window = replace(e.window, end=e.window.start + timedelta(minutes=end))
    start = e.window.start
    env = SimpleNamespace(e=e, profile=e.profile, window=e.window, hroot=hroot, name=name, start=start,
                          c=[start - timedelta(minutes=5)], T=lambda i: start + timedelta(minutes=i))
    env.clock = lambda: env.c[0]
    env.head = BaselineHead(root=hroot, name=name, chain=LH.chain_for(env))
    env.head.initialize_reviewed_head(GENESIS)
    LH.attach(env)
    env.identity = env.h.bind(env.d)
    return env


def record(env, i, prices, *, symbol=BTC, booked=True, tick=D(1), bid=None, ask=None, cash=D(10000),
           holdings=None, positions=(), slot_universe=None):
    """Record slot i at slot + 1 s: `symbol`'s book (or none), the account and the slot's universe inputs."""
    env.c[0] = env.T(i) + LH.seconds(1)
    return env.h.record_slot(book(env, i, symbol, bid, ask) if booked else None,
                             account(env, i, cash=cash, holdings=holdings), trade_symbol=symbol,
                             universe=reads(env, i, prices) if slot_universe is None else slot_universe,
                             tick_size=tick, positions=positions)


def tick(env, i, *, symbol=BTC, tick_size=D(1), bid=None, ask=None, cash=D(10000), holdings=None, driver=None):
    """One driver tick at slot i + 2 s, with the profile renewed to `symbol` at `tick_size` (only fields the
    universe contract digest leaves out change) and the quote of the book `record` used."""
    now = env.T(i) + LH.seconds(2)
    env.c[0] = now
    driver = driver or env.d
    rules = replace(env.profile.instrument_rules, symbol=symbol, tick_size=tick_size)
    observation = DecisionInput(now=now, profile=replace(env.profile, symbol=symbol, instrument_rules=rules),
                                quote=to_runner_quote(book(env, i, symbol, bid, ask), now=now),
                                account=account(env, i, cash=cash, holdings=holdings))
    return driver.callback(observation, driver.parameters_json)


def substitute(env, frame):
    """Another issued driver of the same universe deployment, handed `frame` and the fixture's invented
    authentication, so only the driver's own frame checks can refuse."""
    return LD.construct(env.e, window=env.window, history_provider=lambda observation: frame,
                        history_verifier=LD.invented_authentication)


def test_universe_driver_construction_pins_benchmark_symbol_ioc_and_rule():
    e = universe_env()
    assert describe_fixed_driver(LD.construct(e)).profile_contract_digest == e.protocol.profile_contract_digest
    for changes in ({"time_in_force": "gtc"}, {"symbol": ETH}, {"universe_rule_sha256": "c" * 64}):
        changed = SimpleNamespace(**(vars(e) | {"profile": replace(e.profile, **changes)}))
        LD.reject(lambda: LD.construct(changed), "FIXED_DRIVER_SCOPE_MISMATCH")
    fixed = LD.fixture()
    changed = SimpleNamespace(**(vars(fixed) | {"profile": replace(fixed.profile, time_in_force="ioc")}))
    LD.reject(lambda: LD.construct(changed), "FIXED_DRIVER_SCOPE_MISMATCH")


def test_universe_slots_require_their_inputs_and_a_book_of_the_coin_at_its_tick():
    with head_root() as hroot:
        env = ubuild(hroot)
        env.c[0] = env.T(0) + LH.seconds(1)
        acct, slot = account(env, 0), reads(env, 0, SWITCH[0])
        for options in ({}, {"trade_symbol": BTC, "tick_size": D(1)}, {"universe": slot, "tick_size": D(1)},
                        {"trade_symbol": "BTC", "universe": slot, "tick_size": D(1)},
                        {"trade_symbol": BTC, "universe": slot, "tick_size": D(0)},
                        {"trade_symbol": BTC, "universe": slot, "tick_size": D(1), "positions": [()]},
                        {"trade_symbol": BTC, "universe": replace(slot, allow=[BTC]), "tick_size": D(1)}):
            LH.refused(lambda: env.h.record_slot(book(env, 0), acct, **options), "HISTORY_INPUT_REQUIRED")
        options = {"trade_symbol": BTC, "universe": slot, "tick_size": D(1)}
        LH.refused(lambda: env.h.record_slot(book(env, 0, ETH), acct, **options), "HISTORY_BOOK_MARKET_MISMATCH")
        LH.refused(lambda: env.h.record_slot(book(env, 0, BTC, D("100.5"), D(102)), acct, **options),
                   "HISTORY_BOOK_OFF_TICK")
        assert len(LH.rows(env)) == 1 and env.h.recorded_allow is None
        env.h.record_slot(None, acct, **options)
        assert LH.rows(env)[1]["data"]["receipt"] == "unavailable"
        assert env.h.recorded_allow == frozenset({BTC, ETH})


def test_history_row_v2_records_the_slot_universe_and_frames_carry_it():
    with head_root() as hroot:
        env = ubuild(hroot)
        stamp = env.T(1) - LH.seconds(3)
        positions = (Position(market="spot", symbol=ETH, base_currency="ETH", quote_currency="KRW", units=D(2),
                              price=D(105), asof=stamp),
                     Position(market="spot", symbol="KRW-OLD", base_currency="OLD", quote_currency="KRW",
                              units=D(7), price=D(0), asof=stamp, unlisted=True))
        record(env, 0, SWITCH[0])
        record(env, 1, SWITCH[1], symbol=ETH, holdings={ETH: D(2)}, positions=positions)
        record(env, 2, SWITCH[2], slot_universe=reads(env, 2, SWITCH[2], flags={XRP: "caution"}))
        record(env, 3, SWITCH[3], booked=False)
        assert env.h.recorded_allow == frozenset({BTC, ETH})
        record(env, 4, SWITCH[4], slot_universe=down(env, 4))
        data = [row["data"] for row in LH.rows(env)[1:]]
        assert all(set(item) == {"index", "trade_symbol", "tick_size", "receipt", "anchor", "holdings", "universe",
                                 "decision"} for item in data)
        assert [item["trade_symbol"] for item in data] == [BTC, ETH, BTC, BTC, BTC]
        assert data[1]["tick_size"] == "1" and data[1]["receipt"]["sha256"] == book(env, 1, ETH).receipt.sha256
        assert data[1]["anchor"] == {"cash_quote": "10000", "units": "2", "account_asof": _utc(env.T(1) - LH.seconds(1))}
        assert data[1]["holdings"] == [[ETH, "2", "105", _utc(stamp), False, False],
                                       ["KRW-OLD", "7", "0", _utc(stamp), True, True]]
        assert data[1]["universe"] == {
            "snapshot": {"day": env.window.start.date().isoformat(), "sha256": "e" * 64, "top_n": [BTC, ETH]},
            "flags": {"sha256": "1" * 64, "exceptions": []},
            "tickers": {"sha256": "2" * 64,
                        "prices": [[BTC, "110", -2000], [ETH, "105", -2000], [XRP, "200", -2000]]},
            "allow": [BTC, ETH], "reasons": [], "events": []}
        assert [item["decision"] for item in data] == [
            {"coin": None, "target_fraction": "0", "held": None, "hold_count": 1},
            {"coin": BTC, "target_fraction": "0.5", "held": BTC, "hold_count": 1},
            {"coin": BTC, "target_fraction": "0.5", "held": BTC, "hold_count": 2},
            {"coin": ETH, "target_fraction": "0.5", "held": ETH, "hold_count": 1},
            {"coin": ETH, "target_fraction": "0.5", "held": ETH, "hold_count": 2}]
        assert data[2]["universe"]["flags"]["exceptions"] == [[XRP, "caution"]]
        assert data[3]["receipt"] == "unavailable"
        assert data[4]["universe"] == {"snapshot": "unavailable", "flags": "unavailable", "tickers": "unavailable",
                                       "allow": [], "reasons": ["UNIVERSE_NO_SNAPSHOT"], "events": []}
        assert env.h.recorded_allow == frozenset()
        frame = env.h.provider(LH.obs(env, env.T(4) + LH.seconds(2)))
        assert frame.universe_sha256 == evidence_digest(data[4]["universe"])
        assert frame.bars[3] == UniverseBar(observed_at=env.T(3), received_at=env.T(3) + LH.seconds(1), symbol=BTC,
                                            tick_size=D(1), bid=None, ask=None, mark=None, source_sha256=None)
        assert (frame.bars[1].symbol, frame.bars[1].bid, frame.bars[1].ask) == (ETH, D(101), D(103))
        assert frame.chooser_inputs == ChooserInputs(held=BTC, hold_count=2, top_n=(BTC, ETH), flags=ALL_UNFLAGGED,
                                                     prices=pairs(SWITCH[3]), lag_prices=pairs(SWITCH[2]))


def test_oversized_row_drops_flag_and_ticker_parts_and_allows_no_buys():
    with head_root() as hroot:
        env = ubuild(hroot)
        extra = tuple("KRW-X%05d" % n for n in range(8000))
        prices = {market: D("1234567.12345678") for market in extra} | SWITCH[0]
        snap = snapshot(env, listed=(BTC, ETH, XRP) + extra)
        record(env, 0, prices, slot_universe=reads(env, 0, prices, snap=snap))
        assert len(LH.journal(env).read_bytes().splitlines()[1]) < MAX_ROW_BYTES
        assert LH.rows(env)[1]["data"]["universe"] == {
            "snapshot": {"day": env.window.start.date().isoformat(), "sha256": "e" * 64, "top_n": [BTC, ETH]},
            "flags": "unavailable", "tickers": "unavailable", "allow": [], "reasons": [SIZE_FALLBACK], "events": []}
        assert env.h.recorded_allow == frozenset()
        record(env, 1, SWITCH[1])
        assert LH.rows(env)[2]["data"]["universe"]["tickers"]["prices"][0] == [BTC, "110", -2000]
        assert env.h.recorded_allow == frozenset({BTC, ETH})
```

Append to the end of `tests/launch_live_history.py`:

```python
def test_fixed_window_refuses_universe_inputs():
    with head_root() as hroot:
        env = build(hroot)
        env.c[0] = env.T(0) + seconds(1)
        account = account_at(env, env.T(0) - seconds(1))
        for options in ({"trade_symbol": SYMBOL}, {"tick_size": D(1)}, {"universe": object()},
                        {"positions": (None,)}):
            refused(lambda: env.h.record_slot(book_at(env, 0), account, **options), "HISTORY_INPUT_REQUIRED")
        assert len(rows(env)) == 1
        record(env, 0)
        assert set(rows(env)[1]["data"]) == {"index", "receipt", "anchor"}
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
focus launch launch_universe_history/
focus launch launch_live_history/test_fixed_window_refuses
```

Expected: a line starting
`FAIL launch_universe_history/import ImportError: cannot import name 'SIZE_FALLBACK' from 'execution_launch.live_history'`
(the message ends with the module path), and
`FAIL launch_live_history/test_fixed_window_refuses_universe_inputs TypeError: LiveHistory.record_slot() got an unexpected keyword argument 'trade_symbol'`.

- [ ] **Step 3: Write the driver construction rule**

In `execution_launch/driver.py`, replace lines 162-165 (inside `_identity`):

```python
    _require((profile.venue, profile.market, profile.symbol, profile.quote_currency, profile.time_in_force)
             == (protocol.venue, protocol.market, protocol.symbol, "KRW", "gtc")
             and profile.account_scope is not None and profile.instrument_rules is not None,
             "FIXED_DRIVER_SCOPE_MISMATCH")
```

with:

```python
    universe = protocol.universe_rule_sha256 is not None
    # A universe protocol's symbol is the benchmark KRW-BTC, never a trading pin: a universe launch profile starts
    # with it, trades with IOC orders and carries the same signed rule as its program (spec section 12).
    _require((profile.venue, profile.market, profile.symbol, profile.quote_currency, profile.time_in_force)
             == (protocol.venue, protocol.market, protocol.symbol, "KRW", "ioc" if universe else "gtc")
             and profile.universe_rule_sha256 == program.universe_rule_sha256 == protocol.universe_rule_sha256
             and (program.kind == "universe_top1_momentum") == universe
             and profile.account_scope is not None and profile.instrument_rules is not None,
             "FIXED_DRIVER_SCOPE_MISMATCH")
```

PR 4c does not edit `execution_launch/driver.py` (it allows `ioc` only in `validate_order`), and PR 0 adds its lines
after this block, so the quoted text is still exact when this task runs. If the old block is not found, stop and
report the difference instead of merging by hand.

- [ ] **Step 4: Write the LiveHistory recording**

In `execution_launch/live_history.py`, replace lines 22-25 (end of the module docstring):

```python
which the trusted head replaces here; its row codec, lock and sync helpers are reused as they are. Not defended: a
process that rewrites the journal and the head coherently (the ceiling stated in baseline_head). Nothing here
fetches, signs, arms, orders or reads credentials.
"""
```

with:

```python
which the trusted head replaces here; its row codec, lock and sync helpers are reused as they are. Not defended: a
process that rewrites the journal and the head coherently (the ceiling stated in baseline_head). Nothing here
fetches, signs, arms, orders or reads credentials.

A universe window (``protocol.universe_rule_sha256`` set) records history row v2 instead (spec section 12): the
trade coin the coordinator chose and its tick, that coin's book receipt or ``"unavailable"``, the anchor of that
coin, every holding, the slot's universe record (snapshot in force, flag exceptions and defined ticker prices with
the raw-body sha256s, allow-list, buy-block reasons, events) and the chooser's decision. The section 14 chooser runs
here at recording and again at replay, over the last L+1 price vectors, h and the hold count, and replay requires
the stored decision to equal the derived one. A row over the cap drops the flag and ticker parts and allows no
buys; it is never refused for size.
"""
```

Replace lines 28-63 (imports and constants):

```python
import base64
from contextlib import contextmanager
from dataclasses import asdict, dataclass, fields
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import hashlib
import os
from pathlib import Path
import stat
import threading
from typing import Callable

from core.isolation import checked_target, state_root
from execution_accounts.collector import SourceReceipt
from execution_control.capability import digest
from execution_control.controller import AccountObservation
from execution_control.store import (GENESIS, MAX_ROW_BYTES, SCHEMA, _ROW_KEYS, _canonical, _decode, _lock,
                                     _sync_directory, _utc, _valid_stamp)
from execution_launch.baseline_head import BaselineHead, BaselineHeadError
from execution_launch.driver import (AccountAnchor, DeploymentWindow, FixedDriverIdentity, HistoryFrame,
                                     HistoryReceipt, describe_fixed_driver, fixed_history_dependencies,
                                     history_frame_digest)
from execution_launch.paper_capture import sample_prefetched_book
from execution_launch.profile import LaunchProfile, profile_contract_digest
from execution_launch.program import ProgramSpec, program_digest, target_fraction
from execution_launch.runner import DecisionInput, StrategyDriver
from execution_launch.strategy import ForwardProtocol, PaperBar, PaperDecision, _decimal, _plain, evidence_digest

STORE_DIRECTORY = "execution-history"
EXECUTION_WINDOW = timedelta(seconds=10)     # the driver's slot window and the quote freshness bound
ACCOUNT_MAX_AGE = timedelta(seconds=30)      # the driver's account-anchor age bound
_LOCK = threading.Lock()                     # own lock: the head takes its own, the chain reads without one
_NAMES = ("history.jsonl", "history.lock")
_RECEIPT_KEYS = frozenset({"path", "params", "account_scope", "received_at", "server_time", "raw_body_b64", "sha256"})
_ANCHOR_KEYS = frozenset({"cash_quote", "units", "account_asof"})
_IDENTITY_KEYS = frozenset(f.name for f in fields(FixedDriverIdentity))
```

with:

```python
import base64
from contextlib import contextmanager
from dataclasses import asdict, dataclass, fields
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from fractions import Fraction
import hashlib
import os
from pathlib import Path
import stat
import threading
from typing import Callable

from core.compliance.model import Universe
from core.compliance.rules import UNIVERSE_MARKET, universe_top_n
from core.isolation import checked_target, state_root
from execution_accounts.collector import SourceReceipt
from execution_accounts.model import Position
from execution_accounts.universe import FlagRead, TickerRead
from execution_control.capability import digest
from execution_control.controller import AccountObservation
from execution_control.store import (GENESIS, MAX_ROW_BYTES, SCHEMA, _HASH, _ROW_KEYS, _canonical, _decode, _lock,
                                     _sync_directory, _utc, _valid_stamp)
from execution_launch.baseline_head import BaselineHead, BaselineHeadError
from execution_launch.driver import (AccountAnchor, ChooserInputs, DeploymentWindow, FixedDriverIdentity,
                                     HistoryFrame, HistoryReceipt, UniverseBar, chooser_decision,
                                     describe_fixed_driver, fixed_history_dependencies, history_frame_digest)
from execution_launch.paper_capture import sample_prefetched_book
from execution_launch.profile import LaunchProfile, profile_contract_digest
from execution_launch.program import ChooserState, ProgramSpec, program_digest, target_fraction
from execution_launch.runner import DecisionInput, StrategyDriver
from execution_launch.strategy import ForwardProtocol, PaperBar, PaperDecision, _decimal, _plain, evidence_digest

STORE_DIRECTORY = "execution-history"
EXECUTION_WINDOW = timedelta(seconds=10)     # the driver's slot window and the quote freshness bound
ACCOUNT_MAX_AGE = timedelta(seconds=30)      # the driver's account-anchor age bound
SIZE_FALLBACK = "HISTORY_ROW_SIZE_FALLBACK"  # buy-block reason of a row whose flag and ticker parts hit the cap
PRICE_WINDOW_MS = 60_000                     # a price is defined only for a trade within 60 s of the slot (section 14)
MAX_PRICE_TEXT = 16                          # section 14 price encoding: a decimal string of at most 16 characters
_LOCK = threading.Lock()                     # own lock: the head takes its own, the chain reads without one
_NAMES = ("history.jsonl", "history.lock")
_RECEIPT_KEYS = frozenset({"path", "params", "account_scope", "received_at", "server_time", "raw_body_b64", "sha256"})
_ANCHOR_KEYS = frozenset({"cash_quote", "units", "account_asof"})
_IDENTITY_KEYS = frozenset(f.name for f in fields(FixedDriverIdentity))
_EXCEPTION_CLASSES = ("caution", "unknown", "warning")   # the flag classes a row lists; "unflagged" is implied
_START = ChooserState(held=None, hold_count=0)           # a window's chooser starts in cash (PR 4b)
```

Insert after line 166 (the end of `_parse_anchor`), with two blank lines on each side:

```python
def _sha256(value):
    return type(value) is str and _HASH.fullmatch(value) is not None


def _markets(value):
    """A list of distinct KRW market ids."""
    return (type(value) is list and all(type(item) is str and UNIVERSE_MARKET.fullmatch(item) is not None
                                        for item in value) and len(set(value)) == len(value))


def _price_text(price):
    """A defined price in the section 14 encoding: a positive finite Decimal as canonical text of at most 16
    characters. Anything else is no price at that slot."""
    if type(price) is not Decimal or not price.is_finite() or price <= 0:
        return None
    try:
        text = _plain(price)
    except ValueError:
        return None
    return text if len(text) <= MAX_PRICE_TEXT else None


def _chooser_parts(record):
    """(top_n, flags, prices) of one stored universe record, as ChooserInputs holds them. Prices exist only when
    both reads were available; a priced market is unflagged unless it is a recorded exception (spec section 14)."""
    top_n = () if record["snapshot"] == "unavailable" else tuple(record["snapshot"]["top_n"])
    flags = {} if record["flags"] == "unavailable" else {market: kind for market, kind in record["flags"]["exceptions"]}
    prices = {}
    if record["tickers"] != "unavailable":
        for market, text, _ in record["tickers"]["prices"]:
            prices[market] = _decimal(text)
            flags.setdefault(market, "unflagged")
    return top_n, tuple(sorted(flags.items())), tuple(sorted(prices.items()))
```

Insert before line 213 (the `@dataclass` of `_Slot`):

```python
@dataclass(frozen=True)
class SlotUniverse:
    """The coordinator's universe inputs for one slot (spec section 12): the snapshot in force (None when there is
    none), the slot's flag and ticker reads, and the allow-list, buy-block reasons and events it derived."""
    snapshot: Universe | None
    flags: FlagRead
    tickers: TickerRead
    allow: frozenset[str]
    reasons: tuple[str, ...]
    events: tuple[str, ...]


```

Replace lines 213-220 (`_Slot`):

```python
@dataclass(frozen=True, kw_only=True)
class _Slot:
    """In-memory, verified and derived; never serialized."""
    bar: PaperBar
    anchor: AccountAnchor
    decision: PaperDecision | None       # None only at the window end
    sampled_at: datetime
    row_sha256: str
```

with:

```python
@dataclass(frozen=True, kw_only=True)
class _Slot:
    """In-memory, verified and derived; never serialized."""
    bar: PaperBar | UniverseBar
    anchor: AccountAnchor
    decision: PaperDecision | None       # None only at the window end
    sampled_at: datetime
    row_sha256: str
    universe_sha256: str | None = None   # universe windows: evidence_digest of the slot's stored universe record
```

Replace lines 239-243 (in `LiveHistory.__init__`):

```python
        self._program, self._protocol, self._profile, self._window = program, protocol, profile, window
        self._clock, self._head_authority = clock, trusted_head
        self._identity, self._bound, self._failed = "", False, False
        self._slots, self._chain, self._marks = (), "", ()
        self._head, self._size, self._seq = GENESIS, 0, 0
```

with:

```python
        self._program, self._protocol, self._profile, self._window = program, protocol, profile, window
        self._universe = protocol.universe_rule_sha256 is not None   # a universe window records history row v2
        self._clock, self._head_authority = clock, trusted_head
        self._identity, self._bound, self._failed = "", False, False
        self._slots, self._chain, self._marks = (), "", ()
        self._prices, self._state, self._inputs = (), _START, ()    # last L+1 price vectors, h and count, inputs
        self.recorded_allow = None   # the allow-list of the last universe row; that slot's buys use only it
        self._head, self._size, self._seq = GENESIS, 0, 0
```

Replace line 298:

```python
    def _anchor(self, account):
```

with:

```python
    def _anchor(self, account, symbol):
```

and replace lines 305-308 (inside `_anchor`):

```python
            anchor = AccountAnchor(cash_quote=account.settled_cash_krw[key],
                                   units=account.holdings.get((venue, scope, self._profile.market,
                                                               self._profile.symbol), Decimal(0)),
                                   account_asof=account.asof)
```

with:

```python
            anchor = AccountAnchor(cash_quote=account.settled_cash_krw[key],
                                   units=account.holdings.get((venue, scope, self._profile.market, symbol),
                                                              Decimal(0)),
                                   account_asof=account.asof)
```

Replace lines 318-323 (start of `_derive`):

```python
    def _derive(self, index, book, anchor, sampled_at, chain, marks):
        """The bar, the decision and the running chain for slot `index`, under the same rules at recording and replay."""
        slot = self._window.start + index * self._step
        _require(slot <= self._window.end, "HISTORY_WINDOW_COMPLETE")
        _require(slot <= sampled_at, "HISTORY_SLOT_NOT_DUE")
        _require(sampled_at <= slot + EXECUTION_WINDOW, "HISTORY_SLOT_MISSED")
```

with:

```python
    def _slot_at(self, index, sampled_at):
        """Slot `index`'s time; a slot is recorded only inside [slot, slot + 10 s] and never past the window end."""
        slot = self._window.start + index * self._step
        _require(slot <= self._window.end, "HISTORY_WINDOW_COMPLETE")
        _require(slot <= sampled_at, "HISTORY_SLOT_NOT_DUE")
        _require(sampled_at <= slot + EXECUTION_WINDOW, "HISTORY_SLOT_MISSED")
        return slot

    def _derive(self, index, book, anchor, sampled_at, chain, marks):
        """The bar, the decision and the running chain for slot `index`, under the same rules at recording and replay."""
        slot = self._slot_at(index, sampled_at)
```

Insert after line 335 (`return bar, decision, chain, marks`, the end of `_derive`), with one blank line before each
method:

```python
    def _holding(self, symbol, units, price, asof):
        """One holding of the row's account anchor (spec section 12): symbol, units, mark, mark time, unlisted
        (marked at 0, spec section 11) and dust (worth less than the signed minimum order at its mark; an unlisted
        holding is always dust)."""
        _require(type(symbol) is str and UNIVERSE_MARKET.fullmatch(symbol) is not None
                 and type(units) is Decimal and units.is_finite() and units >= 0
                 and type(price) is Decimal and price.is_finite() and price >= 0 and _aware(asof),
                 "HISTORY_INPUT_REQUIRED")
        minimum = Fraction(self._profile.instrument_rules.min_notional_krw)
        return [symbol, _plain(units), _plain(price), _utc(asof), price == 0,
                price == 0 or Fraction(units) * Fraction(price) < minimum]

    def _universe_record(self, slot, universe):
        """The row's universe part (spec section 12): the snapshot in force (day, sha256, top-N), the flag read's
        exceptions and the ticker read's defined prices of listed coins, each with its raw-body sha256 or
        "unavailable", then the allow-list, buy-block reasons and events as given. A price is kept only for a market
        the flag read lists, so the ticker part is unavailable whenever the flag part is."""
        _require(type(universe.allow) is frozenset and type(universe.reasons) is tuple
                 and type(universe.events) is tuple and _markets(sorted(universe.allow))
                 and all(type(item) is str for item in universe.reasons + universe.events),
                 "HISTORY_INPUT_REQUIRED")
        snapshot, flags, tickers = universe.snapshot, universe.flags, universe.tickers
        in_force = (type(snapshot) is Universe and snapshot.rule_sha256 == self._protocol.universe_rule_sha256
                    and snapshot.valid_from <= slot < snapshot.valid_until)
        flagged = (type(flags) is FlagRead and flags.ok is True and _sha256(flags.sha256)
                   and _markets(list(flags.flags)))
        priced = flagged and type(tickers) is TickerRead and tickers.ok is True and _sha256(tickers.sha256)
        prices = []
        for market in snapshot.listed if priced and in_force else ():
            if market in flags.flags and market in tickers.prices:
                price, traded = tickers.prices[market]
                offset = (traded - slot) // timedelta(milliseconds=1)
                text = _price_text(price)
                if text is not None and abs(offset) <= PRICE_WINDOW_MS:
                    prices.append([market, text, offset])
        return {"snapshot": {"day": snapshot.day.isoformat(), "sha256": snapshot.snapshot_sha256,
                             "top_n": list(universe_top_n(snapshot, self._program.max_candidates))}
                if in_force else "unavailable",
                "flags": {"sha256": flags.sha256,
                          "exceptions": sorted([market, kind if kind in _EXCEPTION_CLASSES else "unknown"]
                                               for market, kind in flags.flags.items() if kind != "unflagged")}
                if flagged else "unavailable",
                "tickers": {"sha256": tickers.sha256, "prices": prices} if priced else "unavailable",
                "allow": sorted(universe.allow), "reasons": list(universe.reasons), "events": list(universe.events)}

    def _derive_universe(self, index, book, anchor, sampled_at, chain, prices, state, symbol, tick, record):
        """A universe slot (spec section 12): the recorded trade coin's bar (no book fields when its book was
        unavailable), the section 14 decision from the stored record, and the running chain, last L+1 price vectors
        and chooser state, under the same rules at recording and replay."""
        slot = self._slot_at(index, sampled_at)
        if book is None:
            bar = UniverseBar(observed_at=slot, received_at=sampled_at, symbol=symbol, tick_size=tick,
                              bid=None, ask=None, mark=None, source_sha256=None)
        else:
            paper = sample_prefetched_book(book, slot=slot, sampled_at=sampled_at)
            _require(book.symbol == symbol, "HISTORY_BOOK_MARKET_MISMATCH")
            # The driver re-checks every bar at its own tick on every later tick, so an off-tick book would block
            # the rest of the window; it is refused here and the caller can record the slot without a book.
            _require((Fraction(paper.bid) / Fraction(tick)).denominator == 1
                     and (Fraction(paper.ask) / Fraction(tick)).denominator == 1, "HISTORY_BOOK_OFF_TICK")
            bar = UniverseBar(observed_at=slot, received_at=sampled_at, symbol=symbol, tick_size=tick,
                              bid=paper.bid, ask=paper.ask, mark=paper.mark, source_sha256=paper.source_sha256)
        _require(timedelta(0) <= sampled_at - anchor.account_asof <= ACCOUNT_MAX_AGE, "HISTORY_ACCOUNT_STALE_OR_FUTURE")
        chain = evidence_digest((chain, bar))
        top_n, flags, now_prices = _chooser_parts(record)
        window = self._program.lookback_slots + 1
        prices = (prices + (now_prices,))[-window:]
        decision = inputs = choice = None
        if slot < self._window.end:
            _require(sampled_at + timedelta(seconds=self._protocol.minimum_fill_delay_seconds) <= slot + self._step,
                     "HISTORY_DECISION_TOO_LATE")
            inputs = ChooserInputs(held=state.held, hold_count=state.hold_count, top_n=top_n, flags=flags,
                                   prices=now_prices, lag_prices=prices[0] if len(prices) == window else None)
            coin, state = chooser_decision(self._program, inputs)
            fraction = self._program.exposure_fraction if coin is not None else Decimal(0)
            decision = PaperDecision(bar_index=index, decided_at=sampled_at, history_sha256=chain,
                                     target_fraction=fraction)
            choice = {"coin": coin, "target_fraction": _plain(fraction), "held": state.held,
                      "hold_count": state.hold_count}
        return bar, decision, chain, prices, state, inputs, choice
```

Replace lines 337-341 (`_frame`):

```python
    def _frame(self):
        return HistoryFrame(deployment_window_digest=self._digest, source_kind="prospective_paper_capture",
                            bars=tuple(slot.bar for slot in self._slots),
                            prior_decision=self._slots[-2].decision if len(self._slots) >= 2 else None,
                            anchor=self._slots[-1].anchor)
```

with:

```python
    def _frame(self):
        prior = len(self._slots) >= 2
        return HistoryFrame(deployment_window_digest=self._digest, source_kind="prospective_paper_capture",
                            bars=tuple(slot.bar for slot in self._slots),
                            prior_decision=self._slots[-2].decision if prior else None,
                            anchor=self._slots[-1].anchor, universe_sha256=self._slots[-1].universe_sha256,
                            chooser_inputs=self._inputs[-2] if prior and self._universe else None)
```

Replace lines 462-475 (`record_slot`):

```python
    def record_slot(self, book, account: AccountObservation) -> str:
        """Record the next slot from a prefetched original book and the current account observation; returns the
        new journal head. Memory changes only after the durable append, the head advance and its readback."""
        with _LOCK:
            self._ready()
            sampled_at = self._now()
            anchor = self._anchor(account)
            index = len(self._slots)
            bar, decision, chain, marks = self._derive(index, book, anchor, sampled_at, self._chain, self._marks)
            data = {"index": index, "receipt": _receipt_body(book.receipt), "anchor": _anchor_body(anchor)}
            head = self._append("slot", data, sampled_at)
            self._slots += (_Slot(bar=bar, anchor=anchor, decision=decision, sampled_at=sampled_at, row_sha256=head),)
            self._chain, self._marks = chain, marks
            return head
```

with:

```python
    def record_slot(self, book, account: AccountObservation, *, trade_symbol: str | None = None,
                    universe: SlotUniverse | None = None, tick_size: Decimal | None = None,
                    positions: tuple[Position, ...] = ()) -> str:
        """Record the next slot from a prefetched original book and the current account observation; returns the
        new journal head. Memory changes only after the durable append, the head advance and its readback. A
        universe window also takes the trade coin, its current tick, the slot's universe inputs and the account
        capture's positions, and `book` is that coin's book or None when it was unavailable; a fixed window takes
        none of them."""
        with _LOCK:
            self._ready()
            if self._universe:
                return self._record_universe(book, account, trade_symbol, universe, tick_size, positions)
            _require(trade_symbol is None and universe is None and tick_size is None and positions == (),
                     "HISTORY_INPUT_REQUIRED")
            sampled_at = self._now()
            anchor = self._anchor(account, self._profile.symbol)
            index = len(self._slots)
            bar, decision, chain, marks = self._derive(index, book, anchor, sampled_at, self._chain, self._marks)
            data = {"index": index, "receipt": _receipt_body(book.receipt), "anchor": _anchor_body(anchor)}
            head = self._append("slot", data, sampled_at)
            self._slots += (_Slot(bar=bar, anchor=anchor, decision=decision, sampled_at=sampled_at, row_sha256=head),)
            self._chain, self._marks = chain, marks
            return head

    def _record_universe(self, book, account, symbol, universe, tick, positions):
        """One history row v2 (spec section 12). Over the 256 KiB cap the flag and ticker parts become
        "unavailable", the allow-list empty and SIZE_FALLBACK a reason; a row is never refused for size."""
        _require(type(symbol) is str and UNIVERSE_MARKET.fullmatch(symbol) is not None
                 and type(universe) is SlotUniverse and type(tick) is Decimal and tick.is_finite() and tick > 0
                 and type(positions) is tuple and all(type(item) is Position for item in positions),
                 "HISTORY_INPUT_REQUIRED")
        sampled_at = self._now()
        anchor = self._anchor(account, symbol)
        index = len(self._slots)
        slot = self._slot_at(index, sampled_at)
        try:
            tick_text = _plain(tick)
            record = self._universe_record(slot, universe)
            holdings = sorted(self._holding(item.symbol, item.units, item.price, item.asof) for item in positions)
            _require(len({item[0] for item in holdings}) == len(holdings), "HISTORY_INPUT_REQUIRED")
        except LiveHistoryError:
            raise
        except Exception:
            raise LiveHistoryError("HISTORY_INPUT_REQUIRED") from None
        for fallback in (False, True):
            if fallback:
                record = {**record, "flags": "unavailable", "tickers": "unavailable", "allow": [],
                          "reasons": record["reasons"] + [SIZE_FALLBACK]}
            bar, decision, chain, prices, state, inputs, choice = self._derive_universe(
                index, book, anchor, sampled_at, self._chain, self._prices, self._state, symbol, tick, record)
            data = {"index": index, "trade_symbol": symbol, "tick_size": tick_text,
                    "receipt": "unavailable" if book is None else _receipt_body(book.receipt),
                    "anchor": _anchor_body(anchor), "holdings": holdings, "universe": record, "decision": choice}
            if len(_canonical(_row(self._seq + 1, self._head, "slot", data, sampled_at))) < MAX_ROW_BYTES:
                break
        head = self._append("slot", data, sampled_at)
        self._slots += (_Slot(bar=bar, anchor=anchor, decision=decision, sampled_at=sampled_at, row_sha256=head,
                              universe_sha256=evidence_digest(record)),)
        self._chain, self._prices, self._state = chain, prices, state
        self._inputs = (self._inputs + (inputs,))[-2:]
        self.recorded_allow = frozenset(record["allow"])
        return head
```

The size check builds the exact row `_append` writes (same seq, previous head, kind, data and time); `_append`
accepts a line of at most `MAX_ROW_BYTES` including its newline, hence `< MAX_ROW_BYTES` for the canonical row.

- [ ] **Step 5: Run the focused tests and the module tests**

```bash
focus launch launch_universe_history/
focus launch launch_live_history/
focus launch launch_driver/
focus launch launch_guards/
```

Expected: only `PASS` lines; each command exits 0. `launch_guards` checks that `live_history.py` still has only its
pinned writes and no `/v1/` literal.

- [ ] **Step 6: Commit**

```bash
git add execution_launch/driver.py execution_launch/live_history.py tests/launch_universe_history.py tests/launch_live_history.py
diff <(git diff --cached --stat) <(git diff --cached --stat --ignore-cr-at-eol) && echo LF-OK
"$PY" -X utf8 -c "import sys; bad = [p for p in sys.argv[1:] if b'\r' in open(p, 'rb').read()]; print(bad); sys.exit(1 if bad else 0)" execution_launch/driver.py execution_launch/live_history.py tests/launch_universe_history.py tests/launch_live_history.py
git commit -F - <<'EOF'
Record history row v2 and run the chooser for universe windows

A universe protocol now constructs the fixed driver with an IOC profile on the
benchmark symbol and the program's rule. LiveHistory takes the trade coin, its
tick, the slot's universe inputs and the account positions, writes one v2 row
per slot with the size fallback, runs the section 14 chooser incrementally and
hands the driver the prior decision's inputs (spec section 12).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

Expected: `LF-OK`, then `[]` (no staged file holds a CR byte; `git diff --stat` alone misses a file written whole
with CRLF), then one commit.

---

### Task 3: Per-tick universe checks in the driver

**Files:**
- Modify: `execution_launch/driver.py` (line numbers are fd85850's; PR 0, PR 4b and Tasks 1-2 shift them, so match
  the quoted text): insert before `:21` (import), `:247-264` (frame source and bar loop), `:265-290` (current bar,
  quote anchor and prior decision), `:302-303` (holding key), `:315-316` (other holdings)
- Test: `tests/launch_universe_history.py` (append four tests)

**Interfaces:**
- Consumes: Task 1 (`UniverseBar`, `ChooserInputs`, `chooser_decision`, frame fields), Task 2 (universe recording,
  the test helpers `ubuild`, `record`, `tick`, `substitute`, `SWITCH`, `ALL_UNFLAGGED`, `pairs`, `reads`); PR 0's
  local `profile = observation.profile` and `rules = profile.instrument_rules` in `_validate_frame`; PR 1
  `UNIVERSE_MARKET`.
- Produces: `_validate_frame` for universe frames: each bar is a `UniverseBar` checked at its own symbol and tick
  (no price check without a book); the current bar must have a book (`FIXED_DRIVER_BOOK_UNAVAILABLE`) of
  `observation.profile.symbol` at that profile's tick (`FIXED_DRIVER_QUOTE_ANCHOR_MISMATCH`); the quote anchor and the
  holding key use `observation.profile.symbol`; the prior decision is recomputed with `chooser_decision` from
  `frame.chooser_inputs`; the target is the decided fraction only when the prior decision names `profile.symbol`;
  other coins' holdings are allowed. Fixed frames refuse `universe_sha256` or `chooser_inputs`
  (`FIXED_DRIVER_HISTORY_SOURCE_INVALID`) and are otherwise checked exactly as before.

- [ ] **Step 1: Write the failing tests**

Append to the end of `tests/launch_universe_history.py`:

```python
def test_two_slot_switch_sells_the_old_coin_then_buys_the_new_one():
    with head_root() as hroot:
        env = ubuild(hroot)
        holdings = ({}, {}, {}, {BTC: D(45)}, {BTC: D(45)}, {BTC: D("0.01")})
        cash = (D(10000), D(10000), D(10000), D(5000), D(5000), D(9600))
        signals = []
        for i in range(6):
            symbol = ETH if i == 5 else BTC   # the coordinator renews to ETH once the account is flat in BTC
            record(env, i, SWITCH[i], symbol=symbol, cash=cash[i], holdings=holdings[i])
            signals.append(tick(env, i, symbol=symbol, cash=cash[i], holdings=holdings[i]))
        assert [(s.action, s.quantity, s.limit_price) for s in signals] == [
            ("hold", D(0), D(0)), ("hold", D(0), D(0)), ("entry", D("48.05"), D(105)),
            ("entry", D("1.52"), D(106)), ("exit", D(45), D(103)), ("entry", D("44.83"), D(108))]
        frame = env.h.provider(LH.obs(env, env.T(5) + LH.seconds(2)))
        assert [(bar.symbol, bar.tick_size) for bar in frame.bars] == [(BTC, D(1))] * 5 + [(ETH, D(1))]
        assert frame.chooser_inputs == ChooserInputs(held=ETH, hold_count=1, top_n=(BTC, ETH), flags=ALL_UNFLAGGED,
                                                     prices=pairs(SWITCH[4]), lag_prices=pairs(SWITCH[3]))
        assert [row["data"]["decision"]["coin"] for row in LH.rows(env)[1:]] == [None, BTC, BTC, ETH, ETH, ETH]


def test_prior_decision_is_recomputed_from_the_inputs_the_frame_carries():
    with head_root() as hroot:
        env = ubuild(hroot)
        for i in range(3):
            record(env, i, SWITCH[i])
        frame = env.h.provider(LH.obs(env, env.T(2) + LH.seconds(2)))
        carried = frame.chooser_inputs
        assert carried == ChooserInputs(held=None, hold_count=1, top_n=(BTC, ETH), flags=ALL_UNFLAGGED,
                                        prices=pairs(SWITCH[1]), lag_prices=pairs(SWITCH[0]))
        assert frame.prior_decision.target_fraction == D("0.5")
        signal = tick(env, 2)
        assert (signal.action, signal.quantity, signal.limit_price) == ("entry", D("48.05"), D(105))
        # The same frame whose carried prices make ETH the decision gives BTC a target of 0.
        swapped = replace(carried, prices=((BTC, D(105)), (ETH, D(110)), (XRP, D(200))))
        assert tick(env, 2, driver=substitute(env, replace(frame, chooser_inputs=swapped))).action == "hold"
        for changes, code in (({"chooser_inputs": replace(carried, lag_prices=None)}, "FIXED_DRIVER_TARGET_MISMATCH"),
                              ({"chooser_inputs": None}, "FIXED_DRIVER_CHOOSER_INPUTS_REQUIRED"),
                              ({"universe_sha256": None}, "FIXED_DRIVER_DIGEST_INVALID")):
            LH.refused(lambda: tick(env, 2, driver=substitute(env, replace(frame, **changes))), code)
        fixed = LD.fixture()
        base = fixed.frame
        for changes in ({"chooser_inputs": carried}, {"universe_sha256": "e" * 64}):
            fixed.frame = replace(base, **changes)
            LD.reject(lambda: LD.decide(fixed), "FIXED_DRIVER_HISTORY_SOURCE_INVALID")
        # A fixed profile still refuses another coin's holding in its own account.
        other = LD.fixture()
        key = (other.profile.venue, other.profile.account_scope)
        held = dict(other.observation.account.holdings) | {(*key, "spot", ETH): D(1)}
        other.observation = replace(other.observation, account=replace(other.observation.account, holdings=held))
        LD.reject(lambda: LD.decide(other), "FIXED_DRIVER_OTHER_INVENTORY_UNSUPPORTED")


def test_each_bar_is_checked_at_its_own_coin_and_tick_and_a_bookless_bar_never_anchors():
    with head_root() as hroot:
        env = ubuild(hroot)
        record(env, 0, SWITCH[0])
        record(env, 1, SWITCH[1], symbol=ETH, tick=D("0.5"), bid=D("100.5"), ask=D("101.5"))
        record(env, 2, SWITCH[2], booked=False)
        LH.refused(lambda: tick(env, 2), "FIXED_DRIVER_BOOK_UNAVAILABLE")
        record(env, 3, SWITCH[3])
        frame = env.h.provider(LH.obs(env, env.T(3) + LH.seconds(2)))
        assert [(bar.symbol, bar.tick_size, bar.bid) for bar in frame.bars] == [
            (BTC, D(1), D(100)), (ETH, D("0.5"), D("100.5")), (BTC, D(1), None), (BTC, D(1), D(103))]
        signal = tick(env, 3)
        assert (signal.action, signal.quantity, signal.limit_price) == ("entry", D("47.59"), D(106))
        assert tick(env, 3, driver=substitute(env, frame)) == signal
        bars = list(frame.bars)
        for index, change, code in ((1, {"tick_size": D(1)}, "FIXED_DRIVER_BAR_PRICE_INVALID"),
                                    (2, {"bid": D(102)}, "FIXED_DRIVER_BAR_REQUIRED"),
                                    (2, {"symbol": "BTC"}, "FIXED_DRIVER_BAR_REQUIRED"),
                                    (3, {"tick_size": D("0.5")}, "FIXED_DRIVER_QUOTE_ANCHOR_MISMATCH")):
            changed = replace(frame, bars=tuple(bars[:index] + [replace(bars[index], **change)] + bars[index + 1:]))
            LH.refused(lambda: tick(env, 3, driver=substitute(env, changed)), code)


def test_window_end_targets_zero_and_records_no_decision():
    with head_root() as hroot:
        env = ubuild(hroot, end=2)
        record(env, 0, SWITCH[0])
        record(env, 1, SWITCH[1])
        record(env, 2, SWITCH[2], cash=D(5000), holdings={BTC: D(45)})
        assert [row["data"]["decision"] for row in LH.rows(env)[2:]] == [
            {"coin": BTC, "target_fraction": "0.5", "held": BTC, "hold_count": 1}, None]
        signal = tick(env, 2, cash=D(5000), holdings={BTC: D(45)})
        assert (signal.action, signal.quantity, signal.limit_price) == ("exit", D(45), D(101))
        LH.refused(lambda: record(env, 3, SWITCH[3]), "HISTORY_WINDOW_COMPLETE")
```

Where the numbers come from (protocol slippage 20 bps, fee 0.001, lot 0.01, tick 1, exposure 0.5): slot 2 buys
`floor(5000 / (105 * 1.001 - 0.5 * (105 * 1.001 - 103)), 0.01) = 48.05` at `ceil(104 * 1.002) = 105`; slot 3 tops
up 1.52 at 106; slot 4 sells all 45 BTC at `floor(104 * 0.998) = 103` because the prior decision names ETH; slot 5
buys 44.83 ETH at 108 from 9,600 KRW with 0.01 BTC dust held; the per-bar test buys 47.59 at 106. In the
window-end test slot 2 is the window end, so the target is 0 although the prior decision names BTC: all 45 BTC
sell at `floor(102 * 0.998) = 101`.

- [ ] **Step 2: Run the tests to verify they fail**

```bash
focus launch launch_universe_history/test_two_slot_switch
focus launch launch_universe_history/test_prior_decision
focus launch launch_universe_history/test_each_bar
focus launch launch_universe_history/test_window_end
```

Expected (the bar loop still accepts only `PaperBar`):
`FAIL launch_universe_history/test_window_end_targets_zero_and_records_no_decision FixedDriverError: FIXED_DRIVER_BAR_REQUIRED`,
`FAIL launch_universe_history/test_two_slot_switch_sells_the_old_coin_then_buys_the_new_one FixedDriverError: FIXED_DRIVER_BAR_REQUIRED`,
`FAIL launch_universe_history/test_prior_decision_is_recomputed_from_the_inputs_the_frame_carries FixedDriverError: FIXED_DRIVER_BAR_REQUIRED`
and
`FAIL launch_universe_history/test_each_bar_is_checked_at_its_own_coin_and_tick_and_a_bookless_bar_never_anchors AssertionError: ('FIXED_DRIVER_BAR_REQUIRED', 'FIXED_DRIVER_BOOK_UNAVAILABLE')`.

- [ ] **Step 3: Write the implementation**

In `execution_launch/driver.py`, insert before line 21 (`from execution_control.capability import digest`):

```python
from core.compliance.rules import UNIVERSE_MARKET
```

Replace the block that is lines 247-264 at fd85850 (254-271 after PR 0); after PR 0 it reads:

```python
    frame_sha = history_frame_digest(frame)
    _require(frame.deployment_window_digest == identity.deployment_window_digest
             and frame.source_kind == "prospective_paper_capture", "FIXED_DRIVER_HISTORY_SOURCE_INVALID")
    step = timedelta(seconds=protocol.bar_seconds)
    rules = profile.instrument_rules
    for index, row in enumerate(frame.bars):
        _require(type(row) is PaperBar, "FIXED_DRIVER_BAR_REQUIRED")
        _instant(row.observed_at); _instant(row.received_at); _sha(row.source_sha256)
        _require(row.observed_at == window.start+index*step and row.observed_at <= window.end
                 and row.observed_at <= row.received_at <= row.observed_at+timedelta(seconds=10)
                 and row.received_at <= observation.now, "FIXED_DRIVER_HISTORY_TIME_INVALID")
        for value in (row.bid, row.ask, row.mark, row.quote_krw):
            _amount(value, positive=True)
        _require(row.quote_krw == 1 and row.bid <= row.ask
                 and Fraction(row.mark) == (Fraction(row.bid)+Fraction(row.ask))/2
                 and (Fraction(row.bid)/Fraction(rules.tick_size)).denominator == 1
                 and (Fraction(row.ask)/Fraction(rules.tick_size)).denominator == 1,
                 "FIXED_DRIVER_BAR_PRICE_INVALID")
```

with:

```python
    frame_sha = history_frame_digest(frame)
    universe = protocol.universe_rule_sha256 is not None
    _require(frame.deployment_window_digest == identity.deployment_window_digest
             and frame.source_kind == "prospective_paper_capture"
             and (universe or (frame.universe_sha256 is None and frame.chooser_inputs is None)),
             "FIXED_DRIVER_HISTORY_SOURCE_INVALID")
    if universe:
        _sha(frame.universe_sha256)
    step = timedelta(seconds=protocol.bar_seconds)
    rules = profile.instrument_rules
    for index, row in enumerate(frame.bars):
        # A universe bar carries its own coin and tick (spec section 12); one whose book was unavailable has no
        # prices to check. A fixed bar is checked exactly as before, at the profile's tick.
        _require(type(row) is (UniverseBar if universe else PaperBar), "FIXED_DRIVER_BAR_REQUIRED")
        booked = not universe or row.source_sha256 is not None
        _instant(row.observed_at); _instant(row.received_at)
        if booked:
            _sha(row.source_sha256)
        _require(row.observed_at == window.start+index*step and row.observed_at <= window.end
                 and row.observed_at <= row.received_at <= row.observed_at+timedelta(seconds=10)
                 and row.received_at <= observation.now, "FIXED_DRIVER_HISTORY_TIME_INVALID")
        if universe:
            _require(type(row.symbol) is str and UNIVERSE_MARKET.fullmatch(row.symbol) is not None
                     and (booked or (row.bid, row.ask, row.mark) == (None, None, None)),
                     "FIXED_DRIVER_BAR_REQUIRED")
            _amount(row.tick_size, positive=True)
            if not booked:
                continue
        tick = row.tick_size if universe else rules.tick_size
        for value in (row.bid, row.ask, row.mark) + (() if universe else (row.quote_krw,)):
            _amount(value, positive=True)
        _require((universe or row.quote_krw == 1) and row.bid <= row.ask
                 and Fraction(row.mark) == (Fraction(row.bid)+Fraction(row.ask))/2
                 and (Fraction(row.bid)/Fraction(tick)).denominator == 1
                 and (Fraction(row.ask)/Fraction(tick)).denominator == 1,
                 "FIXED_DRIVER_BAR_PRICE_INVALID")
```

Replace the block that is lines 265-290 at fd85850 (272-297 after PR 0):

```python
    current = frame.bars[-1]
    _require(current.observed_at <= observation.now <= current.observed_at+timedelta(seconds=10),
             "FIXED_DRIVER_EXECUTION_SLOT_EXPIRED")
    quote = observation.quote
    _instant(quote.asof)
    _amount(quote.bid, positive=True); _amount(quote.ask, positive=True)
    _require((quote.venue, quote.market, quote.symbol) == (protocol.venue, protocol.market, protocol.symbol)
             and (quote.bid, quote.ask, quote.source_sha256) == (current.bid, current.ask, current.source_sha256)
             and timedelta(0) <= current.observed_at-quote.asof <= timedelta(seconds=10)
             and timedelta(0) <= observation.now-quote.asof <= timedelta(seconds=10),
             "FIXED_DRIVER_QUOTE_ANCHOR_MISMATCH")
    if len(frame.bars) == 1:
        _require(frame.prior_decision is None, "FIXED_DRIVER_INITIAL_DECISION_INVALID")
        target = Decimal(0)
    else:
        prior = frame.prior_decision
        _require(type(prior) is PaperDecision and type(prior.bar_index) is int
                 and prior.bar_index == len(frame.bars)-2, "FIXED_DRIVER_PRIOR_DECISION_REQUIRED")
        _instant(prior.decided_at); _sha(prior.history_sha256); _amount(prior.target_fraction)
        _require(prior.history_sha256 == history_digest(frame.bars[:-1])
                 and frame.bars[-2].received_at <= prior.decided_at
                 and prior.decided_at+timedelta(seconds=protocol.minimum_fill_delay_seconds)
                 <= current.observed_at, "FIXED_DRIVER_DECISION_LOOKAHEAD_OR_CHANGED")
        expected = target_fraction(callback.program, tuple(row.mark for row in frame.bars[:-1]))
        _require(prior.target_fraction == expected, "FIXED_DRIVER_TARGET_MISMATCH")
        target = Decimal(0) if current.observed_at == window.end else expected
```

with:

```python
    current = frame.bars[-1]
    _require(current.observed_at <= observation.now <= current.observed_at+timedelta(seconds=10),
             "FIXED_DRIVER_EXECUTION_SLOT_EXPIRED")
    if universe:
        # Only a booked bar of the current trade coin at its current tick anchors the quote and sizes the order.
        _require(current.source_sha256 is not None, "FIXED_DRIVER_BOOK_UNAVAILABLE")
        _require((current.symbol, current.tick_size) == (profile.symbol, rules.tick_size),
                 "FIXED_DRIVER_QUOTE_ANCHOR_MISMATCH")
    quote = observation.quote
    _instant(quote.asof)
    _amount(quote.bid, positive=True); _amount(quote.ask, positive=True)
    _require((quote.venue, quote.market, quote.symbol) == (protocol.venue, protocol.market, profile.symbol)
             and (quote.bid, quote.ask, quote.source_sha256) == (current.bid, current.ask, current.source_sha256)
             and timedelta(0) <= current.observed_at-quote.asof <= timedelta(seconds=10)
             and timedelta(0) <= observation.now-quote.asof <= timedelta(seconds=10),
             "FIXED_DRIVER_QUOTE_ANCHOR_MISMATCH")
    if len(frame.bars) == 1:
        _require(frame.prior_decision is None and frame.chooser_inputs is None,
                 "FIXED_DRIVER_INITIAL_DECISION_INVALID")
        target = Decimal(0)
    else:
        prior = frame.prior_decision
        _require(type(prior) is PaperDecision and type(prior.bar_index) is int
                 and prior.bar_index == len(frame.bars)-2, "FIXED_DRIVER_PRIOR_DECISION_REQUIRED")
        _instant(prior.decided_at); _sha(prior.history_sha256); _amount(prior.target_fraction)
        _require(prior.history_sha256 == history_digest(frame.bars[:-1])
                 and frame.bars[-2].received_at <= prior.decided_at
                 and prior.decided_at+timedelta(seconds=protocol.minimum_fill_delay_seconds)
                 <= current.observed_at, "FIXED_DRIVER_DECISION_LOOKAHEAD_OR_CHANGED")
        if universe:
            # Recompute only the prior decision, from the inputs the frame carries (spec section 12).
            coin, _ = chooser_decision(callback.program, frame.chooser_inputs)
            expected = callback.program.exposure_fraction if coin is not None else Decimal(0)
        else:
            coin, expected = None, target_fraction(callback.program, tuple(row.mark for row in frame.bars[:-1]))
        _require(prior.target_fraction == expected, "FIXED_DRIVER_TARGET_MISMATCH")
        # The decided fraction is the target only for the coin the decision names; at the window end it is 0.
        target = (Decimal(0) if current.observed_at == window.end or (universe and coin != profile.symbol)
                  else expected)
```

For a fixed profile `profile.symbol == protocol.symbol` (the fixed contract digest pins the symbol), so the quote
anchor and the holding key below compare the same values as before.

Replace lines 302-303:

```python
    key = (protocol.venue, callback.profile.account_scope)
    holding_key = (*key, protocol.market, protocol.symbol)
```

with:

```python
    key = (protocol.venue, callback.profile.account_scope)
    holding_key = (*key, protocol.market, profile.symbol)
```

Replace lines 315-316:

```python
        _require(held_key[:2] != key or held_key == holding_key or units == 0,
                 "FIXED_DRIVER_OTHER_INVENTORY_UNSUPPORTED")
```

with:

```python
        # A universe driver trades only the profile's coin; other holdings are the coordinator's (spec section 12).
        _require(universe or held_key[:2] != key or held_key == holding_key or units == 0,
                 "FIXED_DRIVER_OTHER_INVENTORY_UNSUPPORTED")
```

- [ ] **Step 4: Run the focused tests and the module tests**

```bash
focus launch launch_universe_history/
focus launch launch_driver/
focus launch launch_live_history/
```

Expected: only `PASS` lines; each command exits 0. `launch_driver` still refuses another coin's holding for a fixed
profile (`FIXED_DRIVER_OTHER_INVENTORY_UNSUPPORTED`).

- [ ] **Step 5: Commit**

```bash
git add execution_launch/driver.py tests/launch_universe_history.py
diff <(git diff --cached --stat) <(git diff --cached --stat --ignore-cr-at-eol) && echo LF-OK
"$PY" -X utf8 -c "import sys; bad = [p for p in sys.argv[1:] if b'\r' in open(p, 'rb').read()]; print(bad); sys.exit(1 if bad else 0)" execution_launch/driver.py tests/launch_universe_history.py
git commit -F - <<'EOF'
Check universe frames per bar and recompute the prior decision from its inputs

Each universe bar is checked at its own coin and tick, a bar without a book has
no price check and never anchors the quote, the quote anchor and holding key use
the observed profile's coin, other coins' holdings are allowed, and the prior
decision is recomputed from the chooser inputs the frame carries; its fraction
is the target only for the coin it names (spec section 12).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

Expected: `LF-OK`, then `[]` (no staged file holds a CR byte; `git diff --stat` alone misses a file written whole
with CRLF), then one commit.

---

### Task 4: Replay of history row v2

**Files:**
- Modify: `execution_launch/live_history.py` (line numbers are fd85850's; Task 2 shifts them, so match the quoted
  text): insert after the `_START` line added in Task 2 (constants), insert after `_chooser_parts` (Task 2)
  (`_parse_record`), insert after `_holding` (Task 2) (`_parse_holdings`), `:383` (replay locals), `:405-412`
  (slot-row branch), `:424` (replay result)
- Test: `tests/launch_universe_history.py` (append two tests)

**Interfaces:**
- Consumes: Task 2 (`_derive_universe`, `_holding`, `_sha256`, `_markets`, `_price_text`, `_chooser_parts`,
  `_EXCEPTION_CLASSES`, `PRICE_WINDOW_MS`, `_START`, the row v2 shape, `recorded_allow`); `chooser_decision`
  imported in `live_history.py` (the test patches `execution_launch.live_history.chooser_decision`).
- Produces: `LiveHistory._replay` accepts v2 rows for a universe window only (fixed windows still accept only
  `{"index", "receipt", "anchor"}`), checks each row's book against the row's own trade coin, derives the bar and the
  decision again and refuses `HISTORY_STORE_RECORD_INVALID` unless the derived decision equals the stored one, and
  restores `_prices`, `_state`, `_inputs` and `recorded_allow`. New module names `_SLOT_V2_KEYS`, `_RECORD_KEYS`,
  `_parse_record(value) -> dict`; new method `LiveHistory._parse_holdings(value) -> None`.

- [ ] **Step 1: Write the failing tests**

Append to the end of `tests/launch_universe_history.py`:

```python
def test_restart_replays_v2_rows_and_restores_the_chooser_state():
    with head_root() as hroot:
        env = ubuild(hroot)
        held = (Position(market="spot", symbol=BTC, base_currency="BTC", quote_currency="KRW", units=D(45),
                         price=D(104), asof=env.T(3) - LH.seconds(3)),)
        holdings = ({}, {}, {}, {BTC: D(45)}, {BTC: D(45)})
        cash = (D(10000), D(10000), D(10000), D(5000), D(5000))
        for i in range(5):
            record(env, i, SWITCH[i], booked=i != 1, cash=cash[i], holdings=holdings[i],
                   positions=held if i == 3 else (),
                   slot_universe=reads(env, 2, SWITCH[2], flags={XRP: "caution"}) if i == 2 else None)
        frame = env.h.provider(LH.obs(env, env.T(4) + LH.seconds(2)))
        signal = tick(env, 4, cash=D(5000), holdings={BTC: D(45)})
        assert (signal.action, signal.quantity, signal.limit_price) == ("exit", D(45), D(103))
        LH.restart(env)
        assert env.h.provider(LH.obs(env, env.T(4) + LH.seconds(2))) == frame
        assert env.h.recorded_allow == frozenset({BTC, ETH})
        assert tick(env, 4, cash=D(5000), holdings={BTC: D(45)}) == signal
        # The next decisions read the restored state (ETH held for two decisions) and price vectors: BTC jumps, so
        # slot 5 switches to BTC, and slot 6, flat over one slot, goes to cash.
        jump = {BTC: D(150), ETH: D(120), XRP: D(200)}
        record(env, 5, jump)
        record(env, 6, jump)
        assert [row["data"]["decision"]["coin"] for row in LH.rows(env)[1:]] == [None, BTC, BTC, ETH, ETH, BTC, None]
        later = env.h.provider(LH.obs(env, env.T(6) + LH.seconds(2)))
        assert later.chooser_inputs == ChooserInputs(held=ETH, hold_count=2, top_n=(BTC, ETH), flags=ALL_UNFLAGGED,
                                                     prices=pairs(jump), lag_prices=pairs(SWITCH[4]))
        with patch("execution_launch.live_history.chooser_decision",
                   return_value=(XRP, ChooserState(held=XRP, hold_count=1))):
            LH.refused(lambda: LH.restart(env), "HISTORY_STORE_RECORD_INVALID")
        LH.restart(env)
        assert env.h.provider(LH.obs(env, env.T(6) + LH.seconds(2))) == later
        # A slot missed across a restart is never backfilled: slot 7 recorded at slot 8 + 1 s refuses, and the
        # window has no later row (the coordinator's status field for it is PR 4e).
        LH.refused(lambda: record(env, 8, jump), "HISTORY_SLOT_MISSED")
        assert len(LH.rows(env)) == 8


def test_restart_replays_every_row_v2_variant():
    """Replay of a coin on another tick, unlisted and dust holdings, a bookless slot with a flag exception and a
    slot whose universe reads all failed."""
    with head_root() as hroot:
        env = ubuild(hroot)
        stamp = env.T(1) - LH.seconds(3)
        positions = (Position(market="spot", symbol=ETH, base_currency="ETH", quote_currency="KRW", units=D(2),
                              price=D(105), asof=stamp),
                     Position(market="spot", symbol="KRW-OLD", base_currency="OLD", quote_currency="KRW",
                              units=D(7), price=D(0), asof=stamp, unlisted=True))
        record(env, 0, SWITCH[0])
        record(env, 1, SWITCH[1], symbol=ETH, tick=D("0.5"), bid=D("100.5"), ask=D("101.5"), holdings={ETH: D(2)},
               positions=positions)
        record(env, 2, SWITCH[2], booked=False, slot_universe=reads(env, 2, SWITCH[2], flags={XRP: "caution"}))
        record(env, 3, SWITCH[3], slot_universe=down(env, 3))
        frame = env.h.provider(LH.obs(env, env.T(3) + LH.seconds(2)))
        LH.restart(env)
        assert env.h.provider(LH.obs(env, env.T(3) + LH.seconds(2))) == frame
        assert env.h.recorded_allow == frozenset()
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
focus launch launch_universe_history/test_restart_replays
```

Expected: `FAIL launch_universe_history/test_restart_replays_v2_rows_and_restores_the_chooser_state LiveHistoryError: HISTORY_STORE_RECORD_INVALID`
and `FAIL launch_universe_history/test_restart_replays_every_row_v2_variant LiveHistoryError: HISTORY_STORE_RECORD_INVALID`
(the replay still accepts only fixed slot rows).

- [ ] **Step 3: Write the implementation**

In `execution_launch/live_history.py`, insert after the line added in Task 2:

```python
_START = ChooserState(held=None, hold_count=0)           # a window's chooser starts in cash (PR 4b)
```

these lines:

```python
_SLOT_V2_KEYS = frozenset({"index", "trade_symbol", "tick_size", "receipt", "anchor", "holdings", "universe",
                           "decision"})
_RECORD_KEYS = frozenset({"snapshot", "flags", "tickers", "allow", "reasons", "events"})
```

Insert after `_chooser_parts` (Task 2), with two blank lines on each side:

```python
def _parse_record(value):
    """A stored universe record, checked for shape and canonical text; the chooser reads it exactly as stored."""
    _require(type(value) is dict and set(value) == _RECORD_KEYS, "HISTORY_STORE_RECORD_INVALID")
    snapshot, flags, tickers = value["snapshot"], value["flags"], value["tickers"]
    _require(snapshot == "unavailable"
             or (type(snapshot) is dict and set(snapshot) == {"day", "sha256", "top_n"}
                 and type(snapshot["day"]) is str and _sha256(snapshot["sha256"]) and _markets(snapshot["top_n"])),
             "HISTORY_STORE_RECORD_INVALID")
    _require(flags == "unavailable"
             or (type(flags) is dict and set(flags) == {"sha256", "exceptions"} and _sha256(flags["sha256"])
                 and type(flags["exceptions"]) is list
                 and all(type(item) is list and len(item) == 2 and item[1] in _EXCEPTION_CLASSES
                         for item in flags["exceptions"])
                 and _markets([item[0] for item in flags["exceptions"]])
                 and flags["exceptions"] == sorted(flags["exceptions"])),
             "HISTORY_STORE_RECORD_INVALID")
    _require(tickers == "unavailable"
             or (flags != "unavailable" and type(tickers) is dict and set(tickers) == {"sha256", "prices"}
                 and _sha256(tickers["sha256"]) and type(tickers["prices"]) is list
                 and all(type(item) is list and len(item) == 3 and type(item[1]) is str
                         and _price_text(_decimal(item[1])) == item[1]
                         and type(item[2]) is int and abs(item[2]) <= PRICE_WINDOW_MS for item in tickers["prices"])
                 and _markets([item[0] for item in tickers["prices"]])),
             "HISTORY_STORE_RECORD_INVALID")
    _require(_markets(value["allow"]) and value["allow"] == sorted(value["allow"])
             and all(type(value[key]) is list and all(type(item) is str for item in value[key])
                     for key in ("reasons", "events")), "HISTORY_STORE_RECORD_INVALID")
    return value
```

Insert after the `_holding` method (Task 2), with one blank line before it:

```python
    def _parse_holdings(self, value):
        """Stored holdings must be exactly what _holding writes for their own values."""
        _require(type(value) is list and all(type(row) is list and len(row) == 6 and _valid_stamp(row[3])
                                             for row in value), "HISTORY_STORE_RECORD_INVALID")
        parsed = sorted(self._holding(row[0], _decimal(row[1]), _decimal(row[2]), datetime.fromisoformat(row[3]))
                        for row in value)
        _require(parsed == value and len({row[0] for row in value}) == len(value), "HISTORY_STORE_RECORD_INVALID")
```

In `_replay`, replace line 383:

```python
            slots, chain, marks, previous, size, seq = [], "", (), GENESIS, 0, 0
```

with:

```python
            slots, chain, marks, previous, size, seq = [], "", (), GENESIS, 0, 0
            prices, state, recent, allow = (), _START, (), None
```

Replace lines 405-412:

```python
                        else:
                            _require(set(data) == {"index", "receipt", "anchor"} and type(data["index"]) is int
                                     and data["index"] == seq - 2, "HISTORY_STORE_RECORD_INVALID")
                            receipt, anchor = _parse_receipt(data["receipt"]), _parse_anchor(data["anchor"])
                            book = parse_orderbook(receipt, symbol=self._protocol.symbol, now=at)
                            bar, decision, chain, marks = self._derive(seq - 2, book, anchor, at, chain, marks)
                            slots.append(_Slot(bar=bar, anchor=anchor, decision=decision, sampled_at=at,
                                               row_sha256=row["row_sha256"]))
```

with:

```python
                        elif self._universe:
                            # History row v2: the row's own trade coin and tick and its book or none; the decision
                            # derived again from the stored record must equal the stored one (spec section 12).
                            _require(set(data) == _SLOT_V2_KEYS and type(data["index"]) is int
                                     and data["index"] == seq - 2 and type(data["trade_symbol"]) is str
                                     and UNIVERSE_MARKET.fullmatch(data["trade_symbol"]) is not None,
                                     "HISTORY_STORE_RECORD_INVALID")
                            symbol, tick = data["trade_symbol"], _decimal(data["tick_size"])
                            _require(tick > 0 and _plain(tick) == data["tick_size"], "HISTORY_STORE_RECORD_INVALID")
                            anchor, record = _parse_anchor(data["anchor"]), _parse_record(data["universe"])
                            self._parse_holdings(data["holdings"])
                            book = None if data["receipt"] == "unavailable" else parse_orderbook(
                                _parse_receipt(data["receipt"]), symbol=symbol, now=at)
                            bar, decision, chain, prices, state, inputs, choice = self._derive_universe(
                                seq - 2, book, anchor, at, chain, prices, state, symbol, tick, record)
                            _require(choice == data["decision"], "HISTORY_STORE_RECORD_INVALID")
                            slots.append(_Slot(bar=bar, anchor=anchor, decision=decision, sampled_at=at,
                                               row_sha256=row["row_sha256"], universe_sha256=evidence_digest(record)))
                            recent, allow = (recent + (inputs,))[-2:], frozenset(record["allow"])
                        else:
                            _require(set(data) == {"index", "receipt", "anchor"} and type(data["index"]) is int
                                     and data["index"] == seq - 2, "HISTORY_STORE_RECORD_INVALID")
                            receipt, anchor = _parse_receipt(data["receipt"]), _parse_anchor(data["anchor"])
                            book = parse_orderbook(receipt, symbol=self._protocol.symbol, now=at)
                            bar, decision, chain, marks = self._derive(seq - 2, book, anchor, at, chain, marks)
                            slots.append(_Slot(bar=bar, anchor=anchor, decision=decision, sampled_at=at,
                                               row_sha256=row["row_sha256"]))
```

Replace line 424:

```python
            self._slots, self._chain, self._marks = tuple(slots), chain, marks
```

with:

```python
            self._slots, self._chain, self._marks = tuple(slots), chain, marks
            self._prices, self._state, self._inputs, self.recorded_allow = prices, state, recent, allow
```

Every exception inside the replay loop other than `HISTORY_IDENTITY_CHANGED` already becomes
`HISTORY_STORE_RECORD_INVALID` (`live_history.py:415-422`), including a `FixedDriverError` from `chooser_decision`
and a refusal from `_holding`.

- [ ] **Step 4: Run the focused test and the module tests**

```bash
focus launch launch_universe_history/
focus launch launch_live_history/
focus launch launch_driver/
focus launch launch_guards/
```

Expected: only `PASS` lines; each command exits 0.

- [ ] **Step 5: Commit**

```bash
git add execution_launch/live_history.py tests/launch_universe_history.py
diff <(git diff --cached --stat) <(git diff --cached --stat --ignore-cr-at-eol) && echo LF-OK
"$PY" -X utf8 -c "import sys; bad = [p for p in sys.argv[1:] if b'\r' in open(p, 'rb').read()]; print(bad); sys.exit(1 if bad else 0)" execution_launch/live_history.py tests/launch_universe_history.py
git commit -F - <<'EOF'
Replay history row v2 and restore the chooser state on restart

A universe window's replay checks each v2 row's shape and canonical text and
its book against the row's own trade coin, derives the bar and the decision
again from the stored record, refuses unless the decision equals the stored
one, and restores the price vectors, h, the hold count, the prior inputs and
the recorded allow-list (spec section 12).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

Expected: `LF-OK`, then `[]` (no staged file holds a CR byte; `git diff --stat` alone misses a file written whole
with CRLF), then one commit.

---

### Task 5: Guards, full suite and the pull request

**Files:**
- No file changes. Reads the four commits of Tasks 1-4.

**Interfaces:**
- Consumes: the commits of Tasks 1-4.
- Produces: branch `claude/universe-pr4d-driver-history` pushed to `origin` and one open pull request against
  `main`. The owner merges it; PR 4e is cut from `main` after that merge (and after PR 4a).

- [ ] **Step 1: Run the guard modules**

```bash
focus compliance compliance_guards/
focus control control_guards/
focus accounts accounts_guards/
focus launch launch_guards/
focus execution execution_guards/
```

Expected: only `PASS` lines, each command exits 0. `control_guards` runs the `tests/renewal_boundaries.py` checks;
neither `driver.py` nor `live_history.py` is in their pins. If a guard fails, stop and report; never regenerate a
pin.

- [ ] **Step 2: Run the full suite**

```bash
"$PY" -X utf8 -m tests.run_all
git restore qa/acceptance_results.json
```

Expected: the last line reads `<n>/<m> passed, <f> failed, <k> not run; ...qa/acceptance_results.json`, and no
failing test is one that passes on `origin/main` (the suite at fd85850 may already have failures of its own). The
run rewrites the tracked `qa/acceptance_results.json`; the `git restore` keeps it out of this PR. For each `FAIL`
line, run that test with `focus` in a separate worktree of `origin/main`, then remove the worktree:

```bash
git worktree add ../tgu-main origin/main
(cd ../tgu-main && focus <suite> <module>/<name>)
git worktree remove ../tgu-main
```

A test that fails there too is pre-existing: list it in the PR body under "Not verified" and do not fix it here. A
test that fails only on this branch is a defect of this PR: fix it in a new task before opening the PR. A failure
`FIXED_DRIVER_REGISTRY_LIMIT` means the suite issued 1024 fixed drivers in one process (`driver.py:412`; the
registry is never cleared between tests): report it rather than raising the limit.

- [ ] **Step 3: Check the branch**

```bash
git status --short
git log --oneline origin/main..HEAD
diff <(git diff --stat origin/main..HEAD) <(git diff --stat --ignore-cr-at-eol origin/main..HEAD) && echo LF-OK
git diff --stat origin/main..HEAD
```

Expected: no tracked change pending (untracked spec and plan documents may show as `??`); four commits; `LF-OK`;
exactly `execution_launch/driver.py`, `execution_launch/live_history.py`, `tests/launch_acceptance.py`,
`tests/launch_live_history.py` and `tests/launch_universe_history.py` changed.

- [ ] **Step 4: Push and open the pull request**

```bash
git push -u origin claude/universe-pr4d-driver-history
gh pr create --repo xkg4real/tradegen --base main --head claude/universe-pr4d-driver-history \
  --title "Universe driver, history row v2 and the chooser in LiveHistory" --body-file - <<'EOF'
## Summary

- The fixed driver accepts a universe protocol: its symbol stays the benchmark `KRW-BTC`, the launch profile starts
  with it and trades with IOC orders, and profile, program and protocol carry the same signed rule. A fixed protocol
  keeps `gtc`.
- Per tick, a universe frame's bars (`UniverseBar`) are checked at their own coin and tick; a bar without a book has
  no price check and never anchors the quote (`FIXED_DRIVER_BOOK_UNAVAILABLE`). The quote anchor and the holding key
  use the observed profile's coin, other coins' holdings are allowed, and the prior decision is recomputed from the
  chooser inputs the frame carries. Its fraction is the target only for the coin it names, so a switch sells at one
  slot and buys at the next.
- `LiveHistory.record_slot` takes the trade coin, its tick, the slot's `SlotUniverse` and the account positions,
  and writes history row v2: anchor and per-holding marks (unlisted, dust), the book receipt or `unavailable`, the
  snapshot in force, flag exceptions and defined ticker prices with raw-body sha256s, allow-list, reasons, events and
  the chooser's decision and state. Over the 256 KiB cap the flag and ticker parts become `unavailable` and nothing
  is allowed (`HISTORY_ROW_SIZE_FALLBACK`); `recorded_allow` exposes what was recorded.
- The section 14 chooser runs in LiveHistory at recording and at replay, over the last L+1 price vectors, h and the
  hold count; replay refuses unless each derived decision equals the stored one.
- Fixed windows are unchanged: frames and rows keep their fd85850 digests (golden test).

Spec: `docs/superpowers/specs/2026-11-11-upbit-krw-universe-design.md`, section 12 (universe driver, history row
v2, LiveHistory follows the trade coin, the chooser in LiveHistory, raw bodies), section 14 (price rule and
encoding), section 19 (driver and history tests). Plan:
`docs/superpowers/plans/2026-11-11-upbit-krw-universe-pr4d-driver-history.md`.

## Tests added

- `tests/launch_universe_history.py` (new, in `MODULES`): chooser decision from carried inputs; construction rule;
  required universe inputs, book coin and tick at recording; history row v2 contents and frames; the row size
  fallback; the two-slot switch; the prior-decision check from carried inputs, and a fixed profile still refusing
  another coin's holding; per-bar tick checks and the bookless bar; the window end (target 0, no decision, no
  later slot); restart replay restoring the chooser state, and a missed slot never recorded after it; replay of
  every row v2 variant (another coin on another tick, unlisted and dust holdings, a bookless slot with a flag
  exception, a slot with every universe read unavailable).
- `tests/launch_live_history.py`: fixed-window frame and rows byte-identical to fd85850; a fixed window refuses the
  universe keywords.

Guards (`compliance_guards`, `control_guards` with the renewal boundaries, `accounts_guards`, `launch_guards`,
`execution_guards`) pass. The full suite has no failure that does not also fail on `origin/main`; each failure it
shares with `origin/main` is listed under "Not verified".

## Effect on deployments

- `execution_launch/driver.py` is part of the fixed driver identity and of the compliance code hash. After merge:
  code-approve on the merged head, a new strategy review for the new identity, and a new history window. A journal
  bound under the old identity refuses `HISTORY_IDENTITY_CHANGED` at restart, before any tick.
- Unchanged: fixed frames, rows, profile, contract, rule-terms and protocol digests.

## Not verified

- The coordinator still calls `record_slot(book, observation)`; a universe LiveHistory refuses that
  (`HISTORY_INPUT_REQUIRED`) until PR 4e passes the trade coin, tick, universe inputs and positions and uses
  `recorded_allow` as the runner's `entry_allow`. No universe window can run before PR 4e.
- The missed-slot status field and the 72-hour bound are coordinator work (PR 4e). The section 17 measurement of
  `record_slot` plus the tick at the last slot of a 72-hour window is not done.
- No rehearsal and no run on the owner's PC.

This is software design, not legal, tax or investment advice.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
```

Expected: `gh` prints the pull request URL. Do not merge; the owner merges on GitHub.
