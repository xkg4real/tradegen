### Task 1: Branch and guards: xml.dom, string-exec modules, bare compile, the suite-list check

**Files:**
- Modify: `tests/compliance_guards.py` (LF; anchors: the module's import block; the constant `NETWORK_MODULES`; the
  dynamic-import comment and constants between `FORBIDDEN_MODULES` and `# base name -> attributes that read the
  clock`; the checker `_dynamic_hits`; the tests `test_no_http_verb_calls`, `test_no_forbidden_module_import`,
  `test_imports_stay_on_the_allowlist` and `test_suite_is_registered_in_run_all_and_readme`)
- Test: `tests/compliance_guards.py` (the guards are their own tests; 15 tests become 16)

No product file and no table changes. `tests/` is outside the D14 closure, so the code hash does not move.

**Interfaces:**
- Consumes (existing names in `tests/compliance_guards.py`, unchanged): `ROOT`, `X`, `COMPLIANCE`, `ODDS`,
  `_scope(*bases)`, `_walk(node)`, `_imports(rel, tree)` (yields `(node, absolute module, imported names, enclosing
  functions)`), `_forbidden_hits`, `_allowlist_hits(rel, src)` (keeps its own `[module] + [module.n]` targets),
  `DYNAMIC_NAMES` (unchanged); `tests.run_all.select(entries, suite="compliance")` and `tests.run_all.tests()`.
- Produces (Appendix A section 3.10; the odds guards import these and never copy them):
  - `NETWORK_MODULES`: 26 entries; `DYNAMIC_MODULES`: 29 entries; `DYNAMIC_NAMES`: unchanged;
    `DYNAMIC_BARE = frozenset({"compile"})`; `DYNAMIC_EXEMPT = "importlib.metadata"`.
  - `_dynamic_module(target: str) -> bool`: True for a dotted import target equal to or below a `DYNAMIC_MODULES`
    entry, False for `importlib.metadata` and everything below it. An import target is tested with this function,
    never with a raw prefix match over `DYNAMIC_MODULES` (`importlib` is an entry, so a raw match would drop
    `importlib.metadata`).
  - `_dynamic_hits(rel: str, src: str) -> list[str]`: signature unchanged. New hit texts:
    `"<rel>:<line>: importlib.<attr>"` and `"<rel>:<line>: compile"`.
  - `_suite_names(text: str) -> list[str]` (Appendix A sections 3.9 and 3.10). The odds guards do not import it, but
    the E1 plan's `tests/execution_guards.py` does, as `CG._suite_names`, in its registration test (the E1 plan's
    Appendix A sections 0.6 and 4.5), so its name and signature are fixed like the names of Appendix A section 3.10.
    The odds plan adds `odds` to the two suite lists without touching a compliance test.
  - New test `test_bare_compile_and_importlib_submodules_are_dynamic`. No name is renamed or removed.

**Plan decisions used:** R1 (as amended by round-2 ruling R2-10), R7, R9, R13 (as amended by R2-11); the drift rule
(R2-13) of Global Constraints.

Notes (read before Step 1):
- What the new bans close (repo map `followup` section 1; each was checked in the venv's own stdlib sources):
  - `xml.dom` as one package: `xml.dom.xmlbuilder`'s `DOMBuilder.parseURI` opens a URL with `urllib.request`, and
    both `minidom` and the bare `xml.dom.getDOMImplementation()` hand that builder out. So
    `from xml.dom import minidom` leaves the negative control and becomes a positive one.
  - `antigravity` opens a URL at import; `ctypes` and `_ctypes` call any DLL; `_ssl` and `_overlapped` are the C
    halves of `ssl` and asyncio's Windows transport.
  - The dynamic modules run code named in a string or read from data. `profile`, `pdb`, `bdb`, `trace` and
    `doctest` exec a string. `unittest` imports by string (mock.patch targets, the loader). `logging.config` builds
    classes from strings and runs a TCP listener. `pickle`, `_pickle`, `shelve` and `marshal` load objects and code
    from bytes. `site` execs `.pth` lines. `ensurepip` and `venv` run pip through runpy. `tkinter`, `_tkinter`,
    `turtle`, `turtledemo` and `idlelib` embed a Tcl interpreter with sockets (idlelib also execs). `pstats` and
    `tracemalloc` (R2-10) load files with marshal and pickle (`pstats.Stats`, `tracemalloc.Snapshot.load`).
  - `importlib` as a whole except `importlib.metadata` (R9): the bare `import importlib` is dynamic, and so are
    `importlib.resources`, `importlib.abc` and `importlib._bootstrap`. `import importlib.metadata` binds the name
    `importlib`, so any attribute of that name except `metadata` is a hit too (`importlib.util.spec_from_file_location`
    would otherwise load a file with no banned import). In the dynamic scan only, `from X import a` is judged by `X.a`,
    so `from importlib import metadata` stays legal; every other entry is still caught in every import form.
  - The bare builtin `compile` is banned as an `ast.Name` only (a call, a reference or a rebinding), so every
    `re.compile` in core/compliance (rules.py:155, :190, :383-386, owner.py:75-78, alerts.py:25-28) stays legal.
- What stays open, named as left to review (the counts of R1 are binding; banning more needs a controller ruling):
  `codeop` and `dis` compile a string (`codeop.compile_command`, `dis.Bytecode(src).codeobj`) that
  `types.FunctionType` runs; `_frozen_importlib` and `_frozen_importlib_external` are `importlib._bootstrap` and
  `importlib._bootstrap_external` under their sys.modules names (`SourceFileLoader(name, path).get_code(name)` loads a
  file), and `_imp.create_dynamic` loads an extension module; `_interpreters.run_string` runs a string. All six are in
  `sys.stdlib_module_names`, so the allowlist passes them; no file under core/, tools/ or tests/ imports one. The
  Edit 8 comment names them. Likewise `sqlite3`'s `Connection.load_extension` loads any DLL by path, as ctypes does;
  the Edit 10 docstring names it under "Not covered".
- Wording that differs from Appendix A (the task wins): Edit 8's comment reads "(importlib.util,
  importlib._bootstrap)" with no trailing ellipsis and adds the left-to-review sentence above; Edit 10's docstring
  adds the sqlite3 clause and ends "All three are left to review"; Edit 6's `_suite_names` docstring says
  "a, b or c" where Appendix A section 3.9 has a longer example. Behaviour is the same.
- What stays allowed, as negative controls: `import logging`, `from logging import getLogger`, `xml.etree`,
  `subprocess` (the P26 toast), `importlib.metadata` (owner.py reads the RECORD files with it), `faulthandler` (it
  runs no string and opens nothing), `traceback` (the `trace` ban must not catch a longer name) and `re.compile`.
- Scope is unchanged: `NETWORK_MODULES` binds core/compliance only (`test_imports_stay_on_the_allowlist`);
  `DYNAMIC_*` binds core/compliance and core/odds (`test_no_forbidden_module_import`). Checked in-process on
  2026-10-24 with exactly the code below: the six core/compliance files give no hit, and neither does Task 2's
  rules.py; core/odds holds no .py file yet.
- R7 is a test refactor: the new registration test passes before and after the list changes. Its own positive
  controls (a list without `compliance`, a text with no list) prove the parser. It needs `import re`, so the import
  goes in Step 1.
- Every Edit below is an exact old/new pair quoted from the tree at `5816d3c` (equal to `995534b` outside docs/) with
  its anchor. Before each Edit, re-read the file; if the old text is not found exactly once, apply the drift rule of
  Global Constraints. This plan runs first, so outside docs/ no earlier plan has changed this file (Step 1a checks it).

- [ ] **Step 1: Check the base, create the branch, then write the failing tests**

  **1a. The base (R13, R2-11).** From the repo root in Git Bash:

```bash
git branch --show-current
git status --short
git diff --stat 995534b HEAD -- . ':!docs'
```

  Expected: `main`, then nothing, then nothing. Since `995534b` only docs commits have landed on main: the E1 spec
  (`5816d3c`) and the docs commits of this plan, the odds plan and the E1 plan. If the first command prints another
  branch, run `git switch main` and repeat. The one `git status --short` line allowed is
  `?? docs/superpowers/plans/2026-10-24-compliance-followup-execution-ledger.md` (the executor's untracked ledger, if
  already started). If either of the other two commands prints anything else, stop and report to the controller:
  every line number and count in this plan rests on that tree. Then:

```bash
git switch -c compliance-followup
git ls-files --eol tests/compliance_guards.py
```

  Expected: `Switched to a new branch 'compliance-followup'`, then a line starting `i/lf    w/lf    attr/-text`. If
  `git switch -c` reports that `compliance-followup` already exists, stop and report; never `git switch -C`, and never
  delete the branch.

  **1b. The tests.** Six Edit-tool replacements in `tests/compliance_guards.py` (LF, kept). They add the positive
  and negative controls, the new test, the R7 helper and `import re`. The lists themselves change in Step 3.

  Edit 1. Anchor: the module's import block (guards:12-18). Old text:

```python
import io
import os
import sys
```

  New text:

```python
import io
import os
import re
import sys
```

  Edit 2. Anchor: test_no_forbidden_module_import, its docstring (guards:273-276). Only the docstring's last two lines
  change ("or bare compile()"). Old text:

```python
def test_no_forbidden_module_import():
    """core.engine.orders in every form (T-RO-01 misses `from core.engine import orders`), the forward simulator,
    the refusal legs and the protected context modules, at module or function level; and no star or dynamic import,
    which would hide one from this scan and load code the D14 closure never signed (P6)."""
```

  New text:

```python
def test_no_forbidden_module_import():
    """core.engine.orders in every form (T-RO-01 misses `from core.engine import orders`), the forward simulator,
    the refusal legs and the protected context modules, at module or function level; and no star or dynamic import
    or bare compile(), which would hide one from this scan and load code the D14 closure never signed (P6)."""
```

  Edit 3. Anchor: test_no_forbidden_module_import, the explicit dynamic positives, the module loop and the negative
  control (guards:284-297). The explicit list gains the motivating positives of every new entry (`import pstats`,
  `from pstats import Stats`, `import tracemalloc` and `from tracemalloc import Snapshot` among them, R2-10; the old
  `import importlib.util` and `from importlib import util` stay). The module loop is unchanged and covers every tuple
  entry in three import forms. A second negative control follows the first: traceback, faulthandler, logging and
  `re.compile` are not banned, and pstats and tracemalloc are not in it. Old text:

```python
    for src in ("from core.engine import *\n", "from core.compliance.model import *\n",
                "import importlib\nm = importlib.import_module('numpy')\n", "m = __import__('numpy')\n",
                "from importlib import import_module as im\n", "import importlib.util\n",
                "from importlib import util\n", "import runpy\n", "import pkgutil\n", "exec(src)\n", "eval(src)\n",
                "spec.loader.exec_module(m)\n", "import pydoc\n", "from pydoc import locate\n",
                "from timeit import timeit\n", "import timeit\n", "import code\n", "from code import interact\n",
                "import cProfile\n", "from cProfile import run\n"):
        assert _dynamic_hits(X, src), src
    for module in DYNAMIC_MODULES:                      # every banned module, in each import form
        for src in (f"import {module}\n", f"import {module}.x\n", f"from {module} import x\n"):
            assert _dynamic_hits(X, src), src
    assert not _dynamic_hits(X, "import importlib.metadata\nfrom importlib import metadata\n"
                                "v = importlib.metadata.distribution('PyYAML')\nimport json\nimport codecs\n"
                                "import profile_notes\nfrom core.compliance import code_files\n")
```

  New text:

```python
    for src in ("from core.engine import *\n", "from core.compliance.model import *\n",
                "import importlib\nm = importlib.import_module('numpy')\n", "m = __import__('numpy')\n",
                "from importlib import import_module as im\n", "import importlib.util\n",
                "from importlib import util\n", "import runpy\n", "import pkgutil\n", "exec(src)\n", "eval(src)\n",
                "spec.loader.exec_module(m)\n", "import pydoc\n", "from pydoc import locate\n",
                "from timeit import timeit\n", "import timeit\n", "import code\n", "from code import interact\n",
                "import cProfile\n", "from cProfile import run\n", "import importlib\n",
                "import importlib.resources\n", "from importlib import resources\n", "import profile\n",
                "import pdb\n", "from bdb import Bdb\n", "import trace\n", "import doctest\n", "import unittest.mock\n",
                "from unittest import mock\n", "from logging import config\n", "import logging.config\n",
                "from logging.config import dictConfig\n", "import pickle\n", "import _pickle\n", "import shelve\n",
                "import marshal\n", "import site\n", "import ensurepip\n", "import venv\n", "import tkinter\n",
                "from tkinter import Tcl\n", "import _tkinter\n", "import turtle\n", "import turtledemo\n",
                "import idlelib.run\n", 'x = compile(s, "x", "exec")\n', "import pstats\n",
                "from pstats import Stats\n", "import tracemalloc\n", "from tracemalloc import Snapshot\n"):
        assert _dynamic_hits(X, src), src
    for module in DYNAMIC_MODULES:                      # every banned module, in each import form
        for src in (f"import {module}\n", f"import {module}.x\n", f"from {module} import x\n"):
            assert _dynamic_hits(X, src), src
    assert not _dynamic_hits(X, "import importlib.metadata\nfrom importlib import metadata\n"
                                "v = importlib.metadata.distribution('PyYAML')\nimport json\nimport codecs\n"
                                "import profile_notes\nfrom core.compliance import code_files\n")
    assert not _dynamic_hits(X, "from importlib.metadata import distribution, PackageNotFoundError\nimport traceback\n"
                                "import faulthandler\nimport logging\nfrom logging import getLogger\n"
                                "_P = re.compile(r'x')\n")    # not banned (R1); pstats and tracemalloc are (R2-10)
```

  Edit 4. Anchor: the def line and docstring of test_imports_stay_on_the_allowlist (guards:305-309); the new test goes
  right above it. Old text:

```python
def test_imports_stay_on_the_allowlist():
    """stdlib, yaml, cryptography (inside a function only), core.isolation and core.compliance.* (contract
    section 0), so the D14 signed closure stays core/__init__.py, core/isolation.py and core/compliance (P6). The
    stdlib modules in NETWORK_MODULES are not allowed even though they are stdlib: core/compliance never needs the
    network (the alert email is sent by the scheduled Claude task, the toast is a subprocess)."""
```

  New text:

```python
def test_bare_compile_and_importlib_submodules_are_dynamic():
    """The builtin compile() turns a string into code (types.FunctionType can then run it with no exec or eval), so the
    bare name is banned; re.compile is an attribute and stays legal. Every importlib import but importlib.metadata is
    dynamic (importlib.resources imports a package named by a string), and so is every attribute of the name
    importlib but metadata, which `import importlib.metadata` binds (R9)."""
    for src in ('x = compile(s, "x", "exec")\n', "f = compile\n", "compile = None\n", "import importlib\n",
                "import importlib.resources\n", "from importlib import resources\n", "import importlib.abc\n",
                "import importlib._bootstrap\n", "from importlib import metadata, util\n",
                "import importlib.metadata\nm = importlib.util.spec_from_file_location('m', p)\n",
                "import importlib.metadata\nimportlib._bootstrap._load(s)\n",
                "import importlib.metadata\nimportlib.reload(m)\n"):
        assert _dynamic_hits(X, src), src
    assert _dynamic_module("importlib.util") and not _dynamic_module("importlib.metadata.x")
    assert not _dynamic_hits(X, "_P = re.compile(r'x')\nself.compile()\nm.compile\n")
    assert not _dynamic_hits(X, "import importlib.metadata\nfrom importlib import metadata\n"
                                "from importlib.metadata import distribution, PackageNotFoundError\n"
                                "import importlib.metadata as md\nv = importlib.metadata.version('PyYAML')\n")


def test_imports_stay_on_the_allowlist():
    """stdlib, yaml, cryptography (inside a function only), core.isolation and core.compliance.* (contract
    section 0), so the D14 signed closure stays core/__init__.py, core/isolation.py and core/compliance (P6). The
    stdlib modules in NETWORK_MODULES are not allowed even though they are stdlib: core/compliance never needs the
    network (the alert email is sent by the scheduled Claude task, the toast is a subprocess)."""
```

  Edit 5. Anchor: test_imports_stay_on_the_allowlist, the "modules a plain socket/urllib list misses" loop and the
  sub-module negative control (guards:323-333). The list gains the xml.dom, antigravity, ctypes, _ctypes, _ssl and
  _overlapped positives (the three old xml.dom cases stay), and `from xml.dom import minidom` leaves the negative
  control. Old text:

```python
    # the modules a plain socket/urllib list misses: each can open a connection or fetch a URL on its own
    for src in ("import multiprocessing.connection\n", "from multiprocessing import connection\n",
                "import logging.handlers\n", "from logging import handlers\n",
                "from logging.handlers import HTTPHandler\n", "import _socket\n", "import socketserver\n",
                "import selectors\n", "from wsgiref import simple_server\n", "import xml.sax\n",
                "from xml import sax\n", "from xml.dom import pulldom\n", "from xml.dom import expatbuilder\n",
                "import xml.dom.expatbuilder\n"):
        assert _allowlist_hits(X, src), src
    # a banned SUB-module does not ban its parent package or its harmless siblings
    assert not _allowlist_hits(X, "import logging\nfrom logging import getLogger\nimport xml.etree.ElementTree\n"
                                  "from xml.etree import ElementTree\nfrom xml.dom import minidom\n")
```

  New text:

```python
    # the modules a plain socket/urllib list misses: each can open a connection or fetch a URL on its own
    for src in ("import multiprocessing.connection\n", "from multiprocessing import connection\n",
                "import logging.handlers\n", "from logging import handlers\n",
                "from logging.handlers import HTTPHandler\n", "import _socket\n", "import socketserver\n",
                "import selectors\n", "from wsgiref import simple_server\n", "import xml.sax\n",
                "from xml import sax\n", "from xml.dom import pulldom\n", "from xml.dom import expatbuilder\n",
                "import xml.dom.expatbuilder\n", "import xml.dom\n", "from xml.dom import minidom\n",
                "import xml.dom.minidom\n", "import xml.dom.xmlbuilder\n", "from xml import dom\n",
                "from xml.dom.minidom import parseString\n", "import antigravity\n", "import ctypes\n",
                "from ctypes import wintypes\n", "import _ctypes\n", "import _ssl\n", "import _overlapped\n"):
        assert _allowlist_hits(X, src), src
    # a banned SUB-module does not ban its parent package or its harmless siblings
    assert not _allowlist_hits(X, "import logging\nfrom logging import getLogger\nimport xml.etree.ElementTree\n"
                                  "from xml.etree import ElementTree\n")
```

  Edit 6. Anchor: test_suite_is_registered_in_run_all_and_readme, the whole function (guards:483-489). Old text:

```python
def test_suite_is_registered_in_run_all_and_readme():
    """`tests/run_all.py --suite compliance` selects this suite, and both hand-written suite lists name it."""
    from tests import run_all
    names = [n for n, _f in run_all.select(run_all.tests(), suite="compliance")]
    assert any(n.startswith("compliance/compliance_guards/") for n in names), names
    assert "paper, grokteam or compliance" in (ROOT / "tests" / "run_all.py").read_text(encoding="utf-8")
    assert "paper, grokteam or compliance" in (ROOT / "README.md").read_text(encoding="utf-8")
```

  New text (`read_text` uses universal newlines, so the CRLF files split cleanly; tests/run_all.py:113 and
  README.md:816 hold the only "one suite: " lines today):

```python
def _suite_names(text: str) -> list[str]:
    """The names of the first hand-written "one suite: a, b or c" list in `text` ([] when there is none)."""
    line = next((s for s in text.splitlines() if "one suite: " in s), "")
    listed = line.split("one suite: ", 1)[1].rstrip('")').strip() if line else ""
    return [n for n in re.split(r", | or ", listed) if n]


def test_suite_is_registered_in_run_all_and_readme():
    """`tests/run_all.py --suite compliance` selects this suite, and both hand-written suite lists name it; the check
    reads the list, so adding a suite to either list breaks nothing (R7)."""
    from tests import run_all
    names = [n for n, _f in run_all.select(run_all.tests(), suite="compliance")]
    assert any(n.startswith("compliance/compliance_guards/") for n in names), names
    assert _suite_names('help="run one suite: cockpit, compliance or odds")') == ["cockpit", "compliance", "odds"]
    assert "compliance" not in _suite_names("x  # one suite: cockpit or paper\n") and _suite_names("none\n") == []
    for path in (ROOT / "tests" / "run_all.py", ROOT / "README.md"):
        assert "compliance" in _suite_names(path.read_text(encoding="utf-8")), path.name
```

- [ ] **Step 2: Run to verify it fails**

  Overlap check with the PowerShell tool (it must print nothing; otherwise wait and re-run it):

```powershell
Get-CimInstance Win32_Process -Filter "Name LIKE 'python%'" | Where-Object { $_.CommandLine -match 'run_all' } | Select-Object ProcessId,Name,CommandLine
```

  Then from the repo root in Git Bash:

```bash
.venv/Scripts/python.exe -m tests.compliance_acceptance compliance_guards/; echo "exit $?"
```

  Expected: three tracebacks, and these three FAIL lines among 13 PASS lines (the runner sorts by test name):

```
FAIL compliance_guards/test_bare_compile_and_importlib_submodules_are_dynamic AssertionError: x = compile(s, "x", "exec")
FAIL compliance_guards/test_imports_stay_on_the_allowlist AssertionError: import xml.dom
FAIL compliance_guards/test_no_forbidden_module_import AssertionError: import importlib
```

  then `13/16 passed, 3 failed, 0 not run` and `exit 1`. Each first failing case is a route the lists miss today:
  the bare compile, the whole xml.dom package and the bare importlib. The PASS line of
  `test_suite_is_registered_in_run_all_and_readme` shows the R7 refactor is green already. Any other FAIL means an
  Edit of Step 1 went wrong: fix the Edit, never the expectation.

- [ ] **Step 3: Implement**

  Four Edit-tool replacements in `tests/compliance_guards.py` (LF, kept). Line numbers below are those of the tree
  before Step 1; after Edit 1 they are one higher, and each Edit below shifts the ones after it, so find each Edit by
  its anchor.

  Edit 7. Anchor: the constant NETWORK_MODULES (guards:39-41). The two `xml.dom.*` entries become one `xml.dom` (in
  place), and five entries are appended: 22 entries become 26. The comment above the constant stays. Old text:

```python
NETWORK_MODULES = ("urllib", "http", "socket", "_socket", "socketserver", "selectors", "ssl", "smtplib", "ftplib",
                   "imaplib", "poplib", "nntplib", "telnetlib", "xmlrpc", "asyncio", "webbrowser", "multiprocessing",
                   "wsgiref", "xml.sax", "xml.dom.pulldom", "xml.dom.expatbuilder", "logging.handlers")
```

  New text:

```python
NETWORK_MODULES = ("urllib", "http", "socket", "_socket", "socketserver", "selectors", "ssl", "smtplib", "ftplib",
                   "imaplib", "poplib", "nntplib", "telnetlib", "xmlrpc", "asyncio", "webbrowser", "multiprocessing",
                   "wsgiref", "xml.sax", "xml.dom", "logging.handlers", "antigravity", "ctypes", "_ctypes", "_ssl",
                   "_overlapped")
```

  Edit 8. Anchor: the comment block "# Star and dynamic imports hide" through the end of DYNAMIC_MODULES, between
  FORBIDDEN_MODULES and "# base name -> attributes that read the clock" (guards:45-51). `importlib` replaces
  `importlib.util` and `importlib.machinery` (first), the seven old entries follow, then the 19 of F1 and `pstats`,
  `tracemalloc` (R2-10): 9 entries become 29. `DYNAMIC_NAMES` is unchanged. Old text:

```python
# Star and dynamic imports hide what a file loads from these guards and from the D14 closure (P6). pydoc (locate),
# timeit, code and cProfile import or run code named in a string, so they count as dynamic imports too.
# importlib.metadata stays allowed: owner.py reads the RECORD files with it. core/ probes for cryptography with a
# lazy `import` inside try/except ImportError; importlib.util.find_spec is for tests only.
DYNAMIC_NAMES = frozenset({"__import__", "import_module", "exec_module", "load_module", "exec", "eval"})
DYNAMIC_MODULES = ("importlib.util", "importlib.machinery", "runpy", "pkgutil", "zipimport", "pydoc", "timeit",
                   "code", "cProfile")
```

  New text:

```python
# Star and dynamic imports hide what a file loads from these guards and from the D14 closure (P6). Each module below
# imports or runs code named in a string or read from data: importlib (every submodule but metadata), runpy, pkgutil,
# zipimport, pydoc (locate), timeit, code, cProfile, profile, pdb, bdb, trace and doctest (exec of a string), unittest
# (mock.patch targets, the loader's __import__), logging.config (class strings, and a TCP listener), pickle, _pickle,
# shelve and marshal (objects and code from bytes), site (.pth lines are exec'd), ensurepip and venv (pip through
# runpy), tkinter, _tkinter, turtle, turtledemo and idlelib (a Tcl interpreter with sockets; idlelib exec), pstats
# and tracemalloc (they load files with marshal and pickle: pstats.Stats, tracemalloc.Snapshot.load). The builtin
# compile() is banned as a bare name only, so re.compile stays legal (builtins.compile is left to review).
# importlib.metadata stays allowed: owner.py reads the RECORD files with it. `import importlib.metadata` binds the
# name importlib, so any other attribute of it (importlib.util, importlib._bootstrap) is a hit too; its
# EntryPoint.load imports by string through an attribute, which this scan does not see. faulthandler stays allowed
# (R1): it runs no string and opens nothing. A denylist, not a proof: codeop and dis (they compile a string, which
# types.FunctionType runs), _frozen_importlib, _frozen_importlib_external and _imp (importlib's bootstrap under other
# names) and _interpreters (run_string) are not on it and are left to review. core/ probes for cryptography with a
# lazy `import` inside try/except ImportError; importlib.util.find_spec is for tests only.
DYNAMIC_NAMES = frozenset({"__import__", "import_module", "exec_module", "load_module", "exec", "eval"})
DYNAMIC_BARE = frozenset({"compile"})               # an ast.Name only: re.compile is an attribute
DYNAMIC_MODULES = ("importlib", "runpy", "pkgutil", "zipimport", "pydoc", "timeit", "code", "cProfile", "profile",
                   "pdb", "bdb", "trace", "doctest", "unittest", "logging.config", "pickle", "_pickle", "shelve",
                   "marshal", "site", "ensurepip", "venv", "tkinter", "_tkinter", "turtle", "turtledemo", "idlelib",
                   "pstats", "tracemalloc")
DYNAMIC_EXEMPT = "importlib.metadata"               # and everything below it (R9)
```

  Edit 9. Anchor: the checker _dynamic_hits, the whole function (guards:146-157). Old text:

```python
def _dynamic_hits(rel: str, src: str) -> list[str]:
    tree, hits = ast.parse(src), []
    for node, module, names, _f in _imports(rel, tree):
        targets = [module] + [f"{module}.{n}" for n in names]
        if ("*" in names or DYNAMIC_NAMES.intersection(names)
                or any(t == m or t.startswith(m + ".") for t in targets for m in DYNAMIC_MODULES)):
            hits.append(f"{rel}:{node.lineno}: star or dynamic import from {module}")
    for node, _f in _walk(tree):
        name = node.id if isinstance(node, ast.Name) else node.attr if isinstance(node, ast.Attribute) else None
        if name in DYNAMIC_NAMES:
            hits.append(f"{rel}:{node.lineno}: {name}")
    return hits
```

  New text (one new helper above the checker):

```python
def _dynamic_module(target: str) -> bool:
    """A dotted import target in DYNAMIC_MODULES (or below one), unless it is DYNAMIC_EXEMPT or below it (R9)."""
    if target == DYNAMIC_EXEMPT or target.startswith(DYNAMIC_EXEMPT + "."):
        return False
    return any(target == m or target.startswith(m + ".") for m in DYNAMIC_MODULES)


def _dynamic_hits(rel: str, src: str) -> list[str]:
    tree, hits = ast.parse(src), []
    for node, module, names, _f in _imports(rel, tree):
        targets = [f"{module}.{n}" for n in names] or [module]     # `from importlib import metadata` is that module
        if "*" in names or DYNAMIC_NAMES.intersection(names) or any(_dynamic_module(t) for t in targets):
            hits.append(f"{rel}:{node.lineno}: star or dynamic import from {module}")
    for node, _f in _walk(tree):
        name = node.id if isinstance(node, ast.Name) else node.attr if isinstance(node, ast.Attribute) else None
        via = isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == "importlib"
        if via and name != "metadata":                  # `import importlib.metadata` binds the name importlib (R9)
            hits.append(f"{rel}:{node.lineno}: importlib.{name}")
        elif name in DYNAMIC_NAMES or (isinstance(node, ast.Name) and node.id in DYNAMIC_BARE):
            hits.append(f"{rel}:{node.lineno}: {name}")
    return hits
```

  Edit 10. Anchor: test_no_http_verb_calls, its def line and docstring (guards:248-262; the body below it stays). The
  docstring names the new network bans, drops the minidom and ctypes routes from "not covered" and adds sqlite3's
  load_extension there. Old text:

```python
def test_no_http_verb_calls():
    """core/compliance never calls .post/.put/.delete/.patch/.request on anything (contract section 0), a dict-like
    `.put` included, nor urlopen, urlretrieve or create_connection (bare or as an attribute). This is the second
    line. The first is test_imports_stay_on_the_allowlist, which bans every import form of the stdlib modules that
    open a connection or fetch a URL (NETWORK_MODULES: urllib, http, socket, ssl, the mail, ftp and telnet clients,
    xmlrpc, asyncio, selectors, socketserver, wsgiref, multiprocessing, webbrowser, logging.handlers, xml.sax, which
    opens a URL given as a system id, and two xml.dom modules that are not fetchers themselves: pulldom, built on
    xml.sax, and expatbuilder, which imports xml.dom.xmlbuilder). Together they catch a stdlib network call written
    in the ordinary ways; they do not prove that core/compliance cannot reach the network. Not covered: a
    `subprocess` call (the P26 alert toast is one; os.system, os.popen and os.startfile launch processes the same
    way), `ctypes`, and reaching a network API through an allowed module, by attribute or by `getattr(module,
    "name")`. That needs no banned import and no banned name: the allowed xml.dom.minidom hands out an
    xml.dom.xmlbuilder DOMBuilder whose parseURI opens a URL with urllib.request
    (`minidom.getDOMImplementation().createDOMBuilder(1, None).parseURI(url)`), and an allowed module that imports
    a banned one carries it as an attribute. All three are left to review."""
```

  New text:

```python
def test_no_http_verb_calls():
    """core/compliance never calls .post/.put/.delete/.patch/.request on anything (contract section 0), a dict-like
    `.put` included, nor urlopen, urlretrieve or create_connection (bare or as an attribute). This is the second
    line. The first is test_imports_stay_on_the_allowlist, which bans every import form of the stdlib modules that
    open a connection or fetch a URL (NETWORK_MODULES: urllib, http, socket, ssl and _ssl, the mail, ftp and telnet
    clients, xmlrpc, asyncio and _overlapped, selectors, socketserver, wsgiref, multiprocessing, webbrowser and
    antigravity, which opens a URL at import, logging.handlers, xml.sax, which opens a URL given as a system id, the
    whole xml.dom package, whose xmlbuilder DOMBuilder.parseURI opens a URL with urllib.request and which minidom and
    xml.dom.getDOMImplementation() both hand out, and ctypes and _ctypes, which call any DLL). Together they catch a
    stdlib network call written in the ordinary ways; they do not prove that core/compliance cannot reach the
    network. Not covered: a `subprocess` call (the P26 alert toast is one; os.system, os.popen, os.startfile and
    _winapi launch processes the same way), sqlite3's Connection.load_extension, which loads any DLL as ctypes does,
    and reaching a network API through an allowed module, by attribute or by `getattr(module, "name")`: an allowed
    module that imports a banned one carries it as an attribute (mailbox carries socket, concurrent.futures.process
    carries multiprocessing.connection). All three are left to review."""
```

- [ ] **Step 4: Run to verify it passes**

  Run the overlap check of Step 2 (PowerShell tool; it must print nothing) before EACH Python command below. All
  run from the repo root in Git Bash.

  Overlap check, then:

```bash
.venv/Scripts/python.exe -m tests.compliance_acceptance compliance_guards/; echo "exit $?"
```

  Expected: 16 PASS lines, then `16/16 passed, 0 failed, 0 not run`, then `exit 0`. A
  FAIL of `test_no_forbidden_module_import` or `test_imports_stay_on_the_allowlist` on a shipped file names the file
  and line: report it to the controller, never shorten a list to make it pass.

  Overlap check, then the compliance suite (it rewrites the tracked `qa/acceptance_results.json`, which is restored
  at once). Every `--suite` run first imports all ten suites (tests/run_all.py:41-50), against the Bash tool's 120 s
  default, so give this line `timeout: 300000`; never start a second run meanwhile:

```bash
.venv/Scripts/python.exe tests/run_all.py --suite compliance; echo "exit $?"; git checkout -- qa/acceptance_results.json
```

  Expected last lines: `316/318 passed, 0 failed, 2 not run; ` followed by the path of `qa\acceptance_results.json`,
  then `exit 0`. The two NOT_RUN rows are the REFDATA symlink tests
  (`compliance_isolation/test_symlinks_are_refused`, `compliance_tables/test_calendar_sha256_refuses_a_file_symlink`);
  with Windows Developer Mode on they pass instead and the line reads `318/318 passed, 0 failed, 0 not run`. Then:

```bash
git status --short
```

  Expected: exactly ` M tests/compliance_guards.py`, plus, if the executor keeps its ledger in the repo and has not
  committed it, `?? docs/superpowers/plans/2026-10-24-compliance-followup-execution-ledger.md`; nothing else.

- [ ] **Step 5: Commit**

```bash
git add tests/compliance_guards.py
git diff --cached --stat
git diff --cached --stat --ignore-cr-at-eol
```

  The two stat outputs must be identical (the file is LF): `tests/compliance_guards.py | 127` followed by its bar,
  and `1 file changed, 98 insertions(+), 29 deletions(-)`. If they differ, an edit converted line endings: run
  `git restore --staged tests/compliance_guards.py`, `git checkout -- tests/compliance_guards.py` and redo the
  Edits with the Edit tool. Then:

```bash
git commit -m "test(guards): ban xml.dom, string-exec modules and bare compile; read the suite lists" -m "Task 1 (R1 with R2-10, R7, R9): NETWORK_MODULES 22 -> 26, DYNAMIC_MODULES 9 -> 29 with DYNAMIC_BARE and DYNAMIC_EXEMPT, and the registration test reads the one-suite lists." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
