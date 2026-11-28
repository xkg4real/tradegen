"""Offline BR-6/BR-7 previews from private read archives. No default source.

Replaying bytes detects incorrect derived fields; source authentication and the
complete interval order roster must come from the independent capture/reviewer.
Findings carry no authority to commit risk, sign terms or send an order.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from execution.upbit_inquiry import ORDER_PATH
from execution_accounts.collector import SourceReceipt, TradeFeeEvidence, identifier, instant, require
from execution_accounts.model import content_digest
from execution_accounts.upbit_collector import (
    OrderFillsResult, TradeWindowResult, collect_order_fills, collect_trade_window,
)

_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)
_MAX_ARCHIVE_BYTES = 64 * 1024 * 1024


@dataclass(frozen=True, kw_only=True)
class CheckFinding:
    kind: str
    symbol: str
    at: datetime
    price: Decimal | None
    evidence_sha256: str
    occurrences: int = 1


def receipt_fingerprint(r):
    require(type(r) is SourceReceipt, "PATH_CHECK_RECEIPT_REQUIRED")
    return content_digest((r.account_scope, r.path, r.params, r.received_at, r.server_time, r.sha256))


class _Replay:
    """Sequential read-only replay. A missing, reordered or unused receipt is a failure."""
    def __init__(self, receipts, scope):
        self.receipts, self.account_scope, self.index = receipts, scope, 0

    def fetch(self, path, params):
        require(self.index < len(self.receipts), "PATH_CHECK_RECEIPT_MISSING")
        r = self.receipts[self.index]
        require(type(r) is SourceReceipt and (r.account_scope, r.path, r.params) == (self.account_scope, path, params),
                "PATH_CHECK_RECEIPT_BINDING")
        self.index += 1
        return r

    def finish(self):
        require(self.index == len(self.receipts), "PATH_CHECK_UNUSED_RECEIPTS")


def replay_window(walk, *, account_scope, anchor_trade_id=None):
    """Check the raw byte hashes, dated query, cursor chain, normalization and proof digest."""
    scope = identifier(account_scope)
    require(type(walk) is TradeWindowResult and type(walk.receipts) is tuple and 2 <= len(walk.receipts) <= 501,
            "PATH_CHECK_WINDOW_REQUIRED")
    require(all(type(r) is SourceReceipt and type(r.raw_body) is bytes for r in walk.receipts)
            and sum(len(r.raw_body) for r in walk.receipts) <= _MAX_ARCHIVE_BYTES, "PATH_CHECK_ARCHIVE_BOUND")
    params = walk.receipts[1].params
    require(type(params) is tuple and all(type(p) is tuple and len(p) == 2 and all(type(v) is str for v in p) for p in params),
            "PATH_CHECK_RECEIPT_BINDING")
    count = dict(params).get("count")
    require(type(count) is str and count.isascii() and count.isdecimal() and len(count) <= 3,
            "PATH_CHECK_RECEIPT_BINDING")
    source = _Replay(walk.receipts, scope)
    rebuilt = collect_trade_window(source, walk.market, start=walk.start, end=walk.end, account_scope=scope,
        count=int(count), max_pages=500, max_prints=50000, anchor_trade_id=anchor_trade_id)
    source.finish()
    require(walk == rebuilt, "PATH_CHECK_WINDOW_REPLAY_MISMATCH")
    return rebuilt


def ticker_findings(walk, *, account_scope, anchor_trade_id=None):
    verified = replay_window(walk, account_scope=account_scope, anchor_trade_id=anchor_trade_id)
    if verified.ticker_discrepancy is None:
        return ()
    at, price = verified.ticker_discrepancy
    proof = content_digest(("upbit-ticker-check-v1", verified.proof_sha256, at, price))
    return (CheckFinding(kind="TICKER_MISMATCH", symbol=verified.market, at=at, price=price, evidence_sha256=proof),)


def own_fill_findings(walk, orders, *, account_scope, expected_order_ids, anchor_trade_id=None, trade_fees=()):
    """Consume one public print per distinct own fill in the half-open interval.

    The caller supplies the account capture's reviewed order IDs for this market.
    Both boundaries must be aligned to the public feed's milliseconds so that
    truncating an execution time cannot move it across a boundary. Matching
    uses milliseconds, exact price and quantity. Public maker/taker side is not attested. A prevented quantity has no execution to match.
    """
    verified = replay_window(walk, account_scope=account_scope, anchor_trade_id=anchor_trade_id)
    require(verified.start.microsecond % 1000 == verified.end.microsecond % 1000 == 0,
            "PATH_CHECK_MILLISECOND_BOUNDARIES_REQUIRED")
    require(type(orders) is tuple and len(orders) <= 2000 and all(type(r) is OrderFillsResult for r in orders)
            and all(identifier(r.order_id) for r in orders)
            and type(expected_order_ids) is frozenset and all(identifier(s) for s in expected_order_ids)
            and {r.order_id for r in orders} == expected_order_ids and len(orders) == len(expected_order_ids),
            "PATH_CHECK_ORDER_ROSTER_MISMATCH")
    require(type(trade_fees) is tuple and all(type(f) is TradeFeeEvidence and f.order_id in expected_order_ids
            for f in trade_fees), "PATH_CHECK_FEE_EVIDENCE_INVALID")
    counts = Counter((p.timestamp_ms, p.price, p.volume) for p in verified.prints)
    own, seen, fingerprints = {}, set(), []
    for order in sorted(orders, key=lambda r: r.order_id):
        r = order.receipt
        require(type(r) is SourceReceipt and r.path == ORDER_PATH and r.account_scope == account_scope
                and min(instant(r.server_time), instant(r.received_at)) >= verified.end
                and type(r.params) is tuple and len(r.params) == 1
                and type(r.params[0]) is tuple and len(r.params[0]) == 2, "PATH_CHECK_ORDER_RECEIPT_BINDING")
        key, value = r.params[0]
        require(key in ("identifier", "uuid"), "PATH_CHECK_ORDER_RECEIPT_BINDING")
        source = _Replay((r,), account_scope)
        rebuilt = collect_order_fills(source, value if key == "uuid" else None,
            identifier_id=value if key == "identifier" else None, account_scope=account_scope,
            fee_evidence=tuple(f for f in trade_fees if f.order_id == order.order_id))
        source.finish()
        require(rebuilt == order and r.decode().get("market") == verified.market, "PATH_CHECK_ORDER_REPLAY_MISMATCH")
        fingerprints.append(receipt_fingerprint(r))
        for fill in rebuilt.fills:
            require(fill.fill_id not in seen, "PATH_CHECK_DUPLICATE_OWN_FILL")
            seen.add(fill.fill_id)
            if verified.start <= fill.executed_at < verified.end:
                ms = (instant(fill.executed_at) - _EPOCH) // timedelta(milliseconds=1)
                fingerprint = (ms, fill.price, fill.quantity)
                own.setdefault(fingerprint, []).append((fill.order_id, fill.fill_id, fill.executed_at))
    capture = content_digest(("upbit-own-fill-canary-v1", verified.proof_sha256, tuple(fingerprints)))
    findings = []
    # Multiple orders can be indistinguishable on the public wire. Report the
    # missing multiplicity, without attributing a public print to a guessed fill.
    for fingerprint, candidates in sorted(own.items()):
        missing = len(candidates) - counts[fingerprint]
        if missing > 0:
            ms, price, _ = fingerprint
            proof = content_digest((capture, fingerprint, tuple(sorted(candidates)), counts[fingerprint], missing))
            findings.append(CheckFinding(kind="OWN_FILL_MISS", symbol=verified.market, price=price, occurrences=missing,
                at=_EPOCH + timedelta(milliseconds=ms), evidence_sha256=proof))
    return tuple(findings)
