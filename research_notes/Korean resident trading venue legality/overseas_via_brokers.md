# Overseas securities and derivatives for a Korean resident: Korean brokers vs. foreign brokers

Scope: South Korean national resident in Korea, ~KRW 42,000 (~USD 30) starting capital, as of 2026-10-22. These notes describe what statutes, regulators and platform pages say. They are not legal advice. "UNCERTAIN" marks anything not confirmed from a primary source or that may have changed after mid-2026.

Quick matrix (details and citations in the sections below):

| Venue / instrument | Status for this person | Reachable with KRW 42k | Min ticket | Max leverage | Rule relied on |
|---|---|---|---|---|---|
| US stocks/ETFs via Korean broker (incl. fractional) | legal | yes | fractional from KRW 1,000 at Toss (blog source, UNCERTAIN for other brokers) | 1x (cash) | 자본시장법 시행령 제184조① (trade via 투자중개업자); BOK: 일반투자가 외화증권취득은 투자중개업자에 위탁 |
| Overseas leveraged/inverse ETPs (TQQQ, SOXL, single-stock 2x) via Korean broker | legal_with_conditions | yes (after ~KRW 4,000 KOFIA course fee, KB figure) | one share or fractional if broker allows (UNCERTAIN) | 3x daily (product-level) | FSS/KOFIA investor-protection scheme, effective 2025-12-15: 1h 사전교육; no 모의거래; no 기본예탁금 reported. Single-stock leveraged/inverse: +1h course (2026) |
| US-listed equity options via Korean broker (Samsung, KB, Samsung Futures, KIS; Toss status UNCERTAIN) | legal_with_conditions | marginal/unclear (one long contract with a few-cent premium plus ~USD 5.9 commission could fit; writing not allowed at Samsung) | 1 contract = 100 shares | long premium only (embedded leverage); writing restricted | Since 2025-12-15: 1h 사전교육 + 3h 모의거래; no 기본예탁금 |
| Overseas futures/options (CME etc.) via Korean broker | legal_with_conditions | no (per-contract margin far above KRW 42k; inference) | 1 contract | exchange margin leverage | Same 1h + 3h scheme; no 기본예탁금 for overseas products |
| Interactive Brokers (direct) | grey | yes in principle (no IBKR minimum confirmed here) | n/a | margin account possible | 시행령 제184조① requires general investors to trade via 투자중개업자; 2018 FSC reply: foreign broker not soliciting is outside the Act; BOK reporting for acquiring securities from non-residents |
| Webull | blocked_by_platform (third-party source) | n/a | n/a | n/a | platform eligibility |
| Moomoo | blocked_by_platform (Korea not on Moomoo's official list) | n/a | n/a | n/a | platform eligibility |
| eToro | unknown (conflicting sources) | n/a | n/a | n/a | platform eligibility + 시행령 제184조① |

## 1. US stocks and ETFs via Korean brokers: fractional minimums, commissions, FX spread, settlement

### Takeaway
Buying US stocks and ETFs through a domestic broker is the plainly lawful route, and the law expects it: the Enforcement Decree makes general investors trade foreign securities through a 투자중개업자. The KRW 42,000 budget is enough for fractional purchases. Fee and FX figures found are mostly from blogs and change with promotions, so treat them as indicative.

### Cited Findings
- 자본시장법 시행령 제184조①: general investors (including FSC-designated professional investors) trading foreign securities and exchange-traded derivatives on overseas markets, including foreign MTFs, must do so through a 투자중개업자. The broker must open a client trading account at the foreign broker, separate from its proprietary account — [lawnb.com, 시행령 제184조 (2024-08-13 version)](https://www.lawnb.com/Info/ContentView?sid=L0002ED8D96EACC3_184_20240813); [law.go.kr 시행령 link](https://www.law.go.kr/LSW/lumLsLinkPop.do?lspttninfSeq=62426&chrClsCd=010202). The search tool reported a law.go.kr version updated by another statute on 2026-09-29; whether Article 184 changed then is UNCERTAIN.
- Bank of Korea: residents may invest in foreign securities without limit, and non-institutional "일반투자가" must entrust foreign-securities purchases to a 투자중개업자 — [BOK 자본거래 안내](https://www.bok.or.kr/portal/main/contents.do?menuNo=200405)
- Before a 2024 amendment, "개인투자자 등은 예외 없이 국내 증권사를 통해서만" could trade overseas-listed foreign securities and foreign derivatives. The FSC announced the amendment on 2024-02-27, effective on promulgation in early March 2024. — [일간NTN, 2024-02-27](https://www.intn.co.kr/news/articleView.html?idxno=2034122)
- Toss Securities: fractional US stocks/ETFs from KRW 1,000; commission 0.1% each way; FX preferential rate around 95% in Korean business hours, reported as 50% outside them. Sources conflict on the FX rate (one says 100%), and the commission may rise after promotions end. Blog source, UNCERTAIN. — [TILNOTE 2026 Toss fees](https://tilnote.io/en/pages/6a407f5e60849a3435aef1bd); [TILNOTE 2026 broker comparison](https://tilnote.io/en/pages/6a31d44ccb0ed8aacd89c0ec)
- Kiwoom: standard online overseas commission 0.25%, 0.07% under event conditions, FX preferential rate up to 95%. KIS: 0.08% after the new-customer event. Most brokers' standard rate is about 0.25%, cut to 0.03–0.09% during events. Some brokers have minimum commissions, which weigh heavily on small trades. Blog source, UNCERTAIN. — [TILNOTE 2026 fee comparison](https://tilnote.io/en/pages/6aa81f3a93f9084d15902733); [ttegl.com 2026 comparison](https://ttegl.com/overseas-stock-fees-comparison-guide/)
- US SEC fee on sales: 0.00206% of proceeds (minimum USD 0.01) for trades from 2026-04-02. Blog source, UNCERTAIN. — [TILNOTE 2026 Toss fees](https://tilnote.io/en/pages/6a407f5e60849a3435aef1bd)
- US equity settlement moved from T+2 to T+1 (SEC rule adopted Feb 2023; compliance from May 2024) — [SEC press release 2023-29](https://www.sec.gov/news/press-release/2023-29)

### Inferences
- Legal status: legal. Max leverage: 1x in a cash account. No source found that any Korean broker offers margin or credit for overseas stocks to retail.
- With KRW 42,000, a 0.1–0.25% commission costs about KRW 40–105 per side. FX conversion cost matters more: at a 95% preferential rate on a typical ~1% bank spread, the round trip costs about 0.1%. The ~1% base spread is not sourced here (inference).
- A minimum-commission rule at any broker could dominate costs on KRW-thousands orders. A designer should read each broker's fee schedule from its official page.

### Gaps
- Official fractional-trading minimums and eligible-ticker lists for KIS (미니스탁), Kiwoom, Mirae, Samsung, KB and NH were not retrieved. In particular, whether leveraged ETFs such as TQQQ or SOXL can be bought fractionally is unknown.
- Official FX spread tables (base spread) for each broker were not retrieved.
- How Korean brokers settle with the client in KRW (T+1 or T+2 for cash availability) was not confirmed from a broker page.

## 2. Overseas leveraged / inverse ETPs: the 2025 FSS/KOFIA investor-protection rules

### Takeaway
Since 2025-12-15, a new general retail investor must complete at least 1 hour of pre-education before buying overseas leveraged ETPs. Mock trading is not required for these products, and no basic deposit (기본예탁금) requirement for overseas products was reported. Single-stock leveraged/inverse products (domestic and overseas) need an extra 1-hour course that KOFIA added in 2026. Existing overseas leveraged ETP holders and earlier domestic course completers are exempt.

### Cited Findings
- The scheme was announced in May 2025 by the FSS and KOFIA (not the FSC), targeting December 2025 — [아시아경제 2025-05-25](https://www.asiae.co.kr/article/2025052512383160365); [디지털데일리 2025-05-25](https://m.ddaily.co.kr/page/view/2025052521020257390)
- Effective date: 2025-12-15. KB Securities' customer notice of 2025-11-14 states it. — [KB증권 공지 2025-11-14](https://m.kbsec.com/go.able?idt=20251114&linkcd=s060300010000&seq=10009222); [경향신문 2025-11-16](https://www.khan.co.kr/article/202511162115025)
- Overseas leveraged ETPs: at least 1 hour of pre-education. Mock trading is exempt because losses cannot exceed principal and trading works like ordinary stocks. — [경향신문 2025-11-16](https://www.khan.co.kr/article/202511162115025); [이데일리](https://marketin.edaily.co.kr/News/ReadE?newsId=01446486642172528)
- Provider: pre-education comes from KOFIA's 금융투자교육원 or from brokers that intermediate overseas derivatives. Hours can be raised by investor profile; inexperienced investors aged 65+ are recommended 10 hours of education and 7 hours of mock trading (for derivatives). — [아시아경제](https://www.asiae.co.kr/article/2025111417182638345); [이투데이](https://www.etoday.co.kr/news/view/2525851)
- Exempt: existing domestic or overseas leveraged ETP investors, and people who completed domestic leveraged ETP pre-education before the effective date. Completion gives a 14-digit number to register in the broker app. KB says completion is permanent (once per lifetime) and the course fee is KRW 4,000. — [데일리안](https://www.dailian.co.kr/news/view/1502047/); [extrememanual KB guide](https://extrememanual.net/60289)
- 기본예탁금: domestic futures and options need KRW 10M or more, but no such requirement exists for overseas futures and options, and reports said one would not be introduced — [이투데이](https://www.etoday.co.kr/news/view/2525851); [서울경제 (earlier)](https://www.sedaily.com/article/12915255)
- Single-stock leveraged/inverse products (domestic and overseas-listed): a new 1-hour KOFIA course is required. Investors without prior leveraged ETP experience need 2 hours in total (1h leveraged ETP guide + 1h single-stock course). Korea's first domestic single-stock leveraged/inverse products were set to launch 2026-05-22. — [한경비즈니스 2026-04-29](https://magazine.hankyung.com/business/article/202604295841b); [아시아경제 2026-04-28](https://core.asiae.co.kr/article/2026042809541792418)
- Leveraged ETPs track the daily return, so compounding can enlarge cumulative losses in volatile markets — [데일리안](https://www.dailian.co.kr/news/view/1502047/)

### Inferences
- Status: legal_with_conditions. Reachable: yes, but the KB-quoted KRW 4,000 course fee is about 10% of KRW 42,000. Max leverage: 3x daily at product level (TQQQ/SOXL); single-stock products are typically 2x. Losses are capped at the amount invested.
- The rule applies to general individual investors making new purchases, so the person must finish the course before the first buy order.
- US-listed leveraged ETFs are taxed like other overseas stocks (22% above KRW 2.5M). This is an inference, consistent with how overseas listed ETFs are treated; no source specific to leveraged ETFs was found.

### Gaps
- The exact definition of "해외 레버리지 ETP" (multiple threshold; whether -1x inverse is covered) was not read from the FSS or KOFIA primary text. The KB notice page rendered garbled.
- No FSS or FSC primary press release (fss.or.kr) was fetched. Dates and hours come from a broker notice and consistent news reports.
- Whether any post-June-2026 tightening happened (for example, a deposit for overseas leveraged ETPs) was not found. UNCERTAIN.

## 3. US-listed equity options and overseas futures/options via Korean brokers

### Takeaway
Several Korean brokers have offered US equity and ETF options since 2024. Samsung (2024-04-15, 56 underlyings) and KB (2024-08-05, 50 underlyings) offer long-only or close-only trading, and Samsung Futures offers 0DTE and single-stock options. Toss's November 2025 launch was postponed after FSS pushback, and its current status is unconfirmed. Since 2025-12-15, all overseas derivatives need at least 1 hour of education and at least 3 hours of mock trading, with no basic deposit. FSS data show Korean retail lost money on overseas derivatives every year from 2020 to 2025H1.

### Cited Findings
- Samsung Securities' US stock options service opened 2024-04-15 with 56 underlyings. Calls and puts can be bought; selling is allowed only to close. Monthly (3rd Friday) and weekly expiries. — [삼성증권 공지](https://www.samsungpop.com/ux/kor/customer/notice/notice/noticeViewContent.do?MenuSeqNo=20804)
- KB Securities' US stock options opened 2024-08-05 with 50 underlyings. Commission: USD 5.9 per contract online, USD 12.0 by phone or offline. 100 shares per contract. Trading hours 22:30–05:00 KST (23:30–06:00 outside US daylight time). T+1 settlement. Tax: 11% overseas-derivatives capital gains tax above the KRW 2.5M deduction. The page rendered garbled, so some labels are inferred. — [KB증권 미국주식옵션 공지 2024-08-05](https://m.kbsec.com/go.able?linkcd=s060300010000&seq=10007347&idt=20240805)
- Samsung Futures offers zero-day (0DTE) options and single-stock options brokerage and requires an overseas futures account — [삼성선물 FAQ](https://www.ssfutures.com/ssf/customer/advice/faq/CUS_02302.cmd)
- KIS: overseas options can be traded without a separate basic deposit, using the option premium (buy) or per-contract margin (sell) — [한국투자증권 해외옵션 안내](https://www.truefriend.com/main/bond/foreign/_static/TF03df110100.jsp); [KIS 해외선물옵션 특장점](https://m.koreainvestment.com/main/bond/foreign/_view/TF03df100500.jsp)
- Toss: full launch of US stock options was set for 2025-11-10 but postponed indefinitely after the FSS flagged ads on 2025-11-06 (e.g., the copy "엔비디아가 5% 오르면 옵션가격은 214% 오른다"). The mock-trading page and pre-application event were paused. — [SBS Biz 2025-11-07](https://biz.sbs.co.kr/amp/article/20000270729). Another result reports a 장내파생상품 투자중개업 license "in February" and a staged rollout. Its date is unclear and the launch is UNCERTAIN. — [중앙이코노미뉴스](https://www.joongangenews.com/news/articleView.html?idxno=419281); [insight.co.kr](https://www.insight.co.kr/news/515910)
- From 2025-12-15, first-time general retail investors in overseas derivatives must complete at least 1h of pre-education and at least 3h of mock trading before ordering — [경향신문 2025-11-16](https://www.khan.co.kr/article/202511162115025); [KB증권 공지 2025-11-14](https://m.kbsec.com/go.able?idt=20251114&linkcd=s060300010000&seq=10009222)
- KB's notice appears to exempt holders of valid derivatives qualifications such as CFA or FRM (garbled page, UNCERTAIN) — [KB증권 공지 2025-11-14](https://m.kbsec.com/go.able?idt=20251114&linkcd=s060300010000&seq=10009222)
- FSS retail loss statistics for overseas derivatives (KRW): 2020 5,667억; 2021 4,151억; 2022 4,574억; 2023 4,458억; 2024 3,609억; 2025H1 2,521억. Average about 4,580억 a year; cumulative 2조2,459억 over 5+ years; no profitable year. — [경향신문](https://www.khan.co.kr/article/202511162115025); [이투데이](https://www.etoday.co.kr/news/view/2525851)
- No 기본예탁금 for overseas futures and options, unlike the KRW 10M+ for domestic futures and options — [이투데이](https://www.etoday.co.kr/news/view/2525851)

### Inferences
- Status: legal_with_conditions for both US equity options and overseas futures, through a licensed Korean broker with a 해외선물옵션 account after 1h + 3h.
- Reachability with KRW 42,000:
  - Options: unclear or marginal. One long contract costs premium × 100 plus about USD 5.9 commission, so only options priced at a few cents fit in USD 30.
  - Futures: effectively no. Exchange margin per contract, even for micro contracts, is normally far above USD 30. This is an inference; margins were not fetched.
- Max leverage to this person: long-premium exposure only at Samsung, and probably at KB. Short options or futures margin would need margin capacity the capital does not support.

### Gaps
- Entry conditions at Kiwoom, Mirae, NH and KIS for US single-stock options specifically, and their current underlying lists, were not retrieved.
- Whether Toss actually launched options in 2026 was not confirmed.
- The FSS primary press release (fss.or.kr) with the loss table was not fetched directly. Figures come from two consistent news reports.

## 4. Foreign brokers (Interactive Brokers, Webull, Moomoo, eToro): legality of direct accounts and platform acceptance

### Takeaway
Korean law routes general investors' foreign-securities trading through a 투자중개업자 (시행령 제184조①). FX rules exempt residents' securities purchases from reporting when made through a 투자중개업자; otherwise acquiring securities from non-residents or holding overseas deposits is reportable. A direct account at a foreign broker is therefore grey at best for this person: the foreign broker itself may be outside the Act if it does not solicit, but the investor-side obligation in 제184조① still reads as binding. No investor-side penalty case was found. On the platform side, Moomoo and (per third parties) Webull do not serve Korea. IBKR appears to open accounts for Asian residents through IB LLC but bars Korean residents from KRX. eToro's status conflicts.

### Cited Findings
- 시행령 제184조① (under 자본시장법 제166조): general investors must trade foreign securities and exchange-traded derivatives on overseas markets "투자중개업자를 통하여". A 2024 amendment carved out a sell-only exception for foreign securities that were not acquired via a Korean dealer or broker and were acquired in a reporting-exempt capital transaction, such as employee stock compensation, inheritance, or gifts from non-residents. — [lawnb 시행령 제184조](https://www.lawnb.com/Info/ContentView?sid=L0002ED8D96EACC3_184_20240813); [일간NTN 2024-02-27](https://www.intn.co.kr/news/articleView.html?idxno=2034122); [KCMI 제도동향 2024-04](https://www.kcmi.re.kr/kcmifile/weekly_jedo/1779/webzinepdf_1779.pdf)
- NTN on the amendment: trades in overseas-listed securities or overseas derivatives other than the exceptions "기존과 동일하게 국내 증권사를 통해서 거래해야" — [일간NTN](https://www.intn.co.kr/news/articleView.html?idxno=2034122)
- FSC/FSS legal interpretation (reply 2018-10-25): when a foreign dealer or broker accepts a domestic resident's order without 투자권유 or 투자광고, its brokerage "자본시장법 적용 대상이 아닙니다". The basis is 시행령 제7조④6호나목. The reply concerned Koreans posted abroad who opened accounts in person at a foreign subsidiary. — [CaseNote: 자본시장법 시행령 제184조 관련 법령해석](https://casenote.kr/%EA%B8%88%EC%9C%B5%EC%9C%84%EC%9B%90%ED%9A%8C%C2%B7%EA%B8%88%EC%9C%B5%EA%B0%90%EB%8F%85%EC%9B%90/de7e327262)
- A separate FSC reply, as summarized by search, says 제184조① requires general investors trading foreign securities on overseas markets to go through a 투자중개업자, as one of the exceptionally permitted off-exchange methods — [CaseNote: 일반투자자의 외화증권 매도 관련 질의](https://casenote.kr/%EA%B8%88%EC%9C%B5%EC%9C%84%EC%9B%90%ED%9A%8C%C2%B7%EA%B8%88%EC%9C%B5%EA%B0%90%EB%8F%85%EC%9B%90/5cb355c4b9) (not fetched directly; UNCERTAIN wording)
- FX rules (BOK summary): when a resident acquires securities from a non-resident, the transaction must be reported to the Bank of Korea unless it is reporting-exempt or reportable to a foreign exchange bank. General investors' entrusting purchases to a 투자중개업자 is listed under 신고예외사항. — [BOK 자본거래](https://www.bok.or.kr/portal/main/contents.do?menuNo=200405). The NTN article ties the exemption to 외국환거래규정 제7-31조①. — [일간NTN](https://www.intn.co.kr/news/articleView.html?idxno=2034122)
- Overseas deposits (해외예금) are capital transactions that in principle need prior reporting to a foreign exchange bank. Annual cumulative overseas-deposit remittances over USD 10,000 are notified to the FSS. — [KB국민은행 kbthink 외환거래 신고](https://kbthink.com/fx/foreign-exchange-reporting.html); 1,072 FX-reporting violations were sanctioned in one FSS round — [SBS Biz](https://biz.sbs.co.kr/amp/article/20000322369)
- One secondary source says the current 외국환거래규정 is 재정경제부고시 제2026-88호, effective 2026-07-06 (UNCERTAIN; not checked on law.go.kr) — [cello library](https://library.cello.bz/article/164-foreign-exchange-investment-reporting-guide)
- IBKR: its Hong Kong site says residents of Asia (except India, Hong Kong and Japan) who open accounts get them with Interactive Brokers LLC (US) — [IBKR HK](https://www.interactivebrokers.com.hk/en/index.php?f=4089). KRX equity access is not available to residents of Korea (IBKR KRX launch, 2026) — [IBKR KRX page](https://www.interactivebrokers.com/en/trading/krx-exchange.php); [IBKR press release](https://www.interactivebrokers.com/en/general/about/mediaRelations/5-7-26.php). Third-party sites conflict on whether Korea is a restricted country: [TradersUnion lists Korea as restricted](https://tradersunion.com/brokers/forex/view/interactive_brokers/available-countries/), while [alexontrading says accounts are open to Korean residents](https://www.alexontrading.com/faq/availability/brokers/interactive-brokers-south-korea).
- Moomoo's official page lists availability in the US, Canada, Singapore, Australia, Japan, Malaysia and New Zealand; Korea is not listed — [Moomoo available countries](https://www.moomoo.com/us/learn/moomoo-available-countries)
- Webull reportedly does not accept new registrations from South Korea as of 2026 (third-party) — [BrokerRank](https://brokerrank.net/broker/webull/south-korea)
- eToro: a third-party site lists South Korea as accepted — [TradersUnion eToro countries](https://tradersunion.com/brokers/fond/view/etoro/etoro-available-countries/). eToro's own "Is eToro blocked in my country?" page would not render — [eToro help](https://help.etoro.com/s/article/is-etoro-blocked-in-my-country?language=en_GB). UNCERTAIN.
- Tax note: an account at a foreign financial institution can trigger the 해외금융계좌 신고 if month-end balances exceed KRW 500M. Foreign stocks held in a Korean broker account are not foreign financial accounts. — [cello library](https://library.cello.bz/article/164-foreign-exchange-investment-reporting-guide)

### Inferences
- IBKR direct: grey. The investor-side text of 제184조① points to a 투자중개업자. The FSC's own reading treats the foreign broker's non-solicited brokerage as outside the Act, and funding a foreign account brings FX reporting duties. No sanction case against an individual was found.
- Webull and Moomoo: blocked_by_platform. eToro: unknown.
- eToro's CFD products would also bring in 장외파생상품 rules not covered here.
- For a KRW 42,000 account, foreign brokers add international wire costs (often more than the capital) and FX reporting friction. This is an inference; wire fees were not sourced.

### Gaps
- Direct law.go.kr text of 외국환거래규정 제7-31조 and 제7-11조 (current 2026 version) was not retrieved, so the exact reporting thresholds for a resident funding a foreign brokerage account are unconfirmed.
- No source found on penalties actually applied to an individual for violating 시행령 제184조①. Whether a penalty provision covers the investor (as opposed to the broker) is UNCERTAIN.
- IBKR's own current country-eligibility statement for Korean residents, and eToro's and Webull's official lists, were not retrieved.

## 5. Taxes: overseas stock capital gains, dividends, 2026 changes

### Takeaway
Overseas stock gains are taxed separately from domestic stocks at 22% (20% national + 2% local) on annual net gains above KRW 2.5M, self-filed each May. Overseas derivatives are taxed at 11% above their own KRW 2.5M deduction. US dividends are withheld at 15% under the treaty. The 2026 changes are temporary FX-stabilization measures: RIA (국내시장 복귀계좌) deductions for overseas stocks held as of 2025-12-23, and a 5% deduction for FX-hedge products. They barely matter for a KRW 42,000 account.

### Cited Findings
- Overseas stock capital gains: KRW 2.5M annual basic deduction, 20% on the excess plus 2% local tax (22% in total). Gains and losses net within overseas stocks in the same year; taxed separately from domestic stocks (분류과세). Filed 1–31 May of the following year; 20% penalty for not filing. Blog-level sources, consistent with each other. — [wikidocs @Insight_Lab](https://wikidocs.net/blog/@Insight_Lab/22185/); [wikidocs @TaxSave](https://wikidocs.net/blog/@TaxSave/26706/); [삼성증권 양도소득세 안내](https://www.samsungpop.com/ux/kor/trading/overseasStock/overseasStockDealGuide/transferTax.do)
- A blog claims a 25% rate above KRW 300M and an expanded exit tax from 2026. This conflicts with other sources and is UNVERIFIED. — [wikidocs @infoplant](https://wikidocs.net/blog/@infoplant/18085/)
- Overseas derivatives (including US equity options): 11% tax on gains above KRW 2.5M, as stated by KB — [KB증권 미국주식옵션](https://m.kbsec.com/go.able?linkcd=s060300010000&seq=10007347&idt=20240805)
- US dividends: 15% withholding under the Korea–US treaty (30% without W-8BEN). Because the Korean rate of 14% is below 15%, no additional Korean withholding applies. Financial income above KRW 20M a year goes into comprehensive taxation with a foreign tax credit. — [PwC 삼일 one point tax](https://www.pwc.com/kr/ko/insights/issue-brief/samilpwc_one-point-tax-11.pdf); [KB think 해외주식 세금](https://kbthink.com/stock/foreign-tax.html)
- RIA: announced 2026-01-20 by 재정경제부. Cap: KRW 50M of sales per person. Proceeds must be converted to KRW and kept in domestic stocks or equity funds for 1 year. Net purchases of overseas stocks in general accounts reduce the benefit. FX-hedge products: 5% of the investment deductible from overseas stock gains, cap KRW 5M. Both are for 2026 only. — [정책브리핑 2026-01-20](https://www.korea.kr/news/policyNewsView.do?newsId=148958323)
- RIA deduction by sale-settlement date: 100% through 2026-05-31, 80% through 2026-07-31, 50% through 2026-12-31. Only applies to overseas stocks held as of 2025-12-23. — [신한투자증권 RIA 안내문 (2026-07-24 revision)](http://file.shinhansec.com/filedoc/clause/ria_keyinfo.pdf); [토스뱅크 RIA](https://www.tossbank.com/articles/ria). The legal basis is reported as 조세특례제한법 제91조의26 (new, 2026-04-21) and 시행령 제93조의12 (blog, UNCERTAIN) — [easyzetec](https://www.easyzetec.com/blog/ria-account-overseas-stock-sale-deduction-50-percent-adjustment-ratio)

### Inferences
- For a KRW 42,000 account, capital gains tax is zero unless annual net overseas stock gains exceed KRW 2.5M (or KRW 2.5M separately for derivatives). The person still has to file in May if gains exceed the deduction.
- RIA does not apply, because shares bought now were not held on 2025-12-23.

### Gaps
- NTS primary guide (2025 해외주식과 세금) was downloaded but could not be text-extracted, so the 소득세법 article numbers (e.g., 제94조, 제104조, 제118조의2) are not cited from primary text.
- Whether the 2026 tax-law amendment (passed late 2026 for 2027) changes overseas stock rates was not checked. UNCERTAIN.
