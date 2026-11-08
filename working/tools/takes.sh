#!/bin/bash
# takes.sh N [seconds]: N takes in the current mode, each after a 12 -> 16 reconfigure.
# Prints the counters T22-T30 judge by; a token that is absent means the stats line did not print it
# (the recording stats line only appears when a counter is non-zero; the phase-lock line only with the lock on).
S=$(dirname "$0")
N=${1:-5}; SECS=${2:-10}
for i in $(seq 1 "$N"); do
    python3 -I $S/core.py set_raw_bit_depth value=12 >/dev/null; python3 -c 'import time; time.sleep(5)'
    python3 -I $S/core.py set_raw_bit_depth value=16 >/dev/null; python3 -c 'import time; time.sleep(6)'
    T1=$(date '+%F %T')
    python3 -I $S/core.py record_start >/dev/null
    python3 -c "import time; time.sleep($SECS)"
    python3 -I $S/core.py record_stop >/dev/null
    T2=$(date '+%F %T')
    python3 -c 'import time; time.sleep(6)'
    clip=$(journalctl -u apertar-core --since "$T1" --no-pager | grep -oE 'recording clip: [^ ]+' | tail -1 | cut -d' ' -f3)
    stats=$(journalctl -u apertar-core --since "$T1" --no-pager | grep -oE 'enqueued=[0-9]+|dropped_queue_full=[0-9]+|dropped_gap_estimate=[0-9]+|peak_queue=[0-9/]+|write_failures=[0-9]+|discarded_on_failure=[0-9]+|skipped_after_failure=[0-9]+|fault=[a-z_]*|media_class=[a-z-]+|media_fs=[a-z-]+|direct_io=[01]|max_abs_err_us=[0-9]+|duration_pushes=[0-9]+|peak_backlog_kb=[0-9]+|changes=[0-9]+|base_fps=[0-9.]+|min_fps=[0-9.]+|max_fps=[0-9.]+' | tr '\n' ' ')
    files=$(find "$clip" -name '*.dng' -printf '%f\n' | grep -oE '_[0-9]{9}\.dng$' | tr -dc '0-9\n' | sed 's/^0*//;s/^$/0/' | sort -n | awk '{if(NR>1 && $1!=p+1){g++; miss+=$1-p-1}; p=$1} END{printf "files=%d last=%d missing=%d", NR, p, miss+0}')
    ipa=$(python3 -I $S/ipa_rate.py "$T1" "$T2" | head -1 | grep -oE 'rate=[0-9.]+/s intervals>60ms=[0-9]+')
    echo "$(basename "$clip") $files | $stats| ipa $ipa"
done
