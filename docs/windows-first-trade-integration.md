# Windows first-trade integration plan

**Status: design, not launcher implementation.** Reviewed against TRADEGEN source
`af46688`; validation results are recorded separately in the execution ledger. This document performs
no network request, signing, activation or order. Existing libraries are building
blocks; they do not establish authentic sources or a completed Windows launcher.

Windows PC, delegated market selection, exceptional-day budgets and preservation
of the existing principal/peak floors are settled decisions. Do not ask the owner
to choose them again. Monetary values and account identifiers remain in the
private profile. The explicit recovery condition is 22:00 Asia/Seoul against the
same day's opening marked equity. Recovery is checked, never guaranteed.

## Scope and actual operator inputs

The complete collector/evaluator/fixed-driver path currently supports one Upbit
KRW spot account. KIS Live supplies public-market viewing through its separate
approval-key/WebSocket flow; it does not provide private account evidence, an
automatic-order launcher or expanded strategy-validation coverage. Internal
research must select a qualifying strategy and instrument; no current real
prospective passing candidate is established. Additional venue launch support
requires implementation and validation, not another owner market-choice prompt.

The owner must supply or perform, in their own reviewed Windows environment:

- The actual checkout, pinned interpreter, private state location and account
  binding; securely configured inquiry/order credentials and applicable network
  restrictions. Never put credential values or account numbers in chat/documents.
- Authentic source/access and account-history evidence, including original funding
  and inventory/history coverage. Engineering defines the interfaces below; the
  owner is not expected to fabricate their records or write those adapters.
- Review/merge approval for the final code, trusted signer setup, genuine code,
  tables, eligibility and effective-limit approvals, actual research/implementation
  review, then authorization of the actual prepared session. First/looser limits
  retain D12's next-Seoul-date rule; no approval or historical date is assumed.

KIS Live market viewing does not require the app's electronic owner signature.
Authenticated KIS **account** inquiry through E1 does require signed code. Neither
operation establishes permission to trade.

## Implementation still needed

| Integration | Required interface and behavior | Reuse |
|---|---|---|
| Windows private-input loader | Explicit bounded regular files; reject links/junctions, alternate-stream/device paths, credential/state traversal and overwrite. Parse strict schemas without echoing values. | Implemented: `execution_launch/private_input.py`, dispatched by `cli._read_profile` and `workflow._read_file` on `os.name == "nt"` only, so `cli --profile`, every `workflow` command and `deployment compare` run on Windows. Win32 lexical rules, lstat of every component (reparse points, offline and cloud-recall attributes refuse), canonical-path equality (8.3 aliases, SUBST and network drives refuse) and an opened-handle identity check; no override. The POSIX readers and the pure profile/protocol/program/review parsers are unchanged. |
| Authentic account interval producer | `source(previous: BaselineState, now) -> BaselineFrame(interval, accounts)` over prefetched, authenticated, complete account evidence. `interval.source_sha256` binds `content_digest(accounts)`; retain originals and independent coverage evidence. | Implemented, flat-only: `execution_launch/account_interval.py` `UpbitIntervalSource`. `collect(collector_source, previous=..., anchor=..., coverage=..., clock=..., trade_fees=...)` runs one fenced `collect_upbit` capture before the tick time is chosen and stages one frame (`StagedInterval`: the frame, the original receipts, the manifest and the real observation instant); `__call__(previous, now)` returns that frame without I/O when it extends `previous` or is its committed endpoint and the observation is not after `now`, so same-tick redelivery advances the head once. The only extrema the evidence proves are a flat interval's (no position at the endpoint, no fill or external flow at or after the previous endpoint), so `minimum == maximum == equity`; a held position, any fill inside the interval (a round trip included) or any flow refuses `ACCOUNT_INTERVAL_EXTREMA_EVIDENCE_REQUIRED` / `ACCOUNT_INTERVAL_EXTERNAL_FLOW_UNSUPPORTED`, which stops the chain after a first fill (owner open item: a reviewed intra-interval price path is needed for held intervals). A pending 22:00 cutoff or the next Seoul midnight is bracketed only by a capture whose first balance read is at or before the boundary and whose fenced observation is at or after it; the evidence is then stamped at the boundary instant (rows, digests, server time and manifest unchanged); a late first read is `ACCOUNT_INTERVAL_BOUNDARY_MISSED`, an in-window capture that ends early is `ACCOUNT_INTERVAL_BOUNDARY_NOT_BRACKETED`, and nothing is ever relabelled. The midnight capture hands the collector a module-private opening baseline for its structural self-check only; it is never staged or exported and is discarded before the bridge runs the reducer's own `risk_baseline` (guarded by a test). Frames live in memory only; a restart, a gap over 30 s or a missed boundary refuses until a fresh capture or a reviewed re-anchor. |
| Independent latest-head adapter | `read() -> digest`; `compare_and_set(old, new) -> True` only after durable authorized advancement. Use a separately protected authority with an explicit recovery procedure, not a second writable file beside the checkpoint. Initialization is an explicit reviewed step. | Implemented: `execution_launch/baseline_head.py` `BaselineHead(root=..., name=..., chain=...)` with `CheckpointChain(store)`. One digest-plus-sequence record under `<root>/<name>/` (`head.json`, `head.lock`, `head.tmp` only while a write is in flight) in an operator-provisioned, link-free, drive-letter folder that neither contains nor lies inside `TRADEGEN_HOME` or the checkout (recommended `%LOCALAPPDATA%\TRADEGEN-head`), with its own OS byte lock, fsync and atomic replace. `compare_and_set` advances only to the digest the chain already holds durably as the committed direct successor of the current head with the next sequence; `initialize_reviewed_head(digest)` is the only creator, adopts a seed-shaped checkpoint once and has no runtime caller (guard-pinned). Crash between checkpoint and head, rollback of either root alone, mutation, links, concurrent CAS and day-opening/peak/loss resets refuse without repair. A coherent rollback of both roots is refused only by the 30 s freshness rules (reducer maximum interval, `risk_baseline`) and the fixed driver's 30 s account-anchor rule; no frame is retained durably in this phase. Recovery is the owner-performed reviewed re-anchor in `docs/account-baseline-integration.md`. The history row instantiates its own head with its own name and chain check. |
| Durable live-history/anchor adapter | `history_provider(DecisionInput) -> HistoryFrame`; `history_verifier(frame, identity, now) -> HistoryReceipt` only after checking original receipts, coverage and immutable per-slot account anchor. Preserve history and anchor identity across restart. | Implemented: `execution_launch/live_history.py` `LiveHistory(program, protocol, profile, window=..., root=state_root(), clock=..., trusted_head=BaselineHead(...))`. An append-only, hash-chained journal `<TRADEGEN_HOME>/execution-history/<window digest>/history.jsonl` (row 1 binds the fixed driver identity; each later row holds one slot's original orderbook receipt bytes and the account anchor taken from the supplied `AccountObservation`, stamped with the trusted clock at recording); the bar and the decision are re-derived from the receipt, the slot grid, the recording time and the program at recording and at every restart replay, never stored. The journal head is a `BaselineHead` of its own name whose chain is `live_history.HistoryChain(root, window)` (GENESIS over an empty journal at the reviewed `initialize_reviewed_head(GENESIS)`, the fsynced tail row at every advance). `bind(driver)` requires the issued driver's callables to be exactly `h.provider` / `h.verifier` and its identity to match the constructor inputs, creates the journal only before `window.start` over a head at GENESIS, otherwise replays every row from the original bytes and requires the last row to equal the head. `record_slot(book, account)` records the next index only, inside `[slot, slot + 10 s]`, quote age at most 10 s, account age at most 30 s and never newer than sampling; append, fsync, `compare_and_set`, readback, then memory. The verifier accepts a tick only inside the latest recorded slot's window, with `sampled_at <= now <= trusted clock <= slot + 10 s`, a frame digest equal to the recorded frame, and the head and the file size unchanged; `verified_at` is the recording time. A missed slot, a rewritten row or anchor (with or without re-hashing), a dropped tail, a torn tail, a changed code hash, a second writer, a crash between append and head advance, or a window that has already started refuses with a fixed `HISTORY_*` code; nothing is backfilled, repaired or reseeded. `sample_prefetched_book` and `parse_orderbook` supply the quote rules; `PaperCapture` stays the research capture. Neither a prospective label nor matching hashes authenticates a source: the E1 quote source, the injected clock and the account observation remain trusted deployment dependencies. |
| Current owner authority adapter | `authority_provider(now) -> ReviewAuthority(context, public_key_raw, observed_at)`. Use the actual trusted `owner.load_context(now, positions, session_id=...)` and current PEM reader; retain true observation time and detect key/log/context changes. | Implemented: `execution_control/owner_authority.py` `CurrentOwnerAuthority(clock=...)`. Every call runs `owner.load_context(now, Positions(equity_krw=1.0))` with no session id and reads the current PEM; `observed_at` is that `now`, and the adapter's own clock read after the load must lie within 30 s of it. The first signed observation pins (key fingerprint, D14 code hash, log head); a rotated or replaced key, another code hash, a lost approval, a log that is not a verified extension, a late observation or a clock rollback refuses, and after the pin the first refusal latches until a new instance is wired. `ReviewAuthority` now lives in that module and `review_auth.py` re-exports it; `ReviewVerifiers` is unchanged. Never synthesizes a Context or a receipt. |
| Windows coordinator and cancellable scheduler | Own exactly one account provider, serialized ticks, prefetched snapshots, actual prepared-object registry, bounded work, stop handling, cutoff monitoring and sanitized status. Explicit operation mode; no connect/arm on import or startup. | Implemented, rehearsal only: `execution_launch/coordinator.py` `Coordinator(mode="rehearsal", profile=..., evidence=..., driver=..., implementation_verifier=..., adapters={"upbit": DryRunAdapter(...)}, account_source=..., account_prefetch=..., trusted_head=..., quote_source=..., window=..., bar_seconds=..., monitor_until=..., clock=..., history=..., monitor_seconds=10, prefetch_lead_seconds=3, boundary_lead_seconds=2)` builds and owns one `ContinuousAccountProvider`, `Journal`, `Controller` and `Runner` over the explicit adapters; construction creates no file and reads no clock. `run()` works on the caller's thread over a lazily merged schedule of slot (prefetch lead before each slot), monitor (every `monitor_seconds`) and boundary (each Seoul midnight and, with a recovery condition, each 22:00) items; a `CancellableTimer` waits on the close event in steps of at most one second and re-reads the injected wall clock, so a suspend shows up as skipped deadlines (a late slot is never run, moved or re-run; a missed boundary is reported, never fabricated) followed by a gap unit that reconciles before the next decision. Every unit loads the checkpoint behind the trusted head, runs the account prefetch, picks its time only after all fetching, publishes one immutable frame that every provider call in the unit redelivers (one head advance per unit), then observes risk and reconciles; a slot unit also reads the book before the slot, samples it at the slot, records it with `history.record_slot` and feeds `Runner.run` one prefetched timestamp inside `[slot, slot + 10 s]`. One work lock serializes units with the explicit `cancel`, `submit_exit` (available after `stop`) and `prepare` (the actual `PreparedSession` is kept and served by identity); `stop()` ends strategy slots while monitoring continues through the cutoff, `close(timeout)` ends the schedule and is bounded by the dependencies' own timeouts. `status()` is an immutable record of fixed codes, counts and instants that keeps the account-step failure apart from risk and order state. A boundary capture is attempted once at its lead and must last longer than the lead to span the boundary; `prefetch_lead_seconds` caps at 8 s and the book must arrive by the slot, so a slower account collection loses the slot while monitoring continues. `compose(profile_path, program_path, protocol_path, capture_path, review_path, evaluated_at=..., window=..., clock=..., head_root=...)` is the owned wiring: the private-input loader, the capture re-evaluated at the original evaluator time, `make_fixed_driver` with the `LiveHistory` callables, `LiveHistory.bind` (over a history head the operator initialized to GENESIS, named `history_head_name(window)`), `ReviewVerifiers` over `CurrentOwnerAuthority` on the same clock, and the `EvidencePackage`. `"controlled"` is refused while the interval producer is flat-only (a filled entry would stop the account chain); `AuthenticatedTransport` stays a later authorized controlled deployment. |

The interval producer is substantive engineering: account polls alone do not
provide a complete interval's extrema, per-fill fees, transfer coverage, lifetime
high or first-trading-day history. The current collector also requires an external
quiescent-account fence and reviewed identity/retention evidence. If those cannot
be established during activity, implement a reviewed archival/event integration
or refuse; do not replace the requirements with booleans.

Use `BaselineConventions` with the reviewed daily-loss/external-flow conventions,
bounded interval length and explicit `recovery_cutoff_seconds=79200`. Initialize
with `initialize_account_baseline(conventions, anchor, accounts, now=...)` and
separately seed the approved state/head. On first/previous-zero-profit days the
source must provide an actual exact 22:00 boundary; midnight also requires its
true opening boundary. A late balance cannot be relabelled as either boundary.
Retain historical daily loss, lifetime peak and cutoff proof; do not migrate or
reinitialize an existing checkpoint to discard history. Current implementation
supports known zero external flows, not a guessed deposit/withdrawal adjustment.

## Composition and order

1. **Complete and test adapters with invented data first.** Implement the six
   integration rows, freeze the Windows source/dependency closure and run Windows
   acceptance. Independently finish qualifying prospective research. Missing
   credentials or approvals need not delay this engineering, but cannot be treated
   as present in a readiness result.
2. **Receive reviewed artifacts privately.** Load final profile, rules, program,
   frozen protocol/registration, original capture and its actually recomputed
   evaluator result. Bind the genuine source provenance and complete candidate
   family. Keep original evaluator timestamps when reproducing a signed evidence
   digest; arbitrary re-evaluation times may produce a different binding.
3. **Construct the actual fixed driver and export its identity.** Call
   `make_fixed_driver(program, protocol, profile, window=..., history_provider=...,
   history_verifier=..., program_artifact=actual_installed_bytes)`. This constructs
   the registered callback without invoking history sources. Export
   `dataclasses.asdict(describe_fixed_driver(driver))`. Distinguish its fixed-source
   `deployment_code_sha256` from the complete D14 deployment `code_hash`.
4. **Owner approvals.** In the reviewed external signer, approve final Windows
   code and required tables/eligibility/limits. Verify actual limit effectiveness.
   After real research/source/implementation review, the owner uses
   `review-approve` on the unsigned request, actual driver identity and audit
   artifact. Code approval must precede that detached review signature. Keep the
   running integration and supplied dependencies unchanged; any changed binding
   requires matching evidence/review rather than editing a receipt.
5. **Wire authenticated reviews and prepare.** Construct
   `ReviewVerifiers(document, clock=clock, authority_provider=authority_provider,
   approved_history_provider=history_provider,
   approved_history_verifier=history_verifier)`. Pass its `source` callback into
   `EvidencePackage(protocol=..., result=..., review_verifier=...)`. Call
   `prepare_launch_session(profile=..., evidence=..., driver=...,
   implementation_verifier=verifiers.implementation, journal=..., selected_plan=...,
   inputs=..., positions=..., now=..., selection_seed_hex=..., expires_at=...)`
   with real current reconciled inputs and the original selection seed. Preparation
   writes its existing journal event; it does not sign or arm.
6. **Retain the actual session while the owner reviews it.** Show the returned
   `launch.prepared.session_id` and bound inputs. Only the owner performs the
   corresponding activation. Keep a process-local lookup returning that exact
   `PreparedSession` object; deserialization is not valid preparation. Refresh
   data and verify that review, rules, session and owner state remain effective
   after the human interaction. Expiry means fresh preparation, not clock editing.
7. **Compose the selected mode explicitly.** Construct
   `ContinuousAccountProvider(source=..., store=..., trusted_head=...)`; install
   the exact same callable object in `Controller(journal=..., account_provider=...,
   policy=risk_policy(profile), adapters=..., session_provider=...)` and
   `Runner(profile=..., quote_provider=..., account_provider=..., evidence=...,
   driver=..., implementation_verifier=verifiers.implementation, mode=...,
   controller=..., launch_session=launch, isolated_state_root=...)`.
   Rehearsal uses exact DryRunAdapters and isolated state. Controlled transport is
   a separate explicit operator action after actual readiness; this plan provides
   no live command or default activation.

## Tick timing, monitoring and stop behavior

- Prefetch authentic account evidence and `E1UpbitQuoteSource(...).read()` before
  choosing the runner timestamp. Convert the received book with
  `to_runner_quote(book, now=...)`. For a scheduled strategy slot, the book must
  have arrived by that slot; sample it with its real receipt and sampling times.
  Do not stamp a request that finishes later with an earlier tick time.
- Publish one immutable decision frame and account endpoint for a tick. Controller
  observation, Runner observation, reservation, dispatch and reconciliation may
  call `account_provider(now)` repeatedly. Redeliver the identical interval/accounts
  for that endpoint: no new sequence or second head advancement, and no changed
  content under an old interval digest. Serialize coordinator access.
- Authenticate the HistoryFrame/AccountAnchor before permitting the decision.
  Preserve the prior causal decision. Quote age is at most 10 seconds and account
  age at most 30 seconds; the fixed driver also has a 10-second execution-slot
  window. Receipt verification cannot occur after the supplied tick timestamp.
  Missing/stale slots refuse rather than being backfilled as prospective.
- Use `Runner.run(timestamps, max_steps=..., should_stop=...)` only with a genuinely
  cancellable external iterator. It provides no timer or worker itself. Run
  independent account/risk monitoring through cutoff even when strategy ticks are
  absent or stopped; serialize `Controller.observe(now=...)` with other control
  operations. Provider failure blocks work but may occur before a daily-stop
  snapshot is written, so retain source-failure status separately.
- Cancel the waiting iterator on stop, stop producing ticks and call `Runner.stop()`.
  This does not cancel an exchange order. Display outstanding/unknown orders and
  expose reviewed explicit cancellation/reducing-exit handling. Never retry an
  uncertain create; reconcile it. After restart, restore baseline/head/history and
  reconcile orders, then obtain fresh preparation before new entries. Windows
  suspend/resume is a data-gap/reconciliation event, not proof of missed recovery.

## Acceptance before an owner-operated trial

- Windows loader refuses symlinks/junctions, hardlinks, device/alternate-stream
  paths, oversized/duplicate-key files and unsafe destinations; diagnostics omit
  private values. Pinned interpreter and final D14 manifest match the signer.
- Complete synthetic account intervals reconcile cash, FIFO fees, cumulative and
  day profits; wrong scope, changed duplicate, missing fee/flow coverage or invented
  endpoint extrema refuse. Repeated same-tick calls advance the head once only.
- Crash between checkpoint and head advancement refuses on restart. Rollback,
  mutation, concurrent CAS failure and day-opening/peak/loss reset all refuse.
- Authentic-boundary fixtures cover 21:59:59, exactly 22:00 and afterward; stale
  pre-cutoff snapshots cannot extend permission. Recovery equality passes; missing
  proof or shortfall blocks; historical loss and daily stops survive recovery and
  restart. Principal/HWM floors and prior-loss-day zero allowance remain unchanged.
- Rewritten history/anchors, late books, future receipts, replaced history callbacks,
  stale/rotated owner authority and forged/copied review/prepared objects refuse.
  A reserved entry cannot dispatch across the cutoff without current valid evidence.
- Dry-run integration covers partial fills, cancel acknowledgment versus confirmed
  cancellation, unknown-create reconciliation, restart, deduplication and explicit
  exits after a stop. Stop while awaiting a timer or provider terminates boundedly;
  simulated Windows suspend/resume cannot send or fabricate a missed slot.
- KIS display remains isolated: market-data subscription creates no account bundle,
  source-review receipt, session approval or order capability.

These are required acceptance cases, not results claimed by this design. Passing
software tests is distinct from a qualifying real prospective strategy or actual
owner authorization. This software is not legal, tax or investment advice and is
not a licensed adviser.
