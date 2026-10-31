"""Synthetic exact exchange receipts: no network, credentials, files or owner state."""
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import tempfile
from unittest.mock import patch

from execution.transport import Answer
from execution_accounts.collector import CoverageEvidence, OpeningAnchor, SourceReceipt, TradeFeeEvidence
from execution_accounts.model import RiskBaseline
from execution_accounts.provider import EvidenceError, assess_bundle, build_observation
from execution_accounts.upbit_collector import E1UpbitSource, _Capture, collect_upbit

D = Decimal
NOW = datetime(2026, 10, 31, 1, tzinfo=timezone.utc)
ORIGIN = NOW-timedelta(days=1)
SHA = "a"*64
SCOPE = "synthetic-main-pocket"


def receipt(path, params=(), body=None, *, raw=None):
    raw = json.dumps(body, separators=(",", ":")).encode() if raw is None else raw
    return SourceReceipt(path=path, params=tuple(params), account_scope=SCOPE,
        received_at=NOW, server_time=NOW, raw_body=raw, sha256=hashlib.sha256(raw).hexdigest())


def proofs():
    anchor = OpeningAnchor(account_scope=SCOPE, origin=ORIGIN, cash_krw=D("100000"), source_sha256=SHA,
        inventory_and_open_orders="verified-zero")
    coverage = CoverageEvidence(account_scope=SCOPE, source_sha256=SHA,
        history_from=ORIGIN, history_through=NOW+timedelta(seconds=30),
        quiescent_from=NOW, quiescent_until=NOW+timedelta(seconds=30),
        identity_binding="reviewed-credential-to-main-pocket", history_retention="reviewed-complete-since-origin",
        transfer_scope="reviewed-no-unreported-flows-or-pocket-transfers", account_mode="reviewed-krw-spot-cash-only")
    baseline = RiskBaseline(day_start_equity=D("100000"), prior_high_watermark=D("100000"),
        observed_daily_loss=D("0"), approved_effective_floor=None, first_trading_day=NOW.date(),
        asof=NOW, source_sha256=SHA)
    return anchor, coverage, baseline


def order_fixture():
    return dict(uuid="order-1", identifier="client-1", market="KRW-BTC", side="bid", ord_type="limit", state="done",
        created_at=(NOW-timedelta(hours=2)).isoformat(), volume="1", remaining_volume="0", executed_volume="1",
        price="10000", locked="0", paid_fee="5", trades_count=1,
        trades=[dict(uuid="fill-1", market="KRW-BTC", side="bid", price="10000", volume="1", funds="10000",
                     created_at=(NOW-timedelta(hours=1)).isoformat())])


class SyntheticSource:
    account_scope = SCOPE

    def __init__(self, *, with_order=False):
        self.calls = []
        self.detail = order_fixture() if with_order else None
        self.balances = [dict(currency="KRW", balance="89995" if with_order else "100000", locked="0")]
        if with_order:
            self.balances.append(dict(currency="BTC", balance="1", locked="0"))
        self.deposits = []; self.withdrawals = []
        self.change_balances = False

    def fetch(self, path, params):
        self.calls.append((path, params))
        if path == "/v1/accounts":
            body = deepcopy(self.balances)
            if self.change_balances and sum(p == path for p, _ in self.calls) > 1:
                body[0]["balance"] = "99999"
        elif path in ("/v1/orders/open", "/v1/orders/closed"):
            active = self.detail is not None and self.detail["state"] == "wait"
            body = [{k:v for k,v in self.detail.items() if k != "trades"}] if self.detail and (
                (path.endswith("open") and active) or (path.endswith("closed") and not active)) else []
        elif path == "/v1/order":
            body = self.detail
        elif path == "/v1/deposits":
            body = self.deposits
        elif path == "/v1/withdraws":
            body = self.withdrawals
        elif path == "/v1/ticker":
            body = [dict(market="KRW-BTC", trade_price=10000, timestamp=int(NOW.timestamp()*1000),
                         trade_timestamp=int(NOW.timestamp()*1000))]
        else:
            raise AssertionError("unexpected synthetic route")
        return receipt(path, params, deepcopy(body))


def collect(source=None, **kwargs):
    anchor, coverage, baseline = proofs()
    return collect_upbit(source or SyntheticSource(), anchor=kwargs.pop("anchor", anchor),
        coverage=kwargs.pop("coverage", coverage), risk_baseline=kwargs.pop("risk_baseline", baseline),
        clock=kwargs.pop("clock", lambda: NOW), **kwargs)


def refusal(call, code):
    try:
        call()
    except EvidenceError as exc:
        assert exc.code == code, (exc.code, code)
        return
    raise AssertionError("expected collector refusal")


def test_cash_account_requires_full_empty_history_and_preserves_exact_receipt_manifest():
    source = SyntheticSource()
    result = collect(source)
    assert len(result.bundle.accounts[0].pages) == 3
    assert len(result.receipts) == 9
    assert len(result.manifest_sha256) == 64
    assert all(hashlib.sha256(r.raw_body).hexdigest() == r.sha256 for r in result.receipts)
    status = assess_bundle(result.bundle, now=NOW)
    assert status.account_evidence_ready and not status.execution_ready
    assert build_observation(result.bundle, now=NOW).risk.equity == D("100000")
    assert all(("states[]", "watch") in params for path, params in source.calls if path.endswith("/open"))


def test_order_detail_single_trade_fee_and_position_reconcile_exactly():
    result = collect(SyntheticSource(with_order=True))
    observation = build_observation(result.bundle, now=NOW)
    assert observation.risk.equity == D("99995")
    assert observation.fills[0].fee_amount == D("5")
    assert observation.reconciled_client_ids == {"client-1"}
    assert any(r.path == "/v1/order" and r.params == (("uuid", "order-1"),) for r in result.receipts)


def test_partial_open_order_fills_and_locked_cash_are_reconciled():
    source = SyntheticSource(with_order=True)
    source.detail.update(state="wait", volume="2", remaining_volume="1", locked="10005")
    source.balances[0].update(balance="79990", locked="10005")
    observation = build_observation(collect(source).bundle, now=NOW)
    assert observation.fills[0].quantity == D("1")
    gross = observation.settled_cash_krw[("upbit", SCOPE)]
    reserved = D(str(observation.positions.exposure["upbit"].reservations["client-1"]))
    assert gross == D("89995") and reserved == D("10005")
    assert gross-reserved == D("79990")
    source.balances[0]["locked"] = "10000"
    refusal(lambda: collect(source), "COLLECTOR_CASH_LOCK_RECONCILIATION_MISMATCH")


def test_canceled_partial_order_keeps_fills_and_zeroes_remaining_reservation():
    source = SyntheticSource(with_order=True)
    source.detail.update(state="cancel", volume="2", remaining_volume="1")
    result = collect(source)
    orders = next(p.rows for p in result.bundle.accounts[0].pages if p.kind == "orders")
    assert orders[0].remaining_quantity == 0 and orders[0].status == "canceled"
    assert len(build_observation(result.bundle, now=NOW).fills) == 1


def test_multitrade_order_does_not_guess_fee_allocations():
    source = SyntheticSource(with_order=True)
    first = source.detail["trades"][0]
    first.update(volume="0.5", funds="5000")
    source.detail["trades"].append({**first, "uuid":"fill-2"})
    source.detail["trades_count"] = 2
    refusal(lambda: collect(source), "COLLECTOR_PER_TRADE_FEE_EVIDENCE_REQUIRED")
    fees = tuple(TradeFeeEvidence(order_id="order-1", fill_id=f"fill-{i}", fee_krw=amount, source_sha256=SHA)
                 for i, amount in ((1,D("2")), (2,D("3"))))
    observation = build_observation(collect(source, trade_fees=fees).bundle, now=NOW)
    assert [f.fee_amount for f in observation.fills] == [D("2"), D("3")]
    refusal(lambda: collect(source, trade_fees=(replace(fees[0], fee_krw=D("1")), fees[1])),
            "COLLECTOR_FEE_RECONCILIATION_MISMATCH")


def test_zero_fee_multitrade_and_unused_fee_evidence_are_distinguished():
    source = SyntheticSource(with_order=True)
    source.detail["paid_fee"] = "0"; source.balances[0]["balance"] = "90000"
    source.detail["trades"][0].update(volume="0.5", funds="5000")
    source.detail["trades"].append({**source.detail["trades"][0], "uuid":"fill-2"})
    source.detail["trades_count"] = 2
    assert all(f.fee_amount == 0 for f in build_observation(collect(source).bundle, now=NOW).fills)
    extra = TradeFeeEvidence(order_id="unknown-order", fill_id="unknown-fill", fee_krw=D("0"), source_sha256=SHA)
    refusal(lambda: collect(source, trade_fees=(extra,)), "COLLECTOR_UNUSED_OR_DUPLICATE_FEE_EVIDENCE")


def test_missing_trade_details_market_orders_unknown_states_and_float_amounts_refuse():
    for mutation, code in (({"trades":[]}, "COLLECTOR_TRADE_DETAILS_INCOMPLETE"),
                           ({"ord_type":"price"}, "COLLECTOR_ORDER_TYPE_OR_STATE_UNSUPPORTED"),
                           ({"volume":1.0}, "COLLECTOR_DECIMAL_STRING_REQUIRED")):
        source = SyntheticSource(with_order=True); source.detail.update(mutation)
        refusal(lambda: collect(source), code)
    source = SyntheticSource(with_order=True); source.detail["state"] = "watch"
    refusal(lambda: collect(source), "COLLECTOR_CLOSED_STATE_INVALID")


def test_completed_zero_fee_krw_flow_reconciles_but_unsupported_flows_refuse():
    source = SyntheticSource()
    source.deposits = [dict(type="deposit", uuid="deposit-1", currency="KRW", state="ACCEPTED", fee="0",
        transaction_type="default", amount="1000", created_at=(NOW-timedelta(hours=2)).isoformat(),
        done_at=(NOW-timedelta(hours=1)).isoformat())]
    source.balances[0]["balance"] = "101000"
    assert build_observation(collect(source).bundle, now=NOW).risk.equity == D("101000")
    for key, value, code in (("fee","1","COLLECTOR_FLOW_FEE_CONVENTION_UNREVIEWED"),
                             ("state","PROCESSING","COLLECTOR_PENDING_OR_REVERSED_FLOW_UNSUPPORTED"),
                             ("currency","BTC","COLLECTOR_EXTERNAL_FLOW_UNSUPPORTED"),
                             ("transaction_type","internal","COLLECTOR_EXTERNAL_FLOW_UNSUPPORTED")):
        changed = deepcopy(source); changed.deposits[0][key] = value
        refusal(lambda: collect(changed), code)


def test_retention_identity_anchor_scope_and_capture_fence_are_required_before_fetch():
    anchor, coverage, baseline = proofs()
    cases = (({"anchor":replace(anchor, inventory_and_open_orders="unknown")},
              "COLLECTOR_ZERO_INVENTORY_AND_OPEN_ORDERS_ANCHOR_REQUIRED"),
             ({"coverage":replace(coverage, account_scope="other")}, "COLLECTOR_COVERAGE_SCOPE_MISMATCH"),
             ({"coverage":replace(coverage, history_retention="unverified")}, "COLLECTOR_SOURCE_OBLIGATIONS_UNRESOLVED"),
             ({"coverage":replace(coverage, history_from=NOW)}, "COLLECTOR_HISTORY_RETENTION_EVIDENCE_REQUIRED"),
             ({"coverage":replace(coverage, quiescent_from=NOW+timedelta(seconds=1))},
              "COLLECTOR_QUIESCENT_CAPTURE_EVIDENCE_REQUIRED"))
    for kwargs, code in cases:
        source = SyntheticSource()
        refusal(lambda: collect(source, **kwargs), code)
        assert not source.calls


def test_balance_mutation_and_full_history_cash_mismatch_refuse():
    source = SyntheticSource(); source.change_balances = True
    refusal(lambda: collect(source), "COLLECTOR_BALANCES_CHANGED_DURING_CAPTURE")
    source = SyntheticSource(); source.balances[0]["balance"] = "99999"
    refusal(lambda: collect(source), "CASH_RECONCILIATION_MISMATCH")
    refusal(lambda: collect(max_requests=1), "COLLECTOR_REQUEST_BOUND_EXCEEDED")


def test_raw_decimal_numbers_are_lossless_duplicate_json_keys_and_digest_changes_refuse():
    value = receipt("/v1/ticker", raw=b'[{"trade_price":0.12345678901234567890123456789}]').decode()
    assert value[0]["trade_price"] == D("0.12345678901234567890123456789")
    refusal(lambda: receipt("/v1/accounts", raw=b'{"balance":"1","balance":"2"}').decode(),
            "COLLECTOR_DUPLICATE_JSON_KEY")
    refusal(lambda: receipt("/v1/accounts", raw=b'{"balance":NaN}').decode(), "COLLECTOR_JSON_NONFINITE")
    refusal(lambda: replace(receipt("/v1/accounts", body=[]), raw_body=b"{}").decode(),
            "COLLECTOR_RECEIPT_DIGEST_MISMATCH")


def test_numbered_pages_reach_terminal_and_repeated_page_is_not_completeness():
    class Pages:
        account_scope = SCOPE
        def __init__(self, repeat=False):
            self.repeat = repeat; self.pages = []
        def fetch(self, path, params):
            page = int(dict(params)["page"]); self.pages.append(page)
            rows = [{"uuid":f"record-{i}"} for i in range(100)] if page == 1 or self.repeat else []
            return receipt(path, params, rows)
    source = Pages()
    capture = _Capture(source, SCOPE, NOW, max_requests=10, max_rows=1000)
    assert len(capture.pages("/v1/deposits")) == 100 and source.pages == [1,2]
    source = Pages(repeat=True)
    refusal(lambda: _Capture(source,SCOPE,NOW,max_requests=10,max_rows=1000).pages("/v1/deposits"),
            "COLLECTOR_PAGE_OVERLAP")


def test_closed_windows_are_bounded_overlap_and_do_not_invent_page_cursor():
    class Windows:
        account_scope = SCOPE
        def __init__(self):
            self.queries = []
        def fetch(self, path, params):
            query = dict(params); self.queries.append(query)
            assert "page" not in query and "cursor" not in query
            return receipt(path, params, [])
    source = Windows(); capture = _Capture(source,SCOPE,NOW,max_requests=20,max_rows=1000)
    assert capture.closed(NOW-timedelta(days=16), NOW) == {}
    ranges = sorted((int(q["start_time"]),int(q["end_time"])) for q in source.queries)
    assert len(ranges) == 3
    assert all(end-start <= 7*86400*1000 for start,end in ranges)
    assert all(ranges[i][1] > ranges[i+1][0] for i in range(2))


def test_saturated_single_timestamp_is_refused_instead_of_fabricating_history():
    class Saturated:
        account_scope = SCOPE
        def fetch(self, path, params):
            query = dict(params); target = int(NOW.timestamp()*1000)
            rows = [dict(uuid=f"order-{i}", state="done", created_at=NOW.isoformat()) for i in range(1000)]
            return receipt(path,params,rows if int(query["start_time"]) <= target <= int(query["end_time"]) else [])
    capture = _Capture(Saturated(),SCOPE,NOW,max_requests=100,max_rows=100000)
    refusal(lambda: capture.closed(NOW-timedelta(milliseconds=4),NOW), "COLLECTOR_SATURATED_TIMESTAMP")


def test_e1_binding_refuses_missing_environment_names_and_never_uses_env_fallback():
    with tempfile.TemporaryDirectory() as temporary:
        with patch.dict(os.environ, {"TRADEGEN_HOME":temporary}, clear=True):
            with patch("execution_accounts.upbit_collector.request", side_effect=AssertionError("network forbidden")):
                refusal(lambda: E1UpbitSource(account_scope=SCOPE,state_directory=Path(temporary),clock=lambda:NOW),
                        "COLLECTOR_ENV_CREDENTIAL_NAMES_REQUIRED")


def test_e1_binding_uses_only_fixed_gets_and_exact_raw_answer_not_float_body():
    raw = b'[{"currency":"KRW","balance":"100000.0000000000000000001","locked":"0"}]'
    answer = Answer(body=[{"balance":100000.0}],server_utc=NOW,received_utc=NOW,
                    sha256=hashlib.sha256(raw).hexdigest(),raw_body=raw)
    with tempfile.TemporaryDirectory() as temporary:
        # Empty synthetic values: the stub intercepts E1; real transport would refuse them.
        with patch.dict(os.environ, {"TRADEGEN_HOME":temporary,"UPBIT_ACCESS_KEY":"","UPBIT_SECRET_KEY":""}, clear=True):
            with patch("execution_accounts.upbit_collector.request", return_value=answer) as stub:
                source=E1UpbitSource(account_scope=SCOPE,state_directory=Path(temporary),clock=lambda:NOW)
                result=source.fetch("/v1/accounts",())
                assert result.decode()[0]["balance"] == "100000.0000000000000000001"
                stub.assert_called_once_with("upbit","GET","/v1/accounts",())
                refusal(lambda: source.fetch("/v1/orders",()), "COLLECTOR_ENDPOINT_REFUSED")


def test_prior_day_realized_loss_cannot_be_relabeled_as_first_trading_day():
    buy = order_fixture()
    buy.update(created_at=(NOW-timedelta(hours=14)).isoformat(), paid_fee="0")
    buy["trades"][0]["created_at"] = (NOW-timedelta(hours=12)).isoformat()
    sell = deepcopy(buy)
    sell.update(uuid="sell-1", identifier="sell-client", side="ask", price="9900",
                created_at=(NOW-timedelta(hours=12)).isoformat())
    sell["trades"][0].update(uuid="sell-fill", side="ask", price="9900", funds="9900",
                             created_at=(NOW-timedelta(hours=11)).isoformat())
    class PriorLoss(SyntheticSource):
        def __init__(self):
            super().__init__()
            self.balances[0]["balance"] = "99900"
        def fetch(self, path, params):
            if path == "/v1/orders/closed":
                return receipt(path,params,[{k:v for k,v in item.items() if k != "trades"} for item in (buy,sell)])
            if path == "/v1/order":
                return receipt(path,params,{"order-1":buy,"sell-1":sell}[dict(params)["uuid"]])
            return super().fetch(path,params)
    refusal(lambda: collect(PriorLoss()), "COLLECTOR_FIRST_TRADING_DAY_CONTRADICTS_HISTORY")
    baseline = replace(proofs()[2],first_trading_day=ORIGIN.date())
    observation = build_observation(collect(PriorLoss(),risk_baseline=baseline).bundle, now=NOW)
    assert not observation.risk.is_first_trading_day
    assert observation.risk.prior_day_realized_net_profit == D("-100")


def test_fresh_ticker_metadata_cannot_hide_a_stale_last_trade():
    class StaleTrade(SyntheticSource):
        def fetch(self,path,params):
            if path == "/v1/ticker":
                return receipt(path,params,[dict(market="KRW-BTC",trade_price=10000,
                    timestamp=int(NOW.timestamp()*1000),trade_timestamp=int((NOW-timedelta(minutes=1)).timestamp()*1000))])
            return super().fetch(path,params)
    refusal(lambda: collect(StaleTrade(with_order=True)), "COLLECTOR_TICKER_STALE_OR_FUTURE")
