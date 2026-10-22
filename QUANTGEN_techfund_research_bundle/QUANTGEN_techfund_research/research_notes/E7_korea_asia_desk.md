# E7 — Korea Equities & Derivatives desk: which technical and fundamental signals pay on KRX after 35 bp per side (position paper, as of 2 Oct 2026, Asia/Seoul)

**Persona line.** E7 is a fictional composite persona, not a real person, and speaks for no real firm: "Head of Korea Equities & Derivatives at a global bank's Seoul branch, formerly head of a Korean securities firm's quant desk". E7 argues from execution and market structure: price limits, volatility interruptions (VI), short-sale bans, the sell-side transaction tax, retail-dominated turnover and a two-stock index. E7 distrusts rules imported from US data unless they survive KRX fills and costs, and checks each opinion against KRX history.

**How to read the local numbers (label "E7-QC").** E7 ran desk quick-checks on the data lab's local KRX file (`/home/claude/data_raw/marcap`). It covers all listed KRX stocks, daily, survivorship-free, 1995 to 29 Sep 2026. Scripts, CSVs and stdout are in `/home/claude/research_notes/QUANTGEN technical and fundamental signals/E7_quickchecks/`.

The construction:
- **Universe ("liquid").** KOSPI and KOSDAQ common stocks (codes ending in 0), excluding SPACs, preferred shares and names flagged as administrative issues (관리종목) or investment-caution issues (투자주의환기종목). A name must also have market cap ≥ ₩100bn, 20-day average traded value ≥ ₩1bn and price ≥ ₩1,000, and must have traded that day. That leaves about 700–800 names in 2015–19.
- **Returns.** KRX official daily change ratios. These are price-only: split-adjusted (the Samsung 50:1 split on 4 May 2018 shows as −2.08%), with **no dividends**. IPO and relisting artefacts beyond the daily limit are dropped.
- **Portfolios.** Decided at the month-end close and earned from the next session. Equal-weight quintiles. The benchmark ("EWM") is the equal-weight universe formed at the same month-end.
- **Costs.** 35 bp per side, charged as 2 × one-way turnover; 2× stress is 70 bp per side.
- **Statistics.** Annualised mean, volatility, Sharpe and iid t-statistics. Event studies use date-clustered t-statistics.

**Every E7-QC number is in-sample (IS) and descriptive. None is a run of QUANTGEN's nine-step gate.** About 20 families × 5 periods were looked at, so any |t| < 3 should be treated as noise. The data lab should re-run them under the gate (§10).

**Known limitations:**
- The liquidity screen uses same-day volume (a mild look-ahead in the eligibility filter).
- The daily equal-weight benchmark used in event studies rebalances daily. It ran about 3–8 pp below the month-formed benchmark over 5-year windows, so §6 uses the month-formed one.
- Delisting returns are only the last traded change ratio (survivorship-free, but no delisting-return correction).

---

## 1. Persona and position summary

### Takeaway
On KRX stock-level data for 2015–2026, the robust result is negative: **chasing attention loses money.** That covers locked limit-ups bought the next morning, volume spikes, +50% 20-day run-ups and lottery-like MAX stocks. QUANTGEN should use this as an exclusion screen. Of the classic factors, only four are marginally positive long-only net of 35 bp per side (2015-07 – 2024-12, against the EW universe): low-turnover momentum (+3.1%/yr), low-volatility (+1.7%), 52-week-high (+1.0%) and a long-term-reversal value proxy (+0.2%). **None is significant, and none except low-turnover momentum (about +0.2%/yr) stays positive at 2× costs.** The prior design's Korea weights for short-term reversal (3) and foreign flow (3) are not supported at QUANTGEN's costs or in the 2026 regime.

### Cited Findings
- **Limit-up chasing (상한가 따라잡기).** Buying at the next open after a locked limit-up close lost **−400 bp at 5 days and −595 bp at 20 days** relative to the equal-weight universe (n = 10,943, date-clustered t −14.3 and −11.3). It was negative in 2015–19, 2020–24 and 2025–26 (KRX, 2015-07 to 2026-08, IS, gross) — [local E7-QC part 2/3](file:///home/claude/research_notes/QUANTGEN%20technical%20and%20fundamental%20signals/E7_quickchecks/E7_part2_retail_rule_events.csv).
- **Volume-spike chasing.** Volume ≥ 5× its 20-day average with r ≥ +5% gave **−98 bp over 20 days** (t −6.7). It was negative in every sub-period — same file.
- **Short-term reversal.** One-month reversal, long-only versus EWM, made **+4.2%/yr gross but −2.7%/yr net** over 2015-07 to 2024-12. Weekly reversal had 41.7× one-way turnover and went from **+9.3% gross to −20.0%/yr net** (2015–19) — [local E7-QC part 7](file:///home/claude/research_notes/QUANTGEN%20technical%20and%20fundamental%20signals/E7_quickchecks/E7_part7_longonly_vs_monthformed_EW.csv); [part 1 stdout](file:///home/claude/research_notes/QUANTGEN%20technical%20and%20fundamental%20signals/E7_quickchecks/e7_checks_part1_stdout.txt).
- **Foreign flow in 2026.** Foreigners net-sold **₩148.3tn in H1 2026** while KOSPI nearly doubled — [KEIA](https://keia.org/analysis/explaining-south-koreas-stock-market-boom/).
- **Concentration.** Samsung and SK hynix were **55.7% of KOSPI market cap on 22 Jun 2026** (local; KEIA gives 55.5%) and **42.8% of KOSPI traded value in 2026 YTD**. Meanwhile **66.2% of KOSPI common stocks fell** between 30 Dec 2025 and 22 Jun 2026 while the cap-weighted index rose 117% — [local E7-QC part 3/5](file:///home/claude/research_notes/QUANTGEN%20technical%20and%20fundamental%20signals/E7_quickchecks/e7_checks_part3_stdout.txt).

### Inferences (position summary)
1. Korea is not a "reversal market" at 70 bp a round trip. The gross reversal premium is real and documented: in Sim & Kim's 1999–2021 sample the one-month reversal strategy earned a five-factor alpha of 1.275% a month. But on 2015–2026 data it is smaller than the cost of trading it. It decayed after 2019 and inverted in the 2025–26 melt-up.
2. What pays in Korea is mostly **not owning what retail is chasing**. The tradeable form is a negative screen on any long book, not a long-short factor, because the short leg is unimplementable for most of the sample.
3. Most Korean anomaly long-short spreads sit in the unshortable short leg. Low-vol long-short earned +16–21%/yr gross, but long-only versus EW earned +3.7–5.0% (2015–19 and 2020–24). US-style long-short factor cards will therefore massively overstate what a long-only Korean investor can capture.
4. ±30% limits make close-to-close backtests lie around limit events. The apparent +3.3% next-day return after a locked limit-up cannot be filled. Locked limit-downs continue to fall (−6.6% the next day), so reversal books must exclude them and exits can be trapped.
5. The 2026 index is a leveraged two-stock memory-chip book. Any equal-weight or factor book is mechanically a bet against Samsung and SK hynix. QUANTGEN must report every Korea card against EW, cap-weighted (CW) and CW-ex-pair benchmarks, or verdicts will be benchmark artefacts.
6. Momentum in Korea is a low-turnover phenomenon (consistent with Eom et al. 2020). Its July 2026 crash came after a bull market, so a Daniel–Moskowitz bear gate would not have fired. Only own-volatility scaling plus concentration caps could have helped. This is untested.
7. Value-up "outperformance" is mostly chip exposure: SK hynix plus Samsung are 38.5% of the main tracker. It is not evidence for a low-P/B value factor. Value needs a proper point-in-time OpenDART test with a 2024 structural-break split.
8. **What QUANTGEN should test first** (detail in §9):
   1. the attention-fade exclusion screen;
   2. low-vol / low-MAX as a protective card;
   3. low-turnover, vol-scaled 12-1 momentum, long-only;
   4. a t−1 KIS investor-flow card with a pre/post-May-2026 split;
   5. OpenDART value, quality and shareholder-yield.

   Drop daily and weekly reversal, golden/dead crosses, 정배열 (moving-average alignment) entries, limit-up chasing and size tilts.

### Gaps
- The web-search quota for this session (200 calls) ran out mid-research. KRX's data portal (data.krx.co.kr) also refused proxied access with a 403. Official KRX statistics were therefore partly unavailable, notably individual investors' annual share of traded value for 2015–2026 and factor-ETF NAV histories (§2 and §5 gaps).

---

## 2. Market structure and rules that break US-derived strategies

### Takeaway
Six rule sets matter for a daily close-to-close stock card:
- **±30% price limits** (since 15 Jun 2015), with locked limit closes that cannot be filled;
- **VI and opening single-price auctions**;
- **repeated short-sale bans**, including a partial-ban regime from May 2021 to Nov 2023 in which only KOSPI200/KOSDAQ150 names could be shorted;
- **a sell-side transaction tax** that changed every year from 2023 to 2026 and is 0.20% in 2026;
- **NXT extended hours**, 08:00–20:00 since 2025;
- **a market where retail turnover and two mega-caps dominate**.

### Cited Findings
**Price limits**
- Local KRX data show the daily limit switching on **15 Jun 2015**. The largest daily moves were exactly ±15.00% through 12 Jun 2015 and 29.93–30.00% from 15 Jun. 22 stocks moved more than 15.5% on the first day, and 132 such prints over 2013 to mid-June 2015 are IPO or relisting days — [local E7-QC part 5](file:///home/claude/research_notes/QUANTGEN%20technical%20and%20fundamental%20signals/E7_quickchecks/e7_checks_part5_stdout.txt); [part 3](file:///home/claude/research_notes/QUANTGEN%20technical%20and%20fundamental%20signals/E7_quickchecks/e7_checks_part3_stdout.txt).
- *Correction:* the 132 earlier prints are presumably IPO, relisting or base-price-reset days, but they were not checked one by one.
- **Locked limit-up closes** (≥ 29.5% and close = high, all common stocks) numbered 774 (2015, from 15 Jun), 848, 609, 866, 790, **1,579 (2020)**, 1,037, 872, 1,204, 1,172, 1,332 and **1,994 (2026 to 29 Sep)**. Locked limit-downs rose from 56 (2015) to **196 (2026)** — [local part 3](file:///home/claude/research_notes/QUANTGEN%20technical%20and%20fundamental%20signals/E7_quickchecks/e7_checks_part3_stdout.txt).

**Volatility interruptions**
- 42% of KOSPI VIs fell between 9 and 10 a.m. Of those, **80.9% came within 30 minutes of the open** and 53.2% within 10 minutes. Static VIs were 68.8% of 9–10 a.m. triggers. A VI moves the stock into a single-price auction for about two minutes. Totals were 7,239 against 4,470 a year earlier (+61.9%) — [Seoul Economic Daily](https://en.sedaily.com/finance/2026/05/07/kospi-volatility-interruptions-double-in-early-trading-hours).
- *Conflict:* the article is dated 7 May 2026 but its text says the period ran to "Nov. 6", so the exact window is ambiguous.

**Circuit breakers**
- The record −12.06% day on 4 Mar 2026 triggered a 20-minute halt, the seventh KOSPI circuit breaker ever — [Korea Herald](https://www.koreaherald.com/article/10686893).
- KEIA counted six market-wide circuit breakers in 2026 (to 22 Jul) against six in total before 2026 — [KEIA](https://keia.org/analysis/explaining-south-koreas-stock-market-boom/). An earlier fetch of the same page read "7", so the count is uncertain.
- July 2026 alone had **4 circuit breakers and 15 sidecars** — [Sedaily](https://en.sedaily.com/finance/2026/07/31/kospi-whipsaws-18-percent-plunge-over-three-days-then-18).

**Short-selling bans** ([KCMI, Hwang Seiwoon, 1 Apr 2025](https://www.kcmi.re.kr/en/publications/pub_detail_view?syear=2025&zcd=002001017&zno=1840&cno=6517); [PDF](https://www.kcmi.re.kr/common/downloadw?fid=27533&amp=&fgu=002001&amp=&fty=004003))
- Four complete bans:
  - **1 Oct 2008 – 31 May 2009** (about 8 months);
  - **11 Aug – 9 Nov 2011**;
  - **16 Mar 2020**, partially lifted **3 May 2021** for KOSPI200/KOSDAQ150 only;
  - **5 Nov 2023 – 31 Mar 2025** (about 17 months, the longest).
- Rules from 31 Mar 2025:
  - a mandatory naked short-selling detection system (NSDS);
  - stock-loan repayment capped at 90 days, and at 12 months including extensions;
  - collateral of 105% for both retail and institutions.
- *Correction to the brief:* the 2008 ban began **1 Oct 2008**, not November.
- During the ban, in 2024, KOSPI fell **10.1%** (2,669.81 → 2,399.49) and KOSDAQ **22.8%** — same KCMI paper.
- Resumption on 31 Mar 2025 covered **all listed stocks**, the first time since March 2020. The partial 2021 resumption covered about 350 names. Foreigners held **64.8% of securities lending** in late Feb 2025, with ₩66.64tn of loans outstanding. On the same day NXT doubled its tradable list to 800 — [KED Global](https://www.kedglobal.com/short-selling/newsView/ked202503300002).
- Foreigners sold ₩27.7tn from Sep 2024 to the resumption, described as the third-longest foreign selling streak since 2008 — [Investment Monitor](https://www.investmentmonitor.ai/news/end-of-korean-short-selling-ban-expected-to-attract-foreign-investors/) (T3).

**Securities transaction tax** (all-in, charged on sales)

| Market | 2023 | 2024 | 2025 | 2026 (enacted / proposed) | KONEX |
|---|---|---|---|---|---|
| KOSPI | 0.20% | 0.18% | 0.15% | 0.20% | — |
| KOSDAQ / K-OTC | 0.20% | 0.18% | 0.15% | 0.20% | — |
| KONEX | — | — | — | — | 0.10% |

Sources: [KPMG Korea tax brief, Aug 2025](https://assets.kpmg.com/content/dam/kpmgsites/kr/pdf/2025/tkc/tax-brief/korea-tax-brief-202508-eng_F.pdf.coredownload.inline.pdf) for the 2023–25 schedule and the proposal; [PwC](https://taxsummaries.pwc.com/republic-of-korea/corporate/other-taxes) for KOSPI 2026+ at 0.20%, including the rural special tax. PwC's page as fetched gave no KOSDAQ 2026 rate; EY (below) gives it.

- [EY](https://taxnews.ey.com/news/2026-0126-korea-enacts-2026-tax-reform-bill): the reform bill was **enacted 23 Dec 2025**, effective **1 Jan 2026**. KOSDAQ goes from 0.15% to 0.20%. On KOSPI an agricultural and fishery special tax of **0.15%** applies on top of the securities transaction tax.
- *Inference:* this implies a 0.05% KOSPI securities transaction tax plus the 0.15% special tax, 0.20% all-in. EY's summary as fetched was garbled ("0% to 0.20%").

**NXT (Nextrade)**
- Sessions are pre-market **08:00–08:50**, main **09:00:30–15:20** and after-market **15:40–20:00**. About 590–601 stocks trade in its sessions, at fees below KRX's — [Nextrade](https://nextrade.co.kr/).
- KED Global reported that NXT expanded to 800 stocks on 31 Mar 2025 ([KED](https://www.kedglobal.com/short-selling/newsView/ked202503300002)). Why the site now shows about 600 was not verified.
- The companion macro spec already excludes NXT and KRX after-hours prints from signals and uses the KRX 15:30 close (project doc `QUANTGEN_MACRO_INTEGRATION.md` §4.1).

**Turnover structure (local, KOSPI vs KOSDAQ, all listed common and preferred)**
- KOSPI average daily traded value: ₩5.35tn (2015), ₩4.99tn (2019), **₩12.20tn (2020)**, ₩15.42tn (2021), ₩10.74tn (2024), ₩12.40tn (2025), **₩33.68tn (2026 YTD)**.
- KOSDAQ: ₩3.52tn (2015), ₩10.82tn (2020), ₩7.55tn (2025), ₩11.19tn (2026).
- Annual turnover velocity: KOSPI 82–122%, except **201% (2020)** and 173% (2021); KOSDAQ 360–708%, except **945% (2020)**. The 2026 figures (KOSPI 114%, KOSDAQ 368%) are year-to-date, over 181 sessions, and not annualised.
- The bottom half of names by market cap captured only **1.6% (KOSPI) and 5.1% (KOSDAQ)** of traded value in 2026 — [local E7-QC part 5](file:///home/claude/research_notes/QUANTGEN%20technical%20and%20fundamental%20signals/E7_quickchecks/E7_part5_turnover_by_market_year.csv).

**Retail share of trading (long run)**
- KCMI found individuals' share of traded value fell from **76% (1999) to 47% (2013)**. Foreigners rose from 5% to 29% and domestic institutions from 16% to 23%. Individuals' turnover fell from 928% (2002) to 196% (2013) — [Seoul Shinmun, 26 May 2015, reporting KCMI](https://www.seoul.co.kr/news/economy/securities/2015/05/26/20150526800049) (T2 reporting T1).

**Single-stock leveraged ETFs and leverage, 2026**
- KRX introduced single-stock leveraged ETFs on Samsung and SK hynix in **May 2026** — [KEIA](https://keia.org/analysis/explaining-south-koreas-stock-market-boom/).
- 16 funds launched, with ₩10.41tn of first-day trading and ₩2.05tn of net purchases. Margin loans were **₩36.25tn on 26 May 2026 (+33% y/y)** and VKOSPI was 70.83 — [Sedaily, 27 May 2026](https://en.sedaily.com/finance/2026/05/27/samsung-sk-hynix-surge-alone-as-chip-duo-tops-half-of-kospi).
- ETF daily turnover went from ₩6.6tn (Dec 2025) to ₩34tn (Jun 2026). ETFs are about 30% of stock-market trading volume — KEIA.

### Inferences
- **Limits break close-based fills.** A backtest that buys at the close of a locked limit-up day, or sells at a locked limit-down close, assumes liquidity that does not exist. QUANTGEN's "decide at close t, earn from t+1" rule needs a **limit-state fill rule**:
  - no entry at a locked limit-up close, with the entry moved to the t+1 open price;
  - an exit at a locked limit-down close is carried to the next session with an unlocked print, at 2× cost.
- **The partial short ban** (3 May 2021 – 5 Nov 2023), when only KOSPI200/KOSDAQ150 names could be shorted, is a natural experiment for overpricing (§10 DC3). The full-ban regimes mean any long-short card is unimplementable for about **2.5 of the 11 years since 2015** (16 Mar 2020 – 2 May 2021, about 1.1 years; 6 Nov 2023 – 28 Mar 2025, about 1.4 years). For non-index names the figure is about **5 years**, once the partial regime is added. The short leg is also impractical for retail outside index names.
- **The tax path is not monotonic.** It is 0.20% (2023), 0.18% (2024), 0.15% (2025) and 0.20% (2026). QUANTGEN's flat 35 bp per side is conservative for 2024–25 and roughly right for 2026. Pre-2023 rates were higher; they are unverified here, see Gaps. The tax is sell-only, so strategies with many exits pay most of it.
- **The open is the worst-priced moment on KRX.** VIs cluster there, NXT pre-market prints arrive from 08:00, and the opening auction absorbs overnight US moves. Rules that enter at the open, such as "buy the gap", should be priced at the auction with a VI flag.
- **Desk view (opinion, unverified):** all-in costs for KOSPI200 names at retail size are probably 15–25 bp per side: commission, a half-tick spread, impact, and on average half of the sell tax. 35 bp is conservative there. For KOSDAQ names near ₩1bn ADV in stress weeks, 35 bp may be light. This needs KIS quote snapshots; an OHLC spread proxy failed (§6).

### Gaps
- **Individuals' share of KOSPI/KOSDAQ traded value by year, 2015–2026.** Not retrieved: KRX portal 403 and search quota exhausted. Data request: KIS investor-type flows, or the KRX "투자자별 거래실적" screen.
- **KOSPI200 weekly options** (launch dates, expiry days) — not verified in any fetched source.
- **Investor-type flow disclosure timing** (intraday preliminary vs final after the close). Only the project spec's statement was available; no KRX page was fetched.
- **Pre-2023 securities transaction tax schedule** — not verified in fetched sources.
- **NXT launch date** — the brief says March 2025; no fetched page gives the exact day.
- **VI article period** is ambiguous (see above).

---

## 3. Retail technical practice and theme stocks: profitability on KRX

### Takeaway
The popular Korean retail rules do not survive 70 bp a round trip; most do not survive even gross. This covers 정배열 (moving-average alignment), golden and dead crosses, volume spikes, 상한가 따라잡기 and theme spikes. KCMI's account-level studies show retail turnover and lottery preference destroying returns. On the evidence, the "edge" in Korean retail TA is being on the other side of it.

### Cited Findings
**E7-QC event studies** (liquid universe; KRX 2015-07 to 2026-08; excess return versus the EW universe; IS; gross unless stated; net = gross − 70 bp round trip) — [E7_part2_retail_rule_events.csv](file:///home/claude/research_notes/QUANTGEN%20technical%20and%20fundamental%20signals/E7_quickchecks/E7_part2_retail_rule_events.csv)

| Rule | n events | t+1 | t+5 | t+20 | Date-clustered t (t+5 / t+20) | Net of 70 bp (t+20) |
|---|---|---|---|---|---|---|
| Golden cross MA5 > MA20 | 71,477 | +4.0 bp | +3.8 | +4.9 | −1.61 / −1.46 | −65 bp |
| Dead cross MA5 < MA20 | 77,123 | 0.0 | +3.6 | −8.0 | 0.04 / −2.82 | −78 |
| Golden cross MA20 > MA60 | 24,732 | −1.9 | −1.7 | −2.8 | −2.35 / −1.00 | −73 |
| 정배열 onset (MA5 > 20 > 60 > 120) | 34,164 | +2.9 | +6.3 | +17.4 | −0.03 / −0.58 | −53 |
| Volume ≥ 5× 20d avg and r ≥ +5% | 35,823 | +2.1 | **−46.7** | **−98.4** | **−5.21 / −6.66** | −168 |
| Locked limit-up, buy at close t (not fillable) | 11,102 | +331.9 | +239.9 | +24.9 | 8.32 / 1.97 | (illusory) |
| Locked limit-up, buy at t+1 open | 10,943 | — | **−400.3** | **−595.4** | **−14.34 / −11.31** | −665 |
| Locked limit-down close | 755 | **−662.7** | −772.8 | −1,094 | −9.13 / −9.73 | — |
| 20d return ≥ +50% ("theme blow-off") | 61,072 | −1.2 | −11.1 | **−73.3** (median −738) | −1.68 / −5.55 | −143 |
| 20d return ≤ −30% | 33,028 | +15.2 | +34.4 | +78.2 (median −120) | −3.45 / −4.91 | +8 |

Further results:
- **Limit-up next-open gap:** mean **+5.02%**, median +5.43%; 24.9% of gaps were ≥ +10% and 20.9% were negative. Buy-at-open hit rates were 30.6% (t+5) and 27.6% (t+20).
- **By sub-period** (next-open entry, t+5 / t+20): 2015–19 −305 / −425 bp; 2020–24 −431 / −574 bp; **2025–26 −462 / −868 bp**. Volume spikes at t+20: −96, −82 and **−160 bp** — same file.
- **Trend-state portfolios** (monthly, long-only versus the EW universe) — [E7_part6_trend_state_ports.csv](file:///home/claude/research_notes/QUANTGEN%20technical%20and%20fundamental%20signals/E7_quickchecks/E7_part6_trend_state_ports.csv):
  - holding all 정배열-aligned names: **−5.3%/yr gross, −10.9% net** (2015-07–2019-12); +0.5% / −5.1% (2020–24); +16.0% / +10.6% in the melt-up (2 Jan 2025 – 22 Jun 2026); then **−48.7% against the universe's −27.1%** in the 23 Jun–30 Jul 2026 crash. Turnover 7.9×/yr.
  - price above MA200: −2.8%/yr gross (2015–19), −1.0% (2020–24), +6.8% (melt-up), −34.6% in the crash.

**KCMI account-level evidence on retail investors**
- **COVID cohort** (Kim Min-gi & Kim Jun-seok, Issue Report 21-11, 14 Jun 2021; 204,004 investors at four brokers, Mar–Oct 2020) — [KCMI](https://www.kcmi.re.kr/report/report_view?report_no=1243):
  - portfolio return 18.4% gross / 14.4% net;
  - **new investors 5.9% gross / −1.2% net, and 60% of them lost money**;
  - daily turnover **6.8% against 1.4%** for the market; accounts ≤ ₩10m turned over 29.7% a day (a 3.4-day holding period);
  - day trading was 55.4% of volume;
  - one-year annualised returns ranged from −13.3% (≤ ₩10m accounts) to +20.0% (> ₩100m).
- **Behavioural biases** (Research Report 22-02, 3 Feb 2022) — [KCMI](https://www.kcmi.re.kr/report/report_view?report_no=1481):
  - annual turnover about 1,600% in 2020;
  - average holding period 9.67 days (median 3);
  - disposition-effect hazard ratio **2.18**: at a one-day holding period, 41% sold winners against 22% losers.
- **KCMI webinar, 13 Apr 2021** — [Financial News](https://www.fnnews.com/news/202104131912345956):
  - 46% of individuals lost money (39% of existing, 62% of new investors);
  - higher turnover, a higher intraday share and more stock switching went with lower daily excess returns;
  - excess trading in **lottery-type stocks** was 32.7% for the top-two lottery-preference groups and 39.3% for men under 30;
  - 63% of completed sales were gains, while 63% of positions still held were losses.
  - Corroborated by [Seoul Shinmun](https://www.seoul.co.kr/news/economy/2021/04/13/20210413500168): average holding 8.2 days, daily turnover 12.2%, 55% same-day round trips among new investors.
- **Overseas investing** (Kang So-hyun & Kim Min-gi, Research Report 26-04, 9 Feb 2026; about 102,380 investors, 2020–22) — [KCMI](https://www.kcmi.re.kr/report/report_view?report_no=2254). Leveraged and inverse ETPs drove the growth in overseas holdings, especially among young, small accounts. The effective number of holdings was tiny, and returns lagged benchmarks after costs.
- **Older evidence.** In 1996–98, domestic individuals' large trades carried short-lived information relative to foreigners' — [Choe, Kho & Stulz, NBER w8073](https://www.nber.org/papers/w8073). This is an old sample and predates retail-app trading.

### Inferences
- **Golden crosses, dead crosses and 정배열** carry ≤ 17 bp of mean excess over 1–20 days, with date-clustered t-statistics around zero or negative, against a 70 bp round trip. They are noise at retail-relevant horizons. The 정배열 *state* is just a lagged momentum or beta bet. It looked brilliant in the melt-up and lost 49% in five weeks.
- **Volume spikes, locked limit-ups and +50% run-ups** are the retail "theme" footprint, and they **mean-revert hard over 5–20 days**. The reversal was larger in 2025–26 than before. The skew is extreme: the median 20-day excess after a +50% run-up is −7.4% while the mean is −0.7%. That is a lottery payoff, consistent with KCMI's finding that retail overweights lottery-type stocks.
- **Limit-downs are not a reversal opportunity.** They continue (−6.6% the next day), plausibly because of delayed price discovery and bad-news designations.
- **For QUANTGEN this is the cleanest Korea-specific signal,** but it works as an *exclusion screen* on long books. Shorting the flagged names is not possible for retail in non-index names, and was banned outright in 2020–21 and 2023–25.

### Gaps
- No academic or FSS study of **theme stocks (테마주)** specifically, for example political theme stocks before elections, was retrieved (search quota exhausted). The local blow-off and limit-up events are proxies, not a theme taxonomy.
- No post-2022 KCMI or FSS update on aggregate retail performance was retrieved for the 2025–26 boom.

---

## 4. Investor flows (수급) as predictors

### Takeaway
The best evidence says Korean foreign flows are **positive-feedback**: foreigners buy after up days in Korea and in the US. Their **price impact is contemporaneous and permanent**, with no reversal, and is complete within about 10 days. That supports flows as a same-day *explanation*, not a next-day *signal*. In 2026 the aggregate sign broke outright: foreigners sold ₩148tn into a +101% half-year and bought on the worst day in history. QUANTGEN should log t−1 final flows and test them, not weight them at 3.

### Cited Findings
- **Richards, RBA RDP 2004-05** (KSE and Kosdaq, daily, Jan 1999–Sep 2002) — [abstract](https://www.rba.gov.au/publications/rdp/2004/2004-05.html); [PDF](https://www.rba.gov.au/publications/rdp/2004/pdf/rdp2004-05.pdf):
  - daily foreign net purchases have a first-order autocorrelation of **0.43 (KSE) and 0.35 (Kosdaq)**, and same-day correlations with returns of 0.39 and 0.16;
  - they respond to overnight US returns with t > 5, and Kosdaq responds to the SOX;
  - the contemporaneous price-impact coefficient is **0.119 (t 11.9)** on the KSE, roughly a 12% price rise per 1% of market cap of inflow;
  - impacts are **largely permanent**, more than half contemporaneous, complete within about 10 days, with no reversal.
- **Choe, Kho & Stulz** (JFE 1999; Korea, 30 Nov 1996 – end 1997) — [NBER w6661](https://www.nber.org/papers/w6661). Foreigners showed positive-feedback trading and herding before the crisis, and both weakened during it. There was **no evidence foreign trades destabilised the market**: prices adjusted quickly to large foreign sales, with no subsequent negative abnormal returns.
- **Choe, Kho & Stulz** (Dec 1996 – Nov 1998) — [NBER w8073](https://www.nber.org/papers/w8073). Foreigners traded at worse prices than residents, especially for large trades, small stocks and sales.
- **2026 aggregates:**
  - foreigners net-sold **₩148.3tn (US$96.7bn) in H1 2026**, while KOSPI nearly doubled — [KEIA, 22 Jul 2026](https://keia.org/analysis/explaining-south-koreas-stock-market-boom/);
  - on the record close of **9,114.55 on 22 Jun 2026**: foreigners −₩2.55tn, retail +₩2.15tn, institutions +₩308.4bn — [Korea JoongAng Daily](https://www.koreajoongangdaily.com/business/kospi-hits-fresh-record-over-9100-as-chip-stocks-rally/12734799);
  - on **23 Jun 2026 (−9.99%)**: retail +₩8.54tn, foreigners −₩4.14tn, institutions −₩4.53tn; pension funds sold ₩2.318tn over the month; 46 stocks rose and 859 fell — [Sedaily](https://en.sedaily.com/markets/2026/06/23/kospi-plunges-10-percent-on-chip-concentration-leverage);
  - on the **record −12.06% day (4 Mar 2026)**, foreigners were net **buyers** of ₩231.2bn, retail bought ₩79.7bn and institutions sold ₩588.8bn — [Korea Herald](https://www.koreaherald.com/article/10686893).
- **Companion macro research** (project doc `QUANTGEN_MACRO_BACKLOG.md`, BL-C06). Foreigners sold ₩21.5tn in Sep 2026 while USD/KRW fell 12.4% over Q3. The question of whether flows remain informative is open, with a pre/post-May-2026 split proposed.

### Inferences
- If impact is contemporaneous and permanent, a flow signal observed after the close can only pay through **persistence** (autocorrelation 0.35–0.43 in 1999–2002), not through reversal. Whether that persistence earns more than 70 bp per stock-level round trip is untested.
- In 2026 the marginal price-setter was domestic leverage: retail, single-stock leveraged ETFs and margin. Aggregate foreign selling was partly hedging or profit-taking into a two-stock index. Foreign net buying as a market-direction signal fails that year by construction. At stock level it may still carry information in non-chip names, which is testable once flows are logged.
- **Program trading and NPS flows:** no usable evidence beyond the June 2026 pension-fund figure. Keep them as context.

### Gaps
- **Stock-level** foreign and institutional flow predictability in 2015–2026, net of costs, is not available locally (no flow data in marcap). Data request DC9.
- **Hong & Lee (1998–2010)** (foreign and institutional investors informed) is cited in the companion research but was not re-opened here.
- **Program-trading (차익/비차익) statistics and NPS daily flows** were not retrieved.

---

## 5. Fundamentals: the Korea discount, Value-up, governance and tax reforms, factor-ETF analogues

### Takeaway
2024–26 brought the biggest governance shift in Korean market history:
- the Value-up programme (Feb 2024);
- the Value-up index (30 Sep 2024);
- Commercial Act amendments (Jul and Aug 2025);
- dividend separate taxation from FY2026.

But the measurable "Value-up outperformance" is largely memory-chip exposure. Over 2015-07 to 2024-12, factor quintiles inside a KOSPI200 proxy all lost to the cap-weighted index, mostly by underweighting Samsung and SK hynix. Value as low P/B is **untested** on KRX in this desk's work: there are no book values locally.

### Cited Findings
**Programme and index design**
- FSC announced the Corporate Value-up Programme in **Feb 2024**. KRX finalised guidelines on **27 May 2024**, covering disclosure of PBR, PER, ROE and payout plus three-year plans. The Korea Value-up Index launched in **Sep 2024** with 100 names (67 KOSPI, 33 KOSDAQ). Its screens: top-400 market cap, no losses over two years, consistent dividends or buybacks, **top 50% by P/B**, and high ROE. Treasury-stock cancellations rose 33% from 2022 to 2023 — [Glass Lewis, 30 Sep 2024](https://www.glasslewis.com/article/navigating-south-koreas-corporate-value-up-program).

**Value-up performance**
- The index stood at 2,330.7 at **end-Jan 2026**, **+134.9% since launch (30 Sep 2024) against KOSPI +101.5%** — [Korea Times, citing KRX](https://www.koreatimes.co.kr/economy/20260204/koreas-value-up-index-sets-new-record-last-month-krx). 13 tracking ETFs held ₩1.7tn.
- KEIA reports Value-up Index shareholder return outperforming the **KOSPI 200 by 17%** since launch; the end date is unspecified, in an article dated 22 Jul 2026 — [KEIA](https://keia.org/analysis/explaining-south-koreas-stock-market-boom/).
- **RISE Korea Value-Up ETF (495050)**, listed 4 Nov 2024, as of **2 Oct 2026** — [RISE ETF](https://eng.riseetf.co.kr/prod/finderDetail/44H7):
  - **+248.94% since inception**, 1Y +136.36%, 6M +34.56%, **3M −15.88%**;
  - top holdings **SK hynix 20.92%, Samsung Electronics 17.53%**, SK Square 8.79%;
  - IT is **50.78%** of the fund;
  - TER 0.008%, AUM ₩960bn.

**Governance and tax reforms**
- Commercial Act — [KEIA](https://keia.org/analysis/explaining-south-koreas-stock-market-boom/):
  - **Jul 2025:** shareholders added to directors' duty of loyalty; "outside" directors renamed "independent", with the required share rising from one-quarter to one-third in Jul 2026;
  - **Aug 2025:** cumulative-voting opt-outs prohibited; separately elected audit-committee members raised from one to two.
- **Dividend tax (as proposed, Aug 2025)** — [KPMG](https://assets.kpmg.com/content/dam/kpmgsites/kr/pdf/2025/tkc/tax-brief/korea-tax-brief-202508-eng_F.pdf.coredownload.inline.pdf):
  - separate taxation at **14% (≤ ₩20m), 20% (₩20m–300m) and 35% (> ₩300m)**;
  - for companies with no dividend cut and either a payout ≥ 40%, or a payout ≥ 25% with a ≥ 5% dividend increase;
  - for fiscal years from 1 Jan 2026 through FY2028.
  - KPMG also lists a proposed cut in the large-shareholder capital-gains threshold from ₩5bn to ₩1bn. *Final enacted terms not verified* (Gaps).

**Valuation**
- Goldman Sachs (21 May 2026) put KOSPI on a forward P/E of about 7×, forecast 2026 earnings growth of **300%**, raised its target to 9,000, and expected Value-up to narrow the discount gradually — [Goldman Sachs](https://www.goldmansachs.com/insights/articles/koreas-stock-market-is-forecast-to-set-fresh-highs).

**E7-QC factor-ETF analogues** (KOSPI200 proxy = top 200 KOSPI common stocks by cap; top quintile; monthly; equal-weight; price-only; net of 35 bp per side) — [E7_part2_k200proxy_factor_years.csv](file:///home/claude/research_notes/QUANTGEN%20technical%20and%20fundamental%20signals/E7_quickchecks/E7_part2_k200proxy_factor_years.csv):

| Period | K200 proxy CW | CW ex-Samsung/SK hynix | EW200 | Low-vol Q5 (net) | 12-1 momentum Q5 (net) | 1m reversal Q5 (net) |
|---|---|---|---|---|---|---|
| 2015-07 – 2024-12 (cum.) | **+17.7%** | **−7.5%** | +1.5% | −14.1% | −15.3% | −51.2% |
| 2 Jan 2025 – 22 Jun 2026 | +302.4% | +120.1% | +103.9% | +52.9% | +178.8% | +62.9% |
| 23 Jun – 30 Jul 2026 | −39.3% | −26.7% | −18.7% | **+3.2%** | −44.4% | −30.1% |

**E7-QC value proxy** (long-term reversal: 36-to-12-month losers, the DeBondt–Thaler/Fama–French proxy for value without book data; liquid universe; long-only versus EWM) — [E7_part8_value_proxy_and_market_split.csv](file:///home/claude/research_notes/QUANTGEN%20technical%20and%20fundamental%20signals/E7_quickchecks/E7_part8_value_proxy_and_market_split.csv):
- 2015-07 – 2024-12: **+2.9%/yr gross (t 1.48), +0.2% net**; long-short +7.4% gross (t 2.07);
- melt-up: −9.8%/yr gross;
- crash: −32.4% against −25.4%.

### Inferences
- **Value-up is not a value index.** Its screen selects the *upper* half by P/B together with profitability and shareholder returns, and its tracker is 38.5% SK hynix + Samsung. Its +134.9% against KOSPI's +101.5% (to Jan 2026) and its −15.9% over three months to 2 Oct 2026 are chip-cycle beta. They do not show the Korea discount closing for cheap stocks.
- **The governance reforms are a structural break** (2024–26) for value, dividend and shareholder-yield signals. Any value card should be estimated pre- and post-Feb-2024 and should not pool regimes.
- **"Smart beta" in Korea lost to the cap-weighted index over 2015–2024** because the index is Samsung (with SK hynix growing). Excluding the pair, Korean large caps lost 7.5% in price over 9.5 years. These quintiles are price-only, so they understate high-dividend and low-vol books by their yield gap. A benchmark choice of KOSPI200 CW versus EW or ex-pair will decide most Korea factor verdicts.

### Gaps
- **Actual factor-ETF histories** (KODEX, TIGER, KBSTAR/RISE value, momentum, low-vol, quality and dividend ETFs) against KOSPI200 for 2015–2026 were **not retrieved**. The marcap file contains no ETFs (KODEX 200, 069500, is absent). KIS ETF history is needed.
- **P/B, E/P, quality (GP/A, ROE), accruals, dividend and buyback-cancellation yield**: not testable locally, because there are no fundamentals. Needs point-in-time OpenDART data.
- **Treasury-share cancellation mandate** (proposed third Commercial Act amendment) and the **final** dividend-tax and large-shareholder thresholds enacted in Dec 2025 were not verified.
- **Chaebol holding-company discount** studies were not retrieved.

---

## 6. Cross-sectional factors on KRX, 2015–2026, net of 35 bp per side (the core evidence)

### Takeaway
Net of QUANTGEN's KRX stock cost, long-only versus the EW universe over 2015-07 to 2024-12, **no family is significant**:

| Family | Gross | Net of 35 bp |
|---|---|---|
| 12-1 momentum, low-turnover tercile | +6.0% | **+3.1%/yr** |
| Low-vol | +4.3% | **+1.7%** |
| 52-week high | +5.1% | **+1.0%** |
| Value proxy (LTR) | +2.9% | **+0.2%** |
| 1-month reversal | +4.2% | −2.7% |
| Low-MAX | +2.5% | −2.9% |
| All-name 12-1 momentum | −2.0% | −4.4% |

At 2× costs (70 bp per side) every family except low-turnover momentum (about +0.2%/yr) is negative. The big Korean long-short premia are short-leg overpricing that a long-only or ban-constrained investor cannot harvest.

### Cited Findings
**E7-QC long-only versus EWM** (liquid universe; monthly quintiles; annualised mean %, volatility %, Sharpe, t; IS) — [E7_part7_longonly_vs_monthformed_EW.csv](file:///home/claude/research_notes/QUANTGEN%20technical%20and%20fundamental%20signals/E7_quickchecks/E7_part7_longonly_vs_monthformed_EW.csv); [E7_part8](file:///home/claude/research_notes/QUANTGEN%20technical%20and%20fundamental%20signals/E7_quickchecks/E7_part8_value_proxy_and_market_split.csv)

| Family (long leg) | One-way turnover/yr | 2015-07–2024-12 gross | Net 35 bp | Implied net 70 bp | 2015–19 gross | 2020–24 gross | Years positive, net (2015–25) |
|---|---|---|---|---|---|---|---|
| 12-1 momentum, all | 3.4 | −2.0 (t −0.65) | −4.4 (t −1.40) | ≈ −6.8 | −3.2 | −1.0 | 45% |
| 12-1 momentum, low-turnover tercile | 4.1 | **+6.0 (t 1.55)** | **+3.1 (t 0.80)** | ≈ +0.2 | +2.3 | **+9.3 (t 1.67)** | 45% |
| 12-1 momentum, high-turnover tercile | 3.6 | **−8.4 (t −1.55)** | −10.9 (t −2.00) | ≈ −13.4 | −8.8 | −8.0 | 27% |
| 1-month reversal | 10.0 | +4.2 (t 1.53) | −2.7 (t −0.96) | ≈ −9.6 | +7.5 (t 1.86) | +1.3 | 27% |
| 60d low-vol | 3.8 | +4.3 (t 1.24) | +1.7 (t 0.50) | ≈ −0.9 | +5.0 | +3.7 | 45% |
| Low MAX (21d max return) | 7.8 | +2.5 (t 1.00) | −2.9 (t −1.10) | ≈ −8.3 | +5.1 | +0.2 | 36% |
| 52-week-high proximity | 6.1 | +5.1 (t 1.63) | +1.0 (t 0.33) | ≈ −3.1 | +2.9 | +7.2 (t 1.60) | **64%** |
| Value proxy (LTR 36-12 losers) | 3.9 | +2.9 (t 1.48) | +0.2 (t 0.11) | ≈ −2.5 | +5.0 (t 1.80) | +1.0 | n/a |

**E7-QC long-short, gross** (the short leg is unimplementable in ban years) — [E7_factor_quickcheck.csv](file:///home/claude/research_notes/QUANTGEN%20technical%20and%20fundamental%20signals/E7_quickchecks/E7_factor_quickcheck.csv); [E7_part2_signal_splits.csv](file:///home/claude/research_notes/QUANTGEN%20technical%20and%20fundamental%20signals/E7_quickchecks/E7_part2_signal_splits.csv):
- **Low-vol long-short:** +16.2%/yr (Sharpe 0.76) in 2015–19 and +21.2% (Sharpe 1.12) in 2020–24. The high-vol quintile lost **59.1% and 61.8%** over those windows.
- **Low-MAX long-short:** +17.6% (Sharpe 1.03) and +12.9% (0.85).
- **1-month reversal long-short:** +16.2% (Sharpe 0.98, t 2.04), net +2.1%, in 2015–19; +9.2% gross, net −4.6%, in 2020–24.
- **12-1 momentum long-short:** −5.1% (2015–19) and +2.5% (2020–24).
- **Size (small minus big):** −7.9% and −4.8%.
- **Reversal by market (2015-07 – 2024-12):** KOSDAQ-only long-short +15.2% gross (t 2.59) but long-only net −1.4%; KOSPI-only long-short +6.1% (t 1.08) and long-only net −5.7% — [E7_part8](file:///home/claude/research_notes/QUANTGEN%20technical%20and%20fundamental%20signals/E7_quickchecks/E7_part8_value_proxy_and_market_split.csv).
- **Weekly 5-day reversal, weekly rebalance:** long-leg one-way turnover **41.7×/yr**. Long-short gross +18.8%/yr (Sharpe 1.08) in 2015–19 becomes **−39.7% net**; long-only +9.3% gross becomes **−20.0% net**. In 2020–24: +7.5% gross becomes −50.0% net — [part 1 stdout](file:///home/claude/research_notes/QUANTGEN%20technical%20and%20fundamental%20signals/E7_quickchecks/e7_checks_part1_stdout.txt).
- **The prior design's daily reversal spec** (bottom-quintile 5-day z-score with volume ≥ 1.5× its 20-day average), 2015-07 to 2026-08: **−0.4 bp (t+1), +12.3 bp (t+5, t 0.03), +31.5 bp (t+20, t 0.63)**. By sub-period at t+5: **2015–19 +34.0 bp (t 3.45); 2020–24 +0.6 bp; 2025–26 −21.0 bp**. The low-volume mirror gave −38.7 bp at t+20 — [E7_part4_reversal_variants.csv](file:///home/claude/research_notes/QUANTGEN%20technical%20and%20fundamental%20signals/E7_quickchecks/E7_part4_reversal_variants.csv).
- **By short-sale regime** (2015-07 – 2026-09, gross long-short, annualised) — [E7_part2_shortban_regimes.csv](file:///home/claude/research_notes/QUANTGEN%20technical%20and%20fundamental%20signals/E7_quickchecks/E7_part2_shortban_regimes.csv):

  | Family | Open | Partial ban (only K200/KQ150 shortable) | Full ban |
  |---|---|---|---|
  | Low-vol | +14.3% | **+27.0%** | +14.9% |
  | Low-MAX | +12.3% | +18.6% | +11.4% |
  | 1-month reversal | +4.5% | +15.3% | +8.9% |
  | 12-1 momentum | +3.5% | +3.5% | −0.9% |

**Literature**
- **Sim & Kim** (JDQS 2021; KRX, Jan 1999 – Feb 2021) — [Emerald](https://www.emerald.com/jdqs/article/29/3/174/206550/The-effect-of-short-term-return-reversals-on):
  - pret(12,2) five-factor alpha **0.285%/month (t 0.85)**; pret(12,7) **0.531% (t 2.05)**;
  - one-month **reversal coefficient −2.950 (t −3.77)**; reversal strategy (k = 1) five-factor alpha **1.275%/month (t 3.22)**, gross;
  - momentum's term structure reflects two-month reversal.
  - *Correction to the brief:* the paper reports −2.950 as a regression coefficient. Its strategy-level figure is the 1.275%/month alpha. The brief's "−2.95%/month return" label is probably a misreading.
- **Eom, Chang, Kang, Lee & Park** (KJFS 2020; Jul 2000 – Jun 2019) — [KJFS](https://www.e-kjfs.org/journal/view.php?number=901):
  - high-turnover winner-minus-loser 12-1 (one-month holding) **−6.13%/yr (t −4.76)**, FF3 alpha −5.97% (t −3.08);
  - low-turnover −0.53% (t −1.17);
  - driven by loser rebounds (+6.85%, t 4.87).

**Failed check**
- An OHLC effective-spread estimator (Abdi–Ranaldo close-high-low) gave median full spreads of **57–79 bp even for > ₩2tn names**. That is implausible against one-tick quotes in mega-caps, so the estimator is unusable on KRX daily data — [E7_part3_spread_proxy.csv](file:///home/claude/research_notes/QUANTGEN%20technical%20and%20fundamental%20signals/E7_quickchecks/E7_part3_spread_proxy.csv).

### Inferences
- **Korean momentum lives in low-turnover stocks.** Over 2015-07 to 2024-12 the low-turnover tercile's winners beat the EW universe by +6.0%/yr gross, while high-turnover winners lagged by 8.4%/yr. That replicates the *winner* side of Eom et al. on a later, partly out-of-sample window. It does not replicate their negative long-short (high-turnover long-short was −0.2% in 2015–19 and +6.9% in 2020–24). The prior "XS-mom weight 1" is right only for a low-turnover or residual variant.
- **Reversal's gross edge is real but has decayed.** Monthly reversal earned +7.5%/yr gross in 2015–19, +1.3% in 2020–24 and −15% in the melt-up. At 10× (monthly) to 42× (weekly) turnover, 35 bp per side removes it. The prior weight of 3 and the "costs take half" estimate are too optimistic: at QUANTGEN's costs the costs take **more than all** of it. The volume filter from the prior design does not rescue it.
- **Low-vol and low-MAX** are mainly *avoid-the-lottery* effects: the high-vol and high-MAX quintiles lost about 60% over five years. A long-only investor gets only the small long-leg premium. Their value is crash protection (§7), which suits a drawdown-first protective card rather than an alpha card.
- **Overpricing looked worst when shorting was restricted** (partial-ban long-short spreads roughly double the open-regime values). That fits Miller-type short-sale constraints but is confounded with the 2021–22 bubble deflation. QUANTGEN should carry a **short-regime flag** and run the diff-in-diff in DC3 before using it.
- **Size:** small caps lost to large caps inside the liquid universe in every window (−47%/yr in the melt-up). The prior "weak: size" is confirmed; set it to 0.

### Gaps
- Earnings-announcement drift (prior Korea weight 3) was **not tested or researched** here: no announcement dates or consensus locally. Needs OpenDART filing timestamps and KIS or FnGuide consensus.
- Residual (FF3-residual) momentum and 12-7 momentum were not run locally. Sim & Kim's pret(12,7) is the only evidence.

---

## 7. The 2025–2026 melt-up and crash

### Takeaway
The melt-up was a two-stock event. In H1 2026, **two-thirds of KOSPI stocks fell** while the index doubled. Strategies that leaned on the leaders (12-1 momentum, 52-week high, 정배열) won the melt-up and lost most in the crash: momentum winners fell −43% against −25% for the EW universe. Everything contrarian or defensive lost the melt-up and protected in the crash:
- **low-vol was flat (−0.8%) while the universe fell 25%**;
- the top low-vol quintile in the K200 proxy rose 3.2% while the CW proxy fell 39%.

Then low-vol gave most of it back in the 31 Jul–29 Sep rebound. Short-term reversal and small caps lost in both phases.

### Cited Findings
**Index path** (from the companion macro research, partly recomputed here)
- KOSPI **+75.6% in 2025** and **+101.1% in H1 2026**.
- Closing **peak 9,114.55 on 22 Jun 2026**, then **−38.6%** to **5,593.56 on 30 Jul**.
- Record daily moves: **−12.06% on 4 Mar**, **−9.99% on 23 Jun** and **+17.91% on 31 Jul**.
- Sources: project doc `QUANTGEN_macro_overlay_research_report.md`; [Korea JoongAng Daily](https://www.koreajoongangdaily.com/business/kospi-hits-fresh-record-over-9100-as-chip-stocks-rally/12734799); [Sedaily 31 Jul](https://en.sedaily.com/finance/2026/07/31/kospi-whipsaws-18-percent-plunge-over-three-days-then-18).
- Local cap-weighted KOSPI common stocks reproduce **−38.6% for 22 Jun–30 Jul** exactly — [part 3 stdout](file:///home/claude/research_notes/QUANTGEN%20technical%20and%20fundamental%20signals/E7_quickchecks/e7_checks_part3_stdout.txt).

**Breadth** (local, KOSPI common stocks, price) — same file

| Window | n | EW mean | Median | Share falling | CW | CW ex-pair | Samsung / SK hynix |
|---|---|---|---|---|---|---|---|
| 2 Jan – 30 Dec 2025 | 836 | +28.6% | +12.4% | 32.7% | +75.9% | +48.0% | +125% / +280% |
| 30 Dec 2025 – 22 Jun 2026 | 831 | **+2.8%** | **−9.3%** | **66.2%** | **+117.1%** | +41.7% | +195% / +349% |
| 22 Jun – 30 Jul 2026 | 815 | −10.6% | −7.8% | 73.4% | −38.6% | −25.8% | −41% / −55% |
| 30 Jul – 29 Sep 2026 | 812 | +12.7% | +6.6% | 26.0% | +22.8% | +13.7% | +32% / +34% |

- On 27 May 2026, a record intraday high (8,457.09), only **77 KOSPI stocks rose and 826 fell** — [Sedaily](https://en.sedaily.com/finance/2026/05/27/samsung-sk-hynix-surge-alone-as-chip-duo-tops-half-of-kospi).

**Concentration**
- Samsung + SK hynix share of KOSPI market cap (local, all KOSPI listings as denominator): end-2015 16.7%, end-2019 27.2%, end-2022 21.8%, **end-2023 26.9%**, end-2024 22.6%, end-2025 34.0%, **50.4% on 27 May 2026** (Sedaily: 50.44%), **55.7% on 22 Jun**, **peak 57.1% on 25 Jun**, 50.8% on 29 Sep 2026.
- Their share of KOSPI traded value: 8–15% in 2012–23, 21.6% (2024), 21.0% (2025), **42.8% (2026 YTD)** — [E7_part5_pair_share.csv](file:///home/claude/research_notes/QUANTGEN%20technical%20and%20fundamental%20signals/E7_quickchecks/E7_part5_pair_share.csv); [part 8 stdout](file:///home/claude/research_notes/QUANTGEN%20technical%20and%20fundamental%20signals/E7_quickchecks/e7_checks_part8_stdout.txt).
- *Conflict:* KEIA's "22% at end-2023" ([KEIA](https://keia.org/analysis/explaining-south-koreas-stock-market-boom/)) does not match the local 26.9%. It matches end-2022 (21.8%) or end-2024 (22.6%). The anchor in the companion project docs should be corrected.

**Factor behaviour by phase** (local, liquid universe, long-only cumulative returns against EWM; IS) — [E7_part7](file:///home/claude/research_notes/QUANTGEN%20technical%20and%20fundamental%20signals/E7_quickchecks/E7_part7_longonly_vs_monthformed_EW.csv); [E7_factor_quickcheck.csv](file:///home/claude/research_notes/QUANTGEN%20technical%20and%20fundamental%20signals/E7_quickchecks/E7_factor_quickcheck.csv); [E7_part8](file:///home/claude/research_notes/QUANTGEN%20technical%20and%20fundamental%20signals/E7_quickchecks/E7_part8_value_proxy_and_market_split.csv)

| Family | Melt-up, 2 Jan 2025 – 22 Jun 2026 (EWM +45.5%) | Crash, 23 Jun – 30 Jul 2026 (EWM −25.4%) | Rebound, 31 Jul – 29 Sep 2026 (EWM +29.5%) |
|---|---|---|---|
| 12-1 momentum winners | **+87.4%** (+20.0%/yr excess, t 2.09) | **−43.0%** | **+52.7%** |
| … low-turnover tercile | +84.1% | **−14.5%** | +10.8% |
| … high-turnover tercile | +55.3% | −46.4% | +64.5% |
| 52-week high | +94.7% | −26.2% | +17.5% |
| 1-month reversal (losers) | +16.0% (−15.0%/yr excess, t −1.84) | −33.2% | +38.1% |
| 60d low-vol | +38.5% | **−0.8%** | +5.4% |
| Low MAX | +35.6% | −10.3% | +9.2% |
| Value proxy (LTR) | +26.5% | −32.4% | +39.7% |
| Small (size Q1) vs big (Q5) | +5.8% vs **+106.3%** | −27.5% vs −26.2% | +38.7% vs +19.4% |
| 정배열 state | +78.0% | **−48.7%** (vs −27.1% daily EW) | +14.0% (September only: just 12 liquid aligned names at the 31 Jul close, below the 30-name minimum, so August was skipped) |

**Leverage context**
- Margin loans were ₩36.25tn on 26 May 2026; 16 single-stock leveraged ETFs launched in May; VKOSPI reached 70.83 — [Sedaily](https://en.sedaily.com/finance/2026/05/27/samsung-sk-hynix-surge-alone-as-chip-duo-tops-half-of-kospi).
- Samsung and SK hynix leveraged products fell about 25% on 23 Jun — [Sedaily](https://en.sedaily.com/markets/2026/06/23/kospi-plunges-10-percent-on-chip-concentration-leverage).
- On 31 Jul SK hynix hit its upper limit for the first time since 28 Jan 2009 — [Sedaily](https://en.sedaily.com/finance/2026/07/31/kospi-whipsaws-18-percent-plunge-over-three-days-then-18).
- Korea's September 2026 exports were **$120.9bn (+83.5%)**, with chips **$60.3bn (+263%)** — [Korea Times](https://www.koreatimes.co.kr/economy/20261001/koreas-monthly-exports-hit-1209-bil-in-sept-on-record-chip-sales).

### Inferences
- **The July 2026 momentum crash happened inside a market crash after a bull run,** the opposite of the Daniel–Moskowitz rebound-from-bear pattern. A 24-month market-return gate would have stayed OFF, as the macro research found for the US. Only own-volatility scaling (Korea rv21 was above 30% on 88% of 2026 days, per the macro research) and concentration caps could have cut it. That needs testing (DC4).
- **Low-turnover momentum fell 14.5% against the universe's 25.4%.** The turnover split is also a crash-risk split: high-turnover winners are the retail-leveraged names.
- **Low-vol is the only family that protected,** and it handed back 24 points of relative return in the 60-day rebound. As an alpha card it would be REJECTed for its bull tax; as a protective card it is promising.
- Cap-weighted KOSPI behaved like a two-stock option on memory prices. A long-only Korean factor sleeve benchmarked to KOSPI would have shown about −70 to −250 points of underperformance in the melt-up, and a large outperformance in the crash, purely from the pair. Use EW and CW-ex-pair benchmarks.

### Gaps
- Margin-debt and leveraged-ETF AUM daily series (BL-U01) were not available locally, so whether leverage *led* the crash is untested.
- Retail and foreign flows at stock level during the crash are unavailable.

---

## 8. Where and when it failed (mandatory)

### Takeaway
Every Korean signal family had at least one dated episode of large failure in 2015–2026. Most failures cluster in retail-boom years (2015 H1, 2020, 2021, 2025–26) and in the July 2026 deleveraging.

### Cited Findings
Sources: local E7-QC files [part 7 years](file:///home/claude/research_notes/QUANTGEN%20technical%20and%20fundamental%20signals/E7_quickchecks/E7_part7_calendar_years_net_vs_EWM.csv), [part 7](file:///home/claude/research_notes/QUANTGEN%20technical%20and%20fundamental%20signals/E7_quickchecks/E7_part7_longonly_vs_monthformed_EW.csv), [part 3/4/6](file:///home/claude/research_notes/QUANTGEN%20technical%20and%20fundamental%20signals/E7_quickchecks/); press as cited. All local values are net of 35 bp unless marked gross, and are excess returns versus EWM.

| Date | Family / rule | What happened |
|---|---|---|
| 23 Jun – 30 Jul 2026 | **12-1 momentum** | Winners −43.0% against EW −25.4%. Mid- and high-turnover winners −41.6% / −46.4%. |
| 23 Jun – 30 Jul 2026 | **정배열 state** | −48.7% (against −27.1% daily EW). |
| 23 Jun – 30 Jul 2026 | **Price > MA200** | −34.6%. |
| 23 Jun – 30 Jul 2026 | **Value proxy** | −32.4%. |
| 23 Jun – 30 Jul 2026 | **1-month reversal** | −33.2%. |
| 23 Jun – 30 Jul 2026 | **K200-proxy 12-1 momentum** | −44.4% (CW −39.3%). |
| 2 Jan 2025 – 22 Jun 2026 | **1-month reversal** | −15.0%/yr gross excess (−22.2% net). Weekly reversal −37.1%/yr net. |
| 2 Jan 2025 – 22 Jun 2026 | **Size** | Small +5.8% against big +106.3%. |
| 2 Jan 2025 – 22 Jun 2026 | **Value proxy / low-vol** | −9.8% / −6.0% per year gross excess. |
| 2 Jan 2025 – 22 Jun 2026 | **Breadth** | 66.2% of KOSPI stocks fell in H1 2026 while the index rose about 101%. |
| 31 Jul – 29 Sep 2026 | **Low-vol** | +5.4% against EW +29.5% (−24 pp). |
| 31 Jul – 29 Sep 2026 | **Low-MAX** | +9.2% (−20 pp). |
| 31 Jul – 29 Sep 2026 | **52-week high** | +17.5% (−12 pp). |
| 31 Jul – 29 Sep 2026 | **Low-turnover momentum** | +10.8% (−19 pp). |
| 2020 (COVID retail boom) | **Low-vol** | −19.8% net vs EWM. |
| 2020 | **Low-MAX** | −16.4%. Lottery stocks rallied while new retail accounts turned over 6.8% a day (KCMI). |
| 2020 | **Low-turnover momentum** | −11.3%. |
| 2021 | **12-1 momentum** | −18.4%; high-turnover momentum **−31.0%**. |
| 2017 | **High-turnover momentum** | −20.2%. |
| 2015 (limit regime change; KOSDAQ bio/theme rally) | **Low-vol / low-MAX** | −12.8% / −17.2%. |
| 2023 | **Low-turnover momentum** | −12.5%. |
| 2023 | **Low-MAX** | −10.8%. |
| 2024 – 2026 YTD | **1-month reversal** | −11.7% (2024), −16.3% (2025), −17.0% (2026 YTD). Reversal net was negative in 8 of 11 years from 2015 to 2025. |
| 2015–19, 2020–24, 2025–26 | **Limit-up chasing** (next-open entry) | Negative in every window: −305, −431, **−462 bp** at t+5 (gross). |
| 2015–19, 2020–24, 2025–26 | **Volume-spike chasing** | Negative in every window: −96, −82, **−160 bp** at t+20 (gross). |
| 2020–24 and 2025–26 | **Prior-design daily reversal** (5d z with volume ≥ 1.5×) | Positive only in 2015–19 (+34 bp at t+5). Then +0.6 bp and **−21 bp** gross, against a 70 bp round trip. |
| 4 Mar 2026 (−12.06%, record) | **Foreign-flow direction** | Foreigners were net *buyers* (₩231.2bn) on the worst day ever — [Korea Herald](https://www.koreaherald.com/article/10686893). |
| H1 2026 | **Foreign-flow direction** | Foreigners net-sold ₩148.3tn while KOSPI rose about 101% — [KEIA](https://keia.org/analysis/explaining-south-koreas-stock-market-boom/). |
| 23 Jun 2026 (−9.99%) | **Retail "buy the dip"** | Retail bought a record ₩8.54tn; KOSPI fell a further 32% to 30 Jul (8,203.84 → 5,593.56) — [Sedaily](https://en.sedaily.com/markets/2026/06/23/kospi-plunges-10-percent-on-chip-concentration-leverage). |
| 2024 (Nov 2023 – Mar 2025 short ban) | **"Ban supports prices"** | KOSPI −10.1%, KOSDAQ −22.8% — [KCMI](https://www.kcmi.re.kr/en/publications/pub_detail_view?syear=2025&zcd=002001017&zno=1840&cno=6517). |
| 3 months to 2 Oct 2026 | **Value-up tracker** | RISE Korea Value-Up ETF −15.88%: the "governance" index fell with chips — [RISE ETF](https://eng.riseetf.co.kr/prod/finderDetail/44H7). |

### Inferences
- Failures are **regime-clustered**, not random. Retail-boom years (2015 H1, 2020, 2021, 2025–26) break defensive and contrarian books. Deleveraging episodes (Jul 2026) break trend and momentum books. A Korea card that passes on 2015–2019 alone should be treated as unproven.
- No single family has ≥ 60% positive years net of costs except 52-week high (64%), so most will fail gate step 8 as specified.

### Gaps
- Episodes before 2015 (2008 GFC, 2011 ban) were not run. The data exist back to 1995, and the ±15% limit regime before 15 Jun 2015 must be handled separately.

---

## 9. QUANTGEN translation: Korea weights, constraints and ranked first experiments

### Takeaway
Re-weight Korea away from reversal and flow and towards an **attention-fade exclusion screen**, protective low-vol, and low-turnover vol-scaled momentum. Make **long-only realism, limit-state fills, a short-regime flag, liquidity screens and two-stock-aware benchmarks** mandatory for every Korea card.

### Cited Findings
The basis is §§2–8 (E7-QC files and the sources cited there). The companion macro decisions apply unchanged:
- macro sizes risk only;
- Korea gets a 20-day local volatility target capped at 1.0;
- Samsung + SK hynix pair cap of ≤ 0.35 of the long book when their KOSPI share exceeds 0.45;
- momentum gets own-volatility scaling plus a floored D&M gate;
- reversal and quality are held at 1.0×.

Source: project doc `QUANTGEN_MACRO_INTEGRATION.md` R-07 and §2.

### Inferences
**Proposed Korea weights** (0–3; prior → E7 proposal; all remain UNVERIFIED until a gate run)

| Family | Prior | E7 | Reason |
|---|---|---|---|
| XS momentum | 1 | **1, low-turnover or residual variant only, vol-scaled; raw 12-1 = 0** | Low-turnover winners +3.1%/yr net (t 0.8); high-turnover −10.9%; −43% crash in Jul 2026 |
| Short-term reversal | 3 | **1 for monthly reversal as a conditioning or tie-break input; 0 for daily or weekly** | Gross edge decayed after 2019; net negative at 35 bp; weekly −20%/yr net |
| Value | 2 | **1 until the OpenDART test** | LTR proxy +0.2% net; Value-up confounded by chips; 2024 structural break |
| Quality | 1 | 1 | Untested locally; Value-up screens reward ROE and profitability (a possible tailwind post-2024) |
| Low-vol | 2 | **2, as a protective card, not alpha** | +1.7% net (t 0.5), but −0.8% vs −25.4% in the Jul 2026 crash |
| Flow | 3 | **1 (log now, test)** | Literature: positive feedback, permanent same-day impact; 2026 sign failures |
| Earnings drift | 3 | 2 | No Korean evidence reviewed or tested here |
| TS momentum | 2 | 1 | KOSPI long/flat 0.47 vs 0.52 (macro research); stock trend states negative in 2015–24 |
| **NEW: attention-fade exclusion** | — | **3 (as a screen)** | Robust negative 5–20-day excess for spikes and limit-up chases, t −5 to −14, in all sub-periods |
| Size | weak | 0 | Small minus big negative in every window |

**Mandatory Korea constraints**
1. **Long-only realism.** Gate every Korea stock card long-only against EWM, plus K200-proxy CW and CW-ex-pair as reported comparators. Long-short results are reported only as overpricing diagnostics.
2. **Short-regime flag.** Carry a regime value on every Korea card:
   - 0 = open;
   - 1 = partial (3 May 2021 – 5 Nov 2023: only K200/KQ150 shortable);
   - 2 = full ban (1 Oct 2008 – 31 May 2009; 11 Aug – 9 Nov 2011; 16 Mar 2020 – 2 May 2021; 6 Nov 2023 – 28 Mar 2025).

   Report results by regime.
3. **Limit-state fill rule.**
   - Entry at a locked limit-up close (≥ 29.5% from 15 Jun 2015, ≥ 14.5% before, with close = high) is not allowed. The order is carried to the t+1 open price.
   - An exit at a locked limit-down close is carried forward to the first unlocked session, at 2× cost.
   - Flag VI and circuit-breaker days.
4. **Liquidity and eligibility screens** (point-in-time):
   - market cap ≥ ₩100bn, 20-day ADV ≥ ₩1bn (a ₩3bn capacity variant), price ≥ ₩1,000;
   - exclude 관리종목, 투자주의환기종목, SPACs and preferreds;
   - drop IPO and relisting days and post-delisting liquidation trading.
5. **Attention-fade exclusion.** Do not open longs in names that, within the last 5 sessions (20 for blow-offs):
   - had volume ≥ 5× their 20-day average with r ≥ +5%; or
   - closed locked limit-up; or
   - rose ≥ 50% over 20 days; or
   - sit in the top decile of 21-day MAX.
6. **Costs.** 35 bp per side, with a 70 bp stress. Add a time-varying sell-tax sensitivity: 0.20% / 0.18% / 0.15% / 0.20% for 2023–26, plus the verified pre-2023 schedule.
7. **Data convention.** marcap returns are price-only. Add dividends before judging value, low-vol or dividend cards, otherwise they are understated by roughly their yield.
8. **Concentration.** Apply the companion pair cap and semis cap. Also report each Korea card's correlation with the pair's return.

**Ranked first experiments on KRX stock-level data**

| Rank | Card | Spec (decide at close t, earn t+1) | Why first | Expected risk |
|---|---|---|---|---|
| 1 | **K-AF attention-fade exclusion** | Apply constraint 5 to three base books (EW universe, low-vol Q5, momentum Q5). Measure ΔSharpe, ΔMDD and Δturnover against the same book without exclusion, 2015-07 – 2026-09, at 35 / 70 bp. | Strongest and most robust Korean evidence (t −5 to −14, all sub-periods); no shorting needed; low turnover | Benefit only where the base book would have bought flagged names |
| 2 | **K-LV protective low-vol** | 60-day low-vol (and low-MAX) top quintile in the liquid universe and the K200 proxy; monthly with a no-trade band; judged as a protective card (drawdown-first, Sharpe non-inferiority) | Only family that protected in Jul 2026 (−0.8% vs −25.4%; K200 +3.2% vs −39.3%) | Bull tax (−24 pp in the Aug–Sep rebound); 2015 and 2020 losses |
| 3 | **K-MOM-LT low-turnover momentum** | 12-1 (and 12-7) winners within the bottom 12-month-turnover tercile; long-only; own-vol scaling (σ126, 12% target, cap 1.0) + D&M floor 0.5; pair cap | Only family positive net at 35 bp (+3.1%/yr) and about +0.2% at 70 bp; low-turnover winners fell 14.5% vs 43% for all winners in the crash | t 0.8; 45% positive years; a 2020 and 2023 drag |
| 4 | **K-FLOW** | t−1 final foreign / institutional / individual net buys from KIS, scaled by market cap → t+1 open-to-close and close-to-close returns; deciles by size; 5-day foreign-buy streaks; split pre/post 2026-05 | Prior weight 3 is unverified; literature says same-day impact; starts the forward record now | No history locally; 2026 sign breaks |
| 5 | **K-VAL/QUAL** (OpenDART) | Point-in-time B/M, E/P, GP/A, ROE, accruals, dividend and net-buyback-cancellation yield (filing date + 1 session); sector-neutral; split pre/post Feb 2024 | Value is untested; the Value-up regime break needs a clean test | Data engineering; break in 2024 |
| 6 | **K-52WH** | 52-week-high proximity, quarterly rebalance to cut turnover from 6.1× | 64% of years positive (the only family ≥ 60%) | Net +1.0% (t 0.33); fails at 2× costs at monthly turnover |
| 7 | **K-SHORTREG study** (context) | Diff-in-diff: MAX and high-vol quintile returns, shortable (K200/KQ150) vs non-shortable names, 3 May 2021 – 5 Nov 2023; event windows around 6 Nov 2023 and 31 Mar 2025 | Decides whether exclusion and low-vol screens should be regime-weighted | Needs historical index membership |
| 8 | **K-LD exit rule** | After a locked limit-down, exit at the t+1 open against holding | Limit-downs continue (−6.6% the next day, −10.9% at 20 days) | Rare events (n = 755); fills uncertain |

**DROP** (record as REJECT cards, not built):
- daily and weekly short-term reversal at 35 bp;
- golden and dead crosses (5/20, 20/60);
- 정배열 onset and 정배열-state books;
- price above MA200 as a stock-selection rule;
- limit-up chasing (상한가 따라잡기) and volume-spike buying;
- size tilt;
- raw all-name 12-1 momentum.

### Gaps
- None of the ranked experiments has run through the nine-step gate. All weights are proposals.

---

## 10. Data-check requests for the data lab

### Takeaway
Eleven exact tests: eight on the existing marcap KRX data, three that need new data (KIS flows and quotes, OpenDART).

### Cited Findings
- **DC1: Gate re-run of the E7-QC factor table.**
  - Universe and returns as defined above. Monthly quintiles for 12-1 momentum (all, and by 12-month-turnover tercile), 1-month reversal, 60d low-vol, 21d MAX, 52-week high and LTR 36-12.
  - Long-only against month-formed EW; costs 35 / 70 bp per side.
  - Nine-step gate: purged walk-forward 756 / 126 with embargo = holding period, Lo SE, block bootstrap, DSR counting all E7 trials (about 20 families × variants), PBO, and the 60%-years criterion.
  - Report 2015-07 – 2024-12 and 2025-01 – 2026-09 separately.
  - Pass: low-turnover momentum interval clears zero at 35 bp. Expectation: INSUFFICIENT DATA or REJECT.
- **DC2: Attention-fade exclusion.**
  - Events:
    - (a) volume ≥ 5× 20-day average and r ≥ +5%;
    - (b) locked limit-up (change ≥ 29.5% and close = high; ≥ 14.5% before 15 Jun 2015), entry priced at the t+1 open;
    - (c) 20-day return ≥ +50%;
    - (d) top decile of 21-day MAX.
  - Measure t+1 / 5 / 20 excess with date-clustered t, by sub-period and by market.
  - Then exclude names flagged in the last 5 (or 20) sessions from three base books and report ΔSharpe, ΔMDD and Δturnover at 35 / 70 bp.
- **DC3: Short-regime diff-in-diff.**
  - During 2021-05-03 – 2023-11-05, compare MAX and high-vol quintile next-month returns for KOSPI200/KOSDAQ150 constituents (shortable) against non-constituents. Repeat in ±60-session windows around 2023-11-06 (ban) and 2025-03-31 (resumption).
  - Needs historical index membership: KRX index-change files.
- **DC4: Momentum crash anatomy.**
  - 12-1 winners against EW over 2026-06-23 – 07-30: does own-vol scaling (σ126, 12% target, cap 1.0) and/or the D&M gate (24-month KOSPI return < 0 → 0.5) reduce the −43.0% loss?
  - Report the low-turnover variant and the pair-capped variant.
- **DC5: Limit-fill audit.** For every Korea card, count simulated entries at locked limit-up closes and exits at locked limit-down closes. Re-price them under the fill rule (§9, constraint 3) and report the Sharpe change.
- **DC6: Tax schedule sensitivity.** Re-run DC1 with the time-varying sell tax (2023 0.20%, 2024 0.18%, 2025 0.15%, 2026 0.20%; pre-2023 once verified from MOEF or KRX) plus commission and spread, against the flat 35 bp.
- **DC7: Concentration anchors.**
  - Recompute the Samsung + SK hynix share of KOSPI cap at every year-end 2015–2026, using all listings and common-only denominators. Local: end-2023 26.9% against KEIA's 22%.
  - Report EW, CW and CW-ex-pair KOSPI returns by year, and correct the project anchor.
- **DC8: Cost calibration.** OHLC spread estimators fail on KRX (CHL median 57–79 bp for > ₩2tn names). Pull KIS bid/ask snapshots at the close for a stratified sample (K200, KOSDAQ150, small caps), including stress days (4 Mar, 23 Jun, 28–31 Jul 2026), and test whether 35 bp per side covers half-spread + commission + 0.5 × sell tax.
- **DC9: Flow card (new data).**
  - KIS daily investor-type net buys by stock, 2015–2026 (or log from now): foreign, institution (with pension), individual.
  - Signal: t−1 final net buys / market cap, deciles, and 5-day streaks. Targets: t+1 open-to-close and close-to-close excess returns, by size tercile.
  - Split pre/post 2026-05-01 (single-stock leveraged ETFs). Also aggregate KOSPI-level flows → next-day index return.
- **DC10: OpenDART value and quality.**
  - Point-in-time book equity, earnings, gross profit, accruals, dividends, buyback and cancellation filings, each available from filing date + 1 session.
  - B/M, E/P, GP/A, ROE and shareholder yield; sector-neutral quintiles; long-only against EW.
  - Split pre/post 2024-02-26 (Value-up announcement window).
- **DC11: Dividend-inclusive returns.** Add cash dividends (OpenDART or KRX) to the marcap price returns. Recompute low-vol, value and K200-proxy results, and report the yield gap by family.

### Inferences
- DC2, DC4, DC5 and DC7 can run immediately on marcap. DC9–DC11 need new data. DC9 should start logging today, because the forward record is the only clean test of the 2026 flow regime.

### Gaps
- The marcap file has no ETFs, flows, short-sale balances, fundamentals or index membership. Each of those needs KIS, KRX or OpenDART.

---

## 11. Claims ledger (mandatory)

| ID | Claim (one sentence) | Evidence (numbers, market, period, IS/OOS, gross/net) | Source(s) with URL | Tier | Robustness | Failure cases | QUANTGEN implication |
|---|---|---|---|---|---|---|---|
| E7-C01 | KRX daily price limits widened from ±15% to ±30% on 15 Jun 2015. | Max daily change exactly 15.00% to 12 Jun 2015; 29.93–30.00% from 15 Jun; 22 names > 15.5% on day one | Local marcap (E7-QC part 5) | T1 (exchange data, local) | Exact | — | CONTEXT: limit thresholds by date in the fill rule |
| E7-C02 | Buying the next open after a locked limit-up close (상한가 따라잡기) loses; the close-to-close gain is unfillable. | Next-open entry −400 bp (t+5), −595 bp (t+20), date-clustered t −14.3 / −11.3, n = 10,943; close entry +332 bp at t+1; mean gap +5.0%; KRX 2015-07 – 2026-08, IS, gross | [E7_part2_retail_rule_events.csv](file:///home/claude/research_notes/QUANTGEN%20technical%20and%20fundamental%20signals/E7_quickchecks/E7_part2_retail_rule_events.csv) | T1-local | Negative in 2015–19, 2020–24 and 2025–26 | None for the fade; chasing fails everywhere | DROP chasing; BUILD-candidate: fill rule plus exclusion |
| E7-C03 | Locked limit-down closes continue rather than reverse. | −663 bp (t+1), −773 bp (t+5), −1,094 bp (t+20), n = 755, t ≈ −9 to −12; 2015-07 – 2026-08, IS, gross | Same file | T1-local | Single window; few events | — | BACKLOG: exit rule (K-LD); exclude from reversal books |
| E7-C04 | Volume-spike chasing (≥ 5× volume, ≥ +5% day) underperforms over 5–20 days. | −47 bp (t+5, t −5.2), −98 bp (t+20, t −6.7); sub-periods −96 / −82 / −160 bp at t+20; IS, gross | Same file | T1-local | All three sub-periods | — | BUILD-candidate: exclusion screen (rank 1) |
| E7-C05 | Golden and dead crosses and 정배열 signals carry no edge after 70 bp round trips. | Mean ≤ 17 bp over 1–20 days, date-clustered t ≤ 0; 정배열 state −10.9%/yr net (2015–19), −5.1% (2020–24), −48.7% in the Jul 2026 crash | Same file; [E7_part6](file:///home/claude/research_notes/QUANTGEN%20technical%20and%20fundamental%20signals/E7_quickchecks/E7_part6_trend_state_ports.csv) | T1-local | Large n (25k–77k events) | Melt-up only (+10.6% net) | DROP |
| E7-C06 | Korean retail investors underperform through turnover, disposition and lottery preference. | New investors −1.2% net vs +5.9% gross, 60% losing (Mar–Oct 2020, n = 204,004); daily turnover 6.8% vs 1.4%; disposition hazard ratio 2.18; lottery excess trading 32.7% | [KCMI 1243](https://www.kcmi.re.kr/report/report_view?report_no=1243); [KCMI 1481](https://www.kcmi.re.kr/report/report_view?report_no=1481); [fnnews](https://www.fnnews.com/news/202104131912345956) | T1 (KCMI); T2 press | Account-level, one cohort (2020) | Existing investors earned +15% net in 2020 | CONTEXT: supports attention-fade and MAX screens |
| E7-C07 | Individuals' share of traded value fell from 76% (1999) to 47% (2013); 2015–26 shares are unverified here. | KCMI structural-change report; foreigners 5% → 29%, institutions 16% → 23%; individual turnover 928% → 196% | [Seoul Shinmun / KCMI](https://www.seoul.co.kr/news/economy/securities/2015/05/26/20150526800049) | T2 reporting T1 | Old | 2020–21 retail surge (local turnover doubled) | CONTEXT; data request (KIS flows) |
| E7-C08 | Korea imposed four complete short-sale bans plus a partial regime; the 2023–25 ban did not support prices. | 1 Oct 2008 – 31 May 2009; 11 Aug – 9 Nov 2011; 16 Mar 2020 – 3 May 2021, then K200/KQ150-only until Nov 2023; 5 Nov 2023 – 31 Mar 2025; 2024: KOSPI −10.1%, KOSDAQ −22.8% | [KCMI (Hwang 2025)](https://www.kcmi.re.kr/en/publications/pub_detail_view?syear=2025&zcd=002001017&zno=1840&cno=6517); [KED Global](https://www.kedglobal.com/short-selling/newsView/ked202503300002) | T1; T2 | Official chronology | The brief's "Nov 2008" is wrong (it was Oct 2008) | BUILD: short-regime flag; long-only cards |
| E7-C09 | Most Korean anomaly long-short profit sits in the short leg, which is unimplementable for long-only or ban-constrained investors. | Low-vol long-short +16.2% / +21.2% per year gross vs long-only +5.0% / +3.7% (2015–19 / 2020–24); low-MAX long-short +17.6% / +12.9% vs long-only +5.1% / +0.2%; high-vol quintile −59% / −62% | [E7_factor_quickcheck.csv](file:///home/claude/research_notes/QUANTGEN%20technical%20and%20fundamental%20signals/E7_quickchecks/E7_factor_quickcheck.csv); [E7_part7](file:///home/claude/research_notes/QUANTGEN%20technical%20and%20fundamental%20signals/E7_quickchecks/E7_part7_longonly_vs_monthformed_EW.csv) | T1-local | IS; consistent across windows | Melt-up: low-vol long-short ≈ 0 | BUILD: long-only realism in every Korea card |
| E7-C10 | Anomaly spreads were larger under the partial short ban, consistent with short-constraint overpricing but confounded. | Partial regime low-vol long-short +27.0%/yr vs +14.3% open; low-MAX +18.6% vs +12.3%; reversal +15.3% vs +4.5% (gross) | [E7_part2_shortban_regimes.csv](file:///home/claude/research_notes/QUANTGEN%20technical%20and%20fundamental%20signals/E7_quickchecks/E7_part2_shortban_regimes.csv) | T1-local | Confounded with 2021–22 bubble deflation | — | BACKLOG: DC3 diff-in-diff |
| E7-C11 | The all-in sell-side securities transaction tax was 0.20% (2023), 0.18% (2024), 0.15% (2025) and 0.20% (2026) on KOSPI and KOSDAQ. | 2026 reform enacted 23 Dec 2025, effective 1 Jan 2026; KOSPI includes a 0.15% rural special tax | [KPMG](https://assets.kpmg.com/content/dam/kpmgsites/kr/pdf/2025/tkc/tax-brief/korea-tax-brief-202508-eng_F.pdf.coredownload.inline.pdf); [PwC](https://taxsummaries.pwc.com/republic-of-korea/corporate/other-taxes); [EY](https://taxnews.ey.com/news/2026-0126-korea-enacts-2026-tax-reform-bill) | T2 | Three firms agree on totals | Pre-2023 unverified | CONTEXT: 35 bp per side covers it; DC6 sensitivity |
| E7-C12 | NXT runs 08:00–08:50, 09:00:30–15:20 and 15:40–20:00, and VIs cluster at the KRX open. | About 600 NXT stocks; 42% of KOSPI VIs in 9–10 a.m., 80.9% of those in the first 30 min; VI ≈ 2-minute auction | [Nextrade](https://nextrade.co.kr/); [Sedaily VI](https://en.sedaily.com/finance/2026/05/07/kospi-volatility-interruptions-double-in-early-trading-hours) | T1 (venue); T2 | The VI article's period is ambiguous | — | CONTEXT: signals at the KRX close only; price open entries at the auction |
| E7-C13 | Foreign flows in Korea are positive-feedback, with contemporaneous, permanent impact and no reversal. | KSE 1999–2002: autocorrelation 0.43; same-day correlation 0.39; impact 0.119 (t 11.9); complete within about 10 days | [Richards, RBA RDP 2004-05](https://www.rba.gov.au/publications/rdp/2004/pdf/rdp2004-05.pdf); [Choe–Kho–Stulz w6661](https://www.nber.org/papers/w6661) | T1 | Old samples; pre-2003 | — | BACKLOG: flows are same-day; test t−1 (DC9) |
| E7-C14 | The aggregate foreign-flow signal broke in 2026. | H1 2026: foreigners −₩148.3tn while KOSPI rose about 101%; 4 Mar (−12.06%): foreigners +₩231.2bn; 22 Jun peak: foreigners −₩2.55tn; 23 Jun (−9.99%): retail +₩8.54tn | [KEIA](https://keia.org/analysis/explaining-south-koreas-stock-market-boom/); [Korea Herald](https://www.koreaherald.com/article/10686893); [JoongAng](https://www.koreajoongangdaily.com/business/kospi-hits-fresh-record-over-9100-as-chip-stocks-rally/12734799); [Sedaily](https://en.sedaily.com/markets/2026/06/23/kospi-plunges-10-percent-on-chip-concentration-leverage) | T2 | Multiple outlets | — | Flow weight 3 → 1; regime split |
| E7-C15 | Value-up outperformance is largely memory-chip exposure, not a low-P/B value factor. | Index +134.9% vs KOSPI +101.5% (30 Sep 2024 – end-Jan 2026); KEIA: +17% vs KOSPI200; tracker top-2 = SK hynix 20.92% + Samsung 17.53%, IT 50.8%; 3M −15.88% to 2 Oct 2026; index screens on the top 50% by P/B | [Korea Times](https://www.koreatimes.co.kr/economy/20260204/koreas-value-up-index-sets-new-record-last-month-krx); [KEIA](https://keia.org/analysis/explaining-south-koreas-stock-market-boom/); [RISE ETF](https://eng.riseetf.co.kr/prod/finderDetail/44H7); [Glass Lewis](https://www.glasslewis.com/article/navigating-south-koreas-corporate-value-up-program) | T2 | Short history (2 years) | 3M −15.9% | CONTEXT: do not treat it as value evidence; DC10 |
| E7-C16 | Governance and tax reforms in 2025–26 create a structural break for value, dividend and shareholder-yield signals. | Commercial Act Jul and Aug 2025 (duty of loyalty, independent directors to 1/3, no cumulative-voting opt-out, two separately elected audit members); dividend separate tax 14/20/35% for qualifying payers from FY2026 (proposal) | [KEIA](https://keia.org/analysis/explaining-south-koreas-stock-market-boom/); [KPMG](https://assets.kpmg.com/content/dam/kpmgsites/kr/pdf/2025/tkc/tax-brief/korea-tax-brief-202508-eng_F.pdf.coredownload.inline.pdf) | T2 | Final dividend-tax terms unverified | — | BACKLOG: pre/post split in K-VAL |
| E7-C17 | Korean momentum profits reflect short-term reversal; 12-1 momentum is weak. | 1999 – Feb 2021: pret(12,2) alpha 0.285%/month (t 0.85); pret(12,7) 0.531% (t 2.05); reversal coefficient −2.950 (t −3.77); reversal-strategy alpha 1.275%/month (t 3.22), gross | [Sim & Kim, JDQS 2021](https://www.emerald.com/jdqs/article/29/3/174/206550/The-effect-of-short-term-return-reversals-on) | T1 (KCI) | Peer-reviewed; gross; pre-2021 | — | CONTEXT: the brief's "−2.95%/month" is a coefficient; the strategy alpha is 1.275%/month gross |
| E7-C18 | Momentum in Korea works only in low-turnover stocks; high-turnover winners lag. | Eom et al.: high-turnover winner-minus-loser −6.13%/yr (t −4.76), 2000–19. E7-QC 2015-07 – 2024-12: low-turnover winners +6.0% gross / +3.1% net (t 0.80); high-turnover −8.4% gross / −10.9% net | [Eom et al., KJFS 2020](https://www.e-kjfs.org/journal/view.php?number=901); [E7_part7](file:///home/claude/research_notes/QUANTGEN%20technical%20and%20fundamental%20signals/E7_quickchecks/E7_part7_longonly_vs_monthformed_EW.csv) | T1; T1-local | Winner side replicated on a later window; negative long-short not replicated | 2020 (−11.3%), 2023 (−12.5%) for low-turnover | BUILD-candidate: K-MOM-LT (rank 3) |
| E7-C19 | Short-term reversal does not pay at QUANTGEN's 35 bp per side. | Monthly long-only +4.2% gross → −2.7% net (2015-07 – 2024-12); weekly +9.3% gross → −20.0% net (2015–19, 41.7× turnover); prior-design daily spec +12 bp per 5 days (t 0.03), negative after 2020 | [E7_part7](file:///home/claude/research_notes/QUANTGEN%20technical%20and%20fundamental%20signals/E7_quickchecks/E7_part7_longonly_vs_monthformed_EW.csv); [E7_part4](file:///home/claude/research_notes/QUANTGEN%20technical%20and%20fundamental%20signals/E7_quickchecks/E7_part4_reversal_variants.csv); [part 1 stdout](file:///home/claude/research_notes/QUANTGEN%20technical%20and%20fundamental%20signals/E7_quickchecks/e7_checks_part1_stdout.txt) | T1-local | Decayed after 2019; IS | Net negative in 8 of 11 years | Reversal weight 3 → 1 (monthly) / 0 (daily, weekly) |
| E7-C20 | Low-vol is a crash hedge, not an alpha source, in Korea. | Long-only vs EWM +4.3% gross / +1.7% net (t 0.50), 2015-07 – 2024-12; 23 Jun – 30 Jul 2026: −0.8% vs −25.4% (K200 top quintile +3.2% vs CW −39.3%); rebound +5.4% vs +29.5% | [E7_part7](file:///home/claude/research_notes/QUANTGEN%20technical%20and%20fundamental%20signals/E7_quickchecks/E7_part7_longonly_vs_monthformed_EW.csv); [E7_part2 K200](file:///home/claude/research_notes/QUANTGEN%20technical%20and%20fundamental%20signals/E7_quickchecks/E7_part2_k200proxy_factor_years.csv) | T1-local | Price-only (understated by yield) | 2015 (−12.8%), 2020 (−19.8%), Aug–Sep 2026 | BUILD-candidate: protective card K-LV (rank 2) |
| E7-C21 | The size premium was negative in Korea 2015–2026. | Small minus big within the liquid universe: −7.9%/yr (2015–19), −4.8% (2020–24), −47.2%/yr (melt-up), gross long-short | [E7_factor_quickcheck.csv](file:///home/claude/research_notes/QUANTGEN%20technical%20and%20fundamental%20signals/E7_quickchecks/E7_factor_quickcheck.csv) | T1-local | All windows | Rebound only (+98% annualised) | DROP size tilt |
| E7-C22 | The 2025–26 melt-up had collapsing breadth: two-thirds of KOSPI stocks fell in H1 2026 while the index doubled. | 30 Dec 2025 – 22 Jun 2026: 66.2% fell, median −9.3%, EW +2.8%, CW +117.1%; 27 May 2026: 77 up, 826 down | [part 3 stdout](file:///home/claude/research_notes/QUANTGEN%20technical%20and%20fundamental%20signals/E7_quickchecks/e7_checks_part3_stdout.txt); [Sedaily](https://en.sedaily.com/finance/2026/05/27/samsung-sk-hynix-surge-alone-as-chip-duo-tops-half-of-kospi) | T1-local; T2 | Exact | — | BUILD: EW and CW-ex-pair benchmarks for every Korea card |
| E7-C23 | Samsung + SK hynix peaked at 57.1% of KOSPI cap (25 Jun 2026) and took 42.8% of KOSPI traded value in 2026. | All-listings denominator: 26.9% end-2023, 22.6% end-2024, 34.0% end-2025, 50.4% (27 May; Sedaily 50.44%), 55.7% (22 Jun), 50.8% (29 Sep 2026) | [E7_part5_pair_share.csv](file:///home/claude/research_notes/QUANTGEN%20technical%20and%20fundamental%20signals/E7_quickchecks/E7_part5_pair_share.csv); [Sedaily](https://en.sedaily.com/finance/2026/05/27/samsung-sk-hynix-surge-alone-as-chip-duo-tops-half-of-kospi) | T1-local; T2 | Matches Sedaily to 0.01 pp | — | CONTEXT: pair cap is binding; correlation to the pair reported |
| E7-C24 | KEIA's "pair 22% of KOSPI at end-2023" conflicts with KRX data. | Local end-2023 26.9%; 21.8% at end-2022; 22.6% at end-2024 | [KEIA](https://keia.org/analysis/explaining-south-koreas-stock-market-boom/); [E7_part8 stdout](file:///home/claude/research_notes/QUANTGEN%20technical%20and%20fundamental%20signals/E7_quickchecks/e7_checks_part8_stdout.txt) | T2 vs T1-local | Exact | — | CONTEXT: correct the anchor in project docs (DC7) |
| E7-C25 | 12-1 momentum crashed with the market in Jul 2026, without a D&M bear state, then rebounded. | Winners −43.0% vs EW −25.4% (23 Jun – 30 Jul); low-turnover −14.5%; rebound +52.7% vs +29.5% (31 Jul – 29 Sep); melt-up +20.0%/yr excess (t 2.09) | [E7_part7](file:///home/claude/research_notes/QUANTGEN%20technical%20and%20fundamental%20signals/E7_quickchecks/E7_part7_longonly_vs_monthformed_EW.csv) | T1-local | One episode | Jul 2026 | BUILD-candidate only with own-vol scaling + caps (DC4) |
| E7-C26 | Korean "smart beta" quintiles lost to the cap-weighted index in 2015–2024, mainly through underweighting Samsung and SK hynix. | K200 proxy 2015-07 – 2024-12: CW +17.7%, CW ex-pair −7.5%, EW200 +1.5%; low-vol Q5 −14.1%, momentum Q5 −15.3%, reversal Q5 −51.2% (net, price-only) | [E7_part2 K200](file:///home/claude/research_notes/QUANTGEN%20technical%20and%20fundamental%20signals/E7_quickchecks/E7_part2_k200proxy_factor_years.csv) | T1-local | Price-only; proxy, not actual ETFs | — | CONTEXT: benchmark choice decides verdicts; pull real ETF data |
| E7-C27 | Korean turnover is extreme and concentrated, so liquidity screens are mandatory. | KOSPI ADV ₩5.35tn (2015) → ₩12.2tn (2020) → ₩33.7tn (2026 YTD); KOSDAQ velocity 360–945%/yr; bottom half of names by cap = 1.6% (KOSPI) / 5.1% (KOSDAQ) of 2026 value | [E7_part5_turnover](file:///home/claude/research_notes/QUANTGEN%20technical%20and%20fundamental%20signals/E7_quickchecks/E7_part5_turnover_by_market_year.csv) | T1-local | Exact | — | BUILD: liquidity screens (§9, constraint 4) |
| E7-C28 | Daily-OHLC spread estimators are unusable on KRX for cost calibration. | CHL median full spread 57–79 bp even for > ₩2tn names (implausible vs one-tick quotes) | [E7_part3_spread_proxy.csv](file:///home/claude/research_notes/QUANTGEN%20technical%20and%20fundamental%20signals/E7_quickchecks/E7_part3_spread_proxy.csv) | T1-local (failed check) | — | — | BACKLOG: KIS quote snapshots (DC8) |
| E7-C29 | Retail leverage structure amplified the 2026 crash. | Single-stock leveraged ETFs in May 2026 (16 funds; ₩10.41tn first-day trading); margin ₩36.25tn (+33% y/y); VKOSPI 70.83; leveraged products about −25% on 23 Jun; July: 4 circuit breakers, 15 sidecars | [Sedaily 27 May](https://en.sedaily.com/finance/2026/05/27/samsung-sk-hynix-surge-alone-as-chip-duo-tops-half-of-kospi); [Sedaily 23 Jun](https://en.sedaily.com/markets/2026/06/23/kospi-plunges-10-percent-on-chip-concentration-leverage); [Sedaily 31 Jul](https://en.sedaily.com/finance/2026/07/31/kospi-whipsaws-18-percent-plunge-over-three-days-then-18); [KEIA](https://keia.org/analysis/explaining-south-koreas-stock-market-boom/) | T2 | n = 1 | — | BACKLOG: BL-U01 leverage state; log margin and ETF AUM |
| E7-C30 | 52-week-high proximity is the only family with ≥ 60% positive years net, but its edge is tiny. | Long-only vs EWM +5.1% gross / +1.0% net (t 0.33), 2015-07 – 2024-12; 64% of years positive; the crash was in line (−26.2% vs −25.4%) | [E7_part7](file:///home/claude/research_notes/QUANTGEN%20technical%20and%20fundamental%20signals/E7_quickchecks/E7_part7_longonly_vs_monthformed_EW.csv) | T1-local | IS; 6.1× turnover | Rebound −12 pp | BACKLOG: quarterly variant (K-52WH, rank 6) |

---

## 12. Source list

**Tier 1: academic, official, KCI journals and research institutes**
- KCMI (Hwang Seiwoon), "Short Selling Resumption in Korea", 1 Apr 2025 — https://www.kcmi.re.kr/en/publications/pub_detail_view?syear=2025&zcd=002001017&zno=1840&cno=6517 ; PDF https://www.kcmi.re.kr/common/downloadw?fid=27533&amp=&fgu=002001&amp=&fty=004003
- KCMI (Kim Min-gi, Kim Jun-seok), COVID-19 individual investors, Issue Report 21-11 — https://www.kcmi.re.kr/report/report_view?report_no=1243
- KCMI (Kim Min-gi, Kim Jun-seok), individual investors' behavioural biases, Research Report 22-02 — https://www.kcmi.re.kr/report/report_view?report_no=1481
- KCMI (Kang So-hyun, Kim Min-gi), individual investors' overseas investing, Research Report 26-04 — https://www.kcmi.re.kr/report/report_view?report_no=2254
- Sim & Kim, "The effect of short-term return reversals on momentum profits", JDQS 2021 — https://www.emerald.com/jdqs/article/29/3/174/206550/The-effect-of-short-term-return-reversals-on
- Eom, Chang, Kang, Lee & Park, "Investor Attention, Market Dynamics, and Momentum in the Korean Stock Market", KJFS 2020 — https://www.e-kjfs.org/journal/view.php?number=901
- Richards, "Big Fish in Small Ponds", RBA RDP 2004-05 — https://www.rba.gov.au/publications/rdp/2004/2004-05.html ; https://www.rba.gov.au/publications/rdp/2004/pdf/rdp2004-05.pdf
- Choe, Kho & Stulz, "Do Foreign Investors Destabilize Stock Markets? The Korean Experience in 1997", NBER w6661 / JFE 1999 — https://www.nber.org/papers/w6661
- Choe, Kho & Stulz, "Do Domestic Investors Have More Valuable Information…", NBER w8073 — https://www.nber.org/papers/w8073
- Nextrade (NXT) official site, session hours — https://nextrade.co.kr/
- Local KRX data (marcap, survivorship-free daily, 1995–2026) and E7-QC scripts and outputs — `/home/claude/data_raw/marcap/data/` ; `/home/claude/research_notes/QUANTGEN technical and fundamental signals/E7_quickchecks/` (e7_checks_part1_factors.py … part8.py; E7_*.csv; *_stdout.txt)
- Companion project docs (QUANTGEN macro research, 2 Oct 2026): `claude/QUANTGEN_macro_overlay_research_report.md`, `claude/QUANTGEN_MACRO_INTEGRATION.md`, `claude/QUANTGEN_MACRO_BACKLOG.md`

**Tier 2: professional services, asset managers, banks, think tanks, major press**
- KPMG Korea tax brief, Aug 2025 (securities transaction tax schedule; dividend separate taxation; large-shareholder threshold proposal) — https://assets.kpmg.com/content/dam/kpmgsites/kr/pdf/2025/tkc/tax-brief/korea-tax-brief-202508-eng_F.pdf.coredownload.inline.pdf
- PwC Worldwide Tax Summaries, Korea other taxes — https://taxsummaries.pwc.com/republic-of-korea/corporate/other-taxes
- EY, Korea enacts 2026 tax reform bill — https://taxnews.ey.com/news/2026-0126-korea-enacts-2026-tax-reform-bill
- KEIA (Randall S. Jones), "Explaining South Korea's Stock Market Boom", 22 Jul 2026 — https://keia.org/analysis/explaining-south-koreas-stock-market-boom/
- Glass Lewis, "Navigating South Korea's Corporate Value-Up Program", 30 Sep 2024 — https://www.glasslewis.com/article/navigating-south-koreas-corporate-value-up-program
- RISE (KB) Korea Value-Up ETF page (as of 2 Oct 2026) — https://eng.riseetf.co.kr/prod/finderDetail/44H7
- Goldman Sachs, "Korea's Stock Market Is Forecast to Set Fresh Highs", 21 May 2026 — https://www.goldmansachs.com/insights/articles/koreas-stock-market-is-forecast-to-set-fresh-highs
- Korea Times, Value-up index record (4 Feb 2026) — https://www.koreatimes.co.kr/economy/20260204/koreas-value-up-index-sets-new-record-last-month-krx ; September exports (1 Oct 2026) — https://www.koreatimes.co.kr/economy/20261001/koreas-monthly-exports-hit-1209-bil-in-sept-on-record-chip-sales
- Korea JoongAng Daily, KOSPI record close 9,114.55 (22 Jun 2026) — https://www.koreajoongangdaily.com/business/kospi-hits-fresh-record-over-9100-as-chip-stocks-rally/12734799
- Korea Herald, record −12.06% (4 Mar 2026) — https://www.koreaherald.com/article/10686893
- Seoul Economic Daily: chip duo > 50% (27 May 2026) — https://en.sedaily.com/finance/2026/05/27/samsung-sk-hynix-surge-alone-as-chip-duo-tops-half-of-kospi ; −9.99% (23 Jun 2026) — https://en.sedaily.com/markets/2026/06/23/kospi-plunges-10-percent-on-chip-concentration-leverage ; whipsaw and +17.91% (31 Jul 2026) — https://en.sedaily.com/finance/2026/07/31/kospi-whipsaws-18-percent-plunge-over-three-days-then-18 ; VI clustering — https://en.sedaily.com/finance/2026/05/07/kospi-volatility-interruptions-double-in-early-trading-hours
- KED Global, all listed stocks available for shorting (30 Mar 2025) — https://www.kedglobal.com/short-selling/newsView/ked202503300002
- Financial News (KCMI webinar, 13 Apr 2021) — https://www.fnnews.com/news/202104131912345956
- Seoul Shinmun: new investors' losses (13 Apr 2021) — https://www.seoul.co.kr/news/economy/2021/04/13/20210413500168 ; individual turnover and trading share, KCMI (26 May 2015) — https://www.seoul.co.kr/news/economy/securities/2015/05/26/20150526800049
- Yahoo Finance, KOSPI +100% (28 May 2026; context only) — https://finance.yahoo.com/markets/world-indices/articles/south-koreas-kospi-surges-100-121544935.html

**Tier 3: used for chronology only**
- Investment Monitor, end of short-selling ban (31 Mar 2025) — https://www.investmentmonitor.ai/news/end-of-korean-short-selling-ban-expected-to-attract-foreign-investors/

*No Wikipedia, Reddit, Medium, Investopedia, Naver blog or YouTube source was used as evidence. Search results that pointed to such sites were discarded.*
