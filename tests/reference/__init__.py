"""Reference mode entry points (spec section 9.3.3 L5992; TASK-M2-07).

The only place that passes `reference_only=True` into `core/quant/costed.py` (and, from M4/M5, into the sleeve
and ladder builders). Configurations the rules store refuses - a vol-target cap above 1.0, product stacks, the
literal v1.2 ladder - are computed here for the `reference_only` goldens (G-KR-06, G-MOM-07, G-KR-L13 cap 1.5,
G-LAD-01..03) and never enter a book, a card or an artifact.

`core/` can never import this package: the import below refuses when any importing frame lives under `core/`,
and tests/macro_m2_costed.py checks statically that no `core/**` module names it or passes `reference_only=True`.
"""
from __future__ import annotations

import inspect
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_CORE = _ROOT / "core"


def _refuse_core_importer() -> None:
    frame = inspect.currentframe()
    while frame is not None:
        path = Path(frame.f_code.co_filename)
        if path.is_absolute():
            try:
                path.resolve().relative_to(_CORE)
            except ValueError:
                pass
            else:
                raise ImportError(f"tests.reference is reference mode; core/ cannot import it (L5992): {path}")
        frame = frame.f_back


_refuse_core_importer()
