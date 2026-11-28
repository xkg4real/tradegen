"""AST/DAG nodes, LabelContext, causal lag enforcement, and CSE compiler for qlib_lab expressions."""
from __future__ import annotations

import abc
from contextlib import contextmanager
import threading
from typing import Any, Mapping, Sequence

import numpy as np
import pandas as pd

from qlib_lab.exceptions import CausalLagViolationError, LookAheadSyntaxError

_TLS = threading.local()


@contextmanager
def LabelContext():
    """Authorize forward-looking operators (e.g., Ref($close, -2)) strictly for label construction."""
    prev = getattr(_TLS, "in_label_context", False)
    _TLS.in_label_context = True
    try:
        yield
    finally:
        _TLS.in_label_context = prev


def in_label_context() -> bool:
    return bool(getattr(_TLS, "in_label_context", False))


def _to_utc_timestamps(idx: pd.Index) -> pd.DatetimeIndex:
    if isinstance(idx, pd.DatetimeIndex):
        if idx.tz is None:
            return idx.tz_localize("UTC")
        return idx.tz_convert("UTC")
    # Accept integer UTC epoch seconds, >=9-digit epoch strings (e.g. CLI --as-of), or ISO/YYYYMMDD strings
    if pd.api.types.is_integer_dtype(idx) or pd.api.types.is_float_dtype(idx):
        return pd.to_datetime(np.asarray(idx, dtype=np.int64), unit="s", utc=True)
    if len(idx) > 0 and all(isinstance(x, str) and len(x.strip()) >= 9 and x.strip().lstrip("-").isdigit() for x in idx):
        return pd.to_datetime(np.asarray([int(x.strip()) for x in idx], dtype=np.int64), unit="s", utc=True)
    parsed = pd.to_datetime(idx, utc=True)
    return pd.DatetimeIndex(parsed)


def _epoch_seconds_array(values: Any, default_dt_index: pd.DatetimeIndex | None = None) -> np.ndarray:
    arr = np.asarray(values)
    if np.issubdtype(arr.dtype, np.datetime64):
        ts = pd.DatetimeIndex(arr)
        if ts.tz is None:
            ts = ts.tz_localize("UTC")
        else:
            ts = ts.tz_convert("UTC")
        return (ts.asi8 // 1_000_000_000).astype(np.float64)
    if arr.dtype == object:
        out = np.full(arr.shape, np.nan, dtype=np.float64)
        flat = arr.ravel()
        out_flat = out.ravel()
        for i, v in enumerate(flat):
            if v is None or (isinstance(v, float) and np.isnan(v)):
                continue
            if isinstance(v, (int, float, np.integer, np.floating)):
                out_flat[i] = float(v)
            else:
                out_flat[i] = pd.Timestamp(v).tz_convert("UTC").timestamp() if pd.Timestamp(v).tzinfo else pd.Timestamp(v, tz="UTC").timestamp()
        return out
    return arr.astype(np.float64)


class EvalContext:
    """Panel evaluation context on MultiIndex(['datetime', 'instrument']) with causal known_at enforcement."""

    def __init__(
        self,
        panel: pd.DataFrame,
        *,
        pit_provider: Any = None,
        bar_lag: int = 0,
        on_lag_violation: str = "raise",
        known_at_col: str | tuple[str, str] | None = "known_at",
        is_label_eval: bool = False,
    ) -> None:
        if not isinstance(panel.index, pd.MultiIndex) or panel.index.nlevels != 2:
            raise ValueError("Panel must have a 2-level MultiIndex(['datetime', 'instrument'])")
        if list(panel.index.names) != ["datetime", "instrument"]:
            panel = panel.copy()
            panel.index = panel.index.set_names(["datetime", "instrument"])
        if not panel.index.is_monotonic_increasing:
            panel = panel.sort_index()

        if on_lag_violation not in ("raise", "nan"):
            raise ValueError(f"on_lag_violation must be 'raise' or 'nan', got {on_lag_violation!r}")
        if bar_lag < 0:
            raise LookAheadSyntaxError(f"bar_lag must be >= 0, got {bar_lag}")

        self.panel = panel
        self.pit_provider = pit_provider
        self.bar_lag = 0 if is_label_eval else int(bar_lag)
        self.on_lag_violation = on_lag_violation
        self.is_label_eval = bool(is_label_eval)

        raw_dts = panel.index.get_level_values("datetime").unique().sort_values()
        self.datetimes_raw = raw_dts
        self.datetimes_utc = _to_utc_timestamps(raw_dts)
        self.as_of_epochs = (self.datetimes_utc.asi8 // 1_000_000_000).astype(np.float64)
        self.instruments = sorted(panel.index.get_level_values("instrument").unique().tolist())

        self.T = len(self.datetimes_raw)
        self.N = len(self.instruments)
        self._full_grid = pd.MultiIndex.from_product(
            [self.datetimes_raw, self.instruments], names=["datetime", "instrument"]
        )
        self._col_map: dict[str, Any] = {}
        for col in panel.columns:
            if isinstance(col, tuple):
                # Map both "$close", "close", and group-qualified names
                leaf = str(col[-1])
                self._col_map.setdefault(leaf, col)
                if leaf.startswith("$"):
                    self._col_map.setdefault(leaf[1:], col)
                else:
                    self._col_map.setdefault("$" + leaf, col)
            else:
                s = str(col)
                self._col_map[s] = col
                if s.startswith("$"):
                    self._col_map.setdefault(s[1:], col)
                else:
                    self._col_map.setdefault("$" + s, col)

        self._raw_matrix_cache: dict[str, np.ndarray] = {}
        self.known_at_matrix: np.ndarray | None = None
        if known_at_col is not None and not self.is_label_eval:
            resolved_ka = None
            if known_at_col in panel.columns:
                resolved_ka = known_at_col
            elif isinstance(known_at_col, str) and known_at_col in self._col_map:
                resolved_ka = self._col_map[known_at_col]
            if resolved_ka is not None:
                s_ka = panel[resolved_ka].reindex(self._full_grid)
                self.known_at_matrix = _epoch_seconds_array(s_ka.to_numpy()).reshape(self.T, self.N)

    def has_late_backfills(self) -> tuple[bool, list[tuple[int, int]]]:
        """Identify (t, inst_idx) pairs where some bar s <= t - bar_lag has known_at[s, j] > as_of[t]."""
        if self.known_at_matrix is None or self.is_label_eval:
            return False, []
        ka = self.known_at_matrix
        lag = self.bar_lag
        late_cells: list[tuple[int, int]] = []
        for t in range(lag, self.T):
            cutoff = self.as_of_epochs[t]
            upto = t - lag + 1
            sub = ka[:upto, :]
            # A finite bar whose known_at > cutoff violates point-in-time visibility at t
            bad_mask = np.isfinite(sub) & (sub > cutoff)
            if np.any(bad_mask):
                for j in range(self.N):
                    if np.any(bad_mask[:, j]):
                        if self.on_lag_violation == "raise":
                            bad_s = int(np.flatnonzero(bad_mask[:, j])[0])
                            raise CausalLagViolationError(
                                f"Instrument {self.instruments[j]} bar at {self.datetimes_utc[bad_s]} "
                                f"has known_at={ka[bad_s, j]:.0f} > as_of={cutoff:.0f} "
                                f"(bar_lag={lag}); causal lag violated"
                            )
                        late_cells.append((t, j))
        return bool(late_cells), late_cells

    def get_raw_field_matrix(self, field_name: str) -> np.ndarray:
        """Return (T, N) float64 matrix aligned to (datetimes_raw, instruments) BEFORE bar_lag shifting."""
        clean = field_name[1:] if field_name.startswith("$") else field_name
        if clean in self._raw_matrix_cache:
            return self._raw_matrix_cache[clean]
        if clean not in self._col_map:
            raise KeyError(f"Field ${clean} not found in panel columns {list(self.panel.columns)}")
        col_key = self._col_map[clean]
        ser = self.panel[col_key].reindex(self._full_grid)
        mat = ser.to_numpy(dtype=np.float64, copy=True).reshape(self.T, self.N)
        self._raw_matrix_cache[clean] = mat
        return mat

    def get_causal_field_matrix(self, field_name: str) -> np.ndarray:
        """Return (T, N) float64 matrix with bar_lag applied and immediate known_at validation."""
        raw = self.get_raw_field_matrix(field_name)
        if self.is_label_eval:
            return raw.copy()

        # Trigger raise check if on_lag_violation == "raise"; when "nan", ExpressionDAG.evaluate
        # runs _recompute_late_backfill_cells per timestamp t so late bars become visible once known_at <= as_of[t].
        if self.known_at_matrix is not None and self.on_lag_violation == "raise":
            self.has_late_backfills()

        lag = self.bar_lag
        if lag == 0:
            return raw.copy()

        out = np.full_like(raw, np.nan)
        if lag < self.T:
            out[lag:] = raw[: self.T - lag]
        return out

    def to_series(self, mat: np.ndarray, name: str) -> pd.Series:
        """Convert (T, N) matrix back to panel-indexed pd.Series."""
        s = pd.Series(mat.reshape(-1), index=self._full_grid, name=name, dtype=np.float64)
        if len(self.panel.index) != len(self._full_grid) or not self.panel.index.equals(self._full_grid):
            s = s.reindex(self.panel.index)
        return s


class ExprNode(metaclass=abc.ABCMeta):
    """Immutable AST/DAG node in the qlib_lab formulaic alpha/feature engine."""

    is_cross_sectional: bool = False
    uses_bar_fields: bool = False

    @abc.abstractmethod
    def children(self) -> tuple[ExprNode, ...]:
        """Child expression nodes."""

    @abc.abstractmethod
    def canonical_key(self) -> str:
        """Structural identity string for Common Subexpression Elimination (CSE)."""

    def max_forward_bars(self) -> int:
        """Maximum forward reach in bars (> 0 means future peek, forbidden outside LabelContext)."""
        return max((c.max_forward_bars() for c in self.children()), default=0)

    def max_backward_bars(self) -> int:
        """Maximum historical lookback window in bars."""
        return max((c.max_backward_bars() for c in self.children()), default=0)

    def contains_cross_sectional(self) -> bool:
        return self.is_cross_sectional or any(c.contains_cross_sectional() for c in self.children())

    def contains_bar_fields(self) -> bool:
        return self.uses_bar_fields or any(c.contains_bar_fields() for c in self.children())

    @abc.abstractmethod
    def compute(self, child_values: Sequence[np.ndarray], ctx: EvalContext) -> np.ndarray:
        """Compute (T, N) float64 output from evaluated child (T, N) arrays."""

    def __repr__(self) -> str:
        return self.canonical_key()


class ConstantNode(ExprNode):
    def __init__(self, value: float) -> None:
        self.value = float(value)

    def children(self) -> tuple[ExprNode, ...]:
        return ()

    def canonical_key(self) -> str:
        return f"Const({self.value!r})"

    def compute(self, child_values: Sequence[np.ndarray], ctx: EvalContext) -> np.ndarray:
        _ = child_values
        return np.full((ctx.T, ctx.N), self.value, dtype=np.float64)


class FieldNode(ExprNode):
    """Bar-grid column reference ($close, $volume, $return_bps, etc.)."""

    uses_bar_fields = True

    def __init__(self, name: str) -> None:
        clean = name[1:] if name.startswith("$") else name
        if not clean:
            raise ValueError("Empty field name")
        self.name = clean

    def children(self) -> tuple[ExprNode, ...]:
        return ()

    def canonical_key(self) -> str:
        return f"Field(${self.name})"

    def compute(self, child_values: Sequence[np.ndarray], ctx: EvalContext) -> np.ndarray:
        _ = child_values
        return ctx.get_causal_field_matrix(self.name)


class PITSeriesRefNode(ExprNode):
    """Symbolic handle for $$series passed into bitemporal PIT operators."""

    def __init__(self, series_id: str) -> None:
        clean = series_id[2:] if series_id.startswith("$$") else series_id
        if not clean:
            raise ValueError("Empty PIT series id")
        self.series_id = clean

    def children(self) -> tuple[ExprNode, ...]:
        return ()

    def canonical_key(self) -> str:
        return f"PITRef($${self.series_id})"

    def compute(self, child_values: Sequence[np.ndarray], ctx: EvalContext) -> np.ndarray:
        # Bare $$series outside PIT(...) collapses via default PIT($$series)
        from qlib_lab.expression.pit_ops import evaluate_pit_collapse

        _ = child_values
        return evaluate_pit_collapse(self.series_id, ctx, period_offset=0)


class ExpressionDAG:
    """CSE-deduplicated topological execution DAG for a batch of named expressions."""

    def __init__(self, named_roots: Mapping[str, ExprNode]) -> None:
        self.named_roots: dict[str, ExprNode] = {}
        self._intern_pool: dict[str, ExprNode] = {}
        self.topo_order: list[ExprNode] = []
        self.last_eval_counts: dict[str, int] = {}

        for out_name, root in named_roots.items():
            self.named_roots[out_name] = self._intern(root)

        visited: set[str] = set()
        for root in self.named_roots.values():
            self._build_topo(root, visited)

    def _intern(self, node: ExprNode) -> ExprNode:
        # Rebuild children recursively so identical subtrees share the exact same ExprNode object
        orig_children = node.children()
        if orig_children:
            dedup_children = tuple(self._intern(c) for c in orig_children)
            if any(a is not b for a, b in zip(orig_children, dedup_children)):
                node = node._with_children(dedup_children) if hasattr(node, "_with_children") else node
        key = node.canonical_key()
        if key not in self._intern_pool:
            self._intern_pool[key] = node
        return self._intern_pool[key]

    def _build_topo(self, node: ExprNode, visited: set[str]) -> None:
        key = node.canonical_key()
        if key in visited:
            return
        visited.add(key)
        for child in node.children():
            self._build_topo(child, visited)
        self.topo_order.append(node)

    @property
    def unique_node_count(self) -> int:
        return len(self.topo_order)

    def evaluate(
        self,
        panel: pd.DataFrame,
        *,
        pit_provider: Any = None,
        bar_lag: int = 0,
        on_lag_violation: str = "raise",
        known_at_col: str | tuple[str, str] | None = "known_at",
        is_label_eval: bool = False,
    ) -> pd.DataFrame:
        ctx = EvalContext(
            panel,
            pit_provider=pit_provider,
            bar_lag=bar_lag,
            on_lag_violation=on_lag_violation,
            known_at_col=known_at_col,
            is_label_eval=is_label_eval,
        )
        memo: dict[str, np.ndarray] = {}
        self.last_eval_counts = {}

        for node in self.topo_order:
            key = node.canonical_key()
            c_vals = [memo[c.canonical_key()] for c in node.children()]
            memo[key] = node.compute(c_vals, ctx)
            self.last_eval_counts[key] = self.last_eval_counts.get(key, 0) + 1

        # Exact bitemporal fixup when on_lag_violation == "nan" and a prior bar was backfilled late
        has_late, late_cells = ctx.has_late_backfills()
        if has_late and not ctx.is_label_eval:
            self._recompute_late_backfill_cells(ctx, late_cells, memo)

        cols = {name: ctx.to_series(memo[root.canonical_key()], name) for name, root in self.named_roots.items()}
        return pd.DataFrame(cols, index=ctx.panel.index)

    def _recompute_late_backfill_cells(
        self,
        ctx: EvalContext,
        late_cells: list[tuple[int, int]],
        memo: dict[str, np.ndarray],
    ) -> None:
        """Re-evaluate affected (t, inst) points on causally masked prefix histories."""
        assert ctx.known_at_matrix is not None
        lag = ctx.bar_lag
        by_t: dict[int, set[int]] = {}
        for t, j in late_cells:
            by_t.setdefault(t, set()).add(j)

        for t, bad_insts in sorted(by_t.items()):
            cutoff = ctx.as_of_epochs[t]
            upto = t - lag + 1
            # Build a lightweight prefix view up to index t (or upto for raw fields)
            sub_memo: dict[str, np.ndarray] = {}
            for node in self.topo_order:
                key = node.canonical_key()
                if isinstance(node, FieldNode):
                    raw = ctx.get_raw_field_matrix(node.name)[:upto, :].copy()
                    ka_sub = ctx.known_at_matrix[:upto, :]
                    mask_unknown = np.isfinite(ka_sub) & (ka_sub > cutoff)
                    raw[mask_unknown] = np.nan
                    if lag == 0:
                        padded = raw
                    else:
                        padded = np.full((t + 1, ctx.N), np.nan, dtype=np.float64)
                        padded[lag : t + 1, :] = raw
                    sub_memo[key] = padded
                elif isinstance(node, ConstantNode):
                    sub_memo[key] = np.full((t + 1, ctx.N), node.value, dtype=np.float64)
                elif not node.contains_bar_fields():
                    sub_memo[key] = memo[key][: t + 1, :]
                else:
                    c_vals = [sub_memo[c.canonical_key()] for c in node.children()]
                    sub_ctx = _PrefixEvalView(ctx, t + 1)
                    sub_memo[key] = node.compute(c_vals, sub_ctx)  # type: ignore[arg-type]

            for root in self.named_roots.values():
                rkey = root.canonical_key()
                if root.contains_bar_fields():
                    if root.contains_cross_sectional():
                        memo[rkey][t, :] = sub_memo[rkey][t, :]
                    else:
                        for j in bad_insts:
                            memo[rkey][t, j] = sub_memo[rkey][t, j]


class _PrefixEvalView:
    """Lightweight prefix view of EvalContext for late-backfill point-in-time recomputation."""

    def __init__(self, parent: EvalContext, length: int) -> None:
        self.T = length
        self.N = parent.N
        self.pit_provider = parent.pit_provider
        self.datetimes_utc = parent.datetimes_utc[:length]
        self.as_of_epochs = parent.as_of_epochs[:length]
        self.instruments = parent.instruments
        self.is_label_eval = parent.is_label_eval

    def get_causal_field_matrix(self, field_name: str) -> np.ndarray:
        raise RuntimeError("FieldNode handled directly by _recompute_late_backfill_cells")
