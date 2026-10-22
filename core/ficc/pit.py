"""Point-in-time store and as-of reads (M1; R-01 rules (1)-(5); P5, P18; section 3.5, 4.1).

Implements: `PITValue`, `MissingInput`, `RunContext`, `PITStore` (append-only JSONL per series, dedupe by content
hash, first-seen `retrieved_at_utc`, `fetch_log.jsonl`), `pit_value` (visibility, ranking, close-type guard, consumer
bindings), `pit_last`, `pit_window`, `data_snapshot_id`, close/bar/release stamping with the close + 10 min
quarantine, reconciliation (never auto-correct), derived records with lineage, calendar-offset monthly arithmetic,
`ingest` and `check_fixture`.

Tests: T-PROV-01, T-FIX-01, T-BAR-01/02, T-CLOSE-01 (data clauses), T-PRINT-01 (logic), T-SYN-01, T-MISS-01,
T-SER-01, T-H10-01/02, T-H15-01, T-VIX-01.

Every function takes `decision_utc` / `knowledge_utc` explicitly; nothing here reads a wall clock. Calendar
functions come from a `clocks` object (close_print_bound_utc, publication_instant, next_expected_obs,
add_publication_bdays, is_session): `core.calendars.adapter.CalendarClocks` in production, `StubClocks` in tests.
"""
from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass, fields, replace
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from core.ficc.macro_schema import canonical_json, md5_hex

VALUE_STATUS_RANK = ("official_close", "revised", "first_release", "vendor_close", "vendor_derived",
                     "vendor_derived_across_gap", "live_snapshot", "provisional_intraday")
OBS_KINDS = ("close", "quote_snapshot", "release", "bar", "derived")
AVAILABLE_AT_SOURCES = ("published", "calendar_bound", "inferred_from_retrieval")
ROLES = ("acting_exposure", "forward_sim", "risk_model", "context", "history")
REASONS = ("missing", "stale", "provisional_intraday", "session_mismatch", "synthetic_rejected")
RUN_MODES = ("live", "backtest", "replay")
DEDUPE_KEY = ("series_id", "obs_date", "vintage", "source", "value", "value_status")
QUARANTINE_MINUTES = 10          # data.reject_rows_retrieved_before_close_plus_minutes (L4206)
CLOSE_STATUSES = ("official_close", "vendor_close")
_UNNAMED = ("brent", "oil", "crude", "wti", "gold", "dollar", "usd", "vix", "rates", "yield")


class PITError(ValueError):
    """A store or read rule was violated (the message names the rule)."""


class UnnamedSeries(PITError):
    """A read by a nickname instead of a registered series id (data.named_series_required; T-SER-01)."""


class UnboundConsumer(PITError):
    """A non-context consumer read a series it has no binding for (R-19 rule 5; T-SER-02)."""


class FixtureRefused(PITError):
    """A fixture holds a row retrieved before its session's close + 10 min or before its publication instant."""


@dataclass(frozen=True)
class PITValue:
    series_id: str
    value: float
    obs_date: date
    session_date: date | None
    obs_utc: datetime
    obs_kind: str
    value_status: str
    dispute: bool
    available_at_utc: datetime
    available_at_source: str
    retrieved_at_utc: datetime
    vintage: date | None
    source: str
    channel: str | None
    provider_mode: str
    synthetic: bool
    content_hash: str
    role: str
    books: tuple[str, ...]

    @property
    def status(self) -> str:
        return "disputed" if self.dispute else "ok"


@dataclass(frozen=True)
class MissingInput:
    series_id: str
    reason: str
    role: str
    books: tuple[str, ...]
    detail: str = ""            # what failed (a refused calendar, a contract violation); the alert text

    def __post_init__(self) -> None:
        if self.reason not in REASONS:
            raise PITError(f"MissingInput.reason {self.reason!r} not in {REASONS}")


@dataclass(frozen=True)
class RunContext:
    decision_utc: datetime
    knowledge_utc: datetime
    run_mode: str = "live"

    def __post_init__(self) -> None:
        if self.run_mode not in RUN_MODES:
            raise PITError(f"run_mode {self.run_mode!r} not in {RUN_MODES}")
        for name in ("decision_utc", "knowledge_utc"):
            if getattr(self, name).tzinfo is None:
                raise PITError(f"{name} must be tz-aware UTC")


@dataclass(frozen=True)
class Flag:
    """A row that was not stored, with the rule that refused it (stale carry, print after bound, bar as close)."""
    series_id: str
    obs_date: date
    code: str
    detail: str = ""


@dataclass(frozen=True)
class IngestReport:
    appended: int
    logged: int
    flags: tuple[Flag, ...] = ()


# --------------------------------------------------------------------------- #
# Row encoding
# --------------------------------------------------------------------------- #
_ROW_FIELDS = tuple(f.name for f in fields(PITValue) if f.name not in ("role", "books", "dispute"))
_DT = ("obs_utc", "available_at_utc", "retrieved_at_utc")
_D = ("obs_date", "session_date", "vintage")


def iso_utc(dt: datetime) -> str:
    if dt.tzinfo is None:
        raise PITError("naive datetime; every instant is tz-aware UTC")
    dt = dt.astimezone(timezone.utc).replace(microsecond=0)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_utc(text: str) -> datetime:
    return datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def content_hash(row: dict) -> str:
    """md5 of the canonical JSON of the dedupe-key fields (F-6); a derived row also covers its inputs' hashes."""
    key = {k: _encode(k, row.get(k)) for k in DEDUPE_KEY}
    if row.get("inputs"):
        key["inputs"] = sorted(row["inputs"])
    return md5_hex(canonical_json(key))


def _encode(name: str, value):
    if value is None:
        return None
    if name in _DT:
        return iso_utc(value) if isinstance(value, datetime) else str(value)
    if name in _D:
        return value.isoformat() if isinstance(value, date) else str(value)
    if name == "value":
        return float(value)
    return value


def _decode(row: dict) -> dict:
    out = dict(row)
    for k in _DT:
        if isinstance(out.get(k), str):
            out[k] = parse_utc(out[k])
    for k in _D:
        if isinstance(out.get(k), str):
            out[k] = date.fromisoformat(out[k])
    return out


def make_row(**kw) -> dict:
    """A stored row: every PITValue field except role, books, dispute; content_hash filled; enums checked."""
    row = {k: kw.get(k) for k in _ROW_FIELDS}
    row.setdefault("channel", None)
    row["provider_mode"] = kw.get("provider_mode", "explicit")
    row["synthetic"] = bool(kw.get("synthetic", False))
    if kw.get("inputs"):
        row["inputs"] = list(kw["inputs"])
    if row["obs_kind"] not in OBS_KINDS:
        raise PITError(f"obs_kind {row['obs_kind']!r} not in {OBS_KINDS}")
    if row["value_status"] not in VALUE_STATUS_RANK:
        raise PITError(f"value_status {row['value_status']!r} not in {VALUE_STATUS_RANK}")
    if row["available_at_source"] not in AVAILABLE_AT_SOURCES:
        raise PITError(f"available_at_source {row['available_at_source']!r} not in {AVAILABLE_AT_SOURCES}")
    if row["provider_mode"] not in ("explicit", "auto"):
        raise PITError("provider_mode must be explicit or auto")
    if row["obs_kind"] == "close" and row["session_date"] is None:
        raise PITError("a close-type row needs session_date (L1276)")
    if row["obs_kind"] not in ("close", "derived") and row["value_status"] in CLOSE_STATUSES:
        raise PITError(f"value_status {row['value_status']} on a {row['obs_kind']} row: only a close is a close")
    for k in _DT:
        if not isinstance(row[k], datetime) or row[k].tzinfo is None:
            raise PITError(f"{k} must be a tz-aware datetime")
    row["content_hash"] = content_hash(row)
    return row


def _dump(row: dict) -> str:
    out = {k: _encode(k, v) for k, v in row.items() if k != "inputs"}
    if row.get("inputs"):
        out["inputs"] = list(row["inputs"])
    return canonical_json(out)


def to_value(row: dict, *, role: str, books: tuple[str, ...], dispute: bool = False) -> PITValue:
    return PITValue(**{k: row.get(k) for k in _ROW_FIELDS}, role=role, books=tuple(books), dispute=dispute)


# --------------------------------------------------------------------------- #
# Store
# --------------------------------------------------------------------------- #
class PITStore:
    """Append-only bitemporal store: one JSONL file per series under `path`, plus `fetch_log.jsonl`.

    Rows are never mutated (`rows_mutated: never`); a correction is a new row. A row is appended only when its
    content hash is new for the series (`dedupe_key`); an unchanged-content fetch is written to the fetch log only,
    so the stored `retrieved_at_utc` is first-seen. Appends are binary, flushed, fsynced, and raise on failure.
    """

    def __init__(self, path, *, registry=None, clocks=None) -> None:
        self.path = Path(path)
        self.registry = registry
        self.clocks = clocks                     # core.calendars.adapter.CalendarClocks (or a test stub)
        self._rows: dict[str, list[dict]] = {}
        self._hashes: dict[str, set[str]] = {}

    def _file(self, series_id: str) -> Path:
        safe = "".join(c if c.isalnum() or c in "_.-" else "_" for c in series_id)
        return self.path / f"{safe}.jsonl"

    def series_ids(self) -> list[str]:
        if not self.path.is_dir():
            return []
        ids = set(self._rows)
        for p in self.path.glob("*.jsonl"):
            if p.name in ("fetch_log.jsonl", "disputes.jsonl"):
                continue
            try:
                with p.open("rb") as fh:
                    first = fh.readline()
                if first:
                    ids.add(json.loads(first)["series_id"])
            except Exception as exc:
                raise PITError(f"{p}: unreadable store file ({exc})") from exc
        return sorted(ids)

    def rows(self, series_id: str) -> list[dict]:
        if series_id not in self._rows:
            out = []
            p = self._file(series_id)
            if p.is_file():
                with p.open("rb") as fh:
                    for n, line in enumerate(fh, 1):
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            out.append(_decode(json.loads(line)))
                        except Exception as exc:
                            raise PITError(f"{p}:{n}: corrupt store line ({exc})") from exc
            self._rows[series_id] = out
            self._hashes[series_id] = {r["content_hash"] for r in out}
        return self._rows[series_id]

    def _append_line(self, path: Path, text: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(str(path), os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
        try:
            os.write(fd, (text + "\n").encode("utf-8"))
            os.fsync(fd)
        finally:
            os.close(fd)

    def log_fetch(self, series_id: str, fetch_utc: datetime, provider: str, status: str, digest: str) -> None:
        self._append_line(self.path / "fetch_log.jsonl", canonical_json({
            "series_id": series_id, "fetch_utc": iso_utc(fetch_utc), "provider": provider,
            "status": status, "content_hash": digest}))

    def append(self, rows, *, fetch_utc: datetime | None = None, provider: str | None = None) -> int:
        """Append the rows whose content is new; log the others. Returns the number appended."""
        n = 0
        for row in rows:
            if row.get("content_hash") != content_hash(row):
                raise PITError(f"{row.get('series_id')}: content_hash does not match the row (use make_row)")
            sid = row["series_id"]
            known = self.rows(sid)
            if row["content_hash"] in self._hashes[sid]:
                self.log_fetch(sid, fetch_utc or row["retrieved_at_utc"], provider or row["source"],
                               "unchanged", row["content_hash"])
                continue
            self._append_line(self._file(sid), _dump(row))
            known.append(dict(row))
            self._hashes[sid].add(row["content_hash"])
            n += 1
            if fetch_utc is not None:
                self.log_fetch(sid, fetch_utc, provider or row["source"], "appended", row["content_hash"])
        return n

    def log_dispute(self, record: dict) -> None:
        self._append_line(self.path / "disputes.jsonl", canonical_json(record))

    def ingest_rows(self, provider: str, series_id: str, rows, retrieved_at_utc: datetime) -> int:
        """Ingest hook for core.ficc.data._provider_rows: `rows` = [(iso_date, value), ...]. Needs registry + clocks;
        an unregistered id is not stored (context loaders keep their own cache)."""
        if self.registry is None or self.clocks is None or not self.registry.is_series(series_id):
            return 0
        source = {"FRED": "FRED", "YFINANCE": "Yahoo", "KIS": "KIS", "KRX": "KRX", "FMP": "FMP"}.get(provider, provider)
        report = ingest(self, series_id, [(date.fromisoformat(d), v) for d, v in rows], source=source,
                        retrieved_at_utc=retrieved_at_utc, registry=self.registry, clocks=self.clocks)
        return report.appended


# --------------------------------------------------------------------------- #
# Reads
# --------------------------------------------------------------------------- #
def _visible(rows, decision_utc: datetime, knowledge_utc: datetime):
    return [r for r in rows if r["available_at_utc"] <= decision_utc and r["retrieved_at_utc"] <= knowledge_utc]


def _rank(row: dict, precedence) -> tuple:
    src = precedence.index(row["source"]) if row["source"] in precedence else len(precedence)
    return (VALUE_STATUS_RANK.index(row["value_status"]), src, -row["available_at_utc"].timestamp(),
            -row["retrieved_at_utc"].timestamp())


def _best_per_obs(rows, precedence) -> dict[date, dict]:
    best: dict[date, dict] = {}
    for r in rows:
        cur = best.get(r["obs_date"])
        if cur is None or _rank(r, precedence) < _rank(cur, precedence):
            best[r["obs_date"]] = r
    return best


def _precedence(registry, series_id) -> tuple[str, ...]:
    if registry is None:
        return ()
    return tuple(registry.series[series_id].get("sources") or ())


def named_series(series_id: str) -> str:
    """Refuses a nickname ("Brent"): every read names a registered series id (data.named_series_required)."""
    if not isinstance(series_id, str) or not series_id.strip():
        raise UnnamedSeries("blank series id")
    if series_id.strip().lower() in _UNNAMED or " " in series_id.strip():
        raise UnnamedSeries(f"{series_id!r} is not a series id: name the series (DCOILBRENTEU or BZ=F, never 'Brent')")
    return series_id.strip()


def _registry(registry):
    if registry is not None:
        return registry
    from core.ficc import contracts                      # lazy: contracts imports this module
    return contracts.default_registry()


def _dispute(rows_same_obs, chosen: dict, registry, series_id: str) -> bool:
    """Two close sources of one obs_date disagree beyond tolerance (index 1 bp; stock exact): the official value is
    used, dispute = True (never a failure, never auto-corrected)."""
    if chosen["value_status"] != "official_close":
        return False
    tol = (registry.series[series_id].get("tolerance") or {}) if registry is not None else {}
    others = [r for r in rows_same_obs if r["value_status"] == "vendor_close"]
    for r in others:
        if "index_bp" in tol:
            if abs(r["value"] / chosen["value"] - 1.0) > float(tol["index_bp"]) * 1e-4:
                return True
        elif r["value"] != chosen["value"]:
            return True
    return False


def pit_value(store: PITStore, series_id: str, decision_utc: datetime, knowledge_utc: datetime, consumer: str,
              require_session: date | None = None, *, run_mode: str = "live", vendor: str | None = None,
              registry=None) -> PITValue | MissingInput:
    """As-of read (L998-1013). Visible rows: available_at_utc <= decision_utc and retrieved_at_utc <= knowledge_utc.
    Close-type acting reads need `require_session` (else raise), select among rows with obs_date == require_session
    (none -> missing, even when the previous close is visible), and return provisional_intraday for any status
    other than official_close (backtest: vendor_close when `vendor` is the row's source) or session_mismatch for a
    mis-dated row. A synthetic or auto-degraded value for a non-context consumer is synthetic_rejected."""
    series_id = named_series(series_id)
    registry = _registry(registry)
    if run_mode not in RUN_MODES:
        raise PITError(f"run_mode {run_mode!r} not in {RUN_MODES}")
    binding = registry.resolve_binding(series_id, consumer)
    role, books = binding.role, tuple(binding.books)
    kind = registry.consumers.get(consumer)
    if run_mode == "live" and series_id == "DEXKOUS" and kind in ("acting_exposure", "risk_model"):
        raise PITError("DEXKOUS is a labelled proxy: production never reads it for an acting or risk-model "
                       "input (data.usdkrw.production_reads_dexkous: false; T-H10-01)")
    close_type = registry.obs_kind(series_id) == "close"
    acting = role == "acting_exposure"
    if close_type and acting and require_session is None:
        raise PITError(f"{series_id}: require_session is mandatory for a close-type acting read (L1012)")
    visible = _visible(store.rows(series_id), decision_utc, knowledge_utc)
    if close_type and acting:
        visible = [r for r in visible if r["obs_date"] == require_session]
    if not visible:
        return MissingInput(series_id, "missing", role, books)
    precedence = _precedence(registry, series_id)
    best = _best_per_obs(visible, precedence)
    chosen = best[max(best)]
    if role != "context" and (chosen["synthetic"] or chosen["provider_mode"] == "auto"):
        return MissingInput(series_id, "synthetic_rejected", role, books)
    if (close_type or chosen["obs_kind"] == "close") and acting:
        ok = chosen["value_status"] == "official_close" or (
            run_mode == "backtest" and vendor and chosen["value_status"] == "vendor_close" and chosen["source"] == vendor)
        if not ok:
            return MissingInput(series_id, "provisional_intraday", role, books)
        if chosen["session_date"] != require_session:
            return MissingInput(series_id, "session_mismatch", role, books)
    if chosen["obs_kind"] == "derived" and acting and chosen.get("close_inputs_official") is False:
        return MissingInput(series_id, "provisional_intraday", role, books)
    same = [r for r in visible if r["obs_date"] == chosen["obs_date"]]
    return to_value(chosen, role=role, books=books, dispute=_dispute(same, chosen, registry, series_id))


def pit_last(store: PITStore, series_id: str, decision_utc: datetime, knowledge_utc: datetime, *,
             registry=None) -> PITValue | None:
    """Latest visible record (any status), or None. Role/books are not a binding here: labelled `history`."""
    series_id = named_series(series_id)
    visible = _visible(store.rows(series_id), decision_utc, knowledge_utc)
    if not visible:
        return None
    best = _best_per_obs(visible, _precedence(registry, series_id))
    return to_value(best[max(best)], role="history", books=())


def pit_window(store: PITStore, series_id: str, decision_utc: datetime, knowledge_utc: datetime, *,
               n: int | None = None, start: date | None = None, registry=None,
               statuses: tuple[str, ...] | None = None) -> list[PITValue]:
    """Best visible row per obs_date, ascending; the batched read for vol windows. Roll days (registry) are excluded."""
    series_id = named_series(series_id)
    registry = _registry(registry)
    rolls = set(roll_days(registry, series_id))
    visible = _visible(store.rows(series_id), decision_utc, knowledge_utc)
    if statuses:
        visible = [r for r in visible if r["value_status"] in statuses]
    best = _best_per_obs(visible, _precedence(registry, series_id))
    out = [to_value(best[d], role="history", books=()) for d in sorted(best)
           if (start is None or d >= start) and d not in rolls]
    return out[-n:] if n else out


def roll_days(registry, series_id: str) -> tuple[date, ...]:
    raw = registry.series[series_id].get("roll_days") or ()
    return tuple(d if isinstance(d, date) else date.fromisoformat(str(d)) for d in raw)


def returns_excluding_rolls(values: list[PITValue], rolls) -> list[tuple[date, float]]:
    """Simple returns between consecutive observations; a return into or out of a roll day is excluded (L1377)."""
    rolls = set(rolls)
    out = []
    for a, b in zip(values, values[1:]):
        if a.obs_date in rolls or b.obs_date in rolls:
            continue
        out.append((b.obs_date, b.value / a.value - 1.0))
    return out


def data_snapshot_id(store: PITStore, knowledge_utc: datetime) -> str:
    """md5 of the sorted content hashes of every row with retrieved_at_utc <= knowledge_utc (order-invariant;
    unchanged by a later correction)."""
    hashes = [r["content_hash"] for sid in store.series_ids() for r in store.rows(sid)
              if r["retrieved_at_utc"] <= knowledge_utc]
    return md5_hex("\n".join(sorted(hashes)))


# --------------------------------------------------------------------------- #
# Stamping (section 4.1 "Value status"; L1311-1312, L1319-1325)
# --------------------------------------------------------------------------- #
def stamp_close(series_id: str, obs_date: date, value: float, *, retrieved_at_utc: datetime, source: str, registry,
                clocks, print_time_utc: datetime | None = None, ohlcv: dict | None = None, channel: str | None = None,
                provider_mode: str = "explicit", synthetic: bool = False, obs_kind: str = "close") -> dict | Flag:
    """Stamp one fetched close. official_close only for a verified primary source retrieved >= bound + 10 min;
    a vendor row retrieved after that is vendor_close; anything retrieved earlier is provisional_intraday on a
    quote_snapshot row (never a close). A bar is never a close; a flat-OHLC zero-volume row is a stale carry;
    a print later than its bound fails closed (calendar-review alert) and is never re-stamped."""
    if obs_kind == "bar":
        raise PITError(f"{series_id}: a daily close is never derived from bars (data.daily_close_from_bars: forbidden)")
    market = registry.market(series_id)
    bound = clocks.close_print_bound_utc(market, obs_date)
    if ohlcv and all(ohlcv.get(k) is not None for k in ("open", "high", "low", "close")):
        flat = ohlcv["open"] == ohlcv["high"] == ohlcv["low"] == ohlcv["close"]
        if flat and float(ohlcv.get("volume") or 0.0) == 0.0 and clocks.is_session(market, obs_date):
            return Flag(series_id, obs_date, "stale_carry", "flat OHLC, zero volume on a session day (L1324)")
    if print_time_utc is not None and print_time_utc > bound:
        return Flag(series_id, obs_date, "print_after_bound",
                    f"print {iso_utc(print_time_utc)} > bound {iso_utc(bound)}: calendar review (L1311)")
    quarantine_end = bound + timedelta(minutes=QUARANTINE_MINUTES)
    if retrieved_at_utc < quarantine_end:
        return make_row(series_id=series_id, value=float(value), obs_date=obs_date, session_date=obs_date,
                        obs_utc=retrieved_at_utc, obs_kind="quote_snapshot", value_status="provisional_intraday",
                        available_at_utc=retrieved_at_utc, available_at_source="inferred_from_retrieval",
                        retrieved_at_utc=retrieved_at_utc, vintage=None, source=source, channel=channel,
                        provider_mode=provider_mode, synthetic=synthetic)
    verified = (registry.primary_sources.get(source) == "verified")
    status = "official_close" if verified else "vendor_close"
    if synthetic or provider_mode == "auto":
        status = "vendor_close"
    if print_time_utc is not None:
        available, src = print_time_utc, "published"
    else:
        available, src = bound, "calendar_bound"
    return make_row(series_id=series_id, value=float(value), obs_date=obs_date, session_date=obs_date, obs_utc=bound,
                    obs_kind="close", value_status=status, available_at_utc=available, available_at_source=src,
                    retrieved_at_utc=retrieved_at_utc, vintage=None, source=source, channel=channel,
                    provider_mode=provider_mode, synthetic=synthetic)


def stamp_bar(series_id: str, bar_end_utc: datetime, value: float, *, retrieved_at_utc: datetime, source: str,
              latency_s: float = 0.0, session_date: date | None = None, channel: str | None = None) -> dict:
    """A bar row: stamped bar_end, available_at = bar_end + latency; status provisional_intraday, never a close."""
    available = bar_end_utc + timedelta(seconds=float(latency_s))
    return make_row(series_id=series_id, value=float(value), obs_date=session_date or bar_end_utc.date(),
                    session_date=session_date, obs_utc=bar_end_utc, obs_kind="bar",
                    value_status="provisional_intraday", available_at_utc=available, available_at_source="calendar_bound",
                    retrieved_at_utc=retrieved_at_utc, vintage=None, source=source, channel=channel)


def stamp_release(series_id: str, obs_date: date, value: float, *, retrieved_at_utc: datetime, source: str, registry,
                  clocks, posting_time_utc: datetime | None = None, vintage: date | None = None,
                  value_status: str = "first_release", channel: str | None = None, provider_mode: str = "explicit",
                  synthetic: bool = False) -> dict:
    """A published observation. available_at = the logged posting time (published) when the source gives one, else
    the registry's publication instant (calendar_bound; backfilled history is never inferred_from_retrieval).
    A row seen before its publication instant is a provisional print (inferred_from_retrieval)."""
    if posting_time_utc is not None:
        available, src = posting_time_utc, "published"
    else:
        due = clocks.publication_instant(series_id, obs_date)
        if due is None:
            available, src = retrieved_at_utc, "inferred_from_retrieval"
        elif retrieved_at_utc < due:
            available, src, value_status = retrieved_at_utc, "inferred_from_retrieval", "provisional_intraday"
        else:
            available, src = due, "calendar_bound"
    return make_row(series_id=series_id, value=float(value), obs_date=obs_date, session_date=None, obs_utc=available,
                    obs_kind="release", value_status=value_status, available_at_utc=available, available_at_source=src,
                    retrieved_at_utc=retrieved_at_utc, vintage=vintage, source=source, channel=channel,
                    provider_mode=provider_mode, synthetic=synthetic)


def stamp_quote(series_id: str, obs_date: date, value: float, *, quote_utc: datetime, retrieved_at_utc: datetime,
                source: str, channel: str | None = None, provider_mode: str = "explicit", synthetic: bool = False) -> dict:
    """A live quote snapshot: live_snapshot on a quote_snapshot row, available at its stamp."""
    return make_row(series_id=series_id, value=float(value), obs_date=obs_date, session_date=None, obs_utc=quote_utc,
                    obs_kind="quote_snapshot", value_status="live_snapshot", available_at_utc=quote_utc,
                    available_at_source="published", retrieved_at_utc=retrieved_at_utc, vintage=None, source=source,
                    channel=channel, provider_mode=provider_mode, synthetic=synthetic)


def ingest(store: PITStore, series_id: str, rows, *, source: str, retrieved_at_utc: datetime, registry, clocks,
           provider_mode: str = "explicit", synthetic: bool = False, print_times: dict | None = None,
           ohlcv: dict | None = None, channel: str | None = None) -> IngestReport:
    """Stamp and append `[(obs_date, value), ...]` by the series' obs_kind (single shot; the M8 workflow schedules
    it). Flags are returned, never stored. `retrieved_at_utc` is the caller's pinned instant."""
    series_id = named_series(series_id)
    kind = registry.obs_kind(series_id)
    out, flags = [], []
    for obs_date, value in rows:
        if isinstance(obs_date, str):
            obs_date = date.fromisoformat(obs_date)
        if value is None or not math.isfinite(float(value)):
            flags.append(Flag(series_id, obs_date, "non_finite", "no value"))
            continue
        if kind == "close":
            if not clocks.is_session(registry.market(series_id), obs_date):
                flags.append(Flag(series_id, obs_date, "not_a_session", "vendor row on a non-session date"))
                continue
            r = stamp_close(series_id, obs_date, value, retrieved_at_utc=retrieved_at_utc, source=source,
                            registry=registry, clocks=clocks, print_time_utc=(print_times or {}).get(obs_date),
                            ohlcv=(ohlcv or {}).get(obs_date), channel=channel, provider_mode=provider_mode,
                            synthetic=synthetic)
        elif kind == "quote_snapshot":
            r = stamp_quote(series_id, obs_date, value, quote_utc=retrieved_at_utc, retrieved_at_utc=retrieved_at_utc,
                            source=source, channel=channel, provider_mode=provider_mode, synthetic=synthetic)
        elif kind == "release":
            r = stamp_release(series_id, obs_date, value, retrieved_at_utc=retrieved_at_utc, source=source,
                              registry=registry, clocks=clocks, channel=channel, provider_mode=provider_mode,
                              synthetic=synthetic)
        else:
            raise PITError(f"{series_id}: obs_kind {kind} is not ingested from a provider (use put_derived)")
        if isinstance(r, Flag):
            flags.append(r)
        else:
            out.append(r)
    n = store.append(out, fetch_utc=retrieved_at_utc, provider=source)
    return IngestReport(appended=n, logged=len(out) - n, flags=tuple(flags))


def ingest_series(store: PITStore, series_id: str, series, *, retrieved_at_utc: datetime, registry, clocks,
                  provider_mode: str = "explicit") -> IngestReport:
    """Ingest a `core.ficc.data.Series` (or `core.quant.history.History`); a SYNTHETIC source is stamped synthetic."""
    values = getattr(series, "values", None) or getattr(series, "closes", ())
    synthetic = str(getattr(series, "source", "")).upper() == "SYNTHETIC"
    source = "Yahoo" if series.source == "YFINANCE" else series.source
    return ingest(store, series_id, list(zip(series.dates, values)), source=source, retrieved_at_utc=retrieved_at_utc,
                  registry=registry, clocks=clocks, provider_mode=provider_mode, synthetic=synthetic,
                  channel=getattr(series, "note", None) or None)


# --------------------------------------------------------------------------- #
# Reconciliation (L1320-1322; T-BAR-01/02)
# --------------------------------------------------------------------------- #
def reconcile(store: PITStore, series_id: str, obs_date: date, *, knowledge_utc: datetime, registry) -> str:
    """Official vs vendor close of one session: "ok", "disputed" (official used, logged, alerted; never corrected)
    or "vendor_missing" (no vendor row on a KRX session is not a dispute)."""
    rows = [r for r in store.rows(series_id) if r["obs_date"] == obs_date and r["retrieved_at_utc"] <= knowledge_utc]
    official = [r for r in rows if r["value_status"] == "official_close"]
    vendor = [r for r in rows if r["value_status"] == "vendor_close"]
    if not official:
        return "official_missing"
    if not vendor:
        return "vendor_missing"
    best = min(official, key=lambda r: _rank(r, _precedence(registry, series_id)))
    if _dispute(rows, best, registry, series_id):
        store.log_dispute({"series_id": series_id, "obs_date": obs_date.isoformat(), "official": best["value"],
                           "vendor": [r["value"] for r in vendor], "official_source": best["source"],
                           "knowledge_utc": iso_utc(knowledge_utc), "action": "disputed_use_official_and_alert",
                           "auto_correct": False})
        return "disputed"
    return "ok"


# --------------------------------------------------------------------------- #
# Derived and monthly records (TASK-M1-13)
# --------------------------------------------------------------------------- #
def weakest_status(statuses) -> str:
    return max(statuses, key=VALUE_STATUS_RANK.index)


def put_derived(store: PITStore, series_id: str, obs_date: date, value: float, inputs, *, retrieved_at_utc: datetime,
                source: str = "derived", channel: str | None = None, session_date: date | None = None) -> int:
    """A derived row: available_at = latest input available_at; value_status = weakest input status; content_hash
    covers the inputs' hashes; `close_inputs_official` records whether every close-type input is official."""
    if not inputs:
        raise PITError(f"{series_id}: a derived row needs its inputs (lineage)")
    rows = [i if isinstance(i, dict) else {f.name: getattr(i, f.name) for f in fields(PITValue)} for i in inputs]
    available = max(r["available_at_utc"] for r in rows)
    status = weakest_status([r["value_status"] for r in rows])
    closes = [r for r in rows if r["obs_kind"] == "close" or r["value_status"] in CLOSE_STATUSES
              or r["value_status"] == "provisional_intraday"]
    row = make_row(series_id=series_id, value=float(value), obs_date=obs_date, session_date=session_date,
                   obs_utc=available, obs_kind="derived", value_status=status, available_at_utc=available,
                   available_at_source="calendar_bound", retrieved_at_utc=max(retrieved_at_utc, available),
                   vintage=None, source=source, channel=channel,
                   provider_mode="auto" if any(r["provider_mode"] == "auto" for r in rows) else "explicit",
                   synthetic=any(r["synthetic"] for r in rows), inputs=[r["content_hash"] for r in rows])
    row["close_inputs_official"] = all(r["value_status"] == "official_close" for r in closes)
    return store.append([row])


def month_start(d: date) -> date:
    return d.replace(day=1)


def add_months(d: date, n: int) -> date:
    y, m = divmod(d.month - 1 + n, 12)
    return date(d.year + y, m + 1, 1)


@dataclass(frozen=True)
class MonthlyValue:
    value: float            # NaN when flagged
    flagged: bool
    reason: str = ""


def calendar_change(series: dict, obs_month: date, months: int, *, kind: str = "pct") -> MonthlyValue:
    """Change by calendar offset, never positional shift (data.monthly_lag_method: calendar). A missing endpoint
    makes the value NaN and flagged; a gap merely inside the window does not."""
    obs_month = month_start(obs_month)
    base = add_months(obs_month, -months)
    a, b = series.get(base), series.get(obs_month)
    if a is None or b is None or not (math.isfinite(a) and math.isfinite(b)):
        return MonthlyValue(math.nan, True, f"endpoint missing: {base if a is None else obs_month}")
    return MonthlyValue((b / a - 1.0) if kind == "pct" else (b - a), False)


def yoy(series: dict, obs_month: date) -> MonthlyValue:
    return calendar_change(series, obs_month, 12)


def mom(series: dict, obs_month: date) -> MonthlyValue:
    return calendar_change(series, obs_month, 1)


def rolling_mean(series: dict, obs_month: date, n: int = 3) -> MonthlyValue:
    """n-month mean by calendar months (Sahm's 3-month mean); any missing member -> NaN and flagged."""
    obs_month = month_start(obs_month)
    xs = [series.get(add_months(obs_month, -i)) for i in range(n)]
    if any(x is None or not math.isfinite(x) for x in xs):
        return MonthlyValue(math.nan, True, "window member missing")
    return MonthlyValue(sum(xs) / n, False)


def vendor_status_across_gap(window_months, missing_months) -> str:
    """A vendor-derived value whose window contains a missing month is vendor_derived_across_gap (L1354)."""
    missing = {month_start(m) for m in missing_months}
    return "vendor_derived_across_gap" if any(month_start(m) in missing for m in window_months) else "vendor_derived"


# --------------------------------------------------------------------------- #
# Fixtures (TASK-M1-22; T-FIX-01)
# --------------------------------------------------------------------------- #
_PUBLICATION_SCHEDULES = ("FRED_H15", "H10", "TREASURY_PAR", "VIXCLS", "BLS", "BEA")


def _fixture_rows(path: Path) -> list[dict]:
    """Rows of a JSONL store fixture or of a CSV fixture written by docs/macro_fixtures.py (section 4.1 columns)."""
    text = path.read_text(encoding="utf-8")
    lines = [ln for ln in text.split("\n") if ln.strip()]
    if not lines:
        raise FixtureRefused(f"{path.name}: empty fixture")
    if lines[0].lstrip().startswith("{"):
        return [json.loads(ln) for ln in lines]
    import csv
    import io
    rows = list(csv.DictReader(io.StringIO(text)))
    if not rows or "series_id" not in rows[0]:
        raise FixtureRefused(f"{path.name}: a CSV fixture names its series_id on every row")
    return rows


def check_fixture(path, *, registry, clocks) -> int:
    """Refuses a fixture with a close-type row retrieved before close_print_bound_utc(session) + 10 min, or a
    publication-timed row retrieved before its publication_instant. A first line `{"fixture": "synthetic",
    "exempt": true}` labels a test-built synthetic store (T-PROV-01) and exempts it. Returns the rows checked."""
    path = Path(path)
    raw_rows = _fixture_rows(path)
    head = raw_rows[0]
    if head.get("fixture") == "synthetic" and head.get("exempt") is True:
        return 0
    n = 0
    for k, raw in enumerate(raw_rows, 1):
        row = _decode(raw)
        sid = row["series_id"]
        n += 1
        if row.get("obs_kind") == "close" or row.get("value_status") in CLOSE_STATUSES:
            session = row.get("session_date") or row["obs_date"]
            bound = clocks.close_print_bound_utc(registry.market(sid), session)
            if row["retrieved_at_utc"] < bound + timedelta(minutes=QUARANTINE_MINUTES):
                raise FixtureRefused(f"{path.name}:{k}: {sid} {session} retrieved {iso_utc(row['retrieved_at_utc'])} "
                                     f"< close + 10 min {iso_utc(bound + timedelta(minutes=QUARANTINE_MINUTES))}")
        elif registry.is_series(sid) and registry.schedule(sid) in _PUBLICATION_SCHEDULES:
            due = clocks.publication_instant(sid, row["obs_date"])
            if due is not None and row["retrieved_at_utc"] < due:
                raise FixtureRefused(f"{path.name}:{k}: {sid} {row['obs_date']} retrieved before its publication "
                                     f"instant {iso_utc(due)}")
    return n


def write_fixture(path, rows, *, label: dict | None = None) -> Path:
    """Write store rows as a JSONL fixture; `label` (e.g. the synthetic exemption) becomes the first line."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = (canonical_json(label) + "\n" if label else "") + "".join(_dump(r) + "\n" for r in rows)
    path.write_text(text, encoding="utf-8", newline="\n")
    return path


__all__ = [n for n in dir() if not n.startswith("_")]
