"""OKX read-only inquiry (E1 spec 5 and 6; plan C7, C11): the frozen allowlist, the read-only self-check and the OKX
snapshot of one poll. Nothing is sent while the OKX keys are missing; public/time comes first, since its offset
gates every signed call (E32); a failed self-check stops OKX for that poll. OKX lists no withdrawal address book,
so OKX addresses are not checked."""
from __future__ import annotations

import math
from collections.abc import Mapping
from datetime import datetime, timedelta, timezone

from core.compliance import model
from execution.snapshot import FieldError, Holding, Move, Order, Snapshot, failed
from execution.transport import AuthError, InquiryError, InquiryRefused, KeyMissing, request, require_keys

ENDPOINTS = frozenset({
    ("GET", "/api/v5/account/config"), ("GET", "/api/v5/account/balance"), ("GET", "/api/v5/account/positions"),
    ("GET", "/api/v5/asset/balances"), ("GET", "/api/v5/asset/asset-valuation"),
    ("GET", "/api/v5/finance/savings/balance"), ("GET", "/api/v5/finance/flexible-loan/loan-info"),
    ("GET", "/api/v5/trade/orders-pending"), ("GET", "/api/v5/trade/orders-algo-pending"),
    ("GET", "/api/v5/trade/fills"), ("GET", "/api/v5/asset/deposit-history"),
    ("GET", "/api/v5/asset/withdrawal-history"), ("GET", "/api/v5/public/time"), ("GET", "/api/v5/market/ticker"),
})
PUBLIC = frozenset({"/api/v5/public/time", "/api/v5/market/ticker"})
ALGO_TYPES = ("conditional", "oco", "trigger", "move_order_stop", "iceberg", "twap", "chase")

SELF_CHECK = ("perm", "acctLv", "enableSpotBorrow", "autoLoan", "ip")

_FLAGS = ("okx_perm", "okx_acct_lv", "okx_spot_borrow", "okx_auto_loan", "okx_no_ip")   # one per SELF_CHECK name
_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)   # epoch + timedelta: an absurd ts is OverflowError, never the
                                                    # OSError that datetime.fromtimestamp raises on Windows
_TIME = "/api/v5/public/time"
_CONFIG = "/api/v5/account/config"
_BALANCE = "/api/v5/account/balance"
_FUNDING = "/api/v5/asset/balances"
_POSITIONS = "/api/v5/account/positions"
_VALUATION = "/api/v5/asset/asset-valuation"
_SAVINGS = "/api/v5/finance/savings/balance"
_LOANS = "/api/v5/finance/flexible-loan/loan-info"
_PENDING = "/api/v5/trade/orders-pending"
_ALGO = "/api/v5/trade/orders-algo-pending"
_FILLS = "/api/v5/trade/fills"
_DEPOSITS = "/api/v5/asset/deposit-history"
_WITHDRAWALS = "/api/v5/asset/withdrawal-history"
_TICKER = "/api/v5/market/ticker"
_BEFORE_ALGO = ((_BALANCE, None), (_FUNDING, None), (_POSITIONS, None), (_VALUATION, [("ccy", "USDT")]),
                (_SAVINGS, None), (_LOANS, None), (_PENDING, None))
_AFTER_ALGO = ((_FILLS, None), (_DEPOSITS, None), (_WITHDRAWALS, None), (_TICKER, [("instId", "BTC-USDT")]))
_CONTAINED = (KeyMissing, InquiryRefused, InquiryError, LookupError, ValueError, TypeError, AttributeError,
              ArithmeticError)                      # E38: the venue's own errors (AuthError and FieldError included)


def self_check(config: Mapping) -> frozenset[str]:
    """The failed flags of the key and account self-check (spec 5): `perm` exactly "read_only" (OKX may report
    permissions its docs do not list), spot mode, spot borrow and auto-loan off, and a bound IP. Pure."""
    ip = config.get("ip")
    passed = (config.get("perm") == "read_only", config.get("acctLv") == "1",
              config.get("enableSpotBorrow") is False, config.get("autoLoan") is False,
              isinstance(ip, str) and ip != "")
    return frozenset(flag for flag, ok in zip(_FLAGS, passed) if not ok)


def snapshot(now: datetime, usdt_krw: float | None) -> Snapshot:
    """The OKX snapshot of the poll at `now` (C11); `usdt_krw` is Upbit's KRW-USDT price of this poll, or None. A
    venue error gives a failed snapshot whose text holds names, paths and codes only (E37, E38); a refused write, the
    suite's refusing stub and a programming error propagate."""
    utc, path, answers, server_utc, offset = model.iso_utc(now), _TIME, {}, None, None
    try:
        require_keys("okx")                                 # no call at all while the keys are missing (E32)
        answers[path] = request("okx", "GET", path)
        ts = _num(_one(answers[path].body, "data"), "ts") / 1000
        server_utc = model.iso_utc(_EPOCH + timedelta(seconds=ts))
        offset = ts - answers[path].received_utc.timestamp()      # transport keeps the same offset for its check
        path = _CONFIG
        answers[path] = request("okx", "GET", path)
        bad = self_check(_one(answers[path].body, "data"))
        if bad:
            names = ", ".join(name for name, flag in zip(SELF_CHECK, _FLAGS) if flag in bad)
            return failed("okx", utc, f"okx self-check failed: {names}", flags=bad, server_utc=server_utc,
                          clock_offset_s=offset)
        for path, params in _BEFORE_ALGO:
            answers[path] = request("okx", "GET", path, params)
        path = _ALGO
        for kind in ALGO_TYPES:                             # one call per ordType, never a comma list (E25)
            answers[f"{_ALGO}?ordType={kind}"] = request("okx", "GET", path, [("ordType", kind)])
        for path, params in _AFTER_ALGO:
            answers[path] = request("okx", "GET", path, params)
        flags, units, locked, loans, earn = set(), {}, {}, {}, {}
        path = _BALANCE
        for row in _list(_one(answers[path].body, "data"), "details"):
            ccy = _field(row, "ccy")
            _add(units, ccy, _num(row, "cashBal"))
            _add(locked, ccy, _num(row, "frozenBal"))
            _add(loans, f"liab:{ccy}", _num(row, "liab"))
            if _field(row, "autoLendStatus") in ("pending", "active"):
                _add(earn, f"auto_lend:{ccy}", _num(row, "autoLendMtAmt") or 1.0)
        path = _FUNDING
        for row in _list(answers[path].body, "data"):
            ccy = _field(row, "ccy")
            _add(units, ccy, _num(row, "bal"))
            _add(locked, ccy, _num(row, "frozenBal"))
        path = _POSITIONS
        for row in _list(answers[path].body, "data"):
            kind = _field(row, "instType")
            if kind == "EVENTS":
                flags.add("EVENTS")                         # any EVENTS row, even one of size 0 (okx.md correction 8)
                continue
            if _field(row, "pos") == "":
                raise FieldError("pos")                     # a position always has a size: "" fails closed (E25)
            size = _num(row, "pos")
            if size == 0:
                continue                                    # a zero row is no exposure (okx.md correction 7)
            if kind == "MARGIN":
                _add(loans, f"margin:{_field(row, 'instId')}", abs(size))
            else:                                           # SWAP, FUTURES, OPTION, and any type OKX adds later
                flags.add("derivative_position")
        path = _VALUATION
        earn["asset_valuation"] = _num(_field(_one(answers[path].body, "data"), "details"), "earn")
        path = _SAVINGS
        for row in _list(answers[path].body, "data"):
            _add(earn, f"savings:{_field(row, 'ccy')}", _num(row, "amt"))
        path = _LOANS
        for info in _list(answers[path].body, "data"):
            for row in _list(info, "loanData"):
                _add(loans, f"flexible_loan:{_field(row, 'ccy')}", _num(row, "amt"))
        orders, fills = [], []
        for key in (_PENDING,) + tuple(f"{_ALGO}?ordType={kind}" for kind in ALGO_TYPES):
            path = key.partition("?")[0]
            for row in _list(answers[key].body, "data"):
                if _field(row, "instType") == "EVENTS":
                    flags.add("EVENTS")
                order_id = _field(row, "ordId" if path == _PENDING else "algoId")
                orders.append(Order(id=order_id, symbol=_pair(row)[0], side=_field(row, "side"),
                                    units=_num(row, "sz"), price=_num(row, "px") or None))
        path = _FILLS
        for row in _list(answers[path].body, "data"):
            if _field(row, "instType") == "EVENTS":
                flags.add("EVENTS")
            base, quote = _pair(row)
            fills.append(Move(id=_field(row, "tradeId"), symbol=base, counter=quote, side=_field(row, "side"),
                              units=_num(row, "fillSz")))
        path = _DEPOSITS
        deposits = tuple(Move(id=_field(r, "depId"), symbol=_field(r, "ccy"), side="in", units=_num(r, "amt"))
                         for r in _list(answers[path].body, "data"))
        path = _WITHDRAWALS
        withdrawals = tuple(Move(id=_field(r, "wdId"), symbol=_field(r, "ccy"), side="out", units=_num(r, "amt"))
                            for r in _list(answers[path].body, "data"))
        path = _TICKER
        last, prices = _num(_one(answers[path].body, "data"), "last"), {}
        if usdt_krw is not None and math.isfinite(usdt_krw) and usdt_krw > 0:   # other coins stay unpriced (E17)
            prices = {"USDT": usdt_krw, "USDC": usdt_krw, "BTC": last * usdt_krw}
        return Snapshot(venue="okx", utc=utc, server_utc=server_utc, clock_offset_s=offset, ok=True,
                        holdings={c: Holding(units=u, locked=locked[c]) for c, u in units.items() if u > 0},
                        open_orders=tuple(orders), fills=tuple(fills), deposits=deposits, withdrawals=withdrawals,
                        loans=loans, earn=earn, flags=frozenset(flags), prices_krw=prices,
                        response_sha256={k: a.sha256 for k, a in answers.items()})
    except _CONTAINED as exc:
        return _failed(utc, path, exc, server_utc, offset)


def _failed(utc: str, path: str, exc: Exception, server_utc: str | None, offset: float | None) -> Snapshot:
    """A contained venue error as a failed snapshot (E38); the text is built from names only, never str() of a
    parse or network error (E37). It keeps the clock offset, so CLOCK_SKEW still sees a refused poll (E39)."""
    if isinstance(exc, KeyMissing):
        error, flags = f"keys missing: {exc.name}", frozenset({"keys_missing"})
    elif isinstance(exc, AuthError):
        error, flags = str(exc), frozenset({"auth_error"})
    elif isinstance(exc, (InquiryRefused, InquiryError)):
        error, flags = str(exc), frozenset()
    elif isinstance(exc, FieldError):
        error, flags = f"okx: {path}: field {exc.args[0]}", frozenset()
    else:
        error, flags = f"okx: {path}: {type(exc).__name__}", frozenset()
    return failed("okx", utc, error, flags=flags, server_utc=server_utc, clock_offset_s=offset)


def _add(totals: dict, key: str, amount: float) -> None:
    totals[key] = totals.get(key, 0.0) + amount


def _pair(row) -> tuple[str, str]:
    """(base, quote) of an instId such as BTC-USDT or BTC-USDT-SWAP."""
    inst = _field(row, "instId")
    base, _, rest = inst.partition("-") if isinstance(inst, str) else ("", "", "")
    if not base or not rest:
        raise FieldError("instId")
    return base, rest.partition("-")[0]


def _field(row, name: str):
    """row[name]; FieldError(name) when row is not a dict or lacks it (E37)."""
    if not isinstance(row, dict) or name not in row:
        raise FieldError(name)
    return row[name]


def _num(row, name: str) -> float:
    """A finite number from an OKX string ("" means not applicable, so 0); otherwise FieldError(name), never the
    value."""
    value = _field(row, name)
    if not isinstance(value, str):
        raise FieldError(name)
    try:
        number = 0.0 if value == "" else float(value)
    except ValueError:
        raise FieldError(name) from None
    if not math.isfinite(number):
        raise FieldError(name)
    return number


def _one(body, name: str) -> dict:
    """body[name] as one dict: the dict itself, or the first row of a non-empty list."""
    value = _field(body, name)
    if isinstance(value, list) and value:
        value = value[0]
    if not isinstance(value, dict):
        raise FieldError(name)
    return value


def _list(body, name: str) -> list:
    """body[name], which must be a list."""
    rows = _field(body, name)
    if not isinstance(rows, list):
        raise FieldError(name)
    return rows
