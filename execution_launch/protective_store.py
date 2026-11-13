"""Durable P1 model state and outbox, not a lifecycle, signature or order authority.

Explicit temporary/provisioned roots only. A complete transition (supplied facts,
external ledger references, recomputed state and every reducer effect) is one P0
payload, followed by a small chained journal row, then an independent head CAS.
No state or newly pending effect is returned before head readback succeeds.

Inspection is historical model evidence, never current execution eligibility.
Every reopened nonempty writer must first commit a restart event. P1 then keeps
entry blocked until its separate reconciliation and explicit rearm gates pass.
Those facts remain caller-supplied models, NOT verified approvals. There is no
broker adapter, approval application, reduction dispatch/ack, automatic head
initialization, re-anchor, backup adoption or signed exact-recovery issuer here.
Notification delivery is not owner approval. Risk/high/floor/halt references are
opaque references to the authoritative ledgers; this log never changes them.

Lock order: singleton session -> object store (released) -> head -> object read
during the head's successor check. The successor check never takes the session
lock or reads the head. No object lock is held while acquiring the head lock.
Journal/head disagreement is preserved and refused, never silently repaired.
An attacker/coherent rollback controlling both roots is outside this discipline;
hashes are not provenance. Windows power-loss durability is not established.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import asdict, dataclass, fields, replace
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import stat
from threading import get_ident

from core.isolation import checked_target, state_root
from execution_launch import protective_state as P
from execution_launch.baseline_head import BaselineHead, BaselineHeadError
from execution_launch.evidence_objects import (
    EvidenceObjectError, EvidenceObjectStore, ObjectLimits, PayloadReference, StoreBudget,
)

_DOMAIN = b"TRADEGEN-PROTECTIVE-STORE-v1\x00"
_HASH = re.compile(r"[0-9a-f]{64}")
_MAX_ROW = 16384
_MAX_JOURNAL = 256 * 1024 * 1024
_MAX_RECORDS = 100000
_FLAGS = getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_BINARY", 0)
_ROW_KEYS = {"schema", "sequence", "previous_sha256", "context_sha256", "payload_ref", "row_sha256"}
_TRANSITION_KEYS = {"schema", "kind", "context_sha256", "event", "authority", "observations", "ledger_refs",
                    "state", "effects"}
_RECEIPT_KEYS = {"schema", "kind", "context_sha256", "receipt"}
_DATETIMES = {"checked_at", "issued_at", "entry_until", "reduce_until", "cancel_until", "monitor_until",
              "holding_deadline", "at", "last_event_at", "not_after"}


class ProtectiveStoreError(ValueError):
    """Fixed codes only: never provider text, account values, filenames or paths."""


def _require(condition, code):
    if not condition:
        raise ProtectiveStoreError(code)


def _hash(value):
    return type(value) is str and _HASH.fullmatch(value) is not None


def _identity(info):
    _require(type(info.st_dev) is int and info.st_dev >= 0 and type(info.st_ino) is int and info.st_ino > 0,
             "PROTECTIVE_STORE_IDENTITY_UNAVAILABLE")
    return info.st_dev, info.st_ino


def _plain(value):
    if type(value) is datetime:
        _require(value.utcoffset() is not None, "PROTECTIVE_STORE_TIME_INVALID")
        return value.astimezone(timezone.utc).isoformat(timespec="microseconds")
    if type(value) is dict:
        return {key: _plain(item) for key, item in value.items()}
    if type(value) in (tuple, list):
        return [_plain(item) for item in value]
    return value


def _canonical(value):
    return json.dumps(_plain(value), sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                      allow_nan=False).encode("ascii")


def _digest(kind, value):
    return hashlib.sha256(_DOMAIN + kind.encode("ascii") + b"\x00" + _canonical(value)).hexdigest()


def _body(value):
    return _plain(asdict(value))


def _parse_time(value):
    _require(type(value) is str, "PROTECTIVE_STORE_RECORD_INVALID")
    try:
        result = datetime.fromisoformat(value)
        _require(_plain(result) == value, "PROTECTIVE_STORE_RECORD_INVALID")
        return result
    except (ValueError, TypeError, OverflowError):
        raise ProtectiveStoreError("PROTECTIVE_STORE_RECORD_INVALID") from None


def _typed(cls, body):
    _require(type(body) is dict and set(body) == {item.name for item in fields(cls)},
             "PROTECTIVE_STORE_RECORD_INVALID")
    values = dict(body)
    for key, value in body.items():
        if key in _DATETIMES and value is not None:
            values[key] = _parse_time(value)
        if key in ("reasons", "risk_causes"):
            _require(type(value) is list, "PROTECTIVE_STORE_RECORD_INVALID")
            values[key] = tuple(value)
    try:
        result = cls(**values)
        _require(_body(result) == body, "PROTECTIVE_STORE_RECORD_INVALID")
        return result
    except (TypeError, ValueError, OverflowError):
        raise ProtectiveStoreError("PROTECTIVE_STORE_RECORD_INVALID") from None


def _decode(raw, maximum):
    _require(type(raw) is bytes and 0 < len(raw) <= maximum, "PROTECTIVE_STORE_RECORD_INVALID")
    # Bound structure before json.loads; quoted JSON characters do not count.
    depth, count, quoted, escaped = 0, 0, False, False
    for char in raw:
        if quoted:
            if escaped:
                escaped = False
            elif char == 92:
                escaped = True
            elif char == 34:
                quoted = False
        elif char == 34:
            quoted = True
        elif char in (91, 123):
            depth += 1
            count += 1
        elif char in (93, 125):
            depth -= 1
        elif char in (44, 58):
            count += 1
        _require(depth <= 12 and count <= 10000, "PROTECTIVE_STORE_RECORD_INVALID")

    def pairs(items):
        result = {}
        for key, value in items:
            _require(key not in result, "PROTECTIVE_STORE_RECORD_INVALID")
            result[key] = value
        return result

    def invalid(_):
        raise ProtectiveStoreError("PROTECTIVE_STORE_RECORD_INVALID")
    try:
        body = json.loads(raw.decode("ascii"), object_pairs_hook=pairs, parse_float=invalid, parse_constant=invalid)
        _require(type(body) is dict and _canonical(body) == raw, "PROTECTIVE_STORE_RECORD_INVALID")
        return body
    except (ValueError, TypeError, UnicodeError, RecursionError, OverflowError):
        raise ProtectiveStoreError("PROTECTIVE_STORE_RECORD_INVALID") from None


@dataclass(frozen=True, kw_only=True)
class StoreBinding:
    """Caller-supplied context commitments, not proof of research or code approval."""
    driver_identity_sha256: str
    research_sha256: str
    source_sha256: str

    def __post_init__(self):
        _require(all(_hash(value) for value in asdict(self).values()), "PROTECTIVE_STORE_BINDING_INVALID")


@dataclass(frozen=True, kw_only=True)
class LedgerReferences:
    """Opaque authoritative-record references. None is unknown, never zero P&L or an unchanged floor.

    These references preserve dependencies for later independent verification.
    Their mere presence does not authenticate a ledger or permit reconciliation.
    """
    account_head_sha256: str | None
    orders_head_sha256: str | None
    risk_head_sha256: str | None
    high_water_sha256: str | None
    floor_sha256: str | None
    halt_sha256: str | None
    source_evidence_sha256: str | None

    def __post_init__(self):
        _require(all(value is None or _hash(value) for value in asdict(self).values()),
                 "PROTECTIVE_STORE_LEDGER_REFS_INVALID")


@dataclass(frozen=True, kw_only=True)
class StoreLimits:
    object_limits: ObjectLimits
    object_budget: StoreBudget
    max_journal_bytes: int
    max_records: int

    def __post_init__(self):
        _require(type(self.object_limits) is ObjectLimits and type(self.object_budget) is StoreBudget
                 and type(self.max_journal_bytes) is int and 1 <= self.max_journal_bytes <= _MAX_JOURNAL
                 and type(self.max_records) is int and 1 <= self.max_records <= _MAX_RECORDS,
                 "PROTECTIVE_STORE_LIMITS_INVALID")
        try:
            self.object_limits.__post_init__()
            self.object_budget.__post_init__()
        except EvidenceObjectError:
            raise ProtectiveStoreError("PROTECTIVE_STORE_LIMITS_INVALID") from None


@dataclass(frozen=True, kw_only=True)
class NotificationReceipt:
    """Untrusted delivery observation only; never authentication, consent or request application.

    One attempt has one immutable outcome. A failed/unknown notification may be
    retried under a fresh attempt ID while retaining the same logical effect ID.
    """
    effect_id: str
    attempt_id: str
    outcome: str
    at: datetime

    def __post_init__(self):
        _require(_hash(self.effect_id) and _hash(self.attempt_id) and type(self.outcome) is str
                 and self.outcome in ("delivered", "failed", "unknown"), "PROTECTIVE_STORE_RECEIPT_INVALID")
        _require(type(self.at) is datetime and self.at.utcoffset() is not None, "PROTECTIVE_STORE_RECEIPT_INVALID")


@dataclass(frozen=True, kw_only=True)
class StoreSnapshot:
    """Historical/model-only view. It is never a production permission or current account assertion."""
    state: P.ManagementState
    head: str
    journal_sequence: int
    outbox: tuple[P.EffectIntent, ...]
    receipts: tuple[NotificationReceipt, ...]
    ledger_refs: LedgerReferences | None
    restart_required: bool

    @property
    def pending_notifications(self):
        delivered = {item.effect_id for item in self.receipts if item.outcome == "delivered"}
        return tuple(item for item in self.outbox if item.kind in ("notify", "request_management_approval")
                     and item.intent_id not in delivered)

    @property
    def unresolved_reductions(self):
        # P2 cannot discharge these obligations; no notification receipt can do it.
        return tuple(item for item in self.outbox if item.kind == "consider_reduce")


def _merge_effects(outbox, effects):
    known = {item.intent_id: item for item in outbox}
    for item in effects:
        previous = known.get(item.intent_id)
        _require(previous is None or previous == item, "PROTECTIVE_STORE_EFFECT_ID_COLLISION")
        if previous is None:
            known[item.intent_id] = item
    return tuple(known.values())


def _pending_consistency(snapshot, observations, state=None, effects=()):
    # The store knows its own queued reduction obligations. Caller facts cannot
    # erase them, and notification delivery cannot settle a reduction. P3 must
    # introduce separately verified execution/reconciliation before any clearing
    # API exists. This P2 model therefore conservatively leaves them unresolved.
    if snapshot.unresolved_reductions and observations is not None:
        _require(not observations.no_pending_reduce, "PROTECTIVE_STORE_PENDING_REDUCTION_CONFLICT")
    if state is not None:
        pending = snapshot.unresolved_reductions or any(item.kind == "consider_reduce" for item in effects)
        _require(not pending or not state.can_enter, "PROTECTIVE_STORE_PENDING_ENTRY_CONFLICT")


def _add_receipt(snapshot, receipt):
    _require(type(receipt) is NotificationReceipt, "PROTECTIVE_STORE_RECEIPT_INVALID")
    receipt.__post_init__()
    target = next((item for item in snapshot.outbox if item.intent_id == receipt.effect_id), None)
    _require(target is not None and target.kind in ("notify", "request_management_approval"),
             "PROTECTIVE_STORE_RECEIPT_TARGET_INVALID")
    for previous in snapshot.receipts:
        if previous.attempt_id == receipt.attempt_id:
            _require(previous == receipt, "PROTECTIVE_STORE_RECEIPT_REWRITTEN")
            return snapshot.receipts
    _require(not any(item.effect_id == receipt.effect_id and item.outcome == "delivered"
                     for item in snapshot.receipts), "PROTECTIVE_STORE_ALREADY_DELIVERED")
    return (*snapshot.receipts, receipt)


class _ProtectiveChain:
    """Head's verifier reads full committed graph without taking session/head locks."""
    def __init__(self, store):
        self.store = store

    def seed(self, digest):
        self.store._configuration()
        raw = self.store._read_journal()
        _require(digest == self.store.genesis_digest and not raw, "PROTECTIVE_STORE_SEED_REQUIRED")
        inventory = self.store._objects().inventory(budget=self.store.limits.object_budget)
        _require(inventory.object_count == 1, "PROTECTIVE_STORE_SEED_REQUIRED")
        return 0

    def successor(self, old, new):
        snapshot, _, last_previous = self.store._replay()
        _require(snapshot.journal_sequence > 0 and snapshot.head == new and last_previous == old,
                 "PROTECTIVE_STORE_SUCCESSOR_INVALID")
        return snapshot.journal_sequence


class ProtectiveStore:
    """One explicit, dedicated state-root child and a separately provisioned independent head.

    Construction creates nothing. provision_empty creates storage only; the
    operator's existing explicit head-provisioning procedure remains separate.
    That procedure itself cannot prove review and is never called by this module.
    """
    def __init__(self, *, root: Path, head_root: Path, head_name: str, policy: P.ManagementPolicy,
                 binding: StoreBinding, limits: StoreLimits):
        _require(isinstance(root, Path) and root.is_absolute() and ".." not in root.parts,
                 "PROTECTIVE_STORE_ROOT_INVALID")
        _require(type(binding) is StoreBinding and type(limits) is StoreLimits,
                 "PROTECTIVE_STORE_CONTEXT_INVALID")
        self.root, self.policy, self.binding, self.limits = root, policy, binding, limits
        self._fixed_root, self._fixed_head_root, self._fixed_head_name = root, head_root, head_name
        self._context = self._configuration_body()
        self.context_sha256 = _digest("context", self._context)
        self.genesis_digest = _digest("genesis", {"context_sha256": self.context_sha256})
        self._paths(require_exists=False)
        self._head_chain = _ProtectiveChain(self)
        self.head = BaselineHead(root=head_root, name=head_name, chain=self._head_chain)
        self._fixed_head = self.head

    def _configuration_body(self):
        _require(type(self.binding) is StoreBinding and type(self.limits) is StoreLimits,
                 "PROTECTIVE_STORE_CONTEXT_INVALID")
        P.policy_digest(self.policy)
        self.binding.__post_init__()
        self.limits.__post_init__()
        return {"schema": 1, "policy": _body(self.policy), "binding": _body(self.binding),
                "limits": _body(self.limits)}

    def _configuration(self):
        current = self._configuration_body()
        _require(self.root == self._fixed_root and current == self._context
                 and _digest("context", current) == self.context_sha256
                 and _digest("genesis", {"context_sha256": self.context_sha256}) == self.genesis_digest,
                 "PROTECTIVE_STORE_CONTEXT_CHANGED")
        if hasattr(self, "_fixed_head"):
            _require(type(self.head) is BaselineHead and self.head is self._fixed_head
                     and self.head._root == self._fixed_head_root
                     and self.head._dir == self._fixed_head_root / self._fixed_head_name
                     and self.head._chain is self._head_chain and type(self._head_chain) is _ProtectiveChain
                     and self._head_chain.store is self, "PROTECTIVE_STORE_CONTEXT_CHANGED")

    def _paths(self, *, require_exists=True):
        self._configuration()
        try:
            home = state_root().absolute()
            _require(self.root != home and self.root.resolve().is_relative_to(home.resolve()),
                     "PROTECTIVE_STORE_ROOT_INVALID")
            _require(not any(part.casefold() == "onedrive" or part.casefold().startswith("onedrive - ")
                             for part in self.root.parts), "PROTECTIVE_STORE_SYNC_ROOT_REFUSED")
            checked_target(self.root, "protective state directory", within=home)
            for path in (self.root, *self.root.parents):
                try:
                    info = os.lstat(path)
                except FileNotFoundError:
                    _require(path == self.root and not require_exists, "PROTECTIVE_STORE_PATH_REFUSED")
                    continue
                _require(stat.S_ISDIR(info.st_mode) and not (getattr(info, "st_file_attributes", 0) & 0x400),
                         "PROTECTIVE_STORE_PATH_REFUSED")
            if not self.root.exists():
                return
            if require_exists:
                with os.scandir(self.root) as entries:
                    names = set()
                    for entry in entries:
                        _require(len(names) < 3 and entry.name in ("session.lock", "journal.jsonl", "payload-objects"),
                                 "PROTECTIVE_STORE_PATH_REFUSED")
                        names.add(entry.name)
                _require(names == {"session.lock", "journal.jsonl", "payload-objects"},
                         "PROTECTIVE_STORE_PATH_REFUSED")
            for name in ("session.lock", "journal.jsonl"):
                path = checked_target(self.root / name, "protective state file", within=self.root)
                if path.exists():
                    self._file_info(os.lstat(path), 1 if name == "session.lock" else self.limits.max_journal_bytes)
        except ProtectiveStoreError:
            raise
        except (OSError, RuntimeError, ValueError, TypeError):
            raise ProtectiveStoreError("PROTECTIVE_STORE_PATH_REFUSED") from None

    @staticmethod
    def _file_info(info, maximum):
        _identity(info)
        _require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and info.st_size <= maximum
                 and not (getattr(info, "st_file_attributes", 0) & 0x400), "PROTECTIVE_STORE_FILE_REFUSED")

    def _sync(self):
        if os.name != "nt":
            descriptor = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_NOFOLLOW", 0))
            try:
                os.fsync(descriptor)
            finally:
                os.close(descriptor)

    def _objects(self):
        return EvidenceObjectStore(root=self.root / "payload-objects", limits=self.limits.object_limits)

    def provision_empty(self):
        """Explicit fresh setup only; preserve partial setup and refuse retries/adoption."""
        self._paths(require_exists=False)
        _require(not self.root.exists(), "PROTECTIVE_STORE_ALREADY_PROVISIONED")
        try:
            self.root.mkdir(mode=0o700)
            for name in ("session.lock", "journal.jsonl"):
                descriptor = os.open(checked_target(self.root / name, "protective setup", within=self.root),
                                     os.O_WRONLY | os.O_CREAT | os.O_EXCL | _FLAGS, 0o600)
                with os.fdopen(descriptor, "wb") as handle:
                    if name == "session.lock":
                        _require(handle.write(b"0") == 1, "PROTECTIVE_STORE_IO_REFUSED")
                    handle.flush()
                    os.fsync(handle.fileno())
            self._objects().initialize()
            self._objects().inventory(budget=self.limits.object_budget)
            self._sync()
        except ProtectiveStoreError:
            raise
        except (OSError, ValueError, RuntimeError, EvidenceObjectError):
            raise ProtectiveStoreError("PROTECTIVE_STORE_PROVISION_FAILED") from None

    @contextmanager
    def _locked(self):
        self._paths()
        target = self.root / "session.lock"
        try:
            root_identity = _identity(os.lstat(self.root))
            before = os.lstat(target)
            descriptor = os.open(checked_target(target, "protective lock", within=self.root), os.O_RDWR | _FLAGS)
            with os.fdopen(descriptor, "r+b") as handle:
                opened = os.fstat(handle.fileno())
                self._file_info(opened, 1)
                _require(_identity(before) == _identity(opened),
                         "PROTECTIVE_STORE_PATH_REFUSED")
                try:
                    if os.name == "nt":
                        import msvcrt
                        handle.seek(0)
                        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                    else:
                        import fcntl
                        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                except OSError:
                    raise ProtectiveStoreError("PROTECTIVE_STORE_LOCKED") from None
                try:
                    anchor = (root_identity, _identity(opened))
                    self._check_lock(anchor)
                    yield anchor
                    self._check_lock(anchor)
                finally:
                    if os.name == "nt":
                        handle.seek(0)
                        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                    else:
                        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        except ProtectiveStoreError:
            raise
        except (OSError, RuntimeError, ValueError, TypeError):
            raise ProtectiveStoreError("PROTECTIVE_STORE_IO_REFUSED") from None

    def _check_lock(self, anchor):
        self._paths()
        try:
            current = os.lstat(self.root / "session.lock")
            self._file_info(current, 1)
            _require((_identity(os.lstat(self.root)), _identity(current)) == anchor,
                     "PROTECTIVE_STORE_LOCK_CHANGED")
        except ProtectiveStoreError:
            raise
        except (OSError, RuntimeError, ValueError, TypeError):
            raise ProtectiveStoreError("PROTECTIVE_STORE_LOCK_CHANGED") from None

    def _read_journal(self):
        self._paths()
        target = self.root / "journal.jsonl"
        try:
            before = os.lstat(target)
            self._file_info(before, self.limits.max_journal_bytes)
            descriptor = os.open(checked_target(target, "protective journal", within=self.root), os.O_RDONLY | _FLAGS)
            with os.fdopen(descriptor, "rb") as handle:
                opened = os.fstat(handle.fileno())
                self._file_info(opened, self.limits.max_journal_bytes)
                _require(_identity(before) == _identity(opened),
                         "PROTECTIVE_STORE_PATH_REFUSED")
                raw = handle.read(self.limits.max_journal_bytes + 1)
                after = os.fstat(handle.fileno())
            current = os.lstat(target)
            self._file_info(after, self.limits.max_journal_bytes)
            self._file_info(current, self.limits.max_journal_bytes)
            _require((*_identity(current), current.st_size, current.st_mtime_ns)
                     == (*_identity(after), after.st_size, after.st_mtime_ns)
                     == (*_identity(opened), opened.st_size, opened.st_mtime_ns)
                     and len(raw) == opened.st_size, "PROTECTIVE_STORE_CHANGED")
            return raw
        except ProtectiveStoreError:
            raise
        except (OSError, RuntimeError, ValueError, TypeError):
            raise ProtectiveStoreError("PROTECTIVE_STORE_IO_REFUSED") from None

    def _empty(self):
        return StoreSnapshot(state=P.initial_state(self.policy), head=self.genesis_digest, journal_sequence=0,
                             outbox=(), receipts=(), ledger_refs=None, restart_required=False)

    def _apply_payload(self, snapshot, body):
        _require(body.get("schema") == 1 and type(body.get("schema")) is int
                 and body.get("context_sha256") == self.context_sha256, "PROTECTIVE_STORE_CONTEXT_MISMATCH")
        if body.get("kind") == "transition":
            _require(set(body) == _TRANSITION_KEYS, "PROTECTIVE_STORE_RECORD_INVALID")
            event = _typed(P.ManagementEvent, body["event"])
            authority = None if body["authority"] is None else _typed(P.AuthorityFacts, body["authority"])
            observations = None if body["observations"] is None else _typed(P.ObservationFacts, body["observations"])
            _pending_consistency(snapshot, observations)
            refs = _typed(LedgerReferences, body["ledger_refs"])
            recorded_state = _typed(P.ManagementState, body["state"])
            _require(type(body["effects"]) is list, "PROTECTIVE_STORE_RECORD_INVALID")
            recorded_effects = tuple(_typed(P.EffectIntent, item) for item in body["effects"])
            state, effects = P.reduce_management(self.policy, snapshot.state, event,
                                                 authority=authority, observations=observations)
            _pending_consistency(snapshot, observations, state, effects)
            _require(state.sequence == snapshot.state.sequence + 1, "PROTECTIVE_STORE_DUPLICATE_TRANSITION")
            _require(state == recorded_state and effects == recorded_effects
                     and _canonical(_body(state)) == _canonical(body["state"])
                     and _canonical([_body(item) for item in effects]) == _canonical(body["effects"]),
                     "PROTECTIVE_STORE_REDUCER_MISMATCH")
            return replace(snapshot, state=state, outbox=_merge_effects(snapshot.outbox, effects), ledger_refs=refs)
        _require(body.get("kind") == "notification" and set(body) == _RECEIPT_KEYS,
                 "PROTECTIVE_STORE_RECORD_INVALID")
        receipt = _typed(NotificationReceipt, body["receipt"])
        receipts = _add_receipt(snapshot, receipt)
        _require(receipts != snapshot.receipts, "PROTECTIVE_STORE_DUPLICATE_RECEIPT")
        return replace(snapshot, receipts=receipts)

    def _replay(self):
        self._configuration()
        raw = self._read_journal()
        _require(not raw or raw.endswith(b"\n"), "PROTECTIVE_STORE_TRUNCATED")
        _require(raw.count(b"\n") <= self.limits.max_records, "PROTECTIVE_STORE_LIMIT_EXCEEDED")
        lines = raw.split(b"\n")[:-1] if raw else ()
        snapshot, last_previous = self._empty(), None
        try:
            for line in lines:
                _require(len(line) + 1 <= _MAX_ROW, "PROTECTIVE_STORE_RECORD_INVALID")
                row = _decode(line, _MAX_ROW)
                _require(set(row) == _ROW_KEYS and type(row["schema"]) is int and row["schema"] == 1
                         and type(row["sequence"]) is int and row["sequence"] == snapshot.journal_sequence + 1
                         and row["previous_sha256"] == snapshot.head
                         and row["context_sha256"] == self.context_sha256 and _hash(row["row_sha256"]),
                         "PROTECTIVE_STORE_CHAIN_INVALID")
                payload_ref = _typed(PayloadReference, row["payload_ref"])
                _require(_digest("row", {key: value for key, value in row.items() if key != "row_sha256"})
                         == row["row_sha256"], "PROTECTIVE_STORE_CHAIN_INVALID")
                payload = self._objects().read(payload_ref)
                body = _decode(payload, self.limits.object_limits.max_payload_bytes)
                snapshot = self._apply_payload(snapshot, body)
                last_previous = row["previous_sha256"]
                snapshot = replace(snapshot, head=row["row_sha256"], journal_sequence=row["sequence"],
                                   restart_required=True)
            return snapshot, len(raw), last_previous
        except ProtectiveStoreError:
            raise
        except (EvidenceObjectError, P.ProtectiveStateError, TypeError, ValueError, KeyError, OverflowError):
            raise ProtectiveStoreError("PROTECTIVE_STORE_REPLAY_REFUSED") from None

    def _load(self):
        try:
            before = self.head.read()
            snapshot, size, _ = self._replay()
            _require(snapshot.head == before == self.head.read(), "PROTECTIVE_STORE_HEAD_MISMATCH")
            return snapshot, size
        except ProtectiveStoreError:
            raise
        except BaselineHeadError:
            raise ProtectiveStoreError("PROTECTIVE_STORE_HEAD_REFUSED") from None

    def inspect(self):
        """Read-only full graph/head inspection; never a writable/resumed lifecycle."""
        with self._locked() as anchor:
            snapshot = self._load()[0]
            self._check_lock(anchor)
            return snapshot

    @contextmanager
    def session(self):
        """Exclusive writer; every existing history requires a persisted restart first."""
        with self._locked() as anchor:
            snapshot, size = self._load()
            writer = _Writer(self, snapshot, size, anchor)
            try:
                yield writer
            finally:
                writer._active = False


class _Writer:
    def __init__(self, store, snapshot, size, anchor):
        self._store, self._snapshot, self._size = store, snapshot, size
        self._anchor = anchor
        self._active, self._failed, self._thread = True, False, get_ident()

    def _ready(self):
        _require(self._active and self._thread == get_ident(), "PROTECTIVE_STORE_SESSION_REQUIRED")
        _require(not self._failed, "PROTECTIVE_STORE_SESSION_FAILED")
        self._store._check_lock(self._anchor)

    def snapshot(self):
        self._ready()
        return self._snapshot

    def _append(self, payload, proposed):
        self._ready()
        store, previous = self._store, self._snapshot
        # Detect mutation of any retained source, not only a cached tail/size.
        current, size = store._load()
        _require(replace(current, restart_required=previous.restart_required) == previous and size == self._size,
                 "PROTECTIVE_STORE_CHANGED")
        raw = _canonical(payload)
        objects = store._objects()
        try:
            preview = objects.preview(raw)
            row = {"schema": 1, "sequence": previous.journal_sequence + 1, "previous_sha256": previous.head,
                   "context_sha256": store.context_sha256, "payload_ref": _body(preview.reference)}
            row["row_sha256"] = _digest("row", row)
            line = _canonical(row) + b"\n"
            _require(row["sequence"] <= store.limits.max_records and len(line) <= _MAX_ROW
                     and size + len(line) <= store.limits.max_journal_bytes, "PROTECTIVE_STORE_LIMIT_EXCEEDED")
            reference = objects.stage(raw, budget=store.limits.object_budget)
            _require(reference == preview.reference, "PROTECTIVE_STORE_REFERENCE_CHANGED")
        except EvidenceObjectError as exc:
            code = "PROTECTIVE_STORE_LIMIT_EXCEEDED" if "LIMIT" in str(exc) else "PROTECTIVE_STORE_OBJECT_REFUSED"
            raise ProtectiveStoreError(code) from None
        # From here an interruption may leave a journal ahead of the head. The
        # current writer is poisoned before the first append and cannot retry it.
        self._failed = True
        try:
            store._check_lock(self._anchor)
            target = checked_target(store.root / "journal.jsonl", "protective journal", within=store.root)
            before = os.lstat(target)
            descriptor = os.open(target, os.O_WRONLY | os.O_APPEND | _FLAGS)
            with os.fdopen(descriptor, "ab") as handle:
                opened = os.fstat(handle.fileno())
                store._file_info(opened, store.limits.max_journal_bytes)
                _require((*_identity(before), before.st_size)
                         == (*_identity(opened), self._size), "PROTECTIVE_STORE_CHANGED")
                _require(handle.write(line) == len(line), "PROTECTIVE_STORE_IO_REFUSED")
                handle.flush()
                os.fsync(handle.fileno())
                written = os.fstat(handle.fileno())
            current_file = os.lstat(target)
            store._file_info(written, store.limits.max_journal_bytes)
            store._file_info(current_file, store.limits.max_journal_bytes)
            _require(_identity(current_file) == _identity(written) == _identity(opened)
                     and current_file.st_size == written.st_size == self._size + len(line),
                     "PROTECTIVE_STORE_CHANGED")
            store._check_lock(self._anchor)
            _require(store.head.compare_and_set(previous.head, row["row_sha256"]) is True,
                     "PROTECTIVE_STORE_HEAD_UPDATE_REFUSED")
            store._check_lock(self._anchor)
            _require(store.head.read() == row["row_sha256"], "PROTECTIVE_STORE_HEAD_MISMATCH")
            confirmed, confirmed_size = store._load()
            expected = replace(proposed, head=row["row_sha256"], journal_sequence=row["sequence"], restart_required=True)
            _require(confirmed == expected and confirmed_size == self._size + len(line),
                     "PROTECTIVE_STORE_CHANGED")
            store._check_lock(self._anchor)
        except ProtectiveStoreError:
            raise
        except (OSError, RuntimeError, ValueError, TypeError):
            raise ProtectiveStoreError("PROTECTIVE_STORE_COMMIT_INTERRUPTED") from None
        self._snapshot = replace(proposed, head=row["row_sha256"], journal_sequence=row["sequence"])
        self._size += len(line)
        self._failed = False
        return self._snapshot

    def commit(self, event, *, authority, observations, ledger_refs):
        self._ready()
        _require(type(ledger_refs) is LedgerReferences, "PROTECTIVE_STORE_LEDGER_REFS_INVALID")
        ledger_refs.__post_init__()
        _require(type(event) is P.ManagementEvent, "PROTECTIVE_STORE_EVENT_REQUIRED")
        _require(not self._snapshot.restart_required or event.kind == "restart", "PROTECTIVE_STORE_RESTART_REQUIRED")
        _require(observations is None or type(observations) is P.ObservationFacts,
                 "PROTECTIVE_STORE_OBSERVATIONS_INVALID")
        state, effects = P.reduce_management(self._store.policy, self._snapshot.state, event,
                                             authority=authority, observations=observations)
        if state.sequence == self._snapshot.state.sequence:
            _require(ledger_refs == self._snapshot.ledger_refs, "PROTECTIVE_STORE_DUPLICATE_CONTEXT_CHANGED")
            # Idempotence does not bypass integrity checking of the retained graph.
            current, size = self._store._load()
            _require(replace(current, restart_required=self._snapshot.restart_required) == self._snapshot
                     and size == self._size, "PROTECTIVE_STORE_CHANGED")
            return self._snapshot
        _pending_consistency(self._snapshot, observations, state, effects)
        payload = {"schema": 1, "kind": "transition", "context_sha256": self._store.context_sha256,
                   "event": _body(event), "authority": None if authority is None else _body(authority),
                   "observations": None if observations is None else _body(observations),
                   "ledger_refs": _body(ledger_refs), "state": _body(state), "effects": [_body(item) for item in effects]}
        proposed = replace(self._snapshot, state=state, outbox=_merge_effects(self._snapshot.outbox, effects),
                           ledger_refs=ledger_refs, restart_required=False)
        return self._append(payload, proposed)

    def record_notification(self, receipt):
        self._ready()
        _require(not self._snapshot.restart_required, "PROTECTIVE_STORE_RESTART_REQUIRED")
        receipts = _add_receipt(self._snapshot, receipt)
        if receipts == self._snapshot.receipts:
            current, size = self._store._load()
            _require(replace(current, restart_required=False) == self._snapshot and size == self._size,
                     "PROTECTIVE_STORE_CHANGED")
            return self._snapshot
        payload = {"schema": 1, "kind": "notification", "context_sha256": self._store.context_sha256,
                   "receipt": _body(receipt)}
        return self._append(payload, replace(self._snapshot, receipts=receipts))
