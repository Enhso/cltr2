# Checks behind essay sections 4-6 not covered by boot.py: what non-rogue matches are, keyword precision by family,
# behaviour and confidence mix of rogue reports, and duplicate-label shares. Stratum-weighted like monthly_series.py.
# Periods: P1 = 2025Q3-Q4, P2 = 2026Q2-Q3.
import pandas as pd, json, numpy as np
R='/home/hatim/applications/cltr2/rtc/research/'
rd=lambda f:pd.DataFrame([json.loads(l) for l in open(R+f)])
s1=rd('stage1_codes.jsonl').drop_duplicates('key',keep='last'); deep=rd('deep_codes.jsonl')
q=pd.DataFrame([{k:json.loads(l)[k] for k in ('key','repo','quarter','families','labels')} for l in open(R+'queue.jsonl')])
q['dup']=q.labels.apply(lambda L: any('duplicate' in str(x).lower() for x in (L or [])))
L={3,4,5}; s=s1.merge(q,on='key')
s['cls']=np.where(s.codes.apply(lambda c: bool(set(c)&L)),'s1_loc',np.where(s.confidence=='low','s1_lowconf','unflagged'))
d=deep.merge(s[['key','quarter','cls','families','dup']],on='key')
w=(s.groupby(['quarter','cls']).size()/d.groupby(['quarter','cls']).size()).rename('w'); d=d.join(w,on=['quarter','cls'])
d['loc']=d.codes.apply(lambda c: bool(set(c)&L))
d['P']=d.quarter.map({'2025Q3':'P1','2025Q4':'P1','2026Q2':'P2','2026Q3':'P2'})
wm=lambda g,x: 100*(x*g.w).sum()/g.w.sum()

print('Top code of each match, weighted % by quarter (rogue = any of 3/4/5):')
d['top']=np.where(d['loc'],'rogue',np.where(d.codes.apply(lambda c:2 in c),'2 competence',np.where(d.codes.apply(lambda c:1 in c),'1 user/approved','0 not agent action')))
t=d.groupby(['quarter','top']).w.sum().unstack(); print((t.div(t.sum(1),axis=0)*100).round(1).to_string())

print('\nPrecision (rogue share of matches) by keyword family, weighted %:')
for fam in ['destructive','ignored_instruction','safeguard_bypass','misreport']:
    m=d[d.families.apply(lambda f: fam in f)]
    print(f'  {fam:20s}', {p: round(wm(m[m.P==p], m[m.P==p]['loc']),1) for p in ['P1','P2']})

print('\nRogue reports: behaviour and confidence mix, weighted %:')
r=d[d['loc']].copy()
for c in (3,4,5): r[f'c{c}']=r.codes.apply(lambda x: c in x)
r['irrev']=r.irreversible=='y'
for p in ['P1','P2']:
    g=r[r.P==p]
    print(f'  {p}', {k: round(wm(g,g[k]),1) for k in ['c3','c4','c5','irrev']},
          {f'conf_{c}': round(wm(g,g.confidence==c),1) for c in ['high','medium','low']})

print('\nDuplicate label, % by quarter: all matches', (100*q.groupby('quarter').dup.mean()).round(1).to_dict())
print('                             rogue reports (weighted)', {k: round(wm(g,g.dup),1) for k,g in r.groupby('quarter')})
