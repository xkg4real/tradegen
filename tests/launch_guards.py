"""New runtime roots remain in the signed and tested acting closure."""
import ast
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
PROCESS_PREFIXES = ("execv", "spawn")
ENDPOINT = re.compile(r"(?i)/(?:v1|uapi|api/v5)/")
# One write ban for both packages. A writer row pins its exact call shapes under its own package-relative path;
# every other write, any other shape and any other file is a hit.
HEAD = "execution_launch/baseline_head.py"
HISTORY = "execution_launch/live_history.py"
STUDY = "execution_launch/study.py"
PINNED_WRITES: dict[str, tuple[str, ...]] = {
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
}
# The head's initialization is an explicit reviewed operator step: no runtime module may reference it.
OPERATOR_ONLY = frozenset({"initialize_reviewed_head"})
_PINNED_WRITE_TREES = {relative: frozenset(ast.dump(ast.parse(shape, mode="eval").body) for shape in shapes)
                       for relative, shapes in PINNED_WRITES.items()}
WRITE_FLAGS = frozenset({"O_CREAT", "O_WRONLY", "O_RDWR", "O_APPEND", "O_TRUNC"})
OS_WRITES = frozenset({"replace", "rename", "renames", "remove", "unlink", "mkdir", "makedirs", "rmdir",
                       "removedirs", "link", "symlink", "truncate", "ftruncate", "write", "pwrite", "writev",
                       "pwritev"})
PATH_WRITES = frozenset({"write_text", "write_bytes", "touch", "unlink", "rename", "rmdir", "mkdir",
                         "symlink_to", "hardlink_to"})
WRITE_MODE = re.compile(r"[wax+]")
# The trusted baseline head is advanced only by the account provider and the live-history journal.
CAS_CALLERS = frozenset({"execution_accounts/baseline_bridge.py", "execution_launch/live_history.py"})


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


def _writes(node):
    """A write of a file, directory or link, a write flag, or shutil in any form."""
    if isinstance(node, ast.Name):
        return node.id == "shutil"
    if isinstance(node, (ast.Import, ast.ImportFrom)):
        modules = [a.name for a in node.names] if isinstance(node, ast.Import) else [node.module or ""]
        return any(m == "shutil" or m.startswith("shutil.") for m in modules)
    if isinstance(node, ast.Attribute):
        return node.attr in WRITE_FLAGS
    if not isinstance(node, ast.Call):
        return False
    name = _call_name(node)
    if isinstance(node.func, ast.Name):
        return name == "open" and _mode_writes(node, 1)
    if not isinstance(node.func, ast.Attribute):
        return False
    owner = ast.unparse(node.func.value)
    if owner == "os":
        if name == "open":                                # numeric flags hide a write mode
            return isinstance(_mode_argument(node, 1, "flags"), ast.Constant)
        return name in OS_WRITES or (name == "fdopen" and _mode_writes(node, 1))
    if name == "open":
        return _mode_writes(node, 1 if owner in ("io", "codecs", "gzip", "bz2", "lzma") else 0)
    if name == "replace":                                 # Path.replace(target); str.replace takes two, datetime.replace keywords
        return (len(node.args) == 1 and not node.keywords) or [k.arg for k in node.keywords] == ["target"]
    return name in PATH_WRITES


def problems(source, relative=""):
    tree, failures = ast.parse(source), []
    pinned = {id(inner) for node in ast.walk(tree) if isinstance(node, ast.Call)
              and ast.dump(node) in _PINNED_WRITE_TREES.get(relative, frozenset()) for inner in ast.walk(node)}
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            modules = ([alias.name for alias in node.names] if isinstance(node, ast.Import)
                       else [node.module or ""])
            for module in modules:
                if any(module == prefix or module.startswith(prefix + ".") for prefix in TRANSPORT_PREFIXES):
                    failures.append("inquiry or order transport import")
                elif any(module == prefix or module.startswith(prefix + ".") for prefix in EFFECT_PREFIXES):
                    failures.append("direct effect import")
            if isinstance(node, ast.ImportFrom) and any(
                    alias.name in TRANSPORT_FROM.get(node.module, frozenset()) for alias in node.names):
                failures.append("inquiry or order transport import")
        if isinstance(node, ast.Call):
            name = _call_name(node)
            if name in PRIVILEGED:
                failures.append("privileged or dynamic call")
            if name == "compile" and ast.unparse(node.func) != "re.compile":
                failures.append("dynamic compilation")
            if name in PROCESS_CALLS or name.startswith(PROCESS_PREFIXES):
                failures.append("process escape")
        if isinstance(node, ast.Attribute):
            if ast.unparse(node) == "os.environ":
                failures.append("environment access")
            if node.attr in {"__globals__", "__code__", "__closure__", "_ISSUED"}:
                failures.append("runtime mutation")
            if node.attr in PRIVILEGED_REFERENCES:
                failures.append("privileged reference")
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and ENDPOINT.search(node.value):
            failures.append("venue endpoint literal")
        if id(node) not in pinned and _writes(node):
            failures.append("write outside pinned writer")
        if ((isinstance(node, ast.Attribute) and node.attr == "compare_and_set")
                or (isinstance(node, ast.Name) and node.id == "compare_and_set")) and relative not in CAS_CALLERS:
            failures.append("trusted head advance outside pinned callers")
        if ((isinstance(node, ast.Attribute) and node.attr in OPERATOR_ONLY)
                or (isinstance(node, ast.Name) and node.id in OPERATOR_ONLY)) and relative != HEAD:
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
)
CLEAN = (
    "from urllib.parse import urlsplit", "import msvcrt", "pattern = re.compile('x')",
    "from execution_accounts.quotes import to_runner_quote", "from execution_control.controller import Controller",
    "from execution_control.dry_run import DryRunAdapter", "from execution_accounts import baseline_bridge",
    "import math\nmath.copysign(1, x)", "text.replace('a', 'b')", "when.replace(tzinfo=None)",
    "with open(p, 'rb') as fh:\n    fh.read()", "path.open('rb')", "data = path.read_bytes()",
    "os.open(p, os.O_RDONLY | os.O_NOFOLLOW)", "os.fstat(fd)", "is_sealed(context)",
)
WRITES = (
    "open(p, 'ab')", "open(p, mode='w')", "open(p, m)", "p.open('a')", "p.open(mode='xb')", "io.open(p, 'w')",
    "p.write_text(s)", "p.write_bytes(b'')", "p.touch()", "p.unlink()", "p.mkdir()", "p.replace(q)",
    "p.rename(q)", "p.symlink_to(q)", "checked_target(p).mkdir(mode=0o777)", "os.replace(a, b)", "os.remove(p)",
    "os.makedirs(p)", "os.link(a, b)", "os.truncate(p, 0)", "os.write(fd, b'x')", "os.fdopen(fd, 'w')",
    "os.open(p, os.O_CREAT | os.O_WRONLY)", "os.open(p, 769)", "flags = os.O_APPEND", "import shutil",
    "from shutil import copyfile", "shutil.rmtree(p)",
)


def test_launch_guard_pins_transport_routes_and_process_effects():
    for source in HITS:
        assert problems(source), source
    for source in CLEAN:
        assert not problems(source), (source, problems(source))


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
        if any((isinstance(n, ast.Attribute) and n.attr == "compare_and_set")
               or (isinstance(n, ast.Name) and n.id == "compare_and_set") for n in ast.walk(tree)):
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
        if any((isinstance(n, ast.Attribute) and n.attr in OPERATOR_ONLY)
               or (isinstance(n, ast.Name) and n.id in OPERATOR_ONLY) for n in ast.walk(tree)):
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
