# P6: Technical and fundamental anomalies outside the US (Korea first, then Japan, China A, Taiwan, EM) and what QUANTGEN should do

As of 2 October 2026 (Asia/Seoul). These notes are by panel member P6, a fictional composite persona. Every number carries its market, period, in-sample (IS) or out-of-sample (OOS) status, and gross or net basis.

"Local check" means P6's own indicative run on the survivorship-free KRX marcap file (KOSPI + KOSDAQ common stocks, 1998-2026). The scripts and CSVs are in `/home/claude/datalab/scripts/p6_indicative/` (see `README.txt` there). Read every local number with these caveats:
- It is in-sample. About 60 configurations were tried and no deflation was applied.
- Returns are price returns from KRX `ChangesRatio`, which is split-adjusted but excludes cash dividends.
- Each monthly sort is decided at the month-end close and earned the following month.
- Costs are 35 bp per side on every unit of weight change, with a 2x stress at 70 bp.
- The universe excludes preferred shares and SPACs. It requires at least 15 traded days in the month, a close of at least KRW 1,000, and a market cap above the 20th percentile, unless stated otherwise.
- Holding month January 2001 is excluded. It is an outlier: the December-2000 loser decile rose 111.8% in January 2001.

These are evidence for the data lab to re-run, not gate results.

## Q0. Persona line and position summary

### Takeaway
**Persona line.** P6 is the "Professor of International and Korean Finance", a fictional composite persona and not a real person. The persona is a Korean finance professor who has published in Korean (KCI-indexed) and international journals on cross-sectional anomalies, investor-type trading and market microstructure in Korea and Asia. P6 argues from local replication: a US factor prior is not evidence for KRX until it survives KRX data, KRX costs and KRX market rules.

**Position summary.**
1. Outside the US, the anomaly family that travels best is low risk and lottery, not momentum. In Griffin-Ji-Martin's 40-country sample, 6/6 momentum is insignificant in every East Asian market: Korea -0.76%/month, Japan 0.02, Taiwan 0.01, China -0.01. Low-volatility and MAX effects, by contrast, are large in China, Korea and emerging markets.
2. In Korea the lottery family (MAX, volatility, turnover; pairwise correlations 0.83-0.93) is the strongest signal both before and after QUANTGEN's costs. The local check gives an equal-weighted long-short Sharpe of 0.6-0.9 net of 35 bp per side over 2001-2026, in-sample. But nearly all of it sits in the short leg. For a read-only, long-only desk it is therefore an exclusion screen, not a tilt: worth about +0.23%/month equal-weighted and +0.04%/month capped value-weighted.
3. Korean 12-1 momentum is contested.
   - The headline KJFS result, -6.13%/month in high-turnover stocks over 2000-2019, does not replicate on survivorship-free KRX data. P6's approximate replication of the same design gives +0.58% to +1.42%/month; an exact replication is requested as DC-P6-02.
   - Momentum still lost money in 2017-2019 and 2021, and crashed by -22.3% in July 2026.
   - The intermediate-horizon (12-7) and 52-week-high variants behave better, but their margin after costs is thin.
4. One-month reversal is real before costs: 0.86%/month, t 2.70.
   - It has fallen by roughly two thirds to three quarters since 2001-09 (1.55 to 0.54 and 0.41%/month).
   - It needs 3.5x monthly turnover and is negative at 35 bp per side.
   - The prior design's volume-filtered 5-day reversal has the wrong sign in Korea: high-volume weekly moves do not reverse.
5. The prior design's strong Korean flow weight is not supported for close-to-close trading. Lagged foreign and institutional net buying predicts the next open but not the next close, and copying foreign buying underperformed KOSPI.
6. The fundamental candidates are earnings drift and value plus profitability. Both are cheap to hold, and both still need a point-in-time DART test.
   - Earnings drift: a 60-day spread of 4.8% over 2002-2017, driven by retail investors selling into good news.
   - Value plus profitability: HML 1.05%/month and RMW 0.65%/month over 2002-2015.
7. Market structure changes the answer.
   - Shorting has been banned for 42 months since 2008, and for small caps for five continuous years (2020-2025).
   - Price limits have been ±30% since June 2015.
   - A 0.20% sell tax applies from 2026.
   - Estimated half-spreads are about 27-39 bp outside the top 5% of caps.
   - KOSPI is effectively a two-stock market (Samsung and SK hynix are 55.5% of its cap). A value-weighted low-risk tilt lagged the value-weighted universe by 20.3 points in 2025 and 46.4 points in 2026 to date.
8. Outside Korea:
   - Japan keeps value at 3, with momentum allowed only when paired with value or dynamically scaled.
   - China A and Taiwan get 0 for cross-sectional momentum.
   - China A gets 3 for low volatility.
9. QUANTGEN should:
   - cut Korean short-term reversal and flow from 3 to 1;
   - raise quality from 1 to 2;
   - cut low volatility as a tilt from 2 to 1;
   - add a lottery-exclusion screen at 3 and a 52-week-high tilt at 2;
   - cut earnings drift from 3 to 2 until a point-in-time DART test passes;
   - run the five experiments in Q6 before any Korean stock card is believed.

### Cited Findings
- 6/6 momentum by country, to December 2000, gross: Korea -0.76%/month (t -0.80), Japan 0.02 (0.10), Taiwan 0.01 (0.02), China -0.01 (-0.02). The Asia average is 0.32 (t 1.64), against 0.77 (t 8.15) for Europe. — [Griffin, Ji, Martin 2003, JF (PDF copy)](https://gyanresearch.wdfiles.com/local--files/alpha/Momentum.pdf)
- Korea, July 2000 to June 2019, equal-weighted, gross, IS: in high-turnover stocks, 12-1 momentum winners minus losers is -6.13%/month (t -4.76). — [Eom, Chang, Kang, Lee, Park 2020, KJFS 49(4)](https://www.e-kjfs.org/journal/view.php?number=901). The local replication of this design gives +0.58%/month (t 1.50) on all stocks and +1.42% (t 3.52) excluding the smallest 20% of caps. — [P6 local check p6_eom_x01.py](/home/claude/datalab/scripts/p6_indicative/p6_eom_x01.py)
- Korea, February 2001 to September 2026, monthly decile long-short, local IS (details in Q2):
  - Low-volatility, equal-weighted: 2.40%/month gross (t 6.31); Sharpe net of 35 bp 0.91.
  - Low-MAX, equal-weighted: 1.95%/month (t 6.55); Sharpe net of 35 bp 0.59.
  - One-month reversal, equal-weighted: 0.86%/month gross (t 2.70); Sharpe net of 35 bp -0.22.
  - Source: [P6 local check p6_sorts.py](/home/claude/datalab/scripts/p6_indicative/p6_sorts.py)

### Inferences
- The US prior (cross-sectional momentum at 3) is the wrong starting point for Korea, Japan, Taiwan and China A. The low-risk and lottery family and fundamental drift are the right starting points.

### Gaps
- None at summary level; see the Gaps under Q1 to Q7.

## Q1. How do momentum and reversal behave outside the US (Rouwenhorst; Griffin-Ji-Martin; Chui-Titman-Wei; Asness on Japan; Fama-French 2012; Cakici-Fabozzi-Tan; Hanauer-Lauterbach; Jacobs-Müller; Liu-Stambaugh-Yuan; China reversal)?

### Takeaway
Momentum is the least portable major anomaly into East Asia:
- It is insignificant in Japan, Korea, Taiwan and China in every multi-country study found.
- It survives in Japan only when paired with value or scaled dynamically.
- It is replaced by short-term reversal in retail-dominated, short-constrained markets. China A versus B shares is the cleanest natural experiment.

Outside the US, anomalies did not decay after publication (Jacobs-Müller). Korea's local data nevertheless show strong time decay.

### Cited Findings
- **Rouwenhorst (1998).** Found out-of-sample momentum in many European countries (cited through the synthesis). — [Subrahmanyam 2018 momentum synthesis, PBFJ (PDF)](https://anderson-review.ucla.edu/wp-content/uploads/2021/03/Subra2018_Momentum.pdf)
- **Rouwenhorst (1999), emerging markets.**
  - Momentum, small-cap and value premia are present.
  - There is no evidence that high-beta stocks outperform.
  - The return factors are strongly correlated with share turnover.
  - Source: [Rouwenhorst 1999, JF 54(4), RePEc abstract](https://ideas.repec.org/a/bla/jfinan/v54y1999i4p1439-1464.html)
- **Griffin-Ji-Martin (2003), 40 countries to December 2000.** Design: rank on months t-7 to t-2, hold 6 months, top versus bottom 20%. Monthly winner-minus-loser returns, gross, IS:

  | Market | %/month | t |
  |---|---|---|
  | Korea | -0.76 | -0.80 |
  | Japan | 0.02 | 0.10 |
  | Taiwan | 0.01 | 0.02 |
  | China | -0.01 | -0.02 |
  | Hong Kong | 0.41 | 0.97 |
  | India | 0.80 | 1.74 |
  | Indonesia | -1.00 | -1.16 |
  | Asia ex-Japan | 0.40 | 1.35 |
  | Europe | 0.77 | 8.15 |
  | Americas ex-US | 0.78 | 3.13 |

  Macro risk factors do not explain momentum. — [GJM 2003 (PDF copy)](https://gyanresearch.wdfiles.com/local--files/alpha/Momentum.pdf); [JF abstract page](https://onlinelibrary.wiley.com/doi/abs/10.1046/j.1540-6261.2003.00614.x)
- **Chui-Titman-Wei (2010).** Hofstede individualism is positively associated with momentum profits, trading volume and volatility. The relation survives controls for analyst dispersion, transaction costs, firm size and volatility. — [Chui, Titman, Wei 2010, JF, EconPapers abstract](https://econpapers.repec.org/RePEc:bla:jfinan:v:65:y:2010:i:1:p:361-392)
- **Fama-French (2012), November 1989 to March 2011, gross, IS.**

  | Region | WML %/month (t) | HML %/month (t) |
  |---|---|---|
  | North America | 0.64 (1.91) | 0.33 (1.48) |
  | Europe | 0.92 (3.38) | 0.55 (3.51) |
  | Japan | -0.08 (0.25) | 0.48 (2.59) |
  | Asia Pacific | 0.69 (2.24) | 0.62 (3.04) |

  Japan's WML is close to zero for both small and big stocks. The authors call chance "a serious contender" for the Japan result. — [Fama-French 2012, JFE (PDF)](https://www.johnhcochrane.com/s/Fama_French_size_value_momentum_JFE.pdf)
- **Asness-Moskowitz-Pedersen (2013), Japan stocks, January 1974 to July 2011, gross, IS.**
  - Value: 12.0%/year (t 4.31), Sharpe 0.79.
  - Momentum: 1.7%/year (t 0.57), Sharpe 0.09.
  - 50/50 combination: 6.4%/year (t 4.28), Sharpe 0.78.
  - Correlation between value and momentum: -0.64.
  - For comparison, US momentum earned 5.4%/year (t 2.08), Sharpe 0.33.
  - Source: [AMP 2013, JF (PDF)](https://w4.stern.nyu.edu/facdir/lpederse/papers/ValMomEverywhere.pdf)
- **Asness (2011).** Price momentum in Japan "made no money for near 30 years". Studied as a system with value, which is strongly negatively correlated with it, momentum works in Japan. — [AQR summary of Asness 2011, JPM](https://www.aqr.com/Insights/Research/Journal-Article/Momentum-in-Japan-The-Exception-that-Proves-the-Rule)
- **Hanauer (2014).** Japanese momentum is higher when the market stays in the same state. Japan's low average comes from more frequent market transitions, not a different momentum effect. — [Hanauer 2014, IRF, RePEc](https://ideas.repec.org/a/bla/irvfin/v14y2014i1p141-160.html)
- **Iwanaga-Hirose-Yoshida (2023/24), Japan.** Momentum splits into high-to-price and price-to-high components. High-to-price has lower downside risk and a higher Sharpe. Momentum drawdowns come mainly from price-to-high in bear markets. — [APFM 31(2)](https://link.springer.com/article/10.1007/s10690-023-09413-y)
- **Chang et al. (2018), cited by Subrahmanyam.** Standard momentum is absent in Japan, but residual-return momentum is present. — [Subrahmanyam 2018 (PDF)](https://anderson-review.ucla.edu/wp-content/uploads/2021/03/Subra2018_Momentum.pdf)
- **Daniel-Moskowitz dynamic momentum (Table 11), as recorded by the companion macro research.** It raises Japan's WML Sharpe from 0.067 to 0.416, and Europe's from 0.462 to 1.130. — [QUANTGEN_MACRO_INTEGRATION.md (project doc, N-08 row)](claude/QUANTGEN_MACRO_INTEGRATION.md)
- **Cakici-Fabozzi-Tan (2013), 18 emerging markets, January 1990 to December 2011.**
  - Value is present in all of them.
  - Momentum is present in all but Eastern Europe.
  - Local factors price returns better than US or global factors, which indicates segmentation.
  - Source: [CFT 2013, EMR, EconPapers](https://econpapers.repec.org/article/eeeememar/v_3a16_3ay_3a2013_3ai_3ac_3ap_3a46-65.htm)
- **Hanauer-Lauterbach (2019), 28 emerging markets, July 1995 to June 2016.**
  - Cash-flow-to-price, gross profitability, composite equity issuance and momentum are robust in equal- and value-weighted sorts and in regressions.
  - There is no positive risk-return relation.
  - Alternative factor definitions beat the FF5 definitions out of sample.
  - Source: [HL 2019, EMR](https://www.sciencedirect.com/science/article/abs/pii/S1566014118304230)
- **Jacobs-Müller (2020).** 241 anomalies, 39 markets, more than 2 million anomaly-country-months. They find "the United States is the only country with a reliable post-publication decline", and read it as arbitrage barriers and mispricing. — [JFE 135(1), RePEc](https://ideas.repec.org/a/eee/jfinec/v135y2020i1p213-230.html)
- **Liu-Liu-Ma (2011).** 52-week-high momentum is profitable in 18 of 20 markets (significant in 10), independent of Jegadeesh-Titman momentum, and does not reverse in the long run. It is no longer significant in most markets after transaction costs. Individualism does not explain it. — [JIMF 30(1), RePEc](https://ideas.repec.org/a/eee/jimfin/v30y2011i1p180-204.html)
- **China, Liu-Stambaugh-Yuan (2019), 2000-2016.**
  - "There is no momentum effect in China."
  - Past returns over various windows predict future returns negatively.
  - One-month reversal CAPM alpha: 1.49%/month (t 3.07); size-neutral 1.66 (t 3.68). Gross, IS.
  - Source: [LSY, NBER w24458 (PDF)](https://www.nber.org/system/files/working_papers/w24458/w24458.pdf); [Wharton PDF](https://faculty.wharton.upenn.edu/wp-content/uploads/2018/03/Size-and-Value-in-China.pdf)
- **China, Chui-Subrahmanyam-Titman (2001-2018): A shares versus B shares.** These are the same firms with different investor bases.
  - Momentum: A shares 0.27%/month (insignificant); B shares 1.15% value-weighted (t 3.33).
  - Monthly reversal: A shares 1.2% equal-weighted (t 4.93); insignificant in B shares.
  - A-share reversal is driven by positive returns, consistent with short-sale constraints.
  - Retail is about 85% of A-share volume (2015).
  - Source: [NBER w29453 (PDF)](https://www.nber.org/system/files/working_papers/w29453/w29453.pdf)
- **China, Jansen-Swinkels-Zhou, 2008-2020, efficient sorts.** Reversal 1.41%/month (t 4.09); momentum 0.04 (t 0.11). — [JSZ "More powerful tests" (PDF)](https://www.cfrn.com.cn/uploads/fileupload/a86579f7d6fb4328b45fa45156d074f7/paper/2a7aea538ad943c4b4220e51ec6dbfe5.pdf). Their 2000-2019 study finds strong residual momentum and reversal, with strong out-of-sample evidence for residual reversal and return seasonality. — [JSZ 2021, PBFJ 68, RePEc](https://ideas.repec.org/a/eee/pacfin/v68y2021ics0927538x21001141.html)
- **Taiwan.**
  - Taiwan is "widely documented" as an exception to momentum (1982-2020). Momentum restricted to persistent winners and losers earns up to 0.756%/month. — [Chen, Hsieh, Lee 2023, PBFJ](https://www.sciencedirect.com/science/article/abs/pii/S0927538X23000094)
  - Over 1990-2011, 6- and 12-month momentum is insignificant, while short-term reversal is significant in multiple regressions. — [Cakici, Topyan, Wang (PDF)](https://content.manhattan.edu/school-of-business/research-papers/taiwan_stock_exchange_cakici_topyan_wang_cover.pdf)
- **Chen-Stivers-Sun (2024).** Short-term reversal weakens as turnover and the prior month's price-to-52-week-high ratio rise. Their reading:
  - Reversal is compensation for liquidity provision in low-turnover stocks far from their high.
  - Anchoring on the 52-week high causes underreaction, and so momentum, when turnover is high.
  - The abstract does not name the market.
  - Source: [JEF 79, RePEc](https://ideas.repec.org/a/eee/empfin/v79y2024ics0927539824000902.html)

### Inferences
- No multi-country study found shows significant standalone 12-1 or 6/6 momentum in Japan, Korea, Taiwan or China A. The Asian regional average is about 40% of Europe's (0.32 versus 0.77%/month). This matches Chui-Titman-Wei's low-individualism prior.
- Short-term reversal replaces momentum where retail dominates and shorting is constrained. China's A/B split shows the clientele effect directly, so it is the best external guide to Korea.
- In Japan the momentum failure is a value-momentum system effect. Japanese momentum should only ever enter QUANTGEN paired with value, as residual momentum, or with dynamic scaling.
- Jacobs-Müller argue against a universal publication-decay haircut outside the US. However, Korea's own anomalies fell by roughly one half (low volatility, MAX) to three quarters (one-month reversal) after 2001-09 (Q2), so the 60% live haircut (gate step 9) should stay for Korea. The cause is time and maturation rather than publication.

### Gaps
- Rouwenhorst (1998) is cited only through Subrahmanyam's synthesis; the RePEc and EconPapers pages returned 404.
- Chui-Titman-Wei's country-level numbers and Korea's Hofstede score were not obtained (the PDF is disallowed by robots.txt; the Hofstede site failed).
- The 2021 Jansen-Swinkels-Zhou full table (2000-2019) was not obtained (SSRN rate limit).
- The Ken French international files could not be downloaded from this sandbox (egress 403). There is therefore no out-of-sample update after March 2011 of Fama-French 2012's Japan and Asia-Pacific numbers (DC-P6-08).
- No net-of-cost momentum or reversal evidence was found for Japan, Taiwan or China.

## Q2. Korea in depth: momentum, reversal, 52-week high, MAX/lottery, low volatility, value/P-B, quality, earnings drift, investor flows

### Takeaway
On local KRX data (2001-2026, in-sample) the ranking after QUANTGEN's 35 bp costs is:
1. Low volatility, low turnover and low MAX: all one lottery factor.
2. Intermediate momentum (12-7).
3. 52-week-high nearness.
4. 12-1 momentum.
5. One-month reversal and size, which are negative net.

The lottery premium lives in the short leg, which QUANTGEN cannot hold. Long-only, it works as an exclusion screen.

The literature's Korean headline, "negative momentum and reversal carry-over", does not replicate on survivorship-free data. Momentum is fragile, not reliably negative.

Earnings drift (retail investors trading against the news) and value plus profitability are the best-documented fundamental signals. Flow signals predict the next open, not the next close.

### Cited Findings

**Momentum and short-term reversal (literature)**
- **Eom, Chang, Kang, Lee, Park 2020, KJFS 49(4).** Design (Table 3): KOSPI + KOSDAQ, July 2000 to June 2019; 12-month formation skipping month t-1; 1-month hold; top and bottom 30% turnover groups by period-average turnover; 3x5 sorts; financials, non-December fiscal years and the highest-volatility decile excluded. Returns are monthly averages in excess of the risk-free rate; the weighting is not stated explicitly (likely equal). Gross, IS:
  - High-turnover winners minus losers: -6.13%/month (t -4.76). Losers earn 6.85% (t 4.87); winners 0.73% (t 1.05).
  - Low-turnover winners minus losers: -0.53% (t -1.17).
  - 6-1 high turnover: -5.52% (t -4.51). 3-1: -2.89% (t -2.83).
  - Source: [KJFS article page](https://www.e-kjfs.org/journal/view.php?number=901); [KJFS PDF](https://www.e-kjfs.org/upload/pdf/KJFS-2020-08-49-4-589.pdf)
- **Eom and Park (2021).** Negative momentum profits occur in high-attention stocks, and the reversal comes from firm-specific rather than common return components. — [RIBAF 57, RePEc](https://ideas.repec.org/a/eee/riibaf/v57y2021ics0275531921000258.html)
- **Chae and Eom (2009, APJFS), "Negative Momentum Profit in Korea and its Sources".** The title was confirmed, but the abstract could not be fetched (403). — [Wiley](https://onlinelibrary.wiley.com/doi/10.1111/j.2041-6156.2009.tb00013.x)
- **Sim and Kim (2021), JDQS 29(3), January 1999 to February 2021.**
  - pret(12,7) momentum FF5 alpha: 0.531%/month (t 2.05). pret(6,2): -0.084% (t -0.28).
  - Return coefficients: one-month r(-1) -2.950 (t -3.77); r(-2) -1.108 (t -2.01).
  - Reversal-strategy FF5 alpha: 1.275%/month (t 3.22) at k=1; 0.514% (t 1.99) at k=2.
  - Conclusion: the term structure of momentum is a two-month reversal effect.
  - Gross, IS. Source: [Emerald JDQS](https://www.emerald.com/jdqs/article/29/3/174/206550/The-effect-of-short-term-return-reversals-on)
- **Bae and Lee (2021), JDQS 29(1), July 2001 to June 2019, value-weighted.**
  - Winners minus losers: 0.76%/month (t 1.58) at top/bottom 10%; 1.06% (t 2.53) at 20%; 0.83% (t 2.43) at 30%.
  - These are significant after CAPM, FF3 and FF5 adjustment.
  - A duration factor explains 54-67% of momentum's variation.
  - Source: [Emerald JDQS](https://www.emerald.com/jdqs/article/29/1/49/195316/Illiquidity-duration-and-momentum-profits-evidence)
- **Ryu (2021), JKDAS 23(4).** In Korea, 52-week-high strategies (George-Hwang and RR) beat Jegadeesh-Titman momentum after risk adjustment. The skip period matters. — [Kyobo Scholar abstract](https://scholar.kyobobook.co.kr/article/detail/4010028467563)
- **SK Securities (sell-side, 30 April 2025).**
  - Practitioner claim: "since 2020, as retail influence rose, short-term momentum exists" in Korea.
  - On KS200 + KQ150, a "leading" price-and-volume group had a Sharpe of 0.964 and a "lagging" group -1.728.
  - The backtest is not fully specified. T2/T3 claim to be tested.
  - Source: [SK Securities report (PDF)](https://www.sks.co.kr/data1/research/qna_file/20250429151923625_0_ko.pdf)

**Momentum and short-term reversal (local check, KRX marcap)**

Monthly top-minus-bottom deciles, February 2001 to September 2026 holding months. "EW" is equal-weighted and "VW" value-weighted. "net35" deducts 35 bp per side on turnover; "SR" is annualised Sharpe.

| Signal | EW gross %/month (t) | EW Sharpe net35 / 2x | VW gross %/month (t) | VW Sharpe net35 | Turnover L+S per month | 2001-09 / 2010-19 / 2020-26 (EW %/month, t) |
|---|---|---|---|---|---|---|
| 1-month reversal | 0.86 (2.70) | -0.22 / -0.94 | 0.04 (0.09) | -0.51 | 3.50 | 1.55 (2.8) / 0.54 (1.2) / 0.41 (0.6) |
| 12-1 momentum | 0.76 (2.37) | 0.18 / -0.09 | 1.66 (2.71) | 0.39 | 1.31 | 1.44 (2.7) / 0.41 (0.8) / 0.40 (0.7) |
| 12-7 momentum | 1.30 (4.91) | 0.54 / 0.10 | 1.46 (2.75) | 0.30 | 1.66 | 1.96 (4.5) / 0.95 (2.3) / 0.95 (1.8) |
| 52-week-high nearness | 1.23 (3.22) | 0.30 / 0.01 | 1.44 (2.69) | 0.28 | 1.71 | 1.37 (1.7) / 1.19 (2.4) / 1.08 (1.6) |

  Source: [P6 local check p6_sorts.py and CSV](/home/claude/datalab/scripts/p6_indicative/p6_krx_monthly_anomalies.csv). Keeping delisting-window returns changes no mean by more than 0.03%/month. — [p6_krx_monthly_anomalies_delist.csv](/home/claude/datalab/scripts/p6_indicative/p6_krx_monthly_anomalies_delist.csv)
- **Local replication of Eom et al.'s design.** Top and bottom 30% period-average turnover, highest-volatility decile dropped, 1-month hold, equal-weighted raw returns; holding months July 2000 to June 2019, excluding January 2001 (n = 227):

  | Universe | Horizon | High-turnover W-L %/month (t) | Losers / winners | Low-turnover W-L %/month (t) |
  |---|---|---|---|---|
  | All caps | 12-1 | +0.58 (1.50) | 0.00 / 0.58 | +0.59 (1.92) |
  | Excluding smallest 20% | 12-1 | +1.42 (3.52) | -1.02 / 0.39 | +0.82 (2.68) |
  | All caps | 3-1 | -0.37 (-1.01) | n/a | n/a |
  | Excluding smallest 20% | 3-1 | -0.04 (-0.10) | n/a | n/a |

  In the paper, losers earn +6.85%/month. In the replication they earn -1.02% to 0.00%. — [P6 local check p6_eom_x01.py](/home/claude/datalab/scripts/p6_indicative/p6_eom_x01.py)
- **By trailing-12-month-turnover tercile** (excluding the smallest 20% of caps), 12-1 momentum winners minus losers:
  - T1 (lowest turnover): 0.95%/month (t 3.17).
  - T2: 1.10% (t 2.79).
  - T3 (highest turnover): 0.80% (t 1.90). By period: 1.52 (2.2) in 2001-09, 0.04 (0.1) in 2010-19, 0.98 (1.2) in 2020-26.
  - In T3, losers minus the universe earn -1.16% (t -4.9): high-attention losers keep losing, not reversing.
  - 6-1 momentum in T3: -0.43% (t -1.11). In the T3 tercile of the all-stocks universe (micro-caps included): -0.74% (t -2.11), and -1.50% (t -2.3) in 2020-26.
  - One-month reversal is concentrated in T3: -1.48%/month (t -3.14). Low-turnover stocks: -0.51% (t -2.02).
  - Source: [P6 local check p6_split_f01.py](/home/claude/datalab/scripts/p6_indicative/p6_split_f01.py)
- **Skipping the most recent month matters.** Measured in the lowest and highest 1-month-turnover terciles, on both universes. Without a skip (12-0), momentum winners minus losers is -0.02 to +0.49%/month (all t < 1.6). With the one-month skip (12-1), it is +0.21 to +1.38%/month (t up to 3.25). — [P6 local check p6_final_f01.py](/home/claude/datalab/scripts/p6_indicative/p6_final_f01.py)
- **Weekly 5-day reversal** (the daily-swing proxy for the prior design's ST-rev). Weekly long last-week losers, short winners, equal-weighted deciles, February 2001 to September 2026:
  - Gross: 0.30%/week (t 3.8), Sharpe 0.80. 2001-09: 0.64%/week (Sharpe 1.44). 2020-26: -0.03%/week.
  - Net of 35 bp per side: Sharpe -2.37 (3.25x weekly turnover).
  - With the prior design's volume filter (week's average traded value over the prior 20-day average above 1.5): gross 0.03%/week (t 0.2).
  - Long-only losers versus the universe under the filter: -0.34%/week (t -4.1). High-volume losers continue down.
  - Source: [P6 local check p6_weekly_f01.py](/home/claude/datalab/scripts/p6_indicative/p6_weekly_f01.py)

**52-week high and anchoring**
- **Goh and Jeon (2017).** In Korea, earnings drift after positive earnings is pronounced for stocks near their 52-week high. Individuals buy stocks far from the high around announcements. — [PBFJ 44, RePEc](https://ideas.repec.org/a/eee/pacfin/v44y2017icp150-159.html)
- **Local check, long-only nearness-to-high tilt.** Top 52-week-high-ratio quintile, equal-weighted, monthly:
  - Net of 35 bp: +0.34%/month over the equal-weighted universe (t 2.31); Sharpe 0.57 versus 0.31; turnover 0.78 per month.
  - At 2x costs: only +0.09%/month.
  - Excluding lottery stocks as well: +0.55%/month (t 3.63) net of 35 bp; +0.31 at 2x; Sharpe 0.72.
  - Capped value-weighted (5% cap): +0.06%/month (t 0.40), and negative at 2x.
  - Source: [P6 local check p6_excl2.py](/home/claude/datalab/scripts/p6_indicative/p6_excl2.py)

**MAX / lottery, low volatility, turnover**
- **Cheon and Lee (2018), Korea, January 1992 to June 2016.**
  - Value-weighted low-minus-high MAX abnormal return: 2.40%/month, versus 0.66% in the US.
  - The overpayment is 2.23% in high-volatility periods and 0.13% in calm ones.
  - Source: [PBFJ](https://www.sciencedirect.com/science/article/abs/pii/S0927538X17304870)
- **Goh and Kim (2024), JDQS 32(2), July 2000 to December 2020.**
  - Equal-weighted high-minus-low MAX: -2.08%/month (t -5.01); FF3 alpha -2.00 (t -4.61).
  - The effect is significant only among overpriced stocks: alpha -2.78 (t -5.79) in the most overpriced quintile.
  - Individuals' buying concentrates in overpriced high-MAX stocks.
  - Source: [Emerald JDQS](https://www.emerald.com/jdqs/article/32/2/159/1236382/The-role-of-arbitrage-risk-in-the-MAX-effect)
- **Cho (2021), JDQS 29(1), 2000-2016.** High-minus-low MAX: -1.94%/month (t -5.10) equal-weighted; -1.89% (t -3.40) value-weighted. The standalone effect is insignificant once idiosyncratic volatility is controlled. — [Emerald JDQS](https://www.emerald.com/jdqs/article/29/1/29/195322/Extreme-returns-and-idiosyncratic-risks-evidence)
- **Eom, Lee, Park, Jang, Park (2014), KJFS 43(4), July 1992 to June 2012.** Idiosyncratic volatility is significantly negatively related to future returns after controls for reversal, momentum and turnover. The effect concentrates in down markets and outside January. — [DBpia abstract](https://dbpia.co.kr/Journal/articleDetail?nodeId=NODE07228272)
- **Local check, long-short (equal-weighted unless noted), February 2001 to September 2026:**

  | Signal | Gross %/month (t) | Sharpe net35 / 2x | Positive years |
  |---|---|---|---|
  | Low volatility (63-day) | 2.40 (6.31) | 0.91 / 0.72 | 85% |
  | Low volatility, VW | 2.29 (4.09) | 0.63 / n/a | n/a |
  | Low turnover | 2.42 (6.00) | 0.84 / 0.60 | 88% |
  | Low MAX | 1.95 (6.55) | 0.59 / -0.02 | 85% |

  - Pairwise correlations among the three are 0.83 to 0.93.
  - For every one, the long leg minus the universe is small (low volatility: +0.25%/month, t 1.25). The short leg (the riskiest decile) minus the universe is about -1.6% to -2.4%/month.
  - Source: [P6 local check p6_sorts.py](/home/claude/datalab/scripts/p6_indicative/p6_sorts.py); [p6_regime_f01.py](/home/claude/datalab/scripts/p6_indicative/p6_regime_f01.py)
- **Local check, low-risk as a long-only tilt.** A composite of low volatility, low MAX and low turnover, top quintile, February 2001 to September 2026:
  - Equal-weighted, net of 35 bp: +0.12%/month over the equal-weighted universe (t 0.75).
  - Value-weighted, net: -0.50%/month versus the value-weighted universe (t -2.16). Annual relative returns of -20.3 points in 2025 and -46.4 points in 2026.
  - Source: [P6 local check p6_final_hold.py](/home/claude/datalab/scripts/p6_indicative/p6_final_hold.py)
- **Local check, lottery exclusion (long-only).** Drop the worst-decile composite stocks, about 135 of about 1,361 per month:
  - Equal-weighted: +0.23%/month net of 35 bp (t 8.25); +0.20 at 2x; 92% of years positive; +0.18 in 2020-26. Sharpe 0.31 to 0.44.
  - Value-weighted with a 5% cap: +0.04%/month (t 3.46).
  - Value-weighted excluding Samsung and SK hynix: +0.04%/month (t 3.36).
  - Source: [P6 local check p6_excl2.py](/home/claude/datalab/scripts/p6_indicative/p6_excl2.py); [p6_exclusion_hold.py](/home/claude/datalab/scripts/p6_indicative/p6_exclusion_hold.py)

**Size, value, quality**
- **Kang (Korea, July 2002 to June 2015, 2x3 sorts).**
  - SMB: 0.16%/month (t 0.45), insignificant.
  - HML: 1.05% (t 3.41).
  - RMW (quarterly profitability): 0.65% (t 2.75).
  - CMA: 0.66% (t 3.57).
  - Gross, IS. Source: [KFA 2016 conference paper (PDF)](http://www.korfin.org/korfin_file/forum/2016co-conf19-3.pdf)
- **Kim (2021).** Risk premia exist in Korea for size, value, momentum, profitability and low risk, with size the highest. Removing unintended negative factor exposures improves multifactor returns. — [PBFJ 67](https://www.sciencedirect.com/science/article/abs/pii/S0927538X21000652). This conflicts with Kang's and P6's insignificant size premium.
- **Local check, size.** Small-minus-big deciles, equal-weighted: 0.28%/month (t 0.87); Sharpe net of 35 bp -0.02. Annual sums of -29.3 points in 2025 and -25.7 points in 2026 (to September). — [P6 local check](/home/claude/datalab/scripts/p6_indicative/p6_krx_monthly_anomalies.csv)
- **Mispricing and investor types.** Kim, Kang and Roh (2025) build a mispricing measure from 26 significant Korean anomalies. Individuals are the uninformed traders who create the anomalies. Only asset-management institutions and registered foreigners exploit them. — [PBFJ 90, RePEc](https://ideas.repec.org/a/eee/pacfin/v90y2025ics0927538x24003743.html)

**Earnings drift**
- **Shin, Shin and Kim (2019), Korea, 2002Q4-2017Q4.**
  - Unconditional 60-day market-adjusted drift spread: 4.80% (t 9.35).
  - 6.93% (t 8.19) when market sentiment trends up; 3.49% when it trends down.
  - Gross, IS. Source: [Sustainability 11(18), MDPI](https://www.mdpi.com/2071-1050/11/18/5137)
- **Eom, Hahn and Sohn (2019).** Individuals trade against earnings surprises. Drift exists only in stocks where individuals trade against the news, and it is larger with heavier contrarian individual trading. — [PBFJ 53, RePEc](https://ideas.repec.org/a/eee/pacfin/v53y2019icp379-398.html)
- **Choi and Cho (2021).** More related-party transactions increase drift, especially in chaebol firms (1,286 firm-years, 2015-2018). — [FRL](https://www.sciencedirect.com/science/article/abs/pii/S1544612320317293)

**Investor-type flows**
- **Choe, Kho and Stulz (1999).** Foreigners showed strong positive-feedback trading and herding before the 1997 crisis. The market adjusted quickly to their large sales, with no destabilising effect. — [NBER w6661, RePEc](https://ideas.repec.org:443/p/nbr/nberwo/6661.html)
- **Choe, Kho and Stulz (2001 and 2004/05).**
  - Foreigners sell to domestic investors before large positive abnormal returns and buy before large negative ones.
  - Domestic individuals, not institutions, hold the short-lived edge.
  - Foreign money managers pay 21 bp more on purchases and receive 16 bp less on sales (trade-weighted daily).
  - Source: [NBER w8073](https://www.nber.org/papers/w8073); [NBER w10502](https://www.nber.org/papers/w10502)
- **Kim and Byun (2011), 2003 to April 2011.**
  - Lagged (t-1) foreign and institutional net-buying intensity has a significant negative effect on the next close-to-close return.
  - It has a positive effect on the next close-to-open return.
  - Same-day intensity is positively related to returns.
  - Source: [Korea Science (PDF)](https://koreascience.kr/article/JAKO201103750648232.pdf)
- **Yu and Jang (2012), 22 large caps, 2004-2010.** Following foreign net buying underperformed KOSPI. Following institutions beat KOSPI in 20 of 22 stocks. — [Hanyang ScholarWorks (PDF)](https://hanyang.scholarworks.kr/api/assets/9df82c36-bd3b-4089-af65-b5235f10bb6b/download)
- **Richards (2005).** Foreign flows into six Asian emerging markets show positive-feedback trading, with price impacts "much larger than earlier estimates". — [JFQA, RePEc](https://ideas.repec.org/a/cup/jfinqa/v40y2005i01p1-27_00.html)

### Inferences
- **Momentum.** The "Korean negative momentum" result in Eom et al. (2020) is not robust to a survivorship-free re-run. Likely causes:
  - Their Table 3 reports monthly averages with a 1-month hold and a skip month, so the gap is not a units mismatch (excess-versus-raw returns shift both legs by under 0.5%/month and cannot explain it). More likely it is sample construction: they exclude the top-volatility decile and keep December fiscal-year non-financials only, and their database's handling of delistings and suspended or managed stocks may differ.
  - The robust local facts: short-horizon (3-6 month) momentum is weak or negative in high-turnover stocks, and the most recent month reverses. That is why the skip and the 12-7 window matter.
  - Korea's 12-1 momentum should be treated as "positive on average, fragile, with 2017-21 losses", not "negative".
- **Reversal.** One-month and 5-day reversal is a gross anomaly that QUANTGEN cannot harvest at 35 bp per side. Its edge has fallen about 75% since 2001-09 (1.55 to 0.41%/month; weekly 0.64 to -0.03%/week). The prior design's volume filter selects continuation, not reversal.
- **Lottery and low risk.** This is a short-leg phenomenon, partly because shorting small Korean stocks was banned or impractical for long stretches. It belongs in QUANTGEN as an exclusion screen and a risk flag, not as an alpha tilt. A value-weighted low-risk tilt loses badly in concentrated, momentum-led bull markets (2025-26).
- **Fundamentals.** Earnings drift, value and profitability are the most "fundamental" Korean signals with academic support and low turnover. They are the best candidates for the 35 bp cost structure but need OpenDART point-in-time data.

### Gaps
- Abstracts and results that could not be opened (CAPTCHA, 403 or robots.txt): Ko and Kim, "저변동성 이상현상과 투자전략의 수익성 검증" (KCI ART001885142); Chae and Eom (2009); Lee (2014, APJFS) on news and momentum; KCI papers on 52-week high and crash risk (ART002739222); low-beta and lottery (ART002915381); idiosyncratic-volatility robustness (ART002377110); investor-type predictability (ART001162926).
- No Korean-journal net-of-cost study of short-term reversal was found.
- No Korean quality-composite study (GP/A, accruals, leverage) with post-2015 data was found. Kang's RMW sample ends June 2015.
- Earnings-drift net-of-cost evidence for Korea was not found.
- Dividends are missing from the local returns. This understates value and low-volatility long legs by roughly the dividend-yield spread (not measured).

## Q3. Which Korean market-structure features change the answer (short-sale bans, ±30% limits, transaction tax, retail share, chaebol and Korea discount, Value-up, liquidity)?

### Takeaway
Five structural facts change the answer in Korea:
1. **Shorting has rarely been available.** Full bans covered about 42 months since 2008, and small caps could not be shorted at all from March 2020 to March 2025. Overpricing anomalies (lottery, recent winners) therefore persist on the short side, where QUANTGEN cannot trade anyway.
2. **Price limits are ±30% (since 15 June 2015), with volatility interruptions (VIs).** Limit hits cluster in retail manias: 54 upper-limit hits per 10,000 KOSDAQ stock-days in 2026, against about 20 normally.
3. **Trading tax.** The sell-side tax has been 0.20% since 1 January 2026, up from 0.15%.
4. **Spreads.** Estimated full spreads are 50-80 bp outside the largest 5% of stocks, so 35 bp per side is tight for small caps.
5. **Governance and concentration.** The Korea discount (P/B about 1 against 1.8 in Japan) is tied to controlling-family governance and inheritance tax. The Value-up and Commercial Act reforms (2024-26) are a regime break for value signals. KOSPI is now 55.5% two stocks.

### Cited Findings

**Short-selling regime**
- Full bans since the 2000s (KCMI):

  | Ban | Dates | Length |
  |---|---|---|
  | GFC | 1 Oct 2008 to 31 May 2009 | about 8 months |
  | Eurozone crisis | 11 Aug to 9 Nov 2011 | about 3 months |
  | COVID-19 | 16 Mar 2020 to 3 May 2021 | about 14 months; then lifted only for KOSPI 200 / KOSDAQ 150 |
  | Naked-shorting reform | 5 Nov 2023 to 31 Mar 2025 | about 17 months |

  The author judges the last ban "ineffective in driving up stock prices". He reports KOSPI -10.1% and KOSDAQ -22.8% while it was in force (2024; exact window not stated), with Korea the weakest major Asian market. The companion macro report has KOSPI -9.6% for calendar 2024. — [KCMI, Hwang, 1 Apr 2025](https://www.kcmi.re.kr/en/publications/pub_detail_view?syear=2025&zcd=002001017&zno=1840&cno=6517)
- Shorting of stocks outside KOSPI 200 / KOSDAQ 150 resumed "after about five years". — [AMRO 2026 Korea report (PDF)](https://amro-asia.org/wp-content/uploads/2026/03/Korea-ACV-2025-SI-3.pdf)
- **Resumption rules (31 Mar 2025, all listed stocks).**
  - A Naked Short Selling Detection System (NSDS) at KRX.
  - 83 institutions, 85.6% of pre-ban activity, had the required systems in place.
  - Penalties of 4-6x unfair profits.
  - Stock repayment period of 90 days, renewable to 12 months, for retail and institutions alike.
  - Retail cash collateral cut to 105%.
  - Expanded "overheated stock" designations through 31 May 2025.
  - Source: [FSC press release](https://www.fsc.go.kr/eng/pr010101/84220)
- Position-reporting and public-disclosure thresholds are 0.01% with market value above KRW 100m, or KRW 1bn or more. The old 0.5% public-disclosure threshold was removed effective 1 Dec 2024. — [aosphere](https://www.aosphere.com/know-how/south-korea-short-selling-where-are-we-now/)
- **2008 ban (KCMI, 2010).**
  - Pre-ban short selling was about 4-5% of trading.
  - Heavily shorted stocks showed no significant price effect (CAR -4.52%, not significant).
  - Their price efficiency "dramatically decreased".
  - Source: [KCMI weekly (PDF)](https://www.kcmi.re.kr/kcmifile/oldfiledata/weekly_6_4_567.pdf)
- **March 2020 ban (KCMI, Kim and Hwang, Aug 2023).**
  - Price efficiency fell, and negative information entered prices more slowly.
  - Amihud illiquidity and turnover worsened, although quoted spreads narrowed.
  - Volatility of positive returns and the frequency of extreme positive returns rose.
  - Source: [KCMI report 23-05](https://www.kcmi.re.kr/en/report/report_view?report_no=1521)
- **May 2021 partial resumption (Kim and Kim 2024, KJFS 53(4)).** The design exploits index entries and exits.
  - Permission to short cut price delay by about 0.14-0.15 (significant at 5%).
  - It was followed by positive, not negative, abnormal returns.
  - Volatility did not change.
  - Results are insignificant for KOSDAQ 150 alone.
  - Source: [KJFS (PDF)](https://www.e-kjfs.org/upload/pdf/KJFS-2024-08-53-4-393.pdf)
- **Status in July 2026.** No new ban despite a 22 July 2026 petition for a 6-month KOSDAQ suspension and a REITs association request. Officials cite MSCI goals and the negative assessment of the 2023 ban. Korea's short-sale ratio is reported below 5%, against 30-40% in the US and Japan (as reported). — [Invest Chosun, 23 Jul 2026](https://www.investchosun.com/site/data/html_dir/2026/07/23/2026072380147.html)
- **MSCI (24 Jun 2026).** Korea was not added to the developed-market watch list. Reasons: limited offshore won convertibility, limited omnibus and in-kind adoption, and "significant operational burdens" of the short-selling compliance regime. — [Korea Times](https://www.koreatimes.co.kr/economy/20260624/msci-keeps-korea-off-developed-market-watchlist-but-global-analysts-stay-bullish). Korea was on the list in 2008-2014; upgrading could take "three to four years at the fastest". — [Korea Herald](https://www.koreaherald.com/article/10786876)
- **Local check: short legs by holding-month regime.** Each figure is the riskiest equal-weighted decile minus the universe, per month.

  | Signal (short leg) | Full ban 2023-25, n=17 | Full resumption Apr 2025-Sep 2026, n=18 | Any restriction, n=73 | Unrestricted, n=235 |
  |---|---|---|---|---|
  | High MAX | -2.56 (t -9.5) | -1.41 (t -1.3) | -1.90 | -1.56 |
  | High volatility | -2.26 (t -8.3) | -1.73 (t -1.4) | -1.95 | -2.19 |
  | High turnover | -2.62 (t -8.0) | -0.78 (t -0.5) | -1.84 | -2.42 |
  | Last month's winners | -1.84 (t -2.6) | +0.70 (t 0.6) | -1.43 | -0.89 |
  | 12-7 losers | -1.65 (t -3.0) | -0.39 (t -0.6) | -0.71 | -1.38 |

  Source: [P6 local check p6_regime_f01.py](/home/claude/datalab/scripts/p6_indicative/p6_regime_f01.py)

**Price limits and volatility interruptions**
- Daily limits were ±15% from 7 Dec 1998 to 14 Jun 2015 and ±30% from 15 Jun 2015.
- A dynamic VI (3% threshold) started 1 Sep 2014. A static VI (±10%) started 15 Jun 2015.
- The dynamic VI is effective (31-43% net stabilisation). The static VI adds little (under 2%).
- Source: [Eom, Kwon, La, Park 2022, JRFM 15(3)](https://www.mdpi.com/1911-8074/15/3/105)
- After the 2015 widening, intraday realised volatility of the 200 largest stocks rose 3.6-9.3%, all in low-frequency components (July 2014 to May 2016). — [Kim and Jun (arXiv)](https://www.arxiv.org/pdf/1805.04728)
- **Local check, limit hits per 10,000 traded stock-days (|change| ≥ 29.5%).**

  | | Up, normal years 2016-25 | Up, 2020 | Up, 2026 YTD | Down |
  |---|---|---|---|---|
  | KOSPI | 9.6-14.2 | 22.9 | 27.7 | 0.5-3.2 |
  | KOSDAQ | 15.3-28.1 | 35.7 | 54.0 | 2.8-7.0 |

  Source: [P6 local check p6_micro.py](/home/claude/datalab/scripts/p6_indicative/p6_micro.py)
- **Local check, one-month reversal long-short before and after the limit change.** Feb 2001 to May 2015: 1.15%/month (t 2.8). Jul 2015 to Sep 2026: 0.53% (t 1.1). This is confounded with the time trend. — [P6 local check p6_regime_f01.py](/home/claude/datalab/scripts/p6_indicative/p6_regime_f01.py)

**Transaction tax**
- **2026 schedule.** From 1 Jan 2026 the securities transaction tax plus rural special tax is 0.20%: KOSPI is 0.05% plus 0.15%; KOSDAQ and K-OTC are 0.20%; KONEX stays at 0.10%. In 2025 it was 0.15% (KOSPI 0% plus 0.15%) and in 2019 0.30%. The cuts were tied to the financial investment income tax, which was repealed in December 2024. — [Herald Economy, 1 Dec 2025](https://biz.heraldcorp.com/article/10627001); [KB Think](https://kbthink.com/main/asset-management/wealth-manage-tip/kbthink-original/202410/kr-stocktax.html)
- An investor with KRW 100m selling twice a month pays about KRW 1.2m more a year after the increase. — [Daum/Biz Talk, 4 Jan 2026](https://v.daum.net/v/20260104000443380)
- The large-shareholder capital-gains threshold on KOSPI is 1% or KRW 5bn (as of Oct 2025). — [KB Think](https://kbthink.com/main/asset-management/wealth-manage-tip/kbthink-original/202410/kr-stocktax.html)

**Liquidity and spreads (local check)**
- Corwin-Schultz high-low full-spread estimates, Jan 2024 to Sep 2026, by market-cap bucket:

  | Cap bucket | Median spread (bp) | Median daily traded value (KRW bn) |
  |---|---|---|
  | Top 5% | 39 | 38.7 |
  | 80-95% | 55 | 4.5 |
  | 60-80% | 54 | 1.0 |
  | 40-60% | 62 | 0.4 |
  | 20-40% | 72 | about 0.1-0.2 |
  | Bottom 20% | 79 | about 0.1-0.2 |

  - Median by market: KOSPI 53 bp, KOSDAQ 72 bp.
  - Means are 97-130 bp because the estimator is noisy and biased upward for volatile stocks.
  - Source: [P6 local check p6_micro.py](/home/claude/datalab/scripts/p6_indicative/p6_micro.py)

**Retail share and concentration**
- In 2026 ETFs passed 30% of trading value while being about 6% of market cap. Year-to-date to 19 Jun 2026, individuals net bought KRW 64.3tn of listed stocks and KRW 55.3tn of ETFs. — [Financial News, 21 Jun 2026](https://www.fnnews.com/news/202606210907465517)
- **KEIA (22 Jul 2026).**
  - Samsung and SK hynix are 55.5% of KOSPI cap, against 22% at end-2023.
  - Foreigners net sold KRW 148.3tn in H1 2026.
  - Daily ETF turnover rose from KRW 6.6tn (Dec 2025) to KRW 34tn (Jun 2026). Leveraged ETFs are about 20% of 1,142 ETFs.
  - Circuit breakers fired 7 times in 2026.
  - P/B is 0.99, against 1.8 in Japan and 3.7 in the US.
  - Source: [KEIA](https://keia.org/analysis/explaining-south-koreas-stock-market-boom/)
- On 23 Jun 2026 (KOSPI -9.99%), individuals bought a record KRW 8.54tn. Foreigners sold KRW 4.14tn and institutions KRW 4.53tn. Single-stock leveraged ETFs on SK hynix fell 25.6% on average. — [Seoul Economic Daily](https://en.sedaily.com/markets/2026/06/23/kospi-plunges-10-percent-on-chip-concentration-leverage)
- **Comparators.** Taiwan individuals were about 90% of volume (1995-1999) and lost about 3.5 percentage points a year; virtually all losses came from aggressive orders. — [Barber, Lee, Liu, Odean (PDF)](http://faculty.haas.berkeley.edu/odean/papers/taiwan%20performance/who%20gains%20from%20trade%20040407.pdf). China: individuals own 88% of free float. — [LSY (PDF)](https://faculty.wharton.upenn.edu/wp-content/uploads/2018/03/Size-and-Value-in-China.pdf)

**Korea discount, chaebol and Value-up**
- Over ten years KOSPI P/B averaged 0.99, against 2.65 for advanced economies and 1.61 for EM.
- At end-2025, about 70% of stocks traded below P/B 1, and over 60% of firms had ROE below 7%.
- The ten-year average dividend payout is 31.3%.
- Controlling shareholders dominate governance, and minority protection is weak.
- Source: [AMRO 2026 (PDF)](https://amro-asia.org/wp-content/uploads/2026/03/Korea-ACV-2025-SI-3.pdf)
- **Value-up timeline.**
  - Announced 26 Feb 2024; guidelines 27 May 2024.
  - Korea Value-up Index (100 firms: 67 KOSPI, 33 KOSDAQ) launched 24 Sep 2024. It selects on profitability, shareholder returns, P/B and ROE. It excluded four top-10 caps.
  - ETFs and futures followed in Nov 2024.
  - By end-2025, 171 firms (44.5% of market cap but only 6% of listed firms) had disclosed plans.
  - Source: [KED Global](https://www.kedglobal.com/korean-stock-market/newsView/ked202409250005); [AMRO (PDF)](https://amro-asia.org/wp-content/uploads/2026/03/Korea-ACV-2025-SI-3.pdf)
- 65.8% of KOSPI companies had P/B below 1 at end-2023. — [TWSE market insight, 27 Aug 2024](https://www.twse.com.tw/market_insights/en/detail/8a8216d6913637e40191d4af667a0349)
- **Reform outcomes.**
  - Korean equities rose 75.6% in 2025; the Value-up Index rose 89.4% (+13.8 points). — [AMRO](https://amro-asia.org/wp-content/uploads/2026/03/Korea-ACV-2025-SI-3.pdf)
  - The index beat KOSPI 200 by 17% since its October 2024 launch. — [KEIA](https://keia.org/analysis/explaining-south-koreas-stock-market-boom/)
  - Commercial Act revisions in Jul and Aug 2025: directors' fiduciary duty to shareholders, mandatory cumulative voting. Separate dividend taxation at 14-30% from Apr 2026. — [AMRO](https://amro-asia.org/wp-content/uploads/2026/03/Korea-ACV-2025-SI-3.pdf)
- **Inheritance tax.** Rates up to 50%, and 60% for chaebol families, give controlling families an incentive to keep market values low. — [Seafarer Funds, Q2 2024](https://www.seafarerfunds.com/field-notes/seoul/2024/Q2/value-up/)
- **Dividend practice.** 88% of Nikkei 225 firms pay dividends more than once a year, against 15% of KOSPI 200. 44% against 18% have not cut dividends since FY2014. — [S&P Global/IHS Markit (PDF)](https://cdn.ihsmarkit.com/www/pdf/0424/South-Korea-Corporate-Value-up-Program.pdf)
- **Chaebol and information.** Related-party transactions, concentrated in chaebol firms, increase earnings drift. — [Choi and Cho 2021, FRL](https://www.sciencedirect.com/science/article/abs/pii/S1544612320317293)

### Inferences
- **Short sales.** For QUANTGEN (long-only by construction), Korea's short-sale history matters mainly because it lets overpricing persist in the riskiest decile. The usable action is "do not hold it", not "short it".
  - The ban/no-ban split is not consistent across signals.
  - Last month's winners and high-MAX stocks did worse under restrictions, consistent with the China A-share asymmetry.
  - 12-7 losers and stocks far from their high did worse when shorting was allowed.
  - Only 18 post-resumption months exist, so no regime conclusion is possible yet (INSUFFICIENT DATA).
- **Costs.** The 35 bp per side assumption is about right for the largest 20% of stocks: about 10 bp of averaged sell tax, about 1-2 bp of commission and a 20-27 bp half-spread. It is optimistic for the bottom 60% of caps, where the half-spread alone is about 31-39 bp. Korean stock cards should carry a size-tiered cost (DC-P6-05).
- **Price limits.** Limits turn some reversal into delayed continuation: a limit-up close carries unfilled demand into t+1. Limit-hit days should be excluded from reversal signals and flagged for any decide-at-close entry.
- **Value.** Book-to-market alone is contaminated in Korea by structural discounts at holding companies and controlling families. The Value-up regime (Feb 2024 onward) is a break, so value signals need a pre/post-2024 split and a P/B-plus-ROE or payout composite rather than raw P/B.
- **Concentration.** With 55.5% of KOSPI in two stocks, value-weighted cross-sectional signals are mostly bets on or against those two. Equal-weighted or capped portfolios are needed for cross-sectional tests, and value-weighted results must be reported ex-Samsung and SK hynix.

### Gaps
- **Retail share of trading.** No primary source found for individuals' share of KOSPI or KOSDAQ trading value for 2024-2026; the KRX and FSS pages were not fetched. Treat "retail ~60-80% of KOSDAQ-type volume" as unverified (not used as a number here).
- **Low-P/B event returns.** No study found of February-2024 Value-up announcement returns for low-P/B stocks (the S&P note did not contain them). A local test needs DART book equity.
- **Post-resumption shorting data.** S&P Global's April 2025 article was not readable beyond metadata.
- **Short interest.** No KRX short-interest series was obtained.

## Q4. Japan (TSE P/B reform, value, momentum failure, low-vol), China A, Taiwan and EM: per-market evidence

### Takeaway
- **Japan.** Value is the robust anomaly. Standalone momentum has not worked for decades but adds value as a hedge to value. Low beta is positive but weaker than in the US. The TSE March-2023 request changed corporate behaviour, but the evidence on low-P/B returns is mixed.
- **China A.** Reversal, low volatility, turnover, earnings-to-price value and gross profitability work. Momentum does not.
- **Taiwan.** Value (cash-flow-to-price) works. Momentum does not.
- **Emerging markets (EM) broadly.** Value, profitability, issuance and momentum work. The risk-return relation is flat or negative.

### Cited Findings

**Japan**
- **Value versus momentum.** Value earned 12.0%/year (Sharpe 0.79, t 4.31) and momentum 1.7%/year (t 0.57), with a correlation of -0.64, from January 1974 to July 2011. — [AMP 2013 (PDF)](https://w4.stern.nyu.edu/facdir/lpederse/papers/ValMomEverywhere.pdf). Fama-French (Nov 1989 to Mar 2011): Japan HML 0.48%/month (t 2.59), similar for small (0.47%) and big (0.50%) stocks; WML -0.08% (t 0.25). — [FF 2012 (PDF)](https://www.johnhcochrane.com/s/Fama_French_size_value_momentum_JFE.pdf)
- **Low beta.** Across 19 MSCI developed markets excluding the US (January 1984 to March 2012), BAB has a positive Sharpe in 18 of 19 and a positive four-factor alpha in 13. — [Frazzini-Pedersen 2014 (PDF)](https://w4.stern.nyu.edu/facdir/lpederse/papers/BettingAgainstBeta.pdf). One extraction reported Japan at 0.40%/month excess return, four-factor alpha 0.14% (t 1.15), Sharpe 0.52. A second read could not see the table, so treat the Japan row as unverified.
- **TSE request.** On 31 Mar 2023 the TSE asked Prime and Standard firms for "management that is conscious of cost of capital and stock price" (JPX Prime 150 index from July 2023). Over 40% of listed firms had P/B below 1 at 31 Mar 2023. — [TWSE comparison](https://www.twse.com.tw/market_insights/en/detail/8a8216d6913637e40191d4af667a0349); [SPARX](https://www.sparx.co.jp/ins/insights/detail/1473.html)
- **TSE compliance.** By 31 Dec 2023, 815 of 1,656 Prime firms had complied. The share of Prime firms below P/B 1 fell about 4 points (about 5 points for compliers), which cannot "simply" be attributed to the request. — [Dai-ichi Life Research Institute, Feb 2024](https://www.dlri.co.jp/english/report_en/202402YK.html)
- **TSE causal evidence.** A regression-discontinuity and difference-in-differences design around P/B = 1 finds:
  - Firms just below the threshold were initially less likely to disclose.
  - Marginal disclosers subsequently had lower valuations.
  - Disclosers adopted more shareholder-friendly payout and capital policies.
  - The average effects were "modest short-run increases in valuation, higher profitability".
  - Source: [Kitagawa, Liu, Nagata, SSRN 5866042](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=5866042)
- **Momentum dynamics.** Japan's momentum depends on market state and is damaged by frequent transitions. — [Hanauer 2014](https://ideas.repec.org/a/bla/irvfin/v14y2014i1p141-160.html). Daniel-Moskowitz dynamic scaling lifts the Japan WML Sharpe from 0.067 to 0.416 (project doc). — [QUANTGEN_MACRO_INTEGRATION.md](claude/QUANTGEN_MACRO_INTEGRATION.md)

**China A**
- **Liu-Stambaugh-Yuan (2000-2016), gross, IS.**
  - The smallest 30% of stocks are excluded: they are 7% of market cap but 83% of reverse-merger shells.
  - E/P beats B/M in a horse race (t 4.38 versus 1.31).
  - CH-3 factors: SMB 1.03%/month (t 3.25); VMG 1.14% (t 4.34). CH-3 explains 8 of 10 anomalies; a turnover factor explains all 10.
  - CAPM alphas: abnormal turnover 1.27% (t 2.92); one-month volatility 1.03% (t 2.31); MAX 0.81% (t 2.03).
  - Source: [LSY (PDF)](https://faculty.wharton.upenn.edu/wp-content/uploads/2018/03/Size-and-Value-in-China.pdf); [NBER w24458](https://www.nber.org/system/files/working_papers/w24458/w24458.pdf)
- **Blitz, Hanauer, van Vliet (2021), China A, November 2000 to December 2018.**
  - Low-volatility decile: 12.7%/year, Sharpe 0.51. High-volatility decile: -0.2%, Sharpe 0.00.
  - CAPM alpha spread: 16.1%/year.
  - A Fama-French-style VOL factor: 9.1% alpha (t 3.72), Sharpe 0.88. Alpha stays at 8.0% after size, value and momentum, and at 5.2% with E/P value.
  - The effect is "practically uncorrelated" with VOL factors in other regions.
  - Source: [Robeco (PDF)](https://assets.ctfassets.net/tl4x668xzide/1QBgySFzYmwqGlDmSaFYay/b118ecac9f394202b5d657f33f5d5fab/the-volatility-effect-in-china.pdf)
- **Jansen-Swinkels-Zhou, 2008-2020, efficient sorts, per month.**

  | Anomaly | %/month (t) |
  |---|---|
  | Size | 0.74 (2.15) |
  | B/P | 0.83 (2.58) |
  | E/P | 0.60 (2.36) |
  | Gross profitability | 1.10 (4.60) |
  | Volatility | 1.49 (4.10) |
  | Idiosyncratic volatility | 1.56 (5.24) |
  | Beta | 0.28 (0.99) |
  | Reversal | 1.41 (4.09) |
  | Momentum | 0.04 (0.11) |

  Source: [JSZ (PDF)](https://www.cfrn.com.cn/uploads/fileupload/a86579f7d6fb4328b45fa45156d074f7/paper/2a7aea538ad943c4b4220e51ec6dbfe5.pdf)
- **A versus B shares.** Earnings drift is about 2.05% in A shares against about 5% in B shares over 60 days. A-share reversal is driven by positive returns. — [Chui, Subrahmanyam, Titman, NBER w29453](https://www.nber.org/system/files/working_papers/w29453/w29453.pdf)

**Taiwan**
- **1990-2011 Fama-MacBeth slopes.**
  - B/M 0.0043 (t 2.14); cash-flow-to-price 0.0051 (t 3.42); E/P 0.0031 (t 1.87).
  - 6- and 12-month momentum insignificant; size and idiosyncratic volatility insignificant.
  - Short-term reversal significant in multiple regressions.
  - Source: [Cakici, Topyan, Wang (PDF)](https://content.manhattan.edu/school-of-business/research-papers/taiwan_stock_exchange_cakici_topyan_wang_cover.pdf)
- **Persistency momentum.** Taiwan is a "remarkable exception" to momentum. Persistent winners and losers earn up to 0.756%/month (1982-2020). — [Chen, Hsieh, Lee 2023](https://www.sciencedirect.com/science/article/abs/pii/S0927538X23000094)
- **Retail.** Individuals were about 90% of volume in 1995-1999 and lost more than 3.5 points a year. — [Barber, Lee, Liu, Odean (PDF)](http://faculty.haas.berkeley.edu/odean/papers/taiwan%20performance/who%20gains%20from%20trade%20040407.pdf)

**Emerging markets (EM)**
- Value is present in all 18 EMs and momentum in all but Eastern Europe (1990-2011), and local factors dominate. — [Cakici, Fabozzi, Tan 2013](https://econpapers.repec.org/article/eeeememar/v_3a16_3ay_3a2013_3ai_3ac_3ap_3a46-65.htm)
- Across 28 EMs (1995-2016), cash-flow-to-price, gross profitability, equity issuance and momentum are robust; there is no positive risk-return relation. — [Hanauer and Lauterbach 2019](https://www.sciencedirect.com/science/article/abs/pii/S1566014118304230)
- The EM risk-return relation is "flat, or even negative", is growing stronger, and is only weakly related to the developed-market volatility effect. — [Blitz, Pang, van Vliet 2013, EMR, RePEc](https://ideas.repec.org/a/eee/ememar/v16y2013icp31-45.html)

### Inferences
- **Japan.** Value 3 with a governance overlay. Momentum only as residual or value-paired, with a dynamic-scaling rule (TS-mom is unchanged by this note). Low volatility 2, not 3: the Japan BAB row is unverified, and the TSE reform rewards capital efficiency (ROE and payout), favouring a value-plus-quality composite.
- **China A.** The cleanest market for reversal (gross 1.2-1.7%/month), low volatility, turnover and E/P value. QUANTGEN has no China A data path (KIS does not quote A shares), so these weights are design priors only.
- **Taiwan.** Momentum 0, value 2 (cash-flow-to-price), reversal 2 at most (no net evidence). Flow is not tested here.
- **EM.** Weights should differ from the prior, which mirrored the US. Low volatility and quality get more weight. Momentum stays positive, but East Asia drags the EM average down.

### Gaps
- No post-2023 return study was found comparing Japanese low-P/B stocks with high-P/B stocks.
- The Japan BAB country row needs verification.
- No India-specific anomaly evidence was gathered, so the prior's India row is left unchanged and marked unreviewed.
- China A and Taiwan transaction costs, including stamp tax (China) and the 0.3% securities transaction tax (Taiwan), were not verified in this session.

## Q5. QUANTGEN translation: revised per-market x per-family weight table (0-3) and Korea-specific constraints

### Takeaway
Revised table, families as in the prior design plus three columns:
- "Lottery-excl" is an exclusion screen, not a tilt.
- "52wH" is nearness to the 52-week high.
- "Value+Q" is the value-plus-profitability composite.

Weights are design priors, not gate results. Any weight of 2 or more for Korea still needs a PASS card.

The main changes from the prior Korea row:
- Short-term reversal falls from 3 to 1 and flow from 3 to 1.
- Earnings drift falls from 3 to 2, pending a point-in-time DART test.
- Low volatility as a tilt falls from 2 to 1.
- Quality rises from 1 to 2.
- Cross-sectional momentum stays at 1, but only as 12-7 or the 52-week high; the new 52-week-high tilt is weighted 2 and flagged.
- New: a lottery-exclusion screen at 3.

### Cited Findings
The table synthesises the findings cited in Q1-Q4; each cell's justification lists its sources.

| Market | XS-mom | ST-rev | Value | Quality | Low-vol | Flow | Earn. drift | TS-mom | **Lottery-excl (new)** | **52wH (new)** |
|---|---|---|---|---|---|---|---|---|---|---|
| Prior Korea | 1 | 3 | 2 | 1 | 2 | 3 | 3 | 2 | n/a | n/a |
| **Korea (revised)** | **1** (12-7 / 52wH only) | **1** (gross real, net negative) | **2** (pre/post Value-up split) | **2** | **1** as a tilt | **1** (log; open-only effect) | **2** (DART pending) | 2 (unchanged; macro research) | **3** | **2** |
| Japan | 0 → **1** (only value-paired, residual or D-M-scaled) | 2 → **1** | 3 | 2 | 3 → **2** | 1 | 1 | 2 | 1 | 1 |
| China A | 0 | 3 | 1 → **2** (E/P, ex-shells) | 1 → **2** (GP) | 1 → **3** | 3 → **1** (untested) | 1 | 1 | **3** | 0 |
| Taiwan | 1 → **0** | 3 → **2** | 1 → **2** (CF/P) | 1 | 1 | 3 → **1** (untested) | 2 | 2 | 2 | 1 |
| EM (broad) | 3 → **2** | 1 | 2 → **3** | 2 → **3** | 1 → **2** | 2 → **1** | 1 | 3 | 2 | 1 |
| India | 3 | 1 | 2 | 3 | 2 | 2 | 2 | 2 | n/a | n/a |

India is unreviewed by P6 and kept as prior.

**Per-cell justification (Korea)**
- **XS-mom 1.** Literature conflicts (12-1 -6.13% versus +0.76 to +1.06%/month). Locally, equal-weighted 12-1 nets a Sharpe of 0.18 (-0.09 at 2x), while 12-7 nets 0.54 (0.10 at 2x). The strategy lost money in 2017-19 and 2021 and had a -22.3% month in July 2026. — [KJFS](https://www.e-kjfs.org/journal/view.php?number=901); [Bae and Lee](https://www.emerald.com/jdqs/article/29/1/49/195316/Illiquidity-duration-and-momentum-profits-evidence); [P6 local](/home/claude/datalab/scripts/p6_indicative/p6_krx_monthly_anomalies.csv)
- **ST-rev 1.** Gross 1-month reversal is 0.86%/month (t 2.70) but nets a Sharpe of -0.22. Weekly reversal nets -2.37. The volume-filtered version is about zero gross. Keep it as a guard (do not buy last month's top-decile winners) rather than a sleeve. — [Sim and Kim](https://www.emerald.com/jdqs/article/29/3/174/206550/The-effect-of-short-term-return-reversals-on); [P6 local weekly](/home/claude/datalab/scripts/p6_indicative/p6_weekly_f01.py)
- **Value 2.** HML 1.05%/month (t 3.41) over 2002-2015. The Korea discount and Value-up regime break justify a pre/post split. — [Kang (PDF)](http://www.korfin.org/korfin_file/forum/2016co-conf19-3.pdf); [AMRO](https://amro-asia.org/wp-content/uploads/2026/03/Korea-ACV-2025-SI-3.pdf)
- **Quality 2.** RMWq 0.65%/month (t 2.75). Profitability is robust across 28 EMs. Profitability (P/B plus ROE) is also the selection logic of Value-up. — [Kang](http://www.korfin.org/korfin_file/forum/2016co-conf19-3.pdf); [Hanauer and Lauterbach](https://www.sciencedirect.com/science/article/abs/pii/S1566014118304230); [KED Global](https://www.kedglobal.com/korean-stock-market/newsView/ked202409250005)
- **Low-vol 1 as a tilt.** The long-short is strong but lives in the short leg. As a long-only tilt it earns +0.12%/month equal-weighted (t 0.75) and -0.50%/month value-weighted (t -2.16), with 2025-26 relative returns of -20 and -46 points. — [P6 local](/home/claude/datalab/scripts/p6_indicative/p6_final_hold.py)
- **Flow 1.** Lagged foreign/institutional intensity is negative close-to-close and positive close-to-open. Copying foreign flow underperformed KOSPI. Foreigners trade at a disadvantage. — [Kim and Byun (PDF)](https://koreascience.kr/article/JAKO201103750648232.pdf); [Yu and Jang (PDF)](https://hanyang.scholarworks.kr/api/assets/9df82c36-bd3b-4089-af65-b5235f10bb6b/download); [NBER w10502](https://www.nber.org/papers/w10502)
- **Earnings drift 2.** A 4.80% 60-day spread (t 9.35, 2002-2017), driven by individuals trading against the news. Low turnover suits 35 bp costs, but there is no Korean net-of-cost or post-2017 evidence. — [MDPI](https://www.mdpi.com/2071-1050/11/18/5137); [Eom, Hahn, Sohn](https://ideas.repec.org/a/eee/pacfin/v53y2019icp379-398.html)
- **Lottery-exclusion 3.** Locally +0.23%/month equal-weighted net (t 8.25), positive in 92% of years and in every subperiod; small but positive value-weighted (+0.04). Consistent with Cheon and Lee, Goh and Kim, Cho, and Eom et al. (2014). — [P6 local](/home/claude/datalab/scripts/p6_indicative/p6_excl2.py); [Cheon and Lee](https://www.sciencedirect.com/science/article/abs/pii/S0927538X17304870); [Goh and Kim](https://www.emerald.com/jdqs/article/32/2/159/1236382/The-role-of-arbitrage-risk-in-the-MAX-effect)
- **52wH 2.** A local equal-weighted long-only tilt earns +0.34%/month net (+0.55 with lottery exclusion), but +0.09 at 2x and about zero capped value-weighted. Ryu (2021) and Goh and Jeon (2017) support anchoring on the 52-week high in Korea. Internationally the profits do not survive costs. — [P6 local](/home/claude/datalab/scripts/p6_indicative/p6_excl2.py); [Kyobo](https://scholar.kyobobook.co.kr/article/detail/4010028467563); [Liu, Liu, Ma](https://ideas.repec.org/a/eee/jimfin/v30y2011i1p180-204.html)

**Korea-specific constraints for every Korean stock card**
1. **Long-only, size-tiered costs.** Keep 35 bp per side for the top 20% of caps (where the 0.20% sell tax is averaged over both sides). Add the measured half-spread for smaller tiers: Corwin-Schultz medians imply half-spreads of 27-39 bp below the top 20%. Run 2x as usual. — [P6 local](/home/claude/datalab/scripts/p6_indicative/p6_micro.py); [Herald Economy](https://biz.heraldcorp.com/article/10627001)
2. **Price limits.** Flag stocks that closed within 1% of ±30% or had a static VI on day t. Never compute reversal from a limit-locked close. For a stock locked at the limit on day t, simulate entry at the t+1 open rather than the t close, since a locked close cannot be traded (see DC-P6-06). — [Eom, Kwon, La, Park 2022](https://www.mdpi.com/1911-8074/15/3/105)
3. **Short-sale regime as a logged state.** Tag each holding month as full ban, partial (index stocks only) or allowed. Report the anomaly by regime. — [KCMI](https://www.kcmi.re.kr/en/publications/pub_detail_view?syear=2025&zcd=002001017&zno=1840&cno=6517)
4. **Concentration.** Capped weights (for example 5%) or equal weights for cross-sectional tests. Report every value-weighted result with and without Samsung and SK hynix (55.5% of KOSPI). — [KEIA](https://keia.org/analysis/explaining-south-koreas-stock-market-boom/)
5. **Universe hygiene.** Exclude preferred shares, SPACs, KONEX, managed/warning-designated stocks and stocks under KRW 1,000. Require at least 15 traded days. Include delisting returns. Treat January 2001 and other KOSDAQ-bubble months (1999-2001) as stress tests, not training data.
6. **Investor-type flow.** Use only as a logged context variable. Any flow card must be decided with data published by the t close and earn from t+1 open or close, labelled separately (BL-D01).

### Inferences
- The revised Korea row puts its weight on low-turnover fundamental families (value plus quality, earnings drift) and on a risk screen (lottery exclusion). This matches QUANTGEN's high per-side cost and long-only, read-only design better than the prior's reversal and flow emphasis.
- Conflict with the macro research: it holds "reversal and quality at 1.0x". P6 agrees on quality, but recommends that the Korean reversal sleeve not be built as a standalone card at stock level, because it is negative net at 35 bp. The 1.0x rule then applies only to an index-level reversal (for example the KOSPI day-after-a-5%-fall pattern, which is a different test). Flagged for the report writer, not re-litigated.

### Gaps
- No primary data on China A, Taiwan and EM costs or data access through KIS. Those rows are priors only.
- None of the new Korea weights has a gate result yet. They are hypotheses for the experiments in Q6.

## Q6. Where and when it failed, the first five experiments on KRX stock-level data, and data-check requests

### Takeaway
Every Korean family has dated failure episodes:
- Momentum: 2017-2019 and 2021, and -22.3% in July 2026.
- Reversal: 2015 and 2025-26.
- Low volatility and MAX: January 2005, 2015, 2020 and early 2026.
- 52-week high: 2008-09 and April 2020.
- Size: 2003 and 2024-26.

Failures cluster in retail-mania rebounds and in concentrated mega-cap rallies. The first five experiments should settle:
1. lottery exclusion;
2. the momentum term structure;
3. whether reversal is feasible after costs;
4. DART earnings drift;
5. value plus quality across the Value-up break.

### Cited Findings
**Where and when it failed (dated episodes).**
- Local results are equal-weighted long-short gross, labelled by holding month. — [P6 local p6_sorts_hold.py](/home/claude/datalab/scripts/p6_indicative/p6_sorts_hold.py)

  | Signal | Worst months | Losing years (annual sums) |
  |---|---|---|
  | 12-1 momentum | Jul 2026 -22.3%; Nov 2014 -13.2%; Jan 2012 -12.9%; Feb 2017 -12.3% | 2017 -5.2, 2018 -16.4, 2019 -17.6, 2021 -22.6, 2009 -14.7 |
  | 12-7 momentum | Jul 2026 -15.5%; Apr 2009 -12.9% | 2021 -16.7 |
  | 1-month reversal | Jan 2005 -19.1%; Sep 2001 -18.0%; May 2015 -13.6%; May 2026 -12.0% | 2015 -25.6, 2025 -13.6, 2026 YTD -12.6 |
  | Low volatility | Jan 2005 -29.9%; May 2005 -20.6%; Oct 2001 -20.3%; Jan 2018 -18.4% | 2015 -17.9, 2020 -15.0 |
  | Low MAX | Jan 2005 -20.6%; Apr 2026 -14.9%; Jan 2018 -14.1%; Aug 2026 -13.1% | 2015 -20.7, 2020 -10.0 |
  | 52-week-high nearness | Apr 2020 -26.6%; Oct 2001 -24.8%; Dec 2008 -24.0% | 2008 -14.0, 2009 -25.8, 2020 -17.0 |
  | Small size | n/a | 2003 -42.1, 2017 -24.4, 2025 -29.3, 2026 YTD -25.7 |

- **Weekly 5-day reversal** (gross annual sums, by formation year): 2014 -27.7, 2023 -22.3, 2025 -31.9. From 2020 to 2026 the gross mean is -0.03%/week. — [P6 local p6_weekly_f01.py](/home/claude/datalab/scripts/p6_indicative/p6_weekly_f01.py)
- **Long-only low-risk tilt (value-weighted top quintile) against the value-weighted universe, net of 35 bp:** 2009 -29.5 points, 2025 -20.3, 2026 YTD -46.4. Only 35% of years are positive. — [P6 local p6_final_hold.py](/home/claude/datalab/scripts/p6_indicative/p6_final_hold.py)
- **Lottery exclusion (equal-weighted) worst year:** 2015, -1.6 points. — [P6 local p6_exclusion_hold.py](/home/claude/datalab/scripts/p6_indicative/p6_exclusion_hold.py)
- **2023-25 short-sale ban.** It did not support prices: KCMI reports KOSPI -10.1% and KOSDAQ -22.8% in 2024 (window as reported), and Korea was the weakest major Asian market. — [KCMI 2025](https://www.kcmi.re.kr/en/publications/pub_detail_view?syear=2025&zcd=002001017&zno=1840&cno=6517)
- **2020-21 ban.** Price efficiency fell, and extreme positive returns became more frequent. — [KCMI 2023](https://www.kcmi.re.kr/en/report/report_view?report_no=1521)
- **23 Jun 2026.** KOSPI fell 9.99%, retail bought a record KRW 8.54tn, and seven SK hynix leveraged ETFs fell 25.6% on average. — [Seoul Economic Daily](https://en.sedaily.com/markets/2026/06/23/kospi-plunges-10-percent-on-chip-concentration-leverage)
- **Japan momentum.** About 30 years of no profit to 2011. — [Asness 2011 (AQR)](https://www.aqr.com/Insights/Research/Journal-Article/Momentum-in-Japan-The-Exception-that-Proves-the-Rule). WML -0.08%/month over 1989-2011. — [FF 2012](https://www.johnhcochrane.com/s/Fama_French_size_value_momentum_JFE.pdf)
- **Taiwan momentum.** A documented exception over 1982-2020. — [Chen, Hsieh, Lee 2023](https://www.sciencedirect.com/science/article/abs/pii/S0927538X23000094)
- **52-week-high momentum internationally.** Not significant in most of 20 markets after transaction costs. — [Liu, Liu, Ma 2011](https://ideas.repec.org/a/eee/jimfin/v30y2011i1p180-204.html)
- **Following foreign flows (Korea, 2004-2010).** Underperformed KOSPI. — [Yu and Jang 2012 (PDF)](https://hanyang.scholarworks.kr/api/assets/9df82c36-bd3b-4089-af65-b5235f10bb6b/download)
- **TSE P/B request.** Marginal disclosers just below P/B 1 subsequently had lower valuations. — [Kitagawa, Liu, Nagata](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=5866042)

### Inferences
#### First five experiments (KRX stock-level; each a pre-registered card through the nine-step gate)

All five experiments share these settings:
- Decide at the close of day t and earn from t+1.
- Size-tiered costs (Q5 constraint 1), also at 2x.
- Universe hygiene as in Q5 constraint 5.
- Report equal-weighted, 5%-capped value-weighted, and capped value-weighted excluding Samsung and SK hynix.
- Report by short-sale regime and by subperiods 2001-09 / 2010-19 / 2020-26.
- Data: KIS stock OHLCV with investor-type flows (BL-D01/BL-D03), the marcap history file for backfill, and OpenDART for fundamentals.

1. **P6-X1: Lottery-exclusion screen (protective card, family weight 3).**
   - Signal: a composite rank of 63-day volatility, the month's maximum daily return, and 1-month turnover.
   - Rule: drop the worst decile from any Korean long book (base = equal-weighted or capped value-weighted universe, then each candidate sleeve).
   - Pass: excess over the base above 0 at 2x costs, at least 60% of years positive, and positive in each subperiod.
   - Daily-swing variant: also exclude any stock that hit ±29.5% or triggered a static VI on day t.
   - Local prior: +0.23%/month equal-weighted, +0.04%/month capped value-weighted, net.
2. **P6-X2: Momentum term structure.**
   - Signals: 12-1, 12-7, 12-0 (no skip), 52-week-high nearness, and residual momentum (36-month FF3-residual returns, scaled by residual volatility).
   - Splits: by turnover tercile.
   - Overlays: own-volatility scaling and the Daniel-Moskowitz bear gate on KOSPI state (the macro research's R-04).
   - Long-only top quintile against the universe.
   - Must report 2017-2021 and July 2026.
   - Embedded: the exact Eom et al. (2020) Table 3 replication (DC-P6-02).
   - Local prior: 12-7 net Sharpe 0.54 equal-weighted; 52-week-high long-only +0.34%/month net equal-weighted, about zero capped value-weighted.
3. **P6-X3: Reversal feasibility.**
   - Signals: 1-day, 5-day and 1-month reversal, long-only "buy losers" against the universe, by size tier.
   - Volume filter both ways (above 1.5 and below 0.7 times the prior 20-day average).
   - Limit-locked days excluded.
   - Each return split into overnight (close to open) and intraday (open to close).
   - Costs from measured KIS quote half-spreads (DC-P6-05).
   - Decision: no Korean stock reversal card unless the long-only version is positive at measured cost. The index-level KOSPI reversal (backlog BL-C02) is tested separately.
   - Local prior: gross 0.86%/month (monthly) and 0.30%/week (weekly); negative net; the volume-filtered version about zero.
4. **P6-X4: Earnings drift with point-in-time DART.**
   - Signal: SUE from preliminary-earnings disclosures (잠정실적) and periodic reports, timestamped by filing receipt (rcept_dt plus time, so a post-close filing counts as t+1). Alternative: the announcement return CAR[-1,+1].
   - Hold 60 sessions; long-only top quintile.
   - Interactions: individual net selling (Eom, Hahn, Sohn) and 52-week-high nearness (Goh-Jeon).
   - Pass: at 2x costs.
   - Literature prior: 4.80% 60-day spread (2002-2017, gross).
5. **P6-X5: Value plus quality across the Value-up break.**
   - Signals: E/P, B/M and CF/P plus GP/A, ROE and payout/buyback yield.
   - Point-in-time lags: annual reports at fiscal year-end plus 90 days, quarterly at plus 45 days, or the actual DART filing date.
   - Splits: excluding holding companies and financials; pre versus post 26 Feb 2024.
   - Add an event study of P/B deciles around 26 Feb 2024, 27 May 2024 and 24 Sep 2024.
   - Literature prior: HML 1.05%/month and RMWq 0.65%/month (2002-2015).

#### Data-check requests for the data lab
- **DC-P6-01.** Re-run p6_sorts.py on total returns (add DART or KRX cash dividends). Report how much the value, low-volatility and lottery long legs change.
- **DC-P6-02.** Exact replication of Eom et al. (2020) Table 3:
  - KOSPI plus KOSDAQ, holding months Aug 2000 to Jun 2019, December fiscal-year non-financials only (DART).
  - Drop the top decile of 12-month return standard deviation.
  - Turnover = average monthly volume over shares outstanding in the formation window; independent 30/40/30 x quintile sorts; equal-weighted; skip 1; hold 1.
  - Report winners minus losers, winners and losers, with delisting returns as given, and forced to -30% and -100%.
  - Settle: is high-turnover winners minus losers below -5%/month (paper) or about +0.6 to +1.4% (P6 local)?
- **DC-P6-03.** The P6-X1 card through all nine gate steps, with every exclusion-threshold variant (5%, 10%, 20%) counted as a trial.
- **DC-P6-04.** 1-day and 5-day reversal on daily data:
  - Decide at the t close and earn the t+1 close-to-close return, then split it into the t+1 overnight and the t+1 intraday leg.
  - Report by volume ratio (below 0.7, 0.7-1.5, above 1.5) and by size tier.
  - Report the share of the gross edge earned overnight, which a decide-at-close desk cannot capture after costs.
- **DC-P6-05.** Spread calibration:
  - KIS quote snapshots for 200 stocks stratified by size bucket over 20 sessions.
  - Quoted half-spread at about 15:15 (before the closing auction) and at 09:05.
  - Compare with the Corwin-Schultz medians (39-79 bp full spread) and set tier costs.
- **DC-P6-06.** Price limits:
  - After a limit-up close (≥ +29.5%), the t+1 open-to-close and close-to-close returns, 15 Jun 2015 to 2026, against ≥ +14.5% closes in 1998-2015.
  - Re-run the 1-month reversal and MAX sorts excluding stocks with a limit day in the formation month.
- **DC-P6-07.** Short-sale regime:
  - Pooled regression of each family's short-leg excess return on regime dummies (full ban, partial, allowed), with Newey-West errors.
  - Plus the May 2021 KOSPI 200 / KOSDAQ 150 entry/exit difference-in-differences for lottery-stock short legs.
- **DC-P6-08.** Ken French international files (Japan, Asia Pacific ex Japan, Emerging):
  - HML, WML, RMW and CMA over April 2011 to the latest month, as out-of-sample tests against Fama-French 2012 (Japan WML -0.08, HML 0.48; Asia Pacific WML 0.69, HML 0.62%/month).
  - Daniel-Moskowitz scaling on Japan WML.
  - Note: this sandbox could not download the files (egress 403); the lab's local copy ends in 2018.
- **DC-P6-09.** Concentration: every value-weighted Korean result repeated with a 5% cap and excluding 005930 and 000660.
- **DC-P6-10.** Value-up event study: P/B-decile cumulative abnormal returns (CAR) around 26 Feb 2024, 27 May 2024 and 24 Sep 2024, and around the July and August 2025 Commercial Act revisions (dates to be taken from the National Assembly record). Plus a post-Feb-2024 versus pre-Feb-2024 HML comparison.

### Gaps
- The experiments need DART fundamentals (P6-X4 and P6-X5) and KIS quote snapshots (P6-X3). Neither exists in the local lab today.
- No dated Korean value or quality failure episodes could be computed locally, because there are no fundamentals in the marcap file.

## Q7. Claims ledger (P6-C01 to P6-C28)

### Takeaway
There are 28 claims:
- **Nine BUILD-candidates**, each needing a PASS card first: C11, C12, C13 (as an exclusion), C15, C16, C19, C20, C25 (limit-day rule), C26 (cost tiers).
- **Four BACKLOG:** C04, C10, C17, C24.
- **Six DROP:**
  - C03: standalone Japan momentum;
  - C08: stock-level reversal as a sleeve;
  - C09: the volume-filtered 5-day reversal;
  - C14: low-vol as a long-only tilt;
  - C18: size;
  - C21: flow as a close-to-close alpha.
- **Nine CONTEXT:** C01, C02, C05, C06, C07, C22, C23, C27, C28.

Tiers:
- **T1** is peer-reviewed or official.
- **T2** is bank, asset manager, major press or index provider.
- **"T1-local"** is P6's in-sample check on KRX marcap data. It is not peer-reviewed and must be re-run by the data lab.

### Cited Findings

| ID | Claim (one sentence) | Evidence (numbers, market, period, IS/OOS, gross/net) | Source(s) with URL | Tier | Robustness | Failure cases | QUANTGEN implication |
|---|---|---|---|---|---|---|---|
| P6-C01 | Standalone stock momentum is insignificant in every East Asian market in the 40-country GJM sample. | 6/6 momentum to Dec-2000: Korea -0.76%/mo (t -0.80), Japan 0.02, Taiwan 0.01, China -0.01; Asia 0.32 (t 1.64) vs Europe 0.77 (t 8.15). Gross, IS. | [GJM 2003](https://gyanresearch.wdfiles.com/local--files/alpha/Momentum.pdf) | T1 | Consistent with FF 2012 (Japan), LSY (China), Chen et al. (Taiwan) | Asia average positive but weak | CONTEXT: start East Asian XS-mom weights at 0-1, not 3 |
| P6-C02 | Momentum profits rise with national individualism, which predicts weak momentum in Korea, Japan, Taiwan and China. | Positive relation of momentum to Hofstede individualism, robust to controls (country numbers not obtained). | [Chui-Titman-Wei 2010](https://econpapers.repec.org/RePEc:bla:jfinan:v:65:y:2010:i:1:p:361-392) | T1 | Published JF; 52-week-high momentum is NOT explained by individualism (Liu-Liu-Ma) | Not applicable | CONTEXT: prior for low XS-mom weights in collectivist markets |
| P6-C03 | Japanese stock momentum has had no standalone premium but pays as a hedge to value. | Japan 1974-2011: momentum 1.7%/yr (t 0.57), value 12.0% (t 4.31), combo Sharpe 0.78, correlation -0.64. FF: WML -0.08%/mo (t 0.25), 1989-2011. Gross, IS. | [AMP 2013](https://w4.stern.nyu.edu/facdir/lpederse/papers/ValMomEverywhere.pdf); [FF 2012](https://www.johnhcochrane.com/s/Fama_French_size_value_momentum_JFE.pdf); [Asness 2011](https://www.aqr.com/Insights/Research/Journal-Article/Momentum-in-Japan-The-Exception-that-Proves-the-Rule) | T1 | Two independent datasets; no post-2011 OOS obtained | 1974-2011 "near 30 years" without profit | DROP standalone Japan XS-mom; BACKLOG value+mom pair (DC-P6-08) |
| P6-C04 | Dynamic (Daniel-Moskowitz) scaling or market-state conditioning rescues part of Japanese momentum. | Japan WML Sharpe 0.067 → 0.416 (D&M Table 11); momentum higher when market state persists. | [QUANTGEN_MACRO_INTEGRATION.md](claude/QUANTGEN_MACRO_INTEGRATION.md); [Hanauer 2014](https://ideas.repec.org/a/bla/irvfin/v14y2014i1p141-160.html) | T1 | IS in the original paper | Frequent state transitions in Japan | BACKLOG: test on French Japan WML after 2011 |
| P6-C05 | Outside the US, anomalies have not reliably decayed after publication. | 241 anomalies, 39 markets; only the US shows a reliable post-publication decline. | [Jacobs-Müller 2020](https://ideas.repec.org/a/eee/jfinec/v135y2020i1p213-230.html) | T1 | JFE; meta-analysis | Korea's local time decay (C08, C10) contradicts it for reversal | CONTEXT: keep the 60% live haircut for Korea anyway (time decay, not publication) |
| P6-C06 | In China A, past returns at all horizons predict reversal and there is no momentum. | 2000-2016: 1-month reversal CAPM alpha 1.49%/mo (t 3.07); JSZ 2008-20: reversal 1.41 (t 4.09), momentum 0.04 (t 0.11). Gross, IS. | [LSY](https://www.nber.org/system/files/working_papers/w24458/w24458.pdf); [JSZ](https://www.cfrn.com.cn/uploads/fileupload/a86579f7d6fb4328b45fa45156d074f7/paper/2a7aea538ad943c4b4220e51ec6dbfe5.pdf) | T1 | Replicated across samples | No net evidence | CONTEXT: China A XS-mom 0, ST-rev 3 (no data path) |
| P6-C07 | Clientele drives the sign: retail-dominated A shares reverse, foreign-institutional B shares of the same firms show momentum. | 2001-2018: B momentum 1.15%/mo VW (t 3.33) vs A 0.27 (n.s.); A reversal 1.2% EW (t 4.93), B n.s.; A retail ≈ 85% of volume. | [Chui-Subrahmanyam-Titman, NBER w29453](https://www.nber.org/system/files/working_papers/w29453/w29453.pdf) | T1 | Natural experiment; working paper | Not applicable | CONTEXT: Korea's retail-heavy small caps should reverse more than foreign-held large caps |
| P6-C08 | Korea's 1-month reversal is real before costs but has decayed and is negative at QUANTGEN's costs. | Sim-Kim 1999-2021: r(-1) -2.950 (t -3.77). Local Feb-2001 to Sep-2026 EW L/S 0.86%/mo (t 2.70): 1.55 (2001-09) → 0.41 (2020-26); turnover 3.5/mo; net35 Sharpe -0.22; VW 0.04%/mo. | [Sim & Kim 2021](https://www.emerald.com/jdqs/article/29/3/174/206550/The-effect-of-short-term-return-reversals-on); [P6 local](/home/claude/datalab/scripts/p6_indicative/p6_krx_monthly_anomalies.csv) | T1 / T1-local | Literature IS; local IS; not OOS | 2015 -25.6, 2025 -13.6, 2026 YTD -12.6 (annual sums) | DROP as a standalone stock card; keep as a do-not-buy-last-month-winner guard |
| P6-C09 | The prior design's volume-filtered 5-day reversal has no edge in Korea; high-volume losers continue down. | Local weekly 2001-2026: unfiltered gross 0.30%/wk (t 3.8), net35 Sharpe -2.37; filter (vol ratio > 1.5) gross 0.03%/wk (t 0.2); filtered losers minus universe -0.34%/wk (t -4.1). | [P6 local p6_weekly_f01.py](/home/claude/datalab/scripts/p6_indicative/p6_weekly_f01.py) | T1-local | IS; one filter threshold | 2020-26 unfiltered gross -0.03%/wk | DROP the volume-filter spec for Korea; re-test the opposite (low-volume) filter in P6-X3 |
| P6-C10 | Korean 12-1 momentum is positive on average but fragile, not reliably negative as the KJFS headline suggests. | KJFS 2000-19 high-turnover W-L -6.13%/mo (t -4.76) vs local replication +0.58 (t 1.50) all caps / +1.42 (t 3.52) ex-micro; local 12-1 EW 0.76%/mo (t 2.37), net35 Sharpe 0.18, 2x -0.09; Bae-Lee VW 1.06 (t 2.53). | [Eom et al. 2020](https://www.e-kjfs.org/journal/view.php?number=901); [Bae & Lee 2021](https://www.emerald.com/jdqs/article/29/1/49/195316/Illiquidity-duration-and-momentum-profits-evidence); [P6 local](/home/claude/datalab/scripts/p6_indicative/p6_eom_x01.py) | T1 / T1-local | Conflicting; DC-P6-02 must settle | 2017-19, 2021 (-22.6), Jul-2026 -22.3% month | BACKLOG (P6-X2); XS-mom weight 1 |
| P6-C11 | The intermediate window (12-7) and skipping the latest month carry most of Korean momentum. | Sim-Kim pret(12,7) FF5 alpha 0.531%/mo (t 2.05) vs pret(6,2) -0.084; local 12-7 EW 1.30%/mo (t 4.91), net35 Sharpe 0.54 (2x 0.10); 12-0 ≈ 0 vs 12-1 up to 1.38 (t 3.25). | [Sim & Kim](https://www.emerald.com/jdqs/article/29/3/174/206550/The-effect-of-short-term-return-reversals-on); [P6 local](/home/claude/datalab/scripts/p6_indicative/p6_final_f01.py) | T1 / T1-local | Two sources agree; IS | 2021 -16.7; Jul-2026 -15.5% | BUILD-candidate (P6-X2), only with the vol-scaling and D&M gate per the macro research |
| P6-C12 | Nearness to the 52-week high is a Korean anchoring signal that helps an equal-weighted long book but not a cap-weighted one after costs. | Ryu 2021: GH/RR beat JT in Korea. Local EW top-quintile: +0.34%/mo net35 (t 2.31), +0.09 at 2x; with lottery exclusion +0.55 (t 3.63); capped VW +0.06 (t 0.40). | [Ryu 2021](https://scholar.kyobobook.co.kr/article/detail/4010028467563); [Goh & Jeon 2017](https://ideas.repec.org/a/eee/pacfin/v44y2017icp150-159.html); [P6 local](/home/claude/datalab/scripts/p6_indicative/p6_excl2.py) | T1 / T1-local | Internationally fails after costs (Liu-Liu-Ma) | 2008 -14.0, 2009 -25.8, Apr-2020 -26.6% month | BUILD-candidate at weight 2, EW/capped small-mid book only |
| P6-C13 | MAX/lottery stocks earn very low subsequent returns in Korea, more so in volatile markets. | Cheon-Lee 1992-2016: VW low-minus-high MAX 2.40%/mo (US 0.66); Goh-Kim 2000-20: H-L -2.08 (t -5.01); Cho 2000-16: -1.94 (t -5.10); local EW 1.95%/mo (t 6.55). | [Cheon & Lee](https://www.sciencedirect.com/science/article/abs/pii/S0927538X17304870); [Goh & Kim 2024](https://www.emerald.com/jdqs/article/32/2/159/1236382/The-role-of-arbitrage-risk-in-the-MAX-effect); [Cho 2021](https://www.emerald.com/jdqs/article/29/1/29/195322/Extreme-returns-and-idiosyncratic-risks-evidence) | T1 | Replicated by 3 papers + local; IS | 2015, 2020; Apr-2026 -14.9% month | BUILD-candidate as exclusion (see C15), not as a tilt |
| P6-C14 | The Korean low-risk premium sits in the short leg; as a long-only tilt it is about zero (EW) or negative (cap-weighted). | Local L/S EW 2.40%/mo (t 6.31), net35 Sharpe 0.91; long leg minus universe +0.25 (t 1.25); composite long-only EW +0.12 (t 0.75), VW -0.50 (t -2.16) net. | [P6 local](/home/claude/datalab/scripts/p6_indicative/p6_final_hold.py); [Eom et al. 2014](https://dbpia.co.kr/Journal/articleDetail?nodeId=NODE07228272) | T1-local / T1 | IS; dividends excluded (understates long leg) | VW relative -20.3 (2025), -46.4 (2026 YTD) | DROP as a tilt (weight 1); keep for risk display |
| P6-C15 | Excluding the most lottery-like decile improves a long-only Korean book in every subperiod. | Local Feb-2001 to Sep-2026: EW +0.23%/mo net35 (t 8.25), 2x +0.20, 92% of years positive; capped VW +0.04 (t 3.46); VW ex-Samsung/SK hynix +0.04 (t 3.36). | [P6 local](/home/claude/datalab/scripts/p6_indicative/p6_excl2.py) | T1-local | IS; composite chosen ex ante from the literature; no deflation | Worst year 2015 (-1.6) | BUILD-candidate P6-X1 (weight 3) |
| P6-C16 | Korean earnings drift is large and is caused by individuals trading against the news. | 2002Q4-2017Q4: 60-day spread 4.80% (t 9.35); 6.93% when sentiment trends up. Drift only where individuals trade against the news. Gross, IS. | [Shin et al. 2019](https://www.mdpi.com/2071-1050/11/18/5137); [Eom, Hahn, Sohn 2019](https://ideas.repec.org/a/eee/pacfin/v53y2019icp379-398.html) | T1 | Two papers; no net or post-2017 evidence | Not applicable | BUILD-candidate P6-X4 (needs DART timestamps) |
| P6-C17 | Chaebol-style related-party transactions amplify Korean earnings drift. | 1,286 firm-years 2015-18; more RPT → larger drift, especially in chaebol firms. | [Choi & Cho 2021](https://www.sciencedirect.com/science/article/abs/pii/S1544612320317293) | T1 | Short sample | Not applicable | BACKLOG: interaction term in P6-X4 |
| P6-C18 | Size has no reliable premium in Korea. | Kang 2002-15 SMB 0.16%/mo (t 0.45); local small-minus-big EW 0.28 (t 0.87), net35 Sharpe -0.02; Kim 2021 reports a size premium (conflict). | [Kang (PDF)](http://www.korfin.org/korfin_file/forum/2016co-conf19-3.pdf); [Kim 2021](https://www.sciencedirect.com/science/article/abs/pii/S0927538X21000652); [P6 local](/home/claude/datalab/scripts/p6_indicative/p6_krx_monthly_anomalies.csv) | T1 / T1-local | Conflicting | 2003 -42.1; 2025 -29.3; 2026 YTD -25.7 | DROP size as a signal; keep as a risk control |
| P6-C19 | Korean value and profitability premia were significant before Value-up. | Jul-2002 to Jun-2015: HML 1.05%/mo (t 3.41), RMWq 0.65 (t 2.75), CMA 0.66 (t 3.57). Gross, IS. | [Kang (PDF)](http://www.korfin.org/korfin_file/forum/2016co-conf19-3.pdf); [Hanauer-Lauterbach (EM)](https://www.sciencedirect.com/science/article/abs/pii/S1566014118304230) | T1 | No post-2015 Korean evidence found | Not measured | BUILD-candidate P6-X5 (value 2, quality 2) |
| P6-C20 | The Korea discount is structural (governance and inheritance tax), and the 2024-26 reforms are a regime break for value signals. | KOSPI P/B 0.99 (10-yr avg) vs 2.65 advanced; ~70% of stocks P/B < 1 at end-2025; Value-up Index +89.4% vs market +75.6% in 2025; Commercial Act Jul/Aug 2025; inheritance tax up to 60%. | [AMRO 2026](https://amro-asia.org/wp-content/uploads/2026/03/Korea-ACV-2025-SI-3.pdf); [KEIA](https://keia.org/analysis/explaining-south-koreas-stock-market-boom/); [Seafarer](https://www.seafarerfunds.com/field-notes/seoul/2024/Q2/value-up/) | T1 / T2 | Official and think-tank sources; causal effect unmeasured | Gains concentrated in Samsung + SK hynix | BUILD-candidate: pre/post-2024 split in P6-X5; DC-P6-10 |
| P6-C21 | Lagged foreign and institutional net buying predicts the next open, not the next close; copying foreign flow underperformed. | 2003-2011: t-1 intensity negative for the close-to-close return, positive for the close-to-open; 2004-2010: following foreigners < KOSPI, following institutions > KOSPI in 20 of 22 stocks. | [Kim & Byun 2011](https://koreascience.kr/article/JAKO201103750648232.pdf); [Yu & Jang 2012](https://hanyang.scholarworks.kr/api/assets/9df82c36-bd3b-4089-af65-b5235f10bb6b/download) | T1 | Older samples; Korean-journal | Not applicable | DROP flow as a close-to-close alpha (weight 3 → 1); BACKLOG open-leg test |
| P6-C22 | Foreign investors trade at a disadvantage in Korea; domestic individuals hold a short-lived edge. | Foreigners pay 21 bp more on buys and receive 16 bp less on sales; they sell before large positive abnormal returns (1996-98). | [NBER w10502](https://www.nber.org/papers/w10502); [NBER w8073](https://www.nber.org/papers/w8073) | T1 | Published (RFS/JF versions) | Not applicable | CONTEXT: do not treat foreign buying as "smart money" |
| P6-C23 | Korean short-sale bans reduced price efficiency and did not support prices. | 2008: efficiency "dramatically decreased", price effect n.s.; 2020: efficiency and liquidity down, extreme positive returns up; May-2021 index experiment: shorting cut price delay by 0.14-0.15; 2024 ban: KOSPI -10.1%, KOSDAQ -22.8%. | [KCMI 2010 (PDF)](https://www.kcmi.re.kr/kcmifile/oldfiledata/weekly_6_4_567.pdf); [KCMI 2023](https://www.kcmi.re.kr/en/report/report_view?report_no=1521); [Kim & Kim 2024](https://www.e-kjfs.org/upload/pdf/KJFS-2024-08-53-4-393.pdf); [KCMI 2025](https://www.kcmi.re.kr/en/publications/pub_detail_view?syear=2025&zcd=002001017&zno=1840&cno=6517) | T1 | Several bans, consistent | KOSDAQ 150 results insignificant | CONTEXT: tag the short-sale regime on every Korean card (DC-P6-07) |
| P6-C24 | Short-sale regime does not consistently change Korean anomaly short legs. | Local, EW top decile minus universe: high-MAX -2.56 (ban 2023-25) vs -1.41 (resumption 2025-26); 12-7 losers -0.71 (restricted) vs -1.38 (allowed); post-resumption n = 18 months. | [P6 local p6_regime_f01.py](/home/claude/datalab/scripts/p6_indicative/p6_regime_f01.py) | T1-local | IS; tiny post-resumption sample | Not applicable | BACKLOG (INSUFFICIENT DATA): re-check in 2027 |
| P6-C25 | The ±30% price limits (since 15 Jun 2015) raised low-frequency volatility, and limit hits spike in retail manias. | Intraday realised vol +3.6% to +9.3% (2014-16, top 200); static VI adds < 2% stabilisation; local KOSDAQ up-limit hits 54.0 per 10k stock-days in 2026 vs 15-28 normally. | [Kim & Jun (arXiv)](https://www.arxiv.org/pdf/1805.04728); [Eom et al. 2022](https://www.mdpi.com/1911-8074/15/3/105); [P6 local p6_micro.py](/home/claude/datalab/scripts/p6_indicative/p6_micro.py) | T1 / T1-local | Consistent | 2020 and 2026 spikes | BUILD-candidate rule: flag and exclude limit-locked days (DC-P6-06) |
| P6-C26 | QUANTGEN's flat 35 bp per side understates the cost of trading the bottom 60% of KRX caps. | 2026 tax 0.20% (KOSPI 0.05 + 0.15 rural; KOSDAQ 0.20); local Corwin-Schultz median full spread 39 bp (top 5%) to 79 bp (bottom 20%), Jan-2024 to Sep-2026. | [Herald Economy](https://biz.heraldcorp.com/article/10627001); [P6 local p6_micro.py](/home/claude/datalab/scripts/p6_indicative/p6_micro.py) | T2 / T1-local | Estimator noisy and upward-biased (means 97-130 bp) | Not applicable | BUILD-candidate: size-tiered cost schedule after DC-P6-05 |
| P6-C27 | Low volatility, E/P value and gross profitability are robust in China A; low volatility is close to independent of other regions' VOL factors. | Nov-2000 to Dec-2018: VOL factor alpha 9.1% (t 3.72), Sharpe 0.88, CAPM alpha spread 16.1%/yr; JSZ 2008-20: idiosyncratic vol 1.56%/mo (t 5.24), gross profitability 1.10 (t 4.60). | [Blitz-Hanauer-van Vliet 2021](https://assets.ctfassets.net/tl4x668xzide/1QBgySFzYmwqGlDmSaFYay/b118ecac9f394202b5d657f33f5d5fab/the-volatility-effect-in-china.pdf); [JSZ](https://www.cfrn.com.cn/uploads/fileupload/a86579f7d6fb4328b45fa45156d074f7/paper/2a7aea538ad943c4b4220e51ec6dbfe5.pdf) | T2 / T1 | Asset-manager research plus academic replication | No net figures | CONTEXT: China A low-vol 3, quality 2 (no data path yet) |
| P6-C28 | The TSE 2023 P/B request changed payout behaviour, but its valuation effect is modest and uneven. | 815 of 1,656 Prime firms disclosed by Dec-2023; P/B < 1 share down about 4 pp; RD/DiD: modest short-run valuation gains, higher profitability; marginal disclosers lost value. | [DLRI 2024](https://www.dlri.co.jp/english/report_en/202402YK.html); [Kitagawa, Liu, Nagata (SSRN)](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=5866042) | T2 / T1 (WP) | Working paper; short window | Marginal firms just below P/B 1 | CONTEXT: Japan value 3 with a capital-efficiency (ROE, payout) overlay |

### Inferences
- The ledger's BUILD-candidates for Korea are low-turnover or protective (C11, C12, C15, C16, C19/C20, C25, C26), which suits a 35 bp per-side, long-only, read-only desk.
- All "T1-local" claims are in-sample and need the data lab's gate run before any card is believed.

### Gaps
- Claims C02, C04, C17 and C28 rest on abstracts or secondary summaries rather than full tables.
- C10 needs DC-P6-02 to resolve the KJFS-versus-local conflict.

## Q8. Source list

### Takeaway
The source list below has 60 entries: 51 external sources and 9 project or local files. Most external sources are T1 (journals, working papers, official bodies). T2 sources are AMRO, KEIA, the major press, asset managers (Robeco/AQR/Seafarer), sell-side research and DLRI. No Wikipedia, Reddit, Medium, Investopedia or Naver blogs were used as evidence.

### Cited Findings
**International (T1)**
- Griffin, Ji, Martin (2003), JF: [PDF copy](https://gyanresearch.wdfiles.com/local--files/alpha/Momentum.pdf); [Wiley](https://onlinelibrary.wiley.com/doi/abs/10.1046/j.1540-6261.2003.00614.x)
- Chui, Titman, Wei (2010), JF: [EconPapers](https://econpapers.repec.org/RePEc:bla:jfinan:v:65:y:2010:i:1:p:361-392)
- Rouwenhorst (1999), JF: [RePEc](https://ideas.repec.org/a/bla/jfinan/v54y1999i4p1439-1464.html). Rouwenhorst (1998) via the [Subrahmanyam 2018 synthesis (PDF)](https://anderson-review.ucla.edu/wp-content/uploads/2021/03/Subra2018_Momentum.pdf)
- Fama, French (2012), JFE: [PDF](https://www.johnhcochrane.com/s/Fama_French_size_value_momentum_JFE.pdf)
- Asness, Moskowitz, Pedersen (2013), JF: [PDF](https://w4.stern.nyu.edu/facdir/lpederse/papers/ValMomEverywhere.pdf)
- Asness (2011), JPM: [AQR page](https://www.aqr.com/Insights/Research/Journal-Article/Momentum-in-Japan-The-Exception-that-Proves-the-Rule)
- Hanauer (2014), IRF: [RePEc](https://ideas.repec.org/a/bla/irvfin/v14y2014i1p141-160.html)
- Iwanaga, Hirose, Yoshida (2023/24), APFM: [Springer](https://link.springer.com/article/10.1007/s10690-023-09413-y)
- Frazzini, Pedersen (2014), JFE: [PDF](https://w4.stern.nyu.edu/facdir/lpederse/papers/BettingAgainstBeta.pdf)
- Cakici, Fabozzi, Tan (2013), EMR: [EconPapers](https://econpapers.repec.org/article/eeeememar/v_3a16_3ay_3a2013_3ai_3ac_3ap_3a46-65.htm)
- Hanauer, Lauterbach (2019), EMR: [ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S1566014118304230)
- Blitz, Pang, van Vliet (2013), EMR: [RePEc](https://ideas.repec.org/a/eee/ememar/v16y2013icp31-45.html)
- Jacobs, Müller (2020), JFE: [RePEc](https://ideas.repec.org/a/eee/jfinec/v135y2020i1p213-230.html)
- Liu, Liu, Ma (2011), JIMF: [RePEc](https://ideas.repec.org/a/eee/jimfin/v30y2011i1p180-204.html)
- Chen, Stivers, Sun (2024), JEF: [RePEc](https://ideas.repec.org/a/eee/empfin/v79y2024ics0927539824000902.html)
- Liu, Stambaugh, Yuan (2019), JFE: [NBER w24458](https://www.nber.org/system/files/working_papers/w24458/w24458.pdf); [Wharton PDF](https://faculty.wharton.upenn.edu/wp-content/uploads/2018/03/Size-and-Value-in-China.pdf)
- Chui, Subrahmanyam, Titman: [NBER w29453](https://www.nber.org/system/files/working_papers/w29453/w29453.pdf)
- Jansen, Swinkels, Zhou (2021, PBFJ): [RePEc](https://ideas.repec.org/a/eee/pacfin/v68y2021ics0927538x21001141.html); "More powerful tests" (JPM 2024): [PDF](https://www.cfrn.com.cn/uploads/fileupload/a86579f7d6fb4328b45fa45156d074f7/paper/2a7aea538ad943c4b4220e51ec6dbfe5.pdf)
- Chen, Hsieh, Lee (2023), PBFJ (Taiwan): [ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S0927538X23000094)
- Cakici, Topyan, Wang (Taiwan): [PDF](https://content.manhattan.edu/school-of-business/research-papers/taiwan_stock_exchange_cakici_topyan_wang_cover.pdf)
- Barber, Lee, Liu, Odean (Taiwan): [PDF](http://faculty.haas.berkeley.edu/odean/papers/taiwan%20performance/who%20gains%20from%20trade%20040407.pdf)
- Richards (2005), JFQA: [RePEc](https://ideas.repec.org/a/cup/jfinqa/v40y2005i01p1-27_00.html)
- Kitagawa, Liu, Nagata (TSE): [SSRN 5866042](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=5866042)

**Korea (T1)**
- Eom, Chang, Kang, Lee, Park (2020), KJFS 49(4): [article page](https://www.e-kjfs.org/journal/view.php?number=901); [PDF](https://www.e-kjfs.org/upload/pdf/KJFS-2020-08-49-4-589.pdf)
- Eom, Park (2021), RIBAF: [RePEc](https://ideas.repec.org/a/eee/riibaf/v57y2021ics0275531921000258.html)
- Chae, Eom (2009), APJFS (title only): [Wiley](https://onlinelibrary.wiley.com/doi/10.1111/j.2041-6156.2009.tb00013.x)
- Sim, Kim (2021), JDQS 29(3): [Emerald](https://www.emerald.com/jdqs/article/29/3/174/206550/The-effect-of-short-term-return-reversals-on)
- Bae, Lee (2021), JDQS 29(1): [Emerald](https://www.emerald.com/jdqs/article/29/1/49/195316/Illiquidity-duration-and-momentum-profits-evidence)
- Cho (2021), JDQS 29(1): [Emerald](https://www.emerald.com/jdqs/article/29/1/29/195322/Extreme-returns-and-idiosyncratic-risks-evidence)
- Goh, Kim (2024), JDQS 32(2): [Emerald](https://www.emerald.com/jdqs/article/32/2/159/1236382/The-role-of-arbitrage-risk-in-the-MAX-effect)
- Cheon, Lee (2018), PBFJ: [ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S0927538X17304870)
- Eom, Lee, Park, Jang, Park (2014), KJFS 43(4): [DBpia](https://dbpia.co.kr/Journal/articleDetail?nodeId=NODE07228272)
- Ryu (2021), JKDAS 23(4): [Kyobo Scholar](https://scholar.kyobobook.co.kr/article/detail/4010028467563)
- Goh, Jeon (2017), PBFJ: [RePEc](https://ideas.repec.org/a/eee/pacfin/v44y2017icp150-159.html)
- Eom, Hahn, Sohn (2019), PBFJ: [RePEc](https://ideas.repec.org/a/eee/pacfin/v53y2019icp379-398.html)
- Shin, Shin, Kim (2019), Sustainability: [MDPI](https://www.mdpi.com/2071-1050/11/18/5137)
- Choi, Cho (2021), FRL: [ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S1544612320317293)
- Kang (2016), Korean factor models: [KFA PDF](http://www.korfin.org/korfin_file/forum/2016co-conf19-3.pdf)
- Kim (2021), PBFJ: [ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S0927538X21000652)
- Kim, Kang, Roh (2025), PBFJ: [RePEc](https://ideas.repec.org/a/eee/pacfin/v90y2025ics0927538x24003743.html)
- Choe, Kho, Stulz: [NBER w6661](https://ideas.repec.org:443/p/nbr/nberwo/6661.html); [w8073](https://www.nber.org/papers/w8073); [w10502](https://www.nber.org/papers/w10502)
- Kim, Byun (2011): [Korea Science PDF](https://koreascience.kr/article/JAKO201103750648232.pdf)
- Yu, Jang (2012), Korean Journal of Financial Management: [Hanyang PDF](https://hanyang.scholarworks.kr/api/assets/9df82c36-bd3b-4089-af65-b5235f10bb6b/download)
- Kim, Kim (2024), KJFS 53(4): [PDF](https://www.e-kjfs.org/upload/pdf/KJFS-2024-08-53-4-393.pdf)
- Eom, Kwon, La, Park (2022), JRFM: [MDPI](https://www.mdpi.com/1911-8074/15/3/105)
- Kim, Jun (price-limit change): [arXiv](https://www.arxiv.org/pdf/1805.04728)

**Official, regulators and policy institutes (T1/T2)**
- FSC (short-selling resumption): [press release](https://www.fsc.go.kr/eng/pr010101/84220)
- KCMI: [Hwang 2025](https://www.kcmi.re.kr/en/publications/pub_detail_view?syear=2025&zcd=002001017&zno=1840&cno=6517); [Kim and Hwang 2023](https://www.kcmi.re.kr/en/report/report_view?report_no=1521); [Kim 2010 (PDF)](https://www.kcmi.re.kr/kcmifile/oldfiledata/weekly_6_4_567.pdf)
- AMRO 2026 Korea report: [PDF](https://amro-asia.org/wp-content/uploads/2026/03/Korea-ACV-2025-SI-3.pdf)
- TWSE comparison of Japan, Korea and Taiwan programmes: [TWSE](https://www.twse.com.tw/market_insights/en/detail/8a8216d6913637e40191d4af667a0349)

**T2 (research institutes, asset managers, press)**
- KEIA, 22 Jul 2026: [link](https://keia.org/analysis/explaining-south-koreas-stock-market-boom/)
- Robeco, The Volatility Effect in China: [PDF](https://assets.ctfassets.net/tl4x668xzide/1QBgySFzYmwqGlDmSaFYay/b118ecac9f394202b5d657f33f5d5fab/the-volatility-effect-in-china.pdf)
- Dai-ichi Life Research Institute (TSE): [link](https://www.dlri.co.jp/english/report_en/202402YK.html); SPARX: [link](https://www.sparx.co.jp/ins/insights/detail/1473.html)
- Seafarer Funds (Value-up): [link](https://www.seafarerfunds.com/field-notes/seoul/2024/Q2/value-up/); S&P Global/IHS Markit: [PDF](https://cdn.ihsmarkit.com/www/pdf/0424/South-Korea-Corporate-Value-up-Program.pdf)
- SK Securities quant report, 30 Apr 2025: [PDF](https://www.sks.co.kr/data1/research/qna_file/20250429151923625_0_ko.pdf)
- Press:
  - [Herald Economy, 1 Dec 2025](https://biz.heraldcorp.com/article/10627001)
  - [Daum/Biz Talk, 4 Jan 2026](https://v.daum.net/v/20260104000443380)
  - [KB Think](https://kbthink.com/main/asset-management/wealth-manage-tip/kbthink-original/202410/kr-stocktax.html)
  - [Financial News, 21 Jun 2026](https://www.fnnews.com/news/202606210907465517)
  - [Seoul Economic Daily, 23 Jun 2026](https://en.sedaily.com/markets/2026/06/23/kospi-plunges-10-percent-on-chip-concentration-leverage)
  - [Korea Times, 24 Jun 2026](https://www.koreatimes.co.kr/economy/20260624/msci-keeps-korea-off-developed-market-watchlist-but-global-analysts-stay-bullish)
  - [Korea Herald](https://www.koreaherald.com/article/10786876)
  - [Invest Chosun, 23 Jul 2026](https://www.investchosun.com/site/data/html_dir/2026/07/23/2026072380147.html)
  - [KED Global](https://www.kedglobal.com/korean-stock-market/newsView/ked202409250005)
  - [aosphere](https://www.aosphere.com/know-how/south-korea-short-selling-where-are-we-now/)
  - [Korea Pro](https://koreapro.org/2025/02/south-korea-to-resume-short-selling-in-march-but-market-risks-remain-high/)

**Project and local**
- [QUANTGEN_MACRO_INTEGRATION.md](claude/QUANTGEN_MACRO_INTEGRATION.md) and [QUANTGEN_MACRO_BACKLOG.md](claude/QUANTGEN_MACRO_BACKLOG.md) (project docs)
- P6 local checks: `/home/claude/datalab/scripts/p6_indicative/` (README.txt; p6_sorts.py, p6_sorts_hold.py, p6_split_f01.py, p6_weekly_f01.py, p6_regime_f01.py, p6_final_f01.py, p6_final_hold.py, p6_excl2.py, p6_exclusion_hold.py, p6_eom_x01.py, p6_micro.py; CSVs p6_krx_monthly_anomalies*.csv)

### Inferences
- The Korean-journal evidence base is dominated by KJFS, JDQS (선물연구) and PBFJ. KCI landing pages could not be machine-read, so several KCI-only papers remain unexamined (see the Q2 Gaps).

### Gaps
- Blocked or unavailable this session:
  - KCI (robots.txt);
  - Wiley abstracts (403);
  - SSRN and Semantic Scholar (429 rate limit);
  - OpenAlex and the Ken French data library (egress-policy 403);
  - the S&P Global short-selling article body;
  - the CNBC 2026 articles (403).
- The web-search budget ran out mid-session. No search was made for India, the Hofstede scores or the 2026 KRX retail-share statistics.

