"""R3 golden values: every number the TF integration spec's acceptance tests should reproduce,
traced to a result file and a line number (line 1 = CSV header, so the first data row is line 2).
Writes /home/claude/datalab/r3/results/r3_golden_values.csv and charts/golden_values.json.
Values are read programmatically; nothing is typed in by hand except the items marked 'not traced'.
"""
import pandas as pd, json, os
R='/home/claude/datalab/'
OUT=R+'r3/results/r3_golden_values.csv'
JS=R+'r3/charts/golden_values.json'
os.makedirs(R+'r3/charts',exist_ok=True)
cache={}
def load(p):
    if p not in cache: cache[p]=pd.read_csv(R+p)
    return cache[p]
def pick(p, where, col='value'):
    d=load(p); m=pd.Series(True,index=d.index)
    for k,v in where.items(): m&=(d[k].astype(str)==str(v))
    x=d[m]
    if len(x)!=1: raise ValueError(f'{p} {where} -> {len(x)} rows')
    i=x.index[0]; return x.iloc[0][col], int(i)+2
rows=[]
def add(gid, card, decision, quantity, market, period, basis, val, fmt, path, line, note='', status='traced'):
    if isinstance(val,(int,float)) and fmt:
        sval=fmt.format(val)
    else: sval=str(val)
    rows.append(dict(gv_id=gid, card_or_rule=card, decision=decision, quantity=quantity, market=market, period=period,
                     gross_net=basis, value=sval, raw=val, source_file=path, line=line, status=status, note=note))
pct='{:+.2%}'; f2='{:.2f}'; f3='{:.3f}'; f4='{:.4f}'
EX='r2/kr/results/r2_kr_excl_summary.csv'
n=0
def nid():
    global n; n+=1; return f'GV-{n:03d}'
# ---------- 1. Lottery composite screen (F4) and dilution screen (F6): BUILD NOW (CR-06) ----------
for base,bdesc in [('B1','EW ALL book'),('B2','VW ALL 5%-capped'),('B3','top-200 VW 5%-capped'),('B4','12-1 momentum top quintile EW')]:
    for flt,card in [('F4','SCR-1 lottery composite exclusion (F4, worst decile of vol+MAX+turnover ranks)'),('F6','SCR-2 dilution exclusion (F6, 252-session share growth > 10%)')]:
        for cost,basis in [('gross','gross'),('net35','net 35 bp/side'),('net70','net 70 bp/side (2x)')]:
            v,l=pick(EX,dict(base=base,filter=flt,cost=cost,primary='True'),'ann_diff')
            add(nid(),card,'BUILD NOW',f'{base} ({bdesc}): filtered minus unfiltered return, %/yr','KRX','1996-03..2026-09 (366 formations)',basis,v,pct,EX,l)
        for col,lab,fm in [('ir','information ratio of the difference',f2),('nw_t','Newey-West t',f2),('boot_p','one-sided bootstrap p',f4),('pct_years_pos','share of years positive',f2),
                           ('sharpe_filtered','Sharpe filtered book',f2),('sharpe_unfiltered','Sharpe unfiltered book',f2),('maxdd_diff','max DD filtered minus unfiltered (+ = shallower)',pct),
                           ('turnover_filtered','turnover/yr filtered',f2),('turnover_unfiltered','turnover/yr unfiltered',f2),('excl_share_names','share of names excluded',f2)]:
            v,l=pick(EX,dict(base=base,filter=flt,cost='net35',primary='True'),col)
            add(nid(),card,'BUILD NOW',f'{base}: {lab}','KRX','1996-03..2026-09','net 35 bp/side',v,fm,EX,l)
# break-even per side for the screen (derived): gross diff / extra turnover
for base in ['B1','B2','B3','B4']:
    for flt in ['F4','F5','F6']:
        g,lg=pick(EX,dict(base=base,filter=flt,cost='gross',primary='True'),'ann_diff')
        tf,lt=pick(EX,dict(base=base,filter=flt,cost='net35',primary='True'),'turnover_filtered')
        tu,_=pick(EX,dict(base=base,filter=flt,cost='net35',primary='True'),'turnover_unfiltered')
        be=g/(tf-tu)*1e4 if tf>tu else float('nan')
        card={'F4':'SCR-1 lottery composite','F5':'F5 attention-fade monthly screen (DROP)','F6':'SCR-2 dilution screen'}[flt]
        add(nid(),card,'BUILD NOW' if flt!='F5' else 'DROP (CR-06)',f'{base}: break-even cost per side = gross diff / extra turnover (bp); pre-gate screen rejects if < 70 bp',
            'KRX','1996-03..2026-09','derived from gross diff and turnover',be,'{:.0f}',EX,f'{lg};{lt}',note='derived: ann_diff(gross) / (turnover_filtered - turnover_unfiltered)',status='derived')
# sub-periods from long file
EL='r2/kr/results/r2_kr_excl_long.csv'
for base,flt in [('B1','F4'),('B1','F6'),('B4','F4')]:
    for per in ['1996-2005','2006-2015','2016-2026-09']:
        try:
            v,l=pick(EL,dict(base=base,filter=flt,cost='net35',period=per,metric='ann_diff'))
            add(nid(),'SCR-1 lottery composite' if flt=='F4' else 'SCR-2 dilution screen','BUILD NOW',f'{base}: diff %/yr, sub-period','KRX',per,'net 35 bp/side',v,pct,EL,l)
        except ValueError as e: print('miss',e)
# gate and DSR
EG='r2/kr/results/r2_kr_excl_gate.csv'
for base,flt in [('B1','F4'),('B2','F4'),('B3','F4'),('B4','F4')]:
    for col,lab,fm in [('steps_passed','indicative gate steps passed (of 8)','{:.0f}'),('verdict','indicative verdict',None),('g3_dsr','deflated Sharpe, pooled variance over 176 trials',f3),
                       ('g4_pbo_primary8','PBO (8 primary filters)',f3),('g7_plateau_share','plateau share',f2),('g9_haircut_ann_diff','step-9 column as printed by the lab (0.4 x diff)',pct)]:
        v,l=pick(EG,dict(base=base,filter=flt),col)
        note='lab printed 0.4 x diff; spec step 9 = 0.6 x OOS (see corrected anchors)' if col=='g9_haircut_ann_diff' else ''
        add(nid(),'SCR-1 lottery composite','BUILD NOW',f'{base}/F4: {lab}','KRX','1996-03..2026-09','net 35 bp/side',v,fm,EG,l,note=note)
ED='r2/kr/results/r2_kr_excl_dsr_best.csv'
v,l=pick(ED,dict(best_trial='B1|F4_cut5'),'dsr_pooled_variance')
add(nid(),'SCR-1 lottery composite','BUILD NOW','best of 176 trials (B1|F4 cut 5%): deflated Sharpe, pooled variance','KRX','1996-03..2026-09','net 35 bp/side',v,f3,ED,l)
# SCR-3 construction rule: highest-turnover-quintile exclusion (F1) on the EW book (B1) and the momentum top quintile (B4)
for base,bdesc in [('B1','EW ALL book'),('B4','12-1 momentum top quintile EW')]:
    for cost,basis in [('gross','gross'),('net35','net 35 bp/side'),('net70','net 70 bp/side (2x)')]:
        v,l=pick(EX,dict(base=base,filter='F1',cost=cost,primary='True'),'ann_diff')
        add(nid(),'SCR-3 construction rule (F1, highest-turnover quintile excluded)','BUILD NOW (rule)',f'{base} ({bdesc}): filtered minus unfiltered return, %/yr','KRX','1996-03..2026-09 (366 formations)',basis,v,pct,EX,l)
    for col,lab,fm in [('ir','information ratio of the difference',f2),('nw_t','Newey-West t',f2),('pct_years_pos','share of years positive',f2),('maxdd_diff','max DD filtered minus unfiltered (+ = shallower)',pct)]:
        v,l=pick(EX,dict(base=base,filter='F1',cost='net35',primary='True'),col)
        add(nid(),'SCR-3 construction rule (F1, highest-turnover quintile excluded)','BUILD NOW (rule)',f'{base}/F1: {lab}','KRX','1996-03..2026-09','net 35 bp/side',v,fm,EX,l)
    for col,lab,fm in [('steps_passed','indicative gate steps passed (of 8)','{:.0f}'),('verdict','indicative verdict',None),('g3_dsr','deflated Sharpe, pooled variance over 176 trials',f3)]:
        v,l=pick(EG,dict(base=base,filter='F1'),col)
        add(nid(),'SCR-3 construction rule (F1, highest-turnover quintile excluded)','BUILD NOW (rule)',f'{base}/F1: {lab}','KRX','1996-03..2026-09','net 35 bp/side',v,fm,EG,l)
# limit-lock audit
LL='r2/kr/results/r2_kr_excl_limitlock.csv'
for base,flt in [('B1','none'),('B1','F4')]:
    for col,lab in [('share_entries_locked','share of entries bought at a locked limit-up close'),('share_exits_locked','share of exits sold at a locked limit-down close')]:
        v,l=pick(LL,dict(base=base,filter=flt),col)
        add(nid(),'INV-2 limit-lock rule','INVARIANT',f'{base} {flt}: {lab}','KRX','1996-03..2026-09','count share',v,'{:.2%}',LL,l)
# R1 key numbers (regression of the KRX panel engine)
KN='kr/results/kr_key_numbers.csv'
for sig,w,col,lab,fm in [('TURN_1M_LOW','EW','excl_xs_net35_ann','universe minus highest-turnover quintile, excess over EW universe',pct),('TURN_1M_LOW','EW','excl_xs_net35_t','same, NW t',f2),
                         ('VOL_3M','EW','excl_xs_net35_ann','universe minus most volatile quintile, excess over EW universe',pct),('VOL_3M','EW','excl_xs_net35_t','same, NW t',f2),
                         ('MOM_12_1','EW','ls_gross_ann','12-1 momentum L/S quintiles, gross %/yr',pct),('MOM_12_1','EW','ls_gross_sharpe','same, gross Sharpe',f3),('MOM_12_1','EW','ls_net35_sharpe','same, net-35 Sharpe',f3),
                         ('MOM_12_1','EW','lo_xs_net35_ann','12-1 long-only top quintile excess over EW universe',pct),
                         ('REV_1W','EW','ls_net35_sharpe','weekly reversal L/S net-35 Sharpe',f3),('REV_1W','VW','ls_net35_sharpe','weekly reversal L/S net-35 Sharpe (VW)',f3),
                         ('REV_1M','EW','ls_net35_sharpe','1-month reversal L/S net-35 Sharpe',f3),('REV_1M','VW','ls_net35_sharpe','1-month reversal L/S net-35 Sharpe (VW)',f3),
                         ('VOL_3M','EW','lo_xs_net35_ann','low-vol long-only top quintile excess over EW universe',pct),('VOL_3M','VW','lo_xs_net35_ann','low-vol long-only top quintile excess over VW universe',pct)]:
        v,l=pick(KN,dict(signal=sig,universe='ALL',weighting=w),col)
        add(nid(),'R1 KRX panel regression (engine check)','REFERENCE',f'{sig} {w}: {lab}','KRX','1996-03..2026-09','gross' if 'gross' in col else 'net 35 bp/side',v,fm,KN,l)
# break-even pre-gate screen on L/S signals (derived)
for sig,w in [('REV_1W','EW'),('REV_1W','VW'),('REV_1M','EW'),('MOM_12_1','EW'),('HIGH52','EW'),('VOL_3M','EW'),('TURN_1M_LOW','EW'),('MAX_1M','EW')]:
    g,lg=pick(KN,dict(signal=sig,universe='ALL',weighting=w),'ls_gross_ann'); t,lt=pick(KN,dict(signal=sig,universe='ALL',weighting=w),'ls_turnover_yr')
    add(nid(),'GOV-7 break-even pre-gate screen','GOVERNANCE (CR-08)',f'{sig} {w} L/S quintiles: break-even cost per side (bp) = gross /yr / turnover /yr (both legs)','KRX','1996-03..2026-09','derived',g/t*1e4,'{:.1f}',KN,f'{lg}',note='derived; R1 lab quotes 12.5 / 22.2 bp for REV_1W EW / VW',status='derived')
# ---------- 2. Execution invariants: events and adjusted returns ----------
EV='r2/verification/exec_verification_log.csv'
for r,lab in [(82,'locked limit-up, next-open entry, excess vs EW liquid universe: t+5 / t+20 (bp), n'),(84,'locked limit-down: t+1 / t+5 / t+20 (bp), n'),(83,'volume spike (>= 5x, r >= +5%): t+5 / t+20 (bp)'),
              (85,'20-day run-up >= +50%: t+20 (bp)'),(21,'KRX top-500 EW 12-1 D10-D1: overnight vs intraday %/yr'),(86,'eligibility same-day vs lagged one day: EW benchmark %/yr')]:
    v,l=pick(EV,dict(row=r),'value_found')
    add(nid(),'INV-1/INV-2 close fills and limit-lock rule','INVARIANT',lab,'KRX','2015-06..2026-09 (events); 2002-2026 (overnight)','gross event returns',v,None,EV,l)
MC='r2/kr/results/r2_kr_mom_claims_long.csv'
for var,lab in [('adjusted|broad|high-turnover W-L','Eom design, adjusted returns, all caps, high-turnover W-L'),('unadjusted signal + unadjusted holding returns|broad|high-turnover W-L','same with unadjusted closes'),
                ('adjusted|broad_cut|high-turnover W-L','adjusted, ex-bottom-20% caps')]:
    v,l=pick(MC,dict(claim='KJFS/P6-Eom',variant=var,metric='mean_pct_month'))
    add(nid(),'DATA-2 corporate-action-adjusted returns','INVARIANT',lab+', %/month','KRX','2000-07..2019-06','gross',v,'{:+.2f}',MC,l)
    v,l=pick(MC,dict(claim='KJFS/P6-Eom',variant=var,metric='nw_t'))
    add(nid(),'DATA-2 corporate-action-adjusted returns','INVARIANT',lab+', NW t','KRX','2000-07..2019-06','gross',v,f2,MC,l)
VL='kr/results/kr_validation.csv'
v,l=pick(VL,dict(test='V1b'),'value')
add(nid(),'DATA-2 corporate-action-adjusted returns','INVARIANT','share of kept daily returns where |Close/prevClose-1 - r| > 0.5% (KRX base-price adjustments)','KRX','1995-2026','count',v,None,VL,l)
# DATA-5 Korean regime flags: dates and tax path, traced to verification-log rows or chair-resolution lines (text checked programmatically)
PVL='r2/verification/prof_verification_log.csv'
for lid,lab,col in [('V061','full short-sale ban regime (first ban day; resumption)','value_found'),('V062','sell tax path (status MATCH; value as printed and confirmed)','number_as_printed'),('V095','KOSDAQ up-limit closes per 10,000 stock-days','value_found')]:
    v,l=pick(PVL,dict(log_id=lid),col)
    add(nid(),'DATA-5 Korean regime and event flags','BUILD NOW (flags)',lab,'KRX','as stated','dates / rates',v,None,PVL,l)
for r,lab in [(18,'sell tax by year (incl. rural special tax)'),(24,'daily price limit widened to +-30%'),(78,'KOSPI return on 2025-03-31 (short-sale resumption day)')]:
    v,l=pick(EV,dict(row=r),'value_found')
    add(nid(),'DATA-5 Korean regime and event flags','BUILD NOW (flags)',lab,'KRX','as stated','dates / rates',v,None,EV,l)
RN='/home/claude/research_notes/QUANTGEN technical and fundamental signals/'
def md_line(fname,line,must):
    txt=open(RN+fname,encoding='utf-8').read().split('\n')[line-1]
    assert must in txt, (fname,line,must)
    return txt.strip()
for fname,line,must,lab,val in [
    ('R2_EXEC_chair_resolution.md',142,'1 Oct 2008','short-sale ban regimes','1 Oct 2008-31 May 2009; 11 Aug-9 Nov 2011; 16 Mar 2020 (partial lift 3 May 2021); 6 Nov 2023-30 Mar 2025'),
    ('R2_PROF_chair_resolution.md',205,'2020-03-16 to 2021-05-02','short-sale regimes incl. index-only period','2020-03-16..2021-05-02 full, then index stocks only until 2023-11-05; full ban 2023-11-06..2025-03-30; resumed 2025-03-31'),
    ('R2_PROF_chair_resolution.md',187,'2024-02-26','Value-up regime split date for Korean value/payout tests','2024-02-26')]:
    md_line(fname,line,must)
    add(nid(),'DATA-5 Korean regime and event flags','BUILD NOW (flags)',lab,'KRX','as stated','dates',val,None,'research_notes/QUANTGEN technical and fundamental signals/'+fname,line,note='chair-resolution text (not a lab output); line checked programmatically')
# ---------- 3. Pair-share denominator (CR-07) ----------
PS='r3/results/r3_pair_share.csv'
for d in ['2023-12-28','2025-12-30','2026-06-22','2026-06-25','2026-09-29']:
    for col,lab in [('CR07_pair_incl_pref_over_all_lines','CR-07: (005930+005935+000660) / all KOSPI lines'),('alt_pair_common_over_all_lines','alt: (005930+000660) / all KOSPI lines'),
                    ('alt_pair_common_over_common_only','alt: (005930+000660) / KOSPI common lines')]:
        v,l=pick(PS,dict(date=d),col)
        add(nid(),'RISK-1 pair-share series (R-07 pair cap)','INVARIANT (owner to confirm)',f'{lab} on {d}','KRX','daily snapshot','market cap',v,'{:.2%}',PS,l)
v,l=pick(PS,dict(date='2026-09-29'),'alt_pair_incl_pref_over_common_plus_pref')
add(nid(),'RISK-1 pair-share series (R-07 pair cap)','INVARIANT (owner to confirm)','alt: (005930+005935+000660) / (KOSPI common lines + 005935) on 2026-09-29','KRX','daily snapshot','market cap',v,'{:.2%}',PS,l)
PSS='r3/results/r3_pair_share_summary.csv'
for it in ['CR-07 first session > 0.45 in 2026','CR-07 share on first session > 0.45','CR-07 2026 peak date','CR-07 2026 peak share','CR-07 sessions > 0.45 in 2026 (to 2026-09-29)',
           'alt_pair_common_over_all_lines: first session > 0.45 in 2026']:
    v,l=pick(PSS,dict(item=it),'value')
    add(nid(),'RISK-1 pair-share series (R-07 pair cap)','INVARIANT (owner to confirm)',it,'KRX','2026-01-02..2026-09-29','market cap',v,None,PSS,l)
# ---------- 4. Momentum risk controls (R-03 on KRX) ----------
CW='r2/kr/results/r2_kr_crash_windows.csv'
for sl,ctl,lab in [('LS_VW (ALL quintiles)','static','12-1 L/S VW static'),('LS_VW (ALL quintiles)','VS (own vol, 12%, cap 1)','12-1 L/S VW own-vol scaled (R-03)'),
                   ('LS_VW (ALL quintiles)','static at same avg exposure as VS (own vol, 12%, cap 1) (0.53)','12-1 L/S VW static at the same average exposure (0.53)'),
                   ('LS_EW (ALL quintiles)','static','12-1 L/S EW static'),('LS_EW (ALL quintiles)','VS (own vol, 12%, cap 1)','12-1 L/S EW own-vol scaled (R-03)'),
                   ('LO_EW excess (Q5 vs EW univ)','VS (own vol, 12%, cap 1)','12-1 long-only EW excess, own-vol scaled')]:
    v,l=pick(CW,dict(sleeve=sl,control=ctl,window='2026-06-22..07-30 crash'),'cum_return_net35')
    add(nid(),'MOM-1 R-03 own-vol scaling on KRX momentum sleeves','BUILD NOW (risk control; CR-05)',f'{lab}: cumulative return 2026-06-22..07-30','KRX','2026-06-22..07-30','net 35 bp/side',v,pct,CW,l)
CE='r2/kr/results/r2_kr_crash_exposure_2026.csv'
for sl in ['LS_EW (ALL quintiles)','LS_VW (ALL quintiles)','E5 top500 D10-D1 EW','E5 top500 D10-D1 VW']:
    v,l=pick(CE,dict(sleeve=sl,control='VS (own vol, 12%, cap 1)'),'s_on_2026_06_22')
    add(nid(),'MOM-1 R-03 own-vol scaling on KRX momentum sleeves','BUILD NOW (risk control; CR-05)',f'{sl}: R-03 weight on 2026-06-22','KRX','2026-06-22','weight',v,f2,CE,l)
CC='r2/kr/results/r2_kr_crash_controls.csv'
d=load(CC)
for sl in ['LS_EW (ALL quintiles)','LS_VW (ALL quintiles)']:
    for ctl in ['static','VS (own vol, 12%, cap 1)','DM gate (KOSPI, floor 0.5)','VS x DM']:
        for per in sorted(d.period.unique()):
            pass
    for ctl in ['static','VS (own vol, 12%, cap 1)','VS x DM']:
        x=d[(d.sleeve==sl)&(d.control==ctl)&(d.cost=='net35')&(d.metric=='sharpe')]
        for _,r in x.iterrows():
            if r['period'].startswith('full') or r['period'].startswith('2016'):
                add(nid(),'MOM-1 R-03 own-vol scaling on KRX momentum sleeves','BUILD NOW (risk control; CR-05)',f'{sl} {ctl}: Sharpe','KRX',r['period'],'net 35 bp/side',r['value'],f2,CC,int(r.name)+2)
DMO='r2/kr/results/r2_kr_dm_gate_onsets.csv'
add(nid(),'MOM-2 Daniel-Moskowitz gate (spec book only)','SPEC BOOK ONLY (CR-05)','number of D-M gate onsets on the rebuilt KOSPI','KRX','1996-2026','count',len(load(DMO)),'{:.0f}',DMO,'2-10')
# ---------- 5. Constrained momentum (FORWARD-SIM) ----------
G='r2/kr/results/r2_kr_mom_grid_long.csv'
for sig,td,ter,w,leg,per,met,lab,fm in [('MOM_12_1','TURN_12M','low','EW','LO_xs_UEW_net35','full','ann_mean','low-turnover 12-1 winners minus EW universe, %/yr',pct),
    ('MOM_12_1','TURN_12M','low','EW','LO_xs_UEW_net35','full','nw_t','same, NW t',f2),('MOM_12_1','TURN_12M','high','EW','LO_xs_UEW_net35','full','ann_mean','high-turnover 12-1 winners minus EW universe, %/yr',pct),
    ('MOM_12_1','TURN_12M','high','EW','LO_xs_UEW_net35','full','nw_t','same, NW t',f2),('MOM_12_1','TURN_12M','low','EW','LO_xs_UEW_net35','2015-07..2024-12','ann_mean','low-turnover winners minus EW universe, 2015-07..2024-12',pct),
    ('MOM_12_7','all','all','EW','LS_net35','full','sharpe','12-7 L/S quintiles EW net-35 Sharpe',f2),('MOM_12_7','all','all','EW','LS_net35','2016-01..2026-09','sharpe','same 2016-2026',f2),
    ('MOM_12_1','all','all','EW','LS_net35','full','sharpe','12-1 L/S quintiles EW net-35 Sharpe',f2),('MOM_12_1','all','all','EW','LS_net35','2016-01..2026-09','sharpe','same 2016-2026',f2)]:
    v,l=pick(G,dict(signal=sig,turn_def=td,tercile=ter,weighting=w,leg=leg,period=per,metric=met))
    add(nid(),'FS-2 constrained KRX momentum card','FORWARD-SIM (CR-05)',lab,'KRX',per,'net 35 bp/side',v,fm,G,l)
# ---------- 6. Index protective rules: VT20 golden (macro R-06) and floored trend x VT20 (FORWARD-SIM) ----------
GV='r2/idx/results/r2_idx_golden_values.csv'
for _,r in load(GV).iterrows():
    add(nid(),'IDX-1 KOSPI VT20 (macro R-06) reproduction','BUILD NOW (macro R-06; protective workhorse, CR-02)',r['item'],'KOSPI (rebuilt)','2016-01-04..2026-09-29','as labelled',r['ours'],f4,GV,int(r.name)+2,note=f"spec value {r['spec']}; within Level-1 {r['within_level1']}")
SC='r2/idx/results/r2_idx_protective_scorecard.csv'
for rid,book,lab in [('VT','KRX ETF 3bp','KOSPI VT20'),('ENS','KRX ETF 3bp','KOSPI multi-speed trend sleeve'),('ENSxVT','KRX ETF 3bp','KOSPI unbounded trend x VT20'),('SMA200','KRX ETF 3bp','KOSPI SMA200'),('TSM12','KRX ETF 3bp','KOSPI 12-month sign'),
                     ('VT','US via KIS 50bp','SPY VT15 at 50 bp'),('ENS','US via KIS 50bp','SPY trend sleeve at 50 bp'),('ENSxVT','US via KIS 50bp','SPY trend x VT15 at 50 bp'),('ENS','Futures 5bp','SPY trend sleeve at 5 bp')]:
    d=load(SC); x=d[(d.rule_id==rid)&(d.book==book)&(d.set=='centre')]
    if len(x)!=1: print('scorecard miss',rid,book,len(x)); continue
    r=x.iloc[0]; l=int(x.index[0])+2
    mk='KOSPI (rebuilt)' if 'KRX' in book else 'SPY'
    per=f"{r['start']}..{r['end']}"
    dec='BUILD NOW (macro R-06)' if (rid=='VT' and 'KRX' in book) else ('DO-NOT-BUILD at 50 bp (CR-02)' if '50bp' in book else 'REFERENCE / BACKLOG')
    for col,cl,fm in [('pc1_dmdd_pp_1x','PC-1 dMDD vs S at 1x (pp)','{:+.1f}'),('pc1_dmdd_pp_2x','PC-1 dMDD vs S at 2x (pp)','{:+.1f}'),('pc2_tail_ratio','PC-2 tail-exposure ratio',f2),('dsr_vs_S_1x','PC-3 dSR vs S',f3),
                      ('pc3_p_ni','PC-3 non-inferiority p',f3),('pc5_share_years_positive','PC-5 share of years positive',f2),('pc6_share_keep','PC-6 plateau share',f2),('verdict','CARD-P verdict',None)]:
        add(nid(),{'VT':'IDX-1 index vol target','ENS':'IDX trend sleeve','ENSxVT':'IDX trend x vol target','SMA200':'IDX SMA200','TSM12':'IDX 12-month sign'}[rid],dec,f'{lab}: {cl}',mk,per,f'net {book}',r[col],fm,SC,l)
OV='r2/idx/results/r2_idx_overlay_vs_sleeve.csv'
d=load(OV)
for trend,form in [('ENSxVT','overlay clip[0.5,1]'),('ENSxVT','sleeve (0 allowed)'),('ENSxVT','overlay 0.5+0.5x (E3 long/half)'),('ENS','sleeve (0 allowed)'),('ENS','overlay clip[0.5,1]')]:
    x=d[(d.market=='KOSPI')&(d.trend==trend)&(d.form==form)]
    if len(x)!=1: print('ov miss',trend,form,len(x)); continue
    r=x.iloc[0]; l=int(x.index[0])+2
    card='FS-1 KOSPI floored trend x VT20 (primary)' if (trend=='ENSxVT' and form.startswith('overlay clip')) else 'FS-1 comparison cells'
    for col,cl,fm in [('avg_exposure','average exposure',f2),('mdd_1x','max DD',pct),('pc1_dmdd_pp_1x','PC-1 dMDD vs own S (pp)','{:+.1f}'),('pc2_tail_ratio','PC-2 tail ratio',f2),('dsr_vs_S_1x','dSR vs S',f3),
                      ('pc5_share_years_positive','share of years positive',f2),('verdict','indicative CARD-P verdict',None),('ep_1997-98','1997-98 episode return',pct),('win_2026-06-22..07-30','2026-06-22..07-30 crash return',pct)]:
        add(nid(),card,'FORWARD-SIM (CR-02)',f'KOSPI {trend} {form}: {cl}','KOSPI (rebuilt)','1996-09-02..2026-09-29','net 3 bp/side (KRX ETF)',r[col],fm,OV,l)
SD='r2/idx/results/r2_idx_start_date_sensitivity.csv'
d=load(SD)
for st in ['1996-06-03','2001-01-02','2006-01-02','2011-01-03','2016-01-04']:
    for rule,lab in [('VT20 w20','KOSPI VT20'),('ens 20/60/120/250 vote share','KOSPI trend sleeve'),('ens 20/60/120/250 vote share x VT20 w20','KOSPI unbounded trend x VT20')]:
        x=d[(d.market=='KOSPI')&(d.rule==rule)&(d.start==st)]
        r=x.iloc[0]; l=int(x.index[0])+2
        add(nid(),'IDX start-date sensitivity','REFERENCE (CR-02)',f'{lab} from {st}: verdict (PC-1 pp)','KOSPI (rebuilt)',f'{st}..2026-09-29','net 3 bp/side',f"{r['verdict']} ({r['pc1_dmdd_pp_1x']:+.1f})",None,SD,l)
WI='r2/idx/results/r2_idx_windows.csv'
d=load(WI)
for rid in ['buy-and-hold','VT','ENSxVT','SMA200','ENS']:
    x=d[(d.market=='KOSPI')&(d.rule_id==rid)&(d.window=='2026-06-22..07-30 crash')]
    if len(x)!=1: print('win miss',rid,len(x)); continue
    add(nid(),'IDX crash window','REFERENCE',f'KOSPI {rid}: 2026-06-22..07-30 return','KOSPI (rebuilt)','2026-06-23..2026-07-30 returns','net 3 bp/side',x.iloc[0]['cum_return'],pct,WI,int(x.index[0])+2)
SAN='kr/results/kr_index_sanity.csv'
for _,r in load(SAN).iterrows():
    add(nid(),'DATA rebuilt KOSPI check','REFERENCE',f"rebuilt / official KOSPI change ratio {r['start']}..{r['end']}",'KOSPI',f"{r['start']}..{r['end']}",'price index',r['ratio_rebuilt_to_official'],f4,SAN,int(r.name)+2)
# ---------- 7. Gate harness (block length, step 8, power) ----------
GS='r2/idx/results/r2_idx_gate_sim.csv'
d=load(GS)
def gsim(innov,years,sr,step,rho=None,ntr=None):
    x=d[(d.innovations==innov)&(d.years==years)&(d.true_sr==sr)&(d.step==step)]
    if rho is not None: x=x[x.rho==rho]
    if ntr is not None: x=x[x.n_trials==ntr]
    if len(x)!=1: raise ValueError((innov,years,sr,step,rho,ntr,len(x)))
    return x.iloc[0]['pass_rate'], int(x.index[0])+2
for innov in ['kospi_cbb126','kospi_cbb126_signflip','iid_normal']:
    for step in ['step2_bootstrap','step8_years']:
        v,l=gsim(innov,10,0,step)
        add(nid(),'GOV-4 block length max(10, PW) for steps 2 and 5','GOVERNANCE (CR-08)',f'{innov}: false-pass rate of {step} at true Sharpe 0, 10 years (10-session blocks)','simulated','10 years','gross',v,'{:.1%}',GS,l)
print(sorted(d.step.unique()))
v,l=gsim('kospi_cbb126',10,0,'joint_2_3_5_8',rho=0.5,ntr=1)
add(nid(),'GOV-5 gate power and size','GOVERNANCE','kospi_cbb126: joint steps 2+3+5+8 (N 1, rho 0.5) false-pass rate at true Sharpe 0, 10 years','simulated','10 years','gross',v,'{:.1%}',GS,l)
for yrs in [10,18,30]:
    v,l=gsim('kospi_cbb126',yrs,0.4,'step5_benchmark',rho=0.5)
    add(nid(),'GOV-4 block length max(10, PW) for steps 2 and 5','GOVERNANCE (CR-08)',f'kospi_cbb126: step-5 pass rate with NO edge (strategy Sharpe 0.4 = benchmark 0.4, rho 0.5), {yrs} years, nominal 10%','simulated',f'{yrs} years','gross',v,'{:.1%}',GS,l)
PY='r2/idx/results/r2_idx_gate_power_years.csv'
d2=load(PY)
for sr in [0.3,0.4,0.5]:
    x=d2[(d2.innovations=='kospi_cbb126')&(d2.true_sr==sr)&(d2.step=='step2_bootstrap')]
    for _,r in x.iterrows():
        add(nid(),'GOV-5 gate power and size','GOVERNANCE',f"true Sharpe {sr}: years to 50% / 80% power at step 2",'simulated','-','gross',f"{r['years_50pct_txt']} / {r['years_80pct_txt']}",None,PY,int(r.name)+2)
# ---------- 8. Data rule: Shiller averaging ----------
AB='r2/idx/results/r2_idx_averaging_bias.csv'
for comp,rule in [('SPY 1999-03..2021-03','SMA10'),('SPY 1999-03..2021-03','TSM12'),('S&P 500 2000-03..2018-12','SMA10'),('S&P 500 2000-03..2018-12','TSM12')]:
    v,l=pick(AB,dict(comparison=comp,rule=rule),'sharpe_inflation')
    add(nid(),'DATA-3 month-end data rule (no Shiller averages)','INVARIANT (data rule)',f'{comp} {rule}: Sharpe inflation from month-average prices','US',comp.split(' ')[-1],'gross',v,'{:+.2f}',AB,l)
AA='r2/idx/results/r2_idx_averaging_autocorr.csv'
for col in ['acf1_month_end','acf1_month_average']:
    v,l=pick(AA,dict(sample='SPY 1998-02..2021-03'),col)
    add(nid(),'DATA-3 month-end data rule (no Shiller averages)','INVARIANT (data rule)',f'SPY monthly lag-1 autocorrelation, {col}','US','1998-02..2021-03','gross',v,f3,AA,l)
# ---------- 9. Low-vol descriptive sleeve vs S_beta (FORWARD-SIM descriptive; CR-01) ----------
C12='r2/verification/exec_chair_checks/c12_lowvol_samebeta.csv'
d=load(C12)
for _,r in d[(d.cost=='net35')&(d.period=='full')].iterrows():
    l=int(r.name)+2
    for col,lab,fm in [('beta_monthly','beta',f3),('mdd_book','max DD book',pct),('mdd_same_beta_static','max DD same-beta static S_beta',pct),('dMDD_pp','dMDD vs S_beta (pp)','{:+.1f}'),
                       ('sharpe_book','Sharpe book',f3),('sharpe_static','Sharpe S_beta',f3),('tail_ratio_vs_static','tail ratio vs S_beta',f3)]:
        add(nid(),'FS-3 KRX low-vol descriptive sleeve vs S_beta','FORWARD-SIM descriptive (CR-01)',f"{r['book']} vs {r['market']}: {lab}",'KRX','1996-2026','net 35 bp/side',r[col],fm,C12,l)
LV='r2/kr/results/r2_kr_lowvol.csv'
for book in ['low-vol Q1 EW','low-vol Q1 VW']:
    x=load(LV); x=x[(x.book==book)&(x.cost=='net35')&(x.period=='full')]
    r=x.iloc[0]; l=int(x.index[0])+2
    for col,lab,fm in [('beta','beta to VW market',f2),('alpha_ann_rf0','CAPM alpha, rf = 0',pct),('alpha_t','alpha t',f2)]:
        add(nid(),'GOV-3 attribution block (low-vol example)','GOVERNANCE (CR-08)',f'{book}: {lab}','KRX','1996-2026','net 35 bp/side',r[col],fm,LV,l)
# ---------- 10. Attribution: flat SML ----------
UC='us/results/us_C_factors.csv'
v,l=pick(UC,dict(test='C_factors_C1_famamacbeth',series='28 (10 ind + 9 SV + 9 SM)',period='1954-01:2017-03',metric='avg_slope_g1_ann'))
add(nid(),'GOV-3 attribution block (SML check)','GOVERNANCE (CR-08)','US Fama-MacBeth beta slope, %/yr (28 portfolios)','US','1954-01..2017-03','gross',float(v),pct,UC,l)
PV='r2/verification/prof_verification_log.csv'
for lid,lab in [('V002','KR Fama-MacBeth beta slope and low/high-beta alphas (chair prof_v09)'),('V091','chair lottery composite (prof_v02): %/month net 35 bp'),('V047','KR-ISS long-only net information ratio (prof_v03)'),
                ('V113','R2 lottery exclusion EW book'),('V114','R2 issuance exclusion books'),('V117','1-month reversal VW ex-microcap')]:
    v,l=pick(PV,dict(log_id=lid),'value_found')
    add(nid(),'verification log reference','REFERENCE',lab,'KRX','see value','see value',v,None,PV,l)
# ---------- 11. Reversal net numbers (DROP evidence; regression for the pre-gate screen) ----------
RV='r2/kr/results/r2_kr_reversal.csv'
for uni,w,srt,cost in [('ALL','VW','deciles','gross'),('ALL','VW','deciles','net35'),('ALL','EW','deciles','gross'),('ALL','EW','deciles','net35'),('ALL','VW','quintiles','net35'),('LARGE','VW','deciles','net35')]:
    x=load(RV); x=x[(x.universe==uni)&(x.weighting==w)&(x.sort==srt)&(x.cost==cost)&(x.period=='full')]
    r=x.iloc[0]; l=int(x.index[0])+2
    add(nid(),'DNB-4 KRX stock-level short-term reversal (evidence)','DO-NOT-BUILD (CR-03)',f'{uni} {w} {srt}: 1-month reversal losers minus winners, %/month (NW t)','KRX','1996-04..2026-09',cost,f"{r['mean_pct_month']:+.2f} ({r['nw_t']:.1f})",None,RV,l)
# ---------- 12. Stop-loss evidence ----------
SL='r2/kr/results/r2_kr_stoploss.csv'
x=load(SL)
for _,r in x[(x.sleeve=='E5 top500 deciles')&(x.cost=='net35')].iterrows():
    add(nid(),'INV-5 no name-level stops (evidence)','INVARIANT (CR-09)',f"top-500 12-1 deciles {r['weighting']} {r['variant']}: Sharpe",'KRX',r['period'],'net 35 bp/side',r['sharpe'],f2,SL,int(r.name)+2)
# ---------- 13. QUANTGEN record for C3 (CR-10) ----------
add(nid(),'CRY-1 card C3 (keep PASS)','KEEP + governance (CR-10)','C3 KRW-BTC OOS Sharpe [90% CI] vs buy-and-hold; p; Sharpe at 2x; turnover','crypto','QUANTGEN study 2026-09-27','net 10 bp/side (2x 20 bp)','1.22 [0.62, 1.77] vs 0.79; p 0.04; 1.17 at 2x; 13.7x/yr',None,
    'research_notes/QUANTGEN technical and fundamental signals/00_QUANTGEN_context.md','28',note='QUANTGEN gate record, not a lab run')
# ---------- not traceable ----------
for card,q,why in [('FS-1 floored trend x VT20','plateau (PC-6) and start-date sweep of the floored product','not evaluated by R2 IDX (only the unbounded product was swept)'),
                   ('FS-4 ridge / Fama-MacBeth challenger','any performance number','no lab test exists'),
                   ('CRY-1 C3 controls','vol-scaled long-only control, 2024-01-10 split, ETH replication','no local crypto data (E3-C25 UNVERIFIABLE)'),
                   ('RISK-2 ladder (owner decision)','sigma-scaled ladder on KOSPI VT20: Sharpe 0.40, MDD -37.4%, 1 halt','E5 figure, not re-run by the chair (R2_EXEC EX-T-11)'),
                   ('RISK-2 ladder (owner decision)','SPY cumulative vs non-cumulative steps (0.41 -> 0.02)','E5 figure, not re-run (R2_EXEC EC-T-10)'),
                   ('SCR-1/SCR-2 step 9','expected live diff = 0.6 x OOS (+1.85%/yr for B1/F4)','lab printed 0.4 x (+1.23%); 0.6 x 3.08% = 1.85% is arithmetic, not a lab output')]:
    add(nid(),card,'-',q,'-','-','-','NOT TRACED',None,'-','-',note=why,status='not traced')
out=pd.DataFrame(rows)
out.to_csv(OUT,index=False)
js=[{k:(None if (isinstance(v,float) and v!=v) else v) for k,v in r.items() if k!='raw'} for r in rows]
json.dump({'title':'R3 TF golden values (traced to file and line; line 1 = header)','generated':'2026-10-03','n':len(js),'items':js},open(JS,'w'),ensure_ascii=False,indent=1)
print(len(out),'golden values;',out.status.value_counts().to_dict())
