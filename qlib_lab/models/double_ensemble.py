"""Microsoft Qlib DoubleEnsemble (Zhang et al., ICDM 2020): Trajectory Sample Reweighting (SR) + Permutation Feature Shrinkage (FS)."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from typing import Any

import numpy as np
import pandas as pd

from qlib_lab.data.dataset import DatasetH
from qlib_lab.data.handler import DataHandlerLP, StaticDataLoader
from qlib_lab.data.labels import DIRECTION_CLASSES
from qlib_lab.models.base import ArrayReweighter, Model, Reweighter
from qlib_lab.registry import init_instance_by_config, register_component


def _subset_dataset_features(dataset: DatasetH, selected_features: list[str]) -> DatasetH:
    """Create a lightweight DatasetH view retaining only `selected_features` in ('feature', ...)."""
    infer_df = dataset.handler.fetch(col_set=DataHandlerLP.CS_RAW, data_key=DataHandlerLP.DK_I)
    learn_df = dataset.handler.fetch(col_set=DataHandlerLP.CS_RAW, data_key=DataHandlerLP.DK_L)

    def _filter_cols(df: pd.DataFrame) -> pd.DataFrame:
        keep = [c for c in df.columns if c[0] != "feature" or str(c[1]) in selected_features]
        # Preserve exact selected_features column order
        feat_cols = [("feature", f) for f in selected_features if ("feature", f) in df.columns]
        other_cols = [c for c in keep if c[0] != "feature"]
        return df[feat_cols + other_cols]

    sub_handler = DataHandlerLP(
        data_loader=StaticDataLoader(_filter_cols(infer_df)),
        init_data=True,
    )
    sub_handler._infer = _filter_cols(infer_df)
    sub_handler._learn = _filter_cols(learn_df)
    sub_ds = DatasetH(
        handler=sub_handler,
        segments=dataset.raw_segments,
        embargo_bars=dataset.embargo_bars,
        purge_outcomes=dataset.purge_outcomes,
    )
    return sub_ds


@register_component("model")
class DoubleEnsembleModel(Model):
    """Qlib DoubleEnsemble combining trajectory Sample Reweighting (SR) and permutation Feature Shrinkage (FS)."""

    def __init__(
        self,
        base_model_config: Mapping[str, Any] | None = None,
        num_models: int = 3,
        enable_sr: bool = True,
        enable_fs: bool = True,
        alpha1: float = 1.0,
        alpha2: float = 1.0,
        bins_sr: int = 10,
        bins_fs: int = 5,
        decay: float = 0.5,
        sample_ratios: Sequence[float] = (0.8, 0.7),
        seed: int = 11,
        target_col: str | None = None,
    ) -> None:
        super().__init__()
        if num_models < 1:
            raise ValueError("num_models must be >= 1")
        self.base_model_config: dict[str, Any] = deepcopy(
            dict(
                base_model_config
                or {
                    "class": "HistGBDTModel",
                    "kwargs": {"loss": "regression", "num_boost_round": 25, "max_depth": 3},
                }
            )
        )
        # Infer task_type from base model instantiation probe
        probe: Model = init_instance_by_config(self.base_model_config, accept_types=Model)
        self.task_type = probe.task_type

        self.num_models = int(num_models)
        self.enable_sr = bool(enable_sr)
        self.enable_fs = bool(enable_fs)
        self.alpha1 = float(alpha1)
        self.alpha2 = float(alpha2)
        self.bins_sr = max(2, int(bins_sr))
        self.bins_fs = max(2, int(bins_fs))
        self.decay = float(decay)
        self.sample_ratios = tuple(float(r) for r in sample_ratios)
        self.seed = int(seed)
        self.target_col = target_col

        self.sub_models_: list[Model] = []
        self.sub_features_: list[list[str]] = []
        self.model_weights_: np.ndarray = np.empty(0, dtype=np.float64)

    def _get_hyperparams(self) -> dict[str, Any]:
        return {
            "base_model_config": self.base_model_config,
            "num_models": self.num_models,
            "enable_sr": self.enable_sr,
            "enable_fs": self.enable_fs,
            "alpha1": self.alpha1,
            "alpha2": self.alpha2,
            "bins_sr": self.bins_sr,
            "bins_fs": self.bins_fs,
            "decay": self.decay,
            "sample_ratios": list(self.sample_ratios),
            "seed": self.seed,
            "target_col": self.target_col,
        }

    def _sample_loss(self, y: np.ndarray, pred_or_proba: np.ndarray) -> np.ndarray:
        if self.task_type == "direction":
            y_int = y.astype(np.int64)
            return -np.log(np.clip(pred_or_proba[np.arange(y_int.size), y_int], 1e-15, 1.0))
        return 0.5 * (pred_or_proba - y) ** 2

    def _compute_sr_weights(
        self,
        loss_trajectory: np.ndarray | None,
        ens_loss: np.ndarray,
        k_idx: int,
    ) -> np.ndarray:
        """ICDM 2020 Sample Reweighting (SR): C-value (current ensemble residual) & H-value (trajectory dynamics)."""
        n = ens_loss.size
        if n < self.bins_sr:
            return np.ones(n, dtype=np.float64)

        # Rank-normalize C_i into bins_sr quantile buckets -> mean loss per bucket normalized
        c_ranks = pd.Series(ens_loss).rank(pct=True, method="average").to_numpy(dtype=np.float64)
        c_bins = np.minimum((c_ranks * self.bins_sr).astype(np.int64), self.bins_sr - 1)
        c_norm = np.zeros(n, dtype=np.float64)
        for b in range(self.bins_sr):
            m = c_bins == b
            if np.any(m):
                c_norm[m] = float(np.mean(c_ranks[m]))

        if loss_trajectory is not None and loss_trajectory.ndim == 2 and loss_trajectory.shape == (loss_trajectory.shape[0], n) and loss_trajectory.shape[0] >= 2:
            # H_i: how slowly or erratically loss dropped along training trajectory
            h_raw = np.mean(loss_trajectory[:-1] - loss_trajectory[-1:], axis=0)
            # Small or negative h_raw means sample never improved (hard noise) or started trivial (easy)
            h_disp = np.abs(h_raw - np.median(h_raw))
            h_ranks = pd.Series(h_disp).rank(pct=True, method="average").to_numpy(dtype=np.float64)
            h_bins = np.minimum((h_ranks * self.bins_sr).astype(np.int64), self.bins_sr - 1)
            h_norm = np.zeros(n, dtype=np.float64)
            for b in range(self.bins_sr):
                m = h_bins == b
                if np.any(m):
                    h_norm[m] = float(np.mean(h_ranks[m]))
        else:
            h_norm = c_norm

        shrink = self.decay ** k_idx
        denom = shrink * (self.alpha1 * c_norm + self.alpha2 * h_norm) + 1.0
        w = 1.0 / np.maximum(denom, 1e-6)
        w /= max(float(np.mean(w)), 1e-12)
        return w

    def _compute_fs_features(
        self,
        sub_model: Model,
        sub_ds: DatasetH,
        current_features: list[str],
        k_idx: int,
        rng: np.random.Generator,
        target_col: str,
    ) -> list[str]:
        """ICDM 2020 Feature Shrinkage (FS): permutation importance g_f on validation/train split."""
        if len(current_features) <= 2 or not self.sample_ratios:
            return list(current_features)

        eval_seg = "valid" if "valid" in sub_ds.segments else "train"
        try:
            x_eval_df, y_eval, _w, _ = self._prepare_xy_learn(sub_ds, eval_seg, target_col)
        except ValueError:
            x_eval_df, y_eval, _w, _ = self._prepare_xy_learn(sub_ds, "train", target_col)

        if len(y_eval) < 5:
            return list(current_features)

        def _eval_df_predictions(feat_frame: pd.DataFrame) -> np.ndarray:
            tmp_loader = StaticDataLoader(feat_frame, default_group="feature")
            tmp_dh = DataHandlerLP(data_loader=tmp_loader, init_data=True)
            st = feat_frame.index.get_level_values("datetime").min()
            et = feat_frame.index.get_level_values("datetime").max()
            tmp_ds = DatasetH(handler=tmp_dh, segments={"infer_seg": (st, et)}, purge_outcomes=False)
            if self.task_type == "direction":
                return sub_model.predict_proba(tmp_ds, "infer_seg").to_numpy(dtype=np.float64)
            return sub_model.predict(tmp_ds, "infer_seg").to_numpy(dtype=np.float64)

        base_pred = _eval_df_predictions(x_eval_df[current_features])
        base_loss = self._sample_loss(y_eval, base_pred)
        valid_mask = np.isfinite(base_loss)
        if int(np.sum(valid_mask)) < 5:
            return list(current_features)

        g_scores: list[tuple[float, str]] = []
        for f in current_features:
            perm_df = x_eval_df[current_features].copy()
            col_vals = perm_df[f].to_numpy(copy=True)
            rng.shuffle(col_vals)
            perm_df[f] = col_vals
            perm_pred = _eval_df_predictions(perm_df)
            perm_loss = self._sample_loss(y_eval, perm_pred)
            diff = perm_loss[valid_mask] - base_loss[valid_mask]
            sd = float(np.std(diff, ddof=1)) if diff.size > 1 else 0.0
            g_f = float(np.mean(diff)) / (sd + 1e-8)
            g_scores.append((g_f, f))

        g_scores.sort(key=lambda pair: pair[0], reverse=True)
        ratio = self.sample_ratios[min(k_idx, len(self.sample_ratios) - 1)]
        n_keep = max(1, min(len(current_features), int(round(ratio * len(current_features)))))
        kept = {f for _g, f in g_scores[:n_keep]}
        # Preserve original column order
        return [f for f in current_features if f in kept]

    def fit(self, dataset: DatasetH, reweighter: Reweighter | None = None) -> DoubleEnsembleModel:
        default_col = self.target_col or ("direction_class" if self.task_type == "direction" else None)
        x_tr_df, y_tr, base_w, chosen_col = self._prepare_xy_learn(dataset, "train", default_col, reweighter=reweighter)
        self.feature_names_ = [str(c) for c in x_tr_df.columns]

        self.sub_models_ = []
        self.sub_features_ = []
        cur_features = list(self.feature_names_)
        cur_weights = base_w.copy()

        ens_accum = np.zeros((len(y_tr), 3) if self.task_type == "direction" else len(y_tr), dtype=np.float64)
        rng = np.random.default_rng(self.seed)

        for k in range(self.num_models):
            sub_ds = _subset_dataset_features(dataset, cur_features)
            cfg_k = deepcopy(self.base_model_config)
            if "kwargs" in cfg_k and isinstance(cfg_k["kwargs"], dict) and "seed" in cfg_k["kwargs"]:
                cfg_k["kwargs"]["seed"] = int(cfg_k["kwargs"]["seed"]) + k
            sub_m: Model = init_instance_by_config(cfg_k, accept_types=Model)

            rw_k = ArrayReweighter(cur_weights, index=x_tr_df.index)
            sub_m.fit(sub_ds, reweighter=rw_k)

            self.sub_models_.append(sub_m)
            self.sub_features_.append(list(cur_features))

            if self.task_type == "direction":
                tr_pred = sub_m.predict_proba(sub_ds, "train").reindex(x_tr_df.index).to_numpy(dtype=np.float64)
            else:
                tr_pred = sub_m.predict(sub_ds, "train").reindex(x_tr_df.index).to_numpy(dtype=np.float64)
            ens_accum = (ens_accum * float(k) + tr_pred) / float(k + 1)

            if k + 1 < self.num_models:
                if self.enable_sr:
                    ens_loss = self._sample_loss(y_tr, ens_accum)
                    traj = getattr(sub_m, "sample_loss_trajectory_", None)
                    sr_w = self._compute_sr_weights(traj, ens_loss, k + 1)
                    cur_weights = base_w * sr_w
                if self.enable_fs:
                    cur_features = self._compute_fs_features(sub_m, sub_ds, cur_features, k, rng, chosen_col)

        self.model_weights_ = np.full(len(self.sub_models_), 1.0 / float(len(self.sub_models_)), dtype=np.float64)
        self.training_cutoff_ = dataset.effective_training_cutoff(include_valid=True)
        self.fitted = True
        return self

    def predict_proba(self, dataset: DatasetH, segment: str | slice = "test") -> pd.DataFrame:
        if self.task_type != "direction":
            raise NotImplementedError("DoubleEnsembleModel wraps regression sub-models; predict_proba unavailable")
        x_df = self._prepare_features_infer(dataset, segment)
        total = np.zeros((len(x_df), 3), dtype=np.float64)
        for w_m, sub_m, feats in zip(self.model_weights_, self.sub_models_, self.sub_features_):
            sub_ds = _subset_dataset_features(dataset, feats)
            p = sub_m.predict_proba(sub_ds, segment).reindex(x_df.index).to_numpy(dtype=np.float64)
            total += float(w_m) * p
        return pd.DataFrame(total, index=x_df.index, columns=list(DIRECTION_CLASSES), dtype=np.float64)

    def predict(self, dataset: DatasetH, segment: str | slice = "test") -> pd.Series:
        if self.task_type == "direction":
            proba = self.predict_proba(dataset, segment)
            s = proba["up"] - proba["down"]
            s.name = "score"
            return s
        x_df = self._prepare_features_infer(dataset, segment)
        total = np.zeros(len(x_df), dtype=np.float64)
        for w_m, sub_m, feats in zip(self.model_weights_, self.sub_models_, self.sub_features_):
            sub_ds = _subset_dataset_features(dataset, feats)
            p = sub_m.predict(sub_ds, segment).reindex(x_df.index).to_numpy(dtype=np.float64)
            total += float(w_m) * p
        return pd.Series(total, index=x_df.index, name="score", dtype=np.float64)

    def _export_weights(self) -> dict[str, Any]:
        return {
            "model_weights": self.model_weights_.tolist(),
            "sub_features": self.sub_features_,
            "sub_models": [
                {
                    "class": m.__class__.__name__,
                    "hyperparams": m._get_hyperparams(),
                    "weights": m._export_weights(),
                }
                for m in self.sub_models_
            ],
        }

    def _load_weights(self, weights: Mapping[str, Any], feature_names: list[str]) -> None:
        _ = feature_names
        self.model_weights_ = np.asarray(weights["model_weights"], dtype=np.float64)
        self.sub_features_ = [[str(f) for f in flist] for flist in weights["sub_features"]]
        self.sub_models_ = []
        for entry, feats in zip(weights["sub_models"], self.sub_features_):
            sub_m: Model = init_instance_by_config(
                {"class": entry["class"], "kwargs": entry["hyperparams"]},
                accept_types=Model,
            )
            sub_m.feature_names_ = list(feats)
            sub_m._load_weights(entry["weights"], sub_m.feature_names_)
            sub_m.fitted = True
            self.sub_models_.append(sub_m)
