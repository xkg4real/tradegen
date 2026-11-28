"""KIS original response shapes under a stub archive. No HTTP or owner state."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal as D
import hashlib
import json

from execution_accounts.collector import SourceReceipt
from execution_accounts.kis_collector import KisArchivePage, KisStatementReview, collect_kis
from execution_accounts.model import (
    AccountBundle, AccountEvidence, AccountRestrictions, BrokerOrder, CashAmount, CashBalance,
    EvidencePage, ExternalFlow, FxRate, MarketTradeDate, Position, RiskBaseline, content_digest,
)
from execution_accounts.provider import EvidenceError, assess_bundle, build_observation
from execution_control.risk import Fill


NOW = datetime(2026, 11, 9, 1, 30, tzinfo=timezone.utc)
ORIGIN = NOW - timedelta(days=7)
TRADE = ORIGIN + timedelta(days=2)
SCOPE, HASH = "kis-fixture", "0" * 64


def _bundle():
    orders, fills, positions = [], [], []
    for market, symbol, ccy, price, fx, oid in (
        ("krx", "000001", "KRW", 23, 1, "1"), ("nyse", "ABC", "USD", 5, 1200, "2")
    ):
        identity = dict(market=market, symbol=symbol, order_id=oid, order_date="20261104", broker_org_id="012",
                        quantity=D(2), side="buy", quote_currency=ccy)
        orders.append(BrokerOrder(**identity, client_id="", filled_quantity=D(2), remaining_quantity=D(0),
                                  status="filled", limit_price=D(price), reserved_cash=D(0)))
        fills.append(Fill(**identity, fill_id=oid, venue="kis", account_scope=SCOPE,
                          executed_at=TRADE if market == "krx" else TRADE + timedelta(hours=15),
                          price=D(price), quote_krw=D(fx), fee_currency=ccy, fee_amount=D(1)))
        positions.append(Position(market=market, symbol=symbol, base_currency=symbol, quote_currency=ccy,
                                  units=D(2), price=D(price + 1), asof=NOW))
    flows = (ExternalFlow(flow_id="deposit-a", currency="KRW", kind="deposit", amount=D(10), effective_at=TRADE),)
    pages = tuple(EvidencePage(kind=kind, cursor=None, next_cursor=None, start=ORIGIN, end=NOW,
                               rows=tuple(rows), source_sha256=HASH)
                  for kind, rows in (("fills", fills), ("orders", orders), ("flows", flows)))
    evidence = AccountEvidence(venue="kis", account_scope=SCOPE, execution_quote="KRW", origin=ORIGIN,
        opening_cash=tuple(CashAmount(currency=ccy, amount=D(val)) for ccy, val in (("KRW", 100), ("USD", 30))),
        opening_source_sha256=HASH, balances=tuple(CashBalance(currency=ccy, settled=D(val), total=D(val))
        for ccy, val in (("KRW", 63), ("USD", 19))), positions=tuple(positions), pages=pages,
        fx=tuple(FxRate(currency=ccy, krw=D(val), asof=NOW, source_sha256=HASH)
                 for ccy, val in (("KRW", 1), ("USD", 1200))),
        trade_dates=tuple(MarketTradeDate(market=m, trade_date="20261109", asof=NOW, source_sha256=HASH)
                          for m in ("krx", "nyse", "nasd", "amex")), restrictions=AccountRestrictions(
        asof=NOW, source_sha256=HASH, cash_mode="cash", borrowing_enabled=False, auto_loan=False, liabilities=()),
        observed_at=NOW, server_time=NOW)
    return AccountBundle(accounts=(evidence,), risk_baseline=RiskBaseline(day_start_equity=D(100),
        prior_high_watermark=D(100), observed_daily_loss=D(0), approved_effective_floor=None,
        first_trading_day=TRADE.date(), asof=NOW, source_sha256=HASH))


def _review(bundle):
    return KisStatementReview(account_scope=SCOPE, statement_sha256=content_digest(bundle), review_source_sha256=HASH,
        coverage="whole-share-cash-zero-origin-complete-history-v1",
        quiescent_from=NOW - timedelta(seconds=5), quiescent_until=NOW)


def _raw():
    kr_cash = dict(tot_loan_amt="0", tot_stln_slng_chgs="0", dnca_tot_amt="63", nxdy_excc_amt="63",
                   prvs_rcdl_excc_amt="63", bfdy_buy_amt="0", bfdy_sll_amt="0", thdt_buy_amt="0",
                   thdt_sll_amt="0", nxdy_auto_rdpt_amt="0", d2_auto_rdpt_amt="0")
    kr_hold = dict(pdno="000001", loan_amt="0", stln_slng_chgs="0", hldg_qty="2", ord_psbl_qty="2", prpr="24")
    us_hold = dict(ovrs_pdno="ABC", ovrs_excg_cd="NYSE", tr_crcy_cd="USD", loan_type_cd="10",
                   ovrs_cblc_qty="2", ord_psbl_qty="2", now_pric2="6")
    identity = dict(ord_dt="20261104", ord_gno_brno="012", sll_buy_dvsn_cd="02")
    kr_ord = dict(**identity, pdno="000001", odno="1", ord_qty="2", ord_unpr="23", tot_ccld_qty="2",
                  rmn_qty="0", tot_ccld_amt="46", cncl_yn="N", cncl_cfrm_qty="0", rjct_qty="0",
                  excg_id_dvsn_Cd="KRX", ord_dvsn_cd="00")
    us_ord = dict(**identity, pdno="ABC", odno="2", ft_ord_qty="2", ft_ord_unpr3="5", ft_ccld_qty="2",
                  nccs_qty="0", ft_ccld_amt3="10", ovrs_excg_cd="NYSE", tr_crcy_cd="USD", loan_type_cd="10",
                  rvse_cncl_dvsn="00", rjct_rson="")
    return {
        "TTTC8434R": dict(output1=[kr_hold], output2=[kr_cash]),
        "TTTS3012R": dict(output1=[us_hold]),
        "TTTC0081R": dict(output1=[kr_ord]),
        "TTTS3035R": dict(output=[us_ord]),
        "TTTC0084R": dict(output=[]),
        "TTTS3018R": dict(output=[]),
        "CTRP6504R": dict(output1=[dict(pdno="ABC", ovrs_excg_cd="NYSE", buy_crcy_cd="USD", cblc_qty13="2",
            ccld_qty_smtl1="2", loan_rmnd="0")], output2=[dict(crcy_cd="USD", frcr_dncl_amt_2="19",
            frcr_buy_mgn_amt="0", frcr_etc_mgna="0", frcr_drwg_psbl_amt_1="19")],
            output3=dict(ustl_buy_amt_smtl="0", ustl_sll_amt_smtl="0", tot_loan_amt="0")),
    }


class Archive:
    def __init__(self, *, bodies=None, transform=None):
        self.bodies = _raw() if bodies is None else bodies
        self.transform = transform
        self.calls = []

    def read_page(self, tr_id, params):
        self.calls.append((tr_id, dict(params)))
        body = self.bodies[tr_id]
        if tr_id == "TTTS3018R":
            market = dict(params)["OVRS_EXCG_CD"]
            body = dict(output=[row for row in body["output"] if row["ovrs_excg_cd"] == market])
        flag = "E"
        if tr_id == "TTTS3012R" and not dict(params)["tr_cont"]:
            body = dict(output1=[], ctx_area_fk200="condition", ctx_area_nk200="token")
            flag = "F"
        encoded = json.dumps({"rt_cd": "0", **body}).encode()
        receipt = SourceReceipt(path=tr_id, params=params, account_scope=SCOPE, received_at=NOW, server_time=NOW,
                                raw_body=encoded, sha256=hashlib.sha256(encoded).hexdigest())
        page = KisArchivePage(receipt=receipt, response_tr_cont=flag, response_tr_id=tr_id)
        return self.transform(page) if self.transform else page


def _run(source=None, *, bundle=None, review=None, max_pages=256):
    statement = bundle or _bundle()
    return collect_kis(source or Archive(), statement=statement, review=review or _review(statement),
                       now=NOW, max_pages=max_pages)


def _reject(code, **kwargs):
    try:
        _run(**kwargs)
    except EvidenceError as exc:
        assert exc.code == code, (exc.code, code)
    else:
        raise AssertionError("expected KIS evidence refusal")


def test_domestic_and_us_holdings_fills_fees_and_deposit_reconcile_without_order_permission():
    source = Archive()
    result = _run(source)
    assert len(result.pages) == 10 and len(result.manifest_sha256) == 64
    valid = assess_bundle(result.bundle, now=NOW)
    assert valid.account_evidence_ready and not valid.execution_ready and valid.fill_count == 2
    obs = build_observation(result.bundle, now=NOW)
    assert obs.settled_cash_krw[("kis", SCOPE)] == 63
    assert obs.positions.equity_krw == 63 + 2 * 24 + (19 + 2 * 6) * 1200
    assert source.calls[2][1]["CTX_AREA_NK200"] == "token" and source.calls[2][1]["tr_cont"] == "N"
    assert source.calls[3][1]["INQR_END_DT"] == "20261109" and source.calls[3][1]["CCLD_DVSN"] == "00"
    assert source.calls[4][1]["ORD_END_DT"] == "20261108" and source.calls[4][1]["CCLD_NCCS_DVSN"] == "00"
    assert [filters["OVRS_EXCG_CD"] for tr, filters in source.calls if tr == "TTTS3018R"] == ["NASD", "NYSE", "AMEX"]
    assert all(p.receipt.raw_body and "CANO" not in dict(p.receipt.params) for p in result.pages)


def test_receipt_header_hash_and_scope_or_whole_page_bound_fail_closed():
    for transform, code in (
        (lambda p: replace(p, response_tr_id="unknown"), "KIS_RECEIPT_BINDING_MISMATCH"),
        (lambda p: replace(p, receipt=replace(p.receipt, account_scope="another")), "KIS_RECEIPT_BINDING_MISMATCH"),
        (lambda p: replace(p, receipt=replace(p.receipt, params=())), "KIS_RECEIPT_BINDING_MISMATCH"),
        (lambda p: replace(p, receipt=replace(p.receipt, sha256=HASH)), "COLLECTOR_RECEIPT_DIGEST_MISMATCH"),
        (lambda p: replace(p, response_tr_cont=""), "KIS_TERMINAL_HEADER_REQUIRED"),
        (lambda p: replace(p, receipt=replace(p.receipt, received_at=NOW - timedelta(seconds=31))),
         "KIS_CAPTURE_TIME_MISMATCH"),
        (lambda p: replace(p, receipt=replace(p.receipt, server_time=NOW + timedelta(seconds=61))),
         "KIS_CAPTURE_TIME_MISMATCH"),
    ):
        _reject(code, source=Archive(transform=transform))
    _reject("KIS_ARCHIVE_PAGE_LIMIT", max_pages=9)


def test_missing_cursor_loop_and_body_only_continuation_refused():
    _reject("KIS_CURSOR_INCOMPLETE_OR_REPEATED", source=Archive(transform=lambda p: replace(p, response_tr_cont="M")))
    bodies = _raw()
    bodies["TTTS3012R"].update(ctx_area_nk200="token", ctx_area_fk200="condition")
    def loop(p):
        return replace(p, response_tr_cont="M") if p.response_tr_id == "TTTS3012R" else p
    _reject("KIS_CURSOR_INCOMPLETE_OR_REPEATED", source=Archive(bodies=bodies, transform=loop))
    bodies["TTTC8434R"]["tr_cont"] = "D"
    _reject("KIS_TERMINAL_HEADER_REQUIRED", source=Archive(bodies=bodies,
            transform=lambda p: replace(p, response_tr_cont="")))


def test_unsettled_ambiguous_or_unsupported_cash_and_positions_hold_reconciliation():
    for tr, group, field, value, code in (
        ("TTTC8434R", "output2", "prvs_rcdl_excc_amt", "65", "KIS_SETTLEMENT_UNVERIFIED"),
        ("TTTC8434R", "output2", "bfdy_sll_amt", "1", "KIS_SETTLEMENT_UNVERIFIED"),
        ("CTRP6504R", "output3", "ustl_buy_amt_smtl", "1", "KIS_SETTLEMENT_UNVERIFIED"),
        ("CTRP6504R", "output3", "tot_loan_amt", "1", "KIS_LIABILITY_PRESENT"),
        ("CTRP6504R", "output2", "frcr_dncl_amt_2", "21", "KIS_FOREIGN_CASH_MISMATCH"),
        ("CTRP6504R", "output2", "crcy_cd", "HKD", "KIS_FOREIGN_CASH_SCOPE_UNSUPPORTED"),
        ("CTRP6504R", "output1", "pdno", "NEW", "KIS_PRESENT_HOLDINGS_MISMATCH"),
        ("TTTS3012R", "output1", "ovrs_excg_cd", "SEHK", "KIS_FOREIGN_HOLDING_UNSUPPORTED"),
        ("TTTC8434R", "output1", "ord_psbl_qty", "1", "KIS_HOLDING_LOCK_MISMATCH"),
        ("TTTS3012R", "output1", "now_pric2", "7", "KIS_HOLDING_MARK_MISMATCH"),
    ):
        bodies = _raw()
        target = bodies[tr][group]
        (target[0] if type(target) is list else target)[field] = value
        _reject(code, source=Archive(bodies=bodies))


def test_partial_or_ambiguous_order_state_and_extra_or_missing_history_are_refused():
    for tr, group, field, value, code in (
        ("TTTC0081R", "output1", "excg_id_dvsn_Cd", "NXT", "KIS_ORDER_MARKET_OR_TYPE_UNSUPPORTED"),
        ("TTTS3035R", "output", "ft_ccld_amt3", "10.1", "KIS_ORDER_ECONOMICS_MISMATCH"),
        ("TTTS3035R", "output", "ord_dt", "20261103", "KIS_ORDER_IDENTITY_MISMATCH"),
        ("TTTS3035R", "output", "rvse_cncl_dvsn", "02", "KIS_FOREIGN_ORDER_UNSUPPORTED"),
    ):
        bodies = _raw()
        bodies[tr][group][0][field] = value
        _reject(code, source=Archive(bodies=bodies))
    bodies = _raw()
    bodies["TTTC0081R"]["output1"] = []
    _reject("KIS_ORDER_COVERAGE_INCOMPLETE", source=Archive(bodies=bodies))


def test_independent_statement_hash_fees_flow_and_provenance_are_required():
    bundle = _bundle()
    _reject("KIS_STATEMENT_REVIEW_MISMATCH", review=replace(_review(bundle), statement_sha256=HASH))
    _reject("KIS_CAPTURE_COVERAGE_UNSUPPORTED", review=replace(_review(bundle), quiescent_until=ORIGIN))
    account = bundle.accounts[0]
    pages = tuple(replace(p, rows=(), page_sha256="") if p.kind == "flows" else p for p in account.pages)
    _reject("CASH_RECONCILIATION_MISMATCH", bundle=replace(bundle, accounts=(replace(account, pages=pages),)))
    _reject("KIS_MARKET_DATES_REQUIRED", bundle=replace(bundle, accounts=(replace(account,
        trade_dates=tuple(d for d in account.trade_dates if d.market != "amex")),)))


def test_manifest_binds_separate_headers_and_retains_all_bytes():
    original = _run()
    changed = _run(Archive(transform=lambda p: replace(p, response_tr_cont="D")
                           if p.response_tr_cont == "E" else p))
    assert content_digest(changed.bundle) != content_digest(original.bundle)
    assert all(p.source_sha256 == changed.manifest_sha256 for p in changed.bundle.accounts[0].pages)
    assert changed.review == original.review
    assert changed.manifest_sha256 != original.manifest_sha256
    assert [p.receipt.sha256 for p in changed.pages] == [p.receipt.sha256 for p in original.pages]


def test_open_us_buy_and_domestic_sell_reconcile_cash_and_share_reservations():
    bundle = _bundle()
    account = bundle.accounts[0]
    kr = BrokerOrder(market="krx", symbol="000001", order_id="3", order_date="20261109", broker_org_id="012",
                     client_id="fixture-sell", quote_currency="KRW", quantity=D(1), filled_quantity=D(0),
                     remaining_quantity=D(1), limit_price=D(30), reserved_cash=D(0), side="sell", status="open")
    us = replace(kr, market="nyse", symbol="ABC", order_id="4", order_date="20261106", client_id="fixture-buy",
                 quote_currency="USD", limit_price=D(6), reserved_cash=D(6), side="buy")
    pages = tuple(replace(p, rows=(*p.rows, kr, us), page_sha256="") if p.kind == "orders" else p
                  for p in account.pages)
    bundle = replace(bundle, accounts=(replace(account, pages=pages),))
    raw = _raw()
    raw["TTTC8434R"]["output1"][0]["ord_psbl_qty"] = "1"
    kr_rows, us_rows = raw["TTTC0081R"]["output1"], raw["TTTS3035R"]["output"]
    kr_rows.append(dict(kr_rows[0], ord_dt="20261109", odno="3", ord_qty="1", ord_unpr="30", tot_ccld_qty="0",
                        rmn_qty="1", tot_ccld_amt="0", sll_buy_dvsn_cd="01"))
    us_rows.append(dict(us_rows[0], ord_dt="20261106", odno="4", ft_ord_qty="1", ft_ord_unpr3="6", ft_ccld_qty="0",
                        nccs_qty="1", ft_ccld_amt3="0"))
    raw["TTTC0084R"]["output"] = [dict(kr_rows[-1], excg_id_dvsn_cd="KRX", psbl_qty="1")]
    raw["TTTS3018R"]["output"] = [dict(us_rows[-1], rvse_cncl_dvsn_cd="00")]
    raw["CTRP6504R"]["output2"][0].update(frcr_dncl_amt_2="13", frcr_buy_mgn_amt="6", frcr_drwg_psbl_amt_1="13")
    result = _run(Archive(bodies=raw), bundle=bundle)
    exposure = build_observation(result.bundle, now=NOW).positions.exposure["kis"]
    assert exposure.promised_sell_units["000001"] == 1
    assert exposure.reservations["fixture-buy"] == 7200
    pending = raw["TTTS3018R"]["output"].pop()
    _reject("KIS_OPEN_ORDER_COVERAGE_INCOMPLETE", source=Archive(bodies=raw), bundle=bundle)
    raw["TTTS3018R"]["output"].extend([pending, pending])
    _reject("KIS_OPEN_ORDER_IDENTITY_MISMATCH", source=Archive(bodies=raw), bundle=bundle)
    raw["TTTS3018R"]["output"].pop()
    raw["CTRP6504R"]["output2"][0]["frcr_buy_mgn_amt"] = "0"
    _reject("KIS_FOREIGN_CASH_MISMATCH", source=Archive(bodies=raw), bundle=bundle)


def test_open_order_surface_can_reveal_pending_order_missing_from_both_ledgers():
    raw = _raw()
    raw["TTTS3018R"]["output"] = [dict(raw["TTTS3035R"]["output"][0], odno="453", rvse_cncl_dvsn_cd="00")]
    _reject("KIS_OPEN_ORDER_IDENTITY_MISMATCH", source=Archive(bodies=raw))
    # A broker page still advertising another page is incomplete under the
    # workbook's no-tr_cont contract for TTTS3018R.
    archive = Archive(transform=lambda p: replace(p, response_tr_cont="M") if p.response_tr_id == "TTTS3018R" else p)
    _reject("KIS_TERMINAL_HEADER_REQUIRED", source=archive)
