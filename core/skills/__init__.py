"""Skill catalog, readiness, execution and history for the NEXTGEN cockpit."""
# `entrypoints` is exported under an alias: binding the function to that name
# here would shadow the submodule of the same name for every later importer.
from core.skills.entrypoints import Entrypoint, is_runnable, primary
from core.skills.entrypoints import entrypoints as skill_entrypoints
from core.skills.index import Integration, SkillMeta, all_skills, by_id, categories
from core.skills.readiness import Readiness, State, evaluate, summarize
from core.skills.runner import RunHandle, RunResult, Status, describe_args, run_skill
from core.skills.runs import RunRecord, latest_for_skill, recent, record
from core.skills.workflows import Step, WorkflowMeta, all_workflows

__all__ = [
    "Entrypoint", "skill_entrypoints", "is_runnable", "primary",
    "Integration", "SkillMeta", "all_skills", "by_id", "categories",
    "Readiness", "State", "evaluate", "summarize",
    "RunHandle", "RunResult", "Status", "describe_args", "run_skill",
    "RunRecord", "latest_for_skill", "recent", "record",
    "Step", "WorkflowMeta", "all_workflows",
]


def reload_all() -> None:
    """Re-read the repository after the operator changes its location."""
    from core.skills import (entrypoints as _ep, index as _idx,
                             readiness as _rd, workflows as _wf)
    _idx.reload()
    _wf.reload()
    _ep.reload()
    _rd.reload()
