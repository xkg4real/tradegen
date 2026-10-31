"""Research isolation and pre-outcome protocol integrity checks."""
import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def forbidden_imports(source):
    modules = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            modules.extend(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and not node.level:
            modules.append(node.module or "")
    banned = ("requests", "socket", "urllib", "http", "execution", "execution_control", "execution_orders",
              "execution_accounts", "core.compliance", "tools.signer", "grokteam", "paper_live")
    return [m for m in modules if any(m == b or m.startswith(b + ".") for b in banned)]


def test_research_has_no_live_account_network_or_protected_holdout_imports():
    for path in (ROOT / "research_lab").glob("*.py"):
        assert not forbidden_imports(path.read_text()), path.name
    for module in ("requests", "execution_orders.transport", "core.compliance.owner", "grokteam.book", "paper_live.replay"):
        assert forbidden_imports("import " + module)


def test_research_protocol_manifest_and_catalogue_are_bound():
    from research_lab.candidates import catalogue, catalogue_bytes, raw_rules
    protocol = json.loads((ROOT / "research_lab/protocol.json").read_text())
    raw = (ROOT / "research_lab/data_manifest.json").read_bytes()
    assert protocol["data_manifest_sha256"] == hashlib.sha256(raw).hexdigest()
    assert len(raw_rules()) == protocol["raw_rules_per_asset"] == 223
    assert len(catalogue()) == protocol["configurations_per_asset"] == 2676
    assert len(protocol["assets"]) * len(catalogue()) == protocol["total_configurations"] == 21408
    assert (ROOT / "research_lab/catalogue.json").read_bytes() == catalogue_bytes()


def test_research_suite_is_complete_and_registered():
    from tests import research_acceptance, run_all
    from tests.compliance_guards import _suite_names
    names = [n for n, _ in run_all.select(run_all.tests(), suite="strategy_research")]
    for module in research_acceptance.MODULES:
        assert any(n.startswith("strategy_research/" + module + "/test_") for n in names), module
    for name in ("README.md", "tests/run_all.py"):
        assert "strategy_research" in _suite_names((ROOT / name).read_text())
