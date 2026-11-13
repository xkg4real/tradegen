"""Pure restrictive identities, using invented codec claims and disposable keys.

Source request metrics here are deliberately invented schema fixtures, never
issued evaluator results, owner approvals or trustworthy market observations.
No source/implementation authentication is called. Actual owner/store consumers
are covered separately by launch_research_revocation_auth.
"""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import ast
import base64
import hashlib
import json
from pathlib import Path
from types import MappingProxyType

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from execution_launch import bundle_attestation as A
from execution_launch import managed_behavior as M
from execution_launch import research_revocation as R
from execution_launch import review_auth as V, review_request as Q
from tests import launch_bundle_attestation as AF
from tests.compliance_signer import signer

AT = datetime(2031, 1, 7, tzinfo=timezone.utc)
ARCHIVE = 'research_archive_manifest_attestation'
SOURCE = 'strategy_source_and_fixed_implementation_review'
CARRY = 'strategy_source_and_fixed_carry_implementation_review'
TARGET_DOMAIN = b'tradegen-research-attestation-revocation-target/1\n'


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True,
                      allow_nan=False).encode('ascii')


def stamp(value):
    return value.isoformat(timespec='microseconds')


def codec_source_document(schema=1):
    """Well-formed invented claims; this helper never invokes an evaluator."""
    carry = schema in (3, 4)
    end, asked = AT+timedelta(hours=1), AT+timedelta(hours=1, minutes=1)
    metrics = {name: 0 for name in (Q._CARRY_NUMERIC if carry else Q._METRICS)}
    metrics['family_adjusted_p'] = 0.01
    if carry:
        metrics.update({name:'0' for name in Q._CARRY_AMOUNTS})
        metrics.update(terminal_observed_at=stamp(end), terminal_source_sha256='d'*64)
    request = {
        'schema_version':3 if carry else 1,
        'artifact_kind':'unsigned_strategy_review_request',
        'requested_at':stamp(asked), 'capture_start':stamp(AT), 'capture_end':stamp(end),
        'evaluated_at':stamp(asked), 'review_deadline':stamp(AT+timedelta(hours=24)),
        'study_id':'invented-codec-study', 'strategy_id':'invented-codec-strategy',
        'capture_source_id':'invented-codec-source',
        'evaluator_revision':M.CARRY_EVALUATOR_REVISION if carry else 'forward-paper-v1',
        'source_kind_claim':'prospective_paper_capture',
        'bindings':{name:'a'*64 for name in Q._BINDINGS},
        'computed_summary':{'mathematical_criteria_met':True, 'metrics':metrics},
        'profile_blockers':['SIGNED_CONTEXT_REQUIRED'],
        'assessment_reasons':['STRATEGY_TRUSTED_REVIEW_REQUIRED'],
        'required_checks':[{'id':name, 'reviewed':None, 'evidence_sha256':None} for name in Q._CHECKS],
        'reviewer_id':None, 'review_public_key':None, 'review_signature':None,
        'deployment_code_hash':None, 'authority':{name:False for name in Q._AUTH_FLAGS},
    }
    if carry:
        request.update(behavior_revision=M.BEHAVIOR_REVISION,
                       terminal_accounting=M.TERMINAL_ACCOUNTING,
                       management_behavior_sha256=M.behavior_digest())
    request['request_sha256'] = hashlib.sha256(canonical(request)).hexdigest()
    if schema in (2, 4):
        request = Q.bind_review_family(request, Q.build_family_commitment(plan_digest='b'*64,
            capture_digests={request['study_id']:'c'*64},
            result_digests={request['study_id']:request['bindings']['evidence_digest']}))
    key = Ed25519PrivateKey.from_private_bytes(bytes(range(32)))
    identity = {name:'a'*64 for name in V._IDENTITY if name != 'factory_id'}
    identity['factory_id'] = V.CARRY_FACTORY_ID if carry else V.FACTORY_ID
    body = V.review_body(request, identity, deployment_code_hash='e'*64, audit_sha256='f'*64,
        owner_fingerprint='SHA256:'+hashlib.sha256(key.public_key().public_bytes_raw()).hexdigest(),
        issued_at=asked+timedelta(minutes=1), expires_at=AT+timedelta(hours=2))
    return canonical({'body':body, 'signature_b64':base64.b64encode(
        key.sign(V.review_signing_bytes(body))).decode('ascii')})


def documents():
    archives = [(ARCHIVE, AF.signed(verified=verified)[-1]) for verified in (False, True)]
    return archives+[(CARRY if schema in (3, 4) else SOURCE, codec_source_document(schema))
                     for schema in (1, 2, 3, 4)]


def refused(call, code=None):
    try:
        call()
    except R.ResearchRevocationError as exc:
        if code is not None:
            assert str(exc) == code, (str(exc), code)
        assert str(exc) in {
            'RESEARCH_REVOCATION_DOCUMENT_INVALID', 'RESEARCH_REVOCATION_PURPOSE_INVALID',
            'RESEARCH_REVOCATION_DATA_INVALID', 'RESEARCH_REVOCATION_STATE_INVALID',
        }
        return
    raise AssertionError('invalid restrictive input was accepted')


def independently_refused(call):
    try:
        call()
    except ValueError:
        return
    raise AssertionError('standalone signer accepted invalid restrictive input')


def test_actual_existing_domains_and_all_request_schemas_match_independent_signer():
    domains = {ARCHIVE:b'tradegen-research-archive-attestation/1\n',
               SOURCE:b'tradegen-strategy-review/1\n', CARRY:b'tradegen-strategy-review/2\n'}
    seen = set()
    for purpose, document in documents():
        body = json.loads(document)['body']
        expected = hashlib.sha256(TARGET_DOMAIN+domains[purpose]+canonical(body)).hexdigest()
        actual = R.revocation_target(document, purpose=purpose)
        assert actual == expected == signer._research_revocation_target(document, purpose=purpose)
        assert actual not in seen
        seen.add(actual)
        assert actual != hashlib.sha256(document).hexdigest()
        assert actual != hashlib.sha256(base64.b64decode(json.loads(document)['signature_b64'])).hexdigest()
        if purpose == ARCHIVE:
            assert actual != A.attestation_document_digest(document)


def test_source_whitespace_key_order_and_escaped_spelling_cannot_bypass_restriction():
    for schema in (1, 2, 3, 4):
        purpose = CARRY if schema in (3, 4) else SOURCE
        document = codec_source_document(schema)
        envelope = json.loads(document)
        reordered = {key:envelope[key] for key in reversed(tuple(envelope))}
        variants = (json.dumps(envelope, indent=4).encode('ascii'),
                    json.dumps(reordered, separators=(', ', ': ')).encode('ascii'),
                    document.replace(b'invented-codec-study', b'invented-codec-stud\\u0079'))
        target = R.revocation_target(document, purpose=purpose)
        restricted = frozenset({(purpose,target)})
        for raw in variants:
            assert R.revocation_target(raw, purpose=purpose) == target
            assert signer._research_revocation_target(raw, purpose=purpose) == target
            assert R.target_is_revoked(restricted, purpose=purpose,
                                       target_sha256=R.revocation_target(raw,purpose=purpose))


def test_archive_keeps_exact_byte_codec_instead_of_silently_normalizing_input():
    raw = AF.signed()[-1]
    for changed in (raw+b'\n', json.dumps(json.loads(raw),indent=1).encode('ascii')):
        refused(lambda:R.revocation_target(changed,purpose=ARCHIVE), 'RESEARCH_REVOCATION_DOCUMENT_INVALID')
        independently_refused(lambda:signer._research_revocation_target(changed,purpose=ARCHIVE))


def test_target_preserves_signed_identity_and_cannot_cross_declared_purpose():
    for purpose, document in documents():
        original = R.revocation_target(document,purpose=purpose)
        body = json.loads(document)
        for field,value in (('owner_fingerprint','SHA256:'+'d'*64), ('deployment_code_hash','c'*64)):
            changed = deepcopy(body)
            changed['body'][field] = value
            if field == 'owner_fingerprint':
                changed['body']['reviewer_id'] = 'owner:'+'d'*64
            elif purpose == ARCHIVE:
                request = changed['body']['request']
                request['deployment_code_hash'] = value
                unsigned = {k:v for k,v in request.items() if k != 'request_sha256'}
                request['request_sha256'] = hashlib.sha256(A.REQUEST_DOMAIN+canonical(unsigned)).hexdigest()
            encoded = canonical(changed)
            assert R.revocation_target(encoded,purpose=purpose) != original
            assert R.revocation_target(encoded,purpose=purpose) == signer._research_revocation_target(encoded,purpose=purpose)
        for other in R.PURPOSES-{purpose}:
            refused(lambda other=other:R.revocation_target(document,purpose=other))
            independently_refused(lambda other=other:signer._research_revocation_target(document,purpose=other))


def test_invalid_signature_math_still_has_identity_but_is_never_authenticated():
    for purpose, document in documents():
        changed = json.loads(document)
        changed['signature_b64'] = base64.b64encode(bytes(64)).decode('ascii')
        target = R.revocation_target(document,purpose=purpose)
        assert R.revocation_target(canonical(changed),purpose=purpose) == target
        assert signer._research_revocation_target(canonical(changed),purpose=purpose) == target
    _,_,_,public,_,document = AF.signed()
    changed = json.loads(document);changed['signature_b64'] = base64.b64encode(bytes(64)).decode('ascii')
    try:
        A.verify_attestation_signature(canonical(changed),public_key_raw=public)
    except A.ArchiveAttestationError:
        pass
    else:
        raise AssertionError('identity computation authenticated a forged signature')


def test_duplicate_unknown_nonfinite_and_bad_signature_envelopes_are_rejected():
    for purpose, document in documents():
        envelope = json.loads(document)
        bad_signature = envelope | {'signature_b64':'AA=='}
        variants = (b'{"body":{},'+document[1:], document[:-1]+b',"extra":true}',
                    canonical(bad_signature), b'{"body":NaN}', b'{broken', b'\xff',
                    canonical(envelope | {'public_key':'attacker-selected'}))
        for raw in variants:
            refused(lambda:R.revocation_target(raw,purpose=purpose), 'RESEARCH_REVOCATION_DOCUMENT_INVALID')
            independently_refused(lambda:signer._research_revocation_target(raw,purpose=purpose))


def test_document_types_and_per_purpose_resource_limits_are_retained():
    source = codec_source_document()
    for raw in (source.decode('ascii'), bytearray(source), memoryview(source), {}, None, True):
        refused(lambda:R.revocation_target(raw,purpose=SOURCE), 'RESEARCH_REVOCATION_DOCUMENT_INVALID')
        independently_refused(lambda:signer._research_revocation_target(raw,purpose=SOURCE))
    for purpose, size in ((SOURCE,V.MAX_DOCUMENT_BYTES+1),(CARRY,V.MAX_DOCUMENT_BYTES+1),
                           (ARCHIVE,A.MAX_DOCUMENT_BYTES+1)):
        raw = b' '*size
        refused(lambda:R.revocation_target(raw,purpose=purpose), 'RESEARCH_REVOCATION_DOCUMENT_INVALID')
        independently_refused(lambda:signer._research_revocation_target(raw,purpose=purpose))
    for purpose in ('owner_log', '', None, [], True):
        refused(lambda:R.revocation_target(source,purpose=purpose), 'RESEARCH_REVOCATION_PURPOSE_INVALID')


def test_event_data_exact_schema_matches_standalone_and_returns_detached_copy():
    for purpose, document in documents():
        for reason in R.REASON_CODES:
            data = {'purpose':purpose,'target_sha256':R.revocation_target(document,purpose=purpose),
                    'reason_code':reason}
            snapshot = deepcopy(data)
            copied = R.validate_revocation_data(data)
            assert copied == signer._research_revocation_data(data) == snapshot and copied is not data
            copied['reason_code'] = 'changed outside'
            assert data == snapshot


def test_event_data_refuses_extra_missing_subclasses_and_wrong_types():
    valid = {'purpose':ARCHIVE,'target_sha256':'a'*64,'reason_code':'OWNER_WITHDRAWN'}
    class Derived(dict):
        pass
    bad = [None,True,MappingProxyType(valid),Derived(valid),valid|{'unrevoke':True},
           {key:value for key,value in valid.items() if key != 'reason_code'}]
    for key, values in {'purpose':['',True,[],SOURCE+' '],
                        'target_sha256':['A'*64,'a'*63,'a'*65,True,bytes(32)],
                        'reason_code':['',None,True,[],'AUTO_RESTORE']}.items():
        bad.extend(valid|{key:value} for value in values)
    for data in bad:
        refused(lambda:R.validate_revocation_data(data),'RESEARCH_REVOCATION_DATA_INVALID')
        independently_refused(lambda:signer._research_revocation_data(data))


def test_restrictive_set_is_exact_immutable_and_scope_limited():
    first,second = 'a'*64,'b'*64
    revoked = frozenset({(ARCHIVE,first),(SOURCE,first),(CARRY,second)})
    assert R.validate_revoked_targets(revoked) == revoked
    assert R.target_is_revoked(revoked,purpose=ARCHIVE,target_sha256=first)
    assert R.target_is_revoked(revoked,purpose=SOURCE,target_sha256=first)
    assert not R.target_is_revoked(revoked,purpose=CARRY,target_sha256=first)
    assert not R.target_is_revoked(frozenset(),purpose=ARCHIVE,target_sha256=first)
    assert R.validate_revoked_targets(frozenset({(ARCHIVE,first),(ARCHIVE,first)})) == frozenset({(ARCHIVE,first)})


def test_mutable_or_malformed_restriction_state_never_defaults_to_empty():
    class Derived(frozenset):
        pass
    for state in (None,(),[],{},set(),Derived(),frozenset({'invalid'}),frozenset({()}),
                  frozenset({(ARCHIVE,)}),frozenset({(ARCHIVE,'a'*64,'extra')}),
                  frozenset({(True,'a'*64)}),frozenset({(ARCHIVE,False)}),
                  frozenset({(ARCHIVE,'A'*64)})):
        refused(lambda:R.validate_revoked_targets(state),'RESEARCH_REVOCATION_STATE_INVALID')
        refused(lambda:R.target_is_revoked(state,purpose=ARCHIVE,target_sha256='a'*64),
                'RESEARCH_REVOCATION_STATE_INVALID')
    refused(lambda:R.target_is_revoked(frozenset(),purpose='owner_log',target_sha256='a'*64),
            'RESEARCH_REVOCATION_PURPOSE_INVALID')
    refused(lambda:R.target_is_revoked(frozenset(),purpose=ARCHIVE,target_sha256=True),
            'RESEARCH_REVOCATION_DATA_INVALID')


def test_codec_has_no_owner_file_clock_network_or_signature_authority_dependency():
    tree = ast.parse(Path(R.__file__).read_text())
    imports = [node for node in tree.body if isinstance(node,(ast.Import,ast.ImportFrom))]
    names = {node.module if isinstance(node,ast.ImportFrom) else alias.name
             for node in imports for alias in (node.names if isinstance(node,ast.Import) else [None])}
    assert names == {'__future__','hashlib','re'}
    functions = {node.name for node in tree.body if isinstance(node,ast.FunctionDef)}
    assert functions == {'_need','_purpose','_hash','revocation_target','validate_revocation_data',
                         'validate_revoked_targets','target_is_revoked'}
    forbidden = {'open','load_context','read_pubkey','CurrentOwnerAuthority','sign','verify',
                 'evaluate_capture_json','assess_strategy','clock','now','arm','submit'}
    calls = {node.func.id if isinstance(node.func,ast.Name) else node.func.attr
             for node in ast.walk(tree) if isinstance(node,ast.Call)
             and isinstance(node.func,(ast.Name,ast.Attribute))}
    assert not forbidden & calls
