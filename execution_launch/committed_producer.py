"""Fixed isolated rehearsal producer over real local guard/archive boundaries.

Raw market/coverage inputs are external evidence, not authenticated by this
adapter. Owner observations are made at actual supplied-clock instants before
and after intervals. Their private in-process history cannot be reconstructed
from public claims. No setup, writer, source issuer or order permission exists
here; completed local commits are published only through the existing provider.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field, fields, replace
from datetime import datetime, timedelta
from decimal import Decimal
import math
from pathlib import Path
from threading import Lock

from core.compliance import model as CM, owner
from core.isolation import checked_target, state_root
from execution_accounts.baseline import BaselineState, risk_baseline
from execution_accounts.baseline_bridge import advance_account_baseline
from execution_accounts.baseline_store import CheckpointStore
from execution_accounts.collector import CoverageEvidence, OpeningAnchor, TradeFeeEvidence
from execution_accounts.model import AccountEvidence, RiskBaseline, content_digest
from execution_accounts.provider import build_observation
from execution_accounts.upbit_collector import collect_upbit
from execution_control.capability import digest as control_digest
from execution_control.controller import AccountObservation, Controller, _fold
from execution_control.dry_run import DryRunAdapter
from execution_control.store import GENESIS, Journal
from execution_control.risk import RecoveryCheckpoint
from execution_launch import guard_capture_archive as C
from execution_launch import guard_capture_material as M
from execution_launch import guard_generation_archive as A
from execution_launch.account_interval import ContinuousUpbitCandidateSource
from execution_launch.committed_account import CommittedAccountProvider
from execution_launch.committed_startup import CommittedStartup, StartupResult
from execution_launch.continuous_guard import OwnerContextClaim, _owner_terms
from execution_launch.continuous_guard_commit import GuardCheckpointStore
from execution_launch.guard_capture_format import DEFAULT_LIMITS as CAPTURE_DEFAULT_LIMITS
from execution_launch.guard_generation_format import DEFAULT_LIMITS as GENERATION_DEFAULT_LIMITS
from execution_launch.profile import LaunchProfile, profile_contract_digest, risk_policy
from execution_launch.research_bundle_store import BundleStore

_FRESH = timedelta(seconds=30)
_QUANTA = tuple(Decimal((0, (1,), exponent)) for exponent in range(-40, 41))
_CODES = frozenset('INPUT_INVALID REHEARSAL_REQUIRED DEPENDENCY_CHANGED BUSY OPENING_REQUIRED '
    'OWNER_REFUSED OWNER_INTERVAL_NOT_BRACKETED CLOCK_INVALID CLOCK_ROLLBACK STALE CAPTURE_REFUSED '
    'INPUT_ARCHIVE_REFUSED COMMIT_UNCONFIRMED COMPLETION_REFUSED PUBLICATION_REFUSED '
    'RECONCILIATION_REQUIRED'.split())


class CommittedProducerError(ValueError):
    """Fixed public diagnostics only; no private exception text."""
    def __init__(self, code):
        if type(code) is not str or code not in {'COMMITTED_PRODUCER_'+name for name in _CODES}:
            code = 'COMMITTED_PRODUCER_INPUT_INVALID'
        super().__init__(code)


def _need(ok, code):
    if not ok:
        raise CommittedProducerError('COMMITTED_PRODUCER_' + code)


def _account_digest(account):
    # Compliance Positions deliberately contains tuple-keyed mappings; the
    # control codec does not. Its existing canonical codec handles those keys.
    return control_digest((CM.canonical_json(account.positions),
        tuple(sorted(account.account_scopes.items())), account.asof, account.server_time))


def _opening_baseline(value):
    _need(type(value) is RiskBaseline, 'INPUT_INVALID')
    def admit(item):
        if type(item) in (RiskBaseline, RecoveryCheckpoint):
            names = tuple(f.name for f in fields(type(item)))
            data = vars(item)
            _need(len(data) == len(names) and all(type(k) is str for k in data)
                  and set(data) == set(names), 'INPUT_INVALID')
            for name in names:
                admit(data[name])
        elif type(item) is Decimal:
            _need(item.is_finite(), 'INPUT_INVALID')
            exponent = next((i-40 for i, q in enumerate(_QUANTA) if item.same_quantum(q)), None)
            _need(exponent is not None and (item.is_zero() or item.adjusted()-exponent+1 <= 60), 'INPUT_INVALID')
        else:
            M._admit_tree(item)
    admit(value)
    return deepcopy(value)


def _instant(value):
    _need(type(value) is datetime and value.utcoffset() is not None
          and 2 <= value.year <= 9998, 'CLOCK_INVALID')
    return value


class _Inert:
    @property
    def execution_ready(self): return False

    @property
    def source_authenticated(self): return False


@dataclass(frozen=True, kw_only=True)
class ProducerCaptureInputs:
    anchor: OpeningAnchor = field(repr=False)
    coverage: CoverageEvidence = field(repr=False)
    trade_fees: tuple[TradeFeeEvidence, ...] = field(default=(), repr=False)


@dataclass(frozen=True, kw_only=True)
class ProducerOpeningObservation(_Inert):
    observed_at: datetime
    completed_at: datetime
    account_asof: datetime
    manifest_sha256: str
    owner_claim: OwnerContextClaim = field(repr=False)


@dataclass(frozen=True, kw_only=True)
class CommittedProducerUnit(_Inert):
    capture_archive_digest: str
    input_archive_digest: str
    completion_archive_digest: str
    transaction_id: str
    account: AccountEvidence = field(repr=False)
    observation: AccountObservation = field(repr=False)
    reconciliation: StartupResult
    completed_at: datetime


@dataclass(frozen=True, kw_only=True)
class CommittedProducerStatus(_Inert):
    phase: str = 'NEW'
    reason: str = ''
    capture_archive_digest: str | None = None
    input_archive_digest: str | None = None
    completion_archive_digest: str | None = None
    transaction_id: str | None = None
    completed_at: datetime | None = None


@dataclass(frozen=True, kw_only=True)
class _OwnerRead:
    claim: OwnerContextClaim
    context: object = field(repr=False)
    account: AccountObservation = field(repr=False)
    completed_at: datetime
    fingerprint: str
    account_digest: str


class CommittedAccountProducer:
    def __init__(self, *, archive_store, journal, guard_store, guard_head,
                 baseline_store, baseline_head, profile, adapters,
                 isolated_state_root, clock, candidate_source, collector_source,
                 capture_inputs_source, session_id=None,
                 limits=GENERATION_DEFAULT_LIMITS, capture_limits=CAPTURE_DEFAULT_LIMITS):
        _need(type(archive_store) is BundleStore and type(journal) is Journal
              and type(guard_store) is GuardCheckpointStore and type(baseline_store) is CheckpointStore
              and type(profile) is LaunchProfile and type(candidate_source) is ContinuousUpbitCandidateSource
              and callable(clock) and callable(capture_inputs_source)
              and callable(getattr(collector_source, 'fetch', None)), 'INPUT_INVALID')
        _need(type(adapters) is dict and set(adapters) == {'upbit'}
              and type(adapters['upbit']) is DryRunAdapter
              and journal.requires_existing is True and profile.universe_rule_sha256 is None
              and (profile.venue, profile.market, profile.quote_currency) == ('upbit', 'spot', 'KRW'),
              'REHEARSAL_REQUIRED')
        _need(isinstance(isolated_state_root, Path) and isolated_state_root.is_absolute()
              and all(callable(getattr(h, n, None)) for h in (guard_head, baseline_head)
                      for n in ('read', 'compare_and_set')), 'INPUT_INVALID')
        _need(session_id is None or (type(session_id) is str and 0 < len(session_id) <= 128), 'INPUT_INVALID')
        self._archive_store, self._journal = archive_store, journal
        self._guard_store, self._guard_head = guard_store, guard_head
        self._baseline_store, self._baseline_head = baseline_store, baseline_head
        self._profile, self._adapters = profile, dict(adapters)
        self._root, self._clock = isolated_state_root.absolute(), clock
        self._source, self._collector, self._inputs = candidate_source, collector_source, capture_inputs_source
        self._session_id, self._limits, self._capture_limits = session_id, limits, capture_limits
        self._policy = risk_policy(profile)
        self._policy_digest, self._profile_digest = content_digest(self._policy), profile_contract_digest(profile)
        self._pins = (archive_store, journal, guard_store, guard_head, baseline_store, baseline_head,
            profile, clock, candidate_source, collector_source, capture_inputs_source, limits, capture_limits)
        self._source_pins = (candidate_source._path_source, candidate_source._coverage_verifier,
                             candidate_source._archive_root)
        self._adapter = adapters['upbit']
        fetch = collector_source.fetch
        self._fetch_pin = (getattr(fetch, '__self__', None), getattr(fetch, '__func__', fetch))
        self._session_pin = session_id
        self._work, self._last = Lock(), None
        self._startup = self._startup_pin = self._session_provider = None
        self._before = self._opening = self._opening_account = None
        self._unit = self._current = self._unit_digest = None
        self._reconciliation = self._reconciliation_digest = None
        self._blocked = False
        self._status = CommittedProducerStatus()
        self._configuration()

    def _configuration(self):
        fetch = self._collector.fetch
        _need(getattr(fetch, '__self__', None) is self._fetch_pin[0]
              and getattr(fetch, '__func__', fetch) is self._fetch_pin[1]
              and self._session_id == self._session_pin, 'DEPENDENCY_CHANGED')
        values = (self._archive_store, self._journal, self._guard_store, self._guard_head,
            self._baseline_store, self._baseline_head, self._profile, self._clock,
            self._source, self._collector, self._inputs, self._limits, self._capture_limits)
        _need(all(a is b for a, b in zip(values, self._pins))
              and self._source._path_source is self._source_pins[0]
              and self._source._coverage_verifier is self._source_pins[1]
              and self._source._archive_root == self._source_pins[2]
              and self._collector.account_scope == self._profile.account_scope
              and set(self._adapters) == {'upbit'} and self._adapters['upbit'] is self._adapter
              and content_digest(risk_policy(self._profile)) == self._policy_digest
              and content_digest(self._policy) == self._policy_digest
              and profile_contract_digest(self._profile) == self._profile_digest,
              'DEPENDENCY_CHANGED')
        _need(self._journal.requires_existing is True
              and self._journal._base == self._guard_store._base == self._baseline_store._base == self._root
              and state_root().absolute() == self._root
              and not self._root.is_relative_to(Path.home()/'.tradegen'), 'REHEARSAL_REQUIRED')
        checked_target(self._root, 'isolated producer state')
        self._archive_store._configuration()
        if self._startup_pin is not None:
            _need(self._startup is self._startup_pin
                  and self._startup.session_provider is self._session_provider, 'DEPENDENCY_CHANGED')
            self._startup._configuration()

    def _now(self):
        try:
            value = _instant(self._clock())
        except Exception:
            raise CommittedProducerError('COMMITTED_PRODUCER_CLOCK_INVALID') from None
        _need(self._last is None or value >= self._last, 'CLOCK_ROLLBACK')
        self._last = value
        return value

    def _completed(self, value):
        _instant(value)
        _need(self._last is None or value >= self._last, 'CLOCK_ROLLBACK')
        self._last = value

    def _bind_startup(self, *, session_provider):
        self._configuration()
        _need(self._startup is None and callable(session_provider), 'DEPENDENCY_CHANGED')
        app = CommittedStartup(archive_store=self._archive_store, journal=self._journal,
            guard_store=self._guard_store, guard_head=self._guard_head,
            baseline_store=self._baseline_store, baseline_head=self._baseline_head,
            profile=self._profile, adapters=self._adapters, isolated_state_root=self._root,
            clock=self._clock, session_provider=session_provider,
            limits=self._limits, capture_limits=self._capture_limits)
        self._startup = self._startup_pin = app
        self._session_provider = session_provider

    def status(self):
        return replace(self._status)

    def _phase(self, phase, **values):
        self._status = replace(self._status, phase=phase, **values)

    def _inputs_at(self, previous):
        self._configuration()
        if previous is not None:
            M._admit_tree(previous)
        supplied = self._inputs(previous=deepcopy(previous), now=self._now())
        self._configuration()
        self._now()
        _need(type(supplied) is ProducerCaptureInputs
              and len(vars(supplied)) == len(fields(ProducerCaptureInputs))
              and all(type(k) is str for k in vars(supplied))
              and set(vars(supplied)) == {f.name for f in fields(ProducerCaptureInputs)}, 'INPUT_INVALID')
        return M._snapshot_inputs(supplied.anchor, supplied.coverage, supplied.trade_fees)

    def _owner_read(self, account):
        _need(type(account) is AccountObservation
              and dict(account.account_scopes) == {'upbit': self._profile.account_scope}, 'OWNER_REFUSED')
        at = self._now()
        _need(timedelta(0) <= at-account.asof <= _FRESH, 'STALE')
        ctx = owner.load_context(at, account.positions, session_id=self._session_id)
        intact = (type(ctx) is CM.Context and CM.is_sealed(ctx) and type(ctx.owner) is CM.OwnerState
            and type(ctx.active) is CM.ApprovedState and ctx.ctx_hash == CM.context_hash(ctx))
        _need(intact and ctx.owner.ok and ctx.code_signed is True
              and ctx.date == at.astimezone(CM.KST).date() and bool(ctx.owner.fingerprint), 'OWNER_REFUSED')
        amounts = []
        for key in ('total_loss_floor_krw', 'daily_loss_krw'):
            value = ctx.owner.limits.get(key)
            _need(type(value) in (int, float) and math.isfinite(value) and value >= 0, 'OWNER_REFUSED')
            amounts.append(Decimal(str(value)))
        _need(amounts[1] > 0, 'OWNER_REFUSED')
        claim = OwnerContextClaim(owner_head_sha256=ctx.owner.head[1], code_sha256=ctx.code_hash,
            code_approval_sha256=ctx.code_hash, signed_floor_krw=amounts[0], signed_daily_loss_krw=amounts[1],
            observed_at=at, source_sha256=ctx.ctx_hash)
        result = _OwnerRead(claim=claim, context=ctx, account=account, fingerprint=ctx.owner.fingerprint,
                            account_digest=_account_digest(account), completed_at=self._now())
        self._owner_intact(result)
        self._configuration()
        finish = self._now()
        _need(timedelta(0) <= finish-at <= _FRESH
              and timedelta(0) <= finish-account.asof <= _FRESH
              and abs(finish-account.server_time) <= timedelta(seconds=60)
              and finish.astimezone(CM.KST).date() == at.astimezone(CM.KST).date()
              == account.server_time.astimezone(CM.KST).date(), 'STALE')
        return replace(result, completed_at=finish)

    def _owner_intact(self, read):
        _need(type(read) is _OwnerRead and CM.is_sealed(read.context)
              and read.context.ctx_hash == CM.context_hash(read.context) == read.claim.source_sha256
              and _account_digest(read.account) == read.account_digest
              and read.context.owner.fingerprint == read.fingerprint
              and read.context.owner.head[1] == read.claim.owner_head_sha256
              and read.context.code_hash == read.claim.code_sha256 == read.claim.code_approval_sha256,
              'OWNER_REFUSED')

    def _same_owner(self, left, right):
        self._owner_intact(left); self._owner_intact(right)
        _need(_owner_terms(left.claim) == _owner_terms(right.claim)
              and left.fingerprint == right.fingerprint, 'OWNER_REFUSED')

    def observe_opening(self, *, risk_baseline):
        _need(self._work.acquire(blocking=False), 'BUSY')
        try:
            self._configuration()
            _need(self._opening is None and self._unit is None and not self._blocked
                  and type(risk_baseline) is RiskBaseline, 'OPENING_REQUIRED')
            admitted_baseline = _opening_baseline(risk_baseline)
            anchor, coverage, fees = self._inputs_at(None)
            collection = collect_upbit(self._collector, anchor=anchor, coverage=coverage,
                risk_baseline=admitted_baseline, clock=self._now, trade_fees=fees)
            observation = build_observation(collection.bundle, now=self._now())
            read = self._owner_read(observation)
            self._opening_account, self._before = observation, read
            self._opening = ProducerOpeningObservation(observed_at=read.claim.observed_at,
                completed_at=read.completed_at, account_asof=observation.asof,
                manifest_sha256=collection.manifest_sha256, owner_claim=deepcopy(read.claim))
            self._phase('OPENING_OBSERVED', completed_at=read.completed_at)
            return replace(self._opening, owner_claim=deepcopy(read.claim))
        except CommittedProducerError:
            raise
        except Exception:
            raise CommittedProducerError('COMMITTED_PRODUCER_OWNER_REFUSED') from None
        finally:
            self._work.release()

    def _previous(self):
        self._configuration()
        with self._journal.transaction() as tx:
            events = tx.events
            _fold(events)
            gh, bh = self._guard_head.read(), self._baseline_head.read()
            guard, baseline = self._guard_store.load(expected_head=gh), self._baseline_store.load(expected_head=bh)
            _need(guard.baseline == baseline and guard.policy_sha256 == self._policy_digest,
                  'DEPENDENCY_CHANGED')
            if self._unit is not None:
                provider, _, _ = self._runtime_components()
                inspected = CommittedAccountProvider.inspect_committed(provider, now=self._now(), transaction=tx)
                _need(inspected.transaction_id == self._current[2], 'DEPENDENCY_CHANGED')
            _need(self._guard_head.read() == gh and self._baseline_head.read() == bh
                  and self._guard_store.load(expected_head=gh) == guard
                  and self._baseline_store.load(expected_head=bh) == baseline
                  and tx.events == events, 'DEPENDENCY_CHANGED')
            return guard, baseline, (gh, bh, events[-1]['row_sha256'] if events else GENESIS)

    def _predecessor(self, previous):
        actual = self._previous()
        _need(actual == previous, 'DEPENDENCY_CHANGED')

    def _runtime_components(self):
        self._configuration()
        app = self._startup
        _need(app is not None and type(app.provider) is CommittedAccountProvider
              and type(app.controller) is Controller and app.provider is app.controller.account_provider
              and app.controller.journal is self._journal, 'RECONCILIATION_REQUIRED')
        return app.provider, app.controller, self._journal

    def _reconcile(self, retained, completed):
        app = self._startup
        if app.provider is None:
            result = app.reconcile(retained.archive_digest, completed.archive_digest, session_id=self._session_id)
        else:
            inspection, retained, completed = app._inspect(retained.archive_digest, completed.archive_digest)
            result = app._reconcile_runtime(inspection, retained, completed, session_id=self._session_id)
        self._completed(result.completed_at)
        return result

    def _current_read(self, current, requested):
        _need(requested <= self._now(), 'CLOCK_ROLLBACK')
        input_id, completion_id, transaction_id = current
        retained = A.read_guard_completion(self._archive_store, completion_id,
            expected_input_archive_digest=input_id, limits=self._limits, capture_limits=self._capture_limits)
        provider, controller, _ = self._runtime_components()
        with self._journal.transaction() as tx:
            actual = CommittedAccountProvider.inspect_committed(provider, now=self._now(), transaction=tx)
            CommittedStartup._completion_binding(retained.record, actual, tx.events, self._last)
            _need(actual.transaction_id == transaction_id, 'DEPENDENCY_CHANGED')
        paired = Controller.read_committed_account(controller, now=self._now(), session_id=self._session_id)
        self._completed(paired.completed_at)
        _need(paired.committed.transaction_id == transaction_id, 'DEPENDENCY_CHANGED')
        baseline = self._baseline_store.load(expected_head=paired.committed.baseline_head)
        self._configuration()
        _need(self._baseline_head.read() == paired.committed.baseline_head
              and self._guard_head.read() == paired.committed.guard_head, 'DEPENDENCY_CHANGED')
        finish = self._now()
        _need(CommittedStartup._time_status(baseline, finish)[0] == 'FRESH', 'STALE')
        _need(timedelta(0) <= finish-paired.account.asof <= _FRESH
              and timedelta(0) <= finish-paired.committed.owner_claim.observed_at <= _FRESH
              and abs(finish-paired.account.server_time) <= timedelta(seconds=60)
              and finish.astimezone(CM.KST).date() == paired.account.asof.astimezone(CM.KST).date()
              == paired.account.server_time.astimezone(CM.KST).date(), 'STALE')
        return replace(paired, completed_at=finish), deepcopy(retained.retained_input.package['account_capture'].endpoint_accounts[0])

    @staticmethod
    def _unit_binding(unit):
        return control_digest((unit.capture_archive_digest, unit.input_archive_digest,
            unit.completion_archive_digest, unit.transaction_id, unit.reconciliation, unit.completed_at))

    def _current_unit(self, unit, *, now):
        _need(self._work.acquire(blocking=False), 'BUSY')
        try:
            _need(not self._blocked and unit is self._unit and self._current is not None
                  and self._unit_binding(unit) == self._unit_digest, 'DEPENDENCY_CHANGED')
            paired, account = self._current_read(self._current, _instant(now))
            reconciliation = self._reconciliation
            _need(control_digest(reconciliation) == self._reconciliation_digest, 'DEPENDENCY_CHANGED')
            if paired.committed.observed_control_head != reconciliation.final_control_head:
                # At most one genuine reconciliation; a newer order prefix is
                # never combined with the previous entry-readiness result.
                completed = A.read_guard_completion(self._archive_store, self._current[1],
                    expected_input_archive_digest=self._current[0], limits=self._limits,
                    capture_limits=self._capture_limits)
                reconciliation = self._reconcile(completed.retained_input, completed)
                paired, account = self._current_read(self._current, self._now())
            _need(paired.committed.observed_control_head == reconciliation.final_control_head,
                  'RECONCILIATION_REQUIRED')
            self._reconciliation = deepcopy(reconciliation)
            self._reconciliation_digest = control_digest(reconciliation)
            return paired, account, deepcopy(reconciliation)
        except CommittedProducerError:
            raise
        except Exception:
            raise CommittedProducerError('COMMITTED_PRODUCER_DEPENDENCY_CHANGED') from None
        finally:
            self._work.release()

    def _collect_current(self):
        return self._collect(None)

    def collect_and_publish(self, *, anchor, coverage, trade_fees=()):
        return self._collect((anchor, coverage, trade_fees))

    def _collect(self, supplied):
        _need(self._work.acquire(blocking=False), 'BUSY')
        stage = 'CAPTURE_REFUSED'
        try:
            self._configuration()
            _need(self._startup is not None and self._before is not None and not self._blocked,
                  'OPENING_REQUIRED')
            original = self._previous()
            guard, previous, heads = original
            before = self._before
            self._owner_intact(before)
            _need(before.completed_at <= previous.asof
                  and timedelta(0) <= previous.asof-before.claim.observed_at <= _FRESH,
                  'OWNER_INTERVAL_NOT_BRACKETED')
            _need(before.claim.owner_head_sha256 == guard.owner_head_sha256
                  and before.claim.code_sha256 == guard.code_sha256
                  and (not before.context.owner.halted_floors or guard.permanently_halted), 'OWNER_REFUSED')
            inputs = self._inputs_at(previous) if supplied is None else M._snapshot_inputs(*supplied)
            self._predecessor(original)
            if self._unit is None:
                opening_account = self._opening_account
            else:
                _, controller, _ = self._runtime_components()
                paired = Controller.read_committed_account(controller, now=self._now(), session_id=self._session_id)
                self._completed(paired.completed_at)
                opening_account = paired.account
            next_before = self._owner_read(opening_account)
            self._same_owner(before, next_before)
            anchor, coverage, fees = inputs
            captured = C.collect_archive_guard_capture(self._source, self._collector, store=self._archive_store,
                previous=previous, anchor=anchor, coverage=coverage, clock=self._now,
                trade_fees=fees, limits=self._capture_limits)
            self._phase('CAPTURE_ARCHIVED', capture_archive_digest=captured.receipt.archive_digest,
                        input_archive_digest=None, completion_archive_digest=None, transaction_id=None)
            _need(captured.replay is not None and captured.audit_error_code is None, 'CAPTURE_REFUSED')
            material = captured.replay.material
            endpoint = advance_account_baseline(previous, material.interval,
                material.account_capture.endpoint_accounts, now=self._now()).observation
            after = self._owner_read(endpoint)
            self._same_owner(before, after)
            package = dict(baseline_before=previous, policy=self._policy, owner_before=before.claim,
                owner_after=after.claim, path=material.path, valuation_inputs=material.valuation_inputs,
                account_capture=material.account_capture, coverage=material.coverage,
                interval=material.interval, now=after.completed_at)
            stage = 'INPUT_ARCHIVE_REFUSED'
            retained = A.retain_guard_input(self._archive_store, captured.receipt.archive_digest, package,
                expected_guard_head=heads[0], expected_baseline_head=heads[1], expected_control_head=heads[2],
                limits=self._limits, capture_limits=self._capture_limits)
            self._phase('INPUT_RETAINED', input_archive_digest=retained.archive_digest)
            self._same_owner(after, self._owner_read(endpoint))
            self._predecessor(original)
            stage = 'COMMIT_UNCONFIRMED'
            self._phase('COMMIT_UNCONFIRMED')
            self._blocked = True  # Never guess whether a refused/response-lost commit changed heads.
            completed = self._startup.commit_input(retained.archive_digest)
            stage = 'COMPLETION_REFUSED'
            completed = A.read_guard_completion(self._archive_store, completed.archive_digest,
                expected_input_archive_digest=retained.archive_digest,
                limits=self._limits, capture_limits=self._capture_limits)
            self._phase('COMPLETION_RETAINED', completion_archive_digest=completed.archive_digest,
                        transaction_id=completed.record.receipt.transaction_id)
            stage = 'PUBLICATION_REFUSED'
            if self._startup.provider is not None:
                provider, _, _ = self._runtime_components()
                with self._journal.transaction() as tx:
                    candidate = self._startup._provider(completed.retained_input, completed.record.receipt)
                    actual = CommittedAccountProvider.inspect_committed(candidate, now=self._now(), transaction=tx)
                    CommittedStartup._completion_binding(completed.record, actual, tx.events, self._last)
                    CommittedAccountProvider.publish_committed(provider, completed.retained_input.package,
                        completed.record.receipt, expected_guard_head=heads[0], expected_baseline_head=heads[1],
                        expected_control_head=heads[2], now=self._now(), transaction=tx)
                self._phase('PUBLISHED')
            stage = 'RECONCILIATION_REQUIRED'
            reconciliation = self._reconcile(retained, completed)
            _need(self._startup.provider is not None, 'RECONCILIATION_REQUIRED')
            current = (retained.archive_digest, completed.archive_digest, completed.record.receipt.transaction_id)
            paired, account = self._current_read(current, self._now())
            _need(paired.committed.observed_control_head == reconciliation.final_control_head,
                  'RECONCILIATION_REQUIRED')
            unit = CommittedProducerUnit(capture_archive_digest=captured.receipt.archive_digest,
                input_archive_digest=current[0], completion_archive_digest=current[1], transaction_id=current[2],
                account=account, observation=paired.account, reconciliation=reconciliation,
                completed_at=paired.completed_at)
            self._current, self._unit = current, unit
            self._unit_digest = self._unit_binding(unit)
            self._reconciliation = deepcopy(reconciliation)
            self._reconciliation_digest = control_digest(reconciliation)
            self._before = next_before
            self._blocked = False
            self._phase('RECONCILED' if reconciliation.status in ('RECONCILED', 'RECONCILED_OPEN') else 'BLOCKED',
                        reason=reconciliation.reason, completed_at=unit.completed_at)
            return unit
        except CommittedProducerError as exc:
            self._phase('BLOCKED', reason=str(exc))
            raise
        except Exception:
            self._phase('BLOCKED', reason='COMMITTED_PRODUCER_'+stage)
            raise CommittedProducerError('COMMITTED_PRODUCER_'+stage) from None
        finally:
            self._work.release()
