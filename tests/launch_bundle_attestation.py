"""Invented archive metadata and fixture signatures; no owner keys or authority."""
from dataclasses import replace
from datetime import timedelta
import base64
import hashlib
import json
from types import MappingProxyType
from unittest.mock import patch

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from execution_launch import bundle_attestation as A
from execution_launch import research_bundle_format as F
from tests.launch_research_bundle_format import AT, fixture, file_record, raw_manifest


def encoded(body):
    return json.dumps(body, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode('ascii')


def clone(body):
    return json.loads(encoded(body))


def rehash(request):
    request = clone(request)
    unsigned = {name:value for name,value in request.items() if name != 'request_sha256'}
    request['request_sha256'] = hashlib.sha256(A.REQUEST_DOMAIN+encoded(unsigned)).hexdigest()
    return request


def refused(call, code=None):
    try:
        call()
    except A.ArchiveAttestationError as exc:
        if code is not None:
            assert str(exc) == code, (str(exc), code)
        return
    raise AssertionError('expected fixed attestation refusal')


def request(*, verified=True):
    env = fixture()
    body = A.request_from_manifests(F.raw_archive_bytes(env.raw),
        F.verified_bundle_bytes(env.verified) if verified else None,
        requested_at=AT+timedelta(minutes=5), expires_at=AT+timedelta(hours=1),
        deployment_code_hash='e'*64)
    return env, body


def signed(*, verified=True):
    env, asked = request(verified=verified)
    key = Ed25519PrivateKey.from_private_bytes(bytes(range(32)))
    public = key.public_key().public_bytes_raw()
    body = A.attestation_body(asked, owner_fingerprint='SHA256:'+hashlib.sha256(public).hexdigest(),
                              issued_at=AT+timedelta(minutes=6))
    document = A.attestation_document_bytes(body, key.sign(A.attestation_signing_bytes(body)))
    return env, asked, key, public, body, document


def test_raw_and_verified_requests_bind_exact_manifests_entire_file_set_and_domain():
    for verified in (False, True):
        env, asked = request(verified=verified)
        restored = A.parse_archive_request(A.archive_request_bytes(asked))
        assert restored == asked and restored is not asked
        assert encoded(restored['raw_manifest']) == F.raw_archive_bytes(env.raw)
        assert (None if restored['verified_manifest'] is None else encoded(restored['verified_manifest'])) == (
            F.verified_bundle_bytes(env.verified) if verified else None)
        expected = env.verified.files if verified else env.raw.files
        assert restored['payload_files'] == [{'logical_id':f.logical_id,'byte_count':f.byte_count,'sha256':f.sha256}
                                             for f in expected]
        assert restored['input_archive_digest'] == F.raw_archive_digest(env.raw)
        assert restored['file_set_sha256'] == hashlib.sha256(A.FILE_SET_DOMAIN+encoded(restored['payload_files'])).hexdigest()
        assert A.archive_request_digest(asked) == rehash(asked)['request_sha256']


def test_fixture_ed25519_signs_and_verifies_exact_archive_only_body():
    _, asked, _, public, body, document = signed()
    assert A.parse_attestation_document(document)['body'] == body
    assert A.verify_attestation_signature(document,public_key_raw=public) == body
    assert A.attestation_signing_bytes(body) == A.SIGNING_DOMAIN+encoded(body)
    assert A.attestation_document_digest(document) == hashlib.sha256(A.DOCUMENT_DOMAIN+document).hexdigest()
    assert body['purpose'] == A.PURPOSE and body['scope'] == A.SCOPE
    assert body['request'] == asked and 'execution_ready' not in body
    assert 'public_key' not in json.loads(document)


def test_incomplete_empty_and_malformed_originals_are_signed_as_raw_without_upgrade():
    originals = (file_record('empty','other_input',b'',name='../NUL'),
                 file_record('broken','incomplete_capture',b'{broken\n',name='partial.incomplete.json'))
    raw = raw_manifest(originals,expected=None,complete=False)
    asked = A.request_from_manifests(F.raw_archive_bytes(raw),None,requested_at=AT,
        expires_at=AT+timedelta(hours=1),deployment_code_hash='e'*64)
    assert asked['bundle_kind'] == 'RAW_ARCHIVED'
    assert asked['raw_manifest']['expected_candidates'] is None
    assert asked['raw_manifest']['inventory_complete'] is False
    A.validate_request_payloads(asked,{'empty':b'','broken':b'{broken\n'})
    assert A.payload_filename('empty') == 'p-empty.bin'
    refused(lambda:A.validate_request_payloads(asked,{'empty':b'','broken':b'{}'}),
            'ARCHIVE_ATTESTATION_PAYLOAD_MISMATCH')
    lied = rehash(asked | {'bundle_kind':'VERIFIED_UNAPPROVED'})
    refused(lambda:A.archive_request_bytes(lied),'ARCHIVE_ATTESTATION_MANIFEST_BINDING_MISMATCH')


def test_empty_inventory_remains_unknown_and_no_missing_file_is_synthesized():
    raw = raw_manifest((),expected=None,complete=False)
    asked = A.request_from_manifests(F.raw_archive_bytes(raw),None,requested_at=AT,
        expires_at=AT+timedelta(seconds=1),deployment_code_hash='e'*64)
    assert asked['payload_files'] == []
    A.validate_request_payloads(asked,{})
    refused(lambda:A.validate_request_payloads(asked,{'missing':b''}),'ARCHIVE_ATTESTATION_PAYLOAD_MISMATCH')


def test_payload_bytes_are_exact_and_must_cover_the_complete_declared_family():
    env, asked = request()
    A.validate_request_payloads(asked,MappingProxyType(env.verified_payloads))
    for supplied in ({k:v for k,v in env.verified_payloads.items() if k != 'f0009'},
                     env.verified_payloads | {'extra':b'{}'},env.verified_payloads | {'f0000':b'{ }'},
                     env.verified_payloads | {'f0000':'{}'},env.verified_payloads | {'f0000':bytearray(b'{}')}):
        refused(lambda:A.validate_request_payloads(asked,supplied),'ARCHIVE_ATTESTATION_PAYLOAD_MISMATCH')


def test_success_only_subset_cannot_be_rehashed_into_an_archive_attestation_request():
    _, asked = request()
    subset = clone(asked)
    verified = subset['verified_manifest']
    verified['candidates'] = verified['candidates'][:1]
    verified['files'] = [file for file in verified['files'] if file['logical_id'] != 'f0009']
    subset['payload_files'] = [file for file in subset['payload_files'] if file['logical_id'] != 'f0009']
    refused(lambda:A.archive_request_bytes(rehash(subset)),'ARCHIVE_ATTESTATION_MANIFEST_INVALID')


def test_rehashed_outer_request_cannot_change_manifest_raw_link_or_file_inventory():
    _, asked = request()
    for changes in ({'bundle_digest':'0'*64},{'input_archive_digest':'0'*64},
                    {'raw_manifest_sha256':'0'*64},{'verified_manifest_sha256':None},
                    {'bundle_kind':'RAW_ARCHIVED'}):
        refused(lambda:A.archive_request_bytes(rehash(asked | changes)),
                'ARCHIVE_ATTESTATION_MANIFEST_BINDING_MISMATCH')
    changed = clone(asked)
    changed['payload_files'][0]['sha256'] = '0'*64
    changed['file_set_sha256'] = A.file_set_digest(changed['payload_files'])
    refused(lambda:A.archive_request_bytes(rehash(changed)),'ARCHIVE_ATTESTATION_FILE_SET_MISMATCH')


def test_request_digest_and_bound_scope_cannot_be_changed_or_reinterpreted():
    _, asked = request()
    refused(lambda:A.archive_request_bytes(asked | {'request_sha256':'0'*64}),
            'ARCHIVE_ATTESTATION_REQUEST_DIGEST_MISMATCH')
    for changes in ({'scope':'strategy_selection'},{'purpose':'strategy_source_and_fixed_implementation_review'},
                    {'artifact_kind':'approved_archive'},{'schema_version':True},{'execution_ready':True}):
        refused(lambda:A.archive_request_bytes(rehash(asked | changes)))


def test_request_expiry_is_explicit_bounded_and_does_not_precede_verified_evaluation():
    env, _ = request()
    raw, verified = F.raw_archive_bytes(env.raw), F.verified_bundle_bytes(env.verified)
    start = AT+timedelta(minutes=5)
    common = dict(raw_manifest=raw,verified_manifest=verified,requested_at=start,deployment_code_hash='e'*64)
    A.request_from_manifests(**common,expires_at=start+timedelta(seconds=A.MAX_VALIDITY_SECONDS))
    for expiry in (start,start-timedelta(microseconds=1),start+timedelta(seconds=A.MAX_VALIDITY_SECONDS,microseconds=1)):
        refused(lambda:A.request_from_manifests(**common,expires_at=expiry),'ARCHIVE_ATTESTATION_VALIDITY_INVALID')
    refused(lambda:A.request_from_manifests(**(common | {'requested_at':AT}),expires_at=start),
            'ARCHIVE_ATTESTATION_VALIDITY_INVALID')
    refused(lambda:A.request_from_manifests(**(common | {'requested_at':start.replace(tzinfo=None)}),
                                          expires_at=start+timedelta(hours=1)),
            'ARCHIVE_ATTESTATION_TIME_INVALID')


def test_body_issued_time_is_fixed_within_request_window_and_expiry_cannot_be_extended():
    _, asked, _, _, body, _ = signed()
    fp = body['owner_fingerprint']
    A.attestation_body(asked,owner_fingerprint=fp,issued_at=AT+timedelta(minutes=5))
    for issued in (AT,AT+timedelta(hours=1),AT+timedelta(hours=2)):
        refused(lambda:A.attestation_body(asked,owner_fingerprint=fp,issued_at=issued),
                'ARCHIVE_ATTESTATION_VALIDITY_INVALID')
    refused(lambda:A.attestation_signing_bytes(body | {'expires_at':'2026-01-02T00:00:00.000000+00:00'}),
            'ARCHIVE_ATTESTATION_VALIDITY_INVALID')


def test_body_code_identity_and_full_checklist_are_required():
    _, _, _, _, body, _ = signed()
    for changes,code in (({'deployment_code_hash':'0'*64},'ARCHIVE_ATTESTATION_CODE_BINDING_INVALID'),
                         ({'owner_fingerprint':'SHA256:'+'0'*64},'ARCHIVE_ATTESTATION_SIGNER_INVALID'),
                         ({'reviewer_id':'other'},'ARCHIVE_ATTESTATION_SIGNER_INVALID'),
                         ({'approved_checks':list(A.APPROVED_CHECKS)[:-1]},'ARCHIVE_ATTESTATION_CHECKLIST_INVALID'),
                         ({'approved_checks':list(reversed(A.APPROVED_CHECKS))},'ARCHIVE_ATTESTATION_CHECKLIST_INVALID')):
        refused(lambda:A.attestation_signing_bytes(body | changes),code)


def test_old_domains_and_valid_signature_of_other_body_do_not_verify():
    _, _, key, public, body, _ = signed()
    for domain in (b'tradegen-owner-log/1\n',b'tradegen-strategy-review/1\n',b'tradegen-strategy-review/2\n'):
        raw = A.attestation_document_bytes(body,key.sign(domain+encoded(body)))
        refused(lambda:A.verify_attestation_signature(raw,public_key_raw=public),
                'ARCHIVE_ATTESTATION_SIGNATURE_UNVERIFIED')
    changed = clone(body)
    changed['issued_at'] = '2026-01-01T00:07:00.000000+00:00'
    raw = A.attestation_document_bytes(changed,key.sign(A.attestation_signing_bytes(body)))
    refused(lambda:A.verify_attestation_signature(raw,public_key_raw=public),
            'ARCHIVE_ATTESTATION_SIGNATURE_UNVERIFIED')


def test_signature_replay_to_another_archive_or_code_is_refused():
    _, asked, key, public, body, _ = signed()
    for changed_request in (rehash(asked | {'deployment_code_hash':'a'*64}),request(verified=False)[1]):
        other_body = A.attestation_body(changed_request,owner_fingerprint=body['owner_fingerprint'],
                                       issued_at=AT+timedelta(minutes=6))
        raw = A.attestation_document_bytes(other_body,key.sign(A.attestation_signing_bytes(body)))
        refused(lambda:A.verify_attestation_signature(raw,public_key_raw=public),
                'ARCHIVE_ATTESTATION_SIGNATURE_UNVERIFIED')


def test_embedded_attacker_key_is_not_a_trust_input_and_supplied_key_must_match_identity():
    _, _, _, public, _, document = signed()
    envelope = json.loads(document)
    other = Ed25519PrivateKey.from_private_bytes(bytes(reversed(range(32)))).public_key().public_bytes_raw()
    refused(lambda:A.verify_attestation_signature(document,public_key_raw=other),
            'ARCHIVE_ATTESTATION_KEY_MISMATCH')
    refused(lambda:A.parse_attestation_document(encoded(envelope | {'public_key_b64':base64.b64encode(other).decode()})))
    for value in (None,b'',public+b'x',bytearray(public),'0'*64):
        refused(lambda:A.verify_attestation_signature(document,public_key_raw=value),
                'ARCHIVE_ATTESTATION_PUBLIC_KEY_INVALID')


def test_structural_signature_shape_is_separate_from_cryptographic_validation():
    _, _, _, public, body, _ = signed()
    document = A.attestation_document_bytes(body,b'\0'*64)
    assert A.parse_attestation_document(document)['body'] == body
    refused(lambda:A.verify_attestation_signature(document,public_key_raw=public),
            'ARCHIVE_ATTESTATION_SIGNATURE_UNVERIFIED')
    for signature in (b'',b'x'*63,b'x'*65,bytearray(b'x'*64)):
        refused(lambda:A.attestation_document_bytes(body,signature),'ARCHIVE_ATTESTATION_SIGNATURE_INVALID')
    for spelling in ('A'*87,'A'*89,'!'*88,base64.b64encode(b'x'*65).decode()):
        refused(lambda:A.parse_attestation_document(encoded({'body':body,'signature_b64':spelling})),
                'ARCHIVE_ATTESTATION_SIGNATURE_INVALID')


def test_pure_signature_check_does_not_use_current_clock_owner_files_or_grant_current_use():
    _, _, _, public, body, document = signed()
    # Deliberately historical timestamps: this function checks signature math,
    # while actual bundle_auth separately handles current owner/code/time.
    with patch('builtins.open',side_effect=AssertionError('no file access')):
        restored = A.verify_attestation_signature(document,public_key_raw=public)
    assert restored == body
    assert all(name not in restored for name in ('current_use_eligible','revoked','source_authenticated',
                                                 'execution_ready','automatic_recovery_supported'))


def test_returned_bodies_are_detached_and_mutation_cannot_change_signed_originals():
    _, asked, _, _, body, document = signed()
    before = A.archive_request_bytes(asked)
    body['request']['raw_manifest']['inventory_complete'] = False
    assert A.archive_request_bytes(asked) == before
    parsed = A.parse_attestation_document(document)
    parsed['body']['approved_checks'].clear()
    assert A.parse_attestation_document(document)['body']['approved_checks'] == list(A.APPROVED_CHECKS)


def test_file_set_types_generated_names_order_and_empty_hash_are_strict():
    _, asked = request()
    files = asked['payload_files']
    for rows in (list(reversed(files)),files+[files[-1]],
                 [files[0] | {'byte_count':True}]+files[1:],
                 [files[0] | {'other':1}]+files[1:]):
        refused(lambda:A.file_set_digest(rows),'ARCHIVE_ATTESTATION_FILE_SET_INVALID')
    refused(lambda:A.file_set_digest([{'logical_id':'empty','byte_count':0,'sha256':'0'*64}]),
            'ARCHIVE_ATTESTATION_FILE_SET_INVALID')
    for name in ('../escape','/absolute','C:drive','a/b','a.b','A','a\\b',''):
        refused(lambda:A.payload_filename(name),'ARCHIVE_ATTESTATION_FILE_SET_INVALID')


def test_windows_device_logical_ids_remain_valid_with_unambiguous_prefixed_filenames():
    identifiers = ('aux','com1','com9','con','lpt1','lpt9','nul','prn','p-con')
    files = tuple(file_record(name,'other_input',b'original',name=name+'.txt') for name in identifiers)
    raw = raw_manifest(files,expected=None,complete=False)
    asked = A.request_from_manifests(F.raw_archive_bytes(raw),None,requested_at=AT,
        expires_at=AT+timedelta(hours=1),deployment_code_hash='e'*64)
    A.validate_request_payloads(asked,{name:b'original' for name in identifiers})
    generated = [A.payload_filename(name) for name in identifiers]
    assert len(set(generated)) == len(identifiers)
    assert generated == ['p-'+name+'.bin' for name in identifiers]
    assert not set(generated) & {name+'.bin' for name in ('aux','com1','com9','con','lpt1','lpt9','nul','prn')}
    # A prefix-looking original is a different ID; no stripping or aliasing.
    assert A.payload_filename('p-con') != A.payload_filename('con')


def test_request_and_document_parsers_reject_duplicate_keys_extra_fields_and_numbers():
    _, asked, _, _, _, document = signed()
    raw = A.archive_request_bytes(asked)
    refused(lambda:A.parse_archive_request(b'{"schema_version":1,'+raw[1:]))
    refused(lambda:A.parse_attestation_document(b'{"signature_b64":"x",'+document[1:]))
    for token in (b'true',b'1.0',b'1e0',b'NaN',b'Infinity'):
        refused(lambda:A.parse_archive_request(raw.replace(b'"schema_version":1',b'"schema_version":'+token,1)))
    refused(lambda:A.parse_archive_request(encoded(asked | {'signature_b64':'A'*88})))
    refused(lambda:A.parse_attestation_document(encoded(json.loads(document) | {'approved':True})))


def test_envelope_format_is_exact_and_has_no_newline_or_alternate_time_spelling():
    _, asked, _, _, _, document = signed()
    for raw in (document+b'\n',b' '+document,json.dumps(json.loads(document),indent=2).encode('ascii')):
        refused(lambda:A.parse_attestation_document(raw))
    altered = rehash(asked | {'requested_at':'2026-01-01T00:05:00Z'})
    refused(lambda:A.archive_request_bytes(altered),'ARCHIVE_ATTESTATION_TIME_INVALID')


def test_byte_depth_node_integer_and_cyclic_input_limits_fail_before_use():
    refused(lambda:A.parse_archive_request(b' '*(A.MAX_REQUEST_BYTES+1)),
            'ARCHIVE_ATTESTATION_RESOURCE_LIMIT')
    refused(lambda:A.parse_attestation_document(b' '*(A.MAX_DOCUMENT_BYTES+1)),
            'ARCHIVE_ATTESTATION_RESOURCE_LIMIT')
    refused(lambda:A.parse_archive_request(b'['*17+b'0'+b']'*17),'ARCHIVE_ATTESTATION_RESOURCE_LIMIT')
    refused(lambda:A.parse_archive_request(b'['+b'0,'*500001+b'0]'),'ARCHIVE_ATTESTATION_RESOURCE_LIMIT')
    refused(lambda:A.parse_archive_request(b'{"a":12345678901234567}'))
    cyclic = {}; cyclic['a'] = cyclic
    refused(lambda:A.archive_request_bytes(cyclic),'ARCHIVE_ATTESTATION_RESOURCE_LIMIT')


def test_manifest_admission_limit_is_not_relabelled_as_evidence_corruption():
    oversized = b' '*(F.DEFAULT_LIMITS.max_manifest_bytes+1)
    refused(lambda:A.request_from_manifests(oversized,None,requested_at=AT,
        expires_at=AT+timedelta(hours=1),deployment_code_hash='e'*64),
        'ARCHIVE_ATTESTATION_RESOURCE_LIMIT')


def test_appending_unknown_inventory_to_raw_changes_signature_target_without_hiding_it():
    env, asked = request(verified=False)
    missing = F.InputObservation(observation_id='z9999',original_name='unreadable.capture.json',
        source_name=None,role='capture',study_id=None,required=True,status='REFUSED',logical_id=None)
    raw = replace(env.raw,inventory_complete=False,expected_candidates=None,
                  observed_inputs=env.raw.observed_inputs+(missing,))
    changed = A.request_from_manifests(F.raw_archive_bytes(raw),None,requested_at=AT+timedelta(minutes=5),
        expires_at=AT+timedelta(hours=1),deployment_code_hash='e'*64)
    assert changed['request_sha256'] != asked['request_sha256']
    assert changed['raw_manifest']['observed_inputs'][-1]['status'] == 'REFUSED'
    assert changed['payload_files'] == asked['payload_files']  # no fabricated missing bytes


def test_b1a_manifest_domains_and_bytes_are_not_rewritten_by_requests_or_signatures():
    env = fixture()
    raw_before, verified_before = F.raw_archive_bytes(env.raw), F.verified_bundle_bytes(env.verified)
    asked = A.request_from_manifests(raw_before,verified_before,requested_at=AT+timedelta(minutes=5),
        expires_at=AT+timedelta(hours=1),deployment_code_hash='e'*64)
    assert F.raw_archive_bytes(env.raw) == raw_before and F.verified_bundle_bytes(env.verified) == verified_before
    assert asked['raw_manifest_sha256'] == hashlib.sha256(raw_before).hexdigest()
    assert asked['bundle_digest'] == F.verified_bundle_digest(env.verified)
    assert asked['request_sha256'] not in (asked['bundle_digest'],asked['input_archive_digest'])
