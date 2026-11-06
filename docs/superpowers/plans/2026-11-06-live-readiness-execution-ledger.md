# November 6 live-readiness integration: execution record

Base: merged PR12, `21259f8d8ab76ea35c46a61df582fe5d792e916f`.
Review: [PR13](https://github.com/xkg4real/tradegen/pull/13).
First integrated runtime/test freeze: `e24b956`, following `c72c9b8` and
`250face`; corrections are now in progress. The owner approved PR12; that approval is neither approval of PR13
nor a new application signature. This record accompanies the
[48-hour execution plan](2026-11-06-live-readiness-48h.md).

**FINAL_REGRESSION_PENDING**

The completed full regression on `e24b956`, with its environment corrected,
measured **2499 cases: 2357 PASS, 7 FAIL, 135 NOT_RUN**. This is a failed
integration run, not final acceptance. Its artifacts are preserved, and source/
test corrections are in progress. A new freeze and final regression remain
pending. Replace this marker only after inspecting that completed report,
inherited case identities, failures/skips, protected-home metadata and
frozen-source checks. Neither component passes nor the restored earlier QA file
establish that the new revision passes.

## Implemented scope

| Unit | Implemented behavior at the freeze | Boundary still in force |
| --- | --- | --- |
| `launch-held-positions-1` | `execution_accounts/continuous.py` records bounded, ordered mark/fill paths, checks a separately bound coverage receipt, recomputes FIFO/fees and archives immutable candidates. `execution_launch/account_interval.py` reconciles these with account captures and exact boundary values. | Candidates are not live baseline authority. The production interval source remains flat-only; a fill or held coin is still refused. |
| Chronological guard follow-up | `execution_control/continuous_guard.py` recomputes every point from raw events, binds opening/closing account components, retains effective floor/peak/halts and handles recovery and midnight ordering. | It produces a pure plan with `execution_ready=false`. The multi-store durable transaction, production authentication and restart recovery remain a documented contract. |
| `launch-instrument-refresh-1` | `execution_accounts/instrument_terms.py`, `execution_launch/instrument_refresh.py` and the fixed Upbit inquiry helpers issue fresh observations from the two reviewed GET routes. Runner/session/controller integration admits unchanged-contract renewal without changing session authority. | No timestamp relabelling, altered economics, guessed constraints or KIS/OKX renewal. Actual account-to-key identity and source-document authority still require review. |
| `launch-controlled-coordinator-1` | `tools/owner/launch.py` provides explicit baseline/history setup, unsigned driver/deployment export and a process-local console. Coordinator/Runner retain issued preparation, expose bounded lifecycle diagnostics and preserve exact pending renewals on transient application failure. | The shipped coordinator still refuses `controlled`. No helper signs, arms, repairs a baseline or restores a prepared session from JSON. |
| Standalone owner rehearsal | `tools/owner/rehearsal.py` composes the existing read-only flat-account source with exact DryRun adapters. Signed private audit/document bindings and current request guards precede E1 reads; retry and pacing paths retain those guards. | This is an owner-run rehearsal, not automatic trading. A current planner provider is still absent from the standalone composition, and actual Windows/source evidence has not been exercised. |
| `launch-authenticated-selection-1` | `execution_launch/study_review.py` recomputes the complete registered family and authenticates current detached source reviews. `study.py`, `review_request.py`, `review_auth.py` and the external signer bind every candidate's original bytes and computed result into schema 2 family commitments. | Numerical eligibility is not owner/source approval. Authenticated selection still leaves implementation and execution readiness false; no actual strategy passed in this work. |
| `launch-market-readiness-1` | The market audit separates viewing, inquiry, execution codecs, research and complete account evidence. OKX no longer invents a USDC mark from the supplied USDT rate; actual USDC holdings remain visible and unpriced exposure refuses valuation. | No independent USDC price source, new venue execution path or missing fee/FX/lot contract was invented. KIS viewing and KIS/OKX building blocks do not establish complete automated launch support. |
| `rules-review-1122/closeout` | The narrow Korbit/DigitalX naming/source ambiguity was documented and the domestic row's source references updated. | No matching, permission, treatment or review-deadline expansion. Full renewal remains open: 25 rows retain November 22 and 22 retain November 23 deadlines. New table bytes require owner approval. |

Detailed contracts and acceptance obligations are in
[continuous candidates](../../continuous-price-candidates.md),
[guard commit ordering](../../continuous-guard-commit-contract.md),
[instrument renewal](../../instrument-term-renewal.md),
[owner operations](../../owner-runtime-operations.md),
[standalone rehearsal](../../standalone-owner-rehearsal.md),
[authenticated selection](../../authenticated-study-selection.md),
[market readiness](../../remaining-market-readiness-2026-11-06.md), and
[the rule-source closeout](../../../research_notes/Korean%20resident%20trading%20venue%20legality/review_closeout_2026-11-06.md).

## Independent review corrections

Review found substantive trust-boundary defects; these were corrected in source
and represented by negative/boundary tests rather than accepted as limitations
of a successful live run. This list records implemented corrections, not a claim
that the pending full regression has passed.

- **Unbacked stablecoin valuation:** the USDT conversion input no longer prices
  USDC. Positive USDC balances, including locked balances and either account
  pocket, are retained while aggregate/live valuation refuses without a real
  supported mark. Zero balance does not manufacture an exposure. The inquiry
  signature is unchanged; account diagnostics may remain connected while their
  account-evidence/execution flags remain false.
- **Initial instrument ceiling and source issuance:** an initial observed rule
  snapshot must match an observation issued for its known authority, even before
  the first renewal. Maximum notional is checked at the controller boundary for
  both buys and sells. Constructing a source registers its authority without I/O;
  saved snapshots under it cannot become authenticated by restarting or editing
  `asof`. The legacy unknown-source caller contract remains explicitly separate.
- **Renewal chain and lifecycle:** mutated predecessor roots cannot be inherited
  without validation. Issuance registries are synchronized; stale/replayed/forked
  observations refuse. A transient Runner application failure retains the exact
  already-issued renewal for retry instead of issuing from an obsolete profile.
  Freshness still expires normally. Explicit renewal after stop or close keeps
  the stop/close latches and does not restart entries or extend preparation.
- **Shutdown reporting:** bounded disarm reports a pending durable write when
  the work lock is busy. Local journal kill and owner-log disarm are separate
  outcomes. EOF/close reports the actual worker state; it does not claim venue
  cancellation, liquidation or completed shutdown while work is outstanding.
- **Whole-family study integrity:** every signed selection request binds the
  complete original family, including failed candidates. Editing a former winner
  into failure and omitting its review cannot select a different candidate using
  old signatures. Candidate-only schema 1 reviews are not silently upgraded.
- **Chronological account/risk binding:** equal aggregate endpoint equity cannot
  substitute different cash or holdings and hide a loss. The reducer binds full
  FIFO/account components, original capture timing, stream continuity and raw
  event order; threshold crossing, recovery or midnight cannot erase an earlier
  peak-floor breach or permanent halt. Source coverage and durable enforcement
  are still separate unimplemented production obligations.
- **Current read authority:** rehearsal requests recheck current owner/source/
  implementation authority before each attempt, including retries and the two
  term GETs. Fence expiry during verification, pacing or response handling
  refuses and discards the result. One fresh authority observation is shared
  only within a single request assessment; there is no positive authority cache
  across requests. Private exception text is not promoted into public status.

## Verification record and limits

The inherited PR12 evidence is **2354 cases: 2219 PASS, 0 FAIL, 135 NOT_RUN**.
Those are the previous revision's results. All **2354 inherited case identities
are expected to remain present** in this revision; the final case-ID comparison
is pending. Additions must not hide deletions or renames. Existing Windows and
reference-data skips must be reported by cause rather than relabelled as passes.

| Observation | Recorded result | What it establishes |
| --- | --- | --- |
| Focused E1 execution/account-readiness run after the OKX correction | 250 PASS, 0 FAIL, 0 NOT_RUN; fake transports, KEYLESS inputs and temporary state | The examined inquiry/positions/account compatibility paths passed at that development point. It is not the later integrated branch's full result. |
| Independent renewal plus existing session run during concurrent source work | 26 cases: 25 PASS, 1 FAIL in the signed renewal-chain case; an already-started instrumented target rerun passed | The first failure was retained. Its initial failure lacked instrumentation sufficient to prove a cause; source was changing. Final frozen execution must resolve it. Further broad reruns were stopped until freeze. |
| Component tests and independent source review across new modules | Synthetic receipt, signature, account, clock, stream and failure fixtures; no combined success count asserted here | Negative contracts have component evidence. Fixture signatures do not establish a real owner signature, real data coverage, live performance or production persistence. |
| First full-regression attempt on the integrated freeze | Interrupted; failed environment setup, not a completed acceptance result | Catalog/workflow tests saw no installed skill root; localhost fixture sockets also received sandbox `Operation not permitted`. Original outputs were preserved. |
| Environment-corrected full regression on `e24b956` | 2499 cases: 2357 PASS, 7 FAIL, 135 NOT_RUN | Complete failed run; the seven failures below require correction and renewed verification. The original log/result bytes are preserved and checkout QA restored. |
| New freeze after integration corrections | **FINAL_REGRESSION_PENDING** | Corrections are in progress. No new full-run result or final acceptance count is asserted. |

The interrupted attempt is retained outside the checkout as
`live48-20261106-environment-attempt-full.log` and
`live48-20261106-environment-attempt-partial-record.json`. Its wrapper restores
the prior QA file on interruption/failure; a preserved partial-record file is
not evidence of a newly completed test run. Do not overwrite these artifacts or
report the attempt as passed.

The environment investigation found identical `config.py` bytes in the previous
and new worktrees. Neither relied on a copied `.claude/skills` directory. The
previous successful run used the separately installed catalogue selected by
`NEXTGEN_SKILLS_ROOT`; its absence in the first invocation caused the empty
catalogue. The installed dependency at revision
`cb0f3aadffed6d1089db4b224162c964368baa46` was present, with 74 index entries,
74 skill directories and 12 workflow files. This required explicit environment
setup, not a weakened catalogue test or source fallback. The corrected invocation
also permits local fixture sockets while venue/data transports remain fake.

The completed `e24b956` failure evidence is preserved separately as
`live48-20261106-e24b956-full.log` and
`live48-20261106-e24b956-partial-record.json`. Despite the wrapper's
`partial-record` filename, this particular JSON contains the completed 2499-case
run; its observed status counts are the failed-run counts above. The checkout's
QA file was restored after failure and must not be mistaken for this run's
result. Neither preserved attempt is overwritten by correction work.

| Failed cases on `e24b956` | Observed failure and assigned correction scope |
| --- | --- |
| `compliance_store/test_code_files_is_the_import_closure` | The expected closure omitted the three new `tools/owner` module paths. Reconcile the exact reviewed source closure and its regression expectation. |
| `control_guards/test_runtime_sources_obey_control_and_transport_boundaries` | Seven import-boundary findings across the new continuous guard and changed controller/session modules. Review the exact dependencies and narrowly reconcile the static boundary rules. |
| `accounts_guards/test_account_sources_have_no_signing_orders_network_or_writes` | The continuous candidate helper names and explicit candidate-archive write triggered the older static assumptions. Reconcile the bounded archive/helper contract without allowing arbitrary account-source effects. |
| `accounts_quotes/test_only_exact_get_orderbook_route_is_allowed_before_keys_or_send` | The original negative-route fixture expected refusal for a GET now explicitly supported by the new term source. Update the exact allowlist assertion while retaining refusal of unapproved routes, methods and query shapes. |
| Three `launch_owner_rehearsal` cases: `test_transport_retry_wait_expiring_fence_prevents_second_header_and_send`, `test_unreviewed_source_document_change_refuses_before_any_request`, `test_unsigned_complete_flags_and_unknown_live_options_are_not_configuration` | All failed with `StrategyEvidenceError: STRATEGY_EVALUATION_REGISTRY_FULL` late in the aggregate run. Isolate test-issued registry state without enlarging or disabling the production cap. These are three failures, not skipped cases. |

A separate actual stale-preparation defect was identified during follow-up and
is being corrected in an isolated worktree. It is not one of the seven recorded
full-run failures and is not yet counted as fixed or validated in this record.
Assigned work and likely explanations do not convert any failed case to PASS;
retain the original case identities and prove the corrections on the new freeze.

Before closing this record, record that freeze's final source SHA, total/PASS/
FAIL/NOT_RUN counts, elapsed time, artifact locations, inherited case-ID
comparison, skip reasons, real-home metadata check and frozen-research diff.
Do not reuse the `e24b956` run as proof of changed source or publish its counts
as final acceptance.

## Required test isolation

All 19 credential variables must be explicitly set to the literal `<unset>`
for the full runner:

```text
KIS_APP_KEY KIS_APP_SECRET KIS_ACCOUNT_8 KIS_ACCOUNT_PD
UPBIT_ACCESS_KEY UPBIT_SECRET_KEY
OKX_API_KEY OKX_API_SECRET OKX_API_PASSPHRASE
OPENDART_API_KEY KRX_API_KEY FMP_API_KEY ANTHROPIC_API_KEY
GS_CLIENT_ID GS_CLIENT_SECRET FINVIZ_API_KEY
ALPACA_API_KEY ALPACA_SECRET_KEY FXMACRODATA_API_KEY
```

Use an explicit temporary `TRADEGEN_HOME`, temporary plotting/cache locations
where required, the provisioned `NEXTGEN_SKILLS_ROOT`, and fake transports.
Do not redirect the user's actual home or copy real owner logs/keys into a
fixture. The full wrapper checks that source/tests are committed and frozen,
that no real owner public key was introduced in the Cloud checkout, that the
two frozen research paths have no diff, and that real-home metadata is unchanged.
Those configured checks become evidence only after their completed results are
inspected. This documentation task changes no runtime or test source.

No real venue/broker/data API request, credential access, actual owner signing,
arming or order placement was performed for this development work. Official
documentation research is distinct from a venue API call. Test-only synthetic
signatures and DryRun adapters do not grant real authority. QUANTGEN and the
protected frozen studies are outside this change.

## Remaining live-use gates

1. **Final integration and owner review.** Correct the observed integration
   failures and stale-preparation defect, freeze again, and complete the new full
   regression and inherited-ID audit. Review PR13 and obtain its own merge approval. The actual
   Windows interpreter, final source closure, external signer copy and changed
   rules table then need the existing owner review/signature procedure. Chat
   approval and an older code signature do not sign this deployment.
2. **Real Windows and source composition.** Establish current baseline/history
   heads, original source documents, account/key identity, venue constraints and
   source-review bindings privately. Measure actual collection, authority-check,
   quote and slot timing. Synthetic pacing results do not prove the PC meets the
   unchanged deadlines. The standalone rehearsal still needs a reviewed current
   planner composition before its preparation command can succeed.
3. **Held-position completeness and durable enforcement.** Establish an actual
   authenticated coverage authority for all relevant price/account changes. Then
   implement and review the guard/controller/baseline independent-head commit,
   concurrent-transition checks, permanent-halt persistence and crash/restart
   recovery contract. A recorder, heartbeat, local hash, endpoint match or pure
   guard plan cannot supply these obligations. Controlled mode remains refused.
4. **Fresh study and current authenticated reviews.** Freeze and publish the new
   capture-bound code/protocol before observations begin. Complete the actual
   registered duration and full candidate family, retain failures, recompute
   costs/statistics and obtain current source/implementation review. A new
   48-hour capture started after development began cannot also finish within the
   same 48-hour delivery target. Shortening further requires a justified new
   protocol, not fabricated history. No eligible strategy or return is promised.
5. **Unchanged floor and economic feasibility.** The principal/high-watermark
   floor, daily rules and recovery cutoff remain. Equality with the floor is not
   itself a breach, but positive fees/spread can make a positive opening stake
   inadmissible; sizing may still return `STUCK_AT_START`. There is no fee waiver,
   floor relaxation, reset peak or guaranteed recovery. Coding completion alone
   cannot establish a feasible first order under the unchanged owner policy.
6. **Other markets and legal closeout.** KIS/OKX full account evidence, instrument
   economics, FX, research and launch contracts remain separate work, as listed
   in the market audit. Complete unresolved primary-source/eligibility questions
   before proposing any rule-row deadline renewal. Current narrow-path progress
   does not authorize broader products or account operations.

The 48-hour target therefore describes an engineering delivery objective. It
does not waive elapsed observation time, owner actions, source trust, loss limits
or the remaining production integration. A completed mock test suite would not
by itself make today's live trading available.

This is engineering and research documentation, not legal, tax or investment
advice; the author is not a licensed adviser.
