"""Offline BR-1/BR-2 evidence binding, UTC-day pagination and order identity."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import hashlib
import json

from execution_accounts.collector import SourceReceipt
from execution_accounts.provider import EvidenceError
from execution_accounts.upbit_collector import collect_order_fills, collect_trade_window


END = datetime(2026, 11, 24, 0, 0, 2, tzinfo=timezone.utc)
START = END - timedelta(seconds=4)
SCOPE = "fixture-scope"


def trade(offset, sequence, price):
    return {"market": "KRW-BTC", "timestamp": int((END + timedelta(seconds=offset)).timestamp() * 1000),
            "sequential_id": sequence, "trade_price": price, "trade_volume": "1", "ask_bid": "ASK"}


class Source:
    account_scope = SCOPE

    def __init__(self):
        self.now = END + timedelta(seconds=3)
        self.ticker = [dict(market="KRW-BTC", trade_timestamp=trade(-1, 1, 3)["timestamp"], trade_price=3)]
        self.pages = {(1, None): [trade(-3, 7, 1), trade(-3.5, 99, 2)],
                      (1, "99"): [trade(-3.5, 99, 2), trade(-5, 150, 1)],
                      (0, None): [trade(-1, 3, 3)], (0, "3"): []}
        self.calls = []

    def fetch(self, path, params):
        self.calls.append((path, params))
        q = dict(params)
        if path == "/v1/ticker":
            body = self.ticker
        elif path == "/v1/order":
            body = {"uuid": "fixture-order", "identifier": "fixture-client", "market": "KRW-BTC",
                    "side": "bid", "ord_type": "limit", "state": "wait", "volume": "1", "remaining_volume": "1",
                    "price": "1", "locked": "1", "executed_volume": "0", "paid_fee": "0",
                    "trades_count": 0, "trades": [], "created_at": START.isoformat()}
        else:
            body = self.pages[(int(q.get("days_ago", 0)), q.get("cursor"))]
        raw = json.dumps(body).encode()
        return SourceReceipt(path=path, params=params, account_scope=self.account_scope,
                             received_at=self.now, server_time=self.now,
                             raw_body=raw, sha256=hashlib.sha256(raw).hexdigest())


def refused(code, fn):
    try:
        fn()
    except EvidenceError as exc:
        assert exc.code == code, exc.code
    else:
        raise AssertionError("expected " + code)


def walk(src, **options):
    return collect_trade_window(src, "KRW-BTC", start=START, end=END, **options)


def test_both_trade_days_last_wire_cursor_and_complete_global_budget():
    s = Source()
    result = walk(s)
    assert [p.sequential_id for p in result.prints] == [99, 7, 3]
    assert result.opening_print.sequential_id == 150
    requests = [dict(r.params) for r in result.receipts]
    assert [r.get("cursor") for r in requests[1:]] == [None, "99", None, "3"]
    assert all(r["count"] == "500" for r in requests[1:])
    assert "to" not in requests[1] and requests[-1]["to"] == "00:00:03"
    assert "days_ago" not in requests[-1] and requests[1]["days_ago"] == "1"
    refused("UPBIT_TRADE_COVERAGE_INCOMPLETE", lambda: walk(Source(), max_pages=3, anchor_trade_id=7))


def test_settlement_gate_stops_before_first_trade_read_and_retains_ticker_disagreement():
    s = Source()
    s.now = END + timedelta(milliseconds=1999)
    refused("COLLECTOR_TRADE_WINDOW_UNSETTLED", lambda: walk(s))
    assert [path for path, _ in s.calls] == ["/v1/ticker"]
    s.now = END + timedelta(seconds=2)
    s.ticker[0]["trade_price"] = 12
    result = walk(s)
    assert result.ticker_discrepancy == (END - timedelta(seconds=1), 12)
    assert result.prints and result.receipts[0].path == "/v1/ticker"


def test_conflicting_trade_or_nonprogressing_cursor_cannot_close_window():
    s = Source()
    s.pages[(1, "99")] = [trade(-3.5, 99, 9)]
    refused("COLLECTOR_DUPLICATE_CONTRADICTION", lambda: walk(s))
    s.pages[(1, "99")] = [trade(-3.5, 99, 2)]
    refused("UPBIT_TRADE_COVERAGE_INCOMPLETE", lambda: walk(s))


def test_query_scope_broker_uuid_and_client_identifier_match_the_receipt():
    s = Source()
    assert collect_order_fills(s, "fixture-order").order.client_id == "fixture-client"
    assert collect_order_fills(s, identifier_id="fixture-client").order_id == "fixture-order"
    refused("COLLECTOR_ORDER_IDENTITY_MISMATCH", lambda: collect_order_fills(s, "other-order"))
    refused("COLLECTOR_ORDER_IDENTITY_MISMATCH", lambda: collect_order_fills(s, identifier_id="other-client"))
    refused("COLLECTOR_RECEIPT_SCOPE_MISMATCH", lambda: collect_order_fills(s, "fixture-order", account_scope="another"))
    refused("COLLECTOR_RECEIPT_SCOPE_MISMATCH", lambda: walk(s, account_scope="another"))


def test_server_utc_day_rollover_invalidates_relative_query():
    class Midnight(Source):
        def fetch(self, path, params):
            receipt = super().fetch(path, params)
            if path == "/v1/trades/ticks":
                tomorrow = receipt.server_time + timedelta(days=1)
                return replace(receipt, received_at=tomorrow, server_time=tomorrow)
            return receipt
    refused("COLLECTOR_SERVER_DAY_MISMATCH", lambda: walk(Midnight()))


def test_unset_signed_threshold_blocks_flat_upbit_entry_without_a_fictitious_price_alarm():
    from decimal import Decimal
    from execution_accounts.provider import _check_bid_gap, build_observation
    from execution_control.risk import evaluate
    from tests.accounts_provider import NOW, bundle
    from tests.control_risk import _policy

    obs = build_observation(bundle(), now=NOW, bid_gap_y=None)
    assert not obs.risk.bid_gap_triggered and obs.risk.bid_gap_policy_missing
    assert "SIGNED_BID_GAP_REQUIRED" in evaluate(_policy(), obs.risk, now=NOW).reasons
    assert not build_observation(bundle(), now=NOW, bid_gap_y=Decimal("0.01")).risk.bid_gap_policy_missing
    assert not _check_bid_gap(Decimal("101"), Decimal("100"), None)
    assert _check_bid_gap(Decimal("100"), Decimal("100"), None)
    assert _check_bid_gap(None, Decimal("100"), None)


def test_upbit_stale_mark_exception_does_not_apply_to_kis_or_okx():
    from decimal import Decimal
    from execution_accounts.provider import build_observation
    from tests.accounts_kis_collector import _bundle
    from tests import accounts_okx_collector as okx

    statements = (_bundle(), okx.collect_okx(okx.Archive(okx.fixture()), **okx.kwargs()).bundle)
    for original in statements:
        account = original.accounts[0]
        now = account.observed_at
        stale = replace(account.positions[0], asof=now - timedelta(seconds=31),
                        best_bid=Decimal(1), best_bid_asof=now)
        changed = replace(account, positions=(stale, *account.positions[1:]))
        evidence = replace(original, accounts=(changed,))
        refused("EVIDENCE_STALE_OR_FUTURE", lambda: build_observation(evidence, now=now, bid_gap_y=Decimal("0.05")))



def test_walk_refuses_unordered_page_or_unverified_eighth_utc_day():
    s = Source()
    s.pages[(1, None)].reverse()
    refused("COLLECTOR_TRADE_PAGE_NOT_CHRONOLOGICAL", lambda: walk(s))
    s = Source()
    s.now = END + timedelta(days=6, seconds=3)
    refused("UPBIT_TRADE_COVERAGE_INCOMPLETE", lambda: walk(s))
    assert [path for path, _ in s.calls] == ["/v1/ticker"]


def test_br6_matches_any_preopening_print_and_checks_ambiguous_or_empty_history():
    s = Source()
    old, last = trade(-6, 151, 4), trade(-5, 150, 1)
    s.pages[(1, "99")] = [trade(-3.5, 99, 2), last, old]
    s.ticker = [dict(market="KRW-BTC", trade_timestamp=old["timestamp"], trade_price=4)]
    assert walk(s).ticker_discrepancy is None

    s.pages[(1, "99")] = [trade(-3.5, 99, 2), last, trade(-5, 152, 9)]
    for price in (1, 9, 7):
        s.ticker[0].update(trade_timestamp=last["timestamp"], trade_price=price)
        result = walk(s)
        assert result.opening_print is None
        assert result.ticker_discrepancy == (None if price in (1, 9) else (END - timedelta(seconds=5), 7))

    s.pages = {(1, None): [], (0, None): []}
    assert walk(s).ticker_discrepancy == (END - timedelta(seconds=5), 7)


def test_br6_uses_actual_exclusive_query_end_at_utc_day_rollover():
    cutoff = END - timedelta(seconds=2)
    s = Source()
    s.ticker = [dict(market="KRW-BTC", trade_timestamp=trade(-2, 1, 8)["timestamp"], trade_price=8)]
    result = collect_trade_window(s, "KRW-BTC", start=START, end=cutoff)
    assert result.ticker_discrepancy is None
    assert all(dict(r.params)["days_ago"] == "1" for r in result.receipts[1:])
    s.ticker[0]["trade_timestamp"] -= 1
    assert collect_trade_window(s, "KRW-BTC", start=START, end=cutoff).ticker_discrepancy == (
        cutoff - timedelta(milliseconds=1), 8)


def test_limit_order_receipt_reconciles_reported_volume_and_terminal_state_before_canary():
    class Orders(Source):
        def __init__(self):
            super().__init__()
            self.patch = {}

        def fetch(self, path, params):
            original = super().fetch(path, params)
            body = json.loads(original.raw_body)
            body.update(self.patch)
            raw = json.dumps(body).encode()
            return replace(original, raw_body=raw, sha256=hashlib.sha256(raw).hexdigest())

    s = Orders()
    def collect():
        return collect_order_fills(s, "fixture-order")

    assert collect().order.status == "open"
    for patch, code in (
        (dict(state="done", remaining_volume="0", locked="0"), "COLLECTOR_ORDER_QUANTITY_MISMATCH"),
        (dict(state="done", remaining_volume="1", locked="0"), "COLLECTOR_DONE_ORDER_INCOMPLETE"),
        (dict(state="wait", remaining_volume="2"), "COLLECTOR_ORDER_QUANTITY_MISMATCH"),
        (dict(state="wait", prevented_volume="0.1"), "COLLECTOR_SMP_LIMIT_STATE_UNVERIFIED"),
    ):
        s.patch = patch
        refused(code, collect)
    fill = dict(uuid="fixture-fill", market="KRW-BTC", side="bid", created_at=START.isoformat(),
                volume="0.5", price="1", funds="0.5")
    s.patch = dict(state="wait", trades=[fill], trades_count=1, executed_volume="0.5", remaining_volume="0.5")
    assert collect().order.status == "partial"
    s.patch.update(state="done", volume="0.5", remaining_volume="0", locked="0")
    assert collect().order.status == "filled"
    s.patch.update(state="wait")
    refused("COLLECTOR_ACTIVE_ORDER_EMPTY", collect)
    s.patch.update(state="cancel", volume="1", prevented_volume="0.5", remaining_volume="0.5")
    canceled = collect()
    assert canceled.order.status == "canceled" and len(canceled.fills) == 1
    s.patch.update(ord_type="market", volume=None, price=None)
    market = collect()
    assert market.order is None and len(market.fills) == 1
