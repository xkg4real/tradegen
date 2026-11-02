"""Independent latest-head record beside a durable chain: compare-and-set to a committed successor only.

One digest-only record (``<root>/<name>/head.json``) in a separately provisioned root, with its own OS byte lock,
fsync and atomic replace. ``read()`` returns the retained head. ``compare_and_set(old, new)`` advances only to a
digest that the injected chain already holds durably as the direct successor of ``old``; for the checkpoint store
that is ``CheckpointChain`` (the committed BaselineState whose ``previous_state_digest`` is ``old``). Another
durable chain (the live-history journal) instantiates its own head with its own name and chain check.
Initialization is an explicit, reviewed, one-time operator step with no runtime caller.

Defended: a crash between the checkpoint replace and the head replace; a rollback of either root alone; mutation,
truncation, non-canonical or duplicate-key records, hard links and junctions; a second process on the same roots;
accidental re-initialization; a caller asking for a digest the chain does not hold as the committed successor.
Not defended: code running as the same Windows user (it can rewrite both roots coherently), and a coherent
rollback of both roots. No frame is retained durably in this phase, so an old coherent rollback is refused only by
the 30 s freshness rules (the reducer's maximum interval and ``risk_baseline``) and by the fixed driver's 30 s
account-anchor rule; a coherent rollback younger than 30 s followed by a fresh honest interval is indistinguishable
from an ordinary tick. Recovery after any refusal is an owner-performed reviewed re-anchor (both roots moved aside
as evidence, a new reviewed anchor, ``store.seed``, ``initialize_reviewed_head``), never an in-code adoption of a
local digest. There is no directory fsync on Windows and no durability claim beyond fsync plus atomic replace.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import json
import ntpath
import os
from pathlib import Path
import re
import stat
from threading import Lock

from core.isolation import checked_target, state_root
from execution_accounts.baseline_store import CheckpointStore, _lock_file
from execution_control.store import _sync_directory

_MAX_BYTES = 4096
_HASH = re.compile(r"[0-9a-f]{64}")
_NAME = re.compile(r"[a-z][a-z0-9-]{0,63}")
_DRIVE = re.compile(r"[A-Za-z]:")
_REPO = Path(__file__).resolve().parents[1]
_PROCESS_LOCK = Lock()               # own lock: the chain check may take the checkpoint store's lock
_FLAGS = getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_BINARY", 0) | getattr(os, "O_NONBLOCK", 0)
_NAMES = ("head.json", "head.tmp", "head.lock")


class BaselineHeadError(ValueError):
    """Fixed UPPER_SNAKE codes; never paths, digests, amounts or OS messages."""


def _require(ok, code):
    if not ok:
        raise BaselineHeadError(code)


def _digest(value):
    _require(type(value) is str and _HASH.fullmatch(value) is not None, "HEAD_DIGEST_REQUIRED")
    return value


@dataclass(frozen=True, kw_only=True)
class HeadRecord:
    schema_version: int        # exactly 1
    baseline_sequence: int     # the chain sequence of `head`, 0 <= n < 2**63
    head: str                  # 64 lowercase hex


def _record_bytes(record):
    return json.dumps({"baseline_sequence": record.baseline_sequence, "head": record.head,
                       "schema_version": record.schema_version},
                      sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")


def _parse(raw):
    def pairs(items):
        out = {}
        for key, value in items:
            _require(key not in out, "HEAD_RECORD_INVALID")
            out[key] = value
        return out

    def invalid(_):
        raise BaselineHeadError("HEAD_RECORD_INVALID")
    try:
        body = json.loads(raw.decode("ascii"), object_pairs_hook=pairs, parse_float=invalid, parse_constant=invalid)
    except BaselineHeadError:
        raise
    except (ValueError, UnicodeError, RecursionError):
        raise BaselineHeadError("HEAD_RECORD_INVALID") from None
    _require(type(body) is dict and set(body) == {"baseline_sequence", "head", "schema_version"}
             and type(body["schema_version"]) is int and body["schema_version"] == 1
             and type(body["baseline_sequence"]) is int and 0 <= body["baseline_sequence"] < 2**63
             and type(body["head"]) is str and _HASH.fullmatch(body["head"]) is not None, "HEAD_RECORD_INVALID")
    record = HeadRecord(**body)
    _require(_record_bytes(record) == raw, "HEAD_RECORD_INVALID")
    return record


class CheckpointChain:
    """The reviewed checkpoint store as the chain behind a head: seed shape at initialization, the committed
    direct successor at every advance. The store's own lock and digest checks run inside each call."""
    def __init__(self, store: CheckpointStore) -> None:
        _require(type(store) is CheckpointStore, "HEAD_STORE_REQUIRED")
        self._store = store

    def seed(self, digest: str) -> int:
        state = self._store.load(expected_head=digest)
        _require(not state.previous_state_digest and not state.last_interval_digest, "HEAD_SEED_REQUIRED")
        return state.sequence

    def successor(self, old: str, new: str) -> int:
        state = self._store.load(expected_head=new)
        _require(state.previous_state_digest == old, "HEAD_TRANSITION_UNVERIFIED")
        return state.sequence


class BaselineHead:
    """Fixed filenames below an explicit, operator-provisioned, link-free local root that neither contains nor lies
    inside the state root or the repository. Construction reads metadata and creates nothing; only
    initialize_reviewed_head creates the directory. Every operation re-checks the paths, then takes the process
    lock and the OS byte lock, and refuses an interrupted write.
    """
    def __init__(self, *, root: Path, name: str, chain) -> None:
        _require(callable(getattr(chain, "seed", None)) and callable(getattr(chain, "successor", None)),
                 "HEAD_CHAIN_REQUIRED")
        _require(type(name) is str and _NAME.fullmatch(name) is not None and not ntpath.isreserved(name),
                 "HEAD_NAME_REQUIRED")
        _require(isinstance(root, Path) and root.is_absolute(), "HEAD_EXPLICIT_ROOT_REQUIRED")
        self._chain, self._root, self._dir = chain, root, root / name
        self._paths()

    def _paths(self):
        try:
            if os.name == "nt":
                _require(_DRIVE.fullmatch(self._root.drive) is not None, "HEAD_LOCAL_ROOT_REQUIRED")
            for path in (self._root, *self._root.parents, self._dir):
                _require(not path.is_symlink() and not path.is_junction(), "HEAD_LINK_REFUSED")
            _require(self._root.is_dir(), "HEAD_ROOT_REFUSED")
            resolved = self._root.resolve()
            for other in (state_root().absolute().resolve(), _REPO):
                _require(not resolved.is_relative_to(other) and not other.is_relative_to(resolved),
                         "HEAD_ROOT_NOT_SEPARATE")
            checked_target(self._root, "baseline head root")
            checked_target(self._dir, "baseline head directory", within=self._root)
            for name in _NAMES:
                target = self._dir / name
                _require(not target.is_symlink() and not target.is_junction(), "HEAD_LINK_REFUSED")
                if target.exists():
                    info = os.lstat(target)
                    _require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and info.st_size <= _MAX_BYTES,
                             "HEAD_FILE_REFUSED")
                checked_target(target, "baseline head file", within=self._dir)
        except BaselineHeadError:
            raise
        except (OSError, ValueError, RuntimeError):
            raise BaselineHeadError("HEAD_ROOT_REFUSED") from None

    @contextmanager
    def _locked(self, *, create=False):
        with _PROCESS_LOCK:
            try:
                self._paths()
                if create:
                    checked_target(self._dir, "baseline head directory", within=self._root).mkdir(mode=0o700, exist_ok=True)
                else:
                    _require((self._dir / "head.lock").exists(), "HEAD_NOT_INITIALIZED")
                descriptor = os.open(checked_target(self._dir / "head.lock", "baseline head lock", within=self._dir),
                                     os.O_RDWR | (os.O_CREAT if create else 0) | _FLAGS, 0o600)
                with os.fdopen(descriptor, "r+b") as handle:
                    info = os.fstat(handle.fileno())
                    _require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and info.st_size <= _MAX_BYTES,
                             "HEAD_FILE_REFUSED")
                    _lock_file(handle, True)
                    try:
                        self._paths()
                        _require(not (self._dir / "head.tmp").exists(), "HEAD_INTERRUPTED_WRITE")
                        yield
                    finally:
                        _lock_file(handle, False)
            except BaselineHeadError:
                raise
            except (OSError, ValueError, RuntimeError, TypeError):
                raise BaselineHeadError("HEAD_IO_REFUSED") from None

    def _record(self):
        target = self._dir / "head.json"
        _require(target.exists(), "HEAD_NOT_INITIALIZED")
        descriptor = os.open(checked_target(target, "baseline head record", within=self._dir), os.O_RDONLY | _FLAGS)
        with os.fdopen(descriptor, "rb") as handle:
            info = os.fstat(handle.fileno())
            _require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and info.st_size <= _MAX_BYTES,
                     "HEAD_FILE_REFUSED")
            raw = handle.read(_MAX_BYTES+1)
        _require(len(raw) <= _MAX_BYTES, "HEAD_FILE_REFUSED")
        return _parse(raw)

    def _write(self, record):
        raw = _record_bytes(record)
        _require(_parse(raw) == record, "HEAD_RECORD_INVALID")
        descriptor = os.open(checked_target(self._dir / "head.tmp", "baseline head temporary file", within=self._dir),
                             os.O_WRONLY | os.O_CREAT | os.O_EXCL | _FLAGS, 0o600)
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(checked_target(self._dir / "head.tmp", "baseline head temporary file", within=self._dir),
                   checked_target(self._dir / "head.json", "baseline head record", within=self._dir))
        _sync_directory(self._dir)

    def initialize_reviewed_head(self, reviewed_head: str) -> HeadRecord:
        """Explicit one-time setup with the digest the operator retained from the reviewed anchor. The chain must
        already hold it in seed shape; an advanced chain is never adopted into a fresh head. A refusal creates
        nothing. The code cannot prove the review; it only stops implicit or repeated initialization."""
        _digest(reviewed_head)
        self._paths()
        _require(not (self._dir / "head.json").exists(), "HEAD_ALREADY_INITIALIZED")
        try:
            sequence = self._chain.seed(reviewed_head)
        except Exception:
            raise BaselineHeadError("HEAD_SEED_REQUIRED") from None
        _require(type(sequence) is int, "HEAD_SEED_REQUIRED")
        record = HeadRecord(schema_version=1, baseline_sequence=sequence, head=reviewed_head)
        with self._locked(create=True):
            _require(not (self._dir / "head.json").exists(), "HEAD_ALREADY_INITIALIZED")
            self._write(record)
        return record

    def read(self) -> str:
        """The retained head; re-read from the file on every call, never created, repaired or cached."""
        with self._locked():
            return self._record().head

    def compare_and_set(self, old: str, new: str) -> bool:
        """Exact True only after the record naming `new` is fsynced and atomically in place. False only when the
        current head differs from `old` (nothing is written and the chain is not read). Every other failure is a
        fixed code; `new` must be the chain's committed direct successor of `old` with the next sequence."""
        _digest(old); _digest(new)
        with self._locked():
            record = self._record()
            if record.head != old:
                return False
            try:
                sequence = self._chain.successor(old, new)
            except Exception:
                raise BaselineHeadError("HEAD_TRANSITION_UNVERIFIED") from None
            _require(type(sequence) is int and sequence == record.baseline_sequence+1, "HEAD_TRANSITION_UNVERIFIED")
            self._write(HeadRecord(schema_version=1, baseline_sequence=sequence, head=new))
        return True
