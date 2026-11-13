# PR5 causality and input regressions — preparation only

2026-11-13. Inspected `/workspace/tradegen-universe-pr4d-1113` at
`ea4e2a4925922ce468208c89020881cb01a08403`, plus the existing `pr5-preflight.md`.
No tracked edits, tests, application imports, network calls, private home/key reads, signing or arming.
Scratch fragments below were written and syntax-checked only. They are not measured RED/GREEN results.
PR5 implementation still depends on the earlier universe PRs merging.

`Plan` below is `docs/superpowers/plans/2026-11-11-upbit-krw-universe-pr5-study.md`;
`Spec` is `docs/superpowers/specs/2026-11-11-upbit-krw-universe-design.md` rev3.
Line references are to the inspected files, not an eventual merged PR5 implementation.

## Approved contracts and minimal regressions

| Topic | Existing authority / exact interface | Required regression |
|---|---|---|
| Decision completion | Spec §14: decisions use recorded inputs at k; execution is later by the prescribed lag. Plan `_universe_inputs:1888–1925` requires `sampled[i] <= decided_at` and `decided_at + delay <= next_slot`. Plan `run_universe_capture:2776–2798` instead stamps every later decision with the time sampled before frame construction and `choose`. | Delay the actual chooser using the fake clock. Each candidate's recorded decision time must be at or after that candidate's observed completion and within its deadline. Equality at the deadline is valid; one microsecond beyond makes the capture incomplete with `STUDY_CAPTURE_DECISION_TOO_LATE`. No reuse of an earlier time to fit the deadline. |
| Receipt-time causality | Plan `_on_time:2531`, `_prices:2588`, batch quote parser at `:449` enforce availability by the slot. `_book_rows:2602` calls `parse_instruments` with no slot; that parser uses its own receipt time for both bounds (`:745–747`). | With unchanged on-time books, tick receipt at the slot is usable; receipt +1 microsecond and +1 second is `unavailable` for each requested book row. Apply at the capture boundary; do not invent a tick-age rule or change single-instrument API authority. |
| Malformed listing versus absence | Spec §14 capture: a missing needed coin is `vanished` only after a good flag read; failed flag read requests all needed coins. Plan Task3 `:906–920` retains Answer on parse failure. Current `UniverseSlotSource.read_flags:228` calls `rules.market_flags`, whose filtering (`core/compliance/rules.py:1064–1078`) ignores missing/nonmatching IDs. | Missing/null/non-string/bad market IDs and duplicate full IDs make the whole slot flag read unavailable, retaining exact raw Answer bytes/hash. Valid empty and valid non-KRW-only lists remain good empty KRW maps; a valid KRW ID with incomplete flag fields remains `unknown`, not malformed or absent. |
| Cumulative market index | Spec §14 `:695–700`: index <320, read >320 unavailable, never truncated. Plan `_frame:2619–2656` has a persistent dictionary and silently skips new price/book names once full; only an unindexable flag exception makes flags unavailable. | Fill the dictionary with 320 names, then replace one listed name with a new coin in a still-320-name read. An emitted ordinary frame must not silently encode 319 of the 320 valid prices. Existing index bindings must not move, limits must not increase, and existing held/benchmark book rows must stay represented. See the unresolved narrow contract below. |

All of these concern input integrity and timing, independent of the pending authenticated failed-trial outcome
amendment. These notes introduce no numerical outcome, family-selection relaxation, signer change or new capture format.

## Prepared fragments

| Scratch file | Integration point | Scope |
|---|---|---|
| `pr5-causality-tests-fragment.py` | Append sequentially to `tests/launch_universe_study.py` after Tasks4–6 fixtures exist | Three tests: two-candidate post-computation timestamps; completion deadline equality/+1 microsecond; tick receipt slot boundary. |
| `pr5-listing-tests-fragment.py` | Append to `tests/accounts_universe.py` after Task3 Answer fields exist | Two tests: malformed/duplicate market IDs preserve failed raw evidence; valid empty/non-KRW and unknown/warning states remain distinct. |
| `pr5-market-index-fixture.py` | Diagnostic fixture and returned-frame postcondition only; not an auto-discovered test | 320-entry churn input and invariant assertions. Does not choose a new refusal code or an outage scope. |

The tests use the plan's `uplan`, `Feed`, `scripted`, `RULES_ROWS`, `rotation`, `S`, `T`, `replace`, `patch`,
`timedelta`, and the existing fake `F.serve` public routes. All values are invented. No sleep, venue request,
private financial value or real signing key is needed. Recheck fixtures after dependency merges; do not weaken
quantities, timestamp assertions or established byte digests to accommodate a different implementation.

Static expected failures against the literal proposed code: both timestamp tests expose the earlier `sampled`
value, late tick receipts remain usable, malformed IDs return ok/empty, and unflagged index churn emits a partial
price list. These are reasoned expectations only; none was executed in this preparation.

## Decision time: details to keep explicit

- Capture `frame.sampled_at` and `decision.decided_at` are different facts. A frame can be sampled at the slot;
  its decision must be stamped from the trusted clock after producing that decision. Sharing an early sampled
  time among candidates masks work by the second and third candidates.
- Keep causal history hashes and the exact existing inequality in `_universe_inputs`. Changing timestamps must
  not loosen fill delay, backdate receipt timestamps or import a future slot's inputs.
- Also cover a clock rollback during frame/chooser work. Current `paper_capture.py:167` uses
  `CAPTURE_CLOCK_ROLLBACK`; PR5's `_clock_value` import only validates a clock value, not monotonicity across calls.
  The later implementation should pin its chosen existing sanitized refusal and incomplete outcome. No valid
  decision may predate its frame. This additional case remains a test worksheet item, not a claimed passing test.
- Delayed `_replays` is a separate useful probe: it maintains held-coin state for later book requests. Work
  crossing the next scheduling boundary must not be hidden by the earlier sample; the existing missed-slot/
  incomplete-trial behavior still applies. Do not assert that work performed after a genuinely finished decision
  retroactively changes that decision's computation time. Capture timing includes more than chooser timing and
  still requires the Spec §17 measurement; a fake-clock test is not a performance result.
- On a too-late result, `CaptureOutcome.complete` must be false and the final sink line must carry the fixed
  refusal. Partial frames/decisions may remain as incomplete evidence; do not convert them into an issued result.
  Treatment of authenticated failed candidates is deliberately outside this assignment.

## Receipt boundaries and malformed listings

- The approved 1-second future **book stamp** allowance is separate from **receipt time**. Even after the
  later clock PR, receipt after slot must not become evidence available at that slot
  (`docs/pc-clock-decision-2026-11-12.md`, decision 1 and follow-up PR). The fragment includes a +1 second receipt
  so that calibration cannot accidentally relax causality. The existing 10-second book/receipt age checks remain.
- Flag/ticker reads received after slot already fail `_on_time`; retain exact-at-slot acceptance. The ±60,000 ms
  trade-time offset is an explicitly approved encoding rule, not permission to use a late-received ticker.
- The listing check should reuse the already reviewed consumer semantics in `execution/upbit_inquiry.py:171–190`:
  list of objects, each full market ID matching `[A-Z0-9]+-[A-Z0-9]+`, unique across all quote groups, then existing
  strict `market_flags` classification. A valid non-KRW market must not be mistaken for malformed data.
  Keep duplicate JSON-key/nonfinite rejection from `rules.market_flags`; do not replace it with permissive JSON parsing.
- End-to-end follow-up after reader integration: a malformed listing must leave `flags=None`, ask all previously
  needed books and produce no `vanished` rows solely from that failure (Plan `run_universe_capture:2762–2779`).
  A good empty list must still record genuine disappearance. Persist raw responses in the receipts sink in both
  cases. This does not decide the pending policy for authenticating failed candidates.

## Cumulative index: exact limit of the approved text

The existing contract fixes the index and requires reads not be silently truncated, but does not say whether
**a <=320-market read after cumulative exhaustion** makes only its unrepresentable data unavailable or ends
the bounded-format capture with a named refusal. The literal plan's comment expressly drops book/price names;
that is the finding to resolve, not evidence of approval to omit them invisibly. This is separate from the
pending PR4d history-row capacity amendment and from PR5 authenticated failed-outcome approval.

The later implementation must choose and document behavior within the existing format before adding a final
code-specific regression. Do not recycle indexes used by earlier hash-chained frames, enlarge 320, invent
per-frame index tables, truncate a current read or label partial data complete. The scratch postcondition applies
only when a frame is returned: prices are explicitly unavailable or every in-range current price is represented.

Necessary cases: new unflagged coin, new warning coin, same names at exactly320, >320 current read, already-indexed
held coin and KRW-BTC at capacity, and all new prices individually within the size/time bounds. Keep the old
mapping unchanged and verify frame decoding/history bindings. In the normal capture path a needed held/decision
coin has already appeared in the index; BTC is requested from the first slot. Do not manufacture a new held coin
fixture that violates `_needed` provenance and then call that an observed runtime path.

No code, plan implementation, test result, actual study or probability was produced by this preparation.
This is software verification preparation, not legal, tax or investment advice; the author is not a licensed adviser.
