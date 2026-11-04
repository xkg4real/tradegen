"""Market display stays outside order/account effects and inside keyless testing."""
import ast
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def _effect_problems(source):
    problems = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names = [a.name for a in node.names] if isinstance(node, ast.Import) else [node.module or ""]
            if any(name == prefix or name.startswith(prefix + ".") for name in names for prefix in
                   ("execution", "execution_orders", "execution_control", "execution_accounts", "execution_launch",
                    "execution_network", "tools.signer", "core.compliance.owner")):
                problems.append("account or order import")
        if isinstance(node, ast.Call):
            name = node.func.id if isinstance(node.func, ast.Name) else node.func.attr if isinstance(node.func, ast.Attribute) else ""
            if name in {"arm", "sign_entry", "load_context", "eval", "exec", "__import__", "write_text", "write_bytes"}:
                problems.append("privileged or persistent effect")
    return problems


def test_live_display_has_no_account_order_signing_or_persistent_credential_effects():
    for name in ("data/kis_live.py", "data/kis_live_catalog.py", "ui/kis_live_page.py"):
        assert not _effect_problems((ROOT / name).read_text(encoding="utf-8")), name


def test_live_display_guard_rejects_neighboring_privileged_paths():
    for source in ("from execution_orders import transport", "import execution.kis_inquiry",
                   "from tools.signer import sign", "owner.load_context(now)",
                   "target.write_text(token)", "controller.arm(session)", "eval(payload)"):
        assert _effect_problems(source), source


def test_live_display_guard_rejects_account_review_and_launch_imports():
    for source in ("from execution_accounts.provider import ContinuousAccountProvider",
                   "import execution_launch.review_auth", "from execution_network.route import route_options"):
        assert _effect_problems(source) == ["account or order import"], source
    assert not _effect_problems("from data.kis_live_catalog import CHANNELS")


def test_hermetic_guard_allows_only_the_socketpair_loopback_connect():
    """asyncio's self-pipe on Windows is socket.socketpair(), a loopback connect to its own listener; that one
    connect works inside the guard, every ordinary loopback connect and connect_ex still raises, and the allowance
    does not outlive the socketpair call."""
    import asyncio
    import socket
    from tests.macro_acceptance import HermeticViolation, hermetic

    def refused(call):
        try:
            call()
        except HermeticViolation:
            return
        raise AssertionError("a plain loopback connect passed inside the hermetic guard")

    with hermetic():
        left, right = socket.socketpair()
        try:
            left.sendall(b"ping")
            assert right.recv(4) == b"ping"
        finally:
            left.close()
            right.close()
        asyncio.new_event_loop().close()
        listener = socket.socket()
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        try:
            for method in ("connect", "connect_ex"):
                client = socket.socket()
                try:
                    refused(lambda: getattr(client, method)(listener.getsockname()))
                finally:
                    client.close()
        finally:
            listener.close()


def test_live_suite_is_registered_complete_and_import_failure_is_a_failed_case():
    from tests import kis_live_acceptance, run_all
    from tests.compliance_guards import _suite_names
    rows = run_all.select(run_all.tests(), suite="kis_live")
    names = [name for name, _ in rows]
    for stem in kis_live_acceptance.MODULES:
        assert any(name.startswith("kis_live/" + stem + "/test_") for name in names), stem
    for name in ("README.md", "tests/run_all.py"):
        assert "kis_live" in _suite_names((ROOT / name).read_text(encoding="utf-8"))
    with patch.object(kis_live_acceptance, "MODULES", ("deliberately_missing_kis_live",)):
        failed = kis_live_acceptance.tests()
    assert len(failed) == 1 and failed[0][0].endswith("/import")
    try:
        failed[0][1]()
    except ModuleNotFoundError:
        pass
    else:
        raise AssertionError("missing KIS suite was hidden")


def test_swallowed_unfaked_network_attempt_is_not_a_passing_test():
    from tests.kis_live_acceptance import _wrap
    def bad():
        import requests
        try:
            requests.get("https://example.invalid")
        except Exception:
            pass
    try:
        _wrap(bad)()
    except AssertionError as exc:
        assert "unfaked transport" in str(exc)
    else:
        raise AssertionError("swallowed unexpected transport passed")
