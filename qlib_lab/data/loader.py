"""Causal DataLoaders (StaticDataLoader & ExpressionDataLoader) on MultiIndex(['datetime', 'instrument'])."""
from __future__ import annotations

import abc
from collections.abc import Mapping
from typing import Any

import numpy as np
import pandas as pd

from qlib_lab.data.labels import PurgedHorizonReturnLabel
from qlib_lab.expression.ast_nodes import LabelContext, _epoch_seconds_array, _to_utc_timestamps
from qlib_lab.expression.parser import compile_expressions
from qlib_lab.registry import init_instance_by_config, register_component


def normalize_panel_index(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize index to sorted MultiIndex(['datetime', 'instrument']) with UTC pd.Timestamp datetimes."""
    if not isinstance(df.index, pd.MultiIndex) or df.index.nlevels != 2:
        if "datetime" in df.columns and "instrument" in df.columns:
            df = df.set_index(["datetime", "instrument"])
        else:
            raise ValueError("DataFrame must have MultiIndex(['datetime', 'instrument'])")

    names = list(df.index.names)
    if names == ["instrument", "datetime"]:
        df = df.swaplevel(0, 1)
    elif names != ["datetime", "instrument"]:
        df = df.copy()
        df.index = df.index.set_names(["datetime", "instrument"])

    dts = _to_utc_timestamps(df.index.get_level_values(0))
    insts = df.index.get_level_values(1).astype(str)
    out = df.copy()
    out.index = pd.MultiIndex.from_arrays([dts, insts], names=["datetime", "instrument"])
    if not out.index.is_monotonic_increasing:
        out = out.sort_index()
    if out.index.has_duplicates:
        raise ValueError("Duplicate (datetime, instrument) keys refused in panel")
    return out


def ensure_grouped_columns(df: pd.DataFrame, default_group: str = "feature") -> pd.DataFrame:
    """Ensure 2-level MultiIndex columns (group, col_name)."""
    if isinstance(df.columns, pd.MultiIndex) and df.columns.nlevels == 2:
        return df
    tuples = []
    for c in df.columns:
        if isinstance(c, tuple) and len(c) == 2:
            tuples.append((str(c[0]), str(c[1])))
        else:
            tuples.append((default_group, str(c)))
    out = df.copy()
    out.columns = pd.MultiIndex.from_tuples(tuples)
    return out


def filter_panel_slice(
    df: pd.DataFrame,
    instruments: list[str] | tuple[str, ...] | None = None,
    start_time: Any = None,
    end_time: Any = None,
) -> pd.DataFrame:
    out = df
    if instruments is not None:
        inst_set = {str(x) for x in instruments}
        mask = out.index.get_level_values("instrument").isin(inst_set)
        out = out.loc[mask]
    if start_time is not None or end_time is not None:
        dts = out.index.get_level_values("datetime")
        mask = np.ones(len(out), dtype=bool)
        if start_time is not None:
            st = _to_utc_timestamps(pd.Index([start_time]))[0]
            mask &= dts >= st
        if end_time is not None:
            et = _to_utc_timestamps(pd.Index([end_time]))[0]
            mask &= dts <= et
        out = out.loc[mask]
    return out


class DataLoader(metaclass=abc.ABCMeta):
    """Abstract base class for loading MultiIndex(['datetime', 'instrument']) panels."""

    @abc.abstractmethod
    def load(
        self,
        instruments: list[str] | tuple[str, ...] | None = None,
        start_time: Any = None,
        end_time: Any = None,
    ) -> pd.DataFrame:
        """Load panel data within optional instrument and [start_time, end_time] bounds."""


@register_component("loader")
class StaticDataLoader(DataLoader):
    """In-memory DataFrame loader (zero pickle)."""

    def __init__(self, df: pd.DataFrame, default_group: str = "feature") -> None:
        if not isinstance(df, pd.DataFrame):
            raise TypeError(f"StaticDataLoader expects a pandas DataFrame, got {type(df).__name__}")
        norm = normalize_panel_index(df)
        self._df = ensure_grouped_columns(norm, default_group=default_group)

    def load(
        self,
        instruments: list[str] | tuple[str, ...] | None = None,
        start_time: Any = None,
        end_time: Any = None,
    ) -> pd.DataFrame:
        return filter_panel_slice(self._df, instruments=instruments, start_time=start_time, end_time=end_time).copy()


@register_component("loader")
class ExpressionDataLoader(DataLoader):
    """Formulaic alpha/feature + purged label DataLoader backed by CSE ExpressionDAG and PIT engine."""

    def __init__(
        self,
        raw_data: pd.DataFrame | DataLoader | Mapping[str, Any],
        feature_expressions: Mapping[str, str],
        label_config: PurgedHorizonReturnLabel | Mapping[str, Any] | None = None,
        label_expressions: Mapping[str, str] | None = None,
        pit_provider: Any = None,
        bar_lag: int = 0,
        on_lag_violation: str = "raise",
        known_at_col: str | None = "known_at",
    ) -> None:
        if isinstance(raw_data, pd.DataFrame):
            self._raw_panel = normalize_panel_index(raw_data)
            self._raw_loader = None
        else:
            self._raw_panel = None
            self._raw_loader = init_instance_by_config(raw_data, accept_types=DataLoader)

        if not feature_expressions:
            raise ValueError("ExpressionDataLoader requires at least one feature expression")
        self.feature_expressions = dict(feature_expressions)
        # Compile eagerly so LookAheadSyntaxError fires immediately at construction time!
        self.feature_dag = compile_expressions(self.feature_expressions)

        self.label_builder: PurgedHorizonReturnLabel | None = None
        if label_config is not None:
            if isinstance(label_config, PurgedHorizonReturnLabel):
                self.label_builder = label_config
            else:
                self.label_builder = init_instance_by_config(label_config, accept_types=PurgedHorizonReturnLabel)

        self.label_expressions = dict(label_expressions) if label_expressions else None
        self.label_dag = None
        if self.label_expressions is not None:
            with LabelContext():
                self.label_dag = compile_expressions(self.label_expressions)

        self.pit_provider = pit_provider
        self.bar_lag = int(bar_lag)
        self.on_lag_violation = on_lag_violation
        self.known_at_col = known_at_col

    def load(
        self,
        instruments: list[str] | tuple[str, ...] | None = None,
        start_time: Any = None,
        end_time: Any = None,
    ) -> pd.DataFrame:
        if self._raw_panel is not None:
            # Evaluate on full history first so rolling lookbacks before start_time are warm,
            # while labels beyond end_time are still purged by DatasetH via label_end_utc!
            base = filter_panel_slice(self._raw_panel, instruments=instruments)
        else:
            assert self._raw_loader is not None
            base = normalize_panel_index(self._raw_loader.load(instruments=instruments))

        feat_df = self.feature_dag.evaluate(
            base,
            pit_provider=self.pit_provider,
            bar_lag=self.bar_lag,
            on_lag_violation=self.on_lag_violation,
            known_at_col=self.known_at_col,
            is_label_eval=False,
        )
        feat_df.columns = pd.MultiIndex.from_tuples([("feature", str(c)) for c in feat_df.columns])
        parts = [feat_df]

        if self.label_builder is not None:
            lbl_df = self.label_builder.compute(base)
            parts.append(lbl_df)
        elif self.label_dag is not None:
            lbl_raw = self.label_dag.evaluate(
                base,
                pit_provider=self.pit_provider,
                bar_lag=0,
                on_lag_violation="raise",
                known_at_col=None,
                is_label_eval=True,
            )
            max_fwd = max((r.max_forward_bars() for r in self.label_dag.named_roots.values()), default=0)
            lbl_raw.columns = pd.MultiIndex.from_tuples([("label", str(c)) for c in lbl_raw.columns])
            parts.append(lbl_raw)
            # Stamp meta.label_end_utc from forward shift reach on each instrument's bar grid
            dts_utc = _to_utc_timestamps(base.index.get_level_values("datetime"))
            ep_all = _epoch_seconds_array(dts_utc)
            inst_all = base.index.get_level_values("instrument")
            end_ep = np.full(len(base), np.nan, dtype=np.float64)
            for inst in inst_all.unique():
                pos = np.flatnonzero(inst_all == inst)
                m = pos.size
                if max_fwd == 0:
                    end_ep[pos] = ep_all[pos]
                elif max_fwd < m:
                    end_ep[pos[: m - max_fwd]] = ep_all[pos[max_fwd:]]
            meta_df = pd.DataFrame(
                end_ep,
                index=base.index,
                columns=pd.MultiIndex.from_tuples([("meta", "label_end_utc")]),
            )
            parts.append(meta_df)

        # Attach as_of_epoch in meta for downstream exporter / closed-window checks
        as_of_ep = _epoch_seconds_array(_to_utc_timestamps(base.index.get_level_values("datetime")))
        meta_as_of = pd.DataFrame(
            as_of_ep,
            index=base.index,
            columns=pd.MultiIndex.from_tuples([("meta", "as_of_utc")]),
        )
        parts.append(meta_as_of)

        combined = pd.concat(parts, axis=1)
        return filter_panel_slice(combined, instruments=None, start_time=start_time, end_time=end_time)
