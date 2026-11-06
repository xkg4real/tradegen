"""Explicit owner commands remain signed, scanned and isolated from research context."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_owner_commands_are_in_runtime_and_acting_graphs():
    from tests import acceptance
    from core.ficc import context_log
    scanned = {path.relative_to(ROOT).as_posix() for path in acceptance.runtime_py()}
    graph = context_log.repo_modules(ROOT)
    files = tuple((ROOT / "tools" / "owner").rglob("*.py"))
    assert files
    for path in files:
        relative = path.relative_to(ROOT).as_posix()
        assert relative in scanned, relative
        parts = list(path.relative_to(ROOT).with_suffix("").parts)
        if parts[-1] == "__init__":
            parts.pop()
        module = ".".join(parts)
        assert module in graph, module
        assert context_log.is_acting_module(module + ".probe"), module


def test_owner_commands_cannot_turn_narrative_context_into_an_action_input():
    from core.ficc import context_log
    forbidden = {"tools.owner.unreviewed":
                 "from core.ficc.context_log import read_context_log\n"
                 "def prepare():\n    return read_context_log()\n"}
    assert context_log.scan_isolation(forbidden)
    assert not context_log.scan_isolation({"tools.owner.inspection": "VALUE = 1\n"})


def test_owner_and_execution_helpers_cannot_hide_transitive_narrative_imports():
    from core.ficc import context_log
    for helper in ("tools.owner.helper", "execution.helper", "execution_control.helper",
                   "execution_orders.helper", "execution_accounts.helper", "execution_network.helper",
                   "execution_launch.helper"):
        sources = {
            "tools.owner.unreviewed": "import " + helper + "\n",
            helper: "import core.ficc.context_log\n",
        }
        violations = context_log.scan_isolation(sources)
        assert any(row.module == "tools.owner.unreviewed" for row in violations), (helper, violations)
