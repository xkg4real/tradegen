# Account evidence connection and exploratory strategy research

The owner approved PR #6/#7 merges and requested account-data connection work, owner setup preparation, broad quantitative strategy evaluation and an academic-style PDF on 2026-10-31. Both PRs are merged; this branch starts from main `c5459a2`.

## Deliverables and boundaries

1. Add exact, explicitly scoped account evidence and a reconciled provider for the E2 controller. Require complete history/fees/flows, current valuation and explicit spendable quote currency. E1's floating-point, bounded first-page summaries cannot be relabeled complete execution evidence.
2. Add sanitized read-only connection/readiness tooling and a name-only environment configuration manifest. No credential value, actual account order, owner signing or activation is performed by development. Current Cloud readiness has no credential/runtime/identity binding, venue domains are not permitted, and the inherited direct-only E1 transport needs a reviewed Cloud proxy route before live connectivity can be certified. Record each limit rather than treating an injected test probe as a real connection.
3. Extend signed code closure and acting/runtime guards for `execution_accounts`. Code-hash changes require the owner's later review and signature. Bind buy capacity to the actual settled quote currency; KRW-converted cash of another currency cannot fund an order silently.
4. Freeze a finite strategy catalogue, selected source hashes, chronological phases, costs and statistical procedure before candidate performance is computed. The separate strategy protocol governs research. Preserve every candidate result and selection rule. Previously studied prices permit exploratory internal out-of-sample evidence only, not new independent confirmation.
5. Produce reproducible research results, diagnostics, figures, sources and a Korean academic-style PDF with English abstract. Clearly distinguish economic hypotheses, statistical evidence, daily marked returns, FIFO realized accounting and live feasibility. Do not manufacture a winning strategy or a profit guarantee.
6. Test synthetic economic invariants and execution/account safety boundaries serially under KEYLESS and temporary homes; run required integration/full regression after final runtime edits. Do not change frozen studies or protected holdouts. Record failures, fixes, actual skips and source hashes honestly.
7. Push named-file commits, open a reviewable PR for the new work and update the append-only handoff. Earlier approvals cover PR #6/#7 only; new PRs need their own approval.

## Work ownership

- Account evidence/provider: `execution_accounts/model.py`, `provider.py`, account provider tests and contract document; narrow quote-currency controller correction and its fixtures.
- Connection/readiness: `execution_accounts/readiness.py`, `cli.py`, readiness tests and owner connection runbook.
- Research data: fixed cache inventory/manifest, read-only loader and data-integrity tests.
- Research protocol/inference: preregistered computation plan, finite-grid protocol, multiplicity/bootstrap/HAC routines and synthetic inference tests.
- Research engine: causal candidate generation, self-financing costed backtest, selection/report runner and synthetic execution tests.
- Paper: verified bibliography, reproducible figures, LaTeX/PDF build and readable report from actual results.
- Root: merges, shared closure/guards/runners, serial test orchestration, source/data freeze, performance run authorization, review, commits, PR and handoff.

## Actual owner-side prerequisites

The available managed-environment tool exposes status/diagnostics only, with no configuration-write workflow. Credentials must be registered through secure owner configuration, never pasted into chat. Merely setting an environment variable name does not establish authentication or account eligibility. The real signer and account activation remain owner actions; a prepared instruction or test signature is not their completion.

First-day/zero-profit loss budgets and any other unresolved policy measurements remain explicit missing inputs. The owner's already settled conditions are preserved; new limits are not guessed. Research inputs are public historical caches and contain no private owner financial parameters.
