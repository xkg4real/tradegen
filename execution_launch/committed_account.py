"""Read a committed local guard/account pair without reducing or publishing it.

The caller supplies an actual open control transaction; this module never opens
one or acquires a publisher lock. Stores and independently retained heads are
read twice. No initialization, baseline advancement, commit, CAS, source fetch,
owner authorization or execution occurs. A matching local package/receipt proves
correspondence to that commit, not the authenticity of its source/owner claims.

This deliberately is NOT the callable account provider accepted by Controller.
The separate daily-stop and provenance metadata must survive a future reviewed
consumer integration. Every returned projection remains non-operational. In
particular a later fill/reconcile row does not refresh the old endpoint account.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, replace
from datetime import date, datetime
from decimal import Decimal, DecimalException, Inexact, localcontext

from core.compliance.model import KST
from execution_accounts.baseline import BaselineInterval, BaselineState
from execution_accounts.baseline_bridge import reconcile_committed_baseline
from execution_accounts.baseline_store import CheckpointStore
from execution_accounts.continuous import ContinuousPath, VerifiedCoverage
from execution_accounts.model import content_digest
from execution_control.capability import digest as control_digest
from execution_control.controller import AccountObservation, _fold
from execution_control.risk import RiskPolicy
from execution_control.store import Journal, Transaction, _utc
from execution_launch.continuous_guard import (
    AccountCaptureInputs, OwnerContextClaim, ValuationInputs, _SHA, _input_digest,
    _instant, _owner, _owner_terms,
)
from execution_launch.continuous_guard_commit import (
    COMPLETE, CONSISTENT, PREPARE, GuardCheckpointStore, GuardCommitReceipt,
    _PACKAGE_KEYS, classify_restart,
)


class CommittedAccountError(ValueError):
    """Fixed diagnostics; never private evidence or underlying exception text."""


def _need(ok, code):
    if not ok:
        raise CommittedAccountError(code)


def _digest(value):
    _need(type(value) is str and _SHA.fullmatch(value) is not None,
          "COMMITTED_ACCOUNT_DIGEST_REQUIRED")
    return value


def _package_digest(package):
    return content_digest(tuple((name, package[name]) for name in sorted(_PACKAGE_KEYS)))


def _check_package(package):
    _need(type(package) is dict and set(package) == _PACKAGE_KEYS,
          "COMMITTED_ACCOUNT_PACKAGE_REQUIRED")
    types = {"baseline_before": BaselineState, "policy": RiskPolicy,
             "owner_before": OwnerContextClaim, "owner_after": OwnerContextClaim,
             "path": ContinuousPath, "valuation_inputs": ValuationInputs,
             "account_capture": AccountCaptureInputs, "coverage": VerifiedCoverage,
             "interval": BaselineInterval, "now": datetime}
    _need(all(type(package[name]) is cls for name, cls in types.items()),
          "COMMITTED_ACCOUNT_PACKAGE_REQUIRED")
    _instant(package["now"])
    _owner(package["owner_before"]); _owner(package["owner_after"])
    _need(_owner_terms(package["owner_before"]) == _owner_terms(package["owner_after"]),
          "COMMITTED_ACCOUNT_OWNER_CLAIM_CHANGED")
    return _package_digest(package)


@dataclass(frozen=True, kw_only=True)
class CommittedAccountProjection:
    """Descriptive local evidence, never a current owner/source authorization."""
    observation: AccountObservation
    policy_day: date
    daily_stopped: bool
    transaction_id: str
    guard_head: str
    baseline_head: str
    completion_head: str
    receipt_control_head: str
    observed_control_head: str
    owner_claim: OwnerContextClaim
    policy_sha256: str

    @property
    def execution_ready(self):
        return False


class CommittedAccountProvider:
    """Non-callable reader of one explicit commit, under the caller's Journal lock.

    Head adapters are the existing explicitly trusted read integrations, not a
    Python sandbox. The immutable package snapshot has no source issuance power.
    No constructor or read path creates a missing store or adopts a local head.
    """
    def __init__(self, *, package: dict, receipt: GuardCommitReceipt,
                 expected_guard_head: str, expected_baseline_head: str,
                 expected_control_head: str, journal: Journal,
                 guard_store: GuardCheckpointStore, guard_head,
                 baseline_store: CheckpointStore, baseline_head):
        try:
            _need(type(receipt) is GuardCommitReceipt
                  and type(receipt.permanently_halted) is bool and type(receipt.replayed) is bool,
                  "COMMITTED_ACCOUNT_RECEIPT_REQUIRED")
            for value in (receipt.transaction_id, receipt.guard_head, receipt.baseline_head,
                          receipt.control_head, expected_guard_head, expected_baseline_head,
                          expected_control_head):
                _digest(value)
            _need(type(journal) is Journal and type(guard_store) is GuardCheckpointStore
                  and type(baseline_store) is CheckpointStore
                  and all(callable(getattr(head, "read", None)) for head in (guard_head, baseline_head)),
                  "COMMITTED_ACCOUNT_INTEGRATIONS_REQUIRED")
            original = _check_package(package)
            self._package = deepcopy(package)
            _need(_check_package(self._package) == original, "COMMITTED_ACCOUNT_PACKAGE_CHANGED")
            self._package_sha256 = original
            self._receipt = deepcopy(receipt)
            self._expected_guard = expected_guard_head
            self._expected_baseline = expected_baseline_head
            self._expected_control = expected_control_head
            self._journal = journal
            self._guard_store, self._guard_head = guard_store, guard_head
            self._baseline_store, self._baseline_head = baseline_store, baseline_head
        except CommittedAccountError:
            raise
        except (ValueError, TypeError, AttributeError, KeyError, DecimalException, OverflowError, RecursionError):
            raise CommittedAccountError("COMMITTED_ACCOUNT_INPUT_REFUSED") from None

    def _events(self, transaction):
        _need(type(transaction) is Transaction and transaction._journal is self._journal,
              "COMMITTED_ACCOUNT_TRANSACTION_REQUIRED")
        try:
            events = transaction.events  # checks thread-bound active transaction identity first
            self._journal._check_paths()
            rows, size = self._journal._load(initialize=False)
            _need(tuple(rows) == events and size == transaction._size,
                  "COMMITTED_ACCOUNT_CONTROL_CHANGED")
            return events
        except CommittedAccountError:
            raise
        except OSError:
            raise CommittedAccountError("COMMITTED_ACCOUNT_CONTROL_READ_REFUSED") from None
        except (ValueError, RuntimeError, AttributeError):
            raise CommittedAccountError("COMMITTED_ACCOUNT_TRANSACTION_REQUIRED") from None

    def _states(self):
        try:
            receipt = self._receipt
            _need(self._guard_head.read() == receipt.guard_head
                  and self._baseline_head.read() == receipt.baseline_head,
                  "COMMITTED_ACCOUNT_HEAD_CHANGED")
            guard = self._guard_store.load(expected_head=receipt.guard_head)
            baseline = self._baseline_store.load(expected_head=receipt.baseline_head)
            _need(guard.baseline == baseline, "COMMITTED_ACCOUNT_STORE_DISAGREEMENT")
            _need(self._guard_head.read() == receipt.guard_head
                  and self._baseline_head.read() == receipt.baseline_head,
                  "COMMITTED_ACCOUNT_HEAD_CHANGED")
            return guard, baseline
        except CommittedAccountError:
            raise
        except Exception:
            raise CommittedAccountError("COMMITTED_ACCOUNT_STORE_REFUSED") from None

    def _binding(self, guard, baseline):
        package, receipt = self._package, self._receipt
        _need(_check_package(package) == self._package_sha256, "COMMITTED_ACCOUNT_PACKAGE_CHANGED")
        before, path, interval = package["baseline_before"], package["path"], package["interval"]
        capture = package["account_capture"]
        input_sha = _input_digest(self._expected_guard, before, package["policy"],
            package["owner_before"], package["owner_after"], path, package["valuation_inputs"],
            capture, package["coverage"], interval)
        path_sha = content_digest(path)
        _need(guard.previous_guard_sha256 == self._expected_guard
              and before.state_digest == self._expected_baseline
              and baseline.previous_state_digest == self._expected_baseline
              and baseline.last_interval_digest == content_digest(interval)
              and baseline.sequence == before.sequence+1
              and guard.last_input_sha256 == input_sha and guard.last_path_sha256 == path_sha,
              "COMMITTED_ACCOUNT_PACKAGE_BINDING_MISMATCH")
        _need(interval.source_sha256 == content_digest(capture.endpoint_accounts)
              and interval.coverage_sha256 == content_digest((path, package["coverage"]))
              and interval.previous_state_digest == before.state_digest
              and interval.start == path.start == before.asof
              and interval.end == path.end == baseline.asof
              and interval.account_scope == before.account_scope == baseline.account_scope == path.account_scope,
              "COMMITTED_ACCOUNT_ENDPOINT_BINDING_MISMATCH")
        claim = package["owner_after"]
        _need(guard.owner_head_sha256 == claim.owner_head_sha256
              and guard.code_sha256 == claim.code_sha256
              and guard.policy_sha256 == content_digest(package["policy"]),
              "COMMITTED_ACCOUNT_AUTHORITY_CLAIM_MISMATCH")
        binding = {"input_sha256": input_sha,
            "owner_sha256": content_digest((package["owner_before"], claim)),
            "control_head_sha256": self._expected_control, "path_sha256": path_sha,
            "old_guard_sha256": self._expected_guard, "new_guard_sha256": receipt.guard_head,
            "old_baseline_sha256": self._expected_baseline, "new_baseline_sha256": receipt.baseline_head}
        _need(content_digest(tuple(sorted(binding.items()))) == receipt.transaction_id,
              "COMMITTED_ACCOUNT_RECEIPT_BINDING_MISMATCH")
        return binding

    def _history(self, events, guard, binding, now):
        receipt = self._receipt
        _need(events and now >= datetime.fromisoformat(events[-1]["utc"]),
              "COMMITTED_ACCOUNT_CLOCK_ROLLBACK")
        # Journal has verified row bytes, chain and retained anchor. Existing
        # lifecycle validation retains all order/kill/halt/risk semantics.
        _, _, halted, _ = _fold(events)
        state = classify_restart(events, guard_head=receipt.guard_head, baseline_head=receipt.baseline_head,
            expected_guard_head=self._expected_guard, expected_baseline_head=self._expected_baseline,
            expected_control_head=self._expected_control)
        _need(state.status == CONSISTENT and state.transaction_id == receipt.transaction_id,
              "COMMITTED_ACCOUNT_COMPLETION_REQUIRED")
        prepares = [(i, row) for i, row in enumerate(events)
                    if row["kind"] == PREPARE and row["data"]["transaction_id"] == receipt.transaction_id]
        completes = [(i, row) for i, row in enumerate(events)
                     if row["kind"] == COMPLETE and row["data"]["transaction_id"] == receipt.transaction_id]
        _need(len(prepares) == len(completes) == 1, "COMMITTED_ACCOUNT_COMPLETION_REQUIRED")
        pi, prepare = prepares[0]; ci, completion = completes[0]
        _need(pi < ci and all(prepare["data"][name] == value for name, value in binding.items())
              and prepare["data"]["path_start"] == _utc(self._package["path"].start)
              and prepare["data"]["path_end"] == _utc(self._package["path"].end)
              and prepare["data"]["halt_required"] is guard.permanently_halted,
              "COMMITTED_ACCOUNT_PREPARE_BINDING_MISMATCH")
        prefix = [i for i, row in enumerate(events) if row["row_sha256"] == receipt.control_head]
        _need(len(prefix) == 1 and prefix[0] >= ci, "COMMITTED_ACCOUNT_RECEIPT_PREFIX_MISSING")
        receipt_halted = any(row["kind"] == "halt" for row in events[:prefix[0]+1])
        _need(receipt.permanently_halted is receipt_halted
              and (not guard.permanently_halted or any(row["kind"] == "halt" for row in events[:ci+1])),
              "COMMITTED_ACCOUNT_HALT_EFFECT_MISSING")
        _need(not any(row["kind"] == "risk_snapshot" and row["data"]["floor_relaxation_approved"]
                      for row in events[ci+1:]), "COMMITTED_ACCOUNT_CONTROL_EPOCH_CHANGED")
        return completion["row_sha256"], ci, halted

    def read(self, *, now: datetime, transaction: Transaction) -> CommittedAccountProjection:
        try:
            with localcontext() as numeric:
                numeric.prec = 512; numeric.traps[Inexact] = True
                return self._read(now, transaction)
        except CommittedAccountError:
            raise
        except (ValueError, RuntimeError, TypeError, AttributeError, KeyError, DecimalException,
                OverflowError, RecursionError):
            raise CommittedAccountError("COMMITTED_ACCOUNT_EVIDENCE_REFUSED") from None

    def _read(self, now, transaction):
        _instant(now)
        events = self._events(transaction)
        guard, baseline = self._states()
        binding = self._binding(guard, baseline)
        completion, complete_index, halted = self._history(events, guard, binding, now)
        _need(guard.recorded_at == self._package["now"] and guard.recorded_at <= now,
              "COMMITTED_ACCOUNT_CLOCK_ROLLBACK")
        interval = self._package["interval"]
        update = reconcile_committed_baseline(baseline, self._package["account_capture"].endpoint_accounts,
            now=now, source_sha256=interval.source_sha256, interval_start=interval.start)
        observation = update.observation
        policy_day = baseline.asof.astimezone(KST).date()
        high = max(observation.risk.prior_high_watermark, guard.high_watermark)
        floor = guard.applied_floor_krw
        if observation.risk.approved_effective_floor is not None:
            floor = max(observation.risk.approved_effective_floor, floor)
        stopped = guard.daily_stopped
        latest_control_floor = None
        for index, row in enumerate(events):
            if row["kind"] != "risk_snapshot":
                continue
            data = row["data"]
            if index > complete_index:
                _need(data["policy_digest"] == control_digest(self._package["policy"]),
                      "COMMITTED_ACCOUNT_CONTROL_EPOCH_CHANGED")
            # Retain the currently effective validated controller floor, including
            # one recorded before this commit. Taking every historical maximum
            # would incorrectly undo an approved relaxation preceding the epoch.
            latest_control_floor = (None if data["effective_floor"] is None
                                    else Decimal(data["effective_floor"]))
            high = max(high, Decimal(data["high_watermark"]))
            if data["day"] == policy_day.isoformat():
                _need(Decimal(data["day_start_equity"]) == baseline.day_start_equity,
                      "COMMITTED_ACCOUNT_DAY_OPEN_CONFLICT")
                stopped = stopped or data["daily_stopped"]
        if latest_control_floor is not None:
            floor = max(floor, latest_control_floor)
        risk = replace(observation.risk, prior_high_watermark=high, approved_effective_floor=floor,
            observed_daily_loss=max(observation.risk.observed_daily_loss, guard.observed_daily_loss),
            halted=observation.risk.halted or guard.permanently_halted or halted)
        # Do not silently re-reconcile or advance after any changed dependency.
        _need(self._states() == (guard, baseline), "COMMITTED_ACCOUNT_STATE_CHANGED")
        _need(_check_package(self._package) == self._package_sha256,
              "COMMITTED_ACCOUNT_PACKAGE_CHANGED")
        _need(self._events(transaction) == events, "COMMITTED_ACCOUNT_CONTROL_CHANGED")
        receipt = self._receipt
        return CommittedAccountProjection(observation=replace(observation, risk=risk), policy_day=policy_day,
            daily_stopped=stopped, transaction_id=receipt.transaction_id, guard_head=receipt.guard_head,
            baseline_head=receipt.baseline_head, completion_head=completion,
            receipt_control_head=receipt.control_head, observed_control_head=events[-1]["row_sha256"],
            owner_claim=deepcopy(self._package["owner_after"]), policy_sha256=guard.policy_sha256)
