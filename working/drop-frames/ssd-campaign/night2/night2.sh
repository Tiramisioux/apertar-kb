#!/bin/bash
# SSD campaign night 2 (T7, exFAT): confirm the night 1 recommendations. Optional items left out (User, 2026-11-09).
# Run 1: the split layout (frames_per_folder 5000, merge off) at 2kSDR12 unc 32 fps: split30, split10x3, long30, soak x2.
# Run 2: long take 2kSDR12 lossless 48 fps. Run 3: long take 2kHDR16 lossless 27 fps.
# End: frames_per_folder stays 5000 (User: "keep 5000 as the default"), merge back on. No reboot resume.
set -u
cd ~/longtakes
C="python3 -I $HOME/apertar-kb/working/tools/core.py"
LOG=~/ssd-campaign/night2.log
say(){ echo "$(date '+%F %T') $*" >> "$LOG"; }
layout(){ $C set_clip_merge enabled=false >> "$LOG" 2>&1; $C set_frames_per_folder value=5000 >> "$LOG" 2>&1; }
run(){ # name, args...
  local name=$1; shift
  layout
  say "$name start: $*"
  python3 -I bin/longtakes.py --out ~/longtakes/$name "$@" >> ~/longtakes/$name.out 2>&1
  say "$name end rc=$? DONE: $(head -2 ~/longtakes/$name/DONE 2>/dev/null | tr '\n' ' ')"
}
say "night2 start; drive: $(ls -A /media/RAW | tr '\n' ' ')"
run night2-split   --stages sLS --modes 2kSDR12 --split-fps 32 --long-fps 32 --budget-gb 1500 --disk-mbps 167
say "idle 10 min (drive recovery after heavy writes)"; sleep 600
run night2-lj12    --stages L --modes 2kSDR12 --long-comp lossless_jpeg --long-fps 48 --budget-gb 400 --disk-mbps 167
say "idle 10 min"; sleep 600
run night2-lj16    --stages L --modes 2kHDR16 --long-comp lossless_jpeg --long-fps 27 --budget-gb 400 --disk-mbps 167
$C set_frames_per_folder value=5000 >> "$LOG" 2>&1
$C set_clip_merge enabled=true >> "$LOG" 2>&1
say "night2 end; kept frames_per_folder 5000, merge on; drive: $(ls -A /media/RAW | tr '\n' ' ')"
