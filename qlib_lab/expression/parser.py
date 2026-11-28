"""Safe ast.parse(..., mode='eval') whitelist parser with Static Future-Shift Ban."""
from __future__ import annotations

import ast
import re
from typing import Any, Mapping

import pandas as pd

from qlib_lab.exceptions import LookAheadSyntaxError, SecurityRefusalError
from qlib_lab.expression import ops, pit_ops
from qlib_lab.expression.ast_nodes import (
    ConstantNode,
    ExpressionDAG,
    ExprNode,
    FieldNode,
    PITSeriesRefNode,
    in_label_context,
)

# Whitelisted function call map (zero dynamic getattr / eval)
OPERATOR_WHITELIST: dict[str, Any] = {
    "Add": ops.Add,
    "Sub": ops.Sub,
    "Mul": ops.Mul,
    "Div": ops.Div,
    "Log": ops.Log,
    "Abs": ops.Abs,
    "Sign": ops.Sign,
    "Clip": ops.Clip,
    "If": ops.If,
    "Ref": ops.Ref,
    "Delta": ops.Delta,
    "ROC": ops.ROC,
    "Mean": ops.Mean,
    "Sum": ops.Sum,
    "Std": ops.Std,
    "Var": ops.Var,
    "Skew": ops.Skew,
    "Kurt": ops.Kurt,
    "Max": ops.Max,
    "Min": ops.Min,
    "Med": ops.Med,
    "Quantile": ops.Quantile,
    "TSRank": ops.TSRank,
    "IdxMax": ops.IdxMax,
    "IdxMin": ops.IdxMin,
    "EMA": ops.EMA,
    "WMA": ops.WMA,
    "RSI": ops.RSI,
    "ATR": ops.ATR,
    "Cov": ops.Cov,
    "Corr": ops.Corr,
    "Slope": ops.Slope,
    "Rsquare": ops.Rsquare,
    "Resi": ops.Resi,
    "ZScore": ops.ZScore,
    "RobustZScore": ops.RobustZScore,
    "CSRank": ops.CSRank,
    "CSZScore": ops.CSZScore,
    "CSDemean": ops.CSDemean,
    # Bitemporal PIT operators
    "PIT": pit_ops.PIT,
    "P": pit_ops.PIT,
    "PRef": pit_ops.PRef,
    "PITYoY": pit_ops.PITYoY,
    "PITMoM": pit_ops.PITMoM,
    "PITNewEventFlag": pit_ops.PITNewEventFlag,
    "PITSlotRatio": pit_ops.PITSlotRatio,
    "PITPinnedScoreMean": pit_ops.PITPinnedScoreMean,
}

# Operators whose non-ExprNode literal scalar arguments are unpacked directly
_LITERAL_ARG_OPS = {
    "Ref",
    "Delta",
    "ROC",
    "Mean",
    "Sum",
    "Std",
    "Var",
    "Skew",
    "Kurt",
    "Max",
    "Min",
    "Med",
    "Quantile",
    "TSRank",
    "IdxMax",
    "IdxMin",
    "EMA",
    "WMA",
    "RSI",
    "ATR",
    "Cov",
    "Corr",
    "Slope",
    "Rsquare",
    "Resi",
    "ZScore",
    "RobustZScore",
    "Clip",
    "PIT",
    "P",
    "PRef",
    "PITYoY",
    "PITMoM",
    "PITNewEventFlag",
    "PITSlotRatio",
    "PITPinnedScoreMean",
}

_TOKEN_RE = re.compile(
    r"""(?P<sq>'[^'\\]*(?:\\.[^'\\]*)*')|(?P<dq>"[^"\\]*(?:\\.[^"\\]*)*")|(?P<pit>\$\$[A-Za-z0-9_][A-Za-z0-9_.-]*)|(?P<fld>\$[A-Za-z_][A-Za-z0-9_.]*)"""
)


def _preprocess_dollar_tokens(expr: str) -> str:
    if not isinstance(expr, str) or not expr.strip():
        raise SyntaxError("Expression must be a non-empty string")
    if "__" in expr:
        raise SecurityRefusalError(f"Dunder token '__' is forbidden in expression: {expr!r}")

    def _repl(match: re.Match[str]) -> str:
        if match.group("sq") is not None or match.group("dq") is not None:
            raw_lit = match.group(0)[1:-1]
            if raw_lit.startswith("$$") and len(raw_lit) > 2:
                return f'_QLIB_PIT_("{raw_lit[2:]}")'
            if raw_lit.startswith("$") and len(raw_lit) > 1:
                return f'_QLIB_FLD_("{raw_lit[1:]}")'
            return match.group(0)
        if match.group("pit") is not None:
            name = match.group("pit")[2:]
            return f'_QLIB_PIT_("{name}")'
        name = match.group("fld")[1:]
        return f'_QLIB_FLD_("{name}")'

    return _TOKEN_RE.sub(_repl, expr)


def _extract_scalar_literal(node: ast.AST) -> int | float | str:
    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool):
            raise SecurityRefusalError("Boolean literals are not valid numeric/string operator parameters")
        if isinstance(node.value, (int, float, str)):
            return node.value
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
        inner = _extract_scalar_literal(node.operand)
        if isinstance(inner, (int, float)):
            return -inner if isinstance(node.op, ast.USub) else +inner
    if isinstance(node, ast.Name) and node.id == "nan":
        return float("nan")
    raise SecurityRefusalError(f"Expected scalar literal parameter, got AST node {type(node).__name__}")


def _compile_ast(node: ast.AST) -> ExprNode:
    if isinstance(node, ast.Expression):
        return _compile_ast(node.body)

    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
            raise SecurityRefusalError(f"Unsupported top-level constant {node.value!r} in expression")
        return ConstantNode(float(node.value))

    if isinstance(node, ast.UnaryOp):
        operand = _compile_ast(node.operand)
        if isinstance(node.op, ast.UAdd):
            return operand
        if isinstance(node.op, ast.USub):
            if isinstance(operand, ConstantNode):
                return ConstantNode(-operand.value)
            return ops.Neg(operand)
        raise SecurityRefusalError(f"Unsupported unary operator {type(node.op).__name__}")

    if isinstance(node, ast.BinOp):
        left = _compile_ast(node.left)
        right = _compile_ast(node.right)
        if isinstance(node.op, ast.Add):
            return ops.Add(left, right)
        if isinstance(node.op, ast.Sub):
            return ops.Sub(left, right)
        if isinstance(node.op, ast.Mult):
            return ops.Mul(left, right)
        if isinstance(node.op, ast.Div):
            return ops.Div(left, right)
        raise SecurityRefusalError(f"Unsupported binary operator {type(node.op).__name__}")

    if isinstance(node, ast.Compare):
        if len(node.ops) != 1 or len(node.comparators) != 1:
            raise SecurityRefusalError("Chained comparisons are not supported; combine explicit comparisons")
        left = _compile_ast(node.left)
        right = _compile_ast(node.comparators[0])
        op = node.ops[0]
        cmp_map = {
            ast.Gt: ops.Gt,
            ast.GtE: ops.Ge,
            ast.Lt: ops.Lt,
            ast.LtE: ops.Le,
            ast.Eq: ops.Eq,
            ast.NotEq: ops.Ne,
        }
        cls = cmp_map.get(type(op))
        if cls is None:
            raise SecurityRefusalError(f"Unsupported comparison operator {type(op).__name__}")
        return cls(left, right)

    if isinstance(node, ast.BoolOp):
        if isinstance(node.op, ast.And):
            cur = _compile_ast(node.values[0])
            for nxt in node.values[1:]:
                cur = ops.And(cur, _compile_ast(nxt))
            return cur
        if isinstance(node.op, ast.Or):
            cur = _compile_ast(node.values[0])
            for nxt in node.values[1:]:
                cur = ops.Or(cur, _compile_ast(nxt))
            return cur
        raise SecurityRefusalError(f"Unsupported boolean operator {type(node.op).__name__}")

    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name):
            raise SecurityRefusalError(
                "Attribute/method calls are forbidden in expression DSL; use whitelisted operator names only"
            )
        fname = node.func.id
        if fname == "_QLIB_FLD_":
            if len(node.args) != 1 or node.keywords:
                raise SecurityRefusalError("Malformed $field token")
            fld = _extract_scalar_literal(node.args[0])
            return FieldNode(str(fld))
        if fname == "_QLIB_PIT_":
            if len(node.args) != 1 or node.keywords:
                raise SecurityRefusalError("Malformed $$series token")
            sid = _extract_scalar_literal(node.args[0])
            return PITSeriesRefNode(str(sid))

        op_cls = OPERATOR_WHITELIST.get(fname)
        if op_cls is None:
            raise SecurityRefusalError(f"Operator {fname!r} is not in OPERATOR_WHITELIST")

        compiled_args: list[Any] = []
        for idx, arg in enumerate(node.args):
            if fname in _LITERAL_ARG_OPS:
                # Determine whether arg is an expression child or scalar parameter
                if fname == "ATR" and len(node.args) == 1:
                    compiled_args.append(_extract_scalar_literal(arg))
                elif fname == "ATR" and idx < 3:
                    compiled_args.append(_compile_ast(arg))
                elif fname in ("Cov", "Corr") and idx < 2:
                    compiled_args.append(_compile_ast(arg))
                elif fname.startswith("PIT") or fname in ("P", "PRef"):
                    if idx == 0:
                        if isinstance(arg, ast.Call) and isinstance(arg.func, ast.Name) and arg.func.id == "_QLIB_PIT_":
                            compiled_args.append(_compile_ast(arg))
                        else:
                            lit = _extract_scalar_literal(arg)
                            compiled_args.append(PITSeriesRefNode(str(lit)))
                    else:
                        compiled_args.append(_extract_scalar_literal(arg))
                elif idx == 0:
                    compiled_args.append(_compile_ast(arg))
                else:
                    compiled_args.append(_extract_scalar_literal(arg))
            else:
                compiled_args.append(_compile_ast(arg))

        compiled_kwargs: dict[str, Any] = {}
        for kw in node.keywords:
            if kw.arg is None:
                raise SecurityRefusalError("Starred **kwargs unpacking is forbidden in expression DSL")
            compiled_kwargs[kw.arg] = _extract_scalar_literal(kw.value)

        return op_cls(*compiled_args, **compiled_kwargs)

    raise SecurityRefusalError(f"Disallowed AST construct {type(node).__name__} in expression DSL")


def parse_expression(expr: str | ExprNode) -> ExprNode:
    """Parse a formulaic expression into a verified ExprNode, enforcing the Static Future-Shift Ban."""
    if isinstance(expr, ExprNode):
        node = expr
    else:
        preprocessed = _preprocess_dollar_tokens(expr)
        try:
            tree = ast.parse(preprocessed, mode="eval")
        except SyntaxError as exc:
            raise SyntaxError(f"Invalid expression syntax {expr!r}: {exc}") from exc
        node = _compile_ast(tree)

    if not in_label_context() and node.max_forward_bars() > 0:
        raise LookAheadSyntaxError(
            f"Expression {expr!r} has max_forward_bars={node.max_forward_bars()} > 0; "
            "forward shifts are strictly forbidden outside LabelContext"
        )
    return node


def compile_expressions(expressions: Mapping[str, str | ExprNode]) -> ExpressionDAG:
    """Compile {name: expr} into a CSE-deduplicated ExpressionDAG."""
    parsed = {name: parse_expression(ex) for name, ex in expressions.items()}
    return ExpressionDAG(parsed)


def evaluate_expressions(
    panel: pd.DataFrame,
    expressions: Mapping[str, str | ExprNode],
    *,
    pit_provider: Any = None,
    bar_lag: int = 0,
    on_lag_violation: str = "raise",
    known_at_col: str | tuple[str, str] | None = "known_at",
) -> pd.DataFrame:
    """Parse, CSE-deduplicate, and evaluate a batch of expressions on a panel."""
    is_lbl = in_label_context()
    dag = compile_expressions(expressions)
    return dag.evaluate(
        panel,
        pit_provider=pit_provider,
        bar_lag=bar_lag,
        on_lag_violation=on_lag_violation,
        known_at_col=known_at_col,
        is_label_eval=is_lbl,
    )
