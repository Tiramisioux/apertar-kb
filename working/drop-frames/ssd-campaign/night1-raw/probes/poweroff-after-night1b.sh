#!/bin/bash
# One-shot: when night1.sh has ended (any reason), wait 2 min, then power the Pi off through Core (User asked, 2026-11-09).
LOG=~/ssd-campaign/night1.log
C="python3 -I $HOME/apertar-kb/working/tools/core.py"
P=${1:?pid of night1b.sh}; while kill -0 $P 2>/dev/null; do sleep 60; done
sleep 120
for i in $(seq 1 30); do
  $C get_state 2>/dev/null | grep -q '"recording":false' && break
  sleep 60
done
sync
echo "$(date '+%F %T') night over; powering off through Core (power_off_system)" >> "$LOG"
sync
$C power_off_system >> "$LOG" 2>&1
