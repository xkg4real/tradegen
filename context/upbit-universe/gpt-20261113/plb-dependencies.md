# PLB dependency preflight — 2026-11-13

Read-only source/spec inspection at `c80c56cdab946a80ae40be31432b41c881dcd5a2` in
`/workspace/tradegen-universe-1113`. This is dependency evidence, **not an implementation plan**.
No application/test edits, test execution, repository imports, venue requests, private owner-state reads,
signing, arming or orders were performed. Only this scratch document was written.

References below use repo-relative paths at that commit. `PLB` means
`docs/superpowers/specs/2026-11-11-principal-loss-budget-design.md`.
`Handoff` means `/workspace/tradegen-handoff-1113`.

## Approval and sequencing already established

- PLB header line 5 still says proposed, but explicitly says merging its PR constitutes approval; line 7
  adopts the recommended defaults of §12.2 unless changed in that PR. PR18 is merged at
  `42a595f0e5599bf47da6bcfb94878c227303e4d7` (local commit inspected; Handoff `LEDGER.md:146`).
  The universe spec also recognizes approval. **O1–O16 are not sixteen outstanding questions.**
- PLB §12.5, line 704: “its plan is written against that main” after universe PR5. Handoff
  `CURRENT.md:57` and `context/upbit-universe/universe-impl-status.md:27` confirm “Universe first”.
  PR4d/4e/5 are absent from the inspected source; their proposed interfaces are dependencies, not working code.
- The read-only check already landed as PR23 (`0962e94`; Handoff `LEDGER.md:147–148`). Do not reimplement it.
  PLB implementation docs/example JSON belong with the runtime change, not before it (PLB §12.5, line 704).
- Final signing is once after universe, PLB and the approved clock change, not after each PR
  (Handoff `CURRENT.md:57–58`; `universe-impl-status.md:48`). The clock change follows PR5's shared `_book`
  extraction and precedes final code approval (`docs/pc-clock-decision-2026-11-12.md:3–5,98`).
  Source merge, design approval, electronic code approval, review approval and session arming remain distinct.

## Approved behavior to preserve

| Contract | Exact approved clauses |
|---|---|
| Required budget and one floor | PLB §§2.1, 3.1–3.2: `C = W0 - LB` below activation, `0 < LB < W0`, whole-KRW `C`; no legacy mode or implicit zero. `RiskPolicy` and protocol additions have no defaults. |
| Entry protection | §§2.5, 4.1; O1/O3/O8: below `A`, signed and effective floors must equal `C`; cash after pending buys, new buy and fees must be at least the governing floor. Equality admits. No extra rounding reserve. |
| Live/paper parity | §§4.2, 12.5 line 712: use `max(cash - C, 0)` for sizing in every regime; change all fixed/universe/benchmark paths, with required `cash_floor_quote` and both evaluator revisions bumped. |
| Preparation | §4.3 and O16: `floor_safe`; fixed profile also has stake ≤ equity and flat holdings; universe instead has stake ≤ `min(W0, settled trading-account cash)`. Remainders are not cash. |
| Windows and state | §6.1, O2/O6: first-bar cash may be ≥ `C`; owner must avoid surplus above `W0` at the first anchor. No deposits, withdrawals or rebase of loss history. |
| Halts | §6.3, O10: owner-log halt blocks buys across journals; retry a previously failed system-halt write, in its own reviewable commit. No un-halt, automatic liquidation or new journal reset. |
| Activation | §§2.4, 12.2 O4/O5: existing post-activation formula remains; owner separately signs `L = W0` when state check first shows `H >= A`. This stops new preparations until a later post-activation spec; an already armed crossing session can continue. |
| Dust, daily rules and mirrors | §5, O9/O11/O12/O13: existing daily/22:00 rules unchanged; no daily-budget/LB coupling or sell margin; dust risk accepted and disclosed; research mirror updated. |
| Other defaults | O7 adds no cumulative-loosening mechanism; O15 adds no pre-risk inside/outside-session floor comparison. O14 is conditional on actual state, below. |

`core/odds`, `core/compliance` and signer code remain unchanged (PLB §§1.2, 1.4, 8).
The cash protection is conditional on §4.6; above activation it is not a general floor guarantee.
PLB §7.1 gives a no-edge bound `LB / (T - W0 + LB)`, not a measured success probability or a target-date forecast.

## Owner evidence and actions still needed

The parent has already requested whether the owner ran the state check and its fixed S1–S12 codes.
That reply is pending. No amounts, personal paths, keys, log contents or account identifiers are needed here.

| Dependency | Why it cannot be assumed |
|---|---|
| Step-0 result for the intended operating home | PLB §9.3 step 0: before PLB implementation starts. Tool availability and an earlier `--check OK` do not establish the S1–S12 state. §§9.1/10.1 explicitly require confirmation. |
| Conditional relaxation scope | O14 and §§8.1/10.2: add an owner-console relaxation command only if step 0 finds journal floor above `C` with no halt. Do not assume that case or build it preemptively. This is state-dependent scope, not a new floor-policy choice. |
| Halt / activation / stranded arming | §9.1: S2 or S3 halt is a stop, not migration; S4 at/above activation prohibits adopting `L=C` on that history; S8 armed after its process ended requires separate reviewed recovery outside PLB. Never hand-edit/reset logs. |
| Private parameters and anchor | §§3.1–3.2, 6.1, 9.3: owner sets private `LB`, `A`, `T`, policy version/source; intended anchor floor is `C`. S10 surplus and S11 equity below the governing floor require the documented owner route. No actual values inferred or recorded here. |
| Final signature/order sequence | §9.2: keep runtime stopped until anchor gates pass; code-approve before lowering `limit_set`; verify effective floor on a later Seoul date. §9.3: fresh study/review, candidate gate → setup → seeded gate within the anchor freshness window; then prepare, arm, S12 before runner start. |
| Extra date change when relaxation applies | §10.2: lower limit on D; earliest eligible new-code pending observation D+1; relaxation only on a later Seoul date. No amount-less placeholder signature substitutes for this. |
| New prospective evidence | §§7.3–7.4, 12.4: prior profile/policy/protocol/driver/review/session/guard artifacts become stale. Current workflow calls for a fresh 48-hour capture, then evaluation/review; this is not a guarantee of qualification or a universal code minimum. Date wait may overlap capture. |
| Universe table and later activation act | §12.5 line 705 requires new `universe_rule` venues-table approval after code approval. O5's activation tightening remains a later owner action, not already signed by spec approval. |

`tools/floor_state_check.py:1–31,60–61` emits relations only. Its `--gate` does **not** gate S1, S5, S8 or S9;
those rows still need the §9.1 procedure. A plain exit 0 means readable state, not adoption readiness.
S12 is checked by the gate only when a session is supplied. The state check was not run in this Cloud inspection.

## Source interfaces that the later plan must remap

| Current surface | Dependency / affected contract |
|---|---|
| `execution_control/risk.py:58,167,276` | `RiskPolicy`, validation and below-activation formula still have the old peak floor. Ratchet, post-activation arm, strict breach and daily behavior stay intact. |
| `execution_control/controller.py:409,469,568,627` | `_snapshot_risk`, existing `approve_floor_relaxation`, `_capacity`, `_authorize`; cash and pending-fee amounts already exist. New agreement/owner-halt reasons and cash admission belong here. Preserve risk-snapshot shape. |
| `execution_control/session.py:77` | `prepare_session` already has universe-batch and two-context freshness checks. PLB floor agreement applies before simulation and inside its existing transaction, without bypassing batch identity/expiry/guard checks. |
| `execution_launch/profile.py:30,52,365,394,459` | Policy input/schema/digests, completeness/ranges and obsolete low-principal-floor warning. `LB` must remain a required user input even though incomplete profile templates use null. |
| `execution_launch/strategy.py:102,345`; `execution_launch/driver.py:154,208,332` | `ForwardProtocol`, current `_simulate`, driver identity/sizing/first-bar checks. PR5's `_order(...)` does not yet exist here (proposed at PR5 plan line 1633); PLB must target its merged shared helper, including the benchmark, not just today's `_simulate`. |
| `execution_launch/study.py:258`; `workflow.py:187`; `review_request.py:248`; `runner.py:146` | Freeze and every capital equality must bind protocol cash floor to `W0-LB`. Old study and identity digests deliberately change. |
| `execution_launch/runner.py:186`; `coordinator.py:710` | `prepare_launch_session` currently receives Positions/asof, not settled cash. O16 needs the validated account cash from the same last observation. PR4e also changes this call; remap after it lands. |
| `execution_control/universe_odds.py:30,146`; `controller.py:187` | Batch needs agreement and `floor_safe` checks plus preserved per-coin refusal codes (§12.5 line 713). Preserve existing positions/asof API: no account-provider call. Stake changes need a new batch; signing a limit invalidates the owner-head binding. |
| `tools/owner/launch.py`; `execution_launch/coordinator.py` | Relaxation command only under O14's state condition; coordinator is already in the PLB closure under O16 even without that command. Future PR4e warning text must disclose that manual dust top-up spends outside the controller's cash cap (§12.5 line 714). |
| Research/example/docs/tests | §8.2–8.3: mirror, synthetic builder, example JSON and affected contracts land with implementation. New required fields deliberately change universe fixed-profile digest pins (§12.5 line 718); review boundary pins by hand, not automatic acceptance of failures. |

**Compatibility issue to resolve in the later plan:** adding a required refusal-code field directly to `CoinOdds`
would make existing `universe_odds_batch` rows fail today's strict `set(coin) == fields(CoinOdds)` check
(`controller.py:188–195`). §12.5 line 713 requires retaining codes, while §8.1 promises existing journals still
fold and §10.1 adds no migration. The later plan must state the compatible recording/reading contract;
silently making old journals unreadable or discarding their history is not acceptable. No design choice is made here.

## Readiness and verification boundaries

- PLB removes the floor blocker only (§7.4). Current `coordinator.py:281` still accepts rehearsal only;
  `account_interval.py:117` is flat-only and `:418` refuses continuous live risk integration;
  `tools/owner/rehearsal.py:403` constructs rehearsal. Universe support is not a controlled producer.
  Production evidence authority, held-position interval/guard integration, planner provider and controlled
  coordinator still need their own completion. No qualifying real study was established by this inspection.
- PLB §12.1 excludes KIS/OKX/fixed-fee venues, external-flow stages and post-activation expansion.
  They are not silently covered by the Upbit budget implementation.
- Required later evidence is specified in §§11.1–11.3: cash-after-fee/pending-buy boundaries; floor agreement
  before/inside preparation and during observations; unchanged exits/daily/activation boundaries; halt resend;
  fixed/universe driver-paper parity; stale artifacts; dust variants; changed pins reviewed explicitly.
  O16 additionally needs held/remainder cases proving the stake cap uses settled cash, not marked equity.
- Start that later implementation from a measured baseline on merged PR5 main; source citations and fixture
  amounts in this preflight are not a replacement for its actual affected-test inventory. No tests were run here.

This is a software dependency record, not legal, tax or investment advice; the author is not a licensed adviser.
