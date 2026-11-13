"""Actual committed Controller completion checks in signed disposable fixtures.

Account pages/prices/coverage and the explicit clock are synthetic. Owner logs,
guard/baseline checkpoints, heads, journal transactions, gates and capability
consumption are real local implementations. No positive verifier is replaced,
no session/capability registry entry is manufactured, and no transport is used.
"""
from contextlib import ExitStack, contextmanager
from dataclasses import replace
from datetime import datetime, timedelta
from unittest.mock import patch

from core.compliance import model as M, owner
from execution_accounts.baseline_store import CheckpointStore
from execution_control import controller as C
from execution_control.controller import Controller
from execution_control.store import Journal, Transaction
from execution_launch.baseline_head import BaselineHead
from execution_launch.continuous_guard_commit import GuardCheckpointStore
from tests import compliance_fixtures as CF, control_committed_account as F
from tests import control_continuous_guard as GF


SESSION = 'completion-fixture'
STALE = 'COMMITTED_COMPLETION_STALE'
AUTHORITY = 'COMMITTED_COMPLETION_AUTHORITY_REFUSED'
PHASE = 'COMMITTED_COMPLETION_PHASE_CHANGED'
LOCAL_FAILED = 'COMMITTED_COMPLETION_LOCAL_RECORD_FAILED'
INVALID = 'COMMITTED_COMPLETION_CLOCK_INVALID'
ROLLBACK = 'COMMITTED_COMPLETION_CLOCK_ROLLBACK'
BOUNDARY = 'COMMITTED_COMPLETION_POLICY_BOUNDARY'


def refused(call, expected):
    try:
        call()
    except (ValueError, RuntimeError) as exc:
        allowed = (expected,) if isinstance(expected, str) else expected
        assert str(exc) in allowed, (str(exc), allowed)
        return str(exc)
    raise AssertionError('completion boundary unexpectedly admitted the operation')


def reserve(e):
    return e.controller.reserve(e.order, e.rules, session_id=getattr(e, 'session_id', SESSION), now=e.now)


def dispatch(e):
    return e.controller.dispatch(e.order.client_id, now=e.now)


def order_rows(e):
    return tuple(row for row in e.s.journal.snapshot()
                 if row['data'].get('client_id') == e.order.client_id)


def guard_files(e):
    roots = (e.s.bstore._root, e.s.gstore._root, e.s.bhead._dir, e.s.ghead._dir)
    return {(index, str(path.relative_to(root))): path.read_bytes()
            for index, root in enumerate(roots) for path in root.rglob('*') if path.is_file()}


def restart(e):
    return Controller(journal=e.s.journal, account_provider=e.provider, policy=e.s.policy,
        adapters={'upbit': e.adapter}, session_provider=lambda _: None, clock=e.clock)


@contextmanager
def issued_buy_fixture():
    """Actual issuer + signed arm BEFORE capture, with explicit small synthetic terms.

    There is no approved-result substitution: the real odds simulation must
    succeed, the real issuer writes its row/registers its object, and the guard
    commits after that actual journal prefix and signed owner head.
    """
    from core.odds import models
    from execution_control.model import InstrumentRules
    from execution_control.session import prepare_session
    from tests import odds_fixtures as OF
    policy = GF.policy(initial='50', activation='50')
    prepared = {}
    def configure(home, key, start):
        CF.approve(home, key, 'venues', OF.venues_with(upbit={'min_order': {'quote': {'KRW': 1}}}))
        at = start - timedelta(seconds=1)
        rules = InstrumentRules(venue='upbit', market='spot', symbol='KRW-BTC',
            lot_size=F.D('0.1'), tick_size=F.D(1), min_quantity=F.D('0.1'), min_notional_krw=F.D(1),
            fee_fraction=F.D(0), asof=at, source_digest='a' * 64)
        positions = M.Positions(equity_krw=100.0, holdings={('upbit', 'BTC'): 0.5},
            exposure={'upbit': M.Exposure(held_krw=50.0)})
        plan = OF.plan(stake_krw=100, target_krw=200, start=at.astimezone(M.KST).date(), horizon_days=1)
        series = OF.fresh_series(end=(plan.start - timedelta(days=1)).isoformat())
        inputs = OF.inputs(plan, series, now=at)
        seed = models.market_seed(models.data_hashes(series, inputs.replay), inputs.calendar_sha256,
                                 inputs.comparison_id, inputs.run_counter).hex()
        with OF.chunk(), OF.pilots():
            session = prepare_session(journal=Journal(), session_id='completion-buy', selected_plan=plan,
                inputs=inputs, positions=positions, policy=policy, instrument_rules=rules, now=at,
                selection_seed_hex=seed, account_scope=GF.SCOPE, market='spot', quote_currency='KRW',
                clock=lambda: at, positions_asof=at, expires_at=start + timedelta(seconds=3))
        CF.sign(key, 'session_armed', {'session_id': session.session_id}, M.iso_utc(at))
        prepared.update(session=session, rules=rules)
    with F.fixture(pol=policy, floor='65', spare_cash=True, configure=configure, control_prefix=True) as e:
        e.prepared, e.rules = prepared['session'], prepared['rules']
        e.session_id = e.prepared.session_id
        e.order = replace(e.order, side='buy', client_id='completion-issued-buy')
        e.controller.session_provider = lambda _: e.prepared
        assert e.prepared.expires_at == e.now + timedelta(seconds=1)
        assert e.package['owner_after'].owner_head_sha256 == e.contexts[-1].owner.head[1]
        yield e


@contextmanager
def after_append(e, kind, callback):
    real = Transaction.append
    reached = []
    def append(tx, actual_kind, data, *, now):
        result = real(tx, actual_kind, data, now=now)
        if tx._journal is e.s.journal and actual_kind == kind:
            reached.append(result)
            callback(tx, result)
        return result
    with patch.object(Transaction, 'append', append):
        yield reached


def no_send(e, issued):
    assert issued.call_count == 0 and not e.adapter.requests


def local_rejected(e, state, expected_reason):
    assert state.status == 'REJECTED'
    rows = order_rows(e)
    assert [row['kind'] for row in rows] == ['reserved', 'dispatching', 'rejected']
    data = rows[-1]['data']
    assert data['venue_order_id'] == ''
    assert dict(data['metadata']) == {
        'tg_local_pre_send': 'not_called', 'tg_local_reason': expected_reason,
        'tg_dispatch_row': rows[-2]['row_sha256'],
    }
    assert e.controller.states()[0].status == 'REJECTED'


def test_exact_committed_provider_requires_explicit_clock_without_legacy_api_change():
    with F.fixture() as e:
        args = dict(journal=e.s.journal, account_provider=e.provider, policy=e.s.policy,
                    adapters={'upbit': e.adapter}, session_provider=lambda _: None)
        for clock in (None, True, e.now):
            refused(lambda clock=clock: Controller(**args, clock=clock),
                    'COMMITTED_COMPLETION_CLOCK_REQUIRED')
        observation = F.PF.read(e.s, e.provider, e.now).observation
        legacy = Controller(**(args | {'account_provider': lambda _: observation}))
        assert legacy.observe(now=e.now).high_watermark == observation.risk.prior_high_watermark
        assert not e.adapter.requests


def test_future_caller_request_and_invalid_initial_clocks_do_not_write_order_rows():
    for invalid in (None, True, 'not-a-time', datetime(2026, 11, 6)):
        with F.fixture() as e:
            e.clock_cell[0] = invalid
            with patch.object(C, '_issue', wraps=C._issue) as issued:
                refused(lambda: reserve(e), INVALID)
                no_send(e, issued)
            assert order_rows(e) == ()
    with F.fixture() as e:
        refused(lambda: e.controller.reserve(e.order, e.rules, session_id=SESSION,
            now=e.now + timedelta(microseconds=1)), 'COMMITTED_COMPLETION_REQUEST_FUTURE')
        assert order_rows(e) == ()


def test_raising_clock_has_fixed_diagnostic_and_no_private_error_text():
    def broken():
        raise OSError('invented private clock provider path')
    with F.fixture(clock=broken) as e:
        refused(lambda: reserve(e), INVALID)
        assert order_rows(e) == () and not e.adapter.requests


def test_internal_clock_watermark_survives_an_earlier_caller_now():
    with F.fixture() as e:
        e.clock_cell[0] = e.now + timedelta(seconds=1)
        e.controller.observe(now=e.now)
        before = e.s.journal.snapshot()
        e.clock_cell[0] = e.now
        refused(lambda: e.controller.observe(now=e.now), ROLLBACK)
        assert e.s.journal.snapshot() == before and not e.adapter.requests


def test_slow_actual_account_read_cannot_retimestamp_original_evidence():
    with F.fixture() as e:
        original = e.provider.read
        reached = []
        def slow(**kwargs):
            value = original(**kwargs)
            reached.append(value.observation.asof)
            e.clock_cell[0] = e.now + timedelta(seconds=30, microseconds=1)
            return value
        before = guard_files(e)
        with patch.object(e.provider, 'read', slow), patch.object(C, '_issue', wraps=C._issue) as issued:
            refused(lambda: reserve(e), STALE)
            no_send(e, issued)
        assert reached and set(reached) == {e.now}
        assert guard_files(e) == before and order_rows(e) == ()


def test_slow_initial_actual_owner_lookup_is_counted_in_original_lifetime():
    with F.fixture() as e:
        original = owner.load_context
        reached = []
        def slow(*args, **kwargs):
            value = original(*args, **kwargs)
            reached.append(value.owner.head)
            e.clock_cell[0] = e.now + timedelta(seconds=30, microseconds=1)
            return value
        with patch.object(owner, 'load_context', slow), patch.object(C, '_issue', wraps=C._issue) as issued:
            refused(lambda: reserve(e), STALE)
            no_send(e, issued)
        assert reached and order_rows(e) == ()


def test_exact_thirty_second_prepare_boundary_and_one_microsecond_over():
    for delta, accepted in ((timedelta(seconds=30), True),
                            (timedelta(seconds=30, microseconds=1), False)):
        with F.fixture() as e:
            assert e.package['owner_after'].observed_at == e.now
            original = e.adapter.prepare
            reached = []
            def delayed(*args, **kwargs):
                request = original(*args, **kwargs)
                reached.append(request)
                e.clock_cell[0] = e.now + delta
                return request
            with patch.object(e.adapter, 'prepare', delayed), patch.object(C, '_issue', wraps=C._issue) as issued:
                if accepted:
                    assert reserve(e).status == 'RESERVED'
                else:
                    refused(lambda: reserve(e), STALE)
                no_send(e, issued)
            assert len(reached) == 1
            assert [row['kind'] for row in order_rows(e)] == (['reserved'] if accepted else [])


def test_final_actual_owner_read_cannot_reset_prior_owner_check_age():
    with F.fixture() as e:
        real_owner, real_prepare = owner.load_context, e.adapter.prepare
        prepared, final_reads = [], []
        def prepare(*args, **kwargs):
            value = real_prepare(*args, **kwargs)
            prepared.append(value)
            e.clock_cell[0] = e.now + timedelta(seconds=20)
            return value
        def load(*args, **kwargs):
            value = real_owner(*args, **kwargs)
            if prepared:
                final_reads.append(value.owner.head)
                e.clock_cell[0] = e.now + timedelta(seconds=30, microseconds=1)
            return value
        with patch.object(e.adapter, 'prepare', prepare), patch.object(owner, 'load_context', load), \
             patch.object(C, '_issue', wraps=C._issue) as issued:
            refused(lambda: reserve(e), STALE)
            no_send(e, issued)
        assert len(prepared) == 1 and final_reads and order_rows(e) == ()


def test_prepare_clock_rollback_does_not_create_a_reservation():
    with F.fixture() as e:
        real = e.adapter.prepare
        def changed(*args, **kwargs):
            request = real(*args, **kwargs)
            e.clock_cell[0] = e.now - timedelta(microseconds=1)
            return request
        with patch.object(e.adapter, 'prepare', changed):
            refused(lambda: reserve(e), ROLLBACK)
        assert order_rows(e) == () and not e.adapter.requests


def test_slow_reserved_append_retains_actual_row_but_does_not_return_fresh_success():
    with F.fixture() as e:
        before = guard_files(e)
        with after_append(e, 'reserved', lambda *_: e.clock_cell.__setitem__(
                0, e.now + timedelta(seconds=31))) as reached, \
             patch.object(C, '_issue', wraps=C._issue) as issued:
            refused(lambda: reserve(e), STALE)
            no_send(e, issued)
        assert len(reached) == 1 and e.controller.states()[0].status == 'RESERVED'
        with patch.object(C, '_issue', wraps=C._issue) as issued:
            refused(lambda: dispatch(e), (STALE, 'COMMITTED_ACCOUNT_EVIDENCE_REFUSED'))
            no_send(e, issued)
        assert [row['kind'] for row in order_rows(e)] == ['reserved']
        assert guard_files(e) == before


def test_slow_actual_risk_snapshot_retains_protection_without_reporting_fresh_observation():
    with F.fixture(daily_stopped=True) as e:
        before = guard_files(e)
        with after_append(e, 'risk_snapshot', lambda *_: e.clock_cell.__setitem__(
                0, e.now + timedelta(seconds=31))) as reached:
            refused(lambda: e.controller.observe(now=e.now), STALE)
        assert len(reached) == 1 and reached[0]['data']['daily_stopped'] is True
        rows = e.s.journal.snapshot()
        assert rows[-1] == reached[0] and rows[-1]['data']['high_watermark'] == '101'
        assert order_rows(e) == () and not e.adapter.requests and guard_files(e) == before


def test_slow_dispatching_append_records_definite_local_no_send_and_never_resends():
    with F.fixture() as e:
        assert reserve(e).status == 'RESERVED'
        before = guard_files(e)
        with after_append(e, 'dispatching', lambda *_: e.clock_cell.__setitem__(
                0, e.now + timedelta(seconds=31))) as reached, \
             patch.object(C, '_issue', wraps=C._issue) as issued:
            local_rejected(e, dispatch(e), STALE)
            no_send(e, issued)
        assert len(reached) == 1 and guard_files(e) == before
        with patch.object(C, '_issue', wraps=C._issue) as issued:
            assert dispatch(e).status == 'REJECTED'
            assert restart(e).dispatch(e.order.client_id, now=e.now).status == 'REJECTED'
            no_send(e, issued)


def test_actual_owner_epoch_code_or_limits_change_during_prepare_refuses_reservation():
    for change in ('owner_head', 'code', 'limits'):
        with F.fixture() as e:
            real = e.adapter.prepare
            def changed(*args, **kwargs):
                request = real(*args, **kwargs)
                if change == 'owner_head':
                    CF.sign(e.key, 'age_of_majority', {'birth_date': '2000-01-01', 'evidence': 'completion fixture'},
                            M.iso_utc(e.now))
                elif change == 'code':
                    CF.other_code(e.key, M.iso_utc(e.now))
                else:
                    CF.sign(e.key, 'limit_set', {'total_loss_floor_krw': 99.0, 'daily_loss_krw': 9.0},
                            M.iso_utc(e.now))
                return request
            with patch.object(e.adapter, 'prepare', changed), patch.object(C, '_issue', wraps=C._issue) as issued:
                refused(lambda: reserve(e), AUTHORITY)
                no_send(e, issued)
            assert order_rows(e) == ()


def test_actual_owner_change_after_dispatching_is_provable_local_no_send():
    with F.fixture() as e:
        reserve(e)
        def changed(*_):
            CF.sign(e.key, 'age_of_majority', {'birth_date': '2000-01-01', 'evidence': 'after dispatch row'},
                    M.iso_utc(e.now))
        with after_append(e, 'dispatching', changed), patch.object(C, '_issue', wraps=C._issue) as issued:
            local_rejected(e, dispatch(e), AUTHORITY)
            no_send(e, issued)


def test_actual_key_or_signed_log_damage_after_dispatching_records_only_local_no_send():
    for change in ('key', 'log'):
        with F.fixture() as e:
            reserve(e)
            def changed(*_):
                if change == 'key':
                    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
                    CF.write_pubkey(owner.PUBKEY_PATH, Ed25519PrivateKey.from_private_bytes(b'Z' * 32))
                else:
                    path = owner.log_path()
                    path.write_bytes(path.read_bytes() + b'{incomplete fixture owner row\n')
            with after_append(e, 'dispatching', changed), patch.object(C, '_issue', wraps=C._issue) as issued:
                local_rejected(e, dispatch(e), AUTHORITY)
                no_send(e, issued)


def test_slow_actual_final_owner_after_dispatching_is_checked_after_its_return():
    with F.fixture() as e:
        reserve(e)
        dispatched, loaded = [], []
        real = owner.load_context
        def load(*args, **kwargs):
            value = real(*args, **kwargs)
            if dispatched:
                loaded.append(value.owner.head)
                e.clock_cell[0] = e.now + timedelta(seconds=30, microseconds=1)
            return value
        with after_append(e, 'dispatching', lambda tx, row: dispatched.append(row)), \
             patch.object(owner, 'load_context', load), patch.object(C, '_issue', wraps=C._issue) as issued:
            local_rejected(e, dispatch(e), STALE)
            no_send(e, issued)
        assert len(dispatched) == 1 and loaded


def test_invalid_or_rollback_clock_after_dispatching_never_fabricates_terminal_time():
    for value, code in ((None, INVALID), ('not-a-time', INVALID), ('rollback', ROLLBACK)):
        with F.fixture() as e:
            reserve(e)
            after = e.now - timedelta(microseconds=1) if value == 'rollback' else value
            with after_append(e, 'dispatching', lambda *_: e.clock_cell.__setitem__(0, after)), \
                 patch.object(C, '_issue', wraps=C._issue) as issued:
                refused(lambda: dispatch(e), code)
                no_send(e, issued)
            assert [row['kind'] for row in order_rows(e)] == ['reserved', 'dispatching']
            assert e.controller.states()[0].status == 'UNKNOWN'
            assert restart(e).dispatch(e.order.client_id, now=e.now).status == 'UNKNOWN'
            assert not e.adapter.requests


def test_local_rejection_append_failure_keeps_uncertainty_and_no_restart_create():
    with F.fixture() as e:
        reserve(e)
        real = Transaction.append
        def failing(tx, kind, data, *, now):
            if tx._journal is e.s.journal and kind == 'rejected':
                raise OSError('invented rejection disk failure')
            result = real(tx, kind, data, now=now)
            if tx._journal is e.s.journal and kind == 'dispatching':
                e.clock_cell[0] = e.now + timedelta(seconds=31)
            return result
        with patch.object(Transaction, 'append', failing), patch.object(C, '_issue', wraps=C._issue) as issued:
            refused(lambda: dispatch(e), LOCAL_FAILED)
            no_send(e, issued)
        assert [row['kind'] for row in order_rows(e)] == ['reserved', 'dispatching']
        assert restart(e).dispatch(e.order.client_id, now=e.now).status == 'UNKNOWN'
        assert not e.adapter.requests


def test_durable_local_rejection_response_loss_never_rewinds_committed_terminal_fact():
    with F.fixture() as e:
        reserve(e)
        real = Transaction.append
        def lost(tx, kind, data, *, now):
            result = real(tx, kind, data, now=now)
            if tx._journal is e.s.journal and kind == 'dispatching':
                e.clock_cell[0] = e.now + timedelta(seconds=31)
            if tx._journal is e.s.journal and kind == 'rejected':
                raise OSError('invented durable result response loss')
            return result
        with patch.object(Transaction, 'append', lost), patch.object(C, '_issue', wraps=C._issue) as issued:
            refused(lambda: dispatch(e), LOCAL_FAILED)
            no_send(e, issued)
        assert [row['kind'] for row in order_rows(e)] == ['reserved', 'dispatching', 'rejected']
        assert restart(e).dispatch(e.order.client_id, now=e.now).status == 'REJECTED'
        assert not e.adapter.requests


def test_extra_actual_tail_invalidates_private_dispatch_phase_without_terminal_release():
    with F.fixture() as e:
        reserve(e)
        real = Transaction.append
        def changed(tx, _):
            real(tx, 'kill', {'session_id': 'unrelated-session', 'reason': 'fixture tail extension'}, now=e.now)
        with after_append(e, 'dispatching', changed), patch.object(C, '_issue', wraps=C._issue) as issued:
            refused(lambda: dispatch(e), PHASE)
            no_send(e, issued)
        assert [row['kind'] for row in order_rows(e)] == ['reserved', 'dispatching']
        assert e.s.journal.snapshot()[-1]['kind'] == 'kill'
        assert restart(e).dispatch(e.order.client_id, now=e.now).status == 'UNKNOWN'


def test_torn_actual_journal_after_dispatching_is_preserved_and_never_called_rejected():
    with F.fixture() as e:
        reserve(e)
        path = e.s.journal._root / 'journal.jsonl'
        def changed(*_):
            with path.open('ab') as handle:
                handle.write(b'{incomplete fixture tail')
        with after_append(e, 'dispatching', changed), patch.object(C, '_issue', wraps=C._issue) as issued:
            refused(lambda: dispatch(e), (PHASE, LOCAL_FAILED))
            no_send(e, issued)
        raw = path.read_bytes()
        assert raw.endswith(b'{incomplete fixture tail') and b'"kind":"rejected"' not in raw
        try:
            restart(e).dispatch(e.order.client_id, now=e.now)
        except (ValueError, RuntimeError):
            pass
        else:
            raise AssertionError('torn actual journal was accepted')
        assert path.read_bytes() == raw and not e.adapter.requests


def test_actual_adapter_entry_failure_stays_unknown_and_never_claims_local_no_send():
    with F.fixture() as e:
        reserve(e)
        real = e.adapter.dispatch
        def uncertain(*args, **kwargs):
            real(*args, **kwargs)
            raise OSError('invented response loss after actual dry capability consumption')
        with patch.object(e.adapter, 'dispatch', uncertain), patch.object(C, '_issue', wraps=C._issue) as issued:
            assert dispatch(e).status == 'UNKNOWN'
            assert issued.call_count == 1 and len(e.adapter.requests) == 1
        rows = order_rows(e)
        assert [row['kind'] for row in rows] == ['reserved', 'dispatching', 'unknown']
        assert not dict(rows[-1]['data']['metadata']).get('tg_local_pre_send')
        assert restart(e).dispatch(e.order.client_id, now=e.now).status == 'UNKNOWN'
        assert len(e.adapter.requests) == 1


def test_fresh_reducing_order_still_consumes_one_capability_under_daily_stop_and_kill():
    for stopped, killed in ((False, False), (True, False), (True, True)):
        with F.fixture(daily_stopped=stopped) as e:
            if killed:
                with e.s.journal.transaction() as tx:
                    tx.append('kill', {'session_id': SESSION, 'reason': 'fixture entry kill'}, now=e.now)
            before = guard_files(e)
            with patch.object(C, '_issue', wraps=C._issue) as issued:
                assert reserve(e).status == 'RESERVED'
                assert dispatch(e).status == 'ACKNOWLEDGED'
                assert dispatch(e).status == 'ACKNOWLEDGED'
                assert issued.call_count == 1 and len(e.adapter.requests) == 1
            assert e.adapter.requests[0].operation == 'create' and guard_files(e) == before


def test_committed_reads_never_advance_heads_reinitialize_or_nest_journal_transactions():
    with F.fixture() as e:
        before = guard_files(e)
        real = Journal.transaction
        entered = []
        @contextmanager
        def checked(journal):
            assert not entered, 'nested control transaction'
            entered.append(journal)
            try:
                with real(journal) as tx:
                    yield tx
            finally:
                entered.pop()
        with ExitStack() as scope:
            for cls, name in ((CheckpointStore, 'commit'), (CheckpointStore, 'seed'),
                              (GuardCheckpointStore, 'commit'), (GuardCheckpointStore, 'seed'),
                              (BaselineHead, 'compare_and_set'), (BaselineHead, 'initialize_reviewed_head'),
                              (Journal, 'snapshot')):
                scope.enter_context(patch.object(cls, name, side_effect=AssertionError('unexpected source mutation/read')))
            scope.enter_context(patch.object(Journal, 'transaction', checked))
            e.controller.observe(now=e.now)
            assert reserve(e).status == 'RESERVED'
            assert dispatch(e).status == 'ACKNOWLEDGED'
        assert guard_files(e) == before and len(e.adapter.requests) == 1


def test_recovery_cutoff_and_midnight_crossing_reject_old_policy_epoch():
    for start, policy in ((datetime(2026, 11, 6, 21, 59, 55, tzinfo=M.KST), GF.policy(recovery=True)),
                          (datetime(2026, 11, 6, 23, 59, 55, tzinfo=M.KST), GF.policy())):
        with F.fixture(start=start, pol=policy) as e:
            real = e.adapter.prepare
            def changed(*args, **kwargs):
                request = real(*args, **kwargs)
                e.clock_cell[0] = e.now + timedelta(seconds=3)
                return request
            with patch.object(e.adapter, 'prepare', changed), patch.object(C, '_issue', wraps=C._issue) as issued:
                refused(lambda: reserve(e), BOUNDARY)
                no_send(e, issued)
            assert order_rows(e) == ()


def test_same_owner_head_midnight_effective_limit_change_is_not_a_fresh_epoch():
    start = datetime(2026, 11, 6, 23, 59, 55, tzinfo=M.KST)
    def schedule(home, key, at):
        CF.sign(key, 'limit_set', {'total_loss_floor_krw': 90.0, 'daily_loss_krw': 20.0},
                M.iso_utc(at - timedelta(hours=1)))
    with F.fixture(start=start, configure=schedule) as e:
        original = e.adapter.prepare
        context = e.contexts[-1]
        assert context.owner.limits['total_loss_floor_krw'] == 100.0
        def changed(*args, **kwargs):
            request = original(*args, **kwargs)
            e.clock_cell[0] = e.now + timedelta(seconds=3)
            return request
        with patch.object(e.adapter, 'prepare', changed):
            refused(lambda: reserve(e), BOUNDARY)
        actual = owner.load_context(e.clock_cell[0], M.Positions(equity_krw=101.0,
            holdings={('upbit', 'BTC'): 1.0}), session_id=SESSION)
        assert actual.owner.head == context.owner.head
        assert actual.owner.limits['total_loss_floor_krw'] == 90.0
        assert actual.owner.limits['daily_loss_krw'] == 20.0
        assert order_rows(e) == () and not e.adapter.requests


def test_actual_rules_expiry_during_prepare_is_rechecked_without_aging_account():
    with F.fixture() as e:
        e.rules = replace(e.rules, asof=e.now - timedelta(minutes=5) + timedelta(seconds=1))
        real = e.adapter.prepare
        def changed(*args, **kwargs):
            request = real(*args, **kwargs)
            e.clock_cell[0] = e.now + timedelta(seconds=2)
            return request
        with patch.object(e.adapter, 'prepare', changed), patch.object(C, '_issue', wraps=C._issue) as issued:
            refused(lambda: reserve(e), AUTHORITY)
            no_send(e, issued)
        assert order_rows(e) == ()


def test_actual_guard_head_change_during_prepare_refuses_without_advancing_other_state():
    with F.fixture() as e:
        real = e.adapter.prepare
        path = e.s.ghead._dir / 'head.json'
        original = path.read_bytes()
        def changed(*args, **kwargs):
            request = real(*args, **kwargs)
            path.write_bytes(b'{invalid fixture head')
            return request
        with patch.object(e.adapter, 'prepare', changed), patch.object(C, '_issue', wraps=C._issue) as issued:
            refused(lambda: reserve(e), AUTHORITY)
            no_send(e, issued)
        assert path.read_bytes() != original and order_rows(e) == ()


def test_genuine_issued_and_signed_session_allows_one_fresh_dry_buy():
    with issued_buy_fixture() as e:
        prepared_rows = [row for row in e.s.journal.snapshot() if row['kind'] == 'session_prepared']
        assert len(prepared_rows) == 1 and prepared_rows[0]['data']['session_id'] == e.prepared.session_id
        assert prepared_rows[0]['seq'] < next(row['seq'] for row in e.s.journal.snapshot()
                                             if row['kind'] == 'continuous_guard_prepare')
        before = guard_files(e)
        with patch.object(C, '_issue', wraps=C._issue) as issued:
            assert reserve(e).status == 'RESERVED'
            assert dispatch(e).status == 'ACKNOWLEDGED'
            assert dispatch(e).status == 'ACKNOWLEDGED'
            assert issued.call_count == 1 and len(e.adapter.requests) == 1
        assert guard_files(e) == before


def test_genuine_session_expiry_is_exclusive_at_prepare_completion():
    for delta, accepted in ((timedelta(seconds=1) - timedelta(microseconds=1), True),
                            (timedelta(seconds=1), False)):
        with issued_buy_fixture() as e:
            real = e.adapter.prepare
            reached = []
            def changed(*args, **kwargs):
                request = real(*args, **kwargs)
                reached.append(request)
                e.clock_cell[0] = e.now + delta
                return request
            with patch.object(e.adapter, 'prepare', changed), patch.object(C, '_issue', wraps=C._issue) as issued:
                if accepted:
                    assert reserve(e).status == 'RESERVED'
                else:
                    refused(lambda: reserve(e), AUTHORITY)
                no_send(e, issued)
            assert len(reached) == 1
            assert [row['kind'] for row in order_rows(e)] == (['reserved'] if accepted else [])


def test_genuine_session_expiry_after_dispatching_proves_local_no_send():
    with issued_buy_fixture() as e:
        reserve(e)
        with after_append(e, 'dispatching', lambda *_: e.clock_cell.__setitem__(0, e.prepared.expires_at)), \
             patch.object(C, '_issue', wraps=C._issue) as issued:
            local_rejected(e, dispatch(e), AUTHORITY)
            no_send(e, issued)


def test_actual_risk_suffix_is_rechecked_without_second_permit_or_risk_snapshot():
    for blocked in (False, True):
        with issued_buy_fixture() as e:
            original = e.adapter.prepare
            added = []
            def changed(*args, **kwargs):
                request = original(*args, **kwargs)
                # The same actual active transaction is required: do not nest a
                # journal acquisition or counterfeit an issued phase/session.
                from execution_control import store as S
                tx = S._THREAD.transaction
                last = [row for row in tx.events if row['kind'] == 'risk_snapshot'][-1]
                data = dict(last['data'])
                if blocked:
                    data.update(high_watermark='110', effective_floor='110', calculated_floor='110',
                                daily_stopped=False)
                added.append(tx.append('risk_snapshot', data, now=e.now))
                return request
            with patch.object(e.adapter, 'prepare', changed), patch.object(C.gate, 'permit', wraps=C.gate.permit) as permit, \
                 patch.object(C, '_issue', wraps=C._issue) as issued:
                if blocked:
                    refused(lambda: reserve(e), AUTHORITY)
                else:
                    assert reserve(e).status == 'RESERVED'
                no_send(e, issued)
                assert permit.call_count == 1
            assert len(added) == 1
            assert len([row for row in e.s.journal.snapshot() if row['kind'] == 'risk_snapshot']) == 2
            assert [row['kind'] for row in order_rows(e)] == ([] if blocked else ['reserved'])


def test_genuine_observed_terms_expiry_is_checked_after_actual_final_owner_load():
    from execution_accounts import instrument_terms as T
    from tests import launch_instrument_refresh as TF
    # Fake E1 response bytes enter the real source/parser/issuer. Clearing the
    # fixture registries isolates them; no positive entry is manually inserted.
    for delta, accepted in ((timedelta(seconds=1) - timedelta(microseconds=1), True),
                            (timedelta(seconds=1), False)):
        with F.fixture() as e, TF.registries():
            auth = TF.authority(account_scope=e.order.account_scope, lot_size=F.D('0.1'),
                min_quantity=F.D('0.1'), valid_from=e.now - timedelta(seconds=1),
                valid_until=e.now + timedelta(seconds=1))
            chance, instruments = TF.bodies(auth)
            for key in ('bid_fee', 'ask_fee', 'maker_bid_fee', 'maker_ask_fee'):
                chance[key] = '0'
            chance['market']['bid']['min_total'] = '1'
            chance['market']['ask']['min_total'] = '1'
            observed = TF.observed(e.now, auth=auth, chance=chance, instruments=instruments)
            resolved = T.observation_for_rules(observed.rules, account_scope=e.order.account_scope,
                                               now=e.now)
            # The genuine issuer identity is checked internally, then receipts
            # are reparsed into a fresh complete value rather than returned by identity.
            assert type(resolved) is T.TermsObservation and resolved == observed
            e.rules = observed.rules
            real_prepare, real_owner = e.adapter.prepare, owner.load_context
            prepared, final_reads = [], []
            def prepare(*args, **kwargs):
                request = real_prepare(*args, **kwargs)
                prepared.append(request)
                return request
            def load(*args, **kwargs):
                current = real_owner(*args, **kwargs)
                if prepared:
                    final_reads.append(current.owner.head)
                    e.clock_cell[0] = e.now + delta
                return current
            with patch.object(e.adapter, 'prepare', prepare), patch.object(owner, 'load_context', load), \
                 patch.object(C, '_issue', wraps=C._issue) as issued:
                if accepted:
                    assert reserve(e).status == 'RESERVED'
                else:
                    refused(lambda: reserve(e), AUTHORITY)
                no_send(e, issued)
            assert len(prepared) == 1 and final_reads
            assert [row['kind'] for row in order_rows(e)] == (['reserved'] if accepted else [])


def test_observe_rejects_changed_restrictive_risk_result_but_accepts_identical_actual_suffix():
    for restrictive in (False, True):
        with F.fixture() as e:
            real = Transaction.append
            inserted = []
            def append(tx, kind, data, *, now):
                row = real(tx, kind, data, now=now)
                if tx._journal is e.s.journal and kind == 'risk_snapshot' and not inserted:
                    changed = dict(row['data'])
                    if restrictive:
                        changed.update(high_watermark='110', effective_floor='110',
                                       calculated_floor='110', daily_stopped=False)
                    inserted.append(real(tx, 'risk_snapshot', changed, now=now))
                return row
            before = guard_files(e)
            with patch.object(Transaction, 'append', append), patch.object(C, '_issue', wraps=C._issue) as issued:
                if restrictive:
                    refused(lambda: e.controller.observe(now=e.now), AUTHORITY)
                else:
                    assert not e.controller.observe(now=e.now).new_entry_blocked
                no_send(e, issued)
            rows = e.s.journal.snapshot()
            assert len(inserted) == 1 and rows[-1] == inserted[0]
            assert len([row for row in rows if row['kind'] == 'risk_snapshot']) == 2
            assert not any(row['kind'] == 'halt' for row in rows)
            assert order_rows(e) == () and guard_files(e) == before


def test_existing_actual_halt_with_breached_floor_preserves_original_risk_result():
    with F.fixture(prices=('110', '105')) as e:
        before = guard_files(e)
        owner_before = owner.log_path().read_bytes()
        halt_rows = [row for row in e.s.journal.snapshot() if row['kind'] == 'halt']
        assert len(halt_rows) == 1 and halt_rows[0]['data']['floor'] == '110'
        with patch.object(C, '_issue', wraps=C._issue) as issued:
            first = e.controller.observe(now=e.now)
            second = e.controller.observe(now=e.now)
            no_send(e, issued)
        assert first == second and first.new_entry_blocked and first.protective_action_needed
        assert first.high_watermark == F.D('110') and first.effective_floor == F.D('110')
        # The legacy snapshot path reports both the existing latch and breach.
        # Completion comparison may normalize this duplicate, not rewrite the result.
        assert first.reasons.count('PERSISTENT_HALT') == 2
        assert [row for row in e.s.journal.snapshot() if row['kind'] == 'halt'] == halt_rows
        assert owner.log_path().read_bytes() == owner_before and guard_files(e) == before
        assert order_rows(e) == ()


def test_exact_committed_provider_cannot_be_swapped_for_a_callable_observation():
    for phase in ('observe', 'reserve', 'dispatch'):
        with F.fixture() as e:
            if phase == 'dispatch':
                assert reserve(e).status == 'RESERVED'
            original = e.provider
            actual_observation = F.PF.read(e.s, original, e.now).observation
            e.controller.account_provider = lambda _: actual_observation
            before = e.s.journal.snapshot()
            invoke = (lambda: e.controller.observe(now=e.now)) if phase == 'observe' else (
                (lambda: reserve(e)) if phase == 'reserve' else (lambda: dispatch(e)))
            with patch.object(C, '_issue', wraps=C._issue) as issued:
                refused(invoke, AUTHORITY)
                no_send(e, issued)
            assert e.s.journal.snapshot() == before
            if phase == 'dispatch':
                assert e.controller.states()[0].status == 'RESERVED'
