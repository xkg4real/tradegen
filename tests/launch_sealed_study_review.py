"""Actual sealed source/factory selection over recorded invented market data.

All stores, keys, signed owner logs and independent history heads are temporary.
The real recorder, evaluator, signature verification and registered factories are
used; the invented prices prove integration only, never live profitability.
"""
from contextlib import contextmanager
from dataclasses import asdict, replace
from datetime import timedelta
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from core.compliance import owner
from execution_control.owner_authority import CurrentOwnerAuthority
from execution_control.store import GENESIS
from execution_launch import bundle_attestation as A, bundle_auth as U
from execution_launch import coordinator as C, research_bundle as R
from execution_launch import sealed_study_review as V, strategy as E, study as S
from execution_launch import managed_behavior as M
from execution_launch.baseline_head import BaselineHead
from execution_launch.driver import DeploymentWindow, make_fixed_driver, make_fixed_carry_driver, describe_fixed_driver
from execution_launch.capture_v2 import capture_json_v2
from execution_launch.paper_capture import capture_json
from execution_launch.program import program_digest, parameters_json
from execution_launch.review_auth import review_body
from execution_launch.review_request import build_review_request, build_family_commitment, bind_review_family
from execution_launch.research_revocation import EVENT_KIND, revocation_target
from tests import compliance_fixtures as CF, launch_study as SF, launch_research_bundle as RF
from tests.launch_bundle_auth import document
from tests.launch_carry_coordinator import memoized_pure_inputs
from tests.launch_study_review import signed


def recorded(*, carry=False, count=500):
    template = SF.template(count)
    if carry:
        template = replace(template, schema_version=2, evaluator_revision=M.CARRY_EVALUATOR_REVISION,
            behavior_revision=M.BEHAVIOR_REVISION, terminal_accounting=M.TERMINAL_ACCOUNTING,
            management_behavior_sha256=M.behavior_digest())
    programs = (SF.A, SF.B, SF.program('fixture-ma-200-250', 200, 250)) if count >= 500 else SF.PROGRAMS
    plan = S.build_study_plan(SF.profile(), programs,
        template=template, plan_id='sealed-selection-fixture', asset='BTC', risk_group='crypto-btc')
    source = SF.Driver(plan)
    def clock():
        elapsed = source.clock[0]-source.start
        if elapsed >= timedelta(0) and elapsed % SF.BAR < timedelta(seconds=1):
            source.clock[0] += timedelta(microseconds=1000)
        return source.clock[0]
    outcome = S.run_capture(plan, book_source=source.read, clock=clock, wait_until=source.wait_until,
                            record=source.lines.append)
    assert outcome.complete
    captures = {candidate.protocol.study_id:(capture_json_v2(archive) if carry else capture_json(archive)).encode('ascii')
                for candidate,archive in zip(plan.candidates, outcome.archives)}
    return SimpleNamespace(plan=plan, captures=captures, receipt_log=b''.join(source.lines), outcome=outcome)


def no_history(*_):
    raise AssertionError('source review preparation cannot read live history')


@contextmanager
def fixture(*, carry=False, count=500, provision=True):
    """Shared real-path fixture for CLI. Caller may only patch wall clock for CLI."""
    with memoized_pure_inputs():
        capture = recorded(carry=carry, count=count)
        with patch.object(RF.RF, 'fixture', return_value=capture), RF.fixture(carry=carry) as e:
            home = C.state_root()
            with CF.pubkey_at(home/'owner_pubkey.pem'):
                key = CF.full_home(home)
                code = owner.code_hash(owner.REPO_ROOT)
                finished = RF.finalize(e)
                assert finished.status == 'VERIFIED_UNAPPROVED', finished.reasons
                stored = e.store.read_verified(finished.bundle_digest, require_backup=True)
                raw = e.store.read_raw(finished.input_archive_digest, require_backup=True)
                # Preparation's real evaluation is separate from each actual
                # selection attempt. Its digests are reproducible, not authority.
                prepared = R.evaluate_sealed_study(e.store, finished.bundle_digest)
                now = e.at+timedelta(seconds=2)
                current = SF.profile(instrument_rules=replace(SF.profile().instrument_rules, asof=e.at))
                cell = [now]
                clock = lambda:cell[0]
                provider = CurrentOwnerAuthority(clock=clock)
                window = DeploymentWindow(deployment_id='sealed-selection-fixture', start=now+timedelta(seconds=60),
                    end=now+timedelta(hours=1,seconds=60))
                hroot = e.base/'independent-history'; hroot.mkdir()
                if provision:
                    BaselineHead(root=hroot, name=C.history_head_name(window),
                        chain=C.HistoryChain(root=home, window=window)).initialize_reviewed_head(GENESIS)
                archive_request = A.request_from_manifests(raw.manifest_bytes, stored.manifest_bytes,
                    requested_at=now, expires_at=now+timedelta(hours=1), deployment_code_hash=code)
                archive = document(archive_request, key, issued_at=now)
                results = {row.study_id:row.result for row in prepared.family.rows}
                ranking = S.rank_market_evidence(capture.plan, results, profile=current, now=now)
                eligible = {row.study_id for row in ranking.rows if row.reasons == ('STRATEGY_TRUSTED_REVIEW_REQUIRED',)}
                family = build_family_commitment(plan_digest=S.validate_study_plan(capture.plan),
                    capture_digests=prepared.family.capture_digests,
                    result_digests={identifier:E.evidence_digest(result) for identifier,result in results.items()})
                artifact = S._fixed_file(S.PROGRAM_SOURCE)
                report = next(item for item in stored.manifest.files if item.role == 'report')
                audit_hash = hashlib.sha256(stored.files[report.logical_id]).hexdigest()
                fp = 'SHA256:'+hashlib.sha256(key.public_key().public_bytes_raw()).hexdigest()
                reviews, bodies = {}, {}
                for candidate in capture.plan.candidates:
                    identifier = candidate.protocol.study_id
                    if identifier not in eligible:
                        continue
                    variant = replace(current, strategy_id=candidate.program.strategy_id,
                                      strategy_code_sha256=program_digest(candidate.program, artifact))
                    request = build_review_request(variant, candidate.protocol, results[identifier], now=e.at,
                        program_artifact=artifact, parameters_json=parameters_json(candidate.program))
                    request = bind_review_family(request, family)
                    factory = make_fixed_carry_driver if carry else make_fixed_driver
                    driver = factory(candidate.program, candidate.protocol, variant, window=window,
                        history_provider=no_history, history_verifier=no_history, program_artifact=artifact)
                    body = review_body(request, asdict(describe_fixed_driver(driver)), deployment_code_hash=code,
                        audit_sha256=audit_hash, owner_fingerprint=fp, issued_at=now,
                        expires_at=now+timedelta(minutes=30))
                    bodies[identifier] = body
                    reviews[identifier] = signed(body, key).encode('ascii')
                yield SimpleNamespace(**vars(e), digest=finished.bundle_digest, archive=archive, reviews=reviews,
                    audits={identifier:report.logical_id for identifier in reviews}, profile=current, window=window,
                    history_head_root=hroot, clock=clock, provider=provider, cell=cell, key=key, code=code,
                    home=home, bodies=bodies, report=report, stored=stored, research=prepared)


def select(e, **changes):
    args = dict(archive_attestation=e.archive, source_reviews=e.reviews, audit_logical_ids=e.audits,
        current_profile=e.profile, window=e.window, history_head_root=e.history_head_root,
        clock=e.clock, authority_provider=e.provider)
    return V.authenticate_sealed_study_selection(e.store, e.digest, **(args|changes))


def refused(call, code=None):
    try:
        call()
    except ValueError as exc:
        if code is not None:
            assert str(exc) == code, (str(exc), code)
        return str(exc)
    raise AssertionError('untrusted sealed selection accepted')


def test_actual_fixed_single_evaluation_signatures_history_and_all_candidate_records():
    with fixture() as e:
        assert len(e.reviews) == 2 and len(e.research.family.rows) == 3
        actual = E.evaluate_capture_json
        calls = []
        def evaluate(protocol, *args, **kwargs):
            calls.append(protocol.study_id)
            return actual(protocol, *args, **kwargs)
        with patch.object(E, 'evaluate_capture_json', side_effect=evaluate):
            result = select(e)
        assert len(calls) == 3 and len(set(calls)) == 3
        assert result.selection.status == 'SELECTED' and result.selection.selected_strategy_id == 'fixture-ma-1-2-a'
        assert result.archive_identity_authenticated and result.source_reviews_authenticated
        assert result.selected_implementation_authenticated and result.research_selection_ready
        assert not result.execution_ready and not result.current_operational_use and not result.automatic_recovery_supported
        assert result.authenticated_study_ids == tuple(sorted(e.reviews))
        assert len(result.selection.rows) == 3
        assert e.profile.instrument_rules.asof > SF.profile().instrument_rules.asof
        assert result.evaluated_at == e.at
        assert (e.history_head_root/C.history_head_name(e.window)/'head.json').is_file()


def test_actual_carry_single_evaluation_and_registered_factory_authentication():
    with fixture(carry=True) as e:
        assert len(e.reviews) == 2, {row.study_id:row.result.primary.completed_roundtrips for row in e.research.family.rows}
        actual, calls = E.evaluate_capture_json, []
        def evaluate(protocol,*args,**kwargs):
            calls.append(protocol.study_id)
            return actual(protocol,*args,**kwargs)
        with patch.object(E,'evaluate_capture_json',side_effect=evaluate):
            result = select(e)
        assert len(calls) == 3 and len(set(calls)) == 3
        assert result.research_selection_ready and result.selected_implementation_authenticated
        assert result.selection.selected_strategy_id == 'fixture-ma-1-2-a'
        assert not result.execution_ready and not result.current_operational_use


def test_no_qualified_market_authenticates_archive_without_creating_history():
    with fixture(count=60, provision=False) as e:
        assert not e.reviews
        with patch.object(C, '_compose_driver', side_effect=AssertionError('no selected factory')):
            result = select(e)
        assert result.selection.status == 'NO_QUALIFIED_MARKET' and result.archive_identity_authenticated
        assert not result.source_reviews_authenticated and not result.selected_implementation_authenticated
        assert not result.research_selection_ready and not result.execution_ready
        assert not list(e.history_head_root.iterdir())
        stale = replace(e.profile, instrument_rules=replace(e.profile.instrument_rules, asof=e.cell[0]-timedelta(minutes=6)))
        refused(lambda:select(e,current_profile=stale),'SEALED_SELECTION_PROFILE_NOT_CURRENT')
        wrong = replace(e.profile, policy=replace(e.profile.policy, first_day_loss_budget=e.profile.policy.first_day_loss_budget+1))
        refused(lambda:select(e,current_profile=wrong),'SEALED_SELECTION_CURRENT_CONTRACT_MISMATCH')


def test_all_eligible_reviews_and_exact_sealed_audits_required_before_factory():
    with fixture() as e:
        first = next(iter(e.reviews))
        with patch.object(C,'_compose_driver',side_effect=AssertionError('factory before complete review')):
            refused(lambda:select(e,source_reviews={first:e.reviews[first]},audit_logical_ids={first:e.audits[first]}),
                    'STUDY_REVIEW_ELIGIBLE_FAMILY_INCOMPLETE')
            refused(lambda:select(e,audit_logical_ids=e.audits|{first:'absent'}),'SEALED_SELECTION_AUDIT_FILE_INVALID')
            body = dict(e.bodies[first],audit_sha256='f'*64)
            refused(lambda:select(e,source_reviews=e.reviews|{first:signed(body,e.key).encode()}),
                    'SEALED_SELECTION_AUDIT_HASH_MISMATCH')


def revoke(e, raw, purpose):
    CF.sign(e.key, EVENT_KIND, {'purpose':purpose,
        'target_sha256':revocation_target(raw,purpose=purpose),'reason_code':'OWNER_WITHDRAWN'})


def test_archive_revocation_and_source_revocation_refuse_without_reranking():
    for archive in (True, False):
        with fixture() as e:
            first = next(iter(e.reviews))
            raw = e.archive if archive else e.reviews[first]
            purpose = A.PURPOSE if archive else e.bodies[first]['purpose']
            revoke(e,raw,purpose)
            with patch.object(C,'_compose_driver',side_effect=AssertionError('revoked cannot compose')):
                code = refused(lambda:select(e))
            assert code == ('SEALED_SELECTION_ARCHIVE_REVOKED' if archive else 'REVIEW_ATTESTATION_REVOKED'), code


def test_missing_independent_head_is_not_implicitly_provisioned():
    with fixture(provision=False) as e:
        refused(lambda:select(e))
        assert not list(e.history_head_root.rglob('head.json'))


def test_selected_window_mismatch_refuses_without_fallback():
    with fixture() as e:
        window = replace(e.window,end=e.window.end+timedelta(seconds=300))
        BaselineHead(root=e.history_head_root,name=C.history_head_name(window),
            chain=C.HistoryChain(root=e.home,window=window)).initialize_reviewed_head(GENESIS)
        refused(lambda:select(e,window=window),'REVIEW_FIXED_DRIVER_MISMATCH')


def test_final_graph_and_same_size_history_corruption_refuse():
    for history in (False, True):
        with fixture() as e:
            actual, calls = U._graph, []
            def graph(*args,**kwargs):
                calls.append(1)
                result = actual(*args,**kwargs)
                if len(calls)==2:
                    if not history:
                        return (result[0],result[1],result[2]+(('invented',b'changed'),))
                    journals = list((e.home/'execution').rglob('*.jsonl'))
                    if not journals:
                        journals = [p for p in e.home.rglob('*.jsonl') if 'history' in str(p)]
                    assert len(journals)==1, journals
                    raw = journals[0].read_bytes()
                    journals[0].write_bytes(raw.replace(b'"',b"'",1))
                return result
            with patch.object(U,'_graph',side_effect=graph):
                refused(lambda:select(e))
            assert len(calls)==2


def test_final_crypto_expiry_and_original_observation_age_are_not_refreshed():
    for seconds, code in ((31,'SEALED_SELECTION_OWNER_AUTHORITY_STALE'), (6,'SEALED_SELECTION_EXPIRED_OR_FUTURE')):
        with fixture() as e:
            if seconds == 6:
                e.reviews.update({identifier:signed(dict(body, expires_at=(e.cell[0]+timedelta(seconds=5)).isoformat(timespec='microseconds')),e.key).encode()
                                  for identifier,body in e.bodies.items()})
            actual, calls = V.verify_implementation_review, []
            def slow(*args,**kwargs):
                result=actual(*args,**kwargs)
                calls.append(1)
                if len(calls)==2:
                    e.cell[0]+=timedelta(seconds=seconds)
                return result
            with patch.object(V,'verify_implementation_review',side_effect=slow):
                refused(lambda:select(e),code)
            assert len(calls)==2


def test_fabricated_authority_or_result_never_replaces_actual_sealed_inputs():
    with fixture(count=60) as e:
        observed=e.provider(e.cell[0])
        with patch.object(R,'_evaluate_sealed_study_snapshot',side_effect=AssertionError('invalid input')):
            for provider in (observed,lambda _:observed,True):
                refused(lambda provider=provider:select(e,authority_provider=provider),
                        'SEALED_SELECTION_ACTUAL_PROVIDER_REQUIRED')


def test_actual_backup_object_damage_during_selection_is_not_repaired_or_ignored():
    from tests.launch_research_bundle_store import chunk_path
    with fixture() as e:
        path = chunk_path(e.store,e.stored.files[e.report.logical_id],backup=True)
        before = path.read_bytes()
        actual, calls = U._graph, []
        def graph(*args,**kwargs):
            calls.append(1)
            if len(calls)==2:
                path.write_bytes(before+b'fault injection')
            return actual(*args,**kwargs)
        with patch.object(U,'_graph',side_effect=graph):
            refused(lambda:select(e))
        assert len(calls)==2 and path.read_bytes()==before+b'fault injection'


def test_final_owner_observation_checks_archive_and_nonselected_eligible_revocations():
    for archive in (True,False):
        with fixture() as e:
            identifier = next(identifier for identifier,body in e.bodies.items()
                              if body['request']['strategy_id']=='fixture-ma-1-2-b')
            actual, calls = U._graph, []
            def graph(*args,**kwargs):
                result=actual(*args,**kwargs)
                calls.append(1)
                if len(calls)==2:
                    revoke(e,e.archive if archive else e.reviews[identifier],
                           A.PURPOSE if archive else e.bodies[identifier]['purpose'])
                return result
            with patch.object(U,'_graph',side_effect=graph):
                refused(lambda:select(e),'SEALED_SELECTION_ARCHIVE_REVOKED' if archive else 'REVIEW_ATTESTATION_REVOKED')
            assert len(calls)==2


def test_actual_history_head_rollback_between_bind_and_final_check_is_not_adopted():
    with fixture() as e:
        path=e.history_head_root/C.history_head_name(e.window)/'head.json'
        original=path.read_bytes()
        actual,calls=U._graph,[]
        def graph(*args,**kwargs):
            result=actual(*args,**kwargs)
            calls.append(1)
            if len(calls)==2:
                assert path.read_bytes()!=original
                path.write_bytes(original)
            return result
        with patch.object(U,'_graph',side_effect=graph):
            refused(lambda:select(e))
        assert len(calls)==2 and path.read_bytes()==original


def test_custom_mapping_cannot_evade_bounded_snapshot_or_duplicate_detection():
    from collections.abc import Mapping
    class Unbounded(Mapping):
        def __len__(self):return 0
        def __getitem__(self,key):return b'{}'
        def __iter__(self):
            for i in range(1000):yield 'id'+str(i)
    class Duplicated(Unbounded):
        def items(self):
            yield 'duplicate', b'{}'
            yield 'duplicate', b'{}'
            raise AssertionError('duplicate must stop enumeration')
    with fixture(count=60) as e:
        with patch.object(R,'_evaluate_sealed_study_snapshot',side_effect=AssertionError('bounded admission before evaluation')):
            for mapping in (Unbounded(),Duplicated()):
                refused(lambda mapping=mapping:select(e,source_reviews=mapping),'SEALED_SELECTION_DOCUMENT_FAMILY_INVALID')
