#!/bin/bash
# 10 s take with counters: take.sh [reconfigure]   (reconfigure = 12 -> 16 first)
S=$(dirname "$0")
P=$(pgrep -x apertar-core | head -1)
if [ "$1" = reconfigure ]; then
    python3 -I $S/core.py set_raw_bit_depth value=12 >/dev/null; python3 -c 'import time; time.sleep(5)'
    python3 -I $S/core.py set_raw_bit_depth value=16 >/dev/null; python3 -c 'import time; time.sleep(6)'
fi
TID=$(for t in /proc/$P/task/*; do [ "$(cat $t/comm)" = CameraManager ] && echo "$(awk '{print $14+$15}' $t/stat) ${t##*/}"; done | sort -rn | head -1 | cut -d' ' -f2)
vm() { awk '/^(allocstall_normal|allocstall_movable|pgscan_direct|pgsteal_direct|compact_stall|pgmajfault) /{printf "%s=%s ", $1, $2}' /proc/vmstat; }
th() { awk '{printf "minflt=%s majflt=%s utime=%s stime=%s", $10, $12, $14, $15}' /proc/$P/task/$TID/stat; }
echo "before: $(th) | $(vm)"
echo "temp=$(cat /sys/class/thermal/thermal_zone0/temp) freq=$(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq) mem_free=$(awk '/MemFree/{print $2}' /proc/meminfo)kB"
T1=$(date '+%F %T')
python3 -I $S/core.py record_start >/dev/null
( for i in $(seq 1 10); do echo -n "$(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq)/$(cat /sys/class/thermal/thermal_zone0/temp)/$(awk '/MemFree/{print int($2/1024)}' /proc/meminfo)M "; python3 -c 'import time; time.sleep(1)'; done; echo )
python3 -I $S/core.py record_stop >/dev/null
T2=$(date '+%F %T')
echo "after:  $(th) | $(vm)"
python3 -c 'import time; time.sleep(5)'
python3 -I $S/ipa_rate.py "$T1" "$T2" | head -1
journalctl -u apertar-core --since "$T1" --no-pager | grep -E 'recording clip|capture stats|recording stats' | sed -E 's/.*ApertarCore //'
