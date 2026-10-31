"""Explicit, synchronous launch orchestration; importing this module does nothing.

The default mode only diagnoses supplied observations. Rehearsal requires a
separate explicit state root and exact DryRunAdapters. Controlled operation must
be constructed explicitly by the owner with providers, reviewed strategy code,
and an actual E2 prepared session; there are no credentials or live defaults.
"""
from __future__ import annotations

import base64
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re
from threading import Lock
from typing import Callable

from core.isolation import checked_target, state_root
from execution_control.capability import digest
from execution_control.controller import AccountObservation, Controller
from execution_control.dry_run import DryRunAdapter
from execution_control.model import Order, order_digest, rules_digest, validate_order
from execution_control.risk import evaluate
from execution_control.session import PreparedSession, prepare_session
from execution_launch.profile import (LaunchProfile, preflight_profile, profile_digest,
    profile_contract_digest, rule_terms_digest, risk_policy)
from execution_launch.strategy import assess_strategy

_ACTIVE = frozenset({'RESERVED', 'UNKNOWN', 'ACKNOWLEDGED', 'PARTIAL', 'CANCEL_REQUESTED'})
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
        _require(type(body) is dict and canonical == driver.parameters_json, 'RUNNER_PARAMETERS_NOT_CANONICAL')
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
        rule_terms_digest=rule_terms_digest(profile.instrument_rules),
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
                           selection_seed_hex, expires_at=None) -> LaunchSession:
    """Prepare fresh odds with a derived label BEFORE the owner signs its ID.

    This writes only the existing preparation event. It does not sign, arm, fetch
    account data or send an order. The owner must subsequently use the returned
    actual PreparedSession object, not reconstruct a serialized copy.
    """
    _instant(now)
    _require(preflight_profile(profile, now=now).profile_complete, 'RUNNER_PROFILE_INCOMPLETE')
    assessment, binding = _assess(profile, evidence, driver, implementation_verifier, now)
    _require(assessment.research_review_ready, 'RUNNER_STRATEGY_NOT_QUALIFIED')
    symbol = (profile.symbol.split('-')[1] if profile.venue == 'upbit' else
              profile.symbol.split('-')[0] if profile.venue == 'okx' else profile.symbol)
    _require((selected_plan.leg.venue, selected_plan.leg.symbol) == (profile.venue, symbol),
             'RUNNER_SELECTED_PLAN_SCOPE_MISMATCH')
    _require(0 < selected_plan.stake_krw <= profile.policy.initial_equity,
             'RUNNER_SELECTED_STAKE_EXCEEDS_RESEARCH_CAPITAL')
    prepared = prepare_session(journal=journal, session_id=_label(binding), selected_plan=selected_plan,
        inputs=inputs, positions=positions, policy=risk_policy(profile), instrument_rules=profile.instrument_rules,
        now=now, selection_seed_hex=selection_seed_hex, account_scope=profile.account_scope,
        market=profile.market, quote_currency=profile.quote_currency, expires_at=expires_at)
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


class Runner:
    """One tick at a time, using the caller's clock and explicit providers.

    Source/review verifiers and strategy callbacks are trusted code supplied by
    the operator. There is no hidden scheduler, retry worker or credential path.
    A Runner stops after an unexpected control error; restart still reconciles
    durable state before considering a new entry.
    """
    def __init__(self, *, profile, quote_provider, account_provider, evidence=None,
                 driver=None, implementation_verifier=None, mode='observe', controller=None,
                 launch_session=None, isolated_state_root=None):
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
        if mode != 'observe':
            self._controller_boundary()

    def _controller_boundary(self):
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

    def _order(self, signal, account):
        _require(type(signal) is Signal and _SIGNAL.fullmatch(signal.signal_id) is not None
                 and signal.action in ('entry', 'exit', 'hold'), 'RUNNER_SIGNAL_INVALID')
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
        validate_order(order, self.profile.instrument_rules)
        return order

    def _session(self, binding, now):
        launch = self.launch_session
        _require(type(launch) is LaunchSession and type(launch.prepared) is PreparedSession,
                 'RUNNER_ACTUAL_PREPARED_SESSION_REQUIRED')
        p = launch.prepared
        _require(launch.profile_digest == profile_digest(self.profile) and launch.binding == binding
                 and p.session_id.rpartition('-')[0] == _label(binding)
                 and p.policy_digest == digest(risk_policy(self.profile))
                 and p.rules_digest == rules_digest(self.profile.instrument_rules)
                 and (p.venue, p.account_scope, p.market, p.quote_currency) ==
                     (self.profile.venue, self.profile.account_scope, self.profile.market, self.profile.quote_currency)
                 and p.prepared_at <= now < p.expires_at
                 and self.controller.session_provider(p.session_id) is p,
                 'RUNNER_SESSION_BINDING_MISMATCH')
        return p.session_id  # E2 verifies registry, object integrity, signed owner and journal next.

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

    def tick(self, *, now) -> TickResult:
        _instant(now)
        if self._stopped:
            return TickResult(mode=self.mode, status='stopped', reasons=('RUNNER_STOPPED',))
        _require(self._lock.acquire(blocking=False), 'RUNNER_CONCURRENT_TICK_REFUSED')
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
            risk = risk if risk is not None else evaluate(risk_policy(self.profile), account.risk)
            assessment, binding = _assess(self.profile, self.evidence, self.driver,
                                          self.implementation_verifier, now)
            signal = self.driver.callback(DecisionInput(now=now, profile=self.profile, quote=quote, account=account),
                                          self.driver.parameters_json)
            order = self._order(signal, account)
            if order is None:
                return TickResult(mode=self.mode, status='hold', reasons=assessment.reasons,
                    reconciled_orders=reconciled, protective_action_needed=risk.protective_action_needed)
            reasons = assessment.reasons if order.side == 'buy' else ()
            if order.side == 'buy' and risk.new_entry_blocked:
                reasons += ('RUNNER_RISK_BLOCKS_ENTRY',)
            if reasons:
                return TickResult(mode=self.mode, status='blocked', reasons=reasons, client_id=order.client_id,
                    reconciled_orders=reconciled, protective_action_needed=risk.protective_action_needed)
            if self.mode == 'observe':
                return TickResult(mode=self.mode, status='observed', reasons=('RUNNER_OBSERVATION_ONLY',),
                    client_id=order.client_id, protective_action_needed=risk.protective_action_needed)
            if self.stopped:
                return TickResult(mode=self.mode, status='stopped', reasons=('RUNNER_STOPPED',))
            session_id = self._session(binding, now) if order.side == 'buy' else self._exit_session_id()
            states = self.controller.states()
            existing = next((s for s in states if s.client_id == order.client_id), None)
            if existing is not None:
                _require(existing.order_digest == order_digest(order), 'RUNNER_DECISION_CHANGED')
                return TickResult(mode=self.mode, status='existing', client_id=existing.client_id,
                    order_status=existing.status, reconciled_orders=reconciled)
            if order.side == 'buy' and any(s.status in _ACTIVE for s in states):
                return TickResult(mode=self.mode, status='blocked', reasons=('RUNNER_OUTSTANDING_ORDERS',),
                    client_id=order.client_id, reconciled_orders=reconciled)
            self.controller.reserve(order, self.profile.instrument_rules, session_id=session_id, now=now)
            if self.stopped:
                state = self.controller.cancel(order.client_id, now=now)
                return TickResult(mode=self.mode, status='stopped', reasons=('RUNNER_STOPPED',),
                                  client_id=state.client_id, order_status=state.status)
            # Controller durably writes DISPATCHING before its single send.
            state = self.controller.dispatch(order.client_id, now=now)
            return TickResult(mode=self.mode, status='submitted', client_id=state.client_id,
                order_status=state.status, reconciled_orders=reconciled,
                protective_action_needed=risk.protective_action_needed)
        except RunnerError as exc:
            return TickResult(mode=self.mode, status='blocked', reasons=(str(exc),))
        except Exception:
            # Uncertain control effects must be reviewed/reconciled, not retried
            # by a catch-all scheduler. No provider/account text is exposed.
            self._stopped = self.mode != 'observe'
            return TickResult(mode=self.mode, status='blocked', reasons=('RUNNER_DEPENDENCY_REFUSED',))
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
            order = self._order(signal, account)
            existing = next((s for s in self.controller.states() if s.client_id == order.client_id), None)
            if existing is not None:
                _require(existing.order_digest == order_digest(order), 'RUNNER_DECISION_CHANGED')
                return existing
            self.controller.reserve(order, self.profile.instrument_rules,
                                    session_id=self._exit_session_id(), now=now)
            return self.controller.dispatch(order.client_id, now=now)

    def run(self, timestamps, *, max_steps, should_stop=None) -> tuple[TickResult, ...]:
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
            results.append(self.tick(now=now))
        return tuple(results)
