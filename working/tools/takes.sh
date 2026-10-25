#!/bin/bash
# takes.sh N [seconds]: N takes in the current mode, each after a 12 -> 16 reconfigure.
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
    stats=$(journalctl -u apertar-core --since "$T1" --no-pager | grep -oE 'enqueued=[0-9]+|dropped_queue_full=[0-9]+|dropped_gap_estimate=[0-9]+|peak_queue=[0-9/]+' | tr '\n' ' ')
    files=$(ls "$clip" | grep -oE '_[0-9]{9}\.dng$' | tr -dc '0-9\n' | sed 's/^0*//;s/^$/0/' | sort -n | awk '{if(NR>1 && $1!=p+1){g++; miss+=$1-p-1}; p=$1} END{printf "files=%d last=%d missing=%d", NR, p, miss+0}')
    ipa=$(python3 -I $S/ipa_rate.py "$T1" "$T2" | head -1 | grep -oE 'rate=[0-9.]+/s intervals>60ms=[0-9]+')
    echo "$(basename "$clip") $files | $stats| ipa $ipa"
done
