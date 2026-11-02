"""Explicit private baseline checkpoint storage, not an anti-rollback authority.

A separately trusted expected head must accompany every read and write. A crash
between this file's replacement and external head advancement causes a mismatch;
the store refuses to choose or repair an authoritative head on its own.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import os
from pathlib import Path
import stat
from threading import Lock

from core.compliance.model import KST
from core.isolation import checked_target, state_root
from execution_accounts.baseline import BaselineError, BaselineState, restore_state, state_json

_MAX_BYTES = 65536
_PROCESS_LOCK = Lock()


class CheckpointError(ValueError):
    """Fixed diagnostic codes, never private paths, source records or amounts."""


def _require(ok, code):
    if not ok:
        raise CheckpointError(code)


def _lock_file(handle, acquire):
    handle.seek(0)
    if os.name == "nt":
        import msvcrt
        msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK if acquire else msvcrt.LK_UNLCK, 1)
    else:
        import fcntl
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX if acquire else fcntl.LOCK_UN)


@dataclass(frozen=True, kw_only=True)
class CommitReceipt:
    previous_head: str | None
    new_head: str
    sequence: int


class CheckpointStore:
    """Fixed filenames below explicit TRADEGEN_HOME/execution-baseline.

    Construction reads path metadata but creates nothing. Only seed/commit may
    create private state. load requires an existing lock and checkpoint. The
    existing path-isolation contract is reused; hostile arbitrary-code processes
    with access to both storage and the trusted head remain outside that boundary.
    """
    def __init__(self, *, root: Path):
        try:
            _require(isinstance(root, Path) and root.is_absolute(), "BASELINE_STORE_EXPLICIT_ROOT_REQUIRED")
            self._base = root.absolute()
            self._root = self._base / "execution-baseline"
            self._paths()
        except CheckpointError:
            raise
        except (OSError, ValueError, RuntimeError):
            raise CheckpointError("BASELINE_STORE_ROOT_REFUSED") from None

    def _paths(self):
        _require(self._base == state_root().absolute(), "BASELINE_STORE_ROOT_MISMATCH")
        # The selected base and existing ancestors are checked on every operation.
        for path in (self._base, *self._base.parents):
            _require(not path.is_symlink() and not path.is_junction(), "BASELINE_STORE_LINK_REFUSED")
        checked_target(self._base, "baseline state root")
        checked_target(self._root, "baseline directory", within=self._base)
        for name in ("checkpoint.json", "checkpoint.tmp", "checkpoint.lock"):
            target = checked_target(self._root / name, "baseline file", within=self._root)
            if target.exists():
                info = target.stat()
                _require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and info.st_size <= _MAX_BYTES,
                         "BASELINE_STORE_FILE_REFUSED")
        return self._root

    @contextmanager
    def _locked(self, *, create=False):
        with _PROCESS_LOCK:
            try:
                self._paths()
                if create:
                    checked_target(self._root, "baseline directory", within=self._base).mkdir(mode=0o700, exist_ok=True)
                target = checked_target(self._root / "checkpoint.lock", "baseline lock", within=self._root)
                flags = os.O_RDWR | (os.O_CREAT if create else 0)
                descriptor = os.open(target, flags | getattr(os, "O_NOFOLLOW", 0)
                                     | getattr(os, "O_NONBLOCK", 0), 0o600)
                with os.fdopen(descriptor, "r+b") as handle:
                    info = os.fstat(handle.fileno())
                    _require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and info.st_size <= _MAX_BYTES,
                             "BASELINE_STORE_FILE_REFUSED")
                    _lock_file(handle, True)
                    try:
                        self._paths()
                        _require(not (self._root / "checkpoint.tmp").exists(), "BASELINE_STORE_INTERRUPTED_WRITE")
                        yield
                    finally:
                        _lock_file(handle, False)
            except (CheckpointError, BaselineError):
                raise
            except (OSError, ValueError, RuntimeError, TypeError):
                raise CheckpointError("BASELINE_STORE_IO_REFUSED") from None

    def _load(self, expected_head):
        target = checked_target(self._root / "checkpoint.json", "baseline checkpoint", within=self._root)
        descriptor = os.open(target, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
                             | getattr(os, "O_NONBLOCK", 0))
        with os.fdopen(descriptor, "rb") as handle:
            info = os.fstat(handle.fileno())
            _require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and info.st_size <= _MAX_BYTES,
                     "BASELINE_STORE_FILE_REFUSED")
            raw = handle.read(_MAX_BYTES+1)
        _require(len(raw) <= _MAX_BYTES, "BASELINE_STORE_FILE_REFUSED")
        return restore_state(raw, expected_head=expected_head)

    def load(self, *, expected_head: str) -> BaselineState:
        with self._locked():
            return self._load(expected_head)

    def _write(self, state):
        # Validate before opening a temp file. No caller-controlled filename exists.
        raw = state_json(state).encode("utf-8")
        restore_state(raw, expected_head=state.state_digest)
        _require(len(raw) <= _MAX_BYTES, "BASELINE_STORE_FILE_REFUSED")
        target = checked_target(self._root / "checkpoint.tmp", "baseline temporary file", within=self._root)
        descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(checked_target(self._root / "checkpoint.tmp", "baseline temporary file", within=self._root),
                   checked_target(self._root / "checkpoint.json", "baseline checkpoint", within=self._root))
        if os.name != "nt":
            descriptor = os.open(checked_target(self._root, "baseline directory", within=self._base), os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(descriptor)
            finally:
                os.close(descriptor)

    def seed(self, state: BaselineState, *, expected_head: str) -> CommitReceipt:
        """Explicit first setup: externally reviewed head and an empty local store."""
        restored = restore_state(state_json(state), expected_head=expected_head)
        _require(not restored.previous_state_digest and not restored.last_interval_digest,
                 "BASELINE_STORE_ANCHOR_REQUIRED")
        _require(restored.recovery_checkpoint is None or restored.recovery_checkpoint.cutoff_at == restored.asof,
                 "BASELINE_STORE_RECOVERY_ANCHOR_REFUSED")
        with self._locked(create=True):
            _require(not (self._root / "checkpoint.json").exists(), "BASELINE_STORE_ALREADY_INITIALIZED")
            self._write(restored)
        return CommitReceipt(previous_head=None, new_head=restored.state_digest, sequence=restored.sequence)

    def commit(self, state: BaselineState, *, expected_previous_head: str) -> CommitReceipt:
        restored = restore_state(state_json(state), expected_head=state.state_digest)
        with self._locked():
            previous = self._load(expected_previous_head)
            _require(restored.previous_state_digest == previous.state_digest
                     and restored.sequence == previous.sequence+1 and restored.asof > previous.asof,
                     "BASELINE_STORE_TRANSITION_REFUSED")
            for name in ("schema_version", "account_scope", "conventions", "first_trading_day",
                         "approved_effective_floor", "anchor_sha256"):
                _require(getattr(restored, name) == getattr(previous, name), "BASELINE_STORE_ANCHOR_CHANGED")
            _require(restored.high_watermark >= previous.high_watermark, "BASELINE_STORE_PEAK_ROLLBACK")
            if previous.asof.astimezone(KST).date() == restored.asof.astimezone(KST).date():
                _require(restored.day_start_equity == previous.day_start_equity
                         and restored.observed_daily_loss >= previous.observed_daily_loss,
                         "BASELINE_STORE_DAILY_HISTORY_CHANGED")
                if previous.recovery_checkpoint is not None:
                    _require(restored.recovery_checkpoint == previous.recovery_checkpoint,
                             "BASELINE_STORE_RECOVERY_CHANGED")
                elif restored.recovery_checkpoint is not None:
                    _require(previous.asof < restored.recovery_checkpoint.cutoff_at == restored.asof,
                             "BASELINE_STORE_RECOVERY_CHANGED")
            self._write(restored)
        return CommitReceipt(previous_head=previous.state_digest, new_head=restored.state_digest,
                             sequence=restored.sequence)
