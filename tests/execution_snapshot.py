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
from tests.compliance_fixtures import directory_link

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
    root = _t4_root()                                   # scanned clean before the junction exists
    day = S.inquiry_path(date(2026, 10, 24))
    elsewhere = root / "elsewhere"
    elsewhere.mkdir()
    directory_link(root / "execution", elsewhere)
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
