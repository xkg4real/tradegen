"""Explicit, synchronous launch orchestration; importing this module does nothing.

The default mode only diagnoses supplied observations. Rehearsal requires a
separate explicit state root and exact DryRunAdapters. Controlled operation must
be constructed explicitly by the owner with providers, reviewed strategy code,
and an actual E2 prepared session; there are no credentials or live defaults.
"""
from __future__ import annotations

import base64
from contextlib import contextmanager
from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from decimal import Decimal, Inexact, localcontext
import hashlib
import json
from pathlib import Path
import re
from threading import Lock
from typing import Callable

from core.isolation import checked_target, state_root
from core.compliance.model import Universe
from execution_accounts.model import AccountEvidence
from execution_control.capability import digest
from execution_control.controller import AccountObservation, Controller
from execution_control.dry_run import DryRunAdapter
from execution_control.model import Order, order_digest, rules_digest, validate_order
from execution_control.risk import evaluate
from execution_control.session import PreparedSession, prepare_session
from execution_control.universe_odds import registered_batch
from execution_launch.profile import (LaunchProfile, preflight_profile, profile_digest,
    profile_contract_digest, rule_terms_digest, risk_policy)
from execution_launch.strategy import assess_strategy
from execution_launch.instrument_refresh import (validate_renewal, rules_binding_matches,
                                                  validate_observed_order)

_ACTIVE = frozenset({'RESERVED', 'UNKNOWN', 'ACKNOWLEDGED', 'PARTIAL', 'CANCEL_REQUESTED'})
_LIVE = _ACTIVE | {'DISPATCHING'}
_HASH = re.compile(r'[0-9a-f]{64}')
_SIGNAL = re.compile(r'[A-Za-z0-9_.:/-]{1,128}')


class RunnerError(ValueError):
    """Stable diagnostic codes; provider exceptions never become public text."""


def _require(ok, code):
    if not ok:
        raise RunnerError(code)


def _instant(value):
    _require(type(value) is datetime and value.utcoffset() is not None, 'RUNNER_AWARE_TIME_REQUIRED')


def _positive(value):
    return type(value) is Decimal and value.is_finite() and value > 0



def active(state) -> bool:
    """True while an order can still fill, including an interrupted dispatch."""
    return state.status in _LIVE


def dust(position, minimum) -> bool:
    """An exact nonnegative marked holding below the market minimum; zero marks are dust.

    This classifies already validated account evidence; it does not authorize a
    sale, remove the position, or prove an unavailable mark is really zero.
    """
    _require(_positive(minimum) and type(position.units) is Decimal and position.units.is_finite()
             and position.units >= 0 and type(position.price) is Decimal and position.price.is_finite()
             and position.price >= 0, 'RUNNER_HOLDING_INVALID')
    with localcontext() as numeric:
        numeric.prec = 2048
        numeric.traps[Inexact] = True
        return position.units * position.price < minimum


def flat_in(symbol, positions, states, *, asof, minimum) -> bool:
    """No non-dust holding or unsettled order in this symbol at account time.

    Unknown-symbol live orders block switching too. A terminal order updated at
    or after the account snapshot might contain a fill that snapshot has not
    observed, so it also prevents declaring the account flat.
    """
    _instant(asof)
    return (not any(p.symbol == symbol and not dust(p, minimum) for p in positions)
            and not any((active(s) and s.symbol in (symbol, None))
                        or (s.symbol == symbol and s.updated_at is not None and s.updated_at >= asof)
                        for s in states))


@dataclass(frozen=True, kw_only=True)
class Quote:
    venue: str
    market: str
    symbol: str
    bid: Decimal
    ask: Decimal
    asof: datetime
    source_sha256: str


@dataclass(frozen=True, kw_only=True)
class Signal:
    """A stable decision key must identify the same decision across restarts."""
    signal_id: str
    action: str  # hold, entry, exit
    quantity: Decimal = Decimal(0)
    limit_price: Decimal = Decimal(0)
    decision_state: str | None = None
    decision_cause: str | None = None
    execution_block_reasons: tuple[str, ...] = ()


def _signal_metadata(signal):
    """Preserve a model verdict separately from execution availability; no grant."""
    _require(type(signal) is Signal and type(signal.signal_id) is str
             and _SIGNAL.fullmatch(signal.signal_id) is not None
             and type(signal.action) is str and signal.action in ('entry', 'exit', 'hold'),
             'RUNNER_SIGNAL_INVALID')
    states = {'long_target': ('trend_above',), 'cash_target': ('trend_not_above', 'always_cash'),
              'warmup': ('insufficient_history',), 'unavailable': ('input_unavailable',)}
    blocked = signal.execution_block_reasons
    _require(type(blocked) is tuple and len(blocked) <= 4
             and all(type(reason) is str and reason in ('MANAGED_DEADLINE_REACHED',
                 'MANAGED_AUTHORITY_UNAVAILABLE', 'MANAGED_DECISION_UNAVAILABLE',
                 'MANAGED_ORDER_BELOW_MINIMUM') for reason in blocked)
             and len(set(blocked)) == len(blocked), 'RUNNER_SIGNAL_METADATA_INVALID')
    if signal.decision_state is None:
        _require(signal.decision_cause is None and not blocked, 'RUNNER_SIGNAL_METADATA_INVALID')
    else:
        state, cause = signal.decision_state, signal.decision_cause
        _require(type(state) is str and state in states and type(cause) is str and cause in states[state],
                 'RUNNER_SIGNAL_METADATA_INVALID')
        _require((signal.action != 'exit' or state == 'cash_target')
                 and (signal.action != 'entry' or state == 'long_target')
                 and (state != 'unavailable' or 'MANAGED_DECISION_UNAVAILABLE' in blocked),
                 'RUNNER_SIGNAL_METADATA_INVALID')
    return dict(decision_state=signal.decision_state, decision_cause=signal.decision_cause,
                execution_block_reasons=blocked)


@dataclass(frozen=True, kw_only=True)
class DecisionInput:
    now: datetime
    profile: LaunchProfile
    quote: Quote
    account: AccountObservation


@dataclass(frozen=True, kw_only=True)
class StrategyDriver:
    """An audited injection boundary, never a Python sandbox or hash attestation.

    artifact contains the reviewed source/package manifest. parameters_json is a
    canonical object with decimal parameters encoded as strings. The trusted
    implementation verifier must establish that this exact callback implements
    the tested artifact and parameters. The callback receives the exact canonical
    parameter string as its second argument.
    """
    callback: Callable
    artifact: bytes
    parameters_json: str


def program_digest(driver: StrategyDriver) -> str:
    _require(type(driver) is StrategyDriver and callable(driver.callback), 'RUNNER_DRIVER_REQUIRED')
    _require(type(driver.artifact) is bytes and 0 < len(driver.artifact) <= 1048576,
             'RUNNER_ARTIFACT_INVALID')
    _require(type(driver.parameters_json) is str and len(driver.parameters_json) <= 16384,
             'RUNNER_PARAMETERS_INVALID')
    try:
        def invalid(value):
            raise ValueError('invalid parameter number')
        body = json.loads(driver.parameters_json, parse_float=invalid, parse_constant=invalid)
        canonical = json.dumps(body, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False)
        _require(type(body) is dict and canonical == driver.parameters_json, 'RUNNER_PARAMETERS_FORMAT_INVALID')
    except (ValueError, TypeError, RecursionError):
        raise RunnerError('RUNNER_PARAMETERS_INVALID') from None
    return digest({'artifact_sha256': hashlib.sha256(driver.artifact).hexdigest(), 'parameters': body})


@dataclass(frozen=True, kw_only=True)
class EvidencePackage:
    protocol: object
    result: object
    review_verifier: Callable | None = None


@dataclass(frozen=True, kw_only=True)
class ImplementationBinding:
    program_digest: str
    protocol_digest: str
    evidence_digest: str
    profile_contract_digest: str
    rule_terms_digest: str


@dataclass(frozen=True, kw_only=True)
class ImplementationReceipt:
    binding_digest: str
    callback: Callable
    audit_sha256: str
    reviewed_at: datetime
    expires_at: datetime


def _assess(profile, evidence, driver, implementation_verifier, now):
    _require(type(evidence) is EvidencePackage, 'RUNNER_STRATEGY_EVIDENCE_REQUIRED')
    code = program_digest(driver)
    _require(code == profile.strategy_code_sha256, 'RUNNER_PROGRAM_PROFILE_MISMATCH')
    _require(evidence.protocol.quote_currency == 'KRW'
             and evidence.protocol.initial_cash_quote == profile.policy.initial_equity,
             'RUNNER_RESEARCH_CAPITAL_MISMATCH')
    assessment = assess_strategy(evidence.protocol, evidence.result,
        profile_contract_digest=profile_contract_digest(profile),
        rule_terms_digest=rule_terms_digest(profile.instrument_rules,
                                            universe_rule_sha256=profile.universe_rule_sha256),
        strategy_code_sha256=code, now=now, review_verifier=evidence.review_verifier)
    _require(assessment.strategy_id == profile.strategy_id, 'RUNNER_STRATEGY_ID_MISMATCH')
    binding = ImplementationBinding(program_digest=code, protocol_digest=assessment.protocol_digest,
        evidence_digest=assessment.evidence_digest, profile_contract_digest=assessment.profile_contract_digest,
        rule_terms_digest=assessment.rule_terms_digest)
    _require(callable(implementation_verifier), 'RUNNER_IMPLEMENTATION_REVIEW_REQUIRED')
    try:
        receipt = implementation_verifier(binding, driver)
    except Exception:
        raise RunnerError('RUNNER_IMPLEMENTATION_REVIEW_FAILED') from None
    _require(type(receipt) is ImplementationReceipt, 'RUNNER_IMPLEMENTATION_REVIEW_UNVERIFIED')
    _instant(receipt.reviewed_at); _instant(receipt.expires_at)
    _require(receipt.binding_digest == digest(binding) and receipt.callback is driver.callback
             and type(receipt.audit_sha256) is str and _HASH.fullmatch(receipt.audit_sha256) is not None
             and receipt.reviewed_at <= now < receipt.expires_at,
             'RUNNER_IMPLEMENTATION_REVIEW_UNVERIFIED')
    return assessment, binding


def _label(binding):
    # 31 base64 characters retain 186 bits; the complete digests remain in the
    # LaunchSession wrapper and are recomputed on every entry.
    raw = bytes.fromhex(digest(binding))
    return 'L' + base64.urlsafe_b64encode(raw).decode('ascii')[:31]


@dataclass(frozen=True, kw_only=True)
class LaunchSession:
    prepared: PreparedSession
    profile_digest: str
    binding: ImplementationBinding


def prepare_launch_session(*, profile, evidence, driver, implementation_verifier,
                           journal, selected_plan, inputs, positions, now,
                           selection_seed_hex, clock, positions_asof, expires_at=None,
                           universe_batch=None) -> LaunchSession:
    """Prepare fresh odds with a derived label BEFORE the owner signs its ID.

    This writes only the existing preparation event. It does not sign, arm, fetch
    account data or send an order. The owner must subsequently use the returned
    actual PreparedSession object, not reconstruct a serialized copy.
    """
    _instant(now); _instant(positions_asof)
    _require(callable(clock), "RUNNER_PREPARATION_CLOCK_REQUIRED")
    started = clock()
    _instant(started)
    _require(preflight_profile(profile, now=started).profile_complete, 'RUNNER_PROFILE_INCOMPLETE')
    assessment, binding = _assess(profile, evidence, driver, implementation_verifier, started)
    _require(assessment.research_review_ready, 'RUNNER_STRATEGY_NOT_QUALIFIED')
    symbol = (profile.symbol.split('-')[1] if profile.venue == 'upbit' else
              profile.symbol.split('-')[0] if profile.venue == 'okx' else profile.symbol)
    if profile.universe_rule_sha256 is None:
        scoped = universe_batch is None and (selected_plan.leg.venue, selected_plan.leg.symbol) == (profile.venue, symbol)
    else:
        # The reviewed template may be any coin in this batch, not only the
        # currently selected trade coin. prepare_session verifies actual issuance.
        scoped = (universe_batch is not None and selected_plan.leg.venue == 'upbit'
                  and 'KRW-' + selected_plan.leg.symbol in {coin.market for coin in universe_batch.coins})
    _require(scoped, 'RUNNER_SELECTED_PLAN_SCOPE_MISMATCH')
    _require(0 < selected_plan.stake_krw <= profile.policy.initial_equity,
             'RUNNER_SELECTED_STAKE_EXCEEDS_RESEARCH_CAPITAL')
    def completion_check(stamp):
        _require(preflight_profile(profile, now=stamp).profile_complete, 'RUNNER_PROFILE_INCOMPLETE')
        receipts = []

        def source_receipt(review_binding):
            receipt = evidence.review_verifier(review_binding)
            receipts.append(receipt)
            return receipt

        def implementation_receipt(review_binding, actual_driver):
            receipt = implementation_verifier(review_binding, actual_driver)
            receipts.append(receipt)
            return receipt

        # _assess validates BOTH exact receipt types, bindings, callback and
        # dates before their deadlines are retained. No parser-only timestamp
        # or callback boolean can extend the final commit window.
        current, current_binding = _assess(profile, replace(evidence, review_verifier=source_receipt),
                                          driver, implementation_receipt, stamp)
        _require(current.research_review_ready and current_binding == binding and len(receipts) == 2,
                 'RUNNER_PREPARATION_REVIEW_CHANGED')
        return min(receipt.expires_at for receipt in receipts)

    prepared = prepare_session(journal=journal, session_id=_label(binding), selected_plan=selected_plan,
        inputs=inputs, positions=positions, policy=risk_policy(profile), instrument_rules=profile.instrument_rules,
        now=now, selection_seed_hex=selection_seed_hex, account_scope=profile.account_scope,
        market=profile.market, quote_currency=profile.quote_currency, expires_at=expires_at,
        universe_batch=universe_batch,
        clock=clock, positions_asof=positions_asof, completion_check=completion_check)
    return LaunchSession(prepared=prepared, profile_digest=profile_digest(profile), binding=binding)


@dataclass(frozen=True, kw_only=True)
class TickResult:
    mode: str
    status: str
    reasons: tuple[str, ...] = ()
    client_id: str = ''
    order_status: str = ''
    reconciled_orders: int = 0
    protective_action_needed: bool = False
    decision_state: str | None = None
    decision_cause: str | None = None
    execution_block_reasons: tuple[str, ...] = ()


class Runner:
    """One tick at a time, using the caller's clock and explicit providers.

    Source/review verifiers and strategy callbacks are trusted code supplied by
    the operator. There is no hidden scheduler, retry worker or credential path.
    A Runner stops after an unexpected control error; restart still reconciles
    durable state before considering a new entry.
    """
    def __init__(self, *, profile, quote_provider, account_provider, evidence=None,
                 driver=None, implementation_verifier=None, mode='observe', controller=None,
                 launch_session=None, isolated_state_root=None, clock=None, deadline_record=None):
        _require(mode in ('observe', 'rehearsal', 'controlled'), 'RUNNER_MODE_INVALID')
        _require(type(profile) is LaunchProfile, 'RUNNER_PROFILE_REQUIRED')
        _require(callable(quote_provider) and callable(account_provider), 'RUNNER_PROVIDERS_REQUIRED')
        self.profile, self.quote_provider, self.account_provider = profile, quote_provider, account_provider
        self.evidence, self.driver, self.implementation_verifier = evidence, driver, implementation_verifier
        self.mode, self.controller, self.launch_session = mode, controller, launch_session
        self._profile_digest = profile_digest(profile)
        self._namespace = 'lr' + profile_contract_digest(profile)[:24] + '-'
        self._lock, self._last_now, self._stopped = Lock(), None, False
        self._isolated_state_root = isolated_state_root
        self._clock, self._deadline_record, self._last_carry_clock = clock, deadline_record, None
        if evidence is not None and getattr(getattr(evidence, 'protocol', None), 'schema_version', None) == 2:
            _require(callable(clock), 'RUNNER_CARRY_CLOCK_REQUIRED')
        if mode != 'observe':
            self._controller_boundary()

    def _controller_boundary(self):
        _require(not (self.mode == 'controlled' and self.evidence is not None
                      and getattr(getattr(self.evidence, 'protocol', None), 'schema_version', None) == 2),
                 'RUNNER_CARRY_CONTROLLED_UNSUPPORTED')
        c = self.controller
        _require(type(c) is Controller and c.account_provider is self.account_provider,
                 'RUNNER_CONTROLLER_PROVIDER_MISMATCH')
        _require(digest(c.policy) == digest(risk_policy(self.profile)), 'RUNNER_CONTROLLER_POLICY_MISMATCH')
        if self.mode == 'rehearsal':
            _require(bool(c.adapters) and all(type(a) is DryRunAdapter for a in c.adapters.values()),
                     'RUNNER_REHEARSAL_REQUIRES_DRY_ADAPTERS')
            _require(self._isolated_state_root is not None, 'RUNNER_ISOLATED_STATE_REQUIRED')
            root = checked_target(Path(self._isolated_state_root).absolute(), 'rehearsal state')
            _require(not root.is_relative_to(Path.home() / '.tradegen') and state_root().absolute() == root
                     and c.journal._base == root, 'RUNNER_REHEARSAL_STATE_MISMATCH')

    def refresh_instrument_rules(self, renewal, *, now, account=None):
        """Apply an issued same-contract snapshot without changing owner authority.

        Coordinator callers serialize this with account/quote work. This lock
        also refuses concurrent ticks; the original prepared object is retained.
        """
        _instant(now)
        _require(self._lock.acquire(blocking=False), 'RUNNER_CONCURRENT_TICK_REFUSED')
        try:
            # Stop latches entries; same-contract renewal remains necessary for exits.
            _require(self._last_now is None or now >= self._last_now, 'RUNNER_CLOCK_ROLLBACK')
            _require(profile_digest(self.profile) == self._profile_digest, 'RUNNER_PROFILE_MUTATED')
            current = validate_renewal(renewal, previous_profile=self.profile, now=now)
            if current.symbol != self.profile.symbol:
                # A renewal's source authority cannot prove this account flat.
                # Recheck the coordinator's current account and durable orders
                # under the same runner lock immediately before applying it.
                _require(type(account) is AccountEvidence and type(self.controller) is Controller
                         and (account.venue, account.account_scope, account.execution_quote) ==
                             (self.profile.venue, self.profile.account_scope, self.profile.quote_currency)
                         and type(account.observed_at) is datetime and account.observed_at.utcoffset() is not None
                         and timedelta(0) <= now-account.observed_at <= timedelta(seconds=30)
                         and flat_in(self.profile.symbol, account.positions, self.controller.states(),
                                     asof=account.observed_at,
                                     minimum=self.profile.instrument_rules.min_notional_krw),
                         'RUNNER_UNIVERSE_NOT_FLAT')
            launch = self.launch_session
            if launch is not None:
                _require(type(launch) is LaunchSession
                         and launch.profile_digest == self._profile_digest,
                         'RUNNER_SESSION_BINDING_MISMATCH')
                _require(rules_binding_matches(launch.prepared.rules_digest, current.instrument_rules,
                         account_scope=current.account_scope, now=now), 'RUNNER_SESSION_BINDING_MISMATCH')
                launch = replace(launch, profile_digest=profile_digest(current))
            self.profile, self._profile_digest, self.launch_session = current, profile_digest(current), launch
            self._last_now = now
            return current
        finally:
            self._lock.release()

    @property
    def stopped(self):
        return self._stopped

    def stop(self):
        """Prevent future tick work; this does not pretend to cancel venue orders."""
        self._stopped = True

    def _observations(self, now):
        quote, account = self.quote_provider(now), self.account_provider(now)
        _require(type(quote) is Quote and type(account) is AccountObservation, 'RUNNER_OBSERVATIONS_REQUIRED')
        _instant(quote.asof); _instant(account.asof); _instant(account.server_time)
        _require((quote.venue, quote.market, quote.symbol) ==
                 (self.profile.venue, self.profile.market, self.profile.symbol), 'RUNNER_QUOTE_SCOPE_MISMATCH')
        _require(_positive(quote.bid) and _positive(quote.ask) and quote.bid <= quote.ask
                 and type(quote.source_sha256) is str and _HASH.fullmatch(quote.source_sha256) is not None,
                 'RUNNER_QUOTE_INVALID')
        _require(timedelta(0) <= now-quote.asof <= timedelta(seconds=10), 'RUNNER_QUOTE_STALE_OR_FUTURE')
        _require(timedelta(0) <= now-account.asof <= timedelta(seconds=30)
                 and abs(now-account.server_time) <= timedelta(seconds=60)
                 and account.risk.asof == account.asof, 'RUNNER_ACCOUNT_STALE_OR_FUTURE')
        _require(account.account_scopes.get(self.profile.venue) == self.profile.account_scope
                 and account.no_credit is True and account.risk.data_complete is True
                 and account.risk.external_flows_known is True, 'RUNNER_ACCOUNT_INCOMPLETE_OR_MISMATCHED')
        return quote, account

    def _order(self, signal, account, now=None):
        _signal_metadata(signal)
        _require(not signal.execution_block_reasons, 'RUNNER_SIGNAL_EXECUTION_BLOCKED')
        if signal.action == 'hold':
            return None
        _require(_positive(signal.quantity) and _positive(signal.limit_price), 'RUNNER_SIGNAL_AMOUNTS_INVALID')
        side = 'buy' if signal.action == 'entry' else 'sell'
        identity = digest({'profile_contract_digest': profile_contract_digest(self.profile),
                           'signal_id': signal.signal_id, 'side': side})
        rate = account.quote_rates_krw.get((self.profile.venue, self.profile.account_scope, self.profile.quote_currency))
        _require(_positive(rate), 'RUNNER_ACCOUNT_FX_REQUIRED')
        order = Order(client_id=self._namespace+identity[:37], account_scope=self.profile.account_scope,
            venue=self.profile.venue, market=self.profile.market, symbol=self.profile.symbol, side=side,
            quantity=signal.quantity, limit_price=signal.limit_price, quote_krw=rate,
            time_in_force=self.profile.time_in_force)
        # Private construction callers may use the supplied observation instant.
        # Dispatch always rechecks the actual current time at the controller boundary.
        validate_observed_order(order, self.profile.instrument_rules, now=account.asof if now is None else now)
        return order

    def _carry_execution_time(self, now, metadata):
        """Fresh runtime deadline gate, never a management authorization issuer.

        A pre-E tick may finish after E. The clock is an explicit composition
        dependency; the deadline comes from the actual issued factory instance,
        not the historical study end or a caller's extra timestamp field.
        """
        if getattr(getattr(self.evidence, 'protocol', None), 'schema_version', None) != 2:
            return now, ()
        from execution_launch.driver import fixed_carry_deadline
        deadline = fixed_carry_deadline(self.driver)
        _require(callable(self._clock), 'RUNNER_CARRY_CLOCK_REQUIRED')
        try:
            fresh = self._clock()
            _instant(fresh)
        except Exception:
            raise RunnerError('RUNNER_CARRY_CLOCK_UNAVAILABLE') from None
        _require(fresh >= now and (self._last_carry_clock is None or fresh >= self._last_carry_clock),
                 'RUNNER_CLOCK_ROLLBACK')
        self._last_carry_clock = fresh
        if fresh < deadline:
            return fresh, ()
        reasons = ('MANAGED_DEADLINE_REACHED',)
        if metadata.get('decision_state') == 'cash_target':
            reasons += ('MANAGED_AUTHORITY_UNAVAILABLE',)
        try:
            recorded = callable(self._deadline_record) and self._deadline_record(fresh) is True
        except Exception:
            recorded = False
        if not recorded:
            reasons += ('MANAGED_DEADLINE_STATE_UNAVAILABLE',)
        return fresh, reasons

    def _session(self, binding, now):
        launch = self.launch_session
        _require(type(launch) is LaunchSession and type(launch.prepared) is PreparedSession,
                 'RUNNER_ACTUAL_PREPARED_SESSION_REQUIRED')
        p = launch.prepared
        _require(launch.profile_digest == profile_digest(self.profile) and launch.binding == binding
                 and p.session_id.rpartition('-')[0] == _label(binding)
                 and p.policy_digest == digest(risk_policy(self.profile))
                 and rules_binding_matches(p.rules_digest, self.profile.instrument_rules,
                                           account_scope=self.profile.account_scope, now=now)
                 and (p.venue, p.account_scope, p.market, p.quote_currency) ==
                     (self.profile.venue, self.profile.account_scope, self.profile.market, self.profile.quote_currency)
                 and p.prepared_at <= now < p.expires_at
                 and self.controller.session_provider(p.session_id) is p,
                 'RUNNER_SESSION_BINDING_MISMATCH')
        return p.session_id  # E2 verifies registry, object integrity, signed owner and journal next.

    def _universe_reasons(self, entry_allow, universe, now):
        """Ordinary unavailable entry inputs block this tick without latching stop."""
        reasons = ()
        if type(entry_allow) is not frozenset or self.profile.symbol not in entry_allow:
            reasons += ('RUNNER_UNIVERSE_ENTRY_NOT_ALLOWED',)
        if (type(universe) is not Universe or type(universe.valid_from) is not datetime
                or universe.valid_from.utcoffset() is None or type(universe.valid_until) is not datetime
                or universe.valid_until.utcoffset() is None
                or not universe.valid_from <= now < universe.valid_until
                or universe.rule_sha256 != self.profile.universe_rule_sha256):
            reasons += ('RUNNER_UNIVERSE_SNAPSHOT_MISMATCH',)
        return reasons

    def _universe_batch(self, universe):
        """Called after _session: use its issued batch for this snapshot and coin."""
        bound = self.launch_session.prepared.universe_batch_digest
        batch = registered_batch(bound) if type(bound) is str else None
        _require(batch is not None and batch.snapshot_sha256 == universe.snapshot_sha256,
                 'RUNNER_UNIVERSE_SNAPSHOT_MISMATCH')
        _require(self.profile.symbol in {coin.market for coin in batch.coins}, 'RUNNER_UNIVERSE_COIN_NOT_IN_BATCH')

    def _exit_session_id(self):
        # The owner context requires a nonempty label even for reducing sells.
        # An exit needs no fresh preparation/arm; retain an available session's
        # context, or use a deterministic protective context when none exists.
        launch = self.launch_session
        if (type(launch) is LaunchSession and type(launch.prepared) is PreparedSession
                and type(launch.prepared.session_id) is str and launch.prepared.session_id):
            return launch.prepared.session_id
        return 'launch-exit-' + profile_contract_digest(self.profile)[:24]

    def _reconcile(self, now):
        count = 0
        for state in self.controller.states():
            if state.status == 'RESERVED':
                if state.client_id.startswith(self._namespace):
                    self.controller.cancel(state.client_id, now=now)
            elif state.status in _ACTIVE:
                self.controller.reconcile(state.client_id, now=now)
                count += 1
        return count

    def tick(self, *, now, entry_allow=None) -> TickResult:
        _instant(now)
        if self._stopped:
            return TickResult(mode=self.mode, status='stopped', reasons=('RUNNER_STOPPED',))
        _require(self._lock.acquire(blocking=False), 'RUNNER_CONCURRENT_TICK_REFUSED')
        metadata = {}
        try:
            _require(self._last_now is None or now >= self._last_now, 'RUNNER_CLOCK_ROLLBACK')
            self._last_now = now
            _require(profile_digest(self.profile) == self._profile_digest, 'RUNNER_PROFILE_MUTATED')
            reconciled = 0
            risk = None
            if self.mode != 'observe':
                self._controller_boundary()
                # A failed account/quote/research refresh must never cause a new
                # create retry; reconcile durable orders first on every tick.
                reconciled = self._reconcile(now)
                risk = self.controller.observe(now=now)
            report = preflight_profile(self.profile, now=now)
            _require(report.profile_complete, 'RUNNER_PROFILE_INCOMPLETE')
            quote, account = self._observations(now)
            risk = risk if risk is not None else evaluate(risk_policy(self.profile), account.risk, now=now)
            assessment, binding = _assess(self.profile, self.evidence, self.driver,
                                          self.implementation_verifier, now)
            signal = self.driver.callback(DecisionInput(now=now, profile=self.profile, quote=quote, account=account),
                                          self.driver.parameters_json)
            metadata = _signal_metadata(signal)
            execution_now, deadline_reasons = self._carry_execution_time(now, metadata)
            blocked = tuple(dict.fromkeys(signal.execution_block_reasons + deadline_reasons))
            if blocked:
                metadata['execution_block_reasons'] = blocked
                return TickResult(mode=self.mode, status='blocked',
                    reasons=assessment.reasons + blocked,
                    reconciled_orders=reconciled, protective_action_needed=risk.protective_action_needed,
                    **metadata)
            order = self._order(signal, account, now)
            if order is None:
                return TickResult(mode=self.mode, status='hold', reasons=assessment.reasons,
                    reconciled_orders=reconciled, protective_action_needed=risk.protective_action_needed, **metadata)
            reasons = assessment.reasons if order.side == 'buy' else ()
            if order.side == 'buy' and risk.new_entry_blocked:
                reasons += ('RUNNER_RISK_BLOCKS_ENTRY',)
            universe_buy = order.side == 'buy' and self.profile.universe_rule_sha256 is not None
            if universe_buy:
                reasons += self._universe_reasons(entry_allow, risk.universe, now)
            if reasons:
                return TickResult(mode=self.mode, status='blocked', reasons=reasons, client_id=order.client_id,
                    reconciled_orders=reconciled, protective_action_needed=risk.protective_action_needed, **metadata)
            if self.mode == 'observe':
                return TickResult(mode=self.mode, status='observed', reasons=('RUNNER_OBSERVATION_ONLY',),
                    client_id=order.client_id, protective_action_needed=risk.protective_action_needed, **metadata)
            if self.stopped:
                return TickResult(mode=self.mode, status='stopped', reasons=('RUNNER_STOPPED',), **metadata)
            session_id = self._session(binding, now) if order.side == 'buy' else self._exit_session_id()
            if universe_buy:
                self._universe_batch(risk.universe)
            states = self.controller.states()
            existing = next((s for s in states if s.client_id == order.client_id), None)
            if existing is not None:
                _require(existing.order_digest == order_digest(order), 'RUNNER_DECISION_CHANGED')
                return TickResult(mode=self.mode, status='existing', client_id=existing.client_id,
                    order_status=existing.status, reconciled_orders=reconciled, **metadata)
            if order.side == 'buy' and any(s.status in _ACTIVE for s in states):
                return TickResult(mode=self.mode, status='blocked', reasons=('RUNNER_OUTSTANDING_ORDERS',),
                    client_id=order.client_id, reconciled_orders=reconciled, **metadata)
            if order.side == 'sell' and any(active(s) and s.side == 'sell' and s.symbol == order.symbol
                                            for s in states):
                return TickResult(mode=self.mode, status='blocked', reasons=('RUNNER_OUTSTANDING_ORDERS',),
                    client_id=order.client_id, reconciled_orders=reconciled, **metadata)
            execution_now, deadline_reasons = self._carry_execution_time(execution_now, metadata)
            if deadline_reasons:
                metadata['execution_block_reasons'] = deadline_reasons
                return TickResult(mode=self.mode, status='blocked', reasons=deadline_reasons,
                    client_id=order.client_id, reconciled_orders=reconciled, **metadata)
            self.controller.reserve(order, self.profile.instrument_rules, session_id=session_id, now=execution_now)
            if self.stopped:
                state = self.controller.cancel(order.client_id, now=now)
                return TickResult(mode=self.mode, status='stopped', reasons=('RUNNER_STOPPED',),
                                  client_id=state.client_id, order_status=state.status, **metadata)
            # Controller durably writes DISPATCHING before its single send.
            execution_now, deadline_reasons = self._carry_execution_time(execution_now, metadata)
            if deadline_reasons:
                metadata['execution_block_reasons'] = deadline_reasons
                return TickResult(mode=self.mode, status='blocked', reasons=deadline_reasons,
                    client_id=order.client_id, order_status='RESERVED', reconciled_orders=reconciled, **metadata)
            state = self.controller.dispatch(order.client_id, now=execution_now)
            return TickResult(mode=self.mode, status='submitted', client_id=state.client_id,
                order_status=state.status, reconciled_orders=reconciled,
                protective_action_needed=risk.protective_action_needed, **metadata)
        except RunnerError as exc:
            return TickResult(mode=self.mode, status='blocked', reasons=(str(exc),), **metadata)
        except Exception:
            # Uncertain control effects must be reviewed/reconciled, not retried
            # by a catch-all scheduler. No provider/account text is exposed.
            self._stopped = self.mode != 'observe'
            return TickResult(mode=self.mode, status='blocked', reasons=('RUNNER_DEPENDENCY_REFUSED',), **metadata)
        finally:
            self._lock.release()

    @contextmanager
    def _protective_action(self, now):
        _require(self.mode != 'observe', 'RUNNER_OBSERVATION_ONLY')
        _instant(now)
        _require(self._lock.acquire(blocking=False), 'RUNNER_CONCURRENT_TICK_REFUSED')
        try:
            _require(self._last_now is None or now >= self._last_now, 'RUNNER_CLOCK_ROLLBACK')
            _require(profile_digest(self.profile) == self._profile_digest, 'RUNNER_PROFILE_MUTATED')
            self._last_now = now
            self._controller_boundary()
            yield
        finally:
            self._lock.release()

    def cancel(self, client_id, *, now):
        """Explicit protective action remains available after stop/evidence expiry."""
        with self._protective_action(now):
            _require(type(client_id) is str and client_id.startswith(self._namespace), 'RUNNER_ORDER_SCOPE_MISMATCH')
            return self.controller.cancel(client_id, now=now)

    def submit_exit(self, signal, *, now):
        """Explicit risk-reducing order; E2 retains holdings/conduct/fee checks.

        Research expiry never removes the existing exit route. Current supplied
        quote/account/rules are still required; a stop does not veto this method.
        """
        with self._protective_action(now):
            _require(type(signal) is Signal and signal.action == 'exit', 'RUNNER_EXIT_REQUIRED')
            _, account = self._observations(now)
            order = self._order(signal, account, now)
            states = self.controller.states()
            existing = next((s for s in states if s.client_id == order.client_id), None)
            if existing is not None:
                _require(existing.order_digest == order_digest(order), 'RUNNER_DECISION_CHANGED')
                return existing
            _require(not any(active(s) and s.side == 'sell' and s.symbol == order.symbol for s in states),
                     'RUNNER_OUTSTANDING_ORDERS')
            self.controller.reserve(order, self.profile.instrument_rules,
                                    session_id=self._exit_session_id(), now=now)
            return self.controller.dispatch(order.client_id, now=now)

    def run(self, timestamps, *, max_steps, should_stop=None, entry_allow=None) -> tuple[TickResult, ...]:
        """Bounded synchronous adapter over an external clock/scheduler iterable.

        The caller owns timer delivery; this function never sleeps or starts a
        thread. A blocking external iterator must itself provide cancellation.
        """
        _require(type(max_steps) is int and 1 <= max_steps <= 10000, 'RUNNER_STEP_BOUND_REQUIRED')
        iterator, results = iter(timestamps), []
        for _ in range(max_steps):
            if self.stopped or (should_stop is not None and should_stop()):
                self.stop()
                break
            try:
                now = next(iterator)
            except StopIteration:
                break
            results.append(self.tick(now=now, entry_allow=entry_allow))
        return tuple(results)
