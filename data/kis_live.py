"""Explicit, bounded KIS market-data streaming; no execution or account channel.

Construction/import never reads credentials or opens a connection. Only start()
does so. Approval material remains local to the worker, never in a snapshot or on
disk. Uploaded contracts define every admitted positional field and subscription.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal, localcontext
from fractions import Fraction
import hashlib
import json
import logging
import re
from threading import Event, RLock, Thread, current_thread
import time
from typing import Callable
from zoneinfo import ZoneInfo

from data.kis_live_catalog import (CHANNELS, Channel, PAPER_APPROVAL_URL, PAPER_WS_URL,
    PRODUCTION_APPROVAL_URL, PRODUCTION_WS_URL, subscription_delay_seconds, validate_subscription)

MAX_FRAME_BYTES = 524288
MAX_RECORDS = 100
MAX_SUBSCRIPTIONS = 8
MAX_TRADES = 1000
FRESH_SECONDS = 15
WINDOW_SECONDS = 60
_NUMBER = re.compile(r"(?:0|[0-9]{1,24})(?:\.[0-9]{1,12})?")
_CONTROL_BYTES = 16384


class KISLiveError(ValueError):
    """Fixed codes only; remote text and transport exceptions are not exposed."""


def _require(ok, code):
    if not ok:
        raise KISLiveError(code)


def _instant(value):
    try:
        _require(type(value) is datetime and value.utcoffset() is not None, "CLOCK_INVALID")
        return value.astimezone(timezone.utc)
    except (OverflowError, ValueError, TypeError):
        raise KISLiveError("CLOCK_INVALID") from None


def _utc_now():
    return datetime.now(timezone.utc)


def _decimal(value, *, positive=False, optional=False):
    if optional and value == "":
        return None
    _require(type(value) is str and len(value) <= 40 and _NUMBER.fullmatch(value) is not None,
             "INVALID_FRAME")
    amount = Decimal(value)
    _require(not positive or amount > 0, "INVALID_FRAME")
    return amount


@dataclass(frozen=True, kw_only=True)
class Subscription:
    tr_id: str
    tr_key: str


@dataclass(frozen=True, kw_only=True)
class TradeTick:
    symbol: str
    market: str
    tr_id: str
    price: Decimal
    size: Decimal | None
    cumulative_volume: Decimal | None
    observed_at: datetime
    received_at: datetime
    state: str
    delay_seconds: int
    time_inferred: bool
    source_sha256: str
    session_date: str | None = None


@dataclass(frozen=True, kw_only=True)
class BookLevel:
    bid: Decimal | None
    bid_size: Decimal | None
    ask: Decimal | None
    ask_size: Decimal | None


@dataclass(frozen=True, kw_only=True)
class OrderBook:
    symbol: str
    market: str
    tr_id: str
    levels: tuple[BookLevel, ...]
    observed_at: datetime
    received_at: datetime
    state: str
    delay_seconds: int
    time_inferred: bool
    source_sha256: str


@dataclass(frozen=True, kw_only=True)
class Metrics:
    spread: Decimal | None = None
    imbalance: Decimal | None = None
    window_return: Decimal | None = None
    vwap: Decimal | None = None
    sample_count: int = 0
    window_seconds: int = WINDOW_SECONDS


@dataclass(frozen=True, kw_only=True)
class InstrumentSnapshot:
    tr_key: str
    market: str
    trade: TradeTick | None
    book: OrderBook | None
    trades: tuple[TradeTick, ...]
    metrics: Metrics
    trade_stale: bool
    book_stale: bool
    continuity_breaks: int = 0


@dataclass(frozen=True, kw_only=True)
class SessionSnapshot:
    status: str
    reason: str
    connected_at: datetime | None
    last_received_at: datetime | None
    subscriptions: tuple[Subscription, ...]
    instruments: tuple[InstrumentSnapshot, ...]
    reconnect_count: int


@dataclass(frozen=True, kw_only=True)
class ControlFrame:
    kind: str
    tr_id: str = ""
    tr_key: str = ""
    pong: bytes = b""


def _normalizable(channel):
    if channel.normalization != "decimal" or not channel.timezone or not channel.time_field:
        return False
    if channel.kind in ("trade", "indicator"):
        return bool(channel.price_field)
    return (channel.kind == "book" and bool(channel.ask_fields)
            and len(channel.ask_fields) == len(channel.bid_fields)
            == len(channel.ask_size_fields) == len(channel.bid_size_fields))


def supported_channels(environment="production") -> tuple[Channel, ...]:
    _require(environment in ("production", "paper"), "INVALID_SUBSCRIPTION")
    return tuple(channel for channel in CHANNELS.values()
                 if _normalizable(channel) and (environment == "production" or channel.paper))


def _subscriptions(subscriptions, environment):
    _require(type(subscriptions) is tuple and 1 <= len(subscriptions) <= MAX_SUBSCRIPTIONS
             and environment in ("production", "paper"), "INVALID_SUBSCRIPTION")
    seen, instrument_kinds = set(), set()
    for sub in subscriptions:
        _require(type(sub) is Subscription, "INVALID_SUBSCRIPTION")
        try:
            channel = validate_subscription(sub.tr_id, sub.tr_key, paper=environment == "paper")
        except (ValueError, TypeError):
            raise KISLiveError("INVALID_SUBSCRIPTION") from None
        _require(_normalizable(channel), "UNSUPPORTED_NORMALIZATION")
        pair = (sub.tr_id, sub.tr_key)
        kind_key = (channel.market, sub.tr_key, "book" if channel.kind == "book" else "price")
        _require(pair not in seen and kind_key not in instrument_kinds, "INVALID_SUBSCRIPTION")
        seen.add(pair); instrument_kinds.add(kind_key)
    return subscriptions


def _observed(channel, fields, received):
    clock = fields[channel.time_field]
    _require(re.fullmatch(r"[0-9]{6}", clock) is not None, "INVALID_FRAME")
    try:
        hour, minute, second = int(clock[:2]), int(clock[2:4]), int(clock[4:])
        zone = ZoneInfo(channel.timezone)
        if channel.date_field:
            day = fields[channel.date_field]
            _require(re.fullmatch(r"[0-9]{8}", day) is not None, "INVALID_FRAME")
            stamp = datetime(int(day[:4]), int(day[4:6]), int(day[6:]), hour, minute, second, tzinfo=zone)
            inferred = False
        else:
            local = received.astimezone(zone)
            day = local.date()
            base = datetime(day.year, day.month, day.day, hour, minute, second, tzinfo=zone)
            stamp = min((base-timedelta(days=1), base, base+timedelta(days=1)), key=lambda t:abs(received-t))
            inferred = True
        stamp = stamp.astimezone(timezone.utc)
        _require(timedelta(seconds=-2) <= received-stamp <= timedelta(days=4), "INVALID_FRAME")
        return stamp, inferred
    except (ValueError, OverflowError, KeyError):
        raise KISLiveError("INVALID_FRAME") from None


def _state(channel, fields, delay):
    if delay:
        return "delayed"
    if channel.state_field:
        state = fields[channel.state_field]
        if state in channel.indicative_values:
            return "indicative"
        if state not in channel.regular_values:
            return "unknown"
    return "indicator" if channel.kind == "indicator" else "reported"


def _side(price_text, size_text):
    price, size = _decimal(price_text, optional=True), _decimal(size_text, optional=True)
    if price is None or size is None or price == 0 or size == 0:
        _require(not (price in (None, Decimal(0)) and size is not None and size > 0), "INVALID_FRAME")
        return None, None
    return price, size


def _record(channel, values, subscriptions, received, source_sha):
    fields = dict(zip(channel.fields, values))
    symbol = fields[channel.symbol_field]
    _require(any(sub.tr_id == channel.tr_id and sub.tr_key == symbol for sub in subscriptions),
             "UNSUBSCRIBED_FRAME")
    observed, inferred = _observed(channel, fields, received)
    delay = subscription_delay_seconds(channel.tr_id, symbol)
    state = _state(channel, fields, delay)
    common = dict(symbol=symbol, market=channel.market, tr_id=channel.tr_id,
        observed_at=observed, received_at=received, state=state, delay_seconds=delay,
        time_inferred=inferred, source_sha256=source_sha)
    if channel.kind in ("trade", "indicator"):
        price = _decimal(fields[channel.price_field], positive=True)
        size = _decimal(fields[channel.size_field], optional=True) if channel.size_field else None
        cumulative = (_decimal(fields[channel.cumulative_volume_field], optional=True)
                      if channel.cumulative_volume_field else None)
        session_date = fields.get("TYMD") or fields.get("BSOP_DATE") or None
        if session_date is not None:
            _require(re.fullmatch(r"[0-9]{8}", session_date) is not None, "INVALID_FRAME")
            try:
                datetime.strptime(session_date, "%Y%m%d")
            except ValueError:
                raise KISLiveError("INVALID_FRAME") from None
        return TradeTick(**common, price=price, size=size, cumulative_volume=cumulative,
                         session_date=session_date)
    levels, bids, asks = [], [], []
    missing_bid = missing_ask = False
    for bid_field, ask_field, bid_size, ask_size in zip(channel.bid_fields, channel.ask_fields,
                                                     channel.bid_size_fields, channel.ask_size_fields):
        bid, bsize = _side(fields[bid_field], fields[bid_size])
        ask, asize = _side(fields[ask_field], fields[ask_size])
        if bid is None:
            missing_bid = True
        else:
            _require(not missing_bid and (not bids or bid < bids[-1]), "INVALID_FRAME")
            bids.append(bid)
        if ask is None:
            missing_ask = True
        else:
            _require(not missing_ask and (not asks or ask > asks[-1]), "INVALID_FRAME")
            asks.append(ask)
        if bid is not None or ask is not None:
            levels.append(BookLevel(bid=bid, bid_size=bsize, ask=ask, ask_size=asize))
    _require(state == "indicative" or not bids or not asks or bids[0] <= asks[0], "INVALID_FRAME")
    return OrderBook(**common, levels=tuple(levels))


def _json_object(raw):
    def unique(items):
        result = {}
        for key, value in items:
            _require(key not in result, "INVALID_FRAME")
            result[key] = value
        return result
    def invalid(value):
        raise KISLiveError("INVALID_FRAME")
    try:
        result = json.loads(raw, object_pairs_hook=unique, parse_constant=invalid)
        _require(type(result) is dict, "INVALID_FRAME")
        return result
    except (ValueError, TypeError, UnicodeError, RecursionError):
        raise KISLiveError("INVALID_FRAME") from None


def parse_frame(raw: str | bytes, subscriptions: tuple[Subscription, ...], *, received_at: datetime):
    """Pure bounded market/control parser; preserves market and receipt times."""
    received = _instant(received_at)
    _require(type(raw) in (str, bytes) and 0 < len(raw) <= MAX_FRAME_BYTES, "INVALID_FRAME")
    try:
        data = raw.decode("utf-8") if type(raw) is bytes else raw
        encoded = data.encode("utf-8")
    except UnicodeError:
        raise KISLiveError("INVALID_FRAME") from None
    _require(len(encoded) <= MAX_FRAME_BYTES, "INVALID_FRAME")
    _subscriptions(subscriptions, "production")
    if data.startswith("{"):
        _require(len(encoded) <= _CONTROL_BYTES, "INVALID_FRAME")
        control = _json_object(data)
        header, body = control.get("header"), control.get("body")
        _require(type(header) is dict, "INVALID_FRAME")
        tr_id = header.get("tr_id")
        if tr_id == "PINGPONG":
            _require(set(control) <= {"header", "body"} and body is None
                     and set(header) <= {"tr_id", "datetime"}
                     and ("datetime" not in header or type(header["datetime"]) is str), "INVALID_FRAME")
            return ControlFrame(kind="ping", pong=encoded)
        _require(type(tr_id) is str and any(sub.tr_id == tr_id for sub in subscriptions)
                 and type(body) is dict and header.get("encrypt", "N") == "N", "UNSUBSCRIBED_FRAME")
        key = header.get("tr_key", "")
        _require(type(key) is str and (not key or any(sub.tr_id == tr_id and sub.tr_key == key
                                                    for sub in subscriptions)), "UNSUBSCRIBED_FRAME")
        _require(body.get("rt_cd") == "0", "SUBSCRIPTION_REJECTED")
        # No keys, decryption material or remote messages leave this parser.
        return ControlFrame(kind="subscribed", tr_id=tr_id, tr_key=key)
    pieces = data.split("|", 3)
    _require(len(pieces) == 4 and pieces[0] == "0", "INVALID_FRAME")
    tr_id, count_text, payload = pieces[1:]
    _require(tr_id in CHANNELS and any(sub.tr_id == tr_id for sub in subscriptions), "UNSUBSCRIBED_FRAME")
    channel = CHANNELS[tr_id]
    _require(_normalizable(channel) and re.fullmatch(r"[0-9]{1,3}", count_text) is not None, "INVALID_FRAME")
    count = int(count_text)
    _require(1 <= count <= MAX_RECORDS, "INVALID_FRAME")
    values = payload.split("^")
    _require(len(values) == count*len(channel.fields)
             and all(len(value) <= 128 for value in values), "INVALID_FRAME")
    source_sha = hashlib.sha256(encoded).hexdigest()
    width = len(channel.fields)
    return tuple(_record(channel, values[index*width:(index+1)*width], subscriptions, received, source_sha)
                 for index in range(count))


def subscription_message(sub: Subscription, approval: str) -> str:
    """Build only a validated read-only registration message; never log it."""
    _subscriptions((sub,), "production")
    _require(type(approval) is str and 1 <= len(approval) <= 2048 and approval.isascii()
             and all(32 < ord(char) < 127 for char in approval), "APPROVAL_FAILED")
    return json.dumps({"header":{"approval_key":approval,"custtype":"P","tr_type":"1",
                      "content-type":"utf-8"},
                      "body":{"input":{"tr_id":sub.tr_id,"tr_key":sub.tr_key}}}, separators=(",", ":"))


def _credentials():
    import config
    return config.kis_credentials()


def _approval(url, credentials, post, *, cancelled=None):
    _require(url in (PRODUCTION_APPROVAL_URL, PAPER_APPROVAL_URL), "INVALID_SUBSCRIPTION")
    response = None
    deadline = time.monotonic()+20
    try:
        _require(cancelled is None or not cancelled(), "APPROVAL_FAILED")
        key, secret = credentials()
        _require(type(key) is str and type(secret) is str and bool(key) and bool(secret)
                 and len(key) <= 4096 and len(secret) <= 4096, "NO_CREDENTIALS")
        _require(cancelled is None or not cancelled(), "APPROVAL_FAILED")
        if post is None:
            import requests
            post = requests.post
        response = post(url, json={"grant_type":"client_credentials","appkey":key,"secretkey":secret},
                        headers={"content-type":"application/json; charset=utf-8"},
                        timeout=(5, 8), allow_redirects=False, stream=True)
        key = secret = ""
        _require(response.status_code == 200, "APPROVAL_FAILED")
        data = bytearray()
        # One-byte reads allow a total deadline check even for a trickling body;
        # the fixed socket timeout also bounds a stalled individual read.
        for block in response.iter_content(chunk_size=1):
            _require(cancelled is None or not cancelled(), "APPROVAL_FAILED")
            _require(time.monotonic() <= deadline, "APPROVAL_FAILED")
            _require(type(block) is bytes, "APPROVAL_FAILED")
            data.extend(block)
            _require(len(data) <= 16384, "APPROVAL_FAILED")
        body = _json_object(bytes(data))
        approval = body.get("approval_key")
        _require(type(approval) is str and 1 <= len(approval) <= 2048 and approval.isascii()
                 and all(32 < ord(char) < 127 for char in approval), "APPROVAL_FAILED")
        return approval
    except KISLiveError as exc:
        raise KISLiveError("NO_CREDENTIALS" if str(exc) == "NO_CREDENTIALS" else "APPROVAL_FAILED") from None
    except Exception:
        raise KISLiveError("APPROVAL_FAILED") from None
    finally:
        if response is not None:
            try:
                response.close()
            except Exception:
                pass


def _ratio(value):
    with localcontext() as context:
        context.prec = 34
        return Decimal(value.numerator)/Decimal(value.denominator)


def _fresh(value, now):
    return (value is not None and value.delay_seconds == 0 and value.state not in ("indicative", "unknown")
            and timedelta(seconds=-2) <= now-value.observed_at <= timedelta(seconds=FRESH_SECONDS)
            and timedelta(0) <= now-value.received_at <= timedelta(seconds=FRESH_SECONDS))


def _metrics(trades, book, *, now, trade_fresh, book_fresh):
    spread = imbalance = window_return = vwap = None
    if book_fresh and book is not None and book.levels:
        best = book.levels[0]
        if best.bid is not None and best.ask is not None:
            spread = _ratio(Fraction(best.ask)-Fraction(best.bid))
        bid_sum = sum((Fraction(level.bid_size) for level in book.levels if level.bid_size is not None), Fraction())
        ask_sum = sum((Fraction(level.ask_size) for level in book.levels if level.ask_size is not None), Fraction())
        if bid_sum+ask_sum:
            imbalance = _ratio((bid_sum-ask_sum)/(bid_sum+ask_sum))
    recent = tuple(tick for tick in trades if tick.delay_seconds == 0 and tick.state not in ("indicative", "unknown")
                   and timedelta(0) <= now-tick.observed_at <= timedelta(seconds=WINDOW_SECONDS)
                   and tick.received_at <= now) if trade_fresh else ()
    if len(recent) >= 2:
        window_return = _ratio(Fraction(recent[-1].price)/Fraction(recent[0].price)-1)
    weighted = tuple(tick for tick in recent if tick.size is not None and tick.size > 0 and tick.state == "reported")
    volume = sum((Fraction(tick.size) for tick in weighted), Fraction())
    if volume:
        vwap = _ratio(sum((Fraction(tick.price)*Fraction(tick.size) for tick in weighted), Fraction())/volume)
    return Metrics(spread=spread, imbalance=imbalance, window_return=window_return,
                   vwap=vwap, sample_count=len(recent))


class LiveSession:
    """One explicit connection lifecycle. Stop/close never submits a broker action.

    Injected transports and credentials are for isolated fixtures or a reviewed
    embedding; defaults are loaded only by explicit start. Instances are not
    pickled, cached to disk or shared with the order/strategy runtime.
    """
    def __init__(self, subscriptions: tuple[Subscription, ...], *, environment="production",
                 clock: Callable | None = None, credential_provider: Callable | None = None,
                 http_post: Callable | None = None, connector: Callable | None = None,
                 proxy_mode="system"):
        self.subscriptions = _subscriptions(subscriptions, environment)
        self.environment = environment
        _require(proxy_mode in ("system", "direct"), "INVALID_SUBSCRIPTION")
        self._proxy_mode = proxy_mode
        self._clock = clock or _utc_now
        _require(callable(self._clock), "CLOCK_INVALID")
        self._credentials = credential_provider or _credentials
        self._post, self._connector = http_post, connector
        self._lock, self._stop = RLock(), Event()
        self._thread = self._socket = None
        self._status, self._reason = "stopped", ""
        self._connected_at = self._last_received = self._last_clock = None
        self._reconnects = self._generation = 0
        self._data = {}
        for sub in subscriptions:
            channel = CHANNELS[sub.tr_id]
            self._data.setdefault((channel.market,sub.tr_key),
                {"trade":None,"book":None,"trades":deque(maxlen=MAX_TRADES),
                 "trade_generation":-1,"book_generation":-1,"continuity_breaks":0})

    def _now(self):
        with self._lock:
            try:
                now = _instant(self._clock())
            except Exception:
                raise KISLiveError("CLOCK_INVALID") from None
            _require(self._last_clock is None or now >= self._last_clock, "CLOCK_INVALID")
            self._last_clock = now
        return now

    def start(self):
        with self._lock:
            _subscriptions(self.subscriptions, self.environment)
            _require(self._thread is None or not self._thread.is_alive(), "ALREADY_RUNNING")
            self._stop.clear()
            self._status, self._reason = "connecting", ""
            self._connected_at = self._last_received = self._last_clock = None
            self._reconnects = 0
            self._thread = Thread(target=self._run, name="tradegen-kis-market", daemon=True)
            self._thread.start()

    def stop(self, timeout=3.0):
        _require(type(timeout) in (int,float) and 0 <= timeout <= 10, "STOP_TIMEOUT")
        self._stop.set()
        with self._lock:
            socket, thread = self._socket, self._thread
        if socket is not None:
            try:
                socket.close()
            except Exception:
                pass
        if thread is not None and thread is not current_thread():
            thread.join(timeout)
        with self._lock:
            pending = thread is not None and thread.is_alive()
            self._status = "stopping" if pending else "stopped"
            self._reason = "STOP_TIMEOUT" if pending else ""

    def _set(self, status, reason=""):
        with self._lock:
            self._status, self._reason = status, reason

    def _accept(self, events):
        with self._lock:
            for event in events:
                state = self._data[(event.market,event.symbol)]
                key = "trade" if type(event) is TradeTick else "book"
                prior = state[key] if state[key+"_generation"] == self._generation else None
                _require(prior is None or event.observed_at >= prior.observed_at, "OUT_OF_ORDER_FRAME")
                if (key == "trade" and event.state != "indicator" and prior is not None
                        and event.cumulative_volume is not None):
                    known_session = event.session_date is not None and prior.session_date is not None
                    changed_session = known_session and event.session_date != prior.session_date
                    dropped = prior.cumulative_volume is not None and event.cumulative_volume < prior.cumulative_volume
                    if changed_session or (dropped and not known_session):
                        state["trades"].clear()
                        state["continuity_breaks"] += 1
                    elif prior.cumulative_volume is not None:
                        _require(not dropped, "OUT_OF_ORDER_FRAME")
                        if event.cumulative_volume == prior.cumulative_volume:
                            continue  # Repeated cumulative tick is not another real trade.
                state[key], state[key+"_generation"] = event, self._generation
                if key == "trade" and (event.state == "indicator" or (event.size is not None and event.size > 0)):
                    state["trades"].append(event)
                    while state["trades"] and event.received_at-state["trades"][0].received_at > timedelta(seconds=300):
                        state["trades"].popleft()

    def _run(self):
        approval = ""
        try:
            _subscriptions(self.subscriptions, self.environment)
            endpoint = PRODUCTION_APPROVAL_URL if self.environment == "production" else PAPER_APPROVAL_URL
            address = PRODUCTION_WS_URL if self.environment == "production" else PAPER_WS_URL
            self._now()
            if self._stop.is_set():
                return
            approval = _approval(endpoint, self._credentials, self._post, cancelled=self._stop.is_set)
            if self._stop.is_set():
                return
            connector = self._connector
            if connector is None:
                from websockets.sync.client import connect
                connector = connect
            quiet = logging.Logger("tradegen-kis-market-wire", level=logging.CRITICAL)
            quiet.disabled = True
            for attempt in range(3):
                if self._stop.is_set():
                    return
                with self._lock:
                    self._generation += 1
                    self._reconnects = attempt
                    for state in self._data.values():
                        state["trades"].clear()
                        if attempt:
                            state["continuity_breaks"] += 1
                self._set("connecting" if attempt == 0 else "reconnecting")
                socket = None
                try:
                    socket = connector(address, open_timeout=8, close_timeout=1, ping_interval=None,
                                       max_size=MAX_FRAME_BYTES, max_queue=16, logger=quiet,
                                       proxy=True if self._proxy_mode == "system" else None)
                    with self._lock:
                        self._socket = socket
                        self._connected_at = self._now()
                    if self._stop.is_set():
                        return
                    for sub in self.subscriptions:
                        socket.send(subscription_message(sub, approval))
                    acknowledged = set()
                    last_frame = self._now()
                    opened = last_frame
                    while not self._stop.is_set():
                        try:
                            raw = socket.recv(timeout=1)
                        except TimeoutError:
                            now = self._now()
                            _require(now-last_frame <= timedelta(seconds=60), "IDLE_TIMEOUT")
                            _require(len(acknowledged) == len(self.subscriptions)
                                     or now-opened <= timedelta(seconds=15), "SUBSCRIPTION_REJECTED")
                            continue
                        now = self._now()
                        parsed = parse_frame(raw, self.subscriptions, received_at=now)
                        last_frame = now
                        with self._lock:
                            self._last_received = now
                        if type(parsed) is ControlFrame:
                            if parsed.kind == "ping":
                                socket.pong(parsed.pong)
                            else:
                                candidates = tuple(sub for sub in self.subscriptions if sub.tr_id == parsed.tr_id
                                                   and (not parsed.tr_key or sub.tr_key == parsed.tr_key))
                                _require(len(candidates) == 1, "SUBSCRIPTION_REJECTED")
                                acknowledged.add(candidates[0])
                        else:
                            self._accept(parsed)
                        if len(acknowledged) == len(self.subscriptions):
                            self._set("streaming")
                except KISLiveError as exc:
                    if self._stop.is_set():
                        return
                    self._set("error", str(exc))
                    return
                except Exception:
                    if self._stop.is_set():
                        return
                    self._set("reconnecting", "DISCONNECTED" if socket is not None else "CONNECTION_FAILED")
                finally:
                    if socket is not None:
                        try:
                            socket.close()
                        except Exception:
                            pass
                    with self._lock:
                        self._socket = None
                if attempt < 2 and self._stop.wait(2**attempt):
                    return
            self._set("error", "RECONNECT_LIMIT")
        except KISLiveError as exc:
            self._set("error", str(exc))
        except Exception:
            self._set("error", "CONNECTION_FAILED")
        finally:
            approval = ""
            if self._stop.is_set():
                self._set("stopped")

    def snapshot(self, *, now=None) -> SessionSnapshot:
        now = self._now() if now is None else _instant(now)
        with self._lock:
            active = self._status == "streaming" and not self._stop.is_set()
            output = []
            for (market,key), state in self._data.items():
                trade, book = state["trade"], state["book"]
                tf = active and state["trade_generation"] == self._generation and _fresh(trade,now)
                bf = active and state["book_generation"] == self._generation and _fresh(book,now)
                trades = tuple(state["trades"])
                output.append(InstrumentSnapshot(tr_key=key, market=market, trade=trade, book=book,
                    trades=tuple(tick for tick in trades[-20:] if tick.state != "indicator"),
                    metrics=_metrics(trades,book,now=now,trade_fresh=tf,book_fresh=bf),
                    trade_stale=not tf, book_stale=not bf, continuity_breaks=state["continuity_breaks"]))
            pending = self._stop.is_set() and self._thread is not None and self._thread.is_alive()
            status = "stopping" if pending else "stopped" if self._stop.is_set() else self._status
            reason = "STOP_TIMEOUT" if pending else "" if self._stop.is_set() else self._reason
            return SessionSnapshot(status=status, reason=reason,
                connected_at=self._connected_at, last_received_at=self._last_received,
                subscriptions=self.subscriptions, instruments=tuple(output), reconnect_count=self._reconnects)
