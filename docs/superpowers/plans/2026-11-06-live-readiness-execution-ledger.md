# November 6 live-readiness integration: execution record

Base: merged PR12, `21259f8d8ab76ea35c46a61df582fe5d792e916f`.
Review: [PR13](https://github.com/xkg4real/tradegen/pull/13).
Current runtime/test freeze: `eed84bc`, following the first integrated freeze
`e24b956` and its corrections. The owner approved PR12; that approval is neither
approval of PR13 nor a new application signature. This record accompanies the
[48-hour execution plan](2026-11-06-live-readiness-48h.md).

**Final frozen regression completed: 2026-11-06.**

Source `eed84bc1b519ffc8a482c8a1848507432f8d5532` completed the full Linux Cloud
run in **896.548 seconds: 2515 cases, 2380 PASS, 0 FAIL, 135 NOT_RUN**.
All 2354 inherited case IDs and statuses are unchanged; all 161 new cases passed.
The measured report confirms 19 KEYLESS inputs, isolated state and unchanged
real-home metadata. Protected frozen research has no diff against merged PR12.
This establishes offline acceptance, not live-trading readiness.

The earlier completed run on `e24b956` measured **2499 cases: 2357 PASS, 7 FAIL,
135 NOT_RUN**. Its original artifacts and the interrupted environment attempt
remain preserved below; their history is not replaced by the final pass.

## Implemented scope

| Unit | Implemented behavior at the freeze | Boundary still in force |
| --- | --- | --- |
| `launch-held-positions-1` | `execution_accounts/continuous.py` records bounded, ordered mark/fill paths, checks a separately bound coverage receipt and recomputes FIFO/fees without filesystem writes. `execution_launch/continuous_archive.py` owns immutable candidate storage; `execution_launch/account_interval.py` reconciles captures and exact boundary values. | Candidates are not live baseline authority. The production interval source remains flat-only; a fill or held coin is still refused. |
| Chronological guard follow-up | `execution_launch/continuous_guard.py` recomputes every point from raw events, binds opening/closing account components, retains effective floor/peak/halts and handles recovery and midnight ordering. | It produces a pure plan with `execution_ready=false`. The multi-store durable transaction, production authentication and restart recovery remain a documented contract. |
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
of a successful live run. The final frozen run covers these corrections; the
component history below retains the findings and earlier failures that led to them.

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
- **Renewal import and callback boundaries:** controller/session imports are
  restricted to the exact reviewed `validate_observed_order` and
  `rules_binding_matches` ports in their respective files. Neighboring imports,
  aliases, extra symbols and access to the E1 reader remain refused. Supplemental
  checks in `tests/renewal_boundaries.py` pin 45 reviewed callable bodies and
  16 initialization surfaces, including decoder hooks, model constructors and
  helper dependencies. Independent review reproduced a callback bypass; exact
  JSON-hook and trusted-callable checks were added and the final independent
  boundary review passed. These are bounded AST checks, not a proof against
  hostile Python or a replacement for signed deployment hashes.
- **Layer ownership:** the chronological reducer moved from the control package
  to `execution_launch/continuous_guard.py`. Candidate writes moved out of the
  account package into `execution_launch/continuous_archive.py`, with exact
  writer/path checks and negative controls. Renaming the pure coverage-request
  helper removed its accidental resemblance to a transport request without
  granting account code a new write or network exception.
- **Preparation through persistence:** the coordinator's actual clock and both
  input/account timestamps are checked through simulation, lock acquisition,
  renewed owner/review assessment and final content work. Changed authority,
  stale evidence, rollback, Seoul midnight, expiry or stop/close refuses issuance.
  Checks continue after append/fsync and transaction exit: if persistence itself
  finishes too late, the durable `session_prepared` row remains an inert audit
  event, but no issued session object is registered or returned. The row is not
  deleted or made recoverable. Successful completion records its actual time
  without extending expiry. Lower-level callers now provide an explicit clock
  and `positions_asof`; historical simulation remains a separate pure API.

## Verification record and limits

The inherited PR12 evidence is **2354 cases: 2219 PASS, 0 FAIL, 135 NOT_RUN**.
Those are the previous revision's results. Comparing the current case records
with `21259f8:qa/acceptance_results.json` proves all **2354 inherited case IDs
and statuses are unchanged**, with no missing IDs or status changes. All
**161 new case IDs are PASS**. The 135 skips are unchanged: 121 macro reference-
data cases, 12 Windows private-input cases, one Windows workflow case and one
Windows console API case. None establishes successful Windows execution.

| Observation | Recorded result | What it establishes |
| --- | --- | --- |
| Focused E1 execution/account-readiness run after the OKX correction | 250 PASS, 0 FAIL, 0 NOT_RUN; fake transports, KEYLESS inputs and temporary state | The examined inquiry/positions/account compatibility paths passed at that development point. It is not the later integrated branch's full result. |
| Independent renewal plus existing session run during concurrent source work | 26 cases: 25 PASS, 1 FAIL in the signed renewal-chain case; an already-started instrumented target rerun passed | The initial failure lacked instrumentation sufficient to prove a cause; source was changing. Further broad reruns stopped until freeze. The signed-chain case passes in the final frozen run; the earlier observation remains recorded. |
| Component tests and independent source review across new modules | Synthetic receipt, signature, account, clock, stream and failure fixtures; no combined success count asserted here | Negative contracts have component evidence. Fixture signatures do not establish a real owner signature, real data coverage, live performance or production persistence. |
| First full-regression attempt on the integrated freeze | Interrupted; failed environment setup, not a completed acceptance result | Catalog/workflow tests saw no installed skill root; localhost fixture sockets also received sandbox `Operation not permitted`. Original outputs were preserved. |
| Environment-corrected full regression on `e24b956` | 2499 cases: 2357 PASS, 7 FAIL, 135 NOT_RUN | Complete failed run; its seven failures are retained below with the implemented corrections. The original log/result bytes are preserved and checkout QA restored. |
| Focused held-position and boundary correction checks | 88 PASS | Component evidence for extraction, reducer/account behavior and boundaries; not a final integrated count. |
| Focused guard and final callback checks | 8 PASS, followed by 3 PASS for final hook checks | The reproduced callback bypass was corrected; independent final boundary review also passed. Runs overlap and are not summed. |
| Focused preparation correction checks | 75 PASS in affected suites, 3 PASS in final checks, and 3 PASS for post-write checks | Covers actual preparation freshness and late persistence refusal. These runs overlap and are not counts of unique tests. |
| Isolated rehearsal fixture suite | 17 PASS | Genuine test-issued registry state is isolated and restored; production registry limits are unchanged. |
| Full regression on `eed84bc1b519ffc8a482c8a1848507432f8d5532`, 2026-11-06 | 2515 cases: 2380 PASS, 0 FAIL, 135 NOT_RUN; 896.548 seconds | Complete source-frozen run; all inherited IDs/statuses unchanged, all 161 additions PASS, real-home metadata unchanged and frozen research unchanged. |

The correction-run figures are individual focused observations during integration,
not an additive test total. The final full run verifies their combined behavior
and inherited identities on the single frozen revision.

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

| Failed cases on `e24b956` | Observed failure and correction implemented before `eed84bc` |
| --- | --- |
| `compliance_store/test_code_files_is_the_import_closure` | The expected closure omitted the three new `tools/owner` module paths. Its expectation now includes the exact reviewed modules in the signing closure. |
| `control_guards/test_runtime_sources_obey_control_and_transport_boundaries` | Seven import-boundary findings across the continuous guard and changed controller/session modules. The reducer now belongs to launch; exact renewal imports and the reviewed helper/initialization/callback boundaries are checked separately. |
| `accounts_guards/test_account_sources_have_no_signing_orders_network_or_writes` | Pure helper names and candidate-archive writes triggered the older assumptions. The coverage helper was renamed and actual writes extracted to the exactly guarded launch archive; account recording/valuation remains write-free. |
| `accounts_quotes/test_only_exact_get_orderbook_route_is_allowed_before_keys_or_send` | The negative fixture expected refusal for a now-reviewed term GET. It now asserts refusal for genuinely unapproved routes while retaining the reviewed exact-route contract. |
| Three `launch_owner_rehearsal` cases: `test_transport_retry_wait_expiring_fence_prevents_second_header_and_send`, `test_unreviewed_source_document_change_refuses_before_any_request`, `test_unsigned_complete_flags_and_unknown_live_options_are_not_configuration` | All failed with `StrategyEvidenceError: STRATEGY_EVALUATION_REGISTRY_FULL` late in the aggregate run. The fixture now isolates its genuine evaluation records and restores caller state. The production cap is neither enlarged nor disabled; no failed case is skipped. |

A separate actual stale-preparation defect was identified during follow-up,
corrected and integrated with the final post-persistence issuance checks described
above. It was not one of the seven recorded full-run failures. The focused
preparation evidence does not retroactively alter that failed run. The subsequent
complete `eed84bc` run establishes the corrected revision's outcome. Original
failure identities and artifacts remain.

The completed run artifacts are `live48-20261106-full.log` and
`live48-20261106-run.json`. The repository's complete case records are
[`qa/acceptance_results.json`](../../../qa/acceptance_results.json), preserved as
CRLF. The derived [validation summary](../../../qa/live48_20261106_validation.json)
contains the measured report, per-suite and skip-module counts, all new case IDs,
the inherited-ID/status comparison, source/file hashes and earlier-run history.
The comparison and hashes received a separate read-only metadata check. No
runtime/test source changed during the final documentation update, and no broad
test run was repeated.

These public SHA256 values identify reviewed file bytes, **not Windows code
approval** or an owner signature. The existing code-approval procedure binds
the complete deployment and intended interpreter separately.

| File | SHA256 |
| --- | --- |
| `tools/signer/sign.py` | `a5a7cc359ddc053f617cb4b31c7e15d7fcf452166d3612b7900bae9cb141615e` |
| `core/compliance/kr_rules.yaml` | `f06f4728f60578131898918bd9e24a1bdf12a549d5f816e3e1c88c2ac4dd020e` |

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
The completed wrapper report and metadata comparison confirmed those checks.
This documentation task changes no runtime or test source.

No real venue/broker/data API request, credential access, actual owner signing,
arming or order placement was performed for this development work. Official
documentation research is distinct from a venue API call. Test-only synthetic
signatures and DryRun adapters do not grant real authority. QUANTGEN and the
protected frozen studies are outside this change.

## Remaining live-use gates

1. **Owner review and deployment approval.** The final full regression and
   inherited-ID audit are complete; the earlier failed-run record remains.
   Review PR13 and obtain its own merge approval. The actual
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
