# PR 4c Task 6 — collector and unlisted positions

Status: implementation and focused checks complete; final shared-source integration pending.

## Implemented

- Added exact collector GET routes market/all and orderbook; listing before ticker only for positive held coins.
- Unlisted holdings retain units with price zero and listing receipt time; no ticker request for those coins.
- Optional Position.unlisted marker omitted from canonical bytes when absent; provider requires exact True for zero mark.
- Added collector, provider, E1 seam and runner dust tests and updated interval fixtures/routes guards.
- All plan anchors matched by content. Initialization surface change outside functions is exactly Position.unlisted.
- Reviewed model surface: `e7807322ce6b91df9ada3724e43d64fb39f40bac328bfbcbdd0150498e6d52a2` (matches plan).

## Verification

- Task6 RED: 29 PASS, 6 FAIL. Four new collector assertions and provider TypeError failed as planned; the runner dust test additionally failed during fresh odds preparation (investigation pending stable shared code).
- Broad Task6 GREEN attempt interrupted after parent requested no signed integration while concurrent source edits continue. Its partial log is retained and is not claimed as validation.
- After Task7 changes, focused collector + interval + continuous + guards + provider: **104 PASS / 0 FAIL / 0 NOT_RUN**.
- Logs: collector-task-6-red.log, collector-task-6-green.log (interrupted), collector-task-7-green.log.
- Pending: stable runner, rehearsal, coordinator and renewal-boundary checks under parent freeze.

## Reviewed correction to the plan

The exact plan treated malformed listing rows as absence and marked holdings zero. A hermetic probe confirmed `[{}]` and `[{"market": null}]` both produced `unlisted=True`. The parent approved the narrow within-Task6 fix: validate each row's market against `[A-Z0-9]+-[A-Z0-9]+`, reject duplicate IDs, then derive absence. Other quote groups and an empty list remain valid. Refusal code is `COLLECTOR_MARKET_LIST_INVALID`.

Regression RED: 1 PASS / 1 FAIL (malformed listing incorrectly accepted). After the fix, the 5 focused modules are **106 PASS / 0 FAIL / 0 NOT_RUN**; logs `collector-listing-hardening-{red,green}.log`. E1 worker received the same payload contract so malformed E1 flags remain unknown rather than zero-valued absence. This changes only the collector function body, not a pinned initialization surface.

## Conditions

- Base main `971a5389208c85d34fdd6479c96580e9b8fcc68d`; shared worktree, no commit/stage/push by this worker.
- Offline wrappers, 19 KEYLESS variables, explicit scratch runs and matplotlib directories; existing venv only.
- No real service/API, credentials, signing, arming, owner state or order used.
- Source files remain LF. `tests/launch_account_interval.py` was CRLF at base and remains entirely CRLF.
- Scoped diff stats match with and without `--ignore-cr-at-eol`. Plain `diff --check` flags the retained CRLF terminators as whitespace; no added spaces before those terminators.
- Parent owns the reviewed renewal surface pin and final stable integration run.
