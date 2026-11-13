"""Durable live-history and anchor adapter for the fixed driver: an append-only, hash-chained journal of original
Upbit book receipts and per-slot account anchors behind an independent BaselineHead.

``LiveHistory`` writes ``<state_root>/execution-history/<deployment window digest>/history.jsonl`` (and the lock
file ``history.lock``). Row 1 binds the fixed driver identity; every later row holds one slot's original orderbook
receipt bytes and the account anchor taken from the supplied AccountObservation, stamped with the trusted clock at
recording. The bar and the decision are never stored: they are derived from the receipt, the slot grid, the
recording time and the program, at recording and again at every restart replay, so no rewritable copy exists. The
journal head is retained by the injected ``BaselineHead`` whose chain check is ``HistoryChain`` (GENESIS over an
empty journal at the reviewed initialization, the fsynced tail row at every advance); that initialization is the
explicit operator step and has no caller here. ``provider`` and ``verifier`` are the exact callables that
``make_fixed_driver`` and ``ReviewVerifiers`` must receive; the verifier authenticates a frame only against the
durable record and re-checks the head and the file size before returning a receipt.

Rules: one slot per ``record_slot`` call, always the next index, recorded inside ``[slot, slot + 10 s]``; a missed
slot is never backfilled and blocks the deployment until a new reviewed window; a history cannot be created once
its window has started; the account is at most 30 s old and never newer than sampling; the receipt's
``verified_at`` is the recording time, never after the tick. A crash between the append and the head advance leaves
the file one row ahead of the head and refuses at the next bind; nothing repairs, reseeds or adopts a local digest.
``execution_control.store.Journal`` is not reused: its event kinds are the control lifecycle, its payload strings
are capped at 4096 bytes (a receipt body is up to 131072) and it keeps its own checkpoint anchor beside the journal,
which the trusted head replaces here; its row codec, lock and sync helpers are reused as they are. Not defended: a
process that rewrites the journal and the head coherently (the ceiling stated in baseline_head). Nothing here
fetches, signs, arms, orders or reads credentials.

A universe window (``protocol.universe_rule_sha256`` set) records history row v2 instead (spec section 12): the
trade coin the coordinator chose and its tick, that coin's book receipt or ``"unavailable"``, the anchor of that
coin, every holding, the slot's universe record (snapshot in force, flag exceptions and defined ticker prices with
the raw-body sha256s, allow-list, buy-block reasons, events) and the chooser's decision. The section 14 chooser runs
here at recording and again at replay, over the last L+1 price vectors, h and the hold count, and replay requires
the stored decision to equal the derived one. New universe windows require an explicit protocol-bound storage
policy and history data v3: a small journal reference names the complete lossless contextual payload. Existing v2
bytes remain readable for auditing; their old approvals do not authorize new source. Valid flags, tickers, quotes
and holdings are never discarded for size. Quota or storage failures refuse before a new slot is committed.
"""
from __future__ import annotations

import base64
from contextlib import contextmanager
from dataclasses import asdict, dataclass, fields
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from fractions import Fraction
import hashlib
import json
import os
from pathlib import Path
import stat
import threading
from typing import Callable

from core.compliance.model import Universe
from core.compliance.rules import UNIVERSE_MARKET, universe_top_n
from core.isolation import checked_target, state_root
from execution_accounts.collector import SourceReceipt
from execution_accounts.model import Position
from execution_accounts.universe import FlagRead, TickerRead
from execution_control.capability import digest
from execution_control.controller import AccountObservation
from execution_control.store import (GENESIS, MAX_ROW_BYTES, SCHEMA, _HASH, _ROW_KEYS, _canonical, _decode, _lock,
                                     _sync_directory, _utc, _valid_stamp)
from execution_launch.baseline_head import BaselineHead, BaselineHeadError
from execution_launch.driver import (AccountAnchor, ChooserInputs, DeploymentWindow, FixedDriverIdentity,
                                     HistoryFrame, HistoryReceipt, UniverseBar, chooser_decision,
                                     describe_fixed_driver, fixed_history_dependencies, history_frame_digest)
from execution_launch.evidence_objects import EvidenceObjectError, EvidenceObjectStore, decode_reference
from execution_launch.history_storage import (HistoryStorageError, HistoryStoragePolicy, SlotContext,
    admit_journal_row, decode_slot_payload, encode_slot_payload, parse_policy, policy_bytes, policy_digest)
from execution_launch.paper_capture import sample_prefetched_book
from execution_launch.managed_behavior import FixedDecisionV2, derive_fixed_decision_v2, resolve_behavior
from execution_launch.profile import LaunchProfile, profile_contract_digest
from execution_launch.program import ChooserState, ProgramSpec, program_digest, target_fraction
from execution_launch.runner import DecisionInput, StrategyDriver
from execution_launch.strategy import ForwardProtocol, PaperBar, PaperDecision, _decimal, _plain, evidence_digest

STORE_DIRECTORY = "execution-history"
EXECUTION_WINDOW = timedelta(seconds=10)     # the driver's slot window and the quote freshness bound
ACCOUNT_MAX_AGE = timedelta(seconds=30)      # the driver's account-anchor age bound
SIZE_FALLBACK = "HISTORY_ROW_SIZE_FALLBACK"  # historical v2 reason only; never produced by the v3 writer
PRICE_WINDOW_MS = 60_000                     # a price is defined only for a trade within 60 s of the slot (section 14)
MAX_PRICE_TEXT = 16                          # section 14 price encoding: a decimal string of at most 16 characters
_LOCK = threading.Lock()                     # own lock: the head takes its own, the chain reads without one
_NAMES = ("history.jsonl", "history.lock")
_RECEIPT_KEYS = frozenset({"path", "params", "account_scope", "received_at", "server_time", "raw_body_b64", "sha256"})
_ANCHOR_KEYS = frozenset({"cash_quote", "units", "account_asof"})
_IDENTITY_KEYS = frozenset(f.name for f in fields(FixedDriverIdentity))
_EXCEPTION_CLASSES = ("caution", "unknown", "warning")   # the flag classes a row lists; "unflagged" is implied
_START = ChooserState(held=None, hold_count=0)           # a window's chooser starts in cash (PR 4b)
_SLOT_V2_KEYS = frozenset({"index", "trade_symbol", "tick_size", "receipt", "anchor", "holdings", "universe",
                           "decision"})
_RECORD_KEYS = frozenset({"snapshot", "flags", "tickers", "allow", "reasons", "events"})
_BOUND_V3_KEYS = frozenset({"identity", "history_version", "history_storage"})
_SLOT_V3_KEYS = frozenset({"history_version", "index", "payload_ref"})
OBJECT_DIRECTORY = "payload-objects"


class LiveHistoryError(ValueError):
    """Fixed UPPER_SNAKE codes only; never paths, receipt bytes, amounts or upstream text."""


def _require(ok, code):
    if not ok:
        raise LiveHistoryError(code)


def _aware(value):
    try:
        return type(value) is datetime and value.utcoffset() is not None and value.astimezone(timezone.utc) is not None
    except (ValueError, OverflowError):
        return False


def _clock_value(clock):
    try:
        value = clock()
        if not _aware(value):
            raise ValueError
    except Exception:
        raise LiveHistoryError("HISTORY_CLOCK_FAILED") from None
    return value


def _window_digest(window):
    _require(type(window) is DeploymentWindow, "HISTORY_INPUT_REQUIRED")
    try:
        return digest(window)
    except ValueError:
        raise LiveHistoryError("HISTORY_INPUT_REQUIRED") from None


def _checked(root, window_digest):
    """The store directory of one window after every path rule; the root must be the explicit absolute state root."""
    _require(isinstance(root, Path), "HISTORY_INPUT_REQUIRED")
    try:
        _require(root.is_absolute() and root == state_root().absolute(), "HISTORY_STORE_ROOT_MISMATCH")
        store = root / STORE_DIRECTORY
        directory = store / window_digest
        checked_target(root, "history state root")
        checked_target(store, "history store", within=root)
        checked_target(directory, "history directory", within=root)
        for name in _NAMES:
            target = checked_target(directory / name, "history file", within=directory)
            if target.exists():
                info = os.lstat(target)
                _require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1, "HISTORY_STORE_PATH_REFUSED")
        return directory
    except LiveHistoryError:
        raise
    except (OSError, ValueError, RuntimeError):
        raise LiveHistoryError("HISTORY_STORE_PATH_REFUSED") from None


def _row_digest(row):
    return hashlib.sha256(_canonical({key: value for key, value in row.items() if key != "row_sha256"})).hexdigest()


def _row(seq, previous, kind, data, at):
    body = {"schema": SCHEMA, "seq": seq, "prev_sha256": previous, "kind": kind, "utc": _utc(at), "data": data}
    return {**body, "row_sha256": hashlib.sha256(_canonical(body)).hexdigest()}


def _receipt_body(receipt):
    return {"path": receipt.path, "params": [[key, value] for key, value in receipt.params],
            "account_scope": receipt.account_scope, "received_at": _utc(receipt.received_at),
            "server_time": _utc(receipt.server_time),
            "raw_body_b64": base64.b64encode(receipt.raw_body).decode("ascii"), "sha256": receipt.sha256}


def _anchor_body(anchor):
    return {"cash_quote": _plain(anchor.cash_quote), "units": _plain(anchor.units),
            "account_asof": _utc(anchor.account_asof)}


def _parse_receipt(value):
    """The stored receipt back as a SourceReceipt; its canonical body must reproduce the stored mapping exactly."""
    _require(type(value) is dict and set(value) == _RECEIPT_KEYS and type(value["params"]) is list
             and all(type(pair) is list and len(pair) == 2 and all(type(item) is str for item in pair)
                     for pair in value["params"])
             and all(type(value[key]) is str for key in ("path", "account_scope", "raw_body_b64", "sha256"))
             and _valid_stamp(value["received_at"]) and _valid_stamp(value["server_time"]),
             "HISTORY_STORE_RECORD_INVALID")
    receipt = SourceReceipt(path=value["path"], params=tuple((key, item) for key, item in value["params"]),
                            account_scope=value["account_scope"],
                            received_at=datetime.fromisoformat(value["received_at"]),
                            server_time=datetime.fromisoformat(value["server_time"]),
                            raw_body=base64.b64decode(value["raw_body_b64"], validate=True), sha256=value["sha256"])
    _require(_receipt_body(receipt) == value, "HISTORY_STORE_RECORD_INVALID")
    return receipt


def _parse_anchor(value):
    _require(type(value) is dict and set(value) == _ANCHOR_KEYS and _valid_stamp(value["account_asof"]),
             "HISTORY_STORE_RECORD_INVALID")
    anchor = AccountAnchor(cash_quote=_decimal(value["cash_quote"]), units=_decimal(value["units"]),
                           account_asof=datetime.fromisoformat(value["account_asof"]))
    _require(_anchor_body(anchor) == value, "HISTORY_STORE_RECORD_INVALID")
    return anchor


def _sha256(value):
    return type(value) is str and _HASH.fullmatch(value) is not None


def _markets(value):
    """A list of distinct KRW market ids."""
    return (type(value) is list and all(type(item) is str and UNIVERSE_MARKET.fullmatch(item) is not None
                                        for item in value) and len(set(value)) == len(value))


def _price_text(price):
    """A defined price in the section 14 encoding: a positive finite Decimal as canonical text of at most 16
    characters. Anything else is no price at that slot."""
    if type(price) is not Decimal or not price.is_finite() or price <= 0:
        return None
    try:
        text = _plain(price)
    except ValueError:
        return None
    return text if len(text) <= MAX_PRICE_TEXT else None


def _chooser_parts(record):
    """(top_n, flags, prices) of one stored universe record, as ChooserInputs holds them. Prices exist only when
    both reads were available; a priced market is unflagged unless it is a recorded exception (spec section 14)."""
    top_n = () if record["snapshot"] == "unavailable" else tuple(record["snapshot"]["top_n"])
    flags = {} if record["flags"] == "unavailable" else {market: kind for market, kind in record["flags"]["exceptions"]}
    prices = {}
    if record["tickers"] != "unavailable":
        for market, text, _ in record["tickers"]["prices"]:
            prices[market] = _decimal(text)
            flags.setdefault(market, "unflagged")
    return top_n, tuple(sorted(flags.items())), tuple(sorted(prices.items()))


def _parse_record(value):
    """A stored universe record, checked for shape and canonical text; the chooser reads it exactly as stored."""
    _require(type(value) is dict and set(value) == _RECORD_KEYS, "HISTORY_STORE_RECORD_INVALID")
    snapshot, flags, tickers = value["snapshot"], value["flags"], value["tickers"]
    _require(snapshot == "unavailable"
             or (type(snapshot) is dict and set(snapshot) == {"day", "sha256", "top_n"}
                 and type(snapshot["day"]) is str and _sha256(snapshot["sha256"]) and _markets(snapshot["top_n"])),
             "HISTORY_STORE_RECORD_INVALID")
    _require(flags == "unavailable"
             or (type(flags) is dict and set(flags) == {"sha256", "exceptions"} and _sha256(flags["sha256"])
                 and type(flags["exceptions"]) is list
                 and all(type(item) is list and len(item) == 2 and item[1] in _EXCEPTION_CLASSES
                         for item in flags["exceptions"])
                 and _markets([item[0] for item in flags["exceptions"]])
                 and flags["exceptions"] == sorted(flags["exceptions"])),
             "HISTORY_STORE_RECORD_INVALID")
    _require(tickers == "unavailable"
             or (flags != "unavailable" and type(tickers) is dict and set(tickers) == {"sha256", "prices"}
                 and _sha256(tickers["sha256"]) and type(tickers["prices"]) is list
                 and all(type(item) is list and len(item) == 3 and type(item[1]) is str
                         and _price_text(_decimal(item[1])) == item[1]
                         and type(item[2]) is int and abs(item[2]) <= PRICE_WINDOW_MS for item in tickers["prices"])
                 and _markets([item[0] for item in tickers["prices"]])),
             "HISTORY_STORE_RECORD_INVALID")
    _require(_markets(value["allow"]) and value["allow"] == sorted(value["allow"])
             and all(type(value[key]) is list and all(type(item) is str for item in value[key])
                     for key in ("reasons", "events")), "HISTORY_STORE_RECORD_INVALID")
    return value


def _tail_row(journal):
    """The last complete, hash-checked row of the journal, read without the journal lock."""
    try:
        with open(journal, "rb") as fh:
            fh.seek(0, os.SEEK_END)
            fh.seek(max(0, fh.tell() - MAX_ROW_BYTES - 1))
            tail = fh.read(MAX_ROW_BYTES + 2)
        row = _decode(tail[tail.rfind(b"\n", 0, len(tail) - 1) + 1:])
        _require(set(row) == _ROW_KEYS and type(row["seq"]) is int and row["seq"] >= 1
                 and _row_digest(row) == row["row_sha256"], "HISTORY_CHAIN_TRANSITION_UNVERIFIED")
        return row
    except LiveHistoryError:
        raise
    except Exception:
        raise LiveHistoryError("HISTORY_CHAIN_TRANSITION_UNVERIFIED") from None


def _validate_slot_structure(data, index, at):
    """Independent v3 head boundary. Profile-dependent dust and chooser math remain replay's job."""
    from execution_accounts.quotes import parse_orderbook
    _require(type(data) is dict and set(data) == _SLOT_V2_KEYS
             and type(data["index"]) is int and data["index"] == index
             and type(data["trade_symbol"]) is str
             and UNIVERSE_MARKET.fullmatch(data["trade_symbol"]) is not None,
             "HISTORY_STORE_RECORD_INVALID")
    tick = _decimal(data["tick_size"])
    _require(tick > 0 and _plain(tick) == data["tick_size"], "HISTORY_STORE_RECORD_INVALID")
    anchor = _parse_anchor(data["anchor"])
    _require(anchor.cash_quote >= 0 and anchor.units >= 0
             and timedelta(0) <= at - anchor.account_asof <= ACCOUNT_MAX_AGE,
             "HISTORY_STORE_RECORD_INVALID")
    if data["receipt"] != "unavailable":
        book = parse_orderbook(_parse_receipt(data["receipt"]), symbol=data["trade_symbol"], now=at)
        _require((Fraction(book.bid) / Fraction(tick)).denominator == 1
                 and (Fraction(book.ask) / Fraction(tick)).denominator == 1,
                 "HISTORY_STORE_RECORD_INVALID")
    holdings = data["holdings"]
    _require(type(holdings) is list, "HISTORY_STORE_RECORD_INVALID")
    for row in holdings:
        _require(type(row) is list and len(row) == 6 and type(row[0]) is str
                 and UNIVERSE_MARKET.fullmatch(row[0]) is not None and _valid_stamp(row[3])
                 and type(row[4]) is bool and type(row[5]) is bool,
                 "HISTORY_STORE_RECORD_INVALID")
        units, price = _decimal(row[1]), _decimal(row[2])
        _require(units >= 0 and price >= 0 and _plain(units) == row[1] and _plain(price) == row[2]
                 and row[4] == (price == 0) and (price != 0 or row[5]),
                 "HISTORY_STORE_RECORD_INVALID")
    _require(holdings == sorted(holdings) and len({row[0] for row in holdings}) == len(holdings),
             "HISTORY_STORE_RECORD_INVALID")
    _parse_record(data["universe"])
    choice = data["decision"]
    if choice is not None:
        _require(type(choice) is dict and set(choice) == {"coin", "target_fraction", "held", "hold_count"}
                 and type(choice["hold_count"]) is int and choice["hold_count"] >= 0
                 and all(choice[key] is None or (type(choice[key]) is str
                         and UNIVERSE_MARKET.fullmatch(choice[key]) is not None) for key in ("coin", "held")),
                 "HISTORY_STORE_RECORD_INVALID")
        fraction = _decimal(choice["target_fraction"])
        _require(0 <= fraction <= 1 and _plain(fraction) == choice["target_fraction"],
                 "HISTORY_STORE_RECORD_INVALID")
    return data


def _v3_slot(root, window_sha, identity, policy, row):
    """Resolve an authenticated reference against externally bound context, never context learned from a row."""
    try:
        data = row["data"]
        _require(type(data) is dict and set(data) == _SLOT_V3_KEYS
                 and type(data["history_version"]) is int and data["history_version"] == 3
                 and type(data["index"]) is int and data["index"] == row["seq"] - 2
                 and _valid_stamp(row["utc"]), "HISTORY_STORE_RECORD_INVALID")
        reference = decode_reference(_canonical(data["payload_ref"]))
        context = SlotContext(window_digest=window_sha, driver_identity_digest=digest(identity),
                              index=data["index"], sampled_at=datetime.fromisoformat(row["utc"]))
        objects = EvidenceObjectStore(root=root / STORE_DIRECTORY / window_sha / OBJECT_DIRECTORY,
                                      limits=policy.object_limits)
        slot = decode_slot_payload(objects.read(reference), context=context, policy=policy)
        return _validate_slot_structure(slot, context.index, context.sampled_at)
    except LiveHistoryError:
        raise
    except (EvidenceObjectError, HistoryStorageError, ValueError, TypeError, KeyError, OverflowError):
        raise LiveHistoryError("HISTORY_STORE_RECORD_INVALID") from None


class HistoryChain:
    """The journal as the chain behind its BaselineHead: GENESIS over an absent or empty journal at the reviewed
    initialization, the fsynced tail row (``prev_sha256 == old``, ``row_sha256 == new``) at every advance. It reads
    without the journal lock, because the recording instance holds that lock while the head advances."""
    def __init__(self, *, root: Path, window: DeploymentWindow,
                 storage_policy: HistoryStoragePolicy | None = None) -> None:
        self._digest = _window_digest(window)
        self._root, self._window = root, window
        self._storage_policy = storage_policy
        self._identity, self._step = None, None
        self._policy_sha = None
        if storage_policy is not None:
            try:
                parse_policy(policy_bytes(storage_policy))
                self._policy_sha = policy_digest(storage_policy)
            except (HistoryStorageError, ValueError, TypeError):
                raise LiveHistoryError("HISTORY_STORAGE_POLICY_INVALID") from None
        _checked(root, self._digest)

    def bind_identity(self, identity: FixedDriverIdentity, *, bar_seconds: int) -> None:
        """One-time external context from the issued driver's checked LiveHistory.bind, not from journal bytes."""
        _require(type(identity) is FixedDriverIdentity and identity.deployment_window_digest == self._digest
                 and type(bar_seconds) is int and 60 <= bar_seconds <= 86400,
                 "HISTORY_DRIVER_BINDING_MISMATCH")
        step = timedelta(seconds=bar_seconds)
        _require(self._identity is None or (identity == self._identity and step == self._step),
                 "HISTORY_IDENTITY_CHANGED")
        self._identity, self._step = identity, step

    def _journal(self):
        return _checked(self._root, self._digest) / "history.jsonl"

    def seed(self, digest: str) -> int:
        journal = self._journal()
        try:
            empty = not journal.exists() or os.lstat(journal).st_size == 0
        except OSError:
            empty = False
        _require(digest == GENESIS and empty, "HISTORY_CHAIN_SEED_REQUIRED")
        return 0

    def successor(self, old: str, new: str) -> int:
        row = _tail_row(self._journal())
        _require(row["prev_sha256"] == old and row["row_sha256"] == new, "HISTORY_CHAIN_TRANSITION_UNVERIFIED")
        if self._storage_policy is not None:
            _require(policy_digest(self._storage_policy) == self._policy_sha,
                     "HISTORY_STORAGE_POLICY_MISMATCH")
            _require(self._identity is not None and self._step is not None,
                     "HISTORY_DRIVER_BINDING_MISMATCH")
            _require(type(row["schema"]) is int and row["schema"] == SCHEMA and _valid_stamp(row["utc"]),
                     "HISTORY_CHAIN_TRANSITION_UNVERIFIED")
            data = row["data"]
            if row["seq"] == 1:
                _require(row["kind"] == "bound" and type(data) is dict and set(data) == _BOUND_V3_KEYS
                         and type(data["history_version"]) is int and data["history_version"] == 3
                         and datetime.fromisoformat(row["utc"]) < self._window.start
                         and data["identity"] == asdict(self._identity)
                         and parse_policy(_canonical(data["history_storage"])) == self._storage_policy,
                         "HISTORY_CHAIN_TRANSITION_UNVERIFIED")
            else:
                _require(row["kind"] == "slot", "HISTORY_CHAIN_TRANSITION_UNVERIFIED")
                slot = self._window.start + (row["seq"] - 2) * self._step
                at = datetime.fromisoformat(row["utc"])
                _require(slot <= self._window.end and slot <= at <= slot + EXECUTION_WINDOW,
                         "HISTORY_CHAIN_TRANSITION_UNVERIFIED")
                payload = _v3_slot(self._root, self._digest, self._identity, self._storage_policy, row)
                _require((payload["decision"] is None) == (slot == self._window.end),
                         "HISTORY_CHAIN_TRANSITION_UNVERIFIED")
        else:
            _require(type(row["data"]) is dict and "history_version" not in row["data"],
                     "HISTORY_CHAIN_TRANSITION_UNVERIFIED")
        return row["seq"]


@dataclass(frozen=True)
class SlotUniverse:
    """The coordinator's universe inputs for one slot (spec section 12): the snapshot in force (None when there is
    none), the slot's flag and ticker reads, and the allow-list, buy-block reasons and events it derived."""
    snapshot: Universe | None
    flags: FlagRead
    tickers: TickerRead
    allow: frozenset[str]
    reasons: tuple[str, ...]
    events: tuple[str, ...]




@dataclass(frozen=True, kw_only=True)
class _Slot:
    """In-memory, verified and derived; never serialized."""
    bar: PaperBar | UniverseBar
    anchor: AccountAnchor
    decision: PaperDecision | FixedDecisionV2 | None  # carry-v2 retains the final observed decision too
    sampled_at: datetime
    row_sha256: str
    universe_sha256: str | None = None   # universe windows: evidence_digest of the slot's stored universe record


class LiveHistory:
    """Construction validates types and paths only: no clock, no head, nothing created. ``bind`` either creates
    the journal (before the window starts, head at GENESIS) or replays it from the original bytes; every later
    operation re-runs the path checks and the head and size checks before trusting the durable record."""
    def __init__(self, program: ProgramSpec, protocol: ForwardProtocol, profile: LaunchProfile, *,
                 window: DeploymentWindow, root: Path, clock: Callable[[], datetime], trusted_head,
                 storage_policy: HistoryStoragePolicy | None = None) -> None:
        _require(type(program) is ProgramSpec and type(protocol) is ForwardProtocol and type(profile) is LaunchProfile
                 and callable(clock) and type(trusted_head) is BaselineHead, "HISTORY_INPUT_REQUIRED")
        self._digest = _window_digest(window)
        try:
            self._step = timedelta(seconds=protocol.bar_seconds)
            self._slot_count = (window.end - window.start) // self._step + 1
        except (TypeError, ValueError, ZeroDivisionError, OverflowError):
            raise LiveHistoryError("HISTORY_INPUT_REQUIRED") from None
        self._dir = _checked(root, self._digest)
        self._base = root
        self._program, self._protocol, self._profile, self._window = program, protocol, profile, window
        self._universe = protocol.universe_rule_sha256 is not None
        self._carry = resolve_behavior(protocol) == "protective-carry-v2"
        self._storage_policy = storage_policy
        try:
            _require((storage_policy is None) == (protocol.history_storage_sha256 is None),
                     "HISTORY_STORAGE_POLICY_REQUIRED")
            if storage_policy is not None:
                _require(self._universe and policy_digest(storage_policy) == protocol.history_storage_sha256,
                         "HISTORY_STORAGE_POLICY_MISMATCH")
                chain = trusted_head._chain
                _require(type(chain) is HistoryChain and chain._root == root and chain._digest == self._digest
                         and chain._storage_policy == storage_policy, "HISTORY_DRIVER_BINDING_MISMATCH")
        except LiveHistoryError:
            raise
        except (HistoryStorageError, ValueError, TypeError, AttributeError):
            raise LiveHistoryError("HISTORY_STORAGE_POLICY_INVALID") from None
        self._storage_policy_sha = protocol.history_storage_sha256
        self._driver_identity = None
        self._clock, self._head_authority = clock, trusted_head
        self._identity, self._bound, self._failed = "", False, False
        self._slots, self._chain, self._marks = (), "", ()
        self._prices, self._state, self._inputs = (), _START, ()    # last L+1 price vectors, h and count, inputs
        self.recorded_allow = None   # the allow-list of the last universe row; that slot's buys use only it
        self._head, self._size, self._seq = GENESIS, 0, 0
        self.provider = self._provide
        self.verifier = self._verify

    # -- paths, clock and the trusted head -------------------------------------------------------------------

    def _paths(self):
        _checked(self._base, self._digest)

    def _now(self):
        return _clock_value(self._clock)

    def _read_head(self):
        try:
            return self._head_authority.read()
        except Exception as exc:
            uninitialized = isinstance(exc, BaselineHeadError) and str(exc) == "HEAD_NOT_INITIALIZED"
            raise LiveHistoryError("HISTORY_HEAD_NOT_INITIALIZED" if uninitialized
                                   else "HISTORY_TRUSTED_HEAD_READ_FAILED") from None

    def _file_size(self):
        try:
            target = self._dir / "history.jsonl"
            return os.lstat(target).st_size if target.exists() else 0
        except OSError:
            raise LiveHistoryError("HISTORY_STORE_IO_REFUSED") from None

    def _check_storage_policy(self):
        try:
            _require((self._storage_policy is None) == (self._storage_policy_sha is None)
                     and self._protocol.history_storage_sha256 == self._storage_policy_sha,
                     "HISTORY_STORAGE_POLICY_MISMATCH")
            if self._storage_policy is not None:
                _require(policy_digest(self._storage_policy) == self._storage_policy_sha,
                         "HISTORY_STORAGE_POLICY_MISMATCH")
        except HistoryStorageError:
            raise LiveHistoryError("HISTORY_STORAGE_POLICY_MISMATCH") from None

    def _ready(self):
        self._check_storage_policy()
        _require(not self._failed, "HISTORY_RECONCILIATION_REQUIRED")
        _require(self._bound, "HISTORY_NOT_BOUND")

    @contextmanager
    def _locked(self, *, create=False):
        try:
            self._paths()
            if create:
                checked_target(self._dir, "history directory", within=self._base).mkdir(mode=0o700, parents=True, exist_ok=True)
            handle = open(checked_target(self._dir / "history.lock", "history lock", within=self._dir), "a+b")
        except LiveHistoryError:
            raise
        except (OSError, ValueError, RuntimeError, TypeError):
            raise LiveHistoryError("HISTORY_STORE_IO_REFUSED") from None
        with handle:
            try:
                _lock(handle, True)
            except OSError:
                raise LiveHistoryError("HISTORY_STORE_IO_REFUSED") from None
            try:
                self._paths()
                yield
            finally:
                _lock(handle, False)

    # -- derivation --------------------------------------------------------------------------------------------

    def _anchor(self, account, symbol):
        _require(type(account) is AccountObservation, "HISTORY_ACCOUNT_REQUIRED")
        venue, scope = self._profile.venue, self._profile.account_scope
        key = (venue, scope)
        _require(account.account_scopes.get(venue) == scope and key in account.settled_cash_krw,
                 "HISTORY_ACCOUNT_SCOPE_MISMATCH")
        try:
            anchor = AccountAnchor(cash_quote=account.settled_cash_krw[key],
                                   units=account.holdings.get((venue, scope, self._profile.market, symbol),
                                                              Decimal(0)),
                                   account_asof=account.asof)
            _require(type(anchor.cash_quote) is Decimal and type(anchor.units) is Decimal and _aware(anchor.account_asof),
                     "HISTORY_ANCHOR_INVALID")
            _anchor_body(anchor)
        except LiveHistoryError:
            raise
        except Exception:
            raise LiveHistoryError("HISTORY_ANCHOR_INVALID") from None
        return anchor

    def _slot_at(self, index, sampled_at):
        """Slot `index`'s time; a slot is recorded only inside [slot, slot + 10 s] and never past the window end."""
        slot = self._window.start + index * self._step
        _require(slot <= self._window.end, "HISTORY_WINDOW_COMPLETE")
        _require(slot <= sampled_at, "HISTORY_SLOT_NOT_DUE")
        _require(sampled_at <= slot + EXECUTION_WINDOW, "HISTORY_SLOT_MISSED")
        return slot

    def _derive(self, index, book, anchor, sampled_at, chain, marks):
        """The bar, the decision and the running chain for slot `index`, under the same rules at recording and replay."""
        slot = self._slot_at(index, sampled_at)
        bar = sample_prefetched_book(book, slot=slot, sampled_at=sampled_at)
        _require(book.symbol == self._protocol.symbol, "HISTORY_BOOK_MARKET_MISMATCH")
        _require(timedelta(0) <= sampled_at - anchor.account_asof <= ACCOUNT_MAX_AGE, "HISTORY_ACCOUNT_STALE_OR_FUTURE")
        chain = evidence_digest((chain, bar))
        marks = (marks + (bar.mark,)) if self._carry else (
            (marks + (bar.mark,))[-self._program.slow_window:] if self._program.kind != "cash" else (bar.mark,))
        decision = None
        if slot < self._window.end:
            _require(sampled_at + timedelta(seconds=self._protocol.minimum_fill_delay_seconds) <= slot + self._step,
                     "HISTORY_DECISION_TOO_LATE")
        if self._carry:
            # Retain the last actual model observation. _frame still supplies only the prior
            # slot's decision, so recording the final verdict does not remove execution lag.
            decision = derive_fixed_decision_v2(self._program, marks, bar_index=index,
                                                decided_at=sampled_at, history_sha256=chain)
        elif slot < self._window.end:
            decision = PaperDecision(bar_index=index, decided_at=sampled_at, history_sha256=chain,
                                     target_fraction=target_fraction(self._program, marks))
        return bar, decision, chain, marks

    def _holding(self, symbol, units, price, asof):
        """One holding of the row's account anchor (spec section 12): symbol, units, mark, mark time, unlisted
        (marked at 0, spec section 11) and dust (worth less than the signed minimum order at its mark; an unlisted
        holding is always dust)."""
        _require(type(symbol) is str and UNIVERSE_MARKET.fullmatch(symbol) is not None
                 and type(units) is Decimal and units.is_finite() and units >= 0
                 and type(price) is Decimal and price.is_finite() and price >= 0 and _aware(asof),
                 "HISTORY_INPUT_REQUIRED")
        minimum = Fraction(self._profile.instrument_rules.min_notional_krw)
        return [symbol, _plain(units), _plain(price), _utc(asof), price == 0,
                price == 0 or Fraction(units) * Fraction(price) < minimum]

    def _parse_holdings(self, value):
        """Stored holdings must be exactly what _holding writes for their own values."""
        _require(type(value) is list and all(type(row) is list and len(row) == 6 and _valid_stamp(row[3])
                                             for row in value), "HISTORY_STORE_RECORD_INVALID")
        parsed = sorted(self._holding(row[0], _decimal(row[1]), _decimal(row[2]), datetime.fromisoformat(row[3]))
                        for row in value)
        _require(parsed == value and len({row[0] for row in value}) == len(value), "HISTORY_STORE_RECORD_INVALID")

    def _universe_record(self, slot, universe):
        """The row's universe part (spec section 12): the snapshot in force (day, sha256, top-N), the flag read's
        exceptions and the ticker read's defined prices of listed coins, each with its raw-body sha256 or
        "unavailable", then the allow-list, buy-block reasons and events as given. A price is kept only for a market
        the flag read lists, so the ticker part is unavailable whenever the flag part is."""
        _require(type(universe.allow) is frozenset and type(universe.reasons) is tuple
                 and type(universe.events) is tuple and _markets(sorted(universe.allow))
                 and all(type(item) is str for item in universe.reasons + universe.events),
                 "HISTORY_INPUT_REQUIRED")
        snapshot, flags, tickers = universe.snapshot, universe.flags, universe.tickers
        in_force = (type(snapshot) is Universe and snapshot.rule_sha256 == self._protocol.universe_rule_sha256
                    and snapshot.valid_from <= slot < snapshot.valid_until)
        flagged = (type(flags) is FlagRead and flags.ok is True and _sha256(flags.sha256)
                   and _markets(list(flags.flags)))
        priced = flagged and type(tickers) is TickerRead and tickers.ok is True and _sha256(tickers.sha256)
        prices = []
        for market in snapshot.listed if priced and in_force else ():
            if market in flags.flags and market in tickers.prices:
                price, traded = tickers.prices[market]
                offset = (traded - slot) // timedelta(milliseconds=1)
                text = _price_text(price)
                if text is not None and abs(offset) <= PRICE_WINDOW_MS:
                    prices.append([market, text, offset])
        return {"snapshot": {"day": snapshot.day.isoformat(), "sha256": snapshot.snapshot_sha256,
                             "top_n": list(universe_top_n(snapshot, self._program.max_candidates))}
                if in_force else "unavailable",
                "flags": {"sha256": flags.sha256,
                          "exceptions": sorted([market, kind if kind in _EXCEPTION_CLASSES else "unknown"]
                                               for market, kind in flags.flags.items() if kind != "unflagged")}
                if flagged else "unavailable",
                "tickers": {"sha256": tickers.sha256, "prices": prices} if priced else "unavailable",
                "allow": sorted(universe.allow), "reasons": list(universe.reasons), "events": list(universe.events)}

    def _derive_universe(self, index, book, anchor, sampled_at, chain, prices, state, symbol, tick, record):
        """A universe slot (spec section 12): the recorded trade coin's bar (no book fields when its book was
        unavailable), the section 14 decision from the stored record, and the running chain, last L+1 price vectors
        and chooser state, under the same rules at recording and replay."""
        slot = self._slot_at(index, sampled_at)
        if book is None:
            bar = UniverseBar(observed_at=slot, received_at=sampled_at, symbol=symbol, tick_size=tick,
                              bid=None, ask=None, mark=None, source_sha256=None)
        else:
            paper = sample_prefetched_book(book, slot=slot, sampled_at=sampled_at)
            _require(book.symbol == symbol, "HISTORY_BOOK_MARKET_MISMATCH")
            # The driver re-checks every bar at its own tick on every later tick, so an off-tick book would block
            # the rest of the window; it is refused here and the caller can record the slot without a book.
            _require((Fraction(paper.bid) / Fraction(tick)).denominator == 1
                     and (Fraction(paper.ask) / Fraction(tick)).denominator == 1, "HISTORY_BOOK_OFF_TICK")
            bar = UniverseBar(observed_at=slot, received_at=sampled_at, symbol=symbol, tick_size=tick,
                              bid=paper.bid, ask=paper.ask, mark=paper.mark, source_sha256=paper.source_sha256)
        _require(timedelta(0) <= sampled_at - anchor.account_asof <= ACCOUNT_MAX_AGE, "HISTORY_ACCOUNT_STALE_OR_FUTURE")
        chain = evidence_digest((chain, bar))
        top_n, flags, now_prices = _chooser_parts(record)
        window = self._program.lookback_slots + 1
        prices = (prices + (now_prices,))[-window:]
        decision = inputs = choice = None
        if slot < self._window.end:
            _require(sampled_at + timedelta(seconds=self._protocol.minimum_fill_delay_seconds) <= slot + self._step,
                     "HISTORY_DECISION_TOO_LATE")
            inputs = ChooserInputs(held=state.held, hold_count=state.hold_count, top_n=top_n, flags=flags,
                                   prices=now_prices, lag_prices=prices[0] if len(prices) == window else None)
            coin, state = chooser_decision(self._program, inputs)
            fraction = self._program.exposure_fraction if coin is not None else Decimal(0)
            decision = PaperDecision(bar_index=index, decided_at=sampled_at, history_sha256=chain,
                                     target_fraction=fraction)
            choice = {"coin": coin, "target_fraction": _plain(fraction), "held": state.held,
                      "hold_count": state.hold_count}
        return bar, decision, chain, prices, state, inputs, choice

    def _frame(self):
        prior = len(self._slots) >= 2
        return HistoryFrame(deployment_window_digest=self._digest, source_kind="prospective_paper_capture",
                            bars=tuple(slot.bar for slot in self._slots),
                            prior_decision=self._slots[-2].decision if prior else None,
                            anchor=self._slots[-1].anchor, universe_sha256=self._slots[-1].universe_sha256,
                            chooser_inputs=self._inputs[-2] if prior and self._universe else None)

    def _current(self, now):
        _require(self._slots, "HISTORY_SLOT_NOT_RECORDED")
        slot = self._slots[-1]
        _require(slot.bar.observed_at <= now <= slot.bar.observed_at + EXECUTION_WINDOW, "HISTORY_SLOT_NOT_RECORDED")
        return slot

    # -- durable record ----------------------------------------------------------------------------------------

    def _object_store(self):
        return EvidenceObjectStore(root=self._dir / OBJECT_DIRECTORY, limits=self._storage_policy.object_limits)

    def _append(self, kind, data, at, *, create=False):
        self._check_storage_policy()
        if create and self._storage_policy is not None:
            # Refuse an impossible header before creating even the history lock/directory.
            try:
                preflight = _canonical(_row(self._seq + 1, self._head, kind, data, at)) + b"\n"
                admit_journal_row(self._storage_policy, journal_bytes=self._size, next_row_bytes=len(preflight))
            except HistoryStorageError:
                raise LiveHistoryError("HISTORY_STORAGE_LIMIT_EXCEEDED") from None
        with self._locked(create=create):
            _require(self._read_head() == self._head, "HISTORY_HEAD_MISMATCH")
            _require(self._file_size() == self._size, "HISTORY_STORE_CHANGED")
            payload = preview = objects = None
            policy = self._storage_policy
            try:
                if policy is not None and kind == "slot":
                    context = SlotContext(window_digest=self._digest, driver_identity_digest=self._identity,
                                          index=data["index"], sampled_at=at)
                    payload = encode_slot_payload(data, context=context, policy=policy)
                    objects = self._object_store()
                    preview = objects.preview(payload)
                    data = {"history_version": 3, "index": data["index"],
                            "payload_ref": asdict(preview.reference)}
                row = _row(self._seq + 1, self._head, kind, data, at)
                line = _canonical(row) + b"\n"
                _require(len(line) <= MAX_ROW_BYTES and self._seq < self._slot_count + 1,
                         "HISTORY_STORE_RECORD_INVALID")
                if policy is not None:
                    admit_journal_row(policy, journal_bytes=self._size, next_row_bytes=len(line))
                    if create:
                        # Window infrastructure, before its bound row commits; slot admission itself creates no infra.
                        self._object_store().initialize()
                        self._object_store().inventory(budget=policy.store_budget)
                    if payload is not None:
                        reference = objects.stage(payload, budget=policy.store_budget)
                        _require(reference == preview.reference, "HISTORY_STORAGE_REFERENCE_CHANGED")
            except (EvidenceObjectError, HistoryStorageError) as exc:
                code = "HISTORY_STORAGE_LIMIT_EXCEEDED" if "LIMIT" in str(exc) else "HISTORY_STORAGE_UNAVAILABLE"
                raise LiveHistoryError(code) from None
            self._failed = True
            try:
                with open(checked_target(self._dir / "history.jsonl", "history journal", within=self._dir), "ab") as fh:
                    _require(fh.write(line) == len(line), "HISTORY_STORE_IO_REFUSED")
                    fh.flush()
                    os.fsync(fh.fileno())
                if create:
                    _sync_directory(self._dir)
            except (OSError, ValueError, RuntimeError, TypeError):
                raise LiveHistoryError("HISTORY_STORE_IO_REFUSED") from None
            new = row["row_sha256"]
            try:
                accepted = self._head_authority.compare_and_set(self._head, new)
            except Exception:
                raise LiveHistoryError("HISTORY_TRUSTED_HEAD_UPDATE_FAILED") from None
            _require(accepted is True, "HISTORY_TRUSTED_HEAD_UPDATE_REFUSED")
            _require(self._read_head() == new, "HISTORY_TRUSTED_HEAD_CHANGED")
            self._head, self._size, self._seq = new, self._size + len(line), self._seq + 1
            self._failed = False
            return new

    def _replay(self, identity, *, install=True):
        """Validate the complete prefix. With install=False return a snapshot without adopting any state."""
        from execution_accounts.quotes import parse_orderbook
        self._check_storage_policy()
        with self._locked():
            slots, chain, marks, previous, size, seq = [], "", (), GENESIS, 0, 0
            prices, state, recent, allow = (), _START, (), None
            try:
                with open(checked_target(self._dir / "history.jsonl", "history journal", within=self._dir), "rb") as fh:
                    while True:
                        line = fh.readline(MAX_ROW_BYTES + 1)
                        if not line:
                            break
                        seq += 1
                        if self._storage_policy is not None:
                            admit_journal_row(self._storage_policy, journal_bytes=size, next_row_bytes=len(line))
                        _require(seq <= self._slot_count + 1, "HISTORY_STORE_RECORD_INVALID")
                        row = _decode(line)
                        _require(set(row) == _ROW_KEYS and type(row["schema"]) is int and row["schema"] == SCHEMA
                                 and type(row["seq"]) is int and row["seq"] == seq and row["prev_sha256"] == previous
                                 and row["kind"] == ("bound" if seq == 1 else "slot") and _valid_stamp(row["utc"])
                                 and type(row["data"]) is dict and _row_digest(row) == row["row_sha256"],
                                 "HISTORY_STORE_RECORD_INVALID")
                        at, data = datetime.fromisoformat(row["utc"]), row["data"]
                        if seq == 1:
                            expected_keys = {"identity"} if self._storage_policy is None else _BOUND_V3_KEYS
                            _require(set(data) == expected_keys, "HISTORY_STORE_RECORD_INVALID")
                            if self._storage_policy is not None:
                                _require(type(data["history_version"]) is int and data["history_version"] == 3
                                         and at < self._window.start
                                         and parse_policy(_canonical(data["history_storage"])) == self._storage_policy,
                                         "HISTORY_STORE_RECORD_INVALID")
                            _require(type(data["identity"]) is dict
                                     and set(data["identity"]) == _IDENTITY_KEYS
                                     and all(type(value) is str for value in data["identity"].values()),
                                     "HISTORY_STORE_RECORD_INVALID")
                            _require(data["identity"] == asdict(identity), "HISTORY_IDENTITY_CHANGED")
                        elif self._universe:
                            if self._storage_policy is not None:
                                data = _v3_slot(self._base, self._digest, identity, self._storage_policy, row)
                            # The preserved logical history row v2: the row's own trade coin and tick and its book or none; the decision
                            # derived again from the stored record must equal the stored one (spec section 12).
                            _require(set(data) == _SLOT_V2_KEYS and type(data["index"]) is int
                                     and data["index"] == seq - 2 and type(data["trade_symbol"]) is str
                                     and UNIVERSE_MARKET.fullmatch(data["trade_symbol"]) is not None,
                                     "HISTORY_STORE_RECORD_INVALID")
                            symbol, tick = data["trade_symbol"], _decimal(data["tick_size"])
                            _require(tick > 0 and _plain(tick) == data["tick_size"], "HISTORY_STORE_RECORD_INVALID")
                            anchor, record = _parse_anchor(data["anchor"]), _parse_record(data["universe"])
                            self._parse_holdings(data["holdings"])
                            book = None if data["receipt"] == "unavailable" else parse_orderbook(
                                _parse_receipt(data["receipt"]), symbol=symbol, now=at)
                            bar, decision, chain, prices, state, inputs, choice = self._derive_universe(
                                seq - 2, book, anchor, at, chain, prices, state, symbol, tick, record)
                            _require(choice == data["decision"], "HISTORY_STORE_RECORD_INVALID")
                            slots.append(_Slot(bar=bar, anchor=anchor, decision=decision, sampled_at=at,
                                               row_sha256=row["row_sha256"], universe_sha256=evidence_digest(record)))
                            recent, allow = (recent + (inputs,))[-2:], frozenset(record["allow"])
                        else:
                            _require(set(data) == {"index", "receipt", "anchor"} and type(data["index"]) is int
                                     and data["index"] == seq - 2, "HISTORY_STORE_RECORD_INVALID")
                            receipt, anchor = _parse_receipt(data["receipt"]), _parse_anchor(data["anchor"])
                            book = parse_orderbook(receipt, symbol=self._protocol.symbol, now=at)
                            bar, decision, chain, marks = self._derive(seq - 2, book, anchor, at, chain, marks)
                            slots.append(_Slot(bar=bar, anchor=anchor, decision=decision, sampled_at=at,
                                               row_sha256=row["row_sha256"]))
                        previous, size = row["row_sha256"], size + len(line)
                _require(seq >= 1, "HISTORY_STORE_RECORD_INVALID")
            except LiveHistoryError as exc:
                if str(exc) == "HISTORY_IDENTITY_CHANGED":
                    raise
                raise LiveHistoryError("HISTORY_STORE_RECORD_INVALID") from None
            except OSError:
                raise LiveHistoryError("HISTORY_STORE_IO_REFUSED") from None
            except Exception:
                raise LiveHistoryError("HISTORY_STORE_RECORD_INVALID") from None
            _require(self._read_head() == previous, "HISTORY_HEAD_MISMATCH")
            result = (tuple(slots), chain, marks, prices, state, recent, allow, previous, size, seq)
            if install:
                self._slots, self._chain, self._marks = tuple(slots), chain, marks
                self._prices, self._state, self._inputs, self.recorded_allow = prices, state, recent, allow
                self._head, self._size, self._seq = previous, size, seq
            return result

    def _durable_unchanged(self):
        _require(self._read_head() == self._head, "HISTORY_HEAD_MISMATCH")
        self._paths()
        _require(self._file_size() == self._size, "HISTORY_STORE_CHANGED")
        if self._storage_policy is not None:
            actual = self._replay(self._driver_identity, install=False)
            expected = (self._slots, self._chain, self._marks, self._prices, self._state, self._inputs,
                        self.recorded_allow, self._head, self._size, self._seq)
            _require(actual == expected, "HISTORY_STORE_CHANGED")

    # -- public contract ---------------------------------------------------------------------------------------

    def bind(self, driver: StrategyDriver) -> FixedDriverIdentity:
        """Bind the issued fixed driver whose history callables are exactly this instance's, then create the
        journal (only before the window starts, over a head at GENESIS) or replay the existing one."""
        with _LOCK:
            self._check_storage_policy()
            _require(not self._failed, "HISTORY_RECONCILIATION_REQUIRED")
            _require(not self._bound, "HISTORY_ALREADY_BOUND")
            try:
                identity = describe_fixed_driver(driver)
                provider, verifier = fixed_history_dependencies(driver)
            except Exception:
                raise LiveHistoryError("HISTORY_DRIVER_REQUIRED") from None
            _require(provider is self.provider and verifier is self.verifier, "HISTORY_CALLBACK_MISMATCH")
            _require(identity.deployment_window_digest == self._digest
                     and identity.protocol_digest == evidence_digest(self._protocol)
                     and identity.profile_contract_digest == profile_contract_digest(self._profile)
                     and identity.program_digest == program_digest(self._program, driver.artifact),
                     "HISTORY_DRIVER_BINDING_MISMATCH")
            self._paths()
            if self._storage_policy is not None:
                self._head_authority._chain.bind_identity(identity, bar_seconds=self._protocol.bar_seconds)
            if self._file_size() == 0:
                _require(not self._universe or self._storage_policy is not None, "HISTORY_STORAGE_POLICY_REQUIRED")
                now = self._now()
                _require(now < self._window.start, "HISTORY_WINDOW_ALREADY_STARTED")
                _require(self._read_head() == GENESIS, "HISTORY_HEAD_NOT_INITIALIZED")
                header = {"identity": asdict(identity)}
                if self._storage_policy is not None:
                    header |= {"history_version": 3, "history_storage": json.loads(policy_bytes(self._storage_policy))}
                self._append("bound", header, now, create=True)
            else:
                self._replay(identity)
            self._identity, self._bound, self._driver_identity = digest(identity), True, identity
            return identity

    def record_slot(self, book, account: AccountObservation, *, trade_symbol: str | None = None,
                    universe: SlotUniverse | None = None, tick_size: Decimal | None = None,
                    positions: tuple[Position, ...] = ()) -> str:
        """Record the next slot from a prefetched original book and the current account observation; returns the
        new journal head. Memory changes only after the durable append, the head advance and its readback. A
        universe window also takes the trade coin, its current tick, the slot's universe inputs and the account
        capture's positions, and `book` is that coin's book or None when it was unavailable; a fixed window takes
        none of them."""
        with _LOCK:
            self._ready()
            if self._universe:
                return self._record_universe(book, account, trade_symbol, universe, tick_size, positions)
            _require(trade_symbol is None and universe is None and tick_size is None and positions == (),
                     "HISTORY_INPUT_REQUIRED")
            sampled_at = self._now()
            anchor = self._anchor(account, self._profile.symbol)
            index = len(self._slots)
            bar, decision, chain, marks = self._derive(index, book, anchor, sampled_at, self._chain, self._marks)
            data = {"index": index, "receipt": _receipt_body(book.receipt), "anchor": _anchor_body(anchor)}
            head = self._append("slot", data, sampled_at)
            self._slots += (_Slot(bar=bar, anchor=anchor, decision=decision, sampled_at=sampled_at, row_sha256=head),)
            self._chain, self._marks = chain, marks
            return head

    def _record_universe(self, book, account, symbol, universe, tick, positions):
        """One lossless v3 row. Storage limits never alter valid market data or chooser inputs."""
        _require(type(symbol) is str and UNIVERSE_MARKET.fullmatch(symbol) is not None
                 and type(universe) is SlotUniverse and type(tick) is Decimal and tick.is_finite() and tick > 0
                 and type(positions) is tuple and all(type(item) is Position for item in positions),
                 "HISTORY_INPUT_REQUIRED")
        sampled_at = self._now()
        anchor = self._anchor(account, symbol)
        index = len(self._slots)
        slot = self._slot_at(index, sampled_at)
        try:
            tick_text = _plain(tick)
            record = self._universe_record(slot, universe)
            holdings = sorted(self._holding(item.symbol, item.units, item.price, item.asof) for item in positions)
            _require(len({item[0] for item in holdings}) == len(holdings), "HISTORY_INPUT_REQUIRED")
        except LiveHistoryError:
            raise
        except Exception:
            raise LiveHistoryError("HISTORY_INPUT_REQUIRED") from None
        _require(self._storage_policy is not None, "HISTORY_STORAGE_POLICY_REQUIRED")
        bar, decision, chain, prices, state, inputs, choice = self._derive_universe(
            index, book, anchor, sampled_at, self._chain, self._prices, self._state, symbol, tick, record)
        data = {"index": index, "trade_symbol": symbol, "tick_size": tick_text,
                "receipt": "unavailable" if book is None else _receipt_body(book.receipt),
                "anchor": _anchor_body(anchor), "holdings": holdings, "universe": record, "decision": choice}
        try:
            _validate_slot_structure(data, index, sampled_at)
        except (ValueError, TypeError, KeyError, OverflowError):
            raise LiveHistoryError("HISTORY_INPUT_REQUIRED") from None
        head = self._append("slot", data, sampled_at)
        self._slots += (_Slot(bar=bar, anchor=anchor, decision=decision, sampled_at=sampled_at, row_sha256=head,
                              universe_sha256=evidence_digest(record)),)
        self._chain, self._prices, self._state = chain, prices, state
        self._inputs = (self._inputs + (inputs,))[-2:]
        self.recorded_allow = frozenset(record["allow"])
        return head

    def decided_symbol(self) -> str | None:
        """The coin the latest recorded decision targets (spec section 7, rule 3): None for cash, for the window-end
        slot (no decision), before any slot and for a fixed window. Before a slot's record_slot it is the decision
        that slot's tick acts on; after it, the one the next tick acts on."""
        with _LOCK:
            if not self._universe or not self._slots or self._slots[-1].decision is None:
                return None
            return self._state.held

    def _provide(self, observation):
        with _LOCK:
            self._ready()
            _require(type(observation) is DecisionInput and _aware(observation.now), "HISTORY_OBSERVATION_REQUIRED")
            self._current(observation.now)
            if self._storage_policy is not None:
                before = self._now()
                _require(observation.now <= before, "HISTORY_TICK_IN_FUTURE")
                self._durable_unchanged()
                after = self._now()
                _require(before <= after, "HISTORY_CLOCK_ROLLBACK")
                self._current(after)
            return self._frame()

    def _verify(self, frame, identity, now):
        with _LOCK:
            self._ready()
            _require(type(identity) is FixedDriverIdentity and digest(identity) == self._identity,
                     "HISTORY_IDENTITY_MISMATCH")
            _require(_aware(now), "HISTORY_OBSERVATION_REQUIRED")
            slot = self._current(now)
            _require(slot.sampled_at <= now, "HISTORY_VERIFIED_AFTER_TICK")
            checked_at = self._now()
            _require(now <= checked_at, "HISTORY_TICK_IN_FUTURE")
            expires = slot.bar.observed_at + EXECUTION_WINDOW
            _require(now < expires and checked_at <= expires, "HISTORY_SLOT_WINDOW_CLOSED")
            try:
                recorded = type(frame) is HistoryFrame and history_frame_digest(frame) == history_frame_digest(self._frame())
            except ValueError:
                recorded = False
            _require(recorded, "HISTORY_FRAME_NOT_RECORDED")
            self._durable_unchanged()
            if self._storage_policy is not None:
                finished_at = self._now()
                _require(checked_at <= finished_at, "HISTORY_CLOCK_ROLLBACK")
                _require(finished_at <= expires, "HISTORY_SLOT_WINDOW_CLOSED")
            return HistoryReceipt(frame_digest=history_frame_digest(frame), driver_identity_digest=self._identity,
                                  source_audit_sha256=slot.row_sha256, verified_at=slot.sampled_at, expires_at=expires)
