#!/bin/bash
# est-after-night.sh <run dir> <night tag, e.g. S6>      (estimator campaign; runs on the Pi, no computer needed)
#
# User 2026-11-11: "can you start the day run automatically after the nights run?". Started while the NVMe nights run; it
#  1. ends a hopeless GO wait: when status.md says a GO condition is false (go_wait would hold the night for 8 h, nobody answers
#     at night), it sends the runner SIGTERM: the take is not running, the runner restores and ends the night, and the chain
#     goes on as it would after the 8 h;
#  2. takes over from night <tag>'s power-off follower once it appears (start-night.sh starts it as
#     "poweroff-after-night.sh <runner pid> <run> <tag>"), follows that runner, and when it has ended waits for a quiet camera,
#     RESTORE OK in restore-<tag>.txt, frames_per_folder 5000 and the merge on, and an end that is not a watchdog;
#  3. runs the EST smoke (P0 with 20-s takes, kept apart as smoke-P0) from ~/longtakes/bin-est and requires RESTORE OK, no
#     traceback and at least 6 usable smoke probes;
#  4. starts the estimator day: start-est.sh EST with campaign-est.env (cap 16 TB) and bin-est; it powers off at the end.
# Anything missing = the day is not started and the Pi powers off through poweroff-after-night.sh's own checks.
# Log: ~/nvme-campaign/EST-chain.log (stdout).
set -u
RUN=${1:?run dir}; TAG=${2:?night tag}
NC=$HOME/nvme-campaign
C="python3 -I $HOME/longtakes/bin/core.py"
say(){ echo "$(date '+%F %T') $*"; }
field(){ $C get_state 2>/dev/null | grep -oE "\"$1\":(\"[^\"]*\"|[^,}]*)" | head -1 | cut -d: -f2- | tr -d '"'; }
say "waiting for night $TAG (run $RUN)"
P=""; termed=""
for i in $(seq 1 2880); do                               # up to 48 h
  F=$(pgrep -af "[p]oweroff-after-night.sh [0-9]+ $RUN $TAG\$" | head -1)
  if [ -n "$F" ]; then
    FP=${F%% *}; P=$(echo "$F" | awk '{print $4}')
    kill "$FP" && say "took over from night $TAG's power-off follower (pid $FP); following runner pid $P"
    break
  fi
  h=$(head -1 "$RUN/status.md" 2>/dev/null)
  case "$h" in
    "WAITING for GO-"*" is false"*)
      a=$(sed -n 's/^pid=\([0-9]*\).*/\1/p' "$RUN/ACTIVE" 2>/dev/null)
      if [ -n "$a" ] && [ "$a" != "$termed" ] && kill -0 "$a" 2>/dev/null; then
        say "status: $h -> SIGTERM to runner $a (an 8-h wait nobody answers; the runner restores and ends the night)"
        kill -TERM "$a"; termed=$a
      fi ;;
  esac
  sleep 30
done
[ -n "$P" ] || { say "night $TAG never started within 48 h"; exit 0; }
while kill -0 "$P" 2>/dev/null; do sleep 60; done
say "night $TAG's runner ended; waiting for a quiet camera"
sleep 60
quiet=0
for i in $(seq 1 30); do
  if [ "$(field recording)" = "false" ] && [ "$(field media_writes_pending)" = "false" ] && [ -z "$(field clip_merge_active)" ]; then quiet=1; break; fi
  sleep 60
done
fb(){ say "NOT starting the estimator day: $*; handing over to the power-off follower"; exec bash "$NC/poweroff-after-night.sh" "$P" "$RUN" "$TAG"; }
[ "$quiet" = 1 ] || fb "Core still recording, writing or merging after 30 min"
grep -q '^RESTORE OK' "$RUN/restore-$TAG.txt" 2>/dev/null || fb "restore-$TAG.txt missing or not RESTORE OK"
fpf=$(field frames_per_folder); mrg=$(field clip_merge_enabled)
{ [ "$fpf" = "5000" ] && [ "$mrg" = "true" ]; } || fb "read back frames_per_folder=$fpf clip_merge_enabled=$mrg"
why=$(grep -h "night .* over" "$RUN/runner.log" | tail -1)
say "night $TAG ended on: ${why:0:200}"
case "$why" in *watchdog*|*critical*|*serial*|*"not mounted"*|*fault*|*"needs a human"*) fb "the night ended on a hardware or setup problem" ;; esac
say "EST smoke (P0, 20-s takes) from bin-est"
. "$NC/campaign-est.env"
python3 -I "$HOME/longtakes/bin-est/longtakes.py" --out "$RUN" --stages N --night EST --est-blocks P0 --max-seconds 20 --no-go \
  --audio-optional --expect-serial "$EXPECT_SERIAL" --modes "$MODES" --idle-between 0 --cold-wait 0 > "$NC/EST-smoke.log" 2>&1
grep -q '^RESTORE OK' "$RUN/restore-EST.txt" 2>/dev/null || fb "the smoke's restore-EST.txt is not RESTORE OK"
grep -q 'Traceback' "$NC/EST-smoke.log" && fb "the smoke raised (see EST-smoke.log)"
n=$(python3 -I -c "
import json,sys
n=0
for l in open(sys.argv[1]):
    r=json.loads(l)
    if r.get('block')=='smoke-P0' and r.get('verdict') not in ('skip','void','stop',None): n+=1
print(n)" "$RUN/est/probes.jsonl" 2>/dev/null || echo 0)
say "smoke: $n usable probes of 10"
[ "${n:-0}" -ge 6 ] || fb "only $n usable smoke probes"
say "starting the estimator day"
CAMPAIGN_ENV="$NC/campaign-est.env" LT_BIN="$HOME/longtakes/bin-est" bash "$NC/start-est.sh" EST --max-voids 4
