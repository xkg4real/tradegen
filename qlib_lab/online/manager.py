"""OnlineManager: Champion vs Shadow Challenger routine, closed-window scoring & Promotion Dossier."""
from __future__ import annotations

from collections.abc import Mapping
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from core.isolation import checked_target, refuse_quantgen
from core.quant import forecast_eval, validate
from qlib_lab import RESEARCH_FLAGS, canonical_sha256
from qlib_lab.data.dataset import DatasetH, authorized_eval_context
from qlib_lab.data.handler import DataHandlerLP
from qlib_lab.data.labels import DIRECTION_CLASSES
from qlib_lab.exceptions import PromotionGateRefusedError
from qlib_lab.expression.ast_nodes import _epoch_seconds_array, _to_utc_timestamps
from qlib_lab.models.base import FrozenModelSpec, Model
from qlib_lab.online.drift import DriftMonitor
from qlib_lab.workflow.ledger_bridge import register_trial_and_compute_neff
from qlib_lab.workflow.recorder import DEFAULT_PINNED_UTC
from tools.research import adaptive_bid_gap_preview as br26_preview


class OnlineManager:
    """Governance-safe Champion vs Shadow Challenger manager.

    - Scores closed outcome windows ONLY (`label_end_utc <= as_of`).
    - Registers challenger evaluations in `FamilyLedger` (`N_eff`).
    - Emits a `ChampionPromotionCandidate` dossier JSON when a Challenger simultaneously passes:
      1) Stage-1 directional gate (calls, Wilson 95% lower bound >= confidence, calibration gap <= max_gap),
      2) Cumulative FamilyLedger Deflated Sharpe Ratio (`dsr >= dsr_min`), AND
      3) Diebold-Mariano predictive-ability test vs Champion (`t < 0` and `p <= dm_p_max`).
    - NEVER silently swaps `champion_spec` during `routine()`; promotion requires explicit review ack.
    """

    def __init__(
        self,
        *,
        state_dir: Path,
        champion_spec: FrozenModelSpec,
        challengers: Mapping[str, FrozenModelSpec] | None = None,
        drift_monitor: DriftMonitor | None = None,
        family_id: str = "QLIB-ONLINE",
        rule_id: str = "QLIB-ONLINE-DIR",
        market: str = "KRW-BTC",
        horizon_bars: int = 2,
        step_seconds: int = 3600,
        hurdle_bps: int = 10,
    ) -> None:
        refuse_quantgen(state_dir, "online_state_dir")
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.ledger_dir = checked_target(self.state_dir / "ledgers", "online_ledger_dir", within=self.state_dir)
        self.dossier_dir = checked_target(
            self.state_dir / "promotion_candidates", "dossier_dir", within=self.state_dir
        )

        self.champion_spec = champion_spec
        self.champion_model: Model = Model.from_frozen_spec(champion_spec)
        self.challengers: dict[str, tuple[FrozenModelSpec, Model]] = {}
        for name, spec in (challengers or {}).items():
            self.add_challenger(name, spec)

        self.drift_monitor = drift_monitor or DriftMonitor(hurdle_bps=hurdle_bps)
        self.family_id = str(family_id)
        self.rule_id = str(rule_id)
        self.market = str(market)
        self.horizon_bars = int(horizon_bars)
        self.step_seconds = int(step_seconds)
        self.hurdle_bps = int(hurdle_bps)
        self.routine_history: list[dict[str, Any]] = []

    def add_challenger(self, name: str, spec: FrozenModelSpec) -> None:
        self.challengers[str(name)] = (spec, Model.from_frozen_spec(spec))

    def _predict_up_to_as_of(
        self,
        model: Model,
        dataset: DatasetH,
        as_of_ts: pd.Timestamp,
    ) -> tuple[pd.Series, pd.DataFrame | None]:
        feat_up_to = dataset.handler.fetch(slice(None, as_of_ts), col_set="feature", data_key=DataHandlerLP.DK_I)
        if feat_up_to.empty:
            return pd.Series(dtype=np.float64), (
                pd.DataFrame(columns=list(DIRECTION_CLASSES), dtype=np.float64)
                if model.task_type == "direction"
                else None
            )
        min_dt = feat_up_to.index.get_level_values("datetime").min()
        tmp_ds = DatasetH(
            handler=dataset.handler,
            segments={"online_slice": (min_dt, as_of_ts)},
            purge_outcomes=False,
        )
        scores = model.predict(tmp_ds, "online_slice")
        proba = model.predict_proba(tmp_ds, "online_slice") if model.task_type == "direction" else None
        return scores, proba

    def _evaluate_stage1_closed(
        self,
        proba_df: pd.DataFrame,
        realized_ret: pd.Series,
        *,
        confidence: float,
        min_calls: int,
        max_cal_gap: float,
    ) -> dict[str, Any]:
        up_bar = math.log1p(self.hurdle_bps / 10000.0)
        down_bar = math.log1p(-self.hurdle_bps / 10000.0)
        horizon_sec = self.horizon_bars * self.step_seconds
        stats = {"up": {"calls": 0, "hits": 0, "prob_sum": 0.0}, "down": {"calls": 0, "hits": 0, "prob_sum": 0.0}}

        inst_all = proba_df.index.get_level_values("instrument")
        for inst in inst_all.unique():
            sub_p = proba_df.loc[inst_all == inst].sort_index()
            sub_r = realized_ret.reindex(sub_p.index).to_numpy(dtype=np.float64)
            epochs = _epoch_seconds_array(_to_utc_timestamps(sub_p.index.get_level_values("datetime")))
            p_mat = sub_p[list(DIRECTION_CLASSES)].to_numpy(dtype=np.float64)

            last_ep: float | None = None
            for i in range(len(sub_p)):
                if not np.all(np.isfinite(p_mat[i])) or not math.isfinite(float(sub_r[i])):
                    continue
                if last_ep is not None and epochs[i] < last_ep + horizon_sec - 1e-6:
                    continue
                last_ep = float(epochs[i])

                p_up, p_down, p_neu = float(p_mat[i, 0]), float(p_mat[i, 1]), float(p_mat[i, 2])
                top = max(p_up, p_down, p_neu)
                winners = [c for c, v in zip(DIRECTION_CLASSES, (p_up, p_down, p_neu)) if abs(v - top) <= 1e-12]
                if len(winners) != 1:
                    continue
                d = winners[0]
                if d in ("up", "down"):
                    p_d = p_up if d == "up" else p_down
                    if p_d + 1e-12 >= confidence:
                        hit = int(sub_r[i] > up_bar if d == "up" else sub_r[i] < down_bar)
                        stats[d]["calls"] += 1
                        stats[d]["hits"] += hit
                        stats[d]["prob_sum"] += p_d

        out_dirs: dict[str, Any] = {}
        passing: list[str] = []
        for d in ("up", "down"):
            c = int(stats[d]["calls"])
            h = int(stats[d]["hits"])
            hr = h / float(c) if c > 0 else 0.0
            mp = float(stats[d]["prob_sum"]) / float(c) if c > 0 else 0.0
            gap = abs(hr - mp) if c > 0 else 1.0
            wlo = float(br26_preview.wilson_lower(h, c))
            ok = bool(c >= min_calls and wlo >= confidence - 1e-12 and gap <= max_cal_gap + 1e-12)
            out_dirs[d] = {"calls": c, "hits": h, "hit_rate": hr, "wilson_lower": wlo, "calibration_gap": gap, "passes": ok}
            if ok:
                passing.append(d)
        return {"directions": out_dirs, "passing_directions": passing, "passes": len(passing) > 0}

    def routine(
        self,
        as_of: Any,
        dataset: DatasetH,
        *,
        evaluation_start: Any = None,
        run_utc: str = DEFAULT_PINNED_UTC,
        confidence: float = 0.60,
        min_validation_calls: int = 15,
        max_calibration_gap: float = 0.10,
        dsr_min: float = 0.95,
        dm_p_max: float = 0.10,
        sr_sd_daily_prior: float = 0.05,
    ) -> dict[str, Any]:
        """Run one causal online cycle at `as_of`, scoring closed outcomes (`label_end_utc <= as_of`) ONLY."""
        as_of_ts = _to_utc_timestamps(pd.Index([as_of]))[0]
        as_of_ep = float(as_of_ts.value // 1_000_000_000)
        eval_start_ts = (
            _to_utc_timestamps(pd.Index([evaluation_start]))[0]
            if evaluation_start is not None
            else _to_utc_timestamps(pd.Index([self.champion_spec.frozen_at]))[0]
        )

        champ_scores, champ_proba = self._predict_up_to_as_of(self.champion_model, dataset, as_of_ts)

        # Fetch raw labels/meta strictly up to `as_of_ts` and IMMEDIATELY mask out any row with label_end_utc > as_of_ep!
        with authorized_eval_context("OnlineManager"):
            raw_slice = dataset.handler.fetch(slice(eval_start_ts, as_of_ts), col_set=DataHandlerLP.CS_RAW, data_key=DataHandlerLP.DK_R)

        closed_idx = pd.MultiIndex.from_arrays([[], []], names=["datetime", "instrument"])
        open_window_count = 0
        y_ret_closed = pd.Series(dtype=np.float64)
        y_cls_closed = pd.Series(dtype=np.float64)
        end_utc_closed = pd.Series(dtype=np.float64)

        if not raw_slice.empty and ("meta", "label_end_utc") in raw_slice.columns:
            end_ser = raw_slice[("meta", "label_end_utc")]
            end_arr = _epoch_seconds_array(end_ser.to_numpy())
            closed_mask = np.isfinite(end_arr) & (end_arr <= as_of_ep + 1e-9)
            open_window_count = int(np.sum(~closed_mask))
            closed_rows = raw_slice.loc[closed_mask]
            closed_idx = closed_rows.index
            if ("label", "realized_log_return") in closed_rows.columns:
                y_ret_closed = closed_rows[("label", "realized_log_return")].astype(np.float64)
            if ("label", "direction_class") in closed_rows.columns:
                y_cls_closed = closed_rows[("label", "direction_class")].astype(np.float64)
            end_utc_closed = closed_rows[("meta", "label_end_utc")].astype(np.float64)

        cur_feat = dataset.handler.fetch(slice(eval_start_ts, as_of_ts), col_set="feature", data_key=DataHandlerLP.DK_I)
        drift_report = self.drift_monitor.evaluate(
            as_of_ts,
            current_features=cur_feat,
            scores=champ_scores,
            probabilities=champ_proba,
            realized_returns=y_ret_closed if not y_ret_closed.empty else None,
            direction_classes=y_cls_closed if not y_cls_closed.empty else None,
            label_end_utc=end_utc_closed if not end_utc_closed.empty else None,
        )

        challenger_evals: dict[str, Any] = {}
        emitted_dossiers: list[dict[str, Any]] = []

        for ch_name, (ch_spec, ch_model) in sorted(self.challengers.items()):
            ch_scores, ch_proba = self._predict_up_to_as_of(ch_model, dataset, as_of_ts)
            common_closed = closed_idx.intersection(champ_scores.index).intersection(ch_scores.index).sort_values()

            if len(common_closed) < 10:
                challenger_evals[ch_name] = {
                    "challenger_sha256": ch_spec.model_sha256,
                    "n_closed_windows": int(len(common_closed)),
                    "status": "INSUFFICIENT_CLOSED_WINDOWS",
                }
                continue

            if ch_proba is not None and champ_proba is not None and not y_cls_closed.empty:
                cp_ch = np.clip(ch_proba.reindex(common_closed)[list(DIRECTION_CLASSES)].to_numpy(dtype=np.float64), 1e-12, 1.0)
                cp_cm = np.clip(champ_proba.reindex(common_closed)[list(DIRECTION_CLASSES)].to_numpy(dtype=np.float64), 1e-12, 1.0)
                yc = y_cls_closed.reindex(common_closed).to_numpy(dtype=np.float64)
                yr = y_ret_closed.reindex(common_closed)

                nn_mask = np.isfinite(yc) & ((yc == 0) | (yc == 1)) & np.all(np.isfinite(cp_ch), axis=1) & np.all(np.isfinite(cp_cm), axis=1)
                if int(np.sum(nn_mask)) >= 8:
                    y_nn = yc[nn_mask].astype(np.int64)
                    q_ch = np.clip(cp_ch[nn_mask, 0] / np.maximum(cp_ch[nn_mask, 0] + cp_ch[nn_mask, 1], 1e-12), 1e-12, 1.0 - 1e-12)
                    q_cm = np.clip(cp_cm[nn_mask, 0] / np.maximum(cp_cm[nn_mask, 0] + cp_cm[nn_mask, 1], 1e-12), 1e-12, 1.0 - 1e-12)
                    loss_ch = np.where(y_nn == 0, -np.log(q_ch), -np.log(1.0 - q_ch))
                    loss_cm = np.where(y_nn == 0, -np.log(q_cm), -np.log(1.0 - q_cm))
                    dm = forecast_eval.dm_test(loss_ch, loss_cm, h=self.horizon_bars)
                    skill_diff = pd.Series(loss_cm - loss_ch, index=common_closed[nn_mask].get_level_values("datetime"))
                else:
                    dm = {"t": float("nan"), "p": float("nan"), "mean_diff": float("nan"), "n": int(np.sum(nn_mask))}
                    skill_diff = pd.Series(dtype=np.float64)

                s1 = self._evaluate_stage1_closed(
                    ch_proba.reindex(common_closed),
                    yr,
                    confidence=confidence,
                    min_calls=min_validation_calls,
                    max_cal_gap=max_calibration_gap,
                )
            else:
                # Regression / score loss comparison
                yr_arr = y_ret_closed.reindex(common_closed).to_numpy(dtype=np.float64)
                sc_ch = ch_scores.reindex(common_closed).to_numpy(dtype=np.float64)
                sc_cm = champ_scores.reindex(common_closed).to_numpy(dtype=np.float64)
                loss_ch = (sc_ch - yr_arr) ** 2
                loss_cm = (sc_cm - yr_arr) ** 2
                dm = forecast_eval.dm_test(loss_ch, loss_cm, h=self.horizon_bars)
                skill_diff = pd.Series(
                    sc_ch * yr_arr - sc_cm * yr_arr,
                    index=common_closed.get_level_values("datetime"),
                )
                s1 = {"passes": bool(dm["mean_diff"] < 0), "directions": {}, "passing_directions": []}

            # Aggregate skill_diff by unique date/timestamp for FamilyLedger registration & DSR
            dated_diff = skill_diff.groupby(level=0).mean()
            dts_span = _to_utc_timestamps(common_closed.get_level_values("datetime"))
            span_iso = (dts_span.min().strftime("%Y-%m-%d"), dts_span.max().strftime("%Y-%m-%d"))

            if len(dated_diff) >= 3:
                mult = register_trial_and_compute_neff(
                    ledger_dir=self.ledger_dir,
                    family_id=self.family_id,
                    rule=self.rule_id,
                    params={"challenger": ch_name, "model_sha256": ch_spec.model_sha256},
                    span=span_iso,
                    market=self.market,
                    run_utc=run_utc,
                    diff_series=dated_diff,
                    delta_sr=float(validate.sharpe(dated_diff.to_numpy(dtype=np.float64))),
                    script="qlib_lab.online.OnlineManager",
                )
                n_trials_eff = max(1, int(math.ceil(mult.n_eff)))
                dsr_val = float(
                    validate.deflated_sharpe(
                        dated_diff.to_numpy(dtype=np.float64),
                        n_trials=n_trials_eff,
                        sr_sd_daily=sr_sd_daily_prior,
                    )
                )
                mult_dict = mult.to_dict()
            else:
                dsr_val = float("nan")
                mult_dict = None

            dm_pass = bool(math.isfinite(dm["t"]) and dm["t"] < 0.0 and math.isfinite(dm["p"]) and dm["p"] <= dm_p_max)
            dsr_pass = bool(math.isfinite(dsr_val) and dsr_val >= dsr_min)
            stage1_pass = bool(s1["passes"])
            eligible = stage1_pass and dsr_pass and dm_pass

            eval_entry = {
                "challenger_name": ch_name,
                "challenger_sha256": ch_spec.model_sha256,
                "n_closed_windows": int(len(common_closed)),
                "stage1": s1,
                "dm_vs_champion": dm,
                "cumulative_dsr": dsr_val,
                "ledger_multiplicity": mult_dict,
                "passes_all_gates": eligible,
            }
            challenger_evals[ch_name] = eval_entry

            if eligible:
                dossier_body = {
                    "schema": "tradegen-qlib-promotion-candidate-v1",
                    "as_of_utc": as_of_ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "champion_model_sha256": self.champion_spec.model_sha256,
                    "challenger_name": ch_name,
                    "challenger_model_sha256": ch_spec.model_sha256,
                    "challenger_spec": ch_spec.to_dict(),
                    "evidence": eval_entry,
                    "drift_context": {
                        "drift_detected": drift_report["drift_detected"],
                        "alerts": drift_report["alerts"],
                    },
                    "auto_promoted": False,
                    "owner_approval_required": True,
                    "research_flags": dict(RESEARCH_FLAGS),
                    **RESEARCH_FLAGS,
                }
                dossier_body["dossier_sha256"] = canonical_sha256(dossier_body)
                self.dossier_dir.mkdir(parents=True, exist_ok=True)
                d_path = checked_target(
                    self.dossier_dir / f"candidate_{ch_name}_{ch_spec.model_sha256[:12]}.json",
                    "promotion_dossier",
                    within=self.state_dir,
                )
                d_path.write_bytes(
                    (json.dumps(dossier_body, sort_keys=True, ensure_ascii=True, indent=2, allow_nan=False) + "\n").encode("ascii")
                )
                emitted_dossiers.append({"dossier": dossier_body, "path": str(d_path)})

        latest_champ_rows = champ_scores.loc[_to_utc_timestamps(champ_scores.index.get_level_values("datetime")) == as_of_ts]
        routine_summary = {
            "schema": "tradegen-qlib-online-routine-v1",
            "as_of_utc": as_of_ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "active_champion_sha256": self.champion_spec.model_sha256,
            "n_closed_windows_scored": int(len(closed_idx)),
            "n_open_windows_held_back": open_window_count,
            "latest_champion_scores": {str(idx[1]): float(val) for idx, val in latest_champ_rows.items() if math.isfinite(float(val))},
            "drift_report": drift_report,
            "challenger_evaluations": challenger_evals,
            "promotion_candidates": [d["dossier"] for d in emitted_dossiers],
            "promotion_dossier_paths": [d["path"] for d in emitted_dossiers],
            "research_flags": dict(RESEARCH_FLAGS),
            **RESEARCH_FLAGS,
        }
        self.routine_history.append(routine_summary)
        return routine_summary

    def apply_reviewed_promotion(
        self,
        dossier_or_path: Mapping[str, Any] | Path,
        *,
        explicit_offline_review_ack: bool = False,
    ) -> FrozenModelSpec:
        """Promote a verified candidate ONLY in offline research simulation when explicitly acknowledged."""
        if not explicit_offline_review_ack:
            raise PromotionGateRefusedError(
                "Silent or unacknowledged promotion is forbidden; set explicit_offline_review_ack=True for offline study"
            )
        if isinstance(dossier_or_path, (Path, str)):
            target = checked_target(Path(dossier_or_path), "promotion_dossier")
            dossier = json.loads(target.read_text(encoding="utf-8"))
        else:
            dossier = dict(dossier_or_path)

        if dossier.get("schema") != "tradegen-qlib-promotion-candidate-v1":
            raise PromotionGateRefusedError("Invalid promotion dossier schema")
        expected_sha = dossier.get("dossier_sha256")
        body = {k: v for k, v in dossier.items() if k != "dossier_sha256"}
        if expected_sha != canonical_sha256(body):
            raise PromotionGateRefusedError("Promotion dossier SHA-256 verification failed")
        if not (dossier.get("evidence") or {}).get("passes_all_gates"):
            raise PromotionGateRefusedError("Promotion dossier did not pass all required gates")
        if dossier.get("champion_model_sha256") != self.champion_spec.model_sha256:
            raise PromotionGateRefusedError("Promotion dossier was built against a different Champion version")

        new_spec = FrozenModelSpec.from_dict(dossier["challenger_spec"])
        self.champion_spec = new_spec
        self.champion_model = Model.from_frozen_spec(new_spec)
        return new_spec
