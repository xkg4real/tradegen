"""Only invented wire records, fake transports and in-memory lifecycle fixtures."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal, localcontext
import json
from queue import Empty, Queue
from threading import Event
import time
from unittest.mock import patch

from data.kis_live import (ControlFrame, KISLiveError, LiveSession, MAX_FRAME_BYTES,
    MAX_TRADES, OrderBook, Subscription, TradeTick, _approval, parse_frame,
    subscription_message, supported_channels)
from data.kis_live_catalog import CHANNELS, PRODUCTION_APPROVAL_URL, PRODUCTION_WS_URL

D = Decimal
NOW = datetime(2031,1,1,tzinfo=timezone.utc)
TRADE = Subscription(tr_id="H0STCNT0", tr_key="005930")
BOOK = Subscription(tr_id="H0STASP0", tr_key="005930")


def reject(call, code=None):
    try:
        call()
    except ValueError as exc:
        if code:
            assert str(exc) == code, (str(exc),code)
        return
    raise AssertionError("expected refusal")


def wire(sub=TRADE, *, clock="090000", day="20310101", price="100", size="5", total="100", changes=None):
    channel = CHANNELS[sub.tr_id]
    fields = {field:"0" for field in channel.fields}
    fields[channel.symbol_field] = sub.tr_key
    fields[channel.time_field] = clock
    if channel.date_field:
        fields[channel.date_field] = day
    if "TYMD" in fields:
        fields["TYMD"] = day
    if channel.state_field:
        fields[channel.state_field] = "0"
    if channel.price_field:
        fields[channel.price_field] = price
    if channel.size_field:
        fields[channel.size_field] = size
    if channel.cumulative_volume_field:
        fields[channel.cumulative_volume_field] = total
    for index, name in enumerate(channel.bid_fields):
        fields[name] = str(99-index)
    for index, name in enumerate(channel.ask_fields):
        fields[name] = str(101+index)
    for name in channel.bid_size_fields:
        fields[name] = "10"
    for name in channel.ask_size_fields:
        fields[name] = "20"
    fields.update(changes or {})
    return "0|"+sub.tr_id+"|001|"+"^".join(fields[name] for name in channel.fields)


def ack(sub):
    return json.dumps({"header":{"tr_id":sub.tr_id,"tr_key":sub.tr_key,"encrypt":"N"},
                       "body":{"rt_cd":"0","msg1":"invented response text is never surfaced"}})


def active_session(subscriptions=(TRADE,BOOK)):
    session = LiveSession(subscriptions, clock=lambda:NOW)
    session._status = "streaming"  # Fixture only: no connection or credentials.
    session._generation = 1
    return session


class Response:
    def __init__(self, body=b'{"approval_key":"fixture-approval"}', status=200):
        self.body, self.status_code, self.closed = body, status, False

    def iter_content(self, chunk_size):
        for start in range(0,len(self.body),min(chunk_size,4096)):
            yield self.body[start:start+min(chunk_size,4096)]

    def close(self):
        self.closed = True


class Socket:
    def __init__(self, messages=()):
        self.queue = Queue()
        for message in messages:
            self.queue.put(message)
        self.sent, self.pongs, self.closed = [], [], False

    def send(self, message):
        self.sent.append(message)

    def recv(self, timeout):
        try:
            message = self.queue.get(timeout=min(timeout,0.02))
        except Empty:
            raise TimeoutError from None
        if type(message) is Exception:
            raise message
        return message

    def pong(self, message):
        self.pongs.append(message)

    def close(self):
        self.closed = True
        self.queue.put(Exception("fixture closed"))


def wait_for(predicate):
    end = time.monotonic()+2
    while time.monotonic() < end:
        if predicate():
            return
        time.sleep(0.005)
    raise AssertionError("fixture worker did not reach expected state")


def test_construction_and_invalid_subscriptions_never_read_credentials_or_transport():
    def forbidden(*args,**kwargs):
        raise AssertionError("must not touch fixture dependency")
    session = LiveSession((TRADE,), credential_provider=forbidden, connector=forbidden, http_post=forbidden)
    assert session.snapshot(now=NOW).status == "stopped"
    for subscriptions, environment in (
        ((),"production"), ((Subscription(tr_id="H0STCNI0",tr_key="private"),),"production"),
        ((Subscription(tr_id=TRADE.tr_id,tr_key="https://other"),),"production"),
        ((TRADE,TRADE),"production"), ((TRADE,Subscription(tr_id="H0NXCNT0",tr_key=TRADE.tr_key)),"production"),
        ((Subscription(tr_id="HDFSCNT0",tr_key="DNASAAPL"),),"paper"), ((TRADE,),"other")):
        reject(lambda:LiveSession(subscriptions, environment=environment, credential_provider=forbidden))
    assert {channel.tr_id for channel in supported_channels("paper")} == {TRADE.tr_id,BOOK.tr_id}
    assert "HDFFF020" not in {channel.tr_id for channel in supported_channels()}
    assert "H0STNAV0" not in {channel.tr_id for channel in supported_channels()}


def test_approval_fixed_https_body_no_redirect_no_disk_and_bounded_response():
    calls = []
    response = Response()
    def post(url,**kwargs):
        calls.append((url,kwargs)); return response
    assert _approval(PRODUCTION_APPROVAL_URL,lambda:("fixture-key","fixture-secret"),post) == "fixture-approval"
    assert calls[0][0] == PRODUCTION_APPROVAL_URL and response.closed
    assert calls[0][1]["json"] == {"grant_type":"client_credentials","appkey":"fixture-key","secretkey":"fixture-secret"}
    assert calls[0][1]["allow_redirects"] is False and calls[0][1]["stream"] is True
    def forbidden():
        raise AssertionError("credential provider must not be called")
    reject(lambda:_approval("https://untrusted.invalid/oauth2/Approval",forbidden,post), "INVALID_SUBSCRIPTION")
    for response in (Response(status=302),Response(b"x"*16385),Response(b'{"approval_key":null}'),
                     Response(b'{"approval_key":"a","approval_key":"b"}')):
        reject(lambda:_approval(PRODUCTION_APPROVAL_URL,lambda:("fixture-key","fixture-secret"),
                                lambda *a,**k:response),"APPROVAL_FAILED")
        assert response.closed


def test_subscription_messages_contain_only_fixed_market_registration_fields():
    body = json.loads(subscription_message(TRADE,"fixture-approval"))
    assert body["body"] == {"input":{"tr_id":TRADE.tr_id,"tr_key":TRADE.tr_key}}
    assert body["header"]["tr_type"] == "1" and body["header"]["custtype"] == "P"
    reject(lambda:subscription_message(Subscription(tr_id="unknown",tr_key="005930"),"fixture-approval"))
    reject(lambda:subscription_message(TRADE,"fixture\nunsafe"),"APPROVAL_FAILED")


def test_exact_record_counts_decimal_values_and_separate_timestamps():
    first = wire(price="100.125",total="100")
    second = wire(price="100.25",total="105")
    multi = "0|H0STCNT0|002|"+first.split("|",3)[3]+"^"+second.split("|",3)[3]
    events = parse_frame(multi,(TRADE,),received_at=NOW+timedelta(seconds=1))
    assert len(events) == 2 and type(events[0]) is TradeTick
    assert events[0].price == D("100.125") and events[0].size == D(5)
    assert events[0].observed_at == NOW and events[0].received_at == NOW+timedelta(seconds=1)
    assert not events[0].time_inferred and events[0].session_date == "20310101"
    for invalid in (multi.replace("|002|","|001|"),multi+"^extra",first.replace("|001|","|000|"),
                    first.replace("|001|","|101|"),first.replace("0|","1|",1),b"x"*(MAX_FRAME_BYTES+1)):
        reject(lambda:parse_frame(invalid,(TRADE,),received_at=NOW))
    for price in ("NaN","1e2","-1","0",".1"):
        reject(lambda:parse_frame(wire(price=price),(TRADE,),received_at=NOW),"INVALID_FRAME")


def test_market_symbol_unsubscribed_private_or_future_frames_fail_closed():
    reject(lambda:parse_frame(wire(Subscription(tr_id=TRADE.tr_id,tr_key="000660")),(TRADE,),received_at=NOW),
           "UNSUBSCRIBED_FRAME")
    reject(lambda:parse_frame(wire(clock="090003"),(TRADE,),received_at=NOW),"INVALID_FRAME")
    reject(lambda:parse_frame(wire(day="20310132"),(TRADE,),received_at=NOW),"INVALID_FRAME")
    reject(lambda:parse_frame(wire(),(TRADE,),received_at=NOW.replace(tzinfo=None)),"CLOCK_INVALID")
    reject(lambda:parse_frame('{"header":{"tr_id":"H0STCNI0"},"body":{"rt_cd":"0"}}',
                             (TRADE,),received_at=NOW),"UNSUBSCRIBED_FRAME")


def test_book_depth_order_missing_levels_and_inferred_date_are_explicit():
    book = parse_frame(wire(BOOK),(BOOK,),received_at=NOW)[0]
    assert type(book) is OrderBook and len(book.levels) == 10
    assert book.time_inferred and book.observed_at == NOW
    assert book.levels[0].bid == 99 and book.levels[0].ask == 101
    channel = CHANNELS[BOOK.tr_id]
    missing = {field:"0" for field in (*channel.bid_fields,*channel.ask_fields,*channel.bid_size_fields,*channel.ask_size_fields)}
    empty = parse_frame(wire(BOOK,changes=missing),(BOOK,),received_at=NOW)[0]
    assert empty.levels == ()
    for changes in ({"BIDP1":"102"},{"BIDP2":"100"},{"ASKP2":"100"},
                    {"BIDP1":"0","BIDP_RSQN1":"10"}):
        reject(lambda:parse_frame(wire(BOOK,changes=changes),(BOOK,),received_at=NOW),"INVALID_FRAME")


def test_indicative_unknown_and_delayed_data_are_never_reported_as_live_metrics():
    for code, expected in (("A","indicative"),("?","unknown")):
        session = active_session((BOOK,))
        session._accept(parse_frame(wire(BOOK,changes={"HOUR_CLS_CODE":code}),(BOOK,),received_at=NOW))
        row = session.snapshot(now=NOW).instruments[0]
        assert row.book.state == expected and row.book_stale and row.metrics.spread is None
    sub = Subscription(tr_id="HDFSCNT0",tr_key="DHKS00003")
    session = active_session((sub,))
    session._accept(parse_frame(wire(sub),(sub,),received_at=NOW))
    row = session.snapshot(now=NOW).instruments[0]
    assert row.trade.delay_seconds == 900 and row.trade.state == "delayed"
    assert row.trade_stale and row.metrics.vwap is None


def test_metrics_use_only_captured_real_trades_and_exact_book_sizes():
    session = active_session()
    session._accept(parse_frame(wire(price="100",size="5",total="100"),(TRADE,BOOK),received_at=NOW))
    session._accept(parse_frame(wire(clock="090001",price="110",size="5",total="105"),
                               (TRADE,BOOK),received_at=NOW+timedelta(seconds=1)))
    session._accept(parse_frame(wire(BOOK),(TRADE,BOOK),received_at=NOW+timedelta(seconds=1)))
    with localcontext() as context:
        context.prec = 2
        row = session.snapshot(now=NOW+timedelta(seconds=1)).instruments[0]
    assert row.metrics.vwap == D(105) and row.metrics.window_return == D("0.1")
    assert row.metrics.spread == 2 and row.metrics.imbalance == D("-0."+"3"*34)
    assert row.metrics.sample_count == 2 and len(row.trades) == 2
    stale = session.snapshot(now=NOW+timedelta(seconds=20)).instruments[0]
    assert stale.trade_stale and stale.book_stale and stale.metrics.vwap is None and stale.metrics.spread is None
    session._status = "reconnecting"
    stale = session.snapshot(now=NOW+timedelta(seconds=1)).instruments[0]
    assert stale.metrics.window_return is None and stale.trade_stale


def test_cumulative_duplicates_zero_size_and_out_of_order_do_not_invent_trades():
    session = active_session((TRADE,))
    event = parse_frame(wire(),(TRADE,),received_at=NOW)[0]
    session._accept((event,event))
    assert len(session.snapshot(now=NOW).instruments[0].trades) == 1
    session._accept((replace(event,size=D(0),cumulative_volume=D(101)),))
    assert len(session.snapshot(now=NOW).instruments[0].trades) == 1
    reject(lambda:session._accept((replace(event,cumulative_volume=D(99)),)),"OUT_OF_ORDER_FRAME")
    reject(lambda:session._accept((replace(event,observed_at=NOW-timedelta(seconds=1)),)),"OUT_OF_ORDER_FRAME")


def test_explicit_foreign_trading_date_and_unknown_session_reset_break_windows():
    sub = Subscription(tr_id="HDFSCNT0",tr_key="DNASAAPL")
    session = active_session((sub,))
    event = parse_frame(wire(sub),(sub,),received_at=NOW)[0]
    session._accept((event,))
    # Both reports arrive on the same KST date, but the documented trading date changes.
    changed = replace(event,cumulative_volume=D(5),session_date="20310102")
    session._accept((changed,))
    row = session.snapshot(now=NOW).instruments[0]
    assert len(row.trades) == 1 and row.continuity_breaks == 1 and row.metrics.window_return is None
    session = active_session((sub,))
    session._accept((replace(event,session_date=None),))
    session._accept((replace(event,session_date=None,cumulative_volume=D(5)),))
    assert session.snapshot(now=NOW).instruments[0].continuity_breaks == 1


def test_indicator_ticks_are_not_volume_weighted_trade_prints():
    sub = Subscription(tr_id="H0UPCNT0",tr_key="0001")
    session = active_session((sub,))
    one = parse_frame(wire(sub,price="100"),(sub,),received_at=NOW)[0]
    two = replace(one,price=D(101))
    session._accept((one,two))
    row = session.snapshot(now=NOW).instruments[0]
    assert row.trade.state == "indicator" and row.trades == ()
    assert row.metrics.window_return == D("0.01") and row.metrics.vwap is None


def test_buffers_are_bounded_and_new_connection_generation_does_not_fill_gaps():
    session = active_session((TRADE,))
    event = parse_frame(wire(),(TRADE,),received_at=NOW)[0]
    session._accept(tuple(replace(event,cumulative_volume=D(i+100)) for i in range(MAX_TRADES+20)))
    assert len(session._data[(event.market,event.symbol)]["trades"]) == MAX_TRADES
    assert len(session.snapshot(now=NOW).instruments[0].trades) == 20
    session._generation += 1
    assert session.snapshot(now=NOW).instruments[0].trade_stale


def test_json_controls_are_typed_and_never_surface_remote_text_or_private_material():
    parsed = parse_frame(ack(TRADE),(TRADE,),received_at=NOW)
    assert parsed == ControlFrame(kind="subscribed",tr_id=TRADE.tr_id,tr_key=TRADE.tr_key)
    ping = '{"header":{"tr_id":"PINGPONG","datetime":"20310101090000"}}'
    assert parse_frame(ping,(TRADE,),received_at=NOW).pong == ping.encode()
    reject(lambda:parse_frame('{"header":{"tr_id":"PINGPONG","approval_key":"hidden"}}',
                             (TRADE,),received_at=NOW),"INVALID_FRAME")
    rejected = json.loads(ack(TRADE)); rejected["body"]["rt_cd"] = "1"
    reject(lambda:parse_frame(json.dumps(rejected),(TRADE,),received_at=NOW),"SUBSCRIPTION_REJECTED")
    rejected["header"]["encrypt"] = "Y"
    reject(lambda:parse_frame(json.dumps(rejected),(TRADE,),received_at=NOW),"UNSUBSCRIBED_FRAME")


def test_explicit_worker_uses_fixed_origins_proxy_policy_and_stops_cleanly():
    socket = Socket((ack(TRADE),ack(BOOK),wire(),wire(BOOK)))
    calls = []
    def connector(address,**options):
        calls.append((address,options)); return socket
    session = LiveSession((TRADE,BOOK),clock=lambda:NOW,
        credential_provider=lambda:("fixture-key","fixture-secret"),
        http_post=lambda *a,**k:Response(),connector=connector)
    session.start()
    try:
        wait_for(lambda:session.snapshot(now=NOW).instruments[0].book is not None)
        snapshot = session.snapshot(now=NOW)
        assert snapshot.status == "streaming" and snapshot.instruments[0].metrics.spread == 2
        assert calls[0][0] == PRODUCTION_WS_URL and calls[0][1]["proxy"] is True
        assert calls[0][1]["logger"].disabled and len(socket.sent) == 2
        assert "fixture-approval" not in repr(snapshot)
    finally:
        session.stop()
    assert socket.closed and session.snapshot(now=NOW).status == "stopped"


def test_stop_during_pending_auth_retains_worker_and_prevents_later_transport():
    entered, release = Event(), Event()
    calls = []
    def credentials():
        entered.set(); release.wait(2)
        return "fixture-key","fixture-secret"
    session = LiveSession((TRADE,),clock=lambda:NOW,credential_provider=credentials,
        http_post=lambda *a,**k:calls.append("unexpected"),connector=lambda *a,**k:calls.append("unexpected"))
    session.start()
    try:
        assert entered.wait(1)
        session.stop(timeout=0.01)
        assert session.snapshot(now=NOW).status == "stopping"
        reject(session.start,"ALREADY_RUNNING")
    finally:
        release.set(); session.stop()
    assert session.snapshot(now=NOW).status == "stopped" and calls == []


def test_reconnect_attempts_are_bounded_with_no_raw_error_or_reissued_approval():
    attempts, approvals = [], []
    def connection(*args,**kwargs):
        attempts.append(1); raise RuntimeError("fixture-private-content")
    def post(*args,**kwargs):
        approvals.append(1); return Response()
    session = LiveSession((TRADE,),clock=lambda:NOW,
        credential_provider=lambda:("fixture-key","fixture-secret"),http_post=post,connector=connection)
    with patch.object(session._stop,"wait",return_value=False):
        session.start()
        session._thread.join(2)
    snapshot = session.snapshot(now=NOW)
    assert not session._thread.is_alive() and len(attempts) == 3 and len(approvals) == 1
    assert snapshot.status == "error" and snapshot.reason == "RECONNECT_LIMIT"
    assert "fixture-private-content" not in repr(snapshot)
    session.stop()
