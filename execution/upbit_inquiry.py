"""Upbit read-only inquiry (E1 spec 5 and 6; plan C7, C10): the frozen allowlist and the Upbit snapshot of one poll,
for the owner's main pocket. Transport signs every call but the public ticker with an HS512 JWT whose query hash
covers the exact query sent. The wallet status stays on the allowlist but nothing reads it (E22)."""
from __future__ import annotations

import math
from datetime import datetime

from core.compliance import model
from execution.snapshot import Address, FieldError, Holding, Move, Order, Snapshot, failed
from execution.transport import AuthError, InquiryError, InquiryRefused, KeyMissing, request

ENDPOINTS = frozenset({
    ("GET", "/v1/accounts"), ("GET", "/v1/orders/open"), ("GET", "/v1/orders/closed"), ("GET", "/v1/withdraws"),
    ("GET", "/v1/withdraws/coin_addresses"), ("GET", "/v1/deposits"), ("GET", "/v1/api_keys"),
    ("GET", "/v1/status/wallet"), ("GET", "/v1/ticker"),
})
PUBLIC = frozenset({"/v1/ticker"})

_ACCOUNTS = "/v1/accounts"
_OPEN = "/v1/orders/open"
_CLOSED = "/v1/orders/closed"
_WITHDRAWS = "/v1/withdraws"
_ADDRESSES = "/v1/withdraws/coin_addresses"
_DEPOSITS = "/v1/deposits"
_KEYS = "/v1/api_keys"
_TICKER = "/v1/ticker"
_SIGNED = ((_ACCOUNTS, None), (_OPEN, [("states[]", "wait"), ("states[]", "watch"), ("limit", "100")]),
           (_CLOSED, [("states[]", "done"), ("states[]", "cancel"), ("limit", "1000")]),   # no time: the last 7 days
           (_WITHDRAWS, [("limit", "100")]), (_ADDRESSES, None), (_DEPOSITS, [("limit", "100")]), (_KEYS, None))
_CONTAINED = (KeyMissing, InquiryRefused, InquiryError, LookupError, ValueError, TypeError, AttributeError,
              ArithmeticError)                      # E38: the venue's own errors (AuthError and FieldError included)


def snapshot(now: datetime) -> Snapshot:
    """The Upbit snapshot of the poll at `now` (C10). A venue error gives a failed snapshot whose text holds names,
    paths and codes only (E37, E38); a refused write, the suite's refusing stub and a programming error propagate."""
    utc, path, answers = model.iso_utc(now), _ACCOUNTS, {}
    try:
        for path, params in _SIGNED:
            answers[path] = request("upbit", "GET", path, params)
        path, cash, holdings = _ACCOUNTS, {}, {}
        for row in _rows(answers[path].body):
            currency, locked = _field(row, "currency"), _num(row, "locked")
            units = _num(row, "balance") + locked
            if currency == "KRW":
                cash["KRW"] = units
            elif units > 0:
                cost = _num(row, "avg_buy_price") if _field(row, "unit_currency") == "KRW" else None
                holdings[currency] = Holding(units=units, locked=locked, avg_cost=cost)
        path = _OPEN
        orders = tuple(Order(id=_field(r, "uuid"), symbol=_market(r)[1], side=_side(r),
                             units=_num(r, "remaining_volume"), price=_price(r)) for r in _rows(answers[path].body))
        path, fills = _CLOSED, []
        for row in _rows(answers[path].body):
            units = _num(row, "executed_volume")
            if units > 0:                                   # a cancelled order with nothing executed is no fill
                quote, base = _market(row)
                fills.append(Move(id=_field(row, "uuid"), symbol=base, counter=quote, side=_side(row), units=units))
        path = _WITHDRAWS
        withdrawals = tuple(Move(id=_field(r, "uuid"), symbol=_field(r, "currency"), side="out",
                                 units=_num(r, "amount")) for r in _rows(answers[path].body))
        path = _DEPOSITS
        deposits = tuple(Move(id=_field(r, "uuid"), symbol=_field(r, "currency"), side="in",
                              units=_num(r, "amount")) for r in _rows(answers[path].body))
        path = _ADDRESSES
        addresses = tuple(Address(currency=_field(r, "currency"), net_type=_field(r, "net_type"),
                                  address=_field(r, "withdraw_address"),
                                  secondary_address=_field(r, "secondary_address") or "")
                          for r in _rows(answers[path].body))
        path = _KEYS                                        # every key of the account: E1 never sees its own (E21)
        expiries = [_when(r, "expire_at") for r in _rows(answers[path].body)]
        path = _TICKER
        markets = sorted({f"KRW-{c}" for c in holdings} | {"KRW-USDT"})     # KRW-USDT values OKX too (E32)
        answers[path] = request("upbit", "GET", path, [("markets", ",".join(markets))])
        prices = {}
        for row in _rows(answers[path].body):
            quote, base = _market(row)
            if quote != "KRW":                              # only KRW markets were asked: prices_krw is KRW only
                raise FieldError("market")
            prices[base] = _num(row, "trade_price")
        server_utc, offset = _clock_of(answers)
        return Snapshot(venue="upbit", utc=utc, server_utc=server_utc, clock_offset_s=offset, ok=True,
                        holdings=holdings, cash=cash, open_orders=orders, fills=tuple(fills), deposits=deposits,
                        withdrawals=withdrawals, withdrawal_addresses=addresses,
                        key_expiry=model.iso_utc(min(expiries)) if expiries else None, prices_krw=prices,
                        response_sha256={p: a.sha256 for p, a in answers.items()})
    except _CONTAINED as exc:
        return _failed(utc, path, exc, answers)


def _failed(utc: str, path: str, exc: Exception, answers: dict) -> Snapshot:
    """A contained venue error as a failed snapshot (E38), keeping the venue time read so far (E39); the text is
    built from names only, never str() of a parse or network error (E37). An out_of_scope answer (a permission the
    key lacks) reaches here as an AuthError, so auth_error (spec 5)."""
    if isinstance(exc, KeyMissing):
        error, flags = f"keys missing: {exc.name}", frozenset({"keys_missing"})
    elif isinstance(exc, AuthError):
        error, flags = str(exc), frozenset({"auth_error"})
    elif isinstance(exc, (InquiryRefused, InquiryError)):
        error, flags = str(exc), frozenset()
    elif isinstance(exc, FieldError):
        error, flags = f"upbit: {path}: field {exc.args[0]}", frozenset()
    else:
        error, flags = f"upbit: {path}: {type(exc).__name__}", frozenset()
    server_utc, offset = _clock_of(answers)
    return failed("upbit", utc, error, flags=flags, server_utc=server_utc, clock_offset_s=offset)


def _clock_of(answers: dict) -> tuple[str | None, float | None]:
    """server_utc and clock_offset_s from the first answer with a Date header (E39)."""
    for answer in answers.values():
        if answer.server_utc is not None:
            return model.iso_utc(answer.server_utc), (answer.server_utc - answer.received_utc).total_seconds()
    return None, None


def _rows(body) -> list:
    """An Upbit list answer."""
    if not isinstance(body, list):
        raise FieldError("body")
    return body


def _field(row, name: str):
    """row[name]; FieldError(name) when row is not a dict or lacks it (E37)."""
    if not isinstance(row, dict) or name not in row:
        raise FieldError(name)
    return row[name]


def _num(row, name: str) -> float:
    """A finite number from a decimal string (exchange answers) or a JSON number (quotation prices); otherwise
    FieldError(name), never the value."""
    value = _field(row, name)
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        raise FieldError(name)
    try:
        number = float(value)
    except (ValueError, OverflowError):                 # OverflowError: an integer too large for a float
        raise FieldError(name) from None
    if not math.isfinite(number):
        raise FieldError(name)
    return number


def _price(row) -> float | None:
    """An order's price; None for a null or zero price (a market order)."""
    return None if _field(row, "price") is None else _num(row, "price") or None


def _market(row) -> tuple[str, str]:
    """(quote, base) of a market such as KRW-BTC."""
    market = _field(row, "market")
    quote, _, base = market.partition("-") if isinstance(market, str) else ("", "", "")
    if not quote or not base or "-" in base:
        raise FieldError("market")
    return quote, base


def _side(row) -> str:
    return "buy" if _field(row, "side") == "bid" else "sell"


def _when(row, name: str) -> datetime:
    """An ISO time; one with no offset is Asia/Seoul, as the Upbit docs give KST (E21)."""
    value = _field(row, name)
    if not isinstance(value, str):
        raise FieldError(name)
    try:
        moment = datetime.fromisoformat(value)
    except ValueError:
        raise FieldError(name) from None
    return moment if moment.utcoffset() is not None else moment.replace(tzinfo=model.KST)
