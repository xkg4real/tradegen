"""Turn a finished skill run into one sentence saying what went wrong.

The cockpit used to report a failure as `exit code 2`. That is the number
argparse returns when the command line is wrong, but the operator sees only the
number, and the sentence that explains it — "the following arguments are
required: --query" — is the last line of a usage block that has already
scrolled out of a 260-pixel console. Two failures that need completely
different responses (fill in a field / buy a data plan) looked identical.

This module reads the transcript and classifies it. The classification drives
three things: the headline shown next to the status chip, which form fields get
highlighted, and whether the run is even presented as a failure — a screener
that exits non-zero because nothing matched today has not malfunctioned.

Ordering matters. The checks run most-specific first, because a traceback that
mentions a 402 should be reported as a plan limit, not as a generic crash.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional

_MAX_EXCERPT_LINES = 6


class Cause(str, Enum):
    OK = "ok"
    NO_RESULTS = "no_results"          # ran fine, found nothing
    MISSING_ARGS = "missing_args"
    INVALID_ARG = "invalid_arg"
    MISSING_INPUT = "missing_input"    # a path was given but is not there
    MISSING_KEY = "missing_key"
    PLAN_LIMIT = "plan_limit"
    RATE_LIMIT = "rate_limit"
    NETWORK = "network"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"
    CRASH = "crash"
    UNKNOWN = "unknown"


# How each cause is acted on. Shown under the headline so the next step is
# never left to inference.
_REMEDY: dict[Cause, str] = {
    Cause.MISSING_ARGS: "Fill in the highlighted fields, then run again.",
    Cause.INVALID_ARG: "Correct the highlighted field and run again.",
    Cause.MISSING_INPUT: "Point the path field at a file that exists.",
    Cause.MISSING_KEY: "Add the credential in Settings, then run again.",
    Cause.PLAN_LIMIT: "This endpoint is outside the current data plan.",
    Cause.RATE_LIMIT: "Wait for the provider's window to reset, then retry.",
    Cause.NETWORK: "Check connectivity and retry.",
    Cause.TIMEOUT: "Raise NEXTGEN_SKILL_TIMEOUT or narrow the run's scope.",
    Cause.NO_RESULTS: "Nothing matched. Widen the criteria if that is unexpected.",
    Cause.CRASH: "The script raised. The traceback is in the transcript.",
}

_ARGPARSE_REQUIRED = re.compile(
    r"error:\s*(?:the following arguments are required:\s*(?P<list>.+)"
    r"|(?P<one>-{1,2}[\w-]+)\s+is required"
    r"|one of the arguments\s+(?P<any>.+?)\s+is required)",
    re.IGNORECASE)
_ARGPARSE_INVALID = re.compile(
    r"error:\s*(?P<msg>(?:argument\s+|unrecognized arguments|invalid\s).+)",
    re.IGNORECASE)
_ARGPARSE_ANY = re.compile(r"^[\w./\\-]+\.py:\s*error:\s*(?P<msg>.+)$",
                           re.MULTILINE)
_FLAG = re.compile(r"-{1,2}[A-Za-z][\w-]*")
_TRACEBACK_LAST = re.compile(r"^(?P<exc>[A-Za-z_][\w.]*Error|[A-Za-z_][\w.]*Exception)"
                             r":\s*(?P<msg>.*)$")
_MISSING_KEY = re.compile(
    r"(api[_ ]?key\s+(?:is\s+)?(?:required|missing|not set)"
    r"|missing\s+(?:the\s+)?[A-Z_]*API_KEY"
    r"|set\s+[A-Z][A-Z0-9_]*_API_KEY"
    r"|no\s+[A-Z][A-Z0-9_]*_API_KEY)", re.IGNORECASE)
_NO_RESULTS = re.compile(
    r"(\bno [a-z]+s? (?:found|matching|to (?:report|process|analyse|analyze))"
    r"|\bno (?:candidates|results|stocks|matches|rows|symbols|pairs|events)\b"
    r"|\bfound 0 |\b0 candidates\b|\bnothing to report\b"
    r"|\bfound 0 qualified\b)", re.IGNORECASE)
_NETWORK = re.compile(
    r"(ConnectionError|ReadTimeout|ConnectTimeout|Max retries exceeded"
    r"|Temporary failure in name resolution|getaddrinfo failed"
    r"|SSLError|Connection aborted)", re.IGNORECASE)
_LEGACY_ENDPOINT = re.compile(r"legacy endpoint", re.IGNORECASE)
# `with open(output_file, "w", …)` in a traceback frame: the path that went
# missing is one the script was writing, not one the operator supplied.
_WRITE_OPEN = re.compile(r"""open\([^)]*,\s*["']w""")

# Scripts that validate their own inputs rather than letting argparse do it.
# They exit 1, not 2, and phrase the complaint themselves — nine of them in the
# repository, each differently:
#
#   [ERROR] --tickets-dir or --from-ohlcv required for concepts stage
#   Error: At least one of --filters, --themes, or --subthemes is required.
#   ERROR: No symbols to process. Use --fmp-universe, --symbols, ...
#
# Recognising these matters more than it looks: without it they land in the
# same "exit code 1" bucket as a genuine crash, which is exactly the confusion
# this module exists to remove. The line must both read as a complaint and name
# at least one flag, so ordinary prose that happens to contain a word like
# "required" is not mistaken for one.
_DEMAND_WORDS = re.compile(
    r"\b(?:is required|are required|required|at least one of|provide|specify"
    r"|supply|must pass|use one of|expected one of|use\b)", re.IGNORECASE)
_COMPLAINT = re.compile(r"^\s*(?:\[?(?:error|fatal|usage)\]?\b|.+:\s*error:)",
                        re.IGNORECASE)

# Lines the runner itself writes into the transcript; never the script's words.
_RUNNER_NOISE = re.compile(r"^(?:\$ |# cwd=)")

# A CLI that prints its own usage block and exits non-zero is saying the call
# was wrong, even when it never uses the word "error" (two scripts hand-roll
# their dispatch and do exactly this).
_USAGE_BLOCK = re.compile(r"^\s*usage:\s", re.IGNORECASE | re.MULTILINE)


@dataclass(frozen=True)
class Diagnosis:
    cause: Cause
    headline: str                       # one line, always populated
    detail: str = ""                    # the remedy, when there is one
    fields: tuple[str, ...] = ()        # flags to highlight in the form
    excerpt: tuple[str, ...] = ()       # the lines the verdict came from

    @property
    def actionable(self) -> bool:
        """True when the operator can fix this from the run panel."""
        return self.cause in (Cause.MISSING_ARGS, Cause.INVALID_ARG,
                              Cause.MISSING_INPUT)

    @property
    def benign(self) -> bool:
        """Ran correctly; the result is simply empty."""
        return self.cause in (Cause.OK, Cause.NO_RESULTS)


def _lines(text: str) -> list[str]:
    """Transcript lines, minus the header the runner prepends.

    Without this the "last output" of a script that printed nothing is the
    runner's own `# cwd=...` line, which reads as though the script said it.
    """
    return [ln.rstrip() for ln in (text or "").splitlines()
            if ln.strip() and not _RUNNER_NOISE.match(ln)]


def _self_reported_demand(lines: list[str]) -> Optional[tuple[str, tuple[str, ...]]]:
    """A script's own complaint that a required input was not supplied."""
    for line in reversed(lines[-40:]):
        if not _COMPLAINT.match(line) or not _DEMAND_WORDS.search(line):
            continue
        flags = _flags_in(line)
        if flags:
            return line.strip(), flags
    return None


def _tail(lines: list[str], count: int = _MAX_EXCERPT_LINES) -> tuple[str, ...]:
    return tuple(lines[-count:])


def _flags_in(text: str) -> tuple[str, ...]:
    return tuple(dict.fromkeys(_FLAG.findall(text or "")))


def _last_exception(lines: list[str]) -> Optional[tuple[str, str]]:
    for line in reversed(lines):
        match = _TRACEBACK_LAST.match(line.strip())
        if match:
            return match.group("exc"), match.group("msg").strip()
    return None


def diagnose(*, status: str, exit_code: Optional[int], stdout: str,
             error: str = "") -> Diagnosis:
    """Classify one finished run. Never raises; falls back to UNKNOWN."""
    lines = _lines(stdout)
    blob = "\n".join(lines)

    if status == "cancelled":
        return Diagnosis(Cause.CANCELLED, "Stopped by the operator.")
    if status == "timeout":
        return Diagnosis(Cause.TIMEOUT, error or "The script exceeded its timeout.",
                         _REMEDY[Cause.TIMEOUT], excerpt=_tail(lines))
    if status == "error":
        return Diagnosis(Cause.CRASH, error or "The script could not be started.",
                         excerpt=_tail(lines))

    # -- argparse rejected the command line ---------------------------------
    # Exit 2 is argparse's own code; check the text too, since a few scripts
    # call parser.error() after their own validation.
    required = _ARGPARSE_REQUIRED.search(blob)
    if required and (exit_code == 2 or "error:" in blob):
        raw = (required.group("list") or required.group("one")
               or required.group("any") or "").strip()
        flags = _flags_in(raw)
        shown = ", ".join(flags) if flags else raw
        joiner = "one of " if required.group("any") else ""
        return Diagnosis(
            Cause.MISSING_ARGS,
            f"Missing required {joiner}argument{'s' if len(flags) > 1 else ''}: {shown}",
            _REMEDY[Cause.MISSING_ARGS], fields=flags,
            excerpt=tuple(ln for ln in lines if "error:" in ln)[-2:])

    if exit_code == 2:
        invalid = _ARGPARSE_INVALID.search(blob) or _ARGPARSE_ANY.search(blob)
        if invalid:
            message = invalid.group("msg").strip()
            return Diagnosis(
                Cause.INVALID_ARG, f"The command line was rejected: {message}",
                _REMEDY[Cause.INVALID_ARG], fields=_flags_in(message),
                excerpt=tuple(ln for ln in lines if "error:" in ln)[-2:])
        # Exit 2 with no readable message is still argparse; say so plainly
        # rather than showing the bare number.
        return Diagnosis(
            Cause.MISSING_ARGS,
            "The script rejected its command line (exit 2).",
            "Open Show --help to see what it expects.", excerpt=_tail(lines))

    # -- a clean exit is not a failure, whatever the transcript contains ----
    #
    # Every classifier below scans the whole transcript, which reads a run's
    # narration as if it were its verdict. `market-breadth-analyzer` prints
    # "6-Component Health Scoring (No API Key Required)" in its banner, scores
    # all six components, writes both reports and exits 0 — and was reported as
    # "A credential is missing: API Key Required". A step that succeeded has to
    # be allowed to say so before anything goes looking for reasons it did not.
    if exit_code == 0 or (exit_code is None and status == "ok"):
        if _NO_RESULTS.search(blob):
            line = next((ln for ln in reversed(lines) if _NO_RESULTS.search(ln)), "")
            return Diagnosis(Cause.NO_RESULTS, line[:200] or "The run matched nothing.",
                             _REMEDY[Cause.NO_RESULTS], excerpt=(line,))
        return Diagnosis(Cause.OK, "Completed.")

    # -- the traceback the run actually died on ------------------------------
    #
    # Provider complaints appear mid-transcript and are often survived: the
    # market-top detector logs four 403s, recovers from all of them, completes
    # its six components, and then dies writing its report into a directory
    # that does not exist. Reading the 403 as the cause names something the run
    # got past. An exception that is not itself about the provider is the more
    # honest answer, so it is checked first.
    fatal = _last_exception(lines)
    if fatal and not re.search(r"40[23]|429|rate limit|legacy endpoint",
                               fatal[1], re.IGNORECASE):
        if fatal[0] in ("FileNotFoundError", "NotADirectoryError",
                        "IsADirectoryError"):
            # A missing path the script was *writing* is not something the
            # operator can point at a file: it is the skill failing to create
            # its own output directory. Telling them to fix a path field they
            # do not have would send them looking for a form that isn't there.
            writing = _WRITE_OPEN.search("\n".join(_tail(lines, 12)))
            if writing:
                return Diagnosis(
                    Cause.CRASH,
                    f"The script could not write its report: {fatal[1]}",
                    "It is writing into a directory it never creates. That is a "
                    "defect in the skill, not in this run.",
                    excerpt=_tail(lines, 4))
            return Diagnosis(Cause.MISSING_INPUT,
                             f"A path the script needed does not exist: {fatal[1]}",
                             _REMEDY[Cause.MISSING_INPUT], excerpt=_tail(lines, 4))
        return Diagnosis(Cause.CRASH, f"{fatal[0]}: {fatal[1]}"[:220],
                         _REMEDY[Cause.CRASH], excerpt=_tail(lines, 5))

    # -- provider and credential problems -----------------------------------
    if "402" in blob or "payment required" in blob.lower():
        line = next((ln for ln in lines if "402" in ln), "")
        return Diagnosis(Cause.PLAN_LIMIT,
                         "The data provider refused: the plan does not cover this "
                         "endpoint (HTTP 402).",
                         _REMEDY[Cause.PLAN_LIMIT],
                         excerpt=(line,) if line else _tail(lines))
    if "429" in blob or "rate limit" in blob.lower():
        return Diagnosis(Cause.RATE_LIMIT, "The data provider rate-limited the run "
                                           "(HTTP 429).",
                         _REMEDY[Cause.RATE_LIMIT], excerpt=_tail(lines, 3))
    key_hit = _MISSING_KEY.search(blob)
    if key_hit:
        return Diagnosis(Cause.MISSING_KEY,
                         f"A credential is missing: {key_hit.group(0).strip()}",
                         _REMEDY[Cause.MISSING_KEY], excerpt=_tail(lines, 3))
    if _LEGACY_ENDPOINT.search(blob):
        return Diagnosis(Cause.PLAN_LIMIT,
                         "The provider retired this endpoint; the script is calling "
                         "an API version that no longer serves new subscriptions.",
                         "This needs a change in the skill, not in the run.",
                         excerpt=_tail(lines, 3))

    # -- the script validated its own inputs and refused --------------------
    if exit_code not in (0, None):
        demand = _self_reported_demand(lines)
        if demand is not None:
            message, flags = demand
            return Diagnosis(Cause.MISSING_ARGS, message[:200],
                             _REMEDY[Cause.MISSING_ARGS], fields=flags,
                             excerpt=(message,))

        if _USAGE_BLOCK.search(blob):
            return Diagnosis(
                Cause.MISSING_ARGS,
                "The script printed its usage and exited: the call was incomplete.",
                "Open Show --help, or fill in the fields below.",
                excerpt=tuple(ln for ln in lines if _USAGE_BLOCK.match(ln))[:2])

    # -- an input path that is not there ------------------------------------
    exception = _last_exception(lines)
    if exception and exception[0] in ("FileNotFoundError", "NotADirectoryError",
                                      "IsADirectoryError"):
        return Diagnosis(Cause.MISSING_INPUT,
                         f"An input path does not exist: {exception[1]}",
                         _REMEDY[Cause.MISSING_INPUT], excerpt=_tail(lines, 4))
    if re.search(r"\b(?:not found|does not exist|no such file)\b", blob,
                 re.IGNORECASE) and exit_code not in (0, None):
        line = next((ln for ln in reversed(lines)
                     if re.search(r"not found|does not exist|no such file",
                                  ln, re.IGNORECASE)), "")
        return Diagnosis(Cause.MISSING_INPUT, line[:200] or "An input path is missing.",
                         _REMEDY[Cause.MISSING_INPUT], excerpt=(line,))

    if _NETWORK.search(blob):
        return Diagnosis(Cause.NETWORK, "The run could not reach the data provider.",
                         _REMEDY[Cause.NETWORK], excerpt=_tail(lines, 3))

    # -- ran, but produced nothing ------------------------------------------
    if _NO_RESULTS.search(blob):
        line = next((ln for ln in reversed(lines) if _NO_RESULTS.search(ln)), "")
        return Diagnosis(Cause.NO_RESULTS, line[:200] or "The run matched nothing.",
                         _REMEDY[Cause.NO_RESULTS], excerpt=(line,))

    if exit_code == 0:
        return Diagnosis(Cause.OK, "Completed.")

    if exception:
        return Diagnosis(Cause.CRASH, f"{exception[0]}: {exception[1]}"[:220],
                         _REMEDY[Cause.CRASH], excerpt=_tail(lines, 5))

    # Nothing matched. Show the script's own last words rather than the number.
    last = lines[-1][:200] if lines else ""
    return Diagnosis(
        Cause.UNKNOWN,
        f"Exited with code {exit_code}." + (f" Last output: {last}" if last else ""),
        excerpt=_tail(lines, 5))
