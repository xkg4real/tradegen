"""Reconcile a real interval-derived baseline before durable account-provider use.

The source and separately trusted head are explicit caller integrations. They
must authenticate account identity/coverage and the latest head; this module
does not turn a periodic balance poll or a caller-supplied hash into that proof.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import DecimalException, Inexact, localcontext
import re
from threading import Lock

from execution_accounts.baseline import (
    BaselineAnchor, BaselineConventions, BaselineInterval, BaselineState,
    advance_baseline, initialize_baseline, restore_state, risk_baseline, state_json,
)
from execution_accounts.baseline_store import CheckpointStore
from execution_accounts.model import AccountBundle, AccountEvidence, content_digest
from execution_accounts.provider import build_observation
from execution_control.controller import AccountObservation
from execution_control.risk import account_fills


class BaselineBridgeError(ValueError):
    """Fixed error codes without source exception text or private account values."""


def _require(ok, code):
    if not ok:
        raise BaselineBridgeError(code)


@dataclass(frozen=True, kw_only=True)
class BaselineFrame:
    interval: BaselineInterval
    accounts: tuple[AccountEvidence, ...]


@dataclass(frozen=True, kw_only=True)
class BaselineUpdate:
    state: BaselineState
    bundle: AccountBundle
    observation: AccountObservation


def _reconcile(state, accounts, *, now, source_sha256, interval_start=None):
    baseline = risk_baseline(state, now=now, expected_head=state.state_digest)
    _require(type(accounts) is tuple and len(accounts) == 1 and type(accounts[0]) is AccountEvidence,
             "BASELINE_BRIDGE_SINGLE_ACCOUNT_REQUIRED")
    _require(content_digest(accounts) == source_sha256, "BASELINE_BRIDGE_ENDPOINT_CHANGED")
    checkpoint = state.recovery_checkpoint
    if checkpoint is not None and checkpoint.cutoff_at == state.asof:
        _require(checkpoint.source_sha256 == source_sha256, "BASELINE_BRIDGE_RECOVERY_SOURCE_CHANGED")
    account = accounts[0]
    _require(account.account_scope == state.account_scope and account.execution_quote == "KRW"
             and account.observed_at == state.asof, "BASELINE_BRIDGE_ACCOUNT_BINDING_MISMATCH")
    bundle = AccountBundle(accounts=accounts, risk_baseline=baseline)
    observation = build_observation(bundle, now=now)
    _require(observation.risk.equity == state.equity_krw and observation.asof == state.asof,
             "BASELINE_BRIDGE_EQUITY_MISMATCH")
    # Existing reconciliation has already validated row types/page chains.
    for page in account.pages:
        if page.kind == "fills":
            _require(all(row.executed_at < state.asof for row in page.rows),
                     "BASELINE_BRIDGE_CUTOFF_MISMATCH")
        elif page.kind == "flows":
            _require(all(row.effective_at < state.asof for row in page.rows),
                     "BASELINE_BRIDGE_CUTOFF_MISMATCH")
            if interval_start is not None:
                _require(not any(interval_start <= row.effective_at for row in page.rows),
                         "BASELINE_BRIDGE_INTERVAL_FLOW_REFUSED")
    accounting = account_fills(observation.fills)
    _require(accounting.ok and accounting.realized_net_profit_krw == state.realized_net_total_krw,
             "BASELINE_BRIDGE_CUMULATIVE_PROFIT_MISMATCH")
    _require(observation.risk.current_day_realized_net_profit
             == state.realized_net_total_krw-state.day_open_realized_net_total_krw,
             "BASELINE_BRIDGE_DAILY_PROFIT_MISMATCH")
    _require(observation.risk.prior_day_realized_net_profit == state.previous_day_realized_net_krw,
             "BASELINE_BRIDGE_PRIOR_PROFIT_MISMATCH")
    return BaselineUpdate(state=state, bundle=bundle, observation=observation)


def initialize_account_baseline(conventions: BaselineConventions, anchor: BaselineAnchor,
                                accounts: tuple[AccountEvidence, ...], *, now: datetime) -> BaselineUpdate:
    """Reconcile an explicitly reviewed anchor before the separate store.seed step.

    The anchor baseline source digest must bind these exact account records.
    Historical day-open/peak/trough evidence still requires independent review.
    This operation does not choose an anchor, create files or advance trusted heads.
    """
    try:
        with localcontext() as numeric:
            numeric.prec = 512; numeric.traps[Inexact] = True
            state = initialize_baseline(conventions, anchor)
            return _reconcile(state, accounts, now=now, source_sha256=anchor.baseline.source_sha256)
    except BaselineBridgeError:
        raise
    except (ValueError, TypeError, AttributeError, DecimalException, OverflowError):
        raise BaselineBridgeError("BASELINE_BRIDGE_EVIDENCE_REFUSED") from None


def advance_account_baseline(previous: BaselineState, interval: BaselineInterval,
                             accounts: tuple[AccountEvidence, ...], *, now: datetime) -> BaselineUpdate:
    """Use the actual reduced baseline, then reconcile both account and counters.

    The narrow current path is one KRW-settled account. All cumulative FIFO totals
    start at its complete, zero-inventory source origin preceding its first trade.
    There is no invented offset, dummy baseline, endpoint-derived extremum or
    permissive fallback when full account evidence cannot be reconstructed.
    """
    try:
        with localcontext() as numeric:
            numeric.prec = 512; numeric.traps[Inexact] = True
            state = advance_baseline(previous, interval)
            return _reconcile(state, accounts, now=now, source_sha256=interval.source_sha256,
                              interval_start=interval.start)
    except BaselineBridgeError:
        raise
    except (ValueError, TypeError, AttributeError, DecimalException, OverflowError):
        raise BaselineBridgeError("BASELINE_BRIDGE_EVIDENCE_REFUSED") from None


def reconcile_committed_baseline(state: BaselineState, accounts: tuple[AccountEvidence, ...], *,
                                  now: datetime, source_sha256: str,
                                  interval_start: datetime | None = None) -> BaselineUpdate:
    """Project an already committed state without advancing or persisting it.

    The strict state codec proves internal integrity only. This pure function
    does not prove that a state was committed, read an independent head, verify
    a source/owner, or grant current account or trading authority. The caller
    must bind state and source_sha256 to its actual committed package; computing
    a fresh hash of arbitrary accounts is not that provenance proof. Optional
    interval_start is that package's original start, not a fabricated cutoff.

    The observed timestamp and all baseline counters remain unchanged. Existing
    full-account reconciliation (including FIFO fees, source identity and half-
    open cutoffs) is reused under exact decimal arithmetic. Guard/controller
    latches that are outside BaselineState require a separate verified consumer.
    No initialization, baseline reduction, store, CAS or journal call occurs.
    """
    try:
        with localcontext() as numeric:
            numeric.prec = 512; numeric.traps[Inexact] = True
            _require(type(state) is BaselineState, "BASELINE_BRIDGE_STATE_REQUIRED")
            _require(type(source_sha256) is str and re.fullmatch(r"[0-9a-f]{64}", source_sha256) is not None,
                     "BASELINE_BRIDGE_SOURCE_DIGEST_REQUIRED")
            # Snapshot strict fields without treating the self-digest as an
            # external latest-head attestation or migrating an existing version.
            retained = restore_state(state_json(state), expected_head=state.state_digest)
            if interval_start is not None:
                _require(type(interval_start) is datetime and interval_start.utcoffset() is not None
                         and 2 <= interval_start.year <= 9998 and interval_start < retained.asof,
                         "BASELINE_BRIDGE_INTERVAL_START_INVALID")
            return _reconcile(retained, accounts, now=now, source_sha256=source_sha256,
                              interval_start=interval_start)
    except BaselineBridgeError:
        raise
    except (ValueError, TypeError, AttributeError, DecimalException, OverflowError, RecursionError):
        raise BaselineBridgeError("BASELINE_BRIDGE_EVIDENCE_REFUSED") from None


class ContinuousAccountProvider:
    """Explicit source + private checkpoint + separately trusted compare-and-set.

    ``source(previous, now)`` returns BaselineFrame. ``trusted_head.read()`` returns
    the independently retained digest; ``compare_and_set(old, new)`` returns exact
    True only after its durable update succeeds. Source/head are trusted adapters,
    not a Python sandbox. A local file with a matching hash is not such authority.
    Initialization is deliberately separate and never runs on a missing store.
    """
    def __init__(self, *, source, store: CheckpointStore, trusted_head):
        _require(callable(source) and type(store) is CheckpointStore
                 and callable(getattr(trusted_head, "read", None))
                 and callable(getattr(trusted_head, "compare_and_set", None)),
                 "BASELINE_PROVIDER_INTEGRATIONS_REQUIRED")
        self._source, self._store, self._head = source, store, trusted_head
        self._lock = Lock()

    def __call__(self, now: datetime) -> AccountObservation:
        _require(type(now) is datetime and now.utcoffset() is not None and 2 <= now.year <= 9998,
                 "BASELINE_PROVIDER_AWARE_TIME_REQUIRED")
        _require(self._lock.acquire(blocking=False), "BASELINE_PROVIDER_CONCURRENT_CALL")
        try:
            try:
                old_head = self._head.read()
            except Exception:
                raise BaselineBridgeError("BASELINE_TRUSTED_HEAD_READ_FAILED") from None
            try:
                previous = self._store.load(expected_head=old_head)
            except Exception:
                raise BaselineBridgeError("BASELINE_PROVIDER_CHECKPOINT_REFUSED") from None
            try:
                frame = self._source(previous, now)
            except Exception:
                raise BaselineBridgeError("BASELINE_INTERVAL_SOURCE_FAILED") from None
            _require(type(frame) is BaselineFrame, "BASELINE_PROVIDER_FRAME_REQUIRED")
            update = advance_account_baseline(previous, frame.interval, frame.accounts, now=now)
            if update.state.state_digest != old_head:
                try:
                    self._store.commit(update.state, expected_previous_head=old_head)
                except Exception:
                    raise BaselineBridgeError("BASELINE_PROVIDER_COMMIT_REFUSED") from None
                try:
                    accepted = self._head.compare_and_set(old_head, update.state.state_digest)
                except Exception:
                    raise BaselineBridgeError("BASELINE_TRUSTED_HEAD_UPDATE_FAILED") from None
                _require(accepted is True, "BASELINE_TRUSTED_HEAD_UPDATE_REFUSED")
            try:
                confirmed = self._head.read()
            except Exception:
                raise BaselineBridgeError("BASELINE_TRUSTED_HEAD_READ_FAILED") from None
            _require(confirmed == update.state.state_digest, "BASELINE_TRUSTED_HEAD_CHANGED")
            return update.observation
        finally:
            self._lock.release()
