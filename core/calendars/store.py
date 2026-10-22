"""Owner-signed calendar data files, change control and the coverage horizon (R-20 rule 6; TASK-M1-05;
T-CAL-01, T-CAL-02).

Every file under `core/calendars/data/` is a YAML document with one envelope:

    file_id, version, covers: {from, to}, coverage_calendar, signed_off_by, signed_utc, md5, rows: [...]

and every row carries `effective_from`, `effective_to`, `source_url`, `retrieved_at_utc`, `signed_off_by`
(spec L2001). A file is REFUSED at load (`CalendarUnsigned`) when any of these holds: `signed_off_by` or
`signed_utc` is missing or empty at file level or on any row; `md5` differs from the md5 of the canonical
content; the file has no MANIFEST.yaml row; the manifest md5, signer or `test_ids` disagree. The shipped
drafts are unsigned on purpose and therefore refused: every KR and US acting input fails closed and every
book stays DISARMED until the owner signs (spec L2088, L2100). This module never writes a signature.

Coverage (spec L2077, L2090): `sessions_left(file, decision_date)` counts the sessions of the file's own
calendar after the decision date; <= 60 warns, <= 20 pages, a decision date outside `covers` raises
`CalendarCoverageError`, which the runtime maps to an OPS HALT with reason `calendar_coverage`.

All dates are quoted strings in the YAML (PyYAML 1.1 would otherwise read 15:30 as 930 and 2016-08-01 as
a date object); the loader refuses unquoted date/time scalars.
"""
from __future__ import annotations

import os
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Iterable, Optional

import yaml

from core.ficc.macro_schema import canonical_json, md5_hex

DATA_DIR = Path(__file__).resolve().parent / "data"
MANIFEST = "MANIFEST.yaml"
SIGNATURE_FIELDS = ("signed_off_by", "signed_utc", "md5")
ROW_FIELDS = ("effective_from", "effective_to", "source_url", "retrieved_at_utc", "signed_off_by")
ENVELOPE_FIELDS = ("file_id", "version", "covers", "coverage_calendar", "rows") + SIGNATURE_FIELDS
HOLIDAY_SETS = ("KRX", "NYSE", "FED", "SIFMA", "CBOE", "CME", "JPX", "SSE", "HKEX", "TWSE", "ECOS")
# Which signed files a market's decision clock reads (spec L2088: an unsigned file fails that market closed).
MARKET_FILES = {
    "KR": ("kr_sessions", "holidays_KRX"),
    "US": ("holidays_NYSE",),
    "JP": ("holidays_JPX",),
    "CN": ("holidays_SSE", "market_closes"),
    "HK": ("holidays_HKEX", "market_closes"),
    "TW": ("holidays_TWSE", "market_closes"),
}
# Every file whose coverage a market's decisions depend on (clock files + regime tags + publication files).
COVERAGE_FILES = {
    "KR": MARKET_FILES["KR"] + ("kr_regime_tags", "publication_schedules", "source_skipped"),
    "US": MARKET_FILES["US"] + ("holidays_FED", "holidays_SIFMA", "publication_schedules", "source_skipped"),
    "JP": MARKET_FILES["JP"], "CN": MARKET_FILES["CN"], "HK": MARKET_FILES["HK"], "TW": MARKET_FILES["TW"],
}
MARKET_HOLIDAY_SET = {"KR": "KRX", "US": "NYSE", "JP": "JPX", "CN": "SSE", "HK": "HKEX", "TW": "TWSE"}
MARKET_TZ = {"KR": "Asia/Seoul", "US": "America/New_York", "JP": "Asia/Tokyo",
             "CN": "Asia/Shanghai", "HK": "Asia/Hong_Kong", "TW": "Asia/Taipei"}
ALERT_CODE = "calendar_coverage"
COMPONENT = "core/calendars"


class NotASession(Exception):
    """`decision_time_utc` on a non-session; it never rolls to the next day (spec L2087)."""


class CalendarUnsigned(Exception):
    """A calendar, regime-tag, publication-schedule or source-exception file refused at load (T-CAL-01)."""


class CalendarCoverageError(Exception):
    """A decision date outside a file's coverage: OPS HALT `calendar_coverage`, never a silent NotASession."""


@dataclass(frozen=True)
class CalendarFile:
    file_id: str
    version: str
    md5: str
    covers_from: date
    covers_to: date
    coverage_calendar: str
    signed_off_by: str
    signed_utc: str
    rows: tuple[dict, ...]
    doc: dict
    path: Optional[Path] = None

    def covers(self, d: date) -> bool:
        return self.covers_from <= d <= self.covers_to


def _iso_date(text, where: str) -> date:
    if not isinstance(text, str):
        raise CalendarUnsigned(f"{where}: date must be a quoted ISO string, got {type(text).__name__}")
    try:
        return date.fromisoformat(text)
    except ValueError as exc:
        raise CalendarUnsigned(f"{where}: {exc}") from None


def _reject_native_dates(value, where: str) -> None:
    if isinstance(value, (date, datetime)):
        raise CalendarUnsigned(f"{where}: unquoted date/time scalar; quote every date and time string")
    if isinstance(value, dict):
        for k, v in value.items():
            _reject_native_dates(v, f"{where}.{k}")
    elif isinstance(value, list):
        for i, v in enumerate(value):
            _reject_native_dates(v, f"{where}[{i}]")


def content_md5(doc: dict) -> str:
    """md5 of the canonical JSON of the document without its three signature fields (what the owner signs)."""
    body = {k: v for k, v in doc.items() if k not in SIGNATURE_FIELDS}
    return md5_hex(canonical_json(body))


def read_yaml(path: Path) -> dict:
    doc = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(doc, dict):
        raise CalendarUnsigned(f"{path.name}: not a mapping")
    _reject_native_dates(doc, path.name)
    return doc


def _signed(value) -> bool:
    return isinstance(value, str) and bool(value.strip())


def parse_file(doc: dict, *, manifest_row: Optional[dict], path: Optional[Path] = None) -> CalendarFile:
    """Validate the envelope, every row's five fields, the signature and the manifest row; refuse otherwise."""
    name = (path.name if path else doc.get("file_id") or "<doc>")
    missing = [k for k in ENVELOPE_FIELDS if k not in doc]
    if missing:
        raise CalendarUnsigned(f"{name}: envelope lacks {missing}")
    if not _signed(doc.get("signed_off_by")):
        raise CalendarUnsigned(f"{name}: signed_off_by is empty; an unsigned calendar file is refused (T-CAL-01)")
    if not _signed(doc.get("signed_utc")):
        raise CalendarUnsigned(f"{name}: signed_utc is empty")
    digest = content_md5(doc)
    if doc.get("md5") != digest:
        raise CalendarUnsigned(f"{name}: md5 {doc.get('md5')!r} != content md5 {digest}; an edit under an old "
                               "signature is an unsigned change")
    if manifest_row is None:
        raise CalendarUnsigned(f"{name}: no {MANIFEST} row (change control: test_per_change required)")
    if manifest_row.get("md5") != digest or manifest_row.get("version") != doc["version"]:
        raise CalendarUnsigned(f"{name}: {MANIFEST} row (version {manifest_row.get('version')!r}, md5 "
                               f"{manifest_row.get('md5')!r}) does not match the file ({doc['version']!r}, {digest})")
    if not _signed(manifest_row.get("signed_off_by")) or manifest_row["signed_off_by"] != doc["signed_off_by"]:
        raise CalendarUnsigned(f"{name}: {MANIFEST} signer does not match the file signer")
    tests = manifest_row.get("test_ids")
    if not isinstance(tests, list) or not tests or not all(_signed(t) for t in tests):
        raise CalendarUnsigned(f"{name}: {MANIFEST} row names no test id (test_per_change: required)")
    rows = doc.get("rows")
    if not isinstance(rows, list):
        raise CalendarUnsigned(f"{name}: rows must be a list")
    for i, row in enumerate(rows):
        if not isinstance(row, dict):
            raise CalendarUnsigned(f"{name}: rows[{i}] is not a mapping")
        lacking = [k for k in ROW_FIELDS if k not in row]
        if lacking:
            raise CalendarUnsigned(f"{name}: rows[{i}] lacks {lacking}")
        if not _signed(row.get("signed_off_by")):
            raise CalendarUnsigned(f"{name}: rows[{i}] is unsigned")
        for k in ("effective_from", "effective_to"):
            if row[k] is not None:
                _iso_date(row[k], f"{name}: rows[{i}].{k}")
    covers = doc.get("covers")
    if not isinstance(covers, dict) or covers.get("from") is None or covers.get("to") is None:
        raise CalendarUnsigned(f"{name}: covers.from / covers.to required (coverage horizon, T-CAL-02)")
    c_from, c_to = _iso_date(covers["from"], f"{name}: covers.from"), _iso_date(covers["to"], f"{name}: covers.to")
    if c_to < c_from:
        raise CalendarUnsigned(f"{name}: covers.to precedes covers.from")
    if not isinstance(doc["coverage_calendar"], str) or not doc["coverage_calendar"]:
        raise CalendarUnsigned(f"{name}: coverage_calendar must name a holiday set or market")
    return CalendarFile(file_id=str(doc["file_id"]), version=str(doc["version"]), md5=digest,
                        covers_from=c_from, covers_to=c_to, coverage_calendar=doc["coverage_calendar"],
                        signed_off_by=doc["signed_off_by"], signed_utc=doc["signed_utc"],
                        rows=tuple(rows), doc=doc, path=path)


def effective_rows(rows: Iterable[dict], d: date) -> list[dict]:
    """Rows whose [effective_from, effective_to] (either side open when null) contains d."""
    out = []
    for row in rows:
        lo, hi = row.get("effective_from"), row.get("effective_to")
        if (lo is None or date.fromisoformat(lo) <= d) and (hi is None or d <= date.fromisoformat(hi)):
            out.append(row)
    return out


def effective_one(rows: Iterable[dict], d: date, what: str) -> dict:
    found = effective_rows(rows, d)
    if len(found) != 1:
        raise ValueError(f"{what}: {len(found)} rows effective on {d.isoformat()} (exactly one required)")
    return found[0]


def effective_config(entries, d: date, what: str) -> dict:
    """The rules-store list form `[{to: ..}, {from: ..}]`: exactly one entry whose from/to range holds d."""
    if isinstance(entries, dict):
        return entries
    found = []
    for e in entries:
        lo, hi = e.get("from"), e.get("to")
        if (lo is None or date.fromisoformat(lo) <= d) and (hi is None or d <= date.fromisoformat(hi)):
            found.append(e)
    if len(found) != 1:
        raise ValueError(f"{what}: {len(found)} config entries effective on {d.isoformat()}")
    return found[0]


class CalendarSet:
    """The signed data files of one directory plus the `calendars` block of the rules store.

    Files load lazily and independently: an unsigned JPX file leaves KR decisions intact, an unsigned KRX file
    fails every KR acting input closed. `config` is injected (tests pin it); the default is the shipped store.
    """

    def __init__(self, data_dir: Path | None = None, *, config: dict | None = None,
                 buffer_s: int | None = None) -> None:
        self.data_dir = Path(data_dir) if data_dir is not None else DATA_DIR
        self._config = config
        self._buffer_s = buffer_s
        self._files: dict[str, CalendarFile] = {}
        self._refused: dict[str, CalendarUnsigned] = {}
        self._manifest: Optional[dict] = None
        self._sets: dict[str, tuple[frozenset, dict, frozenset]] = {}

    # -- config ---------------------------------------------------------------
    @property
    def config(self) -> dict:
        if self._config is None:
            from core.rules.macro_rules import load_store      # the shipped store is read-only (T-HERM-02)
            self._config = load_store().get("calendars")
        return self._config

    @property
    def buffer_s(self) -> int:
        """`data_contracts.cross_market.buffer_s` (60 s; spec L1915), injectable for tests."""
        if self._buffer_s is None:
            from core.rules.macro_rules import load_store
            self._buffer_s = int(load_store().get("data_contracts.cross_market.buffer_s"))
        return self._buffer_s

    def market_config(self, market: str) -> dict:
        try:
            return self.config[market]
        except KeyError:
            raise KeyError(f"calendars.{market}: not an M1 market (KR, US, JP, CN, HK, TW)") from None

    # -- manifest and files -----------------------------------------------------
    @property
    def manifest(self) -> dict:
        if self._manifest is None:
            path = self.data_dir / MANIFEST
            if not path.is_file():
                self._manifest = {"rows": {}}
            else:
                doc = read_yaml(path)
                rows = doc.get("rows") or []
                self._manifest = {"version": doc.get("version"), "signed_off_by": doc.get("signed_off_by"),
                                  "rows": {r.get("file"): r for r in rows if isinstance(r, dict)}}
        return self._manifest

    @property
    def version(self) -> str:
        """The signed data version stamped as `event_calendar.calendar_version`; "unsigned" when none."""
        v = self.manifest.get("version")
        return str(v) if _signed(self.manifest.get("signed_off_by")) and v else "unsigned"

    def file_ids(self) -> tuple[str, ...]:
        return tuple(sorted(p.stem for p in self.data_dir.glob("*.yaml") if p.name != MANIFEST))

    def file(self, file_id: str) -> CalendarFile:
        if file_id in self._files:
            return self._files[file_id]
        if file_id in self._refused:
            raise self._refused[file_id]
        path = self.data_dir / f"{file_id}.yaml"
        try:
            if not path.is_file():
                raise CalendarUnsigned(f"{file_id}.yaml: missing from {self.data_dir}")
            parsed = parse_file(read_yaml(path), manifest_row=self.manifest["rows"].get(path.name), path=path)
            if parsed.file_id != file_id:
                raise CalendarUnsigned(f"{path.name}: file_id {parsed.file_id!r} != {file_id!r}")
        except CalendarUnsigned as exc:
            self._refused[file_id] = exc
            raise
        self._files[file_id] = parsed
        return parsed

    def refusal(self, file_id: str) -> Optional[str]:
        """The refusal reason, or None when the file loads (never raises)."""
        try:
            self.file(file_id)
            return None
        except CalendarUnsigned as exc:
            return str(exc)

    # -- holiday sets -------------------------------------------------------------
    def holiday_set(self, set_id: str) -> tuple[frozenset[date], dict[date, str], frozenset[date]]:
        """(closed dates, early-close date -> local close "HH:MM", weekend dates that are sessions)."""
        if set_id in self._sets:
            return self._sets[set_id]
        f = self.file(f"holidays_{set_id}")
        closed, early, extra = set(), {}, set()
        for row in f.rows:
            d = date.fromisoformat(row["date"])
            kind = row.get("kind")
            if kind == "closed":
                closed.add(d)
            elif kind == "early_close":
                early[d] = row["close_local"]
            elif kind == "open":
                extra.add(d)
            else:
                raise CalendarUnsigned(f"holidays_{set_id}: row {row['date']} has kind {kind!r}")
        self._sets[set_id] = (frozenset(closed), early, frozenset(extra))
        return self._sets[set_id]

    def require_covered(self, file_id: str, d: date) -> CalendarFile:
        f = self.file(file_id)
        if not f.covers(d):
            raise CalendarCoverageError(f"{file_id} v{f.version} covers {f.covers_from}..{f.covers_to}; "
                                        f"{d.isoformat()} is outside (OPS HALT {ALERT_CODE})")
        return f


_DEFAULT: Optional[CalendarSet] = None


def default() -> CalendarSet:
    """The production set: the shipped files and the shipped store. Application code passes no data_dir."""
    global _DEFAULT
    if _DEFAULT is None:
        _DEFAULT = CalendarSet()
    return _DEFAULT


def reload() -> None:
    """Drop the cached default set (after the owner signs a file); the next call re-reads every file."""
    global _DEFAULT
    _DEFAULT = None


# --------------------------------------------------------------------------- #
# Coverage horizon (T-CAL-02)
# --------------------------------------------------------------------------- #
def _calendar_sessions(cal: CalendarSet, calendar_id: str, lo: date, hi: date) -> int:
    """Sessions of a holiday set or market strictly after lo and up to hi (business days for FED, SIFMA, ECOS)."""
    from core.calendars import publication      # local: publication imports this module
    n, d = 0, lo + timedelta(days=1)
    while d <= hi:
        try:
            if publication.business_day(calendar_id, d, cal=cal):
                n += 1
        except CalendarCoverageError:            # the underlying calendar ran out: nothing beyond it is countable
            break
        d += timedelta(days=1)
    return n


def sessions_left(cal: CalendarSet, f: CalendarFile, decision_date: date) -> int:
    if decision_date >= f.covers_to:
        return 0
    return _calendar_sessions(cal, f.coverage_calendar, decision_date, f.covers_to)


def _alert(code: str, severity: str, now_utc: datetime, file_id: str, detail: str) -> dict:
    return {"alert_id": uuid.uuid5(uuid.NAMESPACE_URL, f"quantgen:{code}:{file_id}:{severity}").hex,
            "code": code, "severity": severity, "component": COMPONENT, "series_id": None, "books": [],
            "first_seen_utc": now_utc.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "count": 1,
            "escalated": severity == "page", "ack_utc": None, "detail": detail}


def status(market_or_set: str, decision_date: date, *, cal: CalendarSet | None = None,
           now_utc: datetime | None = None) -> dict:
    """{signed, version, covers_from, covers_to, sessions_left, alerts[], refused} for one market's files or one set."""
    cal = cal or default()
    file_ids = COVERAGE_FILES.get(market_or_set) or ((f"holidays_{market_or_set}",) if market_or_set in HOLIDAY_SETS
                                                      else (market_or_set,))
    out = {"id": market_or_set, "signed": True, "version": cal.version, "covers_from": None, "covers_to": None,
           "sessions_left": None, "alerts": [], "refused": {}}
    now_utc = now_utc or datetime(decision_date.year, decision_date.month, decision_date.day, tzinfo=timezone.utc)
    for fid in file_ids:
        reason = cal.refusal(fid)
        if reason is not None:
            out["signed"] = False
            out["refused"][fid] = reason
            continue
        f = cal.file(fid)
        out["covers_from"] = max(out["covers_from"] or f.covers_from, f.covers_from)
        out["covers_to"] = min(out["covers_to"] or f.covers_to, f.covers_to)
        try:
            out["alerts"] += check_coverage(decision_date, (fid,), cal=cal, now_utc=now_utc)
            left = sessions_left(cal, f, decision_date)
            out["sessions_left"] = left if out["sessions_left"] is None else min(out["sessions_left"], left)
        except CalendarCoverageError as exc:
            out["sessions_left"] = 0
            out["alerts"].append(_alert(ALERT_CODE, "page", now_utc, fid, str(exc)))
        except CalendarUnsigned as exc:          # a sibling file this one's session count depends on is refused
            out["signed"] = False
            out["refused"].setdefault(fid, str(exc))
    return out


def check_coverage(decision_date: date, file_ids: Iterable[str], *, cal: CalendarSet | None = None,
                   now_utc: datetime, book_ids: Iterable[str] = (),
                   halt: Callable[[str, str, str], None] | None = None) -> list[dict]:
    """Alerts (`warn` at <= 60 sessions left, `page` at <= 20) for every file; raises `CalendarCoverageError`
    when the decision date lies outside a file's coverage, after calling `halt(book_id, "OPS", "calendar_coverage")`
    for every book given (the runtime hook; `halt` is `core.engine.books.runtime_halt` bound to its registry).
    """
    cal = cal or default()
    cov = cal.config.get("coverage") or {}
    warn_at, page_at = int(cov.get("warn_at_sessions_left", 60)), int(cov.get("page_at_sessions_left", 20))
    alerts = []
    for fid in file_ids:
        f = cal.file(fid)
        if not f.covers(decision_date):
            reason = (f"{fid} v{f.version} covers {f.covers_from}..{f.covers_to}; decision date "
                      f"{decision_date.isoformat()} is outside")
            for book_id in book_ids:
                if halt is not None:
                    halt(book_id, "OPS", ALERT_CODE)
                # `halt` = core.engine.books.coverage_halt(registry, decision_utc): every book that reads this
                # calendar HALTs (OPS, calendar_coverage); the OPS re-arm is automatic at the first decision
                # inside coverage (spec L1179).
            raise CalendarCoverageError(reason)
        left = sessions_left(cal, f, decision_date)
        if left <= page_at:
            alerts.append(_alert(ALERT_CODE, "page", now_utc, fid, f"{fid}: {left} sessions left (page at {page_at})"))
        elif left <= warn_at:
            alerts.append(_alert(ALERT_CODE, "warn", now_utc, fid, f"{fid}: {left} sessions left (warn at {warn_at})"))
    return alerts


def arm_precondition(decision_date: date, market: str, *, cal: CalendarSet | None = None) -> bool:
    """DISARMED -> ARMED needs every file of the market signed and >= min_sessions_ahead sessions covered (L1180)."""
    cal = cal or default()
    need = int((cal.config.get("coverage") or {}).get("min_sessions_ahead", 60))
    try:
        return all(sessions_left(cal, cal.file(fid), decision_date) >= need for fid in MARKET_FILES[market])
    except (CalendarUnsigned, KeyError):
        return False


# --------------------------------------------------------------------------- #
# Governance: one `calendar_change` event per loaded version (spec L4096, L4104)
# --------------------------------------------------------------------------- #
def record_calendar_changes(log_path: Path, file_ids: Iterable[str], clock: Callable[[], datetime], *,
                            cal: CalendarSet | None = None, actor: str = "owner") -> list[str]:
    """Append one `calendar_change` event for every signed file whose (version, md5) differs from the last one
    logged; returns the row md5s written. Unsigned files are skipped (they never become a version)."""
    from core.rules.governance import append_event, read_events
    cal = cal or default()
    log_path = Path(log_path)
    last: dict[str, dict] = {}
    for ev in (read_events(log_path) if log_path.exists() else []):
        if ev.get("kind") == "calendar_change" and ev.get("key"):
            last[ev["key"]] = ev.get("new") or {}
    written = []
    for fid in file_ids:
        try:
            f = cal.file(fid)
        except CalendarUnsigned:
            continue
        new = {"version": f.version, "md5": f.md5, "signed_off_by": f.signed_off_by, "signed_utc": f.signed_utc}
        prev = last.get(fid)
        if prev and prev.get("version") == new["version"] and prev.get("md5") == new["md5"]:
            continue
        event = {"kind": "calendar_change", "book_id": None, "rule_id": "R-20", "key": fid,
                 "old": {k: prev.get(k) for k in ("version", "md5")} if prev else None, "new": new,
                 "actor": actor, "reason": f"{fid} loaded at version {f.version} signed by {f.signed_off_by}",
                 "refs": ["R-20 rule 6", "T-CAL-01"]}
        written.append(append_event(log_path, event, clock))
    return written


def describe(cal: CalendarSet | None = None) -> list[dict]:
    """One row per data file: loads or the refusal reason (read-only; the Macro page's 'Open owner actions')."""
    cal = cal or default()
    out = []
    for fid in cal.file_ids():
        reason = cal.refusal(fid)
        row = {"file": f"{fid}.yaml", "status": "signed" if reason is None else "REFUSED", "reason": reason}
        try:
            doc = read_yaml(cal.data_dir / f"{fid}.yaml")
            row.update(version=doc.get("version"), covers=doc.get("covers"), content_md5=content_md5(doc),
                       unverified=doc.get("unverified"), owner_must_sign=doc.get("owner_must_sign"))
        except Exception as exc:          # a malformed draft is still listed, with its error
            row["reason"] = row["reason"] or str(exc)
        out.append(row)
    return out


if __name__ == "__main__":
    # Read-only report of the shipped drafts: what is refused and why, and the content md5 the owner would sign.
    for row in describe():
        print(f"{row['status']:8} {row['file']:32} v{row.get('version')} md5={row.get('content_md5')}")
        if row.get("reason"):
            print(f"         {row['reason']}")
        for item in (row.get("owner_must_sign") or []):
            print(f"         owner: {item}")
    print("data_dir:", DATA_DIR, "| pid", os.getpid())
