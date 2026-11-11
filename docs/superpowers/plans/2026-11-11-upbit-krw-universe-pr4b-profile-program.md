# Upbit KRW universe PR 4b: universe profile, protocol digests and rotation program Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give launch profiles, forward protocols and programs an optional universe form (bound to the signed rule's
sha256 instead of one coin) without changing a single fixed KRW-BTC digest, and add the `universe_top1_momentum`
program kind with its pure chooser.

**Architecture:** One optional field, `universe_rule_sha256`, on `LaunchProfile`, `ForwardProtocol` and `ProgramSpec`
(plus the four other rotation parameters on `ProgramSpec`), each `None` by default and left out of every canonical
encoding while `None`. `rule_terms_digest` and `profile_contract_digest` gain a universe form that drops the trade
coin's symbol, tick and asof and hashes the rule sha256; every site that computes rule terms passes the profile's (or
protocol's) selector, and `workflow._bound_profile` binds the rule instead of the coin. The chooser is one pure
function in `program.py` over recorded slot values, using exact fractions.

**Tech Stack:** Python 3.13 (venv at `TRADEGEN_PR9/.venv`, read-only), stdlib `dataclasses`, `decimal`, `fractions`,
`json`, `hashlib`, `ast` (one test). No new dependency.

**Spec:** [2026-11-11-upbit-krw-universe-design.md](../specs/2026-11-11-upbit-krw-universe-design.md), sections 10,
12 and 14.

## Global Constraints

All constraints in the index apply: [2026-11-11-upbit-krw-universe-index.md](2026-11-11-upbit-krw-universe-index.md)
(base, one branch and PR, no new dependency, offline tests, `focus` runner, byte-exact line endings, never `sed -i`,
commit trailer, PR body ending, the owner merges).

Constraints specific to this PR, verbatim from the spec:

- "`LaunchProfile` gets `universe_rule_sha256` (`None` for fixed profiles). A universe profile still carries `symbol`
  and `instrument_rules`; they mean the trade coin." (section 10)
- "Every new field (on `LaunchProfile`, `ForwardProtocol`, `ProgramSpec` and `PreparedSession`) defaults to `None`
  and is left out of its canonical encoding when `None`: `profile_body`, `strategy._plain` and `protocol_json`
  (`strategy.py:65-67`, `172`, `600`), and the session's `fields` and `digest(fields)` (`session.py:172-180`). Each
  closed-key parser accepts the old key set or the old set plus the new keys: `strategy._object`
  (`strategy.py:567-569`, used by `parse_protocol` at `587`) and the `session_prepared` shape in
  `controller._event_data` (`controller.py:151`, `170-171`). Fixed profiles, protocols, programs and sessions
  therefore keep today's digests byte for byte, and existing journal rows still fold." (section 10; the
  `PreparedSession` and `controller` parts belong to PR 4a)
- "For a universe profile, `profile_contract_digest` leaves out the top-level `symbol` and `instrument_rules.symbol`,
  `tick_size` and `asof`. Lot, minimums, fees, `source_digest` and `universe_rule_sha256` stay pinned." (section 10)
- "`rule_terms_digest(rules, *, universe_rule_sha256=None)`: with `None` it is today's function. With a value it
  drops `symbol`, `tick_size` and `asof` and adds the rule sha256 to the hashed body, so the two forms never collide.
  `InstrumentRules` gets no marker field, because `rules_digest` hashes every field and signed code reads it."
  (section 10)
- "Every computing site passes the selector: `profile.universe_rule_sha256` at `instrument_refresh.py:75` (both
  sides use the old profile's value), `runner.py:151`, `driver.py:166`, `workflow.py:179` and `208`, `study.py:247`
  and `479`, `study_review.py:87` and `review_request.py:242`; `protocol.universe_rule_sha256` at
  `strategy._rule_terms` (`strategy.py:92-94`, used at `288`); the example profile's value at
  `prepare_launch_example.py:70`." (section 10)
- "`workflow._bound_profile` (`workflow.py:175-176`) compares venue, market, quote, strategy id and
  `universe_rule_sha256` instead of `symbol` for a universe protocol." (section 10)
- "A universe protocol's `symbol` is the benchmark `KRW-BTC`, never a trading pin" (section 12)
- "`_protocol` (`strategy.py:135`, also reached from `parse_protocol` and the runner's tick) accepts
  `forward-universe-v1` as well as `forward-paper-v1`." (section 14)
- "**Program kind** `universe_top1_momentum` (program schema v2). Fields, all frozen per candidate: `lookback_slots`
  L, `min_hold_slots` m (at least 1), `switch_margin` (a fraction, at least 0), `exposure_fraction`,
  `max_candidates` N (at least 1), `universe_rule_sha256`." (section 14)
- "`price_X(j)` is the `trade_price` from slot j's ticker read, defined only if X's trade time is within 60 seconds
  of slot j. `r_X(k) = price_X(k) / price_X(k - L) - 1`, defined only when both prices are defined. A slot whose flag
  read or ticker read is `unavailable` gives no prices at all." (section 14; the 60-second rule is applied by the
  caller that builds `ChooserSlot.prices`, PR 4d and PR 5)
- "**Buy targets at k**: coins in the top-N of the snapshot in force at k, `unflagged` at k, with `r_X(k)` defined."
  (section 14)
- "Decision at k: 1. h is `warning` at k: cash. 2. h is a coin and `r_h(k)` is undefined: keep h. 3. best = the buy
  target with the largest r; ties by symbol, ascending; none if there are no buy targets. 4. h is cash: best if
  `r_best > 0`, else cash. 5. Hold count of h below m: keep h. 6. `r_h <= 0` and (best is none or `r_best <= 0`):
  cash. 7. best is not h, `r_best > 0` and `r_best - r_h > switch_margin`: best. 8. Otherwise keep h. m counts
  decisions." (section 14)
- "The driver identity hashes `driver.py`, `program.py`, `strategy.py`, `runner.py`, `profile.py` and three
  `execution_control` files, including `controller.py`. These changes make a new identity, so a new history window
  (GENESIS), a new protocol and a new review are needed. Any in-flight KRW-BTC study or window finishes first."
  (section 12)
- Tests: "a fixed profile's and protocol's digests byte-identical to today's; the same rules give different fixed
  and universe digests" (section 19) and "the chooser cases" (section 19).

PR-specific rules that follow from the index:

- This PR starts after PR 0 and PR 1 are merged. It uses no PR 1 name: tests use the literal
  `hashlib.sha256(b"fixture-universe-rule").hexdigest()` as a rule sha256. PR 0 may shift `driver.py` lines after
  240; this PR touches only `driver.py:166`.
- `tests/renewal_boundaries.py` pins the initialization surface of `execution_launch/profile.py`. Task 1 changes it
  (one new field, one new keyword-only parameter). The pin is updated by hand to the value stated in Task 1 after the
  surface diff is reviewed; it is never regenerated blindly.
- Byte-identical digests mean: the same inputs give the same digest. Real deployments still change, because this
  PR edits source files that other digests hash: `program.py` is the program artifact
  (`study.py:63` `PROGRAM_SOURCE`, `workflow.py:232`, `coordinator.py:804`), so `program_digest` over the installed
  `program.py`, which is the `strategy_code_sha256` of every real profile and protocol, changes; `study.py`,
  `program.py` and `strategy.py` are in `CAPTURE_FILES` (`study.py:59-61`), so `capture_source_code_sha256` changes
  and a frozen or in-flight study capture no longer binds; `driver.py`, `program.py`, `strategy.py`, `runner.py` and
  `profile.py` are in the driver identity (`driver.py:35-38`); every changed `execution_launch` file is in the
  compliance code hash (`core/compliance/owner.py:789-798`), so code-approve runs on the merged head. The PR body
  states all of this; the owner merges only after any in-flight KRW-BTC study or window has finished (spec section
  12).
- Line endings, checked at fd85850: every file this PR touches is LF except `execution_launch/study.py`, which is
  CRLF on every line (the index's "Python files are LF" does not hold for it). Task 5 edits it at two sites, each one
  line becoming two; all four resulting lines end in CRLF like the rest of the file. The new `tests/launch_program.py`
  is LF.

## File Structure

- Modify `execution_launch/profile.py`: `LaunchProfile.universe_rule_sha256`, its validation, its omission from
  `profile_body`, and the universe forms of `rule_terms_digest` and `profile_contract_digest`.
- Modify `execution_launch/strategy.py`: `ForwardProtocol.universe_rule_sha256`, `UNIVERSE_EVALUATOR_REVISION`, the
  omit-when-`None` rule in `_plain`, the optional-key rule in `_object`, `_protocol` acceptance, the selector in
  `_rule_terms`, and the fixed evaluator's refusal of the universe revision.
- Modify `execution_launch/program.py`: schema v2 kind `universe_top1_momentum` (fields, validation, canonical body,
  parser), `target_fraction` refusal of that kind, and `ChooserState`, `ChooserSlot`, `choose`.
- Modify the selector sites: `execution_launch/instrument_refresh.py`, `execution_launch/runner.py`,
  `execution_launch/driver.py`, `execution_launch/workflow.py` (also `_bound_profile`), `execution_launch/study.py`,
  `execution_launch/study_review.py`, `execution_launch/review_request.py`, `tools/research/prepare_launch_example.py`.
- Modify tests: `tests/launch_profile.py` (pins, universe digests, call-site scan), `tests/launch_strategy.py`
  (pins, universe protocol), `tests/launch_workflow.py` (`_bound_profile`), `tests/launch_instrument_refresh.py`
  (universe renewal), `tests/renewal_boundaries.py` (one pin), `tests/launch_acceptance.py` (`MODULES`).
- Create `tests/launch_program.py`: program schema v2 and every chooser rule.

## Contract notes

- The omit-when-`None` rule is carried by dataclass field metadata `{"omit_none": True}`: `strategy._plain` leaves
  such a field out while it is `None`, and `strategy._object` accepts it absent (never `null`). `profile_body` is
  explicit code and drops the one key by name, so `tests/renewal_boundaries.py` sees no new call in `profile_body`.
- Program schema v2 keeps `fast_window` and `slow_window` (both 0) in its canonical body: the v2 key set is the v1
  key set plus the five universe keys, which is the index's "old set plus the new keys" rule, and it keeps
  `parse_program(json.dumps(strategy._plain(spec)))` a round trip for study plans.
- `ChooserState` and `ChooserSlot` are `@dataclass(frozen=True)` exactly as the index states. A window starts at
  `ChooserState(held=None, hold_count=0)`; the returned state's `hold_count` is the previous count plus 1 when the
  decision equals `held`, else 1.
- Additions to the index's Interface contract that later plans (PR 4c, 4d, 5) rely on:
  - `ChooserSlot`: an unavailable flag read gives empty `flags` and `prices`; an unavailable ticker read gives empty
    `prices` and keeps the available flag classes (spec section 14 drops prices only). The index's "an unavailable
    read gives an empty mapping and empty `flags`" is read this way, as PR 4d does. `choose` checks
    `len(now_slot.top_n) <= max_candidates`; `lag_slot.top_n` and `lag_slot.flags` are not read.
  - Refusal codes: `PROGRAM_UNIVERSE_PARAMETERS_INVALID` (L, m and N not ints in 1..4096, `fast_window` or
    `slow_window` not 0, a bad rule sha256, or a universe field set on another kind), `PROGRAM_CHOOSER_INPUT_INVALID`
    (state or slot shape, or a top-N wider than N); `target_fraction` refuses the universe kind with
    `PROGRAM_KIND_UNSUPPORTED`. `exposure_fraction` of the universe kind satisfies `0 < e <= 1`.
  - `strategy._protocol`: `forward-paper-v1` exactly when `universe_rule_sha256 is None`, `forward-universe-v1`
    exactly when it is set, and then `symbol == "KRW-BTC"`; `run_paper_validation` refuses `forward-universe-v1` with
    `STRATEGY_EVALUATOR_UNSUPPORTED` (PR 5 adds that evaluator); `strategy._rule_terms(rules, universe_rule_sha256)`
    takes a required second argument.
  - JSON: an explicit `"universe_rule_sha256": null` in a profile parses to the fixed form, like every other profile
    field; in a protocol it is refused (`STRATEGY_JSON_SCHEMA_INVALID`), since `_object` accepts an `omit_none` key
    absent, never `null`.

---

### Task 1: Universe profile field and digests

**Files:**
- Modify: `execution_launch/profile.py:91-95` (field), `:166-167` (validation), `:261-262` (`profile_body`),
  `:283-310` (`rule_terms_digest`, `profile_contract_digest`)
- Modify: `tests/renewal_boundaries.py:35` (profile surface pin)
- Test: `tests/launch_profile.py:4-5` (import) and new tests appended after line 246

**Interfaces:**
- Consumes: nothing new.
- Produces:
  - `LaunchProfile.universe_rule_sha256: str | None = None` (64 lowercase hex or `None`; anything else raises
    `ProfileError("PROFILE_TEXT_INVALID", "universe_rule_sha256")`).
  - `profile_body(profile) -> dict` without the `universe_rule_sha256` key when it is `None`.
  - `rule_terms_digest(rules: InstrumentRules, *, universe_rule_sha256: str | None = None) -> str`.
  - `profile_contract_digest(profile: LaunchProfile) -> str`, universe form when `profile.universe_rule_sha256` is
    set.
  - Test fixture `RULE = hashlib.sha256(b"fixture-universe-rule").hexdigest()` in `tests/launch_profile.py`, which
    PR 4c's tests import.

- [ ] **Step 1: Start the branch from main**

```bash
git fetch origin
git switch -c claude/universe-pr4b-profile-program origin/main
git log --oneline -5
```

Expected: the log shows the merges of PR 0 (driver pin, or the separate driver-renewal change that replaces it) and
PR 1 (compliance, pure). If either is missing, stop and report; this PR is ordered after both. In the index's merge
order PR 2, PR 3 and PR 4a are usually merged too. None of them moves a line this plan edits: PR 2 replaces
`tests/launch_acceptance.py:15` (Task 3 below has the exact text for both cases) and `tests/renewal_boundaries.py:25`,
PR 4a replaces `tests/renewal_boundaries.py:32`, and PR 3 replaces `execution_launch/profile.py:413-414` inside
`preflight_profile` (a function body, so the profile surface pin at `tests/renewal_boundaries.py:35` is unchanged).
Still match every edit below by its quoted text, not only by its line number.

- [ ] **Step 2: Write the failing tests**

In `tests/launch_profile.py`, replace lines 4-5:

```python
from decimal import Decimal, localcontext
import json
```

with:

```python
from decimal import Decimal, localcontext
import hashlib
import json
```

Append to the end of `tests/launch_profile.py` (two blank lines before the first new line):

```python
RULE = hashlib.sha256(b"fixture-universe-rule").hexdigest()


def test_fixed_profile_digests_are_byte_identical_to_the_pre_universe_encoding():
    profile = fixture_profile()
    assert profile.universe_rule_sha256 is None and "universe_rule_sha256" not in profile_body(profile)
    assert profile_digest(profile) == "5aebfdf42857cc0a9ece19bbb988779535a7f0db63ee53ee890cfe249c5fdbd4"
    assert profile_contract_digest(profile) == "96895573944a45434a4ca6383bfe51b39c05486bbfa6d0a54b66fff41f7b8b35"
    assert rule_terms_digest(profile.instrument_rules) == (
        "3786c81272167bb525374d9f049e4213acdadae88c04cfdf28e0f5bd5add7eeb")
    assert (rule_terms_digest(profile.instrument_rules, universe_rule_sha256=None)
            == rule_terms_digest(profile.instrument_rules))


def test_universe_profile_round_trips_and_differs_from_the_fixed_form_on_the_same_rules():
    fixed = fixture_profile()
    universe = replace(fixed, universe_rule_sha256=RULE)
    assert profile_body(universe)["universe_rule_sha256"] == RULE
    assert parse_profile_json(json.dumps(profile_body(universe))) == universe
    rules = fixed.instrument_rules
    assert rule_terms_digest(rules, universe_rule_sha256=RULE) != rule_terms_digest(rules)
    assert (rule_terms_digest(rules, universe_rule_sha256="f"*64)
            != rule_terms_digest(rules, universe_rule_sha256=RULE))
    assert profile_contract_digest(universe) != profile_contract_digest(fixed)
    assert profile_digest(universe) != profile_digest(fixed)
    for value in ("F"*64, "f"*63, 7):
        rejected(lambda value=value: replace(fixed, universe_rule_sha256=value), "PROFILE_TEXT_INVALID")
        rejected(lambda value=value: rule_terms_digest(rules, universe_rule_sha256=value), "PROFILE_TEXT_INVALID")
    body = profile_body(fixed)
    body["universe_rule_sha256"] = None
    assert parse_profile_json(json.dumps(body)) == fixed  # an explicit null is the fixed form, like other fields


def test_universe_contract_and_rule_terms_follow_the_rule_not_the_trade_coin():
    fixed = fixture_profile()
    universe = replace(fixed, universe_rule_sha256=RULE)
    def terms(profile):
        return rule_terms_digest(profile.instrument_rules, universe_rule_sha256=RULE)
    moved = replace(universe, symbol="KRW-ETH", instrument_rules=replace(universe.instrument_rules,
                    symbol="KRW-ETH", tick_size=D("5"), asof=NOW+timedelta(days=3)))
    assert profile_contract_digest(moved) == profile_contract_digest(universe) and terms(moved) == terms(universe)
    assert profile_digest(moved) != profile_digest(universe)
    for field, value in (("lot_size", D("0.1")), ("min_quantity", D("0.1")), ("min_notional_krw", D("30")),
                         ("fee_fraction", D("0.002")), ("source_digest", "d"*64)):
        changed = replace(universe, instrument_rules=replace(universe.instrument_rules, **{field: value}))
        assert profile_contract_digest(changed) != profile_contract_digest(universe), field
        assert terms(changed) != terms(universe), field
    assert profile_contract_digest(replace(universe, universe_rule_sha256="f"*64)) != profile_contract_digest(universe)
    fixed_moved = replace(fixed, symbol="KRW-ETH", instrument_rules=replace(fixed.instrument_rules, symbol="KRW-ETH"))
    assert profile_contract_digest(fixed_moved) != profile_contract_digest(fixed)
```

- [ ] **Step 3: Run the tests to verify they fail**

Define `focus` once per shell as the index states, then run:

```bash
focus launch launch_profile/test_fixed_profile_digests
focus launch launch_profile/test_universe_
```

Expected: exit 1 for both. The first prints
`FAIL launch_profile/test_fixed_profile_digests_are_byte_identical_to_the_pre_universe_encoding AttributeError: 'LaunchProfile' object has no attribute 'universe_rule_sha256'`;
the second prints two `FAIL` rows with
`TypeError: LaunchProfile.__init__() got an unexpected keyword argument 'universe_rule_sha256'`.

- [ ] **Step 4: Implement the profile field and the universe digests**

In `execution_launch/profile.py`, replace lines 91-95:

```python
    strategy_id: str | None = None
    strategy_code_sha256: str | None = None

    def __post_init__(self):
        _validate_profile(self)
```

with:

```python
    strategy_id: str | None = None
    strategy_code_sha256: str | None = None
    # Universe profile (spec section 10): the signed universe rule's sha256; symbol and instrument_rules then name
    # the current trade coin. None for a fixed profile, whose canonical body leaves the key out.
    universe_rule_sha256: str | None = None

    def __post_init__(self):
        _validate_profile(self)
```

In `execution_launch/profile.py`, replace lines 166-167:

```python
    if profile.strategy_code_sha256 is not None:
        _text(profile.strategy_code_sha256, "strategy_code_sha256", _SHA)
```

with:

```python
    if profile.strategy_code_sha256 is not None:
        _text(profile.strategy_code_sha256, "strategy_code_sha256", _SHA)
    if profile.universe_rule_sha256 is not None:
        _text(profile.universe_rule_sha256, "universe_rule_sha256", _SHA)
```

In `execution_launch/profile.py`, replace lines 261-262:

```python
    body = {f.name: getattr(profile, f.name) for f in fields(LaunchProfile)
            if f.name not in ("policy", "conventions", "instrument_rules")}
```

with:

```python
    body = {f.name: getattr(profile, f.name) for f in fields(LaunchProfile)
            if f.name not in ("policy", "conventions", "instrument_rules")}
    if profile.universe_rule_sha256 is None:
        del body["universe_rule_sha256"]  # a fixed profile keeps today's canonical body byte for byte
```

In `execution_launch/profile.py`, replace lines 283-310:

```python
def rule_terms_digest(rules: InstrumentRules) -> str:
    """Stable economic rule identity; refresh time is checked separately by E2.

    The source digest and every lot/tick/minimum/fee/scope term remain bound.
    Only the observation's asof timestamp is omitted for prospective evidence.
    """
    try:
        rules_digest(rules)
    except (TypeError, ValueError, AttributeError, ArithmeticError):
        raise ProfileError("PROFILE_INSTRUMENT_RULES_INVALID", "instrument_rules") from None
    body = {f.name: decimal_text(v) if type(v := getattr(rules, f.name)) is Decimal else v
            for f in fields(InstrumentRules) if f.name != "asof"}
    raw = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)
    return hashlib.sha256(raw.encode("ascii")).hexdigest()


def profile_contract_digest(profile: LaunchProfile) -> str:
    """Stable owner/strategy/economic contract for prospective qualification.

    This is not the complete runtime snapshot digest. Current asof is deliberately
    excluded so fresh identical rules do not invalidate multi-day research. The
    controller still enforces the full current rules_digest and five-minute age.
    """
    body = profile_body(profile)
    if body["instrument_rules"] is not None:
        del body["instrument_rules"]["asof"]
    raw = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)
    return hashlib.sha256(raw.encode("ascii")).hexdigest()
```

with:

```python
def rule_terms_digest(rules: InstrumentRules, *, universe_rule_sha256: str | None = None) -> str:
    """Stable economic rule identity; refresh time is checked separately by E2.

    The source digest and every lot/tick/minimum/fee/scope term remain bound.
    Only the observation's asof timestamp is omitted for prospective evidence.
    A universe profile passes its universe_rule_sha256: the coin's symbol and
    tick are then left out as well and the rule sha256 is hashed in their place,
    so the fixed and universe forms never share a digest (spec section 10).
    """
    try:
        rules_digest(rules)
    except (TypeError, ValueError, AttributeError, ArithmeticError):
        raise ProfileError("PROFILE_INSTRUMENT_RULES_INVALID", "instrument_rules") from None
    left_out = ("asof",) if universe_rule_sha256 is None else ("asof", "symbol", "tick_size")
    body = {f.name: decimal_text(v) if type(v := getattr(rules, f.name)) is Decimal else v
            for f in fields(InstrumentRules) if f.name not in left_out}
    if universe_rule_sha256 is not None:
        body["universe_rule_sha256"] = _text(universe_rule_sha256, "universe_rule_sha256", _SHA)
    raw = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)
    return hashlib.sha256(raw.encode("ascii")).hexdigest()


def profile_contract_digest(profile: LaunchProfile) -> str:
    """Stable owner/strategy/economic contract for prospective qualification.

    This is not the complete runtime snapshot digest. Current asof is deliberately
    excluded so fresh identical rules do not invalidate multi-day research. The
    controller still enforces the full current rules_digest and five-minute age.
    A universe profile also leaves out its trade coin (the top-level symbol and
    the rules' symbol and tick); lot, minimums, fees, source digest and
    universe_rule_sha256 stay bound, so the contract holds across coins.
    """
    body = profile_body(profile)
    left_out = ("asof",)
    if profile.universe_rule_sha256 is not None:
        del body["symbol"]
        left_out = ("asof", "symbol", "tick_size")
    if body["instrument_rules"] is not None:
        for name in left_out:
            del body["instrument_rules"][name]
    raw = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)
    return hashlib.sha256(raw.encode("ascii")).hexdigest()
```

- [ ] **Step 5: Run the profile tests**

```bash
focus launch launch_profile/
```

Expected: every `launch_profile/...` row `PASS`, exit 0. The three pinned digests prove the fixed encoding did not
move.

- [ ] **Step 6: Review the renewal surface change and update its one pin**

```bash
focus control control_guards/test_renewal_
"$PY" -B -X utf8 -c "from pathlib import Path; from tests.renewal_boundaries import source_map, problems; print(problems(source_map(Path('.'))))"
```

Expected before the pin update: the `focus` run exits 1 with three rows, one `PASS`
(`test_renewal_import_ports_...`) and two `FAIL`,
`control_guards/test_renewal_validation_has_only_reviewed_pure_calls_and_import_surfaces AssertionError:` and
`control_guards/test_renewal_effect_closure_rejects_source_io_clock_aliases_and_import_time_effects AssertionError:`
(both assert `not problems(...)`); the one-liner prints exactly
`['execution_launch/profile.py: initialization surface changed']`. Any other entry (for example a
"callable surface changed" line for `profile_body`, `profile_contract_digest` or `_validate_profile`) means the code
gained a call that Step 4 does not contain, and must be fixed in the code, not in the pin.

Review: `git diff -- execution_launch/profile.py` must show, outside function bodies, exactly the new
`universe_rule_sha256: str | None = None` field of `LaunchProfile` and the new keyword-only parameter of
`rule_terms_digest`. Then print the new surface value:

```bash
"$PY" -B -X utf8 -c "from pathlib import Path; from tests.renewal_boundaries import _surface; print(_surface(Path('execution_launch/profile.py').read_text(encoding='utf-8')))"
```

Expected output: `74a7733068b1b392df3389054c4e300881f274383adf42da7831455e6aaa0c32` (computed by the plan author from
fd85850 plus the Step 4 code; if the printed value differs, the code differs from Step 4: reconcile the code, do not
copy the printed value).

In `tests/renewal_boundaries.py`, replace line 35:

```python
    "execution_launch/profile.py": "86a4935bd8ef5842cecc6409b282dc78cb3b0635fbc72d2438f9c2826603726e",
```

with:

```python
    "execution_launch/profile.py": "74a7733068b1b392df3389054c4e300881f274383adf42da7831455e6aaa0c32",
```

```bash
focus control control_guards/test_renewal_
```

Expected: all three `control_guards/test_renewal_...` rows `PASS`, exit 0.

- [ ] **Step 7: Commit**

```bash
git diff --stat -- execution_launch/profile.py tests/launch_profile.py tests/renewal_boundaries.py
git diff --stat --ignore-cr-at-eol -- execution_launch/profile.py tests/launch_profile.py tests/renewal_boundaries.py
git add execution_launch/profile.py tests/launch_profile.py tests/renewal_boundaries.py
git commit -m "$(cat <<'EOF'
feat(launch): universe profile field and rule-bound digests

LaunchProfile.universe_rule_sha256 (None for fixed profiles, left out of
profile_body), rule_terms_digest(rules, *, universe_rule_sha256=None) and the
universe form of profile_contract_digest (spec section 10). Fixed digests are
pinned byte for byte; the renewal surface pin for profile.py is updated after
review.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
)"
```

Expected: the two `--stat` outputs are identical before `git add`.

### Task 2: Universe protocol field, omit-when-None encoding and evaluator revisions

**Files:**
- Modify: `execution_launch/strategy.py:12` (import), `:27` (revision), `:65-67` (`_plain`), `:92-94`
  (`_rule_terms`), `:127-128` (`ForwardProtocol`), `:135` and `:144-145` (`_protocol`), `:288-289`
  (`_validate_capture`), `:418-419` (`run_paper_validation`), `:567-569` (`_object`)
- Test: `tests/launch_strategy.py:9-10` (import) and new tests appended after line 288

**Interfaces:**
- Consumes: `rule_terms_digest(rules, *, universe_rule_sha256: str | None = None) -> str` (Task 1).
- Produces:
  - `ForwardProtocol.universe_rule_sha256: str | None = None`, declared with metadata `{"omit_none": True}`.
  - `UNIVERSE_EVALUATOR_REVISION = "forward-universe-v1"`.
  - `_plain(value)`: a dataclass field with metadata `{"omit_none": True}` is left out while `None` (used by
    `evidence_digest`, `protocol_json` and study plan encoding).
  - `_object(value, cls)`: every field required except `omit_none` fields, which may be absent but never `null`.
  - `_protocol(protocol)`: `forward-paper-v1` iff `universe_rule_sha256 is None`; `forward-universe-v1` iff it is set,
    with `symbol == "KRW-BTC"`.
  - `_rule_terms(rules, universe_rule_sha256) -> str`.
  - `run_paper_validation(...)` raises `StrategyEvidenceError("STRATEGY_EVALUATOR_UNSUPPORTED")` for a
    `forward-universe-v1` protocol (the universe evaluator is PR 5).

- [ ] **Step 1: Write the failing tests**

In `tests/launch_strategy.py`, replace lines 9-10:

```python
from decimal import Decimal, localcontext
import json
```

with:

```python
from decimal import Decimal, localcontext
import hashlib
import json
```

Append to the end of `tests/launch_strategy.py` (two blank lines before the first new line):

```python
RULE = hashlib.sha256(b'fixture-universe-rule').hexdigest()


def universe_protocol(protocol, rules):
    from execution_launch.strategy import UNIVERSE_EVALUATOR_REVISION
    return replace(protocol, evaluator_revision=UNIVERSE_EVALUATOR_REVISION, universe_rule_sha256=RULE,
                   rule_terms_digest=rule_terms_digest(rules, universe_rule_sha256=RULE))


def test_fixed_protocol_digest_and_json_are_byte_identical_to_the_pre_universe_encoding():
    p, *_ = fixture_capture()
    encoded = protocol_json(p)
    assert p.universe_rule_sha256 is None and 'universe_rule_sha256' not in encoded
    assert evidence_digest(p) == '8d008761f9b0ddd58d148e52d5b6088d3acbdba18bf30f5317e05bdace8ca937'
    assert hashlib.sha256(encoded.encode('ascii')).hexdigest() == (
        '28ea85cb261fb70bbd56558656ecce3e738b41b886ccfe7c02445183bd2a43dd')
    assert parse_protocol(encoded) == p


def test_universe_protocol_round_trips_and_binds_its_rule_and_the_btc_benchmark():
    p, _, _, rules, _, _, _ = fixture_capture()
    u = universe_protocol(p, rules)
    encoded = protocol_json(u)
    assert parse_protocol(encoded) == u and evidence_digest(parse_protocol(encoded)) == evidence_digest(u)
    assert json.loads(encoded)['universe_rule_sha256'] == RULE and evidence_digest(u) != evidence_digest(p)
    assert register_protocol(u)[-1].protocol_digest == evidence_digest(u)
    for changes, code in (({'symbol': 'KRW-ETH'}, 'STRATEGY_EVALUATOR_SCOPE_UNSUPPORTED'),
                          ({'evaluator_revision': EVALUATOR_REVISION}, 'STRATEGY_EVALUATOR_UNSUPPORTED'),
                          ({'universe_rule_sha256': 'e'*63}, 'STRATEGY_DIGEST_INVALID')):
        rejected(lambda changes=changes: register_protocol(replace(u, **changes)), code)
    rejected(lambda: register_protocol(replace(p, evaluator_revision=u.evaluator_revision)),
             'STRATEGY_EVALUATOR_UNSUPPORTED')
    body = json.loads(encoded)
    del body['universe_rule_sha256']
    rejected(lambda: parse_protocol(json.dumps(body)), 'STRATEGY_EVALUATOR_UNSUPPORTED')
    body = json.loads(protocol_json(p))
    body['universe_rule_sha256'] = None
    rejected(lambda: parse_protocol(json.dumps(body)), 'STRATEGY_JSON_SCHEMA_INVALID')


def test_fixed_evaluator_refuses_a_universe_protocol_and_capture_rules_use_its_selector():
    from execution_launch.strategy import _rule_terms
    p, bars, decisions, rules, _, _, now = fixture_capture()
    u = universe_protocol(p, rules)
    rejected(lambda: run_paper_validation(u, bars, decisions, rules, registry=register_protocol(u),
                                          source_kind='synthetic', now=now), 'STRATEGY_EVALUATOR_UNSUPPORTED')
    assert _rule_terms(rules, RULE) == u.rule_terms_digest != p.rule_terms_digest == _rule_terms(rules, None)
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
focus launch launch_strategy/test_fixed_protocol_digest
focus launch launch_strategy/test_universe_protocol
focus launch launch_strategy/test_fixed_evaluator_refuses
```

Expected: exit 1 each. The first prints
`AttributeError: 'ForwardProtocol' object has no attribute 'universe_rule_sha256'`; the other two print
`ImportError: cannot import name 'UNIVERSE_EVALUATOR_REVISION' from 'execution_launch.strategy'`.

- [ ] **Step 3: Implement the protocol field, encoding rules and revisions**

In `execution_launch/strategy.py`, replace line 12:

```python
from dataclasses import dataclass, fields, is_dataclass
```

with:

```python
from dataclasses import dataclass, field, fields, is_dataclass
```

In `execution_launch/strategy.py`, replace line 27:

```python
EVALUATOR_REVISION = "forward-paper-v1"
```

with:

```python
EVALUATOR_REVISION = "forward-paper-v1"
UNIVERSE_EVALUATOR_REVISION = "forward-universe-v1"  # spec section 14; carried only by a universe protocol
```

In `execution_launch/strategy.py`, replace lines 65-67:

```python
def _plain(value):
    if is_dataclass(value) and not isinstance(value, type):
        return {f.name: _plain(getattr(value, f.name)) for f in fields(value)}
```

with:

```python
def _plain(value):
    if is_dataclass(value) and not isinstance(value, type):
        # A field declared with metadata {"omit_none": True} is left out while it is None, so values without the
        # newer optional fields keep today's encoding and digest byte for byte (spec section 10).
        return {f.name: _plain(getattr(value, f.name)) for f in fields(value)
                if not (f.metadata.get("omit_none") and getattr(value, f.name) is None)}
```

In `execution_launch/strategy.py`, replace lines 92-94:

```python
def _rule_terms(rules):
    rules_digest(rules)  # Revalidate even deliberately mutated frozen inputs.
    return economic_rules_digest(rules)
```

with:

```python
def _rule_terms(rules, universe_rule_sha256):
    rules_digest(rules)  # Revalidate even deliberately mutated frozen inputs.
    return economic_rules_digest(rules, universe_rule_sha256=universe_rule_sha256)
```

In `execution_launch/strategy.py`, replace lines 127-128:

```python
    review_max_age_seconds: int
    seed: int
```

with:

```python
    review_max_age_seconds: int
    seed: int
    # Universe protocol only (evaluator forward-universe-v1): the signed rule's sha256. Its symbol is then the
    # KRW-BTC benchmark, never a trading pin (spec section 12). None is left out of every encoding.
    universe_rule_sha256: str | None = field(default=None, metadata={"omit_none": True})
```

In `execution_launch/strategy.py`, replace line 135:

```python
    _require(protocol.evaluator_revision == EVALUATOR_REVISION, 'STRATEGY_EVALUATOR_UNSUPPORTED')
```

with:

```python
    _require(protocol.evaluator_revision in (EVALUATOR_REVISION, UNIVERSE_EVALUATOR_REVISION)
             and (protocol.universe_rule_sha256 is None) == (protocol.evaluator_revision == EVALUATOR_REVISION),
             'STRATEGY_EVALUATOR_UNSUPPORTED')
```

In `execution_launch/strategy.py`, replace lines 144-145:

```python
             and re.fullmatch(r'KRW-[A-Z0-9]{1,20}', protocol.symbol) is not None,
             'STRATEGY_EVALUATOR_SCOPE_UNSUPPORTED')
```

with:

```python
             and re.fullmatch(r'KRW-[A-Z0-9]{1,20}', protocol.symbol) is not None,
             'STRATEGY_EVALUATOR_SCOPE_UNSUPPORTED')
    if protocol.universe_rule_sha256 is not None:
        _hash(protocol.universe_rule_sha256)
        _require(protocol.symbol == 'KRW-BTC', 'STRATEGY_EVALUATOR_SCOPE_UNSUPPORTED')
```

In `execution_launch/strategy.py`, replace lines 288-289:

```python
    _require(type(rules) is InstrumentRules and _rule_terms(rules) == protocol.rule_terms_digest,
             "STRATEGY_RULES_MISMATCH")
```

with:

```python
    _require(type(rules) is InstrumentRules
             and _rule_terms(rules, protocol.universe_rule_sha256) == protocol.rule_terms_digest,
             "STRATEGY_RULES_MISMATCH")
```

In `execution_launch/strategy.py`, replace lines 418-419:

```python
    sha = _protocol(protocol); _instant(now)
    registry_sha = validate_registry(registry)
```

with:

```python
    sha = _protocol(protocol); _instant(now)
    # This is the fixed-symbol evaluator; a forward-universe-v1 protocol is evaluated only by its own revision.
    _require(protocol.evaluator_revision == EVALUATOR_REVISION, 'STRATEGY_EVALUATOR_UNSUPPORTED')
    registry_sha = validate_registry(registry)
```

In `execution_launch/strategy.py`, replace lines 567-569:

```python
def _object(value, cls):
    _require(type(value) is dict and set(value) == {f.name for f in fields(cls)}, 'STRATEGY_JSON_SCHEMA_INVALID')
    return dict(value)
```

with:

```python
def _object(value, cls):
    """Closed key set: every field, except that an {"omit_none": True} field may be absent (never null)."""
    names = {f.name for f in fields(cls)}
    optional = {f.name for f in fields(cls) if f.metadata.get("omit_none")}
    _require(type(value) is dict and names - optional <= set(value) <= names
             and all(value[name] is not None for name in optional & set(value)), 'STRATEGY_JSON_SCHEMA_INVALID')
    return dict(value)
```

- [ ] **Step 4: Run the strategy tests and the modules that encode protocols**

```bash
focus launch launch_strategy/
focus launch launch_study/
focus launch launch_capture/
focus launch launch_shortened_study/
```

Expected: every row `PASS`, exit 0 for each. `launch_study` proves study plans and commitments still encode and
parse with unchanged bytes.

- [ ] **Step 5: Commit**

```bash
git diff --stat -- execution_launch/strategy.py tests/launch_strategy.py
git diff --stat --ignore-cr-at-eol -- execution_launch/strategy.py tests/launch_strategy.py
git add execution_launch/strategy.py tests/launch_strategy.py
git commit -m "$(cat <<'EOF'
feat(launch): universe protocol field and forward-universe-v1 revision

ForwardProtocol.universe_rule_sha256 is left out of _plain/protocol_json while
None and optional in _object/parse_protocol; _protocol accepts
forward-universe-v1 only with a rule sha256 and the KRW-BTC benchmark symbol;
_rule_terms takes the protocol's selector; the fixed evaluator refuses the
universe revision (spec sections 10, 12, 14). Fixed protocol bytes pinned.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
)"
```

Expected: the two `--stat` outputs are identical before `git add`.

### Task 3: Program schema v2, kind `universe_top1_momentum`

**Files:**
- Modify: `execution_launch/program.py:9` (import), `:18-21` (constants), `:33-40` (`ProgramSpec`), `:50-60`
  (`_validate` head), `:70-76` (`_body`), `:111-117` (`parse_program`), `:135-136` (`target_fraction`)
- Create: `tests/launch_program.py`
- Modify: `tests/launch_acceptance.py:16` (last `MODULES` line once PR 2 added `launch_universe_store`; `:15` at
  fd85850)

**Interfaces:**
- Consumes: `strategy._plain` omit rule for `{"omit_none": True}` fields (Task 2).
- Produces:
  - `ProgramSpec.lookback_slots: int | None`, `min_hold_slots: int | None`, `switch_margin: Decimal | None`,
    `max_candidates: int | None`, `universe_rule_sha256: str | None`, each `= None` with metadata
    `{"omit_none": True}`; set (and validated) exactly when `kind == "universe_top1_momentum"` and
    `schema_version == 2`, with `fast_window == slow_window == 0`, `1 <= L, m, N <= 4096`, `switch_margin >= 0`,
    `0 < exposure_fraction <= 1`.
  - `parameters_json`, `program_json`, `program_digest` and `parse_program` accept schema v2; their output for
    existing kinds is unchanged.
  - `target_fraction(spec, marks)` raises `ProgramError("PROGRAM_KIND_UNSUPPORTED")` for the universe kind.
  - New refusal code `PROGRAM_UNIVERSE_PARAMETERS_INVALID`.

- [ ] **Step 1: Write the failing tests**

Create `tests/launch_program.py`:

```python
"""Program schema v2 and the universe chooser (spec section 14); invented values only, no market data."""
from dataclasses import replace
from decimal import Decimal, localcontext
import hashlib
import json

from execution_launch.program import (ProgramError, ProgramSpec, parameters_json, parse_program,
    program_digest, program_json, target_fraction)
from execution_launch.strategy import _plain, evidence_digest

D = Decimal
ARTIFACT = b"fixture-program-artifact"
RULE = hashlib.sha256(b"fixture-universe-rule").hexdigest()
TREND = ProgramSpec(schema_version=1, strategy_id="test-strategy", kind="moving_average_trend",
                    fast_window=2, slow_window=4, exposure_fraction=D("0.5"))
CASH = ProgramSpec(schema_version=1, strategy_id="fixture-cash", kind="cash", fast_window=0, slow_window=0,
                   exposure_fraction=D("0"))


def rotation(**changes):
    values = dict(schema_version=2, strategy_id="fixture-rotation", kind="universe_top1_momentum",
                  fast_window=0, slow_window=0, exposure_fraction=D("0.5"), lookback_slots=3,
                  min_hold_slots=2, switch_margin=D("0.01"), max_candidates=3, universe_rule_sha256=RULE)
    return ProgramSpec(**(values | changes))


def rejected(call, code=None):
    try:
        call()
    except ProgramError as exc:
        if code is not None:
            assert str(exc) == code, (str(exc), code)
        return
    raise AssertionError("expected program refusal")


def test_existing_kinds_keep_parameters_digests_and_plan_encoding_byte_for_byte():
    assert parameters_json(TREND) == ('{"exposure_fraction":"0.5","fast_window":2,"kind":"moving_average_trend",'
                                      '"schema_version":1,"slow_window":4,"strategy_id":"test-strategy"}')
    assert program_digest(TREND, ARTIFACT) == "19aefe2ec60beb021706e946813da7ac9c96802ebd72bc7c87c4fdf5739f9fff"
    assert program_digest(CASH, ARTIFACT) == "277aa374f681fc5c688ae28a4ed23d3cf148dbd27dfd83364598b94e78cf3d50"
    # Study plans and commitments encode programs through strategy._plain.
    assert evidence_digest(TREND) == "965a008190694d2821ffaaafff36e678bd474cb3495c4b0cbdcedb7a8cb9f433"
    assert sorted(_plain(TREND)) == ["exposure_fraction", "fast_window", "kind", "schema_version",
                                     "slow_window", "strategy_id"]
    for spec in (TREND, CASH):
        assert parse_program(program_json(spec)) == spec
        assert parse_program(json.dumps(_plain(spec))) == spec


def test_rotation_kind_is_schema_2_and_round_trips_through_every_encoding():
    spec = rotation()
    assert json.loads(parameters_json(spec)) == {
        "schema_version": 2, "strategy_id": "fixture-rotation", "kind": "universe_top1_momentum",
        "fast_window": 0, "slow_window": 0, "exposure_fraction": "0.5", "lookback_slots": 3,
        "min_hold_slots": 2, "switch_margin": "0.01", "max_candidates": 3, "universe_rule_sha256": RULE}
    assert parse_program(program_json(spec)) == spec
    assert parse_program(json.dumps(_plain(spec))) == spec
    digest = program_digest(spec, ARTIFACT)
    for changes in ({"lookback_slots": 4}, {"min_hold_slots": 3}, {"switch_margin": D("0.02")},
                    {"max_candidates": 2}, {"universe_rule_sha256": "f"*64}, {"exposure_fraction": D("0.4")}):
        assert program_digest(rotation(**changes), ARTIFACT) != digest, changes
    assert program_digest(rotation(switch_margin=D("0.010")), ARTIFACT) == digest


def test_rotation_parameters_are_validated_and_closed_to_the_other_kinds():
    for changes, code in (({"schema_version": 1}, "PROGRAM_SCHEMA_INVALID"),
                          ({"fast_window": 2}, "PROGRAM_UNIVERSE_PARAMETERS_INVALID"),
                          ({"lookback_slots": 0}, "PROGRAM_UNIVERSE_PARAMETERS_INVALID"),
                          ({"lookback_slots": True}, "PROGRAM_UNIVERSE_PARAMETERS_INVALID"),
                          ({"min_hold_slots": 0}, "PROGRAM_UNIVERSE_PARAMETERS_INVALID"),
                          ({"max_candidates": 0}, "PROGRAM_UNIVERSE_PARAMETERS_INVALID"),
                          ({"universe_rule_sha256": "F"*64}, "PROGRAM_UNIVERSE_PARAMETERS_INVALID"),
                          ({"universe_rule_sha256": None}, "PROGRAM_UNIVERSE_PARAMETERS_INVALID"),
                          ({"switch_margin": None}, "PROGRAM_DECIMAL_REQUIRED"),
                          ({"switch_margin": D("-0.01")}, "PROGRAM_AMOUNT_INVALID"),
                          ({"exposure_fraction": D("0")}, "PROGRAM_EXPOSURE_INVALID"),
                          ({"exposure_fraction": D("1.01")}, "PROGRAM_EXPOSURE_INVALID")):
        rejected(lambda changes=changes: parameters_json(rotation(**changes)), code)
    rejected(lambda: parameters_json(replace(TREND, schema_version=2)), "PROGRAM_SCHEMA_INVALID")
    rejected(lambda: parameters_json(replace(TREND, lookback_slots=3)), "PROGRAM_UNIVERSE_PARAMETERS_INVALID")
    rejected(lambda: target_fraction(rotation(), (D(1),)*8), "PROGRAM_KIND_UNSUPPORTED")
    body = json.loads(program_json(rotation()))
    for key in ("lookback_slots", "switch_margin", "universe_rule_sha256"):
        rejected(lambda key=key: parse_program(json.dumps({k: v for k, v in body.items() if k != key})),
                 "PROGRAM_JSON_SCHEMA_INVALID")
    rejected(lambda: parse_program(json.dumps(body | {"switch_margin": "1e-2"})), "PROGRAM_DECIMAL_STRING_REQUIRED")
    rejected(lambda: parse_program(json.dumps(body | {"switch_margin": None})), "PROGRAM_DECIMAL_STRING_REQUIRED")
    rejected(lambda: parse_program(json.dumps(body).replace('"0.01"', '0.01')), "PROGRAM_JSON_NUMBER_INVALID")
    trend = json.loads(program_json(TREND))
    rejected(lambda: parse_program(json.dumps(trend | {"lookback_slots": 3})), "PROGRAM_JSON_SCHEMA_INVALID")
    rejected(lambda: parse_program(json.dumps(trend | {k: v for k, v in body.items() if k not in trend})),
             "PROGRAM_UNIVERSE_PARAMETERS_INVALID")
```

Register the new module as the last entry of `MODULES` in `tests/launch_acceptance.py`. Run
`grep -n "launch_universe_store" tests/launch_acceptance.py` first.

If it prints a line (PR 2 is merged; the expected case), replace line 16:

```python
           "launch_universe_store")
```

with:

```python
           "launch_universe_store", "launch_program")
```

If it prints nothing (PR 2 is not merged yet), replace line 15 instead:

```python
           "launch_instrument_refresh", "launch_owner_ops", "owner_guards", "launch_owner_rehearsal")
```

with:

```python
           "launch_instrument_refresh", "launch_owner_ops", "owner_guards", "launch_owner_rehearsal",
           "launch_program")
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
focus launch launch_program/
```

Expected: exit 1. `PASS launch_program/test_existing_kinds_keep_parameters_digests_and_plan_encoding_byte_for_byte`
(it pins today's values and must stay green), and two `FAIL` rows,
`launch_program/test_rotation_...`, each with
`TypeError: ProgramSpec.__init__() got an unexpected keyword argument 'lookback_slots'`.

- [ ] **Step 3: Implement schema v2**

In `execution_launch/program.py`, replace line 9:

```python
from dataclasses import dataclass
```

with:

```python
from dataclasses import dataclass, field
```

In `execution_launch/program.py`, replace lines 18-21:

```python
_ID = re.compile(r"[A-Za-z][A-Za-z0-9_.:-]{0,95}")
_DECIMAL = re.compile(r"(?:0|[1-9][0-9]*)(?:\.[0-9]+)?")
MAX_PROGRAM_BYTES = 16384
MAX_MARKS = 20000
```

with:

```python
_ID = re.compile(r"[A-Za-z][A-Za-z0-9_.:-]{0,95}")
_DECIMAL = re.compile(r"(?:0|[1-9][0-9]*)(?:\.[0-9]+)?")
_SHA = re.compile(r"[0-9a-f]{64}")
MAX_PROGRAM_BYTES = 16384
MAX_MARKS = 20000
_UNIVERSE = "universe_top1_momentum"  # program schema v2 (spec section 14)
_UNIVERSE_FIELDS = ("lookback_slots", "min_hold_slots", "switch_margin", "max_candidates", "universe_rule_sha256")
_V1_KEYS = frozenset({"schema_version", "strategy_id", "kind", "fast_window", "slow_window", "exposure_fraction"})
_OMIT = {"omit_none": True}  # strategy._plain and strategy._object treat the field as absent while it is None
```

In `execution_launch/program.py`, replace lines 33-40:

```python
@dataclass(frozen=True, kw_only=True)
class ProgramSpec:
    schema_version: int
    strategy_id: str
    kind: str
    fast_window: int
    slow_window: int
    exposure_fraction: Decimal
```

with:

```python
@dataclass(frozen=True, kw_only=True)
class ProgramSpec:
    schema_version: int
    strategy_id: str
    kind: str
    fast_window: int
    slow_window: int
    exposure_fraction: Decimal
    # universe_top1_momentum only (schema 2): L, m, margin, N and the signed rule. None for every other kind.
    lookback_slots: int | None = field(default=None, metadata=_OMIT)
    min_hold_slots: int | None = field(default=None, metadata=_OMIT)
    switch_margin: Decimal | None = field(default=None, metadata=_OMIT)
    max_candidates: int | None = field(default=None, metadata=_OMIT)
    universe_rule_sha256: str | None = field(default=None, metadata=_OMIT)
```

In `execution_launch/program.py`, replace lines 50-60:

```python
def _validate(spec):
    _require(type(spec) is ProgramSpec and type(spec.schema_version) is int
             and spec.schema_version == 1, "PROGRAM_SCHEMA_INVALID")
    _require(type(spec.strategy_id) is str and _ID.fullmatch(spec.strategy_id) is not None,
             "PROGRAM_ID_INVALID")
    _require(type(spec.kind) is str, "PROGRAM_KIND_UNSUPPORTED")
    _require(type(spec.fast_window) is int and type(spec.slow_window) is int,
             "PROGRAM_WINDOW_INVALID")
    _decimal(spec.exposure_fraction)
    if spec.kind == "cash":
        _require(spec.fast_window == spec.slow_window == 0 and spec.exposure_fraction == 0,
```

with:

```python
def _validate(spec):
    universe = type(spec) is ProgramSpec and spec.kind == _UNIVERSE
    _require(type(spec) is ProgramSpec and type(spec.schema_version) is int
             and spec.schema_version == (2 if universe else 1), "PROGRAM_SCHEMA_INVALID")
    _require(type(spec.strategy_id) is str and _ID.fullmatch(spec.strategy_id) is not None,
             "PROGRAM_ID_INVALID")
    _require(type(spec.kind) is str, "PROGRAM_KIND_UNSUPPORTED")
    _require(type(spec.fast_window) is int and type(spec.slow_window) is int,
             "PROGRAM_WINDOW_INVALID")
    _decimal(spec.exposure_fraction)
    if universe:
        # L, m and N count slots, decisions and coins; 4096 is the moving-average window bound below.
        _require(spec.fast_window == spec.slow_window == 0
                 and all(type(value) is int and 1 <= value <= 4096
                         for value in (spec.lookback_slots, spec.min_hold_slots, spec.max_candidates))
                 and type(spec.universe_rule_sha256) is str
                 and _SHA.fullmatch(spec.universe_rule_sha256) is not None,
                 "PROGRAM_UNIVERSE_PARAMETERS_INVALID")
        _decimal(spec.switch_margin)
        _require(0 < spec.exposure_fraction <= 1, "PROGRAM_EXPOSURE_INVALID")
        return
    _require(all(getattr(spec, name) is None for name in _UNIVERSE_FIELDS),
             "PROGRAM_UNIVERSE_PARAMETERS_INVALID")
    if spec.kind == "cash":
        _require(spec.fast_window == spec.slow_window == 0 and spec.exposure_fraction == 0,
```

In `execution_launch/program.py`, replace lines 70-76:

```python
def _body(spec):
    _validate(spec)
    fraction = format(spec.exposure_fraction, "f")
    fraction = (fraction.rstrip("0").rstrip(".") if "." in fraction else fraction)
    return {"schema_version": spec.schema_version, "strategy_id": spec.strategy_id,
            "kind": spec.kind, "fast_window": spec.fast_window, "slow_window": spec.slow_window,
            "exposure_fraction": fraction if spec.exposure_fraction else "0"}
```

with:

```python
def _text(value):
    text = format(value, "f")
    text = (text.rstrip("0").rstrip(".") if "." in text else text)
    return text if value else "0"


def _body(spec):
    _validate(spec)
    body = {"schema_version": spec.schema_version, "strategy_id": spec.strategy_id,
            "kind": spec.kind, "fast_window": spec.fast_window, "slow_window": spec.slow_window,
            "exposure_fraction": _text(spec.exposure_fraction)}
    if spec.kind == _UNIVERSE:
        body |= {"lookback_slots": spec.lookback_slots, "min_hold_slots": spec.min_hold_slots,
                 "switch_margin": _text(spec.switch_margin), "max_candidates": spec.max_candidates,
                 "universe_rule_sha256": spec.universe_rule_sha256}
    return body
```

In `execution_launch/program.py`, replace lines 111-117:

```python
        _require(type(body) is dict and set(body) == {
            "schema_version", "strategy_id", "kind", "fast_window", "slow_window", "exposure_fraction"},
            "PROGRAM_JSON_SCHEMA_INVALID")
        value = body["exposure_fraction"]
        _require(type(value) is str and len(value) <= 72 and _DECIMAL.fullmatch(value) is not None,
                 "PROGRAM_DECIMAL_STRING_REQUIRED")
        spec = ProgramSpec(**(body | {"exposure_fraction": Decimal(value)}))
```

with:

```python
        # Schema 1 keys, or schema 1 keys plus every universe key (spec section 10: old set, or old plus new).
        _require(type(body) is dict and set(body) in (_V1_KEYS, _V1_KEYS | set(_UNIVERSE_FIELDS)),
                 "PROGRAM_JSON_SCHEMA_INVALID")
        decimals = {}
        for key in ("exposure_fraction", "switch_margin"):
            if key in body:
                value = body[key]
                _require(type(value) is str and len(value) <= 72 and _DECIMAL.fullmatch(value) is not None,
                         "PROGRAM_DECIMAL_STRING_REQUIRED")
                decimals[key] = Decimal(value)
        spec = ProgramSpec(**(body | decimals))
```

In `execution_launch/program.py`, replace lines 135-136:

```python
    _validate(spec)
    _require(type(marks) is tuple and len(marks) <= MAX_MARKS, "PROGRAM_HISTORY_INVALID")
```

with:

```python
    _validate(spec)
    _require(spec.kind != _UNIVERSE, "PROGRAM_KIND_UNSUPPORTED")  # the rotation decides through choose()
    _require(type(marks) is tuple and len(marks) <= MAX_MARKS, "PROGRAM_HISTORY_INVALID")
```

- [ ] **Step 4: Run the program tests and the modules that use programs**

```bash
focus launch launch_program/
focus launch launch_study/
focus launch launch_driver/
focus launch launch_workflow/
focus launch launch_review_request/
focus launch launch_capture/
```

Expected: every row `PASS`, exit 0 for each.

- [ ] **Step 5: Commit**

```bash
git diff --stat -- execution_launch/program.py tests/launch_acceptance.py
git diff --stat --ignore-cr-at-eol -- execution_launch/program.py tests/launch_acceptance.py
git add execution_launch/program.py tests/launch_program.py tests/launch_acceptance.py
git commit -m "$(cat <<'EOF'
feat(launch): program schema v2 kind universe_top1_momentum

ProgramSpec gains lookback_slots, min_hold_slots, switch_margin,
max_candidates and universe_rule_sha256 (None and left out for other kinds);
parse_program accepts the v1 key set or v1 plus the universe keys;
target_fraction refuses the rotation kind (spec section 14). Existing program
digests and plan encodings are pinned.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
)"
```

Expected: the two `--stat` outputs are identical before `git add`.

### Task 4: The chooser `choose()`

**Files:**
- Modify: `execution_launch/program.py:9` (import, as changed in Task 3) and append after line 143 (end of file at
  fd85850)
- Test: `tests/launch_program.py` (import lines from Task 3, new tests appended)

**Interfaces:**
- Consumes: `ProgramSpec` schema v2 and `_validate` (Task 3).
- Produces (index contract, exact):
  - `@dataclass(frozen=True) class ChooserState: held: str | None; hold_count: int`.
  - `@dataclass(frozen=True) class ChooserSlot: top_n: tuple[str, ...]; flags: Mapping[str, str];
    prices: Mapping[str, Decimal]` (`prices` holds defined prices only. An unavailable flag read gives empty `flags`
    and empty `prices`; an unavailable ticker read gives empty `prices` but keeps the flag classes of an available
    flag read, so rule 1 still sees a `warning`. Spec section 14 drops prices, not flags; PR 4d builds slots this
    way).
  - `choose(spec: ProgramSpec, state: ChooserState, now_slot: ChooserSlot, lag_slot: ChooserSlot | None)
    -> tuple[str | None, ChooserState]`; `lag_slot` is the slot `lookback_slots` before `now_slot`, or `None`.
  - Refusals: `PROGRAM_KIND_UNSUPPORTED` (not the rotation kind), `PROGRAM_CHOOSER_INPUT_INVALID` (state or slot
    shape, or `len(now_slot.top_n) > max_candidates`), `PROGRAM_DECIMAL_REQUIRED` / `PROGRAM_AMOUNT_INVALID` (a price
    that is not a positive finite `Decimal`).

- [ ] **Step 1: Write the failing tests**

In `tests/launch_program.py`, replace lines 7-8:

```python
from execution_launch.program import (ProgramError, ProgramSpec, parameters_json, parse_program,
    program_digest, program_json, target_fraction)
```

with:

```python
from execution_launch.program import (ChooserSlot, ChooserState, ProgramError, ProgramSpec, choose,
    parameters_json, parse_program, program_digest, program_json, target_fraction)
```

Append to the end of `tests/launch_program.py` (two blank lines before the first new line):

```python
COINS = ("KRW-AAA", "KRW-BBB", "KRW-CCC")
LAG = ChooserSlot(top_n=COINS, flags={coin: "unflagged" for coin in COINS}, prices={coin: D(100) for coin in COINS})
CASH_STATE = ChooserState(held=None, hold_count=3)


def at(prices, flags=None, top=COINS):
    """Slot k: decimal-string prices, every top-N coin unflagged unless flags says otherwise."""
    return ChooserSlot(top_n=top, flags={coin: "unflagged" for coin in top} if flags is None else flags,
                       prices={coin: D(value) for coin, value in prices.items()})


def held(coin, count=2):
    return ChooserState(held=coin, hold_count=count)


def decide(state, now, lag=LAG, **changes):
    """rotation() has L=3, m=2, switch_margin=0.01, N=3; LAG prices every coin at 100."""
    return choose(rotation(**changes), state, now, lag)


def test_rule_1_a_warning_on_the_held_coin_decides_cash_even_inside_the_minimum_hold():
    now = at({"KRW-AAA": "130", "KRW-BBB": "101"}, {"KRW-AAA": "warning", "KRW-BBB": "unflagged"})
    assert decide(held("KRW-AAA", 1), now) == (None, ChooserState(held=None, hold_count=1))
    unpriced = ChooserSlot(top_n=COINS, flags={"KRW-AAA": "warning"}, prices={})  # only the ticker read failed
    assert decide(held("KRW-AAA", 1), unpriced) == (None, ChooserState(held=None, hold_count=1))


def test_rule_2_a_held_coin_without_a_return_is_kept():
    for now, lag in ((at({"KRW-BBB": "150"}), LAG),                         # no price for the held coin now
                     (at({"KRW-AAA": "90", "KRW-BBB": "150"}), None),        # no slot L back yet
                     (ChooserSlot(top_n=COINS, flags={}, prices={}), LAG)):  # flag read unavailable
        assert decide(held("KRW-AAA"), now, lag) == ("KRW-AAA", ChooserState(held="KRW-AAA", hold_count=3))
    assert decide(held("KRW-ZZZ"), at({"KRW-BBB": "150"}))[0] == "KRW-ZZZ"   # left the top-N, still no return


def test_rule_3_best_is_the_largest_return_among_unflagged_top_n_coins_ties_by_symbol():
    flags = {"KRW-AAA": "caution", "KRW-BBB": "unflagged", "KRW-CCC": "unflagged"}
    now = at({"KRW-AAA": "200", "KRW-BBB": "110", "KRW-CCC": "110", "KRW-ZZZ": "300"}, flags)
    assert decide(CASH_STATE, now)[0] == "KRW-BBB"  # AAA is caution, ZZZ is outside the top-N, BBB ties CCC
    now = at({"KRW-AAA": "120", "KRW-CCC": "110"}, {**flags, "KRW-AAA": "unknown"})
    assert decide(CASH_STATE, now)[0] == "KRW-CCC"  # unknown is not unflagged; BBB has no price


def test_rule_4_from_cash_only_a_strictly_positive_best_is_bought():
    assert decide(CASH_STATE, at({"KRW-BBB": "101"})) == ("KRW-BBB", ChooserState(held="KRW-BBB", hold_count=1))
    assert decide(CASH_STATE, at({"KRW-BBB": "100", "KRW-CCC": "99"})) == (None, ChooserState(held=None, hold_count=4))
    assert decide(CASH_STATE, at({"KRW-BBB": "150"}), None)[0] is None       # warm-up: no lag slot, no target
    assert decide(ChooserState(held=None, hold_count=0), at({}))[0] is None  # window start with an empty read


def test_rule_5_the_minimum_hold_counts_decisions_and_comes_before_rules_6_and_7():
    now = at({"KRW-AAA": "90", "KRW-BBB": "150"})
    assert decide(held("KRW-AAA", 1), now) == ("KRW-AAA", ChooserState(held="KRW-AAA", hold_count=2))
    assert decide(held("KRW-AAA", 2), now) == ("KRW-BBB", ChooserState(held="KRW-BBB", hold_count=1))
    assert decide(held("KRW-AAA", 1), now, min_hold_slots=1)[0] == "KRW-BBB"


def test_rule_6_a_losing_hold_with_no_positive_target_goes_to_cash():
    assert decide(held("KRW-AAA"), at({"KRW-AAA": "99", "KRW-BBB": "100"})) == (
        None, ChooserState(held=None, hold_count=1))
    flags = {"KRW-AAA": "unflagged", "KRW-BBB": "caution", "KRW-CCC": "warning"}
    assert decide(held("KRW-AAA"), at({"KRW-AAA": "100", "KRW-BBB": "150", "KRW-CCC": "150"}, flags))[0] is None


def test_rule_7_switches_only_when_the_best_beats_the_held_return_by_more_than_the_margin():
    assert decide(held("KRW-AAA"), at({"KRW-AAA": "101", "KRW-BBB": "103"})) == (
        "KRW-BBB", ChooserState(held="KRW-BBB", hold_count=1))
    assert decide(held("KRW-AAA"), at({"KRW-AAA": "99", "KRW-BBB": "100.5"}))[0] == "KRW-BBB"


def test_rule_8_otherwise_the_held_coin_is_kept_including_a_caution_coin():
    assert decide(held("KRW-AAA"), at({"KRW-AAA": "101", "KRW-BBB": "102"})) == (
        "KRW-AAA", ChooserState(held="KRW-AAA", hold_count=3))       # a gap of exactly the margin keeps h
    flags = {"KRW-AAA": "caution", "KRW-BBB": "unflagged", "KRW-CCC": "unflagged"}
    assert decide(held("KRW-AAA"), at({"KRW-AAA": "110", "KRW-BBB": "105"}, flags))[0] == "KRW-AAA"
    assert decide(held("KRW-AAA"), at({"KRW-AAA": "110", "KRW-BBB": "102"}))[0] == "KRW-AAA"  # h is the best


def test_a_switch_path_counts_decisions_and_ignores_the_decimal_context():
    state, path = ChooserState(held=None, hold_count=0), []
    for prices in ({"KRW-AAA": "101"}, {"KRW-AAA": "101", "KRW-BBB": "120"}, {"KRW-AAA": "101", "KRW-BBB": "120"}):
        with localcontext() as numeric:
            numeric.prec = 2
            decision, state = decide(state, at(prices))
        path.append((decision, state.hold_count))
    assert path == [("KRW-AAA", 1), ("KRW-AAA", 2), ("KRW-BBB", 1)]


def test_chooser_refuses_other_kinds_bad_state_bad_prices_and_a_wider_candidate_set():
    rejected(lambda: choose(TREND, CASH_STATE, at({}), LAG), "PROGRAM_KIND_UNSUPPORTED")
    for state in (ChooserState(held=None, hold_count=-1), ChooserState(held=5, hold_count=1), (None, 0)):
        rejected(lambda state=state: decide(state, at({})), "PROGRAM_CHOOSER_INPUT_INVALID")
    rejected(lambda: decide(CASH_STATE, at({}, top=COINS+("KRW-DDD",))), "PROGRAM_CHOOSER_INPUT_INVALID")
    rejected(lambda: decide(CASH_STATE, at({"KRW-AAA": "0"})), "PROGRAM_AMOUNT_INVALID")
    rejected(lambda: decide(CASH_STATE, ChooserSlot(top_n=COINS, flags={}, prices={"KRW-AAA": 101.0})),
             "PROGRAM_DECIMAL_REQUIRED")
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
focus launch launch_program/
```

Expected: exit 1 with one row,
`FAIL launch_program/import ImportError: cannot import name 'ChooserSlot' from 'execution_launch.program'`.

- [ ] **Step 3: Implement the chooser**

In `execution_launch/program.py`, replace line 9 (as changed in Task 3):

```python
from dataclasses import dataclass, field
```

with:

```python
from collections.abc import Mapping
from dataclasses import dataclass, field
```

Append to the end of `execution_launch/program.py` (two blank lines before the first new line):

```python
@dataclass(frozen=True)
class ChooserState:
    """The decided path so far (spec section 14): held is h (None is cash) and hold_count the number of
    consecutive decisions for h. A window starts at ChooserState(held=None, hold_count=0)."""
    held: str | None
    hold_count: int


@dataclass(frozen=True)
class ChooserSlot:
    """One recorded slot: the top-N of the snapshot in force, each market's flag class and the defined trade
    prices only. An unavailable flag read gives empty flags and prices; an unavailable ticker read gives empty
    prices and keeps the flags (spec section 14 drops prices, so rule 1 still applies)."""
    top_n: tuple[str, ...]
    flags: Mapping[str, str]
    prices: Mapping[str, Decimal]


def choose(spec: ProgramSpec, state: ChooserState, now_slot: ChooserSlot,
           lag_slot: ChooserSlot | None) -> tuple[str | None, ChooserState]:
    """One universe_top1_momentum decision by spec section 14 rules 1-8: (coin, or None for cash; new state).

    lag_slot is the slot lookback_slots before now_slot, or None when there is none. r_X = price_X(now) /
    price_X(lag) - 1 is defined only when both prices are. Only these recorded values and the decided path are
    read, never fills or holdings. Exact fractions keep the result independent of the decimal context.
    """
    _validate(spec)
    _require(spec.kind == _UNIVERSE, "PROGRAM_KIND_UNSUPPORTED")
    slots = (now_slot,) if lag_slot is None else (now_slot, lag_slot)
    _require(type(state) is ChooserState and (state.held is None or type(state.held) is str)
             and type(state.hold_count) is int and state.hold_count >= 0
             and all(type(slot) is ChooserSlot and type(slot.top_n) is tuple and isinstance(slot.flags, Mapping)
                     and isinstance(slot.prices, Mapping) for slot in slots)
             and len(now_slot.top_n) <= spec.max_candidates, "PROGRAM_CHOOSER_INPUT_INVALID")
    for slot in slots:
        for price in slot.prices.values():
            _decimal(price, positive=True)

    def ret(coin):
        if lag_slot is None or coin not in now_slot.prices or coin not in lag_slot.prices:
            return None
        return Fraction(now_slot.prices[coin]) / Fraction(lag_slot.prices[coin]) - 1

    h = state.held
    targets = [(ret(coin), coin) for coin in now_slot.top_n
               if now_slot.flags.get(coin) == "unflagged" and ret(coin) is not None]
    best_r, best = min(targets, key=lambda item: (-item[0], item[1])) if targets else (None, None)
    r_h = None if h is None else ret(h)
    if h is not None and now_slot.flags.get(h) == "warning":
        decision = None                                                      # rule 1
    elif h is not None and r_h is None:
        decision = h                                                         # rule 2
    elif h is None:
        decision = best if best is not None and best_r > 0 else None         # rules 3 and 4
    elif state.hold_count < spec.min_hold_slots:
        decision = h                                                         # rule 5
    elif r_h <= 0 and (best is None or best_r <= 0):
        decision = None                                                      # rule 6
    elif best is not None and best != h and best_r > 0 and best_r - r_h > Fraction(spec.switch_margin):
        decision = best                                                      # rule 7
    else:
        decision = h                                                         # rule 8
    return decision, ChooserState(held=decision, hold_count=state.hold_count + 1 if decision == h else 1)
```

- [ ] **Step 4: Run the program tests**

```bash
focus launch launch_program/
```

Expected: every `launch_program/...` row `PASS` (13 rows), exit 0.

- [ ] **Step 5: Commit**

```bash
git diff --stat -- execution_launch/program.py tests/launch_program.py
git diff --stat --ignore-cr-at-eol -- execution_launch/program.py tests/launch_program.py
git add execution_launch/program.py tests/launch_program.py
git commit -m "$(cat <<'EOF'
feat(launch): universe chooser for universe_top1_momentum

ChooserState, ChooserSlot and choose() implement spec section 14 rules 1-8
over recorded slot values with exact fractions; the hold count counts
decisions. Every rule has a test.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
)"
```

Expected: the two `--stat` outputs are identical before `git add`.

### Task 5: The selector at every computing site and the universe `_bound_profile`

**Files:**
- Modify: `execution_launch/instrument_refresh.py:75-76`, `execution_launch/runner.py:150-151`,
  `execution_launch/driver.py:166`, `execution_launch/workflow.py:173-181` and `:207-208`,
  `execution_launch/study.py:247` and `:479`, `execution_launch/study_review.py:87`,
  `execution_launch/review_request.py:242`, `tools/research/prepare_launch_example.py:70`
- Test: `tests/launch_profile.py`, `tests/launch_workflow.py` (after line 323),
  `tests/launch_instrument_refresh.py` (after line 419)

**Interfaces:**
- Consumes: `rule_terms_digest(rules, *, universe_rule_sha256=None)`, `LaunchProfile.universe_rule_sha256`
  (Task 1); `ForwardProtocol.universe_rule_sha256`, `UNIVERSE_EVALUATOR_REVISION` (Task 2).
- Produces:
  - `workflow._bound_profile(profile, protocol) -> None`: for a protocol with `universe_rule_sha256` set it compares
    venue, market, quote currency, strategy id and `universe_rule_sha256` (not the symbol), plus the existing code,
    contract, rule-terms and capital checks; a fixed protocol keeps today's symbol check. Refusal stays
    `WORKFLOW_PROFILE_PROTOCOL_MISMATCH`.
  - Every `rule_terms_digest` call in `execution_launch` and `tools` passes `universe_rule_sha256=`.

- [ ] **Step 1: Write the failing tests**

Append to the end of `tests/launch_profile.py` (two blank lines before the first new line):

```python
def test_every_rule_terms_digest_call_passes_the_universe_selector():
    import ast
    root = Path(__file__).resolve().parents[1]
    calls = []
    for path in sorted((root/"execution_launch").rglob("*.py")) + sorted((root/"tools").rglob("*.py")):
        for node in ast.walk(ast.parse(path.read_bytes())):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                    and node.func.id in ("rule_terms_digest", "economic_rules_digest")):
                calls.append((path.relative_to(root).as_posix(), node.lineno,
                              any(k.arg == "universe_rule_sha256" for k in node.keywords)))
    assert len(calls) >= 12, calls  # the 12 calls at the spec section 10 sites; fewer means the scan collapsed
    assert all(selected for _, _, selected in calls), [call for call in calls if not call[2]]
```

Append to the end of `tests/launch_workflow.py` (two blank lines before the first new line):

```python
def test_universe_protocol_binds_the_rule_instead_of_the_trade_coin():
    from execution_launch.profile import rule_terms_digest
    from execution_launch.strategy import UNIVERSE_EVALUATOR_REVISION
    profile, protocol, _, _ = fixture()
    rule = hashlib.sha256(b'fixture-universe-rule').hexdigest()
    universe = replace(profile, universe_rule_sha256=rule)
    bound = replace(protocol, evaluator_revision=UNIVERSE_EVALUATOR_REVISION, universe_rule_sha256=rule,
                    profile_contract_digest=profile_contract_digest(universe),
                    rule_terms_digest=rule_terms_digest(universe.instrument_rules, universe_rule_sha256=rule))
    moved = replace(universe, symbol='KRW-ETH',
                    instrument_rules=replace(universe.instrument_rules, symbol='KRW-ETH', tick_size=D('5')))
    for accepted in ((universe, bound), (moved, bound), (profile, protocol)):
        W._bound_profile(*accepted)
    fee = replace(moved, instrument_rules=replace(moved.instrument_rules, fee_fraction=D('0.0005')))
    fixed_moved = replace(profile, symbol='KRW-ETH',
                          instrument_rules=replace(profile.instrument_rules, symbol='KRW-ETH'))
    for refused in ((replace(moved, universe_rule_sha256='f'*64), bound), (fee, bound),
                    (universe, protocol), (profile, bound), (fixed_moved, protocol)):
        try:
            W._bound_profile(*refused)
        except W.WorkflowError as exc:
            assert str(exc) == 'WORKFLOW_PROFILE_PROTOCOL_MISMATCH'
        else:
            raise AssertionError('mismatched profile and protocol accepted')
```

Append to the end of `tests/launch_instrument_refresh.py` (two blank lines before the first new line):

```python
def test_universe_profile_renews_across_a_tick_change_and_keeps_its_contract():
    with registries():
        rule = hashlib.sha256(b"fixture-universe-rule").hexdigest()
        p = replace(profile(), universe_rule_sha256=rule)
        stale = replace(p, instrument_rules=replace(p.instrument_rules, tick_size=D("5")))
        o = observed()
        r = R.renew_profile(stale, o, now=o.checked_at)
        assert r.profile.instrument_rules.tick_size == D("1") and r.profile.universe_rule_sha256 == rule
        assert profile_contract_digest(r.profile) == profile_contract_digest(stale)
        assert R.validate_renewal(r, previous_profile=stale, now=o.checked_at) == r.profile
        fee = replace(p, instrument_rules=replace(p.instrument_rules, fee_fraction=D("0.002")))
        refused(lambda: R.renew_profile(fee, o, now=o.checked_at), "RENEWAL_ECONOMIC_OR_SOURCE_CHANGE")
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
focus launch launch_profile/test_every_rule_terms_digest_call
focus launch launch_workflow/test_universe_protocol_binds
focus launch launch_instrument_refresh/test_universe_profile_renews
```

Expected: exit 1 each. The first prints an `AssertionError` listing the 11 calls still without the selector (the
twelfth, `execution_launch/strategy.py` `_rule_terms`, passes it since Task 2), starting
`[('execution_launch/driver.py', 166, False), ('execution_launch/instrument_refresh.py', 75, False), ...`; the second
prints `WorkflowError: WORKFLOW_PROFILE_PROTOCOL_MISMATCH`; the third prints
`RenewalError: RENEWAL_ECONOMIC_OR_SOURCE_CHANGE`.

- [ ] **Step 3: Pass the selector at every site**

In `execution_launch/instrument_refresh.py`, replace lines 75-76:

```python
    _require(rule_terms_digest(profile.instrument_rules) == rule_terms_digest(verified.rules),
             "RENEWAL_ECONOMIC_OR_SOURCE_CHANGE")
```

with:

```python
    # Both sides use the old profile's selector (spec section 10).
    _require(rule_terms_digest(profile.instrument_rules, universe_rule_sha256=profile.universe_rule_sha256)
             == rule_terms_digest(verified.rules, universe_rule_sha256=profile.universe_rule_sha256),
             "RENEWAL_ECONOMIC_OR_SOURCE_CHANGE")
```

In `execution_launch/runner.py`, replace lines 150-151:

```python
        profile_contract_digest=profile_contract_digest(profile),
        rule_terms_digest=rule_terms_digest(profile.instrument_rules),
```

with:

```python
        profile_contract_digest=profile_contract_digest(profile),
        rule_terms_digest=rule_terms_digest(profile.instrument_rules,
                                            universe_rule_sha256=profile.universe_rule_sha256),
```

In `execution_launch/driver.py`, replace line 166:

```python
    terms = rule_terms_digest(profile.instrument_rules)
```

with:

```python
    terms = rule_terms_digest(profile.instrument_rules, universe_rule_sha256=profile.universe_rule_sha256)
```

In `execution_launch/workflow.py`, replace lines 173-181:

```python
def _bound_profile(profile, protocol):
    _require(profile.instrument_rules is not None, 'WORKFLOW_INSTRUMENT_RULES_REQUIRED')
    _require((profile.venue, profile.market, profile.symbol, profile.quote_currency, profile.strategy_id)
             == (protocol.venue, protocol.market, protocol.symbol, protocol.quote_currency, protocol.strategy_id)
             and profile.strategy_code_sha256 == protocol.strategy_code_sha256
             and profile_contract_digest(profile) == protocol.profile_contract_digest
             and rule_terms_digest(profile.instrument_rules) == protocol.rule_terms_digest
             and profile.policy.initial_equity == protocol.initial_cash_quote,
             'WORKFLOW_PROFILE_PROTOCOL_MISMATCH')
```

with:

```python
def _bound_profile(profile, protocol):
    """A universe protocol binds the signed rule instead of a coin: the profile's symbol is its current trade coin
    and the protocol's symbol is the KRW-BTC benchmark (spec sections 10 and 12)."""
    _require(profile.instrument_rules is not None, 'WORKFLOW_INSTRUMENT_RULES_REQUIRED')
    universe = protocol.universe_rule_sha256 is not None
    _require((profile.venue, profile.market, profile.quote_currency, profile.strategy_id,
              profile.universe_rule_sha256)
             == (protocol.venue, protocol.market, protocol.quote_currency, protocol.strategy_id,
                 protocol.universe_rule_sha256)
             and (universe or profile.symbol == protocol.symbol)
             and profile.strategy_code_sha256 == protocol.strategy_code_sha256
             and profile_contract_digest(profile) == protocol.profile_contract_digest
             and rule_terms_digest(profile.instrument_rules, universe_rule_sha256=profile.universe_rule_sha256)
             == protocol.rule_terms_digest
             and profile.policy.initial_equity == protocol.initial_cash_quote,
             'WORKFLOW_PROFILE_PROTOCOL_MISMATCH')
```

In `execution_launch/workflow.py`, replace lines 207-208:

```python
        profile_contract_digest=profile_contract_digest(profile),
        rule_terms_digest=rule_terms_digest(profile.instrument_rules),
```

with:

```python
        profile_contract_digest=profile_contract_digest(profile),
        rule_terms_digest=rule_terms_digest(profile.instrument_rules,
                                            universe_rule_sha256=profile.universe_rule_sha256),
```

`execution_launch/study.py` is CRLF: every replaced and new line below ends in `\r\n` in the file (use the Edit tool
or Python on bytes, never `sed -i`; the Step 5 `--stat` pair shows a converted file).

In `execution_launch/study.py`, replace line 247:

```python
    terms, candidates = rule_terms_digest(profile.instrument_rules), []
```

with:

```python
    terms = rule_terms_digest(profile.instrument_rules, universe_rule_sha256=profile.universe_rule_sha256)
    candidates = []
```

In `execution_launch/study.py`, replace line 479:

```python
    artifact, terms = _fixed_file(PROGRAM_SOURCE), rule_terms_digest(profile.instrument_rules)
```

with:

```python
    artifact = _fixed_file(PROGRAM_SOURCE)
    terms = rule_terms_digest(profile.instrument_rules, universe_rule_sha256=profile.universe_rule_sha256)
```

In `execution_launch/study_review.py`, replace line 87:

```python
        "rule_terms_digest": rule_terms_digest(profile.instrument_rules),
```

with:

```python
        "rule_terms_digest": rule_terms_digest(profile.instrument_rules,
                                               universe_rule_sha256=profile.universe_rule_sha256),
```

In `execution_launch/review_request.py`, replace line 242:

```python
        terms = rule_terms_digest(profile.instrument_rules)
```

with:

```python
        terms = rule_terms_digest(profile.instrument_rules, universe_rule_sha256=profile.universe_rule_sha256)
```

In `tools/research/prepare_launch_example.py`, replace line 70:

```python
        rule_terms_digest=rule_terms_digest(rules), venue='upbit', market='spot', symbol='KRW-BTC',
```

with:

```python
        rule_terms_digest=rule_terms_digest(rules, universe_rule_sha256=profile.universe_rule_sha256),
        venue='upbit', market='spot', symbol='KRW-BTC',
```

- [ ] **Step 4: Run the focused tests and every module that owns a changed site**

```bash
focus launch launch_profile/
focus launch launch_workflow/
focus launch launch_instrument_refresh/
focus launch launch_runner/
focus launch launch_driver/
focus launch launch_study/
focus launch launch_study_review/
focus launch launch_review_request/
focus launch launch_shortened_study/
focus launch launch_coordinator/
focus launch launch_live_history/
```

Expected: every row `PASS`, exit 0 for each.

- [ ] **Step 5: Commit**

```bash
FILES="execution_launch/instrument_refresh.py execution_launch/runner.py execution_launch/driver.py execution_launch/workflow.py execution_launch/study.py execution_launch/study_review.py execution_launch/review_request.py tools/research/prepare_launch_example.py tests/launch_profile.py tests/launch_workflow.py tests/launch_instrument_refresh.py"
git diff --stat -- $FILES
git diff --stat --ignore-cr-at-eol -- $FILES
git add $FILES
git commit -m "$(cat <<'EOF'
feat(launch): universe selector at every rule-terms site and _bound_profile

instrument_refresh (both sides, old profile), runner, driver, workflow,
study, study_review, review_request and the example tool pass
universe_rule_sha256 to rule_terms_digest; _bound_profile binds the rule
instead of the coin for a universe protocol (spec section 10). An AST test
keeps every call site on the selector.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
)"
```

Expected: the two `--stat` outputs are identical before `git add`.

### Task 6: Guards, full suite and pull request

**Files:**
- No code change. Read-only checks, then push and open the PR.

**Interfaces:**
- Consumes: Tasks 1 to 5.
- Produces: one PR against `main` that the owner reviews and merges.

- [ ] **Step 1: Run the guard modules**

```bash
focus compliance compliance_guards/
focus control control_guards/
focus accounts accounts_guards/
focus launch launch_guards/
focus execution execution_guards/
```

Expected: every row `PASS`, exit 0 for each. `control_guards/test_renewal_*` runs `tests/renewal_boundaries.py`
with the Task 1 pin; `launch_guards/test_launch_suite_is_complete_registered_and_import_errors_fail` sees
`launch_program` in `MODULES`. Two known checkout-location rows require the interpreter to be the checkout's own
`.venv`: `compliance_guards/test_cryptography_is_pinned_installed_and_usable` (`tests/compliance_guards.py:583-584`,
"cryptography loaded from ...TRADEGEN_PR9\.venv\..., not .venv") and, in the full suite only,
`compliance_signer/test_commands_sign_exactly_what_was_shown` (`tests/compliance_signer.py:950`). They pass in the
`TRADEGEN_PR9` checkout itself and fail identically on unmodified `origin/main` anywhere else; those two rows with
exactly those messages are the only allowed FAIL rows, and the PR body then names them under "Not verified here".

- [ ] **Step 2: Run the full suite**

```bash
"$PY" -X utf8 -m tests.run_all
git restore qa/acceptance_results.json
```

Expected: the last line of the run reads `<n>/<m> passed, <f> failed, <k> not run; ...qa/acceptance_results.json`
with `<f>` 0, or only the two checkout-location rows of Step 1 (NOT_RUN rows are allowed and listed with their
reason). `qa/acceptance_results.json` is tracked and every full run rewrites it, so `git restore` puts the committed
record back: this PR does not commit it. For any other FAIL row, check it on `origin/main` in a separate worktree:

```bash
git worktree add --detach ../pr4b-main-check origin/main
(cd ../pr4b-main-check && focus <suite> <module>/<test_name>)
git worktree remove ../pr4b-main-check
```

A row that fails there too is pre-existing: name it under "Not verified here" in the PR body and do not fix it in
this PR. A row that fails only on this branch is a defect of this PR: fix it in a new task before opening the PR. PR 0
recorded one such pre-existing row on unmodified fd85850,
`launch_owner_ops/test_runtime_worker_runs_once_and_closes_with_bounded_lifecycle` (a worker thread still alive after
its 10-second join, `tests/launch_owner_ops.py:239-240`); confirm it the same way.

- [ ] **Step 3: Check line endings and the branch diff**

```bash
git status --short
git log --oneline origin/main..HEAD
git diff --stat origin/main...HEAD
git diff --stat --ignore-cr-at-eol origin/main...HEAD
```

Expected: `git status --short` lists no tracked change (untracked `docs/superpowers` spec and plan files may be
listed with `??`; they are never committed by this plan); five commits; the two `--stat` outputs are identical and
list exactly the 18 files of Tasks 1 to 5 (`execution_launch/` driver, instrument_refresh, profile, program,
review_request, runner, strategy, study, study_review, workflow; `tests/` launch_acceptance, launch_instrument_refresh,
launch_profile, launch_program, launch_strategy, launch_workflow, renewal_boundaries;
`tools/research/prepare_launch_example.py`).

- [ ] **Step 4: Push and open the PR (the owner merges; never merge with tools)**

Before running the command, adjust the body's "Not verified here" list: delete the bullet on the two
checkout-location tests if both passed in Steps 1 and 2, and add one bullet per pre-existing failure confirmed on
`origin/main` in Step 2, in the form `- <module>/<test_name> fails on unmodified main too (<one-line reason>).`

```bash
git push -u origin claude/universe-pr4b-profile-program
gh pr create --base main --head claude/universe-pr4b-profile-program \
  --title "Upbit KRW universe PR 4b: universe profile, protocol digests and rotation program" \
  --body "$(cat <<'EOF'
## Summary

- `LaunchProfile.universe_rule_sha256` and `ForwardProtocol.universe_rule_sha256` (spec sections 10 and 12). Both
  are `None` for fixed KRW-BTC profiles and protocols and left out of every canonical encoding, so for the same
  inputs the fixed profile, contract, rule-terms, protocol and program digests are byte-identical to `main` (pinned
  in tests against fixed fixtures and a fixed artifact).
- Universe forms of `profile_contract_digest` and `rule_terms_digest(rules, *, universe_rule_sha256=None)`: the
  trade coin's symbol, tick and asof are left out and the rule sha256 is bound. Every computing site passes the
  selector (instrument_refresh on both sides with the old profile, runner, driver, workflow, study, study_review,
  review_request, the example tool, and the evaluator's `_rule_terms`).
- `workflow._bound_profile` binds venue, market, quote, strategy id and the rule sha256 instead of the symbol for
  a universe protocol.
- `_protocol` accepts `forward-universe-v1` only together with a rule sha256 and the `KRW-BTC` benchmark symbol;
  the fixed evaluator `run_paper_validation` refuses that revision.
- Program schema v2 kind `universe_top1_momentum` and the chooser `choose()` (spec section 14, rules 1 to 8, the
  hold count counts decisions). `target_fraction` refuses the new kind.

## Tests added

- `tests/launch_profile.py`: fixed digests pinned; universe round trip; same rules give different fixed and
  universe digests; the universe contract and rule terms are stable across symbol, tick and asof and move with
  lot, minimums, fees, source digest and rule sha256; an AST scan that every `rule_terms_digest` call passes the
  selector.
- `tests/launch_strategy.py`: fixed protocol digest and JSON bytes pinned; universe protocol round trip and
  refusals; the fixed evaluator refuses the universe revision.
- `tests/launch_program.py` (new, in `MODULES`): existing program digests and plan encoding pinned; schema v2
  round trip and validation; one test per chooser rule, a decision path and decimal-context independence.
- `tests/launch_workflow.py`, `tests/launch_instrument_refresh.py`: universe `_bound_profile`; a universe profile
  renews across a tick change with an unchanged contract digest.
- `tests/renewal_boundaries.py`: the `execution_launch/profile.py` surface pin is updated by hand after review (one
  new field, one new keyword-only parameter).

## Not verified here

- No universe evaluator, capture, driver, LiveHistory or coordinator use yet (PR 4c, PR 4d, PR 4e, PR 5); nothing
  in this PR can produce qualified universe evidence or a universe session.
- `compliance_guards/test_cryptography_is_pinned_installed_and_usable` and
  `compliance_signer/test_commands_sign_exactly_what_was_shown` were run from a checkout without its own `.venv`,
  where they fail on unmodified `main` too (they require the checkout's own interpreter).

## Effect on deployments (owner acts after merge)

- Merge only after any in-flight KRW-BTC study or window has finished (spec section 12).
- `program.py` is the program artifact, so `program_digest` over the installed file, the `strategy_code_sha256` of
  every real profile and protocol, changes: a new profile and protocol are needed.
- `study.py`, `program.py` and `strategy.py` are in `CAPTURE_FILES`, so `capture_source_code_sha256` changes and a
  frozen or in-flight study capture no longer binds.
- The driver identity covers the changed `profile.py`, `program.py`, `strategy.py`, `runner.py` and `driver.py`, so
  a new history window (GENESIS) and a new strategy review are needed before any live window.
- Every changed `execution_launch` file is in the compliance code hash, so code-approve runs on the merged head.

This is software design, not legal, tax or investment advice.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

Expected: `gh` prints the PR URL. Report it to the owner and stop; the owner reviews and merges.
