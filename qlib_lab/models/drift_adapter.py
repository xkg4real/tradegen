"""Concept-drift adapters: RegimeKernelReweighter & causal OnlineHedgeCombiner."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
import math
from typing import Any

import numpy as np
import pandas as pd

from qlib_lab.data.labels import DIRECTION_CLASSES
from qlib_lab.expression.ast_nodes import _epoch_seconds_array, _to_utc_timestamps
from qlib_lab.models.base import Reweighter
from qlib_lab.registry import register_component


@register_component("reweighter")
class RegimeKernelReweighter(Reweighter):
    """Exponential time-decay x Mahalanobis regime similarity Reweighter fitted strictly on train.

    Computes per-timestamp regime summary z_t (cross-sectional mean of regime_features),
    estimates regularized covariance on the training slice, anchors target regime z_* on the
    trailing `anchor_bars` at the end of `train` (zero future leakage), and assigns:
      w_t proportional to exp(-ln(2) * age_bars / halflife_bars) * exp(-0.5 * d_M^2(z_t, z_*) / kernel_bandwidth^2).
    """

    def __init__(
        self,
        halflife_bars: float = 120.0,
        anchor_bars: int = 24,
        kernel_bandwidth: float = 2.0,
        cov_ridge: float = 1e-3,
        regime_features: Sequence[str] | None = None,
        min_weight: float = 0.05,
        max_weight: float = 5.0,
    ) -> None:
        if halflife_bars <= 0 or anchor_bars < 1 or kernel_bandwidth <= 0:
            raise ValueError("Invalid RegimeKernelReweighter parameters")
        self.halflife_bars = float(halflife_bars)
        self.anchor_bars = int(anchor_bars)
        self.kernel_bandwidth = float(kernel_bandwidth)
        self.cov_ridge = float(cov_ridge)
        self.regime_features = tuple(str(f) for f in regime_features) if regime_features is not None else None
        self.min_weight = float(min_weight)
        self.max_weight = float(max_weight)
        self.last_weights_summary_: dict[str, float] = {}

    def reweight(self, df: pd.DataFrame) -> np.ndarray:
        if df.empty:
            return np.empty(0, dtype=np.float64)

        feat_df = df["feature"] if (isinstance(df.columns, pd.MultiIndex) and "feature" in df.columns.get_level_values(0)) else df
        if self.regime_features is not None:
            cols = [c for c in self.regime_features if c in feat_df.columns]
            if not cols:
                raise KeyError(f"None of regime_features {self.regime_features} present in {list(feat_df.columns)}")
            sub_f = feat_df[cols]
        else:
            sub_f = feat_df

        # Aggregate per timestamp across instruments
        by_dt = sub_f.groupby(level="datetime").mean().sort_index()
        T_dates = len(by_dt)
        if T_dates < 3:
            return np.ones(len(df), dtype=np.float64)

        Z = np.nan_to_num(by_dt.to_numpy(dtype=np.float64), nan=0.0)
        d_dim = Z.shape[1]

        # Exponential time decay measured in calendar bar steps from end of df (train end)
        age = np.arange(T_dates - 1, -1, -1, dtype=np.float64)
        decay_w = np.exp(-math.log(2.0) * age / self.halflife_bars)

        # Mahalanobis distance to trailing anchor_bars at the end of train
        k_anc = min(self.anchor_bars, T_dates)
        z_star = np.mean(Z[-k_anc:], axis=0)
        cov = np.cov(Z, rowvar=False, ddof=1) if T_dates > 1 else np.eye(d_dim)
        cov = np.atleast_2d(np.asarray(cov, dtype=np.float64)) + self.cov_ridge * np.eye(d_dim, dtype=np.float64)
        diff = Z - z_star[None, :]
        inv_cov_diff = np.linalg.solve(cov, diff.T).T
        d_mah2 = np.maximum(0.0, np.sum(diff * inv_cov_diff, axis=1))
        sim_w = np.exp(-0.5 * d_mah2 / (self.kernel_bandwidth ** 2))

        dt_weights = np.clip(decay_w * sim_w, self.min_weight, self.max_weight)
        dt_series = pd.Series(dt_weights, index=by_dt.index)

        row_dts = df.index.get_level_values("datetime")
        w_rows = dt_series.reindex(row_dts).fillna(1.0).to_numpy(dtype=np.float64)
        w_rows /= max(float(np.mean(w_rows)), 1e-12)
        self.last_weights_summary_ = {
            "min": float(np.min(w_rows)),
            "max": float(np.max(w_rows)),
            "std": float(np.std(w_rows)),
        }
        return w_rows


class OnlineHedgeCombiner:
    """Causal Multiplicative-Weights (Hedge) ensemble over M candidate models.

    STRICT CAUSALITY INVARIANT:
    At forecast timestamp `as_of`, model losses from historical forecast origin `s < as_of`
    are incorporated into Hedge weights IF AND ONLY IF `label_end_utc[s] <= as_of`!
    Any open outcome window (`label_end_utc[s] > as_of`) is strictly held back until closed.
    """

    def __init__(
        self,
        model_names: Sequence[str],
        learning_rate: float = 0.5,
        min_weight_floor: float = 0.02,
        loss_clip: float = 5.0,
        task_type: str = "direction",
    ) -> None:
        names = [str(n) for n in model_names]
        if len(names) < 2:
            raise ValueError("OnlineHedgeCombiner requires at least 2 candidate models")
        if learning_rate <= 0 or not (0.0 <= min_weight_floor < 1.0 / len(names)):
            raise ValueError("Invalid learning_rate or min_weight_floor in OnlineHedgeCombiner")
        if task_type not in ("direction", "regression"):
            raise ValueError("task_type must be 'direction' or 'regression'")

        self.model_names = tuple(names)
        self.learning_rate = float(learning_rate)
        self.min_weight_floor = float(min_weight_floor)
        self.loss_clip = float(loss_clip)
        self.task_type = task_type
        self.weight_history_: pd.DataFrame = pd.DataFrame()

    def combine(
        self,
        predictions_by_model: Mapping[str, pd.DataFrame | pd.Series],
        realized_labels: pd.Series,
        label_end_utc: pd.Series,
    ) -> tuple[pd.DataFrame | pd.Series, pd.DataFrame]:
        """Causally combine candidate predictions across timestamps using only closed past outcomes.

        Returns `(combined_predictions, weights_by_datetime_df)`.
        """
        for name in self.model_names:
            if name not in predictions_by_model:
                raise KeyError(f"Missing predictions for candidate model {name!r}")

        first_pred = predictions_by_model[self.model_names[0]]
        common_index = first_pred.index
        for name in self.model_names[1:]:
            common_index = common_index.intersection(predictions_by_model[name].index)
        common_index = common_index.sort_values()

        dts_unique = common_index.get_level_values("datetime").unique().sort_values()
        dts_utc = _to_utc_timestamps(dts_unique)
        as_of_epochs = _epoch_seconds_array(dts_utc)

        y_aligned = realized_labels.reindex(common_index).to_numpy(dtype=np.float64)
        end_aligned = _epoch_seconds_array(label_end_utc.reindex(common_index).to_numpy())
        row_dts = common_index.get_level_values("datetime")

        m_count = len(self.model_names)
        # Precompute per-row losses for each model (never read before end_aligned[r] <= cur_as_of!)
        per_model_losses = np.full((len(common_index), m_count), np.nan, dtype=np.float64)
        pred_arrays: list[np.ndarray] = []

        for m_idx, name in enumerate(self.model_names):
            p_obj = predictions_by_model[name].reindex(common_index)
            if self.task_type == "direction":
                if not isinstance(p_obj, pd.DataFrame):
                    raise TypeError("Direction OnlineHedgeCombiner expects DataFrame(columns=['up','down','neutral'])")
                arr = p_obj[list(DIRECTION_CLASSES)].to_numpy(dtype=np.float64)
                pred_arrays.append(arr)
                ok = np.isfinite(y_aligned) & np.all(np.isfinite(arr), axis=1)
                if np.any(ok):
                    y_int = y_aligned[ok].astype(np.int64)
                    probs_ok = arr[ok]
                    ll = -np.log(np.clip(probs_ok[np.arange(y_int.size), y_int], 1e-12, 1.0))
                    per_model_losses[ok, m_idx] = np.clip(ll, 0.0, self.loss_clip)
            else:
                ser = p_obj.iloc[:, 0] if isinstance(p_obj, pd.DataFrame) else p_obj
                arr1d = ser.to_numpy(dtype=np.float64)
                pred_arrays.append(arr1d)
                ok = np.isfinite(y_aligned) & np.isfinite(arr1d)
                if np.any(ok):
                    sq = (arr1d[ok] - y_aligned[ok]) ** 2
                    per_model_losses[ok, m_idx] = np.clip(sq, 0.0, self.loss_clip)

        # Sort closed outcome events by their realization time `end_aligned`
        valid_outcome_rows = np.flatnonzero(
            np.isfinite(end_aligned) & np.all(np.isfinite(per_model_losses), axis=1)
        )
        order_by_end = valid_outcome_rows[np.argsort(end_aligned[valid_outcome_rows], kind="stable")]
        sorted_ends = end_aligned[order_by_end]

        log_w = np.zeros(m_count, dtype=np.float64)
        ptr = 0
        n_closed = sorted_ends.size

        weight_records = np.zeros((len(dts_unique), m_count), dtype=np.float64)
        if self.task_type == "direction":
            combined_arr = np.zeros((len(common_index), 3), dtype=np.float64)
        else:
            combined_arr = np.zeros(len(common_index), dtype=np.float64)

        for t_idx, dt_val in enumerate(dts_unique):
            cur_ep = as_of_epochs[t_idx]
            # ONLY incorporate outcomes whose window has FULLY CLOSED at or before cur_ep!
            while ptr < n_closed and sorted_ends[ptr] <= cur_ep + 1e-9:
                r_idx = int(order_by_end[ptr])
                log_w -= self.learning_rate * per_model_losses[r_idx]
                log_w -= np.max(log_w)
                ptr += 1

            raw_w = np.exp(log_w - np.max(log_w))
            raw_w /= float(raw_w.sum())
            # Mix with uniform floor so no expert permanently starves to 0 under regime switch
            w = (1.0 - m_count * self.min_weight_floor) * raw_w + self.min_weight_floor
            w /= float(w.sum())
            weight_records[t_idx] = w

            row_mask = row_dts == dt_val
            for m_idx in range(m_count):
                combined_arr[row_mask] += w[m_idx] * pred_arrays[m_idx][row_mask]

        weights_df = pd.DataFrame(weight_records, index=dts_unique, columns=list(self.model_names), dtype=np.float64)
        self.weight_history_ = weights_df
        if self.task_type == "direction":
            out_pred: pd.DataFrame | pd.Series = pd.DataFrame(
                combined_arr, index=common_index, columns=list(DIRECTION_CLASSES), dtype=np.float64
            )
        else:
            out_pred = pd.Series(combined_arr, index=common_index, name="score", dtype=np.float64)
        return out_pred, weights_df
