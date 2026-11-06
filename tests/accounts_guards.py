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

READ_ROUTES = {"upbit_collector.py": COLLECTOR_ROUTES,
               "quotes.py": frozenset({"/v1/orderbook"})}
TRANSPORT_IMPORTS = {
    "upbit_collector.py": frozenset({"inquiry_clock", "request"}),
    "quotes.py": frozenset({"Answer", "inquiry_clock", "request"}),
    "readiness.py": frozenset({"inquiry_clock"}),
    "instrument_terms.py": frozenset({"Answer", "inquiry_clock"}),
}

CHECKPOINT_WRITES = (
    'checked_target(self._root, "baseline directory", within=self._base).mkdir(mode=0o700, exist_ok=True)',
    'os.replace(checked_target(self._root / "checkpoint.tmp", "baseline temporary file", within=self._root), '
    'checked_target(self._root / "checkpoint.json", "baseline checkpoint", within=self._root))',
)
_CHECKPOINT_WRITE_TREES = frozenset(ast.dump(ast.parse(s, mode="eval").body) for s in CHECKPOINT_WRITES)


def _fixed_read_call(node, routes):
    return (isinstance(node, ast.Call) and bool(routes) and isinstance(node.func, ast.Name)
            and node.func.id == "request" and len(node.args) == 4 and not node.keywords
            and all(isinstance(arg, ast.Constant) for arg in node.args[:3])
            and node.args[0].value == "upbit" and node.args[1].value == "GET"
            and node.args[2].value in routes
            and isinstance(node.args[3], ast.Name) and node.args[3].id == "params")


def problems(source, relative_path=""):
    tree = ast.parse(source)
    failures = []
    routes = READ_ROUTES.get(relative_path, frozenset())
    allowed_requests = {id(node.func) for node in ast.walk(tree) if _fixed_read_call(node, routes)}
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            modules = [a.name for a in node.names] if isinstance(node, ast.Import) else [node.module or ""]
            if any(m == banned or m.startswith(banned + ".") for m in modules for banned in FORBIDDEN_MODULES):
                failures.append("effectful import")
            if isinstance(node, ast.ImportFrom) and node.module == "core.compliance" and any(a.name == "owner" for a in node.names):
                failures.append("owner side effects")
            if isinstance(node, ast.Import):
                if any(a.name == "execution.transport" or a.name.startswith("execution.transport.")
                       for a in node.names):
                    failures.append("transport module import")
            elif node.module == "execution.transport":
                permitted = TRANSPORT_IMPORTS.get(relative_path, frozenset())
                if node.level or any(a.name not in permitted or a.asname is not None for a in node.names):
                    failures.append("transport import outside fixed names")
            elif ((node.module or "").startswith("execution.transport.")
                  or node.module == "execution" and any(a.name == "transport" for a in node.names)):
                failures.append("transport module import")
        if (isinstance(node, ast.Constant) and isinstance(node.value, str)
                and "/v1/" in node.value.lower() and node.value not in routes):
            failures.append("endpoint literal outside fixed routes")
        if isinstance(node, ast.Name) and node.id == "request" and id(node) not in allowed_requests:
            failures.append("request outside fixed GET call")
        if isinstance(node, ast.Attribute) and node.attr == "request":
            failures.append("request attribute alias")
        if isinstance(node, ast.Call):
            call = node.func.id if isinstance(node.func, ast.Name) else node.func.attr if isinstance(node.func, ast.Attribute) else ""
            regex_compile = isinstance(node.func, ast.Attribute) and ast.unparse(node.func) == "re.compile"
            collector_read = id(node.func) in allowed_requests
            checkpoint_write = (relative_path == "baseline_store.py"
                                and ast.dump(node) in _CHECKPOINT_WRITE_TREES)
            if call in FORBIDDEN_CALLS and not (call == "compile" and regex_compile) and not collector_read and not checkpoint_write:
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
        found = problems(path.read_text(encoding="utf-8"), relative)
        assert not found, (relative, found)


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


def test_e1_transport_imports_and_request_aliases_are_pinned():
    for relative, names in TRANSPORT_IMPORTS.items():
        source = "from execution.transport import " + ", ".join(sorted(names))
        assert not problems(source, relative), (relative, source)
        assert problems(source, "nested/" + relative)
        assert problems(source, "provider.py")
    bad = (
        'from execution.transport import request as fetch\nfetch("upbit", "POST", "/v1/orders", params)',
        'from execution.transport import request as fetch\nfetch("upbit", "DELETE", "/v1/order", params)',
        'from execution.transport import request as request',
        'from execution.transport import *',
        'from execution.transport import _send',
        'import execution.transport as transport',
        'from execution import transport as wire',
        'r = request\nr("upbit", "GET", "/v1/accounts", params)',
        'r = transport.request\nr("upbit", "GET", "/v1/accounts", params)',
    )
    for relative in TRANSPORT_IMPORTS:
        for source in bad:
            assert problems(source, relative), (relative, source)
    assert problems("from execution.transport import request", "instrument_terms.py")


def test_account_endpoint_literals_are_file_exact():
    for relative, routes in READ_ROUTES.items():
        for route in routes:
            source = f'PATH = {route!r}'
            assert not problems(source, relative), (relative, route)
            assert problems(source, "provider.py")
            assert problems(source, "nested/" + relative)
    for route in ("/v1/orders", "/v1/withdraws/coin", "/v1/withdraws/krw",
                  "/v1/orders/open/x", "/v1/orders/uuids", "/v1/order/new",
                  "/v1/deposits/generate_coin_address", "/V1/ORDERS/OPEN",
                  "/v1/orderbook", "/v1/withdraws/coin_addresses"):
        assert problems(f'PATH = {route!r}', "upbit_collector.py"), route


def test_macro_collector_exception_preserves_exact_get_checks():
    from tests import macro_m0_harness as macro
    saved_root = macro.ROOT
    try:
        with tempfile.TemporaryDirectory(prefix="collector-guard-") as directory:
            macro.ROOT = root = Path(directory)
            collector = root / "execution_accounts" / "upbit_collector.py"
            collector.parent.mkdir()
            source = ('from execution.transport import inquiry_clock, request\n'
                      + "\n".join(f'request("upbit", "GET", {route!r}, params)'
                                  for route in sorted(COLLECTOR_ROUTES)))
            collector.write_text(source, encoding="utf-8")
            assert not macro._offences(collector), macro._offences(collector)
            for relative in ("execution_accounts/unreviewed.py",
                             "execution_accounts/nested/upbit_collector.py"):
                neighbor = root / relative
                neighbor.parent.mkdir(parents=True, exist_ok=True)
                neighbor.write_text(source, encoding="utf-8")
                assert macro._offences(neighbor), relative
            rejected = (
                'PATH = "/v1/orders"', 'PATH = "/v1/withdraws/coin"',
                'PATH = "/v1/orders/open/x"', 'PATH = "/V1/ORDERS/OPEN"',
                'request("upbit", "POST", "/v1/accounts", params)',
                'request("upbit", "DELETE", "/v1/order", params)',
                'request("upbit", "PUT", "/v1/accounts", params)',
                'request("upbit", "GET", path, params)',
                'request("upbit", "GET", "/v1/accounts", params, data=body)',
                'request("upbit", "GET", "/v1/accounts", body)',
                'from execution.transport import request as fetch\n'
                'fetch("upbit", "GET", "/v1/accounts", params)',
                'import ccxt', 'wallet.withdraw()',
                'requests.post("https://example.invalid/v1/orders")',
            )
            for candidate in rejected:
                collector.write_text(candidate, encoding="utf-8")
                assert macro._offences(collector), candidate
    finally:
        macro.ROOT = saved_root


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


def test_quote_source_exception_is_public_get_and_file_exact():
    source = 'request("upbit", "GET", "/v1/orderbook", params)'
    assert not problems(source, "quotes.py")
    for path in ("provider.py", "upbit_collector.py", "nested/quotes.py", ""):
        assert problems(source, path)
    for method in ("POST", "DELETE", "PUT"):
        assert problems(source.replace('"GET"', repr(method)), "quotes.py")
    for route in COLLECTOR_ROUTES | {"/v1/orders", "/v1/orderbooks"}:
        assert problems(source.replace('"/v1/orderbook"', repr(route)), "quotes.py")
    assert problems('request("upbit", "GET", path, params)', "quotes.py")
    assert problems('request("upbit", "GET", "/v1/orderbook", params, data=x)', "quotes.py")


def test_checkpoint_write_exception_is_path_shape_and_file_exact():
    for source in CHECKPOINT_WRITES:
        assert not problems(source, "baseline_store.py")
        for path in ("", "provider.py", "baseline_bridge.py", "nested/baseline_store.py"):
            assert problems(source, path)
        assert problems(source.replace("self._root", "other_root"), "baseline_store.py")
    for source in ('os.replace(source, destination)',
                   'os.replace(checked_target(source), checked_target(destination))',
                   'checked_target(path).mkdir(mode=0o777)',
                   'target.write_text(secret)', 'target.unlink()',
                   'request("upbit", "POST", "/v1/orders", params)'):
        assert problems(source, "baseline_store.py"), source


def test_account_code_is_signed_recursively_in_owner_and_signer():
    from core.compliance import owner
    from tools.signer import sign
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        nested = root / "execution_accounts" / "nested"
        nested.mkdir(parents=True)
        (root / "execution_accounts" / "__init__.py").write_text("", encoding="utf-8")
        (nested / "unused.py").write_text("VALUE = 1\n", encoding="utf-8")
        first = dict(owner.code_files(root))
        assert first == dict(sign.code_files(root))
        assert "execution_accounts/nested/unused.py" in first
        (nested / "unused.py").write_text("VALUE = 2\n", encoding="utf-8")
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
        assert "execution_accounts" in _suite_names((ROOT / name).read_text(encoding="utf-8"))
