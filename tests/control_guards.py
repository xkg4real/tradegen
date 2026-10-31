"""E2/E3 boundaries: exact protocol exceptions, one HTTP seam, signed coverage.

These AST checks catch reviewed classes of accidental bypass, not arbitrary
hostile Python. Runtime request/capability/lifecycle tests remain necessary.
"""
from __future__ import annotations

import ast
import os
from pathlib import Path
import re
import tempfile

ROOT = Path(__file__).resolve().parents[1]
PACKAGES = ("execution_control", "execution_orders")
TRANSPORT = "execution_orders/transport.py"
CONTROLLER = "execution_control/controller.py"
STORE = "execution_control/store.py"
CAPABILITY = "execution_control/capability.py"
STD = frozenset({"__future__", "base64", "collections.abc", "contextlib", "dataclasses", "datetime", "decimal",
                 "fcntl", "fractions", "hashlib", "hmac", "json", "math", "msvcrt", "os", "pathlib", "re",
                 "secrets", "threading", "types", "typing", "uuid", "weakref", "zoneinfo"})
PATHS = {
    "execution_orders/upbit.py": frozenset({"/v1/orders", "/v1/order"}),
    "execution_orders/kis.py": frozenset({
        "/uapi/domestic-stock/v1/trading/order-cash",
        "/uapi/domestic-stock/v1/trading/order-rvsecncl",
        "/uapi/domestic-stock/v1/trading/inquire-daily-ccld",
        "/uapi/overseas-stock/v1/trading/order",
        "/uapi/overseas-stock/v1/trading/order-rvsecncl",
        "/uapi/overseas-stock/v1/trading/inquire-ccnl",
    }),
    "execution_orders/okx.py": frozenset({"/api/v5/trade/order", "/api/v5/trade/cancel-order"}),
}
TRS = frozenset({"TTTC0011U", "TTTC0012U", "TTTC0013U", "TTTC0081R",
                 "TTTT1002U", "TTTT1006U", "TTTT1004U", "TTTS3035R"})
HOSTS = frozenset({"https://api.upbit.com", "https://openapi.koreainvestment.com:9443", "https://www.okx.com"})
HTTP_VERBS = frozenset({"post", "put", "patch", "delete", "request", "send", "urlopen", "getresponse",
                        "connect", "create_connection"})
FORBIDDEN_CALLS = frozenset({"eval", "exec", "__import__", "compile", "seal_context", "system", "popen",
                             "startfile", "fork", "forkpty", "posix_spawn", "posix_spawnp",
                             "transfer", "transfer_funds", "withdraw", "withdraw_coin", "withdraw_krw",
                             "create_withdrawal", "deposit_address", "generate_coin_address"})
WRITE_METHODS = frozenset({"write_text", "write_bytes", "touch", "unlink", "rename", "rmdir", "remove"})


def _files():
    return sorted(p for name in PACKAGES for p in (ROOT / name).rglob("*.py"))


def _checked(node):
    return isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "checked_target"


def _imports_allowed(rel, module):
    if module == "collections":
        return rel == "execution_control/dry_run.py"
    if module == "functools":
        return rel == CONTROLLER
    if module in STD:
        return True
    if module in {"requests", "urllib.parse"}:
        return rel == TRANSPORT
    if module == "core.isolation" or module == "core.compliance" or module.startswith("core.compliance."):
        return True
    if module == "core.odds" or module.startswith("core.odds."):
        return rel.startswith("execution_control/")
    if module in {"execution.snapshot", "execution.positions"}:
        return rel.startswith("execution_control/")
    return module in PACKAGES or any(module.startswith(name + ".") for name in PACKAGES)


def _problems(rel, source):
    tree = ast.parse(source)
    hits = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if (not _imports_allowed(rel, alias.name) or alias.name == "functools"
                        or alias.name == "requests" and alias.asname):
                    hits.append("unapproved import")
                if alias.name in {"execution_orders.transport", "execution.keys", "execution.transport"}:
                    hits.append("alternate transport or inquiry credential access")
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if node.level or not _imports_allowed(rel, module) or any(a.name == "*" for a in node.names):
                hits.append("unapproved from import")
            if module == "functools" and (rel != CONTROLLER or len(node.names) != 1
                    or node.names[0].name != "wraps" or node.names[0].asname is not None):
                hits.append("unapproved functools helper")
            if module == "execution_orders.transport" and rel != TRANSPORT:
                hits.append("direct trading transport import")
            if module == "execution_control.capability" and rel != CONTROLLER:
                if any(a.name == "_issue" for a in node.names):
                    hits.append("capability issuance outside controller")
            if any(a.name in {"seal_context", "_send"} for a in node.names):
                hits.append("unapproved privileged import")
        elif isinstance(node, ast.Constant) and type(node.value) is str:
            value = node.value
            if re.match(r"/(?:v1|uapi|api/v5)/", value) and value not in PATHS.get(rel, ()):
                hits.append("unapproved endpoint")
            if re.fullmatch(r"[A-Za-z]{4}\d{4}[A-Za-z]", value):
                if rel != "execution_orders/kis.py" or value not in TRS:
                    hits.append("unapproved KIS transaction")
            if value.startswith(("http://", "https://")) and (rel != TRANSPORT or value not in HOSTS):
                hits.append("unapproved host")
            if value in {"CANO", "ACNT_PRDT_CD", "KIS_ACCOUNT", "KIS_ACCOUNT_8", "KIS_ACCOUNT_PD"}:
                if rel != TRANSPORT or value not in {"CANO", "ACNT_PRDT_CD"}:
                    hits.append("account field outside credential boundary")
        elif isinstance(node, ast.Name) and node.id in {"eval", "exec", "__import__"}:
            hits.append("dynamic execution")
        elif isinstance(node, ast.Attribute):
            if node.attr in {"environ", "getenv", "__globals__", "__code__", "__closure__", "f_globals", "f_locals"}:
                hits.append("ambient credentials or runtime introspection")
            if node.attr in {"_ISSUED", "_issue"} and rel != CAPABILITY and rel != CONTROLLER:
                hits.append("capability registry access")
        if isinstance(node, ast.Call):
            name = node.func.id if isinstance(node.func, ast.Name) else node.func.attr if isinstance(node.func, ast.Attribute) else ""
            regex_compile = (name == "compile" and isinstance(node.func, ast.Attribute)
                             and isinstance(node.func.value, ast.Name) and node.func.value.id == "re")
            if (name in FORBIDDEN_CALLS and not regex_compile) or name.startswith(("execv", "spawn")):
                hits.append("forbidden effect")
            if name == "_issue" and rel != CONTROLLER:
                hits.append("capability issuance outside controller")
            if name in HTTP_VERBS and not (rel == TRANSPORT and name == "request"
                                            and isinstance(node.func, ast.Attribute)
                                            and isinstance(node.func.value, ast.Name) and node.func.value.id == "session"):
                hits.append("alternate HTTP path")
            if name in WRITE_METHODS:
                hits.append("unchecked state write")
            if name == "open":
                if rel != STORE or not node.args or not _checked(node.args[0]):
                    hits.append("unchecked file access")
            if name == "mkdir":
                if rel != STORE or not isinstance(node.func, ast.Attribute) or not _checked(node.func.value):
                    hits.append("unchecked directory write")
            if name == "replace" and isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name) and node.func.value.id == "os":
                if rel != STORE or len(node.args) != 2 or not all(_checked(arg) for arg in node.args):
                    hits.append("unchecked atomic replace")
            if name == "append_system_entry":
                if rel != CONTROLLER or not node.args or not isinstance(node.args[0], ast.Constant) or node.args[0].value not in {"system_halt", "system_disarm"}:
                    hits.append("unapproved owner event writer")
    return hits


def test_runtime_sources_obey_control_and_transport_boundaries():
    files = _files()
    assert len(files) >= 10, "control/order scan scope collapsed"
    hits = [(p.relative_to(ROOT).as_posix(), why) for p in files
            for why in _problems(p.relative_to(ROOT).as_posix(), p.read_text(encoding="utf-8"))]
    assert not hits, hits


def test_guard_negative_controls_for_routes_effects_and_credentials():
    ordinary = "execution_control/probe.py"
    snippets = ["import requests\n", "import socket\n", "from execution import keys\n",
                "from execution_orders.transport import _send\n", "from core.compliance.model import seal_context\n",
                "x = os.environ['KEY']\n", "request = __import__('requests')\n",
                "from execution_control.capability import _issue\n", "x._ISSUED = {}\n",
                "compile('x', 'name', 'exec')\n", "other.compile(source)\n",
                "open(path, 'wb')\n", "path.write_text('x')\n", "path.mkdir()\n",
                "os.replace(source, destination)\n", "owner.append_system_entry('session_armed', {}, now)\n",
                "client.post(url)\n", "client.transfer()\n", "session.request('GET', url)\n"]
    for source in snippets:
        assert _problems(ordinary, source), source
    assert not _problems(ordinary, "import re\nVALUE = re.compile('[a-z]+')\n")
    assert not _problems(CONTROLLER, "from functools import wraps\n")
    for rel, source in ((ordinary, "from functools import wraps\n"),
                        (CONTROLLER, "from functools import partial\n"),
                        (CONTROLLER, "from functools import wraps as other\n"),
                        (CONTROLLER, "import functools\n")):
        assert _problems(rel, source), (rel, source)
    for rel, approved in PATHS.items():
        for path in approved:
            assert not _problems(rel, f"PATH = {path!r}\n"), (rel, path)
            assert _problems(ordinary, f"PATH = {path!r}\n"), path
        for bad in ("/v1/withdraws/coin", "/v1/deposits/generate_coin_address", "/api/v5/asset/transfer",
                    "/api/v5/trade/batch-orders", "/uapi/domestic-stock/v1/trading/order-credit"):
            assert _problems(rel, f"PATH = {bad!r}\n"), (rel, bad)
    assert _problems(TRANSPORT, "import requests as r\n")
    assert _problems(TRANSPORT, "URL = 'https://attacker.invalid'\n")


def test_single_http_seam_is_bounded_and_has_no_redirect_or_proxy():
    tree = ast.parse((ROOT / TRANSPORT).read_text(encoding="utf-8"))
    send = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "_send")
    calls = [node for node in ast.walk(send) if isinstance(node, ast.Call)
             and isinstance(node.func, ast.Attribute) and node.func.attr == "request"]
    assert len(calls) == 1
    call = calls[0]
    assert ast.unparse(call.func) == "session.request"
    keywords = {kw.arg: ast.unparse(kw.value) for kw in call.keywords}
    assert keywords == {"headers": "headers", "data": "body or None", "timeout": "timeout",
                        "allow_redirects": "False", "verify": "True"}, keywords
    assert not any(isinstance(node, (ast.For, ast.AsyncFor, ast.While)) for node in ast.walk(send))
    assert any(isinstance(node, ast.Assign) and ast.unparse(node) == "session.trust_env = False"
               for node in ast.walk(send))
    http = [(fn.name, node) for fn in tree.body if isinstance(fn, ast.FunctionDef)
            for node in ast.walk(fn) if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
            and node.func.attr == "request"]
    assert len(http) == 1 and http[0][0] == "_send"


def test_capability_consumed_before_credential_provider_and_single_send():
    tree = ast.parse((ROOT / TRANSPORT).read_text(encoding="utf-8"))
    dispatch = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "dispatch")
    calls = [(node.lineno, node.func.id) for node in ast.walk(dispatch)
             if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)]
    positions = {name: [line for line, called in calls if called == name]
                 for name in ("validate_request", "consume_capability", "credentials", "_send")}
    assert all(len(lines) == 1 for lines in positions.values()), positions
    assert positions["validate_request"][0] < positions["consume_capability"][0] < positions["credentials"][0] < positions["_send"][0], positions
    assert not any(isinstance(node, (ast.For, ast.AsyncFor, ast.While)) for node in ast.walk(dispatch))


def test_exact_legacy_exceptions_still_reject_neighbor_files():
    from tests import acceptance as A, macro_m0_harness as M
    old_a, old_m = A.ROOT, M.ROOT
    root = Path(os.environ["TRADEGEN_HOME"]) / "negative-roots"
    root.mkdir()
    try:
        A.ROOT = M.ROOT = root
        cases = [("execution_orders/kis.py", 'PATH = "/uapi/domestic-stock/v1/trading/order-cash"\n'),
                 ("execution_orders/upbit.py", 'PATH = "/v1/orders"\n'),
                 (TRANSPORT, 'FIELDS = ("CANO", "ACNT_PRDT_CD")\n')]
        for rel, source in cases:
            path = root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(source, encoding="utf-8")
            assert not M._offences(path), (rel, M._offences(path))
            neighbor = path.with_name("unreviewed.py")
            neighbor.write_text(source, encoding="utf-8")
            assert M._offences(neighbor), rel
            for check in (A.test_08_no_broker_order_path, A.test_09_no_account_credentials_requested):
                if "order-cash" in source and check is A.test_08_no_broker_order_path or "CANO" in source and check is A.test_09_no_account_credentials_requested:
                    try:
                        check()
                    except AssertionError:
                        pass
                    else:
                        raise AssertionError("legacy check excluded an unreviewed neighboring file")
            neighbor.unlink()
            path.unlink()
    finally:
        A.ROOT, M.ROOT = old_a, old_m


def test_nested_unimported_execution_code_is_signed_in_lockstep():
    from core.compliance import owner
    from tests.compliance_signer import signer
    root = Path(os.environ["TRADEGEN_HOME"]) / "nested-code"
    for package in PACKAGES:
        target = root / package / "nested" / "unimported.py"
        target.parent.mkdir(parents=True)
        target.write_text("VALUE = 1\n", encoding="utf-8")
    first = owner.code_files(root)
    assert first == signer.code_files(root)
    names = {name for name, _ in first}
    for package in PACKAGES:
        assert package + "/nested/unimported.py" in names
    target.write_text("VALUE = 2\n", encoding="utf-8")
    assert owner.code_files(root) != first
    assert owner.code_files(root) == signer.code_files(root)


def test_runtime_and_acting_graph_include_both_packages():
    from tests import acceptance as A
    from core.ficc import context_log as C
    scanned = {p.relative_to(ROOT).as_posix() for p in A.runtime_py()}
    graph = C.repo_modules(ROOT)
    for path in _files():
        rel = path.relative_to(ROOT).as_posix()
        assert rel in scanned, rel
        module = rel[:-3].replace("/", ".")
        if module.endswith(".__init__"):
            module = module[:-9]
        assert module in graph, module
        assert C.is_acting_module(module + ".probe"), module


def test_control_suite_registration_and_never_live_wrapper():
    from tests import run_all, compliance_guards as CG, control_acceptance as CA, control_fixtures as F
    names = [name for name, _ in run_all.select(run_all.tests(), suite="execution_control")]
    assert any(name.startswith("execution_control/control_guards/") for name in names), names
    for stem in CA.MODULES:
        assert (ROOT / "tests" / (stem + ".py")).is_file(), stem
        assert any(name.startswith("execution_control/" + stem + "/") for name in names), stem
    for name in ("README.md", "tests/run_all.py"):
        assert "execution_control" in CG._suite_names((ROOT / name).read_text(encoding="utf-8"))
    from execution_orders import transport
    try:
        transport._send("POST", "ignored", headers={}, body=b"", timeout=10)
    except F.Refused:
        pass
    else:
        raise AssertionError("unmocked transport escaped wrapper")
    assert F.STRAYS
    F.STRAYS.clear()
    try:
        CA._wrap(lambda: F.STRAYS.append("swallowed"))()
    except AssertionError:
        pass
    else:
        raise AssertionError("swallowed send passed")


_STORE_WORKER = '''
def _process_writer(base, channel):
    os.environ["TRADEGEN_HOME"] = base
    journal = Journal()
    channel.send("ready")
    with journal.transaction() as tx:
        tx.append("reserved", {"client_id": "child"}, now=NOW)
    channel.send("written")
    channel.close()
'''
_STORE_HOME = '''
@contextmanager
def _home():
    prior = os.environ.get("TRADEGEN_HOME")
    with tempfile.TemporaryDirectory(prefix="tradegen_control_") as name:
        os.environ["TRADEGEN_HOME"] = name
        isolation._LINK_SCAN.clear()
        try:
            yield Path(name), Journal()
        finally:
            if prior is None:
                os.environ.pop("TRADEGEN_HOME", None)
            else:
                os.environ["TRADEGEN_HOME"] = prior
            isolation._LINK_SCAN.clear()
'''
_STORE_PROCESS_TEST = '''
def test_processes_share_the_control_lock():
    with _home() as (home, journal):
        context = multiprocessing.get_context("spawn")
        parent, child = context.Pipe()
        process = context.Process(target=_process_writer, args=(str(home), child))
        try:
            with journal.transaction() as tx:
                process.start()
                assert parent.poll(10) and parent.recv() == "ready"
                assert not parent.poll(0.1), "child wrote while parent held the lock"
                tx.append("reserved", {"client_id": "parent"}, now=NOW)
            assert parent.poll(10) and parent.recv() == "written"
            process.join(timeout=10)
            assert process.exitcode == 0
            assert [row["data"]["client_id"] for row in _events(journal)] == ["parent", "child"]
        finally:
            if process.is_alive(): process.terminate(); process.join(timeout=3)
            parent.close(); child.close()
'''


def _test_process_problems(rel, source):
    """One pinned store-lock worker can spawn; it imports no network or key reader.

    Spawn does not inherit the monkeypatch wrapper, so the complete worker and
    its invocation are pinned here rather than exempting a module or package.
    """
    tree, hits = ast.parse(source), []
    expected = {node.name: ast.dump(node, include_attributes=False)
                for text in (_STORE_WORKER, _STORE_HOME, _STORE_PROCESS_TEST) for node in ast.parse(text).body}
    approved = set()
    if rel == "tests/control_store.py":
        found = {name: [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == name]
                 for name in expected}
        if all(len(found[name]) == 1 and ast.dump(found[name][0], include_attributes=False) == value
               for name, value in expected.items()):
            approved = {id(node) for name in expected for node in ast.walk(found[name][0])}
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            modules = [alias.name for alias in node.names] if isinstance(node, ast.Import) else [node.module or ""]
            for module in modules:
                if module.split(".")[0] in {"subprocess", "multiprocessing", "runpy"}:
                    if not (approved and isinstance(node, ast.Import) and len(node.names) == 1
                            and node.names[0].name == "multiprocessing" and node.names[0].asname is None):
                        hits.append("unapproved process import")
                if approved and module not in {"contextlib", "datetime", "decimal", "json", "multiprocessing",
                                                "os", "pathlib", "tempfile", "threading", "core",
                                                "execution_control.store"}:
                    hits.append("unsafe import in spawned store module")
            if approved and isinstance(node, ast.ImportFrom):
                names = {alias.name for alias in node.names}
                if node.module == "core" and names != {"isolation"}:
                    hits.append("unsafe core import in spawned store module")
                if node.module == "execution_control.store" and names != {"Journal", "JournalError", "Transaction"}:
                    hits.append("unsafe store import in spawned store module")
        if isinstance(node, ast.Name) and node.id == "multiprocessing" and id(node) not in approved:
            hits.append("multiprocessing outside pinned store lock test")
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr in {"reload", "system", "popen", "startfile", "fork", "spawn", "execv", "set_executable"}:
                hits.append("process or reload escape")
            if node.func.attr in {"Process", "Pool", "get_context", "get_all_start_methods"} and id(node) not in approved:
                hits.append("unapproved process creation")
        if approved and isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id in {"eval", "exec", "__import__", "compile"}:
                hits.append("dynamic execution in spawned store module")
        if isinstance(node, ast.Attribute):
            if isinstance(node.value, ast.Name) and node.value.id == "sys" and node.attr == "executable":
                hits.append("interpreter escape")
    return hits


def test_control_tests_have_no_process_or_reload_escape():
    paths = sorted((ROOT / "tests").glob("control_*.py")) + sorted((ROOT / "tests").glob("orders_*.py"))
    hits = [(path.name, why) for path in paths for why in
            _test_process_problems(path.relative_to(ROOT).as_posix(), path.read_text(encoding="utf-8"))]
    assert not hits, hits


def test_store_process_exception_is_exact_and_rejects_new_effects():
    source = "import multiprocessing\n" + _STORE_WORKER + _STORE_HOME + _STORE_PROCESS_TEST
    assert not _test_process_problems("tests/control_store.py", source)
    assert _test_process_problems("tests/control_controller.py", source)
    for old, new in (("journal = Journal()", "import requests\n    journal = Journal()"),
                     ('get_context("spawn")', 'get_context("fork")'),
                     ("target=_process_writer", "target=other_worker"),
                     ("args=(str(home), child)", "args=(str(Path.home()), child)")):
        changed = source.replace(old, new)
        assert changed != source and _test_process_problems("tests/control_store.py", changed)
    for extra in ("import subprocess\n", "from multiprocessing import Process\n", "p = context.Process(target=x)\n",
                  "p = multiprocessing.get_context('spawn')\n", "import runpy\n", "x.reload(y)\n",
                  "from execution import keys\n", "from core import config\n", "x = __import__('requests')\n"):
        assert _test_process_problems("tests/control_store.py", source + extra), extra
