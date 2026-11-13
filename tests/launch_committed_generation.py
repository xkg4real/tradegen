"""Real sequential local commits/publication with disposable signed owner context.

Account prices/pages and continuous coverage are explicitly synthetic inputs.
Actual guard reducers, Journal transactions, stores, heads and owner signatures
run normally. No production source authority, API, credential or live order.
"""
from contextlib import contextmanager, ExitStack
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
import threading
from unittest.mock import patch

from core.compliance import model as M, owner
from execution_accounts import baseline_bridge as B
from execution_accounts.baseline_store import CheckpointStore
from execution_accounts.model import content_digest
from execution_control.capability import digest as control_digest
from execution_control.store import GENESIS, Journal, Transaction
from execution_launch import committed_account as C
from execution_launch.baseline_head import BaselineHead
from execution_launch.continuous_guard import OwnerContextClaim
from execution_launch.continuous_guard_commit import (
    COMPLETE, PREPARE, GuardCheckpointStore, commit_continuous_guard,
)
from tests import control_committed_account as F
from tests import control_continuous_guard as GF
from tests import control_continuous_guard_commit as GC
from tests import launch_committed_account as PF

D = Decimal


@contextmanager
def fixture(**kwargs):
    """The existing real signed-owner fixture; original fields are retained."""
    with F.fixture(**kwargs) as e:
        yield e


def _claim(e, checkpoint, account, at, *, equity=None):
    holdings = {(account.venue, row.base_currency): float(row.units) for row in account.positions}
    ctx = owner.load_context(at, M.Positions(equity_krw=float(checkpoint.baseline.equity_krw if equity is None else equity),
                                             holdings=holdings))
    assert M.is_sealed(ctx) and ctx.owner.ok and ctx.code_signed
    e.contexts.append(ctx)
    return OwnerContextClaim(owner_head_sha256=ctx.owner.head[1], code_sha256=ctx.code_hash,
        code_approval_sha256=ctx.code_hash,
        signed_floor_krw=D(str(ctx.owner.limits['total_loss_floor_krw'])),
        signed_daily_loss_krw=D(str(ctx.owner.limits['daily_loss_krw'])),
        observed_at=at, source_sha256=ctx.ctx_hash)


def prepare(e, *, prices=None, end=None):
    """Build the next original synthetic input packet; do not commit or publish.

    Signed owner observations are actual. The preexisting fixture's invented
    coverage callback remains explicit; it never becomes production provenance.
    """
    state = e.s.gstore.load(expected_head=e.s.ghead.read())
    assert state.baseline == e.s.bstore.load(expected_head=e.s.bhead.read())
    previous = getattr(e, '_generation_fixture_latest', e).package
    account = previous['account_capture'].endpoint_accounts[0]
    old_price = (account.positions[0].price if account.positions else
                 previous['path'].events[-1].mark.price if previous['path'].events else
                 previous['path'].opening_marks[0].price)
    prices = (str(old_price),) if prices is None else prices
    before = _claim(e, state, account, state.baseline.asof)
    origin_start = account.origin + timedelta(hours=3)
    with patch.object(GF, 'START', origin_start):
        package = GF.build(state, e.s.policy, before, prices, end=end)
    if not account.positions:
        package = F.with_flat_cash(package)
    elif account.positions[0].units == D('0.5'):
        path = package['path']
        package = package | {'path': replace(path, opening_marks=(
            replace(path.opening_marks[0], price=old_price),))}
        package = F.with_spare_cash(package)
    # Observe the actual signed owner again at the endpoint; no claimed context
    # or permanently-true verifier substitutes for the loader.
    package = package | {'owner_after': _claim(e, state,
        package['account_capture'].endpoint_accounts[0], package['now'],
        equity=package['interval'].equity_krw)}
    rows = e.s.journal.snapshot()
    return SimpleNamespace(package=package, now=package['now'], receipt=None, projection=None,
        expected_guard_head=state.state_sha256,
        expected_baseline_head=state.baseline.state_digest,
        expected_control_head=rows[-1]['row_sha256'] if rows else GENESIS)


def commit(e, successor, **changes):
    """Actual durable commit outside the caller's publication transaction."""
    args = dict(now=successor.now, expected_guard_head=successor.expected_guard_head,
        expected_baseline_head=successor.expected_baseline_head,
        expected_control_head=successor.expected_control_head, journal=e.s.journal,
        guard_store=e.s.gstore, guard_head=e.s.ghead,
        baseline_store=e.s.bstore, baseline_head=e.s.bhead)
    successor.receipt = commit_continuous_guard(successor.package, **(args | changes))
    e.clock_cell[0] = successor.now
    e._generation_fixture_latest = successor
    return successor


def publish(e, successor, *, transaction=None, **changes):
    """Use the real open transaction when supplied; otherwise open one explicitly."""
    args = dict(expected_guard_head=successor.expected_guard_head,
        expected_baseline_head=successor.expected_baseline_head,
        expected_control_head=successor.expected_control_head, now=successor.now)
    args.update(changes)
    if transaction is None:
        with e.s.journal.transaction() as tx:
            return publish(e, successor, transaction=tx, **args)
    return e.provider.publish_committed(successor.package, successor.receipt,
                                        transaction=transaction, **args)


def advance(e, *, publish=True, prices=None, end=None):
    """Actual commit then optional publication; only clock_cell/latest inputs move.

    e.now/package/receipt/provider/controller remain unchanged for old/new tests.
    The returned namespace records the new endpoint and exact predecessor heads.
    """
    successor = commit(e, prepare(e, prices=prices, end=end))
    if publish:
        successor.projection = globals()['publish'](e, successor)
    return successor


def initial(e):
    rows = e.s.journal.snapshot()
    prepare_row = next(row for row in rows if row['kind'] == PREPARE
                       and row['data']['transaction_id'] == e.receipt.transaction_id)
    return SimpleNamespace(package=e.package, receipt=e.receipt, now=e.now,
        expected_guard_head=e.s.state.state_sha256,
        expected_baseline_head=e.s.state.baseline.state_digest,
        expected_control_head=prepare_row['data']['control_head_sha256'])


def read(e, now=None):
    return PF.read(e.s, e.provider, now or e.clock_cell[0])


def refused(call, code=None):
    return PF.refused(call, code)


def test_two_actual_successors_keep_same_provider_and_controller_without_second_commit():
    with fixture() as e:
        identities = (id(e.provider), id(e.controller))
        first = read(e)
        for price in ('102', '103'):
            next_ = advance(e, publish=False, prices=(price,))
            saved = PF.files(e.s)
            with e.s.journal.transaction() as tx, ExitStack() as blocked:
                for cls, name in ((Journal, 'transaction'), (Journal, 'snapshot'),
                    (Transaction, 'append'), (CheckpointStore, 'commit'),
                    (GuardCheckpointStore, 'commit'), (BaselineHead, 'compare_and_set'),
                    (BaselineHead, 'initialize_reviewed_head'), (B, 'advance_baseline')):
                    blocked.enter_context(patch.object(cls, name, side_effect=AssertionError('unexpected mutation')))
                result = publish(e, next_, transaction=tx)
                assert e.provider.read(now=next_.now, transaction=tx) == result
            assert PF.files(e.s) == saved
            assert result.transaction_id == next_.receipt.transaction_id != first.transaction_id
            assert result.observation.asof == next_.now and result.observation.risk.equity == D(price)
            assert not result.execution_ready and (id(e.provider), id(e.controller)) == identities
        rows = e.s.journal.snapshot()
        assert sum(row['kind'] == PREPARE for row in rows) == 3
        assert sum(row['kind'] == COMPLETE for row in rows) == 3
        assert e.package['now'] == e.now and e.receipt.transaction_id == first.transaction_id
        assert not e.adapter.requests


def test_moved_actual_heads_refuse_old_read_until_explicit_publication():
    with fixture() as e:
        next_ = advance(e, publish=False)
        refused(lambda: read(e), 'COMMITTED_ACCOUNT_HEAD_CHANGED')
        result = publish(e, next_)
        assert result == read(e) and result.transaction_id == next_.receipt.transaction_id


def test_exact_retry_retains_original_receipt_identity_after_real_control_suffix_and_replay():
    with fixture() as e:
        next_ = advance(e)
        first = next_.projection
        PF.risk_row(e.s, high='102', floor='102', stop=True, at=next_.now)
        with e.s.journal.transaction() as tx:
            tail = tx.append('halt', {'floor': '102'}, now=next_.now)
        replay = commit(e, next_).receipt
        assert replay.replayed and replay.control_head == tail['row_sha256']
        assert replay.permanently_halted and replay.control_head != first.receipt_control_head
        saved = PF.files(e.s)
        result = publish(e, next_)
        assert result.receipt_control_head == first.receipt_control_head
        assert result.completion_head == first.completion_head
        assert result.observed_control_head == replay.control_head
        assert result.observation.risk.halted and result.daily_stopped
        assert PF.files(e.s) == saved


def test_skipped_successor_and_rollback_do_not_replace_published_generation():
    with fixture() as e:
        original = initial(e)
        second = advance(e, publish=False)
        third = advance(e, publish=False)
        refused(lambda: publish(e, third), 'COMMITTED_ACCOUNT_DIRECT_SUCCESSOR_REQUIRED')
        refused(lambda: publish(e, second), 'COMMITTED_ACCOUNT_HEAD_CHANGED')
        refused(lambda: read(e), 'COMMITTED_ACCOUNT_HEAD_CHANGED')
        # A separate restart reader with explicit complete evidence may inspect
        # current state; it cannot retroactively authorize this provider's skip.
        restarted = C.CommittedAccountProvider(package=third.package, receipt=third.receipt,
            expected_guard_head=third.expected_guard_head, expected_baseline_head=third.expected_baseline_head,
            expected_control_head=third.expected_control_head, journal=e.s.journal,
            guard_store=e.s.gstore, guard_head=e.s.ghead, baseline_store=e.s.bstore, baseline_head=e.s.bhead)
        with e.s.journal.transaction() as tx:
            assert restarted.read(now=third.now, transaction=tx).transaction_id == third.receipt.transaction_id
        assert original.receipt == e.receipt
    with fixture() as e:
        original = initial(e)
        next_ = advance(e)
        refused(lambda: publish(e, original), 'COMMITTED_ACCOUNT_DIRECT_SUCCESSOR_REQUIRED')
        assert read(e).transaction_id == next_.receipt.transaction_id


def test_closed_foreign_and_cross_thread_transactions_never_publish():
    with fixture() as e:
        next_ = advance(e, publish=False)
        with e.s.journal.transaction() as tx:
            pass
        refused(lambda: publish(e, next_, transaction=tx), 'COMMITTED_ACCOUNT_TRANSACTION_REQUIRED')
        foreign = Journal()
        with foreign.transaction() as tx:
            refused(lambda: publish(e, next_, transaction=tx), 'COMMITTED_ACCOUNT_TRANSACTION_REQUIRED')
        errors = []
        with e.s.journal.transaction() as tx:
            worker = threading.Thread(target=lambda: errors.append(refused(
                lambda: publish(e, next_, transaction=tx), 'COMMITTED_ACCOUNT_TRANSACTION_REQUIRED')))
            worker.start(); worker.join(timeout=5)
            assert not worker.is_alive()
        assert errors == ['COMMITTED_ACCOUNT_TRANSACTION_REQUIRED']
        assert publish(e, next_).transaction_id == next_.receipt.transaction_id


def test_candidate_mutations_and_wrong_predecessors_refuse_but_original_retry_recovers():
    with fixture() as e:
        next_ = advance(e, publish=False)
        original = deepcopy(next_.package)
        for field, value in (('now', next_.now+timedelta(seconds=1)),
                              ('policy', replace(next_.package['policy'], version='changed')),
                              ('owner_before', replace(next_.package['owner_before'], signed_floor_krw=D(0)))):
            next_.package = original | {field: value}
            refused(lambda: publish(e, next_))
        next_.package = original
        for field in ('expected_guard_head', 'expected_baseline_head', 'expected_control_head'):
            refused(lambda: publish(e, next_, **{field:'f'*64}))
        assert publish(e, next_).transaction_id == next_.receipt.transaction_id


def test_caller_and_projection_mutations_do_not_replace_private_generation():
    with fixture() as e:
        next_ = advance(e)
        expected = read(e)
        next_.package['now'] += timedelta(seconds=1)
        object.__setattr__(next_.receipt, 'guard_head', 'f'*64)
        object.__setattr__(next_.projection.owner_claim, 'signed_floor_krw', D(0))
        e.provider._package = next_.package
        e.provider._receipt = next_.receipt
        e.provider._expected_guard = 'e'*64
        e.provider._generation = object()
        assert read(e) == expected
        try:
            e.provider._CommittedAccountProvider__generation = object()
        except AttributeError:
            pass
        else:
            raise AssertionError('private generation replaced by ordinary attribute assignment')
        assert read(e) == expected


def test_incomplete_actual_commit_must_complete_before_publication():
    with fixture() as e:
        next_ = prepare(e)
        with GC.crash_on_append(COMPLETE):
            try:
                commit(e, next_)
            except GC.Crash:
                pass
            else:
                raise AssertionError('completion fault not reached')
        # A forged receipt does not replace the missing actual COMPLETE row.
        rows = e.s.journal.snapshot()
        data = rows[-1]['data']
        next_.receipt = replace(e.receipt, transaction_id=data['transaction_id'],
            guard_head=data['new_guard_sha256'], baseline_head=data['new_baseline_sha256'],
            control_head=rows[-1]['row_sha256'])
        refused(lambda: publish(e, next_), 'COMMITTED_ACCOUNT_COMPLETION_REQUIRED')
        commit(e, next_)
        assert publish(e, next_).transaction_id == next_.receipt.transaction_id


def test_one_head_advance_never_publishes_or_readopts_old_head():
    with fixture() as e:
        next_ = prepare(e)
        with GC.crash_on_append(COMPLETE):
            try:
                commit(e, next_, guard_head=GC.Head(e.s.ghead, crash=True))
            except ValueError as exc:
                assert str(exc) == 'GUARD_CHECKPOINT_HEAD_UPDATE_FAILED'
        rows = e.s.journal.snapshot()
        data = rows[-1]['data']
        next_.receipt = replace(e.receipt, transaction_id=data['transaction_id'],
            guard_head=data['new_guard_sha256'], baseline_head=data['new_baseline_sha256'],
            control_head=rows[-1]['row_sha256'])
        assert e.s.bhead.read() == next_.receipt.baseline_head
        assert e.s.ghead.read() == e.receipt.guard_head
        refused(lambda: publish(e, next_), 'COMMITTED_ACCOUNT_HEAD_CHANGED')
        commit(e, next_)
        assert publish(e, next_).transaction_id == next_.receipt.transaction_id


def test_store_damage_after_completed_commit_refuses_without_generation_change():
    with fixture() as e:
        next_ = advance(e, publish=False)
        path = e.s.gstore._root/'checkpoint.json'
        raw = path.read_bytes(); path.write_bytes(raw[:-1])
        refused(lambda: publish(e, next_), 'COMMITTED_ACCOUNT_STORE_REFUSED')
        path.write_bytes(raw)
        assert publish(e, next_).transaction_id == next_.receipt.transaction_id


def test_final_dependency_read_mutation_is_refused_and_exact_replay_remains_possible():
    with fixture() as e:
        prior_head = (e.s.ghead._dir/'head.json').read_bytes()
        next_ = advance(e, publish=False)
        head = e.s.ghead._dir/'head.json'; latest_head = head.read_bytes()
        actual = e.s.bstore.load
        calls = []
        def mutated(**kwargs):
            result = actual(**kwargs)
            calls.append(True)
            if len(calls) == 2:
                head.write_bytes(prior_head)
            return result
        with patch.object(e.s.bstore, 'load', mutated):
            refused(lambda: publish(e, next_), 'COMMITTED_ACCOUNT_HEAD_CHANGED')
        head.write_bytes(latest_head)
        assert publish(e, next_).transaction_id == next_.receipt.transaction_id


def test_reentrant_real_publication_cannot_overwrite_outer_captured_generation():
    with fixture() as e:
        next_ = advance(e, publish=False)
        actual = e.s.bstore.load
        entered = []
        with e.s.journal.transaction() as tx:
            def nested(**kwargs):
                result = actual(**kwargs)
                if not entered:
                    entered.append(True)
                    published = publish(e, next_, transaction=tx)
                    assert published.transaction_id == next_.receipt.transaction_id
                return result
            with patch.object(e.s.bstore, 'load', nested):
                refused(lambda: publish(e, next_, transaction=tx), 'COMMITTED_ACCOUNT_GENERATION_CHANGED')
            assert e.provider.read(now=next_.now, transaction=tx).transaction_id == next_.receipt.transaction_id


def test_two_publishers_serialize_under_actual_journal_and_exact_retry_is_idempotent():
    with fixture() as e:
        next_ = advance(e, publish=False)
        saved = PF.files(e.s)
        results, errors = [], []
        gate = threading.Barrier(2)
        def attempt():
            gate.wait(timeout=5)
            try:
                results.append(publish(e, next_))
            except Exception as exc:
                errors.append(type(exc).__name__)
        workers = [threading.Thread(target=attempt) for _ in range(2)]
        for worker in workers: worker.start()
        for worker in workers: worker.join(timeout=10)
        assert not any(worker.is_alive() for worker in workers)
        assert not errors and len(results) == 2 and results[0] == results[1]
        assert PF.files(e.s) == saved


def test_high_floor_daily_stop_and_halt_survive_real_successor_and_boundary():
    with fixture(prices=('110','105','115')) as e:
        first = read(e)
        next_ = advance(e, prices=('116',))
        result = next_.projection
        assert first.observation.risk.halted and result.observation.risk.halted
        assert result.observation.risk.approved_effective_floor >= first.observation.risk.approved_effective_floor
        assert result.observation.risk.prior_high_watermark >= first.observation.risk.prior_high_watermark
    with fixture(daily_stopped=True) as e:
        assert read(e).daily_stopped and advance(e).projection.daily_stopped


def test_publication_does_not_restamp_expired_account_or_accept_clock_rollback():
    with fixture() as e:
        next_ = advance(e, publish=False)
        refused(lambda: publish(e, next_, now=next_.now-timedelta(seconds=1)),
                'COMMITTED_ACCOUNT_CLOCK_ROLLBACK')
        refused(lambda: publish(e, next_, now=next_.now+timedelta(seconds=31)))
        result = publish(e, next_)
        assert result.observation.asof == next_.package['account_capture'].endpoint_accounts[0].observed_at
        assert result.owner_claim.observed_at == next_.package['owner_after'].observed_at


def test_completed_successor_cannot_hide_old_foreign_policy_or_relaxed_floor_suffix():
    for changes in ({'policy_digest':'f'*64}, {'floor_relaxation_approved':True}):
        with fixture() as e:
            data = dict(policy_digest=control_digest(e.s.policy), day=e.now.date().isoformat(),
                high_watermark='101', day_start_equity='100', effective_floor='101',
                calculated_floor='101', daily_stopped=False, floor_relaxation_approved=False)
            with e.s.journal.transaction() as tx:
                tx.append('risk_snapshot', data | changes, now=e.now)
            refused(lambda: read(e), 'COMMITTED_ACCOUNT_CONTROL_EPOCH_CHANGED')
            next_ = advance(e, publish=False)
            refused(lambda: publish(e, next_), 'COMMITTED_ACCOUNT_CONTROL_EPOCH_CHANGED')
            refused(lambda: read(e), 'COMMITTED_ACCOUNT_HEAD_CHANGED')


def test_midnight_successor_preserves_prior_day_open_conflict_in_historical_prefix():
    start = datetime(2026, 11, 6, 23, 59, 56, tzinfo=M.KST)
    with fixture(start=start) as e:
        data = dict(policy_digest=control_digest(e.s.policy), day=e.now.date().isoformat(),
            high_watermark='101', day_start_equity='99', effective_floor='101',
            calculated_floor='101', daily_stopped=False, floor_relaxation_approved=False)
        with e.s.journal.transaction() as tx:
            tx.append('risk_snapshot', data, now=e.now)
        refused(lambda: read(e), 'COMMITTED_ACCOUNT_DAY_OPEN_CONFLICT')
        next_ = advance(e, publish=False)
        assert next_.now.astimezone(M.KST).date() != e.now.astimezone(M.KST).date()
        refused(lambda: publish(e, next_), 'COMMITTED_ACCOUNT_DAY_OPEN_CONFLICT')


def test_midnight_and_recovery_cutoff_keep_actual_original_times_and_latches():
    for hour, minute, stopped, pol in ((23,59,True,None), (21,59,False,GF.policy(recovery=True))):
        start = datetime(2026,11,6,hour,minute,56,tzinfo=M.KST)
        with fixture(start=start, daily_stopped=stopped, pol=pol) as e:
            original = read(e)
            next_ = advance(e)
            result = next_.projection
            assert result.observation.asof == next_.now
            assert result.owner_claim.observed_at == next_.now
            assert result.observation.risk.prior_high_watermark >= original.observation.risk.prior_high_watermark
            assert result.observation.risk.approved_effective_floor >= original.observation.risk.approved_effective_floor
            if hour == 23:
                assert result.policy_day > original.policy_day and not result.daily_stopped
            else:
                assert next_.now.astimezone(M.KST).hour == 22
                assert result.observation.risk.recovery_checkpoint.cutoff_at == next_.now


def test_exact_retry_rejects_substituted_same_transaction_material_and_unverified_receipt_prefix():
    with fixture() as e:
        next_ = advance(e)
        saved = deepcopy(next_.package)
        next_.package = saved | {'now':next_.now+timedelta(seconds=1)}
        refused(lambda: publish(e, next_), 'COMMITTED_ACCOUNT_RETRY_MISMATCH')
        next_.package = saved
        original_receipt = next_.receipt
        next_.receipt = replace(original_receipt, control_head='f'*64, replayed=True)
        refused(lambda: publish(e, next_), 'COMMITTED_ACCOUNT_RECEIPT_PREFIX_MISSING')
        next_.receipt = original_receipt
        assert publish(e, next_) == next_.projection
