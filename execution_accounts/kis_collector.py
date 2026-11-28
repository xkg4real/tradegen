"""Offline KIS cash-equity capture from injected archive pages and a reviewed statement.

Each receipt's path is its KIS TR identifier. The source binds the opaque scope
to the original account and supplies response headers separately from the body.
Workbooks supplied with TRADEGEN: [국내주식] 주문_계좌.xlsx, sheets 주식잔고조회,
주식일별주문체결조회 and 주식정정취소가능주문조회; [해외주식] 주문_계좌.xlsx, sheets 해외주식 잔고,
해외주식 미체결내역, 해외주식 주문체결내역 and 해외주식 체결기준현재잔고. Source file SHA-256:
63f289ecaa421f98df3a7b24b1bb90afe953b3490ef0380e01c5c33350ce7534 and
209af25e5820fc39ed8d1f95a2eb81b6983113c2e1ea3d6990c9bb74e2706619.

The supported cut must cover both currencies, all four market dates, whole
shares, ordinary cash orders and fully settled cash. The history window is
bounded to 80 days inside the domestic recent-history TR. Unknown US terminal
cancellations, recent unsettled trades, unsupported flows, credit, incomplete
archives and fractional shares require additional evidence. Exchange receipt
times are never used as execution, mark or FX times. See docs/account-evidence-contract.md.
This module has no default source, HTTP transport, credential reader or order API.
"""
from __future__ import annotations

from dataclasses import dataclass, field, fields
from datetime import datetime, timedelta
from decimal import Inexact, localcontext
from zoneinfo import ZoneInfo

from core.compliance.model import KST
from execution_accounts.collector import SourceReceipt, digest, identifier, instant, number, require
from execution_accounts.model import AccountBundle, AccountEvidence, EvidencePage, content_digest
from execution_accounts.provider import EvidenceError, build_observation


_KR_BAL, _US_BAL = "TTTC8434R", "TTTS3012R"
_KR_ORD, _US_ORD, _CASH = "TTTC0081R", "TTTS3035R", "CTRP6504R"
_KR_OPEN, _US_OPEN = "TTTC0084R", "TTTS3018R"
_US_MARKETS = ("nasd", "nyse", "amex")
_EASTERN = ZoneInfo("America/New_York")


@dataclass(frozen=True, kw_only=True, repr=False)
class KisArchivePage:
    receipt: SourceReceipt = field(repr=False)
    response_tr_id: str
    response_tr_cont: str


@dataclass(frozen=True, kw_only=True)
class KisStatementReview:
    """External reviewer binds exact E2 economics, source identity and coverage.

    The review covers a zero-inventory/no-pending opening anchor, per-execution
    identities, actual fill times, fees/taxes, FX, complete cash flows and venue
    dates. Only fully settled ordinary whole-share cash accounts with no hidden
    holdings or activity are supported. A digest by itself proves no authority.
    """
    account_scope: str
    statement_sha256: str
    review_source_sha256: str
    coverage: str
    quiescent_from: datetime
    quiescent_until: datetime


@dataclass(frozen=True, kw_only=True, repr=False)
class KisCollection:
    bundle: AccountBundle
    pages: tuple[KisArchivePage, ...]
    review: KisStatementReview
    manifest_sha256: str


def _queries(account):
    domestic_from = account.origin.astimezone(KST).strftime("%Y%m%d")
    domestic_to = account.observed_at.astimezone(KST).strftime("%Y%m%d")
    us_from = account.origin.astimezone(_EASTERN).strftime("%Y%m%d")
    us_to = account.observed_at.astimezone(_EASTERN).strftime("%Y%m%d")
    return (
        (_KR_BAL, "100", "output1", dict(AFHR_FLPR_YN="N", OFL_YN="", INQR_DVSN="01", UNPR_DVSN="01",
            FUND_STTL_ICLD_YN="N", FNCG_AMT_AUTO_RDPT_YN="N", PRCS_DVSN="00")),
        (_US_BAL, "200", "output1", dict(OVRS_EXCG_CD="NASD", TR_CRCY_CD="USD")),
        (_KR_ORD, "100", "output1", dict(INQR_STRT_DT=domestic_from, INQR_END_DT=domestic_to,
            SLL_BUY_DVSN_CD="00", INQR_DVSN="00", PDNO="", CCLD_DVSN="00", ORD_GNO_BRNO="", ODNO="",
            INQR_DVSN_3="00", INQR_DVSN_1="", EXCG_ID_DVSN_CD="ALL")),
        (_US_ORD, "200", "output", dict(PDNO="%", ORD_STRT_DT=us_from, ORD_END_DT=us_to, SLL_BUY_DVSN="00",
            CCLD_NCCS_DVSN="00", OVRS_EXCG_CD="NASD", SORT_SQN="DS", ORD_DT="", ORD_GNO_BRNO="", ODNO="")),
        (_KR_OPEN, "100", "output", dict(INQR_DVSN_1="0", INQR_DVSN_2="0")),
        *((_US_OPEN, "200", "output", dict(OVRS_EXCG_CD=market.upper(), SORT_SQN="DS"))
          for market in _US_MARKETS),
        (_CASH, "", "output2", dict(WCRC_FRCR_DVSN_CD="02", NATN_CD="000", TR_MKET_CD="00", INQR_DVSN_CD="00")),
    )


def _capture(source, account, review, limit):
    pages, rows, summaries = [], {}, {}
    rows["present_positions"] = []
    row_count = byte_count = 0
    for tr_id, width, output, filters in _queries(account):
        rows.setdefault(tr_id, [])
        cursor, seen = ("", ""), set()
        while True:
            require(len(pages) < limit, "KIS_ARCHIVE_PAGE_LIMIT")
            params = dict(filters)
            if width:
                params.update({f"CTX_AREA_FK{width}": cursor[0], f"CTX_AREA_NK{width}": cursor[1]})
            params["tr_cont"] = "N" if seen else ""
            params = tuple(sorted(params.items()))
            page = source.read_page(tr_id, params)
            require(type(page) is KisArchivePage and type(page.receipt) is SourceReceipt, "KIS_PAGE_REQUIRED")
            r = page.receipt
            require((r.path, r.params, r.account_scope) == (tr_id, params, account.account_scope)
                    and page.response_tr_id == tr_id, "KIS_RECEIPT_BINDING_MISMATCH")
            received, server = instant(r.received_at), instant(r.server_time)
            require(review.quiescent_from <= received <= account.observed_at
                    and timedelta(0) <= account.observed_at - received <= timedelta(seconds=30)
                    and abs(received - server) <= timedelta(seconds=60)
                    and server.astimezone(KST).date() == account.observed_at.astimezone(KST).date(),
                    "KIS_CAPTURE_TIME_MISMATCH")
            require(type(r.raw_body) is bytes, "COLLECTOR_RAW_BYTES_REQUIRED")
            byte_count += len(r.raw_body)
            require(byte_count <= 64 * 1024 * 1024, "KIS_ARCHIVE_BYTE_LIMIT")
            payload = r.decode()
            require(type(payload) is dict and payload.get("rt_cd") == "0", "KIS_RESPONSE_UNSUCCESSFUL")
            records = payload.get(output)
            require(type(records) is list and all(type(row) is dict for row in records), "KIS_RECORDS_REQUIRED")
            row_count += len(records)
            require(row_count <= 100000, "KIS_ARCHIVE_ROW_LIMIT")
            if tr_id == _US_OPEN:
                require(all(row.get("ovrs_excg_cd") == filters["OVRS_EXCG_CD"] for row in records),
                        "KIS_OPEN_EXCHANGE_MISMATCH")
            pages.append(page)
            rows[tr_id].extend(records)
            if tr_id == _CASH:
                current_positions = payload.get("output1")
                require(type(current_positions) is list and len(current_positions) <= 100000 - row_count
                        and all(type(row) is dict for row in current_positions), "KIS_RECORDS_REQUIRED")
                rows["present_positions"].extend(current_positions)
                row_count += len(current_positions)
            if tr_id in (_KR_BAL, _CASH):
                summary = payload.get("output2" if tr_id == _KR_BAL else "output3")
                if type(summary) is list and len(summary) == 1:
                    summary = summary[0]
                require(type(summary) is dict and (tr_id not in summaries or summaries[tr_id] == summary),
                        "KIS_BALANCE_SUMMARY_MISMATCH")
                summaries[tr_id] = summary
            if page.response_tr_cont in ("D", "E"):
                # KIS can echo the search context on its terminal page.
                break
            # TTTS3018R's workbook does not support tr_cont continuation.
            require(tr_id != _US_OPEN and width and page.response_tr_cont in ("F", "M"), "KIS_TERMINAL_HEADER_REQUIRED")
            cursor = (payload.get("ctx_area_fk" + width), payload.get("ctx_area_nk" + width))
            require(all(type(part) is str and len(part) <= int(width) for part in cursor)
                    and bool(cursor[1].strip()) and cursor not in seen, "KIS_CURSOR_INCOMPLETE_OR_REPEATED")
            seen.add(cursor)
    return pages, rows, summaries


def _orders(account, records):
    expected = {}
    fills = {}
    for page in account.pages:
        if page.kind not in ("fills", "orders"):
            continue
        for record in page.rows:
            key = (record.market, record.order_date, record.broker_org_id, record.order_id)
            require(record.quantity == record.quantity.to_integral_value(), "KIS_FRACTIONAL_SHARES_UNSUPPORTED")
            if page.kind == "orders":
                require(key not in expected, "KIS_DUPLICATE_ORDER")
                expected[key] = record
            else:
                local_day = record.executed_at.astimezone(KST if record.market == "krx" else _EASTERN).strftime("%Y%m%d")
                require(record.order_date <= local_day, "KIS_FILL_BEFORE_ORDER")
                group = fills.setdefault(key, {})
                require(record.fill_id not in group, "KIS_DUPLICATE_FILL")
                group[record.fill_id] = record
    require(fills.keys() <= expected.keys(), "KIS_FILL_ORDER_REQUIRED")
    found = set()
    locked_shares = {}
    for tr_id in (_KR_ORD, _US_ORD):
        kr = tr_id == _KR_ORD
        for row in records[tr_id]:
            if kr:
                exchanges = [row[k] for k in ("excg_id_dvsn_cd", "excg_id_dvsn_Cd") if k in row]
                require(exchanges and all(v == "KRX" for v in exchanges) and row.get("ord_dvsn_cd") == "00",
                        "KIS_ORDER_MARKET_OR_TYPE_UNSUPPORTED")
                market = "krx"
            else:
                market = row["ovrs_excg_cd"].lower()
                require(market in _US_MARKETS and row.get("tr_crcy_cd") == "USD"
                        and row.get("loan_type_cd") in ("00", "10") and row.get("rvse_cncl_dvsn") == "00",
                        "KIS_FOREIGN_ORDER_UNSUPPORTED")
            key = market, row["ord_dt"], row["ord_gno_brno"], row["odno"]
            require(key in expected and key not in found, "KIS_ORDER_IDENTITY_MISMATCH")
            order = expected[key]
            zone = KST if kr else _EASTERN
            require(account.origin.astimezone(zone).strftime("%Y%m%d") <= order.order_date
                    <= account.observed_at.astimezone(zone).strftime("%Y%m%d"), "KIS_ORDER_OUTSIDE_CAPTURE")
            found.add(key)
            quantity = number(row["ord_qty" if kr else "ft_ord_qty"], positive=True)
            filled = number(row["tot_ccld_qty" if kr else "ft_ccld_qty"])
            remaining = number(row["rmn_qty" if kr else "nccs_qty"])
            price = number(row["ord_unpr" if kr else "ft_ord_unpr3"], positive=True)
            reported_amount = number(row["tot_ccld_amt" if kr else "ft_ccld_amt3"])
            executed_amount = sum((f.quantity * f.price for f in fills.get(key, {}).values()), 0)
            require(row.get("sll_buy_dvsn_cd") == {"buy": "02", "sell": "01"}[order.side]
                    and (row.get("pdno"), quantity, price, filled, remaining, reported_amount)
                    == (order.symbol, order.quantity, order.limit_price, order.filled_quantity,
                        order.remaining_quantity, executed_amount), "KIS_ORDER_ECONOMICS_MISMATCH")
            if kr:
                cancelled, rejected = number(row["cncl_cfrm_qty"]), number(row["rjct_qty"])
                require(row.get("cncl_yn") == ("Y" if cancelled else "N")
                        and filled + remaining + cancelled + rejected == quantity
                        and not (cancelled and rejected)
                        and (not rejected or rejected == quantity), "KIS_TERMINAL_STATE_UNVERIFIED")
            else:
                # A translated status text cannot prove a final overseas cancellation.
                cancelled = rejected = 0
                require(filled + remaining == quantity and not row.get("rjct_rson", "").strip(),
                        "KIS_TERMINAL_STATE_UNVERIFIED")
            status = ("rejected" if rejected else "canceled" if cancelled and not remaining else
                      "filled" if filled == quantity else "partial" if filled else "open")
            require(status == order.status, "KIS_ORDER_STATUS_MISMATCH")
            if order.side == "sell" and remaining:
                ticker = market, order.symbol
                locked_shares[ticker] = locked_shares.get(ticker, 0) + remaining
    require(found == expected.keys(), "KIS_ORDER_COVERAGE_INCOMPLETE")
    _open_orders(expected.values(), records)
    return locked_shares


def _open_orders(orders, records):
    # Domestic cancelable-order replies lack order date. Never guess between
    # two active orders with the same branch and number on different dates.
    expected = {}
    for order in orders:
        if order.status not in ("open", "partial"):
            continue
        key = (order.market, order.broker_org_id, order.order_id,
               "" if order.market == "krx" else order.order_date)
        require(key not in expected, "KIS_OPEN_ORDER_AMBIGUOUS")
        expected[key] = order

    seen = set()
    for tr_id in (_KR_OPEN, _US_OPEN):
        domestic = tr_id == _KR_OPEN
        for row in records[tr_id]:
            if domestic:
                require(row.get("excg_id_dvsn_cd") == "KRX" and row.get("ord_dvsn_cd") == "00",
                        "KIS_ORDER_MARKET_OR_TYPE_UNSUPPORTED")
                market, date = "krx", ""
            else:
                market, date = row["ovrs_excg_cd"].lower(), row["ord_dt"]
                require(row.get("tr_crcy_cd") == "USD" and row.get("loan_type_cd") in ("00", "10")
                        and row.get("rvse_cncl_dvsn_cd") == "00", "KIS_FOREIGN_ORDER_UNSUPPORTED")
            key = market, row["ord_gno_brno"], row["odno"], date
            require(key in expected and key not in seen, "KIS_OPEN_ORDER_IDENTITY_MISMATCH")
            seen.add(key)
            order = expected[key]
            require(row["pdno"] == order.symbol and row["sll_buy_dvsn_cd"] == {"buy": "02", "sell": "01"}[order.side]
                    and number(row["ord_qty" if domestic else "ft_ord_qty"]) == order.quantity
                    and number(row["ord_unpr" if domestic else "ft_ord_unpr3"]) == order.limit_price
                    and number(row["tot_ccld_qty" if domestic else "ft_ccld_qty"]) == order.filled_quantity,
                    "KIS_OPEN_ORDER_TERMS_MISMATCH")
            if domestic:
                cancelable = number(row["psbl_qty"], positive=True)
                require(cancelable <= order.remaining_quantity and (order.cancelable_quantity is None
                        or order.cancelable_quantity == cancelable), "KIS_CANCELABLE_QUANTITY_UNVERIFIED")
            else:
                require(number(row["nccs_qty"]) == order.remaining_quantity and order.cancelable_quantity is None,
                        "KIS_CANCELABLE_QUANTITY_UNVERIFIED")
    require(seen == expected.keys(), "KIS_OPEN_ORDER_COVERAGE_INCOMPLETE")


def _holdings(account, records, locked):
    positions = {(p.market, p.symbol): p for p in account.positions}
    found, seen = set(), set()
    for tr_id in (_KR_BAL, _US_BAL):
        kr = tr_id == _KR_BAL
        for row in records[tr_id]:
            if kr:
                market = "krx"
                require(number(row["loan_amt"]) == number(row["stln_slng_chgs"]) == 0, "KIS_LIABILITY_PRESENT")
            else:
                market = row["ovrs_excg_cd"].lower()
                require(market in _US_MARKETS and row.get("tr_crcy_cd") == "USD"
                        and row.get("loan_type_cd") in ("00", "10"), "KIS_FOREIGN_HOLDING_UNSUPPORTED")
            key = market, row["pdno" if kr else "ovrs_pdno"]
            require(key not in seen, "KIS_DUPLICATE_HOLDING")
            seen.add(key)
            shares = number(row["hldg_qty" if kr else "ovrs_cblc_qty"])
            sellable = number(row["ord_psbl_qty"])
            require(shares == shares.to_integral_value() and sellable + locked.get(key, 0) == shares,
                    "KIS_HOLDING_LOCK_MISMATCH")
            if not shares:
                continue
            require(key in positions and key not in found, "KIS_HOLDING_IDENTITY_MISMATCH")
            found.add(key)
            p = positions[key]
            require(p.units == shares and p.price == number(row["prpr" if kr else "now_pric2"], positive=True)
                    and p.unlisted is None and p.best_bid is None and p.best_bid_asof is None,
                    "KIS_HOLDING_MARK_MISMATCH")
    require(found == positions.keys(), "KIS_HOLDING_COVERAGE_INCOMPLETE")
    # The present-balance capture uses all countries and includes MiniStock.
    # An unexpected market, fractional holding or nonzero loan blocks the account.
    foreign, seen = set(), set()
    for row in records["present_positions"]:
        key = row["ovrs_excg_cd"].lower(), row["pdno"]
        require(key not in seen, "KIS_DUPLICATE_HOLDING")
        seen.add(key)
        shares = number(row["ccld_qty_smtl1"])
        require(key[0] in _US_MARKETS and row["buy_crcy_cd"] == "USD" and number(row["loan_rmnd"]) == 0
                and number(row["cblc_qty13"]) == shares, "KIS_FOREIGN_HOLDING_UNSUPPORTED")
        if shares:
            require(key in positions and key not in foreign and positions[key].units == shares,
                    "KIS_PRESENT_HOLDINGS_MISMATCH")
            foreign.add(key)
    require(foreign == {k for k in found if k[0] in _US_MARKETS}, "KIS_PRESENT_HOLDINGS_MISMATCH")


def _cash(account, records, summaries):
    kr, us = summaries[_KR_BAL], summaries[_CASH]
    balances = {b.currency: b for b in account.balances}
    require(set(balances) == {"KRW", "USD"}, "KIS_BOTH_CURRENCY_STATEMENTS_REQUIRED")
    require(number(kr["tot_loan_amt"]) == number(kr["tot_stln_slng_chgs"]) == number(us["tot_loan_amt"]) == 0,
            "KIS_LIABILITY_PRESENT")
    # Restricted fully settled profile. Projected settlements or available
    # foreign cash alone do not establish either ledger cash or settled cash.
    home = balances["KRW"]
    require(home.settled == home.total == number(kr["dnca_tot_amt"]) == number(kr["nxdy_excc_amt"])
            == number(kr["prvs_rcdl_excc_amt"]), "KIS_SETTLEMENT_UNVERIFIED")
    require(all(number(kr[field]) == 0 for field in ("bfdy_buy_amt", "bfdy_sll_amt", "thdt_buy_amt",
            "thdt_sll_amt", "nxdy_auto_rdpt_amt", "d2_auto_rdpt_amt")), "KIS_SETTLEMENT_UNVERIFIED")
    require(number(us["ustl_buy_amt_smtl"]) == number(us["ustl_sll_amt_smtl"]) == 0,
            "KIS_SETTLEMENT_UNVERIFIED")
    amounts = records[_CASH]
    require(len(amounts) == 1 and amounts[0].get("crcy_cd") == "USD", "KIS_FOREIGN_CASH_SCOPE_UNSUPPORTED")
    usd, row = balances["USD"], amounts[0]
    reserved = sum((o.reserved_cash for p in account.pages if p.kind == "orders" for o in p.rows
                    if o.quote_currency == "USD"), 0)
    require(number(row["frcr_buy_mgn_amt"]) == reserved and number(row["frcr_etc_mgna"]) == 0
            and usd.total == usd.settled == number(row["frcr_dncl_amt_2"]) + reserved
            and number(row["frcr_drwg_psbl_amt_1"]) <= usd.settled, "KIS_FOREIGN_CASH_MISMATCH")


def collect_kis(source, *, statement: AccountBundle, review: KisStatementReview, now,
                max_pages: int = 256) -> KisCollection:
    """Replay seven TRs across nine explicit query scopes, reconcile the reviewed E2 bundle, retain original bytes.

    The source implements read_page(tr_id, params) over an offline capture.
    The result is available only if every transaction, header, checkpoint, clock
    and account reconciliation agrees. The manifest binds the capture to the
    reviewed statement. An operating account still needs the external reviewer.
    """
    try:
        with localcontext() as ctx:
            ctx.prec = 512
            ctx.traps[Inexact] = True
            require(type(statement) is AccountBundle and len(statement.accounts) == 1
                    and type(review) is KisStatementReview, "KIS_REVIEWED_STATEMENT_REQUIRED")
            require(type(max_pages) is int and 9 <= max_pages <= 2000, "KIS_ARCHIVE_PAGE_LIMIT")
            account = statement.accounts[0]
            require(account.venue == "kis" and identifier(account.account_scope) == review.account_scope,
                    "KIS_SCOPE_MISMATCH")
            require(review.coverage == "whole-share-cash-zero-origin-complete-history-v1"
                    and digest(review.statement_sha256) == content_digest(statement), "KIS_STATEMENT_REVIEW_MISMATCH")
            digest(review.review_source_sha256)
            instant(now)
            require(instant(review.quiescent_from) <= instant(account.observed_at) <= instant(review.quiescent_until)
                    and timedelta(0) <= account.observed_at - instant(account.origin) <= timedelta(days=80),
                    "KIS_CAPTURE_COVERAGE_UNSUPPORTED")
            build_observation(statement, now=now)
            require({d.market for d in account.trade_dates} == {"krx", *_US_MARKETS}, "KIS_MARKET_DATES_REQUIRED")
            pages, rows, summaries = _capture(source, account, review, max_pages)
            _holdings(account, rows, _orders(account, rows))
            _cash(account, rows, summaries)
            manifest = content_digest((review, tuple((p.response_tr_id, p.response_tr_cont, p.receipt.params,
                p.receipt.account_scope, p.receipt.received_at, p.receipt.server_time, p.receipt.sha256) for p in pages)))
            # Preserve the source binding when a caller passes only the bundle to E2.
            # The manifest includes the reviewed statement digest (and thus every
            # original page digest), all raw body digests and both header values.
            bound_pages = tuple(EvidencePage(kind=p.kind, cursor=p.cursor, next_cursor=p.next_cursor,
                start=p.start, end=p.end, rows=p.rows, source_sha256=manifest) for p in account.pages)
            values = {f.name: getattr(account, f.name) for f in fields(AccountEvidence) if f.name != "pages"}
            bound = AccountBundle(accounts=(AccountEvidence(**values, pages=bound_pages),),
                                  risk_baseline=statement.risk_baseline)
            return KisCollection(bundle=bound, pages=tuple(pages), review=review, manifest_sha256=manifest)
    except EvidenceError:
        raise
    except (ValueError, TypeError, LookupError, AttributeError, ArithmeticError, OSError):
        raise EvidenceError("KIS_ARCHIVE_SCHEMA_INVALID") from None
