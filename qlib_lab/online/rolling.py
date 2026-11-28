"""Leak-free TaskGen, RollingGen & RollingTrainer fixing Qlib's rolling processor contamination."""
from __future__ import annotations

import abc
import bisect
from collections.abc import Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from qlib_lab import RESEARCH_FLAGS
from qlib_lab.data.dataset import DatasetH
from qlib_lab.data.handler import DataHandlerLP
from qlib_lab.data.processors import StatefulProcessor
from qlib_lab.exceptions import FitLeakageError
from qlib_lab.expression.ast_nodes import _to_utc_timestamps
from qlib_lab.models.base import FrozenModelSpec, Model, ModelFT
from qlib_lab.registry import init_instance_by_config, register_component
from qlib_lab.workflow.recorder import DEFAULT_PINNED_UTC, R


class TaskGen(metaclass=abc.ABCMeta):
    """Base generator transforming one task template dict into a sequence of concrete task dicts."""

    @abc.abstractmethod
    def generate(self, task: Mapping[str, Any]) -> list[dict[str, Any]]:
        """Generate derived tasks from `task` without mutating `task` in place."""

    def __call__(self, task: Mapping[str, Any]) -> list[dict[str, Any]]:
        return self.generate(task)


def task_generator(
    tasks: Mapping[str, Any] | Sequence[Mapping[str, Any]],
    generators: TaskGen | Sequence[TaskGen],
) -> list[dict[str, Any]]:
    cur_list: list[dict[str, Any]] = [deepcopy(dict(tasks))] if isinstance(tasks, Mapping) else [deepcopy(dict(t)) for t in tasks]
    gen_list: list[TaskGen] = [generators] if isinstance(generators, TaskGen) else list(generators)
    for gen in gen_list:
        nxt: list[dict[str, Any]] = []
        for t in cur_list:
            nxt.extend(gen.generate(t))
        cur_list = nxt
    return cur_list


def _rebind_processor_configs_inplace(handler_cfg: dict[str, Any], fit_start_iso: str, fit_end_iso: str) -> None:
    """Rewrite [fit_start_time, fit_end_time] on every stateful processor config inside a task dict."""
    h_kw = handler_cfg.setdefault("kwargs", {})
    if "fit_start_time" in h_kw:
        h_kw["fit_start_time"] = fit_start_iso
    if "fit_end_time" in h_kw:
        h_kw["fit_end_time"] = fit_end_iso

    stateful_names = {"WinsorizeClip", "RobustZScoreNorm", "StandardZScoreNorm"}
    for chain_key in ("shared_processors", "infer_processors", "learn_processors"):
        chain = h_kw.get(chain_key)
        if not isinstance(chain, list):
            continue
        for i, item in enumerate(chain):
            if isinstance(item, dict) and item.get("class") in stateful_names:
                p_kw = item.setdefault("kwargs", {})
                p_kw["fit_start_time"] = fit_start_iso
                p_kw["fit_end_time"] = fit_end_iso
            elif isinstance(item, StatefulProcessor):
                cloned = deepcopy(item)
                cloned.rebind_fit_window(fit_start_iso, fit_end_iso)
                chain[i] = cloned


@register_component("task_gen")
class RollingGen(TaskGen):
    """Leak-free rolling task generator with automatic processor fit-window rebinding & disjoint OOS stamps.

    Fixes Qlib's rolling contamination bug by:
    1. Truncating `train` and `valid` ends by `embargo_bars + horizon_bars` before `test_start`;
    2. Rebinding every `StatefulProcessor` `[fit_start_time, fit_end_time]` to each window's `[train_start, train_end]`;
    3. Stamping disjoint `[active_from, active_until)` OOS intervals across all generated windows.
    """

    ROLL_EX = "expanding"
    ROLL_SD = "sliding"

    def __init__(
        self,
        calendar: Sequence[Any],
        step: int = 24,
        rtype: str = ROLL_EX,
        embargo_bars: int = 0,
        horizon_bars: int = 1,
        train_key: str = "train",
        valid_key: str = "valid",
        test_key: str = "test",
    ) -> None:
        if step < 1:
            raise ValueError("RollingGen step must be >= 1")
        if rtype not in (self.ROLL_EX, self.ROLL_SD):
            raise ValueError(f"rtype must be {self.ROLL_EX!r} or {self.ROLL_SD!r}, got {rtype!r}")
        if embargo_bars < 0 or horizon_bars < 0:
            raise ValueError("embargo_bars and horizon_bars must be >= 0")

        cal_utc = sorted(_to_utc_timestamps(pd.Index(list(calendar))).unique().tolist())
        if len(cal_utc) < 4:
            raise ValueError("RollingGen calendar requires at least 4 distinct timestamps")
        self.calendar: list[pd.Timestamp] = cal_utc
        self.step = int(step)
        self.rtype = rtype
        self.embargo_bars = int(embargo_bars)
        self.horizon_bars = int(horizon_bars)
        self.train_key = str(train_key)
        self.valid_key = str(valid_key)
        self.test_key = str(test_key)

    def _idx_ge(self, ts: Any) -> int:
        target = _to_utc_timestamps(pd.Index([ts]))[0]
        idx = bisect.bisect_left(self.calendar, target)
        if idx >= len(self.calendar):
            raise ValueError(f"Timestamp {target} lies beyond calendar end {self.calendar[-1]}")
        return idx

    def _idx_le(self, ts: Any) -> int:
        target = _to_utc_timestamps(pd.Index([ts]))[0]
        idx = bisect.bisect_right(self.calendar, target) - 1
        if idx < 0:
            raise ValueError(f"Timestamp {target} precedes calendar start {self.calendar[0]}")
        return idx

    def generate(self, task: Mapping[str, Any]) -> list[dict[str, Any]]:
        base = deepcopy(dict(task))
        ds_kw = base["dataset"]["kwargs"]
        raw_segs = ds_kw["segments"]

        tr_s0, tr_e0 = self._idx_ge(raw_segs[self.train_key][0]), self._idx_le(raw_segs[self.train_key][1])
        has_valid = self.valid_key in raw_segs
        if has_valid:
            va_s0, va_e0 = self._idx_ge(raw_segs[self.valid_key][0]), self._idx_le(raw_segs[self.valid_key][1])
            va_len = va_e0 - va_s0 + 1
        else:
            va_s0, va_e0, va_len = -1, -1, 0

        te_s0, te_final = self._idx_ge(raw_segs[self.test_key][0]), self._idx_le(raw_segs[self.test_key][1])
        tr_len = tr_e0 - tr_s0 + 1
        gap = self.embargo_bars + self.horizon_bars

        if len(self.calendar) >= 2:
            bar_delta = self.calendar[-1] - self.calendar[-2]
        else:
            bar_delta = pd.Timedelta(seconds=3600)

        tasks_out: list[dict[str, Any]] = []
        win_idx = 0
        cur_te_s = te_s0

        while cur_te_s <= te_final:
            cur_te_e = min(te_final, cur_te_s + self.step - 1)
            shift = cur_te_s - te_s0

            if has_valid:
                cur_va_e = cur_te_s - 1 - gap
                cur_va_s = max(0, cur_va_e - va_len + 1)
                cur_tr_e = cur_va_s - 1 - gap
            else:
                cur_va_s, cur_va_e = -1, -1
                cur_tr_e = cur_te_s - 1 - gap

            if self.rtype == self.ROLL_EX:
                cur_tr_s = tr_s0
            else:
                cur_tr_s = max(tr_s0, cur_tr_e - tr_len + 1)

            if cur_tr_e <= cur_tr_s or (has_valid and cur_va_e < cur_va_s):
                raise FitLeakageError(
                    f"Rolling window {win_idx} has insufficient lookback before test_start={self.calendar[cur_te_s]}"
                )

            tr_start_iso = self.calendar[cur_tr_s].strftime("%Y-%m-%dT%H:%M:%SZ")
            tr_end_iso = self.calendar[cur_tr_e].strftime("%Y-%m-%dT%H:%M:%SZ")
            te_start_iso = self.calendar[cur_te_s].strftime("%Y-%m-%dT%H:%M:%SZ")
            te_end_iso = self.calendar[cur_te_e].strftime("%Y-%m-%dT%H:%M:%SZ")

            active_from_ts = self.calendar[cur_te_s]
            active_until_ts = (
                self.calendar[cur_te_e + 1]
                if (cur_te_e + 1) < len(self.calendar)
                else (self.calendar[cur_te_e] + bar_delta)
            )

            t_copy = deepcopy(base)
            segs_k: dict[str, tuple[str, str]] = {
                self.train_key: (tr_start_iso, tr_end_iso),
            }
            if has_valid:
                va_start_iso = self.calendar[cur_va_s].strftime("%Y-%m-%dT%H:%M:%SZ")
                va_end_iso = self.calendar[cur_va_e].strftime("%Y-%m-%dT%H:%M:%SZ")
                segs_k[self.valid_key] = (va_start_iso, va_end_iso)
            segs_k[self.test_key] = (te_start_iso, te_end_iso)

            t_copy["dataset"]["kwargs"]["segments"] = segs_k
            t_copy["dataset"]["kwargs"]["embargo_bars"] = self.embargo_bars

            handler_obj_or_cfg = t_copy["dataset"]["kwargs"].get("handler")
            if isinstance(handler_obj_or_cfg, dict):
                _rebind_processor_configs_inplace(handler_obj_or_cfg, tr_start_iso, tr_end_iso)
                # Ensure handler end_time reaches cur_te_e if bounded
                h_kw = handler_obj_or_cfg.setdefault("kwargs", {})
                if h_kw.get("end_time") is not None:
                    h_kw["end_time"] = te_end_iso

            t_copy["rolling_meta"] = {
                "window_index": win_idx,
                "shift_bars": shift,
                "rtype": self.rtype,
                "fit_start_time": tr_start_iso,
                "fit_end_time": tr_end_iso,
                "active_from": active_from_ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "active_until": active_until_ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
            }
            tasks_out.append(t_copy)
            cur_te_s += self.step
            win_idx += 1

        # Static disjointness & causality self-verification
        for prev_t, next_t in zip(tasks_out, tasks_out[1:]):
            u_prev = _to_utc_timestamps(pd.Index([prev_t["rolling_meta"]["active_until"]]))[0]
            f_next = _to_utc_timestamps(pd.Index([next_t["rolling_meta"]["active_from"]]))[0]
            if u_prev > f_next:
                raise FitLeakageError(f"Overlapping rolling OOS intervals: {u_prev} > {f_next}")
        return tasks_out


@dataclass(frozen=True)
class RollingRunResult:
    """Complete output of RollingTrainer across disjoint OOS windows."""

    experiment_name: str
    train_mode: str
    frozen_specs: tuple[FrozenModelSpec, ...]
    recorder_ids: tuple[str, ...]
    rolling_metas: tuple[dict[str, Any], ...]
    oos_predictions: pd.Series
    oos_probabilities: pd.DataFrame | None
    lineage_chain: tuple[tuple[str | None, str], ...]

    def to_summary_dict(self) -> dict[str, Any]:
        return {
            "schema": "tradegen-qlib-rolling-summary-v1",
            "experiment_name": self.experiment_name,
            "train_mode": self.train_mode,
            "n_windows": len(self.frozen_specs),
            "recorder_ids": list(self.recorder_ids),
            "rolling_metas": list(self.rolling_metas),
            "lineage_chain": [{"parent_sha256": p, "model_sha256": c} for p, c in self.lineage_chain],
            "n_oos_predictions": int(len(self.oos_predictions)),
            "research_flags": dict(RESEARCH_FLAGS),
            **RESEARCH_FLAGS,
        }


class RollingTrainer:
    """Executes RollingGen tasks with strict per-window processor rebinding and ModelFT finetune lineage."""

    def __init__(
        self,
        *,
        uri: Path | str,
        experiment_name: str = "rolling_factory",
        train_mode: str = "retrain",
        model_name_prefix: str = "rolling-model",
        run_utc: str = DEFAULT_PINNED_UTC,
    ) -> None:
        if train_mode not in ("retrain", "finetune"):
            raise ValueError("train_mode must be 'retrain' or 'finetune'")
        self.uri = Path(uri)
        self.experiment_name = str(experiment_name)
        self.train_mode = train_mode
        self.model_name_prefix = str(model_name_prefix)
        self.run_utc = str(run_utc)

    def run(
        self,
        rolling_tasks: Sequence[Mapping[str, Any]],
        *,
        shared_handler: DataHandlerLP | None = None,
        finetune_kwargs: Mapping[str, Any] | None = None,
    ) -> RollingRunResult:
        if not rolling_tasks:
            raise ValueError("rolling_tasks must be non-empty")

        specs: list[FrozenModelSpec] = []
        rec_ids: list[str] = []
        metas: list[dict[str, Any]] = []
        pred_chunks: list[pd.Series] = []
        proba_chunks: list[pd.DataFrame] = []
        lineage: list[tuple[str | None, str]] = []

        prev_spec: FrozenModelSpec | None = None

        for k, raw_task in enumerate(rolling_tasks):
            task = deepcopy(dict(raw_task))
            meta = dict(task.get("rolling_meta") or {"window_index": k})
            fit_st = meta.get("fit_start_time") or task["dataset"]["kwargs"]["segments"]["train"][0]
            fit_et = meta.get("fit_end_time") or task["dataset"]["kwargs"]["segments"]["train"][1]

            if shared_handler is not None:
                # Rebind fit windows directly on the shared handler before DatasetH construction!
                shared_handler.rebind_processor_fit_windows(fit_st, fit_et)
                ds_kwargs = deepcopy(dict(task["dataset"].get("kwargs", {})))
                ds_kwargs["handler"] = shared_handler
                dataset: DatasetH = init_instance_by_config(
                    {"class": task["dataset"]["class"], "kwargs": ds_kwargs},
                    accept_types=DatasetH,
                )
            else:
                dataset = init_instance_by_config(task["dataset"], accept_types=DatasetH)
                if isinstance(dataset.handler, DataHandlerLP):
                    dataset.handler.rebind_processor_fit_windows(fit_st, fit_et)
                    dataset._validate_and_build_effective_segments()

            reweighter = None
            if "reweighter" in task and task["reweighter"] is not None:
                from qlib_lab.models.base import Reweighter
                reweighter = init_instance_by_config(task["reweighter"], accept_types=Reweighter)

            with R.start(
                experiment_name=self.experiment_name,
                recorder_name=f"window_{k:03d}",
                uri=self.uri,
                run_utc=self.run_utc,
            ) as rec:
                rec.log_params(train_mode=self.train_mode, **{**meta, "window_index": k})
                if self.train_mode == "finetune" and prev_spec is not None:
                    loaded_m = Model.from_frozen_spec(prev_spec)
                    if not isinstance(loaded_m, ModelFT):
                        raise TypeError(
                            f"train_mode='finetune' requires a ModelFT subclass, got {type(loaded_m).__name__}"
                        )
                    model: Model = loaded_m.finetune(dataset, reweighter=reweighter, **dict(finetune_kwargs or {}))
                else:
                    model = init_instance_by_config(task["model"], accept_types=Model)
                    model.fit(dataset, reweighter=reweighter)

                proc_states = (
                    dataset.handler.export_processor_states()
                    if isinstance(dataset.handler, DataHandlerLP)
                    else None
                )
                tc = dataset.effective_training_cutoff(include_valid="valid" in dataset.segments)
                active_from_ts = _to_utc_timestamps(
                    pd.Index([meta.get("active_from", dataset.segments["test"][0])])
                )[0]
                active_until_ts = _to_utc_timestamps(
                    pd.Index([meta.get("active_until", dataset.segments["test"][1])])
                )[0]
                active_from_ep = int(active_from_ts.value // 1_000_000_000)
                frozen_at = max(tc, active_from_ep - 1) if active_from_ep > tc else tc

                spec = model.to_frozen_spec(
                    model_name=self.model_name_prefix,
                    model_version=f"0.1.{k}",
                    training_cutoff=tc,
                    frozen_at=frozen_at,
                    processor_states=proc_states,
                )

                pred_k = model.predict(dataset, "test")
                dts_k = _to_utc_timestamps(pred_k.index.get_level_values("datetime"))
                if "active_from" in meta and "active_until" in meta:
                    in_window = (dts_k >= active_from_ts) & (dts_k < active_until_ts)
                    pred_k = pred_k.loc[in_window]
                pred_chunks.append(pred_k)

                if model.task_type == "direction":
                    proba_k = model.predict_proba(dataset, "test").reindex(pred_k.index)
                    proba_chunks.append(proba_k)
                    rec.save_objects(frozen_model=spec, oos_pred=pred_k, oos_proba=proba_k)
                else:
                    rec.save_objects(frozen_model=spec, oos_pred=pred_k)

                specs.append(spec)
                rec_ids.append(rec.id)
                metas.append(meta)
                lineage.append((spec.parent_model_sha256, spec.model_sha256))
                prev_spec = spec

        stitched_pred = pd.concat(pred_chunks, axis=0).sort_index() if pred_chunks else pd.Series(dtype=float)
        if stitched_pred.index.has_duplicates:
            raise FitLeakageError("Duplicate (datetime, instrument) OOS predictions detected across rolling windows")

        stitched_proba = pd.concat(proba_chunks, axis=0).sort_index() if proba_chunks else None
        return RollingRunResult(
            experiment_name=self.experiment_name,
            train_mode=self.train_mode,
            frozen_specs=tuple(specs),
            recorder_ids=tuple(rec_ids),
            rolling_metas=tuple(metas),
            oos_predictions=stitched_pred,
            oos_probabilities=stitched_proba,
            lineage_chain=tuple(lineage),
        )
