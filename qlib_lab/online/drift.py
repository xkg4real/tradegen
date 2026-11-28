"""Causal DriftMonitor (Page CUSUM log-loss/RankIC, calibration drift, 10-bin PSI) & deterministic RevisionProposer."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats as sps
import yaml

from core.isolation import checked_target
from qlib_lab import RESEARCH_FLAGS, canonical_sha256
from qlib_lab.data.labels import DIRECTION_CLASSES
from qlib_lab.expression.ast_nodes import _epoch_seconds_array, _to_utc_timestamps
from qlib_lab.online.rolling import TaskGen


def _page_cusum_upper(series: np.ndarray, target_mean: float, slack_k: float) -> tuple[float, float]:
    """One-sided upper Page CUSUM S_t = max(0, S_{t-1} + (x_t - target_mean - slack_k)).

    Returns `(final_S, max_S)`.
    """
    s = 0.0
    max_s = 0.0
    for val in series:
        f = float(val)
        if not math.isfinite(f):
            continue
        s = max(0.0, s + (f - target_mean - slack_k))
        if s > max_s:
            max_s = s
    return s, max_s


class DriftMonitor:
    """Causal covariate & concept-drift monitor for active Champion models.

    Tracks:
    1) Per-feature 10-bin Population Stability Index (PSI) against reference training quantiles;
    2) Page's tabular CUSUM on conditional Up-vs-Down log-loss degradation (closed windows ONLY);
    3) Page's tabular CUSUM on RankIC decay (closed windows ONLY);
    4) Empirical vs predicted probability calibration gap drift (closed windows ONLY).
    """

    def __init__(
        self,
        *,
        psi_bins: int = 10,
        psi_moderate_threshold: float = 0.10,
        psi_severe_threshold: float = 0.25,
        cusum_logloss_slack: float = 0.03,
        cusum_logloss_threshold: float = 1.5,
        cusum_ic_slack: float = 0.02,
        cusum_ic_threshold: float = 0.50,
        confidence: float = 0.60,
        max_calibration_gap: float = 0.10,
        hurdle_bps: int = 10,
    ) -> None:
        if psi_bins < 2:
            raise ValueError("psi_bins must be >= 2")
        self.psi_bins = int(psi_bins)
        self.psi_moderate_threshold = float(psi_moderate_threshold)
        self.psi_severe_threshold = float(psi_severe_threshold)
        self.cusum_logloss_slack = float(cusum_logloss_slack)
        self.cusum_logloss_threshold = float(cusum_logloss_threshold)
        self.cusum_ic_slack = float(cusum_ic_slack)
        self.cusum_ic_threshold = float(cusum_ic_threshold)
        self.confidence = float(confidence)
        self.max_calibration_gap = float(max_calibration_gap)
        self.hurdle_bps = int(hurdle_bps)

        self.ref_edges_: dict[str, np.ndarray] = {}
        self.ref_props_: dict[str, np.ndarray] = {}
        self.baseline_cond_logloss_: float = math.log(2.0)
        self.baseline_rank_ic_: float = 0.05
        self.fitted_ref_: bool = False

    def fit_reference(
        self,
        ref_features: pd.DataFrame,
        *,
        baseline_cond_logloss: float | None = None,
        baseline_rank_ic: float | None = None,
    ) -> DriftMonitor:
        """Fit 10-bin reference feature edges and proportions strictly on training features."""
        feat_df = (
            ref_features["feature"]
            if (isinstance(ref_features.columns, pd.MultiIndex) and "feature" in ref_features.columns.get_level_values(0))
            else ref_features
        )
        self.ref_edges_ = {}
        self.ref_props_ = {}
        qs = np.linspace(0.0, 1.0, self.psi_bins + 1)[1:-1]

        for col in feat_df.columns:
            vals = feat_df[col].to_numpy(dtype=np.float64)
            fin = vals[np.isfinite(vals)]
            name = str(col)
            if fin.size < self.psi_bins:
                edges = np.linspace(-1.0, 1.0, self.psi_bins - 1)
                props = np.full(self.psi_bins, 1.0 / float(self.psi_bins), dtype=np.float64)
            else:
                edges = np.unique(np.quantile(fin, qs))
                if edges.size == 0:
                    edges = np.array([float(fin[0])], dtype=np.float64)
                bins = np.searchsorted(edges, fin, side="right")
                counts = np.bincount(bins, minlength=edges.size + 1).astype(np.float64)
                props = np.maximum(counts / float(fin.size), 1e-4)
                props /= float(props.sum())
            self.ref_edges_[name] = edges
            self.ref_props_[name] = props

        if baseline_cond_logloss is not None and math.isfinite(float(baseline_cond_logloss)):
            self.baseline_cond_logloss_ = float(baseline_cond_logloss)
        if baseline_rank_ic is not None and math.isfinite(float(baseline_rank_ic)):
            self.baseline_rank_ic_ = float(baseline_rank_ic)
        self.fitted_ref_ = True
        return self

    def compute_psi(self, cur_features: pd.DataFrame) -> dict[str, float]:
        if not self.fitted_ref_:
            raise RuntimeError("DriftMonitor.fit_reference() must be called before compute_psi()")
        feat_df = (
            cur_features["feature"]
            if (isinstance(cur_features.columns, pd.MultiIndex) and "feature" in cur_features.columns.get_level_values(0))
            else cur_features
        )
        psi_by_feature: dict[str, float] = {}
        eps = 1e-4
        for name, edges in self.ref_edges_.items():
            if name not in feat_df.columns:
                continue
            vals = feat_df[name].to_numpy(dtype=np.float64)
            fin = vals[np.isfinite(vals)]
            if fin.size == 0:
                psi_by_feature[name] = 0.0
                continue
            p_ref = self.ref_props_[name]
            bins = np.searchsorted(edges, fin, side="right")
            counts = np.bincount(bins, minlength=p_ref.size).astype(np.float64)
            q_cur = np.maximum(counts / float(fin.size), eps)
            q_cur /= float(q_cur.sum())
            psi = float(np.sum((q_cur - p_ref) * np.log((q_cur + eps) / (p_ref + eps))))
            psi_by_feature[name] = max(0.0, psi)
        return psi_by_feature

    def evaluate(
        self,
        as_of: Any,
        *,
        current_features: pd.DataFrame,
        scores: pd.Series | None = None,
        probabilities: pd.DataFrame | None = None,
        realized_returns: pd.Series | None = None,
        direction_classes: pd.Series | None = None,
        label_end_utc: pd.Series | None = None,
    ) -> dict[str, Any]:
        """Evaluate covariate PSI up to `as_of` and outcome drift strictly on closed windows (`label_end_utc <= as_of`)."""
        as_of_ts = _to_utc_timestamps(pd.Index([as_of]))[0]
        as_of_ep = float(as_of_ts.value // 1_000_000_000)

        # Filter current_features causally to datetime <= as_of
        f_dts = _to_utc_timestamps(current_features.index.get_level_values("datetime"))
        cur_f = current_features.loc[f_dts <= as_of_ts]
        psi_map = self.compute_psi(cur_f) if (self.fitted_ref_ and not cur_f.empty) else {}

        moderate_psi = sorted(k for k, v in psi_map.items() if v >= self.psi_moderate_threshold)
        severe_psi = sorted(k for k, v in psi_map.items() if v >= self.psi_severe_threshold)
        max_psi = max(psi_map.values(), default=0.0)

        alerts: list[str] = []
        recommended_targets: list[str] = []
        if severe_psi:
            alerts.append("covariate_shift_severe")
            recommended_targets.append("covariate_shift")
        elif moderate_psi:
            alerts.append("covariate_shift_moderate")

        cusum_ll_final, cusum_ll_max = 0.0, 0.0
        cusum_ic_final, cusum_ic_max = 0.0, 0.0
        cal_gaps: dict[str, float] = {"up": 0.0, "down": 0.0}
        n_closed_scored = 0

        # Strictly gate outcome evaluation by label_end_utc <= as_of!
        if label_end_utc is not None:
            end_ep = _epoch_seconds_array(label_end_utc.to_numpy())
            closed_index = label_end_utc.index[np.isfinite(end_ep) & (end_ep <= as_of_ep + 1e-9)]
            n_closed_scored = int(len(closed_index))

            if probabilities is not None and direction_classes is not None and len(closed_index) > 0:
                common_p = closed_index.intersection(probabilities.index).intersection(direction_classes.index).sort_values()
                if len(common_p) > 0:
                    p_sub = probabilities.reindex(common_p)[list(DIRECTION_CLASSES)].to_numpy(dtype=np.float64)
                    y_sub = direction_classes.reindex(common_p).to_numpy(dtype=np.float64)
                    ok = np.all(np.isfinite(p_sub), axis=1) & np.isfinite(y_sub) & ((y_sub == 0) | (y_sub == 1))
                    if np.any(ok):
                        p_nn = p_sub[ok]
                        y_nn = y_sub[ok].astype(np.int64)
                        q_up = np.clip(p_nn[:, 0] / np.maximum(p_nn[:, 0] + p_nn[:, 1], 1e-12), 1e-12, 1.0 - 1e-12)
                        ll_seq = np.where(y_nn == 0, -np.log(q_up), -np.log(1.0 - q_up))
                        cusum_ll_final, cusum_ll_max = _page_cusum_upper(
                            ll_seq, self.baseline_cond_logloss_, self.cusum_logloss_slack
                        )
                        if cusum_ll_max > self.cusum_logloss_threshold:
                            alerts.append("cusum_logloss_alert")
                            recommended_targets.append("logloss_decay")

                    # Calibration gap check on closed calls
                    if realized_returns is not None:
                        r_sub = realized_returns.reindex(common_p).to_numpy(dtype=np.float64)
                        up_bar = math.log1p(self.hurdle_bps / 10000.0)
                        down_bar = math.log1p(-self.hurdle_bps / 10000.0)
                        for col_idx, d_label, thr_val, flag_up in (
                            (0, "up", up_bar, True),
                            (1, "down", down_bar, False),
                        ):
                            top_p = np.max(p_sub, axis=1)
                            called_mask = (
                                np.all(np.isfinite(p_sub), axis=1)
                                & np.isfinite(r_sub)
                                & (p_sub[:, col_idx] >= top_p - 1e-12)
                                & (p_sub[:, col_idx] >= self.confidence)
                            )
                            if int(np.sum(called_mask)) >= 5:
                                hits = np.mean(r_sub[called_mask] > thr_val if flag_up else r_sub[called_mask] < thr_val)
                                mean_p = float(np.mean(p_sub[called_mask, col_idx]))
                                gap = abs(float(hits) - mean_p)
                                cal_gaps[d_label] = gap
                                if gap > self.max_calibration_gap:
                                    if "calibration_drift_alert" not in alerts:
                                        alerts.append("calibration_drift_alert")
                                    if "calibration_drift" not in recommended_targets:
                                        recommended_targets.append("calibration_drift")

            if scores is not None and realized_returns is not None and len(closed_index) >= 10:
                common_s = closed_index.intersection(scores.index).intersection(realized_returns.index).sort_values()
                s_arr = scores.reindex(common_s).to_numpy(dtype=np.float64)
                r_arr = realized_returns.reindex(common_s).to_numpy(dtype=np.float64)
                ok_s = np.isfinite(s_arr) & np.isfinite(r_arr)
                s_arr, r_arr = s_arr[ok_s], r_arr[ok_s]
                if s_arr.size >= 10:
                    # Compute rolling chunk RankICs (chunks of 10) for Page CUSUM decay check
                    n_chunks = max(1, s_arr.size // 10)
                    chunk_rics = []
                    for ch in np.array_split(np.arange(s_arr.size), n_chunks):
                        if ch.size >= 5 and np.std(s_arr[ch]) > 1e-15 and np.std(r_arr[ch]) > 1e-15:
                            chunk_rics.append(float(sps.spearmanr(s_arr[ch], r_arr[ch]).statistic))
                    if chunk_rics:
                        # Decay means (baseline_rank_ic - ric) is positive -> feed (-ric) vs (-baseline_rank_ic)
                        cusum_ic_final, cusum_ic_max = _page_cusum_upper(
                            -np.asarray(chunk_rics, dtype=np.float64),
                            -self.baseline_rank_ic_,
                            self.cusum_ic_slack,
                        )
                        if cusum_ic_max > self.cusum_ic_threshold:
                            alerts.append("cusum_rank_ic_decay_alert")
                            recommended_targets.append("ic_decay")

        return {
            "schema": "tradegen-qlib-drift-report-v1",
            "as_of_utc": as_of_ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "n_closed_outcomes_scored": n_closed_scored,
            "psi_by_feature": psi_map,
            "max_psi": float(max_psi),
            "moderate_shift_features": moderate_psi,
            "severe_shift_features": severe_psi,
            "cusum_cond_logloss": {"current": cusum_ll_final, "max": cusum_ll_max, "threshold": self.cusum_logloss_threshold},
            "cusum_rank_ic_decay": {"current": cusum_ic_final, "max": cusum_ic_max, "threshold": self.cusum_ic_threshold},
            "calibration_gaps": cal_gaps,
            "alerts": alerts,
            "recommended_targets": recommended_targets,
            "drift_detected": len(alerts) > 0,
            "research_flags": dict(RESEARCH_FLAGS),
            **RESEARCH_FLAGS,
        }


class RevisionProposer(TaskGen):
    """Deterministic bounded TaskGen creating reviewable YAML/JSON revision proposals.

    NON-NEGOTIABLE GUARDRAILS:
    - Never mutates active models or tasks in place;
    - Never lowers `cost_bps`, never lowers `confidence`, never widens `max_calibration_gap`;
    - Every emitted proposal sets `auto_apply=False` and `requires_owner_review=True`.
    """

    SUPPORTED_TARGETS = (
        "over-search",
        "execution",
        "plateau",
        "covariate_shift",
        "calibration_drift",
        "logloss_decay",
        "ic_decay",
        "regime",
        "sample",
    )

    def __init__(
        self,
        *,
        gate_report: Mapping[str, Any] | None = None,
        drift_report: Mapping[str, Any] | None = None,
        explicit_targets: Sequence[str] = (),
    ) -> None:
        self.gate_report = dict(gate_report) if gate_report is not None else {}
        self.drift_report = dict(drift_report) if drift_report is not None else {}
        self.explicit_targets = tuple(str(t) for t in explicit_targets)

    def _collect_targets(self) -> list[str]:
        found: list[str] = []
        for t in self.explicit_targets:
            if t not in found:
                found.append(t)

        rt = self.gate_report.get("revise_target")
        if isinstance(rt, str) and rt.strip():
            # Map verbose validate.py revise_target prose back to canonical key if needed
            low = rt.lower()
            mapped = rt
            if "coarsen the grid" in low:
                mapped = "over-search"
            elif "holding period" in low or "hysteresis" in low:
                mapped = "execution"
            elif "plateau" in low:
                mapped = "plateau"
            elif "regime" in low:
                mapped = "regime"
            elif "extend history" in low:
                mapped = "sample"
            if mapped not in found:
                found.append(mapped)

        for dt in self.drift_report.get("recommended_targets") or ():
            if str(dt) not in found:
                found.append(str(dt))
        return found or ["over-search"]

    def generate(self, task: Mapping[str, Any]) -> list[dict[str, Any]]:
        targets = self._collect_targets()
        proposals: list[dict[str, Any]] = []

        for idx, target in enumerate(targets):
            cand = deepcopy(dict(task))
            model_cfg = cand.setdefault("model", {"class": "MultinomialDirectionModel", "kwargs": {}})
            m_kw = model_cfg.setdefault("kwargs", {})
            rationale = ""

            if target == "over-search":
                if "reg_lambda" in m_kw or model_cfg.get("class") in ("MultinomialDirectionModel", "HistGBDTModel"):
                    cur_reg = float(m_kw.get("reg_lambda", 1.0))
                    m_kw["reg_lambda"] = min(100.0, cur_reg * 2.0)
                if "alpha" in m_kw or model_cfg.get("class") == "RidgeLinearModel":
                    cur_a = float(m_kw.get("alpha", 1.0))
                    m_kw["alpha"] = min(100.0, cur_a * 2.0)
                if "max_depth" in m_kw:
                    m_kw["max_depth"] = max(2, int(m_kw["max_depth"]) - 1)
                rationale = "Increased L2 regularization / reduced tree depth to curb in-sample over-search."

            elif target == "execution":
                # Lengthen horizon_bars or add hysteresis; NEVER lower cost_bps!
                ds_kw = cand.setdefault("dataset", {}).setdefault("kwargs", {})
                ds_kw["embargo_bars"] = max(int(ds_kw.get("embargo_bars", 1)), 2)
                port_kw = cand.setdefault("portfolio_gate_kwargs", {})
                port_kw["signal_grid"] = [
                    {"threshold": 0.05, "hysteresis": 0.10},
                    {"threshold": 0.10, "hysteresis": 0.10},
                    {"threshold": 0.15, "hysteresis": 0.15},
                ]
                rationale = "Tightened rebalance hysteresis band to reduce turnover without lowering cost assumptions."

            elif target == "covariate_shift":
                cand["reweighter"] = {
                    "class": "RegimeKernelReweighter",
                    "kwargs": {"halflife_bars": 96.0, "anchor_bars": 24, "kernel_bandwidth": 2.0},
                }
                rationale = "Attached RegimeKernelReweighter (exponential decay x Mahalanobis similarity) for PSI shift."

            elif target == "calibration_drift":
                if model_cfg.get("class") == "MultinomialDirectionModel":
                    m_kw["calibrate_temperature"] = True
                rationale = "Enabled post-hoc validation temperature scaling to restore probability calibration."

            elif target in ("logloss_decay", "ic_decay"):
                cand["model"] = {
                    "class": "DoubleEnsembleModel",
                    "kwargs": {
                        "base_model_config": deepcopy(model_cfg) if model_cfg.get("class") != "DoubleEnsembleModel" else m_kw.get("base_model_config"),
                        "num_models": 3,
                        "enable_sr": True,
                        "enable_fs": True,
                    },
                }
                rationale = f"Proposed DoubleEnsembleModel (SR + FS) shadow challenger in response to {target}."

            elif target == "plateau":
                if "learning_rate" in m_kw:
                    m_kw["learning_rate"] = round(0.5 * float(m_kw["learning_rate"]) + 0.05, 4)
                rationale = "Recentered learning hyperparameters toward interior plateau midpoint."

            else:
                rationale = f"Diagnostic hold/review proposal for target={target!r} (no rule loosening permitted)."

            proposal_body = {
                "schema": "tradegen-qlib-revision-proposal-v1",
                "proposal_index": idx,
                "trigger_target": target,
                "rationale": rationale,
                "proposed_task": cand,
                "auto_apply": False,
                "requires_owner_review": True,
                "counts_as_new_ledger_trial": True,
                "research_flags": dict(RESEARCH_FLAGS),
                **RESEARCH_FLAGS,
            }
            proposal_body["proposal_sha256"] = canonical_sha256(proposal_body)
            proposals.append(proposal_body)

        return proposals

    def write_proposals(self, task: Mapping[str, Any], output_dir: Path, *, stem: str = "revision_proposal") -> list[dict[str, Any]]:
        """Write deterministic `.json` and `.yaml` revision proposals via `checked_target`."""
        out_root = checked_target(Path(output_dir), "revision_proposals_dir")
        out_root.mkdir(parents=True, exist_ok=True)
        proposals = self.generate(task)

        written: list[dict[str, Any]] = []
        for idx, prop in enumerate(proposals):
            json_path = checked_target(out_root / f"{stem}_{idx:02d}.json", "proposal_json", within=out_root)
            yaml_path = checked_target(out_root / f"{stem}_{idx:02d}.yaml", "proposal_yaml", within=out_root)

            json_bytes = (json.dumps(prop, sort_keys=True, ensure_ascii=True, indent=2, allow_nan=False) + "\n").encode("ascii")
            yaml_str = yaml.safe_dump(prop, sort_keys=True, allow_unicode=False)
            json_path.write_bytes(json_bytes)
            yaml_path.write_bytes(yaml_str.encode("ascii"))
            written.append(
                {
                    "proposal": prop,
                    "json_path": str(json_path),
                    "yaml_path": str(yaml_path),
                }
            )
        return written
