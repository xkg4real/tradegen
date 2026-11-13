# Universe PR 4d — Task 1

Status: implemented, self-reviewed and frozen for independent review.
Base: merged PR #33, `7d256f9090bb4de593bf496b010a9753ae5508fd`.
Plan: `docs/superpowers/plans/2026-11-11-upbit-krw-universe-pr4d-driver-history.md`, Task 1.

## Changes

- Added immutable `UniverseBar` and `ChooserInputs` records in the fixed driver.
- Added `chooser_decision`, which recomputes one decision from carried inputs and maps invalid inputs to the specified refusal code.
- Added optional `HistoryFrame.universe_sha256` and `chooser_inputs`, omitted from the canonical encoding while `None`.
- Added the planned chooser fixture/test and fixed-frame/row golden test.
- Registered `launch_universe_history` while preserving every existing suite entry, including floor-state and clock checks.
- No Task 2 or row-capacity amendment was implemented.

## Test-first evidence

RED (`task1-red.log`, `task1-red-summary.json`): both planned tests failed for exactly the expected missing `ChooserInputs` import and missing `HistoryFrame.universe_sha256` attribute. Source and real-home metadata remained unchanged during the run.

GREEN (`task1-green.log`, `task1-green-summary.json`, `task1-green-rows.json`): **31 PASS, 0 FAIL, 0 NOT_RUN** across the universe-history, fixed live-history and fixed-driver modules. The run used 19 KEYLESS inputs and isolated state, lasted 3.388 seconds, and reported `source_unchanged=true` and `real_homes_unchanged=true`.

The fixed golden hashes remained:

- Frame: `59a151ab1b66133c71c030384df91a391178417f9249ec8a34a00558d4e16587`
- Slot data: `1354351db76d3a43b7e7ed508ae77fd98e3c22698cc70fefa1168c2b80c8bde8`

After GREEN, only the MODULES tuple's appended item was wrapped onto its own line to keep new lines within 120 characters; syntax was checked and runtime/test behavior did not change. Final file hashes are in `task1-files.json`.

## Self-review and byte preservation

- Every runtime addition and both new test blocks match the plan exactly.
- `tests/launch_live_history.py` already used CRLF on the merged base. Its complete original byte prefix was preserved and the new test appended using CRLF. This follows the repository's byte-preservation rule and the parent instruction, instead of the stale plan command requiring all files to be LF.
- Driver, new universe-history test and acceptance registry remain LF-only.
- Ordinary diff stats and `--ignore-cr-at-eol` stats matched; CRLF-aware whitespace check passed using the one-command `git -c core.whitespace=cr-at-eol diff --check` setting.
- No persistent Git configuration, boundary pin, dependency or existing source file outside the four assigned files was changed.

No staging, commit, push, live API, real credentials, actual owner signing, arming or order was performed. The full suite and independent review remain parent-owned. These are software fixture results, not evidence of a profitable or live-approved strategy. This is not legal, tax or investment advice; the author is not a licensed advisor.
