"""DataHandler & DataHandlerLP with DK_R / DK_I / DK_L and zero-pickle JSON state serialization."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
import json
from pathlib import Path
from typing import Any, Callable

import numpy as np
import pandas as pd

from core.isolation import checked_target
from qlib_lab import RESEARCH_FLAGS, canonical_sha256
from qlib_lab.data.loader import DataLoader, StaticDataLoader, ensure_grouped_columns, normalize_panel_index
from qlib_lab.data.processors import Processor, StatefulProcessor
from qlib_lab.expression.ast_nodes import _to_utc_timestamps
from qlib_lab.registry import init_instance_by_config, register_component


def fetch_df_by_col(df: pd.DataFrame, col_set: str | Sequence[str]) -> pd.DataFrame:
    if col_set == DataHandler.CS_RAW:
        return df
    if not isinstance(df.columns, pd.MultiIndex):
        return df
    if col_set == DataHandler.CS_ALL:
        out = df.copy()
        out.columns = out.columns.droplevel(0)
        return out
    if isinstance(col_set, str):
        if col_set not in df.columns.get_level_values(0):
            raise KeyError(f"Column group {col_set!r} not present in {list(df.columns.levels[0])}")
        return df[col_set]
    selected = [g for g in col_set if g in df.columns.get_level_values(0)]
    missing = [g for g in col_set if g not in selected]
    if missing:
        raise KeyError(f"Column group(s) {missing} not present")
    return df[list(col_set)]


def fetch_df_by_index(
    df: pd.DataFrame,
    selector: Any = slice(None, None),
    level: str | int | None = "datetime",
) -> pd.DataFrame:
    if isinstance(selector, (tuple, list)) and len(selector) == 2 and level == "datetime":
        selector = slice(selector[0], selector[1])

    if isinstance(selector, slice) and selector == slice(None, None):
        return df

    if level == "datetime" or level == 0:
        dts = _to_utc_timestamps(df.index.get_level_values("datetime"))
        if isinstance(selector, slice):
            mask = np.ones(len(df), dtype=bool)
            if selector.start is not None:
                st = _to_utc_timestamps(pd.Index([selector.start]))[0]
                mask &= dts >= st
            if selector.stop is not None:
                et = _to_utc_timestamps(pd.Index([selector.stop]))[0]
                mask &= dts <= et
            return df.loc[mask]
        if isinstance(selector, (pd.Index, np.ndarray, list, tuple)):
            targets = _to_utc_timestamps(pd.Index(selector))
            return df.loc[dts.isin(targets)]
        pt = _to_utc_timestamps(pd.Index([selector]))[0]
        return df.loc[dts == pt]

    if level == "instrument" or level == 1:
        insts = df.index.get_level_values("instrument")
        if isinstance(selector, str):
            return df.loc[insts == selector]
        return df.loc[insts.isin(list(selector))]

    return df.loc[selector]


@register_component("handler")
class DataHandler:
    """Base panel DataHandler maintaining sorted MultiIndex(['datetime', 'instrument'])."""

    CS_ALL = "__all"
    CS_RAW = "__raw"

    DK_R = "raw"
    DK_I = "infer"
    DK_L = "learn"

    def __init__(
        self,
        instruments: Sequence[str] | None = None,
        start_time: Any = None,
        end_time: Any = None,
        data_loader: DataLoader | Mapping[str, Any] | str | None = None,
        init_data: bool = True,
        fetch_orig: bool = True,
    ) -> None:
        if data_loader is None:
            raise ValueError("DataHandler requires a data_loader")
        self.data_loader: DataLoader = init_instance_by_config(data_loader, accept_types=DataLoader)
        self.instruments = list(instruments) if instruments is not None else None
        self.start_time = start_time
        self.end_time = end_time
        self.fetch_orig = bool(fetch_orig)
        self._data: pd.DataFrame = pd.DataFrame()
        if init_data:
            self.setup_data()

    def config(self, **kwargs: Any) -> None:
        for k in ("instruments", "start_time", "end_time", "fetch_orig"):
            if k in kwargs:
                setattr(self, k, kwargs[k])

    def setup_data(self, **kwargs: Any) -> None:
        _ = kwargs
        loaded = self.data_loader.load(self.instruments, self.start_time, self.end_time)
        self._data = ensure_grouped_columns(normalize_panel_index(loaded))

    def _fetch_data(
        self,
        data_storage: pd.DataFrame,
        selector: Any = slice(None, None),
        level: str | int | None = "datetime",
        col_set: str | Sequence[str] = CS_ALL,
        squeeze: bool = False,
        proc_func: Callable[[pd.DataFrame], pd.DataFrame] | None = None,
    ) -> pd.DataFrame:
        if proc_func is not None:
            sliced = fetch_df_by_index(data_storage, selector=selector, level=level).copy()
            processed = proc_func(sliced)
            out = fetch_df_by_col(processed, col_set)
        else:
            cols_df = fetch_df_by_col(data_storage, col_set)
            out = fetch_df_by_index(cols_df, selector=selector, level=level)
            if not self.fetch_orig:
                out = out.copy()
        if squeeze:
            out = out.squeeze()
        return out

    def fetch(
        self,
        selector: Any = slice(None, None),
        level: str | int | None = "datetime",
        col_set: str | Sequence[str] = CS_ALL,
        data_key: str = DK_I,
        squeeze: bool = False,
        proc_func: Callable[[pd.DataFrame], pd.DataFrame] | None = None,
    ) -> pd.DataFrame:
        _ = data_key
        return self._fetch_data(
            self._data, selector=selector, level=level, col_set=col_set, squeeze=squeeze, proc_func=proc_func
        )

    def get_cols(self, col_set: str | Sequence[str] = CS_ALL) -> list[Any]:
        return fetch_df_by_col(self._data.head(0), col_set).columns.to_list()


@register_component("handler")
class DataHandlerLP(DataHandler):
    """DataHandler with Learnable Processors (DK_R, DK_I, DK_L) and zero-pickle JSON state export."""

    ATTR_MAP = {DataHandler.DK_R: "_data", DataHandler.DK_I: "_infer", DataHandler.DK_L: "_learn"}

    PTYPE_I = "independent"
    PTYPE_A = "append"

    IT_FIT_SEQ = "fit_seq"
    IT_FIT_IND = "fit_ind"
    IT_LS = "load_state"

    def __init__(
        self,
        instruments: Sequence[str] | None = None,
        start_time: Any = None,
        end_time: Any = None,
        data_loader: DataLoader | Mapping[str, Any] | str | None = None,
        infer_processors: Sequence[Processor | Mapping[str, Any] | str] = (),
        learn_processors: Sequence[Processor | Mapping[str, Any] | str] = (),
        shared_processors: Sequence[Processor | Mapping[str, Any] | str] = (),
        process_type: str = PTYPE_A,
        drop_raw: bool = False,
        init_type: str = IT_FIT_SEQ,
        init_data: bool = True,
        **kwargs: Any,
    ) -> None:
        if process_type not in (self.PTYPE_A, self.PTYPE_I):
            raise ValueError(f"Unsupported process_type {process_type!r}")
        self.shared_processors: list[Processor] = [
            init_instance_by_config(p, accept_types=Processor) for p in shared_processors
        ]
        self.infer_processors: list[Processor] = [
            init_instance_by_config(p, accept_types=Processor) for p in infer_processors
        ]
        self.learn_processors: list[Processor] = [
            init_instance_by_config(p, accept_types=Processor) for p in learn_processors
        ]
        for proc in self.shared_processors + self.infer_processors:
            if not proc.is_for_infer():
                raise TypeError(
                    f"Processor {proc.__class__.__name__} has is_for_infer()=False and cannot be used in infer/shared chains"
                )
        self.process_type = process_type
        self.drop_raw = bool(drop_raw)
        self._init_type_default = init_type
        self._infer: pd.DataFrame = pd.DataFrame()
        self._learn: pd.DataFrame = pd.DataFrame()
        super().__init__(
            instruments=instruments,
            start_time=start_time,
            end_time=end_time,
            data_loader=data_loader,
            init_data=init_data,
            **kwargs,
        )

    def get_all_processors(self) -> list[Processor]:
        return self.shared_processors + self.infer_processors + self.learn_processors

    def rebind_processor_fit_windows(self, fit_start_time: Any, fit_end_time: Any) -> None:
        """Rebind all StatefulProcessors to [fit_start_time, fit_end_time] and re-run fit_process_data."""
        for proc in self.get_all_processors():
            if isinstance(proc, StatefulProcessor):
                proc.rebind_fit_window(fit_start_time, fit_end_time)
        if not self._data.empty:
            self.fit_process_data()

    @staticmethod
    def _run_proc_list(
        df: pd.DataFrame,
        procs: Sequence[Processor],
        *,
        with_fit: bool,
        check_for_infer: bool,
    ) -> pd.DataFrame:
        cur = df
        for proc in procs:
            if check_for_infer and not proc.is_for_infer():
                raise TypeError(f"Processor {proc.__class__.__name__} is not valid for inference")
            if with_fit:
                proc.fit(cur)
            cur = proc(cur)
        return cur

    def fit(self) -> None:
        for proc in self.get_all_processors():
            proc.fit(self._data)

    def fit_process_data(self) -> None:
        self.process_data(with_fit=True)

    def process_data(self, with_fit: bool = False) -> None:
        shared_df = self._data.copy() if self.shared_processors else self._data
        shared_df = self._run_proc_list(shared_df, self.shared_processors, with_fit=with_fit, check_for_infer=True)

        infer_df = shared_df.copy() if self.infer_processors else shared_df
        infer_df = self._run_proc_list(infer_df, self.infer_processors, with_fit=with_fit, check_for_infer=True)
        self._infer = infer_df

        if self.process_type == self.PTYPE_I:
            learn_base = shared_df
        else:
            learn_base = infer_df
        learn_df = learn_base.copy() if self.learn_processors else learn_base
        learn_df = self._run_proc_list(learn_df, self.learn_processors, with_fit=with_fit, check_for_infer=False)
        self._learn = learn_df

        if self.drop_raw:
            self._data = pd.DataFrame()

    def setup_data(self, init_type: str | None = None, **kwargs: Any) -> None:
        mode = init_type or self._init_type_default
        super().setup_data(**kwargs)
        if mode == self.IT_FIT_IND:
            self.fit()
            self.process_data(with_fit=False)
        elif mode == self.IT_LS:
            self.process_data(with_fit=False)
        elif mode == self.IT_FIT_SEQ:
            self.fit_process_data()
        else:
            raise ValueError(f"Unsupported init_type {mode!r}")

    def _get_df_by_key(self, data_key: str = DataHandler.DK_I) -> pd.DataFrame:
        if data_key not in self.ATTR_MAP:
            raise KeyError(f"Unknown data_key {data_key!r}; expected one of {tuple(self.ATTR_MAP)}")
        if data_key == self.DK_R and self.drop_raw:
            raise AttributeError("Raw data was dropped (drop_raw=True)")
        return getattr(self, self.ATTR_MAP[data_key])

    def fetch(
        self,
        selector: Any = slice(None, None),
        level: str | int | None = "datetime",
        col_set: str | Sequence[str] = DataHandler.CS_ALL,
        data_key: str = DataHandler.DK_I,
        squeeze: bool = False,
        proc_func: Callable[[pd.DataFrame], pd.DataFrame] | None = None,
    ) -> pd.DataFrame:
        return self._fetch_data(
            self._get_df_by_key(data_key),
            selector=selector,
            level=level,
            col_set=col_set,
            squeeze=squeeze,
            proc_func=proc_func,
        )

    def get_cols(self, col_set: str | Sequence[str] = DataHandler.CS_ALL, data_key: str = DataHandler.DK_I) -> list[Any]:
        return fetch_df_by_col(self._get_df_by_key(data_key).head(0), col_set).columns.to_list()

    def export_processor_states(self) -> dict[str, Any]:
        """Export all processor chains and fitted parameters to a canonical JSON-safe dict (zero pickle)."""
        body = {
            "schema": "tradegen-qlib-processor-states-v1",
            "process_type": self.process_type,
            "shared_processors": [p.to_state_dict() for p in self.shared_processors],
            "infer_processors": [p.to_state_dict() for p in self.infer_processors],
            "learn_processors": [p.to_state_dict() for p in self.learn_processors],
            "research_flags": dict(RESEARCH_FLAGS),
            **RESEARCH_FLAGS,
        }
        body["state_sha256"] = canonical_sha256(body)
        return body

    def save_processor_states(self, path: Path) -> Path:
        target = checked_target(path, "processor_states")
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = self.export_processor_states()
        raw = json.dumps(payload, sort_keys=True, ensure_ascii=True, indent=2, allow_nan=False) + "\n"
        target.write_bytes(raw.encode("ascii"))
        return target

    def load_processor_states(self, states_or_path: Mapping[str, Any] | Path, *, reprocess: bool = True) -> None:
        """Restore processor chains from JSON dict or file with SHA-256 verification."""
        if isinstance(states_or_path, Path) or isinstance(states_or_path, str):
            target = checked_target(Path(states_or_path), "processor_states")
            payload = json.loads(target.read_text(encoding="utf-8"))
        else:
            payload = dict(states_or_path)

        if payload.get("schema") != "tradegen-qlib-processor-states-v1":
            raise ValueError("Invalid processor state schema")
        expected_sha = payload.get("state_sha256")
        body = {k: v for k, v in payload.items() if k != "state_sha256"}
        if expected_sha != canonical_sha256(body):
            raise ValueError("Processor state SHA-256 mismatch")

        self.process_type = str(payload["process_type"])
        for attr in ("shared_processors", "infer_processors", "learn_processors"):
            restored: list[Processor] = []
            for item in payload.get(attr, []):
                proc = init_instance_by_config(
                    {"class": item["class"], "kwargs": item.get("kwargs", {})},
                    accept_types=Processor,
                )
                proc.load_state_dict(item)
                restored.append(proc)
            setattr(self, attr, restored)

        if reprocess and not self._data.empty:
            self.process_data(with_fit=False)

    @classmethod
    def from_df(
        cls,
        df: pd.DataFrame,
        *,
        infer_processors: Sequence[Any] = (),
        learn_processors: Sequence[Any] = (),
        shared_processors: Sequence[Any] = (),
        process_type: str = PTYPE_A,
    ) -> DataHandlerLP:
        loader = StaticDataLoader(df)
        return cls(
            data_loader=loader,
            infer_processors=infer_processors,
            learn_processors=learn_processors,
            shared_processors=shared_processors,
            process_type=process_type,
        )
