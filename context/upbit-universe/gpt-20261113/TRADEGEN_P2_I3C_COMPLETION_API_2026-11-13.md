# P2 I3c-time exact contract — 2026-11-13

Scope: existing Controller's exact committed-account operations only. This is implementation authority, not live trading activation or a source-completeness assertion. Base is PR50 main d21ffaa. No Runner, Coordinator, transport, capability registry, session wire, reserved-row shape or carry deadline wire changes.

## 1. Public API and ownership

```python
Controller(*, journal, account_provider, policy, adapters, session_provider, clock=None)
# Existing observe(now=...), reserve(...now=...), dispatch(...now=...) signatures unchanged.
```

At constructor admission, exact `CommittedAccountProvider` requires callable clock; no default datetime.now, imported review authority, caller boolean or datetime substitutes. Legacy callable provider keeps existing behavior with clock omitted. Supplying clock to a legacy provider does not silently enable new committed semantics.

Implementation: `execution_control/controller.py` (pr4e_coordinator). New actual integration tests: `tests/control_committed_completion.py` (pr4e_runner). Existing actual committed fixture updates and necessary exact guard checks: pr4e_owner. Root owns registry/runtime/delivery. This card/design: protective_hold_design. No actual home/API/key/order; temporary signed fixture + synthetic source + actual DryRunAdapter only. No runtime until joint freeze.

New clock requirement applies to the object, but completion flow runs only in observe, a new reserve, and a RESERVED→dispatch attempt. Existing already-recorded order returns remain historical `OrderState` facts; they do not become fresh eligibility assertions. Kill/halt/states/known cancel/reconcile/local RESERVED cancellation preserve existing behavior and do not acquire new clock/owner requirements on their operation paths.

## 2. Clock and private lifetime

`now` remains the caller's requested observation instant. It does not set the internal clock. Under exact committed use:

- Validate `now` and read actual injected clock after acquiring the existing actual Journal transaction and folding its rows. Initial actual `t0 >= now`; future caller request is refused. Actual times must be aware exact datetime and remain ordered against prior accepted internal clock observations and current Journal tail time.
- Keep every accepted internal clock observation as a watermark. Do not replace it with a later operation's original caller now. On rollback/invalid time, retain the last trusted watermark and mark the current operation's clock unusable for a local terminal write.
- Use actual t0 for current account/owner authorization. Original account.asof/server_time/risk.asof and committed owner claim.observed_at remain unchanged. Private operation frame retains original t0 and owner-load start/completion observations; a second owner read cannot reset the age of the first actual check.
- Read clock after heavy account/head/owner/code/session/permit/request work. Final time must be >= all trusted observations and current Journal tail; original account freshness remains <=30 seconds, original server comparison <=60 seconds, original first current-check lifetime <=30 seconds, and existing same-Seoul-date constraints remain.
- All heavy checks precede the final completion clock. The final pass is finite comparisons over exact previously validated values: original times, existing rule/session bounds, policy time boundary and request/phase identity. No fresh source callback or current timestamp on old evidence.
- Crossing Seoul midnight or an applicable existing recovery cutoff (22:00 under the current policy) during this operation refuses it. Do not reuse a pre-boundary risk decision or invent a new loss budget. The next ordinary operation evaluates existing policy at its actual time.

The clock is a dependency of trusted signed composition, not proof of remote source identity. Same-head D12/session-effective terms still require actual owner reloading; a head equality check alone is insufficient.

## 3. Internal phases and reused authorization

Private names may be chosen by the implementation owner; tests must exercise actual public operations and actual I/O seams, not forge a private phase object. Exact required lifecycle:

1. **STARTED:** actual transaction, initial clock, exact provider/Journal, original read/positions/current owner, policy/session/rules/request identities retained privately. Existing `_authorize` remains the initial gate/permit producer. Its return may be refactored into a private internal result to retain `_AccountRead`, actual ctx/intent/permit and actual prepared session; this is not a public credential.
2. **PREPARED:** after actual adapter.prepare and validate_request, re-read actual committed account/head and current owner using the same operation session/positions. Reuse `_account`, `_capacity`, `_positions`, `_committed_context`, `_intent`, `_exact_caps`, actual `gate.verify_permit` and, for buys, actual `verify_session`. Preserve code/head/actual key continuity already represented by the genuine owner context and retained signed-chain identity; compare effective terms/day/session, not head alone.
3. **RESERVED:** only after the above + final clock, append the existing reserved row using a validated actual timestamp. Check actual completion after append before returning success. A late append leaves its real RESERVED row intact; do not issue a successful fresh reservation result, erase the row or create a different client ID. A later dispatch revalidates independently. Existing own permit bookkeeping must remain consistent with the actual retained reservation; an unreturned permit is not inferred from a public row.
4. **DISPATCHING:** initial dispatch authorization and request checks precede its existing row. Retain a private proof of that exact new row: actual active tx identity, row seq/hash/prev, client/order/request/permit digests and journal extent. No input argument can supply this proof. The only intended exception is this operation's just-written DISPATCHING row. **Do not call the whole `_authorize` again after the row**, because its uncertain-order loop also sees the current client despite exclude, and do not broadly exclude uncertain records to make it pass.
5. **FINAL_CHECKED:** after DISPATCHING append/fsync, use a read-only revalidation helper under the same actual tx. Recheck actual committed state and actual current owner/session/permit using existing predicates, not a second permission engine. Retain guard daily-stop/high/floor/halt and existing reducing rules. Verify the exact own tail again and read final clock after all heavy work. Then and only then call the existing `_send`, which issues the existing one-use capability. No baseline advance/commit/head CAS, no nested Journal transaction/snapshot, no rebaseline.

Risk policy code is not duplicated. Extract and reuse the existing exact pure `_risk_view` / risk.evaluate predicates for the final current buy check, including current journal suffix high/floor/daily-stop/halt. Re-evaluating that same read-only policy is required; it must not append another risk snapshot or issue a second permit. Do not call `_snapshot_risk` merely to mint another permit. Existing initial risk snapshot/protection latch writes remain conservative. A time-boundary crossing is refused rather than silently switching policy epoch inside a partially recorded dispatch.

## 4. Definite local no-send versus uncertainty

A post-DISPATCHING refusal is **definite local no-send** only while all of these facts hold: this public dispatch invocation has never entered `_send` or adapter.dispatch; the same actual tx is still active and healthy; current physical journal readback agrees with tx and its last row is the exact private DISPATCHING proof; actual trusted recording time is available and nondecreasing. Validate paths/readback under the existing transaction without calling Journal.snapshot or nesting a lock. No caller field or exception text can establish no-send.

For this proven case, reuse existing `_result` and existing `rejected` shape:

```python
AdapterResult(
    status='rejected',
    code='local_pre_send_boundary_refused',
    client_id=original_order.client_id,
    venue_order_id='',
    metadata=(
        ('tg_local_pre_send', 'not_called'),
        ('tg_local_reason', fixed_reason_code),
        ('tg_dispatch_row', original_dispatching_row_sha256),
    ),
)
```

The `code` is not currently persisted by `_result`; the exact local provenance metadata above is therefore required. This record means local rejection before sending, not an exchange response. Successful durable REJECTED can release a never-sent reservation. Same-client dispatch returns that terminal historical state and does not retry. Public dispatch returns the actual replayed REJECTED OrderState after successful local record/readback; it does not return success/submitted or synthesize an acknowledgment.

If `_send`/adapter was entered, proof fails, clock fails, the rejection append/cleanup fails or journal becomes torn, **do not claim a local terminal rejection or release capacity**. Preserve actual durable facts and existing uncertain/reconciliation behavior. If the local REJECTED row plus retained journal anchor became durable but cleanup/response was lost, do not roll it back or overwrite it with UNKNOWN: the caller cannot claim confirmed success from that failed invocation, while restart replays and honors the actually durable REJECTED. If append/anchor completion is unconfirmed or torn, no terminal state is invented and the last DISPATCHING/UNKNOWN or damaged state remains refused. Do not rewind to RESERVED, truncate/repair the journal, fabricate a current timestamp, or retry create. A fixed diagnostic is raised when no terminal result can be proved. The next process reads durable facts; an in-memory no-send belief is not restart proof.

The local rejection path may read its trusted clock and actual Journal, but must not require the failing account/source/owner condition to recover before recording an otherwise provable no-send. It must still refuse if the Journal/phase/clock proof itself is damaged. Existing late genuine broker-response and uncertain-send behavior remains separate.

## 5. Fixed diagnostic contract

New completion errors are fixed ValueError codes only; no underlying exceptions, raw owner/source data or private paths. Proposed exact codes for the new branches:

- `COMMITTED_COMPLETION_CLOCK_REQUIRED`: exact provider without callable clock.
- `COMMITTED_COMPLETION_CLOCK_INVALID`: clock raises/naive/wrong-type/out-of-range.
- `COMMITTED_COMPLETION_CLOCK_ROLLBACK`: clock before any retained trusted observation or current Journal tail.
- `COMMITTED_COMPLETION_REQUEST_FUTURE`: caller now later than first actual clock.
- `COMMITTED_COMPLETION_STALE`: first actual check/original evidence exceeded its finite freshness window.
- `COMMITTED_COMPLETION_POLICY_BOUNDARY`: operation crossed Seoul day or applicable recovery cutoff.
- `COMMITTED_COMPLETION_PHASE_CHANGED`: exact active transaction/current physical tail proof no longer matches.
- `COMMITTED_COMPLETION_AUTHORITY_REFUSED`: final actual account/owner/rule/permit/session checks refuse or change; the detailed existing underlying failure is not copied into local metadata.
- `COMMITTED_COMPLETION_LOCAL_RECORD_FAILED`: definite no-send terminal append/readback/cleanup cannot be established.

Existing initial `_account` / `_authorize` / owner evidence diagnostics need not be renamed. At postrow final refusal map only the above narrow new categories to `tg_local_reason` (length and enum enforced); unexpected final errors become AUTHORITY_REFUSED only if actual no-send proof can independently be established, otherwise propagate a fixed nonterminal failure. Never convert an already-entered adapter/send exception into local rejection.

## 6. Required tests and boundaries

Actual fixtures: existing control_committed_account produces temp signed owner/code log, actual baseline/guard stores+heads/commit/provider and DryRunAdapter. Source/coverage remain explicitly synthetic. New tests cover actual public operation paths:

- Clock required, future requested now, rollback between every observed boundary, delayed owner/code/provider/prepare/fsync, exact 30 seconds and +1µs; no resetting the original lifetime to a later owner read.
- Final current owner change including actual signed head/code/session/effective-limit change; same-head midnight/D12 distinction, key replacement/broken actual log fails closed.
- Actual DISPATCHING append then late completion: definite no-send gives durable REJECTED/local metadata/create0 and same-client no resend. Successful fresh reducing create remains exactly one through actual capability consumption.
- Rejection append failure, forged/extended/replaced tail, torn journal, clock failure or adapter already entered never yields local terminal release. Preserve uncertainty and existing restart no-create-retry.
- Existing halt/kill/daily-stop independent reducing behavior preserved; buy guards, session/rules expiry and scope unchanged. Existing recorded-order return is historical, not a current fresh approval.
- No new baseline/guard advance/commit/CAS/auto seed, no nested Journal acquisition, original account/claim times retained, no caller-supplied Context/private phase proof.
- Legacy callable paths and known cancel/reconcile/kill/halt retain previous API and behavior. Existing row wire shapes remain exact. Existing carry controlled/source/Coordinator refusal tests continue to pass.

No Controller-visible E is added here, so no promise of E being enforced inside a slow Controller call. No final-wire freshness promise: actual capability issuance, credentials provider, wire signing and HTTP boundary can still consume time. Those are explicitly later tasks. The new result is a finite actual Controller completion check, not a remote lease, source-completeness proof, protected-loss guarantee, current guard publisher or trading activation.

법률, 세무, 투자 조언이 아니며 면허를 가진 자문가가 아니다
