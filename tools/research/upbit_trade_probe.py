"""A0: bounded public-market measurements, never account or execution evidence.

Only the explicit CLI --allow-public-network enables HTTP. Importing this module
does not load app code, keys, configuration, a home directory, or a network client.
"""
from __future__ import annotations

import argparse
import base64
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from email.utils import parsedate_to_datetime
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
import time
from urllib import error, parse, request


ORIGIN = "https://api.upbit.com"
SCHEMA = "tradegen-upbit-a0-v1"
MAX_BODY = 2 * 1024 * 1024
MAX_LINE = 3 * 1024 * 1024
MAX_ARCHIVE = 1024 * 1024 * 1024
SETTLE_TOLERANCE_SECONDS = 0.1
PATHS = frozenset(("/v1/trades/ticks", "/v1/trades/ticks/", "/v1/ticker", "/v1/candles/minutes/1"))
UTC = timezone.utc


class ProbeError(Exception):
    """Public fixed diagnostic; never forward HTTP/OS exception strings."""


class ProbeStop(ProbeError):
    pass


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("ascii")


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def utc_text(value):
    return datetime.fromtimestamp(value, UTC).isoformat(timespec="milliseconds")


def _number(value):
    if isinstance(value, bool) or not isinstance(value, (str, int, float, Decimal)):
        raise ProbeError("MALFORMED_RESPONSE")
    text = str(value)
    if len(text) > 128:
        raise ProbeError("MALFORMED_RESPONSE")
    try:
        out = Decimal(text)
    except InvalidOperation:
        raise ProbeError("MALFORMED_RESPONSE") from None
    if not out.is_finite() or out <= 0 or len(out.as_tuple().digits) > 64 or not -64 <= out.as_tuple().exponent <= 64 or not -64 <= out.adjusted() <= 64:
        raise ProbeError("MALFORMED_RESPONSE")
    # Decimal.normalize uses ambient precision and can silently round a price.
    fixed = format(out, "f")
    return fixed.rstrip("0").rstrip(".") if "." in fixed else fixed


def _integer(value):
    if type(value) is not int or value < 0:
        raise ProbeError("MALFORMED_RESPONSE")
    return value


def parse_trades(body, market):
    if type(body) is not list or len(body) > 500:
        raise ProbeError("MALFORMED_RESPONSE")
    rows = []
    for item in body:
        if type(item) is not dict or item.get("market") != market or item.get("ask_bid") not in ("ASK", "BID"):
            raise ProbeError("MALFORMED_RESPONSE")
        rows.append({"id": _integer(item.get("sequential_id")), "timestamp": _integer(item.get("timestamp")),
                     "price": _number(item.get("trade_price")), "volume": _number(item.get("trade_volume")),
                     "ask_bid": item["ask_bid"]})
    return rows


def _json(raw, *, decimals=True):
    def pairs(items):
        out = {}
        for key, value in items:
            if key in out:
                raise ProbeError("MALFORMED_RESPONSE")
            out[key] = value
        return out
    try:
        return json.loads(raw, object_pairs_hook=pairs, parse_float=Decimal if decimals else float,
                          parse_constant=lambda _: (_ for _ in ()).throw(ProbeError("MALFORMED_RESPONSE")))
    except (ValueError, UnicodeError, RecursionError):
        raise ProbeError("MALFORMED_RESPONSE") from None


@dataclass(frozen=True)
class Config:
    market: str
    interval_seconds: int = 5
    max_pages: int = 20
    requests_per_second: float = 2.0
    trailing_slash: bool = False

    def validate(self):
        if not re.fullmatch(r"KRW-[A-Z0-9]{1,20}", self.market):
            raise ProbeError("INVALID_MARKET")
        if type(self.interval_seconds) is not int or not 1 <= self.interval_seconds <= 3600:
            raise ProbeError("INVALID_INTERVAL")
        if type(self.max_pages) is not int or not 1 <= self.max_pages <= 100:
            raise ProbeError("INVALID_PAGE_BOUND")
        if type(self.requests_per_second) not in (int, float) or not math.isfinite(self.requests_per_second) or not 0 < self.requests_per_second <= 5:
            raise ProbeError("INVALID_RATE")
        if type(self.trailing_slash) is not bool:
            raise ProbeError("INVALID_CONFIG")
        return self

    def document(self):
        self.validate()
        return {"market": self.market, "interval_seconds": self.interval_seconds, "max_pages": self.max_pages,
                "requests_per_second": self.requests_per_second, "trailing_slash": self.trailing_slash}


@dataclass(frozen=True)
class Reply:
    status: int
    headers: dict
    body: bytes
    truncated: bool = False


class Clock:
    wall = staticmethod(time.time)
    monotonic = staticmethod(time.monotonic)
    sleep = staticmethod(time.sleep)


class _NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def public_request(path, params):
    """Fixed host GET only; no ambient proxy credentials, redirect, or Origin."""
    allowed = {"/v1/trades/ticks": {"market", "count", "to", "days_ago", "cursor"},
               "/v1/trades/ticks/": {"market", "count"},
               "/v1/ticker": {"markets"}, "/v1/candles/minutes/1": {"market", "count", "to"}}
    if path not in PATHS or type(params) is not dict or not set(params) <= allowed[path]:
        raise ProbeError("REQUEST_NOT_ALLOWED")
    if any(not isinstance(k, str) or type(v) not in (str, int) for k, v in params.items()):
        raise ProbeError("REQUEST_NOT_ALLOWED")
    opener = request.build_opener(request.ProxyHandler({}), _NoRedirect())
    req = request.Request(ORIGIN + path + "?" + parse.urlencode(params), method="GET",
                          headers={"Accept": "application/json", "User-Agent": "TRADEGEN-A0/1"})
    try:
        response = opener.open(req, timeout=10)
    except error.HTTPError as exc:
        response = exc
    with response:
        raw = response.read(MAX_BODY + 1)
        headers = {k.lower(): v for k, v in response.headers.items()
                   if k.lower() in ("date", "remaining-req", "retry-after", "content-type")}
        return Reply(response.status, headers, raw[:MAX_BODY], len(raw) > MAX_BODY)


def _ordinary(path, directory=False):
    info = path.lstat()
    if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
        raise ProbeError("ARCHIVE_PATH_REFUSED")
    if directory:
        if not stat.S_ISDIR(info.st_mode):
            raise ProbeError("ARCHIVE_PATH_REFUSED")
    elif not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise ProbeError("ARCHIVE_PATH_REFUSED")


class Archive:
    """Exclusive append log. Resume preserves all prior sessions and failures.

    A torn final row is deliberately refused, never silently truncated. This is
    measurement storage, not a signed research bundle or secure owner ledger.
    """
    def __init__(self, root, config):
        self.root = Path(root).absolute()
        if any(x.casefold() in (".tradegen", ".nextgen") for x in self.root.parts):
            raise ProbeError("ARCHIVE_PATH_REFUSED")
        for parent in reversed((self.root, *self.root.parents)):
            if parent.exists() or parent.is_symlink():
                _ordinary(parent, directory=True)
        self.root.mkdir(parents=True, exist_ok=True)
        _ordinary(self.root, directory=True)
        self.path = self.root / "observations.jsonl"
        self.lock = self.root / ".probe.lock"
        self.lock_fd = None
        self.seq = 0
        self.previous = "0" * 64
        try:
            self.lock_fd = os.open(self.lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            if self.path.exists() or self.path.is_symlink():
                _ordinary(self.path)
                if self.path.stat().st_size > MAX_ARCHIVE:
                    raise ProbeError("ARCHIVE_RESOURCE_LIMIT")
                with self.path.open("rb") as stream:
                    first = True
                    while True:
                        line = stream.readline(MAX_LINE + 1)
                        if not line:
                            break
                        if len(line) > MAX_LINE or not line.endswith(b"\n"):
                            raise ProbeError("ARCHIVE_INCOMPLETE")
                        row = _json(line, decimals=False)
                        if type(row) is not dict or set(row) != {"seq", "previous", "data", "sha256"}:
                            raise ProbeError("ARCHIVE_INVALID")
                        sha = row.pop("sha256")
                        if row["seq"] != self.seq or row["previous"] != self.previous or digest(row) != sha:
                            raise ProbeError("ARCHIVE_INVALID")
                        if first and row["data"] != {"kind": "config", "schema": SCHEMA, "config": config.document()}:
                            raise ProbeError("ARCHIVE_CONFIG_MISMATCH")
                        first = False
                        self.seq += 1
                        self.previous = sha
                if first:
                    raise ProbeError("ARCHIVE_INCOMPLETE")
            else:
                self.append({"kind": "config", "schema": SCHEMA, "config": config.document()})
        except BaseException:
            self.close()
            raise

    def append(self, data):
        if self.lock_fd is None:
            raise ProbeError("ARCHIVE_NOT_LOCKED")
        row = {"seq": self.seq, "previous": self.previous, "data": data}
        sha = digest(row)
        raw = canonical({**row, "sha256": sha}) + b"\n"
        if len(raw) > MAX_LINE:
            raise ProbeError("ARCHIVE_RESOURCE_LIMIT")
        if self.path.exists() or self.path.is_symlink():
            _ordinary(self.path)
            if self.path.stat().st_size + len(raw) > MAX_ARCHIVE:
                raise ProbeError("ARCHIVE_RESOURCE_LIMIT")
        flags = os.O_CREAT | os.O_APPEND | os.O_WRONLY | getattr(os, "O_NOFOLLOW", 0)
        fd = os.open(self.path, flags, 0o600)
        try:
            current = os.fstat(fd)
            if not stat.S_ISREG(current.st_mode) or current.st_nlink != 1:
                raise ProbeError("ARCHIVE_PATH_REFUSED")
            with os.fdopen(fd, "ab", closefd=False) as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(fd)
        finally:
            os.close(fd)
        self.previous, self.seq = sha, self.seq + 1
        return self.seq - 1

    def close(self):
        if self.lock_fd is not None:
            os.close(self.lock_fd)
            self.lock_fd = None
            self.lock.unlink()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()


class Probe:
    def __init__(self, config, transport, archive, clock=None):
        self.config = config.validate()
        self.transport = transport
        self.archive = archive
        self.clock = clock or Clock()
        self.next_request = 0.0
        self.last_wall = self.clock.wall()
        self.first_seen = {}
        self.max_seen = 200000
        self.last_response_timing = None

    def _wait_until(self, target):
        delay = target - self.clock.wall()
        if delay > 0:
            self.clock.sleep(delay)

    def read(self, path, params, purpose):
        if path not in PATHS:
            raise ProbeError("REQUEST_NOT_ALLOWED")
        delay = self.next_request - self.clock.monotonic()
        if delay > 0:
            self.clock.sleep(delay)
        start = self.clock.wall()
        tick = self.clock.monotonic()
        if start < self.last_wall:
            raise ProbeStop("CLOCK_ROLLBACK")
        self.next_request = tick + 1 / self.config.requests_per_second
        try:
            reply = self.transport(path, dict(params))
        except (OSError, error.URLError, TimeoutError):
            self.archive.append({"kind": "response", "purpose": purpose, "path": path, "params": params,
                                 "sent_at": utc_text(start), "received_at": utc_text(self.clock.wall()),
                                 "error": "TRANSPORT_FAILED"})
            raise ProbeStop("TRANSPORT_FAILED") from None
        end, finish = self.clock.wall(), self.clock.monotonic()
        if type(reply) is not Reply or type(reply.body) is not bytes or len(reply.body) > MAX_BODY:
            raise ProbeStop("TRANSPORT_CONTRACT_INVALID")
        headers = {k.lower(): v for k, v in reply.headers.items()
                   if k.lower() in ("date", "remaining-req", "retry-after", "content-type")}
        date = None
        try:
            date = parsedate_to_datetime(headers.get("date", "")).timestamp()
        except (ValueError, TypeError, OverflowError):
            pass
        latency = finish - tick
        observation = {"kind": "response", "purpose": purpose, "path": path, "params": params,
                       "sent_at": utc_text(start), "received_at": utc_text(end), "latency_seconds": latency,
                       "status": reply.status, "headers": headers, "body_base64": base64.b64encode(reply.body).decode("ascii"),
                       "body_sha256": hashlib.sha256(reply.body).hexdigest(), "body_truncated": reply.truncated,
                       "date_offset_seconds": None if date is None else date - (start + end) / 2,
                       "date_offset_uncertainty_seconds": None if date is None else 1 + latency / 2}
        self.archive.append(observation)
        self.last_response_timing = (start, end)
        self.last_wall = end
        if end < start or finish < tick:
            raise ProbeStop("CLOCK_ROLLBACK")
        if reply.status in (418, 429):
            # Stop the entire run. The owner can honour Retry-After before a new run.
            raise ProbeStop("RATE_LIMIT_STOP_" + str(reply.status))
        if reply.truncated:
            raise ProbeStop("RESPONSE_TOO_LARGE")
        if not 200 <= reply.status < 300:
            if purpose == "trailing_slash":
                return None, date, reply.status
            raise ProbeStop("HTTP_REFUSED")
        return _json(reply.body), date, reply.status

    def walk(self, start_ms, end_ms, purpose):
        """Observe bounded pages; 'bounded' is not proof of source completeness."""
        start = datetime.fromtimestamp(start_ms / 1000, UTC)
        end = datetime.fromtimestamp((end_ms - 1) / 1000, UTC)
        days = (end.date() - start.date()).days
        if days > 1:
            raise ProbeStop("INTERVAL_BOUND_INVALID")
        rows, page_count, all_bounded = {}, 0, True
        first_trade_request_at = None
        last_trade_response_at = None
        for index in range(days + 1):
            day = start.date() + timedelta(days=index)
            lower = max(start_ms, int(datetime.combine(day, datetime.min.time(), UTC).timestamp() * 1000))
            upper = min(end_ms, int(datetime.combine(day + timedelta(days=1), datetime.min.time(), UTC).timestamp() * 1000))
            # 23:59:59 cannot encode next UTC midnight in a date-relative `to`.
            # Omit `to` for the final second; timestamp filtering retains [S,E).
            ceiling = math.ceil(upper / 1000) + 1
            bound_time = datetime.fromtimestamp(ceiling, UTC)
            params = {"market": self.config.market, "count": 500}
            if bound_time.date() == day:
                params["to"] = bound_time.strftime("%H:%M:%S")
            days_ago = (datetime.fromtimestamp(self.clock.wall(), UTC).date() - day).days
            if not 0 <= days_ago <= 6:
                raise ProbeStop("DAY_OUTSIDE_REACH")
            if days_ago:
                params["days_ago"] = days_ago
            previous_cursor = None
            bounded = False
            for _ in range(self.config.max_pages):
                raw, server_date, _status = self.read("/v1/trades/ticks", params, purpose)
                if first_trade_request_at is None:
                    first_trade_request_at = self.last_response_timing[0]
                last_trade_response_at = self.last_response_timing[1]
                page_count += 1
                if server_date is None:
                    raise ProbeStop("DATE_HEADER_REQUIRED")
                actual_day = datetime.fromtimestamp(server_date, UTC).date() - timedelta(days=days_ago)
                if actual_day != day:
                    raise ProbeStop("SERVER_DAY_MISMATCH")
                trades = parse_trades(raw, self.config.market)
                for item in trades:
                    if item["id"] in rows and rows[item["id"]] != item:
                        raise ProbeStop("TRADE_ID_CHANGED")
                    rows[item["id"]] = item
                    if item["id"] not in self.first_seen:
                        if len(self.first_seen) >= self.max_seen:
                            raise ProbeStop("OBSERVATION_LIMIT")
                        self.first_seen[item["id"]] = self.last_response_timing[1]
                if not trades or any(x["timestamp"] < lower for x in trades):
                    bounded = True
                    break
                # Cursor is taken from the last received row, never sorted by id.
                cursor = trades[-1]["id"]
                if previous_cursor == cursor:
                    raise ProbeStop("CURSOR_NOT_PROGRESSING")
                previous_cursor = cursor
                params = {**params, "cursor": str(cursor)}
            all_bounded = all_bounded and bounded
        kept = sorted((x for x in rows.values() if start_ms <= x["timestamp"] < end_ms), key=lambda x: (x["timestamp"], x["id"]))
        return {"rows": kept, "observed_marks": sorted({(x["timestamp"], x["price"]) for x in rows.values()}),
                "walk_to_bound_ms": (math.ceil(end_ms / 1000) + 1) * 1000,
                "first_trade_request_at": first_trade_request_at, "last_trade_response_at": last_trade_response_at,
                "pages": page_count, "range_walk_bounded": all_bounded, "source_complete": False}

    def sample(self, start_ms, end_ms, target_settle, attempt):
        started = self.clock.monotonic()
        actual_settle = self.clock.wall() - end_ms / 1000
        ticker, _, _ = self.read("/v1/ticker", {"markets": self.config.market}, "ticker")
        wait_started = self.clock.monotonic()
        self._wait_until(end_ms / 1000 + target_settle)
        scheduled_wait = self.clock.monotonic() - wait_started
        walked = self.walk(start_ms, end_ms, "trades")
        trade_settle = walked["first_trade_request_at"] - end_ms / 1000
        minute_end = end_ms // 60000 * 60
        candle_to = utc_text(minute_end).replace("+00:00", "Z")
        candles, _, _ = self.read("/v1/candles/minutes/1", {"market": self.config.market, "count": 1, "to": candle_to}, "candle")
        if type(ticker) is not list or len(ticker) != 1 or type(ticker[0]) is not dict or ticker[0].get("market") != self.config.market:
            raise ProbeStop("MALFORMED_TICKER")
        tick_stamp, tick_price = _integer(ticker[0].get("trade_timestamp")), _number(ticker[0].get("trade_price"))
        comparable = start_ms <= tick_stamp < walked["walk_to_bound_ms"]
        ticker_match = None if not comparable else (tick_stamp, tick_price) in walked["observed_marks"]
        if type(candles) is not list or len(candles) > 1 or any(type(x) is not dict or x.get("market") != self.config.market for x in candles):
            raise ProbeStop("MALFORMED_CANDLE")
        # Canonical decimal values are strings, preserving exact observed fields.
        candle = None if not candles else {k: str(v) if isinstance(v, Decimal) else v for k, v in candles[0].items()}
        candle_stamp = None
        if candle is not None:
            try:
                candle_time = datetime.fromisoformat(candle["candle_date_time_utc"])
                if candle_time.tzinfo is None:
                    candle_time = candle_time.replace(tzinfo=UTC)
                candle_stamp = candle_time.timestamp()
            except (KeyError, TypeError, ValueError, OverflowError):
                raise ProbeStop("MALFORMED_CANDLE") from None
        candle_target_match = candle_stamp == minute_end - 60
        same_ms = defaultdict(set)
        for row in walked["rows"]:
            same_ms[row["timestamp"]].add(row["price"])
        result = {"kind": "sample", "start_ms": start_ms, "end_ms": end_ms, "target_settle_seconds": target_settle,
                  "actual_settle_seconds": actual_settle, "attempt": attempt, **walked,
                  "actual_trade_settle_seconds": trade_settle,
                  "trade_settle_tolerance_seconds": SETTLE_TOLERANCE_SECONDS,
                  "trade_settle_target_met": abs(trade_settle - target_settle) <= SETTLE_TOLERANCE_SECONDS,
                  "ticker_comparable": comparable, "ticker_match": ticker_match,
                  "candle": candle, "candle_target_minute_end": candle_to,
                  "candle_observed_minute_start": None if candle_stamp is None else utc_text(candle_stamp),
                  "candle_target_match": candle_target_match,
                  "same_ms_multi_price": {str(k): sorted(v, key=Decimal) for k, v in same_ms.items() if len(v) > 1},
                  "ask_bid_counts": dict(Counter(x["ask_bid"] for x in walked["rows"])),
                  "ask_bid_semantics": "UNRESOLVED_WITH_PUBLIC_ONLY_DATA",
                  "first_seen_delay_seconds": {str(x["id"]): self.first_seen[x["id"]] - x["timestamp"] / 1000 for x in walked["rows"]},
                  "unit_seconds": self.clock.monotonic() - started,
                  "scheduled_settle_wait_seconds": scheduled_wait,
                  "public_read_seconds": self.clock.monotonic() - started - scheduled_wait,
                  "crosses_0900_kst": datetime.fromtimestamp(start_ms / 1000, UTC).date() != datetime.fromtimestamp((end_ms - 1) / 1000, UTC).date()}
        self.archive.append(result)
        return result

    def run(self, cycles=1, pause_seconds=5):
        if type(cycles) is not int or not 1 <= cycles <= 100000 or type(pause_seconds) not in (int, float) or not math.isfinite(pause_seconds) or pause_seconds < 0:
            raise ProbeError("INVALID_RUN_BOUND")
        session = {"kind": "session_start", "at": utc_text(self.clock.wall()), "cycles": cycles}
        session_id = self.archive.append(session)
        completed = 0
        observed_no_go = False
        try:
            if self.config.trailing_slash:
                _, _, status = self.read("/v1/trades/ticks/", {"market": self.config.market, "count": 1}, "trailing_slash")
                self.archive.append({"kind": "slash_result", "status": status, "refused": not 200 <= status < 300})
            for _ in range(cycles):
                samples = []
                pairs = []
                for settle in (0.5, 1.0, 2.0):
                    # Fresh interval per target. Leave time for ticker and pacing;
                    # an unusually slow response still marks a missed target.
                    pacing_delay = max(0, self.next_request - self.clock.monotonic())
                    end_ms = (math.ceil(self.clock.wall() + pacing_delay) + 1) * 1000
                    start_ms = end_ms - self.config.interval_seconds * 1000
                    group = []
                    for attempt in (1, 2):
                        group.append(self.sample(start_ms, end_ms, settle, attempt))
                    samples.extend(group)
                    a, b = group
                    pairs.append({"start_ms": start_ms, "end_ms": end_ms,
                                  "target_settle_seconds": a["target_settle_seconds"], "equal": a["rows"] == b["rows"],
                                  "actual_settles_seconds": [a["actual_trade_settle_seconds"], b["actual_trade_settle_seconds"]],
                                  "first_trade_settle_target_met": a["trade_settle_target_met"],
                                  "repeat_is_later_observation": True,
                                  "candle_target_match": a["candle_target_match"] and b["candle_target_match"],
                                  "candle_stable_in_observation_window": a["candle"] == b["candle"] if a["candle_target_match"] and b["candle_target_match"] else None})
                blockers = []
                if not all(x["range_walk_bounded"] for x in samples):
                    blockers.append("PAGE_BOUND_REACHED")
                if any(x["ticker_match"] is False for x in samples):
                    blockers.append("TICKER_MISMATCH")
                if any(not x["equal"] for x in pairs):
                    blockers.append("REPEATED_WINDOW_CHANGED")
                if any(x["public_read_seconds"] > 5 for x in samples):
                    blockers.append("PUBLIC_READ_UNIT_OVER_FIVE_SECONDS")
                report = {"kind": "cycle_report", "session_id": session_id,
                          "pairs": pairs, "cross_settle_comparison": "INDEPENDENT_WINDOWS_NOT_COMPARED",
                          "all_first_trade_settle_targets_met": all(x["first_trade_settle_target_met"] for x in pairs),
                          "candle_finality_proven": False,
                          "walks_bounded": all(x["range_walk_bounded"] for x in samples),
                          "max_unit_seconds": max(x["unit_seconds"] for x in samples),
                          "max_public_read_seconds": max(x["public_read_seconds"] for x in samples),
                          "public_read_unit_within_five_seconds": all(x["public_read_seconds"] <= 5 for x in samples),
                          "whole_account_unit_timing": "NOT_MEASURED",
                          "crosses_0900_kst": any(x["crosses_0900_kst"] for x in samples),
                          "decision": "NO_GO_OBSERVED" if blockers else "REVIEW_REQUIRED", "observed_blockers": blockers,
                          "source_complete": False, "execution_ready": False}
                self.archive.append(report)
                observed_no_go = observed_no_go or bool(blockers)
                completed += 1
                if completed < cycles:
                    self.clock.sleep(pause_seconds)
        except (ProbeError, KeyboardInterrupt) as exc:
            code = str(exc) if isinstance(exc, ProbeError) else "INTERRUPTED"
            self.archive.append({"kind": "session_stop", "session_id": session_id, "completed_cycles": completed, "code": code})
            if isinstance(exc, KeyboardInterrupt):
                return {"completed_cycles": completed, "status": "INTERRUPTED", "execution_ready": False}
            raise
        self.archive.append({"kind": "session_end", "session_id": session_id, "completed_cycles": completed})
        return {"completed_cycles": completed, "status": "NO_GO_OBSERVED" if observed_no_go else "REVIEW_REQUIRED", "execution_ready": False}


def main(argv=None):
    parser = argparse.ArgumentParser(description="A0 public-only measurement; no orders, keys, or completeness certification.")
    parser.add_argument("--market", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cycles", type=int, default=1)
    parser.add_argument("--interval-seconds", type=int, default=5)
    parser.add_argument("--max-pages", type=int, default=20)
    parser.add_argument("--requests-per-second", type=float, default=2)
    parser.add_argument("--pause-seconds", type=float, default=5)
    parser.add_argument("--probe-trailing-slash", action="store_true")
    parser.add_argument("--allow-public-network", action="store_true")
    args = parser.parse_args(argv)
    if not args.allow_public_network:
        parser.error("public reads require --allow-public-network; no request was made")
    try:
        config = Config(args.market, args.interval_seconds, args.max_pages, args.requests_per_second, args.probe_trailing_slash).validate()
        with Archive(args.output, config) as archive:
            result = Probe(config, public_request, archive).run(args.cycles, args.pause_seconds)
        print(json.dumps(result, sort_keys=True))
        return 0
    except ProbeError as exc:
        print(json.dumps({"status": str(exc), "execution_ready": False}))
        return 2
    except (OSError, ValueError, TypeError):
        print(json.dumps({"status": "LOCAL_IO_OR_FORMAT_REFUSED", "execution_ready": False}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
