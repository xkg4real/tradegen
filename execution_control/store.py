"""Checked, durable control journal with a separately persisted tail anchor.

The journal validates structure; the controller validates lifecycle and trading
semantics. An interrupted append is never repaired or silently discarded. A
journal ahead of its checkpoint, a truncated tail, or a missing anchor refuses
the next transaction. No writable local hash chain authenticates a malicious
process able to replace both the entire journal and its anchor.
"""
from __future__ import annotations

from collections.abc import Mapping
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import threading

from core.isolation import checked_target, state_root

SCHEMA = 1
GENESIS = "0" * 64
EVENT_KINDS = frozenset({"session_prepared", "reserved", "dispatching", "acknowledged", "rejected", "unknown",
                       "expired", "cancelled_local", "cancel_requested", "reconciled", "fill", "risk_snapshot",
                       "kill", "halt"})
MAX_ROW_BYTES = 262_144
MAX_JOURNAL_BYTES = 67_108_864
MAX_EVENTS = 100_000
_ROW_KEYS = frozenset({"schema", "seq", "prev_sha256", "kind", "utc", "data", "row_sha256"})
_ANCHOR_KEYS = frozenset({"schema", "seq", "head_sha256", "journal_bytes"})
_HASH = re.compile(r"[0-9a-f]{64}")
_STAMP = re.compile(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{6}Z")
_PROCESS_LOCK = threading.Lock()
_THREAD = threading.local()


class JournalError(RuntimeError):
    """A sanitized structural, path or durability refusal; damaged files remain."""


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                      allow_nan=False).encode("ascii")


def _copy_primitive(value: object, depth: int = 0, count: list | None = None):
    count = [0] if count is None else count
    count[0] += 1
    if depth > 16 or count[0] > 8192:
        raise JournalError("control payload exceeds structural limits")
    if value is None or type(value) is bool:
        return value
    if type(value) is int:
        if -(2 ** 63) <= value < 2 ** 63:
            return value
        raise JournalError("control payload integer out of range")
    if type(value) is str:
        if len(value) <= 4096:
            return value
        raise JournalError("control payload string too long")
    if type(value) is list:
        return [_copy_primitive(item, depth + 1, count) for item in value]
    if isinstance(value, Mapping):
        if len(value) > 512:
            raise JournalError("control payload mapping too large")
        out = {}
        for key, item in value.items():
            if type(key) is not str or not key or len(key) > 128:
                raise JournalError("control payload key invalid")
            if key in out:
                raise JournalError("duplicate control payload key")
            out[key] = _copy_primitive(item, depth + 1, count)
        return out
    raise JournalError("control payload is not a JSON primitive")


def _pairs(items: list) -> dict:
    out = {}
    for key, value in items:
        if key in out:
            raise JournalError("duplicate control JSON key")
        out[key] = value
    return out


def _decode(raw: bytes) -> dict:
    if not raw.endswith(b"\n") or b"\n" in raw[:-1] or b"\r" in raw or len(raw) > MAX_ROW_BYTES:
        raise JournalError("control record is not one bounded complete line")
    try:
        obj = json.loads(raw[:-1].decode("ascii"), object_pairs_hook=_pairs)
        if type(obj) is not dict or _canonical(obj) + b"\n" != raw:
            raise JournalError("control record is not canonical")
        return obj
    except (ValueError, TypeError, RecursionError, UnicodeError):
        raise JournalError("control record cannot be decoded") from None


def _utc(now: datetime) -> str:
    if type(now) is not datetime or now.utcoffset() is None:
        raise JournalError("control timestamp must be aware")
    try:
        return now.astimezone(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")
    except (ValueError, OverflowError):
        raise JournalError("control timestamp invalid") from None


def _valid_stamp(value: object) -> bool:
    if type(value) is not str or _STAMP.fullmatch(value) is None:
        return False
    try:
        return _utc(datetime.fromisoformat(value)) == value
    except (ValueError, JournalError):
        return False


def _hash(value: object) -> bool:
    return type(value) is str and _HASH.fullmatch(value) is not None


def _sync_directory(path: Path) -> None:
    if os.name == "nt":
        return  # Windows has no portable directory fsync; file handles still flush/fsync.
    descriptor = os.open(checked_target(path, "control directory"), os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _lock(fh, acquire: bool) -> None:
    fh.seek(0)
    if os.name == "nt":
        import msvcrt
        msvcrt.locking(fh.fileno(), msvcrt.LK_LOCK if acquire else msvcrt.LK_UNLCK, 1)
    else:
        import fcntl
        fcntl.flock(fh, fcntl.LOCK_EX if acquire else fcntl.LOCK_UN)


class Journal:
    def __init__(self, root: Path | None = None):
        try:
            self._base = state_root().absolute()
            self._root = Path(root).absolute() if root is not None else self._base / "execution-control"
            if self._root == self._base:
                raise JournalError("control journal requires its own directory")
            self._check_paths()
        except (OSError, RuntimeError, ValueError, TypeError):
            raise JournalError("control state path refused") from None

    def _check_paths(self) -> None:
        checked_target(self._root, "control directory", within=self._base)
        for path in (self._root, *self._root.parents):
            checked_target(path, "control ancestor")
            if path == self._base:
                break
        for name in ("control.lock", "journal.jsonl", "checkpoint.json"):
            checked_target(self._root / name, "control state file", within=self._root)

    def _read(self, name: str, maximum: int) -> bytes:
        with open(checked_target(self._root / name, "control state file", within=self._root), "rb") as fh:
            raw = fh.read(maximum + 1)
        if len(raw) > maximum:
            raise JournalError("control state exceeds size limit")
        return raw

    def _anchor(self, seq: int, head: str, size: int) -> None:
        body = {"schema": SCHEMA, "seq": seq, "head_sha256": head, "journal_bytes": size}
        temp = self._root / (".checkpoint." + os.urandom(12).hex() + ".tmp")
        with open(checked_target(temp, "control checkpoint temporary", within=self._root), "xb") as fh:
            fh.write(_canonical(body) + b"\n")
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(checked_target(temp, "control checkpoint temporary", within=self._root),
                   checked_target(self._root / "checkpoint.json", "control checkpoint", within=self._root))
        _sync_directory(self._root)

    def _load(self) -> tuple[list[dict], int]:
        journal = self._root / "journal.jsonl"
        anchor = self._root / "checkpoint.json"
        if not journal.exists() and not anchor.exists():
            # Only a genuinely empty pair is initialized. A partial first write is a refusal.
            with open(checked_target(journal, "control journal", within=self._root), "xb") as fh:
                fh.flush()
                os.fsync(fh.fileno())
            _sync_directory(self._root)
            self._anchor(0, GENESIS, 0)
        if not journal.is_file() or not anchor.is_file():
            raise JournalError("control journal or checkpoint missing")
        raw = self._read("journal.jsonl", MAX_JOURNAL_BYTES)
        checkpoint = _decode(self._read("checkpoint.json", 4096))
        if (set(checkpoint) != _ANCHOR_KEYS or type(checkpoint["schema"]) is not int
                or checkpoint["schema"] != SCHEMA or type(checkpoint["seq"]) is not int
                or not 0 <= checkpoint["seq"] <= MAX_EVENTS
                or type(checkpoint["journal_bytes"]) is not int or checkpoint["journal_bytes"] != len(raw)
                or not _hash(checkpoint["head_sha256"])):
            raise JournalError("control checkpoint invalid")
        if raw and not raw.endswith(b"\n"):
            raise JournalError("control journal has torn tail")
        rows, previous = [], GENESIS
        for sequence, line in enumerate(raw.splitlines(keepends=True), start=1):
            if sequence > MAX_EVENTS:
                raise JournalError("control event limit exceeded")
            row = _decode(line)
            if (set(row) != _ROW_KEYS or type(row["schema"]) is not int or row["schema"] != SCHEMA
                    or type(row["seq"]) is not int or row["seq"] != sequence
                    or row["prev_sha256"] != previous or type(row["kind"]) is not str
                    or row["kind"] not in EVENT_KINDS or not _valid_stamp(row["utc"])
                    or type(row["data"]) is not dict or not _hash(row["row_sha256"])):
                raise JournalError("control journal row invalid")
            data = _copy_primitive(row["data"])
            if _canonical(data) != _canonical(row["data"]):
                raise JournalError("control payload invalid")
            body = {key: value for key, value in row.items() if key != "row_sha256"}
            digest = hashlib.sha256(_canonical(body)).hexdigest()
            if digest != row["row_sha256"]:
                raise JournalError("control journal hash mismatch")
            rows.append(row)
            previous = digest
        if checkpoint["seq"] != len(rows) or checkpoint["head_sha256"] != previous:
            raise JournalError("control journal checkpoint mismatch")
        return rows, len(raw)

    @contextmanager
    def transaction(self):
        if getattr(_THREAD, "active", False):
            raise JournalError("nested control transaction refused")
        tx = None
        entered = False
        with _PROCESS_LOCK:
            _THREAD.active = True
            try:
                self._check_paths()
                checked_target(self._root, "control directory", within=self._base).mkdir(parents=True, exist_ok=True)
                with open(checked_target(self._root / "control.lock", "control lock", within=self._root), "a+b") as fh:
                    _lock(fh, True)
                    try:
                        rows, size = self._load()
                        tx = Transaction(self, rows, size)
                        _THREAD.transaction = tx
                        entered = True
                        yield tx
                    finally:
                        if tx is not None:
                            tx._active = False
                        _THREAD.transaction = None
                        _lock(fh, False)
            except JournalError:
                raise
            except (OSError, RuntimeError, ValueError, TypeError, RecursionError):
                if entered:
                    raise  # The caller's business rejection is not journal corruption.
                raise JournalError("control transaction refused") from None
            finally:
                _THREAD.active = False
                _THREAD.transaction = None


class Transaction:
    def __init__(self, journal: Journal, rows: list[dict], size: int):
        self._journal, self._rows, self._size = journal, rows, size
        self._active = True

    def _require_active(self) -> None:
        if not self._active or getattr(_THREAD, "transaction", None) is not self:
            raise JournalError("control transaction is closed or failed")

    @property
    def events(self) -> tuple[dict, ...]:
        self._require_active()
        return tuple(json.loads(_canonical(row)) for row in self._rows)

    def append(self, kind: str, data: Mapping, *, now: datetime) -> dict:
        self._require_active()
        if type(kind) is not str or kind not in EVENT_KINDS or not isinstance(data, Mapping):
            raise JournalError("control event kind or payload invalid")
        payload = _copy_primitive(data)
        utc = _utc(now)
        previous = self._rows[-1]["row_sha256"] if self._rows else GENESIS
        body = {"schema": SCHEMA, "seq": len(self._rows) + 1, "prev_sha256": previous,
                "kind": kind, "utc": utc, "data": payload}
        row = {**body, "row_sha256": hashlib.sha256(_canonical(body)).hexdigest()}
        line = _canonical(row) + b"\n"
        if len(line) > MAX_ROW_BYTES or self._size + len(line) > MAX_JOURNAL_BYTES or len(self._rows) >= MAX_EVENTS:
            raise JournalError("control append exceeds size limit")
        try:
            self._journal._check_paths()
            rows, size = self._journal._load()
            if size != self._size or rows != self._rows:
                raise JournalError("control state changed during transaction")
            with open(checked_target(self._journal._root / "journal.jsonl", "control journal",
                                     within=self._journal._root), "ab") as fh:
                if fh.write(line) != len(line):
                    raise JournalError("control append incomplete")
                fh.flush()
                os.fsync(fh.fileno())
            self._journal._anchor(row["seq"], row["row_sha256"], size + len(line))
        except (OSError, RuntimeError, ValueError, TypeError):
            self._active = False
            raise JournalError("control append failed; reconciliation required") from None
        self._rows.append(row)
        self._size += len(line)
        return json.loads(_canonical(row))
