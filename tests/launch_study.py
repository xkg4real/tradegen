"""Prospective study module over invented 2031 data: one-cell clocks, scripted waiters, fake books, list sinks,
temporary output directories and a fixture-only review verifier. Nothing here fetches, signs, arms, publishes,
reads a credential or touches a real home."""
from __future__ import annotations

import ast
import base64
from contextlib import ExitStack, redirect_stdout
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import hashlib
from io import StringIO
import json
import os
from pathlib import Path
import random
import statistics
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

from execution_accounts.quotes import QuoteError
from execution_control.model import InstrumentRules
from execution_launch import study as S
from execution_launch.paper_capture import capture_json, replay_capture
from execution_launch.profile import (AccountingConventions, LaunchProfile, PolicyInputs, profile_body,
                                      profile_contract_digest)
from execution_launch.program import ProgramSpec, program_digest, program_json
from execution_launch.strategy import (EVALUATOR_REVISION, ForwardProtocol, _plain, evaluate_capture_json,
                                       evidence_digest, protocol_json)
from execution_launch.workflow import _artifact
from tests import compliance_fixtures as F
from tests.compliance_guards import CLOCKS, _walk
from tests.launch_capture import book
from tests.launch_guards import problems
from tests.launch_strategy import fixture_review

D = Decimal
ROOT = Path(__file__).resolve().parents[1]
MODULE = "execution_launch/study.py"
START = datetime(2031, 1, 6, tzinfo=timezone.utc)
BAR = timedelta(seconds=300)
SCOPE = "synthetic-acct-zq7"
PRINCIPAL = "13579"
PERIOD = 20                     # bars per triangle cycle: ten rising and ten falling marks between 200 and 300
_SHARED = {}                    # one complete 501-slot capture, evaluated once per process


# -- fixtures ------------------------------------------------------------------------------------------------

def rules(asof=START - timedelta(days=1)):
    return InstrumentRules(venue="upbit", market="spot", symbol="KRW-BTC", lot_size=D("0.01"), tick_size=D("1"),
                           min_quantity=D("0.01"), min_notional_krw=D("1"), fee_fraction=D("0.001"), asof=asof,
                           source_digest="a" * 64)


def profile(**changes):
    base = LaunchProfile(schema_version=1, profile_id="synthetic-study-profile", venue="upbit", market="spot",
        symbol="KRW-BTC", quote_currency="KRW", account_scope=SCOPE, time_in_force="gtc", instrument_rules=rules(),
        policy=PolicyInputs(version="synthetic-policy", source_sha256="b" * 64, initial_equity=D(PRINCIPAL),
            drawdown_activation_equity=D("50000"), positive_profit_loss_fraction=D("0.2"),
            peak_drawdown_fraction=D("0.2"), zero_profit_day_target_fraction=D("0.1"),
            first_day_loss_budget=D("10"), zero_profit_day_loss_budget=D("8")),
        conventions=AccountingConventions(valuation="marked_equity", daily_loss="externally_reconciled",
            external_flows="externally_cashflow_adjusted", realized_profit="fifo_all_fees_krw",
            fx="current_marks_execution_time_fills", rounding="fifo_floor_18dp_remainder_to_final",
            day_boundary="Asia/Seoul", first_day_scope="first_trading_day_only"))
    return replace(base, **changes)


def program(strategy_id, fast, slow):
    return ProgramSpec(schema_version=1, strategy_id=strategy_id, kind="moving_average_trend", fast_window=fast,
                       slow_window=slow, exposure_fraction=D("1"))


A, B, C = program("fixture-ma-1-2-a", 1, 2), program("fixture-ma-1-2-b", 1, 2), program("fixture-ma-2-4", 2, 4)
PROGRAMS = (A, B, C)


def template(observations=60, bar_seconds=300, **changes):
    base = ForwardProtocol(schema_version=1, study_id="fixture-study", strategy_id="placeholder",
        strategy_code_sha256="0" * 64, capture_source_id="fixture-orderbook-source",
        capture_source_code_sha256="0" * 64, evaluator_revision=EVALUATOR_REVISION,
        profile_contract_digest="0" * 64, rule_terms_digest="0" * 64, venue="upbit", market="spot",
        symbol="KRW-BTC", quote_currency="KRW", preregistered_at=START - timedelta(days=1), capture_start=START,
        capture_end=START + timedelta(seconds=bar_seconds * observations), initial_cash_quote=D("1"),
        fee_fraction=D("0"), slippage_bps=D("0"), bar_seconds=bar_seconds, minimum_fill_delay_seconds=60,
        minimum_observations=observations, minimum_roundtrips=20, block_length=5, bootstrap_replications=999,
        family_members=("placeholder",), alpha=D("0.05"), max_drawdown=D("0.2"), review_max_age_seconds=86400,
        seed=83)
    return replace(base, **changes)


def plan(observations=60, programs=PROGRAMS, current=None, **changes):
    return S.build_study_plan(current or profile(), programs, template=template(observations, **changes),
                              plan_id="fixture-plan-2031", asset="BTC", risk_group="crypto-btc")


def draft_json():
    return json.dumps({"schema_version": 1, "plan_id": "fixture-plan-2031", "asset": "BTC",
                       "risk_group": "crypto-btc", "template": json.loads(protocol_json(template())),
                       "programs": [json.loads(program_json(p)) for p in PROGRAMS]}, indent=2) + "\n"


def refused(call, code):
    try:
        call()
    except ValueError as exc:
        assert str(exc) == code, (str(exc), code)
        assert PRINCIPAL not in str(exc) and SCOPE not in str(exc)
        return
    raise AssertionError("expected " + code)


def invoke(*argv):
    output = StringIO()
    with redirect_stdout(output):
        code = S.main(list(argv))
    text = output.getvalue()
    try:
        return code, json.loads(text), text
    except ValueError:
        return code, None, text


class Driver:
    """A scripted capture run: a one-cell clock, a waiter that advances it, a book source stamped at the clock and
    a list sink. on_wait(when) may move the clock or answer False; on_read(index) may return a book or raise."""

    def __init__(self, plan):
        self.plan = plan
        self.start = plan.candidates[0].protocol.capture_start
        self.clock = [self.start - timedelta(seconds=120)]
        self.lines, self.reads = [], 0
        self.on_wait = lambda when: True
        self.on_read = lambda index: None
        self.probe_failure = None

    def slot(self, index):
        return self.start + BAR * index

    def book_at(self, at, received_delta=0):
        phase = round((at - self.start) / BAR) % PERIOD
        mid = 200 + 10 * min(phase, PERIOD - phase)
        return book(at, received_delta=received_delta, asof_delta=received_delta - 1, bid=mid - 1, ask=mid + 1)

    def wait_until(self, when):
        answer = self.on_wait(when)
        self.clock[0] = max(self.clock[0], when)
        return answer

    def read(self):
        self.reads += 1
        if self.reads == 1 and self.probe_failure is not None:
            raise self.probe_failure
        scripted = None if self.reads == 1 else self.on_read(round((self.clock[0] - self.start) / BAR))
        return self.book_at(self.clock[0]) if scripted is None else scripted

    def run(self):
        return S.run_capture(self.plan, book_source=self.read, clock=lambda: self.clock[0],
                             wait_until=self.wait_until, record=self.lines.append)


def shared():
    """A, B and C over one complete 501-slot triangle capture; the evaluator issues results once per process."""
    if not _SHARED:
        p = plan(500)
        driver = Driver(p)
        outcome = driver.run()
        assert outcome.complete and outcome.slots_recorded == 501, outcome.reason
        now = p.candidates[0].protocol.capture_end + timedelta(seconds=60)
        results = {c.protocol.study_id: evaluate_capture_json(c.protocol, capture_json(archive), rules(), now=now)
                   for c, archive in zip(p.candidates, outcome.archives)}
        _SHARED.update(plan=p, outcome=outcome, results=results, now=now)
    return SimpleNamespace(**_SHARED)


def study_id(spec):
    return "fixture-study." + spec.strategy_id


def rank(**changes):
    env = shared()
    args = dict(plan=env.plan, results=env.results, profile=profile(), now=env.now, review_verifier=None)
    args.update(changes)
    return S.rank_market_evidence(args.pop("plan"), args.pop("results"), **args)


def naive_sharpe_lower(returns, protocol, rank_index):
    """The design's bound by brute force: circular blocks drawn in strategy._block_p's order from the same seed."""
    n, length = len(returns), protocol.block_length
    whole, remainder = divmod(n, length)
    rng, draws = random.Random(protocol.seed), []
    for _ in range(protocol.bootstrap_replications):
        sample = []
        for _ in range(whole):
            at = rng.randrange(n)
            sample.extend(returns[(at + j) % n] for j in range(length))
        if remainder:
            at = rng.randrange(n)
            sample.extend(returns[(at + j) % n] for j in range(remainder))
        draws.append(statistics.fmean(sample) / statistics.stdev(sample))
    return sorted(draws)[rank_index - 1]


# -- capture (T1-T5) -----------------------------------------------------------------------------------------

def test_capture_complete_window_reproduces_evaluator_input():
    p = plan()
    driver = Driver(p)
    outcome = driver.run()
    assert outcome.complete and outcome.reason is None and outcome.slots_recorded == 61
    assert outcome.plan_digest == S.validate_study_plan(p) and len(outcome.archives) == 3
    end = p.candidates[0].protocol.capture_end
    for candidate, archive in zip(p.candidates, outcome.archives):
        assert len(archive.bars) == 61 and len(archive.decisions) == 60
        assert archive.source_kind == "prospective_paper_capture" and archive.registry == p.registry
        assert archive.bars[0].observed_at == START and archive.bars[-1].observed_at == end
        result = evaluate_capture_json(candidate.protocol, capture_json(archive), rules(),
                                       now=end + timedelta(seconds=60))
        assert result.inputs_digest == evidence_digest((archive.bars, archive.decisions))
        assert result.source_kind == "prospective_paper_capture" and result.primary.observations == 60
    assert outcome.archives[0].decisions == outcome.archives[1].decisions      # A and B share the parameters
    lines = [json.loads(line) for line in driver.lines]
    assert len(lines) == 63 and set(lines[0]) == {"probe"} and lines[-1] == {"end": None} and driver.reads == 62
    keys = {"path", "params", "account_scope", "received_at", "server_time", "sha256", "raw_body_b64"}
    for receipt in [lines[0]["probe"]] + [line["receipt"] for line in lines[1:-1]]:
        assert set(receipt) == keys and receipt["account_scope"] == "public-upbit-orderbook"
        assert hashlib.sha256(base64.b64decode(receipt["raw_body_b64"])).hexdigest() == receipt["sha256"]
    for index, line in enumerate(lines[1:-1]):
        assert line["slot"] == index and line["observed_at"] == _plain(driver.slot(index))
        assert [sid for sid, _ in line["decisions"]] == [c.program.strategy_id for c in p.candidates]
        assert all(target is None for _, target in line["decisions"]) == (index == 60)
        assert all(target in (None, "0", "1") for _, target in line["decisions"])


def test_late_book_stops_without_backfill():
    driver = Driver(plan())

    def late(index):
        if index == 7:
            driver.clock[0] = driver.slot(7) + timedelta(seconds=1)
            return driver.book_at(driver.clock[0])
    driver.on_read = late
    outcome = driver.run()
    assert not outcome.complete and outcome.reason == "CAPTURE_BOOK_NOT_AVAILABLE_AT_SLOT"
    assert outcome.slots_recorded == 7 and driver.reads == 9
    for archive in outcome.archives:
        assert len(archive.bars) == 7 and max(row.observed_at for row in archive.bars) == driver.slot(6)
        assert archive.source_kind == "prospective_paper_capture"
    lines = [json.loads(line) for line in driver.lines]
    assert len(lines) == 9 and lines[-1] == {"end": "CAPTURE_BOOK_NOT_AVAILABLE_AT_SLOT"}
    assert [line["slot"] for line in lines[1:-1]] == list(range(7))


def test_future_receipt_and_rewritten_history_refuse():
    driver = Driver(plan())
    driver.on_read = lambda index: driver.book_at(driver.slot(7), received_delta=5) if index == 7 else None
    outcome = driver.run()
    assert not outcome.complete and outcome.reason == "QUOTE_RECEIPT_STALE_OR_FUTURE" and outcome.slots_recorded == 7
    assert all(len(archive.bars) == 7 for archive in outcome.archives)
    assert json.loads(driver.lines[-1]) == {"end": "QUOTE_RECEIPT_STALE_OR_FUTURE"}
    p = plan()
    complete = Driver(p).run()
    assert complete.complete
    body = json.loads(capture_json(complete.archives[0]))
    body["bars"][5]["bid"] = str(int(body["bars"][5]["bid"]) - 1)
    end = p.candidates[0].protocol.capture_end
    refused(lambda: evaluate_capture_json(p.candidates[0].protocol, json.dumps(body), rules(),
                                          now=end + timedelta(seconds=60)), "STRATEGY_DECISION_INPUT_MISMATCH")


def test_stop_while_waiting_or_in_provider_is_bounded():
    driver = Driver(plan())
    driver.on_wait = lambda when: when != driver.slot(3) - S._PREFETCH_LEAD
    outcome = driver.run()
    assert outcome.reason == "STUDY_CAPTURE_STOPPED" and outcome.slots_recorded == 3 and driver.reads == 4
    assert len(driver.lines) == 5 and json.loads(driver.lines[-1]) == {"end": "STUDY_CAPTURE_STOPPED"}
    assert all(len(archive.bars) == 3 for archive in outcome.archives)
    driver = Driver(plan())

    def interrupted(when):
        if when == driver.slot(4):
            raise KeyboardInterrupt
        return True
    driver.on_wait = interrupted
    outcome = driver.run()
    assert outcome.reason == "STUDY_CAPTURE_STOPPED" and outcome.slots_recorded == 4
    for failure, reason in ((RuntimeError("acct-secret-zq7"), "STUDY_CAPTURE_SOURCE_FAILED"),
                            (QuoteError("QUOTE_PUBLIC_INQUIRY_FAILED"), "QUOTE_PUBLIC_INQUIRY_FAILED"),
                            (ValueError("acct-secret-zq7"), "STUDY_CAPTURE_REFUSED"),
                            (QuoteError("not a code: acct-secret-zq7"), "STUDY_CAPTURE_REFUSED")):
        driver = Driver(plan())

        def failing(index, failure=failure):
            if index == 2:
                raise failure
        driver.on_read = failing
        outcome = driver.run()
        assert outcome.reason == reason and outcome.slots_recorded == 2 and not outcome.complete
        assert len(outcome.archives) == 3 and all(len(archive.bars) == 2 for archive in outcome.archives)
        text = b"".join(driver.lines).decode("ascii")
        assert "acct-secret" not in text and "acct-secret" not in repr(outcome)
        assert json.loads(driver.lines[-1]) == {"end": reason}
    # Before the window nothing is recorded: a late start and a failed probe refuse outright.
    driver = Driver(plan())
    driver.clock[0] = START - timedelta(seconds=59)
    refused(driver.run, "STUDY_CAPTURE_START_MISSED")
    driver = Driver(plan())
    driver.probe_failure = QuoteError("QUOTE_BOOK_STALE_OR_FUTURE")
    refused(driver.run, "STUDY_PREWINDOW_PROBE_FAILED")
    assert driver.lines == [] and driver.reads == 1


def test_suspend_resume_cannot_fabricate_missed_slot():
    driver = Driver(plan())

    def suspend(when):
        if when == driver.slot(5) - S._PREFETCH_LEAD:
            driver.clock[0] = driver.slot(5) + timedelta(seconds=30)
        return True
    driver.on_wait = suspend
    outcome = driver.run()
    assert outcome.reason == "STUDY_CAPTURE_SLOT_MISSED" and outcome.slots_recorded == 5 and driver.reads == 6
    for archive in outcome.archives:
        assert max(row.observed_at for row in archive.bars) == driver.slot(4)
        assert len(archive.decisions) == 5 and all(decision.bar_index < 5 for decision in archive.decisions)
    assert json.loads(driver.lines[-1]) == {"end": "STUDY_CAPTURE_SLOT_MISSED"}


# -- plan (T6-T9) --------------------------------------------------------------------------------------------

def test_plan_binds_complete_common_family():
    p = plan()
    assert S.validate_study_plan(p) == evidence_digest(p)
    candidates = p.candidates
    family = replace(candidates[1], protocol=replace(candidates[1].protocol,
                                                     family_members=(A.strategy_id, C.strategy_id)))
    refused(lambda: S.validate_study_plan(replace(p, candidates=(candidates[0], family, candidates[2]))),
            "STUDY_FAMILY_INCOMPLETE")
    shifted = replace(candidates[2], protocol=replace(candidates[2].protocol,
                                                      capture_end=candidates[2].protocol.capture_end + BAR))
    refused(lambda: S.validate_study_plan(replace(p, candidates=candidates[:2] + (shifted,))),
            "STUDY_TERMS_NOT_COMMON")
    cash = ProgramSpec(schema_version=1, strategy_id="fixture-cash", kind="cash", fast_window=0, slow_window=0,
                       exposure_fraction=D("0"))
    refused(lambda: plan(programs=PROGRAMS + (cash,)), "STUDY_CASH_MEMBER_CANNOT_QUALIFY")
    refused(lambda: plan(study_id="fixture:study"), "STUDY_PLAN_SCHEMA_INVALID")   # NTFS stream in the archive name
    refused(lambda: plan(study_id="CON"), "STUDY_PLAN_SCHEMA_INVALID")             # DOS device: CON.<id>.capture.json
    retuned = tuple(replace(c, protocol=replace(c.protocol, alpha=D("0.04"))) for c in candidates)
    refused(lambda: S.validate_study_plan(replace(p, candidates=retuned)), "CAPTURE_PROTOCOL_NOT_REGISTERED")
    refused(lambda: S.validate_study_plan(replace(p, prior_research_sha256="f" * 64)), "STUDY_PRIOR_RESEARCH_MISMATCH")
    for broken in (replace(p, selection_rule="other-rule"), replace(p, candidates=()),
                   replace(p, candidates=(candidates[1], candidates[0], candidates[2])),
                   replace(p, candidates=(candidates[0], candidates[0], candidates[2])),
                   replace(p, schema_version=2), replace(p, plan_id="private plan id"),
                   replace(p, candidates=(replace(candidates[0], program=B),) + candidates[1:])):
        refused(lambda broken=broken: S.validate_study_plan(broken), "STUDY_PLAN_SCHEMA_INVALID")


def test_feasibility_refuses_impossible_plans_without_relaxing_bounds():
    refused(lambda: plan(alpha=D("0.001")), "STUDY_PVALUE_RESOLUTION_INFEASIBLE")
    refused(lambda: plan(19999, bar_seconds=60, block_length=1, minimum_fill_delay_seconds=30),
            "STUDY_INFERENCE_WORK_LIMIT")
    refused(lambda: plan(programs=(A, B, program("fixture-ma-20-40", 20, 40))), "STUDY_ROUNDTRIPS_INFEASIBLE")
    refused(lambda: plan(minimum_fill_delay_seconds=295), "STUDY_FILL_DELAY_INFEASIBLE")
    refused(lambda: plan(minimum_roundtrips=19), "STRATEGY_THRESHOLD_INVALID")
    assert S._WORK_LIMIT == 10_000_000 and S.SELECTION_RULE == "upbit-krw-single-asset-v1"
    assert plan(alpha=D("0.003")).candidates[0].protocol.alpha == D("0.003")        # 3/1000 is still reachable
    assert plan(minimum_fill_delay_seconds=290).candidates[0].protocol.minimum_fill_delay_seconds == 290


def test_plan_json_strict_and_commitment_hides_private_values():
    p = plan()
    raw = S.study_plan_json(p)
    parsed = S.parse_study_plan(raw)
    assert parsed == p and S.validate_study_plan(parsed) == S.validate_study_plan(p)
    assert S.parse_study_plan(raw.encode("ascii")) == p
    # strategy._json folds its duplicate-key and float hooks into one refusal (strategy.py:563); it is reused as is.
    refused(lambda: S.parse_study_plan(raw.replace('"schema_version": 1', '"schema_version": 1, "schema_version": 1', 1)),
            "STRATEGY_JSON_INVALID")
    refused(lambda: S.parse_study_plan(raw.replace('"alpha": "0.05"', '"alpha": 0.05')), "STRATEGY_JSON_INVALID")
    refused(lambda: S.parse_study_plan(raw.replace('"alpha": "0.05"', '"alpha": NaN')), "STRATEGY_JSON_INVALID")
    refused(lambda: S.parse_study_plan(raw.rstrip()[:-1] + ', "eligible": true}'), "STUDY_PLAN_SCHEMA_INVALID")
    refused(lambda: S.parse_study_plan(raw.replace('"selection_rule": "upbit-krw-single-asset-v1"',
                                                   '"selection_rule": "other"')), "STUDY_PLAN_SCHEMA_INVALID")
    refused(lambda: S.parse_study_plan(" " * (S._MAX_PLAN_BYTES + 1)), "STRATEGY_JSON_SIZE_OR_TYPE")
    assert PRINCIPAL in raw and "initial_cash_quote" in raw               # the plan itself stays private
    commitment = S.commitment_json(p)
    body = json.loads(commitment)
    assert body["plan_sha256"] == S.validate_study_plan(p) and body["plan_id"] == "fixture-plan-2031"
    assert body["registry"] == _plain(p.registry) and body["selection_rule"] == S.SELECTION_RULE
    assert body["window"] == {"capture_start": _plain(START), "capture_end": _plain(START + BAR * 60),
                              "bar_seconds": 300, "preregistered_at": _plain(START - timedelta(days=1))}
    assert [c["program"] for c in body["candidates"]] == [_plain(c.program) for c in p.candidates]
    assert body["capture_source_code_sha256"] == p.candidates[0].protocol.capture_source_code_sha256
    assert body["capture_source_manifest"] == json.loads(S.capture_source_artifact())
    assert body["prior_research_sha256"] == p.prior_research_sha256
    for private in (PRINCIPAL, SCOPE, "initial_cash_quote", "profile_contract_digest",
                    *(c.protocol.profile_contract_digest for c in p.candidates)):
        assert private not in commitment, private


def test_freeze_binds_profile_variants_capital_fee_and_source():
    p = plan()
    artifact = _artifact("program.py")
    ids = tuple(sorted(spec.strategy_id for spec in PROGRAMS))
    assert tuple(c.program.strategy_id for c in p.candidates) == ids
    for candidate in p.candidates:
        protocol, spec = candidate.protocol, candidate.program
        code = program_digest(spec, artifact)
        variant = replace(profile(), strategy_id=spec.strategy_id, strategy_code_sha256=code)
        assert protocol.profile_contract_digest == profile_contract_digest(variant)
        assert protocol.strategy_code_sha256 == code and protocol.strategy_id == spec.strategy_id
        assert protocol.study_id == study_id(spec) and protocol.family_members == ids
        assert protocol.initial_cash_quote == D(PRINCIPAL) and protocol.fee_fraction == rules().fee_fraction
        assert protocol.capture_source_code_sha256 == hashlib.sha256(S.capture_source_artifact()).hexdigest()
        assert protocol.capture_start == START and protocol.preregistered_at == START - timedelta(days=1)
    assert [row.study_id for row in p.registry] == [c.protocol.study_id for c in p.candidates]
    assert p.prior_research_sha256 == hashlib.sha256((ROOT / S.PRIOR_RESEARCH).read_bytes()).hexdigest()
    refused(lambda: plan(current=profile(account_scope=None)), "STUDY_PROFILE_INCOMPLETE")
    refused(lambda: plan(current=profile(instrument_rules=rules(asof=START - timedelta(days=1, minutes=10)))),
            "STUDY_PROFILE_INCOMPLETE")
    refused(lambda: plan(current=profile(policy=replace(profile().policy, initial_equity=None))),
            "STUDY_PROFILE_INCOMPLETE")
    refused(lambda: plan(current=profile(symbol="KRW-ETH", instrument_rules=replace(rules(), symbol="KRW-ETH"))),
            "WORKFLOW_PROFILE_PROTOCOL_MISMATCH")
    refused(lambda: plan(programs=(A, replace(B, strategy_id=A.strategy_id))), "STUDY_PLAN_SCHEMA_INVALID")


# -- selection (T10-T13) -------------------------------------------------------------------------------------

def test_math_pass_without_trusted_review_is_no_qualified_market():
    env = shared()
    selection = rank()
    assert selection.status == "NO_QUALIFIED_MARKET" and selection.reasons == ("STUDY_NO_QUALIFIED_CANDIDATE",)
    assert selection.selected_study_id is None and selection.selected_strategy_id is None
    assert selection.plan_digest == S.validate_study_plan(env.plan) and selection.symbol == "KRW-BTC"
    assert selection.qualified_assets == 0 and selection.qualified_risk_groups == 0
    assert not selection.execution_ready and len(selection.rows) == 3
    for row in selection.rows:
        assert row.status == "EXCLUDED" and row.evidence_digest is not None and row.evaluated_at == env.now
        assert row.sharpe is not None and row.sharpe_lower is not None and row.turnover_ratio is not None
    for spec in (A, B):
        row = next(row for row in selection.rows if row.strategy_id == spec.strategy_id)
        assert row.math_qualified and row.reasons == ("STRATEGY_TRUSTED_REVIEW_REQUIRED",) and row.study_id == study_id(spec)
    plain = _plain(selection)
    assert json.dumps(plain, allow_nan=False) and plain["execution_ready"] is False
    refused(lambda: rank(profile=profile(instrument_rules=None)), "STUDY_PROFILE_INCOMPLETE")


def test_selection_never_promotes_synthetic_mutated_unknown_or_missing():
    env = shared()
    verifier = fixture_review(env.now)
    synthetic = {}
    for candidate, archive in zip(env.plan.candidates, env.outcome.archives):
        replayed = replay_capture(candidate.protocol, env.plan.registry, candidate.program, archive.bars,
                                  program_artifact=_artifact("program.py"),
                                  capture_source_artifact=S.capture_source_artifact(), source_kind="synthetic",
                                  now=env.now)
        synthetic[candidate.protocol.study_id] = evaluate_capture_json(candidate.protocol, capture_json(replayed),
                                                                        rules(), now=env.now)
    selection = rank(results=synthetic, review_verifier=verifier)
    assert selection.status == "NO_QUALIFIED_MARKET"
    for row in selection.rows:
        assert row.status == "EXCLUDED" and row.math_qualified and "STRATEGY_NONPROSPECTIVE_SOURCE" in row.reasons
    first = study_id(A)
    mutated = dict(env.results)
    mutated[first] = replace(env.results[first], family_adjusted_p=0.001)
    selection = rank(results=mutated, review_verifier=verifier)
    row = next(row for row in selection.rows if row.study_id == first)
    assert row.status == "EXCLUDED" and row.reasons == ("STRATEGY_RESULT_NOT_ISSUED_OR_MUTATED",)
    assert not row.math_qualified and row.sharpe is None and row.evidence_digest is None
    assert selection.status == "SELECTED" and selection.selected_strategy_id in (B.strategy_id, C.strategy_id)
    refused(lambda: rank(results=dict(env.results, **{"other.study": env.results[first]}), review_verifier=verifier),
            "STUDY_RESULT_NOT_IN_PLAN")
    refused(lambda: rank(results=[env.results[first]], review_verifier=verifier), "STUDY_PLAN_SCHEMA_INVALID")
    without = {key: value for key, value in env.results.items() if key != study_id(C)}
    selection = rank(results=without, review_verifier=verifier)
    row = next(row for row in selection.rows if row.study_id == study_id(C))
    assert row.status == "MISSING" and row.reasons == ("STUDY_RESULT_MISSING",) and row.sharpe is None
    assert row.evaluated_at is None and len(selection.rows) == 3 and selection.status == "SELECTED"
    for result in env.results.values():
        assert result.family_adjusted_p == min(1.0, 3 * result.benchmark_p)
    selection = rank(results={first: {"research_label": "PASS"}}, review_verifier=verifier)
    row = next(row for row in selection.rows if row.study_id == first)
    assert row.status == "EXCLUDED" and row.reasons == ("STRATEGY_COMPUTED_RESULT_REQUIRED",)


def test_selection_order_is_frozen_and_deterministic():
    env = shared()
    verifier = fixture_review(env.now)
    selection = rank(review_verifier=verifier)
    assert selection.status == "SELECTED" and selection.reasons == () and not selection.execution_ready
    assert selection.qualified_assets == selection.qualified_risk_groups == 1
    qualified = [row for row in selection.rows if row.status == "QUALIFIED"]
    assert {row.strategy_id for row in qualified} >= {A.strategy_id, B.strategy_id}
    expected = min(qualified, key=lambda row: (-row.sharpe_lower, row.worst_drawdown, row.turnover_ratio,
                                                 row.strategy_id))
    assert (selection.selected_strategy_id, selection.selected_study_id) == (expected.strategy_id, expected.study_id)
    rows = {row.strategy_id: row for row in selection.rows}
    metrics = lambda row: (row.sharpe, row.sharpe_lower, row.worst_drawdown, row.turnover_ratio, row.math_qualified)
    assert metrics(rows[A.strategy_id]) == metrics(rows[B.strategy_id])
    assert selection.selected_strategy_id == A.strategy_id            # equal metrics: the lexical identifier wins
    reversed_order = dict(reversed(list(env.results.items())))
    assert S.rank_market_evidence(env.plan, reversed_order, profile=profile(), now=env.now,
                                  review_verifier=verifier) == selection
    for row in qualified:
        result, protocol = env.results[row.study_id], env.plan.candidates[0].protocol
        returns = list(result.net_returns)
        assert abs(row.sharpe - statistics.fmean(returns) / statistics.stdev(returns)) < 1e-12
        assert row.sharpe_lower < row.sharpe and row.sharpe > 0
        assert abs(row.sharpe_lower - naive_sharpe_lower(returns, protocol, 16)) < 1e-9     # floor(0.05/3 * 1000)
        assert row.worst_drawdown == max(result.primary.max_drawdown, result.double_cost.max_drawdown,
                                         result.extra_bar_delay.max_drawdown)
        assert row.turnover_ratio == result.primary.turnover_quote / float(D(PRINCIPAL))
    constant = replace(env.results[study_id(A)], net_returns=(0.0,) * len(env.results[study_id(A)].net_returns))
    assert S._sharpe_bound(constant.net_returns, env.plan.candidates[0].protocol) == (None, None)


def test_selection_rechecks_current_bindings_and_capture_code():
    env = shared()
    verifier = fixture_review(env.now)
    selection = rank(profile=profile(account_scope="synthetic-acct-other"), review_verifier=verifier)
    assert selection.status == "NO_QUALIFIED_MARKET"
    for row in selection.rows:
        assert row.status == "EXCLUDED" and "STRATEGY_DEPLOYMENT_BINDING_MISMATCH" in row.reasons
    with patch.object(S, "capture_source_artifact", return_value=b"other capture code"):
        refused(lambda: rank(review_verifier=verifier), "STUDY_CAPTURE_SOURCE_CHANGED")
        refused(Driver(env.plan).run, "STUDY_CAPTURE_SOURCE_CHANGED")
        refused(lambda: S.validate_study_plan(env.plan), "STUDY_CAPTURE_SOURCE_CHANGED")
    with patch.object(S, "CAPTURE_FILES", S.CAPTURE_FILES + ("execution_launch/missing.py",)):
        refused(S.capture_source_artifact, "STUDY_SOURCE_FILE_INVALID")
    stale = rank(now=env.now + timedelta(days=15), review_verifier=verifier)
    assert stale.status == "NO_QUALIFIED_MARKET"
    assert all("STRATEGY_EVIDENCE_STALE_OR_FUTURE" in row.reasons for row in stale.rows)


# -- CLI (T14, T16) ------------------------------------------------------------------------------------------

def test_cli_outputs_are_new_redacted_files_only():
    env = shared()
    with tempfile.TemporaryDirectory(prefix="launch_study_") as directory:
        root = Path(os.path.realpath(directory))
        inputs, out, empty, link = root / "inputs", root / "out", root / "empty", root / "alias"
        for folder in (inputs, out, empty):
            folder.mkdir()
        (inputs / "profile.json").write_text(json.dumps(profile_body(profile()), indent=2), encoding="utf-8")
        (inputs / "draft.json").write_text(draft_json(), encoding="utf-8")
        freeze = ("freeze", "--profile", str(inputs / "profile.json"), "--draft", str(inputs / "draft.json"))
        code, report, raw = invoke(*freeze, "--out", str(out))
        assert code == 0 and report["execution_ready"] is False and report["research_review_ready"] is False
        assert report["reasons"] == ["STUDY_COMMITMENT_NOT_PUBLISHED"] and report["command"] == "freeze"
        assert '"' + PRINCIPAL + '"' not in raw and SCOPE not in raw and str(root) not in raw
        written = S.parse_study_plan((out / "plan.json").read_bytes())
        assert written == plan() and report["plan_sha256"] == S.validate_study_plan(written)
        assert report["candidates"] == [c.protocol.study_id for c in written.candidates]
        assert report["capture_source_code_sha256"] == written.candidates[0].protocol.capture_source_code_sha256
        assert sorted(path.name for path in out.iterdir()) == ["commitment.json", "plan.json"]
        assert (out / "commitment.json").read_text(encoding="utf-8") == S.commitment_json(written)
        assert all(os.lstat(path).st_nlink == 1 and not path.is_symlink() for path in out.iterdir())
        code, report, raw = invoke(*freeze, "--out", str(out))
        assert code == 2 and report["reasons"] == ["STUDY_OUTPUT_EXISTS"] and not report["execution_ready"]
        F.directory_link(link, empty)
        for destination in (str(link), str(root / ".tradegen" / "out"), "out:stream", str(empty) + ":stream",
                            str(root / "missing"), str(inputs / "draft.json"), str(root / "x" / ".." / "empty")):
            code, report, raw = invoke(*freeze, "--out", destination)
            assert code == 2 and report["reasons"] == ["STUDY_OUTPUT_REFUSED"], destination
            assert str(root) not in raw and "alias" not in raw and not report["execution_ready"]
        assert not any(empty.iterdir())
        with ExitStack() as stack:
            stack.enter_context(patch("execution_accounts.quotes.E1UpbitQuoteSource",
                                      side_effect=AssertionError("constructed")))
            stack.enter_context(patch("execution_launch.study._read_file", side_effect=AssertionError("read")))
            for argv in (["capture"], [], ["capture", "--plan", "p.json"], ["activate"],
                         ["freeze", "--profile", "a.json", "--profile", "b.json", "--out", str(out)],
                         ["capture", "--plan", "p.json", "--out", str(empty), "--extra", "x"]):
                code, report, raw = invoke(*argv)
                assert code == 2 and report["reasons"] == ["STUDY_ARGUMENTS_INVALID"], argv
                assert not report["execution_ready"] and "p.json" not in raw
            code, report, raw = invoke("select", "--plan", "p.json", "--profile", "q.json", "--captures", str(empty),
                                       "--now", "yesterday")
            assert code == 2 and report["reasons"] == ["WORKFLOW_EXPLICIT_TIME_REQUIRED"]
            code, report, raw = invoke("capture", "--plan", str(inputs / "draft.json"), "--out", str(out))
            assert code == 2 and report["reasons"] == ["STUDY_OUTPUT_EXISTS"]
        code, _, raw = invoke("--help")
        assert code == 0 and "freeze" in raw and "select" in raw
        # select: two complete captures and one missing file; without a trusted verifier nothing qualifies
        captures = root / "captures"
        captures.mkdir()
        (inputs / "plan.json").write_text(S.study_plan_json(env.plan), encoding="utf-8")
        for candidate, archive in list(zip(env.plan.candidates, env.outcome.archives))[:2]:
            (captures / (candidate.protocol.study_id + ".capture.json")).write_text(capture_json(archive),
                                                                                   encoding="utf-8")
        code, report, raw = invoke("select", "--plan", str(inputs / "plan.json"), "--profile",
                                   str(inputs / "profile.json"), "--captures", str(captures), "--now",
                                   env.now.isoformat())
        assert code == 0 and report["execution_ready"] is False and report["research_review_ready"] is False
        selection = report["selection"]
        assert selection["status"] == "NO_QUALIFIED_MARKET" and report["reasons"] == ["STUDY_NO_QUALIFIED_CANDIDATE"]
        assert selection["execution_ready"] is False and selection["selected_study_id"] is None
        statuses = {row["study_id"]: (row["status"], row["reasons"]) for row in selection["rows"]}
        assert statuses == {study_id(A): ("EXCLUDED", ["STRATEGY_TRUSTED_REVIEW_REQUIRED"]),
                            study_id(B): ("EXCLUDED", ["STRATEGY_TRUSTED_REVIEW_REQUIRED"]),
                            study_id(C): ("MISSING", ["STUDY_RESULT_MISSING"])}
        assert report["evaluation"] == {study_id(A): "EVALUATED", study_id(B): "EVALUATED",
                                        study_id(C): "WORKFLOW_FILE_UNAVAILABLE_OR_REFUSED"}
        requests = report["review_requests"]
        assert requests == []  # A missing family member cannot be omitted from signed selection evidence.
        assert all(request["artifact_kind"] == "unsigned_strategy_review_request"
                   and request["authority"]["execution_ready"] is False for request in requests)
        assert '"' + PRINCIPAL + '"' not in raw and SCOPE not in raw and str(root) not in raw
        assert sorted(path.name for path in captures.iterdir()) == sorted(
            candidate.protocol.study_id + ".capture.json" for candidate in env.plan.candidates[:2])


def test_cli_capture_runs_through_the_injected_clock_and_writes_only_new_files():
    p = plan()
    driver = Driver(p)
    end = p.candidates[0].protocol.capture_end

    class FakeSource:
        def __init__(self, *, symbol, clock):
            assert symbol == "KRW-BTC" and callable(clock)

        def read(self):
            return driver.read()

    def sleep(seconds):
        assert 0 < seconds <= 1.0
        if driver.stop_at is not None and driver.clock[0] >= driver.stop_at:
            raise KeyboardInterrupt
        driver.clock[0] = driver.clock[0] + timedelta(seconds=seconds)
    driver.stop_at = None
    with tempfile.TemporaryDirectory(prefix="launch_study_") as directory:
        root = Path(os.path.realpath(directory))
        plan_path = root / "plan.json"
        plan_path.write_text(S.study_plan_json(p), encoding="utf-8")
        with ExitStack() as stack:
            stack.enter_context(patch("execution_accounts.quotes.E1UpbitQuoteSource", FakeSource))
            stack.enter_context(patch.object(S, "time", SimpleNamespace(sleep=sleep)))
            stack.enter_context(patch.object(S, "datetime", SimpleNamespace(now=lambda tz: driver.clock[0])))
            out = root / "out"
            out.mkdir()
            code, report, raw = invoke("capture", "--plan", str(plan_path), "--out", str(out))
            assert code == 0 and report["workflow_complete"] and report["slots_recorded"] == 61
            assert report["reasons"] == [] and report["execution_ready"] is False and driver.reads == 62
            assert report["plan_sha256"] == S.validate_study_plan(p) and str(root) not in raw
            names = sorted(path.name for path in out.iterdir())
            assert names == sorted(["receipts.jsonl"] + [c.protocol.study_id + ".capture.json" for c in p.candidates])
            lines = (out / "receipts.jsonl").read_bytes().split(b"\n")
            assert len(lines) == 64 and lines[-1] == b"" and json.loads(lines[-2]) == {"end": None}
            assert set(json.loads(lines[0])) == {"probe"} and json.loads(lines[1])["slot"] == 0
            for candidate in p.candidates:
                archive = (out / (candidate.protocol.study_id + ".capture.json")).read_bytes()
                result = evaluate_capture_json(candidate.protocol, archive, rules(), now=end + timedelta(seconds=60))
                assert result.primary.observations == 60 and result.source_kind == "prospective_paper_capture"
            # Ctrl+C while waiting for slot 11 (no signal handler: the waiter answers False) is a failed trial.
            driver = Driver(p)
            driver.stop_at = driver.slot(10)
            stopped = root / "stopped"
            stopped.mkdir()
            code, report, raw = invoke("capture", "--plan", str(plan_path), "--out", str(stopped))
            assert code == 1 and not report["workflow_complete"] and report["slots_recorded"] == 11
            assert report["reasons"] == ["STUDY_CAPTURE_STOPPED"] and report["execution_ready"] is False
            names = sorted(path.name for path in stopped.iterdir())
            assert names == sorted(["receipts.jsonl"] + [c.protocol.study_id + ".incomplete.json" for c in p.candidates])
            lines = (stopped / "receipts.jsonl").read_bytes().split(b"\n")
            assert len(lines) == 14 and json.loads(lines[-2]) == {"end": "STUDY_CAPTURE_STOPPED"}
            body = json.loads((stopped / (study_id(A) + ".incomplete.json")).read_text(encoding="utf-8"))
            assert len(body["bars"]) == 11 and body["source_kind"] == "prospective_paper_capture"
            # A probe failure before the window leaves the directory empty, so the same destination can be reused.
            driver = Driver(p)
            driver.probe_failure = QuoteError("QUOTE_BOOK_STALE_OR_FUTURE")
            probe = root / "probe"
            probe.mkdir()
            code, report, raw = invoke("capture", "--plan", str(plan_path), "--out", str(probe))
            assert code == 2 and report["reasons"] == ["STUDY_PREWINDOW_PROBE_FAILED"] and not any(probe.iterdir())


def test_cli_maps_a_keyboard_interrupt_anywhere_to_the_stopped_code():
    """K13: Ctrl+C outside the capture waiter (inside the pre-window probe read, and inside another command's plan
    parse) prints only the fixed code STUDY_CAPTURE_STOPPED: no traceback, no path, nothing written."""
    p = plan()
    driver = Driver(p)

    class InterruptedSource:
        def __init__(self, *, symbol, clock):
            assert symbol == "KRW-BTC" and callable(clock)

        def read(self):
            raise KeyboardInterrupt
    with tempfile.TemporaryDirectory(prefix="launch_study_") as directory:
        root = Path(os.path.realpath(directory))
        plan_path = root / "plan.json"
        plan_path.write_text(S.study_plan_json(p), encoding="utf-8")
        out = root / "out"
        out.mkdir()
        with ExitStack() as stack:
            stack.enter_context(patch("execution_accounts.quotes.E1UpbitQuoteSource", InterruptedSource))
            stack.enter_context(patch.object(S, "datetime", SimpleNamespace(now=lambda tz: driver.clock[0])))
            code, report, raw = invoke("capture", "--plan", str(plan_path), "--out", str(out))
        assert code == 2 and report["reasons"] == ["STUDY_CAPTURE_STOPPED"] and report["execution_ready"] is False
        assert "Traceback" not in raw and str(root) not in raw and not any(out.iterdir())
        with patch.object(S, "parse_study_plan", side_effect=KeyboardInterrupt):
            code, report, raw = invoke("select", "--plan", str(plan_path), "--profile", str(plan_path),
                                       "--captures", str(out), "--now", "2031-01-01T00:00:00+00:00")
        assert code == 2 and report["reasons"] == ["STUDY_CAPTURE_STOPPED"] and report["execution_ready"] is False
        assert "Traceback" not in raw and str(root) not in raw


# -- static contract (T15) -----------------------------------------------------------------------------------

def test_study_reads_clock_only_in_main_and_has_no_endpoint_literal():
    source = (ROOT / MODULE).read_bytes()
    source.decode("ascii")
    text = source.decode("utf-8")
    assert problems(text, MODULE) == [], problems(text, MODULE)
    tree = ast.parse(text)
    for node, functions in _walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            base = node.func.value
            owner = base.id if isinstance(base, ast.Name) else base.attr if isinstance(base, ast.Attribute) else ""
            if node.func.attr in CLOCKS.get(owner, ()):
                assert "main" in functions, ast.unparse(node)
    names = ({node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
             | {node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)})
    assert not names & {"Thread", "signal", "SIGINT", "atexit", "environ", "getenv", "compare_and_set",
                        "initialize_reviewed_head", "home", "state_root"}
    for node in tree.body:
        if isinstance(node, ast.If):                       # the command-line guard is the only statement
            assert ast.unparse(node.test) == "__name__ == '__main__'" and node is tree.body[-1]
            continue
        assert isinstance(node, (ast.Expr, ast.Import, ast.ImportFrom, ast.Assign, ast.FunctionDef, ast.ClassDef)), node
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            modules = [alias.name for alias in node.names] if isinstance(node, ast.Import) else [node.module or ""]
            assert not any(m.startswith(("execution_accounts.quotes", "execution.transport", "execution_orders",
                                         "execution_control")) for m in modules), modules
    assert isinstance(tree.body[0], ast.Expr) and isinstance(tree.body[0].value, ast.Constant)
    assert not any(isinstance(node, ast.Expr) for node in tree.body[1:])
    manifest = json.loads(S.capture_source_artifact())
    assert manifest["kind"] == "tradegen-study-capture/1" and set(manifest["files"]) == set(S.CAPTURE_FILES)
    assert MODULE in S.CAPTURE_FILES and "execution_launch/paper_capture.py" in S.CAPTURE_FILES
    for name, digest in manifest["files"].items():
        assert digest == hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
    assert S.capture_source_artifact() == S.capture_source_artifact()
    assert (ROOT / S.PRIOR_RESEARCH).is_file()
