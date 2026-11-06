"""Prospective single-market study: a frozen candidate family, a scheduled public-orderbook capture and a frozen
selection rule. Offline unless main() is asked to capture.

    python -m execution_launch.study freeze  --profile PROFILE.json --draft DRAFT.json --out NEW_EMPTY_DIR
    python -m execution_launch.study capture --plan PLAN.json --out NEW_EMPTY_DIR
    python -m execution_launch.study select  --plan PLAN.json --profile PROFILE.json --captures DIR --now AWARE_ISO_TIME

Freeze: K moving-average programs over one complete private profile and one template protocol become K registered
ForwardProtocols sharing the window, capital, fees, inference budget and family; the plan binds the installed
capture code (CAPTURE_FILES) and the disclosed negative retrospective result (PRIOR_RESEARCH) by digest and refuses
a plan that cannot pass before any data is seen (p-value resolution, inference work, roundtrip room, fill-delay
margin). plan.json is private (it holds the principal); commitment.json carries digests, the window, the programs
and the registry rows only, so the owner can publish it before capture_start. Capture: one PaperCapture per
candidate is fed the same prefetched book at every slot of the frozen grid through an injected clock, book source,
waiter and record sink; the first refusal, stop or missed slot ends the trial for every candidate and nothing is
backfilled, re-slotted or relabelled. Selection: every family member is assessed through strategy.assess_strategy
against the current profile's variant and ranked by the protocol's frozen order (simultaneous block-bootstrap
Sharpe lower bound, worst stress drawdown, turnover, lexical identifier); no qualified row is NO_QUALIFIED_MARKET
and nothing here is ever execution_ready. Trimmed per ruling R9: no signal handler and no threads (Ctrl+C reaches
the waiter, which answers False, and the trial ends as STUDY_CAPTURE_STOPPED).

Only main() reads a wall clock or constructs the E1 public quote source. Nothing here signs, arms, places an
order, reads a credential or looks up a home directory; the only writes are new exclusive files inside an explicit
empty local output directory (the writer is pinned in tests/launch_guards.py). Every refusal is one fixed code.
"""
from __future__ import annotations

import base64
from collections.abc import Mapping
from dataclasses import dataclass, fields, replace
from datetime import datetime, timedelta, timezone
from fractions import Fraction
import hashlib
import json
import math
import ntpath
import os
from pathlib import Path
import random
import stat
import sys
import time
from typing import Callable

from core.isolation import checked_target
from execution_launch.paper_capture import CaptureArchive, PaperCapture, _bindings, _clock_value, capture_json
from execution_launch.private_input import _REFUSED_ATTRIBUTES
from execution_launch.profile import (LaunchProfile, ProfileError, parse_profile_json, preflight_profile,
                                      profile_contract_digest, rule_terms_digest)
from execution_launch.program import ProgramSpec, parameters_json, parse_program, program_digest
from execution_launch.review_request import build_review_request, build_family_commitment, bind_review_family
from execution_launch.strategy import (ForwardProtocol, Registration, StrategyEvidenceError, ValidationResult,
                                       _HASH, _ID, _date, _instant, _json, _object, _plain, assess_strategy,
                                       evaluate_capture_json, evidence_digest, parse_protocol, register_protocol)
from execution_launch.workflow import (MAX_CAPTURE_BYTES, MAX_CONFIG_BYTES, WorkflowError, _CODE, _PRIVATE,
                                       _base, _bound_profile, _read_file, _time)

SELECTION_RULE = "upbit-krw-single-asset-v1"
CAPTURE_FILES = ("execution_launch/study.py", "execution_launch/paper_capture.py", "execution_launch/program.py",
                 "execution_launch/strategy.py", "execution_accounts/quotes.py", "execution/transport.py",
                 "execution/upbit_inquiry.py")
PRIOR_RESEARCH = "docs/research/2026-10-31-strategy-lab/results/summary.json"
PROGRAM_SOURCE = "execution_launch/program.py"
# ponytail: calibration knob. The book is read this long before each slot and must arrive by the slot; it is
# bound by the manifest of this file, so changing it is a new study.
_PREFETCH_LEAD = timedelta(seconds=5)
_START_MARGIN = timedelta(seconds=60)
_SAMPLING_MARGIN = 10                      # seconds: the quote source's freshness bound
_WORK_LIMIT = 10_000_000                   # equals the evaluator's inference budget (strategy.run_paper_validation)
_MAX_PLAN_BYTES = 262144
_MAX_SOURCE_BYTES = 1048576
_PER_CANDIDATE = frozenset({"study_id", "strategy_id", "strategy_code_sha256", "profile_contract_digest",
                            "family_members"})
_COMMANDS = {"freeze": ("profile", "draft", "out"), "capture": ("plan", "out"),
             "select": ("plan", "profile", "captures", "now")}
_ROOT = Path(__file__).resolve().parent.parent
_FLAGS = getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NOINHERIT", 0)


class StudyError(ValueError):
    """Fixed STUDY_* codes only; never a path, amount, account scope or provider text."""


def _require(condition, code):
    if not condition:
        raise StudyError(code)


@dataclass(frozen=True, kw_only=True)
class StudyCandidate:
    program: ProgramSpec
    protocol: ForwardProtocol


@dataclass(frozen=True, kw_only=True)
class StudyPlan:
    schema_version: int
    plan_id: str
    selection_rule: str
    asset: str
    risk_group: str
    prior_research_sha256: str
    candidates: tuple[StudyCandidate, ...]
    registry: tuple[Registration, ...]


@dataclass(frozen=True, kw_only=True)
class CaptureOutcome:
    plan_digest: str
    complete: bool
    reason: str | None
    slots_recorded: int
    archives: tuple[CaptureArchive, ...]


@dataclass(frozen=True, kw_only=True)
class CandidateRow:
    study_id: str
    strategy_id: str
    status: str                          # QUALIFIED, EXCLUDED or MISSING
    reasons: tuple[str, ...]
    math_qualified: bool
    evidence_digest: str | None
    evaluated_at: datetime | None
    sharpe: float | None                 # mean(net) / sample sd(net); cash return 0; unannualized
    sharpe_lower: float | None           # simultaneous (alpha / K) block-bootstrap lower bound
    worst_drawdown: float | None         # over the primary, double-cost and extra-delay runs
    turnover_ratio: float | None         # primary turnover over the initial cash, no absolute amount


@dataclass(frozen=True, kw_only=True)
class MarketSelection:
    plan_digest: str
    status: str                          # SELECTED or NO_QUALIFIED_MARKET
    symbol: str
    selected_study_id: str | None
    selected_strategy_id: str | None
    qualified_assets: int
    qualified_risk_groups: int
    rows: tuple[CandidateRow, ...]
    reasons: tuple[str, ...]
    execution_ready: bool = False


# -- fixed files ----------------------------------------------------------------------------------------------

def _fixed_file(relative):
    """Bounded read of one fixed repository path (the fixed driver's idiom): no link, a regular file, at most 1 MiB."""
    path = _ROOT / relative
    try:
        _require(not path.is_symlink() and path.is_file() and 0 < path.stat().st_size <= _MAX_SOURCE_BYTES,
                 "STUDY_SOURCE_FILE_INVALID")
        with path.open("rb") as stream:
            body = stream.read(_MAX_SOURCE_BYTES + 1)
    except OSError:
        raise StudyError("STUDY_SOURCE_FILE_INVALID") from None
    _require(0 < len(body) <= _MAX_SOURCE_BYTES, "STUDY_SOURCE_FILE_INVALID")
    return body


def capture_source_artifact() -> bytes:
    """Canonical ASCII manifest of the installed capture code; protocol.capture_source_code_sha256 is its digest."""
    files = {name: hashlib.sha256(_fixed_file(name)).hexdigest() for name in CAPTURE_FILES}
    return json.dumps({"kind": "tradegen-study-capture/1", "files": files}, sort_keys=True,
                      separators=(",", ":"), ensure_ascii=True).encode("ascii")


# -- plan -----------------------------------------------------------------------------------------------------

def _structure(plan):
    _require(type(plan) is StudyPlan and type(plan.schema_version) is int and plan.schema_version == 1
             and plan.selection_rule == SELECTION_RULE and type(plan.candidates) is tuple and plan.candidates
             and type(plan.registry) is tuple
             and all(type(c) is StudyCandidate and type(c.program) is ProgramSpec
                     and type(c.protocol) is ForwardProtocol for c in plan.candidates),
             "STUDY_PLAN_SCHEMA_INVALID")
    for value in (plan.plan_id, plan.asset, plan.risk_group):
        _require(type(value) is str and _ID.fullmatch(value) is not None, "STUDY_PLAN_SCHEMA_INVALID")
    _require(type(plan.prior_research_sha256) is str and _HASH.fullmatch(plan.prior_research_sha256) is not None,
             "STUDY_PLAN_SCHEMA_INVALID")
    ids = tuple(c.program.strategy_id for c in plan.candidates)
    _require(ids == tuple(sorted(set(ids)))
             and all(c.protocol.strategy_id == c.program.strategy_id for c in plan.candidates),
             "STUDY_PLAN_SCHEMA_INVALID")
    # The archive <study_id>.capture.json must be a legal file name on Windows (no stream colon, no DOS device
    # such as CON.<id>) or the writer would refuse it only after the window; ntpath is pure, so a plan frozen
    # anywhere is refused here, before any data is seen.
    _require(all(type(c.protocol.study_id) is str and ":" not in c.protocol.study_id
                 and not ntpath.isreserved(c.protocol.study_id + ".capture.json") for c in plan.candidates),
             "STUDY_PLAN_SCHEMA_INVALID")
    _require(all(c.program.kind != "cash" for c in plan.candidates), "STUDY_CASH_MEMBER_CANNOT_QUALIFY")
    return ids


def _feasible(protocol, candidates):
    """Refusals only: a plan that the frozen evaluator could never pass does not deserve a week and a family slot."""
    family = len(protocol.family_members)
    _require(Fraction(family, protocol.bootstrap_replications + 1) <= Fraction(protocol.alpha),
             "STUDY_PVALUE_RESOLUTION_INFEASIBLE")
    returns = (protocol.capture_end - protocol.capture_start) // timedelta(seconds=protocol.bar_seconds)
    _require(protocol.bootstrap_replications * (returns // protocol.block_length + 1) <= _WORK_LIMIT,
             "STUDY_INFERENCE_WORK_LIMIT")
    _require(all((returns - c.program.slow_window + 1) // 2 >= protocol.minimum_roundtrips for c in candidates),
             "STUDY_ROUNDTRIPS_INFEASIBLE")
    _require(protocol.minimum_fill_delay_seconds + _SAMPLING_MARGIN <= protocol.bar_seconds,
             "STUDY_FILL_DELAY_INFEASIBLE")


def validate_study_plan(plan: StudyPlan) -> str:
    """Return evidence_digest(plan) or raise, in a fixed order: structure, common terms, family, capture source and
    prior research, paper_capture's bindings per candidate, feasibility."""
    ids = _structure(plan)
    protocols = [c.protocol for c in plan.candidates]
    common = [{k: v for k, v in _plain(p).items() if k not in _PER_CANDIDATE} for p in protocols]
    _require(all(terms == common[0] for terms in common), "STUDY_TERMS_NOT_COMMON")
    _require(all(p.family_members == ids for p in protocols), "STUDY_FAMILY_INCOMPLETE")
    source = capture_source_artifact()
    _require(protocols[0].capture_source_code_sha256 == hashlib.sha256(source).hexdigest(),
             "STUDY_CAPTURE_SOURCE_CHANGED")
    _require(plan.prior_research_sha256 == hashlib.sha256(_fixed_file(PRIOR_RESEARCH)).hexdigest(),
             "STUDY_PRIOR_RESEARCH_MISMATCH")
    artifact = _fixed_file(PROGRAM_SOURCE)
    for candidate in plan.candidates:
        _bindings(candidate.protocol, plan.registry, candidate.program, artifact, source)
    _feasible(protocols[0], plan.candidates)
    return evidence_digest(plan)


def build_study_plan(profile: LaunchProfile, programs: tuple[ProgramSpec, ...], *, template: ForwardProtocol,
                     plan_id: str, asset: str, risk_group: str,
                     registry: tuple[Registration, ...] = ()) -> StudyPlan:
    """Freeze K candidates from one complete private profile and one template protocol.

    Each program gets the profile variant carrying its identifier and installed-code digest, and a protocol whose
    study id, strategy fields, profile contract, rule terms, capture source, capital, fee and family are derived
    from the profile and the installed code; the template's other terms are common to every candidate.
    """
    _require(type(profile) is LaunchProfile and type(programs) is tuple and len(programs) > 0
             and all(type(p) is ProgramSpec for p in programs) and type(template) is ForwardProtocol
             and type(registry) is tuple, "STUDY_PLAN_SCHEMA_INVALID")
    _require(profile.instrument_rules is not None and profile.policy.initial_equity is not None,
             "STUDY_PROFILE_INCOMPLETE")
    programs = tuple(sorted(programs, key=lambda p: p.strategy_id))
    ids = tuple(p.strategy_id for p in programs)
    _require(len(set(ids)) == len(ids), "STUDY_PLAN_SCHEMA_INVALID")
    artifact, source = _fixed_file(PROGRAM_SOURCE), capture_source_artifact()
    terms, candidates = rule_terms_digest(profile.instrument_rules), []
    for program in programs:
        code = program_digest(program, artifact)
        variant = replace(profile, strategy_id=program.strategy_id, strategy_code_sha256=code)
        _require(preflight_profile(variant, now=template.preregistered_at).profile_complete,
                 "STUDY_PROFILE_INCOMPLETE")
        protocol = replace(template, study_id=template.study_id + "." + program.strategy_id,
                           strategy_id=program.strategy_id, strategy_code_sha256=code,
                           profile_contract_digest=profile_contract_digest(variant), rule_terms_digest=terms,
                           capture_source_code_sha256=hashlib.sha256(source).hexdigest(),
                           initial_cash_quote=profile.policy.initial_equity,
                           fee_fraction=profile.instrument_rules.fee_fraction, family_members=ids)
        _bound_profile(variant, protocol)
        registry = register_protocol(protocol, registry)
        candidates.append(StudyCandidate(program=program, protocol=protocol))
    plan = StudyPlan(schema_version=1, plan_id=plan_id, selection_rule=SELECTION_RULE, asset=asset,
                     risk_group=risk_group,
                     prior_research_sha256=hashlib.sha256(_fixed_file(PRIOR_RESEARCH)).hexdigest(),
                     candidates=tuple(candidates), registry=registry)
    validate_study_plan(plan)
    return plan


def study_plan_json(plan: StudyPlan) -> str:
    """The private plan: it holds every protocol body, so the principal."""
    validate_study_plan(plan)
    return json.dumps(_plain(plan), sort_keys=True, indent=2) + "\n"


def parse_study_plan(raw: str | bytes) -> StudyPlan:
    body = _json(raw, _MAX_PLAN_BYTES)
    _require(type(body) is dict and set(body) == {f.name for f in fields(StudyPlan)}
             and type(body["candidates"]) is list and type(body["registry"]) is list, "STUDY_PLAN_SCHEMA_INVALID")
    candidates = []
    for item in body["candidates"]:
        _require(type(item) is dict and set(item) == {"program", "protocol"}, "STUDY_PLAN_SCHEMA_INVALID")
        candidates.append(StudyCandidate(program=parse_program(json.dumps(item["program"])),
                                         protocol=parse_protocol(json.dumps(item["protocol"]))))
    registry = []
    for item in body["registry"]:
        row = _object(item, Registration)
        row["registered_at"] = _date(row["registered_at"])
        registry.append(Registration(**row))
    plan = StudyPlan(**{name: body[name] for name in ("schema_version", "plan_id", "selection_rule", "asset",
                                                      "risk_group", "prior_research_sha256")},
                     candidates=tuple(candidates), registry=tuple(registry))
    validate_study_plan(plan)
    return plan


def commitment_json(plan: StudyPlan) -> str:
    """The publishable record: digests, the window, the programs and the registry rows. Never a protocol body, the
    principal, an account scope or a profile contract digest."""
    sha = validate_study_plan(plan)
    protocol = plan.candidates[0].protocol
    body = {"kind": "tradegen-study-commitment/1", "plan_id": plan.plan_id, "plan_sha256": sha,
            "selection_rule": plan.selection_rule, "asset": plan.asset, "risk_group": plan.risk_group,
            "prior_research_sha256": plan.prior_research_sha256,
            "capture_source_code_sha256": protocol.capture_source_code_sha256,
            "capture_source_manifest": json.loads(capture_source_artifact()),
            "window": {"preregistered_at": _plain(protocol.preregistered_at),
                       "capture_start": _plain(protocol.capture_start), "capture_end": _plain(protocol.capture_end),
                       "bar_seconds": protocol.bar_seconds},
            "candidates": [{"study_id": c.protocol.study_id, "program": _plain(c.program)} for c in plan.candidates],
            "registry": _plain(plan.registry)}
    return json.dumps(body, sort_keys=True, indent=2) + "\n"


# -- capture --------------------------------------------------------------------------------------------------

def _line(body):
    return json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii") + b"\n"


def _receipt(receipt):
    return {"path": receipt.path, "params": [list(pair) for pair in receipt.params],
            "account_scope": receipt.account_scope, "received_at": _plain(receipt.received_at),
            "server_time": _plain(receipt.server_time), "sha256": receipt.sha256,
            "raw_body_b64": base64.b64encode(receipt.raw_body).decode("ascii")}


def _record(record, body):
    try:
        record(_line(body))
    except Exception:
        raise StudyError("STUDY_RECORD_SINK_FAILED") from None


def _read(book_source):
    try:
        return book_source()
    except ValueError:
        raise
    except Exception:
        raise StudyError("STUDY_CAPTURE_SOURCE_FAILED") from None


def _reason(exc):
    """The fixed code of a refusal raised by a reused helper or the source; any other text is the generic refusal."""
    text = str(exc)
    return text if type(exc) is not ValueError and _CODE.fullmatch(text) is not None else "STUDY_CAPTURE_REFUSED"


def run_capture(plan: StudyPlan, *, book_source: Callable, clock: Callable[[], datetime],
                wait_until: Callable[[datetime], bool], record: Callable[[bytes], None]) -> CaptureOutcome:
    """Drive one PaperCapture per candidate over the frozen grid.

    Before the window everything refuses outright and nothing is recorded: a late start, a failed probe read or a
    failed probe record. Inside the window the first stop (wait_until answered False or Ctrl+C), missed slot
    (the clock is at or past the slot before its prefetch), source failure, sink failure or sampling refusal
    ends the trial for every candidate: the reason is recorded as the last line and the archives are snapshots.
    After the last slot every recorder is finished and the archives are complete.
    """
    digest = validate_study_plan(plan)
    protocol = plan.candidates[0].protocol
    artifact, source = _fixed_file(PROGRAM_SOURCE), capture_source_artifact()
    _require(_clock_value(clock) <= protocol.capture_start - _START_MARGIN, "STUDY_CAPTURE_START_MISSED")
    captures = [PaperCapture(c.protocol, plan.registry, c.program, program_artifact=artifact,
                             capture_source_artifact=source, clock=clock) for c in plan.candidates]
    try:
        probe = _receipt(book_source().receipt)
    except Exception:
        raise StudyError("STUDY_PREWINDOW_PROBE_FAILED") from None
    _record(record, {"probe": probe})
    step = timedelta(seconds=protocol.bar_seconds)
    recorded, reason, archives = 0, None, ()
    try:
        for index in range((protocol.capture_end - protocol.capture_start) // step + 1):
            slot = protocol.capture_start + index * step
            _require(wait_until(slot - _PREFETCH_LEAD), "STUDY_CAPTURE_STOPPED")
            _require(_clock_value(clock) < slot, "STUDY_CAPTURE_SLOT_MISSED")
            book = _read(book_source)
            _require(wait_until(slot), "STUDY_CAPTURE_STOPPED")
            decisions = [(c.program.strategy_id, capture.append_book(book))
                         for c, capture in zip(plan.candidates, captures)]
            _record(record, {"slot": index, "observed_at": _plain(slot), "receipt": _receipt(book.receipt),
                             "decisions": [[identifier, None if decision is None else _plain(decision.target_fraction)]
                                           for identifier, decision in decisions]})
            recorded += 1
        archives = tuple(capture.finish() for capture in captures)
    except KeyboardInterrupt:
        reason = "STUDY_CAPTURE_STOPPED"
    except ValueError as exc:
        reason = _reason(exc)
    if reason is None:
        _record(record, {"end": None})
        return CaptureOutcome(plan_digest=digest, complete=True, reason=None, slots_recorded=recorded,
                              archives=archives)
    try:
        record(_line({"end": reason}))
    except Exception:
        pass                                   # the trial has already failed; the sink's failure is not hidden
    return CaptureOutcome(plan_digest=digest, complete=False, reason=reason, slots_recorded=recorded,
                          archives=tuple(capture.snapshot() for capture in captures))


# -- selection ------------------------------------------------------------------------------------------------

def _sharpe_bound(returns, protocol):
    """Sample Sharpe ratio (cash return 0, unannualized) and its simultaneous lower bound: the
    floor(alpha / K * (B + 1))-th smallest circular moving-block bootstrap draw, drawn in strategy._block_p's order
    from the protocol's seed so every candidate sees the same index draws. (None, None) when the sample has no
    finite positive variance and (sharpe, None) when a draw has none: never an infinite winner."""
    n, length = len(returns), protocol.block_length
    values = [float(v) for v in returns]
    mean = math.fsum(values) / n
    variance = math.fsum((v - mean) ** 2 for v in values) / (n - 1)
    if not (math.isfinite(variance) and variance > 0):
        return None, None
    sharpe = mean / math.sqrt(variance)
    sums, squares = [0.0], [0.0]
    for v in values + values:
        sums.append(sums[-1] + v)
        squares.append(squares[-1] + v * v)
    whole, remainder = divmod(n, length)
    blocks = [(sums[i + length] - sums[i], squares[i + length] - squares[i]) for i in range(n)]
    tails = [(sums[i + remainder] - sums[i], squares[i + remainder] - squares[i]) for i in range(n)] if remainder else ()
    rng, draws = random.Random(protocol.seed), []
    for _ in range(protocol.bootstrap_replications):
        picked = [blocks[rng.randrange(n)] for _ in range(whole)]
        if remainder:
            picked.append(tails[rng.randrange(n)])
        drawn_mean = math.fsum(p[0] for p in picked) / n
        drawn_variance = (math.fsum(p[1] for p in picked) - n * drawn_mean * drawn_mean) / (n - 1)
        if not (math.isfinite(drawn_variance) and drawn_variance > 0):
            return sharpe, None
        draws.append(drawn_mean / math.sqrt(drawn_variance))
    rank = int(Fraction(protocol.alpha) * (protocol.bootstrap_replications + 1) / len(protocol.family_members))
    return sharpe, sorted(draws)[rank - 1]      # rank >= 1 by the plan's p-value resolution check


def _row(candidate, result, profile, artifact, terms, now, review_verifier):
    protocol, program = candidate.protocol, candidate.program
    empty = dict(study_id=protocol.study_id, strategy_id=protocol.strategy_id, math_qualified=False,
                 evidence_digest=None, sharpe=None, sharpe_lower=None, worst_drawdown=None, turnover_ratio=None,
                 evaluated_at=result.evaluated_at if type(result) is ValidationResult else None)
    if result is None:
        return CandidateRow(**empty, status="MISSING", reasons=("STUDY_RESULT_MISSING",))
    variant = replace(profile, strategy_id=program.strategy_id, strategy_code_sha256=program_digest(program, artifact))
    try:
        assessment = assess_strategy(protocol, result, profile_contract_digest=profile_contract_digest(variant),
                                     rule_terms_digest=terms, strategy_code_sha256=variant.strategy_code_sha256,
                                     now=now, review_verifier=review_verifier)
    except StrategyEvidenceError as exc:
        return CandidateRow(**empty, status="EXCLUDED", reasons=(str(exc),))
    sharpe, lower = _sharpe_bound(result.net_returns, protocol)
    reasons = assessment.reasons + (("STUDY_SHARPE_UNRANKABLE",) if lower is None else ())
    return CandidateRow(study_id=protocol.study_id, strategy_id=protocol.strategy_id,
                        status="QUALIFIED" if assessment.research_review_ready and lower is not None else "EXCLUDED",
                        reasons=reasons, math_qualified=assessment.math_qualified,
                        evidence_digest=assessment.evidence_digest, evaluated_at=result.evaluated_at,
                        sharpe=sharpe, sharpe_lower=lower,
                        worst_drawdown=max(result.primary.max_drawdown, result.double_cost.max_drawdown,
                                           result.extra_bar_delay.max_drawdown),
                        turnover_ratio=result.primary.turnover_quote / float(protocol.initial_cash_quote))


def rank_market_evidence(plan: StudyPlan, results: Mapping[str, ValidationResult], *, profile: LaunchProfile,
                         now: datetime, review_verifier: Callable | None = None) -> MarketSelection:
    """The frozen single-market selection over actual evaluated results keyed by study id.

    profile is the current base profile; each candidate is assessed against its variant, so a changed scope,
    policy, convention or rule term excludes every row. review_verifier is the trusted ReviewVerifiers.source
    wired by the coordinator; None can never select. Steps 1-2 of the protocol's order (risk groups, distinct
    assets) are reported as counts and are constant inside this single-asset market; steps 3-4 order the
    qualified rows by (-sharpe_lower, worst_drawdown, turnover_ratio, strategy_id). A winner is never forced.
    """
    digest = validate_study_plan(plan)
    _require(isinstance(results, Mapping) and all(type(key) is str for key in results), "STUDY_PLAN_SCHEMA_INVALID")
    _require(type(profile) is LaunchProfile and profile.instrument_rules is not None, "STUDY_PROFILE_INCOMPLETE")
    _instant(now)
    _require(set(results) <= {c.protocol.study_id for c in plan.candidates}, "STUDY_RESULT_NOT_IN_PLAN")
    artifact, terms = _fixed_file(PROGRAM_SOURCE), rule_terms_digest(profile.instrument_rules)
    rows = tuple(_row(c, results.get(c.protocol.study_id), profile, artifact, terms, now, review_verifier)
                 for c in plan.candidates)
    qualified = [row for row in rows if row.status == "QUALIFIED"]
    best = min(qualified, key=lambda row: (-row.sharpe_lower, row.worst_drawdown, row.turnover_ratio,
                                           row.strategy_id)) if qualified else None
    return MarketSelection(plan_digest=digest, status="SELECTED" if best else "NO_QUALIFIED_MARKET",
                           symbol=plan.candidates[0].protocol.symbol,
                           selected_study_id=best.study_id if best else None,
                           selected_strategy_id=best.strategy_id if best else None,
                           qualified_assets=1 if best else 0, qualified_risk_groups=1 if best else 0,
                           rows=rows, reasons=() if best else ("STUDY_NO_QUALIFIED_CANDIDATE",))


# -- command line ---------------------------------------------------------------------------------------------

def _arguments(argv):
    values = sys.argv[1:] if argv is None else argv
    _require(type(values) in (list, tuple) and all(type(v) is str for v in values) and len(values) > 0,
             "STUDY_ARGUMENTS_INVALID")
    if tuple(values) in (("--help",), ("-h",)):
        return "help", {}
    names = _COMMANDS.get(values[0])
    _require(names is not None and len(values) == 1 + 2 * len(names), "STUDY_ARGUMENTS_INVALID")
    output = {}
    for key, value in zip(values[1::2], values[2::2]):
        _require(key.startswith("--") and key[2:] in names and key[2:] not in output and value
                 and not value.startswith("--"), "STUDY_ARGUMENTS_INVALID")
        output[key[2:]] = value
    return values[0], output


def _draft(raw):
    body = _json(raw, _MAX_PLAN_BYTES)
    _require(type(body) is dict and set(body) == {"schema_version", "plan_id", "asset", "risk_group", "template",
                                                   "programs"}
             and type(body["schema_version"]) is int and body["schema_version"] == 1
             and type(body["programs"]) is list, "STUDY_PLAN_SCHEMA_INVALID")
    return (parse_protocol(json.dumps(body["template"])), tuple(parse_program(json.dumps(p)) for p in body["programs"]),
            {name: body[name] for name in ("plan_id", "asset", "risk_group")})


def _output_directory(path):
    """An existing, empty, absolute, link-free local directory with no private component or stream suffix
    (STUDY_OUTPUT_REFUSED); one that already holds something is STUDY_OUTPUT_EXISTS. Nothing is created here."""
    try:
        _require(type(path) is str and path and "\x00" not in path, "STUDY_OUTPUT_REFUSED")
        candidate = Path(path)
        _require(candidate.is_absolute() and ".." not in candidate.parts
                 and ":" not in str(candidate)[len(candidate.anchor):]
                 and not any(part.casefold() in _PRIVATE or part.casefold() == ".env"
                             or part.casefold().startswith(".env.") for part in candidate.parts),
                 "STUDY_OUTPUT_REFUSED")
        absolute = Path(os.path.abspath(candidate))
        _require(os.path.normcase(os.path.realpath(absolute, strict=True)) == os.path.normcase(str(absolute)),
                 "STUDY_OUTPUT_REFUSED")
        for prefix in (absolute, *absolute.parents):
            entry = os.lstat(prefix)
            _require(stat.S_ISDIR(entry.st_mode)
                     and not getattr(entry, "st_file_attributes", 0) & _REFUSED_ATTRIBUTES, "STUDY_OUTPUT_REFUSED")
        checked_target(absolute, "study output directory")
        _require(not any(absolute.iterdir()), "STUDY_OUTPUT_EXISTS")
        return absolute
    except StudyError:
        raise
    except (OSError, RuntimeError, ValueError):
        raise StudyError("STUDY_OUTPUT_REFUSED") from None


def _open_new(directory, name):
    """The module's only writer: one new, exclusive, append-only file inside the checked output directory."""
    try:
        _require(type(name) is str and ":" not in name and not (os.name == "nt" and os.path.isreserved(name)),
                 "STUDY_OUTPUT_REFUSED")
        descriptor = os.open(checked_target(directory / name, "study output file", within=directory),
                             os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_APPEND | _FLAGS, 0o600)
    except FileExistsError:
        raise StudyError("STUDY_OUTPUT_EXISTS") from None
    except (OSError, RuntimeError):
        raise StudyError("STUDY_OUTPUT_REFUSED") from None
    return os.fdopen(descriptor, "ab")


def _write_new(directory, name, raw):
    with _open_new(directory, name) as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())


class _Sink:
    """receipts.jsonl: created on the first line (a failed probe leaves the directory empty), one fsync per line."""

    def __init__(self, directory):
        self._directory, self._handle = directory, None

    def __call__(self, line):
        if self._handle is None:
            self._handle = _open_new(self._directory, "receipts.jsonl")
        self._handle.write(line)
        self._handle.flush()
        os.fsync(self._handle.fileno())

    def close(self):
        if self._handle is not None:
            self._handle.close()


def _select(plan, profile, captures, now):
    results, evaluation, capture_digests = {}, {}, {}
    for candidate in plan.candidates:
        identifier = candidate.protocol.study_id
        try:
            raw = _read_file(str(Path(captures) / (identifier + ".capture.json")), MAX_CAPTURE_BYTES)
            results[identifier] = evaluate_capture_json(candidate.protocol, raw, profile.instrument_rules, now=now)
            capture_digests[identifier] = hashlib.sha256(raw).hexdigest()
            evaluation[identifier] = "EVALUATED"
        except (WorkflowError, StrategyEvidenceError) as exc:
            evaluation[identifier] = _reason(exc)
    selection = rank_market_evidence(plan, results, profile=profile, now=now, review_verifier=None)
    artifact, requests = _fixed_file(PROGRAM_SOURCE), []
    # A review binds failures too: partial families cannot emit selectable review requests.
    if len(results) != len(plan.candidates):
        return selection, evaluation, requests
    family = build_family_commitment(plan_digest=validate_study_plan(plan), capture_digests=capture_digests,
                                     result_digests={key: evidence_digest(value) for key, value in results.items()})
    for candidate, row in zip(plan.candidates, selection.rows):
        if row.reasons == ("STRATEGY_TRUSTED_REVIEW_REQUIRED",):      # math met; the review is the owner's step
            variant = replace(profile, strategy_id=candidate.program.strategy_id,
                              strategy_code_sha256=program_digest(candidate.program, artifact))
            request = build_review_request(variant, candidate.protocol, results[row.study_id], now=now,
                                           program_artifact=artifact,
                                           parameters_json=parameters_json(candidate.program))
            requests.append(bind_review_family(request, family))
    return selection, evaluation, requests


def main(argv: list[str] | None = None) -> int:
    command = None
    try:
        command, args = _arguments(argv)
        if command == "help":
            print(__doc__)
            return 0
        if command == "select":
            now = _time(args["now"])                        # refuse an invalid time before any file is read
        else:
            directory = _output_directory(args["out"])     # refuse a bad destination before any private read
        output = _base(command)
        if command == "freeze":
            profile = parse_profile_json(_read_file(args["profile"], MAX_CONFIG_BYTES))
            template, programs, names = _draft(_read_file(args["draft"], _MAX_PLAN_BYTES))
            plan = build_study_plan(profile, programs, template=template, **names)
            _write_new(directory, "plan.json", study_plan_json(plan).encode("ascii"))
            _write_new(directory, "commitment.json", commitment_json(plan).encode("ascii"))
            output.update(workflow_complete=True, plan_sha256=validate_study_plan(plan),
                          capture_source_code_sha256=plan.candidates[0].protocol.capture_source_code_sha256,
                          candidates=[c.protocol.study_id for c in plan.candidates],
                          reasons=["STUDY_COMMITMENT_NOT_PUBLISHED"])
        elif command == "capture":
            plan = parse_study_plan(_read_file(args["plan"], _MAX_PLAN_BYTES))
            from execution_accounts.quotes import E1UpbitQuoteSource

            def clock():
                return datetime.now(timezone.utc)

            def wait_until(when):
                try:
                    while True:
                        remaining = (when - clock()).total_seconds()
                        if remaining <= 0:
                            return True
                        time.sleep(min(1.0, remaining))
                except KeyboardInterrupt:
                    return False
            source = E1UpbitQuoteSource(symbol=plan.candidates[0].protocol.symbol, clock=clock)
            sink = _Sink(directory)
            try:
                outcome = run_capture(plan, book_source=source.read, clock=clock, wait_until=wait_until, record=sink)
            finally:
                sink.close()
            suffix = ".capture.json" if outcome.complete else ".incomplete.json"
            for candidate, archive in zip(plan.candidates, outcome.archives):
                _write_new(directory, candidate.protocol.study_id + suffix, capture_json(archive).encode("ascii"))
            output.update(workflow_complete=outcome.complete, plan_sha256=outcome.plan_digest,
                          slots_recorded=outcome.slots_recorded, reasons=[] if outcome.complete else [outcome.reason])
            print(json.dumps(output, sort_keys=True))
            return 0 if outcome.complete else 1
        else:
            plan = parse_study_plan(_read_file(args["plan"], _MAX_PLAN_BYTES))
            profile = parse_profile_json(_read_file(args["profile"], MAX_CONFIG_BYTES))
            selection, evaluation, requests = _select(plan, profile, args["captures"], now)
            output.update(workflow_complete=True, selection=_plain(selection), evaluation=evaluation,
                          review_requests=requests, reasons=list(selection.reasons))
        print(json.dumps(output, sort_keys=True, allow_nan=False))
        return 0                                   # an offline result, never permission to trade
    except ValueError as exc:
        code = exc.code if type(exc) is ProfileError else str(exc)
        if type(exc) is ValueError or _CODE.fullmatch(code) is None:
            code = "STUDY_INPUT_REFUSED"
    except (OSError, TypeError, AttributeError, ArithmeticError, RecursionError, KeyError):
        code = "STUDY_INPUT_REFUSED"
    except KeyboardInterrupt:                      # Ctrl+C anywhere outside the capture waiter: the same fixed code
        code = "STUDY_CAPTURE_STOPPED"
    output = _base(command if command in _COMMANDS else None)
    output["reasons"] = [code]
    print(json.dumps(output, sort_keys=True))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
