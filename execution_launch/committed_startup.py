"""Retained local guard recovery and isolated dry-run startup reconciliation.

Historical linkage, current account reconciliation and current owner checks are
separate. Nothing here issues source coverage, seeds/adopts a head, refreshes an
old timestamp, creates an order, or enables controlled operation.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from threading import Lock

from core.compliance.model import KST
from core.isolation import state_root
from execution_accounts.baseline import _required_cutoff
from execution_accounts.baseline_store import CheckpointStore
from execution_accounts.model import content_digest
from execution_control.capability import digest as control_digest
from execution_control.controller import Controller, _exact, _fold, _view
from execution_control.dry_run import DryRunAdapter
from execution_control.store import GENESIS, Journal, _utc
from execution_launch import guard_generation_archive as A
from execution_launch.guard_generation_format import DEFAULT_LIMITS
from execution_launch.guard_capture_format import DEFAULT_LIMITS as CAPTURE_DEFAULT_LIMITS
from execution_launch.committed_account import CommittedAccountProvider
from execution_launch.continuous_guard import plan_continuous_guard
from execution_launch.continuous_guard_commit import (
    COMPLETE, PREPARE, CONSISTENT, FRESH, DIVERGENCE, REFUSED,
    GuardCheckpointStore, classify_restart, commit_continuous_guard,
)
from execution_launch.runner import Runner, _ACTIVE, risk_policy
from execution_launch.profile import LaunchProfile
from execution_launch.research_bundle_store import BundleStore

MAX_STARTUP_ORDERS = 1024
_ERRORS = (ValueError, RuntimeError, OSError, TypeError, AttributeError, KeyError, ArithmeticError)


class CommittedStartupError(ValueError):
    """Fixed STARTUP_* diagnostics, without paths or private evidence."""


def _need(ok, code):
    if not ok:
        raise CommittedStartupError(code)


def _instant(value):
    _need(type(value) is datetime and value.utcoffset() is not None
          and 2 <= value.year <= 9998, 'STARTUP_CLOCK_INVALID')
    return value


def _no_quote(_now):
    raise CommittedStartupError('STARTUP_QUOTE_UNAVAILABLE')


@dataclass(frozen=True, kw_only=True)
class StartupInspection:
    input_archive_digest: str
    completion_archive_digest: str | None
    durable_status: str
    current_status: str
    reason: str
    transaction_id: str | None
    observed_control_head: str | None
    asof: datetime
    inspected_at: datetime

    @property
    def execution_ready(self): return False

    @property
    def source_authenticated(self): return False


@dataclass(frozen=True, kw_only=True)
class StartupResult:
    inspection: StartupInspection
    status: str
    reason: str
    attempted_reconciliations: int
    unresolved_client_ids: tuple[str, ...]
    external_order_ids: tuple[str, ...]
    open_client_ids: tuple[str, ...]
    holdings: tuple[tuple[str, str, Decimal], ...] = field(repr=False)
    final_control_head: str | None
    completed_at: datetime

    @property
    def execution_ready(self): return False

    @property
    def source_authenticated(self): return False


class CommittedStartup:
    """One pinned isolated composition; retained records are not authority.

    The nonblocking local work lock only serializes this object's entry points.
    No Controller/provider callback requests it and no archive lock is retained
    while requesting the actual control Journal.
    """
    def __init__(self, *, archive_store, journal, guard_store, guard_head,
                 baseline_store, baseline_head, profile, adapters,
                 isolated_state_root, clock, session_provider=None,
                 limits=DEFAULT_LIMITS, capture_limits=CAPTURE_DEFAULT_LIMITS):
        _need(type(archive_store) is BundleStore and type(journal) is Journal and type(guard_store) is GuardCheckpointStore
              and type(baseline_store) is CheckpointStore and type(profile) is LaunchProfile
              and callable(clock) and (session_provider is None or callable(session_provider)),
              'STARTUP_INPUT_INVALID')
        _need(journal.requires_existing is True, 'STARTUP_REHEARSAL_REQUIRED')
        _need(type(adapters) is dict and adapters and all(type(a) is DryRunAdapter for a in adapters.values()),
              'STARTUP_REHEARSAL_REQUIRED')
        _need(isinstance(isolated_state_root, Path) and isolated_state_root.is_absolute(),
              'STARTUP_REHEARSAL_REQUIRED')
        root = isolated_state_root.absolute()
        _need(journal._base == guard_store._base == baseline_store._base == root,
              'STARTUP_REHEARSAL_REQUIRED')
        _need((profile.venue, profile.market, profile.quote_currency) == ('upbit', 'spot', 'KRW')
              and set(adapters) == {'upbit'}, 'STARTUP_REHEARSAL_REQUIRED')
        _need(all(callable(getattr(h, name, None)) for h in (guard_head, baseline_head)
                  for name in ('read', 'compare_and_set')), 'STARTUP_INPUT_INVALID')
        self.archive_store, self.journal = archive_store, journal
        self.guard_store, self.guard_head = guard_store, guard_head
        self.baseline_store, self.baseline_head = baseline_store, baseline_head
        self.profile, self.adapters, self.root = profile, dict(adapters), root
        self.clock, self.session_provider = clock, session_provider
        self.limits, self.capture_limits = limits, capture_limits
        self._integrations = (archive_store, journal, guard_store, guard_head,
                              baseline_store, baseline_head, profile, clock, session_provider)
        self._adapter_pins = tuple(sorted(self.adapters.items()))
        self._profile_policy = control_digest(risk_policy(profile))
        self._last = None
        self._work = Lock()
        self._binding = None
        self.provider = self.controller = self.runner = None

    def _configuration(self):
        _need(all(a is b for a, b in zip((self.archive_store, self.journal, self.guard_store,
              self.guard_head, self.baseline_store, self.baseline_head, self.profile, self.clock,
              self.session_provider), self._integrations)), 'STARTUP_DEPENDENCY_CHANGED')
        _need(tuple(sorted(self.adapters)) == tuple(k for k, _ in self._adapter_pins)
              and all(self.adapters[k] is v for k, v in self._adapter_pins)
              and control_digest(risk_policy(self.profile)) == self._profile_policy,
              'STARTUP_DEPENDENCY_CHANGED')
        _need(self.journal.requires_existing is True
              and self.journal._base == self.guard_store._base == self.baseline_store._base == self.root
              and state_root().absolute() == self.root, 'STARTUP_REHEARSAL_REQUIRED')
        self.archive_store._configuration()
        if self.runner is not None:
            _need(all(a is b for a, b in zip((self.provider, self.controller, self.runner), self._runtime_pins)),
                  'STARTUP_DEPENDENCY_CHANGED')
            _need(self.runner.controller is self.controller and self.runner.account_provider is self.provider,
                  'STARTUP_DEPENDENCY_CHANGED')
            Runner._controller_boundary(self.runner)

    def _now(self):
        try:
            value = _instant(self.clock())
        except _ERRORS:
            raise CommittedStartupError('STARTUP_CLOCK_INVALID') from None
        _need(self._last is None or value >= self._last, 'STARTUP_CLOCK_ROLLBACK')
        self._last = value
        return value

    def _completed(self, observation):
        # Actual Controller clocks may advance during owner/provider work.
        # Keep that completion as the next startup phase's minimum time.
        value = _instant(observation.completed_at)
        _need(self._last is None or value >= self._last, 'STARTUP_CLOCK_ROLLBACK')
        self._last = value

    def _input(self, digest):
        value = A.read_guard_input(self.archive_store, digest, limits=self.limits,
                                   capture_limits=self.capture_limits)
        _need(control_digest(value.package['policy']) == self._profile_policy
              and value.package['baseline_before'].account_scope == self.profile.account_scope,
              'STARTUP_BINDING_CHANGED')
        return value

    def _completion(self, digest, expected):
        return A.read_guard_completion(self.archive_store, digest, expected_input_archive_digest=expected,
            limits=self.limits, capture_limits=self.capture_limits)

    def _provider(self, retained, receipt):
        r = retained.record
        return CommittedAccountProvider(package=retained.package, receipt=receipt,
            expected_guard_head=r.expected_guard_head, expected_baseline_head=r.expected_baseline_head,
            expected_control_head=r.expected_control_head, journal=self.journal,
            guard_store=self.guard_store, guard_head=self.guard_head,
            baseline_store=self.baseline_store, baseline_head=self.baseline_head)

    def _physical(self, tx, events):
        self.journal._check_paths()
        actual, size = self.journal._load(initialize=False)
        _need(tuple(actual) == tuple(events) == tx.events and size == tx._size,
              'STARTUP_DEPENDENCY_CHANGED')

    @staticmethod
    def _time_status(baseline, now):
        if now < baseline.asof:
            return 'REFUSED', 'STARTUP_CLOCK_ROLLBACK'
        if now.astimezone(KST).date() != baseline.asof.astimezone(KST).date():
            return 'REFUSED', 'STARTUP_POLICY_BOUNDARY'
        cutoff = _required_cutoff(baseline)
        if cutoff is not None and baseline.asof < cutoff <= now:
            return 'REFUSED', 'STARTUP_POLICY_BOUNDARY'
        if now - baseline.asof > timedelta(seconds=30):
            return 'STALE', 'STARTUP_STALE'
        return 'FRESH', ''

    @staticmethod
    def _completion_binding(saved, actual, events, now):
        receipt = saved.receipt
        pairs = {'transaction_id': receipt.transaction_id, 'guard_head': receipt.guard_head,
            'baseline_head': receipt.baseline_head, 'completion_head': saved.completion_head,
            'receipt_control_head': receipt.control_head, 'package_sha256': saved.package_sha256,
            'input_sha256': saved.input_sha256}
        _need(all(getattr(actual, k) == v for k, v in pairs.items()), 'STARTUP_BINDING_CHANGED')
        indices = {row['row_sha256']: i for i, row in enumerate(events)}
        _need(saved.observed_control_head in indices and receipt.control_head in indices
              and indices[saved.observed_control_head] >= indices[receipt.control_head],
              'STARTUP_BINDING_CHANGED')
        stamp = datetime.fromisoformat(events[indices[saved.observed_control_head]]['utc'])
        _need(stamp <= saved.recorded_at <= now, 'STARTUP_BINDING_CHANGED')

    @staticmethod
    def _stored(store, head, proposed=None):
        try:
            return store.load(expected_head=head), head
        except (ValueError, OSError):
            _need(proposed is not None and proposed != head, 'STARTUP_DURABLE_REFUSED')
            return store.load(expected_head=proposed), proposed

    def _inspect_loaded(self, retained, completed):
        self._configuration()
        record, package = retained.record, retained.package
        now = self._now()
        self.journal.snapshot()  # Existing journal/lock/anchor required; never bootstrap on startup.
        with self.journal.transaction() as tx:
            events = tx.events
            _fold(events)
            gh, bh = self.guard_head.read(), self.baseline_head.read()
            state = classify_restart(events, guard_head=gh, baseline_head=bh,
                expected_guard_head=record.expected_guard_head,
                expected_baseline_head=record.expected_baseline_head,
                expected_control_head=record.expected_control_head)
            pending = state.status.startswith('PENDING_')
            guard, stored_guard = self._stored(self.guard_store, gh,
                state.new_guard_sha256 if pending and gh == record.expected_guard_head else None)
            baseline, stored_baseline = self._stored(self.baseline_store, bh,
                state.new_baseline_sha256 if pending and bh == record.expected_baseline_head else None)
            current, reason = 'NOT_CHECKED', state.reason
            projection = None
            if state.status not in (REFUSED, DIVERGENCE):
                plan = plan_continuous_guard(guard, **package)
                proposed = plan.proposed_checkpoint
                _need(proposed.recorded_at == record.evaluated_at == package['now'],
                      'STARTUP_BINDING_CHANGED')
                _need(plan.input_sha256 == record.input_sha256
                      and plan.previous_guard_sha256 == record.expected_guard_head
                      and plan.previous_baseline_sha256 == record.expected_baseline_head,
                      'STARTUP_BINDING_CHANGED')
                if state.status != FRESH:
                    prepares = [row for row in events if row['kind'] == PREPARE
                                and row['data']['transaction_id'] == state.transaction_id]
                    _need(len(prepares) == 1, 'STARTUP_DURABLE_REFUSED')
                    expected = dict(input_sha256=record.input_sha256,
                        owner_sha256=content_digest((package['owner_before'], package['owner_after'])),
                        control_head_sha256=record.expected_control_head,
                        path_sha256=content_digest(package['path']), old_guard_sha256=record.expected_guard_head,
                        new_guard_sha256=proposed.state_sha256, old_baseline_sha256=record.expected_baseline_head,
                        new_baseline_sha256=proposed.baseline.state_digest)
                    expected['transaction_id'] = content_digest(tuple(sorted(expected.items())))
                    data = prepares[0]['data']
                    _need(all(data[k] == v for k, v in expected.items())
                          and data['path_start'] == _utc(package['path'].start)
                          and data['path_end'] == _utc(package['path'].end)
                          and data['halt_required'] is proposed.permanently_halted, 'STARTUP_BINDING_CHANGED')
            if state.status == CONSISTENT:
                if completed is None:
                    reason = 'STARTUP_COMPLETION_RECORD_REQUIRED'
                else:
                    provider = self._provider(retained, completed.record.receipt)
                    now = self._now()
                    actual = CommittedAccountProvider.inspect_committed(provider, now=now, transaction=tx)
                    self._completion_binding(completed.record, actual, events, now)
                    current, reason = self._time_status(baseline, now)
                    if current == 'FRESH':
                        # Generic read refusal is never used as evidence of stale integrity.
                        projection = CommittedAccountProvider.read(provider, now=now, transaction=tx)
            elif completed is not None:
                _need(False, 'STARTUP_BINDING_CHANGED')
            _need(self.guard_head.read() == gh and self.baseline_head.read() == bh
                  and self.guard_store.load(expected_head=stored_guard) == guard
                  and self.baseline_store.load(expected_head=stored_baseline) == baseline
                  and self.guard_head.read() == gh and self.baseline_head.read() == bh,
                  'STARTUP_DEPENDENCY_CHANGED')
            self._physical(tx, events)
            self._configuration()
            finished = self._now()
            if events:
                _need(finished >= datetime.fromisoformat(events[-1]['utc']), 'STARTUP_CLOCK_ROLLBACK')
            if current == 'FRESH':
                current, reason = self._time_status(baseline, finished)
                obs = projection.observation
                if current == 'FRESH' and (abs(finished-obs.server_time) > timedelta(seconds=60)
                        or finished.astimezone(KST).date() != obs.server_time.astimezone(KST).date()):
                    current, reason = 'STALE', 'STARTUP_STALE'
            return StartupInspection(input_archive_digest=retained.archive_digest,
                completion_archive_digest=None if completed is None else completed.archive_digest,
                durable_status=state.status, current_status=current, reason=reason,
                transaction_id=state.transaction_id or None,
                observed_control_head=events[-1]['row_sha256'] if events else GENESIS,
                asof=package['interval'].end, inspected_at=finished)

    def _inspect(self, input_digest, completion_digest):
        retained = self._input(input_digest)
        completed = None if completion_digest is None else self._completion(completion_digest, input_digest)
        first = self._inspect_loaded(retained, completed)
        after = self._input(input_digest)
        final = None if completed is None else self._completion(completion_digest, input_digest)
        _need(after.record_sha256 == retained.record_sha256
              and (final is None or final.record_sha256 == completed.record_sha256),
              'STARTUP_DEPENDENCY_CHANGED')
        result = self._inspect_loaded(after, final)
        _need(first.transaction_id in (None, result.transaction_id), 'STARTUP_DEPENDENCY_CHANGED')
        return result, after, final

    @_exact
    def inspect(self, input_archive_digest, completion_archive_digest=None):
        _need(self._work.acquire(blocking=False), 'STARTUP_DEPENDENCY_CHANGED')
        try:
            return self._inspect(input_archive_digest, completion_archive_digest)[0]
        except CommittedStartupError:
            raise
        except _ERRORS:
            raise CommittedStartupError('STARTUP_DURABLE_REFUSED') from None
        finally:
            self._work.release()

    @_exact
    def commit_input(self, input_archive_digest):
        _need(self._work.acquire(blocking=False), 'STARTUP_DEPENDENCY_CHANGED')
        try:
            self._configuration()
            retained = self._input(input_archive_digest)
            check = self._inspect_loaded(retained, None)
            _need(check.durable_status not in (REFUSED, DIVERGENCE), 'STARTUP_DURABLE_REFUSED')
            r = retained.record
            receipt = commit_continuous_guard(retained.package, now=self._now(),
                expected_guard_head=r.expected_guard_head, expected_baseline_head=r.expected_baseline_head,
                expected_control_head=r.expected_control_head, journal=self.journal,
                guard_store=self.guard_store, guard_head=self.guard_head,
                baseline_store=self.baseline_store, baseline_head=self.baseline_head,
                expected_evaluated_at=r.evaluated_at)
            return A.record_guard_completion(self.archive_store, input_archive_digest, receipt,
                journal=self.journal, guard_store=self.guard_store, guard_head=self.guard_head,
                baseline_store=self.baseline_store, baseline_head=self.baseline_head, clock=self._now,
                limits=self.limits, capture_limits=self.capture_limits)
        except CommittedStartupError:
            raise
        except _ERRORS:
            raise CommittedStartupError('STARTUP_DURABLE_REFUSED') from None
        finally:
            self._work.release()

    def _runtime(self, retained, completed):
        binding = (retained.archive_digest, retained.record_sha256,
                   completed.archive_digest, completed.record_sha256)
        if self._binding is not None:
            _need(binding == self._binding, 'STARTUP_BINDING_CHANGED')
            self._configuration()
            return
        provider = self._provider(retained, completed.record.receipt)
        controller = Controller(journal=self.journal, account_provider=provider,
            policy=retained.package['policy'], adapters=self.adapters,
            session_provider=self.session_provider, clock=self.clock)
        runner = Runner(profile=self.profile, quote_provider=_no_quote, account_provider=provider,
            mode='rehearsal', controller=controller, isolated_state_root=self.root, clock=self.clock)
        self.provider, self.controller, self.runner, self._binding = provider, controller, runner, binding
        self._runtime_pins = (provider, controller, runner)

    @staticmethod
    def _rows(retained):
        account = retained.package['account_capture'].endpoint_accounts[0]
        rows = tuple(row for page in account.pages if page.kind == 'orders' for row in page.rows)
        _need(len(rows) <= MAX_STARTUP_ORDERS, 'STARTUP_RESOURCE_LIMIT')
        return account, rows

    @staticmethod
    def _mismatch(rec, row):
        order = rec['order']
        return (row.client_id != order.client_id or (row.market, row.symbol, row.side) !=
                (order.market, order.symbol, order.side) or row.quantity != order.quantity or row.limit_price != order.limit_price
                or (rec['venue_order_id'] and row.order_id != rec['venue_order_id']))

    def _assess_orders(self, orders, broker_rows, attempted, events, start_sequence):
        unresolved, external, opened = set(), set(), set()
        rows = {row.client_id: row for row in broker_rows if row.client_id}
        recent = {r['data']['client_id'] for r in events[start_sequence:] if r['kind'] == 'reconciled'}
        for row in broker_rows:
            if row.status in ('open', 'partial') and (not row.client_id or row.client_id not in orders):
                external.add(row.order_id)
        for client, rec in orders.items():
            row = rows.get(client)
            status = rec['status']
            if status in ('RESERVED', 'DISPATCHING', 'UNKNOWN'):
                unresolved.add(client)
            if row is not None:
                mapped = {'open': 'ACKNOWLEDGED', 'partial': 'PARTIAL', 'filled': 'FILLED',
                          'canceled': 'CANCELED', 'rejected': 'REJECTED'}[row.status]
                if self._mismatch(rec, row) or row.filled_quantity != rec['filled'] or status != mapped:
                    unresolved.add(client)
                elif row.status in ('open', 'partial'):
                    opened.add(client)
                    if client not in recent:
                        unresolved.add(client)
            elif rec['venue_order_id']:
                unresolved.add(client)
            if client in attempted and client not in recent:
                unresolved.add(client)
            if rec['order'].account_scope != self.profile.account_scope or rec['order'].venue != 'upbit':
                unresolved.add(client)
        return tuple(sorted(unresolved)), tuple(sorted(external)), tuple(sorted(opened))

    @_exact
    def reconcile(self, input_archive_digest, completion_archive_digest):
        _need(self._work.acquire(blocking=False), 'STARTUP_DEPENDENCY_CHANGED')
        try:
            inspection, retained, completed = self._inspect(input_archive_digest, completion_archive_digest)
            if inspection.durable_status != CONSISTENT or inspection.current_status != 'FRESH':
                return StartupResult(inspection=inspection, status='BLOCKED',
                    reason=inspection.reason or 'STARTUP_DURABLE_REFUSED', attempted_reconciliations=0,
                    unresolved_client_ids=(), external_order_ids=(), open_client_ids=(), holdings=(),
                    final_control_head=inspection.observed_control_head, completed_at=inspection.inspected_at)
            self._runtime(retained, completed)
            _need((self.provider, self.controller, self.runner) == self._runtime_pins,
                  'STARTUP_DEPENDENCY_CHANGED')
            self._configuration()
            first = Controller.read_committed_account(self.controller, now=self._now())
            self._completed(first)
            _need(first.committed.transaction_id == inspection.transaction_id, 'STARTUP_BINDING_CHANGED')
            account, broker_rows = self._rows(retained)
            with self.journal.transaction() as tx:
                before = tx.events
                orders = _fold(before)[0]
                _need(len(orders) <= MAX_STARTUP_ORDERS, 'STARTUP_RESOURCE_LIMIT')
                start_sequence = len(before)
                # Local never-sent reservations cannot be released against actual contrary evidence.
                conflicting = {row.client_id for row in broker_rows if row.client_id in orders
                    and (orders[row.client_id]['status'] == 'RESERVED'
                         or self._mismatch(orders[row.client_id], row))}
                conflicting.update(client for client, rec in orders.items()
                    if rec['order'].account_scope != self.profile.account_scope or rec['order'].venue != 'upbit')
                foreign = {row.order_id for row in broker_rows if row.status in ('open', 'partial')
                    and (not row.client_id or row.client_id not in orders)}
                self._physical(tx, before)
            attempted = set()
            if not conflicting and not foreign:
                for client, rec in sorted(orders.items()):
                    self._configuration()
                    now = self._now()
                    if rec['status'] == 'RESERVED' and client.startswith(self.runner._namespace):
                        Controller.cancel(self.controller, client, now=now)
                    elif _view(rec).status in _ACTIVE and rec['status'] != 'RESERVED':
                        Controller.reconcile(self.controller, client, now=now)
                        attempted.add(client)
            # Revalidate original dependency bytes after status work, outside the Journal lock.
            checked_input = self._input(input_archive_digest)
            checked_completion = self._completion(completion_archive_digest, input_archive_digest)
            _need(checked_input.record_sha256 == retained.record_sha256
                  and checked_completion.record_sha256 == completed.record_sha256,
                  'STARTUP_DEPENDENCY_CHANGED')
            # Actual owner/account check after status work; no stale observation is restamped.
            final = Controller.read_committed_account(self.controller, now=self._now())
            self._completed(final)
            _need(final.committed.transaction_id == inspection.transaction_id, 'STARTUP_BINDING_CHANGED')
            with self.journal.transaction() as tx:
                actual = CommittedAccountProvider.inspect_committed(self.provider, now=self._now(), transaction=tx)
                events = tx.events
                self._completion_binding(completed.record, actual, events, self._last)
                final_baseline = self.baseline_store.load(expected_head=actual.baseline_head)
                current = _fold(events)[0]
                _need(len(current) <= MAX_STARTUP_ORDERS, 'STARTUP_RESOURCE_LIMIT')
                unresolved, external, opened = self._assess_orders(current, broker_rows, attempted, events, start_sequence)
                unresolved = tuple(sorted(set(unresolved) | conflicting))
                external = tuple(sorted(set(external) | foreign))
                self._physical(tx, events)
                head = events[-1]['row_sha256'] if events else GENESIS
            self._configuration()
            finished = self._now()
            _need(finished >= final.completed_at, 'STARTUP_CLOCK_ROLLBACK')
            # Reuse actual completion lifetime at the current clock via another real read,
            # rather than treating a successful historical inspection as fresh authority.
            last = Controller.read_committed_account(self.controller, now=finished)
            self._completed(last)
            _need(last.committed.transaction_id == inspection.transaction_id
                  and last.committed.observed_control_head == head, 'STARTUP_DEPENDENCY_CHANGED')
            self._configuration()
            finished = self._now()
            _need(finished >= last.completed_at, 'STARTUP_CLOCK_ROLLBACK')
            final_status, final_reason = self._time_status(final_baseline, finished)
            _need(final_status == 'FRESH', final_reason)
            _need(timedelta(0) <= finished-last.committed.owner_claim.observed_at <= timedelta(seconds=30)
                  and abs(finished-last.account.server_time) <= timedelta(seconds=60)
                  and finished.astimezone(KST).date() == last.account.server_time.astimezone(KST).date(),
                  'STARTUP_STALE')
            holdings = tuple(sorted((account.venue, row.base_currency, row.units)
                for row in account.positions))
            blocked = bool(unresolved or external)
            return StartupResult(inspection=replace(inspection, inspected_at=finished),
                status='BLOCKED' if blocked else 'RECONCILED_OPEN' if opened else 'RECONCILED',
                reason='STARTUP_ORDER_CONFLICT' if conflicting or external else
                       'STARTUP_RECONCILIATION_REQUIRED' if unresolved else '',
                attempted_reconciliations=len(attempted), unresolved_client_ids=unresolved,
                external_order_ids=external, open_client_ids=opened, holdings=holdings,
                final_control_head=head, completed_at=finished)
        except CommittedStartupError:
            raise
        except _ERRORS:
            raise CommittedStartupError('STARTUP_CURRENT_AUTHORITY_REFUSED') from None
        finally:
            self._work.release()
