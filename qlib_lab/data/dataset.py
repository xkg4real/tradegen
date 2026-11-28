"""DatasetH, TSDatasetH & TSDataSampler with fit-leakage guard, outcome purging, embargo, and test-label lock."""
from __future__ import annotations

import bisect
from collections.abc import Mapping, Sequence
from contextlib import contextmanager
from copy import deepcopy
import threading
from typing import Any

import numpy as np
import pandas as pd

from qlib_lab.data.handler import DataHandler, DataHandlerLP
from qlib_lab.data.processors import StatefulProcessor
from qlib_lab.exceptions import FitLeakageError, LookAheadSyntaxError, TestLabelLeakageError
from qlib_lab.expression.ast_nodes import _epoch_seconds_array, _to_utc_timestamps
from qlib_lab.registry import init_instance_by_config, register_component

_EVAL_TLS = threading.local()


@contextmanager
def authorized_eval_context(caller: str = "evaluator"):
    """Context manager entered ONLY by authorized gate/signal evaluators to access test labels."""
    if not isinstance(caller, str) or not caller.strip():
        raise ValueError("authorized_eval_context requires a non-empty caller name")
    depth = getattr(_EVAL_TLS, "depth", 0)
    _EVAL_TLS.depth = depth + 1
    try:
        yield
    finally:
        _EVAL_TLS.depth = depth


def is_eval_authorized() -> bool:
    return int(getattr(_EVAL_TLS, "depth", 0)) > 0


def _np_ffill_1d(arr: np.ndarray) -> np.ndarray:
    out = arr.copy()
    mask = np.isnan(out)
    idx = np.where(~mask, np.arange(out.size), 0)
    np.maximum.accumulate(idx, out=idx)
    valid_after_first = ~np.all(mask)
    if valid_after_first:
        first_valid = int(np.flatnonzero(~mask)[0])
        out[first_valid:] = out[idx[first_valid:]]
    return out


class Dataset:
    """Base Dataset abstraction."""

    def __init__(self, **kwargs: Any) -> None:
        self.setup_data(**kwargs)

    def config(self, **kwargs: Any) -> None:
        for k, v in kwargs.items():
            setattr(self, k, v)

    def setup_data(self, **kwargs: Any) -> None:
        _ = kwargs

    def prepare(self, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedError


@register_component("dataset")
class DatasetH(Dataset):
    """Dataset with DataHandler enforcing:
    (a) StatefulProcessor fit_end_time <= train_end (FitLeakageError),
    (b) automatic outcome purging where meta.label_end_utc > segment_end,
    (c) embargo_bars separation between train, valid, and test splits,
    (d) TestLabelLeakageError when test segment is requested with DK_L or label columns outside authorized_eval_context.
    """

    def __init__(
        self,
        handler: DataHandler | Mapping[str, Any],
        segments: Mapping[str, tuple[Any, Any] | list[Any]],
        embargo_bars: int = 0,
        fetch_kwargs: Mapping[str, Any] | None = None,
        purge_outcomes: bool = True,
        **kwargs: Any,
    ) -> None:
        if embargo_bars < 0:
            raise ValueError(f"embargo_bars must be >= 0, got {embargo_bars}")
        self.handler: DataHandler = init_instance_by_config(handler, accept_types=DataHandler)
        self.raw_segments: dict[str, tuple[pd.Timestamp, pd.Timestamp]] = {}
        for k, seg in segments.items():
            if not isinstance(seg, (tuple, list)) or len(seg) != 2:
                raise ValueError(f"Segment {k!r} must be a (start, end) pair, got {seg!r}")
            st = _to_utc_timestamps(pd.Index([seg[0]]))[0]
            et = _to_utc_timestamps(pd.Index([seg[1]]))[0]
            if st > et:
                raise ValueError(f"Segment {k!r} has start ({st}) > end ({et})")
            self.raw_segments[str(k)] = (st, et)

        self.embargo_bars = int(embargo_bars)
        self.purge_outcomes = bool(purge_outcomes)
        self.fetch_kwargs = dict(fetch_kwargs or {})
        self.segments: dict[str, tuple[pd.Timestamp, pd.Timestamp]] = {}
        super().__init__(**kwargs)

    def setup_data(self, handler_kwargs: Mapping[str, Any] | None = None, **kwargs: Any) -> None:
        super().setup_data(**kwargs)
        if handler_kwargs is not None:
            self.handler.setup_data(**handler_kwargs)
        self._validate_and_build_effective_segments()

    def _calendar(self) -> list[pd.Timestamp]:
        base_key = DataHandler.DK_I if isinstance(self.handler, DataHandlerLP) else DataHandler.DK_R
        df = self.handler.fetch(col_set=DataHandler.CS_RAW, data_key=base_key)
        if df.empty and not getattr(self.handler, "_data", pd.DataFrame()).empty:
            df = self.handler.fetch(col_set=DataHandler.CS_RAW, data_key=DataHandler.DK_R)
        dts = _to_utc_timestamps(df.index.get_level_values("datetime").unique())
        return sorted(dts.tolist())

    def _validate_and_build_effective_segments(self) -> None:
        segs = dict(self.raw_segments)
        # Verify chronological ordering of standard splits (train < valid < test)
        ordered_keys = [k for k in ("train", "valid", "test") if k in segs]
        for a, b in zip(ordered_keys, ordered_keys[1:]):
            if segs[a][1] >= segs[b][0]:
                raise FitLeakageError(
                    f"Segment {a!r} end ({segs[a][1]}) overlaps or touches {b!r} start ({segs[b][0]})"
                )

        # (c) Enforce embargo_bars gap between consecutive ordered segments by truncating prior segment tail
        cal = self._calendar()
        eff = dict(segs)
        if self.embargo_bars > 0 and cal:
            for prior_k, next_k in zip(ordered_keys, ordered_keys[1:]):
                next_start = eff[next_k][0]
                next_idx = bisect.bisect_left(cal, next_start)
                max_allowed_idx = next_idx - 1 - self.embargo_bars
                if max_allowed_idx < 0:
                    raise FitLeakageError(
                        f"Cannot satisfy embargo_bars={self.embargo_bars} before segment {next_k!r} starting at {next_start}"
                    )
                allowed_end = min(eff[prior_k][1], cal[max_allowed_idx])
                if allowed_end < eff[prior_k][0]:
                    raise FitLeakageError(
                        f"Segment {prior_k!r} becomes empty after applying embargo_bars={self.embargo_bars}"
                    )
                eff[prior_k] = (eff[prior_k][0], allowed_end)

        if "train" in eff and isinstance(self.handler, DataHandlerLP):
            train_start, train_end = eff["train"]
            for proc in self.handler.get_all_processors():
                if isinstance(proc, StatefulProcessor) and (
                    proc.fit_start_time < train_start or proc.fit_end_time > train_end
                ):
                    raise FitLeakageError(
                        f"{type(proc).__name__} fit window lies outside the effective train segment"
                    )
        self.segments = eff

    def _overlaps_test(self, slc: Any, level: Any) -> bool:
        if "test" not in self.segments:
            return False
        test_start, test_end = self.segments["test"]
        if level not in ("datetime", 0):
            # An instrument selection spans the entire calendar.
            return True
        if isinstance(slc, slice):
            s0 = _to_utc_timestamps(pd.Index([slc.start]))[0] if slc.start is not None else pd.Timestamp.min.tz_localize("UTC")
            s1 = _to_utc_timestamps(pd.Index([slc.stop]))[0] if slc.stop is not None else pd.Timestamp.max.tz_localize("UTC")
            return s0 <= test_end and test_start <= s1
        if isinstance(slc, (tuple, list)) and len(slc) == 2 and level == "datetime":
            s0 = _to_utc_timestamps(pd.Index([slc[0]]))[0]
            s1 = _to_utc_timestamps(pd.Index([slc[1]]))[0]
            return s0 <= test_end and test_start <= s1
        targets = slc if isinstance(slc, (list, tuple, pd.Index, np.ndarray)) else [slc]
        dates = _to_utc_timestamps(pd.Index(targets))
        return bool(((dates >= test_start) & (dates <= test_end)).any())

    def _guard_test_leakage(self, slc: Any, col_set: Any, data_key: str, fetch_options: Mapping[str, Any]) -> Any:
        touches_test = self._overlaps_test(slc, fetch_options.get("level", "datetime"))
        if not touches_test or is_eval_authorized():
            return col_set

        if fetch_options.get("proc_func") is not None:
            # Handler callbacks see the full frame before column projection.
            raise TestLabelLeakageError("Raw processing callbacks cannot run on held-out rows")
        if data_key == DataHandlerLP.DK_L:
            raise TestLabelLeakageError(
                "prepare('test', data_key=DK_L) is forbidden outside authorized_eval_context"
            )
        if col_set == "label" or (isinstance(col_set, (list, tuple)) and "label" in col_set):
            raise TestLabelLeakageError(
                "Requesting 'label' columns on 'test' segment is forbidden outside authorized_eval_context"
            )
        # If CS_ALL or CS_RAW was requested on test with DK_I, strip label columns so labels never leak!
        if col_set in (DataHandler.CS_ALL, DataHandler.CS_RAW):
            raw_cols = self.handler.get_cols(col_set=DataHandler.CS_RAW, data_key=data_key) if isinstance(self.handler, DataHandlerLP) else self.handler.get_cols(col_set=DataHandler.CS_RAW)
            has_label = any(isinstance(c, tuple) and c[0] == "label" for c in raw_cols)
            if has_label:
                if col_set == DataHandler.CS_ALL:
                    return "feature"
                raise TestLabelLeakageError(
                    "Fetching CS_RAW containing labels on 'test' segment is forbidden outside authorized_eval_context"
                )
        return col_set

    def _purge_segment_df(
        self,
        df: pd.DataFrame,
        seg_name: str | None,
        seg_bounds: tuple[pd.Timestamp, pd.Timestamp],
        data_key: str,
    ) -> pd.DataFrame:
        """Purge rows whose outcome window (meta.label_end_utc) extends past seg_bounds[1]."""
        if df.empty or not self.purge_outcomes:
            return df
        # Apply purging on train / valid (and any non-test segment, or whenever DK_L is prepared on non-test)
        if seg_name == "test" and data_key != DataHandlerLP.DK_L:
            return df

        boundary_epoch = float(seg_bounds[1].value // 1_000_000_000)
        # Fetch meta.label_end_utc from handler on matching index
        src_key = data_key if isinstance(self.handler, DataHandlerLP) else DataHandler.DK_R
        raw_full = self.handler.fetch(selector=slice(seg_bounds[0], seg_bounds[1]), col_set=DataHandler.CS_RAW, data_key=src_key)
        meta_col = ("meta", "label_end_utc")
        if meta_col not in raw_full.columns:
            return df

        clock_col = ("meta", "label_known_at") if ("meta", "label_known_at") in raw_full else meta_col
        end_utc_ser = raw_full[clock_col].reindex(df.index)
        end_epochs = end_utc_ser.to_numpy(dtype=np.float64)
        # Keep rows whose outcome ends at or before segment boundary!
        # On DK_L, a NaN label_end_utc means incomplete outcome -> also purge!
        if data_key == DataHandlerLP.DK_L:
            keep = np.isfinite(end_epochs) & (end_epochs <= boundary_epoch + 1e-6)
        else:
            keep = (~np.isfinite(end_epochs)) | (end_epochs <= boundary_epoch + 1e-6)
        return df.loc[keep]

    def _prepare_seg(
        self,
        slc: Any,
        *,
        seg_name: str | None = None,
        col_set: Any = DataHandler.CS_ALL,
        data_key: str = DataHandlerLP.DK_I,
        **kwargs: Any,
    ) -> Any:
        merged_kw = {**self.fetch_kwargs, **kwargs}
        safe_col_set = self._guard_test_leakage(slc, col_set, data_key, merged_kw)
        df = self.handler.fetch(slc, col_set=safe_col_set, data_key=data_key, **merged_kw)
        if seg_name is not None and seg_name in self.segments:
            df = self._purge_segment_df(df, seg_name, self.segments[seg_name], data_key)
        return df

    def prepare(
        self,
        segments: str | Sequence[str] | slice | pd.Index,
        col_set: Any = DataHandler.CS_ALL,
        data_key: str = DataHandlerLP.DK_I,
        **kwargs: Any,
    ) -> pd.DataFrame | list[pd.DataFrame] | Any:
        if isinstance(segments, str) and segments in self.segments:
            st, et = self.segments[segments]
            return self._prepare_seg(slice(st, et), seg_name=segments, col_set=col_set, data_key=data_key, **kwargs)
        if isinstance(segments, (list, tuple)) and all(isinstance(s, str) and s in self.segments for s in segments):
            return [
                self._prepare_seg(
                    slice(self.segments[s][0], self.segments[s][1]),
                    seg_name=s,
                    col_set=col_set,
                    data_key=data_key,
                    **kwargs,
                )
                for s in segments
            ]
        return self._prepare_seg(segments, seg_name=None, col_set=col_set, data_key=data_key, **kwargs)

    def effective_training_cutoff(self, include_valid: bool = True) -> int:
        """Compute exact integer UTC epoch training_cutoff = max(label_end_utc) across purged train(/valid) rows."""
        target_segs = ["train"]
        if include_valid and "valid" in self.segments:
            target_segs.append("valid")

        max_ep: float | None = None
        for seg in target_segs:
            if seg not in self.segments:
                continue
            st, et = self.segments[seg]
            df = self.handler.fetch(
                slice(st, et),
                col_set=DataHandler.CS_RAW,
                data_key=DataHandlerLP.DK_L if isinstance(self.handler, DataHandlerLP) else DataHandler.DK_R,
            )
            df = self._purge_segment_df(df, seg, (st, et), DataHandlerLP.DK_L)
            if ("meta", "label_end_utc") in df.columns and not df.empty:
                clock_col = ("meta", "label_known_at") if ("meta", "label_known_at") in df else ("meta", "label_end_utc")
                vals = df[clock_col].to_numpy(dtype=np.float64)
                fin = vals[np.isfinite(vals)]
                if fin.size > 0:
                    cur = float(np.max(fin))
                    max_ep = cur if max_ep is None else max(max_ep, cur)
            elif not df.empty:
                dts = _epoch_seconds_array(_to_utc_timestamps(df.index.get_level_values("datetime")))
                cur = float(np.max(dts))
                max_ep = cur if max_ep is None else max(max_ep, cur)

        if max_ep is None:
            # Fallback to end of train/valid segment
            end_ts = self.segments["valid"][1] if (include_valid and "valid" in self.segments) else self.segments["train"][1]
            return int(end_ts.value // 1_000_000_000)
        return int(round(max_ep))


class TSDataSampler:
    """Causal time-series tensor sampler over MultiIndex(['datetime', 'instrument']).

    Refuses non-causal backfill ('bfill' / 'ffill+bfill') with LookAheadSyntaxError.
    """

    def __init__(
        self,
        data: pd.DataFrame,
        start: Any,
        end: Any,
        step_len: int,
        fillna_type: str = "none",
        dtype: Any = np.float64,
        flt_data: pd.Series | pd.DataFrame | None = None,
    ) -> None:
        if step_len < 1:
            raise ValueError(f"step_len must be >= 1, got {step_len}")
        if "bfill" in str(fillna_type).lower():
            raise LookAheadSyntaxError(
                f"fillna_type={fillna_type!r} uses backward fill (future look-ahead) and is forbidden"
            )
        if fillna_type not in ("none", "ffill"):
            raise ValueError(f"fillna_type must be 'none' or 'ffill', got {fillna_type!r}")

        self.start = _to_utc_timestamps(pd.Index([start]))[0]
        self.end = _to_utc_timestamps(pd.Index([end]))[0]
        self.step_len = int(step_len)
        self.fillna_type = fillna_type

        swapped = data.swaplevel(0, 1).sort_index()
        arr = np.asarray(swapped.to_numpy(), dtype=dtype)
        nan_row = np.full((1, arr.shape[1]), np.nan, dtype=arr.dtype)
        self.data_arr = np.vstack([arr, nan_row])
        self.nan_idx = len(self.data_arr) - 1

        self.idx_df, idx_map_dict = self._build_index(swapped)
        data_index = swapped.index.copy()

        if flt_data is not None:
            if isinstance(flt_data, pd.DataFrame):
                flt_ser = flt_data.iloc[:, 0]
            else:
                flt_ser = flt_data
            flt_swapped = flt_ser.astype(bool).swaplevel(0, 1).reindex(data_index, fill_value=False)
            keep_pos = np.flatnonzero(flt_swapped.to_numpy())
            new_map = {new_i: idx_map_dict[int(old_i)] for new_i, old_i in enumerate(keep_pos)}
            idx_map_dict = new_map
            data_index = data_index[keep_pos]

        if idx_map_dict:
            arr_map = np.array([idx_map_dict[i] for i in range(len(idx_map_dict))], dtype=np.int32)
            start_r = bisect.bisect_left(self.idx_df.index, self.start)
            end_r = bisect.bisect_right(self.idx_df.index, self.end)
            mask = (arr_map[:, 0] >= start_r) & (arr_map[:, 0] < end_r)
            self.idx_map = arr_map[mask]
            self.data_index = data_index[mask]
        else:
            self.idx_map = np.empty((0, 2), dtype=np.int32)
            self.data_index = data_index[:0]

        self.idx_arr = np.asarray(self.idx_df.to_numpy(), dtype=np.float64)

    @staticmethod
    def _build_index(swapped: pd.DataFrame) -> tuple[pd.DataFrame, dict[int, tuple[int, int]]]:
        if swapped.empty:
            return pd.DataFrame(), {}
        s = pd.Series(np.arange(len(swapped), dtype=np.float64), index=swapped.index)
        idx_df = s.unstack(level=0).sort_index().sort_index(axis=1)
        idx_map: dict[int, tuple[int, int]] = {}
        mat = idx_df.to_numpy(dtype=np.float64)
        for r in range(mat.shape[0]):
            for c in range(mat.shape[1]):
                val = mat[r, c]
                if not np.isnan(val):
                    idx_map[int(val)] = (r, c)
        return idx_df, idx_map

    def get_index(self) -> pd.MultiIndex:
        return self.data_index.swaplevel(0, 1)

    def __len__(self) -> int:
        return int(len(self.idx_map))

    def _get_row_col(self, idx: int | tuple[Any, str]) -> tuple[int, int]:
        if isinstance(idx, (int, np.integer)):
            ii = int(idx)
            if not (0 <= ii < len(self.idx_map)):
                raise IndexError(f"Index {ii} out of range [0, {len(self.idx_map)})")
            return int(self.idx_map[ii, 0]), int(self.idx_map[ii, 1])
        if isinstance(idx, tuple) and len(idx) == 2:
            dt_val, inst = idx
            ts = _to_utc_timestamps(pd.Index([dt_val]))[0]
            if (inst, ts) not in self.data_index:
                raise KeyError(f"Sample {idx!r} is outside the selected endpoints")
            r = bisect.bisect_left(self.idx_df.index, ts)
            c = bisect.bisect_left(list(self.idx_df.columns), str(inst))
            if r < 0 or c >= len(self.idx_df.columns) or str(self.idx_df.columns[c]) != str(inst):
                raise KeyError(f"Sample {idx!r} not found in TSDataSampler")
            return r, c
        raise TypeError(f"Unsupported TSDataSampler key {idx!r}")

    def _get_indices(self, row: int, col: int) -> np.ndarray:
        indices = self.idx_arr[max(row - self.step_len + 1, 0) : row + 1, col]
        if indices.size < self.step_len:
            indices = np.concatenate([np.full(self.step_len - indices.size, np.nan), indices])
        if self.fillna_type == "ffill":
            indices = _np_ffill_1d(indices)
        return np.nan_to_num(indices, nan=float(self.nan_idx)).astype(np.int64)

    def __getitem__(self, idx: int | tuple[Any, str] | Sequence[int] | np.ndarray) -> np.ndarray:
        if isinstance(idx, (list, np.ndarray)):
            if len(idx) == 0:
                return np.empty((0, self.step_len, self.data_arr.shape[1]), dtype=self.data_arr.dtype)
            all_idx = np.concatenate([self._get_indices(*self._get_row_col(int(i))) for i in idx])
            out = self.data_arr[all_idx]
            return out.reshape(len(idx), self.step_len, self.data_arr.shape[1])
        indices = self._get_indices(*self._get_row_col(idx))
        return self.data_arr[indices]


@register_component("dataset")
class TSDatasetH(DatasetH):
    """Time-Series DatasetH returning causal TSDataSampler windows while preserving all DatasetH guards."""

    DEFAULT_STEP_LEN = 30

    def __init__(
        self,
        handler: DataHandler | Mapping[str, Any],
        segments: Mapping[str, tuple[Any, Any] | list[Any]],
        step_len: int = DEFAULT_STEP_LEN,
        fillna_type: str = "none",
        flt_col: str | None = None,
        **kwargs: Any,
    ) -> None:
        if "bfill" in str(fillna_type).lower():
            raise LookAheadSyntaxError(f"fillna_type={fillna_type!r} is forbidden in TSDatasetH")
        self.step_len = int(step_len)
        self.fillna_type = fillna_type
        self.flt_col = flt_col
        super().__init__(handler=handler, segments=segments, **kwargs)

    def setup_data(self, handler_kwargs: Mapping[str, Any] | None = None, **kwargs: Any) -> None:
        super().setup_data(handler_kwargs=handler_kwargs, **kwargs)
        self.cal = self._calendar()

    def _extend_slice(self, slc: slice) -> slice:
        if not self.cal or slc.start is None:
            return slc
        st = _to_utc_timestamps(pd.Index([slc.start]))[0]
        idx = bisect.bisect_left(self.cal, st)
        pad_idx = max(0, idx - self.step_len + 1)
        return slice(self.cal[pad_idx], slc.stop)

    def _prepare_seg(
        self,
        slc: Any,
        *,
        seg_name: str | None = None,
        col_set: Any = DataHandler.CS_ALL,
        data_key: str = DataHandlerLP.DK_I,
        **kwargs: Any,
    ) -> TSDataSampler:
        dtype = kwargs.pop("dtype", np.float64)
        flt_col = kwargs.pop("flt_col", self.flt_col)
        if not isinstance(slc, slice):
            slc = slice(slc[0], slc[1])

        ext_slice = self._extend_slice(slc)
        fetch_options = {**self.fetch_kwargs, **kwargs}
        safe_col_set = self._guard_test_leakage(ext_slice, col_set, data_key, fetch_options)
        if flt_col is not None:
            self._guard_test_leakage(slc, flt_col, data_key, fetch_options)

        # Fetch extended historical feature lookback using DK_I so historical context rows aren't dropped by label filters,
        # while indexable targets are restricted to the purged segment rows!
        ext_data = self.handler.fetch(ext_slice, col_set=safe_col_set, data_key=data_key, **deepcopy(self.fetch_kwargs))
        target_df = super()._prepare_seg(slc, seg_name=seg_name, col_set=safe_col_set, data_key=data_key, **kwargs)

        # Build filter mask so ONLY purged rows in target_df are indexable sample endpoints,
        # while prior bars in ext_data remain available as causal historical lookback steps!
        valid_endpoints = pd.Series(True, index=target_df.index)
        if flt_col is not None:
            flt_raw = self.handler.fetch(slc, col_set=flt_col, data_key=data_key)
            flt_ser = flt_raw.iloc[:, 0] if isinstance(flt_raw, pd.DataFrame) else flt_raw
            valid_endpoints = valid_endpoints & flt_ser.reindex(target_df.index).fillna(False).astype(bool)

        return TSDataSampler(
            data=ext_data,
            start=slc.start,
            end=slc.stop,
            step_len=self.step_len,
            fillna_type=self.fillna_type,
            dtype=dtype,
            flt_data=valid_endpoints,
        )
