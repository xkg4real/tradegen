"""Read-only OQ12 ownership assessment for one authenticated Upbit KRW account.

The caller pins the venue evidence and the existing complete control journal in
one startup inspection. A personal-order source, if present, must authenticate
personal origin independently of this snapshot. The supplied Ed25519 reader
accepts an independently provisioned review key; neither this reader nor a
successful classification creates any approval, session or order authority.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from decimal import Decimal, DecimalException, Inexact, localcontext
from itertools import groupby
import hashlib

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from execution_accounts.model import AccountEvidence, content_digest
from execution_accounts.provider import EvidenceError, _account, _id, _require, _sha
from execution_control.capability import digest
from execution_control.controller import _fill_key, _fold
from execution_control.store import GENESIS, MAX_EVENTS, SCHEMA

_ZERO = Decimal(0)
_ACTIVE = frozenset(("open", "partial"))
_STATUS = {"open": "ACKNOWLEDGED", "partial": "PARTIAL", "filled": "FILLED",
           "canceled": "CANCELED", "rejected": "REJECTED"}
_DOMAIN = b"TRADEGEN personal order origin v1\x00"


def personal_order_terms(account_scope, order):
    """Stable terms survive partial fills. Bind the scope, venue and actual order ID."""
    return content_digest(("upbit", account_scope, order.order_id, order.client_id,
                           order.market, order.symbol, order.side, order.quote_currency,
                           order.quantity.as_integer_ratio(), order.limit_price.as_integer_ratio()))


@dataclass(frozen=True, kw_only=True)
class PersonalOrderRecord:
    account_scope: str
    order_id: str
    terms_sha256: str
    source_sha256: str

    def message(self):
        return _DOMAIN + content_digest(self).encode("ascii")


class SignedPersonalOrders:
    """Offline (record, detached signature, original evidence bytes) triples.

    The review key is provisioned outside the archive. A valid reviewer attests
    the original source establishes personal origin; a venue ID is not proof.
    """

    def __init__(self, trusted_public_key: bytes, signed_records: tuple):
        self._key = Ed25519PublicKey.from_public_bytes(trusted_public_key)
        self._records = tuple(signed_records)

    def read_personal_orders(self, account_scope, order_ids):
        records = []
        wanted = set(order_ids)
        for record, signature, original in self._records:
            _require(type(record) is PersonalOrderRecord, "OWNERSHIP_REVIEW_INVALID")
            if record.account_scope == account_scope and record.order_id in wanted:
                try:
                    self._key.verify(signature, record.message())
                except (TypeError, ValueError, InvalidSignature):
                    raise EvidenceError("OWNERSHIP_REVIEW_INVALID") from None
                records.append((record, original))
        return tuple(records)


@dataclass(frozen=True, kw_only=True)
class OwnedPosition:
    symbol: str
    app_units: Decimal
    personal_units: Decimal
    free_app_units: Decimal


@dataclass(frozen=True, kw_only=True)
class OwnershipAssessment:
    origin_ready: bool
    reason: str
    unknown_order_count: int = 0
    app_open_count: int = 0
    personal_open_count: int = 0
    positions: tuple[OwnedPosition, ...] = field(default=(), repr=False)
    app_open_order_ids: tuple[str, ...] = field(default=(), repr=False)
    personal_open_order_ids: tuple[str, ...] = field(default=(), repr=False)
    unknown_order_ids: tuple[str, ...] = field(default=(), repr=False)
    unreserved_cash_krw: Decimal | None = field(default=None, repr=False)
    personal_reserved_cash_krw: Decimal | None = field(default=None, repr=False)
    whole_account_equity_krw: Decimal | None = field(default=None, repr=False)

    @property
    def execution_ready(self):
        return False


def _scoped_journal(events, head, scope, now):
    _sha(head)
    _require(type(events) is tuple and len(events) <= MAX_EVENTS, "OWNERSHIP_JOURNAL_INVALID")
    previous = GENESIS
    for sequence, row in enumerate(events, 1):
        _require(type(row) is dict and set(row) == {"schema", "seq", "prev_sha256", "row_sha256",
                 "kind", "data", "utc"} and type(row["seq"]) is int and row["seq"] == sequence
                 and type(row["schema"]) is int and row["schema"] == SCHEMA
                 and row["prev_sha256"] == previous, "OWNERSHIP_JOURNAL_INVALID")
        previous = digest({k: v for k, v in row.items() if k != "row_sha256"})
        _require(previous == row["row_sha256"], "OWNERSHIP_JOURNAL_INVALID")
    _require(previous == head, "OWNERSHIP_JOURNAL_HEAD_CHANGED")
    orders, _, _, last = _fold(events)
    _require(last is None or last <= now, "OWNERSHIP_JOURNAL_FUTURE")
    return {client: rec for client, rec in orders.items()
            if (rec["order"].venue, rec["order"].account_scope) == ("upbit", scope)}


def _app_orders(orders, by_id, fills):
    """Tie both IDs, terms, status and the exact journaled fill evidence to venue rows."""
    by_client = {row.client_id: row for row in by_id.values() if row.client_id}
    matched = set()
    for client, rec in orders.items():
        row = by_client.get(client)
        venue_id = rec["venue_order_id"]
        status = rec["status"]
        if row is None and not venue_id and status in ("EXPIRED", "CANCELLED_LOCAL", "REJECTED"):
            continue
        _require(row is not None and venue_id == row.order_id and _STATUS[row.status] == status
                 and not rec["cancel_pending"], "OWNERSHIP_JOURNAL_ORDER_UNRESOLVED")
        order = rec["order"]
        _require((row.market, row.symbol, row.side, row.quantity, row.limit_price)
                 == (order.market, order.symbol, order.side, order.quantity, order.limit_price)
                 and row.filled_quantity == rec["filled"], "OWNERSHIP_ORDER_CONFLICT")
        _require({_fill_key(f): digest(f) for f in fills.get(venue_id, ())} == rec["fill_hashes"],
                 "OWNERSHIP_FILL_CONFLICT")
        matched.add(venue_id)
    return matched


def _personal_orders(source, account, by_id):
    if source is None:
        return set()
    try:
        records = source.read_personal_orders(account.account_scope, tuple(sorted(by_id)))
    except EvidenceError:
        raise
    except Exception:
        raise EvidenceError("OWNERSHIP_REVIEW_UNAVAILABLE") from None
    _require(type(records) is tuple and len(records) <= len(by_id), "OWNERSHIP_REVIEW_INVALID")
    personal = set()
    for item in records:
        _require(type(item) is tuple and len(item) == 2, "OWNERSHIP_REVIEW_INVALID")
        record, original = item
        _require(type(record) is PersonalOrderRecord and record.account_scope == account.account_scope
                 and record.order_id in by_id and record.order_id not in personal,
                 "OWNERSHIP_REVIEW_INVALID")
        _id(record.order_id)
        _sha(record.source_sha256)
        _require(type(original) is bytes and bool(original)
                 and hashlib.sha256(original).hexdigest() == record.source_sha256,
                 "OWNERSHIP_REVIEW_INVALID")
        _require(record.terms_sha256 == personal_order_terms(account.account_scope, by_id[record.order_id]),
                 "OWNERSHIP_REVIEW_INVALID")
        personal.add(record.order_id)
    return personal


def _positions(account, fills, by_id, app):
    """Replay attributed quantities in exchange time, refusing unproved lock/order history."""
    app_units = defaultdict(Decimal)
    locked_app = defaultdict(Decimal)
    locked_total = defaultdict(Decimal)
    potential_app_sells = set()
    for row in by_id.values():
        if row.side != "sell":
            continue
        if row.order_id in app and row.status != "rejected":
            potential_app_sells.add(row.symbol)
        if row.status in _ACTIVE:
            locked_total[row.symbol] += row.remaining_quantity
            if row.order_id in app:
                locked_app[row.symbol] += row.remaining_quantity
    ordered = sorted(fills, key=lambda f: (f.symbol, f.executed_at))
    for (symbol, _), group in groupby(ordered, key=lambda f: (f.symbol, f.executed_at)):
        bucket = tuple(group)
        tags = {(f.order_id in app, f.side) for f in bucket}
        _require(not ((False, "sell") in tags and any(is_app for is_app, _ in tags))
                 and not ({(True, "buy"), (True, "sell")} <= tags),
                 "OWNERSHIP_FILL_SEQUENCE_UNRESOLVED")
        for f in bucket:
            base_fee = f.fee_amount if f.fee_currency == f.base_currency else _ZERO
            if f.side == "buy":
                if f.order_id in app:
                    app_units[symbol] += f.quantity - base_fee
                continue
            quantity = f.quantity + base_fee
            if f.order_id in app:
                _require(quantity <= app_units[symbol], "OWNERSHIP_APP_SELL_EXCEEDS_UNITS")
                app_units[symbol] -= quantity
            elif app_units[symbol]:
                # The endpoint has no per-order lock/unlock timeline. Do not guess
                # the app units available at an earlier hand sale when this matters.
                _require(symbol not in potential_app_sells, "OWNERSHIP_LOCK_HISTORY_REQUIRED")
                app_units[symbol] -= min(quantity, app_units[symbol])
    balances = {p.symbol: p.units for p in account.positions}
    result = []
    for symbol in sorted(set(balances) | set(app_units)):
        units, owned = balances.get(symbol, _ZERO), app_units[symbol]
        _require(locked_app[symbol] <= owned <= units and locked_total[symbol] <= units,
                 "OWNERSHIP_POSITION_CONFLICT")
        result.append(OwnedPosition(symbol=symbol, app_units=owned, personal_units=units-owned,
                                    free_app_units=min(owned-locked_app[symbol], units-locked_total[symbol])))
    return tuple(result)


def _assess(account, journal_events, now, account_sha256, journal_head, personal_source):
    _require(type(account) is AccountEvidence and account.venue == "upbit"
             and account.execution_quote == "KRW", "OWNERSHIP_SCOPE_UNSUPPORTED")
    _sha(account_sha256)
    _require(content_digest(account) == account_sha256, "OWNERSHIP_ACCOUNT_CHANGED")
    evidence = _account(account, now)
    # Upbit's collector reconciles balance + locked to total/settled KRW.
    # A different convention cannot be safely combined with the same deduction.
    _require(all(b.settled == b.total for b in account.balances), "OWNERSHIP_CASH_BASIS_UNCONFIRMED")
    orders = _scoped_journal(journal_events, journal_head, account.account_scope, now)
    by_id = {row.order_id: row for p in account.pages if p.kind == "orders" for row in p.rows}
    fills = defaultdict(list)
    for fill in evidence["fills"]:
        fills[fill.order_id].append(fill)
    _require(set(fills) <= set(by_id), "OWNERSHIP_FILL_WITHOUT_ORDER")
    app = _app_orders(orders, by_id, fills)
    personal = _personal_orders(personal_source, account, by_id)
    _require(not app & personal, "OWNERSHIP_ORDER_CONFLICT")
    unknown = tuple(sorted(by_id.keys() - app - personal))
    if unknown:
        return OwnershipAssessment(origin_ready=False, reason="OWNERSHIP_ORDER_ORIGIN_UNKNOWN",
                                   unknown_order_count=len(unknown), unknown_order_ids=unknown)
    positions = _positions(account, evidence["fills"], by_id, app)
    app_open = tuple(sorted(i for i in app if by_id[i].status in _ACTIVE))
    personal_open = tuple(sorted(i for i in personal if by_id[i].status in _ACTIVE))
    personal_cash = sum((by_id[i].reserved_cash for i in personal_open), _ZERO)
    all_reserved = personal_cash + sum((by_id[i].reserved_cash for i in app_open), _ZERO)
    return OwnershipAssessment(origin_ready=True, reason="OWNERSHIP_RECONCILED",
        app_open_count=len(app_open), personal_open_count=len(personal_open), positions=positions,
        app_open_order_ids=app_open, personal_open_order_ids=personal_open,
        unreserved_cash_krw=evidence["available"]-all_reserved,
        personal_reserved_cash_krw=personal_cash, whole_account_equity_krw=evidence["equity"])


def reconcile_first_order(account, journal_events, *, now, account_sha256, journal_head, personal_source=None):
    """Assess OQ12 for the retained account and physical journal at this inspection.

    Gross settled Upbit KRW includes venue order locks; deduct exactly once.
    Unreserved KRW is only an account ceiling, subject to separately approved
    capital/risk limits. The optional trusted reader's read_personal_orders(scope,
    ids) authenticates positive origin and returns (PersonalOrderRecord, original
    evidence bytes) pairs. Supply this dependency independently of account input.
    A broker-authenticated, audited origin source can replace a signed review.
    Results are diagnostic and convey no sell/cancel right.
    """
    try:
        with localcontext() as numeric:
            numeric.prec = 512
            numeric.traps[Inexact] = True
            return _assess(account, journal_events, now, account_sha256, journal_head, personal_source)
    except EvidenceError as exc:
        return OwnershipAssessment(origin_ready=False, reason=exc.code)
    except (ValueError, TypeError, AttributeError, KeyError, DecimalException, OverflowError, RecursionError):
        return OwnershipAssessment(origin_ready=False, reason="OWNERSHIP_EVIDENCE_INVALID")
