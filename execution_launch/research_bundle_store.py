"""Explicit-root immutable research archives with catalog/head publication and copied backups.

RAW_ARCHIVED preserves observations, including empty/malformed files and failures.
VERIFIED_UNAPPROVED is a separate same-input derivation, never an evaluation or
approval issuer. Only the adapter can actually revalidate/evaluate a study.
Objects, temporary files and final names are not published bundles. A complete
requested graph plus catalog/head CAS and readback is the visibility boundary.
Primary and backup commits are separate; no cross-root atomicity is claimed.

Catalog integrity is shared; object validation is limited to the requested bundle
and its raw dependency. An unrelated damaged object does not invalidate another
study. All interrupted files are retained. No truncation, cleanup, re-anchor,
automatic head initialization, backup adoption or recovery is performed here.
Both roots must be explicitly provided existing real directories outside the
repository/state home. Provisioning only prepares empty storage; the operator's
separate head-initialization procedure is mandatory. OneDrive name rejection
is not proof against every synchronization product. Same-device backups do not
prove independent failure domains, nor does fsync prove Windows power-loss safety.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import asdict, dataclass, replace
import hashlib
import errno
import json
import os
from pathlib import Path
import re
import stat
from threading import Lock
from types import MappingProxyType
from typing import Mapping

from core.isolation import checked_target, state_root
from execution_launch.baseline_head import BaselineHead, BaselineHeadError
from execution_launch.evidence_objects import (
    EvidenceObjectError, EvidenceObjectStore, InventoryEntry, ObjectLimits,
    PayloadReference, StoreBudget, StoreInventory, admit_store_budget,
    decode_reference, preview_payload,
)
from execution_launch import research_bundle_format as F

_DOMAIN = b'tradegen-research-store/1\x00'
_HASH = re.compile(r'[0-9a-f]{64}')
_ID = re.compile(r'[A-Za-z][A-Za-z0-9_.:-]{0,95}')
_CODE = re.compile(r'[A-Z][A-Z0-9_]{0,95}')
_ROW_MAX = 16384
_FLAGS = getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0) | getattr(os, 'O_BINARY', 0)
_REPO = Path(__file__).resolve().parents[1]
_LOCK = Lock()
_EVENTS = ('PRIMARY_COMMITTED', 'BACKUP_VERIFIED', 'DIAGNOSTIC')
_KINDS = ('RAW_ARCHIVED', 'VERIFIED_UNAPPROVED')
_ROW_KEYS = frozenset(('schema', 'sequence', 'previous_sha256', 'context_sha256', 'event', 'kind',
    'bundle_sha256', 'run_id', 'revision_id', 'attempt_id', 'manifest_ref', 'files_sha256', 'code', 'row_sha256'))


class BundleStoreError(ValueError):
    """Fixed codes only; no paths, account values or upstream exception text."""


def _require(ok, code):
    if not ok:
        raise BundleStoreError(code)


def _hash(value):
    return type(value) is str and _HASH.fullmatch(value) is not None


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True,
                      allow_nan=False).encode('ascii')


def _digest(kind, body):
    return hashlib.sha256(_DOMAIN + kind.encode('ascii') + b'\x00' + _canonical(body)).hexdigest()


def _identity(info):
    _require(type(info.st_ino) is int and info.st_ino > 0 and type(info.st_dev) is int and info.st_dev >= 0,
             'BUNDLE_STORE_IDENTITY_UNAVAILABLE')
    return info.st_dev, info.st_ino


def _directory(path):
    info = os.lstat(path)
    _require(stat.S_ISDIR(info.st_mode) and not getattr(info, 'st_file_attributes', 0) & 0x400,
             'BUNDLE_STORE_PATH_REFUSED')
    return _identity(info)


def _file(info, maximum):
    _identity(info)
    _require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and 0 <= info.st_size <= maximum
             and not getattr(info, 'st_file_attributes', 0) & 0x400, 'BUNDLE_STORE_FILE_REFUSED')


def _decode(raw):
    def pairs(items):
        body = {}
        for key, value in items:
            _require(key not in body, 'BUNDLE_STORE_CATALOG_INVALID')
            body[key] = value
        return body
    def invalid(_):
        raise BundleStoreError('BUNDLE_STORE_CATALOG_INVALID')
    def integer(value):
        _require(len(value) <= 18, 'BUNDLE_STORE_CATALOG_INVALID')
        return int(value)
    try:
        _require(type(raw) is bytes and 0 < len(raw) <= _ROW_MAX, 'BUNDLE_STORE_CATALOG_INVALID')
        body = json.loads(raw.decode('ascii'), object_pairs_hook=pairs, parse_int=integer,
                          parse_float=invalid, parse_constant=invalid)
        _require(type(body) is dict and set(body) == _ROW_KEYS and _canonical(body) == raw,
                 'BUNDLE_STORE_CATALOG_INVALID')
        return body
    except BundleStoreError:
        raise
    except (ValueError, TypeError, UnicodeError, RecursionError, OverflowError):
        raise BundleStoreError('BUNDLE_STORE_CATALOG_INVALID') from None


@dataclass(frozen=True, kw_only=True)
class BundleRoots:
    sealed_root: Path
    backup_root: Path

    def __post_init__(self):
        for root in (self.sealed_root, self.backup_root):
            _require(isinstance(root, Path) and root.is_absolute() and '..' not in root.parts,
                     'BUNDLE_STORE_EXPLICIT_ROOT_REQUIRED')
        _require(not self.sealed_root.is_relative_to(self.backup_root)
                 and not self.backup_root.is_relative_to(self.sealed_root), 'BUNDLE_STORE_ROOT_OVERLAP')


@dataclass(frozen=True, kw_only=True)
class BundleStoreLimits:
    """Object budgets include temporary-copy peak; catalog has a separate finite cap.

    The combined primary byte bound is primary_budget.max_bytes +
    max_catalog_bytes + one session-lock byte. Backup objects and bounded head
    files are separate. This is not a free-space reservation against other apps.
    """
    format_limits: F.BundleLimits
    object_limits: ObjectLimits
    primary_budget: StoreBudget
    backup_budget: StoreBudget
    max_catalog_bytes: int
    max_catalog_records: int

    def __post_init__(self):
        _require(type(self.format_limits) is F.BundleLimits and type(self.object_limits) is ObjectLimits
                 and type(self.primary_budget) is StoreBudget and type(self.backup_budget) is StoreBudget,
                 'BUNDLE_STORE_LIMITS_INVALID')
        for value in (self.format_limits, self.object_limits, self.primary_budget, self.backup_budget):
            value.__post_init__()
        _require(type(self.max_catalog_bytes) is int and 0 < self.max_catalog_bytes <= 256 * 1024 * 1024
                 and type(self.max_catalog_records) is int and 0 < self.max_catalog_records <= 100000,
                 'BUNDLE_STORE_LIMITS_INVALID')

    @property
    def policy_sha256(self):
        self.__post_init__()
        return _digest('policy', asdict(self))


@dataclass(frozen=True, kw_only=True)
class BundleReceipt:
    """Historical storage facts, never current graph usability or research approval."""
    kind: str
    bundle_digest: str
    run_id: str
    revision_id: str
    attempt_id: str
    backup_verified: bool


@dataclass(frozen=True, kw_only=True)
class StoredBundle:
    manifest_bytes: bytes
    manifest: F.RawArchiveManifest | F.VerifiedBundleManifest
    files: Mapping[str, bytes]
    backup_verified: bool


@dataclass(frozen=True)
class _Entry:
    row: dict
    backed: bool = False
    diagnostics: tuple[str, ...] = ()


@dataclass(frozen=True)
class _Catalog:
    head: str
    sequence: int
    size: int
    entries: dict[str, _Entry]
    previous: str | None = None
    last: dict | None = None


class _BundleChain:
    def __init__(self, store):
        self.store = store

    def seed(self, digest):
        store = self.store
        store._configuration()
        catalog = store._catalog()
        _require(digest == store.genesis_digest and catalog.sequence == 0, 'BUNDLE_STORE_SEED_REQUIRED')
        for backup in (False, True):
            inventory = store._objects(backup).inventory(budget=store._budget(backup))
            _require(inventory.object_count == 1, 'BUNDLE_STORE_SEED_REQUIRED')
        return 0

    def successor(self, old, new):
        store = self.store
        catalog = store._catalog()
        _require(catalog.sequence > 0 and catalog.head == new and catalog.previous == old,
                 'BUNDLE_STORE_SUCCESSOR_INVALID')
        row = catalog.last
        if row['event'] != 'DIAGNOSTIC':
            store._validate_graph(catalog, row['bundle_sha256'], require_backup=row['event'] == 'BACKUP_VERIFIED')
        # A diagnostic only claims the bounded incident code, never graph validity.
        return catalog.sequence


class BundleStore:
    def __init__(self, *, roots: BundleRoots, limits: BundleStoreLimits, head_name: str):
        _require(type(roots) is BundleRoots and type(limits) is BundleStoreLimits, 'BUNDLE_STORE_CONTEXT_INVALID')
        roots.__post_init__(); limits.__post_init__()
        _require(type(head_name) is str and head_name != 'payload-objects', 'BUNDLE_STORE_HEAD_NAME_INVALID')
        self.roots, self.limits = roots, limits
        self._fixed_roots, self._fixed_limits = roots, asdict(limits)
        self._head_name = head_name
        self.context_sha256 = _digest('context', {'policy_sha256': limits.policy_sha256, 'head_name': head_name})
        self.genesis_digest = _digest('genesis', {'context_sha256': self.context_sha256})
        self._paths(prepared=False)
        self._root_ids = tuple(_directory(p) for p in (roots.sealed_root, roots.backup_root))
        _require(self._root_ids[0] != self._root_ids[1], 'BUNDLE_STORE_ROOT_OVERLAP')
        self._chain = _BundleChain(self)
        self.head = BaselineHead(root=roots.backup_root, name=head_name, chain=self._chain)
        self._fixed_head = self.head

    def _configuration(self):
        _require(type(self.roots) is BundleRoots and self.roots == self._fixed_roots
                 and type(self.limits) is BundleStoreLimits and asdict(self.limits) == self._fixed_limits,
                 'BUNDLE_STORE_CONTEXT_CHANGED')
        _require(self.context_sha256 == _digest('context', {'policy_sha256': self.limits.policy_sha256,
                                                         'head_name': self._head_name})
                 and self.genesis_digest == _digest('genesis', {'context_sha256': self.context_sha256}),
                 'BUNDLE_STORE_CONTEXT_CHANGED')
        if hasattr(self, '_fixed_head'):
            _require(type(self.head) is BaselineHead and self.head is self._fixed_head
                     and self.head._root == self.roots.backup_root
                     and self.head._dir == self.roots.backup_root / self._head_name
                     and self.head._chain is self._chain and type(self._chain) is _BundleChain
                     and self._chain.store is self, 'BUNDLE_STORE_CONTEXT_CHANGED')

    def _paths(self, *, prepared=True):
        self._configuration()
        try:
            roots = (self.roots.sealed_root, self.roots.backup_root)
            for root in roots:
                checked_target(root, 'research bundle root')
                _require(not any(p.casefold() == 'onedrive' or p.casefold().startswith('onedrive - ')
                                 for p in root.parts), 'BUNDLE_STORE_SYNC_ROOT_REFUSED')
                for path in (root, *root.parents):
                    _directory(path)
                for other in (state_root().absolute().resolve(), _REPO):
                    _require(not root.resolve().is_relative_to(other) and not other.is_relative_to(root.resolve()),
                             'BUNDLE_STORE_ROOT_NOT_SEPARATE')
            current = tuple(_directory(p) for p in roots)
            if hasattr(self, '_root_ids'):
                _require(current == self._root_ids, 'BUNDLE_STORE_ROOT_CHANGED')
            for backup, root in enumerate(roots):
                allowed = {'payload-objects', self._head_name} if backup else {'payload-objects', 'session.lock', 'catalog.jsonl'}
                with os.scandir(root) as entries:
                    names = set()
                    for entry in entries:
                        _require(entry.name in allowed and len(names) < len(allowed), 'BUNDLE_STORE_PATH_REFUSED')
                        names.add(entry.name)
                if prepared:
                    required = {'payload-objects'} if backup else allowed
                    _require(required <= names, 'BUNDLE_STORE_NOT_PROVISIONED')
                if 'payload-objects' in names:
                    _directory(root / 'payload-objects')
            for name, maximum in (('session.lock', 1), ('catalog.jsonl', self.limits.max_catalog_bytes)):
                target = self.roots.sealed_root / name
                if target.exists():
                    _file(os.lstat(target), maximum)
        except BundleStoreError:
            raise
        except (OSError, ValueError, RuntimeError, TypeError):
            raise BundleStoreError('BUNDLE_STORE_PATH_REFUSED') from None

    def _objects(self, backup=False):
        root = self.roots.backup_root if backup else self.roots.sealed_root
        return EvidenceObjectStore(root=root / 'payload-objects', limits=self.limits.object_limits)

    def _budget(self, backup):
        return self.limits.backup_budget if backup else self.limits.primary_budget

    def preview_payload(self, raw):
        self._configuration()
        _require(type(raw) is bytes, 'BUNDLE_STORE_PAYLOAD_INVALID')
        return None if raw == b'' else preview_payload(raw, limits=self.limits.object_limits).reference

    def _sync(self, root):
        if os.name != 'nt':
            descriptor = os.open(root, os.O_RDONLY | os.O_DIRECTORY | getattr(os, 'O_NOFOLLOW', 0))
            try:
                os.fsync(descriptor)
            finally:
                os.close(descriptor)

    def provision_empty(self):
        """Prepare two empty explicit roots; never initialize or adopt any head."""
        self._paths(prepared=False)
        _require(not any(self.roots.sealed_root.iterdir()) and not any(self.roots.backup_root.iterdir()),
                 'BUNDLE_STORE_ALREADY_PROVISIONED')
        try:
            for name, raw in (('session.lock', b'0'), ('catalog.jsonl', b'')):
                target = checked_target(self.roots.sealed_root / name, 'research store setup', within=self.roots.sealed_root)
                descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | _FLAGS, 0o600)
                with os.fdopen(descriptor, 'wb') as handle:
                    _require(handle.write(raw) == len(raw), 'BUNDLE_STORE_IO_REFUSED')
                    handle.flush(); os.fsync(handle.fileno())
            for backup in (False, True):
                objects = self._objects(backup)
                objects.initialize()
                objects.inventory(budget=self._budget(backup))
            for root in (self.roots.sealed_root, self.roots.backup_root):
                self._sync(root)
            self._paths()
        except BundleStoreError:
            raise
        except (OSError, ValueError, RuntimeError, TypeError):
            raise BundleStoreError('BUNDLE_STORE_PROVISION_FAILED') from None

    def _anchor(self):
        self._paths()
        paths = [self.roots.sealed_root / 'session.lock', self.roots.sealed_root / 'catalog.jsonl']
        for root in (self.roots.sealed_root, self.roots.backup_root):
            paths.extend((root / 'payload-objects', root / 'payload-objects' / 'objects',
                          root / 'payload-objects' / 'objects.lock'))
        paths.extend((self.head._dir, self.head._dir / 'head.lock'))
        return tuple((p, _identity(os.lstat(p))) for p in paths)

    def _check_anchor(self, anchor):
        self._paths()
        _require(self._anchor() == anchor, 'BUNDLE_STORE_STORAGE_CHANGED')

    @contextmanager
    def _locked(self):
        _require(_LOCK.acquire(blocking=False), 'BUNDLE_STORE_LOCKED')
        try:
            self._paths()
            # Missing heads refuse before any object staging or catalog change.
            self.head.read()
            target = self.roots.sealed_root / 'session.lock'
            before = os.lstat(target)
            descriptor = os.open(target, os.O_RDWR | _FLAGS)
            with os.fdopen(descriptor, 'r+b') as handle:
                opened = os.fstat(handle.fileno())
                _file(opened, 1)
                _require(_identity(before) == _identity(opened), 'BUNDLE_STORE_STORAGE_CHANGED')
                try:
                    if os.name == 'nt':
                        import msvcrt
                        handle.seek(0); msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                    else:
                        import fcntl
                        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                except OSError:
                    raise BundleStoreError('BUNDLE_STORE_LOCKED') from None
                try:
                    anchor = self._anchor()
                    _require(dict(anchor)[target] == _identity(opened), 'BUNDLE_STORE_STORAGE_CHANGED')
                    yield anchor
                    self._check_anchor(anchor)
                finally:
                    if os.name == 'nt':
                        handle.seek(0); msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                    else:
                        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        except (BundleStoreError, F.BundleFormatError):
            raise
        except BaselineHeadError:
            raise BundleStoreError('BUNDLE_STORE_HEAD_REFUSED') from None
        except EvidenceObjectError as exc:
            code = ('BUNDLE_STORE_RESOURCE_LIMIT' if 'LIMIT' in str(exc)
                    else 'BUNDLE_STORE_IO_REFUSED' if '_IO_' in str(exc)
                    else 'BUNDLE_STORE_OBJECT_REFUSED')
            raise BundleStoreError(code) from None
        except OSError as exc:
            code = 'BUNDLE_STORE_NO_SPACE' if exc.errno in (errno.ENOSPC, errno.EDQUOT) else 'BUNDLE_STORE_IO_REFUSED'
            raise BundleStoreError(code) from None
        except (ValueError, RuntimeError, TypeError):
            raise BundleStoreError('BUNDLE_STORE_IO_REFUSED') from None
        finally:
            _LOCK.release()

    def _read_catalog(self):
        self._paths()
        target = self.roots.sealed_root / 'catalog.jsonl'
        before = os.lstat(target)
        _file(before, self.limits.max_catalog_bytes)
        descriptor = os.open(target, os.O_RDONLY | _FLAGS)
        with os.fdopen(descriptor, 'rb') as handle:
            opened = os.fstat(handle.fileno())
            _file(opened, self.limits.max_catalog_bytes)
            _require(_identity(opened) == _identity(before), 'BUNDLE_STORE_STORAGE_CHANGED')
            raw = handle.read(self.limits.max_catalog_bytes + 1)
            after = os.fstat(handle.fileno())
        current = os.lstat(target)
        _file(current, self.limits.max_catalog_bytes)
        _require((*_identity(current), current.st_size, current.st_mtime_ns)
                 == (*_identity(after), after.st_size, after.st_mtime_ns)
                 == (*_identity(opened), opened.st_size, opened.st_mtime_ns)
                 and len(raw) == opened.st_size, 'BUNDLE_STORE_STORAGE_CHANGED')
        return raw

    def _catalog(self):
        """Validate shared chain and metadata only, not unrelated artifact graphs."""
        raw = self._read_catalog()
        _require(not raw or raw.endswith(b'\n'), 'BUNDLE_STORE_CATALOG_TRUNCATED')
        _require(raw.count(b'\n') <= self.limits.max_catalog_records, 'BUNDLE_STORE_RESOURCE_LIMIT')
        head, sequence, previous, last, entries, identities = self.genesis_digest, 0, None, None, {}, set()
        for line in raw.split(b'\n')[:-1] if raw else ():
            row = _decode(line)
            _require(type(row['schema']) is int and row['schema'] == 1
                     and type(row['sequence']) is int and row['sequence'] == sequence + 1
                     and row['previous_sha256'] == head and row['context_sha256'] == self.context_sha256
                     and row['event'] in _EVENTS and row['kind'] in _KINDS
                     and all(_hash(row[k]) for k in ('bundle_sha256', 'files_sha256', 'row_sha256'))
                     and all(type(row[k]) is str and _ID.fullmatch(row[k]) is not None
                             for k in ('run_id', 'revision_id', 'attempt_id'))
                     and row['row_sha256'] == _digest('row', {k:v for k,v in row.items() if k != 'row_sha256'}),
                     'BUNDLE_STORE_CATALOG_INVALID')
            decode_reference(_canonical(row['manifest_ref']))
            key = row['bundle_sha256']
            entry = entries.get(key)
            if row['event'] == 'PRIMARY_COMMITTED':
                identity = (row['run_id'], row['revision_id'])
                _require(entry is None and identity not in identities and row['code'] is None,
                         'BUNDLE_STORE_CATALOG_INVALID')
                identities.add(identity); entries[key] = _Entry(row)
            else:
                _require(entry is not None and all(row[k] == entry.row[k] for k in
                         ('kind', 'run_id', 'revision_id', 'attempt_id', 'manifest_ref', 'files_sha256')),
                         'BUNDLE_STORE_CATALOG_INVALID')
                if row['event'] == 'BACKUP_VERIFIED':
                    _require(not entry.backed and row['code'] is None, 'BUNDLE_STORE_CATALOG_INVALID')
                    entries[key] = replace(entry, backed=True)
                else:
                    _require(row['kind'] == 'RAW_ARCHIVED' and type(row['code']) is str
                             and _CODE.fullmatch(row['code']) is not None and row['code'] not in entry.diagnostics,
                             'BUNDLE_STORE_CATALOG_INVALID')
                    entries[key] = replace(entry, diagnostics=(*entry.diagnostics, row['code']))
            previous, head, sequence, last = head, row['row_sha256'], row['sequence'], row
        return _Catalog(head, sequence, len(raw), entries, previous, last)

    def _load(self):
        before = self.head.read()
        catalog = self._catalog()
        _require(catalog.head == before == self.head.read(), 'BUNDLE_STORE_HEAD_MISMATCH')
        return catalog

    def _manifest(self, kind, raw):
        parser = F.parse_raw_archive if kind == 'RAW_ARCHIVED' else F.parse_verified_bundle
        digest = F.raw_archive_digest if kind == 'RAW_ARCHIVED' else F.verified_bundle_digest
        manifest = parser(raw, limits=self.limits.format_limits)
        _require(manifest.storage_policy_sha256 == self.limits.policy_sha256
                 and manifest.object_policy_sha256 == self.limits.object_limits.policy_sha256,
                 'BUNDLE_STORE_POLICY_MISMATCH')
        return manifest, digest(manifest, limits=self.limits.format_limits)

    def _files_digest(self, manifest):
        return _digest('files', [asdict(item) for item in manifest.files])

    def _graph(self, entry, backup):
        objects = self._objects(backup)
        raw = objects.read(decode_reference(_canonical(entry.row['manifest_ref'])))
        manifest, digest = self._manifest(entry.row['kind'], raw)
        _require(digest == entry.row['bundle_sha256'] and self._files_digest(manifest) == entry.row['files_sha256']
                 and all(getattr(manifest, k) == entry.row[k] for k in ('run_id', 'revision_id', 'attempt_id')),
                 'BUNDLE_STORE_MANIFEST_MISMATCH')
        payloads = {}
        for item in manifest.files:
            value = b'' if item.payload_ref is None else objects.read(item.payload_ref)
            _require(self.preview_payload(value) == item.payload_ref, 'BUNDLE_STORE_REFERENCE_MISMATCH')
            payloads[item.logical_id] = value
        F.validate_payloads(manifest, payloads, limits=self.limits.format_limits)
        return StoredBundle(manifest_bytes=raw, manifest=manifest, files=MappingProxyType(payloads),
                            backup_verified=entry.backed)

    def _validate_graph(self, catalog, digest, *, require_backup):
        _require(_hash(digest) and digest in catalog.entries, 'BUNDLE_STORE_NOT_PUBLISHED')
        entry = catalog.entries[digest]
        _require(not require_backup or entry.backed, 'BUNDLE_STORE_BACKUP_REQUIRED')
        primary = self._graph(entry, False)
        if require_backup:
            backup = self._graph(entry, True)
            _require(backup == primary, 'BUNDLE_STORE_BACKUP_MISMATCH')
        if entry.row['kind'] == 'VERIFIED_UNAPPROVED':
            raw_digest = primary.manifest.input_archive_digest
            _require(raw_digest in catalog.entries and catalog.entries[raw_digest].row['kind'] == 'RAW_ARCHIVED',
                     'BUNDLE_STORE_RAW_ARCHIVE_REQUIRED')
            raw = self._validate_graph(catalog, raw_digest, require_backup=require_backup)
            F.validate_verified_inputs(raw.manifest, primary.manifest, limits=self.limits.format_limits)
        return primary

    def _receipt(self, entry):
        return BundleReceipt(kind=entry.row['kind'], bundle_digest=entry.row['bundle_sha256'],
            run_id=entry.row['run_id'], revision_id=entry.row['revision_id'], attempt_id=entry.row['attempt_id'],
            backup_verified=entry.backed)

    def inspect(self, digest):
        """Historical catalog metadata only; use read_* for actual graph verification."""
        with self._locked():
            catalog = self._load()
            _require(_hash(digest) and digest in catalog.entries, 'BUNDLE_STORE_NOT_PUBLISHED')
            return self._receipt(catalog.entries[digest])

    def _read(self, kind, digest, require_backup):
        _require(type(require_backup) is bool, 'BUNDLE_STORE_INPUT_INVALID')
        with self._locked():
            catalog = self._load()
            _require(_hash(digest) and digest in catalog.entries, 'BUNDLE_STORE_NOT_PUBLISHED')
            _require(catalog.entries[digest].row['kind'] == kind, 'BUNDLE_STORE_KIND_MISMATCH')
            result = self._validate_graph(catalog, digest, require_backup=require_backup)
            _require(self._load() == catalog, 'BUNDLE_STORE_STORAGE_CHANGED')
            return result

    def read_raw(self, digest, *, require_backup=True):
        return self._read('RAW_ARCHIVED', digest, require_backup)

    def read_verified(self, digest, *, require_backup=True):
        return self._read('VERIFIED_UNAPPROVED', digest, require_backup)

    def _row(self, catalog, event, source, *, code=None):
        row = {k: source[k] for k in ('kind', 'bundle_sha256', 'run_id', 'revision_id', 'attempt_id',
                                     'manifest_ref', 'files_sha256')}
        row.update(schema=1, sequence=catalog.sequence + 1, previous_sha256=catalog.head,
                   context_sha256=self.context_sha256, event=event, code=code)
        row['row_sha256'] = _digest('row', row)
        return row

    def _admit_catalog(self, catalog, rows):
        _require(catalog.sequence + len(rows) <= self.limits.max_catalog_records
                 and all(len(_canonical(row)) + 1 <= _ROW_MAX for row in rows)
                 and catalog.size + sum(len(_canonical(row)) + 1 for row in rows) <= self.limits.max_catalog_bytes,
                 'BUNDLE_STORE_RESOURCE_LIMIT')

    def _admit_objects(self, values, backup):
        inventory = self._objects(backup).inventory(budget=self._budget(backup))
        entries = {item.name:item for item in inventory.entries}
        for value in values:
            if not value:
                continue
            preview = preview_payload(value, limits=self.limits.object_limits)
            admit_store_budget(preview, StoreInventory(entries=tuple(sorted(entries.values(), key=lambda i:i.name))),
                               self._budget(backup))
            for item in preview.objects:
                name = 'objects/' + item.sha256 + '.blob'
                entries.setdefault(name, InventoryEntry(name=name, byte_count=item.byte_count))

    def _stage(self, values, backup, anchor):
        objects = self._objects(backup)
        for value in values:
            if not value:
                continue
            self._check_anchor(anchor)
            reference = objects.stage(value, budget=self._budget(backup))
            _require(reference == self.preview_payload(value) and objects.read(reference) == value,
                     'BUNDLE_STORE_REFERENCE_MISMATCH')
            self._check_anchor(anchor)

    def _append(self, catalog, row, anchor):
        self._admit_catalog(catalog, (row,))
        _require(self._load() == catalog, 'BUNDLE_STORE_STORAGE_CHANGED')
        self._check_anchor(anchor)
        line = _canonical(row) + b'\n'
        target = self.roots.sealed_root / 'catalog.jsonl'
        before = os.lstat(target)
        descriptor = os.open(target, os.O_WRONLY | os.O_APPEND | _FLAGS)
        with os.fdopen(descriptor, 'ab') as handle:
            opened = os.fstat(handle.fileno())
            _file(opened, self.limits.max_catalog_bytes)
            _require((*_identity(before), before.st_size) == (*_identity(opened), catalog.size),
                     'BUNDLE_STORE_STORAGE_CHANGED')
            _require(handle.write(line) == len(line), 'BUNDLE_STORE_IO_REFUSED')
            handle.flush(); os.fsync(handle.fileno())
            written = os.fstat(handle.fileno())
        current = os.lstat(target)
        _file(current, self.limits.max_catalog_bytes)
        _require(_identity(current) == _identity(written) == _identity(opened)
                 and current.st_size == written.st_size == catalog.size + len(line), 'BUNDLE_STORE_STORAGE_CHANGED')
        self._check_anchor(anchor)
        _require(self.head.compare_and_set(catalog.head, row['row_sha256']) is True, 'BUNDLE_STORE_HEAD_UPDATE_REFUSED')
        self._check_anchor(anchor)
        _require(self.head.read() == row['row_sha256'], 'BUNDLE_STORE_HEAD_MISMATCH')
        result = self._load()
        _require(result.head == row['row_sha256'] and result.size == catalog.size + len(line)
                 and result.sequence == catalog.sequence + 1, 'BUNDLE_STORE_STORAGE_CHANGED')
        return result

    def _commit(self, kind, raw, payloads):
        self._configuration()
        manifest, digest = self._manifest(kind, raw)
        F.validate_payloads(manifest, payloads, limits=self.limits.format_limits)
        payloads = dict(payloads)  # immutable byte snapshot; caller mapping is never read again
        F.validate_payloads(manifest, payloads, limits=self.limits.format_limits)
        for item in manifest.files:
            _require(self.preview_payload(payloads[item.logical_id]) == item.payload_ref,
                     'BUNDLE_STORE_REFERENCE_MISMATCH')
        reference = self.preview_payload(raw)
        source = dict(kind=kind, bundle_sha256=digest, run_id=manifest.run_id, revision_id=manifest.revision_id,
                      attempt_id=manifest.attempt_id, manifest_ref=asdict(reference), files_sha256=self._files_digest(manifest))
        values = tuple(payloads[item.logical_id] for item in manifest.files) + (raw,)
        with self._locked() as anchor:
            catalog = self._load()
            existing = catalog.entries.get(digest)
            _require(not any(entry.row['run_id'] == manifest.run_id
                             and entry.row['revision_id'] == manifest.revision_id
                             and entry.row['bundle_sha256'] != digest for entry in catalog.entries.values()),
                     'BUNDLE_STORE_ID_REUSED')
            if kind == 'VERIFIED_UNAPPROVED':
                _require(manifest.input_archive_digest in catalog.entries
                         and catalog.entries[manifest.input_archive_digest].row['kind'] == 'RAW_ARCHIVED',
                         'BUNDLE_STORE_RAW_ARCHIVE_REQUIRED')
                archived = self._validate_graph(catalog, manifest.input_archive_digest, require_backup=True)
                F.validate_verified_inputs(archived.manifest, manifest, limits=self.limits.format_limits)
            if existing is not None:
                retained = self._validate_graph(catalog, digest, require_backup=existing.backed)
                _require(retained.manifest_bytes == raw and dict(retained.files) == payloads,
                         'BUNDLE_STORE_ID_REUSED')
                if existing.backed:
                    return self._receipt(existing)
            # Admission for the whole primary+backup operation, before staging any bytes.
            primary_row = self._row(catalog, 'PRIMARY_COMMITTED', source) if existing is None else None
            predicted = catalog if primary_row is None else replace(catalog, head=primary_row['row_sha256'],
                            sequence=catalog.sequence + 1, size=catalog.size + len(_canonical(primary_row)) + 1)
            backup_row = self._row(predicted, 'BACKUP_VERIFIED', source)
            self._admit_catalog(catalog, (backup_row,) if primary_row is None else (primary_row, backup_row))
            self._admit_objects(values, False)
            self._admit_objects(values, True)
            if primary_row is not None:
                self._stage(values, False, anchor)
                self._graph(_Entry(primary_row), False)
                catalog = self._append(catalog, primary_row, anchor)
            # Backup consists of actual destination objects, never links to primary.
            self._stage(values, True, anchor)
            _require(self._graph(catalog.entries[digest], False) == self._graph(catalog.entries[digest], True),
                     'BUNDLE_STORE_BACKUP_MISMATCH')
            catalog = self._append(catalog, self._row(catalog, 'BACKUP_VERIFIED', source), anchor)
            self._validate_graph(catalog, digest, require_backup=True)
            self._check_anchor(anchor)
            return self._receipt(catalog.entries[digest])

    def archive_raw(self, manifest, payloads):
        return self._commit('RAW_ARCHIVED', manifest, payloads)

    def commit_verified(self, manifest, payloads):
        return self._commit('VERIFIED_UNAPPROVED', manifest, payloads)

    def record_diagnostic(self, raw_digest, code):
        """Preserve a bounded incident against an existing raw ID; not a failed-evaluation issuer.

        This metadata event can record damage even when that raw graph is unreadable.
        It does not assert collection completeness, source authenticity or approval.
        """
        _require(_hash(raw_digest) and type(code) is str and _CODE.fullmatch(code) is not None,
                 'BUNDLE_STORE_DIAGNOSTIC_INVALID')
        with self._locked() as anchor:
            catalog = self._load()
            _require(raw_digest in catalog.entries and catalog.entries[raw_digest].row['kind'] == 'RAW_ARCHIVED',
                     'BUNDLE_STORE_RAW_ARCHIVE_REQUIRED')
            entry = catalog.entries[raw_digest]
            if code not in entry.diagnostics:
                catalog = self._append(catalog, self._row(catalog, 'DIAGNOSTIC', entry.row, code=code), anchor)
            return self._receipt(catalog.entries[raw_digest])
