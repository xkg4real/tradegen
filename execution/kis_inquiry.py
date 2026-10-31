"""KIS read-only inquiry (E1 spec 5 and 6; plan C7, C9): the frozen allowlist, the pinned TR ids and the KIS snapshot
of one poll. The only E1 file that names the KIS account fields. A KIS key can also trade, so `snapshot` reads no
key and sends nothing unless the poll's sealed context says the code on disk is the code the owner signed (E42).
Every list is read on its first page only."""
from __future__ import annotations

import math
from datetime import date, datetime, timedelta

from core.compliance import model
from execution import keys
from execution.snapshot import FieldError, Holding, Move, Order, Snapshot, failed
from execution.transport import AuthError, InquiryError, InquiryRefused, KeyMissing, request

ENDPOINTS = frozenset({
    ("POST", "/oauth2/tokenP"),
    ("GET", "/uapi/domestic-stock/v1/trading/inquire-balance"),
    ("GET", "/uapi/domestic-stock/v1/trading/inquire-psbl-rvsecncl"),
    ("GET", "/uapi/domestic-stock/v1/trading/inquire-daily-ccld"),
    ("GET", "/uapi/domestic-stock/v1/trading/inquire-account-balance"),
    ("GET", "/uapi/domestic-stock/v1/trading/intgr-margin"),
    ("GET", "/uapi/overseas-stock/v1/trading/inquire-balance"),
    ("GET", "/uapi/overseas-stock/v1/trading/inquire-nccs"),
    ("GET", "/uapi/overseas-stock/v1/trading/inquire-ccnl"),
    ("GET", "/uapi/overseas-stock/v1/trading/inquire-present-balance"),
})
TR_IDS = frozenset({
    ("/uapi/domestic-stock/v1/trading/inquire-balance", "TTTC8434R"),
    ("/uapi/domestic-stock/v1/trading/inquire-psbl-rvsecncl", "TTTC0084R"),
    ("/uapi/domestic-stock/v1/trading/inquire-daily-ccld", "TTTC0081R"),
    ("/uapi/domestic-stock/v1/trading/inquire-account-balance", "CTRP6548R"),
    ("/uapi/domestic-stock/v1/trading/intgr-margin", "TTTC0869R"),
    ("/uapi/overseas-stock/v1/trading/inquire-balance", "TTTS3012R"),
    ("/uapi/overseas-stock/v1/trading/inquire-nccs", "TTTS3018R"),
    ("/uapi/overseas-stock/v1/trading/inquire-ccnl", "TTTS3035R"),
    ("/uapi/overseas-stock/v1/trading/inquire-present-balance", "CTRP6504R"),
})
PUBLIC = frozenset()
ACCOUNT_NAMES = ("KIS_ACCOUNT_8", "KIS_ACCOUNT_PD")

_BALANCE = "/uapi/domestic-stock/v1/trading/inquire-balance"
_OPEN = "/uapi/domestic-stock/v1/trading/inquire-psbl-rvsecncl"
_FILLS = "/uapi/domestic-stock/v1/trading/inquire-daily-ccld"
_ASSETS = "/uapi/domestic-stock/v1/trading/inquire-account-balance"
_MARGIN = "/uapi/domestic-stock/v1/trading/intgr-margin"
_US_BALANCE = "/uapi/overseas-stock/v1/trading/inquire-balance"
_US_OPEN = "/uapi/overseas-stock/v1/trading/inquire-nccs"
_US_FILLS = "/uapi/overseas-stock/v1/trading/inquire-ccnl"
_US_CASH = "/uapi/overseas-stock/v1/trading/inquire-present-balance"
_CONTAINED = (KeyMissing, InquiryRefused, InquiryError, LookupError, ValueError, TypeError, AttributeError,
              ArithmeticError)                      # E38: the venue's own errors (AuthError and FieldError included)


def snapshot(now: datetime, ctx: model.Context) -> Snapshot:
    """The KIS snapshot of the poll at `now` (C9); `ctx` is the context that poll loaded first (E24). A venue error
    gives a failed snapshot whose text holds names, paths and codes only (E37, E38); a refused write, the suite's
    refusing stub and a programming error propagate."""
    if not (model.is_sealed(ctx) and ctx.code_signed is True):
        return failed("kis", model.iso_utc(now), "code not signed", flags=frozenset({"code_unsigned"}))
    utc, path, answers = model.iso_utc(now), "", {}
    try:
        cano, prdt = keys.read(ACCOUNT_NAMES)
        if not (_digits(cano, 8) and _digits(prdt, 2)):
            return failed("kis", utc, "kis: KIS account number is not 8 + 2 digits")
        pinned = dict(TR_IDS)
        # ponytail: first page only; a 51st holding or 101st fill is missed; add tr_cont paging when the account grows
        for path, params in _calls(cano, prdt, now.astimezone(model.KST).date()):
            answers[path] = request("kis", "GET", path, params, tr_id=pinned[path])
        body = {p: a.body for p, a in answers.items()}
        path, cash, prices, rates = _US_CASH, {}, {}, {}    # first: the overseas prices need its rates
        for row in _list(body[path], "output2"):
            ccy = _text(row, "crcy_cd")
            cash[ccy] = _num(row, "frcr_dncl_amt_2")
            rates[ccy] = prices[ccy] = _num(row, "frst_bltn_exrt")
        path, holdings = _BALANCE, {}
        rows, total = _list(body[path], "output1"), _one(body[path], "output2")
        cash["KRW"] = _num(total, "prvs_rcdl_excc_amt")     # D+2: a buy not yet settled is not counted twice (E16)
        deposit = _num(total, "dnca_tot_amt")
        loans = {"tot_loan_amt": _num(total, "tot_loan_amt"),
                 "loan_amt": sum((_num(r, "loan_amt") for r in rows), 0.0)}
        for row in rows:
            units = _num(row, "hldg_qty")
            if units > 0:
                holdings[_text(row, "pdno")] = _holding(row, units)
                prices[_text(row, "pdno")] = _num(row, "prpr")
        path = _US_BALANCE
        for row in _list(body[path], "output1"):
            units = _num(row, "ovrs_cblc_qty")
            if units > 0:
                symbol, rate = _text(row, "ovrs_pdno"), rates.get(_text(row, "tr_crcy_cd"))
                holdings[symbol] = _holding(row, units)
                if rate is not None:                        # no rate, no price: positions then fail closed (E17)
                    prices[symbol] = _num(row, "now_pric2") * rate
        path, orders = _OPEN, []
        for row in _list(body[path], "output"):
            units = _num(row, "psbl_qty")
            if units > 0:
                orders.append(Order(id=_text(row, "odno"), symbol=_text(row, "pdno"), side=_side(row), units=units,
                                    price=_num(row, "ord_unpr")))
        path = _US_OPEN
        for row in _list(body[path], "output"):
            orders.append(Order(id=_text(row, "odno"), symbol=_text(row, "pdno"), side=_side(row),
                                units=_num(row, "nccs_qty") or _num(row, "ft_ord_qty"),
                                price=_num(row, "ft_ord_unpr3")))
        fills = []
        for path, rows_name, units_name in ((_FILLS, "output1", "tot_ccld_qty"), (_US_FILLS, "output", "ft_ccld_qty")):
            for row in _list(body[path], rows_name):
                units = _num(row, units_name)
                if units > 0:
                    counter = "KRW" if path == _FILLS else _text(row, "tr_crcy_cd")
                    fills.append(Move(id=f"{_text(row, 'ord_dt')}-{_text(row, 'odno')}", symbol=_text(row, "pdno"),
                                      counter=counter, side=_side(row), units=units))
        path = _ASSETS
        assets = _one(body[path], "output2")
        loans["crdt_fncg_amt"] = _num(assets, "crdt_fncg_amt")
        loans["thdt_rcvb_amt"] = _num(assets, "thdt_rcvb_amt")
        path = _MARGIN
        loans["rcvb_amt"] = _num(_one(body[path], "output"), "rcvb_amt")
        server_utc, offset = _clock_of(answers)
        return Snapshot(venue="kis", utc=utc, server_utc=server_utc, clock_offset_s=offset, ok=True,
                        holdings=holdings, cash=cash, deposit_krw=deposit, open_orders=tuple(orders),
                        fills=tuple(fills), loans=loans, prices_krw=prices,
                        response_sha256={p: a.sha256 for p, a in answers.items()})   # paths only, never a query
    except _CONTAINED as exc:
        return _failed(utc, path, exc, answers)


def _calls(cano: str, prdt: str, today: date) -> tuple[tuple[str, list[tuple[str, str]]], ...]:
    """(path, params) of the nine GETs in their order (C9); the dates are Seoul dates."""
    d0, d1, d2 = (f"{today - timedelta(days=n):%Y%m%d}" for n in (0, 1, 2))
    acct = [("CANO", cano), ("ACNT_PRDT_CD", prdt)]
    return (
        (_BALANCE, acct + [("AFHR_FLPR_YN", "N"), ("OFL_YN", ""), ("INQR_DVSN", "01"), ("UNPR_DVSN", "01"),
                           ("FUND_STTL_ICLD_YN", "N"), ("FNCG_AMT_AUTO_RDPT_YN", "N"), ("PRCS_DVSN", "00"),
                           ("CTX_AREA_FK100", ""), ("CTX_AREA_NK100", "")]),
        (_OPEN, acct + [("CTX_AREA_FK100", ""), ("CTX_AREA_NK100", ""), ("INQR_DVSN_1", "0"),
                        ("INQR_DVSN_2", "0")]),
        (_FILLS, acct + [("INQR_STRT_DT", d1), ("INQR_END_DT", d0), ("SLL_BUY_DVSN_CD", "00"), ("INQR_DVSN", "00"),
                         ("PDNO", ""), ("CCLD_DVSN", "01"), ("ORD_GNO_BRNO", ""), ("ODNO", ""),
                         ("INQR_DVSN_3", "00"), ("INQR_DVSN_1", ""), ("EXCG_ID_DVSN_CD", "ALL"),
                         ("CTX_AREA_FK100", ""), ("CTX_AREA_NK100", "")]),
        (_ASSETS, acct + [("INQR_DVSN_1", ""), ("BSPR_BF_DT_APLY_YN", "")]),
        (_MARGIN, acct + [("CMA_EVLU_AMT_ICLD_YN", "N"), ("WCRC_FRCR_DVSN_CD", "01"),
                          ("FWEX_CTRT_FRCR_DVSN_CD", "01")]),
        (_US_BALANCE, acct + [("OVRS_EXCG_CD", "NASD"), ("TR_CRCY_CD", "USD"), ("CTX_AREA_FK200", ""),
                              ("CTX_AREA_NK200", "")]),
        (_US_OPEN, acct + [("OVRS_EXCG_CD", "NASD"), ("SORT_SQN", "DS"), ("CTX_AREA_FK200", ""),
                           ("CTX_AREA_NK200", "")]),
        (_US_FILLS, acct + [("PDNO", "%"), ("ORD_STRT_DT", d2), ("ORD_END_DT", d0), ("SLL_BUY_DVSN", "00"),
                            ("CCLD_NCCS_DVSN", "01"), ("OVRS_EXCG_CD", "NASD"), ("SORT_SQN", "DS"), ("ORD_DT", ""),
                            ("ORD_GNO_BRNO", ""), ("ODNO", ""), ("CTX_AREA_NK200", ""), ("CTX_AREA_FK200", "")]),
        (_US_CASH, acct + [("WCRC_FRCR_DVSN_CD", "02"), ("NATN_CD", "000"), ("TR_MKET_CD", "00"),
                           ("INQR_DVSN_CD", "00")]),
    )


def _failed(utc: str, path: str, exc: Exception, answers: dict) -> Snapshot:
    """A contained venue error as a failed snapshot (E38), keeping the venue time read so far (E39); the text is
    built from names only, never str() of a parse or network error (E37)."""
    if isinstance(exc, KeyMissing):
        error, flags = f"keys missing: {exc.name}", frozenset({"keys_missing"})
    elif isinstance(exc, AuthError):
        error, flags = str(exc), frozenset({"auth_error"})
    elif isinstance(exc, (InquiryRefused, InquiryError)):
        error, flags = str(exc), frozenset()
    elif isinstance(exc, FieldError):
        error, flags = f"kis: {path}: field {exc.args[0]}", frozenset()
    else:
        error, flags = f"kis: {path}: {type(exc).__name__}", frozenset()
    server_utc, offset = _clock_of(answers)
    return failed("kis", utc, error, flags=flags, server_utc=server_utc, clock_offset_s=offset)


def _clock_of(answers: dict) -> tuple[str | None, float | None]:
    """server_utc and clock_offset_s from the first answer with a Date header (E39)."""
    for answer in answers.values():
        if answer.server_utc is not None:
            return model.iso_utc(answer.server_utc), (answer.server_utc - answer.received_utc).total_seconds()
    return None, None


def _field(row, name: str):
    """row[name]; FieldError(name) when row is not a dict or lacks it (E37)."""
    if not isinstance(row, dict) or name not in row:
        raise FieldError(name)
    return row[name]


def _text(row, name: str) -> str:
    """row[name] as a non-empty string (an id, a symbol, a currency or a date); otherwise FieldError(name)."""
    value = _field(row, name)
    if not isinstance(value, str) or not value:
        raise FieldError(name)
    return value


def _num(row, name: str) -> float:
    """A finite number from a KIS string ("" is 0, commas dropped); otherwise FieldError(name), never the value."""
    value = _field(row, name)
    if not isinstance(value, str):
        raise FieldError(name)
    try:
        number = 0.0 if value == "" else float(value.replace(",", ""))
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


def _side(row) -> str:
    return "sell" if _field(row, "sll_buy_dvsn_cd") == "01" else "buy"


def _holding(row, units: float) -> Holding:
    free = _num(row, "ord_psbl_qty")
    if not 0.0 <= free <= units:                    # more free than held is a field mismatch: fail closed (E1R2-5)
        raise FieldError("ord_psbl_qty")
    return Holding(units=units, locked=units - free, avg_cost=_num(row, "pchs_avg_pric"))


def _digits(value: str, n: int) -> bool:
    return len(value) == n and value.isascii() and value.isdigit()
