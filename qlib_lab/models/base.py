"""Unified Model / ModelFT / Reweighter abstractions & zero-pickle FrozenModelSpec."""
from __future__ import annotations

import abc
from collections.abc import Mapping
from dataclasses import dataclass
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from core.isolation import checked_target
from qlib_lab import RESEARCH_FLAGS, canonical_json_ascii, canonical_sha256
from qlib_lab.data.dataset import DatasetH
from qlib_lab.data.handler import DataHandlerLP
from qlib_lab.exceptions import SecurityRefusalError
from qlib_lab.registry import get_registered_class, register_component

FROZEN_MODEL_SCHEMA = "tradegen-qlib-frozen-model-v1"


def _sanitize_json_tree(obj: Any) -> Any:
    """Validate and convert numpy scalars/arrays to strict finite JSON primitives."""
    if isinstance(obj, Mapping):
        return {str(k): _sanitize_json_tree(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_sanitize_json_tree(v) for v in obj]
    if isinstance(obj, np.ndarray):
        return _sanitize_json_tree(obj.tolist())
    if isinstance(obj, (np.bool_, bool)):
        return bool(obj)
    if isinstance(obj, (np.integer, int)):
        return int(obj)
    if isinstance(obj, (np.floating, float)):
        f = float(obj)
        if not math.isfinite(f):
            raise ValueError(f"Non-finite float {f!r} refused in FrozenModelSpec")
        return f
    if obj is None or isinstance(obj, str):
        return obj
    raise TypeError(f"Unsupported type {type(obj).__name__} in FrozenModelSpec")


class Reweighter(metaclass=abc.ABCMeta):
    """Sample reweighting interface for concept-drift and trajectory adaptation."""

    @abc.abstractmethod
    def reweight(self, df: pd.DataFrame) -> np.ndarray:
        """Compute non-negative 1D sample weights aligned to `df.index`."""


@register_component("reweighter")
class ArrayReweighter(Reweighter):
    """Explicit index-aligned sample weight wrapper (used internally by DoubleEnsemble SR)."""

    def __init__(self, weights: pd.Series | np.ndarray, index: pd.Index | None = None) -> None:
        if isinstance(weights, pd.Series):
            self._series = weights.astype(np.float64)
        else:
            arr = np.asarray(weights, dtype=np.float64).ravel()
            if index is None:
                raise ValueError("ArrayReweighter requires index when weights is an ndarray")
            self._series = pd.Series(arr, index=index, dtype=np.float64)

    def reweight(self, df: pd.DataFrame) -> np.ndarray:
        aligned = self._series.reindex(df.index).fillna(1.0).to_numpy(dtype=np.float64)
        return np.clip(aligned, 0.0, None)


@dataclass(frozen=True)
class FrozenModelSpec:
    """Canonical ASCII JSON frozen model artifact (`tradegen-qlib-frozen-model-v1`, zero pickle)."""

    schema: str
    model_class: str
    model_name: str
    model_version: str
    task_type: str
    feature_names: tuple[str, ...]
    hyperparams: dict[str, Any]
    weights: dict[str, Any]
    processor_states: dict[str, Any] | None
    upstream_identities: dict[str, Any]
    training_cutoff: int
    frozen_at: int
    parent_model_sha256: str | None
    research_flags: dict[str, bool]
    model_sha256: str

    @classmethod
    def build(
        cls,
        *,
        model_class: str,
        model_name: str,
        model_version: str,
        task_type: str,
        feature_names: list[str] | tuple[str, ...],
        hyperparams: Mapping[str, Any],
        weights: Mapping[str, Any],
        training_cutoff: int,
        frozen_at: int,
        processor_states: Mapping[str, Any] | None = None,
        upstream_identities: Mapping[str, Any] | None = None,
        parent_model_sha256: str | None = None,
    ) -> FrozenModelSpec:
        if not isinstance(model_name, str) or not (1 <= len(model_name) <= 128):
            raise ValueError("model_name must be 1..128 characters")
        if not isinstance(model_version, str) or not (1 <= len(model_version) <= 128):
            raise ValueError("model_version must be 1..128 characters")
        if task_type not in ("regression", "direction"):
            raise ValueError(f"task_type must be 'regression' or 'direction', got {task_type!r}")
        tc = int(training_cutoff)
        fa = int(frozen_at)
        if tc < 0 or fa < tc:
            raise ValueError(f"Require 0 <= training_cutoff ({tc}) <= frozen_at ({fa})")

        clean_hp = _sanitize_json_tree(dict(hyperparams))
        clean_w = _sanitize_json_tree(dict(weights))
        clean_ps = _sanitize_json_tree(dict(processor_states)) if processor_states is not None else None
        clean_up = _sanitize_json_tree(dict(upstream_identities or {}))
        feats = tuple(str(f) for f in feature_names)

        body = {
            "schema": FROZEN_MODEL_SCHEMA,
            "model_class": str(model_class),
            "model_name": model_name,
            "model_version": model_version,
            "task_type": task_type,
            "feature_names": list(feats),
            "hyperparams": clean_hp,
            "weights": clean_w,
            "processor_states": clean_ps,
            "upstream_identities": clean_up,
            "training_cutoff": tc,
            "frozen_at": fa,
            "parent_model_sha256": parent_model_sha256,
            "research_flags": dict(RESEARCH_FLAGS),
            **RESEARCH_FLAGS,
        }
        digest = canonical_sha256(body)
        return cls(
            schema=FROZEN_MODEL_SCHEMA,
            model_class=str(model_class),
            model_name=model_name,
            model_version=model_version,
            task_type=task_type,
            feature_names=feats,
            hyperparams=clean_hp,
            weights=clean_w,
            processor_states=clean_ps,
            upstream_identities=clean_up,
            training_cutoff=tc,
            frozen_at=fa,
            parent_model_sha256=parent_model_sha256,
            research_flags=dict(RESEARCH_FLAGS),
            model_sha256=digest,
        )

    def to_body_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "model_class": self.model_class,
            "model_name": self.model_name,
            "model_version": self.model_version,
            "task_type": self.task_type,
            "feature_names": list(self.feature_names),
            "hyperparams": self.hyperparams,
            "weights": self.weights,
            "processor_states": self.processor_states,
            "upstream_identities": self.upstream_identities,
            "training_cutoff": self.training_cutoff,
            "frozen_at": self.frozen_at,
            "parent_model_sha256": self.parent_model_sha256,
            "research_flags": dict(RESEARCH_FLAGS),
            **RESEARCH_FLAGS,
        }

    def to_dict(self) -> dict[str, Any]:
        out = self.to_body_dict()
        out["model_sha256"] = self.model_sha256
        return out

    def to_json(self, *, indent: int | None = 2) -> str:
        if indent is None:
            return canonical_json_ascii(self.to_dict())
        return json.dumps(self.to_dict(), sort_keys=True, ensure_ascii=True, indent=indent, allow_nan=False)

    def save(self, path: Path) -> Path:
        target = checked_target(path, "frozen_model_spec")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((self.to_json(indent=2) + "\n").encode("ascii"))
        return target

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> FrozenModelSpec:
        if not isinstance(payload, Mapping) or payload.get("schema") != FROZEN_MODEL_SCHEMA:
            raise SecurityRefusalError("Invalid FrozenModelSpec schema")
        for flag_k, flag_v in RESEARCH_FLAGS.items():
            if payload.get(flag_k) is not flag_v:
                raise SecurityRefusalError(f"FrozenModelSpec missing or altered research flag {flag_k!r}")
        if payload.get("research_flags") != RESEARCH_FLAGS:
            raise SecurityRefusalError("FrozenModelSpec research_flags block mismatch")

        expected_sha = payload.get("model_sha256")
        body = {k: v for k, v in payload.items() if k != "model_sha256"}
        computed_sha = canonical_sha256(body)
        if expected_sha != computed_sha:
            raise SecurityRefusalError(
                f"FrozenModelSpec SHA-256 mismatch: expected={expected_sha} vs computed={computed_sha}"
            )
        tc = int(payload["training_cutoff"])
        fa = int(payload["frozen_at"])
        if tc < 0 or fa < tc:
            raise SecurityRefusalError("FrozenModelSpec training_cutoff > frozen_at")

        return cls(
            schema=FROZEN_MODEL_SCHEMA,
            model_class=str(payload["model_class"]),
            model_name=str(payload["model_name"]),
            model_version=str(payload["model_version"]),
            task_type=str(payload["task_type"]),
            feature_names=tuple(str(f) for f in payload["feature_names"]),
            hyperparams=dict(payload["hyperparams"]),
            weights=dict(payload["weights"]),
            processor_states=dict(payload["processor_states"]) if payload.get("processor_states") is not None else None,
            upstream_identities=dict(payload.get("upstream_identities") or {}),
            training_cutoff=tc,
            frozen_at=fa,
            parent_model_sha256=payload.get("parent_model_sha256"),
            research_flags=dict(RESEARCH_FLAGS),
            model_sha256=str(expected_sha),
        )

    @classmethod
    def load(cls, path: Path) -> FrozenModelSpec:
        target = checked_target(Path(path), "frozen_model_spec")
        def _reject_const(_c: str) -> None:
            raise SecurityRefusalError("Non-finite JSON constant in FrozenModelSpec")
        payload = json.loads(target.read_text(encoding="utf-8"), parse_constant=_reject_const)
        return cls.from_dict(payload)


class BaseModel(metaclass=abc.ABCMeta):
    """Base prediction interface matching Qlib's BaseModel."""

    @abc.abstractmethod
    def predict(self, *args: Any, **kwargs: Any) -> Any:
        """Produce predictions."""

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        return self.predict(*args, **kwargs)


class Model(BaseModel):
    """Learnable Qlib-compatible model with zero-pickle FrozenModelSpec export/import."""

    task_type: str = "regression"

    def __init__(self) -> None:
        self.fitted: bool = False
        self.feature_names_: list[str] = []
        self.training_cutoff_: int | None = None
        self.parent_model_sha256_: str | None = None
        self.last_frozen_sha256_: str | None = None

    def _snapshot_parent_sha256(self) -> str:
        if self.last_frozen_sha256_ is not None:
            return self.last_frozen_sha256_
        return self.to_frozen_spec(
            training_cutoff=self.training_cutoff_ or 0,
            frozen_at=self.training_cutoff_ or 0,
        ).model_sha256

    @abc.abstractmethod
    def fit(self, dataset: DatasetH, reweighter: Reweighter | None = None) -> Model:
        """Fit model on dataset's 'train' (and optional 'valid') segment."""

    @abc.abstractmethod
    def predict(self, dataset: DatasetH, segment: str | slice = "test") -> pd.Series:
        """Predict 1D score Series on `segment` using DK_I features only."""

    def predict_proba(self, dataset: DatasetH, segment: str | slice = "test") -> pd.DataFrame:
        """For direction models: predict DataFrame(columns=['up', 'down', 'neutral']) summing to 1."""
        raise NotImplementedError(f"{self.__class__.__name__} does not output direction probabilities")

    @abc.abstractmethod
    def _get_hyperparams(self) -> dict[str, Any]:
        """Return JSON-serializable hyperparameter dict."""

    @abc.abstractmethod
    def _export_weights(self) -> dict[str, Any]:
        """Return JSON-serializable learned weights dict."""

    @abc.abstractmethod
    def _load_weights(self, weights: Mapping[str, Any], feature_names: list[str]) -> None:
        """Restore learned weights from dict."""

    def _prepare_features_infer(self, dataset: DatasetH, segment: str | slice) -> pd.DataFrame:
        if not self.fitted:
            raise RuntimeError(f"{self.__class__.__name__} has not been fitted")
        x_df = dataset.prepare(segment, col_set="feature", data_key=DataHandlerLP.DK_I)
        if isinstance(x_df, pd.Series):
            x_df = x_df.to_frame()
        missing = [f for f in self.feature_names_ if f not in x_df.columns]
        if missing:
            raise KeyError(f"Missing expected features {missing} in segment {segment!r}")
        return x_df[self.feature_names_]

    @staticmethod
    def _prepare_xy_learn(
        dataset: DatasetH,
        segment: str,
        target_col: str | None = None,
        reweighter: Reweighter | None = None,
    ) -> tuple[pd.DataFrame, np.ndarray, np.ndarray, str]:
        df = dataset.prepare(segment, col_set=["feature", "label"], data_key=DataHandlerLP.DK_L)
        if df.empty:
            raise ValueError(f"Segment {segment!r} produced 0 learning rows after purging/dropna")
        x_df = df["feature"]
        y_df = df["label"]
        if isinstance(y_df, pd.Series):
            chosen_col = str(y_df.name)
            y_raw = y_df.to_numpy(dtype=np.float64)
        else:
            if target_col is not None and target_col in y_df.columns:
                chosen_col = target_col
            elif "net_excess_return" in y_df.columns:
                chosen_col = "net_excess_return"
            elif "realized_log_return" in y_df.columns:
                chosen_col = "realized_log_return"
            else:
                chosen_col = str(y_df.columns[0])
            y_raw = y_df[chosen_col].to_numpy(dtype=np.float64)

        valid = np.isfinite(y_raw)
        df_valid = df.loc[valid]
        x_valid = x_df.loc[valid]
        y_valid = y_raw[valid]
        if y_valid.size == 0:
            raise ValueError(f"Segment {segment!r} has 0 finite labels for {chosen_col!r}")

        if reweighter is not None:
            w = np.asarray(reweighter.reweight(df_valid), dtype=np.float64).ravel()
            if w.size != y_valid.size:
                raise ValueError("Reweighter output length mismatch")
            w = np.clip(w, 0.0, None)
            if float(w.sum()) <= 0.0:
                w = np.ones_like(y_valid)
        else:
            w = np.ones_like(y_valid)
        return x_valid, y_valid, w, chosen_col

    def to_frozen_spec(
        self,
        *,
        model_name: str | None = None,
        model_version: str = "0.1.0",
        training_cutoff: int | None = None,
        frozen_at: int | None = None,
        processor_states: Mapping[str, Any] | None = None,
        upstream_identities: Mapping[str, Any] | None = None,
    ) -> FrozenModelSpec:
        if not self.fitted:
            raise RuntimeError(f"Cannot freeze unfitted {self.__class__.__name__}")
        tc = int(training_cutoff if training_cutoff is not None else (self.training_cutoff_ or 0))
        fa = int(frozen_at if frozen_at is not None else tc)
        spec = FrozenModelSpec.build(
            model_class=self.__class__.__name__,
            model_name=model_name or self.__class__.__name__.lower(),
            model_version=model_version,
            task_type=self.task_type,
            feature_names=self.feature_names_,
            hyperparams=self._get_hyperparams(),
            weights=self._export_weights(),
            training_cutoff=tc,
            frozen_at=fa,
            processor_states=processor_states,
            upstream_identities=upstream_identities,
            parent_model_sha256=self.parent_model_sha256_,
        )
        self.last_frozen_sha256_ = spec.model_sha256
        return spec

    @classmethod
    def from_frozen_spec(cls, spec: FrozenModelSpec | Mapping[str, Any] | Path) -> Model:
        if isinstance(spec, (Path, str)):
            parsed = FrozenModelSpec.load(Path(spec))
        elif isinstance(spec, Mapping):
            parsed = FrozenModelSpec.from_dict(spec)
        elif isinstance(spec, FrozenModelSpec):
            parsed = spec
        else:
            raise TypeError(f"Expected FrozenModelSpec, dict, or Path, got {type(spec).__name__}")

        target_cls = get_registered_class(parsed.model_class, category="model")
        if cls is not Model and not issubclass(target_cls, cls):
            raise SecurityRefusalError(
                f"FrozenModelSpec class {parsed.model_class!r} is not a subclass of {cls.__name__}"
            )
        inst: Model = target_cls(**parsed.hyperparams)
        inst.feature_names_ = list(parsed.feature_names)
        inst._load_weights(parsed.weights, inst.feature_names_)
        inst.training_cutoff_ = parsed.training_cutoff
        inst.parent_model_sha256_ = parsed.parent_model_sha256
        inst.last_frozen_sha256_ = parsed.model_sha256
        inst.fitted = True
        return inst


class ModelFT(Model):
    """Fine-tunable Qlib-compatible model recording cryptographic parent_model_sha256 lineage."""

    @abc.abstractmethod
    def finetune(self, dataset: DatasetH, reweighter: Reweighter | None = None, **kwargs: Any) -> ModelFT:
        """Warm-start / continuation fine-tune on `dataset`, recording prior `parent_model_sha256_`."""
