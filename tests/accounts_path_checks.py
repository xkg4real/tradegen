"""Synthetic raw receipts for lagging public-data comparisons, all clocks injected."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal as D
import hashlib
import json

from execution_accounts.collector import SourceReceipt
from execution_accounts.path_checks import own_fill_findings, ticker_findings
from execution_accounts.provider import EvidenceError
from execution_accounts.upbit_collector import collect_order_fills, collect_trade_window

MINUTE = datetime(2026, 11, 25, 3, 2, tzinfo=timezone.utc)
SCOPE, MARKET = "fixture-main", "KRW-BTC"
NOW = MINUTE + timedelta(minutes=4)


def ms(at):
    return (at - datetime(1970, 1, 1, tzinfo=timezone.utc)) // timedelta(milliseconds=1)


def receipt(path, params, rows, *, at=NOW):
    raw = json.dumps(rows, separators=(",", ":")).encode()
    return SourceReceipt(path=path, params=params, raw_body=raw, sha256=hashlib.sha256(raw).hexdigest(),
                         account_scope=SCOPE, received_at=at, server_time=at)


def tick(at, px, seq, *, qty=1):
    return dict(market=MARKET, timestamp=ms(at), sequential_id=seq, trade_price=px, trade_volume=qty, ask_bid="BID")


class Archive:
    account_scope = SCOPE

    def __init__(self, ticks=()):
        self.ticks, self.orders = list(ticks), {}
        self.ticker = max(ticks, key=lambda t:t["timestamp"]) if ticks else tick(MINUTE-timedelta(seconds=3), 1, 1)

    def fetch(self, path, params):
        query = dict(params)
        if path == "/v1/ticker":
            rows = [dict(market=MARKET, trade_price=self.ticker["trade_price"], trade_timestamp=self.ticker["timestamp"])]
        elif path == "/v1/order":
            rows = self.orders[query["uuid"]]
        elif path == "/v1/trades/ticks":
            if "cursor" in query:
                rows = []
            else:
                cutoff = datetime.combine(NOW.date(), datetime.strptime(query["to"], "%H:%M:%S").time(), timezone.utc)
                rows = sorted((t for t in self.ticks if t["timestamp"] < ms(cutoff)), key=lambda t:-t["timestamp"])
        else:
            raise AssertionError(path)
        return receipt(path, params, rows)


def window(src, *, start=MINUTE, end=None):
    return collect_trade_window(src, MARKET, start=start, end=end or start+timedelta(minutes=1))


def order(src, oid, specs, *, prevented="0"):
    # Private order side is ask, public print denotes a bid. Without paired A0
    # evidence those fields cannot be compared.
    trades = [dict(uuid=str(i), market=MARKET, side="ask", created_at=at.isoformat(), price=str(px),
                   volume=str(qty), funds=str(D(qty)*D(px))) for i, at, px, qty in specs]
    executed = sum((D(r["volume"]) for r in trades), D(0))
    src.orders[oid] = dict(uuid=oid, identifier="", market=MARKET, side="ask", created_at=(MINUTE-timedelta(days=1)).isoformat(),
                           volume=str(executed + D(prevented)), remaining_volume=prevented, prevented_volume=prevented,
                           price="1", paid_fee="0", locked="0", executed_volume=str(executed), ord_type="limit",
                           state="cancel" if D(prevented) else "done", trades_count=len(trades), trades=trades)
    return collect_order_fills(src, oid)


def refused(reason, fn):
    try:
        fn()
    except EvidenceError as exc:
        assert exc.code == reason, (exc.code, reason)
    else:
        raise AssertionError("Expected " + reason)


def check(path, orders=(), **kw):
    return own_fill_findings(path, orders, account_scope=SCOPE,
        **({"expected_order_ids": frozenset(o.order_id for o in orders)} | kw))


def test_canary_consumes_multiplicity_across_orders_and_matches_submilliseconds_without_side():
    stamp = MINUTE+timedelta(seconds=1)
    src = Archive([tick(stamp, 11, 9), tick(MINUTE-timedelta(seconds=2), 6, 7)])
    a = order(src, "order-a", [("fill-a", stamp+timedelta(microseconds=900), 11, 1)], prevented="2")
    b = order(src, "order-b", [("fill-b", stamp, 11, 1)])
    path = window(src)
    assert not check(path, (a,))
    findings = check(path, (b,a))
    assert findings == check(path, (a,b)) and len(findings) == 1
    assert (findings[0].kind, findings[0].price, findings[0].at) == ("OWN_FILL_MISS", D(11), stamp)
    c = order(src, "order-c", [("fill-c",stamp+timedelta(microseconds=100),11,1)])
    group, = check(path, (c,b,a))
    assert group.occurrences == 2 and group.at == stamp
    src.ticks.append(tick(stamp, 11, 10))
    assert not check(window(src), (a,b))


def test_microsecond_boundaries_cannot_split_a_public_print_bucket_in_the_own_fill_canary():
    public_at = MINUTE + timedelta(milliseconds=1)
    own_at = public_at + timedelta(microseconds=300)
    src = Archive([tick(public_at, 11, 9)])
    observed = order(src, "partial-boundary", [("fill-at-300us", own_at, 11, 1)])
    # A start 200 us into the bin would exclude the public print and include the fill.
    start_cut = window(src, start=public_at+timedelta(microseconds=200), end=MINUTE+timedelta(seconds=1))
    # An end 200 us into the bin would include the public print but cannot prove when its trade occurred.
    end_cut = window(src, start=MINUTE, end=public_at+timedelta(microseconds=200))
    for candidate in (start_cut, end_cut):
        refused("PATH_CHECK_MILLISECOND_BOUNDARIES_REQUIRED", lambda: check(candidate, (observed,)))
    assert not check(window(src,start=public_at,end=public_at+timedelta(milliseconds=1)), (observed,))


def test_prevented_only_orders_produce_no_miss_and_existing_fills_are_checked_in_half_open_interval():
    src = Archive([tick(MINUTE, 3, 10)])
    canceled = order(src, "zero", [], prevented="2")
    end = MINUTE+timedelta(minutes=1)
    active = order(src, "active", [("before", MINUTE-timedelta(milliseconds=1), 2, 1),
                                  ("within", MINUTE, 2, 1), ("next", end, 2, 1)], prevented="1")
    one, = check(window(src), (canceled,active))
    assert one.at == MINUTE and one.price == 2 and one.kind == "OWN_FILL_MISS"
    assert len(one.evidence_sha256) == 64


def test_roster_receipt_scope_bytes_and_derived_order_or_window_cannot_be_substituted():
    src = Archive([tick(MINUTE, 5, 4)])
    path = window(src)
    o = order(src,"original", [("fill",MINUTE, 5, 1)])
    refused("PATH_CHECK_ORDER_ROSTER_MISMATCH", lambda: check(path, (o,), expected_order_ids=frozenset()))
    refused("PATH_CHECK_ORDER_REPLAY_MISMATCH", lambda: check(path, (replace(o, fills=()),)))
    refused("PATH_CHECK_WINDOW_REPLAY_MISMATCH", lambda: check(replace(path, prints=()), (o,)))
    refused("COLLECTOR_RECEIPT_DIGEST_MISMATCH", lambda: check(path,(replace(o, receipt=replace(o.receipt, raw_body=b"[]")),)))
    refused("PATH_CHECK_ORDER_RECEIPT_BINDING", lambda: check(path,(replace(o, receipt=replace(o.receipt, account_scope="other")),)))
    refused("PATH_CHECK_ORDER_RECEIPT_BINDING", lambda: check(path,(replace(o, receipt=replace(o.receipt, server_time=MINUTE)),)))
    refused("PATH_CHECK_UNUSED_RECEIPTS", lambda: check(replace(path, receipts=(*path.receipts, path.receipts[0]))))


def test_order_receipt_received_before_the_end_cannot_use_a_fast_server_clock():
    src = Archive([tick(MINUTE, 5, 4)])
    path = window(src)
    o = order(src, "original", [("fill", MINUTE, 5, 1)])
    boundary = replace(o.receipt, received_at=path.end, server_time=path.end)
    earlier = replace(boundary, received_at=path.end-timedelta(microseconds=1))
    refused("PATH_CHECK_ORDER_RECEIPT_BINDING", lambda: check(path, (replace(o,receipt=earlier),)))
    assert not check(path, (replace(o,receipt=boundary),))


def test_ticker_findings_replayed_from_wire_and_outside_bound_excluded():
    src = Archive([tick(MINUTE, 5, 4), tick(MINUTE-timedelta(seconds=2), 3, 1)])
    src.ticker = tick(MINUTE+timedelta(seconds=4), 50, 8)
    f, = ticker_findings(window(src), account_scope=SCOPE)
    assert f.kind == "TICKER_MISMATCH" and f.price == D(50)
    src.ticker = tick(MINUTE+timedelta(seconds=61), 50, 8)
    assert not ticker_findings(window(src), account_scope=SCOPE)
    src.ticker = tick(MINUTE-timedelta(seconds=2), 9, 8)
    f, = ticker_findings(window(src), account_scope=SCOPE)
    assert f.price == 9


def test_incorrect_public_volume_is_a_miss_even_with_matching_time_and_price():
    src = Archive([tick(MINUTE, 5, 4, qty=2)])
    o = order(src, "original", [("fill", MINUTE, 5, 1)])
    f, = check(window(src), (o,))
    assert (f.kind, f.at, f.price) == ("OWN_FILL_MISS", MINUTE, D(5))
