# PR4c Task 1: terms authority v2

Implemented prescribed v2 rule-bound authority, exact query symbol derivation, split market refusal codes, optional read-time symbol. Fixed v1 authority digest remains pinned and identical.

- Preflight: dependencies present; plan merge-order narrative differs, with both 4a and 4b on main. No semantic anchor conflicts.
- RED: 4 expected failures (missing UniverseTermsAuthority and changed refusal code).
- GREEN: 26 PASS / 0 FAIL / 0 NOT_RUN in isolated launch_instrument_refresh suite.
- Reviewed init surface: 460adbdc092e4da47bccfefab259ea873ae2bc80cfec64c7e4233bfe7a07e2df, matching plan. Parent owns pin update and parse_term_receipts call whitelist addition _SYMBOL.fullmatch.
- Code matches task blocks; runtime/tests preserve LF. No actual API, key, signing or order.
- Global guard integration and full PR regression are pending.
