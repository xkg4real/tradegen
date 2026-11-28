"""Continuous public Upbit price-bar & spread recorder for Section-12 direction study.

Research only. Public GET only when --allow-public-network is passed on CLI.
Zero imports from core.compliance, core.odds, execution*, tools.owner, config, or main.
"""
from __future__ import annotations

import argparse
from contextlib import nullcontext
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_CEILING, ROUND_HALF_EVEN
from email.utils import parsedate_to_datetime
from http import client as http_client
import math
import os
from pathlib import Path
import re
import statistics
import time
from typing import Any, Callable, Sequence
from urllib import error, parse, request

from tools.research._study_common import (
    HashChainedLog,
    MARKET_RE,
    RESEARCH_FLAGS,
    StudyError,
    UTC,
    atomic_publish_bytes,
    atomic_publish_json_ascii,
    canonical_ascii_bytes,
    canonical_ascii_str,
    check_safe_path,
    ensure_safe_directory,
    loads_strict_json,
    read_safe_bytes,
    read_verified_chained_log,
    require,
    sha256_ascii,
)


ORIGIN = "https://api.upbit.com"
RECORDER_SCHEMA = "tradegen-upbit-price-recorder-v1"
MAX_HTTP_BODY = 2 * 1024 * 1024
ALLOWED_STEPS = {900: "/v1/candles/minutes/15", 3600: "/v1/candles/minutes/60"}
ALLOWED_PATHS: dict[str, set[str]] = {
    "/v1/candles/minutes/15": {"market", "count", "to"},
    "/v1/candles/minutes/60": {"market", "count", "to"},
    "/v1/orderbook": {"markets"},
    "/v1/ticker": {"markets"},
}
RESPONSE_HEADERS = frozenset({
    "date",
    "remaining-req",
    "retry-after",
    "content-type",
    "content-length",
    "transfer-encoding",
})


@dataclass(frozen=True)
class HttpReply:
    status: int
    headers: dict[str, str]
    body: bytes
    truncated: bool = False
    error: str | None = None


class Clock:
    wall: Callable[[], float] = staticmethod(time.time)
    monotonic: Callable[[], float] = staticmethod(time.monotonic)
    sleep: Callable[[float], None] = staticmethod(time.sleep)


class _NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, req: Any, fp: Any, code: int, msg: str, headers: Any, newurl: str) -> None:
        return None


def public_get(path: str, params: Mapping[str, str | int]) -> HttpReply:
    """Bounded public GET to api.upbit.com; no proxy, no redirect, no credentials."""
    require(path in ALLOWED_PATHS and isinstance(params, dict), "REQUEST_NOT_ALLOWED")
    require(set(params) <= ALLOWED_PATHS[path], "REQUEST_NOT_ALLOWED")
    require(all(type(k) is str and type(v) in (str, int) for k, v in params.items()), "REQUEST_NOT_ALLOWED")

    opener = request.build_opener(request.ProxyHandler({}), _NoRedirect())
    url = ORIGIN + path + "?" + parse.urlencode(params)
    req = request.Request(
        url,
        method="GET",
        headers={"Accept": "application/json", "User-Agent": "TRADEGEN-RESEARCH-RECORDER/1"},
    )
    try:
        resp = opener.open(req, timeout=10)
    except error.HTTPError as exc:
        resp = exc
    except (error.URLError, TimeoutError, http_client.HTTPException, OSError):
        raise StudyError("TRANSPORT_FAILED") from None

    with resp:
        headers = {k.lower(): v for k, v in resp.headers.items() if k.lower() in RESPONSE_HEADERS}
        failure: str | None = None
        try:
            raw = resp.read(MAX_HTTP_BODY + 1)
        except http_client.IncompleteRead as exc:
            raw = exc.partial
            failure = "HTTP_BODY_INCOMPLETE"
        except (http_client.HTTPException, OSError):
            raw = b""
            failure = "HTTP_RESPONSE_FAILED"

        truncated = len(raw) > MAX_HTTP_BODY
        if (
            failure is None
            and not truncated
            and "content-length" in headers
            and headers.get("transfer-encoding", "").strip().lower() != "chunked"
        ):
            length_str = headers["content-length"]
            if not re.fullmatch(r"[0-9]{1,20}", length_str):
                failure = "HTTP_LENGTH_INVALID"
            elif len(raw) != int(length_str):
                failure = "HTTP_BODY_INCOMPLETE"
        return HttpReply(resp.status, headers, raw[:MAX_HTTP_BODY], truncated, failure)


from typing import Mapping  # noqa: E402


def _retry_deadline(headers: Mapping[str, str], received_wall: float) -> int | None:
    val = headers.get("retry-after", "").strip()
    if re.fullmatch(r"[0-9]{1,12}", val):
        return math.ceil(received_wall + int(val))
    try:
        retry_dt = parsedate_to_datetime(val)
        date_dt = parsedate_to_datetime(headers["date"])
        if retry_dt.tzinfo is None or date_dt.tzinfo is None:
            return None
        return math.ceil(max(retry_dt.timestamp(), received_wall + max(0.0, (retry_dt - date_dt).total_seconds())))
    except (KeyError, ValueError, TypeError, OverflowError, OSError):
        return None


class TransientPublicBudget:
    """Per-poll shared Upbit public-IP coordination.

    Reads upbit-public-cooldown.json before every poll, records a hold on 429/418,
    never clears/deletes an existing hold file, and releases upbit-public-session.lock
    immediately after each poll so A0 and M9-T4 probes are not blocked between polls.
    """

    def __init__(self, directory: Path | str, *, clock: Clock | None = None) -> None:
        self.root = ensure_safe_directory(directory, error_code="PUBLIC_BUDGET_PATH_REFUSED")
        self.lock_path = check_safe_path(self.root / "upbit-public-session.lock", error_code="PUBLIC_BUDGET_PATH_REFUSED")
        self.hold_path = check_safe_path(self.root / "upbit-public-cooldown.json", error_code="PUBLIC_BUDGET_PATH_REFUSED")
        self.clock = clock or Clock()
        self.keep_lock = False
        self._locked = False

    def __enter__(self) -> TransientPublicBudget:
        try:
            fd = os.open(self.lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            raise StudyError("PUBLIC_BUDGET_BUSY_OR_UNREVIEWED") from None
        os.close(fd)
        self._locked = True
        try:
            self.check_cooldown()
        except BaseException:
            self._release_lock()
            raise
        return self

    def check_cooldown(self) -> None:
        if os.path.lexists(self.hold_path):
            raw = read_safe_bytes(
                self.hold_path,
                max_bytes=128,
                path_error="PUBLIC_BUDGET_REVIEW_REQUIRED",
                size_error="PUBLIC_BUDGET_REVIEW_REQUIRED",
            )
            try:
                state = loads_strict_json(raw, max_bytes=128, size_error="PUBLIC_BUDGET_REVIEW_REQUIRED")
            except StudyError:
                raise StudyError("PUBLIC_BUDGET_REVIEW_REQUIRED") from None
            if (
                type(state) is not dict
                or set(state) != {"retry_at_unix", "status"}
                or type(state["status"]) is not int
                or state["status"] not in (418, 429)
            ):
                raise StudyError("PUBLIC_BUDGET_REVIEW_REQUIRED")
            deadline = state["retry_at_unix"]
            if deadline is None:
                raise StudyError("PUBLIC_BUDGET_REVIEW_REQUIRED")
            if type(deadline) is not int or deadline < 0:
                raise StudyError("PUBLIC_BUDGET_REVIEW_REQUIRED")
            if self.clock.wall() < deadline:
                raise StudyError("PUBLIC_BUDGET_COOLDOWN")
            # Intentionally never unlink upbit-public-cooldown.json (Section 9.2 invariant).

    def record_rate_limit(self, status: int, headers: Mapping[str, str], received_wall: float) -> str:
        self.keep_lock = True
        state = {"status": status, "retry_at_unix": _retry_deadline(headers, received_wall)}
        payload = canonical_ascii_bytes(state)
        try:
            if not os.path.lexists(self.hold_path):
                atomic_publish_bytes(
                    self.hold_path,
                    payload,
                    max_bytes=128,
                    exists_error="PUBLIC_BUDGET_HOLD_EXISTS",
                    path_error="PUBLIC_BUDGET_PATH_REFUSED",
                )
            else:
                # Update expired cooldown marker atomically without leaving a window without a hold file
                tmp = self.root / f".hold-update-{os.getpid()}.tmp"
                fd = os.open(tmp, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
                try:
                    with os.fdopen(fd, "wb") as stream:
                        stream.write(payload)
                        stream.flush()
                        os.fsync(stream.fileno())
                    os.replace(tmp, self.hold_path)
                finally:
                    if os.path.lexists(tmp):
                        tmp.unlink()
        except (OSError, StudyError):
            return "REVIEW_LOCK_RETAINED"
        self.keep_lock = False
        return "REVIEW_REQUIRED" if state["retry_at_unix"] is None else "COOLDOWN_RECORDED"

    def _release_lock(self) -> None:
        if self._locked and not self.keep_lock:
            try:
                self.lock_path.unlink()
            except FileNotFoundError:
                pass
            self._locked = False

    def __exit__(self, *_exc: Any) -> None:
        self._release_lock()


# --------------------------------------------------------------------------- #
# Positive Decimal price parsing & return/spread arithmetic
# --------------------------------------------------------------------------- #
def parse_positive_price(value: Any, code: str = "MALFORMED_UPBIT_PRICE") -> tuple[Decimal, str]:
    if type(value) is bool or not isinstance(value, (str, int, float, Decimal)):
        raise StudyError(code)
    text = str(value)
    require(0 < len(text) <= 128, code)
    try:
        dec = Decimal(text)
    except InvalidOperation:
        raise StudyError(code) from None
    require(
        dec.is_finite()
        and dec > 0
        and len(dec.as_tuple().digits) <= 64
        and -64 <= dec.as_tuple().exponent <= 64
        and -64 <= dec.adjusted() <= 64,
        code,
    )
    fixed = format(dec, "f")
    norm_str = fixed.rstrip("0").rstrip(".") if "." in fixed else fixed
    return Decimal(norm_str), norm_str


def compute_return_bps(prev_price: Decimal, close_price: Decimal) -> int:
    require(prev_price > 0 and close_price > 0, "MALFORMED_UPBIT_PRICE")
    raw_bps = ((close_price - prev_price) / prev_price) * Decimal("10000")
    rounded = int(raw_bps.quantize(Decimal("1"), rounding=ROUND_HALF_EVEN))
    require(-9999 <= rounded <= 100_000, "RETURN_BPS_OUT_OF_RANGE")
    return rounded


def compute_spread_bps(bid: Decimal, ask: Decimal) -> str:
    require(Decimal("0") < bid <= ask, "MALFORMED_ORDERBOOK")
    mid = (ask + bid) / Decimal("2")
    bps = ((ask - bid) / mid) * Decimal("10000")
    q = bps.quantize(Decimal("0.000001"), rounding=ROUND_HALF_EVEN)
    return format(q, "f")


def compute_warmup_hurdle_bps(
    bars: Sequence[Mapping[str, Any]],
    *,
    round_trip_fee_bps: Decimal = Decimal("10"),
    slippage_bps: Decimal = Decimal("5"),
) -> int:
    """Section 10 Row 6(a): integer rounded up from round-trip fee + median live warmup spread + 5 bps slippage."""
    spreads: list[Decimal] = []
    for bar in bars:
        sp = bar.get("spread_bps")
        if sp is not None and not bar.get("backfilled", False):
            dec = Decimal(str(sp))
            require(dec >= 0, "INVALID_SPREAD_BPS")
            spreads.append(dec)
    require(len(spreads) > 0, "NO_WARMUP_SPREADS_RECORDED")
    ordered = sorted(spreads)
    mid_idx = len(ordered) // 2
    if len(ordered) % 2 == 1:
        median_spread = ordered[mid_idx]
    else:
        median_spread = (ordered[mid_idx - 1] + ordered[mid_idx]) / Decimal("2")
    total = round_trip_fee_bps + median_spread + slippage_bps
    hurdle = int(total.to_integral_value(rounding=ROUND_CEILING))
    require(0 <= hurdle <= 9999, "HURDLE_BPS_OUT_OF_RANGE")
    return hurdle


# --------------------------------------------------------------------------- #
# Recorder Config & State
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class PriceRecorderConfig:
    market: str
    step_seconds: int = 3600
    requests_per_second: float = 2.0

    def validate(self) -> PriceRecorderConfig:
        require(type(self.market) is str and MARKET_RE.fullmatch(self.market) is not None, "INVALID_MARKET")
        require(type(self.step_seconds) is int and self.step_seconds in ALLOWED_STEPS, "INVALID_STEP_SECONDS")
        require(
            type(self.requests_per_second) in (int, float)
            and math.isfinite(self.requests_per_second)
            and 0.0 < self.requests_per_second <= 5.0,
            "INVALID_RATE",
        )
        return self

    def document(self) -> dict[str, Any]:
        self.validate()
        return {
            "market": self.market,
            "step_seconds": int(self.step_seconds),
            "requests_per_second": float(self.requests_per_second),
        }


def _parse_candle_row(item: Any, market: str, step_seconds: int) -> dict[str, Any]:
    require(type(item) is dict and item.get("market") == market, "MALFORMED_CANDLE")
    utc_str = item.get("candle_date_time_utc")
    require(type(utc_str) is str and 0 < len(utc_str) <= 40, "MALFORMED_CANDLE")
    try:
        dt = datetime.fromisoformat(utc_str.replace("Z", "+00:00"))
    except ValueError:
        raise StudyError("MALFORMED_CANDLE") from None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    open_ts = int(dt.timestamp())
    end_ts = open_ts + step_seconds
    require(end_ts % step_seconds == 0, "CANDLE_OFF_GRID")

    open_dec, open_str = parse_positive_price(item.get("opening_price"), "MALFORMED_CANDLE")
    high_dec, high_str = parse_positive_price(item.get("high_price", item.get("trade_price")), "MALFORMED_CANDLE")
    low_dec, low_str = parse_positive_price(item.get("low_price", item.get("trade_price")), "MALFORMED_CANDLE")
    close_dec, close_str = parse_positive_price(item.get("trade_price"), "MALFORMED_CANDLE")
    require(low_dec <= open_dec <= high_dec and low_dec <= close_dec <= high_dec, "MALFORMED_CANDLE")

    return {
        "end": end_ts,
        "open_dec": open_dec,
        "close_dec": close_dec,
        "open": open_str,
        "high": high_str,
        "low": low_str,
        "close": close_str,
    }


def _parse_orderbook_top(body: Any, market: str) -> tuple[Decimal, str, Decimal, str]:
    require(type(body) is list and len(body) == 1 and type(body[0]) is dict, "MALFORMED_ORDERBOOK")
    entry = body[0]
    require(entry.get("market") == market, "MALFORMED_ORDERBOOK")
    units = entry.get("orderbook_units")
    require(type(units) is list and len(units) >= 1 and type(units[0]) is dict, "MALFORMED_ORDERBOOK")
    bid_dec, bid_str = parse_positive_price(units[0].get("bid_price"), "MALFORMED_ORDERBOOK")
    ask_dec, ask_str = parse_positive_price(units[0].get("ask_price"), "MALFORMED_ORDERBOOK")
    require(bid_dec <= ask_dec, "MALFORMED_ORDERBOOK")
    return bid_dec, bid_str, ask_dec, ask_str


class UpbitPriceRecorder:
    """Captures hourly / 15-minute bars with honest known_at, close bid/ask spread, and missed-bar backfill."""

    def __init__(
        self,
        archive_dir: Path | str,
        config: PriceRecorderConfig,
        *,
        transport: Callable[[str, Mapping[str, str | int]], HttpReply] = public_get,
        coordination_dir: Path | str | None = None,
        clock: Clock | None = None,
    ) -> None:
        self.archive_dir = Path(archive_dir)
        self.config = config.validate()
        self.transport = transport
        self.coordination_dir = Path(coordination_dir) if coordination_dir is not None else None
        self.clock = clock or Clock()
        self._next_mono = 0.0

    def _call_api(
        self,
        path: str,
        params: Mapping[str, str | int],
        budget: TransientPublicBudget | None,
        log: HashChainedLog,
    ) -> tuple[Any, float]:
        if budget is not None:
            budget.check_cooldown()
        wait = self._next_mono - self.clock.monotonic()
        if wait > 0:
            self.clock.sleep(wait)
        sent_wall = self.clock.wall()
        self._next_mono = self.clock.monotonic() + (1.0 / self.config.requests_per_second)
        reply = self.transport(path, dict(params))
        recv_wall = self.clock.wall()
        require(recv_wall >= sent_wall, "CLOCK_ROLLBACK")

        if reply.status in (418, 429):
            hold_status = (
                budget.record_rate_limit(reply.status, reply.headers, recv_wall)
                if budget is not None
                else "UNCOORDINATED_RATE_LIMIT"
            )
            log.append({
                "kind": "rate_limit_stop",
                "status": reply.status,
                "path": path,
                "received_at": math.ceil(recv_wall),
                "hold": hold_status,
            })
            raise StudyError(f"RATE_LIMIT_STOP_{reply.status}")
        if reply.error is not None:
            raise StudyError(reply.error)
        require(not reply.truncated, "RESPONSE_TOO_LARGE")
        require(200 <= reply.status < 300, "HTTP_REFUSED")
        parsed = loads_strict_json(reply.body, max_bytes=MAX_HTTP_BODY, size_error="RESPONSE_TOO_LARGE")
        return parsed, recv_wall

    def poll_once(self) -> dict[str, Any]:
        """Poll the latest closed bar(s), backfilling any missed bars with honest late known_at."""
        step = self.config.step_seconds
        candle_path = ALLOWED_STEPS[step]
        budget_ctx = (
            TransientPublicBudget(self.coordination_dir, clock=self.clock)
            if self.coordination_dir is not None
            else nullcontext(None)
        )

        with HashChainedLog(self.archive_dir, "bars.jsonl", lock_name=".bars.lock") as log:
            if not log.entries:
                log.append({
                    "kind": "config",
                    "schema": RECORDER_SCHEMA,
                    "config": self.config.document(),
                })
            else:
                first_data = log.entries[0]["data"]
                require(
                    first_data == {"kind": "config", "schema": RECORDER_SCHEMA, "config": self.config.document()},
                    "ARCHIVE_CONFIG_MISMATCH",
                )

            recorded_bars = [e["data"] for e in log.entries if e["data"].get("kind") == "bar"]
            last_end = recorded_bars[-1]["end"] if recorded_bars else None
            last_close = Decimal(recorded_bars[-1]["close"]) if recorded_bars else None

            now_wall = self.clock.wall()
            target_end = (int(now_wall) // step) * step
            require(target_end > 0, "INVALID_CLOCK_TIME")

            if last_end is not None and target_end <= last_end:
                return {
                    **RESEARCH_FLAGS,
                    "status": "UP_TO_DATE",
                    "market": self.config.market,
                    "appended_bars": 0,
                    "last_end": last_end,
                    "archive_head_sha256": log.head_sha256,
                }

            needed_ends = (
                [target_end]
                if last_end is None
                else list(range(last_end + step, target_end + step, step))
            )

            with budget_ctx as active_budget:
                fetched_by_end: dict[int, tuple[dict[str, Any], float]] = {}
                cursor_end = target_end
                # Fetch an extra anchor candle on first poll so bar 0 can use prev_close if available
                remaining_count = len(needed_ends) + (1 if last_end is None else 0)
                while remaining_count > 0:
                    batch_count = min(200, remaining_count)
                    to_iso = datetime.fromtimestamp(cursor_end, UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
                    raw_candles, candle_recv = self._call_api(
                        candle_path,
                        {"market": self.config.market, "count": batch_count, "to": to_iso},
                        active_budget,
                        log,
                    )
                    require(type(raw_candles) is list and len(raw_candles) <= batch_count, "MALFORMED_CANDLE")
                    if not raw_candles:
                        break
                    parsed_batch = [_parse_candle_row(c, self.config.market, step) for c in raw_candles]
                    for c_row in parsed_batch:
                        fetched_by_end[c_row["end"]] = (c_row, candle_recv)
                    earliest_in_batch = min(c["end"] for c in parsed_batch)
                    if earliest_in_batch >= cursor_end:
                        break
                    cursor_end = earliest_in_batch - step
                    remaining_count -= len(parsed_batch)

                missing_ends = [e for e in needed_ends if e not in fetched_by_end]
                if missing_ends:
                    log.append({
                        "kind": "s1_unbackfillable_gap",
                        "missing_ends": missing_ends,
                        "detected_at": math.ceil(self.clock.wall()),
                    })
                    raise StudyError("S1_UNBACKFILLABLE_BAR")

                # Capture live close orderbook iff the latest bar was polled within one bar interval of its close
                live_ob: tuple[str, str, str] | None = None
                if self.clock.wall() < target_end + step:
                    ob_body, _ob_recv = self._call_api(
                        "/v1/orderbook",
                        {"markets": self.config.market},
                        active_budget,
                        log,
                    )
                    bid_dec, bid_str, ask_dec, ask_str = _parse_orderbook_top(ob_body, self.config.market)
                    live_ob = (bid_str, ask_str, compute_spread_bps(bid_dec, ask_dec))

            appended = 0
            for bar_end in needed_ends:
                c_row, recv_wall = fetched_by_end[bar_end]
                if last_close is not None:
                    base_price = last_close
                elif (bar_end - step) in fetched_by_end:
                    base_price = fetched_by_end[bar_end - step][0]["close_dec"]
                else:
                    base_price = c_row["open_dec"]

                ret_bps = compute_return_bps(base_price, c_row["close_dec"])
                # Invariant: known_at = max(end + 1, math.ceil(received_wall)) -> strictly > end
                known_at = max(bar_end + 1, math.ceil(recv_wall))
                is_backfilled = bar_end < target_end or live_ob is None

                bar_entry = {
                    "kind": "bar",
                    "end": bar_end,
                    "known_at": known_at,
                    "return_bps": ret_bps,
                    "open": c_row["open"],
                    "high": c_row["high"],
                    "low": c_row["low"],
                    "close": c_row["close"],
                    "bid": None if is_backfilled else live_ob[0],
                    "ask": None if is_backfilled else live_ob[1],
                    "spread_bps": None if is_backfilled else live_ob[2],
                    "backfilled": bool(is_backfilled),
                }
                log.append(bar_entry)
                last_close = c_row["close_dec"]
                appended += 1

            return {
                **RESEARCH_FLAGS,
                "status": "RECORDED",
                "market": self.config.market,
                "step_seconds": step,
                "appended_bars": appended,
                "backfilled_bars": sum(1 for e in needed_ends if e < target_end or live_ob is None),
                "last_end": needed_ends[-1],
                "archive_head_sha256": log.head_sha256,
            }


def read_recorded_bars(
    archive_dir: Path | str,
    *,
    pinned_head: str | None = None,
) -> tuple[PriceRecorderConfig, list[dict[str, Any]], str]:
    entries, head = read_verified_chained_log(archive_dir, "bars.jsonl", pinned_head=pinned_head)
    require(len(entries) > 0, "EMPTY_BAR_ARCHIVE")
    first = entries[0]["data"]
    require(type(first) is dict and first.get("kind") == "config" and first.get("schema") == RECORDER_SCHEMA, "ARCHIVE_CONFIG_MISMATCH")
    cfg_doc = first["config"]
    cfg = PriceRecorderConfig(
        market=cfg_doc["market"],
        step_seconds=cfg_doc["step_seconds"],
        requests_per_second=cfg_doc["requests_per_second"],
    ).validate()

    for entry in entries[1:]:
        if entry["data"].get("kind") == "s1_unbackfillable_gap":
            raise StudyError("S1_UNBACKFILLABLE_BAR")

    bars = [e["data"] for e in entries[1:] if e["data"].get("kind") == "bar"]
    for idx, bar in enumerate(bars):
        require(bar["known_at"] > bar["end"], "BAR_KNOWN_AT_NOT_AFTER_END")
        if idx > 0:
            require(bar["end"] - bars[idx - 1]["end"] == cfg.step_seconds, "MISSING_OR_DUPLICATE_BAR")
    return cfg, bars, head


def export_history(
    archive_dir: Path | str,
    output_path: Path | str,
    *,
    scope: str,
    source_id: str,
    max_bars: int = 1024,
    start_end: int | None = None,
    stop_end: int | None = None,
    exported_at: int | None = None,
) -> dict[str, Any]:
    """Export validated contiguous bars to atomic history.json + sidecar .manifest.json."""
    require(type(scope) is str and 0 < len(scope) <= 140, "INVALID_SCOPE")
    require(type(source_id) is str and 0 < len(source_id) <= 140, "INVALID_SOURCE_ID")
    require(type(max_bars) is int and 1 <= max_bars <= 1024, "HISTORY_SIZE")

    cfg, all_bars, archive_head = read_recorded_bars(archive_dir)
    selected = [
        b for b in all_bars
        if (start_end is None or b["end"] >= start_end)
        and (stop_end is None or b["end"] <= stop_end)
    ]
    if len(selected) > max_bars:
        selected = selected[-max_bars:]
    require(1 <= len(selected) <= max_bars, "HISTORY_SIZE")
    for idx in range(1, len(selected)):
        require(selected[idx]["end"] - selected[idx - 1]["end"] == cfg.step_seconds, "MISSING_OR_DUPLICATE_BAR")

    history_doc = {
        "scope": scope,
        "source_id": source_id,
        "bars": [
            {
                "end": int(b["end"]),
                "known_at": int(b["known_at"]),
                "return_bps": int(b["return_bps"]),
            }
            for b in selected
        ],
    }
    out_file = Path(output_path)
    manifest_file = out_file.with_suffix(".manifest.json") if out_file.suffix.lower() == ".json" else Path(f"{out_file}.manifest.json")

    _, history_sha = atomic_publish_json_ascii(out_file, history_doc)
    live_spreads = [float(b["spread_bps"]) for b in selected if b.get("spread_bps") is not None and not b.get("backfilled")]
    manifest_body = {
        "format": "tradegen-price-history-manifest-v1",
        **RESEARCH_FLAGS,
        "market": cfg.market,
        "step_seconds": cfg.step_seconds,
        "scope": scope,
        "source_id": source_id,
        "history_file": out_file.name,
        "history_sha256": history_sha,
        "archive_head_sha256": archive_head,
        "bar_count": len(selected),
        "first_bar_end": selected[0]["end"],
        "last_bar_end": selected[-1]["end"],
        "backfilled_bar_count": sum(1 for b in selected if b.get("backfilled")),
        "live_spread_count": len(live_spreads),
        "median_live_spread_bps": None if not live_spreads else round(statistics.median(live_spreads), 6),
        "exported_at": int(time.time()) if exported_at is None else int(exported_at),
    }
    manifest_body["manifest_sha256"] = sha256_ascii(manifest_body)
    atomic_publish_json_ascii(manifest_file, manifest_body)
    return manifest_body


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_poll = sub.add_parser("poll", help="Capture closed Upbit candle(s) + orderbook spread")
    p_poll.add_argument("--market", required=True)
    p_poll.add_argument("--archive-dir", type=Path, required=True)
    p_poll.add_argument("--step-seconds", type=int, default=3600, choices=[900, 3600])
    p_poll.add_argument("--coordination-dir", type=Path)
    p_poll.add_argument("--cycles", type=int, default=1)
    p_poll.add_argument("--pause-seconds", type=float, default=60.0)
    p_poll.add_argument("--allow-public-network", action="store_true")

    p_exp = sub.add_parser("export", help="Export contiguous history.json + manifest from offline archive")
    p_exp.add_argument("--archive-dir", type=Path, required=True)
    p_exp.add_argument("--output", type=Path, required=True)
    p_exp.add_argument("--scope", required=True)
    p_exp.add_argument("--source-id", required=True)
    p_exp.add_argument("--max-bars", type=int, default=1024)

    args = parser.parse_args(argv)
    if args.cmd == "poll" and not args.allow_public_network:
        parser.error("public Upbit reads require --allow-public-network; no request was made")

    try:
        if args.cmd == "poll":
            require(1 <= args.cycles <= 100_000 and args.pause_seconds >= 0, "INVALID_RUN_BOUND")
            cfg = PriceRecorderConfig(market=args.market, step_seconds=args.step_seconds).validate()
            rec = UpbitPriceRecorder(args.archive_dir, cfg, coordination_dir=args.coordination_dir)
            last_res: dict[str, Any] = {}
            for i in range(args.cycles):
                last_res = rec.poll_once()
                if i + 1 < args.cycles:
                    time.sleep(args.pause_seconds)
            print(canonical_ascii_str(last_res))
            return 0
        manifest = export_history(
            args.archive_dir,
            args.output,
            scope=args.scope,
            source_id=args.source_id,
            max_bars=args.max_bars,
        )
        print(canonical_ascii_str(manifest))
        return 0
    except StudyError as exc:
        reason = str(exc)
    except (OSError, ValueError, TypeError):
        reason = "LOCAL_IO_OR_FORMAT_REFUSED"
    print(canonical_ascii_str({**RESEARCH_FLAGS, "reason": reason}))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
