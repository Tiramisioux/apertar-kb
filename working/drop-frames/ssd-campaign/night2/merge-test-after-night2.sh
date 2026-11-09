#!/bin/bash
# SSD campaign night 2, after the chain (User asked, 2026-11-09): time the merge of one 30-minute split clip.
# Waits for night2.sh (pid $1) to end, idles 10 min (drive recovery), records one take of 30 min at 2kSDR12
# uncompressed 25 fps with frames_per_folder 5000 and the merge off (45,000 frames in 9 parts, ~140 GB), then turns
# the merge on and logs Core's clip_merge_* fields every 10 s until nothing is pending. Then Core's own merge lines
# from the journal, the delete of that one clip through Core's media route (never a glob, never rmtree), and the
# camera settings back as they were. Leaves frames_per_folder 5000 and the merge on (User's defaults). The Pi powers
# off after this script, not after night2.sh: poweroff-after-night2.sh follows this pid.
set -u
P=${1:?pid of night2.sh}
C="python3 -I $HOME/apertar-kb/working/tools/core.py"
LOG=~/ssd-campaign/merge-test.log
say(){ echo "$(date '+%F %T') $*" >> "$LOG"; }
field(){ $C get_state 2>/dev/null | grep -oE "\"$1\":(\"[^\"]*\"|[^,}]*)" | head -1 | cut -d: -f2- | tr -d '"'; }
while kill -0 "$P" 2>/dev/null; do sleep 60; done
say "night2 ended; merge test start; idle 10 min"
sleep 600
[ "$(field recording)" = "false" ] || { say "STOP: the camera is recording"; exit 1; }
free_gb=$(python3 -I -c "import os;s=os.statvfs('/media/RAW');print(s.f_bavail*s.f_frsize//10**9)")
[ "$free_gb" -ge 200 ] || { say "STOP: only $free_gb GB free"; exit 1; }
# What to put back afterwards.
O_HDR=$(field clear_hdr); O_RES=$(field resolution); O_BITS=$(field raw_bit_depth); O_FPS=$(field fps)
O_COMP=$(field cdng_compression)
say "before: clear_hdr=$O_HDR resolution=$O_RES bits=$O_BITS fps=$O_FPS comp=$O_COMP; free ${free_gb} GB"
$C set_clip_merge enabled=false >> "$LOG" 2>&1
$C set_frames_per_folder value=5000 >> "$LOG" 2>&1
$C set_clear_hdr enabled=false >> /dev/null 2>&1; sleep 4
$C set_resolution width=1920 height=1080 >> /dev/null 2>&1; sleep 4
$C set_raw_bit_depth value=10 >> /dev/null 2>&1; sleep 5
$C set_raw_bit_depth value=12 >> /dev/null 2>&1; sleep 6
$C set_cdng_compression value=none >> /dev/null 2>&1
$C set_cdng_log value=off >> /dev/null 2>&1
$C set_fps value=25 >> /dev/null 2>&1; sleep 4
say "set: clear_hdr=$(field clear_hdr) resolution=$(field resolution) bits=$(field raw_bit_depth) fps=$(field fps) comp=$(field cdng_compression) fpf=$(field frames_per_folder)"
before=$(ls -1 /media/RAW | sort)
$C record_start >> "$LOG" 2>&1
say "record_start; 1800 s"
sleep 1800
$C record_stop >> "$LOG" 2>&1
for i in $(seq 1 120); do
  [ "$(field recording)" = "false" ] && [ "$(field media_writes_pending)" != "true" ] && break
  sleep 5
done
CLIP=$(comm -13 <(echo "$before") <(ls -1 /media/RAW | sort) | head -1)
say "record_stop; clip=$CLIP dropped=$(field recording_dropped_frames)"
if [ -z "$CLIP" ] || [ ! -e "/media/RAW/$CLIP/.parts" ]; then
  say "STOP: no new split clip (clip='$CLIP')"
else
  say "parts: $(ls -d /media/RAW/$CLIP/part_* 2>/dev/null | wc -l)"
  T0=$(date +%s)
  $C set_clip_merge enabled=true >> /dev/null 2>&1
  say "merge on"
  for i in $(seq 1 540); do   # up to 90 min
    s=$($C get_state 2>/dev/null)
    line=$(echo "$s" | grep -oE "\"clip_merge_(pending|active|paused|clip_done|clip_total|all_done|all_total|eta_s)\":(\"[^\"]*\"|[^,}]*)" | tr '\n' ' ')
    echo "$(( $(date +%s) - T0 )) s $line" >> ~/ssd-campaign/merge-test-samples.txt
    if echo "$s" | grep -q '"clip_merge_pending":0' && echo "$s" | grep -q '"clip_merge_active":""'; then break; fi
    sleep 10
  done
  say "merge over after $(( $(date +%s) - T0 )) s; parts left: $(ls -d /media/RAW/$CLIP/part_* 2>/dev/null | wc -l); .parts: $([ -e /media/RAW/$CLIP/.parts ] && echo yes || echo no)"
  journalctl -u apertar-core --no-pager -o short-iso --since "@$T0" 2>/dev/null | grep "clip merge" >> "$LOG"
  r=$(curl -s -X POST "http://127.0.0.1:8000/api/media/delete?kind=folder&id=$CLIP")
  say "delete $CLIP: $r"
fi
$C set_clear_hdr enabled="$O_HDR" >> /dev/null 2>&1; sleep 4
$C set_resolution width="${O_RES%x*}" height="${O_RES#*x}" >> /dev/null 2>&1; sleep 4
$C set_raw_bit_depth value=$([ "$O_BITS" = 12 ] && echo 16 || echo 12) >> /dev/null 2>&1; sleep 5
$C set_raw_bit_depth value="$O_BITS" >> /dev/null 2>&1; sleep 6
$C set_cdng_compression value="$O_COMP" >> /dev/null 2>&1
$C set_fps value="$O_FPS" >> /dev/null 2>&1; sleep 2
$C set_frames_per_folder value=5000 >> /dev/null 2>&1
$C set_clip_merge enabled=true >> /dev/null 2>&1
say "restored: clear_hdr=$(field clear_hdr) resolution=$(field resolution) bits=$(field raw_bit_depth) fps=$(field fps) comp=$(field cdng_compression) fpf=$(field frames_per_folder) merge=$(field clip_merge_enabled); merge test end"
