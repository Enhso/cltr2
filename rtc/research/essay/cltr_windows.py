# GitHub rogue reports over the two windows behind CLTR's March "4.9x" (Scheming in the Wild, p.29):
# W1 = 12 Oct-12 Nov 2025, W2 = 9 Feb-12 Mar 2026. Same stratum weights and within quarter x stratum
# resampling as boot.py. Writes boot_out/cltr_windows.csv.
import pandas as pd, json, numpy as np
R='/home/hatim/applications/cltr2/rtc/research/'
# Issues filed per window: GitHub search total_count for `repo:R is:issue created:A..B`, retrieved 2026-10-17
# (the main analysis's monthly denominators were pulled on 2026-10-15).
T={'claude-code':(1987,8876),'codex':(757,1742),'gemini-cli':(1091,1584)}
W={'W1':('2025-10-12','2025-11-12'),'W2':('2026-02-09','2026-03-12')}
rd=lambda f:pd.DataFrame([json.loads(l) for l in open(R+f)])
s1=rd('stage1_codes.jsonl').drop_duplicates('key',keep='last'); deep=rd('deep_codes.jsonl')
q=pd.DataFrame([{k:json.loads(l)[k] for k in ('key','repo','quarter','created_at')} for l in open(R+'queue.jsonl')])
L={3,4,5}; s=s1.merge(q,on='key')
s['cls']=np.where(s.codes.apply(lambda c: bool(set(c)&L)),'s1_loc',np.where(s.confidence=='low','s1_lowconf','unflagged'))
d=deep.merge(s[['key','repo','quarter','cls','created_at']],on='key')
d['day']=d.created_at.str[:10]; d['r']=d.repo.str.split('/').str[1]
d['win']=None
for w,(a,b) in W.items(): d.loc[(d.day>=a)&(d.day<=b),'win']=w
d['loc']=d.codes.apply(lambda c: bool(set(c)&L)).astype(float)
d['cc']=(d.r=='claude-code').astype(float)
N=s.groupby(['quarter','cls']).size()
groups={k:g[['loc','cc']].assign(w1=(g.win=='W1').astype(float),w2=(g.win=='W2').astype(float)).to_numpy()
        for k,g in d.groupby(['quarter','cls']) if g.win.notna().any()}
T1=sum(v[0] for v in T.values()); T2=sum(v[1] for v in T.values()); C1,C2=T['claude-code']
rng=np.random.default_rng(2)
def est(res):
    a=np.zeros(4)  # all W1, all W2, cc W1, cc W2
    for k,g in groups.items():
        if res: g=g[rng.integers(0,len(g),len(g))]
        f=N[k]/len(g); loc,cc,w1,w2=g.T
        a+=f*np.array([(loc*w1).sum(),(loc*w2).sum(),(loc*cc*w1).sum(),(loc*cc*w2).sum()])
    return {'rogue_W1':a[0],'rogue_W2':a[1],'count_ratio':a[1]/a[0],'issue_ratio':T2/T1,
            'per1k_W1':1000*a[0]/T1,'per1k_W2':1000*a[1]/T2,'rate_ratio':(a[1]/T2)/(a[0]/T1),
            'cc_rogue_W1':a[2],'cc_rogue_W2':a[3],'cc_count_ratio':a[3]/a[2],'cc_issue_ratio':C2/C1,
            'cc_rate_ratio':(a[3]/C2)/(a[2]/C1)}
pt=est(False); B=pd.DataFrame([est(True) for _ in range(2000)])
res=pd.DataFrame({'est':pd.Series(pt),'lo':B.quantile(.025),'hi':B.quantile(.975)}).round(2)
print(res.to_string()); res.to_csv(R+'essay/boot_out/cltr_windows.csv')
