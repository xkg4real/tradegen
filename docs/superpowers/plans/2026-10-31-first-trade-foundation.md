# First-trade foundation: five priority deliverables

The owner requested a new Notion summary in the specified account, implementation of the five most important remaining tasks, and concise ordered owner setup/signing instructions. This work starts from merged main `8cd4e833eef44ff32cd2464c3a16d689f5dc4e78` (PR #8). The existing 1,923-test baseline has 1,801 PASS, zero FAIL and 122 inherited NOT_RUN. Actual account connection, signing, activation and orders remain unperformed.

## Scope and acceptance

1. **Explicit Cloud network route.** Support the managed sidecar through a validated, explicitly supplied proxy/CA context. Retain TLS verification, `trust_env=False`, no redirects, fixed venue hosts/ports, method/path restrictions and no fallback to direct networking. Default direct behavior remains isolated from environment credentials. Validate route configuration and both E1/E3 send seams with fake HTTP. Standalone inquiry receives an explicit clock; exact raw response bytes remain private and available to the collector.
2. **Concrete account source and collector.** Use documented Upbit KRW main-pocket read-only requests as the reversible development reference. Decode exact decimal tokens, partition bounded closed-order creation windows, paginate documented paged endpoints, fetch individual order detail, preserve receipt digests and reconcile the resulting evidence through the existing provider. Missing retention/coverage, order drift, unsupported pocket transfers, ambiguous fee allocation or nonzero-flow fee semantics remain explicit refusals. Do not manufacture complete history from a short E1 summary. A narrow GET-only order-detail extension is documented and guarded; no trading method is added to E1.
3. **Versioned launch profile and policy preflight.** Parse explicit inputs strictly, bind venue/account scope/instrument terms/policy/strategy evidence, and report actionable missing values. The owner's settled loss formulas remain intact; unknown first-day/zero-profit budgets and measurement/flow conventions are not guessed. Existing sealed current owner context determines effective signed limits. Separate stable economic/provenance contract digests from ephemeral quote/rule timestamps without weakening E2 freshness checks.
4. **Prospective strategy evidence.** Preserve the frozen retrospective study and its zero passing candidates. Add a future-only, preregistered, costed and lot-aware paper validation procedure with immutable protocol/result bindings and source-review requirements. A hash establishes integrity, not independent data or authenticity. Research qualification never grants execution permission by itself; the controller's actual owner/prepared-session gates remain required. No new historical winner search or protected-holdout access occurs.
5. **Automatic orchestration and rehearsal.** Implement an explicit deterministic loop over quote/account/strategy inputs and existing controller reservation/dispatch/reconciliation/risk handling. Default operation observes; a fake transport and temporary state exercise rehearsal. Any future controlled entry requires typed qualifying evidence, exact profile/rules bindings and an actual fresh owner-prepared/armed session. Never retry an uncertain create, silently clear reservations, invent an owner event, or launch a background trader during development.

The first-market decision belongs in the profile; the current Upbit development reference is not an owner live-market selection. End-to-end rehearsal belongs to item5. Owner secure configuration and actual signatures remain separate completion conditions.

## Source boundaries and ownership

- Network agent: `execution_network/`, E1/E3 transport seams, transport-specific E1/control guard updates and tests, Cloud transport contract.
- Collector agent: `execution_accounts/collector.py`, `upbit_collector.py` as needed, narrow Upbit GET endpoint addition, collector tests and documented API evidence.
- Profile agent: `execution_launch/profile.py`, profile tests/example and contract.
- Strategy agent: `execution_launch/strategy.py`, prospective validation contract/manifest and tests. Prior `research_lab/` source and existing results remain untouched.
- Runner agent: `execution_launch/runner.py`, narrow public controller state snapshot, orchestration tests and contract.
- Root: package/CLI, shared signed/acting/runtime closure, accounts/readiness integration, new suite registration, serial tests, commits/PR/handoff and Notion page.

## Validation and reporting

- Add meaningful synthetic tests for actual failure boundaries, causal execution, exact cash/fee/lot accounting, immutable binding, pagination and uncertain-order recovery. Test runs are serial, all19 KEYLESS variables are asserted, and all state uses temporary isolated homes with real-home metadata watches.
- Run focused affected suites and required full acceptance after source integration. Never weaken an inherited guard merely to pass; add precise guarded extensions with negative controls. Preserve all original test identities/statuses except justified actual fixes. Record failures and unresolved skips honestly.
- Root may update `qa/acceptance_results.json`, README counts and this task's execution ledger only at final full verification. Existing CRLF files remain CRLF; new files use LF. Stage explicit filenames only.
- Publish a reviewable new PR, not an unapproved merge. Maintain append-only handoff IDs and code hashes. Notion progress must distinguish implementation, verification, missing owner inputs, live connectivity and actual activation; a created page is not implementation evidence.

## Actual current environment and owner steps

Current managed Cloud observations are enforced/current, but have no credential/runtime/identity bindings and do not permit venue destinations. Tool capabilities expose status/diagnostics rather than a configuration-write workflow. Configuration must use the supported owner workflow; never bypass the sidecar or request secrets in chat, Notion or GitHub.

The signer remains owner-operated Windows Terminal software. Use a reviewed copy outside the repository, compare its SHA256 and inspect the repository venv's `.pth` names; reuse existing keys and use keygen only for initial setup. The owner signs code and required tables/eligibility/limits. First or loosened limits have next-Seoul-day effectiveness and session/halt constraints. KIS authenticated inquiry needs code approval beforehand. A final session uses only the real content-derived `prepared.session_id`, with expiry/process binding and renewed preparation after changes or restart. No owner signer or active trading session is run by development.
