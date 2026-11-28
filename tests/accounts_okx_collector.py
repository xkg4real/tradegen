"""Offline v5 receipts. All account identifiers, prices and fills are synthetic."""
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import hashlib
import json

from execution_accounts.collector import CoverageEvidence, SourceReceipt
from execution_accounts.model import CashAmount, FxRate, RiskBaseline, content_digest
from execution_accounts.okx_collector import OkxOpeningAnchor, collect_okx
from execution_accounts.provider import EvidenceError, assess_bundle, build_observation

D = Decimal
NOW = datetime(2026, 11, 28, 3, tzinfo=timezone.utc)
ORIGIN = NOW - timedelta(minutes=45)
FILL_TIME = NOW - timedelta(minutes=5)
SHA = "a" * 64
SCOPE = "fixture-spot"
CONFIG = "/api/v5/account/config"
BALANCE = "/api/v5/account/balance"
PENDING = "/api/v5/trade/orders-pending"
HISTORY = "/api/v5/trade/orders-history"
FILLS = "/api/v5/trade/fills"
BILLS = "/api/v5/account/bills"
TICKER = "/api/v5/market/ticker"


def ms(at):
    return str(int(at.timestamp()) * 1000)


def balance(ccy, amount, avail, frozen):
    return {"ccy": ccy, "cashBal": amount, "eq": amount, "availBal": avail, "frozenBal": frozen,
            "liab": "0", "autoLendStatus": "off", "autoLendMtAmt": ""}


def fx(at, price, quote="USDT"):
    return FxRate(currency=quote, krw=D(price), asof=at, source_sha256=SHA)


def fixture(quote="USDT", *, now=NOW):
    origin, fill_time = now - timedelta(minutes=45), now - timedelta(minutes=5)
    pair = "BTC-" + quote
    order = dict(instId=pair, instType="SPOT", ordId="300", clOrdId="fixtureA", side="buy", tdMode="cash",
                 ordType="limit", state="partially_filled", sz="2", accFillSz="1", px="5", fee="-0.1", feeCcy="BTC", rebate="0",
                 cTime=ms(origin + timedelta(minutes=5)), uTime=ms(fill_time))
    fill = dict(instType="SPOT", instId=pair, ordId="300", clOrdId="fixtureA", side="buy", fillTime=ms(fill_time),
                ts=ms(fill_time), billId="611", tradeId="85", fillPx="4", fillSz="1", fee="-0.1", feeCcy="BTC")
    bill = dict(instType="SPOT", instId=pair, type="2", mgnMode="cash", ts=ms(fill_time), interest="",
                ordId="300", tradeId="85")
    return {
        CONFIG: [dict(perm="read_only", acctLv="1", enableSpotBorrow=False, autoLoan=False, ip="192.0.2.7",
                      uid="1001", mainUid="1001", type="0")],
        BALANCE: [dict(details=[balance(quote, "6", "1", "5"), balance("BTC", "0.9", "0.9", "0")])],
        PENDING: [order], HISTORY: [], FILLS: [fill],
        BILLS: [dict(bill, ccy=quote, balChg="-4", billId="612"), dict(bill, ccy="BTC", balChg="0.9", billId="611")],
        TICKER: [dict(instId=pair, instType="SPOT", bidPx="5", ts=ms(now))],
        "/api/v5/account/positions": [], "/api/v5/asset/balances": [], "/api/v5/finance/savings/balance": [],
        "/api/v5/finance/flexible-loan/loan-info": [], "/api/v5/trade/orders-algo-pending": [],
        "/api/v5/asset/asset-valuation": [{"details": {"funding": "0", "earn": "0"}}],
        "/api/v5/asset/deposit-history": [], "/api/v5/asset/withdrawal-history": [],
    }


class Archive:
    account_scope = SCOPE

    def __init__(self, rows, *, mutate=None, receipt_mutator=None, now=NOW):
        self.rows, self.calls, self.now = rows, [], now
        self.mutate, self.receipt_mutator = mutate, receipt_mutator

    def fetch(self, path, params):
        rows = deepcopy(self.rows[path])
        self.calls.append((path, params))
        cursor = dict(params).get("after")
        if "limit" in dict(params):
            key = {HISTORY: "ordId", PENDING: "ordId", BILLS: "billId", FILLS: "billId"}.get(path, "ts")
            rows = [r for r in rows if cursor is None or int(r[key]) < int(cursor)][:1]
        if self.mutate:
            rows = self.mutate(self, path, params, rows)
        raw = json.dumps({"code": "0", "data": rows}).encode()
        receipt = SourceReceipt(account_scope=self.account_scope, path=path, params=params, raw_body=raw,
                                sha256=hashlib.sha256(raw).hexdigest(), received_at=self.now, server_time=self.now)
        return self.receipt_mutator(receipt) if self.receipt_mutator else receipt


def kwargs(quote="USDT", *, now=NOW):
    origin, fill_time = now - timedelta(minutes=45), now - timedelta(minutes=5)
    anchor = OkxOpeningAnchor(account_scope=SCOPE, uid_sha256=content_digest("1001"), origin=origin,
                              opening_cash=(CashAmount(currency=quote, amount=D("10")),),
                              inventory_and_open_orders="verified-zero", source_sha256=SHA)
    coverage = CoverageEvidence(account_scope=SCOPE, history_from=origin, history_through=now,
                                quiescent_from=now, quiescent_until=now, source_sha256=SHA,
                                identity_binding="reviewed-credential-to-main-pocket", history_retention="reviewed-complete-since-origin",
                                transfer_scope="reviewed-no-external-flows-or-pocket-transfers", account_mode="reviewed-okx-main-cash-spot-only")
    baseline = RiskBaseline(day_start_equity=D("10000"), prior_high_watermark=D("10000"), observed_daily_loss=D("0"),
                            approved_effective_floor=None, asof=now, first_trading_day=now.date(), source_sha256=SHA)
    return dict(anchor=anchor, coverage=coverage, risk_baseline=baseline, clock=lambda: now, execution_quote=quote,
                current_fx=(fx(now, "1000", quote),), fill_fx=(fx(fill_time, "995", quote),))


def refused(source, reason, **options):
    args = kwargs()
    args.update(options)
    try:
        collect_okx(source, **args)
    except EvidenceError as exc:
        assert exc.code == reason, (exc.code, reason)
    else:
        raise AssertionError("Expected evidence refusal: " + reason)


def test_partial_order_fill_fee_and_short_cursor_pages_reconcile_for_each_quote():
    for quote in ("USDT", "USDC"):
        source = Archive(fixture(quote))
        out = collect_okx(source, **kwargs(quote))
        obs = build_observation(out.bundle, now=NOW)
        assessment = assess_bundle(out.bundle, now=NOW)
        assert assessment.account_evidence_ready and not assessment.execution_ready
        assert obs.risk.equity == D(10500)
        assert obs.fills[0].quantity == D(1) and obs.fills[0].fee_amount == D("0.1")
        assert obs.fills[0].quote_krw == D("995") and obs.reconciled_client_ids == frozenset({"fixtureA"})
        assert obs.positions.exposure["okx"].reservations == {"fixtureA": 5000}
        assert len(out.manifest_sha256) == 64 and len(out.receipts) == len(source.calls)
        assert [dict(p).get("after") for path, p in source.calls if path == BILLS] == [None, "612", "611"]


def test_flat_opening_and_terminal_fill_reconcile_without_assuming_cash_peg():
    rows = fixture()
    order, = rows[PENDING]
    rows[HISTORY] = [dict(order, state="filled", sz="1")]
    rows[PENDING] = []
    rows[BALANCE][0]["details"][0] = balance("USDT", "6", "6", "0")
    out = collect_okx(Archive(rows), **kwargs())
    assert build_observation(out.bundle, now=NOW).positions.exposure["okx"].reservations == {}
    rows = fixture()
    rows[PENDING], rows[FILLS], rows[BILLS] = [], [], []
    rows[BALANCE] = [{"details": [balance("USDT", "10", "10", "0")]}]
    out = collect_okx(Archive(rows), **(kwargs() | {"fill_fx": ()}))
    assert not build_observation(out.bundle, now=NOW).fills


def test_unverified_identity_cash_mode_or_other_pockets_refuse():
    for changes in (dict(perm="read_only,trade"), dict(type="2"), dict(uid="1002", mainUid="1002"),
                    dict(enableSpotBorrow=True), dict(autoLoan=True), dict(ip="")):
        rows = fixture()
        rows[CONFIG][0].update(changes)
        refused(Archive(rows), "OKX_MAIN_READONLY_SPOT_REQUIRED")
    for path, value, expected in (
        ("/api/v5/account/positions", [{}], "OKX_DERIVATIVE_OR_MARGIN_POSITION"),
        ("/api/v5/asset/balances", [dict(bal="1", frozenBal="0", availBal="1")], "OKX_FUNDING_POCKET_NOT_EMPTY"),
        ("/api/v5/trade/orders-algo-pending", [{}], "OKX_ALGO_UNSUPPORTED"),
        ("/api/v5/asset/asset-valuation", [{"details": {"funding": "0", "earn": "0", "classic": "1"}}],
         "OKX_OTHER_POCKET_EXPOSURE"),
        ("/api/v5/finance/flexible-loan/loan-info", [dict(loanData=[{}])], "OKX_LOAN_UNSUPPORTED"),
        ("/api/v5/asset/withdrawal-history", [dict(ts=ms(NOW), state="2")], "OKX_EXTERNAL_FLOW_OR_PENDING_MOVEMENT"),
        ("/api/v5/asset/deposit-history", [dict(ts=ms(ORIGIN-timedelta(days=1)), state="0")], "OKX_EXTERNAL_FLOW_OR_PENDING_MOVEMENT"),
    ):
        rows = fixture()
        rows[path] = value
        refused(Archive(rows), expected)


def test_no_partial_or_wrong_history_pocket_or_scope_proof():
    args = kwargs()
    for prop, change, code in (("anchor", dict(account_scope="different"), "OKX_ACCOUNT_SCOPE_MISMATCH"),
                               ("coverage", dict(history_through=ORIGIN), "OKX_CAPTURE_WINDOW_INCOMPLETE"),
                               ("coverage", dict(identity_binding=""), "OKX_COVERAGE_INCOMPLETE"),
                               ("coverage", dict(transfer_scope=""), "OKX_COVERAGE_INCOMPLETE"),
                               ("anchor", dict(inventory_and_open_orders="unchecked"), "OKX_CASH_ANCHOR_REQUIRED")):
        refused(Archive(fixture()), code, **{prop: replace(args[prop], **change)})
    origin = NOW - timedelta(hours=2)
    refused(Archive(fixture()), "OKX_CANCELED_ORDER_RETENTION_EXCEEDED", anchor=replace(args["anchor"], origin=origin),
            coverage=replace(args["coverage"], history_from=origin))


def test_missing_terminal_cursor_duplicate_page_request_bound_and_receipt_tamper():
    def repeat(source, path, params, rows):
        return source.rows[PENDING] if path == PENDING and "after" in dict(params) else rows
    refused(Archive(fixture(), mutate=repeat), "OKX_PAGINATION_NOT_DESCENDING")
    refused(Archive(fixture()), "OKX_CAPTURE_REQUEST_LIMIT", max_requests=2)
    for change, expected in ((dict(account_scope="different"), "OKX_RECEIPT_SCOPE_MISMATCH"),
                             (dict(params=(("after", "123"),)), "OKX_RECEIPT_SCOPE_MISMATCH"),
                             (dict(sha256="0"*64), "COLLECTOR_RECEIPT_DIGEST_MISMATCH"),
                             (dict(server_time=ORIGIN), "OKX_RECEIPT_TIME_INVALID")):
        refused(Archive(fixture(), receipt_mutator=lambda r: replace(r, **change)), expected)
    rows = fixture()
    del rows[HISTORY]
    refused(Archive(rows), "OKX_ARCHIVE_READ_FAILED")


def test_stale_or_wrong_marks_and_unmatched_fx_or_changed_account_refuse():
    rows = fixture()
    rows[TICKER][0]["ts"] = ms(NOW - timedelta(seconds=31))
    refused(Archive(rows), "EVIDENCE_STALE_OR_FUTURE")
    rows = fixture()
    rows[TICKER][0]["instId"] = "ETH-USDT"
    refused(Archive(rows), "OKX_MARKET_SCOPE_MISMATCH")
    refused(Archive(fixture()), "OKX_EXECUTION_FX_REQUIRED", fill_fx=(fx(NOW, "995"),))
    refused(Archive(fixture()), "SPENDABLE_CURRENCY_MISSING", current_fx=(fx(NOW, "1000", "USDC"),))
    def changed(source, path, params, rows):
        if path == BALANCE and source.calls.count((path, params)) == 2:
            rows[0]["details"][0] = balance("USDT", "7", "2", "5")
        return rows
    refused(Archive(fixture(), mutate=changed), "OKX_ACCOUNT_CHANGED_DURING_CAPTURE")


def test_fill_order_cash_and_bill_crosschecks_reject_inconsistent_archives():
    for path, key, value, expected in (
        (PENDING, "tdMode", "cross", "OKX_CASH_LIMIT_ORDER_REQUIRED"),
        (PENDING, "instType", "SWAP", "OKX_SPOT_INSTRUMENT_REQUIRED"),
        (PENDING, "state", "filled", "OKX_ORDER_STATE_INVALID"),
        (PENDING, "fee", "-0.2", "OKX_ORDER_FEE_MISMATCH"),
        (PENDING, "rebate", "0.1", "OKX_ORDER_REBATE_UNSUPPORTED"),
        (FILLS, "ordId", "299", "OKX_FILL_UNMATCHED_OR_OUTSIDE_WINDOW"),
        (FILLS, "fee", "0.1", "OKX_REBATE_OR_THIRD_CURRENCY_FEE"),
        (FILLS, "feeCcy", "EUR", "OKX_REBATE_OR_THIRD_CURRENCY_FEE"),
        (FILLS, "fillPx", "5.1", "OKX_FILL_LIMIT_MISMATCH"),
        (BILLS, "balChg", "-3", "OKX_BILL_FILL_MISMATCH"),
        (BILLS, "type", "1", "OKX_NONTRADE_BILL_UNSUPPORTED"),
    ):
        rows = fixture()
        rows[path][0][key] = value
        refused(Archive(rows), expected)
    for balance_row, code in ((balance("USDT", "8", "3", "5"), "CASH_RECONCILIATION_MISMATCH"),
                              (balance("USDT", "6", "6", "0"), "OKX_UNEXPLAINED_FROZEN_BALANCE")):
        rows = fixture()
        rows[BALANCE][0]["details"][0] = balance_row
        refused(Archive(rows), code)
    rows = fixture()
    rows[BILLS].pop()
    refused(Archive(rows), "OKX_BILL_FILL_MISMATCH")


def test_completed_sell_quote_fee_and_base_fee_buy_preserve_exact_fifo():
    rows = fixture()
    buy, = rows[PENDING]
    bought = dict(buy, sz="1", state="filled")
    sell_at = FILL_TIME + timedelta(minutes=1)
    sell = dict(bought, side="sell", ordId="301", clOrdId="fixtureB", sz="0.9", accFillSz="0.9",
                px="6", fee="-0.4", feeCcy="USDT", cTime=ms(sell_at), uTime=ms(sell_at))
    sale = dict(rows[FILLS][0], ordId="301", tradeId="86", billId="614", side="sell", fillTime=ms(sell_at),
                ts=ms(sell_at), clOrdId="fixtureB", fillSz="0.9", fillPx="6", fee="-0.4", feeCcy="USDT")
    bill = dict(rows[BILLS][0], ordId="301", tradeId="86", ts=ms(sell_at))
    rows[BILLS][:0] = [dict(bill, ccy="BTC", balChg="-0.9", billId="614"),
                       dict(bill, ccy="USDT", balChg="5", billId="613")]
    rows[HISTORY], rows[PENDING] = [sell, bought], []
    rows[FILLS].insert(0, sale)
    rows[BALANCE] = [{"details": [balance("USDT", "11", "11", "0")]}]
    args = kwargs()
    args["fill_fx"] += (fx(sell_at, "1000"),)
    out = collect_okx(Archive(rows), **args)
    obs = build_observation(out.bundle, now=NOW)
    assert obs.risk.equity == D("11000") and obs.risk.current_day_realized_net_profit == D("1020")
    assert len(obs.fills) == 2 and not obs.holdings


def test_output_manifest_recomputes_and_binds_actual_raw_bytes_and_external_fx_references():
    args = kwargs()
    original = collect_okx(Archive(fixture()), **args)
    def whitespace(r):
        raw = r.raw_body + b" "
        return replace(r, raw_body=raw, sha256=hashlib.sha256(raw).hexdigest())
    changed = collect_okx(Archive(fixture(), receipt_mutator=whitespace), **args)
    other_fx = (replace(args["fill_fx"][0], source_sha256="b" * 64),)
    reissued = collect_okx(Archive(fixture()), **(args | {"fill_fx": other_fx}))
    assert len({original.manifest_sha256, changed.manifest_sha256, reissued.manifest_sha256}) == 3
    for output in (original, changed, reissued):
        acct = output.bundle.accounts[0]
        receipt_records = tuple((r.path, r.params, r.account_scope, r.received_at, r.server_time, r.sha256)
                                for r in output.receipts)
        assert output.manifest_sha256 == content_digest((output.anchor, output.coverage, output.bundle.risk_baseline,
                              acct.execution_quote, acct.fx, output.fill_fx, receipt_records))
        assert all(p.source_sha256 == output.manifest_sha256 for p in acct.pages)
        assert build_observation(output.bundle, now=NOW) == build_observation(original.bundle, now=NOW)
