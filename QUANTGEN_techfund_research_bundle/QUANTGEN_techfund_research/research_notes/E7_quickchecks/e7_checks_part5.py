# E7 part 5: market-structure descriptives from local marcap KRX data (no investor-type data available locally)
import pandas as pd, numpy as np, warnings
warnings.filterwarnings('ignore')
OUT = '/home/claude/research_notes/QUANTGEN technical and fundamental signals/E7_quickchecks/'
BASE = '/home/claude/data_raw/marcap/data/marcap-{}.parquet'
rows = []; lim_rows = []; pair_rows = []
for y in range(2012, 2027):
    d = pd.read_parquet(BASE.format(y), columns=['Code', 'Name', 'ChangesRatio', 'Volume', 'Amount', 'Marcap', 'Market', 'Date'])
    d = d[d.Market.isin(['KOSPI', 'KOSDAQ', 'KOSDAQ GLOBAL'])]
    d['M'] = np.where(d.Market == 'KOSPI', 'KOSPI', 'KOSDAQ')
    for m, g in d.groupby('M'):
        daily_amt = g.groupby('Date').Amount.sum(); daily_mc = g.groupby('Date').Marcap.sum()
        # trading-value share of the bottom half of names by cap (cross-section each day)
        g = g.copy(); g['crank'] = g.groupby('Date').Marcap.rank(pct=True)
        small_share = g[g.crank <= 0.5].groupby('Date').Amount.sum() / daily_amt
        rows.append(dict(year=y, market=m, sessions=daily_amt.size, avg_daily_value_trn=round(daily_amt.mean()/1e12, 2),
                         turnover_velocity_pct=round(daily_amt.sum()/daily_mc.mean()*100, 0),
                         bottom_half_by_cap_value_share_pct=round(small_share.mean()*100, 1)))
    k = d[d.M == 'KOSPI']
    tot_amt = k.groupby('Date').Amount.sum(); tot_mc = k.groupby('Date').Marcap.sum()
    pr = k[k.Code.isin(['005930', '000660'])]
    pair_rows.append(dict(year=y, pair_share_of_KOSPI_value_traded_pct=round(pr.groupby('Date').Amount.sum().sum()/tot_amt.sum()*100, 1),
                          pair_share_of_KOSPI_mcap_yearend_pct=round(pr[pr.Date == pr.Date.max()].Marcap.sum()/tot_mc.iloc[-1]*100, 1)))
    if y == 2015:
        x = d[(d.Date >= '2015-06-08') & (d.Date <= '2015-06-19') & (d.Volume > 0)]
        lim_rows = x.groupby('Date').ChangesRatio.agg(['max', 'min', lambda s: int((s.abs() > 15.5).sum())]).reset_index()
st = pd.DataFrame(rows); st.to_csv(OUT + 'E7_part5_turnover_by_market_year.csv', index=False)
pd.set_option('display.width', 200)
print(st.pivot(index='year', columns='market', values=['avg_daily_value_trn', 'turnover_velocity_pct', 'bottom_half_by_cap_value_share_pct']).to_string())
pp = pd.DataFrame(pair_rows); pp.to_csv(OUT + 'E7_part5_pair_share.csv', index=False); print(pp.to_string())
print('Daily max/min change and count |chg|>15.5% around the limit change:'); print(lim_rows.to_string())
