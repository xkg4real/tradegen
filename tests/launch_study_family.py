"""Whole-family CLI admission over invented captures and temporary directories."""
from contextlib import contextmanager
from dataclasses import replace
from datetime import timedelta
import hashlib
import json
import os
from pathlib import Path
import tempfile
from unittest.mock import patch

from execution_launch import strategy as E, study as S, study_evidence as SE
from execution_launch.paper_capture import capture_json
from execution_launch.profile import profile_body
from tests import compliance_fixtures as CF, launch_study as F


@contextmanager
def fixture():
    saved = dict(E._EVALUATED)
    E._EVALUATED.clear()
    try:
        plan = F.plan()
        outcome = F.Driver(plan).run()
        assert outcome.complete
        raw = {candidate.protocol.study_id: capture_json(archive).encode('ascii')
               for candidate, archive in zip(plan.candidates, outcome.archives)}
        now = plan.candidates[0].protocol.capture_end + timedelta(seconds=60)
        with tempfile.TemporaryDirectory(prefix='tradegen_family_cli_') as name:
            root = Path(name)
            captures = root / 'captures'
            captures.mkdir()
            for identifier, body in raw.items():
                (captures / (identifier+'.capture.json')).write_bytes(body)
            yield plan, F.profile(), raw, now, root, captures
    finally:
        E._EVALUATED.clear()
        E._EVALUATED.update(saved)


def no_issue(call, code=None):
    before = dict(E._EVALUATED)
    with patch.object(E, 'evaluate_capture_json', side_effect=AssertionError('evaluation before complete admission')):
        try:
            call()
        except ValueError as exc:
            if code is not None:
                assert str(exc) == code, (str(exc), code)
        else:
            raise AssertionError('incomplete family accepted')
    assert E._EVALUATED == before


def test_later_missing_extra_and_case_aliased_capture_all_refuse_before_any_issuance():
    for mode in ('missing', 'extra', 'case_alias'):
        with fixture() as (plan, profile, raw, now, _, directory):
            last = next(reversed(raw))
            original = directory/(last+'.capture.json')
            if mode == 'missing':
                original.unlink()
            elif mode == 'extra':
                (directory/'unregistered.capture.json').write_bytes(b'{}')
            else:
                original.rename(directory/(last+'.CAPTURE.JSON'))
            before = {path.name: path.read_bytes() for path in directory.iterdir()}
            no_issue(lambda: S._select(plan, profile, directory, now), 'STUDY_CAPTURE_FAMILY_INCOMPLETE')
            assert {path.name: path.read_bytes() for path in directory.iterdir()} == before


def test_last_candidate_last_frame_prefix_registry_and_duplicate_key_damage_issue_nothing():
    for mode in ('last_frame', 'last_prefix', 'registry', 'duplicate_key'):
        with fixture() as (plan, profile, raw, now, _, directory):
            last = next(reversed(raw))
            body = json.loads(raw[last])
            if mode == 'last_frame':
                body['bars'][-1]['source_sha256'] = 'damaged-original'
            elif mode == 'last_prefix':
                body['decisions'][-1]['history_sha256'] = 'f'*64
            elif mode == 'registry':
                body['registry'][-1]['protocol_digest'] = 'e'*64
            changed = json.dumps(body).encode('ascii')
            if mode == 'duplicate_key':
                changed = b'{"source_kind":"synthetic",'+changed[1:]
            (directory/(last+'.capture.json')).write_bytes(changed)
            no_issue(lambda: S._select(plan, profile, directory, now))
            assert (directory/(last+'.capture.json')).read_bytes() == changed


def test_complete_family_keeps_numerical_losers_and_raw_whitespace_while_ignoring_reports():
    with fixture() as (plan, profile, raw, now, _, directory):
        last = next(reversed(raw))
        raw[last] += b' \n'
        (directory/(last+'.capture.json')).write_bytes(raw[last])
        (directory/'receipts.jsonl').write_bytes(b'invented receipt log; not a capture')
        (directory/'report.json').write_bytes(b'{"display_only":true}')
        (directory/'notes.md').write_bytes(b'invented report')
        read = S.load_capture_family(plan, directory)
        assert read == raw
        issued = []
        real = S.evaluate_study_family

        def record(*args, **kwargs):
            value = real(*args, **kwargs)
            issued.append(value)
            return value

        with patch.object(S, 'evaluate_study_family', new=record):
            selection, evaluation, requests = S._select(plan, profile, directory, now)
        assert len(issued) == 1 and len(issued[0].rows) == len(plan.candidates)
        assert evaluation == {identifier: 'EVALUATED' for identifier in raw}
        assert issued[0].capture_digests == {identifier: hashlib.sha256(body).hexdigest() for identifier, body in raw.items()}
        assert all(row.raw_capture == raw[row.study_id] for row in issued[0].rows)
        assert all(not row.math_qualified for row in selection.rows)
        assert selection.status == 'NO_QUALIFIED_MARKET' and not requests


def test_private_or_linked_directory_is_refused_before_inventory_or_capture_read():
    with fixture() as (plan, _, _, _, root, directory):
        linked = root/'alias'
        CF.directory_link(linked, directory)
        for path in (root/'.tradegen'/'captures', root/'.env'/'captures', linked, root/'missing'):
            with (patch.object(S, '_capture_names', side_effect=AssertionError('inventory accessed')),
                  patch.object(S, '_read_file', side_effect=AssertionError('capture accessed'))):
                no_issue(lambda: S.load_capture_family(plan, path), 'STUDY_CAPTURE_DIRECTORY_REFUSED')


def test_extra_candidate_appearing_during_read_is_detected_before_evaluation():
    with fixture() as (plan, profile, _, now, _, directory):
        actual_read = S._read_file
        calls = []

        def read(path, maximum):
            value = actual_read(path, maximum)
            calls.append(path)
            if len(calls) == 1:
                (directory/'new.capture.json').write_bytes(b'{}')
            return value

        with patch.object(S, '_read_file', new=read):
            no_issue(lambda: S._select(plan, profile, directory, now), 'STUDY_CAPTURE_FAMILY_INCOMPLETE')
        assert (directory/'new.capture.json').read_bytes() == b'{}'


def test_total_capture_byte_boundary_is_checked_before_shared_evaluation():
    with fixture() as (plan, profile, raw, now, _, directory):
        total = sum(map(len, raw.values()))
        with patch.object(S, 'DEFAULT_LIMITS', replace(SE.DEFAULT_LIMITS, max_total_bytes=total)):
            assert S.load_capture_family(plan, directory) == raw
        with patch.object(S, 'DEFAULT_LIMITS', replace(SE.DEFAULT_LIMITS, max_total_bytes=total-1)):
            no_issue(lambda: S._select(plan, profile, directory, now), 'STUDY_EVIDENCE_RESOURCE_LIMIT')


def test_cli_missing_later_candidate_reports_whole_research_hold_without_partial_evaluations():
    with fixture() as (plan, profile, raw, now, root, directory):
        plan_path, profile_path = root/'plan.json', root/'profile.json'
        plan_path.write_text(S.study_plan_json(plan), encoding='utf-8', newline='')
        profile_path.write_text(json.dumps(profile_body(profile)), encoding='utf-8', newline='')
        (directory/(next(reversed(raw))+'.capture.json')).unlink()
        before = dict(E._EVALUATED)
        with patch.object(E, 'evaluate_capture_json', side_effect=AssertionError('partial evaluation')):
            code, report, output = F.invoke('select', '--plan', str(plan_path), '--profile', str(profile_path),
                '--captures', str(directory), '--now', now.isoformat())
        assert code == 2 and not report['workflow_complete'] and not report['execution_ready']
        assert report['reasons'] == ['STUDY_CAPTURE_FAMILY_INCOMPLETE']
        assert 'evaluation' not in report and 'selection' not in report and not report.get('review_requests')
        assert E._EVALUATED == before and str(root) not in output and F.SCOPE not in output


def test_actual_oversized_regular_capture_is_resource_admission_without_reading_or_changing_it():
    with fixture() as (plan, profile, raw, now, _, directory):
        target = directory/(next(iter(raw))+'.capture.json')
        original = b' ' * (16*1024*1024+1)
        target.write_bytes(original)
        assert target.stat().st_size == SE.DEFAULT_LIMITS.max_capture_bytes+1
        with patch.object(S, '_read_file', side_effect=AssertionError('oversized capture was read')):
            no_issue(lambda: S._select(plan, profile, directory, now), 'STUDY_EVIDENCE_RESOURCE_LIMIT')
        assert target.read_bytes() == original


def test_oversized_symlink_and_open_failure_keep_file_refusals_instead_of_resource_classification():
    with fixture() as (plan, profile, raw, now, _, directory):
        target = directory/(next(iter(raw))+'.capture.json')
        original = b' ' * (16*1024*1024+1)
        oversized = directory/'retained-source.bin'
        oversized.write_bytes(original)
        target.unlink()
        target.symlink_to(oversized)
        no_issue(lambda: S._select(plan, profile, directory, now), 'WORKFLOW_FILE_REFUSED')
        assert target.is_symlink() and oversized.read_bytes() == original
    with fixture() as (plan, profile, raw, now, _, directory):
        target = directory/(next(iter(raw))+'.capture.json')
        original = b' ' * (16*1024*1024+1)
        target.write_bytes(original)
        real_open = os.open

        def denied(path, *args, **kwargs):
            if str(path) in (target.name, str(target)):
                raise PermissionError('synthetic denied open')
            return real_open(path, *args, **kwargs)

        with (patch.object(S.os, 'open', new=denied),
              patch.object(S.os, 'supports_dir_fd', os.supports_dir_fd | {denied})):
            no_issue(lambda: S._select(plan, profile, directory, now), 'WORKFLOW_FILE_UNAVAILABLE_OR_REFUSED')
        assert target.read_bytes() == original


def test_capture_replaced_after_open_is_not_misclassified_as_an_oversized_resource_limit():
    with fixture() as (plan, profile, raw, now, _, directory):
        target = directory/(next(iter(raw))+'.capture.json')
        original = b' ' * (16*1024*1024+1)
        target.write_bytes(original)
        retained = directory/'original-retained.bin'
        real_open, changed = os.open, []

        def replaced(path, *args, **kwargs):
            fd = real_open(path, *args, **kwargs)
            if not changed and str(path) in (target.name, str(target)):
                target.rename(retained)
                target.write_bytes(b'replacement')
                changed.append(True)
            return fd

        with (patch.object(S.os, 'open', new=replaced),
              patch.object(S.os, 'supports_dir_fd', os.supports_dir_fd | {replaced})):
            no_issue(lambda: S._select(plan, profile, directory, now), 'WORKFLOW_FILE_REFUSED')
        assert changed and target.read_bytes() == b'replacement' and retained.read_bytes() == original
