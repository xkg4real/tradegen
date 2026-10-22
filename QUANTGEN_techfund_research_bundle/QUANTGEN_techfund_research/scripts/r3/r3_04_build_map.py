# -*- coding: utf-8 -*-
"""R3 Neural Link: build nodes, edges, focus counts, weight table and go/no-go register; write CSV and chart JSON.
Inputs: r3_nodes_def.py (judgement), the two R2 claim matrices, the parsed round-1 ledgers (r3_ledger_claims.json).
Focus counts: fp / fe = distinct professor / executive ledger claim IDs (supporting + qualifying/contradicting, ranges expanded) across the
claim-matrix propositions mapped to the node (primary and secondary), plus distinct non-ledger references (position paragraphs, data-check
requests, constraint lists) cited in those propositions.
"""
import sys, json, re, collections, pandas as pd
sys.path.insert(0,'/home/claude/datalab/r3/scripts')
from r3_00_claims import load, ids, others
from r3_nodes_def import N
R='/home/claude/datalab/r3/'
props=load()
led=json.load(open(R+'results/r3_ledger_claims.json'))
pm=pd.read_csv('/home/claude/datalab/r2/verification/prof_claim_matrix.csv').set_index('prop_id')
em=pd.read_csv('/home/claude/datalab/r2/verification/exec_claim_matrix.csv').set_index('prop_id')
# ---- coverage check: every proposition mapped at least once
allP=set(pm.index); allX=set(em.index); used=set()
def pid(e): return e.split(':')[0]
def contrib(e):
    p=pid(e); pr=props[p]
    if ':' not in e: return pr['sup']|pr['qual'], set(pr['other'])
    toks=[t.strip() for t in e.split(':',1)[1].split(',')]
    led_ids={t for t in toks if re.match(r'^[PE][1-7]-C\d{2}$',t)}
    oth={t for t in toks if t not in led_ids}
    allc=pr['sup']|pr['qual']
    bad=led_ids-allc
    assert not bad, (e,bad)
    oo={o for o in pr['other'] if any(o.endswith(t) or t in o for t in oth)}
    assert len(oo)==len(oth), (e,oth,pr['other'])
    return led_ids, oo
for n in N: used.update(pid(e) for e in n['P']+n['Ps']+n['X']+n['Xs'])
missing=sorted((allP|allX)-used)
assert not missing, missing
prim=collections.Counter()
for n in N: prim.update(pid(e) for e in n['P']+n['X'])
def members(pid):
    if pid in pm.index:
        v=str(pm.loc[pid,'members_holding']); return set(re.findall(r'P[1-7]',v))
    v=str(em.loc[pid,'holders_for']); return set(re.findall(r'E[1-7]',v))
URLPREF=['nber.org','ssrn','sciencedirect','jstor','wiley','tandfonline','emerald','e-kjfs','kci.go.kr','dachxiu','aqr.com','arxiv','duke.edu','federalreserve','repec','cambridge.org','oup.com','springer','msci.com','spglobal','ishares','krx','dart','fsc.go.kr','bis.org','kentdaniel','yale.edu','chicagobooth','nyu.edu','mit.edu','harvard','wharton','lse.ac.uk']
def pick_urls(claims,k=3):
    cand=[]
    for c in sorted(claims):
        r=led.get(c)
        if not r: continue
        t1=1 if 'T1' in r.get('tier','') else (2 if 'T2' in r.get('tier','') else 3)
        for u in r['urls']:
            pref=0 if any(p in u for p in URLPREF) else 1
            cand.append((t1,pref,c,u))
    cand.sort(); out=[]; seen=set()
    for t,p,c,u in cand:
        if u in seen: continue
        seen.add(u); out.append(f'{u} [{c}]')
        if len(out)>=k: break
    return out
rows=[]
for n in N:
    Pall=n['P']+n['Ps']; Xall=n['X']+n['Xs']
    pl=set(); po=set(); xl=set(); xo=set(); pmem=set(); xmem=set()
    for p in Pall:
        a,b=contrib(p); pl|=a; po|=b; pmem|=members(pid(p))
    for x in Xall:
        a,b=contrib(x); xl|=a; xo|=b; xmem|=members(pid(x))
    fp=len(pl)+len(po); fe=len(xl)+len(xo)
    urls=pick_urls(pl|xl)
    rows.append(dict(node_id=n['id'],theme=n['theme'],label=n['label'],fp=fp,fe=fe,fp_ledger=len(pl),fp_other=len(po),fe_ledger=len(xl),fe_other=len(xo),
        prof_members=' '.join(sorted(pmem)),exec_members=' '.join(sorted(xmem)),ps=n['ps'],es=n['es'],data=n['data'],data_files=n['dfiles'],
        class_rule=n['crule'],ruling=n['ruling'],cls=n['cls'],class_changed_by_ruling=(n['crule']!=n['cls']),destination=n['dest'],decision=n['dec'],key_numbers=n['key'],
        settling_test=n['settle'],prof_props=' '.join(n['P'])+(' | sec: '+' '.join(n['Ps']) if n['Ps'] else ''),exec_props=' '.join(n['X'])+(' | sec: '+' '.join(n['Xs']) if n['Xs'] else ''),
        prof_chair_items=n['pitems'],exec_chair_items=n['eitems'],prof_claims=' '.join(sorted(pl)),exec_claims=' '.join(sorted(xl)),other_refs='; '.join(sorted(po|xo)),urls=' ; '.join(urls)))
nodes=pd.DataFrame(rows)
nodes.to_csv(R+'R3_TF_nodes.csv',index=False)
# ---------------- edges ----------------
E=[
('TF-03','TF-19','refutes','KRX-adjusted holding returns give +1.43%/month (t 3.3); the KJFS sign appears only with unadjusted closes (-11.37%/month).'),
('TF-01','TF-21','supports','KRX 12-1 momentum is earned overnight (+18.4%/yr vs -7.9% intraday), so the constrained card must fill at the close.'),
('TF-01','TF-02','qualifies','Close fills need the locked-limit exception: a locked limit-up close cannot be bought.'),
('TF-02','TF-14','qualifies','Attention and limit events act over 5-20 sessions, so they belong in the entry rule, not in a month-end screen.'),
('TF-12','TF-02','supports','The F4 screen cuts entries at a locked limit-up close from 6.3% to 1.9% of EW-book entries.'),
('TF-07','TF-41','refutes','Weekly reversal break-even is 12.5 bp per side (22.2 bp VW), far below 2 x 35 bp: rejected before the gate.'),
('TF-07','TF-14','refutes','The F5 attention screen breaks even at 68 bp per side on the EW book, below 70 bp: rejected before the gate.'),
('TF-07','TF-20','refutes','Raw 12-1 L/S quintiles break even near 64 bp per side, below 70 bp.'),
('TF-07','TF-61','refutes','Intraday edges of 1-7 bp cannot pay a 25-46 bp KRX round trip.'),
('TF-07','TF-34','refutes','SPY trend turnover of 7.3-11.9 units/yr costs 3.7-6.0%/yr at 50 bp per side.'),
('TF-08','TF-12','supports','Screens add under one unit of turnover per year (F4: 2.8 vs 1.9), well inside the turnover limit.'),
('TF-09','TF-07','qualifies','Break-even screens use the flat 35 bp until quote calibration; a bucket may only raise the cost.'),
('TF-10','TF-21','qualifies','No name-level stops: a 15% stop cut KRX 12-1 net Sharpe from 0.04 to -0.15 (EW) and 0.28 to 0.07 (VW).'),
('TF-10','TF-30','qualifies','Trend sleeves stop through their own signal exit; a separate stop layer double counts.'),
('TF-11','TF-21','qualifies','The winner-led 2026-06-22..07-30 crash replay is mandatory for any Korean momentum card.'),
('TF-11','TF-22','supports','The 2026 replay shows R-03 had cut exposure to 0.55 / 0.27 before the crash (VW L/S -10.5% vs -40.3% static).'),
('TF-04','TF-36','qualifies','Prerequisite: the KR-VQ composite needs the OpenDART point-in-time store (statements from 2015).'),
('TF-04','TF-43','qualifies','Prerequisite: US-VQ needs EDGAR acceptance-time data and FMP prices.'),
('TF-04','TF-38','qualifies','Prerequisite: a Korean drift test needs DART timestamps (entry at rcept_dt + 1 session).'),
('TF-04','TF-46','qualifies','Prerequisite: insider and IPO tests need EDGAR Form 4 / S-1 data with acceptance times.'),
('TF-04','TF-40','supports','Forward archives include final investor flows with timestamps.'),
('TF-05','TF-36','qualifies','Korean value tests must split at 2024-02-26 (Value-up).'),
('TF-05','TF-37','qualifies','Value-up ETF returns are chip beta, not value evidence; regime split required.'),
('TF-06','TF-12','supports','The low-risk/lottery premium sits in the short leg; the long-only form is an exclusion screen.'),
('TF-06','TF-17','refutes','Long-only low-vol top quintile excess is +1.1%/yr (t 0.5) EW and -1.8% VW.'),
('TF-06','TF-20','refutes','Long-only 12-1 top-quintile excess is -1.3%/yr (t -0.6).'),
('TF-26','TF-20','qualifies','A 5% name cap cuts VW 12-1 net Sharpe in 2016-26 from 0.30 to 0.02: the post-2016 VW edge is a two-stock artefact.'),
('TF-26','TF-31','qualifies','The pair cap applies on look-through to the KOSPI ETF line once the pair share exceeds 0.45 (owner open point).'),
('TF-06','TF-26','supports','Benchmark set includes CW ex-pair and capped CW (H1-2026 CW +117.1% vs EW +3.4%).'),
('TF-12','TF-15','supports','Inside the 12-1 top quintile the F4 screen adds +6.13%/yr (IR 1.24).'),
('TF-13','TF-12','qualifies','Dilution and lottery flags overlap little (Jaccard 0.13): complementary screens; report the overlap.'),
('TF-14','TF-12','conflicts','Adding the attention screen to the composite (F8) lowers the IR from 1.53 to 0.67.'),
('TF-15','TF-21','supports','The constrained card inherits the exclusion (+7.81%/yr vs the unfiltered momentum quintile).'),
('TF-16','TF-12','supports','Low volatility enters as the high-volatility tail exclusion inside the lottery composite (F2 alone +3.64%/yr on B1).'),
('TF-59','TF-16','refutes','Against the same-beta static book S_beta, Korean low-vol drawdowns are 7-22 pp worse and the tail ratio is 0.97-0.99.'),
('TF-50','TF-17','refutes','Low-vol CAPM alpha is +2.2% (t 0.8) EW, +0.7% (t 0.3) VW: a factor tilt, not alpha.'),
('TF-50','TF-18','qualifies','Size stays an attribution factor (SMB) and a microcap risk control, not a signal.'),
('TF-19','TF-41','refutes','The -2.95 anchor that justified reversal weight 3 is a regression slope, not a spread.'),
('TF-19','TF-20','qualifies','Momentum is positive but fragile, not negative; the drop rests on net-of-cost failure, not on sign.'),
('TF-22','TF-20','qualifies','Controls raise full-sample net Sharpe (0.20 -> 0.31 EW) but lower 2016-26 and leave long-only winners negative.'),
('TF-22','TF-21','supports','The constrained card is R-03 scaled: the only control de-risked before July 2026.'),
('TF-23','TF-22','qualifies','The D-M gate was off on 2026-06-22 and fired 9 times in 30 years; R-03 carries the crash control on KRX.'),
('TF-24','TF-21','qualifies','The 52-week high may be tested once inside the constrained card as a Tier A single configuration.'),
('TF-25','TF-22','qualifies','Any crowding multiplier must beat R-03 out of sample before it acts.'),
('TF-27','TF-31','qualifies','A book-level ladder on VT20 cuts Sharpe 0.40 -> 0.35 and max DD -47.4% -> -34.8%.'),
('TF-28','TF-27','qualifies','Threshold units remain open; fixed and sigma ladders coincide at an 8% book volatility.'),
('TF-22','TF-29','qualifies','US momentum gets weight 1 only as an R-03-scaled composite or ETF leg.'),
('TF-62','TF-24','supports','The 52-week high is one of the feature primitives.'),
('TF-30','TF-59','supports','Single-index trend is judged on CARD-P checks against S, never on step 5 alone.'),
('TF-31','TF-32','supports','VT20 is the robust component of the floored product (PASS from every start 1996-2006).'),
('TF-33','TF-32','qualifies','Flooring trend gives back slow-bear protection (1997-98: -39.2% vs -6.9%) unless VT20 sits on top.'),
('TF-03','TF-30','qualifies','Month-end data only: Shiller averages inflate trend Sharpe by +0.10 (SMA10) to +0.23 (12-month sign).'),
('TF-59','TF-31','supports','VT20 fails CARD-O step 5 (p 0.51) yet passes CARD-P (dMDD +6.5 pp vs S).'),
('TF-54','TF-31','qualifies','INSUFFICIENT DATA from 2011/2016 starts reflects power (11-16 years), not failure.'),
('TF-30','TF-35','qualifies','Single-asset trend is weak; a diversified book must claim breadth (>= 25 markets).'),
('TF-67','TF-30','qualifies','Crypto trend C3 is the one technical alpha card kept (CARD-O PASS); the CARD-P-only rule covers equity single-index trend.'),
('TF-51','TF-60','refutes','Family tests reject classic rules: SPA p 0.880 over 303 KOSPI rules; 0.82-0.97 over 322 SPY rules.'),
('TF-13','TF-36','supports','Net issuance, a KR-VQ leg, is already buildable from KRX share counts.'),
('TF-37','TF-36','qualifies','Individual value and quality weights stay 1 until a point-in-time test passes.'),
('TF-44','TF-43','qualifies','Quality enters as a composite leg at weight 2, never as a hedge.'),
('TF-45','TF-43','qualifies','Earnings drift only as a confirmation input inside a composite; the standalone card is dropped.'),
('TF-56','TF-43','qualifies','Expected net L/S Sharpe after decay haircuts at 50 bp is 0.42 (0.17 after the 60% haircut).'),
('TF-39','TF-40','qualifies','No direction rule; flows are logged to build a t-1 history for an open-leg test.'),
('TF-41','TF-42','qualifies','Reversal is real gross but not net; only a conditioning guard survives.'),
('TF-41','TF-60','qualifies','RSI14 and %B are re-parameterised 1-month reversal (correlation 0.92 / 0.87) and share its net failure.'),
('TF-22','TF-41','qualifies','Vol scaling hurts reversal (KR STR EW net -0.29 -> -0.59), consistent with macro R-05 (reversal at 1.0x).'),
('TF-56','TF-47','refutes','Live records undercut headline backtests: FFTY 3.52%/yr vs 13-14% for the S&P; AIEQ 4.18% vs 12.65%.'),
('TF-51','TF-12','qualifies','Pooled over 176 trials the screen\'s deflated Sharpe is 0.94 < 0.95: REVISE, not PASS.'),
('TF-53','TF-54','qualifies','Longer blocks fix the size of steps 2 and 5; power stays the binding constraint.'),
('TF-54','TF-58','supports','History cannot settle realistic edges (Sharpe 0.4 needs 40 years for 80% power): prospective incubation is the clean test.'),
('TF-55','TF-54','qualifies','Step 8 alone passes 24-31% of zero-Sharpe strategies, but the joint false-pass rate is 0.5% at 10 years.'),
('TF-57','TF-56','conflicts','The per-factor Ilmanen haircuts in the macro spec are unverifiable; plan with 0.5 / 0.3 and measured local decay.'),
('TF-58','TF-21','qualifies','The constrained card runs as FORWARD-SIM (incubation from the header commit).'),
('TF-58','TF-32','qualifies','The floored trend x VT20 cell runs as FORWARD-SIM; its plateau and start-date sweep are still owed.'),
('TF-50','TF-16','qualifies','Jensen\'s alpha against a beta-matched benchmark is the alpha-side test for beta < 1 sleeves.'),
('TF-52','TF-51','qualifies','Tiered hurdles would complement the family gate (one-sided professors\' proposal).'),
('TF-62','TF-63','supports','L0 combines the primitive features with signs fixed in advance.'),
('TF-63','TF-64','qualifies','Nonlinear combiners run only as shadows against L0/L1: a +0.10 uplift needs 27-108 years to detect.'),
('TF-66','TF-63','qualifies','No macro x characteristic terms in any combiner (macro P1).'),
('TF-58','TF-65','refutes','In-window LLM backtests are contaminated; only point-in-time models are honest.'),
('TF-69','TF-68','refutes','Short-horizon crypto cross-sectional evidence is momentum (1-4 weeks), not reversal.'),
('TF-67','TF-69','qualifies','C3 stays the crypto trend card; CTREND-lite would be a separate, pre-registered card.'),
('TF-35','TF-70','qualifies','FX trend only inside a diversified futures book or as one USD/KRW slow-trend test.'),
('TF-30','TF-34','qualifies','US single-index trend is CARD-P only; at 50 bp it fails PC-1, at 5 bp it is INSUFFICIENT DATA.'),
('TF-12','TF-17','qualifies','Low volatility survives only as the high-vol tail exclusion inside the screen.'),
]
ed=pd.DataFrame(E,columns=['source','target','type','reason'])
ids_ok=set(nodes.node_id); assert set(ed.source)<=ids_ok and set(ed.target)<=ids_ok
ed.insert(0,'edge_id',[f'E-{i+1:03d}' for i in range(len(ed))])
ed.to_csv(R+'R3_TF_edges.csv',index=False)
# ---------------- charts: focus map ----------------
fm=[dict(node_id=r.node_id,label=r.label,theme=r.theme,fp=int(r.fp),fe=int(r.fe),focus_total=int(r.fp+r.fe),cls=r.cls,class_rule=r.class_rule,ps=r.ps,es=r.es,data=r.data,destination=r.destination,decision=r.decision) for r in nodes.itertuples()]
json.dump({'title':'R3 TF focus map: professor vs executive claims devoted to each node','x':'fp (distinct professor claims)','y':'fe (distinct executive claims)',
           'note':'fp/fe = distinct ledger claim IDs (supporting + qualifying) plus distinct non-ledger references in the mapped claim-matrix propositions; a claim can count for more than one node.',
           'nodes':fm,'edges':[dict(source=a,target=b,type=t) for _,a,b,t,_ in ed.itertuples(index=False)]},open(R+'charts/focus_map.json','w'),ensure_ascii=False,indent=1)
print('nodes',len(nodes),'edges',len(ed))
print(nodes.cls.value_counts().to_dict()); print(nodes.class_rule.value_counts().to_dict())
print(nodes[['node_id','fp','fe','fp_ledger','fp_other','fe_ledger','fe_other','cls']].assign(t=lambda d:d.fp+d.fe).sort_values('t',ascending=False).head(20).to_string(index=False))
# focus by theme
tot_p=len(set(' '.join(nodes.prof_claims).split())); tot_e=len(set(' '.join(nodes.exec_claims).split()))
print('distinct claims covered',tot_p,tot_e)
th=nodes.groupby('theme').agg(fp=('fp','sum'),fe=('fe','sum'),n=('node_id','count'))
print(th)
json.dump({'by_theme':{k:dict(fp=int(v.fp),fe=int(v.fe),n=int(v.n)) for k,v in th.iterrows()}},open(R+'results/r3_focus_by_theme.json','w'),indent=1)
# ---------------- mechanical class check (precedence rules stated in the method) ----------------
DESIGN={'TF-04','TF-40','TF-63'}
SUP={'Strong','Moderate'}
def rule_class(r):
    ps,es,data=r.ps,r.es,r.data
    if (ps=='Refuted' and es=='Refuted') or (ps=='Refuted' and es=='Silent' and data=='Refutes') or (es=='Refuted' and ps=='Silent' and data=='Refutes'):
        return 'CORE-PROHIBITION'
    if ps=='Silent' or es=='Silent':
        return 'ONE-SIDED'
    if ps in SUP and es in SUP:
        if data=='Refutes': return 'CONTESTED'
        if data=='Untested' and r.node_id not in DESIGN: return 'UNTESTED'
        return 'CORE-LINK'
    if ps=='Split' or es=='Split' or (ps=='Refuted')!=(es=='Refuted'):
        return 'CONTESTED'
    if (ps in SUP and es=='Weak') or (es in SUP and ps=='Weak'):
        return 'ONE-SIDED'
    if ps=='Weak' and es=='Weak':
        return 'UNTESTED' if data=='Untested' else 'ONE-SIDED'
    return 'CHECK'
nodes['class_mechanical']=nodes.apply(rule_class,axis=1)
bad=nodes[nodes.class_mechanical!=nodes.class_rule]
print('mechanical vs stated class_rule mismatches:',len(bad))
if len(bad): print(bad[['node_id','ps','es','data','class_rule','class_mechanical']].to_string(index=False))
nodes.to_csv(R+'R3_TF_nodes.csv',index=False)
