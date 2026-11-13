"""Lossless content-addressed payload objects; not a history commit or an authority.

P0a stores exact caller-supplied bytes and returns a small manifest reference. It
never reads state-home contents, advances a journal/head, chooses a strategy, repairs a
history, removes orphan evidence, or changes unavailable/valid market data. The
caller must authenticate the reference and bind it to its window/slot separately.

Publication uses an exclusive store lock, a fsynced same-directory temporary
file, and exclusive final-name creation followed by a bounded verified copy.
Only that publication's own temporary name is removed on success; all files
have one link. Final-name visibility is NOT atomic: an interrupted copy leaves
an unreferenced partial object, never an issued reference or a committed slot. A
crash leaving a temporary file blocks further staging; reading an unrelated
authenticated reference remains possible. A referenced two-link final file is
refused. Missing, changed, partial or over-limit objects never become a replacement payload.

Limits bound each payload, not the total store/window. Repeated staging needs
the integrating caller's finite window byte/object quota before operational use.

The explicit root must have an existing real parent. Path and opened-file
identity checks reject links/reparse points and unexpected replacement; this is
path discipline, not a boundary against an adversary able to replace arbitrary
ancestors while this process runs. File fsync is used on every platform. Windows
has no portable directory fsync here: power-loss durability on a particular
Windows filesystem is NOT established by this module. Publication never links,
renames or overwrites an existing object.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import asdict, dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import stat
from threading import Lock

# Reuse the application isolation guard, including QUANTGEN alias metadata
# checks. Never call state_root or choose a home as this component's storage root.
from core.isolation import checked_target

SCHEMA = 1
MAX_REFERENCE_BYTES = 4096
_HARD_CHUNK_BYTES = 1024 * 1024
_HARD_PAYLOAD_BYTES = 64 * 1024 * 1024
_HARD_CHUNKS = 4096
_HARD_MANIFEST_BYTES = 1024 * 1024
_DOMAIN = b"TRADEGEN-EVIDENCE-OBJECTS-v1\x00"
_HASH = re.compile(r"[0-9a-f]{64}")
_PROCESS_LOCK = Lock()
_REFERENCE_KEYS = frozenset({"schema", "manifest_sha256", "manifest_bytes", "payload_sha256", "payload_bytes",
                             "policy_sha256"})
_MANIFEST_KEYS = frozenset({"schema", "policy_sha256", "payload_sha256", "payload_bytes", "chunk_bytes", "chunks"})
_CHUNK_KEYS = frozenset({"index", "bytes", "sha256"})


class EvidenceObjectError(ValueError):
    """Fixed diagnostic codes; never include paths, evidence or account values."""


def _require(ok, code):
    if not ok:
        raise EvidenceObjectError(code)


def _integer(value, maximum):
    return type(value) is int and 0 < value <= maximum


def _hash(value):
    return type(value) is str and _HASH.fullmatch(value) is not None


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                      allow_nan=False).encode("ascii")


def _object_digest(kind, raw):
    _require(kind in ("chunk", "manifest") and type(raw) is bytes, "EVIDENCE_OBJECT_INPUT_INVALID")
    return hashlib.sha256(_DOMAIN + kind.encode("ascii") + b"\x00" + raw).hexdigest()


def _pairs(items):
    out = {}
    for key, value in items:
        if key in out:
            raise ValueError("duplicate key")
        out[key] = value
    return out


def _decode(raw, maximum, code):
    _require(type(raw) is bytes and 0 < len(raw) <= maximum, code)
    try:
        value = json.loads(raw.decode("ascii"), object_pairs_hook=_pairs,
                           parse_constant=lambda value: (_ for _ in ()).throw(ValueError("constant")))
        _require(type(value) is dict and _canonical(value) == raw, code)
        return value
    except EvidenceObjectError:
        raise
    except (ValueError, TypeError, RecursionError, UnicodeError, OverflowError):
        raise EvidenceObjectError(code) from None


@dataclass(frozen=True, kw_only=True)
class ObjectLimits:
    """Explicit deployment policy, below defensive parser ceilings; no operational defaults.

    Limits bind independently. For example a chunk-count cap can be reached
    before the payload-byte cap. Admission validates all caps before any I/O.
    """
    chunk_bytes: int
    max_payload_bytes: int
    max_chunks: int
    max_manifest_bytes: int

    def __post_init__(self):
        _require(_integer(self.chunk_bytes, _HARD_CHUNK_BYTES)
                 and _integer(self.max_payload_bytes, _HARD_PAYLOAD_BYTES)
                 and _integer(self.max_chunks, _HARD_CHUNKS)
                 and _integer(self.max_manifest_bytes, _HARD_MANIFEST_BYTES), "EVIDENCE_OBJECT_INPUT_INVALID")

    @property
    def policy_sha256(self):
        return hashlib.sha256(_DOMAIN + b"policy\x00" + _canonical(asdict(self))).hexdigest()


@dataclass(frozen=True, kw_only=True)
class PayloadReference:
    schema: int
    manifest_sha256: str
    manifest_bytes: int
    payload_sha256: str
    payload_bytes: int
    policy_sha256: str

    def __post_init__(self):
        _require(type(self.schema) is int and self.schema == SCHEMA
                 and _hash(self.manifest_sha256) and _hash(self.payload_sha256) and _hash(self.policy_sha256)
                 and _integer(self.manifest_bytes, _HARD_MANIFEST_BYTES)
                 and _integer(self.payload_bytes, _HARD_PAYLOAD_BYTES), "EVIDENCE_OBJECT_REFERENCE_INVALID")


def encode_reference(reference: PayloadReference) -> bytes:
    """Canonical bounded ASCII; no newline. A reference is not a trusted signature."""
    _require(type(reference) is PayloadReference, "EVIDENCE_OBJECT_REFERENCE_INVALID")
    PayloadReference(**asdict(reference))
    raw = _canonical(asdict(reference))
    _require(len(raw) <= MAX_REFERENCE_BYTES, "EVIDENCE_OBJECT_REFERENCE_INVALID")
    return raw


def decode_reference(raw: bytes) -> PayloadReference:
    value = _decode(raw, MAX_REFERENCE_BYTES, "EVIDENCE_OBJECT_REFERENCE_INVALID")
    _require(set(value) == _REFERENCE_KEYS, "EVIDENCE_OBJECT_REFERENCE_INVALID")
    return PayloadReference(**value)


def _reparse(info):
    return bool(getattr(info, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))


def _identity(info):
    _require(type(info.st_ino) is int and info.st_ino > 0, "EVIDENCE_OBJECT_PATH_REFUSED")
    return info.st_dev, info.st_ino


def _file_info(info, maximum):
    _identity(info)  # Unavailable inode identity cannot establish replacement checks.
    _require(stat.S_ISREG(info.st_mode) and not _reparse(info) and info.st_nlink == 1
             and 0 <= info.st_size <= maximum, "EVIDENCE_OBJECT_PATH_REFUSED")


def _lock_file(handle, acquire):
    handle.seek(0)
    if os.name == "nt":
        import msvcrt
        msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK if acquire else msvcrt.LK_UNLCK, 1)
    else:
        import fcntl
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX if acquire else fcntl.LOCK_UN)


@dataclass(frozen=True, kw_only=True)
class EvidenceObjectStore:
    """Immutable configuration for a single-writer object store under explicit root.

    stage() can leave unreferenced objects when interrupted. It returns only
    after manifest and every chunk have been re-read and verified. The returned
    reference is still uncommitted until the external journal/head accepts it.
    read() always verifies actual bytes; it does not use a previous-read cache.
    """
    root: Path
    limits: ObjectLimits

    def __post_init__(self):
        _require(isinstance(self.root, Path) and self.root.is_absolute() and ".." not in self.root.parts
                 and type(self.limits) is ObjectLimits, "EVIDENCE_OBJECT_INPUT_INVALID")
        _require(self.root != self.root.parent, "EVIDENCE_OBJECT_PATH_REFUSED")
        self._paths()

    @property
    def _objects(self):
        return self.root / "objects"

    def _paths(self):
        try:
            checked_target(self.root, "evidence object root")
            for path in reversed((self.root, *self.root.parents)):
                try:
                    info = os.lstat(path)
                except FileNotFoundError:
                    _require(path == self.root, "EVIDENCE_OBJECT_PATH_REFUSED")
                    continue
                _require(stat.S_ISDIR(info.st_mode) and not _reparse(info), "EVIDENCE_OBJECT_PATH_REFUSED")
            try:
                info = os.lstat(self._objects)
            except FileNotFoundError:
                return
            _require(stat.S_ISDIR(info.st_mode) and not _reparse(info), "EVIDENCE_OBJECT_PATH_REFUSED")
        except EvidenceObjectError:
            raise
        except (OSError, ValueError, RuntimeError):
            raise EvidenceObjectError("EVIDENCE_OBJECT_PATH_REFUSED") from None

    def _regular(self, path, maximum):
        self._paths()
        info = os.lstat(path)
        _file_info(info, maximum)
        return info

    def _sync_directory(self, path):
        self._paths()
        if os.name == "nt":
            return  # No portable directory fsync; never claim Windows power-loss durability.
        descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_NOFOLLOW", 0))
        try:
            _require(stat.S_ISDIR(os.fstat(descriptor).st_mode), "EVIDENCE_OBJECT_PATH_REFUSED")
            os.fsync(descriptor)
        finally:
            os.close(descriptor)

    @contextmanager
    def _locked(self, *, create):
        with _PROCESS_LOCK:
            try:
                self._paths()
                if create:
                    self.root.mkdir(mode=0o700, exist_ok=True)
                    self._paths()
                    self._sync_directory(self.root.parent)
                lock = self.root / "objects.lock"
                try:
                    before = self._regular(lock, 1)
                except FileNotFoundError:
                    _require(create, "EVIDENCE_OBJECT_MISSING")
                    before = None
                # Exclusive creation first, then reopen only a checked existing lock.
                if before is None:
                    try:
                        descriptor = os.open(lock, os.O_RDWR | getattr(os, "O_NOFOLLOW", 0)
                                             | getattr(os, "O_NONBLOCK", 0) | os.O_CREAT | os.O_EXCL, 0o600)
                    except FileExistsError:
                        before = self._regular(lock, 1)
                        descriptor = os.open(lock, os.O_RDWR | getattr(os, "O_NOFOLLOW", 0)
                                             | getattr(os, "O_NONBLOCK", 0))
                else:
                    descriptor = os.open(lock, os.O_RDWR | getattr(os, "O_NOFOLLOW", 0)
                                         | getattr(os, "O_NONBLOCK", 0))
                with os.fdopen(descriptor, "r+b") as handle:
                    opened = os.fstat(handle.fileno())
                    _file_info(opened, 1)
                    _require(before is None or _identity(before) == _identity(opened), "EVIDENCE_OBJECT_PATH_REFUSED")
                    _lock_file(handle, True)
                    try:
                        _require(_identity(self._regular(lock, 1)) == _identity(opened), "EVIDENCE_OBJECT_PATH_REFUSED")
                        if create:
                            self._objects.mkdir(mode=0o700, exist_ok=True)
                            self._sync_directory(self.root)
                        self._paths()
                        _require(self._objects.is_dir(), "EVIDENCE_OBJECT_MISSING")
                        # A pending new publication blocks writes, not unrelated
                        # authenticated references. Reads still validate the entire
                        # referenced graph and reject any referenced two-link file.
                        if create:
                            try:
                                os.lstat(self._objects / "pending.blob")
                            except FileNotFoundError:
                                pass
                            else:
                                raise EvidenceObjectError("EVIDENCE_OBJECT_INTERRUPTED_WRITE")
                        yield
                    finally:
                        _lock_file(handle, False)
            except EvidenceObjectError:
                raise
            except FileNotFoundError:
                raise EvidenceObjectError("EVIDENCE_OBJECT_MISSING") from None
            except (OSError, ValueError, RuntimeError, TypeError):
                raise EvidenceObjectError("EVIDENCE_OBJECT_IO_REFUSED") from None

    def _read_file(self, path, maximum):
        before = self._regular(path, maximum)
        descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0))
        with os.fdopen(descriptor, "rb") as handle:
            opened = os.fstat(handle.fileno())
            _file_info(opened, maximum)
            _require(_identity(before) == _identity(opened), "EVIDENCE_OBJECT_PATH_REFUSED")
            raw = handle.read(maximum + 1)
            after = os.fstat(handle.fileno())
            _file_info(after, maximum)
            _require(_identity(after) == _identity(opened) and after.st_size == opened.st_size
                     and len(raw) == opened.st_size, "EVIDENCE_OBJECT_IO_REFUSED")
        current = self._regular(path, maximum)
        _require(_identity(current) == _identity(opened) and current.st_size == opened.st_size,
                 "EVIDENCE_OBJECT_PATH_REFUSED")
        return raw

    def _read_object(self, kind, digest, length):
        _require(_hash(digest) and type(length) is int and length > 0, "EVIDENCE_OBJECT_REFERENCE_INVALID")
        maximum = self.limits.chunk_bytes if kind == "chunk" else self.limits.max_manifest_bytes
        _require(length <= maximum, "EVIDENCE_OBJECT_LIMIT_EXCEEDED")
        raw = self._read_file(self._objects / (digest + ".blob"), length)
        _require(len(raw) == length and _object_digest(kind, raw) == digest, "EVIDENCE_OBJECT_HASH_MISMATCH")
        return raw

    def _publish(self, kind, raw):
        digest = _object_digest(kind, raw)
        target = self._objects / (digest + ".blob")
        try:
            existing = self._read_file(target, len(raw))
        except FileNotFoundError:
            pass
        else:
            _require(existing == raw, "EVIDENCE_OBJECT_HASH_MISMATCH")
            return digest
        pending = self._objects / "pending.blob"
        self._paths()
        descriptor = os.open(pending, os.O_RDWR | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
        with os.fdopen(descriptor, "w+b") as handle:
            _file_info(os.fstat(handle.fileno()), len(raw))
            _require(handle.write(raw) == len(raw), "EVIDENCE_OBJECT_IO_REFUSED")
            handle.flush()
            os.fsync(handle.fileno())
            handle.seek(0)
            _require(handle.read(len(raw) + 1) == raw, "EVIDENCE_OBJECT_HASH_MISMATCH")
        temporary = self._regular(pending, len(raw))
        _require(self._read_file(pending, len(raw)) == raw, "EVIDENCE_OBJECT_HASH_MISMATCH")
        try:
            descriptor = os.open(target, os.O_RDWR | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
        except FileExistsError:
            # Another conforming process is locked out, but never overwrite an
            # independently created destination, even when its hash-name agrees.
            _require(self._read_file(target, len(raw)) == raw, "EVIDENCE_OBJECT_HASH_MISMATCH")
        else:
            # The verified temporary bytes are bounded by the per-object cap.
            # No reference is issued until this copy and the complete graph have
            # passed readback. A crash here preserves pending and partial target.
            with os.fdopen(descriptor, "w+b") as handle:
                _file_info(os.fstat(handle.fileno()), len(raw))
                _require(handle.write(raw) == len(raw), "EVIDENCE_OBJECT_IO_REFUSED")
                handle.flush()
                os.fsync(handle.fileno())
                handle.seek(0)
                _require(handle.read(len(raw) + 1) == raw, "EVIDENCE_OBJECT_HASH_MISMATCH")
        _require(self._read_file(target, len(raw)) == raw, "EVIDENCE_OBJECT_HASH_MISMATCH")
        _require(_identity(self._regular(pending, len(raw))) == _identity(temporary)
                 and self._read_file(pending, len(raw)) == raw, "EVIDENCE_OBJECT_PATH_REFUSED")
        # Only remove this successful publication's own temporary name.
        pending.unlink()
        self._sync_directory(self._objects)
        _require(self._read_file(target, len(raw)) == raw, "EVIDENCE_OBJECT_HASH_MISMATCH")
        return digest

    def _reference(self, reference):
        _require(type(reference) is PayloadReference, "EVIDENCE_OBJECT_REFERENCE_INVALID")
        PayloadReference(**asdict(reference))
        _require(reference.policy_sha256 == self.limits.policy_sha256, "EVIDENCE_OBJECT_POLICY_MISMATCH")
        _require(reference.payload_bytes <= self.limits.max_payload_bytes
                 and reference.manifest_bytes <= self.limits.max_manifest_bytes, "EVIDENCE_OBJECT_LIMIT_EXCEEDED")

    def _prepare(self, payload):
        _require(type(payload) is bytes and len(payload) > 0, "EVIDENCE_OBJECT_INPUT_INVALID")
        size = len(payload)
        count = (size + self.limits.chunk_bytes - 1) // self.limits.chunk_bytes
        _require(size <= self.limits.max_payload_bytes and count <= self.limits.max_chunks,
                 "EVIDENCE_OBJECT_LIMIT_EXCEEDED")
        chunks = tuple(payload[i:i + self.limits.chunk_bytes] for i in range(0, size, self.limits.chunk_bytes))
        manifest = {"schema": SCHEMA, "policy_sha256": self.limits.policy_sha256,
                    "payload_sha256": hashlib.sha256(payload).hexdigest(), "payload_bytes": size,
                    "chunk_bytes": self.limits.chunk_bytes,
                    "chunks": [{"index": i, "bytes": len(chunk), "sha256": _object_digest("chunk", chunk)}
                               for i, chunk in enumerate(chunks)]}
        raw = _canonical(manifest)
        _require(len(raw) <= self.limits.max_manifest_bytes, "EVIDENCE_OBJECT_LIMIT_EXCEEDED")
        reference = PayloadReference(schema=SCHEMA, manifest_sha256=_object_digest("manifest", raw),
                                     manifest_bytes=len(raw), payload_sha256=manifest["payload_sha256"],
                                     payload_bytes=size, policy_sha256=self.limits.policy_sha256)
        return reference, raw, chunks

    def _read(self, reference):
        self._reference(reference)
        raw = self._read_object("manifest", reference.manifest_sha256, reference.manifest_bytes)
        manifest = _decode(raw, self.limits.max_manifest_bytes, "EVIDENCE_OBJECT_MANIFEST_INVALID")
        _require(set(manifest) == _MANIFEST_KEYS and type(manifest["schema"]) is int and manifest["schema"] == SCHEMA
                 and manifest["policy_sha256"] == reference.policy_sha256
                 and _hash(manifest["payload_sha256"]) and manifest["payload_sha256"] == reference.payload_sha256
                 and type(manifest["payload_bytes"]) is int and manifest["payload_bytes"] == reference.payload_bytes
                 and type(manifest["chunk_bytes"]) is int and manifest["chunk_bytes"] == self.limits.chunk_bytes
                 and type(manifest["chunks"]) is list
                 and 0 < len(manifest["chunks"]) <= self.limits.max_chunks, "EVIDENCE_OBJECT_MANIFEST_INVALID")
        expected_count = (reference.payload_bytes + self.limits.chunk_bytes - 1) // self.limits.chunk_bytes
        _require(len(manifest["chunks"]) == expected_count, "EVIDENCE_OBJECT_MANIFEST_INVALID")
        # Validate every descriptor before reading any payload object. Repeated
        # content hashes are valid deduplication; repeated/missing indices are not.
        for i, item in enumerate(manifest["chunks"]):
            expected_size = min(self.limits.chunk_bytes, reference.payload_bytes - i * self.limits.chunk_bytes)
            _require(type(item) is dict and set(item) == _CHUNK_KEYS and type(item["index"]) is int
                     and item["index"] == i and type(item["bytes"]) is int and item["bytes"] == expected_size
                     and _hash(item["sha256"]), "EVIDENCE_OBJECT_MANIFEST_INVALID")
        payload = b"".join(self._read_object("chunk", item["sha256"], item["bytes"])
                           for item in manifest["chunks"])
        _require(len(payload) == reference.payload_bytes and hashlib.sha256(payload).hexdigest() == reference.payload_sha256,
                 "EVIDENCE_OBJECT_HASH_MISMATCH")
        return payload

    def stage(self, payload: bytes) -> PayloadReference:
        """Validate admission before I/O, then publish objects; never commit a history slot."""
        reference, manifest, chunks = self._prepare(payload)
        with self._locked(create=True):
            for chunk in chunks:
                self._publish("chunk", chunk)
            self._publish("manifest", manifest)
            # Also flush when every object was reused. A previous publication
            # may have removed its temporary name and then failed directory
            # fsync; retrying must not turn that failed durability step into a
            # successful reference merely because all final names now exist.
            self._sync_directory(self._objects)
            _require(self._read(reference) == payload, "EVIDENCE_OBJECT_HASH_MISMATCH")
        return reference

    def read(self, reference: PayloadReference) -> bytes:
        """Return exact validated bytes or refuse; never repair/adopt missing evidence."""
        self._reference(reference)
        with self._locked(create=False):
            return self._read(reference)
