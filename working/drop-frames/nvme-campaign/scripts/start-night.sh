#!/bin/bash
# start-night.sh <stages> [--go STAGE=CONDITION ...] [runner args ...]     (NVMe campaign; runs on the Pi, no computer needed)
#
# The one command that starts a night, from any terminal on the Pi (an ssh app on a phone is enough). Examples:
#   bash ~/nvme-campaign/start-night.sh S2
#   bash ~/nvme-campaign/start-night.sh S4,S5 --go "S4=unconditional" --go "S5=if all_passed S4"
#   bash ~/nvme-campaign/start-night.sh S6,END --go "S6=unconditional"
#   bash ~/nvme-campaign/start-night.sh SMOKE --max-seconds 20 --no-go --smoke-delete      (the build evening's smoke take)
# It reads ~/nvme-campaign/campaign.env, writes the GO-<stage> sentinels asked for (one line each: unconditional |
# if all_passed <stage> | if passed <mode> <stage>), then starts, detached (setsid nohup, the lesson of nights 1-2):
#   the runner     longtakes.py --stages N --night <stages> ...      log ~/nvme-campaign/<tag>.log
#   the watcher    longtakes_watch.py <run>                          log ~/nvme-campaign/<tag>-watch.log
#   the power-off  poweroff-after-night.sh <runner pid> <run> <tag>  log ~/nvme-campaign/<tag>-poweroff.log
# The runner masks the timers itself (the helper's NOPASSWD word) and checks FE depth 4 in Core's environment (the start script
# sets it since 2026-11-06), so no password is needed. Follow it with:  cat <run>/status.md
set -u
STAGES=${1:?stages, e.g. S2 or S4,S5}; shift
. "$HOME/nvme-campaign/campaign.env"
TAG=$(echo "$STAGES" | tr ',' '-')
GOS=(); ARGS=()
while [ $# -gt 0 ]; do
  case "$1" in
    --go) GOS+=("$2"); shift 2 ;;
    --out) RUN=$2; ARGS+=("$1" "$2"); shift 2 ;;
    *) ARGS+=("$1"); shift ;;
  esac
done
mkdir -p "$RUN" "$HOME/nvme-campaign"
if [ -f "$RUN/ACTIVE" ]; then
  pid=$(sed -n 's/^pid=\([0-9]*\).*/\1/p' "$RUN/ACTIVE")
  if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then echo "a night is already running (pid $pid): $(head -1 "$RUN/status.md")"; exit 1; fi
  echo "stale ACTIVE marker (pid $pid gone): removed"; rm -f "$RUN/ACTIVE"
fi
for g in "${GOS[@]+"${GOS[@]}"}"; do
  st=${g%%=*}; cond=${g#*=}
  printf '%s\n' "$cond" > "$RUN/GO-$st"; echo "GO-$st: $cond"
done
ORDER=""
case "$STAGES" in *S5*) [ -n "$ORDER_S5" ] && ORDER="--order $ORDER_S5" ;; *S6*) [ -n "$ORDER_S6" ] && ORDER="--order $ORDER_S6" ;; esac
CROPARG=""; [ -n "$CROPS" ] && CROPARG="--crop-modes $CROPS"
B=$HOME/longtakes/bin
CMD="python3 -I $B/longtakes.py --out $RUN --stages N --night $STAGES --modes $MODES --start-fps $START_FPS --budget-gb $BUDGET_GB \
--expect-serial $EXPECT_SERIAL --abba $ABBA $ORDER $CROPARG $EXTRA ${ARGS[*]+"${ARGS[*]}"}"
echo "$(date '+%F %T') start-night $STAGES: $CMD" >> "$HOME/nvme-campaign/nights.log"
setsid nohup $CMD </dev/null > "$HOME/nvme-campaign/$TAG.log" 2>&1 &
RP=$!
sleep 2
kill -0 "$RP" 2>/dev/null || { echo "the runner did not start:"; tail -5 "$HOME/nvme-campaign/$TAG.log"; exit 1; }
setsid nohup python3 -I "$B/longtakes_watch.py" "$RUN" </dev/null > "$HOME/nvme-campaign/$TAG-watch.log" 2>&1 &
if [ "$TAG" = SMOKE ]; then
  echo "night SMOKE started: runner pid $RP; no power-off after a smoke run."
else
  setsid nohup bash "$HOME/nvme-campaign/poweroff-after-night.sh" "$RP" "$RUN" "$TAG" </dev/null > "$HOME/nvme-campaign/$TAG-poweroff.log" 2>&1 &
  echo "night $STAGES started: runner pid $RP; the Pi powers off when it is over (if the restore reads back)."
fi
echo "follow:  cat $RUN/status.md"
