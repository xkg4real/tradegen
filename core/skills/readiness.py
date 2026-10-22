"""Decide whether a skill can run *right now*, and say precisely why not.

`index.py` says what a skill needs; `config.py` says which credentials exist;
this module joins the two into one verdict per skill. The distinction the UI
cares about is between three very different kinds of "not ready":

  * MISSING_KEY   — a credential is absent. Fixable in Settings.
  * NEEDS_INPUT   — the skill needs something from the operator before it can
                    run: a file its manifest declares (a prices JSON, a chart
                    image, an MT5 report), or a required command-line argument
                    its script declares. Fixable at run time, not in Settings.
  * DOC_ONLY      — the skill ships no CLI at all. Nothing to fix; it is
                    guidance for a human or for Claude, not a program.

Required arguments are part of this verdict, and that is a correction rather
than an embellishment. Readiness used to consider only credentials, so twenty
skills whose scripts reject an empty command line were reported READY; the
operator clicked Run and got exit 2 in a sixth of a second. A skill that cannot
be launched as-is is not ready, whatever the state of its API keys.

Only `required` integrations block. A `recommended` or `optional` integration
that is unsatisfied degrades the run, so it is reported as a warning and the
skill still counts as runnable.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from functools import lru_cache
from pathlib import Path

import config
from core.skills.entrypoints import is_runnable, primary
from core.skills.index import Integration, SkillMeta
from core.skills.params import spec_for

# Every credential env var any integration maps to, for the code scan below.
_ALL_CREDENTIAL_VARS: dict[str, str] = {
    var: integration
    for integration, names in config.SKILL_CREDENTIALS.items()
    for var in names
}


@lru_cache(maxsize=256)
def _credentials_used_in_code(scripts_dir_str: str) -> tuple[str, ...]:
    """Env vars a skill's scripts actually read.

    The index is hand-maintained and drifts: five skills read `FMP_API_KEY`
    without declaring an `fmp` integration, so trusting the manifest alone
    reports them Ready and then they fail at run time with
    "FMP API key required". Readiness has to reflect the code, not the promise.
    """
    scripts = Path(scripts_dir_str)
    if not scripts.is_dir():
        return ()
    found: set[str] = set()
    for path in scripts.rglob("*.py"):
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for var in _ALL_CREDENTIAL_VARS:
            if var in text:
                found.add(var)
    return tuple(sorted(found))


class State(str, Enum):
    READY = "ready"
    MISSING_KEY = "missing_key"
    NEEDS_INPUT = "needs_input"
    DOC_ONLY = "doc_only"


@dataclass(frozen=True)
class Readiness:
    state: State
    missing_credentials: tuple[str, ...] = ()      # env var names
    missing_providers: tuple[str, ...] = ()        # integration ids
    input_integrations: tuple[str, ...] = ()       # integration ids needing a file
    warnings: tuple[str, ...] = ()                 # unsatisfied optional/recommended
    undeclared: tuple[str, ...] = ()               # creds found in code, absent from the index
    required_arguments: tuple[str, ...] = ()       # flags the script will not run without
    arguments_unknown: bool = False                # the CLI could not be read statically

    @property
    def reason(self) -> str:
        """One line for the list row, so the chip is never the only signal."""
        if self.state is State.DOC_ONLY:
            return "reference only — no script to run"
        if self.state is State.MISSING_KEY:
            return "needs " + ", ".join(self.missing_credentials or self.missing_providers)
        if self.state is State.NEEDS_INPUT:
            parts = []
            if self.required_arguments:
                parts.append(", ".join(self.required_arguments))
            if self.input_integrations:
                parts.append(", ".join(self.input_integrations))
            if self.arguments_unknown:
                parts.append("arguments not declared")
            return "needs " + ("; ".join(parts) if parts else "operator input")
        return "ready to run"

    @property
    def runnable(self) -> bool:
        return self.state in (State.READY, State.NEEDS_INPUT)

    @property
    def blocked(self) -> bool:
        return self.state in (State.MISSING_KEY, State.DOC_ONLY)


def _satisfied(integration: Integration) -> tuple[bool, tuple[str, ...]]:
    """(satisfied, missing_env_var_names) for one integration."""
    iid = integration.id
    if iid in config.KEYLESS_INTEGRATIONS:
        return True, ()
    if iid in config.FILE_INPUT_INTEGRATIONS:
        return True, ()          # satisfiable, but only with operator input
    names = config.SKILL_CREDENTIALS.get(iid)
    if not names:
        # Unknown integration id from a newer index revision. Do not invent a
        # blocker for something this build has never heard of.
        return True, ()
    missing = tuple(n for n in names if not config._present(n))
    return (not missing), missing


def evaluate(skill: SkillMeta) -> Readiness:
    if not is_runnable(skill.id, skill.directory):
        return Readiness(state=State.DOC_ONLY)

    missing_creds: list[str] = []
    missing_providers: list[str] = []
    needs_input: list[str] = []
    warnings: list[str] = []

    for integration in skill.integrations:
        ok, missing = _satisfied(integration)
        if integration.id in config.FILE_INPUT_INTEGRATIONS and integration.blocking:
            needs_input.append(integration.id)
            continue
        if ok:
            continue
        if integration.blocking:
            missing_providers.append(integration.id)
            missing_creds.extend(missing)
        else:
            warnings.append(
                f"{integration.id} unavailable ({integration.requirement}) — "
                f"the run will proceed with reduced coverage"
            )

    # Second pass: credentials the scripts read but the index never declared.
    declared_vars = {
        var
        for integration in skill.integrations
        for var in config.SKILL_CREDENTIALS.get(integration.id, ())
    }
    undeclared: list[str] = []
    for var in _credentials_used_in_code(str(skill.directory / "scripts")):
        if var in declared_vars or config._present(var):
            continue
        undeclared.append(var)
        missing_creds.append(var)
        provider = _ALL_CREDENTIAL_VARS.get(var, var)
        if provider not in missing_providers:
            missing_providers.append(provider)

    # Third pass: what the script's own argparse demands. A missing credential
    # still outranks this — no point asking for a symbol when the run cannot
    # authenticate — but a required flag is enough on its own to keep a skill
    # out of READY.
    entry = primary(skill.id, skill.directory)
    spec = spec_for(entry.path) if entry is not None else None
    required_args: tuple[str, ...] = ()
    arguments_unknown = False
    if spec is not None:
        if spec.parsed:
            required_args = spec.missing()
        else:
            # The CLI exists but was assembled in a way static reading cannot
            # follow. Saying READY would be a guess; say so instead.
            arguments_unknown = True

    if missing_providers:
        return Readiness(
            state=State.MISSING_KEY,
            missing_credentials=tuple(dict.fromkeys(missing_creds)),
            missing_providers=tuple(dict.fromkeys(missing_providers)),
            input_integrations=tuple(needs_input),
            warnings=tuple(warnings),
            undeclared=tuple(undeclared),
            required_arguments=required_args,
            arguments_unknown=arguments_unknown,
        )
    if needs_input or required_args or arguments_unknown:
        return Readiness(
            state=State.NEEDS_INPUT,
            input_integrations=tuple(needs_input),
            warnings=tuple(warnings),
            required_arguments=required_args,
            arguments_unknown=arguments_unknown,
        )
    return Readiness(state=State.READY, warnings=tuple(warnings))


def reload() -> None:
    _credentials_used_in_code.cache_clear()


def summarize(skills) -> dict[State, int]:
    counts = {s: 0 for s in State}
    for skill in skills:
        counts[evaluate(skill).state] += 1
    return counts
