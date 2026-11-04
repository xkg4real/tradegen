"""Lossless read-only source receipts and explicit evidence obligations.

Digests bind bytes; they do not establish account identity, history retention or
an atomic exchange snapshot. The reviewed external evidence below supplies
those obligations. Nothing in this module signs, persists or activates orders.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
import re

from execution_accounts.provider import EvidenceError

_SHA = re.compile(r"[0-9a-f]{64}")
_ID = re.compile(r"[A-Za-z0-9_.:/-]{1,128}")
MAX_BODY_BYTES = 8 * 1024 * 1024


def require(condition, code):
    if not condition:
        raise EvidenceError(code)


def identifier(value):
    require(type(value) is str and _ID.fullmatch(value) is not None, "COLLECTOR_ID_INVALID")
    return value


def digest(value):
    require(type(value) is str and _SHA.fullmatch(value) is not None, "COLLECTOR_SOURCE_DIGEST_REQUIRED")
    return value


def instant(value):
    require(type(value) is datetime and value.utcoffset() is not None, "COLLECTOR_AWARE_TIME_REQUIRED")
    return value.astimezone(timezone.utc)


def when(value):
    require(type(value) is str and len(value) <= 40, "COLLECTOR_TIME_INVALID")
    try:
        result = datetime.fromisoformat(value)
    except ValueError:
        raise EvidenceError("COLLECTOR_TIME_INVALID") from None
    return instant(result)


def number(value, *, positive=False, json_number=False):
    require(type(value) is str or (json_number and type(value) in (int, Decimal)),
            "COLLECTOR_DECIMAL_STRING_REQUIRED")
    try:
        result = Decimal(value)
    except (ValueError, ArithmeticError):
        raise EvidenceError("COLLECTOR_DECIMAL_INVALID") from None
    require(result.is_finite() and len(result.as_tuple().digits) <= 60
            and -40 <= result.as_tuple().exponent <= 40, "COLLECTOR_DECIMAL_RANGE")
    require(result > 0 if positive else result >= 0, "COLLECTOR_AMOUNT_INVALID")
    return result


def _object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "COLLECTOR_DUPLICATE_JSON_KEY")
        result[key] = value
    return result


def _constant(_value):
    raise EvidenceError("COLLECTOR_JSON_NONFINITE")


@dataclass(frozen=True, kw_only=True)
class SourceReceipt:
    path: str
    params: tuple[tuple[str, str], ...]
    account_scope: str
    received_at: datetime
    server_time: datetime
    raw_body: bytes = field(repr=False)
    sha256: str

    def decode(self):
        identifier(self.account_scope); instant(self.received_at); instant(self.server_time)
        digest(self.sha256)
        require(type(self.raw_body) is bytes and 0 < len(self.raw_body) <= MAX_BODY_BYTES,
                "COLLECTOR_RAW_BYTES_REQUIRED")
        require(hashlib.sha256(self.raw_body).hexdigest() == self.sha256, "COLLECTOR_RECEIPT_DIGEST_MISMATCH")
        try:
            return json.loads(self.raw_body.decode("utf-8"), parse_float=Decimal,
                              object_pairs_hook=_object, parse_constant=_constant)
        except (UnicodeError, ValueError, RecursionError) as exc:
            if isinstance(exc, EvidenceError):
                raise
            raise EvidenceError("COLLECTOR_JSON_INVALID") from None


@dataclass(frozen=True, kw_only=True)
class OpeningAnchor:
    account_scope: str
    origin: datetime
    cash_krw: Decimal
    source_sha256: str
    # Required reviewed statement: holdings AND pending/part-filled orders were empty.
    inventory_and_open_orders: str


@dataclass(frozen=True, kw_only=True)
class CoverageEvidence:
    """A source/operator-reviewed document, not an exchange API's boolean claim.

    ``quiescent_from``/``quiescent_until`` cover the entire collection. This is
    a pre-established exclusive-account fence: no manual/API matching activity,
    transfers, rewards or balance changes. Repeated pages are additional checks,
    never a substitute for this external consistency evidence.
    """
    account_scope: str
    source_sha256: str
    history_from: datetime
    history_through: datetime
    quiescent_from: datetime
    quiescent_until: datetime
    identity_binding: str
    history_retention: str
    transfer_scope: str
    account_mode: str


@dataclass(frozen=True, kw_only=True)
class TradeFeeEvidence:
    order_id: str
    fill_id: str
    fee_krw: Decimal
    source_sha256: str
