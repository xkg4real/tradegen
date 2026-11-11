"""The daily Upbit universe snapshot store (spec section 5). write_snapshot writes one snapshot once, content
addressed, as owner.universe_path(day, sha256), through a new temporary file, fsync and a rename to a name that does
not exist yet. It never replaces a file, so a rebuild adds a file and never changes one that a session or history
row already names."""
from __future__ import annotations

import contextlib
from datetime import date
import os
from pathlib import Path
import re

from core.compliance import owner
from core.isolation import checked_target, state_root

_SHA = re.compile(r"[0-9a-f]{64}")
_FLAGS = getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NOINHERIT", 0)


class UniverseStoreError(ValueError):
    """A fixed refusal code; no path or body is quoted."""


def _require(condition, code):
    if not condition:
        raise UniverseStoreError(code)


def write_snapshot(raw: bytes, day: date, sha256: str) -> Path:
    """Write `raw` once as owner.universe_path(day, sha256) and return that path. An existing snapshot is refused
    (UNIVERSE_SNAPSHOT_EXISTS) and kept; any failure removes the temporary file. The caller verified `raw`; this
    function checks only the shape of its arguments."""
    _require(type(raw) is bytes and len(raw) > 0 and type(day) is date and type(sha256) is str
             and _SHA.fullmatch(sha256) is not None, "UNIVERSE_STORE_INPUT_INVALID")
    try:
        root = state_root()
        directory, target = owner.universe_dir(day), owner.universe_path(day, sha256)
        _require(target.parent == directory, "UNIVERSE_STORE_PATH_REFUSED")
        _require(not target.exists(), "UNIVERSE_SNAPSHOT_EXISTS")
        checked_target(directory, "universe directory", within=root).mkdir(mode=0o700, parents=True, exist_ok=True)
        name = "." + sha256 + "." + os.urandom(6).hex() + ".tmp"
        descriptor = os.open(checked_target(directory / name, "universe temporary file", within=directory),
                             os.O_WRONLY | os.O_CREAT | os.O_EXCL | _FLAGS, 0o600)
        try:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(raw)
                handle.flush()
                os.fsync(handle.fileno())
            # ponytail: Windows rename refuses an existing name; a POSIX rename would replace a file that appeared
            # since the check above (the same content-addressed bytes). Use link plus unlink if POSIX ever matters.
            os.rename(checked_target(directory / name, "universe temporary file", within=directory),
                      checked_target(target, "universe snapshot", within=directory))
        except BaseException:
            with contextlib.suppress(OSError, RuntimeError):
                os.unlink(checked_target(directory / name, "universe temporary file", within=directory))
            raise
    except UniverseStoreError:
        raise
    except FileExistsError:
        raise UniverseStoreError("UNIVERSE_SNAPSHOT_EXISTS") from None
    except (OSError, RuntimeError, ValueError):
        raise UniverseStoreError("UNIVERSE_STORE_REFUSED") from None
    return target
