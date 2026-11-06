# Remaining market readiness and the 48-hour boundary

Audit date: 2026-11-06, Asia/Seoul. Source baseline:
`21259f8d8ab76ea35c46a61df582fe5d792e916f` (PR #12 merged).
This records what the merged code establishes and what evidence is still needed.
Other changes in the current development branch must be assessed by their own
tests and execution record; the baseline column below is not a claim that those
changes have already passed. Private capital, account identifiers and local
owner paths are deliberately absent.

This audit made no market/account API request and accessed no credentials,
actual owner log or private signing material. Source inspection and fake HTTP
fixtures cannot certify a live connection, a qualifying strategy or an order.

## Capability boundary

| Area | Established in the merged baseline | What is required before live automatic use |
| --- | --- | --- |
| Upbit public quotes | `execution_accounts/quotes.py` provides the reviewed KRW orderbook reader; `execution_launch/quote_diagnostics.py` reports receipt timing and refusals. | Owner-PC timing observations and a reviewed capture source. Apparent quote age combines network delay and clock difference; it is not a clock-offset measurement. |
| Upbit complete account evidence | `execution_accounts/collector.py`, the Upbit collector modules and `execution_launch/account_interval.py` supply the supported account path. The shipped interval source establishes flat intervals only. | Complete held-position valuation/fill coverage, gap detection, retained daily/lifetime baselines and authentic boundary evidence. A price chart or endpoint pair does not establish an interval's extrema. |
| Upbit research and selection | `execution_launch/study.py` and `strategy.py` support one KRW spot asset and a frozen candidate family. PR #12 adds a new 48-hour draft preparer. | Actual preregistration/publication, new complete future observations, all numerical filters, authenticated source/implementation review and applicable owner approvals. The existing historical study has zero passing candidates. |
| Controlled launcher | `execution_launch/coordinator.py` wires the rehearsal mode; the baseline rejects controlled mode. E2/E3 order building blocks exist. | Reviewed controlled integration, current terms and account evidence, exact prepared-session binding, stop/cancel/exit/restart handling and owner-operated deployment validation. Removing a mode guard alone does not complete the launcher. |
| KIS Live market display | The uploaded-workbook catalog describes 32 market-data channels; `data/kis_live.py` and `ui/kis_live_page.py` implement viewing and bounded sample indicators. | Actual channel entitlement and transport checks. Some channels require unresolved master scale/time semantics. Delayed or partial-market data must retain that qualification. This screen supplies no account fills, order/cancel commands or strategy permission. |
| KIS E1 account inquiry | `execution/kis_inquiry.py` exposes pinned domestic/US inquiry calls behind sealed signed-code context. It reads the first page of each list. | A complete authenticated account collector with terminal pagination, retention, settlement, cash locks, exact fills/fees/taxes/flows and acquisition history. A bounded E1 summary cannot be upgraded to E2 account evidence. |
| KIS E3 order codecs | `execution_orders/kis.py` implements KRX and supported US cash limit request/response codecs; `AuthenticatedTransport` requires explicit credentials and capability. | Current product/account terms, complete collector and research model, reviewed live wiring and reconciliation. Paginated order-status responses remain unknown; US terminal cancellation is not established by a cancellation acknowledgment. |
| OKX public data | `data/crypto/okx_public.py` supplies keyless spot daily candles and limited funding/mark/index data for existing analysis/UI paths. | A live execution-grade quote and evidence contract, actual lawful/product access and complete currency/account models. Public derivatives data display does not authorize derivatives trading. |
| OKX E1 account inquiry | `execution/okx_inquiry.py` performs bounded read-only inquiry with spot/no-borrow/no-auto-loan/IP checks. Its caller supplies the current USDT/KRW conversion. | Independently sourced marks for every held currency/asset, exact complete account history and private account configuration. No asset may disappear from valuation because its price is missing. The USDC correction below preserves this refusal. |
| OKX E3 order codecs | `execution_orders/okx.py` implements cash SPOT limit create/cancel/status codecs and validates returned identity and state. | Complete terms, source and account evidence, separate authorized order credentials, FX/cost research and a controlled launch path. E1's read-only key check is not an order-permission check. |
| Other KIS products or other venues | Market display, rule rows or provider metadata may exist. | A product-specific implementation and acceptance plan. Visibility in the catalog or compliance table is not evidence of a completed account/research/order path. |

The canonical contracts are [Windows integration](windows-first-trade-integration.md),
[account evidence](account-evidence-contract.md), [KIS channel semantics](kis-live-api-contract.md),
[forward validation](forward-strategy-validation.md) and
[market selection](market-selection-protocol.md). No cross-market Sharpe or
"most validated assets" conclusion follows from the current single-market scope.

## Missing product terms are concrete blockers

The signed venue table and a fresh runtime `InstrumentRules` object are separate
inputs. Neither substitutes for the other.

| Input | Baseline evidence | Completion condition |
| --- | --- | --- |
| KIS signed venue facts | `core/odds/venues.yaml` includes a limited domestic lot map, a KRW minimum and a KRX stock tick ladder. It does not provide signed fixed charges; the US lot/minimum coverage is incomplete. | Source and review the exact applicable lots, tick bands, minima, fixed charges and cost model for each selected product. Do not insert zero merely because a field is absent. |
| OKX signed venue facts | The table lists limited spot pairs/settlement currencies but lacks signed lot/minimum/fixed-charge data; its overall source is explicitly unverified. | Establish exact pair, quote currency, account-specific fee schedule, lot/tick/minimum rules and source version before approval. Existing `core/odds/costs.py:terms` refuses missing facts. |
| Fresh runtime terms | `InstrumentRules` binds venue, market, symbol, lot, tick, minimum quantity/notional, fee, source digest and observation time. Preparation/dispatch require terms no older than five minutes. | A reviewed refresh process must carry genuine observation/provenance through the full runtime profile, session and order digests. Replacing only `asof` supplies no evidence. |
| Foreign settlement and stablecoins | E1 accepts a supplied USDT/KRW mark; the odds model also accepts a single conversion parameter for foreign quote conventions. | Keep current marks and execution-time fill FX distinct. Independent currencies need independent evidence; assumed USD/USDT/USDC parity is not authenticated conversion. Add currency/tax/calendar/cost models before expanding prospective evaluation. |
| Legal/account eligibility | PR #12 corrected explanations/sources while preserving entry conditions and the November review deadlines. | Resolve remaining source/entity/product/account questions and obtain the applicable reviewed approvals. The absence of a product in one restriction list is not affirmative access permission. |

## USDC valuation correction in this batch

The baseline OKX inquiry assigned `prices_krw["USDC"] = usdt_krw` without an
independent USDC quote. This could value a held USDC balance at another token's
price. The correction removes only that unsupported mark:

- `snapshot(now, usdt_krw)` keeps its public signature and its existing USDT/BTC
  pricing route. No endpoint, credential or key permission is added.
- USDC holdings, including funding/trading balances and locked units, remain in
  the snapshot. A positive holding without a mark makes
  `execution.positions.venue_value_krw` and the combined `live_positions` refuse
  valuation; the unpriced asset is never omitted from the account total.
- Zero balances remain absent holdings. Accounts with only supported priced
  holdings retain their existing valuation path.
- E1 inquiry may still report a successful read and record counts. The account
  connector continues to return `account_evidence_ready=false` and
  `execution_ready=false`; read success is not valuation or execution readiness.
- A future USDC integration needs an explicit independently sourced mark with
  currency identity, observation time, original source and freshness checks.
  This patch does not add an unchecked numeric override or assert such a source.

Tests preserve the existing case identities, replace the two incorrect peg
expectations, exercise USDC in trading/funding/both balances through the actual
fake inquiry plus valuation path, and check zero balances and connector flags.
The pure valuation fixtures use a distinct explicitly synthetic USDC mark to
exercise independent-currency arithmetic; they do not claim a live source.

Focused verification: all E1 execution cases plus `accounts_readiness` completed
with **250 PASS, 0 FAIL, 0 NOT_RUN**, using 19 KEYLESS placeholders, temporary
state and fake HTTP. The two new case identities are
`execution_okx/test_usdc_holdings_are_retained_but_refuse_valuation_without_an_independent_mark`
and `execution_okx/test_zero_usdc_balances_do_not_create_an_unpriced_exposure`.
All existing case identities remain. These are software tests, not real account
or venue observations; the final combined-branch regression is recorded separately.

## The unchanged loss floor and entry costs

Let `P` be protected principal, `H` the lifetime high-watermark, `A` the privately
configured drawdown-activation threshold, and `E` current marked equity. The
existing risk engine requests `H` while `H < A`; above that threshold it requests
`max(P, 0.65 H)`. The effective floor also retains a higher previously approved
floor until a valid relaxation takes effect. Crossing the activation threshold
does not silently erase an earlier floor or its approval history.

`execution_control/risk.py` uses `E < effective_floor` for a breach. Equality by
itself is allowed. Order affordability is a different question:

- If `E = effective_floor`, available loss/cost headroom is zero.
- At an unchanged mark, buying notional `Q > 0` with fee fraction `f > 0`
  reduces equity by `Q f`, before spread, exit costs or adverse price changes.
- The existing `core/odds/costs.py:afford` preserves cash covering the floor and
  reserved exit charges. Its `first_stake` therefore returns zero in this case;
  `core/odds/simulate.py` reports `STUCK_AT_START`.
- A positive first-day intraday budget, a positive expected return, a paper
  strategy pass or the 22:00 recovery target does not create floor headroom.
  A zero-fee assumption alone also does not create cash above the protected
  floor under the shipped `floor_safe` sizing rule.

This is a binding feasibility issue under the confirmed policy, not a claim that
equality itself violates risk rules. Preserve the policy and report the blocked
entry accurately. Do not lower the floor, exempt fees, rebase away prior losses,
invent a market profit or treat an expected recovery as guaranteed. Any future
proposal must show a lawful, reviewed funding/valuation/execution path consistent
with the same protected amounts and history. There is currently no demonstrated
path in this audit that does so. Target-hit probability remains unmeasured.

## Finite completion checklist

These items define evidence needed for completion; a row is not complete merely
because a document or parser exists. Parallel agents may close implementation
items in this branch, but genuine external evidence and owner actions remain
separate.

| ID | Deliverable and acceptance evidence | Dependency / boundary |
| --- | --- | --- |
| M1 | Held-position source contract and implementation: exact fills/fees, complete valuation path, missing/duplicate/out-of-order records, boundary and restart fixtures. | Upbit first; requires honest coverage semantics. Periodic samples cannot be relabelled as complete extrema. |
| M2 | Genuine product-term refresh with unchanged economic terms distinguished from changed terms; bound profile/session/dispatch tests. | M1-independent development; the actual provider observations occur in the owner's environment. |
| M3 | Controlled coordinator and owner lifecycle commands with immutable prepared-object identity, reconciliation, cancel/exit and persistent-stop tests. | M1/M2 and reviewed source/owner authority; no automatic signing or activation. |
| M4 | Authenticated review/selection wiring and exact final source, profile, rule and driver bindings. | Final capture implementation and unchanged candidate family; no fabricated PASS/reviewer. |
| M5 | Final merged source, Linux regression plus required Windows checks, actual timing/boundary and recovery observations. | Fake fixtures establish software behavior; Windows/network observations must be measured separately. |
| M6 | Actual complete prospective capture, evaluation of every candidate, failed-trial retention, source/implementation review. | New fixed future window, private profile, current real terms and preregistration/publication before capture. |
| M7 | Current owner code/table/review approvals and actual session preparation/authorization. | Owner-only on the reviewed deployment. Initial/loosened limits retain their next-Seoul-date rule; existing effective limits must be verified rather than reset. |
| M8 | Demonstrated entry feasibility under unchanged principal/peak floors and all modeled entry/exit costs. | Currently unresolved; code completion and elapsed time cannot establish it. |
| M9 | November rule renewal: resolve outstanding sources and submit the supported row/deadline changes for review. | The PR #12 audit did not extend the November 22/23 deadlines. |
| M10 | KIS live-launch expansion: complete account collector, current terms, supported cancellation/status reconciliation, calendar/tax/FX model, prospective evaluation and owner-operated trial. | Separate from KIS Live viewing; complete these before claiming KIS automatic-trading readiness. |
| M11 | OKX live-launch expansion: verified product/access terms, independent marks, complete account collector, FX/cost research and controlled integration. | Separate from public data, E1 inquiry and cash-limit codecs; no trading with a read-only key. |
| M12 | Multi-market comparison and additional products: common comparison protocol, full disclosed selection family, independent asset-risk grouping and product-specific acceptance. | Depends on M10/M11 or other fully validated market paths. A shared SR label is not comparable evidence. |

## What a 48-hour deadline can and cannot mean

Let `t0` be the start of the requested deadline and `ts` the actual start of the
new fixed 48-hour capture. That capture ends at `ts + 48 hours`. If preparation,
source freeze, publication or setup makes `ts > t0`, its end is later than
`t0 + 48 hours`, before allowing time for evaluation, review or owner actions.
Parallel development does not remove this elapsed-time dependency.

The installed capture manifest binds `study.py`, `paper_capture.py`, `program.py`,
`strategy.py`, `execution_accounts/quotes.py`, `execution/transport.py` and
`execution/upbit_inquiry.py`. Work outside that frozen boundary may run in
parallel if the profile/economic/strategy contracts remain unchanged. Changing
bound code or terms requires correctly matched new evidence; it cannot be
hidden behind the old commitment.

The 48-hour draft is an engineering pilot, not an established statistical-power
result. A completed window may have too few trades or fail return, cost, delay,
drawdown or family-adjusted significance checks. A missed slot stops the trial;
retries use new declared future windows. No finish date for a profitable strategy
or first order can be inferred from software effort. The confirmed floor and
owner-only signatures are additional independent boundaries.

A defensible 48-hour development commitment is a reviewable, tested batch with
each remaining blocker stated and an executable next step. It is not evidence
that all markets, live account validation, a future 48-hour study and successful
trading have already been completed. This document introduces no shorter study,
weaker filter, floor exception, simulated signature or deadline extension.

This software and documentation are not legal, tax or investment advice, and
their authors do not act as licensed advisers.
