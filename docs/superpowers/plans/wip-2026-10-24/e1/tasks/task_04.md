### Task 4: Snapshot records and JSONL helpers (`execution/snapshot.py`)

**Files:**
- Create: `execution/snapshot.py` (LF, UTF-8, no BOM)
- Create: `tests/execution_snapshot.py` (LF, UTF-8, no BOM)
- Modify: `tests/execution_fixtures.py` (anchor: the end of Task 3's `serve()`, the last four lines of the file; LF)
- Test: `tests/execution_snapshot.py`

**Interfaces:**
- Consumes:
  - `core.isolation.checked_target(path, what="path", *, within=None) -> Path` (core/isolation.py:40-56 at `5816d3c`):
    `RuntimeError` for a QUANTGEN path, a symlink or junction (its text holds `is a symlink or junction`), or an
    existing file with a second name (its text holds `is a hard link`); it judges only the final component and
    creates nothing. `core.isolation.state_root() -> Path` (core/isolation.py:105-110): `TRADEGEN_HOME`, else
    `~/.tradegen`; its link scan runs once per root and is memoised in `isolation._LINK_SCAN`, which
    `tests.compliance_fixtures.temp_home()` clears on the way in and out (compliance_fixtures.py:16-32).
  - `core.compliance.model` (model.py:24-70): `jsonable(obj)` (a dataclass becomes a dict of its fields, a Mapping a
    dict, a set or frozenset a sorted list, a tuple a list; a non-finite float is a `ValueError` whose text starts
    `not a finite number`; it recurses once per nesting level), `canonical_json(obj) -> str` (`json.dumps(
    jsonable(obj), sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)`),
    `sha256_hex(data) -> str`, `iso_utc(moment) -> str`. Neither later plan changes these four (contract 0.6 lists
    only new users of model.py and Task 9's `seal_context` edit).
  - `core.compliance.owner._exclusive` (owner.py:378-397 at `5816d3c`): copied into `exclusive`, never imported (it
    is private). The copy is E1's own: a later change to the original needs no change here.
  - Task 1: `tests/execution_acceptance.py` (`MODULES` already lists `execution_snapshot`; `_wrap` runs each test
    inside `hermetic()`, `temp_home()` and `isolated(home)`; `_main` runs the entries whose name contains its
    argument and prints `<passed>/<total> passed, <failed> failed, <not run> not run`); `tests.execution_fixtures.NOW`
    (`datetime(2026, 10, 24, 0, 0, 0, tzinfo=timezone.utc)`, 09:00 KST); `tests/execution_guards.py`, whose scans of
    every `execution/**/*.py` now see `execution/snapshot.py` (with Task 2's `_path_hits` and `_token_hits`).
  - `tests.compliance_fixtures.temp_home()` names the temp home `tradegen_home_*` (compliance_fixtures.py:19);
    `tests.notrun.NotRun` (tests/notrun.py:25; reasons start `REFDATA:` here, as tests/compliance_isolation.py:46).
- Produces (`execution/snapshot.py`, contract section 8; Tasks 5 to 12 use these exact names):
  - `VENUES = ("kis", "upbit", "okx")`; `STALE_AFTER = timedelta(minutes=15)`; `FLAGS`, the ten flags of section 8
    (`code_unsigned` included).
  - `class FieldError(ValueError)`: `args[0]` is the field's name, never its value (E37).
  - Frozen kw_only records: `Holding(units, locked=0.0, avg_cost=None)`, `Order(id, symbol, side, units,
    price=None)`, `Move(id, symbol, counter="", side, units)`, `Address(currency, net_type, address,
    secondary_address="")`, and `Snapshot` with the 21 fields of section 8 in that order, `snapshot_sha256` last.
  - `Snapshot.__post_init__`: makes `flags` a frozenset (a list or set given by a parser hashes the same as the
    frozenset `load` rebuilds), raises `ValueError("snapshot: venue is not kis, upbit or okx")` for a venue outside
    `VENUES` and `ValueError("snapshot: a flag outside FLAGS")` for a flag outside `FLAGS`, then sets
    `snapshot_sha256 = model.sha256_hex(model.canonical_json(body))` over every other field with
    `object.__setattr__` (as `model.Decision` sets `decision_id`); a non-finite number is model.jsonable's
    `ValueError`. Each of these is a `ValueError`, which E38 contains as a failed snapshot in a venue parser.
  - `home() -> Path` = `state_root() / "execution"`; `inquiry_path(day: date) -> Path` =
    `home() / f"inquiry-{day:%Y%m%d}.jsonl"`. Neither creates anything; `day` is the Asia/Seoul date, which the
    caller computes (Task 12).
  - `failed(venue, utc, error, *, flags=frozenset(), server_utc=None, clock_offset_s=None) -> Snapshot`: `ok=False`,
    every collection empty, `flags` a frozenset, `error` exactly as given (it adds no text).
  - `dump(snap) -> bytes` = `(model.canonical_json(snap) + "\n").encode("utf-8")`.
  - `load(obj) -> Snapshot`: raises only `ValueError`, whose text starts `"snapshot row: "` and names no value: when
    `obj` is not a dict with exactly the 21 field names, when a record does not rebuild (a `TypeError`,
    `ValueError`, `AttributeError` or `RecursionError` inside, reported by its type name only), when
    `snapshot_sha256` does not recompute, or when `obj` is not the row `dump` writes for the record it rebuilt
    (`"snapshot row: not canonical"`: a string, list or dict standing in for another container, flags unsorted or
    repeated).
  - `exclusive(path)`, a context manager: `checked_target(path.parent, "E1 state folder").mkdir(parents=True,
    exist_ok=True)`, then one process-wide `threading.Lock` and the OS byte lock on
    `checked_target(str(path) + ".lock", "E1 lock file")` opened `"a+b"` (`msvcrt.LK_LOCK` after `seek(0)`, which
    retries for about 10 s and then raises `OSError`; else `fcntl.LOCK_EX`), released in `finally`. It creates the
    folder and the lock file only. No caller may nest two `exclusive()` calls in one thread (none does: contract
    16.2 takes the inquiry, evidence and alerts locks one after another, and poll.py takes `poll.lock` with its own
    code, 16.1).
  - `write_lines(path, lines, what) -> None`: the caller holds `exclusive(path)`, or for the daily files
    `exclusive(home() / "inquiry")`; that `exclusive` is what judges the folder. No lines: it returns at once
    (nothing is opened or created). Else `open(checked_target(path, what), "a+b")`, a `b"\n"` first when the file is
    non-empty and does not end in one, the joined lines, flush, `os.fsync`. A refused target raises
    `checked_target`'s `RuntimeError`, uncaught (a crash, E33, E38).
  - `append_lines(path, lines, what) -> None` = `write_lines` under `exclusive(path)`.
  - `read_all(path) -> list[dict]`: the JSON-object lines in file order; a line that is not UTF-8, not JSON, nested
    deeper than `json.loads` reads (`RecursionError`) or not an object is skipped; a missing file is `[]`; any other
    `OSError` propagates. It takes no lock and creates nothing.
  - Private: `_FIELDS` (the frozenset of the 21 field names) and `_LOCK`. There is no `read_since` (E30, E1R2-4).
- Produces (`tests/execution_fixtures.py`, contract 3.2): `snap(venue: str, **fields) -> Snapshot`, the ok snapshot
  `Snapshot(venue=venue, utc="2026-10-24T00:00:00Z", server_utc="2026-10-24T00:00:00Z", clock_offset_s=0.0,
  ok=True)` in which `fields` override any of these or set any other field (Tasks 8 to 12 use it); it imports
  `execution.snapshot` and `core.compliance.model` inside the function, never at module level (Task 1's
  `test_aggregator_skips_missing_and_isolates_broken_modules` checks the module-level imports).

**Plan decisions used:** E4 (canonical JSON, sha256 hex, the copied sidecar lock with fsync), E16 (the snapshot
fields: settled fiat `cash`, coins as holdings, `deposit_krw`, the recent-window lists), E17 (`STALE_AFTER`, read by
Task 8), E30 with E1R2-4 (daily `inquiry-YYYYMMDD.jsonl` files under one `inquiry.lock`; `read_all`, no
`read_since`), E33 and E38 (a refused write propagates as a crash), E37 (`FieldError(name)`; error and `load` texts
from names only), E39 (`clock_offset_s`), E42 (the `code_unsigned` flag); contract sections 0.5, 3.2 and 8.

Design notes (read before Step 3):
- Three points refine section 8 where it is silent; none renames anything. (1) `write_lines` opens `"a+b"` where
  section 8 writes `"ab"`: the same handle reads the last byte to isolate a torn line, and append mode still puts
  every byte at the end (owner.py's lock file is opened the same way); the 0.5 guard accepts it, since the first
  argument of that `open()` is a call of `checked_target`. (2) `__post_init__` makes `flags` a frozenset and
  refuses a venue or flag outside the lists, and `load` refuses a row whose keys are not exactly the fields (an
  extra key would ride along unhashed) or that is not the row `dump` writes for the record it rebuilt (`dict()` and
  `tuple()` would otherwise turn `""`, `[]` or a list of pairs into a valid container and a dict `flags` into its
  keys; the hash binds only the rebuilt values, so such a row changes no value, but it is not a line E1 wrote); all
  raise `ValueError` with names-only text, so E37 and E38 hold. The comparison runs inside the same `try` as the
  rebuild, so any error in it is reported the same way.
  (3) `load` turns a `RecursionError` into `ValueError`: measured on the venv (Python 3.13.14), `json.loads` reads
  2,998 nested objects while `model.jsonable` stops near 1,000, so a forged deep row that `read_all` returns would
  otherwise escape Task 11's `checks._load`, which catches `LookupError`, `TypeError`, `ValueError` and
  `AttributeError` only. No ledger ruling is needed for these: they are this plan's own text.
- Snapshots carry no clock: `utc` is the poll's `now` that the caller passes in, and the Seoul date that picks the
  daily file is computed by the poller (Task 12). This module reads no clock, no key and no network.
- `checked_target` judges only the last component of a path, so `write_lines` alone would write through a junction
  folder; every caller writes inside an `exclusive()` on the same folder (contract 16.2 steps 3, 4 and 7, 16.4),
  and `exclusive` judges that folder first. The junction test writes the way the poller does.
- Every test writes only under the suite's temp home: `_t4_root()` refuses any state root whose folder name does not
  start with `tradegen_home_` before a file is written, so calling a test function outside the wrapper writes
  nothing to the real `~/.tradegen`. The two link tests compute their paths first (so the state-root link scan runs
  on a clean root and is memoised) and make the link after, as tests/compliance_owner.py:568-584 does; they prove
  that `checked_target` itself refuses, not the scan.

- [ ] **Step 1: Write the failing tests**

  First the fixture. Re-read `tests/execution_fixtures.py` (DRIFT RULE, C0.6). `git ls-files --eol
  tests/execution_fixtures.py` must start with `i/lf    w/lf` (Task 1 created and committed it LF; the rest of the
  line is `attr/-text` and the path, since .gitattributes is `* -text`); the file must define `NOW` at module level
  (Task 1) and must not define `snap`. If either does not hold, stop and rule, and record the ruling in
  `docs/superpowers/plans/2026-10-24-e1-account-inquiry-execution-ledger.md`. Then append the block below at the very
  end of the file with one Edit-tool replacement, anchor: the end of Task 3's `serve()` (its `try`/`finally`, the
  last four lines of the file; `Seq` comes before `serve()`). If the file does not end with these four lines, stop
  and rule in the same ledger.
  - `old_string`, with no newline after the last line:

```text
    try:
        yield calls
    finally:
        transport._send = keep
```

  - `new_string` = those same four lines, then `\n\n\n` (one newline ending the old last line, then two empty lines),
    then the block below from its first `#` up to and including `    return Snapshot(**(base | fields))`, with NO
    newline after it. The file's existing final newline, which `old_string` left outside the match, then closes the
    block, so the file still ends in exactly one newline. The block:

```python
# --------------------------------------------------------------------------- #
# Task 4: snapshots (contract 3.2)
# --------------------------------------------------------------------------- #
def snap(venue: str, **fields) -> "Snapshot":
    """An ok `execution.snapshot.Snapshot` of `venue` stamped NOW (venue time NOW, offset 0.0); `fields` override
    any of these or set any other field. execution is imported here, never at module level (contract 3.2)."""
    from core.compliance import model
    from execution.snapshot import Snapshot
    base = {"venue": venue, "utc": model.iso_utc(NOW), "server_utc": model.iso_utc(NOW), "clock_offset_s": 0.0,
            "ok": True}
    return Snapshot(**(base | fields))
```

  Check the end of the file from the repo root; it must print `True False False` (the block ends the file, no blank
  line after it, no CR anywhere):

```bash
.venv/Scripts/python.exe -c "import pathlib; b = pathlib.Path('tests/execution_fixtures.py').read_bytes(); print(b.endswith(b'    return Snapshot(**(base | fields))\n'), b.endswith(b'\n\n'), b'\r' in b)"
```

  Then create `tests/execution_snapshot.py` (whole file, LF):

```python
"""Snapshot records and the JSONL helpers (E1 plan Task 4; spec 4 "State files", 6 "Snapshot"; E4, E16, E30, E37).

Every test runs inside tests.execution_acceptance._wrap (hermetic, a temp TRADEGEN_HOME, the refusing send) and
writes only under that temp home: `_t4_root()` refuses any other state root before a file is written. Helpers are
prefixed `_t4_` so that a later task appending here cannot shadow them.
"""
from __future__ import annotations

import contextlib
import dataclasses
import hashlib
import inspect
import json
import os
import threading
from datetime import date, timedelta
from pathlib import Path

from core.compliance import model
from execution import snapshot as S
from tests import execution_fixtures as F
from tests.notrun import NotRun

_T4_VICTIM = b"another file's bytes: E1 never writes them\n"
_T4_ADDRESS = "bc1qfixtureaddress000000000000000000000"
_T4_KEYS = ("cash", "clock_offset_s", "deposit_krw", "deposits", "earn", "error", "fills", "flags", "holdings",
            "key_expiry", "loans", "ok", "open_orders", "prices_krw", "response_sha256", "server_utc",
            "snapshot_sha256", "utc", "venue", "withdrawal_addresses", "withdrawals")   # contract 8, sorted


def _t4_root() -> Path:
    """The suite's temp TRADEGEN_HOME (tests.compliance_fixtures.temp_home names it tradegen_home_*). Any other root
    is refused before a file is written, so a direct call outside the wrapper never touches ~/.tradegen."""
    root = Path(os.environ.get("TRADEGEN_HOME") or "")
    if not root.name.startswith("tradegen_home_"):
        raise AssertionError(f"not inside the suite's temp home: {root}")
    assert S.home() == root / "execution", S.home()
    return root


def _t4_listing(root: Path) -> list[str]:
    """Every path under `root`, relative and sorted."""
    return sorted(p.relative_to(root).as_posix() for p in root.rglob("*"))


def _t4_raises(call, kind: type[Exception] = ValueError) -> str:
    """The message of the `kind` exception `call()` raises; AssertionError when it raises none."""
    try:
        call()
    except kind as exc:
        return str(exc)
    raise AssertionError(f"no {kind.__name__} raised")


def _t4_refused(call, needle: str) -> None:
    """`call()` must raise checked_target's RuntimeError, whose text names `needle`."""
    text = _t4_raises(call, RuntimeError)
    assert needle in text, text


def _t4_full() -> S.Snapshot:
    """An ok Upbit-shaped snapshot with every field set away from its default."""
    return F.snap(
        "upbit", server_utc="2026-10-24T00:00:01Z", clock_offset_s=1.0,
        holdings={"BTC": S.Holding(units=0.0001, locked=0.0, avg_cost=100_000_000.0)},
        cash={"KRW": 20_000.0}, deposit_krw=21_000.0,
        open_orders=(S.Order(id="u-open-1", symbol="BTC", side="buy", units=0.0001, price=90_000_000.0),),
        fills=(S.Move(id="u-done-1", symbol="BTC", counter="KRW", side="buy", units=0.0001),),
        deposits=(S.Move(id="u-dep-1", symbol="KRW", side="in", units=20_000.0),),
        withdrawals=(S.Move(id="u-wd-1", symbol="BTC", side="out", units=0.0001),),
        withdrawal_addresses=(S.Address(currency="BTC", net_type="BTC", address=_T4_ADDRESS),),
        key_expiry="2027-05-27T06:17:51Z", loans={"loan_amt": 0.0}, earn={"savings": 0.0},
        flags=frozenset({"EVENTS"}), prices_krw={"BTC": 100_000_000.0, "USDT": 1_400.0},
        response_sha256={"/v1/accounts": "a" * 64})


# field -> a value other than _t4_full()'s; a nested record changes one inner field
_T4_ALT = {
    "venue": "kis", "utc": "2026-10-24T00:05:00Z", "server_utc": "2026-10-24T00:00:02Z", "clock_offset_s": 2.0,
    "ok": False, "error": "upbit: /v1/accounts: field balance",
    "holdings": {"BTC": S.Holding(units=0.0001, locked=0.00005, avg_cost=100_000_000.0)},
    "cash": {"KRW": 20_001.0}, "deposit_krw": None,
    "open_orders": (S.Order(id="u-open-1", symbol="BTC", side="buy", units=0.0001, price=90_000_001.0),),
    "fills": (S.Move(id="u-done-1", symbol="BTC", counter="USDT", side="buy", units=0.0001),),
    "deposits": (), "withdrawals": (S.Move(id="u-wd-2", symbol="BTC", side="out", units=0.0001),),
    "withdrawal_addresses": (S.Address(currency="BTC", net_type="BTC", address=_T4_ADDRESS, secondary_address="m"),),
    "key_expiry": None, "loans": {"loan_amt": 1.0}, "earn": {}, "flags": frozenset({"EVENTS", "okx_perm"}),
    "prices_krw": {"BTC": 100_000_001.0, "USDT": 1_400.0}, "response_sha256": {"/v1/accounts": "b" * 64},
}


# --------------------------------------------------------------------------- #
# The records and their hash
# --------------------------------------------------------------------------- #
def test_snapshot_sha256_is_the_hash_of_every_other_field():
    s = _t4_full()
    body = json.loads(S.dump(s))
    stored = body.pop("snapshot_sha256")
    text = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    assert stored == s.snapshot_sha256 == hashlib.sha256(text.encode("utf-8")).hexdigest()
    assert _t4_full().snapshot_sha256 == s.snapshot_sha256                   # stable: same fields, same hash
    assert dataclasses.replace(s, snapshot_sha256="0" * 64).snapshot_sha256 == s.snapshot_sha256   # never supplied
    assert len(s.snapshot_sha256) == 64 and set(s.snapshot_sha256) <= set("0123456789abcdef")


def test_snapshot_sha256_changes_with_every_field():
    names = {f.name for f in dataclasses.fields(S.Snapshot)} - {"snapshot_sha256"}
    assert set(_T4_ALT) == names, sorted(names ^ set(_T4_ALT))              # a new field needs a case here
    base = _t4_full()
    seen = {base.snapshot_sha256}
    for name, value in _T4_ALT.items():
        assert getattr(base, name) != value, name
        changed = dataclasses.replace(base, **{name: value})
        assert changed.snapshot_sha256 not in seen, name
        seen.add(changed.snapshot_sha256)


def test_non_finite_numbers_are_refused():
    nan, inf = float("nan"), float("inf")
    builds = (
        lambda: F.snap("kis", deposit_krw=nan),
        lambda: F.snap("kis", cash={"KRW": inf}),
        lambda: F.snap("kis", clock_offset_s=-inf),
        lambda: F.snap("okx", loans={"liab": nan}),
        lambda: F.snap("okx", earn={"savings": inf}),
        lambda: F.snap("upbit", prices_krw={"BTC": nan}),
        lambda: F.snap("upbit", holdings={"BTC": S.Holding(units=inf)}),
        lambda: F.snap("upbit", holdings={"BTC": S.Holding(units=1.0, avg_cost=nan)}),
        lambda: F.snap("kis", open_orders=(S.Order(id="o", symbol="005930", side="buy", units=1.0, price=inf),)),
        lambda: F.snap("kis", fills=(S.Move(id="f", symbol="005930", side="buy", units=nan),)),
        lambda: S.failed("kis", "2026-10-24T00:00:00Z", "kis: x", clock_offset_s=nan),
    )
    for n, build in enumerate(builds):
        assert "finite" in _t4_raises(build), n
    line = S.dump(_t4_full())
    assert b'"KRW":20000.0' in line and b"NaN" not in line
    row = json.loads(line.replace(b'"KRW":20000.0', b'"KRW":NaN'))           # json.loads reads NaN; load must not
    assert row["cash"]["KRW"] != row["cash"]["KRW"]
    assert _t4_raises(lambda: S.load(row)) == "snapshot row: ValueError"


def test_venues_and_flags_are_fixed():
    assert S.VENUES == ("kis", "upbit", "okx") and S.STALE_AFTER == timedelta(minutes=15)
    assert S.FLAGS == frozenset({"keys_missing", "code_unsigned", "auth_error", "okx_perm", "okx_acct_lv",
                                 "okx_spot_borrow", "okx_auto_loan", "okx_no_ip", "EVENTS", "derivative_position"})
    assert F.snap("okx", flags=S.FLAGS).flags == S.FLAGS                       # every flag together
    for venue in ("binance", "all", "KIS", ""):
        assert _t4_raises(lambda v=venue: F.snap(v)) == "snapshot: venue is not kis, upbit or okx", venue
    for flags in ({"keys-missing"}, {"events"}, {"EVENTS", "withdraw_ok"}, "EVENTS"):   # a str is its letters
        assert _t4_raises(lambda f=flags: F.snap("okx", flags=f)) == "snapshot: a flag outside FLAGS", flags


def test_field_error_carries_the_field_name_only():
    exc = S.FieldError("prvs_rcdl_excc_amt")
    assert isinstance(exc, ValueError) and exc.args == ("prvs_rcdl_excc_amt",) and str(exc) == "prvs_rcdl_excc_amt"
    assert S.FieldError("x").args[0] == "x"


def test_failed_is_not_ok_and_adds_no_text_of_its_own():
    utc = "2026-10-24T00:00:00Z"
    f = S.failed("kis", utc, "code not signed", flags=frozenset({"code_unsigned"}))
    assert f.ok is False and f.error == "code not signed" and f.flags == frozenset({"code_unsigned"})
    obj = json.loads(S.dump(f))
    for key in ("holdings", "cash", "loans", "earn", "prices_krw", "response_sha256"):
        assert obj[key] == {}, key
    for key in ("open_orders", "fills", "deposits", "withdrawals", "withdrawal_addresses"):
        assert obj[key] == [], key
    for key in ("deposit_krw", "key_expiry", "server_utc", "clock_offset_s"):
        assert obj[key] is None, key
    assert {v for v in obj.values() if isinstance(v, str)} == {"kis", utc, "code not signed", f.snapshot_sha256}
    g = S.failed("okx", utc, "okx self-check failed: okx_perm", flags={"okx_perm"}, server_utc=utc,
                 clock_offset_s=0.25)
    assert isinstance(g.flags, frozenset) and g.flags == frozenset({"okx_perm"})
    assert (g.ok, g.server_utc, g.clock_offset_s) == (False, utc, 0.25)


# --------------------------------------------------------------------------- #
# dump and load
# --------------------------------------------------------------------------- #
def test_dump_is_canonical_json_with_sorted_keys_and_one_newline():
    for s in (_t4_full(), S.failed("kis", "2026-10-24T00:00:00Z", "code not signed", flags={"code_unsigned"})):
        line = S.dump(s)
        assert isinstance(line, bytes) and line.endswith(b"\n") and line.count(b"\n") == 1
        assert line == (model.canonical_json(s) + "\n").encode("utf-8")
        obj = json.loads(line)
        assert tuple(obj) == _T4_KEYS                                          # every field, keys sorted
        again = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
        assert line == again.encode("utf-8")                                   # nested keys sorted too
    obj = json.loads(S.dump(_t4_full()))
    assert obj["holdings"] == {"BTC": {"avg_cost": 100000000.0, "locked": 0.0, "units": 0.0001}}
    assert obj["flags"] == ["EVENTS"] and obj["open_orders"][0]["price"] == 90000000.0
    assert obj["withdrawal_addresses"] == [{"address": _T4_ADDRESS, "currency": "BTC", "net_type": "BTC",
                                            "secondary_address": ""}]


def test_load_rebuilds_every_record_and_round_trips():
    snaps = [_t4_full(), F.snap("kis"), F.snap("okx", flags=["okx_perm", "EVENTS"]),
             S.failed("upbit", "2026-10-24T00:00:00Z", "upbit: /v1/accounts: field balance", flags={"auth_error"},
                      server_utc="2026-10-24T00:00:01Z", clock_offset_s=-0.5)]
    assert snaps[2].flags == frozenset({"EVENTS", "okx_perm"})                # a list is made a frozenset
    for s in snaps:
        back = S.load(json.loads(S.dump(s)))
        assert back == s and back.snapshot_sha256 == s.snapshot_sha256
    back = S.load(json.loads(S.dump(snaps[0])))
    assert isinstance(back.holdings["BTC"], S.Holding) and isinstance(back.open_orders, tuple)
    assert isinstance(back.open_orders[0], S.Order) and isinstance(back.fills[0], S.Move)
    assert isinstance(back.withdrawal_addresses[0], S.Address) and isinstance(back.flags, frozenset)
    path = _t4_root() / "execution" / "round_trip.jsonl"
    S.append_lines(path, [S.dump(s) for s in snaps], "probe")
    assert [S.load(r) for r in S.read_all(path)] == snaps


def test_a_tampered_row_is_refused_and_the_text_names_no_value():
    good = json.loads(S.dump(_t4_full()))

    def edited(change) -> dict:
        row = json.loads(json.dumps(good))
        change(row)
        return row

    deep = json.loads('{"a":' * 2000 + "123456" + "}" * 2000)              # json reads it; jsonable cannot recurse
    tampered = [
        edited(lambda r: r["cash"].update(KRW=123456.0)),                    # a value changed, the hash kept
        edited(lambda r: r.update(ok=False)),
        edited(lambda r: r.update(snapshot_sha256="0" * 64)),
        edited(lambda r: r.update(extra=123456)),                            # a field the record does not have
        edited(lambda r: r.pop("error")),
        edited(lambda r: r.update(holdings={"BTC": [123456]})),
        edited(lambda r: r["open_orders"][0].update(note="123456")),
        edited(lambda r: r.update(fills="123456")),
        edited(lambda r: r.update(flags=["EVENTS", "nope"])),
        edited(lambda r: r.update(cash=[["KRW", 123456.0]])),
        edited(lambda r: r.update(cash=deep)),
        [good],
        "123456",
    ]
    for n, row in enumerate(tampered):
        text = _t4_raises(lambda r=row: S.load(r))
        assert text.startswith("snapshot row: ") and "123456" not in text, (n, text)
    assert _t4_raises(lambda: S.load(tampered[-3])) == "snapshot row: RecursionError"
    assert S.load(good) == _t4_full()
    empty = json.loads(S.dump(S.failed("kis", "2026-10-24T00:00:00Z", "kis: x")))
    two = json.loads(S.dump(F.snap("okx", flags={"EVENTS", "okx_perm"})))
    look_alikes = [                                     # the values are unchanged, so the hash still recomputes
        edited(lambda r: r.update(cash=[["KRW", 20000.0]])),
        edited(lambda r: r.update(earn=[["savings", 0.0]])),
        edited(lambda r: r.update(flags={"EVENTS": 0})),
        edited(lambda r: r.update(flags=["EVENTS", "EVENTS"])),
        dict(two, flags=["okx_perm", "EVENTS"]),
        dict(empty, deposits=""), dict(empty, withdrawals={}), dict(empty, open_orders={}),
        dict(empty, prices_krw=""), dict(empty, earn=[]), dict(empty, loans=[]),
    ]
    for n, row in enumerate(look_alikes):
        assert _t4_raises(lambda r=row: S.load(r)) == "snapshot row: not canonical", n
    assert S.load(empty) == S.failed("kis", "2026-10-24T00:00:00Z", "kis: x")
    assert S.load(two).flags == frozenset({"EVENTS", "okx_perm"})


# --------------------------------------------------------------------------- #
# Paths, the sidecar lock and the JSONL helpers
# --------------------------------------------------------------------------- #
def test_paths_live_under_the_state_root_and_computing_them_creates_nothing():
    root = _t4_root()
    before = _t4_listing(root)
    assert S.inquiry_path(date(2026, 10, 24)) == root / "execution" / "inquiry-20261024.jsonl"
    assert S.inquiry_path(date(2026, 10, 24)).name == "inquiry-20261024.jsonl"
    assert S.inquiry_path(date(2027, 1, 5)).name == "inquiry-20270105.jsonl"
    assert S.read_all(S.inquiry_path(date(2026, 10, 24))) == []                # a missing file reads as []
    S.write_lines(S.inquiry_path(date(2026, 10, 24)), [], "E1 inquiry log")   # no lines: nothing opens
    assert _t4_listing(root) == before and not S.home().exists()
    assert not hasattr(S, "read_since")                                        # E30: the daily files replace it


def _t4_order(guard, wait: float) -> list[str]:
    """The order in which two threads pass through `guard()`: A gets in first, then waits up to `wait` s for B."""
    order: list[str] = []
    a_in, b_in = threading.Event(), threading.Event()

    def a() -> None:
        with guard():
            order.append("a-in")
            a_in.set()
            b_in.wait(wait)                    # under a real lock B cannot get in, so this wait times out
            order.append("a-out")

    def b() -> None:
        a_in.wait(5)
        with guard():
            order.append("b-in")
            b_in.set()

    threads = [threading.Thread(target=a), threading.Thread(target=b)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(30)
    assert not any(t.is_alive() for t in threads), "a thread is stuck"
    return order


def _t4_os_locked(lock: Path) -> bool:
    """True when a second, read-only handle cannot take the byte lock of `lock` (another process would not)."""
    with open(lock, "rb") as fh:
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(fh.fileno(), msvcrt.LK_NBRLCK, 1)
                fh.seek(0)
                msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(fh, fcntl.LOCK_SH | fcntl.LOCK_NB)
                fcntl.flock(fh, fcntl.LOCK_UN)
        except OSError:
            return True
    return False


def test_exclusive_serialises_two_threads_and_holds_an_os_lock():
    path = _t4_root() / "execution" / "probe.jsonl"
    assert _t4_order(contextlib.nullcontext, 5) == ["a-in", "b-in", "a-out"]  # control: without a lock B gets in
    assert _t4_order(lambda: S.exclusive(path), 0.5) == ["a-in", "a-out", "b-in"]
    lock = path.parent / "probe.jsonl.lock"
    assert lock.is_file() and not path.exists()                               # only the lock file is made
    with S.exclusive(path):                             # both locks: the OS lock alone also serialises two threads
        assert _t4_os_locked(lock) and S._LOCK.locked()
    assert not _t4_os_locked(lock) and not S._LOCK.locked()


def test_append_lines_isolates_a_torn_last_line():
    path = _t4_root() / "execution" / "rows.jsonl"
    S.append_lines(path, [b'{"a":1}\n'], "probe")
    assert path.read_bytes() == b'{"a":1}\n' and (path.parent / "rows.jsonl.lock").is_file()
    with open(path, "ab") as fh:
        fh.write(b'{"b":')                                                    # a crash in the middle of a line
    S.append_lines(path, [b'{"c":3}\n', b'{"d":4}\n'], "probe")
    S.append_lines(path, [b'{"e":5}\n'], "probe")                              # ends in a newline: none added
    assert path.read_bytes() == b'{"a":1}\n{"b":\n{"c":3}\n{"d":4}\n{"e":5}\n'
    assert S.read_all(path) == [{"a": 1}, {"c": 3}, {"d": 4}, {"e": 5}]
    S.write_lines(path, [], "probe")
    assert path.read_bytes().endswith(b'{"d":4}\n{"e":5}\n')
    assert "os.fsync(fh.fileno())" in inspect.getsource(S.write_lines)       # E4: every append is fsynced


def test_read_all_keeps_file_order_and_skips_unreadable_lines():
    path = _t4_root() / "mixed.jsonl"
    path.write_bytes(b'{"n":1}\n' + b'not json\n' + b'[1,2]\n' + b'"text"\n' + b'\xff\xfe{}\n' + b'\n'
                     + b"[" * 100_000 + b'\n' + b'{"n":2}\r\n' + b'{"n":3,"x":{"y":[1]}}\n' + b'{"n":')
    assert S.read_all(path) == [{"n": 1}, {"n": 2}, {"n": 3, "x": {"y": [1]}}]
    assert S.read_all(_t4_root() / "missing.jsonl") == []


def test_two_seoul_days_land_in_two_files_under_one_lock_file():
    root = _t4_root()
    late = F.snap("kis", utc="2026-10-23T14:59:59Z")                          # 23:59:59 KST on 23 October
    early = F.snap("kis", utc="2026-10-23T15:00:00Z")                         # 00:00:00 KST on 24 October
    with S.exclusive(S.home() / "inquiry"):
        S.write_lines(S.inquiry_path(date(2026, 10, 23)), [S.dump(late)], "E1 inquiry log")
        S.write_lines(S.inquiry_path(date(2026, 10, 24)), [S.dump(early)], "E1 inquiry log")
    assert sorted(p.name for p in (root / "execution").iterdir()) == [
        "inquiry-20261023.jsonl", "inquiry-20261024.jsonl", "inquiry.lock"]
    assert [S.load(r) for r in S.read_all(S.inquiry_path(date(2026, 10, 23)))] == [late]
    assert [S.load(r) for r in S.read_all(S.inquiry_path(date(2026, 10, 24)))] == [early]


def test_a_hard_linked_target_is_refused_and_nothing_is_written():
    root = _t4_root()                                   # the state-root link scan runs now, on a clean root
    day = S.inquiry_path(date(2026, 10, 24))
    day.parent.mkdir()
    victim, lock_victim = root / "victim.jsonl", root / "lock_victim"
    victim.write_bytes(_T4_VICTIM)
    lock_victim.write_bytes(_T4_VICTIM)
    os.link(victim, day)
    os.link(lock_victim, S.home() / "evidence.jsonl.lock")
    line = S.dump(F.snap("kis"))

    def under_the_inquiry_lock() -> None:
        with S.exclusive(S.home() / "inquiry"):
            S.write_lines(day, [line], "E1 inquiry log")

    def under_a_linked_lock() -> None:
        with S.exclusive(S.home() / "evidence.jsonl"):
            raise AssertionError("the hard-linked lock file was opened")

    _t4_refused(under_the_inquiry_lock, "hard link")
    _t4_refused(lambda: S.append_lines(day, [line], "E1 inquiry log"), "hard link")
    _t4_refused(under_a_linked_lock, "hard link")
    _t4_refused(lambda: S.append_lines(S.home() / "evidence.jsonl", [line], "E1 evidence log"), "hard link")
    assert victim.read_bytes() == lock_victim.read_bytes() == _T4_VICTIM
    assert not (S.home() / "evidence.jsonl").exists()


def test_a_junction_folder_is_refused_and_nothing_is_written():
    try:
        import _winapi
    except ImportError:
        raise NotRun("REFDATA: directory junctions need Windows") from None
    root = _t4_root()                                   # scanned clean before the junction exists
    day = S.inquiry_path(date(2026, 10, 24))
    elsewhere = root / "elsewhere"
    elsewhere.mkdir()
    _winapi.CreateJunction(str(elsewhere), str(root / "execution"))
    line = S.dump(F.snap("kis"))

    def as_the_poller_writes() -> None:                 # exclusive() judges the folder before write_lines opens
        with S.exclusive(S.home() / "inquiry"):
            S.write_lines(day, [line], "E1 inquiry log")

    _t4_refused(as_the_poller_writes, "junction")
    _t4_refused(lambda: S.append_lines(day, [line], "E1 inquiry log"), "junction")
    assert list(elsewhere.iterdir()) == []


def test_snap_fixture_is_an_ok_snapshot_stamped_now():
    s = F.snap("kis")
    assert (s.venue, s.ok, s.error, s.clock_offset_s) == ("kis", True, None, 0.0)
    assert s.utc == s.server_utc == model.iso_utc(F.NOW) == "2026-10-24T00:00:00Z"
    later = F.snap("okx", utc="2026-10-24T00:15:01Z", ok=False)
    assert (later.venue, later.utc, later.ok) == ("okx", "2026-10-24T00:15:01Z", False)
```

- [ ] **Step 2: Run to verify it fails**

  Overlap check with the PowerShell tool (it must print nothing; if it prints a process, wait and re-run it):

```powershell
Get-CimInstance Win32_Process -Filter "Name LIKE 'python%'" | Where-Object { $_.CommandLine -match 'run_all' } | Select-Object ProcessId,Name,CommandLine
```

  Then from the repo root in Git Bash (the prefix repeats the overlap check; the command runs only when it is
  empty):

```bash
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && .venv/Scripts/python.exe -m tests.execution_acceptance execution_snapshot/
```

  Expected (exit code 1): a traceback ending
  `ImportError: cannot import name 'snapshot' from 'execution' (<repo>\execution\__init__.py)`, the line
  `FAIL execution_snapshot/import ImportError: cannot import name 'snapshot' from 'execution' (<repo>\execution\__init__.py)`
  (`<repo>` is `C:\Users\whydi\OneDrive\Desktop\TRADEGEN`), then `0/1 passed, 1 failed, 0 not run`. Python 3.13
  reports a missing submodule named in `from execution import snapshot` this way (checked on the venv), not as
  `ModuleNotFoundError`. Any other failure (an `ImportError` naming `tests.execution_fixtures`, a `SyntaxError`)
  means Step 1 went wrong: fix it before Step 3.

- [ ] **Step 3: Implement**

  Create `execution/snapshot.py` (whole file, LF). It imports only `__future__`, `contextlib`, `dataclasses`,
  `json`, `os`, `threading`, `collections.abc`, `datetime`, `pathlib`, `msvcrt` or `fcntl` (inside `exclusive`),
  `core.compliance` and `core.isolation`, all on the 0.5 allowlist. It holds no `getattr`, no attribute assignment
  and no `object.__setattr__` outside `__post_init__` (Task 2's `_path_hits`). If you touch a docstring, write the
  word "canonical" in lower case only: test_09 and T-RO-01 match the KIS account-field text case-sensitively, and
  the upper-case spelling of that word contains it (0.5).

```python
"""One normalised, hashed record per venue per poll (E1 spec 6 "Snapshot"; plan E4, E16, E30, E37), the daily
inquiry files, and the sidecar lock and JSONL helpers every E1 state file uses (spec 4 "State files").

Paths are computed at call time under `core.isolation.state_root()/"execution"`, so a test's TRADEGEN_HOME moves
them; computing one creates nothing. Every write goes through `checked_target` just before it opens, the lock file
included. No clock, no key and no network: the poller passes the time in."""
from __future__ import annotations

import contextlib
import dataclasses
import json
import os
import threading
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

from core.compliance import model
from core.isolation import checked_target, state_root

VENUES = ("kis", "upbit", "okx")
STALE_AFTER = timedelta(minutes=15)                 # an older snapshot gives no live positions (spec 6, E17)
FLAGS = frozenset({"keys_missing", "code_unsigned", "auth_error", "okx_perm", "okx_acct_lv", "okx_spot_borrow",
                   "okx_auto_loan", "okx_no_ip", "EVENTS", "derivative_position"})   # code_unsigned: KIS only, E42


class FieldError(ValueError):
    """A response field is missing or malformed. args[0] is the field's name, a literal of the parser; never its
    value (E37)."""


@dataclass(frozen=True, kw_only=True)
class Holding:
    units: float                          # total held, locked included
    locked: float = 0.0
    avg_cost: float | None = None         # in the venue's quote currency, where the venue gives one


@dataclass(frozen=True, kw_only=True)
class Order:
    id: str
    symbol: str
    side: str                             # "buy" | "sell"
    units: float
    price: float | None = None


@dataclass(frozen=True, kw_only=True)
class Move:
    """A fill, a deposit or a withdrawal."""
    id: str
    symbol: str
    counter: str = ""
    side: str                             # "buy" | "sell" | "in" | "out"
    units: float


@dataclass(frozen=True, kw_only=True)
class Address:
    currency: str
    net_type: str
    address: str
    secondary_address: str = ""


@dataclass(frozen=True, kw_only=True)
class Snapshot:
    """One venue at one poll (spec 6). `flags` is made a frozenset; snapshot_sha256 is always derived from every
    other field. A venue outside VENUES, a flag outside FLAGS or a number that is not finite is ValueError."""
    venue: str
    utc: str                              # the poll's now, model.iso_utc
    server_utc: str | None = None         # the venue's time (first Date header; OKX public/time), model.iso_utc
    clock_offset_s: float | None = None   # venue time minus the PC clock at receipt of that answer (E39)
    ok: bool
    error: str | None = None              # names, paths and codes only (E37)
    holdings: Mapping[str, Holding] = field(default_factory=dict)
    cash: Mapping[str, float] = field(default_factory=dict)          # fiat currency -> settled amount (E16)
    deposit_krw: float | None = None      # KIS dnca_tot_amt (D16 evidence); None elsewhere
    open_orders: tuple[Order, ...] = ()
    fills: tuple[Move, ...] = ()          # the venue's recent window (E16)
    deposits: tuple[Move, ...] = ()
    withdrawals: tuple[Move, ...] = ()
    withdrawal_addresses: tuple[Address, ...] = ()   # Upbit only
    key_expiry: str | None = None         # Upbit: earliest expire_at, model.iso_utc
    loans: Mapping[str, float] = field(default_factory=dict)         # name -> amount (E26)
    earn: Mapping[str, float] = field(default_factory=dict)          # OKX: name -> amount (E26)
    flags: frozenset = frozenset()        # subset of FLAGS
    prices_krw: Mapping[str, float] = field(default_factory=dict)    # symbol or currency -> KRW price used
    response_sha256: Mapping[str, str] = field(default_factory=dict) # path -> sha256 of the body; the OKX algo
                                          # calls use f"{path}?ordType={t}"; never a KIS query (E37)
    snapshot_sha256: str = ""             # set by __post_init__

    def __post_init__(self) -> None:
        object.__setattr__(self, "flags", frozenset(self.flags))     # a list or set hashes as the frozenset would
        if self.venue not in VENUES:
            raise ValueError("snapshot: venue is not kis, upbit or okx")
        if not self.flags <= FLAGS:
            raise ValueError("snapshot: a flag outside FLAGS")
        body = {k: v for k, v in model.jsonable(self).items() if k != "snapshot_sha256"}
        object.__setattr__(self, "snapshot_sha256", model.sha256_hex(model.canonical_json(body)))


_FIELDS = frozenset(f.name for f in dataclasses.fields(Snapshot))


def home() -> Path:
    """`<state root>/execution`, resolved at call time. Computing it creates nothing."""
    return state_root() / "execution"


def inquiry_path(day: date) -> Path:
    """The inquiry file of one Asia/Seoul date (E30): `inquiry-YYYYMMDD.jsonl`. Computing it creates nothing."""
    return home() / f"inquiry-{day:%Y%m%d}.jsonl"


def failed(venue: str, utc: str, error: str, *, flags=frozenset(), server_utc=None, clock_offset_s=None) -> Snapshot:
    """A not-ok snapshot: no holdings, cash or lists, only the error text (names, paths and codes, E37)."""
    return Snapshot(venue=venue, utc=utc, server_utc=server_utc, clock_offset_s=clock_offset_s, ok=False,
                    error=error, flags=flags)


def dump(snap: Snapshot) -> bytes:
    """One inquiry line: the canonical JSON of every field (keys sorted) plus a newline, UTF-8."""
    return (model.canonical_json(snap) + "\n").encode("utf-8")


def load(obj: dict) -> Snapshot:
    """The Snapshot a dump() line holds, nested records rebuilt. ValueError unless `obj` has exactly the snapshot
    fields, every record rebuilds, snapshot_sha256 recomputes (a tampered row) and `obj` is the row dump() writes for
    that Snapshot (a look-alike container is refused); the text names no value."""
    if not isinstance(obj, dict) or set(obj) != _FIELDS:
        raise ValueError("snapshot row: not the snapshot fields")
    try:
        snap = Snapshot(
            venue=obj["venue"], utc=obj["utc"], server_utc=obj["server_utc"], clock_offset_s=obj["clock_offset_s"],
            ok=obj["ok"], error=obj["error"],
            holdings={k: Holding(**v) for k, v in obj["holdings"].items()},
            cash=dict(obj["cash"]), deposit_krw=obj["deposit_krw"],
            open_orders=tuple(Order(**o) for o in obj["open_orders"]),
            fills=tuple(Move(**m) for m in obj["fills"]),
            deposits=tuple(Move(**m) for m in obj["deposits"]),
            withdrawals=tuple(Move(**m) for m in obj["withdrawals"]),
            withdrawal_addresses=tuple(Address(**a) for a in obj["withdrawal_addresses"]),
            key_expiry=obj["key_expiry"], loans=dict(obj["loans"]), earn=dict(obj["earn"]),
            flags=obj["flags"], prices_krw=dict(obj["prices_krw"]),
            response_sha256=dict(obj["response_sha256"]))
        same = json.loads(dump(snap)) == obj            # dict() and tuple() above also take "", [] or pairs
    except (TypeError, ValueError, AttributeError, RecursionError) as exc:   # json nests deeper than jsonable recurses
        raise ValueError(f"snapshot row: {type(exc).__name__}") from None
    if snap.snapshot_sha256 != obj["snapshot_sha256"]:
        raise ValueError("snapshot row: snapshot_sha256 does not recompute")
    if not same:
        raise ValueError("snapshot row: not canonical")
    return snap


# ponytail: one process-wide lock for every path, as owner._exclusive; nesting two exclusive() calls in one thread
# deadlocks (no caller nests them: poll.py takes poll.lock with its own code). Per-path locks if one ever must.
_LOCK = threading.Lock()


@contextlib.contextmanager
def exclusive(path: Path) -> Iterator[None]:
    """Serialise read-and-append on `path` across threads and processes: a sidecar `<path>.lock` holding an OS byte
    lock (a copy of core.compliance.owner._exclusive, which is private). Creates the folder and the lock file only."""
    checked_target(path.parent, "E1 state folder").mkdir(parents=True, exist_ok=True)
    with _LOCK, open(checked_target(str(path) + ".lock", "E1 lock file"), "a+b") as fh:
        if os.name == "nt":
            import msvcrt
            fh.seek(0)
            msvcrt.locking(fh.fileno(), msvcrt.LK_LOCK, 1)       # retries for about 10 s, then raises
        else:
            import fcntl
            fcntl.flock(fh, fcntl.LOCK_EX)
        try:
            yield
        finally:
            if os.name == "nt":
                fh.seek(0)
                msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(fh, fcntl.LOCK_UN)


def write_lines(path: Path, lines: Sequence[bytes], what: str) -> None:
    """Append whole lines (each ending in a newline) to `path` with fsync; the caller holds exclusive(path) or, for
    the daily inquiry files, exclusive(home() / "inquiry"). A torn last line left by a crash stays isolated: a
    newline goes first when the file does not end in one. No lines: no file is opened or created."""
    if not lines:
        return
    with open(checked_target(path, what), "a+b") as fh:     # a+ reads the last byte; every write still appends
        end = fh.seek(0, os.SEEK_END)
        if end:
            fh.seek(end - 1)
            if fh.read(1) != b"\n":
                fh.write(b"\n")
        fh.write(b"".join(lines))
        fh.flush()
        os.fsync(fh.fileno())


def append_lines(path: Path, lines: Sequence[bytes], what: str) -> None:
    """write_lines under exclusive(path)."""
    with exclusive(path):
        write_lines(path, lines, what)


def read_all(path: Path) -> list[dict]:
    """Every JSON-object line of `path` in file order; a line that does not parse as one (a torn line, a foreign
    line, one nested too deep) is skipped; a missing file is []. Takes no lock and creates nothing."""
    try:
        with open(path, "rb") as fh:
            raw = fh.read()
    except FileNotFoundError:
        return []
    rows = []
    for line in raw.split(b"\n"):
        try:
            obj = json.loads(line.decode("utf-8"))
        except (ValueError, RecursionError):            # UnicodeDecodeError and JSONDecodeError are ValueErrors
            continue
        if isinstance(obj, dict):
            rows.append(obj)
    return rows
```

- [ ] **Step 4: Run to verify it passes**

  Run the overlap check before EACH command below (the Git Bash prefix does it). All from the repo root.

```bash
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && .venv/Scripts/python.exe -m tests.execution_acceptance execution_snapshot/
```

  Expected: 17 lines `PASS execution_snapshot/test_<name>`, then `17/17 passed, 0 failed, 0 not run` (exit code 0,
  about 1.5 s; the thread test waits 0.5 s once). On a machine without `_winapi` the junction test is
  `NOT_RUN execution_snapshot/test_a_junction_folder_is_refused_and_nothing_is_written REFDATA: directory junctions
  need Windows` and the line is `16/17 passed, 0 failed, 1 not run`; this PC is Windows, so 17/17 is the result
  here.

```bash
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && .venv/Scripts/python.exe -m tests.execution_acceptance execution_guards/
```

  Expected: only `PASS execution_guards/<name>` lines, then `24/24 passed, 0 failed, 0 not run` (the 18 guard tests
  of Task 1 and the 6 of Task 2, contract 4.5; this task adds none). The guards now scan `execution/snapshot.py`:
  the import allowlist, `checked_target` on every write, no clock, no rebinding, the token rules. If Tasks 1 to 3
  as executed left a different number of guard tests, the same line with that number and `0 failed, 0 not run`
  passes; record the count in the ledger's "Runs" section.

```bash
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && .venv/Scripts/python.exe -c "from tests.macro_m0_harness import test_t_ro_01_no_order_cancel_withdrawal_or_transfer_path as t, test_t_ro_01_orders_module_reached_only_through_the_engine as u; t(); u(); print('T-RO-01 ok')"
```

  Expected: `T-RO-01 ok`.

```bash
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && .venv/Scripts/python.exe -c "from tests.acceptance import test_08_no_broker_order_path as a, test_09_no_account_credentials_requested as b, test_16_every_source_file_is_utf8_readable as c, test_18_eodhd_is_gone_from_the_runtime as d; a(); b(); c(); d(); print('cockpit scans ok')"
```

  Expected: `cockpit scans ok` (the four text scans of `runtime_py()`, which holds `execution/**/*.py` since Task 1,
  over the real tree; nothing is written, no results file).

```bash
git status --short
```

  Expected: exactly `?? execution/snapshot.py`, `?? tests/execution_snapshot.py` and ` M tests/execution_fixtures.py`
  (nothing under `qa/`, nothing else; `__pycache__/` is ignored, .gitignore:3).

- [ ] **Step 5: Commit**

```bash
git add execution/snapshot.py tests/execution_snapshot.py tests/execution_fixtures.py
git diff --cached --stat
git diff --cached --stat --ignore-cr-at-eol
git ls-files --eol execution/snapshot.py tests/execution_snapshot.py tests/execution_fixtures.py
```

  The two stat outputs must be identical (they catch a CR added to the modified fixtures file). They cannot catch a
  CRLF new file, since both count each of its lines as one insertion and .gitattributes (`* -text`) stores it as
  written; the `--eol` lines do. Each of the three lines must start with `i/lf    w/lf` (the rest is `attr/-text`
  and the path; git lists them sorted by path). Any other start (`i/crlf`, `i/mixed`) means stop: rewrite that file
  with LF endings using the Write tool, `git add` it again and repeat all three checks.

  Then commit. In the trailer, replace `<the committing model>` with the name of the model that writes this commit,
  for example `Claude Sonnet 5.5` or `Claude Opus 5.5` (contract 0.4):

```bash
git commit -m "feat(execution): snapshot records, daily inquiry files and JSONL helpers" -m "E1 Task 4: execution/snapshot.py (hashed Snapshot records, failed, dump and load, inquiry-YYYYMMDD.jsonl paths, the sidecar lock, torn-line-safe fsynced appends, read_all), its tests and the snap() fixture." -m "Co-Authored-By: <the committing model> <noreply@anthropic.com>"
```
