# Task8 late correction: contain listing JSON recursion

Date: 2026-11-13. Status: implementation complete; owned files frozen. Parent authorized the correction after the previous full run at 8137c47 completed (parent reported 2569 PASS / 0 FAIL / 135 NOT_RUN). That previous full result does not cover this later source edit; parent will commit and run the required final verification on new source.

## Change

- `execution/upbit_inquiry.py`: only `_held_flags`'s local exception clause changes from `_CONTAINED` to `(*_CONTAINED, RecursionError)`. A recursion failure from either public transport JSON parsing or local shape parsing now produces unknown held-coin flags, as the existing Task8 isolation contract requires.
- `tests/execution_upbit.py`: adds `test_deep_listing_json_keeps_the_snapshot_prices_and_amber_status`, using a 20,034-byte fake HTTP listing response with 10,000 nested lists in an ignored property. It verifies snapshot success, BTC unknown, original ticker price and NAV, ticker request, no successful listing digest, and exactly HELD_FLAGS_UNKNOWN / amber / n=1 among market alerts.
- Global `_CONTAINED`, transport, strict compliance parser, function signatures and initializer surface are unchanged. No renewal pin update is needed for this function-body-only correction.

## Evidence

1. Scratch reproduction confirmed both the transport and direct Answer paths leaked RecursionError; `market_flags` alone already contains it. See `e1-recursion-readonly-repro.py`, `.log`, and `e1-recursion-readonly-findings.md`.
2. RED: new regression through `execution_acceptance.tests()` wrapper failed with RecursionError before ticker. Log: `e1-recursion-red.log` (0 PASS / 1 FAIL).
3. GREEN: complete `execution_upbit/` and `execution_guards/` focused modules through the same suite wrappers: **40 PASS / 0 FAIL / 0 NOT_RUN**. Log: `e1-recursion-green.log`.
4. `git diff --check` passed. Final delta at this correction: 2 source/test files, 20 insertions / 1 deletion. Existing LF endings retained by the narrow patch.

All execution used the read-only Python 3.13 venv, KEYLESS variables, existing cloud skills catalog, one BLAS thread, scratch run/cache directories and temporary fixture state. Network routes were fake; no real credentials, APIs, owner state, signing, arming or orders were used. No commit or push was performed by this agent.

Self-review: the clause encloses both proven failure sites and only affects the deliberately isolated listing query. Existing malformed/empty/good listing, ticker, snapshot error and read-only guard tests all remained green. The new test checks observable snapshot/valuation/alert behavior rather than only asserting the exception tuple. No unrelated behavior or fallback was added.
