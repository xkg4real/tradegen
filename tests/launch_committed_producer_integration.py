"""Independent offline producer vertical with actual durable and owner checks.

Account GET replies, price paths, coverage assertions and planted research prices
are explicitly synthetic. Parsing, temporary owner signatures, retained graphs,
guard commits, publication, Controller gates, review issuance, history and dry
capability consumption use the actual implementations. No production source
authenticity, live execution, process provenance restoration or profitability is
claimed. Only disposable fixtures and exact DryRunAdapter instances are used.
"""
from contextlib import contextmanager, ExitStack
from dataclasses import asdict, replace
from datetime import timedelta
from decimal import Decimal
import base64
import hashlib
import json
import re
from types import SimpleNamespace
from unittest.mock import patch

from core.compliance import model as CM, owner
from execution_accounts.baseline_bridge import ContinuousAccountProvider
from execution_accounts.baseline_store import CheckpointStore
from execution_accounts.quotes import to_runner_quote
from execution_control import controller as CC
from execution_control.capability import digest
from execution_control.controller import Controller, _fold
from execution_control.model import Order
from execution_control.owner_authority import CurrentOwnerAuthority
from execution_control.risk import Fill
from execution_control.store import GENESIS, Journal, Transaction
from execution_launch import committed_producer as P
from execution_launch import guard_generation_archive as A
from execution_launch import managed_behavior as MB, protective_store as PS
from execution_launch import runner as R, strategy as E, study as U
from execution_launch.baseline_head import BaselineHead
from execution_launch.capture_v2 import capture_json_v2
from execution_launch.committed_account import CommittedAccountProvider
from execution_launch.continuous_guard_commit import COMPLETE, PREPARE, GuardCheckpointStore
from execution_launch.driver import DeploymentWindow, describe_fixed_driver, make_fixed_carry_driver
from execution_launch.live_history import HistoryChain, LiveHistory
from execution_launch.profile import profile_contract_digest, risk_policy
from execution_launch.program import parameters_json
from execution_launch.protective_state import ManagementPolicy
from execution_launch.review_auth import ReviewVerifiers, review_body, review_signing_bytes
from execution_launch.review_request import build_review_request
from execution_launch.runner import EvidencePackage, Runner, Signal
from execution_orders.model import AdapterResult
from tests import compliance_fixtures as CF
from tests import launch_committed_producer as F
from tests import launch_study as SF
from tests.accounts_continuous import fill_event
from tests.launch_account_interval import order as raw_order
from tests.launch_capture import book
from tests.launch_protective_store import limits as protective_limits

D = Decimal
BAR = timedelta(seconds=60)


def refused(call, expected=None):
    try:
        call()
    except (ValueError, RuntimeError) as exc:
        code = str(exc)
        assert re.fullmatch(r'[A-Z][A-Z0-9_]+', code), 'private/non-code error'
        if expected is not None:
            assert code in ((expected,) if isinstance(expected, str) else expected), (code, expected)
        return code
    raise AssertionError('expected actual refusal')


def inert(value):
    assert value.execution_ready is False and value.source_authenticated is False


def rows(e):
    return e.journal.snapshot()


def orders(e):
    with e.journal.transaction() as tx:
        return _fold(tx.events)[0]


def checkpoint_state(e):
    return (e.guard_head.read(), e.baseline_head.read(),
        e.guard_store.load(expected_head=e.guard_head.read()),
        e.baseline_store.load(expected_head=e.baseline_head.read()))


def creates(e):
    return tuple(request for request in e.adapter.requests if request.operation == 'create')


@contextmanager
def durable_trace(e):
    """Count only actual runtime commits/CAS; pure preview arithmetic is allowed."""
    counts = dict(baseline=0, guard=0, baseline_cas=0, guard_cas=0)
    active = set()
    original_transaction = Journal.transaction
    original_snapshot = Journal.snapshot
    @contextmanager
    def transaction(journal):
        identity = str(journal._root)
        assert identity not in active, 'nested actual Journal transaction'
        active.add(identity)
        try:
            with original_transaction(journal) as tx:
                yield tx
        finally:
            active.remove(identity)
    def snapshot(journal):
        assert str(journal._root) not in active, 'snapshot inside actual Journal transaction'
        return original_snapshot(journal)
    original_bcommit = CheckpointStore.commit
    original_gcommit = GuardCheckpointStore.commit
    original_cas = BaselineHead.compare_and_set
    def bcommit(store, *args, **kwargs):
        result = original_bcommit(store, *args, **kwargs)
        if store is e.baseline_store:
            counts['baseline'] += 1
        return result
    def gcommit(store, *args, **kwargs):
        result = original_gcommit(store, *args, **kwargs)
        if store is e.guard_store:
            counts['guard'] += 1
        return result
    def cas(head, *args, **kwargs):
        result = original_cas(head, *args, **kwargs)
        if head is e.baseline_head:
            counts['baseline_cas'] += 1
        elif head is e.guard_head:
            counts['guard_cas'] += 1
        return result
    with (patch.object(Journal, 'transaction', transaction),
            patch.object(Journal, 'snapshot', snapshot),
            patch.object(CheckpointStore, 'commit', bcommit),
            patch.object(GuardCheckpointStore, 'commit', gcommit),
            patch.object(BaselineHead, 'compare_and_set', cas),
            patch.object(CheckpointStore, 'seed', side_effect=AssertionError('runtime baseline seed')),
            patch.object(GuardCheckpointStore, 'seed', side_effect=AssertionError('runtime guard seed')),
            patch.object(BaselineHead, 'initialize_reviewed_head', side_effect=AssertionError('runtime head initialization')),
            patch.object(ContinuousAccountProvider, '__call__', side_effect=AssertionError('legacy durable provider'))):
        yield counts


def _study_profile(holder):
    """Build and actually evaluate the research before the producer pins profile.

    The old fixture's triangle source is paced at this protocol's 60-second bar.
    No evaluated result is retargeted to another capital, scope, rules or policy.
    """
    def transform(original):
        now = original.instrument_rules.asof
        profile = replace(original, policy=replace(original.policy, initial_equity=D('100090')))
        end = now-timedelta(seconds=60)
        start = end-BAR*500
        registered = start-timedelta(days=1)
        template = SF.template(500, bar_seconds=60, schema_version=2,
            minimum_fill_delay_seconds=1, preregistered_at=registered, capture_start=start, capture_end=end,
            evaluator_revision=MB.CARRY_EVALUATOR_REVISION, behavior_revision=MB.BEHAVIOR_REVISION,
            terminal_accounting=MB.TERMINAL_ACCOUNTING, management_behavior_sha256=MB.behavior_digest())
        historical = replace(profile, instrument_rules=replace(profile.instrument_rules, asof=registered))
        plan = U.build_study_plan(historical, (SF.A,), template=template,
            plan_id='producer-actual-study', asset='BTC', risk_group='crypto-btc')
        with patch.object(SF, 'BAR', BAR):
            source = SF.Driver(plan)
            def clock():
                elapsed = source.clock[0]-source.start
                if elapsed >= timedelta(0) and elapsed % BAR < timedelta(seconds=1):
                    source.clock[0] += timedelta(milliseconds=1)
                return source.clock[0]
            captured = U.run_capture(plan, book_source=source.read, clock=clock,
                wait_until=source.wait_until, record=source.lines.append)
        assert captured.complete and captured.slots_recorded == 501, captured.reason
        candidate = plan.candidates[0]
        protocol, program = candidate.protocol, candidate.program
        raw = capture_json_v2(captured.archives[0]).encode('ascii')
        result = E.evaluate_capture_json(protocol, raw, profile.instrument_rules, now=now)
        profile = replace(profile, strategy_id=program.strategy_id, strategy_code_sha256=protocol.strategy_code_sha256)
        assert profile_contract_digest(profile) == protocol.profile_contract_digest
        assert protocol.initial_cash_quote == profile.policy.initial_equity == D('100090')
        holder['research'] = SimpleNamespace(capture=captured, plan=plan, raw=raw, result=result,
            protocol=protocol, program=program, artifact=U._fixed_file(U.PROGRAM_SOURCE))
        return profile
    return transform


@contextmanager
def actual_reviewed_producer_fixture(*, bind_startup=True, clock_step=timedelta(0)):
    """Actual new study, signed review, issued carry driver and durable history.

    No production unit has run when yielded. Scheduler tests may bind startup
    themselves and prepare each recorder using F.arm_interval before collection.
    """
    holder = {}
    with F.fixture(profile_transform=_study_profile(holder), bind_startup=bind_startup,
            clock_step=clock_step) as e:
        research = holder['research']
        now = e.clock()
        window = DeploymentWindow(deployment_id='producer-actual-history',
            start=now+timedelta(seconds=20), end=now+timedelta(seconds=140))
        history_head = BaselineHead(root=e.hroot, name='producer-history',
            chain=HistoryChain(root=e.home, window=window))
        history_head.initialize_reviewed_head(GENESIS)
        history = LiveHistory(research.program, research.protocol, e.profile,
            window=window, root=e.home, clock=e.clock, trusted_head=history_head)
        driver = make_fixed_carry_driver(research.program, research.protocol, e.profile,
            window=window, history_provider=history.provider, history_verifier=history.verifier,
            program_artifact=research.artifact)
        identity = history.bind(driver)
        authority = CurrentOwnerAuthority(clock=e.clock)
        current_owner = authority(e.clock())
        request = build_review_request(e.profile, research.protocol, research.result, now=e.clock(),
            program_artifact=research.artifact, parameters_json=parameters_json(research.program))
        body = review_body(request, asdict(identity), deployment_code_hash=current_owner.context.code_hash,
            audit_sha256=hashlib.sha256(b'synthetic producer research; no profitability/source claim').hexdigest(),
            owner_fingerprint=current_owner.context.owner.fingerprint, issued_at=e.clock(),
            expires_at=e.clock()+timedelta(hours=1))
        document = json.dumps({'body':body,
            'signature_b64':base64.b64encode(e.key.sign(review_signing_bytes(body))).decode('ascii')})
        review = ReviewVerifiers(document, clock=e.clock, authority_provider=authority,
            approved_history_provider=history.provider, approved_history_verifier=history.verifier)
        evidence = EvidencePackage(protocol=research.protocol, result=research.result, review_verifier=review.source)
        cutoff = window.end.astimezone(CM.KST).replace(hour=22, minute=0, second=0, microsecond=0)
        monitor_until = max(window.end+timedelta(seconds=40), cutoff+timedelta(seconds=20))
        policy = ManagementPolicy(management_id='producer-actual-management', account_scope=e.profile.account_scope,
            venue='upbit', market='spot', quote_currency='KRW', symbol=e.profile.symbol,
            code_sha256=identity.deployment_code_sha256, strategy_sha256=evidence.protocol.strategy_code_sha256,
            risk_policy_sha256=digest(risk_policy(e.profile)), holding_deadline=window.end,
            monitor_until=monitor_until)
        protection = PS.ProtectiveStore(root=e.home/'producer-protection', head_root=e.hroot,
            head_name='producer-protection', policy=policy,
            binding=PS.StoreBinding(driver_identity_sha256=digest(identity),
                research_sha256=E.evidence_digest(evidence.result), source_sha256=evidence.result.inputs_digest),
            limits=protective_limits())
        protection.provision_empty()
        protection.head.initialize_reviewed_head(protection.genesis_digest)
        e.research, e.review, e.evidence = research, review, evidence
        e.driver, e.identity, e.history, e.history_head = driver, identity, history, history_head
        e.window, e.monitor_until, e.protective_store = window, monitor_until, protection
        assert describe_fixed_driver(driver) == identity
        yield e


def launch_runner(e, *, evidence=None, driver=None, implementation_verifier=None, quote_provider=None):
    provider, controller, journal = e.producer._runtime_components()
    assert journal is e.journal
    return Runner(profile=e.profile, account_provider=provider, controller=controller,
        quote_provider=quote_provider or (lambda now: to_runner_quote(book(now, received_delta=0,
            asof_delta=-1, bid=10050, ask=10051), now=now)), evidence=evidence, driver=driver,
        implementation_verifier=implementation_verifier, mode='rehearsal',
        isolated_state_root=e.home, clock=e.clock)


def sell_order(e, client_id='producer-explicit-reducing', quantity=D('.5')):
    return Order(client_id=client_id, account_scope=e.profile.account_scope, venue='upbit', market='spot',
        symbol='KRW-BTC', side='sell', quantity=quantity, limit_price=D('10050'), quote_krw=D(1))


def test_actual_opening_owner_provenance_two_intervals_and_exactly_two_durable_transitions():
    with F.fixture(clock_step=timedelta(microseconds=1)) as e:
        initial = checkpoint_state(e)
        assert e.opening.account_asof <= e.opening.observed_at <= e.opening.completed_at < e.state.asof
        assert e.opening.owner_claim.observed_at == e.opening.observed_at
        assert e.owner_calls[0][0] == e.opening.observed_at
        with durable_trace(e) as counts:
            first = F.advance(e)
            runtime = e.producer._runtime_components()
            second = F.advance(e)
            assert e.producer._runtime_components() == runtime
            paired, endpoint = e.producer._current_unit(second, now=e.clock())
        assert counts == dict(baseline=2, guard=2, baseline_cas=2, guard_cas=2)
        assert type(runtime[0]) is CommittedAccountProvider and type(runtime[1]) is Controller
        assert runtime[1].account_provider is runtime[0] and runtime[2] is e.journal
        first_input = A.read_guard_input(e.archive_store, first.input_archive_digest)
        second_input = A.read_guard_input(e.archive_store, second.input_archive_digest)
        assert first_input.package['owner_before'] == e.opening.owner_claim
        assert second_input.package['owner_before'].observed_at <= first.account.observed_at
        assert first.account.observed_at == second_input.package['path'].start
        assert first.transaction_id != second.transaction_id == paired.committed.transaction_id
        assert endpoint == second.account and paired.account.asof == second.account.observed_at
        assert second_input.package['now'] >= second_input.package['owner_after'].observed_at
        assert second.account.observed_at <= second_input.package['now'] < second.completed_at
        assert second.reconciliation.status == 'RECONCILED'
        assert checkpoint_state(e)[3].sequence == initial[3].sequence+2
        assert sum(row['kind'] == PREPARE for row in rows(e)) == 2
        assert sum(row['kind'] == COMPLETE for row in rows(e)) == 2
        assert all(left[0] <= right[0] for left,right in zip(e.owner_calls,e.owner_calls[1:]))
        for value in (e.opening, first, second, e.producer.status()):
            inert(value)
        assert not e.adapter.requests


def test_real_reviewed_history_and_runner_reach_warmup_hold_from_second_producer_generation():
    with actual_reviewed_producer_fixture() as e:
        with durable_trace(e) as counts:
            first = F.advance(e)
            runtime = e.producer._runtime_components()
            second = F.advance(e)
            e.clock_cell[0] = e.window.start
            original_book = book(e.window.start, received_delta=0, asof_delta=-1, bid=10050, ask=10051)
            quote = to_runner_quote(original_book, now=e.clock())
            e.history.record_slot(original_book, second.observation)
            runner = launch_runner(e, evidence=e.evidence, driver=e.driver,
                implementation_verifier=e.review.implementation, quote_provider=lambda _:quote)
            before, history_before = checkpoint_state(e), e.history_head.read()
            actual_pair, pairs = Controller.observe_committed, []
            def observe(controller, **kwargs):
                result = actual_pair(controller, **kwargs)
                pairs.append(result)
                return result
            with (patch.object(Controller, 'observe_committed', observe),
                    patch.object(R, 'DecisionInput', wraps=R.DecisionInput) as inputs,
                    patch.object(Controller, 'reserve', side_effect=AssertionError('warmup reserve')),
                    patch.object(Controller, 'dispatch', side_effect=AssertionError('warmup dispatch')),
                    patch.object(CC, '_issue', wraps=CC._issue) as issued):
                result = runner.tick(now=e.clock())
        assert result.status == 'hold' and result.reasons == ()
        assert (result.decision_state,result.decision_cause) == ('warmup','insufficient_history')
        assert len(pairs) == inputs.call_count == 1 and issued.call_count == 0
        assert pairs[0].committed.transaction_id == second.transaction_id != first.transaction_id
        assert inputs.call_args.kwargs['account'] is pairs[0].account is pairs[0].committed.observation
        assert pairs[0].account.asof == second.account.observed_at < pairs[0].completed_at
        assert e.producer._runtime_components() == runtime
        assert runner.account_provider is runtime[0] and runner.controller is runtime[1]
        assert counts == dict(baseline=2, guard=2, baseline_cas=2, guard_cas=2)
        assert checkpoint_state(e) == before and e.history_head.read() == history_before
        assert e.research.capture.complete and len(e.history._slots) == 1
        assert e.driver.callback.seen[e.window.start][1] == 1 and not creates(e)


def test_public_opening_copy_cannot_replace_private_preinterval_owner_observation():
    with F.fixture() as e:
        original = e.opening.owner_claim
        object.__setattr__(e.opening.owner_claim, 'source_sha256', 'f'*64)
        unit = F.advance(e)
        retained = A.read_guard_input(e.archive_store, unit.input_archive_digest)
        assert retained.package['owner_before'].source_sha256 != 'f'*64
        assert retained.package['owner_before'].observed_at == original.observed_at
        fresh = P.CommittedAccountProducer(**e.args)
        fresh._bind_startup(session_provider=lambda _:None)
        fresh.opening = e.opening  # arbitrary descriptive public data is not private provenance
        before, events = checkpoint_state(e), rows(e)
        refused(fresh._collect_current, 'COMMITTED_PRODUCER_OPENING_REQUIRED')
        assert checkpoint_state(e) == before and rows(e) == events and not creates(e)


def test_genuine_reducing_runner_action_after_successor_uses_existing_gates_once():
    with F.fixture(held=True) as e:
        first = F.advance(e)
        runtime = e.producer._runtime_components()
        second = F.advance(e)
        runner = launch_runner(e)
        runner.stop()
        signal = Signal(signal_id='producer-independent-exit', action='exit', quantity=D('.5'), limit_price=D('10050'))
        before = checkpoint_state(e)
        with (patch.object(Controller, 'observe_committed', side_effect=AssertionError('entry risk on reducing')),
                patch.object(Controller, '_snapshot_risk', side_effect=AssertionError('new risk snapshot')),
                patch.object(CC, '_issue', wraps=CC._issue) as issued):
            result = runner.submit_exit(signal, now=e.clock())
            duplicate = runner.submit_exit(signal, now=e.clock())
        assert result.status == duplicate.status == 'ACKNOWLEDGED'
        assert second.transaction_id != first.transaction_id and e.producer._runtime_components() == runtime
        assert len(creates(e)) == issued.call_count == 1 and checkpoint_state(e) == before
        assert not any(row['kind'] == 'risk_snapshot' for row in rows(e))


def test_actual_reducing_partial_fill_is_collected_published_and_reconciled_with_exact_fee():
    with F.fixture(held=True) as e:
        first = F.advance(e)
        provider, controller, _ = e.producer._runtime_components()
        obj = sell_order(e, quantity=D(1))
        assert controller.reserve(obj, e.profile.instrument_rules, session_id='producer-explicit', now=e.clock()).status == 'RESERVED'
        sent = controller.dispatch(obj.client_id, now=e.clock())
        assert sent.status == 'ACKNOWLEDGED' and len(creates(e)) == 1
        fill_at = first.account.observed_at+timedelta(seconds=1)
        raw = raw_order(sent.venue_order_id, 'ask', fill_at, '10050',
            [('producer-partial-fill', '.4', '4020')], paid_fee='2.01')
        raw.update(identifier=obj.client_id, state='wait', volume='1', remaining_volume='.6', locked='.6')
        e.exchange.orders.append(raw)
        for balance in e.exchange.balances:
            if balance['currency'] == 'KRW':
                balance.update(balance='94012.99', locked='0')
            elif balance['currency'] == 'BTC':
                balance.update(balance='0', locked='.6')
        fill = Fill(venue='upbit', account_scope=e.profile.account_scope, order_id=sent.venue_order_id,
            fill_id='producer-partial-fill', market='spot', symbol='KRW-BTC', side='sell', quantity=D('.4'),
            price=D('10050'), quote_currency='KRW', quote_krw=D(1), fee_amount=D('2.01'), fee_currency='KRW',
            executed_at=fill_at, base_currency='BTC')
        sequence = e.guard_store.load(expected_head=e.guard_head.read()).next_sequence
        e.adapter.results.append(AdapterResult(status='partial', code='synthetic_partial',
            venue_order_id=sent.venue_order_id, client_id=obj.client_id, filled_quantity=D('.4'),
            average_price=D('10050'), fee=D('2.01'), fee_currency='KRW'))
        second = F.advance(e, events=(fill_event(sequence, fill),))
        assert e.producer._runtime_components()[:2] == (provider, controller)
        assert second.reconciliation.status == 'RECONCILED_OPEN'
        assert second.reconciliation.open_client_ids == (obj.client_id,)
        assert second.reconciliation.unresolved_client_ids == second.reconciliation.external_order_ids == ()
        state = orders(e)[obj.client_id]
        assert state['status'] == 'PARTIAL' and state['filled'] == D('.4')
        assert state['order'].quantity-state['filled'] == D('.6')
        assert second.account.positions[0].units == D('.6')
        recorded_fills = [row for row in rows(e) if row['kind'] == 'fill']
        assert len(recorded_fills) == 1 and D(recorded_fills[0]['data']['fill']['fee_amount']) == D('2.01')
        assert [request.operation for request in e.adapter.requests] == ['create','status']
        assert second.transaction_id != first.transaction_id


def test_actual_unknown_send_survives_next_unit_without_retry_or_fabricated_flatness():
    with F.fixture(held=True) as e:
        F.advance(e)
        _, controller, _ = e.producer._runtime_components()
        obj = sell_order(e)
        controller.reserve(obj, e.profile.instrument_rules, session_id='producer-explicit', now=e.clock())
        e.adapter.results.extend((AdapterResult(status='unknown', code='synthetic_timeout'),
            AdapterResult(status='unknown', code='synthetic_status_timeout')))
        assert controller.dispatch(obj.client_id, now=e.clock()).status == 'UNKNOWN'
        unit = F.advance(e)
        assert unit.reconciliation.status == 'BLOCKED' and obj.client_id in unit.reconciliation.unresolved_client_ids
        assert e.producer.status().phase == 'BLOCKED'
        assert orders(e)[obj.client_id]['status'] == 'UNKNOWN'
        assert unit.account.positions[0].units == D(1)
        assert [request.operation for request in e.adapter.requests] == ['create','status']


def test_external_open_order_in_new_capture_blocks_even_with_no_local_orders():
    with F.fixture() as e:
        first = F.advance(e)
        raw = raw_order('producer-external', 'bid', first.account.observed_at+timedelta(seconds=1),
            '10050', [])
        raw.update(identifier='external-client', state='wait', volume='1', remaining_volume='1', locked='10055.025')
        e.exchange.orders.append(raw)
        e.exchange.balances[0].update(balance='90034.975', locked='10055.025')
        unit = F.advance(e)
        assert unit.reconciliation.status == 'BLOCKED'
        assert unit.reconciliation.external_order_ids == ('producer-external',)
        assert unit.reconciliation.attempted_reconciliations == 0 and orders(e) == {}
        assert not unit.account.positions and not creates(e) and e.producer.status().phase == 'BLOCKED'


def test_successor_between_real_pair_and_reserve_or_dispatch_refuses_old_generation():
    for phase in ('reserve','dispatch'):
        with F.fixture(held=True) as e:
            first = F.advance(e)
            _, controller, _ = e.producer._runtime_components()
            pair = controller.read_committed_account(now=e.clock())
            obj = sell_order(e, client_id='producer-generation-race')
            if phase == 'dispatch':
                reserved = controller.reserve(obj, e.profile.instrument_rules, session_id='producer-explicit',
                    now=e.clock(), expected_committed_transaction_id=pair.committed.transaction_id)
                assert reserved.status == 'RESERVED'
            second = F.advance(e)
            assert second.transaction_id != first.transaction_id == pair.committed.transaction_id
            if phase == 'reserve':
                refused(lambda:controller.reserve(obj, e.profile.instrument_rules, session_id='producer-explicit',
                    now=e.clock(), expected_committed_transaction_id=pair.committed.transaction_id),
                    'COMMITTED_COMPLETION_GENERATION_CHANGED')
                assert orders(e) == {}
            else:
                refused(lambda:controller.dispatch(obj.client_id, now=e.clock(),
                    expected_committed_transaction_id=pair.committed.transaction_id),
                    'COMMITTED_COMPLETION_GENERATION_CHANGED')
                assert orders(e)[obj.client_id]['status'] == 'RESERVED'
                assert obj.client_id in second.reconciliation.unresolved_client_ids
            assert not creates(e)


def test_actual_owner_change_after_input_retention_preserves_input_and_commits_nothing():
    with F.fixture() as e:
        actual = A.retain_guard_input
        retained = []
        def changed(*args, **kwargs):
            value = actual(*args, **kwargs)
            retained.append(value)
            CF.sign(e.key, 'age_of_majority', {'birth_date':'2000-01-01','evidence':'producer-stage-change'},
                CM.iso_utc(e.clock()))
            return value
        before = checkpoint_state(e)
        with patch.object(A, 'retain_guard_input', changed), durable_trace(e) as counts:
            refused(lambda:F.advance(e), 'COMMITTED_PRODUCER_OWNER_REFUSED')
        assert len(retained) == 1 and e.producer.status().input_archive_digest == retained[0].archive_digest
        assert A.read_guard_input(e.archive_store, retained[0].archive_digest).record == retained[0].record
        assert counts == dict(baseline=0,guard=0,baseline_cas=0,guard_cas=0)
        assert checkpoint_state(e) == before and not rows(e) and not creates(e)


def test_actual_successor_commit_then_publication_failure_keeps_moved_heads_and_old_reader_refused():
    with F.fixture() as e:
        first = F.advance(e)
        provider, controller, journal = e.producer._runtime_components()
        original = checkpoint_state(e)
        with patch.object(CommittedAccountProvider, 'publish_committed',
                side_effect=ValueError('SYNTHETIC_PUBLICATION_FAILURE')):
            refused(lambda:F.advance(e), 'COMMITTED_PRODUCER_PUBLICATION_REFUSED')
        status = e.producer.status()
        assert status.phase == 'BLOCKED' and status.completion_archive_digest and status.transaction_id != first.transaction_id
        moved = checkpoint_state(e)
        assert moved[3].sequence == original[3].sequence+1
        assert e.producer._runtime_components() == (provider,controller,journal)
        with e.journal.transaction() as tx:
            refused(lambda:provider.read(now=e.clock(),transaction=tx), 'COMMITTED_ACCOUNT_HEAD_CHANGED')
        assert sum(row['kind'] == COMPLETE for row in rows(e)) == 2
        count = len(e.exchange.calls)
        refused(e.producer._collect_current, 'COMMITTED_PRODUCER_OPENING_REQUIRED')
        assert len(e.exchange.calls) == count and checkpoint_state(e) == moved and not creates(e)


def test_final_actual_account_read_clock_expiry_preserves_commit_and_never_returns_current_unit():
    with F.fixture() as e:
        first = F.advance(e)
        actual = Controller.read_committed_account
        reads = []
        def delayed(controller, **kwargs):
            value = actual(controller, **kwargs)
            reads.append(value)
            # Delay only after a genuinely published successor is observed.
            if value.committed.transaction_id != first.transaction_id:
                e.clock_cell[0] = value.account.asof+timedelta(seconds=30, microseconds=1)
            return value
        with patch.object(Controller, 'read_committed_account', delayed):
            refused(lambda:F.advance(e))
        assert any(value.committed.transaction_id != first.transaction_id for value in reads)
        assert e.producer.status().phase == 'BLOCKED'
        assert sum(row['kind'] == COMPLETE for row in rows(e)) == 2
        assert not creates(e)


def test_missing_existing_journal_before_next_unit_never_bootstraps_or_collects_again():
    with F.fixture() as e:
        first = F.advance(e)
        before = checkpoint_state(e)
        count = len(e.exchange.calls)
        path = e.journal._root/'journal.jsonl'
        path.unlink()  # disposable fault fixture, not a recovery/repair action
        refused(lambda:F.advance(e))
        assert not path.exists() and len(e.exchange.calls) == count
        assert checkpoint_state(e) == before and e.producer.status().phase == 'BLOCKED'
        assert first.execution_ready is False and not creates(e)


def test_physical_checkpoint_corruption_after_final_actual_owner_read_cannot_return_unit():
    with F.fixture() as e:
        first = F.advance(e)
        actual_current = P.CommittedAccountProducer._current_read
        actual_read = Controller.read_committed_account
        inside, damaged = [], []
        target = e.baseline_store._root/'checkpoint.json'
        def current(producer, *args, **kwargs):
            inside.append(True)
            try:
                return actual_current(producer, *args, **kwargs)
            finally:
                inside.pop()
        def read(controller, **kwargs):
            value = actual_read(controller, **kwargs)
            if inside and not damaged and value.committed.transaction_id != first.transaction_id:
                damaged.append(value.committed.transaction_id)
                target.write_bytes(b'{}')  # actual disposable bytes change after a real successful read
            return value
        with patch.object(P.CommittedAccountProducer, '_current_read', current), \
                patch.object(Controller, 'read_committed_account', read):
            refused(lambda:F.advance(e))
        assert len(damaged) == 1 and e.producer.status().phase == 'BLOCKED'
        assert target.read_bytes() == b'{}'
        assert sum(row['kind'] == COMPLETE for row in rows(e)) == 2
        assert not creates(e)
