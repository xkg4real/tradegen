"""Owner log format and verification (Task 11; spec 6.4 "The log", "Events", 8.9; P20).

Every test runs inside the compliance wrapper: hermetic() and a fresh temporary TRADEGEN_HOME. `_home()` refuses any
other home, and every test that writes calls it before anything else, so a test called bare stops before touching
~/.tradegen. Signed logs use the fixed test key only; tests that need it report NOT_RUN PENDING until cryptography is
installed (Task 10)."""
from __future__ import annotations

import base64
import hashlib
import importlib.util
import json
import os
import random
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path

from core.compliance import model, owner
from tests import compliance_fixtures as F

ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 10, 23, 1, 2, 3, tzinfo=timezone.utc)
FIVE = [
    ("approved", {"kind": "rules", "sha256": "1" * 64}),
    ("cap_set", {"key": "okx_equity_share", "value": 0.1}),
    ("limit_set", {"total_loss_floor_krw": 21000.0, "daily_loss_krw": 5000.0}),
    ("system_halt", {"floor_krw": 21000.0}),
    ("withdrawal_address", {"venue": "upbit", "symbol": "BTC", "network": "bitcoin", "address": "bc1qtest",
                            "tag": None, "evidence": "Upbit deposit-address screen, 2026-10-23"}),
]
FILES = [["core/__init__.py", "7" * 64], ["core/compliance/owner.py", "8" * 64]]
DEEP = b"[" * 100_000 + b"]" * 100_000 + b"\n"          # nested far past the recursion limit


def _home() -> Path:
    """The wrapper's temporary TRADEGEN_HOME; anything else stops the test before it writes."""
    home = Path(os.environ["TRADEGEN_HOME"])            # KeyError outside the compliance wrapper
    assert home.name.startswith("tradegen_home_") and not home.resolve().is_relative_to(
        (Path.home() / ".tradegen").resolve()), f"not a temp home: {home}"
    return home


def _same(a: Path, b: Path) -> bool:
    return a.resolve() == b.resolve()


def _key(start: int):
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    return Ed25519PrivateKey.from_private_bytes(bytes(range(start, start + 32)))


def _raw(key) -> bytes:
    return key.public_key().public_bytes_raw()


def _b64(raw: bytes) -> str:
    return base64.b64encode(raw).decode("ascii")


def _row(line: bytes) -> str:
    return json.loads(line)["row_sha256"]


def _system_lines(n: int) -> list[bytes]:
    """n chained, unsigned system_halt lines: no key, so no cryptography needed."""
    lines, prev = [], owner.GENESIS_PREV
    for seq in range(1, n + 1):
        lines.append(F.signed_entry(None, seq, prev, "system_halt", {"floor_krw": 1000.0 * seq}))
        prev = _row(lines[-1])
    return lines


def _relined(line: bytes, **changes) -> bytes:
    """`line` with fields replaced, re-serialised as canonical JSON; row_sha256 and sig are left as they were."""
    obj = json.loads(line)
    obj.update(changes)
    return (model.canonical_json(obj) + "\n").encode("utf-8")


def _rehash(line: bytes) -> bytes:
    """`line` with row_sha256 recomputed over its (edited) body; the sig is not renewed."""
    obj = json.loads(line)
    obj["row_sha256"] = model.sha256_hex(model.canonical_json({k: obj[k] for k in
                                                               ("seq", "prev_sha256", "utc", "kind", "data")}))
    return (model.canonical_json(obj) + "\n").encode("utf-8")


def _fake_signed(kind: str, data: dict) -> bytes:
    """A seq-1 owner line with a well-formed but meaningless sig: enough to reach the data checks without a key."""
    return _relined(F.signed_entry(None, 1, owner.GENESIS_PREV, kind, data), sig=_b64(bytes(64)))


def _broken(lines, pub=bytes(32), anchors=()) -> str:
    check = owner.verify_log(list(lines), pub, list(anchors))
    assert not check.ok, "expected a broken log"
    assert check.entries == () and check.head == (0, "") and check.first_key_fingerprint == "", check
    return check.reason


def _raises(fn, exc_type, text: str) -> None:
    try:
        fn()
    except exc_type as exc:
        assert text in str(exc), f"{exc_type.__name__} without {text!r}: {exc}"
        return
    raise AssertionError(f"no {exc_type.__name__} raised")


def _alert(seq: int, sha: str) -> None:
    """Append one alerts.jsonl row in the Task 14 shape (contract section 9)."""
    _home()
    row = {"utc": "2026-10-23T00:00:00Z", "channel": "toast", "result": "ok", "code": 0, "due": [], "overdue": [],
           "head_seq": seq, "head_sha256": sha, "fingerprint": "SHA256:" + "0" * 64}
    path = owner.alerts_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "ab") as fh:
        fh.write((model.canonical_json(row) + "\n").encode("utf-8"))


def _rotated_log(old, new, rotation_signer) -> list[bytes]:
    """approved (old key), key_rotated old -> new (signed by rotation_signer), cap_set (new key)."""
    one = F.signed_entry(old, 1, owner.GENESIS_PREV, "approved", {"kind": "rules", "sha256": "1" * 64})
    two = F.signed_entry(rotation_signer, 2, _row(one), "key_rotated",
                         {"old_pubkey_b64": _b64(_raw(old)), "new_pubkey_b64": _b64(_raw(new))})
    three = F.signed_entry(new, 3, _row(two), "cap_set", {"key": "okx_equity_share", "value": 0.1})
    return [one, two, three]


def _listing(root: Path) -> tuple:
    if not root.exists():
        return ()
    return tuple(sorted((p.relative_to(root).as_posix(), p.stat().st_size, p.stat().st_mtime_ns)
                        for p in root.rglob("*") if p.is_file()))


# -- paths and constants -------------------------------------------------------------------------------------------
def test_paths_are_computed_at_call_time_and_create_nothing():
    home = _home()
    assert owner.SIG_DOMAIN == b"tradegen-owner-log/1\n" and owner.GENESIS_PREV == "0" * 64
    assert owner.APPROVAL_KINDS == ("rules", "instruments", "venues", "calendar")
    assert owner.SYSTEM_KINDS == {"system_halt", "system_disarm"} and not owner.OWNER_KINDS & owner.SYSTEM_KINDS
    assert set(owner._DATA) == owner.OWNER_KINDS | owner.SYSTEM_KINDS
    assert owner.PUBKEY_PATH.resolve() == (ROOT / "core" / "compliance" / "owner_pubkey.pem").resolve()
    comp = home / "compliance"
    assert _same(owner.home(), comp) and _same(owner.log_path(), comp / "owner.jsonl")
    assert _same(owner.store_dir(), comp / "approved") and _same(owner.snapshots_dir(), comp / "snapshots")
    assert _same(owner.alerts_path(), comp / "alerts.jsonl")
    other = home / "other"
    other.mkdir()
    saved = os.environ["TRADEGEN_HOME"]
    try:
        os.environ["TRADEGEN_HOME"] = str(other)
        assert _same(owner.log_path(), other / "compliance" / "owner.jsonl")
    finally:
        os.environ["TRADEGEN_HOME"] = saved
    assert _same(owner.log_path(), comp / "owner.jsonl")
    assert owner._log_lines(owner.log_path()) == [] and owner.read_anchors() == []
    assert not comp.exists() and not (other / "compliance").exists(), \
        "computing paths and reading an absent log must create nothing"


# -- verification --------------------------------------------------------------------------------------------------
def test_valid_five_entry_log_verifies():
    key = F.test_key()
    lines = F.write_log(_home(), FIVE)
    assert owner._log_lines(owner.log_path()) == lines
    check = owner.verify_log(lines, _raw(key), [])
    assert check.ok and check.reason == "", check.reason
    assert [e.seq for e in check.entries] == [1, 2, 3, 4, 5]
    assert [e.kind for e in check.entries] == [k for k, _ in FIVE]
    assert [e.signed for e in check.entries] == [True, True, True, False, True]
    assert check.entries[4].data == FIVE[4][1] and check.entries[0].utc == "2026-10-23T00:00:00Z"
    assert check.head == (5, _row(lines[-1])) == (5, check.entries[-1].row_sha256)
    assert check.first_key_fingerprint == owner.fingerprint(_raw(key))
    assert json.loads(lines[0])["prev_sha256"] == owner.GENESIS_PREV
    assert "sig" not in json.loads(lines[3]) and "sig" in json.loads(lines[4])
    rows = [_row(x) for x in lines]
    anchored = owner.verify_log(lines, _raw(key), [(0, ""), (1, rows[0]), (2, rows[1]), (5, rows[4])])
    assert anchored.ok and anchored.head == check.head, anchored.reason
    assert _broken(lines, _raw(_key(32))) == "line 1: bad signature on approved"


def test_empty_log_is_ok_and_an_anchor_beyond_it_is_broken():
    pub = _raw(F.test_key())
    check = owner.verify_log([], pub, [(0, "")])
    assert check.ok and check.entries == () and check.head == (0, "")
    assert check.first_key_fingerprint == owner.fingerprint(pub)
    assert _broken([], pub, [(1, "a" * 64)]) == "an anchor names entry #1 but the log has 0 lines"


def test_edited_last_line_is_caught():
    key = F.test_key()
    lines = F.write_log(_home(), FIVE)
    edited = _relined(lines[-1], data={**FIVE[4][1], "address": "bc1qsomeoneelse"})
    assert _broken(lines[:-1] + [edited], _raw(key)) == "line 5: row_sha256 does not recompute"
    assert _broken(lines[:-1] + [_rehash(edited)], _raw(key)) == "line 5: bad signature on withdrawal_address"
    assert owner.verify_log(lines, _raw(key), []).ok


def test_resigned_line_with_a_wrong_prev_is_caught():
    key = F.test_key()
    lines = F.write_log(_home(), FIVE)
    kind, data = FIVE[2]
    forged = F.signed_entry(key, 3, "f" * 64, kind, data)          # a valid signature, chained to nothing
    assert _broken(lines[:2] + [forged] + lines[3:], _raw(key)) == \
        "line 3: prev_sha256 does not chain to the line before"
    skipped = F.signed_entry(key, 4, _row(lines[1]), kind, data)  # seq 3 left out
    assert _broken(lines[:2] + [skipped], _raw(key)) == "line 3: seq 4, expected 3"


def test_structure_rules_need_no_key():
    lines = _system_lines(3)
    assert owner._structure(lines)[1] == ""
    assert _broken([lines[0], lines[2]]) == "line 2: seq 3, expected 2"
    assert _broken([_rehash(_relined(lines[0], seq=True))]) == "line 1: seq True, expected 1"
    not_genesis = F.signed_entry(None, 1, "1" * 64, "system_halt", {"floor_krw": 1.0})
    assert _broken([not_genesis]) == "line 1: prev_sha256 does not chain to the line before"
    for torn in (lines[0][:-1], lines[0][:-1] + b"\r\n", lines[0] + lines[1]):
        assert _broken([torn]) == "line 1: not one newline-terminated line"
    assert _broken([lines[0], lines[1][:-1]]) == "line 2: not one newline-terminated line"
    assert _broken([b"[1,2]\n"]) == "line 1: not a JSON object"
    assert _broken([b"\xff\xfe\n"]).startswith("line 1: unreadable")
    assert _broken([DEEP]).startswith("line 1: maximum recursion depth exceeded")
    assert _broken([_relined(lines[0], kind="halt")]) == "line 1: unknown kind 'halt'"
    assert _broken([_relined(lines[0], extra="x")]).startswith("line 1: line keys")
    for utc in ("2026-10-23 00:00:00", "2026-02-30T00:00:00Z",
                "２０２６-10-23T00:00:00Z",          # fullwidth year: strptime reads it, `\d` matches it
                "٢٠٢٦-10-23T00:00:00Z"):         # Arabic-Indic year
        assert _broken([_relined(lines[0], utc=utc)]).startswith("line 1: utc")


def test_unsigned_owner_entry_and_signed_system_entry_are_caught():
    unsigned = F.signed_entry(None, 1, owner.GENESIS_PREV, "cap_set", {"key": "okx_equity_share", "value": 0.5})
    assert _broken([unsigned]).startswith("line 1: unsigned cap_set entry")
    signed_halt = _relined(_system_lines(1)[0], sig=_b64(bytes(64)))
    assert _broken([signed_halt]) == "line 1: signature on a system entry (system_halt)"
    assert _broken([_relined(unsigned, sig="not base64!")]) == "line 1: sig is not base64 of 64 bytes"


def test_non_canonical_json_is_caught():
    line = _system_lines(1)[0]
    spaced = line.replace(b'","', b'", "', 1)
    assert spaced != line and json.loads(spaced) == json.loads(line)
    assert _broken([spaced]) == "line 1: not its canonical JSON"
    escaped = _system_lines(1)[0].replace(b"system_halt", b"system\\u005fhalt")
    assert json.loads(escaped) == json.loads(line)
    assert _broken([escaped]) == "line 1: not its canonical JSON"


def test_duplicate_json_keys_are_caught():
    line = _system_lines(1)[0]
    assert line.startswith(b'{"data":')
    assert _broken([b'{"seq":1,' + line[1:]]) == "line 1: unreadable (duplicate key 'seq')"


# -- anchors (unsigned system lines: the anchor checks come before any signature) ----------------------------------
def test_deleted_system_halt_is_caught_by_an_alerts_anchor():
    _home()
    lines = _system_lines(4)
    _alert(4, _row(lines[-1]))
    anchors = owner.read_anchors()
    assert anchors == [(4, _row(lines[-1]))]
    assert _broken(lines[:3], anchors=anchors) == "an anchor names entry #4 but the log has 3 lines"


def test_snapshot_and_store_anchors_are_read_and_a_mismatch_is_caught():
    _home()
    lines = _system_lines(5)
    rows = [_row(x) for x in lines]
    snaps, store = owner.snapshots_dir(), owner.store_dir() / "rules"
    snaps.mkdir(parents=True)
    store.mkdir(parents=True)
    (snaps / "00000002-0123456789abcdef.json").write_bytes(
        model.canonical_json({"head": [2, rows[1]], "state": {}}).encode("utf-8"))
    (store / ("1" * 64 + ".anchor.json")).write_bytes(
        model.canonical_json({"seq": 1, "row_sha256": rows[0]}).encode("utf-8"))
    _alert(0, "")                                               # an empty log's head anchors nothing
    _alert(5, rows[4])
    anchors = owner.read_anchors()
    assert anchors == [(0, ""), (1, rows[0]), (2, rows[1]), (5, rows[4])]
    assert _broken(lines[:4], anchors=anchors) == "an anchor names entry #5 but the log has 4 lines"
    (snaps / "00000003-fedcba9876543210.json").write_bytes(
        model.canonical_json({"head": [3, "e" * 64]}).encode("utf-8"))
    assert _broken(lines, anchors=owner.read_anchors()) == "line 3: row_sha256 differs from its anchor"


def test_an_unreadable_anchor_fails_closed():
    _home()
    path = owner.alerts_path()
    path.parent.mkdir(parents=True)
    for row in (b'{"head_seq":1,"head_sha256":"zz"}', b'{"head_seq":0,"head_sha256":"zz"}',
                b'{"head_seq":null,"head_sha256":null}', b'{"head_seq":true,"head_sha256":"' + b"a" * 64 + b'"}'):
        path.write_bytes(row + b"\n")
        _raises(owner.read_anchors, ValueError, "alerts.jsonl: not an anchor")
    path.write_bytes(b"{torn\n")
    _raises(owner.read_anchors, ValueError, "alerts.jsonl line 1: unreadable")
    path.write_bytes(DEEP)
    _raises(owner.read_anchors, ValueError, "alerts.jsonl line 1: unreadable")
    path.unlink()
    snap = owner.snapshots_dir() / "00000001-0000000000000000.json"
    snap.parent.mkdir(parents=True)
    snap.write_bytes(b'{"state":{}}')
    _raises(owner.read_anchors, ValueError, "no head anchor")
    snap.unlink()
    snap.mkdir()                                                # a file that cannot be read: OSError, also BROKEN
    _raises(owner.read_anchors, OSError, "")


# -- key rotation (P20) --------------------------------------------------------------------------------------------
def test_rotation_signed_by_the_old_key_verifies_and_moves_the_first_key():
    old, new, newest = F.test_key(), _key(32), _key(64)
    lines = _rotated_log(old, new, rotation_signer=old)
    check = owner.verify_log(lines, _raw(new), [])
    assert check.ok, check.reason
    assert [e.kind for e in check.entries] == ["approved", "key_rotated", "cap_set"]
    assert check.first_key_fingerprint == owner.fingerprint(_raw(old)) != owner.fingerprint(_raw(new))
    assert _broken(lines, _raw(old)).startswith("line 2: key_rotated does not lead")    # pem left on the old key
    late = F.signed_entry(old, 4, check.head[1], "cap_set", {"key": "okx_equity_share", "value": 0.05})
    assert _broken(lines + [late], _raw(new)) == "line 4: bad signature on cap_set"   # the old key is retired
    second = F.signed_entry(new, 4, check.head[1], "key_rotated",
                            {"old_pubkey_b64": _b64(_raw(new)), "new_pubkey_b64": _b64(_raw(newest))})
    twice = owner.verify_log(lines + [second], _raw(newest), [])
    assert twice.ok and twice.first_key_fingerprint == owner.fingerprint(_raw(old)), twice.reason
    wrong_old = F.signed_entry(new, 4, check.head[1], "key_rotated",
                               {"old_pubkey_b64": _b64(_raw(old)), "new_pubkey_b64": _b64(_raw(newest))})
    assert _broken(lines + [wrong_old], _raw(newest)).startswith("line 2: key_rotated does not lead")


def test_rotation_signed_by_the_new_key_fails():
    old, new = F.test_key(), _key(32)
    lines = _rotated_log(old, new, rotation_signer=new)
    assert _broken(lines, _raw(new)) == "line 2: bad signature on key_rotated"


def test_read_pubkey_round_trips_and_refuses_other_keys():
    key = F.test_key()
    pem = _home() / "owner_pubkey.pem"
    F.write_pubkey(pem)
    assert pem.read_bytes().startswith(b"-----BEGIN PUBLIC KEY-----")
    assert owner.read_pubkey(pem) == _raw(key)
    assert owner.fingerprint(_raw(key)) == "SHA256:" + hashlib.sha256(_raw(key)).hexdigest()
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
    pem.write_bytes(X25519PrivateKey.from_private_bytes(bytes(32)).public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo))
    _raises(lambda: owner.read_pubkey(pem), ValueError, "not an Ed25519 public key")
    pem.write_bytes(b"-----BEGIN PUBLIC KEY-----\nAAAA\n-----END PUBLIC KEY-----\n")
    _raises(lambda: owner.read_pubkey(pem), ValueError, "")
    _raises(lambda: owner.read_pubkey(_home() / "absent.pem"), FileNotFoundError, "")


def _spki_pem(oid: bytes) -> bytes:
    """A well-formed PEM SubjectPublicKeyInfo naming the algorithm `oid` (DER content bytes) with a 32-byte key."""
    def der(tag: int, body: bytes) -> bytes:
        return bytes([tag, len(body)]) + body                   # every length here is under 128
    spki = der(0x30, der(0x30, der(0x06, oid)) + der(0x03, b"\x00" + bytes(range(32))))
    return b"-----BEGIN PUBLIC KEY-----\n" + base64.b64encode(spki) + b"\n-----END PUBLIC KEY-----\n"


def test_read_pubkey_turns_an_unsupported_key_type_into_a_value_error():
    F.test_key()                                                # NotRun PENDING while cryptography is missing
    pem = _home() / "owner_pubkey.pem"
    pem.write_bytes(_spki_pem(bytes([0x2B, 0xCE, 0x0F, 0x01])))  # OID 1.3.9999.1: well-formed, no such algorithm
    _raises(lambda: owner.read_pubkey(pem), ValueError, "not an Ed25519 public key")
    pem.unlink()
    pem.mkdir()                                                 # not a file: an OSError escapes, also a broken log
    _raises(lambda: owner.read_pubkey(pem), OSError, "")


# -- event data --------------------------------------------------------------------------------------------------
def test_event_data_schemas_are_exact():
    tagged = {"venue": "upbit", "symbol": "XRP", "network": "ripple", "address": "rTEST", "tag": "12345",
              "evidence": "Upbit deposit-address screen"}
    good = {
        "approved": {"kind": "calendar", "sha256": "2" * 64},
        "code_approved": {"sha256": model.sha256_hex(model.canonical_json(FILES)), "files": FILES},
        "course_completed": {"course": "kofia_leveraged_1h", "evidence": "KOFIA certificate 2026-10-20"},
        "broker_approval": {"item": "broker_eligibility", "evidence": "KIS app screen"},
        "age_of_majority": {"birth_date": "2005-03-01", "evidence": "resident card"},
        "cap_set": {"key": "okx_equity_share", "value": 1},
        "limit_set": {"total_loss_floor_krw": 0, "daily_loss_krw": 5000.0},
        "withdrawal_address": tagged,
        "session_armed": {"session_id": "S1"},
        "session_ack": {"session_id": "S1", "row_id": "KR-OKX-SPOT", "warning_sha256": "3" * 64},
        "transfer_ack": {"intent_hash": "4" * 64, "warning_sha256": "5" * 64},
        "key_rotated": {"old_pubkey_b64": _b64(bytes(32)), "new_pubkey_b64": _b64(bytes(range(32)))},
        "system_halt": {"floor_krw": 21000},
        "system_disarm": {"session_id": "S1", "reason": "daily loss limit"},
    }
    assert set(good) == owner.OWNER_KINDS | owner.SYSTEM_KINDS
    for kind, data in good.items():
        assert owner._data_problem(kind, data) == "", (kind, owner._data_problem(kind, data))
    assert owner._data_problem("withdrawal_address", {**tagged, "tag": None}) == ""
    bad = [
        ("approved", {"kind": "rules"}),
        ("approved", {"kind": "rules", "sha256": "1" * 64, "note": "x"}),
        ("approved", {"kind": "code", "sha256": "1" * 64}),
        ("approved", {"kind": "rules", "sha256": "A" * 64}),
        ("code_approved", {"sha256": "6" * 64, "files": FILES}),
        ("code_approved", {"sha256": model.sha256_hex(model.canonical_json(FILES[::-1])), "files": FILES[::-1]}),
        ("code_approved", {"sha256": model.sha256_hex(model.canonical_json([])), "files": []}),
        ("course_completed", {"course": "age_of_majority", "evidence": "x"}),
        ("course_completed", {"course": "kofia_leveraged_1h", "evidence": " "}),
        ("broker_approval", {"item": ["broker_eligibility"], "evidence": "x"}),
        ("age_of_majority", {"birth_date": "2005-02-30", "evidence": "x"}),
        ("age_of_majority", {"birth_date": "２００５-03-01", "evidence": "x"}),
        ("age_of_majority", {"birth_date": "٢٠٠٥-03-01", "evidence": "x"}),
        ("cap_set", {"key": "okx_equity_share", "value": 0}),
        ("cap_set", {"key": "okx_equity_share", "value": 1.5}),
        ("cap_set", {"key": "okx_equity_share", "value": True}),
        ("cap_set", {"key": "binance_share", "value": 0.1}),
        ("limit_set", {"total_loss_floor_krw": -1, "daily_loss_krw": 5000}),
        ("limit_set", {"total_loss_floor_krw": 21000, "daily_loss_krw": 0}),
        ("withdrawal_address", {**tagged, "tag": ""}),
        ("withdrawal_address", {**tagged, "venue": "nowhere"}),
        ("session_ack", {"session_id": "S1", "row_id": "KR-OKX-SPOT", "warning_sha256": "x"}),
        ("key_rotated", {"new_pubkey_b64": _b64(bytes(32))}),
        ("key_rotated", {"old_pubkey_b64": _b64(bytes(31)), "new_pubkey_b64": _b64(bytes(32))}),
        ("system_halt", {"floor_krw": float("nan")}),
        ("system_halt", {"floor_krw": 10 ** 400}),                 # an int too large for a float
        ("system_disarm", {"session_id": "", "reason": "x"}),
        ("system_disarm", ["S1", "x"]),
    ]
    for kind, data in bad:
        assert owner._data_problem(kind, data) != "", (kind, data)
    assert _broken([_fake_signed("approved", {"kind": "rules"})]).startswith("line 1: approved data keys")
    assert _broken([_fake_signed("cap_set", {"key": "okx_equity_share", "value": 1.5})]) == \
        "line 1: cap_set data has invalid value"
    for floor in (-5, 10 ** 400):
        assert _broken([F.signed_entry(None, 1, owner.GENESIS_PREV, "system_halt", {"floor_krw": floor})]) == \
            "line 1: system_halt data has invalid floor_krw"


# -- failure modes ------------------------------------------------------------------------------------------------
def test_missing_cryptography_means_a_broken_log():
    pem = _home() / "owner_pubkey.pem"
    pem.write_bytes(b"-----BEGIN PUBLIC KEY-----\nAAAA\n-----END PUBLIC KEY-----\n")
    names = [k for k in sys.modules if k == "cryptography" or k.startswith("cryptography.")]
    saved = {k: sys.modules[k] for k in names}
    try:
        for k in names:
            sys.modules[k] = None
        sys.modules["cryptography"] = None
        assert importlib.util.find_spec("cryptography") is None, "how test_key() (tests only) sees a missing package"
        try:
            import cryptography.hazmat.primitives.asymmetric.ed25519  # noqa: F401
        except ImportError:
            pass                                                # the lazy probe core/ uses (Tasks 13 and 14)
        else:
            raise AssertionError("the lazy cryptography import did not fail")
        assert _broken([]) == "cryptography missing: install it (Task 10)"
        assert _broken(_system_lines(2)) == "cryptography missing: install it (Task 10)"
        _raises(lambda: owner.read_pubkey(pem), ImportError, "")
    finally:
        for k in [k for k in sys.modules if k == "cryptography" or k.startswith("cryptography.")]:
            del sys.modules[k]
        sys.modules.update(saved)


def test_verify_log_never_raises_on_garbage():
    rng = random.Random(11)
    real = _system_lines(3)
    for i in range(300):
        if i % 2:
            lines = [bytes(rng.randrange(256) for _ in range(rng.randrange(40))) for _ in range(rng.randrange(4))]
        else:
            lines = [bytearray(x) for x in real]
            row = rng.randrange(3)
            lines[row][rng.randrange(len(lines[row]))] = rng.randrange(256)
            lines = [bytes(x) for x in lines]
        pub = rng.choice([bytes(32), b"", None, "x" * 32, bytes(33)])
        anchors = rng.choice([[], [(1, "a" * 64)], [("x", None)], None, [(2.5, 1)]])
        check = owner.verify_log(rng.choice([lines, None, "text", [None]]), pub, anchors)
        assert isinstance(check, owner.LogCheck)
        assert check.ok or (check.entries == () and check.head == (0, ""))


# -- appending system entries --------------------------------------------------------------------------------------
def test_append_system_entry_appends_the_next_seq_unsigned():
    key = F.test_key()
    lines = F.write_log(_home(), FIVE[:2])
    seq, row = owner.append_system_entry("system_halt", {"floor_krw": 21000.0}, NOW)
    after = owner._log_lines(owner.log_path())
    assert seq == 3 and len(after) == 3 and after[:2] == lines
    obj = json.loads(after[2])
    assert obj["seq"] == 3 and obj["prev_sha256"] == _row(lines[1]) and obj["row_sha256"] == row
    assert "sig" not in obj and obj["utc"] == "2026-10-23T01:02:03Z" and obj["data"] == {"floor_krw": 21000.0}
    assert Path(str(owner.log_path()) + ".lock").is_file(), "the sidecar lock file was not created"
    check = owner.verify_log(after, _raw(key), [(3, row)])
    assert check.ok and check.head == (3, row), check.reason


def test_append_waits_for_a_sidecar_lock_held_elsewhere():
    _home()
    path = owner.log_path()
    path.parent.mkdir(parents=True)
    done = []
    with open(str(path) + ".lock", "a+b") as fh:          # a second handle, as another process would hold it
        if os.name == "nt":
            import msvcrt
            fh.seek(0)
            msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
        t = threading.Thread(target=lambda: done.append(
            owner.append_system_entry("system_halt", {"floor_krw": 1.0}, NOW)))
        t.start()
        t.join(0.5)
        waited = t.is_alive() and not path.exists()
        if os.name == "nt":
            fh.seek(0)
            msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            fcntl.flock(fh, fcntl.LOCK_UN)
    t.join(15)
    assert waited, "append_system_entry wrote while another handle held the sidecar lock"
    assert not t.is_alive() and [s for s, _ in done] == [1], done


def test_concurrent_system_entries_chain_under_the_lock():
    _home()
    errors = []

    def one(i: int) -> None:
        try:
            owner.append_system_entry("system_disarm", {"session_id": f"S{i}", "reason": "test"}, NOW)
        except Exception as exc:                                # collected and asserted below
            errors.append(exc)

    threads = [threading.Thread(target=one, args=(i,)) for i in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert errors == [], errors
    lines = owner._log_lines(owner.log_path())
    assert owner._structure(lines)[1] == "" and len(lines) == 8
    objs = [json.loads(x) for x in lines]
    assert [o["seq"] for o in objs] == list(range(1, 9))
    assert sorted(o["data"]["session_id"] for o in objs) == sorted(f"S{i}" for i in range(8))


def test_append_system_entry_refuses_owner_kinds_bad_data_naive_time_and_a_broken_chain():
    _home()
    _raises(lambda: owner.append_system_entry("cap_set", {"key": "okx_equity_share", "value": 0.5}, NOW),
            ValueError, "not a system kind")
    _raises(lambda: owner.append_system_entry("system_halt", {"floor_krw": -1.0}, NOW), ValueError,
            "invalid floor_krw")
    _raises(lambda: owner.append_system_entry("system_halt", {"floor_krw": 10 ** 400}, NOW), ValueError,
            "invalid floor_krw")
    _raises(lambda: owner.append_system_entry("system_halt", {"floor_krw": 1.0, "x": 1}, NOW), ValueError, "keys")
    _raises(lambda: owner.append_system_entry("system_halt", {"floor_krw": 1.0}, datetime(2026, 10, 23, 1, 2, 3)),
            ValueError, "")
    assert not owner.home().exists(), "a refused append must create nothing"
    lines = _system_lines(2)
    path = owner.log_path()
    path.parent.mkdir(parents=True)
    path.write_bytes(lines[0] + lines[1][:-1])                  # a torn last line
    before = path.read_bytes()
    _raises(lambda: owner.append_system_entry("system_halt", {"floor_krw": 1.0}, NOW), RuntimeError,
            "owner log is broken (line 2: not one newline-terminated line)")
    assert path.read_bytes() == before


def test_append_refuses_a_hard_linked_log_or_lock():
    home = _home()
    path = owner.log_path()             # the state-root link scan runs here, on a clean root, and is memoised
    path.parent.mkdir(parents=True)
    path.write_bytes(_system_lines(1)[0])
    before = path.read_bytes()
    os.link(path, home / "victim.jsonl")                        # checked_target judges the link count, not the place
    _raises(lambda: owner.append_system_entry("system_halt", {"floor_krw": 1.0}, NOW), RuntimeError,
            "is a hard link")
    assert path.read_bytes() == before == (home / "victim.jsonl").read_bytes()
    (home / "victim.jsonl").unlink()
    lock = Path(str(path) + ".lock")
    assert lock.is_file()
    os.link(lock, home / "victim.lock")
    _raises(lambda: owner.append_system_entry("system_halt", {"floor_krw": 1.0}, NOW), RuntimeError,
            "is a hard link")
    assert path.read_bytes() == before


def test_no_line_is_written_outside_the_temp_home():
    home = _home()
    real = Path.home() / ".tradegen" / "compliance"
    before = _listing(real)
    owner.append_system_entry("system_halt", {"floor_krw": 21000.0}, NOW)
    owner.append_system_entry("system_disarm", {"session_id": "S1", "reason": "test"}, NOW)
    written = sorted(p.relative_to(home).as_posix() for p in home.rglob("*"))
    assert written == ["compliance", "compliance/owner.jsonl", "compliance/owner.jsonl.lock"], written
    assert _listing(real) == before


# --------------------------------------------------------------------------- #
# Task 12: owner state with D12, and the approvals in force. Pure: hand-built LogChecks, no key, no file.
# --------------------------------------------------------------------------- #
import datetime as _dt  # noqa: E402

from core.compliance import model, owner  # noqa: E402

_HA, _HB, _HC = "a" * 64, "b" * 64, "c" * 64


def _state_kst(y: int, m: int, d: int, hh: int = 12, mm: int = 0, ss: int = 0) -> _dt.datetime:
    return _dt.datetime(y, m, d, hh, mm, ss, tzinfo=model.KST)


def _state_stamp(at: _dt.datetime) -> str:
    return at.astimezone(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _state_log(*rows, first_fp: str = "SHA256:first") -> owner.LogCheck:
    """A LogCheck that passed verification, over (kind, data, Asia/Seoul moment) rows numbered from seq 1."""
    entries = tuple(owner.Entry(seq=n, utc=_state_stamp(at), kind=kind, data=data, row_sha256=f"{n:064x}",
                                signed=kind not in owner.SYSTEM_KINDS)
                    for n, (kind, data, at) in enumerate(rows, start=1))
    head = (len(entries), entries[-1].row_sha256) if entries else (0, "")
    return owner.LogCheck(ok=True, reason="", entries=entries, head=head, first_key_fingerprint=first_fp)


def _state_at(check: owner.LogCheck, at: _dt.datetime, *, session_id=None, first_recorded=None):
    return owner.owner_state(check, date=at.date(), now_utc=_state_stamp(at), session_id=session_id,
                             fingerprint_now="SHA256:now", first_recorded=first_recorded)


def _state_cap(value: float, at: _dt.datetime):
    return ("cap_set", {"key": "okx_equity_share", "value": value}, at)


def _state_limits(floor: float, daily: float, at: _dt.datetime):
    return ("limit_set", {"total_loss_floor_krw": floor, "daily_loss_krw": daily}, at)


def _state_approved(kind: str, sha: str, at: _dt.datetime):
    return ("approved", {"kind": kind, "sha256": sha}, at)


def test_state_in_force_takes_the_latest_approval_per_kind():
    check = _state_log(_state_approved("rules", _HA, _state_kst(2026, 10, 1)),
                       _state_approved("rules", _HB, _state_kst(2026, 10, 2)),
                       _state_approved("instruments", _HC, _state_kst(2026, 10, 3)))
    assert owner.in_force(check) == {"rules": (_HB, 2), "instruments": (_HC, 3)}
    assert owner.history(check, "rules") == [(_HA, 1)], "the older hash is history only"
    assert owner.history(check, "instruments") == [] and owner.history(check, "venues") == []


def test_state_superseded_hash_counts_only_when_signed_again():
    rows = [_state_approved("rules", _HA, _state_kst(2026, 10, 1)),
            _state_approved("rules", _HB, _state_kst(2026, 10, 2))]
    assert owner.in_force(_state_log(*rows))["rules"] == (_HB, 2)
    again = _state_log(*rows, _state_approved("rules", _HA, _state_kst(2026, 10, 3)))
    assert owner.in_force(again)["rules"] == (_HA, 3), "a new signed entry puts the old hash back in force"
    assert owner.history(again, "rules") == [(_HB, 2), (_HA, 1)]


def test_state_code_approval_is_the_latest():
    assert owner.code_approval(_state_log()) is None
    check = _state_log(("code_approved", {"sha256": _HA, "files": [["core/x.py", _HB]]}, _state_kst(2026, 10, 1)),
                       ("code_approved", {"sha256": _HC, "files": [["core/x.py", _HA]]}, _state_kst(2026, 10, 2)))
    assert owner.code_approval(check) == _HC


def test_state_broken_check_means_no_owner_state():
    signed = _state_log(_state_approved("rules", _HA, _state_kst(2026, 10, 1)),
                        _state_approved("rules", _HB, _state_kst(2026, 10, 2)),
                        ("code_approved", {"sha256": _HC, "files": [["core/x.py", _HA]]}, _state_kst(2026, 10, 3)),
                        _state_cap(0.10, _state_kst(2026, 10, 4)))
    broken = owner.LogCheck(ok=False, reason="line 3: bad signature on cap_set", entries=signed.entries,
                            head=signed.head, first_key_fingerprint="")
    state = _state_at(broken, _state_kst(2026, 10, 24))
    assert state.status == "BROKEN" and not state.ok and state.reason == "line 3: bad signature on cap_set"
    assert state.caps == {} and state.flags == frozenset() and state.fingerprint == "SHA256:now"
    assert owner.in_force(broken) == {}, "a broken log's entries count for nothing"
    assert owner.history(broken, "rules") == [] and owner.code_approval(broken) is None


def test_state_cap_tightens_at_once():
    check = _state_log(_state_cap(0.20, _state_kst(2026, 10, 20, 10)), _state_cap(0.10, _state_kst(2026, 10, 24, 10)))
    assert _state_at(check, _state_kst(2026, 10, 20, 11)).caps == {}, "unset is the tightest: setting one waits"
    assert _state_at(check, _state_kst(2026, 10, 21, 0)).caps == {"okx_equity_share": 0.10}, "stamped ahead, applies"
    assert _state_at(check, _state_kst(2026, 10, 24, 9)).caps == {"okx_equity_share": 0.10}, "not stamped yet"
    assert _state_at(check, _state_kst(2026, 10, 24, 10)).caps == {"okx_equity_share": 0.10}, "stamped this second"
    first = _state_log(_state_cap(0.20, _state_kst(2026, 10, 20, 10)))
    assert _state_at(first, _state_kst(2026, 10, 21, 0)).caps == {"okx_equity_share": 0.20}, "alone, it applies next day"


def test_state_cap_loosens_from_the_next_asia_seoul_date():
    loosen = _state_kst(2026, 10, 24, 0, 30)
    assert _state_stamp(loosen) == "2026-10-23T15:30:00Z", "still 23 October in UTC"
    check = _state_log(_state_cap(0.10, _state_kst(2026, 10, 20)), _state_cap(0.30, loosen))
    assert _state_at(check, _state_kst(2026, 10, 24, 12)).caps == {"okx_equity_share": 0.10}
    assert _state_at(check, _state_kst(2026, 10, 24, 23, 59, 59)).caps == {"okx_equity_share": 0.10}
    assert _state_at(check, _state_kst(2026, 10, 25, 0, 0, 0)).caps == {"okx_equity_share": 0.30}


def test_state_loosening_waits_while_the_session_is_armed():
    rows = [_state_cap(0.10, _state_kst(2026, 10, 20)),
            ("session_armed", {"session_id": "S1"}, _state_kst(2026, 10, 22, 10)),
            _state_cap(0.30, _state_kst(2026, 10, 22, 12)),
            ("session_armed", {"session_id": "S2"}, _state_kst(2026, 10, 22, 13)),
            ("session_armed", {"session_id": "S3"}, _state_kst(2026, 10, 23, 10))]
    check, at = _state_log(*rows), _state_kst(2026, 10, 24)
    assert _state_at(check, at).armed_sessions == {"S1", "S2", "S3"}
    assert _state_at(check, at, session_id="S1").caps == {"okx_equity_share": 0.10}, "armed before it"
    assert _state_at(check, at, session_id="S2").caps == {"okx_equity_share": 0.10}, "armed on its date"
    assert _state_at(check, at, session_id="S3").caps == {"okx_equity_share": 0.30}, "armed after it took effect"
    assert _state_at(check, at).caps == {"okx_equity_share": 0.30}, "no session: the loosening counts"
    disarmed = _state_log(*rows, ("system_disarm", {"session_id": "S1", "reason": "session end"},
                                  _state_kst(2026, 10, 23, 12)))
    assert _state_at(disarmed, at, session_id="S1").caps == {"okx_equity_share": 0.30}
    rearmed = _state_log(*rows, ("session_armed", {"session_id": "S1"}, _state_kst(2026, 10, 23, 11)))
    assert _state_at(rearmed, at, session_id="S1").caps == {"okx_equity_share": 0.10}, "still armed from 22 October"


def test_state_no_loosening_after_a_halt():
    check = _state_log(_state_limits(21_000.0, 5_000.0, _state_kst(2026, 10, 10)),
                       _state_cap(0.10, _state_kst(2026, 10, 10)),
                       _state_cap(0.20, _state_kst(2026, 10, 12)),
                       _state_cap(0.30, _state_kst(2026, 10, 14, 10)),
                       ("system_halt", {"floor_krw": 21_000.0}, _state_kst(2026, 10, 14, 20)),
                       _state_limits(10_000.0, 5_000.0, _state_kst(2026, 10, 16)),
                       _state_cap(0.40, _state_kst(2026, 10, 16)))
    state = _state_at(check, _state_kst(2026, 10, 24))
    assert state.halted_floors == {21_000.0}
    assert state.limits == {"total_loss_floor_krw": 21_000.0, "daily_loss_krw": 5_000.0}, "the floor stays"
    assert state.caps == {"okx_equity_share": 0.20}, "0.20 took effect before the halt; 0.30 and 0.40 never do"
    tighter = _state_log(_state_limits(21_000.0, 5_000.0, _state_kst(2026, 10, 10)),
                         ("system_halt", {"floor_krw": 21_000.0}, _state_kst(2026, 10, 14)),
                         _state_limits(30_000.0, 4_000.0, _state_kst(2026, 10, 24, 9)))
    assert _state_at(tighter, _state_kst(2026, 10, 24, 10)).limits == {
        "total_loss_floor_krw": 30_000.0, "daily_loss_krw": 4_000.0}, "a tightening still applies at once"


def test_state_floor_loosening_below_a_halted_floor_is_ignored():
    check = _state_log(_state_limits(21_000.0, 5_000.0, _state_kst(2026, 10, 10)),
                       _state_limits(15_000.0, 5_000.0, _state_kst(2026, 10, 12)),     # in effect from 13 October
                       ("system_halt", {"floor_krw": 21_000.0}, _state_kst(2026, 10, 14)))
    assert _state_at(check, _state_kst(2026, 10, 13)).limits["total_loss_floor_krw"] == 21_000.0, "the halt is ahead"
    no_halt = _state_log(_state_limits(21_000.0, 5_000.0, _state_kst(2026, 10, 10)),
                         _state_limits(15_000.0, 5_000.0, _state_kst(2026, 10, 12)))
    assert _state_at(no_halt, _state_kst(2026, 10, 13)).limits["total_loss_floor_krw"] == 15_000.0
    assert _state_at(check, _state_kst(2026, 10, 24)).limits["total_loss_floor_krw"] == 21_000.0, "for good"
    twice = _state_log(_state_limits(21_000.0, 5_000.0, _state_kst(2026, 10, 1)),
                       ("system_halt", {"floor_krw": 21_000.0}, _state_kst(2026, 10, 5)),
                       _state_limits(30_000.0, 5_000.0, _state_kst(2026, 10, 6)),
                       ("system_halt", {"floor_krw": 30_000.0}, _state_kst(2026, 10, 8)))
    assert _state_at(twice, _state_kst(2026, 10, 24)).limits == {
        "total_loss_floor_krw": 30_000.0, "daily_loss_krw": 5_000.0}, "a second halt keeps the tightened floor"
    only_halt = _state_log(("system_halt", {"floor_krw": 21_000.0}, _state_kst(2026, 10, 5)))
    assert _state_at(only_halt, _state_kst(2026, 10, 24)).limits == {}, "an unset floor stays unset, the tightest"


def test_state_daily_loss_tightens_and_loosens():
    check = _state_log(_state_limits(21_000.0, 5_000.0, _state_kst(2026, 10, 10)),
                       _state_limits(21_000.0, 3_000.0, _state_kst(2026, 10, 24, 10)),
                       _state_limits(21_000.0, 8_000.0, _state_kst(2026, 10, 24, 12)),
                       _state_limits(25_000.0, 9_000.0, _state_kst(2026, 10, 25, 10)))
    assert _state_at(check, _state_kst(2026, 10, 24, 11)).limits["daily_loss_krw"] == 3_000.0
    assert _state_at(check, _state_kst(2026, 10, 24, 13)).limits["daily_loss_krw"] == 3_000.0
    assert _state_at(check, _state_kst(2026, 10, 25, 9)).limits["daily_loss_krw"] == 8_000.0
    assert _state_at(check, _state_kst(2026, 10, 25, 11)).limits == {
        "total_loss_floor_krw": 25_000.0, "daily_loss_krw": 8_000.0}, "the floor rises now, the daily loss tomorrow"
    assert _state_at(check, _state_kst(2026, 10, 26)).limits == {
        "total_loss_floor_krw": 25_000.0, "daily_loss_krw": 9_000.0}


def test_state_age_of_majority_at_19():
    check = _state_log(("age_of_majority", {"birth_date": "2007-10-24", "evidence": "id card"},
                        _state_kst(2026, 10, 1)))
    assert "age_of_majority" not in _state_at(check, _state_kst(2026, 10, 23, 23, 59, 59)).flags
    assert "age_of_majority" in _state_at(check, _state_kst(2026, 10, 24, 0, 0, 0)).flags
    leap = _state_log(("age_of_majority", {"birth_date": "2008-02-29", "evidence": "id card"},
                       _state_kst(2026, 10, 1)))
    assert "age_of_majority" not in _state_at(leap, _state_kst(2027, 2, 28)).flags
    assert "age_of_majority" in _state_at(leap, _state_kst(2027, 3, 1)).flags
    corrected = _state_log(("age_of_majority", {"birth_date": "2000-01-01", "evidence": "typo"},
                            _state_kst(2026, 10, 1)),
                           ("age_of_majority", {"birth_date": "2008-05-01", "evidence": "id card"},
                            _state_kst(2026, 10, 2)))
    assert "age_of_majority" not in _state_at(corrected, _state_kst(2026, 10, 24)).flags, "the latest entry wins"


def test_state_course_and_broker_flags():
    check = _state_log(("course_completed", {"course": "kofia_leveraged_1h", "evidence": "certificate"},
                        _state_kst(2026, 10, 1)),
                       ("broker_approval", {"item": "broker_eligibility", "evidence": "broker letter"},
                        _state_kst(2026, 10, 2)))
    assert _state_at(check, _state_kst(2026, 10, 24)).flags == {"kofia_leveraged_1h", "broker_eligibility"}


def test_state_sessions_armed_until_disarmed():
    rows = [("session_armed", {"session_id": "S1"}, _state_kst(2026, 10, 20)),
            ("session_armed", {"session_id": "S2"}, _state_kst(2026, 10, 21)),
            ("system_disarm", {"session_id": "S1", "reason": "kill switch"}, _state_kst(2026, 10, 22))]
    assert _state_at(_state_log(*rows), _state_kst(2026, 10, 24)).armed_sessions == {"S2"}
    rearmed = _state_log(*rows, ("session_armed", {"session_id": "S1"}, _state_kst(2026, 10, 23)))
    assert _state_at(rearmed, _state_kst(2026, 10, 24)).armed_sessions == {"S1", "S2"}


def test_state_acks_collected():
    check = _state_log(("session_ack", {"session_id": "S1", "row_id": "KR-OKX-SPOT", "warning_sha256": _HA},
                        _state_kst(2026, 10, 20)),
                       ("transfer_ack", {"intent_hash": _HB, "warning_sha256": _HC}, _state_kst(2026, 10, 21)))
    state = _state_at(check, _state_kst(2026, 10, 24))
    assert state.session_acks == {("S1", "KR-OKX-SPOT", _HA)} and state.transfer_acks == {(_HB, _HC)}


def test_state_addresses_use_an_empty_tag_for_null():
    check = _state_log(("withdrawal_address", {"venue": "upbit", "symbol": "BTC", "network": "bitcoin",
                                               "address": "bc1qtestaddress", "tag": None, "evidence": "screenshot"},
                        _state_kst(2026, 10, 20)),
                       ("withdrawal_address", {"venue": "upbit", "symbol": "XRP", "network": "xrp",
                                               "address": "rTestAddress", "tag": "12345", "evidence": "screenshot"},
                        _state_kst(2026, 10, 21)))
    assert _state_at(check, _state_kst(2026, 10, 24)).addresses == {
        ("upbit", "BTC", "bitcoin", "bc1qtestaddress", ""), ("upbit", "XRP", "xrp", "rTestAddress", "12345")}


def test_state_key_changed_since_first_recorded():
    check = _state_log(_state_cap(0.10, _state_kst(2026, 10, 1)), first_fp="SHA256:first")
    at = _state_kst(2026, 10, 24)
    changed = _state_at(check, at, first_recorded=("SHA256:other", "2026-10-20T00:00:00Z"))
    assert changed.status == "BROKEN" and changed.reason == "KEY CHANGED since 2026-10-20" and changed.caps == {}
    undated = _state_at(check, at, first_recorded=("SHA256:other", ""))
    assert undated.reason == "KEY CHANGED since an unknown date", undated.reason
    same = _state_at(check, at, first_recorded=("SHA256:first", "2026-10-20T00:00:00Z"))
    assert same.ok and same.caps == {"okx_equity_share": 0.10}
    assert _state_at(check, at).ok, "nothing recorded yet: nothing to compare"


def test_state_future_entries_ignored():
    at = _state_kst(2026, 10, 24)
    check = _state_log(_state_cap(0.20, _state_kst(2026, 10, 20)), _state_cap(0.50, _state_kst(2026, 10, 25)),
                       ("course_completed", {"course": "short_course_30m", "evidence": "certificate"},
                        _state_kst(2026, 10, 25)),
                       _state_approved("rules", _HA, _state_kst(2026, 10, 25)))
    state = _state_at(check, at)
    assert state.caps == {"okx_equity_share": 0.20} and "short_course_30m" not in state.flags
    assert state.head == check.head, "the head is still the last line"
    assert owner.in_force(owner._up_to(check, _state_stamp(at))) == {}, "load_context filters approvals the same way"


def test_state_unreadable_entry_data_is_broken():
    check = _state_log(("age_of_majority", {"birth_date": "2007/10/24", "evidence": "id card"},
                        _state_kst(2026, 10, 1)))
    state = _state_at(check, _state_kst(2026, 10, 24))
    assert state.status == "BROKEN" and state.reason.startswith("owner log: unreadable entry data"), state.reason


def test_state_backdated_loosening_is_dated_by_the_log_before_it():
    """An entry is never dated earlier than the line before it, so a late-signed, back-stamped loosening cannot skip D12."""
    rows = [_state_cap(0.10, _state_kst(2026, 10, 20)),
            ("session_armed", {"session_id": "S1"}, _state_kst(2026, 10, 24, 10)),
            _state_cap(0.50, _state_kst(2026, 10, 23))]                      # written after the arming, stamped before
    check, today, tomorrow = _state_log(*rows), _state_kst(2026, 10, 24, 12), _state_kst(2026, 10, 25, 12)
    assert _state_at(check, today, session_id="S1").caps == {"okx_equity_share": 0.10}, "S1 was armed before it"
    assert _state_at(check, today).caps == {"okx_equity_share": 0.10}, "dated 24 October, so it applies from the 25th"
    assert _state_at(check, tomorrow).caps == {"okx_equity_share": 0.50}, "no session: the loosening counts"
    assert _state_at(check, tomorrow, session_id="S1").caps == {"okx_equity_share": 0.10}, "S1 is still armed"
    disarmed = _state_log(*rows, ("system_disarm", {"session_id": "S1", "reason": "session end"},
                                  _state_kst(2026, 10, 24, 15)))
    assert _state_at(disarmed, tomorrow, session_id="S1").caps == {"okx_equity_share": 0.50}
    ahead = _state_log(_state_cap(0.10, _state_kst(2026, 10, 20)),
                       ("course_completed", {"course": "short_course_30m", "evidence": "certificate"},
                        _state_kst(2026, 10, 26)),                                # stamped two days ahead
                       _state_cap(0.30, _state_kst(2026, 10, 22)))
    assert _state_at(ahead, _state_kst(2026, 10, 26, 12)).caps == {"okx_equity_share": 0.10}, "dated 26 October"
    assert _state_at(ahead, _state_kst(2026, 10, 27, 12)).caps == {"okx_equity_share": 0.30}


def test_state_halt_and_disarm_apply_before_their_stamp():
    """A halt or a disarm only tightens, so it counts at once even when the clock stepped back and it is stamped ahead."""
    rows = [_state_limits(21_000.0, 5_000.0, _state_kst(2026, 10, 10)),
            _state_limits(15_000.0, 5_000.0, _state_kst(2026, 10, 12)),         # a floor loosening, in effect from the 13th
            _state_cap(0.10, _state_kst(2026, 10, 10)),
            ("session_armed", {"session_id": "S1"}, _state_kst(2026, 10, 20))]
    ahead = _state_kst(2026, 10, 24, 13)
    check = _state_log(*rows, ("system_halt", {"floor_krw": 21_000.0}, ahead),
                       ("system_disarm", {"session_id": "S1", "reason": "kill switch"}, ahead),
                       _state_cap(0.30, _state_kst(2026, 10, 22)))                # written after the halt, stamped before
    now = _state_kst(2026, 10, 24, 12)
    state = _state_at(check, now, session_id="S1")
    assert state.halted_floors == {21_000.0} and state.armed_sessions == frozenset()
    assert state.limits["total_loss_floor_krw"] == 21_000.0, "the halted floor clamps the loosened one"
    assert state.caps == {"okx_equity_share": 0.10}, "a loosening written after the halt never counts"
    plain = _state_at(_state_log(*rows), now)
    assert plain.armed_sessions == {"S1"} and plain.limits["total_loss_floor_krw"] == 15_000.0, "without them: as is"


def test_state_future_tightening_applies_and_future_loosening_does_not():
    now = _state_kst(2026, 10, 24, 12)
    tomorrow = _state_kst(2026, 10, 25)
    base = (_state_cap(0.20, _state_kst(2026, 10, 20)), _state_limits(21_000.0, 5_000.0, _state_kst(2026, 10, 10)))
    assert _state_at(_state_log(*base, _state_cap(0.05, tomorrow)), now).caps == {"okx_equity_share": 0.05}
    assert _state_at(_state_log(*base, _state_cap(0.50, tomorrow)), now).caps == {"okx_equity_share": 0.20}
    assert _state_at(_state_log(_state_cap(0.20, tomorrow)), now).caps == {}, "a first cap is a loosening"
    tighter = _state_at(_state_log(*base, _state_limits(25_000.0, 3_000.0, tomorrow)), now)
    assert tighter.limits == {"total_loss_floor_krw": 25_000.0, "daily_loss_krw": 3_000.0}
    mixed = _state_at(_state_log(*base, _state_limits(30_000.0, 8_000.0, tomorrow)), now)
    assert mixed.limits == {"total_loss_floor_krw": 30_000.0, "daily_loss_krw": 5_000.0}, "per key: floor up, daily no"
    later = _state_at(_state_log(*base, _state_cap(0.05, tomorrow), _state_cap(0.40, _state_kst(2026, 10, 22))), now)
    assert later.caps == {"okx_equity_share": 0.05}, "a loosening written after it, stamped before it, waits"


def _state_ahead(at: _dt.datetime):
    """Any line stamped ahead of the others; a course item, so that it changes nothing but the dates."""
    return ("course_completed", {"course": "short_course_30m", "evidence": "certificate"}, at)


def test_state_a_line_stamped_ahead_does_not_delay_an_arming():
    """An arming is dated as early as the log allows (P31), so a line stamped ahead before it cannot hide it."""
    for ahead in (_state_kst(2026, 10, 30), _state_kst(2099, 1, 1)):
        rows = [_state_cap(0.10, _state_kst(2026, 10, 20)), _state_cap(0.50, _state_kst(2026, 10, 22, 12)),
                _state_ahead(ahead), ("session_armed", {"session_id": "S1"}, _state_kst(2026, 10, 22, 13))]
        check, at = _state_log(*rows), _state_kst(2026, 10, 23, 12)
        assert _state_at(check, at, session_id="S1").caps == {"okx_equity_share": 0.10}, "S1 armed on the loosening's date"
        assert _state_at(check, at).caps == {"okx_equity_share": 0.50}, "control: no session, so the loosening counts"
        later = _state_log(*rows[:3], ("session_armed", {"session_id": "S1"}, _state_kst(2026, 10, 23, 10)))
        control = _state_at(later, _state_kst(2026, 10, 24, 12), session_id="S1")
        assert control.caps == {"okx_equity_share": 0.50}, "control: armed on the 23rd, after the loosening took effect"


def test_state_a_disarm_stamped_ahead_does_not_delay_a_rearming():
    rows = [_state_cap(0.10, _state_kst(2026, 10, 20)),
            ("session_armed", {"session_id": "S1"}, _state_kst(2026, 10, 22, 10)),
            _state_cap(0.50, _state_kst(2026, 10, 22, 12)),
            ("system_disarm", {"session_id": "S1", "reason": "kill switch"}, _state_kst(2099, 1, 1)),
            ("session_armed", {"session_id": "S1"}, _state_kst(2026, 10, 22, 13))]
    state = _state_at(_state_log(*rows), _state_kst(2026, 10, 23, 12), session_id="S1")
    assert state.armed_sessions == {"S1"} and state.caps == {"okx_equity_share": 0.10}


def _state_loosened_before_a_halt():
    """A cap and a daily loss loosened on 14 October, and a halt the same evening."""
    loosen = [_state_limits(21_000.0, 5_000.0, _state_kst(2026, 10, 10)), _state_cap(0.10, _state_kst(2026, 10, 10)),
              _state_limits(21_000.0, 9_000.0, _state_kst(2026, 10, 14, 10)), _state_cap(0.50, _state_kst(2026, 10, 14, 10))]
    return loosen, ("system_halt", {"floor_krw": 21_000.0}, _state_kst(2026, 10, 14, 20))


def test_state_a_line_stamped_ahead_does_not_delay_a_halt():
    """A halt is dated as early as the log allows (D12, P32), so a line stamped ahead before it cannot hide it."""
    loosen, halt = _state_loosened_before_a_halt()
    for ahead in (_state_kst(2026, 10, 30), _state_kst(2099, 1, 1)):
        state = _state_at(_state_log(*loosen, _state_ahead(ahead), halt), _state_kst(2026, 10, 24))
        assert state.caps == {"okx_equity_share": 0.10}, ahead
        assert state.limits == {"total_loss_floor_krw": 21_000.0, "daily_loss_krw": 5_000.0}, ahead


def test_state_a_halt_stamped_far_ahead_does_not_shadow_the_real_one():
    loosen, halt = _state_loosened_before_a_halt()
    bogus = ("system_halt", {"floor_krw": 21_000.0}, _state_kst(2099, 1, 1))     # an unsigned halt stamped far ahead
    state = _state_at(_state_log(*loosen, bogus, halt), _state_kst(2026, 10, 24))
    assert state.caps == {"okx_equity_share": 0.10} and state.limits["daily_loss_krw"] == 5_000.0, "the earliest halt rules"
    alone = _state_at(_state_log(*loosen, bogus), _state_kst(2026, 10, 24))
    assert alone.caps == {"okx_equity_share": 0.50}, "control: nothing shows that halt came before 15 October"
    assert alone.halted_floors == {21_000.0}


def _state_arming_rows(first_arming: _dt.datetime):
    """cap 0.10, a loosening to 0.50 on 22 October, S1 armed at `first_arming`, then a line stamped 22 October 14:00."""
    return [_state_cap(0.10, _state_kst(2026, 10, 20)), _state_cap(0.50, _state_kst(2026, 10, 22, 12)),
            ("session_armed", {"session_id": "S1"}, first_arming),
            _state_ahead(_state_kst(2026, 10, 22, 14))]


def test_state_an_arming_stamped_ahead_still_blocks_a_loosening():
    """An arming blocks a loosening early (D12) but arms the session late (it enables trading)."""
    rows = _state_arming_rows(_state_kst(2099, 1, 1))
    state = _state_at(_state_log(*rows), _state_kst(2026, 10, 23, 12), session_id="S1")
    assert state.caps == {"okx_equity_share": 0.10}, "the line after it dates the arming no later than 22 October"
    assert "S1" not in state.armed_sessions, "armed only from its stamp: it enables nothing yet"
    assert _state_at(_state_log(*rows), _state_kst(2026, 10, 23, 12)).caps == {"okx_equity_share": 0.50}, "no session"
    rearmed = _state_log(*rows, ("session_armed", {"session_id": "S1"}, _state_kst(2026, 10, 23, 10)))
    for now in (_state_kst(2026, 10, 23, 12), _state_kst(2026, 10, 24, 12), _state_kst(2026, 10, 30)):
        state = _state_at(rearmed, now, session_id="S1")
        assert state.caps == {"okx_equity_share": 0.10} and "S1" in state.armed_sessions, now


def test_state_a_rearming_does_not_move_the_blocking_date():
    rows = _state_arming_rows(_state_kst(2026, 10, 23, 20))
    check = _state_log(*rows, ("session_armed", {"session_id": "S1"}, _state_kst(2026, 10, 23, 10)))
    for now in (_state_kst(2026, 10, 23, 12), _state_kst(2026, 10, 23, 21), _state_kst(2026, 10, 24, 12)):
        assert _state_at(check, now, session_id="S1").caps == {"okx_equity_share": 0.10}, now
    assert _state_at(check, _state_kst(2026, 10, 23, 12)).caps == {"okx_equity_share": 0.50}, "no session: it counts"
    disarmed = _state_log(*rows, ("system_disarm", {"session_id": "S1", "reason": "kill switch"},
                                  _state_kst(2026, 10, 23, 11)),
                          ("session_armed", {"session_id": "S1"}, _state_kst(2026, 10, 24, 9)))
    assert _state_at(disarmed, _state_kst(2026, 10, 24, 12), session_id="S1").caps == {"okx_equity_share": 0.50}, \
        "a disarm clears the blocking date: S1 was armed again on the 24th, after the loosening took effect"
