# Per-product and fixed-product-mix rate ratios, Apr-Sep 2026 vs Jul-Dec 2025 (same within quarter x stratum resampling as boot.py).
# loc = any of codes 3/4/5; c45 = code 4 or 5. fixmix_P1w/P2w hold the product mix at Jul-Dec 2025 / Apr-Sep 2026 issue shares. Writes boot_out/mix.csv.
import pandas as pd, json, numpy as np
R='/home/hatim/applications/cltr2/rtc/research/'
rd=lambda f:pd.DataFrame([json.loads(l) for l in open(R+f)])
s1=rd('stage1_codes.jsonl').drop_duplicates('key',keep='last'); deep=rd('deep_codes.jsonl')
q=pd.DataFrame([{k:json.loads(l)[k] for k in ('key','repo','quarter')} for l in open(R+'queue.jsonl')])
L={3,4,5}; s=s1.merge(q,on='key')
s['cls']=np.where(s.codes.apply(lambda c: bool(set(c)&L)),'s1_loc',np.where(s.confidence=='low','s1_lowconf','unflagged'))
d=deep.merge(s[['key','repo','quarter','cls']],on='key')
d['loc']=d.codes.apply(lambda c: bool(set(c)&L)).astype(float)
d['c45']=d.codes.apply(lambda c: bool(set(c)&{4,5})).astype(float)
repos=['claude-code','codex','gemini-cli']; d['ri']=d.repo.str.split('/').str[1].map({r:i for i,r in enumerate(repos)})
den=pd.read_csv(R+'denominators.csv'); den['quarter']=pd.PeriodIndex(den.month,freq='M').asfreq('Q').astype(str); den['r']=den.repo.str.split('/').str[1]
P1=['2025Q3','2025Q4']; P2=['2026Q2','2026Q3']
T1=den[den.quarter.isin(P1)].groupby('r').total_issues.sum()[repos].to_numpy(float)
T2=den[den.quarter.isin(P2)].groupby('r').total_issues.sum()[repos].to_numpy(float)
N=s.groupby(['quarter','cls']).size()
groups={k:g[['ri','loc','c45']].to_numpy() for k,g in d.groupby(['quarter','cls']) if k[0] in P1+P2}
rng=np.random.default_rng(1)
def est(res):
    a={'P1':np.zeros((3,2)),'P2':np.zeros((3,2))}
    for (qq,c),g in groups.items():
        if res: g=g[rng.integers(0,len(g),len(g))]
        n=len(g); per='P1' if qq in P1 else 'P2'
        for r in range(3):
            m=g[:,0]==r
            a[per][r]+=N[(qq,c)]*g[m,1:].sum(0)/n
    o={}
    for j,v in enumerate(['loc','c45']):
        r1=a['P1'][:,j]/T1; r2=a['P2'][:,j]/T2
        for i,rp in enumerate(repos): o[f'{v}_ratio_{rp}']=r2[i]/r1[i]
        p1=a['P1'][:,j].sum()/T1.sum(); p2=a['P2'][:,j].sum()/T2.sum()
        w1=T1/T1.sum(); w2=T2/T2.sum()
        o[f'{v}_ratio_pooled']=p2/p1
        o[f'{v}_ratio_fixmix_P1w']=(w1*r2).sum()/p1
        o[f'{v}_ratio_fixmix_P2w']=p2/(w2*r1).sum()
        o[f'{v}_ratio_cc+codex_P2w']=(w2[:2]*r2[:2]).sum()/(w2[:2]*r1[:2]).sum()
    return o
pt=est(False); B=pd.DataFrame([est(True) for _ in range(2000)])
res=pd.DataFrame({"est":pd.Series(pt),"lo":B.quantile(.025),"hi":B.quantile(.975)}).round(2); print(res.to_string()); res.to_csv(R+"essay/boot_out/mix.csv")
