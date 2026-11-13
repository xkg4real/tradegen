"""Existing-only Journal regressions on explicitly provisioned temporary state.

These are finite path/byte checks, not filesystem leases or native-Windows proof.
The ordinary default Journal is the test operator's explicit provisioning step.
"""
import builtins
from contextlib import contextmanager
from pathlib import Path
import shutil
import threading
from unittest.mock import patch

from execution_control import store as S
from tests.control_store import _home, NOW


def refused(call, expected=None):
    try:
        call()
    except S.JournalError as exc:
        if expected is not None:
            assert str(exc) == expected, str(exc)
        return
    raise AssertionError('expected existing-journal refusal')


def events(journal):
    with journal.transaction() as tx:
        return tx.events


def tree(root):
    return {p.relative_to(root).as_posix():p.read_bytes()
            for p in root.rglob('*') if p.is_file()} if root.exists() else {}


def provision(journal, *, row=False):
    with journal.transaction() as tx:
        if row:
            tx.append('reserved', {'client_id':'fixture','n':1}, now=NOW)
    return S.Journal(journal._root, require_existing=True)


def test_existing_mode_is_exact_bool_and_invalid_admission_has_no_filesystem_effect():
    with _home() as (home, _):
        before = tree(home)
        for value in (None, 0, 1, '', 'true', [], object()):
            refused(lambda value=value:S.Journal(require_existing=value),'control existing mode must be bool')
        assert tree(home) == before


def test_existing_mode_flag_and_property_reject_normal_reassignment_and_deletion():
    with _home() as (_, journal):
        for actual in (journal,S.Journal(require_existing=False),S.Journal(require_existing=True)):
            expected = actual.requires_existing
            for name in ('_require_existing','requires_existing'):
                for action in (lambda name=name:setattr(actual,name,not expected),
                               lambda name=name:delattr(actual,name)):
                    try:
                        action()
                    except AttributeError:
                        pass
                    else:
                        raise AssertionError('construction mode changed')
                assert actual.requires_existing is expected
            # No general freezing of the pre-existing Journal object API.
            actual.fixture_note = 'unchanged'; assert actual.fixture_note == 'unchanged'
            del actual.fixture_note


def test_missing_root_refuses_transaction_snapshot_load_and_anchor_without_creating_files():
    with _home() as (home, _):
        strict = S.Journal(require_existing=True)
        root = strict._root
        assert not root.exists()
        for call in (lambda:events(strict),strict.snapshot,lambda:strict._load(initialize=True),
                     lambda:strict._anchor(0,S.GENESIS,0)):
            refused(call)
            assert not root.exists() and tree(home) == {}


def test_missing_existing_lock_never_recreates_it_or_changes_the_valid_pair():
    with _home() as (home, journal):
        strict = provision(journal,row=True)
        (strict._root/'control.lock').unlink()
        before = tree(home)
        refused(lambda:events(strict))
        refused(strict.snapshot)
        refused(lambda:strict._load(initialize=True))
        assert tree(home) == before and not (strict._root/'control.lock').exists()


def test_both_missing_files_cannot_be_seeded_by_private_load_or_transaction():
    with _home() as (home,journal):
        strict = provision(journal)
        for name in ('journal.jsonl','checkpoint.json'):
            (strict._root/name).unlink()
        before = tree(home)
        for call in (lambda:strict._load(),lambda:strict._load(initialize=True),lambda:events(strict)):
            refused(call)
            assert tree(home) == before
        assert set(p.name for p in strict._root.iterdir()) == {'control.lock'}


def test_partial_pair_empty_checkpoint_and_torn_tail_are_preserved_without_repair():
    for damage in ('journal.jsonl','checkpoint.json','empty-anchor','torn-tail'):
        with _home() as (home,journal):
            strict = provision(journal,row=True)
            if damage in ('journal.jsonl','checkpoint.json'):
                (strict._root/damage).unlink()
            elif damage == 'empty-anchor':
                (strict._root/'checkpoint.json').write_bytes(b'')
            else:
                target = strict._root/'journal.jsonl'
                target.write_bytes(target.read_bytes()+b'{"unfinished":')
            before = tree(home)
            refused(lambda:events(strict)); refused(strict.snapshot)
            assert tree(home) == before


def test_snapshot_then_deleted_root_does_not_authorize_transaction_recreation():
    with _home() as (home,journal):
        strict = provision(journal,row=True)
        assert len(strict.snapshot()) == 1
        shutil.rmtree(strict._root)
        refused(lambda:events(strict))
        assert not strict._root.exists() and tree(home) == {}


def test_deleted_pair_or_lock_during_transaction_poison_append_without_recreation():
    for missing in (('journal.jsonl',),('checkpoint.json',),('control.lock',),
                    ('journal.jsonl','checkpoint.json')):
        with _home() as (home,journal):
            strict = provision(journal,row=True)
            with strict.transaction() as tx:
                for name in missing:
                    (strict._root/name).unlink()
                before = tree(home)
                refused(lambda:tx.append('dispatching',{'client_id':'fixture'},now=NOW),
                        'control append failed; reconciliation required')
                refused(lambda:tx.events,'control transaction is closed or failed')
                assert tree(home) == before
            for name in missing:
                assert not (strict._root/name).exists()


def test_deleted_journal_after_load_before_existing_open_is_not_recreated():
    with _home() as (home,journal):
        strict = provision(journal,row=True)
        real_open, triggered = builtins.open, []
        def raced_open(path,mode='r',*args,**kwargs):
            if Path(path) == strict._root/'journal.jsonl' and mode == 'r+b':
                Path(path).unlink(); triggered.append(True)
            return real_open(path,mode,*args,**kwargs)
        with strict.transaction() as tx:
            anchor = (strict._root/'checkpoint.json').read_bytes()
            with patch.object(S,'open',raced_open,create=True):
                refused(lambda:tx.append('dispatching',{},now=NOW),'control append failed; reconciliation required')
            assert triggered == [True] and not (strict._root/'journal.jsonl').exists()
            assert (strict._root/'checkpoint.json').read_bytes() == anchor
        assert not any(p.name.startswith('.checkpoint.') for p in strict._root.iterdir())


def test_deleted_checkpoint_after_load_before_write_preserves_original_journal():
    with _home() as (_,journal):
        strict = provision(journal,row=True)
        original = (strict._root/'journal.jsonl').read_bytes()
        real_open = builtins.open
        def raced_open(path,mode='r',*args,**kwargs):
            if Path(path) == strict._root/'journal.jsonl' and mode == 'r+b':
                (strict._root/'checkpoint.json').unlink()
            return real_open(path,mode,*args,**kwargs)
        with strict.transaction() as tx:
            with patch.object(S,'open',raced_open,create=True):
                refused(lambda:tx.append('dispatching',{},now=NOW),'control append failed; reconciliation required')
        assert (strict._root/'journal.jsonl').read_bytes() == original
        assert not (strict._root/'checkpoint.json').exists()


def test_size_and_same_size_byte_changes_before_write_are_not_overwritten():
    for same_size in (False,True):
        with _home() as (_,journal):
            strict = provision(journal,row=True)
            path = strict._root/'journal.jsonl'; prior = path.read_bytes()
            changed = prior.replace(b'"n":1',b'"n":2') if same_size else prior+b'\n'
            assert changed != prior
            real_open = builtins.open
            def raced_open(target,mode='r',*args,**kwargs):
                if Path(target) == path and mode == 'r+b':
                    path.write_bytes(changed)
                return real_open(target,mode,*args,**kwargs)
            with strict.transaction() as tx:
                with patch.object(S,'open',raced_open,create=True):
                    refused(lambda:tx.append('dispatching',{},now=NOW),'control append failed; reconciliation required')
            assert path.read_bytes() == changed and b'"kind":"dispatching"' not in changed
            refused(strict.snapshot)


def test_anchor_deletion_after_durable_row_keeps_uncertain_tail_without_reseeding():
    with _home() as (_,journal):
        strict = provision(journal,row=True)
        original_anchor = strict._anchor
        def delete_anchor(*args,**kwargs):
            (strict._root/'checkpoint.json').unlink()
            return original_anchor(*args,**kwargs)
        with strict.transaction() as tx:
            with patch.object(strict,'_anchor',delete_anchor):
                refused(lambda:tx.append('dispatching',{},now=NOW),'control append failed; reconciliation required')
            refused(lambda:tx.append('rejected',{},now=NOW),'control transaction is closed or failed')
        assert not (strict._root/'checkpoint.json').exists()
        assert b'"kind":"dispatching"' in (strict._root/'journal.jsonl').read_bytes()
        refused(strict.snapshot)


def test_anchor_deletion_during_temporary_checkpoint_write_is_not_adopted_or_cleaned():
    with _home() as (_,journal):
        strict = provision(journal,row=True)
        real_open = builtins.open
        @contextmanager
        def raced_open(path,mode='r',*args,**kwargs):
            with real_open(path,mode,*args,**kwargs) as handle:
                yield handle
            if Path(path).name.startswith('.checkpoint.') and mode == 'xb':
                (strict._root/'checkpoint.json').unlink()
        with strict.transaction() as tx:
            with patch.object(S,'open',raced_open,create=True):
                refused(lambda:tx.append('dispatching',{},now=NOW),'control append failed; reconciliation required')
        assert not (strict._root/'checkpoint.json').exists()
        assert len(tuple(strict._root.glob('.checkpoint.*.tmp'))) == 1
        assert b'"kind":"dispatching"' in (strict._root/'journal.jsonl').read_bytes()
        refused(strict.snapshot)


def test_checkpoint_same_size_replacement_before_anchor_is_not_silently_overwritten():
    with _home() as (_,journal):
        strict = provision(journal,row=True)
        path = strict._root/'checkpoint.json'; original = path.read_bytes()
        changed = original.replace(b'"seq":1',b'"seq":2')
        assert len(changed) == len(original) and changed != original
        original_anchor = strict._anchor
        def replace_anchor(*args,**kwargs):
            path.write_bytes(changed)
            return original_anchor(*args,**kwargs)
        with strict.transaction() as tx:
            with patch.object(strict,'_anchor',replace_anchor):
                refused(lambda:tx.append('dispatching',{},now=NOW),'control append failed; reconciliation required')
        assert path.read_bytes() == changed
        refused(strict.snapshot)


def test_existing_only_append_matches_legacy_exact_journal_and_checkpoint_bytes():
    with _home() as (home,_):
        strict_operator = S.Journal(home/'strict-control')
        strict = provision(strict_operator)
        legacy = S.Journal(home/'legacy-control')
        payload = {'client_id':'same','nested':{'unicode':'가','escaped':'\\\n','values':[True,None,1]}}
        for journal in (legacy,strict):
            with journal.transaction() as tx:
                first = tx.append('reserved',payload,now=NOW)
                tx.append('dispatching',{'client_id':'same'},now=NOW)
            assert events(journal)[0] == first
        for name in ('journal.jsonl','checkpoint.json','control.lock'):
            assert (strict._root/name).read_bytes() == (legacy._root/name).read_bytes()
        before = tree(strict._root)
        assert len(strict.snapshot()) == 2 and tree(strict._root) == before


def test_default_and_explicit_false_still_initialize_missing_state_and_append():
    with _home() as (home,_):
        for journal in (S.Journal(home/'omitted'),S.Journal(home/'false',require_existing=False)):
            assert journal.requires_existing is False and not journal._root.exists()
            with journal.transaction() as tx:
                assert tx.events == ()
                tx.append('reserved',{},now=NOW)
            assert set(p.name for p in journal._root.iterdir()) == {'control.lock','journal.jsonl','checkpoint.json'}
            # Existing historical initialization semantics remain for default mode.
            (journal._root/'journal.jsonl').unlink(); (journal._root/'checkpoint.json').unlink()
            assert events(journal) == ()


def test_business_exception_does_not_roll_back_already_durable_strict_row():
    with _home() as (_,journal):
        strict = provision(journal)
        try:
            with strict.transaction() as tx:
                tx.append('reserved',{},now=NOW)
                raise ValueError('synthetic business refusal')
        except ValueError:
            pass
        else:
            raise AssertionError('business refusal swallowed')
        assert len(strict.snapshot()) == 1
        refused(lambda:tx.events,'control transaction is closed or failed')
        assert len(events(strict)) == 1


def test_durable_checkpoint_response_failure_is_preserved_for_fresh_replay():
    with _home() as (_,journal):
        strict = provision(journal)
        with strict.transaction() as tx:
            with patch.object(S,'_sync_directory',side_effect=OSError('synthetic cleanup failure')):
                refused(lambda:tx.append('reserved',{},now=NOW),'control append failed; reconciliation required')
            refused(lambda:tx.events,'control transaction is closed or failed')
        reopened = S.Journal(strict._root,require_existing=True)
        assert len(reopened.snapshot()) == 1
        with reopened.transaction() as tx:
            assert len(tx.events) == 1
            tx.append('dispatching',{},now=NOW)
        assert len(reopened.snapshot()) == 2


def test_strict_transactions_remain_thread_bound_non_nested_and_cleanup_after_failure():
    with _home() as (_,journal):
        strict = provision(journal)
        refused(lambda:S.Transaction(strict,[],0).append('reserved',{},now=NOW),
                'control transaction is closed or failed')
        with strict.transaction() as tx:
            refused(lambda:events(strict),'nested control transaction refused')
            refused(strict.snapshot,'nested control snapshot refused')
            outcomes = []
            def foreign_thread():
                try:
                    tx.append('reserved',{},now=NOW)
                except S.JournalError:
                    outcomes.append('refused')
            worker = threading.Thread(target=foreign_thread)
            worker.start(); worker.join(timeout=3)
            assert not worker.is_alive() and outcomes == ['refused'] and tx.events == ()
        assert events(strict) == ()


def test_lock_release_failure_does_not_revive_transaction_or_rollback_durable_row():
    with _home() as (_,journal):
        strict = provision(journal)
        original_lock = S._lock
        def fail_after_unlock(handle,acquire):
            original_lock(handle,acquire)
            if not acquire:
                raise OSError('synthetic unlock response failure')
        try:
            with patch.object(S,'_lock',fail_after_unlock):
                with strict.transaction() as tx:
                    tx.append('reserved',{},now=NOW)
        except OSError:
            pass
        else:
            raise AssertionError('cleanup failure concealed')
        refused(lambda:tx.events,'control transaction is closed or failed')
        assert len(events(strict)) == 1


def test_truncated_earlier_valid_prefix_remains_blocked_by_existing_checkpoint():
    with _home() as (_,journal):
        strict = provision(journal,row=True)
        with strict.transaction() as tx:
            tx.append('dispatching',{},now=NOW)
        path = strict._root/'journal.jsonl'
        earlier = path.read_bytes().splitlines(keepends=True)[0]
        path.write_bytes(earlier)
        refused(lambda:events(strict)); refused(strict.snapshot)
        assert path.read_bytes() == earlier
