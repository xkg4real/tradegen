"""Actual capture/archive/commit reconstruction with disposable signed owner state.

GET replies, recorder coverage and the reviewed initial account anchor are
explicitly synthetic. The collector/replay, temporary owner signatures, guard
math, Journal, two checkpoint stores, independent heads and BundleStore run for
real. New object construction is not an OS restart or native Windows test.
"""
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
import re
from types import SimpleNamespace
from unittest.mock import patch

from core.compliance import model as CM, owner
from execution_control.dry_run import DryRunAdapter
from execution_control.store import GENESIS, Journal
from execution_launch import committed_account as P
from execution_launch import guard_capture_archive as C
from execution_launch import guard_capture_material as M
from execution_launch import guard_generation_archive as A
from execution_launch import guard_generation_format as F
from execution_launch import continuous_guard_commit as GC
from execution_launch import research_bundle_store as BS
from execution_launch.baseline_head import BaselineHead, CheckpointChain
from execution_launch.continuous_guard import GuardAnchor, OwnerContextClaim, reviewed_guard_anchor
from execution_launch.profile import PolicyInputs, risk_policy
from execution_orders import upbit
from tests import compliance_fixtures as CF
from tests import launch_guard_capture_archive as CA
from tests import launch_guard_capture_material as I
from tests import launch_research_bundle_store as B
from tests.launch_baseline_head import head_root
from tests.launch_profile import fixture_profile

D = Decimal


def make_profile(policy, now):
    """A real profile whose risk policy exactly matches the retained package."""
    profile = fixture_profile(now)
    names = ('version', 'initial_equity', 'drawdown_activation_equity', 'positive_profit_loss_fraction',
             'peak_drawdown_fraction', 'zero_profit_day_target_fraction', 'first_day_loss_budget',
             'zero_profit_day_loss_budget', 'recovery_condition')
    inputs = PolicyInputs(source_sha256='a'*64, **{name: getattr(policy, name) for name in names})
    return replace(profile, profile_id='startup-fixture', account_scope='interval-fixture', policy=inputs,
        conventions=replace(profile.conventions, valuation=policy.valuation_convention,
                            daily_loss=policy.daily_loss_convention))


def _claim(account, equity, when, contexts):
    holdings = {(account.venue, position.base_currency): float(position.units) for position in account.positions}
    context = owner.load_context(when, CM.Positions(equity_krw=float(equity), holdings=holdings))
    assert CM.is_sealed(context) and context.code_signed and context.owner.ok
    contexts.append(context)
    return OwnerContextClaim(owner_head_sha256=context.owner.head[1], code_sha256=context.code_hash,
        code_approval_sha256=context.code_hash, signed_floor_krw=D(str(context.owner.limits['total_loss_floor_krw'])),
        signed_daily_loss_krw=D(str(context.owner.limits['daily_loss_krw'])), observed_at=when,
        source_sha256=context.ctx_hash)


@contextmanager
def fixture(*, held=False, start=I.START, capture_options=None, env_options=None, retain=True,
            committed=False, completed=False, control_setup=None, configure=None,
            daily_stopped=False, halted=False):
    equity = D('100045') if held else D('100090')
    options = dict(day_start=equity, high=equity)
    if not held:
        options['loss'] = D(0)
    options.update(env_options or {})
    with CA.fixture(held=held, start=start, env_options=options, capture_options=capture_options) as (storage, env, captured):
        with CF.pubkey_at(env.home/'fixture-owner.pem'), head_root() as hroot:
            key = CF.full_home(env.home, limits={'total_loss_floor_krw':70000.0, 'daily_loss_krw':10000.0})
            if configure is not None:
                configure(env.home, key, start)
            journal = Journal()
            with journal.transaction():  # explicit fixture operator provisioning
                pass
            journal = Journal(root=journal._root, require_existing=True)
            if control_setup is not None:
                control_setup(journal, start)
            rows = journal.snapshot()
            predecessor = rows[-1]['row_sha256'] if rows else GENESIS
            material = M.prepare_guard_capture_material(captured.staged, env.state, now=captured.staged.observed_at)
            base_profile = fixture_profile(captured.staged.observed_at)
            from execution_control.risk import RecoveryCondition
            profile = replace(base_profile, profile_id='startup-fixture', account_scope=env.state.account_scope,
                policy=PolicyInputs(version='startup-synthetic-v1', source_sha256='a'*64,
                    initial_equity=D('70000'), drawdown_activation_equity=D('6000000'),
                    positive_profit_loss_fraction=D('.35'), peak_drawdown_fraction=D('.35'),
                    zero_profit_day_target_fraction=D('.3'), first_day_loss_budget=D('10000'),
                    zero_profit_day_loss_budget=D('10000'), recovery_condition=RecoveryCondition(
                        cutoff_seconds=79200, timezone='Asia/Seoul', reference='day_start_marked_equity')))
            policy = risk_policy(profile)
            contexts = []
            before = _claim(env.anchor_collection.bundle.accounts[0], env.state.equity_krw,
                            env.state.asof, contexts)
            now = captured.staged.observed_at
            after = _claim(material.account_capture.endpoint_accounts[0], material.interval.equity_krw, now, contexts)
            anchor = GuardAnchor(baseline_state_sha256=env.state.state_digest,
                control_journal_head_sha256=predecessor, high_watermark=env.state.high_watermark,
                day_start_equity=env.state.day_start_equity, observed_daily_loss=env.state.observed_daily_loss,
                applied_floor_krw=env.state.high_watermark, daily_stopped=daily_stopped,
                permanently_halted=halted, recorded_at=env.state.asof, source_sha256='7'*64)
            state = reviewed_guard_anchor(anchor, baseline=env.state, policy=policy, owner=before)
            bstore = env.store
            gstore = GC.GuardCheckpointStore(root=env.home)
            bhead = BaselineHead(root=hroot, name='startup-baseline', chain=CheckpointChain(bstore))
            ghead = BaselineHead(root=hroot, name='startup-guard', chain=GC.GuardChain(gstore))
            bhead.initialize_reviewed_head(env.state.state_digest)
            gstore.seed(state, expected_head=state.state_sha256)
            ghead.initialize_reviewed_head(state.state_sha256)
            package = dict(baseline_before=env.state, policy=policy, owner_before=before, owner_after=after,
                path=material.path, valuation_inputs=material.valuation_inputs, account_capture=material.account_capture,
                coverage=material.coverage, interval=material.interval, now=now)
            capture_receipt = C.archive_guard_capture_packet(storage.store, captured.staged, env.state)
            cell = [now]
            e = SimpleNamespace(store=storage.store, reopen_archive=storage.reopen, archive_args=storage.args,
                storage=storage, env=env, captured=captured, source=captured.source, capture_receipt=capture_receipt,
                package=package, material=material, input=None, receipt=None, completion=None, journal=journal,
                guard_store=gstore, guard_head=ghead, baseline_store=bstore, baseline_head=bhead,
                expected_guard_head=state.state_sha256, expected_baseline_head=env.state.state_digest,
                expected_control_head=predecessor, clock=lambda:cell[0], clock_cell=cell, now=now,
                home=env.home, key=key, contexts=contexts, policy=policy, profile=profile,
                adapter=DryRunAdapter(upbit), head_root=hroot)
            e.s = SimpleNamespace(state=state, policy=policy, context=before, journal=journal,
                                  bstore=bstore, gstore=gstore, bhead=bhead, ghead=ghead)
            if retain or committed or completed:
                e.input = retain_input(e)
            if committed or completed:
                commit(e)
            if completed:
                complete(e)
            yield e


def retain_input(e, **changes):
    arguments = dict(expected_guard_head=e.expected_guard_head,
                     expected_baseline_head=e.expected_baseline_head, expected_control_head=e.expected_control_head)
    arguments.update(changes)
    return A.retain_guard_input(e.store, e.capture_receipt.archive_digest, e.package, **arguments)


def integrations(e):
    return dict(journal=e.journal, guard_store=e.guard_store, guard_head=e.guard_head,
                baseline_store=e.baseline_store, baseline_head=e.baseline_head)


def commit(e, **changes):
    args = dict(now=e.clock(), expected_guard_head=e.expected_guard_head,
                expected_baseline_head=e.expected_baseline_head, expected_control_head=e.expected_control_head,
                **integrations(e))
    args.update(changes)
    e.receipt = GC.commit_continuous_guard(e.package, **args)
    return e.receipt


def complete(e, **changes):
    args = dict(clock=e.clock, **integrations(e)); args.update(changes)
    e.completion = A.record_guard_completion(e.store, e.input.archive_digest, e.receipt, **args)
    return e.completion


def provider(e, retained=None, receipt=None):
    retained = e.input if retained is None else retained
    record = retained.record
    return P.CommittedAccountProvider(package=retained.package, receipt=e.receipt if receipt is None else receipt,
        expected_guard_head=record.expected_guard_head, expected_baseline_head=record.expected_baseline_head,
        expected_control_head=record.expected_control_head, **integrations(e))


def refused(call, code=None):
    try:
        call()
    except ValueError as exc:
        assert re.fullmatch(r'[A-Z][A-Z0-9_]+', str(exc)), 'private error text escaped'
        if code is not None:
            assert str(exc) == code, (str(exc), code)
        return str(exc)
    raise AssertionError('expected refusal')


def inert(value):
    assert value.source_authenticated is value.current_freshness_verified is value.execution_ready is False


def state_bytes(e):
    return I.snapshot(e.home), I.snapshot(e.head_root)


def test_actual_input_commit_completion_and_new_objects_preserve_exact_originals():
    with fixture(completed=True) as e:
        before = state_bytes(e)
        restored = A.read_guard_completion(e.reopen_archive(), e.completion.archive_digest,
                                          expected_input_archive_digest=e.input.archive_digest)
        inert(restored); inert(restored.retained_input)
        CA.typed_equal(restored.retained_input.package['account_capture'], e.package['account_capture'])
        assert restored.record.receipt == e.receipt and restored.record.receipt is not e.receipt
        p = provider(e, restored.retained_input, restored.record.receipt)
        with e.journal.transaction() as tx:
            inspection = p.inspect_committed(now=e.clock(), transaction=tx)
            observation = p.read(now=e.clock(), transaction=tx)
        assert inspection.completion_head == restored.record.completion_head
        assert observation.observation.asof == e.package['interval'].end
        assert state_bytes(e) == before


def test_input_idempotency_and_original_evaluation_time_are_distinct_from_commit_input_hash():
    with fixture() as e:
        before = B.files(e.storage.base)
        again = retain_input(e)
        assert again.archive_digest == e.input.archive_digest and B.files(e.storage.base) == before
        e.package = dict(e.package, now=e.package['now']+timedelta(microseconds=1))
        changed = retain_input(e)
        assert changed.record.input_sha256 == e.input.record.input_sha256
        assert changed.record.package_sha256 != e.input.record.package_sha256
        assert changed.archive_digest != e.input.archive_digest


def test_typed_equal_values_cannot_substitute_retained_path_or_material():
    with fixture(retain=False) as e:
        original = e.package
        for value in (replace(original['path'], watermark_source_sha256='e'*64),
                      replace(original['path'], first_sequence=True)):
            e.package = dict(original, path=value)
            before = B.files(e.storage.base)
            refused(lambda:retain_input(e))
            assert B.files(e.storage.base) == before
        e.package = dict(original, valuation_inputs=replace(original['valuation_inputs'],
            opening_cash_krw=original['valuation_inputs'].opening_cash_krw.quantize(D('.00'))))
        refused(lambda:retain_input(e), 'GENERATION_ARCHIVE_BINDING_MISMATCH')


def test_input_predecessor_mismatch_never_commits_or_invents_heads():
    with fixture(retain=False) as e:
        before = state_bytes(e)
        refused(lambda:retain_input(e, expected_baseline_head='0'*64))
        assert state_bytes(e) == before
        assert not e.journal.snapshot()


def test_completion_requires_actual_complete_and_receipt_correspondence():
    with fixture() as e:
        fake = GC.GuardCommitReceipt(transaction_id='1'*64, guard_head=e.expected_guard_head,
            baseline_head=e.expected_baseline_head, control_head=GENESIS, permanently_halted=False, replayed=False)
        refused(lambda:A.record_guard_completion(e.store, e.input.archive_digest, fake,
            clock=e.clock, **integrations(e)), 'GENERATION_ARCHIVE_DURABLE_REFUSED')
        commit(e)
        for name in ('transaction_id', 'guard_head', 'baseline_head', 'control_head'):
            refused(lambda name=name:A.record_guard_completion(e.store,e.input.archive_digest,
                replace(e.receipt, **{name:'f'*64}), clock=e.clock, **integrations(e)))


def test_replay_receipt_new_prefix_is_new_record_and_original_is_preserved():
    with fixture(completed=True) as e:
        original, receipt = e.completion, e.receipt
        e.clock_cell[0] += timedelta(seconds=1)
        with e.journal.transaction() as tx:
            tx.append('halt', {'floor':'100090'}, now=e.clock())
        replay = commit(e)
        assert replay.replayed and replay.permanently_halted
        assert replay.control_head != receipt.control_head
        current = complete(e)
        assert current.archive_digest != original.archive_digest
        reread = A.read_guard_completion(e.store,original.archive_digest,
                                         expected_input_archive_digest=e.input.archive_digest)
        assert reread.record == original.record and reread.record.receipt == receipt
        assert current.record.completion_head == original.record.completion_head


def test_stale_archived_completion_keeps_original_times_and_durable_inspection_only():
    with fixture(committed=True) as e:
        e.clock_cell[0] += timedelta(minutes=1)
        completion = complete(e)
        assert completion.retained_input.record.evaluated_at == e.now
        p = provider(e)
        with e.journal.transaction() as tx:
            actual = p.inspect_committed(now=e.clock(), transaction=tx)
            assert actual.asof == e.package['interval'].end and actual.execution_ready is False
            refused(lambda:p.read(now=e.clock(), transaction=tx))


def test_same_bytes_retry_is_idempotent_but_new_recording_observation_is_versioned():
    with fixture(completed=True) as e:
        first = e.completion; before = B.files(e.storage.base)
        assert complete(e).archive_digest == first.archive_digest
        assert B.files(e.storage.base) == before
        e.clock_cell[0] += timedelta(microseconds=1)
        second = complete(e)
        assert second.archive_digest != first.archive_digest
        assert second.record.receipt == first.record.receipt


def test_missing_capture_backup_refuses_entire_three_graph_read():
    with fixture(completed=True) as e:
        raw=e.store.read_raw(e.capture_receipt.archive_digest,require_backup=True).files['packet']
        target=B.chunk_path(e.store,raw,backup=True)
        target.write_bytes(b'X'*target.stat().st_size)
        before=B.files(e.storage.base)
        refused(lambda:A.read_guard_completion(e.reopen_archive(),e.completion.archive_digest,
            expected_input_archive_digest=e.input.archive_digest), 'GENERATION_ARCHIVE_STORE_REFUSED')
        assert B.files(e.storage.base)==before


def test_input_and_completion_are_exact_singleton_raw_wrappers_without_authority():
    with fixture(completed=True) as e:
        for retained, name, parent in ((e.input,'guard-input',e.capture_receipt.archive_digest),
                                      (e.completion,'guard-completion',e.input.archive_digest)):
            raw = e.store.read_raw(retained.archive_digest,require_backup=True)
            assert set(raw.files) == {name} and raw.manifest.parent_bundle_sha256 == parent
            assert raw.manifest.kind == 'RAW_ARCHIVED' and raw.manifest.expected_candidates is None
            assert raw.manifest.run_id == name+'-'+retained.record_sha256
            inert(retained)
        refused(lambda:A.read_guard_completion(e.store,e.completion.archive_digest,
            expected_input_archive_digest='a'*64), 'GENERATION_ARCHIVE_BINDING_MISMATCH')


def test_arbitrary_oversized_bundle_is_refused_before_full_payload_read():
    with fixture() as e:
        logical='guard-input'
        raw=b' '*65537
        metadata, digest, payloads=A._manifest(e.store,raw,'a'*64,e.capture_receipt.archive_digest,'input')
        e.store.archive_raw(metadata,payloads)
        with patch.object(e.store,'read_raw',side_effect=AssertionError('full graph must not be allocated')):
            refused(lambda:A.read_guard_input(e.store,digest),'GENERATION_ARCHIVE_RESOURCE_LIMIT')


def test_caller_hidden_attributes_and_huge_decimal_refuse_before_deepcopy():
    with fixture(retain=False) as e:
        class Trap:
            def __deepcopy__(self, memo): raise AssertionError('hidden copy executed')
        bad=deepcopy(e.package)
        object.__setattr__(bad['owner_before'],'extra',Trap())
        for package in (bad, dict(e.package, policy=replace(e.policy, initial_equity=D('1E+1000000000')))):
            copies=[]
            def copied(*args,**kwargs):
                copies.append(True)
                raise AssertionError('copy before admission')
            with patch.object(A,'deepcopy',side_effect=copied):
                refused(lambda package=package:A.retain_guard_input(e.store,e.capture_receipt.archive_digest,package,
                    expected_guard_head=e.expected_guard_head,expected_baseline_head=e.expected_baseline_head,
                    expected_control_head=e.expected_control_head))
            assert copies==[]


def test_completion_clock_failures_refuse_without_claiming_success():
    with fixture(committed=True) as e:
        for clock in (lambda:None, lambda:e.now.replace(tzinfo=None)):
            refused(lambda clock=clock:complete(e,clock=clock),'GENERATION_ARCHIVE_CLOCK_INVALID')
        values=iter((e.now,e.now-timedelta(microseconds=1)))
        refused(lambda:complete(e,clock=lambda:next(values)),'GENERATION_ARCHIVE_CLOCK_ROLLBACK')


def test_final_real_store_recheck_refuses_after_actual_result_publication():
    with fixture(committed=True) as e:
        original=A._inspect
        calls=[]
        def change(provider,journal,now,*args):
            result=original(provider,journal,now,*args); calls.append(result)
            if len(calls)==1:
                # A negative actual independent-head adapter fault, not fake success.
                e.guard_head.read=lambda:'a'*64
            return result
        with patch.object(A,'_inspect',side_effect=change):
            refused(lambda:complete(e),'GENERATION_ARCHIVE_DURABLE_REFUSED')
        assert len(calls)==1
        assert e.store._catalog().entries  # prior raw/input/completion evidence retained


def test_actual_archive_and_journal_locks_never_overlap_in_completion_recording():
    with fixture(committed=True) as e:
        held=[]; lock=e.store._locked; transaction=e.journal.transaction
        @contextmanager
        def archive_lock():
            assert not held
            with lock() as anchor:
                held.append('archive')
                try: yield anchor
                finally: held.pop()
        @contextmanager
        def control_lock():
            assert not held
            with transaction() as tx:
                held.append('control')
                try: yield tx
                finally: held.pop()
        with patch.object(e.store,'_locked',side_effect=archive_lock),patch.object(e.journal,'transaction',side_effect=control_lock):
            completion=complete(e)
        assert completion.record.receipt==e.receipt and not held


def test_actual_write_failure_retains_input_and_never_performs_guard_commit():
    with fixture(retain=False) as e:
        before=state_bytes(e)
        with patch.object(e.store,'archive_raw',side_effect=BS.BundleStoreError('BUNDLE_STORE_RESOURCE_LIMIT')):
            refused(lambda:retain_input(e),'GENERATION_ARCHIVE_RESOURCE_LIMIT')
        assert state_bytes(e)==before and e.journal.snapshot()==()


def test_bad_saved_completion_metadata_is_archive_claim_not_actual_durable_proof():
    with fixture(completed=True) as e:
        for change in (dict(completion_head='d'*64),dict(observed_control_head='c'*64),
                       dict(recorded_at=e.now-timedelta(microseconds=1)),
                       dict(recorded_at=e.now+timedelta(microseconds=1))):
            bad=replace(e.completion.record,**change)
            raw=F.completion_bytes(bad); digest=F.completion_digest(bad)
            manifest, archive, payloads=A._manifest(e.store,raw,digest,e.input.archive_digest,'completion')
            e.store.archive_raw(manifest,payloads)
            retained=A.read_guard_completion(e.store,archive,expected_input_archive_digest=e.input.archive_digest)
            inert(retained)
            with e.journal.transaction() as tx:
                actual=provider(e).inspect_committed(now=e.now,transaction=tx)
                refused(lambda:A._completion_matches(retained.record,retained.retained_input,actual,tx.events,e.now),
                        'GENERATION_ARCHIVE_BINDING_MISMATCH')


def test_partial_primary_publications_require_backup_and_exact_retry_preserves_identity():
    for completion in (False,True):
        with fixture(retain=completion,committed=completion) as e:
            actual=e.store._stage
            def fail_backup(values,backup,anchor):
                if backup:
                    raise BS.BundleStoreError('BUNDLE_STORE_OBJECT_REFUSED')
                return actual(values,backup,anchor)
            before=state_bytes(e)
            with patch.object(e.store,'_stage',side_effect=fail_backup):
                refused(lambda:complete(e) if completion else retain_input(e),'GENERATION_ARCHIVE_STORE_REFUSED')
            with e.store._locked():
                catalog=e.store._load()
                revision='guard-completion-v1' if completion else 'guard-input-v1'
                rows=[row for row in catalog.entries.values() if row.row['revision_id']==revision]
            assert len(rows)==1 and rows[0].backed is False
            digest=rows[0].row['bundle_sha256']
            if completion:
                refused(lambda:A.read_guard_completion(e.store,digest,expected_input_archive_digest=e.input.archive_digest))
            else:
                refused(lambda:A.read_guard_input(e.store,digest))
            retained=complete(e) if completion else retain_input(e)
            assert retained.archive_digest==digest and state_bytes(e)==before


def test_completion_response_loss_preserves_actual_backed_record_for_exact_retry():
    with fixture(committed=True) as e:
        actual=e.store.archive_raw
        written=[]
        def lost(*args,**kwargs):
            written.append(actual(*args,**kwargs))
            raise BS.BundleStoreError('BUNDLE_STORE_STORAGE_CHANGED')
        before=state_bytes(e)
        with patch.object(e.store,'archive_raw',side_effect=lost):
            refused(lambda:complete(e),'GENERATION_ARCHIVE_STORE_REFUSED')
        assert len(written)==1 and written[0].backup_verified
        retained=complete(e)
        assert retained.archive_digest==written[0].bundle_digest and state_bytes(e)==before


def test_clock_rollback_during_last_actual_inspection_never_returns_success():
    with fixture(committed=True) as e:
        original=A._inspect
        calls=[]
        def delayed(*args,**kwargs):
            result=original(*args,**kwargs);calls.append(result)
            if len(calls)==2:
                e.clock_cell[0]-=timedelta(microseconds=1)
            return result
        with patch.object(A,'_inspect',side_effect=delayed):
            refused(lambda:complete(e),'GENERATION_ARCHIVE_CLOCK_ROLLBACK')
        assert len(calls)==2


def test_existing_only_journal_is_mandatory_before_any_completion_inspection():
    with fixture(committed=True) as e:
        legacy=Journal(root=e.journal._root)
        before=state_bytes(e)
        refused(lambda:complete(e,journal=legacy),'GENERATION_ARCHIVE_INPUT_INVALID')
        assert state_bytes(e)==before


def test_missing_or_torn_actual_journal_is_never_reinitialized_by_completion_retention():
    for mode in ('lock','pair','torn'):
        with fixture(committed=True) as e:
            root=e.journal._root
            if mode=='lock':
                (root/'control.lock').unlink()
            elif mode=='pair':
                (root/'journal.jsonl').unlink();(root/'checkpoint.json').unlink()
            else:
                with (root/'journal.jsonl').open('ab') as stream:
                    stream.write(b'{')
            before=state_bytes(e),B.files(e.storage.base)
            refused(lambda:complete(e),'GENERATION_ARCHIVE_DURABLE_REFUSED')
            assert (state_bytes(e),B.files(e.storage.base))==before
