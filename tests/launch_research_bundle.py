"""Actual recorder -> archived bytes -> actual family evaluator -> sealed replay.

Every file, catalog/head and owner provisioning step is temporary. The recorder
uses invented public books; no real credentials, network, owner log or orders.
A storage receipt and the synthetic evaluator results never confer approval.
"""
from contextlib import contextmanager, redirect_stdout
from dataclasses import asdict, replace
from datetime import timedelta
from io import StringIO
import json
import os
from pathlib import Path
import shutil
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

from execution_launch import evidence_objects as O
from execution_launch import research_bundle as R
from execution_launch import research_bundle_format as F
from execution_launch import research_bundle_store as B
from execution_launch import strategy as E, study as S
from execution_launch.profile import profile_body
from execution_launch.study_receipts import ReceiptAudit
from tests import compliance_fixtures as CF
from tests import launch_study as SF, launch_study_receipts as RF
from tools.owner import research_bundle as OWNER


def limits(**changes):
    return B.BundleStoreLimits(**(dict(
        format_limits=F.BundleLimits(max_manifest_bytes=1024*1024, max_files=128,
            max_file_bytes=4*1024*1024, max_total_bytes=32*1024*1024, max_candidates=8, max_name_bytes=512),
        object_limits=O.ObjectLimits(chunk_bytes=65536, max_payload_bytes=4*1024*1024,
                                     max_chunks=64, max_manifest_bytes=65536),
        primary_budget=O.StoreBudget(max_bytes=64*1024*1024, max_objects=4096),
        backup_budget=O.StoreBudget(max_bytes=64*1024*1024, max_objects=4096),
        max_catalog_bytes=2*1024*1024, max_catalog_records=128) | changes))


@contextmanager
def fixture(*, carry=False, aborted=False, provision=True, storage_limits=None):
    prior = dict(E._EVALUATED)
    try:
        with CF.temp_home(), tempfile.TemporaryDirectory(prefix='tradegen_bundle_adapter_') as temp:
            base = Path(temp)
            work = base/'working'; work.mkdir()
            captures = work/'captures'; captures.mkdir()
            primary = base/'primary'; primary.mkdir()
            backup = base/'backup'; backup.mkdir()
            store = B.BundleStore(roots=B.BundleRoots(sealed_root=primary, backup_root=backup),
                limits=storage_limits or limits(), head_name='bundle-head')
            if provision:
                OWNER.provision_research_store(store)
            env = RF.fixture(carry, aborted)
            rows, paths = [], {}
            def add(role, raw, name, source_name=None):
                path = work/name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(raw)
                rows.append(R.BundleInputFile(role=role, path=path, source_name=source_name))
                paths.setdefault(role, []).append(path)
            source = S.capture_source_artifact(env.plan.candidates[0].protocol)
            add('plan', S.study_plan_json(env.plan).encode('ascii'), 'plan.json')
            add('profile', json.dumps(profile_body(SF.profile())).encode('ascii'), 'profile.json')
            add('source_receipts', env.receipt_log, 'receipts.jsonl')
            add('program_source', S._fixed_file(S.PROGRAM_SOURCE), 'program.py')
            add('capture_source_manifest', source, 'capture-source.json')
            add('prior_research', S._fixed_file(S.PRIOR_RESEARCH), 'prior.md')
            add('registration_commitment', S.commitment_json(env.plan).encode('ascii'), 'commitment.json')
            for relative in json.loads(source)['files']:
                add('source_file', S._fixed_file(relative), 'source/'+relative, relative)
            add('report', b'Unapproved display report; originals are separate.\n', 'report.md')
            for identifier, raw in env.captures.items():
                path = captures/(identifier+('.incomplete.json' if aborted else '.capture.json'))
                path.write_bytes(raw)
            yield SimpleNamespace(base=base, work=work, captures=captures, store=store, env=env, paths=paths,
                inputs=R.StudyBundleInputs(files=tuple(rows), captures_directory=captures),
                at=env.plan.candidates[0].protocol.capture_end+timedelta(seconds=1))
    finally:
        # Restore only this sequential test's registry delta; never fake an issued result.
        E._EVALUATED.clear(); E._EVALUATED.update(prior)


def finalize(e, **changes):
    args = dict(run_id='adapter-run', raw_revision_id='raw-v1', verified_revision_id='verified-v1',
                attempt_id='attempt-a', evaluated_at=e.at)
    args.update(changes)
    return R.finalize_study_bundle(e.inputs, e.store, **args)


def archived(e, result):
    return e.store.read_raw(result.input_archive_digest, require_backup=True)


def role_bytes(stored, role):
    return tuple(stored.files[f.logical_id] for f in stored.manifest.files if f.role == role)


def refused(call, code=None):
    try:
        call()
    except ValueError as exc:
        if code is not None:
            assert str(exc) == code, (str(exc), code)
        return str(exc)
    raise AssertionError('untrusted bundle accepted')


def invoke(module, *argv):
    output = StringIO()
    with redirect_stdout(output):
        code = module.main(list(argv))
    return code, json.loads(output.getvalue())


def snapshot(e, inputs=None):
    return R._snapshot(e.inputs if inputs is None else inputs, e.store, run_id='adapter-run',
        raw_revision_id='raw-v1', attempt_id='attempt-a', parent_bundle_sha256=None)


def test_actual_fixed_and_carry_archive_all_results_then_replay_without_working_files():
    for carry in (False, True):
        with fixture(carry=carry) as e:
            actual = R._research
            seen = []
            def after_backup(manifest, payloads, **kwargs):
                digest = F.raw_archive_digest(manifest, limits=e.store.limits.format_limits)
                saved = e.store.read_raw(digest, require_backup=True)
                assert dict(saved.files) == dict(payloads) and saved.backup_verified
                seen.append(digest)
                return actual(manifest, payloads, **kwargs)
            with patch.object(R, '_research', side_effect=after_backup):
                result = finalize(e)
            assert result.status == 'VERIFIED_UNAPPROVED', result.reasons
            assert seen == [result.input_archive_digest]
            assert result.raw_backup_verified and result.verified_backup_verified
            assert not result.execution_ready and not result.manifest_authenticated and not result.source_authenticated
            assert result.reasons == ('BUNDLE_MANIFEST_AUTHENTICATION_REQUIRED',)
            saved = e.store.read_verified(result.bundle_digest)
            raw = archived(e, result)
            assert all(saved.files[k] == value for k, value in raw.files.items())
            assert len(saved.manifest.candidates) == len(e.env.plan.candidates) == 3
            assert len(role_bytes(saved, 'evaluation_record')) == 1
            record = json.loads(role_bytes(saved, 'evaluation_record')[0])
            assert len(record['results']) == 3
            assert {row['study_id'] for row in record['results']} == set(e.env.captures)
            shutil.rmtree(e.work)
            replay = R.evaluate_sealed_study(e.store, result.bundle_digest)
            assert {row.study_id:E.evidence_digest(row.result) for row in replay.family.rows} == {
                row.study_id:row.result_digest for row in saved.manifest.candidates}
            assert replay.evaluated_at == e.at and not replay.execution_ready and not replay.manifest_authenticated
            minimum = e.env.plan.candidates[0].protocol.minimum_roundtrips
            assert all(row.result.primary.completed_roundtrips < minimum for row in replay.family.rows), 'fixture retains insufficient roundtrips'
            assert all(E._EVALUATED.get(id(row.result)) == (row.result, E.evidence_digest(row.result))
                       for row in replay.family.rows)


def test_unexpected_later_actual_evaluator_failure_keeps_backed_raw_without_verified_release():
    with fixture() as e:
        actual = E.evaluate_capture_json
        calls = []
        def fail_second(*args, **kwargs):
            calls.append(args[0].study_id)
            if len(calls) == 2:
                raise ValueError('SYNTHETIC_EVALUATOR_FAILED')
            return actual(*args, **kwargs)
        with patch.object(E, 'evaluate_capture_json', side_effect=fail_second):
            result = finalize(e)
        assert len(calls) == 2 and result.status == 'RAW_ARCHIVED' and result.bundle_digest is None
        assert result.reasons[0] == 'SYNTHETIC_EVALUATOR_FAILED'
        raw = archived(e, result)
        assert raw.backup_verified and set(role_bytes(raw, 'capture')) == set(e.env.captures.values())
        assert not any(item.role == 'evaluation_record' for item in raw.manifest.files)
        assert not result.execution_ready and not result.manifest_authenticated


def test_last_capture_corruption_archives_exact_bytes_and_issues_no_partial_family():
    with fixture() as e:
        path = e.captures/(sorted(e.env.captures)[-1]+'.capture.json')
        bad = b'{malformed final candidate\n'
        path.write_bytes(bad)
        before = dict(E._EVALUATED)
        with patch.object(E, 'evaluate_capture_json', side_effect=AssertionError('partial evaluation')):
            result = finalize(e)
        assert result.status == 'RAW_ARCHIVED' and result.bundle_digest is None
        assert E._EVALUATED == before and path.read_bytes() == bad
        raw = archived(e, result)
        assert bad in role_bytes(raw, 'capture') and raw.backup_verified
        assert not any(f.role == 'evaluation_record' for f in raw.manifest.files)


def test_last_receipt_corruption_and_missing_log_are_preserved_before_refusal():
    for value in (b'{truncated-last-receipt', b''):
        with fixture() as e:
            bad = e.env.receipt_log+value if value else b''
            e.paths['source_receipts'][0].write_bytes(bad)
            before = dict(E._EVALUATED)
            with patch.object(E, 'evaluate_capture_json', side_effect=AssertionError('evaluation forbidden')):
                result = finalize(e)
            assert result.status == 'RAW_ARCHIVED' and E._EVALUATED == before
            assert role_bytes(archived(e, result), 'source_receipts') == (bad,)


def test_recorded_abort_differs_from_truncation_and_keeps_actual_incomplete_snapshots():
    for truncate in (False, True):
        with fixture(aborted=True) as e:
            if truncate:
                e.paths['source_receipts'][0].write_bytes(e.env.receipt_log[:-1])
            with patch.object(E, 'evaluate_capture_json', side_effect=AssertionError('evaluation forbidden')):
                result = finalize(e)
            assert result.status == 'RAW_ARCHIVED'
            assert result.reasons[0] == ('STUDY_RECEIPTS_LOG_INCOMPLETE' if truncate else 'STUDY_RECEIPTS_CAPTURE_ABORTED')
            raw = archived(e, result)
            assert set(role_bytes(raw, 'incomplete_capture')) == set(e.env.captures.values())
            assert not raw.manifest.inventory_complete
            assert any(row.status == 'MISSING' and row.role == 'capture' for row in raw.manifest.observed_inputs)


def test_source_program_prior_and_commitment_mismatches_keep_originals_and_never_issue():
    for role in ('source_file', 'program_source', 'prior_research', 'registration_commitment'):
        with fixture() as e:
            path = e.paths[role][-1]
            original = path.read_bytes()+b'\nchanged exact original bytes\n'
            path.write_bytes(original)
            with patch.object(E, 'evaluate_capture_json', side_effect=AssertionError('evaluation forbidden')):
                result = finalize(e)
            assert result.status == 'RAW_ARCHIVED'
            assert original in role_bytes(archived(e, result), role)


def test_historical_source_mismatch_still_archives_unknown_plan_and_all_read_bytes():
    with fixture() as e:
        actual = S._fixed_file
        def changed(relative):
            body = actual(relative)
            return body+b'\nsource changed\n' if relative == S.PROGRAM_SOURCE else body
        with patch.object(S, '_fixed_file', side_effect=changed), \
             patch.object(E, 'evaluate_capture_json', side_effect=AssertionError('evaluation forbidden')):
            result = finalize(e)
        assert result.status == 'RAW_ARCHIVED'
        raw = archived(e, result)
        assert raw.manifest.expected_candidates is None
        assert role_bytes(raw, 'plan') == (e.paths['plan'][0].read_bytes(),)
        assert set(role_bytes(raw, 'capture')) == set(e.env.captures.values())


def test_sealed_inspection_survives_source_change_but_current_evaluation_refuses():
    with fixture() as e:
        result = finalize(e)
        assert result.status == 'VERIFIED_UNAPPROVED', result.reasons
        actual = S._fixed_file
        def changed(relative):
            body = actual(relative)
            return body+b'\nsource changed\n' if relative == S.PROGRAM_SOURCE else body
        with patch.object(S, '_fixed_file', side_effect=changed), \
             patch.object(E, 'evaluate_capture_json', side_effect=AssertionError('evaluation forbidden')):
            assert e.store.inspect(result.bundle_digest).kind == 'VERIFIED_UNAPPROVED'
            assert e.store.read_verified(result.bundle_digest).backup_verified
            refused(lambda:R.evaluate_sealed_study(e.store, result.bundle_digest))


def test_missing_symlink_unreadable_and_oversized_inputs_are_distinct_opaque_observations():
    with fixture() as e:
        good = e.work/'small.md'; good.write_bytes(b'original')
        missing = e.work/'missing.md'
        linked = e.work/'alias.md'; linked.symlink_to(good)
        huge = e.work/'huge.md'; huge.write_bytes(b'x'*(e.store.limits.format_limits.max_file_bytes+1))
        denied = e.work/'denied.md'; denied.write_bytes(b'not read')
        inputs = R.StudyBundleInputs(files=tuple(R.BundleInputFile(role='report', path=p)
            for p in (good, missing, linked, huge, denied)), captures_directory=e.captures)
        actual_open = os.open
        def open_(path, *args, **kwargs):
            if str(path) in ('denied.md', str(denied)):
                raise PermissionError('synthetic')
            return actual_open(path, *args, **kwargs)
        with patch.object(R.os, 'open', side_effect=open_):
            raw, payloads = snapshot(e, inputs)
        observed = {row.original_name:row.status for row in raw.observed_inputs}
        assert observed['small.md'] == 'COLLECTED' and observed['missing.md'] == 'MISSING'
        assert observed['alias.md'] == observed['denied.md'] == 'REFUSED'
        assert observed['huge.md'] == 'LIMIT_EXCEEDED'
        receipt = e.store.archive_raw(F.raw_archive_bytes(raw), payloads)
        assert e.store.read_raw(receipt.bundle_digest).backup_verified
        assert good.read_bytes() == b'original' and huge.stat().st_size == e.store.limits.format_limits.max_file_bytes+1


def test_inventory_and_object_chunk_limits_preserve_already_read_originals():
    for kind in ('inventory', 'chunk'):
        policy = limits()
        if kind == 'inventory':
            policy = replace(policy, format_limits=replace(policy.format_limits, max_files=4))
        else:
            policy = replace(policy, object_limits=O.ObjectLimits(chunk_bytes=1024, max_payload_bytes=1024*1024,
                max_chunks=10, max_manifest_bytes=65536))
        with fixture(storage_limits=policy) as e:
            names = []
            for i in range(5 if kind == 'inventory' else 2):
                path = e.work/('input-%d.md'%i)
                path.write_bytes(b'first original' if i == 0 else b'x'*(11*1024 if kind == 'chunk' else 8))
                names.append(R.BundleInputFile(role='report', path=path))
            # Empty inventory ensures this case isolates explicit-file admission.
            shutil.rmtree(e.captures); e.captures.mkdir()
            raw, payloads = snapshot(e, R.StudyBundleInputs(files=tuple(names), captures_directory=e.captures))
            assert b'first original' in payloads.values()
            assert not raw.inventory_complete and any(row.status == 'LIMIT_EXCEEDED' for row in raw.observed_inputs)
            receipt = e.store.archive_raw(F.raw_archive_bytes(raw, limits=policy.format_limits), payloads)
            assert b'first original' in e.store.read_raw(receipt.bundle_digest).files.values()


def test_object_manifest_limit_is_resource_but_arbitrary_preview_error_is_not_hidden():
    with fixture() as e:
        path = e.work/'display.md'; path.write_bytes(b'two bytes exceed this synthetic object manifest budget')
        inputs = R.StudyBundleInputs(files=(R.BundleInputFile(role='report', path=path),), captures_directory=e.captures)
        actual = e.store.preview_payload
        def limited(raw):
            if raw == path.read_bytes():
                raise O.EvidenceObjectError('EVIDENCE_OBJECT_LIMIT_EXCEEDED')
            return actual(raw)
        with patch.object(e.store, 'preview_payload', side_effect=limited):
            raw, payloads = snapshot(e, inputs)
        assert any(row.original_name == path.name and row.status == 'LIMIT_EXCEEDED' for row in raw.observed_inputs)
        assert path.read_bytes() not in payloads.values()
        with patch.object(e.store, 'preview_payload', side_effect=O.EvidenceObjectError('EVIDENCE_OBJECT_INPUT_INVALID')):
            refused(lambda:snapshot(e, inputs), 'EVIDENCE_OBJECT_INPUT_INVALID')


def test_single_handle_reader_rejects_a_b_a_swap_before_read():
    with fixture() as e:
        path = e.work/'swap.md'; path.write_bytes(b'AAAA')
        replacement = e.work/'replacement.md'; replacement.write_bytes(b'BBBB')
        held = e.work/'held.md'
        actual_open = os.open
        swapped = []
        def open_(name, *args, **kwargs):
            if str(name) in ('swap.md', str(path)) and not swapped:
                path.rename(held); replacement.rename(path)
                descriptor = actual_open(name, *args, **kwargs)
                path.rename(replacement); held.rename(path)
                swapped.append(True)
                return descriptor
            return actual_open(name, *args, **kwargs)
        with patch.object(R.os, 'open', side_effect=open_):
            raw, status = R._read_snapshot(path, 1024)
        assert swapped and raw is None and status == 'REFUSED'
        assert path.read_bytes() == b'AAAA' and replacement.read_bytes() == b'BBBB'


def test_changed_during_read_keeps_exact_read_bytes_and_separate_incident():
    with fixture() as e:
        path = e.work/'changed.md'; path.write_bytes(b'AAAA')
        actual_fdopen = os.fdopen
        class ChangingHandle:
            def __init__(self, handle): self.handle = handle
            def __enter__(self): return self
            def __exit__(self, *args): return self.handle.__exit__(*args)
            def fileno(self): return self.handle.fileno()
            def read(self, maximum):
                raw = self.handle.read(maximum)
                path.write_bytes(b'BBBB changed size')
                return raw
        def fdopen(fd, *args, **kwargs):
            return ChangingHandle(actual_fdopen(fd, *args, **kwargs))
        inputs = R.StudyBundleInputs(files=(R.BundleInputFile(role='report', path=path),), captures_directory=e.captures)
        # Limit injection to the first explicit reader, not the later capture files.
        with patch.object(R.os, 'fdopen', side_effect=fdopen):
            raw, payloads = snapshot(e, inputs)
        assert b'AAAA' in payloads.values()
        assert any(row.original_name == 'changed.md' and row.status == 'COLLECTED' for row in raw.observed_inputs)
        assert any(row.status == 'CHANGED' for row in raw.observed_inputs)
        assert not raw.inventory_complete


def test_counterfeit_stored_manifest_is_not_an_issued_result_or_manifest_approval():
    with fixture() as e:
        result = finalize(e)
        assert result.status == 'VERIFIED_UNAPPROVED', result.reasons
        original = e.store.read_verified(result.bundle_digest)
        fake = replace(original.manifest, revision_id='forged-summary', candidates=tuple(
            replace(row, result_digest='a'*64) for row in original.manifest.candidates))
        receipt = e.store.commit_verified(F.verified_bundle_bytes(fake), original.files)
        assert receipt.backup_verified  # storage graph is real, research claim is counterfeit
        refused(lambda:R.evaluate_sealed_study(e.store, receipt.bundle_digest), 'BUNDLE_REPRODUCTION_MISMATCH')
        refused(lambda:R.evaluate_sealed_study(original, result.bundle_digest), 'BUNDLE_STORE_REQUIRED')
        fake_audit = ReceiptAudit(plan_digest='a'*64, receipt_log_sha256='b'*64,
            capture_digests=(('study-a','c'*64),), slot_count=1, receipt_count=1)
        refused(lambda:R.finalize_study_bundle(fake_audit, e.store, run_id='forged', raw_revision_id='raw-v2',
            verified_revision_id='verified-v2', attempt_id='fake-a', evaluated_at=e.at), 'BUNDLE_INPUTS_FORMAT_INVALID')
        assert not result.manifest_authenticated and result.reasons == ('BUNDLE_MANIFEST_AUTHENTICATION_REQUIRED',)
        refused(lambda:R.evaluate_sealed_study(e.store, result.input_archive_digest))


def test_runtime_never_initializes_head_and_explicit_operator_refuses_existing_or_partial_store():
    with fixture(provision=False) as e:
        before = {path.relative_to(e.base):path.read_bytes() for path in e.base.rglob('*') if path.is_file()}
        code, output = invoke(R, 'provision')
        assert code == 2 and output['reasons'] == ['BUNDLE_OPERATOR_PROVISION_REQUIRED']
        refused(lambda:finalize(e))
        after = {path.relative_to(e.base):path.read_bytes() for path in e.base.rglob('*') if path.is_file()}
        assert before == after
        genesis = OWNER.provision_research_store(e.store)
        assert genesis == e.store.head.read()
        refused(lambda:OWNER.provision_research_store(e.store), 'BUNDLE_STORE_ALREADY_PROVISIONED')
    with fixture(provision=False) as e:
        partial = e.store.roots.sealed_root/'partial'; partial.write_bytes(b'preserve interrupted storage')
        refused(lambda:OWNER.provision_research_store(e.store), 'BUNDLE_STORE_PATH_REFUSED')
        assert partial.read_bytes() == b'preserve interrupted storage' and not e.store.head._dir.exists()


def test_cli_explicit_operator_finalize_inspect_and_sealed_evaluate_keep_non_authority_status():
    with fixture(provision=False) as e:
        configuration = e.base/'limits.json'; configuration.write_text(json.dumps(asdict(e.store.limits)))
        input_path = e.base/'inputs.json'; input_path.write_text(json.dumps({'schema_version':1,
            'files':[dict(role=i.role,path=str(i.path),source_name=i.source_name,required=i.required) for i in e.inputs.files],
            'captures_directory':str(e.captures)}))
        common = ('--sealed-root', str(e.store.roots.sealed_root), '--backup-root', str(e.store.roots.backup_root),
                  '--head-name','bundle-head','--limits',str(configuration))
        code, output = invoke(OWNER, 'provision', *common)
        assert code == 0 and output['status'] == 'EMPTY_STORE_PROVISIONED' and not output['manifest_authenticated']
        code, output = invoke(R, 'finalize', *common, '--inputs',str(input_path), '--run-id','cli-run',
            '--raw-revision','raw-v1','--verified-revision','verified-v1','--attempt-id','attempt-a',
            '--evaluated-at',e.at.isoformat())
        assert code == 0 and output['status'] == 'VERIFIED_UNAPPROVED', output
        digest = output['bundle_digest']
        shutil.rmtree(e.work)
        for command, status in (('inspect','VERIFIED_UNAPPROVED'),('evaluate','REEVALUATED_UNAPPROVED')):
            code, output = invoke(R, command, *common, '--digest',digest)
            assert code == 0 and output['status'] == status and not output['execution_ready']
            assert not output['manifest_authenticated']
            assert output['reasons'] == ['BUNDLE_MANIFEST_AUTHENTICATION_REQUIRED']
        code, output = invoke(R, 'evaluate', '--digest',digest)
        assert code == 2 and output['reasons'] == ['BUNDLE_ARGUMENTS_REQUIRED']


def test_required_flag_casefold_collision_and_unsafe_names_are_archived_before_zero_evaluation_refusal():
    for kind in ('required', 'collision', 'unsafe'):
        with fixture() as e:
            if kind == 'required':
                e.inputs = replace(e.inputs, files=(replace(e.inputs.files[0], required=False),)+e.inputs.files[1:])
            else:
                path = e.work/('REPORT.md' if kind == 'collision' else 'CON.md')
                path.write_bytes(b'display-only original is retained even with invalid metadata')
                e.inputs = replace(e.inputs, files=e.inputs.files+(R.BundleInputFile(role='report', path=path),))
            before = dict(E._EVALUATED)
            with patch.object(E, 'evaluate_capture_json', side_effect=AssertionError('metadata must preflight')):
                result = finalize(e)
            assert result.status == 'RAW_ARCHIVED' and result.reasons[0] == 'BUNDLE_FORMAT_INVALID'
            assert E._EVALUATED == before
            raw = archived(e, result)
            assert raw.backup_verified
            if kind == 'required':
                assert any(file.role == 'plan' and not file.required for file in raw.manifest.files)
            else:
                assert path.read_bytes() in role_bytes(raw, 'report')
