"""Purged horizon return & direction labels aligned bit-for-bit with direction_forecast_adapter.py."""
from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd

from qlib_lab.expression.ast_nodes import _epoch_seconds_array, _to_utc_timestamps
from qlib_lab.registry import register_component

DIRECTION_CLASSES: tuple[str, str, str] = ("up", "down", "neutral")
CLASS_TO_ID: dict[str, int] = {"up": 0, "down": 1, "neutral": 2}
ID_TO_CLASS: dict[int, str] = {0: "up", 1: "down", 2: "neutral"}


@register_component("label")
class PurgedHorizonReturnLabel:
    """Multi-horizon compounded return & ternary direction label matching BR-26 adapter rules.

    Outcome window for forecast at bar `t` (`as_of = bar[t].end`, with `lag_bars=0`) spans bars
    `t + 1 .. t + horizon_bars`, ending at `label_end_utc = bar[t + horizon_bars].end`.
    Uses `math.log1p(int(return_bps) / 10000)` + `math.fsum` when `return_bps` is present so
    outcomes near `+/- hurdle_bps` match `tools/research/direction_forecast_adapter.py` identically.
    """

    def __init__(
        self,
        horizon_bars: int = 2,
        hurdle_bps: int = 10,
        step_seconds: int = 3600,
        lag_bars: int = 0,
        return_bps_col: str = "return_bps",
        close_col: str = "close",
        enforce_contiguous_grid: bool = True,
    ) -> None:
        if isinstance(horizon_bars, bool) or not isinstance(horizon_bars, int) or horizon_bars < 1:
            raise ValueError(f"horizon_bars must be an integer >= 1, got {horizon_bars!r}")
        if isinstance(hurdle_bps, bool) or not isinstance(hurdle_bps, int) or not (0 <= hurdle_bps <= 9999):
            raise ValueError(f"hurdle_bps must be an integer in [0, 9999], got {hurdle_bps!r}")
        if isinstance(step_seconds, bool) or not isinstance(step_seconds, int) or step_seconds < 1:
            raise ValueError(f"step_seconds must be an integer >= 1, got {step_seconds!r}")
        if isinstance(lag_bars, bool) or not isinstance(lag_bars, int) or lag_bars < 0:
            raise ValueError(f"lag_bars must be an integer >= 0, got {lag_bars!r}")

        self.horizon_bars = int(horizon_bars)
        self.hurdle_bps = int(hurdle_bps)
        self.step_seconds = int(step_seconds)
        self.lag_bars = int(lag_bars)
        self.return_bps_col = str(return_bps_col)
        self.close_col = str(close_col)
        self.enforce_contiguous_grid = bool(enforce_contiguous_grid)

    @property
    def horizon_seconds(self) -> int:
        return self.horizon_bars * self.step_seconds

    def _find_col(self, df: pd.DataFrame, target: str) -> Any | None:
        candidates = (target, f"${target}", ("raw", target), ("raw", f"${target}"), ("feature", target), ("feature", f"${target}"))
        for cand in candidates:
            if cand in df.columns:
                return cand
        for col in df.columns:
            leaf = str(col[-1]) if isinstance(col, tuple) else str(col)
            if leaf in (target, f"${target}"):
                return col
        return None

    def compute(self, raw_panel: pd.DataFrame) -> pd.DataFrame:
        """Return DataFrame with ('label', ...) and ('meta', 'label_end_utc') columns."""
        if not isinstance(raw_panel.index, pd.MultiIndex) or raw_panel.index.nlevels != 2:
            raise ValueError("raw_panel must have MultiIndex(['datetime', 'instrument'])")
        panel = raw_panel if raw_panel.index.is_monotonic_increasing else raw_panel.sort_index()

        rbps_key = self._find_col(panel, self.return_bps_col)
        close_key = self._find_col(panel, self.close_col)
        if rbps_key is None and close_key is None:
            raise KeyError(
                f"PurgedHorizonReturnLabel requires either {self.return_bps_col!r} or {self.close_col!r} in panel"
            )

        up_bar = math.log1p(self.hurdle_bps / 10000.0)
        down_bar = math.log1p(-self.hurdle_bps / 10000.0)

        n_rows = len(panel)
        dir_cls = np.full(n_rows, np.nan, dtype=np.float64)
        realized_ret = np.full(n_rows, np.nan, dtype=np.float64)
        net_excess = np.full(n_rows, np.nan, dtype=np.float64)
        label_end_utc = np.full(n_rows, np.nan, dtype=np.float64)

        inst_level = panel.index.get_level_values("instrument")
        dt_level = panel.index.get_level_values("datetime")
        dt_utc = _to_utc_timestamps(dt_level)
        all_epochs = _epoch_seconds_array(dt_utc)

        rbps_all = panel[rbps_key].to_numpy(dtype=np.float64) if rbps_key is not None else None
        close_all = panel[close_key].to_numpy(dtype=np.float64) if close_key is not None else None

        # Process each instrument slice independently
        for inst in panel.index.get_level_values("instrument").unique():
            pos = np.flatnonzero(inst_level == inst)
            m = pos.size
            if m == 0:
                continue
            ep = all_epochs[pos]
            one_bar_log_ret = np.full(m, np.nan, dtype=np.float64)
            if rbps_all is not None:
                vals = rbps_all[pos]
                for k in range(m):
                    if math.isfinite(float(vals[k])) and vals[k] > -10000.0:
                        one_bar_log_ret[k] = math.log1p(int(round(float(vals[k]))) / 10000.0)
            else:
                assert close_all is not None
                px = close_all[pos]
                for k in range(1, m):
                    if math.isfinite(float(px[k])) and math.isfinite(float(px[k - 1])) and px[k] > 0 and px[k - 1] > 0:
                        one_bar_log_ret[k] = math.log(float(px[k]) / float(px[k - 1]))

            total_shift = self.horizon_bars + self.lag_bars
            expected_span = float(total_shift * self.step_seconds)

            for i in range(m):
                start = i + 1 + self.lag_bars
                stop = i + total_shift
                if stop >= m:
                    continue
                if self.enforce_contiguous_grid and abs((ep[stop] - ep[i]) - expected_span) > 1e-6:
                    continue
                win = one_bar_log_ret[start : stop + 1]
                if not np.all(np.isfinite(win)):
                    continue
                realized = math.fsum(float(v) for v in win)
                if realized > up_bar:
                    cid = 0.0
                elif realized < down_bar:
                    cid = 1.0
                else:
                    cid = 2.0

                row_idx = pos[i]
                dir_cls[row_idx] = cid
                realized_ret[row_idx] = realized
                net_excess[row_idx] = realized - up_bar
                label_end_utc[row_idx] = ep[stop]

        cols = pd.MultiIndex.from_tuples(
            [
                ("label", "direction_class"),
                ("label", "realized_log_return"),
                ("label", "net_excess_return"),
                ("meta", "label_end_utc"),
            ]
        )
        out = pd.DataFrame(
            np.column_stack([dir_cls, realized_ret, net_excess, label_end_utc]),
            index=panel.index,
            columns=cols,
        )
        return out.reindex(raw_panel.index) if not panel.index.equals(raw_panel.index) else out

    def to_config_dict(self) -> dict[str, Any]:
        return {
            "class": "PurgedHorizonReturnLabel",
            "kwargs": {
                "horizon_bars": self.horizon_bars,
                "hurdle_bps": self.hurdle_bps,
                "step_seconds": self.step_seconds,
                "lag_bars": self.lag_bars,
                "return_bps_col": self.return_bps_col,
                "close_col": self.close_col,
                "enforce_contiguous_grid": self.enforce_contiguous_grid,
            },
        }
