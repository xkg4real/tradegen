"""Direction probability models: MultinomialDirectionModel (M/B1), PriorFrequencyBaselineModel (B0), MovingBlockBootstrapModel (B2)."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
import math
import random
from typing import Any

import numpy as np
import pandas as pd
from scipy.optimize import minimize, minimize_scalar

from qlib_lab.data.dataset import DatasetH
from qlib_lab.data.handler import DataHandlerLP
from qlib_lab.data.labels import DIRECTION_CLASSES
from qlib_lab.exceptions import SparseEventRefusalError
from qlib_lab.models.base import Model, ModelFT, Reweighter
from qlib_lab.registry import register_component


def _softmax_2d(logits: np.ndarray) -> np.ndarray:
    shifted = logits - np.max(logits, axis=1, keepdims=True)
    exp_z = np.exp(shifted)
    return exp_z / np.sum(exp_z, axis=1, keepdims=True)


@register_component("model")
class MultinomialDirectionModel(ModelFT):
    """Convex 3-class ('up', 'down', 'neutral') multinomial logistic regression (L-BFGS-B).

    Features:
    - Training-window standardization (stored in FrozenModelSpec)
    - Sparse binary/event floor (`min_event_count=8`, refusing under-sampled D1 features)
    - Optional `valid` temperature scaling calibration
    - Warm-start L2 prior shrinkage `finetune` recording `parent_model_sha256`
    """

    task_type = "direction"

    def __init__(
        self,
        reg_lambda: float = 1.0,
        standardize: bool = True,
        calibrate_temperature: bool = True,
        event_features: Sequence[str] = (),
        min_event_count: int = 8,
        finetune_lambda: float = 5.0,
        max_iter: int = 200,
        target_col: str = "direction_class",
    ) -> None:
        super().__init__()
        if reg_lambda < 0:
            raise ValueError("reg_lambda must be >= 0")
        if min_event_count < 0:
            raise ValueError("min_event_count must be >= 0")
        self.reg_lambda = float(reg_lambda)
        self.standardize = bool(standardize)
        self.calibrate_temperature = bool(calibrate_temperature)
        self.event_features = tuple(str(f) for f in event_features)
        self.min_event_count = int(min_event_count)
        self.finetune_lambda = float(finetune_lambda)
        self.max_iter = int(max_iter)
        self.target_col = str(target_col)

        self.mean_: np.ndarray = np.empty(0, dtype=np.float64)
        self.std_: np.ndarray = np.empty(0, dtype=np.float64)
        self.W_: np.ndarray = np.empty((0, 3), dtype=np.float64)
        self.b_: np.ndarray = np.zeros(3, dtype=np.float64)
        self.temperature_: float = 1.0
        self.sample_loss_trajectory_: np.ndarray | None = None

    def _get_hyperparams(self) -> dict[str, Any]:
        return {
            "reg_lambda": self.reg_lambda,
            "standardize": self.standardize,
            "calibrate_temperature": self.calibrate_temperature,
            "event_features": list(self.event_features),
            "min_event_count": self.min_event_count,
            "finetune_lambda": self.finetune_lambda,
            "max_iter": self.max_iter,
            "target_col": self.target_col,
        }

    def _check_sparse_events(self, x_df: pd.DataFrame) -> None:
        for ef in self.event_features:
            if ef not in x_df.columns:
                raise KeyError(f"Declared event_feature {ef!r} not in training features {list(x_df.columns)}")
            vals = x_df[ef].to_numpy(dtype=np.float64)
            n_events = int(np.sum(np.isfinite(vals) & (np.abs(vals) > 1e-12)))
            if n_events < self.min_event_count:
                raise SparseEventRefusalError(
                    f"Event feature {ef!r} has only {n_events} non-zero event(s) in training "
                    f"(< min_event_count={self.min_event_count}); refused per D1 sparse event floor"
                )

    def _optimize_multinomial(
        self,
        Xs: np.ndarray,
        y_int: np.ndarray,
        w: np.ndarray,
        *,
        init_W: np.ndarray | None = None,
        init_b: np.ndarray | None = None,
        prior_W: np.ndarray | None = None,
        prior_lambda: float = 0.0,
    ) -> tuple[np.ndarray, np.ndarray]:
        n, p = Xs.shape
        n_classes = 3
        w_norm = w / max(float(w.sum()), 1e-12)
        Y_onehot = np.zeros((n, n_classes), dtype=np.float64)
        Y_onehot[np.arange(n), y_int] = 1.0

        w0 = np.zeros((p, n_classes), dtype=np.float64) if init_W is None else init_W.copy()
        if init_b is None:
            # Initialize intercept to log empirical frequencies
            counts = np.bincount(y_int, weights=w, minlength=n_classes).astype(np.float64)
            probs0 = np.clip(counts / max(float(counts.sum()), 1e-12), 1e-4, 1.0)
            b0 = np.log(probs0)
            b0 -= b0.mean()
        else:
            b0 = init_b.copy()

        theta0 = np.concatenate([w0.ravel(), b0])
        traj: list[np.ndarray] = []

        def _obj_grad(theta: np.ndarray) -> tuple[float, np.ndarray]:
            W = theta[: p * n_classes].reshape(p, n_classes)
            b = theta[p * n_classes :]
            logits = Xs @ W + b[None, :]
            probs = _softmax_2d(logits)
            sample_nll = -np.log(np.clip(probs[np.arange(n), y_int], 1e-15, 1.0))
            if len(traj) < 16:
                traj.append(sample_nll)

            nll = float(np.sum(w_norm * sample_nll))
            reg = 0.5 * (self.reg_lambda / float(n)) * float(np.sum(W * W))
            diff = (probs - Y_onehot) * w_norm[:, None]
            grad_W = Xs.T @ diff + (self.reg_lambda / float(n)) * W
            if prior_W is not None and prior_lambda > 0.0:
                delta_W = W - prior_W
                reg += 0.5 * (prior_lambda / float(n)) * float(np.sum(delta_W * delta_W))
                grad_W += (prior_lambda / float(n)) * delta_W
            grad_b = np.sum(diff, axis=0)
            return nll + reg, np.concatenate([grad_W.ravel(), grad_b])

        res = minimize(
            _obj_grad,
            theta0,
            method="L-BFGS-B",
            jac=True,
            options={"maxiter": self.max_iter, "ftol": 1e-10, "gtol": 1e-8},
        )
        W_opt = res.x[: p * n_classes].reshape(p, n_classes)
        b_opt = res.x[p * n_classes :]
        b_opt = b_opt - float(np.mean(b_opt))

        final_probs = _softmax_2d(Xs @ W_opt + b_opt[None, :])
        traj.append(-np.log(np.clip(final_probs[np.arange(n), y_int], 1e-15, 1.0)))
        self.sample_loss_trajectory_ = np.vstack(traj)
        return W_opt, b_opt

    def _fit_temperature_on_valid(self, dataset: DatasetH) -> float:
        if not self.calibrate_temperature or "valid" not in dataset.segments:
            return 1.0
        try:
            x_val_df, y_val, w_val, _ = self._prepare_xy_learn(dataset, "valid", self.target_col)
        except ValueError:
            return 1.0
        if len(y_val) < 10:
            return 1.0
        Xv = x_val_df[self.feature_names_].to_numpy(dtype=np.float64)
        ok = np.all(np.isfinite(Xv), axis=1)
        if int(np.sum(ok)) < 10:
            return 1.0
        Xvs = (Xv[ok] - self.mean_) / self.std_
        yv_int = y_val[ok].astype(np.int64)
        wv = w_val[ok] / max(float(w_val[ok].sum()), 1e-12)
        raw_logits = Xvs @ self.W_ + self.b_[None, :]

        def _temp_nll(temp: float) -> float:
            probs = _softmax_2d(raw_logits / float(temp))
            return float(-np.sum(wv * np.log(np.clip(probs[np.arange(yv_int.size), yv_int], 1e-15, 1.0))))

        opt = minimize_scalar(_temp_nll, bounds=(0.25, 4.0), method="bounded")
        return float(opt.x) if opt.success and math.isfinite(float(opt.x)) else 1.0

    def fit(self, dataset: DatasetH, reweighter: Reweighter | None = None) -> MultinomialDirectionModel:
        x_df, y, w, _ = self._prepare_xy_learn(dataset, "train", self.target_col, reweighter=reweighter)
        self._check_sparse_events(x_df)
        self.feature_names_ = [str(c) for c in x_df.columns]
        X = x_df.to_numpy(dtype=np.float64)
        ok = np.all(np.isfinite(X), axis=1)
        X, y, w = X[ok], y[ok], w[ok]
        y_int = y.astype(np.int64)
        if np.any((y_int < 0) | (y_int > 2)):
            raise ValueError("direction_class labels must be integers in {0 (up), 1 (down), 2 (neutral)}")

        if self.standardize:
            self.mean_ = np.mean(X, axis=0)
            sd = np.std(X, axis=0, ddof=1) if X.shape[0] > 1 else np.ones(X.shape[1])
            self.std_ = np.where(sd > 1e-12, sd, 1.0)
        else:
            self.mean_ = np.zeros(X.shape[1], dtype=np.float64)
            self.std_ = np.ones(X.shape[1], dtype=np.float64)

        Xs = (X - self.mean_) / self.std_
        self.W_, self.b_ = self._optimize_multinomial(Xs, y_int, w)
        self.fitted = True
        self.temperature_ = self._fit_temperature_on_valid(dataset)
        used_valid = self.calibrate_temperature and ("valid" in dataset.segments)
        self.training_cutoff_ = dataset.effective_training_cutoff(include_valid=used_valid)
        self.parent_model_sha256_ = None
        self.last_frozen_sha256_ = None
        return self

    def finetune(
        self,
        dataset: DatasetH,
        reweighter: Reweighter | None = None,
        *,
        finetune_lambda: float | None = None,
        **kwargs: Any,
    ) -> MultinomialDirectionModel:
        _ = kwargs
        if not self.fitted:
            raise RuntimeError("Cannot finetune an unfitted MultinomialDirectionModel")
        parent_sha = self._snapshot_parent_sha256()
        prior_W = self.W_.copy()
        prior_b = self.b_.copy()

        x_df, y, w, _ = self._prepare_xy_learn(dataset, "train", self.target_col, reweighter=reweighter)
        if [str(c) for c in x_df.columns] != self.feature_names_:
            raise ValueError("Feature columns changed during MultinomialDirectionModel.finetune")
        if self.event_features:
            self._check_sparse_events(x_df)

        X = x_df.to_numpy(dtype=np.float64)
        ok = np.all(np.isfinite(X), axis=1)
        X, y, w = X[ok], y[ok], w[ok]
        y_int = y.astype(np.int64)

        # Keep frozen standardization scale so prior_W stays in identical coordinate basis!
        Xs = (X - self.mean_) / self.std_
        ft_lam = self.finetune_lambda if finetune_lambda is None else float(finetune_lambda)
        self.W_, self.b_ = self._optimize_multinomial(
            Xs, y_int, w, init_W=prior_W, init_b=prior_b, prior_W=prior_W, prior_lambda=ft_lam
        )
        self.temperature_ = self._fit_temperature_on_valid(dataset)
        used_valid = self.calibrate_temperature and ("valid" in dataset.segments)
        self.training_cutoff_ = dataset.effective_training_cutoff(include_valid=used_valid)
        self.parent_model_sha256_ = parent_sha
        self.last_frozen_sha256_ = None
        return self

    def predict_proba(self, dataset: DatasetH, segment: str | slice = "test") -> pd.DataFrame:
        x_df = self._prepare_features_infer(dataset, segment)
        X = x_df.to_numpy(dtype=np.float64)
        ok = np.all(np.isfinite(X), axis=1)
        probs = np.full((len(x_df), 3), np.nan, dtype=np.float64)
        if np.any(ok):
            Xs = (X[ok] - self.mean_) / self.std_
            logits = (Xs @ self.W_ + self.b_[None, :]) / max(self.temperature_, 1e-6)
            probs[ok] = _softmax_2d(logits)
        return pd.DataFrame(probs, index=x_df.index, columns=list(DIRECTION_CLASSES), dtype=np.float64)

    def predict(self, dataset: DatasetH, segment: str | slice = "test") -> pd.Series:
        proba = self.predict_proba(dataset, segment)
        score = proba["up"] - proba["down"]
        score.name = "score"
        return score

    def _export_weights(self) -> dict[str, Any]:
        return {
            "class_order": list(DIRECTION_CLASSES),
            "mean": self.mean_.tolist(),
            "std": self.std_.tolist(),
            "W": self.W_.tolist(),
            "b": self.b_.tolist(),
            "temperature": float(self.temperature_),
        }

    def _load_weights(self, weights: Mapping[str, Any], feature_names: list[str]) -> None:
        if list(weights.get("class_order", [])) != list(DIRECTION_CLASSES):
            raise ValueError("Unexpected class_order in MultinomialDirectionModel weights")
        self.mean_ = np.asarray(weights["mean"], dtype=np.float64)
        self.std_ = np.asarray(weights["std"], dtype=np.float64)
        self.W_ = np.asarray(weights["W"], dtype=np.float64)
        self.b_ = np.asarray(weights["b"], dtype=np.float64)
        self.temperature_ = float(weights.get("temperature", 1.0))
        if self.W_.shape != (len(feature_names), 3):
            raise ValueError("Weight matrix shape mismatch in MultinomialDirectionModel")


@register_component("model")
class PriorFrequencyBaselineModel(Model):
    """B0 Baseline: empirical training-window class frequencies over ('up', 'down', 'neutral')."""

    task_type = "direction"

    def __init__(self, target_col: str = "direction_class", smoothing_eps: float = 1e-6) -> None:
        super().__init__()
        self.target_col = str(target_col)
        self.smoothing_eps = float(smoothing_eps)
        self.priors_: np.ndarray = np.array([1.0 / 3.0, 1.0 / 3.0, 1.0 / 3.0], dtype=np.float64)

    def _get_hyperparams(self) -> dict[str, Any]:
        return {"target_col": self.target_col, "smoothing_eps": self.smoothing_eps}

    def fit(self, dataset: DatasetH, reweighter: Reweighter | None = None) -> PriorFrequencyBaselineModel:
        x_df, y, w, _ = self._prepare_xy_learn(dataset, "train", self.target_col, reweighter=reweighter)
        self.feature_names_ = [str(c) for c in x_df.columns]
        y_int = y.astype(np.int64)
        counts = np.bincount(y_int, weights=w, minlength=3).astype(np.float64)
        counts = np.maximum(counts, self.smoothing_eps)
        self.priors_ = counts / float(counts.sum())
        self.training_cutoff_ = dataset.effective_training_cutoff(include_valid=False)
        self.fitted = True
        return self

    def predict_proba(self, dataset: DatasetH, segment: str | slice = "test") -> pd.DataFrame:
        x_df = self._prepare_features_infer(dataset, segment)
        X = x_df.to_numpy(dtype=np.float64)
        ok = np.all(np.isfinite(X), axis=1)
        probs = np.full((len(x_df), 3), np.nan, dtype=np.float64)
        probs[ok] = self.priors_[None, :]
        return pd.DataFrame(probs, index=x_df.index, columns=list(DIRECTION_CLASSES), dtype=np.float64)

    def predict(self, dataset: DatasetH, segment: str | slice = "test") -> pd.Series:
        proba = self.predict_proba(dataset, segment)
        s = proba["up"] - proba["down"]
        s.name = "score"
        return s

    def _export_weights(self) -> dict[str, Any]:
        return {"class_order": list(DIRECTION_CLASSES), "priors": self.priors_.tolist()}

    def _load_weights(self, weights: Mapping[str, Any], feature_names: list[str]) -> None:
        _ = feature_names
        self.priors_ = np.asarray(weights["priors"], dtype=np.float64)
        self.priors_ /= float(self.priors_.sum())


@register_component("model")
class MovingBlockBootstrapModel(Model):
    """B2 Baseline: PR #70 moving-block bootstrap path simulator (`adaptive_bid_gap_preview.sample_direction`).

    Reported on Stage-1 Criterion 1 only (path fractions can hit 0.0, making log-loss infinite per design doc §5).
    """

    task_type = "direction"

    def __init__(
        self,
        lookback: int = 24,
        block: int = 2,
        horizon: int = 2,
        paths: int = 1000,
        hurdle_bps: int = 10,
        seed: int = 11,
        log_return_feature: str | None = None,
    ) -> None:
        super().__init__()
        if block < 1 or horizon < 1 or lookback < block or paths < 64:
            raise ValueError("Invalid MovingBlockBootstrapModel parameters")
        self.lookback = int(lookback)
        self.block = int(block)
        self.horizon = int(horizon)
        self.paths = int(paths)
        self.hurdle_bps = int(hurdle_bps)
        self.seed = int(seed)
        self.log_return_feature = log_return_feature

    def _get_hyperparams(self) -> dict[str, Any]:
        return {
            "lookback": self.lookback,
            "block": self.block,
            "horizon": self.horizon,
            "paths": self.paths,
            "hurdle_bps": self.hurdle_bps,
            "seed": self.seed,
            "log_return_feature": self.log_return_feature,
        }

    def fit(self, dataset: DatasetH, reweighter: Reweighter | None = None) -> MovingBlockBootstrapModel:
        _ = reweighter
        x_df = dataset.prepare("train", col_set="feature", data_key=DataHandlerLP.DK_I)
        self.feature_names_ = [str(c) for c in x_df.columns]
        if self.log_return_feature is not None and self.log_return_feature not in self.feature_names_:
            raise KeyError(f"log_return_feature {self.log_return_feature!r} not in {self.feature_names_}")
        self.training_cutoff_ = dataset.effective_training_cutoff(include_valid=False)
        self.fitted = True
        return self

    def predict_proba(self, dataset: DatasetH, segment: str | slice = "test") -> pd.DataFrame:
        if not self.fitted:
            raise RuntimeError("MovingBlockBootstrapModel.fit() must be called before predict_proba()")
        # Fetch full causal DK_R / DK_I feature history up to segment end so trailing lookback is available
        target_df = self._prepare_features_infer(dataset, segment)
        if target_df.empty:
            return pd.DataFrame(columns=list(DIRECTION_CLASSES), index=target_df.index, dtype=np.float64)

        col_name = self.log_return_feature or self.feature_names_[0]
        # Fetch unstandardized DK_R feature column so hurdle_bps compares against true log returns!
        max_dt = target_df.index.get_level_values("datetime").max()
        full_raw = dataset.handler.fetch(slice(None, max_dt), col_set="feature", data_key=DataHandlerLP.DK_R)
        ret_series = full_raw[col_name]

        up_barrier = math.log1p(self.hurdle_bps / 10000.0)
        down_barrier = math.log1p(-self.hurdle_bps / 10000.0)
        probs = np.full((len(target_df), 3), np.nan, dtype=np.float64)

        target_pos_map = {idx: pos for pos, idx in enumerate(target_df.index)}
        inst_all = ret_series.index.get_level_values("instrument")
        dt_all = ret_series.index.get_level_values("datetime")

        for inst in target_df.index.get_level_values("instrument").unique():
            mask = inst_all == inst
            inst_rets = ret_series.loc[mask].to_numpy(dtype=np.float64)
            inst_dts = dt_all[mask]
            for i in range(self.lookback - 1, len(inst_rets)):
                key = (inst_dts[i], inst)
                if key not in target_pos_map:
                    continue
                win = inst_rets[i - self.lookback + 1 : i + 1]
                if not np.all(np.isfinite(win)):
                    continue
                origin_ep = int(pd.Timestamp(inst_dts[i]).timestamp())
                rng = random.Random((self.seed << 40) + origin_ep)
                pos_cnt = 0
                neg_cnt = 0
                win_list = win.tolist()
                max_start = self.lookback - self.block + 1
                for _ in range(self.paths):
                    rem = self.horizon
                    tot = 0.0
                    while rem > 0:
                        take = min(rem, self.block)
                        st = rng.randrange(max_start)
                        tot += math.fsum(win_list[st : st + take])
                        rem -= take
                    if tot > up_barrier:
                        pos_cnt += 1
                    elif tot < down_barrier:
                        neg_cnt += 1
                neu_cnt = self.paths - pos_cnt - neg_cnt
                out_row = target_pos_map[key]
                probs[out_row, 0] = pos_cnt / float(self.paths)
                probs[out_row, 1] = neg_cnt / float(self.paths)
                probs[out_row, 2] = neu_cnt / float(self.paths)

        return pd.DataFrame(probs, index=target_df.index, columns=list(DIRECTION_CLASSES), dtype=np.float64)

    def predict(self, dataset: DatasetH, segment: str | slice = "test") -> pd.Series:
        proba = self.predict_proba(dataset, segment)
        s = proba["up"] - proba["down"]
        s.name = "score"
        return s

    def _export_weights(self) -> dict[str, Any]:
        return {"rule": "moving-block-v1"}

    def _load_weights(self, weights: Mapping[str, Any], feature_names: list[str]) -> None:
        _ = (weights, feature_names)
