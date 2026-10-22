# E7 desk quick-checks, part 2 (fixes the part-1 event-study stack() bug; adds splits).
# Data: /home/claude/data_raw/marcap (KRX all listed stocks, daily, survivorship-free, price returns from
# official ChangesRatio, no dividends). Universe: common stocks, KOSPI+KOSDAQ, ex SPAC/preferred,
# ex administrative-issue (관리종목/투자주의환기) flags. In-sample descriptive checks, NOT gate runs.
import pandas as pd, numpy as np, time, warnings
warnings.filterwarnings('ignore')
t0 = time.time()
OUT = '/home/claude/research_notes/QUANTGEN technical and fundamental signals/E7_quickchecks/'
BASE = '/home/claude/data_raw/marcap/data/marcap-{}.parquet'
cols = ['Code','Name','Dept','ChangesRatio','Volume','Amount','Open','High','Low','Close','Marcap','Market','Date']
frames = []
for y in range(2013, 2027):
    d = pd.read_parquet(BASE.format(y), columns=cols)
    frames.append(d[d.Market.isin(['KOSPI','KOSDAQ','KOSDAQ GLOBAL'])])
df = pd.concat(frames, ignore_index=True); del frames
df['Dept'] = df['Dept'].fillna('')
df = df[df.Code.str[-1].eq('0') & ~df.Name.str.contains('스팩') & ~df.Dept.str.contains('SPAC')]
df['flag'] = df.Dept.str.contains('관리|투자주의환기').astype(float)
df['kospi'] = (df.Market == 'KOSPI').astype(float)
r = df.ChangesRatio / 100.0
lim = np.where(df.Date >= pd.Timestamp('2015-06-15'), 0.305, 0.155)
df['r'] = r.where(r <= lim).where(df.Volume > 0)
P = lambda c: df.pivot_table(index='Date', columns='Code', values=c, aggfunc='last')
R = P('r'); MC = P('Marcap'); AMT = P('Amount'); VOL = P('Volume'); CL = P('Close'); OP = P('Open'); HI = P('High'); LO = P('Low')
FLAG = P('flag').fillna(0); KS = P('kospi').fillna(0); CR = P('ChangesRatio')
COLS = MC.columns
R, AMT, VOL, CL, OP, HI, LO, FLAG, KS, CR = [x.reindex(columns=COLS) for x in (R, AMT, VOL, CL, OP, HI, LO, FLAG, KS, CR)]
FLAG = FLAG.fillna(0); KS = KS.fillna(0)
dates = R.index
print('pivots', R.shape, round(time.time()-t0, 1))

ADV20 = AMT.rolling(20, min_periods=15).mean()
liquid = (MC >= 100e9) & (ADV20 >= 1e9) & (CL >= 1000) & (VOL > 0) & (FLAG == 0)
Rf = R.fillna(0.0)
PADJ = (1 + Rf).cumprod()
EWU = R.where(liquid.shift(1)).mean(axis=1)
logr = np.log1p(Rf); cum = logr.cumsum()

def stats(x):
    x = x.dropna()
    if len(x) < 5: return (np.nan,)*4
    ann = x.mean()*252; vol = x.std()*np.sqrt(252)
    return (round(ann*100, 1), round(vol*100, 1), round(ann/vol, 2) if vol > 0 else np.nan, round(x.mean()/x.std()*np.sqrt(len(x)), 2))

me_all = pd.Series(dates, index=dates).groupby([dates.year, dates.month]).last().values
me = [d for d in me_all if d >= pd.Timestamp('2014-06-30')]

def monthly_ports(sig, long_high, univ, extra=None, q=5, cost=0.0035, bench=None):
    out = []; prevL = set(); prevS = set()
    for i in range(len(me)-1):
        t, tn = me[i], me[i+1]
        ok = univ.loc[t] & sig.loc[t].notna()
        if extra is not None: ok &= extra.loc[t].fillna(False).astype(bool)
        s = sig.loc[t][ok]
        if len(s) < 50: continue
        qs = pd.qcut(s.rank(method='first'), q, labels=False)
        hi = set(qs[qs == q-1].index); lo = set(qs[qs == 0].index)
        L, S = (hi, lo) if long_high else (lo, hi)
        tauL = 1 - len(L & prevL)/len(L) if prevL else 1.0
        tauS = 1 - len(S & prevS)/len(S) if prevS else 1.0
        prevL, prevS = L, S
        hold = R.loc[(R.index > t) & (R.index <= tn)]
        b = (bench if bench is not None else EWU).loc[hold.index]
        f = pd.DataFrame({'L': hold[list(L)].mean(axis=1), 'S': hold[list(S)].mean(axis=1), 'B': b})
        f['cL'] = 0.0; f['cS'] = 0.0; f['tauL'] = 0.0
        f.iloc[0, 3] = 2*tauL*cost; f.iloc[0, 4] = 2*tauS*cost; f.iloc[0, 5] = tauL
        out.append(f)
    f = pd.concat(out)
    f['LSg'] = f.L - f.S; f['LSn'] = f.LSg - f.cL - f.cS
    f['LXg'] = f.L - f.B; f['LXn'] = f.LXg - f.cL
    return f

periods = {'2015-07..2019-12': ('2015-07-01', '2019-12-31'), '2020-01..2024-12': ('2020-01-01', '2024-12-31'),
           'MeltUp 2025-01-02..2026-06-22': ('2025-01-02', '2026-06-22'), 'Crash 06-23..07-30-2026': ('2026-06-23', '2026-07-30'),
           'Post 2026-07-31..09-29': ('2026-07-31', '2026-09-29')}

def monthly_ports(sig, long_high, univ, extra=None, q=5, cost=0.0035, bench=None):
    out = []; prevL = set(); prevS = set()
    for i in range(len(me)-1):
        t, tn = me[i], me[i+1]
        ok = univ.loc[t] & sig.loc[t].notna()
        if extra is not None: ok &= extra.loc[t].fillna(False).astype(bool)
        s = sig.loc[t][ok]
        if len(s) < 50: continue
        qs = pd.qcut(s.rank(method='first'), q, labels=False)
        hi = set(qs[qs == q-1].index); lo = set(qs[qs == 0].index)
        L, S = (hi, lo) if long_high else (lo, hi)
        tauL = 1 - len(L & prevL)/len(L) if prevL else 1.0
        tauS = 1 - len(S & prevS)/len(S) if prevS else 1.0
        prevL, prevS = L, S
        hold = R.loc[(R.index > t) & (R.index <= tn)]
        b = (bench if bench is not None else EWU).loc[hold.index]
        f = pd.DataFrame({'L': hold[list(L)].mean(axis=1), 'S': hold[list(S)].mean(axis=1), 'B': b})
        f['cL'] = 0.0; f['cS'] = 0.0; f['tauL'] = 0.0
        f.iloc[0, 3] = 2*tauL*cost; f.iloc[0, 4] = 2*tauS*cost; f.iloc[0, 5] = tauL
        out.append(f)
    f = pd.concat(out)
    f['LSg'] = f.L - f.S; f['LSn'] = f.LSg - f.cL - f.cS
    f['LXg'] = f.L - f.B; f['LXn'] = f.LXg - f.cL
    return f

periods = {'2015-07..2019-12': ('2015-07-01', '2019-12-31'), '2020-01..2024-12': ('2020-01-01', '2024-12-31'),
           'MeltUp 2025-01-02..2026-06-22': ('2025-01-02', '2026-06-22'), 'Crash 06-23..07-30-2026': ('2026-06-23', '2026-07-30'),
           'Post 2026-07-31..09-29': ('2026-07-31', '2026-09-29')}
rows=[]
MA = {n: PADJ.rolling(n, min_periods=n).mean() for n in [5, 20, 60, 120, 200]}
align = ((MA[5] > MA[20]) & (MA[20] > MA[60]) & (MA[60] > MA[120])).astype(float)
above200 = (PADJ > MA[200]).astype(float)
for name, sig in [('Jeongbaeyeol state (hold aligned names)', align), ('Price > MA200 state', above200)]:
    # binary signal: q=2 split -> long = signal 1 group; use rank with noise-free tie handling
    f = []
    prevL=set()
    for i in range(len(me)-1):
        t, tn = me[i], me[i+1]
        ok = liquid.loc[t] & sig.loc[t].notna()
        s = sig.loc[t][ok]
        L = set(s[s == 1].index); S = set(s[s == 0].index)
        if len(L) < 30 or len(S) < 30: continue
        tau = 1 - len(L & prevL)/len(L) if prevL else 1.0; prevL = L
        hold = R.loc[(R.index > t) & (R.index <= tn)]
        x = pd.DataFrame({'L': hold[list(L)].mean(axis=1), 'S': hold[list(S)].mean(axis=1), 'B': EWU.loc[hold.index], 'n': len(L)})
        x['c'] = 0.0; x.iloc[0, 4] = 2*tau*0.0035; x['tau'] = 0.0; x.iloc[0, 5] = tau
        f.append(x)
    f = pd.concat(f); f['LXg'] = f.L - f.B; f['LXn'] = f.LXg - f.c
    for pn, (a, b) in periods.items():
        g = f.loc[a:b]
        rows.append(dict(rule=name, period=pn, avg_names=int(g.n.mean()), LongEx_gross=stats(g.LXg), LongEx_net=stats(g.LXn),
                         cumL=round((np.prod(1+g.L)-1)*100,1), cumB=round((np.prod(1+g.B)-1)*100,1), turn_per_yr=round(f.tau.sum()/(len(f)/252),1)))
out = pd.DataFrame(rows); out.to_csv(OUT + 'E7_part6_trend_state_ports.csv', index=False)
pd.set_option('display.width', 250); print(out.to_string())
# Samsung-alone and pair share at year-ends (common shares; KOSPI all listed incl. preferreds)
ks = (KS == 1)
tot = MC.where(ks).sum(axis=1)
for d in ['2019-12-30','2020-12-30','2021-12-30','2022-12-29','2023-12-28','2024-12-30','2025-12-30','2026-06-22','2026-09-29']:
    d = pd.Timestamp(d)
    print(d.date(), 'Samsung %.1f%%  SKhynix %.1f%%  pair %.1f%%' % (MC.loc[d,'005930']/tot[d]*100, MC.loc[d,'000660']/tot[d]*100, (MC.loc[d,'005930']+MC.loc[d,'000660'])/tot[d]*100))
