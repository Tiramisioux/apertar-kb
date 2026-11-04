# e3-unit.sh <unit> <take>...: the lead's unit loop for evening 3 (tier1-prep-2026-11-03.md section 8 steps 5 and 7).
# Run as pi, detached: setsid nohup bash /run/apertar-media/e3-unit.sh u1 P1 P2 > /run/apertar-media/e3-u1.out 2>&1 </dev/null &
# EVENING=<name> (default e3) names the log, the takes and the scratch file; TAKE_WEBUI=refuse|require passes through to take3v3.sh:
#   EVENING=e4 TAKE_FPS=28 TAKE_WEBUI=require setsid nohup bash /run/apertar-media/e3-unit.sh d1 P1 > /run/apertar-media/e4-d1.out 2>&1 </dev/null &
# Before the first take (and before every take with COOL_EACH=1, target 2): Core's pre-roll done, no b1-trace file,
# NVMe <= 40 C (up to 30 min, else NOT STARTED), serial and warm.bin, cat warm.bin, MemFree, fill <= 2 %.
# Before every other take: serial and warm.bin present. OFF<n> = byte size of libcamera's log before/after each take.
# NVME_GATE=on|off (default on): off skips both NVMe <= 40 C waits and prints the two nvme lines with the reading and " (gate off)".
# Take mode from TAKE_* in the environment (passed through to take3v3.sh); UNIT_SECS = take length (default 180).
U=$1; shift
R=/run/apertar-media; T=$HOME/apertar-kb/working/tools/drop-frames-2026-11-01/take3v3.sh
EVENING=${EVENING:-e3}; LC=$R/libcamera-$EVENING.log; SECS=${UNIT_SECS:-180}; SERIAL=A936B442006AC2; NVME_GATE=${NVME_GATE:-on}; GS=""; [ "$NVME_GATE" = off ] && GS=" (gate off)"
C="python3 -I $HOME/apertar-kb/working/tools/core.py"
nvt(){ cat /sys/class/nvme/nvme0/hwmon*/temp1_input 2>/dev/null | head -1; }
ser(){ tr -d ' ' < /sys/class/nvme/nvme0/serial 2>/dev/null; }
off(){ stat -c %s "$LC" 2>/dev/null || echo 0; }
echo "$EVENING-unit.sh unit=$U takes=$* secs=$SECS env: TAKE_CLEAR_HDR=${TAKE_CLEAR_HDR:-} TAKE_BITS=${TAKE_BITS:-} TAKE_FPS=${TAKE_FPS:-} TAKE_COMPRESSION=${TAKE_COMPRESSION:-} TAKE_WEBUI=${TAKE_WEBUI:-} TAKE_STOP_ON_DROP=${TAKE_STOP_ON_DROP:-} NVME_GATE=$NVME_GATE EVENING=$EVENING COOL_EACH=${COOL_EACH:-0} ($(date '+%F %T'))"
CORE=$(systemctl show -p MainPID --value apertar-core)
n=0; until journalctl -b _PID="$CORE" --no-pager 2>/dev/null | grep -q 'storage preroll: reason=start.*result='; do
  n=$((n+1)); [ $n -gt 120 ] && { echo "NOT STARTED: no storage preroll line for Core $CORE after 10 min"; exit 2; }; sleep 5; done
echo "core $CORE pre-roll done: $(journalctl -b _PID="$CORE" --no-pager | grep 'storage preroll: reason=start' | tail -1 | grep -oE 'result=[a-z]+ ms=[0-9]+')"
i=0; first=1
for P in "$@"; do
  if [ $first = 1 ] || [ "${COOL_EACH:-0}" = 1 ]; then
    n=0; while ls $R/b1-trace-* >/dev/null 2>&1; do n=$((n+1)); [ $n -gt 60 ] && { echo "NOT STARTED: b1-trace file left: $(ls $R/b1-trace-*)"; exit 2; }; sleep 10; done
    # one reading decides and is printed (2026-11-04: a second read printed 40850 after a 39850 had passed the check);
    # the same reading again right before OFF0 must also be <= 40000, else wait again
    n=0; while :; do T0=$(nvt); [ "$NVME_GATE" = off ] && break; [ "$T0" -le 40000 ] && break; n=$((n+1)); [ $n -gt 180 ] && { echo "NOT STARTED: NVMe $T0 m°C after 30 min"; exit 2; }; sleep 10; done
    echo "nvme at unit start: $T0 m°C ($(date +%T)) serial=$(ser)$GS"
    [ "$(ser)" = "$SERIAL" ] || { echo "NOT STARTED: card serial $(ser), not $SERIAL"; exit 3; }
    [ -f /media/RAW/warm.bin ] || { echo "NOT STARTED: /media/RAW/warm.bin missing"; exit 3; }
    cat /media/RAW/warm.bin > /dev/null; echo "warm.bin read ($(date +%T))"
    pct=$(df --output=pcent /media/RAW | tail -1 | tr -dc 0-9)
    echo "fill: $(df -h /media/RAW | awk 'NR==2{print $3" used of "$2" ("$5")"}')"
    [ "$pct" -le 2 ] || { echo "NOT STARTED: fill ${pct} % > 2 %"; exit 3; }
  else
    echo "nvme at $P start: $(nvt) m°C ($(date +%T)) serial=$(ser)"
    [ "$(ser)" = "$SERIAL" ] || { echo "STOPPED before $P: card serial $(ser), not $SERIAL"; exit 3; }
    [ -f /media/RAW/warm.bin ] || { echo "STOPPED before $P: /media/RAW/warm.bin missing"; exit 3; }
  fi
  if [ $first = 1 ] || [ "${COOL_EACH:-0}" = 1 ]; then
    n=0; while :; do T1=$(nvt); [ "$NVME_GATE" = off ] && break; [ "$T1" -le 40000 ] && break; n=$((n+1)); [ $n -gt 180 ] && { echo "NOT STARTED: NVMe $T1 m°C after 30 min"; exit 2; }; sleep 10; done
    echo "nvme before OFF: $T1 m°C ($(date +%T))$GS"
  fi
  first=0
  echo "memfree: $(grep MemFree /proc/meminfo | tr -s ' ')"
  echo "OFF$i $(off)"; i=$((i+1))
  echo "===== $P"
  bash "$T" "$SECS" "$EVENING-$U-$P" 2>&1 | tee "$R/.$EVENING-cur.txt"
  if ! grep -q '^restored' "$R/.$EVENING-cur.txt"; then
    echo "TAKE SCRIPT DID NOT FINISH ($P): sending record_stop at $(date +%T)"; $C record_stop; echo; echo "OFF$i $(off)"; exit 4
  fi
done
echo "OFF$i $(off)"
echo "unit $U done $(date +%T)"
