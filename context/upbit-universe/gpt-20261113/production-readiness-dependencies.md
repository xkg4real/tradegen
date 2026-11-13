# Production-readiness dependency inventory — 2026-11-13

Read-only inventory at source `c80c56cdab946a80ae40be31432b41c881dcd5a2` (PR 4c worktree).
The parent is running frozen-source validation separately. This inventory ran no tests, application commands,
API requests, signer, arming, orders or actual owner-home reads. Parser syntax below was verified by reading source,
not by running it. No runtime/test file was edited.

## 1. Latest design sources and precedence

- `handoff/CURRENT.md:8` names the remaining production authority, durable adapter, planner, controlled coordinator,
  private setup, owner setup and prospective-study IDs. These are existing tracked tasks, not newly invented work.
- Universe rev 3 and plans remain the current first dependency: PR 4c → 4d → 4e → 5. Its spec section 3 explicitly
  leaves controlled mode and the held-position producer outside that design.
- **Newer than the November 6 runtime guides:**
  `docs/superpowers/specs/2026-11-12-controlled-launch-and-planner-design.md:4` and
  `2026-11-12-standing-deployment-design.md:4` still say “proposed” but explicitly record owner approval on November 12.
  Their merged documents are design evidence; neither their headers nor their merge prove runtime implementation.
- Controlled design section 9 (`:408`) orders universe through PR 5 → PLB code → L1 live launcher/lifecycle →
  L2 current planner → L3 standing deployment → one final code approval. Its section 3.2 also requires the separate
  held-capable source before controlled mode can be built.
- **Do not implement the original standing safety-stop sale verbatim.**
  `2026-11-12-standing-protective-hold-design.md:20` / `:33` / `:204` (A1) amends it: protective hold rules S/T/B/I/E,
  plus W for universe profiles; trigger or an uncheckable rule starts the sale; halt sells nothing and requests cancel
  of a resting protective sale. X/M/Md are owner-signed values. Owner answers and defaults are recorded in section 1.
- `docs/pc-clock-decision-2026-11-12.md` puts the separately reviewed one-second book-future allowance after universe
  PR 5 and before final code approval/freeze. Its owner pre-study clock check remains a real-PC action.
- Existing code/checklists describing the peak floor, one-day windows, immediate protective liquidation, or missing
  planner must be updated only with the implementation that changes that behavior. PLB and L1–L3 are not yet shipped.

## 2. Dependency map

```text
Universe 4c → 4d → 4e → 5 ──→ PLB implementation ──→ L1 ──→ L2 ──→ L3 + A1
                         └──→ one-second clock change ───────────────────┐
Held-source coverage contract → production authority → durable adapter ──┤
                                                                       ↓
             final deployed code/table/limit approvals + private setup
                                                                       ↓
        real-PC measurements → new preregistration → actual 48h capture
                                                                       ↓
          all-candidate evaluation → authentic review → current odds
                                                                       ↓
             current prepared object → owner arming → live use
```

Arrows express prerequisites, not permission to declare uncertain evidence complete. Development can prepare
adapters and synthetic regressions before private inputs arrive, but fake coverage, a typed dataclass, a local hash,
or an assumed signature must never satisfy the live gates.

## 3. Existing task IDs, actual gates and independent next actions

| Existing task | Current source fact / hard gate | User-independent work already within tracked scope | External or owner dependency |
| --- | --- | --- | --- |
| `launch-held-positions-1/production-authority` | `execution_launch/account_interval.py:118` refuses held positions and interval fills with `ACCOUNT_INTERVAL_EXTREMA_EVIDENCE_REQUIRED`. `ContinuousUpbitCandidateSource.__call__` at `:417` always raises `CONTINUOUS_LIVE_RISK_INTEGRATION_REQUIRED`. `execution_accounts/continuous.py:118` exposes constructible `VerifiedCoverage`; `verify_coverage` at `:281` validates shape/binding, not venue authority. | Inventory actual venue receipt/sequence guarantees, write a concrete provenance/coverage contract and threat cases; implement reviewed issuer-bound verification only when that contract is justified. Reuse the recorder, FIFO valuation, candidate reducer and gap/refusal tests. Never treat endpoint snapshots or heartbeat as interval extrema. | No merged held-source design was found among current specs. Controlled design `:110` explicitly delegates it to a separate blocker-1 design. Any new source/policy assumption or material design choice needs a concrete reviewable proposal and the user's requested approval flow. Real account/price/fill/fee/late-event coverage must subsequently be established in the owner environment. |
| `launch-continuous-guard-adapter-1` | Local commit library exists: `execution_launch/continuous_guard_commit.py:314`; it recomputes the plan, journals prepare, retains halt, advances baseline and guard heads, completes and rereads heads. It does **not** authenticate its package or publish a controller observation. `docs/continuous-guard-commit-contract.md:230` lists remaining adapter duties. | Build the production adapter against the authenticated source; bind current owner/code/limit context and exact predecessors; archive private evidence without credentials; preserve historical stops/halts; publish only after durable completion; test crash/CAS/replay/torn-row boundaries. Keep the existing library and classifier rather than rewriting completed work. | Authenticated package and independent head provenance; trusted pre/post owner context (and a timeline if it changes); original receipts/manifest; real-PC restart validation. A private reviewed re-anchor is an owner procedure, never automatic reset of history. |
| `launch-planner-provider-1` / L2 | `tools/owner/launch.py:223` refuses `prepare` without a provider (`OWNER_CURRENT_PREPARATION_INPUTS_REQUIRED`); `tools/owner/rehearsal.py:409` still returns `OwnerRuntime(coordinator)` without one. `tools/owner/planner.py` does not exist. Current preparation requires a real in-memory prepared object (`execution_launch/runner.py:363`) and fresh inputs (`coordinator.py:724`). | Implement `CurrentPlanner` from controlled design section 6 after universe+PLB interfaces settle: pinned one-plan file, current date/stake cap, receipt-checked daily bars, real comparison registry/seed, separate odds and two-phase preparation builder under the work lock. Keep every existing odds/research gate. | The design explicitly says the **owner writes and reviews the private plan file** (`controlled...:311`). Actual stake/target/horizon/model/FX/sizing input must be supplied or reviewed; the agent must not substitute the study capture for at least 250 final daily bars, invent a plan or manufacture a seed. |
| `launch-controlled-coordinator-1` / L1 | `execution_launch/coordinator.py:281` accepts only `rehearsal`. `Runner._controller_boundary` (`runner.py:274`) implements dry-adapter isolation only; the underlying controlled label is not a complete controlled launcher. `tools/owner/live.py` does not exist. | Implement the separately designed `live.py`, exact live adapter/source/state checks, single-process lock, stale-arming cleanup, current-state start/stop/cancel/exit/reconcile and restart rules. Preserve rehearsal's dry-only guarantee. Controlled design section 7 defines files/tests. | Held-capable authenticated source first. Separate owner-installed inquiry/order credentials and IP/permission setup; authentic approvals and actual Windows operational checks. Removing the mode guard alone is never completion. |
| L3 standing deployment + A1, under controlled follow-up | `tools/owner/launch.py:107` still caps a window at one day; live schedule and `standing_armed` implementation are absent. Newer specs define 7-day maximum signature periods and daily sessions; A1 changes post-stop behavior. | Implement the merged design's schedule, expiry, restart/disarm, signer/fold mirrored validation and protective-hold state machine with their specified regressions. Reconcile current line anchors and PLB/universe interfaces before a concrete task plan; do not reuse obsolete same-slot/immediate-sale rules. | Owner-reviewed final signature data, including any chosen X/M/Md. Design approval is not an actual signed standing arming. Signer changes remain subject to the explicit approved design and reviewed implementation scope. |
| `launch-private-capture-setup-1` | Rehearsal parser/guard exists (`tools/owner/rehearsal.py:352`); it requires original source documents, signed audit binding, fresh anchor and explicit independent head. It does not create/re-anchor them. | Prepare validators, redacted templates, consistency diagnostics and one-time setup instructions. Trace all evidence bindings across account audit, window/schedule, profile, terms, review and deployment. | Owner creates/inspects private account scope, raw history/fills/fees and identity/retention/exclusive-account fence evidence; supplies secure local paths. Private account data must not be pasted into GitHub/Notion/chat. |
| `e1-14-owner-setup` / `universe-code-approve` | `CurrentOwnerAuthority` (`execution_control/owner_authority.py:45`) requires genuine current signed code/head/key and refuses changed/re-written authority. Exact reviewed code and table bytes matter. | Finish all code, deployment manifest tools and precise step-by-step owner instructions before asking for final signing. Reuse existing owner key/state; do not keygen/reset or sign per intermediate PR. | Owner synchronizes final Windows tree, checks trusted signer/venv, signs code and required tables/rule/limits. Initial/loosened limits become effective on the permitted next Seoul date; a Git merge/chat approval does not substitute for these signatures. |
| `launch-prospective-study` | Current `study.py:58` is still fixed-asset; universe capture/evaluator arrives in PR 5. `_select` at `:600` intentionally uses no review verifier; it can emit review requests but is not authentic trading qualification. No new real passing strategy is established by this code inventory. | Finish universe evaluator/capture and full-family evidence review. Prepare fresh IDs, frozen program/parameters/profile/source commitments, capture tooling and checks. Recompute all candidates/cost stresses with no cherry-picking; retain negative results and `prior_attempts`. | After final code and approvals, publish a new commitment before **actual** 48-hour/300-second/577-slot observations. Owner PC must remain awake/current. Complete original evidence review and detached review approval. If no candidate qualifies, no trade; elapsed development time is not a study. |

## 4. Integration trap that must be designed before wiring

`Controller.observe` (`execution_control/controller.py:457`) already holds `journal.transaction()` when it calls
its account provider. `commit_continuous_guard` (`continuous_guard_commit.py:332`) also enters that journal
transaction. Calling the latter naively inside the current provider deadlocks/refuses re-entry.

Separately, `ContinuousAccountProvider.__call__` (`execution_accounts/baseline_bridge.py:141–177`) commits the
baseline and advances its head **without** the control journal lock. The production adapter must not reuse that
advance path and then apply the guard afterward: a published endpoint could lose the intrainterval halt/floor history.
The reviewed contract requires journal → independent heads → stores, exactly one journal transaction, and no
published observation before all effects and both heads agree. A pending prepare already blocks new entries and
preparation (`controller.py:639`, `session.py:216`); preserve those failure states through recovery.

## 5. Existing command syntax — parser-verified only, not executed

In Windows PowerShell, `$py` below means the existing repository interpreter:

```powershell
$py = ".\.venv\Scripts\python.exe"
```

These are existing offline inspection commands, with explicit placeholder files/times where required:

```powershell
& $py -X utf8 -m execution_launch.cli --template
& $py -X utf8 -m execution_launch.cli --profile "<private-profile.json>" --now "<aware-ISO-time>"
& $py -X utf8 -m tools.owner.launch export-manifest --repo "<repository-path>"
& $py -X utf8 -m tools.owner.launch --help
& $py -X utf8 -m tools.owner.rehearsal --help
& $py -X utf8 -m execution_launch.study --help
```

Sources: `execution_launch/cli.py:39`, `tools/owner/launch.py:293`, `tools/owner/rehearsal.py:412`,
`execution_launch/study.py:497`. A complete profile/manifest alone does not establish execution readiness.

Existing owner-only setup syntax (writes private state; run only after reviewed **fresh** evidence and final setup):

```powershell
& $py -X utf8 -m tools.owner.launch setup-account --state "<reviewed-anchor.json>" --reviewed-head "<reviewed-SHA256>" --state-root "<state-root>" --head-root "<independent-head-root>"
& $py -X utf8 -m tools.owner.launch setup-history --window "<future-window.json>" --state-root "<state-root>" --head-root "<independent-head-root>"
& $py -X utf8 -m tools.owner.launch export-driver --profile "<profile.json>" --program "<program.json>" --protocol "<protocol.json>" --window "<window.json>" --state-root "<state-root>" --head-root "<independent-head-root>"
```

Source: `tools/owner/launch.py:293–340`. Explicit state root must match configured `TRADEGEN_HOME`; account setup
requires a reviewed anchor no older than 30 seconds and empty stores/heads. Existing state is never automatically
adopted or overwritten. Current window limit is still one day, so these are not ready-made standing-deployment commands.

Existing study command syntax (PR 5 changes universe support; do not start a final study now):

```powershell
& $py -X utf8 -m execution_launch.study freeze --profile "<profile.json>" --draft "<new-draft.json>" --out "<empty-output-directory>"
& $py -X utf8 -m execution_launch.study capture --plan "<frozen-plan.json>" --out "<empty-capture-directory>"
& $py -X utf8 -m execution_launch.study select --plan "<frozen-plan.json>" --profile "<profile.json>" --captures "<capture-directory>" --now "<aware-ISO-time>"
```

Sources: `study.py:74–75`, `:497`, `:617`. `freeze` writes local commitment files but **does not publish** the
commitment; `capture` makes real public-data requests and waits for the actual window; `select` is offline evaluation
with review requests, not a signature. There is no existing `tools.research.study` or `tools.research.launch_study` module.

Existing real-PC clock diagnostic:

```powershell
& $py -X utf8 -m tools.clock_check
```

Source: `tools/clock_check.py:86` injects the default `KRW-BTC` symbol and delegates to the diagnostic capture parser.
This command is **not offline**: it reads the public orderbook and queries Windows time-service status. Only its
`--help` is an offline help path. It was not executed by this inventory.

Missing commands must not be advertised as runnable: `python -m tools.owner.live`, a planner launch command,
standing arming JSON, `cancel-all`/`exit` console commands and a production continuous-source setup command are
still implementation work. Existing `tools.owner.rehearsal --config <file>` is dry-only and may perform real
read-only requests after its guarded startup; it is not the eventual live launcher.

## 6. Owner actions to surface at the right time

1. **Now, without blocking universe coding:** explain that held-source completeness is the unresolved foundational
   design/evidence contract; develop the concrete proposal and source evidence rather than silently equating a
   sampled feed with complete coverage. Bring material new choices to the user's requested click approval flow.
2. **Before PLB/operational setup that depends on private state:** request only the sanitized conclusion of the
   owner's state check if its approved plan depends on an already raised floor. Never read their actual owner log
   or ask for balances/keys in a public artifact. `tools/floor_state_check.py` exists; its parser requires explicit
   private principal/floor/activation parameters with `0 < floor < principal <= activation` (`:76–95`).
3. **Before final deployment:** owner reviews the private plan/rule/profile/audit and supplies secure credentials
   locally. Existing decisions in the November 12 merged designs should not be re-asked as if absent.
4. **After all closure changes:** one final deployed code approval and required table/limit signatures; verify the
   actual effective date rather than assuming a new signature applies immediately.
5. **After actual study and qualified authentic review:** owner performs the appropriate review and arming operation
   on the real returned session/schedule data. No example ID, copied test PASS or assumed input can replace it.

The remaining KIS/OKX live collectors and multi-market comparison are separately tracked in `CURRENT.md`. Their
market display/E1/E3 adapters are not proof of complete launch evidence. The current approved first path is the
Upbit universe sequence; this inventory does not enlarge its market or leverage scope.

Software engineering inventory, not legal, tax or investment advice; no return probability was estimated here.
