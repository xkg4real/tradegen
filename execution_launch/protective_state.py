"""Pure protective-management state reduction, not an order or approval authority.

All facts below are caller-supplied model inputs. In particular AuthorityFacts is
NOT a cryptographically verified receipt, issued capability, signature or permit.
An eventual integration must derive these facts from independently verified current
code, evidence, owner scopes and the existing risk/order gates. Constructing this
dataclass or receiving an EffectIntent authorizes nothing. This module cannot read
files, fetch data, sign, dispatch orders, renew authority or choose risk limits.

Deadline, faults and restart can block entry/request management review; they never
produce a reduction intent. A separate current assessment can propose reduction
only for an independently eligible strategy/risk cause. Entry halt and reducing
eligibility are separate facts: the existing applicable risk policy, not this
reducer, decides whether a verified reducing action remains eligible under a halt.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
import re

_HASH = re.compile(r"[0-9a-f]{64}")
_ID = re.compile(r"[A-Za-z][A-Za-z0-9_.:-]{0,95}")
_MARKET = re.compile(r"KRW-[A-Z0-9]{1,20}")
_PHASES = frozenset({"waiting_inputs", "monitoring", "recovering", "renewal_pending", "exit_pending",
                     "halted", "owner_action_required", "closed"})
_VERDICTS = frozenset({"hold", "sell", "unavailable"})
_EVENTS = frozenset({"assessment", "deadline", "fault", "restart", "recovery_complete", "authority_updated",
                     "entry_reauthorized", "close"})
_FAULTS = frozenset({"inputs_missing", "strategy_error", "account_unavailable", "storage_unavailable",
                     "settings_missing", "clock_unreliable"})
_RISK_CAUSES = frozenset({"trailing_condition", "floor_band_condition", "daily_band_condition"})
_EFFECTS = frozenset({"block_entry", "request_management_approval", "notify", "reconcile", "consider_reduce"})
_DOMAIN = b"TRADEGEN-PROTECTIVE-STATE-v1\x00"


class ProtectiveStateError(ValueError):
    """Fixed diagnostics only; never include provider text, paths or financial values."""


def _require(ok, code):
    if not ok:
        raise ProtectiveStateError(code)


def _hash(value):
    return type(value) is str and _HASH.fullmatch(value) is not None


def _time(value):
    try:
        _require(type(value) is datetime and value.utcoffset() is not None, "PROTECTIVE_TIME_INVALID")
        return value.astimezone(timezone.utc).isoformat(timespec="microseconds")
    except (ValueError, OverflowError, TypeError):
        raise ProtectiveStateError("PROTECTIVE_TIME_INVALID") from None


def _plain(value):
    if type(value) is datetime:
        return _time(value)
    if type(value) is dict:
        return {key: _plain(item) for key, item in value.items()}
    if type(value) in (tuple, list):
        return [_plain(item) for item in value]
    return value


def _digest(kind, body):
    raw = json.dumps(_plain(body), sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                     allow_nan=False).encode("ascii")
    return hashlib.sha256(_DOMAIN + kind.encode("ascii") + b"\x00" + raw).hexdigest()


@dataclass(frozen=True, kw_only=True)
class ManagementPolicy:
    management_id: str
    account_scope: str
    venue: str
    market: str
    quote_currency: str
    symbol: str
    code_sha256: str
    strategy_sha256: str
    risk_policy_sha256: str
    holding_deadline: datetime
    monitor_until: datetime

    def __post_init__(self):
        _require(all(type(value) is str and _ID.fullmatch(value) is not None
                     for value in (self.management_id, self.account_scope)), "PROTECTIVE_POLICY_INVALID")
        _require(all(type(value) is str for value in (self.venue, self.market, self.quote_currency))
                 and (self.venue, self.market, self.quote_currency) == ("upbit", "spot", "KRW")
                 and type(self.symbol) is str and _MARKET.fullmatch(self.symbol) is not None,
                 "PROTECTIVE_SCOPE_UNSUPPORTED")
        _require(all(_hash(value) for value in (self.code_sha256, self.strategy_sha256, self.risk_policy_sha256)),
                 "PROTECTIVE_POLICY_INVALID")
        _time(self.holding_deadline); _time(self.monitor_until)
        _require(self.holding_deadline <= self.monitor_until, "PROTECTIVE_POLICY_INVALID")


def policy_digest(policy):
    _require(type(policy) is ManagementPolicy, "PROTECTIVE_POLICY_INVALID")
    policy.__post_init__()
    return _digest("policy", asdict(policy))


@dataclass(frozen=True, kw_only=True)
class AuthorityFacts:
    """Explicit upstream findings, NEVER an authority issuance or cryptographic verification.

    None means that scope is absent. accepted/revoked and checked_at must come from
    the eventual independent verifier; an arbitrary caller can construct this
    model input, which therefore cannot be consumed as an execution capability.
    """
    policy_sha256: str
    checked_at: datetime
    issued_at: datetime
    accepted: bool
    revoked: bool
    entry_until: datetime | None
    reduce_until: datetime | None
    cancel_until: datetime | None
    monitor_until: datetime | None

    def __post_init__(self):
        _require(_hash(self.policy_sha256) and type(self.accepted) is bool and type(self.revoked) is bool,
                 "PROTECTIVE_AUTHORITY_FACTS_INVALID")
        _time(self.checked_at); _time(self.issued_at)
        for end in (self.entry_until, self.reduce_until, self.cancel_until, self.monitor_until):
            if end is not None:
                _time(end)
                _require(self.issued_at < end, "PROTECTIVE_AUTHORITY_FACTS_INVALID")


@dataclass(frozen=True, kw_only=True)
class ObservationFacts:
    """Eligibility results for this assessment instant, not raw or authenticated market data.

    strategy_ok includes data/program/review validity; risk_ok includes the
    independent risk-input checks. reduce_eligible is the existing applicable
    reducing gate's finding, including its particular halt policy. No risk
    threshold is calculated here. orders_known/no_pending_reduce are separate:
    no_pending_reduce excludes EVERY unresolved queued/unapplied outbox intent,
    reserved/dispatched/uncertain order and pending reconciliation, not just an
    active partial sell. A new evidence hash never clears that obligation.
    halted is the sticky ENTRY-halt finding. An applicable SD-O1 or other
    prohibition on automatic reductions MUST also make reduce_eligible False;
    mapping that prohibition only to halted would be an invalid integration.
    """
    policy_sha256: str
    evidence_sha256: str
    checked_at: datetime
    monitoring_ok: bool
    account_ok: bool
    market_ok: bool
    recording_ok: bool
    strategy_ok: bool
    risk_ok: bool
    orders_known: bool
    no_pending_reduce: bool
    entry_eligible: bool
    reduce_eligible: bool
    recovery_complete: bool
    halted: bool
    strategy_verdict: str
    risk_causes: tuple[str, ...]

    def __post_init__(self):
        _require(_hash(self.policy_sha256) and _hash(self.evidence_sha256), "PROTECTIVE_OBSERVATION_FACTS_INVALID")
        _time(self.checked_at)
        names = ("monitoring_ok", "account_ok", "market_ok", "recording_ok", "strategy_ok", "risk_ok",
                 "orders_known", "no_pending_reduce", "entry_eligible", "reduce_eligible", "recovery_complete", "halted")
        _require(all(type(getattr(self, name)) is bool for name in names)
                 and type(self.strategy_verdict) is str and self.strategy_verdict in _VERDICTS
                 and type(self.risk_causes) is tuple and all(type(item) is str for item in self.risk_causes)
                 and self.risk_causes == tuple(sorted(set(self.risk_causes)))
                 and set(self.risk_causes) <= _RISK_CAUSES, "PROTECTIVE_OBSERVATION_FACTS_INVALID")


@dataclass(frozen=True, kw_only=True)
class ManagementEvent:
    sequence: int
    previous_state_sha256: str
    at: datetime
    kind: str
    fault: str | None = None

    def __post_init__(self):
        _require(type(self.sequence) is int and 0 < self.sequence <= 2**63 - 1
                 and _hash(self.previous_state_sha256) and type(self.kind) is str and self.kind in _EVENTS,
                 "PROTECTIVE_EVENT_INVALID")
        _time(self.at)
        _require((self.kind == "fault" and type(self.fault) is str and self.fault in _FAULTS)
                 or (self.kind != "fault" and self.fault is None), "PROTECTIVE_EVENT_INVALID")


@dataclass(frozen=True, kw_only=True)
class ManagementState:
    """Immutable model state; last_event_at retains the last TRUSTED event time.

    A clock_unreliable event is sequenced and hashed but cannot advance that
    timestamp. It can remain None after initial clock faults. This preserves
    ordinary rollback rejection without locking recovery to an erroneous clock.
    """
    policy_sha256: str
    sequence: int
    last_event_sha256: str | None
    last_event_at: datetime | None
    phase: str
    strategy_verdict: str
    entry_blocked: bool
    deadline_seen: bool
    recovering: bool
    halted: bool
    renewal_request_id: str | None
    last_reduce_intent_id: str | None
    can_observe: bool
    can_evaluate_strategy: bool
    can_evaluate_risk: bool
    can_record: bool
    can_reduce: bool
    can_cancel: bool
    can_enter: bool
    reasons: tuple[str, ...]

    def __post_init__(self):
        _require(_hash(self.policy_sha256) and type(self.sequence) is int and 0 <= self.sequence <= 2**63 - 1
                 and type(self.phase) is str and self.phase in _PHASES
                 and type(self.strategy_verdict) is str and self.strategy_verdict in _VERDICTS,
                 "PROTECTIVE_STATE_INVALID")
        _require((self.sequence == 0 and self.last_event_at is None and self.last_event_sha256 is None)
                 or (self.sequence > 0 and _hash(self.last_event_sha256)),
                 "PROTECTIVE_STATE_INVALID")
        if self.last_event_at is not None:
            _time(self.last_event_at)
        names = ("entry_blocked", "deadline_seen", "recovering", "halted", "can_observe", "can_evaluate_strategy",
                 "can_evaluate_risk", "can_record", "can_reduce", "can_cancel", "can_enter")
        _require(all(type(getattr(self, name)) is bool for name in names)
                 and all(item is None or _hash(item) for item in (self.renewal_request_id, self.last_reduce_intent_id))
                 and type(self.reasons) is tuple and all(type(item) is str and item.isascii() for item in self.reasons),
                 "PROTECTIVE_STATE_INVALID")
        _require(not self.can_enter or not (self.entry_blocked or self.deadline_seen or self.recovering or self.halted),
                 "PROTECTIVE_STATE_INVALID")


@dataclass(frozen=True, kw_only=True)
class EffectIntent:
    """A proposed effect for later validation/persistence; never an order or executable capability."""
    kind: str
    intent_id: str
    reason: str
    evidence_sha256: str | None
    not_after: datetime | None

    def __post_init__(self):
        _require(type(self.kind) is str and self.kind in _EFFECTS and _hash(self.intent_id)
                 and type(self.reason) is str and self.reason.isascii()
                 and (self.evidence_sha256 is None or _hash(self.evidence_sha256)), "PROTECTIVE_EFFECT_INVALID")
        if self.not_after is not None:
            _time(self.not_after)


def state_digest(state):
    _require(type(state) is ManagementState, "PROTECTIVE_STATE_INVALID")
    state.__post_init__()
    return _digest("state", asdict(state))


def initial_state(policy):
    return ManagementState(policy_sha256=policy_digest(policy), sequence=0, last_event_sha256=None, last_event_at=None,
        phase="waiting_inputs", strategy_verdict="unavailable", entry_blocked=False, deadline_seen=False,
        recovering=False, halted=False, renewal_request_id=None, last_reduce_intent_id=None, can_observe=False,
        can_evaluate_strategy=False, can_evaluate_risk=False, can_record=False, can_reduce=False, can_cancel=False,
        can_enter=False, reasons=("PROTECTIVE_INPUTS_NOT_ASSESSED",))


def reduce_management(policy, previous, event, *, authority, observations):
    """Return immutable (state, intents) from explicit facts; perform no external effect.

    Missing authority/observations must be passed explicitly as None. Duplicate
    delivery of the last exact event returns no effects; earlier/out-of-order or
    rewritten events refuse. P2 must durably bind this state/effect result before
    any delivery. Its request intent is not a signed management approval. close
    closes management, never asserts that the account is flat. A separately
    eligible known-order cancellation may remain available while recovering;
    restart itself never produces a cancellation or reduction effect.
    """
    sha = policy_digest(policy)
    before = state_digest(previous)
    _require(previous.policy_sha256 == sha, "PROTECTIVE_POLICY_BINDING_MISMATCH")
    _require(type(event) is ManagementEvent, "PROTECTIVE_EVENT_INVALID")
    event.__post_init__()
    for value, cls in ((authority, AuthorityFacts), (observations, ObservationFacts)):
        if value is not None:
            _require(type(value) is cls, "PROTECTIVE_FACTS_REQUIRED")
            value.__post_init__()
            _require(value.policy_sha256 == sha, "PROTECTIVE_POLICY_BINDING_MISMATCH")
            _require(value.checked_at == event.at, "PROTECTIVE_FACTS_NOT_CURRENT")
    # Re-delivery is idempotent only for the same event AND the same explicit facts. A changed grant/assessment
    # is a new event, never an excuse to reuse an old state with different authority or source conclusions.
    event_sha = _digest("event", {"event": asdict(event),
                                 "authority": None if authority is None else asdict(authority),
                                 "observations": None if observations is None else asdict(observations)})
    if event.sequence == previous.sequence:
        _require(event_sha == previous.last_event_sha256, "PROTECTIVE_EVENT_REWRITTEN")
        return previous, ()
    _require(event.sequence == previous.sequence + 1 and event.previous_state_sha256 == before,
             "PROTECTIVE_EVENT_SEQUENCE_INVALID")
    clock_unreliable = event.fault == "clock_unreliable"
    _require(clock_unreliable or previous.last_event_at is None or event.at >= previous.last_event_at,
             "PROTECTIVE_CLOCK_ROLLBACK")

    effects, reasons = [], []
    def effect(kind, reason, *, evidence=None, until=None, stable=None):
        identity = stable or _digest("effect", {"event": event_sha, "kind": kind, "reason": reason,
                                               "evidence": evidence, "not_after": until})
        effects.append(EffectIntent(kind=kind, intent_id=identity, reason=reason,
                                    evidence_sha256=evidence, not_after=until))
        return identity

    def scope(name):
        until = getattr(authority, name + "_until") if authority is not None else None
        return (event.fault != "clock_unreliable" and authority is not None
                and authority.accepted and not authority.revoked and until is not None
                and authority.issued_at <= event.at < until)

    closed = previous.phase == "closed" or event.kind == "close"
    deadline = previous.deadline_seen or (event.fault != "clock_unreliable" and event.at >= policy.holding_deadline)
    _require(event.kind != "deadline" or event.at >= policy.holding_deadline, "PROTECTIVE_DEADLINE_NOT_DUE")
    blocked = previous.entry_blocked or deadline or closed or event.kind in ("fault", "restart")
    halted = previous.halted or (observations is not None and observations.halted)
    blocked = blocked or halted
    recovering = previous.recovering or event.kind == "restart"
    renewal = previous.renewal_request_id
    if deadline and renewal is None and not closed:
        renewal = effect("request_management_approval", "PROTECTIVE_DEADLINE_RENEWAL_REQUIRED",
                         stable=_digest("renewal", {"policy": sha, "deadline": policy.holding_deadline}))
    if blocked and not previous.entry_blocked:
        effect("block_entry", "PROTECTIVE_ENTRY_BLOCKED")
    if event.kind == "fault" and not closed:
        reasons.append("PROTECTIVE_FAULT_" + event.fault.upper())
        effect("notify", reasons[-1])
    if event.kind == "restart" and not closed:
        reasons.append("PROTECTIVE_RECONCILIATION_REQUIRED")
        effect("reconcile", reasons[-1])

    fact = observations
    monitor = not closed and event.at < policy.monitor_until and scope("monitor")
    observe = monitor and fact is not None and fact.monitoring_ok
    record = (not closed and fact is not None and fact.recording_ok
              and event.fault not in ("storage_unavailable", "clock_unreliable"))
    if event.kind == "recovery_complete" and not closed:
        _require(fact is not None and fact.recovery_complete and fact.account_ok and fact.orders_known and record,
                 "PROTECTIVE_RECOVERY_UNVERIFIED")
        recovering = False
    account = fact is not None and fact.account_ok and event.fault != "account_unavailable"
    strategy = observe and not recovering and account and fact.market_ok and fact.strategy_ok
    risk = observe and not recovering and account and fact.risk_ok
    cancel = (not closed and scope("cancel") and account and fact.orders_known and record)
    reduce = (risk and scope("reduce") and fact.market_ok and fact.orders_known and fact.no_pending_reduce
              and record and fact.reduce_eligible)
    if event.kind == "entry_reauthorized" and not closed:
        _require(not deadline and not halted and not recovering and scope("entry") and strategy and risk
                 and fact.strategy_verdict == "hold" and record and fact.orders_known
                 and fact.no_pending_reduce and fact.entry_eligible,
                 "PROTECTIVE_ENTRY_REAUTHORIZATION_UNVERIFIED")
        blocked = False
    enter = (not blocked and not halted and strategy and risk and scope("entry") and record
             and fact.strategy_verdict == "hold" and fact.orders_known and fact.no_pending_reduce
             and fact.entry_eligible)
    verdict = fact.strategy_verdict if strategy else "unavailable"
    # Fault/restart are facts about the operation, not a surviving model verdict.
    if event.kind in ("fault", "restart"):
        verdict = "unavailable"
        strategy = reduce = enter = False
    if risk and fact.risk_causes and not reduce:
        reasons.append("PROTECTIVE_KNOWN_RISK_REDUCTION_UNAVAILABLE")
    if strategy and verdict == "sell" and not reduce:
        reasons.append("PROTECTIVE_STRATEGY_REDUCTION_UNAVAILABLE")
    last_reduce = previous.last_reduce_intent_id
    if event.kind == "assessment" and reduce:
        causes = (("strategy_sell",) if strategy and verdict == "sell" else ()) + fact.risk_causes
        if causes:
            until = min(authority.reduce_until, authority.monitor_until, policy.monitor_until)
            intent = _digest("reduce-consideration", {"policy": sha, "evidence": fact.evidence_sha256,
                              "causes": causes, "not_after": until})
            if intent != last_reduce:
                last_reduce = effect("consider_reduce", "+".join(causes), evidence=fact.evidence_sha256,
                                     until=until, stable=intent)
    if not monitor and not closed:
        reasons.append("PROTECTIVE_MONITORING_NOT_AUTHORIZED_OR_ENDED")
    if halted:
        reasons.append("PROTECTIVE_ENTRY_HALT_LATCHED")
    if deadline:
        reasons.append("PROTECTIVE_DEADLINE_RENEWAL_REQUIRED")
    if fact is None:
        reasons.append("PROTECTIVE_OBSERVATION_FACTS_REQUIRED")
    elif not strategy:
        reasons.append("PROTECTIVE_STRATEGY_UNAVAILABLE")
    if closed:
        phase = "closed"
    elif not monitor:
        phase = "owner_action_required"
    elif recovering:
        phase = "recovering"
    elif halted:
        phase = "halted"
    elif event.kind == "fault" or not risk or not record:
        phase = "waiting_inputs"
    elif deadline:
        phase = "renewal_pending"
    elif (any(item.kind == "consider_reduce" for item in effects)
          or (fact is not None and fact.orders_known and not fact.no_pending_reduce)):
        phase = "exit_pending"
    else:
        phase = "monitoring"
    state = ManagementState(policy_sha256=sha, sequence=event.sequence, last_event_sha256=event_sha,
        last_event_at=previous.last_event_at if clock_unreliable else event.at,
        phase=phase, strategy_verdict=verdict, entry_blocked=blocked or halted,
        deadline_seen=deadline, recovering=recovering, halted=halted, renewal_request_id=renewal,
        last_reduce_intent_id=last_reduce, can_observe=observe, can_evaluate_strategy=strategy,
        can_evaluate_risk=risk, can_record=record, can_reduce=reduce, can_cancel=cancel, can_enter=enter,
        reasons=tuple(sorted(set(reasons))))
    return state, tuple(effects)
