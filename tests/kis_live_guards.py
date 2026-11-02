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
                   ("execution", "execution_orders", "execution_control", "tools.signer", "core.compliance.owner")):
                problems.append("account or order import")
        if isinstance(node, ast.Call):
            name = node.func.id if isinstance(node.func, ast.Name) else node.func.attr if isinstance(node.func, ast.Attribute) else ""
            if name in {"arm", "sign_entry", "load_context", "eval", "exec", "__import__", "write_text", "write_bytes"}:
                problems.append("privileged or persistent effect")
    return problems


def test_live_display_has_no_account_order_signing_or_persistent_credential_effects():
    for name in ("data/kis_live.py", "data/kis_live_catalog.py", "ui/kis_live_page.py"):
        assert not _effect_problems((ROOT / name).read_text()), name


def test_live_display_guard_rejects_neighboring_privileged_paths():
    for source in ("from execution_orders import transport", "import execution.kis_inquiry",
                   "from tools.signer import sign", "owner.load_context(now)",
                   "target.write_text(token)", "controller.arm(session)", "eval(payload)"):
        assert _effect_problems(source), source


def test_live_suite_is_registered_complete_and_import_failure_is_a_failed_case():
    from tests import kis_live_acceptance, run_all
    from tests.compliance_guards import _suite_names
    rows = run_all.select(run_all.tests(), suite="kis_live")
    names = [name for name, _ in rows]
    for stem in kis_live_acceptance.MODULES:
        assert any(name.startswith("kis_live/" + stem + "/test_") for name in names), stem
    for name in ("README.md", "tests/run_all.py"):
        assert "kis_live" in _suite_names((ROOT / name).read_text())
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
