# E6: Corporate actions and capital-markets events in the US and Korea. Which still pay after costs, which are only flags (as of 2 October 2026)

**Persona.** E6, "Vice-Chairman of Investment Banking (ECM and M&A) at a bulge-bracket bank". This is a *fictional composite* persona. It is not a real person and does not speak for any real firm. The background is about 25 years on the issuer side in New York and Seoul:
- equity syndicate work: IPOs, follow-ons, overnight blocks, Korean rights offerings (유상증자) and private CB/BW placements;
- running lock-up and index-rebalance execution;
- M&A advisory: public targets, tender offers, spin-offs, chaebol restructurings.

The lens: every corporate event is a supply or demand shock, and the best-informed party in the room chooses its timing. The announcement jump goes to whoever was already positioned. What remains after arbitrage capital is usually smaller than a retail desk's round-trip cost. So I trust event *plumbing* (calendars, supply overhangs, pinned prices, dilution mechanics) more than event *alpha*. Below I check that prejudice against published data.

**Position summary.**
1. Corporate events are priced within a session. QUANTGEN decides at the close and pays 50 bp per side in the US and 35 bp per side on KRX stocks. So the test is not whether an event effect exists. The test is whether drift remains after the first close at which the event is provably public, and whether that drift survives a 100-200 bp (US) or 70-140 bp (KRX) round trip.
2. Most of the US canon fails that test today:
   - The S&P 500 inclusion effect fell from 7.3% (1990s) to an insignificant 0.8% (2010s).
   - Long-run drift after buybacks and SEOs disappeared for events in the most recent decade studied (about 2003-2012, Fu-Huang 2016).
   - Merger-arbitrage spreads compressed by more than 400 bp after 2001.
   - Drift after dividend initiations and omissions does not survive value-weighting or controls for earnings drift.
   - Analyst-recommendation strategies never cleared costs.
3. Two US effects are still alive:
   - **IPO underperformance.** The 2011-2024 cohorts trail style-matched firms by 16.4% over three years, and unprofitable issuers trail by 23.4% over 1980-2024. QUANTGEN should use this only as a cost-free exclusion screen, never as a short.
   - **Opportunistic insider trades from Form 4.** They earned 82 bp/month value-weighted in 1986-2007, gross. The information sits in purchases. This is the one corporate event I would promote to a gated BUILD-candidate signal, with an explicit warning: the holding period behind the 82 bp is unverified, and if the alpha arrives within a month it will not survive the 60% haircut plus a 100 bp US round trip.
4. 13D activism and spin-offs stay in the backlog.
5. Korea runs the other way on issuance. KOSDAQ-heavy SEOs rose about 3% around the announcement, then lost about 31% against the equal-weighted market over the next 12 months (2005-2010). A rights-offering/CB dilution screen is therefore the most promising Korean event idea, pending a post-2015 replication on the lab's share-count data.
6. Korea's 2023-2026 reforms are structural breaks:
   - the short-sale ban and its end on 31 March 2025;
   - the Value-up programme;
   - the December 2024 CB rules;
   - the dividend record-date reform;
   - insider pre-disclosure;
   - mandatory cancellation of treasury shares under the February 2026 Commercial Act amendment.

   Any signal that depends on them has fewer than the 882 post-reform sessions the gate needs. It should be reported as INSUFFICIENT DATA until roughly 2028.
7. Everything else belongs in an **Event Calendar and Risk Screen** layer that can only cut exposure (multipliers ≤ 1.0, as with the macro overlay).
8. Timestamps decide what is tradable. EDGAR gives acceptance date-times. OpenDART gives dates only, so a Korean event must be treated as usable at the next close unless a time-of-day source (KIND) is verified.

**House arithmetic used throughout (from the QUANTGEN brief).**
- Round-trip costs: US shares via KIS 100 bp (200 bp at 2x stress); KRX stocks 70 bp (140 bp at 2x).
- Availability rule: QUANTGEN decides at the close of day t and earns from t+1.
  - An event public before the close of t can be acted on at that close.
  - An after-close event can only be acted on at the close of t+1, so the day-1 reaction is lost.
- Screens versus signals: a screen removes names from the long universe of an existing card. It adds no turnover of its own, so a long-run *negative* drift that cannot be shorted is still monetisable as a screen.
- Gate length: 756 in-sample plus 126 out-of-sample sessions is 882 sessions, about 3.5 years *per regime*.
- Gate step 9 applies a 60% live haircut to any historical drift that survives.

---

## 1. IPOs and seasoned offerings: long-run underperformance, lock-up expiries, SEO announcement returns

### Takeaway
US IPO long-run underperformance has not decayed. The 2011-2024 cohorts trail style-matched firms by 16.4% over three years, with the losses concentrated in small and unprofitable issuers. QUANTGEN can use it only as an exclusion screen. SEO long-run underperformance has shrunk to about −2 to −3% a year on matched-firm measures, and to roughly zero on factor-model or recent-decade measures. Lock-up expiries (about −1% over three days, front-run by short sellers) are a calendar flag, not a trade.

### Cited Findings
- **Ritter (1991, JF).** IPOs issued in 1975-84 substantially underperformed matching firms from the first-day close to their third anniversary. Underperformance was worst for firms that went public in high-volume years, consistent with issuers exploiting "windows of opportunity". [US; 1975-84; in-sample (IS); gross] — [Ritter 1991, RePEc](https://ideas.repec.org/a/bla/jfinan/v46y1991i1p3-27.html)
- **Loughran-Ritter (1995, JF).** Issuers in 1970-1990 delivered only about 5% a year (IPOs) and 7% a year (SEOs) over five years. An investor would have needed 44% more money in issuers than in size-matched non-issuers to end with the same wealth after five years. Book-to-market explains only a modest part. [US; 1970-1990; IS; gross] — [Loughran-Ritter 1995, EconPapers](https://econpapers.repec.org/RePEc:bla:jfinan:v:50:y:1995:i:1:p:23-51)
- **Ritter's updated long-run table (Table 19), all IPOs.** 9,253 US IPOs from 1980-2024, with returns through 31 Dec 2025. Average 3-year buy-and-hold return from the first close: +19.1%. Market-adjusted: −20.5%. Style-adjusted (size and book-to-market matched): −8.9%. [US; 1980-2024; cohorts from 1995 on are out-of-sample (OOS) relative to Loughran-Ritter; gross] — [Ritter, Long-run returns on IPOs](https://site.warrington.ufl.edu/ritter/files/IPOs-long-run-returns-on-IPOs.pdf)
- **Ritter, sub-periods** (3-year market-adjusted / style-adjusted). Same source.

  | Cohort | IPOs | Market-adjusted | Style-adjusted |
  |---|---|---|---|
  | 1980-89 | 2,047 | −22.6% | +2.2% |
  | 1990-98 | 3,616 | −21.0% | −0.1% |
  | 1999-2000 | 856 | −31.8% | −58.9% |
  | 2001-10 | 1,010 | +2.2% | −7.6% |
  | 2011-24 | 1,724 | −24.7% | −16.4% |

  The row counts and weighted averages reproduce the published totals, so the extraction is internally consistent.
- **Ritter, cross-section** (1980-2024, 3-year style-adjusted). Same source.
  - By pre-IPO sales (2025 dollars): below $10m −34.0% (1,739 IPOs); $10-20m −20.6%; $20-50m −9.6%; $50-100m −4.6%; $100-500m +5.4%; $500m and above −3.0%.
  - By profitability: unprofitable −23.4% (3,926 IPOs) versus profitable +1.8% (5,327).
  - By backing: VC-backed −3.2% versus non-VC −12.8%.
- **Ritter, IPO volume and first-day returns** (mean first-day return, number of IPOs). [US; gross; not capturable by a close-to-close desk] — [Ritter, IPO Statistics (2026 update)](https://site.warrington.ufl.edu/ritter/files/IPO-Statistics.pdf)

  | Year | First-day return | IPOs |
  |---|---|---|
  | 2015 | 19.2% | 118 |
  | 2016 | 14.5% | 75 |
  | 2017 | 13.0% | 107 |
  | 2018 | 18.5% | 134 |
  | 2019 | 23.5% | 113 |
  | 2020 | 41.6% | 165 |
  | 2021 | 32.1% | 311 |
  | 2022 | 48.9% | 38 |
  | 2023 | 11.9% | 54 |
  | 2024 | 15.3% | 73 |
  | 2025 | 29.3% | 90 |

- **Ritter, international first-day returns** (document dated 30 Mar 2026). Korea averages 52.8% (2,588 IPOs, 1980-2025), against the US at 17.7% (14,079 IPOs, 1960-2025), Japan 48.7%, Taiwan 37.5% and China 159.3%. — [Ritter, International IPO underpricing](https://site.warrington.ufl.edu/ritter/files/IPOs-International.pdf)
- **Ritter's SEO tables** (five-year geometric mean annual returns; issuer versus size-matched, then the style-matched gap). [US; IS to 1990, OOS after; gross] — [Ritter, SEO long-run tables 1970-2011](https://site.warrington.ufl.edu/ritter/files/2015/04/Seasoned-Equity-Offerings-from-1970-2011-Tables-2013-06.pdf)

  | Period | SEO firms | Size-matched | Gap | Style-matched gap |
  |---|---|---|---|---|
  | 1970-79 | 11.7% | 18.4% | −6.8 pp | −6.3 pp |
  | 1980-89 | 9.3% | 15.7% | −6.4 pp | −4.3 pp |
  | 1990-98 | 14.3% | 16.5% | −2.3 pp | −2.6 pp |
  | 1999-2000 | 7.5% | 16.4% | −8.1 pp | −6.1 pp |
  | 2001-11 | 8.8% | 11.0% | −2.2 pp | −2.6 pp |

- **Eckbo-Masulis-Norli (2000, JFE)**, 4,860 SEOs from 1964-1995.
  - Five-year underperformance against matched firms for industrials is −23.2% equal-weighted and −10.6% value-weighted.
  - Jensen alphas in a six-factor macro model are insignificant.
  - Issuers' lower leverage and higher liquidity reduce risk (NYSE/Amex industrial turnover rises from 5.72% to 7.08%).
  - The paper cites prior work showing a −3% average two-day announcement return for NYSE/Amex SEOs.

  [US; IS; gross] — [Eckbo-Masulis-Norli 2000 (PDF)](https://ronmasulis.wordpress.com/wp-content/uploads/2013/08/seasoned-public-offerings-resolutions-of-the-new-issues-puzzle.pdf)
- **Fu-Huang (2016, Management Science 62(4)).** Long-run abnormal returns after both repurchases and SEOs disappear for events in the most recent decade. The authors attribute this to:
  - more institutional ownership;
  - lower trading costs and better liquidity;
  - tighter governance and disclosure regulation;
  - firms timing issues less opportunistically.

  [US; post-publication OOS for the 1995 papers] — [Fu-Huang 2016, SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1936187)
- **Field-Hanka (2001, JF)**, 1,948 lock-up expirations. They find:
  - a statistically significant abnormal return of about −1.5% over the three days around expiry;
  - a permanent rise of about 40% in trading volume;
  - much larger effects when the firm is VC-financed.

  [US; pre-2000 sample; IS; gross] — [Field-Hanka 2001, SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=236029)
- **Gibbs-Hao (SWFA 2014 working paper)**, 213 IPOs from 2005-2006.
  - The [−1,+1] market-adjusted return is −0.97% (significant at 5%). The expiry-day return of −0.37% is not significant.
  - Abnormal short selling is 39% above benchmark in days −5 to −1, and short sellers appear informed.
  - VC-backed IPOs show −1.58% with volume about 2.15x normal; PE-backed IPOs show no effect.
  - SDC records lock-up dates one day early.

  [US; OOS relative to Field-Hanka; gross] — [Gibbs-Hao (PDF)](https://mediacast.blob.core.windows.net/production/Faculty/StoweConf/submissions/swfa2014_submission_184.pdf)

### Inferences
- A 3-year style-adjusted gap of −16.4% for 2011-2024 is roughly −6% a year compounded. As an *exclusion* of recent IPOs from QUANTGEN's long universe, it costs almost nothing in turnover and clears costs easily. As a short it would fail: borrow fees, recalls and squeezes in hot IPOs make it infeasible, and QUANTGEN has no order path anyway.
- The cross-section says the screen should be conditional. The losses sit in issuers with sales below $50m, unprofitable issuers and non-VC issuers; large profitable IPOs are roughly neutral. Proposed rule (to be gated): exclude unprofitable IPOs, or those with pre-IPO sales below $50m, for 36 months after listing, and cap other IPOs at 0.5x weight.
- From the syndicate desk: issuers sell when they can, not when they must. The hot cohorts were the worst performers:
  - 1999-2000, style-adjusted −58.9%;
  - 2020-2021, with 311 IPOs in 2021 collapsing to 38 in 2022.

  IPO count and first-day returns are therefore a *supply-heat* context indicator. Under the macro panel's rule they can size risk at most, never set direction.
- Lock-ups: an effect of about −1% is below the 100 bp US round trip, needs a short, and is already front-run by short sellers (Gibbs-Hao). So it is a **calendar flag**: no new long entries in IPO names during [−5,+1] around a major expiry, especially VC-backed names.
- SEOs: the evidence is method-dependent. Matched-firm returns are still −2.2 to −2.6 pp a year for 2001-2011, while factor-model alphas are about zero (Eckbo et al.) and recent-decade drift has vanished (Fu-Huang). This is mostly exposure to known investment and issuance factors. It belongs in a *net-issuance* fundamental factor (12-month change in split-adjusted shares), not in an event card.

### Gaps
- The exact numbers in Ritter (1991) (sample size, wealth relative) were not verified; the full text sits behind JSTOR.
- No US SEO announcement-return estimate for the last decade was found. Only the historical −3% two-day figure, cited via Eckbo et al., is available.
- Separate long-run results for the 2020-2021 cohorts were not extracted. Ritter's 2023-2024 cohorts have truncated three-year windows.
- The Field-Hanka sample period was not extracted.
- Ritter's technology split was excluded: its rows are measured from a different base and do not reconcile with the totals.
- No study of long-run returns or lock-up expiries for Korean IPOs was found (see DC1 and DC2). The KRX first-day price-band reform for new listings was not verified.

---

## 2. Payouts: buybacks, dividend initiations and omissions, Korean treasury-share cancellation and Value-up disclosures

### Takeaway
US buyback drift was large in 1980-1990 but has disappeared on post-2003 events. Announcement reactions also shrank, and shrink further with repetition, so a US buyback card should be dropped. Drift after dividend initiations and omissions is not robust. In Korea, the payout story is a 2024-2026 policy regime: Value-up disclosures, record-date reform and mandatory treasury-share cancellation from February 2026. Its event returns either sit on day 0 (Value-up: about +1.5% on the day, about +1% retained), so they are uncapturable at the close, or have too little post-reform history for the gate.

### Cited Findings
- **Ikenberry-Lakonishok-Vermaelen (1995, JFE).** For open-market repurchase announcements in 1980-1990, the average abnormal four-year buy-and-hold return is +12.1%. It is +45.3% for value stocks, with no positive drift for glamour stocks. [US; 1980-90; IS; gross] — [ILV, NBER w4965](https://econpapers.repec.org/RePEc:nbr:nberwo:4965)
- **Peyer-Vermaelen (2009, RFS).** They reject the claim that buyback anomalies have disappeared, using more recent data. Open-market buybacks follow large analyst downgrades and overly pessimistic long-term forecasts. [US; post-publication; gross] — [Peyer-Vermaelen 2009, RePEc](https://ideas.repec.org/a/oup/rfinst/v22y2009i4p1693-1745.html)
- **Fu-Huang (2016).** Long-run abnormal returns after repurchases (and SEOs) disappear for recent-decade events. A later summary dates the disappearance to 2003-2012. [US; post-publication OOS] — [Fu-Huang 2016, SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1936187); [JRFM 2020 summary](https://www.mdpi.com/1911-8074/13/8/176). *Conflict:* Peyer-Vermaelen (2009) argue persistence on earlier data.
- **JRFM 2020 (13(8):176)**, US open-market repurchase announcements from 1996-2014.
  - The 2-day CAR is 2.4% overall and 1.78% since 2000. The authors' literature review cites a fall from above 3% in the 1980s to about 1% by 2004.
  - One-time repurchasers earned 3.56%, against 1.83% for repeat repurchasers.
  - By sequence: first 2.51%, second 1.77%, third 1.25%, fifth or later 0.89%.

  [US; gross; the announcement reaction is not capturable at the close] — [JRFM 2020](https://www.mdpi.com/1911-8074/13/8/176)
- **Manconi-Peyer-Vermaelen (2019, JFQA)**, more than 9,000 buyback announcements in 31 non-US countries. Short- and long-term excess returns are significantly positive. They are larger where undervaluation is likely and where markets are less efficient or liquid. They are not simply takeover-risk compensation and have not weakened in recent years. [ex-US; gross] — [Manconi-Peyer-Vermaelen 2019, RePEc](https://ideas.repec.org/a/cup/jfinqa/v54y2019i05p1899-1935_00.html)
- **Michaely-Thaler-Womack (1995, JF).**
  - Three-day announcement returns are −7.0% for omissions and +3.4% for initiations.
  - Market-adjusted returns over the next 12 months (excluding the announcement month) are +7.5% for initiators and −11.0% for omitters.
  - The combined strategy was positive in 22 of 25 years.

  [US; IS; gross] — [MTW, NBER w4778](https://ideas.repec.org/p/nbr/nberwo/4778.html)
- **Boehme-Sorescu (2002, JF)**, 1927-1998. Drift after initiations and resumptions is significant in equal-weighted calendar-time portfolios but insignificant value-weighted, and not robust across subsamples. Factor loadings fall after the event, suggesting the drift may be chance. [US; OOS extension; gross] — [Boehme-Sorescu 2002, RePEc](https://ideas.repec.org/a/bla/jfinan/v57y2002i2p871-900.html)
- **Liu-Szewczyk-Zantout (2008, JF)**, 2,337 cuts and omissions from 1927-1999. Negative drift lasting one year disappears after controlling for earnings-announcement drift and the distribution of buy-and-hold abnormal returns. [US; gross] — [Liu-Szewczyk-Zantout 2008, RePEc](https://ideas.repec.org/a/bla/jfinan/v63y2008i2p987-1020.html)
- **Third Commercial Act amendment** (passed 25 Feb 2026: 175 in favour and one abstention among 176 present). — [Seoul Shinmun, 26 Feb 2026](https://www.seoul.co.kr/news/politics/2026/02/26/20260226001004)
  - Newly acquired treasury shares must be cancelled within one year.
  - Existing holdings get a six-month grace period, so 18 months in total.
  - Retention for purposes such as employee compensation or an ESOP needs AGM approval.
  - Firms with foreign-ownership limits must dispose within three years.
  - The first amendment (July 2025) and the second (August 2025) covered: directors' duty to shareholders, cumulative voting, separate election of audit-committee members, and electronic AGMs.
- **FSC, 23 Jun 2026** (enforcement-decree amendment; promulgated and effective 30 Jun 2026). — [FSC 23 Jun 2026](https://www.fsc.go.kr/no010101/87169)
  - All listed holders of treasury shares must now disclose cancellation deadlines and the content of approved holding/disposal plans. Previously only holders of 1% or more had to disclose.
  - Cancellations totalled KRW 21.4tn in 2025 and KRW 43.1tn in January-May 2026.
- **FSC treasury-share reform (3 Jun 2024 notice).** — [FSC 3 Jun 2024](https://www.fsc.go.kr/no010101/82390); [FSC treasury-share releases list](https://www.fsc.go.kr/no010101?srchCtgry=&curPage=&srchKey=sj&srchText=%EC%9E%90%EA%B8%B0%EC%A3%BC%EC%8B%9D&srchBeginDt=&srchEndDt=)
  - Treasury shares may no longer receive new shares in personnel spin-offs (인적분할) or mergers (the "treasury-share magic").
  - A board-approved report on purpose and plan is required once holdings reach 5%.
  - Disposals must disclose purpose, counterparty rationale and dilution.
  - Buyback trusts face tighter rules, including an explanation when actual purchases fall short of the plan.
- **Value-up event study (KCMI, Kang So-hyun, reported 27 May 2026).**
  - Announcement-day excess return was about 1.5%, with about 1% retained afterwards.
  - Effects were larger for smaller firms, firms with fewer tangible assets, low analyst coverage and few IR events.
  - Disclosers outperformed non-disclosers by 45.3 pp over May 2024-Feb 2026.

  [KR; 2024-Feb 2026; gross] — [Money Today, 27 May 2026](https://www.mt.co.kr/stock/2026/05/27/2026052715542995595)
- **KCMI (An Yu-mi, Capital Market Focus No. 11, 1 Jun 2026).** — [KCMI report](https://www.kcmi.re.kr/publications/pub_detail_view?syear=2026&zcd=002001016&zno=1917&cno=6774)
  - 718 disclosing firms by April 2026 (339 KOSPI, 375 KOSDAQ).
  - Disclosers' cap-weighted index reached 203.3 against 134.5 for non-disclosers (end-2023 = 100), a 68.8 pp gap.
  - KOSPI disclosers: ROE 11.2% in 2025; PBR from 1.4x (2021) to 1.9x (Q1 2026); payout 30.5% against 14.1% for non-disclosers; buybacks of KRW 20.7tn in 2025 (94.8% of the market total).
- **Korea Value-up Index** (Daeshin Economic Research Institute via KDI EIEC, 29 Jul 2025). The index (100 firms) launched in September 2024, and 12 ETFs started in November 2024 with about KRW 500bn. The index did reasonably well against the market, but the products failed to attract flows. — [KDI EIEC](https://eiec.kdi.re.kr/policy/domesticView.do?ac=0000199677)

### Inferences
- **Value-up.** The post-day-0 drift is about 1% minus 1.5%, so zero or negative. Under the decide-at-close rule nothing is left. The 45-69 pp outperformance is a selection effect, not an event return: disclosers are large-cap, high-payout firms, and the 2025-26 semiconductor rally falls in the window. **DROP as a signal; keep as CONTEXT.**
- **Korean treasury shares.** Mandatory cancellation turns a discretionary, and therefore informative, signal into a mechanical one. Information per event should fall, just as US repeat-buyback reactions decay from 2.51% to 0.89% with repetition. The jump from KRW 21.4tn (2025) to KRW 43.1tn in five months of 2026 points to saturation. Any Korean buyback/cancellation card must be estimated on post-2024 data only, which leaves fewer than 882 sessions. The gate verdict would be INSUFFICIENT DATA until about 2028. **BACKLOG.**
- **Practitioner view (unverified).** Korean trust-based buybacks were historically often left incomplete. The FSC's 2024 requirement to explain shortfalls against the plan is consistent with this having been a supervisory concern.
- **US buybacks.** The persistent part (Peyer-Vermaelen: value plus analyst pessimism) overlaps the value and quality factors that the fundamental panel will build. As a stand-alone event card: **DROP.**
- **Dividends.** Initiation and omission drift is absorbed by earnings drift (Liu et al.). Omissions are a distress marker that the quality card should already capture. **DROP the signal; keep omission as a low-priority RISK FLAG.**

### Gaps
- No event study of Korean buyback or cancellation announcements (before or after 2024) was found (see DC9).
- No US buyback evidence after 2014 was found, and nothing on the 1% US buyback excise tax (2023).
- The status of the SEC's 2023 repurchase-disclosure rule could not be verified (pages returned 404/503). The details of Reg S-K Item 703 were not verified either.
- The promulgation and effective date of the third Commercial Act amendment itself (as opposed to the decree effective 30 Jun 2026) was not verified from a primary legal source.

---

## 3. M&A and restructuring: target and acquirer announcement returns, merger arbitrage, spin-offs, activism

### Takeaway
Takeover premia and acquirer losses are announcement-day events that QUANTGEN cannot capture. Merger arbitrage is a short-put trade whose spread compressed after 2001, which leaves about 2% gross: below costs and with crash risk. Spin-off outperformance is old evidence, partly explained by later takeovers. Activism (13D) is the only US restructuring event with documented positive post-filing returns and no reversal. Even then, the part left after the filing day is probably only about 1-2% gross. In Korea the relevant evidence is about tunneling inside chaebols, which supports a risk screen rather than a signal.

### Cited Findings
- **Andrade-Mitchell-Stafford (2001, JEP).** Over 1973-1998 the combined announcement response of merging parties is positive. 1990s mergers were mostly stock swaps, hostile takeovers almost vanished, and deregulation accounts for nearly half of merger activity since the late 1980s. [US; IS; abstract-level only] — [AEA abstract](https://www.aeaweb.org/articles?id=10.1257/jep.15.2.103)
- **Moeller-Schlingemann-Stulz (2004, JFE; NBER w9523)**, 12,023 acquisitions from 1980-2001.
  - Acquirers lost $218bn at announcement: small acquirers gained $8bn, large ones lost $226bn.
  - Size matters more than financing.
  - Only acquisitions of subsidiaries show positive aggregate gains.
  - Losses after 1997 are dramatic.

  [US; IS; gross] — [NBER w9523](https://www.nber.org/papers/w9523)
- **Moeller-Schlingemann-Stulz (2005, JF; NBER w10200).** In 1998-2001 acquirers lost 12 cents per dollar spent ($240bn), against 1.6 cents ($7bn) in the 1980s. Their losses exceeded targets' gains by $134bn, driven by a small number of deals by highly valued acquirers. [US] — [NBER w10200](https://www.nber.org/papers/w10200)
- **Mitchell-Pulvino (2001, JF)**, 4,750 deals from 1963-1998.
  - Risk arbitrage earned about 4% a year in excess returns after transaction costs.
  - Returns were correlated with the market in severe declines and uncorrelated otherwise, like writing uncovered index puts.

  [US; IS; net of their cost assumptions] — [Mitchell-Pulvino 2001, SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=268144)
- **Jetley-Ji (2010, FAJ).**
  - The median first-day arbitrage spread was 4.10-7.94% for deals before 2001 and 1.74-2.63% after 2001, a compression of more than 400 bp from 2002.
  - Hedge-fund merger-arb alpha fell by about 41 bp a month (4.81 pp a year) in 2002-2007.
  - Causes: lower deal costs and more arbitrage capital. The decline is probably permanent, and investors should judge funds on post-2002 returns.

  [US; post-publication OOS] — [Jetley-Ji 2010, RePEc](https://ideas.repec.org/a/taf/ufajxx/v66y2010i2p54-68.html)
- **Mitchell-Pulvino (2012, JFE).** In 2008, prime-broker distress cut hedge-fund leverage abruptly. Through rehypothecation, apparently long-term funding became short-term, and arbitrageurs could not keep similar assets priced alike. [US; crisis episode] — [Mitchell-Pulvino 2012, RePEc](https://ideas.repec.org/a/eee/jfinec/v104y2012i3p469-490.html)
- **Cusatis-Miles-Woolridge (1993, JFE)**, 146 tax-free spin-offs from 1965-1988 (matched-firm BHAR at 6/12/24/36 months).
  - Spun-off firms: −1.0%, +4.5%, +25.0%, +33.6%.
  - Parents: +6.8%, +12.5%, +26.7%, +18.1%.
  - The 21 spun-off firms later taken over: +61.3% at 24 months and +99.3% at 36 months.
  - The 125 not taken over: +18.9% and +22.5%, both insignificant.

  [US; IS; gross] — [CMW 1993 (PDF)](https://longrunplan.com/wp-content/uploads/2018/09/restructuring-through-spinoffs.pdf); [RePEc record](https://ideas.repec.org/a/eee/jfinec/v33y1993i3p293-311.html)
- **McConnell-Ovtchinnikov, "Predictability of Long-Term Spin-off Returns"**, 311 spin-offs (267 parents) from 1965-2000.
  - Spun-off subsidiaries returned +19.4%, +24.4% and +26.3% at 12, 24 and 36 months against industry- and size-matched benchmarks.
  - Parents returned about +5% over 36 months after removing one outlier, which is insignificant.
  - Parents' excess returns fade in 1989-2000.

  [US; partly OOS relative to CMW; gross] — [McConnell-Ovtchinnikov (ResearchGate)](https://www.researchgate.net/publication/228289308_Predictability_of_Long-Term_Spin-Off_Returns)
- **Brav-Jiang-Partnoy-Thomas (2008, JF)**, 1,059 hedge-fund/target pairs from 2001-2006 (236 funds, 882 targets).
  - The abnormal return over [−20,+20] is about 7-8%, reaching 7.2% by day +20. It includes a 3.2% run-up over days −10 to −1 and a 2.0% move on the filing day.
  - 62% of events are positive; the median is 4.6%.
  - There is no negative drift over the following year.
  - Outcomes: 66.4% success or partial success, 21.4% failure.
  - By objective: sale of the company 8.54%, business strategy 5.95%, undervaluation 6.28%, capital structure 1.47% (insignificant), governance 1.73% (insignificant).
  - Targets decline when activists exit after failing.

  [US; IS; gross] — [BJPT 2008 (Duke PDF)](https://law.duke.edu/sites/default/files/centers/gfmc/session_3/2_brav_et_al-hedge_fund_activism-2008.pdf); [BJPT, Returns to activism, SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1111778)
- **Brav-Jiang-Li (2022, ECGI WP 797/2021)**, 4,094 events from 1994-2018. The positive short-term abnormal return and the absence of a longer-term reversal remain robust. Activists buy 3.8% of shares in the 60 days before disclosure. Under the old rule, the 13D was due within 10 days of crossing 5%. [US; partly OOS (2007-2018); gross] — [Brav-Jiang-Li (ECGI PDF)](https://www.ecgi.global/sites/default/files/working_papers/documents/bravjianglifinal_0.pdf)
- **SEC beneficial-ownership amendments (adopted October 2023).** Initial 13D: five business days instead of 10 days. 13D amendments: two business days. The filing cut-off was extended to 10 p.m. ET. Schedule 13G deadlines were also shortened, with compliance from 30 Sep 2024. — [SEC fact sheet 33-11253](https://www.sec.gov/files/33-11253-fact-sheet.pdf)
- **Bae-Kang-Kim (2002, JF).** When chaebol-affiliated firms make acquisitions, their share prices typically fall. Minority shareholders lose, while controlling shareholders gain through the higher value of other group firms (tunneling). [KR] — [Bae-Kang-Kim 2002, RePEc](https://ideas.repec.org/a/bla/jfinan/v57y2002i6p2695-2740.html)
- **Baek-Kang-Lee (2006, JF).** Intragroup private offerings of equity-linked securities are priced to benefit controlling shareholders. When securities are sold to affiliates at a premium, chaebol issuers' announcement returns are 8.8% higher, and affiliated acquirers' returns are 5.8% lower, than other issuers' and acquirers'. [KR] — [Baek-Kang-Lee 2006, RePEc](https://ideas.repec.org/a/bla/jfinan/v61y2006i5p2415-2449.html)

### Inferences
- Under decide-at-close, both the target premium and the acquirer's move fall on the announcement day and are lost. The only post-announcement trade is merger arbitrage. Its median spread of about 2% after 2001 (Jetley-Ji) is near or below the 200 bp stressed US round trip, carries short-put left-tail risk (2008) and needs shorting in stock deals. **DROP as a strategy.**
- **Practical risk screen.** Announced cash targets have pinned prices, which would corrupt QUANTGEN's reversal, volatility-scaling and momentum cards (artificially low volatility and mean reversion). Exclude announced targets, including Korean 공개매수 (tender offer) and 합병 (merger) targets, from technical cards between announcement and completion or termination. **RISK SCREEN.**
- **Spin-offs.** The evidence is pre-2000, partly explained by takeovers, and parent returns fade after 1989. There are few US spin-offs a year, so an event portfolio would be thin, and the gate would likely return INSUFFICIENT DATA or fail plateau and year-positivity. **BACKLOG.**
- **Activism.** The tradable remainder after the filing-day close is at most about 7.2% − 3.2% − 2.0% ≈ 2.0% over days +1 to +20. This is my arithmetic on BJPT's cumulative figures and assumes days −20 to −11 are near zero. After a 100 bp US round trip, about 1% net is left. The 2024 deadline change (five business days) probably moves more of the reaction onto the filing day, so post-filing drift may shrink. **BACKLOG**, with a specific test (DC10-style design on SC 13D acceptance times).
- **Korea.** The chaebol tunneling evidence supports a *risk screen* on the acquiring side of intragroup deals, for example affiliates buying affiliate shares or assets at premiums. The 2025 amendments (directors' duty to shareholders) may reduce such deals, which is a regime break. **RISK SCREEN, BACKLOG.**

### Gaps
- The Andrade-Mitchell-Stafford table of announcement returns could not be fetched (HTTP 403), so no target/acquirer percentages are quoted.
- No post-2010 US evidence on post-announcement drift for acquirers or targets was found, and no merger-arbitrage returns after 2010.
- Dated deal-break episodes (for example the 2024 antitrust blocks) could not be fetched (403), so no numbers are given.
- The post-2000 spin-off study (McConnell-Sibley-Xu, 2001-2013) could not be fetched (403).
- No evidence was found on Korean activism (5% filings declaring a control or management purpose, 경영참가). Korean 5%-rule filing deadlines, statutory merger-ratio rules and appraisal-right arbitrage, and physical-split (물적분할) evidence were not verified.

---

## 4. Index events: S&P 500 inclusion, KOSPI 200 rebalancing, MSCI

### Takeaway
The S&P 500 inclusion effect has essentially disappeared: additions went from +7.3% in the 1990s to an insignificant +0.8% in the 2010s, and deletions from −16.1% to −0.6%. The cause is a roughly 20-fold drop in price impact per unit of index demand, plus migrations from the S&P 400. Older Korean evidence shows KOSPI 200 price pressure into the effective date and a next-day reversal. A pre-reconstitution long-short that earned +15-21% in 2008-09 lost −2.5% by 2012. Index events are therefore calendar flags. MSCI reclassification is context: Korea was not even placed on the watch list in June 2026.

### Cited Findings
- **Greenwood-Sammon, "The Disappearing Index Effect"** (HBS working paper, December 2022; published in the Journal of Finance in 2025 per the Wiley listing). — [Greenwood-Sammon (PDF, marcosammon.com)](https://marcosammon.com/images/greenwood_sammon.pdf); [same, Ivey-hosted PDF](https://www.ivey.uwo.ca/media/m2kh5j5y/the-disappearing-index-effect.pdf); [JF listing](https://onlinelibrary.wiley.com/doi/10.1111/jofi.13410)
  - **Sample:** S&P 500 changes from 1980-2020; 752 additions and 749 deletions matched to CRSP.
  - **Announcement-to-effective abnormal returns.** Additions: 3.4% (1980s), 7.3% (1990s), 5.1% (2000s), 0.8% (2010s, statistically indistinguishable from zero). Deletions: −4.6%, −16.1%, −12.4%, −0.6% (indistinguishable from zero).
  - **Announcement-day returns.** Additions: 3.36%, 5.15%, 4.13%, 1.05%. Deletions: −4.71%, −14.4%, −10.1%, −0.2%.
  - **Timing:** the average gap from announcement to effective date is 4.8 days for additions and 5.8 for deletions.
  - **Why the effect declined:**
    - Migrations from the S&P 400 explain roughly 35-50% of the decline. They now make up more than 60% of additions, and their returns fell from +6.4% in the late 1990s to −1.8% in the 2010s.
    - Price impact per unit of demand fell by a factor of about 20 for additions between the 1990s and 2010s.
    - Greater predictability and composition changes explain little.
  - **Demand:** index trackers buy about 7-8% of shares at addition by 2020, yet total institutional ownership barely moves.
  - **Pre-announcement returns [−20,−1]:** additions 2.15% (1990s) versus 2.47% (2010s); deletions −14.7% versus −2.4%.
  - **Tesla (December 2020):** more than 2% of index capitalisation, +5.2% announcement return and +4.5% implementation return, with an unusual 32-day gap. As extracted, the 2020 average effect excluding Tesla was about −3 bp.

  [US; post-publication OOS relative to the 1986 index-effect papers; gross]
- **Yun-Kim (KAIST; International Review of Financial Analysis 2010)**, KOSPI 200 regular changes from June 1995 to June 2008 (265 additions, 235 deletions).
  - Additions: +0.94% on the day before announcement (t 4.41), −0.36% on the day after; +2.24% on the day before the effective date (t 8.75), then −1.04% on the day after (t −3.65).
  - Deletions: −1.32% on the day after announcement; −0.90% on the effective date.
  - Reversals are partial. In 2002-2008 a permanent price effect lasts at least two months.
  - A volume run-up indicates anticipatory trading. The changes are not information-free.

  [KR; IS; gross] — [Yun-Kim (KASBA PDF)](https://kasba.or.kr/uploads/papers/NODE06081483.pdf)
- **Mirae Asset Securities, KOSPI 200 reconstitution note (2 May 2013).**
  - Over the prior five years, the average 20-day pre-reconstitution return was +2.01% for additions and −5.27% for deletions, a 7.62% long-short spread.
  - Long-short by year: 2008 +15.16%, 2009 +20.86%, 2010 +3.18%, 2011 +1.43%, 2012 −2.53%.
  - Expected entrants' prices tended to start falling two days before reconstitution.

  [KR; broker research; gross] — [Mirae Asset note (PDF)](https://securities.miraeasset.com/bbs/maildownload/0904fc52804d0a23)
- **MSCI's 2026 market-classification review (24 Jun 2026).** Korea stays in Emerging Markets and was not placed on the Developed Market watch list. — [Korea Times, 24 Jun 2026](https://www.koreatimes.co.kr/economy/20260624/msci-keeps-korea-off-developed-market-watchlist-but-global-analysts-stay-bullish); [Korea Herald](https://www.koreaherald.com/article/10786876)
  - **Reasons cited:** limited offshore convertibility of the won; limited operational use of omnibus accounts and in-kind transfers; the operational burden of the reinstated short-selling compliance regime. 24-hour won trading from July 2026 may need an observation period.
  - **Timeline:** per the Korea Herald, an upgrade is at least 3-4 years away even if Korea makes the watch list next year. A strategist warned that an upgrade could force selling by EM funds while global funds focus on the large semiconductor names.
  - **Reforms already made:** FX hours extended, an offshore won settlement framework, foreign-investor registration abolished, LEIs adopted, more English disclosure, wider omnibus use, and short selling resumed.

### Inferences
- **S&P 500.** In the 2010s the residual after day 1 (from the day-1 close to the effective date) is roughly 0.8% − 1.05% ≤ 0. Nothing is left for a desk that decides at the close, and certainly not after 100 bp. **DROP.** The lesson for QUANTGEN's gate: a famous anomaly lost about 90% of its size within two decades as arbitrage capital grew, which justifies step 9's 60% live haircut.
- **Tesla in 2020** shows that a mega-addition can revive the effect. A mechanical rule to "fade index adds" is unsafe even though the average effect is dead. **CONTEXT.**
- **KOSPI 200.** The old pattern of price pressure the day before the effective date and reversal the day after gives a **calendar flag**:
  - never initiate a long in a newly added stock at the close on the day before the effective date; if a signal says buy, wait until after the day after the effective date;
  - never sell a deleted stock into the effective-date close.

  Whether a tradable drift from announcement to the day before the effective date still exists after 2013 is unknown. **BACKLOG (DC4).** Mirae's 2012 note already shows crowding, with entrants' prices falling two days early.
- **MSCI.** There is no event to trade before about 2029. MSCI quarterly review dates and KOSPI 200/KOSDAQ 150 rebalances should still enter the calendar as liquidity flags, alongside the macro panel's Samsung and SK hynix concentration caps.

### Gaps
- No KOSPI 200 event study for 2015-2026 was found. KRX's current review schedule and announcement lead time were not verified.
- No evidence on MSCI inclusion or deletion events in Korea was found.
- S&P DJI's own research on the index effect was not fetched (the web-search budget ran out).
- Greenwood-Sammon do not document post-effective-date reversal in the US.

---

## 5. Insider and analyst events: Form 4 insider buying, Korean insider pre-disclosure, analyst initiations and recommendations, earnings guidance

### Takeaway
US *opportunistic* (non-routine) insider trades are the strongest surviving corporate-event signal: 82 bp a month value-weighted in 1986-2007, little price reaction at filing, and timestamped public data. The information comes from purchases. How the 82 bp portfolio was built (long-only or buys minus sells, holding period) was not verified here, and that decides whether it clears costs. Insider sales carry no information. Analyst-recommendation strategies make money gross but not net, and QUANTGEN has no analyst data. Korea's 2024 insider pre-disclosure rule creates a usable *supply* calendar flag.

### Cited Findings
- **Cohen-Malloy-Pomorski (2012, JF; NBER digest).**
  - Over 1986-2007, a strategy on opportunistic insider trades earned 82 bp a month in value-weighted abnormal returns.
  - Routine trades, more than half of all insider trades, earned essentially zero.
  - Opportunistic trades predict future news and events, and opportunistic trading fell after SEC enforcement announcements.

  [US; IS; gross] — [NBER Digest, "Decoding Inside Information"](https://www.nber.org/digest/apr11/decoding-inside-information)
- **Jeng-Metrick-Zeckhauser (2003, REStat).** Insider purchases earn abnormal returns of more than 6% a year; insider sales do not earn significant abnormal returns. [US; IS; gross] — [JMZ 2003, RePEc](https://ideas.repec.org/a/tpr/restat/v85y2003i2p453-471.html)
- **Lakonishok-Lee (2001, RFS)**, 1975-1995.
  - Prices move very little when insiders trade or report their trades.
  - Cross-sectional predictive power comes mainly from smaller firms.
  - Purchases are informative; sales are not.

  [US; IS] — [Lakonishok-Lee 2001, RePEc](https://ideas.repec.org/a/oup/rfinst/v14y2001i1p79-111.html)
- **SEC Rule 10b5-1 amendments** (adopted 14 Dec 2022, effective 27 Feb 2023). Forms 4 and 5 must identify trades made under 10b5-1 plans, gifts must be reported on Form 4, and plan adoptions and terminations are disclosed under Item 408. — [SEC rule page](https://www.sec.gov/rules-regulations/2022/12/insider-trading-arrangements-related-disclosures)
- **Form 4 deadline.** Form 4 is due before the end of the second business day after execution. For 10b5-1 and discretionary plans, the deemed execution date is the date the insider is notified, capped at the third business day after the trade. — [17 CFR 240.16a-3 (eCFR)](https://www.ecfr.gov/current/title-17/section-240.16a-3)
- **EDGAR filing cut-offs.** Forms 3, 4 and 5, Form 144 and Schedules 13D/13G submitted by 10 p.m. ET are deemed filed that business day. The general cut-off is 5:30 p.m. — [17 CFR 232.13 (eCFR)](https://www.ecfr.gov/current/title-17/section-232.13)
- **Korean insider pre-disclosure (from 24 Jul 2024).** — [FSC release](https://www.fsc.go.kr/no010101/82635?srchCtgry=&curPage=&srchKey=&srchText=&srchBeginDt=&srchEndDt=)
  - Officers and major shareholders (10% or more, or de facto influence) must file a trading plan 30 days in advance when trades aggregated over six months reach 1% of shares or KRW 5bn.
  - Financial investors such as pension funds are exempt, as are inheritances, M&A transfers and similar cases.
  - Fines run up to KRW 2bn.
  - Reporting applies to trades settling after 23 Aug 2024.
- **Two months into the regime (Economist Korea, Sept 2024).** An industry view held that pre-disclosure protects investors but cannot prevent price falls when a major holder wants to sell. Some holders reportedly switched to smaller on-market sales. [KR; press] — [Economist (Korea), Sept 2024](https://economist.co.kr/article/view/ecn202409130053)
- **Barber-Lehavy-McNichols-Trueman (2001, JF).** Buying stocks with the best consensus recommendations and shorting the worst earns more than 4% a year gross. It needs daily rebalancing and heavy turnover, and net abnormal returns are not reliably above zero. [US; IS; net ≈ 0] — [BLMT 2001, RePEc](https://ideas.repec.org/a/bla/jfinan/v56y2001i2p531-563.html)
- **Womack (1996, JF).** Post-recommendation drift is +2.4% for buy recommendations, modest and short-lived, and −9.1% for sell recommendations, lasting about six months. Few recommendations coincide with public news. [US; IS; gross] — [Womack 1996, RePEc](https://ideas.repec.org/a/bla/jfinan/v51y1996i1p137-67.html)
- **Altinkilic-Hansen (2009, JAE).** Recommendation revisions are usually information-free. They piggyback on recent news, momentum and short-run contrarian predictors. [US] — [Altinkilic-Hansen 2009, RePEc](https://ideas.repec.org/a/eee/jaecon/v48y2009i1p17-36.html)
- **Demiroglu-Ryngaert (2010, Financial Management)**, 549 previously neglected stocks. First analyst coverage brings a +4.86% abnormal announcement return. It is driven by positive coverage rather than coverage itself, plus liquidity and downward-sloping demand. [US; gross; announcement-only] — [Demiroglu-Ryngaert 2010, RePEc](https://ideas.repec.org/a/bla/finmgt/v39y2010i2p555-584.html)

### Inferences
- **Insider purchases** are the one corporate-event signal that ticks every box:
  - public, cheap, timestamped data (Form 4 with an EDGAR acceptance time);
  - little reaction at filing (Lakonishok-Lee), so the move is still capturable after the decide-at-close lag;
  - gross size (82 bp a month) larger than QUANTGEN's US costs, *but only if* the abnormal return keeps accruing over several months.

  **Haircut arithmetic, two cases.**
  - *If the alpha accrues evenly over months:* a 60% haircut leaves about 33 bp a month. A 63-day hold (4 round trips a year at 100 bp, about 33 bp a month) nets about zero. A 126-day hold (2 round trips, about 17 bp a month) leaves a margin.
  - *If the 82 bp is mainly a first-month effect*, as in a one-month holding-period portfolio: the alpha per event is about 82 bp, or about 33 bp after the haircut. That is below one 100 bp round trip, and the card fails.
  - If the 82 bp is a buys-minus-sells spread, the long-only part is smaller again.

  JMZ's figure of more than 6% a year for purchases is encouraging, but its holding period was not verified either. So: purchases only, value-weighted, a pre-registered 126-day hold, excluding routine traders and 10b5-1-flagged trades (flags available since 2023). **BUILD-candidate (signal)**, conditional on DC10 showing how alpha accrues over time. It cannot be tested on the lab's data.
- **Korea.** A pre-disclosed sale plan is a known future supply overhang, which is a **RISK FLAG**: no new long entries during the disclosed trading window. Its magnitude is unmeasured (DC7). Korean officer and major-shareholder purchases (OpenDART 임원·주요주주 소유보고) are **BACKLOG**.
- **Analysts.** QUANTGEN has no analyst data, and the net returns are about zero even in the original studies. **DROP.**

### Gaps
- No US insider-purchase evidence after 2007 was verified. The effect of the 2023 10b5-1 changes on signal quality is untested.
- No evidence on returns to Korean insider trades was found. The statutory deadline for Korea's officer/major-shareholder ownership report (임원·주요주주 소유상황보고) was not verified.
- Earnings guidance was not covered: the only candidate source (Anilowski-Feng-Skinner 2007) has no accessible abstract. It is better handled by the earnings-drift researcher.
- No Korea-specific analyst evidence was found, for example on how rare sell ratings are.

---

## 6. Korea specifics: rights offerings and convertible bonds, chaebol and governance events, the 2025-26 Commercial Act amendments, short-selling resumption, dividend record-date reform

### Takeaway
Korean issuance events behave unlike US ones. KOSDAQ-heavy SEOs rose about 3% around the announcement but lost about 31% against the equal-weighted market over 12 months (2005-2010). Bonus issues and splits pop about 4-5% over three days. CB rules were tightened in December 2024. This makes a dilution *risk screen* the best Korean event idea. The 2023-2026 policy changes (short-sale ban and resumption, record-date reform, insider pre-disclosure, Value-up, CB reform, mandatory treasury-share cancellation) are mostly regime breaks and calendar items, not repeatable signals.

### Cited Findings
- **Kim-Lee (2013, Korean Accounting Association)**, 734 SEOs from 2005-2010 (184 KOSPI, 550 KOSDAQ).
  - The CAR over [−10,+10] is +3.23% size-adjusted and +4.34% market-model adjusted, both significant.
  - Long-run BHARs against the equal-weighted market are about −31% to −32% at 12 months and about −46% to −47% at 24 months.
    - The text gives −31.13% and −46.39%.
    - Table 1, Panel A gives −31.92% and −46.67%, with −36.81% and −50.96% in parentheses. It was not established whether the parentheses are medians or an alternative benchmark.
  - Firms with low accrual quality show bigger short-term pops and larger long-run declines.

  [KR; 2005-10; IS; gross; weak (equal-weighted market) benchmark] — [Kim-Lee 2013 (PDF)](http://www.kaa-edu.or.kr/online3/2013_1/1.%20%EA%B9%80%EA%B2%BD%EC%88%9C,%EC%9D%B4%EC%A7%84%ED%9B%A4(2013s).pdf)
- **Ju-Ryu (2014, Korea Finance Association forum paper)**, September 2008 to June 2014: 113 stock splits and 191 bonus issues (무상증자), 154 of the latter on KOSDAQ.
  - CAR over [−1,+1] is +4.92% for splits (t 4.46) and +4.33% for bonus issues (t 5.16).
  - Positive abnormal returns persist through day +10.
  - Retail ownership and trading volume rise.
  - The text says bonus issues outperformed splits, presumably over a different window from the [−1,+1] figures.

  [KR; IS; gross] — [Ju-Ryu 2014 (PDF)](http://www.korfin.org/korfin_file/forum/15fall1-4.pdf)
- **FSC CB reform (effective 1 Dec 2024).** — [FSC 13 Nov 2024 release](https://www.fsc.go.kr/no010101/83400)
  - The actual holders of call options must be disclosed.
  - Resetting the conversion price below the 70% floor requires a special shareholder resolution for each issue.
  - Conversion-price adjustments for dilution events are capped by formula.
  - Repurchases of CBs before maturity require a major-event report with the plan (cancellation or resale).
  - Private CBs use the reference price on the payment date.
- **FSC, 27 Dec 2024 Capital Markets Act amendment.** — [FSC 27 Dec 2024](https://www.fsc.go.kr/no010101/83741)
  - Quarterly-dividend record dates can be set after the dividend is decided.
  - CB/BW issuance must be disclosed at least one week before payment.
  - Penalty caps for large-holding (5%) reporting violations rise tenfold.
- **Earlier and later CB actions.** The FSC held a CB market-soundness meeting on 23 Jan 2024, gave notice of rule changes on 27 May 2024, and announced enforcement on 29 Oct 2025 against concealment of losses on CB sales to related parties (accounting fraud). — [FSC CB releases list](https://www.fsc.go.kr/no010101?srchCtgry=&curPage=&srchKey=sj&srchText=%EC%A0%84%ED%99%98%EC%82%AC%EC%B1%84&srchBeginDt=&srchEndDt=)
- **Short-selling resumption (FSC release of 21 Mar 2025).** — [FSC 21 Mar 2025](https://fsc.go.kr/no010101/84216?curPage=&srchBeginDt=&srchCtgry=&srchEndDt=&srchKey=sj&srchText=)
  - Full resumption on 31 Mar 2025, after a full ban from 6 Nov 2023, extended from 1 Jul 2024 to 30 Mar 2025. An earlier ban had started on 16 Mar 2020.
  - New safeguards: the NSDS naked-short detection system, institutional control systems, a 90-day repayment limit (12 months with extensions), and higher penalties (4-6x illicit gains, plus prison terms).
  - Stricter temporary designation of "overheated" short-sale stocks (공매도 과열종목), with next-day restrictions, ran until 31 May 2025.
- **First day of resumption (31 Mar 2025).** KOSPI fell 2.93% to 2,482.98 and KOSDAQ fell 3.05% to 672.61. Foreign investors net sold about KRW 1.15tn on KOSPI and KRW 195.2bn on KOSDAQ. LG Energy Solution fell 6.88%, SK hynix 3.96% and Celltrion 4.01%. [KR; one day; confounded] — [Etoday, 31 Mar 2025](https://www.etoday.co.kr/news/view/2457536)
- **Dividend record-date reform (FSC, 31 Jan 2023).** — [FSC 31 Jan 2023](https://www.fsc.go.kr/no010101/79358)
  - Firms decide the dividend first and set the record date afterwards, under a Ministry of Justice interpretation and voluntary changes to articles of incorporation.
  - Quarterly dividends follow through Capital Markets Act changes, completed in the December 2024 amendment above.
  - Adoption is disclosed in governance reports from 2024.
- **Commercial Act amendments** (first, July 2025; second, August 2025; third, 25 Feb 2026, mandatory treasury-share cancellation). See §2. — [Seoul Shinmun](https://www.seoul.co.kr/news/politics/2026/02/26/20260226001004)
- **Chaebol tunneling evidence** (Bae-Kang-Kim 2002; Baek-Kang-Lee 2006) is in §3. The 2024 ban on the "treasury-share magic" in personnel spin-offs (인적분할) is in §2.

### Inferences
- **Issuance runs the opposite way to the US.** KOSDAQ issuers announce into strength (the +3.2% CAR window includes 10 pre-announcement days) and then dilute.
  - The long-run decline of about −31% over 12 months is so large that it would survive even if the equal-weighted benchmark, KOSDAQ distress and the 2008 crisis overstated it by a factor of three. A 12-month exclusion screen could then still be worth having.
  - Practitioner mechanism: third-party allotments (제3자배정) to related or purely financial investors; CBs reset to the 70% floor; call options that hand controlling shareholders cheap upside. Price falls trigger resets, and resets mechanically increase dilution.
  - The December 2024 rules should weaken this, so pre- and post-reform samples must be separated.
  - **RISK SCREEN (BUILD-candidate) pending DC3.**
- **Short-selling resumption** was a one-off regime change, not a repeatable event. Day 1 was confounded by global risk-off; the fetched article does not show this, so treat it as a caveat rather than a finding. It splits any short-interest or flow series into regimes:
  - partial resumption for KOSPI 200 and KOSDAQ 150 from May 2021 (date not verified here);
  - full ban from November 2023 to March 2025;
  - full resumption from 31 Mar 2025.

  Any card using KIS short-sale data must be estimated within a regime. **CONTEXT plus a DATA REGIME FLAG**, and a **CALENDAR FLAG** for 공매도 과열종목 designations.
- **Record dates.** The late-December "year-end ex-dividend" day that dominated Korean year-end trading is now spread across firm-specific dates. Reversal and calendar cards must use per-company record and ex-dates. Price-only data will otherwise show artificial drops (DC5).
- **Bonus issues.** They pop on announcement, and practitioners watch the ex-rights day (권리락) for retail-driven moves. The post-day-1 drift and any post-ex-date reversal are unmeasured. **BACKLOG (DC8).**

### Gaps
- No academic evidence was found on Korean CB/BW announcement or long-run returns, on rights offerings after 2015, or on returns by offering type (shareholder allotment 주주배정, third-party allotment 제3자배정, public offering 일반공모).
- No evidence was found on post-resumption returns of heavily shorted Korean stocks.
- The exact passage dates and texts of the first and second 2025 amendments were not fetched from primary legal sources; only press summaries were used.
- Rules on Korean IPO price bands and lock-ups, appraisal rights for physical splits (물적분할), and the merger-ratio formula were not verified.

---

## 7. QUANTGEN translation: decisions, timestamps, failures, data checks and claims ledger

### Takeaway
Only one corporate event deserves a gated *signal* card now: US opportunistic insider purchases. Two deserve gated *screens*: US IPO age with profitability and size conditions, and a Korean dilution screen pending lab replication. About a dozen become calendar or risk flags that can only reduce exposure. The rest should be dropped or held in backlog until post-reform data is long enough. The binding engineering constraint is availability timestamps.

### Cited Findings (timestamps and data plumbing)
- **EDGAR acceptance times.** EDGAR filing index pages show an acceptance date-time separate from the filing date. For example, Apple's FY2024 10-K shows filing date 2024-11-01 and acceptance 2024-11-01 06:01:36. — [EDGAR index example](https://www.sec.gov/Archives/edgar/data/320193/000032019324000123/0000320193-24-000123-index.htm)
- **EDGAR cut-offs.** The same-day cut-off is 5:30 p.m. ET. Forms 3, 4 and 5, Form 144 and Schedules 13D/13G accepted by 10 p.m. ET also receive the same filing date. So the filing date is *not* an availability time. — [17 CFR 232.13](https://www.ecfr.gov/current/title-17/section-232.13)
- **US filing deadlines.**
  - Form 8-K: within four business days of the event. The relevant items are 1.01 material agreements, 2.01 completed acquisitions, 2.02 results, 3.02 unregistered equity sales, 5.02 officer changes, 7.01 Reg FD and 8.01 other events. — [SEC Form 8-K](https://www.sec.gov/files/form8-k.pdf)
  - Form 4: by the end of the second business day after the trade. — [17 CFR 240.16a-3](https://www.ecfr.gov/current/title-17/section-240.16a-3)
  - Schedule 13D: within five business days (rule adopted October 2023). — [SEC fact sheet](https://www.sec.gov/files/33-11253-fact-sheet.pdf)
- **OpenDART disclosure-list API.** It returns the receipt number and the receipt date (rcept_dt, YYYYMMDD) with **no time of day**. Requests are capped at about 20,000 a day (error -020). — [OpenDART list API guide](https://opendart.fss.or.kr/guide/detail.do?apiGrpCd=DS001&apiId=2019001)
- **OpenDART major-event report APIs (DS005), 36 endpoints.** — [DS005 guide](https://opendart.fss.or.kr/guide/main.do?apiGrpCd=DS005)
  - Rights offering decision (2020023): offering method (ic_mthn) and fund purposes (facilities, operations, debt repayment, acquisition of other firms' securities). — [2020023 guide](https://opendart.fss.or.kr/guide/detail.do?apiGrpCd=DS005&apiId=2020023)
  - Bonus issue (2020024).
  - CB issuance (2020033): conversion price (cv_prc), refix floor (act_mktprcfl_cvprc_lwtrsprc), issue method (bdis_mthn, public or private), coupon and yield, conversion period. — [2020033 guide](https://opendart.fss.or.kr/guide/detail.do?apiGrpCd=DS005&apiId=2020033)
  - BW issuance (2020034).
  - Treasury-share acquisition decision (2020038): planned shares and amount, period, purpose (aq_pp), method (aq_mth), decision date (aq_dd); there is no explicit cancellation-intent field. — [2020038 guide](https://opendart.fss.or.kr/guide/detail.do?apiGrpCd=DS005&apiId=2020038)
  - Treasury trust contract (2020040).
  - Purchase of other firms' shares (2020046).
  - Merger (2020050).
  - Split (2020051): split method (dv_mth, personnel or physical), relisting flag, board, shareholder-meeting and split dates. — [2020051 guide](https://opendart.fss.or.kr/guide/detail.do?apiGrpCd=DS005&apiId=2020051)
  - Share exchange (2020053).
- **OpenDART ownership disclosures (DS004).** Large-holding reports (2019021) and officer/major-shareholder ownership reports (2019022). The FSS does not guarantee the extracted data. — [DS004 guide](https://opendart.fss.or.kr/guide/main.do?apiGrpCd=DS004)

### Event decision table

Magnitudes are gross historical estimates unless noted. "Net" applies QUANTGEN's round trips (US 100/200 bp; KRX 70/140 bp) to the part that can be captured after the event becomes available.

| # | Event (market) | Sign | Horizon | Recent-decade magnitude (label) | Versus QUANTGEN cost | Data and availability rule | Decision |
|---|---|---|---|---|---|---|---|
| 1 | IPO aftermarket, age < 36m (US) | − | 3 yrs | 2011-24 cohorts −16.4% style-adj, −24.7% mkt-adj per 3 yrs; unprofitable −23.4%, sales < $10m −34.0% (1980-2024) [gross] | Exclusion adds ~0 turnover, so it clears | IPO date from EDGAR 424B4 or Ritter lists; first close from FMP; profitability and sales from S-1; known before listing | **RISK SCREEN (BUILD-candidate)**: exclude unprofitable or sales < $50m for 36m; others ≤0.5x |
| 2 | IPO aftermarket, age < 36m (KR) | −? | 3 yrs | Not measured here | Exclusion clears costs | First trading date in KRX marcap; DART 증권신고서 | **BACKLOG → DC1** |
| 3 | IPO first-day pop (US, KR) | + | Day 1 | US 2025 mean 29.3%; KR mean 52.8% (1980-2025) | Not capturable | n/a | **DROP** (CONTEXT: issuance heat) |
| 4 | Lock-up expiry (US; KR mandatory holding expiry 의무보유 해제) | − | [−5,+1] | −0.97% [−1,+1] (2005-06); VC-backed −1.58%; expiry day −0.37% n.s. | Below 100 bp; needs short | US: S-1/424B lock-up terms; KR: lock-up commitments (의무보유확약) in 증권신고서; KIND | **CALENDAR FLAG** |
| 5 | SEO / follow-on (US) | − | 0-2 days / 5 yrs | 2-day ≈ −3% (historical); 5-yr matched −2.2 to −2.6 pp/yr (2001-11); ≈0 in recent decade (Fu-Huang) | Event card fails | 424B5/8-K acceptance time; share-count change | **DROP as card**; fold into net-issuance factor |
| 6 | Rights offering / third-party allotment (KR) | − long-run | 12-24m | 2005-10: CAR [−10,+10] +3.2%, then BHAR ≈ −31% (12m), ≈ −46% (24m) vs EW market [IS] | Exclusion clears costs | OpenDART 2020023 (ic_mthn, fund purpose); rcept_dt only, so use close of next trading day | **RISK SCREEN (BUILD-candidate) pending DC3** |
| 7 | Private CB/BW with reset (KR) | − (dilution) | 12m | Unmeasured; rules tightened 1 Dec 2024 | Exclusion clears costs | OpenDART 2020033/2020034 (cv_prc, refix floor, bdis_mthn) | **RISK SCREEN candidate pending DC3** |
| 8 | Bonus issue / split (KR) | +, then ? | −1 to +10 days | +4.3% / +4.9% CAR [−1,+1] (2008-14) | Drift after day 1 unknown | OpenDART 2020024; ex-date from share-count jump | **BACKLOG → DC8** |
| 9 | Open-market buyback (US) | + | 1-4 yrs | ≈0 after 2003 (Fu-Huang); announcement CAR ~1-2% lost at the open | Negative | 8-K/press release; quarterly 10-Q repurchase table | **DROP** |
| 10 | Treasury-share purchase or cancellation (KR) | +? | 1-12m | Unmeasured; regime break on 25 Feb 2026 | ? | OpenDART 2020038/2020040; cancellation filings | **BACKLOG** (INSUFFICIENT DATA until ~2028 on post-2024 data; ~2029 on the mandatory regime alone) |
| 11 | Value-up plan disclosure (KR) | + on day 0 only | Day 0 | +1.5% day 0, ~+1% retained, so post-day-0 ≤0 (to Feb 2026) | Negative | KIND corporate value-up plan (기업가치 제고 계획) | **DROP** (CONTEXT) |
| 12 | Dividend initiation (US) | + | 12m | Not significant value-weighted (1927-1998) | Negative | 8-K | **DROP** |
| 13 | Dividend cut or omission (US) | − | 12m | Absorbed by earnings drift (1927-1999) | n/a | 8-K | **RISK FLAG** (low priority) |
| 14 | Dividend record / ex-date (KR, after reform) | Price drop equal to dividend | Ex-date | Dividend size | n/a | DART dividend decision / record-date notices | **CALENDAR FLAG + DATA FIX (DC5)** |
| 15 | Announced cash target (US/KR) | Pinned | To close | Median spread 1.7-2.6% after 2001; arbitrage alpha −4.8 pp/yr (2002-07) | Below 2x round trip; left tail | 8-K 1.01, SC TO-T, DEFM14A; DART merger and tender-offer filings | **DROP as trade; RISK SCREEN** (exclude from technical cards) |
| 16 | Large stock-financed acquirer (US) | − | Announcement | 1998-2001: −12 cents per $ | Not capturable | 8-K | **CONTEXT** |
| 17 | Spin-off subsidiary (US) | + | 12-36m | +26% over 36m (1965-2000); after 2000 unverified | Small if real | Form 10-12B, 8-K | **BACKLOG** |
| 18 | Activist 13D (US) | + | +1 to +20 days; 12m | ≤ ~2% after day 0 (2001-06 arithmetic); total effect robust to 2018 | ~1% net | SC 13D acceptance time (≤22:00 ET counts that day); 5 business days since 2024 | **BACKLOG** |
| 19 | S&P 500 addition / deletion (US) | +/− | Announcement to effective | 2010s +0.8% / −0.6% (n.s.); day 0 +1.05% | Negative | S&P DJI notices | **DROP**; CALENDAR FLAG for effective-date close |
| 20 | KOSPI 200 addition / deletion (KR) | +/−, then reversal | To day before effective; day after effective | 1995-2008: day before effective +2.24%, day after −1.04%; 2012 long-short −2.53% | Unknown recently | KRX index notices; constituent history | **CALENDAR FLAG + BACKLOG (DC4)** |
| 21 | MSCI reviews / Korea DM upgrade (KR) | ± | n/a | No watch list (June 2026); ≥3-4 years away | n/a | MSCI | **CONTEXT / CALENDAR FLAG** |
| 22 | Opportunistic insider purchase (US Form 4) | + | 1-6m | 82 bp/month VW, opportunistic trades (1986-2007, gross); portfolio construction and holding period unverified; recent unverified | Positive only if alpha keeps accruing beyond month 1; fails if it is a 1-month effect | Form 4 acceptance time; 10b5-1 flag (2023+) | **BUILD-candidate (signal)**, conditional on DC10 |
| 23 | Insider sales (US) | 0 | n/a | No predictive power | n/a | n/a | **DROP** |
| 24 | Pre-disclosed insider trade plans (KR, 2024+) | − (sales) | 30-day+ window | Unmeasured | n/a | DART trading-plan report (거래계획보고서); date only | **RISK FLAG (DC7)** |
| 25 | Officer / major-shareholder purchases (KR) | +? | 1-6m | Unmeasured | ? | OpenDART 2019022 | **BACKLOG** |
| 26 | Analyst recommendation / initiation (US, KR) | ± | Days to 6m | >4%/yr gross, net ≈0 | ≤0 | No data in QUANTGEN | **DROP** |
| 27 | Chaebol intragroup deal (KR) | − for acquirer's minority holders | Announcement | Historical (pre-2006) | n/a | OpenDART 2020046 plus related-party flags | **RISK SCREEN (BACKLOG)** |
| 28 | Short-selling regime change; 공매도 과열종목 designation (KR) | − (day 1, confounded) | Regime; next day | KOSPI −2.93% on 31 Mar 2025 | n/a | FSC/KRX | **CONTEXT + DATA REGIME FLAG; CALENDAR FLAG** |
| 29 | Commercial Act amendments 2025-26 (KR) | ± | Regime | n/a | n/a | n/a | **CONTEXT** (break dates) |

### Inferences
- **Architecture.** Add one module, "Event Calendar and Risk Screen". Every flag maps to an exposure multiplier in [0, 1.0] or to exclusion from the long universe of existing cards, and never above 1.0. This matches the macro panel's rule that overlays only size risk. A screen is gated by comparing the screened card with the unscreened card on the same days (gate step 5 with the unscreened card as benchmark).
- **Availability rules:**
  - **US:** availability is the EDGAR acceptance time. Accepted at or before 15:30 ET on trading day d means usable at the close of d (a 30-minute buffer). Later than that means the close of d+1. Never use "Filing Date", "period of report" or the 8-K event date.
  - **Korea:** use rcept_dt plus one KRX trading day, so the decision is at the next close, unless KIND time-of-day is verified (see Gaps).
  - From practice (unverified): many Korean board decisions are filed after the close. This rule costs little if that is true and removes look-ahead if it is not.
- **Gate realism for Korea.** Value-up (2024), the CB rules (December 2024), short-selling resumption (March 2025) and mandatory cancellation (February 2026) each leave fewer than 882 sessions of post-break data. Event cards that depend on them should be pre-registered now and expected to return INSUFFICIENT DATA until about 3.5 years after each break: roughly mid-2027 for Value-up, 2028 for the CB rules and short-selling resumption, and 2029 for mandatory cancellation. They should not be fitted on mixed regimes in the meantime.
- **Conflicts with the prior design:**
  - The 1 Oct 2026 map has no event layer. Korea's weights of 3 for short-term reversal and earnings drift depend on clean returns around corporate actions. Raw KRX closes around bonus issues, splits, ex-rights dates (권리락) and ex-dividend dates can create artificial one-day crashes, which inflate measured reversal. DC0 and DC5 are prerequisites for the Korean reversal card.
  - Korea's flow weight of 3 needs short-sale regime dummies (DC6).
- **Persona's bottom line.** In the US, publication and arbitrage capital have competed away most event drift. Korea still pays for avoiding dilution, but the reforms are changing that market while we watch, so build the screen, measure it in regimes, and do not lever it.

### Gaps
- KIND's disclosure-list time column could not be verified (HTTP 403). It is needed to tighten the Korean availability rule.
- The JSON field name for EDGAR acceptance times (believed to be acceptanceDateTime in data.sec.gov submissions) and its time zone (believed to be ET) were not verified this session.
- Search capacity ran out mid-project (the web-search budget was exhausted). As a result, recent-decade evidence on:
  - Korean CB returns;
  - MSCI events in Korea;
  - post-2000 spin-offs;
  - post-2007 insider trading;
  - earnings guidance;
  - deal-break episodes

  is missing. These should be filled by the data lab or a follow-up search.

### Where and when it failed (dated episodes)
1. **1999-2000 US IPO cohort.** 856 IPOs; 3-year buy-and-hold return −53.1%, market-adjusted −31.8%, style-adjusted −58.9%. Buying into the hot window was the worst decision in the data. — [Ritter long-run](https://site.warrington.ufl.edu/ritter/files/IPOs-long-run-returns-on-IPOs.pdf)
2. **2021-2022 US IPO window slammed shut.** 311 IPOs in 2021 (first day +32.1%) fell to 38 in 2022. This cohort sits inside the 2011-2024 style-adjusted −16.4%. — [Ritter IPO statistics](https://site.warrington.ufl.edu/ritter/files/IPO-Statistics.pdf)
3. **1998-2001 acquirer wealth destruction.** Acquirers lost $240bn, or 12 cents per dollar spent, against 1.6 cents in the 1980s, concentrated in a few deals by highly valued acquirers. — [NBER w10200](https://www.nber.org/papers/w10200)
4. **2002-2007 merger-arbitrage compression.** The median spread fell from 4.1-7.9% to 1.7-2.6%, and alpha fell by about 4.81 pp a year. — [Jetley-Ji 2010](https://ideas.repec.org/a/taf/ufajxx/v66y2010i2p54-68.html)
5. **Autumn 2008 arbitrage crash.** Prime-broker distress withdrew leverage, and similar assets stopped trading at similar prices. No figure was extracted. — [Mitchell-Pulvino 2012](https://ideas.repec.org/a/eee/jfinec/v104y2012i3p469-490.html)
6. **2003-2012 US buybacks and SEOs.** Long-run abnormal returns disappeared. — [Fu-Huang 2016](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1936187)
7. **1996-2014 repeat buyback announcements.** The CAR decays from 2.51% for the first programme to 0.89% for the fifth or later. — [JRFM 2020](https://www.mdpi.com/1911-8074/13/8/176)
8. **2010s S&P 500 index effect.** Additions +0.8% and deletions −0.6%, both insignificant, against +7.3% and −16.1% in the 1990s. — [Greenwood-Sammon](https://marcosammon.com/images/greenwood_sammon.pdf)
9. **December 2020 Tesla addition.** +5.2% at announcement and +4.5% at implementation. A "fade the adds" rule would have lost. — [Greenwood-Sammon](https://www.ivey.uwo.ca/media/m2kh5j5y/the-disappearing-index-effect.pdf)
10. **2012 KOSPI 200 pre-reconstitution long-short.** −2.53%, after +15.16% (2008) and +20.86% (2009); entrants' prices began falling two days early. — [Mirae Asset 2013](https://securities.miraeasset.com/bbs/maildownload/0904fc52804d0a23)
11. **Activism failures (2001-2006).** 21.4% of campaigns failed outright, and targets fell when activists exited unsuccessfully. — [BJPT 2008](https://law.duke.edu/sites/default/files/centers/gfmc/session_3/2_brav_et_al-hedge_fund_activism-2008.pdf)
12. **Lock-ups in 2005-2006.** The expiry-day return was only −0.37% (n.s.) because short sellers front-ran: abnormal shorting was +39% over days −5 to −1. — [Gibbs-Hao](https://mediacast.blob.core.windows.net/production/Faculty/StoweConf/submissions/swfa2014_submission_184.pdf)
13. **Korean SEOs in 2005-2010.** The +3.2% announcement pop was followed by a BHAR of about −31% over 12 months against the market. Buying the issuance pop failed. — [Kim-Lee 2013](http://www.kaa-edu.or.kr/online3/2013_1/1.%20%EA%B9%80%EA%B2%BD%EC%88%9C,%EC%9D%B4%EC%A7%84%ED%9B%A4(2013s).pdf)
14. **31 Mar 2025, short selling resumes.** KOSPI −2.93%, KOSDAQ −3.05%, foreign net selling of about KRW 1.15tn on KOSPI, LG Energy Solution −6.88% (confounded). — [Etoday](https://www.etoday.co.kr/news/view/2457536)
15. **Value-up disclosures, 2024 to February 2026.** About +1.5% on day 0, settling back to about +1%. Nothing was left for a decide-at-close desk. — [Money Today/KCMI](https://www.mt.co.kr/stock/2026/05/27/2026052715542995595)
16. **June 2026 MSCI review.** Korea again missed the DM watch list, and an upgrade is at least 3-4 years away. The "upgrade anticipation" trade failed again. — [Korea Herald](https://www.koreaherald.com/article/10786876)
17. **US dividend initiations, 1927-1998.** Drift was insignificant value-weighted and not robust across subsamples. — [Boehme-Sorescu 2002](https://ideas.repec.org/a/bla/jfinan/v57y2002i2p871-900.html)
18. **October 2025 FSC enforcement.** Losses on CB sales to related parties had been concealed in the accounts. CB disclosures can be gamed, which supports a screen over a signal. — [FSC CB releases list](https://www.fsc.go.kr/no010101?srchCtgry=&curPage=&srchKey=sj&srchText=%EC%A0%84%ED%99%98%EC%82%AC%EC%B1%84&srchBeginDt=&srchEndDt=)

### Data-check requests (exact tests)
The lab holds KRX all-stock daily data for 1995-2026 (marcap: survivorship-free OHLCV plus market cap), Shiller, SPY, VIX and French data. DC0-DC9 run on the KRX data. DC10-DC11 need EDGAR plus FMP inside QUANTGEN's own pipeline.

**DC0. Corporate-action integrity of returns (prerequisite for every Korean card).**
1. Compute shares_t = marcap_t / close_t.
2. Flag days where |Δln shares| > 1%.
3. For flagged days, compare the raw close-to-close return with a share-adjusted return. Report what share of the top 1% largest absolute daily raw returns coincide with flagged days (splits, bonus issues, ex-rights days, mergers).
4. Re-run the 5-day reversal card (including its volume filter) excluding ±5 sessions around flagged days, and report the change in Sharpe.
5. Pass condition: the reversal Sharpe changes by less than 10% after masking. If it changes more, all Korean technical cards must use adjusted returns.

**DC1. Korean IPO long-run returns.**
1. Define IPOs as each code's first trading date from 2000-2023. Exclude SPACs (name contains 스팩), REITs and funds, preferred shares, KOSDAQ-to-KOSPI move-ups (the code already exists) and spin-off relistings.
2. Compute BHAR at 12, 24 and 36 months from the day-1 close and from the day-5 close against:
   - a size-matched non-IPO firm in the same market (listed for at least 5 years, nearest market cap);
   - the equal-weighted market.
3. Report mean, median, share negative and t-statistics by cohort (2000-02, 2003-07, 2008-12, 2013-17, 2018-21, 2022-23) and by market.
4. Calendar-time test: the universe excluding IPOs younger than 36 months versus the full universe, monthly, 2003-2026. Run it through the gate with the full universe as benchmark.
5. Adopt the screen if the 36-month BHAR is below −10% in 2011-2023 with t < −2 and the gate passes.

**DC2. Korean lock-up proxy.**
1. For IPOs from 2010-2026, set event days at +21, +63, +126 and +252 trading days after listing (the 1, 3, 6 and 12-month mandatory-holding expiries).
2. Compute CAR over [−5,−1], [0,+1] and [+2,+10] against size-matched firms, plus abnormal volume (volume divided by the median of days +30 to +60).
3. A flag is warranted if CAR[0,+1] ≤ −0.7% (the KRX round trip).

**DC3. Dilution events from share counts.**
1. Using DC0's share series, flag increases of 3% or more that are not splits (the price ratio does not mirror the share ratio) as issuance: rights offerings, third-party allotments, CB/BW conversions, bonus issues identified separately. Flag decreases of 0.5% or more as cancellations.
2. For 2005-2026, compute BHAR over (+1, +250) against size-matched firms, split by:
   - market (KOSPI or KOSDAQ);
   - size of increase (3-10%, 10-30%, >30%);
   - period (2005-14, 2015-24, after December 2024).
3. Note that this dates events at the *listing of new shares*, weeks after the board decision. That makes the lag conservative.
4. Gate the 12-month exclusion screen against the unscreened universe at 35 bp per side.
5. If OpenDART access exists, repeat on decision dates (2020023 and 2020033), with availability at rcept_dt plus one trading day, split by offering method (ic_mthn) and private versus public CBs (bdis_mthn).

**DC4. KOSPI 200 regular changes** (needs constituent history from KRX index data).
1. For each June/December review from 2009-2026, compute CAR from the close on the day after announcement to the close on the day before the effective date, and from the close on the day before the effective date to 5 and 20 days after it, for additions and deletions.
2. Build a predicted-inclusion portfolio (rank by trailing average market cap per KRX methodology) from 20 days before the effective date to the day before.
3. Report results by year, net of 35 bp per side (long-only additions; long-short for information only).
4. Check whether the reversal on the day after the effective date still exists after 2015.

**DC5. Ex-dividend artefact.**
1. Confirm whether marcap closes are dividend-adjusted.
2. For the top-30 dividend-yield KOSPI stocks each year, compute the market-relative return on the first trading day after the year-end record date. Compare 2005-2022 (uniform year-end record date) with 2023-2026 (dispersed record dates).
3. Re-run the reversal card with ex-dates masked.
4. If the masked Sharpe falls by more than 10%, require dividend-adjusted returns.

**DC6. Short-selling regimes** (difference-in-differences).
1. Compare KOSPI 200 plus KOSDAQ 150 constituents (shortable in the partial-resumption period from May 2021) with non-constituents, using 20- and 60-day returns and realised volatility.
2. Run it around three dates: May 2021 (exact date to be verified), 6 Nov 2023 and 31 Mar 2025.
3. Control for size and beta.
4. Output: whether any flow or short-interest card needs regime dummies.

**DC7. Korean insider pre-disclosure** (needs the list of DART trading-plan reports from 24 Jul 2024).
1. Compute CAR from rcept_dt plus one day to the end of the disclosed window against size-matched firms, split by seller type and size (% of shares).
2. Adopt a risk flag if the mean is ≤ −0.7%.

**DC8. Bonus issues and ex-rights days.**
1. Detect ex-rights days for bonus issues from 2008-2026: a share-count jump of 20% or more with a matching price drop.
2. Compute CAR from the ex-day to +5, +20 and +60 days against size-matched firms, plus the announcement-to-ex-day CAR if DART dates are available.
3. Adopt a risk flag if the ex-day to +20 CAR is ≤ −0.7%. Consider a backlog signal if the announcement+1 to +10 CAR is ≥ +1.4% (2x cost).

**DC9. Treasury-share cancellations (proxy).**
1. Take share-count decreases of 0.5% or more (DC3) for 2010-2026.
2. Compute CAR over (+1, +20) and (+1, +120), split into before February 2024 (pre-Value-up), February 2024 to 24 Feb 2026, and after 25 Feb 2026 (mandatory regime).
3. Expect decay. Report the number of events per regime against the 882-session requirement.

**DC10. US opportunistic insider purchases** (QUANTGEN pipeline: EDGAR Form 4 plus FMP closes).
1. Events: open-market purchases (transaction code P) by officers or directors. Exclude 10b5-1-flagged trades (2023+) and routine insiders: those who traded in the same calendar month in each of the prior three years, per Cohen-Malloy-Pomorski.
2. Entry at the close after acceptance time (15:30 ET buffer). Hold 21, 63 and 126 days; equal- and value-weighted.
3. Benchmarks: SPY and size-matched portfolios. Costs 50 and 100 bp per side. Period 2004-2026, through all nine gate steps.
4. Pre-registered configuration: 126 days, value-weighted.

**DC11. US IPO-age screen** (QUANTGEN pipeline).
1. Universe: US stocks with FMP closes. Take IPO dates from 424B4 filings.
2. Apply the screen from row 1 of the decision table to an existing card (for example, the quality sleeve once built).
3. Compare screened with unscreened on the same days over 2005-2026.

### Claims ledger

| ID | Claim (one sentence) | Evidence (numbers, market, period, IS/OOS, gross/net) | Source(s) with URL | Tier | Robustness | Failure cases | QUANTGEN implication |
|---|---|---|---|---|---|---|---|
| E6-C01 | US IPO 3-year underperformance has not decayed and is worst in recent cohorts. | 9,253 IPOs 1980-2024: mkt-adj −20.5%, style-adj −8.9%; 2011-24: −24.7% / −16.4%; US; 3-yr BHR from first close; gross; post-1995 cohorts OOS | [Ritter long-run](https://site.warrington.ufl.edu/ritter/files/IPOs-long-run-returns-on-IPOs.pdf); [Loughran-Ritter 1995](https://econpapers.repec.org/RePEc:bla:jfinan:v:50:y:1995:i:1:p:23-51) | T1 | Replicated across decades; OOS after publication; totals reconcile; recent cohorts truncated | 2001-10 market-adj +2.2%; 1980-89 style-adj +2.2% | BUILD-candidate **risk screen** (exclusion, no shorting) |
| E6-C02 | IPO underperformance is concentrated in small and unprofitable issuers. | 1980-2024 style-adj: sales < $10m −34.0%; unprofitable −23.4% vs profitable +1.8%; non-VC −12.8% vs VC −3.2%; US; gross | [Ritter long-run](https://site.warrington.ufl.edu/ritter/files/IPOs-long-run-returns-on-IPOs.pdf) | T1 | Single-author dataset; cross-sections internally consistent | $100-500m sales cohort +5.4% | Make the US IPO screen conditional on profitability and sales |
| E6-C03 | US first-day IPO returns stay large and swing with market heat, but a close-to-close desk cannot capture them. | Mean first day 2020 41.6% (165 IPOs), 2021 32.1% (311), 2022 48.9% (38), 2025 29.3% (90); US | [Ritter IPO Statistics](https://site.warrington.ufl.edu/ritter/files/IPO-Statistics.pdf) | T1 | Descriptive | 2023 only 11.9% | DROP as signal; CONTEXT (issuance heat) |
| E6-C04 | Korean IPOs show far larger initial returns than US IPOs; their long-run behaviour is unmeasured here. | KR mean 52.8% (2,588 IPOs, 1980-2025) vs US 17.7% | [Ritter International](https://site.warrington.ufl.edu/ritter/files/IPOs-International.pdf) | T1 | Compiled from many studies | Unknown | BACKLOG; DC1 to decide on a Korean IPO-age screen |
| E6-C05 | Lock-up expiries carry small negative returns that short sellers anticipate. | −1.5% over 3 days (1,948 lock-ups, pre-2000); 2005-06: −0.97% [−1,+1], expiry day −0.37% n.s., shorting +39% in [−5,−1], VC-backed −1.58%; US; gross | [Field-Hanka](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=236029); [Gibbs-Hao](https://mediacast.blob.core.windows.net/production/Faculty/StoweConf/submissions/swfa2014_submission_184.pdf) | T1 | Replicated OOS (2005-06) but smaller; front-run | Expiry day n.s.; PE-backed none | CALENDAR FLAG (no new longs in [−5,+1]) |
| E6-C06 | US SEO long-run underperformance has shrunk and is mostly factor exposure. | 5-yr matched: −6.4 pp/yr (1980s) to −2.2 pp/yr (2001-11, size), −2.6 (style); factor alphas n.s. (1964-95); drift gone in recent decade; announcement ≈ −3% (2-day, historical) | [Ritter SEO tables](https://site.warrington.ufl.edu/ritter/files/2015/04/Seasoned-Equity-Offerings-from-1970-2011-Tables-2013-06.pdf); [Eckbo-Masulis-Norli](https://ronmasulis.wordpress.com/wp-content/uploads/2013/08/seasoned-public-offerings-resolutions-of-the-new-issues-puzzle.pdf); [Fu-Huang](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1936187) | T1 | Post-publication OOS; method-dependent | 1999-2000 −8.1 pp/yr | DROP as card; net-issuance factor input |
| E6-C07 | The US open-market buyback drift has disappeared and announcement reactions have shrunk. | ILV 1980-90: +12.1% over 4 yrs (value +45.3%); recent decade (≈2003-12) ≈0; 2-day CAR >3% (1980s) to ~1% (2004), 2.51% to 0.89% by 5th+ programme (1996-2014); US; gross | [ILV](https://econpapers.repec.org/RePEc:nbr:nberwo:4965); [Fu-Huang](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1936187); [JRFM 2020](https://www.mdpi.com/1911-8074/13/8/176) | T1 | OOS decay documented; conflicts with Peyer-Vermaelen 2009 | Post-2003 | DROP (US) |
| E6-C08 | Outside the US, buyback excess returns persist where undervaluation is likely and markets are less efficient. | 9,000+ announcements, 31 non-US countries; positive short- and long-run excess returns, not weaker recently; gross | [Manconi-Peyer-Vermaelen 2019](https://ideas.repec.org/a/cup/jfinqa/v54y2019i05p1899-1935_00.html) | T1 | Multi-country; Korean share not extracted | Not Korea-specific | BACKLOG for Korea, subject to the 2026 regime break (C17) |
| E6-C09 | Drift after US dividend initiations and omissions is not robust. | MTW: +7.5% / −11.0% over 12m; announcement +3.4% / −7.0%; initiation drift n.s. value-weighted (1927-1998); omission drift vanishes with earnings controls (1927-1999); gross | [MTW](https://ideas.repec.org/p/nbr/nberwo/4778.html); [Boehme-Sorescu](https://ideas.repec.org/a/bla/jfinan/v57y2002i2p871-900.html); [Liu et al.](https://ideas.repec.org/a/bla/jfinan/v63y2008i2p987-1020.html) | T1 | Fails OOS and robustness checks | Equal-weighted only | DROP; omission as low-priority RISK FLAG |
| E6-C10 | Acquirer announcement returns are negative in aggregate, driven by large, highly valued bidders. | 12,023 deals 1980-2001: acquirers −$218bn (large −$226bn, small +$8bn); 1998-2001 −12 cents per $ vs 1.6 cents in 1980s; US | [NBER w9523](https://www.nber.org/papers/w9523); [NBER w10200](https://www.nber.org/papers/w10200) | T1 | Widely cited; announcement-only | Subsidiary acquisitions positive | CONTEXT (not capturable at the close) |
| E6-C11 | Merger arbitrage is a short-put trade whose spread compressed sharply after 2001. | 4%/yr excess after costs (1963-98, 4,750 deals); median first-day spread 4.1-7.9% to 1.7-2.6%; alpha −4.81 pp/yr (2002-07); 2008 crash | [Mitchell-Pulvino 2001](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=268144); [Jetley-Ji](https://ideas.repec.org/a/taf/ufajxx/v66y2010i2p54-68.html); [Mitchell-Pulvino 2012](https://ideas.repec.org/a/eee/jfinec/v104y2012i3p469-490.html) | T1 | Post-publication decay documented | 2008; deal breaks | DROP as trade; RISK SCREEN to exclude pinned targets from technical cards |
| E6-C12 | Spin-off subsidiaries historically outperformed, partly because of later takeovers; parents' excess returns faded. | 1965-88: spinoffs +33.6% over 36m (taken over +99.3%, not taken over +22.5% n.s.); 1965-2000: +26.3% over 36m, parents ≈0; US; gross | [CMW 1993](https://longrunplan.com/wp-content/uploads/2018/09/restructuring-through-spinoffs.pdf); [McConnell-Ovtchinnikov](https://www.researchgate.net/publication/228289308_Predictability_of_Long-Term_Spin-Off_Returns) | T1 | Partly OOS; post-2000 unverified | Parents after 1989 | BACKLOG |
| E6-C13 | Activist 13D filings bring ~7% abnormal returns with no one-year reversal; at most ~2% remains after the filing day. | 1,059 events 2001-06: [−20,+20] 7.2%, run-up 3.2%, filing day 2.0%; robust in 4,094 events 1994-2018; sale-of-company objective 8.54%; US; gross; post-day-0 figure is inferred | [BJPT 2008](https://law.duke.edu/sites/default/files/centers/gfmc/session_3/2_brav_et_al-hedge_fund_activism-2008.pdf); [Brav-Jiang-Li 2022](https://www.ecgi.global/sites/default/files/working_papers/documents/bravjianglifinal_0.pdf) | T1 | OOS through 2018; deadline cut to 5 business days in 2024 | 21.4% failures; governance objectives n.s. | BACKLOG (test on 13D acceptance times) |
| E6-C14 | The S&P 500 inclusion effect has disappeared. | Additions 7.3% (1990s) to 0.8% (2010s, n.s.); deletions −16.1% to −0.6%; day 0 5.15% to 1.05%; price impact down ~20x; migrations >60% of adds; US; gross | [Greenwood-Sammon](https://marcosammon.com/images/greenwood_sammon.pdf); [JF listing](https://onlinelibrary.wiley.com/doi/10.1111/jofi.13410) | T1 | Post-publication OOS; JF 2025 | Tesla 2020 (+5.2% / +4.5%) | DROP; CALENDAR FLAG for effective-date close |
| E6-C15 | KOSPI 200 changes showed price pressure into the effective date and a next-day reversal; the pre-reconstitution trade decayed by 2012. | 1995-2008: day before effective +2.24% (t 8.75), day after −1.04%; 20-day pre long-short 7.62% average (2008-12) but 2012 −2.53%; KR; gross | [Yun-Kim](https://kasba.or.kr/uploads/papers/NODE06081483.pdf); [Mirae 2013](https://securities.miraeasset.com/bbs/maildownload/0904fc52804d0a23) | T1 / T2 | Old; no post-2013 evidence | 2012 | CALENDAR FLAG + BACKLOG (DC4) |
| E6-C16 | No MSCI developed-market upgrade event for Korea is near. | June 2026: not on watch list (won convertibility, omnibus/in-kind, short-sale compliance); ≥3-4 years to upgrade | [Korea Times](https://www.koreatimes.co.kr/economy/20260624/msci-keeps-korea-off-developed-market-watchlist-but-global-analysts-stay-bullish); [Korea Herald](https://www.koreaherald.com/article/10786876) | T2 | Dated fact | Repeated misses | CONTEXT; MSCI review dates as calendar flags |
| E6-C17 | Korea's treasury-share regime changed structurally in 2026, and cancellation volumes surged. | 3rd amendment passed 25 Feb 2026 (cancel within 1 yr; existing within 18 months); all holders disclose (effective 30 Jun 2026); cancellations KRW 21.4tn (2025), KRW 43.1tn (Jan-May 2026) | [Seoul Shinmun](https://www.seoul.co.kr/news/politics/2026/02/26/20260226001004); [FSC 23 Jun 2026](https://www.fsc.go.kr/no010101/87169) | T1 / T2 | Official | n/a | CONTEXT + regime break; buyback card BACKLOG (INSUFFICIENT DATA expected) |
| E6-C18 | The Value-up disclosure effect sits on day 0 with no positive drift afterwards; group outperformance is selection. | ~+1.5% day 0, ~+1% retained (to Feb 2026); disclosers +45.3 pp (May 2024-Feb 2026), +68.8 pp (2024-Q1 2026, 718 firms); payout 30.5% vs 14.1%; KR; gross | [MT/KCMI](https://www.mt.co.kr/stock/2026/05/27/2026052715542995595); [KCMI report](https://www.kcmi.re.kr/publications/pub_detail_view?syear=2026&zcd=002001016&zno=1917&cno=6774) | T2 | Short sample; voluntary-disclosure selection | Day-0 gain partly given back | DROP as signal; CONTEXT |
| E6-C19 | Korean SEOs pop on announcement and then dilute severely. | 734 SEOs 2005-10 (75% KOSDAQ): CAR [−10,+10] +3.23%; BHAR ≈ −31% (12m), ≈ −46% (24m) vs EW market; IS; gross | [Kim-Lee 2013](http://www.kaa-edu.or.kr/online3/2013_1/1.%20%EA%B9%80%EA%B2%BD%EC%88%9C,%EC%9D%B4%EC%A7%84%ED%9B%A4(2013s).pdf) | T1 | Single study; weak benchmark; 2008 crisis in window | Post-2015 unknown | BUILD-candidate **risk screen** pending DC3 |
| E6-C20 | Korean chaebol intragroup deals have transferred value from minority shareholders. | Chaebol acquirers decline (tunneling); premium-priced intragroup placements: issuers +8.8%, affiliated acquirers −5.8% relative announcement returns; KR | [Bae-Kang-Kim 2002](https://ideas.repec.org/a/bla/jfinan/v57y2002i6p2695-2740.html); [Baek-Kang-Lee 2006](https://ideas.repec.org/a/bla/jfinan/v61y2006i5p2415-2449.html) | T1 | Top-journal; old samples | 2025 governance reform may weaken | RISK SCREEN (BACKLOG) |
| E6-C21 | Korea tightened CB rules from December 2024 and has sanctioned CB-related fraud. | From 1 Dec 2024: call-option holder disclosure, resets below 70% only by special resolution per issue, repurchase disclosure; CB disclosure ≥1 week before payment; Oct 2025 enforcement | [FSC 83400](https://www.fsc.go.kr/no010101/83400); [FSC 83741](https://www.fsc.go.kr/no010101/83741); [FSC CB list](https://www.fsc.go.kr/no010101?srchCtgry=&curPage=&srchKey=sj&srchText=%EC%A0%84%ED%99%98%EC%82%AC%EC%B1%84&srchBeginDt=&srchEndDt=) | T1 | Official | n/a | RISK SCREEN candidate (private CBs with resets); regime break Dec 2024 |
| E6-C22 | Korea's short-sale ban ended on 31 Mar 2025 with new controls; day 1 was sharply down but confounded. | Ban 6 Nov 2023 to 30 Mar 2025; NSDS; 90-day repayment limit; day 1 KOSPI −2.93%, KOSDAQ −3.05%, foreign net sell ~KRW 1.15tn | [FSC 84216](https://fsc.go.kr/no010101/84216?curPage=&srchBeginDt=&srchCtgry=&srchEndDt=&srchKey=sj&srchText=); [Etoday](https://www.etoday.co.kr/news/view/2457536) | T1 / T2 | One-off | Confounded day | CONTEXT + DATA REGIME FLAG; CALENDAR FLAG for 과열종목 |
| E6-C23 | Korea's record-date reform spreads ex-dividend dates away from year-end. | FSC Jan 2023 (decide dividend, then set record date); Dec 2024 CMA amendment for quarterly dividends | [FSC 79358](https://www.fsc.go.kr/no010101/79358); [FSC 83741](https://www.fsc.go.kr/no010101/83741) | T1 | Official | n/a | CALENDAR FLAG + DATA FIX (DC5) |
| E6-C24 | Korea's insider pre-disclosure creates a 30-day supply calendar. | From 24 Jul 2024: trades ≥1% or ≥KRW 5bn (6-month aggregate) pre-filed 30 days ahead; fines up to KRW 2bn; some holders shifted to smaller on-market sales | [FSC 82635](https://www.fsc.go.kr/no010101/82635?srchCtgry=&curPage=&srchKey=&srchText=&srchBeginDt=&srchEndDt=); [Economist Korea](https://economist.co.kr/article/view/ecn202409130053) | T1 / T2 | New regime; unmeasured | Avoidance by smaller trades | RISK FLAG (DC7) |
| E6-C25 | US opportunistic insider trades predict returns, with the information in purchases; sales and routine trades do not. | Opportunistic-trade portfolio 82 bp/month VW (1986-2007; construction and holding period not verified); purchases >6%/yr; little price reaction at filing; strongest in small firms (1975-95); US; gross | [NBER digest](https://www.nber.org/digest/apr11/decoding-inside-information); [JMZ 2003](https://ideas.repec.org/a/tpr/restat/v85y2003i2p453-471.html); [Lakonishok-Lee 2001](https://ideas.repec.org/a/oup/rfinst/v14y2001i1p79-111.html) | T1 | Several samples; post-2007 unverified | Routine trades ≈0 | **BUILD-candidate signal** (DC10; hold ~126 days) |
| E6-C26 | Analyst-recommendation strategies do not pay net of costs. | >4%/yr gross, net not reliably >0; buy drift +2.4% short-lived, sell drift −9.1% over 6m; revisions piggyback on news; first coverage +4.86% at announcement; US | [BLMT 2001](https://ideas.repec.org/a/bla/jfinan/v56y2001i2p531-563.html); [Womack 1996](https://ideas.repec.org/a/bla/jfinan/v51y1996i1p137-67.html); [Altinkilic-Hansen 2009](https://ideas.repec.org/a/eee/jaecon/v48y2009i1p17-36.html); [Demiroglu-Ryngaert 2010](https://ideas.repec.org/a/bla/finmgt/v39y2010i2p555-584.html) | T1 | Consistent | n/a | DROP (no data; net ≈0) |
| E6-C27 | Point-in-time availability differs sharply between EDGAR and OpenDART. | EDGAR acceptance time (e.g., 06:01:36); 5:30 p.m. / 10 p.m. cut-offs; 8-K 4 business days; Form 4 2 business days; 13D 5 business days; OpenDART rcept_dt date only, ~20,000 calls/day | [17 CFR 232.13](https://www.ecfr.gov/current/title-17/section-232.13); [17 CFR 240.16a-3](https://www.ecfr.gov/current/title-17/section-240.16a-3); [Form 8-K](https://www.sec.gov/files/form8-k.pdf); [EDGAR index example](https://www.sec.gov/Archives/edgar/data/320193/000032019324000123/0000320193-24-000123-index.htm); [OpenDART list API](https://opendart.fss.or.kr/guide/detail.do?apiGrpCd=DS001&apiId=2019001) | T1 | Official | KIND time column unverified | BUILD (data rule): US uses acceptance time with 15:30 ET buffer; Korea uses rcept_dt plus one trading day |
| E6-C28 | Korean bonus issues and splits pop on announcement, with short positive continuation. | 2008-14: CAR [−1,+1] +4.33% (191 bonus issues), +4.92% (113 splits); positive through day +10; retail ownership rises; KR; gross | [Ju-Ryu 2014](http://www.korfin.org/korfin_file/forum/15fall1-4.pdf) | T1 (WP) | Single working paper | Ex-date behaviour unknown | BACKLOG (DC8) |

### Source list
**IPOs and SEOs**
- Ritter, IPO Statistics (2026 update): https://site.warrington.ufl.edu/ritter/files/IPO-Statistics.pdf
- Ritter, Long-run returns on IPOs (1980-2024): https://site.warrington.ufl.edu/ritter/files/IPOs-long-run-returns-on-IPOs.pdf
- Ritter, International IPO underpricing (30 Mar 2026): https://site.warrington.ufl.edu/ritter/files/IPOs-International.pdf
- Ritter, SEO long-run tables 1970-2011: https://site.warrington.ufl.edu/ritter/files/2015/04/Seasoned-Equity-Offerings-from-1970-2011-Tables-2013-06.pdf
- Ritter, IPO data page (index of files): https://site.warrington.ufl.edu/ritter/ipo-data/
- Ritter (1991), JF, RePEc: https://ideas.repec.org/a/bla/jfinan/v46y1991i1p3-27.html
- Loughran-Ritter (1995), JF, EconPapers: https://econpapers.repec.org/RePEc:bla:jfinan:v:50:y:1995:i:1:p:23-51
- Eckbo-Masulis-Norli (2000), JFE (PDF): https://ronmasulis.wordpress.com/wp-content/uploads/2013/08/seasoned-public-offerings-resolutions-of-the-new-issues-puzzle.pdf
- Field-Hanka (2001), JF, SSRN: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=236029
- Gibbs-Hao, lock-up short selling (SWFA 2014 WP): https://mediacast.blob.core.windows.net/production/Faculty/StoweConf/submissions/swfa2014_submission_184.pdf

**Buybacks and dividends**
- Ikenberry-Lakonishok-Vermaelen (1995), NBER w4965: https://econpapers.repec.org/RePEc:nbr:nberwo:4965
- Fu-Huang (2016), Management Science, SSRN: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1936187
- Peyer-Vermaelen (2009), RFS: https://ideas.repec.org/a/oup/rfinst/v22y2009i4p1693-1745.html
- Manconi-Peyer-Vermaelen (2019), JFQA: https://ideas.repec.org/a/cup/jfinqa/v54y2019i05p1899-1935_00.html
- "What Drives the Declining Wealth Effect of Subsequent Share Repurchase Announcements?", JRFM 13(8):176 (2020): https://www.mdpi.com/1911-8074/13/8/176
- Michaely-Thaler-Womack (1995), NBER w4778: https://ideas.repec.org/p/nbr/nberwo/4778.html
- Boehme-Sorescu (2002), JF: https://ideas.repec.org/a/bla/jfinan/v57y2002i2p871-900.html
- Liu-Szewczyk-Zantout (2008), JF: https://ideas.repec.org/a/bla/jfinan/v63y2008i2p987-1020.html

**M&A, spin-offs and activism**
- Andrade-Mitchell-Stafford (2001), JEP abstract: https://www.aeaweb.org/articles?id=10.1257/jep.15.2.103
- Moeller-Schlingemann-Stulz, NBER w9523: https://www.nber.org/papers/w9523
- Moeller-Schlingemann-Stulz, NBER w10200: https://www.nber.org/papers/w10200
- Mitchell-Pulvino (2001), JF, SSRN: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=268144
- Mitchell-Pulvino (2012), JFE: https://ideas.repec.org/a/eee/jfinec/v104y2012i3p469-490.html
- Jetley-Ji (2010), FAJ: https://ideas.repec.org/a/taf/ufajxx/v66y2010i2p54-68.html
- Cusatis-Miles-Woolridge (1993), JFE (PDF): https://longrunplan.com/wp-content/uploads/2018/09/restructuring-through-spinoffs.pdf
- Cusatis-Miles-Woolridge (1993), RePEc record: https://ideas.repec.org/a/eee/jfinec/v33y1993i3p293-311.html
- McConnell-Ovtchinnikov, Predictability of Long-Term Spin-off Returns: https://www.researchgate.net/publication/228289308_Predictability_of_Long-Term_Spin-Off_Returns
- Brav-Jiang-Partnoy-Thomas (2008), JF (Duke PDF): https://law.duke.edu/sites/default/files/centers/gfmc/session_3/2_brav_et_al-hedge_fund_activism-2008.pdf
- Brav-Jiang-Partnoy-Thomas, Returns to Hedge Fund Activism, SSRN: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1111778
- Brav-Jiang-Li (2022), ECGI WP: https://www.ecgi.global/sites/default/files/working_papers/documents/bravjianglifinal_0.pdf
- SEC beneficial-ownership fact sheet (33-11253): https://www.sec.gov/files/33-11253-fact-sheet.pdf
- Bae-Kang-Kim (2002), JF: https://ideas.repec.org/a/bla/jfinan/v57y2002i6p2695-2740.html
- Baek-Kang-Lee (2006), JF: https://ideas.repec.org/a/bla/jfinan/v61y2006i5p2415-2449.html

**Index events**
- Greenwood-Sammon (PDF, marcosammon.com): https://marcosammon.com/images/greenwood_sammon.pdf
- Greenwood-Sammon (PDF, Ivey-hosted): https://www.ivey.uwo.ca/media/m2kh5j5y/the-disappearing-index-effect.pdf
- Greenwood-Sammon, JF listing: https://onlinelibrary.wiley.com/doi/10.1111/jofi.13410
- Yun-Kim, KOSPI 200 index changes (KASBA PDF): https://kasba.or.kr/uploads/papers/NODE06081483.pdf
- Mirae Asset, KOSPI 200 reconstitution note (2013): https://securities.miraeasset.com/bbs/maildownload/0904fc52804d0a23
- Korea Times, MSCI decision (24 Jun 2026): https://www.koreatimes.co.kr/economy/20260624/msci-keeps-korea-off-developed-market-watchlist-but-global-analysts-stay-bullish
- Korea Herald, MSCI decision: https://www.koreaherald.com/article/10786876

**Insider and analyst events**
- NBER Digest, Decoding Inside Information: https://www.nber.org/digest/apr11/decoding-inside-information
- Jeng-Metrick-Zeckhauser (2003), REStat: https://ideas.repec.org/a/tpr/restat/v85y2003i2p453-471.html
- Lakonishok-Lee (2001), RFS: https://ideas.repec.org/a/oup/rfinst/v14y2001i1p79-111.html
- SEC Rule 10b5-1 amendments: https://www.sec.gov/rules-regulations/2022/12/insider-trading-arrangements-related-disclosures
- Barber-Lehavy-McNichols-Trueman (2001), JF: https://ideas.repec.org/a/bla/jfinan/v56y2001i2p531-563.html
- Womack (1996), JF: https://ideas.repec.org/a/bla/jfinan/v51y1996i1p137-67.html
- Altinkilic-Hansen (2009), JAE: https://ideas.repec.org/a/eee/jaecon/v48y2009i1p17-36.html
- Demiroglu-Ryngaert (2010), FM: https://ideas.repec.org/a/bla/finmgt/v39y2010i2p555-584.html

**Filing rules and data plumbing**
- 17 CFR 240.16a-3 (Form 4): https://www.ecfr.gov/current/title-17/section-240.16a-3
- 17 CFR 232.13 (EDGAR filing dates): https://www.ecfr.gov/current/title-17/section-232.13
- SEC Form 8-K: https://www.sec.gov/files/form8-k.pdf
- EDGAR filing index example (acceptance time): https://www.sec.gov/Archives/edgar/data/320193/000032019324000123/0000320193-24-000123-index.htm
- OpenDART disclosure-list API: https://opendart.fss.or.kr/guide/detail.do?apiGrpCd=DS001&apiId=2019001
- OpenDART DS005 (major-event reports): https://opendart.fss.or.kr/guide/main.do?apiGrpCd=DS005
- OpenDART rights offering (2020023): https://opendart.fss.or.kr/guide/detail.do?apiGrpCd=DS005&apiId=2020023
- OpenDART CB issuance (2020033): https://opendart.fss.or.kr/guide/detail.do?apiGrpCd=DS005&apiId=2020033
- OpenDART treasury acquisition (2020038): https://opendart.fss.or.kr/guide/detail.do?apiGrpCd=DS005&apiId=2020038
- OpenDART company split (2020051): https://opendart.fss.or.kr/guide/detail.do?apiGrpCd=DS005&apiId=2020051
- OpenDART DS004 (ownership disclosures): https://opendart.fss.or.kr/guide/main.do?apiGrpCd=DS004

**Korean regulation and policy**
- FSC insider pre-disclosure (24 Jul 2024): https://www.fsc.go.kr/no010101/82635?srchCtgry=&curPage=&srchKey=&srchText=&srchBeginDt=&srchEndDt=
- FSC treasury-share disclosure (23 Jun 2026): https://www.fsc.go.kr/no010101/87169
- FSC treasury-share reform notice (3 Jun 2024): https://www.fsc.go.kr/no010101/82390
- FSC treasury-share releases list: https://www.fsc.go.kr/no010101?srchCtgry=&curPage=&srchKey=sj&srchText=%EC%9E%90%EA%B8%B0%EC%A3%BC%EC%8B%9D&srchBeginDt=&srchEndDt=
- FSC CB reform (effective 1 Dec 2024): https://www.fsc.go.kr/no010101/83400
- FSC CB releases list: https://www.fsc.go.kr/no010101?srchCtgry=&curPage=&srchKey=sj&srchText=%EC%A0%84%ED%99%98%EC%82%AC%EC%B1%84&srchBeginDt=&srchEndDt=
- FSC Capital Markets Act amendment (27 Dec 2024): https://www.fsc.go.kr/no010101/83741
- FSC dividend procedure reform (31 Jan 2023): https://www.fsc.go.kr/no010101/79358
- FSC short-selling resumption (21 Mar 2025): https://fsc.go.kr/no010101/84216?curPage=&srchBeginDt=&srchCtgry=&srchEndDt=&srchKey=sj&srchText=
- Seoul Shinmun, third Commercial Act amendment (26 Feb 2026): https://www.seoul.co.kr/news/politics/2026/02/26/20260226001004

**Korean market evidence and press**
- Etoday, short-selling resumption day 1 (31 Mar 2025): https://www.etoday.co.kr/news/view/2457536
- Economist (Korea), insider pre-disclosure after two months: https://economist.co.kr/article/view/ecn202409130053
- KCMI, Value-up disclosure and listed-firm performance (1 Jun 2026): https://www.kcmi.re.kr/publications/pub_detail_view?syear=2026&zcd=002001016&zno=1917&cno=6774
- Money Today, KCMI Value-up event study (27 May 2026): https://www.mt.co.kr/stock/2026/05/27/2026052715542995595
- KDI EIEC / Daeshin, Value-up index review (29 Jul 2025): https://eiec.kdi.re.kr/policy/domesticView.do?ac=0000199677
- Kim-Lee (2013), Korean SEOs and accrual quality (PDF): http://www.kaa-edu.or.kr/online3/2013_1/1.%20%EA%B9%80%EA%B2%BD%EC%88%9C,%EC%9D%B4%EC%A7%84%ED%9B%A4(2013s).pdf
- Ju-Ryu (2014), Korean splits and bonus issues (PDF): http://www.korfin.org/korfin_file/forum/15fall1-4.pdf
