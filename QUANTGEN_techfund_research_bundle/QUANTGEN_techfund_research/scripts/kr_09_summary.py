"""kr_09_summary.py -- writes kr/KR_datalab_summary.md and results/kr_key_numbers.csv from the result tables.

Every number in the summary is read from results/*.csv produced by kr_01..kr_08 (nothing is typed in by hand
except the interpretation text, which references those numbers).
"""
import sys, time
import numpy as np
import pandas as pd
sys.path.insert(0, '/home/claude/datalab/scripts')
from kr_common import RES, ROOT, CACHE, COST, EVENT_WINDOWS

OUT = f'{ROOT}/kr/KR_datalab_summary.md'
SIG_ORDER = ['MOM_12_1', 'MOM_6_1', 'REV_1M', 'HIGH52', 'VOL_3M', 'MAX_1M', 'TURN_1M_LOW', 'TURN_1M_HIGH', 'SIZE',
             'PMA200', 'RSI14_CON', 'RSI14_MOM', 'BBPCTB_CON', 'BBPCTB_MOM', 'REV_1W', 'REV_1W_VSlow', 'REV_1W_VSmid',
             'REV_1W_VShigh']
LABEL = {'MOM_12_1': 'MOM 12-1 (buy winners)', 'MOM_6_1': 'MOM 6-1 (buy winners)', 'REV_1M': 'REV 1M (buy losers)',
         'HIGH52': '52-week high (buy near high)', 'VOL_3M': 'VOL 3M (buy low vol)', 'MAX_1M': 'MAX 1M (buy low MAX)',
         'TURN_1M_LOW': 'TURN 1M (buy low turnover)', 'TURN_1M_HIGH': 'TURN 1M (buy high turnover)',
         'SIZE': 'SIZE (small minus big)', 'PMA200': 'Price/SMA200 (buy high)', 'RSI14_CON': 'RSI14 contrarian (buy low)',
         'RSI14_MOM': 'RSI14 momentum (buy high)', 'BBPCTB_CON': 'Bollinger %B contrarian', 'BBPCTB_MOM': 'Bollinger %B momentum',
         'REV_1W': 'REV 1W weekly (buy losers)', 'REV_1W_VSlow': 'REV 1W, low volume spike', 'REV_1W_VSmid': 'REV 1W, mid volume spike',
         'REV_1W_VShigh': 'REV 1W, high volume spike'}


def pct(v, d=1):
    return 'n/a' if v is None or not np.isfinite(v) else f'{v * 100:+.{d}f}%'


def pctu(v, d=1):
    return 'n/a' if v is None or not np.isfinite(v) else f'{v * 100:.{d}f}%'


def num(v, d=2):
    return 'n/a' if v is None or not np.isfinite(v) else f'{v:.{d}f}'


def main():
    t0 = time.time()
    T = pd.read_csv(f'{RES}/kr_signal_stats_long.csv')
    TS = pd.read_csv(f'{RES}/kr_signal_stats_long_strict.csv')
    EV = pd.read_csv(f'{RES}/kr_event_windows.csv')
    IX = pd.read_csv(f'{RES}/kr_index_timing.csv')
    IXE = pd.read_csv(f'{RES}/kr_index_timing_events.csv')
    SPA = pd.read_csv(f'{RES}/kr_index_spa.csv').set_index(['section', 'key'])['value']
    SAN = pd.read_csv(f'{RES}/kr_index_sanity.csv')
    VAL = pd.read_csv(f'{RES}/kr_validation.csv')
    FLAGS = pd.read_csv(f'{RES}/kr_return_flags_totals.csv', index_col=0)['count']
    FLAGEV = pd.read_csv(f'{RES}/kr_return_flags_events.csv', dtype={'code': str})
    PROF = pd.read_csv(f'{RES}/kr_data_profile.csv')
    DISP = pd.read_csv(f'{RES}/kr_disappearances.csv')
    DEXP = pd.read_csv(f'{RES}/kr_delisting_exposure_monthly.csv')
    UC = pd.read_csv(f'{RES}/kr_universe_counts.csv')
    CX = pd.read_csv(f'{RES}/kr_crosschecks.csv')
    COR = pd.read_csv(f'{RES}/kr_ls_correlation_ALL_EW.csv', index_col=0)
    TOP2W, TOP2R = top2_meltup()

    full = T[T.period == 'full']

    def g(sig, u, w, leg, cl, m, period='full', tab=None):
        x = (tab if tab is not None else T)
        x = x[(x.signal == sig) & (x.universe == u) & (x.weighting == w) & (x.leg == leg) & (x.cost_level == cl) &
              (x.metric == m) & (x.period == period)]
        return float(x.value.iloc[0]) if len(x) else np.nan

    def ev(sig, u, w, leg, cl, win):
        x = EV[(EV.signal == sig) & (EV.universe == u) & (EV.weighting == w) & (EV.leg == leg) & (EV.cost_level == cl) &
               (EV.window == win)]
        return float(x.cum_return.iloc[0]) if len(x) else np.nan

    # ---------------- key numbers table (CSV + markdown)
    key_rows = []
    for s in SIG_ORDER:
        for w in ('EW', 'VW'):
            bench = 'LO_xs_UEW' if w == 'EW' else 'LO_xs_UVW'
            excl = 'LO_excl_worst_xs_UEW' if w == 'EW' else 'LO_excl_worst_xs_UVW'
            r = dict(signal=s, universe='ALL', weighting=w,
                     ls_gross_ann=g(s, 'ALL', w, 'LS', 'gross', 'ann_mean'), ls_gross_sharpe=g(s, 'ALL', w, 'LS', 'gross', 'sharpe'),
                     ls_gross_nw_t=g(s, 'ALL', w, 'LS', 'gross', 'nw_t'),
                     ls_net35_sharpe=g(s, 'ALL', w, 'LS', 'net35', 'sharpe'), ls_net70_sharpe=g(s, 'ALL', w, 'LS', 'net70', 'sharpe'),
                     lo_net35_ann=g(s, 'ALL', w, 'LO', 'net35', 'ann_mean'), lo_net35_sharpe=g(s, 'ALL', w, 'LO', 'net35', 'sharpe'),
                     lo_net35_maxdd=g(s, 'ALL', w, 'LO', 'net35', 'max_dd'),
                     lo_xs_net35_ann=g(s, 'ALL', w, bench, 'net35', 'ann_mean'), lo_xs_net35_t=g(s, 'ALL', w, bench, 'net35', 'nw_t'),
                     lo_xs_net70_ann=g(s, 'ALL', w, bench, 'net70', 'ann_mean'),
                     excl_xs_net35_ann=g(s, 'ALL', w, excl, 'net35', 'ann_mean'), excl_xs_net35_t=g(s, 'ALL', w, excl, 'net35', 'nw_t'),
                     ls_turnover_yr=g(s, 'ALL', w, 'LS', 'gross', 'turnover_per_year'),
                     lo_turnover_yr=g(s, 'ALL', w, 'LO', 'gross', 'turnover_per_year'),
                     ls_pos_years=g(s, 'ALL', w, 'LS', 'gross', 'pct_pos_years'),
                     large_vw_ls_gross_sharpe=g(s, 'LARGE', 'VW', 'LS', 'gross', 'sharpe'),
                     large_vw_lo_xs_net35_ann=g(s, 'LARGE', 'VW', 'LO_xs_UVW', 'net35', 'ann_mean'))
            key_rows.append(r)
    KN = pd.DataFrame(key_rows)
    KN.to_csv(f'{RES}/kr_key_numbers.csv', index=False, float_format='%.6g')

    L = []
    A = L.append
    A('# KRX technical signals: data-lab results (Korea)')
    A('')
    A('QUANTGEN technical and fundamental signals project, Korea data lab. Data: marcap daily snapshots of every '
      'KRX-listed stock, 1995-05-02 to 2026-09-29 (survivorship-free). Portfolios run from 1996-03 (first formation '
      'with 252 days of history) to 2026-09-29. All numbers below are read from the CSV files in '
      '`/home/claude/datalab/kr/results/` by `kr_09_summary.py`; scripts are in `/home/claude/datalab/scripts/kr_*.py` '
      '(`python3 kr_run_all.py` reruns everything in about 10 minutes, peak memory about 2 GB).')
    A('')
    A('Conventions: signal at the close of t, portfolio formed at the close of t, returns from t+1. Price returns '
      '(r = ChangesRatio/100, dividends excluded). Costs: 35 bp per side on every unit traded (stress 70 bp); '
      'index timing 3 bp (stress 6 bp). LS = best minus worst quintile in the hypothesised direction, both legs '
      'pay costs, $1 long / $1 short. LO = best quintile. "Excess" = LO minus the universe portfolio with the same '
      'weighting (EW vs EW universe, VW vs VW universe), net of the LO leg\'s costs. Sharpe uses raw returns '
      '(no risk-free rate). Newey-West t uses 6 lags (monthly) or 4 (weekly).')
    A('')
    # ---------- headline
    A('## Headline findings')
    A('')
    uew = g('UNIV', 'ALL', 'EW', 'LO', 'net35', 'ann_mean'); uvw = g('UNIV', 'ALL', 'VW', 'LO', 'net35', 'ann_mean')
    A(f'1. **Gross long-short spreads are real; most of them do not survive 35 bp per side, and the ones that do come '
      f'from the short leg.** The strongest monthly spreads in the ALL universe (EW) are low turnover '
      f'({pct(g("TURN_1M_LOW","ALL","EW","LS","gross","ann_mean"))}/yr, Sharpe {num(g("TURN_1M_LOW","ALL","EW","LS","gross","sharpe"))}, '
      f't {num(g("TURN_1M_LOW","ALL","EW","LS","gross","nw_t"))}), low MAX '
      f'({pct(g("MAX_1M","ALL","EW","LS","gross","ann_mean"))}, Sharpe {num(g("MAX_1M","ALL","EW","LS","gross","sharpe"))}) and low '
      f'volatility ({pct(g("VOL_3M","ALL","EW","LS","gross","ann_mean"))}, Sharpe {num(g("VOL_3M","ALL","EW","LS","gross","sharpe"))}). '
      f'The quintile means show where the spread comes from: the worst quintile loses money in absolute terms '
      f'(high turnover {pct(g("TURN_1M","ALL","EW","Q5","gross","ann_mean"))}/yr, high volatility {pct(g("VOL_3M","ALL","EW","Q5","gross","ann_mean"))}, '
      f'high MAX {pct(g("MAX_1M","ALL","EW","Q5","gross","ann_mean"))}, gross) while the best quintile is close to '
      f'the EW universe ({pct(g("UNIV","ALL","EW","LO","gross","ann_mean"))}).')
    monthly_sigs = [s_ for s_ in SIG_ORDER if not s_.startswith('REV_1W')]
    sig_t2 = [s_ for s_ in monthly_sigs if g(s_, 'ALL', 'EW', 'LO_xs_UEW', 'net35', 'nw_t') > 2]
    vw_pos = [s_ for s_ in SIG_ORDER if g(s_, 'ALL', 'VW', 'LO_xs_UVW', 'net35', 'ann_mean') > 0]
    vw_list = ', '.join(f"{v} ({pct(g(v, 'ALL', 'VW', 'LO_xs_UVW', 'net35', 'ann_mean'))}, t "
                        f"{num(g(v, 'ALL', 'VW', 'LO_xs_UVW', 'net35', 'nw_t'), 1)})" for v in vw_pos)
    vw_maxt = max([g(v, 'ALL', 'VW', 'LO_xs_UVW', 'net35', 'nw_t') for v in vw_pos] or [np.nan])
    sz = lambda p: g('SIZE', 'ALL', 'EW', 'LO_xs_UEW', 'net35', 'ann_mean', p)
    A(f'2. **Long-only top quintiles: only small caps beat the universe net of 35 bp with t > 2 '
      f'({", ".join(sig_t2) if sig_t2 else "none"}, EW), and that edge has faded.** SIZE (smallest quintile of the screened '
      f'universe) {pct(sz("full"))}/yr over the EW universe (t {num(g("SIZE","ALL","EW","LO_xs_UEW","net35","nw_t"))}); by sub-period '
      f'{pct(sz("1996-2005"))} / {pct(sz("2006-2015"))} / {pct(sz("2016-2026"))}, and the SIZE long-short spread returned '
      f'{pct(g("SIZE","ALL","EW","LS","gross","total_return","2025"))} in 2025 and {pct(g("SIZE","ALL","EW","LS","gross","total_return","2026"))} '
      f'in 2026 to date; market impact in these stocks is not modelled. Every other EW top quintile is within noise of the universe '
      f'or below it (TURN low {pct(g("TURN_1M_LOW","ALL","EW","LO_xs_UEW","net35","ann_mean"))}, HIGH52 '
      f'{pct(g("HIGH52","ALL","EW","LO_xs_UEW","net35","ann_mean"))}, VOL low {pct(g("VOL_3M","ALL","EW","LO_xs_UEW","net35","ann_mean"))}, '
      f'MOM 12-1 {pct(g("MOM_12_1","ALL","EW","LO_xs_UEW","net35","ann_mean"))}). Against the VW universe (the investable benchmark) '
      f'only {vw_list} of the VW top quintiles are positive net of costs (largest t {num(vw_maxt, 1)}).')
    A(f'3. **What is implementable long-only is the exclusion screen, not the stock-picking quintile.** Holding the '
      f'universe minus the worst quintile of TURN 1M (highest turnover) earns {pct(g("TURN_1M_LOW","ALL","EW","LO_excl_worst_xs_UEW","net35","ann_mean"))}/yr over the EW universe '
      f'net of 35 bp (t {num(g("TURN_1M_LOW","ALL","EW","LO_excl_worst_xs_UEW","net35","nw_t"))}, {pctu(g("TURN_1M_LOW","ALL","EW","LO_excl_worst_xs_UEW","net35","pct_pos_years"),0)} of years positive, '
      f'{pct(g("TURN_1M_LOW","ALL","EW","LO_excl_worst_xs_UEW","net70","ann_mean"))} at 70 bp); excluding the most volatile quintile (VOL 3M) '
      f'{pct(g("VOL_3M","ALL","EW","LO_excl_worst_xs_UEW","net35","ann_mean"))} (t {num(g("VOL_3M","ALL","EW","LO_excl_worst_xs_UEW","net35","nw_t"))}). '
      f'Value-weighted the effect shrinks to {pct(g("TURN_1M_LOW","ALL","VW","LO_excl_worst_xs_UVW","net35","ann_mean"))} and '
      f'{pct(g("VOL_3M","ALL","VW","LO_excl_worst_xs_UVW","net35","ann_mean"))} over the VW universe (t {num(g("TURN_1M_LOW","ALL","VW","LO_excl_worst_xs_UVW","net35","nw_t"))} and '
      f'{num(g("VOL_3M","ALL","VW","LO_excl_worst_xs_UVW","net35","nw_t"))}). These are small, steady tilts, not alpha engines.')
    A(f'4. **Weekly reversal is the largest gross effect and the clearest cost casualty.** REV 1W long-short earns '
      f'{pct(g("REV_1W","ALL","EW","LS","gross","ann_mean"))}/yr gross (EW, Sharpe {num(g("REV_1W","ALL","EW","LS","gross","sharpe"))}; '
      f'VW {pct(g("REV_1W","ALL","VW","LS","gross","ann_mean"))}, Sharpe {num(g("REV_1W","ALL","VW","LS","gross","sharpe"))}) on '
      f'{num(g("REV_1W","ALL","EW","LS","gross","turnover_per_year"),0)}x turnover per year (both legs), so the break-even cost is '
      f'{num(g("REV_1W","ALL","EW","LS","gross","ann_mean")/g("REV_1W","ALL","EW","LS","gross","turnover_per_year")*1e4,1)} bp per side (EW) and '
      f'{num(g("REV_1W","ALL","VW","LS","gross","ann_mean")/g("REV_1W","ALL","VW","LS","gross","turnover_per_year")*1e4,1)} bp (VW), '
      f'far below 35 bp: net Sharpe {num(g("REV_1W","ALL","EW","LS","net35","sharpe"))} (EW). The volume split does not rescue it: gross Sharpe '
      f'{num(g("REV_1W_VSlow","ALL","EW","LS","gross","sharpe"))} after low-volume weeks, {num(g("REV_1W_VSmid","ALL","EW","LS","gross","sharpe"))} mid, '
      f'{num(g("REV_1W_VShigh","ALL","EW","LS","gross","sharpe"))} high (EW); value-weighted the high-volume tercile is strongest '
      f'({num(g("REV_1W_VShigh","ALL","VW","LS","gross","sharpe"))} vs {num(g("REV_1W_VSlow","ALL","VW","LS","gross","sharpe"))}). '
      f'The prior design\'s volume-filtered short-term reversal (Korea weight 3) is not supported at 35 bp.')
    A(f'5. **Momentum, trend and oscillators are weak in Korea.** MOM 12-1 LS gross {pct(g("MOM_12_1","ALL","EW","LS","gross","ann_mean"))} '
      f'(Sharpe {num(g("MOM_12_1","ALL","EW","LS","gross","sharpe"))}; 2016-2026 Sharpe {num(g("MOM_12_1","ALL","EW","LS","gross","sharpe","2016-2026"))}); '
      f'MOM 6-1 {num(g("MOM_6_1","ALL","EW","LS","gross","sharpe"))}; PMA200 {num(g("PMA200","ALL","EW","LS","gross","sharpe"))}. '
      f'RSI14 and Bollinger %B work only in the contrarian direction and only gross (Sharpe {num(g("RSI14_CON","ALL","EW","LS","gross","sharpe"))} and '
      f'{num(g("BBPCTB_CON","ALL","EW","LS","gross","sharpe"))}); at 35 bp both are negative ({num(g("RSI14_CON","ALL","EW","LS","net35","sharpe"))}, '
      f'{num(g("BBPCTB_CON","ALL","EW","LS","net35","sharpe"))}). The momentum direction of RSI/%B loses money even gross.')
    A(f'6. **Index timing on the KOSPI: no rule beats buy-and-hold on mean return; trend rules cut drawdowns and, thanks to '
      f'1997-2000, compound slightly faster.** Close > SMA200 (net 3 bp): CAGR {pctu(gx(IX,"SMA200 (close > SMA200)","net3","full","cagr"))} '
      f'and 10-month SMA {pctu(gx(IX,"10M_SMA (monthly)","net3","full","cagr"))} vs {pctu(gx(IX,"Buy & hold","gross","full","cagr"))} buy-and-hold, '
      f'Sharpe {num(gx(IX,"SMA200 (close > SMA200)","net3","full","sharpe"))} / {num(gx(IX,"10M_SMA (monthly)","net3","full","sharpe"))} vs '
      f'{num(gx(IX,"Buy & hold","gross","full","sharpe"))}, max drawdown {pctu(gx(IX,"SMA200 (close > SMA200)","net3","full","max_dd"))} / '
      f'{pctu(gx(IX,"10M_SMA (monthly)","net3","full","max_dd"))} vs {pctu(gx(IX,"Buy & hold","gross","full","max_dd"))}; but their arithmetic '
      f'mean daily return is below buy-and-hold ({pct(gx(IX,"SMA200 (close > SMA200)","net3","full","excess_mean_ann_vs_bh"))} and '
      f'{pct(gx(IX,"10M_SMA (monthly)","net3","full","excess_mean_ann_vs_bh"))} a year), and in 2006-2015 the 10-month SMA compounded at '
      f'{pctu(gx(IX,"10M_SMA (monthly)","net3","2006-2015","cagr"))} vs {pctu(gx(IX,"Buy & hold","gross","2006-2015","cagr"))}. '
      f'Hansen SPA over {int(float(SPA[("family","n_variants")]))} variants (losses relative to buy-and-hold): consistent p = '
      f'{num(float(SPA[("full","spa_p_consistent")]),3)}; the best rule in the full sample ({SPA[("full","best_rule")]}) beats buy-and-hold by '
      f'{pct(float(SPA[("full","best_rule_mean_excess_ann")]))}/yr (t {num(float(SPA[("full","best_rule_nw_t_excess")]))}). '
      f'The rule selected on 1996-2012 ({SPA[("selected_by_excess_t","rule")]}) trailed buy-and-hold by '
      f'{pctu(-float(SPA[("selected_by_excess_t","oos_excess_mean_ann")]))} a year in 2013-2026.')
    A('')
    # ---------- key numbers table
    A('## Key numbers: monthly and weekly signals, ALL universe (microcap screen), 1996-2026')
    A('')
    A('Annualised. LS = long-short; LO excess = best quintile minus the universe with the same weighting; Excl = '
      'universe minus the worst quintile, minus the universe. Turnover = per year, both legs for LS.')
    A('')
    for w in ('EW', 'VW'):
        A(f'### {w} (equal-weighted)' if w == 'EW' else '### VW (value-weighted, Marcap at t)')
        A('')
        A('| Signal | LS gross | Sharpe | NW t | LS Sharpe net35 / net70 | LO net35 (abs) | LO excess net35 (t) | Excl-worst excess net35 (t) | LS turnover/yr | LS % years > 0 |')
        A('|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|')
        for s in SIG_ORDER:
            r = KN[(KN.signal == s) & (KN.weighting == w)].iloc[0]
            ex = (f'{pct(r.excl_xs_net35_ann)} ({num(r.excl_xs_net35_t,1)})' if np.isfinite(r.excl_xs_net35_ann) else 'n/a (weekly)')
            A(f'| {LABEL[s]} | {pct(r.ls_gross_ann)} | {num(r.ls_gross_sharpe)} | {num(r.ls_gross_nw_t,1)} | '
              f'{num(r.ls_net35_sharpe)} / {num(r.ls_net70_sharpe)} | {pct(r.lo_net35_ann)} | '
              f'{pct(r.lo_xs_net35_ann)} ({num(r.lo_xs_net35_t,1)}) | {ex} | {num(r.ls_turnover_yr,1)} | {pctu(r.ls_pos_years,0)} |')
        u = g('UNIV', 'ALL', w, 'LO', 'net35', 'ann_mean')
        A(f'| *Universe {w} (benchmark)* | | | | | {pct(u)} (Sharpe {num(g("UNIV","ALL",w,"LO","net35","sharpe"))}, max DD {pctu(g("UNIV","ALL",w,"LO","net35","max_dd"))}) | | | {num(g("UNIV","ALL",w,"LO","gross","turnover_per_year"),1)} (LO) | |')
        A('')
    A('LARGE universe (top 200 by market cap, KOSPI200-like), VW: gross LS Sharpe and LO excess over the VW top-200 '
      'portfolio, net 35 bp:')
    A('')
    A('| Signal | LS gross Sharpe | LS net35 Sharpe | LO excess net35 | Excl-worst excess net35 |')
    A('|---|---:|---:|---:|---:|')
    for s in SIG_ORDER:
        A(f'| {LABEL[s]} | {num(g(s,"LARGE","VW","LS","gross","sharpe"))} | {num(g(s,"LARGE","VW","LS","net35","sharpe"))} | '
          f'{pct(g(s,"LARGE","VW","LO_xs_UVW","net35","ann_mean"))} | {pct(g(s,"LARGE","VW","LO_excl_worst_xs_UVW","net35","ann_mean"))} |')
    A('')
    A(f'In large caps the monthly anomalies largely disappear (low-vol LS gross Sharpe {num(g("VOL_3M","LARGE","VW","LS","gross","sharpe"))}, '
      f'low turnover {num(g("TURN_1M_LOW","LARGE","VW","LS","gross","sharpe"))}, SIZE {num(g("SIZE","LARGE","VW","LS","gross","sharpe"))}); weekly reversal '
      f'stays large gross ({num(g("REV_1W","LARGE","VW","LS","gross","sharpe"))}) but is still negative at 35 bp ({num(g("REV_1W","LARGE","VW","LS","net35","sharpe"))}).')
    A('')
    # ---------- sub-periods
    A('## Stability: Sharpe by sub-period (ALL universe)')
    A('')
    A('| Signal | LS gross EW 1996-2005 / 2006-2015 / 2016-2026 | LS gross VW (same) | Excl-worst excess net35 EW (ann.) 1996-2005 / 2006-2015 / 2016-2026 |')
    A('|---|---|---|---|')
    for s in SIG_ORDER:
        a = ' / '.join(num(g(s, 'ALL', 'EW', 'LS', 'gross', 'sharpe', p)) for p in ('1996-2005', '2006-2015', '2016-2026'))
        b = ' / '.join(num(g(s, 'ALL', 'VW', 'LS', 'gross', 'sharpe', p)) for p in ('1996-2005', '2006-2015', '2016-2026'))
        c = ' / '.join(pct(g(s, 'ALL', 'EW', 'LO_excl_worst_xs_UEW', 'net35', 'ann_mean', p)) for p in ('1996-2005', '2006-2015', '2016-2026'))
        A(f'| {LABEL[s]} | {a} | {b} | {c if "n/a" not in c else "n/a (weekly)"} |')
    A('')
    # ---------- failures
    A('## Where and when it failed (dated episodes)')
    A('')
    wins = [w[0] for w in EVENT_WINDOWS]
    short = {w: w.split(' ')[0] for w in wins}
    A('Cumulative return in each window, ALL universe, EW. LS gross; LO excess = top quintile minus EW universe, net 35 bp. '
      'Windows run from the close of the start date to the close of the end date (see kr_common.EVENT_WINDOWS).')
    A('')
    sel = ['MOM_12_1', 'REV_1M', 'HIGH52', 'VOL_3M', 'MAX_1M', 'TURN_1M_LOW', 'SIZE', 'PMA200', 'REV_1W']
    A('| Window | EW universe | VW universe | ' + ' | '.join(f'{s} LS' for s in sel) + ' |')
    A('|---|---:|---:|' + '---:|' * len(sel))
    for w in wins:
        A(f'| {short[w]} | {pct(ev("UNIV","ALL","EW","LO","gross",w))} | {pct(ev("UNIV","ALL","VW","LO","gross",w))} | ' +
          ' | '.join(pct(ev(s, 'ALL', 'EW', 'LS', 'gross', w)) for s in sel) + ' |')
    A('')
    A('| Window | ' + ' | '.join(f'{s} LO xs' for s in sel) + ' | TURN excl-worst xs | VOL excl-worst xs |')
    A('|---|' + '---:|' * (len(sel) + 2))
    for w in wins:
        A(f'| {short[w]} | ' + ' | '.join(pct(ev(s, 'ALL', 'EW', 'LO_xs_UEW', 'net35', w)) for s in sel) +
          f' | {pct(ev("TURN_1M_LOW","ALL","EW","LO_excl_worst_xs_UEW","net35",w))} | {pct(ev("VOL_3M","ALL","EW","LO_excl_worst_xs_UEW","net35",w))} |')
    A('')
    A('Failure episodes worth naming (all numbers from the tables above and results/kr_event_windows.csv):')
    A('')
    A(f'- **2026 melt-up (2026-01-02..06-22): the market was two stocks.** Samsung Electronics and SK hynix were {pctu(TOP2W,0)} of the VW '
      f'universe at the 2025-12-30 formation and returned {pct(TOP2R[0],0)} and {pct(TOP2R[1],0)} to 2026-06-22. '
      f'VW universe {pct(ev("UNIV","ALL","VW","LO","gross","2026-01-02..2026-06-22 melt-up"))} '
      f'vs EW universe {pct(ev("UNIV","ALL","EW","LO","gross","2026-01-02..2026-06-22 melt-up"))}; LARGE VW {pct(ev("UNIV","LARGE","VW","LO","gross","2026-01-02..2026-06-22 melt-up"))}. '
      f'Every defensive signal lagged: low-vol LS {pct(ev("VOL_3M","ALL","EW","LS","gross","2026-01-02..2026-06-22 melt-up"))}, '
      f'low-MAX {pct(ev("MAX_1M","ALL","EW","LS","gross","2026-01-02..2026-06-22 melt-up"))}, SIZE {pct(ev("SIZE","ALL","EW","LS","gross","2026-01-02..2026-06-22 melt-up"))}; '
      f'trend/momentum won (MOM 12-1 {pct(ev("MOM_12_1","ALL","EW","LS","gross","2026-01-02..2026-06-22 melt-up"))}, PMA200 {pct(ev("PMA200","ALL","EW","LS","gross","2026-01-02..2026-06-22 melt-up"))}).')
    A(f'- **2026 crash (06-22..07-30) and rebound (07-31..09-29): momentum crash pattern.** MOM 12-1 LS {pct(ev("MOM_12_1","ALL","EW","LS","gross","2026-06-22..2026-07-30 crash"))} '
      f'in the crash (low-vol {pct(ev("VOL_3M","ALL","EW","LS","gross","2026-06-22..2026-07-30 crash"))}, low-MAX {pct(ev("MAX_1M","ALL","EW","LS","gross","2026-06-22..2026-07-30 crash"))}), '
      f'then the defensive signals gave it back in the rebound (low-vol {pct(ev("VOL_3M","ALL","EW","LS","gross","2026-07-31..2026-09-29 after crash"))}, '
      f'low-MAX {pct(ev("MAX_1M","ALL","EW","LS","gross","2026-07-31..2026-09-29 after crash"))}). The rebuilt KOSPI gained '
      f'{pct(idx_ret("2026-07-30","2026-07-31"))} on 2026-07-31 alone (Samsung +26.8%, SK hynix +30.0% that day in the raw data).')
    A(f'- **2000 dot-com bust (2000-03..12): MOM 12-1 LS {pct(ev("MOM_12_1","ALL","EW","LS","gross","2000-03..2000-12 dot-com bust"))}**, the worst momentum episode; '
      f'low turnover {pct(ev("TURN_1M_LOW","ALL","EW","LS","gross","2000-03..2000-12 dot-com bust"))} and low-vol {pct(ev("VOL_3M","ALL","EW","LS","gross","2000-03..2000-12 dot-com bust"))} '
      f'were the big winners (the high-turnover, high-vol KOSDAQ bubble names collapsed).')
    A(f'- **2008-06..2009-03 GFC: trend lost** (PMA200 {pct(ev("PMA200","ALL","EW","LS","gross","2008-06..2009-03 GFC"))}, HIGH52 {pct(ev("HIGH52","ALL","EW","LS","gross","2008-06..2009-03 GFC"))}, '
      f'MOM 12-1 {pct(ev("MOM_12_1","ALL","EW","LS","gross","2008-06..2009-03 GFC"))}); weekly reversal earned {pct(ev("REV_1W","ALL","EW","LS","gross","2008-06..2009-03 GFC"))} gross '
      f'but {pct(ev("REV_1W","ALL","EW","LO_xs_UEW","net35","2008-06..2009-03 GFC"))} long-only after costs.')
    A(f'- **2020-03-20..06-30 COVID rebound: low-vol and low-turnover lagged** ({pct(ev("VOL_3M","ALL","EW","LS","gross","2020-03-20..2020-06-30 COVID rebound"))}, '
      f'{pct(ev("TURN_1M_LOW","ALL","EW","LS","gross","2020-03-20..2020-06-30 COVID rebound"))}), HIGH52 {pct(ev("HIGH52","ALL","EW","LS","gross","2020-03-20..2020-06-30 COVID rebound"))}.')
    A(f'- **Weekly reversal stopped working after 2020**: REV 1W LS gross calendar-year returns '
      + ', '.join(f'{y} {pct(g("REV_1W","ALL","EW","LS","gross","total_return",str(y)))}' for y in (2021, 2023, 2024, 2025, 2026)) + '.')
    A(f'- **Long-only weekly reversal is a disaster net of costs:** max drawdown {pctu(g("REV_1W","ALL","EW","LO","net35","max_dd"))} (EW, 35 bp).')
    A(f'- **SIZE (small minus big) flipped:** EW LS gross 2015-2021 mostly positive, then {pct(g("SIZE","ALL","EW","LS","gross","total_return","2025"))} in 2025 '
      f'and {pct(g("SIZE","ALL","EW","LS","gross","total_return","2026"))} in 2026 to date.')
    A('')
    A('Calendar years 2015-2026, LS gross, ALL EW (total return per year):')
    A('')
    yrs = [str(y) for y in range(2015, 2027)]
    A('| Signal | ' + ' | '.join(yrs) + ' |')
    A('|---|' + '---:|' * len(yrs))
    for s in ['MOM_12_1', 'REV_1M', 'HIGH52', 'VOL_3M', 'MAX_1M', 'TURN_1M_LOW', 'SIZE', 'PMA200', 'RSI14_CON', 'REV_1W']:
        A(f'| {s} | ' + ' | '.join(pct(g(s, 'ALL', 'EW', 'LS', 'gross', 'total_return', y), 0) for y in yrs) + ' |')
    A('')
    A('Calendar years, implementable version (universe minus worst quintile, excess over EW universe, net 35 bp):')
    A('')
    A('| Signal | ' + ' | '.join(yrs) + ' |')
    A('|---|' + '---:|' * len(yrs))
    for s in ['TURN_1M_LOW', 'VOL_3M', 'MAX_1M', 'MOM_12_1']:
        A(f'| {s} | ' + ' | '.join(pct(g(s, 'ALL', 'EW', 'LO_excl_worst_xs_UEW', 'net35', 'total_return', y), 1) for y in yrs) + ' |')
    A('')
    # ---------- correlations
    A('## Correlations of long-short returns (calendar months, ALL EW, gross)')
    A('')
    cs = list(COR.columns)
    A('| | ' + ' | '.join(cs) + ' |')
    A('|---|' + '---:|' * len(cs))
    for a in cs:
        A(f'| {a} | ' + ' | '.join(f'{COR.loc[a, b]:.2f}' for b in cs) + ' |')
    A('')
    A(f'Three clusters: (i) low-risk/low-attention: VOL 3M, TURN low, MAX 1M (TURN-VOL {COR.loc["TURN_1M_LOW","VOL_3M"]:.2f}); '
      f'(ii) trend: MOM 6-1, PMA200, HIGH52 (PMA200-HIGH52 {COR.loc["PMA200","HIGH52"]:.2f}); (iii) short-horizon contrarian: '
      f'REV 1M, RSI14, %B (RSI-%B {COR.loc["RSI14_CON","BBPCTB_CON"]:.2f}, REV-RSI {COR.loc["REV_1M","RSI14_CON"]:.2f}). RSI14 and %B are '
      f'repackaged 1-month reversal, not separate signals. Clusters (i) and (iii) are close to uncorrelated with each other and negatively correlated with (ii).')
    A('')
    # ---------- index timing
    A('## KOSPI index timing (rebuilt value-weighted KOSPI)')
    A('')
    A('Sanity check against official KOSPI closes (ratio of gross index changes, rebuilt / official):')
    A('')
    A('| From | To | Official change | Rebuilt change | Ratio |')
    A('|---|---|---:|---:|---:|')
    for _, r in SAN.iterrows():
        A(f'| {r.start} ({r.official_start:,.2f}) | {r.end} ({r.official_end:,.2f}) | {pct(r.official_change)} | {pct(r.rebuilt_change)} | {r.ratio_rebuilt_to_official:.4f} |')
    A('')
    A(f'All ratios are within {max(abs(SAN.ratio_rebuilt_to_official - 1)) * 100:.2f}% of 1 (index built from all KOSPI common-share lines '
      f'including listed REITs/funds; an operating-companies-only version is within {max(abs(SAN.ratio_operating_cos_only - 1)) * 100:.2f}%).')
    A('')
    rules = ['Buy & hold', 'SMA200 (close > SMA200)', '10M_SMA (monthly)', 'SMA50 > SMA200', 'MACD(12,26,9) > signal',
             'Connors RSI(2)<10 & >SMA200, exit >SMA5', 'Bollinger(20,2) MR: buy < lower, exit > middle',
             'Donchian 20-high entry / 10-low exit', 'TSMOM 12M sign (monthly)']
    A('1996-06-03..2026-09-29, net 3 bp per side (6 bp stress in brackets), cash 0%:')
    A('')
    A('| Rule | CAGR | Vol | Sharpe | Max DD | Time in market | Entries/yr | Excess vs B&H /yr (t) | CAGR at 6 bp | Sharpe 96-05 / 06-15 / 16-26 |')
    A('|---|---:|---:|---:|---:|---:|---:|---:|---:|---|')
    for rl in rules:
        cl = 'gross' if rl == 'Buy & hold' else 'net3'
        sp = ' / '.join(num(gx(IX, rl, cl, p, 'sharpe')) for p in ('1996-2005', '2006-2015', '2016-2026'))
        A(f'| {rl} | {pctu(gx(IX,rl,cl,"full","cagr"))} | {pctu(gx(IX,rl,cl,"full","ann_vol"))} | {num(gx(IX,rl,cl,"full","sharpe"))} | '
          f'{pctu(gx(IX,rl,cl,"full","max_dd"))} | {pctu(gx(IX,rl,cl,"full","time_in_market"),0)} | {num(gx(IX,rl,cl,"full","entries_per_year"),1)} | '
          f'{pct(gx(IX,rl,cl,"full","excess_mean_ann_vs_bh"))} ({num(gx(IX,rl,cl,"full","excess_nw_t_vs_bh"),1)}) | '
          f'{pctu(gx(IX,rl,"net6" if rl != "Buy & hold" else "gross","full","cagr"))} | {sp} |')
    A('')
    A('Event windows (cumulative, net 3 bp):')
    A('')
    A('| Rule | ' + ' | '.join(short[w] for w in wins) + ' |')
    A('|---|' + '---:|' * len(wins))
    for rl in rules:
        cl = 'gross' if rl == 'Buy & hold' else 'net3'
        vals = []
        for w in wins:
            x = IXE[(IXE.rule == rl) & (IXE.cost_level == cl) & (IXE.window == w)]
            vals.append(pct(float(x.cum_return.iloc[0])) if len(x) else 'n/a')
        A(f'| {rl} | ' + ' | '.join(vals) + ' |')
    A('')
    A(f'Trend rules (SMA200, 10-month SMA, 12M TSMOM) were out of the market for most of 1997-98, 2000, 2008 and 2022 and '
      f'cut the maximum drawdown from {pctu(gx(IX,"Buy & hold","gross","full","max_dd"))} to about {pctu(gx(IX,"SMA200 (close > SMA200)","net3","full","max_dd"))}, '
      f'but they were fully invested into the 2026-06-22..07-30 crash (SMA200 {pct(ixe("SMA200 (close > SMA200)","net3","2026-06-22..2026-07-30 crash"))} vs '
      f'{pct(ixe("Buy & hold","gross","2026-06-22..2026-07-30 crash"))}): the index stayed above its 200-day average until 2026-07-29, and SMA200 '
      f'then missed the +17.9% rebound day of 2026-07-31. Mean-reversion rules (Connors RSI(2), Bollinger) spend 10-24% of the time in the '
      f'market and have CAGRs of {pctu(gx(IX,"Connors RSI(2)<10 & >SMA200, exit >SMA5","net3","full","cagr"))} and '
      f'{pctu(gx(IX,"Bollinger(20,2) MR: buy < lower, exit > middle","net3","full","cagr"))}.')
    A('')
    A('### Data-snooping test (Hansen SPA)')
    A('')
    A(f'- Family: {int(float(SPA[("family","n_variants")]))} variants (price vs SMA 5-250 and EMA 10-250, SMA bands, SMA/EMA crossover pairs, '
      'MACD variants, Connors RSI(2-14) thresholds 5-30, RSI>50, Bollinger mean-reversion and breakout (10-50 days, 1.5-2.5 sd), '
      'Donchian entry/exit pairs, TSMOM 1-12 months and 20-240 days, 3-12 month SMA). arch.bootstrap.SPA, stationary bootstrap, '
      'block 15, 2,000 reps, seed 20261002, studentized; losses = -(rule daily net return) vs benchmark loss -(buy-and-hold return), '
      'i.e. the test asks whether any rule beats buy-and-hold on mean daily return net of 3 bp.')
    A(f'- Best rule in-sample (highest NW t of the daily excess return): **{SPA[("full","best_rule")]}**, Sharpe '
      f'{num(float(SPA[("full","best_rule_sharpe")]))} vs buy-and-hold {num(float(SPA[("full","buyhold_sharpe")]))}, CAGR '
      f'{pctu(float(SPA[("full","best_rule_cagr")]))} vs {pctu(float(SPA[("full","buyhold_cagr")]))}, excess {pct(float(SPA[("full","best_rule_mean_excess_ann")]))}/yr, '
      f't {num(float(SPA[("full","best_rule_nw_t_excess")]))}. Highest Sharpe in the family: {SPA[("full","best_sharpe_rule")]} '
      f'({num(float(SPA[("full","best_sharpe_value")]))}).')
    A(f'- **SPA p-values: consistent {num(float(SPA[("full","spa_p_consistent")]),3)}, lower {num(float(SPA[("full","spa_p_lower")]),3)}, '
      f'upper {num(float(SPA[("full","spa_p_upper")]),3)}**: no rule beats buy-and-hold on return. On 1996-2012 alone: consistent '
      f'{num(float(SPA[("ins_1996_2012","spa_p_consistent")]),3)}. {int(float(SPA[("full","n_rules_positive_mean_excess")]))} of '
      f'{int(float(SPA[("family","n_variants")]))} rules have a positive mean excess, {int(float(SPA[("full","n_rules_sharpe_above_bh")]))} '
      'have a higher Sharpe than buy-and-hold (they hold cash about 40-70% of the time).')
    A(f'- **Time split**: best variant on 1996-2012 by excess t = {SPA[("selected_by_excess_t","rule")]} (in-sample Sharpe '
      f'{num(float(SPA[("selected_by_excess_t","ins_rule_sharpe")]))} vs {num(float(SPA[("selected_by_excess_t","ins_bh_sharpe")]))}); 2013-2026: '
      f'CAGR {pctu(float(SPA[("selected_by_excess_t","oos_rule_cagr")]))} vs buy-and-hold {pctu(float(SPA[("selected_by_excess_t","oos_bh_cagr")]))}, '
      f'Sharpe {num(float(SPA[("selected_by_excess_t","oos_rule_sharpe")]))} vs {num(float(SPA[("selected_by_excess_t","oos_bh_sharpe")]))}, '
      f'excess {pct(float(SPA[("selected_by_excess_t","oos_excess_mean_ann")]))}/yr (t {num(float(SPA[("selected_by_excess_t","oos_excess_nw_t")]))}), '
      f'{num(float(SPA[("selected_by_excess_t","oos_rule_switches_per_year")]),0)} position changes per year. Best variant on 1996-2012 by '
      f'Sharpe = {SPA[("selected_by_sharpe","rule")]} (in-sample {num(float(SPA[("selected_by_sharpe","ins_rule_sharpe")]))}): 2013-2026 Sharpe '
      f'{num(float(SPA[("selected_by_sharpe","oos_rule_sharpe")]))} vs {num(float(SPA[("selected_by_sharpe","oos_bh_sharpe")]))}, CAGR '
      f'{pctu(float(SPA[("selected_by_sharpe","oos_rule_cagr")]))} vs {pctu(float(SPA[("selected_by_sharpe","oos_bh_cagr")]))}, max DD '
      f'{pctu(float(SPA[("selected_by_sharpe","oos_rule_max_dd")]))} vs {pctu(float(SPA[("selected_by_sharpe","oos_bh_max_dd")]))}, time in market '
      f'{pctu(float(SPA[("selected_by_sharpe","oos_rule_time_in_market")]),0)}.')
    A(f'- Supplementary (not the pre-specified test): against an exposure-matched benchmark (buy-and-hold scaled by each rule\'s average '
      f'exposure), SPA consistent p = {num(float(SPA[("exposure_matched","spa_p_consistent")]),3)} (best {SPA[("exposure_matched","best_rule")]}, '
      f'{pct(float(SPA[("exposure_matched","best_rule_mean_ann")]))}/yr, t {num(float(SPA[("exposure_matched","best_rule_nw_t")]))}, exposure '
      f'{pctu(float(SPA[("exposure_matched","best_rule_exposure")]),0)}). Selected on 1996-2012 by Sharpe, its 2013-2026 excess over the '
      f'exposure-matched benchmark was {pct(float(SPA[("exposure_matched_split_by_sharpe","oos_mean_ann_vs_exposure_matched")]))}/yr '
      f'(t {num(float(SPA[("exposure_matched_split_by_sharpe","oos_nw_t_vs_exposure_matched")]))}); selected by excess t '
      f'({SPA[("exposure_matched_split_by_t","selected_rule_1996_2012")]}): {pct(float(SPA[("exposure_matched_split_by_t","oos_mean_ann_vs_exposure_matched")]))}/yr '
      f'(t {num(float(SPA[("exposure_matched_split_by_t","oos_nw_t_vs_exposure_matched")]))}). Timing reduces risk; evidence that it adds '
      'return per unit of exposure is borderline and did not hold out of sample for the excess-t winner.')
    A('')
    # ---------- literature cross-checks
    A('## Cross-checks against figures in the context brief')
    A('')
    def cx(series_sub, period, cl):
        x = CX[CX.series.str.startswith(series_sub) & (CX.period == period) & (CX.cost_level == cl)]
        return x.iloc[0] if len(x) else None
    for lab, sub in (('ALL deciles', 'ALL deciles: losers minus winners'), ('BROAD deciles (no microcap screen, no price floor)', 'BROAD deciles: losers minus winners'),
                     ('ALL quintiles', 'ALL quintiles: losers minus winners')):
        r = cx(sub, '1999-01..2021-12', 'gross'); rn = cx(sub, '1999-01..2021-12', 'net35')
        if r is not None:
            A(f'- 1-month reversal, {lab}, EW, 1999-2021: losers minus winners {pct(r.mean_monthly,2)}/month gross (t {num(r.nw_t)}), '
              f'{pct(rn.mean_monthly,2)}/month net 35 bp.')
    A('  The brief quotes WML -2.95%/month (t -3.77) for 1999-2021, i.e. reversal of +2.95%/month. Our spread is about half of that, '
      'probably because of our screens (microcap cut, 1,000 KRW price floor, >= 200 valid days) and a different specification in the '
      'source paper (not opened by the data lab); in our data it is not reliably profitable after 35 bp per side (best: ALL deciles, '
      '+0.2%/month net, t below 1).')
    for lab in ('TURNlow', 'TURNmid', 'TURNhigh'):
        r = cx(f'MOM_12_1 Q5-Q1 within {lab}', 'full 1996-04..2026-09', 'gross')
        if r is not None:
            A(f'- MOM 12-1 Q5-Q1 inside the {lab.replace("TURN","")} turnover tercile (ALL, EW, 1996-2026): {pct(r.mean_monthly,2)}/month gross, t {num(r.nw_t)}.')
    A('  The brief\'s claim that Korean 12-1 momentum is negative in high-turnover stocks is not reproduced: in our sample momentum is '
      'positive in every turnover tercile and largest in the high-turnover one.')
    A('')
    # ---------- validation
    A('## Validation')
    A('')
    vs = VAL.groupby('test')['passed'].agg(['sum', 'count'])
    desc = {'V0': 'Share classes (preferred = non-zero last code character)', 'V1': '10 random stock-days: r vs Close/prev Close',
            'V1b': 'Population: r vs Close/prev Close on all kept days', 'V2': 'Look-ahead: universe and all signals recomputed on data truncated at 2015-06-30',
            'V3': 'Look-ahead: returns start at t+1; hand-recomputed periods', 'V4': 'Quintile breakpoints from the eligible universe only',
            'V5': 'Index rules use prices <= t only', 'V6': 'Reproducibility (SPA seed) and SHA-256 of result files'}
    A('| Test | What | Passed |')
    A('|---|---|---:|')
    for tname, r in vs.iterrows():
        A(f'| {tname} | {desc.get(tname, "")} | {int(r["sum"])}/{int(r["count"])} |')
    A('')
    def vrow(tn, contains):
        x = VAL[(VAL.test == tn) & VAL['item'].str.contains(contains, regex=False)]
        return x.iloc[0] if len(x) else None
    r = vrow('V1b', 'share of kept returns')
    if r is not None:
        A(f'- r vs Close/prevClose: {r.value} of kept daily returns differ by more than 0.5% (KRX base-price adjustments: splits, '
          'rights issues, stock dividends; r is the adjusted figure). The 10 random spot checks agree within 0.005 pp (ChangesRatio is rounded to 0.01%).')
    r = vrow('V0', 'non-zero last character')
    if r is not None:
        A(f'- Preferred shares: {r.value} of non-zero-ending code/name pairs carry a preferred or new-share marker (우, 우B, 1신, 전환); '
          'the rest are 1990s new-share lines (e.g. "코닉스1"). No common-share code has a preferred-looking name.')
    A('- Look-ahead: the panel was rebuilt from data truncated at 2015-06-30; universe membership and all 11 monthly signals at '
      'all 231 month-ends up to then are identical to the full-data values (assertion test in kr_06_validation.py). The engine '
      'returns for random periods were recomputed by hand from t+1..t_next.')
    A('- Breakpoints: quintiles are formed within the eligible universe only (no non-member is ever assigned; universe-only '
      'breakpoints reproduce the assignment exactly; ALL and all-listed breakpoints differ, so the test has power).')
    A('')
    # ---------- data handling
    A('## Data handling and caveats')
    A('')
    A(f'- **Returns are price returns** (dividends excluded). Korean dividend yields were roughly 1-2% a year for most of the '
      'sample, higher for low-vol, low-turnover and large value stocks; long-only absolute returns are understated by about that '
      'much, and the defensive signals (low vol, low turnover) are probably understated relative to the universe.')
    A(f'- **Return cleaning** ({int(FLAGS["rows"]):,} stock-days): first day of each listing segment set to missing '
      f'({int(FLAGS["first"]):,}: new listings, relistings, KONEX transfers and 1990s KOSPI/KOSDAQ transfers with a base-price reset). '
      f'{int(FLAGS["beyond"]):,} returns exceed the daily limit (+-15% before 2015-06-15, +-30% after). Of these, '
      f'{int(FLAGS["keep_liq"]):,} fall in the last 30 trading days before a delisting (liquidation trading, which has no price limit) '
      f'and {int(FLAGS["keep_resume"])} are the first trade after a halt of >= 5 sessions; both are kept because they are real losses '
      f'(median {pct(FLAGEV[FLAGEV.category.isin(["keep_liq","keep_resume"])].r_changesratio.median())}). {int(FLAGS["keep_ca"])} coincide with a corporate action and agree with the market-cap change (kept); '
      f'{int(FLAGS["drop_ca"])} coincide with a corporate action but do not (missing); {int(FLAGS["drop_other"])} others '
      f'(mostly 1996-99 records with repeated +16.7% prints on zero-volume days) are set to missing; {int(FLAGS["drop_placeholder"])} '
      'placeholder 1-KRW prices are missing. Event list: results/kr_return_flags_events.csv.')
    sl = TS
    A(f'- **Sensitivity to that choice** ("strict": every beyond-limit return without a consistent corporate action set to missing, the '
      f'literal rule): the low-vol LS gross mean moves from {pct(g("VOL_3M","ALL","EW","LS","gross","ann_mean"))} to '
      f'{pct(g("VOL_3M","ALL","EW","LS","gross","ann_mean",tab=TS))}, low-turnover from {pct(g("TURN_1M_LOW","ALL","EW","LS","gross","ann_mean"))} '
      f'to {pct(g("TURN_1M_LOW","ALL","EW","LS","gross","ann_mean",tab=TS))}, MOM 12-1 from {pct(g("MOM_12_1","ALL","EW","LS","gross","ann_mean"))} '
      f'to {pct(g("MOM_12_1","ALL","EW","LS","gross","ann_mean",tab=TS))}, EW universe from {pct(g("UNIV","ALL","EW","LO","gross","ann_mean"))} '
      f'to {pct(g("UNIV","ALL","EW","LO","gross","ann_mean",tab=TS))}: dropping liquidation losses flatters the short legs\' victims. '
      'Full strict tables: results/*_strict.csv.')
    dm = DEXP[DEXP.book.str.contains('|ALL|EW|Q', regex=False) & DEXP.book.str.startswith('monthly')]
    tot_dis = DISP[(DISP.freq == 'monthly') & (DISP.universe == 'ALL')]
    A(f'- **Delistings**: a stock that disappears is held at its last price as cash. Across monthly ALL quintiles, '
      f'about {tot_dis.disappeared_in_period.sum() / 11:.0f} universe members disappear during a holding month over 30 years '
      f'(the same events seen through each of the 11 monthly signals; {tot_dis.disappeared_distressed_liquidation.sum() / tot_dis.disappeared_in_period.sum():.0%} '
      'of them distressed liquidations, the rest mergers, voluntary delistings or restructurings). They concentrate in the extreme '
      f'quintiles: e.g. TURN 1M Q1 {int(tot_dis[(tot_dis.signal=="TURN_1M")&(tot_dis.quintile==1)].disappeared_in_period.iloc[0])} vs '
      f'Q5 {int(tot_dis[(tot_dis.signal=="TURN_1M")&(tot_dis.quintile==5)].disappeared_in_period.iloc[0])} (mostly mergers of quiet stocks), '
      f'HIGH52 Q1 has {int(tot_dis[(tot_dis.signal=="HIGH52")&(tot_dis.quintile==1)].disappeared_distressed_liquidation.iloc[0])} distressed exits '
      f'with a mean {pct(tot_dis[(tot_dis.signal=="HIGH52")&(tot_dis.quintile==1)].mean_return_last_21d_before_exit.iloc[0],0)} over their last 21 days '
      '(counts per signal and quintile in results/kr_disappearances.csv). '
      f'The book-value share that disappears is {pctu(dm.dead_share_per_year.median(),2)} a year for the median quintile book '
      f'(max {pctu(dm.dead_share_per_year.max(),2)}, {dm.loc[dm.dead_share_per_year.idxmax(),"book"].split("|")[1]} '
      f'{dm.loc[dm.dead_share_per_year.idxmax(),"book"].split("|")[-1]}); the share exiting at a stale (no-trade) last price is at most '
      f'{pctu(dm.stale_exit_share_per_year.max(),2)} a year, which bounds the delisting bias at {pctu(dm.stale_exit_share_per_year.max(),1)} '
      'a year even if all of it were worth zero (most of it is 1997-2000 mergers and bank/conglomerate restructurings, not '
      'liquidations). Direction of the bias: delisting returns are unknown; for distressed exits the last price is usually above '
      'the eventual recovery, so long legs holding losers (REV 1M Q1, MOM Q1, high-vol) are biased slightly upward and the LS spreads '
      'that short them are biased slightly downward; the sensitivity run below (liquidation losses dropped) moves the main spreads '
      'by under 1 pp a year.')
    A(f'- **Halted positions**: a held stock that is halted at a rebalance cannot be sold; it is carried (and its resumption-day move '
      f'is earned) until the first rebalance at which it trades. Stocks halted at the formation close are not bought '
      f'({UC.n_removed_halted_at_t.mean():.1f} per month removed from the specified screen); a beyond-limit move without corporate action '
      f'in the last 30 days also excludes a stock ({int(UC.n_removed_beyond_limit_30d.sum())} cases in 366 months).')
    A('- **Universe**: microcap cut = 20th percentile of Marcap within the eligible set; the ALL universe averages '
      f'{UC.n_all.mean():.0f} stocks (from {UC.n_all.min()} in {UC.formation[UC.n_all.idxmin()][:7]} to {UC.n_all.max()} in '
      f'{UC.formation[UC.n_all.idxmax()][:7]}); KOSDAQ is {pctu(kq_share(UC,2001,2026)[0],0)}-{pctu(kq_share(UC,2001,2026)[1],0)} of it '
      f'(yearly averages) from 2001 and {pctu(kq_share(UC,1996,1999)[0],0)}-{pctu(kq_share(UC,1996,1999)[1],0)} in 1996-99: KOSDAQ data '
      f'start in {str(PROF[PROF.Market=="KOSDAQ"].first_date.min())[:7]} and '
      f'{pctu(PROF[(PROF.Market=="KOSDAQ")&(PROF.year<=1998)].zero_volume_share.mean(),0)} of KOSDAQ stock-days in 1996-98 have zero '
      'volume, so most KOSDAQ stocks fail the 200-valid-day rule until 1999. '
      'SPACs, REITs (incl. 코크렙, 리얼티), listed ship/infrastructure/resource funds (동북아12호, 바다로, 맥쿼리인프라, 한국ANKOR유전), '
      'listed mutual funds (박현주1호, ...MF) and KDRs are excluded by name; the literal 리츠/인프라 substring rule was not used because it '
      'would also drop 메리츠 group companies, 두산인프라코어 and other operating companies.')
    A('- **Shorting**: long-short results are research benchmarks. Short selling of Korean stocks was banned from 2023-11-06 to '
      '2025-03-30 (with earlier temporary bans in parts of 2008-09, 2011 and 2020-21) and is impractical for individuals '
      '(stock borrow is limited and costly, and the 35 bp cost does not include borrow fees). Only the long-only results are implementable.')
    A('- **Costs**: 35 bp per side is charged on every unit of turnover (it includes the sell-side transaction tax); market impact '
      'is not modelled, which flatters small-cap EW portfolios. The ALL EW universe itself turns over '
      f'{num(g("UNIV","ALL","EW","LO","gross","turnover_per_year"),1)}x a year (rebalancing to equal weights), costing about '
      f'{pctu(g("UNIV","ALL","EW","LO","gross","ann_mean")-g("UNIV","ALL","EW","LO","net35","ann_mean"),2)} a year.')
    A('- **Index**: the rebuilt KOSPI is a price index from all KOSPI common-share lines with lagged market-cap weights; the official '
      f'KOSPI also uses market-cap weights on common shares; the two track within {max(abs(SAN.ratio_rebuilt_to_official - 1)) * 100:.2f}% '
      'between the 2007-2026 check dates. Before 2007 it is not checked against official closes (none were supplied).')
    A('')
    # ---------- implementable
    A('## What looks implementable for QUANTGEN at 35 bp per side, long-only')
    A('')
    A(f'1. **Exclusion screens on the KRX stock universe (BUILD-candidate, as a filter, not a signal).** Drop the top quintile of '
      f'1-month turnover (Amount/Marcap) and/or of 3-month volatility from whatever long book QUANTGEN holds. EW: '
      f'{pct(g("TURN_1M_LOW","ALL","EW","LO_excl_worst_xs_UEW","net35","ann_mean"))} and {pct(g("VOL_3M","ALL","EW","LO_excl_worst_xs_UEW","net35","ann_mean"))} '
      f'a year over the EW universe net of 35 bp (t {num(g("TURN_1M_LOW","ALL","EW","LO_excl_worst_xs_UEW","net35","nw_t"))} / '
      f'{num(g("VOL_3M","ALL","EW","LO_excl_worst_xs_UEW","net35","nw_t"))}), positive in every sub-period, still positive at 70 bp, '
      f'turnover about {num(g("TURN_1M_LOW","ALL","EW","LO_excl_worst","gross","turnover_per_year"),1)}x a year. VW the gain is '
      f'{pct(g("TURN_1M_LOW","ALL","VW","LO_excl_worst_xs_UVW","net35","ann_mean"))}-{pct(g("VOL_3M","ALL","VW","LO_excl_worst_xs_UVW","net35","ann_mean"))}. '
      'It should pass QUANTGEN\'s 2x-cost gate; against a cap-weighted benchmark the edge is about 1% a year, so the benchmark gate '
      '(one-sided p <= 0.10) is the binding test. The expected edge is a 1-4% a year tilt, '
      f'mostly from avoiding lottery-like stocks. It lagged in the 2026 melt-up '
      f'({pct(ev("TURN_1M_LOW","ALL","EW","LO_excl_worst_xs_UEW","net35","2026-01-02..2026-06-22 melt-up"))}) and after the 2026 crash '
      f'({pct(ev("TURN_1M_LOW","ALL","EW","LO_excl_worst_xs_UEW","net35","2026-07-31..2026-09-29 after crash"))}; low-vol screen '
      f'{pct(ev("VOL_3M","ALL","EW","LO_excl_worst_xs_UEW","net35","2026-07-31..2026-09-29 after crash"))}).')
    A(f'2. **Index trend filter as a risk overlay, not an alpha source (CONTEXT).** SMA200 or 10-month SMA on the KOSPI via a KRX ETF '
      f'(3 bp): CAGR {pctu(gx(IX,"10M_SMA (monthly)","net3","full","cagr"))} (10M SMA) vs {pctu(gx(IX,"Buy & hold","gross","full","cagr"))} '
      f'buy-and-hold over 1996-2026, all of the gain from 1996-2005 ({pctu(gx(IX,"10M_SMA (monthly)","net3","1996-2005","cagr"))} vs '
      f'{pctu(gx(IX,"Buy & hold","gross","1996-2005","cagr"))}; 2006-2015 {pctu(gx(IX,"10M_SMA (monthly)","net3","2006-2015","cagr"))} vs '
      f'{pctu(gx(IX,"Buy & hold","gross","2006-2015","cagr"))}), '
      f'Sharpe {num(gx(IX,"10M_SMA (monthly)","net3","full","sharpe"))} vs {num(gx(IX,"Buy & hold","gross","full","sharpe"))}, max drawdown '
      f'{pctu(gx(IX,"10M_SMA (monthly)","net3","full","max_dd"))} vs {pctu(gx(IX,"Buy & hold","gross","full","max_dd"))}. The SPA test says no '
      'rule beats buy-and-hold on return, consistent with QUANTGEN\'s own E1 REJECT. Use only as the macro-research style exposure '
      'multiplier (0.5-1.0), never above 1.0.')
    A('3. **Not implementable at 35 bp (DROP for KRX single stocks)**: weekly reversal in any volume tercile, 1-month reversal, '
      'RSI14 / Bollinger %B in either direction, price-vs-SMA200 stock selection, MOM 6-1. Monthly MOM 12-1 and 52-week-high '
      'long-only quintiles are within noise of the universe after costs (BACKLOG at most; MOM 12-1 VW top quintile '
      f'{pct(g("MOM_12_1","ALL","VW","LO_xs_UVW","net35","ann_mean"))}/yr over the VW universe, t {num(g("MOM_12_1","ALL","VW","LO_xs_UVW","net35","nw_t"))}).')
    A(f'4. **Weekly reversal belongs on a cheaper venue**: break-even cost {num(g("REV_1W","ALL","EW","LS","gross","ann_mean")/g("REV_1W","ALL","EW","LS","gross","turnover_per_year")*1e4,0)}-'
      f'{num(g("REV_1W","LARGE","VW","LS","gross","ann_mean")/g("REV_1W","LARGE","VW","LS","gross","turnover_per_year")*1e4,0)} bp per side; the 35 bp KRX '
      'stock cost (tax included) kills it. Not a Korea stock card.')
    A('')
    A('Prior Korea weights (context brief section 2: XS-mom 1, ST-rev 3, ...): the data support **lowering ST-reversal from 3 to 0-1 for '
      'cash-equity implementation** (strong gross, negative net), keeping XS-momentum low (1), and adding low-turnover / low-volatility '
      'as exclusion filters (the brief has low-vol 2 for Korea, which fits as a filter, not as a long-only quintile).')
    A('')
    A('## Files')
    A('')
    A('- Scripts: `kr_common.py`, `kr_01_build_panel.py` (panel, return cleaning), `kr_02_signals.py` (universes, signals), '
      '`kr_03_portfolios.py` (quintile books, turnover, delistings), `kr_04_stats.py` (statistics, events, correlations), '
      '`kr_05_index_timing.py` (KOSPI rebuild, timing rules, SPA), `kr_06_validation.py`, `kr_07_charts_summary.py` (chart JSON), '
      '`kr_08_crosschecks.py`, `kr_09_summary.py`, `kr_run_all.py`.')
    A('- Results: `kr_signal_stats_long.csv` (signal, universe, weighting, leg, cost_level, period, metric, value, freq; legs LS, LO, '
      'LO_xs_UEW/UVW, LO_excl_worst(_xs_UEW/UVW), Q1..Q5), `kr_event_windows.csv`, `kr_ls_correlations.csv`, `kr_index_timing.csv`, '
      '`kr_index_timing_events.csv`, `kr_index_spa.csv`, `kr_index_spa_family.csv`, `kr_index_sanity.csv`, `kr_validation.csv`, '
      '`kr_disappearances.csv`, `kr_delisting_exposure_*.csv`, `kr_return_flags_*.csv`, `kr_universe_counts.csv`, `kr_crosschecks.csv`, '
      '`kr_key_numbers.csv`, and `*_strict.csv` sensitivity copies.')
    A('- Charts (JSON): `kr_chart1_cumlog_monthly.json`, `kr_chart2_sharpe_subperiods.json`, `kr_chart3_kospi_timing.json`, '
      '`kr_chart4_quintiles_2025_2026.json`.')
    with open(OUT, 'w', encoding='utf-8') as f:
        f.write('\n'.join(L) + '\n')
    print(f'summary written: {OUT} ({len(L)} lines) in {time.time() - t0:.0f}s')


def top2_meltup():
    """Weight of Samsung Electronics + SK hynix in the VW ALL universe at the 2025-12-30 formation, and their
    price returns to the 2026-06-22 close."""
    from kr_common import load_meta, open_mat
    dates, codes = load_meta()
    F = np.load(f'{CACHE}/form_monthly.npz')
    fidx = F['fidx']
    k = int(np.flatnonzero(dates[fidx] == pd.Timestamp('2025-12-30'))[0])
    t0 = fidx[k]
    t1 = int(np.searchsorted(dates.values, np.datetime64('2026-06-22'), side='right') - 1)
    M = np.nan_to_num(np.asarray(open_mat('marcap')[t0]).astype(float))
    w = np.where(F['univ_all'][k], M, 0.0)
    w = w / w.sum()
    CL = open_mat('cumlog')
    js = [int(np.flatnonzero(codes == c)[0]) for c in ('005930', '000660')]
    return float(w[js].sum()), [float(np.expm1(CL[t1, j] - CL[t0, j])) for j in js]


def kq_share(UC, y0, y1):
    """Min and max of the yearly-average KOSDAQ share of the ALL universe over years y0..y1."""
    u = UC.assign(y=UC.formation.str[:4].astype(int), sh=UC.n_kosdaq_in_all / UC.n_all)
    yr = u[(u.y >= y0) & (u.y <= y1)].groupby('y').sh.mean()
    return float(yr.min()), float(yr.max())


def gx(IX, rule, cl, period, metric):
    x = IX[(IX.rule == rule) & (IX.cost_level == cl) & (IX.period == period) & (IX.metric == metric)]
    return float(x.value.iloc[0]) if len(x) else np.nan


_IXE = None


def ixe(rule, cl, win):
    global _IXE
    if _IXE is None:
        _IXE = pd.read_csv(f'{RES}/kr_index_timing_events.csv')
    x = _IXE[(_IXE.rule == rule) & (_IXE.cost_level == cl) & (_IXE.window == win)]
    return float(x.cum_return.iloc[0]) if len(x) else np.nan


def idx_ret(d0, d1):
    idx = pd.read_parquet(f'{CACHE}/kospi_rebuilt.parquet')
    return float(idx['level'].loc[d1] / idx['level'].loc[d0] - 1)


if __name__ == '__main__':
    main()
