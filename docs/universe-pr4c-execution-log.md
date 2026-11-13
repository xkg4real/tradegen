# Upbit universe PR 4c execution record

Date: 2026-11-13 (Asia/Seoul). Base: `971a5389208c85d34fdd6479c96580e9b8fcc68d`.

This record follows the approved universe revision 3 and
`docs/superpowers/plans/2026-11-11-upbit-krw-universe-pr4c-terms-orders-accounts.md`.
Implementation and software tests are separate from an actual strategy study, owner signatures and arming.

## Workflow and status

The Claude handoff of 2026-11-12 stopped before producing PR 4c code. Its six preceding universe PRs are merged.
The new branch starts from main, with four disjoint implementation assignments and an independent reviewer.
The root agent owns the shared renewal boundary pins and final integration. No dependency was added.

| Task | Implementation | Final integration status |
|---|---|---|
| 1 | v2 terms authority, read-time market, receipt binding; v1 digest retained | Pending frozen-source run |
| 2 | observed maximum, buy-only universe cap, reparsed observation comparison | Pending frozen-source run |
| 3 | Upbit IOC model/profile/request/response; fixed GTC request retained | Pending frozen-source run |
| 4 | explicit cross-coin renewal, all refusal checks before head advancement | Pending frozen-source run |
| 5 | exclusive v1/v2 rehearsal audit authority and profile binding | Pending frozen-source run |
| 6 | listed-market evidence, unlisted position marker and zero valuation | Pending frozen-source run |
| 7 | stale-trade fallback to fresh best bid within the capture time budget | Pending frozen-source run |
| 8 | optional E1 flag encoding, held-market lookup and Upbit-only zero valuation | Pending frozen-source run |
| 9 | held-coin alerts, complete-read clearing and 09:45 snapshot alert | Pending frozen-source run |
| 10 | independent review, boundary checks, full suite and PR delivery | In progress |

## Preflight and reviewed adjustments

- PR 1/2/3/4b interfaces and code anchors exist. Actual merge order was 4b then 4a; both are present.
- Existing Python LF and `tests/launch_account_interval.py` CRLF are preserved byte-for-byte in style.
  The latter is an exception missing from the plan's general line-ending note.
- Four initializer surfaces change: terms, renewal, account model and Upbit inquiry. The exact pure-call
  additions are `_SYMBOL.fullmatch` in the terms parser and `type` in order-limit validation. The network
  readers remain outside the two reviewed E2 validation entry points. Pins were checked against actual diffs.
- No new MODULES registration is needed. Existing signed rule tables and frozen research remain untouched.
- Task 7's existing stale-trade test is renamed to include the stale-book fallback; its original assertion
  remains, with the new fallback cases. Test inventory comparison records the rename rather than a removed test.
- Commit attribution identifies this GPT implementation honestly; the historical plan's Claude execution
  footer is not presented as evidence that Claude ran this change.

## Integration defects found and corrected

1. The planned alert-clear condition accepted a missing or incomplete flag mapping as a complete read.
   Clearing now requires a known class for each positive holding, or no positive holdings. Tests exercise
   prior red alerts through missing, incomplete, unknown and complete follow-up observations.
2. The planned unlisted valuation branch also affected other venues. The exception now applies only to Upbit;
   KIS and OKX retain their missing-price refusal.
3. A malformed market list such as a missing/null market field could be interpreted as authoritative absence.
   The new consumers reject malformed or duplicate market IDs. The collector refuses the capture; E1 retains
   ticker valuation and reports unknown flags. Valid non-KRW markets and an empty valid list remain supported.
4. `readiness.inquire_once` used a generic dataclass encoding that explicitly included the new optional `None`
   field. That broke canonical loading of existing snapshots. It now round-trips the snapshot's own canonical
   dump, retaining hash checks and nested-mutation rejection. This necessary compatibility fix adds
   `execution_accounts/readiness.py` to the plan's production file list.
5. A mutable nested holding could replace a valid quantity with positive infinity, which the new zero-value
   skip would otherwise hide. The unlisted branch retains finite, nonnegative quantity validation.
6. A deeply nested but small JSON market-list response raised `RecursionError` before the ticker read and
   escaped the listing-only failure path. The held-flag reader now contains this decoder failure locally,
   preserving ticker valuation and reporting unknown flags. The global transport exception policy is unchanged.
   An actual fake-HTTP regression reproduces the failure and verifies the retained prices and amber alert.

## Verification protocol

All tests use isolated state, 19 KEYLESS variable names, fake data/transport and one OpenBLAS thread.
Focused implementation checks and their expected RED results are retained in the handoff evidence.
Some signed integration checks ran while sibling agents changed the signed source closure; their refusals
are preserved as diagnostic runs, not final regression evidence. Final verification freezes all source and
tests, checks source fingerprints before/after, compares actual-home metadata without reading its contents,
and preserves the original tracked acceptance-results file. PASS, FAIL and NOT_RUN remain separate.

First frozen run at `8137c4712b164c120ec8063e50dc3e05b741c23f`: 2,704 tests, 2,569 PASS, 0 FAIL,
135 NOT_RUN in 1,094.567 seconds. The source fingerprint and actual-home metadata stayed unchanged. The 135
NOT_RUN entries comprise 121 macro reference/owner/freeze prerequisites and 14 Windows-specific checks.
The 2,672 baseline IDs are retained apart from the documented stale-book test rename; 32 new tests plus that
renamed test all pass. The separate guard run passed 81/81.

The decoder-isolation issue above was reproduced after that run. Its narrow fix and new regression passed the
40-test Upbit/guard check. A new frozen full run is required before delivery; the first full result is not
presented as validation of the later runtime change.

## Remaining after this PR

PR 4d connects the universe driver/history; PR 4e connects the coordinator, renewal and allow-list;
PR 5 supplies the universe evaluator and study tools. PLB and the approved clock allowance follow the universe
work. Production authority, durable guard integration, planner and controlled operation remain distinct tasks.
The final owner code approval occurs after all required code is merged, followed by a new review/history window.
An intermediate merge does not authorize live execution or require signing each intermediate head.

No live exchange query, credential read, owner signature, arm or order was performed. No strategy success rate
was measured. This is software engineering evidence, not legal, tax or investment advice.
