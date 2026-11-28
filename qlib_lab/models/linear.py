"""Ridge & Huber Linear Regression Model with warm-start L2 prior shrinkage finetuning."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import numpy as np
import pandas as pd

from qlib_lab.data.dataset import DatasetH
from qlib_lab.models.base import ModelFT, Reweighter
from qlib_lab.registry import register_component


@register_component("model")
class RidgeLinearModel(ModelFT):
    """Linear model supporting L2 (closed-form Ridge) and IRLS Huber loss + ModelFT shrinkage."""

    task_type = "regression"

    def __init__(
        self,
        alpha: float = 1.0,
        loss: str = "l2",
        huber_delta: float = 1.35,
        fit_intercept: bool = True,
        finetune_alpha: float = 5.0,
        max_iter: int = 50,
        target_col: str | None = None,
    ) -> None:
        super().__init__()
        if alpha < 0:
            raise ValueError("alpha must be >= 0")
        if loss not in ("l2", "huber"):
            raise ValueError(f"loss must be 'l2' or 'huber', got {loss!r}")
        if huber_delta <= 0:
            raise ValueError("huber_delta must be > 0")
        self.alpha = float(alpha)
        self.loss = loss
        self.huber_delta = float(huber_delta)
        self.fit_intercept = bool(fit_intercept)
        self.finetune_alpha = float(finetune_alpha)
        self.max_iter = int(max_iter)
        self.target_col = target_col

        self.coef_: np.ndarray = np.empty(0, dtype=np.float64)
        self.intercept_: float = 0.0
        self.sample_loss_trajectory_: np.ndarray | None = None

    def _get_hyperparams(self) -> dict[str, Any]:
        return {
            "alpha": self.alpha,
            "loss": self.loss,
            "huber_delta": self.huber_delta,
            "fit_intercept": self.fit_intercept,
            "finetune_alpha": self.finetune_alpha,
            "max_iter": self.max_iter,
            "target_col": self.target_col,
        }

    def _solve_weighted_ridge(
        self,
        X: np.ndarray,
        y: np.ndarray,
        w: np.ndarray,
        prior_coef: np.ndarray | None = None,
        prior_intercept: float = 0.0,
        prior_alpha: float = 0.0,
    ) -> tuple[np.ndarray, float]:
        n, p = X.shape
        w_norm = w / max(float(w.sum()), 1e-12) * float(n)
        reg_total = self.alpha + prior_alpha

        if self.fit_intercept:
            w_sum = max(float(w_norm.sum()), 1e-12)
            x_mean = (w_norm[:, None] * X).sum(axis=0) / w_sum
            y_mean = float((w_norm * y).sum() / w_sum)
            Xc = X - x_mean
            yc = y - y_mean
        else:
            x_mean = np.zeros(p, dtype=np.float64)
            y_mean = 0.0
            Xc = X
            yc = y

        # Solve (Xc^T diag(w_norm) Xc / n + reg_total * I) coef = Xc^T diag(w_norm) yc / n + prior_alpha * prior_coef
        sqrt_w = np.sqrt(w_norm / float(n))
        Xw = Xc * sqrt_w[:, None]
        yw = yc * sqrt_w
        gram = Xw.T @ Xw + (reg_total + 1e-12) * np.eye(p, dtype=np.float64)
        rhs = Xw.T @ yw
        if prior_coef is not None and prior_alpha > 0.0:
            rhs = rhs + prior_alpha * prior_coef
        coef = np.linalg.solve(gram, rhs)
        if self.fit_intercept:
            if prior_coef is not None and prior_alpha > 0.0:
                # Mild shrinkage of intercept toward prior_intercept only via data mean
                raw_b = float(y_mean - x_mean @ coef)
                intercept = float((raw_b + 0.1 * prior_alpha * prior_intercept) / (1.0 + 0.1 * prior_alpha))
            else:
                intercept = float(y_mean - x_mean @ coef)
        else:
            intercept = 0.0
        return coef, intercept

    def _fit_arrays(
        self,
        X: np.ndarray,
        y: np.ndarray,
        w: np.ndarray,
        *,
        prior_coef: np.ndarray | None = None,
        prior_intercept: float = 0.0,
        prior_alpha: float = 0.0,
    ) -> None:
        X_clean = np.nan_to_num(X, nan=0.0)
        traj: list[np.ndarray] = []

        if self.loss == "l2":
            # Record a 4-step regularization trajectory from strong ridge down to target alpha for DoubleEnsemble SR
            for mult in (8.0, 4.0, 2.0, 1.0):
                c_step, b_step = self._solve_weighted_ridge(
                    X_clean,
                    y,
                    w,
                    prior_coef=prior_coef,
                    prior_intercept=prior_intercept,
                    prior_alpha=prior_alpha + (mult - 1.0) * max(self.alpha, 0.1),
                )
                pred_step = X_clean @ c_step + b_step
                traj.append(0.5 * (y - pred_step) ** 2)
            self.coef_, self.intercept_ = c_step, b_step
        else:
            coef, intercept = self._solve_weighted_ridge(
                X_clean,
                y,
                w,
                prior_coef=prior_coef,
                prior_intercept=prior_intercept,
                prior_alpha=prior_alpha,
            )
            delta = self.huber_delta
            for _it in range(max(1, self.max_iter)):
                resid = y - (X_clean @ coef + intercept)
                abs_r = np.abs(resid)
                huber_loss = np.where(abs_r <= delta, 0.5 * resid * resid, delta * (abs_r - 0.5 * delta))
                traj.append(huber_loss)
                irls_w = w * np.where(abs_r <= delta, 1.0, delta / np.maximum(abs_r, 1e-12))
                new_coef, new_intercept = self._solve_weighted_ridge(
                    X_clean,
                    y,
                    irls_w,
                    prior_coef=prior_coef,
                    prior_intercept=prior_intercept,
                    prior_alpha=prior_alpha,
                )
                diff = float(np.max(np.abs(new_coef - coef))) + abs(new_intercept - intercept)
                coef, intercept = new_coef, new_intercept
                if diff < 1e-8:
                    break
            self.coef_, self.intercept_ = coef, intercept

        self.sample_loss_trajectory_ = np.vstack(traj)

    def fit(self, dataset: DatasetH, reweighter: Reweighter | None = None) -> RidgeLinearModel:
        x_df, y, w, _col = self._prepare_xy_learn(dataset, "train", self.target_col, reweighter=reweighter)
        self.feature_names_ = [str(c) for c in x_df.columns]
        X = x_df.to_numpy(dtype=np.float64)
        self._fit_arrays(X, y, w)
        self.training_cutoff_ = dataset.effective_training_cutoff(include_valid=False)
        self.parent_model_sha256_ = None
        self.last_frozen_sha256_ = None
        self.fitted = True
        return self

    def finetune(
        self,
        dataset: DatasetH,
        reweighter: Reweighter | None = None,
        *,
        finetune_alpha: float | None = None,
        **kwargs: Any,
    ) -> RidgeLinearModel:
        _ = kwargs
        if not self.fitted:
            raise RuntimeError("Cannot finetune an unfitted RidgeLinearModel")
        parent_sha = self._snapshot_parent_sha256()
        prior_coef = self.coef_.copy()
        prior_intercept = float(self.intercept_)

        x_df, y, w, _col = self._prepare_xy_learn(dataset, "train", self.target_col, reweighter=reweighter)
        if [str(c) for c in x_df.columns] != self.feature_names_:
            raise ValueError("Feature columns changed during RidgeLinearModel.finetune")

        ft_alpha = self.finetune_alpha if finetune_alpha is None else float(finetune_alpha)
        self._fit_arrays(
            x_df.to_numpy(dtype=np.float64),
            y,
            w,
            prior_coef=prior_coef,
            prior_intercept=prior_intercept,
            prior_alpha=ft_alpha,
        )
        self.training_cutoff_ = dataset.effective_training_cutoff(include_valid=False)
        self.parent_model_sha256_ = parent_sha
        self.last_frozen_sha256_ = None
        self.fitted = True
        return self

    def predict(self, dataset: DatasetH, segment: str | slice = "test") -> pd.Series:
        x_df = self._prepare_features_infer(dataset, segment)
        X = x_df.to_numpy(dtype=np.float64)
        row_ok = np.all(np.isfinite(X), axis=1)
        preds = np.full(len(x_df), np.nan, dtype=np.float64)
        if np.any(row_ok):
            preds[row_ok] = X[row_ok] @ self.coef_ + self.intercept_
        return pd.Series(preds, index=x_df.index, name="score", dtype=np.float64)

    def _export_weights(self) -> dict[str, Any]:
        return {
            "coef": self.coef_.tolist(),
            "intercept": float(self.intercept_),
        }

    def _load_weights(self, weights: Mapping[str, Any], feature_names: list[str]) -> None:
        self.coef_ = np.asarray(weights["coef"], dtype=np.float64)
        if self.coef_.size != len(feature_names):
            raise ValueError("Coefficient dimension mismatch in RidgeLinearModel")
        self.intercept_ = float(weights["intercept"])
