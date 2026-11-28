"""Point-in-time feature builder (P1..P4, D1..D3, Q1) for Section-12 direction study.

Research only. Zero imputation; strict known_at <= as_of gating across price bars,
daily DIDM inspection reports, DIDM V0 score exports, QuantGPT snapshots, and run_log.jsonl.
Zero imports from core.compliance, core.odds, execution*, tools.owner, config, or main.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import math
import tempfile
from pathlib import Path
from typing import Any, Mapping, Sequence

from tools.research import didm_run_log as rl
from tools.research import didm_source_bridge as bridge
from tools.research import quantgpt_feature_bridge as qfb
from tools.research._study_common import (
    DEFAULT_MAX_BYTES,
    HEX40_RE,
    HEX64_RE,
    MARKET_RE,
    RESEARCH_FLAGS,
    StudyError,
    UTC,
    atomic_publish_json_ascii,
    canonical_ascii_str,
    format_utc_microseconds,
    parse_aware_iso,
    parse_epoch_int,
    read_strict_json_file,
    require,
    sha256_ascii,
)


FEATURE_TABLE_FORMAT = "tradegen-direction-features-v1"
ALL_FEATURES = ("P1", "P2", "P3", "P4", "D1", "D2", "D3", "Q1")
PRICE_FEATURES = ("P1", "P2", "P3", "P4")
DEFAULT_FEATURES = ("P1", "P2", "P3", "P4", "D2")
DEFAULT_D1_SERIES = ("alfred:CPIAUCSL", "alfred:PAYEMS", "ecos:722Y001:0101000")
DEFAULT_D3_EVENT_TYPES = ("crypto_regulation_hack", "monetary_policy")
DEFAULT_Q1_EVENT_TYPES = ("crypto_regulation_hack", "regulation_litigation", "monetary_policy")

GDELT_NUMERATOR_SLOTS = 96
GDELT_DENOMINATOR_SLOTS = 672
GDELT_MIN_DENOMINATOR_SLOTS = math.ceil(0.95 * GDELT_DENOMINATOR_SLOTS)  # 639


# --------------------------------------------------------------------------- #
# DIDM Report Merging & Point-in-Time Re-Selection (Exact Bridge Parity)
# --------------------------------------------------------------------------- #
def _normalize_didm_record(item: Mapping[str, Any]) -> dict[str, Any]:
    require(type(item) is dict and set(item) == {"record_sha256", "row"}, "DIDM_REPORT_RECORD_INVALID")
    row = item["row"]
    try:
        checked = bridge.check_row(row)
    except bridge.BridgeError as exc:
        raise StudyError(str(exc)) from None
    require(checked["record_sha256"] == item["record_sha256"], "DIDM_RECORD_HASH_MISMATCH")
    recv_dt = checked["times"]["received_at"]
    valid_dt = checked["times"]["valid_at"]
    pub_dt = checked["times"]["published_at"]
    return {
        "record_sha256": checked["record_sha256"],
        "row": row,
        "parsed": checked["parsed"],
        "source_id": row["source_id"],
        "item_id": row["item_id"],
        "payload_sha256": row["payload_sha256"],
        "received_utc": format_utc_microseconds(recv_dt),
        "valid_utc": format_utc_microseconds(valid_dt),
        "published_utc": format_utc_microseconds(pub_dt),
        "received_epoch": recv_dt.timestamp(),
        "slot_stamp": rl.extract_row_slot_stamp(row, checked["parsed"]),
    }


def merge_didm_reports(reports: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Merge one or more tradegen-didm-inspection-v1 reports, deduplicating identical versions."""
    by_version_key: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for rep in reports:
        require(type(rep) is dict and rep.get("format") == bridge.REPORT_FORMAT, "DIDM_REPORT_FORMAT_INVALID")
        for flag_k, flag_v in RESEARCH_FLAGS.items():
            require(rep.get(flag_k) is flag_v, "DIDM_REPORT_FLAGS_INVALID")
        records = rep.get("records")
        require(type(records) is list, "DIDM_REPORT_FORMAT_INVALID")
        for item in records:
            norm = _normalize_didm_record(item)
            vkey = (norm["source_id"], norm["item_id"], norm["received_utc"], norm["payload_sha256"])
            if vkey in by_version_key:
                # Ignore seq differences across separate daily stores only if payload & timestamps match
                prev_row = {k: v for k, v in by_version_key[vkey]["row"].items() if k != "seq"}
                cur_row = {k: v for k, v in norm["row"].items() if k != "seq"}
                require(prev_row == cur_row, "DIDM_CONFLICTING_DUPLICATE_VERSION")
            else:
                by_version_key[vkey] = norm
    merged = list(by_version_key.values())
    merged.sort(key=lambda r: (r["received_utc"], r["source_id"], r["item_id"], r["payload_sha256"]))
    return merged


def reselect_didm_at(
    merged_records: Sequence[Mapping[str, Any]],
    as_of: int | str | datetime,
) -> list[dict[str, Any]]:
    """Reproduce didm_source_bridge.py's exact SELECT_SQL at any cutoff `as_of`.

    For each (source_id, item_id) with received <= cutoff, selects the version maximizing
    (received_utc, payload_sha256), then orders selected items by (valid_utc, source_id, item_id).
    """
    if isinstance(as_of, int):
        cutoff_dt = datetime.fromtimestamp(as_of, UTC)
    elif isinstance(as_of, str):
        cutoff_dt = parse_aware_iso(as_of, error_code="DIDM_TIME_INVALID")
    elif isinstance(as_of, datetime):
        require(as_of.utcoffset() is not None, "DIDM_AWARE_TIME_REQUIRED")
        cutoff_dt = as_of.astimezone(UTC)
    else:
        raise StudyError("DIDM_TIME_INVALID")

    cutoff_utc = format_utc_microseconds(cutoff_dt)
    best: dict[tuple[str, str], dict[str, Any]] = {}
    for rec in merged_records:
        if rec["received_utc"] > cutoff_utc:
            continue
        key = (rec["source_id"], rec["item_id"])
        rank = (rec["received_utc"], rec["payload_sha256"])
        prev = best.get(key)
        if prev is None or rank > (prev["received_utc"], prev["payload_sha256"]):
            best[key] = dict(rec)

    selected = list(best.values())
    selected.sort(key=lambda r: (r["valid_utc"], r["source_id"], r["item_id"]))
    return selected


# --------------------------------------------------------------------------- #
# D1, D2, D3, Q1 & P1..P4 Feature Computations
# --------------------------------------------------------------------------- #
def _matches_d1_series(rec: Mapping[str, Any], registered_series: set[str]) -> str | None:
    src = rec["source_id"]
    item_id = rec["item_id"]
    parsed = rec["parsed"]
    candidates: list[str] = [f"{src}:{item_id}"]
    if src == "alfred":
        sid = parsed.get("series_id") if isinstance(parsed, Mapping) else None
        if type(sid) is str:
            candidates.append(f"alfred:{sid}")
        base_id = item_id.split(":")[0].split("/")[0]
        candidates.append(f"alfred:{base_id}")
    elif src == "ecos":
        if isinstance(parsed, Mapping) and "stat_code" in parsed and "item_code" in parsed:
            candidates.append(f"ecos:{parsed['stat_code']}:{parsed['item_code']}")
        parts = item_id.split(":")
        if len(parts) >= 2:
            candidates.append(f"ecos:{parts[0]}:{parts[1]}")
    for cand in candidates:
        if cand in registered_series:
            return cand
    return None


def extract_d1_events(
    merged_records: Sequence[Mapping[str, Any]],
    d1_series: Sequence[str],
) -> list[dict[str, Any]]:
    """Compute D1 first-receipt and payload-revision events.

    Re-fetching an unchanged ALFRED vintage or ECOS observation (same payload_sha256)
    does NOT emit a new event.
    """
    reg_set = set(d1_series)
    by_item: dict[tuple[str, str], list[Mapping[str, Any]]] = {}
    for rec in merged_records:
        matched = _matches_d1_series(rec, reg_set)
        if matched is None:
            continue
        by_item.setdefault((rec["source_id"], rec["item_id"]), []).append(rec)

    events: list[dict[str, Any]] = []
    for (src, iid), versions in sorted(by_item.items()):
        ordered = sorted(versions, key=lambda r: (r["received_utc"], r["payload_sha256"]))
        last_payload_sha: str | None = None
        for idx, ver in enumerate(ordered):
            if idx == 0 or ver["payload_sha256"] != last_payload_sha:
                matched_series = _matches_d1_series(ver, reg_set)
                assert matched_series is not None
                events.append({
                    "series": matched_series,
                    "source_id": src,
                    "item_id": iid,
                    "payload_sha256": ver["payload_sha256"],
                    "received_utc": ver["received_utc"],
                    "event_epoch": ver["received_epoch"],
                    "is_revision": idx > 0,
                })
                last_payload_sha = ver["payload_sha256"]
    events.sort(key=lambda e: (e["event_epoch"], e["series"], e["item_id"]))
    return events


def _source_schedule_ok(
    source_runs: Mapping[str, Sequence[Mapping[str, Any]]],
    source_name: str,
    as_of: int,
    max_gap_seconds: int,
) -> bool:
    runs = [r for r in source_runs.get(source_name, ()) if int(r["finished_at"]) <= as_of]
    if not runs:
        return False
    latest = max(runs, key=lambda r: int(r["finished_at"]))
    if not latest.get("succeeded", False):
        return False
    return (as_of - int(latest["finished_at"])) <= max_gap_seconds


def compute_price_features_at(
    bars_by_end: Mapping[int, Mapping[str, Any]],
    as_of: int,
    step_seconds: int,
) -> dict[str, float | None]:
    """Compute P1..P4 from m=1..24 bars ending at as_of - m*step, requiring known_at <= as_of."""
    log_rets: list[float | None] = []
    for m in range(1, 25):
        target_end = as_of - m * step_seconds
        bar = bars_by_end.get(target_end)
        if bar is None or int(bar["known_at"]) > as_of:
            log_rets.append(None)
        else:
            log_rets.append(math.log1p(int(bar["return_bps"]) / 10000.0))

    p1 = log_rets[0]
    p2 = math.fsum(log_rets[:4]) if all(x is not None for x in log_rets[:4]) else None  # type: ignore[arg-type]
    if all(x is not None for x in log_rets):
        vals24 = [float(x) for x in log_rets if x is not None]
        p3: float | None = math.fsum(vals24)
        p4: float | None = math.sqrt(math.fsum(r * r for r in vals24))
    else:
        p3 = None
        p4 = None
    return {"P1": p1, "P2": p2, "P3": p3, "P4": p4}


def compute_d2_at(
    merged_records: Sequence[Mapping[str, Any]],
    slot_known_epoch: Mapping[int, int],
    as_of: int,
) -> float | None:
    """Compute 96-slot / 672-slot GDELT volume ratio at `as_of` with strict run-log slot checks."""
    s_96 = [as_of - m * 900 for m in range(1, GDELT_NUMERATOR_SLOTS + 1)]
    if any(slot_known_epoch.get(s, 2**62) > as_of for s in s_96):
        return None
    s_672 = [as_of - m * 900 for m in range(1, GDELT_DENOMINATOR_SLOTS + 1)]
    present_672 = [s for s in s_672 if slot_known_epoch.get(s, 2**62) <= as_of]
    if len(present_672) < GDELT_MIN_DENOMINATOR_SLOTS:
        return None

    present_set = set(present_672)
    selected = reselect_didm_at(merged_records, as_of)
    slot_counts: dict[int, int] = {}
    for rec in selected:
        if rec["source_id"] not in rl.GDELT_SOURCES:
            continue
        stamp = rec.get("slot_stamp")
        if stamp is None:
            continue
        slot_ep = rl.stamp_to_slot_epoch(stamp)
        if slot_ep in present_set:
            slot_counts[slot_ep] = slot_counts.get(slot_ep, 0) + 1

    num = sum(slot_counts.get(s, 0) for s in s_96)
    total_7d = sum(slot_counts.get(s, 0) for s in present_672)
    denom_mean_96 = total_7d * (float(GDELT_NUMERATOR_SLOTS) / float(len(present_672)))
    if denom_mean_96 == 0.0:
        return 0.0
    return float(num) / denom_mean_96


def prepare_didm_v0_scores(
    exports: Sequence[tuple[Mapping[str, Any], int]],
    *,
    pinned_didm_v0: Mapping[str, str] | None = None,
    strict_s4: bool = False,
) -> tuple[list[dict[str, Any]], list[int], int]:
    """Validate DIDM V0 score exports + PC receipt times.

    Returns (pinned_scores_with_known_at, export_receipt_times, unpinned_score_count).
    """
    pinned_scores: list[dict[str, Any]] = []
    receipt_times: list[int] = []
    unpinned_count = 0
    versions = {}
    score_events = {}
    if exports:
        require(type(pinned_didm_v0) is dict
                and type(pinned_didm_v0.get("model_version")) is str and pinned_didm_v0["model_version"].strip()
                and type(pinned_didm_v0.get("prompt_sha256")) is str
                and HEX64_RE.fullmatch(pinned_didm_v0["prompt_sha256"]), "DIDM_SCORE_PIN_REQUIRED")

    for export_doc, receipt_at in exports:
        parse_epoch_int(receipt_at, error_code="DIDM_RECEIPT_TIME_INVALID")
        receipt_times.append(receipt_at)
        try:
            raw = bridge.canonical(export_doc).encode("utf-8")
            require(len(raw) <= bridge.MAX_INPUT_BYTES, "DIDM_EXPORT_INVALID")
            with tempfile.TemporaryDirectory(prefix="tradegen-score-evidence-") as folder:
                with bridge.inspection(raw, input_kind="export", input_sha256=bridge.sha256(raw),
                                       as_of=datetime.fromtimestamp(receipt_at, UTC).isoformat(),
                                       directory=folder) as inspected:
                    checked_scores = inspected.fields["scores"]
        except bridge.BridgeError as exc:
            raise StudyError(str(exc)) from None

        links = {}
        for row in export_doc["rows"]:
            source_item = (row["source_id"], row["item_id"])
            received = bridge.timestamp(row["received_at"])
            version = (received, row["payload_sha256"])
            key = (source_item, version)
            known_at = max(receipt_at, math.ceil(received.timestamp()))
            versions[key] = min(known_at, versions.get(key, known_at))
            links[bridge.sha256(bridge.canonical(row).encode("utf-8"))] = key

        for wrapped in checked_scores:
            score = wrapped["score"]
            if (score["model_version"] != pinned_didm_v0["model_version"]
                    or score["prompt_sha256"] != pinned_didm_v0["prompt_sha256"]):
                unpinned_count += 1
                if strict_s4:
                    raise StudyError("S4_UPSTREAM_IDENTITY_CHANGED")
                continue
            received = bridge.timestamp(score["received_at"])
            known_at = max(receipt_at, math.ceil(received.timestamp()))
            identity = (score["record_id"], score["model_version"], received)
            source_version = links[wrapped["source_record_sha256"]]
            prior = score_events.get(identity)
            if prior is not None:
                require(prior["score_sha256"] == wrapped["score_sha256"] and prior["source_version"] == source_version,
                        "DIDM_SCORE_REVISION_CONFLICT")
                prior["known_at"] = min(prior["known_at"], known_at)
                continue
            score_events[identity] = {
                "record_id": score["record_id"], "event_type": score["event_type"],
                "ess_like_0_100": float(score["ess_like_0_100"]), "received_epoch": received.timestamp(),
                "known_at": known_at, "score_sha256": wrapped["score_sha256"], "source_version": source_version,
            }

    # A later source version supersedes the old one only when it actually arrives.
    # Walk newest to oldest to find the first time any higher-ranked version was available.
    until = {}
    next_known = {}
    for key in sorted(versions, reverse=True):
        item, _version = key
        until[key] = next_known.get(item)
        next_known[item] = min(versions[key], next_known.get(item, versions[key]))
    next_score = {}
    for identity in sorted(score_events, reverse=True):
        score = score_events[identity]
        family = identity[:2]
        bounds = [t for t in (until[score.pop("source_version")], next_score.get(family)) if t is not None]
        score["superseded_at"] = min(bounds) if bounds else None
        next_score[family] = min(score["known_at"], next_score.get(family, score["known_at"]))
        pinned_scores.append(score)
    return pinned_scores, sorted(receipt_times), unpinned_count


def compute_d3_at(
    pinned_scores: Sequence[Mapping[str, Any]],
    export_receipt_times: Sequence[int],
    as_of: int,
    *,
    d3_event_types: frozenset[str],
    d3_cadence_seconds: int = 86400,
) -> float | None:
    """Mean ess_like_0_100 of pinned V0 scores known in (as_of - 86400, as_of]; 50.0 when 0 events on valid delivery."""
    recent_deliveries = [t for t in export_receipt_times if (as_of - d3_cadence_seconds) < t <= as_of]
    if not recent_deliveries:
        return None
    matching_ess = [
        float(s["ess_like_0_100"])
        for s in pinned_scores
        if (as_of - 86400) < int(s["known_at"]) <= as_of
        and (s.get("superseded_at") is None or as_of < s["superseded_at"])
        and float(s["received_epoch"]) > (as_of - 86400)
        and s["event_type"] in d3_event_types
    ]
    if not matching_ess:
        return 50.0
    return math.fsum(matching_ess) / len(matching_ess)


def compute_q1_at(
    q1_items: Sequence[Mapping[str, Any]],
    q1_receipt_times: Sequence[int],
    as_of: int,
    *,
    q1_event_types: frozenset[str],
    q1_cadence_seconds: int = 86400,
) -> float | None:
    """Categorical 1.0/0.0 QuantGPT risk-news judgment indicator in (as_of - 86400, as_of]."""
    recent_deliveries = [t for t in q1_receipt_times if (as_of - q1_cadence_seconds) < t <= as_of]
    if not recent_deliveries:
        return None
    for item in q1_items:
        known_at = int(item["known_at"])
        rec_as_of = int(item["as_of"])
        ev_type = item["event_type"]
        if (as_of - 86400) < known_at <= as_of and rec_as_of > (as_of - 86400) and ev_type in q1_event_types:
            return 1.0
    return 0.0


# --------------------------------------------------------------------------- #
# Main Feature Table Builder
# --------------------------------------------------------------------------- #
def build_feature_table(
    *,
    market: str,
    step_seconds: int,
    bars: Sequence[Mapping[str, Any]],
    target_as_of_times: Sequence[int] | None = None,
    feature_names: Sequence[str] = DEFAULT_FEATURES,
    didm_reports: Sequence[Mapping[str, Any]] = (),
    run_log_summary: Mapping[str, Any] | None = None,
    didm_v0_exports: Sequence[tuple[Mapping[str, Any], int]] = (),
    quantgpt_snapshots: Sequence[tuple[Mapping[str, Any], int]] = (),
    quantgpt_envelope_batches: Sequence[tuple[Sequence[Mapping[str, Any]], int]] = (),
    d1_series: Sequence[str] = DEFAULT_D1_SERIES,
    d3_event_types: Sequence[str] = DEFAULT_D3_EVENT_TYPES,
    q1_event_types: Sequence[str] = DEFAULT_Q1_EVENT_TYPES,
    d1_schedule_window_seconds: int = 3600,
    d3_cadence_seconds: int = 86400,
    q1_cadence_seconds: int = 86400,
    pinned_didm_v0: Mapping[str, str] | None = None,
    pinned_quantgpt_model: Mapping[str, Any] | None = None,
    strict_s4: bool = False,
    feature_builder_commit: str = "0" * 40,
) -> dict[str, Any]:
    """Build deterministic point-in-time feature rows at bar closes with zero imputation."""
    require(type(market) is str and MARKET_RE.fullmatch(market) is not None, "INVALID_MARKET")
    require(type(step_seconds) is int and 1 <= step_seconds <= 86400, "INVALID_STEP_SECONDS")
    require(1 <= len(feature_names) <= 8 and len(set(feature_names)) == len(feature_names), "INVALID_FEATURE_SET")
    require(all(f in ALL_FEATURES for f in feature_names), "UNKNOWN_FEATURE_NAME")
    require(type(feature_builder_commit) is str and HEX40_RE.fullmatch(feature_builder_commit) is not None, "INVALID_COMMIT_SHA")

    bars_by_end: dict[int, Mapping[str, Any]] = {}
    ordered_ends: list[int] = []
    for idx, bar in enumerate(bars):
        end = parse_epoch_int(bar["end"], error_code="INVALID_BAR_TIME")
        known_at = parse_epoch_int(bar["known_at"], low=end, error_code="INVALID_BAR_TIME")
        _ret = int(bar["return_bps"])
        require(-9999 <= _ret <= 100_000, "INVALID_RETURN_BPS")
        if idx > 0:
            require(end - ordered_ends[-1] == step_seconds, "MISSING_OR_DUPLICATE_BAR")
        ordered_ends.append(end)
        bars_by_end[end] = {"end": end, "known_at": known_at, "return_bps": _ret}
    require(len(ordered_ends) > 0, "EMPTY_PRICE_BARS")

    as_of_list = list(ordered_ends) if target_as_of_times is None else [int(t) for t in target_as_of_times]
    first_end = ordered_ends[0]
    require(all((t - first_end) % step_seconds == 0 for t in as_of_list), "AS_OF_OFF_BAR_GRID")

    needs_didm = any(f in feature_names for f in ("D1", "D2"))
    merged_didm = merge_didm_reports(didm_reports) if (didm_reports or needs_didm) else []

    slot_known_epoch: dict[int, int] = {}
    source_runs: Mapping[str, Sequence[Mapping[str, Any]]] = {}
    if run_log_summary is not None:
        raw_slots = run_log_summary.get("slot_known_epoch") or {}
        slot_known_epoch = {int(k): int(v) for k, v in raw_slots.items()}
        if not slot_known_epoch and "slot_known_at" in run_log_summary:
            slot_known_epoch = {rl.stamp_to_slot_epoch(k): int(v) for k, v in run_log_summary["slot_known_at"].items()}
        source_runs = run_log_summary.get("source_runs", {})

    d1_events = extract_d1_events(merged_didm, d1_series) if "D1" in feature_names else []
    d1_required_sources = sorted({s.split(":")[0] for s in d1_series}) if "D1" in feature_names else []

    pinned_scores, d3_receipt_times, unpinned_didm_count = (
        prepare_didm_v0_scores(didm_v0_exports, pinned_didm_v0=pinned_didm_v0, strict_s4=strict_s4)
        if ("D3" in feature_names or didm_v0_exports)
        else ([], [], 0)
    )

    q1_items: list[dict[str, Any]] = []
    q1_receipt_times: list[int] = []
    if "Q1" in feature_names or quantgpt_snapshots or quantgpt_envelope_batches:
        if quantgpt_snapshots:
            snaps = [s for s, _ in quantgpt_snapshots]
            recs = [r for _, r in quantgpt_snapshots]
            merged_q = qfb.merge_feature_snapshots(
                snaps,
                receipt_times=recs,
                pinned_producer="quantgpt",
                pinned_model=pinned_quantgpt_model,
            )
            q1_receipt_times.extend(recs)
            for m_item in merged_q["items"]:
                rec = m_item["record"]
                # Categorical event_type only; direction_probs never read
                q1_items.append({
                    "as_of": int(rec["as_of"]),
                    "known_at": int(m_item["known_at"]),
                    "event_type": rec["event_type"],
                })
        for batch_rows, rec_at in quantgpt_envelope_batches:
            q1_receipt_times.append(int(rec_at))
            extracted = qfb.extract_q1_events_from_envelopes(
                batch_rows,
                receipt_at=int(rec_at),
                pinned_model=pinned_quantgpt_model,
            )
            for ex in extracted:
                q1_items.append({
                    "as_of": int(ex["as_of"]),
                    "known_at": int(ex["known_at"]),
                    "event_type": ex["event_type"],
                })
        q1_receipt_times.sort()

    d3_type_set = frozenset(d3_event_types)
    q1_type_set = frozenset(q1_event_types)

    rows_out: list[dict[str, Any]] = []
    for as_of in as_of_list:
        p_feats = compute_price_features_at(bars_by_end, as_of, step_seconds)
        feat_map: dict[str, float | None] = {}
        for fname in feature_names:
            if fname in PRICE_FEATURES:
                feat_map[fname] = p_feats[fname]
            elif fname == "D1":
                if not all(_source_schedule_ok(source_runs, src, as_of, d1_schedule_window_seconds) for src in d1_required_sources):
                    feat_map["D1"] = None
                else:
                    hit = any((as_of - 86400) < float(ev["event_epoch"]) <= as_of for ev in d1_events)
                    feat_map["D1"] = 1.0 if hit else 0.0
            elif fname == "D2":
                feat_map["D2"] = compute_d2_at(merged_didm, slot_known_epoch, as_of)
            elif fname == "D3":
                feat_map["D3"] = compute_d3_at(
                    pinned_scores,
                    d3_receipt_times,
                    as_of,
                    d3_event_types=d3_type_set,
                    d3_cadence_seconds=d3_cadence_seconds,
                )
            elif fname == "Q1":
                feat_map["Q1"] = compute_q1_at(
                    q1_items,
                    q1_receipt_times,
                    as_of,
                    q1_event_types=q1_type_set,
                    q1_cadence_seconds=q1_cadence_seconds,
                )
        complete = all(feat_map[f] is not None for f in feature_names)
        rows_out.append({
            "as_of": as_of,
            "features": feat_map,
            "complete": complete,
        })

    n_complete = sum(1 for r in rows_out if r["complete"])
    body = {
        "format": FEATURE_TABLE_FORMAT,
        **RESEARCH_FLAGS,
        "market": market,
        "step_seconds": step_seconds,
        "feature_names": list(feature_names),
        "feature_definitions": {
            "d1_series": list(d1_series) if "D1" in feature_names else [],
            "d3_event_types": list(d3_event_types) if "D3" in feature_names else [],
            "q1_event_types": list(q1_event_types) if "Q1" in feature_names else [],
            "d1_schedule_window_seconds": d1_schedule_window_seconds,
            "d3_cadence_seconds": d3_cadence_seconds,
            "q1_cadence_seconds": q1_cadence_seconds,
        },
        "upstream_identities": {
            "didm_v0": dict(pinned_didm_v0) if pinned_didm_v0 is not None else None,
            "quantgpt": dict(pinned_quantgpt_model) if pinned_quantgpt_model is not None else None,
        },
        "feature_builder_commit": feature_builder_commit,
        "unpinned_didm_score_count": unpinned_didm_count,
        "d1_events": [
            {k: v for k, v in ev.items() if k != "event_epoch"} | {"event_epoch": math.ceil(ev["event_epoch"])}
            for ev in d1_events
        ],
        "row_count": len(rows_out),
        "complete_row_count": n_complete,
        "missing_row_count": len(rows_out) - n_complete,
        "rows": rows_out,
    }
    body["table_sha256"] = sha256_ascii(body)
    return body


def read_feature_table(path: Path | str, expected_sha256: str | None = None) -> dict[str, Any]:
    doc, _ = read_strict_json_file(path, max_bytes=64 * 1024 * 1024, path_error="FEATURE_TABLE_FILE", size_error="FEATURE_TABLE_SIZE")
    return verify_feature_table(doc, expected_sha256)


def verify_feature_table(doc: Any, expected_sha256: str | None = None) -> dict[str, Any]:
    require(type(doc) is dict and doc.get("format") == FEATURE_TABLE_FORMAT, "FEATURE_TABLE_FORMAT")
    for k, v in RESEARCH_FLAGS.items():
        require(doc.get(k) is v, "FEATURE_TABLE_FLAGS")
    recorded_sha = doc.get("table_sha256")
    require(type(recorded_sha) is str and HEX64_RE.fullmatch(recorded_sha) is not None, "FEATURE_TABLE_SHA256_MISMATCH")
    body = {k: v for k, v in doc.items() if k != "table_sha256"}
    require(sha256_ascii(body) == recorded_sha, "FEATURE_TABLE_SHA256_MISMATCH")
    if expected_sha256 is not None:
        require(recorded_sha == expected_sha256, "FEATURE_TABLE_SHA256_MISMATCH")
    return doc


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--history", type=Path, required=True, help="Price history JSON (bars list)")
    parser.add_argument("--market", required=True)
    parser.add_argument("--step-seconds", type=int, default=3600)
    parser.add_argument("--features", default="P1,P2,P3,P4,D2")
    parser.add_argument("--didm-report", action="append", default=[], type=Path)
    parser.add_argument("--run-log-dir", type=Path)
    parser.add_argument("--didm-score-model", help="Registered D3 model version")
    parser.add_argument("--didm-score-prompt-sha256", help="Registered D3 prompt SHA-256")
    parser.add_argument("--builder-commit", default="0" * 40)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)

    try:
        hist_doc, _ = read_strict_json_file(args.history, max_bytes=DEFAULT_MAX_BYTES)
        bars = hist_doc["bars"] if isinstance(hist_doc, dict) and "bars" in hist_doc else hist_doc
        reports = [read_strict_json_file(p, max_bytes=64 * 1024 * 1024)[0] for p in args.didm_report]
        log_sum = rl.summarize_run_log(args.run_log_dir) if args.run_log_dir is not None else None
        feats = [f.strip() for f in args.features.split(",") if f.strip()]
        exports = []
        pin = None
        if "D3" in feats:
            require(log_sum is not None and args.didm_score_model and args.didm_score_prompt_sha256
                    and HEX64_RE.fullmatch(args.didm_score_prompt_sha256), "DIDM_SCORE_PIN_AND_RECEIPTS_REQUIRED")
            pin = {"model_version": args.didm_score_model, "prompt_sha256": args.didm_score_prompt_sha256}
            for expected, receipt in log_sum["didm_export_receipts"].items():
                doc, raw = read_strict_json_file(Path(receipt["export_path"]), max_bytes=bridge.MAX_INPUT_BYTES)
                require(bridge.sha256(raw) == expected, "DIDM_EXPORT_RECEIPT_HASH_MISMATCH")
                exports.append((doc, receipt["received_at"]))
        table = build_feature_table(
            market=args.market,
            step_seconds=args.step_seconds,
            bars=bars,
            feature_names=feats,
            didm_v0_exports=exports,
            pinned_didm_v0=pin,
            didm_reports=reports,
            run_log_summary=log_sum,
            feature_builder_commit=args.builder_commit,
        )
        atomic_publish_json_ascii(args.output, table, max_bytes=64 * 1024 * 1024)
        print(canonical_ascii_str({
            "format": FEATURE_TABLE_FORMAT,
            **RESEARCH_FLAGS,
            "row_count": table["row_count"],
            "complete_row_count": table["complete_row_count"],
            "missing_row_count": table["missing_row_count"],
            "table_sha256": table["table_sha256"],
        }))
        return 0
    except StudyError as exc:
        reason = str(exc)
    except (OSError, ValueError, TypeError, KeyError):
        reason = "FEATURE_BUILD_REFUSED"
    print(canonical_ascii_str({**RESEARCH_FLAGS, "reason": reason}))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
