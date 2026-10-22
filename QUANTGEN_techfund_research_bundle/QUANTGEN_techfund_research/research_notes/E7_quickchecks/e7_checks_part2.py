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

RUN_ABC = False
if RUN_ABC:
  pass
# ---------- A. Signals ----------
MOM = cum.shift(21) - cum.shift(252)
NOBS = R.notna().rolling(252).sum()
TURN12 = (AMT / MC).rolling(252, min_periods=200).mean()
MAXR = R.rolling(21, min_periods=15).max()
HI52 = PADJ / PADJ.rolling(252, min_periods=200).max()
LVOL = R.rolling(60, min_periods=50).std()
STR = cum - cum.shift(21)
rows = []
def add(name, f):
    for pn, (a, b) in periods.items():
        g = f.loc[a:b]
        if len(g) == 0: continue
        rows.append(dict(signal=name, period=pn, days=len(g), LS_gross=stats(g.LSg), LS_net=stats(g.LSn),
                         LongEx_gross=stats(g.LXg), LongEx_net=stats(g.LXn),
                         cumL=round((np.prod(1+g.L)-1)*100, 1), cumB=round((np.prod(1+g.B)-1)*100, 1),
                         turn_L_per_yr=round(f.tauL.sum()/(len(f)/252), 1)))
# momentum by turnover tercile (Eom et al. 2020 replication on 2015-2026)
terc = TURN12.rank(axis=1, pct=True)
for lab, lo_, hi_ in [('low', 0, 1/3), ('mid', 1/3, 2/3), ('high', 2/3, 1.01)]:
    ex = (NOBS >= 200) & (terc > lo_) & (terc <= hi_)
    add(f'MOM 12-1 turnover-{lab}', monthly_ports(MOM, True, liquid, extra=ex))
add('MAX 21d (long low-MAX)', monthly_ports(MAXR, False, liquid))
add('52w-high proximity (long near high)', monthly_ports(HI52, True, liquid, extra=NOBS >= 200))
ft = pd.DataFrame(rows); ft.to_csv(OUT + 'E7_part2_signal_splits.csv', index=False)
pd.set_option('display.width', 260); pd.set_option('display.max_columns', 30)
print(ft.to_string()); print('A done', round(time.time()-t0, 1))

# ---------- B. Calendar-year long-only excess (net 35 bp/side) for the main families ----------
fams = {'STR1m': monthly_ports(STR, False, liquid), 'LowVol60': monthly_ports(LVOL, False, liquid),
        'MOM12-1': monthly_ports(MOM, True, liquid, extra=NOBS >= 200), 'lowMAX': monthly_ports(MAXR, False, liquid)}
yr = pd.DataFrame({k: v.LXn.groupby(v.index.year).apply(lambda x: (np.prod(1+x)-1)*100) for k, v in fams.items()}).round(1)
yr_g = pd.DataFrame({k + '_gross': v.LXg.groupby(v.index.year).apply(lambda x: (np.prod(1+x)-1)*100) for k, v in fams.items()}).round(1)
yt = pd.concat([yr, yr_g], axis=1); yt.to_csv(OUT + 'E7_part2_calendar_years_longonly_excess.csv')
print(yt.to_string())
print('share of years positive (net, 2015-2025 full years):', (yr.loc[2015:2025] > 0).mean().round(2).to_dict())

# short-ban regime split (gross L/S, daily) -- 2015-07..2026-09
ban = pd.Series('open', index=dates)
ban[(dates >= '2020-03-16') & (dates <= '2021-05-02')] = 'full ban'
ban[(dates >= '2021-05-03') & (dates <= '2023-11-05')] = 'partial (K200/KQ150 only)'
ban[(dates >= '2023-11-06') & (dates <= '2025-03-28')] = 'full ban'
reg = []
for k, v in fams.items():
    v2 = v.loc['2015-07-01':]
    for lab in ['open', 'partial (K200/KQ150 only)', 'full ban']:
        idx = v2.index[ban.reindex(v2.index).values == lab]
        reg.append(dict(family=k, regime=lab, days=len(idx), LS_gross=stats(v2.loc[idx, 'LSg']), LongEx_gross=stats(v2.loc[idx, 'LXg']), S_minus_B_gross=stats(v2.loc[idx, 'S'] - v2.loc[idx, 'B'])))
rg = pd.DataFrame(reg); rg.to_csv(OUT + 'E7_part2_shortban_regimes.csv', index=False); print(rg.to_string())

# ---------- C. KOSPI200-proxy factor-ETF analogue (top-200 KOSPI common by cap, monthly) ----------
k200 = (KS == 1) & (FLAG == 0) & (VOL > 0)
rank_k = MC.where(k200).rank(axis=1, ascending=False)
inK = rank_k <= 200
def k200_cw():
    out = []
    for i in range(len(me)-1):
        t, tn = me[i], me[i+1]
        names = inK.loc[t][inK.loc[t]].index
        w = MC.loc[t, names]; w = w / w.sum()
        hold = R.loc[(R.index > t) & (R.index <= tn), names].fillna(0)
        # buy-and-hold within month
        gp = (1 + hold).cumprod(); val = (gp * w).sum(axis=1); rr = val / val.shift(1).fillna(1.0) - 1
        rr.iloc[0] = val.iloc[0] - 1
        exp = [c for c in names if c not in ('005930', '000660')]
        w2 = MC.loc[t, exp]; w2 = w2/w2.sum(); gp2 = (1 + hold[exp]).cumprod(); v2 = (gp2*w2).sum(axis=1)
        r2 = v2 / v2.shift(1).fillna(1.0) - 1; r2.iloc[0] = v2.iloc[0] - 1
        out.append(pd.DataFrame({'CW': rr, 'CW_expair': r2, 'EW': hold.mean(axis=1)}))
    return pd.concat(out)
kb = k200_cw()
kf = {'K200 lowvol Q5': monthly_ports(LVOL, False, inK, bench=kb.CW), 'K200 mom Q5': monthly_ports(MOM, True, inK, extra=NOBS >= 200, bench=kb.CW),
      'K200 STR Q5': monthly_ports(STR, False, inK, bench=kb.CW)}
ann = pd.DataFrame({'K200proxy_CW': kb.CW.groupby(kb.index.year).apply(lambda x: (np.prod(1+x)-1)*100),
                    'CW_ex_Samsung_SKhynix': kb.CW_expair.groupby(kb.index.year).apply(lambda x: (np.prod(1+x)-1)*100),
                    'EW200': kb.EW.groupby(kb.index.year).apply(lambda x: (np.prod(1+x)-1)*100)})
for k, v in kf.items():
    ann[k + ' (gross)'] = v.L.groupby(v.index.year).apply(lambda x: (np.prod(1+x)-1)*100)
    ann[k + ' (net35)'] = (v.L - v.cL).groupby(v.index.year).apply(lambda x: (np.prod(1+x)-1)*100)
ann = ann.round(1); ann.to_csv(OUT + 'E7_part2_k200proxy_factor_years.csv'); print(ann.to_string())
for nm, (a, b) in {'2015-07..2024-12': ('2015-07-01', '2024-12-31'), '2025-01-02..2026-06-22': ('2025-01-02', '2026-06-22'), '2026-06-23..07-30': ('2026-06-23', '2026-07-30')}.items():
    line = f'{nm}: CW {(np.prod(1+kb.CW.loc[a:b])-1)*100:.1f}%  CWexPair {(np.prod(1+kb.CW_expair.loc[a:b])-1)*100:.1f}%  EW {(np.prod(1+kb.EW.loc[a:b])-1)*100:.1f}%'
    for k, v in kf.items(): line += f'  {k} net {(np.prod(1+(v.L-v.cL).loc[a:b])-1)*100:.1f}%'
    print(line)
print('C done', round(time.time()-t0, 1))

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
print('done', round(time.time()-t0, 1))
