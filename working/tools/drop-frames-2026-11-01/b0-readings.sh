#!/bin/sh
# b0-readings.sh [--dry-run]
#
# Root-readable readings for step B0 of the drop-frames plan (inspection-2026-11-02.md section 8.3, B0.10 and M1/M4 prerequisites).
# Run as:  sudo sh b0-readings.sh        Preview: sh b0-readings.sh --dry-run
#
# READ-ONLY: it writes nothing (no file, no sysfs/procfs/tracefs value, no service change). Output goes to stdout only.
# It prints, labelled:
#   - date and uptime in seconds
#   - /proc/slabinfo header plus the exfat, buffer_head and dentry caches
#   - the rp1-cfe csi2_errors file (/sys/kernel/debug/rp1-cfe*/csi2_errors)
#   - `nvme smart-log /dev/nvme0` (skipped with a note if `nvme` is not installed) and a loud STOP line if critical_warning != 0
#   - how many times try_to_free_pages, lru_add_drain_all and lru_cache_disable appear in tracefs available_filter_functions
#   - tracefs available_tracers
#   - the per-CPU trace-buffer overrun counts
# --dry-run only lists what it would read (it does not read any of it).
# Undo: nothing to undo.
set -eu

TR=/sys/kernel/tracing
DRY=0

for a in "$@"; do
  case "$a" in
    --dry-run) DRY=1 ;;
    *) printf '%s\n' "usage: sh b0-readings.sh [--dry-run]"; exit 2 ;;
  esac
done

if [ "$(id -u)" -ne 0 ] && [ "$DRY" -eq 0 ]; then
  printf '%s\n' "b0-readings.sh: must run as root (sudo sh b0-readings.sh): /proc/slabinfo, debugfs and nvme smart-log need it. Or use --dry-run. Nothing was read."
  exit 1
fi

if [ "$DRY" -eq 1 ]; then
  cat <<EOF
b0-readings.sh --dry-run: would read (and write nothing):
  1. date '+%F %T %Z' and the first field of /proc/uptime (uptime seconds)
  2. /proc/slabinfo: the header line and the lines starting exfat, buffer_head, dentry
  3. /sys/kernel/debug/rp1-cfe*/csi2_errors (read-only glob; if none or several match, it prints what was found)
  4. nvme smart-log /dev/nvme0 (if nvme is not installed it says so); then a STOP line if critical_warning != 0
  5. grep -cw try_to_free_pages, lru_add_drain_all, lru_cache_disable in $TR/available_filter_functions
  6. $TR/available_tracers
  7. grep overrun $TR/per_cpu/cpu*/stats
EOF
  exit 0
fi

echo "=== 1. date and uptime"
echo "date: $(date '+%F %T %Z')"
if [ -r /proc/uptime ]; then
  IFS=' ' read -r up _ < /proc/uptime
  echo "uptime_s: ${up%%.*}"
else
  echo "uptime_s: unreadable (/proc/uptime)"
fi

echo
echo "=== 2. /proc/slabinfo (exfat, buffer_head, dentry)"
if [ -r /proc/slabinfo ]; then
  grep -E '^(# name|exfat|buffer_head|dentry)' /proc/slabinfo || echo "(no matching lines)"
else
  echo "/proc/slabinfo is not readable (not root, or the kernel has no slabinfo)"
fi

echo
echo "=== 3. csi2_errors"
n=0; list=""; dir=""
for d in /sys/kernel/debug/rp1-cfe*; do
  [ -e "$d" ] || continue
  n=$((n + 1)); list="$list $d"; dir=$d
done
if [ "$n" -eq 0 ]; then
  echo "no directory matches /sys/kernel/debug/rp1-cfe* (debugfs not mounted, or the driver is not loaded)"
elif [ "$n" -gt 1 ]; then
  echo "found $n matches, not reading any:$list"
elif [ -f "$dir/csi2_errors" ]; then
  echo "csi2_errors ($dir):"
  sed 's/^/  /' "$dir/csi2_errors" 2>&1 || echo "  $dir/csi2_errors is not readable"
else
  echo "$dir has no csi2_errors file (kernel without rp1_cfe.track_csi2_errors=1?)"
  echo "contents: $(for f in "$dir"/*; do printf '%s ' "${f##*/}"; done)"
fi

echo
echo "=== 4. nvme smart-log /dev/nvme0"
if command -v nvme > /dev/null 2>&1; then
  if smart=$(nvme smart-log /dev/nvme0 2>&1); then
    printf '%s\n' "$smart"
    cw=$(printf '%s\n' "$smart" | awk -F: '$1 ~ /^critical_warning/ { gsub(/[ \t]/, "", $2); print $2; exit }')
    case "$cw" in
      0|0x0|0x00) echo "critical_warning: $cw (ok)" ;;
      "") echo "STOP: critical_warning could not be read from the smart-log output above. Treat as != 0 until checked." ;;
      *) echo "STOP: critical_warning != 0 (value: $cw). Do not run any take." ;;
    esac
  else
    printf '%s\n' "$smart"
    echo "STOP: nvme smart-log failed; critical_warning unknown. Treat as != 0 until checked."
  fi
else
  echo "nvme is not installed (apt install nvme-cli); skipping smart-log. critical_warning NOT checked."
fi

echo
echo "=== 5. tracefs available_filter_functions (count of exact-word lines)"
aff=$TR/available_filter_functions
if [ -r "$aff" ]; then
  for fn in try_to_free_pages lru_add_drain_all lru_cache_disable; do
    c=$(grep -cw "$fn" "$aff" || true)
    echo "$fn: $c"
  done
else
  echo "$aff is not readable (no tracefs, or not root)"
fi

echo
echo "=== 6. tracefs available_tracers"
if [ -r "$TR/available_tracers" ]; then
  cat "$TR/available_tracers"
else
  echo "$TR/available_tracers is not readable"
fi

echo
echo "=== 7. per-CPU trace-buffer overrun counts"
po=$(grep -H overrun "$TR"/per_cpu/cpu*/stats 2>/dev/null || true)
if [ -n "$po" ]; then printf '%s\n' "$po"; else echo "(no $TR/per_cpu/cpu*/stats readable)"; fi
