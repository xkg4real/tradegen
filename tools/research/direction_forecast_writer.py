"""Batch and live forecast writer producing tradegen-direction-forecast-v1 snapshots + manifests.

Research only. Verifies frozen model.sha256 and S4 upstream identities, omits missing-feature
and rounded-tie bars, enforces non-revision index on (model.sha256, market, as_of, horizon_seconds),
validates snapshots via direction_forecast_adapter.check_snapshot, and publishes sidecar manifests
carrying RESEARCH_FLAGS.
Zero imports from core.compliance, core.odds, execution*, tools.owner, config, or main.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import time
from typing import Any, Mapping, Sequence

from tools.research import adaptive_bid_gap_preview as preview
from tools.research import direction_feature_builder as dfb
from tools.research import direction_forecast_adapter as adapter
from tools.research import direction_model_fit as dmf
from tools.research._study_common import (
    HashChainedLog,
    PRODUCER_RE,
    RESEARCH_FLAGS,
    StudyError,
    atomic_publish_json_ascii,
    canonical_ascii_str,
    parse_epoch_int,
    read_verified_chained_log,
    require,
    sha256_ascii,
)


MANIFEST_FORMAT = "tradegen-direction-forecast-manifest-v1"
INDEX_FILENAME = "forecast_key_index.jsonl"


def _verify_s4_compatibility(artifact: Mapping[str, Any], feature_table: Mapping[str, Any]) -> None:
    """Ensure feature table definitions and upstream identities match the frozen model artifact (S4)."""
    require(feature_table.get("market") == artifact["market"], "S4_FROZEN_DEFINITION_CHANGED")
    require(int(feature_table.get("step_seconds", -1)) == int(artifact["step_seconds"]), "S4_FROZEN_DEFINITION_CHANGED")
    require(feature_table.get("feature_builder_commit") == artifact["feature_builder_commit"], "S4_FROZEN_DEFINITION_CHANGED")

    table_features = set(feature_table.get("feature_names", ()))
    for req_feat in artifact["feature_names"]:
        require(req_feat in table_features, "S4_FROZEN_DEFINITION_CHANGED")

    if artifact["role"] == "M":
        art_defs = artifact.get("feature_definitions", {})
        tbl_defs = feature_table.get("feature_definitions", {})
        if "D1" in artifact["feature_names"]:
            require(tbl_defs.get("d1_series") == art_defs.get("d1_series"), "S4_FROZEN_DEFINITION_CHANGED")
            require(
                tbl_defs.get("d1_schedule_window_seconds") == art_defs.get("d1_schedule_window_seconds"),
                "S4_FROZEN_DEFINITION_CHANGED",
            )
        if "D3" in artifact["feature_names"]:
            require(tbl_defs.get("d3_event_types") == art_defs.get("d3_event_types"), "S4_FROZEN_DEFINITION_CHANGED")
            require(tbl_defs.get("d3_cadence_seconds") == art_defs.get("d3_cadence_seconds"), "S4_FROZEN_DEFINITION_CHANGED")
            require(
                feature_table.get("upstream_identities", {}).get("didm_v0")
                == artifact.get("upstream_identities", {}).get("didm_v0"),
                "S4_FROZEN_DEFINITION_CHANGED",
            )
        if "Q1" in artifact["feature_names"]:
            require(tbl_defs.get("q1_event_types") == art_defs.get("q1_event_types"), "S4_FROZEN_DEFINITION_CHANGED")
            require(tbl_defs.get("q1_cadence_seconds") == art_defs.get("q1_cadence_seconds"), "S4_FROZEN_DEFINITION_CHANGED")
            require(
                feature_table.get("upstream_identities", {}).get("quantgpt")
                == artifact.get("upstream_identities", {}).get("quantgpt"),
                "S4_FROZEN_DEFINITION_CHANGED",
            )


def _load_key_index(index_dir: Path | str) -> dict[tuple[str, str, int, int], dict[str, Any]]:
    entries, _ = read_verified_chained_log(index_dir, INDEX_FILENAME)
    out: dict[tuple[str, str, int, int], dict[str, Any]] = {}
    for row in entries:
        d = row["data"]
        key = (str(d["model_sha256"]), str(d["market"]), int(d["as_of"]), int(d["horizon_seconds"]))
        out[key] = dict(d["forecast_core"])
    return out


def build_forecasts_from_model(
    *,
    artifact: Mapping[str, Any],
    feature_table: Mapping[str, Any],
    issued_at: int,
    generated_at: int | None = None,
    producer: str = "tradegen-research",
    mode: str = "batch",
    start_as_of: int | None = None,
    end_as_of: int | None = None,
    expected_model_sha256: str | None = None,
    index_dir: Path | str | None = None,
    skip_already_indexed: bool = False,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Evaluate frozen model on point-in-time feature rows and return (snapshot, manifest_body)."""
    dmf.verify_model_artifact(dict(artifact), expected_model_sha256)
    dfb.verify_feature_table(feature_table)
    require(mode in ("batch", "live"), "INVALID_WRITER_MODE")
    require(type(producer) is str and PRODUCER_RE.fullmatch(producer) is not None, "INVALID_PRODUCER")
    parse_epoch_int(issued_at, error_code="INVALID_ISSUED_AT")
    gen_at = issued_at if generated_at is None else parse_epoch_int(generated_at, low=issued_at, error_code="INVALID_GENERATED_AT")

    _verify_s4_compatibility(artifact, feature_table)

    frozen_at = int(artifact["frozen_at"])
    market = str(artifact["market"])
    horizon = int(artifact["horizon_seconds"])
    hurdle_bps = int(artifact["hurdle_bps"])
    model_sha = str(artifact["sha256"])

    candidate_rows = sorted(
        [
            r for r in feature_table["rows"]
            if int(r["as_of"]) > frozen_at
            and (start_as_of is None or int(r["as_of"]) >= start_as_of)
            and (end_as_of is None or int(r["as_of"]) <= end_as_of)
        ],
        key=lambda r: int(r["as_of"]),
    )
    if mode == "live" and candidate_rows and start_as_of is None and end_as_of is None:
        candidate_rows = [candidate_rows[-1]]

    existing_index = _load_key_index(index_dir) if index_dir is not None else {}
    new_index_entries: list[dict[str, Any]] = []

    forecasts: list[dict[str, Any]] = []
    omitted_missing = 0
    omitted_ties = 0
    skipped_indexed = 0

    for row in candidate_rows:
        as_of = int(row["as_of"])
        require(as_of <= issued_at, "FORECAST_TIME_ORDER")
        raw_probs = dmf.predict_raw_probabilities(artifact, row["features"])
        if raw_probs is None:
            omitted_missing += 1
            continue
        quant = dmf.quantize_probabilities(raw_probs["up"], raw_probs["down"])
        if quant is None:
            omitted_ties += 1
            continue
        probs_str, direction = quant

        key = (model_sha, market, as_of, horizon)
        core = {
            "hurdle_bps": hurdle_bps,
            "probabilities": probs_str,
            "direction": direction,
        }
        if key in existing_index:
            require(existing_index[key] == core, "FORECAST_REVISED")
            if skip_already_indexed:
                skipped_indexed += 1
                continue
        else:
            existing_index[key] = core
            new_index_entries.append({
                "model_sha256": model_sha,
                "market": market,
                "as_of": as_of,
                "horizon_seconds": horizon,
                "forecast_core": core,
                "first_issued_at": issued_at,
            })

        forecasts.append({
            "market": market,
            "as_of": as_of,
            "issued_at": issued_at,
            "horizon_seconds": horizon,
            "hurdle_bps": hurdle_bps,
            "probabilities": probs_str,
            "direction": direction,
        })

    require(len(forecasts) <= adapter.MAX_FORECASTS, "SNAPSHOT_SIZE")

    snapshot_body = {
        "format": adapter.FORMAT,
        "producer": producer,
        "model": {
            "name": str(artifact["name"]),
            "version": str(artifact["version"]),
            "sha256": model_sha,
            "training_cutoff": int(artifact["training_cutoff"]),
            "frozen_at": frozen_at,
        },
        "generated_at": gen_at,
        "forecasts": forecasts,
    }
    snapshot = {
        **snapshot_body,
        "snapshot_sha256": preview.model_id(snapshot_body),
    }
    try:
        adapter.check_snapshot(snapshot)
    except preview.Invalid as exc:
        raise StudyError(str(exc)) from None

    if index_dir is not None and new_index_entries:
        with HashChainedLog(index_dir, INDEX_FILENAME, lock_name=".forecast_index.lock") as idx_log:
            for item in new_index_entries:
                idx_log.append(item)

    manifest = {
        "format": MANIFEST_FORMAT,
        **RESEARCH_FLAGS,
        "mode": mode,
        "producer": producer,
        "model": dict(snapshot["model"]),
        "role": artifact["role"],
        "upstream_identities": dict(artifact.get("upstream_identities", {})),
        "feature_builder_commit": artifact["feature_builder_commit"],
        "feature_table_sha256": feature_table.get("table_sha256"),
        "snapshot_sha256": snapshot["snapshot_sha256"],
        "issued_at": issued_at,
        "generated_at": gen_at,
        "evaluated_bar_count": len(candidate_rows),
        "forecast_count": len(forecasts),
        "omitted_missing_features": omitted_missing,
        "omitted_rounded_ties": omitted_ties,
        "skipped_already_indexed": skipped_indexed,
    }
    manifest["manifest_sha256"] = sha256_ascii(manifest)
    return snapshot, manifest


def write_forecast_snapshot(
    output_path: Path | str,
    *,
    artifact: Mapping[str, Any],
    feature_table: Mapping[str, Any],
    issued_at: int,
    generated_at: int | None = None,
    producer: str = "tradegen-research",
    mode: str = "batch",
    start_as_of: int | None = None,
    end_as_of: int | None = None,
    expected_model_sha256: str | None = None,
    index_dir: Path | str | None = None,
    skip_already_indexed: bool = False,
) -> tuple[dict[str, Any], dict[str, Any], Path, Path]:
    """Build, validate, and atomically publish snapshot.json + snapshot.manifest.json."""
    out_file = Path(output_path)
    manifest_file = (
        out_file.with_suffix(".manifest.json")
        if out_file.suffix.lower() == ".json"
        else Path(f"{out_file}.manifest.json")
    )
    snapshot, manifest_base = build_forecasts_from_model(
        artifact=artifact,
        feature_table=feature_table,
        issued_at=issued_at,
        generated_at=generated_at,
        producer=producer,
        mode=mode,
        start_as_of=start_as_of,
        end_as_of=end_as_of,
        expected_model_sha256=expected_model_sha256,
        index_dir=index_dir,
        skip_already_indexed=skip_already_indexed,
    )
    manifest = {k: v for k, v in manifest_base.items() if k != "manifest_sha256"}
    manifest["snapshot_file"] = out_file.name
    manifest["manifest_sha256"] = sha256_ascii(manifest)

    atomic_publish_json_ascii(out_file, snapshot)
    atomic_publish_json_ascii(manifest_file, manifest)
    return snapshot, manifest, out_file, manifest_file


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, required=True, help="Frozen tradegen-direction-model-v1 JSON")
    parser.add_argument("--expected-model-sha256", help="Optional pinned model.sha256")
    parser.add_argument("--features", type=Path, required=True, help="tradegen-direction-features-v1 JSON")
    parser.add_argument("--mode", choices=["batch", "live"], default="batch")
    parser.add_argument("--producer", default="tradegen-research")
    parser.add_argument("--issued-at", type=int, help="Explicit write epoch seconds (defaults to current UTC second)")
    parser.add_argument("--start-as-of", type=int)
    parser.add_argument("--end-as-of", type=int)
    parser.add_argument("--index-dir", type=Path, help="Optional persistent non-revision key index directory")
    parser.add_argument("--skip-already-indexed", action="store_true")
    parser.add_argument("--output", type=Path, required=True, help="New snapshot .json path (sidecar .manifest.json written alongside)")
    args = parser.parse_args(argv)

    now_ts = int(time.time()) if args.issued_at is None else args.issued_at
    try:
        artifact = dmf.read_model_artifact(args.model, args.expected_model_sha256)
        ftable = dfb.read_feature_table(args.features)
        _snap, manifest, _out_f, _man_f = write_forecast_snapshot(
            args.output,
            artifact=artifact,
            feature_table=ftable,
            issued_at=now_ts,
            producer=args.producer,
            mode=args.mode,
            start_as_of=args.start_as_of,
            end_as_of=args.end_as_of,
            expected_model_sha256=args.expected_model_sha256,
            index_dir=args.index_dir,
            skip_already_indexed=args.skip_already_indexed,
        )
        print(canonical_ascii_str(manifest))
        return 0
    except StudyError as exc:
        reason = str(exc)
    except (OSError, ValueError, TypeError, KeyError):
        reason = "FORECAST_WRITE_REFUSED"
    print(canonical_ascii_str({**RESEARCH_FLAGS, "reason": reason}))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
