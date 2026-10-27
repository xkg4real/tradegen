### Task 11: The poll checks (`execution/checks.py`)

**Files:**
- Create: `execution/checks.py` (LF, UTF-8, no BOM)
- Create: `tests/execution_checks.py` (LF, UTF-8, no BOM)
- Test: `tests/execution_checks.py`

No existing file is edited, so the DRIFT RULE (Global Constraints 0.6) has no anchor here. `MODULES` of
`tests/execution_acceptance.py` already lists `execution_checks` (Task 1, contract 3.1); the aggregator skipped it while
the file did not exist. If `execution/checks.py` or `tests/execution_checks.py` already exists, stop and rule.

**Interfaces:**
- Consumes:
  - Task 4 (`execution.snapshot`): `VENUES = ("kis", "upbit", "okx")`; the frozen kw-only records
    `Snapshot(venue, utc, ok, server_utc=None, clock_offset_s=None, error=None, holdings={}, cash={},
    deposit_krw=None, open_orders=(), fills=(), deposits=(), withdrawals=(), withdrawal_addresses=(),
    key_expiry=None, loans={}, earn={}, flags=frozenset(), prices_krw={}, response_sha256={})` (its
    `snapshot_sha256` is set by `__post_init__`), `Holding(units, locked=0.0, avg_cost=None)`,
    `Order(id, symbol, side, units, price=None)`, `Move(id, symbol, counter="", side, units)`,
    `Address(currency, net_type, address, secondary_address="")`;
    `failed(venue, utc, error, *, flags=frozenset(), server_utc=None, clock_offset_s=None) -> Snapshot`;
    `dump(snap) -> bytes`; `load(obj) -> Snapshot` (`ValueError` unless `snapshot_sha256` recomputes, and
    `load(json.loads(dump(s))) == s`, both Task 4 tests).
  - Task 8 (`execution.positions`): `live_positions(snapshots, now) -> model.Positions | None` (None unless every
    venue of `VENUES` is present, ok, stamped 0 to 15 minutes before `now`, fully priced and worth >= 0;
    `equity_krw` is the sum of the venue values and `exposure[venue].held_krw` each venue's value; KRW cash is priced
    at 1.0, every other currency and symbol at `prices_krw`).
  - `core.compliance.model` (repo, unchanged by this task): `OwnerState` (`.ok`, `.caps`, `.limits`, `.addresses` as
    `{(venue, symbol, network, address, tag or "")}`, `OwnerState.broken(reason)`), `Positions` (`.equity_krw`,
    `.exposure`), `Exposure.held_krw`, `KST`, `iso_utc`, `canonical_json`, `sha256_hex`. The owner keys come from
    `core/compliance/owner.py` (`_DATA` `cap_set`/`limit_set`, and `_owner_fold`): `caps["okx_equity_share"]`,
    `limits["total_loss_floor_krw"]`, `limits["daily_loss_krw"]`.
  - Task 1 (`tests.execution_fixtures`): `NOW` (2026-10-24 00:00:00 UTC, 09:00 KST). Nothing else from the fixtures:
    the tests build their snapshots with `snapshot.Snapshot` and `snapshot.failed` directly, so no test
    leans on the defaults of Task 4's `snap()`.
- Produces (`execution/checks.py`, exactly contract section 15; pure: no clock, no file, no network):
  - constants `KINDS` (13), `VENUE_NAMES`, `KEY_EXPIRY_WARN = timedelta(days=30)`, `OUTAGE_POLLS = 3`,
    `CLOCK_SKEW_S = 60`, `STAMP`, `INT_SLOTS`, `TIME_SLOTS`, `ITEM_SLOTS`, `NOT_SET_ITEMS` (11 strings), `TEXT`
    (24 text_keys, the contract 15.3 catalogue verbatim, checked against the contract's text offline);
  - `@dataclass(frozen=True, kw_only=True)` records `Alert(venue, kind, level, text_key, slots={})`,
    `Prior(last_ok, fails)`, `Limits(total_loss_floor_krw, daily_loss_krw, okx_equity_share, day_start_equity_krw,
    day_start_utc)`;
  - `limits_from(owner, day_start) -> Limits`; `priors(rows) -> dict[str, Prior]`;
    `day_start(rows, now) -> tuple[float, str] | None`;
    `run_checks(prev, new, owner, limits, now) -> list[Alert]`;
    `evaluated(prev, new, owner, limits, now) -> frozenset[tuple[str, str]]`;
    `not_set(new, owner, limits, live) -> tuple[str, ...]`;
    `due(raw, done, rows, now) -> tuple[list[Alert], list[Alert]]` (fresh, clears);
    `render(alert) -> str`; `row(alert, utc) -> dict`; `verify_row(obj) -> bool`;
  - private helpers (this module only): `_FIELDS`, `_ROW_KEYS`, `_OKX_SELF_CHECK`, `_NOT_AN_OUTAGE`, `_OK_KINDS`,
    `_NO_PRIOR`, `_slot_ok`, `_venue_alerts`, `_holdings`, `_alert`, `_load`, `_units`, `_differs`, `_new_moves`,
    `_address_set`, `_has_start`, `_is_stamp`, `_instant`, `_seoul`.
  - What Task 12 relies on: `Alert` is kw-only, so every alert the poller builds itself (EVIDENCE_BROKEN,
    OUTAGE_CRASH, CRASH_UNLOGGED, the NOT_SET info alert) names its fields
    (`checks.Alert(venue="kis", kind="EVIDENCE", level="amber", text_key="EVIDENCE_BROKEN")`); contract 16.2 writes
    them positionally as shorthand, and a positional call raises `TypeError`. `render` is for red, amber and info
    alerts only (a clear has no slots). `--pending` renders a read-back row only after `verify_row(row)` is True,
    as `checks.render(checks.Alert(venue=row["venue"], kind=row["kind"], level=row["level"],
    text_key=row["text_key"], slots=row["slots"]))`. `due` reads all of `alerts.jsonl` and returns `fresh` already
    sorted (amber and info before red), so the poller writes `fresh + clears` in that order.

**Plan decisions used:** E7 (pure checks, catalogue, leak scan), E19 (dedupe per `(venue, text_key)` per Seoul date,
a level rise fires at once, only evaluated checks clear), E20 (ADDRESS_LIST compares `(currency, address,
secondary)`), E21 (key expiry is the earliest `expire_at`), E31 (missing keys: amber KEY_MISSING, no OUTAGE, listed
as not set), E34 (the daily-loss baseline), E37 (no balance or address in any text), E39 (CLOCK_SKEW reads
`clock_offset_s`), E42 (unsigned KIS: amber KIS_UNSIGNED, no OUTAGE), E43 (the NOT_SET info row); rulings E1R2-2,
E1R2-8, E1R2-9, E1R2-12.

Design notes (read before Step 3; each is a choice inside contract 15, none changes a name or a sentence):
- **The table's parenthesised venue scopes a row.** KIS_UNSIGNED is raised only for `kis`; KEY_OKX_SELF_CHECK,
  D15_BORROW, D15_EARN, HARD_BLOCK_EVENTS and HARD_BLOCK_DERIVATIVE only for `okx`; KEY_EXPIRY, ADDRESS_CHANGED and
  ADDRESS_UNSIGNED only for `upbit`. Their sentences name that venue, so raising them elsewhere would say something
  false. Rows without a parenthesised venue (KEY_MISSING, KEY_AUTH, FOREIGN_ORDER, HOLDINGS_*, D15_LOAN, OUTAGE,
  CLOCK_SKEW) run on every venue.
- **Which rows need an ok snapshot.** As the table says: KEY_EXPIRY, FOREIGN_ORDER, HOLDINGS_*, ADDRESS_*, D15_LOAN and
  D15_EARN need `ok`; KEY_MISSING, KIS_UNSIGNED, KEY_AUTH, KEY_OKX_SELF_CHECK, D15_BORROW and HARD_BLOCK_* read the
  flags (a failed OKX self-check is an `ok: false` snapshot that carries its flags); OUTAGE needs `not ok`; CLOCK_SKEW
  needs only `clock_offset_s` (a failed snapshot may carry one) and is then also evaluated.
- **`due` counts only rows that verify.** Contract 15.2 skips a row that is not a dict or whose text_key is not in
  TEXT; this task skips every row for which `verify_row` is False (a superset), so a malformed or forged line in
  `alerts.jsonl` can neither mute nor clear an alert, and `due` never raises on a bad row (a raise would crash every
  poll into OUTAGE_CRASH). Every row `row()` writes verifies (tested), so nothing the poller writes is lost.
- **A stamp must name a real instant.** `_is_stamp` is `STAMP.fullmatch` plus `datetime.fromisoformat` (which reads
  the `Z` as UTC on Python 3.11+): `"2026-13-40T00:00:00Z"` matches STAMP but is refused, for `utc` and every
  `TIME_SLOTS` value in `verify_row`, for `key_expiry` and for inquiry rows. So `--pending`'s KST conversion (Task 12)
  never meets a month 13.
- **A broken owner log hides every limit.** `limits_from` gives None for the floor, the daily loss and the cap while
  `owner.ok` is False (spec 6.4: then every owner fact counts as absent); those checks are then "not set".
- **Rows that do not load are skipped.** `priors` and `day_start` read inquiry rows through `_load`: a row that
  `snapshot.load` refuses (its hash does not recompute, or it is not a snapshot) or whose `utc` is not a real stamp
  counts for nothing, as `snapshot.read_all` already skips a line that is not a JSON object.
- **No attribute in an assignment target.** The rebinding guard of Global Constraints 0.5 bans an assignment whose
  target is an attribute; `priors` binds a local `venue` instead of writing `last_ok[snap.venue]`, and `day_start`
  fills its dict with `dict.update`, so not even a subscript target holds an attribute.
- **`verify_row` takes any int in an int slot.** The contract types the slots and no more; a process that can write
  `~/.tradegen` could put digits there, as it could forge any row. Recorded, not changed.

- [ ] **Step 1: Write the failing test**

  First check that the names this task consumes exist as the Interfaces block says (an earlier task that renamed one
  is a drift ruling, C0.6). Overlap check with the PowerShell tool (must print nothing; otherwise wait and re-run):

```powershell
Get-CimInstance Win32_Process -Filter "Name LIKE 'python%'" | Where-Object { $_.CommandLine -match 'run_all' } | Select-Object ProcessId,Name,CommandLine
```

  Then from the repo root in Git Bash:

```bash
.venv/Scripts/python.exe -c "from execution import positions, snapshot; import dataclasses; print(snapshot.VENUES, sorted(f.name for f in dataclasses.fields(snapshot.Snapshot)), snapshot.failed, snapshot.dump, snapshot.load, positions.live_positions, sep='\n')"
```

  Expected: `('kis', 'upbit', 'okx')`, then the 21 field names `['cash', 'clock_offset_s', 'deposit_krw', 'deposits',
  'earn', 'error', 'fills', 'flags', 'holdings', 'key_expiry', 'loans', 'ok', 'open_orders', 'prices_krw',
  'response_sha256', 'server_utc', 'snapshot_sha256', 'utc', 'venue', 'withdrawal_addresses', 'withdrawals']`, then
  four function reprs.

  Create `tests/execution_checks.py` (whole file, LF):

```python
"""The poll checks (E1 plan Task 11; spec 7; contract 15): every row of the check table on its trigger and just
inside it, missing keys and unsigned code, not-set items, the once-a-day rule, alert rows and their re-check, and
the leak scan over every sentence.

Snapshots are built here with every collection empty unless a test gives it, so no test leans on another task's
fixture defaults. `_poll` runs one poll through the pure pipeline the poller uses (contract 16.2 steps 2, 6 and 7) on
in-memory rows; `_due_run` runs `due` alone over synthetic alerts. No later task appends to this module.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone

from core.compliance import model
from execution import checks, positions, snapshot
from tests import execution_fixtures as EF

NOW = EF.NOW                                          # 2026-10-24 09:00 KST
UTC = model.iso_utc(NOW)
ADDRESS = "bc1qfixtureaddress000000000000000000000"    # contract 3.2's Upbit fixture address
SELF_CHECK = frozenset({"okx_perm", "okx_acct_lv", "okx_spot_borrow", "okx_auto_loan", "okx_no_ip"})
KEYS_MISSING = frozenset({"keys_missing"})
UNSIGNED = frozenset({"code_unsigned"})
BROKEN = model.OwnerState.broken("test: the owner log does not verify")
SAMPLE = {"n": 2, "k": 1, "added": 1, "removed": 0, "days": 29, "seconds": 61, "fills": 1, "deposits": 0,
          "withdrawals": 0, "expires": "2026-11-22T00:00:00Z", "when": UTC, "since": "2026-10-23T15:00:00Z",
          "skipped": "FLOOR: not set; OKX: keys not in .env"}
CURRENCY = "\u20a9|\\$|krw|usd|usdt|usdc|btc|\uc6d0"                 # the won sign and the Korean "won" syllable
LEAK = re.compile(f"(?i)({CURRENCY})\\s*[0-9]|[0-9][0-9,.]*\\s*({CURRENCY})")
LONG_RUN = re.compile(r"[A-Za-z0-9]{25,}")


def _snap(venue: str, **fields) -> snapshot.Snapshot:
    """An ok snapshot of `venue` stamped NOW (or `utc=`), every collection empty unless given."""
    return snapshot.Snapshot(**{"venue": venue, "utc": UTC, "ok": True, **fields})


def _failed(venue: str, flags=frozenset(), utc: str = UTC, **extra) -> snapshot.Snapshot:
    return snapshot.failed(venue, utc, f"{venue}: test failure", flags=flags, **extra)


def _new(now: datetime = NOW, **venues) -> dict:
    """Three ok snapshots at `now` worth KRW 30,000 (KIS cash), 20,000 (Upbit cash) and 10,000 (OKX, 10 USDT at
    1,000): equity 60,000, OKX held 10,000. Any venue can be replaced."""
    stamp = model.iso_utc(now)
    base = {"kis": _snap("kis", utc=stamp, cash={"KRW": 30_000.0}),
            "upbit": _snap("upbit", utc=stamp, cash={"KRW": 20_000.0}),
            "okx": _snap("okx", utc=stamp, holdings={"USDT": snapshot.Holding(units=10.0)},
                         prices_krw={"USDT": 1_000.0})}
    base.update(venues)
    return base


def _owner(**changes) -> model.OwnerState:
    """An OK owner state: cap 0.5, floor 21,000, daily loss 5,000 and one signed withdrawal address."""
    fields = {"status": "OK", "head": (5, "a" * 64), "caps": {"okx_equity_share": 0.5},
              "limits": {"total_loss_floor_krw": 21_000.0, "daily_loss_krw": 5_000.0},
              "addresses": frozenset({("okx", "BTC", "bitcoin", ADDRESS, "")})}
    fields.update(changes)
    return model.OwnerState(**fields)


def _prev(**last) -> dict:
    """No prior for any venue, except the given `venue=Prior(...)`."""
    out = {v: checks.Prior(last_ok=None, fails=0) for v in snapshot.VENUES}
    out.update(last)
    return out


def _run(new: dict, prev: dict | None = None, owner: model.OwnerState | None = None, start=None,
         now: datetime = NOW) -> dict:
    """run_checks for one poll as {(venue, text_key): slots}; kind and level always match the catalogue."""
    owner = _owner() if owner is None else owner
    alerts = checks.run_checks(_prev() if prev is None else prev, new, owner, checks.limits_from(owner, start), now)
    for a in alerts:
        assert (a.kind, a.level) == checks.TEXT[a.text_key][:2], a
    found = {(a.venue, a.text_key): dict(a.slots) for a in alerts}
    assert len(found) == len(alerts), alerts
    return found


def _alert(venue: str, text_key: str) -> checks.Alert:
    """A catalogue alert with sample slots, so its row verifies."""
    kind, level, template = checks.TEXT[text_key]
    names = set(re.findall(r"\{(\w+)\}", template)) - {"venue"}
    return checks.Alert(venue=venue, kind=kind, level=level, text_key=text_key, slots={n: SAMPLE[n] for n in names})


def _stored(alerts, now: datetime) -> list[dict]:
    """The rows as alerts.jsonl holds them: canonical JSON read back."""
    return [json.loads(model.canonical_json(checks.row(a, model.iso_utc(now)))) for a in alerts]


def _poll(state: dict, new: dict, now: datetime, owner: model.OwnerState | None = None, start=None) -> dict:
    """One poll on in-memory rows, as poll_once runs the pure part (contract 16.2 steps 2, 6, 7): priors from the
    inquiry rows before this poll, the checks, the not-set info alert (E43), due, then this poll's rows appended."""
    owner = _owner() if owner is None else owner
    prev = checks.priors(state["inquiry"])
    limits = checks.limits_from(owner, start)
    raw = checks.run_checks(prev, new, owner, limits, now)
    done = checks.evaluated(prev, new, owner, limits, now)
    skipped = checks.not_set(new, owner, limits, positions.live_positions(new, now))
    if skipped:
        raw = raw + [checks.Alert(venue="all", kind="NOT_SET", level="info", text_key="NOT_SET",
                                  slots={"skipped": "; ".join(skipped)})]
    fresh, clears = checks.due(raw, done, state["alerts"], now)
    state["inquiry"] += [json.loads(snapshot.dump(new[v])) for v in snapshot.VENUES]
    state["alerts"] += _stored(fresh + clears, now)
    return {"raw": [(a.venue, a.text_key) for a in raw], "fresh": [(a.venue, a.text_key) for a in fresh],
            "clears": [(a.venue, a.text_key) for a in clears], "skipped": skipped, "prev": prev}


def _forged(obj: dict, **changes) -> dict:
    """An inquiry row with `changes` and its snapshot_sha256 recomputed, as a writer forging a line would do."""
    out = dict(obj, **changes)
    out["snapshot_sha256"] = model.sha256_hex(model.canonical_json(
        {k: v for k, v in out.items() if k != "snapshot_sha256"}))
    return out


def _due_run(polls, start: datetime = NOW) -> list[tuple[list[str], list[str]]]:
    """due over a list of (raw alerts, done pairs), one poll every 5 minutes from `start`, rows accumulating."""
    rows, out = [], []
    for i, (raw, done) in enumerate(polls):
        now = start + timedelta(minutes=5 * i)
        fresh, clears = checks.due(raw, frozenset(done), rows, now)
        rows += _stored(fresh + clears, now)
        out.append(([a.text_key for a in fresh], [a.text_key for a in clears]))
    return out


# --------------------------------------------------------------------------- #
# The catalogue
# --------------------------------------------------------------------------- #
def test_catalogue_kinds_levels_and_slots_are_consistent():
    assert len(checks.KINDS) == 13 and len(set(checks.KINDS)) == 13
    assert len(checks.TEXT) == 24
    slot_names = checks.INT_SLOTS | checks.TIME_SLOTS | checks.ITEM_SLOTS
    for key, (kind, level, template) in checks.TEXT.items():
        assert kind in checks.KINDS, key
        assert level in ("red", "amber", "info"), key
        assert (level == "info") == (key == "NOT_SET"), key
        names = set(re.findall(r"\{(\w+)\}", template)) - {"venue"}
        assert names <= slot_names, (key, names)
    assert dict(checks.VENUE_NAMES) == {"kis": "KIS", "upbit": "Upbit", "okx": "OKX", "all": "TRADEGEN"}
    assert len(checks.NOT_SET_ITEMS) == 11, sorted(checks.NOT_SET_ITEMS)
    assert not any("; " in item for item in checks.NOT_SET_ITEMS)       # the join stays splittable


def test_a_quiet_poll_raises_nothing_and_skips_nothing():
    owner = _owner()
    assert _run(_new()) == {}
    assert checks.not_set(_new(), owner, checks.limits_from(owner, None), positions.live_positions(_new(), NOW)) == ()


def test_limits_from_reads_the_owner_state_and_the_day_start():
    start = (65_000.0, "2026-10-23T15:00:00Z")
    assert checks.limits_from(_owner(), start) == checks.Limits(
        total_loss_floor_krw=21_000.0, daily_loss_krw=5_000.0, okx_equity_share=0.5,
        day_start_equity_krw=65_000.0, day_start_utc="2026-10-23T15:00:00Z")
    assert checks.limits_from(_owner(caps={}, limits={}), None) == checks.Limits(
        total_loss_floor_krw=None, daily_loss_krw=None, okx_equity_share=None, day_start_equity_krw=None,
        day_start_utc=None)
    not_ok = model.OwnerState(status="BROKEN", caps={"okx_equity_share": 0.5}, limits={"daily_loss_krw": 1.0})
    limits = checks.limits_from(not_ok, start)                  # a broken log: every owner fact counts as absent
    assert (limits.total_loss_floor_krw, limits.daily_loss_krw, limits.okx_equity_share) == (None, None, None)
    assert limits.day_start_equity_krw == 65_000.0


# --------------------------------------------------------------------------- #
# The check table, row by row (contract 15.1)
# --------------------------------------------------------------------------- #
def test_key_missing_unsigned_and_auth_errors():
    assert _run(_new(upbit=_failed("upbit", KEYS_MISSING))) == {("upbit", "KEY_MISSING"): {}}
    assert _run(_new(okx=_failed("okx", KEYS_MISSING))) == {("okx", "KEY_MISSING"): {}}
    assert _run(_new(kis=_failed("kis", KEYS_MISSING))) == {("kis", "KEY_MISSING"): {}}
    assert _run(_new(kis=_failed("kis", UNSIGNED))) == {("kis", "KIS_UNSIGNED"): {}}
    assert _run(_new(upbit=_failed("upbit", frozenset({"auth_error"})))) == {("upbit", "KEY_AUTH"): {}}
    assert _run(_new(kis=_failed("kis", frozenset({"auth_error"})))) == {("kis", "KEY_AUTH"): {}}
    assert _run(_new(upbit=_failed("upbit"))) == {}                           # 1 failed poll: nothing yet


def test_okx_self_check_counts_its_failed_checks():
    assert _run(_new(okx=_failed("okx", frozenset({"okx_perm"})))) == {("okx", "KEY_OKX_SELF_CHECK"): {"n": 1}}
    assert _run(_new(okx=_failed("okx", frozenset({"okx_acct_lv", "okx_no_ip"})))) == {
        ("okx", "KEY_OKX_SELF_CHECK"): {"n": 2}}
    assert _run(_new(okx=_failed("okx", SELF_CHECK))) == {("okx", "KEY_OKX_SELF_CHECK"): {"n": 5},
                                                          ("okx", "D15_BORROW"): {}}
    assert _run(_new(okx=_failed("okx", frozenset({"okx_auto_loan"})))) == {
        ("okx", "KEY_OKX_SELF_CHECK"): {"n": 1}, ("okx", "D15_BORROW"): {}}


def test_upbit_key_expiry_warns_from_30_days():
    def expiry(left: timedelta) -> dict:
        return _run(_new(upbit=_snap("upbit", cash={"KRW": 20_000.0}, key_expiry=model.iso_utc(NOW + left))))
    at_30 = model.iso_utc(NOW + timedelta(days=30))
    assert expiry(timedelta(days=30)) == {("upbit", "KEY_EXPIRY"): {"days": 30, "expires": at_30}}
    assert expiry(timedelta(days=30, seconds=1)) == {}
    assert expiry(timedelta(days=29, hours=23))[("upbit", "KEY_EXPIRY")]["days"] == 29
    assert expiry(-timedelta(hours=1))[("upbit", "KEY_EXPIRY")]["days"] == 0          # already expired
    assert _run(_new(upbit=_snap("upbit", cash={"KRW": 20_000.0}))) == {}               # no key listed


def test_foreign_order_on_an_ok_venue():
    order = snapshot.Order(id="u-open-1", symbol="BTC", side="buy", units=0.0001, price=90_000_000.0)
    other = snapshot.Order(id="u-open-2", symbol="BTC", side="sell", units=0.0001)
    upbit = _snap("upbit", cash={"KRW": 20_000.0}, open_orders=(order,))
    assert _run(_new(upbit=upbit)) == {("upbit", "FOREIGN_ORDER"): {"n": 1}}
    kis = _snap("kis", cash={"KRW": 30_000.0}, open_orders=(order, other))
    assert _run(_new(kis=kis)) == {("kis", "FOREIGN_ORDER"): {"n": 2}}
    assert _run(_new(upbit=_failed("upbit"))) == {}                          # a failed venue lists no orders


def test_holdings_change_explained_by_a_new_fill_and_its_counter():
    last = _snap("okx", holdings={"USDT": snapshot.Holding(units=10.0)}, prices_krw={"USDT": 1_000.0},
                 fills=(snapshot.Move(id="f0", symbol="BTC", counter="USDT", side="buy", units=0.0001),))
    fill = snapshot.Move(id="f1", symbol="BTC", counter="USDT", side="buy", units=0.0001)
    now = _snap("okx", holdings={"USDT": snapshot.Holding(units=3.0), "BTC": snapshot.Holding(units=0.0001)},
                prices_krw={"USDT": 1_000.0, "BTC": 100_000_000.0}, fills=(last.fills[0], fill))
    found = _run(_new(okx=now), _prev(okx=checks.Prior(last_ok=last, fails=0)))
    assert found == {("okx", "HOLDINGS_EXPLAINED"): {"n": 2, "fills": 1, "deposits": 0, "withdrawals": 0}}, found
    # Only the counter changed: the new fill names USDT as its counter, so it explains USDT and counts.
    usdt_only = _snap("okx", holdings={"USDT": snapshot.Holding(units=3.0)}, prices_krw={"USDT": 1_000.0},
                      fills=(last.fills[0], fill))
    found = _run(_new(okx=usdt_only), _prev(okx=checks.Prior(last_ok=last, fails=0)))
    assert found == {("okx", "HOLDINGS_EXPLAINED"): {"n": 1, "fills": 1, "deposits": 0, "withdrawals": 0}}, found
    old_only = _snap("okx", holdings=now.holdings, prices_krw=now.prices_krw, fills=last.fills)   # no new fill
    found = _run(_new(okx=old_only), _prev(okx=checks.Prior(last_ok=last, fails=0)))
    assert found == {("okx", "HOLDINGS_UNEXPLAINED"): {"n": 2, "k": 2, "fills": 0, "deposits": 0,
                                                       "withdrawals": 0}}, found


def test_holdings_change_mixed_case_counts_fills_deposits_and_withdrawals():
    held = {"BTC": 0.0001, "ETH": 0.01, "XRP": 5.0, "SOL": 1.0}
    last = _snap("upbit", cash={"KRW": 20_000.0},
                 holdings={s: snapshot.Holding(units=u) for s, u in held.items()},
                 prices_krw={s: 1.0 for s in held})
    moved = {"BTC": 0.0002, "ETH": 0.02, "XRP": 4.0, "SOL": 2.0, "DOGE": 7.0}   # DOGE new: absent counts as 0
    now = _snap("upbit", cash={"KRW": 21_000.0},
                holdings={s: snapshot.Holding(units=u) for s, u in moved.items()},
                prices_krw={s: 1.0 for s in moved},
                fills=(snapshot.Move(id="u-done-1", symbol="BTC", counter="KRW", side="buy", units=0.0001),),
                deposits=(snapshot.Move(id="u-dep-1", symbol="ETH", side="in", units=0.01),
                          snapshot.Move(id="u-dep-2", symbol="KRW", side="in", units=1_000.0)),
                withdrawals=(snapshot.Move(id="u-wd-1", symbol="XRP", side="out", units=1.0),))
    found = _run(_new(upbit=now), _prev(upbit=checks.Prior(last_ok=last, fails=0)))
    # 5 changed: BTC (fill), ETH (deposit), XRP (withdrawal) explained; SOL and DOGE not. The KRW deposit names no
    # changed holding (KRW is cash), so it is not counted.
    assert found == {("upbit", "HOLDINGS_UNEXPLAINED"): {"n": 5, "k": 2, "fills": 1, "deposits": 1,
                                                         "withdrawals": 1}}, found
    assert _run(_new(upbit=now)) == {}                                      # no previous ok snapshot: no compare


def test_holdings_change_ignores_float_noise():
    last = _snap("upbit", holdings={"BTC": snapshot.Holding(units=1.0)}, prices_krw={"BTC": 1.0})
    noise = _snap("upbit", holdings={"BTC": snapshot.Holding(units=1.0 + 1e-13)}, prices_krw={"BTC": 1.0})
    real = _snap("upbit", holdings={"BTC": snapshot.Holding(units=1.0 + 1e-11)}, prices_krw={"BTC": 1.0})
    prev = _prev(upbit=checks.Prior(last_ok=last, fails=0))
    assert _run(_new(upbit=noise), prev) == {}
    assert ("upbit", "HOLDINGS_UNEXPLAINED") in _run(_new(upbit=real), prev)


def test_address_list_changed_and_unsigned():
    signed = snapshot.Address(currency="BTC", net_type="BTC", address=ADDRESS)
    extra = snapshot.Address(currency="ETH", net_type="ETH", address="0xfixture")
    last = _snap("upbit", cash={"KRW": 20_000.0}, withdrawal_addresses=(signed,))
    prev = _prev(upbit=checks.Prior(last_ok=last, fails=0))
    assert _run(_new(upbit=last), prev) == {}                               # signed and unchanged
    renamed = _snap("upbit", cash={"KRW": 20_000.0},                         # net_type alone is not compared (E20)
                    withdrawal_addresses=(snapshot.Address(currency="BTC", net_type="bitcoin", address=ADDRESS),))
    assert _run(_new(upbit=renamed), prev) == {}
    both = _snap("upbit", cash={"KRW": 20_000.0}, withdrawal_addresses=(signed, extra))
    assert _run(_new(upbit=both), prev) == {("upbit", "ADDRESS_CHANGED"): {"added": 1, "removed": 0},
                                            ("upbit", "ADDRESS_UNSIGNED"): {"n": 1}}
    tagged = _snap("upbit", cash={"KRW": 20_000.0}, withdrawal_addresses=(
        snapshot.Address(currency="BTC", net_type="BTC", address=ADDRESS, secondary_address="7"),))
    assert _run(_new(upbit=tagged), prev) == {("upbit", "ADDRESS_CHANGED"): {"added": 1, "removed": 1},
                                              ("upbit", "ADDRESS_UNSIGNED"): {"n": 1}}
    gone = _snap("upbit", cash={"KRW": 20_000.0})
    assert _run(_new(upbit=gone), prev) == {("upbit", "ADDRESS_CHANGED"): {"added": 0, "removed": 1}}
    # The unsigned half is skipped while the owner log is not OK; the changed half still runs.
    assert _run(_new(upbit=both), prev, owner=BROKEN) == {("upbit", "ADDRESS_CHANGED"): {"added": 1, "removed": 0}}
    assert "ADDRESS_LIST: owner log not OK" in checks.not_set(
        _new(upbit=both), BROKEN, checks.limits_from(BROKEN, None), positions.live_positions(_new(upbit=both), NOW))
    # No previous ok snapshot: only the unsigned half can run.
    assert _run(_new(upbit=both)) == {("upbit", "ADDRESS_UNSIGNED"): {"n": 1}}


def test_d15_borrow_loans_and_earn():
    assert _run(_new(okx=_failed("okx", frozenset({"okx_spot_borrow"})))) == {
        ("okx", "KEY_OKX_SELF_CHECK"): {"n": 1}, ("okx", "D15_BORROW"): {}}
    kis = _snap("kis", cash={"KRW": 30_000.0},
                loans={"tot_loan_amt": 0.0, "loan_amt": 1.0, "crdt_fncg_amt": 2.0, "rcvb_amt": 0.0})
    assert _run(_new(kis=kis)) == {("kis", "D15_LOAN"): {"n": 2}}
    okx = _snap("okx", holdings={"USDT": snapshot.Holding(units=10.0)}, prices_krw={"USDT": 1_000.0},
                loans={"liab:USDT": 0.5}, earn={"savings:USDT": 5.0, "asset_valuation": 0.0, "auto_lend:USDT": 1.0})
    assert _run(_new(okx=okx)) == {("okx", "D15_LOAN"): {"n": 1}, ("okx", "D15_EARN"): {"n": 2}}
    zero = _snap("okx", holdings={"USDT": snapshot.Holding(units=10.0)}, prices_krw={"USDT": 1_000.0},
                 loans={"liab:USDT": 0.0}, earn={"asset_valuation": 0.0})
    assert _run(_new(okx=zero)) == {}


def test_hard_block_events_and_derivatives():
    def okx(flags) -> snapshot.Snapshot:
        return _snap("okx", holdings={"USDT": snapshot.Holding(units=10.0)}, prices_krw={"USDT": 1_000.0},
                     flags=frozenset(flags))
    assert _run(_new(okx=okx({"EVENTS"}))) == {("okx", "HARD_BLOCK_EVENTS"): {}}
    assert _run(_new(okx=okx({"derivative_position"}))) == {("okx", "HARD_BLOCK_DERIVATIVE"): {}}
    assert _run(_new(okx=okx({"EVENTS", "derivative_position"}))) == {("okx", "HARD_BLOCK_EVENTS"): {},
                                                                       ("okx", "HARD_BLOCK_DERIVATIVE"): {}}


def test_floor_at_the_floor_and_1_krw_above():
    assert _run(_new(), owner=_owner(limits={"total_loss_floor_krw": 60_000.0})) == {("all", "FLOOR"): {}}
    assert _run(_new(), owner=_owner(limits={"total_loss_floor_krw": 59_999.0})) == {}   # equity = floor + 1


def test_daily_loss_at_the_limit_and_1_krw_less():
    since = "2026-10-23T15:00:00Z"                                          # 00:00 KST, today's first poll
    assert _run(_new(), start=(65_000.0, since)) == {("all", "DAILY_LOSS"): {"since": since}}
    assert _run(_new(), start=(64_999.0, since)) == {}                      # a loss of 4,999
    assert _run(_new(), start=None) == {}                                   # no day start: nothing to compare


def test_okx_cap_at_the_cap_and_1_krw_above():
    owner = _owner(caps={"okx_equity_share": 0.25})
    def venues(kis_krw: float, okx_usdt: float) -> dict:                    # equity stays 40,000
        return _new(kis=_snap("kis", cash={"KRW": kis_krw}),
                    okx=_snap("okx", holdings={"USDT": snapshot.Holding(units=okx_usdt)}, prices_krw={"USDT": 1.0}))
    assert positions.live_positions(venues(10_000.0, 10_000.0), NOW).equity_krw == 40_000.0
    assert _run(venues(10_000.0, 10_000.0), owner=owner) == {}              # at the cap: 10,000 of 40,000
    assert _run(venues(9_999.0, 10_001.0), owner=owner) == {("okx", "OKX_CAP"): {}}


def test_outage_on_the_third_failed_poll():
    assert _run(_new(upbit=_failed("upbit")), _prev(upbit=checks.Prior(last_ok=None, fails=1))) == {}
    assert _run(_new(upbit=_failed("upbit")), _prev(upbit=checks.Prior(last_ok=None, fails=2))) == {
        ("upbit", "OUTAGE"): {"n": 3, "when": UTC}}
    assert _run(_new(kis=_failed("kis")), _prev(kis=checks.Prior(last_ok=None, fails=7))) == {
        ("kis", "OUTAGE"): {"n": 8, "when": UTC}}
    # Not an outage: KEY_MISSING and KIS_UNSIGNED already say why (E31, E42).
    assert _run(_new(upbit=_failed("upbit", KEYS_MISSING)), _prev(upbit=checks.Prior(last_ok=None, fails=9))) == {
        ("upbit", "KEY_MISSING"): {}}
    assert _run(_new(kis=_failed("kis", UNSIGNED)), _prev(kis=checks.Prior(last_ok=None, fails=9))) == {
        ("kis", "KIS_UNSIGNED"): {}}


def test_clock_skew_reads_the_offset_at_receipt():
    def kis(**fields) -> snapshot.Snapshot:
        return _snap("kis", cash={"KRW": 30_000.0}, **fields)
    assert _run(_new(kis=kis(clock_offset_s=60.0))) == {}
    assert _run(_new(kis=kis(clock_offset_s=61.0))) == {("kis", "CLOCK_SKEW"): {"seconds": 61}}
    assert _run(_new(kis=kis(clock_offset_s=-61.4))) == {("kis", "CLOCK_SKEW"): {"seconds": 61}}
    # A correct clock: KIS answered 90 s after the poll started (read last, E39), with its clock 0.5 s ahead.
    late = kis(server_utc=model.iso_utc(NOW + timedelta(seconds=90)), clock_offset_s=0.5)
    assert _run(_new(kis=late)) == {}
    # A failed snapshot that carries an offset is still checked.
    assert _run(_new(okx=_failed("okx", clock_offset_s=-120.0))) == {("okx", "CLOCK_SKEW"): {"seconds": 120}}


# --------------------------------------------------------------------------- #
# Missing keys and unsigned code (E31, E42; E1R2-8, E1R2-9)
# --------------------------------------------------------------------------- #
def test_missing_keys_alert_once_a_day_never_as_an_outage_and_clear_when_ok():
    state = {"inquiry": [], "alerts": []}
    for i in range(5):
        now = NOW + timedelta(minutes=5 * i)
        out = _poll(state, _new(now, upbit=_failed("upbit", KEYS_MISSING, utc=model.iso_utc(now))), now)
        assert [k for k in out["raw"] if k[0] == "upbit"] == [("upbit", "KEY_MISSING")], (i, out["raw"])
        assert out["prev"]["upbit"].fails == 0, i                         # the streak never starts
        assert "Upbit: keys not in .env" in out["skipped"], out["skipped"]
        want = [("upbit", "KEY_MISSING"), ("all", "NOT_SET")] if i == 0 else []
        assert out["fresh"] == want and out["clears"] == [], (i, out)
    now = NOW + timedelta(minutes=25)
    out = _poll(state, _new(now), now)                                      # the keys are back
    assert out["fresh"] == [] and out["clears"] == [("upbit", "KEY_MISSING")], out
    assert out["skipped"] == ()


def test_unsigned_kis_alerts_once_a_day_and_nothing_else():
    state = {"inquiry": [], "alerts": []}
    for i in range(4):
        now = NOW + timedelta(minutes=5 * i)
        out = _poll(state, _new(now, kis=_failed("kis", UNSIGNED, utc=model.iso_utc(now))), now)
        assert [k for k in out["raw"] if k[0] == "kis"] == [("kis", "KIS_UNSIGNED")], (i, out["raw"])
        assert "KIS: code not signed" in out["skipped"]
        assert out["fresh"] == ([("kis", "KIS_UNSIGNED"), ("all", "NOT_SET")] if i == 0 else []), (i, out)
    now = NOW + timedelta(minutes=20)
    out = _poll(state, _new(now), now)                                      # the code is signed
    assert out["clears"] == [("kis", "KIS_UNSIGNED")] and out["fresh"] == [], out


def test_priors_end_a_fail_streak_at_missing_keys_or_unsigned_code():
    def rows(*snaps) -> list[dict]:
        return [json.loads(snapshot.dump(s)) for s in snaps]
    real = _failed("upbit")
    assert checks.priors(rows(real, real, _failed("upbit", KEYS_MISSING)))["upbit"].fails == 0
    assert checks.priors(rows(_failed("upbit", KEYS_MISSING), real, real))["upbit"].fails == 2
    assert checks.priors(rows(_failed("kis"), _failed("kis", UNSIGNED)))["kis"].fails == 0
    assert checks.priors(rows(real, real, _snap("upbit"), real))["upbit"].fails == 1      # an ok poll ends it too
    # The first real failure after the keys arrive: fails == 0 before it, so no OUTAGE until two more.
    state = {"inquiry": rows(*[_failed("okx", KEYS_MISSING)] * 3), "alerts": []}
    out = _poll(state, _new(okx=_failed("okx")), NOW)
    assert out["prev"]["okx"].fails == 0 and ("okx", "OUTAGE") not in out["raw"], out


def test_three_real_failures_raise_outage_and_a_recovery_clears_it():
    state = {"inquiry": [], "alerts": []}
    for i in range(3):
        now = NOW + timedelta(minutes=5 * i)
        out = _poll(state, _new(now, okx=_failed("okx", utc=model.iso_utc(now))), now)
        assert (("okx", "OUTAGE") in out["raw"]) == (i == 2), (i, out["raw"])
    assert ("okx", "OUTAGE") in out["fresh"]
    now = NOW + timedelta(minutes=15)
    out = _poll(state, _new(now), now)
    assert out["clears"] == [("okx", "OUTAGE")] and out["fresh"] == [], out     # logged, not alerted


# --------------------------------------------------------------------------- #
# Not set (E43; E1R2-12)
# --------------------------------------------------------------------------- #
def test_unset_limits_and_no_live_positions_are_listed_not_alerted():
    unset = _owner(caps={}, limits={})
    poor = _new(kis=_snap("kis", cash={"KRW": 1.0}))                        # far below any floor
    limits = checks.limits_from(unset, (10**9, "2026-10-23T15:00:00Z"))
    assert checks.run_checks(_prev(), poor, unset, limits, NOW) == []
    assert checks.not_set(poor, unset, limits, positions.live_positions(poor, NOW)) == (
        "FLOOR: not set", "DAILY_LOSS: not set", "OKX_CAP: not set")
    assert not {("all", "FLOOR"), ("all", "DAILY_LOSS"), ("okx", "OKX_CAP")} & checks.evaluated(
        _prev(), poor, unset, limits, NOW)
    owner = _owner(limits={"total_loss_floor_krw": 10**9, "daily_loss_krw": 1.0}, caps={"okx_equity_share": 0.01})
    stale = _new(upbit=_failed("upbit"))                                    # no live positions
    limits = checks.limits_from(owner, (10**9, "2026-10-23T15:00:00Z"))
    assert checks.run_checks(_prev(), stale, owner, limits, NOW) == []
    assert checks.not_set(stale, owner, limits, None) == (
        "FLOOR: no live positions", "DAILY_LOSS: no live positions", "OKX_CAP: no live positions")
    new = _new(kis=_failed("kis", UNSIGNED), upbit=_failed("upbit", KEYS_MISSING))
    assert checks.not_set(new, BROKEN, checks.limits_from(BROKEN, None), None) == (
        "KIS: code not signed", "Upbit: keys not in .env", "FLOOR: not set", "DAILY_LOSS: not set",
        "OKX_CAP: not set", "ADDRESS_LIST: owner log not OK")


def test_not_set_returns_only_listed_items_and_reaches_every_one():
    seen: set[str] = set()
    live = positions.live_positions(_new(), NOW)
    flagsets = (frozenset(), KEYS_MISSING, UNSIGNED, frozenset({"auth_error"}))
    for venue in snapshot.VENUES:
        for flags in flagsets:
            new = _new(**{venue: _failed(venue, flags)}) if flags else _new()
            for owner in (_owner(), _owner(caps={}, limits={}), BROKEN):
                for positions_now in (None, live):
                    items = checks.not_set(new, owner, checks.limits_from(owner, None), positions_now)
                    assert set(items) <= checks.NOT_SET_ITEMS, items
                    assert len(set(items)) == len(items), items
                    seen |= set(items)
    assert seen == checks.NOT_SET_ITEMS, sorted(checks.NOT_SET_ITEMS - seen)


# --------------------------------------------------------------------------- #
# evaluated and the once-a-day rule (E19; E1R2-2)
# --------------------------------------------------------------------------- #
def test_evaluated_names_only_checks_whose_inputs_were_there():
    owner = _owner()
    start = (60_000.0, UTC)
    prev = _prev(upbit=checks.Prior(last_ok=_snap("upbit"), fails=0))
    new = _new(kis=_snap("kis", cash={"KRW": 30_000.0}, clock_offset_s=1.0))
    per_ok = ("KEY_HEALTH", "FOREIGN_ORDER", "D15_LIVE", "HARD_BLOCK_LIVE", "OUTAGE")
    want = ({(v, k) for v in snapshot.VENUES for k in per_ok} | {("kis", "CLOCK_SKEW")}
            | {("upbit", "HOLDINGS_CHANGED"), ("upbit", "ADDRESS_LIST")}
            | {("all", "FLOOR"), ("all", "DAILY_LOSS"), ("okx", "OKX_CAP")})
    assert checks.evaluated(prev, new, owner, checks.limits_from(owner, start), NOW) == frozenset(want)
    assert ("all", "DAILY_LOSS") not in checks.evaluated(prev, new, owner, checks.limits_from(owner, None), NOW)
    # The owner log not OK: no ADDRESS_LIST, and no limit checks (their limits count as absent).
    got = checks.evaluated(prev, new, BROKEN, checks.limits_from(BROKEN, start), NOW)
    assert ("upbit", "ADDRESS_LIST") not in got and ("upbit", "HOLDINGS_CHANGED") in got
    assert not {("all", "FLOOR"), ("all", "DAILY_LOSS"), ("okx", "OKX_CAP")} & got
    # A failed venue: nothing of it, except CLOCK_SKEW when it carries an offset; no live positions either.
    failed = _new(upbit=_failed("upbit", clock_offset_s=2.0))
    got = checks.evaluated(prev, failed, owner, checks.limits_from(owner, start), NOW)
    assert {k for v, k in got if v == "upbit"} == {"CLOCK_SKEW"}, got
    assert not {("all", "FLOOR"), ("all", "DAILY_LOSS"), ("okx", "OKX_CAP")} & got
    assert all(pair != ("all", "NOT_SET") for pair in got)


def test_due_fires_once_per_venue_and_text_key_per_seoul_day():
    order = _alert("upbit", "FOREIGN_ORDER")
    assert _due_run([([order], {("upbit", "FOREIGN_ORDER")})] * 3) == [(["FOREIGN_ORDER"], []), ([], []), ([], [])]
    # The same text_key on another venue is its own key.
    kis_order = _alert("kis", "FOREIGN_ORDER")
    assert _due_run([([order], set()), ([order, kis_order], set())]) == [(["FOREIGN_ORDER"], []),
                                                                         (["FOREIGN_ORDER"], [])]


def test_due_two_text_keys_of_one_kind_are_each_fresh():
    loan, earn = _alert("okx", "D15_LOAN"), _alert("okx", "D15_EARN")
    done = {("okx", "D15_LIVE")}
    assert _due_run([([loan, earn], done)]) == [(["D15_LOAN", "D15_EARN"], [])]          # raised together
    assert _due_run([([loan], done), ([loan, earn], done), ([loan, earn], done)]) == [
        (["D15_LOAN"], []), (["D15_EARN"], []), ([], [])]                                   # D15_LOAN then D15_EARN
    explained, unexplained = _alert("upbit", "HOLDINGS_EXPLAINED"), _alert("upbit", "HOLDINGS_UNEXPLAINED")
    done = {("upbit", "HOLDINGS_CHANGED")}
    assert _due_run([([explained], done), ([unexplained], done), ([unexplained], done)]) == [
        (["HOLDINGS_EXPLAINED"], []), (["HOLDINGS_UNEXPLAINED"], ["HOLDINGS_EXPLAINED"]), ([], [])]


def test_due_a_level_rise_fires_at_once():
    auth, missing = _alert("upbit", "KEY_AUTH"), _alert("upbit", "KEY_MISSING")
    # KEY_AUTH red; then KEY_MISSING amber while KEY_HEALTH is not evaluated (KEY_AUTH not cleared); then KEY_AUTH
    # again: the latest non-clear row of (upbit, KEY_HEALTH) is amber, so it fires; the poll after, it does not.
    assert _due_run([([auth], set()), ([missing], set()), ([auth], set()), ([auth], set())]) == [
        (["KEY_AUTH"], []), (["KEY_MISSING"], []), (["KEY_AUTH"], []), ([], [])]


def test_due_lists_amber_and_info_before_red_within_a_poll():
    auth, missing = _alert("upbit", "KEY_AUTH"), _alert("upbit", "KEY_MISSING")
    note = _alert("all", "NOT_SET")
    rows: list[dict] = []
    fresh, clears = checks.due([auth, missing, note], frozenset(), rows, NOW)
    assert [a.text_key for a in fresh] == ["KEY_MISSING", "NOT_SET", "KEY_AUTH"] and clears == []
    rows += _stored(fresh, NOW)
    fresh, clears = checks.due([auth, missing], frozenset(), rows, NOW + timedelta(minutes=5))
    assert fresh == [] and clears == []                       # the red is its group's latest row: no re-fire


def test_due_clears_only_evaluated_keys_and_a_cleared_key_fires_again():
    order = _alert("upbit", "FOREIGN_ORDER")
    done = {("upbit", "FOREIGN_ORDER")}
    assert _due_run([([order], done), ([], done), ([order], done), ([], set()), ([order], done)]) == [
        (["FOREIGN_ORDER"], []), ([], ["FOREIGN_ORDER"]), (["FOREIGN_ORDER"], []), ([], []), ([], [])]
    rows = _stored([order], NOW)
    _fresh, clears = checks.due([], frozenset(done), rows, NOW + timedelta(minutes=5))
    assert clears == [checks.Alert(venue="upbit", kind="FOREIGN_ORDER", level="clear", text_key="FOREIGN_ORDER",
                                   slots={})]
    assert checks.row(clears[0], UTC)["sent"] is True and checks.verify_row(_stored(clears, NOW)[0])


def test_a_flaky_venue_neither_clears_nor_refires_foreign_order():
    order = snapshot.Order(id="u-open-1", symbol="BTC", side="buy", units=0.0001, price=90_000_000.0)
    state = {"inquiry": [], "alerts": []}
    times = [NOW + timedelta(minutes=5 * i) for i in range(3)]
    def upbit(now) -> snapshot.Snapshot:
        return _snap("upbit", utc=model.iso_utc(now), cash={"KRW": 20_000.0}, open_orders=(order,))
    out = _poll(state, _new(times[0], upbit=upbit(times[0])), times[0])
    assert out["fresh"] == [("upbit", "FOREIGN_ORDER")], out
    out = _poll(state, _new(times[1], upbit=_failed("upbit", utc=model.iso_utc(times[1]))), times[1])
    assert ("upbit", "FOREIGN_ORDER") not in out["clears"] and ("upbit", "FOREIGN_ORDER") not in out["fresh"], out
    out = _poll(state, _new(times[2], upbit=upbit(times[2])), times[2])
    assert out["fresh"] == [] and out["clears"] == [], out


def test_due_counts_rows_by_seoul_date():
    order = _alert("upbit", "FOREIGN_ORDER")
    done = frozenset({("upbit", "FOREIGN_ORDER")})
    late = datetime(2026, 10, 24, 14, 59, 59, tzinfo=timezone.utc)       # 23:59:59 KST on 2026-10-24
    rows = _stored([order], late - timedelta(minutes=5))
    assert checks.due([order], done, rows, late) == ([], [])             # the same Seoul day
    fresh, clears = checks.due([order], done, rows, late + timedelta(seconds=1))   # 00:00:00 KST on 2026-10-25
    assert [a.text_key for a in fresh] == ["FOREIGN_ORDER"] and clears == []
    # Yesterday's rows are no reason to clear today either.
    assert checks.due([], done, rows, late + timedelta(seconds=1)) == ([], [])


def test_due_writes_the_not_set_row_once_a_day_and_never_clears_it():
    note = _alert("all", "NOT_SET")
    every = {(v, k) for v in checks.VENUE_NAMES for k in checks.KINDS} - {("all", "NOT_SET")}
    day = [([note], every), ([note], every), ([], every)]
    assert _due_run(day) == [(["NOT_SET"], []), ([], []), ([], [])]
    rows = _stored([note], NOW)
    tomorrow = NOW + timedelta(days=1)
    fresh, clears = checks.due([note], frozenset(every), rows, tomorrow)
    assert [a.text_key for a in fresh] == ["NOT_SET"] and clears == []
    assert checks.row(note, UTC)["sent"] is True and checks.row(note, UTC)["level"] == "info"


def test_due_ignores_rows_that_do_not_verify():
    order = _alert("upbit", "FOREIGN_ORDER")
    good = _stored([order], NOW)[0]
    forged = [dict(good, slots={"n": "21000 KRW"}), dict(good, kind="OUTAGE"), dict(good, utc="2026-13-40T00:00:00Z"),
              dict(good, venue=["upbit"]), dict(good, text_key=["FOREIGN_ORDER"]), "not a row", None]
    fresh, _clears = checks.due([order], frozenset(), forged, NOW + timedelta(minutes=5))
    assert [a.text_key for a in fresh] == ["FOREIGN_ORDER"]               # no forged row mutes it


# --------------------------------------------------------------------------- #
# Rows, priors and the day start
# --------------------------------------------------------------------------- #
def test_row_sent_flags_and_shape():
    for key, (kind, level, _template) in checks.TEXT.items():
        alert = _alert("upbit", key)
        r = checks.row(alert, UTC)
        assert set(r) == {"kind", "level", "sent", "slots", "text_key", "utc", "venue"}
        assert r["sent"] is (level == "info") and (r["kind"], r["level"], r["utc"]) == (kind, level, UTC)
    clear = checks.Alert(venue="kis", kind="OUTAGE", level="clear", text_key="OUTAGE")
    assert checks.row(clear, UTC) == {"kind": "OUTAGE", "level": "clear", "sent": True, "slots": {},
                                      "text_key": "OUTAGE", "utc": UTC, "venue": "kis"}
    assert checks.row(_alert("kis", "FOREIGN_ORDER"), UTC)["sent"] is False
    assert checks.row(_alert("kis", "OUTAGE"), UTC)["sent"] is False


def test_verify_row_accepts_every_written_row():
    for key, (kind, _level, _template) in checks.TEXT.items():
        for venue in checks.VENUE_NAMES:
            assert checks.verify_row(_stored([_alert(venue, key)], NOW)[0]), (venue, key)
            clear = checks.Alert(venue=venue, kind=kind, level="clear", text_key=key)
            assert checks.verify_row(_stored([clear], NOW)[0]), (venue, key, "clear")
    for items in (sorted(checks.NOT_SET_ITEMS), ["KIS: code not signed"]):
        note = checks.Alert(venue="all", kind="NOT_SET", level="info", text_key="NOT_SET",
                            slots={"skipped": "; ".join(items)})
        assert checks.verify_row(_stored([note], NOW)[0])


def test_verify_row_refuses_anything_else():
    good = _stored([_alert("upbit", "HOLDINGS_UNEXPLAINED")], NOW)[0]
    note = _stored([_alert("all", "NOT_SET")], NOW)[0]
    expiry = _stored([_alert("upbit", "KEY_EXPIRY")], NOW)[0]
    assert checks.verify_row(good) and checks.verify_row(note) and checks.verify_row(expiry)
    bad = [
        {k: v for k, v in good.items() if k != "sent"},                    # a missing key
        dict(good, extra=1),                                                # an extra key
        dict(good, text_key="NO_SUCH_KEY"), dict(good, text_key=["HOLDINGS_UNEXPLAINED"]),
        dict(good, kind="FOREIGN_ORDER"), dict(good, kind=["HOLDINGS_CHANGED"]),
        dict(good, level="amber"), dict(good, level="info"),                # the key's own level or "clear" only
        dict(good, venue="binance"), dict(good, venue=["upbit"]),
        dict(good, sent="false"), dict(good, sent=0),
        dict(good, utc="2026-10-24 00:00:00"), dict(good, utc="2026-13-40T00:00:00Z"), dict(good, utc=None),
        dict(good, slots=dict(good["slots"], n=True)),                      # a bool in an int slot
        dict(good, slots=dict(good["slots"], n="2")),                       # a str in an int slot
        dict(good, slots=dict(good["slots"], n=2.0)),
        dict(good, slots=dict(good["slots"], amount=1)),                    # an extra slot
        dict(good, slots={k: v for k, v in good["slots"].items() if k != "k"}),     # a missing slot
        dict(good, slots=[1, 2]),
        dict(good, level="clear"),                                          # a clear row has no slots
        dict(expiry, slots=dict(expiry["slots"], expires="soon")),          # a time slot that is not a stamp
        dict(expiry, slots=dict(expiry["slots"], expires=1792800000)),
        dict(note, slots={"skipped": "FLOOR: not set; the account holds KRW 21000"}),   # not a NOT_SET item
        dict(note, slots={"skipped": "FLOOR: not set; "}),                  # an empty item
        dict(note, slots={"skipped": ""}), dict(note, slots={"skipped": 3}),
        [good], "row", None, 1,
    ]
    for obj in bad:
        assert checks.verify_row(obj) is False, obj


def test_priors_from_inquiry_rows():
    first = _snap("upbit", utc="2026-10-23T23:50:00Z", cash={"KRW": 1.0})
    second = _snap("upbit", utc="2026-10-23T23:55:00Z", cash={"KRW": 2.0})
    rows = [json.loads(snapshot.dump(s)) for s in (
        first, _snap("kis", utc="2026-10-23T23:50:00Z"), second, _failed("upbit", utc="2026-10-23T23:57:00Z"),
        _failed("upbit", utc="2026-10-23T23:58:00Z"))]
    tampered = dict(json.loads(snapshot.dump(_snap("upbit", utc="2026-10-23T23:59:00Z"))), cash={"KRW": 9.0})
    month_13 = _forged(json.loads(snapshot.dump(_snap("upbit", utc="2026-10-23T23:59:30Z"))),
                       utc="2026-13-40T00:00:00Z")
    got = checks.priors(rows + [tampered, month_13, {"venue": "upbit"}])    # all three are skipped
    assert got["upbit"] == checks.Prior(last_ok=second, fails=2), got["upbit"]
    assert got["kis"].last_ok is not None and got["kis"].fails == 0
    assert got["okx"] == checks.Prior(last_ok=None, fails=0)
    assert set(got) == set(snapshot.VENUES)
    assert checks.priors([]) == {v: checks.Prior(last_ok=None, fails=0) for v in snapshot.VENUES}


def test_day_start_is_todays_first_poll_with_live_positions():
    def poll(stamp: str, **venues) -> list[dict]:
        new = _new(datetime.fromisoformat(stamp), **venues)
        return [json.loads(snapshot.dump(new[v])) for v in snapshot.VENUES]
    yesterday = poll("2026-10-23T14:59:59Z")                                # 23:59:59 KST, the day before
    no_live = poll("2026-10-23T15:00:00Z", upbit=_failed("upbit", utc="2026-10-23T15:00:00Z"))
    first = poll("2026-10-23T15:05:00Z", kis=_snap("kis", utc="2026-10-23T15:05:00Z", cash={"KRW": 31_000.0}))
    later = poll("2026-10-23T15:10:00Z")
    hour_25 = [_forged(r, utc="2026-10-23T25:00:00Z") for r in poll("2026-10-23T15:01:00Z")]   # skipped
    assert checks.day_start(yesterday + no_live + hour_25 + first + later, NOW) == (61_000.0, "2026-10-23T15:05:00Z")
    assert checks.day_start(yesterday, NOW) is None
    assert checks.day_start(yesterday + no_live, NOW) is None
    assert checks.day_start([], NOW) is None
    # At 23:59:59 KST the poll at 23:59:59 KST is today's first.
    assert checks.day_start(yesterday, datetime(2026, 10, 23, 14, 59, 59, tzinfo=timezone.utc)) == (
        60_000.0, "2026-10-23T14:59:59Z")


# --------------------------------------------------------------------------- #
# The leak scan (contract 15.3)
# --------------------------------------------------------------------------- #
def _zoo() -> list[checks.Alert]:
    """Three polls whose fixtures hold balances (21000, 0.0001) and the fixture address and that raise every check
    table text_key between them."""
    order = snapshot.Order(id="0000123456", symbol="005930", side="buy", units=1.0, price=60_000.0)
    kis_last = _snap("kis", cash={"KRW": 21_000.0}, holdings={"005930": snapshot.Holding(units=2.0)},
                     prices_krw={"005930": 61_000.0})
    kis = _snap("kis", cash={"KRW": 21_000.0}, deposit_krw=21_000.0, holdings={"005930": snapshot.Holding(units=1.0)},
                prices_krw={"005930": 61_000.0}, loans={"tot_loan_amt": 21_000.0}, open_orders=(order,),
                clock_offset_s=75.0)
    upbit_last = _snap("upbit", cash={"KRW": 20_000.0}, holdings={"BTC": snapshot.Holding(units=0.0002)},
                       prices_krw={"BTC": 100_000_000.0})
    upbit = _snap("upbit", cash={"KRW": 20_000.0}, holdings={"BTC": snapshot.Holding(units=0.0001)},
                  prices_krw={"BTC": 100_000_000.0}, key_expiry=model.iso_utc(NOW + timedelta(days=10)),
                  withdrawals=(snapshot.Move(id="u-wd-1", symbol="BTC", side="out", units=0.0001),),
                  withdrawal_addresses=(snapshot.Address(currency="BTC", net_type="BTC", address=ADDRESS),))
    okx = _snap("okx", holdings={"USDT": snapshot.Holding(units=10.0)}, prices_krw={"USDT": 1_400.0},
                loans={"liab:USDT": 3.0}, earn={"savings:USDT": 5.0}, flags=frozenset({"EVENTS",
                                                                                       "derivative_position"}))
    owner = _owner(caps={"okx_equity_share": 0.01}, limits={"total_loss_floor_krw": 200_000.0,
                                                            "daily_loss_krw": 5_000.0}, addresses=frozenset())
    prev = _prev(kis=checks.Prior(last_ok=kis_last, fails=0), upbit=checks.Prior(last_ok=upbit_last, fails=0),
                 okx=checks.Prior(last_ok=None, fails=2))
    new = {"kis": kis, "upbit": upbit, "okx": okx}
    alerts = checks.run_checks(prev, new, owner, checks.limits_from(owner, (200_000.0, "2026-10-23T15:00:00Z")), NOW)
    new = dict(new, okx=_failed("okx", SELF_CHECK))
    alerts += checks.run_checks(prev, new, owner, checks.limits_from(owner, None), NOW)
    new = {"kis": _failed("kis", UNSIGNED), "upbit": _failed("upbit", frozenset({"auth_error"})),
           "okx": _failed("okx", KEYS_MISSING)}
    alerts += checks.run_checks(prev, new, owner, checks.limits_from(owner, None), NOW)
    return alerts


def test_no_balance_or_address_in_any_sentence():
    for text in ("KRW 21000", "21,000 KRW", "\u20a921000", "21000\uc6d0", "0.0001 BTC", "$5", "usdt 10", "5usd"):
        assert LEAK.search(text), text                                      # the scan catches what it must
    assert LONG_RUN.search(ADDRESS) and not LEAK.search("OKX failed 3 polls in a row")
    texts = [template for _kind, _level, template in checks.TEXT.values()]
    for key in checks.TEXT:
        for venue in checks.VENUE_NAMES:
            texts.append(checks.render(_alert(venue, key)))
    zoo = _zoo()
    raised = {a.text_key for a in zoo}
    poller_own = {"OUTAGE_CRASH", "CRASH_UNLOGGED", "EVIDENCE_BROKEN", "NOT_SET"}
    assert raised == set(checks.TEXT) - poller_own, sorted(set(checks.TEXT) - poller_own - raised)
    for a in zoo:
        assert checks.verify_row(_stored([a], NOW)[0]), a                  # every check alert's row verifies
        texts.append(checks.render(a))
    note = checks.Alert(venue="all", kind="NOT_SET", level="info", text_key="NOT_SET",
                        slots={"skipped": "; ".join(sorted(checks.NOT_SET_ITEMS))})
    texts.append(checks.render(note))
    for text in texts:
        assert not LEAK.search(text), text
        assert not LONG_RUN.search(text), text
        for needle in ("21000", "21,000", "0.0001", "61000", "bc1q", "fixtureaddress", ADDRESS):
            assert needle not in text, (needle, text)
```

- [ ] **Step 2: Run to verify it fails**

  Overlap check with the PowerShell tool (must print nothing):

```powershell
Get-CimInstance Win32_Process -Filter "Name LIKE 'python%'" | Where-Object { $_.CommandLine -match 'run_all' } | Select-Object ProcessId,Name,CommandLine
```

  Then from the repo root in Git Bash:

```bash
.venv/Scripts/python.exe -m tests.execution_acceptance execution_checks/
```

  Expected: a traceback, then

```
FAIL execution_checks/import ImportError: cannot import name 'checks' from 'execution' (C:\Users\whydi\OneDrive\Desktop\TRADEGEN\execution\__init__.py)

0/1 passed, 1 failed, 0 not run
```

  and exit code 1.

- [ ] **Step 3: Implement**

  Create `execution/checks.py` (whole file, LF). The `TEXT` entries are contract 15.3's sentences, split only where a
  line would pass 120 columns; the joined strings are byte-identical to the contract's.

```python
"""The poll checks of E1 spec 7 (plan Task 11; E7, E19, E20, E21, E31, E34, E39, E42, E43). Pure: no clock, no
file, no network.

run_checks compares one poll's three venue snapshots with each venue's prior state, the owner state and the limits,
and returns alerts; evaluated names the checks whose inputs were there, so only those clear; not_set names the checks
skipped for an unset input; due applies the once-a-day rule (E19) to the rows of alerts.jsonl. TEXT is the fixed
sentence catalogue: its slots carry counts, ISO times and not-set items only, never a balance or an address (E37).
E1 only alerts: no check halts, disarms, sells or withdraws."""
from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from types import MappingProxyType

from core.compliance import model
from execution import positions, snapshot

KINDS = ("KEY_HEALTH", "FOREIGN_ORDER", "HOLDINGS_CHANGED", "OKX_CAP", "ADDRESS_LIST", "D15_LIVE",
         "HARD_BLOCK_LIVE", "FLOOR", "DAILY_LOSS", "OUTAGE", "CLOCK_SKEW",     # spec 7's eleven checks
         "EVIDENCE", "NOT_SET")                                              # the poller's own (E33, E43)
VENUE_NAMES = MappingProxyType({"kis": "KIS", "upbit": "Upbit", "okx": "OKX", "all": "TRADEGEN"})
KEY_EXPIRY_WARN = timedelta(days=30)
OUTAGE_POLLS = 3
CLOCK_SKEW_S = 60
STAMP = re.compile(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ")            # model.iso_utc's form
INT_SLOTS = frozenset({"n", "k", "added", "removed", "days", "seconds", "fills", "deposits", "withdrawals"})
TIME_SLOTS = frozenset({"expires", "when", "since"})
ITEM_SLOTS = frozenset({"skipped"})     # a "; "-joined str of NOT_SET_ITEMS (E43)
NOT_SET_ITEMS = frozenset(                # every string not_set can return (contract 15.1)
    {f"{VENUE_NAMES[v]}: keys not in .env" for v in snapshot.VENUES} | {"KIS: code not signed"}
    | {f"{c}: {r}" for c in ("FLOOR", "DAILY_LOSS", "OKX_CAP") for r in ("not set", "no live positions")}
    | {"ADDRESS_LIST: owner log not OK"})
TEXT = MappingProxyType({                 # text_key -> (kind, level, template); contract 15.3
    "KEY_MISSING": ("KEY_HEALTH", "amber", "{venue} keys are not in .env, so E1 did not read {venue}. If you "
                    "removed them on purpose, ignore this; it repeats once a day."),
    "KIS_UNSIGNED": ("KEY_HEALTH", "amber", "E1 sent nothing to KIS: the KIS key can also trade, and TRADEGEN's "
                     "code is not signed by you. KIS stays unread until you sign the code hash; this repeats once "
                     "a day."),
    "KEY_AUTH": ("KEY_HEALTH", "red", "{venue} refused E1's key with an authentication or permission error. Check "
                 "the key, its permissions and its registered IP."),
    "KEY_OKX_SELF_CHECK": ("KEY_HEALTH", "red", "OKX key is not read-only, or the OKX account is not spot mode with "
                           "borrowing off, or the key has no bound IP ({n} of 5 checks failed). OKX inquiry "
                           "stopped for this poll."),
    "KEY_EXPIRY": ("KEY_HEALTH", "amber", "An Upbit API key of this account expires in {days} days ({expires}). "
                   "Issue a new read-only key before then."),
    "FOREIGN_ORDER": ("FOREIGN_ORDER", "red", "{venue} shows {n} open order(s). E1 places no orders: check the "
                      "{venue} app now."),
    "HOLDINGS_EXPLAINED": ("HOLDINGS_CHANGED", "amber", "{venue} holdings changed in {n} symbol(s); {fills} new "
                           "fill(s), {deposits} deposit(s) and {withdrawals} withdrawal(s) explain them."),
    "HOLDINGS_UNEXPLAINED": ("HOLDINGS_CHANGED", "red", "{venue} holdings changed in {n} symbol(s), {k} of them "
                             "with no new fill, deposit or withdrawal to explain it ({fills} new fill(s), "
                             "{deposits} deposit(s) and {withdrawals} withdrawal(s) explain the rest). Check the "
                             "{venue} app now."),
    "ADDRESS_CHANGED": ("ADDRESS_LIST", "red", "Upbit's registered withdrawal addresses changed: {added} added, "
                        "{removed} removed."),
    "ADDRESS_UNSIGNED": ("ADDRESS_LIST", "red", "Upbit lists {n} withdrawal address(es) that no signed "
                         "withdrawal_address entry of yours names."),
    "D15_BORROW": ("D15_LIVE", "red", "OKX borrowing is switched on (spot borrow or auto-loan). D15 forbids "
                   "borrowing."),
    "D15_LOAN": ("D15_LIVE", "red", "{venue} shows {n} loan, credit or margin figure(s) above zero. D15 forbids "
                 "borrowing."),
    "D15_EARN": ("D15_LIVE", "red", "OKX shows {n} Earn or lending figure(s) above zero. D15 forbids lending."),
    "HARD_BLOCK_EVENTS": ("HARD_BLOCK_LIVE", "red", "OKX shows an event-contract (EVENTS) instrument. Prediction "
                          "markets are hard-blocked."),
    "HARD_BLOCK_DERIVATIVE": ("HARD_BLOCK_LIVE", "red", "OKX shows a derivative position (swap, futures or "
                              "option). Derivatives are hard-blocked."),
    "FLOOR": ("FLOOR", "red", "Live total equity is at or below your total-loss floor. E1 only alerts: nothing was "
              "sold, halted or disarmed."),
    "DAILY_LOSS": ("DAILY_LOSS", "red", "Live total equity fell by at least your daily loss limit since the first "
                   "poll of today ({since}). E1 only alerts."),
    "OKX_CAP": ("OKX_CAP", "red", "OKX holds more than your okx_equity_share cap of live total equity (USDT and "
                "USDC included)."),
    "OUTAGE": ("OUTAGE", "amber", "{venue} failed {n} polls in a row (the last at {when})."),
    "OUTAGE_CRASH": ("OUTAGE", "amber", "An E1 poll crashed at {when}; {venue} counts as failed for it. The next "
                     "poll runs as usual."),
    "CRASH_UNLOGGED": ("OUTAGE", "amber", "An E1 poll crashed at {when} and its alert could not be written. Check "
                       "~/.tradegen/execution on the PC."),
    "EVIDENCE_BROKEN": ("EVIDENCE", "amber", "E1's evidence log does not verify, so no D16 evidence is recorded or "
                        "counted. Move ~/.tradegen/execution/evidence.jsonl aside to start a new one."),
    "CLOCK_SKEW": ("CLOCK_SKEW", "amber", "This PC's clock is {seconds} seconds away from {venue}'s server time. "
                   "Fix the Windows clock."),
    "NOT_SET": ("NOT_SET", "info", "Checks skipped (not set): {skipped}."),
})
_FIELDS = MappingProxyType({key: frozenset(re.findall(r"\{(\w+)\}", template)) - {"venue"}
                            for key, (_kind, _level, template) in TEXT.items()})     # slot names per text_key
_ROW_KEYS = frozenset({"kind", "level", "sent", "slots", "text_key", "utc", "venue"})
_OKX_SELF_CHECK = ("okx_perm", "okx_acct_lv", "okx_spot_borrow", "okx_auto_loan", "okx_no_ip")
_NOT_AN_OUTAGE = ("keys_missing", "code_unsigned")     # KEY_MISSING and KIS_UNSIGNED already say why (E31, E42)
_OK_KINDS = ("KEY_HEALTH", "FOREIGN_ORDER", "D15_LIVE", "HARD_BLOCK_LIVE", "OUTAGE")   # evaluated when ok (E19)


@dataclass(frozen=True, kw_only=True)
class Alert:
    venue: str                           # "kis" | "upbit" | "okx" | "all"
    kind: str                            # one of KINDS
    level: str                           # "red" | "amber" | "info" (NOT_SET only, E43) | "clear"
    text_key: str
    slots: Mapping[str, int | str] = field(default_factory=dict)   # ints, ISO times and NOT_SET items only


@dataclass(frozen=True, kw_only=True)
class Prior:
    last_ok: snapshot.Snapshot | None    # the venue's latest ok snapshot before this poll
    fails: int                           # not-ok polls in a row before this one; an ok snapshot or one flagged
                                         # keys_missing or code_unsigned ends the run (not set, not an outage)


@dataclass(frozen=True, kw_only=True)
class Limits:
    total_loss_floor_krw: float | None   # owner limit_set after D12 (None: not set)
    daily_loss_krw: float | None
    okx_equity_share: float | None       # owner cap_set
    day_start_equity_krw: float | None   # E34
    day_start_utc: str | None


_NO_PRIOR = Prior(last_ok=None, fails=0)


def limits_from(owner: model.OwnerState, day_start: tuple[float, str] | None) -> Limits:
    """The owner's limits and cap (None when not set; all None while the owner log is not OK, when every owner fact
    counts as absent) and the day's start (E34)."""
    limits, caps = (owner.limits, owner.caps) if owner.ok else ({}, {})
    equity, utc = day_start if day_start is not None else (None, None)
    return Limits(total_loss_floor_krw=limits.get("total_loss_floor_krw"),
                  daily_loss_krw=limits.get("daily_loss_krw"), okx_equity_share=caps.get("okx_equity_share"),
                  day_start_equity_krw=equity, day_start_utc=utc)


def priors(rows: list[dict]) -> dict[str, Prior]:
    """Per venue of snapshot.VENUES: the latest ok snapshot among `rows` (inquiry rows in file order, E30) and the
    not-ok polls in a row after it. A keys_missing or code_unsigned snapshot also ends the run, so the first real
    failure after keys arrive or the code is signed counts from 0. A row that does not load is skipped."""
    last_ok: dict[str, snapshot.Snapshot | None] = {v: None for v in snapshot.VENUES}
    fails = {v: 0 for v in snapshot.VENUES}
    for obj in rows:
        snap = _load(obj)
        venue = None if snap is None else snap.venue
        if venue not in fails:
            continue
        if snap.ok:
            last_ok[venue], fails[venue] = snap, 0
        elif any(f in snap.flags for f in _NOT_AN_OUTAGE):
            fails[venue] = 0
        else:
            fails[venue] += 1
    return {v: Prior(last_ok=last_ok[v], fails=fails[v]) for v in snapshot.VENUES}


def day_start(rows: list[dict], now: datetime) -> tuple[float, str] | None:
    """(equity_krw, utc) of the first poll on now's Seoul date whose three snapshots give live positions (E34), or
    None when there is none yet (the caller then starts the day at the current poll)."""
    today, polls = _seoul(now), {}
    for obj in rows:
        snap = _load(obj)
        if snap is not None and _seoul(_instant(snap.utc)) == today:
            polls.setdefault(snap.utc, {}).update({snap.venue: snap})   # insertion order: the file's order
    for utc, new in polls.items():
        live = positions.live_positions(new, _instant(utc))
        if live is not None:
            return live.equity_krw, utc
    return None


def run_checks(prev: Mapping[str, Prior], new: Mapping[str, snapshot.Snapshot], owner: model.OwnerState, limits: Limits,
               now: datetime) -> list[Alert]:
    """Every alert of the check table (contract 15.1) for this poll: venue by venue in snapshot.VENUES order, then
    the checks over live positions. An unset limit or cap is skipped (not_set names it)."""
    out: list[Alert] = []
    for venue in snapshot.VENUES:
        if venue in new:
            out += _venue_alerts(venue, new[venue], prev.get(venue) or _NO_PRIOR, owner, now)
    live = positions.live_positions(new, now)
    if live is None:
        return out
    if limits.total_loss_floor_krw is not None and live.equity_krw <= limits.total_loss_floor_krw:
        out.append(_alert("all", "FLOOR"))
    if (limits.daily_loss_krw is not None and _has_start(limits)
            and limits.day_start_equity_krw - live.equity_krw >= limits.daily_loss_krw):
        out.append(_alert("all", "DAILY_LOSS", since=limits.day_start_utc))
    okx = live.exposure.get("okx")
    if (limits.okx_equity_share is not None and okx is not None
            and okx.held_krw > limits.okx_equity_share * live.equity_krw):
        out.append(_alert("okx", "OKX_CAP"))
    return out


def evaluated(prev: Mapping[str, Prior], new: Mapping[str, snapshot.Snapshot], owner: model.OwnerState, limits: Limits,
              now: datetime) -> frozenset[tuple[str, str]]:
    """The (venue, kind) pairs whose inputs were there this poll (E19): only their text_keys clear. A failed venue,
    no live positions or an owner log that is not OK clears nothing; ("all", "NOT_SET") is never here (E43)."""
    done: set[tuple[str, str]] = set()
    for venue in snapshot.VENUES:
        snap = new.get(venue)
        if snap is None:
            continue
        if snap.ok:
            done.update((venue, kind) for kind in _OK_KINDS)
            if (prev.get(venue) or _NO_PRIOR).last_ok is not None:
                done.add((venue, "HOLDINGS_CHANGED"))
                if venue == "upbit" and owner.ok:
                    done.add((venue, "ADDRESS_LIST"))
        if snap.clock_offset_s is not None:
            done.add((venue, "CLOCK_SKEW"))
    if positions.live_positions(new, now) is not None:
        if limits.total_loss_floor_krw is not None:
            done.add(("all", "FLOOR"))
        if limits.daily_loss_krw is not None and _has_start(limits):
            done.add(("all", "DAILY_LOSS"))
        if limits.okx_equity_share is not None:
            done.add(("okx", "OKX_CAP"))
    return frozenset(done)


def not_set(new: Mapping[str, snapshot.Snapshot], owner: model.OwnerState, limits: Limits,
            live: model.Positions | None) -> tuple[str, ...]:
    """The checks skipped this poll, as NOT_SET_ITEMS strings in a fixed order (contract 15.1); no alert."""
    items: list[str] = []
    for venue in snapshot.VENUES:
        flags = new[venue].flags if venue in new else frozenset()
        if "keys_missing" in flags:
            items.append(f"{VENUE_NAMES[venue]}: keys not in .env")
        elif venue == "kis" and "code_unsigned" in flags:
            items.append("KIS: code not signed")
    for check, value in (("FLOOR", limits.total_loss_floor_krw), ("DAILY_LOSS", limits.daily_loss_krw),
                         ("OKX_CAP", limits.okx_equity_share)):
        if value is None:
            items.append(f"{check}: not set")
        elif live is None:
            items.append(f"{check}: no live positions")
    if not owner.ok:
        items.append("ADDRESS_LIST: owner log not OK")
    return tuple(items)


def due(raw: list[Alert], done: frozenset[tuple[str, str]], rows: list[dict], now: datetime
        ) -> tuple[list[Alert], list[Alert]]:
    """(fresh, clears) under the once-a-day rule (E19, contract 15.2), from today's rows of alerts.jsonl: a raw alert
    is fresh when its (venue, text_key) has no row today or its latest row today is a clear, or when it is red and
    the latest non-clear row today of its (venue, kind) is amber (a level rise fires at once). Fresh alerts keep raw
    order, amber and info before red. A key raised today, not raised now and whose kind was evaluated gets one clear.
    A row that does not verify (verify_row) counts for nothing, so a malformed line can never mute an alert."""
    today = _seoul(now)
    latest: dict[tuple[str, str], str] = {}
    group: dict[tuple[str, str], str] = {}
    for obj in rows:
        if not verify_row(obj) or _seoul(_instant(obj["utc"])) != today:
            continue
        key = (obj["venue"], obj["text_key"])
        latest[key] = obj["level"]
        if obj["level"] != "clear":
            group[(key[0], TEXT[key[1]][0])] = obj["level"]
    fresh = [a for a in raw if latest.get((a.venue, a.text_key), "clear") == "clear"
             or (a.level == "red" and group.get((a.venue, a.kind)) == "amber")]
    raised = {(a.venue, a.text_key) for a in raw}
    clears = [Alert(venue=venue, kind=TEXT[key][0], level="clear", text_key=key)
              for (venue, key), level in latest.items()
              if level != "clear" and (venue, TEXT[key][0]) in done and (venue, key) not in raised]
    return sorted(fresh, key=lambda a: a.level == "red"), clears


def render(alert: Alert) -> str:
    """The fixed sentence of a red, amber or info alert (a toast, or a line of --pending)."""
    return TEXT[alert.text_key][2].format(venue=VENUE_NAMES[alert.venue], **alert.slots)


def row(alert: Alert, utc: str) -> dict:
    """The alerts.jsonl row; red and amber rows wait for the daily task (sent false), clear and info rows never
    leave the PC (sent true)."""
    return {"kind": alert.kind, "level": alert.level, "sent": alert.level in ("clear", "info"),
            "slots": dict(alert.slots), "text_key": alert.text_key, "utc": utc, "venue": alert.venue}


def verify_row(obj: object) -> bool:
    """True only for a row of the shape row() writes (contract 15.2): the seven keys, a catalogue text_key with its
    own kind and level (or "clear"), a known venue, a bool sent, a stamp utc, and exactly the template's slots with
    ints, stamps and not-set items in them (none for a clear row). --pending re-checks every row with it."""
    if not isinstance(obj, dict) or set(obj) != _ROW_KEYS:
        return False
    key, level, slots = obj["text_key"], obj["level"], obj["slots"]
    if not isinstance(key, str) or key not in TEXT or not isinstance(slots, dict):
        return False
    if obj["kind"] != TEXT[key][0] or level not in (TEXT[key][1], "clear") or type(obj["sent"]) is not bool:
        return False
    if not isinstance(obj["venue"], str) or obj["venue"] not in VENUE_NAMES:
        return False
    if not _is_stamp(obj["utc"]):
        return False
    if set(slots) != (frozenset() if level == "clear" else _FIELDS[key]):
        return False
    return all(_slot_ok(name, value) for name, value in slots.items())


def _slot_ok(name: str, value: object) -> bool:
    if name in INT_SLOTS:
        return type(value) is int
    if name in TIME_SLOTS:
        return _is_stamp(value)
    if name in ITEM_SLOTS:
        return isinstance(value, str) and all(item in NOT_SET_ITEMS for item in value.split("; "))
    return False


def _venue_alerts(venue: str, snap: snapshot.Snapshot, prior: Prior, owner: model.OwnerState,
                  now: datetime) -> list[Alert]:
    """The per-venue rows of the check table, in table order."""
    flags, out = snap.flags, []
    if "keys_missing" in flags:
        out.append(_alert(venue, "KEY_MISSING"))
    if venue == "kis" and "code_unsigned" in flags:
        out.append(_alert(venue, "KIS_UNSIGNED"))
    if "auth_error" in flags:
        out.append(_alert(venue, "KEY_AUTH"))
    failed = sum(f in flags for f in _OKX_SELF_CHECK)
    if venue == "okx" and failed:
        out.append(_alert(venue, "KEY_OKX_SELF_CHECK", n=failed))
    if venue == "upbit" and snap.ok and _is_stamp(snap.key_expiry):
        left = _instant(snap.key_expiry) - now
        if left <= KEY_EXPIRY_WARN:
            out.append(_alert(venue, "KEY_EXPIRY", days=max(0, left.days), expires=snap.key_expiry))
    if snap.ok and snap.open_orders:
        out.append(_alert(venue, "FOREIGN_ORDER", n=len(snap.open_orders)))
    if snap.ok and prior.last_ok is not None:
        out += _holdings(venue, prior.last_ok, snap)
    listed = _address_set(snap)
    if venue == "upbit" and snap.ok and prior.last_ok is not None and listed != _address_set(prior.last_ok):
        before = _address_set(prior.last_ok)
        out.append(_alert(venue, "ADDRESS_CHANGED", added=len(listed - before), removed=len(before - listed)))
    if venue == "upbit" and snap.ok and owner.ok:
        signed = {(symbol, address, tag) for _dest, symbol, _network, address, tag in owner.addresses}
        if listed - signed:
            out.append(_alert(venue, "ADDRESS_UNSIGNED", n=len(listed - signed)))
    if venue == "okx" and ("okx_spot_borrow" in flags or "okx_auto_loan" in flags):
        out.append(_alert(venue, "D15_BORROW"))
    loans = sum(value > 0 for value in snap.loans.values())
    if snap.ok and loans:
        out.append(_alert(venue, "D15_LOAN", n=loans))
    earn = sum(value > 0 for value in snap.earn.values())
    if venue == "okx" and snap.ok and earn:
        out.append(_alert(venue, "D15_EARN", n=earn))
    if venue == "okx" and "EVENTS" in flags:
        out.append(_alert(venue, "HARD_BLOCK_EVENTS"))
    if venue == "okx" and "derivative_position" in flags:
        out.append(_alert(venue, "HARD_BLOCK_DERIVATIVE"))
    if not snap.ok and not any(f in flags for f in _NOT_AN_OUTAGE) and prior.fails + 1 >= OUTAGE_POLLS:
        out.append(_alert(venue, "OUTAGE", n=prior.fails + 1, when=snap.utc))
    if snap.clock_offset_s is not None and abs(snap.clock_offset_s) > CLOCK_SKEW_S:
        out.append(_alert(venue, "CLOCK_SKEW", seconds=round(abs(snap.clock_offset_s))))
    return out


def _holdings(venue: str, last: snapshot.Snapshot, snap: snapshot.Snapshot) -> list[Alert]:
    """HOLDINGS_EXPLAINED or HOLDINGS_UNEXPLAINED when a symbol's units changed since the last ok snapshot: a
    changed symbol is explained by a new fill naming it (symbol or counter) or a new deposit or withdrawal of it."""
    changed = {s for s in set(last.holdings) | set(snap.holdings) if _differs(_units(last, s), _units(snap, s))}
    if not changed:
        return []
    fills = _new_moves(last.fills, snap.fills)
    deposits = _new_moves(last.deposits, snap.deposits)
    withdrawals = _new_moves(last.withdrawals, snap.withdrawals)
    explained = {m.symbol for m in fills + deposits + withdrawals} | {m.counter for m in fills}
    counts = {"fills": sum(m.symbol in changed or m.counter in changed for m in fills),
              "deposits": sum(m.symbol in changed for m in deposits),
              "withdrawals": sum(m.symbol in changed for m in withdrawals)}
    unexplained = len(changed - explained)
    if unexplained:
        return [_alert(venue, "HOLDINGS_UNEXPLAINED", n=len(changed), k=unexplained, **counts)]
    return [_alert(venue, "HOLDINGS_EXPLAINED", n=len(changed), **counts)]


def _alert(venue: str, text_key: str, **slots: int | str) -> Alert:
    kind, level, _template = TEXT[text_key]
    return Alert(venue=venue, kind=kind, level=level, text_key=text_key, slots=slots)


def _load(obj: object) -> snapshot.Snapshot | None:
    """snapshot.load(obj), or None for a row that does not load or whose utc is not a model.iso_utc stamp."""
    try:
        snap = snapshot.load(obj)
    except (LookupError, TypeError, ValueError, AttributeError):
        return None
    return snap if _is_stamp(snap.utc) else None


def _units(snap: snapshot.Snapshot, symbol: str) -> float:
    held = snap.holdings.get(symbol)
    return 0.0 if held is None else held.units


def _differs(a: float, b: float) -> bool:
    return abs(a - b) > 1e-12 * max(1.0, abs(a), abs(b))


def _new_moves(before: tuple, after: tuple) -> list:
    ids = {m.id for m in before}
    return [m for m in after if m.id not in ids]


def _address_set(snap: snapshot.Snapshot) -> frozenset[tuple[str, str, str]]:
    return frozenset((a.currency, a.address, a.secondary_address or "") for a in snap.withdrawal_addresses)


def _has_start(limits: Limits) -> bool:
    return limits.day_start_equity_krw is not None and limits.day_start_utc is not None


def _is_stamp(value: object) -> bool:
    """A model.iso_utc string that names a real instant (STAMP alone admits month 13)."""
    if not isinstance(value, str) or STAMP.fullmatch(value) is None:
        return False
    try:
        _instant(value)
    except ValueError:
        return False
    return True


def _instant(stamp: str) -> datetime:
    return datetime.fromisoformat(stamp)            # aware UTC: Python 3.11+ reads the "Z"


def _seoul(moment: datetime) -> date:
    return moment.astimezone(model.KST).date()
```

- [ ] **Step 4: Run to verify it passes**

  Run the overlap check of Step 2 (PowerShell tool; it must print nothing) before EACH Python command below. All run
  from the repo root in Git Bash; none of them is a `--suite` run, so `qa/acceptance_results.json` is not written.

  Overlap check, then the new module:

```bash
.venv/Scripts/python.exe -m tests.execution_acceptance execution_checks/
```

  Expected: 40 `PASS execution_checks/test_...` lines, then `40/40 passed, 0 failed, 0 not run` (exit code 0; about
  a second).

  Overlap check, then the execution guards, whose scans now include `execution/checks.py` (import allowlist, no clock,
  no write, no verb call, the token rules, no rebinding):

```bash
.venv/Scripts/python.exe -m tests.execution_acceptance execution_guards/
```

  Expected, ending: `N/N passed, 0 failed, 0 not run` (exit code 0) with the same N as at the end of Task 10: this
  task adds no guard test. A failure names the offending file and text: fix `execution/checks.py`, never the guard.

  Overlap check, then the D14 closure test, since `execution/checks.py` joins the signed code closure (Task 9 seeds
  `execution/*.py`) and must import nothing outside it (`core.compliance.model`, `execution.positions`,
  `execution.snapshot` only):

```bash
.venv/Scripts/python.exe -m tests.compliance_acceptance compliance_store/test_code_files_is_the_import_closure
```

  Expected: `PASS compliance_store/test_code_files_is_the_import_closure`, then `1/1 passed, 0 failed, 0 not run`
  (exit code 0).

  Overlap check, then the repo-wide read-only guards over the runtime surface, `execution/` included (T-RO-01,
  test_08, test_09; this calls the test functions directly and writes nothing):

```bash
.venv/Scripts/python.exe -c "from tests.macro_m0_harness import test_t_ro_01_no_order_cancel_withdrawal_or_transfer_path as t, test_t_ro_01_orders_module_reached_only_through_the_engine as u; from tests.acceptance import test_08_no_broker_order_path as t8, test_09_no_account_credentials_requested as t9; t(); u(); t8(); t9(); print('T-RO-01 ok')"
```

  Expected: `T-RO-01 ok` (exit code 0).

  Then the raw-text checks (git only, no overlap check needed; `--untracked` because the files are not committed yet):

```bash
git grep --untracked -n -i -E "order_cash|order-cash|place_order|submit_order|tttc0802u|tttc0801u|vttc0802u|private_key|seed_phrase|append_system_entry|system_halt|system_disarm|x-simulated-trading|openapivts|/v1/order|/v1/withdraw|/uapi/|context_log/|reference_mode|eodhd|quartr" -- execution/checks.py tests/execution_checks.py
git grep --untracked -n -E "CANO|KIS_ACCOUNT|ACNT_PRDT_CD|KIS_APP|UPBIT_|OKX_API|requests|\.now\(|utcnow|date\.today|time\.time|monotonic|perf_counter|open\(|[A-Za-z]{4}[0-9]{4}[A-Za-z]|0\.4 \*" -- execution/checks.py
git grep --untracked -n -E "CANO|KIS_ACCOUNT|ACNT_PRDT_CD|subprocess|multiprocessing|runpy|sys\.executable|os\.system|os\.popen|importlib" -- tests/execution_checks.py
```

  Expected: all three print nothing (exit code 1 each).

- [ ] **Step 5: Commit**

```bash
git status --short
git add execution/checks.py tests/execution_checks.py
git diff --cached --stat
git diff --cached --stat --ignore-cr-at-eol
```

  `git status --short` lists exactly the two new files (`?? execution/checks.py`, `?? tests/execution_checks.py`).
  The two stat outputs must be identical (both files are LF). Then, with the trailer naming the model that writes
  the commit (Global Constraints 0.4):

```bash
git commit -m "feat(execution): poll checks, alert catalogue and the once-a-day rule" -m "Task 11: execution/checks.py (pure: no clock, no file, no network) and tests/execution_checks.py; execution/*.py is in the D14 code hash since Task 9, so the code hash changes again (nothing is signed yet)." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
