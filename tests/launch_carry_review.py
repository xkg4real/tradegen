"""Carry-v2 detached review contracts; computed fixtures and disposable keys only.

The genuine positive path loads a signed temporary owner home and evaluates the
actual capture. History callbacks fail if invoked: a detached review is not a
live-history attestation, management approval, session arm or order capability.
"""
from copy import deepcopy
from contextlib import ExitStack, nullcontext, redirect_stdout
from dataclasses import asdict, replace
from datetime import timedelta
from functools import lru_cache
import ast
import base64
import hashlib
import io
import json
from pathlib import Path
from types import SimpleNamespace
import sys
import tempfile
from unittest.mock import patch

from core.compliance import model as M, owner
from execution_control.owner_authority import CurrentOwnerAuthority, ReviewAuthority
from execution_launch import driver as driver_module
from execution_launch.driver import (CARRY_FACTORY_ID, FACTORY_ID, DeploymentWindow,
    describe_fixed_driver, make_fixed_carry_driver)
from execution_launch.managed_behavior import behavior_digest, behavior_document
from execution_launch.review_auth import (CARRY_REVIEW_DOMAIN, REVIEW_DOMAIN,
    ReviewAuthenticationError, ReviewVerifiers, parse_review_document, review_body,
    review_signing_bytes, verify_implementation_review, verify_source_review)
from execution_launch.review_request import (ReviewRequestError, bind_review_family,
    build_family_commitment, build_review_request, parse_review_request, review_request_json)
from execution_launch.runner import EvidencePackage, ImplementationBinding, _assess
from execution_launch.strategy import ReviewBinding, assess_strategy, evidence_digest
from tests.compliance_signer import signer, _FILES
from tests.launch_carry_strategy import fixture_capture
from tests.launch_profile import context
from tests.launch_review_auth import invented_provider, invented_verifier, review_fixture
from tests.launch_windows_owner_authority import keys, real_code_hash, signed_home

ROOT = Path(__file__).resolve().parents[1]


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False)


def _rehash(request):
    body = {key: value for key, value in request.items() if key != 'request_sha256'}
    request['request_sha256'] = hashlib.sha256(_canonical(body).encode('ascii')).hexdigest()
    return request


@lru_cache(maxsize=1)
def carry_review_fixture():
    sample = fixture_capture()
    window = DeploymentWindow(deployment_id='invented-carry-review', start=sample.now,
                              end=sample.now+timedelta(hours=1))
    actual = make_fixed_carry_driver(sample.program, sample.protocol, sample.profile, window=window,
        history_provider=invented_provider, history_verifier=invented_verifier,
        program_artifact=sample.artifact)
    request = build_review_request(sample.profile, sample.protocol, sample.result, now=sample.now,
        program_artifact=sample.artifact, parameters_json=sample.parameters)
    key = keys()[0]
    fp = 'SHA256:' + hashlib.sha256(key.public_key().public_bytes_raw()).hexdigest()
    body = review_body(request, asdict(describe_fixed_driver(actual)), deployment_code_hash=real_code_hash(),
        audit_sha256=hashlib.sha256(b'invented carry review, no owner or live trading authorization').hexdigest(),
        owner_fingerprint=fp, issued_at=sample.now, expires_at=sample.now+timedelta(minutes=30))
    return SimpleNamespace(sample=sample, driver=actual, key=key, body=body, window=window)


def _document(body=None, *, key=None, domain=None):
    f = carry_review_fixture()
    body = deepcopy(f.body if body is None else body)
    signing = review_signing_bytes(body)
    if domain is not None:
        signing = domain + signing[len(CARRY_REVIEW_DOMAIN):]
    return _canonical({'body': body, 'signature_b64': base64.b64encode(
        (key or f.key).sign(signing)).decode('ascii')})


def _source_binding():
    f = carry_review_fixture()
    request, b = f.body['request'], f.body['request']['bindings']
    return ReviewBinding(protocol_digest=b['protocol_digest'], evidence_digest=b['evidence_digest'],
        registry_digest=b['registry_digest'], inputs_digest=b['inputs_digest'],
        strategy_id=request['strategy_id'], strategy_code_sha256=b['program_digest'],
        profile_contract_digest=b['profile_contract_digest'], rule_terms_digest=b['rule_terms_digest'],
        capture_end=f.sample.protocol.capture_end, evaluator_revision=request['evaluator_revision'],
        behavior_revision=request['behavior_revision'], terminal_accounting=request['terminal_accounting'],
        management_behavior_sha256=request['management_behavior_sha256'],
        computed_summary_sha256=hashlib.sha256(_canonical(request['computed_summary']).encode('ascii')).hexdigest())


def _implementation_binding():
    b = carry_review_fixture().body['request']['bindings']
    return ImplementationBinding(**{name: b[name] for name in
        ('program_digest', 'protocol_digest', 'evidence_digest', 'profile_contract_digest', 'rule_terms_digest')})


def _authority():
    f = carry_review_fixture()
    ctx = context(f.sample.now, owner=M.OwnerState(status='OK', fingerprint=f.body['owner_fingerprint']),
                  code_hash=real_code_hash())
    return ReviewAuthority(context=ctx, public_key_raw=f.key.public_key().public_bytes_raw(),
                           observed_at=f.sample.now)


def _source(raw=None, binding=None):
    return verify_source_review(_source_binding() if binding is None else binding,
        _document() if raw is None else raw, authority=_authority(), now=carry_review_fixture().sample.now)


def _refused(call, code=None, *, error=ReviewAuthenticationError):
    try:
        call()
    except error as exc:
        if code is not None:
            assert str(exc) == code, (str(exc), code)
        return
    raise AssertionError('carry review boundary accepted an invalid substitution')


def test_real_temporary_owner_and_actual_carry_evaluation_qualify_without_arming():
    f = carry_review_fixture()
    with signed_home():
        before = owner.log_path().read_bytes()
        provider = CurrentOwnerAuthority(clock=lambda: f.sample.now)
        current = provider(f.sample.now)
        assert current.context.code_signed and M.is_sealed(current.context)
        verifiers = ReviewVerifiers(_document(), clock=lambda: f.sample.now, authority_provider=provider,
            approved_history_provider=invented_provider, approved_history_verifier=invented_verifier)
        result = verifiers.assess_bundle(f.sample.profile,
            EvidencePackage(protocol=f.sample.protocol, result=f.sample.result), f.driver)
        assert result.assessment.research_review_ready
        assert not result.assessment.execution_ready
        assert result.binding == _implementation_binding()
        assert verifiers.source(_source_binding()).binding_digest == evidence_digest(_source_binding())
        assert verifiers.implementation(_implementation_binding(), f.driver).callback is f.driver.callback
        assert owner.log_path().read_bytes() == before
        assert current.context.session == M.SessionState()


def test_new_review_version_domain_and_factory_are_exactly_bound():
    f = carry_review_fixture()
    assert f.body['schema_version'] == 2 and f.body['request']['schema_version'] == 3
    assert f.body['purpose'] == 'strategy_source_and_fixed_carry_implementation_review'
    assert f.body['driver_identity']['factory_id'] == CARRY_FACTORY_ID
    assert CARRY_REVIEW_DOMAIN == b'tradegen-strategy-review/2\n'
    assert review_signing_bytes(f.body) == CARRY_REVIEW_DOMAIN + _canonical(f.body).encode('ascii')
    assert parse_review_document(_document())['body'] == f.body


def test_legacy_and_owner_log_signature_domains_cannot_authenticate_carry():
    for domain in (REVIEW_DOMAIN, b'tradegen-owner-log/1\n', b'tradegen-strategy-review/3\n'):
        _refused(lambda domain=domain: _source(_document(domain=domain)), 'REVIEW_SIGNATURE_UNVERIFIED')
    _refused(lambda: _source(_document(key=keys()[1])), 'REVIEW_SIGNATURE_UNVERIFIED')


def test_body_schema_request_schema_and_factory_cannot_be_mixed():
    f = carry_review_fixture()
    changes = (
        {'schema_version': 1, 'purpose': 'strategy_source_and_fixed_implementation_review'},
        {'purpose': 'strategy_source_and_fixed_implementation_review'},
        {'schema_version': 3}, {'schema_version': True},
        {'driver_identity': f.body['driver_identity'] | {'factory_id': FACTORY_ID}},
        {'driver_identity': f.body['driver_identity'] | {'factory_id': 'invented-carry-factory'}},
        {'request': review_fixture()[-1]['request']},
    )
    for change in changes:
        _refused(lambda change=change: review_signing_bytes(deepcopy(f.body) | change))


def test_source_binding_prevents_removing_or_replacing_each_carry_semantic():
    binding = _source_binding()
    changes = {'evaluator_revision': 'forward-paper-v1', 'behavior_revision': 'protective-carry-v3',
               'terminal_accounting': 'force_liquidation', 'management_behavior_sha256': 'f'*64,
               'computed_summary_sha256': 'f'*64}
    for name, value in changes.items():
        for bad in (None, value):
            _refused(lambda name=name, bad=bad: _source(binding=replace(binding, **{name: bad})),
                     'REVIEW_SOURCE_BINDING_MISMATCH')
    no_version = replace(binding, **{name: None for name in changes})
    _refused(lambda: _source(binding=no_version), 'REVIEW_SOURCE_BINDING_MISMATCH')


def test_cloned_driver_or_wrong_history_dependency_cannot_receive_implementation_receipt():
    f = carry_review_fixture()
    def verify(actual, provider=invented_provider):
        return verify_implementation_review(_implementation_binding(), actual, _document(),
            authority=_authority(), now=f.sample.now, approved_history_provider=provider,
            approved_history_verifier=invented_verifier)
    _refused(lambda: verify(replace(f.driver)), 'REVIEW_FIXED_DRIVER_REQUIRED')
    _refused(lambda: verify(f.driver, lambda _: None), 'REVIEW_HISTORY_DEPLOYMENT_MISMATCH')
    _refused(lambda: verify(review_fixture()[6]), 'REVIEW_FIXED_DRIVER_MISMATCH')


def test_post_signature_summary_edit_cannot_change_the_reviewed_evidence():
    value = json.loads(_document())
    value['body']['request']['computed_summary']['metrics']['valuation_total_return'] += 0.125
    _rehash(value['body']['request'])
    _refused(lambda: _source(_canonical(value)), 'REVIEW_SIGNATURE_UNVERIFIED')


def test_signed_changed_display_is_rejected_against_the_actual_issued_result():
    f = carry_review_fixture()
    for name, value in (('valuation_total_return', 0.125), ('realized_net_profit_quote', '-1'),
                        ('terminal_units', '0')):
        body = deepcopy(f.body)
        metrics = body['request']['computed_summary']['metrics']
        assert metrics[name] != value, (name, value)
        metrics[name] = value
        _rehash(body['request'])
        verifiers = ReviewVerifiers(_document(body), clock=lambda: f.sample.now,
            authority_provider=lambda _: _authority(), approved_history_provider=invented_provider,
            approved_history_verifier=invented_verifier)
        report, _ = _assess(f.sample.profile,
            EvidencePackage(protocol=f.sample.protocol, result=f.sample.result, review_verifier=verifiers.source),
            f.driver, verifiers.implementation, f.sample.now)
        assert not report.research_review_ready
        assert report.reasons == ('STRATEGY_TRUSTED_REVIEW_UNVERIFIED',)
        _refused(lambda: verifiers.assess_bundle(f.sample.profile,
            EvidencePackage(protocol=f.sample.protocol, result=f.sample.result), f.driver),
            'REVIEW_EVIDENCE_NOT_QUALIFIED')


def test_carry_signed_summary_distinguishes_valuation_inventory_and_realized_amounts():
    f = carry_review_fixture()
    metrics = f.body['request']['computed_summary']['metrics']
    numeric = {'observations', 'completed_roundtrips', 'valuation_total_return', 'max_drawdown',
        'double_cost_valuation_total_return', 'extra_delay_valuation_total_return', 'family_adjusted_p'}
    amounts = {'terminal_units', 'terminal_cash_quote', 'terminal_mark_quote',
        'terminal_marked_equity_quote', 'terminal_inventory_cost_quote', 'realized_net_profit_quote',
        'unrealized_net_profit_quote', 'total_fees_quote_exact', 'turnover_quote_exact'}
    assert set(metrics) == numeric | amounts | {'terminal_observed_at', 'terminal_source_sha256'}
    assert metrics['valuation_total_return'] == f.sample.result.primary.total_return
    for name in amounts:
        assert type(metrics[name]) is str and metrics[name] == getattr(f.sample.result.primary, name)
    assert metrics['terminal_source_sha256'] == f.sample.bars[-1].source_sha256
    assert metrics['terminal_observed_at'] == f.sample.bars[-1].observed_at.isoformat(timespec='microseconds')
    assert 'total_return' not in metrics and 'net_profit' not in metrics


def test_standalone_and_runtime_signed_amount_codecs_are_strict_and_equal():
    request = carry_review_fixture().body['request']
    for value in ('+1', '-0', '01', '1.0', '1e2', 'NaN', 'Infinity', 1.0, True, None):
        changed = deepcopy(request)
        changed['computed_summary']['metrics']['realized_net_profit_quote'] = value
        raw = _canonical(_rehash(changed))
        _refused(lambda raw=raw: parse_review_request(raw), error=ReviewRequestError)
        _refused(lambda raw=raw: signer._rr_parse_review_request(raw), error=ValueError)
    changed = deepcopy(request)
    changed['computed_summary']['metrics']['realized_net_profit_quote'] = '-0.125'
    raw = _canonical(_rehash(changed))
    assert signer._rr_parse_review_request(raw) == parse_review_request(raw)
    changed['computed_summary']['metrics']['terminal_cash_quote'] = '-0.125'
    raw = _canonical(_rehash(changed))
    _refused(lambda: parse_review_request(raw), error=ReviewRequestError)
    _refused(lambda: signer._rr_parse_review_request(raw), error=ValueError)


def test_unsigned_carry_summary_cannot_grant_or_replace_computed_qualification():
    f = carry_review_fixture()
    unsigned = parse_review_request(review_request_json(f.body['request']))
    assert not any(unsigned['authority'].values())
    assert unsigned['review_signature'] is None
    assessment = assess_strategy(f.sample.protocol, f.sample.result,
        profile_contract_digest=f.sample.protocol.profile_contract_digest,
        rule_terms_digest=f.sample.protocol.rule_terms_digest,
        strategy_code_sha256=f.sample.protocol.strategy_code_sha256, now=f.sample.now)
    assert assessment.math_qualified and not assessment.research_review_ready
    for key in ('signature_verified', 'execution_ready', 'owner_context_verified'):
        changed = deepcopy(unsigned)
        changed['authority'][key] = True
        _rehash(changed)
        _refused(lambda changed=changed: parse_review_request(_canonical(changed)),
                 error=ReviewRequestError)


def test_standalone_carry_single_request_and_signing_bytes_match_runtime():
    body = carry_review_fixture().body
    raw = review_request_json(body['request'])
    assert signer._rr_parse_review_request(raw) == body['request']
    assert signer._rr_review_request_json(body['request']) == raw
    assert signer._rv_review_signing_bytes(body) == review_signing_bytes(body)
    assert signer._rv_review_body(body['request'], body['driver_identity'],
        deployment_code_hash=body['deployment_code_hash'], audit_sha256=body['audit_sha256'],
        owner_fingerprint=body['owner_fingerprint'], issued_at=carry_review_fixture().sample.now,
        expires_at=carry_review_fixture().sample.now+timedelta(minutes=30)) == body


def test_whole_family_carry_request_uses_schema_four_and_new_signature_domain():
    f = carry_review_fixture()
    request = f.body['request']
    commitment = build_family_commitment(plan_digest='a'*64,
        capture_digests={request['study_id']: hashlib.sha256(f.sample.raw).hexdigest()},
        result_digests={request['study_id']: evidence_digest(f.sample.result)})
    family = bind_review_family(request, commitment)
    assert family['schema_version'] == 4 and family['family_commitment'] == commitment
    body = review_body(family, f.body['driver_identity'], deployment_code_hash=f.body['deployment_code_hash'],
        audit_sha256=f.body['audit_sha256'], owner_fingerprint=f.body['owner_fingerprint'],
        issued_at=f.sample.now, expires_at=f.sample.now+timedelta(minutes=30))
    assert signer._rr_parse_review_request(review_request_json(family)) == family
    assert signer._rv_review_signing_bytes(body) == review_signing_bytes(body)
    assert _source(_document(body)).binding_digest == evidence_digest(_source_binding())


def test_independent_behavior_document_hash_and_factory_source_closure_match():
    assert signer._review_carry_behavior_document() == behavior_document()
    assert signer._review_carry_behavior_digest() == behavior_digest()
    assert signer._REVIEW_SOURCES == driver_module._SOURCE_FILES
    assert signer._REVIEW_CARRY_SOURCES == driver_module._CARRY_SOURCE_FILES
    assert len(signer._REVIEW_SOURCES) == len(set(signer._REVIEW_SOURCES)) == 46
    assert len(signer._REVIEW_CARRY_SOURCES) == len(set(signer._REVIEW_CARRY_SOURCES)) == 49
    assert signer._REVIEW_CARRY_SOURCES[-1] == 'execution_launch/review_request.py'
    assert signer._review_source_hash(ROOT) == driver_module._sources()[0]
    carry_hash = signer._review_source_hash(ROOT, factory_id=CARRY_FACTORY_ID)
    assert carry_hash == driver_module._sources(CARRY_FACTORY_ID)[0]
    assert carry_hash == carry_review_fixture().body['driver_identity']['deployment_code_sha256']
    assert carry_hash != signer._review_source_hash(ROOT)


def test_independent_signer_hash_detects_every_carry_behavior_dependency():
    before = signer._review_source_hash(ROOT, factory_id=CARRY_FACTORY_ID)
    read = signer._review_read
    for name in signer._REVIEW_CARRY_SOURCES[len(signer._REVIEW_SOURCES):]:
        def changed(path, limit, name=name):
            raw = read(path, limit)
            return raw + b'\n# invented changed reviewed dependency\n' if path == ROOT/name else raw
        with patch.object(signer, '_review_read', changed):
            assert signer._review_source_hash(ROOT, factory_id=CARRY_FACTORY_ID) != before, name
    _refused(lambda: signer._review_source_hash(ROOT, factory_id='unknown'), error=ValueError)


def test_legacy_source_closure_binds_its_actual_behavior_resolver_dependency():
    assert 'execution_launch/managed_behavior.py' in signer._REVIEW_SOURCES
    before = signer._review_source_hash(ROOT)
    carry_before = signer._review_source_hash(ROOT, factory_id=CARRY_FACTORY_ID)
    read = signer._review_read
    def changed(path, limit):
        raw = read(path, limit)
        return raw+b'\n# changed actual shared dependency\n' if path == ROOT/'execution_launch/managed_behavior.py' else raw
    with patch.object(signer, '_review_read', changed):
        assert signer._review_source_hash(ROOT) != before
        assert signer._review_source_hash(ROOT, factory_id=CARRY_FACTORY_ID) != carry_before


def test_both_factories_and_independent_signer_detect_each_committed_account_dependency():
    """Real public source copies only: changing any consumed file changes both hashes.

    The app and standalone signer read the same disposable checkout independently;
    no hash/verifier result is mocked and the real repository is never edited.
    """
    dependencies = (
        'execution_launch/committed_account.py', 'execution_accounts/baseline_bridge.py',
        'execution_accounts/baseline.py', 'execution_accounts/baseline_store.py',
        'execution_accounts/continuous.py', 'execution_accounts/model.py',
        'execution_accounts/provider.py', 'execution_control/risk.py',
        'execution_launch/continuous_guard.py', 'execution_launch/continuous_guard_commit.py',
    )
    assert signer._REVIEW_SOURCES[15:25] == dependencies
    assert driver_module._SOURCE_FILES[15:25] == dependencies
    with tempfile.TemporaryDirectory(prefix='tradegen-closure-fixture-') as temporary:
        replica = Path(temporary)
        for name in driver_module._CARRY_SOURCE_FILES:
            destination = replica / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes((ROOT / name).read_bytes())
        with patch.object(driver_module, '__file__', str(replica / 'execution_launch/driver.py')):
            original = {}
            for factory in (FACTORY_ID, CARRY_FACTORY_ID):
                original[factory] = driver_module._sources(factory)[0]
                assert signer._review_source_hash(replica, factory_id=factory) == original[factory]
                assert signer._review_source_hash(ROOT, factory_id=factory) == original[factory]
            for name in dependencies:
                target = replica / name
                raw = target.read_bytes()
                target.write_bytes(raw + b'\n# temporary changed committed account dependency\n')
                try:
                    for factory in (FACTORY_ID, CARRY_FACTORY_ID):
                        actual = driver_module._sources(factory)[0]
                        independent = signer._review_source_hash(replica, factory_id=factory)
                        assert actual == independent and actual != original[factory], (name, factory)
                finally:
                    target.write_bytes(raw)
            for factory in (FACTORY_ID, CARRY_FACTORY_ID):
                assert driver_module._sources(factory)[0] == original[factory]
                assert signer._review_source_hash(replica, factory_id=factory) == original[factory]


def test_both_factories_and_independent_signer_detect_each_producer_dependency():
    """Real public source copies only: changing any consumed file changes both hashes.

    The app and standalone signer read the same disposable checkout independently;
    no hash/verifier result is mocked and the real repository is never edited.
    """
    dependencies = (
        'execution_launch/committed_producer.py',
        'execution_launch/committed_startup.py',
        'execution_launch/coordinator.py',
        'execution_launch/account_interval.py',
        'execution_launch/continuous_archive.py',
        'execution_launch/guard_capture_material.py',
        'execution_launch/guard_capture_format.py',
        'execution_launch/guard_capture_archive.py',
        'execution_launch/guard_generation_format.py',
        'execution_launch/guard_generation_archive.py',
        'execution_launch/research_bundle_format.py',
        'execution_launch/research_bundle_store.py',
        'execution_accounts/collector.py',
        'execution_accounts/upbit_collector.py',
        'execution_control/owner_authority.py',
        'execution_control/dry_run.py',
        'core/compliance/model.py',
        'core/compliance/owner.py',
        'execution_launch/protective_state.py',
        'execution_launch/protective_store.py',
        'execution_launch/paper_capture.py',
    )
    assert signer._REVIEW_SOURCES[25:] == dependencies
    assert driver_module._SOURCE_FILES[25:] == dependencies
    with tempfile.TemporaryDirectory(prefix='tradegen-closure-fixture-') as temporary:
        replica = Path(temporary)
        for name in driver_module._CARRY_SOURCE_FILES:
            destination = replica / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes((ROOT / name).read_bytes())
        with patch.object(driver_module, '__file__', str(replica / 'execution_launch/driver.py')):
            original = {}
            for factory in (FACTORY_ID, CARRY_FACTORY_ID):
                original[factory] = driver_module._sources(factory)[0]
                assert signer._review_source_hash(replica, factory_id=factory) == original[factory]
                assert signer._review_source_hash(ROOT, factory_id=factory) == original[factory]
            for name in dependencies:
                target = replica / name
                raw = target.read_bytes()
                target.write_bytes(raw + b'\n# temporary changed producer dependency\n')
                try:
                    for factory in (FACTORY_ID, CARRY_FACTORY_ID):
                        actual = driver_module._sources(factory)[0]
                        independent = signer._review_source_hash(replica, factory_id=factory)
                        assert actual == independent and actual != original[factory], (name, factory)
                finally:
                    target.write_bytes(raw)
            for factory in (FACTORY_ID, CARRY_FACTORY_ID):
                assert driver_module._sources(factory)[0] == original[factory]
                assert signer._review_source_hash(replica, factory_id=factory) == original[factory]


def _carry_command(*, change_after_confirmation=False):
    """Synthetic owner log/key; actual independent carry source closure, no owner files."""
    from cryptography.hazmat.primitives import serialization
    f = carry_review_fixture()
    audit = b'invented carry-v2 reviewer notes for detached command fixture only'
    closure = signer.sha256_hex(signer.canonical_json(_FILES))
    utc = f.sample.now.strftime('%Y-%m-%dT%H:%M:%SZ')
    line, _ = signer.entry_line(f.key, 1, signer.GENESIS_PREV, 'code_approved',
                               {'sha256': closure, 'files': _FILES}, utc)
    shown, written = [], []
    read = signer._review_read
    with tempfile.TemporaryDirectory(prefix='carry-signature-command-fixture-') as folder:
        root = Path(folder)
        request_path, identity_path, audit_path = root/'request.json', root/'driver.json', root/'audit.md'
        values = {request_path: review_request_json(f.body['request']).encode('ascii'),
            identity_path: _canonical(f.body['driver_identity']).encode('ascii'), audit_path: audit,
            ROOT/'core/compliance/owner_pubkey.pem': f.key.public_key().public_bytes(
                serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)}
        def read_inputs(path, limit):
            path = Path(path)
            if path in values:
                assert len(values[path]) <= limit
                return values[path]
            raw = read(path, limit)
            return raw+b'\n# changed after confirmation\n' if (shown and change_after_confirmation
                and path == ROOT/'execution_launch/managed_behavior.py') else raw
        def never(*args, **kwargs):
            raise AssertionError('detached review command must not append owner events')
        args = signer._parser().parse_args(['review-approve', '--repo', str(ROOT), '--request', str(request_path),
            '--driver-manifest', str(identity_path), '--audit', str(audit_path), '--expires-at', f.body['expires_at'],
            '--output', str(root/'detached-document.json')])
        with ExitStack() as stack:
            for obj, name, value in (
                (signer, '_review_read', read_inputs), (signer, 'code_hash', lambda _: closure),
                (signer, '_read_lines', lambda _: [line]), (signer, '_log_path', lambda: root/'owner.jsonl'),
                (signer, '_utc_now', lambda: utc), (signer, '_confirm_review', lambda body: shown.append(body)),
                (signer, '_key_path', lambda _: root/'invented.enc'), (signer, '_unlock', lambda _: f.key),
                (signer, '_exclusive', lambda _: nullcontext()), (signer, '_commit', never), (signer, '_sign', never),
                (signer, '_write_new', lambda path, data, within: written.append(data) is None),
                (sys, 'prefix', str(ROOT/'.venv'))):
                stack.enter_context(patch.object(obj, name, value))
            stack.enter_context(redirect_stdout(io.StringIO()))
            if change_after_confirmation:
                _refused(lambda: args.run(args), error=ValueError)
                assert len(shown) == 1 and not written
            else:
                assert args.run(args) == 0 and len(shown) == len(written) == 1
                signed = parse_review_document(written[0])
                assert signed['body'] == shown[0] and signed['body']['schema_version'] == 2
                assert signed['body']['driver_identity']['factory_id'] == CARRY_FACTORY_ID
                f.key.public_key().verify(base64.b64decode(signed['signature_b64']),
                                          review_signing_bytes(signed['body']))


def test_standalone_carry_command_signs_exact_displayed_synthetic_document():
    _carry_command()


def test_standalone_carry_command_rechecks_new_source_closure_after_confirmation():
    _carry_command(change_after_confirmation=True)


def test_standalone_validator_refuses_unknown_or_cross_revision_contracts():
    f = carry_review_fixture()
    for name, value in (('evaluator_revision', 'forward-universe-v1'),
            ('behavior_revision', 'protective-carry-v3'), ('terminal_accounting', 'force_liquidation'),
            ('management_behavior_sha256', 'f'*64)):
        request = deepcopy(f.body['request'])
        request[name] = value
        _rehash(request)
        raw = _canonical(request)
        _refused(lambda raw=raw: parse_review_request(raw), error=ReviewRequestError)
        _refused(lambda raw=raw: signer._rr_parse_review_request(raw), error=ValueError)
    bad = deepcopy(f.body)
    bad['driver_identity']['factory_id'] = FACTORY_ID
    _refused(lambda: signer._rv_review_signing_bytes(bad), error=ValueError)


def test_legacy_review_bytes_domain_and_optional_binding_omission_stay_unchanged():
    body = review_fixture()[-1]
    assert body['schema_version'] == 1 and body['request']['schema_version'] == 1
    assert review_signing_bytes(body) == REVIEW_DOMAIN + _canonical(body).encode('ascii')
    assert signer._rv_review_signing_bytes(body) == review_signing_bytes(body)
    assert signer._rr_review_request_json(body['request']) == review_request_json(body['request'])
    request = body['request']
    family = bind_review_family(request, build_family_commitment(plan_digest='a'*64,
        capture_digests={request['study_id']: 'b'*64},
        result_digests={request['study_id']: request['bindings']['evidence_digest']}))
    assert family['schema_version'] == 2
    assert signer._rr_review_request_json(family) == review_request_json(family)
    from tests.launch_review_auth import source_binding
    binding = source_binding()
    from execution_launch.strategy import _plain
    data = _plain(binding)
    assert set(data) == {'protocol_digest', 'evidence_digest', 'registry_digest', 'inputs_digest',
        'strategy_id', 'strategy_code_sha256', 'profile_contract_digest', 'rule_terms_digest', 'capture_end'}
    assert evidence_digest(binding) == hashlib.sha256(_canonical(data).encode('ascii')).hexdigest()


def test_standalone_signer_never_imports_runtime_app_modules():
    tree = ast.parse((ROOT/'tools/signer/sign.py').read_text())
    names = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            names.append(node.module or '')
    forbidden = ('execution_launch', 'execution_control', 'core', 'tools', 'tests')
    assert not any(name == prefix or name.startswith(prefix+'.') for name in names for prefix in forbidden)
