import itertools, random
from math import comb
def rank(vals):
    s=sorted((v,i) for i,v in enumerate(vals)); r=[0]*len(vals); i=0
    while i<len(s):
        j=i
        while j+1<len(s) and s[j+1][0]==s[i][0]: j+=1
        for k in range(i,j+1): r[s[k][1]]=(i+j)/2+1
        i=j+1
    return r
def mw_p_onesided(sync, writer):
    allv=sync+writer; r=rank(allv); n=len(sync)
    obs=sum(r[:n]); cnt=0; tot=0
    for c in itertools.combinations(range(len(allv)),n):
        tot+=1
        if sum(r[i] for i in c)<=obs+1e-9: cnt+=1
    return cnt/tot
# critical rank sums, no ties
for n in (4,6):
    N=2*n; tot=comb(N,n)
    print(f"{n} vs {n}: one-sided p by rank sum of the smaller arm (no ties)")
    cum=0
    for W in range(n*(n+1)//2, n*(n+1)//2+12):
        c=sum(1 for s in itertools.combinations(range(1,N+1),n) if sum(s)==W); cum+=c
        print(f"   W<={W}: p={cum/tot:.4f}")
# empirical power: writer 3-min counts seen 11-01 with UI drawing, boot 2; sync 3-min windows seen 11-01
writer_pool=[1,34,153,71]
sync_pool=[0,0,3,0,4]   # #74, #75, and #78's three 3-min windows (min 1-3: 3, 4-6: 0, 7-9: 4)
random.seed(1)
def sim(nper, trials=20000):
    sep=0; p05=0
    for _ in range(trials):
        w=[random.choice(writer_pool) for _ in range(nper)]
        s=[random.choice(sync_pool) for _ in range(nper)]
        if min(w)>max(s): sep+=1
        if mw_p_onesided(s,w)<=0.05: p05+=1
    return sep/trials, p05/trials
for nper in (4,6):
    a,b=sim(nper, 4000 if nper==6 else 20000)
    print(f"{nper} vs {nper}: P(complete separation)={a:.2f}  P(exact MW one-sided p<=0.05)={b:.2f}")
# B6: two clean 10-min takes under the 11-01 sync regime
for pf in (0.25,0.5):
    print(f"P(2 clean 10-min takes | per-take loss prob {pf}) = {(1-pf)**2:.2f}")
print("0 of k failing takes bounds per-take failure prob (95%):", {k: round(1-0.05**(1/k),2) for k in (2,5,10)})
# kswapd share recomputed with the actual frame counts of #70-#72 at 16.9 MB/frame and 16 KiB pages
for t,pg,fr in ((70,3.45e6,4469),(71,3.04e6,4349),(72,3.02e6,4430)):
    gb=pg*16384/1e9; wr=fr*16.9e-3
    print(f"#{t}: kswapd {gb:.1f} GB of {wr:.1f} GB written = {100*gb/wr:.0f}%")
