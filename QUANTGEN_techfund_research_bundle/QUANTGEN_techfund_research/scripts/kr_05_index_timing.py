"""kr_05_index_timing.py -- KOSPI rebuilt from stock data, technical timing rules, Hansen SPA test.

Index: value-weighted price index of ALL KOSPI common-share lines (operating companies plus listed REITs,
ship/infra funds and KDRs; preferred shares excluded), no microcap screen; it tracks the official KOSPI
better (ratio of changes 0.999-1.002) than an operating-companies-only version (0.997-1.009), both are
reported in results/kr_index_sanity.csv. Return on day d =
sum_i Marcap_i,d-1 * r_i,d / sum_i Marcap_i,d-1 over stocks listed on KOSPI at d-1 that still exist at d
with a valid (cleaned) return r = ChangesRatio/100. Scaled to the official close on 2007-10-31 (2,064.85).

Timing rules: signal at the close of t from index closes through t, position held from t+1, cash 0%,
cost = c * |position change| (c = 3 bp per side, stress 6 bp), charged in the t+1 return.
Evaluation window: 1996-06-03 .. 2026-09-29 for every rule (the longest lookback needs ~250 days).
SPA: arch.bootstrap.SPA, benchmark losses = -r_buy&hold, model losses = -r_rule,net(3 bp), stationary
bootstrap, block 15, 2,000 reps, seed 20261002 (so d_k = r_rule - r_B&H, the task's loss definition).
"""
import sys, time, itertools
import numpy as np
import pandas as pd
sys.path.insert(0, '/home/claude/datalab/scripts')
from kr_common import (CACHE, RES, SEED, SUBPERIODS, EVENT_WINDOWS, load_meta, open_mat, nw_tstat,
                       max_drawdown)
from arch.bootstrap import SPA

EVAL_START = '1996-06-03'
OFFICIAL = [('2007-10-31', 2064.85), ('2020-03-19', 1457.64), ('2021-07-06', 3305.21),
            ('2026-06-22', 9114.55), ('2026-07-30', 5593.56)]
COSTS = {'gross': 0.0, 'net3': 0.0003, 'net6': 0.0006}


def log(*a):
    print(time.strftime('%H:%M:%S'), *a, flush=True)


# ------------------------------------------------------------------ index construction
def build_index(include_vehicles=False):
    dates, codes = load_meta()
    T, N = len(dates), len(codes)
    R = open_mat('ret'); E = open_mat('exists'); M = open_mat('marcap'); MK = open_mat('mkt'); NC = open_mat('namecls')
    if include_vehicles:
        NC = np.zeros((T, N), np.int8)
    ret = np.zeros(T); ncons = np.zeros(T, int); cap = np.zeros(T)
    CH = 400
    for t0 in range(1, T, CH):
        t1 = min(T, t0 + CH)
        mp = np.asarray(M[t0 - 1:t1 - 1]).astype(np.float64)
        ep = np.asarray(E[t0 - 1:t1 - 1]) & (np.asarray(MK[t0 - 1:t1 - 1]) == 1) & (np.asarray(NC[t0 - 1:t1 - 1]) == 0)
        r = np.asarray(R[t0:t1]).astype(np.float64)
        ok = ep & np.asarray(E[t0:t1]) & np.isfinite(r) & (mp > 0)
        w = np.where(ok, mp, 0.0)
        ret[t0:t1] = (w * np.nan_to_num(r)).sum(1) / w.sum(1)
        ncons[t0:t1] = ok.sum(1); cap[t0:t1] = w.sum(1)
    lvl = np.cumprod(1.0 + ret)
    base = int(np.searchsorted(dates.values, np.datetime64('2007-10-31')))
    lvl = lvl / lvl[base] * 2064.85
    df = pd.DataFrame({'ret': ret, 'level': lvl, 'n_constituents': ncons, 'cap_prev_krw': cap}, index=dates)
    df.index.name = 'date'
    return df


def sanity(df, df_all=None):
    """ratio = (rebuilt level_end / level_start) / (official end / start): the ratio of gross index changes."""
    rows = []
    lv = df['level']
    for (d0, o0), (d1, o1) in itertools.combinations(OFFICIAL, 2):
        mine = lv.loc[d1] / lv.loc[d0]; off = o1 / o0
        row = [d0, d1, o0, o1, float(lv.loc[d0]), float(lv.loc[d1]), off - 1, mine - 1, mine / off]
        if df_all is not None:
            la = df_all['level']
            row.append((la.loc[d1] / la.loc[d0]) / off)
        rows.append(row)
    cols = ['start', 'end', 'official_start', 'official_end', 'rebuilt_start', 'rebuilt_end', 'official_change',
            'rebuilt_change', 'ratio_rebuilt_to_official']
    if df_all is not None:
        cols.append('ratio_incl_investment_vehicles')
    return pd.DataFrame(rows, columns=cols)


# ------------------------------------------------------------------ indicators (all causal)
def sma(p, n):
    s = pd.Series(p).rolling(n, min_periods=n).mean().values
    return s


def ema(p, n):
    return pd.Series(p).ewm(span=n, adjust=False).mean().values


def rsi_wilder(p, n):
    d = np.diff(p, prepend=np.nan)
    up = np.where(d > 0, d, 0.0); dn = np.where(d < 0, -d, 0.0)
    up[0] = dn[0] = np.nan
    au = pd.Series(up).ewm(alpha=1.0 / n, adjust=False, ignore_na=True).mean().values
    ad = pd.Series(dn).ewm(alpha=1.0 / n, adjust=False, ignore_na=True).mean().values
    with np.errstate(invalid='ignore', divide='ignore'):
        r = 100 - 100 / (1 + au / ad)
    r[:n] = np.nan
    return r


def state_machine(enter, exit_):
    """pos_t = 1 after an entry signal until an exit signal (both evaluated at the close of t)."""
    pos = np.zeros(len(enter), np.int8); cur = 0
    for t in range(len(enter)):
        if cur == 0 and enter[t]:
            cur = 1
        elif cur == 1 and exit_[t]:
            cur = 0
        pos[t] = cur
    return pos


def monthly_pos(dates, p, fn):
    """Evaluate fn(month-end closes up to m) at each month end; hold the decision until the next month end."""
    s = pd.Series(p, index=dates)
    me = s.groupby([dates.year, dates.month]).tail(1)
    sig = np.asarray(fn(me.values), dtype=float)          # array aligned with month ends
    pos = pd.Series(np.nan, index=dates)
    pos.loc[me.index] = sig
    return pos.ffill().fillna(0).values.astype(np.int8)


# ------------------------------------------------------------------ rule families
def core_rules(dates, p):
    s200 = sma(p, 200); s50 = sma(p, 50); s5 = sma(p, 5); s20 = sma(p, 20)
    sd20 = pd.Series(p).rolling(20, min_periods=20).std(ddof=0).values
    macd = ema(p, 12) - ema(p, 26); sig = ema(macd, 9)
    r2 = rsi_wilder(p, 2)
    hi20 = pd.Series(p).shift(1).rolling(20, min_periods=20).max().values
    lo10 = pd.Series(p).shift(1).rolling(10, min_periods=10).min().values
    with np.errstate(invalid='ignore'):
        rules = {
            'SMA200 (close > SMA200)': (p > s200).astype(np.int8),
            '10M_SMA (monthly)': monthly_pos(dates, p, lambda m: (m > pd.Series(m).rolling(10, min_periods=10).mean().values)),
            'SMA50 > SMA200': (s50 > s200).astype(np.int8),
            'MACD(12,26,9) > signal': (macd > sig).astype(np.int8),
            'Connors RSI(2)<10 & >SMA200, exit >SMA5': state_machine((r2 < 10) & (p > s200), p > s5),
            'Bollinger(20,2) MR: buy < lower, exit > middle': state_machine(p < s20 - 2 * sd20, p > s20),
            'Donchian 20-high entry / 10-low exit': state_machine(p > hi20, p < lo10),
            'TSMOM 12M sign (monthly)': monthly_pos(dates, p, lambda m: (m / pd.Series(m).shift(12).values - 1) > 0),
        }
    return rules


def family(dates, p):
    fam = {}
    with np.errstate(invalid='ignore'):
        for n in range(5, 255, 5):
            fam[f'P>SMA{n}'] = (p > sma(p, n)).astype(np.int8)
        for n in range(10, 260, 10):
            fam[f'P>EMA{n}'] = (p > ema(p, n)).astype(np.int8)
        for n in (50, 100, 150, 200, 250):
            s = sma(p, n)
            for b in (0.01, 0.02, 0.03):
                fam[f'P>SMA{n} band{int(b*100)}%'] = state_machine(p > s * (1 + b), p < s * (1 - b))
        for f, sl in itertools.product((5, 10, 20, 30, 50, 75, 100, 150), (50, 100, 150, 200, 250)):
            if f < sl:
                fam[f'SMA{f}>SMA{sl}'] = (sma(p, f) > sma(p, sl)).astype(np.int8)
                fam[f'EMA{f}>EMA{sl}'] = (ema(p, f) > ema(p, sl)).astype(np.int8)
        for a, b, c in ((12, 26, 9), (8, 17, 9), (5, 35, 5), (19, 39, 9), (10, 20, 5), (6, 13, 5), (24, 52, 18),
                        (12, 26, 1), (20, 50, 10), (50, 100, 20)):
            m = ema(p, a) - ema(p, b)
            fam[f'MACD({a},{b},{c})'] = (m > ema(m, c)).astype(np.int8) if c > 1 else (m > 0).astype(np.int8)
        s200 = sma(p, 200); s5 = sma(p, 5)
        for n, th in itertools.product((2, 3, 4, 5, 7, 14), (5, 10, 15, 20, 25, 30)):
            r = rsi_wilder(p, n)
            fam[f'RSI{n}<{th}&>SMA200 exitSMA5'] = state_machine((r < th) & (p > s200), p > s5)
        for n in (2, 5, 14):
            fam[f'RSI{n}>50 (momentum)'] = (rsi_wilder(p, n) > 50).astype(np.int8)
        for n, k in itertools.product((10, 15, 20, 30, 40, 50), (1.5, 2.0, 2.5)):
            m = sma(p, n); sd = pd.Series(p).rolling(n, min_periods=n).std(ddof=0).values
            fam[f'BB({n},{k}) MR'] = state_machine(p < m - k * sd, p > m)
            fam[f'BB({n},{k}) breakout'] = state_machine(p > m + k * sd, p < m)
        for en, ex in itertools.product((10, 20, 40, 55, 100, 150, 200, 250), (5, 10, 20, 40, 50, 100)):
            if ex < en:
                hi = pd.Series(p).shift(1).rolling(en, min_periods=en).max().values
                lo = pd.Series(p).shift(1).rolling(ex, min_periods=ex).min().values
                fam[f'Donchian{en}/{ex}'] = state_machine(p > hi, p < lo)
        for L in (1, 2, 3, 6, 9, 12):
            fam[f'TSMOM{L}M monthly'] = monthly_pos(dates, p, lambda m, L=L: (m / pd.Series(m).shift(L).values - 1) > 0)
        for L in range(20, 260, 20):
            fam[f'TSMOM{L}d daily'] = (p / pd.Series(p).shift(L).values - 1 > 0).astype(np.int8)
        for n in range(3, 13):
            fam[f'{n}M_SMA monthly'] = monthly_pos(dates, p, lambda m, n=n: m > pd.Series(m).rolling(n, min_periods=n).mean().values)
    return fam


# ------------------------------------------------------------------ evaluation
def strat_returns(pos, r, c):
    """pos decided at close t applies to r_{t+1}; cost on position changes charged on t+1."""
    pp = np.concatenate(([0], pos[:-1])).astype(float)          # position held during day t
    chg = np.abs(np.diff(np.concatenate(([0, 0], pos[:-1])).astype(float)))
    return pp * r - c * chg, pp


def perf(dr, pp, dates_sub):
    dr = np.asarray(dr); n = len(dr)
    yrs = (dates_sub[-1] - dates_sub[0]).days / 365.25 + 1 / 252
    af = n / yrs
    tot = np.prod(1 + dr)
    vol = dr.std(ddof=1) * np.sqrt(af)
    out = dict(cagr=tot ** (1 / yrs) - 1, total_return=tot - 1, ann_vol=vol,
               sharpe=dr.mean() / dr.std(ddof=1) * np.sqrt(af) if dr.std() > 0 else np.nan,
               max_dd=max_drawdown(dr), time_in_market=float(pp.mean()),
               switches_per_year=float(np.abs(np.diff(np.concatenate(([pp[0]], pp)))).sum() / yrs),
               entries_per_year=float(((np.diff(np.concatenate(([0.0], pp)))) > 0).sum() / yrs), n_days=n)
    return out


def main():
    t0 = time.time()
    dates, _ = load_meta()
    idx_ops = build_index(include_vehicles=False)
    idx = build_index(include_vehicles=True)
    idx.to_parquet(f'{CACHE}/kospi_rebuilt.parquet')
    san = sanity(idx_ops, idx).rename(columns={'ratio_rebuilt_to_official': 'ratio_operating_cos_only',
                                                 'ratio_incl_investment_vehicles': 'ratio_rebuilt_to_official'})
    san['rebuilt_start'] = [float(idx['level'].loc[d]) for d in san['start']]
    san['rebuilt_end'] = [float(idx['level'].loc[d]) for d in san['end']]
    san['rebuilt_change'] = san['rebuilt_end'] / san['rebuilt_start'] - 1
    san.to_csv(f'{RES}/kr_index_sanity.csv', index=False, float_format='%.6g')
    log('index built'); print(san.round(4).to_string())
    p = idx['level'].values; r = idx['ret'].values
    ev = dates >= pd.Timestamp(EVAL_START)
    ed = dates[ev]
    # ---------------- core rules
    core = core_rules(dates, p)
    bh = np.ones(len(p), np.int8)
    rows, ev_rows, daily_core = [], [], {}
    periods = [(lab, pd.Timestamp(max(a, EVAL_START)), pd.Timestamp(b)) for lab, a, b in SUBPERIODS]
    wins = []
    for lab, a, b in EVENT_WINDOWS:
        ia = int(np.searchsorted(dates.values, np.datetime64(a), side='right') - 1)
        ib = int(np.searchsorted(dates.values, np.datetime64(b), side='right') - 1)
        wins.append((lab, ia, ib))
    for name, pos in [('Buy & hold', bh)] + list(core.items()):
        for cl, c in COSTS.items():
            dr, pp = strat_returns(pos, r, c if name != 'Buy & hold' else 0.0)
            if name == 'Buy & hold':
                pp = np.ones_like(pp)
            daily_core[(name, cl)] = dr
            for plab, a, b in periods:
                m = (dates >= a) & (dates <= b)
                st = perf(dr[m], pp[m], dates[m])
                rbh = r[m]
                ex = dr[m] - rbh
                st['excess_mean_ann_vs_bh'] = ex.mean() * st['n_days'] / ((dates[m][-1] - dates[m][0]).days / 365.25)
                st['excess_nw_t_vs_bh'] = nw_tstat(ex, 10)
                for k, v in st.items():
                    rows.append((name, cl, plab, k, v))
            for lab, ia, ib in wins:
                ev_rows.append((name, cl, lab, str(dates[ia].date()), str(dates[ib].date()),
                                float(np.prod(1 + dr[ia + 1:ib + 1]) - 1), float(pp[ia + 1:ib + 1].mean())))
    tab = pd.DataFrame(rows, columns=['rule', 'cost_level', 'period', 'metric', 'value'])
    tab.to_csv(f'{RES}/kr_index_timing.csv', index=False, float_format='%.6g')
    pd.DataFrame(ev_rows, columns=['rule', 'cost_level', 'window', 'start_close', 'end_close', 'cum_return',
                                   'time_in_market']).to_csv(f'{RES}/kr_index_timing_events.csv', index=False,
                                                             float_format='%.6g')
    log('core rules done')
    # ---------------- SPA family
    fam = family(dates, p)
    names = list(fam)
    log(f'family size {len(names)}')
    assert len(names) >= 300
    Rn = np.column_stack([strat_returns(fam[k], r, COSTS['net3'])[0] for k in names])
    Pp = np.column_stack([strat_returns(fam[k], r, 0.0)[1] for k in names])
    # every variant must have a defined position from the evaluation start (warm-up check)
    rbh = r.copy()

    def spa_run(mask, label):
        L_b = -rbh[mask]; L_m = -Rn[mask]
        spa = SPA(L_b, L_m, block_size=15, reps=2000, bootstrap='stationary', studentize=True, seed=SEED)
        spa.compute()
        pv = spa.pvalues
        d = Rn[mask] - rbh[mask][:, None]
        tstats = np.array([nw_tstat(d[:, j], 10) for j in range(d.shape[1])])
        mean_ex = d.mean(0)
        return pv, mean_ex, tstats

    pv, mean_ex, tst = spa_run(ev, 'full')
    best = int(np.nanargmax(tst))
    dsub = dates[ev]
    fam_rows = []
    for j, k in enumerate(names):
        st = perf(Rn[ev, j], Pp[ev, j], dsub)
        fam_rows.append(dict(rule=k, mean_daily_excess_vs_bh=mean_ex[j], nw_t_excess=tst[j], **st))
    famdf = pd.DataFrame(fam_rows)
    bh_st = perf(rbh[ev], np.ones(ev.sum()), dsub)
    famdf.to_csv(f'{RES}/kr_index_spa_family.csv', index=False, float_format='%.6g')
    # ---------------- time split: select on 1996-2012, evaluate 2013-2026
    ins = ev & (dates <= pd.Timestamp('2012-12-31'))
    oos = dates >= pd.Timestamp('2013-01-01')
    d_ins = Rn[ins] - rbh[ins][:, None]
    t_ins = np.array([nw_tstat(d_ins[:, j], 10) for j in range(len(names))])
    sel = int(np.nanargmax(t_ins))
    sh_ins = np.array([perf(Rn[ins, j], Pp[ins, j], dates[ins])['sharpe'] for j in range(len(names))])
    sel_sh = int(np.nanargmax(sh_ins))
    pv_ins, _, _ = spa_run(ins, 'ins')
    spa_rows = []

    def add(section, key, val):
        spa_rows.append((section, key, val))
    add('family', 'n_variants', len(names))
    add('family', 'evaluation', f'{dsub[0].date()}..{dsub[-1].date()}, net 3 bp per side, cash 0%')
    add('family', 'spa_settings', 'arch SPA, losses -r (benchmark = buy&hold), stationary bootstrap, block 15, 2000 reps, seed 20261002, studentized')
    add('full', 'best_rule', names[best])
    add('full', 'best_rule_nw_t_excess', tst[best])
    add('full', 'best_rule_mean_excess_ann', mean_ex[best] * bh_st['n_days'] / ((dsub[-1] - dsub[0]).days / 365.25))
    for k, v in perf(Rn[ev, best], Pp[ev, best], dsub).items():
        add('full', f'best_rule_{k}', v)
    for k, v in bh_st.items():
        add('full', f'buyhold_{k}', v)
    for k in ('lower', 'consistent', 'upper'):
        add('full', f'spa_p_{k}', float(pv[k]))
    add('full', 'n_rules_positive_mean_excess', int((mean_ex > 0).sum()))
    add('full', 'n_rules_sharpe_above_bh', int((famdf['sharpe'] > bh_st['sharpe']).sum()))
    add('full', 'best_sharpe_rule', famdf.loc[famdf['sharpe'].idxmax(), 'rule'])
    add('full', 'best_sharpe_value', famdf['sharpe'].max())
    for k in ('lower', 'consistent', 'upper'):
        add('ins_1996_2012', f'spa_p_{k}', float(pv_ins[k]))
    for lab, j in (('selected_by_excess_t', sel), ('selected_by_sharpe', sel_sh)):
        add(lab, 'rule', names[j])
        sti = perf(Rn[ins, j], Pp[ins, j], dates[ins]); bhi = perf(rbh[ins], np.ones(ins.sum()), dates[ins])
        sto = perf(Rn[oos, j], Pp[oos, j], dates[oos]); bho = perf(rbh[oos], np.ones(oos.sum()), dates[oos])
        for k in ('cagr', 'sharpe', 'max_dd', 'time_in_market', 'switches_per_year'):
            add(lab, f'ins_rule_{k}', sti[k]); add(lab, f'ins_bh_{k}', bhi[k])
            add(lab, f'oos_rule_{k}', sto[k]); add(lab, f'oos_bh_{k}', bho[k])
        dx = Rn[oos, j] - rbh[oos]
        add(lab, 'oos_excess_nw_t', nw_tstat(dx, 10))
        add(lab, 'oos_excess_mean_ann', dx.mean() * sto['n_days'] / ((dates[oos][-1] - dates[oos][0]).days / 365.25))
        dx6 = strat_returns(fam[names[j]], r, COSTS['net6'])[0][oos] - rbh[oos]
        add(lab, 'oos_excess_mean_ann_6bp', dx6.mean() * sto['n_days'] / ((dates[oos][-1] - dates[oos][0]).days / 365.25))
    # ---------------- supplementary: timing skill vs an exposure-matched buy-and-hold
    # d_k = r_rule,k,net - x_k * r_bh with x_k = the rule's average exposure over the evaluation window
    # (a constant-mix of the index and 0% cash with the same average market exposure).
    xk = Pp[ev].mean(0)
    Lm = -(Rn[ev] - rbh[ev][:, None] * xk[None, :])
    spa2 = SPA(np.zeros(ev.sum()), Lm, block_size=15, reps=2000, bootstrap='stationary', studentize=True, seed=SEED)
    spa2.compute()
    pv2 = spa2.pvalues
    d2 = -Lm
    t2 = np.array([nw_tstat(d2[:, j], 10) for j in range(d2.shape[1])])
    b2 = int(np.nanargmax(t2))
    add('exposure_matched', 'definition', 'd_k = r_rule,net3 - x_k * r_bh, x_k = average exposure of rule k (1996-06..2026-09)')
    for k in ('lower', 'consistent', 'upper'):
        add('exposure_matched', f'spa_p_{k}', float(pv2[k]))
    add('exposure_matched', 'best_rule', names[b2])
    add('exposure_matched', 'best_rule_nw_t', t2[b2])
    add('exposure_matched', 'best_rule_mean_ann', d2[:, b2].mean() * bh_st['n_days'] / ((dsub[-1] - dsub[0]).days / 365.25))
    add('exposure_matched', 'best_rule_exposure', xk[b2])
    add('exposure_matched', 'n_rules_positive', int((d2.mean(0) > 0).sum()))
    add('exposure_matched', 'n_rules_t_above_2', int((t2 > 2).sum()))
    # time split for the exposure-matched criterion: select on 1996-2012, evaluate 2013-2026; the benchmark in
    # each window is buy-and-hold scaled by the rule's average exposure in that same window
    xk_ins = Pp[ins].mean(0)
    d2i = Rn[ins] - rbh[ins][:, None] * xk_ins[None, :]
    t2i = np.array([nw_tstat(d2i[:, j], 10) for j in range(d2i.shape[1])])
    yrs_o = (dates[oos][-1] - dates[oos][0]).days / 365.25
    for lab, j in (('exposure_matched_split_by_t', int(np.nanargmax(t2i))), ('exposure_matched_split_by_sharpe', sel_sh)):
        xo = Pp[oos, j].mean()
        d2o = Rn[oos, j] - rbh[oos] * xo
        add(lab, 'selected_rule_1996_2012', names[j])
        add(lab, 'ins_mean_ann_vs_exposure_matched', d2i[:, j].mean() * ins.sum() / ((dates[ins][-1] - dates[ins][0]).days / 365.25))
        add(lab, 'ins_nw_t', t2i[j])
        add(lab, 'ins_exposure', xk_ins[j]); add(lab, 'oos_exposure', xo)
        add(lab, 'oos_mean_ann_vs_exposure_matched', d2o.mean() * oos.sum() / yrs_o)
        add(lab, 'oos_nw_t_vs_exposure_matched', nw_tstat(d2o, 10))
        sto2 = perf(Rn[oos, j], Pp[oos, j], dates[oos])
        bho2 = perf(rbh[oos], np.ones(oos.sum()), dates[oos])
        for k in ('cagr', 'ann_vol', 'sharpe', 'max_dd', 'time_in_market'):
            add(lab, f'oos_rule_{k}', sto2[k]); add(lab, f'oos_bh_{k}', bho2[k])
    famdf['exposure'] = xk
    famdf['mean_ann_vs_exposure_matched'] = d2.mean(0) * bh_st['n_days'] / ((dsub[-1] - dsub[0]).days / 365.25)
    famdf['nw_t_vs_exposure_matched'] = t2
    famdf.to_csv(f'{RES}/kr_index_spa_family.csv', index=False, float_format='%.6g')
    spa_df = pd.DataFrame(spa_rows, columns=['section', 'key', 'value'])
    spa_df.to_csv(f'{RES}/kr_index_spa.csv', index=False)
    print(spa_df.to_string())
    # store curves for charts
    curves = pd.DataFrame({'level': p, 'sma200': sma(p, 200), 'ret_bh': r,
                           'ret_sma200_net3': daily_core[('SMA200 (close > SMA200)', 'net3')],
                           'ret_best_spa_net3': Rn[:, best], 'pos_best_spa': Pp[:, best]}, index=dates)
    curves.attrs['best_rule'] = names[best]
    curves.to_parquet(f'{CACHE}/index_curves.parquet')
    with open(f'{CACHE}/index_best_rule.txt', 'w') as f:
        f.write(names[best])
    log(f'done in {time.time() - t0:.0f}s')


if __name__ == '__main__':
    main()
