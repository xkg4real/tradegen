"""Flat-only authentic Upbit KRW interval producer for ContinuousAccountProvider.

``UpbitIntervalSource.collect`` runs one complete, fenced ``collect_upbit`` capture before the tick time is
chosen and stages exactly one BaselineFrame; ``__call__`` hands that frame back without any I/O. The only
interval extrema the authenticated evidence proves today are a flat interval's: zero inventory at the endpoint
and no fill or external flow at or after the previous endpoint, so marked equity is the constant KRW cash and
``minimum == maximum == equity`` exactly. A held position, a fill inside the interval (a round trip that leaves
the endpoints equal included) or any flow refuses; a reviewed intra-interval price path would be needed to go
further, so after a first fill this producer stops the chain (owner open item).

Boundaries: a required 22:00 KST cutoff or the next Seoul midnight must end an interval exactly. A capture whose
first balance read is at or before the boundary and whose fenced observation is at or after it spans the
boundary; its evidence is stamped at the boundary instant (rows, server time and the manifest stay as captured;
each page's own digest is recomputed for the new end). A balance first read after the boundary is never
relabelled. For a capture spanning midnight the collector's structural self-check receives a module-private
opening baseline (the previous state's values at the midnight instant, which under the flat rule are the
reducer's real opening); it is never exported, never staged, and is discarded before the bridge runs the
reducer's own ``risk_baseline``. The capture's fenced observation must still lie within 30 s of
``previous.asof``, the freshness rule every capture meets (R17), so a boundary capture never heals a longer
gap; recovery stays the reviewed re-anchor.

Nothing here loads owner context, signs, arms, orders, reads credentials or touches a file.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, time, timedelta
from decimal import Decimal, DecimalException, Inexact, localcontext
from threading import Lock
from pathlib import Path

from core.compliance.model import KST
from execution_accounts.baseline import BaselineError, BaselineInterval, BaselineState, _required_cutoff, risk_baseline
from execution_accounts.baseline_bridge import BaselineFrame, advance_account_baseline
from execution_accounts.collector import CoverageEvidence, OpeningAnchor, SourceReceipt, TradeFeeEvidence, instant
from execution_accounts.model import AccountEvidence, RiskBaseline, content_digest
from execution_accounts.continuous import (ContinuousEvidenceError, ContinuousPath, PathValuation, VerifiedCoverage, value_path, verify_coverage)
from execution_launch.continuous_archive import archive_candidate
from execution_control.risk import account_fills
from execution_accounts.provider import EvidenceError, _fresh, build_observation
from execution_accounts.upbit_collector import CollectionResult, collect_upbit

BOUNDARY_LEAD_SECONDS = 10   # calibration knob: a boundary capture must start inside this window before the boundary
_ZERO = Decimal(0)


class AccountIntervalError(ValueError):
    """Fixed codes only; never account values, paths or source exception text."""


def _require(ok, code):
    if not ok:
        raise AccountIntervalError(code)


@dataclass(frozen=True, kw_only=True)
class StagedInterval:
    """One prefetched flat interval: the frame for the provider plus the original receipts and manifest for the
    caller's private archive. ``observed_at`` is the real fenced observation, at or after ``frame.interval.end``.
    The collector's self-check bundle is not retained."""
    frame: BaselineFrame
    receipts: tuple[SourceReceipt, ...]
    manifest_sha256: str
    observed_at: datetime


def _pending_boundary(previous):
    """The next exact interval end the reducer requires: a pending 22:00 cutoff, else the next Seoul midnight."""
    cutoff = _required_cutoff(previous)
    if cutoff is not None and previous.asof < cutoff:
        return cutoff, False
    day = previous.asof.astimezone(KST).date()
    return datetime.combine(day + timedelta(days=1), time(), tzinfo=KST), True


def _opening_collection_baseline(previous, opening):
    """Collector self-check input for a capture spanning Seoul midnight; module-private, never exported or staged.

    The collector validates its bundle against a same-day baseline at most 30 s old, and no reducer export can
    carry the new day before the interval exists. Under the flat rule these are the reducer's real midnight
    opening values; the bridge then reconciles the reducer's own export against the same accounts.
    """
    return RiskBaseline(day_start_equity=previous.equity_krw, prior_high_watermark=previous.high_watermark,
                        observed_daily_loss=_ZERO, approved_effective_floor=previous.approved_effective_floor,
                        first_trading_day=previous.first_trading_day, asof=opening,
                        source_sha256=previous.state_digest)


def _stamped(account, end):
    """The same evidence stamped at the boundary instant; rows and the manifest are unchanged, and each page's
    own digest is recomputed for the new end."""
    return replace(account, observed_at=end, restrictions=replace(account.restrictions, asof=end),
                   fx=tuple(replace(rate, asof=end) for rate in account.fx),
                   pages=tuple(replace(page, end=end, page_sha256="") for page in account.pages))


def upbit_interval_frame(previous: BaselineState, collection: CollectionResult) -> BaselineFrame:
    """Pure: one flat interval [previous.asof, end) over one capture, or a fixed-code refusal."""
    try:
        _require(type(previous) is BaselineState and type(collection) is CollectionResult,
                 "ACCOUNT_INTERVAL_INPUT_REQUIRED")
        bundle, receipts = collection.bundle, collection.receipts
        _require(len(bundle.accounts) == 1 and bool(receipts)
                 and bundle.accounts[0].venue == "upbit" and bundle.accounts[0].execution_quote == "KRW"
                 and all(page.source_sha256 == collection.manifest_sha256 for page in bundle.accounts[0].pages)
                 and bundle.risk_baseline.first_trading_day == previous.first_trading_day,
                 "ACCOUNT_INTERVAL_COLLECTION_BINDING_INVALID")
        account = bundle.accounts[0]
        first, observed = receipts[0].received_at, account.observed_at
        _require(previous.asof < first, "ACCOUNT_INTERVAL_CAPTURE_NOT_AFTER_PREVIOUS")
        boundary, _ = _pending_boundary(previous)
        if observed < boundary:
            end = observed
        else:
            _require(first <= boundary, "ACCOUNT_INTERVAL_BOUNDARY_MISSED")
            end = boundary
        # ponytail: flat-only exact extrema; held intervals need a reviewed price-path source
        _require(account.positions == (), "ACCOUNT_INTERVAL_EXTREMA_EVIDENCE_REQUIRED")
        for page in account.pages:
            if page.kind == "fills":
                _require(all(row.executed_at < previous.asof for row in page.rows),
                         "ACCOUNT_INTERVAL_EXTREMA_EVIDENCE_REQUIRED")
            elif page.kind == "flows":
                _require(all(row.effective_at < previous.asof for row in page.rows),
                         "ACCOUNT_INTERVAL_EXTERNAL_FLOW_UNSUPPORTED")
        equity = build_observation(bundle, now=observed).risk.equity
        accounts = (account if end == observed else _stamped(account, end),)
        interval = BaselineInterval(account_scope=previous.account_scope, sequence=previous.sequence + 1,
            previous_state_digest=previous.state_digest, start=previous.asof, end=end, equity_krw=equity,
            minimum_equity_krw=equity, maximum_equity_krw=equity,
            realized_net_total_krw=previous.realized_net_total_krw,
            gross_external_inflows_krw=_ZERO, gross_external_outflows_krw=_ZERO,
            source_sha256=content_digest(accounts), coverage_sha256=collection.manifest_sha256)
        return BaselineFrame(interval=interval, accounts=accounts)
    except (AccountIntervalError, EvidenceError, BaselineError):
        raise
    except (ValueError, TypeError, AttributeError, KeyError, IndexError, DecimalException, OverflowError):
        raise AccountIntervalError("ACCOUNT_INTERVAL_EVIDENCE_REFUSED") from None


class UpbitIntervalSource:
    """``source(previous, now)`` for ContinuousAccountProvider over one prefetched collection.

    ``collect`` fetches and stages before the tick time is chosen; ``__call__`` returns the staged frame without
    I/O when it extends ``previous`` or is its committed endpoint, so same-tick redelivery advances the head once.
    Frames live in memory only: after a restart the provider refuses until a fresh ``collect``.
    """

    def __init__(self):
        self._lock = Lock()          # guards _staged only; collect_upbit runs outside it
        self._staged = None

    def collect(self, collector_source, *, previous: BaselineState, anchor: OpeningAnchor,
                coverage: CoverageEvidence, clock, trade_fees: tuple[TradeFeeEvidence, ...] = ()) -> StagedInterval:
        try:
            _require(type(previous) is BaselineState and callable(clock) and type(trade_fees) is tuple,
                     "ACCOUNT_INTERVAL_INPUT_REQUIRED")
            _require(getattr(collector_source, "account_scope", None) == previous.account_scope,
                     "ACCOUNT_INTERVAL_SCOPE_MISMATCH")
            exported = risk_baseline(previous, now=previous.asof, expected_head=previous.state_digest)
            started = instant(clock())
            boundary, midnight = _pending_boundary(previous)
            _require(started <= boundary, "ACCOUNT_INTERVAL_BOUNDARY_MISSED")
            in_window = boundary - started <= timedelta(seconds=BOUNDARY_LEAD_SECONDS)
            baseline = _opening_collection_baseline(previous, boundary) if in_window and midnight else exported
            collection = collect_upbit(collector_source, anchor=anchor, coverage=coverage, risk_baseline=baseline,
                                       clock=clock, trade_fees=trade_fees)
            if in_window and midnight:   # R17: and the 30 s rule against previous.asof that every capture meets
                _fresh(previous.asof, collection.bundle.accounts[0].observed_at)
            frame = upbit_interval_frame(previous, collection)
            _require(not in_window or frame.interval.end == boundary, "ACCOUNT_INTERVAL_BOUNDARY_NOT_BRACKETED")
            staged = StagedInterval(frame=frame, receipts=collection.receipts,
                                    manifest_sha256=collection.manifest_sha256,
                                    observed_at=collection.bundle.accounts[0].observed_at)
        except (AccountIntervalError, EvidenceError, BaselineError):
            raise
        except Exception:
            raise AccountIntervalError("ACCOUNT_INTERVAL_COLLECTION_FAILED") from None
        with self._lock:
            self._staged = staged
        return staged

    def __call__(self, previous: BaselineState, now: datetime) -> BaselineFrame:
        try:
            _require(type(previous) is BaselineState and type(now) is datetime and now.utcoffset() is not None,
                     "ACCOUNT_INTERVAL_INPUT_REQUIRED")
            with self._lock:
                staged = self._staged
            _require(staged is not None, "ACCOUNT_INTERVAL_PREFETCH_REQUIRED")
            interval = staged.frame.interval
            extends = (interval.previous_state_digest == previous.state_digest
                       and interval.sequence == previous.sequence + 1)
            committed = (interval.sequence == previous.sequence and interval.end == previous.asof
                         and content_digest(interval) == previous.last_interval_digest)
            _require(extends or committed, "ACCOUNT_INTERVAL_PREFETCH_REQUIRED")
            _require(staged.observed_at <= now, "ACCOUNT_INTERVAL_EVIDENCE_AFTER_TICK")
            return staged.frame
        except AccountIntervalError:
            raise
        except (ValueError, TypeError, AttributeError):
            raise AccountIntervalError("ACCOUNT_INTERVAL_EVIDENCE_REFUSED") from None


@dataclass(frozen=True, kw_only=True)
class ContinuousCapture:
    """Source view without the collector's temporary risk-baseline self-check."""
    accounts: tuple[AccountEvidence, ...]
    receipts: tuple[SourceReceipt, ...]
    manifest_sha256: str
    observed_at: datetime


@dataclass(frozen=True, kw_only=True)
class ContinuousIntervalPreview:
    """Verified source-path mathematics, deliberately NOT a BaselineFrame.

    Current owner limits, chronological D12 floor ratchets and durable E2 halt
    integration are still required before any account baseline may advance.
    Consequently ContinuousAccountProvider rejects this type.
    """
    interval: BaselineInterval
    accounts: tuple[AccountEvidence, ...]
    path: ContinuousPath
    coverage: VerifiedCoverage
    valuation: PathValuation

    @property
    def execution_ready(self):
        return False


@dataclass(frozen=True, kw_only=True)
class StagedContinuousCandidate:
    preview: ContinuousIntervalPreview
    path_sha256: str
    manifest_sha256: str
    observed_at: datetime


def preview_continuous_upbit_interval(previous: BaselineState, collection: CollectionResult,
                                    path: ContinuousPath, *, coverage_verifier, now: datetime) -> ContinuousIntervalPreview:
    """Exact arithmetic wrapper for the independently authenticated held path."""
    try:
        with localcontext() as numeric:
            numeric.prec = 512
            numeric.traps[Inexact] = True
            return _preview_continuous_upbit_interval(previous, collection, path,
                                                    coverage_verifier=coverage_verifier, now=now)
    except (AccountIntervalError, ContinuousEvidenceError, EvidenceError, BaselineError):
        raise
    except (ValueError, TypeError, AttributeError, KeyError, DecimalException, OverflowError):
        raise AccountIntervalError("ACCOUNT_INTERVAL_CONTINUOUS_EVIDENCE_REFUSED") from None


def _preview_continuous_upbit_interval(previous: BaselineState, collection: CollectionResult,
                                    path: ContinuousPath, *, coverage_verifier, now: datetime) -> ContinuousIntervalPreview:
    """A held-position candidate after independently authenticated complete-path evidence.

    The original fenced capture reconciles cash, positions, history and fees.
    A reviewed verifier must additionally authenticate every ordered valuation
    change through the half-open endpoint. No production Upbit coverage verifier
    is shipped. Raw snapshots, a heartbeat, or a boolean cannot use this path.
    The baseline reducer and bridge recheck the derived extrema and counters.
    """
    try:
        _require(type(previous) is BaselineState and type(collection) is CollectionResult,
                 "ACCOUNT_INTERVAL_INPUT_REQUIRED")
        bundle, receipts = collection.bundle, collection.receipts
        _require(len(bundle.accounts) == 1 and bool(receipts)
                 and bundle.accounts[0].venue == "upbit" and bundle.accounts[0].execution_quote == "KRW"
                 and bundle.accounts[0].account_scope == previous.account_scope
                 and all(page.source_sha256 == collection.manifest_sha256 for page in bundle.accounts[0].pages)
                 and bundle.risk_baseline.first_trading_day == previous.first_trading_day,
                 "ACCOUNT_INTERVAL_COLLECTION_BINDING_INVALID")
        account = bundle.accounts[0]
        first, observed = receipts[0].received_at, account.observed_at
        _require(previous.asof < first <= observed <= now, "ACCOUNT_INTERVAL_CAPTURE_NOT_AFTER_PREVIOUS")
        _fresh(previous.asof, observed)
        boundary, _ = _pending_boundary(previous)
        end = min(observed, boundary)
        _require(observed < boundary or first <= boundary, "ACCOUNT_INTERVAL_BOUNDARY_MISSED")
        _require(type(path) is ContinuousPath and path.account_scope == previous.account_scope
                 and path.previous_state_digest == previous.state_digest
                 and path.start == previous.asof and path.end == end,
                 "ACCOUNT_INTERVAL_PRICE_PATH_BINDING_INVALID")
        observation = build_observation(bundle, now=observed)
        fills = observation.fills
        _require(all(fill.executed_at < end for fill in fills), "ACCOUNT_INTERVAL_FILL_AFTER_BOUNDARY")
        historical = tuple(fill for fill in fills if fill.executed_at < previous.asof)
        inside = tuple(fill for fill in fills if previous.asof <= fill.executed_at < end)
        prior = account_fills(historical)
        _require(prior.ok and prior.duplicate_count == 0, "ACCOUNT_INTERVAL_PRIOR_HISTORY_REFUSED")
        _require(len(account.opening_cash) == 1 and account.opening_cash[0].currency == "KRW",
                 "ACCOUNT_INTERVAL_KRW_ANCHOR_REQUIRED")
        cash = account.opening_cash[0].amount
        cash += sum((amount for venue, scope, amount in prior.cash_deltas_by_account_krw
                     if venue == "upbit" and scope == previous.account_scope), _ZERO)
        seen_flows = {}
        for page in account.pages:
            if page.kind == "flows":
                for flow in page.rows:
                    if flow.flow_id in seen_flows:
                        _require(seen_flows[flow.flow_id] == flow, "ACCOUNT_INTERVAL_FLOW_CONTRADICTION")
                        continue
                    seen_flows[flow.flow_id] = flow
                    _require(flow.effective_at < previous.asof,
                             "ACCOUNT_INTERVAL_EXTERNAL_FLOW_UNSUPPORTED")
                    _require(flow.currency == "KRW" and flow.kind in ("deposit", "withdrawal"),
                             "ACCOUNT_INTERVAL_EXTERNAL_FLOW_UNSUPPORTED")
                    cash += flow.amount if flow.kind == "deposit" else -flow.amount
        units = tuple((row[3], row[4]) for row in prior.inventory if row[4] != 0)
        valuation = value_path(path, opening_cash_krw=cash, opening_units=units, historical_fills=historical,
            interval_fills=inside, previous_equity_krw=previous.equity_krw,
            previous_realized_net_krw=previous.realized_net_total_krw)
        _require(len(account.balances) == 1 and account.balances[0].currency == "KRW"
                 and valuation.closing_cash_krw == account.balances[0].total,
                 "ACCOUNT_INTERVAL_CLOSING_CASH_MISMATCH")
        closing_units = tuple(sorted((position.symbol, position.units) for position in account.positions))
        _require(valuation.closing_units == closing_units, "ACCOUNT_INTERVAL_CLOSING_HOLDINGS_MISMATCH")
        marks = {mark.symbol: mark for mark in valuation.closing_marks}
        if end == observed:
            _require(all(position.price == marks[position.symbol].price for position in account.positions)
                     and valuation.equity_krw == observation.risk.equity,
                     "ACCOUNT_INTERVAL_CLOSING_MARK_MISMATCH")
            accounts = (account,)
        else:
            # The fenced capture brackets the boundary and has no account changes.
            # Prices are reconstructed from the verified path at the boundary,
            # never copied backwards from a later ticker snapshot.
            endpoint = _stamped(account, end)
            endpoint = replace(endpoint, positions=tuple(replace(position, price=marks[position.symbol].price,
                asof=end) for position in endpoint.positions))
            accounts = (endpoint,)
        proof = verify_coverage(path, account_capture_sha256=content_digest((collection.manifest_sha256,
                                collection.bundle.accounts, accounts)), verifier=coverage_verifier, now=now)
        _require(proof.verified_at >= observed, "ACCOUNT_INTERVAL_COVERAGE_BEFORE_CAPTURE")
        interval = BaselineInterval(account_scope=previous.account_scope, sequence=previous.sequence+1,
            previous_state_digest=previous.state_digest, start=previous.asof, end=end,
            equity_krw=valuation.equity_krw, minimum_equity_krw=valuation.minimum_equity_krw,
            maximum_equity_krw=valuation.maximum_equity_krw, realized_net_total_krw=valuation.realized_net_total_krw,
            gross_external_inflows_krw=_ZERO, gross_external_outflows_krw=_ZERO,
            source_sha256=content_digest(accounts), coverage_sha256=content_digest((path, proof)))
        # Includes midnight/cutoff, all FIFO counters and account-mark reconciliation.
        advance_account_baseline(previous, interval, accounts, now=now)
        return ContinuousIntervalPreview(interval=interval, accounts=accounts, path=path,
                                         coverage=proof, valuation=valuation)
    except (AccountIntervalError, ContinuousEvidenceError, EvidenceError, BaselineError):
        raise
    except (ValueError, TypeError, AttributeError, KeyError, IndexError, DecimalException, OverflowError):
        raise AccountIntervalError("ACCOUNT_INTERVAL_CONTINUOUS_EVIDENCE_REFUSED") from None


class ContinuousUpbitCandidateSource:
    """Candidate capture only; cannot serve ContinuousAccountProvider or live trading.

    ``path_source(previous, capture, end)`` must return a candidate from an
    already-running continuous recorder. ``coverage_verifier(request, path)``
    independently authenticates the source contract. Both are trusted reviewed
    code dependencies; neither is loaded from a user JSON field. A class check
    alone must never enable controlled execution. The shipped production source
    remains flat-only until a venue completeness adapter has been established.
    """
    def __init__(self, *, path_source, coverage_verifier, archive_root: Path):
        _require(callable(path_source) and callable(coverage_verifier),
                 "ACCOUNT_INTERVAL_CONTINUOUS_INTEGRATIONS_REQUIRED")
        self._lock, self._staged = Lock(), None
        self._path_source, self._coverage_verifier = path_source, coverage_verifier
        _require(isinstance(archive_root, Path) and archive_root.is_absolute(),
                 "ACCOUNT_INTERVAL_CONTINUOUS_ARCHIVE_REQUIRED")
        self._archive_root = archive_root

    def collect(self, collector_source, *, previous: BaselineState, anchor: OpeningAnchor,
                coverage: CoverageEvidence, clock, trade_fees: tuple[TradeFeeEvidence, ...] = ()) -> StagedContinuousCandidate:
        with self._lock:
            self._staged = None
        try:
            _require(type(previous) is BaselineState and callable(clock) and type(trade_fees) is tuple,
                     "ACCOUNT_INTERVAL_INPUT_REQUIRED")
            _require(getattr(collector_source, "account_scope", None) == previous.account_scope,
                     "ACCOUNT_INTERVAL_SCOPE_MISMATCH")
            exported = risk_baseline(previous, now=previous.asof, expected_head=previous.state_digest)
            started = instant(clock())
            boundary, midnight = _pending_boundary(previous)
            _require(started <= boundary, "ACCOUNT_INTERVAL_BOUNDARY_MISSED")
            in_window = boundary-started <= timedelta(seconds=BOUNDARY_LEAD_SECONDS)
            # Collector self-check only; no opening baseline is published. The
            # bridge subsequently derives the true midnight opening from the path.
            baseline = _opening_collection_baseline(previous, boundary) if in_window and midnight else exported
            collection = collect_upbit(collector_source, anchor=anchor, coverage=coverage, risk_baseline=baseline,
                                       clock=clock, trade_fees=trade_fees)
            observed = collection.bundle.accounts[0].observed_at
            end = min(observed, boundary)
            capture = ContinuousCapture(accounts=collection.bundle.accounts, receipts=collection.receipts,
                                        manifest_sha256=collection.manifest_sha256, observed_at=observed)
            path = self._path_source(previous, capture, end)
            now = instant(clock())
            preview = preview_continuous_upbit_interval(previous, collection, path,
                                                    coverage_verifier=self._coverage_verifier, now=now)
            _require(not in_window or preview.interval.end == boundary, "ACCOUNT_INTERVAL_BOUNDARY_NOT_BRACKETED")
            candidate_sha = archive_candidate(path, root=self._archive_root)
            staged = StagedContinuousCandidate(preview=preview, path_sha256=candidate_sha,
                                               manifest_sha256=collection.manifest_sha256, observed_at=now)
        except (AccountIntervalError, ContinuousEvidenceError, EvidenceError, BaselineError):
            raise
        except Exception:
            raise AccountIntervalError("ACCOUNT_INTERVAL_CONTINUOUS_COLLECTION_FAILED") from None
        with self._lock:
            self._staged = staged
        return staged

    def latest(self):
        """The last audit candidate, never an account-provider frame."""
        with self._lock:
            _require(self._staged is not None, "ACCOUNT_INTERVAL_PREFETCH_REQUIRED")
            return self._staged

    def __call__(self, previous, now):
        raise AccountIntervalError("CONTINUOUS_LIVE_RISK_INTEGRATION_REQUIRED")
