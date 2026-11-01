# take3.sh [seconds]: one take at 4K Clear HDR 16-bit 25 fps uncompressed, per-minute counts, compaction deltas, restore.
SECS=${1:-180}
C="python3 -I $HOME/apertar-kb/working/tools/core.py"
D(){ $C get_state | python3 -c "import sys,json; print(json.load(sys.stdin).get('recording_dropped_frames'))"; }
S(){ grep -E "^(compact_isolated|pgmigrate_success|compact_daemon_wake|pgscan_kswapd|pgsteal_kswapd|pgscan_direct|allocstall_normal|allocstall_movable|kswapd_low_wmark_hit_quickly|pageoutrun)" /proc/vmstat | awk '{printf "%s=%s ", $1, $2}'; }
UP=$(pgrep -f "^/home/pi/ApertarUI/build/Apertar-UI" | head -1)
echo "ui=$(systemctl is-active apertar-ui-direct) switches: $(tr '\0' '\n' < /proc/$UP/environ 2>/dev/null | grep -E '^APERTAR_PREVIEW|^APERTAR_UI_PREVIEW|^QSG_RENDER_TIMING' | tr '\n' ' ')"
echo "aids: $(grep -E '^(focusPeakingEnabled|zebraEnabled|audioMeterEnabled)=' ~/.config/CinePi/UI.conf | tr '\n' ' ')"
$C set_mode_ladder enabled=false >/dev/null; sleep 3; $C set_fps value=25 >/dev/null; sleep 4
$C set_clear_hdr enabled=true >/dev/null; sleep 5; $C set_raw_bit_depth value=16 >/dev/null; sleep 4
$C set_cdng_compression value=none >/dev/null; sleep 5
c=$(ss -tnH state established "( sport = :8000 )" | wc -l)
echo "start $(date +%T) clients=$c builds=$(ps -eo cmd | grep -cE '^[^ ]*(cc1plus|gmake|cmake) ') $(vcgencmd measure_temp) up=$(uptime -p)"
[ "$c" -gt 0 ] && { echo "WebUI connected, not starting"; exit 0; }
echo "  mem before: $(grep -E "^(MemFree|Cached|Dirty|Writeback):" /proc/meminfo | awk "{printf \"%s%dM \", \$1, \$2/1024}")"; a=$(S); T1=$(date '+%F %T'); $C record_start >/dev/null
t=0; while [ $t -lt $SECS ]; do s=$(( SECS - t < 60 ? SECS - t : 60 )); sleep $s; t=$((t+s)); echo "  ${t}s $(date +%T): dropped=$(D) clients=$(ss -tnH state established "( sport = :8000 )" | wc -l)"; done
$C record_stop >/dev/null; sleep 8; b=$(S); echo "  mem after: $(grep -E "^(MemFree|Cached|Dirty|Writeback):" /proc/meminfo | awk "{printf \"%s%dM \", \$1, \$2/1024}")"
journalctl -u apertar-core --since "$T1" --no-pager | grep -oE "dropped_gap_estimate=[0-9]+|enqueued=[0-9]+|dropped_queue_full=[0-9]+" | tr '\n' ' '; echo
python3 -c "import sys; p=lambda s: dict(x.split('=') for x in s.split()); a,b=p(sys.argv[1]),p(sys.argv[2]); print('  compaction during take:', ' '.join(f'{k}=+{int(b[k])-int(a[k])}' for k in a))" "$a" "$b"
$C set_mode_ladder enabled=true >/dev/null; sleep 4; $C set_fps value=30 >/dev/null; sleep 4; echo restored
