# Principal loss budget below activation: one floor, enforced at admission

Date: 2026-11-11 (Asia/Seoul). Base: `origin/main` at `fd85850`. Every `file:line` below refers to that commit. The citations were read at `2c9c478` and re-checked against `fd85850`; the pull requests merged in between moved lines in five cited files and changed the two lines noted in 8.1.

Status: **PROPOSED. NOT APPROVED. NOTHING IMPLEMENTED.** The owner asked for this design on 2026-11-11 KST after seeing the options. It becomes an owner decision only when the owner approves it. Merging the pull request that adds this file is that approval.

- **Approval means:** this design as a whole becomes the owner decision that the implementation must follow. No part of it is optional, except that each open decision of 12.2 takes its recommended default unless the owner changes it in the same pull request. In particular the rule (section 2), its validation (section 3), the sizing rule (section 4), the halt rule (6.3), the order rule (9.2) and the supersession table (1.3) become the written policy for the floor below activation. It also records that the owner accepts the seven points at the end of 0.1.
- **Approval does not mean:** no code is approved, no limit is signed, nothing is armed and no runtime behaviour changes. Until the implementation is merged and code-approved, every superseded sentence still describes what the software does. The spec pull request edits no other document; the implementation pull request does.
- **Do not sign a lower `total_loss_floor_krw` because this spec was approved.** With today's signed code that order of acts can end in a permanent halt (9.2).

Inputs: [the 2026-10-30 equity policy spec](2026-10-30-equity-policy-and-strategy-design.md) (amended here), [the 2026-10-23 compliance and odds spec](2026-10-23-compliance-gate-and-odds-engine-design.md) (D3, D11, D12, D14), [the 2026-10-31 E2/E3 spec](2026-10-31-e2-e3-execution-design.md), and the source at the base commit.

Owner capital, the budget, the activation threshold, targets and dates belong in the private profile. This public document uses symbols and ratios only. Nothing was run for it: no test, no simulation, no network request. Private state (owner log, control journal, baseline store, profile) was not opened, so what it holds is unknown here. A floor is a rule the software enforces. It is not a promise about a venue, a fill or a profit.

Paths are repo-relative. Short forms: `risk.py`, `controller.py`, `session.py`, `store.py` are in `execution_control/`; `owner.py` is `core/compliance/owner.py`; `costs.py`, `simulate.py`, `bold.py`, `report.py` are in `core/odds/`; `profile.py`, `runner.py`, `driver.py`, `strategy.py`, `study.py`, `coordinator.py`, `account_interval.py`, `review_auth.py` are in `execution_launch/`; `baseline.py`, `baseline_store.py`, `provider.py` are in `execution_accounts/`; `launch.py`, `rehearsal.py` are in `tools/owner/`.

## 0. Summary

### 0.1 The design in one page

1. **The rule.** `W0` is the principal and `LB` is the lifetime loss budget. While the highest equity ever reached (`H`) is below the activation threshold `A`, the loss floor is the fixed amount `C = W0 - LB`. It does not rise when equity rises. At or above `A` the existing drawdown rule applies unchanged.
2. **No second mode.** `LB` is a required policy input. A profile without it builds no policy and trades nothing. The trailing-peak rule below `A` is deleted, not kept as an option.
3. **One floor.** While `H < A`, two stored numbers must both equal `C` before any buy: the total-loss floor you signed (`L`), and the floor the controller holds in force for the account (the highest it has recorded). This is checked when a session is prepared and on every observation. A disagreement blocks entries. It never halts and never lowers a floor.
4. **Admission is the cap.** While `H < A`, a buy is admitted only if settled cash after it, less pending buys and including its fee, is still at or above the floor. Under the assumptions of 4.6 a position is then never larger than the remaining budget, and it can fall to zero without a breach while `H` stays below `A`. At `H >= A` the rule is not applied (PLB-O3), and a losing run there can end in a permanent halt (2.4). This is the only working protection: nothing sells on a breach, and the floor is not observed while a position is held (4.1).
5. **Same number everywhere.** The program that sizes live orders and the paper test that qualifies a strategy use the same cap, in every regime (4.2). The odds card must use the sizing mode that keeps the floor even if the position goes to zero (`floor_safe`), with a stake no larger than current equity, and a session is prepared only while the account holds no position (4.3). `core/odds` and `core/compliance` are not edited.
6. **The price.** With no real edge, the chance of reaching a target `T` from `W0` is at most `LB / (T - W0 + LB)` (7.1). A small budget against a far target is a small chance. For a target above `A` the real chance is lower still: with the default of PLB-O5 you sign `L = W0` when `H` first reaches `A`, a separate owner act ((g) below); after it no session is prepared, so this change alone trades above `A` only in the session in which `A` is crossed. Choose `A` and `T` with that in mind (2.4, 7.1). This design makes the odds visible; it does not improve them.
7. **Scope.** This removes one blocker: today the floor sits at the principal, so even the first fee would cross it (M8 in `docs/remaining-market-readiness-2026-11-06.md:152`). A first live trade is still blocked by four others (7.4).
8. **Cost.** Ten files covered by your code signature change, so you sign the code again (`code_approved`) and sign one new limit (`limit_set`). The lower floor counts only from the next calendar day in Seoul (two date changes in the case of 10.2). Every study, review and session made before must be made again, so one new full prospective study (48 hours of capture in the current draft workflow, plus evaluation and review) must also pass (12.4).

By approving, the owner accepts in writing:

- (a) Gains below `A` are not protected. Loss measured from the peak can exceed `LB`; `LB` caps loss against `W0`.
- (b) Position size is at most the remaining budget, with the odds ceiling of 7.1.
- (c) A position that is open when `H` first reaches `A` is exposed to the existing peak-drawdown halt (PLB-O4). So is every new entry above `A`: it is sized against `C` while the floor there is at least `W0`, and no parameter prevents a halt on a losing run (2.4).
- (d) Until a halt, you can sign a lower floor on any later day, and nothing records how much has been loosened or lost so far. A halt and the recorded peak live in one state folder (`TRADEGEN_HOME`); a different folder has no memory of them (6.3, 6.4).
- (e) Deposits and withdrawals are unsupported while a budget is in force. The account must hold no more than `W0` at the first anchor: cash above `W0` there is extra money that can be lost (6.1, 6.2).
- (f) A halt stays permanent, nothing sells on a halt, and the cap rests on the assumptions of 4.6. A spent budget usually ends with a small unsellable position and a stopped runner, not with a clean flat account (4.5).
- (g) With the default of PLB-O5, the written policy is that you sign `L = W0` when the state check first shows `H >= A`. That is a separate owner act; approval signs nothing. After it no new session can be prepared (`STUCK_AT_START`) until a post-activation spec is written, approved and implemented. Under this spec alone, trading above `A` is limited to the session in which `A` is crossed (2.4, PLB-O5).

### 0.2 Symbols

| Symbol | Meaning | In code |
|---|---|---|
| `W0` | Initial contributed capital to protect (the principal) | `policy.initial_equity` |
| `LB` | Lifetime principal loss budget, an absolute KRW amount; `W0 - LB` must be a whole number of KRW (3.2) (new) | `policy.principal_loss_budget` |
| `C` | Budget-regime floor, `C = W0 - LB` | derived; also `ForwardProtocol.cash_floor_quote` (new) |
| `A` | Activation threshold of the drawdown regime | `policy.drawdown_activation_equity` |
| `delta` | Drawdown fraction after activation | `policy.peak_drawdown_fraction` |
| `alpha` | Share of the previous day's realized profit used as the next day's loss budget (2026-10-30 meaning; not `ForwardProtocol.alpha`) | `policy.positive_profit_loss_fraction` |
| `H`, `E` | Lifetime high-watermark; current marked equity | `RiskResult.high_watermark`; `RiskObservation.equity` |
| `F_raw`, `F_effective` | Requested floor; floor in force after the ratchet | `calculated_floor`; `effective_floor` |
| `L` | Owner-signed total-loss floor | owner log `limit_set.total_loss_floor_krw` |
| `G` | Governing floor, `max(F_effective, L)` | derived |
| `R` | Remaining headroom, settled cash minus `G` | derived |
| `T` | Odds plan target; the plan stake is `plan.stake_krw` | `plan.target_krw` |
| `m`, `f`, `k` | Minimum order; runtime fee fraction; card cost rate per side | `rules.min_notional_krw`; `rules.fee_fraction`; `costs.py:23` |

`P[d]` (a day's realized profit) and `B[d]` (a day's loss budget) keep their 2026-10-30 meaning. One field name is used everywhere: `policy.principal_loss_budget`. `C` here is the floor; section 2 of the 2026-10-30 spec uses `C` for cash in one illustration (`:33`).

## 1. Goal, non-goals, what this changes

### 1.1 Goal

- **G1.** While `H < A` the requested floor is the constant `C`. The floor then no longer rules out a first entry (blocker M8): once the signed floor is `C`, the account starts with `LB` of headroom instead of none. A first live trade stays blocked by the four items of 7.4.
- **G2.** One floor: the odds card, session preparation, the controller and the fixed driver work from the same number, and the system blocks entries wherever two stored values differ.
- **G3.** While `H < A` and under the assumptions of 4.6, no admitted order can take equity below the floor, even if the bought asset goes to zero. In that regime the card sentence "your floor ... holds even if this position goes to zero" (`report.py:132`) is true of the runtime. At `H >= A` the cash rule is not applied (PLB-O3) and no such claim is made (2.4). Every limit is visible: named refusals, a read-only state check, and the real odds before any signature.

### 1.2 Non-goals

- No change to the formula at or above `A`, to the ratchet, to the strict breach test or to the permanence of a halt. No new block and no new equality at `H >= A`. Changes that have no regime also apply there (2.4).
- No change to `core/odds` or `core/compliance`. No change to the owner-log schema or the signer.
- No automatic exit, stop order or liquidation. `Controller.observe` still places no exit (`controller.py:434`).
- No un-halt, no rebasing of losses, no fee exemption, no deposit or withdrawal handling, no migration code, and no claim that a first live trade becomes possible from this change alone.

### 1.3 Superseded sentences

Each row is superseded only for the part named, and only once this spec is approved. Until then it stays in force.

| Where | Text today | Replaced by |
|---|---|---|
| `docs/superpowers/plans/2026-11-06-resume-readiness.md:14` (latest recorded owner decision) | "Preserve the existing principal and high-watermark floors; explain costs." | The approval of this spec, for the floor below `A`. A dated record: not edited. |
| `docs/windows-first-trade-integration.md:10-12` | "preservation of the existing principal/peak floors are settled decisions. Do not ask the owner to choose them again." | The floor clause points here. The other settled items stay. |
| same, `:173-174` | "Principal/HWM floors and prior-loss-day zero allowance remain unchanged." | Unchanged at or above `A` and for the prior-loss day; below `A` the floor is `W0 - LB`. |
| `docs/remaining-market-readiness-2026-11-06.md:85`, `:88-92` | Heading "The unchanged loss floor and entry costs"; "requests `H` while `H < A`" | A dated note under the heading; the formula sentence is replaced. |
| same, `:108-114` | "Do not lower the floor"; "consistent with the same protected amounts" | These two clauses only. "exempt fees, rebase away prior losses, invent a market profit or treat an expected recovery as guaranteed" stays in force. |
| same, `:152` (M8), `:177-178` | "under unchanged principal/peak floors"; "The confirmed floor" | M8 reads "under the floor of the 2026-11-11 spec". M1 to M7 are untouched. |
| `docs/first-trade-owner-checklist.md:8-11`, `:15-19` | "without relaxing principal or peak protection"; "Below `drawdown_activation_equity` the protection floor equals the peak" | The new rule; the limits step gains the order rule of 9.2. |
| `docs/account-connection-runbook.md:117-119` | "retain principal/peak protection" | "apply the floor of the 2026-11-11 spec". |
| `docs/launch-profile-contract.md:42`, `:54` | "preserves the existing full-peak/principal floor formula"; "A signed principal floor cannot be below the profile principal." | New field and formula; the sentence at `:54` is replaced (3.3). |
| `docs/fixed-driver-contract.md:58-59` | "a deployment begins with the protocol's initial cash and zero units" | With PLB-O2: zero units and settled cash at or above the protocol's cash floor. |
| `2026-10-30-equity-policy-and-strategy-design.md:69-76` | `if H < A: F_raw = H`; "the rule does not merely protect original contributed capital" | `if H < A: F_raw = W0 - LB`. Below activation the rule protects the principal less the budget, not the peak. A row for `LB` is added to its parameter table (`:13-25`), pointing here. |
| same, `:78` | "the requested floor can decrease discontinuously ... This is a loosening" | Under one policy the requested floor only rises at `A` (2.3). Its section 9 rows at `:200`, `:202`, `:203` point here. |
| `2026-10-31-e2-e3-execution-design.md:331` | "Below activation protect that peak" | "Below activation protect the principal less the signed budget." |
| `README.md:66`, `:934` | "The unchanged protected floor ..."; "The protected floor is unchanged" | Reworded. CRLF file: Edit tool only. |
| `docs/continuous-guard-commit-contract.md:65-68`, `:252`; `docs/continuous-price-candidates.md:82-85` | "a previously applied floor of `109`" below an activation threshold of 110; the path 100, 110, 105, 115 described as a floor breach | True only under the trailing rule; reworded with a path through `W0 - LB`. |
| Dated plans and ledgers under `docs/superpowers/plans/`: `2026-10-31-first-trade-foundation.md:9`; `2026-11-02-first-trade-operational-completion.md:61-64`, `:71-72`; `2026-11-02-first-trade-operational-execution-ledger.md:86-87`; `2026-11-06-live-readiness-48h.md:31`, `:57-58`; `2026-11-06-live-readiness-execution-ledger.md:260-265`; `2026-11-06-resume-readiness.md:73-75`; `2026-11-06-resume-execution-ledger.md:81-82` | Each says the principal and high-watermark floors are unchanged | Historical records. Not edited. Superseded for the floor below `A` by reference from here. |

Wording only, rule kept: "principal/peak floor" becomes "the effective floor" at `risk.py:30`, `docs/recovery-cutoff-contract.md:12-14`, `docs/owner-runtime-operations.md:13-14` and `docs/launch-profile-contract.md:22-23`.

### 1.4 Kept, by name

- **No fee exemption and no rebasing of losses.** Fees count against the budget. `W0` is never rebased.
- **Permanent halt.** A breach halts for good (`controller.py:421-429`). After a halt no loosening counts and the signed floor stays at or above the halted floor (`owner.py:525-528`, `557-558`). No code un-halts.
- **D12 timing.** Tighten at once; loosen only from the next Seoul date, outside an armed session, never after a halt (`owner.py:525-528`). Lowering `L` to `C` goes through it unchanged.
- **The unchanged `floor_safe` code.** `costs.py` and `simulate.py` are byte-identical after this change.
- **Daily rules.** All of section 5, including the 22:00 recovery rule.
- **The post-activation formula**, `max(W0, (1 - delta) * H)` (`risk.py:275`), the ratchet (`risk.py:277`; `controller.py:217-226`, `391-395`) and the strict breach test (`risk.py:279`).
- **D3** (one shared setting; this design makes it checkable), **D11** (exits are never vetoed by a risk rule, `risk.py:98`, `controller.py:613`), **D14** (every code edit needs a new `code_approved`, `owner.py:789-799`).
- **Zero external flows only** (`baseline.py:278-283`).

## 2. The rule

### 2.1 Formula

```text
H           = max(H_prior, E)                                unchanged   risk.py:273
F_raw       = C = W0 - LB                  if H <  A         CHANGED     risk.py:274
            = max(W0, (1 - delta) * H)     if H >= A         unchanged   risk.py:275
F_effective = max(F_prior, F_raw)          if F_prior is set unchanged   risk.py:277
            = none: EFFECTIVE_FLOOR_UNCONFIGURED, entry blocked          risk.py:280-281
breach      = E < F_effective  or  E < L                     unchanged   risk.py:279; controller.py:416-420
agree       = L is set and L == C and F_effective == C       NEW, only while H < A (2.5)
```

`H_prior` is the largest of the anchor's peak and every journaled peak (`controller.py:388`). `F_prior` is the larger of the anchor's `approved_effective_floor` and the last journaled effective floor (`controller.py:391-395`). One arm changes, at `risk.py:274`. There is no separate helper function and no legacy mode.

### 2.2 Below `A`

- The floor is `C` for every `H` in `[W0, A)`. It does not move when equity rises or falls.
- A gain is not protected. If equity rises above `W0` and falls back, the floor is still `C`; loss from the peak can be `LB` plus that gain. Loss measured from `W0` is what `LB` limits.
- `H` is never below `W0` (`risk.py:206`), so with `A == W0` this regime never applies. The engine keeps accepting `A == W0` (`risk.py:196`); the launch preflight blocks it by name (3.2).

### 2.3 The transition at `A`

The comparison stays strict: `H == A` is already the activation arm. At the first observation with `H >= A` the requested floor becomes `max(W0, (1 - delta) * H)`, which is at least `W0` and so above `C`. It is a tightening, takes effect in the same evaluation through `max(F_prior, F_raw)`, and is journaled (`controller.py:410-415`). The journaled peak never decreases (`controller.py:220-221`), so while `A` stays at or below the journaled peak the floor never returns to `C` in that journal. With `A` unchanged, the budget exists below activation, once.

`A` lives in the unsigned profile (3.1). A profile with `A` above the journaled peak requests `C` again. The journal floor stays (`risk.py:277`), so 2.5 blocks every entry in that journal. The only way down is `approve_floor_relaxation`, which accepts while `L == C` is still signed (`controller.py:457-471`). On today's main the same edit only tightens; the new arm makes it a loosening (6.4). With the profile unchanged, `F_raw` never decreases as `H` rises, so `relaxation_pending` (`risk.py:278`) can only come from state written under the old formula (10.2).

### 2.4 At and above `A`: unchanged, and what that leaves open

- **Nothing in this design is specific to `H >= A`:** no block, equality or formula change is added for that regime. Changes that have no regime also apply there: the driver and evaluator cap (4.2), the plan pins (4.3), the first-bar rule (6.1) and the owner-log halt reason (6.3). In particular a driver buy is sized from `max(cash - C, 0)` at every `H`; it is never larger than today's size. Above `A` this is not a floor guarantee (`G >= W0 > C` there); it is kept only so the driver equals the paper study.
- **What lowering `L` opens above `A`.** Today, with the documented `L >= W0`, no entry above `A` is reachable: `L >= W0 >= stake` makes every card `STUCK_AT_START` (4.5). With `L = C` the card passes, preparation needs no equality (2.5) and the cash rule does not apply (4.1). A buy is admitted while `E >= F_effective` (`controller.py:622-627`) and is sized against `C` while the floor is at least `W0`. A loss larger than `E - F_effective` (one fee, when `E` is at the floor) then halts for good. This is the hazard of 9.2 with new signed code. It is also the normal path after a flat activation: a losing run above `A` ends in a permanent halt, not in the end states of 4.5. No static parameter prevents it; `exposure_fraction <= min(delta, 1 - W0/A)` bounds only an entry made at `E == H`, before its fee. The only closures are PLB-O5, which stops new preparations only (a session already armed keeps admitting buys, `controller.py:626-627`), or the every-regime alternative of PLB-O3.
- **Pre-existing limit, stated plainly.** The odds card holds one static signed floor for the whole horizon (`simulate.py:157`, `510`). Above `A` the runtime floor is at least `W0` and follows the peak. A card prepared with `L = C` then overstates the headroom and the chance of the upper outcomes.
- **Recommended owner act, outside this change (PLB-O5).** When the state check (9.1) first shows `H >= A`, sign `L = W0`. It is a tightening and applies at once (`owner.py:538-542`). It puts activation into the owner log, the only store that outlives a moved journal. Its other effect must be understood: the stake may not exceed `W0` (`runner.py:205-206`), so with `L = W0` every later card returns `STUCK_AT_START` (`costs.py:271-272`) and no new session can be prepared until a post-activation spec defines stake and floor there. That spec is a named follow-up. Never sign a floor above current equity: the next observation halts for good (`controller.py:416-425`).
- **Activation with an open position (PLB-O4, default: accept).** At that first observation the floor jumps while nothing sells. A position carried across `A` is exposed to the existing peak-drawdown halt exactly as any position above `A` is today. One wrong high mark has the same effect and also ends the budget for good (with `A` unchanged, 2.3). Guidance: a position of value `V` carried across cannot cause a halt while `V <= min(H - W0, delta * H)`, because cash is then still at or above the new floor. Put `A` well above `W0`. If the plan should stay inside the budget regime for its whole life, put the plan target below `A`. The driver is flat at every window end (`driver.py:290`) and a window is at most one day (`launch.py:107`), so the exposure is inside one window.

### 2.5 Floor agreement (D3 made checkable), budget regime only

Four stored floors exist and the highest wins: the policy formula, the anchor's floor (`baseline.py:242`), the journal's last floor (`controller.py:391-395`) and the signed `L` (`controller.py:416-420`). The odds engine reads only `L` (`costs.py:357`; `simulate.py:510`). They can differ today and nothing reports it. New rule, while `H < A`: an entry needs `L == C` and `F_effective == C`. `L` is compared as `Decimal(str(L))`, the conversion the controller already uses (`controller.py:419`, `458`, `626`).

**(a) At preparation.** Two evaluations in `prepare_session`, with one code: `SESSION_PREPARATION_LOSS_FLOOR_DISAGREES`. In both, the budget regime is presumed unless the reconciled equity or the highest journaled peak is at or above `A`.

1. **Before the card.** On the first context (`session.py:135`), before `simulate` (`session.py:140`). The journaled peak is read with `Journal.snapshot()`, which creates nothing and holds no transaction. It refuses alike on a missing, partial or corrupt journal (`store.py:232-253`); any such refusal counts as no rows here, which is safe because the second evaluation reloads the journal. In the presumed budget regime an unset `L`, or `L != C`, raises. So below `A` the card is reached only with `L == C` (4.5).
2. **Inside the journal transaction** it already opens, beside the final owner-context check (`session.py:147-159`), with the journal rows (`session.py:165`) and the final context: again `L == C` and, when a snapshot exists, a last journaled effective floor equal to `C`. This evaluation is authoritative. On refusal it appends nothing (the `session_prepared` row is written later, `session.py:187`). The two contexts must hash equal (`session.py:158`).

- It covers every caller: `prepare_launch_session` (`runner.py:230`) and any direct one.
- On the signing date the first evaluation refuses, with this code and not the card's. Both contexts carry the session label, not an armed id (`session.py:135`, `155`), so a loosening counts only when its date is before today (`owner.py:525-528`).
- The session id contains the preparation time (`session.py:172-179`) and a session is valid only on its preparation date (`session.py:220-221`). It cannot be armed before it exists, so "armed on or before the loosening date" is unreachable through a normally stamped arming. An arming is dated by the earliest of its own stamp and the stamps of the lines after it (`owner.py:490-492`, `500-503`). If one is stamped back, the loosening does not count inside that session, so the signed floor there is the earlier one, and the buy is refused at (b), which a buy runs with the session's own context (`controller.py:612`, `622-624`). If equity is also below that earlier signed floor, the same evaluation first writes a permanent halt at it (`controller.py:416-425`). The runner's own observation carries no session id (`controller.py:438`), so it shows nothing first; `reserve` raises and the runner stops (`runner.py:447`, `459-463`). The signer refuses a stamp earlier than the last line (`tools/signer/sign.py:967-970`); a system entry has no such check (`owner.py:409-423`). S12 of 9.1 checks the armed session before the runner starts.
- The journal may hold no snapshot. In the shipped flow a bootstrap unit publishes an account observation and then observes (`coordinator.py:488-491`, `650-660`) before the owner prepares, so the journal normally holds `H`. This is not guaranteed. `prepare` needs only a published observation at most 30 s old and does not test the ready flag (`coordinator.py:721-724`). The observation is stored before `observe` runs (`coordinator.py:425-426`), a failed `observe` is caught and leaves it in place (`coordinator.py:497-498`), an engine error writes no snapshot (`controller.py:410`), and a cancel or exit unit publishes without observing (`coordinator.py:547-559`). With no snapshot the check has only the reconciled equity: the budget regime is presumed unless that equity is at or above `A`, and then only `L == C` is required. Rule (b) still runs on the next observation and on every buy.

**(b) On every observation.** In `Controller._snapshot_risk`, after the signed floor is read (`controller.py:416`): when the engine returned floors, `H < A` and `agree` is false, the result gains the reason `LOSS_FLOOR_SETTINGS_DISAGREE` and blocks new entries. It writes no `halt` row and no `system_halt`, changes no floor and adds no journal field (the `risk_snapshot` shape stays, `controller.py:152-153`).

- It runs on every `observe` (`controller.py:441`) and inside every buy authorization (`controller.py:622`), at reserve and at dispatch (`controller.py:658`, `684`). Exits are unaffected: the buy branch is skipped for a sell (`controller.py:613`).
- It is a reason, not a `ValueError`. The runner reads the observation first (`runner.py:413`) and returns `blocked` without stopping (`runner.py:427-431`). Status carries the code (`coordinator.py:494`; `launch.py:215`). The one exception is the back-stamped arming of (a): the observation has no session id and sees no disagreement.

### 2.6 Equality

| Comparison | At equality | Evidence |
|---|---|---|
| `E` against `F_effective` or `L` | not a breach | `risk.py:279`; `controller.py:420` (unchanged) |
| `H` against `A` | activated | `risk.py:274` (unchanged) |
| `L` and `F_effective` against `C`, while `H < A` | required | new (2.5) |
| Settled cash after a buy against `G` | admitted | new (4.1); a later total loss leaves `E == G`, not a breach |
| Daily loss against a daily budget | stopped for the day | `risk.py:312-314` (unchanged) |
| Odds: cash after a fill against `L` | path ends at the floor | `simulate.py:250` (unchanged) |

### 2.7 What a breach does

Unchanged. `E < F_effective` or `E < L` at an observation appends a journal `halt`, tries to append an owner-log `system_halt`, and blocks entries with `PERSISTENT_HALT` (`controller.py:420-429`). Nothing is sold. No loosening ever counts again (`owner.py:525-528`), relaxation refuses (`controller.py:453-454`) and review verification refuses (`review_auth.py:164-166`). Under 4.1 a breach below `A` is not reachable through a price move. If one happens, an assumption of 4.6 was broken, and a permanent stop is the intended response. Section 6.3 hardens the halt.

## 3. Parameters and validation

### 3.1 Where each value lives and what binds it

| Value | Lives in | Set by | Bound by |
|---|---|---|---|
| `policy.principal_loss_budget` (`LB`) | Private profile JSON, a decimal string | Owner | Both profile digests (`profile.py:263-264`, `277-279`, `306-310`), so protocol, study, review request and the signed review document; `digest(RiskPolicy)` (`execution_control/capability.py:40-45`), so `PreparedSession.policy_digest`, the session id the owner arms and every risk snapshot (`session.py:133`, `172-179`, `217`; `controller.py:411`). **The profile file itself is unsigned and no owner-log entry names it.** Owner signatures reach it only through these digests: the signed review document binds the contract digest (`execution_launch/review_request.py:264-268`; `review_auth.py:183-199`, `213-219`) and a signed `session_armed` names the session id. A changed budget therefore voids the study, the review and any prepared session. By 2.5 it also cannot trade below `A` until `L` equals the new `C`; a larger budget is a loosening and waits for the D12 date (6.4). |
| `total_loss_floor_krw` (`L`) | Owner log `limit_set`, with `daily_loss_krw` in the same entry (`owner.py:151-152`) | Owner, by signature | The signature and the D12 fold (`owner.py:525-542`). Schema unchanged. |
| `approved_effective_floor` | Reviewed account anchor (`baseline.py:242`) | Owner; must be `C` | The reviewed head; fixed inside a store (`baseline_store.py:176-178`). |
| `ForwardProtocol.cash_floor_quote` (`C`) | Study protocol | Study freeze, from the profile, beside `initial_cash_quote` (`study.py:257`) | Protocol digest, so registry, plan hash, public commitment, review, driver identity (`driver.py:172-175`). |
| `EVALUATOR_REVISION` | Code (`strategy.py:27`), bumped | Implementation | D14 hash and capture manifest; an old protocol is refused (`strategy.py:135`). |
| `W0`, `A`, `delta`, daily budgets, recovery condition, venue tables, `k` | unchanged | unchanged | unchanged |

### 3.2 Validation rules and codes

| Rule | Where | Code | New? |
|---|---|---|---|
| Decimal string, finite, `>= 0`, bounded digits | `profile.py:130-142`, `174-177`, `233`, once the name is in `_POLICY_NUMBERS` (`:30-32`) | `PROFILE_DECIMAL_STRING_REQUIRED`, `PROFILE_DECIMAL_INVALID` | existing, automatic |
| Present (not null) | `profile.py:340-343`; hard error `:379-380` | `POLICY_INPUT_REQUIRED`; `POLICY_INPUTS_INCOMPLETE` | existing, automatic for a new `PolicyInputs` field |
| Unknown key on an old checkout | `profile.py:118-120`, `224` | `PROFILE_SCHEMA_INVALID` | existing |
| `0 < LB < W0` and `W0 - LB` a whole number of KRW | preflight beside `profile.py:344-348`; hard error beside `:383-385` | `LOSS_BUDGET_OUT_OF_RANGE`; `POLICY_INPUTS_INCONSISTENT` | new issue; existing hard-error code |
| `A > W0`; with `A == W0` the budget regime can never apply | preflight, same place | `LOSS_BUDGET_NEVER_APPLIES` | new; a preflight block, not an engine error |
| `LB >= m * (1 + f)` from `profile.instrument_rules` | preflight, with the rules checks (`profile.py:360-367`) | `LOSS_BUDGET_BELOW_MINIMUM_ORDER` | new |
| `LB` is an exact finite `Decimal` | engine, in the loop at `risk.py:172-175` | `INVALID_POLICY_PRINCIPAL_LOSS_BUDGET` | new name, existing pattern |
| `0 < LB < W0` and `W0 - LB` whole | engine, beside `risk.py:196-197` | `INVALID_PRINCIPAL_LOSS_BUDGET` | new |
| `0 <= C < initial_cash_quote` in a protocol | `strategy.py:146-150`; parse at `:590-591` | `STRATEGY_THRESHOLD_INVALID` | new field, existing code |
| Protocol `C == W0 - LB`, wherever `initial_cash_quote == W0` is compared. A missing `LB` is a mismatch, never arithmetic on a missing value (as `execution_launch/review_request.py:247` already guards `initial_equity`) | `runner.py:146-148`; `driver.py:168-171`; `execution_launch/workflow.py:180`; `execution_launch/review_request.py:247-249` | the existing code at each site | one more clause each |
| Floor agreement while `H < A` | `session.py`, twice (2.5a); `controller.py` (2.5b) | `SESSION_PREPARATION_LOSS_FLOOR_DISAGREES`; `LOSS_FLOOR_SETTINGS_DISAGREE` | new |
| Cash-floor admission while `H < A` | `controller.py`, `_authorize` (4.1) | `ValueError('entry would take settled cash below the loss floor')` | new |
| Plan pins at launch preparation | `runner.py:203-206` (4.3) | `RUNNER_SELECTED_SIZING_UNSUPPORTED`; `RUNNER_SELECTED_STAKE_EXCEEDS_ACCOUNT_EQUITY`; `RUNNER_PREPARATION_REQUIRES_FLAT_ACCOUNT` | new; `RUNNER_SELECTED_STAKE_EXCEEDS_RESEARCH_CAPITAL` stays |

An engine error returns no floors (`risk.py:223-225`), so the controller writes no snapshot (`controller.py:410`): an invalid budget can block entries but cannot ratchet a floor into the journal or cause a halt through the formula. The signed floor is still monitored (`controller.py:416-420`).

**Why an absolute amount and a whole-KRW floor.** The validated condition is on the floor: `W0 - LB` must be a whole number of KRW. `LB` is not separately required to be whole; with a whole `W0` the two are the same. `LB` must agree to the won with a signed absolute number, as the two daily budgets are amounts. The owner log folds limits into floats (`owner.py:540`) and the controller compares `Decimal(str(L))`. A whole number of this size survives that conversion exactly; a fractional floor would make the central equality depend on float printing. The engine validates it, so every place that relies on the equality is covered, including the existing relaxation path (`controller.py:458`).

### 3.3 `SIGNED_PRINCIPAL_FLOOR_TOO_LOW`

The comparison at `profile.py:435-437` flags exactly the state this design needs (`L < W0`), and no shipped caller reaches it: every non-test call of `preflight_profile` omits the context (`execution_launch/cli.py:167`; `runner.py:198`, `208`, `414`; `study.py:251`; `execution_launch/review_request.py:255`; `execution_launch/study_review.py:166`; `rehearsal.py:348`). It is deleted. The enforcing sites are 2.5(a) and 2.5(b). It is not rewritten as an equality, because a preflight has no `H` and cannot tell the regime. `SIGNED_LIMIT_NOT_EFFECTIVE` and `OWNER_HALT_PRESENT` (`profile.py:424-434`) stay.

- `tests/launch_profile.py:142-152`: the low-floor case leaves the loop; the unset-limit, zero-daily and halt-present cases stay; the equality is tested at the session and the controller (11.2).
- `docs/launch-profile-contract.md:54`: the sentence becomes "Below activation the signed floor must equal `W0 - LB`; session preparation and every observation enforce it, this function does not."

## 4. Sizing: admission is the cap

### 4.1 The cash-floor admission rule

Today nothing compares order size with a floor. A buy is capped by settled cash (`controller.py:558-564`) and by the prepared stake (`controller.py:639-640`). With a floor at `C` and a position near `W0`, a price move of about `LB / W0` would cross the floor. Nothing sells on a breach (`controller.py:434`), and the shipped account interval source requires a flat account (`account_interval.py:117-118`), so while a position is held the account chain stops and no observation reaches the floor test. **The halt is not a monitor. Admission control is the only working protection.**

New rule in `Controller._authorize`, buys only, after the risk snapshot, beside the stake cap (`controller.py:638-640`). It uses the three numbers `_capacity` already computes (`controller.py:558-563`):

```text
only while H < A:
    cash    = settled cash of the trading account                       controller.py:558
    pending = pending buys of that account, with their fees              controller.py:561 (528-541)
    needed  = quantity * limit_price * quote_krw * (1 + fee_fraction)    controller.py:562
    G       = max(F_effective, L)
    refuse the buy if   cash - pending - needed  <  G
```

- **Rounding margin: none.** The arithmetic is exact `Decimal` (`controller.py:649-650`) and equality admits. A later total loss of the position then leaves `E == G`, which is not a breach (`risk.py:279`).
- **A refusal is not a halt.** It writes nothing and latches nothing. It is a `ValueError` inside reserve or dispatch (`controller.py:658`, `684`), which would stop the runner (`runner.py:459-463`); 4.2 shows why the driver never proposes such an order. The stake cap beside it is a separate refusal with the same effect on the runner (4.2, 4.3).
- **Why the budget regime only (PLB-O3).** Rule 2.4 adds nothing specific to `H >= A`. Applied in every regime, the rule would give a narrower guarantee there: cash after an admitted buy is at or above `max(F_effective, L)` at admission, so the first-fee halt above `A` (2.4) becomes a refusal, while a later rise of `H` can still lift the floor above cash. But above `A`, `G >= W0 > C`, so the driver, capped with `C`, would propose orders this rule refuses, and that refusal stops the runner (`runner.py:459-463`). It would need a driver and evaluator cap on `G`, which neither can compute, or a runner pre-check that returns `blocked`. Its effect on the existing suite is unmeasured.

What follows while `H < A` and the assumptions of 4.6 hold:

- After every admitted buy, settled cash is at least `G = C`. A limit buy cannot fill above its limit, a sale only adds cash, and holdings are worth at least zero. So `E >= C` on every price path, including a gap to zero. This is the odds engine's `floor_safe` inequality, "cash after the entry >= floor + r_exit" (`costs.py:264-266`, `271-272`), moved to the place that admits real orders.
- Loss measured from `W0` cannot exceed `LB` through trading. This holds without any exit logic.
- Unrealized gains do not enlarge `R`. Realized gains do. Realized losses and fees shrink it.

### 4.2 The fixed driver and the paper evaluator

The driver must size what the controller admits, and the paper study must size what the driver sizes. The driver states that its equations are those of `strategy._simulate` (`driver.py:209`). Both get the same one-term change:

```text
today     min( trend quantity , floor_lot( cash             / (ask * (1 + fee)) ) )   driver.py:222-223; strategy.py:354-355
proposed  min( trend quantity , floor_lot( max(cash - C, 0) / (ask * (1 + fee)) ) )
```

`C` is the protocol's `cash_floor_quote`, set at study freeze and checked against the profile in the driver identity. Sells are unchanged. The cap has no regime in either place; the driver must not read `H` or `A`. The evaluator revision is bumped, so every earlier study is refused (`strategy.py:135`) and the next study measures what the driver does.

**Why the driver's order always passes 4.1.**

1. The driver requires no outstanding order (`driver.py:321-323`) and the runner blocks a buy while any order is active (`runner.py:444-446`), so `pending = 0`.
2. The driver's cash is the trading account's settled cash (`driver.py:309`), the same number the controller reads from the same provider (`runner.py:275`).
3. The order's limit price is the driver's slipped, tick-rounded ask (`driver.py:214`, `224`, `236-237`; `runner.py:352`) and the protocol fee is at least the rules fee (`driver.py:170`). So `needed <= quantity * ask * (1 + protocol fee) <= cash - C`.
4. Entries are allowed below `A` only when `G == C` (2.5). When the floors disagree the runner blocks before it reserves (`runner.py:427-431`), except in the back-stamped case of 2.5(a). At `H >= A` the controller does not apply 4.1.

**Named limit: the proof covers rule 4.1 only.** The stake cap (`controller.py:639-640`) is unchanged, applies in every regime, and the driver does not read the stake. A buy with `inventory + pending + needed > stake` is refused with a `ValueError` and the runner stops (`runner.py:447`, `459-463`); automatic exits stop with it and only the explicit exit remains (`runner.py:487-503`). The paper evaluator has no stake cap, so a study does not show this. 4.3 says when it can happen.

Side effects, stated plainly:

- `exposure_fraction * NAV` (`execution_launch/program.py:143`) is usually far larger than the remaining budget, so the cap binds and position size is the remaining budget. A capped quantity below the venue minimum is a `hold`, not an error (`driver.py:231-235`).
- **The minimum binds sells too.** The order check has no side test (`execution_control/model.py:177-181`), and an exit under the minimum is a `hold` (`driver.py:225-227`, `233-235`). Under the cap the entry notional is at most `R`, so a position bought near the minimum cannot be sold after a small fall. 4.5 says where that ends.
- The buy-and-hold benchmark inside the evaluator takes the same code path (`strategy.py:348`, `354-355`), so the comparison stays like for like.
- The paper evaluator starts at `W0` and applies the static `C` for the whole capture. It has no activation regime, no halt and no daily rules (`strategy.py:332-379`). A pass on paper says nothing about them, and it does not measure the sizing against `C` above `A` (2.4).

### 4.3 What the odds card is given

`core/odds` is not edited. Three pins at `prepare_launch_session` (`runner.py:203-206`):

1. **Sizing mode.** `selected_plan.leg.sizing == "floor_safe"`, else `RUNNER_SELECTED_SIZING_UNSUPPORTED`. A `stop_based` card says "a gap past the stop can take you below your floor" (`report.py:133`) and uses a zero floor for its ceiling (`simulate.py:713`); the runtime has no stop.
2. **Stake.** Keep `0 < stake <= W0` (`runner.py:205-206`) and add `stake <= E`, where `E` is the reconciled equity passed in as `positions`, else `RUNNER_SELECTED_STAKE_EXCEEDS_ACCOUNT_EQUITY`. The card measures headroom as `stake - L` (`costs.py:345`, `357`), so a stake of `W0` after a loss would overstate it. An inequality, not a float equality. The stake is also the session capital cap (`controller.py:639-640`): a smaller stake makes the card more cautious and lowers that cap. Choose the largest allowed stake, `min(W0, E)`. With it a refusal by the stake cap needs `cash - C > min(W0, E)`: a realized gain above `C` inside the session, or equity above `2 * W0 - LB`.
3. **Flat account.** Every holding in `positions` is zero (`core/compliance/model.py:107`), else `RUNNER_PREPARATION_REQUIRES_FLAT_ACCOUNT`. `E` includes marked holdings (`provider.py:320-324`), so with a position held a stake of `E` would show `E - C` of headroom while the runtime has only `cash - C`. Today only the flat-only interval source keeps holdings out of this call (`account_interval.py:117-118`), and 7.4 lists it as a blocker to be removed. Side effect: no session can be prepared while a position is held. Buys wait until the account is flat; sells need no prepared session and continue (`controller.py:613`).

| Quantity at preparation, `H < A` | Card | Runtime | Relation |
|---|---|---|---|
| Floor | `L` | `F_effective` | equal to `C`, enforced (2.5) |
| Headroom | `stake - L`, with `stake <= min(W0, E)` and a flat account | `R = cash - C` | card `<=` runtime (with the flat pin, `E` is the account's cash) |
| Largest entry | `(cash - L) / (1 + k)` (`costs.py:271-272`) | `needed <= cash - pending - G` | same inequality; cost rates differ |
| Floor-keeping claim | "holds even if this position goes to zero" | true by 4.1 | same |
| Daily rules, trades, cost rate | signed daily loss only (`simulate.py:202-203`); its own entries and exits; table rate `k` | all of section 5; the trend program; the observed fee | different; the card is a bound, not a forecast of the program |

### 4.4 First and later stakes

If the account holds `W0` at the first anchor (S10 of 9.1; no code enforces it, 6.1), the first stake meets a flat account with cash `W0` and floor `C`, so `R = LB`: the position, with its entry fee, costs at most `LB`. Each later buy is checked against the `R` of that moment. After a losing round trip `R` is smaller by the loss and both fees; after a winning one it is larger, and it can exceed `LB`. Across windows, see PLB-O2 (6.1).

### 4.5 `STUCK_AT_START` and the end states

- **Today** the refusal is structural: `L >= W0 >= stake` makes `cash - floor <= 0`, so no plan can open (`costs.py:271-272`, `358-359`; `simulate.py:441-444`). **After this change the structural cause is gone below `A`,** because the card is reached there only with `L == C` (2.5a). `STUCK_AT_START` then means one thing: the signed floor is `C` and the card's first stake is zero. The unchanged card has two causes for that: (a) its headroom `stake - L` (not `R`; it is smaller when the selected stake is below current cash) cannot fund one lot-rounded signed minimum order at the table rate `k` (`costs.py:272`, `291-294`, `309-310`); (b) the plan's own fixed or Kelly stake rounds below the minimum order although the headroom is enough (`costs.py:327-328`; `tests/odds_costs.py:544`). At `H >= A` the old structural meaning remains (`L >= stake`, for example after PLB-O5). The code alone never proves the budget is spent; the state check does.
- **Preflight against card.** The preflight blocks `LB < m * (1 + f)` by name (`LOSS_BUDGET_BELOW_MINIMUM_ORDER`). The card needs `(1 + k)` times the lot-rounded minimum, so for `f < k` a band about `m * (k - f)` wide passes the preflight and is refused by the card.
- **Granularity.** `first_stake` checks base costs only (`costs.py:355`). For `(1 + k) m <= LB < (1 + 2k) m` a plan is accepted while its whole stress column (`costs.py:29`) buys nothing. Choose `LB` as several minimum orders (PLB-O9).
- **End state 1: out of budget, flat, not halted.** Defined as: no position, no `halt` row, no `system_halt`, and `R < m * (1 + f)`. Nothing is written and nothing is latched. No buy fits, so it does not end by itself; a larger budget is a new adoption (a lower signed floor on a later date, a new profile, study and review). It is the exception: after a round trip whose sale was at least `m`, `R` is at least about `m * (1 - f)`, so the last sale must land in a band about `2 * f * m` wide. Both end states exist only below `A`; above `A` a losing run ends in a halt (2.4).
- **End state 2, the usual one: out of budget, holding dust, not halted.** A position bought near the minimum falls below the minimum notional and cannot be sold (4.2). Mid-window the exit is a `hold`. At the window end the driver raises `FIXED_DRIVER_TERMINAL_DUST_UNLIQUIDATED` (`driver.py:381-382`), which is not a `RunnerError` (`driver.py:44`), so the runner stops and the owner sees `RUNNER_DEPENDENCY_REFUSED` (`runner.py:459-463`). No later window opens while units are held (`driver.py:326-328`) and no session is prepared (4.3, pin 3). `E >= C` still holds and nothing is halted. **Named gap:** clearing dust is a manual owner act outside this system. A top-up buy to reach the minimum takes cash below `C`, and its fees can put equity below the floor, which is a permanent halt at the next observation. PLB-O13 names the code alternative.
- **How the owner sees it.** (1) The next preparation refuses with a named code: the generic "fresh odds preparation refused" (`session.py:141-142`) becomes `PreparationError('SESSION_PREPARATION_ODDS_' + code)` for an odds refusal, here `..._STUCK_AT_START`; the code set is closed (`core/odds/plan.py:23-26`) and reaches the owner through the coordinator (`coordinator.py:100-108`). A session lasts at most one Seoul date, so this shows no later than the next day. That code is a prompt to run the state check: only S6 `equal`, S4 `below`, no position, no halt and `R < m * (1 + f)` confirm end state 1. (2) Inside a session the driver returns `hold`; at a window end with dust the runner stops as above. (3) The state check (9.1) shows that no halt exists.

### 4.6 Assumptions of the cash rule, as testable conditions

| Assumption | Enforced by | Gap |
|---|---|---|
| One funded Upbit KRW account | The coordinator accepts only Upbit KRW spot (`coordinator.py:282-283`); the interval source requires exactly one Upbit KRW account (`account_interval.py:103-104`); the driver refuses other inventory in it (`driver.py:312-316`). The rule reads that account's settled cash, so a second account can only make it refuse more. | The account builder allows up to three accounts for other callers (`provider.py:350`); other venues are out of scope. |
| No fixed per-order charge | `InstrumentRules` carries only `fee_fraction` (`execution_control/model.py:107-117`); the repo draft of the venues table has `phi_buy: 0, phi_sell: 0` for Upbit (`core/odds/venues.yaml:31`). Only the bytes the owner signed are in force (`venues.yaml:1-2`), and `--check` reports whether the draft equals them (`core/compliance/rules.py:999-1016`). Not checked here. | The runtime does not read that table. A venue with fixed charges needs the exit reserve the card has (`costs.py:258-260`). |
| Actual fee not above `rules.fee_fraction` | Rules at most five minutes old (`controller.py:605-606`); protocol fee at least the rules fee (`driver.py:170`). | **Named gap:** the fee charged on a fill is not compared with the rules before the fill. A higher charge shows only in the next reconciled cash. |
| A limit buy never fills above its limit | Every order is an Upbit `limit` order at `limit_price` (`execution_orders/upbit.py:25-26`, `73`). | Venue behaviour; not checkable in advance. |
| No external flows | The account chain stops on any flow (`baseline.py:278-283`; `account_interval.py:123-125`); a buy needs known flows (`controller.py:608-609`). | Detected after the fact. A withdrawal that takes cash below the floor is a breach and halts. A manual order in the trading account stops the chain the same way (`account_interval.py:117-122`). |
| Account cash at the first anchor is `W0` | None after PLB-O2 (was `driver.py:326-328`). | **Named gap** (6.1); checked by S10 of 9.1. |
| Whole-KRW floor | Engine and preflight validation (3.2). | None after this change. |

## 5. Interaction with the daily rules

`LB` changes none of them and none of them changes `LB` (`risk.py:292-314`). They are daily stops, latched for the Seoul day (`controller.py:402-409`, `215-216`). Only a floor breach is permanent.

| Rule | What it measures | With the fixed budget |
|---|---|---|
| First-day budget | Largest marked drop from the day's open on the first trading day (`risk.py:294-298`) | Still required. Exhaustion is inclusive (`risk.py:312-314`) and an entry fee counts at once (`baseline.py:310-311`), so a budget below one entry's fee stops day one after the first fill. Today it never binds below `A` because the peak floor binds first; now it is the day-one limit. |
| Previous-day loss | Yesterday's realized result below zero gives budget 0 (`risk.py:301-303`) | The whole next day has no new entry, even with most of `LB` unused. |
| Previous-day profit | `alpha` times yesterday's realized profit (`risk.py:304-305`) | Unchanged. |
| Zero-profit day | Configured budget; the target is a diagnostic (`risk.py:306-311`) | Unchanged; unset blocks entry. The day after a blocked day lands here. |
| 22:00 recovery | On a first trading day or a zero-profit day, from 22:00 Seoul equity must be at or above that day's open, with a verified checkpoint (`risk.py:243-268`) | Not loosened by `LB`. A round trip that only cost fees leaves equity below the open, so entries stop from 22:00 to midnight even when the loss is far inside `LB`. |
| Signed `daily_loss_krw` | Daily loss at or above the signed value stops the day (`controller.py:402`, `406`) | Unchanged. It is restated in the same `limit_set` as the floor; an equal value applies at once while the lower floor waits a day (`owner.py:538-542`). |

A daily stop blocks entries only; an open position stays open. Under 4.1 the most that can be lost in a day is that day's remaining budget, so a daily budget above it never binds. The code will not reject one (PLB-O12).

## 6. Windows, deposits, halt and history

### 6.1 The first-bar rule (PLB-O2, default: include)

As shipped, every deployment window must open with zero units and settled cash exactly `W0` (`driver.py:326-328`), and a window is at most one day (`launch.py:107`) and ends flat (`driver.py:290`). After any fill, cash is no longer `W0`, so no second window can open and the unused budget is stranded.

- **Default: change it in the same signed change.** A window opens with zero units and settled cash `>= C`. `W0` is never rebased, and the five study-capital equalities stay (`runner.py:146-148`; `driver.py:169`; `execution_launch/workflow.py:180`; `execution_launch/review_request.py:247-249`; `study.py:257`). The study starts at `W0`; a live window starts from what the account holds. The reviewer must accept that difference.
- **What the equality did, and the owner rule that replaces it.** It was the only check that the account holds `W0`: nothing else ties account cash or anchor equity to `W0` (`launch.py:141-146`; `risk.py:206` needs only `H >= W0`). No code replaces it. Owner rule: the first anchor is taken with settled cash equal to `W0`. Below is safe (`R` is then smaller than `LB`). Cash above `W0` at the first anchor is headroom: the losable amount is `LB` plus the surplus, with no signed act and no external flow. S10 of 9.1 checks it. A driver check `cash <= W0` would be wrong, because cash above `W0` after a realized gain is legitimate (4.4).
- **Alternative: one window only.** The budget works for one window of at most a day. Every later window then needs a later change to `driver.py`, which costs a new code signature, study and review. It keeps the equality and does not have this gap.

### 6.2 Deposits and withdrawals

Out of scope and unsupported, as today: the account chain stops on any external flow (`baseline.py:278-283`).

- **Rule for now:** no cash in the trading account that is not `W0` plus the realized result of this system. So no external flow while a budget is in force, and no surplus at the first anchor (6.1). A re-anchor after a flow is not defined by this spec.
- **Named gap.** With the first-bar rule relaxed, a deposit followed by a re-anchor would be accepted as cash and become headroom (`R = cash - C`), enlarging the losable amount with no signed act. It is safe only if the signed floor is raised by the same amount first. A withdrawal of protected cash, once re-anchored, puts equity below `L` and the first observation halts for good (`controller.py:416-425`). No code binds cumulative loss across anchors. The gap also has the form of 6.1, with no flow and no re-anchor.
- Stage transitions (withdraw at a target, restart with new capital) are a named follow-up spec (PLB-O6).

### 6.3 Halt and history

Two additions, both in `controller.py`. Item (b) is separable and can be reviewed and merged on its own (PLB-O10).

- **(a) A buy is refused when the owner log holds any halted floor, whatever control journal is in use.** A fresh, moved or replaced journal under the same home does not clear it. In `_snapshot_risk`, when the owner state is valid and `halted_floors` is not empty (`owner.py:505`, `562`), the result gains the reason `OWNER_LOG_HALT` and blocks entries. Today the controller blocks buys after a halt only through the journal row (`controller.py:614-615`); called directly with a fresh journal and equity back above the halted floor, it would admit a buy. The shipped runner path already refuses, because both review verifiers refuse on any owner-log halt (`review_auth.py:164-166`; `runner.py:418-419`, `199-200`), but the controller does not depend on that. Rule (a) makes the controller itself refuse.
- **(b) A journal halt whose owner-log write failed is sent again.** Today the write is tried once and a failure is swallowed (`controller.py:422-427`). New: on a later observation, when the journal holds a `halt` row and the owner state is valid with no halted floor, the `system_halt` entry is appended again with the journaled floor. Failure is still swallowed; the journal latch still holds. This covers any journal `halt` row, including one written by the guard commit, which appends no `system_halt` itself (`execution_launch/continuous_guard_commit.py:367`).

What "permanent" covers and what it does not:

- A halt holds **per owner log** and the peak per control journal. Both live under one home (`TRADEGEN_HOME`, which the code calls the state root; `core/isolation.py:105-110`; `owner.py:34-39`; `store.py:151-152`). A different home is a different history. In this spec "home" always means that directory.
- **Allowed file move: only the documented re-anchor**, which moves the baseline store and its head aside as evidence (`docs/account-baseline-integration.md:200-215`). The control journal and the owner log are never moved.
- Activation lives in the journal and in the anchor's peak (`controller.py:388`; `baseline.py:238`). With the journal kept, a new anchor cannot lower `H`. If a journal were moved, **an owner-typed anchor that understates the peak is not detected**. The owner act of 2.4 is what puts activation into the owner log.

### 6.4 What "lifetime" means

- The budget is as strong as the signed floor. D12 lets the owner sign a lower floor on any later date (`owner.py:525-528`), and nothing records how much has been loosened or lost so far.
- `W0`, `LB` and `A` live in the unsigned profile. They are bound by digests into the study, the signed review and the session, so a buy under a changed value needs a new study, `review-approve` and `session_armed`. None of these is a `limit_set`, and none shows a floor movement.
- `W0` and `LB` are also bound by 2.5 to the signed `L`: a profile whose `W0 - LB` differs from `L` cannot trade below `A`. A profile with a different `W0` and `LB` but the same difference passes 2.5; it is a new adoption with a new study and review, and only the rule of 6.2 stands behind it.
- `A` is bound by no `limit_set`. Raised above the journaled peak after activation, it requests `C` again (2.3). With `L = W0` signed at activation (PLB-O5), undoing activation needs a new signed loosening under D12. No new mechanism is added (PLB-O7).

## 7. Real odds and scope, before any signature

### 7.1 The ceiling

Position size is at most the remaining budget. For any plan with no real edge that keeps a floor, the chance of reaching `T` before the floor is at most `(stake - L) / (T - L)` (`bold.py:36-40`; applied at `simulate.py:712-714`). At the start, with stake `W0` and `L = C`:

```text
ceiling = LB / (T - W0 + LB)        the at-risk money must multiply by (T - W0 + LB) / LB
```

If `T` is above `A`, this bound still holds, but this change alone does not carry the account to `T`. Under the default of PLB-O5 the owner signs `L = W0` when `H` first reaches `A`, and from then no session can be prepared (2.4; `runner.py:205-206`; `costs.py:271-272`). The chance of getting as far as `A` is at most `LB / (A - W0 + LB)`. The step from `A` to `T` needs the post-activation spec (12.1); its cost is not estimated here. Under the alternative of PLB-O5, sessions continue above `A` with a card whose floor is below the runtime floor, without the cash rule of 4.1, and with the halt risk of 2.4. If `T` is at or below `A`, the whole path is inside the budget regime.

### 7.2 Ratios (illustrative, not the owner's values)

Rows are `LB / W0`; columns are `T / W0`. Each cell: ceiling, and the multiple the budget must reach. The bound does not depend on the strategy, and costs lower the real figure further. When `T > A`, read the table at `A / W0` for what this change alone can deliver.

| `LB / W0` | `T / W0 = 1.25` | `T / W0 = 2` | `T / W0 = 5` | `T / W0 = 10` |
|---|---|---|---|---|
| 0.05 | 16.7%, x6 | 4.8%, x21 | 1.2%, x81 | 0.6%, x181 |
| 0.10 | 28.6%, x3.5 | 9.1%, x11 | 2.4%, x41 | 1.1%, x91 |
| 0.25 | 50.0%, x2 | 20.0%, x5 | 5.9%, x17 | 2.7%, x37 |
| 0.50 | 66.7%, x1.5 | 33.3%, x3 | 11.1%, x9 | 5.3%, x19 |
| limit `LB / W0 -> 1` (not allowed: `LB < W0`) | 80.0% | 50.0% | 20.0% | 10.0% |

### 7.3 Pace and qualification limits

- A study at this size may not qualify. It needs at least 60 observations and 20 completed round trips (`strategy.py:151-154`, `511-512`), and an order under the venue minimum is counted as rejected, not traded (`strategy.py:363-365`). With a budget of a few minimum orders, a few losses push the capped quantity under the minimum. A study can also abort with no result at all: a terminal sell under the minimum raises `STRATEGY_TERMINAL_DUST_UNLIQUIDATED` in any of the four evaluator runs (`strategy.py:363-367`, `380`, `431-434`). At a budget near one minimum order the buy-and-hold run alone does so whenever the last bid is below the entry ask. Whether a study can qualify at the owner's budget is not established here.
- One realized losing day blocks the whole next day (`risk.py:301-303`). The 22:00 rule can stop an exceptional day after a fee-only round trip (section 5). A window is at most one day and ends flat (`launch.py:107`; `driver.py:290`).
- The card models only the signed daily loss (`simulate.py:202-203`), so its trade counts are not the runtime's. Its ceiling still holds.
- **Time to target is not modelled**, by the card or by this spec. The owner should put the private ratios through 7.2 and compare the result with the private schedule before signing anything.

### 7.4 What still blocks a first live trade

This design removes M8 only (`docs/remaining-market-readiness-2026-11-06.md:152`).

| Blocker | Evidence |
|---|---|
| The account interval source is flat-only: a first fill stops the account chain | `account_interval.py:117-118` |
| The coordinator accepts only `rehearsal` | `coordinator.py:281`; built only at `rehearsal.py:368` |
| No odds-plan provider is shipped, so `prepare` refuses | `launch.py:222-225`; `rehearsal.py:374` |
| No strategy has passed a prospective study | `docs/first-trade-owner-checklist.md:6` |

Separately, and not a first-trade blocker: progress above `A` needs the post-activation spec (7.1, 12.1).

**Sequencing.** Each of the first three needs more signed-code changes. Every closure change needs a new `code_approved` and voids review documents (`review_auth.py:171`); every profile-schema or capture-file change voids the study (`strategy.py:505-508`; `study.py:59-61`). Recommended: merge this change and the remaining blockers first, then sign code once and run the prospective study once, after the last profile-schema change. If the universe design of pull request 19 is adopted, its pull requests are among those changes (12.5).

## 8. Files to change

A check for the implementation pull request: `git diff --stat origin/main -- core/odds core/compliance tools/signer` must be empty.

### 8.1 Signed code closure (D14, `owner.py:789-799`)

| File | Change |
|---|---|
| `execution_control/risk.py` | `RiskPolicy.principal_loss_budget`, a required `Decimal` with no default. Shape (`:172-175`) and range (beside `:196-197`) validation. The `H < A` arm (`:274`). Docstring wording (`:30`, `:217-218`). |
| `execution_control/controller.py` | `_snapshot_risk`: the agreement reason (2.5b), the owner-log halt reason and the halt re-send (6.3). `_authorize`: the cash-floor rule (4.1). No journal row shape changes, so existing journals still fold. |
| `execution_control/session.py` | The agreement check, before the card and inside the transaction (2.5a). The named odds refusal (4.5). `PreparedSession` is unchanged. |
| `execution_launch/profile.py` | `PolicyInputs` field (`:52-63`) and `_POLICY_NUMBERS` (`:30-32`); three preflight issues and the hard check (3.2); delete `:435-437` (3.3). The template gains the key automatically. |
| `execution_launch/strategy.py` | `ForwardProtocol.cash_floor_quote`; validate and parse it; the cap in `_simulate` (`:354-355`); bump `EVALUATOR_REVISION` (`:27`). |
| `execution_launch/study.py` | Set `cash_floor_quote` beside `initial_cash_quote` (`:257`). |
| `execution_launch/workflow.py`, `review_request.py` | One clause beside the capital equality (`workflow.py:180`; `review_request.py:247-249`). |
| `execution_launch/runner.py` | One clause in `_assess` (`:146-148`); the three plan pins (`:203-206`). |
| `execution_launch/driver.py` | One clause in `_identity` (`:168-171`); the cap in `_sized_signal` (`:222-223`); with PLB-O2 the first-bar rule (`:326-328`). |
| Not changed | `core/compliance/*`, `core/odds/*`, `execution_accounts/*`, `execution/*`, `execution_orders/*`, `execution_network/*`, `tools/signer/sign.py`, and `execution_launch/coordinator.py` and `tools/owner/*` (except for the two files of the next row, in the case of 10.2 only, and for `coordinator.py` if the universe design is adopted with the default of PLB-O16). The count of ten in 0.1 and 12.4 is for the fixed driver: in that universe case it is at least eleven (12.5). `execution_launch/continuous_guard.py` needs no edit: it calls `evaluate` (`:293`, `:492`), is not live (`:173-175`), and only its tests change. `execution_launch/continuous_guard_commit.py` needs no edit either: it recomputes the plan through `plan_continuous_guard` (`:340`) and no shipped module imports it. Its two controller-side lines stay as they are: a pending guard transaction refuses buys (`controller.py:614`) and session preparation (`session.py:167`). |
| Only if step 0 finds a journaled floor above `C` | One command name in `tools/owner/launch.py` (`OwnerRuntime.command`, `:256-263`) and one public Coordinator method that runs the existing `Controller.approve_floor_relaxation` (`controller.py:443-479`) inside an operator unit (`coordinator.py:547-564`), because the account read at `controller.py:455` needs a published frame (`coordinator.py:258-261`). It takes no amount: the target is `W0 - LB` from the coordinator's loaded profile. Before any preparation it passes no session id. Two more closure files, in this case only. Same pull request, so one `code-approve` covers it. Not built otherwise (PLB-O14): a journal floor above `C` that appears later (10.3) then costs a new closure change, `code_approved` and reviews. Once built it stays in the closure, and it is the path by which a raised `A` undoes activation (2.3). |

### 8.2 Outside the closure

| File | Change |
|---|---|
| New read-only script, proposed `tools/floor_state_check.py` | The step 0 check (9.1). It is under no closure directory and nothing in the closure imports it, so merging it does not unsign today's code. It ships first, in its own pull request. |
| `tools/research/equity_policy_preview.py` | Research mirror: add the budget to `Policy` (`:19-25`) and change the arm (`:149-150`). |
| `tools/research/test_equity_policy_preview.py` | Rewrite the two trailing-floor pins (`:59-62`, `:142-143`). |
| `tools/research/prepare_launch_example.py` | Synthetic example builder. Give its `PolicyInputs` (`:57-61`) an invented `principal_loss_budget` that satisfies 3.2, and give its `ForwardProtocol` (`:66-76`) `cash_floor_quote` equal to its `initial_cash_quote` minus that budget. Both are needed: `ForwardProtocol` has no defaults (`strategy.py:97-128`), and the new clause of 3.2 needs `C == W0 - LB`. Without them the tool exits 2 (`tools/research/prepare_launch_example.py:202`), and the documented walkthrough (`docs/launch-workflow.md:19-22`) and `tests/launch_workflow.py:218-252` fail. Nothing in the closure imports it. |

### 8.3 Docs and tests (implementation pull request)

Every row of 1.3 except the dated plans, plus: `docs/launch-profile.example.json` (new key, null); `docs/launch-profile-contract.md:12` (field list); `docs/automatic-runner-contract.md:56-61` (the three pins); `docs/launch-workflow.md:50-55` (the principal loss budget may not stay null, and the protocol's cash floor joins the values that must agree with the profile); `docs/execution-runbook.md:67-68` (agreement, cash rule); `docs/first-trade-owner-checklist.md` (state check and order rule); `docs/forward-strategy-validation.md:32-33` (the evaluator revision name, `forward-paper-v1` today, follows the bump of 8.1; a protocol frozen with the old name is refused, `strategy.py:135`) and `:99-101` (paper quantities are also constrained by the cash floor). No `.md` file is in the D14 hash. New files are LF, UTF-8, no BOM. `README.md` is CRLF: Edit tool only, and the suite names its guard tests read must stay.

Tests are in section 11. The implementation plan starts with a measured baseline run of the suite and a measured list of affected tests (11.3). README test counts and `qa/acceptance_results.json` change only after a measured full run.

## 9. The owner's sequence of acts

Every act below is the owner's. No tool and no agent performs any of them.

### 9.1 Step 0: read-only state check

One shipped command shows part of this state. The daily `python -m core.compliance.rules --check` reports whether the owner log verifies (S1) and whether the code on disk is the latest `code_approved` (`core/compliance/rules.py:962-970`), which rule 2 of 9.2 needs. It is not read-only: it goes through `load_context`, which writes the usual approved-tables snapshot (`owner.py:1024-1028`). No shipped standalone command shows halts, effective limits, journal floors or the baseline floor (S2 to S12): `python -m execution_launch.cli` reads only an explicit profile file (`execution_launch/cli.py:7-8`) and `python -m execution_launch.deployment` reads no owner log (`execution_launch/deployment.py:10`). The smallest addition is one read-only script (8.2). It does not exist at the base commit, so step 0 can be run only after this spec is approved (9.3, step 1) and that script is merged in its own pull request.

- **Inputs.** The intended `C`, `A` and `W0` as typed arguments, and `--state-root` and `--head-root` like the existing owner commands (`launch.py:298`, `324-325`). The state root is the home and must equal the configured `TRADEGEN_HOME` (`baseline_store.py:73`); that is how a home is selected. Optional: a candidate anchor file with its reviewed head, read with the `restore_state` call that `setup_account` uses (`launch.py:141`), and an armed session id. When a candidate is given, S4, S7, S10 and S11 read it in place of the store.
- **Output.** Fixed codes and relations (above, equal, below, none, unreadable), never amounts, paths or digests. Exit 0 when every row was read and 2 when any state could not be read (the convention at `launch.py:341-344`); the owner reads go or no-go from the table. With `--gate` it exits 0 only when S2 and S3 read `none`, S4 `below` or `none`, S6 and S7 `equal`, S10 `equal` or `below` and S11 `at or above`, so a prepared script can stop on it (9.3, step 10).
- **Reads.** The pure owner-log fold (`owner.verify_log`, `owner.owner_state`; `owner.py:279`, `464-479`), not `load_context`. `Journal.snapshot()`, which creates nothing (`store.py:232-253`), not a transaction, which initializes a journal (`store.py:186-194`). `BaselineHead.read()` for the trusted head (`execution_launch/baseline_head.py:228-231`), then `CheckpointStore.load(expected_head=...)`, which requires it (`baseline_store.py:126-128`). Neither call creates anything.

| # | Question | Go | No-go, or route |
|---|---|---|---|
| S1 | Does the owner log verify? | yes | No: nothing below is reliable. Repair first. |
| S2 | Any `system_halt` in the owner log? (`owner.py:505`, `562`) | none | **Stop.** This design cannot take effect on this owner log (9.4). |
| S3 | Any `halt` row in the control journal? (`controller.py:154`) | none, or no journal | **Stop.** Buys are refused through this journal (`controller.py:614-615`), and 6.3(b) will send the halt to the owner log. |
| S4 | Journaled peak, and the peak of the stored or candidate anchor, against `A` | none, or below | At or above: **do not sign `L = C` on this home.** The budget regime cannot apply there while `A` is unchanged (2.3), and with `L = C` the first loss beyond `E - F_effective` halts for good (2.4). This is owner procedure; no code blocks it. |
| S5 | Last journaled effective floor against `C` | none, equal or below | Above: the relaxation route (10.2). Before any observation, confirm equity is not below that floor (S11). If it is, **stop**: any observation halts for good, today as well, and this home cannot adopt. |
| S6 | Effective signed limits today, after the D12 fold | both set; floor above `C` before step 6, equal from step 7 | Unset: the first setting is a loosening too (`profile.py:446`). Below `C`: entries blocked (2.5); sign the right value. |
| S7 | Baseline store floor against `C` | no store before step 10; `equal` after it | `none` only when no checkpoint file exists and the head reads `HEAD_NOT_INITIALIZED` (the test of `launch.py:118-127`). A checkpoint with a missing or mismatched head prints `unreadable`. Above, null or unreadable: the documented re-anchor with a floor of `C` (`baseline_store.py:176-178`; `docs/account-baseline-integration.md:200-215`), **before anything observes**, because the first observation journals a higher floor for good (10.3). Below is harmless (`risk.py:277`) but is not what 3.1 asks for. |
| S8 | Any armed session? (`owner.py:513-522`) | none | **Stop** if the arming process has ended. While it still runs, use `disarm` in its owner console (`coordinator.py:679-696`) and confirm `owner_disarm_recorded: true`; a journal-only kill leaves the owner log armed (`controller.py:864-870`). `stop` and `close` do not disarm (`coordinator.py:627-641`). No shipped command disarms a session left by an ended process: the console loads no session from disk (`docs/owner-runtime-operations.md:109-110`), the signer signs no system entry (`tools/signer/sign.py:240-241`) and the fold never expires an arming (`owner.py:512-522`). That state refuses every later preparation (`session.py:138-139`, `156-159`) and the relaxation route (`controller.py:457-459`). It needs its own reviewed change, out of scope here. Never hand-edit the owner log. A loosening does not count inside a session armed on or before its date (`owner.py:523-528`). |
| S9 | Is this the default home, and is there a control journal in it? Two fixed codes: home default or custom; journal absent or present | default home, journal absent | Custom home: a rehearsal may have run on this owner log and journal (`runner.py:281-284`; `rehearsal.py:325`), and a journal here came from one (`coordinator.py:281`, `332`). Default home with a journal: no shipped path wrote it (10.1); find out what did before going on. In both cases S2 to S5 on this home decide. Run the check on every home that will trade. |
| S10 | Equity of the stored or candidate anchor against `W0` | equal, or below | Above: the surplus is extra money that can be lost (6.1). Withdraw it before the anchor is captured; after seeding, a withdrawal is an external flow and stops the chain (`baseline.py:278-283`). Otherwise a new profile with a higher `W0`, or written acceptance of `LB` plus the surplus. |
| S11 | Equity of the stored or candidate anchor against the highest of its own floor, the last journaled floor and the effective `L` | at or above | Below: **do not observe.** The first observation halts for good (`controller.py:416-425`). Move the store aside by the documented re-anchor. |
| S12 | Given an armed session id: the signed floor inside that session (`owner.owner_state` with that id) against `C` | equal | Not equal: the arming, or a later owner-log line, is stamped on or before the loosening's date (2.5a). Disarm and prepare again before the runner starts. |

### 9.2 The hard order rule

**The hazard exists on today's main.** With the old signed code and an effective lowered `L`: the card returns a first stake (`costs.py:271-272`, `357`), preparation passes (`session.py:140-142`), the engine floor below `A` is still the peak, a buy at `E == floor` is admitted because the breach test is strict (`risk.py:279`; `controller.py:622-627`), and the first fee puts equity below the peak. That is a permanent halt (`controller.py:420-425`) which also pins `L` at the halted floor for good (`owner.py:557-558`). Today the other blockers of 7.4 stand in front of it; the order of acts must not depend on them.

Therefore:

1. Keep the runtime stopped from the merge until the anchor is seeded and the state check has passed on it (9.3, step 10): no bootstrap, no observation in this home.
2. `code-approve` strictly before the `limit_set` that lowers the floor.
3. On the next Seoul date, verify the effective limit with the state check before any anchor or preparation. The advisory date is not proof (`profile.py:442-460`).

While `H < A` the new code refuses a mis-sequenced state instead of relying on this procedure: rule 2.5 blocks whenever the signed floor, the journal or the anchor disagrees with `C`, and rule 4.1 compares every buy with the higher floor. Table 10.3 lists each state. Two states are not refused by new code:

- **(i) Old code still signed, `L` already lowered.** That is what rule 2 is for.
- **(ii) `H >= A` with `L = C`.** There neither 2.5 nor 4.1 applies, the card passes because `L` is below the stake, a buy is admitted while `E >= F_effective`, and a loss larger than `E - F_effective` (one fee when `E` is at the floor) halts for good (2.4). S4 is the procedure for it.

A third state is refused only after damage is possible: an anchor floor above `C` is journaled by the first observation (10.3). That is why rule 1 keeps the runtime stopped until the seeded anchor is checked.

### 9.3 The acts

| # | Act | Timing rule |
|---|---|---|
| 0 | State check (9.1) | After step 1 and after the script of 8.2 is merged in its own pull request. Before any other implementation work starts. |
| 1 | Approve this spec by merging its pull request | Docs only. Signs nothing. |
| 2 | Approve the merge of the implementation pull request(s) | A merge is not a code signature (`docs/first-trade-owner-checklist.md:30-31`). See 7.4 on doing this once. |
| 3 | Keep the runtime stopped until step 10 is done | Rule 1 of 9.2. |
| 4 | `code-approve` on the new closure hash | Strictly before step 6. |
| 5 | Private profile: set `principal_loss_budget`, bump `policy.version`, point `policy.source_sha256` at the approved spec | Before the study freeze. Unsigned. |
| 6 | `limit_set` with `total_loss_floor_krw = C` and the daily value restated | Only after step 4, with nothing armed. A loosening: it counts from the Seoul date after its own, and never after a halt (`owner.py:525-528`). |
| 7 | Next Seoul date or later: run the state check. S6 must read "equal" and S4 "below" or "none". Nothing is seeded yet | An anchor cannot be seeded and left: the chain needs an observation within 30 s of it (step 10). |
| 8 | Study: freeze with the new profile, publish the commitment, capture, select | Every earlier study is void (`strategy.py:135`, `505-508`). It may run while step 7 waits. |
| 9 | Export the driver, review request, audit, `review-approve` | After step 4; the review binds the code hash (`review_auth.py:171`). |
| 10 | On the day of the session, with the study and review artifacts ready, from one prepared script: capture the anchor with `approved_effective_floor = C`; state check with `--gate` on the candidate; `setup-account`; state check with `--gate` on the seeded store; start the runtime. A non-zero exit stops the script | Seed age at most 30 s (`launch.py:142`). The startup unit must observe within 30 s of the anchor, and the runtime build refuses an older one (`docs/account-baseline-integration.md:165-172`; `rehearsal.py:342`). No anchor read in the last minute before Seoul midnight or a pending 22:00 KST cutoff (`docs/account-baseline-integration.md:172-175`). Setup happens once (`launch.py:118-127`; `baseline_store.py:165`). A missed 30 s, or a failed gate after seeding, means the documented re-anchor (`docs/account-baseline-integration.md:200-215`) before anything observes, again with a floor of `C`. Every later re-anchor passes the same gate. |
| 11 | `prepare` after the startup unit, then `session_armed` on the returned id, then S12 on that id before the runner starts | On the preparation date (`session.py:220-221`), which 2.5(a) forces to be after the date of step 6. |

Steps 8 to 11 are the existing gates reacting to changed digests. They cannot complete today for the reasons in 7.4.

### 9.4 What a halt blocks

| Act | After an owner-log `system_halt` | After a journal `halt` only (the owner-log write failed or was never attempted) |
|---|---|---|
| `limit_set` that lowers `L` | Can be signed. A loosening signed after the halt never counts (`owner.py:525-528`); `L` stays at or above the halted floor (`:557-558`). | Still counts under D12 until 6.3(b) lands the halt in the owner log. From then `L` is held at or above the halted floor (`:557-558`). |
| `approve_floor_relaxation` | Refused (`controller.py:457-459`). | Refused (`controller.py:453-454`). |
| `review-approve` | Can be signed; verification refuses (`review_auth.py:164-166`). | Verification passes until the halt is in the owner log. |
| `prepare` | The launch `prepare` refuses at `runner.py:199-200`, because review verification refuses (`review_auth.py:164-166`; `strategy.py:543-544`; `runner.py:158-161`). A direct `prepare_session` is not refused. | Not refused. The session is inert because its buys are refused. |
| Any buy | Refused under any control journal of the same home (6.3a). | Refused through that journal (`controller.py:614-615`). |
| A new anchor, a fresh control journal or another journal directory under the same `TRADEGEN_HOME` | Does not help: the halt is in the owner log (`owner.py:34-40`). | A fresh journal has no latch. 6.3(b) closes this on the next observation of the halted journal. |
| Spec approval, merges, `code-approve`, a tightening `limit_set`, sells | Not blocked. | Not blocked. |

A different `TRADEGEN_HOME` has its own owner log and is outside this guarantee (6.3). If step 0 finds an owner-log halt, this design cannot be adopted on that owner log. A journal-only halt is also a stop at step 0 (S3). Recovery after a halt is out of scope.

## 10. Migration and fail-closed behaviour

### 10.1 No migration code

"No journaled floor above `C` and no halt" is the expected case, to be confirmed by step 0. A `Controller` is built only in the coordinator (`coordinator.py:332`), the coordinator accepts only `rehearsal` (`coordinator.py:281`) and is itself built only by the rehearsal tool (`rehearsal.py:368`), and a rehearsal must use a home outside the default one that is also the active home (`runner.py:278-284`). So no shipped path writes a control journal in the default home. In that case: seed the first anchor with a floor of `C`; the first observation journals `C`; nothing is relaxed.

### 10.2 If step 0 finds a journaled floor above `C` and no halt

The only way to lower a journaled floor is the existing `approve_floor_relaxation` (`controller.py:443-479`): no halt, nothing armed, `L` exactly equal to the target, a snapshot from an earlier Seoul date whose calculated floor already equals the target, and the current policy returning that target (`:453-471`). Only the new code journals a calculated floor of `C` below `A` (today's arm requests the peak, `risk.py:274`), and the order rule (9.2) allows no observation before the lowered floor counts. So the order of acts is:

- **Day D:** the `limit_set` (`code-approve` on or before it).
- **Day D+1 or later:** the state check (S6 "equal"; S5 still reads "above"; S11 "at or above", because this observation compares equity with the old journaled floor and a breach halts for good, `controller.py:416-425`). Then the anchor and runtime start of step 10, with a floor of `C`; the study and review artifacts must be ready, because the runtime cannot be built without them. The anchor does not lower the effective floor, because the journal still holds the old one (`controller.py:391-395`); an anchor that still carried the old floor would raise the journal floor again. The startup observation journals the pending snapshot, and 2.5 blocks entries.
- **A later Seoul date:** the relaxation command, with nothing armed (`controller.py:457`, `460-466`). It runs inside a coordinator unit, so the runtime must be running then, after a new anchor if it was stopped. S5 then reads "equal", and only then can a session be prepared (2.5a).

The method has no caller today (`tests/control_controller.py:288-305` exercises it); the command of 8.1 is built only in this case. It sits in the rehearsal-only coordinator, so it reaches only the journal of the home that coordinator runs in (S9). No file move replaces it: `docs/continuous-guard-commit-contract.md:163-165` forbids a re-anchor that lowers a ratcheted floor.

### 10.3 Every half-migrated state fails closed

| State | Result | Evidence |
|---|---|---|
| Old profile JSON on new code | Incomplete (`POLICY_INPUT_REQUIRED`). Runner, study freeze, study review and rehearsal refuse on the preflight. The review-request builder only records preflight reasons; an old profile is stopped there by the contract-digest match (no protocol can be frozen from an incomplete profile) and the new capital clause, and a request carrying any blocker other than `SIGNED_CONTEXT_REQUIRED` is refused at approval. Missing never means zero | `profile.py:340-343`, `379-380`; `runner.py:198`, `414-415`; `study.py:251-252`; `execution_launch/study_review.py:166-167`; `rehearsal.py:348`; `execution_launch/review_request.py:243-249`, `255`, `281`; `review_auth.py:88` |
| New profile JSON on old code | Unknown key refused | `profile.py:118-120`, `224` |
| A policy with a bad budget reaches the engine | No floors, no snapshot, entry blocked; the signed floor is still monitored | `risk.py:223-225`; `controller.py:410`, `416-420` |
| Session prepared under the old policy | "session preparation stale or mismatched" | `session.py:217` |
| Old study, protocol, review or driver identity | Refused by contract digest, evaluator revision, protocol keys or code hash | `strategy.py:505-508`, `135`, `567-569`; `review_auth.py:171` |
| Signed floor not yet lowered, lowered today, or never set, while `H < A` | `SESSION_PREPARATION_LOSS_FLOOR_DISAGREES`, raised before the card (2.5a); 2.5(b) blocks entries. At `H >= A` no equality is checked and the card decides: `STUCK_AT_START` when `L >= stake`, `LIMITS_UNSET` when a limit is unset | `session.py:135-142`; `owner.py:525-528`; `costs.py:271-272`; `core/odds/plan.py:353-355` |
| Signed floor lowered, journal or anchor floor higher, while `H < A` | `LOSS_FLOOR_SETTINGS_DISAGREE` on every observation; preparation refuses; the cash rule compares with the higher floor | 2.5; 4.1; `controller.py:391-395` |
| Signed floor below `C` | Preparation and entries blocked | 2.5 |
| Session armed with a back-dated stamp, or a later owner-log line stamped back | The loosening does not count inside it, so the signed floor there is the earlier one. With equity at or above that floor, or with no earlier signed floor, the buy is refused (2.5b). With equity below it, the existing breach test halts for good at that floor, as today's code would; `observe` carries no session id and shows nothing first | `owner.py:490-492`, `523-528`, `557-558`; `controller.py:612`, `622-624`, `416-425`, `438` |
| Anchor seeded with a floor other than `C` | Higher: the first observation journals it. If `E` is below it, that is a permanent halt. Otherwise entries are blocked until `approve_floor_relaxation`; a re-anchor alone does not lower it. Lower: the effective floor is still `C` | `controller.py:391-395`, `410-415`, `217-226`; `risk.py:277` |
| `A` raised above the journaled peak after activation | `LOSS_FLOOR_SETTINGS_DISAGREE`; entries blocked, no halt, floor unchanged unless the relaxation is approved (2.3) | `risk.py:277`; `controller.py:457-471` |
| Guard checkpoint from the old policy | `GUARD_AUTHORITY_EPOCH_CHANGED`; the guard is not live | `execution_launch/continuous_guard.py:372`, `173-175` |
| Journaled or anchor peak at or above `A`, with `L = C` | **Not refused.** The first loss beyond `E - F_effective` halts (2.4, 9.2) | `controller.py:622-627`; `risk.py:274-279` |
| Account cash above `W0` at the first anchor | **Not refused.** The surplus can be lost (6.1); S10 is the check | `driver.py:326-328` (the equality that PLB-O2 removes) |
| Old code still signed, `L` already lowered | **Not refused. The hazard of 9.2.** | 9.2 |

Except for the three rows marked "Not refused", none of these loosens a floor and none writes a halt that today's code would not write.

## 11. Invariants and tests

### 11.1 Invariants and what enforces each

| # | Invariant | Enforcing site |
|---|---|---|
| I1 | While `H < A` the requested floor is exactly `C`, whatever `H` and `E` are. | `risk.py:274` (changed arm) |
| I2 | A missing or malformed `LB` yields no floors and no snapshot. It is never a default and never a halt through the formula. | `risk.py:172-175`, `196-197` (new clauses), `223-225`; `controller.py:410` |
| I3 | The effective floor never decreases without the approved relaxation; with `A` unchanged, activation raises it for good (2.3). | `risk.py:277`; `controller.py:217-226`, `391-395` (existing) |
| I4 | While `H < A` no session is prepared and no buy is admitted unless `L == C` and `F_effective == C`. | `session.py` (new: before `simulate`, `:135-140`, and at `:155-159`); `controller.py` `_snapshot_risk` (new) through `:622-624` |
| I5 | While `H < A`, after every admitted buy, settled cash less pending buys is at or above `G`. | `controller.py` `_authorize` (new, beside `:638-640`), at reserve and dispatch (`:658`, `:684`) |
| I6 | While `H < A` and 4.6 holds, `E >= C` on every price path. | I4 and I5 |
| I7 | The driver never proposes a buy that I5 refuses, and the paper study sizes the same quantity. The stake cap is outside this invariant (4.2). | The shared cap term at `driver.py:222-223` and `strategy.py:354-355`; `driver.py:170`, `321-323` |
| I8 | A halt recorded in the owner log is final and blocks buys whatever control journal is in use under the same `TRADEGEN_HOME`. A halt that is only in the journal blocks buys through that journal and is re-sent to the owner log. | 6.3(a); `owner.py:525-528`, `557-558`. Journal only: `controller.py:614-615`; 6.3(b) |
| I9 | A disagreement, a budget refusal or an invalid input never writes a halt and never lowers a floor. | The new checks append nothing. On every shipped path only `controller.py:421-425` writes a `halt` row; the two other writers, `Controller.halt` (`controller.py:882`) and the guard commit (`execution_launch/continuous_guard_commit.py:367`, journal row only, no `system_halt`), are not edited and have no shipped caller |
| I10 | At preparation the card never shows more headroom than `E - C`, and the account is flat, so `E` is its cash. | `runner.py:203-206` (the three pins, new) and I4. Reserved cash and open orders are refused at tick time, not at preparation (`driver.py:317-323`) |

### 11.2 Tests by behaviour

Names are proposals. Each name is one behaviour.

- **Engine (`tests/control_risk.py`).** `test_floor_below_activation_is_principal_minus_budget` (several `H` in `[W0, A)`); `test_gain_below_activation_does_not_raise_the_floor`; `test_floor_equality_is_not_a_breach_and_one_unit_below_is`; `test_activation_boundary_uses_the_activation_arm` (`H == A` against just below); `test_activation_raises_the_effective_floor_at_once_without_pending`; `test_higher_supplied_floor_still_wins_and_reports_pending`.
- **Engine, inputs.** `test_missing_or_malformed_budget_returns_no_floors` (none, int, float, NaN, zero, negative, `LB >= W0`, fractional `W0 - LB`); `test_activation_equal_to_principal_is_still_accepted_by_the_engine`; `test_daily_branches_do_not_depend_on_the_budget`; `test_recovery_floor_is_the_day_open_not_the_budget_floor`.
- **Controller, agreement (`tests/control_controller.py`).** `test_entry_needs_signed_and_effective_floor_equal_to_the_budget_floor` (signed higher, signed lower, signed unset, anchor floor higher, journal floor higher; each reports `LOSS_FLOOR_SETTINGS_DISAGREE` on `observe`); `test_floor_disagreement_never_halts_and_never_lowers`; `test_no_agreement_check_at_or_above_activation`; `test_sells_ignore_disagreement_budget_and_halt_reasons`; `test_existing_journal_rows_still_fold`.
- **Controller, cash rule.** `test_buy_admitted_when_cash_after_equals_floor_and_refused_one_lot_more`; `test_cash_rule_counts_pending_buys_and_the_fee`; `test_cash_rule_uses_the_higher_of_effective_and_signed_floor`; `test_unrealized_gain_does_not_enlarge_headroom` (settled cash, not equity); `test_cash_rule_refusal_writes_no_halt`; `test_cash_rule_is_checked_again_at_dispatch`.
- **Controller, hazard regressions.** `test_full_headroom_position_marked_to_zero_does_not_halt`; `test_first_fee_does_not_halt`; `test_lowered_signed_floor_with_higher_journal_floor_refuses_and_writes_no_halt` (the mis-sequenced case).
- **Controller, halt and activation.** `test_owner_log_halt_blocks_buys_on_a_fresh_journal`; `test_journal_halt_is_resent_to_the_owner_log_once`; `test_one_observation_at_activation_ends_the_budget_across_restart`; `test_open_position_can_halt_after_activation` (documents PLB-O4); `test_higher_anchor_floor_is_journaled_and_survives_a_reanchor` (documents 10.3). The existing relaxation test stays as it is (`tests/control_controller.py:288-305`).
- **Session and runner.** `test_preparation_refuses_until_signed_floor_equals_budget_floor` (includes a signed floor below `C`, and `L == C` with a last journaled floor above `C`; asserts the code and that no `session_prepared` row was appended); `test_preparation_refuses_on_the_signing_date_and_passes_the_next_seoul_date` (the floor in force before is `W0`; asserts `SESSION_PREPARATION_LOSS_FLOOR_DISAGREES`, not `..._ODDS_STUCK_AT_START`, on the signing date); `test_preparation_at_or_above_activation_needs_no_equality`; `test_back_stamped_arming_is_refused_at_the_buy` (equity at or above the earlier signed floor: refused, no halt); `test_back_stamped_arming_below_the_old_floor_halts`; `test_preparation_names_the_odds_refusal`; `test_stop_based_plan_is_refused_for_launch`; `test_stake_above_equity_is_refused_and_stake_above_principal_still_is`; `test_preparation_with_inventory_is_refused`.
- **Profile.** `test_profile_without_budget_is_incomplete_and_builds_no_policy`; `test_budget_range_and_whole_krw_floor`; `test_activation_equal_to_principal_is_a_preflight_block`; `test_budget_below_one_minimum_order_is_a_preflight_block`; `test_budget_changes_both_profile_digests_and_the_policy_digest`; `test_template_and_example_json_list_the_new_key`.
- **Paper evaluator and fixed driver.** `test_paper_buy_is_capped_by_cash_minus_floor`; `test_paper_and_driver_size_the_same_quantity_under_the_cap`; `test_driver_order_always_passes_the_controller_rule` (a property over books, lots and fees); `test_capped_quantity_below_minimum_is_a_hold`; `test_driver_refuses_protocol_floor_not_principal_minus_budget`; `test_old_evaluator_revision_and_old_protocol_json_are_refused`; `test_driver_cap_applies_above_activation`. Documenting tests: `test_terminal_dust_stops_the_runner_and_blocks_the_next_window` (end state 2 of 4.5); `test_driver_order_above_session_stake_is_refused_and_stops_the_runner` (the named limit of 4.2). With PLB-O2: `test_window_opens_flat_with_cash_at_or_above_the_floor`; `test_window_refuses_inventory_or_cash_below_the_floor`.
- **Odds inputs, with no `core/odds` edit.** `test_first_stake_positive_exactly_when_headroom_covers_minimum_and_cost` (for a full fixed fraction with the stake equal to cash; a smaller fraction is cause (b) of 4.5); `test_ceiling_with_budget_floor_is_lb_over_t_minus_w0_plus_lb`; `test_headroom_between_base_and_stress_cost_trades_nothing_in_the_stress_column`. The existing odds suites must pass unchanged; that is the evidence that existing cards are untouched.
- **Cross-engine (new file).** `test_loss_from_principal_never_exceeds_budget_over_random_paths`: random prices including a fall to zero and gaps, admitted orders only, below `A`.
- **Rewritten, because they pin the trailing rule (by reading, not by running).** `tests/control_risk.py:54`, `:134`; the tests of `tests/control_continuous_guard.py` that start at `:130`, `:145`, `:153`, `:170`, `:196`, `:291`, `:313` (there only the halt assertion at `:320` pins the rule); the tests of `tests/control_continuous_guard_commit.py` that rely on the default path of that file's `build` helper ending in a halt, or on the floor rising with the peak below activation (it imports `build` and `seed` at `:23`; for the halt, at least those starting at `:102`, `:133`, `:167`, `:180`, `:265`, `:357`; for the rising floor, the one starting at `:190`, where only `:222-225` pin the rule); `tools/research/test_equity_policy_preview.py:59-62`, `:142-143`; the low-floor case of `tests/launch_profile.py:142-152`.

### 11.3 Mutations and the measured baseline

Each named wrong implementation must make the named test fail.

| Wrong implementation | Test that must fail |
|---|---|
| Budget arm reverted to the peak | `test_gain_below_activation_does_not_raise_the_floor` |
| `H < A` changed to `H <= A` | `test_activation_boundary_uses_the_activation_arm` |
| `max(F_prior, F_raw)` replaced by `F_raw` | `test_higher_supplied_floor_still_wins_and_reports_pending` |
| Breach `<` changed to `<=` | `test_floor_equality_is_not_a_breach_and_one_unit_below_is` |
| Missing budget treated as zero, or as the trailing rule | `test_missing_or_malformed_budget_returns_no_floors` |
| Cash rule removed, or `<` changed to `<=` | `test_buy_admitted_when_cash_after_equals_floor_and_refused_one_lot_more` |
| Pending buys or the fee dropped from the cash rule | `test_cash_rule_counts_pending_buys_and_the_fee` |
| Signed floor dropped from `G` | `test_cash_rule_uses_the_higher_of_effective_and_signed_floor` |
| Cash rule computed from equity instead of settled cash | `test_unrealized_gain_does_not_enlarge_headroom` |
| Agreement `==` weakened to `<=` or `>=` | `test_entry_needs_signed_and_effective_floor_equal_to_the_budget_floor` |
| Agreement applied at `H >= A` | `test_no_agreement_check_at_or_above_activation` |
| A disagreement or a budget refusal made to halt, or raised as an error in `observe` | `test_floor_disagreement_never_halts_and_never_lowers`; `test_cash_rule_refusal_writes_no_halt` |
| Agreement check before the card removed | `test_preparation_refuses_on_the_signing_date_and_passes_the_next_seoul_date` (the card would answer `STUCK_AT_START` instead of the named code) |
| Agreement check inside the transaction removed | `test_preparation_refuses_until_signed_floor_equals_budget_floor` (the case `L == C` with a journaled floor above `C`) |
| Owner-log halt check removed; halt re-sent on every observation | `test_owner_log_halt_blocks_buys_on_a_fresh_journal`; `test_journal_halt_is_resent_to_the_owner_log_once` |
| Cap removed from the driver only or the evaluator only; protocol floor not checked against the profile | `test_paper_and_driver_size_the_same_quantity_under_the_cap`; `test_driver_refuses_protocol_floor_not_principal_minus_budget` |
| Budget left out of `_POLICY_NUMBERS` | `test_budget_changes_both_profile_digests_and_the_policy_digest` |
| Equity pin on the stake dropped | `test_stake_above_equity_is_refused_and_stake_above_principal_still_is` |
| Flat pin dropped | `test_preparation_with_inventory_is_refused` |
| Driver or evaluator cap made regime-aware | `test_driver_cap_applies_above_activation`; `test_paper_and_driver_size_the_same_quantity_under_the_cap` |
| First-bar rule left at `== W0` (PLB-O2) | `test_window_opens_flat_with_cash_at_or_above_the_floor` |

**Measured baseline first.** Nothing was run for this spec. The implementation plan's first task is a measured run of the existing suite and a measured list of the tests each change affects. By reading only:

- The shared buy fixtures sit above activation (`tests/control_session.py:45-61`; `tests/orders_lifecycle.py:209-222`; `tests/launch_runner.py:66-69`; `tests/launch_coordinator.py:231-232`). The two controller fixtures should need only the new required field. The `launch_runner` and `launch_coordinator` fixtures also take the new protocol field and pass through the evaluator cap (`tests/launch_runner.py:43`). Driver and evaluator tests change in every regime (2.4).
- **Known exception 1:** `tests/control_controller.py:273-278` has `H < A` with `L = W0` and an anchor floor above `C`. Rule 2.5(b) adds `LOSS_FLOOR_SETTINGS_DISAGREE`, so its `not new_entry_blocked` assertion fails. It needs a rebase to `C` or a move to `H >= A`.
- **Known exception 2:** the reviewed-profile helper at `tests/launch_coordinator.py:1103-1118` has `A == W0`. `LOSS_BUDGET_NEVER_APPLIES` enters the review request's `profile_blockers`, which `review_auth.py:88` refuses, and makes the profile incomplete. It is used at `tests/launch_coordinator.py:1179`, `tests/launch_coordinator.py:1223` and `tests/launch_owner_rehearsal.py:102`. It needs `A > W0`, and a rebase of the signed and anchor floors to `C` only if `A` is put above the fixture's seeded peak.
- The keyword `ForwardProtocol(...)` fixtures need the new field (`tests/launch_capture.py:38`; `tests/launch_strategy.py:31`; `tests/launch_study.py:82`), and `tests/launch_workflow.py:218-252` must keep passing once the example builder of 8.2 is updated.
- **Reviewed pins.** `tests/renewal_boundaries.py:32` and `:35` pin a hash of the initialization surface of `risk.py` and `profile.py`: imports, module-level assignments, class fields with their defaults, decorators and function signatures, not function bodies. The new `RiskPolicy` field, the new `PolicyInputs` field and the `_POLICY_NUMBERS` entry change both. Two tests in `tests/control_guards.py` (`:195`, `:200`) then fail until each pin is reviewed and updated by hand, never regenerated to accept a failure (`tests/renewal_boundaries.py:7-8`). The changed function bodies (the floor arm, the validation clauses, the preflight issues) are outside that pin.

The plan must budget these. The run decides the full list; nothing here is assumed. This spec quotes no test counts.

## 12. Out of scope, open decisions, risks, cost

### 12.1 Out of scope

- **A post-activation spec:** sizing, card floor and stake above `A`, a stake above `W0`, and recording activation by code.
- **Stage transitions and external flows:** withdraw at a target, restart with new capital, any deposit (6.2).
- **Other venues.** KIS, OKX and any venue with fixed per-order charges need the exit reserve term and their own review. The coordinator accepts Upbit KRW spot only (`coordinator.py:282-283`).
- **The other first-trade blockers** (7.4), automatic exits, and recovery after a halt: no un-halt exists and none is proposed.

### 12.2 Open owner decisions

The ids `PLB-O1` to `PLB-O16` are local to this spec. They are unrelated to the odds rulings O1 to O15 and O3-n that the code cites (for example `simulate.py:442`).

| # | Decision | Recommended default | Alternative and consequence |
|---|---|---|---|
| PLB-O1 | Does `LB` bound the position, or only move the halt line? | **Bound the position (4.1).** It is the only form in which "capped at `LB`" is true with code that exists. | Positions up to `W0` with a halt at `C`: needs a real exit mechanism (none exists), accepts that a gap passes the floor and that the first breach is permanent. |
| PLB-O2 | Change the first-bar rule in the same signed change? | **Include (6.1).** With it, nothing checks that the account holds `W0`; the owner rule and S10 stand in. | One window only; each later window costs a new code signature, study and review. It keeps the equality and has no such gap. |
| PLB-O3 | Apply the cash rule in every regime? | **Budget regime only.** Above `A` a losing run can then end in a permanent halt (2.4). | Every regime: cash after an admitted buy is at or above `max(F_effective, L)` at admission, so the first-fee halt above `A` becomes a refusal; a later rise of `H` can still lift the floor above cash. But above `A`, `G >= W0 > C`, so the driver, capped with `C`, proposes orders this rule refuses, and the refusal stops the runner (`runner.py:459-463`). It needs a driver and evaluator cap on `G`, which neither can compute, or a runner pre-check that returns `blocked`. Effect on the suite unmeasured. |
| PLB-O4 | Activation with an open position | **Accept, with the guidance of 2.4.** | Constrain parameters in code, or add a rule in the post-activation spec. |
| PLB-O5 | Raise `L` to `W0` when `H` first reaches `A`? | **Yes, as an owner act outside this change.** It records activation in the owner log and stops new sessions until the post-activation spec. It becomes a required step if the relaxation command is ever built (2.3, PLB-O14). | Leave `L = C`: entries continue above `A` under a card that overstates, and a losing run there ends in a permanent halt (2.4). |
| PLB-O6 | Deposits and withdrawals | **Unsupported; no flow while a budget is in force, and no surplus above `W0` at the first anchor (6.1, 6.2).** | A code rule ("raise `L` by the deposit before a new anchor") in the stage-transition spec. |
| PLB-O7 | Record cumulative loosening, or require an acknowledgement when a loosening follows a loss? | **No new mechanism.** D12 and the signature are the control. | A new owner-log rule: a `core/compliance` change with its own review. |
| PLB-O8 | Rounding margin on the cash rule | **None.** Exact arithmetic; a breach needs a total loss and a fee error together. | One extra fee as margin: slightly smaller positions. |
| PLB-O9 | Smallest budget the code accepts | **One minimum order with its fee; below that the preflight blocks.** Choose several in practice: a budget of about one minimum order ends in dust (4.5). | Require several minimum orders in code. |
| PLB-O10 | The halt re-send, 6.3(b) | **Include, as its own commit**, so it can be reviewed alone. | Its own pull request and code signature later; until then a failed owner-log write stays lost. |
| PLB-O11 | The research mirror | **Update it.** | Retire it; the 2026-10-30 spec section 8 points to it. |
| PLB-O12 | Tie the daily budgets to `LB` in code? | **No.** A larger daily budget is inert, not unsafe. | A validation rule; one more way for a profile to be incomplete. |
| PLB-O13 | Add a sell-side margin: an entry is a `hold` unless its notional is at least `mu * m`, with the same text in the driver and the evaluator? | **No.** The cap stays one term and the smallest budget stays one minimum order (3.2, 4.2). The dust end state of 4.5 is accepted and disclosed. | Include it with a fixed `mu` (for example 2): fewer dust endings. It also raises the preflight to `LB >= mu * m * (1 + f)`, needs a named pin at preparation for the band where the card still gives a plan, and changes PLB-O9. |
| PLB-O14 | Build the relaxation command of 8.1 in the one signed change, whatever step 0 finds? | **No.** Built only if step 0 finds a journaled floor above `C`. | Build it now: an anchor floor typed above `C` that gets observed (10.3) is then recoverable without a new code signature and reviews. But it is the path by which a raised `A` undoes activation (2.3), so PLB-O5 becomes a required step. |
| PLB-O15 | Refuse a buy in `_authorize` before the risk snapshot when the signed floor inside the session's context differs from the one outside it? | **No.** It needs a second owner-context load per buy and suppresses a halt that D12 and the unchanged breach test produce today. | Add it: a back-stamped arming (10.3) is then only refused, never a halt. |
| PLB-O16 | The preparation pins for a universe profile, if the universe design is adopted (12.5) | **For a universe profile, pins 2 and 3 of 4.3 are replaced by one pin: `stake <= min(W0, settled cash of the trading account)`. Fixed profiles keep 4.3 as written.** While `H < A` and the floors agree (2.5), the card's headroom `stake - L` is then at most `R`, whatever is held; at `H >= A` the card can still overstate it (2.4). In the usual case of 4.2 this does not let a session be prepared while the traded coin is held: the cap binds, so after a buy filled in full settled cash is at or just above `C`, every stake the pin allows gives the card a first stake of zero (`STUCK_AT_START`, 4.5) and the preparation is refused. Buys then wait until that coin is sold. Against pin 3, the gain is that a remainder or an unlisted coin no longer blocks a preparation. It needs settled cash passed into `prepare_launch_session`: `Positions` carries equity and units only (`core/compliance/model.py:104-109`), while the coordinator's observation has it (`controller.py:36`; `coordinator.py:726-730`). So `execution_launch/coordinator.py` joins the closure files of 8.1 in that case. | Keep pin 3 for universe profiles: preparing again with a coin held is refused, so buys stop at the first session end until the account holds nothing at all, which a remainder or an unlisted coin can prevent for good. Or ignore remainders under the minimum order and keep `stake <= E`: the card then counts marked remainders as headroom, and I10 fails. |

The sizes of `LB`, `A` and `T` are private owner values. This spec sets only their ranges (3.2).

### 12.3 Risks, and what this design does not protect against

- **Small positions, small chances.** Section 7. Mitigation: none in software; it is the price of a real cap.
- **Gains below `A`, and activation.** A realized gain enlarges the headroom and can be lost again. An open position, or one wrong high mark, at `A` can halt the account (2.4). The card overstates above `A`. With PLB-O5, new sessions stop at `A`; without it, a losing run above `A` ends in a permanent halt.
- **The halt is permanent and does not sell.** Mitigation: 4.1 makes a breach below `A` an accounting anomaly rather than a market event.
- **Dust and a stopped runner.** A spent budget usually ends holding an unsellable remainder with the runner stopped (4.5). Clearing it is a manual act outside this system.
- **The stake cap (pre-existing, accepted).** A driver order above the prepared stake is refused and stops the runner, and the paper study does not show it (4.2, 4.3).
- **The assumptions of 4.6.** A fee above the rules, a fixed charge, a fill above the limit, a wrong mark or a withdrawal can put equity below the floor. The halt remains as backstop.
- **Venue and custody.** The floor limits trading loss. It says nothing about the venue failing, freezing withdrawals or delisting. The protected cash sits on the venue.
- **Fee drag and idle days.** Many flat trades wear the budget down, and the daily rules can idle it (section 5).
- **A wrong number typed three times.** `LB` in the profile, `L` in the owner log and the anchor's floor are separate entries. If they differ, entries are blocked, and an anchor floor above `C` that gets observed is journaled for good (10.3). If all carry the same wrong number, the system trades to it.
- **History outside one home, and signing out of order.** A second home, a moved journal with an understated anchor peak, a deposit, or a surplus at the first anchor (6.1 to 6.4); old code with a lowered floor (9.2); an arming, or a later owner-log line, stamped back (10.3). No owner-log line may be stamped earlier than the loosening's date once it is signed; keep the PC clock right.

### 12.4 The plain cost of adoption

| Item | Cost |
|---|---|
| Signed-closure files changed | Ten (8.1): `risk.py`, `controller.py`, `session.py`, `profile.py`, `strategy.py`, `study.py`, `workflow.py`, `review_request.py`, `runner.py`, `driver.py`. Two more closure files (`coordinator.py`, `tools/owner/launch.py`) only in the case of 10.2. This row and the "Not changed" row of 8.1 are for the fixed driver at the base commit: if the universe design is adopted, the default of PLB-O16 also edits `coordinator.py`, whether or not the case of 10.2 applies (12.5). If that command is not built and a journal floor above `C` appears later (10.3), it costs a further closure change, `code_approved` and reviews (PLB-O14). |
| Outside the closure | One new read-only script, the research mirror and its test, the synthetic example builder, and the docs of 8.3. |
| Owner signatures caused by this change | Two: `code_approved`, and the `limit_set` that lowers the floor. |
| Signatures that exist for any first trade and must be made after it | `review-approve` and `session_armed`. |
| Minimum waiting | One Seoul date change between the `limit_set` and the first preparation. The case of 10.2 needs a second one: the pending snapshot is written by the first observation under the new code, which the order rule (9.2) places on the Seoul date after the `limit_set` at the earliest, and the relaxation needs a snapshot from a date strictly before its own (`controller.py:460-466`). Plus one full new prospective capture, then evaluation and review: 48 hours from the capture start in the current draft workflow (`docs/launch-workflow.md:153-156`; `tools/research/prepare_shortened_study.py:24-25`, `60-63`). That is a development choice, not a code minimum; the code requires only `bar_seconds * minimum_observations`, at least 60 observations and 20 round trips (`strategy.py:151-154`, `169-171`). The date change can pass during the capture, so the two are not added. Whether a study can qualify at the owner's budget is not established (7.3), and the study should start only after the last profile-schema change (7.4). |
| What becomes void | Every profile digest, policy digest, protocol digest, driver identity and code hash changes (`profile.py:263-264`, `306-310`; `execution_control/capability.py:40-45`; `driver.py:35-38`; `study.py:59-61`). Every study, published commitment, review document, prepared session and guard checkpoint made before must be made again. |

### 12.5 Interaction with the proposed Upbit KRW universe design

This spec was designed and reviewed against the single-coin fixed driver at the base commit. Pull request 19, open at the time of writing, proposes a universe mode in which the same driver trades one coin at a time out of the eligible Upbit KRW coins. It is planned as ten pull requests (0, 1, 2, 3, 4a to 4e, 5). Its design is `docs/superpowers/specs/2026-11-11-upbit-krw-universe-design.md` with the plans beside it, read here at commit `eab3047`. None of that code is on main, so this section describes plans, not code, and cites no line numbers for them. The universe design leaves the floor out of its scope (its sections 1, 3 and 21) and none of its plans adds a floor, a budget or a cash-floor term. If it is not adopted, this section has no effect. If it is, the implementation plan of whichever change lands second must settle every row below.

**Order.**

- Both changes edit the same files: `controller.py` (universe PRs 3 and 4a), `session.py` and `risk.py` (4a), `profile.py` (3, 4b, 4c), `strategy.py` and `study.py` (4b, 5), `runner.py` (4b, 4e), `driver.py` (0, 4b, 4d), `execution_launch/workflow.py` and `execution_launch/review_request.py` (4b), `tools/research/prepare_launch_example.py` (4b, inside the `ForwardProtocol` call that 8.2 edits), and `tests/renewal_boundaries.py` (2, 4a, 4b, 4c, 5). PR 4e also edits `coordinator.py` and `tools/owner/launch.py`, which this spec edits only in two cases: `coordinator.py` with the default of PLB-O16, where PR 4e changes the same `prepare_launch_session` call, and both files in the case of 10.2, where PR 4e changes the same `command` lines of `tools/owner/launch.py`.
- The universe plans are exact-text edits written against `fd85850`, with pre-computed pin hashes and digest literals. The first step of PR 4a stops unless `controller.py` differs from `fd85850` by exactly the five lines of PR 3. This spec has no implementation plan yet. **Recommended: the closure code of this spec lands after universe PR 5, and its plan is written against that main.** The read-only state check (8.2) is outside the closure and can land at any time; it ships first, in its own pull request (8.2). The docs of 8.3 are outside the closure too, but they belong to the implementation pull request and must not land before the closure code: until then every superseded sentence still describes what the software does, and `docs/launch-profile.example.json` with the new key is refused by today's parser (`profile.py:118-120`, `224`), which fails `tests/launch_profile.py:225-230`. Landing this change first is possible, but the universe plan steps that quote the same lines, pins or digests must be amended first: at least PR 4a's base check and its `risk.py` pin, PR 4b's `profile.py` pin and digest literals, and PR 5's `_simulate` block.
- Every universe pull request changes the signed closure; several also change the fixed-driver identity and the capture files. So `code-approve`, the `limit_set` that lowers the floor, the study freeze and the review happen once, on one head that holds this change and every universe pull request through PR 5 (7.4). The order rule of 9.2 does not change: never the lowering `limit_set` while the signed code lacks this change. The universe design also needs the venues table signed again, with its new `universe_rule` field, after `code-approve`.

**Where the premises of this spec change.**

| This spec | Under the universe design | What is needed |
|---|---|---|
| Pins 2 and 3 at preparation: `stake <= E` and a flat account (4.3) | A universe session ends at the next snapshot end or Seoul midnight, while a window can run past both: the universe coordinator refuses only a window longer than 72 hours, and the owner tools still allow at most one day (`launch.py:107`, which no universe plan changes). Preparing again with a coin held is therefore the normal case. Remainders under the minimum order and unlisted coins (marked at zero) stay in the account and nothing sells them. Pin 3 would refuse those preparations. `stake <= E` without pin 3 would let the card count a held coin as headroom. | PLB-O16. Its default removes the block by remainders and unlisted coins; with the traded coin held after a capped buy the card still refuses, and buys wait until that coin is sold. Under that default, the last clause of item 5 of 0.1 (a session is prepared only while the account holds no position) and the flat clause of I10 hold for fixed profiles only; for a universe profile what holds instead, while `H < A`, is that the card's headroom `stake - L` is at most `R`. |
| The paper cap is one term in `_simulate` (4.2) | PR 5 moves the buy-size lines into a shared helper `_order(target, nav, units, mark, bid, ask, cash, fee, lot)`. Every universe path, the KRW-BTC benchmark included, sizes through it with its full cash and never calls `_simulate`. The universe study capture replays those paths. | The cap goes inside `_order`, with `C` from `protocol.cash_floor_quote` passed by every caller, never a default. `UNIVERSE_EVALUATOR_REVISION` (added by PR 4b) is bumped as well. Otherwise a universe study sizes uncapped orders while the live driver is capped, and I7 fails. The live cap needs nothing more: universe orders go through `_sized_signal`, which the universe plans leave unchanged. |
| The agreement check runs before the card, in `prepare_session` (2.5a) | PR 4a adds `execution_control/universe_odds.py` `run_batch`, which simulates one card per coin outside `prepare_session` and keeps a pass flag per coin, not the refusal code. With `L >= stake`, or with `stake - L` too small for one minimum order (4.5), the owner would see only that no coin passed. With any other `L != C` below `A` the batch sizes the cards on the wrong floor and coins can pass; the batch shows nothing of the disagreement. | The agreement check and the `floor_safe` pin also run in the batch, and the per-coin refusal code is kept. No buy depends on this: preparation still refuses. Two side effects of the batch's bindings: a plan's hash includes its stake, so a stake changed to satisfy the stake pin (pin 2 of 4.3, or the pin that replaces it under PLB-O16) needs a new batch; and the batch binds the owner-log head, so a `limit_set` signed after it makes it stale. |
| End state 2: a remainder stops the runner and blocks the next window (4.5) | True for the traded coin only. Remainders of earlier coins are ignored by the driver. They count in `E`, not in `R`, and later windows still open. Two warnings of PR 4e (`UNIVERSE_OTHER_COIN_WARNING`, `UNIVERSE_REMAINDER_UNSELLABLE`) tell the owner to top a remainder up and sell it in the Upbit app. | That manual buy spends settled cash outside the controller, so no rule of this spec sees it. It is the hazard named in 4.5. While a budget is in force the warning text must say so, or PLB-O13 is adopted. `test_terminal_dust_stops_the_runner_and_blocks_the_next_window` needs a universe variant. |
| Study pace (7.3) | A universe path that cannot sell a remainder under the minimum cannot move to the next coin, and a candidate that ends that way has no result. A failed benchmark ends every candidate. Under the cap an entry is about the size of the remaining budget, so near one minimum order a single losing switch can end a study. | Counted in the plan's study estimate. The advice of PLB-O9 (a budget of several minimum orders) matters more here. |
| One wrong high mark at `A` ends the budget (2.4) | A thin coin whose last trade is at most 30 seconds old is marked at that trade, which can sit above the best bid. | A more likely source of a false `H >= A`. A named risk; no code here. Low marks are harmless below `A`: by 4.1, `E >= C` even when a held coin is marked at zero. |
| The first-bar rule (6.1) and the first row of 4.6 | After PR 4d the rule applies to the anchor of the traded coin, and holdings of other coins no longer make the driver refuse. | The evidence in the first row of 4.6 (`driver.py:312-316`) holds for fixed drivers only. The cash rule is unaffected: it reads settled cash. |
| `principal_loss_budget` and `cash_floor_quote` are required, with no default (3.2, 8.1, 8.2) | The universe design gives every new field a `None` default that is left out of the encoding, so that fixed digests stay byte for byte, and PR 4b pins those digests as literals. | No conflict in behaviour. Every digest changes with this spec in any case (12.4), so whichever change lands second recomputes the literals. `cash_floor_quote` stays required. |

The universe design text that calls the floor decision open ("its own owner decision is still open"; "While the floor equals the start equity, no coin can start") is superseded by this spec once both are approved. That edit belongs with the universe documents.

## Appendix A. Review findings and where each is answered

| Finding (from the two design reviews that preceded this spec) | Answered in |
|---|---|
| Deposits, withdrawals, the second window, the one-window limit | 6.1 (PLB-O2), 6.2 (PLB-O6) |
| Activation with an open position; card against runtime above `A` | 2.4 (PLB-O4, PLB-O5), 4.3 |
| History that survives a moved file; halt independent of the control journal; "lifetime" as strong as the signed floor | 6.3 (PLB-O10), 6.4 (PLB-O7) |
| The signing-order hazard on today's main; the code must refuse | Status block, 9.2, 10.3 |
| Unknown private state; a code-backed step 0 with a go / no-go table | 9.1 |
| Cash-rule assumptions as testable conditions, rounding margin, named refusal; flat-only accounting | 4.1, 4.6 (PLB-O3, PLB-O8) |
| Honest scope, odds and pace; only M8 is removed; sequencing; cost of adoption | 7.1 to 7.4, 12.4 |
| `SIGNED_PRINCIPAL_FLOOR_TOO_LOW`; float storage against exact comparison | 3.3, 3.2 |
| Budget granularity; the out-of-budget end states | 4.5 (PLB-O9, PLB-O13) |
| Gains below `A` are not protected; the paper evaluator has no floor regime, halt or daily rules | 0.1 (a), 2.2, 4.2 |
| One symbol and one field name; the supersession record | 0.2, 1.3 |
| Nothing was run; measured baseline first | 11.3 |
| Not from those two reviews: overlap with the proposed universe design (pull request 19) | 7.4, 12.5 (PLB-O16) |

This is a software design, not legal, tax or investment advice.
