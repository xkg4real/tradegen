# PR5 A0a: candidate outcome document contract

2026-11-13. This is the metadata contract stage of the amended PR5 design. It does not issue evaluation evidence, authenticate a source, verify prior-attempt lineage, select a strategy, sign a review or activate trading. Existing study/driver/review paths do not consume these documents yet.

`execution_launch/research_outcomes.py` provides strict `CandidateOutcomeDocument` and `EvaluationFailureDetail` types, parsing, canonical encoding, domain-separated digests and exact current-candidate-set checks. An evaluated document has a result digest and no failure; a failed document has a supported failure location and no result or numeric metrics. A valid document remains a caller claim, including its status, original capture hash, registry/input hashes and time.

The module rejects missing, extra or duplicate candidates against the caller-supplied expected set. It does not prove that expected set matches the frozen plan or all prior attempts. Failed candidates cannot be silently dropped from that supplied set. Only the existing fixed/universe revision names are represented; the universe failure vocabulary does not implement its evaluator. The later shared whole-input verifier must authenticate every candidate and original record before issuing an actual evaluation failure or review request.

The codec bounds bytes, nesting, integer lengths, IDs, hashes, exact keys and failure locations. It distinguishes bools from integers, rejects non-finite/numeric coercions and revalidates frozen objects at encoding. Failure and evaluated-document digests use separate domains and never replace the legacy ValidationResult digest. Existing review schema1/2 and signer formats are unchanged.

Validation on the combined PR4e/P2-store base `59e15cb12b822597c2296afda3649eaca3dcb3ad`: **154 PASS / 0 FAIL / 1 NOT_RUN**, 43.321 seconds. The skipped existing signer check requires Windows GetConsoleMode. The run includes all 22 new outcome checks, existing strategy/review/family/signature tests and affected guards. The module has no I/O, implicit clock or app imports.

Runtime/test source fingerprint was unchanged:

`b31638936b1fc446d1b0cc9e2fa02d6ce07e503d18a906c0179af9191c3d2feb`

All 19 KEYLESS variables were set, tests used temporary homes and synthetic data, actual home metadata was unchanged, and QA bytes were preserved. Independent review covered deleted frozen fields, depth4/5 bounds, complete supplied candidate sets, absence of fabricated metrics and refusal to import documents as actual evaluated/signed evidence. No real account, key, source query, notification, approval or order was used.

Whole-family semantic validation and failure issuance, sealed versioned bundles and backup/recovery, new carry/universe evaluation, Telegram/WebAuthn approval, and production activation remain separate work. These tests are not market performance or a complete new repository-suite result.

법률, 세무, 투자 조언이 아니며 면허를 가진 자문가가 아니다.
