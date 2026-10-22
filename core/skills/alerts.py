"""Persisted alert store and sinks (section 3.9 alert sinks L1248-1250; R-35; TASK-M8-06; T-OBS-03; rulings 3.12).

One append-only `alerts.jsonl` under the macro dir: every raise and every acknowledgement is a line, the latest
line per `alert_id` is the alert's state (so the store survives a restart, T-OBS-03). The id is the md5 of
`(code, component, series_id, books)`: a re-raise of an open alert increments `count` and keeps `first_seen_utc`;
a raise after an acknowledgement opens a new episode. Instants are the caller's decision instant, never a wall
clock, so the embedded `macro_state.alerts[]` records stay deterministic (T-REPLAY-01).

Sinks: the Macro-page banner reads `open()`; the OS notification and the e-mail skill are recorded as
`unavailable` (no dependency may be added, rulings 3.2 / 3.12). Binary append, LF, fsync; a failed write raises.
"""
from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

from core.ficc.macro_schema import canonical_json, md5_hex
from core.ficc.pit import iso_utc

SEVERITIES = ("info", "warn", "page")
PAGE_CODES = ("RUN_ERROR", "MISSED_DECISION", "VERDICT_INTEGRITY", "GOVERNANCE_LOG_BROKEN")
SINKS = {"banner": "persisted_store", "os_notification": "unavailable", "email": "unavailable"}
FILE = "alerts.jsonl"
ARTIFACT_KEYS = ("alert_id", "code", "severity", "component", "series_id", "books", "first_seen_utc", "count",
                 "escalated", "ack_utc")


def alert_id(code: str, component: str, series_id: str | None = None, books=()) -> str:
    return md5_hex(f"{code}|{component}|{series_id or ''}|{','.join(sorted(books))}")[:16]


def as_artifact(record: dict) -> dict:
    """The `macro_state.alerts[]` shape (section 6.1 L3625-3629) of a stored record."""
    return {k: record.get(k) for k in ARTIFACT_KEYS}


class AlertStore:
    def __init__(self, path) -> None:
        p = Path(path)
        self.path = p / FILE if p.is_dir() or p.suffix != ".jsonl" else p

    def _rows(self) -> list[dict]:
        if not self.path.is_file():
            return []
        return [json.loads(line) for line in self.path.read_bytes().decode("utf-8").split("\n") if line.strip()]

    def _append(self, row: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "ab") as fh:                     # append-only; raises, never swallows
            fh.write(canonical_json(row).encode("utf-8") + b"\n")
            fh.flush()
            os.fsync(fh.fileno())

    def all(self) -> dict[str, dict]:
        """Latest state per alert id, in first-raise order."""
        out: dict[str, dict] = {}
        for row in self._rows():
            out[row["alert_id"]] = row
        return out

    def open(self, severity: str | None = None) -> list[dict]:
        return [a for a in self.all().values() if a.get("ack_utc") is None and (severity is None or a["severity"] == severity)]

    def raise_alert(self, code: str, severity: str, component: str, *, when: datetime, series_id: str | None = None,
                    books=(), detail: str = "", escalated: bool = False) -> dict:
        if severity not in SEVERITIES:
            raise ValueError(f"alert severity {severity!r} not in {SEVERITIES}")
        if code in PAGE_CODES and severity != "page":
            raise ValueError(f"{code} is a page-severity code (section 3.9)")
        books = sorted(books)
        aid = alert_id(code, component, series_id, books)
        prev = self.all().get(aid)
        stamp = iso_utc(when)
        if prev is not None and prev.get("ack_utc") is None:
            first, count = prev["first_seen_utc"], int(prev["count"]) + 1
        else:
            first, count = stamp, 1
        row = {"alert_id": aid, "code": code, "severity": severity, "component": component, "series_id": series_id,
               "books": books, "first_seen_utc": first, "last_seen_utc": stamp, "count": count,
               "escalated": bool(escalated), "ack_utc": None, "ack_by": None, "detail": detail, "sinks": dict(SINKS)}
        self._append(row)
        return row

    def record_from(self, alert: dict, when: datetime, **kw) -> dict:
        """Persist a producer's alert dict (`risk_layer.alert` shape: code, severity, component, series_id, books)."""
        return self.raise_alert(alert["code"], alert.get("severity", "warn"), alert["component"], when=when,
                                series_id=alert.get("series_id"), books=alert.get("books") or (),
                                escalated=bool(alert.get("escalated", False)), **kw)

    def acknowledge(self, alert_id: str, by: str, when: datetime) -> dict:
        """Operator acknowledgement: the only path that sets `ack_utc` (page alerts persist until then)."""
        if not by:
            raise ValueError("an acknowledgement names the operator")
        prev = self.all().get(alert_id)
        if prev is None:
            raise KeyError(f"alert {alert_id!r} is not in the store")
        if prev.get("ack_utc") is not None:
            return prev
        row = dict(prev, ack_utc=iso_utc(when), ack_by=by)
        self._append(row)
        return row


__all__ = ["AlertStore", "SEVERITIES", "PAGE_CODES", "SINKS", "FILE", "alert_id", "as_artifact"]
