"""Current Upbit terms from two fixed read-only E1 requests.

No read occurs at import or construction. The account identity and terms absent
from the API are explicit reviewed inputs, never inferred from a receipt hash.
Only this process's reader can issue an observation; parsing saved JSON is not
fresh authenticated evidence. Production callers run this on the owner's PC.
"""
from __future__ import annotations

from contextlib import ExitStack
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import hashlib
import json
import re
from typing import Callable
from threading import RLock

from execution.transport import Answer, inquiry_clock
from execution.upbit_inquiry import current_terms, TERMS_CHANCE_PATH, TERMS_INSTRUMENTS_PATH
from execution_accounts.collector import SourceReceipt
from execution_control.model import InstrumentRules, decimal_text, rules_digest
from execution_network.route import ManagedRoute, managed_route

_SHA = re.compile(r"[0-9a-f]{64}")
_SCOPE = re.compile(r"[A-Za-z][A-Za-z0-9_-]{0,63}")
_SYMBOL = re.compile(r"KRW-[A-Z][A-Z0-9]{0,11}")
_MAX_AGE = timedelta(minutes=5)
_MAX_WINDOW = timedelta(seconds=30)
_MAX_BODY = 131072
_MAX_ISSUED = 4096
_ISSUED = {}
_OBSERVED_RULES = {}
_AUTHORITIES = set()
_LOCK = RLock()
_PUBLIC_SCOPE = "public-upbit-terms"


class TermsError(ValueError):
    """Fixed codes only; provider exceptions and account bodies stay private."""


def _require(ok, code):
    if not ok:
        raise TermsError(code)


def _time(value):
    _require(type(value) is datetime and value.utcoffset() is not None,
             "TERMS_AWARE_TIME_REQUIRED")
    try:
        return value.astimezone(timezone.utc)
    except (ValueError, OverflowError):
        raise TermsError("TERMS_TIME_INVALID") from None


def _sha(value):
    _require(type(value) is str and _SHA.fullmatch(value) is not None,
             "TERMS_SOURCE_DIGEST_REQUIRED")
    return value


def _number(value, *, positive=False):
    _require(type(value) in (str, int, Decimal), "TERMS_EXACT_NUMBER_REQUIRED")
    try:
        result = Decimal(value)
    except (ValueError, ArithmeticError):
        raise TermsError("TERMS_NUMBER_INVALID") from None
    _require(result.is_finite() and len(result.as_tuple().digits) <= 60
             and -40 <= result.as_tuple().exponent <= 40,
             "TERMS_NUMBER_INVALID")
    _require(result > 0 if positive else result >= 0, "TERMS_NUMBER_INVALID")
    return result


def _digest(body):
    return hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":"),
        ensure_ascii=True, allow_nan=False).encode("ascii")).hexdigest()


@dataclass(frozen=True, kw_only=True)
class TermsAuthority:
    """Reviewed scope and API omissions; this is configuration, not a signature.

    The owner/deployment review must establish identity_binding_sha256 against
    the actual read-only account key. API bodies do not prove that relationship.
    provenance_sha256 pins the reviewed lot/minimum/maximum policy document.
    Its digest is stable across observations and belongs in InstrumentRules.
    """
    account_scope: str
    symbol: str
    lot_size: Decimal
    min_quantity: Decimal
    maximum_notional_krw: Decimal
    provenance_sha256: str
    identity_binding_sha256: str
    valid_from: datetime
    valid_until: datetime


def authority_digest(authority):
    _require(type(authority) is TermsAuthority, "TERMS_AUTHORITY_REQUIRED")
    _require(type(authority.account_scope) is str and
             _SCOPE.fullmatch(authority.account_scope) is not None, "TERMS_SCOPE_INVALID")
    _require(type(authority.symbol) is str and _SYMBOL.fullmatch(authority.symbol) is not None
             and authority.symbol != "KRW-KRW", "TERMS_KRW_SYMBOL_REQUIRED")
    for name in ("lot_size", "min_quantity", "maximum_notional_krw"):
        value = getattr(authority, name)
        _require(type(value) is Decimal, "TERMS_EXACT_NUMBER_REQUIRED")
        _number(value, positive=name != "min_quantity")
    start, end = _time(authority.valid_from), _time(authority.valid_until)
    _require(start < end, "TERMS_AUTHORITY_WINDOW_INVALID")
    return _digest({"version": "upbit-terms-authority-v1", "venue": "upbit", "market": "spot",
        "account_scope": authority.account_scope, "symbol": authority.symbol,
        "lot_size": decimal_text(authority.lot_size), "min_quantity": decimal_text(authority.min_quantity),
        "maximum_notional_krw": decimal_text(authority.maximum_notional_krw),
        "provenance_sha256": _sha(authority.provenance_sha256),
        "identity_binding_sha256": _sha(authority.identity_binding_sha256),
        "valid_from": start.isoformat(timespec="microseconds"),
        "valid_until": end.isoformat(timespec="microseconds")})


@dataclass(frozen=True, kw_only=True)
class TermsObservation:
    rules: InstrumentRules
    authority: TermsAuthority = field(repr=False)
    requested_at: datetime
    checked_at: datetime
    chance_receipt: SourceReceipt = field(repr=False)
    instruments_receipt: SourceReceipt = field(repr=False)
    evidence_digest: str


def _receipt(receipt, *, path, params, scope, before, checked):
    _require(type(receipt) is SourceReceipt and receipt.path == path and
             type(receipt.params) is tuple and receipt.params == params and
             receipt.account_scope == scope, "TERMS_RECEIPT_SCOPE_MISMATCH")
    received, server = _time(receipt.received_at), _time(receipt.server_time)
    _require(before <= received <= checked, "TERMS_RECEIPT_OUTSIDE_REQUEST")
    _require(abs(received-server) <= timedelta(seconds=60), "TERMS_SERVER_CLOCK_MISMATCH")
    _require(type(receipt.raw_body) is bytes and 0 < len(receipt.raw_body) <= _MAX_BODY,
             "TERMS_BODY_EMPTY_OR_OVERSIZED")
    try:
        return receipt.decode()
    except (ValueError, TypeError, ArithmeticError):
        raise TermsError("TERMS_RECEIPT_INVALID") from None


def parse_term_receipts(*, authority, chance_receipt, instruments_receipt, requested_at,
                        checked_at, now):
    """Pure decoding; its result is deliberately NOT an issued observation."""
    source = authority_digest(authority)
    before, checked, current = _time(requested_at), _time(checked_at), _time(now)
    _require(timedelta(0) <= checked-before <= _MAX_WINDOW,
             "TERMS_REQUEST_WINDOW_INVALID")
    _require(authority.valid_from <= before <= checked <= current < authority.valid_until,
             "TERMS_AUTHORITY_EXPIRED_OR_FUTURE")
    symbol = authority.symbol
    chance = _receipt(chance_receipt, path=TERMS_CHANCE_PATH, params=(("market", symbol),),
        scope=authority.account_scope, before=before, checked=checked)
    instruments = _receipt(instruments_receipt, path=TERMS_INSTRUMENTS_PATH,
        params=(("markets", symbol),), scope=_PUBLIC_SCOPE, before=before, checked=checked)
    _require(chance_receipt.received_at <= instruments_receipt.received_at,
             "TERMS_RECEIPTS_OUT_OF_ORDER")
    asof = min(chance_receipt.received_at, instruments_receipt.received_at)
    _require(timedelta(0) <= current-asof <= _MAX_AGE, "TERMS_STALE_OR_FUTURE")
    _require(type(chance) is dict and type(chance.get("market")) is dict,
             "TERMS_MARKET_RECORD_REQUIRED")
    market = chance["market"]
    _require(market.get("id") == symbol and market.get("state") == "active",
             "TERMS_MARKET_INACTIVE_OR_MISMATCHED")
    for field_name, required in (("order_sides", ("bid", "ask")),
                                 ("bid_types", ("limit",)), ("ask_types", ("limit",))):
        items = market.get(field_name)
        _require(type(items) is list and all(type(v) is str for v in items)
                 and all(v in items for v in required), "TERMS_LIMIT_ORDERS_UNSUPPORTED")
    bid, ask = market.get("bid"), market.get("ask")
    _require(type(bid) is dict and type(ask) is dict and bid.get("currency") == "KRW"
             and ask.get("currency") == symbol.split("-", 1)[1], "TERMS_CURRENCY_MISMATCH")
    minimum = _number(bid.get("min_total"), positive=True)
    _require(_number(ask.get("min_total"), positive=True) == minimum,
             "TERMS_ASYMMETRIC_MINIMUM_UNSUPPORTED")
    maximum = _number(market.get("max_total"), positive=True)
    _require(maximum >= minimum and maximum == authority.maximum_notional_krw,
             "TERMS_MAXIMUM_CHANGED")
    fees = tuple(_number(chance.get(name)) for name in
                 ("bid_fee", "ask_fee", "maker_bid_fee", "maker_ask_fee"))
    _require(all(v == fees[0] for v in fees) and fees[0] <= 1,
             "TERMS_ASYMMETRIC_FEE_UNSUPPORTED")
    _require(type(instruments) is list and len(instruments) == 1
             and type(instruments[0]) is dict and instruments[0].get("market") == symbol,
             "TERMS_SINGLE_INSTRUMENT_REQUIRED")
    instrument = instruments[0]
    _require(instrument.get("quote_currency") == "KRW", "TERMS_CURRENCY_MISMATCH")
    levels = instrument.get("supported_levels")
    _require(type(levels) is list and 1 <= len(levels) <= 64
             and all(type(v) is str for v in levels) and "0" in levels,
             "TERMS_NATIVE_BOOK_UNSUPPORTED")
    tick = _number(instrument.get("tick_size"), positive=True)
    rules = InstrumentRules(venue="upbit", market="spot", symbol=symbol,
        lot_size=authority.lot_size, tick_size=tick, min_quantity=authority.min_quantity,
        min_notional_krw=minimum, fee_fraction=fees[0], asof=asof, source_digest=source)
    evidence = _digest({"version": "upbit-current-terms-v1", "rules_digest": rules_digest(rules),
        "authority_digest": source, "requested_at": before.isoformat(timespec="microseconds"),
        "checked_at": checked.isoformat(timespec="microseconds"),
        "receipts": [{"sha256": r.sha256,
                      "received_at": _time(r.received_at).isoformat(timespec="microseconds"),
                      "server_time": _time(r.server_time).isoformat(timespec="microseconds")}
                     for r in (chance_receipt, instruments_receipt)]})
    return TermsObservation(rules=rules, authority=authority, requested_at=before,
        checked_at=checked, chance_receipt=chance_receipt, instruments_receipt=instruments_receipt,
        evidence_digest=evidence)


def validate_issued_observation(observation, *, now):
    _require(type(observation) is TermsObservation, "TERMS_OBSERVATION_REQUIRED")
    saved = _ISSUED.get(id(observation))
    _require(saved is not None and saved[0] is observation,
             "TERMS_OBSERVATION_NOT_ISSUED")
    parsed = parse_term_receipts(authority=observation.authority,
        chance_receipt=observation.chance_receipt, instruments_receipt=observation.instruments_receipt,
        requested_at=observation.requested_at, checked_at=observation.checked_at, now=now)
    _require(parsed.evidence_digest == observation.evidence_digest == saved[1]
             and rules_digest(parsed.rules) == rules_digest(observation.rules),
             "TERMS_OBSERVATION_CHANGED")
    return parsed


def observation_for_rules(rules, *, account_scope, now):
    """Resolve initial or renewed issued rules; known sources cannot be restamped.

    None denotes a legacy source not issued by this reader, not an approval.
    Existing controller and owner rules remain mandatory for that legacy path.
    """
    fingerprint = rules_digest(rules)
    with _LOCK:
        observation = _OBSERVED_RULES.get((account_scope, fingerprint))
        known = rules.source_digest in _AUTHORITIES
    if observation is None:
        _require(not known, "TERMS_UNISSUED_RULE_SNAPSHOT")
        return None
    return validate_issued_observation(observation, now=now)


@dataclass(frozen=True, kw_only=True)
class E1UpbitTermsSource:
    authority: TermsAuthority = field(repr=False)
    clock: Callable = field(repr=False)
    route: ManagedRoute | None = None

    def __post_init__(self):
        source = authority_digest(self.authority)
        _require(callable(self.clock), "TERMS_CLOCK_REQUIRED")
        _require(self.route is None or type(self.route) is ManagedRoute, "TERMS_ROUTE_INVALID")
        with _LOCK:
            _AUTHORITIES.add(source)

    def read(self):
        """Issue one bounded observation; no arbitrary path or method parameters."""
        authority_digest(self.authority)
        _require(callable(self.clock), "TERMS_CLOCK_REQUIRED")
        _require(len(_ISSUED) < _MAX_ISSUED, "TERMS_PROCESS_CAPACITY_REACHED")
        symbol = self.authority.symbol
        before = _time(self.clock())
        _require(self.authority.valid_from <= before < self.authority.valid_until,
                 "TERMS_AUTHORITY_EXPIRED_OR_FUTURE")
        try:
            with ExitStack() as stack:
                stack.enter_context(inquiry_clock(self.clock))
                if self.route is not None:
                    stack.enter_context(managed_route(self.route))
                chance, instruments = current_terms(symbol)
            checked = _time(self.clock())
        except Exception:
            raise TermsError("TERMS_INQUIRY_FAILED") from None
        for answer in (chance, instruments):
            _require(type(answer) is Answer and answer.server_utc is not None,
                     "TERMS_SERVER_TIME_REQUIRED")
        chance_receipt = SourceReceipt(path=TERMS_CHANCE_PATH, params=(("market", symbol),),
            account_scope=self.authority.account_scope, received_at=chance.received_utc,
            server_time=chance.server_utc, raw_body=chance.raw_body, sha256=chance.sha256)
        instruments_receipt = SourceReceipt(path=TERMS_INSTRUMENTS_PATH, params=(("markets", symbol),),
            account_scope=_PUBLIC_SCOPE, received_at=instruments.received_utc,
            server_time=instruments.server_utc, raw_body=instruments.raw_body, sha256=instruments.sha256)
        observation = parse_term_receipts(authority=self.authority, chance_receipt=chance_receipt,
            instruments_receipt=instruments_receipt, requested_at=before, checked_at=checked, now=checked)
        with _LOCK:
            _require(len(_ISSUED) < _MAX_ISSUED, "TERMS_PROCESS_CAPACITY_REACHED")
            _ISSUED[id(observation)] = (observation, observation.evidence_digest)
            _OBSERVED_RULES[(self.authority.account_scope, rules_digest(observation.rules))] = observation
            _AUTHORITIES.add(observation.rules.source_digest)
        return observation
