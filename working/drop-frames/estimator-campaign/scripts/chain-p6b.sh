#!/bin/bash
# chain-p6b.sh <runner pid>: after the P6 runner ends with a fresh RESTORE OK and "all stages", start P6b of EST-05fb8f1-a
# (the Log modes on the warm drive; start-est.sh starts its own power-off follower); otherwise hand over to the usual
# power-off follower. (User 2026-11-21: "add log to everything".)
P=${1:?runner pid}; R=$HOME/longtakes/nvme-20261110; NC=$HOME/nvme-campaign; T0=$(date +%s); TAG=EST-05fb8f1-a
say(){ echo "$(date '+%F %T') $*"; }
say "following runner $P; then P6b"
while kill -0 "$P" 2>/dev/null; do sleep 30; done
sleep 60
F=$R/restore-$TAG.txt
if [ -f "$F" ] && [ "$(stat -c %Y "$F")" -gt "$T0" ] && tail -1 "$F" | grep -q '^RESTORE OK' \
   && tail -3 "$R/runner.log" | grep -q "night $TAG over: all stages"; then
  say "P6 over and restored: starting P6b"
  CAMPAIGN_ENV=$NC/campaign-est.env LT_BIN=$HOME/longtakes/bin-est bash "$NC/start-est.sh" "$TAG" --est-blocks P6b --max-voids 4 --preserve cDNG_26-11-21_23371407_C0005_cam0
else
  say "no clean end of P6 ($(tail -1 "$F" 2>/dev/null); $(tail -1 "$R/runner.log" | cut -c1-150)): power-off follower instead"
  exec bash "$NC/poweroff-after-night.sh" "$P" "$R" "$TAG"
fi
