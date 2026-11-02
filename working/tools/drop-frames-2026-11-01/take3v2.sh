# take3v2.sh [seconds]: take3.sh plus per-minute reclaim deltas (M2 of night-2026-11-01.md section 8).
# One take at 4K Clear HDR 16-bit 25 fps uncompressed; every minute: lost so far, and the minute's deltas of
# pgsteal_kswapd pgsteal_direct pgscan_direct allocstall_normal allocstall_movable kswapd_low_wmark_hit_quickly,
# plus MemFree/Cached/Dirty; before and after: /proc/meminfo, /proc/pressure/memory (if psi=1), compaction deltas.
# Copy to the Pi as /tmp/take3v2.sh; run with nothing else on the Pi and the WebUI closed. Patrik's ladder is restored at the end.
SECS=${1:-180}
C="python3 -I $HOME/apertar-kb/working/tools/core.py"
D(){ $C get_state | python3 -c "import sys,json; print(json.load(sys.stdin).get('recording_dropped_frames'))"; }
KEYS="pgsteal_kswapd pgsteal_direct pgscan_kswapd pgscan_direct pgscan_direct_throttle allocstall_normal allocstall_movable kswapd_low_wmark_hit_quickly kswapd_high_wmark_hit_quickly pageoutrun pswpin pswpout compact_isolated pgmigrate_success compact_daemon_wake"
S(){ awk -v keys="$KEYS" 'BEGIN{n=split(keys,k," "); for(i=1;i<=n;i++) want[k[i]]=1} ($1 in want){printf "%s=%s ", $1, $2}' /proc/vmstat; }
M(){ grep -E "^(MemFree|MemAvailable|Cached|Dirty|Writeback|Slab|SReclaimable):" /proc/meminfo | awk '{printf "%s%dM ", $1, $2/1024}'; }
P(){ [ -r /proc/pressure/memory ] && tr '\n' ' ' < /proc/pressure/memory || echo "psi off"; }
DELTA(){ python3 -c "import sys; p=lambda s: dict(x.split('=') for x in s.split()); a,b=p(sys.argv[1]),p(sys.argv[2]); print(' '.join(f'{k}=+{int(b[k])-int(a[k])}' for k in a))" "$1" "$2"; }
UP=$(pgrep -f "^/home/pi/ApertarUI/build/Apertar-UI" | head -1)
echo "core knobs: $(tr '\0' '\n' < /proc/$(pgrep -f apertar-core | head -1)/environ 2>/dev/null | grep -E '^APERTAR_(DNG_DONTNEED|MEDIA_SYNC_MS|DNG_WRITEBACK|RAW_CAMERA_BUFFERS|MEDIA_TUNE|RT_CAPTURE_PRIORITY|CDNG_BUFFER)=' | tr '\n' ' ')"
echo "sysctl: dirty_bytes=$(cat /proc/sys/vm/dirty_bytes) dirty_background_bytes=$(cat /proc/sys/vm/dirty_background_bytes) dirty_ratio=$(cat /proc/sys/vm/dirty_ratio) min_free_kbytes=$(cat /proc/sys/vm/min_free_kbytes)"
echo "ui=$(systemctl is-active apertar-ui-direct) switches: $(tr '\0' '\n' < /proc/$UP/environ 2>/dev/null | grep -E '^APERTAR_PREVIEW|^APERTAR_UI_PREVIEW|^QSG_RENDER_TIMING' | tr '\n' ' ')"
echo "aids: $(grep -E '^(focusPeakingEnabled|zebraEnabled|audioMeterEnabled)=' ~/.config/CinePi/UI.conf | tr '\n' ' ')"
echo "pagesize=$(getconf PAGESIZE) buddy: $(awk '{printf "%s:%s ", $4, $NF}' /proc/buddyinfo)"
echo "rss: core=$(grep VmRSS /proc/$(pgrep -f apertar-core | head -1)/status 2>/dev/null | awk '{print $2/1024"M"}') ui=$(grep VmRSS /proc/$UP/status 2>/dev/null | awk '{print $2/1024"M"}') swap: core=$(grep VmSwap /proc/$(pgrep -f apertar-core | head -1)/status 2>/dev/null | awk '{print $2/1024"M"}') ui=$(grep VmSwap /proc/$UP/status 2>/dev/null | awk '{print $2/1024"M"}')"
echo "drive: $(df -h /media/RAW | awk 'NR==2{printf "%s used of %s (%s)", $3, $2, $5}') nvme=$(cat /sys/class/nvme/nvme0/state 2>/dev/null) $(cat /sys/class/nvme/nvme0/device/hwmon*/temp1_input 2>/dev/null | awk '{printf "%d C", $1/1000}')"
$C set_mode_ladder enabled=false >/dev/null; sleep 3; $C set_fps value=25 >/dev/null; sleep 4
$C set_clear_hdr enabled=true >/dev/null; sleep 5; $C set_raw_bit_depth value=16 >/dev/null; sleep 4
$C set_cdng_compression value=none >/dev/null; sleep 5
c=$(ss -tnH state established "( sport = :8000 )" | wc -l)
echo "start $(date +%T) clients=$c builds=$(ps -eo cmd | grep -cE '^[^ ]*(cc1plus|gmake|cmake) ') $(vcgencmd measure_temp) up=$(uptime -p)"
[ "$c" -gt 0 ] && { echo "WebUI connected, not starting"; exit 0; }
echo "  mem before: $(M)"; echo "  psi before: $(P)"
a=$(S); prev=$a; T1=$(date '+%F %T'); $C record_start >/dev/null
t=0; while [ $t -lt $SECS ]; do s=$(( SECS - t < 60 ? SECS - t : 60 )); sleep $s; t=$((t+s)); cur=$(S)
  echo "  ${t}s $(date +%T): dropped=$(D) clients=$(ss -tnH state established "( sport = :8000 )" | wc -l) $(grep -E '^(MemFree|Cached|Dirty):' /proc/meminfo | awk '{printf "%s%dM ", $1, $2/1024}')"
  echo "    minute deltas: $(DELTA "$prev" "$cur" | tr ' ' '\n' | grep -E '^(pgsteal_kswapd|pgsteal_direct|pgscan_direct|pgscan_direct_throttle|allocstall_normal|allocstall_movable|kswapd_low_wmark_hit_quickly|pswpin|pswpout)=' | tr '\n' ' ')"; prev=$cur; done
$C record_stop >/dev/null; sleep 8; b=$(S); echo "  mem after: $(M)"; echo "  psi after: $(P)"
journalctl -u apertar-core --since "$T1" --no-pager | grep -oE "dropped_gap_estimate=[0-9]+|enqueued=[0-9]+|dropped_queue_full=[0-9]+|dropped_copy_slot=[0-9]+|peak_queue=[0-9/]+|synced to the medium in [0-9]+ ms" | tr '\n' ' '; echo
echo "  whole take: $(DELTA "$a" "$b")"
$C set_mode_ladder enabled=true >/dev/null; sleep 4; $C set_fps value=30 >/dev/null; sleep 4; echo restored
