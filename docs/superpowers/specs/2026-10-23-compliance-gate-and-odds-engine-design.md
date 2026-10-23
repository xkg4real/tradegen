# TRADEGEN compliance gate and odds engine

Date: 2026-10-23.

Status:
- **Revision 1**, drafted after the owner approved design sections 1 to 5 in brainstorming on 2026-10-23.
- Next: an adversarial multi-agent review and a Gemini (Antigravity) debate.
- Implementation will be planned as two plans, compliance first and then odds, because odds depends on
  `screen()`.
- A GPT (Codex) referee round follows once the Codex quota resets on 2026-10-27 19:16.
- After that comes the owner's review of this written spec, and only then the implementation plan.

Inputs:
- `reports/Korean resident trading venue legality.md`, with its notes in `research_notes/Korean resident trading venue legality/`;
- `research_notes/QUANTGEN TRADEGEN split map/split_map.md`;
- the Phase A isolation (commit `d47cea9`).

> This is research and software design, not legal, tax or investment advice. Neither TRADEGEN nor its author is a
> licensed advisor. Before any real-money feature ships, the open legal points in section 11 need Korean-qualified
> counsel.

---

## 1. Purpose and scope

TRADEGEN is a personal trading program for one Korean-resident individual. The owner trades their own money: a
starting stake of about KRW 42,000 (USD 30). It runs two tracks:
- a **moonshot** track aimed at USD 30,000, about 1,000 times the stake;
- a realistic **compounding** track.

This spec covers the first two building blocks:
1. **The compliance gate** (`core/compliance/`). It decides whether a venue, instrument, order, transfer or plan is
   allowed for this owner under Korean law, as researched. Unknown or stale cases are refused.
2. **The odds engine** (`core/odds/`). It shows the honest chance of each outcome for any plan the gate allows: the
   chance of reaching the target, the chance of losing the stake, and the full outcome ladder.

**Neither package can place an order.** Execution, strategy research and the UI each get their own spec later. Those
specs are built on the two interfaces defined here: `decide()` and its permit, and `OddsReport`.

## 2. Owner decisions (fixed inputs)

| # | Decision | Source |
|---|---|---|
| D1 | Build order: compliance gate and odds engine first (no money moves), then execution, then strategies and the UI | brainstorming 2026-10-23 |
| D2 | Accounts: KIS stock account; Upbit (opened 2026-10-23), the lawful KRW-spot crypto venue; OKX (overseas exchange) | brainstorming |
| D3 | Ruin = equity reaching the owner's hard total-loss limit. Execution halts for good at the same number. The odds engine and the kill switch read one shared setting | brainstorming |
| D4 | The compounding track reports an outcome ladder: P(+10%), P(+25%), P(2x), P(10x), P(USD 30k), median and 5th-percentile ending equity, and P(lose the stake). It has no single target | brainstorming |
| D5 | A rules row past its review-by date fails closed: every venue it covers is blocked until the row is re-reviewed. The owner is alerted on every channel: an iOS push through the Claude app, an email to their own address, and a Windows notification | brainstorming |
| D6 | OKX spot is grey. It is off by default. Each armed session needs an acknowledgement of a warning, and OKX exposure is hard-capped at a share of total equity that the owner sets. It turns itself off on 2026-12-03 until re-reviewed. OKX derivatives and P2P are hard-blocked | brainstorming |
| D7 | Every plan shows P(reaching USD 30k) and P(losing the stake). Bold play is the reference. Section 7.4 refines this: bold play is shown for bet legs, beside the exact optimum and the ceiling | parent brief |
| D8 | Execution: KIS and exchange APIs are disarmed by default and armed per session by the owner only, with hard daily and total loss limits, a kill switch and an order audit log. The owner adds trading-scope keys | parent brief; execution spec |
| D9 | Approach A: rules as data, a pure `decide()` kernel, and a plan simulator | brainstorming |

## 3. The honest numbers, up front

These numbers frame every report. They were checked by direct computation on 2026-10-23.

- **The ceiling.** Suppose every bet has zero or negative expected value after costs, and losses stop at the account
  balance. Then wealth is a non-negative supermartingale, and P(ever reaching T) ≤ W₀/T for every strategy, by optional
  stopping. For KRW 42,000 → KRW 42,000,000 that is **0.1% (1 in 1,000)**.
- **The ceiling with a loss floor.** If equity is absorbed at the owner's floor L, and no single step can gap below it,
  the bound tightens to (W₀ − L)/(T − L). With L = KRW 21,000 (half the stake) that is **0.050%**.
- **Bold play** (Dubins–Savage) is the most a subfair even-money game can give: stake min(W, T − W) each time.
  - Exact P(1,000×): **0.1000%** at p = 0.50, **0.0816%** at 0.49, **0.0346%** at 0.45, **0.0106%** at 0.40.
  - With the floor at half the stake, it is 0.0400% at p = 0.49.
  - It loses the stake in more than 99.9% of months.
- **KRX cannot do it in a month.**
  - The ±30% daily price limit caps one KRX position at 1.3ⁿ over n sessions: **1.3²¹ ≈ 247×** in 21 sessions.
  - A 1,000× month from 1x KRX shares or ETFs is therefore **impossible**, not merely unlikely.
  - One even-money doubling needs three limit-up sessions, because 1.3² < 2.
- **Kelly** maximises long-run growth, not the chance of hitting a target by a deadline.
  - With zero edge, Kelly bets nothing.
  - Even a genuine 52.5% even-money edge needs about **5,524 bets** to grow 1,000× at full Kelly.
- **Monte Carlo precision.** Estimating a 0.01% event to ±10% (relative standard error) needs about 1,000,000
  simulated months. Estimating a 0.1% event to the same precision needs about 100,000.

Realistic odds of USD 30 → USD 30,000 within a month are **0.01% or less**. The expected result is losing most of the
stake. No report may promise otherwise.

---

## 4. Architecture

Two new packages follow the repo's `core/<domain>` pattern. Neither contains an order path.

```
core/compliance/
  kr_rules.yaml      the rules table (data; one row per venue x instrument class, plus conduct rows)
  rules.py           load + schema check + version hash (sha256 of canonical JSON); staleness; CLI --check
  gate.py            decide(intent, ctx) -> Decision ; screen(plan, ctx) -> Screening      (pure)
  owner.py           owner flags, session acknowledgements, caps: append-only, hash-chained log
  alerts.py          due(rows, today) (pure) + the alert fan-out (iOS push, email, Windows toast)

core/odds/
  plan.py            Plan, Leg, Sizing, Limits (dataclasses; validation)
  venues.yaml        owner-signed venue facts: lot sizes, minimum orders, extra fees, sources
  models.py          return models under one no-edge null: StationaryBootstrap, GarchT, BetLeg; edge sources
  simulate.py        vectorised, chunked path simulator
  bold.py            exact references: ceiling, structural maximum, bold-play value, exact optimum for bet legs
  report.py          OddsReport, plain-language rendering, flags, banned-word self-check
```

**How data flows**
1. A `Plan` goes to `gate.screen(plan, ctx)`. If any leg is blocked, the plan is refused with reasons and is never
   simulated or compared.
2. A screened plan goes to `odds.simulate(plan, screening, ...)`, which refuses an unscreened plan.
3. The result is an `OddsReport`.

In the later specs:
- strategies produce Plans;
- execution calls `decide()` for every order and every transfer, and may proceed only with a `Permit` bound to that
  exact intent and date.

**Boundaries**
- `decide()` and `screen()` are pure: no files, no network, no clock. The date, the rules table, the owner flags and the
  session state are passed in.
- File access exists only in:
  - `rules.py`, which reads `kr_rules.yaml`;
  - `owner.py`;
  - `alerts.py`;
  - `odds.models`, which reads price history through the repo's cached loaders;
  - `venues.yaml`.
- Every mutable path goes through `config.state_path()` / `state_root()` (`~/.tradegen`), and every writer of
  persistent records calls `core.isolation.refuse_quantgen()`.
- The odds engine is deterministic for a given (plan, data hashes, seed).
- It does **not** reuse `core.quant.montecarlo.run_monte_carlo`, which caps n at 100,000, uses one RNG stream, keeps the
  full path matrix and returns only terminal prices. It reuses these pieces instead:
  - `core.quant.garch.fit_garch` / `simulate_returns(rate_daily=0.0)`;
  - `core.quant.gate_stats.pw_block` / `spawn_seeds`;
  - `core.quant.validate.cost_class`, `core.quant.instruments.cost_per_side` / `check_cost_policy`;
  - `core.calendars.clocks.is_session` / `sessions_between`;
  - `core.engine.orders.limit_prices` and `LIMIT_DOWN_CARRY_COST_MULTIPLIER`;
  - `core.quant.tf_books.DELIST_STRESS`;
  - `core.quant.cards.read_chain` / `verify_verdict_chain`;
  - `core.ficc.macro_artifacts.tree_hash`.

---

## 5. The rules table (`core/compliance/kr_rules.yaml`)

### 5.1 Row schema

```yaml
schema: tradegen.kr_rules/1
scope: Korean-resident individual, own funds only
rows:
  - id: KR-OKX-SPOT                      # unique; stable across reviews
    kind: venue                          # venue | conduct
    match: {venue: [okx], instrument: [crypto_spot]}
    treatment: grey                      # hard_block | gated | grey | allow | out_of_scope
    max_leverage: 1.0                    # venue rows: anything above is BLOCK
    requires: {}                         # gated rows: deposit_krw_min, courses, broker_approvals
    grey: {ack: per_session, cap_key: okx_equity_share, auto_off: 2026-12-03}
    reason: "Operator unregistered with the FIU; no user penalty found; transfers contested"
    basis: ["특금법 registration duty", "FSC release 2026-06-24", "FX Act No. 21714 (eff. 2026-12-03)"]
    sources: ["https://www.fsc.go.kr/no010101/87177"]
    research: "reports/Korean resident trading venue legality.md#compliance-matrix row 14"
    confidence: medium                   # high | medium | low (from the report)
    effective_from: 2026-06-24
    effective_until: null
    review_by: 2026-12-02                # at most 90 days after the latest review
    reviews:
      - {date: 2026-10-23, by: claude-research, checked: "legality report rows 13-15, 19; crypto notes section 3"}
```

**Rules for the table**
- Every row has at least one source and a pointer to the research it came from.
- `review_by` may be at most 90 days after the row's latest `reviews` entry.
- Every one of the 38 legality-matrix rows must be covered by at least one table row (tested).
- A change to any row is a git commit. Every `Decision` records the table's `rules_hash`.

### 5.2 Vocabulary

- **Venue ids:**
  - `kis`, `upbit`, `bithumb`, `coinone`, `korbit`, `okx`, `binance`, `bybit`, `bitget`, `hyperliquid`, `pumpfun`,
    `jupiter`, `uniswap`;
  - prediction markets: `polymarket`, `kalshi`, `limitless`, `myriad`, `opinion`, `predictfun`, `drift`;
  - other platforms: `robinhood`, `cryptocom`, `predictit`, `betman`, `lotto`, `ibkr`, `moomoo`, `webull`, `etoro`;
  - `offshore_fx_cfd`, and the state-blocked list (section 5.3).
  - Anything else is unknown, which means BLOCK.
- **Instrument classes:**
  - KRX: `krx_cash_share`, `konex_share`, `krx_etf_1x`, `krx_etn_1x`, `krx_inverse_1x`, `krx_lev_etp`,
    `single_stock_lev_etp`, `krx_derivative`, `elw`;
  - credit and margin: `credit_buy`, `retail_short`, `fx_margin`, `cfd`;
  - US: `us_stock`, `us_etf_1x`, `us_inverse_1x`, `us_lev_etp`, `us_option_long`, `us_option_write`;
  - overseas futures: `overseas_future`;
  - crypto: `crypto_spot`, `crypto_lending`, `crypto_derivative`, `crypto_p2p`;
  - transfers: `crypto_transfer` (kind `transfer`, with a `destination_venue`);
  - `event_contract`, `sports_bet`, `lottery`.

### 5.3 Seed rows

Each row carries the research and source fields from section 5.1. The legality report's "Recommended actions for a
trading-software designer" table sets each treatment.

| Row id | Match | Treatment | Matrix row | review_by |
|---|---|---|---|---|
| KR-KIS-KRX-SHARE | kis: krx_cash_share | allow (max 1x; ±30% limit; 0.20% sell tax, ETFs exempt) | 21 | 2027-01-21 |
| KR-KIS-KONEX | kis: konex_share | allow (±15% limit; 0.10% tax) | 21 | 2027-01-21 |
| KR-KIS-KRX-ETF1X | kis: krx_etf_1x, krx_etn_1x | allow | 21 | 2027-01-21 |
| KR-KIS-KRX-INV1X | kis: krx_inverse_1x | allow; confidence low. The deposit regime targets products above 1x; confirm with the broker | 22 | 2026-12-31 |
| KR-KIS-KRX-LEV | kis: krx_lev_etp | gated: deposit ≥ KRW 10M + `kofia_leveraged_1h` | 25 | 2026-12-31 |
| KR-KIS-SINGLE-LEV | kis: single_stock_lev_etp | gated: deposit ≥ KRW 30M + `single_stock_lev_3h` + `single_stock_mock_5h` | 26 | 2026-12-31 |
| KR-KIS-KRX-DERIV | kis: krx_derivative | gated: deposit ≥ KRW 10M (KRW 20M for writing / VKOSPI) + `krx_deriv_1h` + `krx_deriv_mock_3h` | 27 | 2026-12-31 |
| KR-KIS-ELW | kis: elw | gated: deposit ≥ KRW 15M + `elw_course` | 28 | 2026-12-31 |
| KR-KIS-CREDIT | kis: credit_buy | gated: `broker_credit_approval`; max 2.2x; per-session acknowledgement | 23 | 2026-12-31 |
| KR-KIS-SHORT | kis: retail_short | gated: `broker_short_approval`; per-session acknowledgement | 24 | 2026-12-31 |
| KR-KIS-US-STOCK | kis: us_stock, us_etf_1x | allow | 31 | 2027-01-21 |
| KR-KIS-US-INV1X | kis: us_inverse_1x | allow; confidence low (broker notices) | 33 | 2026-12-31 |
| KR-KIS-US-LEV | kis: us_lev_etp | gated: deposit ≥ KRW 10M + `kofia_leveraged_1h` (since 2026-05-22) | 32 | 2026-12-31 |
| KR-KIS-US-OPT-LONG | kis: us_option_long | gated: `us_option_course_1h` + `us_option_mock_3h`; per-session acknowledgement (commissions of 3-20% of the account per side) | 34 | 2026-12-31 |
| KR-KIS-US-OPT-WRITE | kis: us_option_write | hard_block (not offered; unlimited loss) | 34 | 2027-01-21 |
| KR-KIS-OVERSEAS-FUT | kis: overseas_future | hard_block (recourse leverage; losses can exceed the account) | 35 | 2027-01-21 |
| KR-KIS-FX-MARGIN | kis: fx_margin | hard_block (USD 10,000 per lot; recourse leverage) | 29 | 2027-01-21 |
| KR-KIS-CFD | kis: cfd | hard_block (professional investors only) | 30 | 2027-01-21 |
| KR-UPBIT-SPOT | upbit, bithumb, coinone, korbit: crypto_spot | allow (KRW 5,000 minimum on Upbit) | 10 | 2026-12-02 |
| KR-UPBIT-LENDING | upbit, bithumb, coinone, korbit: crypto_lending | gated: `daxa_lending_course`; per-session acknowledgement | 11 | 2026-12-02 |
| KR-DOMESTIC-CRYPTO-DERIV | upbit, bithumb, coinone, korbit: crypto_derivative | hard_block (no legal framework) | 12 | 2027-01-21 |
| KR-TRANSFER-OWN | upbit, bithumb, coinone, korbit: crypto_transfer | allow only to a `destination_venue` that is itself allowed or grey for this owner (6.2 step 4). A grey destination brings that row's acknowledgement and cap. The source exchange's travel-rule check enforces the name match; the gate requires on_behalf = self | 19 | 2026-12-02 |
| KR-OKX-SPOT | okx: crypto_spot | grey (D6) | 14 | 2026-12-02 |
| KR-OKX-DERIV | okx: crypto_derivative | hard_block (OKX blocks South Korea) | 14 | 2027-01-21 |
| KR-OKX-P2P | okx: crypto_p2p | hard_block (OKX blocks South Korea) | 14 | 2027-01-21 |
| KR-OFFSHORE-CEX | binance, bybit, bitget: any | out_of_scope (grey venues the owner does not use; enabling one needs a reviewed row) | 13 | 2027-01-21 |
| KR-STATE-BLOCKED | kucoin, mexc, phemex, xtcom, bitrue, coinw, poloniex, btcc, bingx, bitmart, digifinex, and every other site on the KCSC block list of 2026-10-13: any | hard_block (reachable only by VPN) | 15 | 2027-01-21 |
| KR-HYPERLIQUID | hyperliquid: any | out_of_scope (grey; the owner holds no wallet; enabling needs a reviewed row) | 16, 18 | 2027-01-21 |
| KR-DEX-SPOT | pumpfun, jupiter, uniswap: any | out_of_scope (grey; not configured) | 17 | 2027-01-21 |
| KR-PREDICTION-VENUES | polymarket, kalshi, limitless, myriad, opinion, predictfun, drift, robinhood, cryptocom, predictit: any | hard_block | 1-6 | 2027-01-21 |
| KR-IBKR | ibkr: any | hard_block (direct foreign-broker routing; FX reporting) | 36 | 2027-01-21 |
| KR-RETAIL-APPS | moomoo, webull, etoro: any | hard_block (blocked or unknown for Korea) | 37 | 2027-01-21 |
| KR-OFFSHORE-FX-CFD | offshore_fx_cfd: any | hard_block | 38 | 2027-01-21 |
| KR-LOTTERY-BETMAN | betman, lotto: any | out_of_scope (lawful, but not trading) | 8, 9 | 2027-01-21 |
| KR-CONDUCT-EVENT | any venue: event_contract | hard_block (Criminal Act Art. 246) | 1-6 | 2027-01-21 |
| KR-CONDUCT-SPORTS | any venue: sports_bet | hard_block (National Sports Promotion Act Art. 26, 48(3)) | 3, 7 | 2027-01-21 |
| KR-CONDUCT-ROUTE | any intent with route ≠ direct | hard_block (VPN/proxy; state blocks; platform terms) | 15, 16 | 2027-01-21 |
| KR-CONDUCT-OTHERS | any intent with on_behalf ≠ self | hard_block (pooled money, copy-trading, trading for others; 특금법, 2024도10710) | 20 | 2027-01-21 |
| KR-CONDUCT-SIGNALS | any intent with publishes_signal | hard_block (signals meant to move prices; VAUPA Art. 10; advisory registration unresearched) | 20 | 2027-01-21 |
| KR-CONDUCT-MANIP | any intent tagged coordinated, self_match, spoof or layer | hard_block (VAUPA Art. 10) | 20 | 2027-01-21 |

**Review dates**
- Crypto rows are due 2026-12-02, the day before the FX Act amendment takes effect.
- Tax and leverage rows are due 2026-12-31, after the December votes.
- Every other row is due within the 90-day cap, which runs to 2027-01-21.
- The travel-rule decree (about 2027-02-18; the reported dates conflict) and the first Gangwon Polymarket rulings
  will each set their rows' next review date when those rows are re-reviewed.

### 5.4 Lifecycle and alerts

- **Fail closed.** If today is after a row's `review_by`, `decide()` treats that row as a hard block with the reason
  "stale: review by YYYY-MM-DD passed" (D5).
- **Re-review.** Someone re-checks the row's sources, appends a `reviews` entry and moves `review_by`, then commits.
  Claude may draft the research. The owner approves the commit.
- **`python -m core.compliance.rules --check [--today YYYY-MM-DD] [--toast]`** lists rows that are overdue or due within
  14 days.
  - Exit 0: nothing is due.
  - Exit 1: something is due soon.
  - Exit 2: something is overdue.
  - Exit 3: the table is missing, corrupt or invalid, which also counts as a block for every decision.
- **The daily alert job.** A local scheduled Claude task runs at 09:00 KST. It runs the check, and when anything is
  overdue, or due in exactly 14 or 3 days, it sends:
  1. an iOS push through the Claude app;
  2. an email **only to the owner's own address** (sapientia@korea.ac.kr, unless the owner names another of their own
     addresses), through the connected Gmail, containing only the alert text;
  3. a Windows toast, via `--toast`.

  The owner approves the task once when it is created. Their D5 instruction is the standing authority for these
  self-addressed alerts, and for nothing else.
- **Alert log.** Each send is logged in `~/.tradegen/compliance/alerts.jsonl` with the channel, time and result. When a
  channel fails, the failure is announced on the others. When the check itself fails, that is announced too.
- **In-app banner.** The TRADEGEN app shows a banner while any row is overdue.
- **No new credentials.** No credential is stored in TRADEGEN for any of this.

---

## 6. The `decide()` kernel (`core/compliance/gate.py`)

### 6.1 Types

```python
@dataclass(frozen=True)
class Intent:
    kind: str                      # "order" | "transfer" | "plan_leg"
    venue: str                     # canonical venue id (section 5.2)
    instrument: str                # instrument class
    side: str = "buy"              # "buy" | "sell"
    leverage: float = 1.0
    notional_krw: float = 0.0
    destination_venue: str | None = None    # transfers only
    route: str = "direct"          # anything else is blocked
    on_behalf: str = "self"        # anything else is blocked
    publishes_signal: bool = False
    tags: frozenset = frozenset()  # e.g. {"coordinated"}; execution adds "self_match" when it detects one

@dataclass(frozen=True)
class Context:
    date: date                     # the KST trading date, supplied by the caller
    rules: RulesTable              # carries rules_hash
    flags: OwnerFlags              # evidenced course completions, dated deposit snapshots, broker approvals
    session: SessionAcks           # row ids acknowledged this armed session + sha256 of the warning text seen
    equity_krw: float
    exposure_krw: Mapping[str, float]       # by venue
    caps: Mapping[str, float]               # e.g. {"okx_equity_share": 0.2}; owner-set; absent = unset

@dataclass(frozen=True)
class Decision:
    verdict: str                   # "ALLOW" | "ACK_REQUIRED" | "BLOCK"
    reasons: tuple                 # ((row_id, plain text), ...), every reason, strictest first
    intent_hash: str; rules_hash: str; ctx_hash: str; date: date
    decision_id: str               # sha256 of the above

@dataclass(frozen=True)
class Permit:                      # only from ALLOW
    decision_id: str; intent_hash: str; rules_hash: str; date: date
```

### 6.2 Evaluation order

1. **Validate the input.** A malformed intent (wrong types, negative notional, leverage < 1, unknown kind) is
   blocked. So is an unknown venue or instrument class. The kernel never raises: any internal error becomes
   `BLOCK ("internal error: <type>")`.
2. **Conduct rows.** These apply on every venue: `event_contract`, `sports_bet`, `route ≠ "direct"`,
   `on_behalf ≠ "self"`, `publishes_signal` and the manipulation tags. Each one gives BLOCK. State-blocked venues are
   known venue ids, blocked by their venue row in step 3, so the refusal names the KCSC block.
3. **Venue rows.** Only rows in force on `ctx.date` count (`effective_from ≤ date`, and `effective_until` either null or
   later than date).
   - No matching row: BLOCK.
   - For each matching row:
     - **stale** (date after `review_by`): BLOCK;
     - **`hard_block`**: BLOCK;
     - **`out_of_scope`**: BLOCK, giving its reason;
     - **`gated`**: every `requires` item must be met by evidenced flags. A course needs a completion date and a
       certificate reference. A deposit needs a snapshot dated within 7 days. Anything unmet is BLOCK, naming what is
       missing. This is a pre-check that explains the refusal; the broker enforces the same walls itself. A gated row
       with `ack: per_session` (credit buying, short selling, coin lending, long US options) also needs this
       session's acknowledgement, or it returns ACK_REQUIRED;
     - **`grey`**:
       - BLOCK if `date ≥ auto_off`;
       - BLOCK if the cap is unset;
       - BLOCK if exposure after the intent would exceed `cap × equity`;
       - ACK_REQUIRED if the row is not acknowledged in `ctx.session`;
       - otherwise ALLOW;
     - **`allow`**: ALLOW.
   - `leverage > row.max_leverage` gives BLOCK. `max_leverage` defaults to 1.0; only KR-KIS-CREDIT (2.2) and the
     gated leverage rows (their product's own multiple) set it higher.
4. **Transfers.** A transfer's destination is evaluated as if it were a `crypto_spot` intent on `destination_venue`.
   The transfer gets the stricter of the two results.
5. **Combine.** BLOCK beats ACK_REQUIRED, which beats ALLOW. Every reason is kept.

### 6.3 Permits and plan screening

- **`permit(decision)`** returns a `Permit` only for ALLOW. The execution spec will make permits single-use: a permit
  must match the exact intent hash, is recorded in the audit log, and expires at the end of `date`. It is refused on
  any date mismatch.
- **`screen(plan, ctx)`** runs `decide()` on every leg, as a `plan_leg` intent at the leg's largest size and leverage.
  - If any leg is blocked, the plan is refused.
  - A leg needing acknowledgement is still simulated, but labelled `GREY_LEG`, and the cap is enforced inside the
    simulation.
  - The returned `Screening` carries the decisions and a hash that `simulate()` requires.

### 6.4 The owner log (`core/compliance/owner.py`)

- **Storage:** `~/.tradegen/compliance/owner.jsonl`. It is append-only and hash-chained: each line carries the sha256
  of the previous line.
- **Events:**
  - `course_completed` {course, date, evidence};
  - `deposit_snapshot` {krw, source: kis_api | manual, date};
  - `broker_approval` {kind, date, evidence};
  - `cap_set` {key, value};
  - `session_armed` / `session_ack` {session_id, row_id, warning_sha256};
  - `limit_set` {total_loss_floor_krw, daily_loss_krw}.
- **Writes** go only through an explicit owner-confirmation API, which prints exactly what will be recorded and waits
  for a typed confirmation. **Claude never records a flag, an acknowledgement, a cap or a limit on the owner's behalf.**
- **A broken chain:** all flags and acknowledgements count as absent, so gated and grey rows are blocked, and the alert
  fires.

---

## 7. The odds engine (`core/odds/`)

### 7.1 Plans

```python
@dataclass(frozen=True)
class Leg:
    venue: str; instrument: str; symbol: str
    model: str                     # "bootstrap" | "garch_t" | "bet"
    bet: BetSpec | None = None     # bet legs: take-profit +u, stop -d (fractions); see 7.2
    edge_source: str = "none"      # "none" | "validated:<card_id>.r<rev>@<results_md5>" | "assumed"
    assumed_p: float | None = None # only with edge_source == "assumed"

@dataclass(frozen=True)
class Plan:
    name: str; track: str          # "moonshot" | "compounding"
    stake_krw: float = 42_000
    target_krw: float              # fixed in KRW at plan creation (e.g. 42,000,000); before tax
    fx_krw_per_usd: float          # recorded FX close used to fix the target
    start: date                    # default: the first armed session
    horizon_days: int = 30         # calendar days; each leg steps only on its market's sessions
    legs: tuple[Leg, ...]
    sizing: Sizing                 # fixed_fraction(f) | kelly(c <= 0.5) | bold()
    limits: Limits                 # {ref: owner-log key} for total_loss_floor_krw and daily_loss_krw (D3)
```

**Sizing**
- `fixed_fraction(f)`: stake f of current equity.
- `kelly(c)`: c × the growth-optimal fraction, computed numerically as argmax E[ln(1 + fR)] from the leg's return
  model.
  - Only a **validated** edge feeds it, using the lower 95% bound after the card's own haircut.
  - With no validated edge it stakes 0 and reports "this plan places no trades".
  - It is labelled "growth-optimal, not target-optimal".
- `bold()`: for bet legs, stake = min(W − L − fee_reserve, (T − W)/b).

**Every stake is then cut**, in this order:
1. to the at-risk limit (a bracket stop d risks at most d × stake, so the stake is at most (W − L)/d);
2. to the grey cap;
3. to whole lots and venue minimums;
4. to no leverage (at most W).

### 7.2 The no-edge null and edge sources (`models.py`)

**One definition of no edge.** Every position's expected *simple* return per step is exactly zero before costs:
E[1 + R] = 1. Costs then make the expected return negative.

- **`GarchT`**: `core.quant.garch.fit_garch`, then `simulate_returns(fit, rate_daily=0.0)`. That call subtracts each
  path's exact convexity correction. The repo's `drift="zero"` is zero *log* drift, which gives an arithmetic edge of
  about σ²/2 per day (+2.4% a month at 4% daily volatility), and is never used.
- **`StationaryBootstrap`**: a new vectorised stationary bootstrap of date-aligned daily (open, low, close) rows, with
  mean block length from `gate_stats.pw_block(x, "stationary")`. It holds running state only, never the path matrix.
  - Simple returns are computed after the KRX price limit has been applied relative to the base price, and are then
    demeaned so that E[1 + R] = 1.
  - Each day's open, low and close, all relative to the previous close, are multiplied by the same factor
    1/mean(1 + R_close). The intraday shape is kept and only the drift is removed.
  - Limit-up and limit-down flags come from the original row, never from the rescaled one.
  - Multi-leg plans resample whole dates jointly. KRW=X is included as a row for US legs.
- **`BetLeg`**: a +u / −d bracket on the leg's price process. Under the no-edge null on a continuous path the win
  probability is p₀ = d/(u + d).
  - Gaps through the stop lower the realised payoff, and the simulator models them (section 7.3).
  - How many bets resolve within the horizon comes from the bracket's simulated first-passage times on the leg's
    bootstrap paths.
  - A typed p is `edge_source = "assumed"`.
- **Edge sources:**
  - `none` is the default and is always the headline.
  - `validated:<card_id>.r<rev>@<results_md5>` is resolved only through `cards.read_chain` / `verify_verdict_chain`.
    It needs verdict PASS and a `results_md5` that re-hashes. A bare `ModelCard` JSON is refused.
    - Its mean is the card's out-of-sample daily P&L mean multiplied by the card's own live multiplier
      (`GATE["haircut"]`, 0.6, read from the card, never a literal). Only the extra costs a small account pays above
      the table rate are added: ticket rounding and FX conversion.
    - **Today no card is PASS**, so the validated column is empty for every plan.
  - `assumed` is the owner's typed win rate, shown only in a separate, labelled column.

**Data rules**
- `models.py` refuses any `History` whose source is SYNTHETIC; the loaders fall back silently, so this refusal must be
  explicit.
- A `provisional_intraday` last bar is dropped.
- OKX has no loader, so OKX legs use Binance USDT spot (`crypto_history`, keyless) as a stand-in, flagged
  `PROXY_DATA`, and are converted to KRW at Upbit KRW-USDT.
- Single-coin and single-name legs add a delisting stress column (`tf_books.DELIST_STRESS`, −30% / −100%).
- Each series is hashed as md5 of canonical JSON {symbol, source, dates, OHLC, adjustment, status}.

**Costs**
- The base cost is `instruments.cost_per_side(cost_class(symbol))`, a class quote that already contains the sell tax and
  exempts ETFs; the tax is never added again on top.
- Extra owner-signed rows in `venues.yaml` may only raise costs, and `check_cost_policy` enforces that:
  - KIS KRW-USD conversion spread;
  - US minimum commission;
  - Upbit and OKX trading fees where they exceed the class quote;
  - Upbit → OKX withdrawal fee.
- Entry and exit are charged on every trade.
- Every plan runs at 1× and at `GATE["cost_stress"]` = 2× cost, and both results are printed.

**Minimum tickets** come from the owner-signed `venues.yaml`:
- KRX: 1 share;
- KIS US: whether fractional orders are allowed, and the minimum;
- Upbit: KRW 5,000;
- OKX: the minimum size per pair, with the source URL.

A missing entry makes the leg `NotTradable`, a named refusal. The simulator carries a price level per path and buys
`floor(stake / price)` whole units, or fractional units where allowed.

**Calendar**
- Steps are calendar days from `start`. A leg moves only when `clocks.is_session(market, d)`; crypto moves every day.
- The report prints each leg's session count (`sessions_between`), which is 18 to 22 for KRX in 30 days.
- A GREY_LEG whose horizon crosses its `auto_off` date is force-exited on that date, with costs charged.

### 7.3 Simulation (`simulate.py`)

- **Path state:** cash, units held, price level, entry price, and one outcome. The outcomes are mutually exclusive and
  always sum to n:
  - REACHED (equity ≥ target; moonshot paths stop here);
  - RUINED (equity at or below the total-loss floor; absorbed, so execution would halt for good);
  - STUCK (too little left to place any order after fees);
  - RUNNING (still trading at the horizon).
- **Stops and the daily limit.** A stop or the daily loss limit triggers when the day's low crosses it, and fills at
  min(open, stop), so gaps go through stops.
- **KRX limit-down.** If a KRX day closes at its limit-down price (`orders.limit_prices` from the dated price limit in
  `kr_regime_tags.yaml`), the exit cannot fill. It carries to the next session at `LIMIT_DOWN_CARRY_COST_MULTIPLIER`
  (2×) cost.
- **Ruin** is recorded at the equity actually reached on the fill, not at the threshold. The report shows the overshoot
  below the floor, as the mean and the worst case (`LIMIT_GAP`).
- **Scale and reproducibility:**
  - `CHUNK = 200_000` paths per chunk, a fixed constant.
  - Chunk i uses `SeedSequence(seed, spawn_key=(i,))`, so results do not depend on the total n.
  - Defaults: n = 1,000,000 for moonshot plans and 200,000 for compounding plans.
  - The seed is derived as sha256(plan canonical JSON ‖ data hashes); the owner does not choose it.
  - A standalone check ran 1,000,000 paths × 30 steps, with sizing and absorbing states, in about 0.4 s. A 200k chunk
    with GARCH temporaries needs about 100 MB.

### 7.4 Exact references (`bold.py`)

- **`ceiling(W0, L, T, gap_possible)`**: (W₀ − L)/(T − L) when no step can gap below L. Otherwise it is W₀/T, and the
  report says which applies. It applies only when every leg has `edge_source = "none"`. Otherwise the report prints
  "the ceiling does not apply: this column assumes an edge".
- **`structural_max(plan)`**: the largest multiple the market allows in the horizon. For KRX that is ∏(1 + limit-up)
  over the leg's sessions; for bootstrap legs it is the empirical per-session maximum compounded over the sessions.
  When target/stake exceeds it, the report prints **"IMPOSSIBLE in this horizon: the most any path can reach is
  N×"** and shows no probability.
- **`bold_even(x, p)`**: the exact even-money bold-play value by binary-expansion recursion, used as the regression
  check.
- **For bet legs only:**
  - **`bet_optimum(bet, W0, L, T, n_bets, fees, min_ticket, caps)`**: the highest P(reach T) any way of staking that bet
    can give. It is computed by value iteration, V_k(w) = max over the allowed stakes of Σ p_j V_{k−1}(w′), on a
    KRW-ticket log grid absorbing at L and T, with k = the bets that fit in the horizon.
  - **`bold_policy_value(...)`**: the bold policy's value, by memoised recursion over the states it can reach.
  - The report shows both, plus how often bold play loses the stake. Simulated P(target) must not exceed
    `bet_optimum` beyond simulation error.
- **Kelly context**, only with a validated edge: "typical bets needed" = ln(T/W₀)/g, compared with the bets the month
  allows. It is not a probability.

### 7.5 The report (`report.py`)

Each plan card shows, in this order:
1. **Average result:** "you end with about KRW X, an average loss of KRW Y (Z%). That is what fees, tax and the bet's
   house edge cost."
   - The expected loss comes from per-path accumulated costs and house edge, which have low variance. It does not come
     from the mean ending equity, which a rare jackpot path makes noisy.
   - Beside it: "No plan without a real edge can beat 1 in N", the applicable ceiling.
2. **The headline pair:** P(reach KRW 42,000,000) and P(lose the stake) = P(RUINED) + P(STUCK), with the split
   underneath. Then the outcome ladder (D4), with each rung measured on ending equity; paths stopped at the target
   carry T.
3. **The plain sentence:** "In 1,000,000 simulated months (made-up months from a model in which nobody has an edge, not
   real history), this plan reached KRW 42,000,000 (USD 30,000 at the plan's fixed rate of 1,400 won) in 63, about
   1 in 16,000 (0.0063%; simulation precision 0.0049–0.0081%, which does not include the model being wrong). It lost
   your stake in 912,034 (91.2%, total-loss limit hit) plus N (left below the minimum order, effectively lost), and
   was still trading at the end in M. On average you end with KRW Z."
4. **Precision:**
   - Clopper–Pearson intervals throughout: two-sided 95% for k > 0. For k = 0 the one-sided 95% upper bound is shown,
     phrased "below resolution: under about 3 in n". **"0%" is never printed.**
   - A structural zero is phrased as "IMPOSSIBLE…" or "this plan places no trades".
5. **Model spread:**
   - P(target) and P(lose the stake) under each eligible model (bootstrap, GARCH-t, bet), plus a parameter bootstrap
     (refit on resampled history), shown as a min–max range.
   - Comparisons use the worst case.
   - A multi-leg plan under GARCH-t is flagged `INDEPENDENT_LEGS`, because the GARCH fit is univariate.
6. **Columns:**
   - **No edge** (always the headline);
   - **If tested edge <card> is real**: this is `VALIDATED_EDGE`, and today it is always empty;
   - **Using your typed win rate**: this is `ASSUMED_EDGE`.
7. **Flags**, each with one plain sentence (section 10 gives the full wording):
   - `HIDDEN_EDGE` (red): the simulated mean of (ending equity + costs paid + house edge accrued) differs from the stake
     by more than 4 standard errors;
   - `CEILING_BREACH`: red when the one-sided 99.9% Clopper–Pearson lower bound on P(target) exceeds the ceiling or
     `bet_optimum`; amber "at the ceiling within simulation noise; rerun with more paths" when only the point estimate
     does. It applies only when every leg has edge `none`;
   - `IMPOSSIBLE`, `BELOW_RESOLUTION`, `GREY_LEG`, `PROXY_DATA`, `LIMIT_GAP`;
   - `COST_DOMINATED`: the round-trip cost exceeds half the leg's median absolute daily move;
   - `INDEPENDENT_LEGS`, `NOT_TRADABLE`, `STUCK_AT_START`.
8. **"Not in these numbers":** "An exchange freezing withdrawals or failing; a coin being delisted or flagged by Upbit
   (the history only contains coins that still trade); orders filling worse than simulated; rule changes. Each of
   these can only make the real result worse."
9. **Footer:** "These numbers describe rules you wrote, run in a model. They are not advice, and TRADEGEN does not
   recommend any plan. A higher chance of USD 30,000 does not make a plan better."

**Comparing plans honestly**
- There is no ranking by P(target). Plans are listed in creation order, or by smallest average loss.
- The moonshot table carries a fixed caption: "With no real edge, the plan with the highest chance of USD 30,000 is
  always the one that bets the most, soonest, and it is also the one that loses your stake most often. Higher here
  means riskier, not better."
- All plans in one comparison share the same random numbers (common random numbers).
- The comparison prints: "You compared K plans (and tried J typed win rates) in this session. The best-looking figure is
  the luckiest of K and is probably too high."
- Before a plan can be armed (execution spec), it is re-run once on a fresh seed derived from (plan, data, run counter),
  and that confirmation figure is shown.

**Language guard.** `report.py`'s self-check fails if rendered text contains "best", "optimal", "recommended", "safe",
"guaranteed" or "likely to reach". The internal function name `bet_optimum` never appears in rendered text, which says
"the highest chance any way of placing this bet can give".

**Provenance** recorded in every report:
- the rules hash;
- the data hashes, and the cost and venue table hashes;
- the model, seed, n, CHUNK, NumPy version and bit generator (PCG64);
- the edge sources;
- `macro_artifacts.tree_hash()`, git HEAD and a dirty flag.

---

## 8. Testing

Two new hermetic suites are registered in `tests/run_all.py`: `compliance` (`tests/compliance_acceptance.py`) and
`odds` (`tests/odds_acceptance.py`). They make no network calls and read no wall clock (dates are passed in). They write
only to temp directories, under `TRADEGEN_HOME` pointed at a temp dir, and are built test-first.

**compliance**
1. **Table integrity:**
   - the schema is valid;
   - ids are unique;
   - every row is sourced and dated;
   - every `review_by` is within 90 days of its latest review;
   - all 38 matrix rows are covered;
   - every `research` pointer resolves to an existing file.
2. **Hard blocks:** one test per conduct class, on every venue id, covering event contracts, sports, route, on_behalf,
   signals, manipulation tags, state-blocked venues, OKX derivatives and OKX P2P. A randomised property test checks that
   any intent carrying a blocked attribute is always BLOCK.
3. **Fail-closed inputs:**
   - unknown venues and instruments are BLOCK;
   - fuzzed garbage gives BLOCK and never raises;
   - a missing, corrupt or invalid table blocks everything (CLI exit code 3).
4. **Gated rows:** a missing flag gives BLOCK naming the flag; a deposit snapshot older than 7 days gives BLOCK;
   evidenced flags give ALLOW.
5. **OKX spot:**
   - no acknowledgement gives ACK_REQUIRED;
   - an unset cap gives BLOCK;
   - exposure over the cap gives BLOCK;
   - any date on or after 2026-12-03 gives BLOCK;
   - a transfer to OKX inherits the OKX row.
6. **Staleness and alerts:**
   - a date after `review_by` gives BLOCK "stale";
   - due-in-14 and due-in-3 are detected;
   - the CLI exit codes are 0, 1, 2 and 3;
   - the fan-out to fake channels works, and one failing channel is announced on the others.
7. **Purity and determinism:**
   - during `decide()`, `open`, sockets and `time`/`datetime.now` are patched to raise;
   - identical inputs give an identical `decision_id`;
   - any field change alters the `intent_hash`, and a permit is refused for a different intent or date.
8. **Owner log:** the chain verifies; a tampered log means flags are absent; only the confirmation API writes; paths
   resolve under `~/.tradegen` and `refuse_quantgen` holds.

**odds**
1. **No-edge null:** under each model, E[1 + R] = 1 within simulation error. A regression test shows that the repo's
   `drift="zero"` fails this check.
2. **Ceiling:** randomised no-edge plans never exceed (W₀ − L)/(T − L) beyond the 99.9% lower bound.
3. **Exact values:**
   - `bold_even` gives 0.1000%, 0.0816%, 0.0346% and 0.0106%, and 0.0400% with L at half the stake;
   - `bet_optimum` ≥ the bold policy, and equals it for fee-free even money;
   - the simulated bold policy matches its exact value within the Clopper–Pearson interval.
4. **Mechanics:**
   - a KRX-only plan for 1,000× is IMPOSSIBLE;
   - gap-through stop fills;
   - the limit-down carry at 2× cost;
   - a share price above the stake gives STUCK_AT_START;
   - the outcomes sum to n;
   - session counts match the calendars (18 KRX sessions from 2026-09-21; 22 from 2026-10-26);
   - an OKX leg is force-exited at 2026-12-03.
5. **Reproducibility:** the same plan and data give an identical report; results are independent of chunk count; the
   NumPy version is recorded.
6. **Costs:** extra rows may only raise costs; the 1× and 2× runs are both present; the tax is never charged twice.
7. **Data:** SYNTHETIC history is refused; a provisional bar is dropped; `PROXY_DATA` is set for OKX.
8. **Edge:**
   - Kelly stakes 0 without a verified chain;
   - a fake PASS chain in a temp dir resolves;
   - a tampered `results_md5` is refused;
   - assumed edges never reach the headline.
9. **Report:**
   - the average result comes first;
   - the footer and the "not in these numbers" box are present;
   - "0%" never appears;
   - there are no banned words;
   - the winner's-curse note shows K;
   - the moonshot caption is present.

**Existing guards stay in force.** Both packages are under `core/`, so the read-only order-path scans cover them:
`tests/acceptance.py` test_08 and test_09, and `tests/macro_m0_harness.py` T-RO-01 and T-RO-02. No identifier,
docstring or comment in either package may contain an order-endpoint name.

## 9. Error handling

- **Gate (fails closed everywhere):**
  - any internal error is BLOCK;
  - a missing, corrupt or invalid table is BLOCK for every decision and fires the alert;
  - a broken owner-log chain means flags and acknowledgements count as absent, and fires the alert;
  - a permit whose date or intent hash does not match is refused.
- **Odds (refuses rather than guessing).** It gives a named reason, never a number, when:
  - the plan is unscreened or blocked;
  - the data is synthetic;
  - a cost or venue row is missing (`NotTradable`);
  - the leg combination is unsupported.
  - If one model fails to fit (a GARCH guardrail, for instance), it is omitted from the spread with a note. If every
    model fails, the plan is refused.
  - A refused run never prints a probability.
- **Alerts:** a failure of the check itself is alerted on every working channel.
- **Paths:** everything is written under `~/.tradegen`, and writers call `refuse_quantgen`.

## 10. The guardrails, in plain language

| Guardrail | What it protects you from | What you see when it binds | Safe to change? |
|---|---|---|---|
| No-edge null | A model that quietly "makes money" with no edge | Nothing; it is the default | Never. Only a validated card can add an edge |
| HIDDEN_EDGE | A bug that hands a plan free money | Red: "On average this model makes money without any edge. That is a bug, so do not use these numbers." | Never disable |
| Ceiling | Believing any no-edge plan can beat 1 in 1,000 | "No plan without a real edge can beat 1 in N." | It is maths, not a setting |
| CEILING_BREACH | Numbers that are impossible under no edge | Red "do not use these numbers", or amber "rerun with more paths" | Never disable |
| IMPOSSIBLE | Chasing a target the market cannot reach in time (KRX: about 247× a month) | "IMPOSSIBLE in this horizon" and no probability | It is a market fact |
| Simulation precision | Mistaking counting noise for your real odds | The range in brackets, with "does not include the model being wrong" | More paths narrow it; never hide it |
| Model spread | Trusting one model of the market | A min–max range; comparisons use the worst case | Adding models is safe; removing one is not |
| BELOW_RESOLUTION | A tiny chance shown as 0% | "under about 3 in n" | More paths |
| 2× costs | Costs eating the edge | A second column at double costs | Never remove |
| Minimum tickets / STUCK | A plan that cannot actually trade its size | "can't open" / "left below the minimum order" | Owner-signed venue table only |
| LIMIT_GAP | Assuming a stop always fills at its level | The worst overshoot below your floor | It is how markets gap |
| Winner's curse | Picking the luckiest of many plans | "You compared K plans…" and a fresh-seed confirmation | Never disable |
| Stale rules | Trading on a rule that may have changed | The venue blocked, plus alerts on every channel | Re-review the row, never skip the date |
| Grey cap and acknowledgement | Unbounded grey-venue exposure | ACK_REQUIRED or BLOCK on OKX | Cap only through the owner log |

## 11. Owner inputs and open legal points

**Values the owner sets** through the owner log. Claude never sets them.
- The total-loss floor `total_loss_floor_krw` (D3).
- The daily loss limit `daily_loss_krw`.
- The OKX cap `okx_equity_share`, in [0, 1]. While it is unset, OKX is blocked.
- The `venues.yaml` fee, lot and minimum rows, each with its source. Claude may draft them from the venues' public fee
  pages; the owner signs them.
- Course completions, deposit snapshots and broker approvals, if any are ever obtained.

**Open legal points for Korean counsel**, from the report's "Further review recommended":
- The user-side status of overseas unregistered exchanges, and of transfers to them, after 2026-12-03 and about
  2027-02-18.
- Whether building and running this tool reaches Criminal Act Art. 247 or National Sports Promotion Act Art. 26②. The
  hard blocks keep prediction and sports features out entirely, but the question remains for the research-only GrokBot
  copy.
- Which FX reports apply to crypto moved to USD-denominated platforms.
- Whether sharing outputs would need advisory registration. The design forbids sharing, through KR-CONDUCT-SIGNALS.
- The November–December 2026 votes: the crypto tax, the Digital Asset Basic Act and the single-stock leverage cap.

## 12. Risks

- **The table goes out of date.** Mitigations: review dates fail closed, plus the daily all-channel alert.
- **The owner reads simulated odds as forecasts.** Mitigations: model-not-history wording, the precision disclaimer,
  the model spread, average loss shown first, and the banned-word guard.
- **An edge creeps into the headline.** Mitigations: validated edges go only through the verified card chain (none
  today), assumed edges go into a separate column, and HIDDEN_EDGE.
- **A grey venue gets tightened suddenly.** Mitigations: auto-off on 2026-12-03, the per-session acknowledgement, the
  cap, and the stale-row block.
- **The alert channels depend on the Claude scheduled task, which runs only while the PC is on.** Mitigation: the
  in-app banner, and the check runs at every app start.

## 13. Out of scope (later specs)

- Broker and exchange adapters, arming, permits made single-use, and the audit log (the execution spec).
- Strategy research and generation (the strategies spec, with `anthropic-skills:deep-research`).
- The UI (a spec using design-system and design-critique).
- `legal:compliance-check` per venue before any real-money feature ships.
- Importance sampling: skipped; add it when a plan needs precision below about 1e-5.
- An OKX candle loader: skipped (the Binance proxy is flagged); add it if the proxy proves misleading.

---

## Appendix A: how the pre-spec review shaped section 7

Three independent critics reviewed the odds-engine draft on 2026-10-23: statistics, honesty and plain language, and
fit with the repository. Their must-fix findings, and how each was resolved:

| Finding | Resolution |
|---|---|
| The repo's "zero drift" is zero log drift, a hidden edge of about σ²/2 per day | No-edge null redefined as zero arithmetic drift (7.2); HIDDEN_EDGE check; regression test |
| Bold play cannot be played with 1x KRX; 1.3²¹ ≈ 247× < 1000× | `structural_max` and IMPOSSIBLE (7.4); bet legs derived from brackets (7.2) |
| The ceiling and the bold stake ignored the loss floor L | Ceiling (W₀ − L)/(T − L); bold stake capped at W − L (7.1, 7.4) |
| Bold play is not the true optimum under fees, tickets and limits | `bet_optimum` by value iteration; bold play shown for comparison only |
| CEILING_BREACH would fire on simulation noise | Clopper–Pearson 99.9% lower bound; amber band |
| A "95% CI" would read as the true odds | "Simulation precision" wording; model spread; one interval convention |
| Daily limits act only at end of day; ±30% clipping; limit-down locks | OHLC bootstrap, gap-through fills, limit-down carry at 2×, overshoot reported |
| STUCK was excluded from ruin | Four-way outcome partition; P(lose the stake) = RUINED + STUCK |
| Kelly misuse | Numeric Kelly on the validated lower bound, at most half-Kelly, labelled growth-optimal |
| No PASS card exists; GATE needs about 8 years of data | Validated edges only through the verified card chain; stated as empty today |
| load_history silently falls back to SYNTHETIC; there is no OKX loader | Explicit refusal; Binance proxy flagged PROXY_DATA |
| The draft's own cost list conflicted with the repo's single cost table | `cost_per_side` as the base; owner-signed rows may only raise costs; 2× run |
| No minimum-ticket data exists in the repo | Owner-signed `venues.yaml`; whole-unit simulation; NotTradable |
| A fixed 21 sessions; the multi-leg calendar; FX | Calendar-day stepping with `is_session`; joint date-aligned bootstrap; target fixed in KRW |
| Ranking by P(target) rewards ruin | No ranking; fixed caption; average loss shown first |
| Winner's curse and seed shopping | Derived seeds, common random numbers, a fresh-seed confirmation, the K note |
| Survivorship, delisting and the OKX auto-off inside the horizon | DELIST_STRESS column; forced exit at auto_off; the "not in these numbers" box |
