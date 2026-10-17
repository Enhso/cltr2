# Monthly stratum-weighted LoC estimates per 1k issues (quarter-level weights), pooled and Claude Code only.
import pandas as pd, json, numpy as np
R='/home/hatim/applications/cltr2/rtc/research/'
rd=lambda f:pd.DataFrame([json.loads(l) for l in open(R+f)])
s1=rd('stage1_codes.jsonl').drop_duplicates('key',keep='last'); deep=rd('deep_codes.jsonl')
q=pd.DataFrame([{k:json.loads(l)[k] for k in ('key','repo','quarter','month')} for l in open(R+'queue.jsonl')])
L={3,4,5}; s=s1.merge(q,on='key')
s['cls']=np.where(s.codes.apply(lambda c: bool(set(c)&L)),'s1_loc',np.where(s.confidence=='low','s1_lowconf','unflagged'))
d=deep.merge(s[['key','repo','quarter','month','cls']],on='key')
d['loc']=d.codes.apply(lambda c: bool(set(c)&L)); d['c45']=d.codes.apply(lambda c: bool(set(c)&{4,5}))
w=(s.groupby(['quarter','cls']).size()/d.groupby(['quarter','cls']).size()).rename('w'); d=d.join(w,on=['quarter','cls'])
den=pd.read_csv(R+'denominators.csv')
out=[]
for name,f in [('all',lambda x:x),('claude-code',lambda x:x[x.repo.str.contains('claude-code')])]:
    dd=f(d); T=f(den).groupby('month').total_issues.sum()
    e=dd.groupby('month').apply(lambda g:pd.Series({'loc':(g['loc']*g.w).sum(),'c45':(g.c45*g.w).sum()}),include_groups=False)
    e=e.join(T); e['loc_per1k']=1000*e['loc']/e.total_issues; e['c45_per1k']=1000*e.c45/e.total_issues; e['set']=name
    out.append(e.reset_index())
o=pd.concat(out); o.round(2).to_csv('/home/hatim/applications/cltr2/rtc/research/essay/monthly_loc.csv',index=False)
print(o.pivot(index='month',columns='set',values=['total_issues','loc_per1k','c45_per1k']).round(1).to_string())
