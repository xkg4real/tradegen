"""Leak-free StatefulProcessor & Stateless Processor suite for DataHandlerLP."""
from __future__ import annotations

import abc
from typing import Any

import numpy as np
import pandas as pd

from qlib_lab.exceptions import FitLeakageError, MissingFeatureVoidError
from qlib_lab.expression.ast_nodes import _to_utc_timestamps
from qlib_lab.registry import register_component


def _group_cols(df: pd.DataFrame, fields_group: str) -> list[Any]:
    if isinstance(df.columns, pd.MultiIndex):
        return [c for c in df.columns if c[0] == fields_group]
    return list(df.columns)


class Processor(metaclass=abc.ABCMeta):
    """Base preprocessor with JSON-serializable state export/import (zero pickle)."""

    def fit(self, df: pd.DataFrame) -> Processor:
        _ = df
        return self

    @abc.abstractmethod
    def __call__(self, df: pd.DataFrame) -> pd.DataFrame:
        """Transform DataFrame and return a new DataFrame."""

    def is_for_infer(self) -> bool:
        return True

    def readonly(self) -> bool:
        return False

    def config(self, **kwargs: Any) -> None:
        for k, v in kwargs.items():
            if hasattr(self, k):
                setattr(self, k, v)

    def to_state_dict(self) -> dict[str, Any]:
        return {"class": self.__class__.__name__, "kwargs": {}, "state": {}}

    def load_state_dict(self, payload: dict[str, Any]) -> Processor:
        _ = payload
        return self


class StatefulProcessor(Processor):
    """Processor whose statistics MUST be fitted strictly on [fit_start_time, fit_end_time]."""

    def __init__(self, fit_start_time: Any = None, fit_end_time: Any = None, fields_group: str = "feature") -> None:
        if fit_start_time is None or fit_end_time is None:
            raise FitLeakageError(
                f"{self.__class__.__name__} requires explicit non-null fit_start_time and fit_end_time"
            )
        self._set_fit_bounds(fit_start_time, fit_end_time)
        self.fields_group = str(fields_group)
        self.fitted: bool = False

    def _set_fit_bounds(self, fit_start_time: Any, fit_end_time: Any) -> None:
        st = _to_utc_timestamps(pd.Index([fit_start_time]))[0]
        et = _to_utc_timestamps(pd.Index([fit_end_time]))[0]
        if st > et:
            raise FitLeakageError(
                f"{self.__class__.__name__}: fit_start_time ({st}) > fit_end_time ({et})"
            )
        self.fit_start_time = st
        self.fit_end_time = et

    def rebind_fit_window(self, fit_start_time: Any, fit_end_time: Any) -> None:
        """Rebind fit window for rolling task execution and clear any prior fitted statistics."""
        self._set_fit_bounds(fit_start_time, fit_end_time)
        self._reset_state()
        self.fitted = False

    @abc.abstractmethod
    def _reset_state(self) -> None:
        """Reset learned statistics."""

    def _slice_fit(self, df: pd.DataFrame) -> pd.DataFrame:
        dts = _to_utc_timestamps(df.index.get_level_values("datetime"))
        mask = (dts >= self.fit_start_time) & (dts <= self.fit_end_time)
        sub = df.loc[mask]
        if sub.empty:
            raise FitLeakageError(
                f"{self.__class__.__name__}: empty fit slice for [{self.fit_start_time}, {self.fit_end_time}]"
            )
        return sub


@register_component("processor")
class WinsorizeClip(StatefulProcessor):
    """Quantile winsorization fitted strictly on [fit_start_time, fit_end_time]."""

    def __init__(
        self,
        fit_start_time: Any = None,
        fit_end_time: Any = None,
        lower_q: float = 0.01,
        upper_q: float = 0.99,
        fields_group: str = "feature",
    ) -> None:
        super().__init__(fit_start_time=fit_start_time, fit_end_time=fit_end_time, fields_group=fields_group)
        if not (0.0 <= float(lower_q) < float(upper_q) <= 1.0):
            raise ValueError(f"Require 0 <= lower_q < upper_q <= 1, got ({lower_q}, {upper_q})")
        self.lower_q = float(lower_q)
        self.upper_q = float(upper_q)
        self.bounds_: dict[str, tuple[float, float]] = {}

    def _reset_state(self) -> None:
        self.bounds_ = {}

    def fit(self, df: pd.DataFrame) -> WinsorizeClip:
        sub = self._slice_fit(df)
        cols = _group_cols(sub, self.fields_group)
        self.bounds_ = {}
        for col in cols:
            vals = sub[col].to_numpy(dtype=np.float64)
            fin = vals[np.isfinite(vals)]
            key = str(col[-1]) if isinstance(col, tuple) else str(col)
            if fin.size == 0:
                self.bounds_[key] = (-1e12, 1e12)
            else:
                lo, hi = np.quantile(fin, [self.lower_q, self.upper_q])
                self.bounds_[key] = (float(lo), float(hi))
        self.fitted = True
        return self

    def __call__(self, df: pd.DataFrame) -> pd.DataFrame:
        if not self.fitted:
            raise FitLeakageError("WinsorizeClip called before fit() or load_state_dict()")
        out = df.copy()
        for col in _group_cols(out, self.fields_group):
            key = str(col[-1]) if isinstance(col, tuple) else str(col)
            if key in self.bounds_:
                lo, hi = self.bounds_[key]
                out[col] = np.clip(out[col].to_numpy(dtype=np.float64), lo, hi)
        return out

    def to_state_dict(self) -> dict[str, Any]:
        return {
            "class": "WinsorizeClip",
            "kwargs": {
                "fit_start_time": self.fit_start_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "fit_end_time": self.fit_end_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "lower_q": self.lower_q,
                "upper_q": self.upper_q,
                "fields_group": self.fields_group,
            },
            "state": {"bounds": {k: [v[0], v[1]] for k, v in sorted(self.bounds_.items())}, "fitted": self.fitted},
        }

    def load_state_dict(self, payload: dict[str, Any]) -> WinsorizeClip:
        st = payload.get("state", {})
        self.bounds_ = {str(k): (float(v[0]), float(v[1])) for k, v in st.get("bounds", {}).items()}
        self.fitted = bool(st.get("fitted", True))
        return self


@register_component("processor")
class RobustZScoreNorm(StatefulProcessor):
    """Median / MAD normalization fitted strictly on [fit_start_time, fit_end_time]."""

    def __init__(
        self,
        fit_start_time: Any = None,
        fit_end_time: Any = None,
        clip_outlier: bool = True,
        max_z: float = 5.0,
        fields_group: str = "feature",
    ) -> None:
        super().__init__(fit_start_time=fit_start_time, fit_end_time=fit_end_time, fields_group=fields_group)
        self.clip_outlier = bool(clip_outlier)
        self.max_z = float(max_z)
        self.stats_: dict[str, tuple[float, float]] = {}

    def _reset_state(self) -> None:
        self.stats_ = {}

    def fit(self, df: pd.DataFrame) -> RobustZScoreNorm:
        sub = self._slice_fit(df)
        self.stats_ = {}
        for col in _group_cols(sub, self.fields_group):
            vals = sub[col].to_numpy(dtype=np.float64)
            fin = vals[np.isfinite(vals)]
            key = str(col[-1]) if isinstance(col, tuple) else str(col)
            if fin.size == 0:
                self.stats_[key] = (0.0, 1.0)
            else:
                med = float(np.median(fin))
                mad = float(1.4826 * np.median(np.abs(fin - med)))
                if mad <= 1e-12:
                    sd = float(np.std(fin, ddof=1)) if fin.size > 1 else 1.0
                    scale = sd if sd > 1e-12 else 1.0
                else:
                    scale = mad
                self.stats_[key] = (med, scale)
        self.fitted = True
        return self

    def __call__(self, df: pd.DataFrame) -> pd.DataFrame:
        if not self.fitted:
            raise FitLeakageError("RobustZScoreNorm called before fit() or load_state_dict()")
        out = df.copy()
        for col in _group_cols(out, self.fields_group):
            key = str(col[-1]) if isinstance(col, tuple) else str(col)
            if key in self.stats_:
                med, scale = self.stats_[key]
                z = (out[col].to_numpy(dtype=np.float64) - med) / scale
                if self.clip_outlier:
                    z = np.clip(z, -self.max_z, self.max_z)
                out[col] = z
        return out

    def to_state_dict(self) -> dict[str, Any]:
        return {
            "class": "RobustZScoreNorm",
            "kwargs": {
                "fit_start_time": self.fit_start_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "fit_end_time": self.fit_end_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "clip_outlier": self.clip_outlier,
                "max_z": self.max_z,
                "fields_group": self.fields_group,
            },
            "state": {"stats": {k: [v[0], v[1]] for k, v in sorted(self.stats_.items())}, "fitted": self.fitted},
        }

    def load_state_dict(self, payload: dict[str, Any]) -> RobustZScoreNorm:
        st = payload.get("state", {})
        self.stats_ = {str(k): (float(v[0]), float(v[1])) for k, v in st.get("stats", {}).items()}
        self.fitted = bool(st.get("fitted", True))
        return self


@register_component("processor")
class StandardZScoreNorm(StatefulProcessor):
    """Mean / sample-SD standardization fitted strictly on [fit_start_time, fit_end_time]."""

    def __init__(
        self,
        fit_start_time: Any = None,
        fit_end_time: Any = None,
        fields_group: str = "feature",
    ) -> None:
        super().__init__(fit_start_time=fit_start_time, fit_end_time=fit_end_time, fields_group=fields_group)
        self.stats_: dict[str, tuple[float, float]] = {}

    def _reset_state(self) -> None:
        self.stats_ = {}

    def fit(self, df: pd.DataFrame) -> StandardZScoreNorm:
        sub = self._slice_fit(df)
        self.stats_ = {}
        for col in _group_cols(sub, self.fields_group):
            vals = sub[col].to_numpy(dtype=np.float64)
            fin = vals[np.isfinite(vals)]
            key = str(col[-1]) if isinstance(col, tuple) else str(col)
            if fin.size == 0:
                self.stats_[key] = (0.0, 1.0)
            else:
                mu = float(np.mean(fin))
                sd = float(np.std(fin, ddof=1)) if fin.size > 1 else 1.0
                self.stats_[key] = (mu, sd if sd > 1e-12 else 1.0)
        self.fitted = True
        return self

    def __call__(self, df: pd.DataFrame) -> pd.DataFrame:
        if not self.fitted:
            raise FitLeakageError("StandardZScoreNorm called before fit() or load_state_dict()")
        out = df.copy()
        for col in _group_cols(out, self.fields_group):
            key = str(col[-1]) if isinstance(col, tuple) else str(col)
            if key in self.stats_:
                mu, sd = self.stats_[key]
                out[col] = (out[col].to_numpy(dtype=np.float64) - mu) / sd
        return out

    def to_state_dict(self) -> dict[str, Any]:
        return {
            "class": "StandardZScoreNorm",
            "kwargs": {
                "fit_start_time": self.fit_start_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "fit_end_time": self.fit_end_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "fields_group": self.fields_group,
            },
            "state": {"stats": {k: [v[0], v[1]] for k, v in sorted(self.stats_.items())}, "fitted": self.fitted},
        }

    def load_state_dict(self, payload: dict[str, Any]) -> StandardZScoreNorm:
        st = payload.get("state", {})
        self.stats_ = {str(k): (float(v[0]), float(v[1])) for k, v in st.get("stats", {}).items()}
        self.fitted = bool(st.get("fitted", True))
        return self


@register_component("processor")
class CSRankNorm(Processor):
    """Stateless cross-sectional rank normalization per timestamp scaled to unit variance."""

    def __init__(self, fields_group: str = "feature") -> None:
        self.fields_group = str(fields_group)

    def __call__(self, df: pd.DataFrame) -> pd.DataFrame:
        out = df.copy()
        cols = _group_cols(out, self.fields_group)
        if not cols:
            return out
        # Rank within each datetime slice; scale uniform [-0.5, 0.5] by sqrt(12) ~= 3.4641016
        grouped = out[cols].groupby(level="datetime", group_keys=False)
        ranked = grouped.rank(pct=True, method="average")
        counts = grouped.transform("count")
        scaled = np.where(counts > 1, (ranked - 0.5) * 3.4641016151377544, np.where(counts == 1, 0.0, np.nan))
        out[cols] = scaled
        return out

    def to_state_dict(self) -> dict[str, Any]:
        return {"class": "CSRankNorm", "kwargs": {"fields_group": self.fields_group}, "state": {}}


@register_component("processor")
class CSZScoreNorm(Processor):
    """Stateless cross-sectional Z-score normalization per timestamp."""

    def __init__(self, fields_group: str = "feature") -> None:
        self.fields_group = str(fields_group)

    def __call__(self, df: pd.DataFrame) -> pd.DataFrame:
        out = df.copy()
        cols = _group_cols(out, self.fields_group)
        if not cols:
            return out
        grouped = out[cols].groupby(level="datetime", group_keys=False)
        means = grouped.transform("mean")
        stds = grouped.transform("std")
        vals = out[cols].to_numpy(dtype=np.float64)
        m_arr = means.to_numpy(dtype=np.float64)
        s_arr = stds.to_numpy(dtype=np.float64)
        with np.errstate(divide="ignore", invalid="ignore"):
            normed = np.where(s_arr > 1e-12, (vals - m_arr) / s_arr, np.where(np.isfinite(vals), 0.0, np.nan))
        out[cols] = normed
        return out

    def to_state_dict(self) -> dict[str, Any]:
        return {"class": "CSZScoreNorm", "kwargs": {"fields_group": self.fields_group}, "state": {}}


@register_component("processor")
class FailClosedDropnaProcessor(Processor):
    """Fail-closed missing-feature guard (S1): NEVER imputes; raises MissingFeatureVoidError above 5%."""

    def __init__(
        self,
        warmup_bars: int = 0,
        max_post_warmup_missing: float = 0.05,
        fields_group: str = "feature",
    ) -> None:
        if warmup_bars < 0:
            raise ValueError("warmup_bars must be >= 0")
        if not (0.0 <= float(max_post_warmup_missing) <= 1.0):
            raise ValueError("max_post_warmup_missing must lie in [0, 1]")
        self.warmup_bars = int(warmup_bars)
        self.max_post_warmup_missing = float(max_post_warmup_missing)
        self.fields_group = str(fields_group)
        self.last_post_warmup_missing_rate: float = 0.0

    def __call__(self, df: pd.DataFrame) -> pd.DataFrame:
        cols = _group_cols(df, self.fields_group)
        if not cols or df.empty:
            return df.copy()

        feat_mat = df[cols].to_numpy(dtype=np.float64)
        row_has_nan = ~np.all(np.isfinite(feat_mat), axis=1)

        inst_level = df.index.get_level_values("instrument")
        post_warmup_mask = np.zeros(len(df), dtype=bool)
        for inst in inst_level.unique():
            pos = np.flatnonzero(inst_level == inst)
            if pos.size > self.warmup_bars:
                post_warmup_mask[pos[self.warmup_bars :]] = True

        n_post = int(np.sum(post_warmup_mask))
        if n_post > 0:
            n_miss = int(np.sum(row_has_nan[post_warmup_mask]))
            miss_rate = float(n_miss) / float(n_post)
            self.last_post_warmup_missing_rate = miss_rate
            if miss_rate > self.max_post_warmup_missing + 1e-12:
                raise MissingFeatureVoidError(
                    f"S1 VOID: post-warmup missing feature rate {miss_rate:.4f} ({n_miss}/{n_post}) "
                    f"exceeds max_post_warmup_missing={self.max_post_warmup_missing:.4f}; silent imputation is forbidden"
                )

        return df.loc[~row_has_nan].copy()

    def to_state_dict(self) -> dict[str, Any]:
        return {
            "class": "FailClosedDropnaProcessor",
            "kwargs": {
                "warmup_bars": self.warmup_bars,
                "max_post_warmup_missing": self.max_post_warmup_missing,
                "fields_group": self.fields_group,
            },
            "state": {"last_post_warmup_missing_rate": self.last_post_warmup_missing_rate},
        }


@register_component("processor")
class ExplicitFillnaProcessor(Processor):
    """Opt-in missing-value filler that stamps explicit `<col>__isna` indicator features."""

    def __init__(
        self,
        fill_value: float = 0.0,
        fields_group: str = "feature",
        add_indicator: bool = True,
    ) -> None:
        self.fill_value = float(fill_value)
        self.fields_group = str(fields_group)
        self.add_indicator = bool(add_indicator)

    def __call__(self, df: pd.DataFrame) -> pd.DataFrame:
        out = df.copy()
        cols = _group_cols(out, self.fields_group)
        if not cols:
            return out

        indicator_cols: dict[Any, np.ndarray] = {}
        for col in cols:
            vals = out[col].to_numpy(dtype=np.float64)
            isna = ~np.isfinite(vals)
            if self.add_indicator:
                ind_col = (
                    (col[0], f"{col[1]}__isna")
                    if isinstance(col, tuple)
                    else f"{col}__isna"
                )
                indicator_cols[ind_col] = isna.astype(np.float64)
            out[col] = np.where(isna, self.fill_value, vals)

        if indicator_cols:
            ind_df = pd.DataFrame(indicator_cols, index=out.index)
            if isinstance(out.columns, pd.MultiIndex) and not isinstance(ind_df.columns, pd.MultiIndex):
                ind_df.columns = pd.MultiIndex.from_tuples(list(indicator_cols.keys()))
            out = pd.concat([out, ind_df], axis=1)
        return out

    def to_state_dict(self) -> dict[str, Any]:
        return {
            "class": "ExplicitFillnaProcessor",
            "kwargs": {
                "fill_value": self.fill_value,
                "fields_group": self.fields_group,
                "add_indicator": self.add_indicator,
            },
            "state": {},
        }


@register_component("processor")
class DropnaLabelProcessor(Processor):
    """Learning-only processor dropping rows with incomplete/NaN labels (forbidden in infer_processors)."""

    def __init__(self, fields_group: str = "label") -> None:
        self.fields_group = str(fields_group)

    def is_for_infer(self) -> bool:
        return False

    def __call__(self, df: pd.DataFrame) -> pd.DataFrame:
        cols = _group_cols(df, self.fields_group)
        if not cols or df.empty:
            return df.copy()
        vals = df[cols].to_numpy(dtype=np.float64)
        ok = np.all(np.isfinite(vals), axis=1)
        return df.loc[ok].copy()

    def to_state_dict(self) -> dict[str, Any]:
        return {"class": "DropnaLabelProcessor", "kwargs": {"fields_group": self.fields_group}, "state": {}}
