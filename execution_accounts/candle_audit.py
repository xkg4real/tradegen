"""Offline lagging BR-8 audit. A0's repeated observations do not prove finality.

The caller provisions the independent finality verifier (as for continuous-path
coverage). It authenticates the venue/study evidence and binds a measured
finality boundary to this exact raw read and trade history. Without it every
observed minute remains pending. This module has no network or execution path.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from execution.upbit_inquiry import candle_params
from execution_accounts.collector import SourceReceipt, digest, identifier, instant, number, require
from execution_accounts.model import content_digest
from execution_accounts.path_checks import CheckFinding, receipt_fingerprint, replay_window
from execution_accounts.provider import EvidenceError

_CANDLE = "/v1/candles/minutes/1"
_MINUTE = timedelta(minutes=1)
_FINALITY_CONTRACT = "upbit-minute-finality-v1"
_EARLIER_CANDLE = object()


@dataclass(frozen=True, kw_only=True)
class MinuteFinalityRequest:
    contract: str
    account_scope: str
    market: str
    minute_start: datetime
    candle_receipt_sha256: str
    trade_history_sha256: str


@dataclass(frozen=True, kw_only=True)
class VerifiedMinuteFinality:
    request_sha256: str
    authority_sha256: str
    study_sha256: str
    final_after: datetime
    verified_at: datetime


@dataclass(frozen=True, kw_only=True)
class MinuteResult:
    start: datetime
    status: str
    findings: tuple[CheckFinding, ...]
    evidence_sha256: str


def _candle(r, market, start, scope, now):
    require(type(r) is SourceReceipt and r.account_scope == scope and r.path == _CANDLE,
            "CANDLE_AUDIT_RECEIPT_BINDING")
    expected = candle_params(market, start + _MINUTE, 1)
    require(type(r.params) is tuple and len(r.params) == len(expected) and all(type(p) is tuple and len(p) == 2
            and all(type(s) is str for s in p) for p in r.params) and dict(r.params) == dict(expected),
            "CANDLE_AUDIT_RECEIPT_BINDING")
    require(instant(r.received_at) <= now and instant(r.server_time) <= now + timedelta(seconds=1)
            and abs(r.server_time-r.received_at) <= timedelta(seconds=60), "CANDLE_AUDIT_RECEIPT_TIME")
    rows = r.decode()
    require(type(rows) is list and len(rows) <= 1, "CANDLE_AUDIT_RESPONSE_INVALID")
    if not rows:
        return None
    row = rows[0]
    require(type(row) is dict and row.get("market") == market and type(row.get("unit")) is int
            and row["unit"] == 1, "CANDLE_AUDIT_RESPONSE_INVALID")
    # The one-candle endpoint can send an older nonempty minute. It is not
    # evidence of this minute's OHLC, even when its extrema happen to match.
    stamp = row.get("candle_date_time_utc")
    require(type(stamp) is str and len(stamp) == 19, "CANDLE_AUDIT_WRONG_MINUTE")
    try:
        candle_at = datetime.strptime(stamp + "+0000", "%Y-%m-%dT%H:%M:%S%z")
    except ValueError:
        raise EvidenceError("CANDLE_AUDIT_WRONG_MINUTE") from None
    require(candle_at.strftime("%Y-%m-%dT%H:%M:%S") == stamp and candle_at.second == 0
            and candle_at <= start, "CANDLE_AUDIT_WRONG_MINUTE")
    low = number(row.get("low_price"), positive=True, json_number=True)
    high = number(row.get("high_price"), positive=True, json_number=True)
    require(low <= high, "CANDLE_AUDIT_RESPONSE_INVALID")
    return _EARLIER_CANDLE if candle_at < start else (low, high)


def _judgment(challenge, receipt, proof, prices, candle):
    minimum = maximum = None
    if prices:
        minimum, maximum = min(prices), max(prices)
    kinds = []
    low = None if candle is None else candle[0]
    if (candle is None) != (minimum is None):
        kinds.append("CANDLE_MINUTE")
    elif candle is not None:
        if low < minimum:
            kinds.append("CANDLE_LOW")
        if candle[1] > maximum:
            kinds.append("CANDLE_HIGH")
    evidence = content_digest((challenge, proof, receipt.sha256, minimum, maximum, len(prices)))
    findings = tuple(CheckFinding(kind=kind, symbol=challenge.market, at=challenge.minute_start, price=low,
                     evidence_sha256=content_digest((evidence, kind))) for kind in kinds)
    return MinuteResult(start=challenge.minute_start, status="CHECKED", findings=findings, evidence_sha256=evidence)


def audit_minutes(windows, receipts, *, market, account_scope, first_minute, now,
                  verify_finality=None, anchor_trade_ids=None):
    """Audit a contiguous batch of UTC minutes. Use None for an uncaptured candle.

    The receipts tuple starts at first_minute. One full minute may span several
    trade windows; gaps, overlap and contradictions refuse the batch. The
    callback returns VerifiedMinuteFinality or None when evidence is unavailable.
    Even after the deadline a candle captured too early requires a new read.
    """
    first, now, scope = instant(first_minute), instant(now), identifier(account_scope)
    require(first.second == first.microsecond == 0 and type(receipts) is tuple and 1 <= len(receipts) <= 10080
            and type(windows) is tuple and 1 <= len(windows) <= 2048, "CANDLE_AUDIT_RANGE_INVALID")
    through = first + len(receipts) * _MINUTE
    require(verify_finality is None or callable(verify_finality), "CANDLE_AUDIT_VERIFIER_REQUIRED")
    anchors = (None,) * len(windows) if anchor_trade_ids is None else anchor_trade_ids
    require(type(anchors) is tuple and len(anchors) == len(windows), "CANDLE_AUDIT_RANGE_INVALID")
    history = []
    seen, counted, minutes = {}, set(), [[] for _ in receipts]
    byte_count = 0
    prior_end = None
    for candidate, anchor in zip(windows, anchors):
        w = replay_window(candidate, account_scope=scope, anchor_trade_id=anchor)
        require(w.market == market and w.start < through and w.end > first and
                (w.start <= first if prior_end is None else w.start == prior_end),
                "CANDLE_AUDIT_PATH_GAP_OR_SCOPE")
        require(all(instant(r.received_at) <= now for r in w.receipts), "CANDLE_AUDIT_RECEIPT_TIME")
        byte_count += sum(len(r.raw_body) for r in w.receipts)
        require(byte_count <= 128 * 1024 * 1024, "CANDLE_AUDIT_BATCH_LIMIT")
        for p in w.all_prints:
            econ = (p.at, p.price, p.volume, p.ask_bid)
            require(p.sequential_id not in seen or seen[p.sequential_id] == econ, "CANDLE_AUDIT_PRINT_CONTRADICTION")
            seen[p.sequential_id] = econ
        for p in w.prints:
            if first <= p.at < through:
                counted.add(p.sequential_id)
                minutes[(p.at-first) // _MINUTE].append(p.price)
        prior_end = w.end
        history.append(w.proof_sha256)
    require(prior_end >= through, "CANDLE_AUDIT_PATH_GAP_OR_SCOPE")
    require(counted == {seq for seq, econ in seen.items() if first <= econ[0] < through},
            "CANDLE_AUDIT_PRINT_COVERAGE_CONTRADICTION")
    history_digest = content_digest(tuple(history))
    results = []
    for i, r in enumerate(receipts):
        start = first + i * _MINUTE
        if r is None:
            results.append(MinuteResult(start=start, status="MISSING_CANDLE_RECEIPT", findings=(),
                           evidence_sha256=content_digest((history_digest, market, start, "missing"))))
            continue
        candle = _candle(r, market, start, scope, now)
        challenge = MinuteFinalityRequest(contract=_FINALITY_CONTRACT, account_scope=scope, market=market,
            minute_start=start, candle_receipt_sha256=receipt_fingerprint(r), trade_history_sha256=history_digest)
        request_sha = content_digest(challenge)
        if candle is _EARLIER_CANDLE:
            results.append(MinuteResult(start=start, status="TARGET_MINUTE_NOT_RETURNED", findings=(),
                                        evidence_sha256=request_sha))
            continue
        try:
            proof = verify_finality(challenge, r) if verify_finality else None
        except Exception:
            raise EvidenceError("CANDLE_AUDIT_FINALITY_VERIFICATION_FAILED") from None
        if proof is None:
            results.append(MinuteResult(start=start, status="FINALITY_UNVERIFIED", findings=(), evidence_sha256=request_sha))
            continue
        require(type(proof) is VerifiedMinuteFinality and proof.request_sha256 == request_sha,
                "CANDLE_AUDIT_FINALITY_BINDING")
        digest(proof.authority_sha256)
        digest(proof.study_sha256)
        require(instant(proof.final_after) >= start + _MINUTE and r.received_at <= instant(proof.verified_at) <= now,
                "CANDLE_AUDIT_FINALITY_TIME")
        if min(r.server_time, r.received_at) < proof.final_after:
            results.append(MinuteResult(start=start, status="NEED_LATER_CAPTURE", findings=(),
                           evidence_sha256=content_digest((challenge, proof))))
            continue
        results.append(_judgment(challenge, r, proof, minutes[i], candle))
    return tuple(results)
