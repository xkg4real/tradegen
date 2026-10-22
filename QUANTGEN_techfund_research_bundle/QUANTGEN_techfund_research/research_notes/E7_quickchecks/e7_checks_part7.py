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
# Month-formed EW benchmark: all liquid names at month-end t, equal weight, held through month (daily-rebalanced within month like the legs)
parts=[]
for i in range(len(me)-1):
    t, tn = me[i], me[i+1]
    names = liquid.loc[t][liquid.loc[t]].index
    hold = R.loc[(R.index > t) & (R.index <= tn), names]
    parts.append(hold.mean(axis=1))
EWM = pd.concat(parts)
print('Benchmark compare (cum %): daily-reformed EWU vs month-formed EWM')
for pn,(a,b) in periods.items():
    print(f'  {pn}: EWU {(np.prod(1+EWU.loc[a:b])-1)*100:.1f}  EWM {(np.prod(1+EWM.loc[a:b])-1)*100:.1f}')
MOM = cum.shift(21) - cum.shift(252); NOBS = R.notna().rolling(252).sum()
STR = cum - cum.shift(21); LVOL = R.rolling(60, min_periods=50).std(); MAXR = R.rolling(21, min_periods=15).max()
HI52 = PADJ / PADJ.rolling(252, min_periods=200).max(); TURN12 = (AMT / MC).rolling(252, min_periods=200).mean()
terc = TURN12.rank(axis=1, pct=True)
fam = {'MOM12-1': monthly_ports(MOM, True, liquid, extra=NOBS >= 200, bench=EWM),
       'MOM12-1 low-turnover tercile': monthly_ports(MOM, True, liquid, extra=(NOBS >= 200) & (terc <= 1/3), bench=EWM),
       'MOM12-1 high-turnover tercile': monthly_ports(MOM, True, liquid, extra=(NOBS >= 200) & (terc > 2/3), bench=EWM),
       'STR1m': monthly_ports(STR, False, liquid, bench=EWM), 'LowVol60': monthly_ports(LVOL, False, liquid, bench=EWM),
       'lowMAX21': monthly_ports(MAXR, False, liquid, bench=EWM), '52wHigh': monthly_ports(HI52, True, liquid, extra=NOBS >= 200, bench=EWM)}
rows=[]
for k,v in fam.items():
    for pn,(a,b) in periods.items():
        g=v.loc[a:b]
        rows.append(dict(family=k, period=pn, LongEx_vsEWM_gross=stats(g.LXg), LongEx_vsEWM_net35=stats(g.LXn), cumL=round((np.prod(1+g.L)-1)*100,1), cumEWM=round((np.prod(1+g.B)-1)*100,1), cumL_net=round((np.prod(1+g.L-g.cL)-1)*100,1)))
    full = v.loc['2015-07-01':'2024-12-31']
    rows.append(dict(family=k, period='FULL 2015-07..2024-12', LongEx_vsEWM_gross=stats(full.LXg), LongEx_vsEWM_net35=stats(full.LXn), cumL=round((np.prod(1+full.L)-1)*100,1), cumEWM=round((np.prod(1+full.B)-1)*100,1), cumL_net=round((np.prod(1+full.L-full.cL)-1)*100,1)))
out=pd.DataFrame(rows); out.to_csv(OUT+'E7_part7_longonly_vs_monthformed_EW.csv', index=False)
pd.set_option('display.width',250); print(out.to_string())
yr = pd.DataFrame({k: v.LXn.groupby(v.index.year).apply(lambda x: (np.prod(1+x)-1)*100) for k,v in fam.items()}).round(1)
print(yr.to_string()); print('share of 2015-2025 years positive (net vs EWM):', (yr.loc[2015:2025]>0).mean().round(2).to_dict())
yr.to_csv(OUT+'E7_part7_calendar_years_net_vs_EWM.csv')
