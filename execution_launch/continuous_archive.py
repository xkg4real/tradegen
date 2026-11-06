"""Private candidate audit storage; never a source verifier or restart authority.

The launch integration owns this explicit file effect. Account path recording,
coverage checks and valuation remain free of filesystem writes. This archive
contains only the candidate path, not its independently verified coverage receipt.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import stat

from core.isolation import checked_target, state_root
from execution_accounts.continuous import ContinuousEvidenceError, validate_path
from execution_accounts.model import canonical, content_digest

MAX_ARCHIVE_BYTES = 32 * 1024 * 1024


def _require(ok, code):
    if not ok:
        raise ContinuousEvidenceError(code)


def archive_candidate(path, *, root: Path):
    """Create one immutable private candidate record before returning a preview.

    Partial/tampered existing records refuse; no append, repair or resume
    operation exists. A crash leaves an unusable record for review. The record
    does not authenticate the source or supply a trusted restart anchor.
    """
    try:
        path = validate_path(path)
        _require(isinstance(root, Path) and root.is_absolute() and root == state_root().absolute(),
                 "CONTINUOUS_ARCHIVE_ROOT_MISMATCH")
        candidate_sha = content_digest(path)
        try:
            checked_target(root, "continuous root")
            directory = checked_target(root / "execution-price-paths", "continuous archive", within=root)
            checked_target(root / "execution-price-paths", "continuous archive", within=root).mkdir(
                mode=0o700, parents=True, exist_ok=True)
            target = checked_target(directory / (candidate_sha + ".json"), "continuous candidate", within=directory)
        except (OSError, ValueError, RuntimeError):
            raise ContinuousEvidenceError("CONTINUOUS_ARCHIVE_PATH_REFUSED") from None
        payload = (json.dumps(canonical(path), ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n").encode()
        _require(len(payload) <= MAX_ARCHIVE_BYTES, "CONTINUOUS_ARCHIVE_SIZE_REFUSED")
        try:
            descriptor = os.open(checked_target(directory / (candidate_sha + ".json"), "continuous candidate", within=directory),
                                 os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
        except FileExistsError:
            descriptor = os.open(target, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
            with os.fdopen(descriptor, "rb") as fh:
                info = os.fstat(fh.fileno())
                _require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1
                         and info.st_size <= MAX_ARCHIVE_BYTES, "CONTINUOUS_ARCHIVE_PATH_REFUSED")
                _require(fh.read(MAX_ARCHIVE_BYTES+1) == payload, "CONTINUOUS_ARCHIVE_CHANGED")
            return candidate_sha
        with os.fdopen(descriptor, "wb") as fh:
            info = os.fstat(fh.fileno())
            _require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1, "CONTINUOUS_ARCHIVE_PATH_REFUSED")
            fh.write(payload)
            fh.flush()
            os.fsync(fh.fileno())
        if os.name != "nt":
            descriptor = os.open(directory, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
            try:
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
        return candidate_sha
    except ContinuousEvidenceError:
        raise
    except (OSError, ValueError, TypeError, RuntimeError):
        raise ContinuousEvidenceError("CONTINUOUS_ARCHIVE_REFUSED") from None
