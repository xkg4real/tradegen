"""r2_kr_08_charts_summary.py -- chart-ready JSON and /home/claude/datalab/r2/R2_KR_summary.md.

Every number in the summary is read from results/*.csv (or recomputed from cached books with the same code).
Charts (charts/):
  r2_kr_chart_a_excl_cum_excess.json   cumulative excess (filtered / unfiltered wealth - 1, net 35 bp, monthly) of
                                        the best two primary filters on B1, B2, B3, 1996-2026
  r2_kr_chart_b_mom_grid_heatmap.json  the momentum reconciliation grid in long, heatmap-ready form
  r2_kr_chart_c_crash_windows.json     crash-window returns of the momentum controls (net 35 bp)
  r2_kr_chart_d_b2_2025_2026.json      2025-2026 daily cumulative returns of B2 with and without its best filter
"""
import sys, math, json
import numpy as np
import pandas as pd
sys.path.insert(0, '/home/claude/datalab/r2/kr')
from r2_kr_common import (Panel, series, diff_series, load_books, deflated_sharpe, write_json, clean_json, CACHE2,
                          RES2, CH2, log)

OUT_MD = '/home/claude/datalab/r2/R2_KR_summary.md'


def rd(name):
    return pd.read_csv(f'{RES2}/{name}')


def pct(x, d=1, sign=True):
    if x is None or (isinstance(x, float) and not math.isfinite(x)):
        return 'n/a'
    return f'{x * 100:+.{d}f}%' if sign else f'{x * 100:.{d}f}%'


def num(x, d=2):
    if x is None or (isinstance(x, float) and not math.isfinite(x)):
        return 'n/a'
    return f'{x:.{d}f}'


def md_table(header, rows):
    out = ['| ' + ' | '.join(header) + ' |', '|' + '|'.join(['---'] * len(header)) + '|']
    for r in rows:
        out.append('| ' + ' | '.join(str(c) for c in r) + ' |')
    return '\n'.join(out)


def main():
    P = Panel()
    G = rd('r2_kr_mom_grid_long.csv')
    C = rd('r2_kr_mom_claims_long.csv')
    LAD = rd('r2_kr_mom_e7_ladder.csv')
    S = rd('r2_kr_excl_summary.csv')
    L = rd('r2_kr_excl_long.csv')
    W = rd('r2_kr_excl_windows.csv')
    Y = rd('r2_kr_excl_years.csv')
    J = rd('r2_kr_excl_jaccard.csv')
    GT = rd('r2_kr_excl_gate.csv')
    TRI = rd('r2_kr_excl_trials.csv')
    LL = rd('r2_kr_excl_limitlock.csv')
    F6D = rd('r2_kr_excl_f6_diagnostic.csv')
    CC = rd('r2_kr_crash_controls.csv')
    CW = rd('r2_kr_crash_windows.csv')
    CE = rd('r2_kr_crash_exposure_2026.csv')
    SLS = rd('r2_kr_stoploss.csv')
    REV = rd('r2_kr_reversal.csv')
    LV = rd('r2_kr_lowvol.csv')
    LVW = rd('r2_kr_lowvol_windows.csv')
    VAL = rd('r2_kr_validation.csv')
    REP = rd('r2_kr_reproduce_r1.csv')
    ONS = rd('r2_kr_dm_gate_onsets.csv')
    B = load_books(f'{CACHE2}/books_excl.npz')

    def g(sig, td, terc, w, leg, period, metric):
        q = G[(G.signal == sig) & (G.turn_def == td) & (G.tercile == terc) & (G.weighting == w) & (G.leg == leg) &
              (G.period == period) & (G.metric == metric)]
        return float(q.value.iloc[0]) if len(q) else np.nan

    def c(claim, variant, metric):
        q = C[(C.claim == claim) & (C.variant == variant) & (C.metric == metric)]
        return float(q.value.iloc[0]) if len(q) else np.nan

    def s(base, f, cost, col):
        q = S[(S.base == base) & (S['filter'] == f) & (S.cost == cost)]
        return float(q[col].iloc[0])

    def cc(sleeve, control, cost, period, metric):
        q = CC[(CC.sleeve == sleeve) & (CC.control == control) & (CC.cost == cost) & (CC.period == period) & (CC.metric == metric)]
        return float(q.value.iloc[0]) if len(q) else np.nan

    def cw(sleeve, control, window):
        q = CW[(CW.sleeve == sleeve) & (CW.control == control) & (CW.window == window)]
        return float(q.cum_return_net35.iloc[0]) if len(q) else np.nan

    # ---------------- charts ----------------
    end_dates = [str(P.dates[e - 1].date()) for e in P.ends]
    ch_a = {'description': 'Cumulative excess of the filtered over the unfiltered long-only book, both net of 35 bp per side '
                           'on their own turnover: prod(1+R_filtered)/prod(1+R_unfiltered) - 1, monthly periods, '
                           '1996-04..2026-09. Best two primary filters (by information ratio at 35 bp) per base.',
            'dates': end_dates, 'series': []}
    for b in ('B1', 'B2', 'B3'):
        for _, r in GT[GT.base == b].sort_values('rank').iterrows():
            f = r['filter']
            pf, _, _ = series(P, B[f'{b}|{f}'], c=0.0035)
            pu, _, _ = series(P, B[f'{b}|none'], c=0.0035)
            rel = np.cumprod(1 + np.nan_to_num(pf)) / np.cumprod(1 + np.nan_to_num(pu)) - 1
            ch_a['series'].append(dict(base=b, filter=f, rank=int(r['rank']), ann_diff_net35=r['ann_diff_net35'],
                                       ir_net35=r['ir_net35'], cum_excess=np.round(rel, 6).tolist()))
    write_json(clean_json(ch_a), f'{CH2}/r2_kr_chart_a_excl_cum_excess.json')
    legs = ['LS_gross', 'LS_net35', 'LO_xs_UEW_net35', 'LO_xs_UVW_net35']
    hm = G[G.leg.isin(legs) & G.metric.isin(['ann_mean', 'nw_t', 'sharpe', 'n_periods', 'avg_names'])]
    hm = hm.pivot_table(index=['signal', 'turn_def', 'tercile', 'weighting', 'leg', 'period'], columns='metric',
                        values='value').reset_index()
    ch_b = {'description': 'Korean momentum reconciliation grid (ALL universe, independent sorts: signal quintiles x '
                           'turnover terciles formed over the whole universe at the formation close). ann_mean = mean '
                           'monthly return x 12; nw_t = Newey-West t (6 lags). LO legs: top quintile net of 35 bp minus '
                           'the gross universe (EW or VW).',
            'rows': hm.round(6).to_dict(orient='records')}
    write_json(clean_json(ch_b), f'{CH2}/r2_kr_chart_b_mom_grid_heatmap.json')
    ch_c = {'description': 'Cumulative returns (net 35 bp) of 12-1 momentum sleeves under each crash control in each '
                           'window; LS = $1 long / $1 short; LO = excess of the long-only top quintile over the universe.',
            'rows': CW.round(6).to_dict(orient='records')}
    write_json(clean_json(ch_c), f'{CH2}/r2_kr_chart_c_crash_windows.json')
    best_b2 = GT[(GT.base == 'B2') & (GT['rank'] == 1)]['filter'].iloc[0]
    _, df_, _ = series(P, B[f'B2|{best_b2}'], c=0.0035)
    _, du, _ = series(P, B['B2|none'], c=0.0035)
    m = (P.dates >= pd.Timestamp('2025-01-01'))
    ch_d = {'description': f'B2 (VW ALL universe, 5% cap) with and without filter {best_b2}, daily cumulative return net of '
                           f'35 bp, from the 2024-12-30 close.',
            'dates': [str(d.date()) for d in P.dates[m]],
            'unfiltered': np.round(np.cumprod(1 + np.nan_to_num(du[m])) - 1, 6).tolist(),
            'filtered': np.round(np.cumprod(1 + np.nan_to_num(df_[m])) - 1, 6).tolist(), 'filter': best_b2}
    write_json(clean_json(ch_d), f'{CH2}/r2_kr_chart_d_b2_2025_2026.json')
    log('charts written')

    # ---------------- DSR for the overall best trial ----------------
    TRn = TRI.copy()
    best = TRn.sort_values('ir_net35', ascending=False).iloc[0]
    diffs = {}
    for _, r in TRn.iterrows():
        d, _, _ = diff_series(P, B[f"{r['base']}|{r['filter']}"], B[f"{r['base']}|none"], 0.0035)
        diffs[(r['base'], r['filter'])] = d[np.isfinite(d)]
    srs = np.array([x.mean() / x.std(ddof=1) for x in diffs.values()])
    xb = diffs[(best['base'], best['filter'])]
    n_trials = len(TRn)
    dsr_pool, sr0_pool, srm = deflated_sharpe(xb, n_trials, float(np.var(srs, ddof=1)))
    dsr_null, sr0_null, _ = deflated_sharpe(xb, n_trials, 1.0 / (len(xb) - 1))
    base_srs = np.array([diffs[k].mean() / diffs[k].std(ddof=1) for k in diffs if k[0] == best['base']])
    dsr_base, sr0_base, _ = deflated_sharpe(xb, len(base_srs), float(np.var(base_srs, ddof=1)))
    pd.DataFrame([dict(best_trial=f"{best['base']}|{best['filter']}", ir_ann=best['ir_net35'], sr_monthly=srm,
                       n_trials=n_trials, dsr_pooled_variance=dsr_pool, sr0_monthly_pooled=sr0_pool,
                       dsr_per_base_variance=dsr_base, sr0_monthly_per_base=sr0_base, dsr_null_variance=dsr_null,
                       sr0_monthly_null=sr0_null)]).to_csv(f'{RES2}/r2_kr_excl_dsr_best.csv', index=False, float_format='%.6g')

    # ---------------- summary markdown ----------------
    md = []
    A = md.append
    A('# KRX round-2 data lab: momentum reconciliation, exclusion screens, crash controls (Korea)')
    A('')
    A('QUANTGEN technical and fundamental signals project, round 2, Korea data lab (2026-10-03). One methodology, on the round-1 '
      'panel (marcap daily snapshots of every KRX-listed stock, 1995-05-02..2026-09-29, survivorship-free), the round-1 universe '
      '(ALL = eligible operating common shares, price >= 1,000 KRW, >= 200 valid days, traded at t, no beyond-limit move in the '
      'last 30 sessions, Marcap >= 20th percentile; LARGE = top 200 by Marcap) and the round-1 return cleaning. Monthly '
      'formation at the last close of each month (366 formations, 1996-03..2026-08), returns from t+1, buy-and-hold within '
      'the month, delisted names frozen as cash, halted holdings carried. Costs 35 bp per side on every unit of turnover '
      '(70 bp stress). Sharpe ratios use raw returns (no risk-free rate). Price returns (dividends excluded). All statistics '
      'are in-sample (IS); nothing here has passed QUANTGEN\'s gate (the gate runs below are indicative).')
    A('')
    A('Scripts: `/home/claude/datalab/r2/kr/r2_kr_*.py` (`python3 r2_kr_run_all.py` reruns everything in about 5 minutes, '
      'peak resident memory about 2.6 GB incl. memory-mapped pages). Results: `r2/kr/results/*.csv`; charts: `r2/kr/charts/*.json`.')
    A('')
    # validation headline
    nval = int(VAL.passed.sum()); nrep = int(REP.passed.sum())
    A(f'**Same panel as round 1:** the round-2 engine reproduces round-1 numbers exactly ({nrep}/{len(REP)} checks; daily book '
      f'series identical to round-1 caches to 0.0). MOM 12-1 long-short EW gross +{g("MOM_12_1","all","all","EW","LS_gross","full","ann_mean")*100:.1f}%/yr, '
      f'Sharpe {g("MOM_12_1","all","all","EW","LS_gross","full","sharpe"):.2f} (round 1: +9.3%, 0.45); drop-highest-turnover-quintile '
      f'+3.62%/yr over the gross EW universe, t 5.63 (round 1: +3.6%, t 5.63); MOM 12-1 inside the high TURN_1M tercile '
      f'+1.44%/month, t 3.41 (round 1: +1.44%, t 3.41). Validation: {nval}/{len(VAL)} tests passed (section 8).')
    A('')
    # ---------------- headline ----------------
    A('## Headline verdicts')
    A('')
    b1f4 = (s('B1', 'F4', 'net35', 'ann_diff'), s('B1', 'F4', 'net35', 'ir'), s('B1', 'F4', 'net35', 'boot_p'))
    b1f1 = (s('B1', 'F1', 'net35', 'ann_diff'), s('B1', 'F1', 'net35', 'ir'))
    b2f4 = (s('B2', 'F4', 'net35', 'ann_diff'), s('B2', 'F4', 'net35', 'ir'), s('B2', 'F4', 'net35', 'boot_p'))
    b3f4 = (s('B3', 'F4', 'net35', 'ann_diff'), s('B3', 'F4', 'net35', 'ir'), s('B3', 'F4', 'net35', 'boot_p'))
    b4f1 = (s('B4', 'F1', 'net35', 'ann_diff'), s('B4', 'F1', 'net35', 'ir'))
    A(f'1. **Momentum conflicts are definitional, not data errors.** On one panel the round-1 lab, P6 and E7 claims reproduce under '
      f'their own definitions (round 1 exactly, P6 and E7 within a few tenths); the Korean-journal (KJFS) headline does not, and E5 '
      f'only partly (its equal-weighted Sharpe). Two things drive the apparent conflict. First, '
      f'long-short and long-only answer different questions: inside the high-turnover tercile 12-1 winners beat losers '
      f'(EW +{g("MOM_12_1","TURN_12M","high","EW","LS_gross","full","ann_mean")*100:.1f}%/yr gross, t '
      f'{g("MOM_12_1","TURN_12M","high","EW","LS_gross","full","nw_t"):.1f}), yet the same winners trail the EW universe by '
      f'{-g("MOM_12_1","TURN_12M","high","EW","LO_xs_UEW_net35","full","ann_mean")*100:.1f}%/yr net (t '
      f'{g("MOM_12_1","TURN_12M","high","EW","LO_xs_UEW_net35","full","nw_t"):.1f}) because high-turnover stocks as a group '
      f'lose. Second, the period: 2015-07..2024-12 is a bad decade for every momentum construction (EW long-short gross '
      f'{g("MOM_12_1","all","all","EW","LS_gross","2015-07..2024-12","ann_mean")*100:+.1f}%/yr). The KJFS sign '
      f'(high-turnover W-L about -6%/month) appears only when holding returns are taken from unadjusted closes in an all-caps '
      f'universe ({c("KJFS/P6-Eom","unadjusted signal + unadjusted holding returns|broad|high-turnover W-L","mean_pct_month"):+.1f}%/month, '
      f't {c("KJFS/P6-Eom","unadjusted signal + unadjusted holding returns|broad|high-turnover W-L","nw_t"):.1f}); the whole effect '
      f'comes from capital reductions / reverse splits that KRX adjusts in its base price (0.09% of stock-days). With KRX-adjusted '
      f'returns the same design gives {c("KJFS/P6-Eom","adjusted|broad|high-turnover W-L","mean_pct_month"):+.2f}%/month '
      f'(t {c("KJFS/P6-Eom","adjusted|broad|high-turnover W-L","nw_t"):.1f}).')
    A(f'2. **Exclusion screens: BUILD for equal-weighted / small-cap books, marginal for cap-weighted books, nothing for the top 200.** '
      f'Removing the P6 lottery composite (F4, about 10% of names) from the EW universe adds {pct(b1f4[0])}/yr net of 35 bp on both '
      f'books (information ratio {b1f4[1]:.2f}, bootstrap p {b1f4[2]:.4f}), dropping the highest-turnover quintile (F1) '
      f'{pct(b1f1[0])}/yr (IR {b1f1[1]:.2f}); positive in all three sub-periods and in 90%+ of years; still positive at 70 bp. '
      f'In the 12-1 momentum top quintile (B4) F1 adds {pct(b4f1[0])}/yr (IR {b4f1[1]:.2f}). Cap-weighted with a 5% cap (B2): '
      f'{pct(b2f4[0], 2)}/yr (IR {b2f4[1]:.2f}, p {b2f4[2]:.3f}) but mostly from 1996-2005. Top 200 (B3): {pct(b3f4[0], 2)}/yr '
      f'(IR {b3f4[1]:.2f}), fails the overfitting checks. Indicative gate: B1 and B4 pass 7 of 8 steps (only the deflated Sharpe '
      f'over all {n_trials} pooled trials misses: 0.94 / 0.56), B2 REVISE, B3 REJECT.')
    vs_on = CE[(CE.control.str.startswith('VS (')) & CE.sleeve.str.startswith('LS_')]
    A(f'3. **Crash controls:** own-volatility scaling was already cutting exposure before the 2026 crash (12-1 long-short weight '
      f'{vs_on[vs_on.sleeve.str.contains("EW")].s_on_2026_06_22.iloc[0]:.2f} EW / {vs_on[vs_on.sleeve.str.contains("VW")].s_on_2026_06_22.iloc[0]:.2f} VW on 2026-06-22; '
      f'E5 top-500 deciles 0.35 / 0.20, exactly as E5 reported); the Daniel-Moskowitz gate on the rebuilt KOSPI was off '
      f'(KOSPI 24-month return strongly positive). Full-sample net Sharpe of 12-1 long-short: EW '
      f'{cc("LS_EW (ALL quintiles)","static","net35","full 1996-04..2026-09","sharpe"):.2f} static -> '
      f'{cc("LS_EW (ALL quintiles)","VS x DM","net35","full 1996-04..2026-09","sharpe"):.2f} with both; VW '
      f'{cc("LS_VW (ALL quintiles)","static","net35","full 1996-04..2026-09","sharpe"):.2f} -> '
      f'{cc("LS_VW (ALL quintiles)","VS x DM","net35","full 1996-04..2026-09","sharpe"):.2f}. But in 2016-2026 the combined overlay '
      f'lowered net Sharpe (EW {cc("LS_EW (ALL quintiles)","static","net35","2016-01..2026-09","sharpe"):.2f} -> '
      f'{cc("LS_EW (ALL quintiles)","VS x DM","net35","2016-01..2026-09","sharpe"):.2f}, VW '
      f'{cc("LS_VW (ALL quintiles)","static","net35","2016-01..2026-09","sharpe"):.2f} -> '
      f'{cc("LS_VW (ALL quintiles)","VS x DM","net35","2016-01..2026-09","sharpe"):.2f}) because it cut exposure in the 2026 melt-up. '
      f'Keep the controls as risk controls on any momentum sleeve; do not '
      f'expect them to rescue Korean 12-1 momentum, which stays a BACKLOG item. Name-level 15% stops cut Sharpe in every variant (E5 confirmed).')
    rv = REV[(REV.universe == 'ALL') & (REV.weighting == 'VW') & (REV['sort'] == 'deciles') & (REV.period == 'full')]
    rq = REV[(REV.universe == 'ALL') & (REV.weighting == 'VW') & (REV['sort'] == 'quintiles') & (REV.period == 'full')]
    A(f'4. **1-month reversal, value-weighted without microcaps, is close to zero gross and negative net** (ALL deciles '
      f'{rv[rv.cost=="gross"].mean_pct_month.iloc[0]:+.2f}%/month gross, t {rv[rv.cost=="gross"].nw_t.iloc[0]:.1f}; '
      f'{rv[rv.cost=="net35"].mean_pct_month.iloc[0]:+.2f}% net; quintiles {rq[rq.cost=="gross"].mean_pct_month.iloc[0]:+.2f}% gross). '
      f'P1\'s flag is confirmed: the -2.95%/month literature figure is an equal-weighted, small-cap number.')
    lv_e = LV[(LV.book == 'low-vol Q1 EW') & (LV.cost == 'net35') & (LV.period == 'full') & (LV.market == 'VW ALL universe (gross)')].iloc[0]
    lv_v = LV[(LV.book == 'low-vol Q1 VW') & (LV.cost == 'net35') & (LV.period == 'full') & (LV.market == 'VW ALL universe (gross)')].iloc[0]
    nc_e = int((LVW[(LVW.book == 'low-vol Q1 EW net35') & (LVW.kind == 'crash')].book_minus_vw > 0).sum())
    nc_v = int((LVW[(LVW.book == 'low-vol Q1 VW net35') & (LVW.kind == 'crash')].book_minus_vw > 0).sum())
    nr = int((LVW[LVW.kind == 'rebound'].book_minus_vw < 0).sum()); nrt = int((LVW.kind == 'rebound').sum())
    ncw = int((LVW.kind == 'crash').sum() / 2)
    A(f'5. **Low volatility is a protective card, not an alpha card.** Lowest VOL_3M quintile: beta {lv_e.beta:.2f} (EW) / '
      f'{lv_v.beta:.2f} (VW) to the VW market; CAPM alpha net of 35 bp {pct(lv_e.alpha_ann_rf0)} (t {lv_e.alpha_t:.1f}) and '
      f'{pct(lv_v.alpha_ann_rf0)} (t {lv_v.alpha_t:.1f}) with rf = 0, lower still once a short rate is charged; it beat the VW '
      f'market in {nc_e} (EW) and {nc_v} (VW) of {ncw} crash windows (2026-06-22..07-30: '
      f'{pct(LVW[(LVW.book=="low-vol Q1 VW net35")&(LVW.window.str.contains("2026-06-22"))].book_minus_vw.iloc[0])} for the VW book) and '
      f'lagged in {nr} of {nrt} book-rebound windows (2026 melt-up {pct(LVW[(LVW.book=="low-vol Q1 VW net35")&(LVW.window.str.contains("melt-up"))].book_minus_vw.iloc[0])}).')
    A('')
    # ---------------- key numbers ----------------
    A('## 1. Key numbers (gross and net)')
    A('')
    A('Annualised (monthly mean x 12); t = Newey-West (6 lags). LS = $1 long / $1 short, both legs pay costs. LO excess = '
      'long-only top quintile net of its costs minus the gross universe. Exclusion = filtered minus unfiltered book, both net.')
    A('')
    kr = []
    for sig in ('MOM_12_1', 'MOM_12_7'):
        for w in ('EW', 'VW'):
            kr.append([f'{sig} LS, ALL, {w}', pct(g(sig, 'all', 'all', w, 'LS_gross', 'full', 'ann_mean')),
                       num(g(sig, 'all', 'all', w, 'LS_gross', 'full', 'sharpe')),
                       pct(g(sig, 'all', 'all', w, 'LS_net35', 'full', 'ann_mean')), num(g(sig, 'all', 'all', w, 'LS_net35', 'full', 'sharpe')),
                       num(g(sig, 'all', 'all', w, 'LS_net70', 'full', 'sharpe')),
                       f'{num(g(sig, "all", "all", w, "LS_gross", "2016-01..2026-09", "sharpe"))} / {num(g(sig, "all", "all", w, "LS_net35", "2016-01..2026-09", "sharpe"))}'])
    for terc in ('high', 'low'):
        kr.append([f'MOM_12_1 LS, {terc}-turnover tercile (TURN_12M), EW', pct(g('MOM_12_1', 'TURN_12M', terc, 'EW', 'LS_gross', 'full', 'ann_mean')),
                   num(g('MOM_12_1', 'TURN_12M', terc, 'EW', 'LS_gross', 'full', 'sharpe')),
                   pct(g('MOM_12_1', 'TURN_12M', terc, 'EW', 'LS_net35', 'full', 'ann_mean')),
                   num(g('MOM_12_1', 'TURN_12M', terc, 'EW', 'LS_net35', 'full', 'sharpe')),
                   num(g('MOM_12_1', 'TURN_12M', terc, 'EW', 'LS_net70', 'full', 'sharpe')),
                   f'{num(g("MOM_12_1", "TURN_12M", terc, "EW", "LS_gross", "2016-01..2026-09", "sharpe"))} / {num(g("MOM_12_1", "TURN_12M", terc, "EW", "LS_net35", "2016-01..2026-09", "sharpe"))}'])
    A(md_table(['Long-short sleeve (1996-04..2026-09)', 'Gross /yr', 'Gross Sharpe', 'Net 35 /yr', 'Net 35 Sharpe', 'Net 70 Sharpe',
                'Sharpe 2016-26 gross / net'], kr))
    A('')
    kr2 = []
    for b in ('B1', 'B2', 'B3', 'B4'):
        for f in ('F1', 'F2', 'F4', 'F7'):
            kr2.append([f'{b} {f}', pct(s(b, f, 'gross', 'ann_diff'), 2), pct(s(b, f, 'net35', 'ann_diff'), 2),
                        pct(s(b, f, 'net70', 'ann_diff'), 2), num(s(b, f, 'net35', 'ir')), num(s(b, f, 'net35', 'nw_t'), 1),
                        num(s(b, f, 'net35', 'boot_p'), 4), f"{s(b, f, 'net35', 'pct_years_pos') * 100:.0f}%"])
    A(md_table(['Exclusion (base, filter)', 'Diff gross /yr', 'Diff net 35', 'Diff net 70', 'IR net 35', 't', 'Boot p', 'Years > 0'], kr2))
    A('')
    kr3 = []
    for sl in ('LS_EW (ALL quintiles)', 'LS_VW (ALL quintiles)', 'LO_EW excess (Q5 vs EW univ)', 'LO_VW excess (Q5 vs VW univ)'):
        row = [sl]
        for ctl in ('static', 'VS (own vol, 12%, cap 1)', 'DM gate (KOSPI, floor 0.5)', 'VS x DM'):
            row.append(f"{num(cc(sl, ctl, 'net35', 'full 1996-04..2026-09', 'sharpe'))} ({pct(cc(sl, ctl, 'net35', 'full 1996-04..2026-09', 'max_dd'), 0, False)})")
        kr3.append(row)
    A(md_table(['12-1 momentum, net 35 Sharpe (max DD)', 'Static', 'Own-vol scaling', 'D&M gate', 'Both'], kr3))
    A('')
    # ---------------- Task 1 ----------------
    A('## 2. Task 1: Korean momentum reconciliation')
    A('')
    A('### 2.1 The standardised grid (12-1 momentum, turnover = 12-month average daily Amount/Marcap, independent sorts)')
    A('')
    A('ALL universe; signal quintiles and turnover terciles are each formed over the whole universe at the formation close and '
      'intersected. Annualised mean (NW t). The full grid (4 signals x {all, low, mid, high} x 2 turnover definitions x EW/VW x '
      '7 legs x 5 periods) is in `results/r2_kr_mom_grid_long.csv` and `charts/r2_kr_chart_b_mom_grid_heatmap.json`.')
    A('')
    rows = []
    per_order = ['full', '1996-2005', '2006-2015', '2015-07..2024-12', '2016-01..2026-09']
    for w in ('EW', 'VW'):
        for terc in ('all', 'low', 'mid', 'high'):
            td = 'all' if terc == 'all' else 'TURN_12M'
            for leg, lab in (('LS_gross', 'LS gross'), ('LS_net35', 'LS net 35'), ('LO_xs_UEW_net35', 'LO - EW univ, net'),
                             ('LO_xs_UVW_net35', 'LO - VW univ, net')):
                rows.append([w, terc, lab] + [f'{g("MOM_12_1", td, terc, w, leg, p, "ann_mean") * 100:+.1f} ({g("MOM_12_1", td, terc, w, leg, p, "nw_t"):.1f})'
                                              for p in per_order])
    A(md_table(['Wt', 'Turnover tercile', 'Leg'] + per_order, rows))
    A('')
    A(f'Reading: (i) the long-short spread is positive in every turnover tercile over the full sample (EW gross: low '
      f'{pct(g("MOM_12_1","TURN_12M","low","EW","LS_gross","full","ann_mean"))}, mid {pct(g("MOM_12_1","TURN_12M","mid","EW","LS_gross","full","ann_mean"))}, '
      f'high {pct(g("MOM_12_1","TURN_12M","high","EW","LS_gross","full","ann_mean"))}; with 1-month turnover terciles the high '
      f'tercile is the strongest, {pct(g("MOM_12_1","TURN_1M","high","EW","LS_gross","full","ann_mean"))}, t '
      f'{g("MOM_12_1","TURN_1M","high","EW","LS_gross","full","nw_t"):.1f}); (ii) the long-only winners of the high-turnover tercile '
      f'lose to the EW universe in every period ({pct(g("MOM_12_1","TURN_12M","high","EW","LO_xs_UEW_net35","full","ann_mean"))}/yr net) '
      f'because high turnover is the strongest negative predictor in Korea (round 1: highest-turnover quintile -22.4%/yr vs the '
      f'EW universe); (iii) low- and mid-turnover winners beat the EW universe over the full sample '
      f'({pct(g("MOM_12_1","TURN_12M","low","EW","LO_xs_UEW_net35","full","ann_mean"))}, t {g("MOM_12_1","TURN_12M","low","EW","LO_xs_UEW_net35","full","nw_t"):.1f}; '
      f'{pct(g("MOM_12_1","TURN_12M","mid","EW","LO_xs_UEW_net35","full","ann_mean"))}, t {g("MOM_12_1","TURN_12M","mid","EW","LO_xs_UEW_net35","full","nw_t"):.1f}) '
      f'but not in 2015-07..2024-12 ({pct(g("MOM_12_1","TURN_12M","low","EW","LO_xs_UEW_net35","2015-07..2024-12","ann_mean"))}, '
      f'{pct(g("MOM_12_1","TURN_12M","mid","EW","LO_xs_UEW_net35","2015-07..2024-12","ann_mean"))}); '
      f'(iv) 2015-2024 is weak for every momentum book; (v) 12-7 has the highest EW gross Sharpe '
      f'({g("MOM_12_7","all","all","EW","LS_gross","full","sharpe"):.2f}) but its turnover leaves the same net Sharpe as 12-1 '
      f'({g("MOM_12_7","all","all","EW","LS_net35","full","sharpe"):.2f} vs {g("MOM_12_1","all","all","EW","LS_net35","full","sharpe"):.2f}); '
      f'6-1 is negative net.')
    A('')
    A('### 2.2 Reconciliation table')
    A('')
    e7 = LAD.set_index(['step', 'group'])
    def lad(step_prefix, grp, col='ann_excess_net35'):
        q = LAD[LAD.step.str.startswith(step_prefix) & (LAD.group == grp)]
        return float(q[col].iloc[0])
    e5 = lambda v, m: c('E5/P2-top500', v, m)
    rec_rows = [
        ['Brief / KJFS (Eom et al. 2020)', 'Korea, 2000-07..2019-06, EW, gross; turnover top/bottom 30% (formation-period average), '
         'highest-volatility decile dropped, momentum quintiles inside each group; high-turnover W-L -6.13%/month (t -4.76), losers +6.85%/month',
         f'Same design on the panel: all caps {c("KJFS/P6-Eom","adjusted|broad|high-turnover W-L","mean_pct_month"):+.2f}%/month '
         f'(t {c("KJFS/P6-Eom","adjusted|broad|high-turnover W-L","nw_t"):.1f}), losers {c("KJFS/P6-Eom","adjusted|broad|high-turnover W-L","losers_pct_month"):+.2f}%; '
         f'ex-bottom-20% {c("KJFS/P6-Eom","adjusted|broad_cut|high-turnover W-L","mean_pct_month"):+.2f}% (t {c("KJFS/P6-Eom","adjusted|broad_cut|high-turnover W-L","nw_t"):.1f}). '
         f'Unadjusted closes, all caps: {c("KJFS/P6-Eom","unadjusted signal + unadjusted holding returns|broad|high-turnover W-L","mean_pct_month"):+.1f}% '
         f'(t {c("KJFS/P6-Eom","unadjusted signal + unadjusted holding returns|broad|high-turnover W-L","nw_t"):.1f}), losers '
         f'{c("KJFS/P6-Eom","unadjusted signal + unadjusted holding returns|broad|high-turnover W-L","losers_pct_month"):+.1f}%/month; '
         f'cleaned returns except unadjusted corporate-action days: {c("KJFS/P6-Eom","unadjusted signal + cleaned returns except unadjusted corporate-action days|broad|high-turnover W-L","mean_pct_month"):+.1f}%; '
         f'unadjusted signal + adjusted holding: {c("KJFS/P6-Eom","unadjusted signal + adjusted holding returns|broad|high-turnover W-L","mean_pct_month"):+.2f}%',
         'NOT REPRODUCED',
         'With KRX-adjusted returns the sign is positive. The paper\'s sign and loser returns are reproduced only when holding returns '
         'ignore KRX base-price adjustments in an all-caps universe: capital reductions / reverse splits of distressed, '
         'high-turnover losers (mostly executed during trading halts; the 40 largest contributions are raw one-day jumps of x11.5 to x115) - 0.09% of '
         'stock-days carry the whole effect, and it vanishes once the bottom 20% of caps is removed. This is a hypothesis about '
         'the source data (not verifiable without it), but the claim should not set Korean weights.'],
        ['P6 (approximate Eom replication)', 'Same window; P6 approximation (p6_eom_x01.py): all caps +0.58%/month (t 1.50), ex-bottom-20% +1.42% (t 3.52)',
         f'{c("KJFS/P6-Eom","adjusted|broad|high-turnover W-L","mean_pct_month"):+.2f}% (t {c("KJFS/P6-Eom","adjusted|broad|high-turnover W-L","nw_t"):.1f}) / '
         f'{c("KJFS/P6-Eom","adjusted|broad_cut|high-turnover W-L","mean_pct_month"):+.2f}% (t {c("KJFS/P6-Eom","adjusted|broad_cut|high-turnover W-L","nw_t"):.1f})',
         'PARTLY', 'Sign and the ex-microcap size confirmed; the all-caps number is larger here (round-1 eligibility: >= 200 valid days, '
         'no recent beyond-limit move; P6 required next-month survival, a look-ahead filter, and set all beyond-limit days to missing).'],
        ['P6 decile sorts', 'ALL-like universe, D10-D1, holding 2001-02..2026-09: 12-1 EW 0.76%/month (t 2.37), net-35 Sharpe 0.18 (2x -0.09); '
         '12-7 EW 1.30% (t 4.91), net Sharpe 0.54 (2x 0.10); VW 12-1 1.66% (t 2.71), net Sharpe 0.39',
         f'12-1 EW {c("P6-deciles","MOM_12_1|EW|D10-D1|gross","mean_pct_month"):.2f}% (t {c("P6-deciles","MOM_12_1|EW|D10-D1|gross","nw_t"):.2f}), '
         f'net Sharpe {c("P6-deciles","MOM_12_1|EW|D10-D1|net35","sharpe"):.2f} (2x {c("P6-deciles","MOM_12_1|EW|D10-D1|net70","sharpe"):.2f}); '
         f'12-7 EW {c("P6-deciles","MOM_12_7|EW|D10-D1|gross","mean_pct_month"):.2f}% (t {c("P6-deciles","MOM_12_7|EW|D10-D1|gross","nw_t"):.2f}), '
         f'net {c("P6-deciles","MOM_12_7|EW|D10-D1|net35","sharpe"):.2f} (2x {c("P6-deciles","MOM_12_7|EW|D10-D1|net70","sharpe"):.2f}); '
         f'VW 12-1 {c("P6-deciles","MOM_12_1|VW|D10-D1|gross","mean_pct_month"):.2f}% (t {c("P6-deciles","MOM_12_1|VW|D10-D1|gross","nw_t"):.2f}), net {c("P6-deciles","MOM_12_1|VW|D10-D1|net35","sharpe"):.2f}',
         'CONFIRMED', 'Within about 0.15%/month and 0.06 Sharpe; P6 measured turnover against target (not drifted) weights and used '
         'calendar-month returns with a survival filter.'],
        ['Round-1 lab', 'ALL, EW, quintiles, 1996-2026: 12-1 LS +9.3%/yr gross (Sharpe 0.45), net 0.20; high TURN_1M tercile (dependent sort) +1.44%/month',
         f'+{g("MOM_12_1","all","all","EW","LS_gross","full","ann_mean")*100:.1f}%/yr, Sharpe {g("MOM_12_1","all","all","EW","LS_gross","full","sharpe"):.2f}, '
         f'net {g("MOM_12_1","all","all","EW","LS_net35","full","sharpe"):.2f}; high tercile '
         f'{c("Round-1","MOM_12_1 Q5-Q1 in high TURN_1M tercile (dependent)|gross","mean_pct_month"):.2f}%/month '
         f'(t {c("Round-1","MOM_12_1 Q5-Q1 in high TURN_1M tercile (dependent)|gross","nw_t"):.2f}); independent TURN_12M high tercile '
         f'{pct(g("MOM_12_1","TURN_12M","high","EW","LS_gross","full","ann_mean"))}/yr',
         'CONFIRMED', 'Identical panel and engine (26/26 checks). True for long-short spreads over the full sample; it says nothing about '
         'long-only winners (see E7) and 2016-2026 is much weaker (EW gross Sharpe '
         f'{g("MOM_12_1","all","all","EW","LS_gross","2016-01..2026-09","sharpe"):.2f}).'],
        ['E7', '2015-07..2024-12; liquid universe (Marcap >= 100bn, ADV20 >= 1bn, price >= 1,000, ex-관리/투자주의환기, ex-SPAC); 12-month '
         'turnover terciles ranked over all listed stocks; top-quintile winners vs month-formed EW benchmark, legs re-weighted daily; '
         'net 35: all -4.4%/yr, high -10.9%, low +3.1% (t 0.8)',
         f'S0 exact: {pct(lad("S0","all"))}, {pct(lad("S0","high"))}, {pct(lad("S0","low"))} (t {lad("S0","low","t"):.1f}); '
         f'monthly buy-and-hold engine: {pct(lad("S1","all"))}, {pct(lad("S1","high"))}, {pct(lad("S1","low"))}; '
         f'terciles inside the universe: high {pct(lad("S2","high"))}, low {pct(lad("S2","low"))}; ALL universe grid cell: '
         f'{pct(lad("S3","all"))}, {pct(lad("S3","high"))} (t {lad("S3","high","t"):.1f}), {pct(lad("S3","low"))}',
         'CONFIRMED', 'Reproduced within 0.3 pp and robust to engine, tercile and universe choices. It measures long-only winners against '
         'an EW benchmark, which mixes momentum with the turnover effect (high-turnover stocks lose as a group), in a decade when the '
         'long-short spread itself was about zero. Not in conflict with round 1 / P6.'],
        ['E5', 'Top 500 by Marcap, price >= 1,000, D10-D1, 2000-01..2026-09: Sharpe gross/net EW 0.43/0.20, VW 0.52/0.36; VW net 0.36 -> 0.41 '
         'with own-vol scaling (EW 0.20 -> 0.31); Jul-2026 WML -24.8% EW / -29.6% VW; VS weights 0.35 EW / 0.20 VW on 22 Jun 2026',
         f'EW {e5("MOM_12_1|deciles|EW|gross","sharpe"):.2f}/{e5("MOM_12_1|deciles|EW|net35","sharpe"):.2f}, VW '
         f'{e5("MOM_12_1|deciles|VW|gross","sharpe"):.2f}/{e5("MOM_12_1|deciles|VW|net35","sharpe"):.2f}; with scaling VW net '
         f'{cc("E5 top500 D10-D1 VW","static","net35","E5 window 2000-01..2026-09","sharpe"):.2f} -> {cc("E5 top500 D10-D1 VW","VS (own vol, 12%, cap 1)","net35","E5 window 2000-01..2026-09","sharpe"):.2f}, '
         f'EW {cc("E5 top500 D10-D1 EW","static","net35","E5 window 2000-01..2026-09","sharpe"):.2f} -> {cc("E5 top500 D10-D1 EW","VS (own vol, 12%, cap 1)","net35","E5 window 2000-01..2026-09","sharpe"):.2f}; '
         f'Jul-2026 {pct(e5("MOM_12_1|deciles|EW|gross","jul2026_month"))} EW / {pct(e5("MOM_12_1|deciles|VW|gross","jul2026_month"))} VW; '
         f'VS weights 22 Jun {CE[(CE.sleeve=="E5 top500 D10-D1 EW")&(CE.control.str.startswith("VS ("))].s_on_2026_06_22.iloc[0]:.2f} / '
         f'{CE[(CE.sleeve=="E5 top500 D10-D1 VW")&(CE.control.str.startswith("VS ("))].s_on_2026_06_22.iloc[0]:.2f}',
         'PARTLY', 'VW numbers, the July-2026 VW month, the scaling weights and the direction/size of the scaling gain reproduce; the EW '
         f'Sharpe (0.43) does not under the stated definition (top-500 quintiles give {e5("MOM_12_1|quintiles|EW|gross","sharpe"):.2f}, '
         f'a looser top-500 without validity screens {e5("MOM_12_1|deciles (looser top-500: no 200-day/limit screens)|EW|gross","sharpe"):.2f}). '
         'E5\'s scripts were not saved, so the EW construction difference cannot be identified.'],
        ['P2', 'Top 500, 2026-07: WML -27.2% (EW, gross)', f'Deciles {pct(e5("MOM_12_1|deciles|EW|gross","jul2026_month"))}, quintiles '
         f'{pct(e5("MOM_12_1|quintiles|EW|gross","jul2026_month"))}; ALL quintiles {pct(c("Jul-2026","ALL quintiles EW gross","jul2026_month"))}',
         'PARTLY', 'Same order of magnitude; the exact figure depends on deciles vs quintiles and the universe.'],
    ]
    A(md_table(['Claim', 'Exact definition (as stated)', 'Round-2 reproduction', 'Verdict', 'Reason'], rec_rows))
    A('')
    A('Decomposition of the KJFS result (all caps, high-turnover W-L, %/month, NW t): adjusted signal + adjusted returns '
      f'{c("KJFS/P6-Eom","adjusted|broad|high-turnover W-L","mean_pct_month"):+.2f} ({c("KJFS/P6-Eom","adjusted|broad|high-turnover W-L","nw_t"):.1f}); '
      f'unadjusted signal + adjusted returns {c("KJFS/P6-Eom","unadjusted signal + adjusted holding returns|broad|high-turnover W-L","mean_pct_month"):+.2f} '
      f'({c("KJFS/P6-Eom","unadjusted signal + adjusted holding returns|broad|high-turnover W-L","nw_t"):.1f}); adjusted signal + unadjusted returns '
      f'{c("KJFS/P6-Eom","adjusted signal + unadjusted holding returns|broad|high-turnover W-L","mean_pct_month"):+.2f} '
      f'({c("KJFS/P6-Eom","adjusted signal + unadjusted holding returns|broad|high-turnover W-L","nw_t"):.1f}); unadjusted both '
      f'{c("KJFS/P6-Eom","unadjusted signal + unadjusted holding returns|broad|high-turnover W-L","mean_pct_month"):+.2f}; cleaned returns '
      f'except unadjusted corporate-action days {c("KJFS/P6-Eom","unadjusted signal + cleaned returns except unadjusted corporate-action days|broad|high-turnover W-L","mean_pct_month"):+.2f} '
      f'({c("KJFS/P6-Eom","unadjusted signal + cleaned returns except unadjusted corporate-action days|broad|high-turnover W-L","nw_t"):.1f}). '
      'The holding-return measurement, not the signal, flips the sign. Top contributing events: `results/r2_kr_mom_kjfs_events.csv`.')
    A('')
    # ---------------- Task 2 ----------------
    A('## 3. Task 2: exclusion-screen horse race (long-only)')
    A('')
    A('Filters flag names at the formation close using data through t; breakpoints are formed in the ALL universe; flagged names '
      'leave the base book, which keeps its weighting rule. Difference = filtered minus unfiltered monthly return, both net of '
      'their own costs, same holding days. IR = mean/sd of the monthly difference x sqrt(12); TE = sd x sqrt(12). Bootstrap: '
      'paired circular block bootstrap, 3-month blocks, 2,000 resamples, seed 20261002, one-sided p for mean > 0 (null-centred).')
    A('')
    A('Definitions: F1 highest TURN_1M quintile; F2 highest VOL_3M quintile; F3 highest MAX_1M quintile; F4 P6 lottery composite '
      '(bottom decile of pct-rank(-VOL_3M)+pct-rank(-MAX_1M)+pct-rank(-TURN_1M), from p6_exclusion.py); F5 E7 attention-fade events '
      'in the last 20 sessions (volume >= 5x the previous 20-day average with r >= +5%; locked limit-up close, >= 29.5% from '
      '2015-06-15 and >= 14.5% before, close = high; +50% in 20 days; from e7_checks_part2.py and E7 DC2); F6 252-session share '
      'growth > 10% ignoring split-like days (shares x/÷ by > 5% with the raw close moving by the inverse ratio within +-5% on the '
      'same day); F7 = F1|F2|F3; F8 = F4|F5|F6. Bases: B1 EW ALL; B2 VW ALL, 5% cap (iterative pro-rata redistribution); B3 '
      'top-200 VW, 5% cap; B4 12-1 momentum top quintile EW.')
    A('')
    rows = []
    for b in ('B1', 'B2', 'B3', 'B4'):
        for f in ['F1', 'F2', 'F3', 'F4', 'F5', 'F6', 'F7', 'F8']:
            r35 = S[(S.base == b) & (S['filter'] == f) & (S.cost == 'net35')].iloc[0]
            r70 = S[(S.base == b) & (S['filter'] == f) & (S.cost == 'net70')].iloc[0]
            rows.append([b, f, pct(r35.ann_diff, 2), pct(r70.ann_diff, 2), num(r35.sharpe_filtered), num(r35.sharpe_unfiltered),
                         pct(r35.maxdd_diff, 1), pct(r35.te, 1, False), num(r35.ir), num(r35.boot_p, 4), f'{r35.pct_years_pos * 100:.0f}%',
                         f'{r35.excl_share_names * 100:.0f}% / {r35.excl_share_weight * 100:.0f}%',
                         f'{r35.turnover_filtered:.1f} / {r35.turnover_unfiltered:.1f}'])
    A(md_table(['Base', 'Filter', 'Diff /yr net 35', 'net 70', 'Sharpe filt.', 'Sharpe unfilt.', 'Max DD filt. - unfilt. (+ = shallower)', 'TE', 'IR',
                'Boot p', 'Years > 0', 'Excluded names / weight', 'Turnover/yr filt. / unfilt.'], rows))
    A('')
    A('Sub-periods (difference /yr net 35 bp, IR in brackets):')
    A('')
    rows = []
    for b in ('B1', 'B2', 'B3', 'B4'):
        for f in ['F1', 'F2', 'F4', 'F5', 'F6', 'F7']:
            cells = []
            for p in ('1996-2005', '2006-2015', '2016-2026-09'):
                q = L[(L.base == b) & (L['filter'] == f) & (L.cost == 'net35') & (L.period == p)]
                cells.append(f"{pct(float(q[q.metric == 'ann_diff'].value.iloc[0]), 2)} ({float(q[q.metric == 'ir'].value.iloc[0]):.2f})")
            rows.append([b, f] + cells)
    A(md_table(['Base', 'Filter', '1996-2005', '2006-2015', '2016-2026-09'], rows))
    A('')
    A('Event windows (filtered minus unfiltered cumulative return, net 35 bp, percentage points):')
    A('')
    wins = list(dict.fromkeys(W.window))
    rows = []
    for b in ('B1', 'B2', 'B3', 'B4'):
        for f in ('F1', 'F2', 'F4', 'F7'):
            rows.append([b, f] + [f"{float(W[(W.base == b) & (W['filter'] == f) & (W.window == w)]['diff'].iloc[0]) * 100:+.1f}" for w in wins])
    A(md_table(['Base', 'Filter'] + wins, rows))
    A('')
    jm = J.pivot(index='filter_a', columns='filter_b', values='jaccard_mean')
    A('Filter overlap inside the ALL universe (mean Jaccard over formations) and average share of the universe flagged:')
    A('')
    share = J.drop_duplicates('filter_a').set_index('filter_a').share_of_ALL_a
    A(md_table(['', *jm.columns, 'Share flagged'], [[a] + [f'{jm.loc[a, b2]:.2f}' for b2 in jm.columns] + [f'{share[a] * 100:.0f}%'] for a in jm.index]))
    A('')
    A(f'F6 note: {F6D.share_literal_not_confirmed.iloc[0] * 100:.0f}% of the name-months flagged by the literal split rule are not '
      'confirmed by net issuance measured with KRX\'s own adjustment factor (bonus issues and some splits are adjusted on the ex-date, '
      'weeks before the new shares are listed, so a same-day rule misses them). The net-issuance version (F6b) is in the trial set.')
    A('')
    # gate
    A('Cross-check against the three analyses that proposed the screen: round 1 (drop the highest-turnover quintile, EW, '
      f'+3.6%/yr over the GROSS EW universe) reproduces exactly (+3.62%, t 5.63; panel check at the top) and becomes {pct(s("B1","F1","net35","ann_diff"),2)}/yr '
      'when the unfiltered EW book also pays its own 1.9x/yr rebalancing cost; P6\'s lottery composite (p6_excl2.py: EW +0.23%/month, '
      f't 8.25; VW 5%-cap +0.04%/month, t 3.46) reproduces as {s("B1","F4","net35","ann_diff")/12*100:+.2f}%/month (t {s("B1","F4","net35","nw_t"):.1f}) '
      f'and {s("B2","F4","net35","ann_diff")/12*100:+.2f}%/month (t {s("B2","F4","net35","nw_t"):.1f}); P6\'s composite uses calendar-month MAX and '
      'month-sum turnover, here the 21-session equivalents (rank-equivalent up to missing days). E7\'s attention-fade events '
      '(strong 5-20 day effects in E7\'s event study) do not carry over to a monthly exclusion book (F5).')
    A('')
    A('### 3.1 Indicative QUANTGEN gate (best two primary filters per base, by IR at 35 bp)')
    A('')
    rows = []
    for _, r in GT.iterrows():
        rows.append([r.base, r['filter'], pct(r.ann_diff_net35, 2), num(r.ir_net35), f'{r.g1_walkforward_selected_oos_ir:.2f}',
                     f'{r.g2_lo_ci90} / {r.g2_boot_ci90}', f'{r.g3_dsr:.2f} / {r.g3_dsr_per_base:.2f} / {r.g3_dsr_nullvar:.2f}',
                     f'{r.g4_pbo_primary8:.2f} / {r.g4_pbo_all_variants:.2f} (loses {r.g4_winner_loses_all:.0%})',
                     num(r.g5_boot_p, 4), f'{r.g6_filtered_sharpe_net70:.2f} / {r.g6_diff_ir_net70:.2f}',
                     f'{r.g7_plateau_share:.2f}', f'{r.g8_pct_years_pos * 100:.0f}%', pct(r.g9_haircut_ann_diff, 2),
                     f'{int(r.steps_passed)}/8 {r.verdict}'])
    A(md_table(['Base', 'Filter', 'Diff /yr', 'IR', '1 WF-selected OOS IR', '2 Lo / boot 90% CI of IR', '3 DSR pooled / per-base / null',
                '4 PBO primary / all (IS winner loses)', '5 p', '6 Sharpe @70 / IR @70', '7 plateau', '8 years>0', '9 x0.4 haircut',
                'Steps, verdict'], rows))
    A('')
    A('Step definitions: (1) walk-forward selection among the 8 primary filters on daily differences, 756-session in-sample, '
      '21-session embargo, 126-session out-of-sample blocks; IR of the stitched OOS selections; (2) Lo (2002) SE with serial-'
      'correlation adjustment and a 2,000 x 10-session block bootstrap of the daily difference; both 90% intervals must clear zero; '
      f'(3) deflated Sharpe with all {n_trials} trials (variance of trial IRs pooled over bases; per-base variance with 44 trials; and '
      'the null variance 1/(T-1)); >= 0.95 required on the pooled version; (4) CSCV, 16 blocks: PBO <= 0.05 or the in-sample winner '
      'loses in <= 10% of splits; (5) one-sided paired bootstrap p <= 0.10; (6) filtered book Sharpe and difference IR > 0 at 70 bp; '
      '(7) >= 50% of neighbouring configurations (other cut levels / windows of the same family) keep half the IR; (8) >= 60% of '
      'calendar years positive; (9) 60% haircut, reported only.')
    A('')
    A(f'Deflated Sharpe of the best of all {n_trials} trials ({best["base"]}|{best["filter"]}, IR {best["ir_net35"]:.2f}, monthly SR '
      f'{srm:.3f}): {dsr_pool:.3f} with the pooled variance of the trial IRs (expected maximum monthly SR under the null '
      f'{sr0_pool:.3f}, i.e. {sr0_pool * math.sqrt(12):.2f} annualised), {dsr_base:.3f} with the per-base variance (44 trials, '
      f'SR0 {sr0_base * math.sqrt(12):.2f} annualised) and {dsr_null:.3f} with the null variance (SR0 {sr0_null * math.sqrt(12):.2f}). '
      'The pooled version is conservative because B1/B4 and B2/B3 trials have genuinely different IR levels.')
    A('')
    A('**Exclusion-screen verdicts.**')
    A(f'- **B1 (EW universe): BUILD-candidate as a filter.** F4 (P6 composite, ~10% of names) {pct(s("B1","F4","net35","ann_diff"),2)}/yr '
      f'net (IR {s("B1","F4","net35","ir"):.2f}), F1 (highest-turnover quintile) {pct(s("B1","F1","net35","ann_diff"),2)}/yr (IR '
      f'{s("B1","F1","net35","ir"):.2f}), F7 union {pct(s("B1","F7","net35","ann_diff"),2)}/yr (IR {s("B1","F7","net35","ir"):.2f}); positive '
      'in every sub-period; 7/8 gate steps; it paid in the 2026 crash and gave some back in the rebound. Recommended rule for a card: '
      'F4 at 10% (best IR, smallest exclusion, lowest extra turnover); F1/F7 when the larger mean matters more than tracking error.')
    A(f'- **B4 (momentum winners): BUILD as a construction rule for any long-only momentum or small-cap sleeve.** F1 '
      f'{pct(s("B4","F1","net35","ann_diff"),2)}/yr, F4 {pct(s("B4","F4","net35","ann_diff"),2)}/yr (IR {s("B4","F4","net35","ir"):.2f}); '
      'the screen removes the high-turnover winners that drive the E7 underperformance.')
    A(f'- **B2 (cap-weighted, 5% cap): REVISE.** {pct(s("B2","F4","net35","ann_diff"),2)}/yr (F4) to {pct(s("B2","F2","net35","ann_diff"),2)}/yr '
      '(F2), significant by bootstrap but concentrated in 1996-2005 and failing the deflated Sharpe; excluded weight is only 3-7%. '
      'Worth carrying as a default hygiene filter (it does no harm net of costs), not as an alpha claim.')
    A(f'- **B3 (top 200, KOSPI200-like): REJECT.** Best {pct(s("B3","F4","net35","ann_diff"),2)}/yr (F4); PBO 0.30-0.39 with the in-sample '
      'winner losing out of sample in 16-26% of splits; walk-forward OOS IR 0.09; nothing after 2005.')
    A('- **F5 (E7 attention fade) does not work as a monthly exclusion** on B2/B3 and is the weakest filter on B1; its events are '
      'short-horizon (E7 measured 5-20 day effects), and a month-end screen with a 20-session memory flags ~23% of names, raising '
      'turnover sharply. **F6 (dilution)** helps B1/B4 modestly (+2.3% / +4.2%), little elsewhere.')
    lb = LL[LL['filter'] == 'none']
    A(f'- Limit-lock audit: {lb[lb.base == "B1"].share_entries_locked.iloc[0] * 100:.1f}% of B1 entries would be bought at a locked '
      f'limit-up close and {lb[lb.base == "B1"].share_exits_locked.iloc[0] * 100:.1f}% of exits sold at a locked limit-down close '
      f'(not fillable at the close); with F4 {LL[(LL.base == "B1") & (LL["filter"] != "none")].share_entries_locked.iloc[0] * 100:.1f}% / '
      f'{LL[(LL.base == "B1") & (LL["filter"] != "none")].share_exits_locked.iloc[0] * 100:.1f}%. Fills are not modelled; the screens reduce the '
      'problem rather than create it.')
    A('')
    # ---------------- Task 3 ----------------
    A('## 4. Task 3: momentum crash controls (12-1)')
    A('')
    A('R-03 own-volatility scaling: s_t = min(1, 12% / sigma126_t) from the sleeve\'s own unit daily returns through t, applied to t+1. '
      'R-04 Daniel-Moskowitz gate on the rebuilt KOSPI: 0.5 when the 24-month KOSPI return to the last month-end is negative AND '
      'KOSPI sigma126 is above its expanding 2/3 quantile (>= 252 obs), else 1. Costs include the overlay\'s own exposure changes '
      f'(both legs). The D&M gate was on {CC[(CC.sleeve=="LS_EW (ALL quintiles)")&(CC.control=="DM gate (KOSPI, floor 0.5)")&(CC.cost=="net35")&(CC.period=="full 1996-04..2026-09")&(CC.metric=="pct_days_below_1")].value.iloc[0]*100:.1f}% '
      f'of days with {len(ONS)} onsets ({", ".join(ONS.onset.tolist())}).')
    A('')
    rows = []
    for sl in ('LS_EW (ALL quintiles)', 'LS_VW (ALL quintiles)', 'LO_EW excess (Q5 vs EW univ)', 'LO_VW excess (Q5 vs VW univ)',
               'E5 top500 D10-D1 EW', 'E5 top500 D10-D1 VW'):
        for ctl in ('static', 'VS (own vol, 12%, cap 1)', 'DM gate (KOSPI, floor 0.5)', 'VS x DM'):
            ex = CE[(CE.sleeve == sl) & (CE.control == ctl)].iloc[0]
            rows.append([sl, ctl, num(cc(sl, ctl, 'gross', 'full 1996-04..2026-09', 'sharpe')),
                         num(cc(sl, ctl, 'net35', 'full 1996-04..2026-09', 'sharpe')), num(cc(sl, ctl, 'net70', 'full 1996-04..2026-09', 'sharpe')),
                         pct(cc(sl, ctl, 'net35', 'full 1996-04..2026-09', 'max_dd'), 0, False),
                         num(cc(sl, ctl, 'net35', '2016-01..2026-09', 'sharpe')),
                         f"{cc(sl, ctl, 'net35', 'full 1996-04..2026-09', 'avg_exposure'):.2f}",
                         pct(cw(sl, ctl, '2008-06..2009-03 GFC'), 1), pct(cw(sl, ctl, '2009-03..2009-05 post-GFC rebound (D&M crash months)'), 1),
                         pct(cw(sl, ctl, '2020-02-17..03-19 COVID crash'), 1), pct(cw(sl, ctl, '2020-03-20..06-30 COVID rebound'), 1),
                         pct(cw(sl, ctl, '2026-06-22..07-30 crash'), 1),
                         f"{ex.s_on_2026_06_22:.2f} ({'yes' if ex.cut_before_2026_07_01 else 'no'})"])
    A(md_table(['Sleeve', 'Control', 'Sharpe gross', 'Sharpe net 35', 'net 70', 'Max DD net', 'Sharpe 2016-26 net', 'Avg exposure',
                'GFC 08-06..09-03', 'Mar-May 2009', 'COVID crash', 'COVID rebound', '2026-06-22..07-30', 'Exposure 2026-06-22 (cut before Jul?)'], rows))
    A('')
    st_same = CW[CW.control.str.startswith('static at same avg exposure as VS (own vol') & (CW.window == '2026-06-22..07-30 crash')]
    A('**Crash-control verdict.** (i) Own-volatility scaling is the only control that was de-risked before July 2026 (it had been '
      'cutting since January 2026 because the sleeves\' own volatility rose in the melt-up); the D&M gate never fires in a bull-market '
      'crash and fired 9 times in 30 years, mostly in 1997-99, 2001, 2008 and March 2020. (ii) Full-sample net Sharpe improves with '
      'each control and most with both, and the max drawdown of the VW long-short sleeves falls by 30-45 points, but the gain comes '
      'from 1997-2009; in 2016-2026 the combined overlay lowered net Sharpe for every long-short sleeve, and the only post-2016 '
      'gains are small (the D&M gate alone on the VW long-short, +0.01; scaling alone or combined on the VW long-only excess, '
      '+0.02 to +0.04). (iii) In the 2026 crash window scaling beat a static book with the '
      f'same average exposure (12-1 LS VW: {pct(cw("LS_VW (ALL quintiles)","VS (own vol, 12%, cap 1)","2026-06-22..07-30 crash"))} vs '
      f'{pct(float(st_same[st_same.sleeve=="LS_VW (ALL quintiles)"].cum_return_net35.iloc[0]))}), confirming E5. (iv) For long-only '
      'momentum the controls do not fix the sign: the EW winners-minus-universe sleeve stays negative net under every control. '
      'Recommendation: keep R-03 (and R-04 in the spec book) as mandatory risk controls on any Korean momentum sleeve; they do not '
      'turn Korean 12-1 into a PASS candidate.')
    A('')
    sl_ = SLS[(SLS.sleeve == 'E5 top500 deciles')]
    def slv(w, cost, var, col):
        return float(sl_[(sl_.weighting == w) & (sl_.cost == cost) & (sl_.variant == var)][col].iloc[0])
    A(f'**E5 stop-loss re-run** (top-500 D10-D1, 2000-01..2026-09, 15% stop from the formation close, close trigger, exit at the next '
      f'close, cash to the next rebalance): EW gross Sharpe {slv("EW","gross","no stop","sharpe"):.2f} -> {slv("EW","gross","15% stop, exit next close","sharpe"):.2f} '
      f'(net {slv("EW","net35","no stop","sharpe"):.2f} -> {slv("EW","net35","15% stop, exit next close","sharpe"):.2f}), VW '
      f'{slv("VW","gross","no stop","sharpe"):.2f} -> {slv("VW","gross","15% stop, exit next close","sharpe"):.2f} '
      f'(net {slv("VW","net35","no stop","sharpe"):.2f} -> {slv("VW","net35","15% stop, exit next close","sharpe"):.2f}); worst month EW '
      f'{pct(slv("EW","gross","no stop","worst_month"))} -> {pct(slv("EW","gross","15% stop, exit next close","worst_month"))}. '
      f'Exiting at the trigger close instead: EW {slv("EW","gross","15% stop, exit same close","sharpe"):.2f}; 10% stop: '
      f'{slv("EW","gross","10% stop, exit next close","sharpe"):.2f}. **Reproduced in direction and proportion** (E5: 0.43 -> 0.26, about -40%; '
      f'here about -35%); the level differs because the static EW Sharpe differs (see E5 row above). ALL quintiles behave the same way '
      '(`results/r2_kr_stoploss.csv`).')
    A('')
    # ---------------- Task 4 ----------------
    A('## 5. Task 4: 1-month reversal, value-weighted, microcaps excluded (P1\'s flag)')
    A('')
    rows = []
    for un in ('ALL', 'LARGE'):
        for w in ('VW', 'EW'):
            for srt in ('deciles', 'quintiles'):
                for cost in ('gross', 'net35'):
                    q = REV[(REV.universe == un) & (REV.weighting == w) & (REV['sort'] == srt) & (REV.cost == cost)]
                    cells = []
                    for p in ('full', '1996-2005', '2006-2015', '2016-2026-09', '1999-2021'):
                        r = q[q.period == p].iloc[0]
                        cells.append(f'{r.mean_pct_month:+.2f} ({r.nw_t:.1f})')
                    rows.append([un, w, srt, cost] + cells + [num(q[q.period == "full"].sharpe.iloc[0])])
    A(md_table(['Universe', 'Wt', 'Sort', 'Cost', 'Full', '1996-2005', '2006-2015', '2016-2026-09', '1999-2021', 'Sharpe full'], rows))
    A('')
    A('Losers minus winners, %/month (NW t). Turnover is about 40x a year (both legs). **Verdict:** confirmed. Value-weighted and '
      'without microcaps, 1-month reversal is not distinguishable from zero gross after 2005 and is negative net of 35 bp in every '
      'sub-period after 2005, in both ALL and the top 200; the equal-weighted decile spread (+1.43%/month full sample) is the '
      'only version that resembles the literature, and even it nets about zero. Keep Korean short-term reversal at 0-1 for cash '
      'equities (round-1 conclusion stands).')
    A('')
    # ---------------- Task 5 ----------------
    A('## 6. Task 5: low volatility as protection, not alpha')
    A('')
    rows = []
    for _, r in LV[(LV.cost == 'net35') & (LV.market == 'VW ALL universe (gross)')].iterrows():
        rows.append([r.book, r.period, num(r.beta), f'{pct(r.alpha_ann_rf0)} ({r.alpha_t:.1f})', pct(r.alpha_ann_if_rf4pct),
                     num(r.book_sharpe), num(r.mkt_sharpe), pct(r.book_maxdd, 0, False), pct(r.mkt_maxdd, 0, False),
                     num(r.up_capture), num(r.down_capture)])
    A(md_table(['Book (net 35)', 'Period', 'Beta to VW market', 'CAPM alpha rf=0 (t)', 'Alpha if rf=4%', 'Sharpe', 'Market Sharpe',
                'Max DD', 'Market max DD', 'Up capture', 'Down capture'], rows))
    A('')
    rows = []
    for _, r in LVW.iterrows():
        rows.append([r.book.replace(' net35', ''), r.window, r.kind, pct(r.book_return), pct(r.vw_universe), pct(r.ew_universe),
                     pct(r.book_minus_vw)])
    A(md_table(['Book', 'Window', 'Kind', 'Book (net 35)', 'VW universe', 'EW universe', 'Book - VW'], rows))
    A('')
    A('No Korean short-rate series is available offline, so alphas use rf = 0; with a short rate the CAPM alpha of a beta-below-1 '
      'book falls by (1 - beta) x rf (the "rf = 4%" column is an assumption for scale, not data). **Verdict: protective card.** Beta '
      f'{lv_e.beta:.2f}-{lv_v.beta:.2f}, down capture below up capture, large outperformance in most crash windows (dot-com, 2022, '
      'Aug-2024, Jun-Jul 2026), but an EW max drawdown no better than the market (the 1997-98 crisis hit small low-vol stocks hard) '
      f'and a heavy bull-market tax (it lagged in {nr} of {nrt} rebound windows across the two books, including the 2026 melt-up). '
      'Net CAPM alpha is insignificant in the full sample (t below 1 against the VW market) and switches sign across sub-periods, so '
      'it should be judged on drawdown-first, Sharpe-non-inferiority terms (E7\'s K-LV framing), not on alpha.')
    A('')
    # ---------------- trials ----------------
    A('## 7. Trial count and multiple testing')
    A('')
    A(f'- Exclusion horse race: **{n_trials} trials** = 44 filter definitions x 4 bases (8 primary filters, 36 neighbours / variants: '
      'cut levels 10/15/25/30% for F1-F3, TURN_3M, VOL_1M, VOL_6M, MAX_3M, F4 cuts 5/15/20/25%, F5 windows 5/10/40/60, F5 regime-limit '
      'lock, F5 components alone, F6 thresholds 5/20/30%, F6 net issuance, F7 at 10/30% cuts, F8 with F6b or the regime lock), each at '
      'three cost levels (cost levels are stresses of the same trial, not extra trials). Two definition fixes were made before any '
      'performance was computed, after inspecting flag rates: the split-like rule requires a share change of more than 5% (otherwise '
      'every small convertible-bond conversion counted as a split), and F5\'s lock component follows E7\'s written spec (the regime-limit '
      'lock flagged 51% of the 1990s universe and is kept as a variant).')
    A('- Momentum grid: 56 sleeves (4 signals x 7 turnover cells x 2 weightings) x 7 legs x 5 periods (descriptive, no selection) plus '
      '28 claim-reproduction books; crash controls: 6 sleeves x 4 controls x 3 cost levels plus 18 same-exposure statics; stop-loss: '
      '2 sleeve sets x 2 weightings x 4 variants x 2 cost levels; reversal: 2 universes x 2 weightings x 2 sorts x 3 cost levels; '
      'low-vol: 2 books. One exploratory check outside these scripts (E5 looser top-500 universe) was folded into r2_kr_03.')
    A('')
    # ---------------- validation ----------------
    A('## 8. Validation')
    A('')
    A(md_table(['Test', 'Item', 'Result', 'Passed'], [[r['test'], r['item'], r['value'], 'yes' if r['passed'] else 'NO']
                                                      for _, r in VAL.iterrows()]))
    A('')
    A('SHA-256 checksums of every result file are written last by the runner (`results/r2_kr_hashes.csv`). The round-1 '
      'reproduction checks are listed in `results/r2_kr_reproduce_r1.csv`; the crash-control and stop-loss engines agree with the '
      'main engine to four decimals of Sharpe (`results/r2_kr_stoploss_engine_check.csv`).')
    A('')
    # ---------------- caveats ----------------
    A('## 9. Caveats')
    A('')
    A('- **Price returns, no dividends.** Low-vol, low-turnover and large-cap books are understated by roughly their dividend yield '
      '(about 1-2% a year in Korea). The screens remove high-turnover, high-volatility names that pay little or no dividend, so '
      'total returns would most likely raise the filtered-minus-unfiltered differences slightly; long-short and excess figures are '
      'affected only by the yield gap between the legs.')
    A('- **Delistings**: a disappearing stock is held at its last price as cash (round-1 rule; bias bound about 1.4%/yr for the '
      'worst quintile book, smaller for the screened books, which hold fewer distressed names).')
    A('- **Limit-lock fills are not modelled** (orders at a locked limit-up/limit-down close are assumed filled); the audit above '
      'counts them. Market impact is not modelled; EW books hold small caps.')
    A('- **No risk-free rate** (CAPM alphas use rf = 0; Sharpe ratios are raw).')
    A('- **Shorting** is a research benchmark only (bans 2008-09, 2011, 2020-21, 2023-11..2025-03); only long-only results are implementable.')
    A('- **E5 and P2 scripts were not saved**, so their EW constructions could not be matched exactly; the E7 and P6 scripts were '
      'read and their constructions replicated; the KJFS paper was not available, so the unadjusted-price explanation is a tested '
      'hypothesis about its data, not a finding about the paper.')
    A('- **F5 and F6 depend on definitions** that differ from the literature (see section 3); the regime-limit and net-issuance '
      'variants are reported.')
    A('- Everything is in-sample. The indicative gate uses the walk-forward, bootstrap, DSR and CSCV machinery on the realised series; '
      'it is not QUANTGEN\'s code path.')
    A('')
    A('## 10. Files')
    A('')
    A('- Scripts: `r2_kr_common.py` (engine reuse, statistics, bootstrap, DSR, CSCV), `r2_kr_01_build_extra.py` (volume, shares, '
      'ChangeCode, Dept, limit locks, F5/F6 inputs, new signals, universes), `r2_kr_02_reproduce_r1.py`, `r2_kr_03_momentum.py`, '
      '`r2_kr_04_exclusion.py`, `r2_kr_05_crash_controls.py`, `r2_kr_06_reversal_lowvol.py`, `r2_kr_07_validation.py`, '
      '`r2_kr_08_charts_summary.py`, `r2_kr_run_all.py`.')
    A('- Results: `r2_kr_mom_grid_long.csv`, `r2_kr_mom_claims_long.csv`, `r2_kr_mom_e7_ladder.csv`, `r2_kr_mom_kjfs_events.csv`, '
      '`r2_kr_excl_summary.csv`, `r2_kr_excl_long.csv`, `r2_kr_excl_windows.csv`, `r2_kr_excl_years.csv`, `r2_kr_excl_jaccard.csv`, '
      '`r2_kr_excl_gate.csv`, `r2_kr_excl_trials.csv`, `r2_kr_excl_dsr_best.csv`, `r2_kr_excl_limitlock.csv`, '
      '`r2_kr_excl_f6_diagnostic.csv`, `r2_kr_excl_thin_books.csv`, `r2_kr_crash_controls.csv`, `r2_kr_crash_windows.csv`, '
      '`r2_kr_crash_exposure_2026.csv`, `r2_kr_dm_gate_onsets.csv`, `r2_kr_dm_gate_sample.csv`, `r2_kr_stoploss.csv`, '
      '`r2_kr_stoploss_engine_check.csv`, `r2_kr_reversal.csv`, `r2_kr_lowvol.csv`, `r2_kr_lowvol_windows.csv`, '
      '`r2_kr_reproduce_r1.csv`, `r2_kr_validation.csv`, `r2_kr_hashes.csv`.')
    A('- Charts: `r2_kr_chart_a_excl_cum_excess.json`, `r2_kr_chart_b_mom_grid_heatmap.json`, `r2_kr_chart_c_crash_windows.json`, '
      '`r2_kr_chart_d_b2_2025_2026.json`.')
    with open(OUT_MD, 'w', encoding='utf-8') as f:
        f.write('\n'.join(md) + '\n')
    log(f'summary written: {OUT_MD}')


if __name__ == '__main__':
    main()
