"""One-click `tradegen-direction-forecast-v1` Snapshot + Manifest + Interface Note Exporter.

Self-verifies every written snapshot through `tools.research.direction_forecast_adapter.check_snapshot`
and `read_snapshot`, enforces 6-decimal exact-sum-1 rounding, omits rounded ties, and maintains an
append-only non-revision index preventing conflicting forecasts for `(model_sha256, market, as_of, horizon_seconds)`.
"""
from __future__ import annotations

from collections.abc import Mapping
from contextlib import contextmanager
from decimal import Decimal, ROUND_HALF_UP
import json
import math
import os
from pathlib import Path
import re
from typing import Any

import numpy as np
import pandas as pd

from core.isolation import checked_target, refuse_quantgen
from qlib_lab import RESEARCH_FLAGS, canonical_json_ascii, sha256_hex
from qlib_lab.data.labels import DIRECTION_CLASSES
from qlib_lab.exceptions import SnapshotContractError
from qlib_lab.expression.ast_nodes import _epoch_seconds_array, _to_utc_timestamps
from qlib_lab.models.base import FrozenModelSpec
from tools.research import adaptive_bid_gap_preview as br26_preview
from tools.research import direction_forecast_adapter as br26_adapter
from tools.research._study_common import StudyError, atomic_publish_bytes

QUANT_6 = Decimal("0.000001")
ONE_DEC = Decimal("1.000000")
ZERO_DEC = Decimal("0.000000")
DISCLAIMER_KO = "법률, 세무, 투자 조언이 아니며 면허를 가진 자문가가 아니다"


def format_exact_probabilities(
    p_up: float,
    p_down: float,
    p_neutral: float,
) -> tuple[dict[str, str], str] | None:
    """Round probabilities to 6 decimal strings summing to exact 1 (`Decimal`), or None on argmax tie."""
    vals = np.asarray([p_up, p_down, p_neutral], dtype=np.float64)
    if not np.all(np.isfinite(vals)) or np.any(vals < -1e-9):
        raise SnapshotContractError(f"Invalid raw probabilities: {vals.tolist()}")
    vals = np.clip(vals, 0.0, None)
    tot = float(vals.sum())
    if tot <= 0.0:
        raise SnapshotContractError("Probabilities sum to zero")
    vals /= tot

    d_up = Decimal(f"{vals[0]:.12f}").quantize(QUANT_6, rounding=ROUND_HALF_UP)
    d_down = Decimal(f"{vals[1]:.12f}").quantize(QUANT_6, rounding=ROUND_HALF_UP)
    d_up = min(ONE_DEC, max(ZERO_DEC, d_up))
    d_down = min(ONE_DEC, max(ZERO_DEC, d_down))

    if d_up + d_down > ONE_DEC:
        overflow = (d_up + d_down) - ONE_DEC
        if d_up >= d_down:
            d_up -= overflow
        else:
            d_down -= overflow

    d_neutral = ONE_DEC - d_up - d_down
    dec_map = {"up": d_up, "down": d_down, "neutral": d_neutral}
    if sum(dec_map.values()) != Decimal("1"):
        raise SnapshotContractError("Internal Decimal rounding failed exact sum == 1")

    top = max(dec_map.values())
    winners = [cls for cls in DIRECTION_CLASSES if dec_map[cls] == top]
    if len(winners) != 1:
        # Contract §2 & Study Design §5: if highest class is tied after 6-decimal rounding, omit forecast!
        return None

    str_map = {cls: format(dec_map[cls], "f") for cls in DIRECTION_CLASSES}
    return str_map, winners[0]


@contextmanager
def _index_lock(path: Path):
    # The lock file stays in place so all exporters lock the same inode across runs.
    lock_path = checked_target(path.with_name(path.name + ".lock"), "forecast_index_lock")
    with lock_path.open("a+b") as lock:
        if os.name == "nt":
            import msvcrt
            lock.seek(0)
            msvcrt.locking(lock.fileno(), msvcrt.LK_LOCK, 1)
        else:
            import fcntl
            fcntl.flock(lock, fcntl.LOCK_EX)
        yield  # closing the descriptor releases the lock, including on error


def _publish(path: Path, data: bytes) -> None:
    try:
        atomic_publish_bytes(path, data)
    except StudyError as exc:
        if str(exc) != "OUTPUT_EXISTS" or path.read_bytes() != data:
            raise SnapshotContractError(f"Cannot publish immutable forecast file {path.name}") from exc


class NonRevisionIndex:
    """Append-only JSONL ledger enforcing Contract §3 Rule 3: first forecast for (model_sha256, market, as_of, horizon_seconds) stands."""

    def __init__(self, index_path: Path) -> None:
        self.path = checked_target(Path(index_path), "non_revision_index")

    def _read(self):
        records = {}
        if self.path.is_file():
            for line_no, raw in enumerate(self.path.read_text(encoding="utf-8").splitlines(), start=1):
                if not raw.strip():
                    continue
                row = json.loads(raw)
                key = (
                    str(row["model_sha256"]),
                    str(row["market"]),
                    int(row["as_of"]),
                    int(row["horizon_seconds"]),
                )
                if records.setdefault(key, row["forecast"]) != row["forecast"]:
                    raise SnapshotContractError("FORECAST_REVISED: conflicting records in existing index")
        return records

    def check_and_commit(self, model_sha256: str, forecasts: list[dict[str, Any]]) -> int:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with _index_lock(self.path):
            return self._commit(model_sha256, forecasts, self._read())

    def _commit(self, model_sha256, forecasts, records) -> int:
        to_append: list[dict[str, Any]] = []
        pending_seen: dict[tuple[str, str, int, int], dict[str, Any]] = {}

        for fc in forecasts:
            key = (str(model_sha256), str(fc["market"]), int(fc["as_of"]), int(fc["horizon_seconds"]))
            if key in records and records[key] != fc:
                raise SnapshotContractError(
                    f"FORECAST_REVISED: conflicting forecast for key={key} against previously exported snapshot"
                )
            if key in pending_seen and pending_seen[key] != fc:
                raise SnapshotContractError(
                    f"FORECAST_REVISED: duplicate conflicting forecast for key={key} within same snapshot"
                )
            if key not in records and key not in pending_seen:
                pending_seen[key] = fc
                to_append.append(
                    {
                        "model_sha256": str(model_sha256),
                        "market": str(fc["market"]),
                        "as_of": int(fc["as_of"]),
                        "horizon_seconds": int(fc["horizon_seconds"]),
                        "forecast": fc,
                    }
                )

        if to_append:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            checked_target(self.path, "non_revision_index")
            lines = "".join(canonical_json_ascii(item) + "\n" for item in to_append).encode("ascii")
            with self.path.open("ab") as fh:
                fh.write(lines)
                fh.flush()
                os.fsync(fh.fileno())
        return len(to_append)


class SnapshotExporter:
    """Exports FrozenModelSpec + probabilities into verified `tradegen-direction-forecast-v1` + sidecars."""

    def __init__(
        self,
        *,
        producer: str = "qlib-lab",
        horizon_seconds: int = 7200,
        hurdle_bps: int = 10,
        index_path: Path | None = None,
    ) -> None:
        if not re.fullmatch(r"[a-z0-9-]{1,64}", producer):
            raise SnapshotContractError(f"Invalid producer name {producer!r}; must match [a-z0-9-]{{1,64}}")
        if not (60 <= int(horizon_seconds) <= 2_592_000):
            raise SnapshotContractError("horizon_seconds must lie in [60, 2592000]")
        if not (0 <= int(hurdle_bps) <= 9999):
            raise SnapshotContractError("hurdle_bps must lie in [0, 9999]")

        self.producer = producer
        self.horizon_seconds = int(horizon_seconds)
        self.hurdle_bps = int(hurdle_bps)
        self.index_path = Path(index_path) if index_path is not None else None

    def _render_interface_note(
        self,
        *,
        snapshot: Mapping[str, Any],
        frozen_spec: FrozenModelSpec,
        markets: list[str],
    ) -> str:
        model_block = snapshot["model"]
        return (
            "# Direction Forecast Producer Interface Note (`qlib_lab`, research only)\n\n"
            "1. **Format & Version**: `tradegen-direction-forecast-v1` (exact schema of `docs/direction-forecast-contract.md` §2).\n"
            "2. **Timestamp Semantics**: `as_of` is the integer UTC bar-close information cutoff (`known_at <= as_of`); "
            "`issued_at` (`as_of <= issued_at <= generated_at`) is the separate forecast materialization timestamp.\n"
            f"3. **Markets, Horizon & Hurdle**: Markets `{', '.join(markets)}`; `horizon_seconds = {self.horizon_seconds}` "
            f"over `(as_of, as_of + horizon_seconds]`; `hurdle_bps = {self.hurdle_bps}` (net of round-trip fees, spread, and slippage allowance).\n"
            "4. **Probability Classes**: `up`, `down`, and `neutral` as 6-decimal ASCII strings summing to exact `1` in `Decimal` arithmetic; rounded argmax ties are omitted.\n"
            f"5. **Pinned Model Identity**: `name={model_block['name']}`, `version={model_block['version']}`, "
            f"`sha256={model_block['sha256']}`, `training_cutoff={model_block['training_cutoff']}`, `frozen_at={model_block['frozen_at']}`.\n"
            f"6. **Published Snapshot Digest & Offline Delivery**: `snapshot_sha256 = {snapshot['snapshot_sha256']}` "
            f"(`{len(snapshot['forecasts'])}` forecasts, `generated_at = {snapshot['generated_at']}`). Delivered strictly via local filesystem paths with zero network or runtime coupling.\n"
            f"7. **Public-Note Hygiene**: Contains zero model weights (`{len(frozen_spec.feature_names)}` feature columns private), zero prompts, zero private terms, and zero credentials.\n\n"
            f"{DISCLAIMER_KO}\n"
        )

    def export(
        self,
        *,
        frozen_spec: FrozenModelSpec,
        probabilities: pd.DataFrame,
        output_path: Path,
        generated_at: int | None = None,
        issued_at_by_row: Mapping[Any, int] | None = None,
        exclude_in_sample: bool = True,
    ) -> dict[str, Any]:
        """Write `<stem>.json`, `<stem>.manifest.json`, and `<stem>.interface_note.md`, self-verified via adapter."""
        if type(generated_at) is not int or generated_at < frozen_spec.frozen_at:
            raise SnapshotContractError("An explicit snapshot write time at or after the model freeze is required")
        out_file = checked_target(Path(output_path), "snapshot_json")
        if out_file.suffix.lower() != ".json":
            raise SnapshotContractError("Snapshot output_path must end with '.json'")
        out_dir = out_file.parent
        refuse_quantgen(out_dir, "snapshot_export_dir")
        out_dir.mkdir(parents=True, exist_ok=True)

        if not isinstance(probabilities.index, pd.MultiIndex) or probabilities.index.nlevels != 2:
            raise SnapshotContractError("probabilities DataFrame must have MultiIndex(['datetime', 'instrument'])")

        proba_sorted = probabilities.sort_index()
        dts_utc = _to_utc_timestamps(proba_sorted.index.get_level_values("datetime"))
        as_of_epochs = _epoch_seconds_array(dts_utc).astype(np.int64)
        insts = proba_sorted.index.get_level_values("instrument").astype(str).tolist()
        p_mat = proba_sorted[list(DIRECTION_CLASSES)].to_numpy(dtype=np.float64)

        forecasts: list[dict[str, Any]] = []
        omitted_nan = 0
        omitted_ties = 0
        omitted_insample = 0
        seen_in_file: set[tuple[str, int, int]] = set()
        markets_set: set[str] = set()

        for i in range(len(proba_sorted)):
            mkt = insts[i]
            if not re.fullmatch(br26_adapter.MARKET, mkt):
                raise SnapshotContractError(f"Market {mkt!r} does not match contract pattern {br26_adapter.MARKET!r}")
            as_of_ep = int(as_of_epochs[i])
            if exclude_in_sample and as_of_ep <= frozen_spec.frozen_at:
                omitted_insample += 1
                continue
            row_p = p_mat[i]
            if not np.all(np.isfinite(row_p)):
                omitted_nan += 1
                continue

            formatted = format_exact_probabilities(float(row_p[0]), float(row_p[1]), float(row_p[2]))
            if formatted is None:
                omitted_ties += 1
                continue
            prob_strs, direction = formatted

            row_key = proba_sorted.index[i]
            issued_ep = generated_at if issued_at_by_row is None else issued_at_by_row.get(row_key)
            if type(issued_ep) is not int:
                raise SnapshotContractError("A recorded issue time is required for each exported row")

            if issued_ep < as_of_ep:
                raise SnapshotContractError(f"issued_at ({issued_ep}) < as_of ({as_of_ep})")

            dedup_k = (mkt, as_of_ep, self.horizon_seconds)
            if dedup_k in seen_in_file:
                raise SnapshotContractError(f"Duplicate (market, as_of, horizon_seconds) row in probabilities: {dedup_k}")
            seen_in_file.add(dedup_k)
            markets_set.add(mkt)

            forecasts.append(
                {
                    "market": mkt,
                    "as_of": as_of_ep,
                    "issued_at": issued_ep,
                    "horizon_seconds": self.horizon_seconds,
                    "hurdle_bps": self.hurdle_bps,
                    "probabilities": prob_strs,
                    "direction": direction,
                }
            )

        if len(forecasts) > br26_adapter.MAX_FORECASTS:
            raise SnapshotContractError(f"Forecast count {len(forecasts)} exceeds MAX_FORECASTS={br26_adapter.MAX_FORECASTS}")

        max_issued = max((fc["issued_at"] for fc in forecasts), default=frozen_spec.frozen_at)
        gen_ep = generated_at
        if gen_ep < max_issued:
            raise SnapshotContractError(f"generated_at ({gen_ep}) < max(issued_at) ({max_issued})")

        model_header = {
            "name": frozen_spec.model_name,
            "version": frozen_spec.model_version,
            "sha256": frozen_spec.model_sha256,
            "training_cutoff": int(frozen_spec.training_cutoff),
            "frozen_at": int(frozen_spec.frozen_at),
        }
        body = {
            "format": br26_adapter.FORMAT,
            "producer": self.producer,
            "model": model_header,
            "generated_at": gen_ep,
            "forecasts": forecasts,
        }
        snap_sha = br26_preview.model_id(body)
        snapshot = {**body, "snapshot_sha256": snap_sha}

        br26_adapter.check_snapshot(snapshot)

        raw_bytes = (canonical_json_ascii(snapshot) + "\n").encode("ascii")
        if len(raw_bytes) > br26_adapter.MAX_BYTES:
            raise SnapshotContractError("Snapshot exceeds the adapter file size limit")

        note_path = checked_target(out_file.with_suffix(".interface_note.md"), "interface_note", within=out_dir)
        note_text = self._render_interface_note(
            snapshot=snapshot,
            frozen_spec=frozen_spec,
            markets=sorted(markets_set) or ["KRW-BTC"],
        )
        note_bytes = note_text.encode("utf-8")

        manifest_path = checked_target(out_file.with_suffix(".manifest.json"), "snapshot_manifest", within=out_dir)
        manifest = {
            "schema": "tradegen-direction-forecast-manifest-v1",
            "snapshot_file": out_file.name,
            "snapshot_sha256": snap_sha,
            "interface_note_file": note_path.name,
            "interface_note_sha256": sha256_hex(note_bytes),
            "model_sha256": frozen_spec.model_sha256,
            "model_class": frozen_spec.model_class,
            "upstream_identities": frozen_spec.upstream_identities,
            "counts": {
                "exported_forecasts": len(forecasts),
                "omitted_ties": omitted_ties,
                "omitted_nan": omitted_nan,
                "omitted_in_sample": omitted_insample,
            },
            "research_flags": dict(RESEARCH_FLAGS),
            **RESEARCH_FLAGS,
        }
        manifest_bytes = (json.dumps(manifest, sort_keys=True, ensure_ascii=True, indent=2, allow_nan=False) + "\n").encode("ascii")
        outputs = ((out_file, raw_bytes), (note_path, note_bytes), (manifest_path, manifest_bytes))
        index_path = self.index_path or (out_dir / "non_revision_index.jsonl")
        index = NonRevisionIndex(index_path)
        index.path.parent.mkdir(parents=True, exist_ok=True)
        with _index_lock(index.path):
            for path, payload in outputs:
                if path.exists() and path.read_bytes() != payload:
                    raise SnapshotContractError(f"Forecast file {path.name} already contains different evidence")
            newly_indexed = index._commit(frozen_spec.model_sha256, forecasts, index._read())
            _publish(out_file, raw_bytes)
            br26_adapter.read_snapshot(out_file, snap_sha)
            _publish(note_path, note_bytes)
            _publish(manifest_path, manifest_bytes)

        return {
            "snapshot": snapshot,
            "snapshot_path": out_file,
            "snapshot_sha256": snap_sha,
            "manifest": manifest,
            "newly_indexed_keys": newly_indexed,
            "manifest_path": manifest_path,
            "interface_note_path": note_path,
            "research_flags": dict(RESEARCH_FLAGS),
            **RESEARCH_FLAGS,
        }
