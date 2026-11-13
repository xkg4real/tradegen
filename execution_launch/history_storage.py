"""Pure history-v3 policy and contextual slot codec; no implicit storage root.

This module does not choose a strategy, stage evidence, append a journal, issue
an authority, initialize a head or turn a storage failure into unavailable data.
The history owner supplies the policy and authenticates its digest in the
protocol. Deeper receipt/account/chooser semantics remain LiveHistory's job.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
import re

from execution_control.store import MAX_ROW_BYTES
from execution_launch.evidence_objects import EvidenceObjectError, ObjectLimits, StoreBudget

POLICY_SCHEMA = 1
HISTORY_VERSION = 3
OBJECT_SCHEMA = 1
MAX_POLICY_BYTES = 16384
MAX_SLOT_INDEX = 19999
MAX_CODEC_DEPTH = 16
MAX_CODEC_ITEMS = 262144
MAX_WINDOW_BYTES = 1024 ** 4
MAX_WINDOW_OBJECTS = 1000000
MAX_JOURNAL_BYTES = 8 * 1024 ** 3
_DOMAIN = b"TRADEGEN-HISTORY-STORAGE-v3\x00"
_HASH = re.compile(r"[0-9a-f]{64}")
_POLICY_KEYS = frozenset({"schema_version", "history_version", "object_schema", "object_limits",
                          "max_window_bytes", "max_window_objects", "max_journal_bytes"})
_LIMIT_KEYS = frozenset({"chunk_bytes", "max_payload_bytes", "max_chunks", "max_manifest_bytes"})
_WRAPPER_KEYS = frozenset({"schema", "window_digest", "driver_identity_digest", "index", "sampled_at", "slot"})
_SLOT_KEYS = frozenset({"index", "trade_symbol", "tick_size", "receipt", "anchor", "holdings", "universe", "decision"})


class HistoryStorageError(ValueError):
    """Fixed diagnostics; never disclose paths, slot contents or account values."""


def _require(ok, code):
    if not ok:
        raise HistoryStorageError(code)


def _integer(value, maximum, *, zero=False):
    return type(value) is int and (0 if zero else 1) <= value <= maximum


def _hash(value):
    return type(value) is str and _HASH.fullmatch(value) is not None


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                      allow_nan=False).encode("ascii")


def _pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError("duplicate key")
        result[key] = value
    return result


def _invalid_number(value):
    raise ValueError("non-integer JSON number")


def _primitive(value, *, depth=0, count=None):
    count = [0] if count is None else count
    count[0] += 1
    _require(depth <= MAX_CODEC_DEPTH and count[0] <= MAX_CODEC_ITEMS, "HISTORY_STORAGE_LIMIT_EXCEEDED")
    if value is None or type(value) in (str, bool, int):
        return
    if type(value) is list:
        for item in value:
            _primitive(item, depth=depth + 1, count=count)
        return
    if type(value) is dict and all(type(key) is str for key in value):
        for item in value.values():
            _primitive(item, depth=depth + 1, count=count)
        return
    raise HistoryStorageError("HISTORY_STORAGE_PAYLOAD_INVALID")


def _structural_bounds(raw):
    # Bound nesting/container delimiters before json.loads allocates a graph.
    # Quoted receipt bytes are ordinary string contents, not structural tokens.
    depth, items, quoted, escaped = 0, 0, False, False
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
            items += 1
        elif char in (93, 125):
            depth -= 1
        elif char in (44, 58):
            items += 1
        _require(depth <= MAX_CODEC_DEPTH + 1 and items <= MAX_CODEC_ITEMS * 3,
                 "HISTORY_STORAGE_LIMIT_EXCEEDED")


def _decode(raw, maximum, code):
    _require(type(raw) is bytes and 0 < len(raw) <= maximum, code)
    _structural_bounds(raw)
    try:
        result = json.loads(raw.decode("ascii"), object_pairs_hook=_pairs, parse_float=_invalid_number,
                            parse_constant=_invalid_number)
        _require(type(result) is dict and _canonical(result) == raw, code)
        return result
    except HistoryStorageError:
        raise
    except (ValueError, TypeError, UnicodeError, OverflowError, RecursionError):
        raise HistoryStorageError(code) from None


@dataclass(frozen=True, kw_only=True)
class HistoryStoragePolicy:
    """Explicit finite window policy. Object quotas include transient data files.

    max_window_bytes and max_window_objects cover object files, orphan final
    objects, a pending copy and the fixed <=1-byte objects.lock infrastructure
    (one file). Journal bytes have their own cap. Filesystem allocation/metadata
    and free-space guarantees are not inferred from logical byte budgets.
    """
    schema_version: int
    history_version: int
    object_limits: ObjectLimits
    max_window_bytes: int
    max_window_objects: int
    max_journal_bytes: int

    def __post_init__(self):
        _require(type(self.schema_version) is int and self.schema_version == POLICY_SCHEMA
                 and type(self.history_version) is int and self.history_version == HISTORY_VERSION
                 and type(self.object_limits) is ObjectLimits
                 and _integer(self.max_window_bytes, MAX_WINDOW_BYTES)
                 and _integer(self.max_window_objects, MAX_WINDOW_OBJECTS)
                 and _integer(self.max_journal_bytes, MAX_JOURNAL_BYTES), "HISTORY_STORAGE_POLICY_INVALID")
        try:
            self.object_limits.__post_init__()
        except EvidenceObjectError:
            raise HistoryStorageError("HISTORY_STORAGE_POLICY_INVALID") from None

    @property
    def store_budget(self):
        return policy_budget(self)


def _policy(policy):
    _require(type(policy) is HistoryStoragePolicy, "HISTORY_STORAGE_POLICY_INVALID")
    policy.__post_init__()
    return policy


def policy_bytes(policy: HistoryStoragePolicy) -> bytes:
    """Canonical explicit policy, including the only supported object revision."""
    _policy(policy)
    result = _canonical({**asdict(policy), "object_schema": OBJECT_SCHEMA})
    _require(len(result) <= MAX_POLICY_BYTES, "HISTORY_STORAGE_POLICY_INVALID")
    return result


def policy_digest(policy: HistoryStoragePolicy) -> str:
    return hashlib.sha256(_DOMAIN + b"policy\x00" + policy_bytes(policy)).hexdigest()


def policy_budget(policy: HistoryStoragePolicy) -> StoreBudget:
    _policy(policy)
    return StoreBudget(max_bytes=policy.max_window_bytes, max_objects=policy.max_window_objects)


def parse_policy(raw: bytes) -> HistoryStoragePolicy:
    body = _decode(raw, MAX_POLICY_BYTES, "HISTORY_STORAGE_POLICY_INVALID")
    _require(set(body) == _POLICY_KEYS and type(body["object_schema"]) is int
             and body["object_schema"] == OBJECT_SCHEMA and type(body["object_limits"]) is dict
             and set(body["object_limits"]) == _LIMIT_KEYS, "HISTORY_STORAGE_POLICY_INVALID")
    try:
        limits = ObjectLimits(**body["object_limits"])
    except (EvidenceObjectError, TypeError):
        raise HistoryStorageError("HISTORY_STORAGE_POLICY_INVALID") from None
    return HistoryStoragePolicy(schema_version=body["schema_version"], history_version=body["history_version"],
                                object_limits=limits, max_window_bytes=body["max_window_bytes"],
                                max_window_objects=body["max_window_objects"], max_journal_bytes=body["max_journal_bytes"])


def _stamp(value):
    try:
        _require(type(value) is datetime and value.utcoffset() is not None, "HISTORY_STORAGE_CONTEXT_MISMATCH")
        return value.astimezone(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")
    except HistoryStorageError:
        raise
    except (ValueError, OverflowError, TypeError):
        raise HistoryStorageError("HISTORY_STORAGE_CONTEXT_MISMATCH") from None


@dataclass(frozen=True, kw_only=True)
class SlotContext:
    window_digest: str
    driver_identity_digest: str
    index: int
    sampled_at: datetime

    def __post_init__(self):
        _require(_hash(self.window_digest) and _hash(self.driver_identity_digest)
                 and _integer(self.index, MAX_SLOT_INDEX, zero=True), "HISTORY_STORAGE_CONTEXT_MISMATCH")
        _stamp(self.sampled_at)


def _context(context):
    _require(type(context) is SlotContext, "HISTORY_STORAGE_CONTEXT_MISMATCH")
    context.__post_init__()
    return {"window_digest": context.window_digest, "driver_identity_digest": context.driver_identity_digest,
            "index": context.index, "sampled_at": _stamp(context.sampled_at)}


def _slot(slot, context):
    _require(type(slot) is dict and set(slot) == _SLOT_KEYS, "HISTORY_STORAGE_PAYLOAD_INVALID")
    _require(type(slot["index"]) is int and slot["index"] == context.index, "HISTORY_STORAGE_CONTEXT_MISMATCH")
    _primitive(slot)
    return slot


def encode_slot_payload(slot: dict, *, context: SlotContext, policy: HistoryStoragePolicy) -> bytes:
    _policy(policy)
    bound = _context(context)
    _slot(slot, context)
    try:
        body = {"schema": 1, **bound, "slot": slot}
        _primitive(body)
        result = _canonical(body)
    except HistoryStorageError:
        raise
    except (ValueError, TypeError, RecursionError, UnicodeError, OverflowError):
        raise HistoryStorageError("HISTORY_STORAGE_PAYLOAD_INVALID") from None
    _require(len(result) <= policy.object_limits.max_payload_bytes, "HISTORY_STORAGE_LIMIT_EXCEEDED")
    # The caller owns a mutable dict. Validate the captured immutable bytes too:
    # a change between prevalidation and serialization must not yield a payload
    # that this same codec would reject during durable replay.
    decode_slot_payload(result, context=context, policy=policy)
    return result


def decode_slot_payload(raw: bytes, *, context: SlotContext, policy: HistoryStoragePolicy) -> dict:
    _policy(policy)
    bound = _context(context)
    _require(type(raw) is bytes and 0 < len(raw) <= policy.object_limits.max_payload_bytes,
             "HISTORY_STORAGE_LIMIT_EXCEEDED")
    body = _decode(raw, policy.object_limits.max_payload_bytes, "HISTORY_STORAGE_PAYLOAD_INVALID")
    _require(set(body) == _WRAPPER_KEYS and type(body["schema"]) is int and body["schema"] == 1,
             "HISTORY_STORAGE_PAYLOAD_INVALID")
    _require(type(body["index"]) is int and all(body[name] == value for name, value in bound.items()),
             "HISTORY_STORAGE_CONTEXT_MISMATCH")
    _primitive(body)
    return _slot(body["slot"], context)


def admit_journal_row(policy: HistoryStoragePolicy, *, journal_bytes: int, next_row_bytes: int) -> int:
    """Pure admission, including the caller-supplied complete row's newline."""
    _policy(policy)
    _require(_integer(journal_bytes, MAX_JOURNAL_BYTES, zero=True)
             and _integer(next_row_bytes, MAX_ROW_BYTES), "HISTORY_STORAGE_LIMIT_EXCEEDED")
    after = journal_bytes + next_row_bytes
    _require(after <= policy.max_journal_bytes, "HISTORY_STORAGE_LIMIT_EXCEEDED")
    return after
