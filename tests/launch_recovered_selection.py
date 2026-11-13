"""Actual restored research selection fixtures; invented prices, disposable keys.

The recorder/evaluator/reviews, recovery controller, independent stores and owner
loader are real. Neither synthetic prices nor local archival identity establishes
production source authenticity. No real API, account, key or order is used.
"""
from contextlib import contextmanager
from types import SimpleNamespace
import shutil
from unittest.mock import patch

from execution_launch import bundle_recovery as B
from execution_launch import research_recovery as R
from execution_launch import research_incident_monitor as M
from execution_launch import recovered_study_selection as V
from tests import launch_research_incident_integration as IR
from tests import launch_research_recovery_integration as RR


@contextmanager
def fixture(*, count=500, carry=False, restored=True, source_removed=False):
    """Actual recorded family→registered route→source damage→exact restoration."""
    with IR.fixture(count=count, carry=carry) as original:
        attempts, attempt_args = RR._attempt_store(original.base)
        destination = IR.new_store(original, 'recovered-destination')
        e = SimpleNamespace(**vars(original), attempts=attempts, attempt_args=attempt_args,
            destination=destination, document=original.archive,
            source=B.SignedBackupSource(roots=original.store.roots, limits=original.store.limits),
            route=None, incident_id=None, recovery=None)
        M.register_target(e.incident_store, e.store, e.digest, clock=e.clock)
        e.route = RR.register_route(e)
        RR.damage(e)
        if restored:
            e.recovery = RR.run(e)
            RR.success(e, e.recovery)
        if source_removed:
            assert restored
            shutil.rmtree(e.store.roots.sealed_root)
            shutil.rmtree(e.store.roots.backup_root)
        yield e


def select(e, **changes):
    args = dict(incident_store=e.incident_store, attempts=e.attempts,
        route_id=e.route.route_id, incident_id=e.incident_id,
        archive_attestation=e.archive, source_reviews=e.reviews, audit_logical_ids=e.audits,
        current_profile=e.profile, window=e.window, history_head_root=e.history_head_root,
        clock=e.clock, authority_provider=e.provider)
    return V.authenticate_recovered_study_selection(e.destination, e.digest, **(args | changes))


def refused(call, code=None):
    try:
        call()
    except ValueError as exc:
        if code is not None:
            assert str(exc) == code, (str(exc), code)
        return str(exc)
    raise AssertionError('recovered selection accepted unverified input')


def releases(e):
    from execution_launch import research_incidents as I
    return I.research_route_releases(e.incident_store.inspect().state,
        route_id=e.route.route_id, incident_id=e.incident_id,
        limits=e.incident_store.limits.format_limits)


def test_exact_actual_inputs_unknown_route_and_nonterminal_attempt_refuse_before_evaluation():
    with fixture(count=60,restored=False) as e:
        with patch.object(V.S,'_authenticate_sealed_study_selection',side_effect=AssertionError('unexpected evaluation')):
            for changes in ({'authority_provider':lambda _:True}, {'attempts':object()},
                            {'incident_store':object()}, {'archive_attestation':'text'},
                            {'route_id':True}, {'incident_id':'F'*64}):
                refused(lambda:select(e,**changes),'RECOVERED_SELECTION_ACTUAL_INPUT_REQUIRED')
            refused(lambda:select(e,route_id='f'*64),'RECOVERED_SELECTION_ROUTE_REQUIRED')
            refused(lambda:select(e),'RECOVERED_SELECTION_RESTORED_ATTEMPT_REQUIRED')
        assert not releases(e)


def test_restored_raw_failure_archive_does_not_become_a_verified_research_target():
    with RR.fixture() as e:
        RR.damage(e); RR.success(e,RR.run(e))
        args=dict(incident_store=e.incident_store,attempts=e.attempts,route_id=e.route.route_id,
            incident_id=e.incident_id,archive_attestation=e.document,source_reviews={},audit_logical_ids={},
            current_profile=None,window=None,history_head_root=e.base,
            clock=e.clock,authority_provider=e.provider)
        with patch.object(V.S,'_authenticate_sealed_study_selection',side_effect=AssertionError('unexpected evaluation')):
            refused(lambda:V.authenticate_recovered_study_selection(e.destination,e.digest,**args),
                    'RECOVERED_SELECTION_VERIFIED_TARGET_REQUIRED')


def test_different_destination_and_document_do_not_change_or_release_the_original_incident():
    with fixture(count=60) as e:
        before=e.incident_store.inspect()
        other=IR.new_store(e,'wrong-destination')
        original=e.destination
        e.destination=other
        refused(lambda:select(e),'RECOVERED_SELECTION_DESTINATION_CHANGED')
        e.destination=original
        refused(lambda:select(e,archive_attestation=e.archive+b'not-json'))
        assert e.incident_store.inspect()==before and not releases(e)


def test_benign_destination_catalog_extension_keeps_exact_original_success_prefix():
    from tests import launch_research_bundle_store as SF
    with fixture(count=60,source_removed=True) as e:
        before=e.recovery
        _,raw,payloads=SF.raw_archive(e.destination,{'other':b'unrelated immutable input'},run='unrelated-archive')
        e.destination.archive_raw(raw,payloads)
        result=select(e)
        assert result.selection_assessment.selection.status=='NO_QUALIFIED_MARKET'
        assert result.release_record_id is None and not result.research_selection_ready
        assert result.outcome_event_id==before.outcome_event_id
        assert not e.store.roots.sealed_root.exists()


def test_additional_actual_incident_blocks_before_family_evaluation_and_preserves_all_holds():
    from execution_launch import research_incidents as I
    with fixture(count=60) as e:
        registration=M.register_target(e.incident_store,e.destination,e.digest,clock=e.clock)
        snapshot=e.incident_store.inspect()
        event=M._failure_event(registration,observed=e.cell[0],scope='TARGET',failed_objects=(),
            category='READ_UNAVAILABLE',reason='SECOND_ACTUAL_FIXTURE_INCIDENT')
        e.incident_store.commit(event,expected_head=snapshot.head)
        with patch.object(V.S,'_authenticate_sealed_study_selection',side_effect=AssertionError('unexpected evaluation')):
            refused(lambda:select(e),'RECOVERED_SELECTION_ADDITIONAL_INCIDENT')
        final=e.incident_store.inspect()
        assert len(I.blocked_incidents(final.state,registration))==2 and not releases(e)


def test_exact_release_reuse_keeps_original_row_and_historical_observation_without_new_signature():
    from datetime import timedelta
    from execution_control.owner_authority import CurrentOwnerAuthority
    with fixture(source_removed=True) as e:
        first=select(e)
        original,=releases(e)
        first_head=e.incident_store.inspect().head
        e.cell[0]+=timedelta(seconds=1)
        e.provider=CurrentOwnerAuthority(clock=e.clock)
        second=select(e)
        assert second.release_record_id==first.release_record_id==original.event_id
        assert releases(e)==(original,) and e.incident_store.inspect().head==first_head
        assert second.selection_assessment.verified_at>first.selection_assessment.verified_at
        assert M.check_target(e.incident_store,e.destination,e.digest,clock=e.clock).held
        observed=SimpleNamespace(**(vars(e)|{'store':e.destination}))
        refused(lambda:IR.select(observed),'INCIDENT_SELECTION_QUARANTINED')


def test_record_write_failure_retains_general_hold_and_latches_the_original_namespace():
    from execution_launch import research_incident_store as IS
    with fixture() as e:
        actual=e.incident_store.commit
        def failure(event,**kwargs):
            if event.kind=='RESEARCH_ROUTE_RELEASE':
                raise IS.IncidentStoreError('INCIDENT_STORE_NO_SPACE')
            return actual(event,**kwargs)
        with patch.object(e.incident_store,'commit',side_effect=failure):
            refused(lambda:select(e),'RECOVERED_SELECTION_RECORD_UNCONFIRMED')
        assert not releases(e)
        refused(lambda:select(e),'INCIDENT_RECORD_UNCONFIRMED')


def test_confirmed_release_response_loss_is_not_reported_as_success_or_silently_retried():
    from execution_launch import research_incident_store as IS
    with fixture() as e:
        actual=e.incident_store.commit
        def lost(event,**kwargs):
            result=actual(event,**kwargs)
            if event.kind=='RESEARCH_ROUTE_RELEASE':
                raise IS.IncidentStoreError('INCIDENT_STORE_RESPONSE_LOST')
            return result
        with patch.object(e.incident_store,'commit',side_effect=lost):
            refused(lambda:select(e),'RECOVERED_SELECTION_RECORD_UNCONFIRMED')
        assert len(releases(e))==1
        # Reopening actual stores in the same process must not erase its latch;
        # this is deliberately not claimed as a new OS process.
        e.incident_store=e.reopen_incidents()
        refused(lambda:select(e),'INCIDENT_RECORD_UNCONFIRMED')


def test_forged_release_claimed_prior_head_is_refused_despite_actual_current_research_validation():
    from execution_launch import research_incidents as I
    with fixture() as e:
        actual=e.incident_store.commit
        captured=[]
        def substitute(event,**kwargs):
            if event.kind=='RESEARCH_ROUTE_RELEASE':
                payload=I._plain(event.payload)
                payload['incident_head']=[1,'f'*64]
                event=I.make_event('RESEARCH_ROUTE_RELEASE',payload,observed_at=event.observed_at)
                captured.append(event)
            return actual(event,**kwargs)
        with patch.object(e.incident_store,'commit',side_effect=substitute):
            refused(lambda:select(e),'RECOVERED_SELECTION_RELEASE_BINDING_CHANGED')
        assert releases(e)==tuple(captured) and len(captured)==1
        refused(lambda:select(e),'RECOVERED_SELECTION_RELEASE_BINDING_CHANGED')


def test_forged_historical_attempt_head_cannot_be_reused_as_an_observed_recovery_fact():
    from execution_launch import research_incidents as I
    with fixture() as e:
        actual=e.incident_store.commit
        def substitute(event,**kwargs):
            if event.kind=='RESEARCH_ROUTE_RELEASE':
                payload=I._plain(event.payload);payload['attempt_head']=[1,'f'*64]
                event=I.make_event('RESEARCH_ROUTE_RELEASE',payload,observed_at=event.observed_at)
            return actual(event,**kwargs)
        with patch.object(e.incident_store,'commit',side_effect=substitute):
            refused(lambda:select(e),'RECOVERED_SELECTION_RELEASE_BINDING_CHANGED')
        assert len(releases(e))==1
        refused(lambda:select(e),'RECOVERED_SELECTION_RELEASE_BINDING_CHANGED')


def test_false_success_outcome_destination_prefix_cannot_be_replaced_by_current_head():
    from execution_launch import research_recovery_attempts as F, research_incidents as I
    with fixture(count=60,restored=False) as e:
        actual=e.attempts.commit
        def substitute(event,**kwargs):
            if event.kind=='ATTEMPT_OBSERVED' and event.payload['status']=='EXACT_ARCHIVE_RESTORED':
                payload=I._plain(event.payload);payload['destination_head']=[1,'f'*64]
                event=F.make_event(event.kind,payload,observed_at=event.observed_at)
            return actual(event,**kwargs)
        with patch.object(e.attempts,'commit',side_effect=substitute):
            e.recovery=RR.run(e)
        assert e.recovery.phase=='EXACT_ARCHIVE_RESTORED'
        with patch.object(V.S,'_authenticate_sealed_study_selection',side_effect=AssertionError('unexpected evaluation')):
            refused(lambda:select(e),'RECOVERED_SELECTION_DESTINATION_CHANGED')
        assert not releases(e)


def test_forged_release_historical_destination_or_owner_prefix_cannot_be_reused():
    from execution_launch import research_incidents as I
    for field in ('destination_head','owner_checkpoint'):
        with fixture() as e:
            actual=e.incident_store.commit
            def substitute(event,**kwargs):
                if event.kind=='RESEARCH_ROUTE_RELEASE':
                    payload=I._plain(event.payload)
                    if field=='destination_head':
                        payload[field]=[1,'f'*64]
                    else:
                        payload[field]['owner_head']=[1,'f'*64]
                    event=I.make_event(event.kind,payload,observed_at=event.observed_at)
                return actual(event,**kwargs)
            with patch.object(e.incident_store,'commit',side_effect=substitute):
                refused(lambda:select(e),'RECOVERED_SELECTION_RELEASE_BINDING_CHANGED')
            assert len(releases(e))==1
            refused(lambda:select(e))
            assert M.check_target(e.incident_store,e.destination,e.digest,clock=e.clock).held


def test_fresh_provider_cannot_ignore_recovery_checkpoint_log_truncation_key_or_code_changes():
    import base64
    from core.compliance import owner
    from execution_control.owner_authority import CurrentOwnerAuthority
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from tests import compliance_fixtures as CF
    for fault in ('truncated','key','code'):
        with fixture(count=60,restored=False) as e:
            before=owner.log_path().read_bytes()
            CF.sign(e.key,'age_of_majority',{'birth_date':'2000-01-01','evidence':'fixture recovery checkpoint'},
                    utc=e.cell[0].strftime('%Y-%m-%dT%H:%M:%SZ'))
            e.recovery=RR.run(e)
            assert e.recovery.phase=='EXACT_ARCHIVE_RESTORED'
            e.provider=CurrentOwnerAuthority(clock=e.clock)
            if fault=='truncated':
                owner.log_path().write_bytes(before)
            elif fault=='key':
                other=Ed25519PrivateKey.from_private_bytes(bytes(range(1,33)))
                encode=lambda key:base64.b64encode(key.public_key().public_bytes_raw()).decode('ascii')
                CF.sign(e.key,'key_rotated',{'old_pubkey_b64':encode(e.key),'new_pubkey_b64':encode(other)},
                        utc=e.cell[0].strftime('%Y-%m-%dT%H:%M:%SZ'))
                CF.write_pubkey(owner.PUBKEY_PATH,other)
            else:
                alternative=e.base/'changed-code';alternative.mkdir()
                (alternative/'module.py').write_text('VALUE = 17\n',encoding='utf-8')
                with patch.object(owner,'REPO_ROOT',alternative):
                    refused(lambda:select(e))
                assert not releases(e)
                continue
            refused(lambda:select(e))
            assert not releases(e)
