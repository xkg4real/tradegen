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


XR = R.sub(EWU, axis=0).fillna(0.0).clip(lower=-0.99)
cx = np.log1p(XR).cumsum()
def fwd(h): return np.expm1(cx.shift(-h) - cx)
F = {1: fwd(1), 5: fwd(5), 20: fwd(20)}
def ev(mask, name, univ, a='2015-07-01', b='2026-08-31', Fd=None, tag=''):
    m = (mask & univ).loc[a:b].values
    out = []
    for h, Fh in (Fd or F).items():
        v = Fh.loc[a:b].values
        ok = m & np.isfinite(v)
        n = ok.sum()
        if n == 0: continue
        vals = v[ok]
        cnt = ok.sum(axis=1); sm = np.where(ok, v, 0).sum(axis=1)
        dm = sm[cnt > 0] / cnt[cnt > 0]
        out.append(dict(rule=name + tag, horizon=f't+{h}', n_events=int(n), n_dates=int((cnt > 0).sum()),
                        mean_gross_bp=round(vals.mean()*1e4, 1), median_bp=round(np.median(vals)*1e4, 1), hit=round((vals > 0).mean(), 3),
                        date_clustered_t=round(dm.mean()/dm.std()*np.sqrt(len(dm)), 2), mean_net70_bp=round((vals.mean()-0.007)*1e4, 1)))
    return out

# Prior-design reversal: 5-day return z-score, only when volume/20d avg > 1.5 (and the low-volume mirror)
r5 = np.expm1(cum - cum.shift(5)); sd20 = R.rolling(20, min_periods=15).std()
z5 = r5 / (sd20 * np.sqrt(5))
vr = VOL / VOL.rolling(20, min_periods=15).mean().shift(1)
zr = z5.where(liquid)
q20 = zr.rank(axis=1, pct=True)
evr = []
evr += ev((q20 <= 0.2), 'Rev: bottom-quintile 5d z (all volume)', liquid)
evr += ev((q20 <= 0.2) & (vr > 1.5), 'Rev: bottom-quintile 5d z & vol/avg>1.5 (prior spec)', liquid)
evr += ev((q20 <= 0.2) & (vr < 0.67), 'Rev: bottom-quintile 5d z & vol/avg<0.67', liquid)
evr += ev((z5 <= -2.0) & (vr > 1.5), 'Rev: z5<=-2 & vol/avg>1.5', liquid)
r20 = np.expm1(cum - cum.shift(20))
evr += ev((r20 >= 0.5), 'Blow-off: 20d return >= +50%', liquid)
evr += ev((r20 <= -0.3), 'Crash: 20d return <= -30%', liquid)
for a, b in [('2015-07-01', '2019-12-31'), ('2020-01-01', '2024-12-31'), ('2025-01-01', '2026-08-31')]:
    evr += ev((q20 <= 0.2) & (vr > 1.5), f'Rev prior spec {a[:4]}-{b[:4]}', liquid, a=a, b=b, Fd={1: F[1], 5: F[5]})
et = pd.DataFrame(evr); et.to_csv(OUT + 'E7_part4_reversal_variants.csv', index=False)
pd.set_option('display.width', 260); print(et.to_string())
print('done', round(time.time()-t0, 1))
