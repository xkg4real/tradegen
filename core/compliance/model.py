"""Shared types of the compliance gate (spec 6.1; plan decisions P2, P5): intents, approved state, owner state,
contexts, decisions, permits and screenings, plus the hashing helpers they rest on. Pure and standard library only,
so gate.py, owner.py and rules.py can all import it without a cycle."""
from __future__ import annotations

import dataclasses
import hashlib
import json
import math
import weakref
import zoneinfo
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.compliance.rules import InstrumentMap, RulesTable, VenueFacts

ALLOW, ALLOW_EXIT, ACK_REQUIRED, BLOCK = "ALLOW", "ALLOW_EXIT", "ACK_REQUIRED", "BLOCK"
KST = zoneinfo.ZoneInfo("Asia/Seoul")            # built at import; decide() never builds a zone


def jsonable(obj):
    """Plain JSON data for hashing: a dataclass becomes a dict of its fields, a Mapping a dict (tuple keys joined
    by "|"), a set a sorted list, a tuple a list, a date its ISO text. A non-finite float is ValueError; any other
    type is TypeError."""
    if obj is None or isinstance(obj, (str, bool, int)):
        return obj
    if isinstance(obj, float):
        if not math.isfinite(obj):
            raise ValueError(f"not a finite number: {obj!r}")
        return obj
    if isinstance(obj, date):
        return obj.isoformat()
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return {f.name: jsonable(getattr(obj, f.name)) for f in dataclasses.fields(obj)}
    if isinstance(obj, Mapping):
        out = {}
        for key, value in obj.items():
            text = "|".join(str(part) for part in key) if isinstance(key, tuple) else str(key)
            if text in out:
                raise ValueError(f"two keys read as {text!r}")
            out[text] = jsonable(value)
        return out
    if isinstance(obj, (set, frozenset)):
        return sorted((jsonable(x) for x in obj), key=_sort_key)
    if isinstance(obj, (list, tuple)):
        return [jsonable(x) for x in obj]
    raise TypeError(f"not JSON data: {type(obj).__name__}")


def _sort_key(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def canonical_json(obj) -> str:
    """The same text as core.ficc.macro_schema.canonical_json, after jsonable(); NaN and inf refused."""
    return json.dumps(jsonable(obj), sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def sha256_hex(data: bytes | str) -> str:
    return hashlib.sha256(data.encode("utf-8") if isinstance(data, str) else data).hexdigest()


def iso_utc(moment: datetime) -> str:
    """An aware instant as "YYYY-MM-DDTHH:MM:SSZ"; a naive one (or a bare date) is ValueError."""
    if not isinstance(moment, datetime) or moment.utcoffset() is None:
        raise ValueError(f"compliance: instants must be tz-aware, got {moment!r}")
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass(frozen=True, kw_only=True)
class Intent:
    """One order, transfer or plan leg as the caller sees it (spec 6.1); the class is derived, never supplied."""
    venue: str
    symbol: str
    counter_symbol: str = ""                      # P18: "" for transfer_out, lend and borrow
    asset: str
    multiple: float
    action: str
    financing: str = "cash"
    quantity: float
    notional_krw: float
    destination_venue: str | None = None
    destination_address: str | None = None
    destination_network: str | None = None
    destination_tag: str | None = None
    route: str = "direct"
    on_behalf: str = "self"
    publishes_signal: bool = False
    tags: frozenset = frozenset()
    reservation_id: str | None = None


@dataclass(frozen=True, kw_only=True)
class Exposure:
    held_krw: float                                                         # everything held there, settlement included
    reservations: Mapping[str, float] = field(default_factory=dict)        # reservation_id -> notional_krw
    promised_sell_units: Mapping[str, float] = field(default_factory=dict) # symbol -> units promised to sell permits


@dataclass(frozen=True, kw_only=True)
class Positions:
    """Caller-supplied until the execution spec adds live reads (P19)."""
    equity_krw: float
    holdings: Mapping[tuple[str, str], float] = field(default_factory=dict)     # (venue, symbol) -> units
    shorts: Mapping[tuple[str, str], float] = field(default_factory=dict)
    exposure: Mapping[str, Exposure] = field(default_factory=dict)              # venue -> Exposure


@dataclass(frozen=True, kw_only=True)
class ApprovedState:
    """The rules table, instrument map and venue facts in force, or `invalid(reason)`."""
    valid: bool
    reason: str = ""
    rules: RulesTable | None = None
    instruments: InstrumentMap | None = None
    venues: VenueFacts | None = None
    hashes: Mapping[str, str] = field(default_factory=dict)   # "rules" | "instruments" | "venues" -> sha256
    seq: int = 0                                              # largest owner-log seq among the approvals in force
    history_maps: tuple = ()                                  # earlier approved InstrumentMaps, newest first

    @classmethod
    def invalid(cls, reason: str) -> ApprovedState:
        return cls(valid=False, reason=reason)

    @property
    def state_hash(self) -> str:
        return sha256_hex(canonical_json({"hashes": self.hashes, "seq": self.seq})) if self.valid else ""


@dataclass(frozen=True, kw_only=True)
class OwnerState:
    """What the verified owner log says (spec 6.4), or BROKEN: then every owner fact counts as absent."""
    status: str                                       # "OK" | "BROKEN"
    reason: str = ""
    head: tuple[int, str] = (0, "")                   # (seq, row_sha256) of the last line
    caps: Mapping[str, float] = field(default_factory=dict)
    limits: Mapping[str, float] = field(default_factory=dict)
    addresses: frozenset = frozenset()                # {(venue, symbol, network, address, tag or "")}
    flags: frozenset = frozenset()                    # met `requires.owner` items
    halted_floors: frozenset = frozenset()
    armed_sessions: frozenset = frozenset()
    session_acks: frozenset = frozenset()             # {(session_id, row_id, warning_sha256)}
    transfer_acks: frozenset = frozenset()            # {(intent_hash, warning_sha256)}
    fingerprint: str = ""

    @classmethod
    def broken(cls, reason: str, *, head=(0, ""), fingerprint="") -> OwnerState:
        return cls(status="BROKEN", reason=reason, head=head, fingerprint=fingerprint)

    @property
    def ok(self) -> bool:
        return self.status == "OK"


@dataclass(frozen=True, kw_only=True)
class SessionState:
    session_id: str | None = None
    armed: bool = False


@dataclass(frozen=True, kw_only=True)
class Context:
    """Everything decide() may read. Only seal_context makes one that decide() accepts (P5)."""
    date: date                                        # Asia/Seoul date of the decision moment
    active: ApprovedState
    snapshot: ApprovedState | None
    owner: OwnerState
    code_hash: str
    code_signed: bool
    session: SessionState
    equity_krw: float
    holdings: Mapping[tuple[str, str], float]
    shorts: Mapping[tuple[str, str], float]
    exposure: Mapping[str, Exposure]
    live_evidence: frozenset = frozenset()            # E1: live D16 requirements in force (owner.evidence_in_force)
    ctx_hash: str = ""                                # set by seal_context


@dataclass(frozen=True, kw_only=True)
class Decision:
    """One verdict with its provenance (spec 6.1). decision_id is always derived from every other field."""
    verdict: str
    kind: str                                         # close_long | cover_short | withdraw | new_exposure | malformed
    reasons: tuple[str, ...]
    warnings: tuple[str, ...] = ()
    intent_hash: str
    state_hash: str
    code_hash: str
    owner_head: tuple[int, str]
    ctx_hash: str
    date: date | None
    decision_id: str = ""
    ack: tuple[str, str] | None = None                # (row_id, warning_sha256) when the verdict is ACK_REQUIRED

    def __post_init__(self) -> None:
        body = {f.name: getattr(self, f.name) for f in dataclasses.fields(self) if f.name != "decision_id"}
        object.__setattr__(self, "decision_id", sha256_hex(canonical_json(body)))


@dataclass(frozen=True, kw_only=True)
class Permit:
    decision_id: str
    intent_hash: str
    state_hash: str
    state_seq: int
    session_id: str | None
    reservation_id: str | None
    date: date


@dataclass(frozen=True, kw_only=True)
class Screening:
    decision: Decision
    allowed: bool                                     # verdict in (ALLOW, ACK_REQUIRED)
    flags: tuple[tuple[date, str, str], ...]          # (date, "review_by" | "auto_off" | "effective_until", row_id)
    exit_date: date | None
    screening_hash: str


def intent_hash(intent: Intent) -> str:
    return sha256_hex(canonical_json(intent))


_SEALED: weakref.WeakValueDictionary = weakref.WeakValueDictionary()     # id(ctx) -> ctx


def seal_context(**fields) -> Context:
    """Build a Context, hash every field into ctx_hash and register the instance (P5). Discipline, not
    security: owner.load_context and the test fixtures are its only callers."""
    fields.pop("ctx_hash", None)
    draft = Context(**fields)                         # defaults filled in; an unknown field is still a TypeError
    body = {f.name: getattr(draft, f.name) for f in dataclasses.fields(Context) if f.name != "ctx_hash"}
    ctx = Context(**body, ctx_hash=sha256_hex(canonical_json(body)))
    _SEALED[id(ctx)] = ctx
    return ctx


def is_sealed(ctx) -> bool:
    return ctx is not None and _SEALED.get(id(ctx)) is ctx      # None would match a missing entry
