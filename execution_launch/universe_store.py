"""The daily Upbit universe snapshot store and its command (spec section 5).

    python -m execution_launch.universe_store snapshot --state-root <root>

builds the snapshot of today's UTC candle day under the Upbit universe rule of the newest approved state and writes
it with write_snapshot. It refuses unless <root> is this process's state root (TRADEGEN_HOME), and a failed read or
build writes nothing. write_snapshot writes one snapshot once, content addressed, as owner.universe_path(day,
sha256), through a new temporary file, fsync and a rename to a name that does not exist yet. It never replaces a
file, so a rebuild adds a file and never changes one that a session or history row already names. The owner
registers the command in Windows Task Scheduler (09:12 KST, retry 09:27 KST); no code creates the task."""
from __future__ import annotations

import contextlib
from datetime import date, datetime, timezone
import json
import os
from pathlib import Path
import re
import sys

from core.compliance import owner, rules
from core.isolation import checked_target, state_root
from execution_accounts.universe import UniverseReadError, build_universe_snapshot

_SHA = re.compile(r"[0-9a-f]{64}")
_FLAGS = getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NOINHERIT", 0)
_CODE = re.compile(r"[A-Z][A-Z0-9_]{0,95}")


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
            # ponytail: Windows rename refuses an existing name; a POSIX rename would silently replace a snapshot that
            # appeared since the check above (same name, so same bytes only when the caller passes verified builder
            # output, as main does). os.link is no upgrade: core.isolation.scan_links refuses hard links in state_root.
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


def _wall_clock() -> datetime:
    """The PC clock, aware UTC: the candle day and every receipt's received_at."""
    return datetime.now(timezone.utc)


def _active_rule() -> rules.UniverseRule:
    """The Upbit universe rule of the newest approved state on disk; UNIVERSE_NO_RULE when there is none.
    execution_launch never references load_context, so the approved venue facts are read directly."""
    state = owner.latest_snapshot()
    venue = None if state is None or state.venues is None else state.venues.venues.get("upbit")
    rule = None if venue is None else venue.universe_rule
    _require(type(rule) is rules.UniverseRule, "UNIVERSE_NO_RULE")
    return rule


def _code(exc: BaseException) -> str:
    """A refusal code worth printing: the fixed code of a universe refusal, else one generic code (no text leaks)."""
    text = str(exc)
    known = isinstance(exc, (UniverseStoreError, UniverseReadError, rules.UniverseError))
    return text if known and _CODE.fullmatch(text) is not None else "UNIVERSE_SNAPSHOT_REFUSED"


def main(argv=None) -> int:
    """`snapshot --state-root <root>`: build today's (UTC) snapshot and write it once. Prints one JSON line; returns
    0 when a file was written, 2 when nothing was written."""
    args = sys.argv[1:] if argv is None else list(argv)
    try:
        _require(len(args) == 3 and args[0] == "snapshot" and args[1] == "--state-root",
                 "UNIVERSE_ARGUMENTS_INVALID")
        explicit = Path(args[2])
        _require(explicit.is_absolute() and explicit == state_root().absolute(), "UNIVERSE_STATE_ROOT_MISMATCH")
        rule = _active_rule()
        day = _wall_clock().astimezone(timezone.utc).date()
        raw, sha256 = build_universe_snapshot(rule, day, clock=_wall_clock)
        write_snapshot(raw, day, sha256)
    except Exception as exc:
        print(json.dumps({"command": "snapshot", "written": False, "reasons": [_code(exc)]}, sort_keys=True))
        return 2
    print(json.dumps({"command": "snapshot", "written": True, "day": day.isoformat(), "snapshot_sha256": sha256},
                     sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
