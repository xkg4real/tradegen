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
for y in range(2011, 2027):
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
parts=[]
for i in range(len(me)-1):
    t, tn = me[i], me[i+1]
    names = liquid.loc[t][liquid.loc[t]].index
    parts.append(R.loc[(R.index > t) & (R.index <= tn), names].mean(axis=1))
EWM = pd.concat(parts)
LTR = cum.shift(252) - cum.shift(756)              # 36-month return skipping the latest 12 months (value proxy)
NO3 = R.notna().rolling(756).sum()
STR = cum - cum.shift(21)
rows=[]
def rep(name, f):
    for pn,(a,b) in list(periods.items()) + [('FULL 2015-07..2024-12', ('2015-07-01','2024-12-31'))]:
        g=f.loc[a:b]
        if len(g)==0: continue
        rows.append(dict(family=name, period=pn, LongEx_gross=stats(g.LXg), LongEx_net35=stats(g.LXn), LS_gross=stats(g.LSg),
                         cumL=round((np.prod(1+g.L)-1)*100,1), cumB=round((np.prod(1+g.B)-1)*100,1), cumL_net=round((np.prod(1+g.L-g.cL)-1)*100,1),
                         turn=round(f.tauL.sum()/(len(f)/252),1)))
rep('LTR 36-12 losers (value proxy)', monthly_ports(LTR, False, liquid, extra=NO3 >= 600, bench=EWM))
for mk, flagv in [('KOSPI', 1), ('KOSDAQ', 0)]:
    um = liquid & (KS == flagv)
    parts=[]
    for i in range(len(me)-1):
        t, tn = me[i], me[i+1]
        names = um.loc[t][um.loc[t]].index
        parts.append(R.loc[(R.index > t) & (R.index <= tn), names].mean(axis=1))
    bm = pd.concat(parts)
    rep(f'STR1m {mk}-only', monthly_ports(STR, False, um, bench=bm))
out=pd.DataFrame(rows); out.to_csv(OUT+'E7_part8_value_proxy_and_market_split.csv', index=False)
pd.set_option('display.width',250); print(out.to_string())
# end-2023 / end-2024 pair share with all-KOSPI-listings denominator (incl. preferreds)
import pandas as pd2
for y, d in [(2023,'2023-12-28'), (2024,'2024-12-30'), (2025,'2025-12-30'), (2026,'2026-06-22')]:
    x = pd.read_parquet(BASE.format(y), columns=['Code','Marcap','Market','Date']); x = x[(x.Market=='KOSPI') & (x.Date==d)]
    tot = x.Marcap.sum(); s = x[x.Code=='005930'].Marcap.sum(); h = x[x.Code=='000660'].Marcap.sum()
    print(d, 'all-listings denominator: Samsung %.1f%% SKhynix %.1f%% pair %.1f%% total KRW %.0ftn' % (s/tot*100, h/tot*100, (s+h)/tot*100, tot/1e12))
