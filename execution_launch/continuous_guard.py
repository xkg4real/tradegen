"""Pure launch-level chronological risk plans; never a live authorization or commit.

This module replays raw path events and FIFO inputs rather than trusting a public
preview's point array. Digests and claim consistency are checked, but the caller
still has to authenticate the source, pre/post owner context, current controller
anchor, and independently retained heads. No production verifier or persistence
adapter is supplied. ``GuardPlan.execution_ready`` is unconditionally false.

Existing controller journal kinds are not changed. Historical source instants
are carried separately from the observation time; no risk_snapshot is backdated.
"""
from __future__ import annotations

from dataclasses import dataclass, fields, replace
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal, DecimalException, Inexact, localcontext
import re

from core.compliance.model import KST
from execution_accounts.baseline import BaselineInterval, BaselineState, risk_baseline
from execution_accounts.baseline_bridge import advance_account_baseline
from execution_accounts.continuous import (
    COVERAGE_CONTRACT, CoverageRequest, ContinuousPath, EquityPoint, VerifiedCoverage,
    validate_path, value_path,
)
from execution_accounts.model import AccountEvidence, content_digest
from execution_accounts.provider import _account as _reconcile_captured_account
from execution_control.risk import Fill, RecoveryCheckpoint, RiskObservation, RiskPolicy, account_fills, evaluate

_SHA = re.compile(r"[0-9a-f]{64}")
_ZERO = Decimal(0)
_FRESH = timedelta(seconds=30)


class ContinuousGuardError(ValueError):
    """Fixed codes, with no private values or source exception messages."""


def _need(ok, code):
    if not ok:
        raise ContinuousGuardError(code)


def _hash(value):
    _need(type(value) is str and _SHA.fullmatch(value) is not None, "GUARD_DIGEST_REQUIRED")


def _instant(value):
    try:
        _need(type(value) is datetime and value.utcoffset() is not None
              and 2 <= value.year <= 9998, "GUARD_AWARE_TIME_REQUIRED")
        return value.astimezone(timezone.utc)
    except Exception:
        raise ContinuousGuardError("GUARD_AWARE_TIME_REQUIRED") from None


def _amount(value, *, positive=False):
    _need(type(value) is Decimal and value.is_finite() and len(value.as_tuple().digits) <= 60
          and -40 <= value.as_tuple().exponent <= 40
          and (value > 0 if positive else value >= 0), "GUARD_EXACT_AMOUNT_REQUIRED")


@dataclass(frozen=True, kw_only=True)
class OwnerContextClaim:
    """Evidence to authenticate outside this pure module, not a verified token.

    Values are the *effective* limits at observed_at. An unchanged owner log head
    alone is insufficient: a scheduled limit can become effective at midnight.
    """
    owner_head_sha256: str
    code_sha256: str
    code_approval_sha256: str
    signed_floor_krw: Decimal
    signed_daily_loss_krw: Decimal
    observed_at: datetime
    source_sha256: str


@dataclass(frozen=True, kw_only=True)
class GuardAnchor:
    """Explicit reviewed controller checkpoint; no default or balance-only seed."""
    baseline_state_sha256: str
    control_journal_head_sha256: str
    high_watermark: Decimal
    day_start_equity: Decimal
    observed_daily_loss: Decimal
    applied_floor_krw: Decimal
    daily_stopped: bool
    permanently_halted: bool
    recorded_at: datetime
    source_sha256: str


@dataclass(frozen=True, kw_only=True)
class GuardCheckpoint:
    schema_version: int
    baseline: BaselineState
    owner_head_sha256: str
    code_sha256: str
    policy_sha256: str
    anchor_sha256: str
    high_watermark: Decimal
    applied_floor_krw: Decimal
    observed_daily_loss: Decimal
    daily_stopped: bool
    permanently_halted: bool
    stream_epoch: str
    next_sequence: int | None
    recorded_at: datetime
    previous_guard_sha256: str
    last_path_sha256: str
    last_input_sha256: str
    state_sha256: str


@dataclass(frozen=True, kw_only=True)
class ValuationInputs:
    opening_cash_krw: Decimal
    opening_units: tuple[tuple[str, Decimal], ...]
    historical_fills: tuple[Fill, ...]
    interval_fills: tuple[Fill, ...]


@dataclass(frozen=True, kw_only=True)
class AccountCaptureInputs:
    """Normalized capture and reconstructed endpoint; raw-source auth remains external."""
    manifest_sha256: str
    captured_accounts: tuple[AccountEvidence, ...]
    endpoint_accounts: tuple[AccountEvidence, ...]
    first_received_at: datetime


@dataclass(frozen=True, kw_only=True)
class GuardPoint:
    source_at: datetime
    policy_day: date
    boundary_side: str
    equity_krw: Decimal
    realized_net_total_krw: Decimal
    high_watermark: Decimal
    effective_floor_krw: Decimal
    observed_daily_loss: Decimal
    daily_stopped: bool
    permanently_halted: bool
    reasons: tuple[str, ...]


@dataclass(frozen=True, kw_only=True)
class RequiredGuardRecord:
    """Required future journal effect, not a performed write or existing row kind."""
    kind: str
    recorded_at: datetime
    source_at: datetime
    policy_day: date
    boundary_side: str
    reason: str
    floor_krw: Decimal | None = None


@dataclass(frozen=True, kw_only=True)
class GuardPlan:
    previous_guard_sha256: str
    previous_baseline_sha256: str
    proposed_checkpoint: GuardCheckpoint
    path_sha256: str
    input_sha256: str
    points: tuple[GuardPoint, ...]
    required_records: tuple[RequiredGuardRecord, ...]
    recorded_at: datetime
    idempotent: bool
    plan_sha256: str

    @property
    def execution_ready(self):
        return False

    @property
    def blockers(self):
        return ("GUARD_SOURCE_AUTHENTICATION_REQUIRED", "GUARD_OWNER_AND_CONTROL_AUTHENTICATION_REQUIRED",
                "GUARD_DURABLE_COMMIT_PROTOCOL_REQUIRED")


def _owner(claim):
    _need(type(claim) is OwnerContextClaim, "GUARD_OWNER_CONTEXT_REQUIRED")
    for name in ("owner_head_sha256", "code_sha256", "code_approval_sha256", "source_sha256"):
        _hash(getattr(claim, name))
    _instant(claim.observed_at)
    _amount(claim.signed_floor_krw)
    _amount(claim.signed_daily_loss_krw, positive=True)


def _owner_terms(claim):
    return (claim.owner_head_sha256, claim.code_sha256, claim.code_approval_sha256,
            claim.signed_floor_krw, claim.signed_daily_loss_krw)


def _checkpoint_digest(state):
    return content_digest(tuple(getattr(state, field.name) for field in fields(GuardCheckpoint)
                                if field.name != "state_sha256"))


def _checkpoint(**kwargs):
    state = GuardCheckpoint(**kwargs, state_sha256="")
    return replace(state, state_sha256=_checkpoint_digest(state))


def _validate_checkpoint(state):
    _need(type(state) is GuardCheckpoint and type(state.schema_version) is int and state.schema_version == 1,
          "GUARD_CHECKPOINT_REQUIRED")
    baseline = state.baseline
    _need(type(baseline) is BaselineState, "GUARD_BASELINE_REQUIRED")
    risk_baseline(baseline, now=baseline.asof, expected_head=baseline.state_digest)
    for name in ("owner_head_sha256", "code_sha256", "policy_sha256", "anchor_sha256", "state_sha256"):
        _hash(getattr(state, name))
    chain = (state.previous_guard_sha256, state.last_path_sha256, state.last_input_sha256)
    _need(all(chain) or not any(chain), "GUARD_CHAIN_INCOMPLETE")
    for value in chain:
        if value:
            _hash(value)
    _instant(state.recorded_at)
    _need(state.recorded_at >= baseline.asof, "GUARD_CHECKPOINT_CLOCK_INVALID")
    if any(chain):
        _need(type(state.stream_epoch) is str and re.fullmatch(r"[A-Za-z0-9_.:/-]{1,128}", state.stream_epoch)
              and type(state.next_sequence) is int and 0 <= state.next_sequence < 2**63,
              "GUARD_STREAM_STATE_REQUIRED")
    else:
        _need(state.stream_epoch == "" and state.next_sequence is None, "GUARD_STREAM_STATE_UNEXPECTED")
    _amount(state.high_watermark, positive=True); _amount(state.applied_floor_krw)
    _amount(state.observed_daily_loss)
    _need(type(state.daily_stopped) is bool and type(state.permanently_halted) is bool,
          "GUARD_LATCH_STATE_REQUIRED")
    _need(state.high_watermark >= baseline.high_watermark
          and state.observed_daily_loss >= baseline.observed_daily_loss,
          "GUARD_HISTORY_WEAKENED")
    if baseline.approved_effective_floor is not None:
        _need(state.applied_floor_krw >= baseline.approved_effective_floor, "GUARD_FLOOR_WEAKENED")
    _need(state.state_sha256 == _checkpoint_digest(state), "GUARD_CHECKPOINT_CHANGED")


def reviewed_guard_anchor(anchor: GuardAnchor, *, baseline: BaselineState,
                          policy: RiskPolicy, owner: OwnerContextClaim) -> GuardCheckpoint:
    """Construct a candidate checkpoint from explicit review inputs; no state is seeded.

    The review/owner/source authenticity is not established by this function.
    A current balance or an initial configured floor cannot stand in for the
    controller's retained applied floor, high-watermark or halt history.
    """
    try:
        with localcontext() as numeric:
            numeric.prec = 512
            numeric.traps[Inexact] = True
            return _reviewed_guard_anchor(anchor, baseline=baseline, policy=policy, owner=owner)
    except ContinuousGuardError:
        raise
    except (ValueError, TypeError, AttributeError, DecimalException, OverflowError):
        raise ContinuousGuardError("GUARD_ANCHOR_REFUSED") from None


def _reviewed_guard_anchor(anchor, *, baseline, policy, owner):
    try:
        _need(type(anchor) is GuardAnchor and type(baseline) is BaselineState
              and type(policy) is RiskPolicy, "GUARD_REVIEWED_ANCHOR_REQUIRED")
        _owner(owner)
        _instant(anchor.recorded_at)
        risk_baseline(baseline, now=baseline.asof, expected_head=baseline.state_digest)
        for name in ("baseline_state_sha256", "control_journal_head_sha256", "source_sha256"):
            _hash(getattr(anchor, name))
        _need(anchor.baseline_state_sha256 == baseline.state_digest, "GUARD_ANCHOR_BASELINE_MISMATCH")
        _need(anchor.day_start_equity == baseline.day_start_equity,
              "GUARD_DAY_OPENING_RECONCILIATION_REQUIRED")
        _need(timedelta(0) <= baseline.asof-owner.observed_at <= _FRESH,
              "GUARD_PREINTERVAL_OWNER_CONTEXT_REQUIRED")
        _need(timedelta(0) <= anchor.recorded_at-baseline.asof <= _FRESH,
              "GUARD_ANCHOR_CLOCK_INVALID")
        _amount(anchor.applied_floor_krw)
        _need(anchor.applied_floor_krw >= owner.signed_floor_krw,
              "GUARD_SIGNED_FLOOR_NOT_APPLIED")
        state = _checkpoint(schema_version=1, baseline=baseline, owner_head_sha256=owner.owner_head_sha256,
            code_sha256=owner.code_sha256, policy_sha256=content_digest(policy), anchor_sha256=content_digest(anchor),
            high_watermark=anchor.high_watermark, applied_floor_krw=anchor.applied_floor_krw,
            observed_daily_loss=anchor.observed_daily_loss, daily_stopped=anchor.daily_stopped,
            permanently_halted=anchor.permanently_halted, stream_epoch="", next_sequence=None,
            recorded_at=anchor.recorded_at, previous_guard_sha256="", last_path_sha256="",
            last_input_sha256="")
        _validate_checkpoint(state)
        view = RiskObservation(equity=baseline.equity_krw, prior_high_watermark=state.high_watermark,
            day_start_equity=baseline.day_start_equity,
            current_day_realized_net_profit=baseline.realized_net_total_krw-baseline.day_open_realized_net_total_krw,
            prior_day_realized_net_profit=baseline.previous_day_realized_net_krw,
            observed_daily_loss=state.observed_daily_loss, approved_effective_floor=state.applied_floor_krw,
            is_first_trading_day=(baseline.first_trading_day == baseline.asof.astimezone(KST).date()),
            asof=baseline.asof, halted=state.permanently_halted, recovery_checkpoint=baseline.recovery_checkpoint)
        result = evaluate(policy, view, now=baseline.asof)
        _need(result.high_watermark is not None and result.effective_floor is not None,
              "GUARD_ANCHOR_POLICY_INVALID")
        _need(state.applied_floor_krw >= result.effective_floor, "GUARD_ANCHOR_FLOOR_HISTORY_REQUIRED")
        stopped = ("DAILY_LOSS_BUDGET_REACHED" in result.reasons
                   or result.recovery_status in ("unverified", "breached")
                   or state.observed_daily_loss >= owner.signed_daily_loss_krw)
        _need(not stopped or state.daily_stopped, "GUARD_ANCHOR_DAILY_STOP_HISTORY_REQUIRED")
        _need(state.permanently_halted or baseline.equity_krw >= state.applied_floor_krw,
              "GUARD_ANCHOR_HALT_HISTORY_REQUIRED")
        return state
    except ContinuousGuardError:
        raise
    except (ValueError, TypeError, AttributeError, DecimalException, OverflowError):
        raise ContinuousGuardError("GUARD_ANCHOR_REFUSED") from None


def _input_digest(previous_guard_sha, baseline, policy, owner_before, owner_after, path, inputs,
                  account_capture, coverage, interval):
    return content_digest((previous_guard_sha, baseline, policy, owner_before, owner_after, path, inputs,
                           account_capture, coverage, interval))


def plan_continuous_guard(previous: GuardCheckpoint, *, baseline_before: BaselineState, policy: RiskPolicy,
                          owner_before: OwnerContextClaim, owner_after: OwnerContextClaim,
                          path: ContinuousPath, valuation_inputs: ValuationInputs,
                          account_capture: AccountCaptureInputs, coverage: VerifiedCoverage,
                          interval: BaselineInterval, now: datetime) -> GuardPlan:
    """Recompute every point and propose ordered latches and a checkpoint.

    No preview-provided extrema or point trace is trusted. Source/owner claims
    remain claims: even a successful plan cannot be supplied as a live frame.
    Owner-head, effective-limit, policy or code changes refuse; an authenticated
    timeline for changes inside an interval is deliberately not implemented.
    """
    try:
        with localcontext() as numeric:
            numeric.prec = 512
            numeric.traps[Inexact] = True
            return _plan(previous, baseline_before, policy, owner_before, owner_after, path,
                         valuation_inputs, account_capture, coverage, interval, now)
    except ContinuousGuardError:
        raise
    except (ValueError, TypeError, AttributeError, KeyError, DecimalException, OverflowError):
        raise ContinuousGuardError("GUARD_EVIDENCE_REFUSED") from None


def _plan(previous, baseline, policy, owner_before, owner_after, path, inputs, capture, coverage, interval, now):
    _validate_checkpoint(previous)
    _need(type(baseline) is BaselineState and type(policy) is RiskPolicy
          and type(inputs) is ValuationInputs and type(interval) is BaselineInterval
          and type(capture) is AccountCaptureInputs,
          "GUARD_INPUT_REQUIRED")
    risk_baseline(baseline, now=baseline.asof, expected_head=baseline.state_digest)
    _instant(now); _hash(capture.manifest_sha256); _owner(owner_before); _owner(owner_after)
    _need(now >= previous.recorded_at, "GUARD_CLOCK_ROLLBACK")
    _instant(capture.first_received_at)
    _need(type(capture.captured_accounts) is tuple and len(capture.captured_accounts) == 1
          and type(capture.endpoint_accounts) is tuple and len(capture.endpoint_accounts) == 1
          and all(type(account) is AccountEvidence
                  for account in capture.captured_accounts+capture.endpoint_accounts),
          "GUARD_ACCOUNT_CAPTURE_REQUIRED")
    _need(all(account.account_scope == baseline.account_scope and account.venue == "upbit"
              and account.execution_quote == "KRW"
              and all(page.source_sha256 == capture.manifest_sha256 for page in account.pages)
              for account in capture.captured_accounts+capture.endpoint_accounts),
          "GUARD_ACCOUNT_CAPTURE_BINDING_MISMATCH")
    capture_sha = content_digest((capture.manifest_sha256, capture.captured_accounts, capture.endpoint_accounts))
    path = validate_path(path)
    duplicate = previous.last_path_sha256 == content_digest(path)
    if previous.stream_epoch:
        _need(path.stream_epoch == previous.stream_epoch, "GUARD_STREAM_EPOCH_CHANGED")
        _need((path.watermark_sequence if duplicate else path.first_sequence) == previous.next_sequence,
              "GUARD_STREAM_SEQUENCE_GAP")
    _need(path.account_scope == baseline.account_scope and path.start == baseline.asof
          and path.previous_state_digest == baseline.state_digest, "GUARD_PATH_BASELINE_MISMATCH")
    _need(_owner_terms(owner_before) == _owner_terms(owner_after), "GUARD_OWNER_TIMELINE_REQUIRED")
    _need(owner_before.owner_head_sha256 == previous.owner_head_sha256
          and owner_before.code_sha256 == previous.code_sha256
          and content_digest(policy) == previous.policy_sha256, "GUARD_AUTHORITY_EPOCH_CHANGED")
    _need(timedelta(0) <= path.start-owner_before.observed_at <= _FRESH
          and path.watermark_received_at <= owner_after.observed_at <= now
          and timedelta(0) <= now-path.end <= _FRESH, "GUARD_OWNER_INTERVAL_NOT_BRACKETED")
    _need(type(coverage) is VerifiedCoverage and coverage.contract == COVERAGE_CONTRACT,
          "GUARD_COVERAGE_CLAIM_REQUIRED")
    _hash(coverage.request_sha256); _hash(coverage.authority_sha256)
    _hash(coverage.source_proof_sha256); _instant(coverage.verified_at)
    request = CoverageRequest(path_sha256=content_digest(path), account_capture_sha256=capture_sha,
        account_scope=path.account_scope, stream_epoch=path.stream_epoch, start=path.start, end=path.end,
        first_sequence=path.first_sequence, watermark_sequence=path.watermark_sequence)
    _need(coverage.request_sha256 == content_digest(request), "GUARD_COVERAGE_BINDING_MISMATCH")
    _need(path.watermark_received_at <= coverage.verified_at <= owner_after.observed_at,
          "GUARD_COVERAGE_TIME_INVALID")
    captured, endpoint = capture.captured_accounts[0], capture.endpoint_accounts[0]
    _need(path.start < capture.first_received_at <= path.end == endpoint.observed_at
          <= captured.observed_at <= coverage.verified_at
          and captured.observed_at-path.start <= _FRESH,
          "GUARD_CAPTURE_TIME_BINDING_MISMATCH")
    if captured.observed_at == endpoint.observed_at:
        _need(captured == endpoint, "GUARD_CAPTURE_ENDPOINT_CONTRADICTION")
    else:
        _need(len(captured.positions) == len(endpoint.positions), "GUARD_CAPTURE_ENDPOINT_CONTRADICTION")
        for before_position, after_position in zip(captured.positions, endpoint.positions):
            _need(replace(before_position, price=after_position.price, asof=after_position.asof) == after_position
                  and after_position.asof == path.end, "GUARD_CAPTURE_ENDPOINT_CONTRADICTION")
        restamped = replace(captured, observed_at=path.end,
            positions=endpoint.positions, restrictions=replace(captured.restrictions, asof=path.end),
            fx=tuple(replace(rate, asof=path.end) for rate in captured.fx),
            pages=tuple(replace(page, end=path.end, page_sha256="") for page in captured.pages))
        _need(restamped == endpoint, "GUARD_CAPTURE_ENDPOINT_CONTRADICTION")
    # Account-only reconciliation validates the original snapshot without
    # fabricating a later baseline or moving the 22:00 checkpoint to its time.
    captured_result = _reconcile_captured_account(captured, captured.observed_at)
    endpoint_update = advance_account_baseline(baseline, interval, capture.endpoint_accounts, now=now)
    all_fills = endpoint_update.observation.fills
    _need(captured_result["fills"] == all_fills, "GUARD_CAPTURE_FILL_CONTRADICTION")
    historical = tuple(fill for fill in all_fills if fill.executed_at < path.start)
    inside = tuple(fill for fill in all_fills if path.start <= fill.executed_at < path.end)
    prior_accounting = account_fills(historical)
    _need(prior_accounting.ok and prior_accounting.duplicate_count == 0,
          "GUARD_OPENING_ACCOUNTING_REFUSED")
    _need(len(endpoint.opening_cash) == 1 and endpoint.opening_cash[0].currency == "KRW"
          and len(endpoint.balances) == 1 and endpoint.balances[0].currency == "KRW",
          "GUARD_KRW_CASH_EVIDENCE_REQUIRED")
    cash = endpoint.opening_cash[0].amount + sum((amount for venue, scope, amount
        in prior_accounting.cash_deltas_by_account_krw if venue == "upbit" and scope == baseline.account_scope), _ZERO)
    flows = {}
    for page in endpoint.pages:
        if page.kind == "flows":
            for flow in page.rows:
                _need(flow.effective_at < path.start and flow.currency == "KRW"
                      and flow.kind in ("deposit", "withdrawal"), "GUARD_EXTERNAL_FLOW_REFUSED")
                _need(flow.flow_id not in flows or flows[flow.flow_id] == flow, "GUARD_FLOW_CONTRADICTION")
                flows[flow.flow_id] = flow
    cash += sum((flow.amount if flow.kind == "deposit" else -flow.amount for flow in flows.values()), _ZERO)
    expected_inputs = ValuationInputs(opening_cash_krw=cash,
        opening_units=tuple(sorted((row[3], row[4]) for row in prior_accounting.inventory if row[4] != 0)),
        historical_fills=historical, interval_fills=inside)
    _need(inputs == expected_inputs, "GUARD_VALUATION_ACCOUNT_BINDING_MISMATCH")
    valuation = value_path(path, opening_cash_krw=inputs.opening_cash_krw, opening_units=inputs.opening_units,
        historical_fills=inputs.historical_fills, interval_fills=inputs.interval_fills,
        previous_equity_krw=baseline.equity_krw, previous_realized_net_krw=baseline.realized_net_total_krw)
    _need(valuation.closing_cash_krw == endpoint.balances[0].total
          and valuation.closing_units == tuple(sorted((p.symbol, p.units) for p in endpoint.positions)),
          "GUARD_CLOSING_ACCOUNT_COMPONENT_MISMATCH")
    closing_marks = {mark.symbol: mark.price for mark in valuation.closing_marks}
    _need(all(closing_marks.get(position.symbol) == position.price for position in endpoint.positions),
          "GUARD_CLOSING_MARK_MISMATCH")
    _need(interval.account_scope == path.account_scope and interval.start == path.start and interval.end == path.end
          and interval.sequence == baseline.sequence+1 and interval.previous_state_digest == baseline.state_digest
          and interval.equity_krw == valuation.equity_krw
          and interval.minimum_equity_krw == valuation.minimum_equity_krw
          and interval.maximum_equity_krw == valuation.maximum_equity_krw
          and interval.realized_net_total_krw == valuation.realized_net_total_krw
          and interval.gross_external_inflows_krw == _ZERO and interval.gross_external_outflows_krw == _ZERO,
          "GUARD_INTERVAL_REPLAY_MISMATCH")
    _need(interval.coverage_sha256 == content_digest((path, coverage))
          and interval.source_sha256 == content_digest(capture.endpoint_accounts),
          "GUARD_INTERVAL_SOURCE_BINDING_MISMATCH")
    after_baseline = endpoint_update.state
    path_sha = content_digest(path)
    prior_digest = previous.previous_guard_sha256 if duplicate else previous.state_sha256
    input_sha = _input_digest(prior_digest, baseline, policy, owner_before, owner_after, path, inputs,
                             capture, coverage, interval)
    if duplicate:
        _need(previous.last_input_sha256 == input_sha and previous.baseline == after_baseline,
              "GUARD_DUPLICATE_CONTRADICTION")
        return _make_plan(previous_guard_sha256=prior_digest, previous_baseline_sha256=baseline.state_digest,
            proposed_checkpoint=previous, path_sha256=path_sha, input_sha256=input_sha, points=(),
            required_records=(), recorded_at=now, idempotent=True)
    _need(previous.baseline == baseline, "GUARD_BASELINE_OR_HEAD_CHANGED")
    _need(previous.applied_floor_krw >= owner_before.signed_floor_krw,
          "GUARD_SIGNED_FLOOR_NOT_APPLIED")
    condition = policy.recovery_condition
    _need((condition is None) == (baseline.conventions.recovery_cutoff_seconds is None)
          and (condition is None or condition.cutoff_seconds == baseline.conventions.recovery_cutoff_seconds),
          "GUARD_RECOVERY_CONVENTION_MISMATCH")
    high, floor = previous.high_watermark, previous.applied_floor_krw
    daily_loss = previous.observed_daily_loss
    daily_stop, permanent = previous.daily_stopped, previous.permanently_halted
    day_start, day_open_realized = baseline.day_start_equity, baseline.day_open_realized_net_total_krw
    prior_profit = baseline.previous_day_realized_net_krw
    day = baseline.asof.astimezone(KST).date()
    checkpoint = baseline.recovery_checkpoint
    records, points = [], []

    def process(point, *, source_at, evaluation_at, side):
        nonlocal high, floor, daily_loss, daily_stop, permanent, checkpoint
        daily_loss = max(daily_loss, day_start-point.equity_krw, _ZERO)
        if (condition is not None and evaluation_at == path.end
                and evaluation_at.astimezone(KST).time() == time(22)
                and (day == baseline.first_trading_day or prior_profit == _ZERO)):
            checkpoint = RecoveryCheckpoint(cutoff_at=evaluation_at, equity_krw=point.equity_krw,
                                             source_sha256=interval.source_sha256)
        observation = RiskObservation(equity=point.equity_krw, prior_high_watermark=high,
            day_start_equity=day_start, current_day_realized_net_profit=point.realized_net_total_krw-day_open_realized,
            prior_day_realized_net_profit=prior_profit, observed_daily_loss=daily_loss,
            approved_effective_floor=floor, is_first_trading_day=(day == baseline.first_trading_day),
            asof=evaluation_at, halted=permanent, recovery_checkpoint=checkpoint)
        result = evaluate(policy, observation, now=evaluation_at)
        _need(result.high_watermark is not None and result.effective_floor is not None
              and not any(reason.startswith("INVALID_") or reason == "ARITHMETIC_NOT_EXACT_OR_FINITE"
                          for reason in result.reasons), "GUARD_POLICY_OR_OBSERVATION_INVALID")
        high = max(high, result.high_watermark)
        floor = max(floor, result.effective_floor, owner_before.signed_floor_krw)
        reasons = list(result.reasons)
        if point.equity_krw < floor:
            if not permanent:
                records.append(RequiredGuardRecord(kind="permanent_floor_halt", recorded_at=now,
                    source_at=source_at, policy_day=day, boundary_side=side,
                    reason="EQUITY_BELOW_EFFECTIVE_FLOOR", floor_krw=floor))
            permanent = True
        stopped = ("DAILY_LOSS_BUDGET_REACHED" in reasons or result.recovery_status in ("unverified", "breached")
                   or daily_loss >= owner_before.signed_daily_loss_krw)
        if daily_loss >= owner_before.signed_daily_loss_krw:
            reasons.append("SIGNED_DAILY_LOSS_LIMIT_REACHED")
        if stopped and not daily_stop:
            records.append(RequiredGuardRecord(kind="daily_stop", recorded_at=now, source_at=source_at,
                policy_day=day, boundary_side=side, reason="DAILY_STOP_REQUIRED"))
        daily_stop = daily_stop or stopped
        if daily_stop and "PERSISTENT_DAILY_STOP" not in reasons:
            reasons.append("PERSISTENT_DAILY_STOP")
        if permanent and "PERSISTENT_HALT" not in reasons:
            reasons.append("PERSISTENT_HALT")
        points.append(GuardPoint(source_at=source_at, policy_day=day, boundary_side=side,
            equity_krw=point.equity_krw, realized_net_total_krw=point.realized_net_total_krw,
            high_watermark=high, effective_floor_krw=floor, observed_daily_loss=daily_loss,
            daily_stopped=daily_stop, permanently_halted=permanent, reasons=tuple(reasons)))

    rollover = path.end.astimezone(KST).date() != day
    for index, point in enumerate(valuation.points):
        closing_left = rollover and index == len(valuation.points)-1
        evaluation_at = point.at-timedelta(microseconds=1) if closing_left else point.at
        _need(evaluation_at.astimezone(KST).date() == day, "GUARD_DAY_BOUNDARY_UNCOVERED")
        process(point, source_at=point.at, evaluation_at=evaluation_at,
                side="left" if closing_left else "at")
    if rollover:
        # The old-day violation records above survive; only the ordinary daily
        # counters reset. The applied floor, lifetime peak and permanent halt do not.
        prior_profit = valuation.realized_net_total_krw-day_open_realized
        day_start, day_open_realized = valuation.equity_krw, valuation.realized_net_total_krw
        day = path.end.astimezone(KST).date()
        daily_loss, daily_stop, checkpoint = _ZERO, False, None
        process(valuation.points[-1], source_at=path.end, evaluation_at=path.end, side="right")
    state = _checkpoint(schema_version=1, baseline=after_baseline,
        owner_head_sha256=previous.owner_head_sha256, code_sha256=previous.code_sha256,
        policy_sha256=previous.policy_sha256, anchor_sha256=previous.anchor_sha256,
        high_watermark=high, applied_floor_krw=floor, observed_daily_loss=daily_loss,
        daily_stopped=daily_stop, permanently_halted=permanent,
        stream_epoch=path.stream_epoch, next_sequence=path.watermark_sequence, recorded_at=now,
        previous_guard_sha256=previous.state_sha256, last_path_sha256=path_sha, last_input_sha256=input_sha)
    _validate_checkpoint(state)
    return _make_plan(previous_guard_sha256=previous.state_sha256,
        previous_baseline_sha256=baseline.state_digest, proposed_checkpoint=state,
        path_sha256=path_sha, input_sha256=input_sha, points=tuple(points), required_records=tuple(records),
        recorded_at=now, idempotent=False)


def _make_plan(**kwargs):
    body = tuple(kwargs[name] for name in ("previous_guard_sha256", "previous_baseline_sha256",
        "proposed_checkpoint", "path_sha256", "input_sha256", "points", "required_records", "recorded_at", "idempotent"))
    return GuardPlan(**kwargs, plan_sha256=content_digest(body))
