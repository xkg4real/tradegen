# PR4c Task 2: Observed maximum and universe buy cap

Adds the required observed_maximum_krw to each parsed observation, verifies it again for issued observations, keeps the v1 maximum-equality refusal, and enforces recorded venue maximum on buys/sells plus authority cap on v2 buys. within_buy_cap excludes below-cap markets without blocking held-coin exits.

## Verification

RED: 1 expected TERMS_MAXIMUM_CHANGED failure. GREEN: launch_instrument_refresh 27 PASS / 0 FAIL. Controller regression was interrupted with SIGINT after concurrent source edits produced signed unarmed floor transition required and SESSION_PREPARATION_OWNER_CHANGED. Partial log is retained in terms-task-2-controller.log; no final pass result is claimed, and parent must rerun after source freeze. Final init surface instrument_terms.py debf4f2f2e095214adf60a193bac5252b4c402373bf3d5e8e039182a74e6a9d0. Parent updates reviewed call set validate_observed_order with type.

## Review and remaining work

Code and test blocks match the existing Task plan. LF preserved; diff --check clean. No changes outside assigned files, no commits or pin regeneration. No real API, key, home, electronic signature or order. Parent owns reviewed shared pins and frozen full PR regression.

## Independent review regression

Added test_order_validation_refuses_an_inflated_issued_or_renewed_observed_maximum. It covers the initial issued-rule lookup and renewed-rule lookup, first confirming an above-venue-maximum sell refuses, then inflating the frozen observation via object.__setattr__ and requiring TERMS_OBSERVATION_CHANGED. Focused result: 1 PASS / 0 FAIL / 0 NOT_RUN. Only tests/launch_instrument_refresh.py changed; runtime remains frozen. Log: terms-tamper-regression.log.
