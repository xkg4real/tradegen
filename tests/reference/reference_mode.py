"""Reference-mode computations (section 9.3.3 L5992): refused configurations, reproduced for the reference goldens.

Every function here is the sole caller of `reference_only=True`. Results are plain dicts; `result_md5` freezes one
(canonical JSON, md5) for the section 9.4 item 2 rerun record. Nothing here writes a file, a book or an artifact.
"""
from __future__ import annotations

import numpy as np

from core.ficc.macro_schema import canonical_json, md5_hex
from core.quant import costed as C
from core.quant.validate import sharpe

CAP_G_KR_06 = 1.5          # the cap-1.5 vol-target line (L5778), prohibited in the store (section 10 item 2)


def vt_weights(returns, target_ann: float, window: int = 20, cap: float = 1.0) -> np.ndarray:
    """Vol-target decided weights with any cap (cap > 1.0 is the refused shape)."""
    return C.vt_weights(returns, target_ann, window, cap, reference_only=True)


def costed_path(weights_earning, returns, cost_bp_per_side: float, stress: float = 1.0, *, legs: int = 1) -> C.CostedPath:
    """The costed engine on a weight path that may exceed 1.0."""
    return C.costed_path(weights_earning, returns, cost_bp_per_side, stress, legs=legs, reference_only=True)


def product_stack(*multipliers) -> np.ndarray:
    """The literal product composition of the labs (ENS x VT; section 10 item 31). Never `min()`, never floored."""
    C.reference_guard(True, "product stack")
    out = np.ones_like(np.asarray(multipliers[0], dtype=float))
    for m in multipliers:
        out = out * np.asarray(m, dtype=float)
    return out


def literal_ladder(*_a, **_k):
    """The literal v1.2 ladder readings of G-LAD-01..03 (cumulative and non-cumulative)."""
    raise NotImplementedError("# integration: provided by M5 (drawdown_ladder, literal v1.2 reading)")


def vol_target_line(returns, target_ann: float, cap: float, cost_bp_per_side: float, window: int = 20,
                    stress: float = 1.0) -> dict:
    """Sharpe, max DD, average exposure and turnover of a vol-target line at any cap (G-KR-06 at cap 1.5)."""
    r = np.asarray(returns, dtype=float)
    w = C.earning_weights(vt_weights(r, target_ann, window, cap))
    book = costed_path(w, r, cost_bp_per_side, stress)
    valid = np.isfinite(w)
    return {"cap": float(cap), "target_ann": float(target_ann), "window": int(window),
            "cost_bp_per_side": float(cost_bp_per_side), "stress": float(stress),
            "sharpe": sharpe(book.net[valid]), "mdd": C.max_drawdown(book.net[valid]),
            "average_exposure": float(np.mean(w[valid])), "turnover_per_year": book.turnover_per_year,
            "reference_only": True}


def result_md5(result: dict) -> str:
    """md5 of the canonical JSON of a reference result (the freeze record of section 9.4 item 2)."""
    return md5_hex(canonical_json(result))
