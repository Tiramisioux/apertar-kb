#!/bin/bash
# Idle delivery check: busiest CameraManager thread CPU (user/sys) and IPA per-frame warnings over 5 s.
PID=$(pgrep -x apertar-core | head -1)
TID=$(for t in /proc/$PID/task/*; do [ "$(cat $t/comm)" = CameraManager ] && echo "$(awk '{print $14+$15}' $t/stat) ${t##*/}"; done | sort -rn | head -1 | cut -d' ' -f2)
S=/proc/$PID/task/$TID/stat
u1=$(awk '{print $14}' $S); s1=$(awk '{print $15}' $S); since=$(date '+%Y-%m-%d %H:%M:%S')
python3 -c 'import time; time.sleep(5)'
u2=$(awk '{print $14}' $S); s2=$(awk '{print $15}' $S)
w=$(journalctl -u apertar-core --since "$since" --no-pager | grep -c 'No HDR algorithm')
echo "pid=$PID tid=$TID user=$(((u2-u1)/5))% sys=$(((s2-s1)/5))% of one core ipa_hdr_warnings=$w in 5 s"
