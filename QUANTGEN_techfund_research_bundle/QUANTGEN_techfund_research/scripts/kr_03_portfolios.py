"""kr_03_portfolios.py -- quintile portfolios for every signal, universe and weighting.

Mechanics (per portfolio "book", formation at the close of t_k, holding t_k+1 .. t_{k+1}):
  * Members: stocks of the universe at t_k in the given quintile; quintiles are percentile-rank groups computed
    over universe members with a finite signal only (average ranks; tied values share a quintile; seeded random
    tie-break only when a tie block would leave a quintile under half its normal size, see quantile_groups).
  * Weights: EW = 1/n; VW = Marcap_t / sum Marcap_t.
  * Buy-and-hold with daily compounding inside the period (weights drift). Daily book return =
    sum_i v_i,d-1 r_i,d / sum_i v_i,d-1 with missing returns = 0.
  * Delisting: once a stock stops existing inside the period its value is frozen (cash, 0%); it is sold
    at the next rebalance (counted in turnover). Each disappearance is classified as 'distressed' if the
    stock had a beyond-limit move without corporate action in its last 30 listed days (liquidation trading,
    정리매매), else 'other' (merger, voluntary delisting, transfer to an unlisted status).
    Bias bound: results/kr_delisting_exposure_{freq}.csv gives, per book, the average book-value share per year
    that disappeared (dead_share_per_year) and the part whose last listed day had no trade, i.e. a stale exit
    price (stale_exit_share_per_year). If every stale exit were really worth 0, the book's annual return would
    be lower by at most stale_exit_share_per_year (in return units per year).
  * Halted at a rebalance (exists but Volume = 0 at t_k): the position cannot be traded, so it is carried
    at its drifted value through the next period (earning the resumption-day move) and sold at the first
    rebalance where it trades. Members are always tradable (the universe requires Volume_t > 0).
  * Turnover per rebalance = sum over listed, tradable names of |w_new - w_drifted_old| (fractions of book
    value); a delisted position is cash, so only its redeployment (buy side) is charged; the first formation
    counts the initial purchase (turnover 1).
Monthly signals also get exclusion-screen books NOTQ1 / NOTQ5 = universe minus quintile 1 / 5 (long-only
use of a signal whose spread comes from the short leg: hold everything except the worst quintile).
Outputs (cache/): port_daily_{monthly,weekly}.parquet (gross daily returns per book, NaN outside the
sample), port_turnover_{freq}.npz (turnover per book per rebalance), and results/kr_disappearances.csv.
"""
import sys, time
import numpy as np
import pandas as pd
sys.path.insert(0, '/home/claude/datalab/scripts')
from scipy.stats import rankdata
from kr_common import CACHE, RES, SEED, load_meta, open_mat

MONTHLY_SIGNALS = ['MOM_12_1', 'MOM_6_1', 'REV_1M', 'HIGH52', 'VOL_3M', 'MAX_1M', 'TURN_1M', 'SIZE', 'PMA200',
                   'RSI14', 'BBPCTB']
UNIVS = {'ALL': 'univ_all', 'LARGE': 'univ_large'}
WEIGHTINGS = ('EW', 'VW')


def log(*a):
    print(time.strftime('%H:%M:%S'), *a, flush=True)


def quantile_groups(s, U, nq, k=0, return_fallback=False):
    """Group 1..nq of s within mask U (finite values only); 0 = not assigned.

    Percentile ranks are computed among universe members only: group = floor(nq * (rank - 0.5) / n) + 1 with
    average ranks, so tied values share the group that contains their average rank. If a tie block would leave
    a group with fewer than half its normal size (stocks tied at the daily price limit in MAX_1M during the
    narrow-limit 1990s), ties are broken by a fixed pseudo-random draw per (formation k, stock) instead
    (seed 20261002 + k), which keeps every group populated and the result reproducible.
    """
    g = np.zeros(s.shape, np.int8)
    m = U & np.isfinite(s)
    n = int(m.sum())
    if n < nq * 5:
        return (g, False) if return_fallback else g
    x = s[m].astype(np.float64)
    r = rankdata(x, method='average')
    gm = np.floor((r - 0.5) / n * nq).astype(np.int64) + 1
    cnt = np.bincount(gm, minlength=nq + 1)[1:]
    fallback = bool(cnt.min() < 0.5 * n / nq)
    if fallback:
        u = np.random.default_rng(SEED + int(k)).random(s.shape[0])[m]
        o = np.lexsort((u, x))                     # sort by value, ties by the random key
        r2 = np.empty(n); r2[o] = np.arange(1, n + 1)
        gm = np.floor((r2 - 0.5) / n * nq).astype(np.int64) + 1
    g[m] = gm
    return (g, fallback) if return_fallback else g


class Book:
    __slots__ = ('v', 'started')

    def __init__(self, N):
        self.v = np.zeros(N)
        self.started = False

    def rebalance(self, members, base_w, E_t, TR_t):
        v = self.v
        stuck = (v > 0) & E_t & ~TR_t
        stuck_val = v[stuck].sum() if self.started else 0.0
        w = np.zeros_like(v)
        if len(members):
            w[members] = (1.0 - stuck_val) * base_w
        else:                                   # no members: hold cash (never happens in practice)
            pass
        # delisted positions are already cash (frozen value): redeploying them costs only the buy side
        ns = ~stuck & E_t
        to = np.abs(w[ns] - v[ns]).sum()
        w[stuck] = v[stuck]
        self.v = w
        self.started = True
        return to, int(stuck.sum())

    def hold(self, G):
        idx = np.flatnonzero(self.v)
        if len(idx) == 0:
            return np.zeros(G.shape[0])
        vals = self.v[idx][None, :] * G[:, idx]
        pv = vals.sum(axis=1)
        prev = np.concatenate(([self.v[idx].sum()], pv[:-1]))
        r = pv / prev - 1.0
        nv = np.zeros_like(self.v)
        nv[idx] = vals[-1] / pv[-1]
        self.v = nv
        return r


def base_weights(members, wt, mcap):
    if wt == 'EW':
        return np.full(len(members), 1.0 / len(members))
    m = mcap[members].astype(np.float64)
    return m / m.sum()


def run_freq(freq, strict=False):
    t0 = time.time()
    sfx = '_strict' if strict else ''
    dates, codes = load_meta()
    T, N = len(dates), len(codes)
    R = np.asarray(open_mat('ret' + sfx))            # 136 MB float32
    E = np.asarray(open_mat('exists'))
    TR = np.asarray(open_mat('traded'))
    BNC = np.asarray(open_mat('beyond_nonca'))
    CLm = open_mat('cumlog' + sfx)
    F = np.load(f'{CACHE}/form_{freq}{sfx}.npz')
    fidx = F['fidx']; K = len(fidx)
    mcap = F['mcap']
    if freq == 'monthly':
        groups = []                                 # (signal label, nq, function(k, U) -> group array)
        for s in MONTHLY_SIGNALS:
            arr = F[s]
            groups.append((s, lambda k, U, arr=arr: quantile_groups(arr[k], U, 5, k)))
    else:
        rev, vs = F['REV_1W'], F['VSPIKE']
        groups = [('REV_1W', lambda k, U: quantile_groups(rev[k], U, 5, k))]
        for j, lab in ((1, 'VSlow'), (2, 'VSmid'), (3, 'VShigh')):
            def f(k, U, j=j):
                ter = quantile_groups(vs[k], U & np.isfinite(rev[k]), 3, k)
                return quantile_groups(rev[k], U & (ter == j), 5, k)
            groups.append((f'REV_1W_{lab}', f))
    names, books = [], []
    for u in UNIVS:
        for wt in WEIGHTINGS:
            names.append(f'{freq}|UNIV|{u}|{wt}|ALL'); books.append(Book(N))
    for sig, _ in groups:
        for u in UNIVS:
            for wt in WEIGHTINGS:
                for q in range(1, 6):
                    names.append(f'{freq}|{sig}|{u}|{wt}|Q{q}'); books.append(Book(N))
                if freq == 'monthly':                 # exclusion screens: universe minus one extreme quintile
                    for q in (1, 5):
                        names.append(f'{freq}|{sig}|{u}|{wt}|NOTQ{q}'); books.append(Book(N))
    pos = {n: i for i, n in enumerate(names)}
    S = len(names)
    D = np.full((S, T), np.nan)
    TO = np.full((S, K), np.nan)
    NSTUCK = np.zeros((S, K), np.int32)
    NMEM = np.zeros((S, K), np.int32)
    WDEAD = np.zeros((S, K))          # book-value share of positions that disappeared during the period
    WSTALE = np.zeros((S, K))         # ... of which the last listed day had no trade (stale exit price)

    def hold_track(i, G, A, t, k):
        b = books[i]
        v0 = b.v
        dead = np.flatnonzero((v0 > 0) & ~A[-1])
        r = b.hold(G)
        if len(dead):
            pv = np.cumprod(1.0 + r) * v0.sum()
            for j in dead:
                l = int(A[:, j].sum()) - 1                      # last alive day index within the period
                if l < 0:
                    share = v0[j] / v0.sum(); traded_last = bool(TR[t, j])
                else:
                    share = v0[j] * G[l, j] / pv[l]; traded_last = bool(TR[t + 1 + l, j])
                WDEAD[i, k] += share
                if not traded_last:
                    WSTALE[i, k] += share
        return r

    disp = {}                                     # (sig, univ, q) -> [member-periods, disappeared, halted at end,
                                                    #   distressed disappearances, sum of last-21-day returns]
    for k in range(K):
        t = fidx[k]
        te = fidx[k + 1] if k + 1 < K else T - 1
        Rb = np.nan_to_num(R[t + 1:te + 1].astype(np.float64), nan=0.0)
        A = np.cumprod(E[t + 1:te + 1], axis=0).astype(bool)      # alive (no gap) since t
        G = np.cumprod(1.0 + Rb * A, axis=0)
        E_t, TR_t = E[t], TR[t]
        alive_end, tr_end = A[-1], TR[te]
        nalive = A.sum(axis=0)
        gone = np.flatnonzero(~alive_end & E[t])
        last = t + nalive[gone]
        distressed = np.array([BNC[max(0, l - 29):l + 1, c].any() for l, c in zip(last, gone)], bool)
        r21 = np.array([np.expm1(CLm[l, c] - CLm[max(0, l - 21), c]) for l, c in zip(last, gone)])
        dmap = dict(zip(gone, zip(distressed, r21)))
        for u, key in UNIVS.items():
            U = F[key][k]
            mem = np.flatnonzero(U)
            for wt in WEIGHTINGS:
                i = pos[f'{freq}|UNIV|{u}|{wt}|ALL']
                TO[i, k], NSTUCK[i, k] = books[i].rebalance(mem, base_weights(mem, wt, mcap[k]), E_t, TR_t)
                D[i, t + 1:te + 1] = hold_track(i, G, A, t, k)
                NMEM[i, k] = len(mem)
            for sig, gf in groups:
                g = gf(k, U)
                for q in range(1, 6):
                    m = np.flatnonzero(g == q)
                    c = disp.setdefault((sig, u, q), [0, 0, 0, 0, 0.0])
                    c[0] += len(m); c[1] += int((~alive_end[m]).sum()); c[2] += int((alive_end[m] & ~tr_end[m]).sum())
                    for j in m[~alive_end[m]]:
                        c[3] += int(dmap[j][0]); c[4] += float(dmap[j][1])
                    for wt in WEIGHTINGS:
                        i = pos[f'{freq}|{sig}|{u}|{wt}|Q{q}']
                        if len(m) == 0:
                            continue
                        TO[i, k], NSTUCK[i, k] = books[i].rebalance(m, base_weights(m, wt, mcap[k]), E_t, TR_t)
                        D[i, t + 1:te + 1] = hold_track(i, G, A, t, k)
                        NMEM[i, k] = len(m)
                if freq == 'monthly':
                    for q in (1, 5):
                        m = np.flatnonzero(U & (g != q))      # names with a missing signal stay in
                        for wt in WEIGHTINGS:
                            i = pos[f'{freq}|{sig}|{u}|{wt}|NOTQ{q}']
                            TO[i, k], NSTUCK[i, k] = books[i].rebalance(m, base_weights(m, wt, mcap[k]), E_t, TR_t)
                            D[i, t + 1:te + 1] = hold_track(i, G, A, t, k)
                            NMEM[i, k] = len(m)
        if k % 100 == 0:
            log(f'{freq} period {k}/{K} {dates[t].date()}')
    df = pd.DataFrame(D.T, index=dates, columns=names)
    df.index.name = 'date'
    df.to_parquet(f'{CACHE}/port_daily_{freq}{sfx}.parquet')
    np.savez(f'{CACHE}/port_turnover_{freq}{sfx}.npz', names=np.array(names), fidx=fidx, turnover=TO,
             n_stuck=NSTUCK, n_members=NMEM, w_dead=WDEAD, w_stale=WSTALE)
    A_ = 12 if freq == 'monthly' else 52
    pd.DataFrame({'book': names, 'n_periods': (NMEM > 0).sum(1),
                  'dead_share_per_year': WDEAD.sum(1) / K * A_, 'stale_exit_share_per_year': WSTALE.sum(1) / K * A_,
                  'periods_with_stuck_positions': (NSTUCK > 0).sum(1)}).to_csv(
        f'{RES}/kr_delisting_exposure_{freq}{sfx}.csv', index=False, float_format='%.6g')
    rows = [(freq, s, u, q, v[0], v[1], v[3], v[1] - v[3], v[4] / v[1] if v[1] else np.nan, v[2])
            for (s, u, q), v in disp.items()]
    out = pd.DataFrame(rows, columns=['freq', 'signal', 'universe', 'quintile', 'member_periods',
                                      'disappeared_in_period', 'disappeared_distressed_liquidation',
                                      'disappeared_other_merger_voluntary', 'mean_return_last_21d_before_exit',
                                      'halted_at_period_end'])
    log(f'{freq}: {S} books, {K} periods, {time.time() - t0:.0f}s')
    return out


if __name__ == '__main__':
    strict = '--strict' in sys.argv
    sfx = '_strict' if strict else ''
    outs = [run_freq('monthly', strict), run_freq('weekly', strict)]
    pd.concat(outs).to_csv(f'{RES}/kr_disappearances{sfx}.csv', index=False)
