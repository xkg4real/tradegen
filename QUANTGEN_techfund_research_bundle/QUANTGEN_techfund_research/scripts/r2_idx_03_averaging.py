"""r2_idx_03_averaging.py -- Task 3: the Shiller monthly-AVERAGE price bias in trend backtests, US checks.

Monthly long/flat rules, position in month m+1 decided from prices through month m, cash 0%, gross:
  SMA10   X(m) > mean(X(m-9..m))
  TSM12   X(m) / X(m-12) - 1 > 0 (price change); TSM12 L/S = +1 / -1 on the same sign (E3's "12m L/S").
Price series X:
  ME      true month-end closes (last session of the month) from daily data;
  AVG     monthly average of daily closes (what Shiller's S&P 500 column is); returns are average-to-average;
  SHILLER Shiller's monthly average S&P 500 (price, or total return with D/12 added; dividends after 2023-06
          imputed at the last 12-month yield, as in the round-1 US lab);
  HYBRID  signal from AVG, returns from ME (isolates the return-measurement part of the bias);
  LAG1    signal from month m-1 applied to month m+1 (the round-1 'lag1' fix for averaged prices).
Daily sources: SPY (Lean, unadjusted, 1998-01..2021-03) and the arch S&P 500 index (1999-01..2018-12).
Windows: SPY / Shiller overlap 1999-03..2021-03 (first month at which the LAG1 variant also has a 12-month signal); arch 2000-03..2018-12.
Sharpe = mean / sd x sqrt(12) of monthly returns (0% cash). R/V (E1) = annualised arithmetic mean / vol.
"""
import numpy as np
import pandas as pd

import r2_idx_common as C

ALL_ROWS = []


def monthly_from_daily(s):
    per = s.index.to_period('M')
    me = s.groupby(per).last()
    avg = s.groupby(per).mean()
    return me, avg


def shiller():
    raw = pd.read_csv(C.SHILLER_CSV, parse_dates=['Date']).set_index('Date')
    raw.index = raw.index.to_period('M')
    raw = raw.astype(float).replace(0.0, np.nan)
    P, D = raw['SP500'], raw['Dividend']
    last_d = D.last_valid_index()
    dy = float(D[last_d] / P[last_d])
    Df = D.copy()
    Df[raw.index > last_d] = dy * P[raw.index > last_d]
    R_tr = (P + Df / 12.0) / P.shift(1) - 1.0
    return P, R_tr, str(last_d)


def signals(X):
    sma10 = (X > X.rolling(10, min_periods=10).mean()).astype(float).where(X.rolling(10, min_periods=10).count() == 10)
    tsm12 = ((X / X.shift(12) - 1.0) > 0).astype(float).where(X.shift(12).notna())
    return {'SMA10': sma10, 'TSM12': tsm12, 'TSM12 L/S': (2 * tsm12 - 1).where(tsm12.notna())}


def stats(x):
    x = x.dropna()
    m = x.mean() * 12
    v = x.std(ddof=1) * np.sqrt(12)
    w = np.concatenate([[1.0], np.cumprod(1 + x.values)])
    return dict(n_months=len(x), mean_ann=m, vol_ann=v, sharpe=m / v if v > 0 else np.nan,
                cagr=float(np.prod(1 + x.values) ** (12 / len(x)) - 1), max_dd=float((w / np.maximum.accumulate(w) - 1).min()),
                acf1=float(x.autocorr(1)))


def evaluate(source, sig_X, ret, window, lag=1, label_extra=''):
    """sig_X: price series used for signals; ret: monthly returns earned; lag 1 = standard, 2 = LAG1."""
    a, b = window
    out = {}
    bh = ret.loc[a:b]
    out['buy-and-hold'] = stats(bh)
    for rn, sg in signals(sig_X).items():
        pos = sg.shift(lag)
        rr = (pos * ret).loc[a:b]
        assert pos.loc[a:b].notna().all(), (source, rn, a)
        st = stats(rr)
        st['time_in_market'] = float((pos.loc[a:b] > 0).mean())
        st['switches_per_year'] = float((pos.loc[a:b].diff().abs() > 0).sum() / (len(rr) / 12))
        out[rn] = st
    rows = []
    for rn, st in out.items():
        rows.append(dict(source=source + label_extra, window=f'{a}..{b}', rule=rn, **st))
    return rows


def main():
    rows = []
    spy = C.load_spy_daily()
    me, avg = monthly_from_daily(spy)
    sp = C.load_sp500_arch()
    me2, avg2 = monthly_from_daily(sp)
    P, R_tr, last_div = shiller()
    R_px = P / P.shift(1) - 1.0
    W_SPY = ('1999-03', '2021-03')
    W_ARCH = ('2000-03', '2018-12')
    r_me, r_avg = me / me.shift(1) - 1, avg / avg.shift(1) - 1
    r_me2, r_avg2 = me2 / me2.shift(1) - 1, avg2 / avg2.shift(1) - 1
    rows += evaluate('SPY month-end', me, r_me, W_SPY)
    rows += evaluate('SPY month-average', avg, r_avg, W_SPY)
    rows += evaluate('SPY month-average LAG1', avg, r_avg, W_SPY, lag=2)
    rows += evaluate('SPY HYBRID (avg signal, month-end returns)', avg, r_me, W_SPY)
    rows += evaluate('SPY month-end LAG1', me, r_me, W_SPY, lag=2)
    rows += evaluate('S&P500 (arch) month-end', me2, r_me2, W_ARCH)
    rows += evaluate('S&P500 (arch) month-average', avg2, r_avg2, W_ARCH)
    rows += evaluate('S&P500 (arch) month-average LAG1', avg2, r_avg2, W_ARCH, lag=2)
    rows += evaluate('Shiller average, price', P, R_px, W_SPY)
    rows += evaluate('Shiller average, price, LAG1', P, R_px, W_SPY, lag=2)
    rows += evaluate('Shiller average, total return', P, R_tr, W_SPY)
    # long history (Shiller), standard vs LAG1, price and total return
    for lab, w in (('1872-2026', ('1872-03', '2026-09')), ('1927-2018', ('1927-01', '2018-11')),
                   ('1999-2021', W_SPY), ('2009-2026', ('2009-01', '2026-09')), ('2010-2026', ('2010-01', '2026-09'))):
        rows += evaluate(f'Shiller TR [{lab}]', P, R_tr, w)
        rows += evaluate(f'Shiller TR LAG1 [{lab}]', P, R_tr, w, lag=2)
        rows += evaluate(f'Shiller price [{lab}]', P, R_px, w)
        rows += evaluate(f'Shiller price LAG1 [{lab}]', P, R_px, w, lag=2)
    df = pd.DataFrame(rows)
    C.save_csv(df, 'r2_idx_averaging_rules.csv')
    # ---------------- bias table on the overlap (rule minus buy-and-hold, averaged minus month-end)
    def get(src, rule, col):
        v = df[(df.source == src) & (df.rule == rule)][col]
        return float(v.iloc[0])
    bias = []
    for rule in ('SMA10', 'TSM12', 'TSM12 L/S'):
        for avg_src, me_src, tag in (('SPY month-average', 'SPY month-end', 'SPY 1999-03..2021-03'),
                                     ('S&P500 (arch) month-average', 'S&P500 (arch) month-end', 'S&P 500 2000-03..2018-12'),
                                     ('Shiller average, price', 'SPY month-end', 'Shiller avg vs SPY month-end 1999-2021'),
                                     ('SPY month-average LAG1', 'SPY month-end', 'SPY avg LAG1 vs month-end'),
                                     ('SPY HYBRID (avg signal, month-end returns)', 'SPY month-end', 'SPY hybrid vs month-end')):
            row = dict(comparison=tag, rule=rule)
            for c in ('sharpe', 'max_dd', 'cagr', 'vol_ann'):
                row[f'{c}_avg'] = get(avg_src, rule, c)
                row[f'{c}_me'] = get(me_src, rule, c)
                row[f'{c}_bh_avg'] = get(avg_src.replace(' LAG1', '').replace('HYBRID (avg signal, month-end returns)', 'month-end') if 'HYBRID' in avg_src else avg_src.replace(' LAG1', ''), 'buy-and-hold', c)
                row[f'{c}_bh_me'] = get(me_src, 'buy-and-hold', c)
            row['sharpe_inflation'] = row['sharpe_avg'] - row['sharpe_me']
            row['timing_benefit_avg'] = row['sharpe_avg'] - row['sharpe_bh_avg']
            row['timing_benefit_me'] = row['sharpe_me'] - row['sharpe_bh_me']
            row['timing_benefit_inflation'] = row['timing_benefit_avg'] - row['timing_benefit_me']
            row['mdd_understatement_pp'] = (row['max_dd_avg'] - row['max_dd_me']) * 100
            bias.append(row)
    C.save_csv(pd.DataFrame(bias), 'r2_idx_averaging_bias.csv')
    # ---------------- autocorrelation (E3: 0.057 month-end vs 0.206 month-average, SPY 1998-2021)
    ac = []
    for lab, a, b in (('SPY 1998-02..2021-03', '1998-02', '2021-03'), ('SPY 1999-02..2021-03', '1999-02', '2021-03')):
        ac.append(dict(sample=lab, acf1_month_end=float(r_me.loc[a:b].autocorr(1)),
                       acf1_month_average=float(r_avg.loc[a:b].autocorr(1)),
                       acf1_shiller_price=float(R_px.loc[a:b].autocorr(1)),
                       vol_month_end=float(r_me.loc[a:b].std() * np.sqrt(12)),
                       vol_month_average=float(r_avg.loc[a:b].std() * np.sqrt(12))))
    ac.append(dict(sample='S&P500 arch 1999-02..2018-12', acf1_month_end=float(r_me2.loc['1999-02':'2018-12'].autocorr(1)),
                   acf1_month_average=float(r_avg2.loc['1999-02':'2018-12'].autocorr(1)),
                   acf1_shiller_price=float(R_px.loc['1999-02':'2018-12'].autocorr(1)),
                   vol_month_end=float(r_me2.loc['1999-02':'2018-12'].std() * np.sqrt(12)),
                   vol_month_average=float(r_avg2.loc['1999-02':'2018-12'].std() * np.sqrt(12))))
    ac.append(dict(sample='Shiller 1872-2026 (price)', acf1_month_end=np.nan, acf1_month_average=np.nan,
                   acf1_shiller_price=float(R_px.loc['1872-02':'2026-09'].autocorr(1)), vol_month_end=np.nan,
                   vol_month_average=float(R_px.loc['1872-02':'2026-09'].std() * np.sqrt(12))))
    # signal agreement
    sm, sa = signals(me), signals(avg)
    for rn in ('SMA10', 'TSM12'):
        x = (sm[rn] == sa[rn]).loc[W_SPY[0]:W_SPY[1]]
        ac.append(dict(sample=f'signal agreement {rn} SPY month-end vs month-average', acf1_month_end=float(x.mean())))
    C.save_csv(pd.DataFrame(ac), 'r2_idx_averaging_autocorr.csv')
    # ---------------- E1: 12-month sign R/V on Shiller (signal on the average-price change, total-return P&L)
    e1 = []
    s12 = signals(P)['TSM12']
    for a, b in (('1927-01', '1991-12'), ('1992-01', '2014-12'), ('2015-01', '2026-09'), ('2015-01', '2021-03')):
        rr = (s12.shift(1) * R_tr).loc[a:b]
        st, sb = stats(rr), stats(R_tr.loc[a:b])
        e1.append(dict(source='Shiller avg (E1 method: TR P&L, flat = 0)', window=f'{a}..{b}',
                       rule_mean=st['mean_ann'], rule_vol=st['vol_ann'], rule_rv=st['sharpe'], rule_mdd=st['max_dd'],
                       bh_mean=sb['mean_ann'], bh_vol=sb['vol_ann'], bh_rv=sb['sharpe'], bh_mdd=sb['max_dd']))
    # month-end SPY 2015-01..2021-03: price only, and with a 1.8%/yr dividend accrual (flagged approximation)
    s12m = signals(me)['TSM12']
    for lab, ret in (('SPY month-end, price', r_me), ('SPY month-end, price + 1.8%/yr dividend accrual', r_me + 0.018 / 12),
                     ('SPY month-average, price', r_avg)):
        sig = s12m if 'month-end' in lab else signals(avg)['TSM12']
        rr = (sig.shift(1) * ret).loc['2015-01':'2021-03']
        st, sb = stats(rr), stats(ret.loc['2015-01':'2021-03'])
        e1.append(dict(source=lab, window='2015-01..2021-03', rule_mean=st['mean_ann'], rule_vol=st['vol_ann'],
                       rule_rv=st['sharpe'], rule_mdd=st['max_dd'], bh_mean=sb['mean_ann'], bh_vol=sb['vol_ann'],
                       bh_rv=sb['sharpe'], bh_mdd=sb['max_dd']))
    # the same rule on SPY month-end for the J.P. Morgan window's overlap 1999-2014
    for lab, ret, sig in (('SPY month-end, price', r_me, s12m), ('SPY month-average, price', r_avg, signals(avg)['TSM12'])):
        rr = (sig.shift(1) * ret).loc['1999-03':'2014-12']
        st, sb = stats(rr), stats(ret.loc['1999-03':'2014-12'])
        e1.append(dict(source=lab, window='1999-03..2014-12', rule_mean=st['mean_ann'], rule_vol=st['vol_ann'],
                       rule_rv=st['sharpe'], rule_mdd=st['max_dd'], bh_mean=sb['mean_ann'], bh_vol=sb['vol_ann'],
                       bh_rv=sb['sharpe'], bh_mdd=sb['max_dd']))
    rr = (s12.shift(1) * R_tr).loc['1999-03':'2014-12']
    st, sb = stats(rr), stats(R_tr.loc['1999-03':'2014-12'])
    e1.append(dict(source='Shiller avg (E1 method)', window='1999-03..2014-12', rule_mean=st['mean_ann'],
                   rule_vol=st['vol_ann'], rule_rv=st['sharpe'], rule_mdd=st['max_dd'], bh_mean=sb['mean_ann'],
                   bh_vol=sb['vol_ann'], bh_rv=sb['sharpe'], bh_mdd=sb['max_dd']))
    C.save_csv(pd.DataFrame(e1), 'r2_idx_e1_checks.csv')
    meta = pd.DataFrame([dict(item='shiller_last_dividend_month', value=last_div),
                         dict(item='spy_first', value=str(spy.index[0].date())), dict(item='spy_last', value=str(spy.index[-1].date())),
                         dict(item='arch_first', value=str(sp.index[0].date())), dict(item='arch_last', value=str(sp.index[-1].date()))])
    C.save_csv(meta, 'r2_idx_averaging_meta.csv')
    C.log('averaging done')


if __name__ == '__main__':
    main()
