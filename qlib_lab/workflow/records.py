"""Pre-registered Evaluation & Gate Records: SignalRecord, DirectionGateRecord, PortfolioGateRecord."""
from __future__ import annotations

import abc
from collections.abc import Mapping, Sequence
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats as sps

from core.quant import forecast_eval, gate_stats, validate
from qlib_lab import RESEARCH_FLAGS
from qlib_lab.data.dataset import DatasetH, authorized_eval_context
from qlib_lab.data.handler import DataHandlerLP
from qlib_lab.data.labels import DIRECTION_CLASSES
from qlib_lab.expression.ast_nodes import _epoch_seconds_array, _to_utc_timestamps
from qlib_lab.models.base import Model
from qlib_lab.models.direction import PriorFrequencyBaselineModel
from qlib_lab.registry import register_component
from qlib_lab.workflow.ledger_bridge import register_trial_and_compute_neff
from qlib_lab.workflow.recorder import DEFAULT_PINNED_UTC, FileGovernanceRecorder
from tools.research import adaptive_bid_gap_preview as br26_preview


def _wilson_lower_z(successes: int, total: int, z: float = 1.959963984540054) -> float:
    if total <= 0:
        return 0.0
    if abs(z - 1.959963984540054) < 1e-12:
        return float(br26_preview.wilson_lower(successes, total))
    p = successes / float(total)
    margin = z * math.sqrt(p * (1.0 - p) / total + (z * z) / (4.0 * total * total))
    return float((p + (z * z) / (2.0 * total) - margin) / (1.0 + (z * z) / total))


class RecordTemp(metaclass=abc.ABCMeta):
    """Base record generator writing structured JSON/NPZ artifacts to a FileGovernanceRecorder."""

    def __init__(self, recorder: FileGovernanceRecorder | None = None) -> None:
        self.recorder = recorder

    @abc.abstractmethod
    def generate(self, **kwargs: Any) -> dict[str, Any]:
        """Execute evaluation and persist results."""


@register_component("record")
class SignalRecord(RecordTemp):
    """Signal quality diagnostics: IC, RankIC, ICIR, RankICIR, Newey-West HAC t, Q1..Q5 bucket spread."""

    def __init__(
        self,
        model: Model | None = None,
        dataset: DatasetH | None = None,
        recorder: FileGovernanceRecorder | None = None,
        segment: str = "test",
        label_col: str | None = None,
        hac_lag: int = 5,
    ) -> None:
        super().__init__(recorder=recorder)
        self.model = model
        self.dataset = dataset
        self.segment = str(segment)
        self.label_col = label_col
        self.hac_lag = int(hac_lag)

    def generate(
        self,
        *,
        pred: pd.Series | None = None,
        recorder: FileGovernanceRecorder | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        _ = kwargs
        rec = recorder or self.recorder
        if self.dataset is None:
            raise ValueError("SignalRecord requires a DatasetH")
        if pred is None:
            if self.model is None:
                raise ValueError("SignalRecord requires either `model` or `pred`")
            pred = self.model.predict(self.dataset, segment=self.segment)

        with authorized_eval_context("SignalRecord"):
            lbl_df = self.dataset.prepare(self.segment, col_set="label", data_key=DataHandlerLP.DK_L)

        if isinstance(lbl_df, pd.Series):
            y_ser = lbl_df
        else:
            col = (
                self.label_col
                if (self.label_col and self.label_col in lbl_df.columns)
                else ("realized_log_return" if "realized_log_return" in lbl_df.columns else str(lbl_df.columns[0]))
            )
            y_ser = lbl_df[col]

        common = pred.index.intersection(y_ser.index)
        s_pred = pred.reindex(common).astype(np.float64)
        s_lbl = y_ser.reindex(common).astype(np.float64)
        valid = np.isfinite(s_pred.to_numpy()) & np.isfinite(s_lbl.to_numpy())
        s_pred = s_pred.loc[valid]
        s_lbl = s_lbl.loc[valid]

        if len(s_pred) < 5:
            report = {
                "schema": "tradegen-qlib-signal-record-v1",
                "segment": self.segment,
                "n_samples": int(len(s_pred)),
                "status": "INSUFFICIENT_SAMPLES",
                "research_flags": dict(RESEARCH_FLAGS),
                **RESEARCH_FLAGS,
            }
            if rec is not None:
                rec.save_objects(pred=s_pred, signal_report=report)
            return report

        df_eval = pd.DataFrame({"score": s_pred, "label": s_lbl}, index=s_pred.index)
        counts_per_dt = df_eval.groupby(level="datetime").size()
        median_cs_n = float(counts_per_dt.median()) if len(counts_per_dt) else 0.0

        # Pooled / time-series metrics (always well-defined even for single-asset KRW-BTC)
        p_arr = df_eval["score"].to_numpy(dtype=np.float64)
        y_arr = df_eval["label"].to_numpy(dtype=np.float64)
        if np.std(p_arr) > 1e-15 and np.std(y_arr) > 1e-15:
            ts_ic = float(np.corrcoef(p_arr, y_arr)[0, 1])
            ts_rank_ic = float(sps.spearmanr(p_arr, y_arr).statistic)
            zp = (p_arr - np.mean(p_arr)) / np.std(p_arr, ddof=1)
            zy = (y_arr - np.mean(y_arr)) / np.std(y_arr, ddof=1)
            ts_nw_t = float(validate.newey_west_t(zp * zy, lag=self.hac_lag))
        else:
            ts_ic, ts_rank_ic, ts_nw_t = 0.0, 0.0, 0.0

        # Block ICIR over non-overlapping chunks of >=10 observations for single-asset stability
        n_chunks = max(2, min(10, len(p_arr) // 10))
        chunk_ics, chunk_rics = [], []
        if len(p_arr) >= 20:
            for idx_chunk in np.array_split(np.arange(len(p_arr)), n_chunks):
                pc, yc = p_arr[idx_chunk], y_arr[idx_chunk]
                if np.std(pc) > 1e-15 and np.std(yc) > 1e-15:
                    chunk_ics.append(float(np.corrcoef(pc, yc)[0, 1]))
                    chunk_rics.append(float(sps.spearmanr(pc, yc).statistic))
        ts_ic_std = float(np.std(chunk_ics, ddof=1)) if len(chunk_ics) > 1 else float("nan")
        ts_ric_std = float(np.std(chunk_rics, ddof=1)) if len(chunk_rics) > 1 else float("nan")
        ts_icir = float(np.mean(chunk_ics) / ts_ic_std) if (chunk_ics and ts_ic_std > 1e-12) else 0.0
        ts_rank_icir = float(np.mean(chunk_rics) / ts_ric_std) if (chunk_rics and ts_ric_std > 1e-12) else 0.0

        # Cross-sectional per-timestamp IC when universe has >= 3 instruments per timestamp
        cs_ics: list[float] = []
        cs_rics: list[float] = []
        if median_cs_n >= 3.0:
            for _dt, grp in df_eval.groupby(level="datetime"):
                if len(grp) < 3:
                    continue
                gp = grp["score"].to_numpy(dtype=np.float64)
                gy = grp["label"].to_numpy(dtype=np.float64)
                if np.std(gp) > 1e-15 and np.std(gy) > 1e-15:
                    cs_ics.append(float(np.corrcoef(gp, gy)[0, 1]))
                    cs_rics.append(float(sps.spearmanr(gp, gy).statistic))

        if len(cs_ics) >= 5:
            ic_arr = np.asarray(cs_ics, dtype=np.float64)
            ric_arr = np.asarray(cs_rics, dtype=np.float64)
            ic_mean = float(np.mean(ic_arr))
            ic_std = float(np.std(ic_arr, ddof=1))
            icir = float(ic_mean / ic_std) if ic_std > 1e-12 else 0.0
            rank_ic_mean = float(np.mean(ric_arr))
            rank_ic_std = float(np.std(ric_arr, ddof=1))
            rank_icir = float(rank_ic_mean / rank_ic_std) if rank_ic_std > 1e-12 else 0.0
            ic_nw_t = float(validate.newey_west_t(ic_arr, lag=self.hac_lag))
            rank_ic_nw_t = float(validate.newey_west_t(ric_arr, lag=self.hac_lag))
            mode_used = "cross_sectional"
        else:
            ic_mean = ts_ic
            ic_std = ts_ic_std if math.isfinite(ts_ic_std) else 0.0
            icir = ts_icir
            rank_ic_mean = ts_rank_ic
            rank_ic_std = ts_ric_std if math.isfinite(ts_ric_std) else 0.0
            rank_icir = ts_rank_icir
            ic_nw_t = ts_nw_t
            rank_ic_nw_t = ts_nw_t
            mode_used = "time_series"

        # Q1..Q5 quintile bucket mean returns & Q5 - Q1 long-short spread
        ranks_pct = (
            df_eval.groupby(level="datetime")["score"].rank(pct=True, method="first")
            if mode_used == "cross_sectional"
            else df_eval["score"].rank(pct=True, method="first")
        )
        buckets = np.minimum((ranks_pct.to_numpy(dtype=np.float64) * 5.0).astype(np.int64), 4)
        quintile_means: dict[str, float] = {}
        for q in range(5):
            m = buckets == q
            quintile_means[f"Q{q + 1}"] = float(np.mean(y_arr[m])) if np.any(m) else 0.0
        q5_q1_spread = quintile_means["Q5"] - quintile_means["Q1"]

        report = {
            "schema": "tradegen-qlib-signal-record-v1",
            "segment": self.segment,
            "mode": mode_used,
            "n_samples": int(len(df_eval)),
            "IC": ic_mean,
            "IC_std": ic_std,
            "ICIR": icir,
            "IC_hac_t": ic_nw_t,
            "RankIC": rank_ic_mean,
            "RankIC_std": rank_ic_std,
            "RankICIR": rank_icir,
            "RankIC_hac_t": rank_ic_nw_t,
            "quintile_returns": quintile_means,
            "Q5_minus_Q1_spread": q5_q1_spread,
            "research_flags": dict(RESEARCH_FLAGS),
            **RESEARCH_FLAGS,
        }
        if rec is not None:
            rec.log_metrics(
                IC=ic_mean,
                ICIR=icir,
                RankIC=rank_ic_mean,
                RankICIR=rank_icir,
                RankIC_hac_t=rank_ic_nw_t,
                Q5_minus_Q1_spread=q5_q1_spread,
            )
            rec.save_objects(pred=s_pred, signal_report=report)
        return report


@register_component("record")
class DirectionGateRecord(RecordTemp):
    """Pre-registered Stage-1 Direction Forecast Gate (`docs/direction-model-study-design.md` §7).

    Evaluates:
    - Criterion 1: Non-overlapping outcome windows, call count >= min_validation_calls,
      nominal 95% Wilson lower bound >= confidence, calibration gap <= max_calibration_gap.
    - Criterion 2: Conditional Up-vs-Down log-loss on non-neutral windows vs B1 & B0,
      24-bar day-block bootstrap 95% one-sided lower bound, plus `forecast_eval.dm_test` & `mcs`.
    - Interim S2 stop check & Criterion 4 half-window stability check.
    """

    def __init__(
        self,
        model: Model | None = None,
        baseline_b1: Model | None = None,
        dataset: DatasetH | None = None,
        baseline_b0: Model | None = None,
        baseline_b2: Model | None = None,
        recorder: FileGovernanceRecorder | None = None,
        horizon_bars: int = 2,
        step_seconds: int = 3600,
        hurdle_bps: int = 10,
        confidence: float = 0.60,
        min_validation_calls: int = 20,
        max_calibration_gap: float = 0.10,
        logloss_margin: float = 0.0,
        block_bars: int = 24,
        bootstrap_B: int = 2000,
        mcs_B: int = 1000,
        seed: int = 11,
        bonferroni_z: float | None = None,
        check_interim_s2: bool = False,
    ) -> None:
        super().__init__(recorder=recorder)
        self.model = model
        self.baseline_b1 = baseline_b1
        self.dataset = dataset
        self.baseline_b0 = baseline_b0
        self.baseline_b2 = baseline_b2
        self.horizon_bars = int(horizon_bars)
        self.step_seconds = int(step_seconds)
        self.hurdle_bps = int(hurdle_bps)
        self.confidence = float(confidence)
        self.min_validation_calls = int(min_validation_calls)
        self.max_calibration_gap = float(max_calibration_gap)
        self.logloss_margin = float(logloss_margin)
        self.block_bars = int(block_bars)
        self.bootstrap_B = int(bootstrap_B)
        self.mcs_B = int(mcs_B)
        self.seed = int(seed)
        self.bonferroni_z = float(bonferroni_z) if bonferroni_z is not None else 1.959963984540054
        self.check_interim_s2 = bool(check_interim_s2)

    @property
    def horizon_seconds(self) -> int:
        return self.horizon_bars * self.step_seconds

    def _score_criterion1_nonoverlap(
        self,
        proba_df: pd.DataFrame,
        realized_ret: pd.Series,
    ) -> dict[str, Any]:
        """Exact non-overlapping window counting matching `direction_forecast_adapter.py` lines 182-201."""
        up_bar = math.log1p(self.hurdle_bps / 10000.0)
        down_bar = math.log1p(-self.hurdle_bps / 10000.0)
        stats: dict[str, dict[str, Any]] = {
            "up": {"calls": 0, "hits": 0, "prob_sum": 0.0},
            "down": {"calls": 0, "hits": 0, "prob_sum": 0.0},
        }
        windows = 0

        # Group per instrument and step non-overlapping windows in chronological order
        inst_all = proba_df.index.get_level_values("instrument")
        for inst in inst_all.unique():
            sub_p = proba_df.loc[inst_all == inst].sort_index()
            sub_r = realized_ret.reindex(sub_p.index).to_numpy(dtype=np.float64)
            dts = _to_utc_timestamps(sub_p.index.get_level_values("datetime"))
            epochs = _epoch_seconds_array(dts)
            p_mat = sub_p[list(DIRECTION_CLASSES)].to_numpy(dtype=np.float64)

            last_as_of: float | None = None
            for i in range(len(sub_p)):
                if not np.all(np.isfinite(p_mat[i])) or not math.isfinite(float(sub_r[i])):
                    continue
                as_of_ep = float(epochs[i])
                if last_as_of is not None and as_of_ep < last_as_of + self.horizon_seconds - 1e-6:
                    continue
                last_as_of = as_of_ep
                windows += 1

                p_up, p_down, p_neu = float(p_mat[i, 0]), float(p_mat[i, 1]), float(p_mat[i, 2])
                top = max(p_up, p_down, p_neu)
                winners = [c for c, v in zip(DIRECTION_CLASSES, (p_up, p_down, p_neu)) if abs(v - top) <= 1e-12]
                if len(winners) != 1:
                    continue
                direction = winners[0]
                if direction in ("up", "down"):
                    p_dir = p_up if direction == "up" else p_down
                    if p_dir + 1e-12 >= self.confidence:
                        hit = int(sub_r[i] > up_bar if direction == "up" else sub_r[i] < down_bar)
                        st = stats[direction]
                        st["calls"] += 1
                        st["hits"] += hit
                        st["prob_sum"] += p_dir

        summary: dict[str, Any] = {"nonoverlap_windows": windows, "directions": {}}
        for d in ("up", "down"):
            calls = int(stats[d]["calls"])
            hits = int(stats[d]["hits"])
            hit_rate = hits / float(calls) if calls > 0 else 0.0
            mean_prob = float(stats[d]["prob_sum"]) / float(calls) if calls > 0 else 0.0
            cal_gap = abs(hit_rate - mean_prob) if calls > 0 else 1.0
            w_lo = _wilson_lower_z(hits, calls, self.bonferroni_z)
            passed = bool(
                calls >= self.min_validation_calls
                and w_lo >= self.confidence - 1e-12
                and cal_gap <= self.max_calibration_gap + 1e-12
            )
            summary["directions"][d] = {
                "calls": calls,
                "hits": hits,
                "hit_rate": hit_rate,
                "mean_called_prob": mean_prob,
                "calibration_gap": cal_gap,
                "wilson_lower": w_lo,
                "passes": passed,
            }
        summary["passing_directions"] = [d for d in ("up", "down") if summary["directions"][d]["passes"]]
        return summary

    @staticmethod
    def _conditional_up_down_losses(proba_df: pd.DataFrame, y_cls: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Compute conditional Up-vs-Down binary log-loss (on y in {0, 1}) and 3-class log-loss."""
        p = np.clip(proba_df[list(DIRECTION_CLASSES)].to_numpy(dtype=np.float64), 1e-12, 1.0)
        p /= np.sum(p, axis=1, keepdims=True)
        y_int = y_cls.astype(np.int64)
        ll_3 = -np.log(np.clip(p[np.arange(y_int.size), y_int], 1e-12, 1.0))

        denom_ud = np.maximum(p[:, 0] + p[:, 1], 1e-12)
        q_up = np.clip(p[:, 0] / denom_ud, 1e-12, 1.0 - 1e-12)
        ll_ud = np.where(
            y_int == 0,
            -np.log(q_up),
            np.where(y_int == 1, -np.log(1.0 - q_up), np.nan),
        )
        return ll_ud, ll_3

    def generate(
        self,
        *,
        proba_m: pd.DataFrame | None = None,
        proba_b1: pd.DataFrame | None = None,
        proba_b0: pd.DataFrame | None = None,
        proba_b2: pd.DataFrame | None = None,
        recorder: FileGovernanceRecorder | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        _ = kwargs
        rec = recorder or self.recorder
        if self.dataset is None:
            raise ValueError("DirectionGateRecord requires a DatasetH")

        if proba_m is None:
            if self.model is None:
                raise ValueError("DirectionGateRecord requires `model` or `proba_m`")
            proba_m = self.model.predict_proba(self.dataset, "test")
        if proba_b1 is None:
            if self.baseline_b1 is None:
                raise ValueError("DirectionGateRecord requires `baseline_b1` or `proba_b1`")
            proba_b1 = self.baseline_b1.predict_proba(self.dataset, "test")
        if proba_b0 is None:
            if self.baseline_b0 is not None:
                proba_b0 = self.baseline_b0.predict_proba(self.dataset, "test")
            else:
                b0_auto = PriorFrequencyBaselineModel().fit(self.dataset)
                proba_b0 = b0_auto.predict_proba(self.dataset, "test")
        if proba_b2 is None and self.baseline_b2 is not None:
            proba_b2 = self.baseline_b2.predict_proba(self.dataset, "test")

        with authorized_eval_context("DirectionGateRecord"):
            lbl_df = self.dataset.prepare("test", col_set="label", data_key=DataHandlerLP.DK_L)

        common = (
            proba_m.index.intersection(proba_b1.index)
            .intersection(proba_b0.index)
            .intersection(lbl_df.index)
            .sort_values()
        )
        pm = proba_m.reindex(common)
        pb1 = proba_b1.reindex(common)
        pb0 = proba_b0.reindex(common)
        y_cls_ser = lbl_df["direction_class"].reindex(common)
        y_ret_ser = lbl_df["realized_log_return"].reindex(common)

        ok_mask = (
            np.all(np.isfinite(pm.to_numpy(dtype=np.float64)), axis=1)
            & np.all(np.isfinite(pb1.to_numpy(dtype=np.float64)), axis=1)
            & np.all(np.isfinite(pb0.to_numpy(dtype=np.float64)), axis=1)
            & np.isfinite(y_cls_ser.to_numpy(dtype=np.float64))
            & np.isfinite(y_ret_ser.to_numpy(dtype=np.float64))
        )
        pm = pm.loc[ok_mask]
        pb1 = pb1.loc[ok_mask]
        pb0 = pb0.loc[ok_mask]
        y_cls = y_cls_ser.loc[ok_mask].to_numpy(dtype=np.float64)
        y_ret = y_ret_ser.loc[ok_mask]

        # Criterion 1: per-direction gate on M (and B1, B2 for reference)
        crit1_m = self._score_criterion1_nonoverlap(pm, y_ret)
        crit1_b1 = self._score_criterion1_nonoverlap(pb1, y_ret)
        crit1_b2 = (
            self._score_criterion1_nonoverlap(proba_b2.reindex(common).loc[ok_mask], y_ret)
            if proba_b2 is not None
            else None
        )

        # Criterion 2: Conditional Up-vs-Down log-loss on non-neutral bars + 24-bar block bootstrap + DM + MCS
        ll_ud_m, ll_3_m = self._conditional_up_down_losses(pm, y_cls)
        ll_ud_b1, ll_3_b1 = self._conditional_up_down_losses(pb1, y_cls)
        ll_ud_b0, ll_3_b0 = self._conditional_up_down_losses(pb0, y_cls)

        non_neutral = np.isfinite(ll_ud_m) & np.isfinite(ll_ud_b1) & np.isfinite(ll_ud_b0)
        n_non_neutral = int(np.sum(non_neutral))

        if n_non_neutral >= 4:
            loss_m_nn = ll_ud_m[non_neutral]
            loss_b1_nn = ll_ud_b1[non_neutral]
            loss_b0_nn = ll_ud_b0[non_neutral]
            mean_impr = float(np.mean(loss_b1_nn - loss_m_nn))
            beats_b0 = bool(float(np.mean(loss_m_nn)) < float(np.mean(loss_b0_nn)))

            # Preserve 24-bar KST-day grid alignment by resampling blocks of length `block_bars` over full bar grid!
            n_grid = len(pm)
            blk = min(self.block_bars, max(2, n_grid // 2))
            idx_boot = gate_stats.block_indices(n_grid, blk, self.bootstrap_B, self.seed, kind="circular")
            diff_grid = np.where(non_neutral, ll_ud_b1 - ll_ud_m, np.nan)
            sampled = diff_grid[idx_boot]
            with np.errstate(invalid="ignore"):
                boot_means = np.nanmean(sampled, axis=1)
            fin_boots = boot_means[np.isfinite(boot_means)]
            ci95_lo = float(np.quantile(fin_boots, 0.05)) if fin_boots.size > 0 else float("nan")
            ci95_hi = float(np.quantile(fin_boots, 0.95)) if fin_boots.size > 0 else float("nan")

            # Interim half-window S2 bound
            half_grid = max(4, n_grid // 2)
            blk_half = min(self.block_bars, max(2, half_grid // 2))
            idx_half = gate_stats.block_indices(half_grid, blk_half, self.bootstrap_B, self.seed + 1, kind="circular")
            sampled_half = diff_grid[:half_grid][idx_half]
            with np.errstate(invalid="ignore"):
                half_means = np.nanmean(sampled_half, axis=1)
            fin_half = half_means[np.isfinite(half_means)]
            interim_upper95 = float(np.quantile(fin_half, 0.95)) if fin_half.size > 0 else float("nan")

            dm_res = forecast_eval.dm_test(loss_m_nn, loss_b1_nn, h=self.horizon_bars)
            if n_non_neutral >= 30:
                mcs_res = forecast_eval.mcs(
                    {"M": loss_m_nn, "B1": loss_b1_nn, "B0": loss_b0_nn},
                    h=self.horizon_bars,
                    B=self.mcs_B,
                    seed=self.seed,
                )
            else:
                mcs_res = {"in_set": {"M": None, "B1": None, "B0": None}, "p": {}, "note": f"n={n_non_neutral} < 30"}

            crit2_pass = bool(math.isfinite(ci95_lo) and ci95_lo > self.logloss_margin and beats_b0)
        else:
            mean_impr, ci95_lo, ci95_hi, interim_upper95 = 0.0, float("nan"), float("nan"), float("nan")
            beats_b0 = False
            dm_res = {"t": float("nan"), "p": float("nan"), "mean_diff": float("nan"), "n": n_non_neutral}
            mcs_res = {"in_set": {}, "p": {}, "note": "insufficient non-neutral outcomes"}
            crit2_pass = False

        # Criterion 4: Half-window stability (point estimates in both halves)
        mid = len(pm) // 2
        half_reports: list[dict[str, Any]] = []
        for h_name, sl in (("first_half", slice(0, mid)), ("second_half", slice(mid, len(pm)))):
            pm_h = pm.iloc[sl]
            y_ret_h = y_ret.iloc[sl]
            c1_h = self._score_criterion1_nonoverlap(pm_h, y_ret_h)
            nn_h = non_neutral[sl]
            if int(np.sum(nn_h)) > 0:
                m_ll_h = float(np.mean(ll_ud_m[sl][nn_h]))
                b1_ll_h = float(np.mean(ll_ud_b1[sl][nn_h]))
            else:
                m_ll_h, b1_ll_h = float("nan"), float("nan")
            half_reports.append(
                {
                    "half": h_name,
                    "up_hit_rate": c1_h["directions"]["up"]["hit_rate"],
                    "up_calls": c1_h["directions"]["up"]["calls"],
                    "down_hit_rate": c1_h["directions"]["down"]["hit_rate"],
                    "down_calls": c1_h["directions"]["down"]["calls"],
                    "m_cond_logloss": m_ll_h,
                    "b1_cond_logloss": b1_ll_h,
                    "logloss_beats_b1": bool(math.isfinite(m_ll_h) and math.isfinite(b1_ll_h) and m_ll_h < b1_ll_h),
                }
            )

        stable_directions: list[str] = []
        for d in crit1_m["passing_directions"]:
            hr_key = f"{d}_hit_rate"
            calls_key = f"{d}_calls"
            if all(
                h[calls_key] > 0 and h[hr_key] >= self.confidence - 1e-12 and h["logloss_beats_b1"]
                for h in half_reports
            ):
                stable_directions.append(d)
        crit4_pass = len(stable_directions) > 0

        max_calls = max(
            crit1_m["directions"]["up"]["calls"],
            crit1_m["directions"]["down"]["calls"],
        )
        if self.check_interim_s2 and math.isfinite(interim_upper95) and interim_upper95 <= 0.0:
            outcome = "STOPPED"
            revise_target = "logloss_decay"
        elif max_calls < self.min_validation_calls:
            outcome = "INCONCLUSIVE"
            revise_target = "sample"
        elif crit1_m["passing_directions"] and crit2_pass and crit4_pass:
            outcome = "PASS"
            revise_target = None
        else:
            outcome = "NOT_SHOWN"
            if not crit1_m["passing_directions"]:
                # Check if calibration gap failed vs hit rate
                any_cal_fail = any(
                    crit1_m["directions"][d]["calls"] >= self.min_validation_calls
                    and crit1_m["directions"][d]["calibration_gap"] > self.max_calibration_gap
                    for d in ("up", "down")
                )
                revise_target = "calibration_drift" if any_cal_fail else "over-search"
            elif not crit2_pass:
                revise_target = "logloss_decay"
            else:
                revise_target = "regime"

        report = {
            "schema": "tradegen-qlib-direction-gate-v1",
            "outcome": outcome,
            "qualified_directions": stable_directions if outcome == "PASS" else [],
            "revise_target": revise_target,
            "criterion_1_m": crit1_m,
            "criterion_1_b1": crit1_b1,
            "criterion_1_b2": crit1_b2,
            "criterion_2": {
                "n_non_neutral": n_non_neutral,
                "m_cond_logloss": float(np.nanmean(ll_ud_m)) if n_non_neutral else None,
                "b1_cond_logloss": float(np.nanmean(ll_ud_b1)) if n_non_neutral else None,
                "b0_cond_logloss": float(np.nanmean(ll_ud_b0)) if n_non_neutral else None,
                "m_3class_logloss": float(np.mean(ll_3_m)) if len(ll_3_m) else None,
                "b1_3class_logloss": float(np.mean(ll_3_b1)) if len(ll_3_b1) else None,
                "mean_improvement_over_b1": mean_impr,
                "block_boot_ci95_lower": ci95_lo,
                "block_boot_ci95_upper": ci95_hi,
                "interim_s2_upper95": interim_upper95,
                "beats_b0_point": beats_b0,
                "dm_test": dm_res,
                "mcs": mcs_res,
                "passes": crit2_pass,
            },
            "criterion_4_halves": half_reports,
            "criterion_4_passes": crit4_pass,
            "research_flags": dict(RESEARCH_FLAGS),
            **RESEARCH_FLAGS,
        }
        if rec is not None:
            rec.log_metrics(
                stage1_pass=int(outcome == "PASS"),
                cond_logloss_impr=mean_impr,
                cond_logloss_ci95_lo=ci95_lo if math.isfinite(ci95_lo) else 0.0,
            )
            rec.save_objects(proba_m=pm, direction_gate_report=report)
        return report


@register_component("record")
class PortfolioGateRecord(RecordTemp):
    """Causal self-financing post-fee portfolio gate -> `validate.walk_forward` + `score_strategy` + FamilyLedger DSR + 2x/3x cost survival -> ModelCard."""

    def __init__(
        self,
        model: Model | None = None,
        dataset: DatasetH | None = None,
        recorder: FileGovernanceRecorder | None = None,
        ledger_dir: Path | None = None,
        family_id: str = "QLIB-ALPHA",
        rule_id: str = "QLIB-PORTFOLIO",
        card_id: str = "qlib_portfolio_card",
        market: str = "KR",
        cost_bps: float = 10.0,
        signal_grid: Sequence[Mapping[str, Any]] | None = None,
        w_is: int = 252,
        w_oos: int = 63,
        min_is: int = 126,
        embargo: int = 1,
        require_3x_cost_survival: bool = True,
        run_utc: str = DEFAULT_PINNED_UTC,
        seed: int = 11,
    ) -> None:
        super().__init__(recorder=recorder)
        self.model = model
        self.dataset = dataset
        self.ledger_dir = Path(ledger_dir) if ledger_dir is not None else None
        self.family_id = str(family_id)
        self.rule_id = str(rule_id)
        self.card_id = str(card_id)
        self.market = str(market)
        self.cost_bps = float(cost_bps)
        self.signal_grid: list[dict[str, Any]] = [
            dict(g)
            for g in (
                signal_grid
                or [
                    {"threshold": 0.0, "hysteresis": 0.0},
                    {"threshold": 0.05, "hysteresis": 0.0},
                    {"threshold": 0.10, "hysteresis": 0.0},
                    {"threshold": 0.0, "hysteresis": 0.05},
                    {"threshold": 0.05, "hysteresis": 0.05},
                    {"threshold": 0.10, "hysteresis": 0.05},
                    {"threshold": 0.15, "hysteresis": 0.0},
                    {"threshold": 0.15, "hysteresis": 0.05},
                ]
            )
        ]
        self.w_is = int(w_is)
        self.w_oos = int(w_oos)
        self.min_is = int(min_is)
        self.embargo = int(embargo)
        self.require_3x_cost_survival = bool(require_3x_cost_survival)
        self.run_utc = str(run_utc)
        self.seed = int(seed)

    def _effective_cost_bps(self, instruments: Sequence[str]) -> float:
        floor_bp, _classes = validate.cost_floor_bp(list(instruments))
        if floor_bp is not None and self.cost_bps < floor_bp - 1e-9:
            raise ValueError(
                f"Configured cost_bps={self.cost_bps} is below pre-registered venue floor {floor_bp} bp for {list(instruments)}"
            )
        return max(self.cost_bps, float(floor_bp or 0.0))

    @staticmethod
    def _build_causal_pnl_grid(
        score_mat: np.ndarray,
        ret_mat: np.ndarray,
        grid: Sequence[Mapping[str, Any]],
        cost_bps: float,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """Compute (T, G) net P&L at 1x, 2x, 3x costs and turnover from causal score_mat & next-period ret_mat."""
        T, N = score_mat.shape
        G = len(grid)
        pnl_1x = np.zeros((T, G), dtype=np.float64)
        pnl_2x = np.zeros((T, G), dtype=np.float64)
        pnl_3x = np.zeros((T, G), dtype=np.float64)
        turnover = np.zeros((T, G), dtype=np.float64)
        rate = float(cost_bps) / 10000.0

        for g_idx, cfg in enumerate(grid):
            thresh = float(cfg.get("threshold", 0.0))
            hyst = float(cfg.get("hysteresis", 0.0))
            prev_w = np.zeros(N, dtype=np.float64)

            for t in range(T):
                sc = score_mat[t]
                rt = ret_mat[t]
                ok = np.isfinite(sc) & np.isfinite(rt)
                target_w = np.zeros(N, dtype=np.float64)
                if np.any(ok):
                    active = ok & (sc > thresh)
                    if np.any(active):
                        # Equal-weight long across instruments exceeding threshold (capped sum <= 1.0)
                        raw_w = np.where(active, 1.0 / max(1.0, float(np.sum(active))), 0.0)
                    else:
                        raw_w = np.zeros(N, dtype=np.float64)
                    # Hysteresis band: hold previous weight if |raw_w - prev_w| < hyst
                    target_w = np.where(np.abs(raw_w - prev_w) >= hyst, raw_w, prev_w)

                dw = float(np.sum(np.abs(target_w - prev_w)))
                gross = float(np.sum(target_w * np.where(np.isfinite(rt), rt, 0.0)))
                pnl_1x[t, g_idx] = gross - rate * dw
                pnl_2x[t, g_idx] = gross - 2.0 * rate * dw
                pnl_3x[t, g_idx] = gross - 3.0 * rate * dw
                turnover[t, g_idx] = dw
                prev_w = target_w

        return pnl_1x, pnl_2x, pnl_3x, turnover

    def generate(
        self,
        *,
        pred_full: pd.Series | None = None,
        recorder: FileGovernanceRecorder | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        _ = kwargs
        rec = recorder or self.recorder
        if self.dataset is None:
            raise ValueError("PortfolioGateRecord requires a DatasetH")

        # Predict causally across the full handler span (DK_I) so walk_forward can tile IS/OOS windows cleanly
        full_slice = slice(None, None)
        with authorized_eval_context("PortfolioGateRecord"):
            if pred_full is None:
                if self.model is None:
                    raise ValueError("PortfolioGateRecord requires `model` or `pred_full`")
                x_all = self.dataset.handler.fetch(full_slice, col_set="feature", data_key=DataHandlerLP.DK_I)
                tmp_ds = DatasetH(
                    handler=self.dataset.handler,
                    segments={"all_infer": (x_all.index.get_level_values("datetime").min(), x_all.index.get_level_values("datetime").max())},
                    purge_outcomes=False,
                )
                pred_full = self.model.predict(tmp_ds, "all_infer")
            lbl_all = self.dataset.handler.fetch(full_slice, col_set="label", data_key=DataHandlerLP.DK_R)

        ret_col = "realized_log_return" if "realized_log_return" in lbl_all.columns else str(lbl_all.columns[0])
        ret_ser = np.expm1(lbl_all[ret_col].astype(np.float64))  # Convert log return to simple return for equity P&L

        common = pred_full.index.intersection(ret_ser.index).sort_values()
        s_mat_df = pred_full.reindex(common).unstack(level="instrument").sort_index()
        r_mat_df = ret_ser.reindex(common).unstack(level="instrument").sort_index()
        valid_rows = s_mat_df.notna().any(axis=1) & r_mat_df.notna().any(axis=1)
        s_mat_df = s_mat_df.loc[valid_rows]
        r_mat_df = r_mat_df.loc[valid_rows]

        instruments = [str(c) for c in s_mat_df.columns]
        eff_cost_bps = self._effective_cost_bps(instruments)
        dates_iso = _to_utc_timestamps(s_mat_df.index).strftime("%Y-%m-%d").tolist()

        pnl_1x, pnl_2x, pnl_3x, turn = self._build_causal_pnl_grid(
            s_mat_df.to_numpy(dtype=np.float64),
            r_mat_df.to_numpy(dtype=np.float64),
            self.signal_grid,
            eff_cost_bps,
        )

        T = len(dates_iso)
        w_is = min(self.w_is, max(20, T // 2))
        min_is = min(self.min_is, w_is)
        w_oos = min(self.w_oos, max(10, (T - min_is - self.embargo - 2) // 2))
        wf = validate.walk_forward(
            pnl_1x,
            dates_iso,
            turnover=turn,
            pnl_stress=pnl_2x,
            w_is=w_is,
            w_oos=max(5, w_oos),
            embargo=self.embargo,
            min_is=min_is,
        )
        wf_3x = validate.walk_forward(
            pnl_1x,
            dates_iso,
            turnover=turn,
            pnl_stress=pnl_3x,
            w_is=w_is,
            w_oos=max(5, w_oos),
            embargo=self.embargo,
            min_is=min_is,
        )
        sr_stress_3x = float(validate.sharpe(wf_3x.pnl_stress))

        # Register trial in FamilyLedger and compute cumulative N_eff across ALL family trials!
        eff_ledger_dir = self.ledger_dir or (rec.root_dir / "ledgers" if rec is not None else None)
        ledger_summary = None
        cumulative_n_trials = len(self.signal_grid)
        if eff_ledger_dir is not None:
            oos_series = pd.Series(wf.pnl, index=pd.Index(wf.dates), dtype=np.float64)
            ledger_summary = register_trial_and_compute_neff(
                ledger_dir=eff_ledger_dir,
                family_id=self.family_id,
                rule=self.rule_id,
                params={"grid_size": len(self.signal_grid), "cost_bps": eff_cost_bps, "w_is": w_is, "w_oos": w_oos},
                span=(dates_iso[0], dates_iso[-1]),
                market=self.market,
                run_utc=self.run_utc,
                diff_series=oos_series,
                delta_sr=float(validate.sharpe(wf.pnl)),
                script="qlib_lab.workflow.PortfolioGateRecord",
                cost=eff_cost_bps,
                seed=self.seed,
            )
            cumulative_n_trials = max(len(self.signal_grid), int(math.ceil(ledger_summary.n_eff)))

        strat_score = validate.score_strategy(
            wf,
            grid=self.signal_grid,
            full_pnl=pnl_1x,
            n_trials=cumulative_n_trials,
            seed=self.seed,
        )

        # Enforce 3x cost survival if configured
        decision = strat_score.decision
        reason = strat_score.reason
        revise_target = strat_score.revise_target
        if self.require_3x_cost_survival and sr_stress_3x <= 0.0 and decision == "PASS":
            decision = "REVISE"
            reason = f"3x cost survival failed (Sharpe at 3x costs = {sr_stress_3x:.2f} <= 0)"
            revise_target = "execution"

        pbo_claim = gate_stats.pbo_on_claim(
            pnl_1x,
            np.zeros(T, dtype=np.float64),
            objective="sharpe",
            S=8 if T < 500 else 16,
            min_configs=min(8, max(2, len(self.signal_grid))),
        )

        created_date = self.run_utc[:10]
        card = validate.ModelCard(
            card_id=self.card_id,
            kind="strategy",
            hypothesis=f"qlib_lab family {self.family_id} ({self.rule_id})",
            rules={"signal_grid_size": len(self.signal_grid), "embargo": self.embargo},
            universe={"market": self.market, "instruments": instruments},
            data={"start": dates_iso[0], "end": dates_iso[-1], "n_bars": T},
            costs={"cost_bps_per_side": eff_cost_bps, "stress_multipliers": [2.0, 3.0]},
            protocol={"w_is": w_is, "w_oos": w_oos, "embargo": self.embargo},
            trials={
                "grid_configs": len(self.signal_grid),
                "cumulative_n_trials": cumulative_n_trials,
                "ledger": ledger_summary.to_dict() if ledger_summary is not None else None,
            },
            seed=self.seed,
            stats={
                "sr_oos": strat_score.sr_oos,
                "sr_is": strat_score.sr_is,
                "sr_stress_2x": strat_score.sr_stress,
                "sr_stress_3x": sr_stress_3x,
                "dsr": strat_score.dsr,
                "pbo": strat_score.pbo,
                "max_drawdown": strat_score.max_drawdown,
                "turnover_annual": strat_score.turnover_annual,
            },
            tests={"pbo_cscv": pbo_claim, "ci90": list(strat_score.ci90)},
            decision=decision,
            decision_reason=reason,
            revise_target=revise_target,
            lines=list(strat_score.lines),
            created=created_date,
            author="TRADEGEN qlib_lab portfolio gate (research only)",
        )
        card_dict = {
            "schema": "tradegen-qlib-portfolio-card-v1",
            **json_compatible_card(card),
            "research_flags": dict(RESEARCH_FLAGS),
            **RESEARCH_FLAGS,
        }
        if rec is not None:
            rec.log_metrics(
                sr_oos=strat_score.sr_oos,
                dsr=strat_score.dsr,
                pbo=strat_score.pbo,
                sr_stress_2x=strat_score.sr_stress,
                sr_stress_3x=sr_stress_3x,
                cumulative_n_trials=cumulative_n_trials,
            )
            rec.save_objects(portfolio_gate_card=card_dict)
        return card_dict


def json_compatible_card(card: validate.ModelCard) -> dict[str, Any]:
    import json as _json
    raw = _json.loads(card.to_json())
    return raw
