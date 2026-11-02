import math, itertools
from math import lgamma, log, exp

def lchoose(n,k): return lgamma(n+1)-lgamma(k+1)-lgamma(n-k+1)
def hyper_logpmf(a, r1, r2, c1):
    # table [[a, r1-a],[c1-a, r2-(c1-a)]], N=r1+r2, column total c1
    N=r1+r2
    return lchoose(r1,a)+lchoose(r2,c1-a)-lchoose(N,c1)
def fisher_two_sided(a,b,c,d):
    r1=a+b; r2=c+d; c1=a+c
    lo=max(0,c1-r2); hi=min(r1,c1)
    obs=hyper_logpmf(a,r1,r2,c1)
    tot=0.0
    for x in range(lo,hi+1):
        lp=hyper_logpmf(x,r1,r2,c1)
        if lp<=obs+1e-12: tot+=exp(lp)
    return tot
def fisher_one_sided_greater(a,b,c,d):
    r1=a+b; r2=c+d; c1=a+c; hi=min(r1,c1)
    return sum(exp(hyper_logpmf(x,r1,r2,c1)) for x in range(a,hi+1))
def binom_logpmf(k,n,p): return lchoose(n,k)+k*log(p)+(n-k)*log(1-p)
def poisson_rate_test(x1,t1,x2,t2):
    # conditional on x1+x2, x1 ~ Bin(n, t1/(t1+t2)) under equal rates; one-sided P(X>=x1)
    n=x1+x2; p=t1/(t1+t2)
    return sum(exp(binom_logpmf(k,n,p)) for k in range(x1,n+1))
def poisson_logpmf(k,lam): return -lam + k*log(lam) - lgamma(k+1) if lam>0 else (0.0 if k==0 else -math.inf)
def poisson_sf(k,lam):  # P(X>=k)
    return 1-sum(exp(poisson_logpmf(i,lam)) for i in range(k))
def rank(vals):
    s=sorted((v,i) for i,v in enumerate(vals)); r=[0]*len(vals); i=0
    while i<len(s):
        j=i
        while j+1<len(s) and s[j+1][0]==s[i][0]: j+=1
        for k in range(i,j+1): r[s[k][1]]=(i+j)/2+1
        i=j+1
    return r
def mw_exact(x,y):
    # exact permutation test on rank sums (ties handled by midranks), x = group of interest, H1: x smaller
    allv=x+y; r=rank(allv); n=len(x); idx=range(len(allv))
    obs=sum(r[i] for i in range(n))
    cnt_le=0; cnt_ge=0; tot=0
    for comb in itertools.combinations(idx,n):
        s=sum(r[i] for i in comb); tot+=1
        if s<=obs+1e-9: cnt_le+=1
        if s>=obs-1e-9: cnt_ge+=1
    return obs, cnt_le/tot, min(1.0, 2*min(cnt_le,cnt_ge)/tot), tot
def spearman(x,y):
    rx=rank(x); ry=rank(y); return pearson(rx,ry)
def pearson(x,y):
    n=len(x); mx=sum(x)/n; my=sum(y)/n
    sxy=sum((a-mx)*(b-my) for a,b in zip(x,y)); sxx=sum((a-mx)**2 for a in x); syy=sum((b-my)**2 for b in y)
    return sxy/math.sqrt(sxx*syy), sxy/sxx
def perm_p_corr(x,y,stat):
    # exact permutation p (two-sided) for correlation with small n
    n=len(x); obs=stat(x,y)[0]; cnt=0; tot=0
    for p in itertools.permutations(y):
        tot+=1
        if abs(stat(x,list(p))[0])>=abs(obs)-1e-12: cnt+=1
    return cnt/tot
def t_p_two_sided_df(r,n):
    # Student t two-sided via regularized incomplete beta (simple numeric integration)
    if abs(r)>=1: return 0.0
    t=abs(r)*math.sqrt((n-2)/(1-r*r)); df=n-2
    # p = I_{df/(df+t^2)}(df/2, 1/2)
    x=df/(df+t*t); a=df/2; b=0.5
    # numeric integration of incomplete beta
    N=200000; h=x/N; s=0.0
    for i in range(1,N):
        u=i*h; s+=u**(a-1)*(1-u)**(b-1)
    # endpoints: u=0 singular if a<1; a>=1 here (df>=2) ; u=x fine
    s+= 0.5*(x**(a-1)*(1-x)**(b-1)); s*=h
    B=exp(lgamma(a)+lgamma(b)-lgamma(a+b))
    return s/B

print("=== sync vs writer, frames as unit ===")
W=[(69,1,4506),(70,34,4469),(71,153,4349),(72,71,4430)]
S=[(74,0,4505),(75,0,4509),(78,25,14998)]
S80=S+[(80,0,15025)]
def tot(l): return sum(x[1] for x in l), sum(x[1]+x[2] for x in l)
wl,wn=tot(W); sl,sn=tot(S); sl2,sn2=tot(S80)
print("writer lost/frames", wl, wn, "%.3f%%"%(100*wl/wn))
print("sync   lost/frames", sl, sn, "%.3f%%"%(100*sl/sn))
print("sync+80 lost/frames", sl2, sn2, "%.3f%%"%(100*sl2/sn2))
print("Fisher two-sided (W vs S):", fisher_two_sided(wl,wn-wl,sl,sn-sl))
print("Fisher one-sided W>S:", fisher_one_sided_greater(wl,wn-wl,sl,sn-sl))
print("Poisson conditional one-sided (W vs S):", poisson_rate_test(wl,wn,sl,sn))
print("Fisher two-sided (W vs S+80):", fisher_two_sided(wl,wn-wl,sl2,sn2-sl2))
print("Poisson conditional one-sided (W vs S+80):", poisson_rate_test(wl,wn,sl2,sn2))
rr=(wl/wn)/(sl/sn); print("rate ratio W/S = %.1f"%rr)
# log rate ratio CI
se=math.sqrt(1/wl+1/sl); print("  95%% CI rate ratio: %.1f .. %.1f"%(exp(log(rr)-1.96*se),exp(log(rr)+1.96*se)))
rr2=(wl/wn)/(sl2/sn2); se2=math.sqrt(1/wl+1/sl2); print("rate ratio W/(S+80) = %.1f, CI %.1f..%.1f"%(rr2,exp(log(rr2)-1.96*se2),exp(log(rr2)+1.96*se2)))

print("\n=== overdispersion within writer takes (per 3 min) ===")
wc=[x[1] for x in W]; m=sum(wc)/4; v=sum((c-m)**2 for c in wc)/3
print("writer counts", wc, "mean %.1f var %.1f sd %.1f dispersion var/mean %.1f"%(m,v,math.sqrt(v),v/m))
# per-3-min normalized
def per3(l): return [x[1]*4500/(x[1]+x[2]) for x in l]
print("writer per 4500:", ["%.1f"%c for c in per3(W)])
print("sync per 4500:", ["%.1f"%c for c in per3(S80)])
# chance of <=1 in a writer take if Poisson with mean m
print("P(X<=1 | Poisson(%.1f)) = %.2e  (take 69 is impossible under homogeneous Poisson)"%(m, sum(exp(poisson_logpmf(k,m)) for k in range(2))))
# Negative binomial fit by moments for writer: mean m, var v -> size k = m^2/(v-m)
k=m*m/(v-m); print("NB moments: size k=%.3f"%k)
def nb_pmf(x,mu,k): return exp(lgamma(x+k)-lgamma(k)-lgamma(x+1)+k*log(k/(k+mu))+x*log(mu/(k+mu)))
p0=nb_pmf(0,m,k); p1=nb_pmf(1,m,k)
print("NB P(0)=%.3f P(<=1)=%.3f; P(two 3-min takes both 0)=%.3f; P(0,0 and a 10-min take <=25 i.e. <=7.5/3min)"%(p0,p0+p1,p0*p0))
p_le25_10min = sum(nb_pmf(x, m*15023/4500, k) for x in range(26))
print("  NB(10-min, mu=%.1f) P(X<=25)=%.3f ; joint P=%.4f"%(m*15023/4500,p_le25_10min,p0*p0*p_le25_10min))

print("\n=== take-level rank test (exact Mann-Whitney permutation), lost %% per take ===")
wpct=[100*x[1]/(x[1]+x[2]) for x in W]; spct=[100*x[1]/(x[1]+x[2]) for x in S]; spct80=[100*x[1]/(x[1]+x[2]) for x in S80]
print("writer %", ["%.2f"%p for p in wpct]); print("sync %", ["%.2f"%p for p in spct80])
obs,p1,p2,tot_=mw_exact(spct,wpct); print("S(3) vs W(4): rank sum sync=%.1f one-sided p=%.3f two-sided p=%.3f (of %d arrangements)"%(obs,p1,p2,tot_))
obs,p1,p2,tot_=mw_exact(spct80,wpct); print("S+80(4) vs W(4): rank sum sync=%.1f one-sided p=%.3f two-sided p=%.3f (of %d)"%(obs,p1,p2,tot_))
# minimum achievable two-sided p for complete separation
for a,b in [(3,3),(3,4),(4,4),(5,5),(6,6),(4,6)]:
    print("  complete separation %d vs %d: one-sided p=%.4f two-sided p=%.4f"%(a,b,1/math.comb(a+b,a),2/math.comb(a+b,a)))

print("\n=== uptime drift within writer takes after reboot ===")
up=[1,5,9,13]; lost=[1,34,153,71]
r,slope=pearson(up,lost); print("Pearson r=%.3f slope=%.1f lost/min-of-uptime per 3-min take; t-test p=%.3f; exact perm p=%.3f"%(r,slope,t_p_two_sided_df(r,4),perm_p_corr(up,lost,pearson)))
rs,_=spearman(up,lost); print("Spearman rho=%.3f exact perm p(two-sided)=%.3f"%(rs,perm_p_corr(up,lost,spearman)))

print("\n=== first boot (18:55), baseline-equivalent takes: lost%% vs clock minutes since 18:55 ===")
# (take, hh:mm, lost%, comparability)
fb=[(3,"19:09",6.97,"strict"),(15,"19:46",7.56,"strict"),(20,"20:01",5.33,"loose: HDMI out, UI drawing"),(22,"20:04",6.16,"loose: RT prio, no effect"),
    (28,"20:18",8.71,"loose: swapinterval ignored"),(29,"20:20",6.35,"loose: swapinterval ignored"),(34,"20:41",8.83,"loose: fast peaking, no gain"),
    (38,"20:55",8.90,"loose: audio meter off"),(39,"20:58",5.42,"loose: no-op switch"),(41,"21:03",10.60,"loose: 12 cam buffers, no effect"),
    (62,"22:10",18.13,"loose: v3d IRQs on CPU2"),(64,"22:15",11.10,"strict"),(65,"22:19",17.15,"strict")]
def mins(s): h,m=s.split(":"); return (int(h)-18)*60+int(m)-55
x=[mins(t[1]) for t in fb]; y=[t[2] for t in fb]
r,slope=pearson(x,y); print("all 13: Pearson r=%.3f slope=%.3f %%/min (= %.2f %%/h) t p=%.4f"%(r,slope,slope*60,t_p_two_sided_df(r,len(x))))
rs,_=spearman(x,y); print("all 13: Spearman rho=%.3f"%rs)
xs=[mins(t[1]) for t in fb if t[3]=="strict"]; ys=[t[2] for t in fb if t[3]=="strict"]
r,slope=pearson(xs,ys); print("strict 4 (#3,#15,#64,#65): r=%.3f slope=%.2f %%/h, exact perm p=%.3f"%(r,slope*60,perm_p_corr(xs,ys,pearson)))
# before 21:10 only
xb=[a for a,t in zip(x,fb) if a<140]; yb=[b for b,t in zip(y,fb) if mins(t[1])<140]
r,slope=pearson(xb,yb); print("19:09-21:03 only (n=%d): r=%.3f slope=%.2f %%/h t p=%.3f"%(len(xb),r,slope*60,t_p_two_sided_df(r,len(xb))))
print("mean 19:09-21:03: %.2f%%  mean 22:10-22:19: %.2f%%"%(sum(yb)/len(yb), sum(y[-3:])/3))
# UI-stopped controls
print("UI stopped controls (writer): #5 19:13 0/1500, #17 19:51 0/749, #59 22:00 2/1495 (0.13%)")

print("\n=== take 78 per-minute ===")
cum=[0,0,3,3,3,3,5,5,7,25]; inc=[cum[0]]+[cum[i]-cum[i-1] for i in range(1,10)]
print("increments:", inc)
lam9=sum(inc[:9])/9; print("rate minutes 1-9: %.2f/min; P(X>=18 | Poisson(%.2f)) = %.2e"%(lam9,lam9,poisson_sf(18,lam9)))
lam10=25/10; print("homogeneous rate 2.5/min: P(max of 10 minutes >= 18) ~ %.2e"%(1-(1-poisson_sf(18,lam10))**10))
# first 9 minutes trend?
mn=list(range(1,10)); rs,_=spearman(mn,inc[:9]); r,slope=pearson(mn,inc[:9]); print("minutes 1-9: Spearman rho=%.3f Pearson r=%.3f slope %.2f/min, perm p=%.3f"%(rs,r,slope,perm_p_corr(mn,inc[:9],pearson)))
# fill per minute (assume 70% at start, +2.68%/min)
fps=25*60; fsz=16.6e6; drive=932e9
pm=fps*fsz/drive*100; print("fill per minute of take: %.2f %% of 932 GB (at 16.6 MB/frame)"%pm)
for f0 in (70,):
    print(" minute: fill-at-end  lost")
    for i in range(10): print("   %2d   %5.1f%%   %d"%(i+1,f0+pm*(i+1),inc[i]))

print("\n=== drive fill reconstruction (16.6 MB/frame HDR16 4K, lossless ~half, 1080p quarter, COMP1 12-bit ~0.75) ===")
takes_first=[(2,412,'ll'),(3,1389,'h'),(4,1357,'h'),(5,1500,'h'),(6,1237,'h'),(7,921,'h'),(11,478,'h'),(12,920,'c'),(15,1381,'h'),(16,679,'h'),(17,749,'h'),(18,750,'h'),(19,1500,'q'),(20,1367,'h'),(22,1402,'h'),(23,2440,'c'),(25,1114,'c'),(26,151,'c'),(27,1450,'h'),(28,1363,'h'),(29,1400,'h'),(30,1498,'h'),(31,1452,'h'),(32,1470,'h'),(33,1337,'h'),(34,1363,'h'),(35,531,'h'),(36,533,'h'),(37,1251,'h'),(38,1362,'h'),(39,1413,'h'),(41,1332,'h'),(44,1437,'h'),(45,185,'c'),(46,1500,'h'),(47,1190,'h'),(48,2688,'h'),(49,4362,'h'),(50,4348,'h')]
w={'h':16.6e6,'ll':8e6,'c':12.4e6,'q':4.15e6}
cum=0
print("first boot, before the 21:50 format (start fill unknown):")
for t,n,k in takes_first:
    cum+=n*w[k]
    if t in (3,15,41,46,50): print("  after #%d: %.0f GB written since 18:55 (%.0f%% of 932 if drive was empty at 18:55)"%(t,cum/1e9,100*cum/932e9))
takes_second=[(52,404,'h'),(53,95,'h'),(54,180,'ll'),(55,100,'ll'),(56,50,'h'),(57,51,'h'),(58,4179,'h'),(59,1493,'h'),(60,540,'h'),(61,3858,'h'),(62,3686,'h'),(64,4003,'h'),(65,1237,'h'),(66,52,'ll'),(67,79,'ll'),(69,4506,'h'),(70,4469,'h'),(71,4349,'h'),(72,4430,'h'),(74,4505,'h'),(75,4509,'h'),(76,665,'h'),(77,812,'c'),(78,14998,'h')]
cum=0; print("after the 21:50 format (pre-rolls deleted, not counted):")
for t,n,k in takes_second:
    before=cum; cum+=n*w[k]
    if t in (58,61,62,64,65,69,70,71,72,74,75,78): print("  #%d: start %.0f GB (%.0f%%) -> end %.0f GB (%.0f%%)"%(t,before/1e9,100*before/932e9,cum/1e9,100*cum/932e9))
print("  reported: 97%% at the end of #78 = %.0f GB -> start of #78 ~ %.0f GB (%.0f%%); the no-deletion sum is %.0f GB higher: clips were deleted or the figure is approximate"%(0.97*932, 0.97*932-14998*16.6e-3, 100*(0.97*932-14998*16.6e-3)/932, (cum-0.97*932e9)/1e9))

print("\n=== power ===")
for p in (5e-4,2e-4,1e-4):
    n=log(0.05)/log(1-p); print("0 events bounds rate < %.2f%% at 95%%: n=%.0f frames = %.1f min at 25 fps (rule of three: %.0f)"%(100*p,n,n/1500,3/p))
def n_two_prop(p1,p2,alpha=0.05,power=0.8):
    za={0.05:1.95996}[alpha]; zb={0.8:0.84162,0.9:1.28155}[power]; pb=(p1+p2)/2
    return (za*math.sqrt(2*pb*(1-pb))+zb*math.sqrt(p1*(1-p1)+p2*(1-p2)))**2/(p1-p2)**2
for pw in (0.8,0.9):
    n=n_two_prop(0.0017,0.0005,power=pw); print("0.17%% vs 0.05%%, power %.0f%%: %.0f frames per arm = %.1f min per arm (independent frames)"%(100*pw,n,n/1500))
    n=n_two_prop(0.0017,0.0,power=pw) if False else None
# Poisson exact: expected events: 10-min take at 0.17% = 25.5 events, at 0.05% = 7.5 events
print("10-min take: expected events 0.17%% -> %.1f ; 0.05%% -> %.1f ; 3-min take: %.1f / %.1f"%(0.0017*15000,0.0005*15000,0.0017*4500,0.0005*4500))
# P(observe <=7 | 25.5) and P(>=25 | 7.5)
print("P(X<=12 | 25.5)=%.4f  P(X>=13 | 7.5)=%.4f  (threshold 12.5 separates them with ~%.0f%% / %.0f%% error in ONE 10-min take)"%(1-poisson_sf(13,25.5),poisson_sf(13,7.5),100*(1-poisson_sf(13,25.5)),100*poisson_sf(13,7.5)))
print("3-min take: P(X<=3 | 7.65)=%.3f P(X>=4 | 2.25)=%.3f"%(1-poisson_sf(4,7.65),poisson_sf(4,2.25)))
# writer vs sync at the observed rates: 1.44% vs 0.10%: expected per 3-min take 65 vs 4.7
print("writer vs sync at observed rates per 3-min take: %.1f vs %.1f ; per 10 min %.0f vs %.0f"%(0.0144*4500,0.00104*4500,0.0144*15000,0.00104*15000))
# with overdispersion: effective sample size. Writer NB k~1 -> design on take-level.
print("\nwall clock: per 10-min take = setup 0.7 + record 10 + stop/stats 0.3 + delete+fstrim 1.5 + Core restart & preroll 0.5 + cool-down 2 = ~15 min; 8 takes = ~2 h; 3-min takes: ~8 min each, 8 takes = ~65 min")
