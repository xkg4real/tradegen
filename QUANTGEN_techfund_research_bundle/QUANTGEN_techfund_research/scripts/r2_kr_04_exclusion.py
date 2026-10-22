"""r2_kr_04_exclusion.py -- Task 2: exclusion-screen horse race (long-only), with an indicative QUANTGEN gate.

Filters (flag a name at the formation close t using rows <= t; flagged names are removed from the base book at
that formation and the book earns from t+1; breakpoints are formed inside the ALL universe = round-1 eligible
set with the microcap cut, so a filter is a property of the stock, not of the base book):
  F1 highest TURN_1M quintile          F2 highest VOL_3M quintile          F3 highest MAX_1M quintile
  F4 P6 lottery composite: pct-rank(-VOL_3M) + pct-rank(-MAX_1M) + pct-rank(-TURN_1M) (average ranks over the
     universe, all three finite), bottom decile by ordinal rank (pandas method='first') = most lottery-like 10%
     (p6_exclusion.py / p6_excl2.py)
  F5 E7 attention-fade: any of {Volume >= 5 x previous-20-day average with r >= +5%; locked limit-up close
     (>= 29.5% from 2015-06-15, >= 14.5% before, close = high); 20-day return >= +50%} in t-19..t
  F6 dilution: 252-session growth in shares outstanding > 10%, ignoring split-like days (shares multiplied by
     > 5% and the raw close moved by the inverse ratio within +-5% on the same day)
  F7 = F1|F2|F3                        F8 = F4|F5|F6
Neighbour variants (trials; used for the plateau step): cut fractions 10/15/25/30% (F1-F3), other windows
(TURN_3M, VOL_1M, VOL_6M, MAX_3M), F4 cut 5/15/20/25%, F5 windows 5/10/40/60 sessions + components + the
regime-limit lock, F6 thresholds 5/20/30% + net-issuance definition (F6b), union variants.
Base books: B1 EW ALL; B2 VW ALL capped at 5% (excess redistributed pro rata, iteratively); B3 top-200 by
Marcap VW capped 5%; B4 MOM_12_1 top quintile (ALL) EW. Filtered book = base members minus flagged names, same
weighting rule. Monthly rebalance, costs 35 / 70 bp per side on each book's own turnover (both books net).
Statistics on the paired monthly difference d_k = R_filtered,k - R_unfiltered,k (identical holding days).
Outputs: results/r2_kr_excl_summary.csv, r2_kr_excl_long.csv, r2_kr_excl_windows.csv, r2_kr_excl_years.csv,
         r2_kr_excl_jaccard.csv, r2_kr_excl_trials.csv, r2_kr_excl_gate.csv, r2_kr_excl_limitlock.csv,
         r2_kr_excl_f6_diagnostic.csv; cache/books_excl.npz
"""
import sys, time, math
import numpy as np
import pandas as pd
sys.path.insert(0, '/home/claude/datalab/r2/kr')
from r2_kr_common import (Panel, run_books, series, diff_series, stats, quantile_groups, weights, log, to_csv,
                          save_books, boot_pvalue, boot_index, deflated_sharpe, pbo_cscv, lo_sharpe_se,
                          window_returns, year_returns, nw_tstat, max_drawdown, SUB3, EXCL_WINDOWS, CACHE2, RES2)
from scipy.stats import rankdata

PRIMARY = ['F1', 'F2', 'F3', 'F4', 'F5', 'F6', 'F7', 'F8']
BASES = {'B1': 'EW ALL universe', 'B2': 'VW ALL capped 5%', 'B3': 'top-200 VW capped 5%', 'B4': 'MOM 12-1 top quintile EW'}


def top_frac(x, U, frac):
    """Flag the top `frac` of x inside U (average ranks; (rank-0.5)/n >= 1-frac). frac=0.2 equals quantile 5."""
    out = np.zeros(x.shape, bool)
    m = U & np.isfinite(x)
    n = int(m.sum())
    if n < 25:
        return out
    r = rankdata(x[m], method='average')
    out[m] = (r - 0.5) / n >= 1.0 - frac
    return out


def p6_composite(F, k, U, frac=0.10):
    """P6 lottery composite: bottom `frac` of the sum of average pct-ranks of -VOL, -MAX, -TURN (ordinal cut)."""
    out = np.zeros(U.shape, bool)
    parts = []
    for s in ('VOL_3M', 'MAX_1M', 'TURN_1M'):
        x = F[s][k].astype(np.float64)
        m = U & np.isfinite(x)
        r = np.full(x.shape, np.nan)
        r[m] = rankdata(-x[m], method='average') / m.sum()
        parts.append(r)
    comp = parts[0] + parts[1] + parts[2]
    m = U & np.isfinite(comp)
    idx = np.flatnonzero(m)
    order = idx[np.argsort(comp[idx], kind='stable')]          # ascending composite = most lottery-like first
    q = np.empty(len(order)); q[:] = np.arange(1, len(order) + 1) / len(order)
    out[order[q <= frac]] = True
    return out


def build_filters(P, X):
    F = P.F
    U = F['univ_all']
    K, N = P.K, P.N
    fl = {}

    def mk(name, fn):
        a = np.zeros((K, N), bool)
        for k in range(K):
            a[k] = fn(k) & U[k]
        fl[name] = a
    mk('F1', lambda k: quantile_groups(F['TURN_1M'][k], U[k], 5, k) == 5)
    mk('F2', lambda k: quantile_groups(F['VOL_3M'][k], U[k], 5, k) == 5)
    mk('F3', lambda k: quantile_groups(F['MAX_1M'][k], U[k], 5, k) == 5)
    mk('F4', lambda k: p6_composite(F, k, U[k], 0.10))
    mk('F5', lambda k: X['F5'][k])
    mk('F6', lambda k: np.nan_to_num(X['DIL_LIT'][k], nan=0.0) > 0.10)
    fl['F7'] = fl['F1'] | fl['F2'] | fl['F3']
    fl['F8'] = fl['F4'] | fl['F5'] | fl['F6']
    # neighbours / variants (each one is a trial)
    nb = {}
    for fr in (0.10, 0.15, 0.25, 0.30):
        nb[f'F1_cut{int(fr*100)}'] = ('F1', lambda k, fr=fr: top_frac(F['TURN_1M'][k], U[k], fr))
        nb[f'F2_cut{int(fr*100)}'] = ('F2', lambda k, fr=fr: top_frac(F['VOL_3M'][k], U[k], fr))
        nb[f'F3_cut{int(fr*100)}'] = ('F3', lambda k, fr=fr: top_frac(F['MAX_1M'][k], U[k], fr))
    nb['F1_TURN3M'] = ('F1', lambda k: top_frac(X['TURN_3M'][k], U[k], 0.20))
    nb['F2_VOL1M'] = ('F2', lambda k: top_frac(X['VOL_1M'][k], U[k], 0.20))
    nb['F2_VOL6M'] = ('F2', lambda k: top_frac(X['VOL_6M'][k], U[k], 0.20))
    nb['F3_MAX3M'] = ('F3', lambda k: top_frac(X['MAX_3M'][k], U[k], 0.20))
    for fr in (0.05, 0.15, 0.20, 0.25):
        nb[f'F4_cut{int(fr*100)}'] = ('F4', lambda k, fr=fr: p6_composite(F, k, U[k], fr))
    for w in (5, 10, 40, 60):
        nb[f'F5_w{w}'] = ('F5', lambda k, w=w: X[f'F5_w{w}'][k])
    nb['F5_reglock'] = ('F5', lambda k: X['F5_reg'][k])
    nb['F5_vspike_only'] = ('F5', lambda k: X['F5_vspike'][k])
    nb['F5_lock_only'] = ('F5', lambda k: X['F5_lu'][k])
    nb['F5_r20_only'] = ('F5', lambda k: X['F5_r20'][k])
    for th in (0.05, 0.20, 0.30):
        nb[f'F6_gt{int(th*100)}'] = ('F6', lambda k, th=th: np.nan_to_num(X['DIL_LIT'][k], nan=0.0) > th)
    nb['F6b_netissuance'] = ('F6', lambda k: np.nan_to_num(X['DIL_NI'][k], nan=0.0) > 0.10)
    for name, (fam, fn) in nb.items():
        mk(name, fn)
    for fr in (10, 30):
        fl[f'F7_cut{fr}'] = fl[f'F1_cut{fr}'] | fl[f'F2_cut{fr}'] | fl[f'F3_cut{fr}']
    fl['F8_F6b'] = fl['F4'] | fl['F5'] | fl['F6b_netissuance']
    fl['F8_reglock'] = fl['F4'] | fl['F5_reglock'] | fl['F6']
    family = {f: f for f in PRIMARY}
    family.update({n: fam for n, (fam, _) in nb.items()})
    family.update({'F7_cut10': 'F7', 'F7_cut30': 'F7', 'F8_F6b': 'F8', 'F8_reglock': 'F8'})
    return fl, family


def main():
    t0 = time.time()
    P = Panel()
    X = P.extra()
    F = P.F
    U, LG, mc = F['univ_all'], F['univ_large'], F['mcap']
    log('building filters')
    FL, FAM = build_filters(P, X)
    fnames = list(FL)
    log(f'{len(fnames)} filter definitions ({len(PRIMARY)} primary)')
    momq5 = np.zeros_like(U)
    for k in range(P.K):
        momq5[k] = quantile_groups(F['MOM_12_1'][k], U[k], 5, k) == 5
    base_mem = {'B1': (U, 'EW'), 'B2': (U, 'VWcap5'), 'B3': (LG, 'VWcap5'), 'B4': (momq5, 'EW')}
    specs = []

    suspended = {}

    def add(name, mem, rule, flag=None):
        def fn(k):
            m = mem[k] if flag is None else (mem[k] & ~flag[k])
            if not m.any():                       # a filter may not empty the book: suspend it for that month
                suspended[name] = suspended.get(name, 0) + 1
                m = mem[k]
            idx = np.flatnonzero(m)
            return idx, weights(idx, rule, mc[k])
        specs.append((name, fn))
    for b, (mem, rule) in base_mem.items():
        add(f'{b}|none', mem, rule)
        for f in fnames:
            add(f'{b}|{f}', mem, rule, FL[f])
    log(f'{len(specs)} books; running engine')
    books = run_books(P, specs, progress=120)
    save_books(f'{CACHE2}/books_excl.npz', P, books)
    small = {nm: int(((b['nmem'] > 0) & (b['nmem'] < 20)).sum()) for nm, b in books.items()}
    small = {k: v for k, v in small.items() if v}
    log(f'books done; filter suspended (would empty the book): {suspended}; months with < 20 names: {small}')
    to_csv(pd.DataFrame([dict(book=k, months_suspended=v) for k, v in suspended.items()] +
                        [dict(book=k, months_lt20_names=v) for k, v in small.items()]), 'r2_kr_excl_thin_books.csv')
    pms = {lab: P.pmask(a, b) for lab, a, b in SUB3}
    pm_full = pms['full']
    summ, longrows, winrows, yrrows, trial_rows = [], [], [], [], []
    diffs35 = {}       # (base, filter) -> monthly diff at 35 bp (for PBO / DSR)
    daily35 = {}
    for b in base_mem:
        Ub = books[f'{b}|none']
        mem_b = base_mem[b][0]
        for f in fnames:
            Xf = books[f'{b}|{f}']
            # exclusion share (names and, for VW bases, base weight)
            ex_n, ex_w = [], []
            for k in range(P.K):
                m = np.flatnonzero(mem_b[k])
                if len(m) == 0:
                    continue
                flg = FL[f][k][m]
                ex_n.append(flg.mean())
                w = weights(m, base_mem[b][1], mc[k])
                ex_w.append(w[flg].sum())
            ex_n = np.array(ex_n); ex_w = np.array(ex_w)
            for cl, c in (('net35', 0.0035), ('net70', 0.0070), ('gross', 0.0)):
                d, dd, _ = diff_series(P, Xf, Ub, c)
                pf, df_, tf = series(P, Xf, c=c)
                pu, du, tu = series(P, Ub, c=c)
                if cl == 'net35':
                    diffs35[(b, f)] = d; daily35[(b, f)] = dd
                    daily35[(b, 'none_book')] = du; daily35[(b, f, 'book')] = df_
                row = dict(base=b, filter=f, family=FAM[f], primary=f in PRIMARY, cost=cl)
                for plab, pm in pms.items():
                    full = plab == 'full'
                    x = d[pm]; x = x[np.isfinite(x)]
                    sf = stats(P, pf, df_, tf, pm, full=False); su = stats(P, pu, du, tu, pm, full=False)
                    o = {'ann_diff': x.mean() * 12, 'te': x.std(ddof=1) * math.sqrt(12),
                         'ir': x.mean() / x.std(ddof=1) * math.sqrt(12), 'nw_t': nw_tstat(x, 6),
                         'sharpe_filtered': sf['sharpe'], 'sharpe_unfiltered': su['sharpe'],
                         'cagr_filtered': sf['cagr'], 'cagr_unfiltered': su['cagr'],
                         'cagr_diff': sf['cagr'] - su['cagr'],
                         'maxdd_filtered': sf['max_dd'], 'maxdd_unfiltered': su['max_dd'],
                         'maxdd_diff': sf['max_dd'] - su['max_dd'],
                         'turnover_filtered': sf['turnover_per_year'], 'turnover_unfiltered': su['turnover_per_year'],
                         'n_months': len(x)}
                    if full:
                        bp = boot_pvalue(x)
                        o.update(boot_p=bp['p_null'], boot_p_perc=bp['p_perc'], boot_ci90_lo=bp['ci90_lo'] * 12,
                                 boot_ci90_hi=bp['ci90_hi'] * 12)
                        yf = year_returns(P, df_); yu = year_returns(P, du)
                        yd = (yf - yu).dropna()
                        o['pct_years_pos'] = float((yd > 0).mean()); o['n_years'] = int(len(yd))
                        o['excl_share_names'] = float(ex_n.mean()); o['excl_share_weight'] = float(ex_w.mean())
                        if cl == 'net35':
                            for y, v in yd.items():
                                yrrows.append(dict(base=b, filter=f, year=int(y), diff=v, filtered=yf[y], unfiltered=yu[y]))
                            wf = window_returns(P, df_, EXCL_WINDOWS); wu = window_returns(P, du, EXCL_WINDOWS)
                            for wl in wf:
                                winrows.append(dict(base=b, filter=f, window=wl, filtered=wf[wl], unfiltered=wu[wl],
                                                    diff=wf[wl] - wu[wl]))
                    for mname, v in o.items():
                        longrows.append(dict(base=b, filter=f, family=FAM[f], primary=f in PRIMARY, cost=cl,
                                             period=plab, metric=mname, value=v))
                    if full:
                        row.update(o)
                summ.append(row)
            trial_rows.append(dict(base=b, filter=f, family=FAM[f], primary=f in PRIMARY,
                                   ir_net35=[r for r in summ if r['base'] == b and r['filter'] == f and r['cost'] == 'net35'][0]['ir']))
        log(f'{b} done')
    S = pd.DataFrame(summ)
    to_csv(S, 'r2_kr_excl_summary.csv')
    to_csv(pd.DataFrame(longrows), 'r2_kr_excl_long.csv')
    to_csv(pd.DataFrame(winrows), 'r2_kr_excl_windows.csv')
    to_csv(pd.DataFrame(yrrows), 'r2_kr_excl_years.csv')
    TR = pd.DataFrame(trial_rows)
    to_csv(TR, 'r2_kr_excl_trials.csv')
    # ---------------- Jaccard overlap of the primary filters inside the ALL universe ----------------
    jac = []
    for i, a in enumerate(PRIMARY):
        for bnm in PRIMARY:
            A, B = FL[a], FL[bnm]
            inter = (A & B).sum(1); uni = (A | B).sum(1)
            j = np.where(uni > 0, inter / np.maximum(uni, 1), np.nan)
            jac.append(dict(filter_a=a, filter_b=bnm, jaccard_mean=float(np.nanmean(j)),
                            jaccard_2016_2026=float(np.nanmean(j[pms['2016-2026-09']])),
                            share_of_ALL_a=float((A.sum(1) / U.sum(1)).mean())))
    to_csv(pd.DataFrame(jac), 'r2_kr_excl_jaccard.csv')
    # ---------------- F6 diagnostic: literal rule vs net issuance ----------------
    lit, ni = FL['F6'], FL['F6b_netissuance']
    to_csv(pd.DataFrame([dict(name_months_literal=int(lit.sum()), name_months_netissuance=int(ni.sum()),
                              both=int((lit & ni).sum()), literal_only=int((lit & ~ni).sum()),
                              netissuance_only=int((ni & ~lit).sum()),
                              share_literal_not_confirmed=float((lit & ~ni).sum() / max(lit.sum(), 1)))]),
           'r2_kr_excl_f6_diagnostic.csv')
    # ---------------- indicative gate ----------------
    n_trials = len(TR)
    srs = np.array([np.nanmean(diffs35[k]) / np.nanstd(diffs35[k], ddof=1) for k in diffs35])
    var_sr = float(np.nanvar(srs, ddof=1))
    gate = []
    T0 = P.starts[0]
    for b in base_mem:
        sb = S[(S.base == b) & (S.cost == 'net35') & S.primary].sort_values('ir', ascending=False)
        # PBO among the 8 primary filters and among all variants (CSCV, S=16, Sharpe of the monthly differences)
        Mp = np.column_stack([diffs35[(b, f)] for f in PRIMARY])
        Ma = np.column_stack([diffs35[(b, f)] for f in fnames])
        okr = np.isfinite(Mp).all(1) & np.isfinite(Ma).all(1)
        pbo_p = pbo_cscv(Mp[okr]); pbo_a = pbo_cscv(Ma[okr])
        # walk-forward selection on daily differences: IS 756 sessions, embargo 21, OOS 126
        Dd = np.column_stack([daily35[(b, f)] for f in PRIMARY])
        valid = np.isfinite(Dd).all(1)
        vidx = np.flatnonzero(valid)
        oos_sel = []
        st = 756
        while st + 21 + 126 <= len(vidx):
            ins = vidx[st - 756:st]
            oos = vidx[st + 21:st + 21 + 126]
            irs = Dd[ins].mean(0) / Dd[ins].std(0, ddof=1)
            j = int(np.argmax(irs))
            oos_sel.append(Dd[oos, j])
            st += 126
        wf = np.concatenate(oos_sel)
        wf_ir = wf.mean() / wf.std(ddof=1) * math.sqrt(252)
        for rank_i, (_, r) in enumerate(sb.head(2).iterrows()):
            f = r['filter']
            d = diffs35[(b, f)]
            x = d[np.isfinite(d)]
            sr_ann, se_ann, eta = lo_sharpe_se(x)
            ddaily = daily35[(b, f)]
            ddx = ddaily[np.isfinite(ddaily)]
            idx = boot_index(len(ddx), 10, 2000)
            xb = ddx[idx]
            ir_b = xb.mean(1) / xb.std(1, ddof=1) * math.sqrt(252)
            ci_lo, ci_hi = np.quantile(ir_b, [0.05, 0.95])
            dsr, sr0, sr_m = deflated_sharpe(x, n_trials, var_sr)
            dsr_null, sr0_null, _ = deflated_sharpe(x, n_trials, 1.0 / (len(x) - 1))
            srs_b = np.array([np.nanmean(diffs35[(b, g)]) / np.nanstd(diffs35[(b, g)], ddof=1) for g in fnames])
            dsr_base, sr0_base, _ = deflated_sharpe(x, len(fnames), float(np.var(srs_b, ddof=1)))
            r70 = S[(S.base == b) & (S['filter'] == f) & (S.cost == 'net70')].iloc[0]
            fam = FAM[f]
            neigh = [n for n in fnames if FAM[n] == fam and n != f]
            neigh_ir = [S[(S.base == b) & (S['filter'] == n) & (S.cost == 'net35')].iloc[0]['ir'] for n in neigh]
            plateau = float(np.mean([v >= 0.5 * r['ir'] for v in neigh_ir])) if neigh_ir else np.nan
            steps = {
                'g1_walkforward_selected_oos_ir': wf_ir, 'g1_pass': wf_ir > 0,
                'g2_lo_ir': sr_ann, 'g2_lo_se': se_ann, 'g2_lo_ci90': f'[{sr_ann - 1.645 * se_ann:.2f}, {sr_ann + 1.645 * se_ann:.2f}]',
                'g2_boot_ci90': f'[{ci_lo:.2f}, {ci_hi:.2f}]', 'g2_pass': (sr_ann - 1.645 * se_ann > 0) and (ci_lo > 0),
                'g3_dsr': dsr, 'g3_sr0_monthly': sr0, 'g3_dsr_nullvar': dsr_null, 'g3_sr0_nullvar': sr0_null,
                'g3_dsr_per_base': dsr_base, 'g3_sr0_per_base': sr0_base, 'g3_n_trials_per_base': len(fnames),
                'g3_pass': dsr >= 0.95,
                'g4_pbo_primary8': pbo_p['pbo'], 'g4_pbo_all_variants': pbo_a['pbo'],
                'g4_winner_loses_primary8': pbo_p['winner_loses_share'], 'g4_winner_loses_all': pbo_a['winner_loses_share'],
                'g4_pass': ((pbo_p['pbo'] <= 0.05) or (pbo_p['winner_loses_share'] <= 0.10)) and
                           ((pbo_a['pbo'] <= 0.05) or (pbo_a['winner_loses_share'] <= 0.10)),
                'g5_boot_p': r['boot_p'], 'g5_pass': r['boot_p'] <= 0.10,
                'g6_filtered_sharpe_net70': r70['sharpe_filtered'], 'g6_diff_ir_net70': r70['ir'],
                'g6_pass': (r70['sharpe_filtered'] > 0) and (r70['ir'] > 0),
                'g7_plateau_share': plateau, 'g7_n_neighbours': len(neigh), 'g7_pass': plateau >= 0.5 if neigh_ir else False,
                'g8_pct_years_pos': r['pct_years_pos'], 'g8_pass': r['pct_years_pos'] >= 0.6,
                'g9_haircut_ann_diff': 0.4 * r['ann_diff'], 'g9_haircut_ir': 0.4 * r['ir']}
            npass = sum(bool(v) for kk, v in steps.items() if kk.endswith('_pass'))
            reject = ((not steps['g5_pass']) and (not steps['g2_pass'])) or \
                     (pbo_a['pbo'] > 0.2 and pbo_a['winner_loses_share'] > 0.10) or (not steps['g6_pass'])
            verdict = 'PASS' if npass == 8 else ('REJECT' if reject else 'REVISE')
            gate.append(dict(base=b, rank=rank_i + 1, filter=f, ann_diff_net35=r['ann_diff'], ir_net35=r['ir'],
                             n_trials=n_trials, var_trial_sr_monthly=var_sr, steps_passed=npass, verdict=verdict, **steps))
    G = pd.DataFrame(gate)
    to_csv(G, 'r2_kr_excl_gate.csv')
    # ---------------- limit-lock audit (entries at a locked limit-up close, exits at a locked limit-down) ----------
    LU, LD = X['LU_LOCK_T'], X['LD_LOCK_T']
    aud = []
    for b in base_mem:
        best = G[(G.base == b) & (G['rank'] == 1)]['filter'].iloc[0]
        for f in ('none', best):
            mem = base_mem[b][0] if f == 'none' else (base_mem[b][0] & ~FL[f])
            ne = nl = xe = xl = 0
            for k in range(1, P.K):
                new = mem[k] & ~mem[k - 1]; out = mem[k - 1] & ~mem[k]
                ne += new.sum(); nl += (new & LU[k]).sum(); xe += out.sum(); xl += (out & LD[k]).sum()
            aud.append(dict(base=b, filter=f, entries=int(ne), entries_at_locked_limit_up=int(nl),
                            share_entries_locked=nl / max(ne, 1), exits=int(xe), exits_at_locked_limit_down=int(xl),
                            share_exits_locked=xl / max(xe, 1)))
    to_csv(pd.DataFrame(aud), 'r2_kr_excl_limitlock.csv')
    pd.set_option('display.width', 260)
    show = S[(S.cost == 'net35') & S.primary][['base', 'filter', 'ann_diff', 'ir', 'nw_t', 'boot_p', 'pct_years_pos',
                                                 'sharpe_filtered', 'sharpe_unfiltered', 'maxdd_diff', 'te',
                                                 'excl_share_names', 'excl_share_weight', 'turnover_filtered', 'turnover_unfiltered']]
    print(show.round(4).to_string())
    print(G[['base', 'rank', 'filter', 'ann_diff_net35', 'ir_net35', 'steps_passed', 'verdict', 'g1_walkforward_selected_oos_ir',
             'g2_boot_ci90', 'g3_dsr', 'g4_pbo_primary8', 'g4_pbo_all_variants', 'g5_boot_p', 'g7_plateau_share',
             'g8_pct_years_pos']].round(3).to_string())
    log(f'trials: {n_trials}; done in {time.time() - t0:.0f}s')


if __name__ == '__main__':
    main()
