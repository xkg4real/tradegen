"""R3 helper: parse ledger claim IDs out of the two R2 claim matrices.
Ledger IDs: P#-C## (professors), E#-C## (executives). Ranges like 'E2-C01..C11' or 'E6-C21..C24' are expanded.
Non-ledger references (e.g. 'E7 constraint 3', 'E5 RL-3', 'E4 DC-1', 'E2 B1-B3', 'E6 #6/#7', 'E3 sec.6 F3') are kept as 'other' items.
"""
import re, pandas as pd
V='/home/claude/datalab/r2/verification/'
ID=re.compile(r'\b([PE][1-7])-C(\d{2})(?:\.\.C(\d{2}))?')
def ids(text):
    out=set()
    if not isinstance(text,str): return out
    for m in ID.finditer(text):
        p,a,b=m.group(1),int(m.group(2)),m.group(3)
        if b:
            for k in range(a,int(b)+1): out.add(f'{p}-C{k:02d}')
        else: out.add(f'{p}-C{a:02d}')
    return out
OTHER=re.compile(r'\b([PE][1-7])\s+(constraint \d+|RL-\d+|DC-?\w+|B\d+(?:[-,]B?\d+)*|#\d+(?:/#\d+)*|sec\.\s?\d+(?: item \d+)?(?: [A-Z]\d)?|section \d+\S*|position \d+|rank \d+|F\d+(?: card)?|weights|ranked table[ \d-]*|power table|cost arithmetic|architecture|conflicts|DROP list|KQ\d|X\d/X\d|D\d|T\d|gaps|D table|\(KR quality 1->2\)|\(section 0 clarification\))')
def others(text):
    out=set()
    if not isinstance(text,str): return out
    for m in OTHER.finditer(text):
        out.add(f'{m.group(1)} {m.group(2).strip()}')
    return out
def load():
    pm=pd.read_csv(V+'prof_claim_matrix.csv'); em=pd.read_csv(V+'exec_claim_matrix.csv')
    rows={}
    for _,r in pm.iterrows():
        sup=ids(r['supporting_claims']); q=ids(r['contradicting_or_qualifying_claims'])
        rows[r['prop_id']]=dict(panel='P',sup=sup,qual=q,other=others(str(r['supporting_claims']))|others(str(r['contradicting_or_qualifying_claims'])),status=r['panel_status'],res=r['resolution_id'])
    for _,r in em.iterrows():
        sup=ids(r['supporting_claims']); q=ids(r['qualifying_or_contradicting_claims'])
        rows[r['prop_id']]=dict(panel='E',sup=sup,qual=q,other=others(str(r['supporting_claims']))|others(str(r['qualifying_or_contradicting_claims'])),status=r['panel_status'],res=r['resolution_item'])
    return rows
if __name__=='__main__':
    rows=load()
    P=set();E=set()
    for k,v in rows.items():
        (P if v['panel']=='P' else E).update(v['sup']|v['qual'])
    print('distinct prof ledger IDs in matrix:',len(P)); print('distinct exec ledger IDs in matrix:',len(E))
    import collections
    print(collections.Counter(x.split('-')[0] for x in P)); print(collections.Counter(x.split('-')[0] for x in E))
    for k,v in rows.items(): print(k,len(v['sup']),len(v['qual']),sorted(v['other']))
