"""New runtime roots remain in the signed and tested acting closure."""
import ast
import hashlib
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import os
from pathlib import Path
import re
import tempfile
from unittest.mock import patch

from tests.compliance_guards import NETWORK_MODULES

ROOT = Path(__file__).resolve().parents[1]
PACKAGES = ("execution_launch", "execution_network")
# Imports that reach a venue, a key file or a process; urllib.parse stays legal (the route parser needs urlsplit).
EFFECT_PREFIXES = (("requests", "socket", "http", "urllib.request", "subprocess", "tools.signer")
                   + tuple(m for m in NETWORK_MODULES if m != "urllib"))
TRANSPORT_PREFIXES = ("execution.transport", "execution.keys", "execution_orders.transport")
TRANSPORT_FROM = {"execution": frozenset({"transport", "keys"}), "execution_orders": frozenset({"transport"})}
PRIVILEGED = frozenset({"eval", "exec", "__import__", "sign", "sign_entry", "arm", "load_context", "getenv",
                        "seal_context"})
PRIVILEGED_REFERENCES = frozenset({"sign_entry", "arm", "load_context", "seal_context"})   # called or not
PROCESS_CALLS = frozenset({"system", "popen", "startfile", "fork", "forkpty", "posix_spawn", "posix_spawnp"})
PROCESS_PREFIXES = ("execv", "execl", "spawn")
ENDPOINT = re.compile(r"(?i)/(?:v1|uapi|api/v5)/")
# One write ban for both packages. A writer row pins its exact call shapes under its own package-relative path;
# every other write and any other file is a hit when it is spelt as a call, a bare name, a from-import, a module
# alias, a getattr with a constant name, or os.open flags that are not provably os.O_* bits (every binding of a
# flags name counts, parameters and loop, with, import and unpacking targets included). Left to review by design: a
# getattr with a computed name (the dataclass field loops), a reference alias that is called later (f = os.replace,
# f = open, x = p.write_text), because os.open in os.supports_dir_fd is a legitimate reference, and a binding made
# at run time (globals()[name] = ..., setattr on a module).
HEAD = "execution_launch/baseline_head.py"
HISTORY = "execution_launch/live_history.py"
STUDY = "execution_launch/study.py"
CONTINUOUS_ARCHIVE = "execution_launch/continuous_archive.py"
UNIVERSE_STORE = "execution_launch/universe_store.py"
EVIDENCE_OBJECTS = "execution_launch/evidence_objects.py"
PROTECTIVE_STORE = "execution_launch/protective_store.py"
RESEARCH_BUNDLE_STORE = "execution_launch/research_bundle_store.py"
BUNDLE_REVIEW = "execution_launch/bundle_review.py"
NATIVE_DIRECTORY_CALLS = {
    "__init__": 'ctypes.WinDLL("kernel32", use_last_error=True)',
    "open_directory": 'self._kernel.CreateFileW(path, 0x80, 0x1, None, 3, 0x02000000 | 0x00200000, None)',
    "information": 'self._kernel.GetFileInformationByHandle(handle, self._ctypes.byref(info))',
    "final_path": 'self._kernel.GetFinalPathNameByHandleW(handle, buffer, len(buffer), 0)',
    "close": 'self._kernel.CloseHandle(handle)',
}
# This reviewed native seam intentionally has no extensibility: changing its
# ctypes structures, aliases, loaders or methods requires a fresh review.
NATIVE_DIRECTORY_AST_SHA256 = "841bd8050ae79d0a222b549b01a803b4b3d3303d376572447ed35e6de30fbf26"
OWNER_RESEARCH_SETUP = "tools/owner/research_bundle.py"
PINNED_WRITES: dict[str, tuple[str, ...]] = {
    BUNDLE_REVIEW: (
        'os.mkdir(self.payloads, 0o700)',
        'os.mkdir("payloads", 0o700, dir_fd=self.root_fd)',
        'os.open(target if directory_fd is None else name, '
        'os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0) '
        '| getattr(os, "O_BINARY", 0) | getattr(os, "O_NOINHERIT", 0) | getattr(os, "O_CLOEXEC", 0), '
        '0o600, **({} if directory_fd is None else {"dir_fd": directory_fd}))',
        'os.fdopen(descriptor, "wb")',
    ),
    RESEARCH_BUNDLE_STORE: (
        'os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | _FLAGS, 0o600)',
        'os.fdopen(descriptor, "wb")',
        'os.open(target, os.O_RDWR | _FLAGS)',
        'os.fdopen(descriptor, "r+b")',
        'os.open(target, os.O_WRONLY | os.O_APPEND | _FLAGS)',
        'os.fdopen(descriptor, "ab")',
    ),
    PROTECTIVE_STORE: (
        'self.root.mkdir(mode=0o700)',
        'os.open(checked_target(self.root / name, "protective setup", within=self.root), '
        'os.O_WRONLY | os.O_CREAT | os.O_EXCL | _FLAGS, 0o600)',
        'os.fdopen(descriptor, "wb")',
        'os.open(checked_target(target, "protective lock", within=self.root), os.O_RDWR | _FLAGS)',
        'os.fdopen(descriptor, "r+b")',
        'os.open(target, os.O_WRONLY | os.O_APPEND | _FLAGS)',
        'os.fdopen(descriptor, "ab")',
    ),
    HEAD: (
        'checked_target(self._dir, "baseline head directory", within=self._root).mkdir(mode=0o700, exist_ok=True)',
        'os.open(checked_target(self._dir / "head.lock", "baseline head lock", within=self._dir), '
        'os.O_RDWR | (os.O_CREAT if create else 0) | _FLAGS, 0o600)',
        'os.fdopen(descriptor, "r+b")',
        'os.open(checked_target(self._dir / "head.tmp", "baseline head temporary file", within=self._dir), '
        'os.O_WRONLY | os.O_CREAT | os.O_EXCL | _FLAGS, 0o600)',
        'os.fdopen(descriptor, "wb")',
        'os.replace(checked_target(self._dir / "head.tmp", "baseline head temporary file", within=self._dir), '
        'checked_target(self._dir / "head.json", "baseline head record", within=self._dir))',
    ),
    HISTORY: (
        'checked_target(self._dir, "history directory", within=self._base).mkdir(mode=0o700, parents=True, exist_ok=True)',
        'open(checked_target(self._dir / "history.lock", "history lock", within=self._dir), "a+b")',
        'open(checked_target(self._dir / "history.jsonl", "history journal", within=self._dir), "ab")',
    ),
    STUDY: (
        'os.open(checked_target(directory / name, "study output file", within=directory), '
        'os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_APPEND | _FLAGS, 0o600)',
        'os.fdopen(descriptor, "ab")',
    ),
    CONTINUOUS_ARCHIVE: (
        'checked_target(root / "execution-price-paths", "continuous archive", within=root).mkdir('
        'mode=0o700, parents=True, exist_ok=True)',
        'os.open(checked_target(directory / (candidate_sha + ".json"), "continuous candidate", within=directory), '
        'os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)',
        'os.fdopen(descriptor, "wb")',
    ),
    UNIVERSE_STORE: (
        'checked_target(directory, "universe directory", within=root).mkdir(mode=0o700, parents=True, exist_ok=True)',
        'os.open(checked_target(directory / name, "universe temporary file", within=directory), '
        'os.O_WRONLY | os.O_CREAT | os.O_EXCL | _FLAGS, 0o600)',
        'os.fdopen(descriptor, "wb")',
        'os.rename(checked_target(directory / name, "universe temporary file", within=directory), '
        'checked_target(target, "universe snapshot", within=directory))',
        'os.unlink(checked_target(directory / name, "universe temporary file", within=directory))',
    ),
    EVIDENCE_OBJECTS: (
        'self.root.mkdir(mode=0o700, exist_ok=True)',
        'self._objects.mkdir(mode=0o700, exist_ok=True)',
        'os.open(lock, os.O_RDWR | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0) '
        '| os.O_CREAT | os.O_EXCL, 0o600)',
        'os.open(lock, os.O_RDWR | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0))',
        'os.fdopen(descriptor, "r+b")',
        'os.open(pending, os.O_RDWR | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)',
        'os.fdopen(descriptor, "w+b")',
        'os.open(target, os.O_RDWR | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)',
        'pending.unlink()',
    ),
}
# The head's initialization is an explicit reviewed operator step: no runtime module may reference it.
OPERATOR_ONLY = frozenset({"initialize_reviewed_head"})
OWNER_SETUP = "tools/owner/launch.py"
OWNER_SETUP_CALLS = {
    "setup_account": "head.initialize_reviewed_head(reviewed_head)",
    "setup_history": "head.initialize_reviewed_head(GENESIS)",
}
_PINNED_WRITE_TREES = {relative: frozenset(ast.dump(ast.parse(shape, mode="eval").body) for shape in shapes)
                       for relative, shapes in PINNED_WRITES.items()}
WRITE_FLAGS = frozenset({"O_CREAT", "O_WRONLY", "O_RDWR", "O_APPEND", "O_TRUNC"})
OS_WRITES = frozenset({"replace", "rename", "renames", "remove", "unlink", "mkdir", "makedirs", "rmdir",
                       "removedirs", "link", "symlink", "truncate", "ftruncate", "write", "pwrite", "writev",
                       "pwritev"})
PATH_WRITES = frozenset({"write_text", "write_bytes", "touch", "unlink", "rename", "rmdir", "mkdir",
                         "symlink_to", "hardlink_to"})
WRITE_NAMES = OS_WRITES | PATH_WRITES | WRITE_FLAGS | {"open", "fdopen", "FileIO"}   # a write however it is reached
WRITER_MODULES = ("shutil", "tempfile", "logging")                                    # modules that write, in any form
OS_MODULES = frozenset({"os", "io", "_io", "nt", "posix", "builtins"})               # where a from-import finds a writer
MODE_AT_ONE = ("io", "_io", "builtins", "codecs", "gzip", "bz2", "lzma")              # their open/FileIO take (file, mode)
WRITE_MODE = re.compile(r"[wax+]")
# The trusted baseline head is advanced only by the account provider, the live-history journal and the continuous
# guard commit coordinator (after its durable prepare record and halt latch).
CAS_CALLERS = frozenset({"execution_accounts/baseline_bridge.py", "execution_launch/live_history.py",
                         "execution_launch/continuous_guard_commit.py", PROTECTIVE_STORE, RESEARCH_BUNDLE_STORE})


def _call_name(node):
    return (node.func.id if isinstance(node.func, ast.Name) else
            node.func.attr if isinstance(node.func, ast.Attribute) else "")


def _mode_argument(call, at, keyword="mode"):
    return call.args[at] if len(call.args) > at else next((k.value for k in call.keywords if k.arg == keyword), None)


def _mode_writes(call, at):
    """The open mode at position `at` (or `mode=`): absent reads; a constant without w, a, x or + reads."""
    mode = _mode_argument(call, at)
    if mode is None:
        return False
    return not (isinstance(mode, ast.Constant) and isinstance(mode.value, str)) or bool(WRITE_MODE.search(mode.value))


def _named(node):
    """The names a from-import binds (as the module spells them) or a getattr with a constant name reaches."""
    if isinstance(node, ast.ImportFrom):
        return {alias.name for alias in node.names}
    if (isinstance(node, ast.Call) and _call_name(node) == "getattr" and len(node.args) >= 2
            and isinstance(node.args[1], ast.Constant) and isinstance(node.args[1].value, str)):
        return {node.args[1].value}
    return set()


def _reached(node):
    """Every name a node reaches: an attribute, a bare name, or what _named finds."""
    if isinstance(node, ast.Attribute):
        return {node.attr}
    if isinstance(node, ast.Name):
        return {node.id}
    return _named(node)


def _assignments(tree):
    """Every expression a module assigns to each plain name, an augmented assignment as the BinOp it computes. A name
    bound any other way (a parameter, an import, a for, with, walrus, unpacking, match or except target) also gets
    an impure None, so no binding of a name is left out when its flags are judged. Scopes are merged on purpose: one
    impure binding anywhere makes the name impure everywhere, which can only add hits."""
    assigned, plain = {}, set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            plain.update(id(target) for target in node.targets)
            for target in node.targets:
                if isinstance(target, ast.Name):
                    assigned.setdefault(target.id, []).append(node.value)
        elif isinstance(node, (ast.AnnAssign, ast.AugAssign)):
            plain.add(id(node.target))
            if isinstance(node.target, ast.Name) and node.value:
                value = node.value if isinstance(node, ast.AnnAssign) else ast.BinOp(node.target, node.op, node.value)
                assigned.setdefault(node.target.id, []).append(value)
    for node in ast.walk(tree):
        if isinstance(node, ast.arg):
            names = [node.arg]
        elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store) and id(node) not in plain:
            names = [node.id]
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            names = [(alias.asname or alias.name).split(".")[0] for alias in node.names]
        elif isinstance(node, (ast.ExceptHandler, ast.MatchAs, ast.MatchStar)) and node.name:
            names = [node.name]
        elif isinstance(node, ast.MatchMapping) and node.rest:
            names = [node.rest]
        else:
            continue
        for name in names:
            assigned.setdefault(name, []).append(ast.Constant(None))
    return assigned


def _pure_flags(expression, assigned, seen=frozenset()):
    """os.open flags that can only be os.O_* bits: os.O_* attributes, getattr(os, "O_*", 0) fallbacks and names whose
    every binding in the module is itself pure, joined by |, with at least one binding that does not use the name
    itself. A number anywhere (1 | 64 is O_WRONLY | O_CREAT), a call, a parameter or any other non-assignment
    binding, a name the module never assigns, a name that is only augmented, or any other form is not."""
    if isinstance(expression, ast.BinOp) and isinstance(expression.op, ast.BitOr):
        return _pure_flags(expression.left, assigned, seen) and _pure_flags(expression.right, assigned, seen)
    if isinstance(expression, ast.Attribute):
        return ast.unparse(expression.value) == "os" and expression.attr.startswith("O_")
    if isinstance(expression, ast.Call):
        return (_call_name(expression) == "getattr" and len(expression.args) == 3
                and ast.unparse(expression.args[0]) == "os"
                and str(getattr(expression.args[1], "value", "")).startswith("O_")
                and isinstance(expression.args[2], ast.Constant) and expression.args[2].value == 0)
    if isinstance(expression, ast.Name):
        if expression.id in seen:                         # flags |= os.O_X: its other assignments decide
            return True
        values = assigned.get(expression.id, ())
        grounded = any(all(not (isinstance(n, ast.Name) and n.id == expression.id) for n in ast.walk(v)) for v in values)
        return grounded and all(_pure_flags(v, assigned, seen | {expression.id}) for v in values)
    return False


def _writes(node, assigned):
    """A write of a file, directory or link, a write flag, or a writer module, in any form: a call, a bare name, a
    from-import, a getattr with a constant name, or os.open flags that are not provably os.O_* bits."""
    if isinstance(node, ast.Name):
        return node.id in WRITER_MODULES or node.id.startswith("O_")
    if isinstance(node, (ast.Import, ast.ImportFrom)):
        modules = [a.name for a in node.names] if isinstance(node, ast.Import) else [node.module or ""]
        if any(m == w or m.startswith(w + ".") for m in modules for w in WRITER_MODULES):
            return True
        return isinstance(node, ast.ImportFrom) and node.module in OS_MODULES and bool(_named(node) & WRITE_NAMES)
    if isinstance(node, ast.Attribute):
        return node.attr in WRITE_FLAGS
    if not isinstance(node, ast.Call):
        return False
    name = _call_name(node)
    if _named(node) & WRITE_NAMES:                        # getattr(x, "<writer>"), bare or as builtins.getattr
        return True
    if isinstance(node.func, ast.Name):
        return name == "open" and _mode_writes(node, 1)
    if not isinstance(node.func, ast.Attribute):
        return False
    owner = ast.unparse(node.func.value)
    if owner == "os":
        if name == "open":                                # anything but os.O_* bits can hide a write mode
            return not _pure_flags(_mode_argument(node, 1, "flags"), assigned)
        return name in OS_WRITES or (name == "fdopen" and _mode_writes(node, 1))
    if name in ("open", "FileIO"):
        return _mode_writes(node, 1 if owner in MODE_AT_ONE else 0)
    if name == "replace":                                 # Path.replace(target); str.replace takes two, datetime.replace keywords
        return (len(node.args) == 1 and not node.keywords) or [k.arg for k in node.keywords] == ["target"]
    return name in PATH_WRITES


def _native_directory_imports(tree, relative):
    """Only two exact local imports for the reviewed Windows read-only pins.

    The exception belongs to this class in this module, and is lost if its native
    calls change. It does not allow ctypes imports elsewhere in the runtime.
    """
    if relative != BUNDLE_REVIEW:
        return set()
    classes = [node for node in tree.body if isinstance(node, ast.ClassDef)
               and node.name == "NativeDirectoryAPI"]
    if len(classes) != 1:
        return set()
    native_class = classes[0]
    if hashlib.sha256(ast.unparse(native_class).encode("utf-8")).hexdigest() != NATIVE_DIRECTORY_AST_SHA256:
        return set()
    inside = {id(node) for node in ast.walk(native_class)}
    native_names = {"ctypes", "wintypes", "_ctypes", "_kernel"}
    if any(id(node) not in inside and _reached(node) & native_names for node in ast.walk(tree)):
        return set()
    methods = [node for node in classes[0].body if isinstance(node, ast.FunctionDef)]
    if {node.name for node in methods} != set(NATIVE_DIRECTORY_CALLS) or len(methods) != len(NATIVE_DIRECTORY_CALLS):
        return set()
    for method in methods:
        calls = [node for node in ast.walk(method) if isinstance(node, ast.Call)
                 and (ast.unparse(node.func).startswith("self._kernel.")
                      or ast.unparse(node.func) == "ctypes.WinDLL")]
        expected = ast.dump(ast.parse(NATIVE_DIRECTORY_CALLS[method.name], mode="eval").body)
        if len(calls) != 1 or ast.dump(calls[0]) != expected:
            return set()
    initializer = next(node for node in methods if node.name == "__init__")
    shapes = {ast.dump(ast.parse(shape).body[0])
              for shape in ("import ctypes", "from ctypes import wintypes")}
    return {id(node) for node in initializer.body if ast.dump(node) in shapes}


def problems(source, relative=""):
    tree, failures = ast.parse(source), []
    assigned = _assignments(tree)
    native_imports = _native_directory_imports(tree, relative)
    pinned = {id(inner) for node in ast.walk(tree) if isinstance(node, ast.Call)
              and ast.dump(node) in _PINNED_WRITE_TREES.get(relative, frozenset()) for inner in ast.walk(node)}
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            modules = ([alias.name for alias in node.names] if isinstance(node, ast.Import)
                       else [node.module or ""])
            for module in modules:
                if any(module == prefix or module.startswith(prefix + ".") for prefix in TRANSPORT_PREFIXES):
                    failures.append("inquiry or order transport import")
                elif (id(node) not in native_imports
                      and any(module == prefix or module.startswith(prefix + ".") for prefix in EFFECT_PREFIXES)):
                    failures.append("direct effect import")
            if isinstance(node, ast.ImportFrom) and any(
                    alias.name in TRANSPORT_FROM.get(node.module, frozenset()) for alias in node.names):
                failures.append("inquiry or order transport import")
            if isinstance(node, ast.Import) and any(
                    alias.name in OS_MODULES and (alias.asname or alias.name in ("nt", "posix", "_io"))
                    for alias in node.names):
                failures.append("os module under another name")
            if isinstance(node, ast.ImportFrom) and any(alias.name == "*" for alias in node.names):
                failures.append("star import")
        called = {_call_name(node)} if isinstance(node, ast.Call) else set()
        reached = _reached(node)
        if (called | _named(node)) & PRIVILEGED:
            failures.append("privileged or dynamic call")
        if "compile" in called and ast.unparse(node.func) != "re.compile":
            failures.append("dynamic compilation")
        if (called | reached) & PROCESS_CALLS or any(name.startswith(PROCESS_PREFIXES) for name in called | reached):
            failures.append("process escape")
        if isinstance(node, ast.Attribute):
            if ast.unparse(node) == "os.environ":
                failures.append("environment access")
            if node.attr in {"__globals__", "__code__", "__closure__", "_ISSUED"}:
                failures.append("runtime mutation")
        if reached & PRIVILEGED_REFERENCES:
            failures.append("privileged reference")
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and ENDPOINT.search(node.value):
            failures.append("venue endpoint literal")
        if id(node) not in pinned and _writes(node, assigned):
            failures.append("write outside pinned writer")
        if "compare_and_set" in reached and relative not in CAS_CALLERS:
            failures.append("trusted head advance outside pinned callers")
        if reached & OPERATOR_ONLY and relative != HEAD:
            failures.append("operator-only head initialization outside its module")
    return failures


def read_text_without_encoding(source):
    """Text reads and writes that depend on the locale (this PC's is cp949): Path.read_text or write_text and a
    text-mode open() without encoding=."""
    hits = []
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.Call) or any(k.arg == "encoding" for k in node.keywords):
            continue
        name = _call_name(node)
        if isinstance(node.func, ast.Attribute) and name in ("read_text", "write_text"):
            hits.append(name + " without encoding")
        elif isinstance(node.func, ast.Name) and name == "open":
            mode = _mode_argument(node, 1)
            if mode is None or (isinstance(mode, ast.Constant) and isinstance(mode.value, str) and "b" not in mode.value):
                hits.append("text open without encoding")
    return hits


def test_launch_and_network_do_not_directly_sign_arm_or_open_http():
    for package in PACKAGES:
        for path in (ROOT / package).rglob("*.py"):
            relative = path.relative_to(ROOT).as_posix()
            found = problems(path.read_text(encoding="utf-8"), relative)
            assert not found, (relative, found)


def test_launch_guard_negative_controls():
    for source in ("import requests", "from urllib.request import urlopen", "import socket",
                   "import tools.signer.sign", "owner.load_context(now)", "owner.arm(x)",
                   "sign_entry(x)", "os.getenv('API_KEY')", "os.environ['API_KEY']",
                   "callback.__globals__", "eval(code)", "compile(code, 'x', 'exec')",
                   "model.seal_context(**fields)", "seal_context(now=now)"):
        assert problems(source), source
    assert not problems("from urllib.parse import urlsplit\npattern = re.compile('x')\nis_sealed(context)")


def test_new_runtime_packages_are_signed_recursively_by_owner_and_signer():
    from core.compliance import owner
    from tools.signer import sign
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        for package in PACKAGES:
            nested = root / package / "unused"
            nested.mkdir(parents=True)
            (root / package / "__init__.py").write_text("", encoding="utf-8")
            (nested / "future.py").write_text("VALUE = 1\n", encoding="utf-8")
        before = dict(owner.code_files(root))
        assert before == dict(sign.code_files(root))
        for package in PACKAGES:
            key = package + "/unused/future.py"
            assert key in before
            (root / key).write_text("VALUE = 2\n", encoding="utf-8")
        after = dict(owner.code_files(root))
        assert after == dict(sign.code_files(root))
        assert all(before[p + "/unused/future.py"] != after[p + "/unused/future.py"] for p in PACKAGES)


def test_new_packages_are_in_runtime_and_acting_graph():
    from tests.acceptance import runtime_py
    from core.ficc import context_log
    paths = {p.relative_to(ROOT).as_posix() for p in runtime_py()}
    for package in PACKAGES:
        assert {p.relative_to(ROOT).as_posix() for p in (ROOT / package).rglob("*.py")} <= paths
        assert context_log.is_acting_module(package + ".future.nested")


def test_launch_suite_is_complete_registered_and_import_errors_fail():
    from tests import launch_acceptance, run_all
    from tests.compliance_guards import _suite_names
    from unittest.mock import patch
    rows = run_all.select(run_all.tests(), suite="execution_launch")
    names = [name for name, _ in rows]
    for module in launch_acceptance.MODULES:
        assert any(n.startswith("execution_launch/" + module + "/test_") for n in names), module
    for name in ("README.md", "tests/run_all.py"):
        assert "execution_launch" in _suite_names((ROOT / name).read_text(encoding="utf-8"))
    with patch.object(launch_acceptance, "MODULES", ("deliberately_missing_launch_module",)), \
            redirect_stdout(StringIO()), redirect_stderr(StringIO()):
        result = run_all.run(launch_acceptance.tests())
    assert len(result) == 1 and result[0]["status"] == "FAIL"


HITS = (
    "from execution.transport import request", "from execution import transport", "from execution import keys",
    "from execution_orders.transport import AuthenticatedTransport", "from execution_orders import transport",
    "import execution.transport", "import execution_orders.transport as wire",
    'P = "/v1/accounts"', 'P = "/V1/ORDERBOOK"', 'P = "/uapi/domestic-stock/v1/quotations/x"',
    'P = "/api/v5/account/balance"', "os.startfile(p)", "os.system(c)", "os.popen(c)", "os.execv(a, b)",
    "os.spawnv(0, a, b)", "os.posix_spawn(a, b, c)", "import multiprocessing", "import asyncio", "import ssl",
    "import ctypes", "from selectors import DefaultSelector", "f = owner.load_context", "x = controller.arm",
    "s = ledger.sign_entry", "make = model.seal_context",
    # The same effects behind a bare name, a module alias, a star import or a getattr with a constant name.
    "os.execl(a, b)", "os.execlp(a, b)", "os.execvpe(a, b, c)", "getattr(os, 'system')(c)",
    "f = getattr(os, 'popen')", "getattr(owner, 'load_context')(now, pos)", "f = getattr(controller, 'arm')",
    "getattr(os, 'getenv')('API_KEY')", "import os as o\no.replace(a, b)", "import nt\nnt.replace(a, b)",
    "import posix", "import io as x", "from os import *\nreplace(a, b)", "from os import system as s\ns(c)",
    "from core.compliance.owner import load_context as lc\nlc(now)", "from os import getenv", "import _io",
)
CLEAN = (
    "from urllib.parse import urlsplit", "import msvcrt", "pattern = re.compile('x')",
    "from execution_accounts.quotes import to_runner_quote", "from execution_control.controller import Controller",
    "from execution_control.dry_run import DryRunAdapter", "from execution_accounts import baseline_bridge",
    "import math\nmath.copysign(1, x)", "text.replace('a', 'b')", "when.replace(tzinfo=None)",
    "with open(p, 'rb') as fh:\n    fh.read()", "path.open('rb')", "data = path.read_bytes()",
    "os.open(p, os.O_RDONLY | os.O_NOFOLLOW)", "os.fstat(fd)", "is_sealed(context)",
    # Negative controls for the bare-name, alias and getattr rules: the reads, the computed names and the constant
    # getattr uses the runtime files make today.
    "from os import fstat\nfstat(fd)", "from os import lstat as ls\nls(p)", "from os import path",
    "from io import StringIO\nStringIO()", "from io import BytesIO", "from builtins import str",
    "import builtins\nbuiltins.open(p, 'rb')", "builtins.getattr(os, 'fstat')(fd)", "os.open not in os.supports_dir_fd",
    "flags = os.O_RDONLY\nflags |= getattr(os, 'O_NOFOLLOW', 0)\nos.open(p, flags)",
    "a = os.O_RDONLY\nb = a | os.O_NOFOLLOW\nos.open(p, b)", "import os\nimport os.path", "import stat",
    "from types import SimpleNamespace", "os.getpid()", "hasattr(os, 'O_NOFOLLOW')", "getattr(os, 'fstat')(fd)",
    "getattr(os, 'getpid')()", "getattr(owner, 'read_pubkey')(path)", "x = getattr(head, 'read')",
    "getattr(value, name)", "getattr(entry, 'st_file_attributes', 0)",
    'getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_BINARY", 0) | getattr(os, "O_NONBLOCK", 0)',
    "os.open(p, os.O_RDONLY | os.O_NOFOLLOW | getattr(os, 'O_CLOEXEC', 0))",
    "flags = os.O_RDONLY | os.O_DIRECTORY\nos.open(p, flags, dir_fd=parent)", "os.open(p, os.O_RDONLY, 0o600)",
    "getattr(quote_source, 'read', None)", "getattr(chain, 'seed', None)", "getattr(chain, 'successor', None)",
    "getattr(exc, 'code', None)", "getattr(inputs, 'now', None)", "getattr(source, 'account_scope', None)",
    "getattr(protocol, 'bar_seconds', None)", "getattr(history, 'record_slot', None)",
    "from core.compliance.alerts import toast",
    # Negative controls for the binding rule: a pure local, and parameters, loops and imports that are not the flags.
    "def f(p):\n    flags = os.O_RDONLY\n    os.open(p, flags)",
    "def f(p, mode):\n    flags = os.O_RDONLY | os.O_NOFOLLOW\n    os.open(p, flags)",
    "import os\nfor name in names:\n    pass\nflags = os.O_RDONLY\nos.open(p, flags)",
)
WRITES = (
    "open(p, 'ab')", "open(p, mode='w')", "open(p, m)", "p.open('a')", "p.open(mode='xb')", "io.open(p, 'w')",
    "p.write_text(s)", "p.write_bytes(b'')", "p.touch()", "p.unlink()", "p.mkdir()", "p.replace(q)",
    "p.rename(q)", "p.symlink_to(q)", "checked_target(p).mkdir(mode=0o777)", "os.replace(a, b)", "os.remove(p)",
    "os.makedirs(p)", "os.link(a, b)", "os.truncate(p, 0)", "os.write(fd, b'x')", "os.fdopen(fd, 'w')",
    "os.open(p, os.O_CREAT | os.O_WRONLY)", "os.open(p, 769)", "flags = os.O_APPEND", "import shutil",
    "from shutil import copyfile", "shutil.rmtree(p)",
    # The same writes behind a from-import, a bare flag name, a getattr with a constant name, flags that are not
    # os.O_* attributes, and the other stdlib writers.
    "from os import replace\nreplace(a, b)", "from os import remove as rm\nrm(p)",
    "from os import makedirs\nmakedirs(p)", "from io import open as io_open\nio_open(p, 'w')",
    "from builtins import open as o\no(p, 'w')", "from nt import replace", "from posix import write",
    "from os import O_WRONLY, O_CREAT\nos.open(p, O_WRONLY | O_CREAT)", "os.open(p, O_WRONLY)", "flags = O_APPEND",
    "getattr(os, 'replace')(a, b)", "x = getattr(p, 'write_text')",
    "os.open(p, getattr(os, 'O_WRONLY') | getattr(os, 'O_CREAT'))", "os.open(p, 1 | 64)",
    "os.open(p, os.O_RDONLY | 64)", "os.open(p, flags=1025)", "os.open(p, int(x))", "io.FileIO(p, 'w')",
    "import tempfile", "from tempfile import mkstemp", "tempfile.mkstemp()", "import logging",
    "logging.basicConfig(filename=p)", "from logging import FileHandler", "import logging.handlers",
    # Numeric flags laundered through a name, a parameter or an unassigned name; FileIO and open by from-import or
    # under builtins and _io; a getattr spelt builtins.getattr.
    "flags = 1 | 64\nos.open(p, flags)", "w = 64\nos.open(p, os.O_RDONLY | w)", "flags = int(x)\nos.open(p, flags)",
    "def f(p, flags):\n    os.open(p, flags)", "os.open(p, flags)", "flags = os.O_RDONLY\nflags = 1025\nos.open(p, flags)",
    "flags = os.O_RDONLY\nflags |= 1\nos.open(p, flags)", "from io import FileIO\nFileIO(p, 'w')",
    "from _io import FileIO", "_io.open(p, 'w')", "import builtins\nbuiltins.open(p, 'w')", "builtins.open('f', 'w')",
    "builtins.getattr(os, 'replace')(a, b)",
    # A name bound any other way is not provably os.O_* bits: a parameter (also one only augmented with pure
    # bits), an import, a walrus, unpacking, for, with, match or except target, a name that is only augmented,
    # and a name cycle fed by a parameter, each beside a pure assignment of the same name.
    "flags = os.O_RDONLY\ndef f(p, flags):\n    os.open(p, flags)",
    "def g():\n    flags = os.O_RDONLY\n    return flags\ndef f(p, flags):\n    os.open(p, flags)",
    "def f(p, flags):\n    flags |= os.O_RDONLY\n    os.open(p, flags)",
    "flags |= os.O_RDONLY\nos.open(p, flags)",
    "from m import flags\nflags = flags | os.O_RDONLY\nos.open(p, flags)",
    "flags = os.O_RDONLY\nif (flags := 1025):\n    pass\nos.open(p, flags)",
    "flags = os.O_RDONLY\nflags, x = 1025, 0\nos.open(p, flags)",
    "flags = os.O_RDONLY\nfor flags in (1025,):\n    os.open(p, flags)",
    "flags = os.O_RDONLY\nwith x as flags:\n    os.open(p, flags)",
    "flags = os.O_RDONLY\nmatch x:\n    case int() as flags:\n        os.open(p, flags)",
    "flags = os.O_RDONLY\ntry:\n    pass\nexcept E as flags:\n    os.open(p, flags)",
    "def f(p, b):\n    a = b\n    b = a\n    os.open(p, a)",
)


def test_launch_guard_pins_transport_routes_and_process_effects():
    for source in HITS:
        assert problems(source), source
    for source in CLEAN:
        assert not problems(source), (source, problems(source))


def test_launch_guard_names_the_effect_behind_bare_names_aliases_and_constant_getattr():
    """The ban sees through a from-import, a module alias, a star import and a getattr with a constant name, and
    names the effect it found; a getattr with a computed name (the dataclass field loops) is left to review."""
    for source, why in (("getattr(os, 'system')(c)", "process escape"), ("f = getattr(os, 'spawnv')", "process escape"),
                        ("os.execl(a, b)", "process escape"), ("from os import system as s", "process escape"),
                        ("getattr(owner, 'load_context')(now)", "privileged reference"),
                        ("getattr(owner, 'load_context')(now)", "privileged or dynamic call"),
                        ("from core.compliance.owner import load_context as lc", "privileged reference"),
                        ("getattr(os, 'getenv')('K')", "privileged or dynamic call"),
                        ("import os as o", "os module under another name"), ("import nt", "os module under another name"),
                        ("from os import *", "star import"), ("getattr(os, 'replace')(a, b)", "write outside pinned writer"),
                        ("from os import O_CREAT", "write outside pinned writer"),
                        ("os.open(p, 1 | 64)", "write outside pinned writer"), ("import tempfile", "write outside pinned writer")):
        assert why in problems(source), (source, problems(source))
    cas = "trusted head advance outside pinned callers"
    for source in ("x = getattr(head, 'compare_and_set')", "from execution_launch.baseline_head import compare_and_set"):
        assert cas in problems(source, "execution_launch/driver.py"), source
        assert cas not in problems(source, HISTORY), source
    operator = "operator-only head initialization outside its module"
    assert operator in problems("getattr(head, 'initialize_reviewed_head')(x)", "execution_launch/runner.py")
    assert operator not in problems("getattr(head, 'initialize_reviewed_head')(x)", HEAD)
    assert not problems("n = 'replace'\ngetattr(os, n)(a, b)")           # a computed name is review's, by design


def test_launch_write_ban_covers_every_shape_and_pins_writers_by_file_and_exact_call():
    for source in WRITES:
        for relative in ("", "execution_launch/runner.py", "execution_network/route.py"):
            assert "write outside pinned writer" in problems(source, relative), (source, relative)
    shape = 'checked_target(self._dir, "x", within=self._root).mkdir(mode=0o700, exist_ok=True)'
    pinned = {"execution_launch/writer.py": frozenset({ast.dump(ast.parse(shape, mode="eval").body)})}
    with patch.dict(_PINNED_WRITE_TREES, pinned, clear=True):
        assert not problems(shape, "execution_launch/writer.py")
        for relative in ("", "execution_launch/runner.py", "execution_launch/nested/writer.py",
                         "execution_network/writer.py"):
            assert problems(shape, relative), relative
        assert problems(shape.replace("self._root", "other_root"), "execution_launch/writer.py")
        assert problems(shape.replace("exist_ok=True", "exist_ok=False"), "execution_launch/writer.py")
        assert problems(shape + "\np.unlink()", "execution_launch/writer.py")
    lock = ('os.open(checked_target(self._dir / "h.lock", "lock", within=self._dir), '
            'os.O_WRONLY | os.O_CREAT | os.O_EXCL)')
    pinned = {"execution_launch/writer.py": frozenset({ast.dump(ast.parse(lock, mode="eval").body)})}
    with patch.dict(_PINNED_WRITE_TREES, pinned, clear=True):
        assert not problems(lock, "execution_launch/writer.py")
        assert problems(lock + "\nflags = os.O_WRONLY", "execution_launch/writer.py")
        assert problems(lock.replace("os.O_EXCL", "os.O_TRUNC"), "execution_launch/writer.py")
    assert all(relative.split("/")[0] in PACKAGES for relative in PINNED_WRITES)
    # A helper that takes its flags as a parameter is a hit even where the module also assigns a pure flags.
    workflow = (ROOT / "execution_launch" / "workflow.py").read_text(encoding="utf-8")
    assert not problems(workflow, "execution_launch/workflow.py")
    helper = workflow + "\n\ndef _helper(path, flags):\n    return os.open(path, flags)\n"
    assert "write outside pinned writer" in problems(helper, "execution_launch/workflow.py")


def test_continuous_archive_writes_are_exact_and_cannot_migrate_into_pure_modules():
    source = (ROOT / CONTINUOUS_ARCHIVE).read_text(encoding="utf-8")
    assert not problems(source, CONTINUOUS_ARCHIVE), problems(source, CONTINUOUS_ARCHIVE)
    calls = {ast.dump(node) for node in ast.walk(ast.parse(source)) if isinstance(node, ast.Call)}
    assert _PINNED_WRITE_TREES[CONTINUOUS_ARCHIVE] <= calls, "a pinned candidate write shape is unused"
    write = "write outside pinned writer"
    for shape in PINNED_WRITES[CONTINUOUS_ARCHIVE]:
        assert not problems(shape, CONTINUOUS_ARCHIVE), shape
        for relative in ("", "execution_launch/account_interval.py", "execution_launch/continuous_guard.py",
                         "execution_launch/nested/continuous_archive.py", "execution_network/continuous_archive.py",
                         "execution_accounts/continuous.py"):
            assert write in problems(shape, relative), (shape, relative)
    mutations = (
        PINNED_WRITES[CONTINUOUS_ARCHIVE][0].replace("within=root", "within=other_root"),
        PINNED_WRITES[CONTINUOUS_ARCHIVE][0].replace("0o700", "0o777"),
        PINNED_WRITES[CONTINUOUS_ARCHIVE][0].replace("execution-price-paths", "other-directory"),
        PINNED_WRITES[CONTINUOUS_ARCHIVE][1].replace("within=directory", "within=other_directory"),
        PINNED_WRITES[CONTINUOUS_ARCHIVE][1].replace("os.O_EXCL", "os.O_TRUNC"),
        PINNED_WRITES[CONTINUOUS_ARCHIVE][1].replace("candidate_sha", "untrusted_name"),
        PINNED_WRITES[CONTINUOUS_ARCHIVE][1].replace("0o600", "0o666"),
        PINNED_WRITES[CONTINUOUS_ARCHIVE][2].replace('"wb"', '"ab"'),
        'os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)',
        'path.unlink()', 'path.write_bytes(payload)', 'os.replace(source, destination)',
    )
    for mutation in mutations:
        assert write in problems(mutation, CONTINUOUS_ARCHIVE), mutation
    for extra in ("import requests", "owner.load_context(now)", "os.environ['UPBIT_SECRET_KEY']",
                  "head.compare_and_set(old, new)"):
        assert problems(extra, CONTINUOUS_ARCHIVE), extra
    account_source = (ROOT / "execution_accounts/continuous.py").read_text(encoding="utf-8")
    from tests.accounts_guards import problems as account_problems
    assert not account_problems(account_source, "continuous.py")
    assert not problems(account_source, "execution_accounts/continuous.py")
    assert not problems((ROOT / "execution_launch/continuous_guard.py").read_text(encoding="utf-8"),
                        "execution_launch/continuous_guard.py")


def test_universe_store_writes_are_exact_and_cannot_migrate():
    source = (ROOT / UNIVERSE_STORE).read_text(encoding="utf-8")
    assert not problems(source, UNIVERSE_STORE), problems(source, UNIVERSE_STORE)
    calls = {ast.dump(node) for node in ast.walk(ast.parse(source)) if isinstance(node, ast.Call)}
    assert _PINNED_WRITE_TREES[UNIVERSE_STORE] <= calls, "a pinned universe write shape is unused"
    write = "write outside pinned writer"
    for shape in PINNED_WRITES[UNIVERSE_STORE]:
        assert not problems(shape, UNIVERSE_STORE), shape
        for relative in ("", STUDY, "execution_launch/nested/universe_store.py", "execution_network/universe_store.py"):
            assert write in problems(shape, relative), (shape, relative)
    create, rename = PINNED_WRITES[UNIVERSE_STORE][1], PINNED_WRITES[UNIVERSE_STORE][3]
    for altered in (create.replace("os.O_EXCL", "os.O_TRUNC"), create.replace(" | os.O_EXCL", ""),
                    create.replace("within=directory", "within=other"), create.replace("0o600", "0o644"),
                    rename.replace("os.rename", "os.replace"), rename.replace("within=directory)", "within=root)"),
                    "os.replace(source, target)", "os.rename(source, target)", "os.link(source, target)",
                    "path.write_bytes(raw)", "os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)"):
        assert write in problems(altered, UNIVERSE_STORE), altered
    for extra in ("import requests", "owner.load_context(now)", "os.environ['TRADEGEN_HOME']", 'P = "/v1/ticker"'):
        assert problems(extra, UNIVERSE_STORE), extra


def test_evidence_object_writes_are_exact_and_cannot_gain_head_or_order_authority():
    source = (ROOT / EVIDENCE_OBJECTS).read_text(encoding="utf-8")
    assert not problems(source, EVIDENCE_OBJECTS), problems(source, EVIDENCE_OBJECTS)
    calls = {ast.dump(node) for node in ast.walk(ast.parse(source)) if isinstance(node, ast.Call)}
    assert _PINNED_WRITE_TREES[EVIDENCE_OBJECTS] <= calls, "a pinned evidence-object write shape is unused"
    write = "write outside pinned writer"
    for shape in PINNED_WRITES[EVIDENCE_OBJECTS]:
        assert not problems(shape, EVIDENCE_OBJECTS), shape
        for relative in ("", "execution_launch/driver.py", "execution_launch/nested/evidence_objects.py",
                         "execution_network/evidence_objects.py", HISTORY, STUDY):
            # Some other reviewed writers share fdopen shapes; file-local calls
            # unique to this store must not migrate to any other runtime file.
            if ast.dump(ast.parse(shape, mode="eval").body) not in _PINNED_WRITE_TREES.get(relative, ()):
                assert write in problems(shape, relative), (shape, relative)
    for altered in (
        PINNED_WRITES[EVIDENCE_OBJECTS][0].replace("self.root", "other_root"),
        PINNED_WRITES[EVIDENCE_OBJECTS][1].replace("0o700", "0o777"),
        PINNED_WRITES[EVIDENCE_OBJECTS][2].replace("os.O_EXCL", "os.O_TRUNC"),
        PINNED_WRITES[EVIDENCE_OBJECTS][2].replace("0o600", "0o666"),
        PINNED_WRITES[EVIDENCE_OBJECTS][5].replace("pending", "untrusted_path"),
        PINNED_WRITES[EVIDENCE_OBJECTS][5].replace(" | os.O_EXCL", ""),
        PINNED_WRITES[EVIDENCE_OBJECTS][7].replace("os.O_EXCL", "os.O_TRUNC"),
        PINNED_WRITES[EVIDENCE_OBJECTS][8].replace("pending", "target"),
        "os.replace(pending, target)", "os.rename(pending, target)", "os.link(pending, target)",
        "path.write_bytes(raw)",
    ):
        assert write in problems(altered, EVIDENCE_OBJECTS), altered
    for extra in ("import requests", "owner.load_context(now)", "os.environ['UPBIT_SECRET_KEY']",
                  "head.compare_and_set(old, new)", "head.initialize_reviewed_head(old)", "controller.arm(x)"):
        assert problems(extra, EVIDENCE_OBJECTS), extra


def test_trusted_head_is_advanced_only_by_pinned_callers():
    from tests.acceptance import runtime_py
    hit = "trusted head advance outside pinned callers"
    for source in ("trusted_head.compare_and_set(a, b)", "f = head.compare_and_set", "compare_and_set(a, b)"):
        assert hit in problems(source, "execution_launch/driver.py")
        assert hit in problems(source, "execution_launch/nested/live_history.py")
        assert hit not in problems(source, "execution_launch/live_history.py")
    callers = set()
    for path in runtime_py():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        if any("compare_and_set" in _reached(n) for n in ast.walk(tree)):
            callers.add(path.relative_to(ROOT).as_posix())
    assert callers and callers <= CAS_CALLERS, callers


def test_head_authority_writes_are_exact_and_operator_steps_have_no_runtime_caller():
    from tests.acceptance import runtime_py
    source = (ROOT / HEAD).read_text(encoding="utf-8")
    assert not problems(source, HEAD), problems(source, HEAD)
    calls = {ast.dump(node) for node in ast.walk(ast.parse(source)) if isinstance(node, ast.Call)}
    assert _PINNED_WRITE_TREES[HEAD] <= calls, "a pinned head write shape is unused"
    write = "write outside pinned writer"
    for shape in PINNED_WRITES[HEAD]:
        for relative in ("", "execution_launch/runner.py", "execution_launch/nested/baseline_head.py"):
            assert write in problems(shape, relative), (shape, relative)
    assert write in problems(PINNED_WRITES[HEAD][0].replace("self._root", "other_root"), HEAD)
    assert write in problems(PINNED_WRITES[HEAD][3].replace("os.O_EXCL", "os.O_TRUNC"), HEAD)
    for extra in ("os.replace(a, b)", "path.unlink()", "os.open(p, os.O_WRONLY | os.O_TRUNC)", "import shutil",
                  "flags = os.O_APPEND", "os.fdopen(descriptor, 'ab')"):
        assert write in problems(extra, HEAD), extra
    operator = "operator-only head initialization outside its module"
    for text in ("head.initialize_reviewed_head(x)", "f = head.initialize_reviewed_head", "initialize_reviewed_head(x)"):
        for relative in ("", "execution_launch/runner.py", "execution_accounts/baseline_bridge.py"):
            assert operator in problems(text, relative), (text, relative)
        assert operator not in problems(text, HEAD)
    assert "trusted head advance outside pinned callers" in problems("trusted_head.compare_and_set(a, b)", HEAD)
    referencing = set()
    for path in runtime_py():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        relative = path.relative_to(ROOT).as_posix()
        allowed = set()
        setup_calls = (OWNER_SETUP_CALLS if relative == OWNER_SETUP else
                       {"provision_research_store": "store.head.initialize_reviewed_head(store.genesis_digest)"}
                       if relative == OWNER_RESEARCH_SETUP else {})
        if setup_calls:
            # Exact explicit operator functions only; runtime readers/writers
            # cannot initialize, adopt or repair authority heads.
            definitions = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
            for function, shape in setup_calls.items():
                expected = ast.dump(ast.parse(shape, mode="eval").body)
                matches = [n for n in ast.walk(definitions[function])
                           if isinstance(n, ast.Call) and ast.dump(n) == expected]
                assert len(matches) == 1, (relative, function)
                allowed.update(id(n) for n in ast.walk(matches[0]))
        if any(id(n) not in allowed and _reached(n) & OPERATOR_ONLY for n in ast.walk(tree)):
            referencing.add(path.relative_to(ROOT).as_posix())
    assert not referencing, referencing


def test_live_history_writes_are_exact_and_only_through_pinned_checked_targets():
    source = (ROOT / HISTORY).read_text(encoding="utf-8")
    assert not problems(source, HISTORY), problems(source, HISTORY)
    calls = {ast.dump(node) for node in ast.walk(ast.parse(source)) if isinstance(node, ast.Call)}
    assert _PINNED_WRITE_TREES[HISTORY] <= calls, "a pinned history write shape is unused"
    write = "write outside pinned writer"
    for shape in PINNED_WRITES[HISTORY]:
        assert not problems(shape, HISTORY), shape
        for relative in ("", "execution_launch/driver.py", "execution_launch/nested/live_history.py",
                         "execution_network/route.py"):
            assert write in problems(shape, relative), (shape, relative)
        assert write in problems(shape.replace("self._dir", "other_dir"), HISTORY), shape
    for extra in ("open(p, 'ab')", "open(p, mode='w')", "open(p, m)", "p.open('a')", "p.open(mode='xb')",
                  "p.write_text(s)", "p.write_bytes(b'')", "p.touch()", "p.unlink()", "p.mkdir()",
                  "checked_target(p).mkdir(mode=0o777)", "os.replace(a, b)", "os.remove(p)", "os.makedirs(p)",
                  "os.open(p, os.O_CREAT | os.O_WRONLY)", "import shutil", "from shutil import copyfile"):
        assert write in problems(extra, HISTORY), extra
    assert not problems("with open(p, 'rb') as fh:\n    fh.read()\npath.open('rb')\nos.open(p, os.O_RDONLY)", HISTORY)
    assert not problems("self._head_authority.compare_and_set(old, new)", HISTORY)
    assert "operator-only head initialization outside its module" in problems("head.initialize_reviewed_head(x)", HISTORY)


def test_study_writes_are_exact_and_only_through_pinned_checked_targets():
    source = (ROOT / STUDY).read_text(encoding="utf-8")
    assert not problems(source, STUDY), problems(source, STUDY)
    calls = {ast.dump(node) for node in ast.walk(ast.parse(source)) if isinstance(node, ast.Call)}
    assert _PINNED_WRITE_TREES[STUDY] <= calls, "a pinned study write shape is unused"
    write = "write outside pinned writer"
    for shape in PINNED_WRITES[STUDY]:
        assert not problems(shape, STUDY), shape
        for relative in ("", "execution_launch/driver.py", "execution_launch/nested/study.py",
                         "execution_network/route.py", HEAD, HISTORY):
            assert write in problems(shape, relative), (shape, relative)
    create = PINNED_WRITES[STUDY][0]
    for altered in (create.replace("within=directory", "within=other"), create.replace("os.O_EXCL", "os.O_TRUNC"),
                    create.replace(" | os.O_EXCL", ""), create.replace("directory / name", "directory / other"),
                    create.replace("0o600", "0o644")):
        assert write in problems(altered, STUDY), altered
    for extra in ("open(p, 'ab')", "open(p, mode='w')", "p.open('a')", "p.write_text(s)", "p.write_bytes(b'')",
                  "p.touch()", "p.unlink()", "p.mkdir()", "os.replace(a, b)", "os.remove(p)", "os.makedirs(p)",
                  "os.write(fd, b'x')", "os.open(p, os.O_WRONLY | os.O_CREAT)", "os.fdopen(descriptor, 'wb')",
                  "os.fdopen(descriptor, 'r+b')", "import shutil", "flags = os.O_APPEND",
                  PINNED_WRITES[HEAD][0], PINNED_WRITES[HISTORY][2]):
        assert write in problems(extra, STUDY), extra
    assert not problems("with open(p, 'rb') as fh:\n    fh.read()\npath.open('rb')\nos.open(p, os.O_RDONLY)\n"
                        "os.lstat(p)\nos.fsync(fd)\nhandle.write(raw)", STUDY)
    assert "trusted head advance outside pinned callers" in problems("trusted_head.compare_and_set(a, b)", STUDY)
    assert "operator-only head initialization outside its module" in problems("head.initialize_reviewed_head(x)", STUDY)


def test_guard_reads_pin_utf8():
    assert read_text_without_encoding("x = Path(p).read_text()\n") == ["read_text without encoding"]
    assert read_text_without_encoding("x = p.read_text(errors='replace')\n") == ["read_text without encoding"]
    assert read_text_without_encoding("p.write_text(s)\n") == ["write_text without encoding"]
    assert read_text_without_encoding("with open(p) as fh:\n    fh.read()\n") == ["text open without encoding"]
    assert read_text_without_encoding("open(p, 'r')\n") == ["text open without encoding"]
    assert not read_text_without_encoding("x = p.read_text(encoding='utf-8')\nopen(p, 'rb')\n"
                                          "open(p, encoding='utf-8')\np.write_text(s, encoding='utf-8')\n"
                                          "os.open(p, flags)\nopen(p, mode)\n")
    for path in sorted((ROOT / "tests").glob("*guard*.py")):
        assert not read_text_without_encoding(path.read_text(encoding="utf-8")), path.name


def test_protective_store_writes_stay_exact_and_cannot_self_initialize_authority():
    source = (ROOT / PROTECTIVE_STORE).read_text(encoding="utf-8")
    assert not problems(source, PROTECTIVE_STORE), problems(source, PROTECTIVE_STORE)
    calls = {ast.dump(node) for node in ast.walk(ast.parse(source)) if isinstance(node, ast.Call)}
    assert _PINNED_WRITE_TREES[PROTECTIVE_STORE] <= calls
    write = "write outside pinned writer"
    for shape in PINNED_WRITES[PROTECTIVE_STORE]:
        assert not problems(shape, PROTECTIVE_STORE), shape
        # Existing writers already pin some shared fdopen shapes. Test migration
        # into unapproved modules without revoking those reviewed exceptions.
        for relative in ("", "execution_launch/protective_state.py", "execution_launch/nested/protective_store.py",
                         "execution_network/protective_store.py"):
            assert write in problems(shape, relative), (shape, relative)
    create = PINNED_WRITES[PROTECTIVE_STORE][1]
    append = PINNED_WRITES[PROTECTIVE_STORE][5]
    for altered in (create.replace("os.O_EXCL", "os.O_TRUNC"), create.replace(" | os.O_EXCL", ""),
                    create.replace("within=self.root", "within=other"), create.replace("0o600", "0o666"),
                    append.replace("os.O_APPEND", "os.O_TRUNC"), append.replace("target,", "other,"),
                    "os.replace(source, target)", "path.unlink()", "path.write_bytes(raw)",
                    "self.root.mkdir(mode=0o777)"):
        assert write in problems(altered, PROTECTIVE_STORE), altered
    for extra in ("import requests", "owner.load_context(now)", "owner.arm(x)",
                  "os.environ['UPBIT_SECRET_KEY']", "head.initialize_reviewed_head(x)"):
        assert problems(extra, PROTECTIVE_STORE), extra
    assert not problems("store.head.compare_and_set(previous.head, row['row_sha256'])", PROTECTIVE_STORE)
    assert "trusted head advance outside pinned callers" in problems(
        "store.head.compare_and_set(previous.head, row['row_sha256'])", "execution_launch/protective_state.py")


def test_launch_and_account_tests_start_no_process():
    from tests.control_guards import _test_process_problems
    for source in ("import subprocess\n", "import multiprocessing\n", "x = sys.executable\n",
                   "importlib.reload(m)\n", "p = ctx.Process(target=f)\n"):
        assert _test_process_problems("tests/launch_x.py", source), source
    paths = (sorted((ROOT / "tests").glob("launch_*.py")) + sorted((ROOT / "tests").glob("accounts_*.py"))
             + [ROOT / "tests" / "network_route.py"])
    hits = [(path.name, why) for path in paths
            for why in _test_process_problems(path.relative_to(ROOT).as_posix(), path.read_text(encoding="utf-8"))]
    assert not hits, hits


def test_wrapper_flags_a_change_to_the_real_baseline_history_and_head_homes():
    from tests import control_acceptance as CA
    fake = Path(os.environ["TRADEGEN_HOME"]) / "fake_real"
    stand_ins = tuple(fake / name for name in ("execution-control", "execution_orders", "execution-baseline",
                                                "execution-history", "TRADEGEN-head"))
    for directory in stand_ins:
        directory.mkdir(parents=True)
    keep = CA._REAL
    try:
        CA._REAL = stand_ins
        CA._wrap(lambda: None)()
        for directory in stand_ins[2:]:
            try:
                CA._wrap(lambda: (directory / "record.json").write_bytes(b"{}"))()
            except AssertionError as exc:
                assert "test changed a real execution-control home" in str(exc), exc
            else:
                raise AssertionError("a change under a real home was not flagged")
    finally:
        CA._REAL = keep
    home = Path.home() / ".tradegen"
    assert {home / "execution-baseline", home / "execution-history"} <= set(CA._REAL)
    if os.environ.get("LOCALAPPDATA"):
        assert Path(os.environ["LOCALAPPDATA"]) / "TRADEGEN-head" in CA._REAL


def test_research_bundle_store_writes_and_operator_provisioning_stay_narrow():
    from tests.acceptance import runtime_py
    source = (ROOT / RESEARCH_BUNDLE_STORE).read_text(encoding="utf-8")
    assert not problems(source, RESEARCH_BUNDLE_STORE), problems(source, RESEARCH_BUNDLE_STORE)
    calls = {ast.dump(node) for node in ast.walk(ast.parse(source)) if isinstance(node, ast.Call)}
    assert _PINNED_WRITE_TREES[RESEARCH_BUNDLE_STORE] <= calls
    write = "write outside pinned writer"
    for shape in PINNED_WRITES[RESEARCH_BUNDLE_STORE]:
        assert not problems(shape, RESEARCH_BUNDLE_STORE), shape
        for relative in ("", "execution_launch/research_bundle.py", "execution_launch/research_bundle_format.py",
                         "execution_launch/study_receipts.py", "execution_launch/nested/research_bundle_store.py"):
            assert write in problems(shape, relative), (shape, relative)
    create, append = PINNED_WRITES[RESEARCH_BUNDLE_STORE][0], PINNED_WRITES[RESEARCH_BUNDLE_STORE][4]
    for altered in (create.replace("os.O_EXCL", "os.O_TRUNC"), create.replace(" | os.O_EXCL", ""),
                    create.replace("target,", "other,"), create.replace("0o600", "0o666"),
                    append.replace("os.O_APPEND", "os.O_TRUNC"), append.replace("target,", "other,"),
                    "os.replace(source, target)", "path.unlink()", "path.write_bytes(raw)"):
        assert write in problems(altered, RESEARCH_BUNDLE_STORE), altered
    for extra in ("import requests", "owner.load_context(now)", "owner.arm(x)",
                  "os.environ['UPBIT_SECRET_KEY']", "head.initialize_reviewed_head(x)"):
        assert problems(extra, RESEARCH_BUNDLE_STORE), extra
    assert not problems("self.head.compare_and_set(old, new)", RESEARCH_BUNDLE_STORE)
    assert "trusted head advance outside pinned callers" in problems(
        "self.head.compare_and_set(old, new)", "execution_launch/research_bundle.py")
    for path in runtime_py():
        relative = path.relative_to(ROOT).as_posix()
        if relative == OWNER_RESEARCH_SETUP:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        assert not any("provision_research_store" in _reached(node) for node in ast.walk(tree)), relative
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                assert all(alias.name != "tools.owner.research_bundle" for alias in node.names), relative
            if isinstance(node, ast.ImportFrom):
                assert node.module != "tools.owner.research_bundle", relative
                assert not (node.module == "tools.owner" and any(alias.name == "research_bundle"
                                                                for alias in node.names)), relative


def test_archive_packet_writes_remain_exclusive_explicit_and_outside_authority():
    source = (ROOT / BUNDLE_REVIEW).read_text(encoding="utf-8")
    assert not problems(source, BUNDLE_REVIEW), problems(source, BUNDLE_REVIEW)
    calls = {ast.dump(node) for node in ast.walk(ast.parse(source)) if isinstance(node, ast.Call)}
    assert _PINNED_WRITE_TREES[BUNDLE_REVIEW] <= calls
    write = "write outside pinned writer"
    for shape in PINNED_WRITES[BUNDLE_REVIEW]:
        for relative in ("", "execution_launch/bundle_auth.py", "execution_launch/bundle_attestation.py",
                         "execution_launch/nested/bundle_review.py", "execution_network/bundle_review.py"):
            assert write in problems(shape, relative), (shape, relative)
    create = PINNED_WRITES[BUNDLE_REVIEW][2]
    for altered in (create.replace("os.O_EXCL", "os.O_TRUNC"), create.replace(" | os.O_EXCL", ""),
                    create.replace("0o600", "0o666"), create.replace("target if", "other if"),
                    "os.replace(source, target)", "path.unlink()", "path.write_bytes(raw)",
                    "os.mkdir(self.payloads, 0o777)"):
        assert write in problems(altered, BUNDLE_REVIEW), altered
    for extra in ("import requests", "owner.load_context(now)", "owner.arm(x)", "key.sign(raw)",
                  "head.initialize_reviewed_head(x)", "head.compare_and_set(old, new)"):
        assert problems(extra, BUNDLE_REVIEW), extra


def test_archive_packet_native_directory_pins_do_not_gain_write_or_delete_sharing():
    source = (ROOT / BUNDLE_REVIEW).read_text(encoding="utf-8")
    shapes = (
        'ctypes.WinDLL("kernel32", use_last_error=True)',
        'self._kernel.CreateFileW(path, 0x80, 0x1, None, 3, 0x02000000 | 0x00200000, None)',
        'self._kernel.GetFileInformationByHandle(handle, self._ctypes.byref(info))',
        'self._kernel.GetFinalPathNameByHandleW(handle, buffer, len(buffer), 0)',
        'self._kernel.CloseHandle(handle)',
    )
    names = {"WinDLL", "CreateFileW", "GetFileInformationByHandle", "GetFinalPathNameByHandleW", "CloseHandle"}
    expected = {ast.dump(ast.parse(shape, mode="eval").body) for shape in shapes}
    def exact_calls(value):
        calls = [node for node in ast.walk(ast.parse(value)) if isinstance(node, ast.Call)
                 and _call_name(node) in names]
        return len(calls) == len(expected) and {ast.dump(node) for node in calls} == expected
    assert exact_calls(source)
    assert not problems(source, BUNDLE_REVIEW)
    # An identical import elsewhere, an alias, or a different module receives
    # none of this narrowly scoped exception.
    for altered in (source + "\nimport ctypes\n", source + "\nfrom ctypes import wintypes\n",
                    source.replace("        import ctypes\n", "        import ctypes as native\n"),
                    source.replace("from ctypes import wintypes", "from ctypes import wintypes, windll"),
                    source.replace("class NativeDirectoryAPI:", "class DifferentAPI:")):
        assert "direct effect import" in problems(altered, BUNDLE_REVIEW)
    assert "direct effect import" in problems(source, "execution_launch/other.py")
    # Access is attributes-only, open-existing, with reparse inspection and no
    # WRITE/DELETE sharing. This is a code contract, not a native Windows test.
    for old, new in (("path, 0x80, 0x1", "path, 0x80, 0x7"),
                     ("path, 0x80, 0x1", "path, 0x40000000, 0x1"),
                     ("None, 3, 0x02000000", "None, 2, 0x02000000"),
                     ('"kernel32"', '"untrusted"')):
        assert old in source
        assert not exact_calls(source.replace(old, new)), (old, new)
        assert "direct effect import" in problems(source.replace(old, new), BUNDLE_REVIEW)
    assert not exact_calls(source + "\nself._kernel.CreateFileW(other, 0x80, 1, None, 3, 0, None)\n")
    changed = source.replace("        self._kernel = ctypes.WinDLL", "        self._kernel.DeleteFileW(path)\n        self._kernel = ctypes.WinDLL")
    assert "direct effect import" in problems(changed, BUNDLE_REVIEW)
    for extra in ("ctypes.windll.kernel32.DeleteFileW('unreviewed')",
                  "ctypes.CDLL('unreviewed')",
                  "alias = self._kernel; alias.DeleteFileW('unreviewed')"):
        changed = source.replace("        import ctypes\n", "        import ctypes\n        " + extra + "\n")
        assert "direct effect import" in problems(changed, BUNDLE_REVIEW), extra
    for extra in ("NativeDirectoryAPI()._kernel.DeleteFileW('unreviewed')",
                  "NativeDirectoryAPI()._ctypes.CDLL('unreviewed')"):
        assert "direct effect import" in problems(source + "\n" + extra + "\n", BUNDLE_REVIEW), extra
