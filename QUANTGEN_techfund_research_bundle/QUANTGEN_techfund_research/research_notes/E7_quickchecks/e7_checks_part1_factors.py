# E7 desk quick-checks on local marcap KRX data (survivorship-free daily, OHLCV + market cap)
# Gross and net (35 bp per side). In-sample descriptive checks, NOT gate runs.
import pandas as pd, numpy as np, time, warnings
warnings.filterwarnings('ignore')
t0 = time.time()
BASE = '/home/claude/data_raw/marcap/data/marcap-{}.parquet'
cols = ['Code','Name','Dept','ChangesRatio','Volume','Amount','Open','High','Close','Marcap','Market','Date']
frames = []
for y in range(2013, 2027):
    d = pd.read_parquet(BASE.format(y), columns=cols)
    d = d[d.Market.isin(['KOSPI','KOSDAQ','KOSDAQ GLOBAL'])]
    frames.append(d)
df = pd.concat(frames, ignore_index=True)
del frames
df['Dept'] = df['Dept'].fillna('')
common = df.Code.str[-1].eq('0') & ~df.Name.str.contains('스팩') & ~df.Dept.str.contains('SPAC')
df = df[common]
df['flag'] = df.Dept.str.contains('관리|투자주의환기').astype(float)
df['kospi'] = (df.Market == 'KOSPI').astype(float)
r = df.ChangesRatio / 100.0
lim = np.where(df.Date >= pd.Timestamp('2015-06-15'), 0.305, 0.155)
r = r.where(r <= lim)            # drop positive artifacts beyond the daily limit (relistings, IPO day)
r = r.where(df.Volume > 0)       # no trade -> no return observation
df['r'] = r
print('loaded', len(df), round(time.time()-t0,1));

P = lambda c: df.pivot_table(index='Date', columns='Code', values=c, aggfunc='last')
R = P('r'); MC = P('Marcap'); AMT = P('Amount'); VOL = P('Volume'); CL = P('Close'); OP = P('Open'); HI = P('High')
FLAG = P('flag').fillna(0); KS = P('kospi')
CR = P('ChangesRatio')
dates = R.index
print('pivots', R.shape, round(time.time()-t0,1))

ADV20 = AMT.rolling(20, min_periods=15).mean()
liquid = (MC >= 100e9) & (ADV20 >= 1e9) & (CL >= 1000) & (VOL > 0) & (FLAG == 0)
# adjusted price index from official change ratios
Rf = R.fillna(0.0)
PADJ = (1 + Rf).cumprod()
EWU = R.where(liquid.shift(1)).mean(axis=1)   # EW return of names liquid at t-1 (benchmark for day t)

# ---------- 1. Monthly factor portfolios ----------
logr = np.log1p(Rf)
cum = logr.cumsum()
MOM = cum.shift(21) - cum.shift(252)                 # 12-1
NOBS = R.notna().rolling(252).sum()
STR = cum - cum.shift(21)                            # 1-month return
WK = cum - cum.shift(5)
LVOL = R.rolling(60, min_periods=50).std()
SIZE = np.log(MC)
me = pd.Series(dates, index=dates).groupby([dates.year, dates.month]).last().values
me = [d for d in me if d >= pd.Timestamp('2014-06-30')]

def factor_series(sig, long_high=True, univ=liquid, extra=None, q=5, cost=0.0035, top_n=None):
    rets_ls, rets_l, costs_ls, costs_l, dts = [], [], [], [], []
    prevL, prevS = set(), set()
    out = []
    for i in range(len(me)-1):
        t, tn = me[i], me[i+1]
        u = univ.loc[t]
        ok = u & sig.loc[t].notna()
        if extra is not None: ok &= extra.loc[t]
        s = sig.loc[t][ok]
        if len(s) < 50: continue
        if top_n:
            s = s.sort_values(ascending=False).iloc[:top_n]
        qs = pd.qcut(s.rank(method='first'), q, labels=False)
        hi = set(qs[qs == q-1].index); lo = set(qs[qs == 0].index)
        L, S = (hi, lo) if long_high else (lo, hi)
        tauL = 1 - len(L & prevL)/len(L) if prevL else 1.0
        tauS = 1 - len(S & prevS)/len(S) if prevS else 1.0
        prevL, prevS = L, S
        hold = R.loc[(R.index > t) & (R.index <= tn)]
        bench = EWU.loc[hold.index]
        rl = hold[list(L)].mean(axis=1); rs = hold[list(S)].mean(axis=1)
        cL = 2*tauL*cost; cS = 2*tauS*cost
        f = pd.DataFrame({'L': rl, 'S': rs, 'B': bench})
        f['cL'] = 0.0; f['cS'] = 0.0
        f.iloc[0, f.columns.get_loc('cL')] = cL; f.iloc[0, f.columns.get_loc('cS')] = cS
        f['tauL'] = 0.0; f.iloc[0, f.columns.get_loc('tauL')] = tauL
        out.append(f)
    return pd.concat(out)

def stats(x):
    x = x.dropna()
    if len(x) < 5: return (np.nan,)*4
    ann = x.mean()*252; vol = x.std()*np.sqrt(252)
    sr = ann/vol if vol > 0 else np.nan
    t = x.mean()/x.std()*np.sqrt(len(x))
    return round(ann*100,1), round(vol*100,1), round(sr,2), round(t,2)

def cumret(x):
    return round((np.prod(1+x.dropna())-1)*100,1)

periods = {
 'P0 2015-07..2019-12': ('2015-07-01','2019-12-31'),
 'P0b 2020-01..2024-12': ('2020-01-01','2024-12-31'),
 'MeltUp 2025-01-02..2026-06-22': ('2025-01-02','2026-06-22'),
 'Crash 2026-06-23..07-30': ('2026-06-23','2026-07-30'),
 'Post 2026-07-31..09-29': ('2026-07-31','2026-09-29'),
}
res = []
specs = {
 'MOM 12-1 (long winners)': (MOM, True, NOBS >= 200),
 'STR 1m (long losers)': (STR, False, None),
 'LowVol 60d (long low)': (LVOL, False, None),
 'Size (long small)': (SIZE, False, None),
}
fac = {}
for name, (sig, lh, ex) in specs.items():
    f = factor_series(sig, long_high=lh, extra=ex)
    fac[name] = f
    f['LS_g'] = f.L - f.S; f['LS_n'] = f.L - f.S - f.cL - f.cS
    f['LX_g'] = f.L - f.B; f['LX_n'] = f.L - f.cL - f.B
    yr_turn = f.tauL.sum() / (len(f)/252)
    for pn, (a, b) in periods.items():
        g = f.loc[a:b]
        if len(g) == 0: continue
        res.append(dict(factor=name, period=pn, days=len(g),
            LS_gross=stats(g.LS_g), LS_net=stats(g.LS_n),
            LongEx_gross=stats(g.LX_g), LongEx_net=stats(g.LX_n),
            cum_L=cumret(g.L), cum_S=cumret(g.S), cum_B=cumret(g.B), cum_LSn=cumret(g.LS_n), cum_LXn=cumret(g.LX_n),
            oneway_turn_per_yr_L=round(yr_turn,2)))
pd.set_option('display.width', 250); pd.set_option('display.max_columns', 30)
fr = pd.DataFrame(res)
print(fr.to_string())
fr.to_csv('/home/claude/research_notes/QUANTGEN technical and fundamental signals/E7_quickchecks/E7_factor_quickcheck.csv', index=False)
print('factors done', round(time.time()-t0,1))

# weekly reversal, weekly rebalance (cost check)
wk_dates = pd.Series(dates, index=dates).groupby([dates.isocalendar().year.values, dates.isocalendar().week.values]).last().values
wk_dates = [d for d in wk_dates if d >= pd.Timestamp('2015-07-01')]
def weekly_rev(univ=liquid, q=5, cost=0.0035):
    out=[]; prevL=set(); prevS=set()
    for i in range(len(wk_dates)-1):
        t, tn = wk_dates[i], wk_dates[i+1]
        ok = univ.loc[t] & WK.loc[t].notna()
        s = WK.loc[t][ok]
        if len(s) < 50: continue
        qs = pd.qcut(s.rank(method='first'), q, labels=False)
        L = set(qs[qs==0].index); S = set(qs[qs==q-1].index)
        tauL = 1 - len(L & prevL)/len(L) if prevL else 1.0
        tauS = 1 - len(S & prevS)/len(S) if prevS else 1.0
        prevL, prevS = L, S
        hold = R.loc[(R.index > t) & (R.index <= tn)]
        f = pd.DataFrame({'L': hold[list(L)].mean(axis=1), 'S': hold[list(S)].mean(axis=1), 'B': EWU.loc[hold.index]})
        f['c'] = 0.0; f.iloc[0, 3] = 2*tauL*cost; f['cS']=0.0; f.iloc[0,4]=2*tauS*cost; f['tau']=0.0; f.iloc[0,5]=tauL
        out.append(f)
    return pd.concat(out)
w = weekly_rev()
w['LXg'] = w.L - w.B; w['LXn'] = w.L - w.c - w.B; w['LSg'] = w.L - w.S; w['LSn'] = w.L - w.S - w.c - w.cS
print('WEEKLY REVERSAL (5d, long losers), one-way turnover/yr L:', round(w.tau.sum()/(len(w)/252),1))
for pn,(a,b) in periods.items():
    g = w.loc[a:b]
    print(pn, 'LS gross', stats(g.LSg), 'LS net', stats(g.LSn), 'LongEx gross', stats(g.LXg), 'LongEx net', stats(g.LXn))

# (event studies moved to e7_checks_part2.py / part3.py; the part-1 version had a stack() bug)
# ---------- 3. Breadth in the melt-up ----------
for a,b in [('2025-01-02','2025-12-30'),('2025-12-30','2026-06-22'),('2026-06-22','2026-07-30'),('2026-07-30','2026-09-29')]:
    ks = (KS.loc[a] == 1)
    names = ks[ks].index
    pa = CL.loc[a, names]; pb = CL.loc[b, names]
    # use adjusted index for returns
    ra = (PADJ.loc[b, names]/PADJ.loc[a, names] - 1).dropna()
    w0 = MC.loc[a, names].reindex(ra.index)
    cw = (ra*w0).sum()/w0.sum()
    pair = [c for c in ['005930','000660'] if c in ra.index]
    cw_ex = (ra.drop(pair)*w0.drop(pair)).sum()/w0.drop(pair).sum()
    print(f'KOSPI common {a}->{b}: n={len(ra)} EW mean {ra.mean()*100:.1f}% median {ra.median()*100:.1f}% share down {(ra<0).mean()*100:.1f}%  CW {cw*100:.1f}%  CW ex-pair {cw_ex*100:.1f}%  pair: ' + ', '.join(f"{c} {ra[c]*100:.0f}%" for c in pair))
print('done', round(time.time()-t0,1))
