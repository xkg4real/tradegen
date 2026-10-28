### Task 5: Plan types, injected inputs and the product, state and data checks (`core/odds/plan.py`)

**Files:**
- Create: `core/odds/plan.py` (LF, UTF-8, no BOM; a D14 closure file: `core/odds/*.py` joins the code hash through the
  `code_files` glob seed, and its only in-repo import, `core.compliance.model`, is in the closure already)
- Modify: `tests/odds_fixtures.py` (anchor: the end of the file, after `pilots()`, as Task 1 wrote it; LF, kept)
- Create: `tests/odds_plan.py` (LF; Task 1 already lists `"odds_plan"` in `tests/odds_acceptance.MODULES`)
- Test: `tests/odds_plan.py` (25 tests)

**Interfaces:**
- Consumes (names as of `5816d3c`; the follow-up renames none of them):
  - `core.compliance.model`: `canonical_json(obj) -> str`, `sha256_hex(data) -> str`, `KST`, `is_sealed(ctx) ->
    bool`, `OwnerState` (`.ok`, `.reason`, `.limits`, `.caps`, `OwnerState.broken(reason)`), `ApprovedState`
    (`.valid`, `.reason`, `.rules`, `.instruments`, `.venues`; `ApprovedState.invalid(reason)`), `Context`
    (`.date`, `.active`, `.owner`, `.code_signed`).
  - `core.compliance.rules`: `Instrument` (`.section`, `.cls`, `.multiple`, `.tax_basis`), `InstrumentMap.entries`
    and `InstrumentMap.lookup(sections, symbol) -> Instrument | None`, `VenueFacts.venues`, `Venue.sections`; in the
    tests also `VENUES`, `CLASSES`, `TAX_BASES` and `parse_instruments(raw)`. From Task 2: `Venue.lot`,
    `Venue.min_order`, `Venue.fee_extras`, `Venue.odds_sources`, `Venue.lot_for(symbol)`,
    `Venue.min_order_for(quote)`, `Venue.ladder_for(book)`, and the parser that accepts the four odds keys.
  - `core.compliance.owner._LIMIT_KEYS` (tests only: the limit keys owner.py signs).
  - `tests.compliance_fixtures` as `F`: `approved(rules=None, instruments=None, venues=None)`, `ctx(**overrides)`
    (date 2026-10-23, owner caps `{"okx_equity_share": 0.10}`, limits `{"total_loss_floor_krw": 21_000.0,
    "daily_loss_krw": 5_000.0}`, `code_signed=True`), `shipped_bytes(kind)`; the harness's `temp_home()`.
  - Task 1: `tests/odds_fixtures.py` (with `chunk()` and `pilots()`), `tests/odds_acceptance.py` (`MODULES` holds
    `"odds_plan"`; `_wrap` runs each test hermetic in a temp home) and `tests/odds_guards.py` (it scans the new
    `core/odds/plan.py`).
- Produces (CONTRACT section 5, exact; Tasks 6 to 18 rely on these names):
  - `core.odds.plan` constants: `REFUSALS`, `VENUES_OK`, `CLASSES_OK`, `TRACKS`, `MODELS`, `SIZINGS`,
    `REPLAY_SOURCE`, `EDGE_SOURCES`, `FRACTION_KINDS`, `TAX_BASES_OK`, `MAX_HORIZON_DAYS = 366`, `MIN_BARS = 250`,
    `SPECIAL_REGIME_BARS = 60`, `STALE_DAYS = {"CRYPTO": 3, "KR": 14, "US": 14}`, `LIMIT_KEYS`, `OKX_CAP_KEY`,
    `FEEDS`, `MARKET`.
  - Types, all `@dataclass(frozen=True, kw_only=True)`: `Bracket(take_profit, stop)`, `Fraction(kind, value=None)`,
    `Leg(venue, symbol, model, bracket=None, sizing="floor_safe", edge_source="none", assumed_p=None)`,
    `Plan(name, track, stake_krw, target_krw, fx_krw_per_usd, start, horizon_days, leg, fraction)`,
    `Refusal(code, sub="", slots={}, detail="")`, `Series(symbol, source, dates, open, close, adjustment, status,
    md5, components=(), proxy_dates=None)`, `Provenance(repo_anchor, tree_hash, cryptography)`,
    `ReplayInput(card_id, input_symbol, input_source, input_dates, input_close, oos_dates, oos_pnl, oos_turnover,
    lookbacks, mas, grid, cost_bps_per_side, embargo, n_trials, seed, domain, protocol, gate_protocol, stats,
    results_md5, card_md5)` and `Inputs(now, series, sessions, price_limits, calendar_sha256,
    calendar_version, calendar_md5s, calendar_error, replay, comparison_id, run_counter, comparison_plans,
    comparison_typed, plan_runs, provenance)`; the constructors `fixed(f) -> Fraction` (value `float(f)`),
    `kelly(c) -> Fraction`, `bold() -> Fraction`.
  - Functions: `series_md5(symbol, source, dates, open_, close, adjustment, status) -> str`;
    `plan_hash(plan) -> str`; `instrument(plan, ctx) -> tuple[rules.Venue | None, rules.Instrument | None]`;
    `section(plan, ctx) -> str | None`; `check_plan(plan, ctx) -> Refusal | None`;
    `check_state(plan, ctx) -> Refusal | None`; `check_now(ctx, now) -> Refusal | None`;
    `check_data(plan, ctx, inputs, market: str) -> Refusal | None`; `check_history(plan, inputs, market: str) ->
    Refusal | None`. `market` is always `MARKET[(leg.venue, section)]`: a plan that passed `check_plan` on a usable
    `ctx.active` has that key, because `check_plan` refuses sub `feed` for a venue and section with no `FEEDS` entry.
    `check_plan`, `check_state` and `check_now` never raise; `check_data` and `check_history` expect a plan that
    passed `check_plan` and a `market` key of `STALE_DAYS`.
  - The Refusal codes and subs these checks return, which Task 12's catalogue renders and Task 13's pipeline orders:
    `MULTI_LEG_UNSUPPORTED` (two or more legs); `UNSUPPORTED_PRODUCT` with sub `file`, `track`, `numbers`, `start`,
    `horizon`, `model`, `sizing`, `fraction`, `bracket`, `edge`, `replay`, `venue`, `feed` (an OKX symbol other than
    BTC, or a venue and section with no `FEEDS` entry), `symbol`, `class`,
    `multiple` or `tax`; `STATE_UNUSABLE` (sub `""`, or `code` for unsigned code); `LIMITS_UNSET` (sub `""`, or `cap`
    for an OKX leg); `DATA_INVALID` with sub `now`, `series`, `stale` (slots `{"days": "3"}` or `{"days": "14"}`),
    `sessions` or `empty`; `SYNTHETIC_REFUSED`; `SPECIAL_REGIME` and `SHORT_HISTORY` (slots `{"symbol": <leg
    symbol>}`). Every other refusal carries no slots; `detail` is internal text, never rendered.
  - Private helpers later tasks of this module may reuse: `_leg(plan) -> Leg | None`, `_usable(state) -> bool` (the
    gate's `_usable` rule), `_is(value, members) -> bool`, `_float(value) -> bool`, `_real(value) -> bool` (the
    gate's `_number` rule), `_iso(value) -> bool`, `_cap_ok(cap) -> bool` (the gate's `_cap` rule); module-private:
    `_ISO`, `_SHA`,
    `_fraction_ok`, `_edge_ok`, `_product`, `_series_problem`, `_sessions_problem`.
  - `tests/odds_fixtures.py`: `ODDS_VENUES: bytes`, `venues_with(**changes) -> bytes`, `series(*, symbol="KRW-BTC",
    source="UPBIT", n=600, seed=1, start=None, vol=0.02, open_gap=0.0, price=50_000_000.0, step_days=1) ->
    plan.Series`, `plan(**changes) -> plan.Plan`, `odds_ctx(**overrides) -> model.Context`; private `_UNVERIFIED`,
    `_ODDS_KEYS`, `_LEG_FIELDS`, `_KRX_LADDER`, `_zero_extras`, `_ODDS_DOC`, `_NoAliases`, `_dump`.
  - A contract for the plan-file loader of Task 18: `Plan.stake_krw`, `target_krw` and `fx_krw_per_usd` must be
    Python floats (a JSON int is converted with `float()` there), and a one-item `legs` list is built as
    `Plan(leg=<that Leg>)`, so every step after `check_plan` can read `plan.leg` as a Leg.

**Plan decisions used:** Q4 (plan types, the whitelist, facts from the approved map), Q7 (refused venues and
feeds), Q8 (SPECIAL_REGIME below 60 KRX bars), Q11 (the OKX cap rule of the precheck), Q23 (horizon 1 to 366 days,
SHORT_HISTORY below 250 bars), Q24 (codes and their order inside each check), Q25 (field ranges), Q37 (the name and
`detail` never render), Q39 (injected-data checks, STALE_DAYS accepted by R2-8), Q40 (fixtures), Q42 (purity), Q46
item 8 (the start-date, unsigned-code and OKX-cap prechecks and the `stale` and `empty` subs are new refusals);
R2-3 (the leg-count rule below is listed under "For spec rev 3.3"); R2-8; O3-6 (the `series()` default, the
leg-count rule and the plan-file loader contract); R2-13 (this task edits no file of `5816d3c`, so the DRIFT RULE
only covers the names it consumes).

What this task does and why:
- `core/odds/plan.py` is the first module of the signed core. It holds the plan types of spec 7.1, the injected-input
  types the unsigned side fills (CONTRACT 5.2), the nineteen refusal codes of Q24 and the checks that need no prices
  or costs. It imports only `dataclasses`, `hashlib`, `math`, `re`, `collections.abc`, `datetime`, `typing` and
  `core.compliance.model` (and `core.compliance.rules` under `TYPE_CHECKING`, for annotations only), so it passes the
  O1 allowlist, reads no clock, opens no file and adds no other file to the D14 closure.
- Each check returns the first refusal it finds, in the order Q24 fixes, and simulate (Task 13) calls them in that
  order: `check_plan` (step 2), `check_state` (steps 3 and 4), `check_now` (step 5), `check_data` (step 7), then,
  after `costs.terms` and `costs.check_validity` (step 8), `check_history` (step 9).
- `check_plan` follows CONTRACT 5.3. Inside UNSUPPORTED_PRODUCT the rules run in a fixed order: types and ranges
  first (`file`, `track`, `numbers`, `start`, `horizon`, then the leg: `model`, `sizing`, `fraction`, `bracket`,
  `edge`, `replay`), then the venue and the feed, and only on a usable `ctx.active` the instrument rules (`symbol`,
  `feed`, `class`, `multiple`, `tax`). Instrument facts come from the APPROVED map in `ctx.active`, never the draft
  file: a symbol the draft lists but the approved map does not is refused `symbol`. With no usable state the
  instrument rules are skipped and `check_state` refuses STATE_UNUSABLE.
  - The second `feed` rule: the venue parser accepts any of krx, us and crypto as a venue's sections, so an
    owner-signed venue file may give kis the crypto section. Then `kis BTC` finds class `coin`, and Task 13's
    `MARKET[(leg.venue, inst.section)]` would raise KeyError. So a venue and section with no `FEEDS` entry is refused
    `feed` right after `symbol`.
  - Cash and long are structural: a `Leg` has no side, financing or option field. The plan file refuses any other
    key (Task 18), and an option in the approved map derives class `option`, which is refused `class`.
  - The `multiple` rule is defensive: the loader derives `etp_1x`, `share` and `coin` only at +1, so a parsed map
    never reaches it. A hand-built map pins it.
  - Contract 5.3 reads "MULTI_LEG_UNSUPPORTED unless exactly one Leg". Here MULTI_LEG_UNSUPPORTED is returned for two
    or more items, because its catalogue sentence says "more than one leg". An empty list, or one item that is not a
    Leg, is UNSUPPORTED_PRODUCT sub `file`. One Leg in a one-item list or tuple is checked as that leg. RULINGS_ROUND3
    O3-6 adopts this into CONTRACT 3.2, 5.3 and 14.2. Spec 7.1 names MULTI_LEG_UNSUPPORTED with no condition, so
    this rule is also a departure from the spec text: the plan header's "For spec rev 3.3" list carries it, and
    Task 19 folds it into rev 3.3.
  - The three plan numbers must be finite Python floats (sub `numbers`), so `plan_hash` never depends on whether a
    number was typed as `42000` or `42000.0`. `start` must be exactly a `date` (a `datetime` or a date subclass is
    refused) equal to `ctx.date`, which is the gate's own rule in `gate._screen` (`type(start) is model.date`,
    `start != ctx.date`). `horizon_days` must be an int (never a bool) from 1 to 366.
- `check_state` refuses STATE_UNUSABLE for an unsealed context, an owner state that is not OK, or an unusable
  approved state (the gate's `_usable`), with the reason in `detail`; sub `code` when `ctx.code_signed` is not True
  (`screen` would BLOCK it anyway). Then LIMITS_UNSET unless both `LIMIT_KEYS` are present (a floor of 0 is a set
  value), and for an OKX leg sub `cap` unless `ctx.owner.caps.get("okx_equity_share")` passes the gate's `_cap` rule
  (a finite float or an int below 2**63, never a bool, in (0, 1]). It reads the cap with `.get`, so no KeyError.
- `check_now` refuses DATA_INVALID sub `now` unless `now` is an aware datetime whose Asia/Seoul date is `ctx.date`.
  An out-of-range moment (OverflowError) and a tzinfo whose `utcoffset` is not a timedelta (TypeError) are refusals
  too. It runs before the calendar step because `owner.calendar_in_force` raises on a naive `now`.
- `check_data` runs the Q39 rules in the order `series`, `stale`, `sessions`, `empty`, then SYNTHETIC_REFUSED:
  - `series`: an exact `Series`; one length >= 2 for dates, opens and closes; every price > 0 and a finite float or
    an int below 2**63, never a bool (`_real`, the gate's `_number` rule, so a huge int is refused, never converted to
    a float); every date a `YYYY-MM-DD` calendar date (the regex is needed because `date.fromisoformat`
    also takes week dates such as `2025-W52-6`); dates strictly increasing and all before the start; the md5
    recomputed here equal to `series.md5`.
  - `stale`: the last bar more than `STALE_DAYS[market]` calendar days before the start.
  - `sessions`: strictly increasing ISO dates inside `[start, start + horizon_days)`; for KR one price limit in
    (0, 1) per session, for other markets none; a 64-hex lower-case calendar sha for KR and US, `""` for crypto.
  - `empty`: no session at all.
  The core can check only shapes and hashes of what unsigned code passes in; the card says so (Q14).
- `check_history` counts the bars dated before the start. For a KR leg below 60 it is SPECIAL_REGIME (each KIS daily
  row is one KRX session, so gaps only lower the count). Then any leg below 250 is SHORT_HISTORY.
- `plan_hash` is the sha256 of the canonical JSON of the plan with its name blanked, so renaming a plan changes
  nothing (8.o 8). `series_md5` is the md5 of the canonical JSON of the seven series fields (spec 7.2 "Data rules").
- The fixtures follow CONTRACT 3.2, with one change: `series(start=None)` (the contract wrote `start="2024-01-01"`)
  ends the walk on 2026-10-22, the day before `plan()`'s start. With the contract's default, 600 daily bars would
  end on 2025-08-22, and `check_data` would refuse every default series as `stale`. An explicit `start` still
  sets the first date.
  - `ODDS_VENUES` is a complete kis, upbit and okx venue file with every odds key, every source the UNVERIFIED
    literal. It is dumped by PyYAML with no anchors, and Task 2's parser reads it VALID against the shipped
    instrument map.
  - `venues_with` replaces or removes odds keys per venue. A mapping without a `source` gets the UNVERIFIED literal.

Before Step 1, re-read `tests/odds_fixtures.py` (Task 1's file). It must define `chunk()` and `pilots()` and none of
the names this task adds there (`ODDS_VENUES`, `venues_with`, `series`, `plan`, `odds_ctx`, `_UNVERIFIED`,
`_ODDS_KEYS`, `_LEG_FIELDS`, `_KRX_LADDER`, `_zero_extras`, `_ODDS_DOC`, `_NoAliases`, `_dump`). If one exists, stop
and rule in the execution ledger.

- [ ] **Step 1: Write the failing tests**

  **1a.** Append the Task 5 fixture block to `tests/odds_fixtures.py` (LF, kept). Use the Edit tool. Anchor: the end
  of the file, after `pilots()`; the old text is the last line of `pilots()`, its `finally:` restore, which occurs
  once in the file as Task 1 wrote it:

```text
        models.PILOT_PATHS, sim.TILT_PILOT, models.PILOT_NODES = saved
```

  The new text is that same line, then two blank lines, then the block below (the file's final newline stays after
  the block). If that line is not the file's last non-blank line (Task 1 wrote something after it), stop and rule in
  the execution ledger. The block imports what it needs itself (`# noqa: E402`, the pattern of
  `tests/compliance_fixtures.py`), and it imports `core.odds.plan` only inside the functions. So `tests/odds_fixtures`
  still imports before `core/odds/plan.py` exists, and Task 1's tests keep passing.

```python
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
```

  **1b.** Create `tests/odds_plan.py` (whole file, LF):

```python
"""Plan types, injected inputs and the product, state and data checks (odds Task 5; spec 7.1, 7.2 "Data rules";
contract 5; Q4, Q7, Q8, Q23, Q24, Q25, Q39). Helpers are prefixed `_t5_` so later tasks cannot shadow them."""
from __future__ import annotations

import dataclasses
import datetime as dt
import hashlib
import json
import math
import types

from core.compliance import model, owner, rules
from core.odds import plan as P
from tests import compliance_fixtures as F
from tests import odds_fixtures as OF

_T5_START = dt.date(2026, 10, 23)                       # F.ctx's date, a Friday
_T5_NOW = dt.datetime(2026, 10, 23, 9, 0, tzinfo=model.KST)
_T5_UTC = dt.timezone.utc
_T5_SHA = "a" * 64
_T5_OPTION = "AAPL261218C00300000"                      # fixture-only symbol; the shipped map has no option
_T5_KRX_DAYS = ("2026-10-23", "2026-10-26", "2026-10-27", "2026-10-28")
_T5_KIS = {"symbol": "005930", "source": "KIS", "price": 70_000.0}
_T5_YAHOO = {"symbol": "AAPL", "source": "YAHOO:AAPL*YAHOO:KRW=X", "price": 300_000.0}


class _T5Date(dt.date):
    """A date subclass: equal to the date it names, but not a plain date."""


class _T5BadTZ(dt.tzinfo):
    """A tzinfo whose utcoffset is not a timedelta, so datetime.utcoffset() raises TypeError."""

    def utcoffset(self, moment):
        return 5


def _t5_code(refusal) -> tuple[str, str] | None:
    return None if refusal is None else (refusal.code, refusal.sub)


def _t5_days(first: dt.date, n: int) -> tuple[str, ...]:
    return tuple((first + dt.timedelta(days=i)).isoformat() for i in range(n))


def _t5_md5(s: P.Series) -> P.Series:
    """`s` with its md5 recomputed (left as it was when a price has no canonical JSON, such as NaN)."""
    try:
        return dataclasses.replace(s, md5=P.series_md5(s.symbol, s.source, s.dates, s.open, s.close, s.adjustment,
                                                         s.status))
    except (TypeError, ValueError):
        return s


def _t5_series(base: P.Series | None = None, **changes) -> P.Series:
    """`base` (OF.series(n=300) by default) with `changes`; the md5 is recomputed unless `md5` is one of them."""
    s = dataclasses.replace(base if base is not None else OF.series(n=300), **changes)
    return s if "md5" in changes else _t5_md5(s)


def _t5_ending(last: str, n: int = 300, **kwargs) -> P.Series:
    """OF.series of n daily bars whose last bar is dated `last`."""
    first = dt.date.fromisoformat(last) - dt.timedelta(days=n - 1)
    return OF.series(n=n, start=first.isoformat(), **kwargs)


def _t5_inputs(series: P.Series, **changes) -> P.Inputs:
    """Inputs of a 10-day crypto horizon from 2026-10-23 (Task 9 adds the public OF.inputs)."""
    fields = dict(now=_T5_NOW, series=series, sessions=_t5_days(_T5_START, 10), price_limits=(),
                  calendar_sha256="", calendar_version="", calendar_md5s=(), calendar_error="", replay=None,
                  comparison_id="c000001", run_counter=1, comparison_plans=1, comparison_typed=0, plan_runs=1,
                  provenance=P.Provenance(repo_anchor="git:" + "0" * 40, tree_hash="f" * 64, cryptography="49.0.0"))
    fields.update(changes)
    return P.Inputs(**fields)


def _t5_krx(series: P.Series | None = None, **changes) -> P.Inputs:
    """Inputs of a KRX horizon: four sessions, a 30% limit each, a 64-hex calendar sha."""
    fields = {"sessions": _T5_KRX_DAYS, "price_limits": (0.3,) * 4, "calendar_sha256": _T5_SHA, **changes}
    return _t5_inputs(series if series is not None else OF.series(**_T5_KIS), **fields)


def _t5_us(series: P.Series | None = None, **changes) -> P.Inputs:
    """Inputs of a US horizon: two New York sessions, no limits, a 64-hex calendar sha."""
    fields = {"sessions": ("2026-10-23", "2026-10-26"), "calendar_sha256": _T5_SHA, **changes}
    return _t5_inputs(series if series is not None else OF.series(**_T5_YAHOO), **fields)


def _t5_ctx_with(entries: dict) -> model.Context:
    """OF.odds_ctx() whose APPROVED map has `entries` applied ((section, symbol) -> Instrument, or None to drop)."""
    state = F.approved(venues=OF.ODDS_VENUES)
    new = dict(state.instruments.entries)
    for key, inst in entries.items():
        if inst is None:
            del new[key]
        else:
            new[key] = inst
    return OF.odds_ctx(active=dataclasses.replace(state, instruments=dataclasses.replace(state.instruments,
                                                                                          entries=new)))


def _t5_option_ctx() -> model.Context:
    """OF.odds_ctx() whose approved map is the shipped one plus a US option, parsed by the real loader."""
    raw = F.shipped_bytes("instruments")
    assert raw.count(b"\ncrypto:\n") == 1
    entry = (f"  {_T5_OPTION}:\n    asset: us_option\n    multiple: 1.0\n    underlying: null\n    class: option\n"
             "    cost_book: null\n    currency: USD\n    tax_basis: unsupported\n"
             '    source: "fixture: not a real listing"\n').encode("utf-8")
    state = F.approved(instruments=raw.replace(b"\ncrypto:\n", b"\n" + entry + b"crypto:\n"), venues=OF.ODDS_VENUES)
    assert state.valid, state.reason
    assert state.instruments.entries[("us", _T5_OPTION)].cls == "option"
    return OF.odds_ctx(active=state)


def _t5_owner(**changes) -> model.OwnerState:
    return dataclasses.replace(OF.odds_ctx().owner, **changes)


# --------------------------------------------------------------------------- #
# Constants, types and fixtures
# --------------------------------------------------------------------------- #
def test_constants_are_the_contracts():
    assert P.REFUSALS == ("PARTIAL_CHUNK", "UNSUPPORTED_PRODUCT", "MULTI_LEG_UNSUPPORTED", "STATE_UNUSABLE",
                          "LIMITS_UNSET", "CALENDAR_UNSIGNED", "CALENDAR_COVERAGE", "DATA_INVALID",
                          "SYNTHETIC_REFUSED", "NOT_TRADABLE", "SPECIAL_REGIME", "SHORT_HISTORY",
                          "CARD_NOT_REPRODUCED", "MODEL_NOT_FOR_LIMITED_VENUE", "COST_DOMINATED", "STUCK_AT_START",
                          "SCREEN_BLOCKED", "ASSUMED_EDGE_UNREACHABLE", "MODEL_CHECK_FAILED")
    assert P.VENUES_OK == ("kis", "upbit", "okx") and set(P.VENUES_OK) <= rules.VENUES
    assert P.CLASSES_OK == ("share", "etp_1x", "coin") and set(P.CLASSES_OK) <= rules.CLASSES
    assert P.TAX_BASES_OK == ("krx_small_holder_exempt", "overseas_22pct_over_2.5m", "crypto_22pct_from_2027")
    assert set(P.TAX_BASES_OK) == rules.TAX_BASES - {"unsupported"}
    assert P.TRACKS == ("moonshot", "compounding") and P.MODELS == ("bootstrap", "garch_t")
    assert P.SIZINGS == ("floor_safe", "stop_based") and P.FRACTION_KINDS == ("fixed", "kelly", "bold")
    assert P.REPLAY_SOURCE == "replay:S_C3_crypto_trend_krwbtc"
    assert P.EDGE_SOURCES == ("none", "assumed", P.REPLAY_SOURCE)
    assert (P.MAX_HORIZON_DAYS, P.MIN_BARS, P.SPECIAL_REGIME_BARS) == (366, 250, 60)
    assert P.STALE_DAYS == {"CRYPTO": 3, "KR": 14, "US": 14}                          # R2-8
    assert P.LIMIT_KEYS == owner._LIMIT_KEYS == ("total_loss_floor_krw", "daily_loss_krw")
    assert P.OKX_CAP_KEY == "okx_equity_share" and P.OKX_CAP_KEY in OF.odds_ctx().owner.caps
    assert P.FEEDS == {("kis", "krx"): "kis_daily", ("kis", "us"): "yfinance", ("upbit", "crypto"): "upbit_daily",
                       ("okx", "crypto"): "binance_x_upbit_usdt"}
    assert P.MARKET == {("kis", "krx"): "KR", ("kis", "us"): "US", ("upbit", "crypto"): "CRYPTO",
                        ("okx", "crypto"): "CRYPTO"}
    assert set(P.MARKET.values()) == set(P.STALE_DAYS) and set(P.MARKET) == set(P.FEEDS)


def test_types_are_frozen_kw_only_dataclasses():
    for cls in (P.Bracket, P.Fraction, P.Leg, P.Plan, P.Refusal, P.Series, P.Provenance, P.ReplayInput, P.Inputs):
        assert dataclasses.is_dataclass(cls) and cls.__dataclass_params__.frozen, cls
        assert all(f.kw_only for f in dataclasses.fields(cls)), cls
    assert P.fixed(1) == P.Fraction(kind="fixed", value=1.0) and type(P.fixed(1).value) is float
    assert P.kelly(0.5) == P.Fraction(kind="kelly", value=0.5) and P.bold() == P.Fraction(kind="bold")
    assert P.bold().value is None
    refusal = P.Refusal(code="LIMITS_UNSET")
    assert (refusal.sub, dict(refusal.slots), refusal.detail) == ("", {}, "")
    leg = P.Leg(venue="upbit", symbol="BTC", model="bootstrap")
    assert (leg.bracket, leg.sizing, leg.edge_source, leg.assumed_p) == (None, "floor_safe", "none", None)
    s = OF.series(n=3)
    assert (s.components, s.proxy_dates) == ((), None)
    try:
        leg.venue = "okx"
    except dataclasses.FrozenInstanceError:
        pass
    else:
        raise AssertionError("Leg is not frozen")


def test_odds_venues_parse_valid_with_every_odds_key():
    state = F.approved(venues=OF.ODDS_VENUES)
    assert state.valid, state.reason
    assert set(state.venues.venues) == {"kis", "upbit", "okx"}
    kis, upbit, okx = (state.venues.venues[v] for v in ("kis", "upbit", "okx"))
    assert kis.lot == (("005930", 1.0), ("069500", 1.0), ("default", 1.0))           # the KRX codes stay text
    assert upbit.lot == okx.lot == (("default", 1e-8),)
    assert (kis.min_order, upbit.min_order, okx.min_order) == ((("KRW", 0.0), ("USD", 0.0)), (("KRW", 5000.0),),
                                                               (("USDT", 1.0),))
    assert (kis.lot_for("005930"), kis.lot_for("069500"), kis.lot_for("AAPL")) == (1.0, 1.0, 1.0)
    assert (kis.min_order_for("KRW"), kis.min_order_for("USD")) == (0.0, 0.0)
    assert kis.fee_extras == upbit.fee_extras == okx.fee_extras == (0.0, 0.0)
    assert kis.ladder_for("KRX_stock_book") == ("2026-10-02", ((0.0, 1.0), (2000.0, 5.0), (5000.0, 10.0),
                                                              (20000.0, 50.0), (50000.0, 100.0), (200000.0, 500.0),
                                                              (500000.0, 1000.0)))
    assert (upbit.lot_for("BTC"), upbit.lot_for("USDT"), upbit.min_order_for("KRW")) == (1e-8, 1e-8, 5000.0)
    assert (okx.lot_for("BTC"), okx.min_order_for("USDT"), okx.min_order_for("USDC")) == (1e-8, 1.0, None)
    assert upbit.ladder_for("crypto_venue") is None and okx.ladder_for("crypto_venue") is None
    assert {key for key, _src in kis.odds_sources} == {"lot", "min_order", "fee_extras", "tick_ladder"}
    assert {key for key, _src in upbit.odds_sources} == {key for key, _src in okx.odds_sources} == {
        "lot", "min_order", "fee_extras"}
    assert {src for v in (kis, upbit, okx) for _key, src in v.odds_sources} == {
        "UNVERIFIED: owner to confirm before approval"}


def test_venues_with_replaces_or_removes_one_venues_odds_keys():
    assert OF.venues_with() == OF.ODDS_VENUES
    raw = OF.venues_with(upbit={"fee_extras": None, "lot": {"units": {"BTC": 0.0001}}})
    state = F.approved(venues=raw)
    assert state.valid, state.reason
    upbit = state.venues.venues["upbit"]
    assert upbit.fee_extras is None and upbit.lot_for("BTC") == 0.0001 and upbit.lot_for("USDT") is None
    assert upbit.min_order_for("KRW") == 5000.0
    assert dict(upbit.odds_sources)["lot"] == "UNVERIFIED: owner to confirm before approval"
    full = F.approved(venues=OF.ODDS_VENUES).venues.venues
    assert state.venues.venues["kis"] == full["kis"] and state.venues.venues["okx"] == full["okx"]
    gone = F.approved(venues=OF.venues_with(kis={"tick_ladder": None})).venues.venues["kis"]
    assert gone.ladder_for("KRX_stock_book") is None and gone.lot_for("005930") == 1.0
    for bad in ({"bithumb": {"lot": None}}, {"upbit": {"markets": None}}):
        try:
            OF.venues_with(**bad)
        except KeyError:
            continue
        raise AssertionError(f"venues_with accepted {bad}")


def test_fixture_defaults_pass_every_check():
    p, ctx = OF.plan(), OF.odds_ctx()
    assert model.is_sealed(ctx) and ctx.date == p.start == _T5_START and ctx.equity_krw == 42_000.0
    assert ctx.code_signed is True and ctx.active.valid
    assert dict(ctx.owner.limits) == {"total_loss_floor_krw": 21_000.0, "daily_loss_krw": 5_000.0}
    assert dict(ctx.owner.caps) == {"okx_equity_share": 0.10}
    assert (p.track, p.stake_krw, p.target_krw, p.fx_krw_per_usd, p.horizon_days) == (
        "compounding", 42_000.0, 42_000_000.0, 1_400.0, 10)
    assert p.leg == P.Leg(venue="upbit", symbol="BTC", model="bootstrap") and p.fraction == P.fixed(1.0)
    s = OF.series()
    assert len(s.dates) == 600 and s.dates[-1] == "2026-10-22" and s.dates[0] == "2025-03-02"
    assert s == OF.series() and s.md5 == _t5_md5(s).md5 and s.status == "final" and s.adjustment == ""
    assert s.open[0] == 50_000_000.0 and s.open[1:] == s.close[:-1]                  # open_gap 0
    assert OF.series(start="2024-01-01", n=3).dates == ("2024-01-01", "2024-01-02", "2024-01-03")
    inputs = _t5_inputs(s)
    assert P.check_plan(p, ctx) is None and P.check_state(p, ctx) is None and P.check_now(ctx, _T5_NOW) is None
    assert P.check_data(p, ctx, inputs, "CRYPTO") is None and P.check_history(p, inputs, "CRYPTO") is None
    widened = OF.plan(stake_krw=50_000, target_krw=60_000, fx_krw_per_usd=1_350)
    assert (widened.stake_krw, widened.target_krw, widened.fx_krw_per_usd) == (50_000.0, 60_000.0, 1_350.0)
    assert all(type(x) is float for x in (widened.stake_krw, widened.target_krw, widened.fx_krw_per_usd))
    assert OF.plan(venue="kis", symbol="005930").leg == P.Leg(venue="kis", symbol="005930", model="bootstrap")


# --------------------------------------------------------------------------- #
# Product checks (Q4, Q7, Q24 step 2, Q25)
# --------------------------------------------------------------------------- #
def test_whitelist_passes_the_supported_legs():
    ctx = OF.odds_ctx()
    for venue, symbol, sect in (("kis", "005930", "krx"), ("kis", "069500", "krx"), ("kis", "AAPL", "us"),
                                ("kis", "SPY", "us"), ("upbit", "BTC", "crypto"), ("upbit", "USDT", "crypto"),
                                ("okx", "BTC", "crypto")):
        p = OF.plan(venue=venue, symbol=symbol)
        assert P.check_plan(p, ctx) is None, (venue, symbol, P.check_plan(p, ctx))
        facts, inst = P.instrument(p, ctx)
        assert facts is ctx.active.venues.venues[venue], (venue, symbol)
        assert inst is ctx.active.instruments.entries[(sect, symbol)], (venue, symbol)
        assert P.section(p, ctx) == sect and P.MARKET[(venue, sect)] in P.STALE_DAYS


def test_whitelist_refuses_everything_else_with_its_sub():
    ctx = _t5_option_ctx()
    cases = {("bithumb", "BTC"): "venue", ("coinone", "BTC"): "venue", ("korbit", "BTC"): "venue",
             ("gopax", "BTC"): "venue", ("binance", "BTC"): "venue", ("nowhere", "BTC"): "venue",
             ("okx", "USDT"): "feed", ("okx", "USDC"): "feed", ("kis", "TQQQ"): "class", ("kis", "252670"): "class",
             ("kis", "114800"): "class", ("kis", "SH"): "class", ("kis", "IBIT"): "class", ("kis", "BITO"): "class",
             ("kis", _T5_OPTION): "class", ("upbit", "DOGE"): "symbol", ("upbit", "005930"): "symbol",
             ("kis", "BTC"): "symbol"}
    for (venue, symbol), sub in cases.items():
        got = P.check_plan(OF.plan(venue=venue, symbol=symbol), ctx)
        assert _t5_code(got) == ("UNSUPPORTED_PRODUCT", sub), (venue, symbol, got)
        assert got.detail and not got.slots, (venue, symbol)
    assert P.check_plan(OF.plan(venue="kis", symbol="AAPL"), ctx) is None        # the option map keeps the rest


def test_instrument_facts_come_from_the_approved_map_never_the_draft():
    shipped = rules.parse_instruments(F.shipped_bytes("instruments")).entries
    assert ("us", "AAPL") in shipped                                   # the draft lists AAPL,
    ctx = _t5_ctx_with({("us", "AAPL"): None})                          # the approved map does not
    got = P.check_plan(OF.plan(venue="kis", symbol="AAPL"), ctx)
    assert _t5_code(got) == ("UNSUPPORTED_PRODUCT", "symbol"), got
    assert P.instrument(OF.plan(venue="kis", symbol="AAPL"), ctx)[1] is None
    base = F.approved(venues=OF.ODDS_VENUES).instruments.entries
    edits = {"class": (("krx", "005930"), {"cls": "etp_leveraged"}),          # the draft says share
             "multiple": (("krx", "069500"), {"multiple": 2.0}),
             "tax": (("krx", "005930"), {"tax_basis": "unsupported"})}
    for sub, (key, change) in edits.items():
        ctx = _t5_ctx_with({key: dataclasses.replace(base[key], **change)})
        got = P.check_plan(OF.plan(venue="kis", symbol=key[1]), ctx)
        assert _t5_code(got) == ("UNSUPPORTED_PRODUCT", sub), (sub, got)
    wide = F.approved(venues=OF.ODDS_VENUES.replace(b"sections: [krx, us]", b"sections: [krx, us, crypto]"))
    assert wide.valid, wide.reason                                     # a signed kis file may list crypto too,
    got = P.check_plan(OF.plan(venue="kis", symbol="BTC"), OF.odds_ctx(active=wide))
    assert _t5_code(got) == ("UNSUPPORTED_PRODUCT", "feed"), got       # but (kis, crypto) has no price feed
    assert P.check_plan(OF.plan(venue="kis", symbol="005930"), OF.odds_ctx(active=wide)) is None


def test_instrument_checks_need_a_usable_approved_state():
    ctx = OF.odds_ctx(active=model.ApprovedState.invalid("unapproved: no signed approval for rules"))
    for symbol in ("TQQQ", "NOT-LISTED"):
        p = OF.plan(venue="kis", symbol=symbol)
        assert P.check_plan(p, ctx) is None, symbol                 # no class or symbol check without a state;
        assert _t5_code(P.check_state(p, ctx)) == ("STATE_UNUSABLE", ""), symbol   # the state step refuses
        assert P.instrument(p, ctx) == (None, None) and P.section(p, ctx) is None
    assert P.instrument(OF.plan(), None) == (None, None)


def test_multi_leg_unsupported_for_two_or_more_legs():
    ctx, leg = OF.odds_ctx(), OF.plan().leg
    for legs in ((leg, leg), [leg, leg], (leg, "not a leg"), (leg, leg, leg)):
        got = P.check_plan(OF.plan(leg=legs), ctx)
        assert _t5_code(got) == ("MULTI_LEG_UNSUPPORTED", ""), (legs, got)
    assert _t5_code(P.check_plan(OF.plan(leg=(leg, leg), horizon_days=0), ctx)) == ("MULTI_LEG_UNSUPPORTED", "")
    for legs in ((), [], ("not a leg",)):                              # no leg at all is not "more than one"
        assert _t5_code(P.check_plan(OF.plan(leg=legs), ctx)) == ("UNSUPPORTED_PRODUCT", "file"), legs
    assert P.check_plan(OF.plan(leg=(leg,)), ctx) is None and P.check_plan(OF.plan(leg=[leg]), ctx) is None
    one_bad = dataclasses.replace(leg, venue="bithumb")
    assert _t5_code(P.check_plan(OF.plan(leg=(one_bad,)), ctx)) == ("UNSUPPORTED_PRODUCT", "venue")


def test_range_rules_each_refuse_with_their_sub():
    ctx, base = OF.odds_ctx(), OF.plan()
    br = P.Bracket(take_profit=0.10, stop=0.05)
    replay = P.REPLAY_SOURCE
    cases = [
        ("file", dataclasses.replace(base, name=None)), ("file", dataclasses.replace(base, name=7)),
        ("file", None), ("file", dataclasses.replace(base, leg={"venue": "upbit", "symbol": "BTC"})),
        ("track", OF.plan(track="lottery")), ("track", OF.plan(track=None)),
        ("numbers", dataclasses.replace(base, stake_krw=0.0)), ("numbers", dataclasses.replace(base, stake_krw=-1.0)),
        ("numbers", dataclasses.replace(base, stake_krw=42_000)),           # an int: the numbers are floats
        ("numbers", dataclasses.replace(base, stake_krw=math.nan)),
        ("numbers", dataclasses.replace(base, target_krw=42_000.0)),        # not above the stake
        ("numbers", dataclasses.replace(base, target_krw=math.inf)),
        ("numbers", dataclasses.replace(base, fx_krw_per_usd=0.0)),
        ("numbers", dataclasses.replace(base, fx_krw_per_usd=True)),
        ("start", dataclasses.replace(base, start="2026-10-23")),
        ("start", dataclasses.replace(base, start=dt.datetime(2026, 10, 23))),
        ("start", dataclasses.replace(base, start=_T5Date(2026, 10, 23))),  # equal to ctx.date, not a date: the gate
                                                                             # refuses it too (`type(start) is date`)
        ("start", dataclasses.replace(base, start=dt.date(2026, 10, 24))),   # not ctx.date (gate.py's own rule)
        ("start", dataclasses.replace(base, start=dt.date(2026, 10, 22))),
        ("horizon", OF.plan(horizon_days=0)), ("horizon", OF.plan(horizon_days=367)),
        ("horizon", OF.plan(horizon_days=10.0)), ("horizon", OF.plan(horizon_days=True)),
        ("model", OF.plan(model="gbm")), ("model", OF.plan(model=None)),
        ("sizing", OF.plan(sizing="aggressive")), ("sizing", OF.plan(sizing="stop_based")),   # stop_based, no bracket
        ("fraction", OF.plan(fraction=P.fixed(0.0))), ("fraction", OF.plan(fraction=P.fixed(1.5))),
        ("fraction", OF.plan(fraction=P.kelly(0.25))),                       # Kelly off the replay
        ("fraction", OF.plan(edge_source=replay, fraction=P.kelly(0.6))),
        ("fraction", OF.plan(fraction=P.bold())),                            # bold with no bracket
        ("fraction", OF.plan(fraction=P.Fraction(kind="bold", value=0.5), bracket=br)),
        ("fraction", OF.plan(edge_source=replay, bracket=br, fraction=P.bold())),   # bold never on the replay
        ("fraction", OF.plan(fraction=P.Fraction(kind="martingale", value=1.0))),
        ("fraction", OF.plan(bracket=br, fraction=P.Fraction(kind="martingale"))),  # no other kind, even bold-shaped
        ("fraction", OF.plan(fraction=1.0)),
        ("bracket", OF.plan(bracket=P.Bracket(take_profit=0.0, stop=0.05))),
        ("bracket", OF.plan(bracket=P.Bracket(take_profit=1000.5, stop=0.05))),
        ("bracket", OF.plan(bracket=P.Bracket(take_profit=0.1, stop=1.0))),
        ("bracket", OF.plan(bracket=P.Bracket(take_profit=0.1, stop=0.0))),
        ("bracket", OF.plan(bracket=P.Bracket(take_profit=math.nan, stop=0.05))),
        ("bracket", OF.plan(bracket=P.Bracket(take_profit=True, stop=0.05))),
        ("bracket", OF.plan(bracket=(0.1, 0.05))),
        ("edge", OF.plan(edge_source="magic")),
        ("edge", OF.plan(edge_source="assumed", assumed_p=0.55)),                            # no bracket
        ("edge", OF.plan(edge_source="assumed", assumed_p=0.55, bracket=br, model="garch_t")),
        ("edge", OF.plan(edge_source="assumed", assumed_p=1.0, bracket=br)),
        ("edge", OF.plan(edge_source="assumed", assumed_p=0.0, bracket=br)),
        ("edge", OF.plan(edge_source="assumed", assumed_p=None, bracket=br)),
        ("edge", OF.plan(assumed_p=0.5)),                                                    # a rate, no assumed edge
        ("replay", OF.plan(edge_source=replay, venue="okx")),
        ("replay", OF.plan(edge_source=replay, symbol="USDT")),
        ("replay", OF.plan(edge_source=replay, bracket=br)),
        ("replay", OF.plan(edge_source=replay, model="garch_t")),
        ("replay", OF.plan(edge_source=replay, bracket=br, sizing="stop_based")),
    ]
    for sub, p in cases:
        got = P.check_plan(p, ctx)
        assert _t5_code(got) == ("UNSUPPORTED_PRODUCT", sub), (sub, p, got)
    passing = [OF.plan(bracket=br), OF.plan(bracket=br, sizing="stop_based"), OF.plan(bracket=br, fraction=P.bold()),
               OF.plan(bracket=P.Bracket(take_profit=1000.0, stop=0.99)), OF.plan(track="moonshot"),
               OF.plan(bracket=br, edge_source="assumed", assumed_p=0.55), OF.plan(model="garch_t"),
               OF.plan(edge_source=replay), OF.plan(edge_source=replay, fraction=P.kelly(0.5)),
               OF.plan(horizon_days=1), OF.plan(horizon_days=366), OF.plan(fraction=P.fixed(1e-9)),
               OF.plan(name="")]
    for p in passing:
        assert P.check_plan(p, ctx) is None, (p, P.check_plan(p, ctx))


def test_product_refusals_come_in_the_contract_order():
    ctx = OF.odds_ctx()
    first = [("file", dataclasses.replace(OF.plan(track="lottery"), name=None)),
             ("track", OF.plan(track="lottery", horizon_days=0)),
             ("start", OF.plan(start=dt.date(2026, 10, 24), horizon_days=0)),
             ("horizon", OF.plan(venue="bithumb", horizon_days=0)),              # every range rule before the venue
             ("model", OF.plan(venue="okx", symbol="USDT", model="gbm")),
             ("venue", OF.plan(venue="bithumb", symbol="USDT")),
             ("feed", OF.plan(venue="okx", symbol="DOGE"))]                       # the feed before the symbol
    for sub, p in first:
        assert _t5_code(P.check_plan(p, ctx)) == ("UNSUPPORTED_PRODUCT", sub), (sub, P.check_plan(p, ctx))


def test_check_plan_never_raises():
    ctx, huge = OF.odds_ctx(), 10 ** 400                               # no float holds it: math.isfinite raises
    odd = [OF.plan(venue=None), OF.plan(venue=["kis"]), OF.plan(symbol=None), OF.plan(symbol=["BTC"]),
           OF.plan(venue="okx", symbol={"BTC": 1}), OF.plan(edge_source=["none"]), OF.plan(sizing={}),
           OF.plan(bracket=P.Bracket(take_profit=huge, stop=0.05)),
           OF.plan(edge_source="assumed", assumed_p=huge, bracket=P.Bracket(take_profit=0.1, stop=0.05)),
           OF.plan(fraction=P.Fraction(kind="fixed", value=huge)), "plan", 3, object()]
    for p in odd:
        got = P.check_plan(p, ctx)
        assert got is not None and got.code == "UNSUPPORTED_PRODUCT", (p, got)
    assert _t5_code(P.check_plan(OF.plan(), None)) == ("UNSUPPORTED_PRODUCT", "start")


# --------------------------------------------------------------------------- #
# State and limits (Q24 steps 3-4)
# --------------------------------------------------------------------------- #
def test_state_unusable_for_a_hand_built_context_a_broken_owner_or_an_invalid_state():
    p, good = OF.plan(), OF.odds_ctx()
    hand = dataclasses.replace(good)                                  # the same fields, never sealed
    assert not model.is_sealed(hand) and model.is_sealed(good)
    broken = OF.odds_ctx(owner=model.OwnerState.broken("no owner key yet: owner act 1"))
    invalid = OF.odds_ctx(active=model.ApprovedState.invalid("unapproved: no signed approval for rules"))
    for what, ctx in (("hand-built", hand), ("none", None), ("broken owner", broken), ("invalid state", invalid)):
        got = P.check_state(p, ctx)
        assert _t5_code(got) == ("STATE_UNUSABLE", ""), (what, got)
    assert "no owner key yet" in P.check_state(p, broken).detail
    assert "unapproved: no signed approval for rules" in P.check_state(p, invalid).detail
    for unsigned in (F.ctx(code_signed=False), OF.odds_ctx(code_signed=False)):
        got = P.check_state(p, unsigned)
        assert _t5_code(got) == ("STATE_UNUSABLE", "code"), got
    assert _t5_code(P.check_state(p, OF.odds_ctx(code_signed=False, owner=_t5_owner(limits={})))) == (
        "STATE_UNUSABLE", "code")                                      # unsigned code before the limits


def test_limits_unset_unless_both_limits_are_signed():
    p = OF.plan()
    for limits in ({"daily_loss_krw": 5_000.0}, {"total_loss_floor_krw": 21_000.0}, {}):
        got = P.check_state(p, OF.odds_ctx(owner=_t5_owner(limits=limits)))
        assert _t5_code(got) == ("LIMITS_UNSET", ""), (limits, got)
    zero = OF.odds_ctx(owner=_t5_owner(limits={"total_loss_floor_krw": 0.0, "daily_loss_krw": 5_000.0}))
    assert P.check_state(p, zero) is None                             # a floor of 0 is a set value


def test_an_okx_leg_needs_the_okx_cap():
    okx, upbit = OF.plan(venue="okx"), OF.plan()
    for caps in ({}, {"okx_equity_share": 0.0}, {"okx_equity_share": 1.5}, {"okx_equity_share": -0.1},
                 {"okx_equity_share": True}, {"okx_equity_share": "0.1"}, {"okx_equity_share": None},
                 {"another_cap": 0.1}):
        ctx = OF.odds_ctx(owner=_t5_owner(caps=caps))
        assert _t5_code(P.check_state(okx, ctx)) == ("LIMITS_UNSET", "cap"), caps
        assert P.check_state(upbit, ctx) is None, caps                # only an OKX leg needs the cap
    for cap in (0.10, 1.0, 1):
        assert P.check_state(okx, OF.odds_ctx(owner=_t5_owner(caps={"okx_equity_share": cap}))) is None, cap
    bare = OF.odds_ctx(owner=_t5_owner(caps={}, limits={}))
    assert _t5_code(P.check_state(okx, bare)) == ("LIMITS_UNSET", "")  # the limits first; no KeyError anywhere


def test_check_now_needs_an_aware_moment_on_the_context_date():
    ctx = OF.odds_ctx()
    for now in (_T5_NOW, dt.datetime(2026, 10, 22, 15, 0, tzinfo=_T5_UTC),
                dt.datetime(2026, 10, 23, 14, 59, tzinfo=_T5_UTC)):
        assert P.check_now(ctx, now) is None, now
    for now in (dt.datetime(2026, 10, 23, 9, 0), dt.date(2026, 10, 23), None, "2026-10-23T09:00:00+09:00",
                dt.datetime(2026, 10, 23, 15, 0, tzinfo=_T5_UTC),           # 2026-10-24 00:00 in Seoul
                dt.datetime(2026, 10, 22, 14, 59, tzinfo=_T5_UTC),          # 2026-10-22 23:59 in Seoul
                dt.datetime.max.replace(tzinfo=_T5_UTC), dt.datetime.min.replace(tzinfo=_T5_UTC),
                dt.datetime(2026, 10, 23, 9, 0, tzinfo=_T5BadTZ())):          # utcoffset() raises TypeError
        assert _t5_code(P.check_now(ctx, now)) == ("DATA_INVALID", "now"), now


# --------------------------------------------------------------------------- #
# Injected data (Q24 steps 7 and 9; Q8, Q23, Q39)
# --------------------------------------------------------------------------- #
def test_data_invalid_series():
    p, ctx = OF.plan(), OF.odds_ctx()
    good, later = OF.series(n=300), OF.series(n=290)              # 2025-12-27 .. and 2026-01-06 .. 2026-10-22
    dates, opens, closes = good.dates, good.open, good.close
    assert (dates[0], later.dates[1]) == ("2025-12-27", "2026-01-07") and dt.date.fromisoformat("2025-W52-6")
    bad = {"not a series": None, "a look-alike": types.SimpleNamespace(**dataclasses.asdict(good)),
           "lengths differ": _t5_series(open=opens[:-1]),
           "one bar": _t5_series(dates=dates[-1:], open=opens[-1:], close=closes[-1:]),
           "nan close": _t5_series(close=closes[:-1] + (math.nan,)),
           "inf open": _t5_series(open=(math.inf,) + opens[1:]),
           "zero open": _t5_series(open=(0.0,) + opens[1:]),
           "negative close": _t5_series(close=(-1.0,) + closes[1:]),
           "bool price": _t5_series(close=(True,) + closes[1:]),
           "text price": _t5_series(close=("1.0",) + closes[1:]),
           "huge int price": _t5_series(close=(10 ** 400,) + closes[1:]),     # refused, never made a float
           "repeated date": _t5_series(dates=dates[:-1] + (dates[-2],)),
           "dates out of order": _t5_series(dates=(dates[1], dates[0]) + dates[2:]),
           "not ISO": _t5_series(dates=dates[:-1] + ("2026/10/22",)),
           "not a calendar date": _t5_series(dates=dates[:-1] + ("2026-10-32",)),
           # the next three still increase and end before the start, so only the ISO rule refuses them
           "a time in a date": _t5_series(dates=(dates[0] + "T00",) + dates[1:]),
           "day 00": _t5_series(dates=(dates[0][:8] + "00",) + dates[1:]),
           "an ISO week date": _t5_series(later, dates=("2025-W52-6",) + later.dates[1:]),
           "a bar on the start": _t5_series(dates=dates[1:] + ("2026-10-23",)),
           "md5 differs": _t5_series(md5="0" * 32),
           "md5 of other fields": dataclasses.replace(good, source="BINANCE")}
    for what, s in bad.items():
        got = P.check_data(p, ctx, _t5_inputs(s), "CRYPTO")
        assert _t5_code(got) == ("DATA_INVALID", "series"), (what, got)
    assert P.check_data(p, ctx, _t5_inputs(good), "CRYPTO") is None
    assert P.check_data(p, ctx, _t5_inputs(OF.series(n=2)), "CRYPTO") is None          # two bars are enough here


def test_data_invalid_stale_after_three_crypto_and_fourteen_krx_or_us_days():
    ctx = OF.odds_ctx()
    crypto, krx, us = OF.plan(), OF.plan(venue="kis", symbol="005930"), OF.plan(venue="kis", symbol="AAPL")
    for last, want in (("2026-10-20", None), ("2026-10-19", ("DATA_INVALID", "stale"))):
        got = P.check_data(crypto, ctx, _t5_inputs(_t5_ending(last)), "CRYPTO")
        assert _t5_code(got) == want, (last, got)
    assert P.check_data(crypto, ctx, _t5_inputs(_t5_ending("2026-10-19")), "CRYPTO").slots == {"days": "3"}
    for last, want in (("2026-10-09", None), ("2026-10-08", ("DATA_INVALID", "stale"))):
        got = P.check_data(krx, ctx, _t5_krx(_t5_ending(last, **_T5_KIS)), "KR")
        assert _t5_code(got) == want, (last, got)
        got = P.check_data(us, ctx, _t5_us(_t5_ending(last, **_T5_YAHOO)), "US")
        assert _t5_code(got) == want, (last, got)
    assert P.check_data(krx, ctx, _t5_krx(_t5_ending("2026-10-08", **_T5_KIS)), "KR").slots == {"days": "14"}


def test_data_invalid_sessions_and_empty():
    ctx, s = OF.odds_ctx(), OF.series(n=300)
    crypto, krx, us = OF.plan(), OF.plan(venue="kis", symbol="005930"), OF.plan(venue="kis", symbol="AAPL")
    days = _t5_days(_T5_START, 10)                                     # 2026-10-23 .. 2026-11-01
    crypto_bad = {"out of order": days[::-1], "repeated": days[:2] + days[1:2], "not ISO": ("2026/10/23",),
                  "before the start": ("2026-10-22",) + days, "at start + horizon": days + ("2026-11-02",),
                  "not text": (_T5_START,)}
    for what, sessions in crypto_bad.items():
        got = P.check_data(crypto, ctx, _t5_inputs(s, sessions=sessions), "CRYPTO")
        assert _t5_code(got) == ("DATA_INVALID", "sessions"), (what, got)
    for what, changes in {"crypto with limits": {"price_limits": (0.3,) * 10},
                          "crypto with a calendar sha": {"calendar_sha256": _T5_SHA}}.items():
        got = P.check_data(crypto, ctx, _t5_inputs(s, **changes), "CRYPTO")
        assert _t5_code(got) == ("DATA_INVALID", "sessions"), (what, got)
    for what, changes in {"limits short": {"price_limits": (0.3,) * 3}, "limit 0": {"price_limits": (0.0,) * 4},
                          "limit 1": {"price_limits": (0.3, 0.3, 0.3, 1.0)},
                          "limit nan": {"price_limits": (0.3, math.nan, 0.3, 0.3)},
                          "limit bool": {"price_limits": (True, 0.3, 0.3, 0.3)},
                          "no sha": {"calendar_sha256": ""}, "upper-case sha": {"calendar_sha256": "A" * 64},
                          "short sha": {"calendar_sha256": "a" * 63}}.items():
        got = P.check_data(krx, ctx, _t5_krx(**changes), "KR")
        assert _t5_code(got) == ("DATA_INVALID", "sessions"), (what, got)
    for what, changes in {"US limits": {"price_limits": (0.3, 0.3)}, "US no sha": {"calendar_sha256": ""}}.items():
        got = P.check_data(us, ctx, _t5_us(**changes), "US")
        assert _t5_code(got) == ("DATA_INVALID", "sessions"), (what, got)
    assert P.check_data(krx, ctx, _t5_krx(), "KR") is None and P.check_data(us, ctx, _t5_us(), "US") is None
    assert P.check_data(crypto, ctx, _t5_inputs(s, sessions=days[3:5]), "CRYPTO") is None
    for market, p, inputs in (("CRYPTO", crypto, _t5_inputs(s, sessions=())),
                              ("KR", krx, _t5_krx(sessions=(), price_limits=())),
                              ("US", us, _t5_us(sessions=()))):
        got = P.check_data(p, ctx, inputs, market)
        assert _t5_code(got) == ("DATA_INVALID", "empty"), (market, got)
    stale = _t5_inputs(_t5_ending("2026-10-19"), sessions=("2026/10/23",))
    assert _t5_code(P.check_data(crypto, ctx, stale, "CRYPTO")) == ("DATA_INVALID", "stale")      # stale first,
    no_sha = _t5_krx(sessions=(), price_limits=(), calendar_sha256="")
    assert _t5_code(P.check_data(krx, ctx, no_sha, "KR")) == ("DATA_INVALID", "sessions")         # then sessions


def test_synthetic_series_are_refused_after_the_data_checks():
    p, ctx = OF.plan(), OF.odds_ctx()
    for change in ({"status": "SYNTHETIC"}, {"source": "SYNTHETIC"}):
        got = P.check_data(p, ctx, _t5_inputs(_t5_series(**change)), "CRYPTO")
        assert _t5_code(got) == ("SYNTHETIC_REFUSED", ""), (change, got)
    stale = _t5_series(_t5_ending("2026-10-19"), status="SYNTHETIC")
    assert _t5_code(P.check_data(p, ctx, _t5_inputs(stale), "CRYPTO")) == ("DATA_INVALID", "stale")


def test_special_regime_below_sixty_krx_bars():
    krx = OF.plan(venue="kis", symbol="005930")
    got = P.check_history(krx, _t5_krx(OF.series(n=59, **_T5_KIS)), "KR")
    assert _t5_code(got) == ("SPECIAL_REGIME", "") and got.slots == {"symbol": "005930"}, got
    assert _t5_code(P.check_history(krx, _t5_krx(OF.series(n=60, **_T5_KIS)), "KR")) == ("SHORT_HISTORY", "")
    assert _t5_code(P.check_history(OF.plan(), _t5_inputs(OF.series(n=59)), "CRYPTO")) == ("SHORT_HISTORY", "")
    assert _t5_code(P.check_history(OF.plan(venue="kis", symbol="AAPL"), _t5_us(OF.series(n=59, **_T5_YAHOO)),
                                    "US")) == ("SHORT_HISTORY", "")


def test_short_history_below_250_bars_before_the_start():
    for market, p, kwargs, make in (("CRYPTO", OF.plan(), {}, _t5_inputs),
                                    ("KR", OF.plan(venue="kis", symbol="005930"), _T5_KIS, _t5_krx),
                                    ("US", OF.plan(venue="kis", symbol="AAPL"), _T5_YAHOO, _t5_us)):
        got = P.check_history(p, make(OF.series(n=249, **kwargs)), market)
        assert _t5_code(got) == ("SHORT_HISTORY", "") and got.slots == {"symbol": p.leg.symbol}, (market, got)
        assert P.check_history(p, make(OF.series(n=250, **kwargs)), market) is None, market
    on_start = _t5_ending("2026-10-23", n=250)                          # 249 bars before the start, one on it
    assert _t5_code(P.check_history(OF.plan(), _t5_inputs(on_start), "CRYPTO")) == ("SHORT_HISTORY", "")


# --------------------------------------------------------------------------- #
# Hashes (spec 7.2 "Data rules"; 8.o 8)
# --------------------------------------------------------------------------- #
def test_series_md5_is_the_md5_of_the_canonical_json():
    body = {"symbol": "KRW-BTC", "source": "UPBIT", "dates": ["2026-10-21", "2026-10-22"],
            "open": [50_000_000.0, 50_100_000.5], "close": [50_100_000.5, 49_900_000.25], "adjustment": "",
            "status": "final"}
    text = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    assert text.startswith('{"adjustment":"","close":[50100000.5,49900000.25],"dates":["2026-10-21",')
    want = hashlib.md5(text.encode("utf-8")).hexdigest()
    got = P.series_md5("KRW-BTC", "UPBIT", ("2026-10-21", "2026-10-22"), (50_000_000.0, 50_100_000.5),
                       (50_100_000.5, 49_900_000.25), "", "final")
    assert got == want
    assert P.series_md5("KRW-BTC", "UPBIT", ["2026-10-21", "2026-10-22"], [50_000_000.0, 50_100_000.5],
                        [50_100_000.5, 49_900_000.25], "", "final") == want            # lists hash like tuples
    assert P.series_md5("KRW-BTC", "UPBIT", ("2026-10-21", "2026-10-22"), (50_000_000.0, 50_100_000.5),
                        (50_100_000.5, 49_900_000.25), "", "SYNTHETIC") != want


def test_plan_hash_ignores_the_name_and_nothing_else():
    a = OF.plan(name="first")
    assert P.plan_hash(a) == P.plan_hash(OF.plan(name="a quite different name")) == P.plan_hash(OF.plan(name=""))
    assert P.plan_hash(a) == model.sha256_hex(model.canonical_json(dataclasses.replace(a, name="")))
    assert len(P.plan_hash(a)) == 64 and set(P.plan_hash(a)) <= set("0123456789abcdef")
    others = [OF.plan(stake_krw=42_001.0), OF.plan(target_krw=42_000_001.0), OF.plan(fx_krw_per_usd=1_401.0),
              OF.plan(track="moonshot"), OF.plan(horizon_days=11), OF.plan(symbol="USDT"), OF.plan(model="garch_t"),
              OF.plan(fraction=P.fixed(0.5)), OF.plan(bracket=P.Bracket(take_profit=0.1, stop=0.05)),
              OF.plan(start=dt.date(2026, 10, 24))]
    hashes = {P.plan_hash(x) for x in others}
    assert len(hashes) == len(others) and P.plan_hash(a) not in hashes
```

- [ ] **Step 2: Run to verify it fails**

  Overlap check with the PowerShell tool (it must print nothing; otherwise wait and re-run):

```powershell
Get-CimInstance Win32_Process -Filter "Name LIKE 'python%'" | Where-Object { $_.CommandLine -match 'run_all' } | Select-Object ProcessId,Name,CommandLine
```

  Then from the repo root in Git Bash:

```bash
.venv/Scripts/python.exe -m tests.odds_acceptance odds_plan/
```

  Expected: a traceback, then

```
FAIL odds_plan/import ImportError: cannot import name 'plan' from 'core.odds' (C:\Users\whydi\OneDrive\Desktop\TRADEGEN\core\odds\__init__.py)

0/1 passed, 1 failed, 0 not run
```

  and exit code 1.

- [ ] **Step 3: Implement**

  Create `core/odds/plan.py` (whole file, LF, UTF-8, no BOM):

```python
"""Odds plan types, the injected-input types, the refusal codes and the product, state and data checks (spec 7.1,
7.2 "Data rules"; odds plan Q4, Q7, Q8, Q23, Q24, Q25, Q39). Pure: no clock, no file, no network. Every check
returns the first Refusal it finds, or None; check_plan, check_state and check_now never raise."""
from __future__ import annotations

import dataclasses
import hashlib
import math
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import TYPE_CHECKING

from core.compliance import model

if TYPE_CHECKING:
    from core.compliance import rules

# --------------------------------------------------------------------------- #
# Constants (contract 5.1)
# --------------------------------------------------------------------------- #
REFUSALS = ("PARTIAL_CHUNK", "UNSUPPORTED_PRODUCT", "MULTI_LEG_UNSUPPORTED", "STATE_UNUSABLE", "LIMITS_UNSET",
            "CALENDAR_UNSIGNED", "CALENDAR_COVERAGE", "DATA_INVALID", "SYNTHETIC_REFUSED", "NOT_TRADABLE",
            "SPECIAL_REGIME", "SHORT_HISTORY", "CARD_NOT_REPRODUCED", "MODEL_NOT_FOR_LIMITED_VENUE", "COST_DOMINATED",
            "STUCK_AT_START", "SCREEN_BLOCKED", "ASSUMED_EDGE_UNREACHABLE", "MODEL_CHECK_FAILED")
            # the codes; their reporting order is Q24's numbered list (DATA_INVALID sub "now" comes before CALENDAR_*)
VENUES_OK = ("kis", "upbit", "okx")
CLASSES_OK = ("share", "etp_1x", "coin")
TRACKS = ("moonshot", "compounding")
MODELS = ("bootstrap", "garch_t")
SIZINGS = ("floor_safe", "stop_based")
REPLAY_SOURCE = "replay:S_C3_crypto_trend_krwbtc"
EDGE_SOURCES = ("none", "assumed", REPLAY_SOURCE)
FRACTION_KINDS = ("fixed", "kelly", "bold")
TAX_BASES_OK = ("krx_small_holder_exempt", "overseas_22pct_over_2.5m", "crypto_22pct_from_2027")
MAX_HORIZON_DAYS = 366
MIN_BARS = 250
SPECIAL_REGIME_BARS = 60
STALE_DAYS = {"CRYPTO": 3, "KR": 14, "US": 14}     # Q39: the last bar at most this many calendar days before start
LIMIT_KEYS = ("total_loss_floor_krw", "daily_loss_krw")
OKX_CAP_KEY = "okx_equity_share"
FEEDS = {("kis", "krx"): "kis_daily", ("kis", "us"): "yfinance", ("upbit", "crypto"): "upbit_daily",
         ("okx", "crypto"): "binance_x_upbit_usdt"}    # okx: symbol BTC only
MARKET = {("kis", "krx"): "KR", ("kis", "us"): "US", ("upbit", "crypto"): "CRYPTO", ("okx", "crypto"): "CRYPTO"}

_ISO = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
_SHA = re.compile(r"[0-9a-f]{64}")


# --------------------------------------------------------------------------- #
# Types (contract 5.2)
# --------------------------------------------------------------------------- #
@dataclass(frozen=True, kw_only=True)
class Bracket:
    take_profit: float                               # +u as a fraction: 0 < u <= 1000
    stop: float                                      # -d as a fraction: 0 < d < 1


@dataclass(frozen=True, kw_only=True)
class Fraction:
    kind: str                                        # "fixed" | "kelly" | "bold"
    value: float | None = None


def fixed(f: float) -> Fraction:
    return Fraction(kind="fixed", value=float(f))


def kelly(c: float) -> Fraction:
    return Fraction(kind="kelly", value=float(c))


def bold() -> Fraction:
    return Fraction(kind="bold")


@dataclass(frozen=True, kw_only=True)
class Leg:
    venue: str
    symbol: str
    model: str                                       # "bootstrap" | "garch_t"
    bracket: Bracket | None = None                   # None: buy at the first check and hold
    sizing: str = "floor_safe"                       # "floor_safe" | "stop_based" (bracket legs only)
    edge_source: str = "none"                        # one of EDGE_SOURCES
    assumed_p: float | None = None


@dataclass(frozen=True, kw_only=True)
class Plan:
    name: str                                        # cosmetic; never hashed, never rendered
    track: str                                       # "moonshot" | "compounding"
    stake_krw: float
    target_krw: float                                # before income tax, fixed in KRW
    fx_krw_per_usd: float
    start: date                                      # the Asia/Seoul date of the run
    horizon_days: int                                # half-open [start, start + horizon_days)
    leg: Leg
    fraction: Fraction


@dataclass(frozen=True, kw_only=True)
class Refusal:
    code: str                                        # one of REFUSALS
    sub: str = ""                                    # a catalogue sub-reason key suffix, or ""
    slots: Mapping[str, str] = field(default_factory=dict)    # render slots: numbers, dates, symbols, row ids only
    detail: str = ""                                 # internal text for logs and tests; never rendered


@dataclass(frozen=True, kw_only=True)
class Series:
    symbol: str
    source: str
    dates: tuple[str, ...]                           # ISO dates, strictly increasing, all before the start
    open: tuple[float, ...]                          # KRW
    close: tuple[float, ...]                         # KRW
    adjustment: str
    status: str
    md5: str                                         # series_md5 of the seven fields above
    components: tuple[tuple[str, str], ...] = ()     # (label, md5) of each downloaded part
    proxy_dates: tuple[str, str] | None = None       # first and last date priced through the FX fallback


@dataclass(frozen=True, kw_only=True)
class Provenance:
    repo_anchor: str
    tree_hash: str
    cryptography: str                                # its version, read by the unsigned side ("absent" when missing)


@dataclass(frozen=True, kw_only=True)
class ReplayInput:
    card_id: str
    input_symbol: str
    input_source: str
    input_dates: tuple[str, ...]
    input_close: tuple[float, ...]
    oos_dates: tuple[str, ...]
    oos_pnl: tuple[float, ...]
    oos_turnover: tuple[float, ...]
    lookbacks: tuple[int, ...]
    mas: tuple[int, ...]
    grid: tuple[float, ...]
    cost_bps_per_side: float
    embargo: int
    n_trials: int
    seed: int
    domain: tuple[float, float]
    protocol: Mapping[str, float]
    gate_protocol: Mapping[str, float]
    stats: Mapping[str, object]      # sr_oos, bench_sr, haircut_sr, bench_diff, bench_ci (2-tuple), decision,
                                     # chosen_last (hysteresis float), n_sessions, n_trades
    results_md5: str
    card_md5: str


@dataclass(frozen=True, kw_only=True)
class Inputs:
    now: datetime                    # aware; the moment load_context saw
    series: Series
    sessions: tuple[str, ...]        # the horizon's session dates (each market's own date), ISO
    price_limits: tuple[float, ...]  # KRX: one per session; other legs: ()
    calendar_sha256: str             # KRX/US: rules.calendar_sha256 of the set used; crypto: ""
    calendar_version: str
    calendar_md5s: tuple[tuple[str, str], ...]       # (file id, md5)
    calendar_error: str              # "" | "unsigned: <text>" | "coverage: <text>"
    replay: ReplayInput | None
    comparison_id: str
    run_counter: int                 # the comparison's own counter, fixed when begin_run created it (Q12, Q34)
    comparison_plans: int            # K, this plan included
    comparison_typed: int            # J, this plan included
    plan_runs: int                   # R: comparisons whose plans include this plan hash, this one included (Q12)
    provenance: Provenance


# --------------------------------------------------------------------------- #
# Hashes and lookups (contract 5.3)
# --------------------------------------------------------------------------- #
def series_md5(symbol, source, dates, open_, close, adjustment, status) -> str:
    """md5 of the canonical JSON {symbol, source, dates, open, close, adjustment, status} (spec 7.2)."""
    return hashlib.md5(model.canonical_json({"symbol": symbol, "source": source, "dates": list(dates),
                                             "open": list(open_), "close": list(close), "adjustment": adjustment,
                                             "status": status}).encode("utf-8")).hexdigest()


def plan_hash(plan: Plan) -> str:
    """sha256 of the canonical JSON of the plan with its name blanked: renaming a plan changes nothing."""
    return model.sha256_hex(model.canonical_json(dataclasses.replace(plan, name="")))


def _leg(plan) -> Leg | None:
    """The plan's one Leg: plan.leg, or the only item of a one-item list or tuple; else None."""
    leg = getattr(plan, "leg", None)
    if isinstance(leg, (list, tuple)) and len(leg) == 1:
        leg = leg[0]
    return leg if type(leg) is Leg else None


def _usable(state) -> bool:
    """gate._usable: a valid ApprovedState with its three tables."""
    return (isinstance(state, model.ApprovedState) and state.valid is True and state.rules is not None
            and state.instruments is not None and state.venues is not None)


def instrument(plan: Plan, ctx) -> tuple[rules.Venue | None, rules.Instrument | None]:
    """The leg's venue facts and instrument from the APPROVED state in ctx.active (never a draft file); (None, None)
    when that state is not usable."""
    state, leg = getattr(ctx, "active", None), _leg(plan)
    if not _usable(state) or leg is None or type(leg.venue) is not str:
        return None, None
    venue = state.venues.venues.get(leg.venue)
    return venue, (state.instruments.lookup(venue.sections, leg.symbol) if venue is not None else None)


def section(plan: Plan, ctx) -> str | None:
    """The instrument's section ("krx" | "us" | "crypto"), or None."""
    inst = instrument(plan, ctx)[1]
    return inst.section if inst is not None else None


# --------------------------------------------------------------------------- #
# Checks (Q24 steps 2-5, 7 and 9; Q25, Q39)
# --------------------------------------------------------------------------- #
def _is(value, members) -> bool:
    return type(value) is str and value in members


def _float(value) -> bool:
    """A finite float (an int is refused, so a plan's hash never depends on how a number was typed)."""
    return type(value) is float and math.isfinite(value)


def _real(value) -> bool:
    """A finite float or an int below 2**63, never a bool (gate._number)."""
    if type(value) is float:
        return math.isfinite(value)
    return type(value) is int and abs(value) < 2 ** 63


def _iso(value) -> bool:
    if type(value) is not str or not _ISO.fullmatch(value):
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def _fraction_ok(frac, bracket, replay: bool) -> bool:
    """fixed(0 < f <= 1); kelly(0 < c <= 0.5) on the replay only; bold() on bracket legs only (Q25)."""
    if type(frac) is not Fraction:
        return False
    if frac.kind == "fixed":
        return _real(frac.value) and 0 < frac.value <= 1
    if frac.kind == "kelly":
        return replay and _real(frac.value) and 0 < frac.value <= 0.5
    if frac.kind == "bold":
        return frac.value is None and bracket is not None and not replay
    return False


def _edge_ok(leg: Leg) -> bool:
    """assumed: a bracket, the bootstrap model and 0 < assumed_p < 1; otherwise no assumed_p (Q25)."""
    if leg.edge_source == "assumed":
        return (leg.bracket is not None and leg.model == "bootstrap" and _real(leg.assumed_p)
                and 0 < leg.assumed_p < 1)
    return _is(leg.edge_source, EDGE_SOURCES) and leg.assumed_p is None


def _product(plan, ctx) -> tuple[str, str] | None:
    """(sub, detail) of the first UNSUPPORTED_PRODUCT rule the plan breaks, in contract 5.3's order."""
    if type(plan) is not Plan or type(plan.name) is not str:
        return "file", "not a Plan with a text name"
    if not _is(plan.track, TRACKS):
        return "track", f"track {plan.track!r}"
    stake, target, fx = plan.stake_krw, plan.target_krw, plan.fx_krw_per_usd
    if not (_float(stake) and _float(target) and _float(fx) and stake > 0 and target > stake and fx > 0):
        return "numbers", f"stake {stake!r}, target {target!r}, fx {fx!r}"
    today = getattr(ctx, "date", None)
    if type(plan.start) is not date or plan.start != today:
        return "start", f"start {plan.start!r}, context date {today!r}"
    if type(plan.horizon_days) is not int or not 1 <= plan.horizon_days <= MAX_HORIZON_DAYS:
        return "horizon", f"horizon_days {plan.horizon_days!r}"
    leg = _leg(plan)
    if leg is None:
        return "file", f"leg {plan.leg!r} is not one Leg"
    if not _is(leg.model, MODELS):
        return "model", f"model {leg.model!r}"
    if not _is(leg.sizing, SIZINGS) or (leg.sizing == "stop_based" and leg.bracket is None):
        return "sizing", f"sizing {leg.sizing!r} with bracket {leg.bracket!r}"
    replay = leg.edge_source == REPLAY_SOURCE
    if not _fraction_ok(plan.fraction, leg.bracket, replay):
        return "fraction", f"fraction {plan.fraction!r} with bracket {leg.bracket!r}"
    b = leg.bracket
    if b is not None and not (type(b) is Bracket and _real(b.take_profit) and _real(b.stop)
                              and 0 < b.take_profit <= 1000 and 0 < b.stop < 1):
        return "bracket", f"bracket {b!r}"
    if not _edge_ok(leg):
        return "edge", f"edge_source {leg.edge_source!r}, assumed_p {leg.assumed_p!r}"
    if replay and not (leg.venue == "upbit" and leg.symbol == "BTC" and b is None and leg.model == "bootstrap"
                       and leg.sizing == "floor_safe"):
        return "replay", f"replay leg {leg.venue!r} {leg.symbol!r}"
    if not _is(leg.venue, VENUES_OK):
        return "venue", f"venue {leg.venue!r}"
    if leg.venue == "okx" and leg.symbol != "BTC":
        return "feed", f"okx {leg.symbol!r} has no price feed"
    if _usable(getattr(ctx, "active", None)):
        inst = instrument(plan, ctx)[1]
        if inst is None:
            return "symbol", f"{leg.venue} {leg.symbol!r} is not in the approved instrument map"
        if (leg.venue, inst.section) not in FEEDS:         # a signed venue file may list a section with no feed
            return "feed", f"{leg.venue} has no price feed for section {inst.section}"
        if inst.cls not in CLASSES_OK:
            return "class", f"class {inst.cls}"
        if inst.multiple != 1.0:
            return "multiple", f"multiple {inst.multiple}"
        if inst.tax_basis not in TAX_BASES_OK:
            return "tax", f"tax basis {inst.tax_basis}"
    return None


def check_plan(plan, ctx) -> Refusal | None:
    """The product refusals of Q24 step 2: MULTI_LEG_UNSUPPORTED for a list or tuple of two or more legs, then
    UNSUPPORTED_PRODUCT with its sub (an empty list, or one item that is not a Leg, is sub "file"). The instrument
    checks run only on a usable ctx.active."""
    legs = getattr(plan, "leg", None)
    if isinstance(legs, (list, tuple)) and len(legs) > 1:
        return Refusal(code="MULTI_LEG_UNSUPPORTED", detail=f"{len(legs)} legs")
    found = _product(plan, ctx)
    return None if found is None else Refusal(code="UNSUPPORTED_PRODUCT", sub=found[0], detail=found[1])


def _cap_ok(cap) -> bool:
    """gate._cap's rule: a number in (0, 1] (_real: a finite float or an int below 2**63, never a bool)."""
    return _real(cap) and 0 < cap <= 1


def check_state(plan, ctx) -> Refusal | None:
    """Q24 steps 3-4: STATE_UNUSABLE (sub "code" for unsigned code), then LIMITS_UNSET (sub "cap" for an OKX leg
    without its cap). A floor of 0 is a set limit."""
    if not model.is_sealed(ctx):
        return Refusal(code="STATE_UNUSABLE", detail="state: context not from load_context")
    owner = ctx.owner
    if not (isinstance(owner, model.OwnerState) and owner.ok):
        return Refusal(code="STATE_UNUSABLE", detail=f"owner log: {getattr(owner, 'reason', '') or 'not OK'}")
    if not _usable(ctx.active):
        return Refusal(code="STATE_UNUSABLE", detail=f"state: {getattr(ctx.active, 'reason', '') or 'unusable'}")
    if ctx.code_signed is not True:
        return Refusal(code="STATE_UNUSABLE", sub="code", detail="unsigned code")
    missing = [key for key in LIMIT_KEYS if key not in owner.limits]
    if missing:
        return Refusal(code="LIMITS_UNSET", detail=f"unset: {', '.join(missing)}")
    leg = _leg(plan)
    if leg is not None and leg.venue == "okx" and not _cap_ok(owner.caps.get(OKX_CAP_KEY)):
        return Refusal(code="LIMITS_UNSET", sub="cap", detail=f"{OKX_CAP_KEY} {owner.caps.get(OKX_CAP_KEY)!r}")
    return None


def check_now(ctx, now) -> Refusal | None:
    """DATA_INVALID sub "now" unless `now` is an aware datetime whose Asia/Seoul date is ctx.date."""
    today = getattr(ctx, "date", None)
    try:
        ok = isinstance(now, datetime) and now.utcoffset() is not None and now.astimezone(model.KST).date() == today
    except (OverflowError, TypeError, ValueError):
        ok = False
    return None if ok else Refusal(code="DATA_INVALID", sub="now", detail=f"now {now!r}, context date {today!r}")


def _series_problem(s, start: date) -> str:
    """Q39 sub "series": "" when the series passes, else why not."""
    if type(s) is not Series:
        return "not a Series"
    try:
        n = len(s.dates)
        if n < 2 or len(s.open) != n or len(s.close) != n:
            return f"lengths {n}, {len(s.open)}, {len(s.close)}: need one length >= 2"
        if not all(_real(x) and x > 0 for x in (*s.open, *s.close)):
            return "a price is not a finite number > 0"
        if not all(_iso(d) for d in s.dates):
            return "a date is not an ISO calendar date"
        if any(a >= b for a, b in zip(s.dates, s.dates[1:])):
            return "dates are not strictly increasing"
        if s.dates[-1] >= start.isoformat():
            return f"the last bar {s.dates[-1]} is not before the start {start}"
        if s.md5 != series_md5(s.symbol, s.source, s.dates, s.open, s.close, s.adjustment, s.status):
            return "md5 differs from the one recomputed here"
    except (TypeError, ValueError) as exc:
        return f"unreadable ({type(exc).__name__})"
    return ""


def _sessions_problem(inputs, start: date, horizon: int, market: str) -> str:
    """Q39 sub "sessions": "" when the session list, the price limits and the calendar sha pass."""
    try:
        days, limits, sha = inputs.sessions, inputs.price_limits, inputs.calendar_sha256
        if not all(_iso(d) for d in days) or any(a >= b for a, b in zip(days, days[1:])):
            return "sessions are not strictly increasing ISO dates"
        end = (start + timedelta(days=horizon)).isoformat()
        if days and (days[0] < start.isoformat() or days[-1] >= end):
            return f"sessions {days[0]} .. {days[-1]} leave [{start}, {end})"
        if market == "KR":
            if len(limits) != len(days) or not all(_real(x) and 0 < x < 1 for x in limits):
                return "a KRX leg needs one price limit in (0, 1) per session"
        elif len(limits):
            return "price limits on a market without a daily band"
        if market in ("KR", "US") and not (type(sha) is str and _SHA.fullmatch(sha)):
            return "a KRX or US leg needs the 64-hex calendar sha"
        if market not in ("KR", "US") and sha != "":
            return "a crypto leg carries no calendar sha"
    except (AttributeError, TypeError, ValueError, OverflowError) as exc:
        return f"unreadable ({type(exc).__name__})"
    return ""


def check_data(plan, ctx, inputs, market: str) -> Refusal | None:
    """Q24 step 7 (Q39): DATA_INVALID subs "series", "stale", "sessions", "empty", in that order, then
    SYNTHETIC_REFUSED. `market` is MARKET[(venue, section)]; `ctx` is not read (simulate checks `now` and the
    calendar before this step)."""
    s, start = getattr(inputs, "series", None), plan.start
    why = _series_problem(s, start)
    if why:
        return Refusal(code="DATA_INVALID", sub="series", detail=why)
    gap = (start - date.fromisoformat(s.dates[-1])).days
    if gap > STALE_DAYS[market]:
        return Refusal(code="DATA_INVALID", sub="stale", slots={"days": str(STALE_DAYS[market])},
                       detail=f"the last bar {s.dates[-1]} is {gap} days before the start {start}")
    why = _sessions_problem(inputs, start, plan.horizon_days, market)
    if why:
        return Refusal(code="DATA_INVALID", sub="sessions", detail=why)
    if not inputs.sessions:
        return Refusal(code="DATA_INVALID", sub="empty", detail=f"no {market} session in the horizon")
    if s.status == "SYNTHETIC" or s.source == "SYNTHETIC":
        return Refusal(code="SYNTHETIC_REFUSED", detail=f"status {s.status!r}, source {s.source!r}")
    return None


def check_history(plan, inputs, market: str) -> Refusal | None:
    """Q24 step 9 (Q8, Q23): a KRX leg with fewer than SPECIAL_REGIME_BARS bars before the start is SPECIAL_REGIME;
    then any leg with fewer than MIN_BARS is SHORT_HISTORY. simulate runs it after costs.terms and check_validity."""
    first = plan.start.isoformat()
    bars = sum(1 for d in inputs.series.dates if d < first)
    slots = {"symbol": _leg(plan).symbol}
    if market == "KR" and bars < SPECIAL_REGIME_BARS:
        return Refusal(code="SPECIAL_REGIME", slots=slots, detail=f"{bars} KRX bars before {first}")
    if bars < MIN_BARS:
        return Refusal(code="SHORT_HISTORY", slots=slots, detail=f"{bars} bars before {first}")
    return None
```

- [ ] **Step 4: Run to verify it passes**

  Run each line below on its own, from the repo root in Git Bash. Every Python line starts with the overlap-check
  prefix of the Global Constraints, so it runs only when no `run_all` Python process is running. If a line prints
  nothing and exits 1 at once, the check found one: wait and re-run that line.

```bash
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && .venv/Scripts/python.exe -m tests.odds_acceptance odds_plan/
```

  Expected: 25 `PASS odds_plan/test_...` lines, then `25/25 passed, 0 failed, 0 not run` (exit code 0; about 2 s).

  Then the odds guards, which now scan `core/odds/plan.py` (the O1 allowlist, no clock, no file I/O,
  no `__main__`, no package re-export, the empty inits, the flat package):

```bash
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && .venv/Scripts/python.exe -m tests.odds_acceptance odds_guards/
```

  Expected: every line PASS and the tail `0 failed`, with the passed and not-run counts Task 1 recorded under "Runs"
  in the execution ledger (exit code 0). This task adds no guard test. A failure names the offending file and text:
  fix `plan.py`, never the guard.

  Then the compliance guards and store (Global Constraints: every task that touches `core/odds`):

```bash
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && .venv/Scripts/python.exe -m tests.compliance_acceptance compliance_guards/
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && .venv/Scripts/python.exe -m tests.compliance_acceptance compliance_store/
```

  Expected: each ends `0 failed, 0 not run` with the same passed count as at the end of Task 4 (this task adds no
  compliance test). The raw-word, forbidden-import and dynamic-import scans of `compliance_guards` cover
  `core/odds/plan.py`. `compliance_store/test_code_files_is_the_import_closure` now finds `core/odds/plan.py` through
  the glob seed and no file outside `core/__init__.py`, `core/isolation.py`, `core/compliance/*.py` and
  `core/odds/*.py`.

  Then the core-wide scans (Global Constraints: every task that changes `core/`), one line at a time:

```bash
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && .venv/Scripts/python.exe -m tests.macro_m0_harness
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && .venv/Scripts/python.exe -m tests.macro_tf_gov
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && .venv/Scripts/python.exe -m tests.macro_m7_ledger
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && .venv/Scripts/python.exe -m tests.macro_m8_forward
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && .venv/Scripts/python.exe -m tests.macro_m6_context
```

  Expected: each prints no FAIL line and ends with `0 failed` and exit code 0, with the same passed and not-run
  counts Task 1 recorded under "Runs" (`macro_m6_context` runs T-CTX-01 over the new acting module
  `core.odds.plan`).

  Then the cockpit suite (test_08, test_09, test_16, test_18) and the odds suite, each followed at once by
  restoring the tracked results file:

```bash
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && KIS_APP_KEY='<unset>' KIS_APP_SECRET='<unset>' KIS_ACCOUNT_8='<unset>' KIS_ACCOUNT_PD='<unset>' UPBIT_ACCESS_KEY='<unset>' UPBIT_SECRET_KEY='<unset>' OKX_API_KEY='<unset>' OKX_API_SECRET='<unset>' OKX_API_PASSPHRASE='<unset>' OPENDART_API_KEY='<unset>' KRX_API_KEY='<unset>' FMP_API_KEY='<unset>' ANTHROPIC_API_KEY='<unset>' GS_CLIENT_ID='<unset>' GS_CLIENT_SECRET='<unset>' FINVIZ_API_KEY='<unset>' ALPACA_API_KEY='<unset>' ALPACA_SECRET_KEY='<unset>' FXMACRODATA_API_KEY='<unset>' .venv/Scripts/python.exe tests/run_all.py --suite cockpit; echo "exit $?"; git checkout -- qa/acceptance_results.json
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && KIS_APP_KEY='<unset>' KIS_APP_SECRET='<unset>' KIS_ACCOUNT_8='<unset>' KIS_ACCOUNT_PD='<unset>' UPBIT_ACCESS_KEY='<unset>' UPBIT_SECRET_KEY='<unset>' OKX_API_KEY='<unset>' OKX_API_SECRET='<unset>' OKX_API_PASSPHRASE='<unset>' OPENDART_API_KEY='<unset>' KRX_API_KEY='<unset>' FMP_API_KEY='<unset>' ANTHROPIC_API_KEY='<unset>' GS_CLIENT_ID='<unset>' GS_CLIENT_SECRET='<unset>' FINVIZ_API_KEY='<unset>' ALPACA_API_KEY='<unset>' ALPACA_SECRET_KEY='<unset>' FXMACRODATA_API_KEY='<unset>' .venv/Scripts/python.exe tests/run_all.py --suite odds; echo "exit $?"; git checkout -- qa/acceptance_results.json
```

  Expected: the cockpit run ends with `0 failed` and the counts Task 1 recorded. The odds run lists the
  `odds/odds_guards/...` rows and the 25 `odds/odds_plan/...` rows, all PASS (or the NOT_RUN rows Task 1 recorded
  for the guards), and ends with `0 failed` and a passed count of Task 1's guard count plus 25 (exit code 0). Then
  `git status --short` lists only ` M tests/odds_fixtures.py`, `?? core/odds/plan.py`, `?? tests/odds_plan.py` and
  `?? docs/superpowers/plans/2026-10-24-odds-engine-execution-ledger.md`.

  Then the raw-text checks (git only; no overlap check needed):

```bash
git grep --untracked -n -i -E "order_cash|order-cash|place_order|submit_order|tttc0802u|tttc0801u|vttc0802u|private_key|seed_phrase|/v1/orders|/v1/withdraws|/v1/deposits|/api/v3/order|/sapi/v1/capital|/uapi/|r18_research_log|r18_break_log|context_log/|tests\.reference|reference_mode|reference_only" -- core/odds/plan.py tests/odds_plan.py tests/odds_fixtures.py
git grep --untracked -n -E "CANO|KIS_ACCOUNT|ACNT_PRDT_CD|0\.4 *[*x]|\.now\(|\.today\(|utcnow|time\.|[ (]open\(|read_text|read_bytes|write_text|write_bytes|__main__" -- core/odds/plan.py
```

  Expected: both print nothing (exit code 1).

  Append the tails of these runs, one line each, under "Runs" in the execution ledger (LF; it stays untracked).
  Then add these four lines under "Drift rulings" there (departures from the CONTRACT, not from the merged main, so
  later drafters read the contract with them):
  - `Task 5: CONTRACT 3.2 series(start=None) ends the walk on 2026-10-22 (the contract wrote start="2024-01-01": 600 daily bars would end on 2025-08-22, so check_data would refuse every default series as stale).`
  - `Task 5: CONTRACT 5.3 an empty legs list or a one-item list whose item is not a Leg is UNSUPPORTED_PRODUCT sub file; MULTI_LEG_UNSUPPORTED is returned only for 2 or more items (O3-6; also a spec 7.1 departure, listed in the plan header under "For spec rev 3.3").`
  - `Task 5: CONTRACT 5.3 the garch_t plus edge_source "assumed" rule (sub edge) runs with the range rules, on every ctx, not only on a valid ctx.active.`
  - `Task 5: CONTRACT 5.3 on a usable ctx.active a venue and section with no FEEDS entry is sub feed, right after sub symbol, so MARKET[(venue, section)] never raises in simulate.`

- [ ] **Step 5: Commit**

```bash
git add core/odds/plan.py tests/odds_plan.py tests/odds_fixtures.py
git diff --cached --stat
git diff --cached --stat --ignore-cr-at-eol
```

  The two stat outputs must be identical (all three files are LF). Then, with the `Co-Authored-By:` line of the model
  that writes the commit (this controller's is the one below):

```bash
git commit -m "feat(odds): plan types, injected inputs and the product, state and data checks" -m "Odds plan Task 5 (Q4, Q24, Q25, Q39): core/odds/plan.py with the refusal codes and checks, the fixture venues, series, plans and contexts, and tests/odds_plan.py." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

  Afterwards `git status --short` prints only `?? docs/superpowers/plans/2026-10-24-odds-engine-execution-ledger.md`.
