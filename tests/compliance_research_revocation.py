"""Signed research restrictions in genuine temporary owner chains and contexts.

Only disposable Ed25519 keys and temporary homes are used. Provider checks use
the actual owner loader and D14 code approval. No source API, account or order.
Restart rollback tests distinguish a preserved trusted anchor from a fresh
in-memory provider; they do not claim detection of coherent rollback of all roots.
"""
from contextlib import contextmanager
from dataclasses import fields, replace
from datetime import datetime, timedelta, timezone
import base64
import json
import os
import stat
from types import SimpleNamespace
from unittest.mock import patch

from core.compliance import model as M, owner
from execution_control.owner_authority import CurrentOwnerAuthority, OwnerAuthorityError
from tests import compliance_fixtures as F

EVENT = 'research_attestation_revoked'
ARCHIVE = 'research_archive_manifest_attestation'
SOURCE = 'strategy_source_and_fixed_implementation_review'
CARRY = 'strategy_source_and_fixed_carry_implementation_review'
PURPOSES = frozenset({ARCHIVE,SOURCE,CARRY})
REASONS = frozenset({'OWNER_WITHDRAWN','EVIDENCE_UNTRUSTED','REVIEW_ERROR'})
FIELD = 'revoked_research_attestations'
NOW = datetime(2031,1,7,tzinfo=timezone.utc)


def data(purpose=ARCHIVE, target='a'*64, reason='OWNER_WITHDRAWN'):
    return dict(purpose=purpose,target_sha256=target,reason_code=reason)


@contextmanager
def signed_home(*, full=False):
    with F.temp_home() as home, F.pubkey_at(home/'owner_pubkey.pem'):
        if full:
            key = F.full_home(home,limits={'total_loss_floor_krw':10.0,'daily_loss_krw':1.0})
        else:
            key = F.owner_key(home)
            code_files = [list(row) for row in owner.code_files(owner.REPO_ROOT)]
            F.sign(key,'code_approved',{'sha256':owner.code_hash(owner.REPO_ROOT),'files':code_files})
        assert owner.home().is_relative_to(home) and owner.PUBKEY_PATH.is_relative_to(home)
        yield SimpleNamespace(home=home,key=key,public=key.public_key().public_bytes_raw())


def load(now=NOW):
    return owner.load_context(now,M.Positions(equity_krw=1.0))


def append(e, value=None, *, utc=None):
    return F.sign(e.key,EVENT,data() if value is None else value,
                  utc='2026-10-23T00:00:00Z' if utc is None else utc)


def refused(call, code=None):
    try:
        call()
    except (ValueError,TypeError,AttributeError) as exc:
        if code is not None:
            assert str(exc)==code,(str(exc),code)
        return
    raise AssertionError('invalid research restriction accepted')


def check(line,key=None):
    return owner.verify_log([line],(key or F.test_key()).public_key().public_bytes_raw(),[])


def historical_hash(context):
    """Independent pre-revocation projection; global canonical_json stays unchanged."""
    body={field.name:getattr(context,field.name) for field in fields(M.Context)
          if field.name not in ('ctx_hash','universe')}
    names=('status','reason','head','caps','limits','addresses','flags','halted_floors',
           'armed_sessions','session_acks','transfer_acks','fingerprint')
    body['owner']={name:getattr(context.owner,name) for name in names}
    return M.sha256_hex(M.canonical_json(body))


def test_research_revocation_is_a_signed_restriction_with_exact_independent_schema():
    assert EVENT in owner.OWNER_KINDS and EVENT not in owner.SYSTEM_KINDS
    assert set(owner._DATA[EVENT])=={'purpose','target_sha256','reason_code'}
    for purpose in PURPOSES:
        for reason in REASONS:
            value=data(purpose,reason=reason)
            assert owner._data_problem(EVENT,value)==''
            line=F.signed_entry(F.test_key(),1,owner.GENESIS_PREV,EVENT,value)
            result=check(line)
            assert result.ok and result.entries[0].signed and result.entries[0].data==value


def test_invalid_event_fields_fail_actual_signature_chain_schema_validation():
    values=[]
    for key in data():
        value=data();del value[key];values.append(value)
    values.append(data()|{'reset':True})
    for key,value in (('purpose','unknown'),('purpose',True),('purpose',None),
                       ('target_sha256','A'*64),('target_sha256','a'*63),('target_sha256',True),
                       ('reason_code',''),('reason_code','UNREVOKE'),('reason_code',False)):
        values.append(data()|{key:value})
    values.extend(([],None))
    for value in values:
        line=F.signed_entry(F.test_key(),1,owner.GENESIS_PREV,EVENT,value)
        result=check(line)
        assert not result.ok and not result.entries
    class Text(str): pass
    class Dictionary(dict): pass
    assert owner._data_problem(EVENT,data()|{'purpose':Text(ARCHIVE)})
    assert owner._data_problem(EVENT,Dictionary(data()))


def test_unsigned_wrong_key_wrong_domain_or_damaged_signature_cannot_restrict_verified_state():
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    key=F.test_key();other=Ed25519PrivateKey.from_private_bytes(bytes(range(1,33)))
    genuine=F.signed_entry(key,1,owner.GENESIS_PREV,EVENT,data())
    body=json.loads(genuine)
    wrong=dict(body,sig=base64.b64encode(key.sign(b'wrong-domain\n'+body['row_sha256'].encode())).decode())
    damaged=dict(body,sig=base64.b64encode(bytes(64)).decode())
    invalid=(F.signed_entry(None,1,owner.GENESIS_PREV,EVENT,data()),
             F.signed_entry(other,1,owner.GENESIS_PREV,EVENT,data()),
             (M.canonical_json(wrong)+'\n').encode(),(M.canonical_json(damaged)+'\n').encode())
    for line in invalid:
        result=check(line)
        assert not result.ok
        state=owner.owner_state(result,date=NOW.astimezone(M.KST).date(),now_utc=M.iso_utc(NOW),
            session_id=None,fingerprint_now=owner.fingerprint(key.public_key().public_bytes_raw()),first_recorded=None)
        assert not state.ok and state.revoked_research_attestations==frozenset()


def test_system_append_cannot_issue_the_owner_only_event():
    with signed_home() as e:
        before=owner.log_path().read_bytes()
        refused(lambda:owner.append_system_entry(EVENT,data(),NOW))
        assert owner.log_path().read_bytes()==before


def test_actual_loader_folds_all_purposes_duplicates_and_head_in_one_sealed_context():
    with signed_home() as e:
        for purpose in PURPOSES:
            append(e,data(purpose))
        append(e,data(ARCHIVE,reason='REVIEW_ERROR'))
        head=append(e,data(ARCHIVE,'b'*64))
        context=load()
        expected=frozenset({(purpose,'a'*64) for purpose in PURPOSES}|{(ARCHIVE,'b'*64)})
        assert context.owner.ok and context.code_signed and M.is_sealed(context)
        assert type(context.owner.revoked_research_attestations) is frozenset
        assert context.owner.revoked_research_attestations==expected
        assert context.owner.head==head and context.ctx_hash==M.context_hash(context)
        assert context.session==M.SessionState() and not context.owner.armed_sessions


def test_future_dated_restriction_applies_now_without_activating_future_code_approval():
    with signed_home() as e:
        future=M.iso_utc(NOW+timedelta(days=4))
        before=load()
        head=append(e,utc=future)
        F.other_code(e.key,utc=future)
        context=load()
        assert context.owner.revoked_research_attestations==frozenset({(ARCHIVE,'a'*64)})
        assert context.owner.head[0]==head[0]+1 and context.code_signed
        assert context.code_hash==before.code_hash
        later=load(NOW+timedelta(days=5))
        assert later.owner.ok and later.owner.revoked_research_attestations==context.owner.revoked_research_attestations
        assert not later.code_signed


def test_existing_loss_limits_halt_and_future_loosening_rules_are_unchanged():
    with signed_home(full=True) as e:
        owner.append_system_entry('system_halt',{'floor_krw':10.0},NOW)
        before=load()
        append(e,utc=M.iso_utc(NOW))
        F.sign(e.key,'limit_set',{'total_loss_floor_krw':1.0,'daily_loss_krw':100.0},utc=M.iso_utc(NOW+timedelta(days=3)))
        after=load()
        assert after.owner.ok and after.owner.revoked_research_attestations
        assert after.owner.limits==before.owner.limits and after.owner.halted_floors==before.owner.halted_floors
        assert after.owner.armed_sessions==before.owner.armed_sessions==frozenset()


def test_empty_field_keeps_exact_legacy_context_hash_without_global_json_changes():
    for state in (M.OwnerState(status='OK'),M.OwnerState.broken('fixture'),F.ctx().owner):
        context=F.ctx(owner=state)
        assert type(state.revoked_research_attestations) is frozenset and not state.revoked_research_attestations
        assert context.ctx_hash==historical_hash(context)==M.context_hash(context)
        assert FIELD in json.loads(M.canonical_json(state))  # Omission is only the Context hash projection.


def test_nonempty_pair_set_changes_context_hash_and_is_order_independent():
    old=F.ctx()
    pairs=((ARCHIVE,'b'*64),(SOURCE,'a'*64),(CARRY,'c'*64))
    one=F.ctx(owner=replace(old.owner,revoked_research_attestations=frozenset(pairs)))
    two=F.ctx(owner=replace(old.owner,revoked_research_attestations=frozenset(reversed(pairs))))
    assert one.ctx_hash==two.ctx_hash!=old.ctx_hash
    assert one.ctx_hash!=historical_hash(one)
    changed=F.ctx(owner=replace(old.owner,revoked_research_attestations=frozenset({(ARCHIVE,'a'*64)})))
    assert changed.ctx_hash not in (one.ctx_hash,old.ctx_hash)
    assert one.owner.head==old.owner.head and M.is_sealed(one)


def test_mutable_or_malformed_revocation_state_cannot_be_sealed_or_hashed_as_empty():
    invalid=(set(),[],{},None,False,((ARCHIVE,'a'*64),),frozenset({ARCHIVE}),
             frozenset({(ARCHIVE,)}),frozenset({(ARCHIVE,'a'*64,True)}),
             frozenset({('unknown','a'*64)}),frozenset({(ARCHIVE,'A'*64)}),frozenset({(ARCHIVE,True)}))
    for value in invalid:
        state=replace(F.ctx().owner,revoked_research_attestations=value)
        refused(lambda state=state:F.ctx(owner=state))
    state=M.OwnerState(status='OK')
    object.__delattr__(state,FIELD)
    refused(lambda:F.ctx(owner=state))


def test_mutation_of_an_already_sealed_target_set_breaks_hash_or_strict_type_check():
    context=F.ctx()
    initial=context.ctx_hash
    object.__setattr__(context.owner,FIELD,frozenset({(ARCHIVE,'a'*64)}))
    assert M.is_sealed(context) and M.context_hash(context)!=initial
    object.__setattr__(context.owner,FIELD,set())
    refused(lambda:M.context_hash(context))
    object.__delattr__(context.owner,FIELD)
    refused(lambda:M.context_hash(context))


def test_current_provider_refreshes_same_head_and_restriction_set_and_latches_rollback():
    with signed_home() as e:
        clock=lambda:NOW
        provider=CurrentOwnerAuthority(clock=clock)
        first=provider(NOW)
        assert first.context.owner.revoked_research_attestations==frozenset()
        before=owner.log_path().read_bytes()
        head=append(e)
        second=provider(NOW)
        assert second.observed_at==NOW and second.context.owner.head==head
        assert second.context.owner.revoked_research_attestations==frozenset({(ARCHIVE,'a'*64)})
        assert first.context.owner.revoked_research_attestations==frozenset()  # No relabelled old context.
        owner.log_path().write_bytes(before)
        refused(lambda:provider(NOW),'OWNER_AUTHORITY_OWNER_STATE_BROKEN')
        with patch.object(owner,'load_context',side_effect=AssertionError('latched provider must not reload')):
            refused(lambda:provider(NOW),'OWNER_AUTHORITY_OWNER_STATE_BROKEN')


def test_restart_replays_restrictions_and_preserved_anchor_detects_deleted_event():
    with signed_home() as e:
        before=owner.log_path().read_bytes()
        head=append(e)
        clock=lambda:NOW
        first=CurrentOwnerAuthority(clock=clock)(NOW)
        restarted=CurrentOwnerAuthority(clock=clock)(NOW)
        assert restarted.context.owner.head==first.context.owner.head==head
        assert restarted.context.owner.revoked_research_attestations==first.context.owner.revoked_research_attestations
        anchor=owner.store_dir()/'research-attestations'/(head[1]+'.anchor.json')
        assert anchor.read_bytes()==M.canonical_json({'seq':head[0],'row_sha256':head[1]}).encode()
        owner.log_path().write_bytes(before)
        refused(lambda:CurrentOwnerAuthority(clock=clock)(NOW),'OWNER_AUTHORITY_OWNER_STATE_BROKEN')


def test_key_rotation_keeps_restrictions_under_actual_verified_key_chain():
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    with signed_home() as e:
        append(e)
        clock=lambda:NOW
        pinned=CurrentOwnerAuthority(clock=clock)
        old=pinned(NOW)
        other=Ed25519PrivateKey.from_private_bytes(bytes(range(1,33)))
        b64=lambda key:base64.b64encode(key.public_key().public_bytes_raw()).decode('ascii')
        F.sign(e.key,'key_rotated',{'old_pubkey_b64':b64(e.key),'new_pubkey_b64':b64(other)})
        F.write_pubkey(owner.PUBKEY_PATH,other)
        head=F.sign(other,EVENT,data(SOURCE,'b'*64))
        refused(lambda:pinned(NOW),'OWNER_AUTHORITY_KEY_CHANGED')
        current=CurrentOwnerAuthority(clock=clock)(NOW)
        assert current.context.owner.head==head and current.public_key_raw==other.public_key().public_bytes_raw()
        assert current.context.owner.revoked_research_attestations==old.context.owner.revoked_research_attestations|{(SOURCE,'b'*64)}


def test_broken_log_after_revocation_never_becomes_not_revoked_current_authority():
    with signed_home() as e:
        append(e)
        lines=owner.log_path().read_bytes().splitlines()
        row=json.loads(lines[-1]);row['sig']=base64.b64encode(bytes(64)).decode()
        owner.log_path().write_bytes(b'\n'.join(lines[:-1]+[M.canonical_json(row).encode()])+b'\n')
        context=load()
        assert M.is_sealed(context) and not context.owner.ok and not context.code_signed
        refused(lambda:CurrentOwnerAuthority(clock=lambda:NOW)(NOW),'OWNER_AUTHORITY_OWNER_STATE_BROKEN')


def test_independent_owner_schema_matches_pure_codec_without_runtime_reverse_dependency():
    # Testing imports the pure consumer codec; owner/model must never import it.
    from execution_launch import research_revocation as R
    assert PURPOSES==R.PURPOSES and REASONS==R.REASON_CODES
    for purpose in PURPOSES:
        for reason in REASONS:
            value=data(purpose,reason=reason)
            assert R.validate_revocation_data(value)==value and owner._data_problem(EVENT,value)==''
    assert R.validate_revoked_targets(frozenset({(ARCHIVE,'a'*64)}))==frozenset({(ARCHIVE,'a'*64)})


def test_observed_future_and_duplicate_events_get_exact_independent_durable_anchors():
    with signed_home() as e:
        heads=(append(e),append(e,utc=M.iso_utc(NOW+timedelta(days=4))))
        context=load()
        assert context.owner.ok and context.owner.revoked_research_attestations==frozenset({(ARCHIVE,'a'*64)})
        base=owner.store_dir()/'research-attestations'
        assert {path.name for path in base.iterdir()}=={sha+'.anchor.json' for _,sha in heads}
        observed={}
        for seq,sha in heads:
            path=base/(sha+'.anchor.json')
            raw=M.canonical_json({'seq':seq,'row_sha256':sha}).encode()
            assert path.read_bytes()==raw and (seq,sha) in owner.read_anchors()
            info=path.stat();observed[path]=(raw,info.st_ino,info.st_mtime_ns)
        assert load().owner.ok
        for path,(raw,inode,mtime) in observed.items():
            assert path.read_bytes()==raw and path.stat().st_ino==inode and path.stat().st_mtime_ns==mtime


def test_legacy_observation_without_restrictions_does_not_create_new_lock_or_anchor_directory():
    with signed_home() as e:
        before=set(e.home.rglob('*'))
        context=load()
        assert context.owner.ok and not context.owner.revoked_research_attestations
        assert set(e.home.rglob('*'))==before
        assert not (owner.store_dir()/'research-attestations').exists()
        assert not owner.log_path().with_suffix('.jsonl.lock').exists()


def test_initial_observed_restriction_cannot_disappear_before_the_actual_writer_lock():
    for mode in ('truncate','grow'):
        with signed_home() as e:
            prefix=owner.log_path().read_bytes()
            first=append(e)
            original=owner._exclusive
            @contextmanager
            def changed(path):
                with original(path):
                    if mode=='truncate':
                        owner.log_path().write_bytes(prefix)
                    else:
                        append(e,data(SOURCE,'b'*64))
                    yield
            with patch.object(owner,'_exclusive',changed):
                context=load()
            if mode=='truncate':
                assert not context.owner.ok and not context.code_signed
                assert not (owner.store_dir()/'research-attestations').exists()
            else:
                assert context.owner.ok and context.owner.head[0]==first[0]+1
                assert context.owner.revoked_research_attestations==frozenset({(ARCHIVE,'a'*64),(SOURCE,'b'*64)})


def test_partial_conflicting_noncanonical_and_unknown_anchor_entries_are_retained_and_refused():
    for case in ('partial','empty','wrong_seq','wrong_sha','unknown_name','extra','newline','duplicate','directory'):
        with signed_home() as e:
            seq,sha=append(e)
            base=owner.store_dir()/'research-attestations';base.mkdir(parents=True)
            path=base/(sha+'.anchor.json')
            body={'seq':seq,'row_sha256':sha}
            raw=M.canonical_json(body).encode()
            if case=='partial':raw=b'{'
            elif case=='empty':raw=b''
            elif case=='wrong_seq':raw=M.canonical_json(body|{'seq':seq-1}).encode()
            elif case=='wrong_sha':raw=M.canonical_json(body|{'row_sha256':'b'*64}).encode()
            elif case=='unknown_name':path=base/'hidden.tmp'
            elif case=='extra':raw=M.canonical_json(body|{'approved':True}).encode()
            elif case=='newline':raw+=b'\n'
            elif case=='duplicate':raw=raw[:-1]+b',"seq":'+str(seq).encode()+b'}'
            if case=='directory':path.mkdir()
            else:path.write_bytes(raw)
            assert not load().owner.ok and path.exists()
            if case!='directory':assert path.read_bytes()==raw


def test_research_anchor_for_an_actual_nonrevocation_owner_row_is_refused():
    with signed_home() as e:
        row=json.loads(owner.log_path().read_bytes().splitlines()[0])
        assert row['kind']=='code_approved'
        base=owner.store_dir()/'research-attestations';base.mkdir(parents=True)
        path=base/(row['row_sha256']+'.anchor.json')
        raw=M.canonical_json({key:row[key] for key in ('seq','row_sha256')}).encode()
        path.write_bytes(raw)
        assert not load().owner.ok and path.read_bytes()==raw


def test_linked_anchor_is_refused_without_modifying_its_target():
    if os.name=='nt':
        from tests.notrun import NotRun
        raise NotRun('Native Windows link creation privileges are not exercised by this POSIX fixture')
    for kind in ('symbolic','hard'):
        with signed_home() as e:
            seq,sha=append(e)
            base=owner.store_dir()/'research-attestations';base.mkdir(parents=True)
            path=base/(sha+'.anchor.json')
            target=e.home/'retained-source'
            raw=M.canonical_json({'seq':seq,'row_sha256':sha}).encode();target.write_bytes(raw)
            if kind=='symbolic':path.symlink_to(target)
            else:os.link(target,path)
            assert not load().owner.ok and target.read_bytes()==raw and path.exists()


def test_partial_exclusive_write_is_not_automatically_repaired_or_reported_as_observed():
    with signed_home() as e:
        seq,sha=append(e)
        original=owner._open_research_anchor
        def interrupted(path,flags,**kwargs):
            descriptor=original(path,flags,**kwargs)
            if flags & os.O_CREAT:
                os.write(descriptor,b'{');os.close(descriptor)
                raise OSError('synthetic interruption after exclusive final creation')
            return descriptor
        with patch.object(owner,'_open_research_anchor',interrupted):
            assert not load().owner.ok
        path=owner.store_dir()/'research-attestations'/(sha+'.anchor.json')
        assert path.read_bytes()==b'{' and not load().owner.ok and path.read_bytes()==b'{'


def test_fsync_failure_refuses_observation_and_exact_retry_really_flushes_existing_bytes():
    with signed_home() as e:
        seq,sha=append(e)
        original=owner.os.fsync
        def fail_file(descriptor):
            if stat.S_ISREG(os.fstat(descriptor).st_mode):
                raise OSError('synthetic file fsync failure')
            return original(descriptor)
        with patch.object(owner.os,'fsync',side_effect=fail_file):
            assert not load().owner.ok
        path=owner.store_dir()/'research-attestations'/(sha+'.anchor.json')
        raw=M.canonical_json({'seq':seq,'row_sha256':sha}).encode()
        assert path.read_bytes()==raw
        with patch.object(owner.os,'fsync',wraps=original) as synchronize:
            assert load().owner.ok and synchronize.call_count>=1
        assert path.read_bytes()==raw


def test_final_observation_rechecks_actual_log_key_and_complete_anchor_inventory():
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    for changed in ('anchor','log','key'):
        with signed_home() as e:
            prefix=owner.log_path().read_bytes()
            seq,sha=append(e)
            original=owner._persist_research_anchor
            def mutate(entry):
                original(entry)
                if changed=='anchor':
                    (owner.store_dir()/'research-attestations'/(sha+'.anchor.json')).unlink()
                elif changed=='log':owner.log_path().write_bytes(prefix)
                else:F.write_pubkey(owner.PUBKEY_PATH,Ed25519PrivateKey.from_private_bytes(bytes(range(1,33))))
            with patch.object(owner,'_persist_research_anchor',mutate):
                context=load()
            assert not context.owner.ok and not context.code_signed


def test_actual_anchor_persistence_runs_under_the_existing_owner_sidecar_lock():
    if os.name=='nt':
        from tests.notrun import NotRun
        raise NotRun('Native Windows byte-lock behavior requires native execution')
    import fcntl
    with signed_home() as e:
        append(e)
        original=owner._persist_research_anchor
        calls=[]
        def locked(entry):
            with open(str(owner.log_path())+'.lock','a+b') as stream:
                try:fcntl.flock(stream.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
                except BlockingIOError:calls.append(True)
                else:
                    fcntl.flock(stream.fileno(),fcntl.LOCK_UN)
                    raise AssertionError('actual owner lock was not held')
            original(entry)
        with patch.object(owner,'_persist_research_anchor',locked):
            assert load().owner.ok
        assert calls==[True]


def test_concurrent_parent_replacement_cannot_redirect_new_directory_creation():
    if os.name=='nt':
        from tests.notrun import NotRun
        raise NotRun('OWNER: native Windows replacement behavior requires native execution; POSIX fixture only')
    with signed_home() as e:
        append(e)
        approved=owner.store_dir();approved.mkdir()
        held=e.home/'retained-approved'
        outside=e.home/'outside-scope';outside.mkdir()
        original=owner.os.mkdir
        attempts=[]
        def replaced(path,mode=0o777,*,dir_fd=None):
            if path=='research-attestations' and dir_fd is not None:
                attempts.append(True)
                approved.rename(held)
                approved.symlink_to(outside,target_is_directory=True)
            return original(path,mode,dir_fd=dir_fd)
        try:
            with patch.object(owner.os,'mkdir',replaced):
                context=load()
            assert attempts==[True] and not context.owner.ok
            assert not (outside/'research-attestations').exists()
            assert (held/'research-attestations').is_dir()
        finally:
            if approved.is_symlink():approved.unlink()
            if held.exists():held.rename(approved)


def test_posix_creation_helper_refuses_windows_without_path_based_mkdir_fallback():
    with F.temp_home() as home:
        candidate=home/'approved'/'research-attestations'
        with patch.object(owner,'_research_anchor_directory',return_value=candidate), \
                patch.object(owner.os,'name','nt'), patch.object(owner.os,'mkdir') as mkdir:
            refused(owner._make_research_anchor_directory,'research restriction directory pin unsupported')
            assert not mkdir.called
        assert not candidate.exists()


def test_synthetic_windows_owner_wiring_retains_pin_through_leaf_write_and_readback():
    # This checks owner call ordering with real temporary leaf I/O. Native Win32
    # handles are replaced explicitly; it is not native Windows validation.
    from core.compliance import revocation_paths
    with signed_home() as e:
        seq,sha=append(e)
        checked=owner.verify_log(owner.log_path().read_bytes().splitlines(keepends=True),e.public,[])
        assert checked.ok
        active=[];events=[]
        @contextmanager
        def pinned(home):
            base=home/'approved'/'research-attestations';base.mkdir(parents=True)
            active.append(True);events.append('enter')
            def check():
                assert active==[True]
                events.append('check')
            try:yield SimpleNamespace(path=base,check=check)
            finally:events.append('exit');active.pop()
        original=owner._open_research_anchor
        def open_leaf(*args,**kwargs):
            assert active==[True]
            events.append('leaf')
            return original(*args,**kwargs)
        platform=SimpleNamespace(**(dict(vars(os))|{'name':'nt'}))
        with owner._exclusive(owner.log_path()):
            with patch.object(owner,'os',platform), \
                    patch.object(revocation_paths,'pinned_research_anchor_directory',pinned), \
                    patch.object(owner,'_open_research_anchor',open_leaf):
                owner._persist_research_anchor(checked.entries[-1])
        assert events==['enter','check','leaf','leaf','check','exit'] and not active
        path=owner.store_dir()/'research-attestations'/(sha+'.anchor.json')
        assert path.read_bytes()==M.canonical_json({'seq':seq,'row_sha256':sha}).encode()
