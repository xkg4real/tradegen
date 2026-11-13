"""Read and explicitly publish already committed local guard/account generations.

The caller supplies an actual open control transaction; this module never opens
one or acquires a publisher lock. Publication replaces only a private in-memory
generation after direct-successor verification under that same Journal lock. Stores and independently retained heads are
read twice. No initialization, baseline advancement, commit, CAS, source fetch,
owner authorization or execution occurs. A matching local package/receipt proves
correspondence to that commit, not the authenticity of its source/owner claims.

Controller and Runner consume this exact non-callable provider so independent
daily-stop and provenance metadata survive. Every returned projection remains
non-operational. A later fill/reconcile row does not refresh the old endpoint
account; publication consumes an actual completed successor instead.
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


@dataclass(frozen=True, kw_only=True)
class CommittedGenerationInspection:
    """Historical durable correspondence, never a current account or permit."""
    transaction_id: str
    guard_head: str
    baseline_head: str
    completion_head: str
    receipt_control_head: str
    observed_control_head: str
    package_sha256: str
    input_sha256: str
    asof: datetime
    evaluated_at: datetime

    @property
    def execution_ready(self):
        return False


@dataclass(frozen=True, slots=True)
class _Generation:
    """Detached evidence, not a public source/owner authorization token."""
    package: dict
    package_sha256: str
    receipt: GuardCommitReceipt
    expected_guard: str
    expected_baseline: str
    expected_control: str
    identity_sha256: str


def _generation(package, receipt, expected_guard, expected_baseline, expected_control):
    _need(type(receipt) is GuardCommitReceipt
          and type(receipt.permanently_halted) is bool and type(receipt.replayed) is bool,
          "COMMITTED_ACCOUNT_RECEIPT_REQUIRED")
    for value in (receipt.transaction_id, receipt.guard_head, receipt.baseline_head,
                  receipt.control_head, expected_guard, expected_baseline, expected_control):
        _digest(value)
    original = _check_package(package)
    saved, saved_receipt = deepcopy(package), deepcopy(receipt)
    _need(_check_package(saved) == original and saved_receipt == receipt,
          "COMMITTED_ACCOUNT_PACKAGE_CHANGED")
    identity = content_digest((original, saved_receipt, expected_guard, expected_baseline, expected_control))
    return _Generation(saved, original, saved_receipt, expected_guard, expected_baseline,
                       expected_control, identity)


def _intact(generation):
    _need(type(generation) is _Generation
          and _check_package(generation.package) == generation.package_sha256,
          "COMMITTED_ACCOUNT_PACKAGE_CHANGED")
    _need(content_digest((generation.package_sha256, generation.receipt,
                          generation.expected_guard, generation.expected_baseline,
                          generation.expected_control)) == generation.identity_sha256,
          "COMMITTED_ACCOUNT_GENERATION_CHANGED")


class CommittedAccountProvider:
    """Non-callable reader of one published generation under the caller's Journal lock.

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
            _need(type(journal) is Journal and type(guard_store) is GuardCheckpointStore
                  and type(baseline_store) is CheckpointStore
                  and all(callable(getattr(head, "read", None)) for head in (guard_head, baseline_head)),
                  "COMMITTED_ACCOUNT_INTEGRATIONS_REQUIRED")
            generation = _generation(package, receipt, expected_guard_head,
                                     expected_baseline_head, expected_control_head)
            self._journal = journal
            self._guard_store, self._guard_head = guard_store, guard_head
            self._baseline_store, self._baseline_head = baseline_store, baseline_head
            object.__setattr__(self, "_CommittedAccountProvider__integrations",
                               (journal, guard_store, guard_head, baseline_store, baseline_head))
            object.__setattr__(self, "_CommittedAccountProvider__generation", generation)
        except CommittedAccountError:
            raise
        except (ValueError, TypeError, AttributeError, KeyError, DecimalException, OverflowError, RecursionError):
            raise CommittedAccountError("COMMITTED_ACCOUNT_INPUT_REFUSED") from None

    def __setattr__(self, name, value):
        if name in ("_CommittedAccountProvider__generation", "_CommittedAccountProvider__integrations"):
            raise AttributeError("COMMITTED_ACCOUNT_PRIVATE_STATE")
        object.__setattr__(self, name, value)

    def _configuration(self):
        _need(all(actual is pinned for actual, pinned in zip(
            (self._journal, self._guard_store, self._guard_head, self._baseline_store, self._baseline_head),
            self.__integrations)), "COMMITTED_ACCOUNT_INTEGRATIONS_CHANGED")

    def _still(self, generation, published):
        self._configuration()
        _need(self.__generation is published, "COMMITTED_ACCOUNT_GENERATION_CHANGED")
        _intact(generation)
        if generation is not published:
            _intact(published)

    def _events(self, transaction):
        self._configuration()
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

    def _states(self, generation):
        try:
            self._configuration()
            receipt = generation.receipt
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

    def _input_binding(self, generation):
        _intact(generation)
        package, receipt = generation.package, generation.receipt
        before, path = package["baseline_before"], package["path"]
        input_sha = _input_digest(generation.expected_guard, before, package["policy"],
            package["owner_before"], package["owner_after"], path, package["valuation_inputs"],
            package["account_capture"], package["coverage"], package["interval"])
        binding = {"input_sha256": input_sha,
            "owner_sha256": content_digest((package["owner_before"], package["owner_after"])),
            "control_head_sha256": generation.expected_control, "path_sha256": content_digest(path),
            "old_guard_sha256": generation.expected_guard, "new_guard_sha256": receipt.guard_head,
            "old_baseline_sha256": generation.expected_baseline, "new_baseline_sha256": receipt.baseline_head}
        _need(content_digest(tuple(sorted(binding.items()))) == receipt.transaction_id,
              "COMMITTED_ACCOUNT_RECEIPT_BINDING_MISMATCH")
        return binding

    def _baseline_binding(self, generation, baseline):
        package = generation.package
        before, path, interval = package["baseline_before"], package["path"], package["interval"]
        _need(before.state_digest == generation.expected_baseline
              and baseline.state_digest == generation.receipt.baseline_head
              and baseline.previous_state_digest == generation.expected_baseline
              and baseline.last_interval_digest == content_digest(interval)
              and baseline.sequence == before.sequence+1,
              "COMMITTED_ACCOUNT_PACKAGE_BINDING_MISMATCH")
        _need(interval.source_sha256 == content_digest(package["account_capture"].endpoint_accounts)
              and interval.coverage_sha256 == content_digest((path, package["coverage"]))
              and interval.previous_state_digest == before.state_digest
              and interval.start == path.start == before.asof
              and interval.end == path.end == baseline.asof
              and interval.account_scope == before.account_scope == baseline.account_scope == path.account_scope,
              "COMMITTED_ACCOUNT_ENDPOINT_BINDING_MISMATCH")

    def _binding(self, generation, guard, baseline):
        binding = self._input_binding(generation)
        self._baseline_binding(generation, baseline)
        _need(guard.previous_guard_sha256 == generation.expected_guard
              and guard.last_input_sha256 == binding["input_sha256"]
              and guard.last_path_sha256 == binding["path_sha256"],
              "COMMITTED_ACCOUNT_PACKAGE_BINDING_MISMATCH")
        package = generation.package
        claim = package["owner_after"]
        _need(guard.owner_head_sha256 == claim.owner_head_sha256
              and guard.code_sha256 == claim.code_sha256
              and guard.policy_sha256 == content_digest(package["policy"]),
              "COMMITTED_ACCOUNT_AUTHORITY_CLAIM_MISMATCH")
        return binding

    def _history(self, generation, events, guard_halted, binding, now, baseline):
        receipt = generation.receipt
        _need(events and now >= datetime.fromisoformat(events[-1]["utc"]),
              "COMMITTED_ACCOUNT_CLOCK_ROLLBACK")
        # Journal has verified row bytes, chain and retained anchor. Existing
        # lifecycle validation retains all order/kill/halt/risk semantics.
        _, _, halted, _ = _fold(events)
        state = classify_restart(events, guard_head=receipt.guard_head, baseline_head=receipt.baseline_head,
            expected_guard_head=generation.expected_guard, expected_baseline_head=generation.expected_baseline,
            expected_control_head=generation.expected_control)
        _need(state.status == CONSISTENT and state.transaction_id == receipt.transaction_id,
              "COMMITTED_ACCOUNT_COMPLETION_REQUIRED")
        prepares = [(i, row) for i, row in enumerate(events)
                    if row["kind"] == PREPARE and row["data"]["transaction_id"] == receipt.transaction_id]
        completes = [(i, row) for i, row in enumerate(events)
                     if row["kind"] == COMPLETE and row["data"]["transaction_id"] == receipt.transaction_id]
        _need(len(prepares) == len(completes) == 1, "COMMITTED_ACCOUNT_COMPLETION_REQUIRED")
        pi, prepare = prepares[0]; ci, completion = completes[0]
        _need(pi < ci and all(prepare["data"][name] == value for name, value in binding.items())
              and prepare["data"]["path_start"] == _utc(generation.package["path"].start)
              and prepare["data"]["path_end"] == _utc(generation.package["path"].end)
              and prepare["data"]["halt_required"] is guard_halted,
              "COMMITTED_ACCOUNT_PREPARE_BINDING_MISMATCH")
        prefix = [i for i, row in enumerate(events) if row["row_sha256"] == receipt.control_head]
        _need(len(prefix) == 1 and prefix[0] >= ci, "COMMITTED_ACCOUNT_RECEIPT_PREFIX_MISSING")
        receipt_halted = any(row["kind"] == "halt" for row in events[:prefix[0]+1])
        _need(receipt.permanently_halted is receipt_halted
              and (not guard_halted or any(row["kind"] == "halt" for row in events[:ci+1])),
              "COMMITTED_ACCOUNT_HALT_EFFECT_MISSING")
        policy_day = baseline.asof.astimezone(KST).date().isoformat()
        for index, row in enumerate(events):
            if row["kind"] != "risk_snapshot":
                continue
            data = row["data"]
            if index > ci:
                _need(not data["floor_relaxation_approved"]
                      and data["policy_digest"] == control_digest(generation.package["policy"]),
                      "COMMITTED_ACCOUNT_CONTROL_EPOCH_CHANGED")
            if data["day"] == policy_day:
                _need(Decimal(data["day_start_equity"]) == baseline.day_start_equity,
                      "COMMITTED_ACCOUNT_DAY_OPEN_CONFLICT")
        return completion["row_sha256"], ci, halted

    def _successor(self, previous, candidate, events, now):
        """Bind the old generation to the actual predecessor prefix, not old stores.

        The stores already hold the successor. Its actual baseline_before and
        the verified Journal prefix retain the previous interval's exact links.
        No reconstructed guard object or arbitrary verification boolean is used.
        """
        old, new = previous.package, candidate.package
        receipt = previous.receipt
        _need(candidate.expected_guard == receipt.guard_head
              and candidate.expected_baseline == receipt.baseline_head
              and candidate.receipt.transaction_id != receipt.transaction_id,
              "COMMITTED_ACCOUNT_DIRECT_SUCCESSOR_REQUIRED")
        binding = self._input_binding(previous)
        self._baseline_binding(previous, new["baseline_before"])
        indices = [i for i, row in enumerate(events)
                   if row["row_sha256"] == candidate.expected_control]
        _need(len(indices) == 1, "COMMITTED_ACCOUNT_PREDECESSOR_PREFIX_MISSING")
        prefix = events[:indices[0]+1]
        prepares = [row for row in prefix if row["kind"] == PREPARE
                    and row["data"]["transaction_id"] == receipt.transaction_id]
        _need(len(prepares) == 1, "COMMITTED_ACCOUNT_COMPLETION_REQUIRED")
        self._history(previous, prefix, prepares[0]["data"]["halt_required"], binding, now,
                      new["baseline_before"])
        _need(new["path"].start == old["path"].end
              and new["interval"].sequence == old["interval"].sequence+1
              and new["path"].account_scope == old["path"].account_scope
              and content_digest(new["policy"]) == content_digest(old["policy"])
              and _owner_terms(new["owner_before"]) == _owner_terms(old["owner_after"])
              and new["path"].stream_epoch == old["path"].stream_epoch
              and new["path"].first_sequence == old["path"].watermark_sequence,
              "COMMITTED_ACCOUNT_GENERATION_CONTINUITY_REQUIRED")

    def publish_committed(self, package, receipt, *, expected_guard_head,
                          expected_baseline_head, expected_control_head, now,
                          transaction) -> CommittedAccountProjection:
        """Publish only an actual completed direct successor under the caller's lock.

        This performs no durable mutation and issues no source/owner authority.
        An exact retry verifies any later receipt prefix but retains the original
        generation and receipt identity. Failure leaves that reference unchanged;
        moved actual heads still make an old-generation read refuse.
        """
        try:
            with localcontext() as numeric:
                numeric.prec = 512; numeric.traps[Inexact] = True
                previous = self.__generation
                _instant(now)
                events = self._events(transaction)
                self._still(previous, previous)
                candidate = _generation(package, receipt, expected_guard_head,
                                        expected_baseline_head, expected_control_head)
                retry = candidate.receipt.transaction_id == previous.receipt.transaction_id
                if retry:
                    _need(candidate.package_sha256 == previous.package_sha256
                          and candidate.receipt.guard_head == previous.receipt.guard_head
                          and candidate.receipt.baseline_head == previous.receipt.baseline_head
                          and candidate.expected_guard == previous.expected_guard
                          and candidate.expected_baseline == previous.expected_baseline
                          and candidate.expected_control == previous.expected_control,
                          "COMMITTED_ACCOUNT_RETRY_MISMATCH")
                else:
                    self._successor(previous, candidate, events, now)
                answer = self._read(now, transaction, candidate, previous)
                if retry:
                    # Validate the supplied replay prefix first, then return the
                    # original identity with the current conservative suffix fold.
                    return self._read(now, transaction, previous, previous)
                self._still(candidate, previous)
                object.__setattr__(self, "_CommittedAccountProvider__generation", candidate)
                return answer
        except CommittedAccountError:
            raise
        except (ValueError, RuntimeError, TypeError, AttributeError, KeyError, DecimalException,
                OverflowError, RecursionError):
            raise CommittedAccountError("COMMITTED_ACCOUNT_EVIDENCE_REFUSED") from None

    def inspect_committed(self, *, now: datetime,
                          transaction: Transaction) -> CommittedGenerationInspection:
        """Inspect an actual completed generation without projecting old accounts.

        The caller supplies its actual current time and active Journal transaction.
        Expired endpoint freshness is not converted into account authority: this
        path never calls current reconciliation, and always completes its own
        actual store/head/control rereads before returning original metadata.
        """
        try:
            with localcontext() as numeric:
                numeric.prec = 512; numeric.traps[Inexact] = True
                generation = self.__generation
                _instant(now)
                self._still(generation, generation)
                events = self._events(transaction)
                guard, baseline = self._states(generation)
                binding = self._binding(generation, guard, baseline)
                completion, _, _ = self._history(generation, events,
                    guard.permanently_halted, binding, now, baseline)
                _need(guard.recorded_at == generation.package["now"]
                      and guard.recorded_at <= now, "COMMITTED_ACCOUNT_CLOCK_ROLLBACK")
                _need(self._states(generation) == (guard, baseline),
                      "COMMITTED_ACCOUNT_STATE_CHANGED")
                self._still(generation, generation)
                _need(self._events(transaction) == events, "COMMITTED_ACCOUNT_CONTROL_CHANGED")
                receipt = generation.receipt
                answer = CommittedGenerationInspection(
                    transaction_id=receipt.transaction_id, guard_head=receipt.guard_head,
                    baseline_head=receipt.baseline_head, completion_head=completion,
                    receipt_control_head=receipt.control_head,
                    observed_control_head=events[-1]["row_sha256"],
                    package_sha256=generation.package_sha256,
                    input_sha256=binding["input_sha256"], asof=baseline.asof,
                    evaluated_at=guard.recorded_at)
                self._still(generation, generation)
                return answer
        except CommittedAccountError:
            raise
        except (ValueError, RuntimeError, TypeError, AttributeError, KeyError, DecimalException,
                OverflowError, RecursionError):
            raise CommittedAccountError("COMMITTED_ACCOUNT_EVIDENCE_REFUSED") from None

    def read(self, *, now: datetime, transaction: Transaction) -> CommittedAccountProjection:
        try:
            with localcontext() as numeric:
                numeric.prec = 512; numeric.traps[Inexact] = True
                generation = self.__generation
                return self._read(now, transaction, generation, generation)
        except CommittedAccountError:
            raise
        except (ValueError, RuntimeError, TypeError, AttributeError, KeyError, DecimalException,
                OverflowError, RecursionError):
            raise CommittedAccountError("COMMITTED_ACCOUNT_EVIDENCE_REFUSED") from None

    def _read(self, now, transaction, generation, published):
        _instant(now)
        self._still(generation, published)
        events = self._events(transaction)
        guard, baseline = self._states(generation)
        binding = self._binding(generation, guard, baseline)
        completion, complete_index, halted = self._history(generation, events, guard.permanently_halted, binding, now, baseline)
        _need(guard.recorded_at == generation.package["now"] and guard.recorded_at <= now,
              "COMMITTED_ACCOUNT_CLOCK_ROLLBACK")
        interval = generation.package["interval"]
        update = reconcile_committed_baseline(baseline, generation.package["account_capture"].endpoint_accounts,
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
            # Retain the currently effective validated controller floor, including
            # one recorded before this commit. Taking every historical maximum
            # would incorrectly undo an approved relaxation preceding the epoch.
            latest_control_floor = (None if data["effective_floor"] is None
                                    else Decimal(data["effective_floor"]))
            high = max(high, Decimal(data["high_watermark"]))
            if data["day"] == policy_day.isoformat():
                stopped = stopped or data["daily_stopped"]
        if latest_control_floor is not None:
            floor = max(floor, latest_control_floor)
        risk = replace(observation.risk, prior_high_watermark=high, approved_effective_floor=floor,
            observed_daily_loss=max(observation.risk.observed_daily_loss, guard.observed_daily_loss),
            halted=observation.risk.halted or guard.permanently_halted or halted)
        # Do not silently re-reconcile or advance after any changed dependency.
        _need(self._states(generation) == (guard, baseline), "COMMITTED_ACCOUNT_STATE_CHANGED")
        self._still(generation, published)
        _need(self._events(transaction) == events, "COMMITTED_ACCOUNT_CONTROL_CHANGED")
        receipt = generation.receipt
        answer = CommittedAccountProjection(observation=replace(observation, risk=risk), policy_day=policy_day,
            daily_stopped=stopped, transaction_id=receipt.transaction_id, guard_head=receipt.guard_head,
            baseline_head=receipt.baseline_head, completion_head=completion,
            receipt_control_head=receipt.control_head, observed_control_head=events[-1]["row_sha256"],
            owner_claim=deepcopy(generation.package["owner_after"]), policy_sha256=guard.policy_sha256)
        self._still(generation, published)
        return answer
