"""Independent recovery-attempt journal, exact row backups and retained head.

Route/attempt/result data does not grant source authenticity, approval, recovery
completion or quarantine release. Runtime never seeds/adopts a head, repairs a
torn append, truncates history or replaces a version. Provisioning is explicit.

A separate operation lock serializes a whole controller run while session/head
locks are held only during each store call. Do not acquire the operation lock
while retaining a session/head lock. Root pins and bounded decoding reuse the
reviewed incident-store primitives; this store owns its domain, format, chain,
configuration, diagnostics and locks. Windows native and power-loss behavior
remain unverified; three paths alone do not prove separate backup media or
protect against coherent rollback of every independent root by the same user.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import asdict, dataclass, fields
import hashlib
import json
import os
from pathlib import Path
import re
from threading import Lock, get_ident

from core.isolation import checked_target, state_root
from execution_launch.baseline_head import BaselineHead
from execution_launch import research_recovery_attempts as F
from execution_launch.research_incident_store import (
    IncidentStoreError, _Pins, _canonical, _decode as _bounded_decode,
    _directory, _file, _hash, _identity, _stamp, _FLAGS,
)

_DOMAIN = b"TRADEGEN-RESEARCH-RECOVERY-STORE-v1\x00"
_NAME = re.compile(r"[a-z][a-z0-9-]{0,63}")
_REPO = Path(__file__).resolve().parents[1]
_LOCK = Lock()
_OPERATION_LOCK = Lock()
_ROW_KEYS = frozenset({"schema", "sequence", "previous_sha256", "context_sha256", "event", "row_sha256"})


class RecoveryStoreError(ValueError):
    """Fixed RECOVERY_STORE_* diagnostics, without private paths or OS text."""


def _need(ok, code):
    if not ok:
        raise RecoveryStoreError(code)


def _digest(kind, body):
    return hashlib.sha256(_DOMAIN + kind.encode("ascii") + b"\x00" + _canonical(body)).hexdigest()


def _decode(raw, maximum):
    try:
        return _bounded_decode(raw, maximum)
    except IncidentStoreError as exc:
        code = ("RECOVERY_STORE_RECORD_LIMIT_EXCEEDED"
                if str(exc) == "INCIDENT_STORE_RECORD_LIMIT_EXCEEDED"
                else "RECOVERY_STORE_RECORD_INVALID")
        raise RecoveryStoreError(code) from None


@dataclass(frozen=True, kw_only=True)
class RecoveryStoreLimits:
    format_limits: F.RecoveryAttemptLimits
    max_journal_bytes: int = 128 * 1024 * 1024
    max_records: int = 16384

    def __post_init__(self):
        try:
            _need(type(self.format_limits) is F.RecoveryAttemptLimits, "RECOVERY_STORE_LIMITS_INVALID")
            _need(F.RecoveryAttemptLimits(**asdict(self.format_limits)) == self.format_limits,
                  "RECOVERY_STORE_LIMITS_INVALID")
            _need(type(self.max_journal_bytes) is int and 1 <= self.max_journal_bytes <= 128 * 1024 * 1024
                  and type(self.max_records) is int and 1 <= self.max_records <= 16384,
                  "RECOVERY_STORE_LIMITS_INVALID")
        except RecoveryStoreError:
            raise
        except (ValueError, TypeError, AttributeError, RecursionError):
            raise RecoveryStoreError("RECOVERY_STORE_LIMITS_INVALID") from None


def limits_bytes(limits: RecoveryStoreLimits) -> bytes:
    try:
        _need(type(limits) is RecoveryStoreLimits, "RECOVERY_STORE_LIMITS_INVALID")
        limits.__post_init__()
        return _canonical(asdict(limits))
    except RecoveryStoreError:
        raise
    except (ValueError, TypeError, AttributeError, RecursionError):
        raise RecoveryStoreError("RECOVERY_STORE_LIMITS_INVALID") from None


def parse_limits(raw: bytes) -> RecoveryStoreLimits:
    try:
        body = _decode(raw, 8192)
        _need(set(body) == {field.name for field in fields(RecoveryStoreLimits)}
              and type(body["format_limits"]) is dict
              and set(body["format_limits"]) == {field.name for field in fields(F.RecoveryAttemptLimits)},
              "RECOVERY_STORE_LIMITS_INVALID")
        value = RecoveryStoreLimits(format_limits=F.RecoveryAttemptLimits(**body["format_limits"]),
            max_journal_bytes=body["max_journal_bytes"], max_records=body["max_records"])
        _need(limits_bytes(value) == raw, "RECOVERY_STORE_LIMITS_INVALID")
        return value
    except RecoveryStoreError:
        raise
    except (ValueError, TypeError, KeyError, AttributeError, RecursionError):
        raise RecoveryStoreError("RECOVERY_STORE_LIMITS_INVALID") from None


@dataclass(frozen=True, kw_only=True)
class RecoveryStoreSnapshot:
    state: object
    head: str
    sequence: int

    @property
    def execution_ready(self):
        return False


class _RecoveryChain:
    def __init__(self, store):
        self.store = store

    def seed(self, digest):
        store = self.store
        _need(digest == store.genesis_digest, "RECOVERY_STORE_GENESIS_REQUIRED")
        with store._pinned(head_required=False) as pins:
            snapshot, _, _, _ = store._replay(pins)
            _need(snapshot.sequence == 0 and snapshot.head == digest, "RECOVERY_STORE_GENESIS_REQUIRED")
        return 0

    def successor(self, old, new):
        with self.store._pinned() as pins:
            snapshot, _, previous, _ = self.store._replay(pins)
            _need(snapshot.head == new and previous == old, "RECOVERY_STORE_DIRECT_SUCCESSOR_REQUIRED")
            return snapshot.sequence


class RecoveryAttemptStore:
    def __init__(self, *, root: Path, backup_root: Path, head_root: Path,
                 head_name: str, limits: RecoveryStoreLimits):
        _need(all(isinstance(p, Path) and p.is_absolute() and ".." not in p.parts
                  for p in (root, backup_root, head_root)), "RECOVERY_STORE_EXPLICIT_ROOTS_REQUIRED")
        _need(type(head_name) is str and _NAME.fullmatch(head_name) is not None,
              "RECOVERY_STORE_HEAD_NAME_INVALID")
        self.root, self.backup_root, self.head_root = root, backup_root, head_root
        self.limits, self._head_name = limits, head_name
        self._roots = (root, backup_root, head_root)
        self._limits_bytes = limits_bytes(limits)
        self.context_sha256 = _digest("context", {"schema": 1, "head_name": head_name,
                                                  "limits": json.loads(self._limits_bytes)})
        self.genesis_digest = _digest("genesis", {"context_sha256": self.context_sha256})
        self._paths(prepared=False)
        try:
            self._root_ids = tuple(_directory(os.lstat(p)) for p in self._roots)
            _need(len(set(self._root_ids)) == 3, "RECOVERY_STORE_ROOT_OVERLAP")
            self._chain = _RecoveryChain(self)
            self.head = BaselineHead(root=head_root, name=head_name, chain=self._chain)
        except RecoveryStoreError:
            raise
        except (OSError, ValueError, RuntimeError, TypeError):
            raise RecoveryStoreError("RECOVERY_STORE_CONSTRUCTION_REFUSED") from None
        self._fixed_head = self.head
        self._operation_state = None

    def _configuration(self):
        _need((self.root, self.backup_root, self.head_root) == self._roots
              and limits_bytes(self.limits) == self._limits_bytes,
              "RECOVERY_STORE_CONTEXT_CHANGED")
        expected = _digest("context", {"schema": 1, "head_name": self._head_name,
                                       "limits": json.loads(self._limits_bytes)})
        _need(self.context_sha256 == expected and self.genesis_digest == _digest("genesis", {
            "context_sha256": expected}), "RECOVERY_STORE_CONTEXT_CHANGED")
        if hasattr(self, "_fixed_head"):
            _need(type(self.head) is BaselineHead and self.head is self._fixed_head
                  and self.head._root == self.head_root and self.head._dir == self.head_root / self._head_name
                  and self.head._chain is self._chain and type(self._chain) is _RecoveryChain
                  and self._chain.store is self, "RECOVERY_STORE_CONTEXT_CHANGED")

    def _paths(self, *, prepared=True, head_required=False):
        self._configuration()
        try:
            for root in self._roots:
                checked_target(root, "research recovery root")
                _need(not any(p.casefold() == "onedrive" or p.casefold().startswith("onedrive - ")
                              for p in root.parts), "RECOVERY_STORE_SYNC_ROOT_REFUSED")
                for path in (root, *root.parents):
                    _directory(os.lstat(path))
                for other in (*[p for p in self._roots if p != root], state_root().absolute(), _REPO):
                    a, b = root.resolve(), other.resolve()
                    _need(not a.is_relative_to(b) and not b.is_relative_to(a),
                          "RECOVERY_STORE_ROOT_OVERLAP")
            ids = tuple(_directory(os.lstat(p)) for p in self._roots)
            if hasattr(self, "_root_ids"):
                _need(ids == self._root_ids, "RECOVERY_STORE_ROOT_CHANGED")
            allowed = ({"session.lock", "operation.lock", "journal.jsonl"}, {"versions"}, {self._head_name})
            for root, names in zip(self._roots, allowed):
                observed = set()
                with os.scandir(root) as entries:
                    for entry in entries:
                        _need(entry.name in names and len(observed) < len(names),
                              "RECOVERY_STORE_PATH_REFUSED")
                        observed.add(entry.name)
                if prepared and root != self.head_root:
                    _need(observed == names, "RECOVERY_STORE_NOT_PROVISIONED")
                if head_required and root == self.head_root:
                    _need(observed == names, "RECOVERY_STORE_HEAD_REQUIRED")
            if (self.backup_root / "versions").exists():
                _directory(os.lstat(self.backup_root / "versions"))
            for name, maximum in (("session.lock", 1), ("operation.lock", 1), ("journal.jsonl", self.limits.max_journal_bytes)):
                path = self.root / name
                if path.exists():
                    _file(os.lstat(path), maximum)
            if (self.head_root / self._head_name).exists():
                _directory(os.lstat(self.head_root / self._head_name))
        except RecoveryStoreError:
            raise
        except (OSError, ValueError, RuntimeError, TypeError):
            raise RecoveryStoreError("RECOVERY_STORE_PATH_REFUSED") from None

    @contextmanager
    def _pinned(self, *, prepared=True, head_required=True):
        self._paths(prepared=prepared, head_required=head_required)
        paths = list(self._roots)
        if prepared:
            paths.append(self.backup_root / "versions")
        if head_required:
            paths.append(self.head_root / self._head_name)
        try:
            with _Pins(paths) as pins:
                self._paths(prepared=prepared, head_required=head_required)
                yield pins
                pins.check()
                self._paths(prepared=prepared, head_required=head_required)
        except RecoveryStoreError:
            raise
        except (OSError, ValueError, RuntimeError, TypeError):
            raise RecoveryStoreError("RECOVERY_STORE_PIN_REFUSED") from None

    @staticmethod
    def _open(pins, root, name, flags):
        target = checked_target(root / name, "research recovery file", within=root)
        return os.open(target if os.name == "nt" else name, flags | _FLAGS, 0o600,
                       **({} if os.name == "nt" else {"dir_fd": pins.fd(root)}))

    @staticmethod
    def _sync(pins, root):
        if os.name != "nt":
            os.fsync(pins.fd(root))

    def provision_empty(self):
        """Explicit empty storage setup only; separate operator head seed is mandatory."""
        try:
            with self._pinned(prepared=False, head_required=False) as pins:
                for root in self._roots:
                    with os.scandir(root) as entries:
                        _need(next(entries, None) is None, "RECOVERY_STORE_ALREADY_PROVISIONED")
                for name, raw in (("session.lock", b"0"), ("operation.lock", b"0"), ("journal.jsonl", b"")):
                    fd = self._open(pins, self.root, name, os.O_WRONLY | os.O_CREAT | os.O_EXCL)
                    with os.fdopen(fd, "wb") as handle:
                        _need(handle.write(raw) == len(raw), "RECOVERY_STORE_WRITE_REFUSED")
                        handle.flush(); os.fsync(handle.fileno())
                if os.name == "nt":
                    os.mkdir(self.backup_root / "versions", mode=0o700)
                else:
                    os.mkdir("versions", mode=0o700, dir_fd=pins.fd(self.backup_root))
                self._sync(pins, self.root); self._sync(pins, self.backup_root)
                pins.check()
            self._paths()
        except RecoveryStoreError:
            raise
        except (OSError, ValueError, RuntimeError, TypeError):
            raise RecoveryStoreError("RECOVERY_STORE_PROVISION_REFUSED") from None

    def _read(self, pins, root, name, maximum):
        before = os.lstat(root / name)
        _file(before, maximum)
        fd = self._open(pins, root, name, os.O_RDONLY)
        with os.fdopen(fd, "rb") as handle:
            opened = os.fstat(handle.fileno()); _file(opened, maximum)
            _need(_stamp(before) == _stamp(opened), "RECOVERY_STORE_FILE_CHANGED")
            raw = handle.read(maximum + 1)
            after = os.fstat(handle.fileno())
        current = os.lstat(root / name); _file(current, maximum)
        _need(_stamp(opened) == _stamp(after) == _stamp(current) and len(raw) == opened.st_size,
              "RECOVERY_STORE_FILE_CHANGED")
        return raw

    def _row_max(self):
        return self.limits.format_limits.max_event_bytes + 1024

    def _replay(self, pins):
        raw = self._read(pins, self.root, "journal.jsonl", self.limits.max_journal_bytes)
        _need(not raw or raw.endswith(b"\n"), "RECOVERY_STORE_PARTIAL_JOURNAL")
        _need(raw.count(b"\n") <= self.limits.max_records, "RECOVERY_STORE_LIMIT_EXCEEDED")
        head, sequence, previous, last_event = self.genesis_digest, 0, None, None
        raw_events = []
        expected_names = set()
        for raw_row in raw.split(b"\n")[:-1] if raw else ():
            _need(len(raw_row) + 1 <= self._row_max(), "RECOVERY_STORE_RECORD_INVALID")
            row = _decode(raw_row, self._row_max())
            _need(set(row) == _ROW_KEYS and type(row["schema"]) is int and row["schema"] == 1
                  and type(row["sequence"]) is int and row["sequence"] == sequence + 1
                  and row["previous_sha256"] == head and row["context_sha256"] == self.context_sha256
                  and _hash(row["row_sha256"]), "RECOVERY_STORE_CHAIN_INVALID")
            body = {key: value for key, value in row.items() if key != "row_sha256"}
            _need(_digest("row", body) == row["row_sha256"], "RECOVERY_STORE_CHAIN_INVALID")
            event_raw = _canonical(row["event"])
            name = row["row_sha256"] + ".json"
            _need(self._read(pins, self.backup_root / "versions", name, self._row_max()) == raw_row,
                  "RECOVERY_STORE_BACKUP_MISMATCH")
            expected_names.add(name)
            raw_events.append(event_raw)
            previous, head, sequence, last_event = head, row["row_sha256"], row["sequence"], event_raw
        observed = set()
        with os.scandir(self.backup_root / "versions") as entries:
            for entry in entries:
                _need(len(observed) < self.limits.max_records and entry.name in expected_names,
                      "RECOVERY_STORE_BACKUP_INVENTORY_MISMATCH")
                observed.add(entry.name)
        _need(observed == expected_names, "RECOVERY_STORE_BACKUP_INVENTORY_MISMATCH")
        # Start from the format's own initial state, parse each recorded event
        # once, fold once, and validate only the final derived projection. Never
        # accept an external state or repeatedly revalidate every history prefix.
        state = F._replay_events(tuple(raw_events), limits=self.limits.format_limits)
        _need(len(state.events) == sequence, "RECOVERY_STORE_DUPLICATE_ROW")
        return RecoveryStoreSnapshot(state=state, head=head, sequence=sequence), len(raw), previous, last_event

    def _load(self, pins):
        before = self.head.read()
        result = self._replay(pins)
        _need(result[0].head == before == self.head.read(), "RECOVERY_STORE_HEAD_MISMATCH")
        return result

    @contextmanager
    def _locked(self):
        if self._operation_state is not None:
            self.check_operation()
        _need(_LOCK.acquire(blocking=False), "RECOVERY_STORE_LOCKED")
        try:
            with self._pinned() as pins:
                target = self.root / "session.lock"
                before = os.lstat(target)
                fd = self._open(pins, self.root, "session.lock", os.O_RDWR)
                with os.fdopen(fd, "r+b") as handle:
                    opened = os.fstat(handle.fileno()); _file(opened, 1)
                    _need(_identity(before) == _identity(opened), "RECOVERY_STORE_LOCK_CHANGED")
                    try:
                        if os.name == "nt":
                            import msvcrt
                            handle.seek(0); msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                        else:
                            import fcntl
                            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    except OSError:
                        raise RecoveryStoreError("RECOVERY_STORE_LOCKED") from None
                    try:
                        anchor = self._anchor(pins, opened)
                        self._check_anchor(pins, anchor)
                        yield pins, anchor
                        self._check_anchor(pins, anchor)
                        if self._operation_state is not None:
                            self.check_operation()
                    finally:
                        if os.name == "nt":
                            handle.seek(0); msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                        else:
                            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        except RecoveryStoreError:
            raise
        except (OSError, ValueError, RuntimeError, TypeError):
            raise RecoveryStoreError("RECOVERY_STORE_IO_REFUSED") from None
        finally:
            _LOCK.release()

    def _anchor(self, pins, opened=None):
        pins.check()
        paths = (self.root / "session.lock", self.root / "journal.jsonl",
                 self.head._dir / "head.lock", self.root / "operation.lock")
        result = tuple((path, _file(os.lstat(path), 1 if path.name in ("session.lock", "operation.lock") else
                        4096 if path.name == "head.lock" else self.limits.max_journal_bytes)) for path in paths)
        if opened is not None:
            _need(result[0][1] == _identity(opened), "RECOVERY_STORE_LOCK_CHANGED")
        return result

    def _check_anchor(self, pins, anchor):
        self._paths(prepared=True, head_required=True)
        _need(self._anchor(pins) == anchor, "RECOVERY_STORE_STORAGE_CHANGED")

    def check_operation(self):
        """Recheck this thread's retained singleflight paths; grants no authority."""
        try:
            active = self._operation_state
            _need(type(active) is tuple and len(active) == 3 and active[2] == get_ident(),
                  "RECOVERY_STORE_OPERATION_REQUIRED")
            self._check_anchor(active[0], active[1])
        except RecoveryStoreError:
            raise
        except (OSError, ValueError, RuntimeError, TypeError):
            raise RecoveryStoreError("RECOVERY_STORE_OPERATION_REFUSED") from None

    @contextmanager
    def operation(self):
        """Singleflight across a controller run, without retaining session/head locks.

        The controller may call inspect/admit/commit inside this context. The
        yielded store is configuration, not a lease or authority to copy data.
        Explicit provisioning creates the lock; runtime never creates it.
        """
        _need(_OPERATION_LOCK.acquire(blocking=False), "RECOVERY_STORE_OPERATION_LOCKED")
        body_error = body_traceback = None
        try:
            with self._pinned() as pins:
                before = os.lstat(self.root / "operation.lock")
                fd = self._open(pins, self.root, "operation.lock", os.O_RDWR)
                with os.fdopen(fd, "r+b") as handle:
                    opened = os.fstat(handle.fileno()); _file(opened, 1)
                    _need(_identity(before) == _identity(opened), "RECOVERY_STORE_OPERATION_LOCK_CHANGED")
                    try:
                        if os.name == "nt":
                            import msvcrt
                            handle.seek(0); msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                        else:
                            import fcntl
                            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    except OSError:
                        raise RecoveryStoreError("RECOVERY_STORE_OPERATION_LOCKED") from None
                    try:
                        anchor = self._anchor(pins)
                        _need(anchor[-1][1] == _identity(opened), "RECOVERY_STORE_OPERATION_LOCK_CHANGED")
                        self._check_anchor(pins, anchor)
                        self._operation_state = (pins, anchor, get_ident())
                        # Preserve the controller's fixed refusal semantics.
                        # Complete real cleanup outside the body exception before
                        # re-raising it outside _pinned's I/O normalizer. A changed
                        # root/lock or failed cleanup still overrides that error.
                        try:
                            yield self
                        except BaseException as exc:
                            body_error, body_traceback = exc, exc.__traceback__
                        self.check_operation()
                    finally:
                        self._operation_state = None
                        if os.name == "nt":
                            handle.seek(0); msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                        else:
                            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        except RecoveryStoreError:
            raise
        except (OSError, ValueError, RuntimeError, TypeError):
            raise RecoveryStoreError("RECOVERY_STORE_OPERATION_REFUSED") from None
        finally:
            _OPERATION_LOCK.release()
        if body_error is not None:
            raise body_error.with_traceback(body_traceback)

    def inspect(self) -> RecoveryStoreSnapshot:
        try:
            with self._locked() as (pins, anchor):
                snapshot = self._load(pins)[0]
                self._check_anchor(pins, anchor)
                return snapshot
        except RecoveryStoreError:
            raise
        except (ValueError, RuntimeError, OSError, TypeError, KeyError, RecursionError):
            raise RecoveryStoreError("RECOVERY_STORE_REPLAY_REFUSED") from None

    def _prepare(self, event, event_raw, expected_head, current, size, previous, last_event):
        # Exact last-row response-loss retry may still carry the old head.
        if last_event == event_raw and expected_head in (current.head, previous):
            return None
        _need(expected_head == current.head, "RECOVERY_STORE_EXPECTED_HEAD_CHANGED")
        proposed = F.reduce(current.state, event, limits=self.limits.format_limits)
        if F.state_bytes(proposed, limits=self.limits.format_limits) == F.state_bytes(
                current.state, limits=self.limits.format_limits):
            return None
        body = {"schema": 1, "sequence": current.sequence + 1, "previous_sha256": current.head,
                "context_sha256": self.context_sha256, "event": json.loads(event_raw)}
        row = body | {"row_sha256": _digest("row", body)}
        raw = _canonical(row); line = raw + b"\n"
        # Each backup contains exactly the corresponding row without its LF, so
        # max_journal_bytes also bounds aggregate committed backup bytes.
        _need(len(line) <= self._row_max() and size + len(line) <= self.limits.max_journal_bytes
              and row["sequence"] <= self.limits.max_records, "RECOVERY_STORE_LIMIT_EXCEEDED")
        _need(_decode(raw, self._row_max()) == row, "RECOVERY_STORE_RECORD_INVALID")
        return proposed, row, raw, line

    def admit(self, event, *, expected_head: str) -> RecoveryStoreSnapshot:
        """Read-only current admission, never a reservation or future I/O guarantee.

        The returned snapshot is the actual CURRENT history. A proposed state or
        head is never published here, and commit repeats every check under lock.
        """
        try:
            _need(_hash(expected_head), "RECOVERY_STORE_EXPECTED_HEAD_REQUIRED")
            event_raw = F.event_bytes(event, limits=self.limits.format_limits)
            event = F.parse_event(event_raw, limits=self.limits.format_limits)
            with self._locked() as (pins, anchor):
                current, size, previous, last_event = self._load(pins)
                self._prepare(event, event_raw, expected_head, current, size, previous, last_event)
                confirmed = self._load(pins)
                _need(confirmed[0] == current and confirmed[1] == size, "RECOVERY_STORE_STORAGE_CHANGED")
                self._check_anchor(pins, anchor)
                return current
        except RecoveryStoreError:
            raise
        except (ValueError, RuntimeError, OSError, TypeError, KeyError, RecursionError, OverflowError):
            raise RecoveryStoreError("RECOVERY_STORE_ADMISSION_REFUSED") from None

    def admit_pair(self, first, second, *, expected_head: str) -> RecoveryStoreSnapshot:
        """Read-only exact two-event capacity check, returning only current history.

        Forecasts stay private and are never observed outcomes or reservations.
        Callers must conservatively bound future fields; actual commit repeats
        admission and may still fail from later state or storage changes.
        """
        try:
            _need(_hash(expected_head), "RECOVERY_STORE_EXPECTED_HEAD_REQUIRED")
            detached = []
            for event in (first, second):
                raw = F.event_bytes(event, limits=self.limits.format_limits)
                detached.append((F.parse_event(raw, limits=self.limits.format_limits), raw))
            with self._locked() as (pins, anchor):
                current, size, previous, last_event = self._load(pins)
                forecast, forecast_size, next_expected = current, size, expected_head
                for event, raw in detached:
                    prepared = self._prepare(event, raw, next_expected, forecast,
                                             forecast_size, previous, last_event)
                    if prepared is not None:
                        proposed, row, _, line = prepared
                        previous, last_event = forecast.head, raw
                        forecast = RecoveryStoreSnapshot(state=proposed, head=row["row_sha256"],
                                                         sequence=row["sequence"])
                        forecast_size += len(line)
                    next_expected = forecast.head
                confirmed = self._load(pins)
                _need(confirmed[0] == current and confirmed[1] == size, "RECOVERY_STORE_STORAGE_CHANGED")
                self._check_anchor(pins, anchor)
                return current
        except RecoveryStoreError:
            raise
        except (ValueError, RuntimeError, OSError, TypeError, KeyError, RecursionError, OverflowError):
            raise RecoveryStoreError("RECOVERY_STORE_ADMISSION_REFUSED") from None

    def commit(self, event, *, expected_head: str) -> RecoveryStoreSnapshot:
        try:
            _need(_hash(expected_head), "RECOVERY_STORE_EXPECTED_HEAD_REQUIRED")
            event_raw = F.event_bytes(event, limits=self.limits.format_limits)
            event = F.parse_event(event_raw, limits=self.limits.format_limits)
            with self._locked() as (pins, anchor):
                current, size, previous, last_event = self._load(pins)
                prepared = self._prepare(event, event_raw, expected_head, current, size, previous, last_event)
                if prepared is None:
                    return current
                proposed, row, raw, line = prepared
                self._check_anchor(pins, anchor)
                self._append(pins, anchor, line, size)
                self._backup(pins, row["row_sha256"] + ".json", raw)
                self._check_anchor(pins, anchor)
                _need(self.head.compare_and_set(current.head, row["row_sha256"]) is True,
                      "RECOVERY_STORE_HEAD_UPDATE_REFUSED")
                confirmed, confirmed_size, _, _ = self._load(pins)
                _need(confirmed.head == row["row_sha256"] and confirmed.sequence == row["sequence"]
                      and F.state_bytes(confirmed.state, limits=self.limits.format_limits)
                      == F.state_bytes(proposed, limits=self.limits.format_limits)
                      and confirmed_size == size + len(line), "RECOVERY_STORE_PUBLICATION_MISMATCH")
                self._check_anchor(pins, anchor)
                return confirmed
        except RecoveryStoreError:
            raise
        except (ValueError, RuntimeError, OSError, TypeError, KeyError, RecursionError, OverflowError):
            raise RecoveryStoreError("RECOVERY_STORE_COMMIT_REFUSED") from None

    def _append(self, pins, anchor, line, size):
        before = os.lstat(self.root / "journal.jsonl")
        fd = self._open(pins, self.root, "journal.jsonl", os.O_WRONLY | os.O_APPEND)
        with os.fdopen(fd, "ab") as handle:
            opened = os.fstat(handle.fileno()); _file(opened, self.limits.max_journal_bytes)
            _need(_stamp(before) == _stamp(opened) and opened.st_size == size,
                  "RECOVERY_STORE_FILE_CHANGED")
            _need(handle.write(line) == len(line), "RECOVERY_STORE_WRITE_REFUSED")
            handle.flush(); os.fsync(handle.fileno())
            written = os.fstat(handle.fileno())
        current = os.lstat(self.root / "journal.jsonl"); _file(current, self.limits.max_journal_bytes)
        _need(_identity(current) == _identity(written) == _identity(opened)
              and current.st_size == written.st_size == size + len(line), "RECOVERY_STORE_FILE_CHANGED")
        raw = self._read(pins, self.root, "journal.jsonl", self.limits.max_journal_bytes)
        _need(len(raw) == size + len(line) and raw[-len(line):] == line, "RECOVERY_STORE_WRITE_REFUSED")
        self._check_anchor(pins, anchor)

    def _backup(self, pins, name, raw):
        root = self.backup_root / "versions"
        fd = self._open(pins, root, name, os.O_WRONLY | os.O_CREAT | os.O_EXCL)
        with os.fdopen(fd, "wb") as handle:
            _need(handle.write(raw) == len(raw), "RECOVERY_STORE_BACKUP_WRITE_REFUSED")
            handle.flush(); os.fsync(handle.fileno())
        self._sync(pins, root)
        _need(self._read(pins, root, name, self._row_max()) == raw, "RECOVERY_STORE_BACKUP_MISMATCH")
