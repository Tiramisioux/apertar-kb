#!/bin/bash
# SSD campaign night 1 (2026-11-09): after smoke test 2, S2 (write-pattern matrix) and S3 (paced 2K emulation, flat vs
# subdir 5000), then the unattended ladder. Each step starts after the last ends; the ladder only after a clean smoke test 2.
# No reboot resume (no crontab line): a reboot ends the night; rerun the ladder line by hand with the same --out to resume.
set -u
cd ~/ssd-campaign
T=~/apertar-kb/working/tools
LOG=~/ssd-campaign/night1.log
say(){ echo "$(date '+%F %T') $*" >> "$LOG"; }
say "night1b start (smoke 2 stopped at MLV setup_mismatch; runner fixed; smoke 3 MkS passed)"
grep -q "all stages done" ~/longtakes/smoke3-20261109/DONE || { say "STOP: smoke 3 not clean"; exit 1; }
[ -z "$(ls -A /media/RAW)" ] || say "note: on the drive before S2: $(ls -A /media/RAW | tr '\n' ' ')"
mkdir -p S2 S3
run_probe(){ # name, args...
  local name=$1; shift
  say "$name start: $*"
  python3 -I $T/exfat_write_probe.py --out ~/ssd-campaign/$name "$@" > ~/ssd-campaign/$name.out 2>&1
  say "$name end rc=$? $(tail -1 ~/ssd-campaign/$name.out | cut -c1-200)"
}
run_probe S2/default   --size-mb 12.4 --files 300
run_probe S2/workers1  --size-mb 12.4 --files 300 --workers 1
run_probe S2/prealloc  --size-mb 12.4 --files 300 --prealloc
run_probe S2/fsyncnone --size-mb 12.4 --files 300 --fsync none
run_probe S2/chunk0    --size-mb 12.4 --files 300 --chunk-kb 0
run_probe S2/direct    --size-mb 12.4 --files 300 --chunk-kb 0 --prealloc --direct
run_probe S2/subdir    --size-mb 12.4 --files 300 --subdir 5000
run_probe S3/flat38    --size-mb 1.3 --fps 38 --seconds 1800 --budget-mb 800
run_probe S3/subdir38  --size-mb 1.3 --fps 38 --seconds 1800 --budget-mb 800 --subdir 5000
say "probes done; drive: $(ls -A /media/RAW | tr '\n' ' ')"
say "ladder start"
cd ~/longtakes && python3 -I bin/longtakes.py --out ~/longtakes/ladder-20261109 --stages msLMkS --modes 2kSDR12,2kHDR16 --budget-gb 3500 --disk-mbps 167 >> ~/longtakes/ladder-20261109.out 2>&1
say "ladder process ended rc=$? DONE: $(head -2 ~/longtakes/ladder-20261109/DONE 2>/dev/null)"
