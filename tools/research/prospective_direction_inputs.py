"""Resolve explicitly supplied private M11 inputs against the existing recorder receipts."""
from __future__ import annotations

from bisect import bisect_right
from pathlib import Path

from tools.research import didm_run_log, direction_feature_builder as features, quantgpt_feature_bridge, upbit_price_recorder, upbit_quote_recorder
from tools.research._study_common import (
    HEX64_RE, RESEARCH_FLAGS, check_safe_path, read_strict_json_file, read_verified_chained_log, require, sha256_ascii, sha256_raw,
)

MAX_FILE = 64 * 1024 * 1024


def _relative(directory, value):
    require(type(value) is str and value and not Path(value).is_absolute() and ".." not in Path(value).parts,
            "INPUT_PATH_NOT_RELATIVE")
    return check_safe_path(directory / value)


def _object(path):
    doc, raw = read_strict_json_file(path, max_bytes=MAX_FILE)
    require(type(doc) is dict, "INVALID_INPUT_OBJECT")
    return doc, sha256_raw(raw)


def _prefix(directory, filename, head, ancestor=None):
    rows, _ = read_verified_chained_log(directory, filename, pinned_head=head)
    prefix = []
    for row in rows:
        prefix.append(row)
        if row["sha256"] == head:
            break
    require(prefix and prefix[-1]["sha256"] == head, "RECORDER_HEAD_MISSING")
    require(ancestor is None or any(r["sha256"] == ancestor for r in prefix), "RECORDER_ARCHIVE_CHANGED")
    return [row["data"] for row in prefix]


def price_export(path, study, now, recorder, ancestor=None):
    hist, _ = _object(path)
    manifest, _ = _object(path.with_suffix(".manifest.json"))
    require(manifest.get("format") == "tradegen-price-history-manifest-v1"
            and all(manifest.get(k) is v for k, v in RESEARCH_FLAGS.items())
            and sha256_ascii({k: v for k, v in manifest.items() if k != "manifest_sha256"}) == manifest.get("manifest_sha256")
            and manifest["history_file"] == path.name and manifest["history_sha256"] == sha256_ascii(hist)
            and type(manifest["exported_at"]) is int and manifest["exported_at"] <= now
            and type(manifest["archive_head_sha256"]) is str and HEX64_RE.fullmatch(manifest["archive_head_sha256"])
            and all(manifest[k] == study[k] for k in ("market", "scope", "source_id", "step_seconds"))
            and hist["scope"] == study["scope"] and hist["source_id"] == study["source_id"]
            and manifest["bar_count"] == len(hist["bars"])
            and all(b["known_at"] <= manifest["exported_at"] for b in hist["bars"]),
            "PRICE_EXPORT_RECEIPT_MISMATCH")
    prefix = _prefix(recorder, "bars.jsonl", manifest["archive_head_sha256"], ancestor)
    header = prefix[0]
    require(header["kind"] == "config" and header["schema"] == upbit_price_recorder.RECORDER_SCHEMA
            and all(header["config"][k] == study[k] for k in ("market", "step_seconds")), "RECORDER_HEADER_MISMATCH")
    require(not any(r.get("kind") == "s1_unbackfillable_gap" for r in prefix), "S1_UNBACKFILLABLE_BAR")
    first, last = hist["bars"][0]["end"], hist["bars"][-1]["end"]
    original = [{k: r[k] for k in ("end", "known_at", "return_bps")} for r in prefix
                if r.get("kind") == "bar" and first <= r["end"] <= last]
    require(original == hist["bars"] and all(b["end"] < b["known_at"] for b in original), "RECORDED_BARS_CHANGED")
    return hist, manifest


def quote_export(path, study, now, recorder, ancestor=None):
    doc, _ = _object(path)
    manifest, _ = _object(path.with_suffix(".manifest.json"))
    upbit_quote_recorder.verify_daily_quotes(doc)
    require(manifest["format"] == upbit_quote_recorder.DAILY_QUOTE_MANIFEST_FORMAT
            and all(manifest.get(k) is v for k, v in RESEARCH_FLAGS.items())
            and sha256_ascii({k: v for k, v in manifest.items() if k != "manifest_sha256"}) == manifest["manifest_sha256"]
            and manifest["exported_at"] <= now and manifest["quote_file"] == path.name
            and all(manifest[k] == doc[k] for k in ("market", "scope", "kst_date", "app_running", "quote_sha256",
                "observation_count", "valid_same_second_count", "expected_observations", "quote_coverage")),
            "QUOTE_EXPORT_RECEIPT_MISMATCH")
    prefix = _prefix(recorder, "quotes.jsonl", manifest["archive_head_sha256"], ancestor)
    header = prefix[0]
    require(header["kind"] == "config" and header["schema"] == upbit_quote_recorder.QUOTE_RECORDER_SCHEMA
            and all(header["config"][k] == study[k] for k in ("market", "scope"))
            and header["config"]["interval_seconds"] == study["quote_interval_seconds"]
            and header["config"]["app_running"] is doc["app_running"], "RECORDER_HEADER_MISMATCH")
    original = [r["observation"] for r in prefix if r.get("kind") == "quote" and r["kst_date"] == doc["kst_date"]]
    require([{**obs, "sequence": i} for i, obs in enumerate(original, 1)] == doc["observations"],
            "RECORDED_QUOTES_CHANGED")
    return doc, manifest


def _covered(times, bars, cadence):
    times = sorted(times)
    for bar in bars:
        end = bar["end"]
        i = bisect_right(times, end) - 1
        if i < 0 or times[i] <= end - cadence:
            return False
    return True


def rebuild(inputs_path, model, study, now, *, training=False, expected_ancestor=None, price_ancestor=None):
    """Use checksummed local inputs for point-in-time reconstruction without trusting supplied feature values."""
    plan, _ = _object(inputs_path)
    require(set(plan) == {"history", "price_log", "run_log", "didm_reports", "didm_exports", "quantgpt_snapshots"}, "INVALID_SOURCE_INPUTS")
    directory = inputs_path.parent
    history_files = plan["history"] if isinstance(plan["history"], list) else [plan["history"]]
    require(history_files and len(set(history_files)) == len(history_files), "INVALID_PRICE_EXPORT_SET")
    combined_bars, receipts = [], []
    anchor = price_ancestor
    for filename in history_files:
        segment, price_manifest = price_export(_relative(directory, filename), study, now,
                                               _relative(directory, plan["price_log"]), anchor)
        anchor = price_manifest["archive_head_sha256"]
        combined_bars.extend(segment["bars"])
        receipts.append(price_manifest)
    history = {"scope": study["scope"], "source_id": study["source_id"], "bars": combined_bars}
    require(all(b["end"] - a["end"] == study["step_seconds"] for a, b in zip(combined_bars, combined_bars[1:])),
            "MISSING_OR_DUPLICATE_BAR")
    run_log = didm_run_log.summarize_run_log(_relative(directory, plan["run_log"]), pinned_head=expected_ancestor)
    require(run_log["entry_count"] > 0, "MISSING_RESEARCH_SOURCE_LOG")
    first_bar = history["bars"][0]["end"]
    hashes = {"run_log_head": run_log["head_sha256"], "price_manifests": receipts,
              "didm_reports": [], "didm_exports": [], "quantgpt_snapshots": []}
    names, defs, pins = model["feature_names"], model["feature_definitions"], model["upstream_identities"]
    require(model["feature_builder_commit"] != "0" * 40, "BUILDER_REVISION_REQUIRED")
    report_receipts = {r["report_sha256"]: r for r in run_log["bridge_snapshots"] if r["captured_at"] <= now}
    reports, exports, qgpt = [], [], []
    qgpt_seen = set()
    for key in ("didm_reports", "didm_exports", "quantgpt_snapshots"):
        require(type(plan[key]) is list and len(set(plan[key])) == len(plan[key]), "INVALID_SOURCE_INPUTS")
        for name in plan[key]:
            path = _relative(directory, name)
            doc, raw_sha = _object(path)
            if key == "didm_reports":
                require(raw_sha in report_receipts, "UNRECORDED_BRIDGE_REPORT")
                reports.append(doc)
            elif key == "didm_exports":
                receipt = run_log["didm_export_receipts"].get(raw_sha)
                require(receipt and receipt["received_at"] <= now, "UNRECORDED_DIDM_EXPORT")
                exports.append((doc, receipt["received_at"]))
            else:
                snap = quantgpt_feature_bridge.check_feature_snapshot(doc)
                receipt = run_log["quantgpt_receipts"].get(snap["snapshot_sha256"])
                require(receipt and receipt["surface"] == "feature_snapshot" and snap["generated_at"] <= receipt["received_at"] <= now,
                        "UNRECORDED_QUANTGPT_SNAPSHOT")
                qgpt_seen.add(snap["snapshot_sha256"])
                qgpt.append((doc, receipt["received_at"]))
            hashes[key].append(raw_sha)
    if {"D1", "D2"} & set(names):
        require(reports, "RECORDED_DIDM_REPORT_REQUIRED")
        by_day = {}
        for r in report_receipts.values():
            if r["captured_at"] >= first_bar - 7 * 86400:
                day = r["kst_day"]
                if day not in by_day or r["captured_at"] >= by_day[day]["captured_at"]:
                    by_day[day] = r
        require({r["report_sha256"] for r in by_day.values()} <= set(hashes["didm_reports"]),
                "KNOWN_DIDM_DAY_OMITTED")
    if "D3" in names:
        pin = pins.get("didm_v0")
        require(exports and type(pin) is dict and type(pin.get("model_version")) is str
                and type(pin.get("prompt_sha256")) is str and HEX64_RE.fullmatch(pin["prompt_sha256"]),
                "LIVE_PINNED_DIDM_EXPORT_REQUIRED")
    if "Q1" in names:
        require(qgpt and type(pins.get("quantgpt")) is dict and
                all(k in pins["quantgpt"] for k in ("name", "version", "sha256")), "LIVE_PINNED_QUANTGPT_REQUIRED")
    for name, seen, key in (("D3", set(hashes["didm_exports"]), "didm_export_receipts"),
                            ("Q1", qgpt_seen, "quantgpt_receipts")):
        if name in names:
            cutoff = first_bar - max(86400, defs[name.lower() + "_cadence_seconds"])
            required = {digest for digest, r in run_log[key].items() if cutoff < r["received_at"] <= now}
            require(required <= seen, "KNOWN_SOURCE_RECEIPT_OMITTED")
    bars = history["bars"]
    if training:
        period = [b for b in bars if model["training_start"] <= b["end"] <= model["training_cutoff"]]
        require(period and period[0]["end"] == model["training_start"] and period[-1]["end"] == model["training_cutoff"],
                "TRAINING_COVERAGE_MISSING")
        for name, rows in (("D3", exports), ("Q1", qgpt)):
            if name in names:
                cadence = defs[name.lower() + "_cadence_seconds"]
                require(_covered((t for _, t in rows), period, cadence), "TRAINING_RECEIPT_COVERAGE_MISSING")
    table = features.build_feature_table(market=study["market"], step_seconds=study["step_seconds"], bars=bars,
        feature_names=names, didm_reports=reports, run_log_summary=run_log, didm_v0_exports=exports,
        quantgpt_snapshots=qgpt, pinned_didm_v0=pins["didm_v0"], pinned_quantgpt_model=pins["quantgpt"],
        feature_builder_commit=model["feature_builder_commit"], strict_s4=True, **defs)
    return table, history, hashes
