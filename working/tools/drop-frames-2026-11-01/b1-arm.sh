#!/bin/sh
# b1-arm.sh <writer|sync|restore|save> [--dry-run] [--trace-buffer]
#
# Root script for one B1 unit of the drop-frames campaign (inspection-2026-11-02.md section 8.3, steps B0.6 and B1).
# Run as:  sudo sh b1-arm.sh writer     (or sync)      after every reboot add --trace-buffer once.
# Preview: sh b1-arm.sh writer --dry-run               (prints everything it would do, changes nothing, may run as a normal user)
#
# writer | sync
#   1. Saves the original tracefs values (buffer_size_kb, tracing_on, each listed event's enable) to /run/b1-arm.orig,
#      only if that file does not exist yet, so a second run keeps the first originals.
#   2. Writes the systemd drop-in /run/systemd/system/apertar-core.service.d/dontneed.conf with exactly
#        [Service]
#        Environment=APERTAR_DNG_DONTNEED=<arm>
#      then `systemctl daemon-reload` and `systemctl restart apertar-core`, waits up to 30 s for the unit to be active with a
#      non-zero MainPID, reads /proc/<MainPID>/environ and exits 1 loudly if APERTAR_DNG_DONTNEED differs from <arm>.
#   3. tracefs (/sys/kernel/tracing): with --trace-buffer only, buffer_size_kb = 8192 (per CPU; never larger). Always: sets
#      `enable` to 1 for the seven vmscan/v4l2/vb2 events (or prints "missing: <event>"), prints the per-CPU overrun counts,
#      clears the trace buffer, sets tracing_on to 1.
#   4. Reads the rp1-cfe csi2_errors file once and prints it as the discarded baseline.
#   Every value it changes is printed as `name: old -> new`, and again in a summary block at the end.
#
# Before it clears or disables anything, every mode saves the trace buffer of the takes since the last arm to
#   /run/apertar-media/b1-trace-<HHMMSS>.txt (mode 0644, for the unprivileged copy to the Mac; tmpfs, so it costs RAM until it is
#   copied and deleted). save: only that, plus the per-CPU overrun counts (after the last unit of a block).
#
# restore
#   Disables the seven events, sets tracing_on and buffer_size_kb back from /run/b1-arm.orig (if that file is absent: events
#   set to 0, buffer size reported unknown and left, tracing_on left), removes the drop-in dontneed.conf if present,
#   daemon-reload, restarts apertar-core, waits as above and prints the Core environ line (expect no APERTAR_DNG_DONTNEED:
#   the build default is sync). /run/b1-arm.orig is NOT deleted (tmpfs, gone at the next reboot).
#
# What it writes (nothing else): /run/systemd/system/apertar-core.service.d/ (directory), .../dontneed.conf, /run/b1-arm.orig,
#   /run/apertar-media/b1-trace-<HHMMSS>.txt,
#   /sys/kernel/tracing/{buffer_size_kb,tracing_on,trace,events/<event>/enable,events/vb2/vb2_buf_done/filter}; and it
#   restarts apertar-core via systemctl. restore clears the filter (writes 0).
#   No /proc/irq, no sysctl, nothing in /etc or /boot. The only deletion is `rm -f` of dontneed.conf, in restore.
#
# How to undo it by hand (same as `sudo sh b1-arm.sh restore`):
#   sudo rm -f /run/systemd/system/apertar-core.service.d/dontneed.conf
#   sudo systemctl daemon-reload && sudo systemctl restart apertar-core
#   and echo 0 into the events' enable files / restore tracing_on and buffer_size_kb from /run/b1-arm.orig.
#   A reboot also undoes all of it (/run and tracefs are not persistent).
set -eu
umask 022

UNIT=apertar-core
FILE=/run/systemd/system/apertar-core.service.d/dontneed.conf
DIR=/run/systemd/system/apertar-core.service.d
ORIG=/run/b1-arm.orig
TR=/sys/kernel/tracing
BUF_KB=8192
# vb2_buf_done fires ~45 times per frame for the ISP nodes and overran CPU0's 8 MiB in one unit (2026-11-02): keep only
# the CFE raw node (type 1, 4K raw frames of ~16.9 MB), whose owned_by_drv/queued show the 8 raw buffers draining
VB2_FILTER='type == 1 && bytesused > 10000000'
EVENTS="vmscan/mm_vmscan_direct_reclaim_begin vmscan/mm_vmscan_direct_reclaim_end vmscan/mm_vmscan_kswapd_wake vmscan/mm_vmscan_kswapd_sleep vmscan/mm_vmscan_throttled v4l2/vb2_v4l2_buf_done vb2/vb2_buf_done"

MODE=""
DRY=0
TRACEBUF=0
NOTES=""
FAIL=0

say() { printf '%s\n' "$*"; }
usage() { say "usage: sh b1-arm.sh <writer|sync|restore|save> [--dry-run] [--trace-buffer]"; }

for a in "$@"; do
  case "$a" in
    writer|sync|restore|save) [ -z "$MODE" ] || { usage; exit 2; }; MODE=$a ;;
    --dry-run) DRY=1 ;;
    --trace-buffer) TRACEBUF=1 ;;
    *) usage; exit 2 ;;
  esac
done
[ -n "$MODE" ] || { usage; exit 2; }

if [ "$(id -u)" -ne 0 ] && [ "$DRY" -eq 0 ]; then
  say "b1-arm.sh: must run as root (sudo sh b1-arm.sh $MODE), or use --dry-run to preview. Nothing was changed."
  exit 1
fi

note() { NOTES="$NOTES
  $*"; }

summary() {
  say ""
  if [ "$DRY" -eq 1 ]; then
    say "=== SUMMARY (DRY RUN: nothing was changed; this is what a real run would change) ==="
  else
    say "=== SUMMARY of every value changed ==="
  fi
  if [ -n "$NOTES" ]; then printf '%s\n' "$NOTES" | sed '1{/^$/d;}'; else say "  (none)"; fi
  say "==="
}

die() {
  say ""
  say "!!!!!! b1-arm.sh: $* !!!!!!"
  summary
  exit 1
}

# First word of a file's first line (the value of a tracefs knob), or "?" if unreadable.
first_word() {
  l=""
  if [ -r "$1" ]; then IFS= read -r l < "$1" || true; fi
  [ -n "$l" ] || l="?"
  printf '%s\n' "${l%% *}"
}

# buffer_size_kb reads "N" or, before the buffer was first used, "N (expanded: M)"; M is what it becomes on first use.
read_buf_kb() {
  l=""
  if [ -r "$TR/buffer_size_kb" ]; then IFS= read -r l < "$TR/buffer_size_kb" || true; fi
  case "$l" in
    *expanded:*) printf '%s\n' "$l" | sed -n 's/.*expanded: *\([0-9][0-9]*\).*/\1/p' ;;
    "") printf '?\n' ;;
    *) printf '%s\n' "${l%% *}" ;;
  esac
}

# set_val <file> <label> <new>: write one tracefs value, print and record `label: old -> new`.
set_val() {
  sv_f=$1; sv_label=$2; sv_new=$3
  if [ "$sv_f" = "$TR/buffer_size_kb" ]; then sv_old=$(read_buf_kb); else sv_old=$(first_word "$sv_f"); fi
  if [ "$DRY" -eq 1 ]; then
    say "  would set $sv_label: $sv_old -> $sv_new"
    note "$sv_label: $sv_old -> $sv_new"
    return 0
  fi
  if printf '%s\n' "$sv_new" > "$sv_f"; then
    say "  $sv_label: $sv_old -> $sv_new"
    note "$sv_label: $sv_old -> $sv_new"
  else
    say "  FAILED to write $sv_new to $sv_f"
    FAIL=1
  fi
}

# run_cmd <cmd...>: run a command (or say that it would run).
run_cmd() {
  if [ "$DRY" -eq 1 ]; then say "  would run: $*"; return 0; fi
  say "  run: $*"
  "$@" || die "command failed: $*"
}

wait_core() {
  wc_i=0
  while [ "$wc_i" -lt 30 ]; do
    wc_st=$(systemctl is-active "$UNIT" 2>/dev/null || true)
    PID=$(systemctl show -p MainPID --value "$UNIT" 2>/dev/null || true)
    case "$PID" in ""|0|*[!0-9]*) ;; *) [ "$wc_st" = active ] && return 0 ;; esac
    wc_i=$((wc_i + 1))
    sleep 1
  done
  return 1
}

core_environ_value() { # prints the APERTAR_DNG_DONTNEED line of MainPID's environment, or nothing
  { tr '\0' '\n' < "/proc/$PID/environ" | grep '^APERTAR_DNG_DONTNEED=' | head -n1; } 2>/dev/null || true
}

restart_and_wait() {
  OLDPID=$(systemctl show -p MainPID --value "$UNIT" 2>/dev/null || true)
  run_cmd systemctl daemon-reload
  run_cmd systemctl restart "$UNIT"
  if [ "$DRY" -eq 1 ]; then
    say "  would wait up to 30 s for: systemctl is-active $UNIT = active and a non-zero MainPID"
    say "  would read /proc/<MainPID>/environ and print the APERTAR_DNG_DONTNEED value"
    note "$UNIT: restarted (MainPID ${OLDPID:-?} -> new)"
    return 0
  fi
  PID=0
  wait_core || die "$UNIT is not active with a MainPID within 30 s of the restart (state: $(systemctl is-active "$UNIT" 2>/dev/null || true))"
  say "  $UNIT active, MainPID ${OLDPID:-?} -> $PID"
  note "$UNIT: restarted (MainPID ${OLDPID:-?} -> $PID)"
}

print_overruns() {
  say "  per-CPU overrun counts (before clearing):"
  po_out=$(grep -H overrun "$TR"/per_cpu/cpu*/stats 2>/dev/null || true)
  if [ -n "$po_out" ]; then printf '%s\n' "$po_out" | sed 's/^/    /'; else say "    (no $TR/per_cpu/cpu*/stats readable)"; fi
}

print_csi2() {
  say "csi2_errors (discarded baseline):"
  p_n=0; p_list=""; p_dir=""
  for p_d in /sys/kernel/debug/rp1-cfe*; do
    [ -e "$p_d" ] || continue
    p_n=$((p_n + 1)); p_list="$p_list $p_d"; p_dir=$p_d
  done
  if [ "$p_n" -eq 0 ]; then
    say "  no directory matches /sys/kernel/debug/rp1-cfe* (debugfs not mounted, not root, or the driver is not loaded)"
  elif [ "$p_n" -gt 1 ]; then
    say "  found $p_n matches, not reading any:$p_list"
  elif [ -f "$p_dir/csi2_errors" ]; then
    { sed 's/^/  /' "$p_dir/csi2_errors"; } 2>&1 || say "  $p_dir/csi2_errors is not readable"
  else
    say "  $p_dir has no csi2_errors file (kernel without rp1_cfe.track_csi2_errors=1?)"
    say "  contents: $(for p_f in "$p_dir"/*; do printf '%s ' "${p_f##*/}"; done)"
  fi
}

# ---- originals -------------------------------------------------------------------------------------------------------
save_orig() {
  if [ -e "$ORIG" ]; then
    say "originals: $ORIG exists, keeping the first originals ($(wc -l < "$ORIG") lines)"
    return 0
  fi
  so_text="buffer_size_kb=$(read_buf_kb)
tracing_on=$(first_word "$TR/tracing_on")"
  for so_e in $EVENTS; do
    if [ -d "$TR/events/$so_e" ]; then
      so_text="$so_text
event:$so_e=$(first_word "$TR/events/$so_e/enable")"
    fi
  done
  if [ "$DRY" -eq 1 ]; then
    say "originals: would write $ORIG with:"
    printf '%s\n' "$so_text" | sed 's/^/    /'
    return 0
  fi
  printf '%s\n' "$so_text" > "$ORIG" || die "cannot write $ORIG"
  say "originals: saved to $ORIG:"
  printf '%s\n' "$so_text" | sed 's/^/    /'
}

orig_get() { # orig_get <key>: value from $ORIG, empty if absent
  [ -r "$ORIG" ] || return 0
  awk -F= -v k="$1" '$1 == k { print $2; exit }' "$ORIG"
}

# ---- service drop-in -------------------------------------------------------------------------------------------------
write_dropin() {
  say "drop-in $FILE:"
  if [ -f "$FILE" ]; then
    wd_oldtxt=$(cat "$FILE")
    wd_oldval=$(printf '%s\n' "$wd_oldtxt" | sed -n 's/^Environment=APERTAR_DNG_DONTNEED=//p' | head -n1)
    [ -n "$wd_oldval" ] || wd_oldval="(file present, setting absent)"
    say "  old content:"
    printf '%s\n' "$wd_oldtxt" | sed 's/^/    /'
  else
    wd_oldval=absent
    say "  old content: absent"
  fi
  wd_new="[Service]
Environment=APERTAR_DNG_DONTNEED=$MODE"
  say "  new content:"
  printf '%s\n' "$wd_new" | sed 's/^/    /'
  if [ "$DRY" -eq 1 ]; then
    if [ -d "$DIR" ]; then say "  would reuse existing directory $DIR"; else say "  would create directory $DIR"; fi
    say "  would write $FILE"
  else
    mkdir -p -- "$DIR" || die "cannot create $DIR"
    printf '%s\n' "$wd_new" > "$FILE" || die "cannot write $FILE"
  fi
  say "  APERTAR_DNG_DONTNEED (dontneed.conf): $wd_oldval -> $MODE"
  note "APERTAR_DNG_DONTNEED (dontneed.conf): $wd_oldval -> $MODE"
}

check_environ_arm() {
  if [ "$DRY" -eq 1 ]; then return 0; fi
  ce_line=$(core_environ_value)
  say "  Core environ (MainPID $PID): ${ce_line:-APERTAR_DNG_DONTNEED not set}"
  if [ "$ce_line" != "APERTAR_DNG_DONTNEED=$MODE" ]; then
    die "THE ARM DID NOT TAKE: wanted APERTAR_DNG_DONTNEED=$MODE in Core's environment, found '${ce_line:-nothing}'. Do not score a take on this unit."
  fi
  say "  OK: Core runs with APERTAR_DNG_DONTNEED=$MODE"
}

# ---- tracefs ---------------------------------------------------------------------------------------------------------
save_trace() { # copy the buffer of the takes since the last arm before anything clears it
  st_out=/run/apertar-media/b1-trace-$(date +%H%M%S).txt   # not /dev/shm: logind RemoveIPC deletes pi's files there
  [ -d /run/apertar-media ] || { say "  /run/apertar-media missing (config/apertar-media.tmpfiles.conf): trace not saved"; return 0; }
  if [ ! -r "$TR/trace" ]; then say "  trace: not readable, not saved"; return 0; fi
  if [ "$DRY" -eq 1 ]; then say "  would save $TR/trace to $st_out"; return 0; fi
  if cat "$TR/trace" > "$st_out" && chmod 0644 "$st_out"; then
    # hand it to the user who ran sudo, so the copy to the Mac can delete it without root
    if [ -n "${SUDO_UID:-}" ] && [ -n "${SUDO_GID:-}" ]; then chown "$SUDO_UID:$SUDO_GID" "$st_out" || true; fi
    say "  trace saved: $st_out ($(wc -l < "$st_out") lines)"
    note "trace saved: $st_out"
  else
    say "  FAILED to save the trace to $st_out"
    FAIL=1
  fi
}

arm_tracefs() {
  say "tracefs ($TR):"
  if [ ! -d "$TR" ]; then
    say "  tracefs not found at $TR; trace events not armed"
    return 0
  fi
  if [ "$TRACEBUF" -eq 1 ]; then
    set_val "$TR/buffer_size_kb" "buffer_size_kb (per CPU)" "$BUF_KB"
  else
    say "  buffer_size_kb (per CPU): $(read_buf_kb), not touched (use --trace-buffer once after each reboot)"
  fi
  if [ -e "$TR/events/vb2/vb2_buf_done/filter" ]; then
    set_val "$TR/events/vb2/vb2_buf_done/filter" "event vb2/vb2_buf_done filter" "$VB2_FILTER"
  fi
  for at_e in $EVENTS; do
    if [ -d "$TR/events/$at_e" ]; then
      set_val "$TR/events/$at_e/enable" "event $at_e enable" 1
    else
      say "  missing: $at_e"
    fi
  done
  print_overruns
  save_trace
  if [ "$DRY" -eq 1 ]; then
    say "  would clear the buffer ($TR/trace)"
    note "trace: cleared"
  elif printf '' > "$TR/trace"; then
    say "  trace: cleared"
    note "trace: cleared"
  else
    say "  FAILED to clear $TR/trace"
    FAIL=1
  fi
  set_val "$TR/tracing_on" "tracing_on" 1
}

restore_tracefs() {
  say "tracefs ($TR):"
  if [ ! -d "$TR" ]; then
    say "  tracefs not found at $TR; nothing to restore there"
    return 0
  fi
  print_overruns
  save_trace
  for rt_e in $EVENTS; do
    if [ -d "$TR/events/$rt_e" ]; then
      set_val "$TR/events/$rt_e/enable" "event $rt_e enable" 0
    else
      say "  missing: $rt_e"
    fi
  done
  if [ -e "$TR/events/vb2/vb2_buf_done/filter" ]; then
    set_val "$TR/events/vb2/vb2_buf_done/filter" "event vb2/vb2_buf_done filter" 0
  fi
  if [ -r "$ORIG" ]; then
    say "  originals from $ORIG:"
    rt_on=$(orig_get tracing_on)
    rt_buf=$(orig_get buffer_size_kb)
    case "$rt_on" in
      0|1) set_val "$TR/tracing_on" "tracing_on" "$rt_on" ;;
      *) say "  tracing_on: original unknown ('$rt_on'), left as is" ;;
    esac
    case "$rt_buf" in
      ""|*[!0-9]*) say "  buffer_size_kb: original unknown ('$rt_buf'), left as is" ;;
      *) set_val "$TR/buffer_size_kb" "buffer_size_kb (per CPU)" "$rt_buf" ;;
    esac
  else
    say "  $ORIG absent: events set to 0; buffer_size_kb original unknown, left as is ($(read_buf_kb)); tracing_on left as is"
  fi
}

remove_dropin() {
  say "drop-in $FILE:"
  if [ ! -e "$FILE" ]; then
    say "  dontneed.conf: absent -> absent"
    return 0
  fi
  rd_old=$(sed -n 's/^Environment=APERTAR_DNG_DONTNEED=//p' "$FILE" | head -n1)
  [ -n "$rd_old" ] || rd_old="(file present, setting absent)"
  if [ "$DRY" -eq 1 ]; then
    say "  would remove $FILE"
  else
    [ "$FILE" = /run/systemd/system/apertar-core.service.d/dontneed.conf ] || die "internal check: unexpected drop-in path"
    rm -f -- "$FILE"
    say "  removed $FILE"
  fi
  say "  APERTAR_DNG_DONTNEED (dontneed.conf): $rd_old -> absent"
  note "APERTAR_DNG_DONTNEED (dontneed.conf): $rd_old -> absent"
}

# ---- main ------------------------------------------------------------------------------------------------------------
say "b1-arm.sh mode=$MODE dry_run=$DRY trace_buffer=$TRACEBUF   $(date '+%F %T')"

if ! command -v systemctl > /dev/null 2>&1; then
  if [ "$DRY" -eq 1 ]; then say "note: systemctl not found on this machine (dry run continues)"; else die "systemctl not found"; fi
fi

case "$MODE" in
  writer|sync)
    if [ "$DRY" -eq 0 ] && [ ! -d "$TR" ]; then
      die "$TR does not exist: no tracefs, nothing was changed"
    fi
    save_orig
    write_dropin
    restart_and_wait
    check_environ_arm
    arm_tracefs
    print_csi2
    ;;
  restore)
    if [ "$TRACEBUF" -eq 1 ]; then say "note: --trace-buffer is ignored by restore"; fi
    restore_tracefs
    remove_dropin
    restart_and_wait
    if [ "$DRY" -eq 0 ]; then
      rs_line=$(core_environ_value)
      say "  Core environ (MainPID $PID): ${rs_line:-APERTAR_DNG_DONTNEED not set (build default: sync)}"
      if [ -n "$rs_line" ]; then
        die "RESTORE INCOMPLETE: Core still has $rs_line (another drop-in or unit file sets it; look in /etc/systemd/system/apertar-core.service.d/)"
      fi
    fi
    say "  $ORIG is kept (tmpfs: it is gone at the next reboot)"
    ;;
  save)
    say "tracefs ($TR):"
    [ -d "$TR" ] || die "$TR does not exist"
    print_overruns
    save_trace
    ;;
esac

if [ "$FAIL" -ne 0 ]; then die "one or more writes failed (see FAILED lines above)"; fi
summary
