# TRADEGEN compliance gate and odds engine

Date: 2026-10-23.

Status:
- **Revision 3.1.**
  - Round 1 reviewed rev 1: Gemini said REJECT, and the Claude 5×2 workflow confirmed most of its points (Appendix B).
  - Round 2 reviewed rev 2.1: GPT (Codex) said REJECT, with 16 major findings (Appendix C). The quota note in the brief
    proved stale.
  - Round 3 reviewed rev 3 (Appendix D):
    - GPT stopped at its usage limit, which resets 2026-10-30 14:40.
    - Gemini's run ended in `status: ERROR`, and most of it reviewed text that is not in this spec. Its six findings
      that do hold are folded in here.
  - The owner decided D11 to D16 on 2026-10-23.
  - All reviews are in `docs/superpowers/specs/2026-10-23-review-gate-odds/`.
- Next: the owner's review, plus GPT's final check of this revision after 2026-10-30 14:40. Then two implementation
  plans; the compliance plan comes first, because the odds engine depends on `screen()`.

Inputs:
- `reports/Korean resident trading venue legality.md`, with its notes in `research_notes/Korean resident trading venue legality/`;
- `research_notes/QUANTGEN asset coverage expansion/crypto_wallets_connectivity.md`;
- `research_notes/QUANTGEN TRADEGEN split map/split_map.md`;
- the Phase A isolation (`d47cea9`).

> This is research and software design, not legal, tax or investment advice. Neither TRADEGEN nor its author is a
> licensed advisor. Before any real-money feature ships, the open legal points in section 11 need Korean-qualified
> counsel.

---

## 1. Purpose and scope

TRADEGEN is a personal trading program for one Korean-resident individual, trading their own money from about
KRW 42,000 (USD 30). It runs two tracks: a **moonshot** track aimed at USD 30,000, about 1,000 times the stake, and a
realistic **compounding** track.

This spec covers two building blocks:
1. **The compliance gate** (`core/compliance/`). It decides whether an order, transfer or plan leg is allowed for this
   owner under Korean law as researched, and under the owner's own stricter policies. Unknown, unapproved or stale
   cases are refused for new exposure. Exits stay open (D11).
2. **The odds engine** (`core/odds/`). It shows the honest chance of each outcome for a plan the gate allows.

**Neither package can place an order.** Execution, strategy research and the UI each get their own spec. They are built
on these interfaces: `decide()`, `permit()` / `verify_permit()`, and `OddsReport`.

**Limits of this version**
- The odds engine accepts **single-leg, cash-financed, 1x, long-only plans** on a whitelist of asset classes. These are
  KRX cash shares, KRX 1x ETFs and ETNs, US stocks and 1x ETFs, and crypto spot.
- Everything else is refused with a named reason, including multi-leg plans, leverage, shorts and options.
- The gate covers every action and asset class, so the execution spec inherits the full rule set.

## 2. Owner decisions (fixed inputs)

| # | Decision | Status |
|---|---|---|
| D1 | Build order: the gate and the odds engine first (no money moves), then execution, then strategies and the UI | decided 2026-10-23 |
| D2 | Accounts: KIS stock account; Upbit (opened 2026-10-23), the lawful KRW-spot crypto venue; OKX (overseas exchange) | decided |
| D3 | Ruin = equity reaching the owner's hard total-loss floor L. Execution halts for good there, and the odds engine and the kill switch read one shared setting | decided |
| D4 | The compounding track reports an outcome ladder (P(+10%), P(+25%), P(2x), P(10x), P(target), median and 5th percentile), not a single target | decided |
| D5 | A rule row past its review date fails closed for new exposure, and the owner is alerted on every channel: iOS push via the Claude app, email to their own address, and a Windows notification | decided |
| D6 | OKX spot is grey. It is off by default. Each armed session needs a warning acknowledgement, and OKX exposure is capped at a share of equity the owner sets. It switches off automatically on 2026-12-03 until re-reviewed. OKX derivatives and P2P are hard-blocked | decided |
| D7 | Every plan shows P(reaching the target) and P(hitting the floor or becoming unable to trade). Bold play is a reference, shown beside the ceiling (7.4) | decided; refined |
| D8 | Execution is disarmed by default and armed per session by the owner only. It has hard daily and total loss limits, a kill switch and an audit log. The owner adds trading-scope keys | decided; execution spec |
| D9 | Approach A: rules as data, a pure `decide()` kernel, and a plan simulator | decided |
| D10 | Grey venues other than OKX (Binance, Bybit, Bitget, Hyperliquid, pump.fun, Jupiter, Uniswap), and the lawful but non-trading Betman, Lotto and Speed-On, are `out_of_scope` (blocked). Enabling one needs a reviewed `grey` row | follows D2/D6 |
| D11 | **Exits stay open.** Stale rows, auto-off, unmet gates, caps and out-of-scope or hard-block venue rows block **new exposure only**. Closing a position is still allowed, and so is withdrawing to an FIU-registered domestic exchange at a registered address. Conduct rows still apply. **If owner state is corrupt,** automated closing orders use the last approved stored snapshot, and withdrawals are done manually by the owner in the exchange app | decided 2026-10-23 |
| D12 | Limits and caps **tighten at once and loosen slowly**: only from the next Asia/Seoul date, never inside an armed session, and never after a recorded halt | decided 2026-10-23 |
| D13 | The "tested edge" column shows only a **replay of the exact validated strategy**: `S_C3_crypto_trend_krwbtc`, the long/flat crypto trend on KRW-BTC, with its own timing and costs. It is re-created and re-verified first. A changed coin, rule or timing needs a new validation, and until then no tested edge is shown | decided 2026-10-23 |
| D14 | **Owner-only writes are signed.** An Ed25519 key is unlocked only by a passphrase typed in the owner's **own** terminal, not Claude's terminal panel. The gate verifies entries with the public key, so no script can forge an entry without the passphrase. A console confirmation with a retyped code stays as the UX. The honest limit: anyone who can edit the code could disable checks, so the gate refuses new exposure until the owner signs the current code hash of `core/compliance` and `core/odds` | decided 2026-10-23 |
| D15 | **No credit buying and no coin lending or borrowing.** This is owner policy, stricter than the law. Both are `out_of_scope` and are kept out of the strategies spec as well | decided 2026-10-23 |
| D16 | Short selling, leveraged and single-stock ETPs, KRX derivatives and ELW are **refused until live broker evidence exists**: real current cash and the broker's own answers, which the execution spec adds. Owner snapshots are not accepted as evidence | decided 2026-10-23 |

## 3. The honest numbers, up front

The first five points are mathematics, checked by direct computation on 2026-10-23. The rest are research estimates and
base rates, labelled as such.

- **The ceiling.** Suppose every trade has zero or negative expected value after costs at every point where it can be
  placed, and losses stop at the account balance. Then wealth is a non-negative supermartingale, and by optional
  stopping P(ever reaching T) ≤ W₀/T for every strategy. For KRW 42,000 → KRW 42,000,000 that is **0.1% (1 in 1,000)**.
- **With a floor that truly holds.** If no outcome can take equity below L_min, the bound is (W₀ − L_min)/(T − L_min).
  - TRADEGEN only claims L_min = L under **floor-safe sizing**, where cash never falls below L plus reserved exit costs,
    so even a total loss of the position leaves L.
  - With L at half the stake, that is **0.050%**.
  - Under stop-based sizing, gaps and limit-down locks can carry losses past L, so the honest bound is W₀/T.
- **Bold play (Dubins–Savage), the even-money benchmark.**
  - Exact P(1,000×): **0.1000%** at p = 0.50, **0.0816%** at 0.49, **0.0346%** at 0.45 and **0.0106%** at 0.40.
  - With a floor at half the stake: 0.0400% at p = 0.49.
  - It loses the stake in more than 99.9% of months.
  - It is the optimum for that benchmark game. It is not a universal rule for every market.
- **KRX.**
  - A KRX position bought at the first open and held is capped by the ±30% daily band at (1.3/0.7)·1.3ⁿ⁻¹ over n
    sessions. A 30-day window holds 18 to 22 sessions, so the cap is **about 161× to 459×**. A buy-and-hold KRX plan
    cannot reach 1,000×.
  - The band is measured from each day's reference price. Repeated intraday round trips from limit-down to limit-up
    (about 1.86× a session), IPO days and special reference-price regimes are **not** bounded this way.
  - The research rates that route as "essentially zero" in practice, because surveillance designations halt such runs.
    That is not a mathematical impossibility (report line 165).
- **Kelly** aims at long-run growth, not at reaching a target by a deadline. With zero edge it bets nothing. A genuine
  52.5% even-money edge needs about **5,524 bets** to grow 1,000×.
- **Typical versus average.**
  - With no edge, the average ending equity is the stake minus costs, because rare jackpots offset the many losses.
  - The typical (median) moonshot month ends at the floor: bold play does so in 99.95% of months.
  - Every card shows the typical result first.
- **Research estimates, not measurements.** The research found no measured probability for this account reaching
  1,000× in a month. Its reasoned estimates (feasibility notes):
  - about 0.01% in general;
  - roughly 0.01–0.03% for long far-out-of-the-money US options;
  - below 0.01% for domestic crypto spot.
- **Base rates,** each with its population and statistic (report line 163 and the feasibility notes):
  - Kalshi takers lost on average about 32% of the amount staked; makers lost about 10%.
  - 74–89% of EU retail CFD accounts lose money (ESMA).
  - 87.7% of Indian retail equity-derivatives traders lost in FY26 (SEBI).
  - Korean retail lost about KRW 458 billion a year on overseas derivatives, 2020 to H1 2025, with no profitable year.
  - In a 2020 study of 204,004 Korean retail accounts, 46% lost money, and 62% of new investors did.
- **Monte Carlo precision.** A 0.01% event needs about 1,000,000 simulated months to reach a 10% relative standard
  error. A 0.1% event needs about 100,000.

---

## 4. Architecture

```
core/compliance/
  kr_rules.yaml        rules table (venue rows + conduct rows; quoted dates)
  instruments.yaml     instrument map: symbol -> asset class, multiple, underlying, currency, cost book, tax basis, source
  owner_pubkey.pem     the owner's Ed25519 public key; its fingerprint is printed in every alert email
  rules.py             safe loaders; schema and vocabulary checks; hashes; immutable approved versions; CLI --check
  gate.py              decide(), permit(), verify_permit(), screen(), render_warning(); hard-coded floor   (pure)
  owner.py             owner log: signed entries (approvals, flags, caps, limits, addresses, sessions); snapshot store
  sign.py              owner-side CLI run in the owner's own terminal: key generation, passphrase unlock, signing
  alerts.py            due() (pure), alert template, Windows toast, alerts.jsonl writer CLI

core/odds/
  plan.py              Plan, Leg, Sizing (kw_only dataclasses; whitelist validation)
  bars.py              daily open/close loader built on the data clients; its own sha-manifest cache under ~/.tradegen
  venues.yaml          lot sizes, minimum orders, fee extras, KRX stock tick ladder, sources (owner-approved)
  models.py            TwoPointBootstrap, GarchT; no-edge law; edge sources; strategy replay (D13)
  simulate.py          vectorised, chunked simulator
  bold.py              ceiling, structural maximum, estimated bracket reference, exact even-money recursion
  report.py            OddsReport rendered from the sentence catalogue; flags; language guard
```

**How data flows**
1. A `Plan` goes to `gate.screen(plan, ctx)`. If any leg is blocked, the plan is refused.
2. `odds.simulate(plan, screening, cal, limits, ...)` refuses an unscreened plan and produces an `OddsReport`.
3. Execution, in its own spec, calls `permit(intent, ctx)` and, at send time, `verify_permit(permit, intent, ctx_now)`.

**Repository facts the design rests on** (verified 2026-10-23; GPT's verification record is in Appendix C)
- **No `core.engine.orders` import.** The odds engine never imports it, because T-RO-01 allows only `core/engine/` and
  two skills modules, and `test_s4` keeps `orders.py` add-only. So:
  - KRX limits are applied by the odds engine itself, from `kr_regime_tags.yaml`'s dated `price_limit` through
    `core.calendars.regime_tags`. That call is KR-only; US and crypto legs have no daily limit.
  - The KRX stock tick ladder lives in `venues.yaml`.
  - `LIMIT_DOWN_CARRY_COST_MULTIPLIER = 2.0` is declared locally, and a test asserts it equals the orders constant.
- **Bars.** `History` holds closes only, so `core/odds/bars.py` loads daily (open, close) bars:
  - KRX: KIS daily rows;
  - Upbit KRW-* and Binance *USDT: `data.crypto` Candles;
  - US: yfinance.
  - US and FX bars are mapped to the Asia/Seoul date of their close.
  - `History` and its loaders are unchanged.
- **Calendars.** The shipped calendar and regime files are unsigned drafts, so `simulate()` takes `cal: CalendarSet`
  and refuses KRX and US legs with `CALENDAR_UNSIGNED` until they are signed. The full signing procedure is in
  section 11. `sessions_between` includes both endpoints. Tests use the signed fixture set in
  `tests/macro_m1_calendars.py`.
- **Costs.**
  - The approved **instrument map** names each symbol's cost book: `KRX_stock_book`, `KRX_ETF_line`, `US_shares_KIS`,
    `crypto_venue`, or a new `KONEX_stock_book`. The base per-side rate is `instruments.cost_per_side(book).bp` with
    `price=None`.
  - Symbol-shape inference (`validate.cost_class`) is not used, because it costs unlisted ETFs as stocks.
  - Extras in `venues.yaml` may only raise costs, under the odds engine's own `check_extras` rule.
  - The buy and sell sides are separate: κ_b and κ_s per side, the sell tax only where the book's `tax_side` says
    `sell`, and fixed charges φ_b and φ_s.
- **Provenance.** The record carries `gate_ledger.repo_anchor()` (`git:<sha>`, packed-refs aware) and
  `macro_artifacts.tree_hash()`, which covers `core/**`, `data/macro/**` and `config.py` only. A separate sha256 of
  `core/compliance` and `core/odds` is the code hash the owner signs under D14.
- **Guards.**
  - The read-only scans: test_08, test_09 and T-RO-01.
  - No identifier, docstring or comment may contain an order-endpoint name or `CANO`.
  - No function or method may be named `transfer`, `withdraw` or `deposit_address`.
  - `core.odds.` and `core.compliance.` are added to `context_log.ACTING_MODULE_PREFIXES` (T-CTX-01).
- **Isolation residual (task A0 of the compliance plan).**
  - Every writer reached by the reused loaders checks its **final** target with `refuse_quantgen` immediately before
    opening it, temp and sidecar files included. That covers the KIS token, the OpenDART cache, `history._cached`, the
    FICC cache, the grokteam cache and the new bars cache.
  - `state_root()` refuses once per process if any entry under `~/.tradegen` is a symlink, a junction or a hard link
    (st_nlink > 1).
  - This is path discipline, not a security boundary against a hostile local user.

---

## 5. Rules, instruments and approvals

### 5.1 Vocabulary

An intent is described along five independent axes:
- **Venue:** an exact lower-case id.
- **Asset class:** what is held, taken from the instrument map.
- **Action:** what is done.
- **Financing:** how it is paid for.
- **Product multiple:** taken from the instrument map.

**Venue ids.**
- Domestic brokers and exchanges: `kis`, `upbit`, `bithumb`, `coinone`, `korbit`, `gopax`.
- Offshore exchanges: `okx`, `binance`, `bybit`, `bitget`.
- DEXes: `hyperliquid`, `pumpfun`, `jupiter`, `uniswap`, `drift`.
- Prediction markets: `polymarket`, `kalshi`, `limitless`, `myriad`, `opinion`, `predictfun`.
- Retail apps with prediction markets: `robinhood`, `cryptocom`, `predictit`.
- Betting and lotteries: `sportsbook`, `betman`, `lotto`, `speedon`.
- Foreign brokers: `ibkr`, `moomoo`, `webull`, `etoro`, `offshore_fx_cfd`.
- The state-blocked ids, plus `bitmart`.
- Anything else is unknown, which means BLOCK.

**Asset classes.**
- KRX: `krx_share`, `konex_share`, `krx_etp` (multiple and underlying come from the map), `krx_derivative`
  (stage 1: futures and long options; stage 2: option writing and VKOSPI futures; the stage comes from the action and
  the contract type), `elw`.
- US: `us_share`, `us_etp`, `us_option`, `us_crypto_spot_etp`.
- Futures and derivatives: `overseas_future`, `overseas_crypto_derivative`.
- Crypto: `crypto_coin`, `crypto_perp_or_future`.
- Other: `fx_pair`, `cfd`, `event_contract`, `sports_bet`, `lottery`.

**Actions.**
- Trading: `buy`, `sell`, `sell_short`, `buy_to_cover`.
- Options: `write`.
- Transfers: `transfer_out`.
- Lending: `lend`, `borrow`.
- P2P: `p2p_buy`, `p2p_sell`.

**Financing.** `cash`, `credit`, `margin`.

**Derived classes,** from the map:
- `krx_etp` or `us_etp` with multiple +1 is the **1x ETF/ETN**.
- With multiple −1 on an index or basket underlying, it is the **index inverse**.
- With any other multiple on an index or basket underlying, it is the **index leveraged ETP**.
- With any multiple other than +1 on a **single** underlying, including −1, domestic or overseas-listed, it is the
  **single-stock ETP**.
- `us_etp` on a crypto **futures** underlying, for example BITO, is a **crypto-futures ETF**. The FSC distinguished
  these and preserved trading in existing overseas bitcoin-futures ETFs.
- `us_crypto_spot_etp` covers the spot-backed products: IBIT, FBTC, ETHA, GDLC, EZPZ and the like.

**The instrument map** (`instruments.yaml`, owner-approved).
- **Contents:** each symbol maps to its asset class, multiple, underlying kind (single | index | basket | crypto_spot |
  crypto_futures), currency, cost book, tax basis and a source, all under the same review rules as the table.
- **Lookups:** the gate looks up `intent.symbol`.
  - An unknown symbol is BLOCK.
  - A caller-supplied class or multiple that disagrees with the map is BLOCK.
  - Effective leverage is derived from the product multiple and the financing; the caller's own value is never trusted.
- **Transfers** name the coin as the symbol (`crypto_coin`) with action `transfer_out`. They do not need a separate
  class.

### 5.2 Row schema and table rules

```yaml
schema: tradegen.kr_rules/3
scope: "Korean-resident individual, own funds only"
known_changes: ["2026-12-03", "2027-01-01", "2027-02-18"]
rows:
  - id: KR-OKX-SPOT
    kind: venue                                   # venue | conduct
    match: {venue: [okx], asset: [crypto_coin], action: [buy, sell], financing: [cash]}
    treatment: grey                               # hard_block | gated | grey | allow | out_of_scope
    requires: {owner: [age_of_majority]}
    ack: per_session
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
    confidence: low
    legal_or_policy: legal                        # legal = a legal reading; policy = the owner's stricter choice
    effective_from: "2021-03-25"
    effective_until: "2027-02-18"
    review_by: "2026-11-22"
    reviews: [{date: "2026-10-23", by: claude-research, checked: "report rows 13-15, 19; crypto notes section 3"}]
```

**Loading**
- The loader uses a SafeLoader subclass that rejects duplicate keys, anchors, aliases and native dates.
- The file is capped at 256 KB.
- Every `match` value must belong to the vocabulary, and `any` is allowed only on `hard_block`, `out_of_scope` and
  conduct rows.
- Any violation makes the table INVALID.
- `instruments.yaml` and `venues.yaml` get the same treatment.

**Sources and review**
- Every row cites a source and its research, and carries `legal_or_policy`. Policy rows say so in their owner-facing
  reason.
- The review cadence is **monthly**: `review_by` is at most 31 days after the latest review, and no later than the day
  before the next `known_changes` date that affects the row.
- All 38 legality-matrix rows must be covered.

**Approval (D14)**
- A table, map or venue file counts only if the owner log holds a **signed** `approved {kind, sha256}` for those exact
  bytes.
- `rules.py` keeps every approved version immutably in `~/.tradegen/compliance/approved/<kind>/<sha256>`, so a snapshot
  can be reconstructed.
- A git commit is not approval, because Claude makes this repo's commits under the owner's identity.
- A `reviews` entry by anyone but the owner is a draft.

**Hard-coded floor.** `gate.py` blocks the following whatever the table says:
- the conduct classes and tags;
- the prediction and sportsbook venues;
- the state-blocked ids;
- OKX derivatives and P2P;
- `fx_pair`, `cfd`, `overseas_future`, `overseas_crypto_derivative`, `us_crypto_spot_etp` and `us_option` + `write`.

### 5.3 Seed rows

The report's "Recommended actions" table sets each treatment, except where owner policy (D10, D15, D16) is stricter.

| Row id | Match (venue: asset / action / financing) | Treatment | Basis | Matrix row |
|---|---|---|---|---|
| KR-KIS-KRX-SHARE | kis: krx_share / buy, sell / cash | allow (±30% band; 0.20% sell tax) | legal | 21 |
| KR-KIS-KONEX | kis: konex_share / buy, sell / cash | allow (±15% band; 0.10% tax) | legal | 21 |
| KR-KIS-KRX-1X | kis: krx_etp (1x) / buy, sell / cash | allow | legal | 21 |
| KR-KIS-KRX-INVERSE | kis: krx_etp (index inverse −1x) / buy, sell / cash | allow; confidence low (confirm with the broker) | legal | 22 |
| KR-KIS-KRX-LEV | kis: krx_etp (index leveraged) / buy | gated; **refused until live evidence (D16)**: deposit ≥ KRW 10M and `kofia_leveraged_1h` | policy (D16) + legal | 25 |
| KR-KIS-SINGLE-ETP | kis: krx_etp, us_etp (single-stock) / buy | gated; **refused until live evidence (D16)**: cash ≥ KRW 30M, cash only, before every buy, + 3h course + 5h mock over 5 days | policy (D16) + legal | 26 |
| KR-KIS-KRX-DERIV | kis: krx_derivative / any | gated; **refused until live evidence (D16)**: stage 1 KRW 10M / stage 2 KRW 20M + broker eligibility | policy (D16) + legal | 27 |
| KR-KIS-ELW | kis: elw / any | gated; **refused until live evidence (D16)**: KRW 15M + course | policy (D16) + legal | 28 |
| KR-KIS-CREDIT | kis: any / buy / credit | out_of_scope (**D15: no credit buying**) | policy | 23 |
| KR-KIS-SHORT | kis: krx_share / sell_short | gated; **refused until live evidence (D16)**: 30m KOFIA + 1h KRX mock + broker approval; 105% collateral | policy (D16) + legal | 24 |
| KR-KIS-US-SHARE | kis: us_share, us_etp (1x) / buy, sell / cash | allow | legal | 31 |
| KR-KIS-US-INVERSE | kis: us_etp (index inverse −1x) / buy, sell / cash | allow; confidence low (broker notices) | legal | 33 |
| KR-KIS-US-LEV | kis: us_etp (index leveraged) / buy | gated; **refused until live evidence (D16)**: KRW 10M + `kofia_leveraged_1h` (since 2026-05-22) | policy (D16) + legal | 32 |
| KR-KIS-US-CRYPTO-FUT-ETF | kis: us_etp (crypto_futures, 1x) / buy, sell / cash | allow; confidence low. The FSC preserved existing overseas bitcoin-futures ETF trading; review monthly | legal | crypto notes Q4 |
| KR-KIS-US-CRYPTO-SPOT-ETP | kis: us_crypto_spot_etp / buy | hard_block. FSC January 2024: brokering overseas spot crypto ETFs may breach the FSCMA. The FSS halted GDLC/EZPZ in November 2025 | legal | crypto notes Q4 |
| KR-KIS-US-OPTION | kis: us_option / buy, sell | gated; per-session acknowledgement; broker eligibility (at least 1h + 3h); commissions of 3–20% of the account per side. The odds engine refuses option legs | legal | 34 |
| KR-KIS-US-OPTION-WRITE | kis: us_option / write | hard_block (recourse leverage) | legal | 34 |
| KR-KIS-CRYPTO-DERIV | kis: overseas_crypto_derivative / any | hard_block (FSC 2017-12-06) | legal | crypto notes Q4 |
| KR-KIS-OVERSEAS-FUT / FX / CFD | kis: overseas_future, fx_pair, cfd / any | hard_block | legal | 35, 29, 30 |
| KR-DOMESTIC-SPOT | upbit, bithumb, coinone, korbit: crypto_coin / buy, sell / cash | allow (KRW 5,000 minimum on Upbit) | legal | 10 |
| KR-GOPAX | gopax: any | out_of_scope (VASP renewal status unverified; not configured) | policy | 10 |
| KR-DOMESTIC-LENDING | upbit, bithumb, coinone, korbit: crypto_coin / lend, borrow | out_of_scope (**D15: no coin lending**) | policy | 11 |
| KR-DOMESTIC-CRYPTO-DERIV | upbit, bithumb, coinone, korbit: crypto_perp_or_future / any | hard_block (no legal framework) | legal | 12 |
| KR-TRANSFER-OUT | upbit, bithumb, coinone, korbit: crypto_coin / transfer_out | allow only to a destination that is allowed or grey (6.2), at a signed registered address. A grey destination needs a per-transfer acknowledgement. `effective_until: "2027-02-18"` | legal | 19 |
| KR-OKX-SPOT | okx: crypto_coin / buy, sell / cash | grey (D6), example in 5.2 | legal | 14 (13 analogue) |
| KR-OKX-WITHDRAW | okx: crypto_coin / transfer_out | exit only (D11): to upbit, bithumb, coinone or korbit at a registered address | legal | 14, 19 |
| KR-OKX-DERIV / P2P | okx: crypto_perp_or_future / any; okx: any / p2p_buy, p2p_sell | hard_block (OKX blocks South Korea) | legal | 14 |
| KR-OFFSHORE-CEX | binance, bybit, bitget: any | out_of_scope (D10) | policy | 13 |
| KR-STATE-BLOCKED | kucoin, mexc, phemex, xtcom, bitrue, coinw, poloniex, btcc, bingx, digifinex, + every other site on the KCSC block list of 2026-10-13: any | hard_block (reachable only by VPN) | legal | 15 |
| KR-BITMART | bitmart: any | hard_block (Google Play app block 2025-03; Korean reports of the 2026-10-13 block do not name it) | legal | 15 |
| KR-HYPERLIQUID / KR-DEX / KR-DRIFT | hyperliquid, pumpfun, jupiter, uniswap, drift: any except event_contract | out_of_scope (D10). Enabling needs: age 19+; no auto-buy of new tokens; a liquidation-price warning on perps | policy | 16, 17, 18 |
| KR-PREDICTION | polymarket, kalshi, limitless, myriad, opinion, predictfun, robinhood, cryptocom, predictit: any; any venue: event_contract | hard_block (Criminal Act Art. 246; platform terms) | legal | 1-6 |
| KR-SPORTS | sportsbook: any; any venue except betman: sports_bet | hard_block (National Sports Promotion Act Art. 26, 48(3); 2022도6462) | legal | 3, 7 |
| KR-IBKR / KR-RETAIL-APPS / KR-OFFSHORE-FX-CFD | ibkr; moomoo, webull, etoro; offshore_fx_cfd: any | hard_block | legal | 36, 37, 38 |
| KR-LOTTERY-RACING | betman, lotto, speedon: any | out_of_scope (D10) | policy | 8, 9 |
| KR-CONDUCT-ROUTE | route ≠ direct | hard_block | legal | 15, 16 |
| KR-CONDUCT-OTHERS | on_behalf ≠ self, or tag copy_lead / copy_follow | hard_block (특금법; 2024도10710) | legal | 20 |
| KR-CONDUCT-FX | tag fx_settlement | hard_block (환치기, where business-like) | legal | 20 |
| KR-CONDUCT-SIGNALS | publishes_signal | hard_block | legal | 20 |
| KR-CONDUCT-PROMOTE | tag unregistered_vasp_referral | hard_block (FSC 2026-06-24). TRADEGEN stores and emits no referral, affiliate or invite codes | legal | 20 |
| KR-CONDUCT-MANIP | tags coordinated, self_match, spoof, layer, mnpi, false_statement, self_issued_coin | hard_block (VAUPA Art. 10(1)–(5)) | legal | 20 |

**Dates**
- Crypto, transfer and OKX rows are due by 2026-11-22, and in no case later than 2026-12-02.
- `KR-TRANSFER-OUT` and `KR-OKX-SPOT` end on 2027-02-18, when the travel-rule expansion takes effect: six months after
  promulgation, per FSC 2026-08-11 (the promulgation date is secondary-sourced).
- Every other row follows the monthly cadence.

### 5.4 Lifecycle and alerts

- **Stale rows.** A row past `review_by` blocks new exposure with "stale: review by … passed". Exits stay open (D11).
- **Re-review.** Someone drafts a `reviews` entry, possibly Claude. The owner signs `approved` for the new bytes. Until
  then the previous approved version stays in force. If no version was ever approved, the table is INVALID.
- **`python -m core.compliance.rules --check [--today …]`** checks the table, the map and the venue file; their
  approvals; the owner-log chain and signatures; the signed code hash; and the public-key fingerprint. Exit codes:
  - 0: nothing due;
  - 1: something due within 14 days;
  - 2: something overdue;
  - 3: invalid, unapproved, unsigned code, a broken chain or a changed key. Exit 3 blocks new exposure.
- **Who sends what.**
  - `alerts.py` renders a fixed template: row id, `review_by`, `auto_off`, days left, the owner-log head and the
    key fingerprint. Rule free text is never interpolated.
  - It shows the Windows toast (PowerShell WinRT, no new dependency).
  - It writes `alerts.jsonl` through `--log <channel> <ok|fail>`.
- **The daily job.** A local scheduled Claude task runs at 09:00 KST:
  - it runs `--check`;
  - it alerts every day while anything is overdue or exit code 3 holds;
  - for a row due soon, it alerts on the first run at or below 14 days, and again at or below 3 days;
  - it sends the iOS push via the Claude app and an email **only to `sapientia@korea.ac.kr`**, written literally in the
    task prompt and in `alerts.OWNER_ALERT_EMAIL`;
  - it records each result through `--log`.
- **Authority.** The owner approves the task once; D5 is the standing authority for these self-addressed alerts only.
- **Failures and the in-app banner.** A failed channel is announced on the others. The in-app banner and an app-start
  check cover the times the PC was off.

---

## 6. The `decide()` kernel (`core/compliance/gate.py`)

### 6.1 Types

```python
@dataclass(frozen=True, kw_only=True)
class Intent:
    venue: str
    symbol: str                      # every intent names a mapped symbol (coins included, for transfers)
    asset: str                       # caller's asset class; must equal the map's
    multiple: float                  # caller's product multiple; must equal the map's
    action: str                      # buy | sell | sell_short | buy_to_cover | write | transfer_out | lend | borrow | p2p_buy | p2p_sell
    financing: str = "cash"          # cash | credit | margin
    quantity: float                  # units (> 0)
    notional_krw: float              # >= 0, finite
    closes_position: bool = False    # caller's claim; checked against ctx.holdings
    destination_venue: str | None = None     # transfer_out only
    destination_address: str | None = None   # transfer_out only; must be signed-registered
    route: str = "direct"
    on_behalf: str = "self"
    publishes_signal: bool = False
    tags: frozenset = frozenset()
    reservation_id: str | None = None        # set by execution for permits (6.3)

@dataclass(frozen=True, kw_only=True)
class Context:
    date: date                       # Asia/Seoul calendar date of the decision moment (never UTC, never a trade date)
    state: ApprovedState             # current approved rules, map and venues; RulesTable.invalid(reason) on any failure
    snapshot: ApprovedState | None   # last approved immutable snapshot (exits under D11 recovery)
    owner: OwnerState                # verified owner log: signed flags, caps, limits, addresses, sessions; or BROKEN
    code_signed: bool                # the owner signed the current sha256 of core/compliance + core/odds (D14)
    session: SessionState            # session_id; acknowledgements bound to warning hashes
    equity_krw: float                # > 0, finite
    holdings: Mapping[tuple, float]  # (venue, symbol) -> units held, >= 0 (short positions listed separately, >= 0)
    exposure: Mapping[str, Exposure] # per venue: filled >= 0, reservations {reservation_id: notional >= 0}
    designations: Mapping[str, str]  # symbol -> KRX designation (credit is out of scope; kept for later specs)
```

`Decision`, with verdicts ALLOW | ALLOW_EXIT | ACK_REQUIRED | BLOCK:
- the reasons, as (row_id, catalogue id, slots), strictest first;
- `intent_hash`, `state_hash`, `ctx_hash`, `owner_head`, `date`, `decision_id`.

`Permit`, issued only from ALLOW or ALLOW_EXIT:
- `decision_id`, `intent_hash`, `state_hash`, `session_id`, `reservation_id`, `date`.

### 6.2 Evaluation order (one decision table)

1. **Validate the intent.** Any of the following gives `BLOCK ("malformed: <field>")`:
   - a field that is non-finite, negative where it must be non-negative, of the wrong type, or not exactly a vocabulary
     member;
   - an unknown symbol;
   - an asset or multiple that disagrees with the map;
   - an inconsistent `action`, `destination_venue` and `destination_address` (`transfer_out` needs both destination
     fields, and the destination must differ from `venue`; other actions must have neither);
   - tags outside the vocabulary.

   The kernel never raises; any internal error is BLOCK.
2. **Conduct rows and the hard-coded conduct floor** apply on every venue and to every intent, exits included.
3. **Classify the intent:**
   - **close-long:** a `sell` with `closes_position`, quantity ≤ `holdings[(venue, symbol)]`, and lower exposure after;
   - **cover-short:** a `buy_to_cover` with quantity ≤ the short held;
   - **withdraw:** a `transfer_out` to a domestic venue whose row is `allow`, at a registered address, with quantity ≤
     holdings;
   - **new exposure:** everything else.
4. **Exits (D11).** They give `ALLOW_EXIT` with warnings, and are **not** blocked by:
   - stale rows, auto-off, unmet gates, caps or D16;
   - out-of-scope or hard-block venue rows.

   Conduct (step 2) still applies. **Which state:**
   - Close-long and cover-short use `ctx.state` if it is valid, and otherwise `ctx.snapshot`.
   - A withdrawal needs a valid `ctx.state` and a valid owner log, because the address must be verifiable.
   - If owner state is broken, a withdrawal is BLOCK with "withdraw manually in the exchange app".
   - If there is no snapshot either, closing orders are BLOCK with "close manually in the broker app". The owner can
     always exit outside TRADEGEN.
5. **New exposure** requires all three of:
   - a valid `ctx.state`;
   - a valid owner log;
   - `code_signed`.

   Otherwise BLOCK. Then the venue rows: only rows in force on `ctx.date` count (Asia/Seoul dates; `effective_from ≤
   date`, and `effective_until` null or later than `date`).
   - **No matching row:** BLOCK. When several rows match, all apply, and the strictest wins.
   - **stale**, **`hard_block`** or **`out_of_scope`**: BLOCK.
   - **`gated`** with D16 in force: BLOCK, "needs live broker evidence (execution spec)". Other gated rows need every
     `requires` item to be met by signed owner state.
   - **`grey`:**
     - BLOCK if `date ≥ auto_off`, the cap is unset, or `requires` is unmet;
     - BLOCK if filled exposure, plus the other reservations, plus this notional exceeds `cap × equity`. Only the
       reservation carrying this intent's own `reservation_id` is excluded when verifying a permit.
   - **`ack: per_session`:** ACK_REQUIRED unless `ctx.session` holds an acknowledgement for the row, with
     `warning_sha256 == sha256(render_warning(row, slots))`, under the current `session_id`.
   - **`allow`:** ALLOW.
   - **Leverage:** effective leverage (multiple × financing) above the row's `max_leverage` is BLOCK.
6. **Transfers.** The destination is evaluated as a `buy` of the same symbol on `destination_venue`; the stricter result
   wins.
   - A grey destination also needs a per-transfer acknowledgement against the intent hash.
   - An unregistered address is BLOCK. Below KRW 1M, before about 2027-02-18, exchanges need not match names, so the
     signed address registry is the guard.
7. **Combine.** BLOCK beats ACK_REQUIRED, which beats ALLOW and ALLOW_EXIT.

### 6.3 Permits and plan screening

- **`permit(intent, ctx)`** calls `decide()` and issues a `Permit` only for ALLOW or ALLOW_EXIT.
- **`verify_permit(permit, intent, ctx_now)`** recomputes:
  - `intent_hash(intent) == permit.intent_hash`;
  - `decide(intent, ctx_now)` is ALLOW or ALLOW_EXIT;
  - the same `session_id`, `reservation_id` and Asia/Seoul date;
  - `state_hash` equal to the issue-time hash or to a newer **approved** state.

  A permit expires at 24:00 Asia/Seoul. Atomic reservation, single use and the audit log belong to the execution spec.
- **`screen(plan, ctx)`** decides the plan's single leg as a `buy` at the leg's first stake, after the 7.1 cuts
  including the grey cap.
  - It scans `[start, start + horizon]` for any `review_by`, `auto_off` or `effective_until`. Each one found is flagged
    `RULE_CHANGE_IN_HORIZON`, and the simulation exits on that date, or at the next check point when the date falls on a
    non-session day.
  - It returns a hashed `Screening`.

### 6.4 The owner log, signing and snapshots

- **The log.** `~/.tradegen/compliance/owner.jsonl` is append-only. Each line carries `prev_sha256`, `row_sha256` and
  `sig`, an Ed25519 signature over the row by the owner key.
  - Unsigned or badly signed lines make the log **BROKEN**.
  - **Head anchoring:** every Decision's `owner_head`, every `alerts.jsonl` row and every daily alert email record the
    head. A log shorter than, or different from, the highest recorded head is BROKEN.
- **Signing (D14).** `python -m core.compliance.sign <command>` is run **by the owner, in the owner's own Windows
  Terminal**, never in the Claude app's terminal panel, which Claude can read.
  - It generates the key, stored as `~/.tradegen/compliance/owner_key.enc`: the private key encrypted with a passphrase
    via scrypt, then sealed with AES-GCM.
  - It writes `core/compliance/owner_pubkey.pem`.
  - It shows exactly what will be signed, with a fresh random code that must be retyped, refuses non-TTY stdin, and
    asks for the passphrase.
  - **Claude never runs it, never asks for the passphrase, and never writes owner entries.**
- **Key changes.** The public-key fingerprint appears in every alert email. Rotating the key requires a signature by the
  old key, and an unexplained change is exit 3.
- **The code hash.** The owner also signs `code_approved {sha256}`. If the code changes, new exposure is BLOCK until the
  owner signs again. The hash covers:
  - `core/compliance` and `core/odds`;
  - their **in-repo import closure**, found by an AST import scan: for example `config.py`, `core/isolation.py`,
    `core/calendars/**`, the `core/quant` and `data/` modules they reach;
  - the scan's output, so the signing prompt lists every file covered.
- **The honest limit.** A process with the owner's file access could still edit the verifier itself. The owner's review
  of every diff to these two packages is the remaining boundary, and the plan makes that review a step of its own.
- **The dependency.** The Python `cryptography` package (Ed25519, scrypt, AES-GCM) is installed into `.venv` only and
  pinned in `constraints.txt`.
- **Events:**
  - approvals: `approved {kind, sha256}`, `code_approved {sha256}`;
  - evidence: `course_completed`, `broker_approval`, `age_of_majority {birth_date, evidence}`;
  - settings: `cap_set {key, value}`, `limit_set {total_loss_floor_krw, daily_loss_krw}`;
  - transfers: `withdrawal_address {venue, symbol, address, evidence}`;
  - sessions: `session_armed`, `session_disarmed`, `session_ack {session_id, row_id, warning_sha256}`, and
    `transfer_ack {intent_hash, warning_sha256}`.
  - Deposit and cash snapshots are not accepted as evidence (D16).
- **D12.** Tightening takes effect immediately. Loosening takes effect only from the next Asia/Seoul date, never inside
  an armed session, and never after a recorded halt for that floor.
- **Snapshot (D11 recovery).** After every successful verification, `owner.py` stores the resolved owner state and the
  approved state hashes as an immutable snapshot. Exits under a broken log use the last one.
- **Unset limits.** While `total_loss_floor_krw` (0 ≤ L < stake) or `daily_loss_krw` is unset, the odds engine refuses
  with `LIMITS_UNSET`. `owner.py` resolves `Plan.limits`, and `simulate()` never reads the log itself.

---

## 7. The odds engine (`core/odds/`)

### 7.1 Plans and stakes

```python
@dataclass(frozen=True, kw_only=True)
class Leg:
    venue: str; symbol: str          # whitelist: krx_share, krx_etp (1x), us_share, us_etp (1x), crypto_coin; cash; long
    model: str                       # "bootstrap" (TwoPointBootstrap) | "garch_t" (US and crypto only)
    bracket: Bracket | None = None   # take-profit +u, stop -d; None = buy at the first open and hold
    sizing: str                      # "floor_safe" (default) | "stop_based"
    edge_source: str = "none"        # "none" | "assumed" (bracket legs) | "replay:S_C3_crypto_trend_krwbtc" (D13)
    assumed_p: float | None = None

@dataclass(frozen=True, kw_only=True)
class Plan:
    name: str                        # cosmetic; never hashed into a seed
    track: str                       # "moonshot" | "compounding"
    stake_krw: float; target_krw: float     # target before income tax, fixed in KRW
    fx_krw_per_usd: float            # recorded close used to fix the target (US legs)
    start: date; horizon_days: int
    leg: Leg
    fraction: Fraction               # fixed(f) | kelly(c <= 0.5) | bold()
```

**The cost ledger.**
- Buying s of notional costs s(1 + κ_b) + φ_b in cash.
- Selling a position worth v returns v(1 − κ_s) − φ_s.
- κ_s includes the sell tax only where the cost book's `tax_side` is `sell`.

**Affordability.** For every entry, after lot rounding and under each cost scenario (1× and 2×):
- **always:** s(1 + κ_b) + φ_b ≤ W;
- **floor-safe** (the default): s(1 + κ_b) + φ_b + R_exit ≤ W − L. Cash never falls below L plus the reserved exit
  charge, so even a total loss of the position leaves L, and **L_min = L** (7.4).
  - R_exit is the **worst-case** exit charge: m_stress × m_carry × φ_s, with m_stress = 2 for the 2× cost scenario and
    m_carry = 2 for the limit-down carry.
  - This needs m_stress × m_carry × κ_s < 1, so the proportional charge can never exceed the position's value; a book
    where that fails is refused;
- **stop-based** (bracket legs only): s[d + κ_b + κ_s(1 − d)] + φ_b + φ_s ≤ W − L before gaps, with **L_min = 0**.

**Fractions**
- `fixed(f)`: s = f·W, then cut by affordability.
- `kelly(c)`: only in the D13 replay column (7.2). c·f*, with f* = argmax E[ln(1 + f·R_net)] on the conservative return
  distribution. That distribution is the replayed net daily returns shifted so their mean equals the lower 95% bound of
  the mean, times `LIVE_SHARPE_MULTIPLIER`. Zero exposure if conservative growth ≤ 0. Labelled "aims at long-run
  growth, not at reaching your target".
- `bold()` (bracket legs): s = min(s_reach, s_afford).
  - s_reach is the smallest stake whose win reaches T net of costs: s(u − κ_b − κ_s(1 + u)) − φ_b − φ_s = T − W.
  - s_afford is the largest stake the affordability rules allow.
  - When one win cannot reach T (s_reach > s_afford), bold play stakes s_afford and tries again after a win, as
    Dubins–Savage bold play does far from the goal.
  - Lot rounding is downward.
- **A bold fraction is refused** when the net win coefficient u − κ_b − κ_s(1 + u) is ≤ 0, or no affordable stake
  exists.

**Rounding.** Stakes round **down** to whole units, or to fractional units where `venues.yaml` allows. A stake below the
venue minimum means no bet; it is never rounded up.

**Refused with named reasons:**
- a leg outside the whitelist, a multiple ≠ +1, or a short, credit or option leg: `UNSUPPORTED_PRODUCT`;
- multi-leg plans: `MULTI_LEG_UNSUPPORTED`;
- unset limits: `LIMITS_UNSET`;
- an unsigned calendar for a KRX or US leg: `CALENDAR_UNSIGNED`;
- a GARCH-t model on a KRX leg: `MODEL_NOT_FOR_LIMITED_VENUE`.

### 7.2 The no-edge law, models and edge sources

**No edge means a conditional martingale at every point where the simulator can act:** each session's open and close.
Given everything so far, the expected next price equals the current one. Costs then make every trade's expectation
negative. Two traps ruled out in review:
- zero log drift is not zero edge;
- per-row demeaning of a block bootstrap lets timing rules harvest historical serial patterns.

**`TwoPointBootstrap`** (the primary model; KRX, US and crypto legs):
- **Price series.** Each leg's price series is in KRW: price × KRW=X for US legs, aligned to the Asia/Seoul close date;
  Binance BTCUSDT × Upbit KRW-USDT for OKX legs.
- **Moves.** From each historical session the model takes two magnitudes:
  - the overnight move, m_o = |ln(open / previous close)|;
  - the intraday move, m_i = |ln(close / open)|.
- **Blocks.** Rows are drawn in stationary-bootstrap blocks (`pw_block(x, kind="stationary")`, with mean length the
  maximum over r and r²), so volatility clustering survives through the magnitudes.
- **The kernel.** At each check point with current price p, the next check's price is one of two values:
  - x_u = min(p·e^{m}, U) with probability q;
  - x_d = max(p·e^{−m}, D) with probability 1 − q;
  - q = (p − x_d)/(x_u − x_d), and when x_u = x_d the price stays at p.
- **Bands.** [D, U] is the session's legal band, the reference price × (1 ∓ dated `price_limit`), for both check points
  of that session. Venues without a daily limit use [0, ∞).
- **Why it is exact.** E[next | p] = p holds algebraically. Prices never leave the band, and a price at a band edge stays
  there with probability 1, which a martingale bounded by that edge must do.
- **Edge sessions.** A session that **opens at its band edge stays there until the close**. This is forced: inside a
  capped band, a no-edge price that starts at the cap cannot move. Real limit-up or limit-down stocks can reverse
  intraday, so such sessions are counted and flagged `BAND_EDGE_SESSIONS`.
- **Ticks.** The band edges are rounded to the KRX tick ladder in `venues.yaml`: D up and U down, toward the reference,
  as the exchange does.
- **The reference price.** The KRX reference is the previous session's close. Special regimes (IPO days,
  reference-price resets) are not simulated; the leg refuses symbols in such a regime (flag `SPECIAL_REGIME`).
- **Limit-down.** A check at D that would exit is a limit-down lock. The exit carries to the next session at 2× cost.
- **Intraday extremes are not modelled,** so the card says "price checks at the open and the close only"
  (`CHECKS_AT_OPEN_CLOSE`). That is a limit of this construction, not a property of martingales.

**`GarchT`** (US and crypto legs only):
- It fits with `garch.fit_garch` and simulates with `simulate_returns(fit, rate_daily=0.0, bound=Z_BOUND)`.
- Checks happen at the close only (`CLOSE_ONLY_CHECKS`).
- The repo's convexity correction is numerical. The engine asserts |mean factor − 1| < 1e-9 per step on a pilot run,
  and otherwise drops the model with a note.
- If the fit falls back to unbounded normal innovations, HIDDEN_EDGE is unavailable for that model (7.5).

**Brackets** are evaluated pathwise at the check points: take-profit +u and stop −d, each filling at the check price.
Under the martingale, a bracket's mean payoff before costs is 0.

**Cash** between trades is held in KRW.

**Edge sources**
- **`none`:** the default and always the headline.
- **`assumed`** (bracket legs): the owner's typed win probability p.
  - The simulator uses an exponentially tilted kernel, q′ = q·e^{θ}/(q·e^{θ} + 1 − q), with θ found by bisection on a
    pilot run so that the bracket's simulated win rate equals p.
  - Unresolved brackets exit at market at the horizon.
  - p outside the range the tilt can reach is refused.
  - The column states the no-edge win rate p₀ of this bracket under the model, and how many recorded brackets would
    tell p from p₀: a one-sided 5% test at 80% power,
    n = ((1.645·√(p₀(1 − p₀)) + 0.842·√(p(1 − p))) / (p − p₀))². For example, 617 brackets for 55% versus 50%, and 153
    for 60%.
- **`replay:S_C3_crypto_trend_krwbtc`** (D13). This is a **separate plan type**: it replays the validated strategy itself
  and nothing else.
  - **Pure replay.** `models.replay_s_c3(bars, card)` is a pure function over **hashed, immutable** KRW-BTC bars. It
    uses the card's rules, grid, seed, protocol (in-sample 756 / out-of-sample 126, embargo 1) and 10 bp costs. It
    emits:
    - canonical out-of-sample daily net returns;
    - turnover;
    - the selected parameters;
    - the 2× stress result;
    - a fresh verdict, using `validate` functions only.
  - **No study runner.** It never imports `docs/asset_expansion_study.py`, which writes at import.
  - **Digests.** Three are recorded: the input bars, the replay output, and the aggregate `results.csv` (`results_md5`).
  - **The check.** The replay must reproduce the card (out-of-sample Sharpe within ±0.02, verdict PASS, the same
    selected parameter), or the plan is refused with `CARD_NOT_REPRODUCED`.
  - **Its column.** The simulator resamples the replayed out-of-sample net returns in stationary blocks, with the mean
    multiplied by `LIVE_SHARPE_MULTIPLIER`.
  - **Costs.** The card's 10 bp is already inside those returns. Only the incremental small-account effects are added:
    whole-unit rounding and the KRW 5,000 Upbit minimum. A venue fee above 10 bp would be added too; Upbit's KRW fee is
    below that.
  - **Kelly** uses the lower 95% bound of the out-of-sample mean, from a stationary block bootstrap with B = 2,000.
  - **The candidate card's figures:** out-of-sample Sharpe 1.22, 90% CI [0.62, 1.77], Sharpe 1.17 at 2× costs, maximum
    drawdown −49%. Its card names Yahoo as the source, while the study runner used the Upbit path. The replay pins
    which one, and records it.

**Data rules**
- `SYNTHETIC_REFUSED`; a provisional last bar is dropped.
- `PROXY_DATA` for OKX.
- Single-name and single-coin legs add a delisting stress column (`tf_books.DELIST_STRESS`), with its losses booked in
  the cost ledger.
- Series hashes are md5 of canonical JSON {symbol, source, dates, open, close, adjustment, status}.

**Costs, minimums and calendar**
- Costs come from section 4 and the cost ledger in 7.1. Every plan runs at 1× and 2× cost.
- Minimums and ticks come from `venues.yaml`. A missing entry gives `NOT_TRADABLE`.
- Steps are calendar days. KRX and US legs move on their market's sessions (`cal`); crypto moves daily.

### 7.3 Simulation and outcomes

- **Terminal outcome**, exactly one per path:
  - **REACHED:** liquidation value after exit costs and tax ≥ T. Moonshot paths stop here.
  - **FLOOR:** liquidation value ≤ L, recorded at the actual fill, overshoot kept. Absorbed.
  - **STUCK:** too little left to place any order.
  - **RUNNING:** still trading at the horizon, at liquidation value. A position whose exit is still limit-locked at the
    horizon is valued at the locked price and flagged.
- **First passage.** `reached_by_deadline` is a separate indicator: liquidation value ≥ T at some check point. For
  compounding paths it can be true while the terminal outcome is FLOOR or RUNNING.
- **The daily loss limit** is checked at the check points. A breach exits and stops trading for the rest of that day.
- **Seeds and streams.**
  - The market seed is sha256(data hashes ‖ comparison id ‖ run counter), shared by every plan in one comparison.
  - Streams are `SeedSequence(int.from_bytes(seed, "big"), spawn_key=(chunk, stream_id))`. The bootstrap index and
    sign streams are keyed by data set and chunk; the GARCH innovations by symbol.
  - Cosmetic fields are excluded, and the owner never chooses the seed.
- **Scale.** CHUNK = 200,000, and n must be a multiple of it. Defaults: 1,000,000 paths for moonshot plans and 200,000
  for compounding plans. Provenance records the NumPy version and PCG64.

### 7.4 References (`bold.py`)

- **`ceiling(W0, L_min, T)`** = (W₀ − L_min)/(T − L_min).
  - L_min = L only under floor-safe sizing (7.1), a global bound that holds across carried positions and every
    remaining session. Otherwise L_min = 0, which gives W₀/T.
  - The no-edge column always shows it and always runs the breach check. Edge columns print "Without the edge assumed
    here, no plan can beat 1 in N".
- **`structural_max(plan, cal)`** applies only to **buy-and-hold KRX or KONEX legs**: (1 + limit)/(1 − limit) ×
  (1 + limit)^{n−1} over the leg's n sessions.
  - When the target exceeds it, the card prints **"IMPOSSIBLE for this buy-and-hold plan: KRX's daily band allows at
    most N× in these S sessions"** and no probability.
  - For bracket legs, which can re-enter, no market-wide bound is claimed.
- **`bracket_reference(plan)`** is an **estimated** reference, not a certified bound. It is a dynamic programme over
  equity and check points remaining, using the simulated joint law of one bracket's (realised payoff, duration). The
  card reads "estimated: the highest chance placing this bracket could give is about X; staking boldly gives about Y,
  and hits your floor in Z% of months". It never drives a red flag.
- **`bold_even(x, p)`:** the exact even-money recursion, used in regression tests only.

### 7.5 The report

All owner-facing text comes from one reviewed **sentence catalogue** with numeric slots. Each plan card shows:

1. **The model and its check points.** "Price checks at the open and the close only", or for GARCH-t "at the close
   only".
2. **The typical result first.**
   - "The middle month ends with KRW M. In P% of months you end at or below your floor of KRW L, keeping about KRW L
     (or less after gaps)."
   - "Averaged over all simulated months: KRW X (an average loss of KRW Y, from fees and the securities transaction tax).
     That average includes rare jackpots and is not what usually happens."
   - **Computing it.** X is the plain mean of terminal liquidation values, overshoots included, with its standard error.
     Y comes from the cost ledger. A difference between the two is what HIDDEN_EDGE tests.
   - In the delisting stress column, Y reads "…from fees, tax and the delisting stress loss".
3. **The headline pair:**
   - P(reached KRW 42,000,000 by the deadline, before income tax), using `reached_by_deadline`;
   - P(hit your floor or became unable to trade) = P(FLOOR) + P(STUCK), with the split;
   - the ladder (D4) on terminal liquidation value.
4. **The plain sentence.** "In 1,000,000 made-up months (from a model in which nobody has an edge, not real history),
   this plan reached KRW 42,000,000 before income tax in 63, about 1 in 16,000 (counting noise alone: between 1 in
   12,000 and 1 in 21,000; other models give 1 in A to 1 in B; neither range covers the model being wrong)…"
5. **Tax.**
   - Estimated with a per-leg `tax_basis` from the instrument map: `krx_small_holder_exempt`, `overseas_22pct_over_2.5m`
     or `crypto_22pct_from_2027`, the last unless postponed again.
   - Example: "about KRW 8.7M due the following May, leaving about KRW 33.3M (USD 23,800)".
   - An unsupported product or tax combination is refused.
6. **The ceiling and the base rates.**
   - "No plan without a real edge can beat 1 in N."
   - Then the base rates of section 3, each with its population, date and statistic.
7. **Precision.**
   - Clopper–Pearson intervals: two-sided 95% for k > 0, and a one-sided 95% upper bound for k = 0 ("below resolution:
     under about 3 in n").
   - A **structural** zero (IMPOSSIBLE, or no trades) is worded as such, not as low resolution.
   - The guard never renders a probability slot equal to zero.
8. **Model spread.**
   - The primary model is the two-point bootstrap.
   - Also shown: GARCH-t where eligible, a parametric GARCH-t refit (B = 20, simulate-then-refit, on common random
     numbers), and the bootstrap at 0.5× and 2× block length.
   - It is shown as a range with the lowest lower and highest upper bound. No figure from outside the range is shown.
9. **Columns:**
   - **No edge**, always the headline;
   - **Using the win rate you typed** (`ASSUMED_EDGE`): "These numbers are only as true as the win rate you typed (W%).
     This bracket's no-edge win rate is P0%; telling them apart would take about N recorded brackets. Without the edge
     you typed, no plan can beat 1 in M." It also shows the typical result and P(hit your floor);
   - **The tested-strategy replay** (`TESTED_REPLAY`, D13), on its own card: "This replays strategy S_C3 exactly as it
     passed QUANTGEN's backtest test, with 40% of its edge removed. Backtest edges often shrink or vanish in live
     trading; read this as the hopeful case."
10. **Flags:**
    - **`HIDDEN_EDGE`**, only where its variable is provably bounded:
      - It applies to two-point bootstrap legs, and to GARCH-t legs with bounded innovations.
      - X = W_τ + C_τ − W₀, with τ = the first of REACHED, FLOOR or the horizon; for this test both tracks stop at T.
      - Its range R is deterministic: W_τ ∈ [0, T·e^{m_max}], since losses stop at the account balance and one check
        can multiply a position (≤ equity < T) by at most e^{m_max}. C_τ is at most the number of check points times
        the largest cost per check. Everything is computed in log space.
      - The delisting stress column is excluded from this test, because its jumps break E = 1 by design.
      - It is red when |mean X| exceeds the empirical-Bernstein bound √(2V·ln(4/δ)/n) + 7R·ln(4/δ)/(3(n − 1)), with
        δ = 1e-4.
      - Its two wordings: "makes money without any edge" and "loses more than its costs explain".
      - The card prints the smallest edge the test can detect (a resolution figure, not a power guarantee).
      - Where the variable is not bounded, the card says "diagnostic unavailable".
    - **`CEILING_BREACH`** against the analytic ceiling only:
      - amber "preliminary evidence, about 5% false-alarm rate: rerun with more paths" when the one-sided 95%
        Clopper–Pearson lower bound exceeds it;
      - red "do not use these numbers" when the one-sided (1 − 0.001/m) bound does (Bonferroni over the m checks).
    - `ABOVE_ESTIMATED_REFERENCE` (amber), `IMPOSSIBLE`, `BELOW_RESOLUTION`, `GREY_LEG`, `PROXY_DATA`,
      `CHECKS_AT_OPEN_CLOSE`, `CLOSE_ONLY_CHECKS`, `LIMIT_GAP`, `LOCKED_AT_HORIZON`, `COST_DOMINATED`, `NOT_TRADABLE`,
      `STUCK_AT_START`, `RULE_CHANGE_IN_HORIZON`, `SPECIAL_REGIME`.
11. **"Not in these numbers":**
    - income tax (estimated, not simulated);
    - the won-dollar rate;
    - Upbit withdrawal holds after a KRW deposit, and the Upbit-to-OKX route closing without notice;
    - exchange freezes or failure;
    - delistings and Upbit warnings (survivorship);
    - KRX halts, VI auctions and designations;
    - unfilled orders at the limits beyond what is modelled;
    - broker refusals;
    - hacked or locked accounts;
    - rule changes.

    "Most of these make the real result worse; none makes a no-edge plan better."
12. **Footer.** "These numbers describe rules you wrote, run in a model. They are not advice, and TRADEGEN does not
    recommend any plan. A higher chance of reaching the target does not make a plan better."

**Comparing plans**
- There is no ranking by P(target). Plans are listed in creation order, or by smallest average loss.
- The fixed moonshot caption: "With no real edge, a higher chance of the target generally comes from putting more of
  your stake at risk, sooner. Check P(hit your floor) beside it. Higher here means riskier, not better."
- The comparison prints: "You compared K plans (and tried J typed win rates) in this session. The highest-looking
  figure is the luckiest of K and is probably too high."
- Before arming (execution spec), the plan is re-run on a fresh market seed.

**Language guard**
- All text comes from the catalogue.
- Whole words banned: best, optimal, recommended, safe, guaranteed, sure, ideal, risk-free, low-risk, proven, "should",
  "worth trying", "good chance", "likely to reach". Korean entries are added once a Korean UI exists.
- Internal names never appear in rendered text.

**Provenance** recorded with every report:
- the state hashes, the owner-log head, the code hash and the key fingerprint;
- the data, model, seed, n, CHUNK and NumPy version;
- the edge source;
- `repo_anchor()` and `tree_hash()`.

---

## 8. Testing

**Setup.**
- Two new suites run under `tests.macro_acceptance.hermetic()`: `compliance` (`tests/compliance_acceptance.py`) and
  `odds` (`tests/odds_acceptance.py`).
- `TRADEGEN_HOME` points to a temp dir. Price data comes from in-memory fixtures. A test key pair is generated per test
  run, and the real owner key is never touched.
- Everything is built test-first.

**compliance**
1. **Loaders:**
   - duplicate keys, anchors, native dates, oversized files, `any` on an allow row and out-of-vocabulary values each
     make the table INVALID;
   - the monthly and `known_changes` rules hold;
   - all 38 matrix rows are covered;
   - every research pointer resolves;
   - every row carries `legal_or_policy`.
2. **Approval and signing (D14):**
   - unsigned or wrongly signed approvals make the table INVALID;
   - a replaced draft blocks new exposure while the previous approved version stays active;
   - an unsigned code hash blocks new exposure;
   - a changed public key gives exit 3;
   - the signing CLI refuses non-TTY stdin and needs the retyped code;
   - nothing in the test suite or any other module can produce a valid owner signature without the test passphrase.
3. **Hard blocks:**
   - each conduct class and tag, on every venue;
   - the hard-coded floor with the table rows deleted;
   - a randomised property test: any blocked attribute gives BLOCK.
4. **Classification:**
   - TQQQ as a 1x ETP, or 252670 as 1x, is BLOCK (multiple mismatch);
   - a US single-stock −1x product is BLOCK (D16);
   - IBIT is BLOCK;
   - BITO is ALLOW (crypto-futures ETF);
   - credit financing is BLOCK (D15);
   - lend and borrow are BLOCK (D15);
   - an unknown symbol is BLOCK.
5. **Fail-closed inputs:** NaN, infinity, negative values, wrong types, case variants, unknown tags, inconsistent
   transfer fields and negative exposure or reservations are each BLOCK; fuzzed input never raises.
6. **Exits (D11):**
   - on 2026-12-03, OKX sell close-long gives ALLOW_EXIT, while a buy is BLOCK;
   - OKX → Upbit withdrawal at a registered address gives ALLOW_EXIT;
   - with a broken owner log, closing uses the snapshot and a withdrawal is BLOCK "withdraw manually";
   - with no snapshot, closing is BLOCK "close manually";
   - a sell larger than holdings is not an exit;
   - conduct still blocks exits.
7. **OKX new exposure:**
   - no acknowledgement, or an acknowledgement with a wrong hash or an old session, gives ACK_REQUIRED;
   - an unset cap, over-cap exposure, missing age, or a date ≥ 2026-12-03 gives BLOCK;
   - Asia/Seoul boundary: 2026-12-02T23:59:59+09:00 ALLOW, 2026-12-03T00:00:00+09:00 BLOCK.
8. **Permits and reservations:**
   - verifying a permit excludes only its own reservation;
   - two permits cannot share one cap's capacity;
   - forged permits, other intents, other sessions, other dates and an unapproved replacement state are refused;
   - purity: during `decide()`, `open`, `socket.connect` and `time.time` are patched to raise, and the module's date
     names are swapped; an AST scan shows no wall-clock call.
9. **Owner log:**
   - an edited last line, truncation below a recorded head, and an unsigned line are each detected;
   - a loosening is deferred and refused after a halt (D12);
   - paths stay under `~/.tradegen`;
   - task A0: a symlink, junction or hard link under the state root is refused, and final-target checks hold in the
     reused writers.
10. **Alerts:** exit codes 0 to 3; thresholds still fire after a missed run; toast and `--log` work with fake channels;
    a failed channel is announced on the others; the template contains no rule free text.

**odds**
1. **The martingale law:**
   - the two-point kernel gives E[next | p] = p exactly (to 1e-12), on random p within random bands, edges included;
   - prices never leave the band, and include the 100 → 70 → 100 example that broke rev 2.1's construction;
   - under every model, a fixed stop, a bracket and buy-and-hold each have a mean payoff of 0 before costs, within error;
   - the repo's `drift="zero"` and per-row demeaning both fail this check.
2. **HIDDEN_EDGE:** its false-alarm rate is ≤ δ at λ = n·P(target) in {1, 2, 10, 50}; a planted edge of twice the
   printed resolution is flagged; it reports "unavailable" for unbounded GARCH innovations.
3. **Exact values:**
   - `bold_even` gives 0.1000%, 0.0816%, 0.0346% and 0.0106%, and 0.0400% with L at half the stake;
   - simulated bold play on an even-money bracket fixture matches;
   - under floor-safe sizing the ceiling (W₀ − L)/(T − L) is never breached at the Bonferroni level, and under
     stop-based sizing neither is W₀/T.
4. **Mechanics:**
   - buy-and-hold KRX at 1,000× is IMPOSSIBLE with N = 161× to 459× across 18 to 22 sessions;
   - a bracket KRX leg is not flagged IMPOSSIBLE;
   - limit-down carry at 2× (with the constant checked against `orders`);
   - LOCKED_AT_HORIZON;
   - STUCK_AT_START;
   - outcomes sum to n, and `reached_by_deadline` is consistent with them;
   - the forced exit at a rule date, a non-session date included;
   - REACHED is measured after exit costs and tax.
5. **Ledger:**
   - both affordability inequalities hold after rounding and under 2× costs;
   - a bold fraction is refused when the net win coefficient is ≤ 0;
   - a stake below the minimum means no bet;
   - the sell tax applies on sells only, per the book.
6. **Refusals:** `UNSUPPORTED_PRODUCT`, `MULTI_LEG_UNSUPPORTED`, `LIMITS_UNSET`, `CALENDAR_UNSIGNED`,
   `MODEL_NOT_FOR_LIMITED_VENUE`, `SYNTHETIC_REFUSED`, `NOT_TRADABLE` and `CARD_NOT_REPRODUCED`.
7. **D13 replay:**
   - the pure replay on fixture bars is deterministic;
   - a statistics mismatch is refused;
   - the replay never imports the study runner;
   - Kelly uses the mean's lower bound, and gives 0 when conservative growth ≤ 0.
8. **Seeds:** plans in one comparison share the same streams; renaming a plan changes nothing; a partial chunk is
   refused.
9. **Report:**
   - the typical result comes first;
   - the mean is computed from terminal values, overshoot included;
   - the tax line, the base rates (with populations), the footer and the "not in these numbers" box are present;
   - structural zeros are worded as structural, and no zero probability slot is rendered;
   - no banned word appears in the catalogue or the output;
   - the K note and the moonshot caption are present.

**Existing guards stay in force:**
- test_08, test_09 and T-RO-01 cover both packages;
- T-RO-02 is unaffected;
- T-CTX-01 covers both packages once its prefixes are extended.

## 9. Error handling

- **Gate:**
  - it never raises;
  - invalid, unapproved or unsigned state, or unsigned code, blocks new exposure (exit 3, alert), while exits follow
    D11;
  - a broken owner log means withdrawals are manual and closing orders use the snapshot;
  - `verify_permit` refuses any mismatch.
- **Odds** refuses with named reasons and never prints a probability from a refused run: `UNSCREENED`, `BLOCKED_LEG`,
  `UNSUPPORTED_PRODUCT`, `MULTI_LEG_UNSUPPORTED`, `LIMITS_UNSET`, `CALENDAR_UNSIGNED`, `MODEL_NOT_FOR_LIMITED_VENUE`,
  `SYNTHETIC_REFUSED`, `NOT_TRADABLE`, `CARD_NOT_REPRODUCED`, `SPECIAL_REGIME`. A model that fails its pilot check is
  left out of the spread with a note.
- **Alerts:** a failure of the check itself is alerted.
- **Paths:** everything is written under `~/.tradegen`, with final-target checks (A0).

## 10. The guardrails, in plain language

| Guardrail | What it protects you from | What you see | Who may change it |
|---|---|---|---|
| No-edge martingale | A model that quietly "makes money" with no edge, or timing rules exploiting old patterns | Nothing; it is the default | No one; edges get their own columns |
| HIDDEN_EDGE | A bug that hands a plan free money, or one that loses more than its costs | Red with one of two wordings, or "diagnostic unavailable" | No one |
| Ceiling | Believing a no-edge plan can beat 1 in 1,000 (1 in 2,000 with a floor at half the stake under floor-safe sizing) | "No plan without a real edge can beat 1 in N." | It is maths |
| CEILING_BREACH | Impossible numbers | Amber "preliminary evidence…", or red "do not use these numbers" | No one |
| IMPOSSIBLE | A buy-and-hold KRX target beyond the daily band | "KRX's daily band allows at most N× in these S sessions" (161× to 459× in 30 days) | It is a market rule for buy-and-hold; bracket plans get no such claim |
| Estimated reference | Trusting an estimate as a proof | "estimated: … about X" | — |
| Typical result first | Mistaking the jackpot-inflated average for the usual month | "The middle month ends with KRW M…" | No one |
| Precision and model spread | Counting noise and one model mistaken for your real odds | "Counting noise alone: … ; other models give …" | Adding models is allowed |
| Open/close checks | Thinking stops fire at intraday lows | "Price checks at the open and the close only" | A future intraday model needs its own martingale test |
| Floor-safe sizing | Losses running past your floor | "Your floor holds even if this position goes to zero", or, for stop-based: "gaps can take you below your floor" | The owner chooses per leg |
| 2× costs | Costs eating the edge | A second column | No one |
| Minimum tickets / STUCK | A plan that cannot trade its size | "Can't open", or "left below the minimum order" | The owner, via the signed venue table |
| LIMIT_GAP / LOCKED_AT_HORIZON | Assuming exits always fill | The worst overshoot; "still locked at the end" | It is how markets gap |
| Typed win rate | A guessed edge dressed up as odds | "Only as true as the win rate you typed… about N recorded brackets…" | The owner types it; never in the headline |
| Tested-strategy replay | Trusting a backtest too much, or borrowing it for another plan | "This replays strategy S_C3 exactly… the hopeful case" | Only an exact, re-verified replay (D13) |
| Winner's curse | Picking the luckiest of many plans | "You compared K plans…", plus a fresh-seed confirmation | No one |
| Stale rules | Trading on a rule that may have changed | New exposure blocked, alerts on every channel; exits open | The owner signs a re-reviewed version |
| OKX cap, acknowledgement and auto-off | Unbounded OKX exposure, or OKX after 2026-12-03 | ACK_REQUIRED or BLOCK on buys; the warning you acknowledge | The owner, signed; loosening waits a day (D12) |
| Signed owner state (D14) | A script or agent acting as you | Unsigned changes are ignored, and exit 3 | Only your passphrase, in your own terminal |
| Signed code hash | Silent changes to the gate | New exposure blocked until you sign the new code | You, after reviewing the diff |
| Language guard | Report text that sounds like advice | Nothing (the build fails) | The catalogue is reviewed |

## 11. Owner inputs and open legal points

**Owner acts.** All are signed in the owner's own terminal (D14); Claude never performs them.
- Generate the signing key, and confirm the public-key fingerprint printed in your own terminal.
- Sign the code hash after reviewing each diff to `core/compliance` and `core/odds`.
- Approve the rules table, the instrument map and the venue table, monthly.
- **Sign the calendars** for KRX and US plans:
  - set `signed_off_by` and each file's `content_md5` in `core/calendars/data/MANIFEST.yaml`, with the version and the
    test ids the store requires;
  - for `holidays_KRX.yaml`, `kr_sessions.yaml`, `holidays_NYSE.yaml`, `us_sessions.yaml` and `kr_regime_tags.yaml`.

  Claude may prepare a source-checked verification first. Until this is done, only crypto plans run.
- Set `total_loss_floor_krw`, `daily_loss_krw` and `okx_equity_share`.
- Record `age_of_majority`, and register withdrawal addresses.

**Open legal points for Korean counsel** (all 8 from the report):
- Kalshi: gambling, or overseas derivatives?
- Does building this tool reach Art. 247 or Art. 26②?
- The user-side status of DEX perps and unregistered exchanges after 2026-12-03 and about 2027-02-18.
- The territorial scope of VAUPA Art. 10.
- FX reports for crypto moved to USD platforms.
- Advisory registration for sharing outputs (forbidden here).
- Bybit and Binance terms, and whether Upbit and Bithumb will keep allowing same-name transfers offshore. This gates
  D6's funding route.
- The November–December 2026 votes.

## 12. Risks

- **The table goes out of date.** Mitigations: monthly review, known-change dates, fail-closed review dates, alerts on
  every channel.
- **Monthly approvals become rubber-stamped.** Mitigation: `--check` lists exactly which rows and sources changed.
- **Simulated odds are read as forecasts.** Mitigations: model-not-history wording, the typical result first, spread,
  base rates, the language guard.
- **A typed win rate tempts the owner.** Mitigations: its own column, the p₀ and bets-needed line, the "without the
  edge" ceiling.
- **A backtest edge is over-trusted.** Mitigations: exact replay only, the live multiplier, lower-bound Kelly, the
  hopeful-case wording.
- **An agent or script acts as the owner.** Mitigations: signatures (D14), the signed code hash, diff review. The
  remaining limit is stated in 6.4.
- **A grey venue tightens suddenly.** Mitigations: auto-off, acknowledgement, cap, exits kept open (D11).
- **The alerts depend on the PC being on.** Mitigations: the app-start check and the in-app banner.

## 13. Out of scope (later specs)

- **Execution:** adapters, arming and sessions, atomic reservations, single-use permits, the audit log, the halt record,
  reading live balances and broker answers (which lifts D16 row by row), and retiring the read-only guards
  consciously.
- **Strategies:** multi-leg, leveraged and short plans. Credit and lending stay out (D15).
- **UI:** with design-system and design-critique.
- **Compliance check:** `legal:compliance-check` per venue before real money.
- **Deferred techniques:** importance sampling, an intraday martingale path model, an OKX candle loader, and modelling
  special KRX reference-price regimes.

---

## Appendix A: the pre-spec review (rev 1)

Three critics shaped section 7 before rev 1: zero arithmetic drift, the structural maximum, the floor in the ceiling,
the exact optimum, noise-aware flags, simulation-precision wording, gaps and limit-down carry, the outcome partition,
lower-bound Kelly, data refusals, cost and ticket tables, calendars, no ranking, the winner's curse, survivorship.
Rounds 1 and 2 found several of those fixes incomplete.

## Appendix B: round 1 rulings (on rev 1)

Gemini's findings are G-n and Gm-n. The Claude workflow's are L (legal), S (statistics), H-F (honesty),
I (implementability), Z (safety) and the "missed" items. Each row gives where the fix lives in **rev 3**.

| Finding | Ruling | Rev 3 location |
|---|---|---|
| G-1, L5 (crypto ETPs) | Accepted; narrowed in round 2 to spot-backed products | 5.1, 5.3 |
| G-2, L7 (coverage gaps; offer-with-warning) | Accepted; D10 | 5.1, 5.3 |
| G-3, L2, L9 (eligibility details) | Accepted, then superseded by D15 and D16 | 5.3 |
| L6 (hard-block KRX derivatives) | Rejected: the report gates them; D16 now refuses them pending live evidence | 5.3 |
| G-4, Z8, L3 (transfers) | Accepted | 5.3, 6.2 |
| G-5, L4, L10 (dates and attributions) | Accepted; the backtest-dates objection rejected (live-decision gate) | 5.2, 5.3 |
| L1, L8 (conduct tags; further-review questions) | Accepted | 5.3, 11 |
| G-6, S1, S-missed-2 (bootstrap) | Accepted; rebuilt again in round 2 as the two-point kernel | 7.2 |
| G-7, S3 (FX) | Accepted (KRW series) | 7.2 |
| G-8 (ceiling and gaps) | Accepted; re-fixed in round 2 (floor-safe sizing) | 7.1, 7.4 |
| G-9, S2, S6, S7 (bets, sizing, optimum) | Accepted; reworked in round 2 | 7.1, 7.4 |
| G-10 (multi-leg) | Resolved by scope | 1, 7.1 |
| G-11, S4, H-F7 (average first) | Accepted; fixed again in round 2 | 7.5 |
| S5 (HIDDEN_EDGE) | Accepted; re-fixed in round 2 | 7.5 |
| S8, I5 (seeds) | Accepted | 7.3 |
| S9, S10 (structural maximum; precision) | Accepted; S9 re-fixed in round 2 | 7.4, 7.5 |
| G-12 to G-16, I1 to I4 (repo facts) | Accepted | 4 |
| G-17, I6 (cards) | Accepted; D13 | 7.2 |
| G-18, Z6 (exits) | Accepted; D11 | 6.2 |
| G-19, Z4, Z-missed-2, H-F1 (owner log) | Accepted; strengthened by D14 | 6.4 |
| G-20 (unset limits) | Accepted | 6.4 |
| Z1, Z2, Z3, Z5, Z7, Z9, Z10, I7 to I10 (safety and harness) | Accepted | 4, 5, 6, 8 |
| H-F2 to H-F10, H-missed (honesty) | Accepted | 3, 7.5, 10 |

## Appendix C: round 2 rulings (GPT on rev 2.1)

| GPT finding | Ruling | Rev 3 location |
|---|---|---|
| Major 1: a 7-day cash snapshot cannot gate per-buy cash | Accepted; D16 (refused until live evidence; snapshots never accepted) | 2, 5.3, 6.4 |
| Major 2: lending conditions incomplete | Superseded by D15 (no lending at all) | 5.3 |
| Major 3: half-step clipping breaks the daily band (100 → 70 → 100 → 169) | Accepted: a two-point kernel with state-dependent probability inside the session band; GARCH-t not used for KRX | 7.2, 8 |
| Major 4: the KRX bound is not market-wide | Accepted: restricted to buy-and-hold legs (161× to 459×); round trips acknowledged; section 3 corrected | 3, 7.4 |
| Major 5: the stake equations miss fixed fees and side-specific tax | Accepted: the cost ledger with κ_b, κ_s, φ_b, φ_s; affordability inequalities; bold refusals | 7.1 |
| Major 6: L_min is a one-check bound | Accepted: L_min = L only under floor-safe sizing, else 0 | 7.1, 7.4 |
| Major 7: the dynamic programme is not certified | Accepted: renamed estimated reference; no red flags | 7.4 |
| Major 8: empirical-Bernstein needs a bounded variable | Accepted: a deterministic range for bounded models; "unavailable" otherwise | 7.5 |
| Major 9: an edge can be transferred; Kelly bound undefined | Accepted: D13 exact replay as its own plan type; the mean's lower bound defined | 7.2 |
| Major 10: overshoot dropped; ever-reached versus terminal | Accepted: the mean from terminal values; `reached_by_deadline` | 7.3, 7.5 |
| Major 11: claims overstated (estimates, the "always" caption, base rates) | Accepted | 3, 7.5 |
| Major 12: asset class conflated with action and financing | Accepted: five independent axes; map-derived multiple and leverage | 5.1, 6.1 |
| Major 13: contradictions in the D11 exits | Accepted: one decision table; snapshot and manual recovery | 6.2 |
| Major 14: TTY plus an unkeyed chain cannot stop an agent | Accepted: D14 signing, signed code hash, the honest limit stated | 6.4 |
| Major 15: grey-cap reservations double-counted; negative exposure | Accepted | 6.1, 6.2, 6.3 |
| Major 16: final targets in reused writers | Accepted: task A0 | 4, 8 |
| Minor 1: cost class by symbol shape | Accepted: cost book from the map | 4 |
| Minor 2: replay contract | Accepted: three digests, pure replay | 7.2 |
| Minor 3: spot versus futures ETFs; Gopax; tax | Accepted | 5.1, 5.3, 7.5 |
| Minor 4: calendar signing procedure; endpoints; regime_tags KR-only | Accepted | 4, 11 |
| Minor 5: the assumed-edge law; sample size | Accepted: tilted kernel; formula stated | 7.2 |
| Minor 6: pw_block kind; GARCH tolerance; wording | Accepted | 7.2, 7.5 |
| Minor 7: permit fields; approved-version storage | Accepted | 5.2, 6.3 |
| L6 rejection, G-5 backtest rejection, G-10 scope | GPT agreed | — |

## Appendix D: round 3 (on rev 3)

- **GPT (Codex):** incomplete. The run hit the ChatGPT usage limit after about 77k tokens ("try again at Oct 30th,
  2026 2:40 PM") and returned no review. The final GPT check runs on rev 3.1 after that time.
- **Gemini (Antigravity):** invalid as a whole. The run ended `status: ERROR`, the review appears twice, and 7 of its 10
  major findings attack content that does not exist in rev 3:
  - `KRX_FUT` / `PAPER_ONLY`, `respect_floor`;
  - edits to `core/engine/state.py`, `orders.py` or `evaluator.py`;
  - compliance events written through `governance.append_event`;
  - `_permit_lock` / `consume_permit`, `OrderIntent`, `LIVE_ELIGIBLE` / `PAUSED`;
  - a GarchT-based S_C3 replay;
  - a "Worked Example 3".

  Those are rejected as not applicable. The findings that do hold against the real text were checked and are accepted
  in rev 3.1:

| Gemini r3 finding | Ruling | Rev 3.1 location |
|---|---|---|
| #3: band-edge opens are absorbing within a session; band tick rounding | Accepted: the absorption is forced by the no-edge law, so it is stated and flagged `BAND_EDGE_SESSIONS`; the band is rounded to the tick ladder | 7.2 |
| #4: bold sizing when one win cannot reach T | Accepted: s = min(s_reach, s_afford) | 7.1 |
| #5: the floor-safe reserve under 2× carry and 2× cost stress; delisting stress inside Y | Accepted: worst-case exit reserve R_exit; Y labelled in the stress column | 7.1, 7.5 |
| #6: undefined "gap" in HIDDEN_EDGE's range | Accepted: lower bound 0, computed in log space; the stress column excluded | 7.5 |
| Minor 1: the code-hash surface | Accepted: in-repo import closure | 6.4 |
| Minor 3: T-CTX-01 prefixes | Already in rev 3 | 4 |
| #1, #2, #7–#10, Minor 2 | Rejected: they review text not in this spec | — |
