"""Record confirmed Upbit evidence discrepancies in the existing control journal.

The caller binds the provisioned account, deployment and policy, owns the raw
capture and authenticates its private order roster/finality verifier. This
protective port has no approval, release, order or halt capability. An absent
price or unknown historical portfolio is not a realized loss or sale signal.
"""
from __future__ import annotations

from dataclasses import dataclass

from execution_accounts.candle_audit import audit_minutes
from execution_accounts.collector import digest, identifier, instant, require
from execution_accounts.path_checks import own_fill_findings, ticker_findings
from execution_control.model import decimal_text
from execution_control.store import Journal, _utc, guard_pending


@dataclass(frozen=True, kw_only=True)
class PathCheckRecorder:
    journal: Journal
    account_scope: str
    deployment_sha256: str
    policy_sha256: str

    def __post_init__(self):
        require(type(self.journal) is Journal and self.journal.requires_existing,
                "PATH_CHECK_EXISTING_JOURNAL_REQUIRED")
        identifier(self.account_scope)
        digest(self.deployment_sha256)
        digest(self.policy_sha256)

    def _record(self, findings, now):
        if not findings:
            return
        # A replayed or concurrent identical receipt must never create a second
        # latch. Distinct corroborating evidence remains independently traceable.
        with self.journal.transaction() as tx:
            events = tx.events
            require(not guard_pending(events), "PATH_CHECK_GUARD_COMMIT_PENDING")
            existing = {(row["data"]["deployment_sha256"], row["data"]["policy_sha256"],
                         row["data"]["account_scope"], row["data"]["evidence_sha256"]): row["data"]
                        for row in events if row["kind"] == "entry_block"}
            for finding in findings:
                key = (self.deployment_sha256, self.policy_sha256, self.account_scope, finding.evidence_sha256)
                body = dict(account_scope=self.account_scope, deployment_sha256=self.deployment_sha256,
                            policy_sha256=self.policy_sha256, symbol=finding.symbol, cause=finding.kind,
                            observed_at=_utc(finding.at), price=None if finding.price is None else decimal_text(finding.price),
                            occurrences=finding.occurrences, evidence_sha256=finding.evidence_sha256)
                if key in existing:
                    require(existing[key] == body, "PATH_CHECK_JOURNAL_CONTRADICTION")
                else:
                    tx.append("entry_block", body, now=now)
                    existing[key] = body

    def check_window(self, walk, orders, *, expected_order_ids, now, anchor_trade_id=None, trade_fees=()):
        """Run authenticated-capture BR-6/7 replays. A failed later check cannot erase an earlier finding."""
        now = instant(now)
        ticker = ticker_findings(walk, account_scope=self.account_scope, anchor_trade_id=anchor_trade_id)
        require(all(instant(r.received_at) <= now for r in walk.receipts), "PATH_CHECK_RECEIPT_TIME")
        self._record(ticker, now)
        own = own_fill_findings(walk, orders, account_scope=self.account_scope, expected_order_ids=expected_order_ids,
                                anchor_trade_id=anchor_trade_id, trade_fees=trade_fees)
        require(all(instant(o.receipt.received_at) <= now for o in orders), "PATH_CHECK_RECEIPT_TIME")
        self._record(own, now)
        return ticker + own

    def check_minutes(self, windows, receipts, *, market, first_minute, now, verify_finality=None, anchor_trade_ids=None):
        """Lagging BR-8 replay. Return pending minute states without inventing a final price or an all-clear."""
        result = audit_minutes(windows, receipts, market=market, account_scope=self.account_scope,
                               first_minute=first_minute, now=now, verify_finality=verify_finality,
                               anchor_trade_ids=anchor_trade_ids)
        self._record(tuple(f for minute in result for f in minute.findings), instant(now))
        return result
