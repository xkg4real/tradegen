"""The owner log `~/.tradegen/compliance/owner.jsonl` (spec 6.4, P20): one canonical-JSON line per entry, chained by
`prev_sha256`, owner entries Ed25519-signed, system entries (`system_halt`, `system_disarm`) unsigned and able only
to tighten. Paths are computed at call time, so a test's TRADEGEN_HOME moves them. `cryptography` is imported only
inside the functions that need it: without it the log never verifies (Task 10)."""
from __future__ import annotations

import base64
import binascii
import json
import math
import os
import re
import threading
from collections.abc import Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from core.compliance import rules
from core.compliance.model import canonical_json, iso_utc, sha256_hex
from core.isolation import checked_target, state_root

PUBKEY_PATH = Path(__file__).with_name("owner_pubkey.pem")   # the trust anchor; absent until owner act 1 (P24)

OWNER_KINDS = frozenset({"approved", "code_approved", "course_completed", "broker_approval", "age_of_majority",
    "cap_set", "limit_set", "withdrawal_address", "session_armed", "session_ack", "transfer_ack", "key_rotated"})
SYSTEM_KINDS = frozenset({"system_halt", "system_disarm"})
APPROVAL_KINDS = ("rules", "instruments", "venues", "calendar")
SIG_DOMAIN = b"tradegen-owner-log/1\n"
GENESIS_PREV = "0" * 64


def home() -> Path:
    """`<state root>/compliance`, resolved at call time. Computing a path creates nothing."""
    return state_root() / "compliance"


def log_path() -> Path:
    return home() / "owner.jsonl"


def store_dir() -> Path:
    return home() / "approved"


def snapshots_dir() -> Path:
    return home() / "snapshots"


def alerts_path() -> Path:
    return home() / "alerts.jsonl"


@dataclass(frozen=True, kw_only=True)
class Entry:
    seq: int
    utc: str
    kind: str
    data: Mapping
    row_sha256: str
    signed: bool


@dataclass(frozen=True, kw_only=True)
class LogCheck:
    ok: bool
    reason: str
    entries: tuple[Entry, ...]
    head: tuple[int, str]                 # (seq, row_sha256) of the last line; (0, "") when empty or broken
    first_key_fingerprint: str            # the key that signed entry 1 (P20); "" when broken


# -- event data schemas (spec 6.4 "Events"; exact keys) ------------------------------------------------------------
_HEX64 = re.compile(r"[0-9a-f]{64}")
# ASCII digits only: `\d` also takes fullwidth and Arabic-Indic digits, and strptime reads some of them.
_UTC = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z")
_ISO_DATE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
_BODY_KEYS = ("seq", "prev_sha256", "utc", "kind", "data")
_LINE_KEYS = frozenset(_BODY_KEYS) | {"row_sha256"}
_ITEMS = rules.OWNER_REQUIREMENTS - {"age_of_majority"}     # that flag comes only from a birth date


def _hex64(v) -> bool:
    return isinstance(v, str) and _HEX64.fullmatch(v) is not None


def _text(v) -> bool:
    return isinstance(v, str) and v.strip() != ""


def _number(v) -> bool:
    """A JSON int or float, not bool, finite as a float; an int too large for a float is refused."""
    try:
        return type(v) in (int, float) and math.isfinite(v)
    except OverflowError:
        return False


def _one_of(options):
    return lambda v: isinstance(v, str) and v in options


def _parses(v, pattern, parse) -> bool:
    if not (isinstance(v, str) and pattern.fullmatch(v)):
        return False
    try:
        parse(v)
    except ValueError:
        return False
    return True


def _iso_date(v) -> bool:
    return _parses(v, _ISO_DATE, date.fromisoformat)


def _utc(v) -> bool:
    return _parses(v, _UTC, lambda s: datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ"))


def _b64_of(n: int):
    """Standard base64 with canonical padding of exactly `n` bytes."""
    def check(v) -> bool:
        if not isinstance(v, str):
            return False
        try:
            raw = base64.b64decode(v, validate=True)
        except (binascii.Error, ValueError):
            return False
        return len(raw) == n and base64.b64encode(raw).decode("ascii") == v
    return check


def _files(v) -> bool:
    """[[relpath, sha256], ...], non-empty, sorted by path with no repeat (the order of code_files, Task 13)."""
    if not (isinstance(v, list) and v and all(isinstance(f, list) and len(f) == 2 and _text(f[0]) and _hex64(f[1])
                                              for f in v)):
        return False
    paths = [f[0] for f in v]
    return paths == sorted(set(paths))


_DATA = {
    "approved": {"kind": _one_of(APPROVAL_KINDS), "sha256": _hex64},
    "code_approved": {"sha256": _hex64, "files": _files},
    "course_completed": {"course": _one_of(_ITEMS), "evidence": _text},
    "broker_approval": {"item": _one_of(_ITEMS), "evidence": _text},
    "age_of_majority": {"birth_date": _iso_date, "evidence": _text},
    "cap_set": {"key": _one_of(("okx_equity_share",)), "value": lambda v: _number(v) and 0 < v <= 1},
    "limit_set": {"total_loss_floor_krw": lambda v: _number(v) and v >= 0,
                  "daily_loss_krw": lambda v: _number(v) and v > 0},
    "withdrawal_address": {"venue": _one_of(rules.VENUES), "symbol": _text, "network": _text, "address": _text,
                           "tag": lambda v: v is None or _text(v), "evidence": _text},
    "session_armed": {"session_id": _text},
    "session_ack": {"session_id": _text, "row_id": _text, "warning_sha256": _hex64},
    "transfer_ack": {"intent_hash": _hex64, "warning_sha256": _hex64},
    "key_rotated": {"old_pubkey_b64": _b64_of(32), "new_pubkey_b64": _b64_of(32)},   # P20: the walk needs both keys
    "system_halt": {"floor_krw": lambda v: _number(v) and v >= 0},
    "system_disarm": {"session_id": _text, "reason": _text},
}


def _data_problem(kind: str, data) -> str:
    """"" when `data` has exactly the keys of `kind` with valid values, else what is wrong."""
    schema = _DATA[kind]
    if not isinstance(data, dict):
        return "is not an object"
    if set(data) != set(schema):
        return f"keys {sorted(map(str, data))} are not {sorted(schema)}"
    bad = sorted(k for k, ok in schema.items() if not ok(data[k]))
    if bad:
        return f"has invalid {', '.join(bad)}"
    if kind == "code_approved" and data["sha256"] != sha256_hex(canonical_json(data["files"])):
        return "sha256 is not the hash of its files"
    return ""


# -- reading and checking lines -----------------------------------------------------------------------------------
def _log_lines(path: Path) -> list[bytes]:
    """The log's lines, each with its b"\\n" (a torn last line has none, which the checks refuse); [] if absent."""
    return path.read_bytes().splitlines(keepends=True) if path.exists() else []


def _no_duplicates(pairs):
    out = {}
    for k, v in pairs:
        if k in out:
            raise ValueError(f"duplicate key {k!r}")
        out[k] = v
    return out


def _parse_line(n: int, line, prev: str) -> tuple[Entry, dict]:
    """Line `n` checked against the row_sha256 of the line before it; ValueError naming the first defect."""
    if not isinstance(line, bytes) or not line.endswith(b"\n") or b"\n" in line[:-1] or b"\r" in line:
        raise ValueError("not one newline-terminated line")
    try:
        obj = json.loads(line[:-1].decode("utf-8"), object_pairs_hook=_no_duplicates)
    except (UnicodeDecodeError, ValueError) as exc:
        raise ValueError(f"unreadable ({exc})") from None
    if not isinstance(obj, dict):
        raise ValueError("not a JSON object")
    try:
        same = canonical_json(obj).encode("utf-8") == line[:-1]
    except (TypeError, ValueError):
        same = False
    if not same:
        raise ValueError("not its canonical JSON")
    kind = obj.get("kind")
    if not isinstance(kind, str) or kind not in OWNER_KINDS | SYSTEM_KINDS:
        raise ValueError(f"unknown kind {kind!r}")
    signed = kind in OWNER_KINDS
    if signed and "sig" not in obj:
        raise ValueError(f"unsigned {kind} entry: only system_halt and system_disarm go unsigned")
    if not signed and "sig" in obj:
        raise ValueError(f"signature on a system entry ({kind})")
    if set(obj) != _LINE_KEYS | ({"sig"} if signed else set()):
        raise ValueError(f"line keys {sorted(obj)}")
    if type(obj["seq"]) is not int or obj["seq"] != n:
        raise ValueError(f"seq {obj['seq']!r}, expected {n}")
    if obj["prev_sha256"] != prev:
        raise ValueError("prev_sha256 does not chain to the line before")
    if not _utc(obj["utc"]):
        raise ValueError(f"utc {obj['utc']!r} is not YYYY-MM-DDTHH:MM:SSZ")
    row = sha256_hex(canonical_json({k: obj[k] for k in _BODY_KEYS}))
    if obj["row_sha256"] != row:
        raise ValueError("row_sha256 does not recompute")
    why = _data_problem(kind, obj["data"])
    if why:
        raise ValueError(f"{kind} data {why}")
    if signed and not _b64_of(64)(obj["sig"]):
        raise ValueError("sig is not base64 of 64 bytes")
    return Entry(seq=n, utc=obj["utc"], kind=kind, data=obj["data"], row_sha256=row, signed=signed), obj


def _structure(lines) -> tuple[list[tuple[Entry, dict]], str]:
    """Every line parsed and chained, signatures not checked: ([(entry, line object), ...], "") when sound, else
    ([], "line N: <defect>"). verify_log and append_system_entry share it."""
    out: list[tuple[Entry, dict]] = []
    prev = GENESIS_PREV
    for n, line in enumerate(lines, start=1):
        try:
            entry, obj = _parse_line(n, line, prev)
        except (ValueError, ArithmeticError, RecursionError) as exc:   # RecursionError: a deeply nested line
            return [], f"line {n}: {exc}"
        out.append((entry, obj))
        prev = entry.row_sha256
    return out, ""


def fingerprint(pubkey_raw: bytes) -> str:
    """"SHA256:" + the sha256 hex of the raw 32-byte public key (what the owner writes down away from the PC)."""
    return "SHA256:" + sha256_hex(pubkey_raw)


def read_pubkey(path: Path) -> bytes:
    """The raw 32 bytes of the Ed25519 key in a PEM SubjectPublicKeyInfo file. FileNotFoundError when the file is
    absent (P24), ImportError without cryptography (Task 10), ValueError for anything but an Ed25519 public key (a
    key of another or an unsupported type included). Any other OSError (for example the pem is a directory) can also
    escape; callers treat every exception from here as a broken log."""
    data = Path(path).read_bytes()
    from cryptography.exceptions import UnsupportedAlgorithm
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    from cryptography.hazmat.primitives.serialization import load_pem_public_key
    try:
        key = load_pem_public_key(data)
    except (ValueError, UnsupportedAlgorithm) as exc:
        raise ValueError(f"{Path(path).name}: not an Ed25519 public key ({exc})") from None
    if not isinstance(key, Ed25519PublicKey):
        raise ValueError(f"{Path(path).name}: not an Ed25519 public key")
    return key.public_bytes_raw()


def _broken(reason: str) -> LogCheck:
    return LogCheck(ok=False, reason=reason, entries=(), head=(0, ""), first_key_fingerprint="")


def verify_log(lines: list[bytes], pubkey_raw: bytes, anchors: list[tuple[int, str]]) -> LogCheck:
    """Spec 6.4 BROKEN rules over the whole log: line structure and chain, every anchor, the key_rotated walk back
    from `pubkey_raw` (owner_pubkey.pem) to the first key (P20), then every owner signature under the key in force at
    its line. Never raises; a broken log yields no entries, head (0, "") and no fingerprint."""
    try:
        return _verify(lines, pubkey_raw, anchors)
    except Exception as exc:                                    # never raises: anything unexpected is BROKEN
        return _broken(f"internal error {type(exc).__name__}")


def _verify(lines, pubkey_raw, anchors) -> LogCheck:
    parsed, why = _structure(lines)
    if why:
        return _broken(why)
    for seq, sha in anchors:
        if seq < 1:
            continue                                            # the head of an empty log anchors nothing
        if seq > len(parsed):
            return _broken(f"an anchor names entry #{seq} but the log has {len(parsed)} lines")
        if parsed[seq - 1][0].row_sha256 != sha:
            return _broken(f"line {seq}: row_sha256 differs from its anchor")
    if not isinstance(pubkey_raw, bytes) or len(pubkey_raw) != 32:
        return _broken("owner key is not a raw 32-byte Ed25519 public key")
    key = pubkey_raw
    for entry, _ in reversed(parsed):                           # P20: from the pinned key back to the first one
        if entry.kind == "key_rotated":
            if base64.b64decode(entry.data["new_pubkey_b64"]) != key:
                return _broken(f"line {entry.seq}: key_rotated does not lead to the key in force after it "
                               "(owner_pubkey.pem after the last rotation)")
            key = base64.b64decode(entry.data["old_pubkey_b64"])
    first = key
    try:
        from cryptography.exceptions import InvalidSignature
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    except ImportError:
        return _broken("cryptography missing: install it (Task 10)")
    verifier = Ed25519PublicKey.from_public_bytes(first)
    for entry, obj in parsed:
        if entry.signed:
            try:
                verifier.verify(base64.b64decode(obj["sig"]), SIG_DOMAIN + entry.row_sha256.encode("ascii"))
            except InvalidSignature:
                return _broken(f"line {entry.seq}: bad signature on {entry.kind}")
        if entry.kind == "key_rotated":
            verifier = Ed25519PublicKey.from_public_bytes(base64.b64decode(entry.data["new_pubkey_b64"]))
    head = (parsed[-1][0].seq, parsed[-1][0].row_sha256) if parsed else (0, "")
    return LogCheck(ok=True, reason="", entries=tuple(e for e, _ in parsed), head=head,
                    first_key_fingerprint=fingerprint(first))


# -- anchors (spec 6.4 "Anchors") ---------------------------------------------------------------------------------
def _json_object(raw: bytes, where: str) -> dict:
    try:
        doc = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError, RecursionError) as exc:
        raise ValueError(f"{where}: unreadable ({exc})") from None
    if not isinstance(doc, dict):
        raise ValueError(f"{where}: not a JSON object")
    return doc


def _alert_rows() -> list[dict]:
    """Every alerts.jsonl row ([] when the file is absent). ValueError on an unreadable line and OSError on an
    unreadable file; both mean a broken log (fail closed)."""
    path = alerts_path()
    if not path.exists():
        return []
    return [_json_object(line, f"alerts.jsonl line {n}")
            for n, line in enumerate(path.read_bytes().splitlines(), start=1) if line.strip()]


def _anchor(seq, sha, where: str) -> tuple[int, str]:
    """(seq >= 1, 64 lower-case hex), or exactly (0, "") for the head of an empty log."""
    if type(seq) is not int or seq < 0 or not (sha == "" if seq == 0 else _hex64(sha)):
        raise ValueError(f"{where}: not an anchor ({seq!r}, {sha!r})")
    return seq, sha


def read_anchors() -> list[tuple[int, str]]:
    """Every recorded (seq, row_sha256), sorted and unique: alerts.jsonl rows (head_seq, head_sha256), snapshot
    files (their "head" pair) and the approved store's *.anchor.json files ({"seq", "row_sha256"}). ValueError on a
    malformed anchor and OSError on a file that cannot be read; the caller treats both as a broken log."""
    found = {_anchor(r.get("head_seq"), r.get("head_sha256"), "alerts.jsonl") for r in _alert_rows()}
    for path in sorted(snapshots_dir().glob("*.json")):
        head = _json_object(path.read_bytes(), path.name).get("head")
        if not (isinstance(head, list) and len(head) == 2):
            raise ValueError(f"{path.name}: no head anchor")
        found.add(_anchor(head[0], head[1], path.name))
    for path in sorted(store_dir().glob("*/*.anchor.json")):
        doc = _json_object(path.read_bytes(), path.name)
        found.add(_anchor(doc.get("seq"), doc.get("row_sha256"), path.name))
    return sorted(found)


# -- appending system entries --------------------------------------------------------------------------------------
_APPEND_LOCK = threading.Lock()


@contextmanager
def _exclusive(path: Path):
    """Serialise read-verify-append on the owner log across threads and processes: a sidecar `<log>.lock` holding
    an OS byte lock (copied from core.quant.gate_ledger._exclusive, which this package may not import)."""
    checked_target(path.parent, "owner log folder").mkdir(parents=True, exist_ok=True)
    with _APPEND_LOCK, open(checked_target(str(path) + ".lock", "owner log lock"), "a+b") as fh:
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


def append_system_entry(kind: str, data: dict, now: datetime) -> tuple[int, str]:
    """Append one unsigned system entry and return its (seq, row_sha256). Under the sidecar lock the chain is
    re-checked first (appending needs no signature check), then one canonical line is appended with fsync.
    ValueError on an owner kind, bad data or a naive `now`; RuntimeError on a broken chain or a linked target."""
    if kind not in SYSTEM_KINDS:
        raise ValueError(f"{kind!r} is not a system kind: owner entries come only from the owner's signer")
    why = _data_problem(kind, data)
    if why:
        raise ValueError(f"{kind} data {why}")
    utc = iso_utc(now)
    path = log_path()
    with _exclusive(path):
        parsed, why = _structure(_log_lines(path))
        if why:
            raise RuntimeError(f"owner log is broken ({why}); nothing appended")
        last = parsed[-1][0] if parsed else None
        body = {"seq": last.seq + 1 if last else 1, "prev_sha256": last.row_sha256 if last else GENESIS_PREV,
                "utc": utc, "kind": kind, "data": data}
        row = sha256_hex(canonical_json(body))
        line = (canonical_json({**body, "row_sha256": row}) + "\n").encode("utf-8")
        with open(checked_target(path, "owner log"), "ab") as fh:
            fh.write(line)
            fh.flush()
            os.fsync(fh.fileno())
    return body["seq"], row


# --------------------------------------------------------------------------- #
# Owner state (Task 12; pure): what a verified log means on a given Asia/Seoul date (spec 6.4 Events, D12)
# --------------------------------------------------------------------------- #
import dataclasses  # noqa: E402
import datetime as _dt  # noqa: E402

from core.compliance import model, rules  # noqa: E402

_LOG_STAMP = "%Y-%m-%dT%H:%M:%SZ"
_LIMIT_KEYS = ("total_loss_floor_krw", "daily_loss_krw")
_TIGHTER = {"okx_equity_share": lambda new, old: new <= old,           # a smaller cap
            "total_loss_floor_krw": lambda new, old: new >= old,       # a larger floor
            "daily_loss_krw": lambda new, old: new <= old}             # a smaller daily loss


def _seoul_date(utc: str) -> _dt.date:
    """The Asia/Seoul date of a log stamp "YYYY-MM-DDTHH:MM:SSZ"."""
    moment = _dt.datetime.strptime(utc, _LOG_STAMP).replace(tzinfo=_dt.timezone.utc)
    return moment.astimezone(model.KST).date()


def _majority_date(birth_date: str) -> _dt.date:
    """The day the owner turns 19, Korea's age of majority; a 29 February birthday counts from 1 March."""
    born = rules.parse_date(birth_date, "birth_date")
    try:
        return born.replace(year=born.year + 19)
    except ValueError:
        return _dt.date(born.year + 19, 3, 1)


def _up_to(check: LogCheck, now_utc: str) -> LogCheck:
    """`check` without the entries stamped after `now_utc`: a future-dated entry counts only from its stamp on.
    For in_force, history and code_approval; owner_state applies its own rule (halts, disarms and tightenings
    count before their stamp)."""
    return dataclasses.replace(check, entries=tuple(e for e in check.entries if e.utc <= now_utc))


def owner_state(check: LogCheck, *, date: _dt.date, now_utc: str, session_id: str | None,
                fingerprint_now: str, first_recorded: tuple[str, str] | None) -> model.OwnerState:
    """What the verified log means on Asia/Seoul `date` at `now_utc`, for `session_id`. BROKEN when the check
    failed, when the first fingerprint recorded in alerts.jsonl is not the log's first key (P20: "KEY CHANGED
    since <date>"), or when entry data cannot be read. An entry stamped after `now_utc` is ignored, except a
    system_halt, a system_disarm and a tightening cap or limit: those only tighten, so they apply at once."""
    if not check.ok:
        return model.OwnerState.broken(check.reason, head=check.head, fingerprint=fingerprint_now)
    if first_recorded is not None and first_recorded[0] != check.first_key_fingerprint:
        since = first_recorded[1][:10] or "an unknown date"
        return model.OwnerState.broken(f"KEY CHANGED since {since}", head=check.head, fingerprint=fingerprint_now)
    try:
        return _owner_fold(check.entries, date, now_utc, session_id, check.head, fingerprint_now)
    except (KeyError, TypeError, ValueError, rules.Invalid) as exc:
        return model.OwnerState.broken(f"owner log: unreadable entry data ({type(exc).__name__})",
                                       head=check.head, fingerprint=fingerprint_now)


def _owner_fold(entries, day: _dt.date, now_utc: str, session_id, head, fingerprint_now) -> model.OwnerState:
    """D12 over the entries in log order. An unset cap or limit counts as the tightest, so setting one is a
    loosening. A tightening applies from its entry. A loosening counts only from the Asia/Seoul date after its
    own, only when it took effect before the first system_halt, and never inside `session_id` while that session
    has been armed, since its last disarm, from a date on or before the loosening's. A set floor is never below the
    highest halted floor. The latest age_of_majority entry wins.
    A loosening is dated as late as the log allows: by the latest Asia/Seoul date among the lines up to and
    including it, so a late-signed entry stamped back cannot count as older than the line before it. A restriction
    (a system_halt or a session_armed) is dated as early as the log allows: by the earliest of its own stamp, the
    stamps of the lines after it, and `day`, so a line stamped ahead cannot push it later than the loosening it
    follows. The halt cutoff is the earliest halt date. An entry stamped after `now_utc` counts only when it is a
    system_halt, a system_disarm or a tightening; a loosening stamped ahead never applies. A session_armed stamped
    after `now_utc` does not arm the session (armed_sessions) but still blocks loosenings, dated as above."""
    stamps = [_seoul_date(e.utc) for e in entries]
    late, seen = [], _dt.date.min
    for on in stamps:
        seen = max(seen, on)
        late.append(seen)
    early, soonest = [_dt.date.min] * len(stamps), day
    for i in range(len(stamps) - 1, -1, -1):
        soonest = min(soonest, stamps[i])
        early[i] = soonest
    dated = list(zip(entries, late, early))
    halts = [(e.seq, soon, float(e.data["floor_krw"])) for e, _, soon in dated if e.kind == "system_halt"]
    first_halt = min((seq for seq, _, _ in halts), default=None)
    halt_day = min((soon for _, soon, _ in halts), default=None)
    halt_floor = max((floor for _, _, floor in halts), default=None)
    # An arming blocks a loosening early but arms the session late (it enables trading):
    # `blocking` takes every session_armed whatever its stamp, session id -> the earliest date of its armings
    # since its last disarm; `armed` takes only the armings stamped by now.
    blocking: dict[str, _dt.date] = {}
    armed: set[str] = set()
    for e, _, soon in dated:
        if e.kind == "session_armed":
            sid = e.data["session_id"]
            blocking[sid] = min(blocking.get(sid, soon), soon)
            if e.utc <= now_utc:
                armed.add(sid)
        elif e.kind == "system_disarm":
            blocking.pop(e.data["session_id"], None)
            armed.discard(e.data["session_id"])
    mine = blocking.get(session_id) if session_id is not None else None

    def loosening_counts(e, on) -> bool:
        return (e.utc <= now_utc and on < day
                and (first_halt is None or (e.seq < first_halt and on < halt_day))
                and (mine is None or mine > on))

    values: dict[str, float] = {}
    majority: _dt.date | None = None
    flags, addresses, session_acks, transfer_acks = set(), set(), set(), set()
    for e, on, _ in dated:
        d = e.data
        if e.utc > now_utc and e.kind not in ("cap_set", "limit_set"):
            continue
        if e.kind in ("cap_set", "limit_set"):
            pairs = [(d["key"], d["value"])] if e.kind == "cap_set" else [(k, d[k]) for k in _LIMIT_KEYS]
            for key, value in pairs:
                value, old = float(value), values.get(key)
                if key in _TIGHTER and ((old is not None and _TIGHTER[key](value, old)) or loosening_counts(e, on)):
                    values[key] = value
        elif e.kind == "age_of_majority":
            majority = _majority_date(d["birth_date"])             # every entry is parsed; the latest wins
        elif e.kind == "course_completed":
            flags.add(d["course"])
        elif e.kind == "broker_approval":
            flags.add(d["item"])
        elif e.kind == "withdrawal_address":
            addresses.add((d["venue"], d["symbol"], d["network"], d["address"], d["tag"] or ""))
        elif e.kind == "session_ack":
            session_acks.add((d["session_id"], d["row_id"], d["warning_sha256"]))
        elif e.kind == "transfer_ack":
            transfer_acks.add((d["intent_hash"], d["warning_sha256"]))
    if majority is not None and majority <= day:
        flags.add("age_of_majority")
    if halt_floor is not None and "total_loss_floor_krw" in values:     # never below a halted floor, for good (D12)
        values["total_loss_floor_krw"] = max(values["total_loss_floor_krw"], halt_floor)
    return model.OwnerState(
        status="OK", head=head, caps={k: v for k, v in values.items() if k == "okx_equity_share"},
        limits={k: v for k, v in values.items() if k in _LIMIT_KEYS}, addresses=frozenset(addresses),
        flags=frozenset(flags), halted_floors=frozenset(floor for _, _, floor in halts),
        armed_sessions=frozenset(armed), session_acks=frozenset(session_acks),
        transfer_acks=frozenset(transfer_acks), fingerprint=fingerprint_now)


def in_force(check: LogCheck) -> dict[str, tuple[str, int]]:
    """kind -> (sha256, seq) of the latest signed `approved` entry of each kind (spec 5.2 What is in force).
    A superseded hash counts again only when a new entry signs it. A broken log approves nothing."""
    out: dict[str, tuple[str, int]] = {}
    for e in check.entries if check.ok else ():
        if e.kind == "approved":
            out[e.data["kind"]] = (e.data["sha256"], e.seq)
    return out


def history(check: LogCheck, kind: str) -> list[tuple[str, int]]:
    """The earlier `approved` entries of `kind` as (sha256, seq), newest first; the one in force is left out."""
    found = [(e.data["sha256"], e.seq) for e in (check.entries if check.ok else ())
             if e.kind == "approved" and e.data["kind"] == kind]
    return found[-2::-1]


def code_approval(check: LogCheck) -> str | None:
    """The sha256 named by the latest code_approved entry, or None."""
    found = [e.data["sha256"] for e in (check.entries if check.ok else ()) if e.kind == "code_approved"]
    return found[-1] if found else None


# --------------------------------------------------------------------------- #
# Approved store, D14 code hash and snapshots (Task 13; spec 5.2 What is in force, 6.4; P6, P21, P34)
# --------------------------------------------------------------------------- #
import ast  # noqa: E402
import importlib.metadata  # noqa: E402
import json  # noqa: E402
import os  # noqa: E402
from pathlib import Path  # noqa: E402

from core.isolation import checked_target  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]
_TABLES = ("rules", "instruments", "venues")
_RECORD_DISTS = ("cryptography", "PyYAML")        # their RECORD files stand for the installed packages (P6)


def _write_new(path: Path, data: bytes) -> bool:
    """Creates `path` holding `data`; False, writing nothing, when it already exists. The bytes go to a fresh temp
    file in the compliance home (fsync) and os.rename moves it into place, so a crash never leaves a torn file under
    the final name; on Windows the rename refuses an existing target, which keeps the file write-once. Every folder
    and file must resolve inside the compliance home and be no link (A0)."""
    root = home()
    checked_target(path.parent, "compliance folder", within=root)
    path.parent.mkdir(parents=True, exist_ok=True)
    checked_target(path, "compliance file", within=root)
    if path.exists():
        return False
    tmp = checked_target(root / f".{path.name}.{os.urandom(6).hex()}.tmp", "compliance temp file", within=root)
    try:
        with open(tmp, "xb") as fh:
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
        # ponytail: a POSIX rename replaces a target that appeared since exists(); use os.link off Windows
        os.rename(tmp, path)
    except FileExistsError:                            # Windows: `path` appeared since the check (write-once)
        tmp.unlink(missing_ok=True)
        return False
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise
    return True


def _calendar_files(raw: bytes) -> list[tuple[str, bytes]]:
    """A calendar stream back into its (name, bytes) files; ValueError unless it is one."""
    parts = raw.split(b"\0")
    if len(parts) < 3 or len(parts) % 2 == 0 or parts[-1] != b"":
        raise ValueError("store: not a calendar stream")
    files = [(parts[i].decode("utf-8"), parts[i + 1]) for i in range(0, len(parts) - 1, 2)]
    names = [name for name, _ in files]
    if names != sorted(set(names)) or any(name in ("", ".", "..") or Path(name).name != name for name in names):
        raise ValueError("store: calendar file names must be plain, unique and sorted")
    return files


def store_put(kind: str, raw: bytes, anchor: tuple[int, str]) -> str:
    """Copies approved bytes into the write-once store under their sha256 and returns it: <kind>/<sha256>.yaml,
    or the directory calendar/<sha256>/ (then `raw` is rules.calendar_stream of the set), plus <kind>/<sha256>.anchor.json
    holding the approval's owner-log anchor. Stored bytes never change: other bytes under the same name are an
    error. An existing anchor is kept, since it already anchors an earlier approval of the same bytes (P34)."""
    if kind not in APPROVAL_KINDS:
        raise ValueError(f"store: unknown kind {kind!r}")
    if not isinstance(raw, bytes):
        raise TypeError("store: raw must be bytes")
    seq, row_sha256 = anchor
    if isinstance(seq, bool) or not isinstance(seq, int) or seq < 1 or not _hex64(row_sha256):
        raise ValueError("store: the anchor must be (seq >= 1, row_sha256)")
    sha = model.sha256_hex(raw)
    base = store_dir() / kind
    blobs = ([(base / sha / name, data) for name, data in _calendar_files(raw)] if kind == "calendar"
             else [(base / f"{sha}.yaml", raw)])
    for path, data in blobs:
        if not _write_new(path, data) and path.read_bytes() != data:
            raise RuntimeError(f"store: {kind}/{path.relative_to(base).as_posix()} exists with other bytes")
    _write_new(base / f"{sha}.anchor.json",
               model.canonical_json({"seq": seq, "row_sha256": row_sha256}).encode("utf-8"))
    return sha


def store_get(kind: str, sha256: str) -> bytes | None:
    """The stored bytes named `sha256`, or None when they are missing, unreadable, hold a link (a calendar set) or no
    longer hash to their name."""
    if kind not in APPROVAL_KINDS or not _hex64(sha256):
        return None
    path = store_dir() / kind / (sha256 if kind == "calendar" else f"{sha256}.yaml")
    try:
        raw = rules.calendar_stream(path) if kind == "calendar" else path.read_bytes()
    except (OSError, rules.Invalid):
        return None
    return raw if model.sha256_hex(raw) == sha256 else None


def _binds(tree: ast.AST, name: str) -> int:
    """How many times `name` is bound anywhere in `tree`, at any depth: by an import, an assignment of any kind, a
    def or class, a parameter, an except-as or a match capture (a keyword argument of that name counts too, which
    only makes callers scan more)."""
    count = 0
    for n in ast.walk(tree):
        if isinstance(n, ast.alias):
            bound = n.asname or n.name.split(".")[0]
        elif isinstance(n, ast.Name):
            bound = n.id if not isinstance(n.ctx, ast.Load) else None
        else:
            bound = getattr(n, "name", None) or getattr(n, "arg", None) or getattr(n, "rest", None)
        count += bound == name
    return count


def _typing_flag(tree: ast.AST) -> bool:
    """True when the bare name TYPE_CHECKING in `tree` is the one from `from typing import TYPE_CHECKING` and is
    never bound anywhere else; a local `TYPE_CHECKING = True` is code that runs (P6)."""
    imported = any(isinstance(n, ast.ImportFrom) and n.level == 0 and n.module == "typing"
                   and any(a.name == "TYPE_CHECKING" and a.asname is None for a in n.names)
                   for n in ast.walk(tree))
    return imported and _binds(tree, "TYPE_CHECKING") == 1


def _guards(tree: ast.AST) -> tuple[bool, bool, bool]:
    """Which `if` guards of `tree` may skip their body (P6, R4): (bare TYPE_CHECKING, typing.TYPE_CHECKING,
    __name__ == "__main__"). The bare name needs _typing_flag; `typing.` needs `typing` bound exactly once, by a
    plain `import typing`; the `__main__` test needs `__name__` bound nowhere in the module. A rebound name
    (typing = SimpleNamespace(TYPE_CHECKING=True), __name__ = "__main__") loses its guard, and a module that can
    change these names without binding them (an attribute store of TYPE_CHECKING or __name__, or any setattr,
    delattr, globals, vars, locals, modules, __dict__, builtins, __builtins__, f_globals or f_locals) trusts no
    guard: the guarded body is scanned. Not seen: another module changing typing.TYPE_CHECKING first (the review of
    each hashed diff)."""
    plain = any(isinstance(n, ast.Import) and any(a.name == "typing" and a.asname is None for a in n.names)
                for n in ast.walk(tree))
    routes = {"setattr", "delattr", "globals", "vars", "locals", "modules", "__dict__", "builtins", "__builtins__",
              "f_globals", "f_locals"}
    if any((isinstance(n, ast.Name) and n.id in routes) or (isinstance(n, ast.Attribute) and (n.attr in routes or (
            n.attr in ("TYPE_CHECKING", "__name__") and not isinstance(n.ctx, ast.Load)))) for n in ast.walk(tree)):
        return False, False, False
    return _typing_flag(tree), plain and _binds(tree, "typing") == 1, _binds(tree, "__name__") == 0


def _skipped(node: ast.AST, guards: tuple[bool, bool, bool]) -> bool:
    """Whether `node` is an `if` whose body never runs at import and so is outside the code closure (P6):
    `if TYPE_CHECKING:`, `if typing.TYPE_CHECKING:` and a single `==` comparison of `__name__` with "__main__" in
    either order, each only while `guards` (see _guards) trusts its name. Every other test (`!=`, `not
    TYPE_CHECKING`, a local or rebound name) is scanned, since its body can run at import."""
    if not isinstance(node, ast.If):
        return False
    bare, dotted, main = guards
    t = node.test
    if isinstance(t, ast.Name):
        return t.id == "TYPE_CHECKING" and bare
    if isinstance(t, ast.Attribute):
        return dotted and t.attr == "TYPE_CHECKING" and isinstance(t.value, ast.Name) and t.value.id == "typing"
    if isinstance(t, ast.Compare) and len(t.ops) == 1 and isinstance(t.ops[0], ast.Eq):
        sides = [t.left, *t.comparators]
        return (main and any(isinstance(s, ast.Name) and s.id == "__name__" for s in sides)
                and any(isinstance(s, ast.Constant) and s.value == "__main__" for s in sides))
    return False


def _import_nodes(node: ast.AST, guards: tuple[bool, bool, bool]):
    """Every import statement at any depth, function bodies included; a skipped `if` keeps its `else`."""
    if _skipped(node, guards):
        for child in node.orelse:
            yield from _import_nodes(child, guards)
        return
    if isinstance(node, (ast.Import, ast.ImportFrom)):
        yield node
    for child in ast.iter_child_nodes(node):
        yield from _import_nodes(child, guards)


def _module_file(root: Path, dotted: str) -> Path | None:
    """The repo file of an in-repo module name; None for stdlib, third-party and attribute names."""
    parts = dotted.split(".")
    if not all(part.isidentifier() for part in parts):
        return None
    for candidate in (root.joinpath(*parts[:-1], parts[-1] + ".py"), root.joinpath(*parts, "__init__.py")):
        if candidate.is_file():
            return candidate
    return None


def _repo_imports(root: Path, path: Path) -> set[Path]:
    """The in-repo files `path` imports, relative imports resolved against its package."""
    package = list(path.relative_to(root).parent.parts)
    names: set[str] = set()
    tree = ast.parse(path.read_bytes())
    for node in _import_nodes(tree, _guards(tree)):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
            continue
        base = package[:len(package) - node.level + 1] if node.level else []
        module = ".".join(base + ([node.module] if node.module else []))
        if module:
            names.add(module)
            names.update(f"{module}.{alias.name}" for alias in node.names)
    return {f for name in names if (f := _module_file(root, name)) is not None}


def code_files(repo_root: Path) -> list[tuple[str, str]]:
    """Sorted (relative POSIX path, sha256) of the D14 code closure (P6): core/compliance/*.py and core/odds/*.py,
    every in-repo file they import at any depth, every ancestor package __init__.py, and the RECORD files of the
    cryptography and PyYAML installs of the running interpreter as venv:<dist>-<version>.dist-info/RECORD (absent
    when not installed)."""
    root = Path(repo_root)
    todo = [p for sub in ("compliance", "odds") for p in sorted((root / "core" / sub).glob("*.py"))]
    seen: set[Path] = set()
    while todo:
        path = todo.pop()
        if path in seen:
            continue
        seen.add(path)
        todo.extend(_repo_imports(root, path))
        todo.extend(d / "__init__.py" for d in path.parents
                    if d != root and d.is_relative_to(root) and (d / "__init__.py").is_file())
    out = {p.relative_to(root).as_posix(): model.sha256_hex(p.read_bytes()) for p in seen}
    for name in _RECORD_DISTS:
        try:
            dist = importlib.metadata.distribution(name)
        except importlib.metadata.PackageNotFoundError:
            continue
        record = next((f for f in dist.files or () if f.name == "RECORD" and f.parent.name.endswith(".dist-info")),
                      None)
        if record is not None:
            out[f"venv:{name}-{dist.version}.dist-info/RECORD"] = model.sha256_hex(Path(record.locate()).read_bytes())
    return sorted(out.items())


def code_hash(repo_root: Path) -> str:
    """The D14 code hash the owner signs as code_approved: sha256 of the canonical JSON of code_files."""
    return model.sha256_hex(model.canonical_json(code_files(repo_root)))


def write_snapshot(state: model.ApprovedState, head: tuple[int, str]) -> Path:
    """Keeps a verified approved state for D11 recovery as snapshots/<seq:08d>-<state_hash[:16]>.json: the
    in-force hashes (their bytes stay in the store) and the owner-log head, which read_anchors uses as an anchor.
    Written once: a snapshot of the same state keeps its first head (P34); one with other content is an error."""
    if not state.valid:
        raise ValueError("snapshot: only a valid approved state is kept")
    body = {"state_seq": state.seq, "state_hash": state.state_hash, "hashes": dict(state.hashes)}
    path = snapshots_dir() / f"{state.seq:08d}-{state.state_hash[:16]}.json"
    if not _write_new(path, model.canonical_json({**body, "head": list(head)}).encode("utf-8")):
        try:
            kept = json.loads(path.read_bytes())
        except ValueError:
            kept = None
        if not isinstance(kept, dict) or {k: kept.get(k) for k in body} != body:
            raise RuntimeError(f"snapshot: {path.name} exists with other content")
    return path


def _stored_history(current: str, below_seq: int) -> tuple[bytes, ...]:
    """Earlier approved instrument maps from the store (anchor seq below `below_seq`), newest first: the exit
    fallback of spec 6.2 step 0 when the log cannot be read."""
    found = []
    for anchor in sorted((store_dir() / "instruments").glob("*.anchor.json")):
        sha = anchor.name[:-len(".anchor.json")]
        try:
            seq = json.loads(anchor.read_bytes())["seq"]
        except (OSError, ValueError, KeyError, TypeError):
            continue
        if sha != current and isinstance(seq, int) and seq < below_seq:
            raw = store_get("instruments", sha)
            if raw is not None:
                found.append((seq, raw))
    return tuple(raw for _, raw in sorted(found, key=lambda t: t[0], reverse=True))


def latest_snapshot() -> model.ApprovedState | None:
    """The newest snapshot (by name, so highest seq) whose stored bytes are intact, rebuilt; None when there is
    none. Never raises: a malformed or unreadable file is skipped, and a refused state root (A0) gives None."""
    try:
        paths = sorted(snapshots_dir().glob("*.json"), key=lambda p: p.name, reverse=True)
    except (OSError, RuntimeError):                    # RuntimeError: the state root holds a link (A0)
        return None
    for path in paths:
        try:
            snap = json.loads(path.read_bytes())
            if not (isinstance(snap, dict) and isinstance(snap.get("hashes"), dict)):
                continue
            seq, hashes = snap.get("state_seq"), snap["hashes"]
            if isinstance(seq, bool) or not isinstance(seq, int):
                continue
            raws = [store_get(kind, hashes.get(kind)) for kind in _TABLES]
            if None in raws:
                continue
            state = rules.approved_state(*raws, seq=seq, history_raws=_stored_history(hashes["instruments"], seq))
            if (state.valid and state.state_hash == snap.get("state_hash")
                    and path.name == f"{seq:08d}-{state.state_hash[:16]}.json"):
                return state
        except (OSError, ValueError, RuntimeError):     # RuntimeError: RecursionError or an A0 refusal
            continue
    return None


# --------------------------------------------------------------------------- #
# load_context (Task 13): the only producer of Context (spec 6.4; P19, P20, P24)
# --------------------------------------------------------------------------- #
import math  # noqa: E402
from collections.abc import Mapping  # noqa: E402
from types import MappingProxyType  # noqa: E402

_CRYPTOGRAPHY_MISSING = "cryptography missing: install it (Task 10)"    # verify_log's text too (Task 11)
_EMPTY = MappingProxyType({})


def _amount(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value >= 0


def _amounts(mapping, key_ok) -> bool:
    return isinstance(mapping, Mapping) and all(key_ok(k) and _amount(v) for k, v in mapping.items())


def _venue_symbol(key) -> bool:
    return isinstance(key, tuple) and len(key) == 2 and all(isinstance(part, str) for part in key)


def _text_key(key) -> bool:
    return isinstance(key, str)


def _positions_problem(positions) -> str:
    """"" when `positions` is a Positions of finite amounts >= 0 with equity > 0 (P19), else the field at fault."""
    if not isinstance(positions, model.Positions):
        return "not a Positions"
    if not _amount(positions.equity_krw) or positions.equity_krw <= 0:
        return "equity_krw"
    for name in ("holdings", "shorts"):
        if not _amounts(getattr(positions, name), _venue_symbol):
            return name
    if not isinstance(positions.exposure, Mapping):
        return "exposure"
    for venue, held in positions.exposure.items():
        if not (isinstance(venue, str) and isinstance(held, model.Exposure) and _amount(held.held_krw)
                and _amounts(held.reservations, _text_key) and _amounts(held.promised_sell_units, _text_key)):
            return "exposure"
    return ""


def _frozen(mapping: Mapping) -> Mapping:
    """A read-only copy, so the caller cannot change what a sealed context holds after ctx_hash was taken."""
    return MappingProxyType({k: float(v) for k, v in mapping.items()})


def _first_recorded() -> tuple[str, str] | None:
    """(fingerprint, utc) of the first alerts.jsonl row that records a fingerprint (P20), or None."""
    for row in _alert_rows():
        if isinstance(row.get("fingerprint"), str) and row["fingerprint"]:
            return row["fingerprint"], str(row.get("utc", ""))
    return None


def _owner_now(day: _dt.date, now_utc: str, session_id: str | None) -> tuple[model.OwnerState, LogCheck | None]:
    """The owner state, and the log check behind it, against the repo public key. A missing cryptography package
    is reported first (spec 6.4), then a missing key (P24); every unreadable input is BROKEN saying why."""
    try:
        import cryptography.hazmat.primitives.asymmetric.ed25519  # noqa: F401  (a lazy probe, never module level)
    except ImportError:
        return model.OwnerState.broken(_CRYPTOGRAPHY_MISSING), None
    if not PUBKEY_PATH.is_file():
        return model.OwnerState.broken("no owner key yet: owner act 1"), None
    try:
        pubkey_raw = read_pubkey(PUBKEY_PATH)
    except ImportError:
        return model.OwnerState.broken(_CRYPTOGRAPHY_MISSING), None
    except Exception as exc:                            # unreadable, or not an Ed25519 public key
        return model.OwnerState.broken(f"owner key unreadable ({type(exc).__name__})"), None
    fp = fingerprint(pubkey_raw)
    try:
        anchors, lines, first = read_anchors(), _log_lines(log_path()), _first_recorded()
    except (OSError, ValueError, RuntimeError) as exc:  # RuntimeError: an A0 link refusal naming the entry
        return model.OwnerState.broken(f"owner log unreadable: {exc}", fingerprint=fp), None
    check = verify_log(lines, pubkey_raw, anchors)
    state = owner_state(check, date=day, now_utc=now_utc, session_id=session_id, fingerprint_now=fp,
                        first_recorded=first)
    return state, check


def _approved_now(check: LogCheck) -> model.ApprovedState:
    """The tables named by the latest signed approvals, with their bytes from the store (spec 5.2)."""
    approvals = in_force(check)
    raws = {}
    for kind in _TABLES:
        if kind not in approvals:
            return model.ApprovedState.invalid(f"unapproved: no signed approval for {kind}")
        raws[kind] = store_get(kind, approvals[kind][0])
        if raws[kind] is None:
            return model.ApprovedState.invalid(f"store: {kind} {approvals[kind][0][:12]} missing or altered")
    current = approvals["instruments"][0]
    earlier = tuple(raw for sha, _ in history(check, "instruments")
                    if sha != current and (raw := store_get("instruments", sha)) is not None)
    return rules.approved_state(raws["rules"], raws["instruments"], raws["venues"],
                                seq=max(approvals[kind][1] for kind in _TABLES), history_raws=earlier)


def load_context(now: _dt.datetime, positions: model.Positions, *, session_id: str | None = None) -> model.Context:
    """The only producer of Context (spec 6.4). Hashes the code on disk, verifies the owner log against the repo
    public key, loads the in-force tables from the store, snapshots a good state and reads the latest snapshot.
    `positions` is the caller's (P19): validated, copied read-only, then hashed into ctx_hash. Never raises, except
    ValueError for a naive or out-of-range `now`; anything else fails closed: nothing in force, nothing signed,
    owner state BROKEN."""
    if not isinstance(now, _dt.datetime):
        raise ValueError(f"load_context: now must be an aware datetime, got {now!r}")
    try:
        now_utc = model.iso_utc(now)                   # ValueError on a naive datetime
        day = now.astimezone(model.KST).date()
    except OverflowError:
        raise ValueError(f"load_context: now is out of range, got {now!r}") from None
    try:
        return _context(day, now_utc, positions, session_id)
    except Exception as exc:
        why = f"load_context: internal error {type(exc).__name__}"
        return model.seal_context(date=day, active=model.ApprovedState.invalid(why), snapshot=None,
                                  owner=model.OwnerState.broken(why), code_hash="", code_signed=False,
                                  session=model.SessionState(), equity_krw=0.0, holdings=_EMPTY, shorts=_EMPTY,
                                  exposure=_EMPTY)


def _context(day: _dt.date, now_utc: str, positions, session_id) -> model.Context:
    if session_id is not None and not (isinstance(session_id, str) and session_id):
        raise TypeError("session_id must be None or a non-empty string")
    owner, check = _owner_now(day, now_utc, session_id)
    check = _up_to(check, now_utc) if check is not None else None
    active = _approved_now(check) if owner.ok else model.ApprovedState.invalid(f"owner log: {owner.reason}")
    try:
        current = code_hash(REPO_ROOT)
    except (OSError, SyntaxError, ValueError):
        current = ""
    signed = owner.ok and bool(current) and code_approval(check) == current
    if active.valid:
        try:
            write_snapshot(active, owner.head)
        except (OSError, RuntimeError, ValueError) as exc:
            active = model.ApprovedState.invalid(f"snapshot: {exc}")
    snapshot = latest_snapshot()
    problem = _positions_problem(positions)
    if problem:
        active, snapshot = model.ApprovedState.invalid(f"positions: {problem}"), None
        equity, holdings, shorts, exposure = 0.0, _EMPTY, _EMPTY, _EMPTY
    else:
        equity, holdings, shorts = float(positions.equity_krw), _frozen(positions.holdings), _frozen(positions.shorts)
        exposure = MappingProxyType({
            venue: model.Exposure(held_krw=float(e.held_krw), reservations=_frozen(e.reservations),
                                  promised_sell_units=_frozen(e.promised_sell_units))
            for venue, e in positions.exposure.items()})
    return model.seal_context(
        date=day, active=active, snapshot=snapshot, owner=owner, code_hash=current, code_signed=signed,
        session=model.SessionState(session_id=session_id, armed=session_id in owner.armed_sessions),
        equity_krw=equity, holdings=holdings, shorts=shorts, exposure=exposure)
