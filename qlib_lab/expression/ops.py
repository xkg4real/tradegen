"""Full Qlib-compatible causal operator library backed by C++17 _accel kernels."""
from __future__ import annotations

from typing import Sequence

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view

from qlib_lab import _accel
from qlib_lab.exceptions import LookAheadSyntaxError
from qlib_lab.expression.ast_nodes import EvalContext, ExprNode, FieldNode, in_label_context


class OperatorNode(ExprNode):
    """Base operator node supporting CSE child reconstruction."""

    op_name: str = "Op"

    def __init__(self, children: Sequence[ExprNode], params: tuple = ()) -> None:
        self._children = tuple(children)
        self._params = tuple(params)

    def children(self) -> tuple[ExprNode, ...]:
        return self._children

    def _with_children(self, new_children: tuple[ExprNode, ...]) -> OperatorNode:
        clone = object.__new__(self.__class__)
        clone.__dict__.update(self.__dict__)
        clone._children = new_children
        return clone

    def canonical_key(self) -> str:
        c_str = ",".join(c.canonical_key() for c in self._children)
        p_str = ",".join(repr(p) for p in self._params)
        if c_str and p_str:
            return f"{self.op_name}({c_str},{p_str})"
        return f"{self.op_name}({c_str or p_str})"


def _validate_positive_window(d: int, op_name: str) -> int:
    if isinstance(d, bool) or not isinstance(d, int) or d < 1:
        if isinstance(d, (int, float)) and d <= 0:
            raise LookAheadSyntaxError(f"{op_name} window must be >= 1, got {d}")
        raise ValueError(f"{op_name} window must be an integer >= 1, got {d!r}")
    return int(d)


# --------------------------------------------------------------------------- #
# Elementwise Arithmetic, Logical, and Nonlinear Operators
# --------------------------------------------------------------------------- #
class Neg(OperatorNode):
    op_name = "Neg"

    def __init__(self, a: ExprNode) -> None:
        super().__init__((a,))

    def compute(self, child_values: Sequence[np.ndarray], ctx: EvalContext) -> np.ndarray:
        _ = ctx
        return -child_values[0]


class Add(OperatorNode):
    op_name = "Add"

    def __init__(self, a: ExprNode, b: ExprNode) -> None:
        super().__init__((a, b))

    def compute(self, child_values: Sequence[np.ndarray], ctx: EvalContext) -> np.ndarray:
        _ = ctx
        return child_values[0] + child_values[1]


class Sub(OperatorNode):
    op_name = "Sub"

    def __init__(self, a: ExprNode, b: ExprNode) -> None:
        super().__init__((a, b))

    def compute(self, child_values: Sequence[np.ndarray], ctx: EvalContext) -> np.ndarray:
        _ = ctx
        return child_values[0] - child_values[1]


class Mul(OperatorNode):
    op_name = "Mul"

    def __init__(self, a: ExprNode, b: ExprNode) -> None:
        super().__init__((a, b))

    def compute(self, child_values: Sequence[np.ndarray], ctx: EvalContext) -> np.ndarray:
        _ = ctx
        return child_values[0] * child_values[1]


class Div(OperatorNode):
    op_name = "Div"

    def __init__(self, a: ExprNode, b: ExprNode) -> None:
        super().__init__((a, b))

    def compute(self, child_values: Sequence[np.ndarray], ctx: EvalContext) -> np.ndarray:
        _ = ctx
        num, den = child_values[0], child_values[1]
        with np.errstate(divide="ignore", invalid="ignore"):
            out = np.where(np.abs(den) > 1e-30, num / den, np.nan)
        return out


class Log(OperatorNode):
    op_name = "Log"

    def __init__(self, a: ExprNode) -> None:
        super().__init__((a,))

    def compute(self, child_values: Sequence[np.ndarray], ctx: EvalContext) -> np.ndarray:
        _ = ctx
        x = child_values[0]
        with np.errstate(divide="ignore", invalid="ignore"):
            return np.where(x > 0.0, np.log(x), np.nan)


class Abs(OperatorNode):
    op_name = "Abs"

    def __init__(self, a: ExprNode) -> None:
        super().__init__((a,))

    def compute(self, child_values: Sequence[np.ndarray], ctx: EvalContext) -> np.ndarray:
        _ = ctx
        return np.abs(child_values[0])


class Sign(OperatorNode):
    op_name = "Sign"

    def __init__(self, a: ExprNode) -> None:
        super().__init__((a,))

    def compute(self, child_values: Sequence[np.ndarray], ctx: EvalContext) -> np.ndarray:
        _ = ctx
        x = child_values[0]
        with np.errstate(invalid="ignore"):
            return np.sign(x)


class Clip(OperatorNode):
    op_name = "Clip"

    def __init__(self, a: ExprNode, lo: float, hi: float) -> None:
        if float(lo) > float(hi):
            raise ValueError(f"Clip lower bound {lo} > upper bound {hi}")
        self.lo = float(lo)
        self.hi = float(hi)
        super().__init__((a,), (self.lo, self.hi))

    def compute(self, child_values: Sequence[np.ndarray], ctx: EvalContext) -> np.ndarray:
        _ = ctx
        return np.clip(child_values[0], self.lo, self.hi)


class If(OperatorNode):
    op_name = "If"

    def __init__(self, cond: ExprNode, true_val: ExprNode, false_val: ExprNode) -> None:
        super().__init__((cond, true_val, false_val))

    def compute(self, child_values: Sequence[np.ndarray], ctx: EvalContext) -> np.ndarray:
        _ = ctx
        c, t_val, f_val = child_values
        out = np.where(c > 0.0, t_val, f_val)
        return np.where(np.isfinite(c), out, np.nan)


class _CmpOp(OperatorNode):
    def __init__(self, a: ExprNode, b: ExprNode) -> None:
        super().__init__((a, b))

    def _cmp(self, a: np.ndarray, b: np.ndarray) -> np.ndarray:
        raise NotImplementedError

    def compute(self, child_values: Sequence[np.ndarray], ctx: EvalContext) -> np.ndarray:
        _ = ctx
        a, b = child_values
        valid = np.isfinite(a) & np.isfinite(b)
        with np.errstate(invalid="ignore"):
            res = self._cmp(a, b).astype(np.float64)
        return np.where(valid, res, np.nan)


class Gt(_CmpOp):
    op_name = "Gt"
    def _cmp(self, a: np.ndarray, b: np.ndarray) -> np.ndarray: return a > b


class Ge(_CmpOp):
    op_name = "Ge"
    def _cmp(self, a: np.ndarray, b: np.ndarray) -> np.ndarray: return a >= b


class Lt(_CmpOp):
    op_name = "Lt"
    def _cmp(self, a: np.ndarray, b: np.ndarray) -> np.ndarray: return a < b


class Le(_CmpOp):
    op_name = "Le"
    def _cmp(self, a: np.ndarray, b: np.ndarray) -> np.ndarray: return a <= b


class Eq(_CmpOp):
    op_name = "Eq"
    def _cmp(self, a: np.ndarray, b: np.ndarray) -> np.ndarray: return np.isclose(a, b, rtol=0.0, atol=1e-12)


class Ne(_CmpOp):
    op_name = "Ne"
    def _cmp(self, a: np.ndarray, b: np.ndarray) -> np.ndarray: return ~np.isclose(a, b, rtol=0.0, atol=1e-12)


class And(OperatorNode):
    op_name = "And"
    def __init__(self, a: ExprNode, b: ExprNode) -> None: super().__init__((a, b))
    def compute(self, child_values: Sequence[np.ndarray], ctx: EvalContext) -> np.ndarray:
        _ = ctx
        a, b = child_values
        valid = np.isfinite(a) & np.isfinite(b)
        return np.where(valid, ((a > 0.0) & (b > 0.0)).astype(np.float64), np.nan)


class Or(OperatorNode):
    op_name = "Or"
    def __init__(self, a: ExprNode, b: ExprNode) -> None: super().__init__((a, b))
    def compute(self, child_values: Sequence[np.ndarray], ctx: EvalContext) -> np.ndarray:
        _ = ctx
        a, b = child_values
        valid = np.isfinite(a) & np.isfinite(b)
        return np.where(valid, ((a > 0.0) | (b > 0.0)).astype(np.float64), np.nan)


# --------------------------------------------------------------------------- #
# Shift & Difference Operators (Static Future-Shift Ban Enforced!)
# --------------------------------------------------------------------------- #
class Ref(OperatorNode):
    """Qlib Ref(x, d): d > 0 looks back d bars (t - d); d < 0 looks ahead |d| bars (LabelContext only)."""

    op_name = "Ref"

    def __init__(self, a: ExprNode, d: int) -> None:
        if isinstance(d, bool) or not isinstance(d, int):
            raise ValueError(f"Ref shift d must be an integer, got {d!r}")
        if d < 0 and not in_label_context():
            raise LookAheadSyntaxError(
                f"Ref(..., {d}) shifts {abs(d)} bar(s) into the future; forbidden outside LabelContext"
            )
        self.d = int(d)
        super().__init__((a,), (self.d,))

    def max_forward_bars(self) -> int:
        child_fwd = super().max_forward_bars()
        return child_fwd + max(0, -self.d)

    def max_backward_bars(self) -> int:
        return super().max_backward_bars() + max(0, self.d)

    def compute(self, child_values: Sequence[np.ndarray], ctx: EvalContext) -> np.ndarray:
        _ = ctx
        x = child_values[0]
        T = x.shape[0]
        if self.d == 0:
            return x.copy()
        out = np.full_like(x, np.nan)
        if self.d > 0:
            if self.d < T:
                out[self.d :] = x[: T - self.d]
        else:
            k = -self.d
            if k < T:
                out[: T - k] = x[k:]
        return out


class Delta(OperatorNode):
    op_name = "Delta"

    def __init__(self, a: ExprNode, d: int = 1) -> None:
        if isinstance(d, bool) or not isinstance(d, int):
            raise ValueError(f"Delta period d must be an integer, got {d!r}")
        if d <= 0 and not in_label_context():
            raise LookAheadSyntaxError(f"Delta(..., {d}) requires d >= 1 outside LabelContext")
        self.d = int(d)
        super().__init__((a,), (self.d,))

    def max_forward_bars(self) -> int:
        return super().max_forward_bars() + max(0, -self.d)

    def max_backward_bars(self) -> int:
        return super().max_backward_bars() + max(0, self.d)

    def compute(self, child_values: Sequence[np.ndarray], ctx: EvalContext) -> np.ndarray:
        x = child_values[0]
        ref = Ref._shift_matrix(x, self.d)
        _ = ctx
        return x - ref


class ROC(OperatorNode):
    op_name = "ROC"

    def __init__(self, a: ExprNode, d: int = 1) -> None:
        if isinstance(d, bool) or not isinstance(d, int):
            raise ValueError(f"ROC period d must be an integer, got {d!r}")
        if d <= 0 and not in_label_context():
            raise LookAheadSyntaxError(f"ROC(..., {d}) requires d >= 1 outside LabelContext")
        self.d = int(d)
        super().__init__((a,), (self.d,))

    def max_forward_bars(self) -> int:
        return super().max_forward_bars() + max(0, -self.d)

    def max_backward_bars(self) -> int:
        return super().max_backward_bars() + max(0, self.d)

    def compute(self, child_values: Sequence[np.ndarray], ctx: EvalContext) -> np.ndarray:
        _ = ctx
        x = child_values[0]
        ref = Ref._shift_matrix(x, self.d)
        with np.errstate(divide="ignore", invalid="ignore"):
            return np.where(np.abs(ref) > 1e-30, x / ref - 1.0, np.nan)


def _shift_matrix(x: np.ndarray, d: int) -> np.ndarray:
    T = x.shape[0]
    if d == 0:
        return x.copy()
    out = np.full_like(x, np.nan)
    if d > 0 and d < T:
        out[d:] = x[: T - d]
    elif d < 0 and (-d) < T:
        k = -d
        out[: T - k] = x[k:]
    return out


Ref._shift_matrix = staticmethod(_shift_matrix)  # type: ignore[attr-defined]


# --------------------------------------------------------------------------- #
# Rolling Univariate Operators
# --------------------------------------------------------------------------- #
class _RollingUnivariateOp(OperatorNode):
    def __init__(self, a: ExprNode, d: int) -> None:
        self.d = _validate_positive_window(d, self.op_name)
        super().__init__((a,), (self.d,))

    def max_backward_bars(self) -> int:
        return super().max_backward_bars() + self.d - 1

    def _eval_1d(self, col: np.ndarray) -> np.ndarray:
        raise NotImplementedError

    def compute(self, child_values: Sequence[np.ndarray], ctx: EvalContext) -> np.ndarray:
        _ = ctx
        x = child_values[0]
        out = np.empty_like(x, dtype=np.float64)
        for j in range(x.shape[1]):
            out[:, j] = self._eval_1d(x[:, j])
        return out


class Mean(_RollingUnivariateOp):
    op_name = "Mean"
    def _eval_1d(self, col: np.ndarray) -> np.ndarray:
        return _accel.rolling_mean(col, self.d, self.d)


class Sum(_RollingUnivariateOp):
    op_name = "Sum"
    def _eval_1d(self, col: np.ndarray) -> np.ndarray:
        return _accel.rolling_sum(col, self.d, self.d)


class Std(_RollingUnivariateOp):
    op_name = "Std"
    def _eval_1d(self, col: np.ndarray) -> np.ndarray:
        return _accel.rolling_std(col, self.d, self.d)


class Var(_RollingUnivariateOp):
    op_name = "Var"
    def _eval_1d(self, col: np.ndarray) -> np.ndarray:
        return _accel.rolling_var(col, self.d, self.d)


class Skew(_RollingUnivariateOp):
    op_name = "Skew"
    def _eval_1d(self, col: np.ndarray) -> np.ndarray:
        return _accel.rolling_skew(col, self.d, self.d)


class Kurt(_RollingUnivariateOp):
    op_name = "Kurt"
    def _eval_1d(self, col: np.ndarray) -> np.ndarray:
        return _accel.rolling_kurt(col, self.d, self.d)


class Max(_RollingUnivariateOp):
    op_name = "Max"
    def _eval_1d(self, col: np.ndarray) -> np.ndarray:
        return _accel.rolling_max(col, self.d, self.d)


class Min(_RollingUnivariateOp):
    op_name = "Min"
    def _eval_1d(self, col: np.ndarray) -> np.ndarray:
        return _accel.rolling_min(col, self.d, self.d)


class Med(_RollingUnivariateOp):
    op_name = "Med"
    def _eval_1d(self, col: np.ndarray) -> np.ndarray:
        n = col.size
        out = np.full(n, np.nan, dtype=np.float64)
        if n < self.d:
            return out
        wins = sliding_window_view(col, self.d)
        ok = np.all(np.isfinite(wins), axis=1)
        if np.any(ok):
            out[self.d - 1 :][ok] = np.median(wins[ok], axis=1)
        return out


class Quantile(OperatorNode):
    op_name = "Quantile"

    def __init__(self, a: ExprNode, d: int, q: float) -> None:
        self.d = _validate_positive_window(d, self.op_name)
        qf = float(q)
        if not (0.0 <= qf <= 1.0):
            raise ValueError(f"Quantile q must lie in [0, 1], got {q}")
        self.q = qf
        super().__init__((a,), (self.d, self.q))

    def max_backward_bars(self) -> int:
        return super().max_backward_bars() + self.d - 1

    def compute(self, child_values: Sequence[np.ndarray], ctx: EvalContext) -> np.ndarray:
        _ = ctx
        x = child_values[0]
        T, N = x.shape
        out = np.full((T, N), np.nan, dtype=np.float64)
        if T < self.d:
            return out
        for j in range(N):
            wins = sliding_window_view(x[:, j], self.d)
            ok = np.all(np.isfinite(wins), axis=1)
            if np.any(ok):
                out[self.d - 1 :, j][ok] = np.quantile(wins[ok], self.q, axis=1)
        return out


class TSRank(_RollingUnivariateOp):
    op_name = "TSRank"
    def _eval_1d(self, col: np.ndarray) -> np.ndarray:
        n = col.size
        out = np.full(n, np.nan, dtype=np.float64)
        if n < self.d:
            return out
        wins = sliding_window_view(col, self.d)
        ok = np.all(np.isfinite(wins), axis=1)
        if not np.any(ok):
            return out
        valid_w = wins[ok]
        cur = valid_w[:, -1:]
        if self.d == 1:
            out[ok] = 0.5
        else:
            less = np.sum(valid_w < cur, axis=1)
            eq = np.sum(valid_w == cur, axis=1)
            out[self.d - 1 :][ok] = (less + 0.5 * (eq - 1.0)) / float(self.d - 1)
        return out


class IdxMax(_RollingUnivariateOp):
    """Offset in [1, d] of the maximum within [t - d + 1, t] (1 = oldest, d = current)."""

    op_name = "IdxMax"
    def _eval_1d(self, col: np.ndarray) -> np.ndarray:
        n = col.size
        out = np.full(n, np.nan, dtype=np.float64)
        if n < self.d:
            return out
        wins = sliding_window_view(col, self.d)
        ok = np.all(np.isfinite(wins), axis=1)
        if np.any(ok):
            out[self.d - 1 :][ok] = np.argmax(wins[ok], axis=1).astype(np.float64) + 1.0
        return out


class IdxMin(_RollingUnivariateOp):
    """Offset in [1, d] of the minimum within [t - d + 1, t] (1 = oldest, d = current)."""

    op_name = "IdxMin"
    def _eval_1d(self, col: np.ndarray) -> np.ndarray:
        n = col.size
        out = np.full(n, np.nan, dtype=np.float64)
        if n < self.d:
            return out
        wins = sliding_window_view(col, self.d)
        ok = np.all(np.isfinite(wins), axis=1)
        if np.any(ok):
            out[self.d - 1 :][ok] = np.argmin(wins[ok], axis=1).astype(np.float64) + 1.0
        return out


class EMA(_RollingUnivariateOp):
    op_name = "EMA"
    def _eval_1d(self, col: np.ndarray) -> np.ndarray:
        return _accel.ema(col, self.d, min_periods=1)


class WMA(_RollingUnivariateOp):
    op_name = "WMA"
    def _eval_1d(self, col: np.ndarray) -> np.ndarray:
        n = col.size
        out = np.full(n, np.nan, dtype=np.float64)
        if n < self.d:
            return out
        weights = np.arange(1, self.d + 1, dtype=np.float64)
        weights /= weights.sum()
        wins = sliding_window_view(col, self.d)
        ok = np.all(np.isfinite(wins), axis=1)
        if np.any(ok):
            out[self.d - 1 :][ok] = wins[ok] @ weights
        return out


class RSI(_RollingUnivariateOp):
    op_name = "RSI"

    def max_backward_bars(self) -> int:
        return super().max_backward_bars() + 1

    def _eval_1d(self, col: np.ndarray) -> np.ndarray:
        return _accel.wilder_rsi(col, self.d)


class ATR(OperatorNode):
    op_name = "ATR"

    def __init__(
        self,
        high_or_period: ExprNode | int,
        low: ExprNode | None = None,
        close: ExprNode | None = None,
        period: int | None = None,
    ) -> None:
        if isinstance(high_or_period, int) and low is None and close is None and period is None:
            self.d = _validate_positive_window(high_or_period, self.op_name)
            children: tuple[ExprNode, ...] = (FieldNode("high"), FieldNode("low"), FieldNode("close"))
        else:
            if not isinstance(high_or_period, ExprNode) or low is None or close is None or period is None:
                raise ValueError("ATR expects either ATR(period) or ATR(high, low, close, period)")
            self.d = _validate_positive_window(period, self.op_name)
            children = (high_or_period, low, close)
        super().__init__(children, (self.d,))

    def max_backward_bars(self) -> int:
        return super().max_backward_bars() + self.d

    def compute(self, child_values: Sequence[np.ndarray], ctx: EvalContext) -> np.ndarray:
        _ = ctx
        h, l, c = child_values
        out = np.empty_like(c, dtype=np.float64)
        for j in range(c.shape[1]):
            out[:, j] = _accel.wilder_atr(h[:, j], l[:, j], c[:, j], self.d)
        return out


# --------------------------------------------------------------------------- #
# Rolling Bivariate & Regression Operators
# --------------------------------------------------------------------------- #
class Cov(OperatorNode):
    op_name = "Cov"

    def __init__(self, a: ExprNode, b: ExprNode, d: int) -> None:
        self.d = _validate_positive_window(d, self.op_name)
        super().__init__((a, b), (self.d,))

    def max_backward_bars(self) -> int:
        return super().max_backward_bars() + self.d - 1

    def compute(self, child_values: Sequence[np.ndarray], ctx: EvalContext) -> np.ndarray:
        _ = ctx
        a, b = child_values
        out = np.empty_like(a, dtype=np.float64)
        for j in range(a.shape[1]):
            out[:, j] = _accel.rolling_cov(a[:, j], b[:, j], self.d, self.d)
        return out


class Corr(OperatorNode):
    op_name = "Corr"

    def __init__(self, a: ExprNode, b: ExprNode, d: int) -> None:
        self.d = _validate_positive_window(d, self.op_name)
        super().__init__((a, b), (self.d,))

    def max_backward_bars(self) -> int:
        return super().max_backward_bars() + self.d - 1

    def compute(self, child_values: Sequence[np.ndarray], ctx: EvalContext) -> np.ndarray:
        _ = ctx
        a, b = child_values
        out = np.empty_like(a, dtype=np.float64)
        for j in range(a.shape[1]):
            out[:, j] = _accel.rolling_corr(a[:, j], b[:, j], self.d, self.d)
        return out


class Slope(_RollingUnivariateOp):
    op_name = "Slope"
    def _eval_1d(self, col: np.ndarray) -> np.ndarray:
        slp, _r2, _resi = _accel.rolling_ols(col, self.d, self.d)
        return slp


class Rsquare(_RollingUnivariateOp):
    op_name = "Rsquare"
    def _eval_1d(self, col: np.ndarray) -> np.ndarray:
        _slp, r2, _resi = _accel.rolling_ols(col, self.d, self.d)
        return r2


class Resi(_RollingUnivariateOp):
    op_name = "Resi"
    def _eval_1d(self, col: np.ndarray) -> np.ndarray:
        _slp, _r2, resi = _accel.rolling_ols(col, self.d, self.d)
        return resi


# --------------------------------------------------------------------------- #
# Time-Series Normalization Operators
# --------------------------------------------------------------------------- #
class ZScore(_RollingUnivariateOp):
    op_name = "ZScore"
    def _eval_1d(self, col: np.ndarray) -> np.ndarray:
        mu = _accel.rolling_mean(col, self.d, self.d)
        sd = _accel.rolling_std(col, self.d, self.d)
        with np.errstate(divide="ignore", invalid="ignore"):
            return np.where(sd > 1e-15, (col - mu) / sd, np.nan)


class RobustZScore(_RollingUnivariateOp):
    op_name = "RobustZScore"
    def _eval_1d(self, col: np.ndarray) -> np.ndarray:
        n = col.size
        out = np.full(n, np.nan, dtype=np.float64)
        if n < self.d:
            return out
        wins = sliding_window_view(col, self.d)
        ok = np.all(np.isfinite(wins), axis=1)
        if not np.any(ok):
            return out
        valid_w = wins[ok]
        med = np.median(valid_w, axis=1)
        mad = 1.4826 * np.median(np.abs(valid_w - med[:, None]), axis=1)
        cur = valid_w[:, -1]
        with np.errstate(divide="ignore", invalid="ignore"):
            z = np.where(mad > 1e-15, (cur - med) / mad, np.nan)
        out[self.d - 1 :][ok] = z
        return out


# --------------------------------------------------------------------------- #
# Cross-Sectional Operators (Across Instruments at Identical Timestamp ONLY)
# --------------------------------------------------------------------------- #
class CSRank(OperatorNode):
    op_name = "CSRank"
    is_cross_sectional = True

    def __init__(self, a: ExprNode) -> None:
        super().__init__((a,))

    def compute(self, child_values: Sequence[np.ndarray], ctx: EvalContext) -> np.ndarray:
        _ = ctx
        x = child_values[0]
        T, N = x.shape
        out = np.full((T, N), np.nan, dtype=np.float64)
        for t in range(T):
            row = x[t]
            ok = np.isfinite(row)
            k = int(np.sum(ok))
            if k == 0:
                continue
            if k == 1:
                out[t, ok] = 0.5
                continue
            vals = row[ok]
            # Mid-rank percentile in [0, 1]
            less = np.sum(vals[:, None] > vals[None, :], axis=1)
            eq = np.sum(vals[:, None] == vals[None, :], axis=1)
            out[t, ok] = (less + 0.5 * (eq - 1.0)) / float(k - 1)
        return out


class CSZScore(OperatorNode):
    op_name = "CSZScore"
    is_cross_sectional = True

    def __init__(self, a: ExprNode) -> None:
        super().__init__((a,))

    def compute(self, child_values: Sequence[np.ndarray], ctx: EvalContext) -> np.ndarray:
        _ = ctx
        x = child_values[0]
        T, N = x.shape
        out = np.full((T, N), np.nan, dtype=np.float64)
        for t in range(T):
            row = x[t]
            ok = np.isfinite(row)
            k = int(np.sum(ok))
            if k < 2:
                continue
            vals = row[ok]
            mu = float(np.mean(vals))
            sd = float(np.std(vals, ddof=1))
            out[t, ok] = (vals - mu) / sd if sd > 1e-15 else 0.0
        return out


class CSDemean(OperatorNode):
    op_name = "CSDemean"
    is_cross_sectional = True

    def __init__(self, a: ExprNode) -> None:
        super().__init__((a,))

    def compute(self, child_values: Sequence[np.ndarray], ctx: EvalContext) -> np.ndarray:
        _ = ctx
        x = child_values[0]
        T, N = x.shape
        out = np.full((T, N), np.nan, dtype=np.float64)
        for t in range(T):
            row = x[t]
            ok = np.isfinite(row)
            if np.any(ok):
                out[t, ok] = row[ok] - float(np.mean(row[ok]))
        return out
