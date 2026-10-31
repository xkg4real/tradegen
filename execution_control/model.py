"""Exact, immutable business inputs for execution control; no I/O or credentials.

The opaque account scope names a local profile, never a broker account number.
Digests bind every order field. Instrument validation refuses an invalid order;
it never changes prices, quantities, account selection or supported products.
"""
from __future__ import annotations

from dataclasses import dataclass, fields
from datetime import datetime, timezone
from decimal import Decimal
from fractions import Fraction
import hashlib
import json
import re

_IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}")
_SCOPE = re.compile(r"[A-Za-z][A-Za-z0-9_-]{0,63}")
_HASH = re.compile(r"[0-9a-f]{64}")
_MARKETS = {"upbit": frozenset({"spot"}), "okx": frozenset({"spot"}),
            "kis": frozenset({"krx", "nasd", "nyse", "amex"})}


def _text(value: object, pattern: re.Pattern, name: str) -> None:
    if type(value) is not str or pattern.fullmatch(value) is None:
        raise ValueError("invalid " + name)


def _decimal(value: object, name: str, *, positive: bool = False) -> None:
    if type(value) is not Decimal or not value.is_finite():
        raise ValueError("invalid " + name)
    # Bound serialized size and exact rational operations before formatting.
    parts = value.as_tuple()
    if len(parts.digits) > 128 or abs(parts.exponent) > 128:
        raise ValueError("oversized " + name)
    if value < 0 or (positive and value == 0):
        raise ValueError("invalid " + name)


def decimal_text(value: Decimal) -> str:
    """Canonical plain decimal, with no context-dependent rounding or exponent."""
    _decimal(value, "decimal")
    if value == 0:
        return "0"
    text = format(value, "f")
    return text.rstrip("0").rstrip(".") if "." in text else text


def _identity(venue: object, market: object, symbol: object) -> None:
    if type(venue) is not str or venue not in _MARKETS:
        raise ValueError("unsupported venue")
    if type(market) is not str or market not in _MARKETS[venue]:
        raise ValueError("unsupported market")
    if type(symbol) is not str:
        raise ValueError("invalid symbol")
    pattern = (r"KRW-[A-Z0-9]{1,20}" if venue == "upbit" else
               r"[A-Z0-9]{1,20}-(?:USDT|USDC)" if venue == "okx" else
               r"[0-9]{6}" if market == "krx" else r"[A-Z][A-Z0-9.-]{0,14}")
    if re.fullmatch(pattern, symbol) is None:
        raise ValueError("unsupported symbol")


def _aware(value: object, name: str) -> None:
    if type(value) is not datetime or value.utcoffset() is None:
        raise ValueError("invalid " + name)
    try:
        value.astimezone(timezone.utc)
    except (OverflowError, ValueError):
        raise ValueError("invalid " + name) from None


@dataclass(frozen=True, kw_only=True)
class Order:
    client_id: str
    account_scope: str
    venue: str
    market: str
    symbol: str
    side: str
    quantity: Decimal
    limit_price: Decimal
    quote_krw: Decimal
    time_in_force: str = "gtc"

    def __post_init__(self) -> None:
        _order_fields(self)


def _order_fields(order: Order) -> None:
    _text(order.client_id, _IDENTIFIER, "client_id")
    _text(order.account_scope, _SCOPE, "account_scope")
    _identity(order.venue, order.market, order.symbol)
    if type(order.side) is not str or order.side not in ("buy", "sell"):
        raise ValueError("unsupported side")
    expected_tif = "day" if order.venue == "kis" else "gtc"
    if type(order.time_in_force) is not str or order.time_in_force != expected_tif:
        raise ValueError("unsupported time_in_force")
    for name in ("quantity", "limit_price", "quote_krw"):
        _decimal(getattr(order, name), name, positive=True)
    if (order.venue == "upbit" or order.market == "krx") and order.quote_krw != 1:
        raise ValueError("invalid KRW quote conversion")
    if order.venue == "kis" and Fraction(order.quantity).denominator != 1:
        raise ValueError("fractional shares unsupported")


@dataclass(frozen=True, kw_only=True)
class InstrumentRules:
    venue: str
    market: str
    symbol: str
    lot_size: Decimal
    tick_size: Decimal
    min_quantity: Decimal
    min_notional_krw: Decimal
    fee_fraction: Decimal
    asof: datetime
    source_digest: str

    def __post_init__(self) -> None:
        _rule_fields(self)


def _rule_fields(rules: InstrumentRules) -> None:
    _identity(rules.venue, rules.market, rules.symbol)
    for name in ("lot_size", "tick_size"):
        _decimal(getattr(rules, name), name, positive=True)
    for name in ("min_quantity", "min_notional_krw", "fee_fraction"):
        _decimal(getattr(rules, name), name)
    if rules.fee_fraction > 1:
        raise ValueError("invalid fee_fraction")
    _aware(rules.asof, "asof")
    _text(rules.source_digest, _HASH, "source_digest")


def order_body(order: Order) -> dict:
    if type(order) is not Order:
        raise ValueError("invalid order type")
    _order_fields(order)  # Recheck even a frozen object deliberately altered by a caller.
    return {field.name: decimal_text(value) if type(value := getattr(order, field.name)) is Decimal else value
            for field in fields(Order)}


def _digest(body: dict) -> str:
    raw = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)
    return hashlib.sha256(raw.encode("ascii")).hexdigest()


def order_digest(order: Order) -> str:
    return _digest(order_body(order))


def rules_digest(rules: InstrumentRules) -> str:
    if type(rules) is not InstrumentRules:
        raise ValueError("invalid instrument rules type")
    _rule_fields(rules)
    body = {}
    for field in fields(InstrumentRules):
        value = getattr(rules, field.name)
        body[field.name] = (decimal_text(value) if type(value) is Decimal else
                            value.astimezone(timezone.utc).isoformat(timespec="microseconds")
                            if type(value) is datetime else value)
    return _digest(body)


def validate_order(order: Order, rules: InstrumentRules) -> None:
    if type(order) is not Order or type(rules) is not InstrumentRules:
        raise ValueError("invalid execution input type")
    _order_fields(order)
    _rule_fields(rules)
    if (order.venue, order.market, order.symbol) != (rules.venue, rules.market, rules.symbol):
        raise ValueError("instrument rules mismatch")
    # Fractions avoid silently rounding Decimal modulo/division under ambient contexts.
    if (Fraction(order.quantity) / Fraction(rules.lot_size)).denominator != 1:
        raise ValueError("quantity not on lot")
    if (Fraction(order.limit_price) / Fraction(rules.tick_size)).denominator != 1:
        raise ValueError("price not on tick")
    if order.quantity < rules.min_quantity:
        raise ValueError("quantity below minimum")
    notional = Fraction(order.quantity) * Fraction(order.limit_price) * Fraction(order.quote_krw)
    if notional < Fraction(rules.min_notional_krw):
        raise ValueError("notional below minimum")
