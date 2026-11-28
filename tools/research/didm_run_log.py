"""Append-only hash-chained run-log wrapper for DIDM 15m collection, snapshots & receipts.

The owner can select the QUANTGEN checkout with --collector-cwd and supply its Python
interpreter, -m, tools.didm.collect_daily and the desired source options with separate
--collector-arg entries. Use --collector-arg=-m for values starting with a dash.
Complete GDELT events/GKG receipts establish slots, even when SQLite deduplicates rows.
Unknown slots remain queued. A later backfill uses its own completion time.

Research only. Coordinates per-KST-day DIDM SQLite stores, GDELT 15-minute slot tracking
and backfill, offline SQLite backup + didm_source_bridge inspection + Section 9 report
retention, and DIDM V0 / QuantGPT delivery receipts.
Zero imports from core.compliance, core.odds, execution*, tools.owner, config, or main.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import tempfile
import time
from typing import Any, Callable, Mapping, Sequence

from tools.research import didm_source_bridge as bridge
from tools.research import quantgpt_feature_bridge as qfb
from tools.research._study_common import (
    DEFAULT_MAX_BYTES,
    HEX64_RE,
    HashChainedLog,
    RESEARCH_FLAGS,
    StudyError,
    UTC,
    canonical_ascii_str,
    check_safe_path,
    ensure_safe_directory,
    kst_day_str,
    loads_strict_json,
    parse_aware_iso,
    parse_epoch_int,
    read_safe_bytes,
    read_verified_chained_log,
    require,
    sha256_raw,
)


RUN_LOG_FILENAME = "run_log.jsonl"
RUN_LOG_SCHEMA = "tradegen-didm-run-log-v1"
SLOT_STAMP_RE = re.compile(r"[0-9]{14}\Z")
GDELT_SOURCES = frozenset({"gdelt-events2", "gdelt-gkg2"})
MAX_BACKFILLS_PER_RUN = 8


@dataclass(frozen=True)
class CollectorExecResult:
    returncode: int
    stdout: str
    stderr: str = ""


# --------------------------------------------------------------------------- #
# 15-Minute UTC GDELT Slot Stamp Helpers
# --------------------------------------------------------------------------- #
def slot_epoch_to_stamp(slot_epoch: int) -> str:
    require(type(slot_epoch) is int and slot_epoch > 0 and slot_epoch % 900 == 0, "INVALID_GDELT_SLOT")
    return datetime.fromtimestamp(slot_epoch, UTC).strftime("%Y%m%d%H%M00")


def stamp_to_slot_epoch(stamp: str) -> int:
    require(type(stamp) is str and SLOT_STAMP_RE.fullmatch(stamp) is not None and stamp.endswith("00"), "INVALID_GDELT_SLOT")
    try:
        dt = datetime(
            int(stamp[0:4]),
            int(stamp[4:6]),
            int(stamp[6:8]),
            int(stamp[8:10]),
            int(stamp[10:12]),
            0,
            tzinfo=UTC,
        )
    except ValueError:
        raise StudyError("INVALID_GDELT_SLOT") from None
    epoch = int(dt.timestamp())
    require(epoch % 900 == 0, "INVALID_GDELT_SLOT")
    return epoch


def default_target_slot_epoch(now_epoch: int) -> int:
    parse_epoch_int(now_epoch, low=900, error_code="INVALID_TIMESTAMP")
    if now_epoch % 900 == 0:
        return now_epoch - 900
    return (now_epoch // 900) * 900


def extract_row_slot_stamp(row: Mapping[str, Any], parsed_payload: Mapping[str, Any] | None = None) -> str | None:
    """Determine a GDELT row's 15-minute UTC slot stamp."""
    if row.get("source_id") not in GDELT_SOURCES:
        return None
    payload = parsed_payload
    if payload is None and type(row.get("payload")) is str:
        try:
            payload = loads_strict_json(row["payload"], max_bytes=bridge.MAX_PAYLOAD_BYTES)
        except StudyError:
            payload = None
    if isinstance(payload, Mapping):
        for key in ("slot_stamp", "slot", "gdelt_slot"):
            candidate = payload.get(key)
            if type(candidate) is str and SLOT_STAMP_RE.fullmatch(candidate) is not None:
                try:
                    stamp_to_slot_epoch(candidate)
                    return candidate
                except StudyError:
                    pass
    item_id = str(row.get("item_id", ""))
    prefix = item_id[:14]
    if len(prefix) == 14 and SLOT_STAMP_RE.fullmatch(prefix) is not None:
        if len(item_id) == 14 or item_id[14] in (":", "-", "_", "/"):
            try:
                stamp_to_slot_epoch(prefix)
                return prefix
            except StudyError:
                pass
    pub_dt = parse_aware_iso(row["published_at"], error_code="DIDM_TIME_INVALID")
    floored = (int(pub_dt.timestamp()) // 900) * 900
    return slot_epoch_to_stamp(floored)


# --------------------------------------------------------------------------- #
# SQLite Inspection Helpers for Live Daily DIDM Store
# --------------------------------------------------------------------------- #
def _read_store_max_seq(store_path: Path) -> int:
    if not os.path.lexists(store_path):
        return 0
    check_safe_path(store_path, error_code="DIDM_STORE_PATH_REFUSED")
    conn = sqlite3.connect(store_path.as_uri() + "?mode=ro", uri=True, timeout=5.0)
    try:
        conn.execute("PRAGMA query_only=ON")
        row = conn.execute("SELECT COALESCE(MAX(seq), 0) FROM items").fetchone()
        return int(row[0]) if row and row[0] is not None else 0
    except sqlite3.Error:
        raise StudyError("DIDM_STORE_READ_FAILED") from None
    finally:
        conn.close()


def _inspect_new_store_rows(store_path: Path, pre_max_seq: int) -> tuple[int, dict[str, int]]:
    if not os.path.lexists(store_path):
        return pre_max_seq, {}
    check_safe_path(store_path, error_code="DIDM_STORE_PATH_REFUSED")
    conn = sqlite3.connect(store_path.as_uri() + "?mode=ro", uri=True, timeout=5.0)
    try:
        conn.execute("PRAGMA query_only=ON")
        cursor = conn.execute(
            "SELECT seq,source_id,item_id,kind,published_at,valid_at,received_at,payload,payload_sha256 "
            "FROM items WHERE seq > ? ORDER BY seq",
            (pre_max_seq,),
        )
        counts = {}
        post_max = pre_max_seq
        for vals in cursor:
            row_dict = dict(zip(bridge.ROW_COLUMNS, vals))
            try:
                bridge.check_row(row_dict)
            except bridge.BridgeError as exc:
                raise StudyError(str(exc)) from None
            source = row_dict["source_id"]
            group = "gdelt" if source in GDELT_SOURCES else source
            counts[group] = counts.get(group, 0) + 1
            post_max = max(post_max, int(row_dict["seq"]))
        return post_max, counts
    except sqlite3.Error:
        raise StudyError("DIDM_STORE_READ_FAILED") from None
    finally:
        conn.close()


_SOURCE_REPORTS = {
    "alfred": ("ALFRED", r"ALFRED (?:file )?[^ :]+: vintage rows ([0-9]+), new [0-9]+"),
    "ecos": ("ECOS", r"ECOS [^ ]+ [^ ]+ [^ :]+: observations ([0-9]+), new [0-9]+"),
    "sec-edgar": ("EDGAR", r"EDGAR CIK [0-9]+: filings ([0-9]+), new [0-9]+"),
    "opendart": ("OpenDART", r"OpenDART [0-9]{8}-[0-9]{8}: pages [0-9]+, filings ([0-9]+), new [0-9]+"),
    "kalshi": ("Kalshi", r"Kalshi [^ :]+: pages [0-9]+ \(complete True\), markets ([0-9]+), "
                         r"priced [0-9]+, volume missing [0-9]+, liquid [0-9]+, new [0-9]+"),
}
COLLECTOR_EVIDENCE = "quantgen-gdelt-file-evidence-v1"


def _new_rows_in_receipts(lines):
    return sum(int(re.search(r", new ([0-9]+)", line)[1]) for line in lines)


def _slot_receipts(stdout: str, wanted: set[str]) -> dict[str, str]:
    """Only an exact events/GKG pair or a fully accounted bounded range proves its slots."""
    receipts = {}
    for line in stdout.splitlines():
        pair = re.fullmatch(r"GDELT (files|backfill files) 2 \(([0-9]{14}):(events|gkg), "
                            r"([0-9]{14}):(events|gkg)\), rows [0-9]+, new [0-9]+", line)
        if pair and pair[2] == pair[4] and pair[2] in wanted and pair[3] != pair[5]:
            receipts[pair[2]] = line
            continue
        fallback = re.fullmatch(r"GDELT fallback ([0-9]{14})\.\.([0-9]{14}): files 4, missing 0, "
                                r"rows [0-9]+, new [0-9]+ \(zip CRC checked, md5 not published for these\)", line)
        if fallback:
            try:
                adjacent = stamp_to_slot_epoch(fallback[2]) - stamp_to_slot_epoch(fallback[1]) == 900
            except StudyError:
                adjacent = False
            if adjacent:
                for stamp in wanted.intersection((fallback[1], fallback[2])):
                    receipts[stamp] = line
            continue
        day = re.fullmatch(r"GDELT day ([0-9]{8}) UTC \(events\+gkg\): files 192, missing 0, "
                           r"rows [0-9]+, new [0-9]+", line)
        if day:
            for stamp in wanted:
                if stamp.startswith(day[1]):
                    receipts[stamp] = line
    return receipts


def _source_receipts(stdout: str, source: str) -> list[str]:
    if source not in _SOURCE_REPORTS:
        return []
    label, pattern = _SOURCE_REPORTS[source]
    reports = [line for line in stdout.splitlines() if line.startswith(label + " ")]
    # One failed series, partial pagination, skipped call or unknown output prevents
    # a group success. Do not mistake the separate diagnostic field list for data.
    if source == "kalshi":
        reports = [line for line in reports if not line.startswith("Kalshi field names (first market): ")]
    for line in reports:
        match = re.fullmatch(pattern, line)
        if not match or int(match[1]) == 0:
            return []
    return reports


# --------------------------------------------------------------------------- #
# Run-Log State Summary
# --------------------------------------------------------------------------- #
def summarize_run_log(
    log_dir: Path | str,
    *,
    pinned_head: str | None = None,
) -> dict[str, Any]:
    entries, head = read_verified_chained_log(log_dir, RUN_LOG_FILENAME, pinned_head=pinned_head)
    slot_known_at: dict[str, int] = {}
    slot_known_epoch: dict[int, int] = {}
    ever_missing_slots: set[str] = set()
    source_runs: dict[str, list[dict[str, Any]]] = {}
    bridge_snapshots: list[dict[str, Any]] = []
    didm_export_receipts: dict[str, dict[str, Any]] = {}
    quantgpt_receipts: dict[str, dict[str, Any]] = {}

    for row in entries:
        data = row["data"]
        kind = data.get("kind")
        if kind == "collector_run":
            finished = int(data["finished_at"])
            received = set(data.get("fetched_slots", ())) | set(data.get("backfilled_slots", ()))
            versioned = data.get("collector_evidence") == COLLECTOR_EVIDENCE
            evidence = data.get("slot_receipts", {})
            source_proofs = data.get("source_receipts", {})
            for stamp in received:
                ep = stamp_to_slot_epoch(stamp)
                receipt = evidence.get(stamp) if type(evidence) is dict else None
                if (not versioned or type(receipt) is not str or data.get("returncode") != 0
                        or stamp not in _slot_receipts(receipt, {stamp})):
                    ever_missing_slots.add(stamp)
                    continue
                if stamp not in slot_known_at or finished < slot_known_at[stamp]:
                    slot_known_at[stamp] = finished
                    slot_known_epoch[ep] = finished
            for stamp in data.get("missing_slots", ()):
                ever_missing_slots.add(stamp)
            for src, ok_val in data.get("sources_ok", {}).items():
                if src == "gdelt":
                    target = data.get("target_slot")
                    receipt = evidence.get(target) if type(evidence) is dict else None
                    seen = type(receipt) is str and target in _slot_receipts(receipt, {target})
                else:
                    lines = source_proofs.get(src, []) if type(source_proofs) is dict else []
                    seen = (type(lines) is list and all(type(line) is str for line in lines)
                            and bool(_source_receipts("\n".join(lines), src)))
                source_runs.setdefault(src, []).append({
                    "started_at": int(data["started_at"]),
                    "finished_at": finished,
                    "succeeded": versioned and bool(seen) and ok_val is True and data.get("returncode") == 0,
                })
        elif kind == "bridge_snapshot":
            bridge_snapshots.append(dict(data))
        elif kind == "didm_export_receipt":
            sha = data["export_sha256"]
            rec_at = int(data["received_at"])
            if sha not in didm_export_receipts or rec_at < didm_export_receipts[sha]["received_at"]:
                didm_export_receipts[sha] = dict(data)
        elif kind == "quantgpt_receipt":
            sha = data["snapshot_sha256"]
            rec_at = int(data["received_at"])
            if sha not in quantgpt_receipts or rec_at < quantgpt_receipts[sha]["received_at"]:
                quantgpt_receipts[sha] = dict(data)

    unresolved_missing = sorted(s for s in ever_missing_slots if s not in slot_known_at)
    return {
        "format": RUN_LOG_SCHEMA,
        **RESEARCH_FLAGS,
        "head_sha256": head,
        "entry_count": len(entries),
        "slot_known_at": slot_known_at,
        "slot_known_epoch": slot_known_epoch,
        "unresolved_missing_slots": unresolved_missing,
        "source_runs": source_runs,
        "bridge_snapshots": bridge_snapshots,
        "didm_export_receipts": didm_export_receipts,
        "quantgpt_receipts": quantgpt_receipts,
    }


# --------------------------------------------------------------------------- #
# Collector Run Wrapper, Bridge Snapshot & Receipt Recorders
# --------------------------------------------------------------------------- #
def _default_subprocess_runner(
    command_prefix: Sequence[str],
    store_path: Path,
    backfill_stamps: Sequence[str],
    collector_cwd: Path | None = None,
) -> CollectorExecResult:
    def call(argv):
        try:
            proc = subprocess.run(argv, cwd=collector_cwd, capture_output=True, text=True,
                                  timeout=300, check=False,
                                  env={k: os.environ[k] for k in ("PATH", "SYSTEMROOT", "TEMP", "TMP", "LANG")
                                       if k in os.environ})
            return CollectorExecResult(proc.returncode, proc.stdout, proc.stderr)
        except (OSError, subprocess.TimeoutExpired):
            return CollectorExecResult(1, "")

    # QUANTGEN collect_daily writes <data-dir>/didm_store.sqlite and fetches
    # the newest published files, which need not match the requested clock slot.
    if collector_cwd is not None:
        collector_cwd = collector_cwd.resolve(strict=True)
    latest = call([*command_prefix, "--data-dir", str(store_path.parent)])
    if latest.returncode != 0 or not backfill_stamps or "--no-gdelt" in command_prefix:
        return latest
    wanted = set(backfill_stamps)
    pending = sorted(wanted - _slot_receipts(latest.stdout, wanted).keys())
    if not pending or collector_cwd is None:
        return latest
    # Targeted repair is available with the canonical Python module invocation.
    # A custom executable has no known interpreter or QUANTGEN package location.
    try:
        index = command_prefix.index("-m")
    except ValueError:
        return latest
    if tuple(command_prefix[index:index+2]) != ("-m", "tools.didm.collect_daily"):
        return latest
    script = Path(__file__).with_name("didm_quantgen_slots.py").resolve()
    repair = call([*command_prefix[:index], str(script), str(collector_cwd),
                   str(store_path.parent), *pending])
    # Each repair receipt is emitted only after its SQLite append. If this child
    # itself aborts, do not count its partial claims; latest remains independent.
    output = latest.stdout + "\n" + repair.stdout if repair.returncode == 0 else latest.stdout
    return CollectorExecResult(latest.returncode, output)


def run_collector_once(
    log_dir: Path | str,
    stores_root: Path | str,
    *,
    started_at: int,
    finished_at: int | None = None,
    target_slot_stamp: str | None = None,
    sources: Sequence[str] | None = None,
    collector_runner: Callable[[Path, str, Sequence[str]], CollectorExecResult] | None = None,
    collector_cmd: Sequence[str] | None = None,
    collector_cwd: Path | None = None,
    max_backfill_lookback_seconds: int = 7 * 86400,
) -> dict[str, Any]:
    """Run one 15-minute DIDM collector step into kst_YYYYMMDD/didm_store.sqlite and log verified state."""
    parse_epoch_int(started_at, low=900, error_code="INVALID_TIMESTAMP")
    require(type(max_backfill_lookback_seconds) is int and 0 <= max_backfill_lookback_seconds <= 7 * 86400,
            "INVALID_BACKFILL_LOOKBACK")
    require(collector_runner is not None or bool(collector_cmd), "COLLECTOR_RUNNER_REQUIRED")

    if sources is None and collector_cmd:
        flags = {arg.partition("=")[0] for arg in collector_cmd}
        options = {"alfred": {"--alfred", "--alfred-file"}, "ecos": {"--ecos"},
                   "sec-edgar": {"--edgar"}, "opendart": {"--opendart"}, "kalshi": {"--kalshi"}}
        sources = [src for src, switches in options.items() if flags.intersection(switches)]
        if "--no-gdelt" not in flags or "--gdelt-day" in flags:
            sources.append("gdelt")
    if sources is None:
        sources = ("gdelt", "alfred", "ecos")
    require(bool(sources) and set(sources) <= {"gdelt", *_SOURCE_REPORTS}, "COLLECTOR_SOURCE_REQUIRED")
    target_epoch = (
        stamp_to_slot_epoch(target_slot_stamp)
        if target_slot_stamp is not None
        else default_target_slot_epoch(started_at)
    )
    target_stamp = slot_epoch_to_stamp(target_epoch)
    kst_day = kst_day_str(started_at)
    day_dir = ensure_safe_directory(Path(stores_root) / f"kst_{kst_day}", error_code="DIDM_STORE_PATH_REFUSED")
    store_path = check_safe_path(day_dir / "didm_store.sqlite", error_code="DIDM_STORE_PATH_REFUSED")

    require(0 < target_epoch <= started_at, "INVALID_GDELT_SLOT")
    with HashChainedLog(log_dir, RUN_LOG_FILENAME, lock_name=".run_log.lock") as log:
        prior_summary = summarize_run_log(log_dir)
        min_backfill_epoch = target_epoch - max_backfill_lookback_seconds
        queued_backfills = [
            s for s in prior_summary["unresolved_missing_slots"]
            if min_backfill_epoch <= stamp_to_slot_epoch(s) < target_epoch
        ]
        last_attempt = {}
        for row in log.entries:
            for stamp in row["data"].get("requested_backfills", ()):
                last_attempt[stamp] = row["seq"]
        queued_backfills.sort(key=lambda stamp: (last_attempt.get(stamp, -1), stamp))
        queued_backfills = queued_backfills[:MAX_BACKFILLS_PER_RUN] if "gdelt" in sources else []
        pre_max_seq = _read_store_max_seq(store_path)
        if collector_runner is not None:
            exec_res = collector_runner(store_path, target_stamp, queued_backfills)
        else:
            assert collector_cmd is not None
            exec_res = _default_subprocess_runner(collector_cmd, store_path, queued_backfills, collector_cwd)

        post_max_seq, added_by_source = _inspect_new_store_rows(store_path, pre_max_seq)
        wanted = {target_stamp, *queued_backfills}
        completed = exec_res.returncode == 0 and store_path.is_file()
        slot_receipts = _slot_receipts(exec_res.stdout, wanted) if completed and "gdelt" in sources else {}
        if _new_rows_in_receipts(set(slot_receipts.values())) > added_by_source.get("gdelt", 0):
            slot_receipts = {}
        verified_slots = set(slot_receipts)
        source_receipts = {src: _source_receipts(exec_res.stdout, src) if completed else []
                           for src in sources if src != "gdelt"}
        for src, lines in source_receipts.items():
            if _new_rows_in_receipts(lines) > added_by_source.get(src, 0):
                source_receipts[src] = []
        sources_ok = {src: bool(lines) for src, lines in source_receipts.items()}
        if "gdelt" in sources:
            sources_ok["gdelt"] = target_stamp in verified_slots

        fetched_primary: list[str] = []
        missing_now: list[str] = []
        if "gdelt" in sources:
            if target_stamp in verified_slots:
                fetched_primary.append(target_stamp)
            else:
                missing_now.append(target_stamp)

        backfilled_now: list[str] = []
        for bf_stamp in queued_backfills:
            if bf_stamp in verified_slots:
                backfilled_now.append(bf_stamp)
            else:
                missing_now.append(bf_stamp)

        # Round up the completed verification instant when recording integer seconds.
        actual_finished = parse_epoch_int(math.ceil(time.time()) if finished_at is None else finished_at,
                                          low=started_at)
        entry_data = {
            "kind": "collector_run",
            "collector_evidence": COLLECTOR_EVIDENCE,
            "slot_receipts": slot_receipts,
            "source_receipts": source_receipts,
            "kst_day": kst_day,
            "store_path": str(store_path),
            "started_at": started_at,
            "finished_at": actual_finished,
            "returncode": int(exec_res.returncode),
            "pre_max_seq": pre_max_seq,
            "post_max_seq": post_max_seq,
            "new_row_count": sum(added_by_source.values()),
            "new_rows_by_source": added_by_source,
            "sources_ok": sources_ok,
            "target_slot": target_stamp,
            "requested_backfills": queued_backfills,
            "fetched_slots": sorted(fetched_primary),
            "backfilled_slots": sorted(backfilled_now),
            "missing_slots": sorted(set(missing_now)),
        }
        appended = log.append(entry_data)
        return {**RESEARCH_FLAGS, **entry_data, "log_seq": appended["seq"], "log_sha256": appended["sha256"]}


def take_bridge_snapshot(
    log_dir: Path | str,
    store_path: Path | str,
    report_output_path: Path | str,
    *,
    as_of_iso: str,
    captured_at: int,
    kst_day: str | None = None,
    retain_latest_only: bool = True,
) -> dict[str, Any]:
    """Coordinated SQLite backup -> didm_source_bridge inspection report -> retention cleanup."""
    parse_epoch_int(captured_at, error_code="INVALID_TIMESTAMP")
    cutoff_dt = parse_aware_iso(as_of_iso, error_code="DIDM_TIME_INVALID")
    src_store = check_safe_path(store_path, error_code="DIDM_STORE_PATH_REFUSED")
    require(src_store.is_file(), "DIDM_STORE_MISSING")
    dest_report = check_safe_path(report_output_path, error_code="DIDM_OUTPUT_PATH_REFUSED")
    inferred_kst = kst_day or kst_day_str(int(cutoff_dt.timestamp()))

    prior_summary = summarize_run_log(log_dir)
    prior_same_day_reports = [
        Path(snap["report_path"])
        for snap in prior_summary["bridge_snapshots"]
        if snap.get("kst_day") == inferred_kst
    ]

    with HashChainedLog(log_dir, RUN_LOG_FILENAME, lock_name=".run_log.lock") as log:
        with tempfile.TemporaryDirectory(prefix="tradegen-didm-backup-") as tmp_dir:
            backup_path = Path(tmp_dir) / "offline_backup.sqlite"
            src_conn = sqlite3.connect(src_store.as_uri() + "?mode=ro", uri=True, timeout=10.0)
            try:
                dst_conn = sqlite3.connect(backup_path)
                try:
                    src_conn.backup(dst_conn)
                finally:
                    dst_conn.close()
            finally:
                src_conn.close()

            # Ensure no sidecars on backup copy and inspect via didm_source_bridge
            work_copy = Path(tmp_dir) / "inspect_copy.sqlite"
            with open(work_copy, "xb") as sink:
                store_digest = bridge.copy_snapshot(backup_path, sink.write, database=True, limit=bridge.MAX_DATABASE_BYTES)

            try:
                with bridge.report_file(dest_report) as write_fn, \
                        bridge.inspection(
                            work_copy,
                            input_kind="sqlite",
                            input_sha256=store_digest,
                            as_of=as_of_iso,
                            directory=tmp_dir,
                        ) as inspection_res:
                    inspection_res.write(write_fn)
                fields = inspection_res.fields
            except bridge.BridgeError as exc:
                raise StudyError(str(exc)) from None

        report_raw = read_safe_bytes(dest_report, max_bytes=bridge.MAX_OUTPUT_BYTES, path_error="DIDM_OUTPUT_PATH_REFUSED")
        report_sha = sha256_raw(report_raw)

        deleted_paths: list[str] = []
        if retain_latest_only:
            for old_path in prior_same_day_reports:
                safe_old = check_safe_path(old_path, error_code="DIDM_OUTPUT_PATH_REFUSED")
                if safe_old != dest_report and safe_old.is_file() and not safe_old.is_symlink():
                    safe_old.unlink()
                    deleted_paths.append(str(safe_old))

        entry_data = {
            "kind": "bridge_snapshot",
            "kst_day": inferred_kst,
            "store_path": str(src_store),
            "store_sha256": store_digest,
            "report_path": str(dest_report),
            "report_sha256": report_sha,
            "as_of": fields["as_of"],
            "captured_at": captured_at,
            "record_count": fields["record_count"],
            "selected_count": fields["selected_count"],
            "deleted_superseded_reports": deleted_paths,
        }
        appended = log.append(entry_data)
        return {**RESEARCH_FLAGS, **entry_data, "log_seq": appended["seq"], "log_sha256": appended["sha256"]}


def record_didm_export(
    log_dir: Path | str,
    export_path: Path | str,
    *,
    received_at: int,
    as_of_iso: str | None = None,
) -> dict[str, Any]:
    """Verify a tradegen-didm-exchange-v1 export file and record its PC receipt time in run_log.jsonl."""
    parse_epoch_int(received_at, error_code="INVALID_TIMESTAMP")
    cutoff_iso = as_of_iso or datetime.fromtimestamp(received_at, UTC).isoformat()
    safe_export = check_safe_path(export_path, error_code="DIDM_EXPORT_PATH_REFUSED")
    try:
        raw = bridge.read_snapshot(safe_export)
        export_sha = bridge.sha256(raw)
        with tempfile.TemporaryDirectory(prefix="tradegen-didm-export-") as tmp_dir:
            with bridge.inspection(
                raw,
                input_kind="export",
                input_sha256=export_sha,
                as_of=cutoff_iso,
                directory=tmp_dir,
            ) as res:
                fields = res.fields
    except bridge.BridgeError as exc:
        raise StudyError(str(exc)) from None

    with HashChainedLog(log_dir, RUN_LOG_FILENAME, lock_name=".run_log.lock") as log:
        entry_data = {
            "kind": "didm_export_receipt",
            "export_path": str(safe_export),
            "export_sha256": export_sha,
            "received_at": received_at,
            "record_count": fields["record_count"],
            "score_count": fields["score_count"],
        }
        appended = log.append(entry_data)
        return {**RESEARCH_FLAGS, **entry_data, "log_seq": appended["seq"], "log_sha256": appended["sha256"]}


def record_quantgpt_receipt(
    log_dir: Path | str,
    snapshot_path: Path | str,
    *,
    received_at: int,
    surface: str = "feature_snapshot",
    expected_sha256: str | None = None,
) -> dict[str, Any]:
    """Validate a QuantGPT snapshot/envelope batch and record its PC receipt time in run_log.jsonl."""
    parse_epoch_int(received_at, error_code="INVALID_TIMESTAMP")
    require(surface in ("feature_snapshot", "envelopes"), "QGPT_SURFACE_INVALID")
    safe_path = check_safe_path(snapshot_path, error_code="QGPT_SNAPSHOT_FILE")

    if surface == "feature_snapshot":
        snap = qfb.read_feature_snapshot(safe_path, expected_sha256)
        snap_sha = snap["snapshot_sha256"]
        producer = snap["producer"]
        model_info = snap["model"]
        item_count = len(snap["records"])
    else:
        raw = read_safe_bytes(safe_path, max_bytes=DEFAULT_MAX_BYTES, path_error="QGPT_SNAPSHOT_FILE")
        snap_sha = sha256_raw(raw)
        if expected_sha256 is not None:
            require(HEX64_RE.fullmatch(expected_sha256) is not None and snap_sha == expected_sha256, "QGPT_SNAPSHOT_SHA256_MISMATCH")
        rows = qfb._read_jsonl_strict(safe_path)
        require(len(rows) > 0, "QGPT_EMPTY_ENVELOPE_BATCH")
        events = qfb.extract_q1_events_from_envelopes(rows, receipt_at=received_at)
        first_env = rows[0]["envelope"]
        producer = "quantgpt"
        model_info = dict(first_env["model"])
        item_count = len(events)

    with HashChainedLog(log_dir, RUN_LOG_FILENAME, lock_name=".run_log.lock") as log:
        entry_data = {
            "kind": "quantgpt_receipt",
            "surface": surface,
            "snapshot_path": str(safe_path),
            "snapshot_sha256": snap_sha,
            "received_at": received_at,
            "producer": producer,
            "model": model_info,
            "item_count": item_count,
        }
        appended = log.append(entry_data)
        return {**RESEARCH_FLAGS, **entry_data, "log_seq": appended["seq"], "log_sha256": appended["sha256"]}


# --------------------------------------------------------------------------- #
# CLI Entry Point
# --------------------------------------------------------------------------- #
def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_col = sub.add_parser("run-collector", help="Run 15-minute DIDM collector into per-KST-day store")
    p_col.add_argument("--log-dir", type=Path, required=True)
    p_col.add_argument("--stores-root", type=Path, required=True)
    p_col.add_argument("--target-slot", help="Optional explicit 14-digit UTC GDELT slot stamp")
    p_col.add_argument("--collector-cwd", type=Path, help="QUANTGEN checkout for python -m tools.didm.collect_daily")
    p_col.add_argument("--source", action="append", choices=["gdelt", *_SOURCE_REPORTS],
                       help="Source group expected in this run (repeat for each group)")
    p_col.add_argument("--collector-arg", action="append", required=True, help="Collector executable and base args")

    p_snap = sub.add_parser("take-snapshot", help="Backup daily SQLite store, run bridge, and clean superseded reports")
    p_snap.add_argument("--log-dir", type=Path, required=True)
    p_snap.add_argument("--database", type=Path, required=True)
    p_snap.add_argument("--output", type=Path, required=True)
    p_snap.add_argument("--as-of", required=True)
    p_snap.add_argument("--keep-superseded", action="store_true")

    p_exp = sub.add_parser("record-didm-export", help="Verify and log a tradegen-didm-exchange-v1 receipt")
    p_exp.add_argument("--log-dir", type=Path, required=True)
    p_exp.add_argument("--export", type=Path, required=True)
    p_exp.add_argument("--received-at", type=int, help="Optional integer epoch seconds (defaults to current UTC second)")

    p_qgpt = sub.add_parser("record-quantgpt", help="Verify and log a QuantGPT snapshot or envelope receipt")
    p_qgpt.add_argument("--log-dir", type=Path, required=True)
    p_qgpt.add_argument("--snapshot", type=Path, required=True)
    p_qgpt.add_argument("--surface", choices=["feature_snapshot", "envelopes"], default="feature_snapshot")
    p_qgpt.add_argument("--expected-sha256")
    p_qgpt.add_argument("--received-at", type=int)

    p_sum = sub.add_parser("summarize", help="Verify chain and print run-log summary")
    p_sum.add_argument("--log-dir", type=Path, required=True)
    p_sum.add_argument("--pinned-head")

    args = parser.parse_args(argv)
    now_ts = int(time.time())
    try:
        if args.cmd == "run-collector":
            report = run_collector_once(
                args.log_dir,
                args.stores_root,
                started_at=now_ts,
                target_slot_stamp=args.target_slot,
                collector_cmd=args.collector_arg,
                collector_cwd=args.collector_cwd,
                sources=args.source,
            )
        elif args.cmd == "take-snapshot":
            report = take_bridge_snapshot(
                args.log_dir,
                args.database,
                args.output,
                as_of_iso=args.as_of,
                captured_at=now_ts,
                retain_latest_only=not args.keep_superseded,
            )
        elif args.cmd == "record-didm-export":
            report = record_didm_export(
                args.log_dir,
                args.export,
                received_at=now_ts if args.received_at is None else args.received_at,
            )
        elif args.cmd == "record-quantgpt":
            report = record_quantgpt_receipt(
                args.log_dir,
                args.snapshot,
                received_at=now_ts if args.received_at is None else args.received_at,
                surface=args.surface,
                expected_sha256=args.expected_sha256,
            )
        else:
            report = summarize_run_log(args.log_dir, pinned_head=args.pinned_head)
        print(canonical_ascii_str(report))
        if args.cmd == "run-collector" and (report["missing_slots"] or not all(report["sources_ok"].values())):
            return 3
        return 0
    except StudyError as exc:
        reason = str(exc)
    except (OSError, ValueError, TypeError):
        reason = "RUN_LOG_REFUSED"
    print(canonical_ascii_str({**RESEARCH_FLAGS, "reason": reason}))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
