"""Restriction consumers over real temporary owner chains, stores and signatures.

Every authority is loaded by CurrentOwnerAuthority. Evaluations use invented
market observations; keys, homes, documents and stored objects are disposable.
No real account, credential, network, activation or order is accessed.
"""
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import replace
from datetime import timedelta
import base64
import json
from types import SimpleNamespace
from unittest.mock import patch

from core.compliance import owner
from execution_control.owner_authority import CurrentOwnerAuthority
from execution_launch import bundle_attestation as A, bundle_auth as B, review_auth as R
from execution_launch import research_revocation as V, strategy as E
from execution_launch.runner import EvidencePackage, ImplementationBinding
from tests import compliance_fixtures as CF
from tests import launch_review_auth as LEGACY, launch_carry_review as CARRY
from tests import launch_carry_strategy as CS, launch_bundle_auth as ARCHIVE
from tests import launch_study_review as STUDY
from execution_launch import study_review as STUDY_AUTH


def refused(call, code):
    try:
        call()
    except ValueError as exc:
        assert str(exc) == code, (str(exc), code)
        return
    raise AssertionError('revoked or corrupted authority accepted')


def signed_review(body, key, *, pretty=False):
    envelope = {'body':body, 'signature_b64':base64.b64encode(key.sign(R.review_signing_bytes(body))).decode('ascii')}
    return json.dumps(envelope, indent=2 if pretty else None, sort_keys=pretty).encode('ascii')


@contextmanager
def source_fixture(carry=False):
    saved = dict(E._EVALUATED)
    try:
        with CF.temp_home() as home, CF.pubkey_at(home/'owner_pubkey.pem'):
            key = CF.full_home(home)
            if carry:
                # Bypass caches, not validators: the actual evaluator and fixed
                # carry driver issue fresh objects belonging only to this case.
                with patch.object(CARRY, 'fixture_capture', CS.fixture_capture.__wrapped__):
                    sample = CARRY.carry_review_fixture.__wrapped__()
                profile, protocol, result, driver, at = (sample.sample.profile, sample.sample.protocol,
                    sample.sample.result, sample.driver, sample.sample.now)
                original = sample.body
            else:
                _, profile, protocol, result, at, _, driver, _, original = LEGACY.review_fixture.__wrapped__()
            body = R.review_body(original['request'], original['driver_identity'],
                deployment_code_hash=owner.code_hash(owner.REPO_ROOT), audit_sha256=original['audit_sha256'],
                owner_fingerprint=owner.fingerprint(key.public_key().public_bytes_raw()), issued_at=at,
                expires_at=at+timedelta(minutes=30))
            document = signed_review(body,key)
            clock = lambda:at
            provider = CurrentOwnerAuthority(clock=clock)
            verifiers = R.ReviewVerifiers(document, clock=clock, authority_provider=provider,
                approved_history_provider=LEGACY.invented_provider, approved_history_verifier=LEGACY.invented_verifier)
            bindings = body['request']['bindings']
            implementation = ImplementationBinding(**{name:bindings[name] for name in
                ('program_digest','protocol_digest','evidence_digest','profile_contract_digest','rule_terms_digest')})
            yield SimpleNamespace(home=home,key=key,at=at,clock=clock,provider=provider,verifiers=verifiers,
                profile=profile,driver=driver,protocol=protocol,result=result,body=body,document=document,
                source=R._source_binding(body),implementation=implementation,
                evidence=EvidencePackage(protocol=protocol,result=result),
                purpose=body['purpose'],target=V.revocation_target(document,purpose=body['purpose']))
    finally:
        E._EVALUATED.clear(); E._EVALUATED.update(saved)


def revoke(key, document, purpose, *, at, target=None):
    target = V.revocation_target(document,purpose=purpose) if target is None else target
    CF.sign(key,V.EVENT_KIND,{'purpose':purpose,'target_sha256':target,'reason_code':'OWNER_WITHDRAWN'},
            utc=at.strftime('%Y-%m-%dT%H:%M:%SZ'))
    return target


def source_calls(e):
    return (
        lambda:R.verify_source_review(e.source,e.document,authority=e.provider(e.at),now=e.at),
        lambda:R.verify_implementation_review(e.implementation,e.driver,e.document,
            authority=e.provider(e.at),now=e.at,approved_history_provider=LEGACY.invented_provider,
            approved_history_verifier=LEGACY.invented_verifier),
        lambda:e.verifiers.source(e.source),
        lambda:e.verifiers.implementation(e.implementation,e.driver),
        e.verifiers.authenticated_body,
        lambda:e.verifiers.assess_bundle(e.profile,e.evidence,e.driver),
    )


def test_real_legacy_and_carry_revocations_refuse_every_shared_source_and_implementation_route():
    for carry in (False,True):
        with source_fixture(carry) as e:
            for call in source_calls(e):
                call()
            cached = e.verifiers.assess_bundle(e.profile,e.evidence,e.driver)
            assert cached.assessment.research_review_ready and not cached.assessment.execution_ready
            before = e.provider(e.at).context.owner.head
            revoke(e.key,e.document,e.purpose,at=e.at)
            current = e.provider(e.at)
            assert current.context.owner.head[0] == before[0]+1
            assert (e.purpose,e.target) in current.context.owner.revoked_research_attestations
            for call in source_calls(e):
                refused(call,'REVIEW_ATTESTATION_REVOKED')
            # Old display evidence is never accepted as fresh owner authority.
            refused(lambda:R.verify_source_review(e.source,e.document,authority=cached,now=e.at),
                    'REVIEW_OWNER_AUTHORITY_REQUIRED')


def test_future_revocation_is_immediate_duplicate_is_monotone_and_restart_does_not_erase_it():
    with source_fixture() as e:
        future=e.at+timedelta(days=2)
        revoke(e.key,e.document,e.purpose,at=future)
        first=e.provider(e.at)
        revoke(e.key,e.document,e.purpose,at=future+timedelta(seconds=1))
        second=e.provider(e.at)
        assert first.context.owner.revoked_research_attestations == second.context.owner.revoked_research_attestations
        assert second.context.owner.head[0] == first.context.owner.head[0]+1
        refused(e.verifiers.authenticated_body,'REVIEW_ATTESTATION_REVOKED')
        restarted=CurrentOwnerAuthority(clock=e.clock)
        refused(lambda:R.verify_source_review(e.source,e.document,authority=restarted(e.at),now=e.at),
                'REVIEW_ATTESTATION_REVOKED')


def test_other_target_does_not_revoke_current_document_but_cosmetic_json_cannot_evade_same_body():
    with source_fixture() as e:
        revoke(e.key,e.document,e.purpose,at=e.at,target='f'*64)
        assert e.verifiers.authenticated_body() == e.body
        revoke(e.key,e.document,e.purpose,at=e.at+timedelta(seconds=1))
        cosmetically_changed=signed_review(e.body,e.key,pretty=True)
        assert cosmetically_changed != e.document
        assert V.revocation_target(cosmetically_changed,purpose=e.purpose)==e.target
        refused(lambda:R.verify_source_review(e.source,cosmetically_changed,
            authority=e.provider(e.at),now=e.at),'REVIEW_ATTESTATION_REVOKED')


def test_source_missing_or_mutable_revocation_state_is_not_treated_as_empty():
    for invalid in ([], {}, set(), frozenset({('wrong','a'*64)}), None):
        with source_fixture() as e:
            actual=owner.load_context
            def load(*args,**kwargs):
                context=actual(*args,**kwargs)
                object.__setattr__(context.owner,'revoked_research_attestations',invalid)
                return context
            with patch.object(owner,'load_context',side_effect=load):
                refused(e.verifiers.authenticated_body,'REVIEW_REVOCATION_STATE_INVALID')
    with source_fixture() as e:
        actual=owner.load_context
        def missing(*args,**kwargs):
            context=actual(*args,**kwargs)
            object.__delattr__(context.owner,'revoked_research_attestations')
            return context
        with patch.object(owner,'load_context',side_effect=missing):
            refused(e.verifiers.authenticated_body,'REVIEW_REVOCATION_STATE_INVALID')


def test_well_typed_revocation_removal_cannot_preserve_the_original_context_seal():
    with source_fixture() as e:
        revoke(e.key,e.document,e.purpose,at=e.at)
        actual=owner.load_context
        def remove(*args,**kwargs):
            context=actual(*args,**kwargs)
            assert context.owner.revoked_research_attestations
            object.__setattr__(context.owner,'revoked_research_attestations',frozenset())
            return context
        with patch.object(owner,'load_context',side_effect=remove):
            refused(e.verifiers.authenticated_body,'REVIEW_OWNER_CONTEXT_INVALID')


def test_archive_reports_actual_unrevoked_then_revoked_head_without_deleting_originals_or_granting_use():
    with ARCHIVE.fixture() as e:
        first=ARCHIVE.authenticate(e)
        assert first.revocation_status=='NOT_REVOKED_AT_HEAD'
        assert first.revocation_target_sha256 == V.revocation_target(e.document,purpose=A.PURPOSE)
        originals=dict(e.store.read_raw(e.digest).files)
        target=revoke(e.signer.key,e.document,A.PURPOSE,at=e.cell[0])
        second=ARCHIVE.authenticate(e)
        assert second.archive_identity_authenticated and second.revocation_status=='REVOKED'
        assert second.revocation_target_sha256==target
        assert second.revocation_owner_head==e.provider(e.cell[0]).context.owner.head
        assert second.revocation_owner_head[0]>first.revocation_owner_head[0]
        assert 'ARCHIVE_AUTH_ATTESTATION_REVOKED' in second.reasons
        assert not any((second.current_use_eligible,second.source_authenticated,second.research_selection_ready,
            second.execution_ready,second.automatic_recovery_supported,second.signature_backup_verified))
        assert dict(e.store.read_raw(e.digest).files)==originals
        assert A.parse_attestation_document(e.document)['body']['request']==e.request


def test_revocation_arriving_between_graph_work_and_final_owner_observation_is_reported_at_final_head():
    with ARCHIVE.fixture() as e:
        actual=e.store.read_raw
        reads=[]
        def read(*args,**kwargs):
            result=actual(*args,**kwargs)
            reads.append(result)
            if len(reads)==2:
                revoke(e.signer.key,e.document,A.PURPOSE,at=e.cell[0]+timedelta(days=1))
            return result
        with patch.object(e.store,'read_raw',side_effect=read):
            result=ARCHIVE.authenticate(e)
        assert len(reads)==2 and result.archive_identity_authenticated
        assert result.revocation_status=='REVOKED'
        assert result.revocation_owner_head==e.provider(e.cell[0]).context.owner.head
        assert not result.current_use_eligible


def test_archive_other_target_does_not_hide_actual_head_or_create_operational_readiness():
    with ARCHIVE.fixture() as e:
        revoke(e.signer.key,e.document,A.PURPOSE,at=e.cell[0],target='f'*64)
        result=ARCHIVE.authenticate(e)
        assert result.revocation_status=='NOT_REVOKED_AT_HEAD'
        assert result.revocation_owner_head==e.provider(e.cell[0]).context.owner.head
        assert result.revocation_target_sha256 != 'f'*64
        assert 'ARCHIVE_AUTH_NOT_REVOKED_AT_VERIFIED_HEAD' in result.reasons
        assert not result.current_use_eligible and not result.execution_ready


def test_archive_mutable_or_missing_revocation_field_refuses_even_with_real_signature_and_backup():
    for invalid in ([], {}, None, frozenset({(A.PURPOSE,True)})):
        with ARCHIVE.fixture() as e:
            actual=owner.load_context
            def load(*args,**kwargs):
                context=actual(*args,**kwargs)
                object.__setattr__(context.owner,'revoked_research_attestations',invalid)
                return context
            with patch.object(owner,'load_context',side_effect=load):
                refused(lambda:ARCHIVE.authenticate(e),'ARCHIVE_AUTH_REVOCATION_STATE_INVALID')


def test_actual_study_selection_refuses_whole_signed_family_instead_of_dropping_revoked_candidate():
    saved=dict(E._EVALUATED)
    try:
        with CF.temp_home() as home, CF.pubkey_at(home/'owner_pubkey.pem'):
            key=CF.full_home(home)
            f=STUDY.fixture.__wrapped__()
            documents={}
            for identifier,original in f.bodies.items():
                body=R.review_body(original['request'],original['driver_identity'],
                    deployment_code_hash=owner.code_hash(owner.REPO_ROOT),audit_sha256=original['audit_sha256'],
                    owner_fingerprint=owner.fingerprint(key.public_key().public_bytes_raw()),
                    issued_at=R._time(original['issued_at']),expires_at=R._time(original['expires_at']))
                documents[identifier]=signed_review(body,key)
            clock=lambda:f.now
            provider=CurrentOwnerAuthority(clock=clock)
            def select():
                return STUDY_AUTH.authenticate_study_selection(f.env.plan,profile=f.profile,captures=f.captures,
                    reviews=documents,evaluated_at=f.env.now,clock=clock,authority_provider=provider)
            before=select()
            assert before.source_reviews_authenticated and not before.execution_ready
            identifier=sorted(documents)[-1]
            body=R.parse_review_document(documents[identifier])['body']
            revoke(key,documents[identifier],body['purpose'],at=f.now)
            refused(select,'REVIEW_ATTESTATION_REVOKED')
            assert set(documents)==set(f.documents), 'the revoked review must not be silently dropped'
    finally:
        E._EVALUATED.clear(); E._EVALUATED.update(saved)


def test_archive_deleted_instance_revocation_field_cannot_fall_back_to_class_default():
    with ARCHIVE.fixture() as e:
        actual=owner.load_context
        def load(*args,**kwargs):
            context=actual(*args,**kwargs)
            object.__delattr__(context.owner,'revoked_research_attestations')
            return context
        with patch.object(owner,'load_context',side_effect=load):
            refused(lambda:ARCHIVE.authenticate(e),'ARCHIVE_AUTH_REVOCATION_STATE_INVALID')
