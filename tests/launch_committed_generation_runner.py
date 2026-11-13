"""Real successor commits through the exact committed Runner consumer.

Owner signatures, stores/heads, guard commit, publication, Controller and
DryRunAdapter are actual. Account/continuous coverage and study market data are
explicitly synthetic. The automatic strategy case proves warmup HOLD only;
explicit exits do not fabricate a strategy SELL or an entry/review approval.
"""
from contextlib import contextmanager
from dataclasses import replace
from datetime import timedelta
from unittest.mock import patch

from execution_control import controller as C
from execution_control.controller import Controller
from execution_launch import runner as R
from tests import control_committed_account as F
from tests import launch_committed_generation as G
from tests import launch_committed_runner as RF
from tests.control_committed_completion import guard_files
from tests.control_committed_observation import risk_rows


def order_rows(e):
    return tuple(row for row in F.rows(e) if row['kind'] in (
        'reserved', 'dispatching', 'acknowledged', 'rejected', 'unknown', 'cancelled_local'))


@contextmanager
def actual_pairs():
    actual, pairs = Controller.read_committed_account, []
    def read(controller, **kwargs):
        pair = actual(controller, **kwargs)
        pairs.append(pair)
        return pair
    with patch.object(Controller, 'read_committed_account', read):
        yield pairs


def test_explicit_exit_passes_the_original_actual_pair_generation_to_both_operations():
    with RF.fixture() as e, actual_pairs() as pairs:
        before = guard_files(e)
        with patch.object(e.controller, 'reserve', wraps=e.controller.reserve) as reserve, \
             patch.object(e.controller, 'dispatch', wraps=e.controller.dispatch) as dispatch, \
             patch.object(Controller, 'observe_committed', side_effect=AssertionError('exit entry-risk route')), \
             patch.object(C, '_issue', wraps=C._issue) as issue:
            state = e.runner.submit_exit(e.signal, now=e.now)
        assert state.status == 'ACKNOWLEDGED' and issue.call_count == len(RF.creates(e)) == 1
        assert len(pairs) == 1 and pairs[0].risk is None
        assert pairs[0].account is pairs[0].committed.observation
        assert pairs[0].account.asof == e.package['account_capture'].endpoint_accounts[0].observed_at
        for call in (reserve.call_args, dispatch.call_args):
            assert call.kwargs['expected_committed_transaction_id'] == pairs[0].committed.transaction_id
            assert call.kwargs['now'] == pairs[0].completed_at
        assert not risk_rows(e) and guard_files(e) == before


def test_successor_keeps_provider_identity_and_original_account_time_for_one_real_exit():
    with RF.fixture() as e:
        original_provider, original_controller = e.provider, e.controller
        original_time, original_receipt = e.now, e.receipt
        successor = G.advance(e)
        assert successor.receipt.transaction_id != original_receipt.transaction_id
        assert e.provider is original_provider and e.controller is original_controller
        assert e.package['now'] == e.now == original_time
        # A later completion clock must not relabel the new original account.
        e.clock_cell[0] = successor.now + timedelta(seconds=1)
        before = guard_files(e)
        with actual_pairs() as pairs, \
             patch.object(e.controller, 'reserve', wraps=e.controller.reserve) as reserve, \
             patch.object(e.controller, 'dispatch', wraps=e.controller.dispatch) as dispatch, \
             patch.object(C, '_issue', wraps=C._issue) as issue:
            state = e.runner.submit_exit(e.signal, now=successor.now)
        assert state.status == 'ACKNOWLEDGED' and issue.call_count == len(RF.creates(e)) == 1
        pair = pairs[0]
        assert pair.committed.transaction_id == successor.receipt.transaction_id
        assert pair.account.asof == successor.package['account_capture'].endpoint_accounts[0].observed_at
        assert pair.account.asof == successor.now < pair.completed_at == e.clock_cell[0]
        assert e.quote.asof == original_time and pair.risk is None
        for call in (reserve.call_args, dispatch.call_args):
            assert call.kwargs['expected_committed_transaction_id'] == successor.receipt.transaction_id
        assert not risk_rows(e) and guard_files(e) == before


def test_publication_after_pair_before_reserve_refuses_even_if_returned_view_is_retargeted():
    for retarget_view in (False, True):
        with RF.fixture() as e, actual_pairs() as pairs:
            successors = []
            def quote(_requested):
                assert len(pairs) == 1 and pairs[0].risk is None
                successor = G.advance(e)
                successors.append(successor)
                if retarget_view:
                    # Deliberately corrupt descriptive output, never the
                    # provider, actual owner, verifier or committed package.
                    object.__setattr__(pairs[0].committed, 'transaction_id', successor.receipt.transaction_id)
                return e.quote
            e.runner.quote_provider = quote
            with patch.object(e.controller, 'reserve', wraps=e.controller.reserve) as reserve, \
                 patch.object(e.controller, 'dispatch', wraps=e.controller.dispatch) as dispatch, \
                 patch.object(C, '_issue', wraps=C._issue) as issue:
                F.refused(lambda: e.runner.submit_exit(e.signal, now=e.now),
                          'COMMITTED_COMPLETION_GENERATION_CHANGED')
            assert len(successors) == 1 and reserve.call_count == 1 and dispatch.call_count == 0
            assert reserve.call_args.kwargs['expected_committed_transaction_id'] == e.receipt.transaction_id
            assert successors[0].receipt.transaction_id != e.receipt.transaction_id
            assert issue.call_count == 0 and not RF.creates(e) and not order_rows(e)
            assert not risk_rows(e)


def test_publication_after_real_reservation_preserves_pending_without_dispatch_or_retry():
    with RF.fixture() as e:
        actual, successors, reservations = e.controller.reserve, [], []
        def reserve(*args, **kwargs):
            state = actual(*args, **kwargs)
            reservations.append(state)
            successors.append(G.advance(e))
            return state
        with patch.object(e.controller, 'reserve', reserve), \
             patch.object(e.controller, 'dispatch', wraps=e.controller.dispatch) as dispatch, \
             patch.object(C, '_issue', wraps=C._issue) as issue:
            F.refused(lambda: e.runner.submit_exit(e.signal, now=e.now),
                      'COMMITTED_COMPLETION_GENERATION_CHANGED')
        assert len(successors) == len(reservations) == dispatch.call_count == 1
        assert dispatch.call_args.kwargs['expected_committed_transaction_id'] == e.receipt.transaction_id
        assert reservations[0].status == 'RESERVED'
        assert [row['kind'] for row in order_rows(e)] == ['reserved']
        assert issue.call_count == 0 and not RF.creates(e)
        assert e.controller.states() == (reservations[0],)
        # Same client remains the actual pending reservation, not a new order.
        with patch.object(e.controller, 'reserve', side_effect=AssertionError('pending re-reserved')), \
             patch.object(e.controller, 'dispatch', side_effect=AssertionError('pending auto-dispatched')):
            again = e.runner.submit_exit(e.signal, now=successors[0].now)
        assert again == reservations[0] and not RF.creates(e)


def test_completed_but_unpublished_successor_does_not_silently_adopt_current_heads():
    with RF.fixture() as e:
        successor = G.advance(e, publish=False)
        before = guard_files(e)
        with patch.object(C, '_issue', wraps=C._issue) as issue:
            F.refused(lambda: e.runner.submit_exit(e.signal, now=successor.now),
                      'COMMITTED_ACCOUNT_HEAD_CHANGED')
        assert issue.call_count == 0 and not order_rows(e) and not RF.creates(e)
        assert guard_files(e) == before


def test_next_generation_daily_stop_and_runner_stop_preserve_independent_exit():
    with RF.fixture(daily_stopped=True) as e:
        successor = G.advance(e)
        assert successor.projection.daily_stopped
        e.runner.stop()
        before = guard_files(e)
        with actual_pairs() as pairs, \
             patch.object(Controller, 'observe_committed', side_effect=AssertionError('entry-risk gate')):
            state = e.runner.submit_exit(e.signal, now=successor.now)
        assert state.status == 'ACKNOWLEDGED' and len(RF.creates(e)) == 1
        assert pairs[0].risk is None and pairs[0].committed.daily_stopped
        assert not risk_rows(e) and guard_files(e) == before


def test_unknown_send_survives_successor_and_same_or_other_exit_does_not_resend():
    with RF.fixture() as e:
        e.adapter.results.append(TimeoutError('synthetic uncertain transport'))
        first = e.runner.submit_exit(e.signal, now=e.now)
        assert first.status == 'UNKNOWN' and len(RF.creates(e)) == 1
        successor = G.advance(e)
        with patch.object(e.controller, 'dispatch', side_effect=AssertionError('uncertain order resent')):
            assert e.runner.submit_exit(e.signal, now=successor.now) == first
            F.refused(lambda: e.runner.submit_exit(replace(e.signal, signal_id='second-explicit-exit'),
                                                  now=successor.now), 'RUNNER_OUTSTANDING_ORDERS')
        assert len(RF.creates(e)) == 1 and e.controller.states() == (first,)
        assert [row['kind'] for row in order_rows(e)] == ['reserved', 'dispatching', 'unknown']


def test_legacy_exit_still_calls_original_keywords_without_generation_requirement():
    with RF.fixture() as e:
        observation = F.PF.read(e.s, e.provider, e.now).observation
        provider = lambda _: observation
        controller = Controller(journal=e.s.journal, account_provider=provider, policy=e.s.policy,
            adapters={'upbit': e.adapter}, session_provider=lambda _: None)
        legacy = RF.build(e, account_provider=provider, controller=controller)
        actual_reserve, actual_dispatch, calls = controller.reserve, controller.dispatch, []
        # Explicit old signatures fail if the new keyword leaks into legacy.
        def reserve(order, rules, *, session_id, now):
            calls.append('reserve')
            return actual_reserve(order, rules, session_id=session_id, now=now)
        def dispatch(client_id, *, now):
            calls.append('dispatch')
            return actual_dispatch(client_id, now=now)
        with patch.object(controller, 'reserve', reserve), patch.object(controller, 'dispatch', dispatch):
            state = legacy.submit_exit(e.signal, now=e.now)
        assert state.status == 'ACKNOWLEDGED' and calls == ['reserve', 'dispatch']
        assert len(RF.creates(e)) == 1


@contextmanager
def next_generation_actual_warmup_fixture():
    """Advance only input setup BEFORE the real new study/history is issued."""
    original = RF.fixture
    @contextmanager
    def prepared_fixture(**kwargs):
        with original(**kwargs) as e:
            first_receipt = e.receipt
            successor = G.advance(e)
            e.generation_successor = successor
            e.generation_first_receipt = first_receipt
            e.now = successor.now
            e.quote = replace(e.quote, asof=successor.now)
            yield e
    with patch.object(RF, 'fixture', prepared_fixture):
        with RF.actual_reviewed_warmup_fixture() as e:
            yield e


def test_real_new_study_and_history_reach_warmup_hold_from_the_successor_account():
    with next_generation_actual_warmup_fixture() as e:
        actual, pairs = Controller.observe_committed, []
        def observe(controller, **kwargs):
            result = actual(controller, **kwargs)
            pairs.append(result)
            return result
        before, history_before = guard_files(e), e.history_head.read()
        with patch.object(Controller, 'observe_committed', observe), \
             patch.object(R, 'DecisionInput', wraps=R.DecisionInput) as inputs, \
             patch.object(e.controller, 'reserve', side_effect=AssertionError('warmup reserved')), \
             patch.object(e.controller, 'dispatch', side_effect=AssertionError('warmup dispatched')), \
             patch.object(C, '_issue', wraps=C._issue) as issue:
            result = e.runner.tick(now=e.now)
        assert result.status == 'hold' and result.reasons == (), result
        assert result.decision_state == 'warmup' and result.decision_cause == 'insufficient_history'
        assert len(pairs) == inputs.call_count == 1 and issue.call_count == 0
        pair = pairs[0]
        assert pair.committed.transaction_id == e.generation_successor.receipt.transaction_id
        assert pair.committed.transaction_id != e.generation_first_receipt.transaction_id
        assert pair.account is pair.committed.observation is inputs.call_args.kwargs['account']
        assert pair.account.asof == e.generation_successor.package['account_capture'].endpoint_accounts[0].observed_at
        assert pair.completed_at == e.now == inputs.call_args.kwargs['now']
        assert not pair.account.holdings and e.driver.callback.seen[e.now][1] == 1
        assert e.research_capture.complete and len(e.research_plan.candidates) == 1
        assert e.history_head.read() == history_before and guard_files(e) == before
        assert not RF.creates(e) and len(risk_rows(e)) == 1
