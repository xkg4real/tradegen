QUANTGEN · MACRO [Neural link](#link) [Macro tape](#tape) [Where models fail](#models) [What survived](#overlays) [The debate](#debate) [Into QUANTGEN](#build) [Sources](#sources)

QUANTGEN research · as of 2 October 2026 · data through Sep 2026

# Macro Neural Link

Six simulated professors and seven simulated finance executives argued over how macroeconomics should enter QUANTGEN. Every claim was then tested on 1926–2026 data. Macro earns a place as risk sizing, data hygiene, hedge checks and event handling. Almost every rule that used macro to time direction failed.

**139**resolved claims, after 13 position papers and 7 cross-examinations

**27**core links both panels backed, written into the integration spec

**11**prohibitions: ideas refuted on the data, listed as do-not-build

**22**backlog items still contested, one-sided or untested

Keep

### Momentum sized by its own risk

Own-volatility scaling lifts US momentum's Sharpe from 0.40 to 0.71 under the spec's 1.0× cap, and to 0.80 with a floored bear-market gate. Max drawdown falls from −63% to −21%.

Keep, with a label

### Korea-local volatility control

A 20-day KOSPI vol target cut the 22 Jun–30 Jul 2026 crash from −38.6% to −12.2%. No US indicator flagged it. It also gave up half of the H1 rally. Eleven years of KOSPI cannot yet confirm it costs no Sharpe, and July 2026 supplies 59% of its benefit, so it stays INSUFFICIENT DATA at QUANTGEN's costs.

Drop

### Macro as a direction signal

Curve, real-rate, credit, oil and VIX-term-structure gates, the prior four-state table and every 1.5× multiplier lost value. The prior Korea gate's +0.31 Sharpe came from look-ahead.

1 · The neural link

## Where both panels pointed, and where only one did

The 139 claims were merged into 60 propositions. Each dot counts how many distinct claims from each panel fed one proposition. Top right means both panels kept returning to it.

### Focus map: professors' claims vs executives' claims per proposition

Hover a dot for the proposition and its key number. Shape and colour both encode the outcome. Small offsets separate dots with identical counts.

Data table

Strongest shared links

Focus counts are professors / executives. The prohibition with the most combined focus is using Street forecasts and surveys as timing signals (8 / 20). "Regime and ML shortcuts are valid" was raised only by professors (12 / 0) and refuted by the data labs.

2 · The macro tape, Jan 2024 → Sep 2026

## Cutting into a soft labor market, then hiking into an oil shock

The Fed cut 175 bp between Sep 2024 and Dec 2025, then hiked on 16 Sep 2026 as inflation, an energy shock and record term premium pushed the 10-year to 5.29%. Korea had its own cycle: a memory-chip boom took KOSPI to 9,114 before a 38.6% crash.

### US unemployment rate

3.7% in Jan 2024, a 4.5% peak in Nov 2025, 4.1% in Aug 2026. The Oct 2025 household survey was never collected because of the shutdown, so that month is blank.

Data table

### Payrolls, 3-month average change (thousands)

Monthly gains averaged 121.6k in 2024, 9.7k in 2025 and 80.4k in Jan–Aug 2026. Openings per unemployed fell from 1.36 to 0.87 before recovering to 1.01.

Data table

### Inflation and the policy rate (%)

Headline CPI jumped from 2.4% to 4.2% (May 2026) on oil while core CPI barely moved. Core PCE sat at 3.0% in August. The seven Taylor-rule variants the panels tested give 4.3–6.2%, above the 3.75–4.00% range after the hike.

Data table

### Treasury yields and term premium (%)

After the first cut in Sep 2024 the 10-year rose 113 bp while the Fed cut 100 bp. Term premium explained 76 bp of it. In 2026 real yields did the work: +100 bp of the 10-year's +111 bp.

Data table

### Dated Brent ($/bbl, weekly)

Strikes on Iran (28 Feb 2026) cut Hormuz flows below 10% of normal. Dated Brent peaked at $138.21 on 7 Apr. These are spot prices; front-month futures were about $103 at the end of September.

Data table

### USD/KRW (weekly)

The won weakened to about 1,549 per dollar in June 2026, then strengthened as USD/KRW fell 12.4% in Q3, while the broad dollar was flat and foreigners sold ₩21.5tn of Korean stocks in September. Record chip exports drove it.

Data table

### KOSPI (weekly close)

From 3,072 (30 Jun 2025) to a 9,114.55 closing peak (22 Jun 2026), then −38.6% to 30 Jul. Record days: −12.06% on 4 Mar, +17.91% on 31 Jul. Samsung and SK hynix explain about two-thirds of the index's move.

Data table

Snapshot · percentile against each series' history since 1990 (or its start)

| Variable | Latest | 12-month change | Percentile vs history |
| --- | --- | --- | --- |

Rates are stressed while credit is calm: real yields sit at the 99th percentile and the Baa spread near the 3rd.

3 · Where models fail

## The textbook relations held for decades, then broke in this cycle

Each model below appears in the attached textbooks or the course materials the professors mapped. Each was re-estimated on FRED data, and most broke between 2020 and 2026.

### Yield curve, 10y minus 3m (pp)

Shaded: NBER recessions. 9 of 13 inversions since 1960 preceded a recession within 24 months. The 2022–24 inversion lasted a record 534 days, and no recession has followed.

Data table

### Recession probability from the curve (%)

The NY Fed's Estrella–Trubin probit peaked at 74% in May 2023 and stayed above 30% for 25 months. Fitted on only six recessions, its own 90% band at that spread was 57–99%.

Data table

### Sahm rule, real time (pp)

It caught all 9 recessions since 1960, a median 2 months after they began. It fired in July 2024 at 0.53 with no recession in the 26 months since.

Data table

### Phillips curve slope by era

Δ12m core PCE on unemployment gap

Dots show the slope, whiskers ±1.96 HAC standard errors. Before 1985 a tight labor market raised inflation. After 1985 the slope is near zero, and the 2023–25 disinflation came with unemployment still below its natural rate.

Data table

### Okun's law, rolling 40-quarter coefficient

Dashed: the −0.405 benchmark (Ball, Leigh and Loungani). The relation replicates through 2010 and breaks around 2011. In 2023–25 unemployment rose 0.9 pp while GDP grew 2.7% a year.

Data table

### Stock–bond correlation, rolling 1 year

Shaded: months with core PCE inflation at or above 3%. Pooled daily correlation is −0.29 below 2% inflation and +0.21 above 3%. When it turns positive, bonds stop hedging equities.

Data table

### Gold vs its 2006–21 real-yield fit ($/oz, log scale)

The level relation broke in 2022. At today's 2.93% real yield the old fit implies $626 against $4,187 actual. The short-run link survives: gold still falls about 7.6% per 1 pp rise in real yields.

Data table

### Broad dollar during US equity sell-offs (%)

change over each S&P drawdown

The dollar rose in 10 of 11 sell-offs. April 2025 broke the pattern: stocks fell, the dollar fell and yields rose together. That combination is a hedge-failure flag, not a de-risk signal.

Model-failure ledger

| Model | Works when | Failed when | Why | QUANTGEN use |
| --- | --- | --- | --- | --- |
| **Yield-curve probit** | 9 of 13 inversions since 1960 led recessions (median 10 months) | 2022–24: record inversion, 74% probability, no recession | Six-recession sample; term premium distortion | Logged prior only |
| **Sahm rule** | 9 of 9 recessions caught | Jul 2024 trigger (0.53), no recession | Labor-supply surge; it confirms rather than predicts | Logged prior only |
| **Phillips curve / NKPC** | 1960–84 (accelerationist slope −0.39) | Flat since 1985; 2021–23 surge; 2023–25 disinflation without slack | Anchored expectations; nonlinearity at high vacancies | Not a signal |
| **Okun's law** | 1961–2010 (β −0.41) | Break around 2011; 2023–25 | Productivity and labor-force shifts | Not a signal |
| **Taylor rule** | Describes policy in calm years | 2021–22: funds rate 5–7 pp below the rules | Look-through of supply shocks; r\* unobservable | Context range (0.4–2.3 pp below rules now) |
| **Expectations hypothesis** | Short-rate path drives the 10-year in most cycles | Sep 2024–Jan 2025: 10y +113 bp during 100 bp of cuts | Term premium (+76 bp), fiscal supply | Real yield and term premium as risk inputs |
| **UIP** | Never at monthly horizons | USD/JPY slope −0.76 vs theory +1; USD/KRW −1.15 | Risk premia; carry crashes | Carry is a crash-prone premium |
| **Dollar as safe haven** | 10 of 11 equity sell-offs | Apr 2025 "sell America" | US-policy shock instead of a global one | Hedge-validity flag |
| **Gold vs real yields** | 2006–21 level relation; short-run beta still holds | 2022–26 level break (+568% residual) | Central-bank buying, reserve diversification | Short-run risk input only |
| **Stock–bond hedge** | Core inflation below 2% | 2022; again from Apr 2026 | Inflation and real-rate shocks hit both | No hedge credit at core PCE ≥3% or positive correlation |
| **Term spread as a return forecast** | In sample, 1960–89 | Out of sample R² −0.57% from 1980, −1.28% from 2010 | Unstable coefficients | Not a signal |
| **Markov-switching regimes** | Smoothed, in hindsight | Real time: about 17 switches a year (US) and 31 (KOSPI); Sharpe 1.52 smoothed vs 0.39 real time | Look-ahead in smoothed probabilities | Filtered states only; no daily HMM gates |

4 · What survived the data

## Volatility rules survived. Macro direction rules did not.

The prior design's overlay rules were back-tested on daily factor returns from 1990 with information lagged one day, then bootstrapped. Survivors were re-run under the spec's caps and at QUANTGEN's own costs.

### Overlay rules: change in Sharpe vs the static factor, US daily 1990–2026

gross of costs · bar label = bootstrap share beating static

A share near 1.00 means the rule beat the static factor in almost every one of 1,000 block resamples; near 0.00 means it lost almost every time. The two momentum rules shown here use a 2× cap and a 0× gate; the spec versions (1.0× cap, 0.5 floor) appear in the next chart. Korea and crypto rules are summarised below.

### US momentum under the spec's rules (cumulative log return, vol-matched)

Sharpe 0.40 static, 0.71 with own-vol scaling capped at 1.0×, 0.80 with the floored Daniel–Moskowitz gate. The scaled lines are rescaled to the static line's volatility so the curves compare return per unit of risk.

Data table

### KOSPI: buy-and-hold vs a 20-day vol target (index, 30 May 2025 close = 100)

Exposure = min(1, 20% ÷ trailing 20-day vol), set at the prior close. It cut the 22 Jun–30 Jul crash to −12.2% from −38.6%, at the cost of a +52% H1 instead of +101%. This is its best episode: over 2016–26 its Sharpe is unchanged (0.638 vs 0.634), and July 2026 supplies 59% of its drawdown benefit.

Data table

### Vol-target exposure on KOSPI

The weight was already near 0.3 before July, which is why the crash cost so little. It sat below 0.5 for most of the 2026 rally.

### KOSPI's beta to the prior US session's semiconductor index

Rolling 252-day beta of KOSPI on the Philadelphia semiconductor index's previous session. It rose from 0.17 (2015–19) to above 0.5. US data arrive after Seoul's close, so they can only inform the next session.

Data table

**Korea and crypto rules.** The prior Korea gate (semiconductor trend × won) showed +0.31 Sharpe only because it used US data that arrive after the KOSPI close. Lagged correctly it adds +0.05, and the semiconductor leg alone lost 0.22 in 2024–26. Scaling bitcoin by US net liquidity added −0.01 overall and −0.20 in 2023–26; bitcoin fell 53% while net liquidity rose.

Indicative verdicts in QUANTGEN's gate, net of its pre-registered costs

| Rule | Card | Evidence at QUANTGEN costs | Indicative verdict |
| --- | --- | --- | --- |
| **Momentum own-vol scaling** | Outperformance | ΔSharpe +0.27 vs unscaled at 50 bp per side on both legs, p ≤ 0.001; Sharpe 0.63 at 2× costs; 70% of years positive | Pass |
| **Daniel–Moskowitz bear gate, floor 0.5** | Add-on to the above | ΔSharpe +0.07, p 0.018, but only 7 gate onsets since 1990 (Tier A needs 30) | Insufficient data |
| **Korea 20-day vol target** | Protective | Max drawdown 4.4 pp better than a static book at the same average exposure; ΔSharpe +0.001 (ETF, 3 bp) or −0.028 (stocks, 35 bp); July 2026 supplies 59% of the benefit | Insufficient data |
| **US 15% vol target** | Protective | Drawdown gain vs the same-exposure static book only +0.2 pp at 50 bp | Reject |
| **USD/KRW leg (20-day rise > 3% → 0.75×)** | Protective, forward-sim | Drawdown gain +0.1 to +1.1 pp; exposure on the worst 5% of days 0.99–1.00 of average; reject on value timing, formally insufficient data (26 onsets) under strict timing | Reject |
| **US rates leg (10-year +40 bp in 20 days → 0.5×)** | Protective, forward-sim | Max drawdown 3.5 pp worse than the static book under strict publication timing | Reject |

Indicative: computed on the research data with QUANTGEN's gate definitions, not a run of QUANTGEN's own gate. The protective card class (drawdown first, Sharpe non-inferiority within 0.10) is defined in the integration spec.

5 · The debate

## What the panels disagreed on, and what settled it

Each panelist cross-examined colleagues in the same panel, re-opened sources and re-ran numbers. Several positions were withdrawn by their own authors.

| Question | Professors | Executives | What settled it |
| --- | --- | --- | --- |
| **How much does momentum crash protection add?** | P3 cited Daniel–Moskowitz as 1.43 vs 0.71 | Use it, but simply | The chair re-opened the published JFE 2016 paper: 0.682 static, 1.041 with constant vol, 1.194 dynamic. Most of the gain is plain vol scaling. |
| **Does macro add anything at daily horizons?** | P6: no, use the market's own states. P1: macro decides scope (hedges, inflation regime). | Only as risk inputs | Both: no macro gate on daily equity exposure, but macro decides whether bond and dollar hedges count. |
| **Should stress raise reversal or quality weights?** | P3 proposed 1.5×; withdrew | E1 proposed 1.5×; conceded | Reversal earns more in stress but its risk rises faster; every 1.5× rule lowered Sharpe (−0.05 to −0.20). All multipliers now stop at 1.0×. |
| **Black out positions around FOMC and data?** | P3: the announcement premium argues against it | E2/E5: black out | 2015–26 data: FOMC days earned about the same as other days. No swing blackouts; short intraday windows. A decision-day size-down stays a backlog test. |
| **Was the Korea gate real?** | P2 flagged the time-zone look-ahead | E4 defended the semiconductor and won legs | +0.31 Sharpe became +0.05 once US data were lagged to the next KRX session. Only the won leg survived, and it fails at QUANTGEN's costs. |
| **Do US rates matter for Korea?** | P1: real yields as a Korea driver | E1/E3: rates-stress cuts | During the July crash the 10-year rose only 17 bp and the won strengthened. Korea inputs must be local. |
| **Can a backtest approve an overlay?** | P2: strict multiple-testing hurdles | E5: 30-event rule; E1: too rigid for 2026 | Detecting +0.05 Sharpe needs 33–44 years. Tiered governance: price rules need 30 onsets, macro rules stay bounded and run forward first. |
| **Are Street forecasts or surveys useful?** | Not as predictors | E7: as a priced-in baseline only | S&P target errors averaged 17%; in 2026 the houses forecast cuts and the Fed hiked. The Aug-2026 survey came out after KOSPI had already fallen 25%. |

6 · Into QUANTGEN

## What the integration spec builds, runs forward, and forbids

QUANTGEN is a read-only research desk, so every rule becomes a model card that passes through its nine-step gate. Nothing here places an order.

Build now

### Core links

- **Point-in-time data**UTC and publication timestamps, vintages, US data usable only from the next KRX session, missing months fail closed.
- **Bounded overlays**Every overlay multiplier in \[0.5, 1.0\] and every vol-target weight in \[0, 1\]; nothing above 1.0; zero exposure only from the risk layer or the engine's HALTED state.
- **Momentum risk state**Own-vol scaling (cap 1.0) plus the bear gate at a 0.5 floor.
- **Per-market vol target**Korea 20-day, cap 1.0, Samsung + SK hynix caps. SMA20 estimator, which passes the vol backtest; EWMA is the registered challenger, and GARCH-t may replace it only after passing.
- **Hedge-validity state**No bond-hedge credit at core PCE ≥3% or positive 63-day stock–bond correlation.
- **Events and context**US nights as KOSPI open-gap inputs; oil to the event calendar and Monte Carlo; Sahm, curve, Taylor and term premium logged, never acting.

Forward-sim and next tests

### Running on paper, or waiting for data

- **USD/KRW leg**20-day rise above 3% → Korea gross 0.75×. Needs a timestamped won history and 12 months forward. Indicative verdict: reject (not de-risked on the worst days).
- **US rates leg**10-year +40 bp in 20 days → US duration-sensitive gross 0.5×. Needs a live yield feed: H.15 posts each day's yield at 16:15 ET the next business day, so a decision at the close can use it only two business days later. Indicative verdict: reject at QUANTGEN's costs.
- **Korea leverage state (backlog)**Margin debt, leveraged-ETF assets and investor flows via KIS. Top backlog priority.
- **Bear-gate holdouts (backlog)**Out-of-region tests to lift the Daniel–Moskowitz gate from INSUFFICIENT DATA.

Do not build

### Prohibited by the evidence

- **Prior four-state table**and every multiplier above 1.0×.
- **VIX-term-structure momentum switch**It predicts volatility, not direction.
- **Curve, real-rate, credit and oil gates**on factor weights or market gross.
- **Semiconductor × won Korea gate**Look-ahead artefact.
- **Net-liquidity crypto rule, Street forecasts and surveys as signals**
- **Smoothed regime probabilities, macro ML "complexity" timing, pre-cutoff LLM backtests, swing blackouts**

`QUANTGEN_MACRO_INTEGRATION.md`

For Claude Code: 18 rules mapped to core/ficc, core/quant, core/engine and the gate, with JSON schemas, YAML config, golden-value tests and a build order.

`QUANTGEN_MACRO_BACKLOG.md`

Contested, one-sided and untested ideas, each with a settling test, plus data to acquire and the failure archive.

`QUANTGEN macro overlay research.md`

The full research report: knowledge map, the 2024–26 macro record, model failures and the panel debate.

7 · Method and sources

## How this was built

The panelists are simulated, fictional personas; nothing here is a statement by a real firm or person. Numbers come from scripts run on downloaded data, or from pages that were opened and checked.

#### Data

- [FRED, Federal Reserve Bank of St. Louis](https://fred.stlouisfed.org/): 70 macro and 50 daily series, downloaded 2 Oct 2026
- [Kenneth R. French Data Library](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html): US and regional factor returns through Aug 2026
- Yahoo Finance: KOSPI, KOSDAQ, Samsung Electronics, SK hynix, Asian and European indices, commodities, FX, MOVE

#### Official

- [FOMC statement, 16 Sep 2026](https://www.federalreserve.gov/newsevents/pressreleases/monetary20260916a.htm) and [Summary of Economic Projections](https://www.federalreserve.gov/monetarypolicy/fomcprojtabl20260916.htm)
- [Bank of Korea monetary policy decision, 27 Aug 2026](https://www.bok.or.kr/eng/bbs/E0000634/view.do?nttId=11064193&oldMenuNo=400007&menuNo=400069&programType=newsDataEng&depth=400069&relate=Y)
- [IEA Oil Market Report, March 2026](https://www.iea.org/reports/oil-market-report-march-2026)
- [Estrella and Trubin, NY Fed Current Issues 12-5](https://www.newyorkfed.org/medialibrary/media/research/current_issues/ci12-5.pdf)

#### Papers

- [Daniel and Moskowitz (2016), Momentum crashes, JFE](https://www.kentdaniel.net/papers/published/jfe_16.pdf)
- [Barroso and Santa-Clara (2015), Momentum has its moments](https://novaresearch.unl.pt/en/publications/momentum-has-its-moments/)
- [Moreira and Muir (2017), Volatility-managed portfolios](https://amoreira2.github.io/alan-moreira.github.io/VolPortfolios_published.pdf)
- [Nagel (2012), Evaporating liquidity](https://www.nber.org/system/files/working_papers/w17653/w17653.pdf)
- [Asness, Moskowitz and Pedersen (2013), Value and momentum everywhere](https://w4.stern.nyu.edu/facdir/lpederse/papers/ValMomEverywhere.pdf)
- [Ilmanen et al. (2021), How do factor premia vary over time?](https://www.aqr.com/Insights/Research/Journal-Article/How-Do-Factor-Premia-Vary-Over-Time-A-Century-of-Evidence)
- [Benigno and Eggertsson (2023), the nonlinear Phillips curve](https://www.nber.org/papers/w31197)
- [Bailey and López de Prado, the deflated Sharpe ratio](https://www.davidhbailey.com/dhbpapers/deflated-sharpe.pdf)
- [Shu, Yu and Mulvey, statistical jump models (arXiv preprint)](https://arxiv.org/html/2402.05272v3)
- [BIS Working Paper 1282, market whiplash after the 2025 tariff shock](https://www.bis.org/publications/working-paper-1282-market-whiplash-after-2025-tariff-shock-event-targeted-var-approach)

#### Courses and textbooks

- [Cochrane, Asset Pricing class (Chicago)](https://www.johnhcochrane.com/asset-pricing)
- [MIT OCW 14.384 Time Series Analysis](https://ocw.mit.edu/courses/14-384-time-series-analysis-fall-2013/)
- [Steinsson, monetary policy lecture (Berkeley)](https://eml.berkeley.edu/~jsteinsson/teaching/Lecture17MonetaryPolicy.pdf)
- [Maggiori and Schreger, international macro-finance syllabus](https://globalcapitalallocation.s3.us-east-2.amazonaws.com/International_Macro+_Finance_Syllabus.pdf)
- [Sheppard, financial econometrics notes (Oxford)](https://www.kevinsheppard.com/teaching/mfe/notes/)
- 이종화·김진일, 동태적 거시경제학 ch.1–9; Blanchard and Johnson, Macroeconomics 6e; Kirchgässner, Wolters and Hassler, Introduction to Modern Time Series Analysis 2e; Dutta, Strategies and Games

#### Events (press, used for dating)

- [Seoul Economic Daily, KOSPI whipsaw, 31 Jul 2026](https://en.sedaily.com/finance/2026/07/31/kospi-whipsaws-18-percent-plunge-over-three-days-then-18)
- [Korea Times, record September exports](https://www.koreatimes.co.kr/economy/20261001/koreas-monthly-exports-hit-1209-bil-in-sept-on-record-chip-sales)
- [Seoul Economic Daily, foreign selling](https://en.sedaily.com/finance/2026/10/01/foreign-investors-dump-135-trillion-won-in-five-months)

#### Limitations

- Macro series are latest vintage, not as first published.
- Factor tests are gross of costs unless marked; KRX investor flows were not available.
- Verdicts are indicative, computed outside QUANTGEN's own gate.

QUANTGEN macro research · prepared 2 Oct 2026 for GEON KOH · research only, not investment advice.