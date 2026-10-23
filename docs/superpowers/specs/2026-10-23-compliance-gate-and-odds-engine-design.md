# TRADEGEN compliance gate and odds engine

Date: 2026-10-23.

Status:
- **Revision 2.1**: rev 2 plus the owner decisions D11 to D14.
- Round 1 was run on rev 1 (`6113c27`).
  - Gemini (Antigravity) said **REJECT**.
  - The Claude adversarial workflow (5 reviewers, each finding checked by a skeptic) confirmed most of the same points.
  - Both reviews are in `docs/superpowers/specs/2026-10-23-review-gate-odds/`. Appendix B gives a ruling on every
    finding.
- GPT (Codex) referees round 2 after the Codex quota resets on 2026-10-27 19:16.
- **The owner decided D11 to D14 on 2026-10-23**, taking the recommended option each time.
- Implementation will be planned as two plans, compliance first and then odds, because odds depends on `screen()`.

Inputs:
- `reports/Korean resident trading venue legality.md`, with its notes in `research_notes/Korean resident trading venue legality/`;
- `research_notes/QUANTGEN asset coverage expansion/crypto_wallets_connectivity.md` (crypto ETP and derivative rules);
- `research_notes/QUANTGEN TRADEGEN split map/split_map.md`;
- the Phase A isolation (commit `d47cea9`).

> This is research and software design, not legal, tax or investment advice. Neither TRADEGEN nor its author is a
> licensed advisor. Before any real-money feature ships, the open legal points in section 11 need Korean-qualified
> counsel.

---

## 1. Purpose and scope

TRADEGEN is a personal trading program for one Korean-resident individual trading their own money, starting from about
KRW 42,000 (USD 30). It has two tracks:
- a **moonshot** track aimed at USD 30,000, about 1,000 times the stake;
- a realistic **compounding** track.

This spec covers the first two building blocks:
1. **The compliance gate** (`core/compliance/`). It decides whether a venue, instrument, order, transfer or plan is
   allowed for this owner under Korean law, as researched. Unknown, unapproved or stale cases are refused for new
   exposure.
2. **The odds engine** (`core/odds/`). It shows the honest chance of each outcome for a plan the gate allows.

**Neither package can place an order.** Execution, strategy research and the UI each get their own spec. They are built
on these two interfaces: `decide()` / `verify_permit()` and `OddsReport`.

**Scope limits in this version:**
- Odds plans have **one leg**, with no leverage and no short selling. Multi-leg, leveraged and short plans are refused
  with a named reason. They are added when the strategies spec needs them.
- The gate still covers every instrument class, so execution later inherits the full rule set.

## 2. Owner decisions (fixed inputs)

| # | Decision | Status |
|---|---|---|
| D1 | Build order: gate and odds engine first (no money moves), then execution, then strategies and the UI | decided 2026-10-23 |
| D2 | Accounts: KIS stock account; Upbit (opened 2026-10-23), the lawful KRW-spot crypto venue; OKX (overseas exchange) | decided |
| D3 | Ruin = equity reaching the owner's hard total-loss floor. Execution halts for good there, and the odds engine and the kill switch read one shared setting | decided |
| D4 | The compounding track reports an outcome ladder: P(+10%), P(+25%), P(2x), P(10x), P(target), median and 5th-percentile ending equity, and P(lose the stake). There is no single target | decided |
| D5 | A rule row past its review date fails closed, and the owner is alerted on every channel: iOS push via the Claude app, email to their own address, and a Windows notification. D11 refines what is blocked | decided; refined by D11 |
| D6 | OKX spot is grey. It is off by default. Each armed session needs a warning acknowledgement, and OKX exposure is capped at an owner-set share of equity. It switches off automatically on 2026-12-03 until re-reviewed. OKX derivatives and P2P are hard-blocked | decided |
| D7 | Every plan shows P(reaching the target) and P(losing the stake), with bold play as the reference. Section 7.4 refines this: bold play is shown beside the exact optimum and the ceiling | decided; refined |
| D8 | Execution is disarmed by default, armed per session by the owner only, with hard daily and total loss limits, a kill switch and an audit log. The owner adds trading-scope keys | decided; execution spec |
| D9 | Approach A: rules as data, a pure `decide()` kernel, and a plan simulator | decided |
| D10 | Grey venues other than OKX (Binance, Bybit, Bitget, Hyperliquid, pump.fun, Jupiter, Uniswap), and the lawful but non-trading Betman, Lotto and Speed-On, are `out_of_scope`, so they are blocked. Enabling one needs a reviewed `grey` row with the report's warning bundle (section 5.3) | follows D2/D6; stricter than the report |
| D11 | **Exits stay open.** Stale rows, auto-off, unmet gates and caps block **new exposure only**. A reduce-only sell, or a withdrawal to an FIU-registered domestic exchange, is still allowed. Conduct rows and the hard-coded floor still apply | decided 2026-10-23 (narrows D5) |
| D12 | **Loss limits and caps tighten at once and loosen slowly.** Raising the floor, lowering the daily limit or lowering the cap takes effect immediately. A loosening takes effect only from the next Asia/Seoul date, never inside an armed session, and never after a recorded halt | decided 2026-10-23 |
| D13 | **Validated edges.** A strategy card counts as a "tested edge", shown in a labelled column and never in the headline, only if it is one of these: (a) a hash-chained registry verdict of PASS; or (b) a committed `validate.ModelCard` with decision PASS whose out-of-sample run TRADEGEN can re-create and re-verify. Today only (b) exists: `S_C3_crypto_trend_krwbtc`, a daily trend rule on KRW-BTC, out-of-sample Sharpe 1.22, 90% CI [0.62, 1.77] | decided 2026-10-23 |
| D14 | **Owner confirmation.** Owner-only writes need an interactive console, with input from a TTY rather than a pipe, and the owner must retype a random code shown on screen | decided 2026-10-23 (console + retyped code; no PIN) |

## 3. The honest numbers, up front

These were checked by direct computation on 2026-10-23.

- **The ceiling.** If every bet has zero or negative expected value after costs, at every point where a trade can
  happen, and losses stop at the account balance, then wealth is a non-negative supermartingale. By optional stopping,
  P(ever reaching T) ≤ W₀/T for every strategy. For KRW 42,000 → KRW 42,000,000 that is **0.1% (1 in 1,000)**.
- **With a loss floor.** If equity is absorbed at the floor L and no single price move can push it below L_min, the
  bound tightens to (W₀ − L_min)/(T − L_min). With L = L_min = KRW 21,000, half the stake, that is **0.050%**.
- **Bold play (Dubins–Savage).** It is the best a subfair even-money game allows: always stake enough to reach the goal.
  - Exact P(1,000×) is **0.1000%** at p = 0.50, **0.0816%** at 0.49, **0.0346%** at 0.45 and **0.0106%** at 0.40.
  - With a floor at half the stake it is 0.0400% at p = 0.49.
  - It loses the stake in more than 99.9% of months.
- **KRX cannot do it in a month.**
  - The ±30% daily limit caps one KRX position at 1.3ⁿ over n sessions. A 30-day window holds 18 to 22 KRX sessions,
    so the cap is **about 112× to 321×**.
  - A 1,000× month from 1x KRX shares or ETFs is therefore impossible, not merely unlikely.
- **Kelly** aims at long-run growth, not at reaching a target by a deadline.
  - With zero edge it bets nothing.
  - A genuine 52.5% even-money edge needs about **5,524 bets** to grow 1,000× at full Kelly.
- **The typical result versus the average result.**
  - With no edge, the *average* ending equity is the stake minus costs, because rare jackpots offset the many losses.
  - The *typical* (median) moonshot month ends at the floor: bold play does so in 99.95% of months.
  - Every card shows both, typical first (section 7.5).
- **Realistic odds of USD 30 → USD 30,000 in a month:** about 0.01%, up to roughly 0.03% for long far-out-of-the-money
  US options, and never above 0.1% without a real edge.
- **Base rates.** In every retail group studied, most traders lose:
  - Kalshi takers lose about 32% of what they stake;
  - 74–89% of EU retail CFD accounts lose money;
  - 87.7% of Indian retail equity-derivatives traders lost in FY26;
  - 62% of new Korean investors lost in 2020.

  (report lines 161–163)
- **Monte Carlo precision.** A 0.01% event needs about 1,000,000 simulated months to reach a 10% relative standard
  error. A 0.1% event needs about 100,000.

No report may promise more than this.

---

## 4. Architecture

Two new packages follow the repo's `core/<domain>` pattern. Neither contains an order path.

```
core/compliance/
  kr_rules.yaml        the rules table (data; venue rows + conduct rows); dates quoted as strings
  instruments.yaml     the instrument map (symbol -> class, multiple, underlying kind, eligibility facts, source)
  rules.py             safe loader + schema/vocabulary check + hash; RulesTable.invalid(reason); CLI --check
  gate.py              decide(), screen(), permit(), verify_permit(), render_warning(); hard-coded floor (pure)
  owner.py             owner log: approvals, flags, acknowledgements, caps, limits, withdrawal addresses (append-only)
  alerts.py            due(rows, today) (pure), the alert text catalogue, the Windows toast, the alerts.jsonl writer CLI

core/odds/
  plan.py              Plan, Leg, Sizing, Limits (kw_only dataclasses; validation)
  bars.py              daily open/close loader for bootstrap legs (reuses the data clients; own cache under ~/.tradegen)
  venues.yaml          venue facts: lot sizes, minimum orders, fee extras, tick ladders, sources (owner-approved)
  models.py            return models under one no-edge null: SignFlipBootstrap, GarchT; edge sources
  simulate.py          vectorised, chunked path simulator
  bold.py              exact references: ceiling, structural maximum, exact optimum and bold policy (dynamic programme)
  report.py            OddsReport and rendering from the sentence catalogue; flags; language guard
```

**How data flows**
1. A `Plan` goes to `gate.screen(plan, ctx)`. If any leg is blocked, the plan is refused and is never simulated or
   compared.
2. `odds.simulate(plan, screening, cal, limits, ...)` refuses an unscreened plan, and produces an `OddsReport`.
3. Execution, in its own spec, obtains a `Permit` from `gate.permit(intent, ctx)` and calls
   `verify_permit(permit, intent, ctx_now)` at send time. A Permit object is never treated as proof by itself.

**Boundaries and repository facts** (verified 2026-10-23)
- `decide()`, `screen()`, `permit()`, `verify_permit()` and `render_warning()` are pure. They do no I/O and read no
  clock: the Asia/Seoul date, the rules table, the instrument map, the owner state and the session are all passed in.
  - `rules.load()` never raises. On any failure it returns `RulesTable.invalid(reason)`, and on an invalid table every
    decision is BLOCK.
- **The odds engine does not import `core.engine.orders`.** Guard T-RO-01 (`tests/macro_m0_harness.py`) allows only
  `core/engine/` and two skills modules to import it, and `test_s4` makes `orders.py` add-only, so its functions cannot
  be moved either. The odds engine therefore:
  - checks KRX price limits itself, from the dated `price_limit` in `kr_regime_tags.yaml`, through `core.calendars`;
  - uses the KRX tick ladder from `venues.yaml`, because `instruments.TICK_TABLES` has only the KRX ETF ladder;
  - declares `LIMIT_DOWN_CARRY_COST_MULTIPLIER = 2.0` locally, and a test (tests are not scanned) asserts it equals
    `core.engine.orders.LIMIT_DOWN_CARRY_COST_MULTIPLIER`.
- **Price history.** `core.quant.history.History` holds closes only, as do all its loaders and its cache.
  - `core/odds/bars.py` is a new loader of daily (open, close) bars, built on the same clients:
    - KIS daily rows, for KRX;
    - `data.crypto` Candles, for Upbit KRW-* and Binance *USDT;
    - yfinance, for US names.
  - Its cache lives under `state_root()/odds_bars/`, with a sha256 manifest.
  - `History` and its loaders are not changed.
  - A leg without open prices falls back to close-only checks, flagged `CLOSE_ONLY_CHECKS`.
- **Calendars.** Every shipped calendar and regime-tag file in `core/calendars/data/` is an unsigned draft
  (`signed_off_by: null`), so `clocks.is_session`, `sessions_between` and `regime_tags` raise `CalendarUnsigned` for KR
  and US.
  - `simulate()` takes a `cal: CalendarSet`. While the files are unsigned, every KRX or US plan is refused with
    `CALENDAR_UNSIGNED`, and only crypto plans run.
  - Signing is an owner act (section 11).
  - The tests use the repo's signed fixture set (`tests/macro_m1_calendars.py`).
- **Costs.**
  - Per-side base cost = `validate.cost_bp(validate.cost_class(symbol))`, in bp. Equivalently it is
    `instruments.cost_per_side(BOOK[cls])` with `price=None`, through an explicit map:
    - `krx_stock` → `KRX_stock_book`;
    - `krx_etf` → `KRX_ETF_line`;
    - `us` → `US_shares_KIS`;
    - `crypto` → `crypto_venue`.
  - Passing a cost-class string straight to `cost_per_side` raises `NotTradable`.
  - `instruments.check_cost_policy` validates macro-card headers and is not used here. `venues.yaml` extras are checked
    by their own rule, `odds.models.check_extras`, which requires every extra to be ≥ 0 and allows a fee row only as
    max(table, fee).
- **Validated cards.**
  - The chained registry (`core.quant.cards`, `model_card.macro` v2.0) has no out-of-sample return field, so it cannot
    supply an edge today.
  - The expansion study's committed `validate.ModelCard` files in `docs/asset_expansion/cards/` can, under D13.
  - The live multiplier is `gate_stats.LIVE_SHARPE_MULTIPLIER` (0.60), imported and never written as a literal.
- **Provenance.**
  - `macro_artifacts.GIT_HASH` is the constant `UNVERSIONED`, so it is not used.
  - The report records `gate_ledger.repo_anchor()` (`git:<sha>`, which reads packed-refs since `d47cea9`) and
    `macro_artifacts.tree_hash()`.
- **Guards to respect:**
  - the read-only scans: `tests/acceptance.py` test_08 and test_09, and T-RO-01;
  - no identifier, docstring or comment containing an order-endpoint name or `CANO`;
  - no function or method named `transfer`, `withdraw` or `deposit_address` (`macro_m0_harness.FORBIDDEN_CALLS`);
  - `core.odds.` and `core.compliance.` are added to `context_log.ACTING_MODULE_PREFIXES`, so T-CTX-01 covers them.
- **Paths.** Every mutable path goes through `config.state_path()` / `state_root()`. Every file-writing function calls
  `core.isolation.refuse_quantgen()` immediately before opening its target.

---

## 5. The rules table and the instrument map

### 5.1 Row schema

```yaml
schema: tradegen.kr_rules/2
scope: "Korean-resident individual, own funds only"
known_changes: ["2026-12-03", "2027-01-01", "2027-02-18"]     # FX Act; crypto tax; travel-rule expansion
rows:
  - id: KR-OKX-SPOT
    kind: venue                              # venue | conduct
    match: {venue: [okx], instrument: [crypto_spot]}
    treatment: grey                          # hard_block | gated | grey | allow | out_of_scope
    max_leverage: 1.0                        # default 1.0
    requires: {owner: [age_of_majority]}     # gated/grey rows: deposits, cash, courses, broker approvals, age
    ack: per_session                         # gated or grey rows that need this session's acknowledgement
    grey: {cap_key: okx_equity_share, auto_off: "2026-12-03"}
    warning: >-
      OKX is not registered with Korea's FIU. The FSC tells users of unregistered exchanges to withdraw their money. You
      get no Korean user protection, and withdrawals can be frozen. Upbit may stop transfers to OKX without notice. New
      rules start on 2026-12-03 and about 2027-02-18. TRADEGEN turns OKX off on 2026-12-03 and caps it at {cap} of your
      equity.
    reason: "Operator unregistered with the FIU; no user penalty found; the FIU contests transfers to it"
    basis: ["특금법 registration duty", "FSC release 2026-06-24",
            "amended FX Act (promulgated 2026-06-02, effective 2026-12-03; Act No. 21714 secondary-sourced)"]
    sources: ["https://www.fsc.go.kr/no010101/87177"]
    research: "reports/Korean resident trading venue legality.md#compliance-matrix row 14"
    confidence: low                          # OKX spot is not separately rated; this is the row-13 analogue
    effective_from: "2021-03-25"             # the regime start, not a press-release date
    effective_until: "2027-02-18"            # the travel-rule expansion needs a new reviewed row
    review_by: "2026-11-22"
    reviews: [{date: "2026-10-23", by: claude-research, checked: "report rows 13-15, 19; crypto notes section 3"}]
```

**Table rules** (the loader enforces each one, and tests cover them)
- **Loading.**
  - A YAML SafeLoader subclass rejects duplicate keys, anchors, aliases and native (unquoted) dates.
  - The file is capped at 256 KB.
  - Every `match` value must belong to the section 5.2 vocabulary, and `any` is allowed only on `hard_block`,
    `out_of_scope` and conduct rows.
  - Any violation makes the table `INVALID`.
- **Sources.** Every row has at least one source and a pointer to the research it came from.
- **Review cadence: monthly,** as the report recommends during the rule-drift window (report line 84).
  - `review_by` is at most 31 days after the row's latest review.
  - `review_by` must also not be later than the day before the next `known_changes` date that affects the row.
- **Coverage.** Every one of the 38 legality-matrix rows is covered by at least one table row.
- **Owner approval (the meaning of "owner-signed").** A table counts only if `owner.jsonl` holds a
  `rules_approved {rules_hash}` event written through the owner-confirmation API (D14).
  - An unapproved table is `INVALID`.
  - A `reviews` entry by anyone other than the owner is a draft: it cannot move `review_by` or `auto_off` until the owner
    approves the resulting hash.
  - A git commit is **not** evidence of owner approval, because Claude makes this repo's commits under the owner's
    identity.
  - `instruments.yaml` and `venues.yaml` follow the same rule, through `instruments_approved {hash}` and
    `venues_approved {hash}`.
- **Hard-coded floor.** `gate.py` blocks the following whatever the table says, as defence in depth:
  - the conduct classes, the prediction venues and the state-blocked ids;
  - OKX derivatives and P2P;
  - `fx_margin`, `cfd`, `overseas_future`, `us_crypto_etp` and `overseas_crypto_derivative`.

### 5.2 Vocabulary

**Venue ids**
- Brokers and domestic exchanges: `kis`, `upbit`, `bithumb`, `coinone`, `korbit`, `gopax`.
- Overseas and decentralised: `okx`, `binance`, `bybit`, `bitget`, `hyperliquid`, `pumpfun`, `jupiter`, `uniswap`,
  `drift`.
- Prediction markets: `polymarket`, `kalshi`, `limitless`, `myriad`, `opinion`, `predictfun`.
- Platforms: `robinhood`, `cryptocom`, `predictit`, `sportsbook` (any foreign or crypto sportsbook).
- Lotteries and racing: `betman`, `lotto`, `speedon`.
- Foreign brokers and apps: `ibkr`, `moomoo`, `webull`, `etoro`, `offshore_fx_cfd`.
- The state-blocked ids of section 5.3.
- Ids are exact lower-case ASCII with no case folding. Anything else is unknown, which means BLOCK.

**Instrument classes**
- **KRX:**
  - `krx_cash_share`, `konex_share`, `krx_etf_1x`, `krx_etn_1x`, `krx_inverse_1x` (index or basket underlyings only);
  - `krx_lev_etp` (index or basket, multiple other than ±1);
  - `krx_derivative_stage1` (futures and long options), `krx_derivative_stage2` (option writing and VKOSPI futures);
  - `elw`.
- **Single-underlying leveraged and inverse:** `single_stock_lev_etp`, meaning any ETF/ETN on a single underlying with
  a multiple other than +1, **including −1x, domestic or overseas-listed**.
- **Credit and short:** `credit_buy`, `retail_short`, `fx_margin`, `cfd`.
- **US:**
  - `us_stock`, `us_etf_1x`, `us_inverse_1x` (index or basket only), `us_lev_etp` (index or basket);
  - `us_option_long`, `us_option_write`;
  - `us_crypto_etp`: any US-listed product whose underlying is crypto, spot or index (for example IBIT, FBTC, ETHA,
    GDLC, EZPZ).
- **Futures:** `overseas_future`, and `overseas_crypto_derivative` (for example CME bitcoin futures and options).
- **Crypto:** `crypto_spot`, `crypto_lending`, `crypto_derivative`, `crypto_p2p`, `crypto_transfer`.
- **Other:** `event_contract`, `sports_bet`, `lottery`.

**The instrument map (`instruments.yaml`, owner-approved).**
- **Contents:** each symbol maps to its class, multiple, underlying kind (single | index | basket | crypto), eligibility
  facts (for lending: top-20 or listed on 3 or more KRW markets) and a source, under the same review rules as the table.
- **Fail closed.** `decide()` and `screen()` **derive** the class from `intent.symbol`:
  - an unknown symbol gives BLOCK;
  - a caller-supplied class that disagrees with the map gives BLOCK (`class mismatch`).

  This is the root fix for mislabelled products. TQQQ cannot pass as `us_etf_1x`, and 252670 (KODEX 200 Futures
  Inverse 2X) cannot pass as `krx_etf_1x`.

### 5.3 Seed rows

Each row carries the research and source fields from section 5.1. The report's "Recommended actions for a
trading-software designer" table sets each treatment, except where D10 is stricter.

| Row id | Match | Treatment | Matrix row |
|---|---|---|---|
| KR-KIS-KRX-SHARE | kis: krx_cash_share | allow (1x; ±30% limit; 0.20% sell tax, ETFs exempt) | 21 |
| KR-KIS-KONEX | kis: konex_share | allow (±15% limit; 0.10% tax) | 21 |
| KR-KIS-KRX-ETF1X | kis: krx_etf_1x, krx_etn_1x | allow | 21 |
| KR-KIS-KRX-INV1X | kis: krx_inverse_1x | allow; confidence low (confirm with the broker) | 22 |
| KR-KIS-KRX-LEV | kis: krx_lev_etp | gated: deposit ≥ KRW 10M + `kofia_leveraged_1h` | 25 |
| KR-KIS-SINGLE-LEV | kis: single_stock_lev_etp | gated: **cash** ≥ KRW 30M (cash only, re-checked on every buy, additional buys included) + `single_stock_lev_3h` + `single_stock_mock_5h_5d` | 26 |
| KR-KIS-KRX-DERIV-1 | kis: krx_derivative_stage1 | gated: deposit ≥ KRW 10M + `broker_approvals.krx_deriv_eligible` (the broker sets course and mock hours by profile; at least 1h + 3h) | 27 |
| KR-KIS-KRX-DERIV-2 | kis: krx_derivative_stage2 | gated: deposit ≥ KRW 20M + `broker_approvals.krx_deriv_stage2` | 27 |
| KR-KIS-ELW | kis: elw | gated: deposit ≥ KRW 15M + `elw_course` | 28 |
| KR-KIS-CREDIT | kis: credit_buy | gated: `broker_approvals.credit`; max 2.2x; per-session acknowledgement; BLOCK on symbols designated 투자경고/투자위험 (designation state in context; unknown state means BLOCK) | 23 |
| KR-KIS-SHORT | kis: retail_short | gated: `kofia_short_edu_30m` + `krx_short_mock_1h` + `broker_approvals.short`; 105% collateral; per-session acknowledgement | 24 |
| KR-KIS-US-STOCK | kis: us_stock, us_etf_1x | allow | 31 |
| KR-KIS-US-INV1X | kis: us_inverse_1x | allow; confidence low (broker notices) | 33 |
| KR-KIS-US-LEV | kis: us_lev_etp | gated: deposit ≥ KRW 10M + `kofia_leveraged_1h` (since 2026-05-22) | 32 |
| KR-KIS-US-OPT-LONG | kis: us_option_long | gated: `broker_approvals.us_option_eligible` (at least 1h + 3h); per-session acknowledgement (commissions of 3–20% of the account per side) | 34 |
| KR-KIS-US-OPT-WRITE | kis: us_option_write | hard_block (recourse leverage; losses can exceed the account) | 34 |
| KR-KIS-US-CRYPTO-ETP | kis: us_crypto_etp | hard_block. FSC January 2024: brokering overseas spot crypto ETFs may breach the FSCMA. The FSS halted GDLC/EZPZ in November 2025. Confidence low; review monthly while the ETF amendment is pending | crypto notes Q4 |
| KR-KIS-CRYPTO-DERIV | kis: overseas_crypto_derivative | hard_block (FSC 2017-12-06: bitcoin is not an underlying asset) | crypto notes Q4 |
| KR-KIS-OVERSEAS-FUT | kis: overseas_future | hard_block (recourse leverage) | 35 |
| KR-KIS-FX-MARGIN | kis: fx_margin | hard_block (USD 10,000 per lot; recourse leverage) | 29 |
| KR-KIS-CFD | kis: cfd | hard_block (professional investors only) | 30 |
| KR-DOMESTIC-SPOT | upbit, bithumb, coinone, korbit: crypto_spot | allow (KRW 5,000 minimum on Upbit) | 10 |
| KR-GOPAX | gopax: any | out_of_scope (VASP renewal delayed indefinitely; not configured) | 10 |
| KR-DOMESTIC-LENDING | upbit, bithumb, coinone, korbit: crypto_lending | gated: `daxa_lending_course` + `daxa_lending_aptitude`; eligible coins only (instrument map); max 1.0x; per-session acknowledgement | 11 |
| KR-DOMESTIC-CRYPTO-DERIV | upbit, bithumb, coinone, korbit: crypto_derivative | hard_block (no legal framework) | 12 |
| KR-TRANSFER-OUT | upbit, bithumb, coinone, korbit: crypto_transfer | allow only to a destination that is itself allowed or grey (6.2 step 5); destination address registered in the owner log; a grey destination needs a per-transfer acknowledgement on top of the session one; `effective_until: "2027-02-18"` | 19 |
| KR-OKX-SPOT | okx: crypto_spot | grey (D6), example in 5.1; requires `age_of_majority` | 14 (13 analogue) |
| KR-OKX-WITHDRAW | okx: crypto_transfer | allow, exit only, to upbit, bithumb, coinone or korbit at a registered address (D11) | 14, 19 |
| KR-OKX-DERIV | okx: crypto_derivative | hard_block (OKX blocks South Korea) | 14 |
| KR-OKX-P2P | okx: crypto_p2p | hard_block (OKX blocks South Korea) | 14 |
| KR-OFFSHORE-CEX | binance, bybit, bitget: any | out_of_scope (D10) | 13 |
| KR-STATE-BLOCKED | kucoin, mexc, phemex, xtcom, bitrue, coinw, poloniex, btcc, bingx, digifinex, and every other site on the KCSC block list of 2026-10-13: any | hard_block (reachable only by VPN) | 15 |
| KR-BITMART | bitmart: any | hard_block (Google Play app block of 2025-03; named in English reports of the 2026-10-13 block, but not in the Korean reports read) | 15 |
| KR-HYPERLIQUID | hyperliquid: any except event_contract | out_of_scope (D10; grey; no wallet) | 16 |
| KR-DEX | pumpfun, jupiter, uniswap: any | out_of_scope (D10). Enabling needs: age 19+, no automatic buys of newly launched tokens, and a liquidation-price warning on perps | 17, 18 |
| KR-DRIFT | drift: any except event_contract | out_of_scope (D10) | 16 analogue |
| KR-PREDICTION | polymarket, kalshi, limitless, myriad, opinion, predictfun, robinhood, cryptocom, predictit: any; hyperliquid and drift: event_contract | hard_block (Criminal Act Art. 246; platform terms) | 1-6 |
| KR-SPORTSBOOK | sportsbook: any | hard_block (National Sports Promotion Act Art. 48(3); Supreme Court 2022도6462) | 7 |
| KR-IBKR | ibkr: any | hard_block (direct foreign-broker routing; FX reporting) | 36 |
| KR-RETAIL-APPS | moomoo, webull, etoro: any | hard_block (blocked or unknown for Korea) | 37 |
| KR-OFFSHORE-FX-CFD | offshore_fx_cfd: any | hard_block | 38 |
| KR-LOTTERY-RACING | betman, lotto, speedon: any | out_of_scope (D10: lawful designated issuers, but not trading) | 8, 9 |
| KR-CONDUCT-EVENT | any venue: event_contract | hard_block (Criminal Act Art. 246) | 1-6 |
| KR-CONDUCT-SPORTS | any venue except betman: sports_bet | hard_block (National Sports Promotion Act Art. 26, 48(3)) | 3, 7 |
| KR-CONDUCT-ROUTE | route ≠ direct | hard_block (VPN or proxy; state blocks; platform terms) | 15, 16 |
| KR-CONDUCT-OTHERS | on_behalf ≠ self, or tag copy_lead / copy_follow | hard_block (pooled money, copy-trading, trading for others: 특금법, Supreme Court 2024도10710) | 20 |
| KR-CONDUCT-FX | tag fx_settlement | hard_block (환치기 under the FX Act, where business-like) | 20 |
| KR-CONDUCT-SIGNALS | publishes_signal | hard_block (VAUPA Art. 10; advisory registration not researched) | 20 |
| KR-CONDUCT-PROMOTE | tag unregistered_vasp_referral | hard_block (FSC 2026-06-24, on promoters of unregistered exchanges). TRADEGEN stores and emits no referral, affiliate or invite codes | 20 |
| KR-CONDUCT-MANIP | tags coordinated, self_match, spoof, layer, mnpi, false_statement, self_issued_coin | hard_block (VAUPA Art. 10(1)–(5)) | 20 |

**Dates**
- Crypto rows are due by 2026-11-22, one month after review. The cadence then pins every crypto, transfer and OKX row to
  2026-12-02 at the latest, the day before the FX Act amendment.
- `KR-TRANSFER-OUT` and `KR-OKX-SPOT` end on 2027-02-18, when the travel-rule expansion takes effect: six months after
  promulgation, per FSC 2026-08-11 (the promulgation date is secondary-sourced).
- Tax-sensitive and leverage rows are due before the November and December votes.
- Every other row is due within the 31-day cadence.

### 5.4 Lifecycle and alerts

- **Fail closed.** If today is after a row's `review_by`, that row blocks **new exposure** with the reason
  "stale: review by YYYY-MM-DD passed". Under D11, exits stay allowed.
- **Re-review.**
  1. Someone re-checks the row's sources and drafts a `reviews` entry, moving `review_by`. Claude may draft this.
  2. The owner approves the new table hash through the confirmation API (`rules_approved`).
  3. Until then, the previous approved hash stays in force. If none is approved, the table is `INVALID`.
- **`python -m core.compliance.rules --check [--today YYYY-MM-DD]`** checks the table, the instrument map, the venue
  table and the owner-log chain and approvals. Exit codes:
  - 0: nothing due;
  - 1: something due within 14 days;
  - 2: something overdue;
  - 3: invalid, unapproved, or the owner chain is broken. Exit 3 blocks every new-exposure decision.
- **Who does what.**
  - `alerts.py` renders the alert text from a fixed template: row id, `review_by`, `auto_off`, days left and the owner-log
    head. Rule free text is never interpolated.
  - It shows the Windows toast (PowerShell WinRT call, no new dependency).
  - It writes `alerts.jsonl` through `python -m core.compliance.alerts --log <channel> <ok|fail> [--detail]`.
- **The daily job.** A local scheduled Claude task runs at 09:00 KST:
  1. It runs `--check`.
  2. While anything is overdue or invalid, it alerts every day. When a row is due within 14 days, it alerts on the first
     run at or below 14 days and again at or below 3 days, so a missed run never skips a threshold.
  3. It sends the iOS push through the Claude app.
  4. It sends an email **only to `sapientia@korea.ac.kr`**. That address is written literally into the task prompt and
     into `alerts.OWNER_ALERT_EMAIL`, and changing it requires the owner to edit the task in chat.
  5. It records each result through the `--log` CLI.
- **Authority.** The owner approves the task once, at creation. Their D5 instruction is the standing authority for
  these self-addressed alerts, and for nothing else.
- **Failures.** A failed channel is announced on the others, and a failed check is itself alerted.
- **The in-app banner** shows while any row is overdue or the table is invalid. The check also runs at every app start,
  because the scheduled task runs only while the PC is on.
- **No credential** is stored in TRADEGEN for alerts.

---

## 6. The `decide()` kernel (`core/compliance/gate.py`)

### 6.1 Types

```python
@dataclass(frozen=True, kw_only=True)
class Intent:
    kind: str                       # "order" | "transfer" | "plan_leg"
    venue: str                      # exact venue id (5.2)
    symbol: str | None              # orders and plan legs: the class is derived from instruments.yaml
    instrument: str                 # caller's class; must equal the derived class
    side: str = "buy"               # "buy" | "sell" | "sell_short"
    reduces_position: bool = False  # a sell that only lowers an existing long (execution verifies it against holdings)
    leverage: float = 1.0           # the financing or product multiple (1.0 = cash), not position size
    notional_krw: float = 0.0
    destination_venue: str | None = None    # transfers only
    destination_address: str | None = None  # transfers only; must be registered in the owner log
    route: str = "direct"           # anything else gives BLOCK
    on_behalf: str = "self"         # anything else gives BLOCK; orders copied to followers are not "self"
    publishes_signal: bool = False
    tags: frozenset = frozenset()   # subset of the conduct-tag vocabulary (5.3); anything else gives BLOCK
    client_order_id: str | None = None      # execution's nonce

@dataclass(frozen=True, kw_only=True)
class Context:
    date: date                      # the Asia/Seoul calendar date of the moment of decision; never UTC or a trade date
    rules: RulesTable; instruments: InstrumentMap
    owner: OwnerState               # resolved from owner.jsonl: approvals, flags, caps, limits, addresses, head
    session: SessionState           # session_id, armed date, acknowledgements bound to warning hashes
    equity_krw: float
    exposure_krw: Mapping[str, float]       # by venue; includes open orders and unexpired permits
    designations: Mapping[str, str]         # symbol -> KRX designation (normal | caution | warning | risk); unknown = absent

@dataclass(frozen=True)
class Decision:
    verdict: str                    # "ALLOW" | "ALLOW_EXIT" | "ACK_REQUIRED" | "BLOCK"
    reasons: tuple                  # ((row_id, catalogue sentence id, slots), ...), strictest first
    intent_hash: str; rules_hash: str; ctx_hash: str; owner_head: str; date: date; decision_id: str

@dataclass(frozen=True)
class Permit:                       # only from ALLOW or ALLOW_EXIT, via permit(intent, ctx)
    decision_id: str; intent_hash: str; rules_hash: str; ctx_hash: str; session_id: str; date: date
```

### 6.2 Evaluation order

1. **Validate everything.** Any of the following gives `BLOCK ("malformed: <field>")`:
   - a numeric field that is not finite (`math.isfinite`);
   - `notional_krw < 0`, `leverage < 1`, `equity_krw ≤ 0`, or a cap outside [0, 1];
   - `publishes_signal` that is not exactly a `bool`;
   - ids that are not exact vocabulary members;
   - `tags` that are not a subset of the conduct vocabulary;
   - `kind == "transfer"` that does not coincide with `instrument == "crypto_transfer"` and with a known
     `destination_venue` different from `venue`;
   - an unknown symbol, or a class that does not match the symbol.

   The kernel never raises. Any internal error becomes `BLOCK ("internal error: <type>")`. An invalid or unapproved
   rules table, instrument map or broken owner chain also gives BLOCK.
2. **The hard-coded floor and the conduct rows** apply on every venue and to exits as well. Each one gives BLOCK.
3. **Exits (D11).** An exit is either a `sell` with `reduces_position = True` where exposure after the
   intent is below exposure before it, or a `crypto_transfer` to an `allow`-row domestic exchange at a registered
   address.
   - If no venue row for the pair is `hard_block`, the result is `ALLOW_EXIT`.
   - Stale rows, auto-off, unmet gates and caps do not block exits. Even a `hard_block` venue row lets an exit through
     with a warning, so funds can always be withdrawn by lawful means.
4. **Venue rows.** Only rows in force on `ctx.date` count: `effective_from ≤ date`, and `effective_until` either null or
   later than `date`. All dates are Asia/Seoul calendar dates.
   - **No matching row:** BLOCK. When several rows match, **all** apply and the strictest result wins.
   - For each matching row:
     - **stale** (`date > review_by`): BLOCK;
     - **`hard_block` or `out_of_scope`**: BLOCK;
     - **`gated`**: every `requires` item must be met by evidenced owner state:
       - courses and broker approvals need a date and an evidence reference;
       - deposit and cash snapshots must be dated within 7 days;
       - `age_of_majority` needs a birth date and evidence;
       - `KR-KIS-CREDIT` also needs a designation state that is known and not warning or risk.

       Anything unmet is BLOCK, naming what is missing. The broker may set stricter walls than these pre-checks.
     - **`grey`**:
       - BLOCK if `date ≥ auto_off`, the cap is unset, or `requires` is unmet;
       - BLOCK if exposure after the intent would exceed `cap × equity`. Exposure after the intent is current venue
         exposure plus `notional_krw` for a buy or a transfer in, and minus it for a sell;
     - **`ack: per_session`** (on a gated or grey row): `ACK_REQUIRED` unless `ctx.session` holds an acknowledgement
       for this row with `warning_sha256 == sha256(render_warning(row, slots))` and the current `session_id`;
     - **`allow`**: ALLOW.
   - **Leverage:** `leverage > row.max_leverage` gives BLOCK.
5. **Transfers.** The destination is evaluated as a `crypto_spot` intent on `destination_venue` with the same notional.
   The transfer gets the stricter of the two results.
   - A grey destination also needs a per-transfer acknowledgement, recorded against the intent hash.
   - An unregistered destination address gives BLOCK. Below KRW 1M, before about 2027-02-18, exchanges need not match
     names, so the owner log's registered address is the guard.
6. **Combine.** BLOCK beats ACK_REQUIRED, which beats ALLOW and ALLOW_EXIT. Every reason is kept.

### 6.3 Permits and plan screening

- **`permit(intent, ctx)`** calls `decide()` itself and returns a `Permit` only for ALLOW or ALLOW_EXIT.
- **`verify_permit(permit, intent, ctx_now)`** re-runs `decide(intent, ctx_now)`. It requires ALLOW or ALLOW_EXIT, the
  same intent hash, the same `session_id` and the same Asia/Seoul date.
  - A permit expires at 24:00 Asia/Seoul on its date. Execution recomputes the date at send time.
  - Single use, the audit trail and `client_order_id` uniqueness belong to the execution spec.
- **`screen(plan, ctx)`** decides every leg as a `plan_leg` intent.
  - Its notional is the leg's first stake after the section 7.1 cuts, including the grey cap.
  - It also scans the whole horizon `[start, start + horizon]` for any `review_by`, `auto_off` or `effective_until` that
    falls inside it. Such a date is flagged `RULE_CHANGE_IN_HORIZON`, and the simulation exits the position on that date,
    with costs charged.
  - The returned `Screening` carries every decision and a hash that `simulate()` requires.

### 6.4 The owner log (`core/compliance/owner.py`)

- **Storage:** `~/.tradegen/compliance/owner.jsonl`, append-only. Every line carries both `prev_sha256` and its own
  `row_sha256` (the canonical JSON of the row minus that field), following `core/quant/gate_ledger.py`. That way the
  last line cannot be edited unnoticed.
- **Head anchoring.** Every Decision's `owner_head` (line count and last `row_sha256`) and every `alerts.jsonl` row
  record the log head. The daily alert email carries it too, which makes the owner's mailbox an external anchor.
  - A log shorter than, or different from, the highest head recorded anywhere is **broken**.
  - When the log is broken, every flag, acknowledgement, cap, limit, approval and address counts as absent, and every
    new-exposure decision is BLOCK. The alert fires.
- **Events:**
  - approvals: `rules_approved`, `instruments_approved`, `venues_approved` {hash};
  - flags: `course_completed` {course, date, evidence}, `deposit_snapshot` {krw, cash_krw, source, date},
    `broker_approval` {kind, date, evidence}, `age_of_majority` {birth_date, evidence};
  - settings: `cap_set` {key, value}, `limit_set` {total_loss_floor_krw, daily_loss_krw};
  - transfers: `withdrawal_address` {venue, address, evidence};
  - sessions: `session_armed` / `session_disarmed` {session_id} and `session_ack` {session_id, row_id, warning_sha256}.
    Arming itself is the execution spec's.
- **Who writes it (D14).** Writes go only through the owner-confirmation API:
  - it refuses unless stdin and stdout are interactive consoles (`CONIN$`/TTY);
  - it prints exactly what will be recorded, with a fresh random code, and the owner must retype that code;
  - a pipe or a script is refused (tested);
  - **Claude never writes this log, and never runs the confirmation API.**
- **Tighten fast, loosen slow (D12).**
  - Raising the floor, lowering the daily limit and lowering a cap take effect at once.
  - A loosening takes effect only from the next Asia/Seoul date, never inside an armed session, and never once a halt
    for that floor is recorded. The halt record is defined in the execution spec.
- **Unset limits.** While `total_loss_floor_krw` (0 ≤ L < stake) or `daily_loss_krw` (> 0) is unset:
  - the odds engine refuses with `LIMITS_UNSET`;
  - execution will refuse to arm.

  `owner.py` resolves `Plan.limits` references to KRW numbers, and `simulate()` receives those numbers; it never reads
  `owner.jsonl` itself.

---

## 7. The odds engine (`core/odds/`)

### 7.1 Plans

```python
@dataclass(frozen=True, kw_only=True)
class Leg:
    venue: str; symbol: str          # the class is derived from instruments.yaml (5.2)
    model: str                       # "bootstrap" | "garch_t"
    bracket: Bracket | None = None   # take-profit +u, stop -d (fractions); None = buy-and-hold to the horizon
    edge_source: str = "none"        # "none" | "validated:<card ref>" | "assumed"
    assumed_p: float | None = None   # bracket legs only, with edge_source == "assumed"

@dataclass(frozen=True, kw_only=True)
class Plan:
    name: str                        # cosmetic; excluded from every hash that feeds a seed
    track: str                       # "moonshot" | "compounding"
    stake_krw: float
    target_krw: float                # fixed in KRW at creation; before income tax
    fx_krw_per_usd: float            # recorded FX close used to fix the target
    start: date                      # required; the caller passes it (e.g. the first armed session)
    horizon_days: int                # calendar days
    leg: Leg                         # one leg in this version (multi-leg: MULTI_LEG_UNSUPPORTED)
    sizing: Sizing                   # fixed_fraction(f) | kelly(c <= 0.5) | bold()
```

**Stake.** The stake `s` is the position notional in KRW. Write κ for the per-side cost rate (base plus extras, plus
the sell tax on sells where it applies) and φ for any fixed fee per order.
- **A win at +u** leaves `W + s·u − κ·s·(2 + u) − 2φ`.
- **A loss at −d** leaves `W − s·d − κ·s·(2 − d) − 2φ`, before gap-through.

**Sizing**
- `fixed_fraction(f)`: `s = f·W`.
- `kelly(c)`: `s = c·f*·W`, where f* = argmax E[ln(1 + f·R)] computed numerically from the leg's model under a
  **validated** edge.
  - It uses the lower 95% bound of the card's out-of-sample mean, after `LIVE_SHARPE_MULTIPLIER`.
  - With no validated edge it gives `s = 0`, and the card reads "this plan places no trades".
  - Its label: "aims at long-run growth, not at reaching your target".
- `bold()` (bracket legs only): `s = min((W − L − 2φ)/(d + κ(2 − d)), (T − W + 2φ)/(u − κ(2 + u)), W/(1 + κ))`, so that
  a win reaches T net of costs and a loss lands at the floor before gaps.

**Every stake is then cut**, in this order:
1. **at-risk:** `s·(d + κ(2 − d)) ≤ W − L`, before gaps;
2. **grey cap:** `s ≤ cap·equity − exposure`;
3. **no leverage:** `s ≤ W/(1 + κ)`;
4. **whole units:** `floor(s / price)` units, or fractional units where `venues.yaml` allows them.

A stake below the venue minimum means **no bet**. It is never rounded up.

**Refused in this version, with named reasons:**
- a leg whose class is `credit_buy` or `retail_short`, or whose leverage is above 1: `UNSUPPORTED_LEVERAGE_OR_SHORT`.
  It is never silently cut to 1x;
- multi-leg plans: `MULTI_LEG_UNSUPPORTED`;
- unset limits: `LIMITS_UNSET`;
- an unsigned calendar for a KRX or US leg: `CALENDAR_UNSIGNED`.

### 7.2 The no-edge null and edge sources (`models.py`)

**One definition of no edge.** At every point where the simulator can act (each session's open and close), the
expected next price relative to the current one is exactly 1 given the past. It is a conditional martingale, not just a
zero average. Costs then make every trade's expectation negative.

The review found two traps:
- **Zero log drift is not zero edge.** The repo's `drift="zero"` gives an edge of about σ²/2 per day.
- **Per-row demeaning of a block bootstrap is not a martingale.** Inside a block, the next row is the historical
  continuation, so a stop or timing rule can harvest past serial patterns.

The two models below are martingales by construction.

- **`SignFlipBootstrap`** (bootstrap legs):
  - **Two half-steps per session.** Each session splits into an overnight half-step, a = ln(open/prev close), and an
    intraday half-step, b = ln(close/open), both computed from the leg's **KRW** price series. For US legs that means
    price × KRW=X, aligned to the KST date of the US close; for OKX legs, Binance BTCUSDT × Upbit KRW-USDT.
  - **Random signs.** Each half-step gets its own random sign ε = ±1 and factor exp(ε·x)/k(x). k is solved per row, so
    that ½[clip(e^{x}/k) + clip(e^{−x}/k)] = 1 exactly after clipping to the dated KRX price limit (no clipping for
    crypto or the US). A row with no solution is dropped from the pool and counted.
  - **Blocks.** Rows are drawn in stationary-bootstrap blocks with mean length max(pw_block(r), pw_block(r²)), so
    volatility clustering survives through the move sizes. The signs are independent, so no historical sign pattern
    survives.
  - **Price checks.** Stops and take-profits are checked at the open and at the close only. A check that finds the
    price beyond the level fills at that price, so overnight gaps go through stops. Optional stopping then holds
    exactly.
  - **Intraday highs and lows are not modelled**, because honest intraday extremes would break the martingale. The card
    says so: `CHECKS_AT_OPEN_CLOSE`.
- **`GarchT`** (`core.quant.garch.fit_garch`, then `simulate_returns(fit, rate_daily=0.0)`): close-to-close only, a
  conditional martingale after the exact convexity correction. Stops are checked at the close only
  (`CLOSE_ONLY_CHECKS`). KRX legs clip to the dated limit, and the same per-step normalisation keeps E = 1.
- **Brackets** are evaluated pathwise on the leg's simulated prices: take-profit +u, stop −d, at the check points above.
  There is no separate p₀ formula. On a martingale, a bracket's mean payoff before costs is exactly 0, and gaps change
  the win rate, not the edge.
- **Cash** between trades is held in KRW (US trades convert each time, and the conversion spread is charged), so idle
  cash carries no FX drift.

**Edge sources**
- **`none`** is the default and is always the headline.
- **`assumed`**: a typed win rate p for a bracket leg. The simulator replaces the martingale with a tilted law under
  which that bracket wins with probability p. It is shown only in its own column (section 7.5).
- **`validated:<ref>`** (D13):
  - (a) `chain:<card_id>.r<rev>@<results_md5>`, resolved through `cards.read_chain(config.macro_dir()/"cards"/"verdicts.jsonl", ...)`.
    This is structurally unavailable today, because the macro card schema has no out-of-sample return field.
  - (b) `modelcard:<path>@<results_md5>`, for a committed `validate.ModelCard` JSON with `decision: PASS`. TRADEGEN
    re-creates its walk-forward run: same rules, grid, seed and data window. It requires the re-run statistics to
    match the card (out-of-sample Sharpe within ±0.02, the same `results_md5` for `results_file`), and that the file is
    tracked and unchanged in git.
    - The edge is the re-run out-of-sample daily P&L, resampled. Its mean is multiplied by
      `gate_stats.LIVE_SHARPE_MULTIPLIER`.
    - Only the extra costs a small account pays above the card's 10 bp are added: rounding to whole units and the
      venue minimum.
    - The only candidate today is `S_C3_crypto_trend_krwbtc`: KRW-BTC, out-of-sample Sharpe 1.22, 90% CI
      [0.62, 1.77], 2× costs 1.17, max drawdown −49%, created 2026-09-27.
  - Plain words: a backtest pass is not proof. Backtest edges often shrink or vanish in live trading, so this column is
    the hopeful case.

**Data rules**
- Synthetic history is refused (`SYNTHETIC_REFUSED`). A provisional intraday last bar is dropped.
- OKX legs carry `PROXY_DATA`, because the prices come from Binance.
- Single-coin and single-name legs add a delisting stress column (`tf_books.DELIST_STRESS`, −30% / −100%), whose
  losses are booked in the cost ledger.
- Each series is hashed as md5 of canonical JSON {symbol, source, dates, open, close, adjustment, status}.

**Costs**
- The base is described in section 4. The extras in `venues.yaml` are:
  - the KIS KRW-USD conversion spread;
  - the US minimum commission;
  - Upbit and OKX fees, as max(table, fee);
  - the Upbit → OKX withdrawal fee.
- Entry and exit are charged on every trade, and the sell tax is never charged twice.
- Every plan runs at 1× and at `GATE["cost_stress"]` = 2× cost, and both results are printed.

**Minimum tickets and ticks** come from `venues.yaml`:
- KRX: 1 share, plus the KRX stock tick ladder;
- KIS US: whether fractional orders are allowed, and the minimum;
- Upbit: KRW 5,000;
- OKX: the minimum per pair, with its source.

A missing entry gives `NOT_TRADABLE`.

**Calendar**
- Steps are calendar days from `start`. A KRX or US leg moves on its market's sessions (`cal` injected); crypto moves
  every day.
- The card prints the session count.
- A rule date inside the horizon (6.3) forces an exit on that date.

### 7.3 Simulation (`simulate.py`)

- **Outcomes.** Each path ends in exactly one of four outcomes, and together they sum to n:
  - **REACHED:** liquidation value after exit costs and sell tax ≥ T (moonshot paths stop here);
  - **RUINED:** liquidation value ≤ L, recorded at the actual fill level, so overshoot below L is kept;
  - **STUCK:** too little left to place any order;
  - **RUNNING:** still trading at the horizon, valued at liquidation.
- **Daily loss limit.** It is checked at the same open and close points. A breach exits and stops trading for that day.
- **KRX limit-down.** A close at the limit-down price (dated `price_limit` and the tick ladder) cannot be exited. The
  exit carries to the next session at `LIMIT_DOWN_CARRY_COST_MULTIPLIER` (2×) cost.
- **Seeds and streams:**
  - **Market seed:** sha256(data hashes ‖ comparison id ‖ run counter), shared by **every plan in one comparison**
    (common random numbers). Cosmetic fields are excluded.
  - **Streams:** `SeedSequence(seed_int, spawn_key=(chunk, stream_id))`, with seed_int =
    int.from_bytes(sha256, "big"). The bootstrap index and sign streams are keyed by data set and chunk, the GARCH
    innovations by symbol. Every plan therefore sees the same market paths.
  - **The owner never chooses the seed.**
- **Scale.** `CHUNK = 200_000`, and n must be a multiple of CHUNK. Defaults: 1,000,000 paths for moonshot plans and
  200,000 for compounding plans. Provenance records the NumPy version and the bit generator (PCG64).
  - A standalone check ran 1,000,000 paths × 30 steps in about 0.4 s. A 200k chunk needs about 100 MB.

### 7.4 Exact references (`bold.py`)

- **`ceiling(W0, L_min, T)`** = (W₀ − L_min)/(T − L_min). L_min is the lowest equity one price check can produce given
  the stake rule:
  - L_min = L when the largest one-check loss of the stake cannot cross L;
  - otherwise L_min is the worst post-gap equity, at most 0 under limited liability, which gives W₀/T.
  - **The no-edge column always shows it and always runs the breach check.** Edge columns print "Without the edge
    assumed here, no plan can beat 1 in N" instead.
- **`structural_max(plan, cal)`:**
  - For a KRX or KONEX leg it is ∏(1 + dated limit-up) over the leg's sessions, a legal bound. When target/stake exceeds
    it, the card prints **"IMPOSSIBLE in this horizon: KRX's daily limit allows at most N× in these S sessions"** and no
    probability.
  - For unlimited venues the card prints "No simulated path can reach N× (a limit of this model, not of the market)".
- **`bracket_optimum(plan)`** (bracket legs): a dynamic programme V(w, k) over equity and price checks remaining.
  - **Law of the bracket:** the joint (outcome, duration) law of one bracket under the leg's model, including
    "unresolved at the horizon, exit at market", estimated by simulation.
  - **Boundary values:** V(w, 0) = 1{w ≥ T}. Stake 0 is always allowed, and STUCK and RUINED states are worth 0.
  - **A certified upper bound** for policies under that law: every w′ is rounded **up** to the next grid node (V is
    non-decreasing in w), and the stake set contains every stake the simulator can choose.
  - **Bold play** is evaluated on the same grid, by memoised recursion over the states it can reach.
  - **On the card:** "the highest chance any way of placing this bracket can give is X; staking boldly gives Y and loses
    your stake in Z% of months".
  - **Breach check:** a simulated P(target) above `bracket_optimum` is a breach.
- **`bold_even(x, p)`** is the exact even-money recursion, used only as a regression test (3).
- **Kelly context,** only in the validated column: "typical bets needed" = ln(T/W₀)/g, compared with the bets the month
  allows. It is not a probability.

### 7.5 The report (`report.py`)

Every owner-facing string is rendered from one reviewed **sentence catalogue** with numeric slots. That covers the
report, gate reasons, warnings, alerts and CLI text. Each plan card shows, in this order:

1. **The model:** "Model: <name>. Price checks at the open and the close only; intraday moves are not modelled."
2. **The typical result first:**
   - "The middle month ends with KRW M. In P% of months you end at or below your floor of KRW L."
   - "Averaged over all simulated months: KRW X (an average loss of KRW Y: fees and the securities transaction tax).
     That average includes the rare jackpots and is not what usually happens."
   - The mean is P(REACHED)·T plus the mean over the other paths, at liquidation value, with its standard error.
   - Edge columns may say "an average gain of KRW Y, only if the edge in this column is real".
   - A no-trade plan says "this plan places no trades".
3. **The headline pair:**
   - P(reach KRW 42,000,000 before income tax) and P(lose the stake) = P(RUINED) + P(STUCK), with the split
     underneath;
   - then the ladder (D4), measured on ending liquidation value.
4. **The plain sentence:** "In 1,000,000 made-up months (from a model in which nobody has an edge, not real history),
   this plan reached KRW 42,000,000 before income tax in 63, about 1 in 16,000 (counting noise alone: between 1 in
   12,000 and 1 in 21,000; other models give 1 in A to 1 in B; neither range covers the model being wrong). In 912,034
   (91.2%) it hit your loss limit, leaving about KRW L or less. In N it fell below the minimum order (effectively lost).
   In M it was still trading at the end."
5. **Tax:**
   - "If those gains came from US shares (or from crypto sold in 2027 or later, unless the tax is postponed again), about
     KRW 8.7M of income tax would be due the following May, leaving about KRW 33.3M (USD 23,800)."
   - Each leg carries a `tax_basis`: `krx_small_holder_exempt`, `overseas_22pct_over_2.5m` or `crypto_22pct_from_2027`.
   - An after-tax target is optional.
6. **The ceiling and base rates,** after the plan's own figures:
   - "No plan without a real edge can beat 1 in N (with your floor)."
   - "In every retail group studied, most traders lose: Kalshi takers lose about 32% of what they stake, 74–89% of EU
     CFD accounts lose money, and 62% of new Korean investors lost in 2020."
7. **Precision.**
   - Clopper–Pearson intervals throughout. For k > 0 they are two-sided 95%, shown both as percentages and as "1 in N".
     For example, 63 of 1,000,000 gives 0.0048–0.0081%.
   - For k = 0 the one-sided 95% upper bound is "below resolution: under about 3 in n".
   - The language guard refuses any rendered probability equal to zero (a regex on probability slots, not on text such
     as "P(+10%)").
8. **Model spread.**
   - The headline uses the primary model: the bootstrap for legs with open prices, otherwise GARCH-t.
   - The spread shows every eligible model and a parametric GARCH-t refit (B = 20; simulate from the fit, refit, all on
     common random numbers), as a range together with the lowest lower and highest upper Clopper–Pearson bound.
   - The bootstrap's sensitivity is shown at 0.5× and 2× block length. No figure outside the range is ever shown.
9. **Columns:**
   - **No edge**: always the headline, always with the ceiling and the breach check;
   - **If tested edge <card> is real**: `VALIDATED_EDGE` (D13);
   - **Using the win rate you typed**: `ASSUMED_EDGE`. Its fixed text: "These numbers are only as true as the win rate
     you typed (W%). Nothing in your records supports it. To tell W% from a coin flip you would need about N recorded
     bets. Without the edge you typed, no plan can beat 1 in M." The same column also shows P(lose the stake) and the
     typical result.
10. **Flags,** each with its catalogue sentence (section 10):
    - **`HIDDEN_EDGE`** (red):
      - D = mean over paths of (W_τ + C_τ − W₀), with τ = the first of REACHED, RUINED or the horizon. Both tracks stop
        at T for this test, and W_τ is the liquidation value at the actual fill.
      - It flags when |D| exceeds the empirical-Bernstein bound √(2V·ln(4/δ)/n) + 7R·ln(4/δ)/(3(n − 1)), with
        R = (T + max overshoot) − L_min and δ = 1e-4.
      - The card prints the smallest edge the test can detect.
      - It has two wordings: "makes money without any edge" and "loses more than its costs explain".
    - **`CEILING_BREACH`**: amber when the one-sided 95% Clopper–Pearson lower bound exceeds the ceiling or
      `bracket_optimum`; red when the one-sided (1 − 0.001/m) lower bound does, where m is the number of bound checks in
      the report (Bonferroni). It never fires on the point estimate alone.
    - `IMPOSSIBLE`, `BELOW_RESOLUTION`, `GREY_LEG`, `PROXY_DATA`, `CHECKS_AT_OPEN_CLOSE`, `CLOSE_ONLY_CHECKS`,
      `LIMIT_GAP`, `COST_DOMINATED`, `NOT_TRADABLE`, `STUCK_AT_START`, `RULE_CHANGE_IN_HORIZON`.
11. **"Not in these numbers":**
    - income tax on gains (estimated above, not simulated);
    - the won-dollar rate moving;
    - Upbit holding withdrawals after a KRW deposit, and the Upbit-to-OKX route being closed without notice;
    - an exchange freezing withdrawals or failing;
    - a coin being delisted or flagged by Upbit (the history only contains coins that still trade);
    - KRX trading halts, VI auctions and caution, warning or risk designations;
    - buy orders not filling at limit-up, and sells not filling at limit-down, beyond what is modelled;
    - a broker refusing an order;
    - a hacked or locked account;
    - rule changes.

    "Most of these make the real result worse; none of them makes a no-edge plan better."
12. **Footer:** "These numbers describe rules you wrote, run in a model. They are not advice, and TRADEGEN does not
    recommend any plan. A higher chance of reaching the target does not make a plan better."

**Comparing plans honestly**
- There is no ranking by P(target). Plans are listed in creation order, or by smallest average loss.
- The moonshot table carries a fixed caption: "With no real edge, the plan with the highest chance of the target is
  always the one that bets the most, soonest, and it is also the one that loses your stake most often. Higher here means
  riskier, not better."
- The comparison prints: "You compared K plans (and tried J typed win rates) in this session. The highest-looking
  figure is the luckiest of K and is probably too high."
- Before arming (execution spec), the plan is re-run on a fresh market seed and that confirmation figure is shown.

**Language guard**
- Owner-facing text outside the catalogue fails the self-check.
- Rendered text fails on whole-word matches of: best, optimal, recommended, safe, guaranteed, sure, ideal, risk-free,
  low-risk, proven, "should", "worth trying", "good chance", "likely to reach".
- Korean entries (최적, 최선, 추천, 안전, 보장, 확실) are added once a Korean UI exists.
- Internal names such as `bracket_optimum` never appear in rendered text.

**Provenance** recorded with every report:
- the rules, instrument and venue hashes, and the owner-log head;
- the data hashes, model, seeds, n, CHUNK, NumPy version and bit generator;
- the edge sources;
- `repo_anchor()` and `tree_hash()`.

---

## 8. Testing

**Setup.** Two new suites are registered in `tests/run_all.py`: `compliance` (`tests/compliance_acceptance.py`) and
`odds` (`tests/odds_acceptance.py`). Every test runs inside `tests.macro_acceptance.hermetic()`, so the network raises,
with `TRADEGEN_HOME` set to a temp dir and price data from in-memory fixtures only. They are built test-first.

**compliance**
1. **Loading the table:**
   - schema and vocabulary are valid;
   - duplicate keys, anchors, native dates, oversized files and an `any` on an allow row each make the table INVALID;
   - ids are unique;
   - every row is sourced;
   - the 31-day cadence and the `known_changes` rule hold;
   - all 38 matrix rows are covered;
   - every research pointer resolves;
   - an unapproved hash is INVALID.
2. **Hard blocks:**
   - one test per conduct class and tag, on every venue id;
   - the hard-coded floor still blocks when the table rows are deleted;
   - a randomised property test: any blocked attribute gives BLOCK.
3. **Classification:**
   - TQQQ labelled `us_etf_1x` gives BLOCK (class mismatch);
   - 252670 labelled `krx_etf_1x` gives BLOCK;
   - a US single-stock −1x product needs the KRW 30M cash gate;
   - IBIT gives BLOCK (`us_crypto_etp`);
   - an unknown symbol gives BLOCK.
4. **Fail-closed inputs:**
   - NaN or infinite numbers, negative notional, wrong types, unknown ids, case variants, unknown tags, and an
     inconsistent kind/instrument/destination each give BLOCK;
   - fuzzed garbage never raises;
   - `RulesTable.invalid` gives BLOCK;
   - a table whose rows were mutated in memory under its old hash gives BLOCK.
5. **Gated rows:**
   - each missing flag gives BLOCK naming that flag;
   - a deposit or cash snapshot older than 7 days gives BLOCK;
   - credit on a designated warning or risk stock, or with an unknown designation, gives BLOCK.
6. **OKX:**
   - no acknowledgement gives ACK_REQUIRED;
   - an acknowledgement with a wrong `warning_sha256`, or from an old session, gives ACK_REQUIRED;
   - an unset cap, exposure over the cap, a missing age record, or a date ≥ 2026-12-03 gives BLOCK for a buy;
   - a reduce-only sell on 2026-12-03 gives ALLOW_EXIT, and a withdrawal OKX → Upbit at a registered
     address gives ALLOW_EXIT;
   - an unregistered address gives BLOCK;
   - Asia/Seoul boundaries: 2026-12-02T23:59:59+09:00 gives ALLOW (buy); 2026-12-03T00:00:00+09:00 gives BLOCK (buy).
7. **Staleness and alerts:**
   - a date after `review_by` blocks new exposure but not exits;
   - the due thresholds still fire after a missed run;
   - CLI exit codes 0, 1, 2 and 3;
   - the toast and the `--log` writer work with fake channels;
   - a failed channel is announced on the others;
   - the alert text contains no rule free text.
8. **Purity and permits:**
   - during `decide()`, `builtins.open`, `socket.socket.connect` and `time.time` are patched to raise, and the gate
     module's `date`/`datetime` names are swapped for raising subclasses;
   - an AST scan of `gate.py` finds no wall-clock call;
   - identical inputs give an identical `decision_id`;
   - `verify_permit` refuses a forged Permit, a different intent, a different session, a different date, and a
     context where the cap was lowered since issue.
9. **Owner log:**
   - editing the last line is detected;
   - truncation below a recorded head is detected;
   - piped stdin is refused by the confirmation API;
   - a loosening is deferred to the next Asia/Seoul date and refused after a halt;
   - every path stays under `~/.tradegen` (`refuse_quantgen`).

**odds**
1. **The martingale null:**
   - every sign-flip factor has mean exactly 1 per row (to 1e-12), including after KRX clipping;
   - under each model, a fixed −d stop, a +u/−d bracket and a buy-and-hold each have a mean payoff of 0 before costs,
     within simulation error;
   - a regression test shows the repo's `drift="zero"` and per-row demeaning both fail this.
2. **HIDDEN_EDGE:**
   - its false-alarm rate on true martingales with λ = n·P(target) in {1, 2, 10, 50} stays at or below δ;
   - a planted edge of twice the printed detectable size is flagged.
3. **Exact values:**
   - `bold_even` gives 0.1000%, 0.0816%, 0.0346% and 0.0106%, and 0.0400% with L at half the stake;
   - `bracket_optimum` ≥ the bold policy, and equals it for fee-free even money;
   - the simulated bold policy matches its exact value within the Clopper–Pearson interval;
   - the ceiling is not breached by randomised no-edge plans at the Bonferroni-corrected level.
4. **Mechanics:**
   - IMPOSSIBLE for a KRX-only 1,000× plan, and the session-dependent N (112× to 321×);
   - gap-through fills at the open;
   - limit-down carry at 2× cost, checked against `orders.LIMIT_DOWN_CARRY_COST_MULTIPLIER`;
   - STUCK_AT_START when a share costs more than the stake;
   - outcomes sum to n;
   - session counts on the fixture calendar;
   - forced exit at a rule date inside the horizon;
   - REACHED measured after exit costs and sell tax.
5. **Refusals:** `CALENDAR_UNSIGNED` on the shipped calendar set, plus `LIMITS_UNSET`, `MULTI_LEG_UNSUPPORTED`,
   `UNSUPPORTED_LEVERAGE_OR_SHORT`, `SYNTHETIC_REFUSED` and `NOT_TRADABLE`.
6. **Seeds:**
   - two plans in one comparison consume identical bootstrap indices, signs and innovations;
   - renaming a plan does not change its numbers;
   - n not a multiple of CHUNK is refused.
7. **Costs:**
   - extras may only raise costs;
   - the 1× and 2× runs are both present;
   - the sell tax is never charged twice;
   - a stake below the minimum means no bet.
8. **Edge:**
   - Kelly stakes 0 without a validated edge;
   - a fixture ModelCard whose re-run statistics do not match is refused, and one that matches resolves;
   - an assumed edge never reaches the headline, and its column always prints the "without the edge you typed" ceiling.
9. **Report and language guard:**
   - the typical result comes before the average;
   - the tax line, the base rates and the footer are present;
   - the "not in these numbers" box is present;
   - no zero probability is rendered;
   - no banned word appears anywhere in the catalogue or in rendered output;
   - the K note and the moonshot caption are present.

**Existing guards stay in force:**
- `tests/acceptance.py` test_08 and test_09, and T-RO-01 (the static scan and the orders-import rule) cover both
  packages;
- T-RO-02, the KIS allowlist, is unaffected;
- T-CTX-01 covers both packages once its prefixes are extended (section 4).

## 9. Error handling

- **Gate:**
  - it never raises; any internal error is BLOCK;
  - an invalid or unapproved table, instrument map or venue table is BLOCK for new exposure, CLI exit 3, and the alert
    fires;
  - a broken owner chain means owner state counts as absent, and the alert fires;
  - `verify_permit` refuses on any mismatch.
- **Odds (refuses rather than guesses).** It gives a named reason, never a number: `UNSCREENED`, `BLOCKED_LEG`,
  `CALENDAR_UNSIGNED`, `LIMITS_UNSET`, `SYNTHETIC_REFUSED`, `NOT_TRADABLE`, `MULTI_LEG_UNSUPPORTED`,
  `UNSUPPORTED_LEVERAGE_OR_SHORT`, `CARD_NOT_REPRODUCED`.
  - A model that fails to fit is left out of the spread with a note. If every model fails, the plan is refused.
  - A refused run never prints a probability.
- **Alerts:** a failure of the check itself is alerted on every working channel.
- **Paths:** everything is written under `~/.tradegen`, and every writer calls `refuse_quantgen`.

## 10. The guardrails, in plain language

| Guardrail | What it protects you from | What you see | Who may change it |
|---|---|---|---|
| No-edge null | A model that quietly "makes money" with no edge | Nothing; it is the default | No one; only a tested edge adds a separate column |
| HIDDEN_EDGE | A bug that hands a plan free money, or one that loses more than its costs | Red: "On average this model makes money without any edge" or "...loses more than its costs explain", "so do not use these numbers" | No one |
| Ceiling | Believing a no-edge plan can beat 1 in 1,000 (1 in 2,000 with a floor at half the stake) | "No plan without a real edge can beat 1 in N." | It is maths |
| CEILING_BREACH | Numbers that are impossible under no edge | Amber "at the ceiling within simulation noise; rerun with more paths", or red "do not use these numbers" | No one |
| IMPOSSIBLE | Chasing a target the market cannot reach in time | "KRX's daily limit allows at most N× in these S sessions" (112× to 321× in 30 days) | It is a market fact for KRX; for other venues the card says it is a limit of the model |
| Typical result first | Mistaking the average (jackpots included) for what usually happens | "The middle month ends with KRW M…" | No one |
| Simulation precision | Mistaking counting noise for your real odds | "Counting noise alone: between 1 in A and 1 in B" | More paths narrow it |
| Model spread | Trusting one model of the market | "Other models give 1 in A to 1 in B" | Adding models is allowed; removing one is not |
| Checks at open and close | Thinking stops fire at intraday lows | "Price checks at the open and the close only" | A future intraday model needs its own martingale test |
| 2× costs | Costs eating the edge | A second column at double costs | No one |
| Minimum tickets / STUCK | A plan that cannot trade its size | "Can't open" / "left below the minimum order (effectively lost)" | The owner, through the approved venue table |
| LIMIT_GAP | Assuming a stop always fills at its level | The worst overshoot below your floor | It is how markets gap |
| Typed win rate | A guessed edge dressed up as odds | "Only as true as the win rate you typed… Without the edge you typed, no plan can beat 1 in M" | The owner types it; it never reaches the headline |
| Tested edge | Trusting a backtest too much | "This column trusts strategy card <id>… Read it as the hopeful case" | Only a re-verified PASS card (D13) |
| Winner's curse | Picking the luckiest of many plans | "You compared K plans…", plus a fresh-seed confirmation | No one |
| Stale rules | Trading on a rule that may have changed | New exposure blocked, plus alerts on every channel; exits stay open (D11) | The owner, by approving a re-reviewed table |
| Grey cap, acknowledgement and auto-off | Unbounded OKX exposure, and trading OKX after 2026-12-03 | ACK_REQUIRED or BLOCK on OKX buys; the warning text you acknowledge | The owner, through the console (D12: loosening waits a day) |
| GREY_LEG | Forgetting OKX's legal status | "This part uses OKX, a venue Korean law has not settled; your money there can be frozen." | — |
| PROXY_DATA | OKX prices taken from Binance | "OKX prices are stood in by Binance prices; real OKX fills may differ." | — |
| COST_DOMINATED | Costs driving the result | "Fees on each trade are larger than half a normal day's move; costs, not the market, drive this result." | — |
| Language guard | Report text that sounds like advice | Nothing (the build fails instead) | The catalogue is reviewed |

## 11. Owner inputs and open legal points

**Owner acts.** Each goes through the console confirmation (D14). Claude never performs them.
- Approve the rules table, the instrument map and the venue table, every month.
- **Sign the calendar files** `holidays_KRX.yaml`, `kr_sessions.yaml`, `holidays_NYSE.yaml` and `kr_regime_tags.yaml`
  before any KRX or US plan can be simulated. Claude may prepare a verification of them against KRX and NYSE sources.
- Set `total_loss_floor_krw` and `daily_loss_krw` (D3). Until then the odds engine refuses.
- Set `okx_equity_share`. While it is unset, OKX is blocked.
- Record `age_of_majority`, and any course completions, deposit or cash snapshots and broker approvals.
- Register withdrawal addresses.

**Open legal points for Korean counsel** (the report's "Further review recommended", all 8):
- Are Kalshi event contracts gambling, or overseas derivatives under FSCMA Art. 184①?
- Does building this tool reach Criminal Act Art. 247 or National Sports Promotion Act Art. 26②? This bears on the
  research-only GrokBot copy.
- What is the user-side status of DEX perps and unregistered exchanges after 2026-12-03 and about 2027-02-18?
- Does VAUPA Art. 10 reach overseas venues and DEXs?
- Which FX reports apply to crypto moved to USD platforms?
- Does sharing outputs need advisory registration? (Forbidden here by KR-CONDUCT-SIGNALS.)
- Do Bybit's and Binance's terms restrict Korea, and **will Upbit and Bithumb keep allowing same-name transfers to
  offshore venues?** This question gates D6's funding route.
- What will the November–December 2026 votes decide: the crypto tax, the Digital Asset Basic Act and the single-stock
  leverage cap?

## 12. Risks

- **The table goes out of date.** Mitigations: a monthly cadence, known-change dates, fail-closed review dates, and the
  all-channel alert.
- **Monthly approvals become a chore and get rubber-stamped.** Mitigation: the check lists exactly which rows changed
  and which sources were re-read.
- **The owner reads simulated odds as forecasts.** Mitigations: model-not-history wording, the typical result first, the
  precision and spread lines, base rates, and the language guard.
- **A typed win rate tempts the owner.** Mitigations: its own column, the bets-needed figure, the "without the edge"
  ceiling, base rates.
- **A backtest edge is trusted too much.** Mitigations: the re-verification under D13, the live multiplier, the
  lower-bound Kelly, the hopeful-case wording.
- **Claude or a script changes owner state.** Mitigations: the console confirmation (D14), approvals by hash rather than
  by commit, head anchoring.
- **A grey venue tightens suddenly.** Mitigations: auto-off, the acknowledgement, the cap, exits kept open (D11).
- **The alerts depend on the PC being on.** Mitigation: the check runs at every app start, plus the in-app banner.

## 13. Out of scope (later specs)

- **Execution:** adapters, arming and sessions, single-use permits, the audit log, the halt record, `client_order_id`.
- **Strategies:** strategy research (with `anthropic-skills:deep-research`); multi-leg, leveraged and short plans.
- **UI:** with design-system and design-critique.
- **Compliance check:** `legal:compliance-check` per venue before any real-money feature ships.
- **Deferred technique:** importance sampling, to add when a plan needs precision below about 1e-5; an intraday
  price-path model, to add if open/close checks prove misleading; an OKX candle loader, to add if the Binance proxy
  proves misleading.

---

## Appendix A: the pre-spec review that shaped section 7 (rev 1)

Three critics (statistics, honesty, repo fit) reviewed the first odds-engine draft. Their must-fix items became rev 1:

- zero arithmetic drift;
- the structural maximum and IMPOSSIBLE;
- the floor in the ceiling;
- the exact optimum;
- noise-aware flags;
- "simulation precision";
- gap-through fills and limit-down carry;
- the four-way outcome partition;
- lower-bound Kelly;
- the refusals for synthetic and unloadable data;
- cost and minimum-ticket tables;
- the calendar;
- no ranking;
- the winner's curse;
- survivorship.

Round 1 then found that several of those fixes were still incomplete; Appendix B rules on each.

## Appendix B: round 1 rulings

Gemini's findings are G-n (Major) and Gm-n (Minor). Claude-workflow findings carry their dimension's prefix: L legal,
S statistics, F honesty (H-F below), I implementability, Z safety, plus each dimension's "missed" items.

| Finding | Ruling | Where |
|---|---|---|
| G-1, L5: US spot-crypto ETFs pass as us_etf_1x | Accepted | `us_crypto_etp`, KR-KIS-US-CRYPTO-ETP, KR-KIS-CRYPTO-DERIV, floor |
| G-2, L7: Hyperliquid/Drift outcome markets; gopax; sportsbooks; Speed-On; offer-with-warning conditions | Accepted (D10 records the stricter choice) | 5.2, 5.3 |
| G-3, L2, L9: single-stock overseas/inverse; cash-only 30M; derivative stages; short and lending requirements; credit designations; course hours as minimums | Accepted | 5.2, 5.3 |
| L6: hard-block KRX derivatives as recourse leverage | Rejected (the report gates them) | — |
| G-4, Z8, L3: no OKX → Upbit path; kind/instrument mismatch; name match below KRW 1M | Accepted | KR-OKX-WITHDRAW, 6.2 steps 1 and 5, registered addresses |
| G-5, L4, L10: BitMart attribution; travel-rule date resolved; monthly cadence; wrong reasons and confidences | Accepted | 5.1, 5.3 |
| G-5 effective_from blocks historical backtests | Rejected: the gate rules on live decisions as of today; rows now carry regime-start dates | 5.1 |
| L1: referral links; copy-trading as lead; 환치기 | Accepted | KR-CONDUCT-PROMOTE, -OTHERS, -FX |
| L8: three missing further-review questions; per-transfer acknowledgement | Accepted | 11, 6.2 step 5 |
| G-6, S1, S-missed-2: bootstrap demeaning contradictory and not a martingale; no high; intraday extremes unfair | Accepted; redesigned as `SignFlipBootstrap` with open/close checks | 7.2 |
| G-7, S3: FX covariance; KRX carry drift | Accepted: KRW series before sign-flipping; carry inside a martingale | 7.2 |
| G-8: ceiling invalid under gap-through | Accepted: L_min | 7.4 |
| G-9, S2, S6, S7: BetLeg inconsistent; bold stake undefined; optimum not an upper bound | Accepted: pathwise brackets, stake algebra, certified dynamic programme | 7.1, 7.2, 7.4 |
| G-10, I-missed-3: multi-leg weights and calendars | Resolved by scope: one leg in this version | 1, 7.1 |
| G-11, S4, H-F7, S-missed-1: average-first line misleading | Accepted: typical result first | 3, 7.5 |
| S5: HIDDEN_EDGE 4-SE test invalid with jackpots | Accepted: empirical-Bernstein | 7.5 |
| S8, I5: seeds contradict common random numbers | Accepted | 7.3 |
| S9: structural_max for unlimited venues | Accepted | 7.4 |
| S10: Bonferroni; precision example; parameter bootstrap | Accepted | 7.5 |
| G-12, I1: orders import breaks T-RO-01 | Accepted: local constant, equality test | 4 |
| G-13, I4: calendars unsigned | Accepted: CALENDAR_UNSIGNED; owner signs | 4, 9, 11 |
| G-14, I3: History has closes only | Accepted: `core/odds/bars.py` | 4 |
| G-15, I2: cost_per_side misuse; check_cost_policy wrong | Accepted | 4, 7.2 |
| G-16: KRX stock tick table missing | Accepted: tick ladder in venues.yaml | 4, 7.2 |
| G-17, I6: card registries; PASS cards exist | Accepted; D13 (owner chose the re-verified hopeful column) | 2, 7.2 |
| G-18, Z6, L-missed-2: exits blocked after auto-off/staleness | Accepted; D11 (owner chose exits open) | 2, 6.2 step 3 |
| G-19, Z4: owner log last-line edits, rollback, stdin piping | Accepted: row hash, head anchoring, console confirmation (D14) | 6.4 |
| G-20, I-missed-1: unset limits | Accepted: LIMITS_UNSET | 6.4, 9 |
| Gm-1 to Gm-5: seed API, git provenance, email recipient, writers, permit expiry | Accepted | 4, 5.4, 6.3, 7.3 |
| Z1: forgeable Permit | Accepted: permit(intent, ctx), verify_permit | 6.3 |
| Z2: NaN and unvalidated Context | Accepted | 6.2 step 1 |
| Z3: YAML loader holes; hard-coded floor | Accepted | 5.1 |
| Z5, L-missed-3, H-F6: acknowledgement not bound to warning text | Accepted: `warning:` field, render_warning, hash check | 5.1, 6.2 |
| Z7: date semantics | Accepted: Asia/Seoul calendar date | 6.1 |
| Z9: missing table mechanism | Accepted: RulesTable.invalid | 4, 9 |
| Z10, I7: alerts split; exact-day triggers | Accepted | 5.4 |
| Z-missed-1: limits loosened mid-streak | Accepted; D12 (owner chose tighten now, loosen next day) | 6.4 |
| Z-missed-2, H-F1: approval by commit is not owner approval | Accepted: approvals by hash in the owner log | 5.1 |
| H-F2: income tax; H-F5: the "not in these numbers" box | Accepted | 7.5 |
| H-F3: leverage silently cut to 1x | Accepted: UNSUPPORTED_LEVERAGE_OR_SHORT | 7.1 |
| H-F4, H-missed-1: typed win rate; ceiling dropped for the whole plan | Accepted: the ceiling is keyed per column | 7.4, 7.5 |
| H-missed-2: base rates | Accepted | 3, 7.5 |
| H-F8: language guard self-contradictory | Accepted: sentence catalogue, rewording, probability-slot regex | 7.5 |
| H-F9, H-F10: plain-sentence fixes; section 10 completeness | Accepted | 7.5, 10 |
| I8: dataclass field order; YAML dates | Accepted: kw_only; quoted dates | 6.1, 7.1, 5.1 |
| I9: purity test technique; hermetic wrapper | Accepted | 8 |
| I10: guard names; T-CTX-01 prefixes; naming traps | Accepted | 4, 8 |
| H-missed-4: the realistic-odds line | Accepted | 3 |
