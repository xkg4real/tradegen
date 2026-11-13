# PR4c Task 4: Explicit universe symbol renewal

Adds boolean allow_symbol_change, rejects it for fixed profiles, preserves account/terms/contract and fork checks before modifying registry head, and replaces profile and instrument symbol together. Universe A-to-B-to-A renewal and held-coin below-cap exits are covered.

## Verification

RED: 2 expected unexpected-keyword failures; existing below-cap sell test passed. Terms/runner/coordinator regression was interrupted with SIGINT after concurrent source edits produced RUNNER_DEPENDENCY_REFUSED and dependent assertion failures. Partial log is retained in terms-task-4-green.log (historical filename, not a success claim). Parent must rerun after source freeze. Reviewed final instrument_refresh.py init surface11f9aaf16bb9528b30146a8887ec0b67a40c32baefd6fc81abd363d123539467 matches plan.

## Review and remaining work

Code and test blocks match the existing Task plan. LF preserved; diff --check clean. No changes outside assigned files, no commits or pin regeneration. No real API, key, home, electronic signature or order. Parent owns reviewed shared pins and frozen full PR regression.
