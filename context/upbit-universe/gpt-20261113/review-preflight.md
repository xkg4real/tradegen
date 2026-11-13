# PR 4c independent preflight review

Baseline: main `971a5389208c85d34fdd6479c96580e9b8fcc68d`. Working tree: `gpt/universe-pr4c-terms`.

Status: preflight only; implementation is changing in parallel, so this is not final code approval.

## Sources inspected

- Handoff `AGENTS.md`, `context/upbit-universe/pr4a-preflight.md` and inherited CURRENT/status evidence.
- Universe spec revision 3, especially sections 10, 11 and 15; plan index.
- PR 4c plan tasks 1–9 and existing runtime/guard definitions.

## Findings and dependency checks

| Item | Result | Evidence / disposition |
|---|---|---|
| Required PR 1/2/3/4b interfaces | Present | UniverseRule/flags, market/all helper, Context.universe and profile selector exist at baseline. |
| Merge ordering | Nonblocking documentation drift | Actual PR 4a followed 4b, but both prerequisites exist. |
| Initializer surfaces | Four final files | instrument_terms.py, instrument_refresh.py, execution_accounts/model.py and upbit_inquiry.py. Plan prose says five but enumerates four files; intermediate task states account for repeated changes. |
| Exact pure-call additions | Two expected additions | parse_term_receipts adds _SYMBOL.fullmatch; validate_observed_order adds type. authority_digest already permits its new v2 code calls. |
| E2 effect boundary | Planned separation preserved | New public/authenticated reader calls stay in E1 source/collector functions; they are not added to the two pinned validation entry points. Final source/diff and guard run still required. |
| IOC fixed-form compatibility | Required | GTC request body must remain byte-identical and only IOC creates add time_in_force; status/cancel handling remains separately validated. |
| Task 9 incomplete flags | Narrow correction approved by root | Planned vacuous clearing of MARKET_FLAGS on None/missing flags is wrong for held coins. Require complete held-coin coverage and no unknown class (or no held coins), with due() regression preserving prior red alerts. |
| Existing actual state | Not exercised | No keys, real owner log, network API, real home, arm or order used. No test executed by this preflight review. |

## Pending final review

- Review actual initializer diffs before root pins any new hash; do not regenerate blindly.
- Check typed v2 authority, observed-maximum tamper binding, both side notional limits, renewal refusal before head advancement.
- Review account listing evidence, thin-book age and E1 failure isolation.
- Check the actual Task 9 full-coverage regression and alert-clear path.
- Await implementation completion, focused evidence and full branch regression before final verdict.
