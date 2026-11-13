"""Independent durable incident history and atomic notification intents.

Three explicitly provisioned roots hold the journal, exact versioned row copies,
and an independent BaselineHead. The pure incident reducer supplies each complete
transition, including its outbox intents. No research store, source verifier,
approval, recovery, transport or order capability is issued here. A normal read
never initializes a head, adopts a partial append, truncates or releases a hold.

Lock order is incident session, then independent head; the head's chain callback
only replays bytes and never acquires either lock. POSIX paths use retained
no-follow ancestor descriptors; Windows uses the existing reviewed directory pin.
Windows native execution and power-loss durability remain unverified. Separate
paths do not establish separate media, and coherent rollback of all roots by the
same user remains outside this local integrity discipline.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import asdict, dataclass, fields
import hashlib
import json
import os
from pathlib import Path
import re
import stat
from threading import Lock

from core.isolation import checked_target, state_root
from execution_launch.baseline_head import BaselineHead, BaselineHeadError
from execution_launch import research_incidents as F

_DOMAIN = b"TRADEGEN-RESEARCH-INCIDENT-STORE-v1\x00"
_HASH = re.compile(r"[0-9a-f]{64}")
_NAME = re.compile(r"[a-z][a-z0-9-]{0,63}")
_FLAGS = getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_BINARY", 0) | getattr(os, "O_NONBLOCK", 0)
_REPO = Path(__file__).resolve().parents[1]
_LOCK = Lock()
_ROW_KEYS = frozenset({"schema", "sequence", "previous_sha256", "context_sha256", "event", "row_sha256"})


class IncidentStoreError(ValueError):
    """Fixed INCIDENT_STORE_* diagnostics, without private paths or OS text."""


def _need(ok, code):
    if not ok:
        raise IncidentStoreError(code)


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                      allow_nan=False).encode("ascii")


def _digest(kind, body):
    return hashlib.sha256(_DOMAIN + kind.encode("ascii") + b"\x00" + _canonical(body)).hexdigest()


def _hash(value):
    return type(value) is str and _HASH.fullmatch(value) is not None


def _identity(info):
    _need(type(info.st_dev) is int and info.st_dev >= 0 and type(info.st_ino) is int and info.st_ino > 0,
          "INCIDENT_STORE_IDENTITY_UNAVAILABLE")
    return info.st_dev, info.st_ino


def _directory(info):
    _need(stat.S_ISDIR(info.st_mode) and not getattr(info, "st_file_attributes", 0) & 0x441400,
          "INCIDENT_STORE_DIRECTORY_REFUSED")
    return _identity(info)


def _file(info, maximum):
    _need(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and 0 <= info.st_size <= maximum
          and not getattr(info, "st_file_attributes", 0) & 0x441400,
          "INCIDENT_STORE_FILE_REFUSED")
    return _identity(info)


def _stamp(info):
    return _identity(info), info.st_size, info.st_mtime_ns, info.st_ctime_ns


def _decode(raw, maximum):
    def pairs(items):
        result = {}
        for key, value in items:
            _need(key not in result, "INCIDENT_STORE_RECORD_INVALID")
            result[key] = value
        return result
    def bad(_):
        raise IncidentStoreError("INCIDENT_STORE_RECORD_INVALID")
    def integer(value):
        _need(len(value) <= 20, "INCIDENT_STORE_RECORD_INVALID")
        result = int(value)
        _need(-(2 ** 63) <= result <= 2 ** 63 - 1, "INCIDENT_STORE_RECORD_INVALID")
        return result
    try:
        _need(type(raw) is bytes and 0 < len(raw) <= maximum, "INCIDENT_STORE_RECORD_INVALID")
        # One store envelope around the format's bounded event. Count structure
        # before JSON allocation; strings/escapes cannot manufacture containers.
        quoted = escaped = False
        depth = nodes = 0
        for byte in raw:
            if quoted:
                if escaped:
                    escaped = False
                elif byte == 92:
                    escaped = True
                elif byte == 34:
                    quoted = False
            elif byte == 34:
                quoted = True
                nodes += 1
            elif byte in (91, 123):
                depth += 1
                nodes += 1
                _need(depth <= 17, "INCIDENT_STORE_RECORD_LIMIT_EXCEEDED")
            elif byte in (93, 125):
                depth -= 1
            elif byte == 44:
                nodes += 1
            _need(nodes <= 2000032, "INCIDENT_STORE_RECORD_LIMIT_EXCEEDED")
        body = json.loads(raw.decode("ascii"), object_pairs_hook=pairs, parse_int=integer,
                          parse_float=bad, parse_constant=bad)
        _need(type(body) is dict and _canonical(body) == raw, "INCIDENT_STORE_RECORD_INVALID")
        return body
    except IncidentStoreError:
        raise
    except (ValueError, TypeError, UnicodeError, OverflowError, RecursionError):
        raise IncidentStoreError("INCIDENT_STORE_RECORD_INVALID") from None


@dataclass(frozen=True, kw_only=True)
class IncidentStoreLimits:
    format_limits: F.IncidentLimits
    max_journal_bytes: int = 128 * 1024 * 1024
    max_records: int = 16384

    def __post_init__(self):
        _need(type(self.format_limits) is F.IncidentLimits, "INCIDENT_STORE_LIMITS_INVALID")
        # Reconstruct the closed format limits to run that type's strict checks.
        _need(F.IncidentLimits(**asdict(self.format_limits)) == self.format_limits,
              "INCIDENT_STORE_LIMITS_INVALID")
        _need(type(self.max_journal_bytes) is int and 1 <= self.max_journal_bytes <= 128 * 1024 * 1024
              and type(self.max_records) is int and 1 <= self.max_records <= 16384,
              "INCIDENT_STORE_LIMITS_INVALID")


def limits_bytes(limits: IncidentStoreLimits) -> bytes:
    try:
        _need(type(limits) is IncidentStoreLimits, "INCIDENT_STORE_LIMITS_INVALID")
        limits.__post_init__()
        return _canonical(asdict(limits))
    except IncidentStoreError:
        raise
    except (ValueError, TypeError, AttributeError, RecursionError):
        raise IncidentStoreError("INCIDENT_STORE_LIMITS_INVALID") from None


def parse_limits(raw: bytes) -> IncidentStoreLimits:
    try:
        body = _decode(raw, 8192)
        _need(set(body) == {field.name for field in fields(IncidentStoreLimits)}
              and type(body["format_limits"]) is dict
              and set(body["format_limits"]) == {field.name for field in fields(F.IncidentLimits)},
              "INCIDENT_STORE_LIMITS_INVALID")
        value = IncidentStoreLimits(format_limits=F.IncidentLimits(**body["format_limits"]),
            max_journal_bytes=body["max_journal_bytes"], max_records=body["max_records"])
        _need(limits_bytes(value) == raw, "INCIDENT_STORE_LIMITS_INVALID")
        return value
    except IncidentStoreError:
        raise
    except (ValueError, TypeError, KeyError, AttributeError, RecursionError):
        raise IncidentStoreError("INCIDENT_STORE_LIMITS_INVALID") from None


@dataclass(frozen=True, kw_only=True)
class IncidentStoreSnapshot:
    state: object
    head: str
    sequence: int

    @property
    def execution_ready(self):
        return False


class _Pins:
    """Retain actual directory handles while checking their lexical identities."""
    def __init__(self, paths):
        self.paths, self.rows, self.native = tuple(dict.fromkeys(paths)), {}, []

    def __enter__(self):
        try:
            if os.name == "nt":
                from execution_launch.bundle_review import pin_windows_directory
                for path in self.paths:
                    context = pin_windows_directory(str(path))
                    pin = context.__enter__()
                    self.native.append((context, pin))
            else:
                for target in self.paths:
                    parent_fd = None
                    for path in reversed((target, *target.parents)):
                        if path in self.rows:
                            parent_fd = self.rows[path][0]
                            continue
                        before = _directory(os.lstat(path))
                        directory_flags = os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_NOFOLLOW", 0)
                        fd = os.open(path if parent_fd is None else path.name, directory_flags,
                                     **({} if parent_fd is None else {"dir_fd": parent_fd}))
                        try:
                            _need(_directory(os.fstat(fd)) == before, "INCIDENT_STORE_PATH_CHANGED")
                        except BaseException:
                            os.close(fd)
                            raise
                        self.rows[path] = (fd, before)
                        parent_fd = fd
            self.check()
            return self
        except BaseException:
            self._close()
            raise

    def check(self):
        for path, (fd, identity) in self.rows.items():
            _need(_directory(os.fstat(fd)) == identity == _directory(os.lstat(path)),
                  "INCIDENT_STORE_PATH_CHANGED")
        for _, pin in self.native:
            pin.check()

    def fd(self, path):
        return self.rows[path][0] if os.name != "nt" else None

    def _close(self):
        failed = False
        native, rows = self.native, self.rows
        self.native, self.rows = [], {}
        for context, _ in reversed(native):
            try:
                context.__exit__(None, None, None)
            except BaseException:
                failed = True
        for fd, _ in reversed(tuple(rows.values())):
            try:
                os.close(fd)
            except OSError:
                failed = True
        if failed:
            raise IncidentStoreError("INCIDENT_STORE_PIN_CLOSE_REFUSED")

    def __exit__(self, *_):
        self._close()


class _IncidentChain:
    def __init__(self, store):
        self.store = store

    def seed(self, digest):
        store = self.store
        _need(digest == store.genesis_digest, "INCIDENT_STORE_GENESIS_REQUIRED")
        with store._pinned(head_required=False) as pins:
            snapshot, _, _, _ = store._replay(pins)
            _need(snapshot.sequence == 0 and snapshot.head == digest, "INCIDENT_STORE_GENESIS_REQUIRED")
        return 0

    def successor(self, old, new):
        with self.store._pinned() as pins:
            snapshot, _, previous, _ = self.store._replay(pins)
            _need(snapshot.head == new and previous == old, "INCIDENT_STORE_DIRECT_SUCCESSOR_REQUIRED")
            return snapshot.sequence


class IncidentStore:
    def __init__(self, *, root: Path, backup_root: Path, head_root: Path,
                 head_name: str, limits: IncidentStoreLimits):
        _need(all(isinstance(p, Path) and p.is_absolute() and ".." not in p.parts
                  for p in (root, backup_root, head_root)), "INCIDENT_STORE_EXPLICIT_ROOTS_REQUIRED")
        _need(type(head_name) is str and _NAME.fullmatch(head_name) is not None,
              "INCIDENT_STORE_HEAD_NAME_INVALID")
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
            _need(len(set(self._root_ids)) == 3, "INCIDENT_STORE_ROOT_OVERLAP")
            self._chain = _IncidentChain(self)
            self.head = BaselineHead(root=head_root, name=head_name, chain=self._chain)
        except IncidentStoreError:
            raise
        except (OSError, ValueError, RuntimeError, TypeError):
            raise IncidentStoreError("INCIDENT_STORE_CONSTRUCTION_REFUSED") from None
        self._fixed_head = self.head

    def _configuration(self):
        _need((self.root, self.backup_root, self.head_root) == self._roots
              and limits_bytes(self.limits) == self._limits_bytes,
              "INCIDENT_STORE_CONTEXT_CHANGED")
        expected = _digest("context", {"schema": 1, "head_name": self._head_name,
                                       "limits": json.loads(self._limits_bytes)})
        _need(self.context_sha256 == expected and self.genesis_digest == _digest("genesis", {
            "context_sha256": expected}), "INCIDENT_STORE_CONTEXT_CHANGED")
        if hasattr(self, "_fixed_head"):
            _need(type(self.head) is BaselineHead and self.head is self._fixed_head
                  and self.head._root == self.head_root and self.head._dir == self.head_root / self._head_name
                  and self.head._chain is self._chain and type(self._chain) is _IncidentChain
                  and self._chain.store is self, "INCIDENT_STORE_CONTEXT_CHANGED")

    def _paths(self, *, prepared=True, head_required=False):
        self._configuration()
        try:
            for root in self._roots:
                checked_target(root, "research incident root")
                _need(not any(p.casefold() == "onedrive" or p.casefold().startswith("onedrive - ")
                              for p in root.parts), "INCIDENT_STORE_SYNC_ROOT_REFUSED")
                for path in (root, *root.parents):
                    _directory(os.lstat(path))
                for other in (*[p for p in self._roots if p != root], state_root().absolute(), _REPO):
                    a, b = root.resolve(), other.resolve()
                    _need(not a.is_relative_to(b) and not b.is_relative_to(a),
                          "INCIDENT_STORE_ROOT_OVERLAP")
            ids = tuple(_directory(os.lstat(p)) for p in self._roots)
            if hasattr(self, "_root_ids"):
                _need(ids == self._root_ids, "INCIDENT_STORE_ROOT_CHANGED")
            allowed = ({"session.lock", "journal.jsonl"}, {"versions"}, {self._head_name})
            for root, names in zip(self._roots, allowed):
                observed = set()
                with os.scandir(root) as entries:
                    for entry in entries:
                        _need(entry.name in names and len(observed) < len(names),
                              "INCIDENT_STORE_PATH_REFUSED")
                        observed.add(entry.name)
                if prepared and root != self.head_root:
                    _need(observed == names, "INCIDENT_STORE_NOT_PROVISIONED")
                if head_required and root == self.head_root:
                    _need(observed == names, "INCIDENT_STORE_HEAD_REQUIRED")
            if (self.backup_root / "versions").exists():
                _directory(os.lstat(self.backup_root / "versions"))
            for name, maximum in (("session.lock", 1), ("journal.jsonl", self.limits.max_journal_bytes)):
                path = self.root / name
                if path.exists():
                    _file(os.lstat(path), maximum)
            if (self.head_root / self._head_name).exists():
                _directory(os.lstat(self.head_root / self._head_name))
        except IncidentStoreError:
            raise
        except (OSError, ValueError, RuntimeError, TypeError):
            raise IncidentStoreError("INCIDENT_STORE_PATH_REFUSED") from None

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
        except IncidentStoreError:
            raise
        except (OSError, ValueError, RuntimeError, TypeError):
            raise IncidentStoreError("INCIDENT_STORE_PIN_REFUSED") from None

    @staticmethod
    def _open(pins, root, name, flags):
        target = checked_target(root / name, "research incident file", within=root)
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
                        _need(next(entries, None) is None, "INCIDENT_STORE_ALREADY_PROVISIONED")
                for name, raw in (("session.lock", b"0"), ("journal.jsonl", b"")):
                    fd = self._open(pins, self.root, name, os.O_WRONLY | os.O_CREAT | os.O_EXCL)
                    with os.fdopen(fd, "wb") as handle:
                        _need(handle.write(raw) == len(raw), "INCIDENT_STORE_WRITE_REFUSED")
                        handle.flush(); os.fsync(handle.fileno())
                if os.name == "nt":
                    os.mkdir(self.backup_root / "versions", mode=0o700)
                else:
                    os.mkdir("versions", mode=0o700, dir_fd=pins.fd(self.backup_root))
                self._sync(pins, self.root); self._sync(pins, self.backup_root)
                pins.check()
            self._paths()
        except IncidentStoreError:
            raise
        except (OSError, ValueError, RuntimeError, TypeError):
            raise IncidentStoreError("INCIDENT_STORE_PROVISION_REFUSED") from None

    def _read(self, pins, root, name, maximum):
        before = os.lstat(root / name)
        _file(before, maximum)
        fd = self._open(pins, root, name, os.O_RDONLY)
        with os.fdopen(fd, "rb") as handle:
            opened = os.fstat(handle.fileno()); _file(opened, maximum)
            _need(_stamp(before) == _stamp(opened), "INCIDENT_STORE_FILE_CHANGED")
            raw = handle.read(maximum + 1)
            after = os.fstat(handle.fileno())
        current = os.lstat(root / name); _file(current, maximum)
        _need(_stamp(opened) == _stamp(after) == _stamp(current) and len(raw) == opened.st_size,
              "INCIDENT_STORE_FILE_CHANGED")
        return raw

    def _row_max(self):
        return self.limits.format_limits.max_event_bytes + 1024

    def _replay(self, pins):
        raw = self._read(pins, self.root, "journal.jsonl", self.limits.max_journal_bytes)
        _need(not raw or raw.endswith(b"\n"), "INCIDENT_STORE_PARTIAL_JOURNAL")
        _need(raw.count(b"\n") <= self.limits.max_records, "INCIDENT_STORE_LIMIT_EXCEEDED")
        head, sequence, previous, last_event = self.genesis_digest, 0, None, None
        raw_events = []
        expected_names = set()
        for raw_row in raw.split(b"\n")[:-1] if raw else ():
            _need(len(raw_row) + 1 <= self._row_max(), "INCIDENT_STORE_RECORD_INVALID")
            row = _decode(raw_row, self._row_max())
            _need(set(row) == _ROW_KEYS and type(row["schema"]) is int and row["schema"] == 1
                  and type(row["sequence"]) is int and row["sequence"] == sequence + 1
                  and row["previous_sha256"] == head and row["context_sha256"] == self.context_sha256
                  and _hash(row["row_sha256"]), "INCIDENT_STORE_CHAIN_INVALID")
            body = {key: value for key, value in row.items() if key != "row_sha256"}
            _need(_digest("row", body) == row["row_sha256"], "INCIDENT_STORE_CHAIN_INVALID")
            event_raw = _canonical(row["event"])
            name = row["row_sha256"] + ".json"
            _need(self._read(pins, self.backup_root / "versions", name, self._row_max()) == raw_row,
                  "INCIDENT_STORE_BACKUP_MISMATCH")
            expected_names.add(name)
            raw_events.append(event_raw)
            previous, head, sequence, last_event = head, row["row_sha256"], row["sequence"], event_raw
        observed = set()
        with os.scandir(self.backup_root / "versions") as entries:
            for entry in entries:
                _need(len(observed) < self.limits.max_records and entry.name in expected_names,
                      "INCIDENT_STORE_BACKUP_INVENTORY_MISMATCH")
                observed.add(entry.name)
        _need(observed == expected_names, "INCIDENT_STORE_BACKUP_INVENTORY_MISMATCH")
        # Start from the format's own initial state, parse each recorded event
        # once, fold once, and validate only the final derived projection. Never
        # accept an external state or repeatedly revalidate every history prefix.
        state = F._replay_events(tuple(raw_events), limits=self.limits.format_limits)
        _need(len(state.events) == sequence, "INCIDENT_STORE_DUPLICATE_ROW")
        return IncidentStoreSnapshot(state=state, head=head, sequence=sequence), len(raw), previous, last_event

    def _load(self, pins):
        before = self.head.read()
        result = self._replay(pins)
        _need(result[0].head == before == self.head.read(), "INCIDENT_STORE_HEAD_MISMATCH")
        return result

    @contextmanager
    def _locked(self):
        _need(_LOCK.acquire(blocking=False), "INCIDENT_STORE_LOCKED")
        try:
            with self._pinned() as pins:
                target = self.root / "session.lock"
                before = os.lstat(target)
                fd = self._open(pins, self.root, "session.lock", os.O_RDWR)
                with os.fdopen(fd, "r+b") as handle:
                    opened = os.fstat(handle.fileno()); _file(opened, 1)
                    _need(_identity(before) == _identity(opened), "INCIDENT_STORE_LOCK_CHANGED")
                    try:
                        if os.name == "nt":
                            import msvcrt
                            handle.seek(0); msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                        else:
                            import fcntl
                            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    except OSError:
                        raise IncidentStoreError("INCIDENT_STORE_LOCKED") from None
                    try:
                        anchor = self._anchor(pins, opened)
                        self._check_anchor(pins, anchor)
                        yield pins, anchor
                        self._check_anchor(pins, anchor)
                    finally:
                        if os.name == "nt":
                            handle.seek(0); msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                        else:
                            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        except IncidentStoreError:
            raise
        except (OSError, ValueError, RuntimeError, TypeError):
            raise IncidentStoreError("INCIDENT_STORE_IO_REFUSED") from None
        finally:
            _LOCK.release()

    def _anchor(self, pins, opened=None):
        pins.check()
        paths = (self.root / "session.lock", self.root / "journal.jsonl",
                 self.head._dir / "head.lock")
        result = tuple((path, _file(os.lstat(path), 1 if path.name == "session.lock" else
                        4096 if path.name == "head.lock" else self.limits.max_journal_bytes)) for path in paths)
        if opened is not None:
            _need(result[0][1] == _identity(opened), "INCIDENT_STORE_LOCK_CHANGED")
        return result

    def _check_anchor(self, pins, anchor):
        self._paths(prepared=True, head_required=True)
        _need(self._anchor(pins) == anchor, "INCIDENT_STORE_STORAGE_CHANGED")

    def inspect(self) -> IncidentStoreSnapshot:
        try:
            with self._locked() as (pins, anchor):
                snapshot = self._load(pins)[0]
                self._check_anchor(pins, anchor)
                return snapshot
        except IncidentStoreError:
            raise
        except (ValueError, RuntimeError, OSError, TypeError, KeyError, RecursionError):
            raise IncidentStoreError("INCIDENT_STORE_REPLAY_REFUSED") from None

    def _prepare(self, event, event_raw, expected_head, current, size, previous, last_event):
        # Exact last-row response-loss retry may still carry the old head.
        if last_event == event_raw and expected_head in (current.head, previous):
            return None
        _need(expected_head == current.head, "INCIDENT_STORE_EXPECTED_HEAD_CHANGED")
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
              and row["sequence"] <= self.limits.max_records, "INCIDENT_STORE_LIMIT_EXCEEDED")
        _need(_decode(raw, self._row_max()) == row, "INCIDENT_STORE_RECORD_INVALID")
        return proposed, row, raw, line

    def admit(self, event, *, expected_head: str) -> IncidentStoreSnapshot:
        """Read-only current admission, never a reservation or future I/O guarantee.

        The returned snapshot is the actual CURRENT history. A proposed state or
        head is never published here, and commit repeats every check under lock.
        """
        try:
            _need(_hash(expected_head), "INCIDENT_STORE_EXPECTED_HEAD_REQUIRED")
            event_raw = F.event_bytes(event, limits=self.limits.format_limits)
            event = F.parse_event(event_raw, limits=self.limits.format_limits)
            with self._locked() as (pins, anchor):
                current, size, previous, last_event = self._load(pins)
                self._prepare(event, event_raw, expected_head, current, size, previous, last_event)
                confirmed = self._load(pins)
                _need(confirmed[0] == current and confirmed[1] == size, "INCIDENT_STORE_STORAGE_CHANGED")
                self._check_anchor(pins, anchor)
                return current
        except IncidentStoreError:
            raise
        except (ValueError, RuntimeError, OSError, TypeError, KeyError, RecursionError, OverflowError):
            raise IncidentStoreError("INCIDENT_STORE_ADMISSION_REFUSED") from None

    def commit(self, event, *, expected_head: str) -> IncidentStoreSnapshot:
        try:
            _need(_hash(expected_head), "INCIDENT_STORE_EXPECTED_HEAD_REQUIRED")
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
                      "INCIDENT_STORE_HEAD_UPDATE_REFUSED")
                confirmed, confirmed_size, _, _ = self._load(pins)
                _need(confirmed.head == row["row_sha256"] and confirmed.sequence == row["sequence"]
                      and F.state_bytes(confirmed.state, limits=self.limits.format_limits)
                      == F.state_bytes(proposed, limits=self.limits.format_limits)
                      and confirmed_size == size + len(line), "INCIDENT_STORE_PUBLICATION_MISMATCH")
                self._check_anchor(pins, anchor)
                return confirmed
        except IncidentStoreError:
            raise
        except (ValueError, RuntimeError, OSError, TypeError, KeyError, RecursionError, OverflowError):
            raise IncidentStoreError("INCIDENT_STORE_COMMIT_REFUSED") from None

    def _append(self, pins, anchor, line, size):
        before = os.lstat(self.root / "journal.jsonl")
        fd = self._open(pins, self.root, "journal.jsonl", os.O_WRONLY | os.O_APPEND)
        with os.fdopen(fd, "ab") as handle:
            opened = os.fstat(handle.fileno()); _file(opened, self.limits.max_journal_bytes)
            _need(_stamp(before) == _stamp(opened) and opened.st_size == size,
                  "INCIDENT_STORE_FILE_CHANGED")
            _need(handle.write(line) == len(line), "INCIDENT_STORE_WRITE_REFUSED")
            handle.flush(); os.fsync(handle.fileno())
            written = os.fstat(handle.fileno())
        current = os.lstat(self.root / "journal.jsonl"); _file(current, self.limits.max_journal_bytes)
        _need(_identity(current) == _identity(written) == _identity(opened)
              and current.st_size == written.st_size == size + len(line), "INCIDENT_STORE_FILE_CHANGED")
        raw = self._read(pins, self.root, "journal.jsonl", self.limits.max_journal_bytes)
        _need(len(raw) == size + len(line) and raw[-len(line):] == line, "INCIDENT_STORE_WRITE_REFUSED")
        self._check_anchor(pins, anchor)

    def _backup(self, pins, name, raw):
        root = self.backup_root / "versions"
        fd = self._open(pins, root, name, os.O_WRONLY | os.O_CREAT | os.O_EXCL)
        with os.fdopen(fd, "wb") as handle:
            _need(handle.write(raw) == len(raw), "INCIDENT_STORE_BACKUP_WRITE_REFUSED")
            handle.flush(); os.fsync(handle.fileno())
        self._sync(pins, root)
        _need(self._read(pins, root, name, self._row_max()) == raw, "INCIDENT_STORE_BACKUP_MISMATCH")
