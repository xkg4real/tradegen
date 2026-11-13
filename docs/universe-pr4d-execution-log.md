# Upbit universe PR 4d execution record

Historical checkpoint: this document describes its recorded revision. The later v3 integration and current validation are in [lossless-history-execution-log.md](lossless-history-execution-log.md).

Date: 2026-11-13 (Asia/Seoul). Base: merged PR33, `7d256f9090bb4de593bf496b010a9753ae5508fd`.
Scope: the existing approved PR4d plan, Tasks 1–4. The additional capacity amendment has not been approved or implemented.

## Implementation

- Task1 (`d34395b`): immutable universe bars and carried chooser inputs, single-decision recomputation,
  optional canonical frame fields, and fixed-frame/slot-data golden checks. Independent review complete;
  committed-head focused check: 31 PASS, 0 FAIL, 0 NOT_RUN.
- Task2 (`f3e6ac3`): universe IOC construction, v2 account/market records, incremental chooser state and
  the original first size fallback. Independent review complete; focused check: 53 PASS, 0 FAIL, 0 NOT_RUN.
- Task3: trade-symbol/tick validation, carried prior-decision checks, bookless bars and two-slot switching.
- Task4: exact v2 parsing, replay and restored chooser/price/allow state after independent-head verification.
- Tasks3 and 4 each received independent review; no additional blocking finding was found.
- Root integrated the six planned Task3/4 regressions plus one malformed-v2 regression with 17 cases.
  The latter distinguishes row validation from an independent-head-only refusal.

The combined focused run of the four affected/guard modules passed 60/60 in 7.445 seconds. Source fingerprint
`1aac24a84d06886bdc132fc36bbab4428978f366dc86f8d8b22edba3886c9cfe` and actual-home metadata were unchanged.
Planned RED runs are retained separately; their expected failures are not final regression failures.
The original implementation's full suite at `ea4e2a4925922ce468208c89020881cb01a08403` completed:
**2,719 total; 2,584 PASS, 0 FAIL, 135 NOT_RUN**, in 1,105.243 seconds. All 2,705 PR4c baseline IDs remain;
the 14 added tests pass. The same 135 NOT_RUN cases remain (121 macro reference/owner/freeze prerequisites and
14 Windows-specific checks), and none is counted as passed. The source fingerprint and actual-home metadata
stayed unchanged. This result does not resolve the known capacity contract gap or validate a later amendment.
Focused counts overlap and must not be added together.
The five boundary guard modules also passed 81/81 in 11.953 seconds on the same frozen fingerprint, with no
source or actual-home metadata change. The delivered commit's Python/YAML fingerprint is checked against these runs.

Both live-history files retain their original CRLF; the driver, new test module and registry remain LF.
Existing MODULES entries, including clock and floor-state checks, remain. Fixed-window golden values are unchanged.
No dependency, boundary pin, frozen research, signed rule table or real owner state was changed.

## Known capacity gap: final merge blocked

The approved original plan drops flags/tickers and clears the allow-list when a row is too large. That does not
prove its unconditional statement that no admissible row is refused for size. The implementation keeps the existing
generic fail-closed append refusal. Two explanatory docstrings acknowledge this unresolved specification gap;
they do not amend the specification.

A synthetic reproduction exercised the actual collector/provider and actual `LiveHistory.record_slot`:

- 1,500 validated unlisted held positions; 1,522 fake collector requests.
- A parser-admitted book with a 131,072-byte raw body.
- Actual row after the original first fallback: **279,312 bytes**, exceeding the **262,144-byte** cap.
- Result: `HISTORY_STORE_RECORD_INVALID` before any journal, independent-head or in-memory slot/chooser change.
- The probe passes by confirming this known refusal and preservation; it does not mean capacity is fixed.

The separate owner decision proposes a second book-unavailable fallback and an explicit finite admission/refusal
contract while retaining every holding. Neither is in this branch. No cap was raised, holding pruned, or new capacity
diagnostic introduced. The original Tasks2–4 can be reviewed independently; final PR4d merge remains on hold until
the capacity contract is resolved. Any later runtime amendment requires review and its own final verification.

## Operational boundary

All recorded tests use 19 KEYLESS variable names, fake sources and isolated state. No live API, credential read,
actual signature, arming or order was performed. Caller-supplied account and mark facts in these fixtures do not
authenticate a production interval source. PR4e, PR5, PLB and operational integration remain separate work.
Software tests are not a qualifying strategy study or a return probability. This is not legal, tax or investment
advice; the implementing agent is not a licensed adviser.
