"""Actual signed archives, durable incidents and recovery transactions.

All owner keys, homes, observations and storage roots are disposable fixtures.
The small verified fixture contains deliberately unissued claims; its recovery
proves archival identity only. A separate actual recorded-research case exercises
the complete family. Fault spies call actual readers/writers before the selected
failure and never fabricate a positive authority, recovery or evaluation result.
No account/API/network/notification transport or actual trading is exercised.
"""
from contextlib import contextmanager
from datetime import timedelta
import base64
import shutil
from types import SimpleNamespace
from unittest.mock import patch

from core.compliance import owner
from execution_control.owner_authority import CurrentOwnerAuthority
from execution_launch import bundle_recovery as B, bundle_attestation as A
from execution_launch import research_bundle_format as BF, research_bundle_store as BS
from execution_launch import research_incidents as IF, research_incident_store as IS
from execution_launch import research_incident_monitor as M, research_revocation as V
from execution_launch import research_recovery as R, research_recovery_attempts as F
from execution_launch import research_recovery_store as S, strategy as E
from execution_launch.recovery_artifact import build_recovery_artifact
from tests import compliance_fixtures as CF, launch_bundle_auth as AF
from tests import launch_bundle_recovery as BR, launch_research_bundle_store as SF
from tests import launch_research_incident_integration as IR
from tools.owner.research_incidents import provision_incident_store
from tools.owner.research_recovery import provision_recovery_attempt_store


class InjectedCrash(BaseException):
    """Simulated process loss, not an ordinary I/O failure or valid observation."""


def _roots(base, names):
    result = tuple(base/name for name in names)
    for root in result:
        root.mkdir()
    return result


def _attempt_store(base, *, max_records=1024):
    roots = _roots(base, ('attempts','attempt-backups','attempt-heads'))
    args = dict(root=roots[0],backup_root=roots[1],head_root=roots[2],head_name='recovery-attempts',
        limits=S.RecoveryStoreLimits(format_limits=F.RecoveryAttemptLimits(),
            max_journal_bytes=32*1024*1024,max_records=max_records))
    attempts = S.RecoveryAttemptStore(**args)
    provision_recovery_attempt_store(attempts)
    return attempts,args


@contextmanager
def fixture(*, verified=False, registered=True, attempt_max_records=1024):
    """Cheap genuine archival fixture shared with CLI tests; no issued metrics."""
    with BR.fixture(verified=verified) as original:
        roots = _roots(original.root, ('incidents','incident-backups','incident-heads'))
        incident_args = dict(root=roots[0],backup_root=roots[1],head_root=roots[2],
            head_name='research-incidents',limits=IS.IncidentStoreLimits(
                format_limits=IF.IncidentLimits(),max_journal_bytes=32*1024*1024,max_records=1024))
        incident_store = IS.IncidentStore(**incident_args)
        provision_incident_store(incident_store)
        attempts,attempt_args = _attempt_store(original.root,max_records=attempt_max_records)
        e = SimpleNamespace(**vars(original),base=original.root,key=original.signer.key,
            code=original.signer.code,destination=BR.destination(original),
            incident_store=incident_store,incident_args=incident_args,
            attempts=attempts,attempt_args=attempt_args,route=None,incident_id=None)
        M.register_target(e.incident_store,e.store,e.digest,clock=e.clock)
        if registered:
            e.route=register_route(e)
        yield e


def register_route(e, **changes):
    args=dict(clock=e.clock,authority_provider=e.provider)
    return R.register_recovery_route(e.incident_store,e.attempts,e.store,e.destination,
        e.digest,e.document,**(args|changes))


def damage(e, *, which='catalog'):
    """Actually damage source primary only; original backup remains exact."""
    if which=='catalog':
        (e.store.roots.sealed_root/'catalog.jsonl').write_bytes(b'broken source catalog\n')
    elif which=='payload':
        saved=e.store.read_raw(e.digest,require_backup=True)
        value=next(value for value in saved.files.values() if value)
        path=SF.chunk_path(e.store,value)
        raw=path.read_bytes();path.write_bytes(bytes([raw[0]^1])+raw[1:])
    else:
        raise AssertionError('unknown fixture fault')
    checked=M.check_target(e.incident_store,e.store,e.digest,clock=e.clock)
    assert checked.held and checked.incident_ids and not checked.graph_checked
    e.incident_id=checked.incident_ids[0]
    return e.incident_id


def run(e, **changes):
    args=dict(route_id=e.route.route_id,incident_id=e.incident_id,
        attestation_bytes=e.document,clock=e.clock,authority_provider=e.provider)
    return R.run_recovery_once(e.incident_store,e.attempts,
        R.RecoveryRouteConfig(source=e.source,destination=e.destination),**(args|changes))


def reopen(e):
    e.attempts=S.RecoveryAttemptStore(**e.attempt_args)
    e.incident_store=IS.IncidentStore(**e.incident_args)
    e.provider=CurrentOwnerAuthority(clock=e.clock)


def archive_bytes(store):
    return SF.files(store.roots.sealed_root),SF.files(store.roots.backup_root)


def attempt_bytes(e):
    return tuple(SF.files(e.attempt_args[name]) for name in ('root','backup_root','head_root'))


def crashed(call):
    try:
        call()
    except InjectedCrash:
        return
    raise AssertionError('simulated process loss did not propagate')


def no_operation(value):
    assert type(value) is R.RecoveryControllerObservation
    for field in ('quarantine_released','current_use_eligible','research_selection_ready',
                  'execution_ready','automatic_operational_recovery_supported'):
        assert getattr(value,field) is False,(field,getattr(value,field))


def success(e, value):
    no_operation(value)
    assert value.phase=='EXACT_ARCHIVE_RESTORED' and value.bundle_digest==e.digest
    snapshot=e.attempts.inspect()
    assert value.attempt_head==snapshot.head and value.attempt_sequence==snapshot.sequence
    attempt=next(item for item in snapshot.state.attempts if item.attempt_id==value.attempt_id)
    assert attempt.terminal and attempt.phase==value.phase
    assert len(attempt.outcomes)==1 and attempt.outcomes[0].status==value.phase
    notice=next(item for item in snapshot.state.outbox if item.outcome_event_id==value.outcome_event_id)
    assert notice.status==value.phase and notice.quarantine=='REMAINS' and notice.current_use=='NOT_GRANTED'
    assert notice.bundle_digest==e.digest and notice.kind=='RECOVERY_RESULT_RECORDED'
    assert M.check_target(e.incident_store,e.store,e.digest,clock=e.clock).held
    artifact=e.destination.read_raw(value.recovery_artifact_digest,require_backup=True)
    assert artifact.files['attestation']==e.document
    return attempt,notice


def revoke(e):
    digest=V.revocation_target(e.document,purpose=A.PURPOSE)
    CF.sign(e.key,V.EVENT_KIND,dict(purpose=A.PURPOSE,target_sha256=digest,reason_code='OWNER_WITHDRAWN'),
        utc=e.cell[0].strftime('%Y-%m-%dT%H:%M:%SZ'))
    return digest


def benign_growth(e, *, evidence='actual temporary checkpoint growth'):
    return CF.sign(e.key,'age_of_majority',dict(birth_date='2000-01-01',evidence=evidence),
        utc=e.cell[0].strftime('%Y-%m-%dT%H:%M:%SZ'))


def test_actual_registration_preserves_all_source_bytes_and_does_not_copy_or_release():
    with fixture(registered=False) as e:
        original,destination=archive_bytes(e.store),archive_bytes(e.destination)
        incidents=e.incident_store.inspect()
        result=register_route(e)
        state=e.attempts.inspect()
        assert result.route_id==state.state.routes[0].route_id
        assert result.bundle_digest==e.digest and state.sequence==1
        assert not state.state.attempts and not state.state.outbox
        assert e.incident_store.inspect()==incidents
        assert archive_bytes(e.store)==original and archive_bytes(e.destination)==destination
        benign_growth(e)
        repeated=register_route(e)
        assert repeated.route_id==result.route_id and e.attempts.inspect()==state
        damage(e)
        AF.refused(lambda:register_route(e))
        assert e.attempts.inspect()==state


def test_durable_start_precedes_actual_copy_and_preserves_failed_raw_and_original_incident():
    with fixture() as e:
        damage(e)
        original,incident=archive_bytes(e.store),e.incident_store.inspect()
        actual,seen=e.destination.archive_raw,[]
        def copy(*args,**kwargs):
            state=e.attempts.inspect().state
            assert len(state.attempts)==1 and state.attempts[0].phase=='IN_PROGRESS'
            assert state.attempts[0].execution_count==1 and not state.outbox
            assert state.events[-1].kind=='ATTEMPT_STARTED'
            seen.append(args[0])
            return actual(*args,**kwargs)
        issued=dict(E._EVALUATED)
        with patch.object(e.destination,'archive_raw',side_effect=copy):
            result=run(e)
        success(e,result)
        restored=e.destination.read_raw(e.digest,require_backup=True)
        assert restored.manifest_bytes==e.raw_bytes and dict(restored.files)==e.payloads
        assert restored.files['bad']==b'{broken JSON' and restored.files['empty']==b''
        assert len(seen)==2 and E._EVALUATED==issued
        assert archive_bytes(e.store)==original and e.incident_store.inspect()==incident


def test_verified_archive_keeps_all_candidates_and_linked_raw_without_new_evaluation():
    with fixture(verified=True) as e:
        damage(e);issued=dict(E._EVALUATED)
        with patch.object(E,'evaluate_capture_json',side_effect=AssertionError('recovery is not evaluation')):
            result=run(e)
        success(e,result)
        saved=e.destination.read_verified(e.digest,require_backup=True)
        raw=e.destination.read_raw(saved.manifest.input_archive_digest,require_backup=True)
        assert tuple(item.study_id for item in saved.manifest.candidates)==('study-a','study-b')
        assert saved.manifest_bytes==e.verified_bytes and raw.manifest_bytes==e.raw_bytes
        assert b'losing result retained' in saved.files['capture_a']
        assert b'not an issued evaluation' in saved.files['evaluation']
        assert dict(saved.files)==e.payloads and E._EVALUATED==issued


def test_real_partial_raw_publication_resumes_same_plan_after_sixty_seconds():
    with fixture(verified=True) as e:
        damage(e)
        actual=e.destination.archive_raw
        def copy_then_crash(*args,**kwargs):
            actual(*args,**kwargs)
            raise InjectedCrash()
        with patch.object(e.destination,'archive_raw',side_effect=copy_then_crash):
            crashed(lambda:run(e))
        snapshot=e.attempts.inspect();attempt=snapshot.state.attempts[0]
        assert attempt.phase=='IN_PROGRESS' and attempt.execution_count==1 and not snapshot.state.outbox
        assert e.destination.read_raw(BF.raw_archive_digest(e.raw),require_backup=True).manifest_bytes==e.raw_bytes
        partial=archive_bytes(e.destination)
        reopen(e);e.cell[0]+=timedelta(seconds=60)-timedelta(microseconds=1)
        AF.refused(lambda:run(e))
        assert e.attempts.inspect()==snapshot and archive_bytes(e.destination)==partial
        e.cell[0]+=timedelta(microseconds=1)
        result=run(e)
        done,_=success(e,result)
        assert result.attempt_id==attempt.attempt_id and result.plan_id==attempt.plan_id
        assert result.execution_count==2 and len(done.entries)==2


def test_completed_target_and_signature_without_outcome_revalidate_after_source_disappears():
    for verified in (False,True):
        with fixture(verified=verified) as e:
            damage(e)
            actual=e.attempts.commit
            def before_outcome(event,**kwargs):
                if event.kind=='ATTEMPT_OBSERVED':
                    assert event.payload['status']=='EXACT_ARCHIVE_RESTORED'
                    raise InjectedCrash()
                return actual(event,**kwargs)
            with patch.object(e.attempts,'commit',side_effect=before_outcome):
                crashed(lambda:run(e))
            pending=e.attempts.inspect().state.attempts[0]
            assert pending.phase=='IN_PROGRESS' and not pending.outcomes
            identifier=F.artifact_incident_id(e.incident_id)
            artifact,_,_=build_recovery_artifact(e.document,incident_id=identifier,limits=e.destination.limits)
            artifact_digest=BF.raw_archive_digest(artifact)
            assert e.destination.read_raw(artifact_digest,require_backup=True).files['attestation']==e.document
            before=archive_bytes(e.destination)
            shutil.rmtree(e.store.roots.sealed_root);shutil.rmtree(e.store.roots.backup_root)
            reopen(e);e.cell[0]+=timedelta(seconds=60)
            with (patch.object(B,'restore_signed_backup',side_effect=AssertionError('source recopy')),
                  patch.object(e.destination,'archive_raw',side_effect=AssertionError('destination mutation')),
                  patch.object(e.destination,'commit_verified',side_effect=AssertionError('destination mutation'))):
                result=run(e)
            success(e,result)
            assert result.execution_count==2 and result.recovery_artifact_digest==artifact_digest
            assert archive_bytes(e.destination)==before


def test_missing_signature_artifact_after_crash_and_missing_source_never_becomes_success():
    with fixture() as e:
        damage(e);actual=e.destination.archive_raw
        def copy_target_then_crash(*args,**kwargs):
            actual(*args,**kwargs)
            raise InjectedCrash()
        with patch.object(e.destination,'archive_raw',side_effect=copy_target_then_crash):
            crashed(lambda:run(e))
        assert e.destination.read_raw(e.digest,require_backup=True).manifest_bytes==e.raw_bytes
        shutil.rmtree(e.store.roots.sealed_root);shutil.rmtree(e.store.roots.backup_root)
        before=archive_bytes(e.destination)
        reopen(e);e.cell[0]+=timedelta(seconds=60)
        result=run(e)
        no_operation(result)
        assert result.phase!='EXACT_ARCHIVE_RESTORED' and result.recovery_artifact_digest is None
        assert archive_bytes(e.destination)==before
        assert all(message.status!='EXACT_ARCHIVE_RESTORED' for message in e.attempts.inspect().state.outbox)


def test_three_durable_execution_entries_exhaust_budget_across_fresh_instances():
    with fixture() as e:
        damage(e);before=archive_bytes(e.destination)
        for number in (1,2,3):
            with patch.object(B,'restore_signed_backup',side_effect=InjectedCrash()):
                crashed(lambda:run(e))
            state=e.attempts.inspect().state
            assert len(state.attempts)==1 and state.attempts[0].execution_count==number
            assert state.attempts[0].phase=='IN_PROGRESS' and not state.outbox
            reopen(e);e.cell[0]+=timedelta(seconds=60)
        final=e.attempts.inspect()
        with patch.object(B,'restore_signed_backup',side_effect=AssertionError('fourth copy')):
            AF.refused(lambda:run(e))
        assert e.attempts.inspect()==final and archive_bytes(e.destination)==before


def test_actual_revocation_before_start_is_terminal_and_new_provider_cannot_retry():
    with fixture() as e:
        damage(e);revoke(e);before=archive_bytes(e.destination)
        result=run(e)
        no_operation(result)
        assert result.phase=='AUTHORITY_REFUSED' and result.execution_count==1
        state=e.attempts.inspect();attempt=state.state.attempts[0]
        assert attempt.terminal and attempt.entries[0].kind=='PREFLIGHT_REFUSED'
        assert len(state.state.outbox)==1
        assert attempt.outcomes[0].reason_code=='RECOVERY_ATTESTATION_REVOKED'
        # The private refusal carries an actual freshly verified checkpoint.
        assert attempt.outcomes[0].revocation_status=='REVOKED'
        assert attempt.outcomes[0].checkpoint is not None
        reopen(e);e.cell[0]+=timedelta(seconds=60)
        with (patch.object(B,'inspect_signed_backup',side_effect=AssertionError('terminal source retry')),
              patch.object(B,'restore_signed_backup',side_effect=AssertionError('terminal copy retry')),
              patch.object(CurrentOwnerAuthority,'observe_checkpoint',side_effect=AssertionError('terminal authority retry'))):
            again=run(e)
        assert again.attempt_id==result.attempt_id and again.phase==result.phase
        assert e.attempts.inspect()==state and archive_bytes(e.destination)==before


def test_revocation_after_actual_copy_preserves_bytes_but_records_terminal_refusal():
    with fixture() as e:
        damage(e);actual=B.restore_signed_backup
        def restore_then_revoke(*args,**kwargs):
            result=actual(*args,**kwargs)
            revoke(e)
            return result
        with patch.object(B,'restore_signed_backup',side_effect=restore_then_revoke):
            result=run(e)
        no_operation(result)
        assert result.phase=='AUTHORITY_REFUSED'
        assert e.destination.read_raw(e.digest,require_backup=True).manifest_bytes==e.raw_bytes
        assert e.attempts.inspect().state.attempts[0].terminal
        assert M.check_target(e.incident_store,e.store,e.digest,clock=e.clock).held


def test_completed_outcome_response_loss_has_one_notification_and_no_second_copy():
    with fixture() as e:
        damage(e);actual=e.attempts.commit
        def committed_then_crash(event,**kwargs):
            result=actual(event,**kwargs)
            if event.kind=='ATTEMPT_OBSERVED':
                raise InjectedCrash()
            return result
        with patch.object(e.attempts,'commit',side_effect=committed_then_crash):
            crashed(lambda:run(e))
        state=e.attempts.inspect();before=archive_bytes(e.destination)
        assert len(state.state.outbox)==1 and state.state.attempts[0].phase=='EXACT_ARCHIVE_RESTORED'
        reopen(e);e.cell[0]+=timedelta(hours=2)  # expired: historical result remains historical
        with (patch.object(B,'restore_signed_backup',side_effect=AssertionError('duplicate copy')),
              patch.object(B,'verify_restored_archive',side_effect=AssertionError('not a refreshed observation')),
              patch.object(CurrentOwnerAuthority,'observe_checkpoint',side_effect=AssertionError('not current authority'))):
            result=run(e)
        no_operation(result)
        assert result.phase=='EXACT_ARCHIVE_RESTORED' and result.observed_at<e.cell[0]
        assert e.attempts.inspect()==state and archive_bytes(e.destination)==before


def test_result_delivery_reports_cannot_clear_incident_or_reissue_recovery():
    with fixture() as e:
        damage(e);result=run(e);_,notice=success(e,result)
        for identifier,outcome in (('delivery-one','unknown'),('delivery-two','failed'),('delivery-three','delivered')):
            state=e.attempts.inspect()
            event=F.make_event('DELIVERY_REPORTED',dict(message_id=notice.message_id,
                delivery_attempt_id=identifier,outcome=outcome),observed_at=e.cell[0])
            committed=e.attempts.commit(event,expected_head=state.head)
            assert e.attempts.commit(event,expected_head=committed.head)==committed
        state=e.attempts.inspect()
        assert not state.state.pending_notifications and len(state.state.outbox)==1
        assert state.state.attempts[0].execution_count==1
        assert M.check_target(e.incident_store,e.store,e.digest,clock=e.clock).held
        altered=F.make_event('DELIVERY_REPORTED',dict(message_id=notice.message_id,
            delivery_attempt_id='delivery-three',outcome='failed'),observed_at=e.cell[0])
        AF.refused(lambda:e.attempts.commit(altered,expected_head=state.head))
        assert e.attempts.inspect()==state


def test_partial_outcome_head_publication_refuses_restart_without_adoption():
    with fixture() as e:
        damage(e);actual=e.attempts.commit
        def refuse_outcome_head(event,**kwargs):
            if event.kind=='ATTEMPT_OBSERVED':
                with patch.object(e.attempts.head,'compare_and_set',return_value=False):
                    return actual(event,**kwargs)
            return actual(event,**kwargs)
        with patch.object(e.attempts,'commit',side_effect=refuse_outcome_head):
            AF.refused(lambda:run(e))
        before=attempt_bytes(e);destination=archive_bytes(e.destination)
        assert e.destination.read_raw(e.digest,require_backup=True).manifest_bytes==e.raw_bytes
        reopen(e);e.cell[0]+=timedelta(seconds=60)
        with patch.object(e.attempts.head,'initialize_reviewed_head',side_effect=AssertionError('adoption')):
            AF.refused(lambda:run(e))
        assert attempt_bytes(e)==before and archive_bytes(e.destination)==destination


def test_failed_start_publication_cannot_begin_copy_or_reanchor_on_restart():
    with fixture() as e:
        damage(e);before=archive_bytes(e.destination)
        with (patch.object(e.attempts.head,'compare_and_set',return_value=False),
              patch.object(B,'restore_signed_backup',side_effect=AssertionError('uncommitted START'))):
            AF.refused(lambda:run(e),'RECOVERY_RECORD_UNCONFIRMED')
        pending=attempt_bytes(e)
        assert archive_bytes(e.destination)==before
        reopen(e);e.cell[0]+=timedelta(seconds=60)
        with (patch.object(e.attempts.head,'initialize_reviewed_head',side_effect=AssertionError('head adoption')),
              patch.object(B,'restore_signed_backup',side_effect=AssertionError('partial START replay'))):
            AF.refused(lambda:run(e))
        assert attempt_bytes(e)==pending and archive_bytes(e.destination)==before


def test_start_fits_but_outcome_capacity_refuses_before_start_or_destination_write():
    with fixture(attempt_max_records=2) as e:
        damage(e)
        before=e.attempts.inspect();storage=attempt_bytes(e)
        destination=archive_bytes(e.destination);incident=e.incident_store.inspect()
        assert before.sequence==1 and len(before.state.routes)==1
        actual_pair=e.attempts.admit_pair;seen=[]
        def admit_pair(first,second,**kwargs):
            assert first.kind=='ATTEMPT_STARTED' and second.kind=='ATTEMPT_OBSERVED'
            # The actual first row alone fits: this is outcome capacity failure,
            # not an invalid START or an invented admission verdict.
            observed=e.attempts.admit(first,**kwargs)
            assert observed==before
            seen.append(first.event_id)
            return actual_pair(first,second,**kwargs)
        with (patch.object(e.attempts,'admit_pair',side_effect=admit_pair),
              patch.object(B,'restore_signed_backup',side_effect=AssertionError('outcome cannot fit'))):
            AF.refused(lambda:run(e),'RECOVERY_STORE_LIMIT_EXCEEDED')
        assert len(seen)==1 and e.attempts.inspect()==before
        assert not before.state.attempts and not before.state.outbox
        assert attempt_bytes(e)==storage and archive_bytes(e.destination)==destination
        assert e.incident_store.inspect()==incident


def test_replaced_source_backup_root_at_same_path_is_terminal_without_copy():
    with fixture() as e:
        damage(e)
        backup=e.source.roots.backup_root
        retained=e.root/'original-backup-retained'
        original_backup=SF.files(backup)
        original_primary=SF.files(e.source.roots.sealed_root)
        old_identity=(backup.stat().st_dev,backup.stat().st_ino)
        backup.rename(retained);backup.mkdir()
        assert (backup.stat().st_dev,backup.stat().st_ino)!=old_identity
        destination=archive_bytes(e.destination);incident=e.incident_store.inspect()
        with patch.object(B,'restore_signed_backup',side_effect=AssertionError('replacement backup')):
            result=run(e)
        no_operation(result)
        assert result.phase=='EVIDENCE_REFUSED' and result.recovery_artifact_digest is None
        snapshot=e.attempts.inspect();attempt=snapshot.state.attempts[0]
        assert attempt.terminal and attempt.execution_count==1
        assert attempt.entries[0].kind=='PREFLIGHT_REFUSED'
        assert attempt.outcomes[0].reason_code=='RECOVERY_ROOT_CHANGED'
        assert len(snapshot.state.outbox)==1 and snapshot.state.outbox[0].status=='EVIDENCE_REFUSED'
        assert not SF.files(backup) and SF.files(retained)==original_backup
        assert SF.files(e.source.roots.sealed_root)==original_primary
        assert archive_bytes(e.destination)==destination and e.incident_store.inspect()==incident
        reopen(e);e.cell[0]+=timedelta(seconds=60)
        again=run(e)
        assert again.phase==result.phase and again.attempt_id==result.attempt_id
        assert e.attempts.inspect()==snapshot and archive_bytes(e.destination)==destination
        assert SF.files(retained)==original_backup and not SF.files(backup)


def test_concurrent_controller_operation_cannot_resume_running_copy_even_after_due_time():
    with fixture() as e:
        damage(e);before=archive_bytes(e.destination);snapshot=e.attempts.inspect()
        other=S.RecoveryAttemptStore(**e.attempt_args)
        with e.attempts.operation():
            original=e.attempts;e.attempts=other
            try:
                AF.refused(lambda:run(e),'RECOVERY_STORE_OPERATION_LOCKED')
            finally:
                e.attempts=original
        assert e.attempts.inspect()==snapshot and archive_bytes(e.destination)==before


def test_actual_checkpoint_accepts_verified_growth_but_rejects_truncated_or_forked_prefix():
    for rewrite in ('truncate','fork'):
        with fixture() as e:
            damage(e);prefix=owner.log_path().read_bytes()
            benign_growth(e)
            with patch.object(B,'restore_signed_backup',side_effect=InjectedCrash()):
                crashed(lambda:run(e))
            checkpoint=e.attempts.inspect().state.attempts[0].entries[0].checkpoint
            assert checkpoint.owner_head[0]>=2
            owner.log_path().write_bytes(prefix)
            if rewrite=='fork':
                benign_growth(e,evidence='different signed entry at same sequence')
            reopen(e);e.cell[0]+=timedelta(seconds=60)
            result=run(e)
            no_operation(result)
            assert result.phase=='AUTHORITY_REFUSED' and e.attempts.inspect().state.attempts[0].terminal
            assert not (e.destination.roots.sealed_root/'catalog.jsonl').read_bytes()
    with fixture() as e:
        damage(e)
        with patch.object(B,'restore_signed_backup',side_effect=InjectedCrash()):
            crashed(lambda:run(e))
        benign_growth(e);reopen(e);e.cell[0]+=timedelta(seconds=60)
        success(e,run(e))


def test_actual_key_rotation_and_new_code_approval_are_terminal_after_restart():
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    for change in ('key','code'):
        with fixture() as e:
            damage(e)
            with patch.object(B,'restore_signed_backup',side_effect=InjectedCrash()):
                crashed(lambda:run(e))
            utc=e.cell[0].strftime('%Y-%m-%dT%H:%M:%SZ')
            if change=='code':
                CF.other_code(e.key,utc=utc)
            else:
                other=Ed25519PrivateKey.from_private_bytes(bytes(range(1,33)))
                encode=lambda key:base64.b64encode(key.public_key().public_bytes_raw()).decode('ascii')
                CF.sign(e.key,'key_rotated',dict(old_pubkey_b64=encode(e.key),new_pubkey_b64=encode(other)),utc=utc)
                CF.write_pubkey(owner.PUBKEY_PATH,other)
            reopen(e);e.cell[0]+=timedelta(seconds=60)
            before=archive_bytes(e.destination)
            result=run(e)
            no_operation(result)
            assert result.phase=='AUTHORITY_REFUSED' and e.attempts.inspect().state.attempts[0].terminal
            assert archive_bytes(e.destination)==before


def test_checkpoint_uses_inner_actual_completion_before_final_clock_and_original_age():
    for times,code in (((5,1),'OWNER_AUTHORITY_CLOCK_ROLLBACK'),
                       ((0,31),'OWNER_AUTHORITY_OBSERVATION_LATE')):
        with fixture(registered=False) as e:
            actual=e.provider(e.cell[0])
            answers=iter(e.cell[0]+timedelta(seconds=seconds) for seconds in times)
            clock=lambda:next(answers)
            provider=CurrentOwnerAuthority(clock=clock)
            AF.refused(lambda:provider.observe_checkpoint(e.cell[0],
                key_fingerprint=actual.context.owner.fingerprint,code_hash=actual.context.code_hash,
                owner_head=actual.context.owner.head),code)


def test_controller_completion_cannot_precede_actual_checkpoint_completion_watermark():
    with fixture() as e:
        damage(e);actual_finish=R._finish;calls=[]
        def finish(document,authorities,clock,**kwargs):
            calls.append(authorities)
            if len(calls)==2:  # actual completed-copy final phase, after preflight
                latest=authorities[-1]
                original_time=latest.observed_at
                e.cell[0]=original_time+timedelta(seconds=5)
                # A real additional checkpoint observation has a slow completion;
                # no caller-created authority or assignment to provider pins.
                observed=e.provider.observe_checkpoint(original_time,
                    key_fingerprint=latest.context.owner.fingerprint,
                    code_hash=latest.context.code_hash,owner_head=latest.context.owner.head)
                assert observed.observed_at==original_time
                assert e.provider._last==original_time+timedelta(seconds=5)
                e.cell[0]=original_time+timedelta(seconds=1)
            return actual_finish(document,authorities,clock,**kwargs)
        with patch.object(R,'_finish',side_effect=finish):
            result=run(e)
        assert len(calls)==2
        no_operation(result)
        assert result.phase=='AUTHORITY_REFUSED'
        state=e.attempts.inspect().state
        assert state.attempts[0].terminal and len(state.outbox)==1
        assert state.attempts[0].outcomes[0].reason_code=='RECOVERY_CLOCK_ROLLBACK'
        assert state.outbox[0].status=='AUTHORITY_REFUSED'
        assert e.destination.read_raw(e.digest,require_backup=True).manifest_bytes==e.raw_bytes


def test_slow_actual_final_destination_read_and_late_revocation_cannot_record_success():
    for fault in ('late','revoked'):
        with fixture() as e:
            damage(e);actual=B.verify_restored_archive;successful=[]
            def verify_then_change(*args,**kwargs):
                result=actual(*args,**kwargs)
                successful.append(result)
                if fault=='late':
                    e.cell[0]+=timedelta(seconds=31)
                else:
                    revoke(e)
                return result
            with patch.object(B,'verify_restored_archive',side_effect=verify_then_change):
                result=run(e)
            assert len(successful)==1, 'only the final complete destination verification succeeds'
            no_operation(result)
            assert result.phase=='AUTHORITY_REFUSED'
            state=e.attempts.inspect().state
            assert state.attempts[0].terminal and len(state.outbox)==1
            assert state.outbox[0].status=='AUTHORITY_REFUSED'
            assert e.destination.read_raw(e.digest,require_backup=True).manifest_bytes==e.raw_bytes


def test_unknown_or_rollback_clock_records_restrictive_outcome_without_destination_writes():
    for kind in ('unknown','rollback'):
        with fixture() as e:
            damage(e);before=archive_bytes(e.destination)
            last=e.attempts.inspect().state.last_trusted_at
            if kind=='unknown':
                def clock():
                    raise OSError('invented temporary clock adapter failure')
                e.clock=clock
            else:
                e.cell[0]-=timedelta(microseconds=1)
            e.provider=CurrentOwnerAuthority(clock=e.clock)
            result=run(e)
            no_operation(result)
            assert result.phase=='AUTHORITY_REFUSED' and result.observed_at is None
            state=e.attempts.inspect().state
            assert state.last_trusted_at==last and state.attempts[0].terminal
            assert state.attempts[0].entries[0].kind=='PREFLIGHT_REFUSED'
            assert state.attempts[0].outcomes[0].checkpoint is None
            assert archive_bytes(e.destination)==before


def test_expired_original_attestation_is_terminal_without_new_signature_or_copy():
    with fixture() as e:
        damage(e);before=archive_bytes(e.destination)
        e.cell[0]+=timedelta(hours=1)
        result=run(e)
        no_operation(result)
        assert result.phase=='AUTHORITY_REFUSED' and e.attempts.inspect().state.attempts[0].terminal
        assert result.recovery_artifact_digest is None and archive_bytes(e.destination)==before


def test_missing_destination_candidate_after_complete_crash_cannot_reuse_cached_result():
    with fixture(verified=True) as e:
        damage(e);actual=e.attempts.commit
        def lose_result(event,**kwargs):
            if event.kind=='ATTEMPT_OBSERVED':
                raise InjectedCrash()
            return actual(event,**kwargs)
        with patch.object(e.attempts,'commit',side_effect=lose_result):
            crashed(lambda:run(e))
        missing=SF.chunk_path(e.destination,e.payloads['capture_b'],True)
        missing.unlink()
        before=archive_bytes(e.destination)
        reopen(e);e.cell[0]+=timedelta(seconds=60)
        result=run(e)
        no_operation(result)
        assert result.phase=='DESTINATION_UNCONFIRMED'
        assert not missing.exists() and archive_bytes(e.destination)==before
        assert e.attempts.inspect().state.attempts[0].terminal


def test_actual_recorded_research_a_restores_separately_while_independent_b_stays_unchanged():
    with IR.fixture(count=500,carry=True) as original:
        independent=IR.distinct_research(original,store=IR.new_store(original,'independent-b'),name='independent-b')
        IR.register(original);IR.register(independent)
        before_b=archive_bytes(independent.store)
        attempts,args=_attempt_store(original.base)
        e=SimpleNamespace(**(vars(original)|dict(root=original.base,document=original.archive,
            source=B.SignedBackupSource(roots=original.store.roots,limits=original.store.limits),
            destination=IR.new_store(original,'recovered-a'),attempts=attempts,attempt_args=args,
            route=None,incident_id=None)))
        e.route=register_route(e)
        IR.damage_payload(original,original.report.logical_id)
        failure=IR.check(original);e.incident_id=failure.incident_ids[0]
        issued=dict(E._EVALUATED)
        with patch.object(E,'evaluate_capture_json',side_effect=AssertionError('copy does not reissue candidates')):
            result=run(e)
        success(e,result)
        saved=e.destination.read_verified(e.digest,require_backup=True)
        assert saved.manifest_bytes==original.stored.manifest_bytes
        assert dict(saved.files)==dict(original.stored.files) and len(saved.manifest.candidates)==3
        assert E._EVALUATED==issued and archive_bytes(independent.store)==before_b
        assert not IR.check(independent).held
        M.register_target(e.incident_store,e.destination,e.digest,clock=e.clock)
        assert M.check_target(e.incident_store,e.destination,e.digest,clock=e.clock).held
        restored=SimpleNamespace(**(vars(original)|dict(store=e.destination)))
        with patch.object(E,'evaluate_capture_json',side_effect=AssertionError('held before issuance')):
            IR.refused(lambda:IR.select(restored),'INCIDENT_SELECTION_QUARANTINED')
