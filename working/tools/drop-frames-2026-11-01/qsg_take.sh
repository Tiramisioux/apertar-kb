C="python3 -I $HOME/apertar-kb/working/tools/core.py"
$C set_mode_ladder enabled=false >/dev/null; sleep 3; $C set_fps value=25 >/dev/null; sleep 4
$C set_clear_hdr enabled=true >/dev/null; sleep 5; $C set_raw_bit_depth value=16 >/dev/null; sleep 4
$C set_cdng_compression value=none >/dev/null; sleep 5
echo "aids: $(grep -E '^(focusPeakingEnabled|zebraEnabled)=' ~/.config/CinePi/UI.conf | tr '\n' ' ')"
$C record_start >/dev/null; sleep 4; T1=$(date '+%F %T'); sleep 20; T2=$(date '+%F %T'); $C record_stop >/dev/null; sleep 4
journalctl -u apertar-ui-direct --since "$T1" --until "$T2" --no-pager -o cat | python3 -c '
import sys,re,statistics as st
fr=[];rd=[];sw=[];dl=[]
for l in sys.stdin:
    m=re.search(r"frame rendered in (\d+)ms, polish=(\d+), sync=(\d+), render=(\d+), swap=(\d+), perWindowFrameDelta=(\d+)",l)
    if m:
        a=list(map(int,m.groups())); fr.append(a[0]); rd.append(a[3]); sw.append(a[4]); dl.append(a[5])
n=len(fr)
if n:
    q=lambda v:(round(st.mean(v),1), sorted(v)[int(0.95*(n-1))], max(v))
    print(f"frames={n} in 20 s = {n/20:.1f}/s; total ms mean/p95/max={q(fr)} render={q(rd)} swap={q(sw)} delta={q(dl)}")
    big=[x for x in fr if x>=20]; print("frames >=20 ms:", len(big), sorted(big)[-8:])
'
journalctl -u apertar-core --since "-40s" --no-pager | grep -oE "dropped_gap_estimate=[0-9]+|enqueued=[0-9]+" | tr '\n' ' '; echo
$C set_mode_ladder enabled=true >/dev/null; sleep 4; $C set_fps value=30 >/dev/null; sleep 4; echo restored
