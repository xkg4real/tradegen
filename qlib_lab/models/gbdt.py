"""2nd-Order Newton 255-bin Histogram GBDT (`HistGBDTModel`) backed by C++17 _accel + NumPy parity."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from qlib_lab import _accel
from qlib_lab.data.dataset import DatasetH
from qlib_lab.data.labels import DIRECTION_CLASSES
from qlib_lab.models.base import ModelFT, Reweighter
from qlib_lab.registry import register_component


def _softmax_rows(logits: np.ndarray) -> np.ndarray:
    shifted = logits - np.max(logits, axis=1, keepdims=True)
    ex = np.exp(shifted)
    return ex / np.sum(ex, axis=1, keepdims=True)


@dataclass
class _TreeNode:
    is_leaf: bool
    leaf_value: float = 0.0
    feature: int = -1
    threshold_bin: int = -1
    nan_go_left: bool = True
    left: int = -1
    right: int = -1

    def to_dict(self) -> dict[str, Any]:
        if self.is_leaf:
            return {"leaf": True, "v": float(self.leaf_value)}
        return {
            "leaf": False,
            "f": int(self.feature),
            "b": int(self.threshold_bin),
            "nl": bool(self.nan_go_left),
            "l": int(self.left),
            "r": int(self.right),
        }

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> _TreeNode:
        if d.get("leaf"):
            return cls(is_leaf=True, leaf_value=float(d["v"]))
        return cls(
            is_leaf=False,
            feature=int(d["f"]),
            threshold_bin=int(d["b"]),
            nan_go_left=bool(d["nl"]),
            left=int(d["l"]),
            right=int(d["r"]),
        )


class _HistTree:
    """Single Newton histogram regression tree with explicit NaN routing."""

    def __init__(self, nodes: list[_TreeNode] | None = None) -> None:
        self.nodes: list[_TreeNode] = nodes or []

    def predict_binned(self, X_binned: np.ndarray) -> np.ndarray:
        n = X_binned.shape[0]
        out = np.empty(n, dtype=np.float64)
        if not self.nodes:
            out.fill(0.0)
            return out

        # Vectorized traversal across samples using node index array
        cur_node_idx = np.zeros(n, dtype=np.int32)
        active = np.arange(n, dtype=np.int32)

        # Traverse depth-by-depth over non-leaf assignments
        while active.size > 0:
            uniq_nodes = np.unique(cur_node_idx[active])
            still_active_mask = np.zeros(active.size, dtype=bool)
            for nid in uniq_nodes:
                node = self.nodes[int(nid)]
                sub_mask = cur_node_idx[active] == nid
                sub_samples = active[sub_mask]
                if node.is_leaf:
                    out[sub_samples] = node.leaf_value
                else:
                    bins = X_binned[sub_samples, node.feature]
                    is_nan = bins == 255
                    if node.nan_go_left:
                        go_left = is_nan | (bins <= node.threshold_bin)
                    else:
                        go_left = (~is_nan) & (bins <= node.threshold_bin)
                    cur_node_idx[sub_samples] = np.where(go_left, node.left, node.right)
                    still_active_mask[sub_mask] = True
            active = active[still_active_mask]
        return out

    def scale_leaves(self, factor: float) -> None:
        for node in self.nodes:
            if node.is_leaf:
                node.leaf_value *= float(factor)

    def to_list(self) -> list[dict[str, Any]]:
        return [n.to_dict() for n in self.nodes]

    @classmethod
    def from_list(cls, items: list[Mapping[str, Any]]) -> _HistTree:
        return cls([_TreeNode.from_dict(d) for d in items])


@register_component("model")
class HistGBDTModel(ModelFT):
    """2nd-Order Newton 255-bin Histogram GBDT supporting 'regression' & 3-class 'multiclass' softmax.

    Features:
    - C++17 `hist_build_f64`, `hist_subtract_f64` (parent-minus-smaller-child!), and `hist_best_split_f64`
      with automatic bit-exact NumPy fallback when `QLIB_LAB_DISABLE_ACCEL=1`
    - Dedicated uint8 bin 255 for NaN values + learned optimal NaN routing per split (never imputes!)
    - Early stopping on `valid` segment
    - Continuation + leaf-shrinkage `finetune` (`ModelFT`) recording `parent_model_sha256`
    """

    def __init__(
        self,
        loss: str = "regression",
        num_boost_round: int = 40,
        learning_rate: float = 0.1,
        max_depth: int = 4,
        max_leaves: int = 15,
        max_bins: int = 255,
        min_samples_leaf: int = 10,
        min_child_weight: float = 1e-3,
        reg_lambda: float = 1.0,
        min_split_gain: float = 0.0,
        colsample_bytree: float = 1.0,
        early_stopping_rounds: int | None = 10,
        seed: int = 11,
        target_col: str | None = None,
    ) -> None:
        super().__init__()
        if loss not in ("regression", "multiclass"):
            raise ValueError(f"loss must be 'regression' or 'multiclass', got {loss!r}")
        if not (2 <= int(max_bins) <= 255):
            raise ValueError(f"max_bins must be in [2, 255] (bin 255 reserved for NaN), got {max_bins}")
        if num_boost_round < 1 or max_depth < 1 or max_leaves < 2:
            raise ValueError("Invalid tree capacity parameters in HistGBDTModel")
        if not (0.0 < float(colsample_bytree) <= 1.0):
            raise ValueError("colsample_bytree must lie in (0, 1]")

        self.loss = loss
        self.task_type = "direction" if loss == "multiclass" else "regression"
        self.num_boost_round = int(num_boost_round)
        self.learning_rate = float(learning_rate)
        self.max_depth = int(max_depth)
        self.max_leaves = int(max_leaves)
        self.max_bins = int(max_bins)
        self.min_samples_leaf = int(min_samples_leaf)
        self.min_child_weight = float(min_child_weight)
        self.reg_lambda = float(reg_lambda)
        self.min_split_gain = float(min_split_gain)
        self.colsample_bytree = float(colsample_bytree)
        self.early_stopping_rounds = int(early_stopping_rounds) if early_stopping_rounds is not None else None
        self.seed = int(seed)
        self.target_col = target_col

        self.bin_edges_: list[np.ndarray] = []
        self.n_finite_bins_: np.ndarray = np.empty(0, dtype=np.int32)
        self.base_margin_: np.ndarray = np.zeros(1, dtype=np.float64)
        # List of rounds; each round has 1 tree (regression) or 3 trees (multiclass)
        self.trees_: list[list[_HistTree]] = []
        self.best_iteration_: int = 0
        self.sample_loss_trajectory_: np.ndarray | None = None

    def _get_hyperparams(self) -> dict[str, Any]:
        return {
            "loss": self.loss,
            "num_boost_round": self.num_boost_round,
            "learning_rate": self.learning_rate,
            "max_depth": self.max_depth,
            "max_leaves": self.max_leaves,
            "max_bins": self.max_bins,
            "min_samples_leaf": self.min_samples_leaf,
            "min_child_weight": self.min_child_weight,
            "reg_lambda": self.reg_lambda,
            "min_split_gain": self.min_split_gain,
            "colsample_bytree": self.colsample_bytree,
            "early_stopping_rounds": self.early_stopping_rounds,
            "seed": self.seed,
            "target_col": self.target_col,
        }

    def _fit_binner(self, X: np.ndarray) -> None:
        n_features = X.shape[1]
        self.bin_edges_ = []
        n_fin = np.zeros(n_features, dtype=np.int32)
        for f in range(n_features):
            col = X[:, f]
            fin = col[np.isfinite(col)]
            if fin.size == 0:
                self.bin_edges_.append(np.empty(0, dtype=np.float64))
                n_fin[f] = 1
                continue
            uniq = np.unique(fin)
            if uniq.size <= 1:
                self.bin_edges_.append(np.empty(0, dtype=np.float64))
                n_fin[f] = 1
            elif uniq.size <= self.max_bins:
                edges = 0.5 * (uniq[:-1] + uniq[1:])
                self.bin_edges_.append(np.asarray(edges, dtype=np.float64))
                n_fin[f] = int(edges.size + 1)
            else:
                qs = np.linspace(0.0, 1.0, self.max_bins + 1)[1:-1]
                edges = np.unique(np.quantile(fin, qs))
                self.bin_edges_.append(np.asarray(edges, dtype=np.float64))
                n_fin[f] = int(edges.size + 1)
        self.n_finite_bins_ = n_fin

    def _transform_bins(self, X: np.ndarray) -> np.ndarray:
        n_samples, n_features = X.shape
        out = np.full((n_samples, n_features), 255, dtype=np.uint8)
        for f in range(n_features):
            col = X[:, f]
            ok = np.isfinite(col)
            if not np.any(ok):
                continue
            edges = self.bin_edges_[f]
            if edges.size == 0:
                out[ok, f] = 0
            else:
                out[ok, f] = np.searchsorted(edges, col[ok], side="right").astype(np.uint8)
        return out

    def _grow_single_tree(
        self,
        X_binned: np.ndarray,
        grad: np.ndarray,
        hess: np.ndarray,
        feature_mask: np.ndarray | None,
    ) -> _HistTree:
        n_samples = X_binned.shape[0]
        root_idx = np.arange(n_samples, dtype=np.int32)
        root_G, root_H, root_C = _accel.hist_build(X_binned, grad, hess, root_idx)

        def _leaf_val(G_hist: np.ndarray, H_hist: np.ndarray) -> float:
            # Sum over feature 0's 256 bins gives total G and H of the node!
            g_sum = float(G_hist[0].sum())
            h_sum = float(H_hist[0].sum())
            return -self.learning_rate * (g_sum / (h_sum + self.reg_lambda))

        nodes: list[_TreeNode] = [_TreeNode(is_leaf=True, leaf_value=_leaf_val(root_G, root_H))]
        # Queue of splittable leaves: (gain, node_id, depth, sample_idx, G_hist, H_hist, C_hist, best_tuple)
        cand_f, cand_b, cand_nl, cand_gain = _accel.hist_best_split(
            root_G,
            root_H,
            root_C,
            self.n_finite_bins_,
            feature_mask,
            self.min_samples_leaf,
            self.min_child_weight,
            self.reg_lambda,
            self.min_split_gain,
        )
        splittable: list[tuple[float, int, int, np.ndarray, np.ndarray, np.ndarray, np.ndarray, tuple[int, int, bool]]] = []
        if cand_f >= 0 and cand_gain > 0.0 and self.max_depth >= 1:
            splittable.append((cand_gain, 0, 0, root_idx, root_G, root_H, root_C, (cand_f, cand_b, cand_nl)))

        n_leaves = 1
        while splittable and n_leaves < self.max_leaves:
            # Best-first (leaf-wise) selection bounded by max_depth and max_leaves
            best_pos = max(range(len(splittable)), key=lambda i: (splittable[i][0], -splittable[i][1]))
            _gain, nid, depth, s_idx, pG, pH, pC, (bf, bb, bnl) = splittable.pop(best_pos)

            bins = X_binned[s_idx, bf]
            is_nan = bins == 255
            if bnl:
                left_mask = is_nan | (bins <= bb)
            else:
                left_mask = (~is_nan) & (bins <= bb)

            left_idx = s_idx[left_mask]
            right_idx = s_idx[~left_mask]
            if left_idx.size < self.min_samples_leaf or right_idx.size < self.min_samples_leaf:
                continue

            # Parent-minus-smaller-child histogram trick!
            if left_idx.size <= right_idx.size:
                lG, lH, lC = _accel.hist_build(X_binned, grad, hess, left_idx)
                rG, rH, rC = _accel.hist_subtract(pG, pH, pC, lG, lH, lC)
            else:
                rG, rH, rC = _accel.hist_build(X_binned, grad, hess, right_idx)
                lG, lH, lC = _accel.hist_subtract(pG, pH, pC, rG, rH, rC)

            left_id = len(nodes)
            nodes.append(_TreeNode(is_leaf=True, leaf_value=_leaf_val(lG, lH)))
            right_id = len(nodes)
            nodes.append(_TreeNode(is_leaf=True, leaf_value=_leaf_val(rG, rH)))

            nodes[nid] = _TreeNode(
                is_leaf=False,
                feature=bf,
                threshold_bin=bb,
                nan_go_left=bnl,
                left=left_id,
                right=right_id,
            )
            n_leaves += 1

            next_depth = depth + 1
            if next_depth < self.max_depth:
                for child_id, c_idx, cG, cH, cC in (
                    (left_id, left_idx, lG, lH, lC),
                    (right_id, right_idx, rG, rH, rC),
                ):
                    cf, cb, cnl, cgain = _accel.hist_best_split(
                        cG,
                        cH,
                        cC,
                        self.n_finite_bins_,
                        feature_mask,
                        self.min_samples_leaf,
                        self.min_child_weight,
                        self.reg_lambda,
                        self.min_split_gain,
                    )
                    if cf >= 0 and cgain > 0.0:
                        splittable.append((cgain, child_id, next_depth, c_idx, cG, cH, cC, (cf, cb, cnl)))

        return _HistTree(nodes)

    def _predict_raw_binned(self, X_binned: np.ndarray, upto_round: int | None = None) -> np.ndarray:
        n_samples = X_binned.shape[0]
        n_out = 3 if self.loss == "multiclass" else 1
        raw = np.repeat(self.base_margin_[None, :], n_samples, axis=0)
        rounds = self.trees_ if upto_round is None else self.trees_[:upto_round]
        for round_trees in rounds:
            for k in range(n_out):
                raw[:, k] += round_trees[k].predict_binned(X_binned)
        return raw

    def _run_boosting(
        self,
        X_tr_bin: np.ndarray,
        y_tr: np.ndarray,
        w_tr: np.ndarray,
        init_raw_tr: np.ndarray,
        *,
        X_val_bin: np.ndarray | None,
        y_val: np.ndarray | None,
        w_val: np.ndarray | None,
        init_raw_val: np.ndarray | None,
        n_rounds: int,
        rng: np.random.Generator,
    ) -> None:
        n_samples, n_features = X_tr_bin.shape
        raw_tr = init_raw_tr.copy()
        raw_val = init_raw_val.copy() if init_raw_val is not None else None

        best_val_loss = float("inf")
        best_round_count = len(self.trees_)
        rounds_since_best = 0
        traj: list[np.ndarray] = []

        w_tr_norm = w_tr / max(float(w_tr.mean()), 1e-12)

        for r in range(n_rounds):
            if self.colsample_bytree < 1.0 and n_features > 1:
                k_keep = max(1, int(round(self.colsample_bytree * n_features)))
                chosen = rng.choice(n_features, size=k_keep, replace=False)
                fmask = np.zeros(n_features, dtype=np.uint8)
                fmask[chosen] = 1
            else:
                fmask = None

            round_trees: list[_HistTree] = []
            if self.loss == "regression":
                pred = raw_tr[:, 0]
                grad = w_tr_norm * (pred - y_tr)
                hess = w_tr_norm.copy()
                tree = self._grow_single_tree(X_tr_bin, grad, hess, fmask)
                step_pred = tree.predict_binned(X_tr_bin)
                raw_tr[:, 0] += step_pred
                round_trees.append(tree)
                traj.append(0.5 * (raw_tr[:, 0] - y_tr) ** 2)
                if raw_val is not None and X_val_bin is not None:
                    raw_val[:, 0] += tree.predict_binned(X_val_bin)
            else:
                y_int = y_tr.astype(np.int64)
                probs = _softmax_rows(raw_tr)
                for k in range(3):
                    target_k = (y_int == k).astype(np.float64)
                    pk = probs[:, k]
                    grad_k = w_tr_norm * (pk - target_k)
                    hess_k = w_tr_norm * np.maximum(pk * (1.0 - pk), 1e-6)
                    tree_k = self._grow_single_tree(X_tr_bin, grad_k, hess_k, fmask)
                    raw_tr[:, k] += tree_k.predict_binned(X_tr_bin)
                    round_trees.append(tree_k)
                    if raw_val is not None and X_val_bin is not None:
                        raw_val[:, k] += tree_k.predict_binned(X_val_bin)
                probs_after = _softmax_rows(raw_tr)
                traj.append(-np.log(np.clip(probs_after[np.arange(n_samples), y_int], 1e-15, 1.0)))

            self.trees_.append(round_trees)

            if (
                self.early_stopping_rounds is not None
                and raw_val is not None
                and y_val is not None
                and w_val is not None
                and y_val.size > 0
            ):
                wv_norm = w_val / max(float(w_val.sum()), 1e-12)
                if self.loss == "regression":
                    val_loss = float(np.sum(wv_norm * 0.5 * (raw_val[:, 0] - y_val) ** 2))
                else:
                    yv_int = y_val.astype(np.int64)
                    pv = _softmax_rows(raw_val)
                    val_loss = float(-np.sum(wv_norm * np.log(np.clip(pv[np.arange(yv_int.size), yv_int], 1e-15, 1.0))))
                if val_loss < best_val_loss - 1e-10:
                    best_val_loss = val_loss
                    best_round_count = len(self.trees_)
                    rounds_since_best = 0
                else:
                    rounds_since_best += 1
                    if rounds_since_best >= self.early_stopping_rounds:
                        break
            else:
                best_round_count = len(self.trees_)

        if best_round_count < len(self.trees_):
            self.trees_ = self.trees_[:best_round_count]
            traj = traj[:best_round_count]
        self.best_iteration_ = len(self.trees_) - 1
        if traj:
            self.sample_loss_trajectory_ = np.vstack(traj)

    def _extract_optional_valid(self, dataset: DatasetH, default_col: str) -> tuple[np.ndarray | None, np.ndarray | None, np.ndarray | None]:
        if "valid" not in dataset.segments:
            return None, None, None
        try:
            xv_df, yv, wv, _ = self._prepare_xy_learn(dataset, "valid", default_col)
        except ValueError:
            return None, None, None
        if len(yv) == 0:
            return None, None, None
        return xv_df[self.feature_names_].to_numpy(dtype=np.float64), yv, wv

    def fit(self, dataset: DatasetH, reweighter: Reweighter | None = None) -> HistGBDTModel:
        default_col = self.target_col or ("direction_class" if self.loss == "multiclass" else None)
        x_df, y_tr, w_tr, chosen_col = self._prepare_xy_learn(dataset, "train", default_col, reweighter=reweighter)
        self.feature_names_ = [str(c) for c in x_df.columns]
        X_tr = x_df.to_numpy(dtype=np.float64)

        self._fit_binner(X_tr)
        X_tr_bin = self._transform_bins(X_tr)

        if self.loss == "regression":
            base = float(np.sum(w_tr * y_tr) / max(float(w_tr.sum()), 1e-12))
            self.base_margin_ = np.array([base], dtype=np.float64)
        else:
            y_int = y_tr.astype(np.int64)
            if np.any((y_int < 0) | (y_int > 2)):
                raise ValueError("HistGBDTModel(loss='multiclass') expects labels in {0, 1, 2}")
            counts = np.bincount(y_int, weights=w_tr, minlength=3).astype(np.float64)
            priors = np.clip(counts / max(float(counts.sum()), 1e-12), 1e-4, 1.0)
            bm = np.log(priors)
            bm -= float(np.mean(bm))
            self.base_margin_ = bm

        X_val, y_val, w_val = self._extract_optional_valid(dataset, chosen_col)
        X_val_bin = self._transform_bins(X_val) if X_val is not None else None

        self.trees_ = []
        init_tr = np.repeat(self.base_margin_[None, :], X_tr_bin.shape[0], axis=0)
        init_val = np.repeat(self.base_margin_[None, :], X_val_bin.shape[0], axis=0) if X_val_bin is not None else None
        rng = np.random.default_rng(self.seed)

        self._run_boosting(
            X_tr_bin,
            y_tr,
            w_tr,
            init_tr,
            X_val_bin=X_val_bin,
            y_val=y_val,
            w_val=w_val,
            init_raw_val=init_val,
            n_rounds=self.num_boost_round,
            rng=rng,
        )
        used_valid = (self.early_stopping_rounds is not None) and (X_val is not None)
        self.training_cutoff_ = dataset.effective_training_cutoff(include_valid=used_valid)
        self.parent_model_sha256_ = None
        self.last_frozen_sha256_ = None
        self.fitted = True
        return self

    def finetune(
        self,
        dataset: DatasetH,
        reweighter: Reweighter | None = None,
        *,
        num_boost_round: int = 15,
        leaf_shrinkage: float = 0.9,
        **kwargs: Any,
    ) -> HistGBDTModel:
        _ = kwargs
        if not self.fitted:
            raise RuntimeError("Cannot finetune an unfitted HistGBDTModel")
        if not (0.0 < float(leaf_shrinkage) <= 1.0):
            raise ValueError("leaf_shrinkage must lie in (0, 1]")

        parent_sha = self._snapshot_parent_sha256()
        default_col = self.target_col or ("direction_class" if self.loss == "multiclass" else None)
        x_df, y_tr, w_tr, chosen_col = self._prepare_xy_learn(dataset, "train", default_col, reweighter=reweighter)
        if [str(c) for c in x_df.columns] != self.feature_names_:
            raise ValueError("Feature columns changed during HistGBDTModel.finetune")

        # Shrink prior leaf values to decay stale regime signal while retaining learned splits
        for round_trees in self.trees_:
            for t in round_trees:
                t.scale_leaves(leaf_shrinkage)

        X_tr = x_df.to_numpy(dtype=np.float64)
        X_tr_bin = self._transform_bins(X_tr)
        init_tr = self._predict_raw_binned(X_tr_bin)

        X_val, y_val, w_val = self._extract_optional_valid(dataset, chosen_col)
        X_val_bin = self._transform_bins(X_val) if X_val is not None else None
        init_val = self._predict_raw_binned(X_val_bin) if X_val_bin is not None else None

        rng = np.random.default_rng(self.seed + len(self.trees_))
        self._run_boosting(
            X_tr_bin,
            y_tr,
            w_tr,
            init_tr,
            X_val_bin=X_val_bin,
            y_val=y_val,
            w_val=w_val,
            init_raw_val=init_val,
            n_rounds=int(num_boost_round),
            rng=rng,
        )
        used_valid = (self.early_stopping_rounds is not None) and (X_val is not None)
        self.training_cutoff_ = dataset.effective_training_cutoff(include_valid=used_valid)
        self.parent_model_sha256_ = parent_sha
        self.last_frozen_sha256_ = None
        return self

    def predict_proba(self, dataset: DatasetH, segment: str | slice = "test") -> pd.DataFrame:
        if self.loss != "multiclass":
            raise NotImplementedError("predict_proba requires HistGBDTModel(loss='multiclass')")
        x_df = self._prepare_features_infer(dataset, segment)
        X_bin = self._transform_bins(x_df.to_numpy(dtype=np.float64))
        raw = self._predict_raw_binned(X_bin)
        probs = _softmax_rows(raw)
        return pd.DataFrame(probs, index=x_df.index, columns=list(DIRECTION_CLASSES), dtype=np.float64)

    def predict(self, dataset: DatasetH, segment: str | slice = "test") -> pd.Series:
        if self.loss == "multiclass":
            proba = self.predict_proba(dataset, segment)
            s = proba["up"] - proba["down"]
            s.name = "score"
            return s
        x_df = self._prepare_features_infer(dataset, segment)
        X_bin = self._transform_bins(x_df.to_numpy(dtype=np.float64))
        raw = self._predict_raw_binned(X_bin)[:, 0]
        return pd.Series(raw, index=x_df.index, name="score", dtype=np.float64)

    def _export_weights(self) -> dict[str, Any]:
        return {
            "bin_edges": [e.tolist() for e in self.bin_edges_],
            "n_finite_bins": self.n_finite_bins_.tolist(),
            "base_margin": self.base_margin_.tolist(),
            "best_iteration": int(self.best_iteration_),
            "trees": [[t.to_list() for t in round_trees] for round_trees in self.trees_],
        }

    def _load_weights(self, weights: Mapping[str, Any], feature_names: list[str]) -> None:
        self.bin_edges_ = [np.asarray(e, dtype=np.float64) for e in weights["bin_edges"]]
        self.n_finite_bins_ = np.asarray(weights["n_finite_bins"], dtype=np.int32)
        if len(self.bin_edges_) != len(feature_names) or self.n_finite_bins_.size != len(feature_names):
            raise ValueError("Binner feature count mismatch in HistGBDTModel")
        self.base_margin_ = np.asarray(weights["base_margin"], dtype=np.float64)
        self.best_iteration_ = int(weights.get("best_iteration", 0))
        self.trees_ = [[_HistTree.from_list(t_nodes) for t_nodes in r] for r in weights["trees"]]
