"""Static guards over core/compliance (and core/odds once it exists): compliance plan Task 1 (spec 4 "Guards", 8.9;
contract section 0; P5).

Each guard is a pure checker `(rel, source) -> [hit, ...]`. Every test first proves its checker catches a synthetic
offender (the positive control), then asserts the shipped files are clean. The repo-wide guards (T-RO-01, test_08,
test_09, T-CTX-01) stay in force; these add what they miss: docstrings and comments, `def` names, every HTTP verb,
every stdlib network module and URL-fetching call, `from core.engine import orders`, star and dynamic imports, the
import allowlist, the wall clock and the sealed context.
"""
from __future__ import annotations

import ast
import contextlib
import io
import os
import re
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "core"
COMPLIANCE, ODDS = CORE / "compliance", CORE / "odds"
INIT = "core/compliance/__init__.py"
X = "core/compliance/x.py"                              # the name a synthetic offender is checked under

# Raw text, docstrings and comments included (case-insensitive, then case-sensitive).
RAW_CI = ("private_key", "seed_phrase", "order_cash", "order-cash", "place_order", "submit_order", "tttc0802u",
          "tttc0801u", "vttc0802u", "r18_research_log", "r18_break_log", "context_log/", "tests.reference",
          "reference_mode")
RAW_CS = ("CANO", "KIS_ACCOUNT", "ACNT_PRDT_CD")
CORE_RAW_CI = ("private_key", "seed_phrase")            # these two hold for every file in core/ (contract section 0)
DEF_NAMES = frozenset({"transfer", "withdraw", "deposit_address"})
HTTP_VERBS = frozenset({"post", "put", "delete", "patch", "request"})
# core/compliance never needs the network: the alert email is sent by the scheduled Claude task and the toast is a
# subprocess (P26). So none of these stdlib modules may be imported in any form (a dotted name bans the module and
# everything below it, not its parent: `import logging` and `import xml.etree.ElementTree` stay allowed), and the calls
# that open a connection or fetch a URL are banned by name too (bare or as an attribute), as a second line behind the
# import ban. A denylist of what can reach the network, not a proof: see the docstring of test_no_http_verb_calls.
NETWORK_MODULES = ("urllib", "http", "socket", "_socket", "socketserver", "selectors", "ssl", "smtplib", "ftplib",
                   "imaplib", "poplib", "nntplib", "telnetlib", "xmlrpc", "asyncio", "webbrowser", "multiprocessing",
                   "wsgiref", "xml.sax", "xml.dom", "logging.handlers", "antigravity", "ctypes", "_ctypes", "_ssl",
                   "_overlapped")
NETWORK_CALLS = frozenset({"urlopen", "urlretrieve", "create_connection"})
FORBIDDEN_MODULES = ("core.engine.orders", "core.quant.forward_sim", "core.quant.refusal", "core.ficc.context_log",
                     "core.ficc.macro", "core.ficc.flows_log", "core.skills.macro_daily")
# Star and dynamic imports hide what a file loads from these guards and from the D14 closure (P6). Each module below
# imports or runs code named in a string or read from data: importlib (every submodule but metadata), runpy, pkgutil,
# zipimport, pydoc (locate), timeit, code, cProfile, profile, pdb, bdb, trace and doctest (exec of a string), unittest
# (mock.patch targets, the loader's __import__), logging.config (class strings, and a TCP listener), pickle, _pickle,
# shelve and marshal (objects and code from bytes), site (.pth lines are exec'd), ensurepip and venv (pip through
# runpy), tkinter, _tkinter, turtle, turtledemo and idlelib (a Tcl interpreter with sockets; idlelib exec), pstats
# and tracemalloc (they load files with marshal and pickle: pstats.Stats, tracemalloc.Snapshot.load). The builtin
# compile() is banned as a bare name and as an imported name (`from builtins import compile as c`), so re.compile stays
# legal (builtins.compile is left to review). importlib.metadata stays allowed: owner.py reads the RECORD files with it.
# `import importlib.metadata` binds the name importlib, so any other attribute of it (importlib.util,
# importlib._bootstrap) is a hit too; its EntryPoint.load imports by string through an attribute, which this scan does
# not see. faulthandler stays allowed (R1): it runs no string and opens nothing. A denylist, not a proof: codeop and dis
# (they compile a string, which types.FunctionType runs), _frozen_importlib, _frozen_importlib_external and _imp
# (importlib's bootstrap under other names), _interpreters (run_string), breakpoint() and sys.breakpointhook
# (PYTHONBREAKPOINT names a callable), string annotations evaluated by typing.get_type_hints or
# inspect.get_annotations(eval_str=True), functools.singledispatch's register, and importlib.metadata through an alias
# or getattr are not on it and are left to review. core/ probes for cryptography with a lazy `import` inside try/except
# ImportError; importlib.util.find_spec is for tests only.
DYNAMIC_NAMES = frozenset({"__import__", "import_module", "exec_module", "load_module", "exec", "eval"})
DYNAMIC_BARE = frozenset({"compile"})               # an ast.Name or an imported name: re.compile is an attribute
DYNAMIC_MODULES = ("importlib", "runpy", "pkgutil", "zipimport", "pydoc", "timeit", "code", "cProfile", "profile",
                   "pdb", "bdb", "trace", "doctest", "unittest", "logging.config", "pickle", "_pickle", "shelve",
                   "marshal", "site", "ensurepip", "venv", "tkinter", "_tkinter", "turtle", "turtledemo", "idlelib",
                   "pstats", "tracemalloc")
DYNAMIC_EXEMPT = "importlib.metadata"               # and everything below it (R9)
# base name -> attributes that read the clock
CLOCKS = {"datetime": {"now", "utcnow", "today"}, "date": {"today"},
          "time": {"time", "time_ns", "monotonic", "monotonic_ns", "perf_counter", "perf_counter_ns", "localtime",
                   "gmtime", "ctime", "asctime", "strftime", "process_time", "process_time_ns", "thread_time",
                   "thread_time_ns"}}
CLOCK_IN_MAIN = ("core/compliance/rules.py", "core/compliance/alerts.py")   # their CLI main() may read the clock
SEAL_USER = "core/compliance/owner.py"                                     # P5: the only caller of seal_context


# --------------------------------------------------------------------------- #
# Scope and AST helpers
# --------------------------------------------------------------------------- #
def _sources(*bases: Path) -> dict[str, str]:
    """rel path -> source of every .py file under `bases` (no __pycache__)."""
    out = {}
    for base in bases:
        if base.is_dir():
            for p in sorted(base.rglob("*.py")):
                if "__pycache__" not in p.parts:
                    out[p.relative_to(ROOT).as_posix()] = p.read_text(encoding="utf-8")
    return out


def _scope(*bases: Path) -> dict[str, str]:
    files = _sources(*bases)
    assert INIT in files, f"scan scope: {INIT} missing"
    return files


def _walk(node: ast.AST, funcs: tuple[str, ...] = ()):
    """Every node below `node`, with the names of the functions whose BODY encloses it: a def's decorators,
    defaults, annotations and type parameters run where the def runs, so they stay outside it."""
    for child in ast.iter_child_nodes(node):
        yield child, funcs
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
            body = {id(s) for s in child.body}
            for sub in ast.iter_child_nodes(child):
                inner = funcs + (child.name,) if id(sub) in body else funcs
                yield sub, inner
                yield from _walk(sub, inner)
        else:
            yield from _walk(child, funcs)


def _imports(rel: str, tree: ast.AST):
    """(node, absolute module, imported names, enclosing functions) per import; relative imports resolved."""
    pkg = rel[:-3].replace("/", ".").rsplit(".", 1)[0]
    for node, funcs in _walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                yield node, a.name, (), funcs
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if node.level:
                parts = pkg.split(".")
                parts = parts[:len(parts) - (node.level - 1)]
                module = ".".join(parts + ([node.module] if node.module else []))
            yield node, module, tuple(a.name for a in node.names), funcs


# --------------------------------------------------------------------------- #
# Checkers: (rel, source) -> hits
# --------------------------------------------------------------------------- #
def _raw_hits(rel: str, src: str, ci: tuple[str, ...] = RAW_CI, cs: tuple[str, ...] = RAW_CS) -> list[str]:
    low = src.lower()
    return [f"{rel}: {n!r}" for n in ci if n in low] + [f"{rel}: {n!r}" for n in cs if n in src]


def _def_hits(rel: str, src: str) -> list[str]:
    return [f"{rel}:{n.lineno}: def {n.name}" for n, _f in _walk(ast.parse(src))
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name in DEF_NAMES]


def _http_hits(rel: str, src: str) -> list[str]:
    hits = []
    for n, _f in _walk(ast.parse(src)):
        if not isinstance(n, ast.Call):
            continue
        name = n.func.attr if isinstance(n.func, ast.Attribute) else n.func.id if isinstance(n.func, ast.Name) else None
        if (isinstance(n.func, ast.Attribute) and name in HTTP_VERBS) or name in NETWORK_CALLS:
            hits.append(f"{rel}:{n.lineno}: {name}()")
    return hits


def _forbidden_hits(rel: str, src: str) -> list[str]:
    hits = []
    for node, module, names, _f in _imports(rel, ast.parse(src)):
        targets = [module] + [f"{module}.{n}" for n in names]
        bad = [t for t in targets for m in FORBIDDEN_MODULES if t == m or t.startswith(m + ".")]
        if bad:
            hits.append(f"{rel}:{node.lineno}: imports {bad[0]}")
    return hits


def _dynamic_module(target: str) -> bool:
    """A dotted import target in DYNAMIC_MODULES (or below one), unless it is DYNAMIC_EXEMPT or below it (R9)."""
    if target == DYNAMIC_EXEMPT or target.startswith(DYNAMIC_EXEMPT + "."):
        return False
    return any(target == m or target.startswith(m + ".") for m in DYNAMIC_MODULES)


def _dynamic_hits(rel: str, src: str) -> list[str]:
    tree, hits = ast.parse(src), []
    for node, module, names, _f in _imports(rel, tree):
        targets = [f"{module}.{n}" for n in names] or [module]     # `from importlib import metadata` is that module
        if ("*" in names or (DYNAMIC_NAMES | DYNAMIC_BARE).intersection(names)
                or any(_dynamic_module(t) for t in targets)):
            hits.append(f"{rel}:{node.lineno}: star or dynamic import from {module}")
    for node, _f in _walk(tree):
        name = node.id if isinstance(node, ast.Name) else node.attr if isinstance(node, ast.Attribute) else None
        via = isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == "importlib"
        if via and name != "metadata":                  # `import importlib.metadata` binds the name importlib (R9)
            hits.append(f"{rel}:{node.lineno}: importlib.{name}")
        elif name in DYNAMIC_NAMES or (isinstance(node, ast.Name) and node.id in DYNAMIC_BARE):
            hits.append(f"{rel}:{node.lineno}: {name}")
    return hits


def _allowed(name: str) -> bool:
    top = name.split(".")[0]
    return (top in sys.stdlib_module_names or top in ("yaml", "cryptography")
            or any(name == p or name.startswith(p + ".") for p in ("core.isolation", "core.compliance")))


def _allowlist_hits(rel: str, src: str) -> list[str]:
    hits = []
    for node, module, names, funcs in _imports(rel, ast.parse(src)):
        net = [t for t in [module] + [f"{module}.{n}" for n in names]
               for m in NETWORK_MODULES if t == m or t.startswith(m + ".")]
        if net:                                         # stdlib, so the allowlist alone would pass it
            hits.append(f"{rel}:{node.lineno}: imports {net[0]}: a network module; core/compliance never needs one")
        elif not (_allowed(module) or (names and all(_allowed(f"{module}.{n}") for n in names))):
            hits.append(f"{rel}:{node.lineno}: imports {module}: not stdlib, yaml, cryptography, core.isolation "
                        "or core.compliance")
        elif module.split(".")[0] == "cryptography" and not funcs:
            hits.append(f"{rel}:{node.lineno}: imports cryptography at module level; import it inside the function")
    return hits


def _clock_hits(rel: str, src: str) -> list[str]:
    tree, hits, alias = ast.parse(src), [], {}
    for n in ast.walk(tree):                            # `import time as t`, `from datetime import date as D`
        if isinstance(n, ast.Import) or (isinstance(n, ast.ImportFrom) and n.module == "datetime"):
            alias.update({a.asname or a.name: a.name for a in n.names if a.name in CLOCKS})
    for node, funcs in _walk(tree):
        if rel in CLOCK_IN_MAIN and "main" in funcs:
            continue
        if isinstance(node, ast.Attribute):
            if isinstance(node.value, ast.Name):
                base = alias.get(node.value.id, node.value.id)
            else:
                base = getattr(node.value, "attr", None)
            if node.attr in CLOCKS.get(base, ()):
                hits.append(f"{rel}:{node.lineno}: {base}.{node.attr}")
        elif isinstance(node, ast.ImportFrom) and node.module == "time":
            hits.append(f"{rel}:{node.lineno}: from time import ...")
    return hits


def _seal_hits(rel: str, src: str) -> list[str]:
    if rel == SEAL_USER:
        return []
    return [f"{rel}:{n.lineno}: seal_context" for n, _f in _walk(ast.parse(src))
            if (isinstance(n, ast.Name) and n.id == "seal_context")
            or (isinstance(n, ast.Attribute) and n.attr == "seal_context")
            or (isinstance(n, ast.alias) and n.name == "seal_context")]


def _main_block_hits(rel: str, src: str) -> list[str]:
    return [f"{rel}:{n.lineno}: a __main__ block must be exactly `raise SystemExit(main())`"
            for n, _f in _walk(ast.parse(src))
            if isinstance(n, ast.If) and ast.unparse(n.test) == "__name__ == '__main__'"
            and ("\n".join(ast.unparse(s) for s in n.body) != "raise SystemExit(main())" or n.orelse)]


def _init_hits(path: Path) -> list[str]:
    return [] if path.is_file() and path.stat().st_size == 0 else [f"{path.name} must exist and be 0 bytes"]


# --------------------------------------------------------------------------- #
# Guards
# --------------------------------------------------------------------------- #
def test_raw_text_has_no_forbidden_words():
    """Docstrings and comments included: T-RO-01 strips them, and test_08/test_09 miss private_key and seed_phrase.
    The full list holds in core/compliance and core/odds; private_key and seed_phrase in every file of core/."""
    for needle in RAW_CI + RAW_CS:
        assert _raw_hits(X, f'"""{needle}"""\n'), needle
    assert _raw_hits(X, "# signs with the PRIVATE_KEY\n") and _raw_hits(X, "x = 1  # the CANONICAL form\n")
    assert not _raw_hits(X, "canonical_json, signing_key, transfer_out\n")
    assert _raw_hits("core/ficc/x.py", "# the Seed_Phrase\n", CORE_RAW_CI, ())
    assert not _raw_hits("core/ficc/x.py", "# r18_research_log, context_log/\n", CORE_RAW_CI, ())
    hits = [h for rel, src in _scope(COMPLIANCE, ODDS).items() for h in _raw_hits(rel, src)]
    hits += [h for rel, src in _scope(CORE).items() for h in _raw_hits(rel, src, CORE_RAW_CI, ())]
    assert not hits, hits


def test_no_function_named_transfer_withdraw_or_deposit_address():
    """Spec 4: FORBIDDEN_CALLS catches call sites only; this catches the definitions, in every file of core/."""
    sample = ("def transfer():\n    pass\nasync def withdraw():\n    pass\n"
              "class A:\n    def deposit_address(self):\n        pass\n")
    assert len(_def_hits(X, sample)) == 3
    assert not _def_hits(X, "def transfer_out():\n    pass\ndef is_withdraw_exit():\n    pass\n")
    hits = [h for rel, src in _scope(CORE).items() for h in _def_hits(rel, src)]
    assert not hits, hits


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
    assert len(_http_hits(X, "requests.post(u)\nstore.put('transfer_ack', 1)\nx.delete()\ny.patch(z)\n"
                             "s.request('POST', u)\n")) == 5
    # a urllib POST with no verb method at all: only the urlopen call names it
    assert len(_http_hits(X, "urllib.request.urlopen(urllib.request.Request(u, data=b'x', method='POST'))\n"
                             "urlopen(u)\nurlretrieve(u, p)\nsocket.create_connection(a)\n")) == 4
    assert not _http_hits(X, "d.get(1)\nlines.append(2)\nmy_urlopen(u)\nx.urlopen_note\n")
    hits = [h for rel, src in _scope(COMPLIANCE).items() for h in _http_hits(rel, src)]
    assert not hits, hits


def test_no_forbidden_module_import():
    """core.engine.orders in every form (T-RO-01 misses `from core.engine import orders`), the forward simulator,
    the refusal legs and the protected context modules, at module or function level; and no star or dynamic import
    or bare compile(), which would hide one from this scan and load code the D14 closure never signed (P6)."""
    for src in ("from core.engine import orders\n", "import core.engine.orders as o\n",
                "from core.engine.orders import OrderBook\n", "from ..engine import orders\n",
                "def f():\n    from core.quant import forward_sim\n", "from core.ficc import macro\n",
                "import core.skills.macro_daily\n", "from core.ficc.context_log import x\n",
                "from core.quant.refusal import y\n", "import core.ficc.flows_log\n"):
        assert _forbidden_hits(X, src), src
    assert not _forbidden_hits(X, "from core.ficc import macro_schema\nfrom core.engine import books\n")
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
    assert not _dynamic_hits(X, "def f():\n    try:\n        import cryptography.hazmat.primitives.asymmetric.ed25519\n"
                                "    except ImportError:\n        return None\n")    # the core/ missing-package probe
    hits = [h for rel, src in _scope(COMPLIANCE, ODDS).items()
            for h in _forbidden_hits(rel, src) + _dynamic_hits(rel, src)]
    assert not hits, hits


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
                "import importlib.metadata\nimportlib.reload(m)\n",
                "from builtins import compile as c\nc(s, 'x', 'exec')\n"):
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
    for src in ("import numpy\n", "import config\n", "from core.quant import instruments\n",
                "from core import isolation, quant\n", "from core.calendars.store import CalendarSet\n",
                "def f():\n    import core.rules.governance\n", "import cryptography\n",
                "from cryptography.exceptions import InvalidSignature\n"):
        assert _allowlist_hits(X, src), src
    for src in ("import urllib.request\n", "from http import client\n", "import socket\n", "import smtplib\n",
                "from urllib.request import urlopen\n", "from urllib import request\n", "import http.client as hc\n",
                "def f():\n    import ssl\n", "from socket import create_connection\n"):
        assert _allowlist_hits(X, src), src
    for module in NETWORK_MODULES:                      # every banned module, in each import form
        for src in (f"import {module}\n", f"import {module}.x\n", f"from {module} import x\n",
                    f"from {module}.x import y\n"):
            assert _allowlist_hits(X, src), src
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
    assert not _allowlist_hits(X, "import subprocess\nimport importlib.metadata\nfrom importlib import metadata\n"
                                  "import ipaddress, email.message, json\n")
    ok = ("from __future__ import annotations\nimport json, zoneinfo\nimport yaml\nfrom core import isolation\n"
          "from core.isolation import checked_target\nfrom . import model\nfrom .model import Intent\n"
          "import core.compliance.rules\ndef f():\n    from cryptography.exceptions import InvalidSignature\n")
    assert not _allowlist_hits(X, ok)
    hits = [h for rel, src in _scope(COMPLIANCE).items() for h in _allowlist_hits(rel, src)]
    assert not hits, hits


def test_no_wall_clock_outside_cli_main():
    """The gate, the model and the owner state take time as an argument; only the BODY of the CLI main() of rules.py
    and alerts.py may read the clock (contract section 0). Its defaults and decorators run at import."""
    for src in ("datetime.now(timezone.utc)\n", "datetime.datetime.utcnow()\n", "date.today()\n", "time.time()\n",
                "time.monotonic()\n", "time.localtime()\n", "time.gmtime()\n", "from time import time\n",
                "def f(clock=datetime.now):\n    pass\n", "x = ctx.date.today()\n",
                "import time as t\nx = t.time()\n", "from datetime import datetime as dt\nx = dt.now()\n",
                "from datetime import date as D\nx = D.today()\n"):
        assert _clock_hits(X, src), src
    main = "def main():\n    return datetime.now(timezone.utc).date()\n"
    assert _clock_hits(X, main) and _clock_hits("core/compliance/gate.py", main)
    assert not _clock_hits("core/compliance/rules.py", main) and not _clock_hits("core/compliance/alerts.py", main)
    for src in ("def main(argv=None, today=date.today()):\n    pass\n",
                "@functools.lru_cache(time.time())\ndef main():\n    pass\n"):
        assert _clock_hits("core/compliance/rules.py", src), src
    assert not _clock_hits("core/compliance/rules.py", "import time as t\ndef main():\n    return t.time()\n")
    assert not _clock_hits(X, "d = moment.astimezone(KST).date()\nt = datetime.fromisoformat(s)\n")
    hits = [h for rel, src in _scope(COMPLIANCE).items() for h in _clock_hits(rel, src)]
    assert not hits, hits


def test_seal_context_only_in_owner():
    """P5: model.py defines seal_context and owner.py alone calls it, anywhere in core/."""
    for src in ("from core.compliance.model import seal_context\n",
                "from core.compliance import model\nc = model.seal_context()\n",
                "from .model import seal_context as s\n"):
        assert _seal_hits("core/compliance/gate.py", src), src
    assert not _seal_hits(SEAL_USER, "from .model import seal_context\nc = seal_context(date=None)\n")
    assert not _seal_hits("core/compliance/model.py", "def seal_context(**fields):\n    return fields\n")
    files = _scope(CORE)
    assert len(files) > 50, "scan scope collapsed"
    hits = [h for rel, src in files.items() for h in _seal_hits(rel, src)]
    assert not hits, hits


def test_main_blocks_are_one_line():
    """T-CTX-01 skips `if __name__ == "__main__":` bodies, so in core/compliance they hold the call and nothing else."""
    assert _main_block_hits(X, 'if __name__ == "__main__":\n    main()\n')
    assert _main_block_hits(X, 'if __name__ == "__main__":\n    import sys\n    raise SystemExit(main())\n')
    assert _main_block_hits(X, 'if __name__ == "__main__":\n    raise SystemExit(main())\nelse:\n    pass\n')
    assert not _main_block_hits(X, 'if __name__ == "__main__":\n    raise SystemExit(main())\n')
    hits = [h for rel, src in _scope(COMPLIANCE).items() for h in _main_block_hits(rel, src)]
    assert not hits, hits


def test_isolation_report_clean_and_prefixes_active():
    """T-CTX-01 with the two new prefixes: compliance and odds modules are acting, their packages are not, a
    synthetic acting import of context_log is caught, and the real tree reports nothing."""
    from core.ficc import context_log as CL
    hits = CL.scan_isolation({"core.compliance.gate": "from core.ficc import context_log\n"})
    assert [v.kind for v in hits] == ["import"], hits
    assert CL.is_acting_module("core.compliance.gate") and CL.is_acting_module("core.odds.plan")
    assert not CL.is_acting_module("core.compliance") and not CL.is_acting_module("core.odds")
    assert CL.static_isolation_report() == []


def test_package_init_is_empty():
    """core/compliance/__init__.py (and core/odds/__init__.py when present) is 0 bytes: under the trailing-dot
    prefix the package module itself is not acting, so it may hold no code."""
    probe = Path(os.environ["TRADEGEN_HOME"]) / "init_probe"        # the per-test temp home; removed with it
    probe.mkdir()
    (probe / "__init__.py").write_bytes(b"x = 1\n")
    assert _init_hits(probe / "__init__.py") and _init_hits(probe / "missing.py")
    assert not _init_hits(COMPLIANCE / "__init__.py"), f"{INIT} must exist and be 0 bytes"
    assert not (ODDS / "__init__.py").exists() or not _init_hits(ODDS / "__init__.py"), "core/odds/__init__.py"


# --------------------------------------------------------------------------- #
# The harness itself
# --------------------------------------------------------------------------- #
def test_suite_runs_hermetic_in_a_temp_home():
    """The aggregator arms the hermetic guard and points TRADEGEN_HOME at a fresh temp dir for every test; a nested
    wrapped call shows the wrapper itself arms one more level, moves the home, and undoes both."""
    from tests import compliance_acceptance as CA
    from tests import macro_acceptance as MA
    home = Path(os.environ["TRADEGEN_HOME"])
    assert MA._DEPTH > 0, "the hermetic guard is not armed"
    assert home.is_dir() and home.name.startswith("tradegen_home_"), home
    assert not home.resolve().is_relative_to((Path.home() / ".tradegen").resolve()), home
    seen = []
    CA._wrap(lambda: seen.append((MA._DEPTH, Path(os.environ["TRADEGEN_HOME"]))))()
    depth, inner = seen[0]
    assert depth == MA._DEPTH + 1 and inner != home and inner.name.startswith("tradegen_home_"), seen
    assert Path(os.environ["TRADEGEN_HOME"]) == home and not inner.exists(), seen


def test_harness_flags_a_change_to_the_real_compliance_home():
    """The wrapper fails a test that changes the real ~/.tradegen/compliance (pointed at a stand-in here)."""
    from tests import compliance_acceptance as CA
    fake = Path(os.environ["TRADEGEN_HOME"]) / "fake_real_home"     # the per-test temp home; removed with it
    fake.mkdir()
    keep, flagged = CA._REAL_HOME, False
    try:
        CA._REAL_HOME = fake
        CA._wrap(lambda: None)()                                        # nothing changed: passes
        try:
            CA._wrap(lambda: (fake / "owner.jsonl").write_bytes(b"{}\n"))()
        except AssertionError as exc:
            flagged = "real ~/.tradegen/compliance" in str(exc)
    finally:
        CA._REAL_HOME = keep
    assert flagged, "a write under the real compliance home was not flagged"


def test_aggregator_skips_missing_and_isolates_broken_modules():
    """Contract section 3: an absent module is skipped, one that fails to import becomes a single `<module>/import`
    entry that re-raises, a `test_*` name imported from elsewhere is not collected, and an empty run exits 1."""
    from tests import compliance_acceptance as CA
    probe = Path(os.environ["TRADEGEN_HOME"]) / "probe"
    probe.mkdir()
    mixed = types.ModuleType("tests.compliance_mixed")
    exec("from tests.compliance_fixtures import temp_home as test_imported\ndef test_own():\n    pass\n", vars(mixed))
    for stem in ("compliance_broken", "compliance_mixed"):
        (probe / f"{stem}.py").write_bytes(b"")
    keep = CA.TESTS, CA.MODULES
    sys.modules.update({"tests.compliance_broken": None, "tests.compliance_mixed": mixed})   # None: import raises
    try:
        CA.TESTS, CA.MODULES = probe, ("compliance_broken", "compliance_absent", "compliance_mixed")
        found = CA.tests()
    finally:
        CA.TESTS, CA.MODULES = keep
        for stem in ("compliance_broken", "compliance_mixed"):
            sys.modules.pop(f"tests.{stem}", None)
    assert [n for n, _f in found] == ["compliance_broken/import", "compliance_mixed/test_own"], found
    try:
        found[0][1]()
    except ImportError:
        pass
    else:
        raise AssertionError("the broken module's entry did not re-raise its import error")
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = CA._main(["no such test"])
    assert code == 1 and out.getvalue().strip() == "0/0 passed, 0 failed, 0 not run", (code, out.getvalue())


# --------------------------------------------------------------------------- #
# Registration
# --------------------------------------------------------------------------- #
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


def test_cryptography_is_pinned_installed_and_usable():
    """Task 10 (spec 6.4 "The dependency"): cryptography==49.0.0 is pinned once each in requirements.txt, the
    pyproject dependencies and constraints.txt, is loaded from TRADEGEN's .venv (never the global user site), and
    offers every API owner.py, the signer and their tests use: raw and PEM Ed25519 keys, key generation,
    sign/verify, an X25519 key to refuse, scrypt and AES-256-GCM."""
    import importlib.metadata
    import tomllib
    pin = "cryptography==49.0.0"
    for name in ("requirements.txt", "constraints.txt"):
        lines = (ROOT / name).read_bytes().decode("utf-8").splitlines()
        assert lines.count(pin) == 1, f"{name} must pin {pin} exactly once"
    project = tomllib.loads((ROOT / "pyproject.toml").read_bytes().decode("utf-8"))["project"]
    assert project["dependencies"].count(pin) == 1, f"pyproject.toml dependencies must pin {pin} exactly once"
    assert project["requires-python"] == ">=3.12", "rules.calendar_stream calls Path.is_junction (Python 3.12)"
    dist = importlib.metadata.distribution("cryptography")
    assert dist.version == "49.0.0", f"cryptography {dist.version} is installed, not 49.0.0"
    where = Path(dist.locate_file("")).resolve()
    assert where.is_relative_to((ROOT / ".venv").resolve()), f"cryptography loaded from {where}, not .venv"
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
    from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
    signing_key = Ed25519PrivateKey.from_private_bytes(bytes(range(32)))
    assert signing_key.private_bytes_raw() == bytes(range(32))
    assert len(Ed25519PrivateKey.generate().private_bytes_raw()) == 32
    verifier = Ed25519PublicKey.from_public_bytes(signing_key.public_key().public_bytes_raw())
    message = b"tradegen-owner-log/1\n" + b"0" * 64
    signature = signing_key.sign(message)
    assert len(signature) == 64
    verifier.verify(signature, message)
    try:
        verifier.verify(signature, message + b"!")
    except InvalidSignature:
        pass
    else:
        raise AssertionError("a signature verified over other bytes")
    spki = serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
    pem = verifier.public_bytes(*spki)
    assert serialization.load_pem_public_key(pem).public_bytes_raw() == verifier.public_bytes_raw()
    other = X25519PrivateKey.from_private_bytes(bytes(32)).public_key().public_bytes(*spki)
    assert not isinstance(serialization.load_pem_public_key(other), Ed25519PublicKey)
    key = Scrypt(salt=bytes(16), length=32, n=2 ** 4, r=8, p=1).derive(b"a test passphrase, not the owner's")
    sealed = AESGCM(key).encrypt(bytes(12), bytes(range(32)), b"header")
    assert AESGCM(key).decrypt(bytes(12), sealed, b"header") == bytes(range(32))
