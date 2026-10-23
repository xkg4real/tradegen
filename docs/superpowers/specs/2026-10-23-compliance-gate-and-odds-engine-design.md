# TRADEGEN compliance gate and odds engine

Date: 2026-10-23.

Status:
- **Revision 3.2.** Review history (every finding is ruled in Appendices B to E):
  - **Round 1, on rev 1:** Gemini said REJECT; the Claude 5×2 workflow confirmed most of its points.
  - **Round 2, on rev 2.1:** GPT said REJECT, with 16 major findings.
  - **Round 3, on rev 3:** GPT stopped at its usage limit. Gemini's run was invalid.
  - **Round 3b, on rev 3.1:** a Claude 5×2 workflow and a grounded Gemini run.
  - All reviews are in `docs/superpowers/specs/2026-10-23-review-gate-odds/`.
- The owner decided D11 to D16 on 2026-10-23.
- Next:
  1. The owner's review.
  2. GPT's final check after its quota resets (2026-10-30 14:40).
  3. Two implementation plans. The compliance plan comes first, because the odds engine depends on `screen()`.

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
on these interfaces: `owner.load_context()`, `decide()`, `permit()` / `verify_permit()`, and `OddsReport`.

**Limits of this version**
- The odds engine accepts **single-leg, cash-financed, 1x, long-only plans** on a whitelist of classes. These are KRX
  cash shares, KRX 1x ETFs and ETNs, US stocks and 1x ETFs, and crypto spot.
- Everything else is refused with a named reason.
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
| D7 | Every plan shows P(reaching the target) and P(ending at the floor). Bold play is a reference, shown beside the ceiling (7.4) | decided; refined |
| D8 | Execution is disarmed by default and armed per session by the owner only. It has hard daily and total loss limits, a kill switch and an audit log. The owner adds trading-scope keys | decided; execution spec |
| D9 | Approach A: rules as data, a pure `decide()` kernel, and a plan simulator | decided |
| D10 | Grey venues other than OKX (Binance, Bybit, Bitget, Hyperliquid, pump.fun, Jupiter, Uniswap), and the lawful but non-trading Betman, Lotto and Speed-On, are `out_of_scope` (blocked). Enabling one needs a reviewed `grey` row | follows D2/D6 |
| D11 | **Exits stay open.** Stale rows, auto-off, unmet gates, caps and out-of-scope or hard-block venue rows block **new exposure only**. Closing a position is still allowed, and so is withdrawing to an FIU-registered domestic exchange at a registered address. Conduct rows still apply. **If owner state is corrupt,** automated closing orders use the last approved stored snapshot, and withdrawals are done manually by the owner in the exchange app | decided 2026-10-23 |
| D12 | Limits and caps **tighten at once and loosen slowly**: only from the next Asia/Seoul date, never inside an armed session, and never after a recorded halt | decided 2026-10-23 |
| D13 | The "tested edge" column shows only a **replay of the exact validated strategy**, `S_C3_crypto_trend_krwbtc`, re-created and re-verified first. Anything changed needs a new validation | decided 2026-10-23 |
| D14 | **Owner-only writes are signed.** An Ed25519 key is unlocked only by a passphrase typed in the owner's own terminal, using a signer the owner keeps outside the repo (6.4). The gate verifies with the public key, and refuses new exposure until the owner signs the current code hash. Section 6.4 states its limits honestly | decided 2026-10-23 |
| D15 | **No credit buying and no coin lending or borrowing.** This is owner policy, stricter than the law, and applies in the strategies spec too | decided 2026-10-23 |
| D16 | Short selling, leveraged and single-stock ETPs, KRX derivatives and ELW are **refused until live broker evidence exists**, which the execution spec adds. Owner snapshots are not accepted as evidence | decided 2026-10-23 |

## 3. The honest numbers, up front

The first five points are mathematics, checked by direct computation on 2026-10-23. The rest are research estimates and
base rates, labelled as such.

- **The ceiling.** Suppose every trade has zero or negative expected value after costs at every point where it can be
  placed, and losses stop at the account balance. Then wealth is a non-negative supermartingale, and P(ever reaching T)
  ≤ W₀/T for every strategy, by Ville's inequality. For KRW 42,000 → KRW 42,000,000 that is **0.1% (1 in 1,000)**.
- **With a floor that truly holds.** If no outcome can take equity below L_min, the bound is (W₀ − L_min)/(T − L_min).
  - TRADEGEN claims L_min = L only under **floor-safe sizing** (7.1). With L at half the stake that is **0.050%
    (1 in 2,000)**.
  - Under stop-based sizing the honest bound is W₀/T.
- **Bold play (Dubins–Savage), the even-money benchmark.**
  - Exact P(1,000×): **0.1000%** at p = 0.50, **0.0816%** at 0.49, **0.0346%** at 0.45 and **0.0106%** at 0.40.
  - With a floor at half the stake: 0.0400% at p = 0.49.
  - It ends at the floor in more than 99.9% of months.
  - It is the optimum for that benchmark game, not a universal rule for every market.
- **KRX.**
  - A KRX position bought at the first open and held is capped by the ±30% daily band at (1.3/0.7)·1.3ⁿ⁻¹ over n
    sessions.
  - On the repo's holiday calendar a 30-day window (half-open) holds **16 to 22** KRX sessions in 2026 and 2027, so the
    cap is **about 95× to 459×**. A buy-and-hold KRX plan cannot reach 1,000×.
  - The band is measured from each day's reference price. Repeated intraday round trips from limit-down to limit-up
    (about 1.86× a session), IPO days and special reference-price regimes are **not** bounded this way.
  - The research rates that route as "essentially zero" in practice, not mathematically impossible (report line 165).
- **Kelly** aims at long-run growth, not at reaching a target by a deadline. With zero edge it bets nothing. A genuine
  52.5% even-money edge needs about **5,524 bets** to grow 1,000×.
- **Typical versus average.**
  - With no edge, the average ending equity is the stake minus costs, because rare jackpots offset the many losses.
  - The typical (median) moonshot month ends at the floor.
  - Every card shows the typical result first.
- **Research estimates, not measurements.** The research found no measured probability for this account reaching
  1,000× in a month. Its reasoned estimates (feasibility notes):
  - **0.01% or less** in general;
  - roughly 0.01–0.03% for long far-out-of-the-money US options;
  - below 0.01% for domestic crypto spot.
- **Base rates,** each with its population, date and statistic:
  - Kalshi takers lost about 32% of the amount staked and makers about 10% (Bürgi, Deng and Whelan working paper,
    2025-26; not re-verified, because the source could not be fetched);
  - 74–89% of EU retail CFD accounts lose money (national regulators' data, ESMA, 27 March 2018);
  - 87.7% of Indian retail equity-derivatives traders lost in FY26 (SEBI);
  - Korean retail lost about KRW 458 billion a year on overseas derivatives, 2020 to H1 2025, with no profitable year;
  - in a 2020 study of 204,004 Korean retail accounts, 46% lost money, and 62% of new investors did.
- **Monte Carlo precision.** A 0.01% event needs about 1,000,000 simulated months to reach a 10% relative standard
  error. A 0.1% event needs about 100,000.

---

## 4. Architecture

```
core/compliance/
  kr_rules.yaml        rules table (venue rows + conduct rows; quoted dates)
  instruments.yaml     instrument map: symbol -> asset, class, multiple, underlying, currency, cost book, tax basis, source
  owner_pubkey.pem     the owner's Ed25519 public key (trust anchor; see 6.4)
  rules.py             safe loaders; schema/vocabulary/derivation checks; hashes; approved-version store; CLI --check
  gate.py              decide(), permit(), verify_permit(), screen(), render_warning(); hard-coded floor   (pure)
  owner.py             load_context(now): the ONLY producer of Context; owner log (signed + system entries); snapshots
  alerts.py            due() (pure), alert template, Windows toast, alerts.jsonl writer CLI
signer/  (owner-kept, outside the repo; see 6.4)
  sign.py              key generation, passphrase unlock, signing; stdlib + `cryptography` only

core/odds/
  plan.py              Plan, Leg, Fraction (kw_only dataclasses; whitelist validation)
  bars.py              daily open/close loader on the data clients; own sha-manifest cache; network via seams
  venues.yaml          lots, minimums, fee extras, KRX stock tick ladder, markets and settlement assets, deposit networks
  models.py            TwoPointBootstrap, GarchT; no-edge law; edge sources; the S_C3 replay (D13)
  simulate.py          vectorised, chunked simulator
  bold.py              ceiling, structural maximum, estimated bracket reference, exact even-money recursion
  report.py            OddsReport rendered from the sentence catalogue; flags; language guard
```

**How data flows**
1. `owner.load_context(now)` hashes the code on disk, verifies the owner log, and loads the latest approved tables and
   the snapshot, building a `Context`.
2. A `Plan` and the first stake computed by the odds engine go to `gate.screen(plan, ctx, first_stake_krw)`. A blocked
   leg means the plan is refused.
3. `odds.simulate(plan, screening, cal, limits, …)` refuses an unscreened plan and produces an `OddsReport`.
4. Execution, in its own spec, calls `permit(intent, ctx)` and, at send time, `verify_permit(permit, intent,
   ctx_now)`, using contexts built only by `load_context`.

**Repository facts the design rests on** (verified 2026-10-23; the rounds' verification records are in the review
folder)
- **No `core.engine.orders` import.** T-RO-01 allows it only in `core/engine/` and two skills modules, and `test_s4`
  keeps `orders.py` add-only.
  - KRX limits come from `regime_tags("KR", d)["price_limit"]`, which is KR-only and raises `KeyError` for other
    markets.
  - The KRX stock tick ladder lives in `venues.yaml`, because `KRX_stock_book.tick_table` is `OWNER_INPUT`.
  - `LIMIT_DOWN_CARRY_COST_MULTIPLIER = 2.0` is declared locally, and a test asserts it equals the orders constant.
- **Bars.** `History` holds closes only, so `core/odds/bars.py` loads daily (open, close) bars:
  - KRX from KIS daily rows;
  - Upbit KRW-* and Binance *USDT from `data.crypto` Candles;
  - US from yfinance.

  US and FX bars are mapped to the Asia/Seoul date of their close. Every network call goes through a module-level seam
  (for example `bars._yf_download`), which the test suites patch, because yfinance uses curl_cffi and bypasses a socket
  patch.
- **Calendars.** The shipped files are unsigned drafts. `simulate()` takes `cal: CalendarSet`, and refuses KRX and US
  legs with `CALENDAR_UNSIGNED` unless the store loads them **and** the owner log holds a signed
  `approved {kind: calendar, sha256}` for that calendar set (section 11). `sessions_between` includes both endpoints;
  horizons are half-open `[start, start + horizon_days)`. Tests use the fixture set in `tests/macro_m1_calendars.py`.
- **Costs.**
  - The instrument map names each symbol's cost book: `KRX_stock_book`, `KRX_ETF_line`, `US_shares_KIS` or
    `crypto_venue`. KONEX is gate-only, so it needs no odds cost book.
  - The per-side rate at each fill is `instruments.cost_per_side(book, price=fill_price, on=fill_date, side=side).bp`.
    That is the repo's R-26 rule, max(table rate, tick floor), which can only raise a cost. For `KRX_stock_book`, whose
    tick table is `OWNER_INPUT`, the same floor formula uses the `venues.yaml` stock ladder.
  - **The repo's per-side table rates already include the sell tax**: KRX stock is 35 bp "incl. tax"
    (`docs/asset_expansion_study.py:19`). So TRADEGEN charges that rate on **both** sides, which is conservative, and
    adds no separate tax.
  - Symbol-shape inference (`validate.cost_class`) is not used.
  - Extras in `venues.yaml` may only raise costs (`check_extras`). Fixed charges φ_b and φ_s are taken from there.
- **Provenance.** Every report records:
  - `gate_ledger.repo_anchor()`;
  - `macro_artifacts.tree_hash()`, which covers `core/**/*.py`, `data/macro/**` and `config.py`;
  - the D14 code hash (6.4);
  - the calendar version and the md5 of each calendar file used.
- **Guards** (T-RO-01 and test_08/test_09). No identifier, string or docstring in `core/` may contain:
  - an order-endpoint name or transaction id;
  - `CANO`, `KIS_ACCOUNT` or `ACNT_PRDT_CD`;
  - **`private_key` or `seed_phrase`** (case-insensitive);
  - a `/uapi/…/trading/` path.

  Also:
  - no function or method may be named `transfer`, `withdraw` or `deposit_address`;
  - the signer lives outside `core/` (6.4);
  - `core.odds.` and `core.compliance.` are added to `context_log.ACTING_MODULE_PREFIXES` (T-CTX-01).
- **Isolation residual (task A0 of the compliance plan).**
  - Every writer reached by the reused loaders checks its **final** target with `refuse_quantgen` immediately before
    opening it, temp and sidecar files included. That covers the KIS token, the OpenDART cache, `history._cached`, the
    FICC cache, the grokteam cache and the bars cache.
  - `state_root()` refuses once per process if any entry under `~/.tradegen` is a symlink, a junction or a hard link.
  - This is path discipline, not a security boundary.

---

## 5. Rules, instruments and approvals

### 5.1 Vocabulary and derived classes

An intent is described along independent axes:
- **Venue:** an exact lower-case id.
- **Asset:** what is held, taken from the map.
- **Class:** derived from the map; the caller never supplies it.
- **Action:** what is done.
- **Financing:** how it is paid for.
- **Counter asset:** what is paid or received.

**Venue ids.**
- Domestic brokers and exchanges: `kis`, `upbit`, `bithumb`, `coinone`, `korbit`, `gopax`.
- Offshore exchanges: `okx`, `binance`, `bybit`, `bitget`.
- DEXes: `hyperliquid`, `pumpfun`, `jupiter`, `uniswap`, `drift`.
- Prediction markets: `polymarket`, `kalshi`, `limitless`, `myriad`, `opinion`, `predictfun`.
- Retail apps with prediction markets: `robinhood`, `cryptocom`, `predictit`.
- Betting and lotteries: `sportsbook`, `betman`, `lotto`, `speedon`.
- Foreign brokers: `ibkr`, `moomoo`, `webull`, `etoro`, `offshore_fx_cfd`.
- The state-blocked ids, plus `bitmart`.
- Unknown means BLOCK.

**Asset kinds.**
- KRX: `krx_share`, `konex_share`, `krx_etp`, `krx_derivative`, `elw`.
- US: `us_share`, `us_etp`, `us_option`.
- Futures: `overseas_future`, `overseas_crypto_derivative`.
- Crypto: `crypto_coin`, `crypto_perp_or_future`.
- Other: `fx_pair`, `cfd`, `event_contract`, `sports_bet`, `lottery`.

**Actions.** `buy`, `sell`, `sell_short`, `buy_to_cover`, `write`, `transfer_out`, `lend`, `borrow`, `p2p_buy`,
`p2p_sell`.

**Financing.** `cash`, `credit`, `margin`.

**Derived class** (the `class` match key; the derivation is total and exclusive). It is computed by `rules.py` from each
map entry's asset, multiple and underlying kind (single | index | basket | crypto_spot | crypto_spot_basket |
crypto_futures), using the first rule that applies:
1. Any ETP whose underlying is `crypto_spot` or `crypto_spot_basket` is `etp_crypto_spot`. That covers IBIT, FBTC,
   ETHA, GDLC and EZPZ, whatever the map calls them.
2. Single underlying and multiple ≠ +1 (−1 included, domestic or overseas-listed) is `etp_single_stock`.
3. A non-single underlying (crypto futures included) with multiple = −1 is `etp_index_inverse`.
4. A non-single underlying with any other multiple ≠ +1 is `etp_leveraged`.
5. Underlying `crypto_futures` with multiple +1 is `etp_crypto_futures_1x`, for example BITO. The FSC distinguished these
   and preserved trading in existing overseas bitcoin-futures ETFs.
6. Multiple +1 otherwise is `etp_1x`.
7. Non-ETP assets map to themselves: `share`, `konex_share`, `coin`, `option` and so on.

An ETP that fits none of these makes the map INVALID.

**Venue facts** (`venues.yaml`, owner-approved).
- **Markets:** for each venue, its markets (base, quote) and settlement assets. Upbit settles in KRW (BTC markets
  included); OKX in USDT and USDC; KIS in KRW and USD.
- **Deposits:** the deposit networks and memo or tag rules of each destination venue.

### 5.2 Row schema and table rules

```yaml
schema: tradegen.kr_rules/4
scope: "Korean-resident individual, own funds only"
known_changes: ["2026-12-03", "2027-01-01", "2027-02-18"]
rows:
  - id: KR-OKX-SPOT
    kind: venue                                   # venue | conduct
    match: {venue: [okx], class: [coin], action: [buy, sell], financing: [cash]}
    treatment: grey                               # hard_block | gated | grey | allow | out_of_scope
    requires: {owner: [age_of_majority]}          # owner-signed evidence; `live: [...]` only execution can satisfy
    ack: per_session
    grey: {cap_key: okx_equity_share, auto_off: "2026-12-03"}
    warning: >-
      OKX is not registered with Korea's FIU. The FSC tells users of unregistered exchanges to withdraw their money. You
      get no Korean user protection, and withdrawals can be frozen. Upbit may stop transfers to OKX without notice. New
      rules start on 2026-12-03 and about 2027-02-18. TRADEGEN turns OKX off on 2026-12-03 and caps everything you hold
      on OKX at {cap} of your equity.
    reason: "Operator unregistered with the FIU; no user penalty found; the FIU contests transfers to it"
    basis: [legal]                                # legal | policy (both allowed)
    policy_ref: null                              # e.g. D15, D16
    sources: ["https://www.fsc.go.kr/no010101/87177"]
    research: "reports/Korean resident trading venue legality.md#compliance-matrix row 14"
    confidence: low
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
- Every row citing D16 must carry `requires.live`.
- Any violation makes the table INVALID.
- `instruments.yaml` and `venues.yaml` are treated the same way. The map additionally fails when an ETP's
  `crypto_spot*` underlying disagrees with its derived class.

**Sources and review**
- Every row cites a source and its research.
- The review cadence is **monthly**: `review_by` is at most 31 days after the latest review, and no later than the day
  before the next `known_changes` date that affects the row.
- All 38 matrix rows must be covered.

**What is in force (D14).**
- For each kind (`rules`, `instruments`, `venues`, `calendar`), the version in force is the sha256 named by the
  **latest** signed `approved {kind, sha256}` entry in log order.
- The gate loads that version's bytes from the immutable store `~/.tradegen/compliance/approved/<kind>/<sha256>`.
- The working file in the repo is only a draft, which `--check` diffs against the version in force.
- A superseded hash never counts again unless it is re-signed as a new entry. That stops a restored old file, from git,
  OneDrive or a worktree, from counting as approved.
- A git commit is not approval.

**Hard-coded floor** (defence in depth, whatever the table says):
- **all intents, exits included:** the conduct classes and tags, and the `event_contract` and `sports_bet` assets;
- **new exposure only** (so a held position can still be closed under D11):
  - the prediction, sportsbook and state-blocked venues;
  - OKX derivatives and P2P;
  - `fx_pair`, `cfd`, `overseas_future`, `overseas_crypto_derivative`;
  - `etp_crypto_spot`;
  - `option` + `write`.

### 5.3 Seed rows

The report's "Recommended actions" table sets each treatment, except where owner policy (D10, D15, D16) is stricter.

| Row id | Match (venue: class / action / financing) | Treatment | basis (policy_ref) | Matrix row |
|---|---|---|---|---|
| KR-KIS-KRX-SHARE | kis: share / buy, sell / cash | allow (±30% band) | legal | 21 |
| KR-KIS-KONEX | kis: konex_share / buy, sell / cash | allow (±15% band; 0.10% tax) | legal | 21 |
| KR-KIS-ETP-1X | kis: etp_1x / buy, sell / cash | allow | legal | 21, 31 |
| KR-KIS-ETP-INVERSE | kis: etp_index_inverse / buy, sell / cash | allow; confidence low (confirm with the broker) | legal | 22, 33 |
| KR-KIS-ETP-LEV | kis: etp_leveraged / buy | gated, `requires.live` (D16): deposit ≥ KRW 10M + `kofia_leveraged_1h` (US since 2026-05-22) | legal, policy (D16) | 25, 32 |
| KR-KIS-SINGLE-ETP | kis: etp_single_stock / buy | gated, `requires.live` (D16): cash ≥ KRW 30M, cash only, before every buy, + 3h course + 5h mock over 5 days | legal, policy (D16) | 26 |
| KR-KIS-CRYPTO-FUT-ETF | kis: etp_crypto_futures_1x / buy, sell / cash | allow; confidence low; review monthly | legal | crypto notes Q4 |
| KR-KIS-CRYPTO-SPOT-ETP | kis: etp_crypto_spot / buy | hard_block. FSC January 2024: brokering overseas spot crypto ETFs may breach the FSCMA. The FSS halted GDLC/EZPZ in November 2025. Sells of a held position stay open (D11) | legal | crypto notes Q4 |
| KR-KIS-KRX-DERIV | kis: krx_derivative / any | gated, `requires.live` (D16): stage 1 KRW 10M / stage 2 KRW 20M + broker eligibility | legal, policy (D16) | 27 |
| KR-KIS-ELW | kis: elw / any | gated, `requires.live` (D16): KRW 15M + course | legal, policy (D16) | 28 |
| KR-KIS-CREDIT | kis: any / buy / credit | out_of_scope (D15) | policy (D15) | 23 |
| KR-KIS-SHORT | kis: share / sell_short | gated, `requires.live` (D16): 30m KOFIA + 1h KRX mock + broker approval; 105% collateral | legal, policy (D16) | 24 |
| KR-KIS-US-SHARE | kis: share (US) / buy, sell / cash | allow | legal | 31 |
| KR-KIS-US-OPTION | kis: option / buy, sell | gated; per-session acknowledgement; broker eligibility (at least 1h + 3h); commissions of 3–20% of the account per side. The odds engine refuses option legs | legal | 34 |
| KR-KIS-US-OPTION-WRITE | kis: option / write | hard_block (recourse leverage) | legal | 34 |
| KR-KIS-CRYPTO-DERIV | kis: overseas_crypto_derivative / any | hard_block (FSC 2017-12-06) | legal | crypto notes Q4 |
| KR-KIS-FUT-FX-CFD | kis: overseas_future, fx_pair, cfd / any | hard_block | legal | 35, 29, 30 |
| KR-DOMESTIC-SPOT | upbit, bithumb, coinone, korbit: coin / buy, sell / cash | allow (KRW 5,000 minimum on Upbit) | legal | 10 |
| KR-GOPAX | gopax: any | out_of_scope (VASP renewal status unverified; not configured) | policy | 10 |
| KR-DOMESTIC-LENDING | upbit, bithumb, coinone, korbit: coin / lend, borrow | out_of_scope (D15) | policy (D15) | 11 |
| KR-DOMESTIC-CRYPTO-DERIV | upbit, bithumb, coinone, korbit: crypto_perp_or_future / any | hard_block (no legal framework) | legal | 12 |
| KR-TRANSFER-OUT | upbit, bithumb, coinone, korbit: coin / transfer_out | allow to a destination that is allowed or grey (6.2 step 6), at a signed registered (address, network, tag). A grey destination needs a per-transfer acknowledgement. `effective_until: "2027-02-18"` | legal | 19 |
| KR-OKX-SPOT | okx: coin / buy, sell / cash | grey (D6), example in 5.2 | legal | 14 (13 analogue) |
| KR-OKX-WITHDRAW | okx: coin / transfer_out | exit only (D11): to upbit, bithumb, coinone or korbit at a registered (address, network, tag) | legal | 14, 19 |
| KR-OKX-DERIV / P2P | okx: crypto_perp_or_future / any; okx: any / p2p_buy, p2p_sell | hard_block (OKX blocks South Korea) | legal | 14 |
| KR-OFFSHORE-CEX | binance, bybit, bitget: any | out_of_scope (D10) | policy (D10) | 13 |
| KR-STATE-BLOCKED | kucoin, mexc, phemex, xtcom, bitrue, coinw, poloniex, btcc, bingx, digifinex, + every other site on the KCSC block list of 2026-10-13: any | hard_block (reachable only by VPN) | legal | 15 |
| KR-BITMART | bitmart: any | hard_block (Google Play app block 2025-03; Korean reports of the 2026-10-13 block do not name it) | legal | 15 |
| KR-HYPERLIQUID / KR-DEX / KR-DRIFT | hyperliquid, pumpfun, jupiter, uniswap, drift: any except event_contract | out_of_scope (D10). Enabling needs: age 19+; no auto-buy of new tokens; a liquidation-price warning on perps | policy (D10) | 16, 17, 18 |
| KR-PREDICTION | polymarket, kalshi, limitless, myriad, opinion, predictfun, robinhood, cryptocom, predictit: any | hard_block (Criminal Act Art. 246; platform terms) | legal | 1-6 |
| KR-SPORTSBOOK | sportsbook: any | hard_block (National Sports Promotion Act Art. 48(3); 2022도6462) | legal | 7 |
| KR-IBKR / KR-RETAIL-APPS / KR-OFFSHORE-FX-CFD | ibkr; moomoo, webull, etoro; offshore_fx_cfd: any | hard_block | legal | 36, 37, 38 |
| KR-LOTTERY-RACING | betman, lotto, speedon: any | out_of_scope (D10) | policy (D10) | 8, 9 |
| KR-CONDUCT-EVENT | any venue: event_contract | hard_block (Criminal Act Art. 246) | legal | 1-6 |
| KR-CONDUCT-SPORTS | any venue except betman: sports_bet | hard_block (National Sports Promotion Act Art. 26, 48(3)) | legal | 3, 7 |
| KR-CONDUCT-ROUTE | route ≠ direct | hard_block | legal | 15, 16 |
| KR-CONDUCT-OTHERS | on_behalf ≠ self (orders copied to followers are not self), or tag copy_lead / copy_follow | hard_block (특금법; 2024도10710) | legal | 20 |
| KR-CONDUCT-FX | tag fx_settlement | hard_block (환치기, where business-like) | legal | 20 |
| KR-CONDUCT-SIGNALS | publishes_signal | hard_block | legal | 20 |
| KR-CONDUCT-PROMOTE | tag unregistered_vasp_referral | hard_block (FSC 2026-06-24). TRADEGEN stores and emits no referral, affiliate or invite codes | legal | 20 |
| KR-CONDUCT-MANIP | tags coordinated, self_match, spoof, layer, mnpi, false_statement, self_issued_coin | hard_block (VAUPA Art. 10(1)–(5)) | legal | 20 |

**Dates**
- Crypto, transfer and OKX rows are due by 2026-11-22, and in no case later than 2026-12-02.
- `KR-TRANSFER-OUT` and `KR-OKX-SPOT` end on 2027-02-18, when the travel-rule expansion takes effect: six months after
  promulgation, per FSC 2026-08-11.
- Every other row follows the monthly cadence.

### 5.4 Lifecycle and alerts

- **Stale rows.** A row past `review_by` blocks new exposure with "stale: review by … passed". Exits stay open (D11).
- **Re-review.** Someone drafts it, possibly Claude. The owner signs `approved` for the new bytes. The latest signed
  version stays in force until then.
- **`python -m core.compliance.rules --check [--today …]`** checks:
  - the table, the map, the venue file and the calendar set, against their latest approvals;
  - the owner log: its chain, signatures and seq anchors;
  - the signed code hash;
  - the public-key fingerprint against the first one recorded.

  **Exit codes:**
  - 0: nothing due;
  - 1: something due within 14 days;
  - 2: something overdue;
  - 3: invalid or unapproved state, unsigned code, a broken chain, or a changed key. Exit 3 blocks new exposure;
  - **4: the check itself failed.** `main()` catches every exception, including a missing `cryptography` package, and
    argparse errors map to 4 as well.

  It also prints one JSON summary line: {code, due, overdue, head_seq, fingerprint}.
- **Who sends what.**
  - `alerts.py` renders a fixed template: row id, `review_by`, `auto_off`, days left, the owner-log head as
    "entry #seq", and the key fingerprint, with "KEY CHANGED since <date>" if it differs. Rule free text is never
    interpolated.
  - It shows the Windows toast and writes `alerts.jsonl` through `--log <channel> <ok|fail>`.
- **The daily job.** A local scheduled Claude task runs at 09:00 KST:
  - it runs `--check`;
  - **it alerts every day** while anything is overdue, on code 3 or 4, or when the summary line is missing or does not
    match the exit code;
  - for a row due soon, it alerts on the first run at or below 14 days, and again at or below 3 days;
  - it sends the iOS push via the Claude app and an email **only to `sapientia@korea.ac.kr`**, written literally in the
    task prompt and in `alerts.OWNER_ALERT_EMAIL`;
  - it records each result through `--log`.
- **Authority.** The owner approves the task once; D5 is the standing authority for these self-addressed alerts only.
- **Failures.** A failed channel is announced on the others. The in-app banner and an app-start check cover the times
  the PC is off.

---

## 6. The `decide()` kernel (`core/compliance/gate.py`)

### 6.1 Types

```python
@dataclass(frozen=True, kw_only=True)
class Intent:
    venue: str
    symbol: str                      # every intent names a mapped symbol (coins too)
    counter_symbol: str              # what is paid/received; must form a market listed in venues.yaml
    asset: str; multiple: float      # caller's view; must equal the map's (class is derived, never supplied)
    action: str                      # buy | sell | sell_short | buy_to_cover | write | transfer_out | lend | borrow | p2p_buy | p2p_sell
    financing: str = "cash"
    quantity: float                  # units (> 0)
    notional_krw: float              # >= 0, finite
    destination_venue: str | None = None      # transfer_out only
    destination_address: str | None = None    # transfer_out only
    destination_network: str | None = None    # transfer_out only; must be a network the destination credits
    destination_tag: str | None = None        # transfer_out only; required where the destination needs a memo/tag
    route: str = "direct"; on_behalf: str = "self"; publishes_signal: bool = False
    tags: frozenset = frozenset()
    reservation_id: str | None = None         # set by execution for permits

@dataclass(frozen=True, kw_only=True)
class Context:                       # built ONLY by owner.load_context(now); every field is derived there
    date: date                       # Asia/Seoul calendar date of the decision moment
    active: ApprovedState            # state in force; or RulesTable.invalid(reason)
    snapshot: ApprovedState | None   # last approved immutable snapshot (D11 recovery)
    owner: OwnerState                # verified: flags, caps, limits, addresses, sessions, halted_floors, armed; or BROKEN
    code_hash: str; code_signed: bool        # computed by hashing on disk, compared with the latest code_approved
    session: SessionState
    equity_krw: float                # > 0, finite
    holdings: Mapping[tuple, float]  # (venue, symbol) -> units >= 0 (shorts listed separately, >= 0)
    exposure: Mapping[str, Exposure] # per venue: KRW value of EVERYTHING held there (settlement assets included) >= 0,
                                     # plus reservations {reservation_id: notional >= 0} and promised sell units
```

**Decision** has the verdicts ALLOW | ALLOW_EXIT | ACK_REQUIRED | BLOCK, and records:
- the reasons, strictest first;
- `intent_hash`, `state_hash`, `code_hash`, `owner_head (seq, row_sha256)`, `ctx_hash`, `date` and `decision_id`.

**Permit** is issued only from ALLOW or ALLOW_EXIT. It carries:
- `decision_id`, `intent_hash`, `state_hash`, `session_id`, `reservation_id`, `date`.

### 6.2 Evaluation order (one decision table)

0. **Choose the state.**
   - Use `ctx.active` if it is valid.
   - Otherwise use `ctx.snapshot`, but only for `sell`, `buy_to_cover` and `transfer_out`.
   - Every later step uses that one state.
   - For an exit, a symbol missing from the chosen map is looked up in earlier approved maps in the immutable store.
     If it is still unknown, the result is BLOCK "close manually in the broker app".
1. **Validate the intent.** Any of these gives `BLOCK ("malformed: <field>")`:
   - a non-finite value, a value of the wrong sign, or a wrong type;
   - an id that is not an exact vocabulary member;
   - an unknown symbol;
   - an asset or multiple that disagrees with the map;
   - a (`symbol`, `counter_symbol`) pair that is not a listed market of the venue;
   - inconsistent transfer fields;
   - tags outside the vocabulary;
   - **a `sell` whose quantity exceeds the holdings minus units already promised to unexpired sell permits**
     ("open a short with sell_short, an option with write");
   - a `buy_to_cover` beyond the short held.

   The kernel never raises.
2. **Conduct, and the all-intents part of the floor,** apply to every intent, exits included.
3. **Classify the intent:**
   - **close-long:** a valid `sell` of a non-settlement asset for a settlement asset of that venue;
   - **cover-short:** a valid `buy_to_cover`;
   - **withdraw:** a `transfer_out`, within holdings, to an FIU-registered domestic venue (`upbit`, `bithumb`,
     `coinone`, `korbit`) at a signed registered (address, network, tag) that this venue credits;
   - **new exposure:** everything else. That includes any trade that acquires a non-settlement asset. For example,
     selling USDT for BTC on OKX is a BTC buy.
4. **Exits** give `ALLOW_EXIT` with warnings, and are **not** blocked by stale rows, auto-off, unmet gates, caps, D16, or
   `out_of_scope` / `hard_block` venue rows.
   - **Step 6 does not apply to them.** A withdraw is checked only against the registered set and its address.
   - Under a broken owner log, a withdrawal is BLOCK "withdraw manually in the exchange app", because its address can't
     be verified.
5. **New exposure** requires all three of:
   - a valid `ctx.active`;
   - a valid owner log;
   - `code_signed`.

   Then come the new-exposure part of the floor and the venue rows in force on `ctx.date` (Asia/Seoul):
   - **No matching row:** BLOCK. When several rows match, all apply, and the strictest wins.
   - **stale**, **`hard_block`** or **`out_of_scope`**: BLOCK.
   - **`gated`:**
     - with `requires.live`: BLOCK "needs live broker evidence (execution spec)", which no owner-log event can
       satisfy;
     - otherwise: each `requires.owner` item must be met by signed owner state.
   - **`grey`:**
     - BLOCK if `date ≥ auto_off`, the cap is unset, or `requires` is unmet;
     - BLOCK if the venue's total held value, plus the other reservations, plus this notional exceeds `cap × equity`.
       Verifying a permit excludes only its own reservation.
   - **`ack: per_session`:** ACK_REQUIRED unless the session holds an acknowledgement whose
     `warning_sha256 == sha256(render_warning(row, slots))`, under the current `session_id`.
   - **`allow`:** ALLOW.
   - Effective leverage above `max_leverage` is BLOCK.
6. **New-exposure transfers** (deposits into a grey venue):
   - The destination is evaluated as a `buy` of the same symbol on `destination_venue`, and the stricter result wins.
   - The transfer also needs a per-transfer acknowledgement, and a registered (address, network, tag) the destination
     credits.
7. **Combine.** BLOCK beats ACK_REQUIRED, which beats ALLOW and ALLOW_EXIT.

### 6.3 Permits and plan screening

- **`permit(intent, ctx)`** calls `decide()`, and issues a Permit only for ALLOW or ALLOW_EXIT.
- **`verify_permit(permit, intent, ctx_now)`** recomputes:
  - the intent hash;
  - `decide(intent, ctx_now)` is ALLOW or ALLOW_EXIT;
  - the same `session_id`, `reservation_id` and Asia/Seoul date;
  - a `state_hash` that is the issue-time hash or a newer in-force state.

  Atomic reservation, single use and the audit log belong to the execution spec.
- **`screen(plan, ctx, first_stake_krw)`** decides the plan's single leg as a `buy` at the first stake, which the odds
  engine computes (7.1).
  - It scans `[start, start + horizon)` for any `review_by`, `auto_off` or `effective_until`. Each one found is flagged
    `RULE_CHANGE_IN_HORIZON`, and the simulation exits on that date, or at the next check point when the date falls on
    a non-session day.
  - It returns a hashed `Screening`.

### 6.4 The owner log, signing and snapshots

**The log** (`~/.tradegen/compliance/owner.jsonl`), append-only.
- **Line fields.** Each line carries `seq`, `prev_sha256`, `row_sha256` and either:
  - `sig`, an Ed25519 signature by the owner key, for **owner entries**; or
  - no signature, for **system entries**: `system_halt {floor_krw}` and `system_disarm {session_id, reason}`. These are
    the only unsigned kinds, and they can only tighten.
- **Anchors.** (seq, row_sha256) is recorded in every `alerts.jsonl` row, every snapshot and the approved store, and
  "owner log entry #seq" is printed in every alert email.
- **BROKEN** means any of:
  - a bad signature on an owner entry;
  - an unsigned line of any other kind;
  - fewer than `seq` lines for some recorded anchor;
  - a line whose `row_sha256` differs from its anchor.
- **What a broken log means.** All owner state counts as absent: new exposure is BLOCK, and withdrawals are manual.
- **The residual.** Deleting every local anchor and the log together is caught only by the owner noticing that the
  emailed #seq went down.

**Events**
- approvals: `approved {kind, sha256}` (rules, instruments, venues, calendar), `code_approved {sha256, files}`;
- evidence: `course_completed`, `broker_approval`, `age_of_majority {birth_date, evidence}`;
- settings: `cap_set`, `limit_set {total_loss_floor_krw, daily_loss_krw}`;
- transfers: `withdrawal_address {venue, symbol, network, address, tag, evidence}`;
- sessions: `session_armed`, `session_ack {session_id, row_id, warning_sha256}`, `transfer_ack {intent_hash,
  warning_sha256}`;
- system (unsigned): `system_halt`, `system_disarm`. The execution spec writes halts here.

**D12.** Tightening takes effect at once. Loosening applies only from the next Asia/Seoul date, never while `armed`, and
never for a floor in `halted_floors`.

**Snapshot (D11 recovery).** After every successful verification, `load_context` stores the resolved state and the
in-force hashes immutably. Exits under a broken log use the last one.

**Unset limits.** The odds engine refuses with `LIMITS_UNSET`, and execution will refuse to arm.

**`load_context(now)`** is the only non-pure constructor in `core/compliance`, and the only producer of `Context`:
- it hashes the code on disk and sets `code_signed`;
- it verifies the log and builds `OwnerState`;
- it loads the in-force tables from the store, and the snapshot.

The execution spec must route every caller through it. No caller may build a `Context` by hand.

**The code hash.** It is computed over sorted (relative path, sha256) pairs of:
- the `.py` files of `core/compliance` and `core/odds`;
- their in-repo `.py` import closure, found by an AST import scan (for example `config.py`, `core/isolation.py`,
  `core/calendars/**`, the `core/quant` and `data/` modules they reach).

Data files are covered by their own approvals, and the public key by the fingerprint rule below. The signing prompt
lists every file. Each Decision records the code hash.

**Signing (D14).**
- **The signer lives outside the repo.** The owner keeps it as `%USERPROFILE%\tradegen-signer\sign.py`: one small file
  using only the standard library and `cryptography`.
- **Verifying the signer.** The owner reads it in full once, writes its sha256 down **away from the PC**, and before
  every passphrase entry runs `certutil -hashfile sign.py SHA256` in their own terminal. Any mismatch means they do not
  type the passphrase.
- **The repo copy** (`tools/signer/sign.py`, outside `core/`) is only a proposal. Updating the owner's copy is a
  deliberate owner act: read the diff, re-hash, re-record.
- **Where it runs.** In the owner's own Windows Terminal. `sign.py` refuses to run when a `CLAUDECODE` or `CLAUDE_CODE_*`
  variable is set, when a parent process is the Claude app, or when stdin is not a TTY. It shows exactly what will be
  signed, together with a fresh random code that must be **typed**, not pasted.
- **The key file.** `~/.tradegen/compliance/owner_key.enc` holds a 32-byte Ed25519 seed, encrypted with AES-256-GCM:
  - the key comes from scrypt over the passphrase, with a 16-byte random salt, n = 2¹⁷, r = 8, p = 1;
  - the nonce is 12 random bytes;
  - the AAD is the header {format version, KDF parameters, pubkey fingerprint}.

  The passphrase needs at least 20 characters, or 5 diceware words. In code, names say `signing_key` (T-RO-01), and
  the key is serialised with `from_private_bytes` / `private_bytes_raw`.
- **Public key and fingerprint.**
  - `owner_pubkey.pem` is the trust anchor. The owner also writes its fingerprint down away from the PC.
  - The first recorded fingerprint is kept in `alerts.jsonl` and in every alert email. A different fingerprint gives
    exit 3 and "KEY CHANGED since <date>".
  - A rotation is valid only if it is signed by the old key.
- **Claude** never runs the signer, never asks for the passphrase, and never writes owner entries.
- **The dependency.** `cryptography==<exact version>` goes in `requirements.txt`, `pyproject` dependencies and
  `constraints.txt`. An ImportError in `owner.py` means a BROKEN state and an alert naming the package. Its RECORD
  hash is recorded at install.

**The honest limits.** Signatures stop forged entries under the pinned key, and stop a restored old file from counting.
A process with the owner's file access could still do the following:
- **swap the key and the log together.** That shows up as a changed fingerprint in the emails, which only the owner
  comparing against the fingerprint written away from the PC can confirm;
- **edit the gate or its import closure.** That is caught by the code hash until the owner signs, so the owner's
  review of each diff before signing is the boundary;
- **edit the venv or `.env`.** Both are outside the code hash;
- **tamper with the signer.** That is caught only by the owner's off-PC hash check before every passphrase entry.

The protection is strong against accidents and against casual or scripted misuse. It is not proof against a determined
agent with full access to the account.

---

## 7. The odds engine (`core/odds/`)

### 7.1 Plans and stakes

```python
@dataclass(frozen=True, kw_only=True)
class Leg:
    venue: str; symbol: str          # whitelist classes: share (KRX, US), etp_1x, coin; cash; long
    model: str                       # "bootstrap" (TwoPointBootstrap) | "garch_t" (US and crypto only)
    bracket: Bracket | None = None   # take-profit +u, stop -d; None = buy at the first open and hold
    sizing: str = "floor_safe"       # "floor_safe" | "stop_based" (bracket legs only)
    edge_source: str = "none"        # "none" | "assumed" (bracket legs) | "replay:S_C3_crypto_trend_krwbtc" (D13)
    assumed_p: float | None = None

@dataclass(frozen=True, kw_only=True)
class Plan:
    name: str                        # cosmetic; never hashed into a seed
    track: str                       # "moonshot" | "compounding"
    stake_krw: float; target_krw: float     # target before income tax, fixed in KRW
    fx_krw_per_usd: float
    start: date; horizon_days: int   # half-open [start, start + horizon_days)
    leg: Leg
    fraction: Fraction               # fixed(f) | kelly(c <= 0.5) | bold()
```

**The cost ledger.**
- At each fill, the per-side rate κ = `cost_per_side(book, price, on, side).bp` × 1e-4 (section 4), charged on both
  sides. The sell tax is inside the table rate.
- Fixed charges φ_b and φ_s come from `venues.yaml`.
- Under the stress scenario both are doubled. Under a limit-down carry the exit charge is doubled again: a flat 2×,
  which never compounds.
- **R_exit = 4·φ_s**, the worst-case exit charge, is always reserved. A book where 4κ ≥ 1 is refused.

**Affordability.** For every entry, after lot rounding and in each cost scenario:
- **always:** s(1 + κ) + φ_b + R_exit ≤ W. Cash after any entry covers the worst exit charge, so equity never goes
  below 0.
- **floor-safe** (the default): s(1 + κ) + φ_b + R_exit ≤ W − L. Cash never falls below L + R_exit, so even a total loss
  of the position leaves at least L, and **L_min = L**.
- **stop-based** (bracket legs only): s[d + κ + κ(1 − d)] + φ_b + φ_s ≤ W − L before gaps, plus the always rule. Here
  **L_min = 0**.

**Fractions**
- **`fixed(f)`:** s = f·W, then cut by affordability.
- **`kelly(c)`:** only on the D13 replay card.
  - R_cons = R_net − mean(R_net) + `LIVE_SHARPE_MULTIPLIER`·μ_lb, with the variance unchanged.
  - μ_lb is the one-sided 95% lower bound (the 5th percentile) of the out-of-sample mean, from a stationary block
    bootstrap with B = 2,000 and the card's block length of 10.
  - f* = argmax over f ∈ [0, 1] of mean ln(1 + f·R_cons), and f* = 0 when μ_lb ≤ 0. The stake is s = c·f*·W, then cut
    by affordability.
  - Its label: "aims at long-run growth, not at reaching your target".
- **`bold()`** (bracket legs): s = min(ceil_lot(max(s_reach, venue_min)), floor_lot(s_afford)).
  - s_reach solves s(u − κ(2 + u)) − φ_b − φ_s = T − W.
  - s_afford is the largest stake affordability allows.
  - A stake that cannot reach T stakes s_afford and tries again after a win, as Dubins–Savage bold play does far from
    the goal.
  - It is refused in any cost scenario where the net win coefficient u − κ(2 + u) ≤ 0.

**Rounding and re-entry**
- Stakes round **down** to whole units, or to fractional units where `venues.yaml` allows. The only exception is bold
  play's reaching stake above, which rounds up when that is affordable.
- A stake below the venue minimum means no bet; it is never rounded up.
- After an exit fills, the next entry happens at the **next** check point.

**Refused with named reasons:**
- `UNSUPPORTED_PRODUCT`: outside the whitelist, a multiple ≠ +1, or a short, credit or option leg;
- `MULTI_LEG_UNSUPPORTED`;
- `LIMITS_UNSET`;
- `CALENDAR_UNSIGNED`;
- `MODEL_NOT_FOR_LIMITED_VENUE`: GARCH-t on a KRX leg;
- `STUCK_AT_START`: no affordable first stake.

### 7.2 The no-edge law, models and edge sources

**No edge means a conditional martingale at every point where the simulator can act:** each session's open and close.
Given everything so far, the expected next price equals the current one. Costs then make every trade's expectation
negative. Two traps were ruled out in review:
- zero log drift is not zero edge;
- per-row demeaning of a block bootstrap lets timing rules harvest historical serial patterns.

**`TwoPointBootstrap`** (the primary model; KRX, US and crypto legs):
- **Price series.** Each leg is priced in KRW, so historical KRW/USD moves are part of the series:
  - US legs: price × KRW=X;
  - OKX legs: Binance BTCUSDT × Upbit KRW-USDT, falling back to KRW=X on dates before Upbit listed KRW-USDT. The dates
    are recorded and flagged `PROXY_DATA`.
- **Moves.** From each historical session the model takes two magnitudes: the overnight move m_o = |ln(open/previous
  close)| and the intraday move m_i = |ln(close/open)|.
- **Blocks.** Rows are drawn in stationary-bootstrap blocks with mean length b = max(pw_block(r), pw_block(r²)), using
  kind "stationary", where r is the close-to-close log return. The 0.5× and 2× sensitivity runs use
  max(1, round(mult·b)).
- **The kernel.** At each check point, with current price p and session band [D, U]:
  - x_u = min(p·e^{m}, U) with probability q, and x_d = max(p·e^{−m}, D) with probability 1 − q;
  - q = (p − x_d)/(x_u − x_d), and when x_u = x_d the price stays at p.
  - E[next | p] = p holds algebraically.
- **Bands.** KRX: the reference (the previous session's close) × (1 ∓ dated `price_limit`), rounded to the tick ladder,
  D up and U down, then **clamped** so that D ≤ reference ≤ U. Venues with no daily limit use [0, ∞).
- **Band edges.** A session that opens at its band edge stays there until the close. That is forced, and such sessions
  are flagged `BAND_EDGE_SESSIONS`.
- **Limit-down locks.** A check at D that would exit is a lock. The exit stays queued across checks and sessions until
  the first check strictly above that session's D, at a flat 2× exit charge. A position still locked at the horizon is
  valued at the locked price less the carried exit charge (`LOCKED_AT_HORIZON`).
- **Special regimes.** Symbols in a special KRX reference regime (IPO days, resets) are refused (`SPECIAL_REGIME`).
- **The card** says "price checks at the open and the close only" (`CHECKS_AT_OPEN_CLOSE`).

**`GarchT`** (US and crypto legs only):
- It fits with `garch.fit_garch` and simulates with `simulate_returns(fit, rate_daily=0.0, bound=Z_BOUND)`. Checks
  happen at the close only (`CLOSE_ONLY_CHECKS`).
- **Two named checks on a pilot run; the model is dropped, with a note naming the failed check, if either fails:**
  1. **Deterministic:** for every σ_t on the pilot paths, |exp(c_quad(σ) − c_table(σ)) − 1| ≤ 1e-7 per step and ≤ 1e-6
     compounded over the horizon, where c_quad is an independent quadrature.
  2. **Statistical:** |mean over paths of e^{r_h} − 1| ≤ 4·SE_h at every step.
- **HIDDEN_EDGE is unavailable for every GARCH-t leg.** Bounding z does not bound σ_t, so no finite deterministic range
  exists.

**Brackets** are evaluated pathwise at the check points: take-profit +u and stop −d, each filling at the check price.
Under the martingale, a bracket's mean payoff before costs is 0.

**Edge sources**
- **`none`:** the default and always the headline.
- **`assumed`** (bracket legs): the owner's typed win probability p.
  - **A win** means the take-profit filled before the stop, counted among brackets resolved by take-profit or stop.
    The card prints the unresolved share beside it: horizon, daily-loss, rule-date and locked exits.
  - **The tilt.** The kernel is tilted, q′ = q·e^{θ}/(q·e^{θ} + 1 − q), with θ found by bisection on a pilot run so
    that this win ratio equals p. A p the tilt cannot reach is refused.
  - **p₀** is computed the same way under no edge. The bracket count needed to tell p from p₀ is n =
    ((1.645·√(p₀(1 − p₀)) + 0.842·√(p(1 − p))) / (p − p₀))², assuming independent resolved brackets. For example, 617
    for 55% versus 50%, and 153 for 60%.
- **`replay:S_C3_crypto_trend_krwbtc`** (D13). This is a separate plan type: a pure replay of the validated strategy.
  - **Input:** the KRW-BTC daily closes from the study's own source, `UpbitPublic().daily("KRW-BTC", days=4000)`. They
    are truncated to [card.data.start, card.data.end] (3,288 sessions) and hashed, and the digest is compared with the
    cached study file.
  - **Steps:**
    1. `strategies.pnl_matrix(closes, strategies.crypto_trend, card.rules.grid, cost_bps=card.rules.cost_bps_per_side)`,
       with `lookbacks = (7, 14, 21, 28)` and `mas = (10, 20, 50, 100, 200)` pinned as constants in `models.py`;
    2. `validate.walk_forward(…, embargo=card.rules.embargo)`;
    3. `validate.score_strategy(…, n_trials=card.trials.N_total, seed=card.seed, domain={"hysteresis": (0.0, 0.889)},
       benchmark = buy-and-hold)`.
  - **Must reproduce the card:** out-of-sample Sharpe 1.216 ± 0.02, verdict PASS, chosen hysteresis 0.667. Otherwise the
    plan is refused with `CARD_NOT_REPRODUCED`.
  - **It never imports `docs/asset_expansion_study.py`.**
  - **Digests:** the input closes, the replay output, and the aggregate `results.csv` (`results_md5`).
  - **The card's column** resamples the replayed out-of-sample net daily returns (close-to-close; the card is close-only)
    in stationary blocks, with the mean multiplied by `LIVE_SHARPE_MULTIPLIER`. The card's 10 bp is already inside;
    only whole-unit rounding and the KRW 5,000 Upbit minimum are added.

**Data rules**
- `SYNTHETIC_REFUSED`; a provisional last bar is dropped.
- Series hashes are md5 of canonical JSON {symbol, source, dates, open, close, adjustment, status}.

**Delisting stress** (single-name and single-coin legs):
- It adds two columns, h ∈ {0.30, 1.00} (`tf_books.DELIST_STRESS`), each with one delisting event at the first check
  after entry, as a worst case. Its losses are booked in the cost ledger.
- Coins use the same pair, because no crypto-specific figure was researched.

**Costs, minimums and calendar.**
- Costs follow section 4 and 7.1. Minimums and ticks come from `venues.yaml`; a missing entry gives `NOT_TRADABLE`.
- Steps are calendar days. KRX and US legs move on their market's sessions (`cal`), and crypto moves daily.

### 7.3 Simulation and outcomes

- **Terminal outcome**, exactly one per path:
  - **REACHED:** liquidation value ≥ T, after exit costs and the sell transaction tax inside the cost rate, and before
    income tax. Moonshot paths stop here.
  - **AT_FLOOR:** the path can no longer trade inside the floor rules. Either:
    - the liquidation value is ≤ L at a fill (stop-based overshoot kept); or
    - the largest affordable stake is below the venue minimum.

    It is absorbed. The card shows what is kept, **between KRW L and KRW L + X**, where X is at most the minimum order
    plus the reserved charges.
  - **RUNNING:** still trading at the horizon, at liquidation value, flagged `LOCKED_AT_HORIZON` where relevant.
- **First passage.** `reached_by_deadline` is true when the liquidation value was ≥ T at some check point. On compounding
  cards it can differ from the terminal outcome.
- **The daily loss limit** is checked at the check points. A breach exits and stops trading for the rest of that day.
- **Seeds and streams.**
  - The market seed is sha256(data hashes ‖ calendar digest ‖ comparison id ‖ run counter), shared by every plan in one
    comparison.
  - Streams are `SeedSequence(int.from_bytes(seed, "big"), spawn_key=(chunk, stream_id))`. The bootstrap index and sign
    streams are keyed by data set and chunk; the GARCH innovations by symbol.
  - Cosmetic fields are excluded, and the owner never chooses the seed.
- **Scale.** CHUNK = 200,000, and n must be a multiple of it. Defaults: 1,000,000 paths for moonshot plans and 200,000
  for compounding plans.

### 7.4 References (`bold.py`)

- **`ceiling(W0, L_min, T)`** = (W₀ − L_min)/(T − L_min).
  - L_min = L under floor-safe sizing; otherwise 0, which gives W₀/T.
  - The no-edge column always shows it, worded **"No plan without a real edge that keeps this floor can beat 1 in N"**,
    and always runs the breach check.
  - Edge columns print "Without the edge assumed here, no plan that keeps this floor can beat 1 in N".
- **`structural_max(plan, cal)`** applies only to buy-and-hold KRX or KONEX legs: (1 + limit)/(1 − limit) ×
  (1 + limit)^{n−1} over the leg's n sessions, counted from the calendar.
  - When the target exceeds it, the card prints **"IMPOSSIBLE for this buy-and-hold plan: KRX's daily band allows at
    most N× in these S sessions"** and no probability.
  - No market-wide bound is claimed for bracket legs.
- **`bracket_reference(plan)`** is an **estimated** reference, not a certified bound. It is a dynamic programme using
  the simulated joint law of a bracket's (realised payoff, duration). It never drives a red flag.
- **`bold_even(x, p)`:** the exact even-money recursion, used in regression tests only.

### 7.5 The report

All owner-facing text comes from one reviewed **sentence catalogue** with numeric slots. Each plan card shows:

1. **The model and its check points.**
2. **The typical result first.**
   - "The middle month ends with KRW M. In P% of months you end at your floor, keeping between KRW L and KRW L+X, and
     can no longer trade."
   - **The average line,** chosen by comparing the plain mean X of terminal liquidation values (with its standard
     error) with W₀ − Y, where Y is the cost ledger's average:
     - when |X − (W₀ − Y)| ≤ 2·SE: "Averaged over all simulated months: about KRW W₀−Y (costs average KRW Y; the
       simulation's own average, KRW X ± SE, agrees). That average includes rare jackpots and is not what usually
       happens."
     - otherwise HIDDEN_EDGE speaks.
   - **The cost words follow the book:**
     - crypto: "fees";
     - KRX: "fees and the securities transaction tax";
     - the stress column adds "and the delisting stress loss".
   - **Edge columns** say "an average gain of KRW G, only if the edge in this column is real" when the mean is a gain.
3. **The headline pair.**
   - **Moonshot:** P(reached KRW 42,000,000 before income tax).
   - **Compounding:** "was worth KRW T at some price check in K months; ended at or above it in K′ months". The ladder
     rungs read "ended at or above".
   - Then P(at your floor) and the ladder.
4. **The plain sentence.** "In 1,000,000 made-up months (from a model in which nobody has an edge, not real history),
   this plan reached KRW 42,000,000 before income tax in 63, about 1 in 16,000 (counting noise alone: between 1 in
   12,000 and 1 in 21,000; other models give 1 in A to 1 in B; the bug checks are coarser than these ranges, and
   nothing here covers the model being wrong)…"
5. **Tax.** From each leg's `tax_basis`: `krx_small_holder_exempt`, `overseas_22pct_over_2.5m`, or
   `crypto_22pct_from_2027` (unless postponed again). Unsupported combinations are refused.
6. **The ceiling** (worded as in 7.4) and the base rates of section 3, with their populations and dates.
7. **Precision.**
   - Clopper–Pearson: two-sided 95% for k > 0, and a one-sided 95% upper bound for k = 0 ("below resolution: under
     about 3 in n").
   - Structural zeros (IMPOSSIBLE, no trades) are worded as such.
   - No probability slot ever renders as zero.
8. **Model spread.** The primary model is the two-point bootstrap. Also shown: GARCH-t where eligible, a parametric
   GARCH-t refit (B = 20), and the bootstrap at 0.5× and 2× block length.
   - It appears as a range with the lowest lower and highest upper bound.
   - A member with k = 0 shows its low end as "below about 3 in n".
   - KRX cards say: "the same model with other block lengths gives …; no second model family is available for KRX".
9. **Columns:**
   - **No edge**, always the headline.
   - **`ASSUMED_EDGE`:** "These numbers are only as true as the win rate you typed (W%). This bracket's no-edge win rate
     is P0% (U% of brackets end unresolved). Telling them apart would take about N recorded brackets. Without the edge
     you typed, no plan that keeps this floor can beat 1 in M." It also shows the typical result and P(at your floor).
   - **`TESTED_REPLAY`** (D13), on its own card: "This replays a tested bitcoin trend strategy (S_C3) on its own
     2019–2026 out-of-sample results, with 40% of its average return removed. Most of that return came from bitcoin
     rising in those years, which the no-edge column leaves out: just holding bitcoin then had a Sharpe ratio of 0.79,
     against 0.73 for this replay after the cut. Its tested advantage over holding bitcoin was +0.43 Sharpe (90% range
     +0.03 to +0.83). Backtest edges often shrink or vanish in live trading; read this as the hopeful case."
10. **Flags:**
    - **`HIDDEN_EDGE`** runs **only in the no-edge column**, and only on two-point bootstrap legs. It is unavailable for
      GARCH-t and the stress columns, and not applicable to edge columns.
      - X = W_τ + C_τ − W₀, with τ = the first of REACHED, AT_FLOOR or the horizon; for this test both tracks stop at T.
      - Its range is R = ((T + φ_s)/(1 − κ))·e^{m_max} + N_checks·C_max, where m_max is the largest historical magnitude.
        W_τ ≥ 0 holds by the always rule.
      - It is red when |mean X| exceeds the empirical-Bernstein bound b_δ = √(2V·ln(4/δ)/n) + 7R·ln(4/δ)/(3(n − 1)),
        with δ = 1e-4.
      - **Resolution** is printed in KRW, as a percentage of the stake, and as "this check would miss a model error
        that moved the chance of the target by up to about 1 in ⌈(T − L_min)/b_δ⌉".
      - Its two wordings: "makes money without any edge" and "loses more than its costs explain".
    - **`CEILING_BREACH`** (no-edge column only, against the analytic ceiling):
      - amber "preliminary evidence, about 5% false-alarm rate per check: rerun with more paths" when the one-sided 95%
        Clopper–Pearson lower bound exceeds it;
      - red when the one-sided (1 − 0.001/m) bound does, where m is the number of no-edge (model × cost-scenario) cells
        on the card, the stress columns excluded.
    - `ABOVE_ESTIMATED_REFERENCE` (amber), `IMPOSSIBLE`, `BELOW_RESOLUTION`, `GREY_LEG`, `PROXY_DATA`,
      `CHECKS_AT_OPEN_CLOSE`, `CLOSE_ONLY_CHECKS`, `BAND_EDGE_SESSIONS`, `LIMIT_GAP`, `LOCKED_AT_HORIZON`,
      `COST_DOMINATED`, `NOT_TRADABLE`, `STUCK_AT_START`, `RULE_CHANGE_IN_HORIZON`, `SPECIAL_REGIME`.
11. **"Not in these numbers":**
    - income tax (estimated, not simulated);
    - won-dollar moves beyond the historical range in the data;
    - Upbit withdrawal holds after a KRW deposit, and the Upbit-to-OKX route closing without notice;
    - exchange freezes or failure;
    - delistings and Upbit warnings (survivorship);
    - KRX halts, VI auctions and designations;
    - intraday moves;
    - unfilled orders beyond what is modelled;
    - broker refusals;
    - hacked or locked accounts;
    - rule changes.

    "Most of these make the real result worse; none makes a no-edge plan better."
12. **Footer.** "These numbers describe rules you wrote, run in a model. They are not advice, and TRADEGEN does not
    recommend any plan. A higher chance of reaching the target does not make a plan better."

**Comparing plans**
- There is no ranking by P(target). Plans are listed in creation order, or by smallest average loss.
- The fixed moonshot caption: "With no real edge, a higher chance of the target generally comes from putting more of
  your stake at risk, sooner. Check P(at your floor) beside it. Higher here means riskier, not better."
- The comparison prints: "You compared K plans (and tried J typed win rates) in this session. The highest-looking
  figure is the luckiest of K."
- Before arming, the plan is re-run on a fresh market seed.

**Language guard**
- All text comes from the catalogue.
- Whole words banned: best, optimal, recommended, safe, guaranteed, sure, ideal, risk-free, low-risk, proven, "should",
  "worth trying", "good chance", "likely to reach". Korean entries are added once a Korean UI exists.
- Internal names never appear in rendered text.

**Provenance** recorded with every report:
- the in-force hashes, the owner-log head (seq), the code hash and the key fingerprint;
- the data hashes and the calendar version and md5s;
- the model, seed, n, CHUNK, NumPy and `cryptography` versions;
- the edge source;
- `repo_anchor()` and `tree_hash()`.

---

## 8. Testing

**Setup.**
- Two new suites run under `tests.macro_acceptance.hermetic()`, with every bars and data-client seam patched:
  `compliance` (`tests/compliance_acceptance.py`) and `odds` (`tests/odds_acceptance.py`).
- `TRADEGEN_HOME` points to a temp dir. A test key pair is used, and the real key is never touched.
- Everything is built test-first.

**compliance**
1. **Loaders:**
   - duplicate keys, anchors, native dates, oversized files, `any` on an allow row and out-of-vocabulary values each
     make the table INVALID;
   - a D16 row without `requires.live` is INVALID;
   - an ETP that cannot be derived, or a `crypto_spot*` underlying mapped outside `etp_crypto_spot`, is INVALID;
   - the monthly and `known_changes` rules hold;
   - all 38 matrix rows are covered.
2. **What is in force:**
   - restoring an older approved file does not count; only the latest approved hash does;
   - a draft differs and blocks nothing until it is signed;
   - an unsigned code hash blocks new exposure;
   - a changed key gives exit 3;
   - `--check` exits 4 on an injected exception and on a missing `cryptography`.
3. **Hard blocks:**
   - each conduct class and tag;
   - the floor with the table rows deleted;
   - a randomised property test;
   - the new-exposure floor items still let a held IBIT be sold.
4. **Classification:**
   - TQQQ is `etp_leveraged`, and 252670 is `etp_leveraged` (a 2x inverse);
   - SH is `etp_index_inverse`;
   - a single-stock −1x product is `etp_single_stock`, which is BLOCK under D16;
   - IBIT, and GDLC or EZPZ mapped as `us_etp` with a basket or `crypto_spot` underlying, are `etp_crypto_spot`, which is
     BLOCK;
   - BITO is `etp_crypto_futures_1x`, which is ALLOW;
   - credit is BLOCK (D15); lend and borrow are BLOCK (D15);
   - a short with every owner event signed stays BLOCK (`requires.live`).
5. **Fail-closed inputs:**
   - NaN, infinity, negatives, wrong types, case variants, unknown tags, inconsistent transfer fields, negative exposure
     and an unlisted market are each BLOCK;
   - a sell beyond holdings, or beyond promised units, is BLOCK;
   - an option sell with no holding is BLOCK;
   - fuzzed input never raises.
6. **Exits (D11):**
   - on 2026-12-03, an OKX BTC→USDT sell gives ALLOW_EXIT, while USDT→BTC is new exposure and BLOCK;
   - OKX → Upbit withdrawal gives ALLOW_EXIT **even with KR-DOMESTIC-SPOT stale and the code unsigned**;
   - a wrong network or a missing tag gives BLOCK;
   - with a broken owner log, closing uses the snapshot and a withdrawal is manual;
   - with an invalid state and a valid snapshot, a close-long passes step 1;
   - with no snapshot, closing is "close manually";
   - conduct still blocks exits.
7. **OKX new exposure:**
   - no acknowledgement, a wrong hash or an old session gives ACK_REQUIRED;
   - an unset cap, a total held value over the cap (USDT included), missing age, or a date ≥ 2026-12-03 gives BLOCK;
   - Asia/Seoul boundary: 2026-12-02T23:59:59+09:00 ALLOW, 2026-12-03T00:00:00+09:00 BLOCK.
8. **Permits:**
   - verification excludes only the permit's own reservation;
   - two permits cannot share capacity;
   - forged permits, other intents, sessions or dates, and a hand-built Context (not from `load_context`) are refused;
   - purity: `open`, `socket.connect` and `time.time` are patched to raise, the module's date names are swapped, and an
     AST scan shows no wall-clock call.
9. **Owner log:**
   - an edited last line, a lower seq than an anchor, an unsigned owner entry and a deleted `system_halt` are each
     detected;
   - a loosening is deferred, refused while armed, and refused after a halt (D12);
   - the signer refuses under `CLAUDECODE` and non-TTY stdin, and needs the typed code;
   - the key file round-trips with the stated KDF parameters;
   - no `private_key` or `seed_phrase` text appears in `core/`;
   - task A0: links under the state root are refused, and final-target checks hold.
10. **Alerts:** exit codes 0 to 4 and the JSON summary; daily alerts on 3, 4 or a missing summary; threshold alerts
    survive a missed run; the template contains no free text.

**odds**
1. **The martingale law:**
   - E[next | p] = p to 1e-12 on random p and random bands, the tick-clamped edges included;
   - prices stay inside the band, including the 100 → 70 → 100 case;
   - a stop, a bracket and buy-and-hold each have a mean payoff of 0 before costs under every model;
   - the repo's `drift="zero"` and per-row demeaning both fail this check;
   - both GARCH pilot checks pass on fixture fits and fail on a corrupted correction table.
2. **HIDDEN_EDGE:**
   - the bound function is tested on synthetic bounded X at δ_test = 0.05 with at least 2,000 replications: the
     Clopper–Pearson upper bound of the alarm rate is ≤ 0.05;
   - the δ = 1e-4 formula is unit-tested against hand values;
   - a planted edge of twice b_δ is flagged;
   - it is "unavailable" for GARCH-t and "not applicable" for edge columns, and a typed p > p₀ does not raise it.
3. **Exact values:**
   - `bold_even` gives 0.1000%, 0.0816%, 0.0346% and 0.0106%, and 0.0400% with L at half the stake;
   - simulated bold play on an even-money fixture matches;
   - the ceilings are never breached at the Bonferroni level.
4. **Mechanics:**
   - buy-and-hold KRX at 1,000× is IMPOSSIBLE with N computed from the fixture calendar;
   - a bracket KRX leg is not flagged IMPOSSIBLE;
   - a limit-down lock persists across checks at a flat 2×;
   - LOCKED_AT_HORIZON;
   - AT_FLOOR under floor-safe sizing keeps between L and L+X;
   - bold play's reaching stake rounds up when affordable, and a path reaches T exactly in the even-money fixture;
   - re-entry happens at the next check point;
   - a forced exit at a rule date;
   - REACHED is measured after the in-rate costs.
5. **Ledger:**
   - the always rule keeps equity ≥ 0 under 2× stress plus carry;
   - floor-safe keeps equity ≥ L;
   - bold is refused where the net coefficient is ≤ 0 under any scenario;
   - the per-fill tick floor raises cost: a 2,005-KRW ETF fill costs at least 13.8 bp per side;
   - no separate sell tax is added.
6. **Refusals:** `UNSUPPORTED_PRODUCT`, `MULTI_LEG_UNSUPPORTED`, `LIMITS_UNSET`, `CALENDAR_UNSIGNED` (unsigned files,
   or files lacking a signed owner approval), `MODEL_NOT_FOR_LIMITED_VENUE`, `SYNTHETIC_REFUSED`, `NOT_TRADABLE`,
   `STUCK_AT_START` and `CARD_NOT_REPRODUCED`.
7. **The D13 replay:**
   - it is deterministic on the fixture closes;
   - with the pinned constants it reproduces the card's statistics, and a changed constant is refused;
   - it never imports the study runner;
   - Kelly is 0 when μ_lb ≤ 0, and f* stays within [0, 1].
8. **Seeds:** plans in one comparison share streams; renaming changes nothing; a partial chunk is refused.
9. **Report:**
   - the typical result comes first;
   - the average line follows its agreement rule;
   - the compounding wording;
   - the tax, base rates (with dates), footer and "not in these numbers" box are present;
   - structural zeros are worded as structural;
   - a k = 0 spread member is worded as below resolution;
   - no banned word appears in the catalogue;
   - the K note and the caption are present.

**Existing guards stay in force:** test_08, test_09, T-RO-01 (including `private_key` and the `/trading/` path) and
T-CTX-01 with the extended prefixes. T-RO-02 is unaffected.

## 9. Error handling

- **Gate:**
  - it never raises;
  - invalid, unapproved or unsigned state, or unsigned code, blocks new exposure (exit 3, alert), while exits follow
    D11;
  - a broken owner log means withdrawals are manual and closing uses the snapshot;
  - `verify_permit` refuses any mismatch.
- **Odds** refuses with named reasons (section 7) and never prints a probability from a refused run. A model that fails
  a pilot check is left out of the spread, with the check named.
- **Alerts:** a failed check is exit 4, and it is alerted daily.
- **Paths:** everything is written under `~/.tradegen`, with final-target checks (A0).

## 10. The guardrails, in plain language

| Guardrail | What it protects you from | What you see | Who may change it |
|---|---|---|---|
| No-edge martingale | A model that quietly "makes money" with no edge, or timing rules exploiting old patterns | Nothing; it is the default | No one; edges get their own columns |
| HIDDEN_EDGE | **Large** bugs that hand a plan free money, or lose more than costs | Red with one of two wordings; the card prints how large an error it could miss; "unavailable" for GARCH-t | No one |
| Ceiling | Believing a no-edge plan that keeps your floor can beat 1 in N (1,000; 2,000 with a floor at half the stake) | "No plan without a real edge that keeps this floor can beat 1 in N." | It is maths |
| CEILING_BREACH | Impossible numbers | Amber "preliminary evidence…", or red "do not use these numbers" | No one |
| IMPOSSIBLE | A buy-and-hold KRX target beyond the daily band | "KRX's daily band allows at most N× in these S sessions" (about 95× to 459× in 30 days) | It is a market rule for buy-and-hold only |
| Typical result first | Mistaking the jackpot-inflated average for the usual month | "The middle month ends with KRW M…" | No one |
| At your floor | Thinking losing months end at exactly L | "You end at your floor, keeping between KRW L and L+X" | — |
| Precision and model spread | Counting noise and one model mistaken for your real odds | "Counting noise alone: … ; other models give …" (KRX: block-length variants only) | Adding models is allowed |
| Open/close checks | Thinking stops fire at intraday lows | "Price checks at the open and the close only" | A future intraday model needs its own martingale test |
| Floor-safe sizing | Losses running past your floor | "Your floor holds even if this position goes to zero" | The owner chooses per leg |
| 2× costs and the tick floor | Costs eating the edge | A second column; per-fill costs never below the repo's floor | No one |
| Minimum tickets | A plan that cannot trade its size | "Can't open" (STUCK_AT_START), or AT_FLOOR | The owner, via the signed venue table |
| LIMIT_GAP / LOCKED_AT_HORIZON / BAND_EDGE_SESSIONS | Assuming exits always fill, and capped sessions | The worst overshoot; "still locked at the end"; capped-session count | They describe how markets behave |
| Typed win rate | A guessed edge dressed up as odds | "Only as true as the win rate you typed… about N recorded brackets…" | The owner types it; never in the headline |
| Tested-strategy replay | Mistaking bitcoin's past rise for strategy skill | "Most of that return came from bitcoin rising… advantage +0.43 Sharpe…" | Only an exact, re-verified replay (D13) |
| Winner's curse | Picking the luckiest of many plans | "You compared K plans…", plus a fresh-seed confirmation | No one |
| Stale rules | Trading on a rule that may have changed | New exposure blocked, daily alerts; exits open | The owner signs a re-reviewed version |
| OKX cap, acknowledgement and auto-off | Unbounded OKX exposure (USDT included), or OKX after 2026-12-03 | ACK_REQUIRED or BLOCK on buys; exits still allowed | The owner, signed; loosening waits a day |
| Signed state and code (D14) | Scripts acting as you; silent gate edits; restored old files | Unsigned changes are ignored; exit 3; "KEY CHANGED" in emails | Only your passphrase, in your verified signer |
| Language guard | Report text that sounds like advice | Nothing (the build fails) | The catalogue is reviewed |

## 11. Owner inputs and open legal points

**Owner acts.** All are signed with your own signer (D14). Claude never performs them.
1. **Set up the signer.**
   - Copy `tools/signer/sign.py` to `%USERPROFILE%\tradegen-signer\`.
   - Read it in full.
   - Write its sha256 and, later, the key fingerprint down away from the PC.
   - Generate the key with a passphrase of at least 20 characters or 5 diceware words.
2. **Sign the code hash** after reviewing each diff of the hashed files. Check the signer's hash before every passphrase
   entry.
3. **Approve** the rules table, the instrument map and the venue table, monthly.
4. **Sign the calendars** (KRX and US plans only):
   - **Files:** `holidays_KRX.yaml`, `kr_sessions.yaml`, `kr_regime_tags.yaml` (fill its `value: null` rows) and
     `holidays_NYSE.yaml`. There is no `us_sessions.yaml`.
   - **Per row:** verify it, and fill `source_url` and `signed_off_by`.
   - **Per file:** set the file-level `signed_off_by`, `signed_utc` and `md5`, using the content md5 that
     `python -m core.calendars.store` prints.
   - **Per MANIFEST row:** `version`, `md5`, `signed_off_by` and `test_ids`.
   - **Then:** sign `approved {kind: calendar, sha256}` for the set. The store's own signature is only a string, so
     the owner-log approval is what counts.
   - Claude may prepare a source-checked verification first. Until all of this is done, only crypto plans run.
5. **Set** `total_loss_floor_krw`, `daily_loss_krw` and `okx_equity_share`.
6. **Record** `age_of_majority`, and register withdrawal (address, network, tag) entries.

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

- **The table goes out of date.** Mitigations: monthly review, known-change dates, fail-closed review dates, daily
  alerts.
- **Monthly approvals become rubber-stamped.** Mitigation: `--check` lists exactly which rows and sources changed.
- **Simulated odds are read as forecasts.** Mitigations: model-not-history wording, the typical result first, spread,
  base rates, the language guard, and "the bug checks are coarser than these ranges".
- **A typed win rate tempts the owner.** Mitigations: its own column, p₀ and the unresolved share, bets needed, the
  floor-qualified ceiling.
- **A backtest edge is over-trusted.** Mitigations: exact replay only, the drift explanation, the live multiplier,
  lower-bound Kelly.
- **An agent or script acts as the owner.** Mitigations: signatures, the latest-approval rule, the signed code hash,
  the off-PC signer hash and fingerprint. The remaining limits are stated in 6.4.
- **A grey venue tightens suddenly.** Mitigations: auto-off, acknowledgement, a cap on everything held there, exits kept
  open.
- **The alerts depend on the PC being on.** Mitigations: the app-start check, the banner, the #seq and fingerprint in
  every email.

## 13. Out of scope (later specs)

- **Execution:** adapters, arming and sessions, atomic reservations, single-use permits, the audit log, writing
  `system_halt` and `system_disarm`, reading live balances and broker answers (which lifts D16 row by row), and retiring
  the read-only guards narrowly. The owner asked on 2026-10-23 about doing this early, for account inquiry only. That
  is its own small reviewed design.
- **Strategies:** multi-leg, leveraged and short plans; credit and lending stay out (D15).
- **UI:** with design-system and design-critique.
- **Compliance check:** `legal:compliance-check` per venue before real money.
- **Deferred techniques:** importance sampling, an intraday martingale path model, an OKX candle loader, special KRX
  reference regimes.

---

## Appendix A: the pre-spec review (rev 1)

Three critics shaped section 7 before rev 1: zero arithmetic drift, the structural maximum, the floor in the ceiling,
the exact optimum, noise-aware flags, simulation-precision wording, gaps and limit-down carry, the outcome partition,
lower-bound Kelly, data refusals, cost and ticket tables, calendars, no ranking, the winner's curse, survivorship.

## Appendix B: round 1 rulings (Gemini REJECT; Claude 5×2 on rev 1)

| Finding | Ruling | Now in |
|---|---|---|
| Crypto ETPs (G-1, L5) | Accepted; derived class `etp_crypto_spot` (rev 3.2) | 5.1 |
| Coverage gaps; offer-with-warning (G-2, L7) | Accepted; D10 | 5.1, 5.3 |
| Eligibility details (G-3, L2, L9) | Accepted, then superseded by D15/D16 | 5.3 |
| Hard-block KRX derivatives (L6) | Rejected (the report gates them); refused under D16 | 5.3 |
| Transfers (G-4, Z8, L3) | Accepted; network and tag added in rev 3.2 | 5.3, 6.2 |
| Dates and attributions (G-5, L4, L10) | Accepted; backtest-dates objection rejected | 5.2, 5.3 |
| Conduct tags; further-review questions (L1, L8) | Accepted | 5.3, 11 |
| Bootstrap (G-6, S1) | Accepted; now the two-point kernel | 7.2 |
| FX (G-7, S3) | Accepted (KRW series) | 7.2 |
| Ceiling and gaps (G-8) | Accepted; floor-safe sizing | 7.1, 7.4 |
| Sizing and optimum (G-9, S2, S6, S7) | Accepted; reworked | 7.1, 7.4 |
| Multi-leg (G-10) | Resolved by scope | 1 |
| Average first (G-11, S4, H-F7) | Accepted; reworked | 7.5 |
| HIDDEN_EDGE (S5) | Accepted; reworked | 7.5 |
| Seeds (S8, I5) | Accepted | 7.3 |
| Structural maximum; precision (S9, S10) | Accepted; reworked | 7.4, 7.5 |
| Repo facts (G-12 to G-17, I1 to I6) | Accepted | 4, 7.2 |
| Exits; owner log; unset limits (G-18 to G-20, Z-series) | Accepted; reworked | 6 |
| Honesty (H-F series) | Accepted | 3, 7.5, 10 |

## Appendix C: round 2 rulings (GPT REJECT on rev 2.1)

All 16 majors and 7 minors were accepted (rev 3) and are carried forward, several reworked again in rev 3.2. The main
ones:
- the two-point kernel;
- the KRX bound restricted to buy-and-hold;
- the cost ledger;
- floor-safe sizing;
- the estimated (not certified) bracket reference;
- the bounded HIDDEN_EDGE;
- D13 exact replay;
- the separate axes;
- one exit table;
- D14 signing;
- reservations;
- task A0.

GPT agreed with the L6, G-5 and G-10 rulings.

## Appendix D: round 3 (on rev 3)

- GPT ran out of quota (resets 2026-10-30 14:40).
- Gemini's run returned `status: ERROR` and reviewed text that is not in the spec. Six of its findings applied, and
  were folded into rev 3.1. The invalid run is kept as `round3_gemini_agy_INVALID.md`.

## Appendix E: round 3b rulings (on rev 3.1)

Sources:
- a Claude 5×2 workflow, every finding quoted from the spec and checked by a skeptic: dimensions martingale-math (M),
  stats (STAT), gate (G), owner-auth (F) and repo-fit (IMP);
- a grounded Gemini run (Gr), with every finding quoting the spec.

Repo claims were spot-checked by hand: the 35 bp KRX rate "incl. tax"; T-RO-01's `private_key`; the calendar file names
and the `md5` key; the S_C3 Upbit source. Gemini's `z_bound` claim was rejected: the parameter is `bound`, and
`Z_BOUND` is 22, not 6.

| Finding | Ruling | Now in |
|---|---|---|
| M1, IMP-2: the 1e-9 GARCH check cannot pass | Accepted: two named checks (1e-7 deterministic; 4·SE statistical) | 7.2 |
| M2, STAT-3, Gr-2: HIDDEN_EDGE vacuous for GARCH-t; range under-bounded | Accepted: unavailable for GARCH-t; the range formula fixed | 7.2, 7.5 |
| M3, STAT-missed-1: FLOOR unreachable under floor-safe sizing | Accepted: the AT_FLOOR outcome "keeping L to L+X" | 7.3, 7.5 |
| M4, Gr-m1: Kelly domain and shift | Accepted: f ∈ [0, 1], mean shift, f* = 0 when μ_lb ≤ 0, block 10 | 7.1 |
| M5: session range | Accepted: 16 to 22 sessions, 95× to 459×; half-open horizon; tests compute N | 3, 7.4 |
| M6: "win rate" undefined | Accepted | 7.2 |
| M7, Gr-4: bold rounding; re-entry timing | Accepted | 7.1 |
| M8: stop-based equity < 0 | Accepted: R_exit in the always rule | 7.1 |
| M-missed, STAT-6: HIDDEN_EDGE in edge columns; m undefined; untestable false-alarm test | Accepted | 7.5, 8 |
| STAT-1: the replay column hides bitcoin's drift | Accepted: new wording with the benchmark figures | 7.5 |
| STAT-2: average line contradicts itself | Accepted: agreement rule; sign-aware and book-aware wording | 7.5 |
| STAT-4: resolution undefined | Accepted | 7.5, 10 |
| STAT-5, Gr-m4: compounding "reached"; tax wording | Accepted | 7.3, 7.5 |
| STAT-7: spread with k = 0; KRX single family | Accepted | 7.5 |
| STAT-8: base-rate dates; "0.01% or less" | Accepted | 3 |
| STAT-missed-2: ceiling sentence needs the floor qualifier | Accepted | 7.4 |
| G1: a sell without holdings becomes a naked short | Accepted | 6.2 |
| G2: pair trades bypass auto-off | Accepted: counter asset, settlement assets, venue-total exposure | 5.1, 6.1, 6.2 |
| G3: spot-crypto ETPs mislabelled as `us_etp` | Accepted: derived class rule 1; map validation | 5.1 |
| G4: derived classes not encodable | Accepted: the `class` match key | 5.1, 5.2 |
| G5: D16 not machine-readable | Accepted: `requires.live`, `basis`, `policy_ref` | 5.2 |
| G6: floor versus exits | Accepted: floor split into all-intents and new-exposure parts | 5.2 |
| G7, Gr-5(2): state chosen too late | Accepted: step 0 | 6.2 |
| G8: no network or tag | Accepted | 6.1, 6.2 |
| G-missed, F5, Gr-5(1): step 6 blocks D11 withdrawals | Accepted | 6.2 |
| Gr-5(3): screen depends on odds | Accepted: `first_stake_krw` passed in | 6.3 |
| F1: restored old approvals count | Accepted: latest-approval rule | 5.2 |
| F2: the pubkey trust anchor | Accepted: off-PC fingerprint, emails, honest limit | 6.4 |
| F3: Context fields caller-supplied; venv and `.env` outside the hash | Accepted: `load_context` the only producer; limits stated | 4, 6.4 |
| F4: "highest head" undefined | Accepted: seq anchors | 6.4 |
| F6: halts cannot be logged | Accepted: unsigned tighten-only system entries | 6.4 |
| F7: exit codes collide with crashes | Accepted: exit 4, JSON summary | 5.4 |
| F8: KDF and passphrase unspecified; no technical refusal | Accepted | 6.4 |
| F-missed (major): an editable signer can capture the passphrase | Accepted: owner-kept signer outside the repo, off-PC hash check | 6.4, 11 |
| IMP-1, Gr-7: calendar signing steps wrong | Accepted: exact procedure plus a signed owner approval | 4, 11 |
| IMP-3, Gr-1: 35 bp includes tax; KONEX book | Accepted: same rate both sides, no separate tax; KONEX gate-only | 4, 7.1 |
| IMP-missed: tick floor skipped with `price=None` | Accepted: per-fill price-aware quote | 4, 7.1, 8 |
| IMP-4: the card cannot replay S_C3 | Accepted: the full replay contract | 7.2 |
| IMP-5: tree_hash scope; code-hash file set | Accepted | 4, 6.4 |
| IMP-6: delisting stress process undefined | Accepted | 7.2 |
| IMP-7: `private_key` text; yfinance bypasses hermetic | Accepted | 4, 6.4, 8 |
| IMP-8: `cryptography` not installable from requirements | Accepted | 6.4 |
| Gr-3: band inversion at low prices; lock carry; block 0 | Accepted | 7.2 |
| Gr-m2: `z_bound` | Rejected (the parameter is `bound`) | — |
| Gr-m3: FX wording | Accepted | 7.2, 7.5 |
