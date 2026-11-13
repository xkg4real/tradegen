# PR 4c Task 8: held-market flags and unlisted valuation

Base: `971a5389208c85d34fdd6479c96580e9b8fcc68d`.
Branch: `gpt/universe-pr4c-terms`.
Recorded: 2026-11-13T17:00:32+09:00.
Status: implemented, self-reviewed, focused tests passed; parent integration review and frozen-source checks pending.
No commit or push by this worker. Runtime files are frozen for integration.

Tests used the repository suite `tests()` wrappers, 19 KEYLESS variables, temporary state and fake transport.
No live API, actual owner state contents, credentials, signing, arming or order was used.
The test interpreter and installed dependencies were reused read-only. All edited files remain LF.

## Requirement and preflight

Source: `docs/superpowers/plans/2026-11-11-upbit-krw-universe-pr4c-terms-orders-accounts.md`, Task 8;
approved universe spec sections 11 and 15. Required PR 1/2/3 interfaces are present.
The existing shared E1 fixture had no market-list route, so the plan's insert alternative was used.
All anchors were found by content after PR 2 line shifts.

## Implemented

- Optional `Snapshot.market_flags`; omit when None from canonical hash and stored row, retain old row acceptance.
- One held-coin market-list read before ticker, outside the snapshot fail-whole path.
- Unlisted Upbit coins are not requested from ticker and contribute zero; failed listing reads yield unknown flags.
- Fixture route and tests for query order, response evidence, field validation, roundtrip and valuation.
- Current shared `execution/upbit_inquiry.py` initialization surface:
  `b84e2b291939c70ce20572f18cdf6c962a5054dbcb39f438fc0bc9be1a9d72f0`.
  Parent owns the manually reviewed pin update. Outside function bodies, changes are the json import,
  UNIVERSE_MARKET/market_flags imports and `_held_flags` signature. No endpoint scope was added.

## Reviewed corrections to the plan

1. A malformed listing such as `[{}]` previously looked like a valid absence, causing zero valuation.
   Validate the same raw JSON as a list of objects with unique complete market IDs matching
   `[A-Z0-9]+-[A-Z0-9]+` before deriving absence. Bad rows yield unknown flags and retain ticker valuation.
   Valid non-KRW quote groups and valid wider market IDs remain accepted structurally; an empty list keeps
   the planned absence behavior. The shared compliance parser and global eligibility policy are unchanged.
2. Restrict absent-marker zero valuation to Upbit. KIS and OKX retain their pricing rules even if supplied
   with a market-flags mapping. Regression covers priced and unpriced cases for both venues.
3. Necessary integration fix, authorized by parent: `execution_accounts/readiness.py` used
   `load(model.jsonable(snap))`, which includes explicit None for the new optional field and therefore fails
   canonical row validation. Change to `load(json.loads(dump(snap)))` without replacing the stored hash.
   Existing mutation detection remains; added test also mutates nested flags after construction.

## Verification

- Planned failing E1 tests: 26 PASS / 7 FAIL of 33 before implementation.
- Planned readiness failing test: 0 PASS / 1 FAIL.
- Wrong-venue scope regression, malformed listing regression and readiness canonical roundtrip each
  failed before their fix and passed afterward.
- Intermediate Task 8 E1 run: 123 PASS / 2 FAIL of 125. Both signed poll failures returned `code not signed`
  while sibling agents changed signed-source files; this log is retained and not treated as final validation.
- Readiness integration initially 11 PASS / 6 FAIL; the canonical roundtrip fix resolves them.
- Final combined pure E1 checks for Tasks 8/9: 119 PASS / 0 FAIL / 0 NOT_RUN.
- Final accounts_readiness: 18 PASS / 0 FAIL / 0 NOT_RUN.
- Parent must still run signed poll/transport integration after source freeze and run renewal guards with
  the reviewed surface pin. No full-suite completion is claimed here.

Logs in session scratch: `e1-task8-red.log`, `e1-task8-readiness-red.log`, `e1-task8-green.log`,
`e1-task8-scope-red.log`, `e1-task8-malformed-red.log`, `e1-task8-roundtrip-red.log`,
`e1-task89-final-pure.log`, `e1-task8-readiness-final.log`.

## Files

`execution/snapshot.py`, `execution/upbit_inquiry.py`, `execution/positions.py`,
`execution_accounts/readiness.py`, `tests/execution_fixtures.py`, `tests/execution_upbit.py`,
`tests/accounts_readiness.py`, `tests/execution_snapshot.py`, `tests/execution_positions.py`.

These are software tests, not measured trading probabilities or live-readiness proof.
This is not legal, tax or investment advice; the author is not a licensed adviser.
