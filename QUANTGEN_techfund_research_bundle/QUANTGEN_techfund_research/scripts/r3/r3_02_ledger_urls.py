"""Parse the claims ledgers of the 14 round-1 papers: claim ID -> (claim text, tier, implication, URLs)."""
import re, json, glob, os
D='/home/claude/research_notes/QUANTGEN technical and fundamental signals/'
OUT='/home/claude/datalab/r3/results/r3_ledger_claims.json'
ID=re.compile(r'^\|\s*\**([PE][1-7]-C\d{2})\**\s*\|')
URL=re.compile(r'https?://[^\s|)\]>,;"]+')
res={}
for f in sorted(glob.glob(D+'[PE][1-7]_*.md')):
    for line in open(f,encoding='utf-8'):
        m=ID.match(line)
        if not m: continue
        cid=m.group(1)
        cells=[c.strip() for c in line.strip().strip('|').split('|')]
        urls=[u.rstrip('.') for u in URL.findall(line)]
        rec=dict(paper=os.path.basename(f)[:2], claim=cells[1] if len(cells)>1 else '', evidence=cells[2] if len(cells)>2 else '',
                 tier=cells[4] if len(cells)>4 else '', implication=cells[-1] if cells else '', urls=list(dict.fromkeys(urls)))
        if cid not in res or len(rec['urls'])>len(res[cid]['urls']): res[cid]=rec
json.dump(res,open(OUT,'w'),ensure_ascii=False,indent=0)
import collections
print(len(res), collections.Counter(k[:2] for k in res))
print(sum(1 for v in res.values() if v['urls']),'claims with >=1 URL')
for k in ['P6-C15','E7-C02','P3-C20','E6-C19','P2-C08','E3-C21','P6-C10','P5-C01','E5-C04','P4-C28']:
    v=res.get(k); print(k, (v['claim'][:90] if v else None), (v['urls'][:2] if v else None))
