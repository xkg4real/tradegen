# Upbit KRW universe PR 0: Driver pin for fixed profiles Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Keep a fixed KRW-BTC driver ticking after a same-terms instrument-rules renewal by pinning the contract
digest and scope of the runner's current profile instead of its full digest, and by reading each tick's rules from
that profile.

**Architecture:** `Runner.refresh_instrument_rules` swaps in each renewed profile (`execution_launch/runner.py:307`)
and passes it to the driver as `DecisionInput.profile`. The driver today compares that profile's full
`profile_digest`, which includes `instrument_rules.asof`, with the digest taken at construction
(`execution_launch/driver.py:244`), so the first renewal makes the next tick refuse `FIXED_DRIVER_PROFILE_CHANGED`
and the runner's catch-all stops it for good outside observe mode (`runner.py:459-463`). This PR changes only
`_validate_frame` and
`_FixedCallback.__call__` in `driver.py`: pin `profile_contract_digest` (every field except `asof`) plus venue, market
and account scope, then read the rules for the bar tick check, sizing and order validation from the current profile.
No digest function, dataclass, protocol or profile encoding changes.

**Tech Stack:** Python 3.13 (venv at `TRADEGEN_PR9/.venv`, read-only), stdlib only. Tests use the repo's suite
runner (no pytest) through the index's `focus` function.

**Spec:** [2026-11-11-upbit-krw-universe-design.md](../specs/2026-11-11-upbit-krw-universe-design.md), section 12
(first bullet) and section 19 (item 0).

## Global Constraints

All constraints in the index apply: [2026-11-11-upbit-krw-universe-index.md](2026-11-11-upbit-krw-universe-index.md)
(Global constraints, Running tests, Task conventions).

Constraints specific to this PR, verbatim from the spec and the index:

- Spec section 12: "**Driver pin (first PR, fixed-symbol profiles too).** `driver.py:244` compares
  `profile_contract_digest(observation.profile)` with `callback.identity.profile_contract_digest` instead of the full
  `profile_digest`. It also requires `observation.profile` to match the protocol's venue and market and
  `callback.profile`'s account scope. The tick check (`driver.py:251`, `262-263`), `_sized_signal` (`380`) and
  `validate_order` (`384-388`) read the rules and symbol from `observation.profile`. `callback.profile` stays for the
  account scope (`302`) and the identity rebuild (`435-439`). The chain itself stays checked in the runner
  (`runner.py:298`, `304-305`, `367-368`) and through `validate_observed_order` (`runner.py:356`)."
- Spec section 19: "0. **Driver pin** (section 12, first bullet), for fixed profiles too. It is the separate
  driver-renewal task; it lands first, with a test of a fixed KRW-BTC tick after a same-terms renewal."
- Spec section 12: "The driver identity hashes `driver.py`, `program.py`, `strategy.py`, `runner.py`, `profile.py`
  and three `execution_control` files, including `controller.py`. These changes make a new identity, so a new history
  window (GENESIS), a new protocol and a new review are needed. Any in-flight KRW-BTC study or window finishes first."
- Index: "If the separate driver-renewal session lands the driver pin first, PR 0 is skipped and PR 4b rebases on it."
- Index: "Fixed-symbol (KRW-BTC) profiles, protocols, programs and sessions keep today's digests byte for byte."

## Running tests

Run every command in this plan from the repository root, in Git Bash. Every task that runs a test first defines these
in its shell, copied from the index's "Running tests" section (a fresh shell for a later task defines them again):

```bash
PY="$HOME/OneDrive/Desktop/TRADEGEN_PR9/.venv/Scripts/python.exe"
export TRADEGEN_RUNS_DIR="${SCRATCH:?set SCRATCH to your session scratchpad directory}/runs_scratch"
focus() { "$PY" -X utf8 -c "import importlib,sys; from tests.run_all import run; s=importlib.import_module('tests.'+sys.argv[1]+'_acceptance'); rows=run([(n,f) for n,f in s.tests() if sys.argv[2] in n]); sys.exit(0 if rows and not any(r['status']=='FAIL' for r in rows) else 1)" "$@"; }
```

`focus <suite> <module>/<test_name>` runs every test whose name contains the second argument and prints one
`PASS <name>` or `FAIL <name> <ExceptionType>: <message>` line per test. It does not write
`qa/acceptance_results.json`; only the full suite (`"$PY" -X utf8 -m tests.run_all`) does.

## Identity change and existing windows

- `_SOURCE_FILES` (`driver.py:35-38`) hashes `driver.py` into `FixedDriverIdentity.deployment_code_sha256`
  (`driver.py:116`, `140`, `173`). Any edit to `driver.py` gives a new identity.
- A live-history journal stores the identity in its first row (`execution_launch/live_history.py:456`). A restart
  with the new code replays that row and refuses `HISTORY_IDENTITY_CHANGED` (`live_history.py:404`, re-raised at
  `416`). `bind` refuses before any tick, so nothing is sent, but that window cannot be resumed. Any running window
  finishes on the old code first; a coin still held is exited with `Coordinator.submit_exit` on the old code or in
  the Upbit app.
- A new window is needed after merge: a new `DeploymentWindow` (a new window digest, so a new
  `execution-history/<digest>/` directory), a head initialized at GENESIS by the operator, and `LiveHistory.bind`
  before the window starts (`live_history.py:454-456`).
- The signed strategy review binds the identity (`execution_launch/review_auth.py:36`, `tools/signer/sign.py:1368`,
  `1391`), so the owner signs a new review for the new identity.
- `driver.py` is inside the compliance code hash (`core/compliance/owner.py:798`), so code-approve runs on the merged
  head. Both are owner acts.
- Unchanged by this PR: `profile_digest`, `profile_contract_digest`, `rule_terms_digest`, the protocol digest and
  `capture_source_code_sha256` (`CAPTURE_FILES`, `execution_launch/study.py:59-61`, does not list `driver.py`). A
  frozen or in-flight study capture stays valid. The "new protocol" in spec section 12 comes from PRs 4b to 4d.

## File Structure

- Modify `execution_launch/driver.py`: the fixed driver adapter. `_validate_frame` pins the current profile's
  contract digest and scope and reads its rules; `_FixedCallback.__call__` sizes and validates the order with them.
- Modify `tests/launch_driver.py`: the driver's offline tests. It is already in `MODULES`
  (`tests/launch_acceptance.py:11`), so no suite file changes.

No file is created. No doc names `FIXED_DRIVER_PROFILE_CHANGED` (only the spec does), so no doc changes. The spec,
index and plan files are not committed by this plan.

---

### Task 1: Pin the current profile's contract digest and scope

**Files:**
- Modify: `execution_launch/driver.py:244-246`
- Test: `tests/launch_driver.py:17` (import) and new tests appended after `tests/launch_driver.py:273`

**Interfaces:**
- Consumes (existing at fd85850):
  - `profile_contract_digest(profile: LaunchProfile) -> str` (`execution_launch/profile.py:299-310`) and
    `profile_digest(profile: LaunchProfile) -> str` (`profile.py:277-279`).
  - `FixedDriverIdentity.profile_contract_digest: str` (`driver.py:118`); `_FixedCallback.protocol: ForwardProtocol`,
    `_FixedCallback.profile: LaunchProfile`, `_FixedCallback.identity: FixedDriverIdentity` (`driver.py:333-343`).
  - `DecisionInput.profile: LaunchProfile` (`execution_launch/runner.py:78-82`).
  - Test helpers in `tests/launch_driver.py`: `D = Decimal`, `reject(call, code=None)`,
    `fixture(index=4, *, cash=D(10000), units=D(0), kind="moving_average_trend")` returning a `SimpleNamespace` with
    `program, protocol, profile, window, bars, artifact, frame, observation, provider, verifier, driver`,
    `next_frame(env, index, *, cash=D(10000), units=D(0))`, `decide(env, driver=None) -> Signal`.
- Produces:
  - `_validate_frame(callback, frame, observation) -> tuple[str, Decimal]`, signature unchanged. It refuses
    `FIXED_DRIVER_SCOPE_MISMATCH` when `observation.profile` is not a `LaunchProfile` or its
    `(venue, market, account_scope)` differs from `(protocol.venue, protocol.market, callback.profile.account_scope)`,
    and `FIXED_DRIVER_PROFILE_CHANGED` when `profile_contract_digest(observation.profile)` differs from
    `callback.identity.profile_contract_digest`. Both codes already exist (`driver.py:165`, `245`); no new name.
  - A local `profile = observation.profile` in `_validate_frame`, used by Task 2.
  - PR 4b relies on this pin: its universe contract digest leaves out the coin, so a renewal to another coin passes.

- [ ] **Step 1: Cut the branch and confirm the bug is still on main**

```bash
git fetch origin
git switch -c claude/universe-pr0-driver-pin origin/main
git log -1 --format=%h origin/main
git show origin/main:execution_launch/driver.py | sed -n 244,246p
```

Expected: `fd85850` (if `main` moved, re-check every line range cited in this plan before editing), then exactly:

```
    _require(profile_digest(observation.profile) == callback.profile_sha,
             "FIXED_DRIVER_PROFILE_CHANGED")
    identity, protocol, window = callback.identity, callback.protocol, callback.window
```

If those lines are gone, the driver-renewal session already landed the pin: stop and report that PR 0 is skipped.

Then define `PY`, `TRADEGEN_RUNS_DIR` and `focus` in this shell exactly as this plan's "Running tests" section
shows; every later step uses them.

- [ ] **Step 2: Write the failing tests**

In `tests/launch_driver.py`, replace line 17:

```python
from execution_launch.profile import profile_contract_digest
```

with:

```python
from execution_launch.profile import profile_contract_digest, profile_digest
```

Append after line 273 (end of file):

```python


def test_same_terms_renewal_moves_only_asof_and_the_fixed_driver_keeps_ticking():
    env = fixture()
    first = decide(env)
    rules = env.profile.instrument_rules
    # instrument_refresh.py:94 builds exactly this profile from identical terms and a newer asof.
    renewed = replace(env.profile, instrument_rules=replace(rules, asof=env.frame.bars[-1].observed_at))
    assert profile_digest(renewed) != profile_digest(env.profile)
    assert profile_contract_digest(renewed) == profile_contract_digest(env.profile)
    env.observation = replace(env.observation, profile=renewed)
    assert decide(env) == first
    expected = decide(fixture(5))
    env.profile = renewed
    next_frame(env, 5)
    assert decide(env) == expected


def test_changed_contract_terms_still_refuse_after_a_renewal():
    for change in (
        lambda p: replace(p, instrument_rules=replace(p.instrument_rules, tick_size=D("0.5"))),
        lambda p: replace(p, instrument_rules=replace(p.instrument_rules, lot_size=D("0.02"))),
        lambda p: replace(p, symbol="KRW-ETH", instrument_rules=replace(p.instrument_rules, symbol="KRW-ETH")),
        lambda p: replace(p, policy=replace(p.policy, first_day_loss_budget=D("9"))),
    ):
        env = fixture()
        changed = change(env.profile)
        assert profile_contract_digest(changed) != profile_contract_digest(env.profile)
        env.observation = replace(env.observation, profile=changed)
        reject(lambda: decide(env), "FIXED_DRIVER_PROFILE_CHANGED")


def test_another_venue_market_or_account_scope_refuses():
    for change in (dict(venue="okx"), dict(market="krx"), dict(account_scope="other-scope")):
        env = fixture()
        env.observation = replace(env.observation, profile=replace(env.profile, **change))
        reject(lambda: decide(env), "FIXED_DRIVER_SCOPE_MISMATCH")
    env = fixture()
    env.observation = replace(env.observation, profile=None)
    reject(lambda: decide(env), "FIXED_DRIVER_SCOPE_MISMATCH")
```

`next_frame(env, 5)` rebuilds the observation from `env.profile`, which is why `env.profile` is set to the renewed
profile first. `fixture(5)` builds the same driver identity and the same slot-5 frame from the construction profile,
so its signal is the reference.

- [ ] **Step 3: Run the new tests and see the stated results**

```bash
focus launch launch_driver/test_same_terms_renewal
focus launch launch_driver/test_changed_contract_terms
focus launch launch_driver/test_another_venue
```

Expected:
- `FAIL launch_driver/test_same_terms_renewal_moves_only_asof_and_the_fixed_driver_keeps_ticking FixedDriverError: FIXED_DRIVER_PROFILE_CHANGED`
  (the bug).
- `PASS launch_driver/test_changed_contract_terms_still_refuse_after_a_renewal` (a guard: today's full-digest pin
  refuses these too, and they must keep refusing after the change).
- `FAIL launch_driver/test_another_venue_market_or_account_scope_refuses AssertionError: ('FIXED_DRIVER_PROFILE_CHANGED', 'FIXED_DRIVER_SCOPE_MISMATCH')`.

- [ ] **Step 4: Write the implementation**

In `execution_launch/driver.py`, replace lines 244-246:

```python
    _require(profile_digest(observation.profile) == callback.profile_sha,
             "FIXED_DRIVER_PROFILE_CHANGED")
    identity, protocol, window = callback.identity, callback.protocol, callback.window
```

with:

```python
    identity, protocol, window = callback.identity, callback.protocol, callback.window
    profile = observation.profile
    # The runner swaps in each renewed profile; a same-terms renewal changes only
    # instrument_rules.asof, which the contract digest leaves out.
    _require(type(profile) is LaunchProfile
             and (profile.venue, profile.market, profile.account_scope)
             == (protocol.venue, protocol.market, callback.profile.account_scope),
             "FIXED_DRIVER_SCOPE_MISMATCH")
    _require(profile_contract_digest(profile) == identity.profile_contract_digest,
             "FIXED_DRIVER_PROFILE_CHANGED")
```

Line 243 (`_instant(observation.now)`) and line 247 onward stay. `LaunchProfile`, `profile_contract_digest` and
`profile_digest` are already imported (`driver.py:24-25`); `profile_digest` stays in use at `408` and `435`, and
`_FixedCallback.profile_sha` stays for `describe_fixed_driver`. The edit adds 7 lines: old line 251 is now 258, old
262-263 are 269-270, old 380 is 387 and old 383-388 are 390-395.

- [ ] **Step 5: Run the focused tests and the module's tests**

```bash
focus launch launch_driver/test_same_terms_renewal
focus launch launch_driver/test_changed_contract_terms
focus launch launch_driver/test_another_venue
focus launch launch_driver/
```

Expected: every line `PASS`; the last command prints 15 `PASS launch_driver/...` lines (12 existing, 3 new) and
exits 0.

- [ ] **Step 6: Commit**

```bash
diff <(git diff --stat) <(git diff --stat --ignore-cr-at-eol) && echo LF-OK
git add execution_launch/driver.py tests/launch_driver.py
git commit -F - <<'EOF'
Pin the fixed driver to the current profile's contract digest and scope

The driver compared the full profile_digest of the runner's current
profile with the digest taken at construction. profile_digest includes
instrument_rules.asof, so the first same-terms renewal made the next
tick refuse FIXED_DRIVER_PROFILE_CHANGED and, outside observe mode, the
runner stopped for good. The driver now compares profile_contract_digest, which leaves out
only asof, and checks the profile's venue, market and account scope
(FIXED_DRIVER_SCOPE_MISMATCH).

driver.py is part of the fixed driver identity: a history window bound
under the old identity refuses HISTORY_IDENTITY_CHANGED, so a new
window and a new review are needed after merge.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

Expected: `LF-OK`, then one commit with exactly these two files.

---

### Task 2: Read each tick's rules from the current profile

**Files:**
- Modify: `execution_launch/driver.py:251`, `380`, `383-388` at fd85850 (`258`, `387`, `390-395` after Task 1)
- Test: `tests/launch_driver.py`, appended after Task 1's tests

**Interfaces:**
- Consumes: Task 1's local `profile = observation.profile` in `_validate_frame`;
  `_sized_signal(identity, frame, target, rules, protocol) -> Signal` (`driver.py:208-237`);
  `validate_order(order: Order, rules: InstrumentRules) -> None` (`execution_control/model.py:165-181`);
  `patch` and `Fraction` (already imported at `tests/launch_driver.py:8` and `5`); the Task 1 test helpers
  `D`, `reject`, `fixture` and `decide`.
- Produces: the bar tick check (`rules.tick_size`), `_sized_signal` and the validation `Order` read
  `observation.profile` and its `instrument_rules`. `callback.profile` stays only for the account key (`driver.py:302`,
  `309` after Task 1), the scope comparison of Task 1 and the identity rebuild (`describe_fixed_driver`,
  `driver.py:434-439` at fd85850). PR 4d relies on this: a profile renewed to another coin carries that coin's symbol and tick.
  For fixed profiles nothing observable changes, because the contract digest pins every rule field except `asof`.

- [ ] **Step 1: Write the failing test**

Append to `tests/launch_driver.py`:

```python


def test_bar_ticks_and_sizing_read_the_observed_profile_rules():
    env = fixture()
    pinned = profile_contract_digest(env.profile)
    rules = env.profile.instrument_rules
    # Hold the contract digest still so only the observed rules differ from the construction profile's.
    with patch("execution_launch.driver.profile_contract_digest", lambda profile: pinned):
        env.observation = replace(env.observation,
            profile=replace(env.profile, instrument_rules=replace(rules, tick_size=D("3"))))
        reject(lambda: decide(env), "FIXED_DRIVER_BAR_PRICE_INVALID")  # bid 100 is off a 3 KRW tick
        env = fixture()
        env.observation = replace(env.observation,
            profile=replace(env.profile, instrument_rules=replace(rules, min_notional_krw=D("1000000"))))
        assert decide(env).action == "hold"  # the slot-4 entry is below the observed minimum
        env = fixture()
        env.observation = replace(env.observation,
            profile=replace(env.profile, instrument_rules=replace(rules, lot_size=D("0.0001"))))
        signal = decide(env)  # validate_order must check this entry against the observed 0.0001 lot
        assert signal.action == "entry"
        assert (Fraction(signal.quantity)/Fraction(rules.lot_size)).denominator != 1
```

The patch replaces the module global that both `_validate_frame` and `_identity` (through `describe_fixed_driver`)
call, and returns the construction profile's real contract digest, so the identity rebuild still matches. The three
cases cover the three reads: the bar tick check (tick 3), `_sized_signal` (minimum notional) and `validate_order`
(lot 0.0001). In the last case the sized entry is on the observed 0.0001 lot but off the construction profile's 0.01
lot, so a `validate_order` that still read `self.profile.instrument_rules` would raise `quantity not on lot`.

- [ ] **Step 2: Run it and see it fail**

```bash
focus launch launch_driver/test_bar_ticks_and_sizing
```

Expected: `FAIL launch_driver/test_bar_ticks_and_sizing_read_the_observed_profile_rules AssertionError: expected refusal`
(the tick check still reads the construction profile's 1 KRW tick, so the frame passes and the driver returns the
entry).

- [ ] **Step 3: Write the implementation**

In `execution_launch/driver.py`, replace line 258 (251 at fd85850):

```python
    rules = callback.profile.instrument_rules
```

with:

```python
    rules = profile.instrument_rules
```

Replace lines 387-395 (380-388 at fd85850):

```python
            signal = _sized_signal(identity, frame, target, self.profile.instrument_rules, self.protocol)
            _require(not (slot == self.window.end and frame.anchor.units > 0 and signal.action == "hold"),
                     "FIXED_DRIVER_TERMINAL_DUST_UNLIQUIDATED")
            if signal.action != "hold":
                validate_order(Order(client_id="fixedvalidation", account_scope=self.profile.account_scope,
                    venue=self.profile.venue, market=self.profile.market, symbol=self.profile.symbol,
                    side="buy" if signal.action == "entry" else "sell", quantity=signal.quantity,
                    limit_price=signal.limit_price, quote_krw=Decimal(1), time_in_force=self.profile.time_in_force),
                    self.profile.instrument_rules)
```

with:

```python
            profile = observation.profile
            signal = _sized_signal(identity, frame, target, profile.instrument_rules, self.protocol)
            _require(not (slot == self.window.end and frame.anchor.units > 0 and signal.action == "hold"),
                     "FIXED_DRIVER_TERMINAL_DUST_UNLIQUIDATED")
            if signal.action != "hold":
                validate_order(Order(client_id="fixedvalidation", account_scope=profile.account_scope,
                    venue=profile.venue, market=profile.market, symbol=profile.symbol,
                    side="buy" if signal.action == "entry" else "sell", quantity=signal.quantity,
                    limit_price=signal.limit_price, quote_krw=Decimal(1), time_in_force=profile.time_in_force),
                    profile.instrument_rules)
```

The validation order takes every field from the same profile the runner's `_order` uses (`runner.py:350-353`).
Venue, market and account scope equal `callback.profile`'s by Task 1's check; time in force and the rest are pinned
by the contract digest. Between the second `_validate_frame` (`driver.py:374` after Task 1) and this read only
`describe_fixed_driver` and the `seen` checks run; neither calls the injected provider or verifier, so the profile
read here is the one just checked.

- [ ] **Step 4: Run the focused test, the module's tests and the real-history driver tests**

```bash
focus launch launch_driver/test_bar_ticks_and_sizing
focus launch launch_driver/
focus launch launch_live_history/
focus launch launch_review_auth/
```

Expected: every line `PASS`; `launch_driver/` prints 16 `PASS` lines (12 existing, 4 new); `launch_live_history/`
prints 13 `PASS` lines (the fixed driver ticking over a real `LiveHistory` journal under a temporary root, about 35
seconds); `launch_review_auth/` prints 14 `PASS` lines (real fixed drivers bound to signed reviews); each command
exits 0. The other modules that build the real fixed driver (`launch_coordinator`, about 9 minutes,
`launch_study_review`, `launch_owner_rehearsal`) run in Task 3's full suite.

- [ ] **Step 5: Commit**

```bash
diff <(git diff --stat) <(git diff --stat --ignore-cr-at-eol) && echo LF-OK
git add execution_launch/driver.py tests/launch_driver.py
git commit -F - <<'EOF'
Read each fixed-driver tick's rules from the runner's current profile

The bar tick check, order sizing and the order validation now use
observation.profile and its instrument_rules. For fixed profiles the
contract digest already pins every rule field except asof, so the
behaviour is unchanged; a later universe profile carries the trade
coin's rules there. callback.profile stays for the account key, the
scope check and the identity rebuild.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

Expected: `LF-OK`, then one commit with exactly these two files.

---

### Task 3: Guards, full suite and the pull request

**Files:**
- No file changes. Reads `execution_launch/driver.py` and `tests/launch_driver.py` as committed in Tasks 1 and 2.

**Interfaces:**
- Consumes: the two commits of Tasks 1 and 2.
- Produces: branch `claude/universe-pr0-driver-pin` pushed to `origin` and one open pull request against `main`.
  The owner merges it; PR 4b is cut from `main` after that merge.

- [ ] **Step 1: Run the guard modules**

```bash
focus compliance compliance_guards/
focus control control_guards/
focus accounts accounts_guards/
focus launch launch_guards/
focus execution execution_guards/
```

Expected: only `PASS` lines, each command exits 0. `control_guards` runs the `tests/renewal_boundaries.py` checks
(`test_renewal_validation_has_only_reviewed_pure_calls_and_import_surfaces`,
`test_renewal_effect_closure_rejects_source_io_clock_aliases_and_import_time_effects`). `driver.py` is not in their
pins (`tests/renewal_boundaries.py:21-38`), so no pin changes; if one fails, stop and report, never regenerate a pin.

- [ ] **Step 2: Run the full suite**

```bash
"$PY" -X utf8 -m tests.run_all
git restore qa/acceptance_results.json
```

Expected: the last line of the run reads `<n>/<m> passed, 0 failed, <k> not run; ...qa/acceptance_results.json`.
`qa/acceptance_results.json` is a tracked file (`git ls-files qa` lists it; `.gitignore` does not apply to tracked
files) and every full run rewrites it, so `git restore` puts the committed record back: this PR does not commit it.
If a test fails, check it on `origin/main` in a separate worktree:

```bash
git worktree add --detach ../pr0-main-check origin/main
(cd ../pr0-main-check && focus <suite> <module>/<test_name>)
git worktree remove ../pr0-main-check
```

A test that fails there too is pre-existing: list it in the PR body under "Not verified" and do not fix it in this
PR. A test that fails only on this branch is a defect of this PR: fix it in a new task before opening the PR.

Known at planning time: on unmodified fd85850, run alone on 2026-11-11,
`launch_owner_ops/test_runtime_worker_runs_once_and_closes_with_bounded_lifecycle` failed (the worker thread was
still alive after the 10-second join, `tests/launch_owner_ops.py:239-240`). That test drives the coordinator's
recording driver (`tests/launch_coordinator.py:241-250`), not `driver.py`; confirm it on the `origin/main` worktree
(`focus launch launch_owner_ops/test_runtime_worker_runs_once`) and treat it as pre-existing. The PR body below names it under "Not verified"; if it passes in your full-suite run,
delete that bullet, and if another test fails on both branches, add a bullet for it in the same form.

- [ ] **Step 3: Check the branch**

```bash
git status --short
git log --oneline origin/main..HEAD
diff <(git diff --stat origin/main..HEAD) <(git diff --stat --ignore-cr-at-eol origin/main..HEAD) && echo LF-OK
git diff --stat origin/main..HEAD
```

Expected: no tracked change pending (no ` M qa/acceptance_results.json`; untracked spec and plan documents may be
listed with `??`); two commits; `LF-OK`; exactly `execution_launch/driver.py` and `tests/launch_driver.py` changed.

- [ ] **Step 4: Push and open the pull request**

```bash
git push -u origin claude/universe-pr0-driver-pin
gh pr create --repo xkg4real/tradegen --base main --head claude/universe-pr0-driver-pin \
  --title "Keep the fixed driver ticking after a same-terms rules renewal" --body-file - <<'EOF'
## Summary

- The fixed driver compared the full `profile_digest` of the runner's current profile with the digest taken at
  construction (`execution_launch/driver.py:244`). `profile_digest` includes `instrument_rules.asof`, so the first
  same-terms renewal (the coordinator renews every 4 minutes) made the next tick refuse
  `FIXED_DRIVER_PROFILE_CHANGED`, and outside observe mode the runner's catch-all stopped it for good
  (`execution_launch/runner.py:459-463`).
- The driver now pins `profile_contract_digest`, which leaves out only `asof`, and checks the current profile's
  venue, market and account scope (`FIXED_DRIVER_SCOPE_MISMATCH`).
- The bar tick check, order sizing and order validation read the rules from the current profile. `callback.profile`
  stays for the account key, the scope check and the identity rebuild.

Spec: `docs/superpowers/specs/2026-11-11-upbit-krw-universe-design.md`, section 12 (first bullet) and section 19
(item 0).

## Tests added (`tests/launch_driver.py`)

- `test_same_terms_renewal_moves_only_asof_and_the_fixed_driver_keeps_ticking`: a fixed KRW-BTC tick after a
  same-terms renewal (only `asof` changes) passes, at the same slot and at the next slot.
- `test_changed_contract_terms_still_refuse_after_a_renewal`: a changed tick, lot, symbol or policy still refuses.
- `test_another_venue_market_or_account_scope_refuses`: another venue, market or account scope, or no profile,
  refuses.
- `test_bar_ticks_and_sizing_read_the_observed_profile_rules`: with the contract digest held still, the tick check,
  sizing and order validation use the current profile's rules (a 3 KRW tick, a higher minimum notional, a finer lot).

Guards (`compliance_guards`, `control_guards` with the renewal boundaries, `accounts_guards`, `launch_guards`,
`execution_guards`) pass. The full suite has no failure except the pre-existing ones listed under "Not verified".

## Effect on deployments

- `execution_launch/driver.py` is part of the fixed driver identity and of the compliance code hash. After merge:
  code-approve on the merged head, a new strategy review for the new identity, and a new history window. A journal
  bound under the old identity refuses `HISTORY_IDENTITY_CHANGED` at restart, before any tick.
- Unchanged: profile, contract and rule-terms digests, the protocol digest and the study capture source hash.

## Not verified

- No runner-level test drives a real issued renewal through `Runner.refresh_instrument_rules` into a tick of the real
  fixed driver; the coordinator tests use a recording driver. The driver test builds the renewed profile exactly as
  `instrument_refresh.py:94` does (same terms, newer `asof`).
- No rehearsal and no run on the owner's PC.
- `launch_owner_ops/test_runtime_worker_runs_once_and_closes_with_bounded_lifecycle` also fails on `origin/main`
  (the worker thread is still alive after the 10-second join); it uses a recording driver and is not touched here.

This is software design, not legal, tax or investment advice.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
```

Expected: `gh` prints the pull request URL. Do not merge; the owner merges on GitHub.
