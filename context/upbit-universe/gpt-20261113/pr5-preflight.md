# PR5 study preflight — 2026-11-13

Status: read-only design/code inspection while PR4c verification continues. No source edits, test execution, repository imports, git commands, API calls, owner-state access, signing or arming were performed for this preflight. Findings about proposed PR5 code are static conclusions, not executed reproductions or strategy results.

Sources: `docs/superpowers/plans/2026-11-11-upbit-krw-universe-pr5-study.md`; `docs/superpowers/specs/2026-11-11-upbit-krw-universe-design.md` sections 14, 17, 18; current source in `/workspace/tradegen-universe-1113`; planned PR4d driver/history and PR4e runner/coordinator. Recheck against merged PR4d/e before implementing exact replacement instructions.

## Blocking finding: candidate failures and authenticated family selection

Spec section 14 says an unmarkable, vanished or terminal-unliquidatable held coin fails only its affected candidates. The same section says existing `ValidationResult`, family commitment, study review and external signer remain unchanged. These statements do not compose with the proposed evaluator and current review pipeline:

- PR5 plan lines 1930–2054: `_UniversePath` raises `StrategyEvidenceError` for legitimate failed trials, and `_evaluate_universe` does not issue a result for them.
- Current `execution_launch/study.py:589` `_select` catches that error, but returns **no review requests** whenever the number of results is less than the number of candidates. Failed capture hashes are not collected into a complete family there.
- Current `execution_launch/study_review.py:119` requires all capture files, then evaluates them in a dictionary comprehension. A legitimate failed-trial exception aborts authentication for every candidate.
- `execution_launch/strategy.py:276` `ValidationResult` requires all four metrics, returns and probabilities. It has no honest representation for a path that cannot be valued. Zero or invented probabilities are not a solution.
- `execution_launch/review_request.py:109` already accepts an opaque evidence digest per family member. This permits a proposed internal outcome representation without changing the schema-2 family JSON shape, but changes what a failed member's digest means.

**Proposed additional design, pending root review and owner approval:** one shared family-evaluation path used by `_select` and `authenticate_study_selection`. Fully validate each entire capture, all frames/decisions, registration, protocol, rules and window before converting any whitelisted market-path failure into an internal failed-trial outcome. Hash a domain-separated canonical failure record binding the protocol, registry, complete inputs, fixed reason and deterministic failure location/path. Keep every exact raw capture hash in every signed family commitment. Only genuine issued `ValidationResult` objects can enter numerical ranking or review eligibility. Report failed candidates as excluded with their concrete failure reason, never missing or numerically evaluated. Malformed, incomplete, omitted or tampered evidence refuses the whole family. Benchmark failure never permits another candidate to qualify.

Do not catch every `StrategyEvidenceError` and call it a failed trial: that would erase the integrity boundary. A valid failure early in a path must not conceal malformed later frames or decisions. Do not weaken the existing PR13 protections in `tests/launch_study_review.py:225–244`: changing a winner to cash or changing even a failed candidate's raw bytes must still invalidate existing signatures.

This is beyond the literal PR5 instruction “study review ... unchanged.” Root requested an owner-facing amendment brief; see `/workspace/outputs/TRADEGEN_PR5_REVIEW_AMENDMENT_2026-11-13.md`. No implementation is authorized by this preflight itself.

## Other concrete findings

| Finding | Evidence and consequence | Required treatment |
| --- | --- | --- |
| Decision time is taken before the computation it attests | Plan `run_universe_capture`, lines 2776–2798: `sampled` is read/checks deadline before frame building, chooser work and evaluator-path replay; every decision later stores that earlier `sampled`. Work that exceeds the next-slot-minus-delay boundary can appear timely. | Read a trusted clock after producing the relevant decision, check monotonicity and the fill-delay deadline, store the actual decision time. Refuse/record a failed incomplete trial if the work is late. This enforces the existing causal timing contract. Current fixed `PaperCapture` also samples before `_append`; do not claim PR5's added work has been measured merely because that older path exists. |
| Tick receipts can arrive after the slot | Plan `_book_rows:2602` parses books with `slot` but calls `parse_instruments(ticks, asked)` without a slot check. `parse_instruments:736` validates receipt time relative to itself. A tick read finishing after slot but before the broad sampling deadline is accepted. | Require the tick receipt to have been received by the slot at the capture boundary, before using it for that slot's rounding. Preserve parser API unless a separately reviewed change is necessary. Choose an explicit age rule only if needed; do not invent one from the 1-second book-clock work. |
| Malformed market listings can become false disappearance | Current `core/compliance/rules.py:1064` ignores rows with missing/non-string/nonmatching market IDs; current `UniverseSlotSource.read_flags:221` and PR5 Task3 proposed replacement call it directly. `[{}]` and `[{"market": null}]` therefore become an `ok` empty map, so capture marks needed coins vanished. PR4c's new E1/collector consumer checks do not cover this source. | Apply the already-reviewed narrow raw-list shape/unique full market-ID check at this consumer too: malformed read unavailable, raw answer retained, never genuine absence. Keep valid non-KRW markets and an empty valid list semantics. Coordinate with PR4d/e because they also consume `UniverseSlotSource`. |
| Retry count is declared, not verified | Plan `build_study_plan:1291` validates only type/ID syntax/uniqueness/disjointness. The plan test at 1078 accepts invented `prior_attempts` without registry entries. Spec calls these “registered study_ids ... for the same selection.” | Resolve the contract before calling retry accounting audited. At minimum validate supplied prior IDs against registration evidence; prove/describe same-selection linkage. Omitted historical attempts cannot be discovered from a tuple alone. Any additional persistent lineage/owner declaration design requires root review. Existing K arithmetic test is necessary but insufficient. |
| Global market-index exhaustion differs from per-read capacity | Plan `_frame:2619` has a permanently growing 320-name dictionary. After a 320-name history, a later valid read of 320 names containing a replacement coin can silently omit that new coin's price/book. An unflagged new coin does not trigger the flag-exception failure path. | Add churn coverage and choose explicit unavailability/refusal behavior at the bound. Do not silently describe the whole read as fully represented. Keep the approved index/size limits unless separately reviewed. This is a capacity edge case, not evidence that the 48-hour byte bound itself fails. |

## Failure/causality test matrix to add

All below use invented fixture data and disposable synthetic review keys only; no real study outcome or success probability is implied.

1. Complete mixed family: one mathematically qualified result and one genuine held-coin failure; complete schema-2 family binds both raw files; the qualified candidate can reach signed selection, failed candidate is excluded with no metrics.
2. Separate held vanished / no mark / terminal no book cases, including lag-2-only and double-cost-path-only holdings. An unrelated candidate remains evaluable. Shared benchmark failure yields no selection.
3. Failure at an early frame followed by a malformed late frame/decision, wrong registry/rules, missing final frame, malformed JSON, or capture omission: whole-family refusal; no partial requests.
4. Failed raw bytes changed by whitespace; failed input bytes changed; failed reason/location changed; winner changed to cash with its review omitted: previous signatures refuse. Keep the PR13 tests intact.
5. All candidates validly fail: complete disclosed family, no requests/selection, no owner-key access, no synthetic probabilities. Legacy fixed candidates and existing schema-2 successful/numerically-failed families keep behavior.
6. A chooser or replay consumes time past `next_slot - fill_delay`; clock rollback; boundary equality: verify exact recorded decision timestamp and refusal behavior. No early timestamp reuse.
7. On-time books with tick receipt after slot; receipt exactly at slot; malformed/future receipt: late ticks unavailable, exact boundary accepted if otherwise valid.
8. Market listing `[{}]`, missing/null/bad market IDs, duplicate IDs: unavailable, never vanished. Valid non-KRW rows, valid empty list, genuinely absent held coin stay distinct.
9. 320 distinct indexed markets, then a replacement/new coin while each read still has 320; flagged and unflagged new coins; needed held/benchmark coin: explicit capacity behavior, no invisible omission.
10. Prior ID absent from registry or linked to another selection, duplicate/current ID, valid prior attempts; K affects p-resolution, Sharpe adjustment and family-adjusted p. Document the limit on detecting omitted history.

The plan's `test_universe_capture_json_is_evaluated_and_assessed_like_the_fixed_one` produces only three round trips while the minimum is twenty. Its assertion that review is required and evidence is not ready does **not** test the eligible/signable/selected path. The plan's size fixture is a serialization stress fixture, not a complete causal market study. Both are useful only within those limits.

## Work groups and file ownership

| Group / plan tasks | Source ownership | Test/docs ownership | Dependencies / integration |
| --- | --- | --- | --- |
| Public books / Task1 | `execution_accounts/quotes.py` | `tests/accounts_quotes.py` | Shared `_book` parser extraction first; preserve single-book behavior. 1-second clock change follows this extraction and precedes final code approval. |
| Public ticks / Task2 | `execution_accounts/instrument_terms.py` | `tests/launch_instrument_refresh.py` | Build on PR4c authority/observation changes. Parent alone reviews/updates `tests/renewal_boundaries.py` initializer pin. Do not apply old exact text over changed authority logic. |
| Raw receipts / Task3 | `execution_accounts/universe.py` | `tests/accounts_universe.py` | Optional `answer=None`, `repr=False`, `compare=False` keeps PR4d/e constructors compatible. Include listing-shape regression if root confirms scope. |
| Freeze rules / Task4 | `execution_launch/study.py` | `tests/launch_universe_study.py`; central `tests/launch_acceptance.py` | Program-specific feasibility, max3, retry contract, CAPTURE_FILES additions. |
| Evaluator / Task5 | `execution_launch/strategy.py` | shared `tests/launch_universe_study.py` | Common arithmetic/result helpers must preserve fixed numerical results. New auth-outcome design, if approved, belongs with evaluator + family integration owner. |
| Capture and CLI / Tasks6–7 | `execution_launch/study.py` | shared `tests/launch_universe_study.py` | Depends on Tasks1–5; same study/test owner should serialize these changes. |
| Auth amendment / additional approval | `execution_launch/strategy.py`, `study.py`, `study_review.py`; `review_request.py` only if actually needed after design review | `tests/launch_universe_study.py`, `tests/launch_study_review.py`, possibly `tests/launch_review_request.py` | Separate reviewable scope; preserve schema2 and original raw-byte binding. No signer changes proposed. |
| Draft tooling / Task8 | `tools/research/prepare_shortened_study.py`; inspect `prepare_launch_example.py` | `tests/launch_shortened_study.py`, shared universe test | Can proceed after freeze API settles; avoid simultaneous shared-test edits. |
| Docs / Task9 | Five docs named below | docs review | After final behavior and measured/owner-dependent limitations are known. |
| Final integration / Task10 | no independent feature ownership | guards, focused regressions then central full suite | Run once files are frozen; separate code checks from actual-data qualification. |

The five Task9 documents are `docs/launch-workflow.md`, `docs/remaining-market-readiness-2026-11-06.md`, `docs/upbit-quote-contract.md`, `docs/instrument-term-renewal.md`, `docs/quote-timing-diagnostics.md`. Keep `study.py` CRLF and existing other encodings; use verified byte-preserving edits.

Readers Tasks1–3 can be parallel. Task4/6/7 all own study.py; Task4/5/6/7/8 all append one test module, so assign one integration owner or explicitly partition then serialize. Parent owns shared test registry/pin edits. PR4d and PR4e both add `tests/launch_acceptance.py` entries; append, never replace their additions.

## PR4d/e and hash boundaries

- PR4d owns `driver.py`, `live_history.py` and history tests; PR4e owns runner/coordinator/toast/owner tooling plus a live_history helper. Neither plan directly edits the PR5 study/evaluator/readers. These are behavioral dependencies despite low text overlap.
- Preserve the PR4c authority classes, inquiry closure changes and evidence validation. Optional Answer fields must preserve existing FlagRead/TickerRead constructor call sites.
- PR5 changes `CAPTURE_FILES` by adding instrument_terms.py, universe.py and rules.py. Every new freeze must bind the new manifest; old plan/source digest mismatch is expected, not a reason to reuse old capture evidence.
- PR5 strategy.py and shared quote changes alter deployment/code identity as well as capture identity. The pending 1-second clock fix must follow PR5's shared `_book` extraction and land before final code approval and study freeze. Review its single/batch boundary tests together; never silently broaden the receipt/slot causal rule.
- Existing signature and result provenance checks remain necessary after all 4d/e/5 work. Regenerate code/source approvals for final bytes; do not relabel previous evidence as current.

## Fixture development versus actual-data gate

Fixture implementation and regression work can proceed offline. The proposed bound uses the actual encoder, 320-market index, 16 books, three candidates, price length16 and offset60000; the plan expects 577 slots / 48h / 5-minute bars to fit 12MiB and 865 slots / 72h to refuse. These are plan expectations, not newly executed measurements. `_plain` already always uses six fractional timestamp digits; timestamp text width is not an identified bound defect.

Spec section17 requires owner-PC measurements **before any real freeze**: endpoint batch acceptance/body sizes, thin-book/ticker freshness, orders/chance warning status (owner-run keyed read), delisting/zero-trade behavior, paged odds cost, snapshot/context load, monitor/slot timing, 72-hour live-history worst-case replay timing, and study chooser/read/frame size. The proposed batch readers do not implement an automatic one-request-per-market fallback. If measurement shows batching fails, implement/review that specified fallback before a real capture; do not assume API support from fixtures.

A real 48-hour prospective capture requires its actual future preregistered wall-clock window, raw receipts, complete candidate/retry evidence, independent source review, effective owner settings and final code identity. Fixture execution cannot shorten this elapsed-data requirement. Twenty completed exits may not occur; neither a winner nor profitability can be promised. No real capture, numerical result or probability was generated in this preflight.
