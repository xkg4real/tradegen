"""Independent, explicitly prepared authority journal; no application imports.

An operation retains process/OS serialization and pinned directory identities.
Crypto replay happens outside writer/head locks. Publication preserves partial
bytes on failure; a reader never initializes, repairs or adopts a trailing row.
Separate roots are not separate media or protection against coherent rollback
of every root. Native Windows execution and power-loss behavior remain untested.
"""
from __future__ import annotations

from contextlib import contextmanager, ExitStack
from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import stat
from threading import Lock, get_ident

from tools.signer import sign as S
from tools.approval_broker import contract as C
from tools.approval_broker import authority_contract as A
from tools.approval_broker import owner_view as O

_FLAGS = getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_BINARY', 0) | getattr(os, 'O_NONBLOCK', 0)
_PROCESS = Lock()
_INDETERMINATE = 'PASSKEY_STORE_INDETERMINATE'


def _need(value, code=_INDETERMINATE):
    C.need(value, code)


def _identity(info, *, directory=False, maximum=None):
    _need(type(info.st_ino) is int and info.st_ino > 0 and info.st_dev >= 0
          and not getattr(info, 'st_file_attributes', 0) & 0x441400)
    if directory:
        _need(stat.S_ISDIR(info.st_mode))
    else:
        _need(stat.S_ISREG(info.st_mode) and info.st_nlink == 1
              and maximum is not None and 0 <= info.st_size <= maximum)
    return info.st_dev, info.st_ino


def _body(value, maximum=14*1024*1024):
    return A.decode_authority(value, maximum=maximum)


@dataclass(frozen=True, slots=True, kw_only=True)
class LedgerRoots:
    primary: Path
    backup: Path
    head: Path


@dataclass(frozen=True, slots=True, kw_only=True)
class LedgerLimits:
    max_event_bytes: int = 14*1024*1024
    max_state_bytes: int = 64*1024*1024
    max_journal_bytes: int = 256*1024*1024
    max_backup_bytes: int = 256*1024*1024
    max_events: int = 16384

    def __post_init__(self):
        for name, cap in (('max_event_bytes',14*1024*1024),('max_state_bytes',64*1024*1024),
                          ('max_journal_bytes',256*1024*1024),('max_backup_bytes',256*1024*1024),
                          ('max_events',16384)):
            value = getattr(self, name)
            _need(type(value) is int and 0 < value <= cap, 'PASSKEY_RESOURCE_LIMIT')


@dataclass(frozen=True, slots=True, kw_only=True)
class LedgerInstallation:
    authority_id: str
    config_sha256: str
    operator_paths_sha256: str
    roots: O.TrustRoots

    def __post_init__(self):
        for value in (self.authority_id,self.config_sha256,self.operator_paths_sha256): C.hashed(value)
        _need(type(self.roots) is O.TrustRoots, 'PASSKEY_FORMAT_INVALID')
        C.binary(self.roots.initial_public_key_raw,32,minimum=32)
        C.binary(self.roots.recovery_public_key_raw,32,minimum=32)
        _need(type(self.roots.initial_owner_head) is A.Head
              and self.roots.initial_owner_head.sequence > 0, 'PASSKEY_FORMAT_INVALID')
        A.head_document(self.roots.initial_owner_head)


@dataclass(frozen=True, slots=True, kw_only=True)
class LedgerSnapshot:
    head: A.Head
    context_sha256: str
    journal_bytes: int
    state: A.AuthorityState


def _installation(value):
    _need(type(value) is LedgerInstallation, 'PASSKEY_FORMAT_INVALID')
    value.__post_init__()
    return dict(authority_id=value.authority_id,config_sha256=value.config_sha256,
        operator_paths_sha256=value.operator_paths_sha256, roots=dict(
        initial_public_key_raw=C.b64(value.roots.initial_public_key_raw),
        recovery_public_key_raw=C.b64(value.roots.recovery_public_key_raw),
        initial_owner_head=A.head_document(value.roots.initial_owner_head)))


def _limits(value):
    _need(type(value) is LedgerLimits, 'PASSKEY_FORMAT_INVALID'); value.__post_init__()
    return {name:getattr(value,name) for name in ('max_event_bytes','max_state_bytes',
        'max_journal_bytes','max_backup_bytes','max_events')}


def _roots(value):
    _need(type(value) is LedgerRoots, 'PASSKEY_FORMAT_INVALID')
    paths = (value.primary,value.backup,value.head)
    for path in paths:
        _need(isinstance(path,Path) and path.is_absolute() and '..' not in path.parts,
              'PASSKEY_FORMAT_INVALID')
        _identity(os.lstat(path),directory=True)
        S._bundle_directory(path)
    real = tuple(p.resolve() for p in paths)
    _need(len(set(real)) == 3 and all(not a.is_relative_to(b) and not b.is_relative_to(a)
        for i,a in enumerate(real) for b in real[i+1:]), 'PASSKEY_FORMAT_INVALID')
    ids = tuple(_identity(os.lstat(p),directory=True) for p in paths)
    _need(len(set(ids)) == 3, 'PASSKEY_FORMAT_INVALID')
    return paths, ids


def _sync(pin):
    pin.check()
    if pin.descriptor is not None: os.fsync(pin.descriptor)


def _read(pin, name, maximum, *, empty=False):
    raw, stamp = S._bundle_read(pin.path/name, maximum, empty=empty, parent_pin=pin)
    _identity(pin.stat(name),maximum=maximum)
    return raw


def _new(pin, name, raw):
    # Exclusive fixed/generated leaf. Reviewed standalone primitive fsyncs and
    # reads the actual bytes back; it never follows original input filenames.
    if raw:
        S._bundle_write_pinned(pin.path/name, raw, pin)
        return
    # Signer's packet writer intentionally refuses empty readback. The explicit
    # genesis journal is the sole empty leaf here; keep that policy unchanged.
    _need(name=='journal.jsonl')
    fd=pin.open(name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|_FLAGS)
    try:
        identity=_identity(os.fstat(fd),maximum=0)
        os.fsync(fd)
    finally: os.close(fd)
    _need(_identity(pin.stat(name),maximum=0)==identity and _read(pin,name,0,empty=True)==b'')
    _sync(pin)


@contextmanager
def _lock(pin, name):
    before = _identity(pin.stat(name),maximum=1)
    fd = pin.open(name, os.O_RDWR|_FLAGS)
    with os.fdopen(fd,'r+b') as handle:
        _need(_identity(os.fstat(handle.fileno()),maximum=1) == before)
        _need(handle.read(2) == b'0')
        if os.name == 'nt':
            import msvcrt
            handle.seek(0); msvcrt.locking(handle.fileno(),msvcrt.LK_NBLCK,1)
        else:
            import fcntl
            fcntl.flock(handle.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        try:
            _need(_identity(pin.stat(name),maximum=1) == before)
            yield
            _need(_identity(pin.stat(name),maximum=1) == before)
        finally:
            if os.name == 'nt':
                handle.seek(0); msvcrt.locking(handle.fileno(),msvcrt.LK_UNLCK,1)
            else: fcntl.flock(handle.fileno(),fcntl.LOCK_UN)


class AuthorityLedger:
    def __init__(self, *, roots: LedgerRoots, installation: LedgerInstallation,
                 limits: LedgerLimits = LedgerLimits()):
        try:
            paths, identities = _roots(roots)
            body = dict(installation=_installation(installation),limits=_limits(limits),
                        roots=[dict(path=str(p),identity=list(i)) for p,i in zip(paths,identities)])
            self.roots,self.installation,self.limits = roots,installation,limits
            self._fixed=(roots,installation,limits)
            self._identities=identities
            self.context_sha256=A.record_digest('ledger-context',A.canonical(body))
            self.genesis_digest=A.record_digest('ledger-genesis',A.canonical({'context_sha256':self.context_sha256}))
            self._context_bytes=A.canonical(body)
            self._active=None
            self._head_dir=roots.head/('authority-'+installation.authority_id)
        except C.PasskeyError: raise
        except (OSError,ValueError,TypeError,AttributeError):
            raise C.PasskeyError(_INDETERMINATE) from None

    def _configuration(self):
        _need(all(a is b for a,b in zip((self.roots,self.installation,self.limits),self._fixed)))
        paths,identities=_roots(self.roots)
        body=dict(installation=_installation(self.installation),limits=_limits(self.limits),
                  roots=[dict(path=str(p),identity=list(i)) for p,i in zip(paths,identities)])
        _need(identities == self._identities and A.canonical(body) == self._context_bytes
              and self._head_dir == self.roots.head/('authority-'+self.installation.authority_id)
              and self.context_sha256==A.record_digest('ledger-context',self._context_bytes)
              and self.genesis_digest==A.record_digest('ledger-genesis',A.canonical({'context_sha256':self.context_sha256})))

    @contextmanager
    def operation(self):
        _need(_PROCESS.acquire(blocking=False), _INDETERMINATE)
        body_error = traceback = None
        try:
            self._configuration()
            with ExitStack() as stack:
                primary=stack.enter_context(S._BundlePin(self.roots.primary))
                backup=stack.enter_context(S._BundlePin(self.roots.backup))
                headroot=stack.enter_context(S._BundlePin(self.roots.head))
                needed=((primary,'operation.lock'),(primary,'writer.lock'),(primary,'journal.jsonl'),
                        (backup,'versions'),(headroot,self._head_dir.name))
                for pin,name in needed:
                    try: pin.stat(name)
                    except FileNotFoundError: raise C.PasskeyError('PASSKEY_BOOTSTRAP_REQUIRED') from None
                versions=stack.enter_context(S._BundlePin(self.roots.backup/'versions'))
                head=stack.enter_context(S._BundlePin(self._head_dir))
                for name in ('head.json','head.lock'):
                    try: head.stat(name)
                    except FileNotFoundError: raise C.PasskeyError('PASSKEY_BOOTSTRAP_REQUIRED') from None
                with _lock(primary,'operation.lock'):
                    op=_Operation(self,(primary,backup,headroot,versions,head))
                    self._active=(op,get_ident())
                    try:
                        op.check()
                        try: yield op
                        except BaseException as exc: body_error,traceback=exc,exc.__traceback__
                        op.check()
                    finally: self._active=None
        except C.PasskeyError: raise
        except (OSError,ValueError,RuntimeError,TypeError,AttributeError):
            raise C.PasskeyError(_INDETERMINATE) from None
        finally: _PROCESS.release()
        if body_error is not None: raise body_error.with_traceback(traceback)

    def inspect(self):
        with self.operation() as op: return op.load()


class _Operation:
    def __init__(self, ledger, pins):
        self._ledger,self._pins=ledger,pins
        p,_,_,_,h=pins
        self._anchors=tuple((pin,name,_identity(pin.stat(name),maximum=cap)) for pin,name,cap in
            ((p,'operation.lock',1),(p,'writer.lock',1),(p,'journal.jsonl',ledger.limits.max_journal_bytes),
             (h,'head.lock',1)))

    def check(self):
        ledger=self._ledger
        _need(ledger._active == (self,get_ident()))
        ledger._configuration()
        for pin in self._pins: pin.check()
        for pin,name,identity in self._anchors:
            _need(_identity(pin.stat(name),maximum=ledger.limits.max_journal_bytes if name=='journal.jsonl' else 1)==identity)

    @contextmanager
    def _writing(self):
        self.check()
        with _lock(self._pins[0],'writer.lock'):
            with _lock(self._pins[4],'head.lock'):
                self.check(); yield; self.check()

    def _disk(self, *, allow_unpublished=False, head_temporary=False):
        ledger=self._ledger; limits=ledger.limits
        p,b,hr,v,h=self._pins
        _need(set(p.names(4)) == {'operation.lock','writer.lock','journal.jsonl'})
        _need(b.names(2) == ['versions'] or set(b.names(2)) == {'versions'})
        _need(set(hr.names(2)) == {ledger._head_dir.name})
        _need(set(h.names(4)) == ({'head.json','head.lock','head.tmp'} if head_temporary else {'head.json','head.lock'}))
        head_raw=_read(h,'head.json',4096)
        head=_body(head_raw,4096)
        C.keys(head,('schema','sequence','sha256','context_sha256'))
        _need(type(head['schema']) is int and head['schema']==1
              and head['context_sha256']==ledger.context_sha256)
        actual_head=A.Head(sequence=head['sequence'],sha256=head['sha256'])
        _need(A.canonical(head)==head_raw)
        raw=_read(p,'journal.jsonl',limits.max_journal_bytes,empty=True)
        _need(not raw or raw.endswith(b'\n'))
        _need(raw.count(b'\n') <= limits.max_events,'PASSKEY_RESOURCE_LIMIT')
        rows=tuple(raw.split(b'\n')[:-1]) if raw else ()
        previous=ledger.genesis_digest; names=set(); backup_bytes=0
        for index,line in enumerate(rows,1):
            _need(0<len(line)+1<=limits.max_event_bytes,'PASSKEY_RESOURCE_LIMIT')
            row=_body(line,limits.max_event_bytes)
            C.keys(row,('schema','sequence','previous_sha256','observed_at','kind','payload','row_sha256'))
            _need(type(row['sequence']) is int and row['sequence']==index
                  and row['previous_sha256']==previous)
            C.hashed(row['row_sha256'])
            unsigned={k:value for k,value in row.items() if k!='row_sha256'}
            _need(row['row_sha256']==A.record_digest('authority-event',A.canonical(unsigned))
                  and A.canonical(row)==line)
            name=row['row_sha256']+'.json'; names.add(name)
            backup_bytes+=len(line)
            _need(backup_bytes<=limits.max_backup_bytes,'PASSKEY_RESOURCE_LIMIT')
            _need(_read(v,name,limits.max_event_bytes)==line)
            previous=row['row_sha256']
        _need(set(v.names(limits.max_events+1))==names)
        if not allow_unpublished:
            _need(actual_head==A.Head(sequence=len(rows),sha256=previous))
        self.check()
        return rows,head_raw,len(raw),backup_bytes

    def _snapshot(self,disk):
        from tools.approval_broker import authority_replay as R
        state=R.replay_events(disk[0],installation=self._ledger.installation,limits=self._ledger.limits)
        body=_body(disk[1],4096)
        return LedgerSnapshot(head=A.Head(sequence=body['sequence'],sha256=body['sha256']),
            context_sha256=self._ledger.context_sha256,journal_bytes=disk[2],state=state)

    def load(self):
        try:
            with self._writing(): disk=self._disk()
            result=self._snapshot(disk)  # actual crypto; no writer/head lock held
            with self._writing(): _need(self._disk()==disk)
            return result
        except C.PasskeyError: raise
        except (OSError,ValueError,RuntimeError,TypeError,KeyError,AttributeError):
            raise C.PasskeyError(_INDETERMINATE) from None

    def commit(self,event,*,expected_head):
        from tools.approval_broker import authority_replay as R
        try:
            _need(type(event) is A.ProposedEvent and type(expected_head) is A.Head,'PASSKEY_FORMAT_INVALID')
            payload=A.proposed_payload(event)
            with self._writing(): disk=self._disk()
            current=self._snapshot(disk)
            if disk[0]:
                last=A.parse_event(disk[0][-1])
                if (last.kind==event.kind and last.observed_at==event.observed_at
                        and last.payload_bytes==A.canonical(payload)
                        and expected_head in (current.head,A.Head(sequence=last.sequence-1,sha256=last.previous_sha256))):
                    with self._writing(): _need(self._disk()==disk)
                    return current
            _need(expected_head==current.head,'PASSKEY_REGISTRY_CHANGED')
            unsigned=dict(schema=1,sequence=current.head.sequence+1,previous_sha256=current.head.sha256,
                observed_at=C.stamp(event.observed_at),kind=event.kind,payload=payload)
            raw=A.canonical(unsigned|{'row_sha256':A.record_digest('authority-event',A.canonical(unsigned))})
            row=A.parse_event(raw)
            # This private fold accepts only the actual locally reconstructed state.
            proposed=R._transition_owned(current.state,row,installation=self._ledger.installation,
                                          limits=self._ledger.limits)
            if proposed is current.state:
                with self._writing(): _need(self._disk()==disk)
                return current
            limit=self._ledger.limits
            R._state_bytes(proposed,limits=limit)
            _need(len(raw)+1<=limit.max_event_bytes and len(disk[0])+1<=limit.max_events
                  and disk[2]+len(raw)+1<=limit.max_journal_bytes
                  and disk[3]+len(raw)<=limit.max_backup_bytes,'PASSKEY_RESOURCE_LIMIT')
            with self._writing():
                _need(self._disk()==disk)
                self._append(raw+b'\n',disk[2])
                _new(self._pins[3],row.row_sha256+'.json',raw)
                after=self._disk(allow_unpublished=True)
                _need(after[0]==disk[0]+(raw,) and after[1]==disk[1])
                self._head(A.Head(sequence=row.sequence,sha256=row.row_sha256),after)
                confirmed=self._disk()
                _need(confirmed[0]==after[0] and confirmed[2:]==after[2:])
            return LedgerSnapshot(head=A.Head(sequence=row.sequence,sha256=row.row_sha256),
                context_sha256=self._ledger.context_sha256,journal_bytes=confirmed[2],state=proposed)
        except C.PasskeyError: raise
        except (OSError,ValueError,RuntimeError,TypeError,KeyError,AttributeError):
            raise C.PasskeyError(_INDETERMINATE) from None

    def _append(self,line,size):
        pin=self._pins[0]; maximum=self._ledger.limits.max_journal_bytes
        before=pin.stat('journal.jsonl'); identity=_identity(before,maximum=maximum)
        fd=pin.open('journal.jsonl',os.O_WRONLY|os.O_APPEND|_FLAGS)
        with os.fdopen(fd,'ab') as handle:
            opened=os.fstat(handle.fileno())
            _need(_identity(opened,maximum=maximum)==identity and opened.st_size==size)
            _need(handle.write(line)==len(line));handle.flush();os.fsync(handle.fileno())
        _need(_identity(pin.stat('journal.jsonl'),maximum=maximum)==identity)
        raw=_read(pin,'journal.jsonl',maximum)
        _need(len(raw)==size+len(line) and raw[-len(line):]==line)

    def _head(self,head,expected_disk):
        pin=self._pins[4]
        raw=A.canonical(dict(schema=1,sequence=head.sequence,sha256=head.sha256,
                             context_sha256=self._ledger.context_sha256))
        _new(pin,'head.tmp',raw)
        # Do not overwrite a changed predecessor after the slow temp fsync.
        # Recheck all actual row/backup bytes, plus the exact old head and temp.
        _need(self._disk(allow_unpublished=True,head_temporary=True)==expected_disk
              and _read(pin,'head.tmp',4096)==raw)
        if pin.descriptor is None: os.replace(pin.path/'head.tmp',pin.path/'head.json')
        else: os.replace('head.tmp','head.json',src_dir_fd=pin.descriptor,dst_dir_fd=pin.descriptor)
        _sync(pin)
        _need(_read(pin,'head.json',4096)==raw)


def prepare_authority_store(*,roots,installation,limits=LedgerLimits()):
    """Explicit empty operator provisioning, not a grant or service installation.

An interrupted preparation remains visible and a second attempt refuses it.
Only this helper creates paths; normal constructors/readers do not call it.
"""
    ledger=AuthorityLedger(roots=roots,installation=installation,limits=limits)
    _need(_PROCESS.acquire(blocking=False),_INDETERMINATE)
    try:
        with ExitStack() as stack:
            pins=[stack.enter_context(S._BundlePin(p)) for p in (roots.primary,roots.backup,roots.head)]
            _need(all(not pin.names(1) for pin in pins),'PASSKEY_BOOTSTRAP_REQUIRED')
            for name,raw in (('operation.lock',b'0'),('writer.lock',b'0'),('journal.jsonl',b'')):
                _new(pins[0],name,raw)
            for pin,name in ((pins[1],'versions'),(pins[2],ledger._head_dir.name)):
                if pin.descriptor is None: os.mkdir(pin.path/name,mode=0o700)
                else: os.mkdir(name,mode=0o700,dir_fd=pin.descriptor)
                _sync(pin)
            h=stack.enter_context(S._BundlePin(ledger._head_dir))
            _new(h,'head.lock',b'0')
            _new(h,'head.json',A.canonical(dict(schema=1,sequence=0,sha256=ledger.genesis_digest,
                                               context_sha256=ledger.context_sha256)))
    except C.PasskeyError: raise
    except (OSError,ValueError,RuntimeError,TypeError,AttributeError):
        raise C.PasskeyError(_INDETERMINATE) from None
    finally: _PROCESS.release()
    _need(ledger.inspect().head==A.Head(sequence=0,sha256=ledger.genesis_digest))
    return ledger
