# PR5 B1b-2a — restrictive research revocation at the verified owner head

2026-11-13. Implementation and the frozen related integration run are complete. This stage adds a signed restriction on one exact research approval body. It neither selects a strategy nor activates trading. The final evidence follows; delivery identifiers are retained in the handoff ledger.

## Restriction and signed identity

`research_attestation_revoked` is an owner-signed event with exactly `purpose`, `target_sha256` and `reason_code`. It applies to archive identity, fixed source/implementation review or fixed-carry source/implementation review. It has no undo, automatic expiry or automatic reactivation operation. A verified future-dated restriction takes effect immediately; existing timing rules for code, tables and limits remain unchanged.

The target is SHA256 of `tradegen-research-attestation-revocation-target/1\n` followed by the existing domain and canonical signing bytes of the document body. It is not the raw JSON file hash or signature-byte hash. Cosmetic whitespace or key-order changes in a source-review envelope cannot bypass the restriction. Computing a target validates structure; it does not authenticate the input document or turn a past approval into a current one.

The actual verified owner-log fold puts an immutable set of purpose/target pairs into the same sealed Context as its owner head. No separate unsigned blacklist or caller-provided `revoked=False` supplies authority. An exact empty set preserves the previous Context hash projection; a nonempty set is deterministically included. Missing instance fields, mutable substitutions and malformed pairs are refused rather than falling back to an empty class default.

All existing source and implementation authentication paths consume the restriction in their common authentication function. A revoked eligible candidate is not silently removed so that another candidate can be selected. Archive authentication continues to report exact archival identity, but reports `REVOKED` or `NOT_REVOKED_AT_HEAD` at the final actual owner observation. It remains a display result, with current use, research selection, recovery and execution flags false.

## Restart and incomplete publication

Inspection found that existing approved-state snapshots preserve their first head. A later restriction could therefore disappear after a log-only rollback and process restart if no newer anchor had been retained. This stage adds one immutable anchor per verified restriction under the existing approved-store anchor mechanism. The filename is the signed event row hash; the exact canonical content is its sequence and row hash.

The actual owner loader verifies the complete signed chain and existing anchors, persists observed restrictions under the owner-log sidecar lock, then rereads and verifies before returning usable authority. The standalone command independently checks its research-anchor inventory before confirmation and under the same lock. An anchor that disagrees with the chain, references a different event, is incomplete or has invalid bytes refuses use. Existing anchors are not overwritten or regenerated to match a rolled-back log.

The new anchor writers use exclusive creation, file flush, exact readback and the platform's supported directory synchronization. They do not reuse the legacy temporary-file rename helper's POSIX overwrite race. A partially written final anchor is retained and refused. Coherent rollback of the log and every independent anchor remains outside this local protection; this is not an external monotonic hardware counter. Native Windows power-loss durability is not established by Linux checks.

## Independent signer

`research-revoke` reads the original bounded detached document and derives its target independently. It displays purpose, target and reason, receives the existing direct owner confirmation, and checks current key, the entire signed owner chain, input bytes and time again under the append lock. It does not require a currently valid strategy review to withdraw that review. Generic `event` and direct generic signing paths cannot bypass the document-derived target procedure.

Success requires both the owner-log row and its durable anchor. If the row was appended but anchoring failed, the error states that the restriction may already exist. An exact retry of the same last restriction verifies that row and completes its anchor without a new signature or duplicate append. Conflicting partial anchors are preserved and refused. Expensive anchor work is followed by input, key and clock rechecks before signing or acknowledging the retry.

No actual owner key, account, exchange API, activation or order is part of development or validation. A restriction does not delete original research and is not a liquidation instruction. Existing loss floors, halt behavior and approval scopes are unchanged.

## Validation and remaining scope

The pure codec development run passed 12 tests. A later signer/owner development run retained one fixture failure: a new event used an earlier UTC timestamp than a future halt already in the fixture. The test timestamp was corrected without changing the risk policy or production timing rules. That failed run remains in `signer-owner-dev2-summary.json`.

The final frozen integration run completed **914 PASS / 0 FAIL / 1 NOT_RUN** out of **915**, in **1231.571 seconds**, one continuous process. It includes all compliance and execution-control cases plus affected archive, source-review, recovery, signer, owner and launch-guard paths. This is a related-suite regression, not a whole-repository run. The NOT_RUN case requires a native Windows console; fake Win32 API tests on Linux are not native deployment or power-loss evidence.

Runtime implementation commit: `17801eb631e6314a33bfe692b15a8312edae444f`. Tested integrated head: `797e8f5b934127734ae1207daaced9d1c3501200`, including the previously merged exact-recovery backend. Tracked Python/YAML fingerprint: `409d7a66ad993bf6fe6eb7adc982b5b9ec189d94977ea473652fd0555d03d681`. Nineteen KEYLESS variables were set; source and protected-home metadata were unchanged from before imports/discovery through completion, and QA bytes were restored. The historical `revocation-integration-dev1` label is retained for the final unchanged run; its summary and rows are the authoritative results. Overlapping development counts are not additive.

The native directory seam has an exact module AST/import guard, retaining its reviewed fixed child names and access/share flags. Owner/signer checks cover append/anchor interruption, partial anchors, log-only rollback, a rollback between initial verification and lock acquisition, canonical target equivalence, late clock/input changes, malformed or deleted revocation state, exact retry without duplicate signing, and actual all-candidate source selection refusing a revoked member.

The next stage still needs the single actual sealed-family evaluation, all eligible source/audit reviews, selected real factory/history verification and completion-time checks. Exact archive recovery is already merged as a separate backend; automatic recovery operations remain unfinished. Telegram/WebAuthn, actual Windows deployment, held-account reconciliation and final owner operational approvals remain unfinished.

법률, 세무, 투자 조언이 아니며 면허를 가진 자문가가 아니다.
