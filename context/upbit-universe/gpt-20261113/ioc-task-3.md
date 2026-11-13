# Universe PR 4c Task 3 — IOC orders

Status: implemented and self-reviewed; owned files frozen for parent integration.
Base: main `971a5389208c85d34fdd6479c96580e9b8fcc68d`.
Task source: `docs/superpowers/plans/2026-11-11-upbit-krw-universe-pr4c-terms-orders-accounts.md`, Task 3.
Spec: approved revision 3, section 11. No design deviation.

## Preflight and implementation

- All Task 3 code anchors and PR 4b profile/RULE prerequisites exist on the base.
- Upbit accepts `gtc` and `ioc`; KIS stays `day`, OKX stays `gtc`.
- Universe Upbit profiles require IOC; fixed Upbit profiles retain GTC.
- Only an IOC create body gains `time_in_force=ioc`; the fixed GTC body remains byte-identical.
- An IOC create response lacking the matching field is `unknown(identity_mismatch)`.
- Create/cancel acknowledgments remain nonterminal; terminal cancellation comes from status reconciliation.
- Planned runtime replacement blocks and tests were applied unchanged. No controller, signer or boundary pin was edited.

## Verification

- RED: all three planned test cases failed for the exact expected pre-implementation reasons.
- Control model: 7 PASS, 0 FAIL.
- Order codecs: 30 PASS, 0 FAIL, including the new IOC body/identity/partial-cancel/status test.
- Launch profile: 19 PASS, 0 FAIL, including fixed-profile digest preservation and universe/fixed TIF checks.
- Lifecycle: 4 PASS, 1 FAIL (`SESSION_PREPARATION_OWNER_CHANGED`) while other signed runtime files were concurrently edited. This is not counted as a passing suite; parent must rerun on frozen source.
- Renewal guards: 1 PASS, 2 FAIL while other PR 4c surface/call changes await the parent's reviewed pin update. Diagnostic list names only `upbit_inquiry.py`, `instrument_terms.py`, account `model.py`, and `instrument_refresh.py`, none of Task 3's surfaces.
- Task 3 model/profile initialization surface hashes still match their pins exactly; no Task 3 pin update is required.
- `git diff --check` passed. All six edited files remain LF-only; ordinary and `--ignore-cr-at-eol` stats match.

Logs in the session scratch directory:

- `ioc-red-control.log`, `ioc-red-profile.log`
- `ioc-green-control.log`, `ioc-green-profile.log`, `ioc-green-renewal.log`
- `ioc-focus.py`: focused suite wrapper with 19 KEYLESS variables, temporary runs/cache paths and the existing Cloud skill catalogue.

## Ownership and remaining checks

Files: `execution_control/model.py`, `execution_launch/profile.py`, `execution_orders/upbit.py`,
`tests/control_model.py`, `tests/orders_codecs.py`, `tests/launch_profile.py`.

No staging, commit, push, full-suite run, live API call, real signing, arming or order was performed.
Parent owns stable lifecycle/renewal/full regression and delivery. This software implementation establishes no real strategy probability or return. It is not legal, tax or investment advice; the author is not a licensed advisor.
