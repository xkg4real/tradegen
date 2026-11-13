# P2 I3a — retained collection and guard material API

2026-11-13. Tree `tradegen-capture-material-1113`, base `ed1b456`. Implementation contract, not an operating approval. No Controller/Runner/Coordinator, head/store, source-closure or registry edits by the implementation owner. Existing live refusals remain.

Owners: pr4e_coordinator owns `execution_launch/account_interval.py` (CRLF retained) and new pure `execution_launch/guard_capture_material.py`; pr4e_owner owns new `tests/launch_guard_capture_material.py`; revision_review performs independent read-only review. Root owns legacy test expectation updates if needed, source closures, guards/registry, combined runtime and commits. No runtime execution until all production sources freeze.

## Retained stage

Keep the existing first four `StagedContinuousCandidate` fields and add the following required fields. All are frozen, detached snapshots made by the actual `ContinuousUpbitCandidateSource.collect` call; no new provider capability is issued.

```python
@dataclass(frozen=True, kw_only=True)
class StagedContinuousCandidate:
    preview: ContinuousIntervalPreview
    path_sha256: str
    manifest_sha256: str
    observed_at: datetime                  # original preview evaluation clock; existing meaning
    capture: ContinuousCapture            # ORIGINAL accounts, full SourceReceipt bytes, manifest, fenced time
    anchor: OpeningAnchor
    collection_coverage: CoverageEvidence
    trade_fees: tuple[TradeFeeEvidence, ...]
    collection_requested_at: datetime      # outer collect clock, before boundary-baseline choice
    collection_clock: tuple[datetime, ...] # exactly two ACTUAL collector reads: start then finish
    collection_baseline_sha256: str        # original temporary self-check baseline commitment

    # read-only properties, never new observations:
    first_received_at: datetime            # capture.receipts[0].received_at
    collection_started_at: datetime        # collection_clock[0]
    collection_completed_at: datetime      # collection_clock[1]
    execution_ready: bool                  # always False
```

The capture supplied to `path_source` remains exact `ContinuousCapture`, with no `bundle` or temporary risk baseline. The original midnight self-check RiskBaseline is **not retained or exported**: retain its digest and derive the identical temporary input from exact previous baseline + `collection_requested_at` during replay. Existing weak-reference/flat-source R6 discipline remains applicable. Captured accounts and the path-derived endpoint accounts remain distinct.

Capture the actual inner clock with a wrapper passed only to `collect_upbit`; do not substitute outer start or first receipt for collector start. The collector's own current implementation calls its clock twice. More/fewer clock reads refuse staging rather than guessing. Source fetch may use its own explicit clock; those original receipt times are retained separately.

Copy the supplied anchor/coverage/fees before collecting. Preserve a detached original capture before calling path/coverage integrations; stage must not retain mutable input aliases. Existing path-only archive is unchanged and is not advertised as a full packet archive or restart authority.

## Pure material builder

```python
MAX_CAPTURE_RECEIPTS = 2000
MAX_CAPTURE_ROWS = 100000
MAX_CAPTURE_BODY_BYTES = 8 * 1024 * 1024
MAX_CAPTURE_TOTAL_BYTES = 64 * 1024 * 1024

class GuardCaptureMaterialError(ValueError): ...

@dataclass(frozen=True, kw_only=True)
class GuardCaptureMaterial:
    account_capture: AccountCaptureInputs
    valuation_inputs: ValuationInputs
    path: ContinuousPath
    coverage: VerifiedCoverage
    interval: BaselineInterval
    capture_material_sha256: str
    @property
    def execution_ready(self): return False
    @property
    def source_authenticated(self): return False

prepare_guard_capture_material(staged, previous, *, now) -> GuardCaptureMaterial
```

Budget is admission, not corruption: fixed `GUARD_CAPTURE_RESOURCE_LIMIT`. Check receipt count, per-body and aggregate bytes **before** deepcopy/JSON decode/replay/hashing. Counts and total bytes are exact ints; never truncate retained receipts or candidate records. The material limit is explicit; it does not claim all existing 2000×8MiB captures fit memory. Actual source collection may already have performed bounded GETs before stage admission refuses; nothing is published and the previous stage has already been invalidated. The retained normalized structure is also admitted before copying: exact declared dataclass fields only, one account, at most 64 positions/marks and three evidence pages, at most 100000 rows, 20000 path events and the corresponding bounded valuation points. A typed traversal caps depth (24), visited nodes (2000000), scalar text (65536 characters each and 16 MiB total), integer width (256 bits), and aggregate byte fields (64 MiB). Decimal coefficients/exponents are bounded before fixed-format comparison; the broad 512-digit/±512 traversal ceiling admits intermediate exact arithmetic only, while the actual collector/path/baseline validators keep their existing narrower numeric rules. Hidden instance attributes are refused before deepcopy.

The helper performs no current clock read, callback to an external source/verifier, filesystem operation, owner observation, commit, head update, Controller or adapter operation. `now` validates age; it never replaces original timestamps. Work runs under the existing exact Decimal precision convention (512, Inexact trap).

### Replay sequence

1. Require exact stage/previous/capture/receipt/claim types and finite budgets before copying. Validate previous state through existing baseline validation. Bind path previous digest/start, stage hashes, exact two collector clock readings, first receipt and fenced end, outer request time and preview evaluation time. Scope remains Upbit KRW spot.
2. Rederive the collector's original temporary risk baseline exactly: exported baseline normally, existing midnight opening helper only when the original outer request falls inside its boundary window. Compare its digest with `collection_baseline_sha256`. Do not retain that temporary baseline in the public stage/material.
3. Construct a private in-memory replay source whose `fetch(path,params)` consumes **the next retained original SourceReceipt exactly once** and requires exact route/params/scope. Its clock yields only the two retained inner clock values. Call the real `collect_upbit` parser/fence/account reconstruction with original anchor/coverage/fees/baseline and the fixed original collector bounds. Reject unused/trailing/missing/reordered receipts or clock reads.
4. Compare real replay `CollectionResult.receipts`, `.manifest_sha256`, `.bundle.accounts`, and fenced time to the retained capture. This binds normalized account evidence to raw receipts; merely recomputing checksums or separately validating an AccountEvidence is insufficient.
5. Recompute the preview from the replayed collection and the original path using the same pure arithmetic as the existing preview. Add a private replay branch in `account_interval` that checks the retained `VerifiedCoverage` request/hash/time/contract as an **external claim**, without invoking a lambda pretending to authenticate it. Existing public preview continues calling the actual configured verifier once; material replay calls no verifier. Compare every preview field (including exact coverage and valuation) with the retained preview.
6. Derive `AccountCaptureInputs` from original capture + recomputed endpoint, and `ValuationInputs` from real replay account/FIFO fills, pre-start flows, historical/inside fill partition and opening cash/units. The existing guard rechecks these inputs when planning. No arbitrary loss/extrema/cash replacement is accepted.
7. Return detached immutable material. Its domain-separated digest binds the original anchor/coverage/fees, exact receipt metadata and verified raw SHA values, original clock/baseline bindings and all derived material fields. Return no owner claim, policy approval, guard receipt, source token or operation flag.

Structural claim binding is deliberately distinct from source authenticity. A fully self-consistent independently constructed packet may be valid audit material; it still has `source_authenticated=False` and cannot be consumed as a live provider. Changing raw/account/preview together is not an authenticated correction, and produces a different material identity. Tests must not demand cryptographic provenance that this stage cannot provide or supply a fake authority to make it appear proven.

## Diagnostics and tests

Helper diagnostics use fixed `GUARD_CAPTURE_*` codes: INPUT_REQUIRED, RESOURCE_LIMIT, CLOCK_BINDING_INVALID, BASELINE_BINDING_MISMATCH, RECEIPT_REPLAY_MISMATCH, COLLECTION_REPLAY_MISMATCH, PREVIEW_REPLAY_MISMATCH, EVIDENCE_REFUSED. Underlying actual collector/baseline/continuous fixed errors may be preserved where they are more specific; no raw exception/path/account text is returned. The actual candidate source preserves its existing AccountInterval/Evidence/Continuous diagnostics and invalidates failed stages.

Meaningful tests use actual synthetic GET parsing and a recorder created before collection, real retained temporary store baselines, and explicitly synthetic coverage/owner claims solely in tests. Cover flat/held/partial fill/open orders, hidden trough, 22:00 and midnight boundary reconstruction, raw/account/manifest substitution, trailing or omitted/reordered/changed route receipts, exact inner clock trace, stale/rollback/gap/epoch boundaries, resource admission before decode, input/output detachment, and actual guard-plan input equality. No positive validation result or verifier is patched to True. Builder/plan changes no files or heads; capture may create only its existing path audit file. Existing source callable, Coordinator controlled mode and non-operational material remain refused/inert.

No full packet archive, restart replay authority, provider publication, owner authentication, live completeness issuer or order path is implemented in I3a. Those remain separate next stages described in `TRADEGEN_P2_NEXT_BRIDGE_PLAN_2026-11-13.md`.

법률, 세무, 투자 조언이 아니며 면허를 가진 자문가가 아니다
