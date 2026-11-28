"""Read existing TRADEGEN alert records. Only opaque deduplication IDs leave these adapters."""
from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from decimal import Decimal, InvalidOperation
import hashlib
import json
import os
from pathlib import Path
import stat

from core.compliance import alerts, model
from core.isolation import checked_target
from execution import checks
from execution_control.store import Journal


MAX_LOG_BYTES = 16 * 1024 * 1024
MAX_LINE_BYTES = 256 * 1024
MAX_ROWS = 100_000


class SourceError(RuntimeError):
    """The configured source could not be read completely. No partial batch is returned."""


def _event_id(source: str, identity: str) -> str:
    data = ("tradegen-notification-v1\0" + source + "\0" + identity).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def scan_control(root: Path) -> tuple[str, ...]:
    """Read the anchored control journal. Report each floor halt and the first daily stop per KST day."""
    try:
        root = Path(root)
        if not root.is_absolute() or ".." in root.parts:
            raise ValueError
        rows = Journal(root=root, require_existing=True).snapshot()
        events = []
        stopped_days = set()
        for row in rows:
            data = row["data"]
            if row["kind"] == "risk_snapshot":
                day = datetime.fromisoformat(row["utc"]).astimezone(model.KST).date().isoformat()
                stopped = data.get("daily_stopped")
                if data.get("day") != day or type(stopped) is not bool or (day in stopped_days and not stopped):
                    raise ValueError
                if not stopped or day in stopped_days:
                    continue
                stopped_days.add(day)
            elif row["kind"] == "halt":
                if set(data) != {"floor"} or type(data["floor"]) is not str:
                    raise ValueError
                floor = Decimal(data["floor"])
                if not floor.is_finite() or floor < 0:
                    raise ValueError
            else:
                continue
            events.append(_event_id("control", row["row_sha256"]))
        return tuple(events)
    except (OSError, RuntimeError, ValueError, TypeError, OverflowError, InvalidOperation):
        raise SourceError("control source unavailable") from None


def _unique_object(pairs: list) -> dict:
    result = dict(pairs)
    if len(result) != len(pairs):
        raise ValueError
    return result


def _scan_log(path: Path, source: str, identify: Callable[[dict], str | None]) -> tuple[str, ...]:
    """Validate and scan a bounded file prefix fixed at open. Writers' appends are picked up next time."""
    try:
        path = Path(path)
        if not path.is_absolute() or ".." in path.parts or path.name != "alerts.jsonl":
            raise ValueError
        for parent in path.parents:
            checked_target(parent, "alert directory")
        checked_target(path, "alert log")
        before = path.lstat()
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_size > MAX_LOG_BYTES:
            raise ValueError
        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
        with os.fdopen(os.open(path, flags), "rb") as stream:
            opened = os.fstat(stream.fileno())
            if not os.path.samestat(before, opened) or opened.st_nlink != 1 or opened.st_size > MAX_LOG_BYTES:
                raise ValueError
            remaining, rows = opened.st_size, 0
            events = []
            while remaining:
                line = stream.readline(min(remaining, MAX_LINE_BYTES + 1))
                remaining -= len(line)
                rows += 1
                if not line.endswith(b"\n") or len(line) > MAX_LINE_BYTES or rows > MAX_ROWS:
                    raise ValueError
                row = json.loads(line.decode("utf-8"), object_pairs_hook=_unique_object)
                if not isinstance(row, dict):
                    raise ValueError
                identity = identify(row)
                if identity is not None:
                    events.append(_event_id(source, identity))
        return tuple(events)
    except (OSError, RuntimeError, ValueError, TypeError, OverflowError):
        raise SourceError(f"{source} source unavailable") from None


def _compliance_identity(row: dict) -> str | None:
    summary = {key: value for key, value in row.items() if key not in ("utc", "channel", "result")}
    if (not alerts._valid_summary(summary) or not checks._is_stamp(row.get("utc"))
            or row.get("channel") not in ("toast", "push", "email") or row.get("result") not in ("ok", "fail")
            or (summary["code"] > 2 and summary["fingerprint"])):
        raise ValueError
    # A failed Windows toast still needs remote delivery. Skip push/email receipts from the separate daily task.
    return model.canonical_json(row) if row["channel"] == "toast" else None


def scan_compliance(path: Path) -> tuple[str, ...]:
    """Read the compliance check's alerts.jsonl. It records toast attempts when a check raises an alert."""
    return _scan_log(path, "compliance", _compliance_identity)


def _execution_identity(row: dict) -> str | None:
    if not checks.verify_row(row):
        raise ValueError
    if row["level"] not in ("red", "amber"):
        return None
    # E1 --mark-sent rewrites this bit for the original daily digest. Our per-channel receipts live separately.
    return model.canonical_json({key: value for key, value in row.items() if key != "sent"})


def scan_execution(path: Path) -> tuple[str, ...]:
    """Read verified red/amber events from the E1 account poller's execution/alerts.jsonl."""
    return _scan_log(path, "execution", _execution_identity)
