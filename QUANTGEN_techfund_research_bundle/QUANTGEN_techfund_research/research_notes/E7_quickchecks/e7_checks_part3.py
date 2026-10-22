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

# ---------- D. Retail technical rules: event studies (fixed) ----------
XR = R.sub(EWU, axis=0).fillna(0.0).clip(lower=-0.99)
cx = np.log1p(XR).cumsum()
def fwd(h): return np.expm1(cx.shift(-h) - cx)
F = {1: fwd(1), 5: fwd(5), 20: fwd(20)}
intr = ((CL / OP - 1).shift(-1)).sub(EWU.shift(-1), axis=0)          # open->close t+1 minus EW close-close t+1 (approx.)
F5o = np.expm1(np.log1p(intr.clip(lower=-0.99)) + (cx.shift(-5) - cx.shift(-1)))
F20o = np.expm1(np.log1p(intr.clip(lower=-0.99)) + (cx.shift(-20) - cx.shift(-1)))
gapn = OP.shift(-1) / CL - 1
MA = {n: PADJ.rolling(n, min_periods=n).mean() for n in [5, 20, 60, 120]}
gc520 = (MA[5] > MA[20]) & (MA[5].shift(1) <= MA[20].shift(1))
dc520 = (MA[5] < MA[20]) & (MA[5].shift(1) >= MA[20].shift(1))
gc2060 = (MA[20] > MA[60]) & (MA[20].shift(1) <= MA[60].shift(1))
al = (MA[5] > MA[20]) & (MA[20] > MA[60]) & (MA[60] > MA[120]); al_on = al & ~al.shift(1, fill_value=False)
vavg = VOL.rolling(20, min_periods=15).mean().shift(1)
vspike = (VOL >= 5*vavg) & (R >= 0.05)
post = pd.DataFrame(np.repeat((dates >= pd.Timestamp('2015-06-15'))[:, None], CR.shape[1], axis=1), index=dates, columns=CR.columns)
limitup = (CR >= 29.5) & (CL >= HI) & post
limitdn = (CR <= -29.5) & (CL <= LO) & post
small_ok = (MC >= 30e9) & (AMT >= 1e9) & (FLAG == 0)
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
evr = []
evr += ev(gc520, 'Golden cross MA5>MA20', liquid)
evr += ev(dc520, 'Dead cross MA5<MA20', liquid)
evr += ev(gc2060, 'Golden cross MA20>MA60', liquid)
evr += ev(al_on, 'Jeongbaeyeol onset 5>20>60>120', liquid)
evr += ev(vspike, 'Volume spike >=5x avg & r>=+5%', liquid)
evr += ev(limitup, 'Limit-up locked close', small_ok)
evr += ev(limitup, 'Limit-up locked close', small_ok, Fd={5: F5o, 20: F20o}, tag=' [entry next open]')
evr += ev(limitdn, 'Limit-down locked close', small_ok)
for a, b in [('2015-07-01', '2019-12-31'), ('2020-01-01', '2024-12-31'), ('2025-01-01', '2026-08-31')]:
    evr += ev(limitup, f'Limit-up {a[:4]}-{b[:4]}', small_ok, a=a, b=b, Fd={5: F5o, 20: F20o}, tag=' [entry next open]')
    evr += ev(vspike, f'Volume spike {a[:4]}-{b[:4]}', liquid, a=a, b=b, Fd={5: F[5], 20: F[20]})
et = pd.DataFrame(evr); et.to_csv(OUT + 'E7_part2_retail_rule_events.csv', index=False); print(et.to_string())
m = (limitup & small_ok).loc['2015-07-01':'2026-08-31'].values
g = gapn.loc['2015-07-01':'2026-08-31'].values[m]; g = g[np.isfinite(g)]
print(f'Limit-up next-open gap: n={len(g)} mean {g.mean()*100:.2f}% median {np.median(g)*100:.2f}% share gap>=+10% {(g>=0.10).mean():.3f} share gap<0 {(g<0).mean():.3f}')
print('limit-up locked closes per year:', (limitup & (MC > 0)).loc['2015-06-15':].sum(axis=1).groupby(lambda d: d.year).sum().to_dict())
print('limit-down locked closes per year:', (limitdn & (MC > 0)).loc['2015-06-15':].sum(axis=1).groupby(lambda d: d.year).sum().to_dict())

# ---------- E. Breadth (KOSPI common stocks) ----------
for a, b in [('2025-01-02', '2025-12-30'), ('2025-12-30', '2026-06-22'), ('2026-06-22', '2026-07-30'), ('2026-07-30', '2026-09-29')]:
    a_, b_ = pd.Timestamp(a), pd.Timestamp(b)
    names = KS.loc[a_][KS.loc[a_] == 1].index
    ra = (PADJ.loc[b_, names] / PADJ.loc[a_, names] - 1)
    ra = ra[(MC.loc[a_, names] > 0) & R.loc[a_:b_, names].notna().any()].dropna()
    w0 = MC.loc[a_, ra.index]
    pair = [c for c in ['005930', '000660'] if c in ra.index]
    cw = (ra*w0).sum()/w0.sum(); cwx = (ra.drop(pair)*w0.drop(pair)).sum()/w0.drop(pair).sum()
    print(f'KOSPI common {a}->{b}: n={len(ra)} EW {ra.mean()*100:.1f}% median {ra.median()*100:.1f}% share<0 {(ra<0).mean()*100:.1f}% CW {cw*100:.1f}% CW-ex-pair {cwx*100:.1f}% | ' + ', '.join(f'{c} {ra[c]*100:.0f}%' for c in pair))


# ---------- F. Effective spread proxy (Abdi-Ranaldo 2017, close-high-low) by size bucket ----------
c = np.log(CL.where(VOL > 0)); eta = (np.log(HI.where(VOL > 0)) + np.log(LO.where(VOL > 0))) / 2
prod = (c - eta) * (c - eta.shift(-1))
mkey = [dates.year, dates.month]
s2 = 4 * prod.groupby(mkey).mean()
spread = np.sqrt(s2.clip(lower=0))
mcm = MC.groupby(mkey).last(); advm = AMT.groupby(mkey).mean()
rows = []
for (lab, lo_, hi_) in [('mcap<100bn', 0, 100e9), ('100bn-500bn', 100e9, 500e9), ('500bn-2tn', 500e9, 2e12), ('>2tn', 2e12, 1e20)]:
    for per, (y0, y1) in {'2015-2019': (2015, 2019), '2020-2024': (2020, 2024), '2025-2026': (2025, 2026)}.items():
        sel = (mcm >= lo_) & (mcm < hi_)
        sel = sel[(sel.index.get_level_values(0) >= y0) & (sel.index.get_level_values(0) <= y1)]
        v = spread.reindex(sel.index)[sel].stack()
        rows.append(dict(bucket=lab, period=per, n_stock_months=len(v), median_full_spread_bp=round(v.median()*1e4, 1), mean_full_spread_bp=round(v.mean()*1e4, 1)))
sp = pd.DataFrame(rows); sp.to_csv(OUT + 'E7_part3_spread_proxy.csv', index=False); print(sp.to_string())
# ---------- G. Price-limit regime check ----------
big = df[(df.ChangesRatio.abs() > 15.5) & (df.ChangesRatio.abs() <= 30.5) & (df.Volume > 0)]
print('first date with |chg| in (15.5, 30.5]:', big.Date.min(), ' count before 2015-06-15:', (big.Date < '2015-06-15').sum(), ' after:', (big.Date >= '2015-06-15').sum())

print('done', round(time.time()-t0, 1))
