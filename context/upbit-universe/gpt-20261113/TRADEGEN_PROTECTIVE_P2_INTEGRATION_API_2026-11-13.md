# P2-I1: committed account projection API

2026-11-13. Implementation base: `f09b7365c9f2b025ec507c33a234c88cf7654d09`, new worktree `/workspace/tradegen-guard-projection-1113`. This card narrows the preceding `TRADEGEN_PROTECTIVE_P2_INTEGRATION_NEXT_STEP_2026-11-13.md`. It is an implementation contract, not a completed runtime test or an operating authorization.

## Smallest implementation now

Implement the read-only reconciliation of an already committed guard/baseline pair. The holder consumes the caller's **actual, currently open Journal Transaction** and reads the actual retained heads and checkpoint stores. It performs no baseline reduction, commit, CAS, initialization, journal acquisition, capture, publication, owner authorization, arm or order. The result remains `execution_ready=False`.

The existing Controller, Coordinator rehearsal restriction, and `ContinuousUpbitCandidateSource.__call__` refusal stay unchanged. In particular, the new holder has no `__call__`: passing it as the old Controller account provider cannot silently discard its daily-stop or provenance metadata. This useful first unit proves store-to-account reconciliation and the future non-nested read seam without pretending that source coverage or live authority exists.

## Fixed APIs and ownership

| Owner | Files | Contract |
|---|---|---|
| protective_hold_design | `execution_accounts/baseline_bridge.py`, `tests/accounts_committed_baseline.py` | New pure reconciliation helper; existing provider behavior unchanged |
| pr4e_runner | NEW `execution_launch/committed_account.py` | Read-only committed projection, actual transaction and durable binding checks |
| revision_review | NEW `tests/launch_committed_account.py` | Real temporary stores/heads/journal with synthetic source/owner fixtures; independent boundary tests |
| root | Test registration, guards, integration, final validation, commits | Review actual source dependency changes; no broad guard exemption |
| pr4e_coordinator | Separate I2 design only | Future Controller consumer and publication order; no I1 production source edits |

```python
def reconcile_committed_baseline(
    state: BaselineState, accounts: tuple[AccountEvidence, ...], *,
    now: datetime, source_sha256: str, interval_start: datetime | None = None,
) -> BaselineUpdate: ...

class CommittedAccountProvider:
    def __init__(self, *, package: dict, receipt: GuardCommitReceipt,
                 expected_guard_head: str, expected_baseline_head: str,
                 expected_control_head: str, journal: Journal,
                 guard_store: GuardCheckpointStore, guard_head,
                 baseline_store: CheckpointStore, baseline_head): ...
    def read(self, *, now: datetime,
             transaction: Transaction) -> CommittedAccountProjection: ...

@dataclass(frozen=True, kw_only=True)
class CommittedAccountProjection:
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
    def execution_ready(self): return False
```

`CommittedAccountError(ValueError)` uses fixed codes only. The helper retains the established 512-digit exact decimal context and `_reconcile` rules, validates the existing state's digest and freshness, and does not call initialize/advance. Its supplied endpoint hash is **not independent authority**: the bridge must obtain it from the original committed package's `interval.source_sha256`, not calculate a self-approving replacement hash from changed accounts.

`owner_claim` is an exact descriptive copy of the original untrusted `package.owner_after`. Together with `policy_sha256`, it permits a future consumer to compare actual current code approval and effective floor/daily limits rather than checking owner head alone. It is never an authenticated current-owner observation.

The holder snapshots the exact package structure and binds its contents at construction and each read. The receipt and returned dataclass are descriptions, not issuers or capabilities. Exact actual store/Journal types and existing head adapter contracts remain explicit. Do not turn arbitrary `OwnerContextClaim`, `VerifiedCoverage`, `AccountCaptureInputs` or the returned projection into live authorization.

## Required read sequence and bindings

1. Require exact active `Transaction` belonging to the holder's exact Journal. Read `.events`; the existing thread-local identity check must reject forged, closed, other-journal and cross-thread transactions. Do not call Journal.snapshot/transaction and do not acquire a publication lock that a committing thread may hold while waiting for Journal.
2. Read both retained heads, require the receipt's exact successor pair, and load both checkpoint stores under those heads. The guard's embedded baseline must exactly equal the separately loaded baseline. Reread these dependencies before returning; a replacement, advancement or rollback during the read is a refusal. No latest-file discovery or automatic head adoption.
3. Validate the actual current event prefix and locate the receipt transaction's PREPARE and COMPLETE. Use the predecessor triple supplied at construction, the exact commit binding and the existing restart classifier. Refuse orphan/duplicate/missing completion, open later PREPARE, interrupted or divergent stores, and a missing required halt. Preserve existing whole-journal lifecycle validation.
4. Bind the original package to stored `last_input_sha256`, `last_path_sha256`, `last_interval_digest`, previous baseline/guard digests and PREPARE fields. Recompute the existing `_input_digest` formula, not the baseline reducer. Bind the original `account_capture` (manifest, captured and endpoint accounts, first receipt), interval source digest, owner before/after claim hash, path times and policy. These checks prove correspondence to the durable local commit, **not that the original claims were authentic**.
5. Derive `completion_head` from the matched COMPLETE row. `receipt.control_head` is an observed prefix head at or after that completion, **not necessarily the completion itself**: an idempotent commit retry can return a later risk_snapshot/kill suffix head. Require that receipt prefix to exist in the current verified history after completion. Do not require `current_head == receipt.control_head`.
6. Reconcile exact `account_capture.endpoint_accounts` against the existing loaded baseline using `interval.source_sha256` and `interval.start`. Retain original state.asof, sequence, digest, day opening and realized/FIFO/recovery-checkpoint values. A changed component with equal equity is still a mismatch. Preserve 30-second, Seoul-day and recovery-cutoff checks; never restamp evidence.
7. Project guard high/floor/daily-loss/permanent-halt conservatively into the observation. Keep `daily_stopped` separate, bound to the baseline's current Seoul `policy_day`. A stop is not a permanent halt and must not be encoded by fabricated losses. Fold legitimate later control risk snapshots/halt without clearing guard values. Same-day opening-equity conflict or an unsupported post-commit approved floor-relaxation/epoch change is a refusal, not a max() reconciliation. Old-day stop events remain history without becoming a new-day stop.
8. Verify the actual transaction remains active with the same event prefix and the actual heads/stores/package remain unchanged. Return the non-operational projection. Kill/order/reconcile suffixes remain current control history; this result does not assert fresh account/order reconciliation after them and cannot authorize entry or reducing execution.

## Following I2 patch, not included in I1

`Controller.observe` and `_authorize` open Journal before `_account`. Calling `commit_continuous_guard` from that provider would nest Journal and fail. Reusing `ContinuousAccountProvider` after guard commit would reduce/commit the interval a second time. The future Coordinator therefore collects and authenticates outside Journal, commits outside Controller, closes the commit transaction, and only then publishes a new holder under a short publication lock. It never holds publication lock while requesting Journal.

Controller's future narrow consumer must receive the actual tx, call this read seam, and carry `(observation, guard control metadata)` explicitly to `_snapshot_risk`; no hidden mutable cache. Existing callables return `(observation, None)` through that private seam. Same-day stop is ORed into the current decision and persisted at the current receipt time. Existing high/floor, owner signed limits, local halt/kill, pending guard, order uncertainty, reconciliation, capacities, session, permits and sell-specific checks remain effective.

That integration also needs an actual owner/code/effective-limit observation, including a same-head scheduled limit change at midnight. I1 has no such issuer. Current guard epoch transitions and approved D12 relaxation cannot be silently adopted by a max() projection. Preserve original capture receipts and pre/post authenticated owner observations through staged candidates; current `StagedContinuousCandidate` retains only preview/digests and cannot invent the omitted source evidence. No production complete-path Upbit verifier currently exists.

P2 management state writes close before Controller operations. Post-E monitor/reduce/cancel authority and a real history/driver revision for the extended period remain separate: the existing driver/history window rejects slots after E. Deadline, restart and storage failure remain non-sale causes. No change to risk policy, GTC behavior, floor, halt or market scope is authorized by I1.

## Meaningful acceptance tests

- Real commit → repeated reads leave baseline digest/sequence/asof, both stores/heads and journal unchanged. Patch advance/initialize/commit/CAS/snapshot/new transaction to fail during the read.
- Exact active transaction succeeds; fake events, constructed/closed/foreign transaction and nested acquisition fail. No live source/owner/code calls are made.
- Correct original package succeeds; changed capture/endpoint component, interval source, owner claim, path/policy, predecessor, transaction or receipt head fails, including equal-equity substitutions.
- Normal risk_snapshot/kill suffix and an idempotent receipt naming that suffix are accepted as local history; missing/future/rolled-back receipt prefix, orphan/duplicate COMPLETE and open later PREPARE refuse.
- Peak→trough→recovered endpoint retains guard high/floor/loss/halt. Same-day stop persists separately; midnight does not copy an old-day stop into the new day. Same-day denominator conflict and later D12 epoch change refuse.
- Store/head changes during final reconciliation refuse; no cached old projection is returned with a fresh timestamp. Freshness/day/cutoff violations refuse without mutations.
- Result is always non-operational; existing continuous source and Coordinator controlled-mode refusals remain. Fixture coverage and invented owner claims are clearly labeled as such.

This card was prepared from source inspection. Runtime results and the eventual source freeze belong to the implementation/verification record; no tests are claimed by this document.
