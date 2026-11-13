"""Invented archival metadata and original bytes, not evaluated or approved research."""
from dataclasses import asdict, replace
from datetime import datetime, timedelta, timezone
import hashlib
import json
from types import MappingProxyType, SimpleNamespace

from execution_launch import research_bundle_format as F
from execution_launch.evidence_objects import ObjectLimits, preview_payload


OBJECT_LIMITS = ObjectLimits(chunk_bytes=65536, max_payload_bytes=64*1024*1024,
                            max_chunks=1024, max_manifest_bytes=1024*1024)
AT = datetime(2026, 1, 1, tzinfo=timezone.utc)


def encoded(body):
    return json.dumps(body, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode('ascii')


def refused(call, code=None):
    try:
        call()
    except F.BundleFormatError as exc:
        if code is not None:
            assert str(exc) == code, (str(exc), code)
        return
    raise AssertionError('expected refusal')


def file_record(logical_id, role, raw=b'{}', *, name=None, study_id=None, source_name=None):
    reference = preview_payload(raw, limits=OBJECT_LIMITS).reference if raw else None
    return F.BundleFile(logical_id=logical_id, original_name=name or role+'.json',
        source_name=source_name, role=role, study_id=study_id, required=True,
        byte_count=len(raw), sha256=hashlib.sha256(raw).hexdigest(), payload_ref=reference)


def observation(file, index):
    return F.InputObservation(observation_id=f'i{index:04d}', original_name=file.original_name,
        source_name=file.source_name, role=file.role, study_id=file.study_id, required=file.required,
        status='COLLECTED', logical_id=file.logical_id)


def raw_manifest(files, *, expected=('candidate-a', 'candidate-b'), complete=True):
    files = tuple(sorted(files, key=lambda file: file.logical_id))
    return F.RawArchiveManifest(schema_version=1, kind='RAW_ARCHIVED', run_id='invented-run',
        revision_id='raw-v1', attempt_id='attempt-1', parent_bundle_sha256=None,
        storage_policy_sha256='1'*64, object_policy_sha256=OBJECT_LIMITS.policy_sha256,
        expected_candidates=expected, inventory_complete=complete,
        observed_inputs=tuple(observation(file, index) for index, file in enumerate(files)), files=files)


def fixture():
    roles = ('plan', 'profile', 'registration_commitment', 'source_receipts', 'program_source',
             'capture_source_manifest', 'prior_research')
    originals = [file_record(f'f{index:04d}', role) for index, role in enumerate(roles)]
    originals += [file_record('f0007', 'source_file', name='program.py',
                             source_name='execution_launch/program.py'),
                  file_record('f0008', 'capture', name='candidate-a.capture.json', study_id='candidate-a'),
                  file_record('f0009', 'capture', name='candidate-b.capture.json', study_id='candidate-b')]
    raw = raw_manifest(originals)
    derived = file_record('f0010', 'evaluation_record')
    verified = F.VerifiedBundleManifest(schema_version=1, kind='VERIFIED_UNAPPROVED',
        run_id=raw.run_id, revision_id='verified-v1', attempt_id=raw.attempt_id,
        parent_bundle_sha256=None, storage_policy_sha256=raw.storage_policy_sha256,
        object_policy_sha256=raw.object_policy_sha256, input_archive_digest=F.raw_archive_digest(raw),
        plan_digest='2'*64, profile_digest='3'*64, rules_digest='4'*64, registry_digest='5'*64,
        source_digest='6'*64, family_digest='7'*64, receipt_audit_digest='8'*64,
        evaluator_revision='forward-paper-carry-v2', source_kind_claim='synthetic',
        capture_start=AT, capture_end=AT+timedelta(minutes=2), evaluated_at=AT+timedelta(minutes=3),
        candidates=(F.CandidateEvidence(study_id='candidate-a', protocol_digest='a'*64,
                                       capture_logical_id='f0008', result_digest='b'*64),
                    F.CandidateEvidence(study_id='candidate-b', protocol_digest='c'*64,
                                       capture_logical_id='f0009', result_digest='d'*64)),
        files=raw.files+(derived,))
    return SimpleNamespace(raw=raw, verified=verified,
        raw_payloads={file.logical_id:b'{}' for file in raw.files},
        verified_payloads={file.logical_id:b'{}' for file in verified.files})


def test_complete_invented_metadata_roundtrip_retains_both_candidates_and_exact_bytes():
    env = fixture()
    raw_bytes = F.raw_archive_bytes(env.raw)
    verified_bytes = F.verified_bundle_bytes(env.verified)
    assert F.parse_raw_archive(raw_bytes) == env.raw
    assert F.parse_verified_bundle(verified_bytes) == env.verified
    F.validate_verified_inputs(env.raw, env.verified)
    F.validate_payloads(env.raw, MappingProxyType(env.raw_payloads))
    F.validate_payloads(env.verified, env.verified_payloads)
    assert F.raw_archive_digest(env.raw) == hashlib.sha256(b'tradegen-research-raw-archive/1\0'+raw_bytes).hexdigest()
    assert F.verified_bundle_digest(env.verified) == hashlib.sha256(b'tradegen-research-bundle/1\0'+verified_bytes).hexdigest()
    assert env.verified.kind == 'VERIFIED_UNAPPROVED'  # a document kind, not issuance


def test_empty_malformed_and_unsafe_original_names_are_preserved_without_rewriting():
    originals = (file_record('empty', 'other_input', b'', name='../NUL'),
                 file_record('malformed', 'incomplete_capture', b'{not-json\n', name='A.capture.json'),
                 file_record('variant', 'other_input', b'\xff\x00', name='a.capture.json'))
    manifest = raw_manifest(originals, expected=None, complete=False)
    restored = F.parse_raw_archive(F.raw_archive_bytes(manifest))
    assert restored == manifest and restored.files[0].payload_ref is None
    F.validate_payloads(restored, {'empty':b'', 'malformed':b'{not-json\n', 'variant':b'\xff\x00'})
    refused(lambda:F.validate_payloads(restored, {'empty':b'', 'malformed':b'{}', 'variant':b'\xff\x00'}),
            'BUNDLE_PAYLOAD_MISMATCH')


def test_unreadable_inventory_and_unknown_candidates_are_distinct_from_empty_expected_set():
    unknown = raw_manifest((), expected=None, complete=False)
    missing = F.InputObservation(observation_id='missing', original_name='unknown.capture.json',
        source_name=None, role='capture', study_id=None, required=True, status='REFUSED', logical_id=None)
    unknown = replace(unknown, observed_inputs=(missing,))
    explicit_empty = replace(unknown, expected_candidates=())
    assert F.raw_archive_digest(unknown) != F.raw_archive_digest(explicit_empty)
    assert F.parse_raw_archive(F.raw_archive_bytes(unknown)).observed_inputs[0].status == 'REFUSED'
    refused(lambda:replace(missing, logical_id='invented'))


def test_original_inventory_is_bijective_and_metadata_cannot_be_relabelled():
    env = fixture()
    refused(lambda:replace(env.raw, observed_inputs=env.raw.observed_inputs[:-1]))
    duplicate = replace(env.raw.observed_inputs[-1], observation_id='z0001', logical_id='f0008',
                        original_name='candidate-a.capture.json', study_id='candidate-a')
    refused(lambda:replace(env.raw, observed_inputs=env.raw.observed_inputs+(duplicate,)))
    changed = replace(env.raw.observed_inputs[0], required=False)
    refused(lambda:replace(env.raw, observed_inputs=(changed,)+env.raw.observed_inputs[1:]))


def test_wrong_original_archive_or_identity_cannot_be_used_for_derivation():
    env = fixture()
    for changes in ({'input_archive_digest':'0'*64}, {'run_id':'another-run'},
                    {'attempt_id':'another-attempt'}, {'revision_id':env.raw.revision_id},
                    {'storage_policy_sha256':'9'*64}):
        refused(lambda:F.validate_verified_inputs(env.raw, replace(env.verified, **changes)),
                'BUNDLE_INPUT_ARCHIVE_MISMATCH')


def test_unknown_or_incomplete_raw_archive_cannot_be_promoted():
    env = fixture()
    for raw in (replace(env.raw, inventory_complete=False), replace(env.raw, expected_candidates=None),
                replace(env.raw, expected_candidates=())):
        verified = replace(env.verified, input_archive_digest=F.raw_archive_digest(raw))
        refused(lambda:F.validate_verified_inputs(raw, verified), 'BUNDLE_INPUT_ARCHIVE_INCOMPLETE')
    missing = F.InputObservation(observation_id='z0001', original_name='missing.json', source_name=None,
        role='report', study_id=None, required=True, status='MISSING', logical_id=None)
    raw = replace(env.raw, observed_inputs=env.raw.observed_inputs+(missing,))
    verified = replace(env.verified, input_archive_digest=F.raw_archive_digest(raw))
    refused(lambda:F.validate_verified_inputs(raw, verified), 'BUNDLE_INPUT_ARCHIVE_INCOMPLETE')


def test_success_only_subset_is_rejected_even_with_a_well_formed_verified_manifest():
    env = fixture()
    subset = replace(env.verified, candidates=env.verified.candidates[:1],
                     files=tuple(file for file in env.verified.files if file.logical_id != 'f0009'))
    refused(lambda:F.validate_verified_inputs(env.raw, subset), 'BUNDLE_CANDIDATE_SET_MISMATCH')


def test_original_report_cannot_disappear_and_only_named_derived_roles_may_be_added():
    env = fixture()
    report = file_record('f0011', 'report', b'original report', name='audit.md')
    raw = raw_manifest(env.raw.files+(report,))
    verified = replace(env.verified, input_archive_digest=F.raw_archive_digest(raw))
    refused(lambda:F.validate_verified_inputs(raw, verified), 'BUNDLE_INPUT_FILE_MISMATCH')
    extra_source = file_record('f0012', 'source_file', name='extra.py', source_name='extra.py')
    verified = replace(env.verified, files=env.verified.files+(extra_source,))
    refused(lambda:F.validate_verified_inputs(env.raw, verified), 'BUNDLE_INPUT_FILE_MISMATCH')


def test_changed_source_bytes_or_file_metadata_do_not_inherit_raw_link():
    env = fixture()
    for changed in (replace(env.verified.files[7], original_name='renamed.py'),
                    file_record('f0007', 'source_file', b'changed', name='program.py',
                                source_name='execution_launch/program.py')):
        verified = replace(env.verified, files=env.verified.files[:7]+(changed,)+env.verified.files[8:])
        refused(lambda:F.validate_verified_inputs(env.raw, verified), 'BUNDLE_INPUT_FILE_MISMATCH')


def test_empty_file_representation_cannot_hide_nonempty_content_or_reference():
    empty = file_record('empty', 'other_input', b'')
    full = file_record('full', 'other_input', b'X')
    refused(lambda:replace(empty, sha256='0'*64))
    refused(lambda:replace(empty, payload_ref=full.payload_ref))
    refused(lambda:replace(full, payload_ref=None))
    refused(lambda:replace(full, byte_count=2))


def test_object_policy_and_reference_binding_are_checked_before_payload_use():
    env = fixture()
    refused(lambda:replace(env.raw, object_policy_sha256='0'*64))
    file = env.raw.files[0]
    refused(lambda:replace(file, payload_ref=replace(file.payload_ref, payload_sha256='0'*64)))
    refused(lambda:replace(file, payload_ref=replace(file.payload_ref, payload_bytes=1)))


def test_source_names_use_role_namespaces_and_repo_relative_paths():
    env = fixture()
    program = replace(env.verified.files[4], original_name='program.py')
    another = file_record('f0011', 'source_file', name='program.py', source_name='another/program.py')
    files = env.verified.files[:4]+(program,)+env.verified.files[5:]+(another,)
    F.verified_bundle_bytes(replace(env.verified, files=files))
    for name in ('/absolute.py', '../escape.py', 'a//b.py', 'C:module.py', 'a\\b.py',
                 'a/CON.txt', 'a/COM¹.py', 'a/trailing. ', 'a/../b.py', 'a/\x01.py'):
        changed = replace(env.verified.files[7], source_name=name)
        refused(lambda:replace(env.verified, files=env.verified.files[:7]+(changed,)+env.verified.files[8:]))


def test_alias_collisions_remain_in_raw_but_cannot_be_verified():
    env = fixture()
    for alias in ('EXECUTION_LAUNCH/PROGRAM.PY',):
        duplicate = file_record('f0011', 'source_file', name='program.py', source_name=alias)
        F.raw_archive_bytes(raw_manifest(env.raw.files+(duplicate,)))
        refused(lambda:replace(env.verified, files=env.verified.files+(duplicate,)))
    first = file_record('f0011', 'report', name='é.md')
    second = file_record('f0012', 'report', name='e\u0301.md')
    F.raw_archive_bytes(raw_manifest(env.raw.files+(first,second)))
    refused(lambda:replace(env.verified, files=env.verified.files+(first,second)))


def test_required_roles_and_original_candidate_bindings_are_not_optional():
    env = fixture()
    for role in ('plan', 'profile', 'registration_commitment', 'source_receipts', 'source_file',
                 'program_source', 'capture_source_manifest', 'prior_research', 'evaluation_record'):
        refused(lambda:replace(env.verified, files=tuple(file for file in env.verified.files if file.role != role)))
    changed = replace(env.verified.files[8], study_id='candidate-b')
    refused(lambda:replace(env.verified, files=env.verified.files[:8]+(changed,)+env.verified.files[9:]))


def test_payload_set_and_exact_bytes_are_required_without_implicit_coercion():
    env = fixture()
    for payloads in ({name:raw for name,raw in env.raw_payloads.items() if name != 'f0009'},
                     env.raw_payloads | {'unknown':b'{}'}, env.raw_payloads | {'f0000':b'{ }'},
                     env.raw_payloads | {'f0000':bytearray(b'{}')}, env.raw_payloads | {'f0000':'{}'}):
        refused(lambda:F.validate_payloads(env.raw, payloads), 'BUNDLE_PAYLOAD_MISMATCH')


def test_integer_booleans_and_mutated_frozen_nested_records_are_refused():
    env = fixture()
    refused(lambda:replace(env.raw, schema_version=True))
    refused(lambda:replace(env.raw, inventory_complete=1))
    refused(lambda:replace(env.raw.files[0], required=1))
    refused(lambda:replace(env.raw.files[0], byte_count=True))
    object.__setattr__(env.raw.files[0], 'required', 1)
    refused(lambda:F.raw_archive_bytes(env.raw))
    env = fixture()
    object.__setattr__(env.raw.files[0].payload_ref, 'schema', True)
    refused(lambda:F.raw_archive_bytes(env.raw))


def test_parser_rejects_extra_keys_duplicate_keys_nonfinite_and_wrong_collection_types():
    env = fixture()
    raw = F.raw_archive_bytes(env.raw)
    body = json.loads(raw)
    changed = body | {'authority':True}
    refused(lambda:F.parse_raw_archive(encoded(changed)))
    refused(lambda:F.parse_raw_archive(b'{"kind":"RAW_ARCHIVED",'+raw[1:]))
    for value in (None, {}, True, 1):
        refused(lambda:F.parse_raw_archive(encoded(body | {'files':value})))
    for spelling in (b'NaN', b'Infinity', b'1.0', b'1e0'):
        refused(lambda:F.parse_raw_archive(raw.replace(b'"schema_version":1', b'"schema_version":'+spelling)))
    bad = json.loads(raw)
    bad['files'][0]['required'] = 1
    refused(lambda:F.parse_raw_archive(encoded(bad)))
    bad = json.loads(raw)
    bad['files'][0]['payload_ref']['unexpected'] = True
    refused(lambda:F.parse_raw_archive(encoded(bad)))


def test_envelope_must_have_exact_format_but_original_payload_whitespace_is_retained():
    env = fixture()
    raw = F.raw_archive_bytes(env.raw)
    refused(lambda:F.parse_raw_archive(raw+b'\n'))
    refused(lambda:F.parse_raw_archive(b' '+raw))
    refused(lambda:F.parse_raw_archive(json.dumps(json.loads(raw), indent=2).encode('ascii')))
    original = b'  { "value": 1 }\r\n'
    manifest = raw_manifest((file_record('raw', 'other_input', original),), expected=None, complete=False)
    F.validate_payloads(F.parse_raw_archive(F.raw_archive_bytes(manifest)), {'raw':original})


def test_custom_limits_enforce_exact_manifest_file_total_count_and_name_boundaries():
    env = fixture()
    length = len(F.raw_archive_bytes(env.raw))
    for maximum, accepted in ((length-1,False),(length,True),(length+1,True)):
        limits = replace(F.DEFAULT_LIMITS,max_manifest_bytes=maximum)
        if accepted:
            assert F.parse_raw_archive(F.raw_archive_bytes(env.raw,limits=limits),limits=limits) == env.raw
        else:
            refused(lambda:F.raw_archive_bytes(env.raw,limits=limits),'BUNDLE_RESOURCE_LIMIT')
    for field, exact in (('max_files',len(env.raw.files)),('max_file_bytes',2),
                         ('max_total_bytes',2*len(env.raw.files)),
                         ('max_name_bytes',max(len(file.original_name.encode('utf-8')) for file in env.raw.files)),
                         ('max_candidates',2)):
        # source_name is independently budgeted, and is longer than a basename.
        if field == 'max_name_bytes':
            exact = max(exact, len('execution_launch/program.py'))
        F.raw_archive_bytes(env.raw,limits=replace(F.DEFAULT_LIMITS,**{field:exact}))
        refused(lambda:F.raw_archive_bytes(env.raw,limits=replace(F.DEFAULT_LIMITS,**{field:exact-1})),
                'BUNDLE_RESOURCE_LIMIT')


def test_invalid_limits_and_noncanonical_time_or_unsupported_revision_refuse():
    for field in asdict(F.DEFAULT_LIMITS):
        for value in (0,-1,True,1.0,getattr(F.DEFAULT_LIMITS,field)+1):
            refused(lambda:replace(F.DEFAULT_LIMITS,**{field:value}),'BUNDLE_LIMITS_INVALID')
    env = fixture()
    for changes in ({'capture_start':AT.replace(tzinfo=None)}, {'capture_end':AT},
                    {'evaluated_at':AT}, {'evaluator_revision':'forward-universe-v1'},
                    {'source_kind_claim':'authenticated'}):
        refused(lambda:replace(env.verified,**changes))
    body = json.loads(F.verified_bundle_bytes(env.verified))
    body['evaluated_at'] = '2026-01-01T00:03:00Z'
    refused(lambda:F.parse_verified_bundle(encoded(body)))


def test_deleted_frozen_limit_slot_refuses_with_fixed_code_on_all_public_consumers():
    env = fixture()
    raw_bytes, verified_bytes = F.raw_archive_bytes(env.raw), F.verified_bundle_bytes(env.verified)
    broken = replace(F.DEFAULT_LIMITS)
    object.__delattr__(broken, 'max_files')
    calls = (
        lambda:F.raw_archive_bytes(env.raw,limits=broken),
        lambda:F.verified_bundle_bytes(env.verified,limits=broken),
        lambda:F.raw_archive_digest(env.raw,limits=broken),
        lambda:F.verified_bundle_digest(env.verified,limits=broken),
        lambda:F.parse_raw_archive(raw_bytes,limits=broken),
        lambda:F.parse_verified_bundle(verified_bytes,limits=broken),
        lambda:F.validate_verified_inputs(env.raw,env.verified,limits=broken),
        lambda:F.validate_payloads(env.raw,env.raw_payloads,limits=broken),
    )
    for call in calls:
        refused(call,'BUNDLE_LIMITS_INVALID')


def test_sorted_exact_collections_and_generated_logical_ids_are_required():
    env = fixture()
    refused(lambda:replace(env.raw,files=tuple(reversed(env.raw.files))))
    refused(lambda:replace(env.raw,expected_candidates=('candidate-b','candidate-a')))
    refused(lambda:replace(env.verified,candidates=tuple(reversed(env.verified.candidates))))
    for name in ('../outside','/absolute','C:drive','a.b','a/b','A'):
        refused(lambda:replace(env.raw.files[0],logical_id=name))


def test_parser_bounds_nesting_and_large_flat_json_before_decoding():
    refused(lambda:F.parse_raw_archive(b'['*13+b'0'+b']'*13))
    refused(lambda:F.parse_raw_archive(b'['+b'0,'*200001+b'0]'),'BUNDLE_RESOURCE_LIMIT')
    refused(lambda:F.parse_raw_archive(b'{"x":12345678901234567}'))


def test_raw_kind_and_verified_kind_have_no_cross_parser_or_approval_upgrade():
    env = fixture()
    refused(lambda:F.parse_verified_bundle(F.raw_archive_bytes(env.raw)))
    refused(lambda:F.parse_raw_archive(F.verified_bundle_bytes(env.verified)))
    refused(lambda:replace(env.raw,kind='VERIFIED_UNAPPROVED'))
    refused(lambda:replace(env.verified,kind='APPROVED'))
    # Existing inputs cannot acquire a new evaluation through a raw-role label.
    evaluation = file_record('result','evaluation_record')
    refused(lambda:raw_manifest((evaluation,),expected=None,complete=False))


def test_archival_parent_claim_neither_changes_input_binding_nor_creates_authority():
    env = fixture()
    claimed = replace(env.verified,parent_bundle_sha256='f'*64)
    F.validate_verified_inputs(env.raw,claimed)
    assert F.verified_bundle_digest(claimed) != F.verified_bundle_digest(env.verified)
    assert not hasattr(claimed,'signature') and not hasattr(claimed,'execution_ready')


def test_complete_input_metadata_preflight_is_pure_and_does_not_require_invented_results():
    env = fixture()
    assert F.validate_complete_inputs(env.raw) is None
    for changes in ({'required':False}, {'original_name':'../unsafe.json'}):
        changed = replace(env.raw.files[0], **changes)
        invalid = raw_manifest((changed,)+env.raw.files[1:])
        assert F.parse_raw_archive(F.raw_archive_bytes(invalid)) == invalid
        refused(lambda:F.validate_complete_inputs(invalid), 'BUNDLE_FORMAT_INVALID')
    report = file_record('f0010', 'report', name='report.md')
    twin = file_record('f0011', 'report', name='REPORT.md')
    invalid = raw_manifest(env.raw.files+(report,twin))
    refused(lambda:F.validate_complete_inputs(invalid), 'BUNDLE_FORMAT_INVALID')
    refused(lambda:F.validate_complete_inputs(replace(env.raw, inventory_complete=False)),
            'BUNDLE_INPUT_ARCHIVE_INCOMPLETE')
    incomplete = raw_manifest(env.raw.files[:-1])
    refused(lambda:F.validate_complete_inputs(incomplete), 'BUNDLE_CANDIDATE_SET_MISMATCH')
