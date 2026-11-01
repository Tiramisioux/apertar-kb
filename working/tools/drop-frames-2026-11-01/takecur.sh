# takecur.sh [seconds]: one take in the camera's CURRENT settings (no mode changes, no restore); per-minute counts.
SECS=${1:-600}
C="python3 -I $HOME/apertar-kb/working/tools/core.py"
D(){ $C get_state | python3 -c "import sys,json; print(json.load(sys.stdin).get('recording_dropped_frames'))"; }
S(){ grep -E "^(pgsteal_kswapd|kswapd_low_wmark_hit_quickly|compact_daemon_wake)" /proc/vmstat | awk '{printf "%s=%s ", $1, $2}'; }
echo "mode: $($C get_state | python3 -c "import sys,json; s=json.load(sys.stdin); print(s.get('ladder_text'), s.get('fps'), s.get('cdng_compression'), 'log', s.get('cdng_log'), 'buffer', s.get('buffer_setting'))")"
echo "core env: $(systemctl show apertar-core -p Environment --value)"
echo "aids: $(grep -E '^(focusPeakingEnabled|zebraEnabled|audioMeterEnabled)=' ~/.config/CinePi/UI.conf | tr '\n' ' ')"
c=$(ss -tnH state established "( sport = :8000 )" | wc -l)
echo "start $(date +%T) clients=$c builds=$(ps -eo cmd | grep -cE '^[^ ]*(cc1plus|gmake|cmake) ') $(vcgencmd measure_temp) up=$(uptime -p)"
[ "$c" -gt 0 ] && { echo "WebUI connected, not starting"; exit 0; }
echo "  mem before: $(grep -E '^(MemFree|Cached):' /proc/meminfo | awk '{printf "%s%dM ", $1, $2/1024}')"
a=$(S); T1=$(date '+%F %T'); $C record_start >/dev/null
t=0; while [ $t -lt $SECS ]; do s=$(( SECS - t < 60 ? SECS - t : 60 )); sleep $s; t=$((t+s)); r=$($C get_state | python3 -c "import sys,json; s=json.load(sys.stdin); print(s.get('recording'), s.get('recording_dropped_frames'), s.get('buffer_fill'))"); echo "  ${t}s $(date +%T): recording/dropped/buffer=$r clients=$(ss -tnH state established "( sport = :8000 )" | wc -l)"; done
$C record_stop >/dev/null; sleep 10; b=$(S)
journalctl -u apertar-core --since "$T1" --no-pager | grep -E "capture stats|recording stats|lossless timing|safety stop" | grep -oE "dropped_gap_estimate=[0-9]+|enqueued=[0-9]+|dropped_queue_full=[0-9]+|peak_queue=[0-9/]+|estimated_capacity_fps=[0-9.]+|safety stop[^)]*\)" | tr '\n' ' '; echo
echo "  mem after: $(grep -E '^(MemFree|Cached):' /proc/meminfo | awk '{printf "%s%dM ", $1, $2/1024}')"
python3 -c "import sys; p=lambda s: dict(x.split('=') for x in s.split()); a,b=p(sys.argv[1]),p(sys.argv[2]); print('  during take:', ' '.join(f'{k}=+{int(b[k])-int(a[k])}' for k in a))" "$a" "$b"
