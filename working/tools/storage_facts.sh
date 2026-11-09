#!/bin/sh
# storage_facts.sh [mountpoint]: the storage facts the slowdown campaign needs before its first take, read-only.
# Runs on the Pi as pi, no sudo. Prints the lines that need root as commands for Patrik to run. Nothing is written.
#   bash ~/apertar-kb/working/tools/storage_facts.sh            # /media/RAW
MNT=${1:-/media/RAW}
echo "== mount =="; findmnt -no SOURCE,FSTYPE,OPTIONS "$MNT" || { echo "$MNT not mounted"; exit 1; }
SRC=$(findmnt -no SOURCE "$MNT"); DEV=$(basename "$(readlink -f "$SRC")")
if [ -e "/sys/class/block/$DEV/partition" ]; then DISK=$(basename "$(readlink -f "/sys/class/block/$DEV/..")"); else DISK=$DEV; fi
echo "device $SRC  disk $DISK"
echo "== exFAT cluster size (statvfs f_bsize) and free space =="; stat -f -c 'cluster_bytes=%S free_clusters=%a total_clusters=%b' "$MNT"; df -B1 "$MNT" | tail -1
echo "== block device =="; lsblk -o NAME,TRAN,MODEL,SIZE,ROTA,DISC-GRAN,DISC-MAX,FSTYPE,LABEL "/dev/$DISK" 2>/dev/null
echo "discard_max_bytes=$(cat /sys/block/$DISK/queue/discard_max_bytes 2>/dev/null)  (0 = the drive or its USB bridge cannot be trimmed)"
echo "scheduler=$(cat /sys/block/$DISK/queue/scheduler 2>/dev/null) nr_requests=$(cat /sys/block/$DISK/queue/nr_requests 2>/dev/null) max_sectors_kb=$(cat /sys/block/$DISK/queue/max_sectors_kb 2>/dev/null) write_cache=$(cat /sys/block/$DISK/queue/write_cache 2>/dev/null) rotational=$(cat /sys/block/$DISK/queue/rotational 2>/dev/null)"
echo "== driver behind the disk (uas = command queuing; usb-storage = one command at a time) =="
D=$(readlink -f "/sys/class/block/$DISK/device"); echo "$D"
P=$D; i=0; while [ "$P" != "/" ] && [ $i -lt 8 ]; do [ -e "$P/driver" ] && echo "  $(basename "$P"): driver $(basename "$(readlink -f "$P/driver")")"; P=$(dirname "$P"); i=$((i+1)); done
grep -m1 -i 'driver=' "/sys/class/block/$DISK/device/uevent" 2>/dev/null
case "$D" in *usb*) echo "USB: $(lsusb -t 2>/dev/null | grep -iE 'uas|storage' | head -5)"; for u in /sys/bus/usb/devices/*/power/control; do echo "  $u = $(cat "$u" 2>/dev/null)"; done | grep -v '= on$' | head -5;; esac
echo "== NVMe =="; for n in /sys/class/nvme/nvme*; do [ -d "$n" ] && echo "$(basename "$n"): $(cat "$n/model" 2>/dev/null) fw $(cat "$n/firmware_rev" 2>/dev/null) state $(cat "$n/state" 2>/dev/null) temp $(cat "$n"/hwmon*/temp1_input 2>/dev/null | head -1)"; done
tr ' ' '\n' < /proc/cmdline | grep -E 'nvme|pcie|psi=' | sed 's/^/  cmdline: /'
dmesg 2>/dev/null | grep -iE 'host memory|hmb' | tail -2 | sed 's/^/  /'
echo "== kernel writeback knobs =="; for k in dirty_bytes dirty_background_bytes dirty_ratio dirty_background_ratio dirty_writeback_centisecs dirty_expire_centisecs; do printf '  %s=%s' "$k" "$(cat /proc/sys/vm/$k)"; done; echo
echo "== power =="; vcgencmd get_throttled 2>/dev/null; vcgencmd pmic_read_adc EXT5V_V 2>/dev/null | head -1; grep -E 'usb_max_current_enable|pciex1' /boot/firmware/config.txt 2>/dev/null | sed 's/^/  config.txt: /'
echo "== Core's view (trim state, media class) =="
if [ -f "$HOME/apertar-kb/working/tools/core.py" ]; then
  python3 -I "$HOME/apertar-kb/working/tools/core.py" get_state 2>/dev/null | python3 -c 'import sys,json; d=json.load(sys.stdin); print({k:d.get(k) for k in ("state","recording","media_state","media_trim_last_result","media_trim_last_bytes","media_trim_last_ms","media_trim_last_unix","media_trim_running","buffer_setting","buffer_capacity","storage_preroll_last")})' 2>/dev/null
fi
journalctl -u apertar-core --no-pager 2>/dev/null | grep -E 'media: trim|media profile|media tune' | tail -4 | sed 's/^/  /'
echo "== newest clip: fragments of its first and last DNG (needs root for FIBMAP on exFAT) =="
CLIP=$(ls -dt "$MNT"/cDNG_* 2>/dev/null | head -1)
if [ -n "$CLIP" ]; then F1=$(ls "$CLIP"/*.dng 2>/dev/null | head -1); F2=$(ls "$CLIP"/*.dng 2>/dev/null | tail -1); N=$(find "$CLIP" -name '*.dng' | wc -l); echo "$CLIP: $N DNGs"
  echo "  run: sudo filefrag -v '$F1' | tail -3; sudo filefrim -v '$F2' | tail -3   (extents > 1 = a FAT-chained file)" | sed 's/filefrim/filefrag/'; else echo "  no cDNG_* folder"; fi
echo "== to run as root (Patrik) =="
echo "  sudo fstrim -v $MNT                      # how long a trim takes here, and whether it works at all"
echo "  sudo smartctl -a /dev/$DISK | grep -iE 'temperature|wear|written|power_on|percent'   # drive temperature and wear (USB SSD: try -d sat)"
[ -e /dev/nvme0 ] && echo "  sudo nvme smart-log /dev/nvme0 | grep -iE 'temperature|data_units_written|percentage_used|unsafe'; sudo nvme id-ctrl /dev/nvme0 | grep -E 'hmpre|hmmin|vwc'   # HMB asked for; volatile write cache"
