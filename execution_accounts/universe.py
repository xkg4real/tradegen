"""Public Upbit universe reads (spec sections 5, 7 and 9): the daily snapshot builder, the odds candles and the
per-slot flag and ticker source. Every read is a fixed public GET of execution.upbit_inquiry under an explicit
inquiry_clock. Nothing here reads a key, writes a file or imports owner; only execution_launch/universe_store.py
writes the snapshot file."""
from __future__ import annotations

import base64
from datetime import date, datetime, timezone

from core.compliance import rules
from execution.transport import Answer, inquiry_clock
from execution.upbit_inquiry import CANDLES_DAYS_PATH, MARKET_ALL_PATH, candle_params, daily_candles, market_all
from execution_accounts.collector import SourceReceipt

PUBLIC_SCOPE = "public"                    # the plain receipt's account_scope (index contract, PR 1)
# ponytail: provisional body caps until the spec section 17 measurement sizes them from real answers
MAX_MARKET_ALL_BODY = 1024 * 1024
MAX_CANDLE_BODY = 256 * 1024
_MARKET_ALL_PARAMS = (("is_details", "true"),)


class UniverseReadError(ValueError):
    """A fixed refusal code; no body, market or provider text is quoted."""


def _require(condition, code):
    if not condition:
        raise UniverseReadError(code)


def _inquire(helper, *args):
    """One public helper call; any failure, after the transport's own single retry, is UNIVERSE_INQUIRY_FAILED."""
    try:
        return helper(*args)
    except Exception:
        raise UniverseReadError("UNIVERSE_INQUIRY_FAILED") from None


def _receipt(answer, path, params, cap):
    """(SourceReceipt, decoded body) of one public answer: the server time is required, the body is 1 to `cap` bytes
    and SourceReceipt.decode checks its sha256."""
    _require(type(answer) is Answer and answer.server_utc is not None, "UNIVERSE_SERVER_TIME_REQUIRED")
    _require(type(answer.raw_body) is bytes and 0 < len(answer.raw_body) <= cap, "UNIVERSE_BODY_EMPTY_OR_OVERSIZED")
    try:
        receipt = SourceReceipt(path=path, params=params, account_scope=PUBLIC_SCOPE,
                                received_at=answer.received_utc, server_time=answer.server_utc,
                                raw_body=answer.raw_body, sha256=answer.sha256)
        return receipt, receipt.decode()
    except (ValueError, TypeError, ArithmeticError, RecursionError):
        raise UniverseReadError("UNIVERSE_RECEIPT_INVALID") from None


def _stamp(moment):
    """ISO 8601 UTC with microseconds and Z, the text execution_control.store._utc writes."""
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _plain(receipt):
    """The 7-key plain receipt of core.compliance.rules (live_history's receipt shape)."""
    return {"path": receipt.path, "params": [[key, value] for key, value in receipt.params],
            "account_scope": receipt.account_scope, "received_at": _stamp(receipt.received_at),
            "server_time": _stamp(receipt.server_time),
            "raw_body_b64": base64.b64encode(receipt.raw_body).decode("ascii"), "sha256": receipt.sha256}


def _candle_request(path, params):
    """(market, to, count) of one candle request the rule implies, refused unless daily_candles sends exactly it."""
    try:
        market, to, count = params[0][1], datetime.fromisoformat(params[1][1]), int(params[2][1])
        exact = path == CANDLES_DAYS_PATH and candle_params(market, to, count) == params
    except Exception:
        exact = False
    _require(exact, "UNIVERSE_REQUEST_INVALID")
    return market, to, count


def build_universe_snapshot(rule: rules.UniverseRule, day: date, *, clock) -> tuple[bytes, str]:
    """The snapshot of candle day `day` (UTC) under `rule`: one market/all read, then exactly the candle reads that
    rules.universe_requests implies for that body, in its order, all under `clock`. The receipts go to
    rules.encode_universe_snapshot in that same order, market/all at its sorted place. Returns the canonical file
    bytes and the manifest sha256 once rules.verify_universe_snapshot accepts them. Any failed read raises and nothing
    is returned; nothing is written here."""
    _require(type(rule) is rules.UniverseRule and type(day) is date and callable(clock), "UNIVERSE_INPUT_INVALID")
    with inquiry_clock(clock):
        first = _inquire(market_all)
        listing = _receipt(first, MARKET_ALL_PATH, _MARKET_ALL_PARAMS, MAX_MARKET_ALL_BODY)[0]
        receipts = []
        for path, params in rules.universe_requests(rule, first.raw_body, day):
            if (path, params) == (MARKET_ALL_PATH, _MARKET_ALL_PARAMS):
                receipts.append(listing)
                continue
            market, to, count = _candle_request(path, params)
            receipts.append(_receipt(_inquire(daily_candles, market, to, count), path, params, MAX_CANDLE_BODY)[0])
    raw, sha256 = rules.encode_universe_snapshot(rule, day, [_plain(receipt) for receipt in receipts])
    universe = rules.verify_universe_snapshot(raw, rules.universe_rule_sha256(rule))
    _require(universe.snapshot_sha256 == sha256, "UNIVERSE_SNAPSHOT_MISMATCH")
    return raw, sha256
