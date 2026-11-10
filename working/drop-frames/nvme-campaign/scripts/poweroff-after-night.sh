#!/bin/bash
# poweroff-after-night.sh <runner pid> <run dir> <night tag>     (NVMe campaign, build list R4; pattern: ssd-campaign/night2/poweroff-after-night2.sh)
#
# Follows the night's runner by its PID. When it has ended (any reason), waits until Core records nothing, has no writes pending
# and no merge running (up to 30 min), then requires the runner's restore list: <run>/restore-<night tag>.txt must say RESTORE OK
# and Core must read back frames_per_folder 5000 and the merge on. Only then: sync, and Core's power_off_system over the socket.
# Anything missing = the Pi stays on and the reason is logged (plan: power off only after the restore list is written and read back).
# Started by start-night.sh, detached. Log: ~/nvme-campaign/<night tag>-poweroff.log (stdout).
set -u
P=${1:?runner pid}; RUN=${2:?run dir}; TAG=${3:?night tag}
C="python3 -I $HOME/longtakes/bin/core.py"
say(){ echo "$(date '+%F %T') $*"; }
field(){ $C get_state 2>/dev/null | grep -oE "\"$1\":(\"[^\"]*\"|[^,}]*)" | head -1 | cut -d: -f2- | tr -d '"'; }
say "following runner pid $P (night $TAG, run $RUN)"
while kill -0 "$P" 2>/dev/null; do sleep 60; done
say "runner ended; waiting for a quiet camera"
sleep 60
quiet=0
for i in $(seq 1 30); do
  if [ "$(field recording)" = "false" ] && [ "$(field media_writes_pending)" = "false" ] && [ -z "$(field clip_merge_active)" ]; then quiet=1; break; fi
  sleep 60
done
[ "$quiet" = 1 ] || { say "NOT powering off: Core still recording, writing or merging after 30 min"; exit 1; }
R="$RUN/restore-$TAG.txt"
if [ ! -f "$R" ] || ! grep -q '^RESTORE OK' "$R"; then
  say "NOT powering off: $R missing or not RESTORE OK: $(tail -1 "$R" 2>/dev/null)"; exit 1
fi
fpf=$(field frames_per_folder); mrg=$(field clip_merge_enabled)
if [ "$fpf" != "5000" ] || [ "$mrg" != "true" ]; then
  say "NOT powering off: read back frames_per_folder=$fpf clip_merge_enabled=$mrg (want 5000, true)"; exit 1
fi
say "restore read back: frames_per_folder=$fpf merge=$mrg; $(tail -1 "$R")"
sync
say "night $TAG over; powering off through Core (power_off_system)"
sync
$C power_off_system
