"""Generation restrictions over real local commits and temporary signed owners.

Account pages, prices and coverage are explicitly synthetic fixture evidence.
No source authority, live account, network request or execution approval is
manufactured by the expected transaction ID. Only DryRunAdapter may dispatch.
"""
from contextlib import ExitStack
from dataclasses import replace
from datetime import timedelta
from unittest.mock import patch

from core.compliance import owner
from execution_control import controller as C
from execution_control.controller import Controller
from tests import compliance_fixtures as CF, control_committed_account as F
from tests.control_committed_completion import guard_files

SESSION = 'fixture-monitor'
REQUIRED = 'COMMITTED_COMPLETION_GENERATION_REQUIRED'
CHANGED = 'COMMITTED_COMPLETION_GENERATION_CHANGED'


def reserve(e, expected, *, at=None, order=None):
    return e.controller.reserve(order or e.order, e.rules, session_id=SESSION,
        now=e.now if at is None else at, expected_committed_transaction_id=expected)


def dispatch(e, expected, *, at=None):
    return e.controller.dispatch(e.order.client_id, now=e.now if at is None else at,
        expected_committed_transaction_id=expected)


def other_id(e):
    return ('0' if e.receipt.transaction_id[0] != '0' else '1') + e.receipt.transaction_id[1:]


def no_admission_effects(e, stack):
    for obj, name in ((owner, 'load_context'), (C.gate, 'permit'), (C, '_issue'),
                      (e.adapter, 'prepare')):
        stack.enter_context(patch.object(obj, name, side_effect=AssertionError('unexpected admission effect')))


def test_matching_actual_read_reducing_order_preserves_wire_and_guard_heads():
    with F.fixture(daily_stopped=True) as e:
        paired = e.controller.read_committed_account(now=e.now, session_id=SESSION)
        assert paired.risk is None and not paired.execution_ready
        expected = paired.committed.transaction_id
        before = guard_files(e)
        assert reserve(e, expected).status == 'RESERVED'
        assert dispatch(e, expected).status == 'ACKNOWLEDGED'
        assert guard_files(e) == before and len(e.adapter.requests) == 1
        rows = F.rows(e)
        assert not any(row['kind'] == 'risk_snapshot' for row in rows)
        held = next(row['data'] for row in rows if row['kind'] == 'reserved')
        sent = next(row['data'] for row in rows if row['kind'] == 'dispatching')
        assert set(held) == {'client_id', 'order_digest', 'order', 'rules', 'session_id',
                             'request_digest', 'permit_digest', 'trade_date'}
        assert set(sent) == {'client_id', 'order_digest', 'request_digest', 'permit_digest'}


def test_invalid_expectations_refuse_new_reserve_before_account_clock_or_admission():
    class Text(str):
        pass
    with F.fixture() as e:
        invalid = (False, 1, b'a' * 64, Text('a' * 64), '', 'a' * 63, 'a' * 65,
                   'A' * 64, 'g' * 64, 'a' * 64 + '\n', '\uff41' * 64)
        before = F.rows(e), guard_files(e)
        with ExitStack() as stack:
            no_admission_effects(e, stack)
            stack.enter_context(patch.object(e.provider, 'read', side_effect=AssertionError('read before admission')))
            stack.enter_context(patch.object(e.controller, '_completion_clock',
                                             side_effect=AssertionError('clock before admission')))
            for value in invalid:
                F.refused(lambda: reserve(e, value), REQUIRED)
        assert (F.rows(e), guard_files(e)) == before and not e.adapter.requests


def test_invalid_expectation_on_reserved_dispatch_preserves_reservation_and_permit():
    with F.fixture() as e:
        assert reserve(e, e.receipt.transaction_id).status == 'RESERVED'
        before = F.rows(e), dict(e.controller._permits)
        with ExitStack() as stack:
            no_admission_effects(e, stack)
            stack.enter_context(patch.object(e.provider, 'read', side_effect=AssertionError('read before admission')))
            for value in (True, b'a' * 64, 'A' * 64, 'a' * 63):
                F.refused(lambda: dispatch(e, value), REQUIRED)
        assert (F.rows(e), e.controller._permits) == before
        assert e.controller.states()[0].status == 'RESERVED' and not e.adapter.requests


def test_expected_generation_requires_same_constructor_admitted_exact_provider():
    with F.fixture() as e:
        assert reserve(e, e.receipt.transaction_id).status == 'RESERVED'
        actual = e.controller.read_committed_account(now=e.now, session_id=SESSION).account
        calls = []
        def legacy(at):
            calls.append(at)
            return actual
        controller = Controller(journal=e.s.journal, account_provider=legacy, policy=e.s.policy,
            adapters={'upbit': e.adapter}, session_provider=lambda _: None)
        new_order = replace(e.order, client_id='generation-legacy-new')
        before = F.rows(e)
        for source in (legacy, e.provider):
            controller.account_provider = source
            F.refused(lambda: controller.reserve(new_order, e.rules, session_id=SESSION, now=e.now,
                expected_committed_transaction_id=e.receipt.transaction_id), REQUIRED)
            F.refused(lambda: controller.dispatch(e.order.client_id, now=e.now,
                expected_committed_transaction_id=e.receipt.transaction_id), REQUIRED)
        e.controller.account_provider = legacy
        F.refused(lambda: reserve(e, e.receipt.transaction_id, order=new_order), REQUIRED)
        assert F.rows(e) == before and not calls and not e.adapter.requests


def test_actual_read_mismatch_refuses_before_owner_risk_permit_or_order_mutation():
    with F.fixture() as e:
        before = F.rows(e), guard_files(e)
        with ExitStack() as stack:
            no_admission_effects(e, stack)
            with patch.object(e.provider, 'read', wraps=e.provider.read) as actual:
                F.refused(lambda: reserve(e, other_id(e)), CHANGED)
                assert actual.call_count == 1
        assert (F.rows(e), guard_files(e)) == before
        assert reserve(e, e.receipt.transaction_id).status == 'RESERVED'
        before = F.rows(e), dict(e.controller._permits)
        with ExitStack() as stack:
            no_admission_effects(e, stack)
            with patch.object(e.provider, 'read', wraps=e.provider.read) as actual:
                F.refused(lambda: dispatch(e, other_id(e)), CHANGED)
                assert actual.call_count == 1
        assert (F.rows(e), e.controller._permits) == before and not e.adapter.requests


def test_matching_generation_does_not_replace_current_signed_owner_verification():
    with F.fixture() as e:
        CF.sign(e.key, 'age_of_majority', {'birth_date': '2000-01-01', 'evidence': 'updated fixture'})
        before = F.rows(e)
        F.refused(lambda: reserve(e, e.receipt.transaction_id), 'COMMITTED_ACCOUNT_OWNER_EPOCH_CHANGED')
        assert F.rows(e) == before and not e.adapter.requests


def test_matching_generation_does_not_bypass_guard_daily_stop_for_first_buy():
    with F.fixture(daily_stopped=True, spare_cash=True) as e:
        buy = replace(e.order, side='buy', client_id='generation-stopped-buy')
        with patch.object(C.gate, 'permit', side_effect=AssertionError('stopped buy reached permit')):
            F.refused(lambda: reserve(e, e.receipt.transaction_id, order=buy), 'risk policy blocks new entry')
        rows = F.rows(e)
        assert rows[-1]['kind'] == 'risk_snapshot' and rows[-1]['data']['daily_stopped']
        assert not any(row['kind'] == 'reserved' for row in rows) and not e.adapter.requests


def test_matching_generation_does_not_refresh_original_completion_lifetime():
    with F.fixture() as e:
        prepare = e.adapter.prepare
        def slow(*args, **kwargs):
            request = prepare(*args, **kwargs)
            e.clock_cell[0] = e.now + timedelta(seconds=31)
            return request
        before = F.rows(e)
        with patch.object(e.adapter, 'prepare', slow):
            F.refused(lambda: reserve(e, e.receipt.transaction_id), 'COMMITTED_COMPLETION_STALE')
        assert F.rows(e) == before and not e.adapter.requests


def test_existing_idempotent_and_terminal_status_views_keep_their_contract():
    with F.fixture() as e:
        reserved = reserve(e, None)
        before = F.rows(e)
        assert reserve(e, False) == reserved and F.rows(e) == before
        # RESERVED dispatch still performs new-operation admission.
        F.refused(lambda: dispatch(e, False), REQUIRED)
        sent = dispatch(e, None)
        before = F.rows(e)
        assert sent.status == 'ACKNOWLEDGED'
        assert reserve(e, object()) == sent and dispatch(e, object()) == sent
        assert F.rows(e) == before and len(e.adapter.requests) == 1


def test_actual_successor_before_reserve_rejects_old_judgment_then_allows_fresh_reduce():
    from tests.launch_committed_generation import advance
    with F.fixture() as e:
        old = e.controller.read_committed_account(now=e.now, session_id=SESSION)
        successor = advance(e)
        assert successor.receipt.transaction_id != old.committed.transaction_id
        before = F.rows(e), guard_files(e)
        F.refused(lambda: reserve(e, old.committed.transaction_id, at=successor.now), CHANGED)
        assert (F.rows(e), guard_files(e)) == before and not e.adapter.requests
        fresh = e.controller.read_committed_account(now=successor.now, session_id=SESSION)
        assert fresh.committed.transaction_id == successor.receipt.transaction_id and fresh.risk is None
        assert fresh.account.asof == successor.package['interval'].end
        assert reserve(e, fresh.committed.transaction_id, at=successor.now).status == 'RESERVED'
        assert dispatch(e, fresh.committed.transaction_id, at=successor.now).status == 'ACKNOWLEDGED'
        assert guard_files(e) == before[1] and len(e.adapter.requests) == 1


def test_actual_successor_after_reserve_does_not_dispatch_or_erase_old_reservation():
    from tests.launch_committed_generation import advance
    with F.fixture() as e:
        expected = e.controller.read_committed_account(now=e.now, session_id=SESSION).committed.transaction_id
        assert reserve(e, expected).status == 'RESERVED'
        successor = advance(e)
        before = F.rows(e), dict(e.controller._permits), guard_files(e)
        with patch.object(C, '_issue', side_effect=AssertionError('generation mismatch issued capability')):
            F.refused(lambda: dispatch(e, expected, at=successor.now), CHANGED)
        assert (F.rows(e), e.controller._permits, guard_files(e)) == before
        assert e.controller.states()[0].status == 'RESERVED' and not e.adapter.requests
        assert e.controller.cancel(e.order.client_id, now=successor.now).status == 'CANCELLED_LOCAL'
        assert not e.adapter.requests


def test_matching_generation_keeps_explicit_reducing_path_independent_of_halt():
    with F.fixture(prices=('110', '105', '115')) as e:
        current = e.controller.read_committed_account(now=e.now, session_id=SESSION)
        assert current.risk is None and current.account.risk.halted
        before = tuple(row for row in F.rows(e) if row['kind'] in ('risk_snapshot', 'halt'))
        assert reserve(e, current.committed.transaction_id).status == 'RESERVED'
        assert dispatch(e, current.committed.transaction_id).status == 'ACKNOWLEDGED'
        assert tuple(row for row in F.rows(e) if row['kind'] in ('risk_snapshot', 'halt')) == before
        assert len(e.adapter.requests) == 1
