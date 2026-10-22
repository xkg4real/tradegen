# R2 Executives' panel — chair's working notes (extraction file)

Chair persona: "Chair of the Executives' panel", fictional composite (former global head of markets risk and trading at a bulge-bracket bank). Not a real person; speaks for no real firm. As of 2026-10-02.
Purpose: compact extraction of E1-E7 (position, ledger, failures, recommendations) so the debate and verification can work from this file, returning to full text only for disputes.
Panel independence: P1-P7 papers NOT read (professors' panel chaired separately).

## 0. Fixed constraints (from 00_QUANTGEN_context.md and QUANTGEN_MACRO_INTEGRATION.md v1.2)
- Costs per side: KRX ETF 3 bp; KRX stock 35 bp (incl. sell tax); US via KIS 50 bp; crypto 10; futures 5; FX 10; all at 2x.
- Decide at close t, earn t+1. Nine-step gate; 60% live haircut reported.
- Macro decisions not to re-litigate: macro never generates direction; overlay multipliers in [0.5,1.0]; vol-target/vol-scale weights in [0,1.0] (no floor); 0x only from risk layer (backtest) or HALTED (sim book).
- P1 macro scales risk only; P2 bounds; P4 Korea risk inputs local; P5 PIT (available_at <= decision_utc), fail closed; P7 only PASS cards feed the displayed book; FORWARD-SIM never feeds it; P8 exposure basis declared; P10 costs never lowered, instrument book declared before run.
- R-03 momentum own-vol scaling sigma126, 12% target, cap 1.0 (US French Mom 0.399 -> 0.714 gross; 0.672 net 50bp). R-04 DM bear gate floor 0.5 (INSUFFICIENT DATA: 7 onsets).
- R-05 reversal and quality fixed 1.0x (never cut by macro, never up-weighted). Reversal card must clear 35 bp and stay positive at 70 bp.
- R-06 Korea VT20 (SMA20, target 20%, cap 1.0) CARD-P indicative INSUFFICIENT DATA; US VT15 REJECT at 50 bp.
- R-07 Korea caps: pair (Samsung+SK hynix) <= 0.35 of Korea long book when pair share of KOSPI > 0.45; semis <= 0.50 (judgment); single name <= 0.05 of NAV; drawdown ladder on sim NAV: -8% gross x0.5 (risk layer), -12% evaluator blocks new entries + overlay forced to 0.5, -15% HALTED, re-arm refused 10 sessions. Open points: whether ladder steps are cumulative; look-through for ETF line; 0.05 vs 0.35 interaction; 0-3 scale normalisation.
- R-14 TS-trend sleeve: 12-1 sign, monthly, per-asset weight min(1, 0.15/sigma12m); EXEMPT from overlay multipliers and market vol target; subject to risk-layer caps and ladder; CARD-O vs EW long-only basket. Per-index weights: KOSPI 1, KOSDAQ 0, US 3, Europe 0-1, Japan 1-2, Taiwan 1-2, China A 0, India 1, crypto 2.
- R-15 priors table (XS mom / ST rev / TS trend): Korea 12-1 0, 12-7/residual 1 (UNVERIFIED), ST-rev 3 (net-of-cost test at 35bp required), TS KOSPI 1 KOSDAQ 0. Prior haircuts value -49%, mom -23%, carry -25%, defensive 0, multifactor -18%.
- §8.7 CARD-P protective class: comparator S = same-average-exposure static book; PC-1 dMDD >= +3pp at 1x and 2x; PC-2 tail-exposure ratio <= 0.90; PC-3 Sharpe non-inferiority margin 0.10 (p <= 0.10); PC-4 >= 3 positive episodes, no episode > 50% of benefit; PC-5 years >= 60%; PC-6 plateau; PC-7 sufficiency (>= 30 de-clustered onsets / >= 5 episodes / >= 882 sessions). Applies only to rules whose output never exceeds 1.0.
- Prior design per-market weights (0-3): US XS-mom 3, ST-rev 1, value 1, quality 3, low-vol 2, flow 1, earnings drift 2, TS-mom 3. Korea 1/3/2/1/2/3/3/2.

## 0b. Data lab R1 results relevant to executives (KR_datalab_summary, US_datalab_summary)
KR (marcap 1996-03..2026-09, ALL universe, 35bp/side):
- REV 1W LS gross +19.9%/yr EW (Sharpe 0.99), turnover 159x, break-even 12.5 bp (EW)/22.2 bp (VW); net Sharpe -1.78 EW. Volume split does not rescue. -> prior Korea ST-rev weight 3 NOT supported at 35bp.
- REV 1M LS gross +11.2% (0.45), net35 -0.08. 1-month reversal 1999-2021 deciles +1.41%/mo gross (t 2.52), +0.20%/mo net; the brief's 2.95%/mo is ~2x lab value.
- MOM 12-1 LS gross +9.3% (0.45; 2016-26 0.12), net35 0.20; LO excess -1.3% EW (t -0.6); VW LO +1.6% (t 0.6). Momentum positive in every turnover tercile (high-turnover +1.44%/mo, t 3.41) -> brief's "negative in high-turnover stocks" NOT reproduced.
- Low-vol (VOL 3M) LS +18.7% (0.76) net 0.56; low MAX 1.12 gross; low TURN +23.1% (0.90) net 0.68. LO top quintiles within noise of universe; spreads come from short leg (worst quintile loses absolutely).
- Implementable: exclusion screens. Universe minus worst TURN quintile +3.6%/yr over EW net35 (t 5.63; 87% yrs +; +2.5% at 70bp); minus worst VOL quintile +3.0% (t 4.67). VW: +0.8%/+1.1% (t 2.86/2.83).
- SIZE LO +5.8% (t 2.94) fading: 2025 -26.9%, 2026 -26.5% (LS).
- RSI14/%B = repackaged 1M reversal (corr 0.92-0.95); negative net.
- KOSPI index timing (rebuilt VW KOSPI, 1996-06..2026-09, 3bp): B&H CAGR 7.2% Sharpe 0.39 MDD -67.1%; SMA200 8.1%/0.53/-41.5%; 10M SMA 9.1%/0.57/-43.7%; TSMOM 12M 7.5%/0.48/-38.8%. Mean excess vs B&H negative (SMA200 -1.1%/yr t -0.3). SPA over 303 variants consistent p 0.880. All gain from 1996-2005; 10M SMA 2006-15 -0.4% vs 3.7%. Trend fully invested into 2026-06-22..07-30 crash (SMA200 -37.9% vs -38.6%).
- 2026 episodes: melt-up (01-02..06-22) VW +104.9% vs EW +0.8%; Samsung/SK hynix 31% of VW universe, +195%/+349%. Crash (06-22..07-30) MOM LS -24.4%, low-vol +36.2%; rebound (07-31..09-29) low-vol -25.9%.
US (Shiller 1871-2026; SPY 1999-2021; French 1926-2018):
- SMA10 standard +1.52pp vs B&H is averaging artefact; lag1 -0.27pp; month-end CRSP -0.04pp; at 50bp lag1 -1.00pp. 2010-2026 all trend rules lost 1.7-5.2pp/yr.
- 322 daily technical variants: SPA p 0.82-0.97 (SPY). 0 of 322 beat SPY B&H mean after 2010.
- CAPE 10y in-sample R2 0.29 (1881-2013 starts), OOS R2 1990-2013 -0.25 (log CAPE); 1y IS R2 0.05; OOS negative after 1990. CAPE de-risk rule (cash > p90) -1.8pp/yr (1891-2023), -4.5pp/yr (1990-2023).
- SML flat: FM slope +0.46%/yr (t 0.17) vs 7.2% premium; low-beta Sharpe 0.65 vs 0.41.
- HML 1926-2018 Sharpe 0.37; HML from 2007 cum -29.8%; Mom 1949-2017 Sharpe 0.62; 2009 -49.3% (Mar-May); HML-Mom corr -0.18; 50/50 Sharpe 0.84 (1949-2017), -0.19 (2008-17).
- Factor ETFs 1y to 2026-10-01 (Stocklake): SPY +15.2%, MTUM +26.0%, QUAL +14.9%, USMV +4.4%, IWM +15.9%.

---

## E1 — Bank quant & derivatives strategy research (Global Head, bulge-bracket style; fictional)
Lens: separates construction advice from sales numbers; haircuts headline backtests.
Position:
1. Bank/AM research good for construction (definitions, risk scaling, combining), unreliable for headline Sharpe (IS, gross/net unlabelled, decays).
2. JPM 2015 TSMOM Sharpe 1.21 (1992-2014 backtest) = ceiling; live trend ~3%/yr over T-bills net (AQMIX 10y); QUANTGEN B3 0.08 OOS.
3. Valuation: 1y R2 5-8% (JPM GTM fwd P/E); GTM 5y R2 44% (Sep-2020) -> 28% (Mar-2026). Shiller: CAPE keeps ranking OOS, level wrong after 1990.
4. Long-only smart beta post-2016 (10y to 30-Jun-2026, net): MTUM +2.1pp/yr vs S&P; QUAL -1.0; USMV -5.9; all four lagged IVV cumulatively 2021-25.
5. Crowding (GS prime) = risk monitor, not timing; record Nov-2023 followed by more outperformance; unwinds Jan-2026, Jun-Jul 2026 (MTUM -18% vs SPY -2% in 5 weeks).
6. AI/big data: AIEQ 4.2%/yr vs SPY 12.7% (5y).
7. Do: copy definitions (multi-measure industry-neutral value; quality composites; risk-adjusted momentum with crash controls; buy/hold bands). Crowding & valuation = sizing context in [0.5,1.0]. Drop factor-ETF rotation, valuation timing, ML. Haircut any bank/AM backtest by >= 50-60% (multiply by 0.4-0.5) then subtract 2 x cost x turnover.
Claims ledger E1-C01..C28 (28 rows):
- C01 JPM 12m TSMOM all-asset Sharpe 1.21 (1992-2014 IS); XS 0.44; enhanced 0.82; EMV 0.78. CONTEXT/DROP as alpha prior; live prior 0.3-0.4.
- C02 6-12m lookbacks beat 1m (equity 0.82 vs 0.33 etc). BUILD design rule (never 1m trend).
- C03 Cash = 4.1 of 7.4%/yr CTA return 1994-2010; -1.9%/yr 2011-13. BUILD accounting (excess-of-cash).
- C04 AQR: 2010s trend weakness = fewer big moves. BACKLOG re-test B3.
- C05 AQMIX 10y 5.44% vs T-bill 2.42% (to 30-Sep-2026); since Jan-2010 4.54% vs 1.48%. PRIOR ~3%/yr net (Sharpe ~0.3 if 10% vol, vol unverified).
- C06 [calc Shiller] S&P 12m long/flat: R/V 1.32 vs 0.81 (1992-2014); 1.02 vs 1.16 (2015-Sep 2026); return 10.9% vs 13.8%; MDD -18.9% vs -19.3%. Gross, no cash, monthly averages. DROP as alpha; CONTEXT overlay <= 1.0.
- C07 JPM GTM fwd P/E 1y R2 8%/7%/5%; 5y 44%->29%->28%. DROP 1y timing.
- C08 [calc Shiller] CAPE full-history R2 0.05/0.16/0.29 (1y/5y/10y); post-1990 10y 0.86 IS; OOS R2 -0.54 (10y), corr +0.93; Jun-2013 forecast 2.9%/yr real vs 9.5% realized. CONTEXT.
- C09 BofA normalized P/E ~80% of 10y returns (interview). CONTEXT.
- C10 BofA Sell Side Indicator. BACKLOG (proprietary).
- C11 [calc Shiller] CAPE>30: 102 months through Sep-2023: mean fwd 1y price +3.0%, 58% positive vs 6.7%/65% unconditional; S&P +208% Sep-2017 -> Sep-2026. DROP timing.
- C12 GS crowding record Nov-2023 (70% of longs in top-10; VIP +31% vs S&P +19% YTD). T2 press summary. CONTEXT.
- C13 Jan-2026 GS systematic L/S ~-1% in 10 days; UBS quant -2.8%; Jul-2026 momentum -3%+ two weeks; GS -2.1%/-3.1%. T2 trade press. BUILD vol scaling+bear gate; factor-vol trigger (DC5).
- C14 [calc Stocklake] MTUM -18.0% vs SPY -2.0% (22-Jun..29-Jul-2026); SPHB -14.1%; USMV +4.3%. BUILD: report worst-5-week relative loss.
- C15 AQR 2014: UMD 8.3%/yr Sharpe 0.50 (1927-2013); large-cap 0.24 (1991-2013); corr with HML -0.4. PRIOR large-cap L/S mom 0.25 gross.
- C16 D&M NBER w20439: dynamic momentum Sharpe 1.18 vs ~0.3 static ("roughly quadruples") 1927-2013 IS. BUILD (already decided). [CHECK vs macro corrected anchor: JFE T7 0.682 -> 1.041 -> 1.194; WML 0.71 in Table 1]
- C17 AQR Craftsmanship: multi-measure industry-neutral value Sharpe 0.26 vs 0.07 since 1990; impact 17bp at 2% ADV / 28bp at 6%. BUILD-candidate KRX via OpenDART PIT.
- C18 AQR May-2020 value spread 100th pct; VLUE +3.4 pts/yr vs IVV (Jul-2021..Jun-2026), -12.0 (2023), -17.8 (2024). CONTEXT.
- C19 Research Affiliates 2016 valuation-adjusted factor returns; USMV -5.9, QUAL -1.0 vs IVV 10y. BUILD (reporting valuation-adjusted).
- C20 iShares 10y to Jun-2026 excess vs IVV: MTUM +2.1, QUAL -1.0, VLUE -0.0, USMV -5.9 pts/yr; cum 2021-25 +64/+82/+80/+50% vs IVV +96%. DROP factor-ETF rotation; prior long-only tilt 0 +/- 2%/yr.
- C21 VLUE Micron 24.46%, IT 41.75%; MTUM IT 54.3%, P/E 46.1x (30-Jun-2026). BUILD single-name cap 5%, sector bands.
- C22 SPIVA: US large-cap 78.78% (2025), 85.59% (10y), 92.89% (20y) lag; survival 34.61%. CONTEXT base rate.
- C23 JPM 2017 alt data small Sharpe; AIEQ 5y 4.18% vs SPY 12.65%. DROP.
- C24 GKX: ML gains concentrated in hard-to-arbitrage stocks. BACKLOG.
- C25 HXZ 64% of 447 anomalies insignificant; McLean-Pontiff ~50% post-pub decay. PRIOR 60% haircut.
- C26 Novy-Marx-Velikov: >50% monthly turnover rarely survives; buy/hold bands. BUILD bands on every stock card.
- C27 Man: vol targeting improves equities/credit Sharpe. CONTEXT (partial conflict with macro "momentum only").
- C28 GS: HF alpha record 2025; Jul-2026 drawdown followed. CONTEXT.
Failures (E1 KQ3): 1932 (losers +232%), Mar-May 2009 (losers +163%); MTUM vs IVV 2021 -15.2, 2023 -17.2 pts; Jun-Jul 2026 MTUM -16.3 relative; trend droughts (CTAs -1.9%/yr 2011-13; S&P 12m long/flat 10.9% vs 13.8% 2015-2026); value 1Q2020 worst since 1963; VLUE -12.0 (2023), -17.8 (2024), +14.8 (2025); QUAL 2022 -20.39% vs IVV -18.13%; USMV lagged 16.1/9.2/10.2 pts 2023-25; CAPE>30 since Sep-2017 -> S&P +208%; GTM Sep-2020 fwd P/E 21.5x -> S&P +32.1% next 12m; AIEQ. T3 item: Artificial Finance blog says GS high-beta momentum basket -37% Jul-2026 (unverified).
Recommendations / cards: F1 multi-measure value (KRX OpenDART PIT -> US) prior L/S 0.26 -> x0.51 -> x0.4 ≈ 0.05-0.10; F2 quality composite (lower US long-only quality 3 -> 2); F3 risk-adj momentum + crash controls (US/Europe BUILD-cand; KRX BACKLOG); F4 composite equal-risk (preferred); C1 crowding monitor BACKLOG (DC5); C2 valuation CONTEXT; T1 vol-targeted trend CONTEXT (drawdown multiplier <= 1.0); X1 factor-ETF rotation DROP; X2 ML DROP; X3 dual momentum BACKLOG. Momentum crash budget: 15-20 pt relative loss in 5-6 weeks every 2-3 years (long-only US).
Conflicts flagged by E1: US TS-mom 3 -> "3 as risk overlay, 1 as alpha"; US quality 3 -> 2 long-only; US low-vol 2 only if DC9 shows alpha net of beta; vol scaling (Man) vs "momentum only".
DCs: DC1 valuation R2 decay; DC2 CAPE>p80 -> 0.5 overlay; DC3 month-end trend; DC4 KRX bank-style momentum top-200 with bands, vol scaling, bear gate; DC5 KRX comomentum + factor-vol trigger; DC6 KRX low-vol top-200; DC7 French UMD subperiods; DC8 VIX->momentum crash; DC9 ETF alphas.
Key numbers to re-check: C06, C08, C11 (Shiller recompute); C16 (D&M "1.18 vs ~0.3"); C14 (Stocklake); C05 (AQMIX URL); C20 (iShares); C13 (Hedgeweek T2 trade press); T3 blog item.

---

## E2 — NYSE floor specialist/DMM -> Head of Electronic Trading (fictional)
Lens: cost first, signal second (spread/tick, tax, impact, honest fills).
Position:
1. Intraday edges real but tiny: SPY intraday momentum ~2.6 bp/trade-day gross (1993-2013); E-mini overnight drift 1.48 bp/day (1998-2020); QQQ ORB ~7c/share gross, break-even ~2.2c slippage.
2. QUANTGEN costs 25-50x larger. KRX round-trip floor 25-45 bp (0.20% sell tax 2026 + one tick 5-25 bp). No intraday rule BUILD; DROP market intraday momentum, ORB, VWAP-cross, gap-and-go, S/R bounces.
3. QUANTGEN cannot test intraday honestly (read-only; needs 882 recorded sessions >= 3.5 years).
4. What survives is slow: one-sided monthly turnover < ~50%. US 1M reversal +0.37%/mo gross -> -1.28%/mo net (1963-2012).
5. S/R = order flow; Osler 60.8% vs 56.2% hit rate.
6. Closing auction is the venue/price convention: US closing auctions ~9-9.4% of consolidated notional (2024); close prices carry 8.1 bp avg abs auction pressure reverting overnight -> close-to-close reversal must be tested with one-day skip.
7. QUANTGEN should: report two fill conventions (close t; close t+1 bound); tick-based spread floor + sqrt impact term; never fill stops at the stop price; flag KRX limit/VI/overheating days unfillable; KRX official closes only (no Nextrade/after-market); reversal cards need skip-day, liquidity filter, buy/hold band before BACKLOG.
8. Conflict: Korea ST-reversal weight 3 -> 1-2 until DC-E2-02/03 pass.
Claims ledger E2-C01..C30 (30 rows):
- C01 Gao-Han-Li-Zhou SPY first->last half hour: R2 1.6% IS/1.4% OOS; Sharpe 1.08 gross; 6.67%/yr -> 4.46% after spread. DROP (break-even ~1.3bp/side).
- C02 Korea intraday momentum weak (KOSEF 200 2008-21 coef 2.06 p 0.084). DROP.
- C03 Baltussen et al.: intraday momentum from short-gamma hedging, reverses. CONTEXT.
- C04 End-of-day reversal 3.45 bp/day VW (1993-2019). DROP.
- C05 Half-hour periodicity 3.01 bp, not net profitable. DROP.
- C06 Lou-Polk-Skouras: momentum 0.98%/mo overnight (t 3.84) vs -0.02% intraday; ROE -0.95% overnight vs +1.42% intraday. BUILD-design: fill momentum at close; DC-E2-01.
- C07 FRBNY SR917: E-mini overnight 1.48 bp/day; Sharpe 1.1 gross -> -0.5 net. DROP.
- C08 Kelly-Clark QQQQ 1999-2006 close-to-open +23.7%/yr vs open-to-close -23.3%. DROP.
- C09 QQQ 5-min ORB (Concretum; GitHub replication): break-even ~2.2c/share; Sharpe 0.23 at 2c; 76% of filtered P&L in 2022. T3. DROP.
- C10 ORB stocks-in-play Sharpe 2.81 (no slippage, 4x lev). DROP.
- C11 MQL5 blog: ORB CFDs 2015-2026 gross 0.13R -> net ~0. T3. DROP.
- C12 sqrt impact Y*sigma*sqrt(Q/V), Y~1. BUILD cost model: impact term + 1% ADV cap.
- C13 Frazzini-Israel-Moskowitz: institutional costs ~10x below academic; reversal fails at scale. CONTEXT.
- C14 Novy-Marx-Velikov: reversal turnover 90.87%/mo; gross 0.37%/mo (t 1.71) -> net -1.28% (t -6.02); banded -0.72%. BUILD gate rule turnover <= 50%/mo + break-even screen.
- C15 Nagel 2012: reversal = liquidity provision, peaks with VIX. BACKLOG VIX-conditioned weekly reversal (DC-E2-09); keep 1.0x.
- C16 Closing auctions 3.1% (2010) -> 7.5% (2018) of volume; ~9-9.44% notional 2024; NYSE-listed 10.5-14.2%; >34% Russell day; NYSE Q1-2026 605.5m sh/day; record 3.57bn 20-Mar-2026. BUILD close-auction fill convention.
- C17 Bogousslavsky-Muravyev: close deviation 8.1 bp avg abs; >63bp in 1%; reverses overnight. BUILD skip-day/t+1 variants.
- C18 Osler: S/R published levels 60.8% vs 56.2%. CONTEXT.
- C19 Bhattacharya-Holden-Jacobsen round numbers ~$1bn/yr retail losses. BACKLOG DC-E2-05.
- C20 Stops fill far away: 6 May 2010 >20,000 trades >60% away; 24 Aug 2015 SPY open -5.2%, IVV -20%+, JPM -13.3% in 65s. BUILD fill rule: next available price; no fill while limit-locked.
- C21 Taiwan day traders net negative 15/15 years; <1% profitable. CONTEXT.
- C22 Brazil 97% lost. CONTEXT.
- C23 KCMI: Korea 2020 new retail net -1.2% vs existing +15.0%; 55.4% intraday; costs -4.0 pts; turnover ~1,600%/yr. CONTEXT.
- C24 Robinhood mixed; round-trip -0.07% to -0.46%. CONTEXT (50 bp US stress plausible).
- C25 KRX VI 3%/6% (2%/4% close), static 10%, 2-min call; +/-30% since 15-Jun-2015; closing call 15:20-15:30 random end <= 30s; overheating 3-day periodic call. BUILD data hygiene: unfillable-day flags.
- C26 KRX ticks 0.05-0.25% of price; sell tax 0.18% (2024), 0.15% (2025), 0.20% (2026). Round-trip floor 25-45 bp. BUILD tick-band spread floor; 35bp adequate for liquid names only (DC-E2-06).
- C27 Nextrade (Mar 2025): 800->630->610 stocks; share 10.64% -> 9.10%. BUILD data hygiene: KRX official close only (DC-E2-10).
- C28 US half-penny tick Nov 2025. CONTEXT regime flag.
- C29 Zhang-Hua: US intraday predictors decayed 2007-18. CONTEXT.
- C30 Break-even per-side cost = gross annual return / (2 x annual turnover); reject pre-gate if < 2x pre-registered cost. BUILD card header + pre-gate screen.
Failures: 6 May 2010; 24 Aug 2015 (1,278 LULD halts); GME Jan 2021; 5 Aug 2024 (TOPIX -12%); US 1M reversal net -1.28%/mo; ORB replication; Taiwan/Brazil/Korea retail; Nextrade removals; QUANTGEN E8 bounce.
Recommendations (B list): two fill conventions; skip-day variants; unfillable-day rules (no entry/exit at limit-locked close; VI/overheating flags; no change during halts); liquidity & tick screens (top N by 20d median trading value; half-tick min half-spread; exclude tick > 0.25% of price or charge more); turnover discipline (hold >= 5 sessions; band enter top decile exit below top 3 deciles; <= 50% one-sided/month); exits at close, stops fill at worse of stop and next open, no fill while locked; momentum entries at close; KRX official close only. Card header fields: decision timestamp; fill convention; itemised cost (commission, time-varying sell tax, tick/2 floor, impact Y*sigma_d*sqrt(Q/ADV20), 2x); turnover & break-even (reject pre-gate if break-even < 2x pre-registered cost); capacity <= 1% of 20d ADV; latency class; fill rules (trade-through, not touch); regime flags.
Arithmetic claims: daily reversal 100% daily turnover cost 2x35bpx252 ≈ 176%/yr; weekly ≈ 36%/yr; monthly 90% turnover ≈ 0.63%/mo.
DCs: DC-E2-01 overnight/intraday split KRX; -02 net ST reversal KRX (pass: net Sharpe > 0 at 70bp in liquid universe); -03 skip-day; -04 limit-hit; -05 round numbers; -06 tick floor; -07 gap fade; -08 stop gap-through; -09 VIX-conditioned reversal; -10 close-source integrity; -11 close-pressure proxy; -12 SPY overnight hold cost kill.
Key numbers to re-check: arithmetic (176%/yr; 36%/yr), 25-45 bp floor (tick table + tax), C14 NMV numbers, C26 tax schedule, DC-E2-02 vs lab (REV 1W break-even 12.5/22.2 bp). Can compute DC-E2-01 (overnight split) and DC-E2-04 (limit hits) and DC-E2-08 (stop gap-through) on marcap if OHLC available.

---

## E3 — CIO systematic managed futures, ex-commodities trader (fictional)
Lens: implementation; distrusts single-asset backtests and diversifier-vs-long-only benchmarks.
Position:
- TSMOM well documented (AQR sim net Sharpe 0.77 1880-2013; 58/58 futures positive 1985-2009) but industry record weaker: net CTA Sharpe ~0.5-0.6 2000-2022; 2009-2025 annual mean/SD ~0.30; Barclay Systematic 2009-18 CAGR -0.30%.
- B3 REJECT replicates industry post-2009; power too low (17y; SE 0.24); wrong benchmark (long-only 0.58).
- C3 passed: crypto 1-4 week autocorrelation; vol large vs 10 bp; -75/-85% bears sidestepped. Edge = timing not vol scaling; shrank 2022-26; negative 2025.
- Single equity index trend = protective tool: SPY (1999-2021) and KOSPI proxy (1996-2026) multi-speed long/flat cut MDD ~13-17 pp vs same-exposure static S, Sharpe ~unchanged. Lost in 2009-2019; did NOT protect in 22 Jun-30 Jul 2026 KOSPI crash; VT20 did.
- BUILD: "trend x VT20" CARD-P per index; diversified futures re-registered (>= 25 markets, multi-speed, per-asset vol, diversifier claim vs cash + portfolio uplift).
- DROP Shiller monthly-average trend evidence (inflates trend Sharpe ~0.15-0.25). Step 8 (>= 60% years) would reject net CTA industry 2009-2025 (9/17).
Key E3 checks (in-sample, price-only, 5 bp equity per side; ~40 configs tried):
- SPY 200d L/F 1999-2021: Sharpe 0.38 vs 0.40; MDD -30.0% vs -56.5%; S (exp 0.72) -43.8%; 7.4 switches/yr. 2009-19 0.57 vs 0.79. 2020: 19 Feb-23 Mar -17.6% vs -34.1%; 19 Feb-31 Dec -1.4% vs +10.5%.
- SPY ens x VT20: Sharpe 0.41 vs S 0.37; MDD -27.3% vs S -41.3% (PC-1 +14.1); tail ratio 0.51; 6/6 episodes (largest 45%); 61% yrs +.
- Mechanism: 200d exposure 0.75 on VIX +20% days vs 0.71 avg -> no de-risk on spike day 1.
- KOSPI proxy 1996-2026 5bp: B&H Sharpe 0.41, MDD -69.8%; ens L/F 0.60, -35.3% (S -48.1%), 12.1 turns/yr, tail 0.77; 200d L/F 0.54, -42.8%; ens L/S 0.42, -60.1%; 250d L/S 0.24, -74.3%; 2x cost ens L/F 0.56.
- KOSPI subperiods ens L/F vs B&H: 1996-2008 0.72 vs 0.26; 2009-2019 0.23 vs 0.49 (200d 0.08; L/S -0.33); 2020-2026 0.77 vs 0.76. vs S: 2001-2026 dSharpe +0.04; 2013-2026 +0.01 with PC-1 -3.4 pp (!).
- KOSPI episodes B&H / ens L/F / ens L/S / ens x VS15: 22 Jun-30 Jul 2026 -38.4 / -31.2 / -23.4 / -7.9 (episode table) [elsewhere B&H -38.0, ens L/F -30.7, 200d -37.2, VT20 -12.0, ens x VT20 -9.5].
- KOSPI trend vs VT20: 2008 -40.9/-7.0/-31.2/-6.4; 2022 -25.0/-5.9/-25.0/-5.9; H1-2026 +101.1/+84.2/+51.5/+47.2. ens x VT20 1996-2026 Sharpe 0.65 vs S 0.41; MDD -26.7% vs S -43.9%; 8/8 episodes (largest 31%); 2009-19 0.24 vs S 0.49; 53-55% yrs + (B&H 69%) -> fails PC-5.
- KOSPI grid 20 cells: dSharpe vs S +0.04..+0.26; PC-1 +6.5..+17.3 pp; all negative 2009-19 (-0.16..-0.42); 2013-26 -0.06..+0.20; years + 45-62%.
- Long/half (floor 0.5): KOSPI 0.5+0.5*votes PC-1 +12.5, tail 0.92 (fails PC-2); KOSPI long/half x VT20 floor 0.5: PC-1 +8.1, tail 0.79, 8/8 (largest 19%), 63% yrs; SPY long/half PC-1 +11.2, 65%.
- Shiller bias: SPY 1998-2021 monthly AC 0.057 (month-end) vs 0.206 (avg); 12m L/S Sharpe 0.35 vs 0.62; 10m SMA 0.70 vs 0.82; Shiller 1872-2026 skip cuts 12m L/S 0.50->0.30, 10m SMA 0.75->0.59.
- Crypto (Coin Metrics) BTC 2017-10..2026-05: C3-like 1.19 vs B&H 0.83 vs vol-scaled LO 0.83; 2022-26 0.61 vs 0.48; 2025 -11% vs -6%.
Claims ledger E3-C01..C30 (30 rows) — key ones:
- C01 HOP 1880-2013 net 11.2%, Sharpe ~0.77 (CONTEXT). C02 MOP 58/58 (CONTEXT). C03 Trends Everywhere single asset 0.34-0.39 vs 1.17-1.60 diversified -> BUILD single-index cards must not claim alpha. C04 HLWZ fragility. C05 KTW vol scaling drives alpha -> BUILD vol-scaled LO control on every trend card. C06 MA=TSMOM one family -> count trials. C07 BK continuous signals cut turnover 36%. C08 2009-13 drought. C09 Barclay Systematic 2000-08 6.98% (9/9) vs 2009-18 -0.30% (3/10); 2009-25 mean/SD 0.30, 9/17 yrs. C10 2022 SG CTA +20.1%, SG Trend +27.3%. C11 2023-25 lean (T3/T2). C12 Apr-2025 SG Trend rolling 12m -18.6% worst. C13 2026 YTD SG Trend +15.85% (estimates). C14 dispersion. C15 HOP fees/costs remove half Sharpe. C16 live net 0.5-0.6. C17 short trends decayed. C18 crisis alpha slow vs fast. C19 SPY (E3 check) BUILD-candidate re-gate E1 as CARD-P. C20 KOSPI ens L/F vs S (E3 check) BUILD-cand CARD-P, never CARD-O. C21 trend vs VT20 different crash types -> trend x VT20 CARD-P on KOSPI200/KODEX 200. C22 plateau. C23 long/half floor 0.5 keeps ~half protection; flag P2 signal-vs-overlay question. C24 crypto momentum (LT/LTW). C25 crypto edge = timing. C26 Shiller averaging inflates trend -> DROP Shiller-average trend Sharpe. C27 B3 power. C28 Kaminski-Lo: stop-losses help only with serial correlation; in trend systems the signal exit IS the stop -> DROP separate stop layers on trend cards (double counting). C29 carry BACKLOG. C30 capacity not binding.
Conflicts flagged by E3 vs macro: (1) R-14 12-1 monthly sign is slowest/weakest cell -> multi-speed daily with band; (2) R-14 as CARD-O vs long-only basket repeats E1 -> CARD-P single index, diversifier claim multi-asset; (3) P2: if trend is an overlay, bound [0.5,1.0] gives ~half protection (PC-1 +8.1 vs +17.3); E3 reads trend as a SIGNAL family so 0 allowed — asks coordinator to classify; (4) prior "0.4-0.8 per asset" -> 0.3-0.4 gross per asset; diversified 0.3-0.6 live net; (5) vol scaling adds little Sharpe alone (KOSPI VT20 LO 0.40 vs S 0.41).
Per-market TS trend weights (alpha / protection): US 1/3; KOSPI 1/2; KOSDAQ 0/1; Japan 1/2 (untested); Europe 0-1/1-2; crypto 2-3/2; FX 0-1/1; rates 1-2/2; commodities 1-2/2; diversified 1-2/3.
Cards: T-K1 KOSPI200 trend x VT20 CARD-P (P&L on KOSPI200 future or KODEX 200; long/half cell pre-registered); T-US1/JP1/EU1; T-F1 diversified futures (>= 25 markets; INSUFFICIENT DATA/REVISE base case); C3 keep with controls.
DCs: DC-1 B3 diagnostics; DC-2 re-gate E1 as CARD-P; DC-3 KOSPI trend x VT20 walk-forward; DC-4 Shiller bias; DC-5 C3 controls; DC-6 VIX conditioning; DC-7 KOSDAQ; DC-8 positive years; DC-9 French month-end trend; DC-10 KOSPI200 futures roll; DC-11 grid plateau OOS.
Key numbers to re-check: KOSPI ens L/F vs S (0.60 vs 0.41; -35.3 vs -48.1); trend x VT20 (0.65, -26.7 vs -43.9; 53-55% yrs); crash window (-38.0/-30.7/-12.0/-9.5); 2009-19 subperiod; Shiller 12m L/S 0.50->0.30; SPY AC 0.057 vs 0.206; SPY 200d -30.0 vs -56.5; 2013-2026 PC-1 -3.4 pp.

---

## E4 — Ex-Head of US Equity Research (BofA/Merrill-style broker), then fundamental L/S PM (fictional)
Lens: can an individual compute it PIT from public filings; survives 35/50 bp at 2x; clears benchmark-relative gate.
Position:
1. Best fundamental signals: profitability (GP/A), net share issuance/payout, value (only as low-weight partner). Own calc French: HML Sharpe 0.60 (1963-2006) vs -0.17 (2007-2017/03).
2. Earnings momentum explains most price momentum (Novy-Marx 2015: SUE net Sharpe 0.55 vs UMD 0.33, 1975-2012). Large-cap US PEAD ~0 since ~2006; costs ~46 bp/mo -> NO standalone US PEAD card. Korea earnings drift weight 3: NO Korean evidence found -> test with DART timestamps first.
3. Sell-side: use changes not levels; rec levels fail net, inverted 2000-01; targets +28% above price, 38% met; high-LTG 3%/yr vs low 15%. No PIT consensus history -> start archiving KIS/FMP snapshots now.
4. Opportunistic insider buys (Cohen-Malloy-Pomorski) VW 82 bp/mo (1986-2007), Form 4 2 business days -> overlay not factor. Short interest = filter on longs. 13F cloning not alpha (GURU lagged ~3 pp/yr over 10y).
5. CANSLIM/IBD, Minervini SEPA/VCP: no independent OOS test; FFTY 3.5%/yr since Apr 2015 vs 13-14% S&P -> T3 descriptions.
6. Fundamentals+technicals: momentum as diversifying sleeve/confirmation (AMP US 50/50 0.63 vs 0.29/0.33, 1972-2011); bear-state protection for earnings-momentum sleeves (SUE crashed spring 2009).
7. Long-only quality not a crash hedge: QUAL -34.1% vs S&P -33.9% (19 Feb-23 Mar 2020); MSCI USA quality -20.3% vs -18.1% (2022).
8. Concentration: US top-10 ~41% end-2025 (vs ~19% end-2015); Korea Samsung+SK hynix 50.8% of KOSPI cap (29-Sep-2026); median KOSPI stock -5.9% YTD vs cap-weighted +64%.
9. Build PIT fundamental layer keyed to filing timestamps (DART rcept_dt; EDGAR/Form 4 dates); small pre-registered composite (profitability, issuance, value + earnings momentum tested in Korea first); filters (F-score in cheap bucket, extreme accruals, high DTC, recent downgrades, highest LTG); long-only tilts vs concentration-capped benchmark. Backtest IR 0.3-0.5 net 1x; live 0.12-0.2.
10. Power: IR 0.3 needs ~18 years at one-sided p <= 0.10; DART API from 2015 -> min detectable IR ~0.41 (10y) / ~0.48 (7y OOS). Expect REVISE/INSUFFICIENT DATA.
Own calcs (French linearmodels 1949-2017/03): HML % / Sharpe: 1949-89 5.12/0.61; 1990-2006 5.34/0.49; 2007-2017/03 -1.59/-0.17; 1963-2006 5.87/0.60. UMD 9.94/0.92; 9.94/0.61; -0.49/-0.03; 9.80/0.71. 50/50: 1.21; 0.80; -0.13; 0.99. corr -0.18; -0.06; -0.44; -0.12. HML cum -18.9% Jan-2007..Mar-2017; MDD -27.5% by Jul-2015; 2007 HML -13.7%, UMD +22.8%; 2009 UMD -52.6%; 2015 HML -9.7%; 2016 HML +21.1%, UMD -17.5%. Mar-2000..Dec-2002 HML +95.7%, UMD +11.1%, mkt -37.3%. Financials Oct-2007..Feb-2009 -69.5% vs mkt -49.3%; HML -19.6%; UMD +36.1%. UMD Mar-May 2009 -11.5/-34.6/-12.3 = -49.3%.
Own calcs (marcap KOSPI): Samsung/SK hynix/both/top-10 % of KOSPI cap: 2007-12-28 8.6/1.3/9.9/32.1; 2012 19.4/1.5/21.0/39.1; 2020 24.4/4.4/28.8/48.4; 2024 16.2/6.4/22.6/41.7; 2025-12-30 20.4/13.6/34.0/48.3; 2026-09-29 28.1/22.7/50.8/64.3. Cap-weighted vs median: 2023 +18.8/-1.4 (pair +10.6pp); 2024 -9.8/-13.3 (-6.0pp); 2025 +78.0/+12.7 (+38.1pp); 2026 YTD (30-Dec-2025..29-Sep-2026) +64.1/-5.9 (+49.4pp); 11.7% of 939 stocks beat; Samsung +127.3%, SK hynix +171.1%.
Own calc (skfolio ETF data, T3): COVID QUAL -34.1 vs S&P -33.9; Q4-2018 QUAL -20.3 vs -19.8; 2022 to 12-Oct QUAL -27.5 vs -24.9; QUAL beta 0.99, USMV 0.78. Stocklake (T3) 25 Feb-30 Mar 2026 QUAL -9.0 vs SPY -8.6. VIX: 80.9 (20-Nov-2008), 82.7 (16-Mar-2020), 15.27 (19-Feb-2025) -> 52.33 (8-Apr-2025), 31.1 (27-Mar-2026).
Data/PIT table: DART fnlttSinglAcntAll from bsns_year 2015 (verified); rcept_dt from list API; FMP filing dates; EDGAR 10-Q 40/45d, 10-K 60/75/90d; Form 4 2 business days; 13F +45 days; KR short series broken 6-Nov-2023..30-Mar-2025; KIS estimate/opinion endpoints exist, depth unknown.
Cost arithmetic: annual cost = 2 x one-sided monthly turnover x 12 x cost. Fundamental 4%/mo: KRX 0.34%/0.67%; US 0.48/0.96. Insider 10%/mo: 0.84/1.68; 1.20/2.40. Revisions 25%/mo: 2.10/4.20; 3.00/6.00. SUE 35%/mo: 2.94/5.88; 4.20/8.40.
Power table (t ≈ IR*sqrt(years); one-sided p<=0.10 t>=1.28): IR 0.2 41y; 0.3 18y; 0.4 10y; 0.5 6.6y.
Ranked features: 1 GP/A (BUILD-cand composite core); 2 net issuance (BUILD-cand, testable now on marcap Stocks, DC-1); 3 value composite (low weight); 4 event earnings momentum (KR BACKLOG pending DC-2; US DROP standalone); 5 opportunistic insider buys (US BUILD-cand overlay; KR BACKLOG); 6 F-score floor (filter); 7 extreme accruals (filter); 8 high DTC (risk screen, BACKLOG KR); 9 revisions (BACKLOG archive); 10 announcement premium BACKLOG; 11 high-LTG exclusion BACKLOG; 12 13F breadth BACKLOG, cloning DROP; 13 rec level/target upside DROP; 14 CANSLIM/SEPA/VCP DROP; 15 aggregate short interest CONTEXT; 16 guidance withdrawal CONTEXT/BACKLOG.
F1 fundamental composite card: z of GP/A + issuance + value (+ KR earnings momentum if DC-2 passes); sector- and size-tercile-neutral; filters 6-8; long-only top 20-30% of liquid universe (KR KOSPI200+KOSDAQ150 or top 300; US S&P 500); 5-10% single-name cap; concentration-capped benchmark pre-registered; monthly with 20%/30% band; 35/50 bp, 2x. Expect REVISE on DART-only history.
Weight corrections: US value 1->1; quality 3->2; earnings drift 2->1; new issuance 2; new insider 1. Korea value 2->2 (regime test Value-up 2024); quality 1->1 pending DC-8; earnings drift 3->2 pending DC-2/DC-3; issuance 2 pending DC-1; insider 0.
Conflicts flagged: (1) DM bear gate should also cover earnings-momentum/revision sleeves; (2) aggregate short interest is direction evidence but macro only allows [0.5,1.0]; (3) quality must not be counted as a hedge in any risk budget.
Failures: Aug-2007 quant unwind (HML -13.7% in 2007); Oct-2007..Feb-2009 financials value trap; Mar-May 2009 junk rally; 2000-01 sell-side recs (top -7.06%/yr vs bottom +13.44%); 2007-2020 value lost decade; 2016 UMD -17.5%; COVID quality; GME; 2022; 2023-25 AI concentration; 2025 tariff (unmeasured); 2026 Q1 US drawdown; KR concentration 2024/2026; KR short-sale bans; FFTY; GURU.
Claims ledger E4-C01..C30 — key: C01 Novy-Marx earnings momentum; C02 PEAD ~0 large caps since 2006 (DROP US standalone); C04 PEAD net 0.26%/mo (t 1.60) -> DROP US; KR only if gross drift > ~3%/yr; C11 insider 82 bp/mo VW (BUILD-cand US overlay); C12 buys only; C13 aggregate SI OOS R2 1.94-13.24% (CONTEXT); C14 DTC filter; C16 13F cloning DROP; C17 GP/A BUILD-cand core; C18 QMJ robust but QUAL not hedge; C19 HML split; C20 value rebounds; C21 val+mom combo failed after 2007 (own calc -0.13); C22 F-score filter; C23 decay meta; C24 anomaly payoffs on news days -> refresh on filing timestamps; C25 concentration; C26 CANSLIM DROP; C27 VCP DROP (send to technical panel); C28 extend DM gate to SUE; C29 PIT layer BUILD; C30 KR regulation regime breaks.
DCs: DC-1 KR net issuance (marcap Stocks); DC-2 KR earnings drift (OpenDART); DC-3 KR info-event drift proxy (vol >= 4x 60d avg & |abn ret| >= 3 sigma); DC-4 KR concentration/benchmark; DC-5 French value/mom stability; DC-6 value traps; DC-7 Shiller CAPE (data flag: Dividend/Earnings/CPI/PE10 zero-filled after mid-2023); DC-8 KR quality/value (OpenDART); DC-9 forward archive; DC-10 ETF tariff gap; DC-11 KR DTC.
Key numbers to re-check: HML/UMD/50-50 Sharpe splits (French linearmodels); HML 2007, 2016; UMD 2009; financials -69.5 vs -49.3; Mar-2000..Dec-2002 HML +95.7; KR concentration table & 2026 YTD +64.1/-5.9/11.7%; VIX dates; NMV table (value 0.47/0.42; PEAD 0.72/0.26 t 1.60 etc); power table.

---

## E5 — CRO of a multi-strategy pod hedge fund (fictional)
Lens: every crowded factor is eventually sold by someone else's risk limit; stay small, diversified, still invested for the rebound.
Korean factor sleeves (E5 local): KOSPI+KOSDAQ common, top 500 by prior month-end cap, price >= 1,000; D10-D1 monthly, daily BH within month; 2000-01..2026-09.
Position:
1. Factor crashes recurring: 19 dated episodes Aug 2007-Sep 2026, 7 in 2025-26. Korea 12-1 WML Jul 2026 -24.8% EW / -29.6% VW (worst month since 2000, gross).
2. Forced-selling crashes partly reverse within days (Aug 2007 -6.85% then +5.92%; Aug 2024 S&P recovered by 9 Aug; Apr 2025 +9.52% intraday).
3. Controls that worked: own-vol scaling of momentum (US 1926-2011 BSC 0.53->0.97; KRX VW net 0.36->0.41; Jun-Jul 2026 window -10.1% vs -22.6% same-exposure static); neutral construction / caps (Jul 2026 VW winner decile 85% Samsung+SK hynix); no leverage + liquidity/turnover limits.
4. Did not survive: name-level stops outside US momentum (KRX 15% stop WML EW Sharpe 0.43->0.26 gross, -0.17 net); vol scaling of value/quality/reversal (Cederburg 53 vs 50); crowding as timing trigger; VIX-type market gates (VIX 12.9-25.8 at 5 crash onsets).
5. Pod-style hard stops = manager-selection device (Millennium: -5% halves capital; -7.5% likely out). For one investor's few sleeves: fires on noise. At 8% vol, true SR 0.5: breaches -8% in 38% of years; -15% with 65% probability in 10 years.
6. Macro ladder (-8/-12/-15, E5 proposed it in macro panel) sound only as book-level tail device; corrections: (1) thresholds in units of book target vol, or book vol <= 8%; (2) never per sleeve (vol-scaled KRX momentum 0.41->0.14); (3) re-arm: reset reference peak, re-enter at 0.5 (HWM reference re-halted 20-22 times/yr).
7. Eleven-part risk layer RL-1..RL-11.
Local results (all IS):
- KR 12-1 momentum 2000-2026: EW gross 0.43 (2016-26 0.08; MDD -70.6%); EW net35 0.20 (-0.13; -81.2%); VW gross 0.52 (0.47; -72.8%); VW net35 0.36 (0.32; -78.5%).
- KR episodes: Mar/Apr 2009 WML EW -10.8/-15.6, VW -19.2/-17.0 while KOSPI +13.5% each month; Oct 2019 WML -18.1 EW / -22.6 VW (KOSPI +1.0%); Nov 2020 -6.5/-4.5 (KOSPI +14.3%); Jan 2021 -11.0/-8.7; Aug 2024 -8.4/-13.6 (KOSPI -12.1% over 2-5 Aug); Apr 2025 +12.1/+20.9; Oct 2025 VW WML -13.9%, STR VW -32.0% (KOSPI +19.9%); May 2026 VW WML +77.0% vs EW +9.5%; VW STR -35.3%; Mar 2026 KOSPI -19.1%, WML VW -13.1%; Jul 2026 -24.8/-29.6 (KOSPI -22.2% in July); Aug-Sep 2026 +15.3 EW / -0.6 VW.
- Concentration: pair share of KOSPI common-share cap 23.1% (Jun 2025), 35.1% (Dec 2025), 57.1% (Jun 2026), 52.6% (Sep 2026). Top-two share of VW winner decile 31.2% (Oct 2025), 77.1% (May 2026), 79.9% (Jun), 85.4% (Jul). SK hynix 68.7%/72.8% of VW winner decile May/Jun.
- Stop (15% from formation close, close trigger, exit t+1, ~70bp per stopped RT): WML EW 0.43->0.26 gross, 0.20->-0.17 net; WML VW 0.52->0.36 gross, 0.36->0.06 net; STR EW 0.32->0.31 gross, -0.29->-0.54 net; STR VW 0.17->0.24, -0.27->-0.36. MDD EW -70.6->-70.4; VW -72.8->-74.9.
- Kaminski-Lo condition (monthly AR1 >= monthly SR): KR WML EW -0.009 vs 0.117 (not met); WML VW +0.148 vs 0.139 (marginal); STR EW 0.079 vs 0.083 no; STR VW 0.126 vs 0.047 met; US Mom 0.039 vs 0.179 no; US HML 0.159 vs 0.129 met. KR stocks median daily AR1 +0.033, weekly -0.024, 63% of 3,556 negative weekly.
- Vol scaling KR (sigma126, 12%, cap1, net35): WML EW 0.20->0.31, MDD -81.2->-55.0, Jul 2026 -25.2->-7.5; same-exposure static (0.58x) 0.20, -59.5%; WML VW 0.36->0.41, -78.5->-41.0; static 0.40x -42.1%. 23 Jun-30 Jul 2026 window: scaled EW -13.1 vs static -24.8; VW -10.1 vs -22.6. Weights 22 Jun 2026: 0.35 EW, 0.20 VW; 30 Sep 2019 0.77/0.65 -> Oct 2019 worst scaled month (-13.1 EW, -14.3 VW). STR EW net -0.29 -> -0.59 scaled.
- US local (French monthly 1949-2017, 6m sigma, 12%, cap1): Sharpe 0.62->0.77; MDD -57.6->-28.5; Mar-May 2009 -49.3->-24.4; 2016 -17.5->-16.7.
- KR DM gate (KOSPI 24m <0 & sigma126 > expanding 2/3 q): on 3.9% of days (245 sessions, ~5 onsets); WML EW -19.8%/yr on vs +11.9% off; VW -47.7 vs +21.2; Sharpe 0.43->0.45 EW, 0.52->0.55 VW (gross, floor 0.5). Off in Oct 2019 and Jul 2026 (24m +235%).
- 5% name cap VW: gross 0.52->0.46; net 0.36->0.27; net 2016-26 -> -0.00; May 2026 +77.0->+17.8; Jul 2026 -29.6->-30.7; Mar-May 2009 -35.3->-29.6.
- Brownian P(MDD reaches -8/-12/-15): 8% vol SR 0.5: 1y 0.38/0.10/0.03; 3y 0.83/0.42/0.22; 10y 1.00/0.88/0.65. 12% SR0.5 10y 1.00/1.00/0.97. 6% SR 0.5 10y 0.95/0.59/0.33.
- Ladder tests (IS): Variant 1 (re-arm 1.0, reset), ladder A non-cumulative: KOSPI cap-weighted 2000-26 35bp 0.42->0.34, MDD -55.7->-53.6, 26 halts; Jul-2026 -38.6->-23.9; rebound +22.8->+7.9; H1-2026 +101.1->+55.2. Ladder B cumulative: 0.42->0.39, -49.3. SPY ladder A 0.41->0.25, MDD -56.5->-63.9 (!); ladder B 0.41->0.02; 2009 rebound +35.0->+2.1. Per sleeve: WML EW 0.20->0.03 (45 halts); WML VW 0.36->0.26 (MDD -78.5->-83.7); STR EW -0.29->-0.59; WML VW vol-scaled 0.41->0.09.
  Variant 2 HWM: SPY 21 halts/yr Sharpe -2.55; KOSPI 22, -1.69; KOSPI VT8 22, -4.53; KR WML VW vs 22, -5.63.
  Variant 3 (re-arm 0.5, reset, back to 1.0 after +4%): SPY 0.34->0.21, MDD -56.5->-48.8, 0.38 halts/yr; KOSPI 0.42->0.40, -55.7->-41.3, 0.67/yr, Jul-2026 -38.6->-21.3, H1-2026 +101.1->+49.0, below full exposure 61% of days; KOSPI VT20 0.40->0.37, -47.5->-34.7, 0.49/yr, Jul-2026 -12.3->-11.7; VT20 sigma-scaled 0.40, -37.4%, 1 halt total; KOSPI VT8 0.23->0.29, -32.6->-27.7; WML VW vs fixed 0.41->0.14; sigma-scaled 0.41->0.27; SPY VT8 0.10->0.04, below full 96% of days.
  Deepening: KOSPI reached -15 after -12 in 9 of 10; -12 after -8 67-75%.
- Turnover KR: WML 30% long / 35% short monthly one-way name turnover per leg; STR 89%/88%.
RL rules: RL-1 neutral construction (L/S: within-sector rank, |beta| <= 0.10, size-neutral, residual momentum; LO: active sector ±5pp, active beta ±0.15) BUILD. RL-2 caps (single name <= 5% NAV; L/S <= 2% sleeve gross per name; VW legs name <= 5% of leg; sector <= bench +10pp; R-07 pair/semis caps on look-through) BUILD. RL-3 liquidity/universe (KRX common, price >= 1,000, top 500 cap & 20d ADV >= 1bn KRW; exclude admin/warning designations, halted, < 60 sessions listed, DART rights-offering/merger windows; position <= 2% of 20d ADV; US price >= $5, ADV >= $5m) BUILD. RL-4 turnover/costs (monthly sleeves: enter top decile, exit below top quintile; <= 30%/mo one-way; reversal only where ex-ante edge >= 2x RT cost i.e. >= 140bp KRX; report 1x/2x) BUILD. RL-5 momentum own-vol scaling every momentum sleeve every market; DM gate spec book only; no vol scaling for value/quality/reversal. RL-6 book vol target <= 8%/yr (judgment) BUILD. RL-7 ladder corrected: scope total book NAV after RL-6, never per sleeve; thresholds -1.0/-1.5/-1.9 sigma of declared target; non-cumulative steps (x0.5; x0.5 + no new entries; HALT 0x, 10 sessions); re-arm at 0.5 with peak reset; back to 1.0 after +0.5 sigma gain or 60 sessions without new -1 sigma breach; never HWM after HALT. RL-8 no name-level stops; statistical review triggers (forward DD > 95th pct of simulated; 12m Sharpe < 90% CI lower) -> REVIEW, never auto-liquidation; HZZ US stop as BACKLOG CARD-O. RL-9 crowding/concentration display CONTEXT (no action until BL-C14 passes). RL-10 factor-episode stress table windows. RL-11 short-leg filters (SI > 20% float; DTC > 10; 5d turnover/float top 1%; 1% per short name; KR shorts research-only).
Flags vs macro: F1 R-07 fixed % only OK at ~8% book vol (at 12% target, -15% HALT fires with 97% prob in 10y at SR 0.5); F2 re-arm under-specified -> reset + 0.5; F3 non-cumulative steps; F4 never cascade into sleeves; F5 pair cap on look-through for LO/ETF books; F6 Korean 12-1 -> 0 supported (VW 2016-26 net 0.32 is concentration artefact: -0.00 with 5% cap; EW -0.13); F7 R-08 no factor-crash protection; F8 vol scaling +0.05 (VW) to +0.11 (EW) net on KR momentum; negative on reversal.
Claims ledger E5-C01..C29 (29 rows) [listed in full text §7]. Key: C04 BUILD R-03 everywhere; C05 R-05 confirmed; C06 HZZ BACKLOG; C07 KRX stops DROP; C08 KL condition convention; C14 sigma-scaled thresholds/book vol <= 8%; C15 re-arm rule; C16 DROP per-sleeve ladders; C17 ladder book-level only; C18 rely on R-03 not R-04; C19 RL-2 caps; C20 own risk state vs VIX; C21 comomentum BACKLOG; C22 DROP holdings crowding; C25 residual momentum BUILD-cand KR (DC-03); C28 KR STR monthly dominated by costs; C29 KR DM gate BACKLOG.
DCs: DC-01 KR factor crash anatomy (expected Jul 2026 -24.8/-29.6; Sharpe 0.43/0.20 EW; 0.52/0.36 VW); DC-02 stops & KL condition; DC-03 neutral momentum (residual, 12-7, sector-neutral; replace "12-1 -> 0" only if net 90% CI 2016-26 excludes 0); DC-04 ladder calibration grid; DC-05 false-alarm table; DC-06 KR comomentum/concentration (BL-C14 test); DC-07 state at crash onset (VIX 22.94, 49.68, 25.75, 12.92, 17.90, -, -, 19.49); DC-08 KR quant quake analogue; DC-09 US HZZ; DC-10 same-exposure vol scaling CIs; DC-11 cap binding frequency; DC-12 French Mom vintage (Apr 2009 -34.58% monthly vs -26.8% daily-compounded).
Key numbers to re-check (high priority): KR WML Sharpes; Jul 2026 -24.8/-29.6; stop result 0.43->0.26 and net -0.17; vol scaling 0.36->0.41 and window -10.1 vs -22.6; ladder variant-3 KOSPI (0.42->0.40; -55.7->-41.3; 0.67/yr); HWM halt loop; Brownian table; pair share 57.1 (Jun 2026)/52.6 (Sep 2026) vs E4 50.8 (29 Sep) vs macro 53.7/55.5; KOSPI -22.2% in July; KOSPI -12.1% 2-5 Aug 2024; VIX onset values.

---

## E6 — Vice-Chairman of IB (ECM and M&A), New York and Seoul (fictional)
Lens: every corporate event is a supply/demand shock timed by the best-informed party; trust event plumbing over event alpha.
Position:
1. Events priced within a session; test = drift after first provably-public close surviving 100-200 bp (US) / 70-140 bp (KRX) round trip.
2. Most US canon fails today: S&P 500 inclusion 7.3% (1990s) -> 0.8% n.s. (2010s); buyback/SEO long-run drift gone (~2003-2012, Fu-Huang); merger arb spreads compressed > 400 bp after 2001; dividend initiation/omission drift not robust; analyst recs never cleared costs.
3. Alive (US): IPO underperformance (2011-24 cohorts -16.4% style-adj over 3y; unprofitable -23.4% 1980-2024) -> cost-free EXCLUSION screen only; opportunistic insider purchases (Form 4) 82 bp/mo VW 1986-2007 gross -> only event promoted to gated BUILD-candidate signal, warning: holding period behind 82 bp unverified; if alpha arrives within a month it won't survive 60% haircut + 100 bp RT.
4. 13D activism, spin-offs BACKLOG.
5. Korea issuance: KOSDAQ-heavy SEOs +3% around announcement then ~-31% vs EW market over 12m (2005-2010) -> rights-offering/CB dilution screen most promising Korean event idea pending post-2015 replication on share counts.
6. Korea 2023-26 reforms are structural breaks (short-sale ban & end 31 Mar 2025; Value-up; Dec 2024 CB rules; dividend record-date reform; insider pre-disclosure; mandatory treasury-share cancellation Feb 2026) -> < 882 post-reform sessions -> INSUFFICIENT DATA until ~2028.
7. Everything else -> "Event Calendar and Risk Screen" layer that can only cut exposure (<= 1.0).
8. Timestamps: EDGAR acceptance date-times (use acceptance <= 15:30 ET -> usable at close d, else d+1; never filing date); OpenDART rcept_dt is DATE ONLY -> treat Korean event usable at next close (rcept_dt + 1 trading day) unless KIND time-of-day verified.
Event decision table (29 rows): BUILD-cand risk screens: #1 US IPO age < 36m (exclude unprofitable or sales < $50m for 36m; others <= 0.5x); #6 KR rights offering/third-party allotment (pending DC3); #7 KR private CB/BW with reset (pending DC3). BUILD-cand signal: #22 US opportunistic insider purchase (conditional on DC10; hold ~126d VW). CALENDAR FLAGS: #4 lock-up expiry; #14 KR dividend record/ex-date + DATA FIX DC5; #19 S&P 500 effective-date close; #20 KOSPI 200 changes (+ BACKLOG DC4); #21 MSCI; #28 short-sale regime/과열종목. RISK SCREEN: #15 announced cash targets (exclude pinned targets from technical cards); #27 chaebol intragroup (BACKLOG); RISK FLAG #13 US dividend cut; #24 KR insider pre-disclosed sale plans (DC7). DROP: #3 IPO pop; #5 US SEO card (fold into net issuance factor); #9 US buyback; #11 Value-up day-0; #12 dividend initiation; #23 insider sales; #26 analyst recs. BACKLOG: #2 KR IPO (DC1); #8 KR bonus issue/split (DC8); #10 KR treasury cancellation (INSUFFICIENT DATA until ~2028-29); #17 spin-off; #18 13D; #25 KR officer purchases.
Architecture: "Event Calendar and Risk Screen" module; every flag maps to an exposure multiplier in [0, 1.0] or to exclusion; screen gated vs unscreened card on same days (step 5 with unscreened card as benchmark).
Conflicts flagged: Korea ST-rev 3 and earnings drift 3 depend on clean returns around corporate actions; raw KRX closes around bonus issues, splits, 권리락, ex-dividend create artificial one-day crashes that inflate measured reversal -> DC0 and DC5 are prerequisites for the Korean reversal card; Korea flow 3 needs short-sale regime dummies (DC6).
Failures: 1999-2000 US IPO cohort 3y BH -53.1% (856 IPOs); 2021-22 IPO window; 1998-2001 acquirers; 2002-07 merger arb compression; autumn 2008 arb crash; 2003-12 buybacks/SEOs; repeat buybacks 2.51% -> 0.89%; 2010s S&P index effect; Tesla Dec 2020; 2012 KOSPI 200 pre-recon L/S -2.53%; activism failures 21.4%; lock-ups 2005-06; KR SEOs 2005-10 -31%; 31 Mar 2025 KOSPI -2.93%; Value-up day-0; June 2026 MSCI; US div initiations; Oct 2025 FSC CB enforcement.
Claims ledger E6-C01..C28 (28 rows). Key: C01 US IPO 3y -20.5% mkt-adj / -8.9% style-adj (1980-2024); 2011-24 -24.7%/-16.4% (Ritter) -> BUILD-cand screen. C02 unprofitable -23.4% vs profitable +1.8%; sales < $10m -34.0%. C04 KR IPO first day 52.8% (Ritter Intl) BACKLOG. C05 lock-up -0.97% [-1,+1]. C06 SEO drift shrunk. C07 buyback drift gone. C08 non-US buybacks persist (MPV 2019) BACKLOG KR. C11 merger arb DROP; pinned targets screen. C13 13D 7.2%, <= ~2% after filing day (inferred) BACKLOG. C14 S&P inclusion gone. C15 KOSPI 200 changes (1995-2008 day-before-effective +2.24%; 2012 -2.53%). C17 KR treasury cancellations KRW 21.4tn (2025), 43.1tn (Jan-May 2026). C18 Value-up day-0 +1.5%. C19 KR SEOs 734 (2005-10, 75% KOSDAQ) CAR +3.23%, BHAR ~-31% (12m), -46% (24m) vs EW market (IS) -> BUILD-cand screen pending DC3. C21 CB rules Dec 2024. C22 short-sale ban end. C24 insider pre-disclosure. C25 insider purchases (82 bp/mo; construction and holding period NOT verified) -> BUILD-cand signal (DC10, ~126d). C27 PIT availability EDGAR vs OpenDART -> BUILD data rule. C28 KR bonus issues +4.33% CAR [-1,+1] (2008-14) BACKLOG.
DCs: DC0 corporate-action integrity of returns (shares = marcap/close; flag |dln shares| > 1%; re-run 5-day reversal masking +/-5 sessions; pass if reversal Sharpe changes < 10%); DC1 KR IPO BHAR; DC2 KR lock-up proxy; DC3 dilution events from share counts (+3% non-split increases; BHAR (+1,+250) vs size-matched; gate 12m exclusion screen); DC4 KOSPI 200 changes; DC5 ex-dividend artefact; DC6 short-selling regimes DiD; DC7 KR insider pre-disclosure; DC8 bonus issues; DC9 treasury cancellations proxy; DC10 US insider purchases (EDGAR+FMP, 126d VW pre-registered); DC11 US IPO-age screen.
Key numbers to re-check: KR SEO -31% (Kim-Lee 2013, T1 Korean journal); Ritter numbers (-16.4%; -23.4%); 82 bp/mo (CMP); S&P 7.3 -> 0.8; EDGAR acceptance example; OpenDART rcept_dt date-only; KOSPI -2.93% on 31 Mar 2025; DC0/DC3 computable on marcap (shares = marcap/close; marcap Stocks column).

---

## E7 — Head of Korea Equities & Derivatives (global bank Seoul branch), ex-Korean securities firm quant desk (fictional)
Lens: execution & market structure (limits, VI, short bans, sell tax, retail turnover, two-stock index); checks against KRX history.
E7-QC construction: liquid universe = KOSPI+KOSDAQ common (code ending 0), ex SPAC/pref/관리/투자주의환기; cap >= 100bn KRW, 20d avg traded value >= 1bn, price >= 1,000, traded that day (same-day volume = mild look-ahead in eligibility); ~700-800 names 2015-19. Price-only returns (no dividends). Monthly EW quintiles; benchmark EWM = EW universe formed same month-end. Costs 35 bp per side as 2x one-way turnover; 70 bp stress. iid t; event studies date-clustered t. ~20 families x 5 periods -> |t| < 3 = noise.
Position:
- Robust result is negative: chasing attention loses (locked limit-ups bought next open, volume spikes, +50% 20d run-ups, high MAX) -> EXCLUSION SCREEN.
- Only four classic factors marginally positive long-only net 35bp (2015-07..2024-12 vs EW): low-turnover momentum +3.1%/yr; low-vol +1.7%; 52wk-high +1.0%; LTR value proxy +0.2%. None significant; only low-turnover momentum (+0.2%) stays positive at 2x.
- Prior Korea ST-reversal 3 and foreign flow 3 not supported.
Key local numbers:
- Limit-up next-open entry: -400 bp (t+5), -595 bp (t+20) vs EW; n=10,943; date-clustered t -14.3/-11.3; 2015-19 -305/-425; 2020-24 -431/-574; 2025-26 -462/-868. Close-entry +332 bp t+1 (unfillable). Mean next-open gap +5.02%.
- Locked limit-down: -663 (t+1), -773 (t+5), -1,094 (t+20), n=755.
- Volume >= 5x 20d avg & r >= +5%: -46.7 bp (t+5, t -5.21), -98.4 bp (t+20, t -6.66); n=35,823; sub-periods t+20 -96/-82/-160.
- 20d return >= +50%: t+20 -73.3 bp (median -738), t -5.55.
- Golden/dead cross, 정배열: <= 17 bp; t ~0. 정배열 state -5.3% gross / -10.9% net (2015-19); crash -48.7% vs -27.1%.
- Prior-design daily reversal (bottom-quintile 5d z with vol >= 1.5x): t+5 +12.3 bp (t 0.03), t+20 +31.5 (t 0.63); 2015-19 t+5 +34.0 (t 3.45); 2020-24 +0.6; 2025-26 -21.0.
- Long-only vs EWM 2015-07..2024-12 (gross / net35 / turnover): mom all -2.0/-4.4 (3.4x); mom low-turn +6.0 (t 1.55)/+3.1 (t 0.80) (4.1x); mom high-turn -8.4/-10.9; 1M rev +4.2/-2.7 (10.0x); low-vol +4.3/+1.7 (3.8x); low-MAX +2.5/-2.9; 52wk +5.1/+1.0 (64% yrs +); LTR +2.9/+0.2.
- Weekly reversal: long-leg turnover 41.7x/yr; LS gross +18.8% (2015-19) -> -39.7% net; LO +9.3% -> -20.0% net.
- LS gross: low-vol +16.2% (2015-19, Sharpe 0.76), +21.2% (2020-24, 1.12); high-vol quintile lost 59.1%/61.8%. Short-regime split: low-vol open +14.3%, partial ban +27.0%, full ban +14.9%.
- K200 proxy 2015-07..2024-12: CW +17.7%, CW ex-pair -7.5%, EW200 +1.5%; low-vol Q5 net -14.1%; mom Q5 -15.3%; rev Q5 -51.2%. Crash: CW -39.3%, low-vol Q5 +3.2%.
- Melt-up/crash/rebound (vs EWM +45.5/-25.4/+29.5): mom winners +87.4/-43.0/+52.7; low-turn mom +84.1/-14.5/+10.8; low-vol +38.5/-0.8/+5.4; low-MAX +35.6/-10.3/+9.2; 52wk +94.7/-26.2/+17.5; rev +16.0/-33.2/+38.1; LTR +26.5/-32.4/+39.7.
- Breadth (KOSPI common): 30 Dec 2025-22 Jun 2026 n=831 EW +2.8%, median -9.3%, 66.2% fell, CW +117.1%, CW ex-pair +41.7%, Samsung +195%, SK hynix +349%; 22 Jun-30 Jul CW -38.6%, ex-pair -25.8%, EW -10.6%; 30 Jul-29 Sep CW +22.8%.
- Pair share of KOSPI cap (all listings denominator): end-2015 16.7%, end-2019 27.2%, end-2022 21.8%, end-2023 26.9% (vs KEIA 22%), end-2024 22.6%, end-2025 34.0%, 27 May 2026 50.4% (Sedaily 50.44%), 22 Jun 55.7%, peak 57.1% (25 Jun), 29 Sep 50.8%. Pair share of KOSPI traded value 42.8% 2026 YTD.
- Limits: ±15% -> ±30% on 15 Jun 2015. Locked limit-ups/yr 774 (2015 from 15 Jun) ... 1,579 (2020) ... 1,994 (2026 to 29 Sep); limit-downs 56 (2015) -> 196 (2026).
- Short bans: 1 Oct 2008-31 May 2009; 11 Aug-9 Nov 2011; 16 Mar 2020 (partial lift 3 May 2021, K200/KQ150 only); 6 Nov 2023-30/31 Mar 2025. 2024 KOSPI -10.1%, KOSDAQ -22.8%.
- Sell tax 0.20% (2023), 0.18% (2024), 0.15% (2025), 0.20% (2026; KOSPI = 0.05% STT + 0.15% rural special tax).
- Spread estimator (Abdi-Ranaldo CHL) failed: 57-79 bp even > 2tn names.
- Literature: Sim & Kim 2021 reversal coefficient -2.950 (t -3.77) = regression coefficient (not %/month); strategy alpha 1.275%/mo (t 3.22) gross; pret(12,7) alpha 0.531% (t 2.05); pret(12,2) 0.285% (t 0.85). Eom et al. 2020 high-turnover WML -6.13%/yr (t -4.76) 2000-19. Richards RBA: foreign flow AC 0.43; impact 0.119 (t 11.9), permanent. KEIA: foreigners -148.3tn H1 2026.
Proposed Korea weights (prior -> E7): XS-mom 1 -> 1 low-turnover/residual only, vol-scaled; raw 12-1 = 0. ST-rev 3 -> 1 (monthly, conditioning/tie-break) / 0 daily-weekly. Value 2 -> 1 until OpenDART. Quality 1 -> 1. Low-vol 2 -> 2 as PROTECTIVE card (not alpha). Flow 3 -> 1 (log now, test). Earnings drift 3 -> 2. TS mom 2 -> 1. NEW attention-fade exclusion 3 (screen). Size -> 0.
Mandatory Korea constraints: (1) long-only realism vs EWM + K200-proxy CW + CW-ex-pair; (2) short-regime flag 0/1/2; (3) limit-state fill rule (no entry at locked limit-up close -> t+1 open; exit at locked limit-down carried to first unlocked session at 2x cost; flag VI/CB days); (4) liquidity (cap >= 100bn, 20d ADV >= 1bn (3bn capacity variant), price >= 1,000; ex 관리/투자주의환기/SPAC/pref; drop IPO/relisting days and liquidation trading); (5) attention-fade exclusion (no new longs if in last 5 sessions (20 for blow-offs): vol >= 5x & r >= +5%; locked limit-up; 20d >= +50%; top-decile 21d MAX); (6) costs 35/70 + time-varying tax sensitivity; (7) dividends needed; (8) pair/semis caps + correlation to pair reported.
Ranked experiments: 1 K-AF attention-fade exclusion; 2 K-LV protective low-vol; 3 K-MOM-LT low-turnover vol-scaled momentum; 4 K-FLOW (t-1 KIS flows, pre/post May 2026); 5 K-VAL/QUAL (OpenDART); 6 K-52WH quarterly; 7 K-SHORTREG DiD; 8 K-LD exit rule.
DROP: daily/weekly reversal; golden/dead crosses; 정배열; price > MA200 stock selection; limit-up chasing & volume-spike buying; size; raw all-name 12-1.
Claims ledger E7-C01..C30 (30 rows) [§11 full text].
DCs: DC1 gate re-run of factor table; DC2 attention-fade exclusion; DC3 short-regime DiD; DC4 momentum crash anatomy with vol scaling/DM; DC5 limit-fill audit; DC6 tax sensitivity; DC7 concentration anchors; DC8 cost calibration (KIS bid/ask); DC9 flow card; DC10 OpenDART value/quality; DC11 dividend-inclusive returns.
Key numbers to re-check (high priority): attention-fade (-400/-595; -98); limit-down continuation; low-turnover momentum +3.1% net; low-vol crash -0.8% vs -25.4%; pair share series; breadth 66.2%; 2015-07..2024-12 factor table; reversal -2.7% net; weekly reversal -20%.

---

## 9. Verification results (added 3 Oct 2026, 00:10 KST; details in exec_verification_log.csv and R2_EXEC_chair_resolution.md)

**Log:** 103 rows: 77 MATCH, 12 MISMATCH, 11 TRACED-NOTE, 3 UNVERIFIABLE. This is after the final R2 summaries arrived (00:16 KST): E7-C18 moved from MISMATCH to MATCH, and an E3-C20(robust) TRACED-NOTE was added.

| Paper | Rows | MATCH / MISMATCH / TRACED / UNVERIFIABLE |
|---|---|---|
| E1 | 14 | 10 / 3 / 1 / 0 |
| E2 | 10 | 8 / 0 / 2 / 0 |
| E3 | 16 | 12 / 1 / 2 / 1 |
| E4 | 16 | 11 / 2 / 3 / 0 |
| E5 | 17 | 14 / 3 / 0 / 0 |
| E6 | 11 | 6 / 2 / 2 / 1 |
| E7 | 19 | 16 / 1 / 1 / 1 |

**Mismatches that change a decision**
- E1-C16: dynamic momentum doubles Sharpe; it does not quadruple it.
- E3-C23: bounding trend to [0.5, 1] does not halve protection. R2 interim: clip × VT20 PASS (PC-1 +15.4), unbounded × VT20 REVISE (PC-5 0.57).
- E7-C20: Korean low-vol protection is de-gearing; a same-beta static book has a 10.5 pp better MDD.
- E4-C11 / E6-C25: CMP's 82 bp is long-short (buys minus sells) over one month.

**Mismatches that change magnitude only**
- E1-C20/C21: MTUM IT 53.22%.
- E1-KQ5 and E4-sec1: the gate multiplier is ×0.6, not ×0.4.
- E5-C18: WML levels are 0.26-0.30 EW gross, not 0.43.
- E5-C29: 3 D-M onsets, not about 5.
- E5-C18 (24m): +227%, not +235%.
- E6-C22: −3.00%, not −2.93%.
- E7-C18 is now MATCH. The lab confirms the number; the low-turnover sign depends on the decade (1996-2026 +9.7%/yr, t 2.8; 2015-24 ≈ 0).

**Chair errors, corrected**
- Vol-scaling warm-up (c05 → c05b).
- Event benchmark with same-day eligibility (c06 → c06b-c06d).

**R2 results used** (`/home/claude/datalab/r2/{kr,idx}/results` and the final summaries `R2_KR_summary.md` and `R2_IDX_summary.md`)
- Exclusion horse race: B1 F4 +3.1%/yr (t 8.3), F1 +4.3%, F5 +1.4% (−0.1% at 70 bp), F6 +2.3%. VW-capped books ~0-1%. B4 F1 +7.8%. Indicative gate REVISE.
- Stop-loss tests: EW net 0.04 → −0.15; VW net 0.28 → 0.07.
- Low-vol: alpha +2.2%/yr (t 0.8); MDD −73.9% vs −69.9%.
- Monthly reversal: +2.7% net35 (t 0.5); −6.7% in 2016-26.
- Low-turnover momentum (E7 ladder): E7-exact +2.9% (t 0.75); ALL −0.1%.
- 12-7 momentum L/S: net35 Sharpe 0.60.
- Protective scorecard and overlay vs sleeve: KOSPI ensemble vote-share PASS; bounded × VT20 PASS; SPY at 50 bp REJECT.
- Gate-power simulation: a true Sharpe of 0.5 needs 13.7 years for a 50% pass on steps 2+3+8.

**Fetch failures:** KIND returned HTTP 403 (3 Oct 2026). The EY tax page came back garbled, so PwC was used. WebSearch was not used (budget exhausted).

**R2 final changes:**
- The attention screen (F5) fails as a monthly filter, so EX-T-04 standalone goes to DROP and stays an entry-day execution exclusion.
- Momentum winners ex high-turnover is a BUILD construction rule (EX-T-05 FORWARD-SIM variant).
- KOSPI trend evidence rests on 1997-2001, while VT20 is robust.
- The lab calls low-vol "protective"; the chair's c12 test (same-beta static on the lab's books: MDD worse by 7-22 pp, tail 0.97-0.99) disagrees, so this is contested.

**Outcome:** 28 consensus items (EC-T-01..28), 14 contested (EX-T-01..14), 12 refuted or withdrawn (ER-T-01..12), 22 corrected anchors, and 18 macro flags (MC-01..18).
