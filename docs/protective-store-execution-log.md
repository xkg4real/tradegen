# Protective holding P2: durable model state and outbox

2026-11-13. Base main `6030fe3063dc6b63eeaad48b3d818577f1c1219b`.

`execution_launch/protective_store.py` persists a complete P1 transition, its supplied facts, external ledger references and effect intents before exposing the updated model state. It adds no live lifecycle, broker adapter, owner approval issuer or order permission. The existing Coordinator does not call it yet.

## Commit and restart behavior

- A caller explicitly supplies the dedicated state directory, independent head directory, policy, context commitments and finite storage limits. Construction writes nothing. Storage provisioning does not seed or repair the head; the existing explicit operator provisioning step remains separate and is not proof of review.
- Each content-addressed payload contains every transition input, recomputed state and reducer effect. A small hash-chained journal row references it. Object staging/readback, journal flush/fsync, independent head CAS and complete graph/state readback must succeed before a new snapshot/outbox is exposed.
- A writer holds the singleton session lock. Root, head/chain configuration, held directory and lock identities are pinned and rechecked through append/CAS. Missing file identities, links, replaced paths and concurrent writers are refused. Readers validate the entire retained graph against the independent head.
- An interrupted write preserves the payload, partial journal or head mismatch for investigation. It never truncates the journal, adopts an unreviewed head or automatically repairs an uncertain commit. A failed writer cannot retry the uncertain append.
- Every nonempty reopened writer requires a persisted restart event. Recovery facts cannot silently rearm it. Missing financial-ledger references remain unknown; this store does not calculate or relax the principal floor, high-water protection, daily loss limit or halt.
- Global effect IDs prevent duplicate logical outbox entries. Notification attempt receipts record delivery only. They cannot approve management, clear a reduction obligation or activate trading. P2 has no reduction settlement API; known pending reduction intents reject contradictory entry/rearm facts until a later verified disposition implementation exists.
- `inspect()` and returned snapshots are historical model evidence, not current production permission. Supplied P1 authority/observation facts and ledger hashes are not authenticated merely by persisting them.

## Validation

Final isolated focused run: **178 PASS / 0 FAIL / 0 NOT_RUN**, 15.545 seconds. It includes all 36 new storage tests, all 24 P1 tests, existing independent-head/object tests and the affected launch, owner, execution, compliance, control and account guards.

Runtime/test source fingerprint before and after:

`ff0bb01a656e0c65cc117cd7a40d1f7adf733402f7021a9d1033d3bde313b5f2`

The launcher set all 19 KEYLESS variables, used temporary homes and preserved QA bytes. Actual home metadata was unchanged; actual home contents, credentials, exchange APIs and orders were not used. New source/test files were included in the fingerprint before execution.

The tests cover strict fully rehashed malformed state/effect records, rollback and head disagreement, partial journal and fsync/CAS interruptions, quota boundaries, notification replay/conflicts, pending reductions, expiry, clock recovery, lock/root replacement and unavailable file identities. A separate pure A–B–A effect projection test verifies global ID deduplication; it is not an executed trading lifecycle.

Independent review reproduced active lock/root replacement allowing a second writer, unavailable inode acceptance and allocation before the record-count bound. Those issues were fixed and received dedicated regressions. The first combined run had 177 passes and one invalid new guard-test expectation: it expected a shared `fdopen` shape to be forbidden in an existing writer where that exact shape was already approved. The negative test now checks unapproved modules; existing write restrictions were not relaxed. The final run above passes.

## Integration with PR4e

The storage branch was integrated with PR4e runtime `a772a24073ffb523ff7fa8d1e030398eaf56227a` at `59e15cb12b822597c2296afda3649eaca3dcb3ad`. All prior 178 focused checks plus the nine independent PR4e regressions passed: **187 PASS / 0 FAIL / 0 NOT_RUN**, 31.198 seconds. Source and actual-home metadata remained unchanged, with the same 19 KEYLESS variables and isolated test homes.

Integrated Python/YAML fingerprint: `7878c4902e3f11682474d697f8ac250089403ab13b52adee6d436f7299db9e13`. The later upstream merge adds only the PR4e execution log; it does not change this runtime fingerprint. PR4e's separate full 2,907-test run is predecessor evidence and is not reported as a complete P2 run.

The completed unit is `protective-hold/p2-store`. Actual lifecycle/bootstrap/account reconciliation remains `protective-hold/p2-integration`.

## Remaining boundaries

No real account/fill/open-order reconciliation, authenticated management approval, reduction dispatch/settlement, exact signed backup recovery, Windows power-loss test or complete application restart integration was performed. A party controlling both storage roots can coherently roll them back; local hashes and a local head do not provide an external trust anchor. These focused results are not a new complete repository-suite result or evidence of trading profitability.

법률, 세무, 투자 조언이 아니며 면허를 가진 자문가가 아니다.
