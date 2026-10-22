"""Hand a step the files the earlier steps wrote.

`market-regime-daily` step 4 declares `consumes: [market_breadth_report,
uptrend_report, top_risk_report]`, and the script behind it takes `--breadth`,
`--uptrend` and `--top-risk`, each wanting a path to a JSON report. Steps 1 to 3
wrote exactly those three files minutes earlier, into a run directory the
cockpit owns. Making the operator find and paste those paths by hand — while the
program already knows all of them — is how a four-step workflow turns into a
fifteen-minute clerical exercise, and how step 4 ends up reporting "missing
critical inputs" on a run where nothing was actually missing.

This joins three declarations that already exist:

  * the workflow's `consumes` / `produces` lists,
  * the artifact registry's `produced_by_step`,
  * the parameter names read out of the script by `core.skills.params`.

Nothing is inferred about a script's meaning. A parameter is filled only when
its own name shares a distinctive word with an artifact the workflow says this
step consumes, and only when that match is unambiguous — two artifacts fitting
one parameter equally well leaves it blank for the operator to settle. The
filled value is placed in the visible form field, never substituted behind the
form, so what runs is always what the operator can see.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Mapping, Optional

from core.skills.params import Kind, Spec

# Words shared by nearly every artifact id and parameter name, so useless for
# telling one apart from another.
_GENERIC = {
    "report", "reports", "json", "path", "paths", "file", "files", "dir",
    "directory", "output", "input", "inputs", "data", "result", "results",
    "doc", "docs", "out", "src", "analysis", "summary",
}
_SPLIT = re.compile(r"[^0-9a-z]+")

# A path may only be handed to a parameter that asks for a file.
#
# This is narrower than it looks worth being, and the narrowness is the point.
# `market-top-detector` takes `--breadth-200dma-date`, which shares the word
# "breadth" with `market_breadth_report` and wants `YYYY-MM-DD`; an earlier
# version of this module put a JSON path into it, and into its sibling, on a
# real run. Free text is where a script asks for anything at all, so it is
# exactly where a guess is least safe. `core.skills.params` already recognises
# a file parameter from the script's own declaration — that judgement is
# trusted here rather than second-guessed.
_ACCEPTS_PATH = (Kind.FILE,)


def _tokens(text: str) -> set[str]:
    parts = _SPLIT.split((text or "").lower())
    return {p for p in parts if len(p) > 1 and p not in _GENERIC}


def _score(param_name: str, artifact_id: str) -> int:
    return len(_tokens(param_name) & _tokens(artifact_id))


def match(spec: Spec, produced: Mapping[str, Path], *,
          consumes: tuple[str, ...] = (),
          subcommand: Optional[str] = None) -> dict[str, str]:
    """Map parameter dest -> file path, for parameters this step can be given.

    `produced` is artifact id -> path, gathered from the steps already run.
    `consumes` narrows the candidates to what the workflow says this step reads;
    an empty tuple means consider everything produced so far.
    """
    if not produced:
        return {}
    wanted = {a: p for a, p in produced.items()
              if not consumes or a in consumes}
    if not wanted:
        return {}

    filled: dict[str, str] = {}
    for param in spec.for_subcommand(subcommand):
        if param.kind not in _ACCEPTS_PATH or not param.flags:
            continue
        name = param.dest or param.flags[0]
        ranked = sorted(((_score(name, artifact), artifact)
                         for artifact in wanted),
                        key=lambda pair: pair[0], reverse=True)
        if not ranked or ranked[0][0] == 0:
            continue
        # Two artifacts fitting equally well is not a match, it is a question.
        if len(ranked) > 1 and ranked[1][0] == ranked[0][0]:
            continue
        filled[param.dest] = str(wanted[ranked[0][1]])
    return filled


def produced_by(step_produces: tuple[str, ...],
                artifacts: tuple[Path, ...]) -> dict[str, Path]:
    """Name the files a finished step produced, using the ids it declares.

    One declared artifact and one JSON file written is the common case and is
    unambiguous. When a step declares several artifacts, each is matched to the
    file whose name shares the most words with it; anything left unmatched is
    dropped rather than guessed at.
    """
    files = [Path(p) for p in artifacts
             if Path(p).suffix.lower() == ".json"
             and "history" not in Path(p).name.lower()
             and Path(p).name.lower() != "run.json"]
    if not files or not step_produces:
        return {}
    if len(step_produces) == 1 and len(files) == 1:
        return {step_produces[0]: files[0]}

    found: dict[str, Path] = {}
    taken: set[Path] = set()
    for artifact in step_produces:
        ranked = sorted(((_score(artifact, f.stem), f) for f in files
                         if f not in taken),
                        key=lambda pair: pair[0], reverse=True)
        if not ranked or ranked[0][0] == 0:
            continue
        if len(ranked) > 1 and ranked[1][0] == ranked[0][0]:
            continue
        found[artifact] = ranked[0][1]
        taken.add(ranked[0][1])
    return found
