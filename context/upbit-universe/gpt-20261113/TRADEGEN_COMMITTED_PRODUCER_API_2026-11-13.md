# Committed producer — narrow rehearsal implementation card

2026-11-13. Proposed implementation tree `/workspace/tradegen-committed-producer-1113`, branch `gpt/committed-producer-link`, actual main `5bb4d7d8bdf65fbd6a3048530947b72b563406a7` (PR58/59 merged). Source inspection began on startup `de547f10375e1b30e2757c8c32c057c32a749138`; the functions below are unchanged on the new base. This card is a design, not an implementation or test result. No runtime, test, HEAD or handoff changes were made for it.

## 1. Bounded result and existing seams

Implement one fixed-symbol **Upbit KRW spot rehearsal** producer: genuine collector parsing and retained synthetic market path → exact archive/readback → actual local guard commit → completion readback → initial actual startup reconciliation or same-provider successor publication → actual fixed history/Runner. Source completeness remains an explicitly supplied rehearsal claim. Do not enable controlled mode, universe rotation, live orders, recovery-gap repair, new owner epochs or automatic liquidation.

Reuse these actual paths:

- `guard_capture_archive.collect_archive_guard_capture` (line251): full capture/previous archive and backup, original-time replay; audit failure retains the archive.
- `guard_generation_archive.retain_guard_input/read_guard_input/read_guard_completion`: exact ten-key package; original evaluation time; explicit completion→input→capture graph reads.
- `CommittedStartup.commit_input`: actual `commit_continuous_guard(expected_evaluated_at=record.evaluated_at)` followed by completion retention. Its guard transaction is not nested inside publication.
- `CommittedAccountProvider.publish_committed`: current full graph/head/prefix/direct-successor checks under the caller's actual strict Journal transaction. No durable advance occurs there.
- `CommittedStartup.reconcile` (line431): exact broker orders/fills, actual local state/status work, final current owner/time and saved completion-prefix checks. Its count is not readiness.
- Controller's paired/account-only reads, exact generation restriction and final-clock checks; Runner's existing committed paths. No new account permit or authority registry.

A fundamental prerequisite is **not** satisfied by those existing helpers: pure guard requires `path.start == previous.baseline.asof` and an actual owner observation no later than that start. Calling the owner loader now with an old timestamp is invalid. A public retained `OwnerContextClaim`, a reconstructed dataclass or a matching hash is not proof that this new producer actually observed the owner before the interval.

## 2. New producer API and fixed bindings

Own new `execution_launch/committed_producer.py`. Exact public API:

```python
class CommittedProducerError(ValueError): ...

class CommittedAccountProducer:
    def __init__(self, *, archive_store, journal, guard_store, guard_head,
                 baseline_store, baseline_head, profile, adapters,
                 isolated_state_root, clock, candidate_source, collector_source,
                 capture_inputs_source, session_id=None, limits=GENERATION_DEFAULT_LIMITS,
                 capture_limits=CAPTURE_DEFAULT_LIMITS): ...

    def observe_opening(self, *, risk_baseline) -> ProducerOpeningObservation: ...

    def collect_and_publish(self, *, anchor, coverage,
                            trade_fees=()) -> CommittedProducerUnit: ...

    def status(self) -> CommittedProducerStatus: ...
```

Constructor checks exact actual `BundleStore`, `Journal(requires_existing=True)`, `GuardCheckpointStore`, `CheckpointStore`, `LaunchProfile`, `ContinuousUpbitCandidateSource`; explicit retained head objects with their existing read/CAS contract; a single actual `DryRunAdapter` under key `upbit`; one absolute isolated state root identical to actual control/checkpoint roots; fixed non-universe Upbit/spot/KRW profile; explicit clock, fixed callable `capture_inputs_source` and collector with matching account scope. Collector may be the existing reviewed source or a test-only synthetic GET source: class identity must never be described as exchange/source authentication. Current `state_root()` and Runner's existing rehearsal root boundary remain mandatory before effects.

Pin all actual dependencies, account scope, profile economic contract, risk policy (using each existing correct digest codec), source path/verifier and capture-input supplier callable identities, archive root and constructor `session_id` (`None` or a bounded nonempty existing session identifier). Snapshot typed anchor/coverage/fees before callbacks through existing bounded admission. Do not accept callback-supplied Context, OwnerContextClaim, provider, prepared session, projection, commit receipt or `ready=True` as substitutes. Same-contract issued terms renewal may update Coordinator's actual rules through its existing path; it does not replace the producer's economic contract/policy.

Constructor and `observe_opening` do not seed, initialize, adopt, truncate or repair any journal/head/checkpoint. Producer has one nonblocking local unit lock and bounded state: one opening observation, at most two rolling owner observations, one current record and one unfinished unit. There is no timer thread, retry worker or generic plugin registry. Public record objects are descriptive, frozen/keyword-only, with private account/claim values `repr=False`:

```python
class ProducerOpeningObservation:
    observed_at: datetime
    completed_at: datetime
    account_asof: datetime
    manifest_sha256: str
    owner_claim: OwnerContextClaim       # existing inert claim; repr=False

class CommittedProducerUnit:
    capture_archive_digest: str
    input_archive_digest: str
    completion_archive_digest: str
    transaction_id: str
    account: AccountEvidence            # exact original endpoint; repr=False
    observation: AccountObservation     # actual final Controller read; repr=False
    reconciliation: StartupResult      # actual call result, never accepted as input
    completed_at: datetime

class CommittedProducerStatus:
    phase: str
    reason: str
    capture_archive_digest: str | None
    input_archive_digest: str | None
    completion_archive_digest: str | None
    transaction_id: str | None
    completed_at: datetime | None
```

The opening/unit/status records expose constant-false `execution_ready` and `source_authenticated` properties. Status is not durable recovery metadata and no result grants order authority. Phase is closed: `NEW`, `OPENING_OBSERVED`, `CAPTURE_ARCHIVED`, `INPUT_RETAINED`, `COMMIT_UNCONFIRMED`, `COMPLETION_RETAINED`, `PUBLISHED`, `RECONCILED`, `BLOCKED`. IDs are actual returned-and-reread identifiers, never fabricated before their stage.

### Exact data-only capture supplier and scheduler call

```python
@dataclass(frozen=True, kw_only=True)
class ProducerCaptureInputs:
    anchor: OpeningAnchor                 # repr=False
    coverage: CoverageEvidence            # repr=False
    trade_fees: tuple[TradeFeeEvidence, ...] = ()  # repr=False

capture_inputs_source(*, previous: BaselineState | None,
                      now: datetime) -> ProducerCaptureInputs
```

The supplier is trusted composition code providing **external raw evidence data**, not a Context, source-coverage issuer or owner approval. No JSON-deserialized callbacks, dynamic imports, returned callback, verified-result flag or implicit defaults. Pin its callable identity once in the producer constructor. It receives `previous=None` for `observe_opening`, or a bounded detached copy of the actual currently loaded predecessor baseline for a rolling collection, plus an actual just-observed clock value. Neither callback argument is authority or an editable reference to internal state.

`observe_opening(risk_baseline=...)` calls that supplier with `previous=None` before its actual collector. Coordinator `_prefetch` calls the **no-argument** private `producer._collect_current()`. This method acquires the producer unit lock, reads the actual predecessor/heads and current clock, calls the fixed supplier, requires the exact `ProducerCaptureInputs` type and exact declared fields, and immediately admits/detaches its three fields with the existing `guard_capture_material._snapshot_inputs`. Both paths recheck actual configuration, supplier/source identities and the visible completion clock after the callback. Rolling collection additionally rechecks its original actual predecessor/head binding before collection; a supplier cannot replace the generation or move the data source and still continue.

The private `_collect_current()` and public explicit `collect_and_publish(anchor=..., coverage=..., trade_fees=...)` call the same private locked collection core after their own bounded admission. They do not invoke one another under the nonreentrant lock, load a different predecessor silently, or call the supplier twice. The explicit public method is useful for existing standalone tools/tests; the scheduler uses only `_collect_current()`. Bad/mutating supplier output refuses before collector/guard writes and never becomes a fabricated approval. No additional source file or storage engine is required.

### One-time runtime binding

To retain Coordinator's existing actual prepared-session lookup without mutating a Controller after construction, add one private producer method `_bind_startup(*, session_provider)`. Coordinator invokes it once with its existing `_session_for` bound method. It constructs the actual `CommittedStartup` from the pinned dependencies/clock and that callback. Rebinding is refused. It creates no runtime account/provider and performs no setup. Standalone tests use a fixed real-code lookup returning the actual PreparedSession or `None`; no verifier-success callback is introduced.

A second private method `_runtime_components()` returns the producer-owned actual startup provider/Controller/Journal only after first actual reconciliation has constructed them. Coordinator calls this method itself, verifies exact identities and its own profile/root/adapter/clock bindings, and creates its launch Runner once. It does not accept a caller-supplied tuple. The startup quote-disabled Runner and its initial binding remain unchanged; the launch Runner is a different consumer of the **same** actual provider/Controller.

## 3. Actual owner observation lifecycle

### Initial operator boundary

`observe_opening` obtains detached setup inputs from the pinned supplier as above, then must perform actual `collect_upbit(collector_source, ..., risk_baseline=...)` and actual `build_observation(collection.bundle, now=real_clock())`. The supplied risk baseline/anchor/coverage are the existing explicit setup inputs, not newly approved by this API. Use the resulting scope and positions in actual `owner.load_context(real_clock(), observation.positions, session_id=constructor_session_id)`. Do not use `_REVIEW_POSITIONS`, a synthetic cash-only Positions object, a caller Context, or a historical `now` parameter.

Validate exact sealed Context and its `context_hash`, actual owner OK/head/fingerprint, current signed code, current KST date and finite effective signed floor/daily limit under the existing Controller conventions. Retain actual original loader-start time and a fresh completion clock after its heavy work; completion cannot precede any accepted clock/receipt or exceed the original account/owner freshness. Retain the actual source manifest and exact parsed positions privately. Map `source_sha256` of the existing OwnerContextClaim to the actual context hash, not to an invented approval or a market-source proof. Require actual fingerprint/head/code/effective terms continuity across later observations.

Return a detached opening description for the **existing explicit operator setup**, and keep the original private provenance inside this producer. Operator/test setup may subsequently build the reviewed baseline and guard anchor using existing helpers and explicitly provision the existing stores/heads. Producer never does this. Its first interval admission requires that actual setup's baseline/guard/policy/scope/owner terms match, and:

```text
opening.observed_at <= opening.completed_at <= initial_baseline.asof
0 <= initial_baseline.asof - opening.observed_at <= 30 seconds
```

There is no replacement or lowering of an existing protected baseline. Missing runtime files are still refused. Calling `observe_opening` after an old baseline's asof cannot make that baseline usable. A new process cannot import a public opening description or archived claim into private preinterval provenance.

### Each collected interval

1. Read actual current control prefix and baseline/guard heads/state. For successors verify the current provider generation as well. Validate the **previously retained real** before-observation against the current baseline asof, signed epoch, session and original freshness. Never manufacture it at collection end.
2. Before starting the collector, make another actual owner observation using the fresh current committed account's positions (initial interval: the still-fresh actual opening collection positions). Retain it privately as a candidate **for the next interval**, not retroactively for the current path. Its completion must be no later than the endpoint eventually chosen for that next path start. When a cutoff clips the endpoint before this observation, it is unusable and must not be backdated.
3. Execute the existing full collect/archive/replay path. After successful retained coverage/endpoint replay, derive endpoint positions through existing pure `advance_account_baseline(previous, material.interval, material.account_capture.endpoint_accounts, now=actual_now).observation`; this is already the mathematical bridge used by preview/replay and does not write, seed or CAS. Its provisional risk view is used only to obtain validated account positions, never as a committed risk/guard state.
4. Perform actual owner load on those endpoint positions after coverage/watermark, with the same session and real clock. Retain fresh completion and validate actual code/key/head/effective limits. Build the after claim from this actual observation. Set package `now` to the accepted completion time; retain the capture's earlier `staged.observed_at` independently. It is not overwritten.
5. The actual guard must still enforce all original inequalities, including before<=path.start, watermark<=coverage<=after<=package.now, endpoint freshness, unchanged owner terms and exact stream continuity. Extra private completion/identity checks are restrictive only.

Ordinary owner loads may persist existing compliance snapshots/revocation anchors; this is not claimed to be a filesystem-read-only workflow. No new owner signing, event kind or authority issuer is added. A later actual owner change is rechecked by Controller after publication. Existing nonzero daily-limit and halt retention constraints remain; no special case weakens them.

**Restart boundary:** PR58 startup can read/reconcile genuine retained generations at current time. That does not reconstruct a lost preinterval observation lifecycle. Fresh processes without that actual prior observation must refuse rolling production, even if public archived claims match. Durable recovery of this lifecycle is outside this unit; do not use process-restoration tests to claim it exists. Long gaps, stream reset and session/owner epoch changes remain explicit refusals.

## 4. Exact unit transaction and publication order

`collect_and_publish` is serialized; it requires the bound startup and an original real before observation. It does not take a caller `now`, package, expected heads or receipt.

1. Retain actual control-prefix/guard/baseline predecessor heads under an actual existing Journal transaction and check their correspondence; then close it. Source collection/archive never runs under that transaction.
2. Call `collect_archive_guard_capture` with detached original baseline/anchor/coverage/fees and the explicit clock. Record the actual archive ID as soon as available. Semantic audit failure preserves RAW and stops before any input/guard commit. Archive/readback failure is not an intact-archive claim.
3. Build the exact existing ten-key package from replay material plus actual before/after owner observations and accepted original evaluation time. Use actual `retain_guard_input` and its backup/readback. Recheck current owner epoch, original time bounds and configuration after slow retention before committing; this does not refresh the package.
4. Call actual `CommittedStartup.commit_input(input_archive_digest)` outside any Journal transaction. Keep its existing `expected_evaluated_at` check; `input_sha256` excludes time, so input hash equality alone is insufficient. Actual commit is the sole durable baseline/guard transition. All plan/replay pure recalculation is allowed, but `ContinuousAccountProvider.__call__`, its durable advance, extra store commit/CAS and reseeding are absent.
5. Re-read `read_guard_completion`, including the full input/capture graph and backups. Preserve receipt tail, actual COMPLETE and recorded observed tail as distinct values. In a **new** actual strict Journal transaction, validate actual completion-prefix membership through existing `CommittedStartup._completion_binding` and actual candidate inspection before publishing. An unrelated/replaced suffix is not ignored.
6. First committed interval: actual `CommittedStartup.reconcile` creates its provider/Controller/quote-disabled Runner exactly once; readiness requires its actual current result. There is no prior provider to replace. Later intervals: call the existing `publish_committed` on this same provider inside the separate real Journal transaction, with the actual current clock and original package. Never try to read the obsolete predecessor against already moved stores first. Close publication before Controller/reconciliation.
7. Reuse the actual reconciliation core below on that exact current runtime and retained completion. Obtain an actual final Controller account-only read on the same session, retain its completion time, and require its transaction ID/head to match the current observed unit. No extra entry-risk gate is added to this account-only step.
8. Return only a detached descriptive unit after configuration/currentness checks. Coordinator publishes the original endpoint/actual account observation and supplied current quote only at this point; history/tick use later actual time and existing slot/book windows. The account/owner/receipt times are never restamped.

A successful commit followed by failed completion archive/publication is not rollback: old provider reference may remain but moved heads make old reads refuse. Preserve pending/confirmed records; report the reached phase and stop further collection/publication in that instance until explicit existing startup inspection/recovery. No catch-all re-send, automatic new input, head adoption or new retry engine. An actual durable row with lost response remains real on fresh replay; failed invocation does not claim confirmation. New producer does not reconstruct private owner provenance from an existing recovery record.

## 5. Reuse startup reconciliation without rebinding it

Own a small extraction in `committed_startup.py`:

```python
# Public default behavior remains identical; session is a restrictive actual context selector.
CommittedStartup.reconcile(input_archive_digest, completion_archive_digest,
                           *, session_id=None) -> StartupResult

# Private, actual bound runtime only; no evaluator/provider/authority parameters.
CommittedStartup._reconcile_runtime(inspection, retained, completed,
                                    *, session_id=None) -> StartupResult
```

Move the existing reconciliation body after `_runtime` into the private method. Public reconcile retains its original lock, full `_inspect`, freshness refusal and `_runtime` one-binding admission before calling it. Private method revalidates the real `_runtime_pins`, actual `_inspect`/retained records, actual provider's current transaction/package/receipt/completion and dependency/head bytes itself. It never trusts the passed inspection as a proof; caller objects alone cannot skip actual reads. `session_id` is passed to **all** existing initial/final account-only owner reads; known-order cancel/reconcile retains each actual recorded order's own session.

For successor reuse, producer performs actual `_inspect(current_input,current_completion)`, then calls the private method on the same startup runtime after actual provider publication. The method does not call `_runtime`, rewrite `_binding`, replace provider/controller/runner, or open the quote path. Public reconcile on a different initial binding must still refuse as before.

Preserve the full original admission/assessment: maximum1024 orders, conflicting RESERVED broker evidence, foreign/unknown open orders, exact quantity/price/status/cumulative fee/cancelable evidence, actual recent reconciled rows, no blind local cancellation, no stale broker lookup, original final archive/current owner/physical-prefix/time checks. Result count alone is never success. `RECONCILED_OPEN` means exact known remaining orders, not flatness; strategy's existing outstanding-order/flat rules continue to block inappropriate entry. A new fill absent from the retained endpoint requires another genuine generation.

## 6. Coordinator's explicit branch

Add `committed_producer=None` to `Coordinator.__init__`. Permit `account_source=None` only in this exact committed branch; require `account_prefetch is None`. Reject simultaneous legacy account integrations. `trusted_head` must be the producer's actual baseline head. Existing omitted producer path keeps its callable admission, constructors, clock and side effects exactly unchanged.

Before any effect reject controlled mode, universe, non-DryRun adapters, different roots/policy/clock/head/source bindings. Initialize common Coordinator fields before `_bind_startup(session_provider=self._session_for)`; defer `_provider/_controller/_runner` adoption until first actual producer unit/reconciliation. `_runtime_components()` identities and existing Runner rehearsal checks must pass. Readiness cannot be supplied in constructor.

- Committed `_prefetch` invokes actual `producer._collect_current()` (no arguments), which obtains its admitted supplier inputs and executes producer collection/commit/publication, and retains only this unit. `_publish` consumes that exact internally retained unit, checks actual current time/head/transaction and places only the quote in the board. It performs no legacy `_provider(now)`, advancing frame or extra commit. No caller `BaselineFrame` becomes committed evidence.
- First startup/bootstrap monitor uses the first committed unit and actual reconciliation; subsequent monitor/gap units call the same private reconciliation core. `_ready` is true only after actual `RECONCILED` or `RECONCILED_OPEN` with current unresolved/external lists empty and final actual bindings intact. Source/commit/owner/archive failures clear readiness, never imply a sell.
- `_slot` keeps actual prefetched book sample, exact original account observation, actual history record, synchronous E event, fresh-clock Runner ordering. Recheck clock after producer work and before history/tick. Expired slot or quote skips execution; do not relabel old raw data or synthesize missing slots. Preserve existing sticky missed-window handling.
- Terms refresh uses the actual retained endpoint account from the current producer unit, without `_latest_frame`. Disarm uses Controller's actual current provider/journal-only fallback and does not republish or advance an old frame. `stop/close` before first runtime creates no account/provider/kill success claim.
- Explicit exit uses existing Runner account-only observation and existing sell reserve/dispatch gates, not monitor `_ready`, new risk snapshot/equality or research acceptance. It may require a fresh actual producer unit; failure to obtain one preserves current holdings and existing independent Controller actions. Explicit cancel/known-order status retain existing current-source behavior and never trigger entry or market liquidation. No post-E new management authority is introduced.
- `prepare` continues to use actual paired account freshness and the existing actual PreparedSession lookup. Signed arm/owner epoch changes are not silently incorporated into the running producer; the existing checks may refuse. This unit's acceptance does not claim automatic BUY or full strategy SELL readiness.

## 7. Errors, bounds and acceptance

New producer diagnostics are fixed `COMMITTED_PRODUCER_` codes: `INPUT_INVALID`, `REHEARSAL_REQUIRED`, `DEPENDENCY_CHANGED`, `BUSY`, `OPENING_REQUIRED`, `OWNER_REFUSED`, `OWNER_INTERVAL_NOT_BRACKETED`, `CLOCK_INVALID`, `CLOCK_ROLLBACK`, `STALE`, `CAPTURE_REFUSED`, `INPUT_ARCHIVE_REFUSED`, `COMMIT_UNCONFIRMED`, `COMPLETION_REFUSED`, `PUBLICATION_REFUSED`, `RECONCILIATION_REQUIRED`. Status may preserve a reviewed existing fixed domain diagnostic by an exact allowlist; do not echo arbitrary exception strings/paths/amounts. Existing limits stay unchanged: full capture64MiB/2000 receipts and existing typed bounds, metadata64KiB, startup1024 orders. No new file engine or writer exception.

Required tests, with actual temporary signed owner logs and actual existing stores/heads/committer/Controller/DryRun. Market GETs/path/coverage remain explicitly synthetic and no successful authority verifier is patched:

1. Actual opening GET parser→actual positions→actual owner load before explicit operator baseline/guard setup; first real interval then second genuine rolling interval. Same provider/Controller identity after initial creation; each durable guard/baseline transition exactly once, publication/history/tick cause zero additional transitions. Existing legacy Coordinator remains unchanged.
2. Missing preinterval lifecycle; post-start owner read; completion after boundary; no backdated clock arguments; forged/copied public opening/Context/claim; source-scope mismatch; old code/key/head, same-head scheduled limits/session mismatch and retained halt. Each refuses without owner/source authority promotion.
3. Preserve actual before/after clocks, rollback observed between heavy stages, age exactly30s/+1µs, 22:00 and KST rollover, original preview vs package evaluation time. Stage delays cannot make old data fresh. Owner change after capture/retention and before/after publication blocks downstream action.
4. Actual raw semantic failure retains RAW; input retention failure commits0; PREPARE/cross-store/COMPLETE/completion-archive/publication failures retain exact durable evidence and do not roll back/reseed. Both confirmed durable response loss and unconfirmed/torn state are distinguished. Prior account cannot be reused as current after heads move.
5. Actual startup/repeated monitor reconciliation: exact known open and partial fill/fee, foreign order, never-sent RESERVED conflicting with broker evidence, UNKNOWN/DISPATCHING, late fill absent from endpoint, stale startup and missing strict Journal files. Only actual matched states produce ready; no count/constructed StartupResult shortcut.
6. Actual temporary reviewed research, signed source/implementation documents, issued fixed/carry factory, actual LiveHistory/head and new committed producer reach warmup HOLD. Preserve E-only no-sale, current synchronous management request event and failure behavior; create count0. Separately verify one genuine isolated reducing action under existing sell gates; do not call this automatic strategy profitability or live execution.
7. Publish successor between paired read and reserve/dispatch: existing expected transaction ID refuses old decision; RESERVED/uncertain durable states stay. Stop/close/disarm/quote/terms failures never fabricate sale, readiness or signed disarm. Initial runtime absence has correct status.
8. Storage/owner/config mutation after early success is caught by actual final reads. Capture-input supplier mutation, wrong return type/extra fields, callback rollback, generation change during callback and attempted internal-object mutation refuse before collection/commit; the no-argument scheduler path calls the supplier once on its detached actual predecessor. All new source dependencies appear in app and independent signer factory closures. Guard negative controls reject alternate writer/network/key/source/clock bypasses, not just test names.

## 8. Parallel ownership and remaining limits

| Owner slice | Source files | New acceptance files |
| --- | --- | --- |
| Producer + actual owner lifecycle | new `execution_launch/committed_producer.py` | `tests/launch_committed_producer.py` |
| Actual startup core reuse | `execution_launch/committed_startup.py` only | `tests/launch_committed_producer_reconcile.py`; necessary legacy startup assertions |
| Scheduler branch | `execution_launch/coordinator.py`, preserve CRLF | `tests/launch_coordinator_committed.py` |
| Independent vertical | no production edits | `tests/launch_committed_producer_integration.py` |
| Root closure/guards/registry | actual explicit source lists in driver/independent signer; precise guards | existing closure/guard negative controls |

Freeze shared source before actual signed fixtures; root owns runtime, merges and measured reports. Do not mutate the old startup/recovered/passkey validation trees. Owner lifecycle and startup core can be implemented in parallel against the fixed signatures; Coordinator waits for producer/runtime methods to land. No test count or timing is promised before actual discovery/execution.

This is missing **rehearsal orchestration**, plus a genuine initial pre-observation requirement. It is not a production completeness solution: hashes/GET fencing/archived receipts cannot prove unseen marks, fills, transfers or gaps absent. `ContinuousUpbitCandidateSource.__call__` continues to refuse live-risk integration; controlled Runner and Coordinator remain closed. Persistent restoration of actual owner-preinterval lifecycle, post-gap recovery, new owner epoch handover, full scheduler production source, native Windows, real account/transport and iPhone approval are not proved by this unit.

법률, 세무, 투자 조언이 아니며 면허를 가진 자문가가 아니다
