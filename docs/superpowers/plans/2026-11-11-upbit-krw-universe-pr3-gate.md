# Upbit KRW universe PR 3: gate, read-back and public lookup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let the compliance gate decide derived Upbit KRW coins: held-coin KRW exits with no snapshot, buys only
under the signed `universe_rule` with the coin eligible in the snapshot that `load_context` reads back, and recorded
orders (cancel, dispatch) whatever the snapshot state.

**Architecture:** `Context.universe` carries the verified snapshot in force. It is hashed into `ctx_hash` only when
set, through one new `model.context_hash`. `owner.load_context` fills it through `_universe_in_force`, which never
raises. A public `gate.lookup` resolves a symbol that no signed map lists to a copy of the signed BTC entry under
three conditions only: a recorded order, an exit of a held coin, or new exposure under the rule. Step 5 then
requires the snapshot and eligibility. The controller and the odds plan switch to `gate.lookup`, and
`gate.market_listed` lists a derived coin against KRW only.

**Tech Stack:** Python 3.13 (venv at `TRADEGEN_PR9/.venv`, read-only), stdlib only (`dataclasses`, `datetime`,
`decimal`, `json`, `hashlib`, `base64`). The repo's own compliance, odds and execution_control modules. No new
dependency.

**Spec:** [2026-11-11-upbit-krw-universe-design.md](../specs/2026-11-11-upbit-krw-universe-design.md), sections 5
(read-back only), 8, 18 (compliance-spec amendments) and the 19 "snapshot" read-back and "gate" tests.

## Global Constraints

All constraints in the index apply:
[2026-11-11-upbit-krw-universe-index.md](2026-11-11-upbit-krw-universe-index.md) (Global constraints, Running tests,
Interface contract, Task conventions).

### PR-specific constraints (verbatim from the spec)

- "Symbols in a signed instrument map keep today's path, unchanged." (spec 8)
- "**Exits never need a snapshot.** A cash sell for KRW on upbit of a coin held per `ctx.holdings`, whose symbol
  matches the pattern, resolves to a derived coin instrument in both the active state and the recovery snapshot,
  whatever the venue facts say." (spec 8)
- "The derived instrument copies the signed BTC entry's fields (`crypto_coin` x1, class `coin`, `crypto_venue`, KRW,
  `crypto_22pct_from_2027`). The quantity is checked by the existing `_within_free`. A later venues approval that
  drops `universe_rule` therefore never traps a held coin." (spec 8)
- "**New exposure** on a derived coin needs a venue whose signed facts carry `universe_rule`, `ctx.universe` in
  force, and the symbol in `eligible`. Otherwise BLOCK `state: universe <reason>`." (spec 8)
- "For an order already recorded in the journal, the lookup resolves the derived instrument whatever its side and the
  snapshot state, so a protective cancel is never refused. Only `reserve` and `dispatch` of a buy need the
  snapshot." (spec 8)
- "`_retired` is false for an eligible coin. The market test accepts (coin, rule quote)." (spec 8)
- "`gate.py:257` (`_transfer`) stays on the signed maps: a transfer of a derived coin stays blocked." (spec 8)
- "Fixed in code: KRW quote only, and the base symbol must match `[A-Z][A-Z0-9]{0,11}`" (spec 4)
- "At most one snapshot is in force at any instant: the one for the day whose window contains `now`. If several
  files for that day verify (a manual rebuild), the earliest built wins." (spec 5)
- "`valid_from = max(built_at, D 00:40 UTC)` and `valid_until = D+1 00:40 UTC` (09:40 KST)." (spec 5)
- "The read-back catches every exception and returns `None`; it can never break the context, so exits never depend
  on it. Verification results are cached in-process by file sha256." (spec 5)
- "`execution_launch` keeps its ban on referencing `load_context`." (spec 6)
- "`Context.universe: Universe | None = None`, sealed into `ctx_hash` only when not `None`." (index, PR 3 contract)

### PR-specific notes

- Line numbers below are at fd85850. PR 1 adds code to `core/compliance/model.py`, `owner.py`, `rules.py` and
  possibly `tests/compliance_fixtures.py`, and appends `"compliance_universe"` to the compliance `MODULES` tuple, so
  every edit names the exact current text to find. Edit with the Edit tool only, never `sed -i`.
- `core/compliance/gate.py` must stay free of the text `datetime` and `ZoneInfo` and of every name in
  `_T9_FORBIDDEN` (`tests/compliance_gate.py:1110-1114`, for example `now`, `time`, `open`), comments and docstrings
  included (`test_gate_call_graph_has_no_clock_zone_file_or_socket`).
- `docs/superpowers/specs/2026-10-23-compliance-gate-and-odds-engine-design.md` is LF at fd85850 (0 CR bytes),
  although the index says specs are CRLF. Keep it LF.
- The execution_control and execution_launch files keep their own code style (the controller's compact
  `a=b` lines stay compact).

### Deviations from the index Interface contract (PR 3, gate)

The index must be updated to match; later plans follow this list, not the index text.

- `gate.lookup(ctx, state, venue, symbol, exits, *, recorded=False) -> rules.Instrument | None`, where `state` is a
  `model.ApprovedState` and `venue` is that state's `rules.Venue`, replaces the index's
  `lookup(ctx, venue: str, symbol: str, exits: bool)`. Reason: `gate.decide` looks symbols up in `ctx.active` or, in
  recovery, `ctx.snapshot`, so `ctx` alone cannot name the state; every caller (gate, controller, odds plan) already
  holds the state and the `Venue`; and spec 8's recorded-order path needs `recorded`. The return type is today's
  `_lookup`'s, as the index says.
- New public names the index does not list: `gate.market_listed(state, venue, inst, counter) -> bool` and
  `model.context_hash(ctx) -> str` (`execution_launch/profile.py` and `review_auth.py` import `model` as
  `compliance`, so they call it as `compliance.context_hash`).
- `owner._universe_in_force(now, rule_sha256)` is as the index says; `owner._universe_now(now, active)` wraps it and
  `owner._UNIVERSE_VERIFIED` is the cache.
- `execution_control/controller.py` changes at lines 513 (`_intent` signature), 519, 584, 641 (`_authorize`) and 754
  (`cancel`), not only at 519 and 584 as the PR 4a plan assumes. PR 4a must match those by quoted text.

---

## File Structure

| File | Change | Responsibility |
|---|---|---|
| `core/compliance/model.py` | Modify | `Context.universe`; `context_hash(ctx)`, the single hash rule `seal_context` and every integrity check use |
| `execution_accounts/readiness.py` | Modify | KIS context integrity check uses `model.context_hash` |
| `execution_launch/profile.py` | Modify | Preflight context integrity check uses `compliance.context_hash` |
| `execution_launch/review_auth.py` | Modify | Review authority context check uses `compliance.context_hash` |
| `core/compliance/gate.py` | Modify | `lookup`, `market_listed`, `_derived`, `_universe`; `_retired`; call sites in `_decide`, `_validate`, `_screen`, `grey_rows` |
| `core/compliance/owner.py` | Modify | `_universe_now`, `_universe_in_force`, `_UNIVERSE_VERIFIED`; `load_context` passes `now` to `_context` |
| `execution_control/controller.py` | Modify | `_intent(..., recorded=)` through `gate.lookup`; `_authorize`, `cancel`, `_exact_caps` |
| `core/odds/plan.py` | Modify | `instrument()` through `gate.lookup`; the market check through `gate.market_listed` |
| `docs/superpowers/specs/2026-10-23-compliance-gate-and-odds-engine-design.md` | Modify | Amend 5.1, 5.2, 6.1, 6.2 (spec 18) |
| `tests/compliance_fixtures.py` | Modify | `universe_venues_raw`, `universe_rule`, `universe` (Task 1); `universe_receipts`, `_candle`, `universe_file` (Task 3) |
| `tests/compliance_model.py` | Modify | Context field case and the hash-only-when-set test |
| `tests/compliance_universe_gate.py` | Create | Gate tests (Task 2) and read-back tests (Task 3) |
| `tests/compliance_acceptance.py` | Modify | `MODULES` gains `"compliance_universe_gate"` |
| `tests/control_controller.py` | Modify | Cancel of a recorded derived-coin buy with no rule and no snapshot |
| `tests/odds_pipeline.py` | Modify | `simulate` on a derived eligible coin |

---

### Task 1: Context.universe sealed only when set

**Files:**
- Modify: `core/compliance/model.py:178-179` (Context fields), `core/compliance/model.py:230-238` (`seal_context`)
- Modify: `execution_accounts/readiness.py:13`, `execution_accounts/readiness.py:242-244`
- Modify: `execution_launch/profile.py:413-414`
- Modify: `execution_launch/review_auth.py:159-160`
- Modify: `tests/compliance_fixtures.py` (append after line 265, after anything PR 1 appended)
- Test: `tests/compliance_model.py:91-97` (existing test), new test inserted before line 104

**Interfaces:**
- Consumes (PR 1): `model.Universe(day, rule_sha256, snapshot_sha256, built_at, valid_from, valid_until, listed,
  eligible: tuple[tuple[str, Decimal], ...])`; `rules.universe_rule_sha256(rule) -> str`;
  `rules.Venue.universe_rule: UniverseRule | None`; the `universe_rule` parser in `rules.parse_venues`.
- Produces:
  - `model.Context.universe: Universe | None = None` (last field before `ctx_hash`).
  - `model.context_hash(ctx) -> str`: sha256 hex over every field but `ctx_hash`, with `universe` included only when
    not None (its `eligible` medians as `str(Decimal)`).
  - `F.universe_venues_raw() -> bytes`, `F.universe_rule() -> rules.UniverseRule`.
  - `F.universe(rule=None, *, eligible=("KRW-XRP",), day=date(2026, 10, 23)) -> model.Universe`.

- [ ] **Step 1: Cut the branch from main with PR 1 merged**

```bash
cd "$SCRATCH/tgu"
git fetch origin
git checkout -b claude/upbit-universe-pr3-gate origin/main
grep -n "^UNIVERSE_MARKET\|^def universe_rule_sha256\|^def verify_universe_snapshot\|^def encode_universe_snapshot\|^def universe_requests\|^class UniverseError" core/compliance/rules.py
grep -n "^class Universe" core/compliance/model.py
grep -n "^def universe_path\|^def universe_dir" core/compliance/owner.py
grep -n "^def universe" tests/compliance_fixtures.py
```

Expected: every PR 1 name above is found. The last grep prints nothing (PR 1's index contract adds no fixture with
these names). If it prints a line, stop and report the collision instead of editing around it.

- [ ] **Step 2: Add the fixtures and write the failing tests**

Append to the end of `tests/compliance_fixtures.py`:

```python
# -- Upbit KRW universe (PR 3): the signed rule and a Universe for sealed contexts ------------------------------------
from decimal import Decimal as _Decimal  # noqa: E402

_UPBIT_MARKETS = b"    markets: [[BTC, KRW], [USDT, KRW]]   # KRW-quoted only (P22)\n"
_UNIVERSE_RULE_YAML = (b"    universe_rule:\n"
                       b'      source: "https://docs.upbit.com/kr/reference/list-trading-pairs"\n'
                       b"      quote: KRW\n"
                       b"      exclude: [USDT, USDC]\n"
                       b"      min_listing_days: 250\n"
                       b"      median_days: 30\n"
                       b"      min_median_value_krw: 1000000000\n")


def universe_venues_raw() -> bytes:
    """The shipped venues.yaml with the spec section 4 universe_rule (its proposed defaults) in the upbit entry, as
    the owner would sign it after code-approve."""
    raw = shipped_bytes("venues")
    if raw.count(_UPBIT_MARKETS) != 1:
        raise AssertionError("universe_venues_raw: the upbit markets line moved")
    return raw.replace(_UPBIT_MARKETS, _UPBIT_MARKETS + _UNIVERSE_RULE_YAML)


def universe_rule():
    """The UniverseRule that rules.parse_venues reads from universe_venues_raw()."""
    state = approved(venues=universe_venues_raw())
    if not state.valid:
        raise AssertionError(f"universe_venues_raw: {state.reason}")
    return state.venues.venues["upbit"].universe_rule


def universe(rule=None, *, eligible=("KRW-XRP",), day=_date(2026, 10, 23)):
    """A model.Universe of candle day `day` built under `rule` (universe_rule() by default): each `eligible` market
    with a median of KRW 2,000,000,000, built at day 00:15 UTC and in force [day 00:40 UTC, day+1 00:40 UTC). Gate
    tests seal it into ctx() as `universe=`; load_context tests write real files with universe_file() instead."""
    from core.compliance import rules as R
    start = _dt.datetime(day.year, day.month, day.day, 0, 40, tzinfo=_dt.timezone.utc)
    markets = tuple(sorted(eligible))
    return _model.Universe(day=day, rule_sha256=R.universe_rule_sha256(rule or universe_rule()),
                           snapshot_sha256="e" * 64, built_at=start - _dt.timedelta(minutes=25), valid_from=start,
                           valid_until=start + _dt.timedelta(days=1), listed=tuple(sorted({*markets, "KRW-BTC"})),
                           eligible=tuple((m, _Decimal(2_000_000_000)) for m in markets))
```

In `tests/compliance_model.py`, replace (lines 95-97):

```python
               "exposure": {"upbit": model.Exposure(held_krw=1.0)}, "live_evidence": frozenset({"deposit_krw_10m"})}
    assert set(changes) | {"ctx_hash"} == {f.name for f in dataclasses.fields(model.Context)}, \
        "a new Context field needs a case"
```

with:

```python
               "exposure": {"upbit": model.Exposure(held_krw=1.0)}, "live_evidence": frozenset({"deposit_krw_10m"}),
               "universe": F.universe()}
    assert set(changes) | {"ctx_hash"} == {f.name for f in dataclasses.fields(model.Context)}, \
        "a new Context field needs a case"
```

In `tests/compliance_model.py`, add `from decimal import Decimal` after `from datetime import date, datetime,
timezone` (line 9). Then insert this test right before `def test_fixture_ctx_is_sealed_and_valid():` (line 104):

```python
def test_context_universe_is_sealed_only_when_set():
    """Upbit KRW universe spec 8: a context with no universe keeps the ctx_hash of the fields it had before the field
    existed (fixed KRW-BTC digests stay byte-identical); one with a universe hashes it, each median as its exact
    decimal text. context_hash is the rule seal_context applied."""
    plain = F.ctx()
    old = {f.name: getattr(plain, f.name) for f in dataclasses.fields(model.Context)
           if f.name not in ("ctx_hash", "universe")}
    assert plain.universe is None and plain.ctx_hash == model.sha256_hex(model.canonical_json(old))
    u = F.universe()
    held = F.ctx(universe=u)
    body = {**old, "universe": {**{f.name: getattr(u, f.name) for f in dataclasses.fields(u)},
                                "eligible": [["KRW-XRP", "2000000000"]]}}
    assert held.universe is u and held.ctx_hash == model.sha256_hex(model.canonical_json(body)) != plain.ctx_hash
    assert model.context_hash(held) == held.ctx_hash and model.context_hash(plain) == plain.ctx_hash
    finer = F.ctx(universe=dataclasses.replace(u, eligible=(("KRW-XRP", Decimal("2000000000.5")),)))
    assert finer.ctx_hash not in (held.ctx_hash, plain.ctx_hash)
    rule = F.universe_rule()
    assert (rule.quote, rule.exclude, rule.min_median_value_krw) == ("KRW", ("USDC", "USDT"), 1_000_000_000)
```

- [ ] **Step 3: Run the tests to verify they fail**

Run (with `PY`, `TRADEGEN_RUNS_DIR` and `focus` defined as in the index, "Running tests"):

```bash
focus compliance compliance_model/test_context_universe_is_sealed_only_when_set
focus compliance compliance_model/test_seal_context_registers_and_hand_built_is_refused
```

Expected: both FAIL. The first fails with `AttributeError: 'Context' object has no attribute 'universe'` (on
`plain.universe`, before any `universe=` keyword is passed). The second fails with `AssertionError: a new Context
field needs a case`. PR 1 stores `UniverseRule.exclude` sorted, so the literal is `("USDC", "USDT")`; if the last
assert of `test_context_universe_is_sealed_only_when_set` still fails after Step 4, print `F.universe_rule().exclude`
and stop: a different order means PR 1's contract changed.

- [ ] **Step 4: Implement `Context.universe` and `context_hash`**

In `core/compliance/model.py`, replace (lines 178-179):

```python
    live_evidence: frozenset = frozenset()            # E1: live D16 requirements in force (owner.evidence_in_force)
    ctx_hash: str = ""                                # set by seal_context
```

with:

```python
    live_evidence: frozenset = frozenset()            # E1: live D16 requirements in force (owner.evidence_in_force)
    universe: Universe | None = None                  # upbit KRW universe spec 8: the snapshot in force, or None
    ctx_hash: str = ""                                # set by seal_context
```

In `core/compliance/model.py`, replace `seal_context` (lines 230-238):

```python
def seal_context(**fields) -> Context:
    """Build a Context, hash every field into ctx_hash and register the instance (P5). Discipline, not
    security: owner.load_context and the test fixtures are its only callers."""
    fields.pop("ctx_hash", None)
    draft = Context(**fields)                         # defaults filled in; an unknown field is still a TypeError
    body = {f.name: getattr(draft, f.name) for f in dataclasses.fields(Context) if f.name != "ctx_hash"}
    ctx = Context(**body, ctx_hash=sha256_hex(canonical_json(body)))
    _SEALED[id(ctx)] = ctx
    return ctx
```

with:

```python
def context_hash(ctx) -> str:
    """sha256 of every Context field but ctx_hash. `universe` counts only when set, so a context without one keeps
    the hash it had before the field existed (upbit KRW universe spec 8); its Decimal medians hash as exact text."""
    body = {f.name: getattr(ctx, f.name) for f in dataclasses.fields(Context)
            if f.name not in ("ctx_hash", "universe")}
    if ctx.universe is not None:
        u = ctx.universe
        body["universe"] = {**{f.name: getattr(u, f.name) for f in dataclasses.fields(u)},
                            "eligible": [[market, str(median)] for market, median in u.eligible]}
    return sha256_hex(canonical_json(body))


def seal_context(**fields) -> Context:
    """Build a Context, hash it into ctx_hash (context_hash) and register the instance (P5). Discipline, not
    security: owner.load_context and the test fixtures are its only callers."""
    fields.pop("ctx_hash", None)
    draft = Context(**fields)                         # defaults filled in; an unknown field is still a TypeError
    ctx = dataclasses.replace(draft, ctx_hash=context_hash(draft))
    _SEALED[id(ctx)] = ctx
    return ctx
```

Three integrity checks recompute the hash over every field and would now disagree with `seal_context` (they would
hash `"universe": null`). Each switches to `context_hash`.

In `execution_accounts/readiness.py`, replace (lines 242-244):

```python
                          and self.kis_context.ctx_hash == model.sha256_hex(model.canonical_json({
                              item.name: getattr(self.kis_context, item.name)
                              for item in fields(model.Context) if item.name != "ctx_hash"})))
```

with:

```python
                          and self.kis_context.ctx_hash == model.context_hash(self.kis_context))
```

and replace line 13 `from dataclasses import dataclass, field, fields` with
`from dataclasses import dataclass, field` (`fields` has no other use in that file).

In `execution_launch/profile.py`, replace (lines 413-414):

```python
                      and context.ctx_hash == compliance.sha256_hex(compliance.canonical_json({
                          f.name: getattr(context, f.name) for f in fields(compliance.Context) if f.name != "ctx_hash"})))
```

with:

```python
                      and context.ctx_hash == compliance.context_hash(context))
```

(`fields` stays imported there; `preflight_profile` is not a reviewed callable in `tests/renewal_boundaries.py`, and
function bodies are outside the pinned initialization surface.)

In `execution_launch/review_auth.py`, replace (lines 159-160):

```python
            and context.ctx_hash == compliance.sha256_hex(compliance.canonical_json({f.name: getattr(context, f.name)
                for f in fields(compliance.Context) if f.name != "ctx_hash"})))
```

with:

```python
            and context.ctx_hash == compliance.context_hash(context))
```

- [ ] **Step 5: Run the focused and module tests**

```bash
focus compliance compliance_model/test_context_universe_is_sealed_only_when_set
focus compliance compliance_model
focus compliance compliance_gate
focus accounts accounts_readiness
focus launch launch_profile
focus launch launch_review_auth
focus launch launch_study_review
focus launch launch_windows_owner_authority
focus control control_guards
```

Expected: every command exits 0 with no FAIL row. `control_guards` runs `tests/renewal_boundaries.py`, which pins
`execution_launch/profile.py`'s initialization surface; the edit is inside a function body, so the pin is unchanged.

- [ ] **Step 6: Commit**

```bash
git add core/compliance/model.py execution_accounts/readiness.py execution_launch/profile.py execution_launch/review_auth.py tests/compliance_fixtures.py tests/compliance_model.py
diff <(git diff --cached --stat) <(git diff --cached --stat --ignore-cr-at-eol) && echo "line endings intact"
git commit -m "feat(compliance): Context.universe, hashed into ctx_hash only when set" -m "One model.context_hash serves seal_context and the readiness, profile and review-authority integrity checks, so a context without a universe keeps today's hash." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

Expected: `line endings intact`, then one commit with six files. If the `diff` prints anything, a staged file
changed its line endings: stop before the commit and report it.

---

### Task 2: Derived Upbit KRW coins at the gate

**Files:**
- Modify: `core/compliance/gate.py:35` (insert after), `core/compliance/gate.py:77-79` (`_decide` steps 5-6),
  `core/compliance/gate.py:156` (`_validate` lookup), `core/compliance/gate.py:171` (market test),
  `core/compliance/gate.py:464` (insert after `_lookup`), `core/compliance/gate.py:467-469` (`_retired`),
  `core/compliance/gate.py:630` (`_screen`), `core/compliance/gate.py:677` (`grey_rows`)
- Modify: `tests/compliance_acceptance.py:25-27` (`MODULES`)
- Create: `tests/compliance_universe_gate.py`
- Test: `tests/compliance_universe_gate.py`, `tests/compliance_gate.py` (unchanged, must stay green)

**Interfaces:**
- Consumes: Task 1's `F.universe_venues_raw()`, `F.universe_rule()`, `F.universe(...)`, `ctx.universe`. PR 1's
  `rules.UNIVERSE_MARKET`, `rules.universe_rule_sha256(rule) -> str`, `Venue.universe_rule`.
- Produces:
  - `gate.lookup(ctx, state, venue, symbol, exits: bool, *, recorded: bool = False) -> rules.Instrument | None`.
    `venue` is the `rules.Venue` of `state`.
  - `gate.market_listed(state, venue, inst, counter) -> bool`.
  - The block reasons `"state: universe no_rule"`, `"state: universe no_snapshot"` and
    `"state: universe not_eligible"`.
  - The private helpers `gate._derived(state, venue, symbol) -> rules.Instrument | None` and
    `gate._universe(ctx, state, venue, symbol) -> list[str]`.

- [ ] **Step 1: Register the module and write the failing tests**

In `tests/compliance_acceptance.py`, replace the `MODULES` tuple as PR 1 left it (lines 25-27):

```python
MODULES = ("compliance_guards", "compliance_isolation", "compliance_loader", "compliance_tables",
           "compliance_model", "compliance_gate", "compliance_owner", "compliance_store", "compliance_cli",
           "compliance_signer", "compliance_universe")
```

with:

```python
MODULES = ("compliance_guards", "compliance_isolation", "compliance_loader", "compliance_tables",
           "compliance_model", "compliance_gate", "compliance_owner", "compliance_store", "compliance_cli",
           "compliance_signer", "compliance_universe", "compliance_universe_gate")
```

Create `tests/compliance_universe_gate.py`:

```python
"""Upbit KRW universe PR 3 (spec 2026-11-11, sections 5 and 8): derived Upbit KRW coins at the gate and the snapshot
that load_context reads back. A coin no signed map lists resolves to a copy of the signed BTC entry for a KRW sell of
a held coin, for new exposure under the venue's signed universe_rule and for a recorded order. New exposure on it
also needs ctx.universe built under that rule with the coin eligible."""
from __future__ import annotations

import dataclasses
import types

from core.compliance import gate, model
from tests import compliance_fixtures as F

_SELL = {"action": "sell", "quantity": 10.0, "notional_krw": 10_000.0}


def _ruled() -> model.ApprovedState:
    """The shipped tables with universe_rule in upbit's venue facts (F.universe_venues_raw)."""
    return F.approved(venues=F.universe_venues_raw())


def _xrp(**changes) -> model.Intent:
    """F.intent for XRP: a buy of 10 XRP for KRW at KRW 50,000 unless `changes` say otherwise."""
    return F.intent(**{"symbol": "XRP", "quantity": 10.0, **changes})


def _grey(state) -> model.ApprovedState:
    """`state` with KR-DOMESTIC-SPOT signed grey, so grey_rows has a row to name for an upbit leg."""
    rows = tuple(dataclasses.replace(r, treatment="grey") if r.id == "KR-DOMESTIC-SPOT" else r
                 for r in state.rules.rows)
    return dataclasses.replace(state, rules=dataclasses.replace(state.rules, rows=rows))


def _plan(symbol: str, start):
    """A duck-typed upbit plan (P3): screen() and grey_rows() read leg.venue, leg.symbol, start and horizon_days."""
    return types.SimpleNamespace(leg=types.SimpleNamespace(venue="upbit", symbol=symbol), start=start,
                                 horizon_days=5)


def test_lookup_resolves_a_derived_coin_only_where_spec_8_says():
    """gate.lookup: the signed entry for a mapped symbol. For an Upbit symbol in no map whose KRW market matches the
    pattern, it returns a copy of the signed BTC entry under that symbol, for a recorded order (either side), an exit
    of a held coin, or new exposure under universe_rule; otherwise None. market_listed lists a derived coin against
    KRW only."""
    plain, ruled, c = F.approved(), _ruled(), F.ctx()
    upbit, ruled_upbit = plain.venues.venues["upbit"], ruled.venues.venues["upbit"]
    btc = plain.instruments.lookup(upbit.sections, "BTC")
    xrp = dataclasses.replace(btc, symbol="XRP")
    assert gate.lookup(c, plain, upbit, "BTC", False) is btc
    assert gate.lookup(c, ruled, ruled_upbit, "BTC", True) == btc
    for exits in (False, True):
        assert gate.lookup(c, plain, upbit, "XRP", exits) is None, exits
        assert gate.lookup(c, plain, upbit, "XRP", exits, recorded=True) == xrp, exits
    held = F.ctx(holdings={("upbit", "XRP"): 1.0})
    assert gate.lookup(held, plain, upbit, "XRP", True) == xrp             # an exit needs no rule
    assert gate.lookup(held, plain, upbit, "XRP", False) is None           # new exposure does
    assert gate.lookup(c, ruled, ruled_upbit, "XRP", False) == xrp
    assert gate.lookup(c, ruled, ruled_upbit, "XRP", True) is None         # nothing held: no exit
    for venue, symbol in ((plain.venues.venues["bithumb"], "XRP"), (upbit, "KRW"), (upbit, "xrp"), (upbit, 5),
                          (upbit, "A" * 13), (upbit, "X-Y")):
        assert gate.lookup(c, plain, venue, symbol, True, recorded=True) is None, (venue.id, symbol)
    assert gate.market_listed(plain, upbit, xrp, "KRW") and not gate.market_listed(plain, upbit, xrp, "USDT")
    assert gate.market_listed(plain, upbit, btc, "KRW") and not gate.market_listed(plain, upbit, btc, "USD")


def test_map_coins_keep_todays_path():
    """Spec 8: a symbol of a signed map is decided as before, with or without universe_rule and a snapshot."""
    ruled = _ruled()
    base = gate.decide(F.intent(), F.ctx())
    assert (base.verdict, base.kind, base.reasons) == (model.ALLOW, "new_exposure", ()), base.reasons
    for c in (F.ctx(active=ruled), F.ctx(active=ruled, universe=F.universe())):
        d = gate.decide(F.intent(), c)
        assert (d.verdict, d.kind, d.reasons) == (base.verdict, base.kind, base.reasons), d.reasons
        usdt = gate.decide(F.intent(symbol="USDT"), c)
        assert usdt.verdict == model.ALLOW, usdt.reasons


def test_derived_buys_need_the_rule_a_snapshot_in_force_and_eligibility():
    """Spec 8: new exposure on a derived coin needs universe_rule in the signed venue facts. Without it the symbol is
    unknown, as before. It also needs ctx.universe built under that rule (else "state: universe no_snapshot") and the
    coin in its eligible set (else "state: universe not_eligible"). With all three, the rows decide it as they decide
    BTC."""
    ruled = _ruled()
    no_rule = gate.decide(_xrp(), F.ctx(universe=F.universe()))
    assert no_rule.verdict == model.BLOCK and no_rule.reasons == ("malformed: symbol",), no_rule.reasons
    foreign = dataclasses.replace(F.universe(), rule_sha256="0" * 64)
    for c in (F.ctx(active=ruled), F.ctx(active=ruled, universe=foreign)):
        d = gate.decide(_xrp(), c)
        assert (d.verdict, d.kind, d.reasons) == (model.BLOCK, "new_exposure", ("state: universe no_snapshot",)), d
    doge = gate.decide(_xrp(symbol="DOGE"), F.ctx(active=ruled, universe=F.universe()))
    assert doge.verdict == model.BLOCK and doge.reasons == ("state: universe not_eligible",), doge.reasons
    ok = gate.decide(_xrp(), F.ctx(active=ruled, universe=F.universe()))
    assert (ok.verdict, ok.kind, ok.reasons) == (model.ALLOW, "new_exposure", ()), ok.reasons
    for bad, field in ((_xrp(counter_symbol="USDT"), "counter_symbol"), (_xrp(asset="us_etp"), "asset"),
                       (_xrp(symbol="xrp"), "symbol"), (_xrp(symbol="KRW"), "symbol")):
        d = gate.decide(bad, F.ctx(active=ruled, universe=F.universe()))
        assert d.verdict == model.BLOCK and f"malformed: {field}" in d.reasons, (field, d.reasons)


def test_held_coin_krw_exits_need_no_snapshot_and_survive_a_dropped_rule():
    """Spec 8: a cash sell for KRW of a held derived coin is ALLOW_EXIT close_long with no snapshot, with no rule (as
    after a venues approval that drops universe_rule), and from the recovery snapshot. _within_free checks its
    quantity, and its only market is (coin, KRW)."""
    held = {("upbit", "XRP"): 25.0}
    sell = _xrp(**_SELL)
    broken = model.OwnerState.broken("bad signature on entry 4")
    for c in (F.ctx(holdings=held), F.ctx(active=_ruled(), holdings=held),
              F.ctx(active=model.ApprovedState.invalid("fixture"), snapshot=F.approved(), holdings=held),
              F.ctx(owner=broken, snapshot=_ruled(), holdings=held)):
        d = gate.decide(sell, c)
        assert (d.verdict, d.kind) == (model.ALLOW_EXIT, "close_long"), d.reasons
    unheld = gate.decide(sell, F.ctx(active=_ruled(), universe=F.universe()))
    assert unheld.verdict == model.BLOCK, unheld.reasons
    assert {"malformed: symbol", "close manually in the broker app"} <= set(unheld.reasons), unheld.reasons
    over = gate.decide(_xrp(**{**_SELL, "quantity": 30.0}), F.ctx(holdings=held))
    assert over.verdict == model.BLOCK and "malformed: quantity" in over.reasons, over.reasons
    usdt = gate.decide(_xrp(**{**_SELL, "counter_symbol": "USDT"}), F.ctx(holdings=held))
    assert usdt.verdict == model.BLOCK and "malformed: counter_symbol" in usdt.reasons, usdt.reasons


def test_a_derived_coin_never_transfers():
    """Spec 8: _transfer stays on the signed maps, and a derived coin leaves only by a KRW sell. Its transfer, to a
    domestic exchange or abroad, is therefore an unknown symbol, and the domestic one is sent to the app."""
    c = F.ctx(active=_ruled(), universe=F.universe(), holdings={("upbit", "XRP"): 25.0})
    move = _xrp(action="transfer_out", counter_symbol="", quantity=10.0, notional_krw=10_000.0,
                destination_venue="bithumb", destination_address="rFixtureAddress", destination_network="ripple")
    home = gate.decide(move, c)
    assert home.verdict == model.BLOCK, home.reasons
    assert {"malformed: symbol", "withdraw manually in the exchange app"} <= set(home.reasons), home.reasons
    away = gate.decide(dataclasses.replace(move, destination_venue="okx"), c)
    assert away.verdict == model.BLOCK and away.reasons == ("malformed: symbol",), away.reasons


def test_the_step_5_universe_check_names_each_reason():
    """The step 5 universe check by itself. decide never reaches no_rule: its lookup already refuses a derived buy
    without the rule ("malformed: symbol"), so no_rule is defence in depth. The check returns no_rule, no_snapshot,
    not_eligible and then [] as each condition is met, and [] for a map coin."""
    plain, ruled = F.approved(), _ruled()
    upbit, ruled_upbit = plain.venues.venues["upbit"], ruled.venues.venues["upbit"]
    full = F.ctx(active=ruled, universe=F.universe())
    assert gate._universe(F.ctx(universe=F.universe()), plain, upbit, "XRP") == ["state: universe no_rule"]
    assert gate._universe(F.ctx(active=ruled), ruled, ruled_upbit, "XRP") == ["state: universe no_snapshot"]
    assert gate._universe(full, ruled, ruled_upbit, "DOGE") == ["state: universe not_eligible"]
    assert gate._universe(full, ruled, ruled_upbit, "XRP") == []
    assert gate._universe(F.ctx(), plain, upbit, "BTC") == []


def test_screen_and_grey_rows_see_a_derived_eligible_coin():
    """Spec 8: screen (exits=False) decides a derived leg as decide does, so simulate can run it. grey_rows names the
    grey rows matching it under the rule, and () without the rule."""
    ruled = _ruled()
    c = F.ctx(active=ruled, universe=F.universe())
    leg = _plan("XRP", c.date)
    s = gate.screen(leg, c, 42_000.0)
    assert s.allowed and s.decision.verdict == model.ALLOW and s.decision.reasons == (), s.decision.reasons
    assert s.decision.intent_hash == model.intent_hash(_xrp(quantity=1.0, notional_krw=42_000.0))
    blocked = gate.screen(leg, F.ctx(active=ruled), 42_000.0)
    assert not blocked.allowed and blocked.decision.reasons == ("state: universe no_snapshot",), blocked
    unknown = gate.screen(leg, F.ctx(universe=F.universe()), 42_000.0)
    assert not unknown.allowed and "malformed: symbol" in unknown.decision.reasons, unknown.decision.reasons
    assert gate.grey_rows(leg, c) == ()
    assert gate.grey_rows(leg, F.ctx(active=_grey(ruled), universe=F.universe())) == ("KR-DOMESTIC-SPOT",)
    assert gate.grey_rows(leg, F.ctx(active=_grey(F.approved()))) == ()
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
focus compliance compliance_universe_gate
```

Expected: FAIL. `test_lookup_resolves...` and `test_the_step_5_universe_check...` fail with `AttributeError: module
'core.compliance.gate' has no attribute 'lookup'` (and `'_universe'`). `test_derived_buys...` and
`test_held_coin...` fail with AssertionError on reasons `('malformed: symbol', ...)`. `test_screen_and_grey_rows...`
fails because the XRP screen is not allowed. `test_map_coins_keep_todays_path` and
`test_a_derived_coin_never_transfers` already PASS.

- [ ] **Step 3: Implement the gate changes**

In `core/compliance/gate.py`, after line 35:

```python
_SLACK = 1 + 1e-12                                                      # float slack on unit comparisons
```

insert:

```python
_DERIVED_VENUE, _DERIVED_QUOTE, _DERIVED_TEMPLATE = "upbit", "KRW", "BTC"    # upbit KRW universe spec 8, fixed in code
```

In `_decide`, replace (lines 77-79):

```python
    else:                                                                                     # steps 5-6
        pre, floor = _preconditions(ctx, state), _floor_new(intent, inst)
        reasons += pre + floor
```

with:

```python
    else:                                                                                     # steps 5-6
        pre, floor = _preconditions(ctx, state), _floor_new(intent, inst)
        pre += _universe(ctx, state, venue, intent.symbol)            # a derived coin (upbit KRW universe spec 8)
        reasons += pre + floor
```

In `_validate`, replace (line 156):

```python
    inst = _lookup(state, venue, intent.symbol, exit_action and intent.financing == "cash")
```

with:

```python
    inst = lookup(ctx, state, venue, intent.symbol, exit_action and intent.financing == "cash")
    if inst is not None and intent.action not in ("buy", "sell") and _derived(state, venue, intent.symbol) is not None:
        inst = None                                   # spec 8: a derived coin is bought, or sold for KRW; never moved
```

In `_validate`, replace (line 171):

```python
            listed = venue.is_market(inst, intent.counter_symbol)
```

with:

```python
            listed = market_listed(state, venue, inst, intent.counter_symbol)
```

After `_lookup` (which ends at line 464, `    return None`), insert:

```python


def lookup(ctx, state, venue, symbol, exits: bool, *, recorded: bool = False):
    """The instrument a decision uses (upbit KRW universe spec 8): _lookup's signed entry; else the derived Upbit KRW
    coin (_derived) for an order already in the journal (`recorded`, whatever its side and the snapshot state), for
    an exit of a coin ctx.holdings holds (whatever the venue facts say), or for new exposure on a venue whose signed
    facts carry universe_rule; else None. Whether new exposure on it may proceed is _universe's call (step 5)."""
    inst = _lookup(state, venue, symbol, exits)
    if inst is not None:
        return inst
    derived = _derived(state, venue, symbol)
    if derived is None or recorded:
        return derived
    if exits:
        held = ctx.holdings.get((venue.id, symbol), 0.0)
        return derived if _number(held) and held > 0 else None
    return derived if venue.universe_rule is not None else None


def market_listed(state, venue, inst, counter) -> bool:
    """venue.is_market; a derived coin (spec 8) is listed against the fixed KRW quote only."""
    if _derived(state, venue, inst.symbol) is not None:
        return counter == _DERIVED_QUOTE
    return venue.is_market(inst, counter)


def _derived(state, venue, symbol):
    """An Upbit symbol that no approved map lists, current or earlier, whose KRW market matches rules.UNIVERSE_MARKET:
    the signed BTC entry (crypto_coin x1, class coin, crypto_venue, KRW, crypto_22pct_from_2027) copied under that
    symbol. None for anything else, a settlement asset included."""
    if (venue is None or venue.id != _DERIVED_VENUE or type(symbol) is not str or symbol in venue.settlement
            or rules.UNIVERSE_MARKET.fullmatch(f"{_DERIVED_QUOTE}-{symbol}") is None
            or _lookup(state, venue, symbol, True) is not None):
        return None
    template = _lookup(state, venue, _DERIVED_TEMPLATE, True)
    return None if template is None else dataclasses.replace(template, symbol=symbol)


def _universe(ctx, state, venue, symbol) -> list[str]:
    """Step 5 for a derived coin (spec 8): the venue's signed universe_rule, ctx.universe built under it, and the
    coin in its eligible set; [] for a coin of a signed map."""
    if _derived(state, venue, symbol) is None:
        return []
    rule = venue.universe_rule
    if rule is None:
        return ["state: universe no_rule"]
    if ctx.universe is None or ctx.universe.rule_sha256 != rules.universe_rule_sha256(rule):
        return ["state: universe no_snapshot"]
    if f"{_DERIVED_QUOTE}-{symbol}" not in dict(ctx.universe.eligible):
        return ["state: universe not_eligible"]
    return []
```

Replace `_retired` (lines 467-469):

```python
def _retired(state, venue, symbol) -> bool:
    """The symbol is not in the map in force for the venue's sections (only an earlier map may know it)."""
    return state.instruments.lookup(venue.sections, symbol) is None
```

with:

```python
def _retired(state, venue, symbol) -> bool:
    """The symbol is not in the map in force for the venue's sections but an earlier approved map knows it. A derived
    coin (spec 8) is in no map, so it is never retired."""
    return state.instruments.lookup(venue.sections, symbol) is None and _lookup(state, venue, symbol, True) is not None
```

In `_screen`, replace (line 630):

```python
    inst = _lookup(state, venue, symbol, False) if venue is not None else None
```

with:

```python
    inst = lookup(ctx, state, venue, symbol, False) if venue is not None else None
```

In `grey_rows`, replace (line 677):

```python
        inst = _lookup(state, venue, symbol, False) if venue is not None else None
```

with:

```python
        inst = lookup(ctx, state, venue, symbol, False) if venue is not None else None
```

Leave `_transfer` (line 257, `dest_inst = _lookup(state, dest, intent.symbol, False) ...`) unchanged.

- [ ] **Step 4: Run the focused and module tests**

```bash
focus compliance compliance_universe_gate
focus compliance compliance_gate
focus compliance compliance_guards
focus odds odds_plan
```

Expected: all exit 0 with no FAIL row. In particular, `compliance_gate/test_gate_call_graph_has_no_clock_zone_file_or_socket`
(which now scans `rules.universe_rule_sha256`), `test_fail_closed_inputs_are_malformed` (DOGE stays "malformed:
symbol"), `test_history_maps_serve_exits_only` and `odds_plan/test_whitelist_refuses_everything_else_with_its_sub`
pass unchanged.

- [ ] **Step 5: Commit**

```bash
git add core/compliance/gate.py tests/compliance_acceptance.py tests/compliance_universe_gate.py
diff <(git diff --cached --stat) <(git diff --cached --stat --ignore-cr-at-eol) && echo "line endings intact"
git commit -m "feat(compliance): derived Upbit KRW coins at the gate" -m "Public gate.lookup and gate.market_listed: KRW exits of held coins need no snapshot or rule, new exposure needs the signed universe_rule, ctx.universe built under it and the coin eligible, recorded orders resolve whatever the snapshot state; transfers stay on the signed maps." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

Expected: `line endings intact`, then one commit with three files (the new test module is staged, so `--cached`
covers it).

---

### Task 3: Read the snapshot in force back in load_context

**Files:**
- Modify: `core/compliance/owner.py:1004` (`load_context` call), `core/compliance/owner.py:1013` (`_context`
  signature), `core/compliance/owner.py:1040-1043` (the `seal_context` call), insert after line 1043
- Modify: `tests/compliance_fixtures.py` (append after Task 1's block)
- Modify: `tests/compliance_universe_gate.py` (imports, append the read-back tests)
- Test: `tests/compliance_universe_gate.py`, `tests/compliance_store.py` and `tests/compliance_owner.py` (unchanged,
  must stay green)

**Interfaces:**
- Consumes (PR 1): `rules.universe_requests(rule, market_all_body, day)` (sorted `(path, params)`; market/all params
  `(("is_details", "true"),)`; candle params `("market", m), ("to", "YYYY-MM-DDT00:00:00Z"), ("count", "n")`);
  receipt stamps (`received_at`, `server_time`) as `YYYY-MM-DDTHH:MM:SS.ffffffZ`; a candle's
  `candle_acc_trade_price` as a non-negative JSON number (an int, or a fraction parsed as a Decimal) and its
  `candle_date_time_utc` as
  `YYYY-MM-DDT00:00:00`; `rules.encode_universe_snapshot(rule, day, receipts) -> (bytes, sha)`;
  `rules.verify_universe_snapshot(raw, rule_sha256) -> Universe`; `rules.UniverseError`;
  `owner.universe_path(day, sha256)`, `owner.universe_dir(day)`. From Task 2: `gate.decide` on derived coins.
- Produces:
  - `owner._universe_in_force(now: datetime, rule_sha256: str) -> Universe | None`, which never raises.
  - `owner._universe_now(now, active) -> Universe | None`, which never raises.
  - `owner._UNIVERSE_VERIFIED: dict`, keyed by `(file sha256, rule sha256)` with a `Universe` or `None` as value.
  - `load_context` sets `Context.universe`.
  - The fixtures `F.universe_receipts(rule, day, *, markets=("KRW-BTC", "KRW-XRP"), value=2_000_000_000,
    served=None) -> list[dict]` and `F.universe_file(rule, day, **changes) -> Path`.

- [ ] **Step 1: Add the snapshot fixtures and write the failing tests**

Append to the end of `tests/compliance_fixtures.py`:

```python
def universe_receipts(rule, day, *, markets=("KRW-BTC", "KRW-XRP"), value=2_000_000_000, served=None) -> list:
    """Plain receipts (PR 1 contract: path, params, account_scope, received_at, server_time, raw_body_b64, sha256)
    answering every request of rules.universe_requests(rule, <market/all body>, day): `markets` unflagged in
    market/all, and each candle request answered with one daily candle per requested day before its `to`, each
    trading `value` KRW. Every receipt is served at `served` (default day 00:15 UTC), which is then built_at."""
    import base64
    import hashlib
    from core.compliance import rules as R
    served = served or _dt.datetime(day.year, day.month, day.day, 0, 15, tzinfo=_dt.timezone.utc)
    stamp = served.astimezone(_dt.timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")
    caution = dict.fromkeys(("PRICE_FLUCTUATIONS", "TRADING_VOLUME_SOARING", "DEPOSIT_AMOUNT_SOARING",
                             "GLOBAL_PRICE_DIFFERENCES", "CONCENTRATION_OF_SMALL_ACCOUNTS"), False)
    listing = _json.dumps([{"market": m, "korean_name": m, "english_name": m,
                            "market_event": {"warning": False, "caution": caution}} for m in markets]).encode()
    out = []
    for path, params in R.universe_requests(rule, listing, day):
        query = dict(params)
        if "market" in query:
            to = _dt.datetime.fromisoformat(query["to"])
            body = _json.dumps([_candle(query["market"], to - _dt.timedelta(days=i), value)
                                for i in range(1, int(query["count"]) + 1)]).encode()
        else:
            body = listing
        out.append({"path": path, "params": [list(p) for p in params], "account_scope": "public",
                    "received_at": stamp, "server_time": stamp, "raw_body_b64": base64.b64encode(body).decode("ascii"),
                    "sha256": hashlib.sha256(body).hexdigest()})
    return out


def _candle(market: str, at, value: int) -> dict:
    """One Upbit daily candle (GET /v1/candles/days fields) opening at `at` (00:00 UTC) and trading `value` KRW.
    `candle_acc_trade_price` stays the int `value`, so each median is that exact integer (PR 1 parses a JSON
    fraction as a Decimal, so a float here would turn into Decimal("2000000000.0"))."""
    return {"market": market, "candle_date_time_utc": at.strftime("%Y-%m-%dT%H:%M:%S"),
            "candle_date_time_kst": (at + _dt.timedelta(hours=9)).strftime("%Y-%m-%dT%H:%M:%S"),
            "opening_price": 1000.0, "high_price": 1000.0, "low_price": 1000.0, "trade_price": 1000.0,
            "timestamp": int(at.timestamp() * 1000), "candle_acc_trade_price": value,
            "candle_acc_trade_volume": value / 1000.0, "prev_closing_price": 1000.0, "change_price": 0.0,
            "change_rate": 0.0}


def universe_file(rule, day, **changes) -> Path:
    """rules.encode_universe_snapshot over universe_receipts(rule, day, **changes), written to owner.universe_path.
    The path must lie inside the temp dir, so the real ~/.tradegen is never written. Returns the path."""
    from core.compliance import owner, rules as R
    raw, sha = R.encode_universe_snapshot(rule, day, universe_receipts(rule, day, **changes))
    path = owner.universe_path(day, sha)
    if not path.resolve().is_relative_to(Path(tempfile.gettempdir()).resolve()):
        raise AssertionError(f"universe_file: {path} is outside the temp dir")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return path
```

In `tests/compliance_universe_gate.py`, replace the import block:

```python
import dataclasses
import types

from core.compliance import gate, model
from tests import compliance_fixtures as F
```

with:

```python
import builtins
import dataclasses
import datetime as _dt
import types
from decimal import Decimal

from core.compliance import gate, model, owner, rules
from tests import compliance_fixtures as F

D23, D24 = _dt.date(2026, 10, 23), _dt.date(2026, 10, 24)
```

Append to the end of `tests/compliance_universe_gate.py`:

```python
# --------------------------------------------------------------------------- #
# Read-back (spec 5): load_context fills ctx.universe with the verified snapshot in force for the active rule
# --------------------------------------------------------------------------- #
def _utc(*parts) -> _dt.datetime:
    return _dt.datetime(*parts, tzinfo=_dt.timezone.utc)


def _signed_home(home):
    """F.full_home with universe_rule in the approved venues; returns the test key."""
    return F.full_home(home, venues_raw=F.universe_venues_raw())


def _held_xrp() -> model.Positions:
    return model.Positions(equity_krw=1_000_000.0, holdings={("upbit", "XRP"): 25.0})


def test_load_context_reads_the_snapshot_in_force_and_drops_it_with_the_rule():
    """Spec 5: the snapshot of candle day 2026-10-23, verified under the active rule, is ctx.universe at NOW
    (2026-10-24 09:00 KST), and an XRP buy is ALLOW. Once the owner approves venues without universe_rule, the
    universe is None, the buy is an unknown symbol, and a held XRP sell is still ALLOW_EXIT."""
    with F.temp_home() as home, F.pubkey_at(home / "owner_pubkey.pem"):
        key = _signed_home(home)
        owner._UNIVERSE_VERIFIED.clear()
        F.universe_file(F.universe_rule(), D23)
        c = owner.load_context(F.NOW, _held_xrp())
        assert c.owner.ok and c.active.valid and c.code_signed, (c.owner.reason, c.active.reason)
        u = c.universe
        assert u is not None and u.day == D23 and u.rule_sha256 == rules.universe_rule_sha256(F.universe_rule())
        assert dict(u.eligible) == {"KRW-BTC": Decimal(2_000_000_000), "KRW-XRP": Decimal(2_000_000_000)}
        assert (u.built_at, u.valid_from, u.valid_until) == (
            _utc(2026, 10, 23, 0, 15), _utc(2026, 10, 23, 0, 40), _utc(2026, 10, 24, 0, 40))
        assert c.ctx_hash == model.context_hash(c)
        assert gate.decide(_xrp(), c).verdict == model.ALLOW
        F.approve(home, key, "venues", F.shipped_bytes("venues"))          # the owner drops universe_rule
        dropped = owner.load_context(F.NOW, _held_xrp())
        assert dropped.active.valid and dropped.universe is None, dropped.active.reason
        assert gate.decide(_xrp(), dropped).reasons == ("malformed: symbol",)
        sell = gate.decide(_xrp(**_SELL), dropped)
        assert (sell.verdict, sell.kind) == (model.ALLOW_EXIT, "close_long"), sell.reasons


def test_the_snapshot_in_force_switches_at_0940_kst():
    """Spec 5: candle day D's file is in force on [max(built_at, D 00:40 UTC), D+1 00:40 UTC), with D the UTC date of
    now minus 40 minutes. Before 09:40 KST on 10-23 nothing holds, because day 10-22 has no file. 10-23's file holds
    from 09:40 KST on 10-23 to 09:39:59 KST on 10-24. 10-24's file was built late, at 01:00 UTC, so it holds only
    from its built_at."""
    with F.temp_home() as home, F.pubkey_at(home / "owner_pubkey.pem"):
        _signed_home(home)
        owner._UNIVERSE_VERIFIED.clear()
        F.universe_file(F.universe_rule(), D23)
        F.universe_file(F.universe_rule(), D24, served=_utc(2026, 10, 24, 1, 0))
        for at, day in ((_utc(2026, 10, 23, 0, 39, 59), None), (_utc(2026, 10, 23, 0, 40), D23),
                        (_utc(2026, 10, 24, 0, 39, 59), D23), (_utc(2026, 10, 24, 0, 40), None),
                        (_utc(2026, 10, 24, 0, 59, 59), None), (_utc(2026, 10, 24, 1, 0), D24)):
            u = owner.load_context(at, F.HELD).universe
            assert (None if u is None else u.day) == day, (at, u)


def test_the_earliest_built_snapshot_wins_and_verification_is_cached():
    """Spec 5: two verified files for one candle day (a manual rebuild). The earliest built is in force. Each file is
    verified once per process, keyed by its sha256, however often load_context runs."""
    with F.temp_home() as home, F.pubkey_at(home / "owner_pubkey.pem"):
        _signed_home(home)
        owner._UNIVERSE_VERIFIED.clear()
        F.universe_file(F.universe_rule(), D23, served=_utc(2026, 10, 23, 0, 20), markets=("KRW-BTC",))
        F.universe_file(F.universe_rule(), D23)                                       # served 00:15
        calls, real = [], rules.verify_universe_snapshot
        rules.verify_universe_snapshot = lambda raw, sha: calls.append(sha) or real(raw, sha)
        try:
            first = owner.load_context(F.NOW, F.HELD).universe
            again = owner.load_context(F.NOW, F.HELD).universe
        finally:
            rules.verify_universe_snapshot = real
        assert first is not None and first.built_at == _utc(2026, 10, 23, 0, 15), first
        assert [m for m, _ in first.eligible] == ["KRW-BTC", "KRW-XRP"] and again == first
        assert len(calls) == 2, calls


def test_a_tampered_or_foreign_snapshot_is_not_in_force():
    """Spec 5: a file whose receipts no longer match its request set and manifest, or a file built under another
    rule, does not verify. ctx.universe is then None and an XRP buy is BLOCK "state: universe no_snapshot", while the
    rest of the context stays intact."""
    with F.temp_home() as home, F.pubkey_at(home / "owner_pubkey.pem"):
        _signed_home(home)
        owner._UNIVERSE_VERIFIED.clear()
        path = F.universe_file(F.universe_rule(), D23)
        raw = path.read_bytes()
        assert b"KRW-XRP" in raw
        path.write_bytes(raw.replace(b"KRW-XRP", b"KRW-XRQ"))
        F.universe_file(dataclasses.replace(F.universe_rule(), min_median_value_krw=5), D23)
        c = owner.load_context(F.NOW, F.HELD)
        assert c.owner.ok and c.active.valid and c.universe is None, (c.owner.reason, c.active.reason)
        assert gate.decide(_xrp(), c).reasons == ("state: universe no_snapshot",)


def test_a_read_back_error_never_breaks_the_context_or_a_held_coin_exit():
    """Spec 5 and 19: the read-back catches every exception. A TypeError raised inside it leaves ctx.universe None and
    the rest of the context intact: a held XRP sell is ALLOW_EXIT and an XRP buy is BLOCK "state: universe
    no_snapshot"."""
    with F.temp_home() as home, F.pubkey_at(home / "owner_pubkey.pem"):
        _signed_home(home)
        owner._UNIVERSE_VERIFIED.clear()
        F.universe_file(F.universe_rule(), D23)
        real = owner.universe_dir

        def broken(day):
            raise TypeError("fixture read-back failure")

        owner.universe_dir = broken
        try:
            c = owner.load_context(F.NOW, _held_xrp())
        finally:
            owner.universe_dir = real
        assert c.owner.ok and c.active.valid and c.code_signed and c.universe is None, (c.owner.reason,
                                                                                         c.active.reason)
        sell = gate.decide(_xrp(**_SELL), c)
        assert (sell.verdict, sell.kind) == (model.ALLOW_EXIT, "close_long"), sell.reasons
        assert gate.decide(_xrp(), c).reasons == ("state: universe no_snapshot",)


def test_the_read_back_recomputes_without_importing_execution():
    """Spec 19: load_context recomputes the snapshot (rules.verify_universe_snapshot over the receipts, with the cache
    cleared) and imports no execution* module on the way."""
    with F.temp_home() as home, F.pubkey_at(home / "owner_pubkey.pem"):
        _signed_home(home)
        owner._UNIVERSE_VERIFIED.clear()
        F.universe_file(F.universe_rule(), D23)
        names, real = [], builtins.__import__

        def spy(name, *args, **kwargs):
            names.append(name)
            return real(name, *args, **kwargs)

        builtins.__import__ = spy
        try:
            c = owner.load_context(F.NOW, F.HELD)
        finally:
            builtins.__import__ = real
        assert c.universe is not None and c.universe.day == D23
        assert [n for n in names if n.split(".")[0].startswith("execution")] == [], names
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
focus compliance compliance_universe_gate
```

Expected: the module exits non-zero with 6 FAIL rows, one per read-back test, each `AttributeError: module
'core.compliance.owner' has no attribute '_UNIVERSE_VERIFIED'`, and the 7 Task 2 gate tests PASS. If instead `rules.encode_universe_snapshot` raises a `UniverseError` from the fixture, the
receipts do not match PR 1's parser. Fix `universe_receipts` and `_candle` against PR 1's `universe_eligible` and
its tests before going on: candle field names, the request `path` strings, the stamp format or the finality rules.

- [ ] **Step 3: Implement the read-back**

In `core/compliance/owner.py`, `load_context`, replace (line 1004):

```python
        return _context(day, now_utc, positions, session_id)
```

with:

```python
        return _context(day, now_utc, positions, session_id, now)
```

Replace the `_context` signature (line 1013):

```python
def _context(day: _dt.date, now_utc: str, positions, session_id) -> model.Context:
```

with:

```python
def _context(day: _dt.date, now_utc: str, positions, session_id, now: _dt.datetime) -> model.Context:
```

Replace the end of `_context` (lines 1040-1043):

```python
    return model.seal_context(
        date=day, active=active, snapshot=snapshot, owner=owner, code_hash=current, code_signed=signed,
        session=model.SessionState(session_id=session_id, armed=session_id in owner.armed_sessions),
        equity_krw=equity, holdings=holdings, shorts=shorts, exposure=exposure, live_evidence=_live_evidence(day))
```

with:

```python
    return model.seal_context(
        date=day, active=active, snapshot=snapshot, owner=owner, code_hash=current, code_signed=signed,
        session=model.SessionState(session_id=session_id, armed=session_id in owner.armed_sessions),
        equity_krw=equity, holdings=holdings, shorts=shorts, exposure=exposure, live_evidence=_live_evidence(day),
        universe=_universe_now(now, active))


# Upbit KRW universe (spec 2026-11-11, section 5): the verified snapshot in force, read back into Context.universe.
# ponytail: one entry per file and rule for the life of the process; a few files a day, so no eviction.
_UNIVERSE_VERIFIED: dict = {}                    # (file sha256, rule sha256) -> Universe, or None for a refused file


def _universe_now(now: _dt.datetime, active: model.ApprovedState) -> model.Universe | None:
    """The snapshot in force at `now` for the universe_rule of the active upbit venue facts. None without a rule, for
    an invalid state, or on any error, so the read-back never breaks the context and exits never depend on it."""
    try:
        venue = active.venues.venues.get("upbit") if active.valid else None
        rule = getattr(venue, "universe_rule", None)
        return None if rule is None else _universe_in_force(now, rules.universe_rule_sha256(rule))
    except Exception:
        return None


def _universe_in_force(now: _dt.datetime, rule_sha256: str) -> model.Universe | None:
    """The verified snapshot built under `rule_sha256` whose [valid_from, valid_until) holds `now`, read from the
    files of candle day (now - rules._IN_FORCE_AT) in UTC. When several verify, the earliest built wins. One bad
    file never hides a good one: an unreadable file is skipped and not cached (the next call reads it again), and a
    file that fails verification for any reason is cached as None (verification is pure, so the answer cannot
    change for the same bytes). Catches every exception and returns None."""
    try:
        day = (now.astimezone(_dt.timezone.utc) - rules._IN_FORCE_AT).date()
        found = []
        for path in sorted(universe_dir(day).glob("*.json")):
            try:
                raw = path.read_bytes()
            except OSError:
                continue
            key = (sha256_hex(raw), rule_sha256)
            if key not in _UNIVERSE_VERIFIED:
                try:
                    _UNIVERSE_VERIFIED[key] = rules.verify_universe_snapshot(raw, rule_sha256)
                except Exception:
                    _UNIVERSE_VERIFIED[key] = None
            universe = _UNIVERSE_VERIFIED[key]
            if universe is not None and universe.day == day and universe.valid_from <= now < universe.valid_until:
                found.append(universe)
        return min(found, key=lambda u: (u.built_at, u.snapshot_sha256)) if found else None
    except Exception:
        return None
```

(`sha256_hex` and `rules` are already imported at the top of `owner.py`, and `_dt` at line 431. `universe_dir` is
PR 1's. `rules._IN_FORCE_AT` is PR 1's `timedelta(minutes=40)`, the same constant `verify_universe_snapshot` uses
for `valid_from` and `valid_until`, so the day choice and the window can never disagree. This is a deliberate read
of a private `rules` name, to keep one source of truth; if a guard in Step 4 objects, stop and report it rather than
copying the constant.)

- [ ] **Step 4: Run the focused and module tests**

```bash
focus compliance compliance_universe_gate
focus compliance compliance_store
focus compliance compliance_owner
focus compliance compliance_guards
focus launch launch_guards
```

Expected: all exit 0 with no FAIL row. `compliance_guards` keeps owner.py as the only `seal_context` caller and finds
no clock read. `launch_guards` keeps `execution_launch` free of `load_context`.

- [ ] **Step 5: Commit**

```bash
git add core/compliance/owner.py tests/compliance_fixtures.py tests/compliance_universe_gate.py
diff <(git diff --cached --stat) <(git diff --cached --stat --ignore-cr-at-eol) && echo "line endings intact"
git commit -m "feat(compliance): load_context reads back the universe snapshot in force" -m "_universe_in_force verifies the candle day's files under the active rule, keeps the earliest built whose window holds now, caches by file sha256, skips an unreadable file and returns None on any error, so exits never depend on it." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

Expected: `line endings intact`, then one commit with three files.

---

### Task 4: Recorded orders resolve derived coins in the controller

**Files:**
- Modify: `execution_control/controller.py:513` (`_intent` signature), `execution_control/controller.py:519`,
  `execution_control/controller.py:584` (`_exact_caps`), `execution_control/controller.py:641` (`_authorize`),
  `execution_control/controller.py:754` (`cancel`)
- Test: `tests/control_controller.py` (append)

**Interfaces:**
- Consumes: Task 2's `gate.lookup(ctx, state, venue, symbol, exits, *, recorded=False)`.
- Produces: `Controller._intent(self, order, ctx, *, recorded=False)`. `_authorize` passes
  `recorded=exclude is not None` (dispatch). `cancel` passes `recorded=True`. `reserve` stays unrecorded.

- [ ] **Step 1: Write the failing test**

Append to the end of `tests/control_controller.py`:

```python
def test_cancel_of_a_recorded_derived_coin_buy_needs_no_rule_or_snapshot():
    """Upbit KRW universe spec 8: a protective cancel of a journaled KRW-XRP buy builds its intent through _intent
    with the derived coin resolved, although the signed venues carry no universe_rule and no snapshot is in force."""
    from execution_control.capability import plain
    from execution_control.model import order_body, order_digest
    from execution_orders.model import request_digest
    with signed_control() as env:
        order=replace(env.order,client_id='xrp-order',symbol='KRW-XRP',quantity=D('10'),limit_price=D('1000'))
        rules=replace(env.rules,symbol='KRW-XRP')
        sha=order_digest(order)
        sent=request_digest(env.adapter.prepare(order,rules))
        with env.journal.transaction() as tx:
            tx.append('reserved',{'client_id':order.client_id,'order_digest':sha,'order':order_body(order),
                      'rules':plain(rules),'session_id':env.session_id,'request_digest':sent,
                      'permit_digest':'d'*64,'trade_date':''},now=env.now)
            tx.append('dispatching',{'client_id':order.client_id,'order_digest':sha,'request_digest':sent,
                      'permit_digest':'d'*64},now=env.now)
            tx.append('acknowledged',{'client_id':order.client_id,'order_digest':sha,
                      'venue_order_id':'broker-xrp','metadata':[]},now=env.now)
        ctx=owner.load_context(env.now,env.observation.positions)
        assert ctx.universe is None and ctx.active.venues.venues['upbit'].universe_rule is None
        env.adapter.results.append(AdapterResult(status='accepted',code='fixture',venue_order_id='broker-xrp',
                                                 client_id=order.client_id))
        state=env.controller.cancel(order.client_id,now=env.now)
        assert env.adapter.requests[-1].operation=='cancel' and state.venue_order_id=='broker-xrp', state
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
focus control control_controller/test_cancel_of_a_recorded_derived_coin_buy_needs_no_rule_or_snapshot
```

Expected: FAIL with `ValueError: approved cash instrument unavailable`, raised by `_intent` inside `cancel`.

- [ ] **Step 3: Implement**

In `execution_control/controller.py`, replace (line 513):

```python
    def _intent(self, order, ctx):
```

with:

```python
    def _intent(self, order, ctx, *, recorded=False):
```

Replace (line 519):

```python
        inst = gate._lookup(state, venue, symbol, order.side == 'sell') if venue else None
```

with:

```python
        inst = gate.lookup(ctx, state, venue, symbol, order.side == 'sell', recorded=recorded) if venue else None
```

In `_exact_caps`, replace (line 584):

```python
        inst=gate._lookup(state,venue,self._symbols(obj)[0],False) if venue else None
```

with:

```python
        inst=gate.lookup(ctx,state,venue,self._symbols(obj)[0],False) if venue else None
```

In `_authorize`, replace (line 641):

```python
        intent = self._intent(obj, ctx)
```

with:

```python
        intent = self._intent(obj, ctx, recorded=exclude is not None)    # dispatch: the order is in the journal
```

In `cancel`, replace (line 754):

```python
                intent=self._intent(obj,ctx)
```

with:

```python
                intent=self._intent(obj,ctx,recorded=True)
```

A recorded buy still needs the rule and the snapshot at dispatch, because `gate.permit` decides it through
`gate.decide`, whose lookup is never `recorded`.

- [ ] **Step 4: Run the focused and module tests**

```bash
focus control control_controller/test_cancel_of_a_recorded_derived_coin_buy_needs_no_rule_or_snapshot
focus control control_controller
focus control control_session
focus control control_guards
```

Expected: all exit 0 with no FAIL row.

- [ ] **Step 5: Commit**

```bash
git add execution_control/controller.py tests/control_controller.py
diff <(git diff --cached --stat) <(git diff --cached --stat --ignore-cr-at-eol) && echo "line endings intact"
git commit -m "feat(control): recorded orders resolve derived coins through gate.lookup" -m "cancel and dispatch build their intent with recorded=True, so a protective cancel of a derived-coin order is never refused; reserve and the gate decision still need the rule and the snapshot." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

Expected: `line endings intact`, then one commit with two files.

---

### Task 5: Odds plan looks legs up through gate.lookup

**Files:**
- Modify: `core/odds/plan.py:15` (import), `core/odds/plan.py:205-212` (`instrument`), `core/odds/plan.py:320` (market
  check)
- Test: `tests/odds_pipeline.py` (append)

**Interfaces:**
- Consumes: Task 2's `gate.lookup(ctx, state, venue, symbol, exits, *, recorded=False)` and
  `gate.market_listed(state, venue, inst, counter)`; Task 1's `F.universe_rule()` and `F.universe()`.
- Produces: `plan.instrument(plan, ctx)` returns the derived instrument for an Upbit KRW leg under the signed rule;
  signature unchanged.

- [ ] **Step 1: Write the failing test**

Append to the end of `tests/odds_pipeline.py`:

```python
def _with_universe_rule(state):
    """`state` with F.universe_rule() in its upbit venue facts, as a signed venues file with the rule carries it."""
    upbit = dataclasses.replace(state.venues.venues["upbit"], universe_rule=F.universe_rule())
    venues = dataclasses.replace(state.venues, venues={**state.venues.venues, "upbit": upbit})
    return dataclasses.replace(state, venues=venues)


def test_a_derived_upbit_coin_runs_under_the_rule_and_a_snapshot():
    """Upbit KRW universe spec 8: plan.instrument and the market check look the leg up through gate.lookup. A KRW-XRP
    leg runs when universe_rule is signed and XRP is eligible in ctx.universe (screen() ALLOW). Without a snapshot it
    is SCREEN_BLOCKED "state: universe no_snapshot", and without the rule it stays an unknown symbol."""
    ruled = _with_universe_rule(F.approved(venues=OF.ODDS_VENUES))
    xrp = OF.plan(symbol="XRP")
    series_obj = OF.fresh_series(symbol="KRW-XRP")
    with OF.chunk(), OF.members("bootstrap"), OF.spy(gate, "screen") as screens:
        ran = OF.pipeline(xrp, OF.odds_ctx(active=ruled, universe=F.universe()), series_obj)
        blocked = OF.pipeline(xrp, OF.odds_ctx(active=ruled), series_obj)
        unknown = OF.pipeline(xrp, OF.odds_ctx(universe=F.universe()), series_obj)
    assert ran.refused is None and ran.columns, ran.refused
    assert dict(ran.model_slots)["symbol"] == "XRP", ran.model_slots
    first = screens[0][2]
    assert first.allowed and first.decision.verdict == model.ALLOW, first.decision.reasons
    ref = blocked.refused
    assert (ref.code, ref.sub) == ("SCREEN_BLOCKED", "other") and "state: universe no_snapshot" in ref.detail, ref
    assert (unknown.refused.code, unknown.refused.sub) == ("UNSUPPORTED_PRODUCT", "symbol"), unknown.refused
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
focus odds odds_pipeline/test_a_derived_upbit_coin_runs_under_the_rule_and_a_snapshot
```

Expected: FAIL with `AssertionError: Refusal(code='UNSUPPORTED_PRODUCT', sub='symbol', ...)` on `ran.refused`.
`plan.instrument` still reads the signed map only.

- [ ] **Step 3: Implement**

In `core/odds/plan.py`, replace (line 15):

```python
from core.compliance import model
```

with:

```python
from core.compliance import gate, model
```

Replace `instrument` (lines 205-212):

```python
def instrument(plan: Plan, ctx) -> tuple[rules.Venue | None, rules.Instrument | None]:
    """The leg's venue facts and instrument from the APPROVED state in ctx.active (never a draft file); (None, None)
    when that state is not usable."""
    state, leg = getattr(ctx, "active", None), _leg(plan)
    if not _usable(state) or leg is None or type(leg.venue) is not str:
        return None, None
    venue = state.venues.venues.get(leg.venue)
    return venue, (state.instruments.lookup(venue.sections, leg.symbol) if venue is not None else None)
```

with:

```python
def instrument(plan: Plan, ctx) -> tuple[rules.Venue | None, rules.Instrument | None]:
    """The leg's venue facts and instrument from the APPROVED state in ctx.active (never a draft file), looked up as
    gate.lookup looks up a buy, so a derived Upbit KRW coin counts under the signed universe_rule (upbit KRW
    universe spec 8); (None, None) when that state is not usable."""
    state, leg = getattr(ctx, "active", None), _leg(plan)
    if not _usable(state) or leg is None or type(leg.venue) is not str:
        return None, None
    venue = state.venues.venues.get(leg.venue)
    return venue, (gate.lookup(ctx, state, venue, leg.symbol, False) if venue is not None else None)
```

Replace (line 320):

```python
        if not venue.is_market(inst, venue.quote_for(inst)):
```

with:

```python
        if not gate.market_listed(ctx.active, venue, inst, venue.quote_for(inst)):
```

- [ ] **Step 4: Run the focused and module tests**

```bash
focus odds odds_pipeline/test_a_derived_upbit_coin_runs_under_the_rule_and_a_snapshot
focus odds odds_pipeline
focus odds odds_plan
focus odds odds_guards
```

Expected: all exit 0 with no FAIL row. `odds_guards/test_core_odds_imports_only_the_allowlist` accepts
`from core.compliance import gate, model`.

- [ ] **Step 5: Commit**

```bash
git add core/odds/plan.py tests/odds_pipeline.py
diff <(git diff --cached --stat) <(git diff --cached --stat --ignore-cr-at-eol) && echo "line endings intact"
git commit -m "feat(odds): plan legs resolve through gate.lookup and gate.market_listed" -m "A derived Upbit KRW leg simulates under the signed universe_rule with the coin eligible; without a snapshot screen() refuses it, without the rule it stays an unknown symbol." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

Expected: `line endings intact`, then one commit with two files.

---

### Task 6: Compliance spec amendments, guards, full suite and PR

**Files:**
- Modify: `docs/superpowers/specs/2026-10-23-compliance-gate-and-odds-engine-design.md:291` (5.1), `:347` (5.2),
  `:459` and `:485` (6.1), `:502` (6.2 step 0), `:506` and `:508` (step 1), `:532-534` (step 5). Every quoted
  anchor below occurs exactly once in the file at fd85850.
- Test: the guard modules and the full suite

**Interfaces:**
- Consumes: Tasks 1 to 5.
- Produces: the amended compliance spec and the PR. The owner merges it; never merge it with tools.

- [ ] **Step 1: Amend the compliance spec (spec section 18), keeping LF**

Use the Edit tool for each replacement in
`docs/superpowers/specs/2026-10-23-compliance-gate-and-odds-engine-design.md`.

5.1, after the odds-terms bullet. Replace:

```markdown
  odds terms can leave a valid venue unusable for an odds plan (Task 2 accepted source-schema limitation).
```

with:

```markdown
  odds terms can leave a valid venue unusable for an odds plan (Task 2 accepted source-schema limitation).
- **Universe rule** (optional, `upbit` only; [Upbit KRW universe design](2026-11-11-upbit-krw-universe-design.md),
  section 4): `universe_rule` with `source`, `quote` (KRW), `exclude`, `min_listing_days`, `median_days` and
  `min_median_value_krw`. It admits Upbit KRW coins that no signed instrument map lists ("derived coins", 6.2 step 0)
  for new exposure, through the daily snapshot in force. Its `rule_sha256` covers the parsed rule only, so other
  edits to `venues.yaml` leave a snapshot valid.
```

5.2, What is in force. Replace:

```markdown
- A git commit is not approval.
```

with:

```markdown
- A git commit is not approval.
- **The Upbit KRW universe snapshot is runtime data admitted by the signed rule, not an approval.**
  `owner.load_context` reads the snapshot in force at `now` for the active `universe_rule` (written once and content
  addressed under `owner.universe_dir(day)`), verifies it with `rules.verify_universe_snapshot` and sets
  `Context.universe`. Any failure gives `None`, which blocks derived-coin buys and nothing else
  ([Upbit KRW universe design](2026-11-11-upbit-krw-universe-design.md), section 5).
```

6.1, Intent. Replace:

```markdown
    symbol: str                      # every intent names a mapped symbol (coins too)
```

with:

```markdown
    symbol: str                      # a mapped symbol, or a derived Upbit KRW coin (6.2 step 0)
```

6.1, Context. Replace:

```markdown
                                     # plus reservations {reservation_id: notional >= 0} and promised sell units
```

with:

```markdown
                                     # plus reservations {reservation_id: notional >= 0} and promised sell units
    universe: Universe | None = None # the verified snapshot in force for the active upbit universe_rule (5.2), or
                                     # None; hashed into ctx_hash only when set
```

6.2 step 0. Replace:

```markdown
     If it is still unknown, the result is BLOCK "close manually in the broker app".
```

with:

```markdown
     If it is still unknown, the result is BLOCK "close manually in the broker app".
   - **Derived coins** ([Upbit KRW universe design](2026-11-11-upbit-krw-universe-design.md), section 8): an
     `upbit` symbol that no approved map lists, current or earlier, and whose `KRW-<symbol>` matches
     `KRW-[A-Z][A-Z0-9]{0,11}`, resolves to a copy of the signed BTC entry under its own symbol. This happens for a
     cash sell for KRW of a coin `holdings` holds (in the active state and the snapshot, whatever the venue facts
     say), for new exposure on a venue whose approved facts carry `universe_rule`, and for an order already in the
     execution journal. A transfer of a derived coin stays an unknown symbol.
```

6.2 step 1. Replace:

```markdown
   - an unknown symbol;
```

with:

```markdown
   - an unknown symbol (a derived coin is known only as step 0 says);
```

and replace:

```markdown
   - a (`symbol`, `counter_symbol`) pair that is not a listed market of the venue;
```

with:

```markdown
   - a (`symbol`, `counter_symbol`) pair that is not a listed market of the venue (a derived coin lists only
     (coin, KRW));
```

6.2 step 5. Replace:

```markdown
   - `code_signed`.

   Then come the new-exposure part of the floor and the venue rows in force on `ctx.date` (Asia/Seoul):
```

with:

```markdown
   - `code_signed`.

   A derived coin (step 0) also needs `universe_rule` in the venue's approved facts, a `Context.universe` built under
   that rule, and the coin in its `eligible` set. Otherwise it is BLOCK "state: universe no_snapshot" or "state:
   universe not_eligible". "state: universe no_rule" is defence in depth: step 0 already leaves a derived buy without
   the rule an unknown symbol, so `decide` never reaches it. Exits (step 4) never need the snapshot.

   Then come the new-exposure part of the floor and the venue rows in force on `ctx.date` (Asia/Seoul):
```

Then check:

```bash
spec=docs/superpowers/specs/2026-10-23-compliance-gate-and-odds-engine-design.md
tr -cd '\r' < "$spec" | wc -c
git diff -U0 -- "$spec" | grep '^+' | grep -v '^+++ ' | LC_ALL=C grep -c $'\xe2\x80[\x93\x94]'
```

Expected: `0` (the file stays LF), then `0` (no added line carries an en or em dash; lines that had one at fd85850
are not touched).

- [ ] **Step 2: Commit the amendments**

```bash
git add docs/superpowers/specs/2026-10-23-compliance-gate-and-odds-engine-design.md
diff <(git diff --cached --stat) <(git diff --cached --stat --ignore-cr-at-eol) && echo "line endings intact"
git commit -m "docs(compliance): amend spec 5.1, 5.2, 6.1 and 6.2 for derived Upbit KRW coins" -m "Universe rule venue fact, the snapshot as runtime data admitted by the signed rule, Context.universe, and steps 0, 1 and 5 for derived coins (upbit KRW universe spec 18)." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

Expected: `line endings intact`, then one commit with one file.

- [ ] **Step 3: Run the guards**

```bash
focus compliance compliance_guards
focus odds odds_guards
focus control control_guards
focus accounts accounts_guards
focus launch launch_guards
focus execution execution_guards
focus compliance compliance_tables
focus launch launch_study
```

Expected: every command exits 0 with no FAIL row. `control_guards` also runs `tests/renewal_boundaries.py`. No pin
changes in this PR. If a pin fails, stop and report it; never regenerate a pin.

- [ ] **Step 4: Run the full suite**

```bash
"$PY" -X utf8 -m tests.run_all
```

Expected: exit 0, no FAIL row (NotRun PENDING rows are allowed).

- [ ] **Step 5: Push and open the PR (the owner merges)**

```bash
git push -u origin claude/upbit-universe-pr3-gate
gh pr create --base main --head claude/upbit-universe-pr3-gate --title "Upbit KRW universe PR 3: gate, read-back and public lookup" --body "$(cat <<'EOF'
## Summary

Spec: `docs/superpowers/specs/2026-11-11-upbit-krw-universe-design.md`, sections 5 (read-back), 8 and 18
(compliance-spec amendments); plan: `docs/superpowers/plans/2026-11-11-upbit-krw-universe-pr3-gate.md`.

- `Context.universe`, hashed into `ctx_hash` only when set. One `model.context_hash` now serves `seal_context` and the
  readiness, profile-preflight and review-authority integrity checks, so a context without a universe keeps today's
  hash.
- `owner.load_context` reads back the verified snapshot in force for the active `universe_rule`
  (`_universe_in_force`: window `[valid_from, valid_until)`, earliest built wins, cached by file sha256, every
  exception gives `None`).
- `gate.lookup` and `gate.market_listed` resolve derived Upbit KRW coins in three cases: for KRW exits of held coins
  (no snapshot or rule needed, active state or recovery snapshot), for new exposure under the signed rule, and for
  recorded orders. New exposure on a derived coin needs `ctx.universe` built under the rule with the coin eligible
  (`state: universe no_snapshot` or `state: universe not_eligible`). Transfers of derived coins stay blocked.
- Callers switched: gate `_validate`, `screen`, `grey_rows`; controller `_intent` (recorded for dispatch and cancel)
  and `_exact_caps`; odds `plan.instrument` and its market check.
- Compliance spec amended: 5.1, 5.2, 6.1, 6.2 steps 0, 1 and 5.

## Tests added

- `tests/compliance_model.py`: a context without a universe keeps its old `ctx_hash`; a universe changes it.
- `tests/compliance_universe_gate.py`: lookup cases; map coins unchanged; derived buys need the rule, a snapshot and
  eligibility; held-coin KRW exits with no snapshot, with the rule dropped and in the recovery state; transfers
  blocked; the step 5 reasons; `screen` and `grey_rows` on a derived coin; read-back in force, the 09:40 KST
  switch, earliest built and the cache, tampered and foreign-rule files, a `TypeError` in the read-back with a
  held-coin exit still ALLOW_EXIT, and no `execution*` import.
- `tests/control_controller.py`: cancel of a recorded KRW-XRP buy with no rule and no snapshot.
- `tests/odds_pipeline.py`: `simulate` on a derived eligible coin, refused without a snapshot or the rule.

## Not verified

- No signed venues file carries `universe_rule`; the owner adds and signs it after code-approve (spec 16).
- Snapshot files are written only by PR 2's writer; these tests write them through a fixture in a temp home.
- Nothing ran against an exchange or the real state root.
- `dispatch` of a recorded derived-coin order has no test of its own; `cancel` is tested end to end.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

Expected: the PR URL. Do not merge; the owner merges on GitHub.

---

## Self-review

- **Spec 8:**
  - `Context.universe` is sealed in Task 1.
  - In Task 2, `test_held_coin_krw_exits_need_no_snapshot_and_survive_a_dropped_rule` covers exits that need no
    snapshot, both in the active state and in the recovery state, and with the quantity checked by `_within_free`.
  - Buys that need the rule, a snapshot in force and eligibility are covered in Task 2, and end to end in Task 3.
  - Recorded orders: Task 4 tests `cancel` end to end. `dispatch` gets `recorded=True` through `_authorize` but has no
    test of its own here, because `gate.permit` still decides a dispatched buy through `gate.decide`, which needs
    the rule and the snapshot; Task 2's `recorded=True` lookup cases cover the lookup itself.
  - In Task 2, `_retired` is false and the market test accepts (coin, KRW).
  - Public `lookup` is used at gate 156, 630 and 677 (Task 2), at controller 519 and 584 (Task 4), and in
    `plan.instrument` and plan 320 (Task 5).
  - `_transfer` at 257 is unchanged (Task 2, `test_a_derived_coin_never_transfers`).
- **Spec 5 read-back:** Task 3 covers every rule:
  - the snapshot in force for the active rule;
  - the earliest built wins;
  - every exception gives None;
  - the sha256 cache.
- **Spec 18:** Task 6 amends sections 5.1, 5.2, 6.1 and 6.2. The five "single market" docs are PR 5's, per the index.
- **Spec 19 tests:** every item named in the scope maps to a test in Tasks 2 to 5.
- **Types:**
  - `gate.lookup(ctx, state, venue, symbol, exits, *, recorded=False)` and
    `gate.market_listed(state, venue, inst, counter)` are used identically in Tasks 2, 4 and 5.
  - `F.universe_rule()` and `F.universe(...)` are defined in Task 1 and used in Tasks 2, 3 and 5.
  - `F.universe_file(rule, day, **changes)` is defined and used in Task 3.
