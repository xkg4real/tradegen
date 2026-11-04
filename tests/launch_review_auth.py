"""Detached review authentication with invented data and disposable synthetic keys."""
from copy import deepcopy
from dataclasses import asdict, replace
from datetime import timedelta
from decimal import Decimal
from functools import lru_cache
import base64
import hashlib
import json
from pathlib import Path

from core.compliance import model as M
from execution_launch.driver import DeploymentWindow, describe_fixed_driver, make_fixed_driver
from execution_launch.profile import profile_contract_digest
from execution_launch.program import ProgramSpec, parameters_json, program_digest
from execution_launch.review_auth import (REVIEW_DOMAIN, ReviewAuthenticationError, ReviewAuthority,
    ReviewVerifiers, parse_review_document, review_body, review_signing_bytes,
    verify_implementation_review, verify_source_review)
from execution_launch.review_request import build_review_request
from execution_launch.runner import ImplementationBinding, StrategyDriver
from execution_launch.strategy import ReviewBinding, assess_strategy, evidence_digest
from tests.launch_profile import context, fixture_profile
from tests.launch_strategy import START, fixture_capture


def invented_provider(_):
    raise AssertionError('authentication tests never fetch a live history frame')


def invented_verifier(*_):
    raise AssertionError('authentication tests never authenticate live history')


@lru_cache(maxsize=1)
def review_fixture():
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    now = START + timedelta(days=250, seconds=1)
    artifact = (Path(__file__).resolve().parents[1] / 'execution_launch/program.py').read_bytes()
    spec = ProgramSpec(schema_version=1, strategy_id='test-strategy', kind='moving_average_trend',
        fast_window=2, slow_window=3, exposure_fraction=Decimal('1'))
    profile = fixture_profile(now)
    profile = replace(profile, strategy_code_sha256=program_digest(spec, artifact),
        policy=replace(profile.policy, initial_equity=Decimal('1000')))
    protocol, _, _, _, _, result, _ = fixture_capture(profile_digest=profile_contract_digest(profile),
        code_digest=profile.strategy_code_sha256, rules=profile.instrument_rules)
    window = DeploymentWindow(deployment_id='invented-deployment', start=now, end=now+timedelta(days=1))
    driver = make_fixed_driver(spec, protocol, profile, window=window, history_provider=invented_provider,
        history_verifier=invented_verifier, program_artifact=artifact)
    request = build_review_request(profile, protocol, result, now=now, program_artifact=artifact,
        parameters_json=parameters_json(spec))
    key = Ed25519PrivateKey.from_private_bytes(bytes(range(32)))
    public = key.public_key().public_bytes_raw()
    fp = 'SHA256:' + hashlib.sha256(public).hexdigest()
    body = review_body(request, asdict(describe_fixed_driver(driver)), deployment_code_hash='c'*64,
        audit_sha256=hashlib.sha256(b'invented test audit, never a genuine owner approval').hexdigest(),
        owner_fingerprint=fp, issued_at=now, expires_at=now+timedelta(hours=1))
    return spec, profile, protocol, result, now, window, driver, key, body


def document(body=None, *, key=None, domain=None):
    *_, expected_key, expected_body = review_fixture()
    body = deepcopy(expected_body if body is None else body)
    signing = review_signing_bytes(body)
    if domain is not None:
        signing = domain + signing[len(REVIEW_DOMAIN):]
    signature = (key or expected_key).sign(signing)
    return json.dumps({'body': body, 'signature_b64': base64.b64encode(signature).decode('ascii')})


def authority(now=None, **changes):
    *_, at, _, _, key, body = review_fixture()
    now = at if now is None else now
    ctx = context(now, owner=M.OwnerState(status='OK', fingerprint=body['owner_fingerprint']), code_hash='c'*64)
    values = dict(context=ctx, public_key_raw=key.public_key().public_bytes_raw(), observed_at=now)
    values.update(changes)
    return ReviewAuthority(**values)


def source_binding():
    *_, body = review_fixture()
    request, b = body['request'], body['request']['bindings']
    return ReviewBinding(protocol_digest=b['protocol_digest'], evidence_digest=b['evidence_digest'],
        registry_digest=b['registry_digest'], inputs_digest=b['inputs_digest'], strategy_id=request['strategy_id'],
        strategy_code_sha256=b['program_digest'], profile_contract_digest=b['profile_contract_digest'],
        rule_terms_digest=b['rule_terms_digest'], capture_end=review_fixture()[2].capture_end)


def implementation_binding():
    b = review_fixture()[-1]['request']['bindings']
    return ImplementationBinding(**{key:b[key] for key in ('program_digest','protocol_digest','evidence_digest',
        'profile_contract_digest','rule_terms_digest')})


def refused(call, code=None):
    try:
        call()
    except ReviewAuthenticationError as exc:
        if code:
            assert str(exc) == code, (str(exc), code)
        return
    raise AssertionError('unverified review accepted')


def source(raw=None, **changes):
    now = review_fixture()[4]
    args = dict(binding=source_binding(), document=document() if raw is None else raw,
        authority=authority(), now=now)
    return verify_source_review(**(args | changes))


def implementation(raw=None, **changes):
    args = dict(binding=implementation_binding(), driver=review_fixture()[6],
        document=document() if raw is None else raw, authority=authority(), now=review_fixture()[4],
        approved_history_provider=invented_provider, approved_history_verifier=invented_verifier)
    return verify_implementation_review(**(args | changes))


def test_genuine_synthetic_signature_roundtrip_qualifies_only_exact_computed_research():
    _, profile, protocol, result, now, _, _, _, _ = review_fixture()
    receipt = source()
    assert receipt.binding_digest == evidence_digest(source_binding())
    verdict = assess_strategy(protocol, result, profile_contract_digest=protocol.profile_contract_digest,
        rule_terms_digest=protocol.rule_terms_digest, strategy_code_sha256=profile.strategy_code_sha256,
        now=now, review_verifier=lambda binding:source(binding=binding))
    assert verdict.research_review_ready
    assert not getattr(verdict, 'execution_ready', False)


def test_registered_fixed_callback_succeeds_but_cloned_or_substituted_callback_refuses():
    driver = review_fixture()[6]
    assert implementation().callback is driver.callback
    for fake in (replace(driver), StrategyDriver(callback=lambda _:None, artifact=driver.artifact,
                                                parameters_json=driver.parameters_json)):
        refused(lambda:implementation(driver=fake), 'REVIEW_FIXED_DRIVER_REQUIRED')


def test_signed_review_cannot_be_replayed_for_different_evidence_or_program():
    binding = source_binding()
    for name in ('protocol_digest','evidence_digest','registry_digest','inputs_digest',
                 'strategy_code_sha256','profile_contract_digest','rule_terms_digest'):
        refused(lambda name=name:source(binding=replace(binding, **{name:'f'*64})), 'REVIEW_SOURCE_BINDING_MISMATCH')
    refused(lambda:implementation(binding=replace(implementation_binding(), evidence_digest='f'*64)),
            'REVIEW_IMPLEMENTATION_BINDING_MISMATCH')


def test_wrong_signature_key_and_owner_log_domain_do_not_authenticate():
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    other = Ed25519PrivateKey.from_private_bytes(bytes(range(1,33)))
    for raw in (document(key=other), document(domain=b'tradegen-owner-log/1\n')):
        refused(lambda:source(raw), 'REVIEW_SIGNATURE_UNVERIFIED')
    value=json.loads(document());value['signature_b64']=base64.b64encode(bytes(64)).decode('ascii')
    refused(lambda:source(json.dumps(value)), 'REVIEW_SIGNATURE_UNVERIFIED')


def test_rotation_expiry_stale_authority_and_changed_signed_deployment_refuse():
    now=review_fixture()[4]
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    public=Ed25519PrivateKey.from_private_bytes(bytes(range(1,33))).public_key().public_bytes_raw()
    ctx=context(now, owner=M.OwnerState(status='OK',fingerprint='SHA256:'+hashlib.sha256(public).hexdigest()))
    refused(lambda:source(authority=authority(context=ctx,public_key_raw=public)), 'REVIEW_CURRENT_KEY_MISMATCH')
    refused(lambda:source(authority=authority(observed_at=now-timedelta(seconds=31))), 'REVIEW_OWNER_AUTHORITY_STALE')
    refused(lambda:source(now=now+timedelta(hours=1),authority=authority(now+timedelta(hours=1))),
            'REVIEW_EXPIRED_OR_FUTURE')
    ctx=authority().context
    refused(lambda:source(authority=authority(context=replace(ctx))), 'REVIEW_OWNER_CONTEXT_INVALID')
    changed=context(now, owner=ctx.owner, code_hash='d'*64)
    refused(lambda:source(authority=authority(context=changed)), 'REVIEW_DEPLOYMENT_CODE_MISMATCH')
    changed=context(now, owner=ctx.owner, code_signed=False)
    refused(lambda:source(authority=authority(context=changed)), 'REVIEW_OWNER_APPROVAL_REQUIRED')


def test_strict_document_rejects_booleans_unknown_fields_duplicates_and_invalid_times():
    value=json.loads(document())
    variants=[]
    for key,val in (('schema_version',True),('approved_checks',[]),('expires_at','2099-01-01T00:00:00.000000+00:00')):
        v=deepcopy(value);v['body'][key]=val;variants.append(json.dumps(v))
    v=deepcopy(value);v['execution_ready']=True;variants.append(json.dumps(v))
    v=deepcopy(value);v['body']['request']['authority']['signature_verified']=True;variants.append(json.dumps(v))
    variants += ['{"body":{},"body":{}}','{"body":NaN}',b'\xff',' '*98305]
    for raw in variants:
        refused(lambda raw=raw:parse_review_document(raw))


def test_deployment_window_and_explicit_trusted_history_selection_are_bound():
    spec,profile,protocol,_,_,window,driver,_,_=review_fixture()
    changed=make_fixed_driver(spec,protocol,profile,window=replace(window,deployment_id='other-deployment'),
        history_provider=invented_provider,history_verifier=invented_verifier,program_artifact=driver.artifact)
    refused(lambda:implementation(driver=changed),'REVIEW_FIXED_DRIVER_MISMATCH')
    substitute=lambda *_:True
    changed=make_fixed_driver(spec,protocol,profile,window=window,history_provider=invented_provider,
        history_verifier=substitute,program_artifact=driver.artifact)
    refused(lambda:implementation(driver=changed),'REVIEW_HISTORY_DEPLOYMENT_MISMATCH')
    refused(lambda:implementation(approved_history_verifier=substitute),'REVIEW_HISTORY_DEPLOYMENT_MISMATCH')


def test_callback_wrapper_refreshes_owner_authority_on_every_verification():
    now=review_fixture()[4];observed=[]
    def current(at):
        observed.append(at)
        return authority() if len(observed)==1 else authority(context=replace(authority().context))
    verifiers=ReviewVerifiers(document(),clock=lambda:now,authority_provider=current,
        approved_history_provider=invented_provider,approved_history_verifier=invented_verifier)
    assert verifiers.source(source_binding()).reviewed_at==now
    refused(lambda:verifiers.implementation(implementation_binding(),review_fixture()[6]),'REVIEW_OWNER_CONTEXT_INVALID')
    assert observed==[now,now]
