"""kr_07_charts_summary.py -- chart-ready JSON (kr/charts/) and the markdown summary (kr/KR_datalab_summary.md).

Charts
 1 kr_chart1_cumlog_monthly.json  monthly cumulative log returns: long-only net 35 bp and long-short gross for
   MOM_12_1, REV_1M, HIGH52, VOL_3M, MAX_1M, PMA200, TURN_1M (low-turnover side) + EW universe (ALL, EW and VW).
 2 kr_chart2_sharpe_subperiods.json  Sharpe by sub-period per signal (LS gross, LO net35, LO excess net35).
 3 kr_chart3_kospi_timing.json  daily rebuilt KOSPI level, SMA200, equity curves of buy & hold, SMA200 rule and
   the best SPA-family rule (net 3 bp).
 4 kr_chart4_quintiles_2025_2026.json  2025-01-02..2026-09-29 daily cumulative returns of the five long-only
   quintiles (net 35 bp, ALL universe, EW) for the top 3 monthly signals by full-sample gross long-short Sharpe.
"""
import sys, time, json
import numpy as np
import pandas as pd
sys.path.insert(0, '/home/claude/datalab/scripts')
from kr_common import (CACHE, RES, CHARTS, ROOT, EVENT_WINDOWS, load_meta, clean_json, write_json)

CHART_SIGNALS = ['MOM_12_1', 'REV_1M', 'HIGH52', 'VOL_3M', 'MAX_1M', 'PMA200', 'TURN_1M_LOW']
KEY = ['MOM_12_1', 'MOM_6_1', 'REV_1M', 'HIGH52', 'VOL_3M', 'MAX_1M', 'TURN_1M_LOW', 'TURN_1M_HIGH', 'SIZE', 'PMA200',
       'RSI14_CON', 'RSI14_MOM', 'BBPCTB_CON', 'BBPCTB_MOM', 'REV_1W', 'REV_1W_VSlow', 'REV_1W_VSmid', 'REV_1W_VShigh']


def monthly_cumlog(d):
    d = d.dropna()
    m = np.log1p(d).groupby([d.index.year, d.index.month]).sum()
    idx = [f'{y}-{mo:02d}' for y, mo in m.index]
    return idx, np.cumsum(m.values)


def chart1(S):
    out = {'description': 'Monthly cumulative log returns (sum of daily log returns), ALL universe. '
                          'Long-only = best quintile net of 35 bp per side; long-short = best minus worst quintile, gross.',
           'units': 'cumulative log return', 'series': []}
    for wt in ('EW', 'VW'):
        for sig in CHART_SIGNALS:
            for leg, cl in (('LO', 'net35'), ('LS', 'gross')):
                col = f'{sig}|ALL|{wt}|{leg}|{cl}'
                x, y = monthly_cumlog(S[col])
                out['series'].append({'signal': sig, 'weighting': wt, 'leg': leg, 'cost_level': cl,
                                      'months': x, 'cumlog': np.round(y, 5)})
        col = f'UNIV|ALL|{wt}|LO|net35'
        x, y = monthly_cumlog(S[col])
        out['series'].append({'signal': 'UNIVERSE', 'weighting': wt, 'leg': 'LO', 'cost_level': 'net35',
                              'months': x, 'cumlog': np.round(y, 5)})
    write_json(clean_json(out), f'{CHARTS}/kr_chart1_cumlog_monthly.json')


def chart2(T):
    per = ['full', '1996-2005', '2006-2015', '2016-2026']
    out = {'description': 'Annualised Sharpe ratio by sub-period (periods assigned by first holding day; 2016-2026 '
                          'ends 2026-09-29).', 'periods': per, 'rows': []}
    x = T[(T.metric == 'sharpe') & (T.period.isin(per))]
    for (sig, u, wt, leg, cl), g in x.groupby(['signal', 'universe', 'weighting', 'leg', 'cost_level']):
        if leg not in ('LS', 'LO', 'LO_xs_UEW', 'LO_xs_UVW', 'LO_excl_worst_xs_UEW') or cl == 'net70':
            continue
        v = g.set_index('period')['value'].reindex(per)
        out['rows'].append({'signal': sig, 'universe': u, 'weighting': wt, 'leg': leg, 'cost_level': cl,
                            'sharpe': [None if not np.isfinite(a) else round(float(a), 4) for a in v.values]})
    write_json(clean_json(out), f'{CHARTS}/kr_chart2_sharpe_subperiods.json')


def chart3():
    c = pd.read_parquet(f'{CACHE}/index_curves.parquet')
    best = open(f'{CACHE}/index_best_rule.txt').read().strip()
    start = pd.Timestamp('1996-06-03')
    c = c[c.index >= start]
    eq = lambda r: np.round(np.cumprod(1 + np.nan_to_num(r.values)), 5)
    out = {'description': 'Rebuilt value-weighted KOSPI (all KOSPI common-share lines, price index, scaled to the '
                          'official 2,064.85 on 2007-10-31) with its 200-day SMA; equity curves start at 1 on '
                          '1996-06-03 (cash 0%, 3 bp per side).',
           'best_spa_rule': best, 'dates': [d.strftime('%Y-%m-%d') for d in c.index],
           'kospi_level': np.round(c['level'].values, 2), 'sma200': np.round(c['sma200'].values, 2),
           'equity_buy_and_hold': eq(c['ret_bh']), 'equity_sma200_net3': eq(c['ret_sma200_net3']),
           'equity_best_spa_rule_net3': eq(c['ret_best_spa_net3']),
           'position_best_spa_rule': c['pos_best_spa'].astype(int).values}
    write_json(clean_json(out), f'{CHARTS}/kr_chart3_kospi_timing.json')


def chart4(T, S, dates):
    x = T[(T.period == 'full') & (T.metric == 'sharpe') & (T.universe == 'ALL') & (T.weighting == 'EW') &
          (T.leg == 'LS') & (T.cost_level == 'gross') & (T.freq == 'monthly')]
    x = x[x.signal.isin(['MOM_12_1', 'MOM_6_1', 'REV_1M', 'HIGH52', 'VOL_3M', 'MAX_1M', 'TURN_1M_LOW', 'SIZE',
                         'PMA200', 'RSI14_CON', 'BBPCTB_CON'])]
    top = x.sort_values('value', ascending=False).signal.head(3).tolist()
    keymap = {'TURN_1M_LOW': 'TURN_1M', 'RSI14_CON': 'RSI14', 'BBPCTB_CON': 'BBPCTB'}
    lo = pd.Timestamp('2025-01-02')
    out = {'description': 'Daily cumulative return (start 0 at the 2024-12-30 close) of the five long-only quintile '
                          'portfolios, net of 35 bp per side, ALL universe, equal-weighted, monthly rebalance; top 3 '
                          'monthly signals by full-sample gross long-short Sharpe (ALL, EW; the same three lead at '
                          'net 35 bp). Q1 = lowest signal value (the long quintile for all three).',
           'top3': top, 'universe_ew': None, 'series': []}
    idx = S.index[S.index >= lo]
    out['dates'] = [d.strftime('%Y-%m-%d') for d in idx]
    u = S.loc[idx, 'UNIV|ALL|EW|LO|net35']
    out['universe_ew'] = np.round(np.cumprod(1 + u.values) - 1, 5)
    for sig in top:
        k = keymap.get(sig, sig)
        for q in range(1, 6):
            col = f'{k}|ALL|EW|Q{q}|net35'
            out['series'].append({'signal': sig, 'quintile': q,
                                  'cumret': np.round(np.cumprod(1 + S.loc[idx, col].values) - 1, 5)})
    write_json(clean_json(out), f'{CHARTS}/kr_chart4_quintiles_2025_2026.json')
    return top


# ------------------------------------------------------------------ summary markdown
def fmt(v, pct=False, d=2):
    if v is None or (isinstance(v, float) and not np.isfinite(v)):
        return 'n/a'
    return f'{v * 100:.{max(0, d - 1)}f}%' if pct else f'{v:.{d}f}'


def main():
    t0 = time.time()
    dates, _ = load_meta()
    T = pd.read_csv(f'{RES}/kr_signal_stats_long.csv')
    S = pd.read_parquet(f'{CACHE}/series_daily.parquet')
    chart1(S); chart2(T); chart3(); top = chart4(T, S, dates)
    print('charts written; top3 =', top, f'{time.time() - t0:.0f}s')


if __name__ == '__main__':
    main()
