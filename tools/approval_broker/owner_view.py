"""Independent actual owner observation; verified history is not grant eligibility.

No app loader, caller status, private key, or approving callback is consumed.
The operator pins the first key and a real signed prefix independently. Current
code failure is reported separately so an authentic restrictive head can first
be retained by the authority ledger.
"""
from __future__ import annotations

import base64
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import hashlib
import json
from pathlib import Path
import stat

from tools.signer import sign as S
from . import authority_contract as A
from . import contract as C
from .release import target_deployment_code_hash

OwnerLogEvidence = A.OwnerLogEvidence
_MAX_LOG = 8 * 1024 * 1024
_MAX_ROWS = 32768
_MAX_ANCHORS = 8192


def _lines(raw):
    C.binary(raw, _MAX_LOG)
    count = raw.count(b'\n')
    C.need(0 < count <= _MAX_ROWS, 'PASSKEY_RESOURCE_LIMIT')
    C.need(raw.endswith(b'\n') and b'\r' not in raw, 'PASSKEY_OWNER_LOG_INVALID')
    return tuple(part+b'\n' for part in raw[:-1].split(b'\n'))


@dataclass(frozen=True, slots=True, kw_only=True)
class OwnerLocations:
    app_repo: Path = field(repr=False)
    app_environment: Path = field(repr=False)
    compliance_root: Path = field(repr=False)
    public_key_path: Path = field(repr=False)

    def __post_init__(self):
        for value in (self.app_repo, self.app_environment, self.compliance_root, self.public_key_path):
            C.need(isinstance(value, Path) and value.is_absolute() and '..' not in value.parts,
                   'PASSKEY_OWNER_LOCATION_INVALID')


@dataclass(frozen=True, slots=True, kw_only=True)
class TrustRoots:
    initial_public_key_raw: bytes
    initial_owner_head: A.Head
    recovery_public_key_raw: bytes

    def __post_init__(self):
        C.binary(self.initial_public_key_raw, 32, minimum=32)
        C.binary(self.recovery_public_key_raw, 32, minimum=32)
        C.checked(self.initial_owner_head, A.Head)
        C.need(self.initial_owner_head.sequence > 0, 'PASSKEY_OWNER_PREFIX_INVALID')


@dataclass(frozen=True, slots=True, kw_only=True)
class OwnerObservation:
    evidence: OwnerLogEvidence = field(repr=False)
    deployment_code_sha256: str | None
    deployment_problem: str | None
    completed_at: datetime

    def __post_init__(self):
        C.checked(self.evidence, OwnerLogEvidence)
        C.instant(self.completed_at)
        C.need(self.completed_at >= self.evidence.completed_at, 'PASSKEY_CLOCK_ROLLBACK')
        if self.deployment_code_sha256 is None:
            C.need(self.deployment_problem == 'PASSKEY_DEPLOYMENT_REFUSED')
        else:
            C.hashed(self.deployment_code_sha256)
            C.need(self.deployment_problem is None)


def _entries(evidence, roots):
    C.checked(roots, TrustRoots)
    C.checked(evidence, OwnerLogEvidence)
    C.binary(evidence.public_key_raw, 32, minimum=32)
    C.binary(evidence.log_bytes, _MAX_LOG)
    C.need(type(evidence.anchors) is tuple and len(evidence.anchors) <= _MAX_ANCHORS,
           'PASSKEY_RESOURCE_LIMIT')
    lines = _lines(evidence.log_bytes)
    C.need(evidence.observed_at <= evidence.completed_at, 'PASSKEY_CLOCK_ROLLBACK')
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    from cryptography.exceptions import InvalidSignature
    current = roots.initial_public_key_raw
    rows, previous = [], S.GENESIS_PREV
    try:
        for number, line in enumerate(lines, 1):
            row = S._parse_line(number, line, previous)
            if row['kind'] in S.SCHEMAS:
                Ed25519PublicKey.from_public_bytes(current).verify(base64.b64decode(row['sig']),
                    S.SIG_DOMAIN + row['row_sha256'].encode('ascii'))
            if row['kind'] == 'key_rotated':
                C.need(base64.b64decode(row['data']['old_pubkey_b64']) == current,
                       'PASSKEY_OWNER_KEY_CHANGED')
                current = base64.b64decode(row['data']['new_pubkey_b64'])
            previous = row['row_sha256']
            rows.append(row)
    except C.PasskeyError:
        raise
    except (ValueError, TypeError, KeyError, ArithmeticError, RecursionError, InvalidSignature):
        raise C.PasskeyError('PASSKEY_OWNER_LOG_INVALID') from None
    C.need(rows and current == evidence.public_key_raw, 'PASSKEY_OWNER_KEY_CHANGED')
    C.need(evidence.head == A.Head(sequence=len(rows), sha256=previous), 'PASSKEY_OWNER_PREFIX_INVALID')
    for head in (roots.initial_owner_head, *evidence.anchors):
        C.checked(head, A.Head)
        C.need((head.sequence == 0 and head.sha256 == S.GENESIS_PREV) or
               (0 < head.sequence <= len(rows) and rows[head.sequence-1]['row_sha256'] == head.sha256),
               'PASSKEY_OWNER_PREFIX_INVALID')
    return tuple(rows)


def verify_owner_evidence(evidence, *, roots, previous):
    """Real historical signatures and independently rooted prefix; no current I/O."""
    rows = _entries(evidence, roots)
    if previous is not None:
        old = _entries(previous, roots)
        C.need(len(rows) >= len(old) and evidence.log_bytes.startswith(previous.log_bytes)
               and rows[len(old)-1]['row_sha256'] == previous.head.sha256,
               'PASSKEY_OWNER_PREFIX_INVALID')
        C.need(set(previous.anchors) <= set(evidence.anchors), 'PASSKEY_OWNER_PREFIX_INVALID')
        C.need(evidence.observed_at >= previous.completed_at, 'PASSKEY_CLOCK_ROLLBACK')


def _object(raw):
    try:
        result = json.loads(raw.decode('utf-8'), object_pairs_hook=S._no_duplicates)
    except (ValueError, UnicodeError, RecursionError):
        raise C.PasskeyError('PASSKEY_OWNER_ANCHOR_INVALID') from None
    C.need(type(result) is dict, 'PASSKEY_OWNER_ANCHOR_INVALID')
    return result


def _anchor(sequence, digest):
    if type(sequence) is int and sequence == 0 and digest == '':
        return A.Head(sequence=0, sha256=S.GENESIS_PREV)
    C.need(type(sequence) is int and 0 < sequence < 2**63, 'PASSKEY_OWNER_ANCHOR_INVALID')
    return A.Head(sequence=sequence, sha256=digest)


def _anchor_snapshot(root, initial_key):
    """Retain exact external inventory and bytes, including strict restriction files."""
    anchors, snapshot = set(), []
    scanned = total_bytes = 0
    def count(amount=1):
        nonlocal scanned
        scanned += amount
        C.need(scanned <= _MAX_ANCHORS, 'PASSKEY_RESOURCE_LIMIT')
    def read(path, maximum):
        nonlocal total_bytes
        count()
        size = path.lstat().st_size
        C.need(0 <= size <= maximum and total_bytes+size <= _MAX_LOG, 'PASSKEY_RESOURCE_LIMIT')
        raw, identity = S._bundle_read(path, maximum)
        total_bytes += len(raw)
        snapshot.append((path.relative_to(root).as_posix(), identity, hashlib.sha256(raw).hexdigest()))
        return raw
    with S._BundlePin(root) as pin:
        names = pin.names(32768)
        if 'alerts.jsonl' in names:
            raw = read(root/'alerts.jsonl', _MAX_LOG)
            C.need(raw.count(b'\n') <= _MAX_ANCHORS, 'PASSKEY_RESOURCE_LIMIT')
            first = None
            for line in raw.split(b'\n'):
                if not line.strip():
                    continue
                row = _object(line)
                anchors.add(_anchor(row.get('head_seq'), row.get('head_sha256')))
                if first is None and type(row.get('fingerprint')) is str and row['fingerprint']:
                    first = row['fingerprint']
            C.need(first is None or first == S.fingerprint(initial_key), 'PASSKEY_OWNER_KEY_CHANGED')
        for folder in ('snapshots', 'approved'):
            if folder not in names:
                snapshot.append((folder, None, None))
                continue
            directory = root/folder
            count()
            with S._BundlePin(directory) as sub:
                snapshot.append((folder, sub.rows[-1][2] if sub.rows else sub.native.identity, None))
                children = sub.names(_MAX_ANCHORS)
                if folder == 'snapshots':
                    for name in sorted(children):
                        count()
                        if name.endswith('.json'):
                            body = _object(read(directory/name, _MAX_LOG))
                            head = body.get('head')
                            C.need(type(head) is list and len(head) == 2, 'PASSKEY_OWNER_ANCHOR_INVALID')
                            anchors.add(_anchor(*head))
                else:
                    for kind in sorted(children):
                        count()
                        info = sub.stat(kind)
                        C.need(stat.S_ISDIR(info.st_mode), 'PASSKEY_OWNER_ANCHOR_INVALID')
                        with S._BundlePin(directory/kind) as leaves:
                            entries = leaves.names(_MAX_ANCHORS)
                            for name in sorted(entries):
                                count()
                                if kind == 'research-attestations':
                                    C.need(name.endswith('.anchor.json') and len(name) == 76,
                                           'PASSKEY_OWNER_ANCHOR_INVALID')
                                    C.hashed(name[:-12])
                                if name.endswith('.anchor.json'):
                                    body = _object(read(directory/kind/name, 4096))
                                    if kind == 'research-attestations':
                                        C.keys(body, ('seq', 'row_sha256'))
                                        C.need(body['row_sha256'] == name[:-12], 'PASSKEY_OWNER_ANCHOR_INVALID')
                                    anchors.add(_anchor(body.get('seq'), body.get('row_sha256')))
                                C.need(len(anchors) <= _MAX_ANCHORS, 'PASSKEY_RESOURCE_LIMIT')
        pin.check()
    return tuple(sorted(anchors, key=lambda h:(h.sequence,h.sha256))), tuple(snapshot)


class OwnerReader:
    def __init__(self, *, locations, roots, clock):
        C.checked(locations, OwnerLocations); C.checked(roots, TrustRoots)
        C.need(callable(clock), 'PASSKEY_CLOCK_INVALID')
        self.locations, self.roots, self.clock = locations, roots, clock
        self._configuration = (locations, roots, clock)
        self._parameters = self._parameters_now()
        self._identities = None
        self._last = None

    def _parameters_now(self):
        C.checked(self.locations, OwnerLocations); C.checked(self.roots, TrustRoots)
        return (str(self.locations.app_repo),str(self.locations.app_environment),
            str(self.locations.compliance_root),str(self.locations.public_key_path),
            self.roots.initial_public_key_raw,self.roots.initial_owner_head.sequence,
            self.roots.initial_owner_head.sha256,self.roots.recovery_public_key_raw)

    def observe(self, *, retained):
        C.need((self.locations, self.roots, self.clock) == self._configuration
               and self.clock is self._configuration[2] and self._parameters_now()==self._parameters,
               'PASSKEY_OWNER_LOCATION_INVALID')
        locations, roots, clock = self._configuration
        C.checked(locations, OwnerLocations); C.checked(roots, TrustRoots)
        begin = C.instant(clock())
        C.need(self._last is None or begin >= self._last, 'PASSKEY_CLOCK_ROLLBACK')
        try:
            paths = (locations.app_repo, locations.app_environment, locations.compliance_root,
                     locations.public_key_path.parent)
            identities = tuple((str(p), S._bundle_directory(p)[1][:2]) for p in paths)
            C.need(self._identities is None or identities == self._identities, 'PASSKEY_OWNER_LOCATION_INVALID')
            raw, log_identity = S._bundle_read(locations.compliance_root/'owner.jsonl', _MAX_LOG)
            pem, pem_identity = S._bundle_read(locations.public_key_path, 4096)
            public = S._pem_raw(pem)
            anchors, inventory = _anchor_snapshot(locations.compliance_root, roots.initial_public_key_raw)
            head = S._head(_lines(raw))
            evidence = OwnerLogEvidence(public_key_raw=public, log_bytes=raw, anchors=anchors,
                observed_at=begin, completed_at=begin, head=A.Head(sequence=head[0], sha256=head[1]))
            verify_owner_evidence(evidence, roots=roots, previous=retained)
            try:
                code = target_deployment_code_hash(locations.app_repo, locations.app_environment)
                problem = None
            except (C.PasskeyError, ValueError, OSError):
                code, problem = None, 'PASSKEY_DEPLOYMENT_REFUSED'
            C.need(S._bundle_read(locations.compliance_root/'owner.jsonl', _MAX_LOG) == (raw,log_identity)
                   and S._bundle_read(locations.public_key_path,4096) == (pem,pem_identity)
                   and _anchor_snapshot(locations.compliance_root,roots.initial_public_key_raw) == (anchors,inventory)
                   and tuple((str(p),S._bundle_directory(p)[1][:2]) for p in paths) == identities
                   and self._parameters_now()==self._parameters and self.clock is clock,
                   'PASSKEY_OWNER_CHANGED')
            finish = C.instant(clock())
            C.need(finish >= begin, 'PASSKEY_CLOCK_ROLLBACK')
            evidence = OwnerLogEvidence(public_key_raw=public, log_bytes=raw, anchors=anchors,
                observed_at=begin, completed_at=finish, head=evidence.head)
            self._identities, self._last = identities, finish
            return OwnerObservation(evidence=evidence,deployment_code_sha256=code,
                deployment_problem=problem,completed_at=finish)
        except C.PasskeyError:
            raise
        except (ValueError, OSError, TypeError, AttributeError, OverflowError):
            raise C.PasskeyError('PASSKEY_OWNER_READ_REFUSED') from None


def require_grant_eligibility(grant, observation, *, at):
    """Current verified observation against the exact grant; never persists a head."""
    C.checked(observation, OwnerObservation)
    body = C.decode(A.grant_bytes(grant), maximum=2*1024*1024)['body']
    evidence = observation.evidence
    now = C.instant(at)
    C.need(evidence.observed_at <= evidence.completed_at <= observation.completed_at <= now,
           'PASSKEY_CLOCK_ROLLBACK')
    C.need(now-evidence.observed_at <= timedelta(seconds=30), 'PASSKEY_OWNER_STALE')
    C.need(C.time_value(body['issued_at']) <= now < C.time_value(body['expires_at']), 'PASSKEY_EXPIRED')
    checkpoint = body['owner_checkpoint']
    C.need(S.fingerprint(evidence.public_key_raw) == checkpoint['fingerprint'], 'PASSKEY_OWNER_KEY_CHANGED')
    C.need(observation.deployment_problem is None and observation.deployment_code_sha256 == checkpoint['code_sha256'],
           'PASSKEY_DEPLOYMENT_CHANGED')
    rows = tuple(json.loads(line) for line in _lines(evidence.log_bytes))
    old = checkpoint['owner_head']
    C.need(0 < old['sequence'] <= len(rows) and rows[old['sequence']-1]['row_sha256'] == old['sha256'],
           'PASSKEY_OWNER_PREFIX_INVALID')
    approvals = tuple((row['utc'],row['data']['sha256']) for row in rows if row['kind']=='code_approved')
    C.need(S._bundle_code_approval_at(approvals,now) == observation.deployment_code_sha256,
           'PASSKEY_DEPLOYMENT_CHANGED')
    return A.OwnerCheckpoint(fingerprint=S.fingerprint(evidence.public_key_raw),
        code_sha256=observation.deployment_code_sha256,owner_head=evidence.head,observed_at=evidence.observed_at)
