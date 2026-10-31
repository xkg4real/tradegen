"""Signed account evidence stays separate from signing and order effects."""
import ast
from pathlib import Path
import tempfile

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_MODULES = ("requests", "urllib", "socket", "http", "subprocess", "importlib",
                     "execution_orders", "tools.signer", "research_lab")
FORBIDDEN_CALLS = {"eval", "exec", "__import__", "compile", "request", "urlopen", "send",
                   "arm", "sign", "sign_entry", "load_context", "append_system", "_issue",
                   "write_text", "write_bytes", "unlink", "rename", "replace", "mkdir",
                   "system", "popen", "startfile", "transfer", "withdraw"}


COLLECTOR_ROUTES = frozenset({"/v1/accounts", "/v1/orders/open", "/v1/orders/closed",
                              "/v1/order", "/v1/deposits", "/v1/withdraws", "/v1/ticker"})


def problems(source, relative_path=""):
    tree = ast.parse(source)
    failures = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            modules = [a.name for a in node.names] if isinstance(node, ast.Import) else [node.module or ""]
            if any(m == banned or m.startswith(banned + ".") for m in modules for banned in FORBIDDEN_MODULES):
                failures.append("effectful import")
            if isinstance(node, ast.ImportFrom) and node.module == "core.compliance" and any(a.name == "owner" for a in node.names):
                failures.append("owner side effects")
        if isinstance(node, ast.Call):
            call = node.func.id if isinstance(node.func, ast.Name) else node.func.attr if isinstance(node.func, ast.Attribute) else ""
            regex_compile = isinstance(node.func, ast.Attribute) and ast.unparse(node.func) == "re.compile"
            collector_read = (relative_path == "upbit_collector.py" and isinstance(node.func, ast.Name)
                and node.func.id == "request" and len(node.args) == 4 and not node.keywords
                and all(isinstance(arg, ast.Constant) for arg in node.args[:3])
                and node.args[0].value == "upbit" and node.args[1].value == "GET"
                and node.args[2].value in COLLECTOR_ROUTES
                and isinstance(node.args[3], ast.Name) and node.args[3].id == "params")
            if call in FORBIDDEN_CALLS and not (call == "compile" and regex_compile) and not collector_read:
                failures.append("effectful call")
            if isinstance(node.func, ast.Attribute) and ast.unparse(node.func.value) == "os.environ":
                if not (call == "get" and len(node.args) == 1 and isinstance(node.args[0], ast.Constant)
                        and node.args[0].value == "TRADEGEN_HOME" and not node.keywords):
                    failures.append("credential value access")
            if call == "getenv":
                failures.append("credential value access")
        if isinstance(node, ast.Subscript) and ast.unparse(node.value) == "os.environ":
            failures.append("credential value access")
        if isinstance(node, ast.Attribute) and node.attr in {"__globals__", "__code__", "__closure__", "_ISSUED"}:
            failures.append("runtime mutation")
    return failures


def test_account_sources_have_no_signing_orders_network_or_writes():
    for path in (ROOT / "execution_accounts").rglob("*.py"):
        relative = path.relative_to(ROOT / "execution_accounts").as_posix()
        assert not problems(path.read_text(), relative), (relative, problems(path.read_text(), relative))


def test_only_reviewed_collector_literals_can_use_e1_authenticated_get():
    for route in COLLECTOR_ROUTES:
        source = f'request("upbit", "GET", {route!r}, params)'
        assert not problems(source, "upbit_collector.py")
        assert problems(source, "provider.py")
        assert problems(source, "nested/upbit_collector.py")
        assert problems(source.replace('"GET"', '"POST"'), "upbit_collector.py")
        assert problems(source.replace('"GET"', '"DELETE"'), "upbit_collector.py")
    for source in ('request("upbit", "GET", path, params)',
                   'request("upbit", "GET", "/v1/orders", params)',
                   'transport.request("upbit", "GET", "/v1/accounts", params)',
                   'request("okx", "GET", "/v1/accounts", params)',
                   'request("upbit", "GET", "/v1/accounts", params, data=body)'):
        assert problems(source, "upbit_collector.py"), source


def test_account_guard_negative_controls_cover_privileged_neighbors():
    for source in ("import requests\n", "from execution_orders import transport\n",
                   "from tools.signer import sign\n", "from core.compliance import owner\n",
                   "import research_lab.run\n", "owner.load_context(now, positions)\n",
                   "target.write_text(secret)\n", "os.environ['UPBIT_SECRET_KEY']\n",
                   "os.environ.get('KIS_APP_SECRET')\n", "os.getenv('KEY')\n",
                   "x.__globals__\n", "transport.request(v, m, p)\n",
                   "compile(code, 'x', 'exec')\n", "compiler.compile(code)\n"):
        assert problems(source), source
    assert not problems("present = 'KIS_APP_KEY' in os.environ\nstate = os.environ.get('TRADEGEN_HOME')\n")
    assert not problems("pattern = re.compile(r'[A-Z]+')\n")


def test_account_code_is_signed_recursively_in_owner_and_signer():
    from core.compliance import owner
    from tools.signer import sign
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        nested = root / "execution_accounts" / "nested"
        nested.mkdir(parents=True)
        (root / "execution_accounts" / "__init__.py").write_text("")
        (nested / "unused.py").write_text("VALUE = 1\n")
        first = dict(owner.code_files(root))
        assert first == dict(sign.code_files(root))
        assert "execution_accounts/nested/unused.py" in first
        (nested / "unused.py").write_text("VALUE = 2\n")
        second = dict(owner.code_files(root))
        assert second == dict(sign.code_files(root))
        assert first["execution_accounts/nested/unused.py"] != second["execution_accounts/nested/unused.py"]


def test_account_runtime_and_acting_graph_include_the_package():
    from tests.acceptance import runtime_py
    from core.ficc import context_log
    paths = {p.relative_to(ROOT).as_posix() for p in runtime_py()}
    assert {p.relative_to(ROOT).as_posix() for p in (ROOT / "execution_accounts").glob("*.py")} <= paths
    assert context_log.is_acting_module("execution_accounts.provider")
    assert not context_log.is_acting_module("research_lab.run")


def test_account_suite_is_complete_and_registered():
    from tests import accounts_acceptance, run_all
    from tests.compliance_guards import _suite_names
    names = [n for n, _ in run_all.select(run_all.tests(), suite="execution_accounts")]
    for module in accounts_acceptance.MODULES:
        assert any(n.startswith("execution_accounts/" + module + "/test_") for n in names), module
    for name in ("README.md", "tests/run_all.py"):
        assert "execution_accounts" in _suite_names((ROOT / name).read_text())
