"""Static guards over execution/ and the execution suite's own harness (E1 plan Tasks 1 and 2; E1 spec 8 "Read-only
guards", 9 "Guards"; contract sections 0.2, 0.5 and 4.5).

Each guard is a pure checker `(rel, source) -> [hit, ...]`. Every test first proves its checker catches a synthetic
offender (the positive control), then asserts the shipped files are clean. The repo-wide guards (T-RO-01, test_08,
test_09, test_16, test_18, T-CTX-01) scan execution/ too, with two file-exact text exceptions: execution/kis_inquiry.py
and execution/upbit_inquiry.py. These add what they miss: docstrings and comments, `def` names, the explicit import
allowlist, every HTTP verb and process call, star and dynamic imports, the wall clock outside poll.main(), writes
that skip checked_target, the one writer of evidence.jsonl, and the never-live harness itself. Task 2 appends the
pinned allowlists and the exactness, transport-only and pinned-send guards.
"""
from __future__ import annotations

import ast
import contextlib
import io
import os
import re
import sys
import tempfile
import types
from pathlib import Path

from tests import acceptance as A
from tests import compliance_guards as CG
from tests import macro_m0_harness as H

ROOT = Path(__file__).resolve().parents[1]
EXECUTION = ROOT / "execution"
INIT = "execution/__init__.py"
X = "execution/x.py"                       # the name a synthetic offender is checked under
RAW_BANNED = ("private_key", "seed_phrase", "append_system_entry", "system_halt", "system_disarm",
              "x-simulated-trading", "openapivts")          # any case
STDLIB = frozenset({"__future__", "argparse", "base64", "collections.abc", "contextlib", "dataclasses", "datetime",
                    "email.utils", "fcntl", "hashlib", "hmac", "json", "math", "msvcrt", "os", "pathlib", "re", "sys",
                    "threading", "time", "traceback", "types", "typing", "uuid", "zoneinfo"})
VERBS = frozenset({"post", "put", "patch", "delete", "request", "send", "urlopen", "getresponse", "connect",
                   "create_connection"})
CLOCK_MAIN = "execution/poll.py"           # only the body of its main() reads the clock (E11)
EXTRA_CLOCKS = {"utils": frozenset({"localtime", "formatdate", "make_msgid"}),   # email.utils and uuid names that
                "uuid": frozenset({"uuid1"})}                                     # read the clock, beyond CG.CLOCKS
TRANSPORT = "execution/transport.py"       # the only user of requests and urllib.parse
EVIDENCE_WRITER = "execution/evidence.py"  # the one writer of evidence.jsonl (spec 6)
OS_PROCESS = ("system", "popen", "startfile")
OS_PROCESS_PREFIXES = ("fork", "exec", "spawn", "posix_spawn")
WRITE_MODE = re.compile(r"[wax+]")
WRITE_METHODS = frozenset({"write_text", "write_bytes", "touch", "unlink", "rename", "rmdir", "symlink_to",
                           "hardlink_to"})
OS_WRITES = frozenset({"remove", "unlink", "rename", "renames", "removedirs", "rmdir", "open", "fdopen", "mkdir",
                       "makedirs", "link", "symlink", "truncate"})


# --------------------------------------------------------------------------- #
# Scope and AST helpers
# --------------------------------------------------------------------------- #
def _sources() -> dict[str, str]:
    """rel path -> raw text of every execution/**/*.py (no __pycache__); execution/__init__.py must be among them."""
    files = CG._sources(EXECUTION)
    assert INIT in files, f"scan scope: {INIT} missing"
    return files


def _test_sources() -> dict[str, str]:
    """rel path -> raw text of every tests/execution_*.py."""
    return {f"tests/{p.name}": p.read_text(encoding="utf-8") for p in sorted((ROOT / "tests").glob("execution_*.py"))}


def _os_process(node: ast.AST) -> bool:
    """`os.<name>` (called or not) or `from os import <name>` for a name that starts a process."""
    if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == "os":
        names = [node.attr]
    elif isinstance(node, ast.ImportFrom) and node.module == "os":
        names = [a.name for a in node.names]
    else:
        return False
    return any(n in OS_PROCESS or n.startswith(OS_PROCESS_PREFIXES) for n in names)


def _modules(node: ast.AST) -> list[str]:
    """The modules an import statement names ([] for any other node)."""
    if isinstance(node, ast.Import):
        return [a.name for a in node.names]
    return [node.module or ""] if isinstance(node, ast.ImportFrom) else []


def _top_body(tree: ast.AST, name: str) -> set[int]:
    """ids of every node in the BODY of the module-level function `name` (a method or a nested def of that name is
    not it; the def's defaults and decorators are outside its body)."""
    return {id(n) for f in tree.body if isinstance(f, ast.FunctionDef) and f.name == name
            for s in f.body for n in ast.walk(s)}


def _checked(node: ast.AST | None) -> bool:
    """A `checked_target(...)` call, bare or as `isolation.checked_target(...)`."""
    return isinstance(node, ast.Call) and "checked_target" in (getattr(node.func, "id", None),
                                                               getattr(node.func, "attr", None))


def _writes(call: ast.Call, at: int) -> bool:
    """The call's mode (positional `at` or keyword `mode`) can write: it holds w, a, x or +, or is not a constant."""
    mode = call.args[at] if len(call.args) > at else next((k.value for k in call.keywords if k.arg == "mode"), None)
    if mode is None:
        return False
    if isinstance(mode, ast.Constant) and isinstance(mode.value, str):
        return bool(WRITE_MODE.search(mode.value))
    return True


# --------------------------------------------------------------------------- #
# Checkers: (rel, source) -> hits
# --------------------------------------------------------------------------- #
def _raw_hits(rel: str, src: str) -> list[str]:
    """RAW_BANNED anywhere in the raw text, in any case."""
    return CG._raw_hits(rel, src, RAW_BANNED, ())


def _allowed(rel: str, name: str) -> bool:
    """One dotted import target on the E1 allowlist (E2): STDLIB exactly, core.isolation, core.compliance.*,
    execution.*, and requests and urllib.parse in transport.py only."""
    if name in STDLIB or name == "core.isolation":
        return True
    if name in ("requests", "urllib.parse", "contextvars", "execution_network.route"):
        return rel == TRANSPORT
    return any(name == p or name.startswith(p + ".") for p in ("core.compliance", "execution"))


def _allowlist_hits(rel: str, src: str) -> list[str]:
    hits = []
    for node, module, names, _f in CG._imports(rel, ast.parse(src)):
        approved = _allowed(rel, module) or (names and all(_allowed(rel, f"{module}.{n}") for n in names))
        if module == "execution_network" or module.startswith("execution_network."):
            approved = (rel == TRANSPORT and isinstance(node, ast.ImportFrom)
                        and module == "execution_network.route" and not node.level
                        and len(node.names) == 1 and node.names[0].name == "route_options"
                        and node.names[0].asname is None)
        if not approved:
            hits.append(f"{rel}:{node.lineno}: imports {module}: not on the E1 allowlist (contract 0.5)")
    return hits


def _verb_hits(rel: str, src: str) -> list[str]:
    """A VERBS attribute call anywhere but the one `session.request(...)` in the body of the module-level `_send` of
    transport.py (E1R2-11; a method of that name is not it); os.system, os.popen, os.startfile, os.fork*, os.exec*,
    os.spawn* and os.posix_spawn*, named or imported; a subscript of sys.modules."""
    tree, hits = ast.parse(src), []
    send = _top_body(tree, "_send") if rel == TRANSPORT else set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in VERBS:
            if not (id(node) in send and ast.unparse(node.func) == "session.request"):
                hits.append(f"{rel}:{node.lineno}: .{node.func.attr}()")
        elif _os_process(node):
            hits.append(f"{rel}:{node.lineno}: {ast.unparse(node)}")
        elif isinstance(node, ast.Subscript) and ast.unparse(node.value) == "sys.modules":
            hits.append(f"{rel}:{node.lineno}: sys.modules[...]")
    return hits


def _clock_hits(rel: str, src: str) -> list[str]:
    """CG.CLOCKS and EXTRA_CLOCKS reads, any `from time import ...` and a `from` import of an EXTRA_CLOCKS name,
    except in the BODY of the module-level main() of execution/poll.py (E11; a method or nested def named main is
    not it); a def's defaults and decorators run where the def runs, so they count."""
    tree, hits, alias = ast.parse(src), [], {}
    clocks = CG.CLOCKS | EXTRA_CLOCKS
    for n in ast.walk(tree):                            # `import time as t`, `from datetime import date as D`
        if isinstance(n, ast.Import) or (isinstance(n, ast.ImportFrom) and n.module in ("datetime", "email")):
            alias.update({a.asname or a.name: a.name.rsplit(".", 1)[-1] for a in n.names
                          if a.name.rsplit(".", 1)[-1] in clocks})
    main = _top_body(tree, "main") if rel == CLOCK_MAIN else set()
    for node in ast.walk(tree):
        if id(node) in main:
            continue
        if isinstance(node, ast.Attribute):
            value = node.value
            base = alias.get(value.id, value.id) if isinstance(value, ast.Name) else getattr(value, "attr", None)
            if node.attr in clocks.get(base, ()):
                hits.append(f"{rel}:{node.lineno}: {base}.{node.attr}")
        elif isinstance(node, ast.ImportFrom) and (node.module == "time" or any(
                a.name in EXTRA_CLOCKS.get((node.module or "").rsplit(".", 1)[-1], ()) for a in node.names)):
            hits.append(f"{rel}:{node.lineno}: from {node.module} import ...")
    return hits


def _write_hits(rel: str, src: str) -> list[str]:
    """Spec 4 "State files": open() for writing only on a checked_target(...) call, no writing `.open(...)`, both
    os.replace arguments and every .mkdir() receiver checked_target(...) calls; write_text, write_bytes, touch,
    unlink, rename, rmdir, the link makers, a one-argument or `target=` .replace() (Path.replace: str.replace takes
    two, datetime.replace only field keywords), the os file writers of OS_WRITES and any shutil use banned outright."""
    hits = []
    for node, _f in CG._walk(ast.parse(src)):
        bad = ""
        if (isinstance(node, ast.Name) and node.id == "shutil") or any(
                m.split(".")[0] == "shutil" for m in _modules(node)):
            bad = "shutil"
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "open":
            first = node.args[0] if node.args else next((k.value for k in node.keywords if k.arg == "file"), None)
            if _writes(node, 1) and not _checked(first):
                bad = "open() for writing without checked_target"
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            name, owner = node.func.attr, ast.unparse(node.func.value)
            if owner == "os" and name == "replace":
                if not (len(node.args) == 2 and all(_checked(a) for a in node.args)):
                    bad = "os.replace() of an unchecked path"
            elif owner == "os" and name in OS_WRITES:
                bad = f"os.{name}()"
            elif name == "open":
                bad = ".open() for writing" if _writes(node, 0) else ""
            elif name == "mkdir":
                bad = "" if _checked(node.func.value) else ".mkdir() on an unchecked path"
            elif name in WRITE_METHODS or (name == "replace" and ((len(node.args) == 1 and not node.keywords)
                                                                  or [k.arg for k in node.keywords] == ["target"])):
                bad = f".{name}()"
        if bad:
            hits.append(f"{rel}:{node.lineno}: {bad}")
    return hits


def _evidence_hits(rel: str, src: str) -> list[str]:
    """Raw text: only execution/evidence.py names evidence_path (spec 6: the one writer of evidence.jsonl)."""
    return [] if rel == EVIDENCE_WRITER or "evidence_path" not in src else [f"{rel}: names evidence_path"]


def _process_hits(rel: str, src: str) -> list[str]:
    """A test that would start a process or reload a module (contract 0.2): an import of subprocess, multiprocessing
    or runpy, sys.executable, an os process name, importlib.reload or `from importlib import reload`."""
    hits = []
    for node, _f in CG._walk(ast.parse(src)):
        mods = _modules(node)
        reload = isinstance(node, ast.ImportFrom) and node.module == "importlib" and any(
            a.name == "reload" for a in node.names)
        attr = isinstance(node, ast.Attribute) and ast.unparse(node) in ("sys.executable", "importlib.reload")
        if (reload or attr or _os_process(node)
                or any(m.split(".")[0] in ("subprocess", "multiprocessing", "runpy") for m in mods)):
            hits.append(f"{rel}:{node.lineno}: {ast.unparse(node)}")
    return hits


def _eager_imports(rel: str, src: str) -> list[str]:
    """The `execution` or `tests.execution_fixtures` import targets of `src` outside every function body (E28)."""
    return [t for _n, module, names, funcs in CG._imports(rel, ast.parse(src)) if not funcs
            for t in [module, *(f"{module}.{n}" for n in names)]
            if t.split(".")[0] == "execution" or t == "tests.execution_fixtures"]


# --------------------------------------------------------------------------- #
# Fake repo roots for the repo-wide guards
# --------------------------------------------------------------------------- #
def _probe_root(files: dict[str, str]) -> Path:
    """A fresh fake repo root inside the per-test temp home, holding `files` (rel path -> text)."""
    root = Path(tempfile.mkdtemp(prefix="root_", dir=os.environ["TRADEGEN_HOME"]))
    for rel, text in files.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(text, encoding="utf-8")
    return root


@contextlib.contextmanager
def _swapped_root(root: Path):
    """tests.acceptance.ROOT and tests.macro_m0_harness.ROOT pointed at `root`; both come back afterwards."""
    keep = A.ROOT, H.ROOT
    A.ROOT = H.ROOT = root
    try:
        yield
    finally:
        A.ROOT, H.ROOT = keep


def _passes(test) -> bool:
    try:
        test()
    except AssertionError:
        return False
    return True


def _verdicts(rel: str, text: str) -> tuple[list[str], bool, bool]:
    """In a fake root holding only `rel` with `text`: T-RO-01's offences for it, and whether test_08 and test_09
    pass."""
    root = _probe_root({rel: text})
    with _swapped_root(root):
        return (H._offences(root / rel), _passes(A.test_08_no_broker_order_path),
                _passes(A.test_09_no_account_credentials_requested))


# --------------------------------------------------------------------------- #
# The repo-wide guards see execution/, with file-exact exceptions
# --------------------------------------------------------------------------- #
def test_runtime_py_scans_execution():
    """E1 spec 8: runtime_py() (test_08, test_09, test_16, test_18 and T-RO-01 through _scan_files) scans execution/,
    and an order string in a synthetic execution/ file fails test_08 and T-RO-01."""
    assert EXECUTION / "__init__.py" in A.runtime_py(), "runtime_py() does not scan execution/"
    root = _probe_root({"execution/probe.py": 'X = "order-cash"\n'})
    with _swapped_root(root):
        assert A.runtime_py() == [root / "execution" / "probe.py"], A.runtime_py()
        assert not _passes(A.test_08_no_broker_order_path), "test_08 missed an order string in execution/"
        hits = H._offences(root / "execution" / "probe.py")
    assert hits == ["execution/probe.py: 'order-cash'"], hits


def test_kis_and_upbit_exceptions_are_file_exact():
    """E6: the text exceptions hold for exactly execution/kis_inquiry.py (KIS_ACCOUNT, CANO, ACNT_PRDT_CD and the
    /uapi/.../trading/ paths; test_09 too) and execution/upbit_inquiry.py (/v1/orders, /v1/withdraws), by full path
    (execution/sub/kis_inquiry.py gets none). The import, call and mutating-HTTP checks still run on both files, and
    test_08 has no exception at all."""
    kis = ('N = "KIS_ACCOUNT_8"\nCANO = "x"\nPD = "ACNT_PRDT_CD"\n'
           'P = "/uapi/domestic-stock/v1/trading/inquire-balance"\n')
    verdict = _verdicts("execution/kis_inquiry.py", kis)
    assert verdict == ([], True, True), verdict
    names = ("KIS_ACCOUNT", "CANO", "ACNT_PRDT_CD", "/uapi/domestic-stock/v1/trading/")
    for rel in ("execution/other.py", "execution/sub/kis_inquiry.py"):     # file-exact, not by base name
        hits, _ok8, ok9 = _verdicts(rel, kis)
        assert hits == [f"{rel}: {n!r}" for n in names], hits
        assert not ok9, f"test_09 passed the account names in {rel}"
    hits, _ok8, _ok9 = _verdicts("execution/upbit_inquiry.py", 'requests.post("https://x/v1/orders")\nx.withdraw()\n')
    assert hits == ["execution/upbit_inquiry.py:1: .post() on an order/withdraw/transfer/deposit URL",
                    "execution/upbit_inquiry.py:2: .withdraw()"], hits        # calls are no text check
    hits, ok8, _ok9 = _verdicts("execution/kis_inquiry.py", 'X = "order-cash"\n')
    assert hits == ["execution/kis_inquiry.py: 'order-cash'"] and not ok8, (hits, ok8)
    hits, _ok8, _ok9 = _verdicts("execution/kis_inquiry.py", "import ccxt\n")
    assert hits == ["execution/kis_inquiry.py:1: import ccxt"], hits
    hits, _ok8, _ok9 = _verdicts("execution/kis_inquiry.py", 'P = "/v1/orders/open"\n')
    assert hits == ["execution/kis_inquiry.py: '/v1/orders'"], hits          # the Upbit exception is Upbit's alone
    verdict = _verdicts("execution/upbit_inquiry.py", 'P = "/v1/orders/open"\nW = "/v1/withdraws"\n')
    assert verdict == ([], True, True), verdict
    hits, _ok8, ok9 = _verdicts("execution/upbit_inquiry.py", 'P = "/v1/orders/open"\nCANO = 1\n')
    assert hits == ["execution/upbit_inquiry.py: 'CANO'"] and not ok9, (hits, ok9)


# --------------------------------------------------------------------------- #
# Guards over every execution/**/*.py
# --------------------------------------------------------------------------- #
def test_no_raw_banned_words():
    """Raw text in any case, docstrings and comments included: no private_key or seed_phrase (the core-wide ban),
    none of owner.py's system-entry writers (E1 only alerts), neither the KIS demo header nor its mock host."""
    for needle in RAW_BANNED:
        assert _raw_hits(X, f'"""the {needle.upper()}"""\n'), needle
        assert _raw_hits(X, f"x = 1  # {needle}\n"), needle
    assert not _raw_hits(X, "signing_key, system_state, simulated, openapi, seed, private\n")
    hits = [h for rel, src in _sources().items() for h in _raw_hits(rel, src)]
    assert not hits, hits


def test_no_def_named_transfer_withdraw_or_deposit_address():
    """The compliance guards' core-wide def-name ban extends to execution/ (spec 8)."""
    sample = ("def transfer():\n    pass\nasync def withdraw():\n    pass\n"
              "class A:\n    def deposit_address(self):\n        pass\n")
    assert len(CG._def_hits(X, sample)) == 3
    assert not CG._def_hits(X, "def transfer_out():\n    pass\ndef withdrawals():\n    pass\n")
    hits = [h for rel, src in _sources().items() for h in CG._def_hits(rel, src)]
    assert not hits, hits


def test_imports_stay_on_the_allowlist():
    """E2 and spec 4 "Imports": exactly the STDLIB modules, core.isolation, core.compliance.*, execution.*, and
    requests and urllib.parse in transport.py only (Task 2 narrows execution.* further). Never config, data.*,
    core.engine.*, core.quant.*, core.calendars.*, core.ficc.*, core.rules.*, subprocess, ctypes, socket or
    shutil, so the signed closure stays small and the toast reaches subprocess only through alerts._toast."""
    for src in ("import config\n", "from data.krx import kis_client\n", "import data.krx.kis_client\n",
                "from core.engine import orders\n", "from core.quant import garch\n", "import urllib.request\n",
                "import socket\n", "import subprocess\n", "import ctypes\n", "import shutil\n", "import requests\n",
                "from urllib.parse import quote\n", "from core import isolation, quant\n",
                "from core.calendars import store\n", "import core.ficc.context_log\n",
                "def f():\n    import core.rules.governance\n", "import collections\n", "import os.path\n"):
        assert _allowlist_hits(X, src), src
    for src in ("import requests\n", "from urllib.parse import quote\n", "from urllib import parse\n",
                "from contextvars import ContextVar\n", "from execution_network.route import route_options\n"):
        assert not _allowlist_hits(TRANSPORT, src), src
        assert _allowlist_hits(X, src), src
    for src in ("from execution_network.unreviewed import route_options\n",
                "from execution_network.route import managed_route\n", "import execution_network.route\n",
                "from execution_network import route\n", "from execution_network.route import route_options as other\n"):
        assert _allowlist_hits(TRANSPORT, src), src
    for module in sorted(STDLIB):
        assert not _allowlist_hits(X, f"import {module}\n"), module
    ok = ("from __future__ import annotations\nfrom collections.abc import Iterator\nfrom datetime import datetime\n"
          "from email.utils import parsedate_to_datetime\nfrom core import isolation\n"
          "from core.isolation import checked_target\nfrom core.compliance import alerts, model\n"
          "import core.compliance.owner\nfrom execution import snapshot\nfrom execution.transport import request\n"
          "from . import checks\n")
    assert not _allowlist_hits(X, ok), _allowlist_hits(X, ok)
    hits = [h for rel, src in _sources().items() for h in _allowlist_hits(rel, src)]
    assert not hits, hits


def test_no_dynamic_import():
    """No star or dynamic import (CG._dynamic_hits): either would hide a module from the allowlist and from the D14
    closure."""
    for src in ("from execution.transport import *\n", "m = __import__('requests')\n",
                "import importlib\nm = importlib.import_module('requests')\n", "exec(src)\n", "eval(src)\n",
                "import runpy\n"):
        assert CG._dynamic_hits(X, src), src
    assert not CG._dynamic_hits(X, "import json\npattern = re.compile('a')\nfrom execution import snapshot\n")
    hits = [h for rel, src in _sources().items() for h in CG._dynamic_hits(rel, src)]
    assert not hits, hits


def test_only_transport_send_calls_requests_request():
    """Spec 8, E36: no post, put, patch, delete, request, send, urlopen, getresponse, connect or create_connection
    attribute call anywhere in execution/ but the single `session.request(...)` in the body of transport._send
    (E1R2-11), no process started through os, no reach into sys.modules. The bare `request(...)` the venue modules
    import from transport is not an attribute call."""
    for src in ("requests.post(u)\n", "s.request('GET', u)\n", "x.delete()\n", "requests.Session().send(p)\n",
                "c.getresponse()\n", "s.connect(a)\n", "store.put(k, v)\n", "y.patch(z)\n",
                "urllib.request.urlopen(u)\n", "socket.create_connection(a)\n", "os.system('curl')\n",
                "os.popen(c)\n", "os.startfile(p)\n", "os.execv(a, b)\n", "os.spawnl(0, a)\n", "os.fork()\n",
                "os.posix_spawn(p, a, e)\n", "from os import system\n", "run = os.system\n",
                "m = sys.modules['requests']\n"):
        assert _verb_hits(X, src), src
    send = ("def _send(method, url, *, headers, params, json_body, timeout):\n"
            "    with requests.Session() as session:\n"
            "        return session.request(method, url, headers=headers)\n")
    assert not _verb_hits(TRANSPORT, send), _verb_hits(TRANSPORT, send)
    assert _verb_hits(X, send)
    assert _verb_hits(TRANSPORT, "def other(session):\n    return session.request('GET', u)\n")
    assert _verb_hits(TRANSPORT, "def _send(method, url):\n    return requests.request(method, url)\n")
    assert _verb_hits(TRANSPORT, "class T:\n    def _send(self, session):\n        return session.request('GET', u)\n")
    assert not _verb_hits(X, "d.get(k)\nlines.append(x)\nanswer = request('kis', 'GET', p)\ntime.sleep(1)\n"
                             "os.fsync(fd)\nn = os.urandom(6)\nkind = os.name\n")
    hits = [h for rel, src in _sources().items() for h in _verb_hits(rel, src)]
    assert not hits, hits


def test_no_wall_clock_outside_poll_main():
    """E11: only the BODY of the module-level main() in execution/poll.py reads the wall clock (CG.CLOCKS, the
    email.utils and uuid names of EXTRA_CLOCKS, or any `from time import`); every other function takes `now` as an
    argument or calls transport._clock, which main() sets."""
    for src in ("x = datetime.now(timezone.utc)\n", "x = time.time()\n", "x = time.monotonic()\n",
                "from time import time\n", "import time as t\nx = t.time()\n", "x = date.today()\n",
                "x = datetime.datetime.utcnow()\n", "def main():\n    return datetime.now(timezone.utc)\n",
                "from email.utils import localtime, formatdate\n", "import email.utils\nx = email.utils.formatdate()\n",
                "from email import utils\nx = utils.localtime()\n", "import email.utils as eu\nx = eu.make_msgid()\n",
                "import uuid\nn = uuid.uuid1()\n", "import uuid as u\nn = u.uuid1()\n", "from uuid import uuid1\n"):
        assert _clock_hits(X, src), src
    for src in ("def main(at=datetime.now(timezone.utc)):\n    pass\n",
                "def poll_once():\n    return datetime.now(timezone.utc)\n",
                "def helper():\n    def main():\n        return time.time()\n",
                "class P:\n    def main(self):\n        return time.time()\n"):
        assert _clock_hits(CLOCK_MAIN, src), src
    main = ("def main(argv=None):\n    now = datetime.now(timezone.utc)\n"
            "    transport._clock = lambda: datetime.now(timezone.utc)\n    return now\n")
    assert not _clock_hits(CLOCK_MAIN, main), _clock_hits(CLOCK_MAIN, main)
    assert _clock_hits(X, main)
    assert not _clock_hits(X, "time.sleep(1)\n_sleep = time.sleep\nx = datetime.fromisoformat(s)\n"
                              "from email.utils import parsedate_to_datetime\nimport uuid\nn = str(uuid.uuid4())\n")
    hits = [h for rel, src in _sources().items() for h in _clock_hits(rel, src)]
    assert not hits, hits


def test_every_write_goes_through_checked_target():
    """Spec 4 "State files": every write opens a path checked_target judged immediately before (temp files
    included), folders are made only on a checked path, and nothing is deleted, renamed or copied any other way."""
    for src in ("open(p, 'ab')\n", "open(p, mode='w')\n", "open(p, 'r+')\n", "open(p, m)\n", "open(file=p, mode='x')\n",
                "p.open('a')\n", "p.open(mode='xb')\n", "os.replace(a, checked_target(b))\n",
                "os.replace(checked_target(a))\n", "p.mkdir()\n", "os.mkdir(p)\n", "os.makedirs(p)\n",
                "p.write_bytes(b'')\n", "p.write_text(s)\n", "p.touch()\n", "p.unlink()\n", "p.rename(q)\n",
                "p.rmdir()\n", "p.replace(q)\n", "p.replace(target=q)\n", "p.symlink_to(q)\n", "os.remove(p)\n",
                "os.unlink(p)\n",
                "os.rename(a, b)\n", "fd = os.open(p, flags)\n", "shutil.copy(a, b)\n", "import shutil\n",
                "from shutil import copyfile\n"):
        assert _write_hits(X, src), src
    ok = ("with open(checked_target(p, 'x'), 'ab') as fh:\n    fh.write(b'1')\n"
          "with open(p, 'rb') as fh:\n    data = fh.read()\n"
          "text = p.read_text(encoding='utf-8')\nwith p.open(encoding='utf-8') as fh:\n    pass\n"
          "checked_target(p.parent, 'folder').mkdir(parents=True, exist_ok=True)\n"
          "isolation.checked_target(q, 'folder').mkdir()\n"
          "os.replace(checked_target(a, 'tmp'), checked_target(b, 'file'))\n"
          "s = s.replace('a', 'b')\nt = moment.replace(tzinfo=KST)\nos.fsync(fh.fileno())\n")
    assert not _write_hits(X, ok), _write_hits(X, ok)
    hits = [h for rel, src in _sources().items() for h in _write_hits(rel, src)]
    assert not hits, hits


def test_init_is_empty_and_main_blocks_are_one_line():
    """execution/__init__.py exists and is 0 bytes (under the trailing-dot prefix the package itself is not acting,
    so it may hold no code), and a __main__ block is exactly `raise SystemExit(main())` (T-CTX-01 skips those
    bodies)."""
    probe = Path(os.environ["TRADEGEN_HOME"]) / "init_probe"        # the per-test temp home; removed with it
    probe.mkdir()
    (probe / "__init__.py").write_bytes(b"x = 1\n")
    assert CG._init_hits(probe / "__init__.py") and CG._init_hits(probe / "missing.py")
    assert not CG._init_hits(EXECUTION / "__init__.py"), f"{INIT} must exist and be 0 bytes"
    assert CG._main_block_hits(X, 'if __name__ == "__main__":\n    main()\n')
    assert CG._main_block_hits(X, 'if __name__ == "__main__":\n    import sys\n    raise SystemExit(main())\n')
    assert not CG._main_block_hits(X, 'if __name__ == "__main__":\n    raise SystemExit(main())\n')
    hits = [h for rel, src in _sources().items() for h in CG._main_block_hits(rel, src)]
    assert not hits, hits


def test_acting_prefix_covers_execution():
    """E1 spec 8, E29: every execution module is acting (T-CTX-01), the package itself is not, the runtime guard
    refuses a frame of an execution module, and the static scan of the real tree reports nothing."""
    from core.ficc import context_log as CL
    assert CL.is_acting_module("execution.poll") and CL.is_acting_module("execution.kis_inquiry"), \
        "execution.* is not an acting prefix"
    assert not CL.is_acting_module("execution") and not CL.is_acting_module("executions.x")
    frame = {"__name__": "execution.probe", "CL": CL}
    exec("def read():\n    CL.assert_not_acting_caller()\n", frame)
    try:
        frame["read"]()
    except CL.ContextIsolationError as exc:
        assert "execution.probe" in str(exc), exc
    else:
        raise AssertionError("a frame of execution.probe read a context surface")
    assert CL.static_isolation_report() == []


def test_only_evidence_names_evidence_path():
    """Spec 6: execution/evidence.py is the one writer of evidence.jsonl, so no other execution file even names
    owner.evidence_path (raw text)."""
    assert _evidence_hits(X, "path = owner.evidence_path()\n")
    assert _evidence_hits(X, "# owner.evidence_path() is the file\n")
    assert not _evidence_hits(EVIDENCE_WRITER, "path = owner.evidence_path()\n")
    assert not _evidence_hits(X, "path = owner.log_path()\nevidence = 1\n")
    hits = [h for rel, src in _sources().items() for h in _evidence_hits(rel, src)]
    assert not hits, hits


# --------------------------------------------------------------------------- #
# The harness itself
# --------------------------------------------------------------------------- #
def test_tests_start_no_process():
    """Contract 0.2: no execution test starts a process (a child has none of the wrapper's patches, and OKX
    public/time needs no key) or reloads a module (a reload points keys._ENV_FILE back at the real .env)."""
    for src in ("import subprocess\n", "from subprocess import run\n", "import multiprocessing\n",
                "from multiprocessing import Process\n", "import multiprocessing.pool\n", "import runpy\n",
                "x = sys.executable\n", "os.system(c)\n", "os.popen(c)\n", "os.startfile(p)\n", "os.execv(a, b)\n",
                "os.spawnv(0, a, b)\n", "importlib.reload(m)\n", "from importlib import reload\n"):
        assert _process_hits("tests/execution_x.py", src), src
    assert not _process_hits("tests/execution_x.py", 'a = "subprocess"\nb = "execution.poll"\nimport importlib\n'
                                                     'm = importlib.import_module("tests.execution_guards")\n')
    files = _test_sources()
    assert {"tests/execution_acceptance.py", "tests/execution_fixtures.py", "tests/execution_guards.py"} <= set(files)
    hits = [h for rel, src in files.items() for h in _process_hits(rel, src)]
    assert not hits, hits


def test_suite_runs_hermetic_in_a_temp_home_with_seams():
    """Every E1 test runs inside hermetic(), a fresh TRADEGEN_HOME and isolated(): no E1 key name in os.environ, the
    toast recorder in place of alerts._toast, no stray send. A nested wrapped call arms one more level, moves the
    home and clears the recorders, and afterwards removes a key name the inner test set; isolated() gives a key name
    that was set before it its value back."""
    from core.compliance import alerts
    from tests import execution_acceptance as EA
    from tests import execution_fixtures as F
    from tests import macro_acceptance as MA
    home = Path(os.environ["TRADEGEN_HOME"])
    assert MA._DEPTH > 0, "the hermetic guard is not armed"
    assert home.is_dir() and home.name.startswith("tradegen_home_"), home
    assert not home.resolve().is_relative_to((Path.home() / ".tradegen").resolve()), home
    assert not [n for n in F.KEY_NAMES if n in os.environ], "an E1 key name reached the test"
    assert alerts._toast("probe title", "probe body") is True and F.TOASTS[-1] == ("probe title", "probe body")
    assert F.STRAYS == [], F.STRAYS
    seen = []

    def inner():
        os.environ["KIS_APP_KEY"] = "set-by-the-inner-test"
        seen.append((MA._DEPTH, Path(os.environ["TRADEGEN_HOME"]), list(F.TOASTS)))

    EA._wrap(inner)()
    depth, inner_home, toasts = seen[0]
    assert depth == MA._DEPTH + 1 and inner_home != home and inner_home.name.startswith("tradegen_home_"), seen
    assert toasts == [], "isolated() did not clear the toast recorder"
    assert Path(os.environ["TRADEGEN_HOME"]) == home and not inner_home.exists(), seen
    assert "KIS_APP_KEY" not in os.environ, "a key name the inner test set survived it"
    os.environ["UPBIT_ACCESS_KEY"] = "set-before-isolated"
    try:
        with F.isolated(home):
            assert "UPBIT_ACCESS_KEY" not in os.environ, "isolated() left a key name in os.environ"
        assert os.environ.get("UPBIT_ACCESS_KEY") == "set-before-isolated", "isolated() lost a key name's value"
    finally:
        os.environ.pop("UPBIT_ACCESS_KEY", None)
    assert alerts._toast("after", "the nested call") is True and F.TOASTS[-1] == ("after", "the nested call")
    # Task 2: the transport and key seams
    from execution import keys, transport
    real, stub, bad = F.REAL_SEND, transport._send, transport._bad_tokens
    assert real is not None and (real.__module__, real.__name__) == ("execution.transport", "_send"), real
    assert (stub.__module__, stub.__name__) == (F.__name__, "_refuse_send"), stub
    try:
        stub("GET", "https://api.upbit.com/v1/ticker?markets=KRW-BTC", headers={}, params=None, json_body=None,
             timeout=10.0)
    except F.Refused:
        pass
    else:
        raise AssertionError("transport._send sent inside the suite")
    assert F.STRAYS == ["GET /v1/ticker"], F.STRAYS
    F.STRAYS.clear()
    assert keys._ENV_FILE == home / "no-such.env" and not keys._ENV_FILE.exists(), keys._ENV_FILE
    assert transport._clock() == F.NOW and transport._next_issue_at is None and transport._okx_offset_s is None
    assert bad == set() and F.SLEEPS == []
    transport._sleep(2.0)
    assert F.SLEEPS == [2.0], F.SLEEPS
    nested = []
    transport._next_issue_at, transport._okx_offset_s = 1.0, 2.0                # so the inner reset is visible
    try:
        EA._wrap(lambda: nested.append((F.REAL_SEND, transport._send, keys._ENV_FILE, transport._bad_tokens,
                                        transport._next_issue_at, transport._okx_offset_s)))()
        assert (transport._next_issue_at, transport._okx_offset_s) == (1.0, 2.0), "a nested exit lost a value"
    finally:
        transport._next_issue_at = transport._okx_offset_s = None
    assert nested[0][0] is real and nested[0][1] is stub and nested[0][3] is not bad, nested
    assert nested[0][2].parent != home and nested[0][2].name == "no-such.env", nested
    assert nested[0][4:] == (None, None), "isolated() carried a token gap or an OKX offset into the test"
    assert F.REAL_SEND is real and transport._send is stub and transport._bad_tokens is bad
    assert keys._ENV_FILE == home / "no-such.env"


def _flagged(run) -> None:
    """`run()` (a wrapped test) fails with the wrapper's real-home message."""
    try:
        run()
    except AssertionError as exc:
        assert "the test touched the real ~/.tradegen" in str(exc), exc
    else:
        raise AssertionError("a change under a real home was not flagged")


def _append(path: Path) -> None:
    with open(path, "ab") as fh:
        fh.write(b"{}\n")


@contextlib.contextmanager
def _held(path: Path):
    """`path` locked by a second in-process handle, as the owner's poller holds poll.lock (contract 0.2)."""
    with open(path, "a+b") as fh:
        fh.seek(0)
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            yield
        finally:
            fh.seek(0)
            if os.name == "nt":
                msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(fh, fcntl.LOCK_UN)


def test_harness_flags_a_change_to_the_real_homes():
    """The wrapper fails a test that changes the real ~/.tradegen/execution, ~/.tradegen/compliance or
    ~/.tradegen/kis_token.json (stand-ins here). While another handle holds execution/poll.lock (the owner's
    running poller, seen by the probe before the test or after it), only the set of paths under execution/ and of
    the token file counts there, the daily inquiry files are left out, and the compliance home is still watched in
    full."""
    from tests import execution_acceptance as EA
    fake = Path(os.environ["TRADEGEN_HOME"]) / "fake_real"        # the per-test temp home; removed with it
    execution, compliance, token = fake / "execution", fake / "compliance", fake / "kis_token.json"
    execution.mkdir(parents=True)
    compliance.mkdir()
    token.write_bytes(b"{}")
    (execution / "inquiry-20261024.jsonl").write_bytes(b"{}\n")
    (execution / "alerts.jsonl").write_bytes(b"{}\n")
    keep = EA._REAL
    try:
        EA._REAL = (execution, compliance, token)
        assert not EA._poller_running()
        EA._wrap(lambda: None)()                                    # nothing changed: passes
        _flagged(EA._wrap(lambda: (compliance / "owner.jsonl").write_bytes(b"{}\n")))
        _flagged(EA._wrap(lambda: _append(execution / "alerts.jsonl")))
        _flagged(EA._wrap(lambda: _append(execution / "inquiry-20261024.jsonl")))
        _flagged(EA._wrap(lambda: token.write_bytes(b'{"access_token": "x"}')))
        with _held(execution / "poll.lock"):
            assert EA._poller_running(), "a held poll.lock was not seen"
            EA._wrap(lambda: (_append(execution / "inquiry-20261024.jsonl"), _append(execution / "alerts.jsonl"),
                              (execution / "inquiry-20261025.jsonl").write_bytes(b"{}\n"),
                              token.write_bytes(b'{"access_token": "refreshed"}')))()
            _flagged(EA._wrap(lambda: (execution / "other.jsonl").write_bytes(b"{}\n")))
            _flagged(EA._wrap(lambda: (compliance / "alerts.jsonl").write_bytes(b"{}\n")))
            _flagged(EA._wrap(lambda: _append(compliance / "owner.jsonl")))    # a kept file grown: full listing only
        assert not EA._poller_running(), "the probe still sees poll.lock held"
        with contextlib.ExitStack() as stack:                 # a poller that starts during the test counts too
            EA._wrap(lambda: (stack.enter_context(_held(execution / "poll.lock")),
                              _append(execution / "alerts.jsonl")))()
    finally:
        EA._REAL = keep


def test_a_stray_send_fails_a_passing_test():
    """isolated() fails a test that returns normally after a refused or unrouted send (E28): the venue snapshots let
    Refused and AssertionError propagate, and STRAYS catches a send whose error was swallowed anyway."""
    from tests import execution_acceptance as EA
    from tests import execution_fixtures as F
    try:
        EA._wrap(lambda: F.STRAYS.append("GET /v1/ticker"))()
    except AssertionError as exc:
        assert "GET /v1/ticker" in str(exc), exc
    else:
        raise AssertionError("a test that left a stray send passed")
    finally:
        F.STRAYS.clear()                                            # the inner test's stray, not this test's
    EA._wrap(lambda: (F.STRAYS.append("GET /v1/ticker"), F.STRAYS.clear()))()


def test_aggregator_skips_missing_and_isolates_broken_modules():
    """Contract 3.1: an absent module is skipped, one that fails to import becomes a single `<module>/import` entry
    that re-raises, a `test_*` name imported from elsewhere is not collected, an empty run exits 1, and neither the
    aggregator nor the fixtures import execution or the fixtures outside a function body (E28)."""
    from tests import execution_acceptance as EA
    probe = Path(os.environ["TRADEGEN_HOME"]) / "probe"
    probe.mkdir()
    mixed = types.ModuleType("tests.execution_mixed")
    exec("from tests.execution_fixtures import isolated as test_imported\ndef test_own():\n    pass\n", vars(mixed))
    for stem in ("execution_broken", "execution_mixed"):
        (probe / f"{stem}.py").write_bytes(b"")
    keep = EA.TESTS, EA.MODULES
    sys.modules.update({"tests.execution_broken": None, "tests.execution_mixed": mixed})   # None: import raises
    try:
        EA.TESTS, EA.MODULES = probe, ("execution_broken", "execution_absent", "execution_mixed")
        found = EA.tests()
    finally:
        EA.TESTS, EA.MODULES = keep
        for stem in ("execution_broken", "execution_mixed"):
            sys.modules.pop(f"tests.{stem}", None)
    assert [n for n, _f in found] == ["execution_broken/import", "execution_mixed/test_own"], found
    try:
        found[0][1]()
    except ImportError:
        pass
    else:
        raise AssertionError("the broken module's entry did not re-raise its import error")
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = EA._main(["no such test"])
    assert code == 1 and out.getvalue().strip() == "0/0 passed, 0 failed, 0 not run", (code, out.getvalue())
    for src in ("from tests import execution_fixtures\n", "import execution.transport\n",
                "with x:\n    from execution import keys\n"):
        assert _eager_imports("tests/x.py", src), src
    assert not _eager_imports("tests/x.py", "def f():\n    from execution import transport\n"
                                            "    from tests.execution_fixtures import isolated\nimport tests.notrun\n")
    for rel in ("tests/execution_acceptance.py", "tests/execution_fixtures.py"):
        eager = _eager_imports(rel, (ROOT / rel).read_text(encoding="utf-8"))
        assert not eager, (rel, eager)


# --------------------------------------------------------------------------- #
# Registration
# --------------------------------------------------------------------------- #
def test_suite_is_registered_in_run_all_and_readme():
    """`tests/run_all.py --suite execution` selects this suite, and both hand-written suite lists name it, read
    through CG._suite_names (README.md:12 already says "execution", so a substring check would prove nothing)."""
    from tests import run_all
    names = [n for n, _f in run_all.select(run_all.tests(), suite="execution")]
    assert any(n.startswith("execution/execution_guards/") for n in names), names
    for path in (ROOT / "tests" / "run_all.py", ROOT / "README.md"):
        assert "execution" in CG._suite_names(path.read_text(encoding="utf-8")), path.name


# --------------------------------------------------------------------------- #
# Task 2: the pinned allowlists, the exact-string rules, the transport-only path and the pinned _send
# (contract 0.5, 4.5 and 7; spec 5, 8 "Read-only guards", 11; E10, E36, E1R2-11)
# --------------------------------------------------------------------------- #
KIS_FILE = "execution/kis_inquiry.py"      # the one file that may name KIS account fields and /trading/ paths
UPBIT_FILE = "execution/upbit_inquiry.py"  # the one file that may name the Upbit order and withdrawal paths
POLL = "execution/poll.py"                 # the one importer of the transport module (for transport._clock)
KIS_ORDER_WORDS = ("order-cash", "order-credit", "order-rvsecncl", "order-resv", "daytime-order", "/trading/order",
                   "/trading/daytime")                       # raw, lower-cased, in kis_inquiry.py
UPBIT_EXACT = frozenset({"/v1/order", "/v1/orders/open", "/v1/orders/closed", "/v1/withdraws", "/v1/withdraws/coin_addresses"})
UPBIT_TOKEN = re.compile(r"(?i)/v1/(?:order|withdraw)[A-Za-z0-9_/\-]*")
KIS_TOKEN = re.compile(r"/uapi/[^\s'\"]*")
KIS_GET_PATHS = frozenset({                # the nine GET paths of contract section 7, written out here (never read
    "/uapi/domestic-stock/v1/trading/inquire-balance",          # from kis_inquiry.ENDPOINTS)
    "/uapi/domestic-stock/v1/trading/inquire-psbl-rvsecncl",
    "/uapi/domestic-stock/v1/trading/inquire-daily-ccld",
    "/uapi/domestic-stock/v1/trading/inquire-account-balance",
    "/uapi/domestic-stock/v1/trading/intgr-margin",
    "/uapi/overseas-stock/v1/trading/inquire-balance",
    "/uapi/overseas-stock/v1/trading/inquire-nccs",
    "/uapi/overseas-stock/v1/trading/inquire-ccnl",
    "/uapi/overseas-stock/v1/trading/inquire-present-balance",
})
KIS_TRS = frozenset({"TTTC8434R", "TTTC0084R", "TTTC0081R", "CTRP6548R", "TTTC0869R", "TTTS3012R", "TTTS3018R",
                     "TTTS3035R", "CTRP6504R"})            # the nine TR ids of contract section 7, written out here
TR_SHAPE = re.compile(r"(?i)(?<![A-Za-z0-9])[A-Z]{4}[0-9]{4}[A-Z](?![A-Za-z0-9])")
ORDER_TR = re.compile(r"(?i)[A-Z]{4}[0-9]{4}U")
OKX_ORDER_PATH = "/api/v5/trade/order"     # the GET also serves the order POST: never a string constant (spec 5)
TRANSPORT_NAMES = frozenset({"request", "require_keys", "Answer", "InquiryRefused", "InquiryError", "AuthError",
                             "KeyMissing", "inquiry_clock"})  # public standalone inquiry clock, no implicit time
CREDENTIAL_NAMES = ("KIS_APP_KEY", "KIS_APP_SECRET", "UPBIT_ACCESS_KEY", "UPBIT_SECRET_KEY", "OKX_API_KEY",
                    "OKX_API_SECRET", "OKX_API_PASSPHRASE")
SEND_SOURCE = ("def _send(method, url, *, headers, params, json_body, timeout):\n"     # ast.unparse of the whole
               "    options = route_options(url)\n"
               "    with requests.Session() as session:\n"                               # _send of section 6
               "        session.trust_env = False\n"                                     # (E1R2-11; checked with
               "        resp = session.request(method, url, headers=headers, params=params, json=json_body, "
               "timeout=timeout, allow_redirects=False, proxies=options.proxies, verify=options.verify)\n"
               "        return (resp.status_code, resp.headers, resp.content)")
# transport.py's own names: outside it, none of them is a name, an attribute, an imported name or a getattr string
TRANSPORT_ONLY = frozenset({"requests", "HOSTS", "CREDENTIALS", "_send", "_rules", "_query", "_upbit_jwt",
                            "_okx_timestamp", "_okx_sign", "_kis_token", "_read_token", "_write_token",
                            "_check_answer", "_next_issue_at", "_okx_offset_s", "_bad_tokens", "_headers",
                            "_TokenRejected", "_now", "_context_clock", "_INQUIRY_CLOCK"})
# attributes no module but transport.py reads or writes (poll.py's one `transport._clock = ...` aside): the two
# send-time seams, the modules a getattr chain would reach, and request (so it is always called by its own name)
SEAM_ATTRS = frozenset({"_clock", "_sleep", "transport", "keys", "request"})
GLOBALS_OK = frozenset({"_next_issue_at", "_okx_offset_s"})   # the only `global` names, in transport.py only
DUNDERS = frozenset({"__globals__", "__dict__", "__builtins__", "__code__", "__closure__", "__subclasses__",
                     "__getattribute__", "__getstate__", "__self__"})   # a module's __getstate__() is its namespace
FRAME_ATTRS = frozenset({"f_globals", "f_locals", "f_back", "f_builtins", "f_code", "tb_frame", "tb_next",
                         "gi_frame", "cr_frame", "ag_frame", "_getframe"})   # a frame reaches another module's globals
REBINDERS = frozenset({"setattr", "delattr", "vars", "globals"})
BINDERS = (ast.Assign, ast.AugAssign, ast.AnnAssign, ast.Delete, ast.For, ast.AsyncFor, ast.withitem,
           ast.comprehension)
SEND_TEMPLATE = ("import requests\n\n"                # contract section 6's _send, wrapped and commented as written
                 "def _send(method, url, *, headers, params, json_body, timeout):\n"
                 "    options = route_options(url)\n"
                 "    with requests.Session() as session:\n"
                 "        session.trust_env = False                  # no proxy, CA bundle or .netrc\n"
                 "        resp = session.request(method, url, headers=headers, params=params, json=json_body,\n"
                 "                               timeout=timeout, allow_redirects=False, proxies=options.proxies, verify=options.verify)\n"
                 "        return resp.status_code, resp.headers, resp.content\n")


def _upbit_token_hits(rel: str, src: str) -> list[str]:
    """Raw text: every Upbit order or withdrawal path token is one of five exact inquiry paths, in upbit_inquiry.py."""
    return [f"{rel}: {m.group(0)!r}: only the five exact Upbit inquiry paths, only in {UPBIT_FILE}"
            for m in UPBIT_TOKEN.finditer(src) if rel != UPBIT_FILE or m.group(0) not in UPBIT_EXACT]


def _kis_token_hits(rel: str, src: str) -> list[str]:
    """Raw text: every /uapi/ token is one of the nine GET paths, in kis_inquiry.py, which names no order path."""
    hits = [f"{rel}: {m.group(0)!r}: only the nine KIS GET paths, only in {KIS_FILE}"
            for m in KIS_TOKEN.finditer(src) if rel != KIS_FILE or m.group(0) not in KIS_GET_PATHS]
    if rel == KIS_FILE:
        hits += [f"{rel}: {w!r}: a KIS order path word" for w in KIS_ORDER_WORDS if w in src.lower()]
    return hits


def _tr_hits(rel: str, src: str) -> list[str]:
    """Raw text: every TR-shaped token is one of the nine pinned TR ids, in kis_inquiry.py; no order TR shape (four
    letters, four digits, U) in any file, in any case; and no string constant equal to the OKX single-order path."""
    hits = [f"{rel}: {m.group(0)!r}: only the nine pinned TR ids, only in {KIS_FILE}"
            for m in TR_SHAPE.finditer(src) if rel != KIS_FILE or m.group(0) not in KIS_TRS]
    hits += [f"{rel}: {m.group(0)!r}: a KIS order TR shape" for m in ORDER_TR.finditer(src)]
    return hits + [f"{rel}:{n.lineno}: {OKX_ORDER_PATH!r}" for n in ast.walk(ast.parse(src))
                   if isinstance(n, ast.Constant) and n.value == OKX_ORDER_PATH]


def _token_hits(rel: str, src: str) -> list[str]:
    """The Upbit, KIS-path, TR and order-TR rules of contract 0.5, docstrings and comments included."""
    return _upbit_token_hits(rel, src) + _kis_token_hits(rel, src) + _tr_hits(rel, src)


def _targets(node: ast.AST) -> list[ast.expr]:
    """The binding targets of an assignment, del, for, with-item or comprehension node, tuples flattened."""
    if isinstance(node, (ast.Assign, ast.Delete)):
        todo = list(node.targets)
    elif isinstance(node, ast.withitem):
        todo = [node.optional_vars] if node.optional_vars is not None else []
    else:                                   # AugAssign, AnnAssign, For, AsyncFor, comprehension
        todo = [node.target]
    out = []
    while todo:
        target = todo.pop()
        if isinstance(target, (ast.Tuple, ast.List)):
            todo.extend(target.elts)
        elif isinstance(target, ast.Starred):
            todo.append(target.value)
        else:
            out.append(target)
    return out


def _rebind_ok(rel: str, node: ast.AST, target: ast.Attribute, funcs: tuple[str, ...]) -> bool:
    """The only attribute targets allowed: `session.trust_env = False` in transport._send, `transport._clock = ...`
    in poll.main, and `self.<name> = ...` in an __init__ (an exception's own fields)."""
    text = ast.unparse(target)
    if isinstance(node, ast.Assign) and (rel, funcs, text) in ((TRANSPORT, ("_send",), "session.trust_env"),
                                                               (POLL, ("main",), "transport._clock")):
        return True
    return (isinstance(node, (ast.Assign, ast.AnnAssign)) and funcs[-1:] == ("__init__",)
            and isinstance(target.value, ast.Name) and target.value.id == "self")


def _import_path_hits(rel: str, tree: ast.AST) -> list[str]:
    """Outside transport.py: transport only as `from execution.transport import <TRANSPORT_NAMES>` with no alias,
    the module only as `from execution import transport` in poll.py, execution.keys only as `from execution import
    keys` in kis_inquiry.py, and no transport-only name imported from any execution module."""
    hits = []
    for node, module, names, _f in CG._imports(rel, tree):
        aliased = {a.name for a in node.names if a.asname}
        if isinstance(node, ast.Import):
            if any(module == m or module.startswith(m + ".") for m in ("execution.transport", "execution.keys")):
                hits.append(f"{rel}:{node.lineno}: import {module}")
        elif module == "execution.transport":
            bad = sorted(n for n in names if n not in TRANSPORT_NAMES or n in aliased)
            if bad:
                hits.append(f"{rel}:{node.lineno}: from execution.transport import {', '.join(bad)}")
        elif module == "execution.keys" or module.startswith("execution.keys."):
            hits.append(f"{rel}:{node.lineno}: from {module} import ...")
        elif module == "execution" or module.startswith("execution."):
            for name in names:
                allowed = module == "execution" and name not in aliased and (
                    (name == "transport" and rel == POLL) or (name == "keys" and rel == KIS_FILE))
                if (name in ("transport", "keys") or name in TRANSPORT_ONLY) and not allowed:
                    hits.append(f"{rel}:{node.lineno}: from {module} import {name}")
    return hits


def _path_hits(rel: str, src: str) -> list[str]:
    """Transport is the only way out, and nothing rebinds from outside (contract 0.5, E36).

    Every file: no `global` but transport.py's two; no attribute as the target of an assignment, augmented or
    annotated assignment, del, for, with or comprehension, except the three of `_rebind_ok`; no setattr, delattr,
    vars or globals; getattr only with a string-constant name that does not start with `_` and is not a
    transport-only, seam or frame name; no DUNDERS attribute (__globals__, __dict__, __getstate__, __self__ and the
    rest) and no FRAME_ATTRS attribute (a frame or traceback reaches another module's globals; exc.__traceback__
    itself is allowed); `object.__setattr__(self, ...)` only in a __post_init__; no sys.modules in any form.
    Outside transport.py also: no transport-only name (requests, the hosts, the credentials, _send, the signing and
    token helpers) as a name, an attribute or a string constant; no `_clock`, `_sleep`, `transport`, `request` or
    `keys` attribute (a `.keys()` call aside); the
    import rules of `_import_path_hits`; every `request` name the function of a call whose second positional
    argument is the literal "GET"; in poll.py the name transport only in `transport._clock = ...` in main; in
    kis_inquiry.py the name keys only in its one `keys.read(ACCOUNT_NAMES)` call; no credential name, even in a
    docstring or comment."""
    tree, hits, ok = ast.parse(src), [], set()     # ok: id() of the nodes an allowed form covers
    outside = rel != TRANSPORT
    if rel == KIS_FILE:
        reads = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and ast.unparse(n.func) == "keys.read"
                 and [ast.unparse(a) for a in n.args] == ["ACCOUNT_NAMES"] and not n.keywords]
        ok.update({id(reads[0].func.value)} if len(reads) == 1 else set())
    for node, funcs in CG._walk(tree):              # parents come before their children, so `ok` is ready
        if isinstance(node, ast.Global) and (outside or not set(node.names) <= GLOBALS_OK):
            hits.append(f"{rel}:{node.lineno}: global {', '.join(node.names)}")
        elif isinstance(node, BINDERS):
            for target in _targets(node):
                if isinstance(target, ast.Attribute) and _rebind_ok(rel, node, target, funcs):
                    ok.update({id(target), id(target.value)})
                elif isinstance(target, ast.Attribute):
                    hits.append(f"{rel}:{target.lineno}: rebinds {ast.unparse(target)}")
        elif isinstance(node, ast.Call):
            func, args = ast.unparse(node.func), node.args
            first_two_plain = len(args) >= 2 and not any(isinstance(a, ast.Starred) for a in args[:2])
            if (func == "getattr" and first_two_plain and isinstance(args[1], ast.Constant)
                    and isinstance(args[1].value, str) and not args[1].value.startswith("_")
                    and args[1].value not in TRANSPORT_ONLY | SEAM_ATTRS | FRAME_ATTRS):
                ok.add(id(node.func))
            elif func == "request" and first_two_plain and isinstance(args[1], ast.Constant) and args[1].value == "GET":
                ok.add(id(node.func))
            elif func == "object.__setattr__" and funcs[-1:] == ("__post_init__",) and args and (
                    ast.unparse(args[0]) == "self"):
                ok.add(id(node.func))
            elif isinstance(node.func, ast.Attribute) and node.func.attr == "keys" and not args and not node.keywords:
                ok.add(id(node.func))                                   # a mapping's .keys()
        if isinstance(node, ast.Name):
            name, seen = node.id, id(node) in ok
            if name in REBINDERS or name in DUNDERS or (name == "getattr" and not seen):
                hits.append(f"{rel}:{node.lineno}: {name}")
            elif outside and (name in TRANSPORT_ONLY or (name == "request" and not seen)
                              or (name == "transport" and rel == POLL and not seen)
                              or (name == "keys" and rel == KIS_FILE and not seen)):
                hits.append(f"{rel}:{node.lineno}: {name} outside its one allowed use")
        elif isinstance(node, ast.Attribute):
            if node.attr in DUNDERS or node.attr in FRAME_ATTRS or ast.unparse(node) == "sys.modules" or (
                    node.attr in ("__setattr__", "__delattr__") and id(node) not in ok):
                hits.append(f"{rel}:{node.lineno}: {ast.unparse(node)}")
            elif outside and id(node) not in ok and (node.attr in TRANSPORT_ONLY or node.attr in SEAM_ATTRS):
                hits.append(f"{rel}:{node.lineno}: {ast.unparse(node)} outside {TRANSPORT}")
        elif outside and isinstance(node, ast.Constant) and node.value in TRANSPORT_ONLY:
            hits.append(f"{rel}:{node.lineno}: the string {node.value!r} outside {TRANSPORT}")
    if outside:
        hits += _import_path_hits(rel, tree)
        hits += [f"{rel}: names the credential {n}" for n in CREDENTIAL_NAMES if n in src]
    return hits


def _send_def(src: str) -> str | None:
    """ast.unparse of the one module-level `def _send` of `src`; None when there is not exactly one or the name
    `_send` is bound anywhere else."""
    tree = ast.parse(src)
    defs = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_send"]
    rebound = [n for n in ast.walk(tree) if isinstance(n, ast.Name) and n.id == "_send"
               and isinstance(n.ctx, (ast.Store, ast.Del))]
    return ast.unparse(defs[0]) if len(defs) == 1 and not rebound else None


def _requests_hits(src: str) -> list[str]:
    """Every `requests` in transport.py is its plain `import requests`, the requests.Session in _send or
    requests.exceptions.ConnectionError (E1R2-11)."""
    tree, hits, allowed = ast.parse(src), [], set()
    for node, funcs in CG._walk(tree):
        if isinstance(node, ast.Import):
            hits += [f"{node.lineno}: import {a.name}" + (f" as {a.asname}" if a.asname else "")
                     for a in node.names if a.name.split(".")[0] == "requests" and (a.asname or a.name != "requests")]
        elif isinstance(node, ast.ImportFrom) and (node.module or "").split(".")[0] == "requests":
            hits.append(f"{node.lineno}: from {node.module} import ...")
        elif isinstance(node, ast.Attribute):
            text = ast.unparse(node)
            if text == "requests.Session" and funcs == ("_send",):
                allowed.add(id(node.value))
            elif text == "requests.exceptions.ConnectionError":
                allowed.add(id(node.value.value))
        elif isinstance(node, ast.Name) and node.id == "requests" and id(node) not in allowed:
            hits.append(f"{node.lineno}: requests used outside its three allowed forms")
    return hits


def test_allowlists_are_pinned():
    """Contract 7 (spec 5: "a test pins each one exactly"): every allowlist equals the set written out here, the hosts
    are the real ones, the KIS token POST is the only entry that is not a GET, every KIS GET path has exactly one TR
    id and it ends in R, and the OKX single-order path is not listed."""
    from execution import kis_inquiry, okx_inquiry, transport, upbit_inquiry
    kis_tr_ids = frozenset({
        ("/uapi/domestic-stock/v1/trading/inquire-balance", "TTTC8434R"),
        ("/uapi/domestic-stock/v1/trading/inquire-psbl-rvsecncl", "TTTC0084R"),
        ("/uapi/domestic-stock/v1/trading/inquire-daily-ccld", "TTTC0081R"),
        ("/uapi/domestic-stock/v1/trading/inquire-account-balance", "CTRP6548R"),
        ("/uapi/domestic-stock/v1/trading/intgr-margin", "TTTC0869R"),
        ("/uapi/overseas-stock/v1/trading/inquire-balance", "TTTS3012R"),
        ("/uapi/overseas-stock/v1/trading/inquire-nccs", "TTTS3018R"),
        ("/uapi/overseas-stock/v1/trading/inquire-ccnl", "TTTS3035R"),
        ("/uapi/overseas-stock/v1/trading/inquire-present-balance", "CTRP6504R"),
    })
    upbit = frozenset({("GET", "/v1/accounts"), ("GET", "/v1/order"), ("GET", "/v1/orders/open"), ("GET", "/v1/orders/closed"),
                       ("GET", "/v1/withdraws"), ("GET", "/v1/withdraws/coin_addresses"), ("GET", "/v1/deposits"),
                       ("GET", "/v1/api_keys"), ("GET", "/v1/status/wallet"), ("GET", "/v1/ticker")})
    okx = frozenset({("GET", "/api/v5/account/config"), ("GET", "/api/v5/account/balance"),
                     ("GET", "/api/v5/account/positions"), ("GET", "/api/v5/asset/balances"),
                     ("GET", "/api/v5/asset/asset-valuation"), ("GET", "/api/v5/finance/savings/balance"),
                     ("GET", "/api/v5/finance/flexible-loan/loan-info"), ("GET", "/api/v5/trade/orders-pending"),
                     ("GET", "/api/v5/trade/orders-algo-pending"), ("GET", "/api/v5/trade/fills"),
                     ("GET", "/api/v5/asset/deposit-history"), ("GET", "/api/v5/asset/withdrawal-history"),
                     ("GET", "/api/v5/public/time"), ("GET", "/api/v5/market/ticker")})
    assert {p for p, _t in kis_tr_ids} == KIS_GET_PATHS and {t for _p, t in kis_tr_ids} == KIS_TRS
    sets = (kis_inquiry.ENDPOINTS, kis_inquiry.TR_IDS, kis_inquiry.PUBLIC, upbit_inquiry.ENDPOINTS,
            upbit_inquiry.PUBLIC, okx_inquiry.ENDPOINTS, okx_inquiry.PUBLIC)
    assert all(type(s) is frozenset for s in sets), [type(s).__name__ for s in sets]
    kis = frozenset({("POST", "/oauth2/tokenP")} | {("GET", p) for p in KIS_GET_PATHS})
    assert kis_inquiry.ENDPOINTS == kis, sorted(kis_inquiry.ENDPOINTS ^ kis)
    assert kis_inquiry.TR_IDS == kis_tr_ids, sorted(kis_inquiry.TR_IDS ^ kis_tr_ids)
    assert kis_inquiry.PUBLIC == frozenset() and kis_inquiry.ACCOUNT_NAMES == ("KIS_ACCOUNT_8", "KIS_ACCOUNT_PD")
    assert upbit_inquiry.ENDPOINTS == upbit, sorted(upbit_inquiry.ENDPOINTS ^ upbit)
    assert upbit_inquiry.PUBLIC == frozenset({"/v1/ticker"})
    assert okx_inquiry.ENDPOINTS == okx, sorted(okx_inquiry.ENDPOINTS ^ okx)
    assert okx_inquiry.PUBLIC == frozenset({"/api/v5/public/time", "/api/v5/market/ticker"})
    assert okx_inquiry.ALGO_TYPES == ("conditional", "oco", "trigger", "move_order_stop", "iceberg", "twap", "chase")
    assert type(transport.HOSTS) is types.MappingProxyType and dict(transport.HOSTS) == {
        "kis": "https://openapi.koreainvestment.com:9443", "upbit": "https://api.upbit.com",
        "okx": "https://www.okx.com"}, dict(transport.HOSTS)
    assert type(transport.CREDENTIALS) is types.MappingProxyType and dict(transport.CREDENTIALS) == {
        "kis": ("KIS_APP_KEY", "KIS_APP_SECRET"), "upbit": ("UPBIT_ACCESS_KEY", "UPBIT_SECRET_KEY"),
        "okx": ("OKX_API_KEY", "OKX_API_SECRET", "OKX_API_PASSPHRASE")}
    assert transport.KIS_TOKEN_PATH == "/oauth2/tokenP"
    assert sorted(e for e in kis_inquiry.ENDPOINTS if e[0] != "GET") == [("POST", "/oauth2/tokenP")]
    assert all(m == "GET" for m, _p in upbit_inquiry.ENDPOINTS | okx_inquiry.ENDPOINTS)
    gets = {p for m, p in kis_inquiry.ENDPOINTS if m == "GET"}
    assert {p for p, _t in kis_inquiry.TR_IDS} == gets and len(kis_inquiry.TR_IDS) == len(gets)   # one TR per path
    assert all(p.startswith("/uapi/") for p in gets) and all(t.endswith("R") for _p, t in kis_inquiry.TR_IDS)
    assert ("GET", OKX_ORDER_PATH) not in okx_inquiry.ENDPOINTS
    for module in (upbit_inquiry, okx_inquiry):
        assert module.PUBLIC <= {p for _m, p in module.ENDPOINTS}, module.__name__


def test_kis_strings_are_exact():
    """Contract 0.5 and spec 8 "KIS exception": every /uapi/ string in execution/ is one of the nine GET paths, in
    kis_inquiry.py only, and that file holds no order path word, raw text included. The nine paths are written out
    here, never read from kis_inquiry.ENDPOINTS, so an edit that adds an order path to the file and to its
    allowlist still fails."""
    for path in sorted(KIS_GET_PATHS):
        assert not _kis_token_hits(KIS_FILE, f'P = "{path}"\n'), path
        assert _kis_token_hits(X, f'P = "{path}"\n') and _kis_token_hits(TRANSPORT, f'"""{path}"""\n'), path
    for src in ('P = "/uapi/overseas-stock/v1/trading/order"\n',
                'P = "/uapi/domestic-stock/v1/trading/inquire-psbl-order"\n',
                'P = "/uapi/overseas-stock/v1/trading/"\n',
                'P = "/uapi/domestic-stock/v1/trading/" + "order-cash"\n',
                '"""reads `/uapi/domestic-stock/v1/trading/inquire-balance` only"""\n',   # the backtick is in it
                'P = "/uapi/domestic-stock/v1/trading/inquire-balance?x=1"\n'):
        assert _kis_token_hits(KIS_FILE, src), src
    for word in KIS_ORDER_WORDS:
        assert _kis_token_hits(KIS_FILE, f"# {word.upper()}\n"), word
    real = (EXECUTION / "kis_inquiry.py").read_text(encoding="utf-8")
    order = '    ("GET", "/uapi/overseas-stock/v1/trading/order"),\n'
    patched = real.replace("ENDPOINTS = frozenset({\n", "ENDPOINTS = frozenset({\n" + order, 1)
    assert patched != real and _kis_token_hits(KIS_FILE, patched)
    from execution import kis_inquiry
    keep = kis_inquiry.ENDPOINTS
    try:
        kis_inquiry.ENDPOINTS = keep | {("GET", "/uapi/overseas-stock/v1/trading/order")}
        assert _kis_token_hits(KIS_FILE, patched)            # the rule never reads the module's allowlist
    finally:
        kis_inquiry.ENDPOINTS = keep
    files = _sources()
    assert KIS_FILE in files and TRANSPORT in files, sorted(files)
    hits = [h for rel, src in files.items() for h in _kis_token_hits(rel, src)]
    assert not hits, hits


def test_upbit_strings_are_exact():
    """Contract 0.5 and spec 8 "Upbit exception": every Upbit order or withdrawal path token in execution/ is one of
    /v1/order, /v1/orders/open, /v1/orders/closed, /v1/withdraws and /v1/withdraws/coin_addresses,
    in upbit_inquiry.py only; the separate endpoint pin permits only GET for these paths."""
    for path in sorted(UPBIT_EXACT):
        assert not _upbit_token_hits(UPBIT_FILE, f'P = "{path}"\n'), path
    for path in ("/v1/withdraws/coin", "/v1/withdraws/krw", "/v1/withdraws/chance", "/v1/orders", "/v1/order/new",
                 "/v1/orders/uuids", "/v1/orders/chance", "/v1/orders/cancel_and_new", "/V1/ORDERS/OPEN",
                 "/v1/orders/open/x"):
        assert _upbit_token_hits(UPBIT_FILE, f'P = "{path}"\n'), path
    assert _upbit_token_hits(X, 'P = "/v1/orders/open"\n') and _upbit_token_hits(TRANSPORT, "# /v1/withdraws\n")
    assert not _upbit_token_hits(X, 'A = "/v1/accounts"\nD = "/v1/deposits"\nO = "/api/v5/trade/orders-pending"\n'
                                    'K = "/uapi/domestic-stock/v1/trading/inquire-balance"\n')
    files = _sources()
    assert UPBIT_FILE in files, sorted(files)
    hits = [h for rel, src in files.items() for h in _upbit_token_hits(rel, src)]
    assert not hits, hits


def test_no_order_tr_anywhere():
    """Contract 0.5: every TR-shaped token is one of the nine pinned ids, upper-case, in kis_inquiry.py only; no
    file in execution/ holds the order TR shape (four letters, four digits, U) in any case, raw text included; and
    no file holds the OKX single-order path as a string constant."""
    for tr in sorted(KIS_TRS):
        assert not _tr_hits(KIS_FILE, f'T = "{tr}"\n'), tr
        assert _tr_hits(X, f'T = "{tr}"\n'), tr
    for src in ('T = "tttc0012u"\n', "# TTTT1002U\n", '"""ttts1002u"""\n', 'T = "TTTC0802U"\n', 'T = "xTTTC0011U"\n'):
        for rel in (X, KIS_FILE, UPBIT_FILE, TRANSPORT):
            assert _tr_hits(rel, src), (rel, src)
    assert _tr_hits(KIS_FILE, 'T = "TTTC0084X"\n') and _tr_hits(KIS_FILE, 'T = "tttc8434r"\n')
    assert not _tr_hits(TRANSPORT, 'C = {"EGW00121", "KIOK0510", "HS512", "SHA512", "50120", "dead1234beef"}\n')
    for rel in (X, "execution/okx_inquiry.py", TRANSPORT):
        assert _tr_hits(rel, f'P = "{OKX_ORDER_PATH}"\n'), rel
    assert not _tr_hits("execution/okx_inquiry.py", 'P = "/api/v5/trade/orders-pending"\n')
    assert _token_hits(X, 'T = "TTTC8434R"\nP = "/v1/orders/open"\nK = "/uapi/x"\n') and not _token_hits(X, "x = 1\n")
    files = _sources()
    assert KIS_FILE in files and TRANSPORT in files, sorted(files)
    hits = [h for rel, src in files.items() for h in _tr_hits(rel, src)]
    assert not hits, hits


def test_transport_is_the_only_path():
    """E36: no execution module but transport.py can reach requests, _send, the signing helpers, the hosts or a
    credential name, and nothing rebinds a seam or an allowlist from outside (contract 0.5)."""
    for src in ("from execution.transport import _send\n", "from execution import transport\n",
                "import execution.transport\n", "import execution.transport as t\n",
                "from execution.transport import request as r\n", "from execution.transport import HOSTS\n",
                "from . import transport\n", "from execution.kis_inquiry import keys\n",
                "from execution.poll import transport\n", "x = execution.transport.Answer\n",
                "transport._send(m, u)\n", 'request("kis", "POST", p)\n', 'request("kis", m, p)\n',
                "request(*a)\n", 'request(*a, "GET")\n', "r = request\n", "from execution import keys\n",
                "import execution.keys\n", "from execution.keys import KeyMissing\n",
                'keys.read(("KIS_APP_KEY",))\n', 'n = "KIS_APP_SECRET"\n', "# reads OKX_API_PASSPHRASE\n",
                "requests.get(u)\n", "x.requests.Session()\n", 'HOSTS["kis"]\n', "c = CREDENTIALS\n",
                "m.keys.read(n)\n", "f = m.request\n", "c = poll.transport\n", "s = transport._sleep\n",
                "kis_inquiry.ENDPOINTS = s\n", "t._clock = c\n", "t.x += 1\n", "t.x: int = 1\n", "del t.x\n",
                "for t.x in y:\n    pass\n", "with f() as t.x:\n    pass\n", "a, t.x = 1, 2\n",
                "[0 for t.x in y]\n", "setattr(t, n, v)\n", "delattr(t, n)\n", "f = setattr\n", "getattr(t, n)\n",
                'getattr(request, "__globals__")\n', 'getattr(t, "_send")\n', 'getattr(m, "keys")\n',
                'getattr(m, "HOSTS")\n', "g = getattr\n", "vars(t)\n", "globals()\n", "request.__globals__\n",
                "f.__code__\n", "m.__dict__\n", "b = __builtins__\n", "m = sys.modules.get(n)\n",
                "def f():\n    global _send\n", "session.trust_env = False\n", "def f(self):\n    self.x = 1\n",
                'object.__setattr__(self, "a", 1)\n', "def f(self):\n    object.__setattr__(self, 'a', 1)\n",
                "def __post_init__(self):\n    object.__setattr__(t, '_send', f)\n",
                "exc.__traceback__.tb_next.tb_frame.f_globals['_send'] = f\n", "g = sys._getframe(1).f_globals\n",
                'getattr(fr, "f_globals")\n', 'd["_send"] = f\n',
                'g = object.__getattribute__(f, "__glo" + "bals__")\n',
                'kis_inquiry.__getstate__()["ENDPOINTS"] = e\n', "b = len.__self__\n"):
        assert _path_hits(X, src), src
    reads = ("from execution import keys\nACCOUNT_NAMES = ('A', 'B')\n"
             "def snapshot():\n    a = keys.read(ACCOUNT_NAMES)\n")
    assert not _path_hits(KIS_FILE, reads), _path_hits(KIS_FILE, reads)
    for extra in ("    b = keys.read(ACCOUNT_NAMES)\n", '    keys._parse("x")\n', "    k = keys\n",
                  "    keys.read(ACCOUNT_NAMES[:1])\n"):
        assert _path_hits(KIS_FILE, reads + extra), extra
    assert _path_hits(KIS_FILE, "from execution import keys as k\n")
    assert _path_hits(KIS_FILE, "from execution.keys import read\n")
    clock = "from execution import transport\ndef main():\n    transport._clock = lambda: now()\n"
    assert not _path_hits(POLL, clock), _path_hits(POLL, clock)
    for bad in ("from execution import transport\ntransport._clock = c\n",
                "from execution import transport\ndef main():\n    transport._send = f\n",
                "from execution import transport\ndef main():\n    e = transport.InquiryError\n",
                "from execution import transport as t\ndef main():\n    t._clock = c\n"):
        assert _path_hits(POLL, bad), bad
    send = "def _send(m, u):\n    with S() as session:\n        session.trust_env = False\n"
    assert not _path_hits(TRANSPORT, send)
    assert _path_hits(TRANSPORT, "def _other(m, u):\n    with S() as session:\n        session.trust_env = False\n")
    assert _path_hits(TRANSPORT, "def f():\n    global _clock\n")
    assert not _path_hits(TRANSPORT, "def f():\n    global _next_issue_at, _okx_offset_s\n")
    for ok in ('x = getattr(y, "name")\n', "from execution.transport import request, Answer, KeyMissing\n"
               'a = request("upbit", "GET", "/v1/accounts")\n',
               "class E(Exception):\n    def __init__(self, n):\n        super().__init__(n)\n        self.name = n\n",
               "class S:\n    def __post_init__(self):\n        object.__setattr__(self, 'h', 1)\n",
               "from execution import snapshot\nfrom execution.snapshot import Snapshot\nd = {}\nd['k'] = 1\n",
               "names = sorted(d.keys())\n", '"""Ten requests a second at most."""\n',
               "frames = traceback.extract_tb(exc.__traceback__)\n"):                  # Task 12's crash line
        assert not _path_hits(X, ok), ok
    files = _sources()
    shipped = {TRANSPORT, KIS_FILE, UPBIT_FILE, "execution/okx_inquiry.py", "execution/keys.py"}
    assert shipped <= set(files), sorted(files)
    hits = [h for rel, src in files.items() for h in _path_hits(rel, src)]
    assert not hits, hits


def test_send_is_pinned():
    """E1R2-11: `_send` is exactly the function of contract section 6 (one requests.Session() with trust_env off,
    one session.request(..., allow_redirects=False), nothing else), compared as ast.unparse text, and transport.py
    uses `requests` in no other way than its import, that Session and requests.exceptions.ConnectionError."""
    assert _send_def(SEND_TEMPLATE) == SEND_SOURCE
    variants = {
        "no trust_env line": ("        session.trust_env = False                  # no proxy, CA bundle or .netrc\n",
                              ""),
        "trust_env True": ("trust_env = False", "trust_env = True"),
        "redirects on": ("allow_redirects=False", "allow_redirects=True"),
        "verify off": ("verify=options.verify", "verify=False"),
        "proxies": ("proxies=options.proxies", "proxies=p"),
        "unreviewed routing": ("options = route_options(url)", "options = other_options(url)"),
        "auth": ("verify=options.verify)", "verify=options.verify, auth=a)"),
        "hooks": ("verify=options.verify)", "verify=options.verify, hooks=h)"),
        "stream": ("verify=options.verify)", "verify=options.verify, stream=True)"),
        "cert": ("verify=options.verify)", "verify=options.verify, cert=c)"),
        "requests.request": ("session.request(", "requests.request("),
        "a docstring": ("    with requests", '    """Send."""\n    with requests'),
        "a second send": ("resp.content\n", "resp.content\n\n_send = print\n"),
    }
    for label, (old, new) in variants.items():
        src = SEND_TEMPLATE.replace(old, new, 1)
        assert src != SEND_TEMPLATE and _send_def(src) != SEND_SOURCE, label
    assert _send_def("import requests\n") is None
    for src in ("from requests import Session\n", "import requests as r\n", "import requests.adapters\n",
                "import requests\ndef f():\n    return requests.get(u)\n",
                "import requests\ndef f():\n    return requests.Session()\n", "import requests\nx = requests\n"):
        assert _requests_hits(src), src
    assert not _requests_hits(SEND_TEMPLATE + "E = requests.exceptions.ConnectionError\n")
    src = (EXECUTION / "transport.py").read_text(encoding="utf-8")
    assert _send_def(src) == SEND_SOURCE, _send_def(src)
    assert not _requests_hits(src), _requests_hits(src)
