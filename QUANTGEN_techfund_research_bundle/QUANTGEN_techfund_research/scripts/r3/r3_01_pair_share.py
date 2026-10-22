"""R3 (CR-07): pre-registered pair-share denominator for the macro R-07 pair cap.
Definition (CR-07): numerator = market cap of 005930 (Samsung common) + 005935 (Samsung preferred) + 000660 (SK hynix);
denominator = total market cap of all KOSPI-listed shares in the KRX daily all-stock file (marcap, Market == 'KOSPI', all lines).
Alternatives reported for transparency. Source: /home/claude/data_raw/marcap/data/marcap-2026.parquet (and 2023-2025 files for history).
"""
import pandas as pd, numpy as np
RAW='/home/claude/data_raw/marcap/data/'
OUT='/home/claude/datalab/r3/results/r3_pair_share.csv'
frames=[pd.read_parquet(RAW+f'marcap-{y}.parquet', columns=['Code','Name','Marcap','Market','Date']) for y in (2023,2024,2025,2026)]
d=pd.concat(frames); d=d[d.Market=='KOSPI'].copy()
d['Date']=pd.to_datetime(d['Date'])
# common-share lines: KRX codes ending in '0' are common lines (preferred / new-share lines end in a non-zero digit or letter); same convention as R1 lab
d['common']=d['Code'].str[-1].eq('0')
def snap(dt):
    x=d[d.Date==pd.Timestamp(dt)]
    if x.empty: return None
    m=x.set_index('Code')['Marcap']
    s_c=m.get('005930',np.nan); s_p=m.get('005935',np.nan); skh=m.get('000660',np.nan)
    tot_all=x['Marcap'].sum(); tot_com=x.loc[x.common,'Marcap'].sum()
    return dict(date=str(pd.Timestamp(dt).date()), n_kospi_lines=len(x), n_common_lines=int(x.common.sum()),
        samsung_common_krw=s_c, samsung_pref_krw=s_p, skhynix_krw=skh, kospi_all_lines_krw=tot_all, kospi_common_only_krw=tot_com,
        CR07_pair_incl_pref_over_all_lines=(s_c+s_p+skh)/tot_all,
        alt_pair_common_over_all_lines=(s_c+skh)/tot_all,
        alt_pair_common_over_common_only=(s_c+skh)/tot_com,
        alt_pair_incl_pref_over_common_plus_pref=(s_c+s_p+skh)/(tot_com+s_p))
rows=[]
for dt in ['2023-12-28','2024-12-30','2025-12-30','2026-05-07','2026-06-22','2026-06-25','2026-06-30','2026-09-29']:
    r=snap(dt)
    if r: rows.append(r)
# CR-07 series in 2026: first date above 0.45 and peak
x26=d[d.Date.dt.year==2026]
g=x26.groupby('Date')
tot=g['Marcap'].sum()
num=x26[x26.Code.isin(['005930','005935','000660'])].groupby('Date')['Marcap'].sum()
ser=(num/tot).dropna()
first45=ser[ser>0.45].index.min(); pk=ser.idxmax()
out=pd.DataFrame(rows)
out.to_csv(OUT,index=False)
pd.set_option('display.width',250); pd.set_option('display.max_columns',30)
print(out[['date','n_kospi_lines','n_common_lines','CR07_pair_incl_pref_over_all_lines','alt_pair_common_over_all_lines','alt_pair_common_over_common_only','alt_pair_incl_pref_over_common_plus_pref']].round(4).to_string(index=False))
print('2026-09-29 raw KRW: Samsung common %.4e, pref %.4e, SK hynix %.4e, KOSPI all lines %.4e, common-only %.4e' % tuple(out.iloc[-1][['samsung_common_krw','samsung_pref_krw','skhynix_krw','kospi_all_lines_krw','kospi_common_only_krw']]))
print('CR-07 series 2026: first date > 0.45:', first45.date(), round(ser[first45],4), '| peak', pk.date(), round(ser[pk],4), '| last', ser.index.max().date(), round(ser.iloc[-1],4))
# sessions above 0.45 in 2026
print('sessions in 2026 with CR-07 share > 0.45:', int((ser>0.45).sum()), 'of', len(ser))
# summary rows for traceability (golden values)
summ=pd.DataFrame([
 dict(item='CR-07 share on 2026-09-29', value=round(float(ser.loc['2026-09-29']),6)),
 dict(item='CR-07 first session > 0.45 in 2026', value=str(first45.date())),
 dict(item='CR-07 share on first session > 0.45', value=round(float(ser[first45]),6)),
 dict(item='CR-07 2026 peak date', value=str(pk.date())),
 dict(item='CR-07 2026 peak share', value=round(float(ser[pk]),6)),
 dict(item='CR-07 sessions > 0.45 in 2026 (to 2026-09-29)', value=int((ser>0.45).sum())),
 dict(item='sessions in 2026 file (to 2026-09-29)', value=int(len(ser))),
])
# alternative denominators, daily in 2026 (for transparency; the exec chair's A5 dates use these)
x26c=x26[x26.common]
tot_c=x26c.groupby('Date')['Marcap'].sum()
num_c=x26[x26.Code.isin(['005930','000660'])].groupby('Date')['Marcap'].sum()
pref=x26[x26.Code=='005935'].groupby('Date')['Marcap'].sum()
alts={'alt_pair_common_over_all_lines':(num_c/tot).dropna(),
      'alt_pair_common_over_common_only':(num_c/tot_c).dropna(),
      'alt_pair_incl_pref_over_common_plus_pref':(num/(tot_c+pref)).dropna()}
extra=[]
for k,s in alts.items():
    f=s[s>0.45].index.min(); p=s.idxmax()
    extra+= [dict(item=f'{k}: first session > 0.45 in 2026', value=str(f.date())),
             dict(item=f'{k}: 2026 peak date / share', value=f'{p.date()} / {s[p]:.6f}'),
             dict(item=f'{k}: sessions > 0.45 in 2026', value=int((s>0.45).sum()))]
summ=pd.concat([summ,pd.DataFrame(extra)],ignore_index=True)
summ.to_csv('/home/claude/datalab/r3/results/r3_pair_share_summary.csv',index=False)
daily=pd.concat([ser.rename('cr07_pair_share')]+[s.rename(k) for k,s in alts.items()],axis=1)
daily.index.name='Date'
daily.to_csv('/home/claude/datalab/r3/results/r3_pair_share_2026_daily.csv')
print(summ.to_string(index=False))
