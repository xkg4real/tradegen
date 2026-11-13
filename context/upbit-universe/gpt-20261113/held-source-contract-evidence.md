# Held-source production authority: candidate contract evidence

Read-only analysis, 2026-11-13, source head `c80c56cdab946a80ae40be31432b41c881dcd5a2`.
Tracked task: `launch-held-positions-1/production-authority`; this is evidence for review, not an approved design,
an implementation, or an operational readiness claim. No API, credential, owner home, signer or order was used.

**Conclusion: the repository's recorded Upbit guarantees do not currently justify an implementable production
held-source completeness contract.** They support parsing/authenticated transport and local reconciliation, but
not proof that every relevant valuation/account event was received in authoritative common order. This is a
limit of the available evidence, not proof that no suitable venue/provider contract can exist. A callback that
returns a correctly bound `VerifiedCoverage` would not close that gap.

Current handoff `CURRENT.md:8` retains this task. The approved controlled-launch design explicitly leaves its
source undesigned (`docs/superpowers/specs/2026-11-12-controlled-launch-and-planner-design.md:23`, `:110`). The
existing exact-path obligations are in `docs/continuous-price-candidates.md:27` and
`docs/continuous-guard-commit-contract.md:91`. Older full-peak examples in those documents must not override
the later approved PLB below-activation floor or protective-hold decisions. PLB changes the floor and admission
cap; it does not establish missing source coverage, event order, or boundary facts.

## Evidence table

“Authenticates now” distinguishes the genuine E1 source's checked HTTPS/JWT request path from validation of
caller-constructible records. Hashes bind stored bytes; they are not venue attestations or completeness proofs.
All source locations below are relative to `/workspace/tradegen-universe-1113`.

| Required interval fact | What authenticates or validates it now | What remains unprovable from recorded guarantees | Option preserving accepted loss semantics | Precise minimum evidence or decision |
| --- | --- | --- | --- | --- |
| **Fills:** all account fills, including partial fills, fee-bearing fills and earlier-created orders, with exact quantities and times | E1 private order reads; listed/detail equality, trade UUID uniqueness, funds/volume reconciliation and FIFO checks (`execution_accounts/upbit_collector.py:267`). REST detail provides per-order `trades[]`; recorded `myOrder` provides `trade_uuid` and `trade_timestamp` (`docs/superpowers/plans/wip-2026-10-24/venues/upbit.md:312`). | REST order-list inclusion/retention and completion of the event set; a creation-time query cutoff is not a fill-finality frontier. Unknown submission outcomes, resting orders and late fills remain possible. Empty/closed/negative queries do not prove no events. | Reconstruct from a demonstrably complete retained order/fill ledger with a proven frontier; preserve refusal on an unknown outcome or gap. A controlled submission journal can corroborate known orders, but cannot replace fill coverage. | Documented inclusion/retention/replay and finality guarantee covering the exact scope and `[start,end)`, all previously live orders, plus identity-bound raw records and a reviewed receipt verifier. No local “all orders accounted for” boolean. |
| **Fees:** exact fee and currency at each fill, assigned to the correct risk day | `_fees` (`execution_accounts/upbit_collector.py:247`) accepts an exact single-fill order fee or zero aggregate fee; otherwise requires complete per-fill evidence summing to `paid_fee`. Recorded private `myOrder.trade_fee` is a promising field, not an implemented authority. | Per-fill fee attribution from nonzero aggregate `paid_fee`; complete delivery, corrections, currency/rounding and eventual-finality semantics of `trade_fee` are not established in the recorded note. | Authenticate the per-fill fee source and reconcile it against order totals; continue refusing multi-fill ambiguity. | Original venue field semantics for fee currency, finality/corrections and exact fill-ID linkage, with the same delivery/coverage proof as fills. Fee-rate estimates or proportional allocation do not suffice. |
| **Flows/account changes:** no omitted deposits, withdrawals, rewards, adjustments, transfers or liabilities during the interval | Reviewed `CoverageEvidence` claims and restricted KRW deposit/withdrawal normalization; repeated pages detect some changes (`execution_accounts/collector.py:113`; `execution_accounts/upbit_collector.py:325`, `:430`). Continuous preview refuses interval flows (`execution_launch/account_interval.py:299`). | Main-pocket deposit/withdrawal history does not enumerate every pocket movement. Matching endpoint balances cannot exclude an out-and-back change. Owner inactivity alone cannot exclude exchange matching or credits. | Retain the existing no-flow/no-liability scope, backed by an enforceable, independently evidenced exclusion; if that cannot be established, refuse. Supporting flows would require a separately reviewed accounting extension. | Evidence tying the account/key to the main pocket and proving the excluded event classes cannot occur in the interval, or an authoritative complete account-change ledger plus an approved extension. A signed assertion alone cannot manufacture exchange facts. |
| **Marks:** opening and every subsequent valuation mark for every held asset, including valuation-mode changes | Exact received ticker/book parsing and freshness; PR4c endpoint policy uses fresh last trade, stale-trade fallback best bid, and zero only for a valid listing response proving the held pair absent (`execution_accounts/upbit_collector.py:407`). Quote receipts prove their own contents, not all intervening prices (`docs/upbit-quote-contract.md:48`). | No recorded lossless stream of all policy-relevant marks or authoritative listing/fallback transition times. The current `PriceMark` requires positive prices (`execution_accounts/continuous.py:146`), so endpoint unlisted-zero behavior is not yet a supported continuous event. | Preserve the accepted endpoint valuation policy and define its authenticated continuous counterpart, including transitions and zero-valued retained holdings. Refuse unsupported/missing mark classes. | A reviewed definition of exactly which changes are valuation events, with source guarantees for their complete delivery and ordering; explicit reconciliation of delisting-zero and stale-trade fallback with the existing continuous model. This is a missing design decision, not permission to infer zeros or time-shift a later quote. |
| **Extrema/risk path:** every equity point relevant to floor, peak, daily loss, activation, 22:00 and midnight | `value_path` derives exact cash, units, FIFO profit and per-event extrema from its supplied path (`execution_accounts/continuous.py:302`). Guard reducer processes every point and the midnight left limit before reset (`docs/continuous-guard-commit-contract.md:60`). | Completeness of the supplied path. Matching opening/closing NAV, even with sampled min/max, can conceal a peak then breach. Independent per-coin OHLC omits account-level chronology and fill/fee timing. | Reuse the existing reducer only after source coverage is established; keep effective floors, activation, daily stops and prior permanent halts. Any conservative-bound certificate would need its own reviewed proof and integration, not promotion to the current exact-path contract. | Complete mark/fill evidence, effective signed policy/control predecessor and exact boundary values. Mathematical worst-case bounds alone cannot supply the missing actual high-watermark/history facts required by this reducer. |
| **Ordering:** one authoritative order across marks, fills, assets and same-time events | Recorder enforces supplied consecutive counters and nondecreasing times; valuation preserves supplied equal-time order (`execution_accounts/continuous.py:153`, `:177`, `:302`). | Venue-global order from local arrival order, millisecond timestamps, trade UUIDs or separate public/private stream sequences. An event received later may belong earlier. | A source-issued common order or a separately justified deterministic merge whose equivalence to all risk-relevant actual orders is proven. Refuse unresolved ties or late events. | Recorded cross-stream sequencing/causality contract and tie semantics, plus replay of the exact ordered set. Local counters merely record the selected order. |
| **Completeness/closure:** no missing event from opening through a genuine closing frontier | `validate_path` checks duration/sequence bounds; `verify_coverage` binds path, capture, scope, epoch and watermark to a trusted callback (`execution_accounts/continuous.py:177`, `:281`). Collector separately requires an external no-matching capture fence and retention evidence (`execution_accounts/upbit_collector.py:223`). | Venue final watermark, loss detection, late-event bounds and repair/replay. Silence on private `myOrder` without activity is documented; delayed initial `myAsset` delivery is documented. Neither silence nor a heartbeat closes an interval. Repeated reads cannot exclude ABA. | A documented loss-detecting, replayable source with a provable final frontier and consistent account snapshot; continue failing closed on gaps. A genuine no-matching fence could support a quiescent capture, but cannot be presumed while resting orders can fill. | Original source guarantees and a reviewed capture/stream barrier protocol: snapshot correspondence, retention, delivery loss detection, closure, late events, reconnect and restart. Current 30-second bounds must be satisfiable without enlarging or backdating evidence by assumption. |
| **Provenance/authority:** evidence belongs to the reviewed account/source and cannot be relabeled or replayed into another context | E1 authenticates private requests with JWT over checked HTTPS; receipts retain raw bytes/path/params/times and digest (`docs/account-collector-contract.md:54`; `execution_accounts/collector.py:78`). Scope identity remains externally reviewed. Public `VerifiedCoverage` fields are shape/binding checks, not an issuer capability. | Owner identity from balance payloads; provenance from an arbitrary receipt/hash; independent authority from a caller-created dataclass; durable replay authority from the candidate archive alone. | A reviewed issuer bound to the authenticated source and account scope; either reverify original evidence or issue a process-valid unforgeable capability. Preserve original package and independent heads for recovery. | Actual credential-to-scope evidence, trusted issuer implementation and dependency identity, raw-evidence retention/reverification rules, and baseline/guard/controller/owner predecessor binding. A signature over an unsupported completeness claim still does not prove completeness. |

## Smallest honest candidate and immediate next work

1. **Conditional implementation route:** one reviewed provider contract must cover opening account state, every
   accepted valuation/fill/fee event, excluded flow classes, common ordering, and a final source frontier. Its
   verifiable proof must bind the exact account capture and path. The existing recorder, FIFO reducer and durable
   commit library can then be reused. No such provider or guarantee has been established in the checked sources.
2. **Evidence request, not a fictional user approval:** obtain the original venue/provider guarantees for the
   missing rows, especially common ordering and closed-interval delivery. The owner can select a proposed source
   and supply private identity material later; the owner cannot turn incomplete observations into complete facts
   merely by approving them. If no qualifying source exists, the honest outcome remains blocked held trading.
3. **Work that can proceed before private inputs:** retain this coverage gap table; enumerate malformed/missing,
   late/corrected, cross-stream-tie, fill-fee, ABA, delisting and exact-boundary refusal cases for the source design;
   review authenticated package retention and durable integration against existing contracts. A production
   authority must not be implemented with affirmative stubs while those source premises are unresolved.
4. **Existing fallback:** the flat-only source remains available within its reviewed evidence conditions. It does
   not permit entering a position and claiming that the held-source blocker is solved. Sampled observed-NAV
   policy, threshold checks only at polls, or automatic reset after gaps would change accepted semantics and
   are outside this candidate. PLB admission safety below activation also does not prove the whole historical
   path or authorize discarding activation/daily/boundary requirements.

## Recorded venue evidence and verification limits

- `docs/account-collector-contract.md:60`: external identity, opening inventory/open orders, retained history,
  excluded movements and genuine no-matching capture fence; repeated reads explicitly do not exclude ABA.
- `docs/account-collector-contract.md:108`: links the official closed/open-order, order-detail, flow and pocket
  contracts; closed-query boundaries/retention and per-trade fee attribution are not assumed.
- `docs/superpowers/plans/wip-2026-10-24/venues/upbit.md:308`: official private WebSocket URLs and recorded fields;
  `myOrder` sends nothing without activity, `myAsset` first delivery may lag minutes. At `:534`, those two facts
  are explicitly recorded as verified against the official references. No common-order/replay/finality promise
  is recorded there. The note's recommendation to poll REST is operational advice, not a completeness theorem.
- `docs/continuous-price-candidates.md:7`: snapshots, candles, timestamps, trade IDs and heartbeats do not prove
  full valuation coverage. `docs/continuous-guard-commit-contract.md:95` requires actual source authentication
  and issuer-bound verification before the implemented local durable transaction may publish live state.
- Exact remaining gates: `execution_launch/account_interval.py:118` refuses held positions/interval fills;
  `:417` unconditionally refuses continuous candidates as a live source. This analysis changes neither gate.

Source reading only; no runtime tests were needed or run. No source/spec/test file changed. Official URLs are
recorded references, not fresh online verification. This is software engineering analysis, not legal, tax or
investment advice; the author is not a licensed adviser.

Fresh-documentation follow-up: [official Upbit documentation check, 2026-11-13](held-source-official-docs.md).
It distinguishes documented limitations from unspecified guarantees and records the historical ordering
wording conflict and the positive reconnect recommendation without promoting either into coverage proof.
