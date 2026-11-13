# PR 4c Task 9: held-coin and missing-universe alerts

Base: `971a5389208c85d34fdd6479c96580e9b8fcc68d`.
Branch: `gpt/universe-pr4c-terms`.
Recorded: 2026-11-13T17:00:32+09:00.
Status: implemented, self-reviewed, focused tests passed; parent integration review and frozen-source checks pending.
No commit or push by this worker. Runtime files are frozen for integration.

Tests used the repository suite `tests()` wrappers, 19 KEYLESS variables, temporary state and fake transport.
No live API, actual owner state contents, credentials, signing, arming or order was used.
The test interpreter and installed dependencies were reused read-only. All edited files remain LF.

## Requirement and preflight

Source: `docs/superpowers/plans/2026-11-11-upbit-krw-universe-pr4c-terms-orders-accounts.md`, Task 9;
approved universe spec section 15. Depends on Task 8 and existing approved-rule/context interfaces.

## Implemented

- New MARKET_FLAGS and UNIVERSE kinds, four exact planned catalogue entries and the reviewed catalogue pin.
- Red held-unlisted and held-warning counts; amber unknown flags.
- Amber missing universe snapshot from 09:45 KST only while an approved Upbit rule is active.
- Each poll combines universe alerts and evaluated pairs with the existing alert persistence flow.
- The new poll test exercises both raising the amber row and a subsequent clear, proving that its evaluated
  pair reaches `due()` rather than merely checking that a new raw alert can be written.

## Reviewed corrections to the plan

1. The planned evaluated condition considered a missing flags mapping complete because it used an empty
   dictionary fallback. A reproduced in-memory sequence raised red alerts and then erroneously cleared both
   on a legacy snapshot with `market_flags=None`. Require every positive holding to have a known flag before
   clearing, or no positive holdings. None/empty/partial/unknown input preserves prior red alerts.
   The regression follows persisted rows through multiple polls and `due()` until a complete read clears them.
2. Alert counts refer only to actual positive holdings. Ignore flags for unheld or zero-balance coins.
   A partial mapping's missing held coins count as unknown. A legacy None mapping means no listing read:
   it fabricates no new flag alert and cannot clear prior red alerts.
3. The plan omitted updating the old exact `evaluated()` expected set for a flat Upbit snapshot.
   Add exactly MARKET_FLAGS to that expected set, preserving the exact-set assertion.

## Verification

- Planned new/changed tests before implementation: 40 PASS / 6 FAIL of 46.
- Two new coverage/count corrections reproduced 0 PASS / 2 FAIL against the planned implementation.
- Final combined pure E1 checks for Tasks 8/9: 119 PASS / 0 FAIL / 0 NOT_RUN, including exact catalogue pin,
  threshold time, prior-red retention, count scope and existing text-leak scans.
- Signed poll integration awaits the parent's global source freeze. The extended two-poll test is present
  but its final frozen-source result is not claimed yet. No full-suite run was made by this worker.

Logs in session scratch: `e1-task9-red.log`, `e1-task9-correction-red.log`, `e1-task89-final-pure.log`.

## Files

`execution/checks.py`, `execution/poll.py`, `tests/execution_checks.py`, `tests/execution_poll.py`.

These are software tests, not measured trading probabilities or live-readiness proof.
This is not legal, tax or investment advice; the author is not a licensed adviser.
