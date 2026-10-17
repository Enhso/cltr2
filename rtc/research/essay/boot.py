# Bootstrap (within quarter x stratum) CIs for LoC rates, subtype shares, and period contrasts.
# Usage: python3 boot.py [repo-substring] [--drop-audit]
import pandas as pd, json, numpy as np, sys
R='/home/hatim/applications/cltr2/rtc/research/'
args=[a for a in sys.argv[1:] if not a.startswith('--')]; repo=args[0] if args else None
rd=lambda f:pd.DataFrame([json.loads(l) for l in open(R+f)])
s1=rd('stage1_codes.jsonl').drop_duplicates('key',keep='last'); deep=rd('deep_codes.jsonl')
q=pd.DataFrame([{k:json.loads(l)[k] for k in ('key','repo','quarter')} for l in open(R+'queue.jsonl')])
L={3,4,5}
s=s1.merge(q,on='key')
s['cls']=np.where(s.codes.apply(lambda c: bool(set(c)&L)),'s1_loc',np.where(s.confidence=='low','s1_lowconf','unflagged'))
d=deep.merge(s[['key','repo','quarter','cls']],on='key')
if '--drop-audit' in sys.argv: d=d[~d.reason.isin(['audit','validation'])]
# 2026 strata are sampled; keep only draws from the current (inspectable) sampler there
if '--drop-phase1' in sys.argv: d=d[~(d.reason.isin(['flagged','audit']) & (d.quarter>='2026Q1'))]
den=pd.read_csv(R+'denominators.csv'); den['quarter']=pd.PeriodIndex(den.month,freq='M').asfreq('Q').astype(str)
if repo: s=s[s.repo.str.contains(repo)]; d=d[d.repo.str.contains(repo)]; den=den[den.repo.str.contains(repo)]
T=den.groupby('quarter').total_issues.sum()
d['loc']=d.codes.apply(lambda c: bool(set(c)&L)).astype(float)
d['c4or5']=d.codes.apply(lambda c: bool(set(c)&{4,5})).astype(float)
d['c5']=d.codes.apply(lambda c: 5 in c).astype(float)
d['c4']=d.codes.apply(lambda c: 4 in c).astype(float)
d['irrev']=d['loc']*(d.irreversible=='y')
if '--no-lowconf' in sys.argv:
    for c in ['loc','c4or5','c5','c4','irrev']: d[c]=d[c]*(d.confidence!='low')
N=s.groupby(['quarter','cls']).size()
V=['loc','c4','c5','c4or5','irrev']
groups={k:g[V].to_numpy() for k,g in d.groupby(['quarter','cls'])}
Q=sorted(T.index); P1=['2025Q3','2025Q4']; P2=['2026Q2','2026Q3']
rng=np.random.default_rng(0)
def est(resample):
    tot={qq:np.zeros(len(V)) for qq in Q}
    for (qq,c),a in groups.items():
        if resample: a=a[rng.integers(0,len(a),len(a))]
        tot[qq]+=N[(qq,c)]*a.mean(0)
    out={}
    for qq in Q: out[f'per1k_{qq}']=1000*tot[qq][0]/T[qq]
    for qq in Q: out[f'sh45_{qq}']=100*tot[qq][3]/tot[qq][0] if tot[qq][0] else np.nan
    a1=sum(tot[x] for x in P1); a2=sum(tot[x] for x in P2)
    t1=T[P1].sum(); t2=T[P2].sum()
    out['rate_ratio_P2/P1']=(a2[0]/t2)/(a1[0]/t1)
    out['count_ratio_P2/P1']=a2[0]/a1[0]; out['issue_ratio_P2/P1']=t2/t1
    for i,v in enumerate(V[1:],1): out[f'share_{v}_P1']=100*a1[i]/a1[0]; out[f'share_{v}_P2']=100*a2[i]/a2[0]
    out['c4or5_per1k_ratio']=(a2[3]/t2)/(a1[3]/t1)
    return out
pt=est(False); B=pd.DataFrame([est(True) for _ in range(2000)])
res=pd.DataFrame({'est':pd.Series(pt),'lo':B.quantile(.025),'hi':B.quantile(.975)}).round(2)
print(f"repo={repo or 'ALL'} flags={[a for a in sys.argv[1:] if a.startswith('--')]}"); print(res.to_string())
# BOOT_CSV=path saves the table (used by figures.py)
import os
if os.environ.get('BOOT_CSV'): res.to_csv(os.environ['BOOT_CSV'])
