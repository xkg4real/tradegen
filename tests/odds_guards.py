"""Static guards over core/odds and core/oddsdata, the D14 closure check, the suite registration and the harness
self-tests: odds plan Task 1 (contract sections 0, 3 and 15; RULINGS O1, O2, O13; RULINGS_ROUND2 R2-6, R2-10).

Each guard is a pure checker `(rel, source) -> [hit, ...]`. Every test first proves its checker catches a synthetic
offender under `core/odds/x.py` (X) or `core/oddsdata/x.py` (XD), the positive control, then asserts the shipped files
are clean. The compliance guards keep their own scopes (they already scan core/odds for raw words, forbidden and
dynamic imports); these add the O1 import allowlist of the signed core, its purity (no clock, no `__main__` block, no
file I/O, no package re-export, no subfolder) and the rules of the unsigned loaders. The lists come from
tests/compliance_guards.py at test time, so the follow-up's additions (pstats and tracemalloc, R2-10) bind core/odds
with no change here. Every import statement is checked, including a name taken from an allowed repo module that it
only imports itself (`from core.isolation import os`). Like every guard here, a denylist read by a scan, not a proof:
an attribute route through an allowed module (`isolation.os.remove(p)`, `scipy.io.loadmat(p)`), `getattr(module,
"name")`, a name assigned from an import (`_os = os` in an allowed module), a clock or a write reached any other way
than the forms listed in each checker, and code run by injected objects are left to review.
"""
from __future__ import annotations

import ast
import contextlib
import io
import os
import sys
import types
from pathlib import Path

from tests import compliance_guards as CG

ROOT = Path(__file__).resolve().parents[1]
ODDS, ODDSDATA = ROOT / "core" / "odds", ROOT / "core" / "oddsdata"
X, XD = "core/odds/x.py", "core/oddsdata/x.py"          # the names a synthetic offender is checked under
RUN = "core/oddsdata/run.py"                            # the one file whose main() may read the clock (O15)
# Q1: everything core/odds may hold (a __pycache__ folder appears when it is imported)
_CORE_FILES = ("__init__.py", "plan.py", "costs.py", "models.py", "simulate.py", "bold.py", "report.py")
_CORE_OTHER = ("venues.yaml", "__pycache__")
_COMPLIANCE_MODULES = ("model", "rules", "gate", "owner")   # O1: the compliance modules the core may import
# The file-I/O modules the signed core never imports: the sixteen of contract section 0, builtins (its open), scipy.io
# and the public and private numpy homes of np.load and open_memmap.
_FILE_MODULES = ("io", "os", "pathlib", "shutil", "tempfile", "glob", "fileinput", "mmap", "sqlite3", "dbm", "csv",
                 "zipfile", "tarfile", "gzip", "bz2", "lzma", "builtins", "scipy.io", "numpy.lib.npyio",
                 "numpy.lib.format", "numpy.lib._npyio_impl", "numpy.lib._format_impl")
# The modules that run a process or native code, reach the OS file API under another name (_io and _pyio, and
# ntpath, posixpath and genericpath, the homes of os.path; fix T1-R1-1), reach a file or the registry by another
# route (linecache, filecmp, configparser, py_compile, logging's FileHandler, xml.etree's parse, winreg,
# scipy.datasets; pre-flight P11) or compile a string, which no core/odds file needs either.
_CORE_ALSO_BANNED = ("subprocess", "_winapi", "nt", "posix", "_io", "codeop", "dis", "_frozen_importlib",
                     "_frozen_importlib_external", "_imp", "_interpreters", "numpy.ctypeslib", "linecache", "filecmp",
                     "configparser", "py_compile", "winreg", "scipy.datasets", "logging", "xml.etree", "_pyio",
                     "ntpath", "posixpath", "genericpath")
# names that read or write a file, called as an attribute (np.load, Path.read_text) or imported by name (from numpy
# import load); `.replace` only on the name os
_IO_ATTRS = frozenset({"open", "read_text", "read_bytes", "write_text", "write_bytes", "mkdir", "unlink", "rename",
                       "load", "save", "savez", "savez_compressed", "loadtxt", "savetxt", "genfromtxt", "fromregex",
                       "fromfile", "tofile", "memmap", "open_memmap"})
# clock readers beyond compliance_guards.CLOCKS (spec 7.3), keyed like it by the name before the dot
_MORE_CLOCKS = {"utils": {"localtime", "formatdate"}, "uuid": {"uuid1"}, "Timestamp": {"now", "today", "utcnow"}}
# what core/oddsdata never imports, beyond compliance_guards.FORBIDDEN_MODULES (O1, O2, R2-6)
_ODDSDATA_BANNED = ("core.engine", "docs.asset_expansion_study", "asset_expansion_study", "core.quant.gate_ledger",
                    "core.ficc.macro_artifacts")
# what writes, renames or deletes a file in core/oddsdata: methods on any object, and module functions
_WRITE_ATTRS = frozenset({"write_text", "write_bytes", "mkdir", "touch", "unlink", "rmdir", "symlink_to",
                          "hardlink_to", "tofile"})
_MODULE_WRITES = {"os": frozenset({"replace", "rename", "renames", "makedirs", "mkdir", "remove", "removedirs",
                                   "unlink", "rmdir", "link", "symlink", "truncate"}),
                  "shutil": frozenset({"copy", "copy2", "copyfile", "copytree", "copymode", "copystat", "move",
                                       "rmtree"}),
                  "numpy": frozenset({"save", "savez", "savez_compressed", "savetxt"})}
_DATA_LAYER = ("core/oddsdata/", "data/", "config.py", "core/quant/", "core/calendars/", "core/engine/")


# --------------------------------------------------------------------------- #
# Scope and helpers
# --------------------------------------------------------------------------- #
def _files(base: Path) -> dict[str, str]:
    """rel path -> source of every .py file under `base`; its __init__.py must be among them, so a moved or renamed
    package cannot empty the scan."""
    files = CG._sources(base)
    init = (base / "__init__.py").relative_to(ROOT).as_posix()
    assert init in files, f"scan scope: {init} missing"
    return files


def _under(target: str, banned: tuple[str, ...]) -> bool:
    """A dotted name equal to, or below, an entry of `banned` (`os.path` is below `os`; `iox` is not)."""
    return any(target == m or target.startswith(m + ".") for m in banned)


def _targets(module: str, names: tuple[str, ...]) -> list[str]:
    """The dotted names one import binds: `from a import b` is `a.b`, `import a.b` is `a.b`."""
    return [f"{module}.{n}" for n in names] or [module]


def _is_module_file(dotted: str, root: Path = ROOT) -> bool:
    """`dotted` names a module FILE under `root` (core.compliance.rules), never a package (core.odds) or a name.
    (Not owner._module_file, which takes (root, dotted) and returns the path.)"""
    parts = dotted.split(".")
    return all(p.isidentifier() for p in parts) and root.joinpath(*parts[:-1], parts[-1] + ".py").is_file()


def _imported_names(dotted: str, root: Path) -> set[str]:
    """Every name the module file `dotted` binds by an import statement, at any depth (core.isolation: os, Path)."""
    tree = ast.parse(root.joinpath(*dotted.split(".")).with_suffix(".py").read_bytes())
    return {a.asname or a.name.split(".")[0] for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom))
            for a in n.names}


def _core_allowed(target: str, root: Path) -> bool:
    """O1: the stdlib minus the network, dynamic, file-I/O and process modules; numpy and scipy minus their file
    modules; core.isolation; an existing module file of core.odds; core.compliance's model, rules, gate and owner. A
    name taken from one of those repo modules must be its own, not a module or name it imports (`from core.isolation
    import os`, `from core.compliance.rules import yaml`)."""
    parts = target.split(".")
    if _under(target, _FILE_MODULES + _CORE_ALSO_BANNED):
        return False
    if parts[0] in ("numpy", "scipy"):
        return True
    if parts[0] == "core":
        n = 2 if parts[1:2] == ["isolation"] else 3     # the module file: core.isolation or core.<pkg>.<mod>
        mine = len(parts) >= n and (n == 2 or parts[1] == "odds"
                                    or (parts[1] == "compliance" and parts[2] in _COMPLIANCE_MODULES))
        module, name = ".".join(parts[:n]), ".".join(parts[n:n + 1])
        return (mine and _is_module_file(module, root)
                and not (name and name in _imported_names(module, root)))
    return (parts[0] in sys.stdlib_module_names and not _under(target, tuple(CG.NETWORK_MODULES))
            and not CG._dynamic_module(target))


def _aliases(tree: ast.AST) -> dict[str, set[str]]:
    """Keep every import target for each name; a nested import must not hide an earlier write alias."""
    out = {}
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            for a in n.names:
                name = a.asname or a.name.split(".")[0]
                out.setdefault(name, set()).add(a.name if a.asname else a.name.split(".")[0])
        elif isinstance(n, ast.ImportFrom) and n.module:
            for a in n.names:
                out.setdefault(a.asname or a.name, set()).add(f"{n.module}.{a.name}")
    return out


def _write_kind(node: ast.AST, alias: dict[str, set[str]]) -> str:
    """Recognise writes through the raw call name and every import alias, including shadowed aliases.

    File modes, writing methods, module writers and Path renames retain their existing checks. This is a static
    guard, not a general evaluator of arbitrary Python expressions or archive/database APIs.
    """
    if not isinstance(node, ast.Call):
        return ""
    f = node.func
    if isinstance(f, ast.Name):
        targets = (f.id, *sorted(alias.get(f.id, ())))
    elif isinstance(f, ast.Attribute):
        bases = (f.value.id, *sorted(alias.get(f.value.id, ()))) if isinstance(f.value, ast.Name) else ("?",)
        targets = tuple(f"{base}.{f.attr}" for base in bases)
    else:
        return ""
    if isinstance(f, ast.Attribute) and f.attr in _WRITE_ATTRS:
        return f".{f.attr}()"
    if (isinstance(f, ast.Attribute) and f.attr in ("replace", "rename") and len(node.args) == 1 and not node.keywords
            and not (isinstance(f.value, ast.Name) and f.value.id in alias)):
        return f".{f.attr}(target)"
    for dotted in targets:
        module, _, name = dotted.rpartition(".")
        if name in _MODULE_WRITES.get(module, ()):
            return f"{dotted}()"
        if name != "open":
            continue
        # open(file, mode) and io.open / os.open / gzip.open (file, mode); path.open(mode)
        at = 1 if module in ("", "io", "os", "builtins", "codecs", "gzip", "bz2", "lzma") else 0
        mode = next((k.value for k in node.keywords if k.arg in ("mode", "flags")),
                    node.args[at] if len(node.args) > at else None)
        if mode is None:                                      # the default mode "r" reads
            continue
        if isinstance(mode, ast.Constant) and isinstance(mode.value, str) and not set(mode.value) & set("wax+"):
            continue
        return "open() for writing"
    return ""


def _own_nodes(fn: ast.AST):
    """Every node of a function's body, the bodies of nested functions and classes excluded."""
    stack = list(fn.body)
    while stack:
        node = stack.pop()
        yield node
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            stack.extend(ast.iter_child_nodes(node))


def _is_checked_target(node: ast.AST) -> bool:
    return isinstance(node, ast.Call) and (
        (isinstance(node.func, ast.Name) and node.func.id == "checked_target")
        or (isinstance(node.func, ast.Attribute) and node.func.attr == "checked_target"))


def _end(node: ast.AST) -> tuple[int, int]:
    return node.end_lineno, node.end_col_offset


# --------------------------------------------------------------------------- #
# Checkers: (rel, source) -> hits
# --------------------------------------------------------------------------- #
def _core_import_hits(rel: str, src: str, root: Path = ROOT) -> list[str]:
    """Every import of a core/odds file outside the O1 allowlist (`root` locates the module files)."""
    hits = []
    for node, module, names, _f in CG._imports(rel, ast.parse(src)):
        bad = [t for t in _targets(module, names) if "*" in names or not _core_allowed(t, root)]
        if bad:
            hits.append(f"{rel}:{node.lineno}: imports {bad[0]}: outside the O1 allowlist (stdlib minus network, "
                        "dynamic and file modules; numpy; scipy; core.isolation; core.compliance and core.odds "
                        "modules; never a name such a module only imports)")
    return hits


def _core_io_hits(rel: str, src: str) -> list[str]:
    """File I/O in a core/odds file: a file-I/O module imported, an _IO_ATTRS name imported from any module (`from
    numpy import load`), the name `open` or `__builtins__` read (a call or a reference; the field `Series.open` is a
    store and stays legal), an _IO_ATTRS attribute call, os.replace."""
    tree, hits = ast.parse(src), []
    for node, module, names, _f in CG._imports(rel, tree):
        bad = [t for t in _targets(module, names) if _under(t, _FILE_MODULES)]
        bad += [f"{module}.{n}" for n in names if n in _IO_ATTRS]
        if bad:
            hits.append(f"{rel}:{node.lineno}: imports {bad[0]}: the core reads and writes no file")
    for node, _f in CG._walk(tree):
        if isinstance(node, ast.Name) and node.id in ("open", "__builtins__") and isinstance(node.ctx, ast.Load):
            hits.append(f"{rel}:{node.lineno}: {node.id}")
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            attr, base = node.func.attr, node.func.value
            if attr in _IO_ATTRS or (attr == "replace" and isinstance(base, ast.Name) and base.id == "os"):
                hits.append(f"{rel}:{node.lineno}: .{attr}()")
    return hits


def _clock_hits_in(rel: str, src: str, allowed: tuple[str, ...] = ()) -> list[str]:
    """compliance_guards._clock_hits with its exemption moved to `allowed`: only the BODY of a function named main
    in an allowed file may read the clock (CLOCKS and _MORE_CLOCKS, `from time import ...`, a clock imported by name,
    `datetime64('now')`, `Timestamp('today')`)."""
    clocks = {k: set(CG.CLOCKS.get(k, ())) | _MORE_CLOCKS.get(k, set()) for k in {*CG.CLOCKS, *_MORE_CLOCKS}}
    tree, hits, alias = ast.parse(src), [], {}
    for n in ast.walk(tree):                            # `import time as t`, `from email import utils as eu`, from
        if isinstance(n, (ast.Import, ast.ImportFrom)):  # any module (T1-R1-2): the map is file-wide, so a name keeps
            for a in n.names:                           # EVERY name it is imported as: none hides another (T1-RR1-1)
                alias.setdefault(a.asname or a.name, set()).add(a.name.rpartition(".")[2])
    for node, funcs in CG._walk(tree):
        if rel in allowed and "main" in funcs:
            continue
        if isinstance(node, ast.Attribute):
            if isinstance(node.value, ast.Name):        # the raw name and every name it is imported as
                bases = (node.value.id, *sorted(alias.get(node.value.id, ())))
            else:
                bases = (getattr(node.value, "attr", None),)
            base = next((b for b in bases if node.attr in clocks.get(b, ())), None)
            if base:
                hits.append(f"{rel}:{node.lineno}: {base}.{node.attr}")
        elif isinstance(node, ast.ImportFrom) and (node.module == "time" or any(
                a.name in clocks.get((node.module or "").rpartition(".")[2], ()) for a in node.names)):
            hits.append(f"{rel}:{node.lineno}: from {node.module} import ...")
        elif (isinstance(node, ast.Call) and ({getattr(node.func, "attr", getattr(node.func, "id", None))}
              | alias.get(getattr(node.func, "id", None), set())) & {"datetime64", "Timestamp"}
              and node.args and isinstance(node.args[0], ast.Constant)
              and node.args[0].value in ("now", "today")):
            hits.append(f"{rel}:{node.lineno}: {ast.unparse(node)}")
    return hits


def _main_hits(rel: str, src: str, allowed: tuple[str, ...] = ()) -> list[str]:
    """Every comparison with `__name__` (a `__main__` test in either operand order, `!=` included) and every `match
    expression containing __name__` (T1-R1-3 and final review), except, in an allowed file, one top-level block that is exactly `if __name__ == "__main__":`
    / `raise SystemExit(main())`."""
    tree = ast.parse(src)
    exact = {id(n.test) for n in tree.body if rel in allowed and isinstance(n, ast.If) and not n.orelse
             and ast.unparse(n.test) == "__name__ == '__main__'"
             and [ast.unparse(s) for s in n.body] == ["raise SystemExit(main())"]}
    return [f"{rel}:{n.lineno}: a __main__ test; only {allowed or 'no file'} may hold one, exactly "
            "`raise SystemExit(main())`"
            for n in ast.walk(tree) if id(n) not in exact and any(
                isinstance(s, ast.Name) and s.id == "__name__"
                for operand in ((n.left, *n.comparators) if isinstance(n, ast.Compare)
                                else (n.subject,) if isinstance(n, ast.Match) else ())
                for s in ast.walk(operand))]


def _reexport_hits(rel: str, src: str, root: Path = ROOT) -> list[str]:
    """An import of a core package itself (`import core.odds`), or `from core.<pkg> import <name>` where <name> is not
    a module file of that package: a package re-export hides the file it loads from the D14 seeds."""
    hits = []
    for node, module, names, _f in CG._imports(rel, ast.parse(src)):
        if module != "core" and not module.startswith("core."):
            continue
        if _is_module_file(module, root):
            continue                                    # import core.compliance.rules / from core.isolation import x
        bad = [module] if isinstance(node, ast.Import) else [
            f"{module}.{n}" for n in names if not _is_module_file(f"{module}.{n}", root)]
        if bad:
            hits.append(f"{rel}:{node.lineno}: imports {bad[0]}, which is not a module file: import the module")
    return hits


def _layout_hits(base: Path) -> list[str]:
    """Q1: every entry of `base` that is not one of _CORE_FILES or _CORE_OTHER, and every .py file in a subfolder
    (relative to `base`): the D14 seed glob is not recursive, so a nested file would run unsigned."""
    stray = [p.name for p in base.iterdir() if p.name not in _CORE_FILES + _CORE_OTHER]
    nested = [p.relative_to(base).as_posix() for p in base.rglob("*.py") if p.parent != base]
    return sorted(stray + nested)


def _data_import_hits(rel: str, src: str) -> list[str]:
    """core/oddsdata imports: compliance_guards.FORBIDDEN_MODULES, any core.engine module, the study runner, the two
    provenance modules (R2-6) and every star or dynamic import (compliance_guards._dynamic_hits)."""
    banned, hits = tuple(CG.FORBIDDEN_MODULES) + _ODDSDATA_BANNED, []
    for node, module, names, _f in CG._imports(rel, ast.parse(src)):
        bad = [t for t in [module] + [f"{module}.{n}" for n in names] if _under(t, banned)]
        if bad:
            hits.append(f"{rel}:{node.lineno}: imports {bad[0]}")
    return hits + CG._dynamic_hits(rel, src)


def _unchecked_write_hits(rel: str, src: str) -> list[str]:
    """Every file write (see _write_kind) not preceded, in the same function, by a call to checked_target; a write
    outside any function always counts. A scan of the source order, not a proof of the path checked."""
    tree, covered = ast.parse(src), set()
    alias = _aliases(tree)
    for fn in ast.walk(tree):
        if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            own = list(_own_nodes(fn))
            checks = [_end(n) for n in own if _is_checked_target(n)]
            covered |= {id(n) for n in own if _write_kind(n, alias) and checks and min(checks) < _end(n)}
    return [f"{rel}:{n.lineno}: {_write_kind(n, alias)} with no checked_target before it in the same function"
            for n in ast.walk(tree) if _write_kind(n, alias) and id(n) not in covered]


def _closure_hits(names: list[str]) -> list[str]:
    """The D14 closure entries that belong to the data layer (O1)."""
    return [n for n in names if any(n == p or n.startswith(p) for p in _DATA_LAYER)]


def _probe_tree(name: str, files: dict[str, str]) -> Path:
    """A synthetic tree under the per-test temp home (removed with it): rel path -> text."""
    root = Path(os.environ["TRADEGEN_HOME"]) / name
    for rel, text in files.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_bytes(text.encode("utf-8"))
    return root


# --------------------------------------------------------------------------- #
# core/odds: the signed core
# --------------------------------------------------------------------------- #
def test_core_odds_imports_only_the_allowlist():
    """O1: the stdlib minus compliance_guards.NETWORK_MODULES and DYNAMIC_MODULES (membership through
    compliance_guards._dynamic_module, so importlib.metadata stays legal) and minus the file-I/O and process modules;
    numpy and scipy minus their file modules; core.isolation; existing module files of core.odds; core.compliance's
    model, rules, gate and owner, never a name one of them only imports. Nothing else of the repo."""
    for src in ("import config\n", "from core.quant import garch\n", "import core.oddsdata.bars\n",
                "from core.oddsdata import bars\n", "from core.calendars.store import CalendarSet\n",
                "from core.engine import books\n", "import data.krx.kis_client\n",
                "from core.ficc import macro_schema\n", "import yfinance\n", "import pandas as pd\n",
                "def f():\n    import yaml\n", "import socket\n",
                "from urllib import request\n", "from xml.dom import minidom\n", "import ctypes\n", "import os\n",
                "from pathlib import Path\n", "import csv\n", "from io import StringIO\n", "import importlib\n",
                "import importlib.util\n", "from importlib import resources\n", "import pickle\n", "import pstats\n",
                "from tracemalloc import Snapshot\n", "import subprocess\n", "import nt\n", "import dis\n",
                "from math import *\n", "import core\n", "import core.compliance\n", "from core import compliance\n",
                "import core.compliance.nosuch\n", "from core.compliance import alerts\n",
                "from core.odds import nosuch\n", "from ... import config\n",
                "from core.isolation import os\n", "from core.isolation import Path\n",
                "from core.compliance.owner import os\n", "from core.compliance.rules import yaml\n",
                "from core.compliance.owner import _dt\n", "from ..compliance.rules import Path as P\n",
                "import builtins\n", "from builtins import open as o\n", "import scipy.io\n",
                "from scipy.io import loadmat\n", "from scipy import io\n", "import numpy.lib.format as F\n",
                "from numpy.lib import npyio\n", "from numpy.lib._npyio_impl import load\n",
                "from numpy import ctypeslib\n"):
        assert _core_import_hits(X, src), src
    for banned in tuple(CG.NETWORK_MODULES) + tuple(CG.DYNAMIC_MODULES) + _FILE_MODULES + _CORE_ALSO_BANNED:
        for src in (f"import {banned}\n", f"import {banned}.x\n", f"from {banned} import x\n"):
            assert _core_import_hits(X, src), src
    ok = ("from __future__ import annotations\nimport dataclasses, functools, hashlib, json, math\n"
          "from datetime import date, timedelta\nimport fractions\nimport numpy as np\nimport numpy.random\n"
          "from scipy import stats\nfrom scipy.integrate import quad\nimport importlib.metadata\n"
          "from importlib import metadata\nfrom core import isolation\n"
          "from core.isolation import checked_target\nfrom core.compliance import gate, model, owner, rules\n"
          "from core.compliance.model import KST\nimport core.compliance.rules\nfrom ..compliance import model as M\n"
          "from core.compliance.rules import Venue\nimport scipy\nfrom numpy.lib import stride_tricks\n"
          "def f():\n    from core.compliance import owner\n")
    assert not _core_import_hits(X, ok), _core_import_hits(X, ok)
    tree = _probe_tree("odds_tree", {"core/odds/plan.py": "from core.compliance import model\n"})
    mine = ("from . import plan\nfrom core.odds import plan as P\nfrom core.odds.plan import Plan\n"
            "import core.odds.plan\n")
    assert not _core_import_hits(X, mine, root=tree), _core_import_hits(X, mine, root=tree)
    assert _core_import_hits(X, "from core.odds import costs\n", root=tree)
    assert _core_import_hits(X, "from core.odds.plan import model\n", root=tree)      # plan's import, not its own
    hits = [h for rel, src in _files(ODDS).items() for h in _core_import_hits(rel, src)]
    assert not hits, hits


def test_core_odds_reads_no_clock():
    """Seeds and odds never depend on time (spec 7.3): no core/odds file reads the wall clock (compliance_guards.CLOCKS,
    `from time import ...`, email.utils.localtime and formatdate, uuid.uuid1, datetime64('now'), Timestamp.now), not
    even in a main(); the time comes in as `Inputs.now`."""
    for src in ("datetime.now(timezone.utc)\n", "datetime.datetime.utcnow()\n", "date.today()\n", "time.time()\n",
                "time.perf_counter()\n", "time.monotonic_ns()\n", "from time import time\n",
                "import time as t\nx = t.time()\n", "from datetime import datetime as dt\nx = dt.now()\n",
                "def main():\n    return datetime.now()\n", "def f(clock=date.today()):\n    pass\n",
                "x = np.datetime64('now')\n", "x = numpy.datetime64('today', 'D')\n", "from uuid import uuid1\n",
                "from numpy import datetime64\nx = datetime64('now')\n", "import uuid\nx = uuid.uuid1()\n",
                "import email.utils\nx = email.utils.localtime()\n", "import uuid as u\nx = u.uuid1()\n",
                "from email import utils\nx = utils.formatdate()\n", "import email.utils as eu\nx = eu.localtime()\n",
                "from email.utils import formatdate\n", "x = pd.Timestamp.now()\n", "x = pd.Timestamp('today')\n",
                "from email import utils as eu\nx = eu.localtime()\n",
                "import time\ndef _u():\n    from email import utils as time\nx = time.time()\n",
                "import time\ndef _u():\n    import email.utils as time\nx = time.time()\n",
                "import time as t\ndef _u():\n    from email import utils as t\nx = t.time()\n",
                "import time as t\ndef _u():\n    import email.utils as t\nx = t.time()\n",
                "import email.utils as eu\ndef _u():\n    from datetime import date as eu\nx = eu.localtime()\n"):
        assert _clock_hits_in(X, src), src
    for src in ("from pandas import Timestamp as T\nx = T('now')\n",
                "from numpy import datetime64 as d\nx = d('today')\n"):
        assert _clock_hits_in(X, src), src
    main = "def main():\n    return datetime.now(timezone.utc)\n"
    assert _clock_hits_in(XD, main, allowed=(RUN,)) and not _clock_hits_in(RUN, main, allowed=(RUN,))
    assert _clock_hits_in(RUN, "def main(today=date.today()):\n    pass\n", allowed=(RUN,))   # a default runs at import
    assert not _clock_hits_in(X, "d = now.astimezone(KST).date()\nt = datetime.fromisoformat(s)\nimport time\n"
                                 "e = np.datetime64('2026-10-23')\nu = uuid.uuid4()\nfrom uuid import uuid4\n"
                                 "from datetime import datetime, date\nw = email.utils.parsedate_to_datetime(s)\n")
    hits = [h for rel, src in _files(ODDS).items() for h in _clock_hits_in(rel, src)]
    assert not hits, hits


def test_core_odds_has_no_main_block():
    """No core/odds file holds a `__main__` test in either operand order (T-CTX-01 skips such bodies, and the core is
    run only through core.oddsdata.run); the one exact block allowed elsewhere is checked by the same checker."""
    exact = 'if __name__ == "__main__":\n    raise SystemExit(main())\n'
    for src in (exact, "if '__main__' == __name__:\n    main()\n", 'if __name__ != "__main__":\n    pass\n',
                'def f():\n    if __name__ == "__main__":\n        pass\n', 'x = __name__ == "__main__"\n',
                "match __name__:\n    case '__main__':\n        main()\n"):
        assert _main_hits(X, src), src
    assert _main_hits(X, "match (__name__,):\n    case ('__main__',):\n        main()\n")
    assert not _main_hits(RUN, exact, allowed=(RUN,))
    assert not _main_hits(X, "name = __name__\nmain = '__main__'\nmatch name:\n    case '__main__':\n        pass\n")
    hits = [h for rel, src in _files(ODDS).items() for h in _main_hits(rel, src)]
    assert not hits, hits


def test_core_odds_does_no_file_io():
    """Every table reaches the core only through the sealed Context of owner.load_context (O2): no file-I/O module
    (builtins, scipy.io and numpy's npyio and format among them), no _IO_ATTRS name imported from any module, no
    `open` (bare, io.open, os.open, Path.open) and no `__builtins__`, no Path read or write call, no numpy file call,
    no os.replace. The only I/O the core reaches is through owner.calendar_in_force (Q19, Q42)."""
    for src in ("f = open(p)\n", "with open(p, 'w') as fh:\n    pass\n", "g = open\n", "io.open(p)\n",
                "os.open(p, 0)\n", "p.open()\n", "p.read_text(encoding='utf-8')\n", "p.read_bytes()\n",
                "p.write_text(s, encoding='utf-8')\n", "p.write_bytes(b)\n", "p.mkdir()\n", "p.unlink()\n",
                "p.rename(q)\n", "os.replace(a, b)\n", "np.load(p)\n", "np.save(p, a)\n", "np.savez(p, a=a)\n",
                "np.savez_compressed(p, a=a)\n", "np.loadtxt(p)\n", "np.savetxt(p, a)\n", "np.genfromtxt(p)\n",
                "np.fromregex(p, r, d)\n", "np.fromfile(p)\n", "a.tofile(p)\n", "np.memmap(p)\n",
                "np.lib.format.open_memmap(p)\n", "def f():\n    import lzma\n", "import os.path\n",
                "from io import BytesIO\n", "from numpy import load\nx = load(p)\n",
                "from numpy import fromfile, memmap\n", "from builtins import open as o\n",
                "import builtins\nf = builtins.open\n", "f = __builtins__.open\n", "from scipy.io import loadmat\n",
                "import scipy.io\n", "import numpy.lib.format as F\nF.open_memmap(p)\n",
                "from numpy.lib._format_impl import open_memmap\n", "from json import load\n"):
        assert _core_io_hits(X, src), src
    for module in _FILE_MODULES:
        for src in (f"import {module}\n", f"from {module} import x\n"):
            assert _core_io_hits(X, src), src
    assert not _core_io_hits(X, "s = t.replace('a', 'b')\nd = dataclasses.replace(c, n=1)\nj = json.loads(s)\n"
                                "x = np.asarray(v)\nimport json, hashlib\nimport iox_notes\nr = report.render(x)\n"
                                "from json import loads\nfrom core.compliance.owner import load_context\n"
                                "import scipy\nfrom scipy import stats\n")
    assert not _core_io_hits(X, "class Series:\n    open: tuple[float, ...]\n"      # plan.Series (contract 5.2)
                                "s = Series(open=(1.0,))\nfirst = s.open[0]\nm = np.log(s.close) - np.log(s.open)\n")
    hits = [h for rel, src in _files(ODDS).items() for h in _core_io_hits(rel, src)]
    assert not hits, hits


def test_core_odds_imports_no_package_reexport():
    """Concrete submodules only (O2): a name taken from a package (`import core.odds`, `from core.compliance import
    <a name that is no module file>`) is whatever that package's __init__ makes of it (core/engine/__init__.py hands
    out orders' OrderBook, core/calendars/__init__.py holds code), so no scan can tell which file it comes from."""
    for src in ("import core\n", "import core.odds\n", "import core.compliance\n", "import core.oddsdata\n",
                "import core.compliance as C\n", "from core import odds\n", "from core import compliance\n",
                "from core.compliance import approved_state\n", "from core.odds import nosuch\n",
                "from . import nosuch\n", "from core.calendars import is_trading_day\n",
                "from core.engine import OrderBook\n"):
        assert _reexport_hits(X, src), src
    assert not _reexport_hits(X, "from core import isolation\nfrom core.compliance import gate, model, owner, rules\n"
                                 "from core.compliance.rules import Venue\nimport core.compliance.rules\n"
                                 "import core.isolation\nfrom ..compliance import model\nimport numpy\n"
                                 "from scipy import stats\n")
    tree = _probe_tree("odds_tree", {"core/odds/plan.py": ""})
    assert not _reexport_hits(X, "from . import plan\nfrom core.odds import plan\n", root=tree)
    hits = [h for rel, src in _files(ODDS).items() for h in _reexport_hits(rel, src)]
    assert not hits, hits


def test_core_odds_is_flat():
    """Q1 and O1: core/odds holds only __init__.py, plan, costs, models, simulate, bold and report, venues.yaml and
    __pycache__, and no subfolder holds a .py file: owner.code_files seeds core/odds/*.py with a non-recursive glob
    (the `for sub in ("compliance", "odds")` seed), so a nested file would run unsigned."""
    probe = _probe_tree("flat_probe", {"plan.py": "", "venues.yaml": "", "notes.txt": "", "sub/b.py": ""})
    assert _layout_hits(probe) == ["notes.txt", "sub", "sub/b.py"], _layout_hits(probe)
    assert (ODDS / "__init__.py").is_file(), "core/odds/__init__.py missing"
    assert not _layout_hits(ODDS), _layout_hits(ODDS)


def test_package_inits_are_empty():
    """core/odds/__init__.py and core/oddsdata/__init__.py exist and are 0 bytes (O1, O13): under the trailing-dot
    acting prefix the package module itself is not acting, so it may hold no code."""
    probe = _probe_tree("init_probe", {"__init__.py": "\n"})
    assert CG._init_hits(probe / "__init__.py") and CG._init_hits(probe / "missing.py")
    for init in (ODDS / "__init__.py", ODDSDATA / "__init__.py"):
        assert not CG._init_hits(init), f"{init.relative_to(ROOT).as_posix()} must exist and be 0 bytes"


# --------------------------------------------------------------------------- #
# core/oddsdata: the unsigned loaders and the CLI
# --------------------------------------------------------------------------- #
def test_oddsdata_raw_words():
    """compliance_guards._raw_hits over core/oddsdata, docstrings and comments included (the compliance raw-word test
    scans core/compliance and core/odds only; core/oddsdata is a sibling)."""
    for needle in tuple(CG.RAW_CI) + tuple(CG.RAW_CS):
        assert CG._raw_hits(XD, f'"""{needle}"""\n'), needle
    assert not CG._raw_hits(XD, "canonical_json, cache_dir, checked_target, transfer_out\n")
    hits = [h for rel, src in _files(ODDSDATA).items() for h in CG._raw_hits(rel, src)]
    assert not hits, hits


def test_oddsdata_never_imports_orders_or_the_study():
    """O1, O2, R2-6: no core.engine module in any form (core/engine/__init__.py imports orders), no forward_sim,
    refusal or context-log module (compliance_guards.FORBIDDEN_MODULES), never the study runner, never
    core.quant.gate_ledger or core.ficc.macro_artifacts (their repo_anchor and tree_hash are copied into
    core/oddsdata/inputs.py), and no star or dynamic import. A direct-import scan: what an allowed module imports in
    turn is not seen here."""
    for src in ("from core.engine import orders\n", "import core.engine.orders as o\n",
                "from core.engine import books\n", "import core.engine\n", "from core import engine\n",
                "def f():\n    from core.engine.risk import x\n",
                "from core.quant import forward_sim\n", "from core.quant.refusal import y\n",
                "from core.ficc import context_log\n", "import core.ficc.flows_log\n", "from core.ficc import macro\n",
                "import core.skills.macro_daily\n", "import docs.asset_expansion_study\n",
                "from docs import asset_expansion_study\n", "import asset_expansion_study\n",
                "from core.quant import gate_ledger\n", "import core.ficc.macro_artifacts\n",
                "from core.ficc.macro_artifacts import tree_hash\n", "from ..quant import gate_ledger\n",
                "import importlib\n", "m = __import__('x')\n", "exec(s)\n", "from math import *\n", "import pickle\n",
                "import pstats\n"):
        assert _data_import_hits(XD, src), src
    assert not _data_import_hits(XD, "from core.quant import garch, instruments, validate, strategies\n"
                                     "from core.calendars import clocks, regime, store\n"
                                     "from data.krx import kis_client\n"
                                     "from data.crypto import crypto_client\nimport yfinance\n"
                                     "from core.ficc import macro_schema\nfrom core.compliance import model, owner\n"
                                     "import core.enginex\nimport importlib.metadata\nimport csv, json, os\n")
    hits = [h for rel, src in _files(ODDSDATA).items() for h in _data_import_hits(rel, src)]
    assert not hits, hits


def test_oddsdata_clock_only_in_run_main():
    """O15: the wall clock is read only in the body of core/oddsdata/run.py's main(); bars, inputs and replay take
    `now` as an argument."""
    main = "def main(argv=None, *, now=None):\n    now = now or datetime.now(timezone.utc)\n"
    assert _clock_hits_in(XD, main, allowed=(RUN,)) and not _clock_hits_in(RUN, main, allowed=(RUN,))
    for src in ("def load(now=datetime.now()):\n    pass\n", "def other():\n    return time.time()\n",
                "STARTED = datetime.now()\n", "from time import monotonic\n",
                "def other():\n    return pd.Timestamp.now(tz='UTC')\n", "def other():\n    return uuid.uuid1()\n",
                "from pandas import Timestamp as T\ndef other():\n    return T.now()\n"):
        assert _clock_hits_in(RUN, src, allowed=(RUN,)), src
    hits = [h for rel, src in _files(ODDSDATA).items() for h in _clock_hits_in(rel, src, allowed=(RUN,))]
    assert not hits, hits


def test_oddsdata_main_block_only_in_run():
    """The only `__main__` block in core/oddsdata is run.py's, exactly `raise SystemExit(main())` at the top level
    (contract section 0; T-CTX-01 skips such bodies)."""
    exact = 'if __name__ == "__main__":\n    raise SystemExit(main())\n'
    assert _main_hits(XD, exact, allowed=(RUN,)) and not _main_hits(RUN, exact, allowed=(RUN,))
    for src in ('if __name__ == "__main__":\n    main()\n',
                'if __name__ == "__main__":\n    import sys\n    raise SystemExit(main())\n',
                exact + "else:\n    pass\n", "if '__main__' == __name__:\n    raise SystemExit(main())\n",
                'def g():\n    if __name__ == "__main__":\n        raise SystemExit(main())\n',
                "match __name__:\n    case '__main__':\n        raise SystemExit(main())\n"):
        assert _main_hits(RUN, src, allowed=(RUN,)), src
    hits = [h for rel, src in _files(ODDSDATA).items() for h in _main_hits(rel, src, allowed=(RUN,))]
    assert not hits, hits


def test_oddsdata_writes_only_checked_targets():
    """O2: every file write in core/oddsdata (open with a mode holding w, a, x or +, or a mode that is not a constant;
    .write_text, .write_bytes, .mkdir, .touch, .unlink, .rmdir, .symlink_to, .hardlink_to, .tofile; Path.replace(t)
    and Path.rename(t); the os, shutil and numpy functions that write, rename or delete, under any import alias)
    comes after a call to checked_target in the same function (core.isolation.checked_target refuses QUANTGEN, links
    and files that would change another file)."""
    for src in ("def f(p):\n    p.write_text('x', encoding='utf-8')\n",
                "def f(p):\n    p.write_bytes(b'')\n    checked_target(p, 'x')\n",
                "def f(p):\n    with open(p, 'w', encoding='utf-8') as fh:\n        fh.write('x')\n",
                "def f(p):\n    open(p, 'a', encoding='utf-8')\n", "def f(p):\n    open(p, mode='x')\n",
                "def f(p):\n    open(p, 'r+b')\n", "def f(p, m):\n    open(p, m)\n", "def f(p):\n    p.open('wb')\n",
                "def f(a, b):\n    os.replace(a, b)\n", "def f(a, b):\n    os.rename(a, b)\n",
                "def f(p):\n    p.mkdir(parents=True, exist_ok=True)\n", "Path('x').write_text('y')\n",
                "def f(p):\n    checked_target(p, 'x')\n    def g():\n        p.write_text('y')\n    g()\n",
                "def f(p, t):\n    p.replace(t)\n", "def f(p, t):\n    p.rename(t)\n", "def f(p):\n    p.touch()\n",
                "def f(p):\n    p.unlink(missing_ok=True)\n", "def f(p):\n    p.rmdir()\n",
                "def f(p, t):\n    p.symlink_to(t)\n", "def f(p, t):\n    p.hardlink_to(t)\n",
                "def f(d):\n    os.makedirs(d, exist_ok=True)\n", "def f(p):\n    os.remove(p)\n",
                "def f(a, b):\n    os.link(a, b)\n", "import shutil\ndef f(a, b):\n    shutil.copyfile(a, b)\n",
                "import shutil as sh\ndef f(d):\n    sh.rmtree(d)\n",
                "from shutil import move\ndef f(a, b):\n    move(a, b)\n",
                "import numpy as np\ndef f(p, a):\n    np.save(p, a)\n", "def f(p, a):\n    a.tofile(p)\n",
                "import os as o\ndef f(a, b):\n    o.replace(a, b)\n",
                "from os import replace\ndef f(a, b):\n    replace(a, b)\n",
                "from io import open as o\ndef f(p):\n    o(p, 'w')\n",
                "def f(p):\n    Path(p).open('a', encoding='utf-8')\n"):
        assert _unchecked_write_hits(XD, src), src
    for src in ("def f(p, d):\n    checked_target(p, 'x', within=d)\n    p.write_text('y', encoding='utf-8')\n",
                "def f(p):\n    with open(checked_target(p, 'x'), 'w', encoding='utf-8') as fh:\n"
                "        fh.write('y')\n",
                "def f(p):\n    isolation.checked_target(p, 'x').write_bytes(b'')\n",
                "def f(p, t):\n    checked_target(p, 'x')\n    checked_target(t, 'x')\n    t.write_bytes(b'')\n"
                "    os.replace(t, p)\n",
                "def f(p):\n    a = open(p, encoding='utf-8')\n    b = open(p, 'rb')\n    c = p.open()\n"
                "    d = p.read_text(encoding='utf-8')\n    return s.replace('a', 'b'), now.replace(tzinfo=None)\n",
                "import dataclasses\nfrom dataclasses import replace\nimport numpy as np\n"
                "c2, c3 = dataclasses.replace(c), replace(c)\nx = np.load(p)\nq = os.path.join(a, b)\n"):
        assert not _unchecked_write_hits(XD, src), src
    for src in ("import shutil as sh\ndef hidden():\n    import json as sh\nsh.rmtree(d)\n",
                "from shutil import move as m\ndef hidden():\n    from json import loads as m\nm(a, b)\n",
                "from io import open as o\ndef hidden():\n    import json as o\no(p, 'w')\n"):
        assert _unchecked_write_hits(XD, src), src
    hits = [h for rel, src in _files(ODDSDATA).items() for h in _unchecked_write_hits(rel, src)]
    assert not hits, hits


# --------------------------------------------------------------------------- #
# The D14 closure (O1)
# --------------------------------------------------------------------------- #
def test_code_closure_holds_no_data_layer():
    """O1: the D14 closure (owner.code_files: core/compliance/*.py, core/odds/*.py and every in-repo file they import
    at any depth) holds no file under core/oddsdata/, data/, core/quant/, core/calendars/ or core/engine/, and not
    config.py. A seeded core/odds file that imports core.oddsdata, even inside a function, pulls it and what it imports
    in (the positive control, on a synthetic tree)."""
    from core.compliance import owner
    root = _probe_tree("code_tree", {
        "config.py": "", "core/__init__.py": "", "core/odds/__init__.py": "",
        "core/odds/x.py": "def f():\n    from core.oddsdata import bars\n    return bars\n",
        "core/oddsdata/__init__.py": "", "core/oddsdata/bars.py": "import config\nfrom core.quant import garch\n",
        "core/quant/__init__.py": "", "core/quant/garch.py": ""})
    names = [n for n, _ in owner.code_files(root)]
    assert _closure_hits(names) == ["config.py", "core/oddsdata/__init__.py", "core/oddsdata/bars.py",
                                    "core/quant/__init__.py", "core/quant/garch.py"], names
    real = [n for n, _ in owner.code_files(ROOT)]
    assert "core/odds/__init__.py" in real, "core/odds/__init__.py is not in the closure: is the odds seed gone?"
    assert not _closure_hits(real), _closure_hits(real)


# --------------------------------------------------------------------------- #
# Registration (the odds twin of compliance_guards.test_suite_is_registered_in_run_all_and_readme)
# --------------------------------------------------------------------------- #
def test_suite_is_registered_in_run_all_and_readme():
    """`tests/run_all.py --suite odds` selects this suite, and both hand-written suite lists (the --suite help text and
    the README verification block) name it; compliance_guards._suite_names reads the lists (follow-up R7)."""
    from tests import run_all
    names = [n for n, _f in run_all.select(run_all.tests(), suite="odds")]
    assert any(n.startswith("odds/odds_guards/") for n in names), names
    assert "odds" not in CG._suite_names("x  # one suite: grokteam or compliance\n")
    for path in (ROOT / "tests" / "run_all.py", ROOT / "README.md"):
        assert "odds" in CG._suite_names(path.read_text(encoding="utf-8")), path.name


# --------------------------------------------------------------------------- #
# The harness itself (the odds twins of the three compliance self-tests)
# --------------------------------------------------------------------------- #
def test_suite_runs_hermetic_in_a_temp_home_with_the_seams_patched():
    """The wrapper arms the hermetic guard and points TRADEGEN_HOME at a fresh temp dir; a nested wrapped call arms
    one more level, moves the home and undoes both. Once core/oddsdata/bars.py exists every seam is the raising stub
    inside a test and REAL_SEAMS holds the real functions. The patch itself is checked on a stand-in bars module with
    one seam missing: inside, every seam raises; afterwards each is back and the missing one is gone again."""
    from tests import macro_acceptance as MA
    from tests import odds_acceptance as OA
    home = Path(os.environ["TRADEGEN_HOME"])
    assert MA._DEPTH > 0, "the hermetic guard is not armed"
    assert home.is_dir() and home.name.startswith("tradegen_home_"), home
    assert not home.resolve().is_relative_to((Path.home() / ".tradegen").resolve()), home
    seen = []
    OA._wrap(lambda: seen.append((MA._DEPTH, Path(os.environ["TRADEGEN_HOME"]))))()
    depth, inner = seen[0]
    assert depth == MA._DEPTH + 1 and inner != home and inner.name.startswith("tradegen_home_"), seen
    assert Path(os.environ["TRADEGEN_HOME"]) == home and not inner.exists(), seen
    if OA._BARS.is_file():                              # Task 15 on: this very test runs with the real seams patched
        bars = sys.modules["core.oddsdata.bars"]
        assert all(vars(bars)[s] is MA._boom for s in OA.SEAMS), "a bars seam is not patched"
        assert sorted(OA.REAL_SEAMS) == sorted(OA.SEAMS), OA.REAL_SEAMS
        assert all(f is not MA._boom for f in OA.REAL_SEAMS.values()), OA.REAL_SEAMS

    def real(*_a, **_k):
        return "real"
    fake = types.ModuleType("core.oddsdata.bars")
    for name in OA.SEAMS[:-1]:
        setattr(fake, name, real)
    probe = home / "bars.py"
    probe.write_bytes(b"")
    keep = OA._BARS, dict(OA.REAL_SEAMS), sys.modules.get("core.oddsdata.bars", MA._MISSING)
    inside = {}
    try:
        OA._BARS = probe
        OA.REAL_SEAMS.clear()
        sys.modules["core.oddsdata.bars"] = fake
        OA._wrap(lambda: inside.update(vars(fake)))()
        recorded = dict(OA.REAL_SEAMS)
    finally:
        OA._BARS = keep[0]
        OA.REAL_SEAMS.clear()
        OA.REAL_SEAMS.update(keep[1])
        if keep[2] is MA._MISSING:
            sys.modules.pop("core.oddsdata.bars", None)
        else:
            sys.modules["core.oddsdata.bars"] = keep[2]
    assert all(inside[name] is MA._boom for name in OA.SEAMS), inside
    assert all(vars(fake)[name] is real for name in OA.SEAMS[:-1]) and OA.SEAMS[-1] not in vars(fake), vars(fake)
    assert recorded == {name: real for name in OA.SEAMS[:-1]}, recorded


def test_harness_flags_a_change_to_the_real_homes_and_the_read_only_repo_files():
    """The wrapper fails a test that changes the real ~/.tradegen/odds or ~/.tradegen/compliance (a new file or folder
    in either) or a repo file the suite only reads (venues.yaml, the S_C3 cache, card and results.csv); stand-ins in
    the temp home take their place here."""
    from tests import odds_acceptance as OA
    base = _probe_tree("watch", {"real_odds/.keep": "", "real_compliance/.keep": "", "card.json": "{}"})
    odds, comp, card = base / "real_odds", base / "real_compliance", base / "card.json"
    keep, flagged = (OA._REAL_HOMES, OA._REPO_FILES), []
    try:
        OA._REAL_HOMES, OA._REPO_FILES = (odds, comp), (card.as_posix(),)   # absolute: TESTS.parent / it is itself
        OA._wrap(lambda: None)()                                            # nothing changed: passes
        for change in (lambda: (odds / "state.json").write_bytes(b"{}\n"),
                       lambda: (comp / "owner.jsonl").write_bytes(b"{}\n"),
                       lambda: (comp / "store").mkdir(),
                       lambda: card.write_bytes(b'{"edited": true}')):
            try:
                OA._wrap(change)()
            except AssertionError as exc:
                flagged.append(str(exc).split(":", 1)[0])
            else:
                flagged.append("not flagged")
    finally:
        OA._REAL_HOMES, OA._REPO_FILES = keep
    assert flagged == ["the test touched the real ~/.tradegen/odds or compliance"] * 3 + [
        "the test changed a repo file it may only read"], flagged


def test_aggregator_skips_missing_and_isolates_broken_modules():
    """Contract section 3.1: an absent module is skipped, one that fails to import becomes a single `<module>/import`
    entry that re-raises, a `test_*` name imported from elsewhere is not collected, and an empty run exits 1."""
    from tests import odds_acceptance as OA
    from tests.compliance_fixtures import temp_home as imported
    probe = _probe_tree("probe", {"odds_broken.py": "", "odds_mixed.py": ""})

    def own():
        pass
    mixed = types.ModuleType("tests.odds_mixed")
    own.__module__ = mixed.__name__
    mixed.test_own, mixed.test_imported = own, imported
    keep = OA.TESTS, OA.MODULES
    sys.modules.update({"tests.odds_broken": None, "tests.odds_mixed": mixed})   # None: the import raises
    try:
        OA.TESTS, OA.MODULES = probe, ("odds_broken", "odds_absent", "odds_mixed")
        found = OA.tests()
    finally:
        OA.TESTS, OA.MODULES = keep
        for stem in ("odds_broken", "odds_mixed"):
            sys.modules.pop(f"tests.{stem}", None)
    assert [n for n, _f in found] == ["odds_broken/import", "odds_mixed/test_own"], found
    try:
        found[0][1]()
    except ImportError:
        pass
    else:
        raise AssertionError("the broken module's entry did not re-raise its import error")
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = OA._main(["no such test"])
    assert code == 1 and out.getvalue().strip() == "0/0 passed, 0 failed, 0 not run", (code, out.getvalue())


def test_chunk_and_pilots_swap_their_sizes_and_restore_them():
    """tests/odds_fixtures (contract 3.2): chunk() sets simulate.CHUNK, every DEFAULT_PATHS track and GARCH_SUB (never
    above its own value); pilots() sets models.PILOT_PATHS, simulate.TILT_PILOT and models.PILOT_NODES; both put every
    value back, after an exception too. Run on stand-in modules, so it holds before simulate.py exists and leaves the
    real modules alone after."""
    from tests import odds_fixtures as OF
    sim, mod = types.ModuleType("core.odds.simulate"), types.ModuleType("core.odds.models")
    defaults = {"moonshot": 1_000_000, "compounding": 200_000}
    sim.CHUNK, sim.DEFAULT_PATHS, sim.GARCH_SUB, sim.TILT_PILOT = 200_000, defaults, 20_000, 20_000
    mod.PILOT_PATHS, mod.PILOT_NODES = 20_000, 512
    missing = object()
    keep = {name: sys.modules.get(name, missing) for name in (sim.__name__, mod.__name__)}
    seen = []
    try:
        sys.modules.update({sim.__name__: sim, mod.__name__: mod})
        with OF.chunk():
            seen.append((sim.CHUNK, sim.DEFAULT_PATHS, sim.GARCH_SUB))
        with OF.chunk(50_000):
            seen.append((sim.CHUNK, sim.DEFAULT_PATHS, sim.GARCH_SUB))
        with OF.pilots():
            seen.append((mod.PILOT_PATHS, sim.TILT_PILOT, mod.PILOT_NODES))
        try:
            with OF.chunk(), OF.pilots(500, 16):
                seen.append((sim.CHUNK, mod.PILOT_PATHS, sim.TILT_PILOT, mod.PILOT_NODES))
                raise KeyError("inside")
        except KeyError:
            pass
        after = (sim.CHUNK, sim.DEFAULT_PATHS, sim.GARCH_SUB, mod.PILOT_PATHS, sim.TILT_PILOT, mod.PILOT_NODES)
    finally:
        for name, module in keep.items():
            if module is missing:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = module
    assert seen == [(2_000, {"moonshot": 2_000, "compounding": 2_000}, 2_000),
                    (50_000, {"moonshot": 50_000, "compounding": 50_000}, 20_000),
                    (2_000, 2_000, 64), (2_000, 500, 500, 16)], seen
    assert after == (200_000, defaults, 20_000, 20_000, 20_000, 512) and after[1] is defaults, after
    assert defaults == {"moonshot": 1_000_000, "compounding": 200_000}, defaults
