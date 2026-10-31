# Daily-close research data audit — 2026-10-31

This audit fixes the input universe before new candidate performance evaluation. It reads only existing public-market CSV caches. No market API, credential, account state, protected GrokBot event or paper_live H2 holdout is accessed. The original caches are not changed or copied.

## Research status and provenance

Every selected series was inspected in the earlier asset-expansion study, whose manifest is dated 2026-09-27. New chronological splits are **internal pseudo-out-of-sample exploratory analyses**, not untouched, independent or prospective confirmation. The previous S_C3 PASS does not transfer to a new rule, risk overlay or expanded search. The fixed instruments are survivors, not a historical point-in-time universe.

- Source cache: `docs/asset_expansion/cache/` (46 CSV files).
- Acquisition code: `docs/asset_expansion_study.py`, functions `yf`, `upbit` and `binance`. Yahoo downloads use `auto_adjust=True` and retain only `Close`.
- Crypto loader: `data/crypto/crypto_client.py`, `UpbitPublic.daily` and `BinancePublic.daily`. Upbit UTC day labels have a 09:00 Asia/Seoul boundary; Binance spot klines use UTC.
- The manifest pins raw bytes and acquisition-code bytes with SHA256. Its selected-row hash also binds the exact retained date/value strings after the cutoff. It retains all 46-file inventory diagnostics.
- The run protocol must separately pin `research_lab/data_manifest.json` and its own bytes before any performance evaluation. The loader exports `manifest_digest()` for that purpose.

## Fixed eight-series universe

| Asset ID | Source symbol | Currency | Annualization | Used rows | First date | Last date | Adjustment |
| --- | --- | --- | ---: | ---: | --- | --- | --- |
| SPY | SPY | USD | 252 | 7985 | 1995-01-03 | 2026-09-24 | provider_adjusted_close |
| QQQ | QQQ | USD | 252 | 6929 | 1999-03-10 | 2026-09-24 | provider_adjusted_close |
| GLD | GLD | USD | 252 | 5496 | 2004-11-18 | 2026-09-24 | provider_adjusted_close |
| TLT | TLT | USD | 252 | 6078 | 2002-07-30 | 2026-09-24 | provider_adjusted_close |
| TIGER200 | 102110.KS | KRW | 252 | 4266 | 2009-04-17 | 2026-09-23 | provider_adjusted_close |
| BTC_KRW | KRW-BTC | KRW | 365 | 3287 | 2017-09-25 | 2026-09-24 | unadjusted_spot_close |
| BTC_USDT | BTCUSDT | USDT | 365 | 3326 | 2017-08-17 | 2026-09-24 | unadjusted_spot_close |
| ETH_USDT | ETHUSDT | USDT | 365 | 3326 | 2017-08-17 | 2026-09-24 | unadjusted_spot_close |

The cutoff is **2026-09-24 inclusive** for every input; KRX has no cached date after 2026-09-23. The crypto downloader does not explicitly exclude an ongoing candle and there is no per-file capture timestamp. Removing the last stored US/crypto day is a conservative convention, not independent certification that every retained bar was closed when first captured. These are stale historical study inputs, not a current market feed.

USD, KRW and USDT returns remain in their native quoted units. Annualization is a reporting convention (252 ETF observations or 365 crypto calendar observations), not a guarantee of data completeness. USDT is not assumed equal to USD. There is no automatic FX conversion or inference of the owner account's KRW realized net profit.

### Exact selected source fingerprints

| Asset | Relative source path | Raw-file SHA256 |
| --- | --- | --- |
| SPY | `docs/asset_expansion/cache/yf_SPY.csv` | `5b6754cb4514247970da589ce77bcc6df29f4a59871a5fab8f9efdd5646cee89` |
| QQQ | `docs/asset_expansion/cache/yf_QQQ.csv` | `57f9f8e0a03ad117cc6fd448391ddd2aa4b1b3147f89f9c541c3a6c67eabc452` |
| GLD | `docs/asset_expansion/cache/yf_GLD.csv` | `2f44fd3cc15e15e4a34fd4121e5843dc121b9bb7fb65b559cf9eef730b7e362c` |
| TLT | `docs/asset_expansion/cache/yf_TLT.csv` | `523bbd66d3e07f16c500a28d5a8739460e161e48fe6baeb4c1c4c080c519bc80` |
| TIGER200 | `docs/asset_expansion/cache/yf_102110.KS.csv` | `710228fde9e520ffbe1417293aebf804e82e26b1705791b434345c974cb00d68` |
| BTC_KRW | `docs/asset_expansion/cache/upbit_KRW-BTC.csv` | `a08e693dc090677985501719d289d55d074428fb930e66eec805da1794de0d6f` |
| BTC_USDT | `docs/asset_expansion/cache/binance_BTCUSDT.csv` | `efd78ccd87c29d8c1fbab385473987e314f748193b20a518c0f36895435358c7` |
| ETH_USDT | `docs/asset_expansion/cache/binance_ETHUSDT.csv` | `b1f928cb63aae2913ad288d5a4d15c39e25e12c52c3c9e48815f347c8da9ab01` |

## Quality findings and decisions

All eight selected files have strictly increasing unique ISO dates, finite positive close values and no empty prices. Crypto daily calendars have no missing dates. The loader verifies the exact raw source hash before parsing, rejects unlisted asset IDs and linked source files, then verifies selected-row fingerprints. It neither fills gaps nor silently removes bad prices.

The unselected KODEX 200 (`yf_069500.KS.csv`) has eight 2007 observations followed by an **800-day gap from 2007-02-07 to 2009-04-17**. It is excluded in favor of TIGER 200 (`yf_102110.KS.csv`), which begins on 2009-04-17. Both have a later 11-day 2017 Chuseok gap. The audit does not equate all long gaps with erroneous data and does not certify every equity exchange calendar.

The FRED FX file has 109 empty observations and the Treasury bill-rate file has 395; current vintages and holiday missingness prevent point-in-time predictive claims without additional release/vintage evidence. They are inventoried, but not used as strategy inputs here. Negative funding rates, zero Treasury rates and the negative crude-oil futures observation are economically possible; nonpositive counts in the inventory are diagnostics, not automatic invalidation of those non-price series. Futures, volatility indices and the one-row KOSPI200 series are excluded from the cash-asset research universe.

## What these data cannot establish

1. Only a date and close are retained. There is no OHLCV, quote spread, order-book depth, volume, borrow, order-status or historical execution record. Limit-order fills, partial fills, slippage, intraday stops and liquidity capacity cannot be directly verified. The research engine must use disclosed conservative return/cost conventions.
2. Provider-adjusted closes reflect Yahoo's adjustment convention. They are not an independently audited total-return series or point-in-time corporate-action vintage. Do not add dividend cash again or infer broker tax/settlement proceeds from these values.
3. Close-based marked portfolio returns do not equal FIFO realized net profit in a live account. A separate exact account ledger, fees, FX, taxes where applicable and cash-flow reconciliation are needed.
4. Trading minimums, integer shares, tick bands, account eligibility and protection-floor execution are not certified by normalized daily-return simulations. In particular, these inputs cannot establish guaranteed principal protection or a minimum daily profit.
5. Testing many rules on previously studied caches increases data-snooping risk. Keep all candidate results, record the complete search size, use chronological validation and multiplicity controls, and reserve prospective evidence for a later independent stage.

## Complete cache inventory

Dates and counts below describe the original file bytes, before the study cutoff. Full SHA256 values, file sizes, columns, all long gaps and selected-row hashes are in `research_lab/data_manifest.json`. Missing, malformed and nonfinite counts are recorded separately.

| File | Rows | First | Last | Missing | Nonpositive | Duplicates | Maximum calendar gap (days) | SHA256 prefix |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: | --- |
| binance_BTCUSDT.csv | 3327 | 2017-08-17 | 2026-09-25 | 0 | 0 | 0 | 1 | `efd78ccd87c2` |
| binance_ETHUSDT.csv | 3327 | 2017-08-17 | 2026-09-25 | 0 | 0 | 0 | 1 | `b1f928cb63aa` |
| binance_funding_BTCUSDT.csv | 2573 | 2019-09-10 | 2026-09-25 | 0 | 324 | 0 | 1 | `54d07c7fa48e` |
| fred_DEXKOUS.csv | 2535 | 2017-01-02 | 2026-09-18 | 109 | 0 | 0 | 3 | `625d69f4829d` |
| fred_DGS3MO.csv | 9583 | 1990-01-01 | 2026-09-23 | 395 | 21 | 0 | 3 | `33a3b49ebbdb` |
| upbit_KRW-BTC.csv | 3288 | 2017-09-25 | 2026-09-25 | 0 | 0 | 0 | 1 | `a08e693dc090` |
| yf_000270.KS.csv | 6681 | 2000-01-04 | 2026-09-23 | 0 | 0 | 0 | 11 | `c0303e00ee70` |
| yf_005380.KS.csv | 6681 | 2000-01-04 | 2026-09-23 | 0 | 0 | 0 | 11 | `7e592a607086` |
| yf_005930.KS.csv | 6681 | 2000-01-04 | 2026-09-23 | 0 | 0 | 0 | 11 | `060495d1feb9` |
| yf_005935.KS.csv | 5184 | 2005-09-29 | 2026-09-23 | 0 | 0 | 0 | 11 | `ffd9da02f88a` |
| yf_069500.KS.csv | 4274 | 2007-01-29 | 2026-09-23 | 0 | 0 | 0 | 800 | `142ad6165670` |
| yf_102110.KS.csv | 4266 | 2009-04-17 | 2026-09-23 | 0 | 0 | 0 | 11 | `710228fde9e5` |
| yf_122630.KS.csv | 4052 | 2010-02-22 | 2026-09-23 | 0 | 0 | 0 | 11 | `480cc807c6d7` |
| yf_132030.KS.csv | 3900 | 2010-10-01 | 2026-09-23 | 0 | 0 | 0 | 11 | `03d49e31cfe1` |
| yf_152380.KS.csv | 3559 | 2012-01-20 | 2026-09-23 | 0 | 0 | 0 | 11 | `09320c901c37` |
| yf_229200.KS.csv | 2663 | 2015-10-01 | 2026-09-23 | 0 | 0 | 0 | 11 | `9fb7b5f76177` |
| yf_379800.KS.csv | 1315 | 2021-04-09 | 2026-09-23 | 0 | 0 | 0 | 8 | `a7c77d328e0b` |
| yf_BTC-USD.csv | 4392 | 2014-09-17 | 2026-09-25 | 0 | 0 | 0 | 1 | `d8f9ff14f14f` |
| yf_CL_F.csv | 6551 | 2000-08-23 | 2026-09-25 | 0 | 1 | 0 | 5 | `1177e7a1bb74` |
| yf_GC_F.csv | 6543 | 2000-08-30 | 2026-09-25 | 0 | 0 | 0 | 5 | `8a3b32594abb` |
| yf_GLD.csv | 5497 | 2004-11-18 | 2026-09-25 | 0 | 0 | 0 | 5 | `2f44fd3cc15e` |
| yf_HG_F.csv | 6547 | 2000-08-30 | 2026-09-25 | 0 | 0 | 0 | 5 | `c344c1f4b907` |
| yf_IAU.csv | 5449 | 2005-01-28 | 2026-09-25 | 0 | 0 | 0 | 5 | `46bbeff347bd` |
| yf_NG_F.csv | 6548 | 2000-08-30 | 2026-09-25 | 0 | 0 | 0 | 5 | `7b3920111776` |
| yf_QQQ.csv | 6930 | 1999-03-10 | 2026-09-25 | 0 | 0 | 0 | 7 | `57f9f8e0a03a` |
| yf_SI_F.csv | 6544 | 2000-08-30 | 2026-09-25 | 0 | 0 | 0 | 5 | `4dba125dc78d` |
| yf_SPY.csv | 7986 | 1995-01-03 | 2026-09-25 | 0 | 0 | 0 | 7 | `5b6754cb4514` |
| yf_TLT.csv | 6079 | 2002-07-30 | 2026-09-25 | 0 | 0 | 0 | 5 | `523bbd66d3e0` |
| yf_VIXY.csv | 3955 | 2011-01-04 | 2026-09-25 | 0 | 0 | 0 | 5 | `0d4271c194cf` |
| yf_XLB.csv | 6982 | 1998-12-22 | 2026-09-25 | 0 | 0 | 0 | 7 | `275e0d2d4ec0` |
| yf_XLE.csv | 6982 | 1998-12-22 | 2026-09-25 | 0 | 0 | 0 | 7 | `0bd0b6a32f37` |
| yf_XLF.csv | 6982 | 1998-12-22 | 2026-09-25 | 0 | 0 | 0 | 7 | `095ecb5a3857` |
| yf_XLI.csv | 6982 | 1998-12-22 | 2026-09-25 | 0 | 0 | 0 | 7 | `67ce62fccb04` |
| yf_XLK.csv | 6982 | 1998-12-22 | 2026-09-25 | 0 | 0 | 0 | 7 | `2f2a05b491e2` |
| yf_XLP.csv | 6982 | 1998-12-22 | 2026-09-25 | 0 | 0 | 0 | 7 | `1cd2b23af3eb` |
| yf_XLU.csv | 6982 | 1998-12-22 | 2026-09-25 | 0 | 0 | 0 | 7 | `22a988a06f88` |
| yf_XLV.csv | 6982 | 1998-12-22 | 2026-09-25 | 0 | 0 | 0 | 7 | `6e4f4fe31c57` |
| yf_XLY.csv | 6982 | 1998-12-22 | 2026-09-25 | 0 | 0 | 0 | 7 | `1a5ec83b7459` |
| yf_ZB_F.csv | 6538 | 2000-09-21 | 2026-09-25 | 0 | 0 | 0 | 5 | `1860ad9e1226` |
| yf_ZC_F.csv | 6554 | 2000-07-17 | 2026-09-25 | 0 | 0 | 0 | 14 | `250be4510e7a` |
| yf_ZF_F.csv | 6544 | 2000-09-21 | 2026-09-25 | 0 | 0 | 0 | 5 | `78b88aebc53e` |
| yf_ZN_F.csv | 6532 | 2000-09-21 | 2026-09-25 | 0 | 0 | 0 | 12 | `26d180bed7b6` |
| yf_ZS_F.csv | 6546 | 2000-09-15 | 2026-09-25 | 0 | 0 | 0 | 5 | `c1f660739016` |
| yf__KS200.csv | 1 | 2026-09-23 | 2026-09-23 | 0 | 0 | 0 | 0 | `d48e9f551ef9` |
| yf__VIX.csv | 7988 | 1995-01-03 | 2026-09-25 | 0 | 0 | 0 | 7 | `1769605eb9c8` |
| yf__VIX3M.csv | 5081 | 2006-07-17 | 2026-09-25 | 0 | 0 | 0 | 5 | `d72950f280b3` |

All 46 files have zero malformed and zero nonfinite nonempty values, no duplicated dates and increasing dates. A date-only gap check is not an exchange-calendar reconciliation.

## Offline loader contract

`research_lab.data.load_series(asset, root=repository_root)` returns dates and closes as immutable tuples, native currency, annualization, source path/hash, selected-row hash, manifest hash, adjustment status and provenance. `load_assets(root=repository_root)` loads all eight assets against one manifest snapshot. There are no network or live-account dependencies. Performance evaluation remains separate and must wait for the manifest/protocol freeze.

This is reproducible exploratory research, not legal, tax or investment advice; the software and its author are not licensed advisers.
