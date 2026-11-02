# take3v3.sh [seconds] [label]: one take at 4K Clear HDR 16-bit 25 fps uncompressed, unprivileged, with the readings
# section 8.3 B0 step 5 of night-2026-11-01.md asks for (inspection-2026-11-02.md has the full plan).
#
# What it adds to take3v2.sh:
#   - KEYS gains allocstall_dma/dma32, compact_stall/fail/success, cma_alloc_success/fail, pgmajfault, workingset_*.
#   - Before the take: MemFree Cached MemAvailable Slab SReclaimable SUnreclaim Buffers, VmRSS/VmSwap of Core and UI,
#     df, uptime in seconds, SoC and NVMe temperature, get_throttled, the arm (APERTAR_DNG_DONTNEED etc.) read from
#     Core's MainPID environment, per-zone boost, the Orphanded count in the kernel log.
#   - A 1 Hz logger in one process (take_logger.py, next to this script) to /dev/shm/take-<label>.log (never /media/RAW):
#     KEYS, MemFree/Dirty/Writeback, NVMe write count and ticks (fields 5 and 8 of /sys/block/nvme0n1/stat), PSI if on,
#     recording_dropped_frames, and M5: schedstat run/wait ns and majflt for every Core thread and the UI's threads.
#   - G1: hwcount.py on libcamera's CameraManager thread for 60 s, starting 60 s into the take (user-space PMU, no sudo).
#
# It needs no sudo and deletes nothing: deleting the take's own clip folder and the trim are steps of the reviewed root
# script for the arm (b1-arm.sh in the plan), never a cDNG_* glob. Nothing else may run on the Pi during the take, and the
# WebUI must be closed (the script refuses otherwise). Patrik's ladder is restored at the end.
SECS=${1:-180}
LABEL=${2:-$(date +%H%M%S)}
LOG=/dev/shm/take-$LABEL.log
KB=$HOME/apertar-kb/working/tools
C="python3 -I $KB/core.py"
D(){ $C get_state | python3 -c "import sys,json; print(json.load(sys.stdin).get('recording_dropped_frames'))"; }
KEYS="pgsteal_kswapd pgsteal_direct pgscan_kswapd pgscan_direct pgscan_direct_throttle allocstall_dma allocstall_dma32 allocstall_normal allocstall_movable kswapd_low_wmark_hit_quickly kswapd_high_wmark_hit_quickly pageoutrun pswpin pswpout pgmajfault workingset_refault_file workingset_refault_anon workingset_activate_file compact_stall compact_fail compact_success compact_isolated pgmigrate_success compact_daemon_wake cma_alloc_success cma_alloc_fail"
S(){ awk -v keys="$KEYS" 'BEGIN{n=split(keys,k," "); for(i=1;i<=n;i++) want[k[i]]=1} ($1 in want){printf "%s=%s ", $1, $2}' /proc/vmstat; }
M(){ grep -E "^(MemFree|MemAvailable|Cached|Buffers|Dirty|Writeback|Slab|SReclaimable|SUnreclaim):" /proc/meminfo | awk '{printf "%s%dM ", $1, $2/1024}'; }
P(){ [ -r /proc/pressure/memory ] && tr '\n' ' ' < /proc/pressure/memory || echo "psi off"; }
DELTA(){ python3 -c "import sys; p=lambda s: dict(x.split('=') for x in s.split()); a,b=p(sys.argv[1]),p(sys.argv[2]); print(' '.join(f'{k}=+{int(b[k])-int(a[k])}' for k in a if k in b))" "$1" "$2"; }
CORE=$(systemctl show -p MainPID --value apertar-core)
UP=$(systemctl show -p MainPID --value apertar-ui-direct)
[ "${CORE:-0}" -gt 0 ] || { echo "apertar-core is not running"; exit 1; }
VM(){ grep -E "^(VmRSS|VmSwap):" /proc/$1/status 2>/dev/null | awk '{printf "%s%dM ", $1, $2/1024}'; }
# Core has several threads named CameraManager, and a mode change replaces them (G1 found its tid gone, 2026-11-02):
# pick libcamera's, the one with the most run time over 2 s, right before record_start
CAMPICK(){ for t in $(ps -L -o tid=,comm= -p "$CORE" | awk '$2=="CameraManager"{print $1}'); do echo "$t $(cut -d' ' -f1 /proc/$CORE/task/$t/schedstat 2>/dev/null || echo 0)"; done > /dev/shm/campick.$$; sleep 2
  while read -r t r0; do echo "$t $(( $(cut -d' ' -f1 /proc/$CORE/task/$t/schedstat 2>/dev/null || echo $r0) - r0 ))"; done < /dev/shm/campick.$$ | sort -k2,2nr | awk 'NR==1{print $1}'; rm -f /dev/shm/campick.$$; }
CAM=$(CAMPICK)
echo "label=$LABEL core=$CORE ui=$UP camtid=${CAM:-none} pagesize=$(getconf PAGESIZE) uptime_s=$(cut -d. -f1 /proc/uptime)"
echo "core knobs: $(tr '\0' '\n' < /proc/$CORE/environ 2>/dev/null | grep -E '^APERTAR_(DNG_DONTNEED|MEDIA_SYNC_MS|DNG_WRITEBACK|RAW_CAMERA_BUFFERS|MEDIA_TUNE|RT_CAPTURE_PRIORITY|CDNG_BUFFER)=' | tr '\n' ' ')"
echo "sysctl: dirty_bytes=$(cat /proc/sys/vm/dirty_bytes) dirty_background_bytes=$(cat /proc/sys/vm/dirty_background_bytes) dirty_ratio=$(cat /proc/sys/vm/dirty_ratio) min_free_kbytes=$(cat /proc/sys/vm/min_free_kbytes) watermark_boost_factor=$(cat /proc/sys/vm/watermark_boost_factor)"
echo "ui switches: $(tr '\0' '\n' < /proc/$UP/environ 2>/dev/null | grep -E '^APERTAR_PREVIEW|^APERTAR_UI_PREVIEW|^QSG_RENDER_TIMING' | tr '\n' ' ')"
echo "aids: $(grep -E '^(focusPeakingEnabled|zebraEnabled|audioMeterEnabled)=' ~/.config/CinePi/UI.conf | tr '\n' ' ')"
echo "rss/swap: core $(VM "$CORE") ui $(VM "$UP")"
echo "drive: $(df -h /media/RAW | awk 'NR==2{printf "%s used of %s (%s)", $3, $2, $5}') nvme=$(cat /sys/class/nvme/nvme0/state 2>/dev/null) $(cat /sys/class/nvme/nvme0/hwmon*/temp1_input 2>/dev/null | awk '{printf "%d C", $1/1000}') soc=$(vcgencmd measure_temp) $(vcgencmd get_throttled)"
echo "zone boost: $(awk '/^Node/{n=$2; z=$4} /^ +boost/{printf "n%sz%s=%s ", n, z, $2}' /proc/zoneinfo)"
echo "kernel log Orphanded lines this boot: $(journalctl -k -b --no-pager 2>/dev/null | grep -c Orphanded)"
$C set_mode_ladder enabled=false >/dev/null; sleep 3; $C set_fps value=25 >/dev/null; sleep 4
$C set_clear_hdr enabled=true >/dev/null; sleep 5; $C set_raw_bit_depth value=16 >/dev/null; sleep 4
$C set_cdng_compression value=none >/dev/null; sleep 5
c=$(ss -tnH state established "( sport = :8000 )" | wc -l)
b=$(ps -eo cmd | grep -cE '^[^ ]*(cc1plus|gmake|cmake) ')
echo "start $(date +%T) clients=$c builds=$b"
[ "$c" -gt 0 ] && { echo "WebUI connected, not starting"; exit 0; }
[ "$b" -gt 0 ] && { echo "a build is running, not starting"; exit 0; }
CSI(){ f=$(ls /sys/kernel/debug/rp1-cfe*/csi2_errors 2>/dev/null | head -1); [ -n "$f" ] && awk 'NR==1 || /^[0-9] /{printf "%s | ", $0}' "$f" | tr -s ' ' || echo "csi2 n/a"; }
# csi2_errors is cleared on every read (measured 2026-11-02): this read clears it just before the take; during the take
# the 1 Hz logger is its only reader, so each log line holds that second's discards
CAM=$(CAMPICK); echo "  camtid at start: ${CAM:-none}"
echo "  mem before: $(M)"; echo "  psi before: $(P)"; echo "  csi2 since the last read (cleared now): $(CSI)"
# 1 Hz logger (M5 + counters) in one process (take_logger.py), stopped after the take
python3 -I "$KB/drop-frames-2026-11-01/take_logger.py" "$CORE" "${UP:-0}" "$LOG" $KEYS &
LOGGER=$!
a=$(S); prev=$a; T1=$(date '+%F %T'); $C record_start >/dev/null
G1OUT=/dev/shm/take-$LABEL.g1; G1PID=""
t=0; while [ $t -lt $SECS ]; do s=$(( SECS - t < 60 ? SECS - t : 60 )); sleep $s; t=$((t+s)); cur=$(S)
  if [ $t -eq 60 ] && [ -n "$CAM" ] && [ $SECS -gt 120 ]; then
    python3 -I "$KB/hwcount.py" "$CORE" "$CAM" 60 > "$G1OUT" 2>&1 &
    G1PID=$!
  fi
  echo "  ${t}s $(date +%T): dropped=$(D) clients=$(ss -tnH state established "( sport = :8000 )" | wc -l) $(grep -E '^(MemFree|Cached|Dirty):' /proc/meminfo | awk '{printf "%s%dM ", $1, $2/1024}')"
  echo "    minute deltas: $(DELTA "$prev" "$cur" | tr ' ' '\n' | grep -E '^(pgsteal_kswapd|pgsteal_direct|pgscan_direct|pgscan_direct_throttle|allocstall_normal|allocstall_movable|kswapd_low_wmark_hit_quickly|pageoutrun|pgmajfault|pswpin|compact_stall)=' | tr '\n' ' ')"; prev=$cur; done
$C record_stop >/dev/null; sleep 8; kill "$LOGGER" 2>/dev/null; b2=$(S)
echo "  mem after: $(M)"; echo "  psi after: $(P)"
journalctl -u apertar-core --since "$T1" --no-pager | grep -oE "recording clip: [^ ]+|dropped_gap_estimate=[0-9]+|enqueued=[0-9]+|dropped_queue_full=[0-9]+|dropped_copy_slot=[0-9]+|peak_queue=[0-9/]+|queue_budget=[0-9]+|synced to the medium in [0-9]+ ms" | tr '\n' ' '; echo
echo "  whole take: $(DELTA "$a" "$b2")"
echo "  drive after: $(df -h /media/RAW | awk 'NR==2{printf "%s used of %s (%s)", $3, $2, $5}') $(cat /sys/class/nvme/nvme0/hwmon*/temp1_input 2>/dev/null | awk '{printf "%d C", $1/1000}')"
echo "  builds after: $(ps -eo cmd | grep -cE '^[^ ]*(cc1plus|gmake|cmake) ')  1 Hz log: $LOG ($(wc -l < "$LOG") lines)"
if [ -n "$G1PID" ]; then wait "$G1PID" 2>/dev/null; echo "  G1 (CameraManager PMU, 60-120 s): $(cat "$G1OUT")"; fi
$C set_mode_ladder enabled=true >/dev/null; sleep 4; $C set_fps value=30 >/dev/null; sleep 4; echo restored
