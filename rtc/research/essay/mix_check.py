# Is the rise in misreport (code 5) share driven by issues caught only via the misreport keyword family?
import pandas as pd, json, numpy as np
R='/home/hatim/applications/cltr2/rtc/research/'
rd=lambda f:pd.DataFrame([json.loads(l) for l in open(R+f)])
s1=rd('stage1_codes.jsonl').drop_duplicates('key',keep='last'); deep=rd('deep_codes.jsonl')
q=pd.DataFrame([{k:json.loads(l)[k] for k in ('key','repo','quarter','families')} for l in open(R+'queue.jsonl')])
L={3,4,5}; s=s1.merge(q,on='key')
s['cls']=np.where(s.codes.apply(lambda c: bool(set(c)&L)),'s1_loc',np.where(s.confidence=='low','s1_lowconf','unflagged'))
d=deep.merge(s[['key','quarter','cls','families']],on='key')
w=(s.groupby(['quarter','cls']).size()/d.groupby(['quarter','cls']).size()).rename('w'); d=d.join(w,on=['quarter','cls'])
d['loc']=d.codes.apply(lambda c: bool(set(c)&L)); d['c5']=d.codes.apply(lambda c:5 in c); d['c4']=d.codes.apply(lambda c:4 in c)
d['non_mis']=d.families.apply(lambda f: any(x!='misreport' for x in f))
d['P']=d.quarter.map({'2025Q3':'P1','2025Q4':'P1','2026Q2':'P2','2026Q3':'P2'})
for lab,sub in [('all LoC',d),('LoC caught by a non-misreport phrase',d[d.non_mis])]:
    g=sub[sub['loc']].groupby('P').apply(lambda g: pd.Series({'c5_share':100*(g.c5*g.w).sum()/g.w.sum(),'c4_share':100*(g.c4*g.w).sum()/g.w.sum(),'n':len(g)}),include_groups=False)
    print(lab); print(g.round(1))
