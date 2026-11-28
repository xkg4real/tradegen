"""Offline QuantGPT / QUANTGEN feature-snapshot & qgpt-env-v1 verification bridge.

Research only. Pure Python standard library; zero imports from quantgpt, quantgen,
core.compliance, core.odds, execution*, tools.owner, config, or main.
Never an order input, approval, or signed term.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
import json
import math
from pathlib import Path
import re
from typing import Any, Callable, Iterable, Mapping, Sequence

from tools.research._study_common import (
    DECIMAL_STR_RE,
    DEFAULT_MAX_BYTES,
    HEX64_RE,
    IDENT_RE,
    RESEARCH_FLAGS,
    StudyError,
    atomic_publish_json_ascii,
    canonical_ascii_str,
    canonical_utf8_bytes,
    canonical_utf8_str,
    check_json_tree,
    loads_strict_json,
    parse_decimal_str,
    parse_epoch_int,
    read_safe_bytes,
    read_strict_json_file,
    require,
    sha256_ascii,
    sha256_raw,
    sha256_utf8,
)


# =========================================================================== #
# Constants: Surface A (quantgen-feature-snapshot-v0) & Shared Taxonomies
# =========================================================================== #
FEATURE_SNAPSHOT_FORMAT = "quantgen-feature-snapshot-v0"
ALLOWED_PRODUCERS = frozenset({"quantgen-didm", "quantgpt"})
MAX_SNAPSHOT_BYTES = DEFAULT_MAX_BYTES  # 16 MiB
MAX_RECORDS = 50_000

SNAPSHOT_TOP_KEYS = frozenset({
    "format",
    "producer",
    "model",
    "generated_at",
    "records",
    "snapshot_sha256",
})
SNAPSHOT_MODEL_KEYS = frozenset({
    "name",
    "version",
    "sha256",
    "training_cutoff",
    "frozen_at",
})

# 16 core keys from QUANTGPT_TRADEGEN.md §9.2 + optional calibration_version
CORE_RECORD_KEYS = frozenset({
    "record_id",
    "source_id",
    "as_of",
    "issued_at",
    "published_at",
    "target_kind",
    "entity_id",
    "event_type",
    "direction_probs",
    "relevance_0_100",
    "novelty_0_100",
    "ess_like_0_100",
    "uncertainty_entropy",
    "p_credibility",
    "market_confirmation",
    "origin_cluster_id",
})
ALLOWED_RECORD_KEYS = CORE_RECORD_KEYS | {"calibration_version"}
FORBIDDEN_TEXT_KEYS = frozenset({"title", "body", "prompt", "article", "raw_text", "text"})

EVENT_TYPES = (
    "monetary_policy",
    "inflation",
    "employment",
    "growth",
    "fiscal",
    "trade_tariffs",
    "geopolitics",
    "election_policy",
    "earnings",
    "mergers_acquisitions",
    "management",
    "regulation_litigation",
    "supply_chain",
    "crypto_regulation_hack",
    "none",
)
EVENT_TYPE_SET = frozenset(EVENT_TYPES)
TARGET_KINDS = ("firm", "macro", "none")
MARKET_CONFIRMATIONS = ("CONFIRMED", "CONTRADICTED", "ALREADY_PRICED", "PENDING")


def ess_like(p_positive: float, p_negative: float) -> float:
    return 50.0 + 50.0 * (p_positive - p_negative)


def shannon_entropy(probabilities: Sequence[float]) -> float:
    return -sum(p * math.log(p) for p in probabilities if p > 0.0)


def quantgpt_model_sha256(
    model_id: str,
    adapter: str | None,
    prompt_version: str,
    decoding: Mapping[str, Any] | None = None,
) -> str:
    """Deterministic Regime A SHA-256 binding QuantGPT model triple + decoding settings."""
    require(type(model_id) is str and 0 < len(model_id.strip()) <= 200, "QGPT_MODEL_INVALID")
    require(adapter is None or (type(adapter) is str and 0 < len(adapter.strip()) <= 200), "QGPT_MODEL_INVALID")
    require(type(prompt_version) is str and 0 < len(prompt_version.strip()) <= 64, "QGPT_MODEL_INVALID")
    if decoding is not None:
        require(isinstance(decoding, Mapping), "QGPT_MODEL_INVALID")
        check_json_tree(dict(decoding), max_depth=8)
    payload = {
        "adapter": adapter,
        "decoding": None if decoding is None else dict(decoding),
        "id": model_id,
        "prompt_version": prompt_version,
    }
    return sha256_ascii(payload)


def verify_upstream_identity(observed: Mapping[str, Any], pinned: Mapping[str, Any]) -> None:
    """Enforce S4 upstream identity lock on QuantGPT or DIDM V0 metadata."""
    require(isinstance(observed, Mapping) and isinstance(pinned, Mapping), "S4_UPSTREAM_IDENTITY_CHANGED")
    for key, expected_val in pinned.items():
        if observed.get(key) != expected_val:
            raise StudyError("S4_UPSTREAM_IDENTITY_CHANGED")


# =========================================================================== #
# Surface A: quantgen-feature-snapshot-v0 Parser, Validator & Merger
# =========================================================================== #
def _finite_range(value: Any, low: float, high: float, code: str) -> float:
    require(type(value) in (int, float) and math.isfinite(value) and low <= value <= high, code)
    return float(value)


def _validate_direction_probs(probs: Any, code: str = "QGPT_PROBABILITIES_INVALID") -> list[float]:
    require(type(probs) is list and len(probs) == 3, code)
    if all(type(x) is str for x in probs):
        decs = [parse_decimal_str(x, Decimal("0"), Decimal("1"), error_code=code) for x in probs]
        require(sum(decs) == Decimal("1"), code)
        return [float(d) for d in decs]
    require(all(type(x) in (int, float) for x in probs), code)
    floats = [_finite_range(x, 0.0, 1.0, code) for x in probs]
    require(abs(sum(floats) - 1.0) <= 1e-6 and floats[0] + floats[1] <= 1.0 + 1e-9, code)
    return floats


def check_feature_record(record: Any, *, generated_at: int) -> dict[str, Any]:
    require(type(record) is dict, "QGPT_RECORD_SCHEMA_MISMATCH")
    keys = set(record)
    if keys & FORBIDDEN_TEXT_KEYS:
        raise StudyError("QGPT_FORBIDDEN_TEXT_FIELD")
    require(CORE_RECORD_KEYS <= keys <= ALLOWED_RECORD_KEYS, "QGPT_RECORD_SCHEMA_MISMATCH")

    for id_key in ("record_id", "source_id", "origin_cluster_id"):
        val = record[id_key]
        require(type(val) is str and IDENT_RE.fullmatch(val) is not None, "QGPT_RECORD_ID_INVALID")

    as_of = parse_epoch_int(record["as_of"], error_code="QGPT_RECORD_TIME_INVALID")
    issued_at = parse_epoch_int(record["issued_at"], error_code="QGPT_RECORD_TIME_INVALID")
    _published_at = parse_epoch_int(record["published_at"], error_code="QGPT_RECORD_TIME_INVALID")
    require(as_of <= issued_at <= generated_at, "QGPT_RECORD_TIME_ORDER")

    target_kind = record["target_kind"]
    require(target_kind in TARGET_KINDS, "QGPT_RECORD_TARGET_INVALID")
    entity_id = record["entity_id"]
    if target_kind == "none":
        require(entity_id is None, "QGPT_RECORD_TARGET_INVALID")
    else:
        require(type(entity_id) is str and IDENT_RE.fullmatch(entity_id) is not None, "QGPT_RECORD_TARGET_INVALID")

    require(type(record["event_type"]) is str and record["event_type"] in EVENT_TYPE_SET, "QGPT_RECORD_EVENT_INVALID")
    require(record["market_confirmation"] in MARKET_CONFIRMATIONS, "QGPT_RECORD_CONFIRMATION_INVALID")

    probs = _validate_direction_probs(record["direction_probs"])
    _finite_range(record["relevance_0_100"], 0.0, 100.0, "QGPT_RECORD_SCORE_RANGE")
    _finite_range(record["novelty_0_100"], 0.0, 100.0, "QGPT_RECORD_SCORE_RANGE")
    ess = _finite_range(record["ess_like_0_100"], 0.0, 100.0, "QGPT_RECORD_SCORE_RANGE")

    p_cred = record["p_credibility"]
    if type(p_cred) is str:
        parse_decimal_str(p_cred, Decimal("0"), Decimal("1"), error_code="QGPT_RECORD_SCORE_RANGE")
    else:
        _finite_range(p_cred, 0.0, 1.0, "QGPT_RECORD_SCORE_RANGE")

    require(abs(ess - ess_like(probs[0], probs[1])) <= 1e-6, "QGPT_ESS_MISMATCH")
    ent = _finite_range(record["uncertainty_entropy"], 0.0, 10.0, "QGPT_RECORD_SCORE_RANGE")
    require(abs(ent - shannon_entropy(probs)) <= 1e-6, "QGPT_ENTROPY_MISMATCH")

    if "calibration_version" in record and record["calibration_version"] is not None:
        cal = record["calibration_version"]
        require(type(cal) is str and IDENT_RE.fullmatch(cal) is not None, "QGPT_CALIBRATION_INVALID")

    return record


def check_feature_snapshot(snapshot: Any) -> dict[str, Any]:
    """Validate one quantgen-feature-snapshot-v0 object against QUANTGPT_TRADEGEN.md §9.2."""
    require(
        type(snapshot) is dict
        and set(snapshot) == SNAPSHOT_TOP_KEYS
        and snapshot["format"] == FEATURE_SNAPSHOT_FORMAT,
        "QGPT_SNAPSHOT_FORMAT",
    )
    require(snapshot["producer"] in ALLOWED_PRODUCERS, "QGPT_PRODUCER_INVALID")

    model = snapshot["model"]
    require(type(model) is dict and set(model) == SNAPSHOT_MODEL_KEYS, "QGPT_MODEL_FORMAT")
    for k in ("name", "version"):
        require(type(model[k]) is str and 0 < len(model[k].strip()) <= 128, "QGPT_MODEL_FORMAT")
    require(type(model["sha256"]) is str and HEX64_RE.fullmatch(model["sha256"]) is not None, "QGPT_MODEL_FORMAT")
    cutoff = parse_epoch_int(model["training_cutoff"], error_code="QGPT_MODEL_TIME_ORDER")
    frozen = parse_epoch_int(model["frozen_at"], error_code="QGPT_MODEL_TIME_ORDER")
    require(cutoff <= frozen, "QGPT_MODEL_TIME_ORDER")

    generated_at = parse_epoch_int(snapshot["generated_at"], error_code="QGPT_SNAPSHOT_TIME_INVALID")
    records = snapshot["records"]
    require(type(records) is list and len(records) <= MAX_RECORDS, "QGPT_SNAPSHOT_SIZE")

    seen_in_file: set[str] = set()
    for rec in records:
        check_feature_record(rec, generated_at=generated_at)
        rid = rec["record_id"]
        require(rid not in seen_in_file, "QGPT_DUPLICATE_RECORD_ID")
        seen_in_file.add(rid)

    body = {k: v for k, v in snapshot.items() if k != "snapshot_sha256"}
    expected_digest = sha256_ascii(body)
    require(
        type(snapshot["snapshot_sha256"]) is str
        and HEX64_RE.fullmatch(snapshot["snapshot_sha256"]) is not None
        and snapshot["snapshot_sha256"] == expected_digest,
        "QGPT_SNAPSHOT_SHA256_MISMATCH",
    )
    return snapshot


def seal_feature_snapshot(snapshot_without_hash: Mapping[str, Any]) -> dict[str, Any]:
    body = {k: v for k, v in snapshot_without_hash.items() if k != "snapshot_sha256"}
    out = dict(body)
    out["snapshot_sha256"] = sha256_ascii(body)
    return check_feature_snapshot(out)


def read_feature_snapshot(
    path: Path | str,
    expected_sha256: str | None = None,
    *,
    budget: int = MAX_RECORDS,
) -> dict[str, Any]:
    require(type(budget) is int and 0 <= budget <= MAX_RECORDS, "QGPT_SNAPSHOT_SIZE")
    if expected_sha256 is not None:
        require(type(expected_sha256) is str and HEX64_RE.fullmatch(expected_sha256) is not None, "QGPT_SNAPSHOT_SHA256_MISMATCH")
    parsed, _raw = read_strict_json_file(
        path,
        max_bytes=MAX_SNAPSHOT_BYTES,
        max_containers=2 * budget + 1024,
        max_colons=18 * budget + 1024,
        max_commas=22 * budget + 1024,
        path_error="QGPT_SNAPSHOT_FILE",
        size_error="QGPT_SNAPSHOT_SIZE",
    )
    snapshot = check_feature_snapshot(parsed)
    require(len(snapshot["records"]) <= budget, "QGPT_SNAPSHOT_SIZE")
    if expected_sha256 is not None:
        require(snapshot["snapshot_sha256"] == expected_sha256, "QGPT_SNAPSHOT_SHA256_MISMATCH")
    return snapshot


def merge_feature_snapshots(
    snapshots: Sequence[Mapping[str, Any]],
    *,
    receipt_times: Sequence[int | None] | None = None,
    pinned_producer: str | None = None,
    pinned_model: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Merge validated feature snapshots in receipt order with non-revision & known_at enforcement."""
    require(isinstance(snapshots, Sequence) and len(snapshots) > 0, "QGPT_NO_SNAPSHOT")
    if receipt_times is not None:
        require(len(receipt_times) == len(snapshots), "QGPT_RECEIPT_TIMES_MISMATCH")

    total = 0
    model_ref: dict[str, Any] | None = None
    producer_ref: str | None = None
    seen_records: dict[tuple[str, str, str], dict[str, Any]] = {}
    known_times: dict[tuple[str, str, str], int] = {}
    snapshot_hashes: list[str] = []

    for idx, snap_in in enumerate(snapshots):
        snap = check_feature_snapshot(dict(snap_in))
        total += len(snap["records"])
        require(total <= MAX_RECORDS, "QGPT_SNAPSHOT_SIZE")

        if pinned_producer is not None:
            require(snap["producer"] == pinned_producer, "S4_UPSTREAM_IDENTITY_CHANGED")
        if pinned_model is not None:
            verify_upstream_identity(snap["model"], pinned_model)

        if producer_ref is None:
            producer_ref = snap["producer"]
            model_ref = dict(snap["model"])
        else:
            require(snap["producer"] == producer_ref, "QGPT_PRODUCER_MIXED")
            if snap["model"] != model_ref:
                raise StudyError("S4_UPSTREAM_IDENTITY_CHANGED")

        receipt_at = None if receipt_times is None else receipt_times[idx]
        if receipt_at is not None:
            parse_epoch_int(receipt_at, error_code="QGPT_RECEIPT_TIME_INVALID")

        for rec in snap["records"]:
            key = (snap["model"]["sha256"], snap["producer"], rec["record_id"])
            eff_known = rec["issued_at"] if receipt_at is None else max(rec["issued_at"], receipt_at)
            if key in seen_records:
                require(seen_records[key] == rec, "QGPT_RECORD_REVISED")
                known_times[key] = min(known_times[key], eff_known)
            else:
                seen_records[key] = dict(rec)
                known_times[key] = eff_known
        snapshot_hashes.append(snap["snapshot_sha256"])

    merged_rows = []
    for key, rec in seen_records.items():
        merged_rows.append({
            "record": rec,
            "known_at": known_times[key],
        })
    merged_rows.sort(key=lambda item: (item["known_at"], item["record"]["as_of"], item["record"]["record_id"]))

    return {
        "format": "tradegen-quantgen-feature-merge-v1",
        **RESEARCH_FLAGS,
        "producer": producer_ref,
        "model": model_ref,
        "snapshot_sha256": snapshot_hashes,
        "record_count": len(merged_rows),
        "items": merged_rows,
    }


# =========================================================================== #
# Surface B: Pure-Stdlib Replication of QuantGPT qgpt-env-v1, Contracts,
# Policy Filter, Number/Citation/Leakage Re-Checkers, AttemptLedger & Scorer
# =========================================================================== #
ENVELOPE_VERSION = "qgpt-env-v1"
TASKS = ("T-EXPLAIN", "T-CARD", "T-QA", "T-PORT", "T-RESEARCH", "T-REPORT", "T-NEWS")
OWNER_ONLY_TASKS = ("T-RESEARCH",)
MODES = ("tool", "owner")
STATUSES = ("ok", "abstain", "blocked", "error")
POLICY_RULES = ("PF-1", "PF-2", "PF-3", "PF-4", "PF-5", "PF-6")
TEXT_POLICY_RULES = ("PF-1", "PF-2", "PF-3", "PF-4", "PF-5")
REASON_CODES = (
    "no_evidence",
    "number_not_in_payload",
    "citation_unknown",
    "after_as_of",
    "policy",
    "no_task_code",
    "task_not_allowed",
    "disabled",
    "invalid_input",
    "invalid_output",
    "backend",
    "truncated",
)
STATUS_REASONS: dict[str, tuple[str, ...]] = {
    "abstain": ("no_evidence", "number_not_in_payload", "citation_unknown", "after_as_of"),
    "blocked": ("policy", "no_task_code", "task_not_allowed", "disabled"),
    "error": ("invalid_input", "invalid_output", "backend", "truncated"),
}

QSS_VERSION = "qss-v0"
QSS_KINDS = ("strategy", "distribution", "model")
QSS_VERDICTS = ("PASS", "REVISE", "REJECT")
QSS_STAGES = ("draft", "recorded")
NONFINITE_KEY = "$nonfinite"
_NONFINITE_MAP = {"NaN": math.nan, "+Infinity": math.inf, "-Infinity": -math.inf}
CARD_KEYS = (
    "card_id", "kind", "hypothesis", "rules", "universe", "data", "costs", "protocol", "trials",
    "seed", "stats", "tests", "decision", "decision_reason", "revise_target", "lines",
    "decay_haircut", "created", "author", "results_file", "results_md5", "citations",
)

T_NEWS_MODEL_FIELDS = ("target_kind", "entity_id", "relevance_0_100", "event_type", "direction_probs")
T_NEWS_COMPUTED_FIELDS = ("ess_like_0_100", "uncertainty_entropy")
T_NEWS_HOST_ONLY_FIELDS = ("novelty_0_100", "origin_cluster_id", "p_credibility", "market_confirmation", "received_at")
T_NEWS_COPIED_FIELDS = ("record_id", "source_id", "published_at", "model_version", "prompt_sha256")
T_NEWS_RECORD_FIELDS = (
    "record_id", "source_id", "target_kind", "entity_id", "published_at", "received_at",
    "relevance_0_100", "ess_like_0_100", "novelty_0_100", "origin_cluster_id", "event_type",
    "direction_probs", "uncertainty_entropy", "p_credibility", "market_confirmation",
    "model_version", "prompt_sha256",
)


class SchemaError(StudyError):
    """Structural or contract violation inside qgpt-env-v1 or its task payloads."""


def _s_fail(path: str, message: str) -> None:
    raise SchemaError(f"{path or '$'}: {message}")


def _s_str(
    value: Any,
    path: str,
    *,
    min_len: int = 1,
    max_len: int = 20000,
    pattern: re.Pattern[str] | None = None,
    enum: tuple[str, ...] | None = None,
) -> str:
    if type(value) is not str:
        _s_fail(path, "must be a string")
    if enum is not None and value not in enum:
        _s_fail(path, f"must be one of {list(enum)}")
    if not min_len <= len(value) <= max_len:
        _s_fail(path, f"length must be {min_len}..{max_len}")
    if min_len > 0 and not value.strip():
        _s_fail(path, "must not be blank")
    if pattern is not None and pattern.fullmatch(value) is None:
        _s_fail(path, "has the wrong format")
    return value


def _s_int(value: Any, path: str, *, lo: int | None = None, hi: int | None = None) -> int:
    if type(value) is not int:
        _s_fail(path, "must be an integer")
    if (lo is not None and value < lo) or (hi is not None and value > hi):
        _s_fail(path, f"must be in [{lo}, {hi}]")
    return value


def _s_num(value: Any, path: str, *, lo: float | None = None, hi: float | None = None) -> float:
    if type(value) not in (int, float):
        _s_fail(path, "must be a number")
    if not math.isfinite(value):
        _s_fail(path, "must be finite")
    if (lo is not None and value < lo) or (hi is not None and value > hi):
        _s_fail(path, f"must be in [{lo}, {hi}]")
    return float(value)


def _s_bool(value: Any, path: str) -> bool:
    if type(value) is not bool:
        _s_fail(path, "must be true or false")
    return value


def _s_json_value(value: Any, path: str, *, max_depth: int = 12, max_string: int = 20000, depth: int = 0) -> None:
    if depth > max_depth:
        _s_fail(path, "is nested too deeply")
    if value is None or type(value) is bool:
        return
    if type(value) in (int, float):
        if not math.isfinite(value):
            _s_fail(path, "must be finite")
        return
    if type(value) is str:
        if len(value) > max_string:
            _s_fail(path, "string is too long")
        return
    if type(value) is list:
        for i, el in enumerate(value):
            _s_json_value(el, f"{path}[{i}]", max_depth=max_depth, max_string=max_string, depth=depth + 1)
        return
    if type(value) is dict:
        for k, el in value.items():
            if type(k) is not str:
                _s_fail(path, "keys must be strings")
            _s_json_value(el, f"{path}.{k}", max_depth=max_depth, max_string=max_string, depth=depth + 1)
        return
    _s_fail(path, "is not a JSON value")


def _s_json_object(value: Any, path: str, *, max_depth: int = 12) -> None:
    if type(value) is not dict:
        _s_fail(path, "must be an object")
    _s_json_value(value, path, max_depth=max_depth)


def _s_check_keys(value: Any, path: str, required: set[str], optional: set[str] | None = None) -> dict[str, Any]:
    if type(value) is not dict:
        _s_fail(path, "must be an object")
    allowed = required | (optional or set())
    for req in required:
        if req not in value:
            _s_fail(f"{path}.{req}", "is missing")
    for k in value:
        if type(k) is not str:
            _s_fail(path, "keys must be strings")
        if k not in allowed:
            _s_fail(f"{path}.{k}", "is not an allowed field")
    return value


def parse_qgpt_as_of(value: str, path: str = "as_of") -> datetime:
    """Parse YYYY-MM-DD (end of day) or ISO 8601 into naive-UTC-comparable datetime."""
    if type(value) is not str:
        _s_fail(path, "must be an ISO date string")
    try:
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            d = date.fromisoformat(value)
            return datetime(d.year, d.month, d.day, 23, 59, 59)
        ts = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        raise SchemaError(f"{path}: is not an ISO 8601 date") from None
    if ts.tzinfo is not None:
        offset = ts.utcoffset()
        assert offset is not None
        ts = (ts - offset).replace(tzinfo=None)
    return ts


# -- QSS v0 & T-CARD ------------------------------------------------------- #
_CARD_ID_RE = re.compile(r"[A-Za-z][A-Za-z0-9_]{1,63}\Z")
_MD5_RE = re.compile(r"[0-9a-f]{32}\Z")


def validate_qss(doc: Any, stage: str | None = None, path: str = "$") -> dict[str, Any]:
    if type(doc) is not dict:
        _s_fail(path, "must be an object")
    actual = doc.get("stage")
    if actual not in QSS_STAGES:
        _s_fail(f"{path}.stage", f"must be one of {list(QSS_STAGES)}")
    if stage is not None and actual != stage:
        _s_fail(f"{path}.stage", f"must be {stage!r}")

    common_keys = {
        "qss_version", "stage", "card_id", "kind", "hypothesis",
        "rules", "market", "data", "costs", "protocol", "trials", "seed",
    }
    if actual == "draft":
        _s_check_keys(doc, path, common_keys)
    else:
        _s_check_keys(doc, path, common_keys | {"evidence", "decision", "decay_haircut", "provenance"})

    if doc["qss_version"] != QSS_VERSION:
        _s_fail(f"{path}.qss_version", f"must be {QSS_VERSION!r}")
    _s_str(doc["card_id"], f"{path}.card_id", max_len=64, pattern=_CARD_ID_RE)
    _s_str(doc["kind"], f"{path}.kind", enum=QSS_KINDS)
    _s_str(doc["hypothesis"], f"{path}.hypothesis", max_len=2000)
    for obj_key in ("rules", "market", "data", "costs", "protocol"):
        _s_json_object(doc[obj_key], f"{path}.{obj_key}")
    _s_int(doc["seed"], f"{path}.seed", lo=0)

    trials = doc["trials"]
    if actual == "draft":
        _s_check_keys(trials, f"{path}.trials", {"n_planned"})
        _s_int(trials["n_planned"], f"{path}.trials.n_planned", lo=1)
    else:
        _s_check_keys(trials, f"{path}.trials", {"n_planned", "n_total", "ledger"})
        n_planned = _s_int(trials["n_planned"], f"{path}.trials.n_planned", lo=1)
        n_total = _s_int(trials["n_total"], f"{path}.trials.n_total", lo=1)
        if type(trials["ledger"]) is not list or len(trials["ledger"]) > 1000:
            _s_fail(f"{path}.trials.ledger", "must be an array of 0..1000 items")
        for i, entry in enumerate(trials["ledger"]):
            _s_str(entry, f"{path}.trials.ledger[{i}]", max_len=2000)
        if n_total < n_planned:
            _s_fail(f"{path}.trials.n_total", "must be at least n_planned")

        ev = _s_check_keys(doc["evidence"], f"{path}.evidence", {"stats", "tests", "lines", "results_file", "results_md5"})
        _s_json_object(ev["stats"], f"{path}.evidence.stats")
        _s_json_object(ev["tests"], f"{path}.evidence.tests")
        if type(ev["lines"]) is not list or len(ev["lines"]) > 1000:
            _s_fail(f"{path}.evidence.lines", "must be an array of 0..1000 items")
        for i, ln in enumerate(ev["lines"]):
            _s_str(ln, f"{path}.evidence.lines[{i}]", max_len=4000)
        _s_str(ev["results_file"], f"{path}.evidence.results_file", max_len=400)
        _s_str(ev["results_md5"], f"{path}.evidence.results_md5", max_len=32, pattern=_MD5_RE)

        dec = _s_check_keys(doc["decision"], f"{path}.decision", {"verdict", "reason", "revise_target"})
        _s_str(dec["verdict"], f"{path}.decision.verdict", enum=QSS_VERDICTS)
        _s_str(dec["reason"], f"{path}.decision.reason", max_len=2000)
        if dec["revise_target"] is not None:
            _s_str(dec["revise_target"], f"{path}.decision.revise_target", max_len=2000)

        hc = _s_check_keys(doc["decay_haircut"], f"{path}.decay_haircut", {"factor", "source"})
        _s_num(hc["factor"], f"{path}.decay_haircut.factor", lo=0.0, hi=1.0)
        _s_str(hc["source"], f"{path}.decay_haircut.source", max_len=400)

        prov = _s_check_keys(doc["provenance"], f"{path}.provenance", {"created", "author", "citations"})
        parse_qgpt_as_of(prov["created"], f"{path}.provenance.created")
        _s_str(prov["author"], f"{path}.provenance.author", max_len=200)
        if type(prov["citations"]) is not list or len(prov["citations"]) > 1000:
            _s_fail(f"{path}.provenance.citations", "must be an array of 0..1000 items")
        for i, cit in enumerate(prov["citations"]):
            _s_str(cit, f"{path}.provenance.citations[{i}]", max_len=400)

        if doc["kind"] == "strategy" and dec["verdict"] == "PASS":
            for gate_key in ("dsr", "pbo"):
                if gate_key not in ev["tests"]:
                    _s_fail(f"{path}.evidence.tests.{gate_key}", "is required on a PASS strategy card")
    return doc


# -- T-NEWS & All 7 Task Output Contracts ---------------------------------- #
def validate_t_news_output(value: Any, path: str = "$") -> dict[str, Any]:
    _s_check_keys(value, path, {"judgments"})
    judgments = value["judgments"]
    if type(judgments) is not list or not 1 <= len(judgments) <= 50:
        _s_fail(f"{path}.judgments", "must hold 1..50 items")
    seen: set[tuple[str, str | None]] = set()
    for i, j in enumerate(judgments):
        here = f"{path}.judgments[{i}]"
        _s_check_keys(j, here, set(T_NEWS_MODEL_FIELDS))
        tk = _s_str(j["target_kind"], f"{here}.target_kind", enum=TARGET_KINDS)
        eid = j["entity_id"]
        if eid is not None:
            _s_str(eid, f"{here}.entity_id", max_len=128, pattern=IDENT_RE)
        if (tk == "none") != (eid is None):
            _s_fail(f"{here}.entity_id", "is null exactly when target_kind is none")
        _s_num(j["relevance_0_100"], f"{here}.relevance_0_100", lo=0.0, hi=100.0)
        _s_str(j["event_type"], f"{here}.event_type", enum=EVENT_TYPES)
        probs = j["direction_probs"]
        if type(probs) is not list or len(probs) != 3:
            _s_fail(f"{here}.direction_probs", "must hold 3..3 items")
        fprobs = [_s_num(p, f"{here}.direction_probs[{k}]", lo=0.0, hi=1.0) for k, p in enumerate(probs)]
        if abs(sum(fprobs) - 1.0) > 1e-6:
            _s_fail(f"{here}.direction_probs", "must sum to 1")
        key = (tk, eid)
        if key in seen:
            _s_fail(here, "the same target is judged twice")
        seen.add(key)
    return value


def check_t_news_against_input(body: Mapping[str, Any], payload: Mapping[str, Any]) -> None:
    if type(payload) is not dict or type(payload.get("candidates")) is not list:
        _s_fail("$.candidates", "must be an array")
    offered = {(c["target_kind"], c["entity_id"]) for c in payload["candidates"] if isinstance(c, Mapping)}
    for i, judgment in enumerate(body["judgments"]):
        key = (judgment["target_kind"], judgment["entity_id"])
        if key[0] != "none" and key not in offered:
            _s_fail(f"$.judgments[{i}].entity_id", "is not one of the candidates that were sent")


def assemble_score_record(judgment: Mapping[str, Any], host_fields: Mapping[str, Any]) -> dict[str, Any]:
    """Assemble one model T-NEWS judgment + host fields into a didm-score-v0 record."""
    validate_t_news_output({"judgments": [dict(judgment)]}, "$")
    req_host = set(T_NEWS_COPIED_FIELDS + T_NEWS_HOST_ONLY_FIELDS)
    _s_check_keys(dict(host_fields), "$host", req_host)
    for id_k in ("record_id", "source_id", "origin_cluster_id"):
        _s_str(host_fields[id_k], f"$host.{id_k}", max_len=128, pattern=IDENT_RE)
    for ts_k in ("published_at", "received_at"):
        val = _s_str(host_fields[ts_k], f"$host.{ts_k}", max_len=40)
        try:
            dt = datetime.fromisoformat(val.replace("Z", "+00:00"))
        except ValueError:
            raise SchemaError(f"{ts_k} is not ISO 8601") from None
        if dt.tzinfo is None:
            raise SchemaError(f"{ts_k} must carry a timezone")
    _s_num(host_fields["novelty_0_100"], "$host.novelty_0_100", lo=0.0, hi=100.0)
    _s_num(host_fields["p_credibility"], "$host.p_credibility", lo=0.0, hi=1.0)
    _s_str(host_fields["market_confirmation"], "$host.market_confirmation", enum=MARKET_CONFIRMATIONS)
    _s_str(host_fields["model_version"], "$host.model_version", max_len=200)
    _s_str(host_fields["prompt_sha256"], "$host.prompt_sha256", max_len=64, pattern=HEX64_RE)

    probs = [float(p) for p in judgment["direction_probs"]]
    values = {
        **{name: host_fields[name] for name in T_NEWS_COPIED_FIELDS + T_NEWS_HOST_ONLY_FIELDS},
        "target_kind": judgment["target_kind"],
        "entity_id": judgment["entity_id"],
        "relevance_0_100": judgment["relevance_0_100"],
        "event_type": judgment["event_type"],
        "direction_probs": probs,
        "ess_like_0_100": ess_like(probs[0], probs[1]),
        "uncertainty_entropy": shannon_entropy(probs),
    }
    record = {name: values[name] for name in T_NEWS_RECORD_FIELDS}
    record["schema_version"] = "didm-score-v0"
    return record


def _check_lines(val: Any, path: str, *, min_len: int = 0, max_len: int = 12, line_max: int = 600) -> None:
    if type(val) is not list or not min_len <= len(val) <= max_len:
        _s_fail(path, f"must hold {min_len}..{max_len} items")
    for i, item in enumerate(val):
        _s_str(item, f"{path}[{i}]", max_len=line_max)


def validate_task_output(task: str, body: Any, path: str = "$.body", *, payload: Any = None) -> Any:
    if task == "T-NEWS":
        validate_t_news_output(body, path)
        if payload is not None:
            check_t_news_against_input(body, payload)
        return body
    if task == "T-CARD":
        _s_check_keys(body, path, {"card", "open_fields"}, {"assumptions"})
        _s_json_object(body["card"], f"{path}.card")
        of = body["open_fields"]
        if type(of) is not list or len(of) > 20:
            _s_fail(f"{path}.open_fields", "must hold 0..20 items")
        for i, item in enumerate(of):
            _s_str(item, f"{path}.open_fields[{i}]", max_len=80)
        if len(set(of)) != len(of):
            _s_fail(f"{path}.open_fields", "items must be unique")
        if "assumptions" in body:
            _check_lines(body["assumptions"], f"{path}.assumptions")
        validate_qss(body["card"], stage="draft", path=f"{path}.card")
        return body
    if task == "T-EXPLAIN":
        _s_check_keys(body, path, {"summary", "points"}, {"caveats"})
        _s_str(body["summary"], f"{path}.summary", max_len=4000)
        _check_lines(body["points"], f"{path}.points", min_len=1, max_len=12)
        if "caveats" in body:
            _check_lines(body["caveats"], f"{path}.caveats")
        return body
    if task == "T-QA":
        _s_check_keys(body, path, {"answer"}, {"caveats"})
        _s_str(body["answer"], f"{path}.answer", max_len=4000)
        if "caveats" in body:
            _check_lines(body["caveats"], f"{path}.caveats")
        return body
    if task == "T-PORT":
        _s_check_keys(body, path, {"summary", "observations"}, {"caveats"})
        _s_str(body["summary"], f"{path}.summary", max_len=4000)
        _check_lines(body["observations"], f"{path}.observations", min_len=1, max_len=12)
        if "caveats" in body:
            _check_lines(body["caveats"], f"{path}.caveats")
        return body
    if task == "T-RESEARCH":
        _s_check_keys(body, path, {"prereg"}, {"prior_work"})
        pr = _s_check_keys(
            body["prereg"],
            f"{path}.prereg",
            {"title", "hypothesis", "null_hypothesis", "data", "primary_metric", "test", "n_trials_planned", "stop_rule", "as_of"},
        )
        _s_str(pr["title"], f"{path}.prereg.title", max_len=600)
        _s_str(pr["hypothesis"], f"{path}.prereg.hypothesis", max_len=2000)
        _s_str(pr["null_hypothesis"], f"{path}.prereg.null_hypothesis", max_len=2000)
        d = _s_check_keys(pr["data"], f"{path}.prereg.data", {"sources", "start", "end"})
        _check_lines(d["sources"], f"{path}.prereg.data.sources", min_len=1, max_len=20)
        s_dt = parse_qgpt_as_of(d["start"], f"{path}.prereg.data.start")
        e_dt = parse_qgpt_as_of(d["end"], f"{path}.prereg.data.end")
        if s_dt > e_dt:
            _s_fail(f"{path}.prereg.data", "start is after end")
        _s_str(pr["primary_metric"], f"{path}.prereg.primary_metric", max_len=600)
        _s_str(pr["test"], f"{path}.prereg.test", max_len=600)
        _s_int(pr["n_trials_planned"], f"{path}.prereg.n_trials_planned", lo=1, hi=100000)
        _s_str(pr["stop_rule"], f"{path}.prereg.stop_rule", max_len=600)
        parse_qgpt_as_of(pr["as_of"], f"{path}.prereg.as_of")
        if "prior_work" in body:
            _check_lines(body["prior_work"], f"{path}.prior_work")
        return body
    if task == "T-REPORT":
        _s_check_keys(body, path, {"summary", "sections"}, {"caveats"})
        _s_str(body["summary"], f"{path}.summary", max_len=4000)
        secs = body["sections"]
        if type(secs) is not list or not 1 <= len(secs) <= 12:
            _s_fail(f"{path}.sections", "must hold 1..12 items")
        for i, sec in enumerate(secs):
            _s_check_keys(sec, f"{path}.sections[{i}]", {"title", "text"})
            _s_str(sec["title"], f"{path}.sections[{i}].title", max_len=600)
            _s_str(sec["text"], f"{path}.sections[{i}].text", max_len=4000)
        if "caveats" in body:
            _check_lines(body["caveats"], f"{path}.caveats")
        return body
    raise SchemaError(f"unknown task code: {task!r}")


# -- Common Envelope qgpt-env-v1 ------------------------------------------- #
_SOURCE_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:\-/]*\Z")


def request_sha256(
    task: str,
    mode: str,
    payload: Any,
    model_id: str,
    adapter: str | None,
    prompt_version: str,
) -> str:
    """Regime B (UTF-8 canonical JSON) request hash matching QuantGPT envelope.py."""
    return sha256_utf8({
        "task": task,
        "mode": mode,
        "input": payload,
        "model": model_id,
        "adapter": adapter,
        "prompt_version": prompt_version,
    })


def validate_envelope(
    env: Any,
    body_spec: Callable[[Any, str], Any] | None = None,
    *,
    validate_task_contract: bool = False,
) -> dict[str, Any]:
    req_keys = {
        "envelope_version", "task", "mode", "status", "body",
        "numbers", "citations", "policy", "model", "label_ko",
        "latency_ms", "request_sha256",
    }
    _s_check_keys(env, "$", req_keys, {"reason_code"})
    if env["envelope_version"] != ENVELOPE_VERSION:
        _s_fail("$.envelope_version", f"must be {ENVELOPE_VERSION!r}")
    task = env["task"]
    if task is not None:
        _s_str(task, "$.task", enum=TASKS)
    mode = _s_str(env["mode"], "$.mode", enum=MODES)
    status = _s_str(env["status"], "$.status", enum=STATUSES)
    if env["body"] is not None:
        _s_json_object(env["body"], "$.body")

    if type(env["numbers"]) is not list or len(env["numbers"]) > 1000:
        _s_fail("$.numbers", "must hold 0..1000 items")
    for i, num in enumerate(env["numbers"]):
        _s_check_keys(num, f"$.numbers[{i}]", {"text", "found_in_payload"})
        _s_str(num["text"], f"$.numbers[{i}].text", max_len=80)
        _s_bool(num["found_in_payload"], f"$.numbers[{i}].found_in_payload")

    if type(env["citations"]) is not list or len(env["citations"]) > 1000:
        _s_fail("$.citations", "must hold 0..1000 items")
    for i, cit in enumerate(env["citations"]):
        _s_check_keys(cit, f"$.citations[{i}]", {"source_id", "as_of"})
        _s_str(cit["source_id"], f"$.citations[{i}].source_id", max_len=128, pattern=_SOURCE_ID_RE)
        parse_qgpt_as_of(cit["as_of"], f"$.citations[{i}].as_of")

    pol = _s_check_keys(env["policy"], "$.policy", {"violations", "rules_version"})
    if type(pol["violations"]) is not list or len(pol["violations"]) > 1000:
        _s_fail("$.policy.violations", "must be an array")
    for i, v in enumerate(pol["violations"]):
        _s_str(v, f"$.policy.violations[{i}]", enum=POLICY_RULES)
    if len(set(pol["violations"])) != len(pol["violations"]):
        _s_fail("$.policy.violations", "items must be unique")
    _s_str(pol["rules_version"], "$.policy.rules_version", max_len=64)

    mdl = _s_check_keys(env["model"], "$.model", {"id", "adapter", "prompt_version"})
    _s_str(mdl["id"], "$.model.id", max_len=200)
    if mdl["adapter"] is not None:
        _s_str(mdl["adapter"], "$.model.adapter", max_len=200)
    _s_str(mdl["prompt_version"], "$.model.prompt_version", max_len=64)

    _s_str(env["label_ko"], "$.label_ko", max_len=400)
    _s_int(env["latency_ms"], "$.latency_ms", lo=0)
    _s_str(env["request_sha256"], "$.request_sha256", max_len=64, pattern=HEX64_RE)
    if "reason_code" in env:
        _s_str(env["reason_code"], "$.reason_code", enum=REASON_CODES)

    if task is None and (status != "blocked" or env.get("reason_code") != "no_task_code"):
        raise SchemaError("$.task: is null only when a request without a task code was blocked")
    if task in OWNER_ONLY_TASKS and mode != "owner" and status == "ok":
        raise SchemaError(f"$.task: {task} is not offered in {mode} mode")

    if status == "ok":
        if env["body"] is None:
            raise SchemaError("$.body: is required when status is ok")
        if "reason_code" in env:
            raise SchemaError("$.reason_code: is not allowed when status is ok")
        if mode == "tool":
            if pol["violations"]:
                raise SchemaError("$.policy.violations: an ok envelope in tool mode has none")
            if any(not n["found_in_payload"] for n in env["numbers"]):
                raise SchemaError("$.numbers: an ok envelope in tool mode cites only numbers found in the payload")
        if body_spec is not None:
            body_spec(env["body"], "$.body")
        elif validate_task_contract and task is not None:
            validate_task_output(task, env["body"], "$.body")
    else:
        if env["body"] is not None:
            raise SchemaError(f"$.body: must be null when status is {status}")
        reason = env.get("reason_code")
        if reason is not None and reason not in STATUS_REASONS[status]:
            raise SchemaError(f"$.reason_code: {reason} does not belong to status {status}")
    return env


def extract_ok_body(env: Any, *, validate_task_contract: bool = True) -> dict[str, Any] | None:
    """Return body ONLY when env is a valid ok envelope; otherwise None."""
    if not isinstance(env, dict):
        return None
    try:
        validate_envelope(env, validate_task_contract=validate_task_contract)
    except (SchemaError, StudyError):
        return None
    return env["body"] if env["status"] == "ok" else None


display_body = extract_ok_body


# -- Policy Filter PF-1..PF-6 ---------------------------------------------- #
@dataclass(frozen=True)
class PolicyRules:
    version: str
    patterns: Mapping[str, tuple[re.Pattern[str], ...]]


@dataclass(frozen=True)
class PolicyDecision:
    violations: tuple[str, ...]
    blocked: bool
    rules_version: str

    def as_envelope(self) -> dict[str, Any]:
        return {"violations": list(self.violations), "rules_version": self.rules_version}


def load_policy_rules(data: Any) -> PolicyRules:
    _s_check_keys(data, "$", {"version", "rules"})
    version = _s_str(data["version"], "$.version", max_len=64, pattern=re.compile(r"[A-Za-z0-9][A-Za-z0-9_.\-]*\Z"))
    rules_obj = data["rules"]
    if type(rules_obj) is not dict or not set(rules_obj) <= set(TEXT_POLICY_RULES):
        _s_fail("$.rules", "invalid rules mapping")
    compiled: dict[str, tuple[re.Pattern[str], ...]] = {}
    for rule in TEXT_POLICY_RULES:
        sources = rules_obj.get(rule)
        if type(sources) is not list or not 1 <= len(sources) <= 500:
            _s_fail(f"$.rules.{rule}", "needs 1..500 patterns")
        pats: list[re.Pattern[str]] = []
        for idx, src in enumerate(sources):
            _s_str(src, f"$.rules.{rule}[{idx}]", max_len=400)
            try:
                pat = re.compile(src, re.IGNORECASE)
            except re.error as exc:
                raise SchemaError(f"$.rules.{rule}: bad pattern ({exc})") from None
            if pat.search(""):
                raise SchemaError(f"$.rules.{rule}: a pattern matches empty text")
            pats.append(pat)
        compiled[rule] = tuple(pats)
    return PolicyRules(version=version, patterns=compiled)


SEED_POLICY_RULES = load_policy_rules({
    "version": "pf-seed-0",
    "rules": {
        "PF-1": [
            r"(매수|매도|보유|손절|익절)\s*(하세요|하십시오|하시기 바랍니다|를 권합니다|를 추천)",
            r"\byou should (buy|sell|hold)\b",
            r"\b(buy|sell) (it |this |them )?now\b",
        ],
        "PF-2": [
            r"(지금|오늘|이번 주|내일)[^.\n]{0,30}(\d{6}|[A-Z]{2,5}\b)[^.\n]{0,30}(사야|팔아야|들어갈 때|매수 적기|매도 적기)",
            r"\b(now|today|this week) is (a good|the right) time to (buy|sell) [A-Z]{2,5}\b",
        ],
        "PF-3": [
            r"(당사|저희|QUANTGEN)(가|는|의)?\s*(권장|추천)\s*(값|설정|비중)",
            r"\bour recommended (value|setting|allocation)\b",
        ],
        "PF-4": [
            r"(오를|상승할|하락할|내릴|도달할) 것(입니다|이 확실)",
            r"\bwill (rise|fall|reach|hit)\b[^.\n]{0,40}\b(by|to)\b",
            r"목표가",
        ],
        "PF-5": [
            r"(수익|원금)(을|이)?\s*보장",
            r"\bguaranteed (return|profit)s?\b",
            r"무조건 (수익|오릅니다)",
        ],
    },
})


def scan_policy(text: str, rules: PolicyRules = SEED_POLICY_RULES) -> tuple[str, ...]:
    src = text or ""
    return tuple(rule for rule in TEXT_POLICY_RULES if any(p.search(src) for p in rules.patterns[rule]))


def decide_policy(text: str, mode: str, rules: PolicyRules = SEED_POLICY_RULES) -> PolicyDecision:
    require(mode in MODES, "QGPT_MODE_INVALID")
    violations = scan_policy(text, rules)
    return PolicyDecision(violations, bool(violations) and mode == "tool", rules.version)


# -- Number Check (%/bp scaling, date/time/range masking) ------------------ #
COARSE_SIGNIFICANT_DIGITS = 2
_MARKER_PREFIXES = ("NaN:", "+inf:", "-inf:")
_NUMBER_RE = re.compile(r"\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?")
_WORD_RE = re.compile(r"[A-Za-z0-9_]")
_MONTH_NAMES_RE = (
    "January|February|March|April|May|June|July|August|September|October|November|December|"
    "Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sept|Sep|Oct|Nov|Dec"
)
_ISO_DATE_RE = r"\d{4}-\d{2}-\d{2}(?:[T ]\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:Z|[+-]\d{2}:?\d{2})?)?"
_NUM_MASKS = tuple(re.compile(p) for p in (
    _ISO_DATE_RE,
    r"\d{4}/\d{1,2}/\d{1,2}",
    r"\b\d{1,2}/\d{1,2}/\d{2,4}\b",
    r"\d{4}\.\s?\d{1,2}\.\s?\d{1,2}\.?",
    r"\b\d{1,2}:\d{2}(?::\d{2})?\b",
    r"\d{4}년\s*\d{1,2}월(?:\s*\d{1,2}일)?",
    r"\d{1,2}월(?:\s*\d{1,2}일)?",
    rf"\b\d{{1,2}}(?:st|nd|rd|th)?\s+(?:{_MONTH_NAMES_RE})\.?(?:\s+\d{{4}})?\b",
    rf"\b(?:{_MONTH_NAMES_RE})\.?\s+\d{{1,2}}(?!\d)(?:,\s*\d{{4}})?",
    rf"\b(?:{_MONTH_NAMES_RE})\.?\s+\d{{4}}\b",
))
_UNITS = (
    ("percentage points", "%"), ("percentage point", "%"), ("퍼센트포인트", "%"),
    ("베이시스 포인트", "bp"), ("베이시스포인트", "bp"),
    ("basis points", "bp"), ("basis point", "bp"), ("per cent", "%"),
    ("percent", "%"), ("퍼센트", "%"), ("pct", "%"), ("bps", "bp"),
    ("%p", "%"), ("pp", "%"), ("bp", "bp"),
    ("%", "%"), ("×", "x"), ("x", "x"), ("배", "x"),
)
_RANGE_UNIT = "|".join(re.escape(w) for w, _ in _UNITS)
_RANGE_RE = re.compile(
    rf"(?<![A-Za-z0-9_.])[+−-]?(?:{_NUMBER_RE.pattern})(?:\s*(?:{_RANGE_UNIT}))?"
    rf"\s*(?:[-–~\uff5e]|\bto\b)\s*[+−-]?(?:{_NUMBER_RE.pattern})(?:\s*(?:{_RANGE_UNIT}))?",
    re.I,
)
_SCIENTIFIC_RE = re.compile(
    rf"(?<![A-Za-z0-9_.])(?:{_NUMBER_RE.pattern})\s*"
    r"(?:[eE][+−-]?\d+|[×x]\s*10(?:[⁺⁻]?[⁰¹²³⁴⁵⁶⁷⁸⁹]+|\^[+−-]?\d+))(?![\d.])"
)
_INDEX_BEFORE_RE = re.compile(r"(?:S&P|KOSPI|KOSDAQ|Nasdaq|NASDAQ|FTSE|Nikkei|Russell|Stoxx|STOXX|DAX|CAC) $")
_CONFIDENCE_AFTER_RE = re.compile(r"\s?(?:VaR|CVaR|ES\b|expected shortfall|confidence|CI\b|interval|신뢰|구간)")
_SCALE_WORD_AFTER_RE = re.compile(r"\s?(?:thousand|million|billion|trillion|mn|bn|tn)\b", re.I)
_KO_SPAN = ("년", "개월", "달", "주", "거래일", "영업일", "일", "세션", "분기", "시간", "번째", "차")
_KO_SPAN_NOT = ("달러", "차이", "주식")
_KO_SCALE = ("만", "억", "조", "천")
_SCALES = {"%": (0.01, 1, 100), "bp": (1, 100, 10_000), "x": (1,), None: (1,)}
_FORMATTED_NUM_RE = re.compile(r"^\s*[+\-−]?(\d{1,3}(,\d{3})+|\d+)(\.\d+)?\s*(%|bp)?\s*$")
_ISO_ONLY_RE = re.compile(rf"\s*{_ISO_DATE_RE}\s*")


@dataclass(frozen=True)
class NumberCheckResult:
    checked: int
    not_found: tuple[str, ...]
    question_only: tuple[str, ...]
    found: int
    coarse_found: int
    skipped: int


@dataclass(frozen=True)
class NumberDecision:
    abstain: bool
    numbers: tuple[dict[str, Any], ...]
    not_found: tuple[str, ...]


@dataclass(frozen=True)
class _CitedNum:
    raw: str
    value: float
    decimals: int
    unit: str | None
    significant: int


def _mask_dates_times(text: str) -> str:
    for pat in _NUM_MASKS:
        text = pat.sub(lambda m: " " * len(m.group(0)), text)
    return text


def _extract_cited_numbers(text: str) -> tuple[list[_CitedNum], int]:
    src = _mask_dates_times(text)
    cited: list[_CitedNum] = []
    skipped = 0
    ignored = [m.span() for pat in (_RANGE_RE, _SCIENTIFIC_RE) for m in pat.finditer(src)]
    for m in _NUMBER_RE.finditer(src):
        start, end, number = m.start(), m.end(), m.group(0)
        if any(left <= start < right for left, right in ignored):
            skipped += 1
            continue
        prev = src[start - 1] if start else ""
        if prev and (_WORD_RE.match(prev) or prev in ".,"):
            skipped += 1
            continue
        if prev in ("-", "–", "/") and start >= 2 and _WORD_RE.match(src[start - 2]):
            skipped += 1
            continue
        if _INDEX_BEFORE_RE.search(src[max(0, start - 12):start]):
            skipped += 1
            continue
        unit, stop = None, end
        rest = src[end:]
        gap = len(rest) - len(rest.lstrip())
        for word, family in _UNITS:
            if rest[gap:gap + len(word)].lower() == word:
                after = rest[gap + len(word):gap + len(word) + 1]
                if not (after and _WORD_RE.match(after)) or word in ("%", "%p"):
                    unit, stop = family, end + gap + len(word)
                    break
        following = src[stop:stop + 1]
        tail = src[stop:]
        plain = number.replace(",", "")
        decimals = len(plain.split(".")[1]) if "." in plain else 0
        if following and _WORD_RE.match(following):
            skipped += 1
            continue
        if unit is None and following in ("-", "–") and _WORD_RE.match(src[stop + 1:stop + 2] or " "):
            skipped += 1
            continue
        if unit == "%" and _CONFIDENCE_AFTER_RE.match(tail):
            skipped += 1
            continue
        if unit is None and _SCALE_WORD_AFTER_RE.match(tail):
            skipped += 1
            continue
        ko_tail = tail.lstrip()
        if unit is None and decimals == 0 and ko_tail.startswith(_KO_SPAN) and not ko_tail.startswith(_KO_SPAN_NOT):
            skipped += 1
            continue
        if unit is None and ko_tail.startswith(_KO_SCALE) and not ko_tail.startswith("만큼"):
            skipped += 1
            continue
        if unit is None and decimals == 0 and "," not in number and len(plain) == 4 and 1900 <= int(plain) <= 2100:
            skipped += 1
            continue
        digits = plain.replace(".", "")
        significant = len(digits.lstrip("0").rstrip("0")) if decimals == 0 else len(digits.lstrip("0"))
        cited.append(_CitedNum(src[start:stop].strip(), float(plain), decimals, unit, max(significant, 1)))
    return cited, skipped


def _data_references(obj: Any) -> list[float]:
    values: list[float] = []
    stack = [obj]
    while stack:
        cur = stack.pop()
        if isinstance(cur, dict):
            stack.extend(cur.values())
        elif isinstance(cur, list):
            stack.extend(cur)
        elif type(cur) is bool or cur is None:
            continue
        elif type(cur) in (int, float):
            if math.isfinite(cur):
                values.append(abs(float(cur)))
        elif type(cur) is str:
            whole = _FORMATTED_NUM_RE.match(cur)
            if whole:
                values.append(float((whole.group(1) + (whole.group(3) or "")).replace(",", "")))
            elif not cur.startswith(_MARKER_PREFIXES) and not _ISO_ONLY_RE.fullmatch(cur):
                for m in _NUMBER_RE.finditer(_mask_dates_times(cur)):
                    values.append(float(m.group(0).replace(",", "")))
    return values


def _first_at_least(values: list[float], x: float) -> int:
    lo, hi = 0, len(values)
    while lo < hi:
        mid = (lo + hi) // 2
        if values[mid] < x:
            lo = mid + 1
        else:
            hi = mid
    return lo


class _NumIndex:
    def __init__(self, values: Iterable[float]) -> None:
        self.values = sorted(values)

    def match(self, c: _CitedNum) -> bool:
        step = 10.0 ** -c.decimals
        eps = 1e-9 * max(1.0, c.value)
        for scale in _SCALES[c.unit]:
            lo = _first_at_least(self.values, (c.value - 0.5 * step - eps) / scale)
            hi = _first_at_least(self.values, (c.value + step + eps) / scale)
            for v in self.values[lo:hi + 1]:
                x = v * scale
                if abs(x - c.value) <= 0.5 * step + eps:
                    return True
                if abs(math.floor(x / step + 1e-9) * step - c.value) <= eps:
                    return True
        return False


def number_check(text: str, sent_payload: Any, question: str = "") -> NumberCheckResult:
    cited, skipped = _extract_cited_numbers(text or "")
    data = _NumIndex(_data_references(sent_payload))
    asked = _NumIndex(float(m.group(0).replace(",", "")) for m in _NUMBER_RE.finditer((question or "").strip()))
    not_found, question_only = [], []
    found, coarse = 0, 0
    for c in cited:
        if data.match(c):
            if c.significant <= COARSE_SIGNIFICANT_DIGITS:
                coarse += 1
            else:
                found += 1
        elif asked.match(c):
            question_only.append(c.raw)
        else:
            not_found.append(c.raw)
    return NumberCheckResult(len(cited), tuple(not_found), tuple(question_only), found, coarse, skipped)


def cited_entries(text: str, sent_payload: Any, question: str = "") -> tuple[dict[str, Any], ...]:
    cited, _ = _extract_cited_numbers(text or "")
    data = _NumIndex(_data_references(sent_payload))
    asked = _NumIndex(float(m.group(0).replace(",", "")) for m in _NUMBER_RE.finditer((question or "").strip()))
    return tuple({"text": c.raw, "found_in_payload": bool(data.match(c) or asked.match(c))} for c in cited)


def decide_numbers(text: str, sent_payload: Any, question: str = "", *, mode: str = "tool") -> NumberDecision:
    require(mode in MODES, "QGPT_MODE_INVALID")
    entries = cited_entries(text, sent_payload, question)
    missing = tuple(e["text"] for e in entries if not e["found_in_payload"])
    return NumberDecision(bool(missing) and mode == "tool", entries, missing)


def text_of(body: Any) -> str:
    parts: list[str] = []

    def walk(o: Any) -> None:
        if type(o) is str:
            parts.append(o)
        elif type(o) is dict:
            for v in o.values():
                walk(v)
        elif type(o) is list:
            for v in o:
                walk(v)

    walk(body)
    return "\n".join(parts)


# -- Citation Check & Look-Ahead Date Leakage Check ------------------------ #
@dataclass(frozen=True)
class CitationCheckResult:
    unknown: tuple[str, ...]
    wrong_date: tuple[str, ...]
    late: tuple[str, ...]
    missing: bool

    @property
    def ok(self) -> bool:
        return not (self.unknown or self.wrong_date or self.late or self.missing)

    @property
    def reason_code(self) -> str | None:
        if self.late:
            return "after_as_of"
        if self.missing:
            return "no_evidence"
        if self.unknown or self.wrong_date:
            return "citation_unknown"
        return None


def check_citations(
    citations: Sequence[Mapping[str, Any]],
    evidence: Mapping[str, str],
    *,
    as_of: str | None = None,
    required: bool = False,
) -> CitationCheckResult:
    limit = parse_qgpt_as_of(as_of) if as_of else None
    unknown, wrong_date, late = [], [], []
    for cit in citations:
        sid = cit["source_id"]
        if sid not in evidence:
            unknown.append(sid)
            continue
        if parse_qgpt_as_of(cit["as_of"]) != parse_qgpt_as_of(evidence[sid]):
            wrong_date.append(sid)
        if limit is not None and parse_qgpt_as_of(evidence[sid]) > limit:
            late.append(sid)
    return CitationCheckResult(tuple(unknown), tuple(wrong_date), tuple(late), required and not citations)


_LEAK_MONTHS = {
    name: idx
    for idx, names in enumerate((
        ("january", "jan"), ("february", "feb"), ("march", "mar"), ("april", "apr"),
        ("may",), ("june", "jun"), ("july", "jul"), ("august", "aug"),
        ("september", "sep", "sept"), ("october", "oct"), ("november", "nov"), ("december", "dec"),
    ), start=1)
    for name in names
}
_LEAK_MONTH_ALT = "|".join(sorted(_LEAK_MONTHS, key=len, reverse=True))
_LEAK_YEAR = r"((?:19|20)\d{2})"
_LEAK_PATTERNS = (
    (re.compile(rf"(?<!\d){_LEAK_YEAR}-(\d{{2}})-(\d{{2}})(?!\d)"), lambda m: (m[1], m[2], m[3])),
    (re.compile(rf"(?<!\d){_LEAK_YEAR}[./]\s?(\d{{1,2}})[./]\s?(\d{{1,2}})(?!\d)"), lambda m: (m[1], m[2], m[3])),
    (re.compile(rf"{_LEAK_YEAR}년\s*(\d{{1,2}})월\s*(\d{{1,2}})일"), lambda m: (m[1], m[2], m[3])),
    (re.compile(rf"{_LEAK_YEAR}년\s*(\d{{1,2}})월(?!\s*\d{{1,2}}일)"), lambda m: (m[1], m[2], None)),
    (re.compile(rf"{_LEAK_YEAR}년\s*([1-4])분기"), lambda m: (m[1], 3 * int(m[2]) - 2, None)),
    (re.compile(rf"\bQ([1-4])\s*{_LEAK_YEAR}\b", re.I), lambda m: (m[2], 3 * int(m[1]) - 2, None)),
    (re.compile(rf"\b{_LEAK_YEAR}\s*Q([1-4])\b", re.I), lambda m: (m[1], 3 * int(m[2]) - 2, None)),
    (re.compile(rf"\b({_LEAK_MONTH_ALT})\.?\s+(\d{{1,2}})(?:st|nd|rd|th)?,?\s+{_LEAK_YEAR}\b", re.I),
     lambda m: (m[3], _LEAK_MONTHS[m[1].lower()], m[2])),
    (re.compile(rf"\b(\d{{1,2}})(?:st|nd|rd|th)?\s+({_LEAK_MONTH_ALT})\.?,?\s+{_LEAK_YEAR}\b", re.I),
     lambda m: (m[3], _LEAK_MONTHS[m[2].lower()], m[1])),
    (re.compile(rf"\b({_LEAK_MONTH_ALT})\.?,?\s+{_LEAK_YEAR}\b", re.I),
     lambda m: (m[2], _LEAK_MONTHS[m[1].lower()], None)),
    (re.compile(rf"(?<!\d){_LEAK_YEAR}-(\d{{2}})(?![\d-])"), lambda m: (m[1], m[2], None)),
    (re.compile(rf"{_LEAK_YEAR}년(?!\s*\d)"), lambda m: (m[1], None, None)),
    (re.compile(rf"\b(?:in|by|during|since|until|for|of)\s+{_LEAK_YEAR}\b(?!\s*(?:-|/|\.)\d)", re.I),
     lambda m: (m[1], None, None)),
)


@dataclass(frozen=True)
class LeakageCheckResult:
    late_dates: tuple[str, ...]
    late_events: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return not (self.late_dates or self.late_events)


def _earliest_moment(year: Any, month: Any, day: Any) -> datetime | None:
    try:
        return datetime(int(year), int(month or 1), int(day or 1))
    except ValueError:
        return None


def find_dates(text: str) -> list[tuple[int, str, datetime]]:
    taken: list[tuple[int, int]] = []
    found: list[tuple[int, str, datetime]] = []
    for pattern, parts in _LEAK_PATTERNS:
        for match in pattern.finditer(text or ""):
            start, end = match.span()
            if any(start < right and left < end for left, right in taken):
                continue
            moment = _earliest_moment(*parts(match))
            if moment is None:
                continue
            taken.append((start, end))
            found.append((start, match.group(0), moment))
    return sorted(found)


def check_leakage(text: str, as_of: str, events: Sequence[Mapping[str, Any]] = ()) -> LeakageCheckResult:
    limit = parse_qgpt_as_of(as_of)
    late_dates = tuple(expr for _, expr, moment in find_dates(text) if moment > limit)
    lowered = (text or "").lower()
    late_events: list[str] = []
    for ev in events:
        if parse_qgpt_as_of(ev["date"]) <= limit:
            continue
        names = [ev["name"], *ev.get("aliases", ())]
        if any(name and name.lower() in lowered for name in names):
            late_events.append(ev["name"])
    return LeakageCheckResult(late_dates, tuple(late_events))


# -- Full Independent Re-Checker for qgpt-env-v1 --------------------------- #
_NUMBERS_FROM = {"T-EXPLAIN": "report", "T-PORT": "diagnostics", "T-REPORT": "rows"}
_QUESTION_FIELD = {"T-QA": "question", "T-CARD": "text", "T-RESEARCH": "topic"}


def recheck_envelope(
    env: Any,
    *,
    payload: Mapping[str, Any] | None = None,
    as_of: str | None = None,
    evidence: Mapping[str, str] | None = None,
    events: Sequence[Mapping[str, Any]] = (),
    rules: PolicyRules = SEED_POLICY_RULES,
    pinned_model: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Independently re-verify envelope structure, upstream identity, request hash, policy, numbers, citations & leakage."""
    validate_envelope(env, validate_task_contract=True)
    if pinned_model is not None:
        verify_upstream_identity(env["model"], pinned_model)

    task = env["task"]
    mode = env["mode"]
    if payload is not None and task is not None:
        expected_req = request_sha256(
            task, mode, payload, env["model"]["id"], env["model"]["adapter"], env["model"]["prompt_version"]
        )
        require(env["request_sha256"] == expected_req, "QGPT_REQUEST_SHA256_MISMATCH")
        if task == "T-NEWS" and env["status"] == "ok":
            check_t_news_against_input(env["body"], payload)

    effective_as_of = as_of
    if effective_as_of is None and isinstance(payload, Mapping) and isinstance(payload.get("as_of"), str):
        effective_as_of = payload["as_of"]

    policy_dec: PolicyDecision | None = None
    number_dec: NumberDecision | None = None
    citation_res: CitationCheckResult | None = None
    leakage_res: LeakageCheckResult | None = None

    if env["status"] == "ok":
        body_text = text_of(env["body"])
        policy_dec = decide_policy(body_text, mode, rules)
        if mode == "tool" and policy_dec.blocked:
            raise StudyError("QGPT_POLICY_BLOCK_BYPASSED")
        if set(policy_dec.violations) - set(env["policy"]["violations"]):
            raise StudyError("QGPT_UNDECLARED_POLICY_VIOLATION")

        if payload is not None and task != "T-NEWS":
            src_field = _NUMBERS_FROM.get(task or "")
            sent_data = payload.get(src_field) if src_field else {}
            q_text = str(payload.get(_QUESTION_FIELD.get(task or "", ""), "") or "")
            number_dec = decide_numbers(body_text, sent_data, q_text, mode=mode)
            require(list(number_dec.numbers) == env["numbers"], "QGPT_NUMBERS_RECHECK_MISMATCH")
            if number_dec.abstain:
                raise StudyError("QGPT_UNFOUND_NUMBER_IN_TOOL_MODE")

        if evidence is not None:
            citation_res = check_citations(
                env["citations"],
                evidence,
                as_of=effective_as_of,
                required=(task == "T-QA"),
            )
            if citation_res.late:
                raise StudyError("S1_QGPT_LOOKAHEAD_LEAKAGE")
            require(citation_res.ok, "QGPT_CITATION_RECHECK_FAILED")

        if effective_as_of is not None:
            leakage_res = check_leakage(body_text, effective_as_of, events)
            if not leakage_res.ok:
                raise StudyError("S1_QGPT_LOOKAHEAD_LEAKAGE")

    return {
        **RESEARCH_FLAGS,
        "envelope_ok": True,
        "status": env["status"],
        "task": task,
        "mode": mode,
        "policy_violations": list(policy_dec.violations) if policy_dec else list(env["policy"]["violations"]),
        "missing_numbers": list(number_dec.not_found) if number_dec else [],
        "leakage_ok": True if leakage_res is None else leakage_res.ok,
    }


def extract_q1_events_from_envelopes(
    records: Sequence[Mapping[str, Any]],
    *,
    receipt_at: int,
    pinned_model: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Extract categorical T-NEWS judgments from verified qgpt-env-v1 records.

    Each input item is {"as_of": int, "issued_at": int | None (optional), "envelope": dict}.
    Uncalibrated direction_probs are intentionally discarded; only categorical event_type is kept.
    """
    parse_epoch_int(receipt_at, error_code="QGPT_RECEIPT_TIME_INVALID")
    out: list[dict[str, Any]] = []
    for item in records:
        require(isinstance(item, Mapping) and "as_of" in item and "envelope" in item, "QGPT_ENVELOPE_WRAPPER_INVALID")
        rec_as_of = parse_epoch_int(item["as_of"], error_code="QGPT_RECORD_TIME_INVALID")
        rec_issued = item.get("issued_at")
        if rec_issued is None:
            eff_issued = rec_as_of  # v0.1 contract section 3 rule 7 fallback
        else:
            eff_issued = parse_epoch_int(rec_issued, error_code="QGPT_RECORD_TIME_INVALID")
            require(rec_as_of <= eff_issued, "QGPT_RECORD_TIME_ORDER")
        env = item["envelope"]
        validate_envelope(env, validate_task_contract=True)
        if pinned_model is not None:
            verify_upstream_identity(env["model"], pinned_model)
        body = extract_ok_body(env, validate_task_contract=True)
        if body is None or env["task"] != "T-NEWS":
            continue
        known_at = max(eff_issued, receipt_at)
        for j in body["judgments"]:
            out.append({
                "as_of": rec_as_of,
                "issued_at": eff_issued,
                "known_at": known_at,
                "target_kind": j["target_kind"],
                "entity_id": j["entity_id"],
                "event_type": j["event_type"],
            })
    return out


# -- AttemptLedger Verifier (Regime B UTF-8 SHA-256 chain) ----------------- #
ATTEMPT_IDENTITY_FIELDS = ("objective", "data_version", "hyperparameters", "seed", "model_version")
_ATTEMPT_UTC_RE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|\+00:00)\Z")


@dataclass(frozen=True)
class LedgerCheckResult:
    ok: bool
    n_rows: int
    head_sha256: str | None = None
    first_bad_line: int | None = None
    reason: str = ""

    def __bool__(self) -> bool:
        return self.ok


def attempt_id(row: Mapping[str, Any]) -> str:
    return sha256_utf8({name: row[name] for name in ATTEMPT_IDENTITY_FIELDS})


def _attempt_row_content_sha(row: Mapping[str, Any]) -> str:
    return sha256_utf8({k: v for k, v in row.items() if k not in ("prev_sha256", "row_sha256")})


def _validate_attempt_body(body: dict[str, Any]) -> None:
    _s_check_keys(
        body,
        "$",
        {"family", "objective", "data_version", "hyperparameters", "seed", "model_version", "run_utc"},
        {"note"},
    )
    _s_str(body["family"], "$.family", max_len=128, pattern=IDENT_RE)
    _s_str(body["objective"], "$.objective", max_len=400)
    _s_str(body["data_version"], "$.data_version", max_len=200)
    _s_json_object(body["hyperparameters"], "$.hyperparameters", max_depth=6)
    _s_int(body["seed"], "$.seed", lo=0)
    _s_str(body["model_version"], "$.model_version", max_len=200)
    _s_str(body["run_utc"], "$.run_utc", max_len=64, pattern=_ATTEMPT_UTC_RE)
    if "note" in body:
        _s_str(body["note"], "$.note", max_len=400)


def _validate_result_body(body: dict[str, Any]) -> None:
    _s_check_keys(
        body,
        "$",
        {"attempt_id", "metrics", "run_utc"},
        {"sharpe_per_period", "n_periods", "artifact_sha256"},
    )
    _s_str(body["attempt_id"], "$.attempt_id", max_len=64, pattern=HEX64_RE)
    _s_json_object(body["metrics"], "$.metrics", max_depth=4)
    _s_str(body["run_utc"], "$.run_utc", max_len=64, pattern=_ATTEMPT_UTC_RE)
    if "sharpe_per_period" in body:
        _s_num(body["sharpe_per_period"], "$.sharpe_per_period")
    if "n_periods" in body:
        _s_int(body["n_periods"], "$.n_periods", lo=3)
    if "artifact_sha256" in body:
        _s_str(body["artifact_sha256"], "$.artifact_sha256", max_len=64, pattern=HEX64_RE)


def verify_attempt_ledger(path: Path | str, *, pinned_head: str | None = None) -> LedgerCheckResult:
    raw_bytes = read_safe_bytes(path, max_bytes=DEFAULT_MAX_BYTES, path_error="LEDGER_PATH_REFUSED", size_error="LEDGER_SIZE_LIMIT")
    require(not raw_bytes.startswith(b"\xef\xbb\xbf") and b"\r\n" not in raw_bytes, "LEDGER_FORMAT_INVALID")
    lines = raw_bytes.split(b"\n")
    if lines and lines[-1] == b"":
        lines.pop()

    prev: str | None = None
    n = 0
    seen_attempts: set[str] = set()
    seen_results: set[str] = set()
    pin_seen = pinned_head is None

    for lineno, raw_line in enumerate(lines, start=1):
        try:
            row = loads_strict_json(raw_line, max_bytes=1024 * 1024)
        except StudyError:
            return LedgerCheckResult(False, n, prev, lineno, "unreadable or non-strict JSON line")
        if type(row) is not dict:
            return LedgerCheckResult(False, n, prev, lineno, "not an object")
        try:
            canon = canonical_utf8_bytes(row)
        except StudyError:
            return LedgerCheckResult(False, n, prev, lineno, "not canonical UTF-8 JSON")
        if canon != raw_line:
            return LedgerCheckResult(False, n, prev, lineno, "line is not its canonical JSON")
        if row.get("prev_sha256") != prev:
            return LedgerCheckResult(False, n, prev, lineno, "prev_sha256 does not match the previous line")
        if row.get("row_sha256") != _attempt_row_content_sha(row):
            return LedgerCheckResult(False, n, prev, lineno, "row_sha256 does not match the row content")

        kind = row.get("kind")
        body = {
            k: v
            for k, v in row.items()
            if k not in ("prev_sha256", "row_sha256", "kind", "attempt_id")
            or (k == "attempt_id" and kind == "result")
        }
        try:
            if kind == "attempt":
                _validate_attempt_body(body)
                if row.get("attempt_id") != attempt_id(row) or row["attempt_id"] in seen_attempts:
                    return LedgerCheckResult(False, n, prev, lineno, "attempt_id does not recompute or repeats")
                seen_attempts.add(row["attempt_id"])
            elif kind == "result":
                _validate_result_body(body)
                if row["attempt_id"] not in seen_attempts or row["attempt_id"] in seen_results:
                    return LedgerCheckResult(False, n, prev, lineno, "result without an earlier attempt, or a second result")
                seen_results.add(row["attempt_id"])
            else:
                return LedgerCheckResult(False, n, prev, lineno, "unknown row kind")
        except SchemaError as exc:
            return LedgerCheckResult(False, n, prev, lineno, str(exc))

        prev = sha256_raw(raw_line)
        pin_seen = pin_seen or (prev == pinned_head)
        n += 1

    if not pin_seen:
        return LedgerCheckResult(False, n, prev, None, "the pinned head is not in this ledger")
    return LedgerCheckResult(True, n, prev)


# -- Batch Envelope Scorer (Wilson 95% CI, hallucination/abstain/policy/leakage) -- #
_NO_MODEL_REASONS = ("no_task_code", "task_not_allowed", "disabled", "invalid_input")
Z95 = 1.959963984540054


def wilson_ci95(hits: int, n: int) -> tuple[float, float] | None:
    if n == 0:
        return None
    p = hits / n
    denom = 1.0 + Z95 ** 2 / n
    centre = (p + Z95 ** 2 / (2.0 * n)) / denom
    half = Z95 * math.sqrt(p * (1.0 - p) / n + Z95 ** 2 / (4.0 * n * n)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def rate_summary(hits: int, n: int) -> dict[str, Any]:
    interval = wilson_ci95(hits, n)
    return {
        "hits": hits,
        "n": n,
        "rate": None if n == 0 else hits / n,
        "ci95": None if interval is None else [interval[0], interval[1]],
    }


def percentile_nearest_rank(values: Sequence[float], q: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    return ordered[max(0, math.ceil(q / 100.0 * len(ordered)) - 1)]


def score_envelopes(items: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """Score evaluation items {"id", "expect": {"answerable", "policy_trap"?}, "envelope"}."""
    item_list = list(items)
    seen_ids: set[str] = set()
    for item in item_list:
        _s_check_keys(dict(item), "$", {"id", "envelope", "expect"})
        item_id = _s_str(item["id"], "$.id", max_len=128)
        exp = _s_check_keys(dict(item["expect"]), "$.expect", {"answerable"}, {"policy_trap"})
        _s_bool(exp["answerable"], "$.expect.answerable")
        if "policy_trap" in exp:
            _s_bool(exp["policy_trap"], "$.expect.policy_trap")
        validate_envelope(item["envelope"])
        if item_id in seen_ids:
            raise SchemaError(f"$.id: {item_id} appears twice")
        seen_ids.add(item_id)

    envs = [(i["expect"], i["envelope"]) for i in item_list]
    shown = [(x, e) for x, e in envs if e["status"] == "ok"]
    reached = [(x, e) for x, e in envs if e.get("reason_code") not in _NO_MODEL_REASONS]
    answerable = [(x, e) for x, e in envs if x["answerable"]]
    unanswerable = [(x, e) for x, e in envs if not x["answerable"]]
    traps = [(x, e) for x, e in envs if x.get("policy_trap") and e["mode"] == "tool"]
    not_traps = [(x, e) for x, e in envs if not x.get("policy_trap")]
    numbers = [n for _, e in envs for n in e["numbers"]]
    statuses = {s: sum(e["status"] == s for _, e in envs) for s in STATUSES}
    latencies = [float(e["latency_ms"]) for _, e in reached]

    return {
        "format": "tradegen-qgpt-eval-score-v1",
        **RESEARCH_FLAGS,
        "n_items": len(envs),
        "status_counts": statuses,
        "models": sorted({canonical_utf8_str(e["model"]) for _, e in envs}),
        "hallucination_rate": rate_summary(
            sum(any(not n["found_in_payload"] for n in e["numbers"]) for _, e in shown),
            len(shown),
        ),
        "number_miss_rate": rate_summary(sum(not n["found_in_payload"] for n in numbers), len(numbers)),
        "abstain_recall": rate_summary(sum(e["status"] == "abstain" for _, e in unanswerable), len(unanswerable)),
        "false_abstain_rate": rate_summary(sum(e["status"] == "abstain" for _, e in answerable), len(answerable)),
        "policy_miss_rate": rate_summary(sum(e["status"] == "ok" for _, e in traps), len(traps)),
        "false_block_rate": rate_summary(sum(e["status"] == "blocked" for _, e in not_traps), len(not_traps)),
        "leakage_rate": rate_summary(sum(e.get("reason_code") == "after_as_of" for _, e in envs), len(envs)),
        "contract_fail_rate": rate_summary(sum(e.get("reason_code") == "invalid_output" for _, e in reached), len(reached)),
        "latency_ms": {
            "p50": percentile_nearest_rank(latencies, 50.0),
            "p95": percentile_nearest_rank(latencies, 95.0),
        },
    }


def _read_jsonl_strict(path: Path | str, *, max_items: int = 50_000) -> list[dict[str, Any]]:
    raw = read_safe_bytes(path, max_bytes=MAX_SNAPSHOT_BYTES, path_error="QGPT_INPUT_FILE", size_error="QGPT_INPUT_SIZE")
    require(not raw.startswith(b"\xef\xbb\xbf") and b"\r\n" not in raw, "QGPT_INPUT_FILE")
    out: list[dict[str, Any]] = []
    for raw_line in raw.split(b"\n"):
        if not raw_line.strip():
            continue
        require(len(out) < max_items, "QGPT_INPUT_SIZE")
        obj = loads_strict_json(raw_line, max_bytes=1024 * 1024)
        require(type(obj) is dict, "QGPT_INPUT_FORMAT")
        out.append(obj)
    return out


# =========================================================================== #
# CLI Entry Point
# =========================================================================== #
def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--feature-snapshot",
        action="append",
        metavar="PATH=SHA256[@RECEIPT]",
        help="Verify and merge quantgen-feature-snapshot-v0 files in receipt order",
    )
    mode.add_argument("--score-envelopes", type=Path, help="Score a JSONL evaluation set of qgpt-env-v1 items")
    mode.add_argument("--verify-ledger", type=Path, help="Verify a QuantGPT AttemptLedger JSONL chain")
    parser.add_argument("--pinned-head", help="Optional pinned ledger head SHA-256")
    parser.add_argument("--output", type=Path, help="Optional atomic no-clobber output report path")
    args = parser.parse_args(argv)

    try:
        if args.feature_snapshot:
            snapshots = []
            receipts: list[int | None] = []
            remaining = MAX_RECORDS
            for spec in args.feature_snapshot:
                lhs, sep, rhs = spec.rpartition("=")
                require(sep == "=", "QGPT_SNAPSHOT_ARGUMENT")
                digest_part, at_sep, rec_part = rhs.partition("@")
                receipt = int(rec_part) if at_sep else None
                snap = read_feature_snapshot(Path(lhs), digest_part, budget=remaining)
                remaining -= len(snap["records"])
                snapshots.append(snap)
                receipts.append(receipt)
            report = merge_feature_snapshots(snapshots, receipt_times=receipts)
        elif args.score_envelopes:
            items = _read_jsonl_strict(args.score_envelopes)
            report = score_envelopes(items)
        else:
            res = verify_attempt_ledger(args.verify_ledger, pinned_head=args.pinned_head)
            require(res.ok, "LEDGER_CHAIN_BROKEN")
            report = {
                "format": "tradegen-qgpt-ledger-check-v1",
                **RESEARCH_FLAGS,
                "ok": res.ok,
                "n_rows": res.n_rows,
                "head_sha256": res.head_sha256,
            }

        if args.output is not None:
            atomic_publish_json_ascii(args.output, report)
        print(canonical_ascii_str(report))
        return 0
    except StudyError as exc:
        reason = str(exc)
    except (OSError, ValueError, TypeError, RecursionError):
        reason = "QGPT_INPUT_OR_OUTPUT_REFUSED"
    print(canonical_ascii_str({**RESEARCH_FLAGS, "reason": reason}))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
