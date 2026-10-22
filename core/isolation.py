r"""TRADEGEN never touches QUANTGEN (split 2026-10-23): one refusal shared by config's path resolver and every writer
of persistent records (gate_ledger, governance). Standard library only, so pure modules such as gate_ledger (no
config import, T-LEDGER-01) can call it too."""
from __future__ import annotations

import os
from pathlib import Path

QUANTGEN_STATE = Path.home() / ".nextgen"                                        # its ledgers, frozen studies, KIS token
QUANTGEN_REPO = Path(__file__).resolve().parents[1].with_name("QUANTGEN")      # its frozen-study records


def refuse_quantgen(path, what: str = "path") -> Path:
    r"""`path`, unless it lies inside QUANTGEN's state root or repository: then RuntimeError, before any I/O.
    Compared as resolved paths (case, 8.3 names, relative paths) and by file identity of every existing ancestor,
    which also catches \\?\, UNC-share and junction aliases of the same directory."""
    p = Path(path).resolve()
    for root in (QUANTGEN_STATE, QUANTGEN_REPO):
        if p.is_relative_to(root.resolve()) or (root.exists() and any(
                a.exists() and os.path.samefile(a, root) for a in (p, *p.parents))):
            raise RuntimeError(f"{what} {path} is inside QUANTGEN ({root}); TRADEGEN keeps its own state under "
                               "~/.tradegen and never reads or writes QUANTGEN's")
    return Path(path)
