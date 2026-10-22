"""Hash-chained `governance_events.jsonl` appender and verifier (section 6.6; R-32; TASK-M0-07).

One canonical-JSON line per event. `prev_row_md5` is the md5 of the previous line's exact bytes
(without its LF), null only on the first line. Binary append, LF only, a failed write raises.
A line is a log record, not an artifact: it carries only its own fields (section 6 closed object).
"""
from __future__ import annotations

import json
import os
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, NamedTuple

from core.ficc.macro_schema import canonical_json, enum_of, load_schema, md5_hex, validate

# One source for the shape: the enums and the required set come from the registry schema (section 6.6).
SCHEMA = "quantgen.governance_event"
SCHEMA_VERSION = "2.0"
KINDS = enum_of("governance_event", "/kind")
ACTORS = enum_of("governance_event", "/actor")
REQUIRED = tuple(load_schema("governance_event")["required"])
# ponytail: one in-process lock serialises read-tail -> append (two threads would fork the chain); a second
# process (CLI beside the app) needs a lock file before Live runs both at once.
_APPEND_LOCK = threading.Lock()


def iso_utc(instant: datetime) -> str:
    if instant.tzinfo is None:
        raise ValueError("governance: instants must be tz-aware UTC")
    return instant.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def validate_event(event) -> list[str]:
    """[] = valid; messages are '<json-pointer>: <message>' from the registry validator."""
    return validate("governance_event", event)


def _lines(path: Path) -> list[bytes]:
    if not path.exists():
        return []
    rows = path.read_bytes().split(b"\n")
    if rows and rows[-1] == b"":
        rows.pop()
    return rows


def last_row_md5(path: Path) -> str | None:
    rows = _lines(Path(path))
    return md5_hex(rows[-1]) if rows else None


def append_event(path: Path, event: dict, clock: Callable[[], datetime] | None = None) -> str:
    """Complete `event` in place (schema, event_id, utc from `clock`, prev_row_md5), validate, append.

    Returns the md5 of the written line. Raises before writing on any validation error and on a
    `prev_row_md5` the caller supplied that does not match the file. Never swallows a write error.
    """
    path = Path(path)
    event.setdefault("schema", SCHEMA)
    event.setdefault("schema_version", SCHEMA_VERSION)
    event.setdefault("event_id", uuid.uuid4().hex)
    if "utc" not in event:
        if clock is None:
            raise ValueError("append_event: the event has no utc and no clock was given")
        event["utc"] = iso_utc(clock())
    for k in ("book_id", "rule_id", "key"):
        event.setdefault(k, None)
    event.setdefault("refs", [])
    with _APPEND_LOCK:
        expected = last_row_md5(path)
        if event.get("prev_row_md5", expected) != expected:
            raise ValueError("append_event: prev_row_md5 does not match the last line of the log")
        event["prev_row_md5"] = expected
        errs = validate_event(event)
        if errs:
            raise ValueError("governance event refused: " + "; ".join(errs))
        line = canonical_json(event).encode("utf-8")
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "ab") as fh:
            fh.write(line + b"\n")
            fh.flush()
            os.fsync(fh.fileno())
        return md5_hex(line)


class ChainCheck(NamedTuple):
    ok: bool
    n_rows: int
    first_bad_line: int | None

    def __bool__(self) -> bool:      # `if verify_chain(p):` reads as "chain intact"
        return self.ok


def verify_chain(path: Path) -> ChainCheck:
    """Re-hash every line's raw bytes; a hand edit, a reformat or a dropped line breaks the chain."""
    prev = None
    n = 0
    for lineno, raw in enumerate(_lines(Path(path)), start=1):
        try:
            event = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, ValueError):
            return ChainCheck(False, n, lineno)
        if (not isinstance(event, dict) or validate_event(event) or event["prev_row_md5"] != prev
                or canonical_json(event).encode("utf-8") != raw):
            return ChainCheck(False, n, lineno)
        prev = md5_hex(raw)
        n += 1
    return ChainCheck(True, n, None)


def read_events(path: Path) -> list[dict]:
    """Every event of an intact chain; refuses a broken one (fail closed)."""
    check = verify_chain(path)
    if not check.ok:
        raise ValueError(f"governance log broken at line {check.first_bad_line}: {path}")
    return [json.loads(raw.decode("utf-8")) for raw in _lines(Path(path))]
