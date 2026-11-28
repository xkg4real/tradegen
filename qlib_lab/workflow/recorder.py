"""Zero-pickle FileGovernanceRecorder & Experiment context manager (`R`).

All file writes pass through `core.isolation.checked_target`.
Objects are serialized strictly as JSON, FrozenModelSpec JSON, or compressed NumPy `.npz` (`allow_pickle=False`).
"""
from __future__ import annotations

from collections.abc import Mapping
from contextlib import contextmanager
import hashlib
import json
import math
from pathlib import Path
import re
import threading
from typing import Any

import numpy as np
import pandas as pd

from core.isolation import checked_target, refuse_quantgen, scan_links
from core.quant.gate_ledger import repo_anchor
from qlib_lab import RESEARCH_FLAGS, canonical_sha256, sha256_hex
from qlib_lab.exceptions import SecurityRefusalError
from qlib_lab.expression.ast_nodes import _to_utc_timestamps
from qlib_lab.models.base import FrozenModelSpec, Model

_SAFE_NAME_RE = re.compile(r"^[A-Za-z0-9_.-]{1,128}$")
DEFAULT_PINNED_UTC = "1970-01-01T00:00:00Z"


def _clean_identifier(value: str, what: str) -> str:
    s = str(value).strip().replace(" ", "_")
    if not _SAFE_NAME_RE.fullmatch(s) or s in (".", ".."):
        raise ValueError(f"Invalid {what} identifier {value!r}; use [A-Za-z0-9_.-]")
    return s


def _json_clean(obj: Any) -> Any:
    if isinstance(obj, Mapping):
        return {str(k): _json_clean(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_json_clean(v) for v in obj]
    if isinstance(obj, np.ndarray):
        return _json_clean(obj.tolist())
    if isinstance(obj, (np.bool_, bool)):
        return bool(obj)
    if isinstance(obj, (np.integer, int)):
        return int(obj)
    if isinstance(obj, (np.floating, float)):
        f = float(obj)
        return f if math.isfinite(f) else None
    if obj is None or isinstance(obj, str):
        return obj
    return str(obj)


class FileGovernanceRecorder:
    """Zero-pickle filesystem experiment recorder backed by checked_target."""

    STATUS_S = "SCHEDULED"
    STATUS_R = "RUNNING"
    STATUS_FI = "FINISHED"
    STATUS_FA = "FAILED"

    def __init__(
        self,
        root_dir: Path,
        experiment_name: str,
        recorder_id: str,
        name: str | None = None,
        run_utc: str = DEFAULT_PINNED_UTC,
    ) -> None:
        refuse_quantgen(root_dir, "recorder_root")
        scan_links(root_dir)
        self.root_dir = Path(root_dir)
        self.experiment_name = _clean_identifier(experiment_name, "experiment_name")
        self.id = _clean_identifier(recorder_id, "recorder_id")
        self.name = _clean_identifier(name or recorder_id, "recorder_name")
        self.run_utc = str(run_utc)

        self.run_dir = checked_target(
            self.root_dir / "experiments" / self.experiment_name / self.id,
            "recorder_run_dir",
            within=self.root_dir,
        )
        self.artifacts_dir = checked_target(self.run_dir / "artifacts", "recorder_artifacts_dir", within=self.root_dir)

        self.status = self.STATUS_S
        self.start_utc: str | None = None
        self.end_utc: str | None = None
        self._params: dict[str, Any] = {}
        self._metrics: dict[str, Any] = {}
        self._tags: dict[str, Any] = {}
        self._artifact_hashes: dict[str, str] = {}

        if (self.run_dir / "meta.json").is_file():
            self._load_existing_metadata()

    def _load_existing_metadata(self) -> None:
        meta = json.loads(checked_target(self.run_dir / "meta.json", "meta", within=self.root_dir).read_text(encoding="utf-8"))
        self.status = str(meta.get("status", self.STATUS_S))
        self.start_utc = meta.get("start_utc")
        self.end_utc = meta.get("end_utc")
        self._artifact_hashes = dict(meta.get("artifact_hashes") or {})
        for fname, attr in (("params.json", "_params"), ("metrics.json", "_metrics"), ("tags.json", "_tags")):
            fp = self.run_dir / fname
            if fp.is_file():
                setattr(self, attr, json.loads(checked_target(fp, fname, within=self.root_dir).read_text(encoding="utf-8")))

    def _write_json(self, path: Path, payload: Mapping[str, Any]) -> str:
        target = checked_target(path, path.name, within=self.root_dir)
        target.parent.mkdir(parents=True, exist_ok=True)
        cleaned = _json_clean(payload)
        raw = (json.dumps(cleaned, sort_keys=True, ensure_ascii=True, indent=2, allow_nan=False) + "\n").encode("ascii")
        target.write_bytes(raw)
        return sha256_hex(raw)

    def _flush_meta(self) -> None:
        meta = {
            "schema": "tradegen-qlib-recorder-meta-v1",
            "experiment_name": self.experiment_name,
            "recorder_id": self.id,
            "name": self.name,
            "status": self.status,
            "start_utc": self.start_utc,
            "end_utc": self.end_utc,
            "git_anchor": repo_anchor(),
            "artifact_hashes": dict(sorted(self._artifact_hashes.items())),
            "research_flags": dict(RESEARCH_FLAGS),
            **RESEARCH_FLAGS,
        }
        self._write_json(self.run_dir / "meta.json", meta)

    @property
    def info(self) -> dict[str, Any]:
        return {
            "class": "FileGovernanceRecorder",
            "id": self.id,
            "name": self.name,
            "experiment_name": self.experiment_name,
            "start_utc": self.start_utc,
            "end_utc": self.end_utc,
            "status": self.status,
            **RESEARCH_FLAGS,
        }

    def start_run(self, start_utc: str | None = None) -> FileGovernanceRecorder:
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        self.status = self.STATUS_R
        self.start_utc = str(start_utc or self.run_utc)
        self._flush_meta()
        return self

    def end_run(self, status: str = STATUS_FI, end_utc: str | None = None) -> None:
        if status not in (self.STATUS_S, self.STATUS_R, self.STATUS_FI, self.STATUS_FA):
            raise ValueError(f"Unsupported recorder status {status!r}")
        self.status = status
        self.end_utc = str(end_utc or self.start_utc or self.run_utc)
        self._flush_meta()

    def log_params(self, **kwargs: Any) -> None:
        self._params.update(_json_clean(kwargs))
        self._write_json(self.run_dir / "params.json", self._params)
        self._flush_meta()

    def log_metrics(self, step: int | None = None, **kwargs: Any) -> None:
        clean_m = _json_clean(kwargs)
        if step is None:
            self._metrics.update(clean_m)
        else:
            step_bucket = self._metrics.setdefault("_steps", {})
            step_bucket[str(int(step))] = clean_m
            self._metrics.update(clean_m)
        self._write_json(self.run_dir / "metrics.json", self._metrics)
        self._flush_meta()

    def set_tags(self, **kwargs: Any) -> None:
        self._tags.update(_json_clean(kwargs))
        self._write_json(self.run_dir / "tags.json", self._tags)
        self._flush_meta()

    def list_params(self) -> dict[str, Any]:
        return dict(self._params)

    def list_metrics(self) -> dict[str, Any]:
        return dict(self._metrics)

    def list_tags(self) -> dict[str, Any]:
        return dict(self._tags)

    def list_artifacts(self) -> list[str]:
        if not self.artifacts_dir.is_dir():
            return []
        return sorted(p.name for p in self.artifacts_dir.iterdir() if p.is_file())

    def _save_single_object(self, name: str, obj: Any) -> None:
        safe = _clean_identifier(name, "artifact_name")
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)

        if isinstance(obj, FrozenModelSpec):
            target = checked_target(self.artifacts_dir / f"{safe}.model.json", safe, within=self.root_dir)
            obj.save(target)
            self._artifact_hashes[f"{safe}.model.json"] = sha256_hex(target.read_bytes())
            return

        if isinstance(obj, Model):
            spec = obj.to_frozen_spec(model_name=safe)
            target = checked_target(self.artifacts_dir / f"{safe}.model.json", safe, within=self.root_dir)
            spec.save(target)
            self._artifact_hashes[f"{safe}.model.json"] = sha256_hex(target.read_bytes())
            return

        if isinstance(obj, (pd.DataFrame, pd.Series)):
            is_series = isinstance(obj, pd.Series)
            df = obj.to_frame(name=str(obj.name or "value")) if is_series else obj
            npz_path = checked_target(self.artifacts_dir / f"{safe}.npz", safe, within=self.root_dir)
            schema_path = checked_target(self.artifacts_dir / f"{safe}.npz.schema.json", safe, within=self.root_dir)

            values = np.ascontiguousarray(df.to_numpy(dtype=np.float64))
            with npz_path.open("wb") as fh:
                np.savez_compressed(fh, values=values)
            npz_sha = sha256_hex(npz_path.read_bytes())

            if isinstance(df.index, pd.MultiIndex):
                idx_levels = []
                for lvl in range(df.index.nlevels):
                    lvl_vals = df.index.get_level_values(lvl)
                    if isinstance(lvl_vals, pd.DatetimeIndex):
                        idx_levels.append(_to_utc_timestamps(lvl_vals).strftime("%Y-%m-%dT%H:%M:%SZ").tolist())
                    else:
                        idx_levels.append([str(x) for x in lvl_vals.tolist()])
                idx_meta = {
                    "multi": True,
                    "names": [str(n or f"level_{i}") for i, n in enumerate(df.index.names)],
                    "levels": idx_levels,
                }
            else:
                if isinstance(df.index, pd.DatetimeIndex):
                    vals_1d = _to_utc_timestamps(df.index).strftime("%Y-%m-%dT%H:%M:%SZ").tolist()
                    idx_kind = "datetime"
                else:
                    vals_1d = [str(x) for x in df.index.tolist()]
                    idx_kind = "str"
                idx_meta = {"multi": False, "name": str(df.index.name or ""), "kind": idx_kind, "values": vals_1d}

            if isinstance(df.columns, pd.MultiIndex):
                col_meta = {"multi": True, "tuples": [[str(x) for x in tup] for tup in df.columns.tolist()]}
            else:
                col_meta = {"multi": False, "names": [str(c) for c in df.columns.tolist()]}

            schema_obj = {
                "schema": "tradegen-qlib-npz-frame-v1",
                "kind": "series" if is_series else "dataframe",
                "series_name": str(obj.name or "score") if is_series else None,
                "npz_sha256": npz_sha,
                "index": idx_meta,
                "columns": col_meta,
                "research_flags": dict(RESEARCH_FLAGS),
                **RESEARCH_FLAGS,
            }
            schema_sha = self._write_json(schema_path, schema_obj)
            self._artifact_hashes[npz_path.name] = npz_sha
            self._artifact_hashes[schema_path.name] = schema_sha
            return

        if isinstance(obj, np.ndarray):
            arr = np.ascontiguousarray(obj)
            if arr.dtype.hasobject:
                raise SecurityRefusalError("Object-dtype ndarray is forbidden in FileGovernanceRecorder (zero pickle)")
            npz_path = checked_target(self.artifacts_dir / f"{safe}.npz", safe, within=self.root_dir)
            schema_path = checked_target(self.artifacts_dir / f"{safe}.npz.schema.json", safe, within=self.root_dir)
            with npz_path.open("wb") as fh:
                np.savez_compressed(fh, values=arr)
            npz_sha = sha256_hex(npz_path.read_bytes())
            schema_sha = self._write_json(
                schema_path,
                {
                    "schema": "tradegen-qlib-npz-frame-v1",
                    "kind": "ndarray",
                    "dtype": str(arr.dtype),
                    "shape": list(arr.shape),
                    "npz_sha256": npz_sha,
                    "research_flags": dict(RESEARCH_FLAGS),
                    **RESEARCH_FLAGS,
                },
            )
            self._artifact_hashes[npz_path.name] = npz_sha
            self._artifact_hashes[schema_path.name] = schema_sha
            return

        if isinstance(obj, (Mapping, list, tuple)):
            json_path = checked_target(self.artifacts_dir / f"{safe}.json", safe, within=self.root_dir)
            payload: Any
            if isinstance(obj, Mapping):
                payload = {**_json_clean(obj), "research_flags": dict(RESEARCH_FLAGS), **RESEARCH_FLAGS}
            else:
                payload = {"items": _json_clean(list(obj)), "research_flags": dict(RESEARCH_FLAGS), **RESEARCH_FLAGS}
            digest = self._write_json(json_path, payload)
            self._artifact_hashes[json_path.name] = digest
            return

        raise SecurityRefusalError(
            f"Unsupported artifact type {type(obj).__name__} for {safe!r}; arbitrary object serialization is refused"
        )

    def save_objects(self, **kwargs: Any) -> None:
        for name, obj in kwargs.items():
            self._save_single_object(name, obj)
        self._flush_meta()

    def load_object(self, name: str, *, trusted: bool = False) -> Any:
        """Load a saved artifact strictly via JSON or `np.load(..., allow_pickle=False)`."""
        if trusted:
            raise SecurityRefusalError(
                "trusted=True (unrestricted object deserialization) is permanently forbidden in qlib_lab"
            )
        safe = _clean_identifier(name[:-5] if name.endswith(".json") else name, "artifact_name")

        model_path = self.artifacts_dir / f"{safe}.model.json"
        if model_path.is_file():
            checked = checked_target(model_path, safe, within=self.root_dir)
            return Model.from_frozen_spec(checked)

        npz_path = self.artifacts_dir / f"{safe}.npz"
        schema_path = self.artifacts_dir / f"{safe}.npz.schema.json"
        if npz_path.is_file() and schema_path.is_file():
            checked_npz = checked_target(npz_path, safe, within=self.root_dir)
            checked_sch = checked_target(schema_path, safe, within=self.root_dir)
            sch = json.loads(checked_sch.read_text(encoding="utf-8"))
            if sch.get("npz_sha256") != sha256_hex(checked_npz.read_bytes()):
                raise SecurityRefusalError(f"NPZ SHA-256 mismatch for artifact {safe!r}")
            with np.load(checked_npz, allow_pickle=False) as archive:
                vals = archive["values"].copy()

            kind = sch.get("kind")
            if kind == "ndarray":
                return vals

            idx_info = sch["index"]
            if idx_info["multi"]:
                arrays = []
                for nm, lvl_list in zip(idx_info["names"], idx_info["levels"]):
                    if nm == "datetime":
                        arrays.append(_to_utc_timestamps(pd.Index(lvl_list)))
                    else:
                        arrays.append(pd.Index(lvl_list, dtype=object))
                index = pd.MultiIndex.from_arrays(arrays, names=idx_info["names"])
            else:
                if idx_info.get("kind") == "datetime":
                    index = _to_utc_timestamps(pd.Index(idx_info["values"]))
                    index.name = idx_info["name"] or None
                else:
                    index = pd.Index(idx_info["values"], name=idx_info["name"] or None)

            if kind == "series":
                return pd.Series(vals.ravel(), index=index, name=sch.get("series_name") or "score")

            col_info = sch["columns"]
            if col_info["multi"]:
                cols = pd.MultiIndex.from_tuples([tuple(t) for t in col_info["tuples"]])
            else:
                cols = pd.Index(col_info["names"])
            return pd.DataFrame(vals, index=index, columns=cols)

        json_path = self.artifacts_dir / f"{safe}.json"
        if json_path.is_file():
            checked_json = checked_target(json_path, safe, within=self.root_dir)
            return json.loads(checked_json.read_text(encoding="utf-8"))

        raise FileNotFoundError(f"Artifact {name!r} not found in recorder {self.id}")


class WorkflowManager:
    """Thread-safe Qlib-style `R` workflow context manager with explicit URI isolation."""

    def __init__(self) -> None:
        self._tls = threading.local()
        self._default_uri: Path | None = None
        self._counter_lock = threading.Lock()
        self._counter = 0

    def set_uri(self, uri: Path | str) -> Path:
        p = Path(uri)
        refuse_quantgen(p, "workflow_uri")
        scan_links(p)
        self._default_uri = p
        return p

    def get_uri(self, explicit_uri: Path | str | None = None) -> Path:
        target = Path(explicit_uri) if explicit_uri is not None else self._default_uri
        if target is None:
            raise RuntimeError(
                "Workflow URI is not set; pass `uri=<temp_or_explicit_dir>` to R.start() or call R.set_uri(...) "
                "(qlib_lab never defaults to ~/.tradegen or ~/.nextgen)"
            )
        refuse_quantgen(target, "workflow_uri")
        scan_links(target)
        return target

    def _next_recorder_id(self, experiment_name: str, recorder_name: str | None, root: Path) -> str:
        with self._counter_lock:
            self._counter += 1
            seq = self._counter
        exp_dir = root / "experiments" / _clean_identifier(experiment_name, "experiment_name")
        existing = len(list(exp_dir.iterdir())) if exp_dir.is_dir() else 0
        seed_str = f"{experiment_name}:{recorder_name or 'run'}:{existing + 1}:{seq}"
        short_hash = hashlib.sha256(seed_str.encode("ascii")).hexdigest()[:12]
        return f"rec_{existing + 1:04d}_{short_hash}"

    @contextmanager
    def start(
        self,
        *,
        experiment_name: str = "default_exp",
        recorder_name: str | None = None,
        recorder_id: str | None = None,
        uri: Path | str | None = None,
        run_utc: str = DEFAULT_PINNED_UTC,
    ):
        root = self.get_uri(uri)
        rid = recorder_id or self._next_recorder_id(experiment_name, recorder_name, root)
        rec = FileGovernanceRecorder(
            root_dir=root,
            experiment_name=experiment_name,
            recorder_id=rid,
            name=recorder_name,
            run_utc=run_utc,
        )
        stack: list[FileGovernanceRecorder] = getattr(self._tls, "stack", [])
        stack.append(rec)
        self._tls.stack = stack
        rec.start_run(start_utc=run_utc)
        try:
            yield rec
        except Exception:
            rec.end_run(status=FileGovernanceRecorder.STATUS_FA, end_utc=run_utc)
            raise
        else:
            rec.end_run(status=FileGovernanceRecorder.STATUS_FI, end_utc=run_utc)
        finally:
            stack.pop()

    def get_recorder(
        self,
        *,
        recorder_id: str | None = None,
        experiment_name: str = "default_exp",
        uri: Path | str | None = None,
    ) -> FileGovernanceRecorder:
        if recorder_id is None:
            stack: list[FileGovernanceRecorder] = getattr(self._tls, "stack", [])
            if not stack:
                raise RuntimeError("No active recorder in current context; use `with R.start(...):`")
            return stack[-1]
        root = self.get_uri(uri)
        return FileGovernanceRecorder(root_dir=root, experiment_name=experiment_name, recorder_id=recorder_id)

    def log_params(self, **kwargs: Any) -> None:
        self.get_recorder().log_params(**kwargs)

    def log_metrics(self, step: int | None = None, **kwargs: Any) -> None:
        self.get_recorder().log_metrics(step=step, **kwargs)

    def set_tags(self, **kwargs: Any) -> None:
        self.get_recorder().set_tags(**kwargs)

    def save_objects(self, **kwargs: Any) -> None:
        self.get_recorder().save_objects(**kwargs)

    def load_object(self, name: str, *, trusted: bool = False) -> Any:
        return self.get_recorder().load_object(name, trusted=trusted)


R = WorkflowManager()
