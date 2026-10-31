# Retrospective strategy-lab protocol — frozen before this computation

Date: 2026-10-31. The owner's research request authorizes broad strategy development, quantitative evaluation and an academic-style report. It does not turn research returns into orders or permit changes to frozen prior studies. This document and [`research_lab/protocol.json`](../../../research_lab/protocol.json) specify the study before candidate performance is computed. The root records their Git commit and SHA256, the data manifest and complete candidate catalogue before evaluation.

**Evidence status:** exploratory, retrospective internal holdout. Every selected historical cache was available to the earlier asset-expansion study. Preregistering this new computation prevents further undocumented tuning; it cannot erase prior researcher exposure to the sample. No result is a fresh independent confirmation or production approval. Existing S_C3 PASS remains evidence only for its original protocol. GrokBot and paper-live frozen holdouts are neither read nor modified.

This is research and software analysis, not legal, tax or investment advice. Neither the software nor its author is a licensed adviser.

## 1. Data and chronology

The fixed eight assets are SPY, QQQ, GLD, TLT, TIGER200, Upbit KRW-BTC, Binance BTC-USDT and Binance ETH-USDT. The data manifest identifies every source file, selected-row digest, source-code provenance and caveat. US ETF series are Yahoo auto-adjusted close proxies, not executable raw prices. Crypto rows are close-only exchange cache observations. There is no intraday OHLCV, depth, fill or spread evidence.

All samples end no later than 2026-09-24; the potentially provisional final crypto candle dated 2026-09-25 is excluded. TIGER200 is chosen in advance because KODEX200 has a documented early 800-day gap. No historical price is forward-filled to manufacture an execution bar. Native currencies remain USD, KRW and USDT; they are not treated as equivalent account units. Current-vintage macro/FX data cannot establish point-in-time causal availability and does not condition these signals.

| Window | Fixed boundary | Minimum scored observations |
| --- | --- | --- |
| Training/descriptive history | Available history through 2020-12-31 | 500 |
| Selection/validation | 2021-01-01 through 2022-12-31 | 365 |
| Retrospective internal holdout | 2023-01-01 through 2026-09-24 | 365 |

A common 500-bar warm-up precedes scored observations. It exceeds the longest required 120-bar volatility estimate plus 252 preceding estimates for a volatility quantile. Insufficient assets remain in the hypothesis family with p=1 and a reason; dates are not moved to rescue them. Annualization is 252 for ETFs and 365 for daily crypto. No result uses the existing research helper's unconditional 252 convention for crypto.

## 2. Finite candidate catalogue

There are eight signal families, not 21,408 independent economic discoveries. The exact parameter grids and equality rules are in protocol.json. Three trend transformations, two reversal oscillators, a breakout rule, volatility conditioning and drawdown recovery overlap economically; that dependence is retained in the resampling.

| Family | Raw rules | Economic interpretation to examine, not assume |
| --- | ---: | --- |
| Time-series momentum | 27 | Underreaction and persistent risk exposure |
| Price relative to moving average | 27 | Trend filtering and regime-dependent risk reduction |
| Fast/slow moving-average crossover | 40 | Persistence across horizons |
| Prior-range breakout | 15 | Continuation after price discovery |
| Log-price z-score reversal | 30 | Temporary displacement and liquidity provision |
| Rolling simple RSI reversal | 30 | Short-horizon reversal versus continuation |
| Low-volatility positive trend | 27 | Volatility-managed exposure, not leverage |
| Drawdown reversal/recovery | 27 | Distress compensation and rebound risk |
| **Total raw rules** | **223** | Correlated technical hypotheses |

Every raw rule crosses rebalance intervals {1,5,21} bars, target caps {0.5,1.0}, and volatility sizing {off,15% annual target}. That yields **2,676 configurations per asset; 21,408 configurations overall**. All declared configurations remain in trial accounting even if their realized signals coincide. No rule is added in response to observed performance.

Binary signals use only closes through their own timestamp, computed on every bar. Sampled rebalance decisions set weight to the cap, or `min(cap, 0.15 / trailing_annualized_volatility)` with a 20-bar log-return sample standard deviation. Invalid or zero volatility gives cash. A cap is a rebalance target; the position can drift between rebalance dates. This is a fractional-share research model, not evidence that an owner's capital can buy the required whole lot or meet venue minimums.

## 3. Timing, costs and accounting model

At close t, the portfolio first marks previously held shares. A signal known at close t-1 can then execute at close t; it earns only the following interval's price return. Primary delay is one complete bar, with two-bar delay as a separately reported stress. This avoids assigning a fill at the same close that first supplies the signal, but close proxies still do not establish actual limit fills or executable market-on-close prices.

Each phase starts entirely in cash. Rebalance dates are anchored to that phase's first close and repeat every k observed bars. The final row liquidates the remaining position, charging its cost and skipping any new entry. Signal history before the phase can supply causal trailing indicators; no uncharged position carries into it.

Shares and nonnegative cash evolve self-financingly, without shorting or leverage. If E is pretrade equity, V current asset value, w target post-fee weight, P price and c per-side cost, a buy changes units by `(w*E-V)/(P*(1+c*w))`; a sell changes units by `(V-w*E)/(P*(1-c*w))`. Costs are deducted once. The fee-inclusive equation avoids silently financing commissions from unavailable cash.

Per-side model floors are 50 bp for US ETFs, 3 bp for KRX ETFs and 10 bp for crypto, matching `core/quant/validate.py:COST_BP_PER_SIDE`. They are historical research assumptions, not verified current broker charges. Recompute at 2x and 3x costs; do not infer a stress path by mechanically scaling final profits. Cash earns zero, and income taxes are not modeled. The benchmark is a same-window fully invested buy-and-hold portfolio with the same initial and terminal costs.

## 4. Selection and inferential tests

Select at most one configuration per asset on validation net Sharpe, requiring positive validation net mean and at least 20 completed round trips. Ties within 1e-12 choose lower turnover and then lexical candidate ID. Freeze that identity before exposing internal-holdout results. If none qualify, the sleeve stays cash. A failed holdout never triggers selection of the runner-up.

The primary validation diagnostic is a White-style centered circular moving-block max-mean test over all configurations against costed buy-and-hold. For each strategy j, use `d[t,j]=r_strategy[t,j]-r_benchmark[t]`; compare `max(0, sqrt(T)*max_j(mean(d[:,j])))` with joint resampled maxima after centering every column by its sample mean. All candidates share each date draw, retaining cross-strategy dependence. Centering poor alternatives too can be conservative; this is not Hansen's SPA.

Use 1,999 bootstrap replicates with 20-bar blocks. Fixed sensitivities use 999 replicates with 5- and 60-bar blocks. A sensitivity cannot replace the primary because it is more favorable. Every Monte Carlo p is `(1+exceedances)/(B+1)`, never zero. Holm adjusts the eight primary asset omnibus p values without an independence assumption. Missing or insufficient assets remain p=1.

For the already frozen winner, report paired block-bootstrap 95% mean, mean-difference and Sharpe-difference intervals, plus the centered one-sided mean-difference p against costed buy-and-hold. Holm adjusts those eight holdout comparisons as a separate, explicitly identified family. Positive return over zero cash is secondary: compensation for exposure to a rising risky asset is not proof of alpha.

The market-model regression `r_strategy=alpha+beta*r_benchmark+error` is diagnostic. Its intercept uses Bartlett Newey-West covariance with 20 lags and n/(n-2) correction; no causal factor attribution or unobserved Fama-French controls are claimed. Degenerate benchmarks or residual variances produce unavailable diagnostics instead of manufactured significance.

The label **promising_exploratory** requires all of: validation omnibus Holm p<=0.05; holdout winner-versus-benchmark mean Holm p<=0.05; positive holdout net mean; positive holdout mean at 2x costs; and at least 30 completed holdout round trips. Every other outcome is reported without searching again. Even this label remains **NOT_VALIDATED_FOR_PRODUCTION**, because the sample has been inspected before and actual execution feasibility is unproven.

## 5. Basket and economic interpretation

Only the four USD ETF sleeves form a common-currency descriptive basket. Give each independent selected sleeve one quarter of initial model capital, retaining cash for no selection; do not rebalance or transfer capital between sleeves. Basket wealth is the mean of their normalized wealth paths, and returns follow its changes. Require identical holdout dates or report the basket unavailable. Compare with identically constructed buy-and-hold sleeves. It is a secondary fractional-capital model with no extra pass gate, never KRW realized P&L or a mixture of USD/KRW/USDT pretending to be one investable account.

Report the full candidate distribution, turnover, completed trades, cost effects, exposures, maximum drawdowns, phase degradation and failures. Higher Sharpe paired with lower mean can describe risk reduction without benchmark-beating return. An economic story motivates a hypothesis; it is not causal evidence. No observed zero frequency becomes a zero-probability claim.

## 6. Owner protection policy and final artifacts

Keep the requested equity-protection policy separate from marked daily research returns. Prior-day realized net profit requires actual lot/fill/fee accounting; marked gains in an open position do not qualify. Daily close observations cannot prove intraday protection-floor compliance. Unknown first-session and zero-profit-day loss allowances, valuation and external-flow conventions remain unknown. No simulation manufactures an exemption or unlimited risk budget.

Output the frozen catalogue, every candidate outcome, selected identities, all adjusted/raw p values with their families, holdout/stress paths, methodology hashes, source revision and explicit limitations. The academic-style PDF must include abstract, data/provenance, economic hypotheses, methods, results including nulls, limitations, reproducibility and references. It is a technical research report, not a claim of peer review.

Meaningful synthetic tests cover known null/alternative behavior, shared dependence, autocorrelated sampling uncertainty, Holm ordering and declared family size, timing causality, self-financing accounting and malformed-input refusal. Tests use no historical candidate P&L before the root freezes this protocol. Any later methodological change is versioned as a new study rather than hidden in the result.
