#!/bin/bash
# chain-after-night.sh <runner pid> <run dir> <night tag> <next stages> [start-night args ...]     (NVMe campaign)
#
# Takes the place of poweroff-after-night.sh for a night that another night should follow without anyone there
# (User 2026-11-10: "add S4-S5 to the run"). Follows the runner by its PID; when it has ended, waits for a quiet camera
# (not recording, no writes pending, no merge; up to 30 min), requires <run>/restore-<night tag>.txt to say RESTORE OK
# and Core to read back frames_per_folder 5000 and the merge on, then starts the next night through start-night.sh, which
# starts that night's runner, watcher and power-off follower. Anything missing = nothing is started and the Pi powers
# off through the usual checks of poweroff-after-night.sh, so it is never left running with nobody watching.
# Log: ~/nvme-campaign/<night tag>-chain.log (stdout).
set -u
P=${1:?runner pid}; RUN=${2:?run dir}; TAG=${3:?night tag}; NEXT=${4:?next stages}; shift 4
C="python3 -I $HOME/longtakes/bin/core.py"
say(){ echo "$(date '+%F %T') $*"; }
field(){ $C get_state 2>/dev/null | grep -oE "\"$1\":(\"[^\"]*\"|[^,}]*)" | head -1 | cut -d: -f2- | tr -d '"'; }
fallback(){ say "NOT starting $NEXT: $*; handing over to the power-off follower"; exec bash "$HOME/nvme-campaign/poweroff-after-night.sh" "$P" "$RUN" "$TAG"; }
say "following runner pid $P (night $TAG, run $RUN); next: $NEXT $*"
while kill -0 "$P" 2>/dev/null; do sleep 60; done
say "runner ended; waiting for a quiet camera"
sleep 60
quiet=0
for i in $(seq 1 30); do
  if [ "$(field recording)" = "false" ] && [ "$(field media_writes_pending)" = "false" ] && [ -z "$(field clip_merge_active)" ]; then quiet=1; break; fi
  sleep 60
done
[ "$quiet" = 1 ] || fallback "Core still recording, writing or merging after 30 min"
R="$RUN/restore-$TAG.txt"
{ [ -f "$R" ] && grep -q '^RESTORE OK' "$R"; } || fallback "$R missing or not RESTORE OK"
fpf=$(field frames_per_folder); mrg=$(field clip_merge_enabled)
{ [ "$fpf" = "5000" ] && [ "$mrg" = "true" ]; } || fallback "read back frames_per_folder=$fpf clip_merge_enabled=$mrg"
say "night $TAG ended on: $(grep -h 'night .* over' "$RUN/runner.log" 2>/dev/null | tail -1 | cut -c1-200)"
say "restore read back (frames_per_folder=$fpf merge=$mrg); starting night $NEXT"
bash "$HOME/nvme-campaign/start-night.sh" "$NEXT" "$@"
