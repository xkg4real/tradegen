"""New runtime roots remain in the signed and tested acting closure."""
import ast
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
import tempfile

ROOT = Path(__file__).resolve().parents[1]
PACKAGES = ("execution_launch", "execution_network")


def problems(source):
    failures = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            modules = ([alias.name for alias in node.names] if isinstance(node, ast.Import)
                       else [node.module or ""])
            for module in modules:
                if any(module == prefix or module.startswith(prefix + ".") for prefix in
                       ("requests", "socket", "http", "urllib.request", "subprocess", "tools.signer")):
                    failures.append("direct effect import")
        if isinstance(node, ast.Call):
            name = (node.func.id if isinstance(node.func, ast.Name) else
                    node.func.attr if isinstance(node.func, ast.Attribute) else "")
            if name in {"eval", "exec", "__import__", "sign", "sign_entry", "arm", "load_context", "getenv"}:
                failures.append("privileged or dynamic call")
            if name == "compile" and ast.unparse(node.func) != "re.compile":
                failures.append("dynamic compilation")
        if isinstance(node, (ast.Attribute, ast.Subscript)):
            if (isinstance(node, ast.Attribute) and ast.unparse(node) == "os.environ"):
                failures.append("environment access")
            if isinstance(node, ast.Attribute) and node.attr in {"__globals__", "__code__", "__closure__", "_ISSUED"}:
                failures.append("runtime mutation")
    return failures


def test_launch_and_network_do_not_directly_sign_arm_or_open_http():
    for package in PACKAGES:
        for path in (ROOT / package).rglob("*.py"):
            assert not problems(path.read_text()), (str(path), problems(path.read_text()))


def test_launch_guard_negative_controls():
    for source in ("import requests", "from urllib.request import urlopen", "import socket",
                   "import tools.signer.sign", "owner.load_context(now)", "owner.arm(x)",
                   "sign_entry(x)", "os.getenv('API_KEY')", "os.environ['API_KEY']",
                   "callback.__globals__", "eval(code)", "compile(code, 'x', 'exec')"):
        assert problems(source), source
    assert not problems("from urllib.parse import urlsplit\npattern = re.compile('x')")


def test_new_runtime_packages_are_signed_recursively_by_owner_and_signer():
    from core.compliance import owner
    from tools.signer import sign
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        for package in PACKAGES:
            nested = root / package / "unused"
            nested.mkdir(parents=True)
            (root / package / "__init__.py").write_text("")
            (nested / "future.py").write_text("VALUE = 1\n")
        before = dict(owner.code_files(root))
        assert before == dict(sign.code_files(root))
        for package in PACKAGES:
            key = package + "/unused/future.py"
            assert key in before
            (root / key).write_text("VALUE = 2\n")
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
        assert "execution_launch" in _suite_names((ROOT / name).read_text())
    with patch.object(launch_acceptance, "MODULES", ("deliberately_missing_launch_module",)), \
            redirect_stdout(StringIO()), redirect_stderr(StringIO()):
        result = run_all.run(launch_acceptance.tests())
    assert len(result) == 1 and result[0]["status"] == "FAIL"
