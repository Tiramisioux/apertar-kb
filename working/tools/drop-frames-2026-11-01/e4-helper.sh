#!/bin/sh
# e4-helper.sh <arm|disarm|compact0|compact-restore|smartlog|status|reboot|poweroff> [--dry-run]
#
# Root helper for the unsupervised test night (E4) of the drop-frames campaign. The camera owner installs it as a root-owned copy,
# /usr/local/libexec/apertar-e4-helper, and the sudoers file e4-sudoers lets user pi run exactly the eight mode words below.
# Preview: sh e4-helper.sh <mode> --dry-run   (prints what it would do, changes nothing, may run as a normal user)
# Without --dry-run it refuses to run as non-root (exit 1, nothing changed). Exactly one mode word; anything else prints usage, exit 2.
#
# arm
#   Refuses (exit 1, nothing changed) unless /run/apertar-media/pisp-pipeline.yaml exists, is a regular file and not a symlink,
#   is owned by uid 1000 (pi), is <= 65536 bytes and contains a line with the substring  "target": "pisp"
#   Then writes the systemd drop-in /run/systemd/system/apertar-core.service.d/zz-libcamera-e4.conf (mode 0644) with exactly
#     [Service]
#     Environment=LIBCAMERA_LOG_LEVELS=IPARPI:ERROR,RPI:0,RPiStream:0
#     Environment=LIBCAMERA_LOG_FILE=/run/apertar-media/libcamera-e4.log
#     Environment=LIBCAMERA_RPI_PISP_CONFIG_DUMP=/run/apertar-media/be-cfg.json
#     Environment=LIBCAMERA_RPI_CONFIG_FILE=/run/apertar-media/pisp-pipeline.yaml
#   (zz- so it sorts after /etc/.../libcamera-log.conf and its LIBCAMERA_LOG_LEVELS wins, as evening 3's zz-libcamera-log.conf)
#   and runs `systemctl daemon-reload`. It does NOT restart apertar-core (the next `apertar-b1-arm sync` does).
#   Prints the file, the md5sum of the YAML and every `grep -n num_cfe_config_queue` match of it.
# disarm
#   `rm -f` of that one drop-in, daemon-reload, `systemctl restart apertar-core`, waits up to 30 s for active with a non-zero
#   MainPID, prints every LIBCAMERA_ line of /proc/<MainPID>/environ (expect only LIBCAMERA_LOG_LEVELS=IPARPI:ERROR from /etc).
#   Does not touch /run/apertar-media.
# compact0
#   Saves /proc/sys/vm/compaction_proactiveness to /run/e4-compact.orig only if that file does not exist yet, writes 0.
# compact-restore
#   Writes back the value in /run/e4-compact.orig (absent: writes the kernel default 20 and says so). The .orig file is kept.
# smartlog   `nvme smart-log /dev/nvme0`
# status     read-only: drop-in, compaction_proactiveness, /run/e4-compact.orig, Core MainPID + its LIBCAMERA_ environ lines, the YAML's ls -l
# reboot     `systemctl reboot`        poweroff   `systemctl poweroff`
#
# What it writes (nothing else): /run/systemd/system/apertar-core.service.d/ (directory), .../zz-libcamera-e4.conf,
#   /run/e4-compact.orig, /proc/sys/vm/compaction_proactiveness. The only deletion is `rm -f` of zz-libcamera-e4.conf, in disarm.
#   It restarts apertar-core (disarm only) and reboots/powers off via systemctl (reboot/poweroff only).
#   No /etc, no /boot, no /proc/irq, no defaults-pisp, no installed libcamera YAML, no other sysctl.
#
# How to undo it by hand:
#   sudo rm -f /run/systemd/system/apertar-core.service.d/zz-libcamera-e4.conf
#   sudo systemctl daemon-reload && sudo systemctl restart apertar-core
#   echo <old value> | sudo tee /proc/sys/vm/compaction_proactiveness     (old value is in /run/e4-compact.orig; default 20)
#   A reboot also undoes all of it (/run and /proc/sys are not persistent).
set -eu
umask 022

UNIT=apertar-core
DIR=/run/systemd/system/apertar-core.service.d
FILE=$DIR/zz-libcamera-e4.conf
YAML=/run/apertar-media/pisp-pipeline.yaml
COMPACT=/proc/sys/vm/compaction_proactiveness
ORIG=/run/e4-compact.orig
NVME=/dev/nvme0
DROPIN="[Service]
Environment=LIBCAMERA_LOG_LEVELS=IPARPI:ERROR,RPI:0,RPiStream:0
Environment=LIBCAMERA_LOG_FILE=/run/apertar-media/libcamera-e4.log
Environment=LIBCAMERA_RPI_PISP_CONFIG_DUMP=/run/apertar-media/be-cfg.json
Environment=LIBCAMERA_RPI_CONFIG_FILE=/run/apertar-media/pisp-pipeline.yaml"

MODE=""
DRY=0
PID=0

say() { printf '%s\n' "$*"; }
usage() { say "usage: sh e4-helper.sh <arm|disarm|compact0|compact-restore|smartlog|status|reboot|poweroff> [--dry-run]"; }

for a in "$@"; do
  case "$a" in
    arm|disarm|compact0|compact-restore|smartlog|status|reboot|poweroff) [ -z "$MODE" ] || { usage; exit 2; }; MODE=$a ;;
    --dry-run) [ "$DRY" -eq 0 ] || { usage; exit 2; }; DRY=1 ;;
    *) usage; exit 2 ;;
  esac
done
[ -n "$MODE" ] || { usage; exit 2; }

if [ "$(id -u)" -ne 0 ] && [ "$DRY" -eq 0 ]; then
  say "e4-helper.sh: must run as root (sudo apertar-e4-helper $MODE), or use --dry-run to preview. Nothing was changed."
  exit 1
fi

die() { say ""; say "!!!!!! e4-helper.sh: $* !!!!!!"; exit 1; }

# run_cmd <cmd...>: run a command (or say that it would run).
run_cmd() {
  if [ "$DRY" -eq 1 ]; then say "  would run: $*"; return 0; fi
  say "  run: $*"
  "$@" || die "command failed: $*"
}

# First line of a file, or "?" if unreadable.
first_line() {
  l=""
  if [ -r "$1" ]; then IFS= read -r l < "$1" || true; fi
  [ -n "$l" ] || l="?"
  printf '%s\n' "$l"
}

file_uid() { stat -c %u "$1" 2>/dev/null || stat -f %u "$1" 2>/dev/null || printf '?\n'; }
file_md5() { { md5sum "$1" 2>/dev/null || md5 -r "$1" 2>/dev/null; } | awk '{print $1}' || true; }

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

print_environ() { # print_environ <pid>: every LIBCAMERA_ line of that process's environment
  case "$1" in ""|0|*[!0-9]*) say "  (no MainPID)"; return 0 ;; esac
  if [ ! -r "/proc/$1/environ" ]; then say "  /proc/$1/environ: not readable"; return 0; fi
  pe_out=$(tr '\0' '\n' < "/proc/$1/environ" 2>/dev/null | grep '^LIBCAMERA_' || true)
  if [ -n "$pe_out" ]; then printf '%s\n' "$pe_out" | sed 's/^/  /'; else say "  (no LIBCAMERA_ lines)"; fi
}

# ---- arm -------------------------------------------------------------------------------------------------------------
check_yaml() { # sets BAD (newline-separated reasons); empty BAD = all checks pass
  BAD=""
  if [ ! -e "$YAML" ] && [ ! -L "$YAML" ]; then BAD="$YAML does not exist"; return 0; fi
  if [ -L "$YAML" ]; then BAD="$YAML is a symlink"; return 0; fi
  if [ ! -f "$YAML" ]; then BAD="$YAML is not a regular file"; return 0; fi
  cy_uid=$(file_uid "$YAML")
  [ "$cy_uid" = 1000 ] || BAD="$BAD
$YAML is owned by uid $cy_uid, not 1000"
  cy_size=$(wc -c < "$YAML" 2>/dev/null | tr -d ' ' || true)
  case "$cy_size" in ""|*[!0-9]*) BAD="$BAD
$YAML size unreadable" ;; *) [ "$cy_size" -le 65536 ] || BAD="$BAD
$YAML is $cy_size bytes, more than 65536" ;; esac
  if [ -r "$YAML" ]; then
    grep -qF '"target": "pisp"' "$YAML" || BAD="$BAD
$YAML has no line containing \"target\": \"pisp\""
  else
    BAD="$BAD
$YAML is not readable"
  fi
  BAD=$(printf '%s' "$BAD" | sed '1{/^$/d;}')
}

do_arm() {
  say "YAML checks ($YAML):"
  check_yaml
  if [ -n "$BAD" ]; then
    printf '%s\n' "$BAD" | sed 's/^/  FAIL: /'
    if [ "$DRY" -eq 0 ]; then die "refusing to arm, nothing was changed"; fi
    say "  (dry run: a real run would refuse here, exit 1, and write nothing; below is what it would write if the checks passed)"
  else
    say "  OK: regular file, not a symlink, uid 1000, <= 65536 bytes, has \"target\": \"pisp\""
  fi
  say "drop-in $FILE:"
  if [ -f "$FILE" ]; then ar_old=present; else ar_old=absent; fi
  if [ -f "$FILE" ]; then say "  old content:"; sed 's/^/    /' "$FILE"; else say "  old content: absent"; fi
  say "  new content:"
  printf '%s\n' "$DROPIN" | sed 's/^/    /'
  if [ "$DRY" -eq 1 ]; then
    if [ -d "$DIR" ]; then say "  would reuse existing directory $DIR"; else say "  would create directory $DIR (mode default, umask 022)"; fi
    say "  would write $FILE (mode 0644)"
  else
    mkdir -p -- "$DIR" || die "cannot create $DIR"
    printf '%s\n' "$DROPIN" > "$FILE" || die "cannot write $FILE"
    chmod 0644 "$FILE" || die "cannot chmod $FILE"
  fi
  say "  zz-libcamera-e4.conf: $ar_old -> armed"
  run_cmd systemctl daemon-reload
  say "  $UNIT is NOT restarted (the next apertar-b1-arm sync does that)"
  if [ "$DRY" -eq 1 ]; then
    say "  would print the file, the md5sum of $YAML and the grep -n num_cfe_config_queue matches"
  else
    say "file $FILE:"; sed 's/^/  /' "$FILE"
  fi
  say "YAML md5sum: $(if [ -f "$YAML" ]; then file_md5 "$YAML"; else printf 'unreadable (no %s)' "$YAML"; fi)"
  say "YAML num_cfe_config_queue matches (grep -n):"
  am=$(grep -n num_cfe_config_queue "$YAML" 2>/dev/null || true)
  if [ -n "$am" ]; then printf '%s\n' "$am" | sed 's/^/  /'; else say "  (none, or $YAML not readable)"; fi
}

# ---- disarm ----------------------------------------------------------------------------------------------------------
do_disarm() {
  OLDPID=$(systemctl show -p MainPID --value "$UNIT" 2>/dev/null || true)
  if [ -e "$FILE" ]; then
    if [ "$DRY" -eq 1 ]; then say "  would remove $FILE"; else rm -f -- "$FILE"; say "  removed $FILE"; fi
    say "  zz-libcamera-e4.conf: present -> absent"
  else
    say "  zz-libcamera-e4.conf: absent -> absent"
  fi
  run_cmd systemctl daemon-reload
  run_cmd systemctl restart "$UNIT"
  if [ "$DRY" -eq 1 ]; then
    say "  would wait up to 30 s for: systemctl is-active $UNIT = active and a non-zero MainPID"
    say "  would print every LIBCAMERA_ line of /proc/<MainPID>/environ (expect only LIBCAMERA_LOG_LEVELS=IPARPI:ERROR from /etc)"
    return 0
  fi
  wait_core || die "$UNIT is not active with a MainPID within 30 s of the restart (state: $(systemctl is-active "$UNIT" 2>/dev/null || true))"
  say "  $UNIT active, MainPID ${OLDPID:-?} -> $PID"
  say "  LIBCAMERA_ lines in Core's environment (MainPID $PID):"
  print_environ "$PID"
}

# ---- compaction ------------------------------------------------------------------------------------------------------
set_compact() { # set_compact <new>
  sc_old=$(first_line "$COMPACT")
  if [ "$DRY" -eq 1 ]; then
    say "  would set vm.compaction_proactiveness: $sc_old -> $1"
    return 0
  fi
  if printf '%s\n' "$1" > "$COMPACT"; then
    say "  vm.compaction_proactiveness: $sc_old -> $(first_line "$COMPACT")"
  else
    die "cannot write $1 to $COMPACT"
  fi
}

do_compact0() {
  if [ -e "$ORIG" ]; then
    say "  $ORIG exists ($(first_line "$ORIG")), keeping the first original"
  elif [ "$DRY" -eq 1 ]; then
    say "  would write $ORIG with: $(first_line "$COMPACT")"
  else
    first_line "$COMPACT" > "$ORIG" || die "cannot write $ORIG"
    say "  saved original to $ORIG: $(first_line "$ORIG")"
  fi
  set_compact 0
}

do_compact_restore() {
  if [ -r "$ORIG" ]; then
    cr_val=$(first_line "$ORIG")
    case "$cr_val" in ""|"?"|*[!0-9]*) die "$ORIG holds '$cr_val', not a number; nothing changed" ;; esac
  else
    cr_val=20
    say "  orig file absent, wrote the kernel default 20"
  fi
  set_compact "$cr_val"
  say "  $ORIG is kept"
}

# ---- status ----------------------------------------------------------------------------------------------------------
do_status() {
  say "drop-in $FILE:"
  if [ -f "$FILE" ]; then sed 's/^/  /' "$FILE"; else say "  absent"; fi
  say "vm.compaction_proactiveness: $(first_line "$COMPACT")"
  if [ -f "$ORIG" ]; then say "$ORIG: $(first_line "$ORIG")"; else say "$ORIG: absent"; fi
  st_pid=$(systemctl show -p MainPID --value "$UNIT" 2>/dev/null || true)
  say "$UNIT MainPID: ${st_pid:-?}"
  say "LIBCAMERA_ lines in its environment:"
  print_environ "$st_pid"
  say "ls -l $YAML:"
  { ls -l "$YAML" 2>&1 || true; } | sed 's/^/  /'
}

# ---- main ------------------------------------------------------------------------------------------------------------
say "e4-helper.sh mode=$MODE dry_run=$DRY   $(date '+%F %T')"

if ! command -v systemctl > /dev/null 2>&1; then
  if [ "$DRY" -eq 1 ]; then say "note: systemctl not found on this machine (dry run continues)"; else die "systemctl not found"; fi
fi

case "$MODE" in
  arm) do_arm ;;
  disarm) do_disarm ;;
  compact0) do_compact0 ;;
  compact-restore) do_compact_restore ;;
  smartlog) run_cmd nvme smart-log "$NVME" ;;
  status) do_status ;;
  reboot) run_cmd systemctl reboot ;;
  poweroff) run_cmd systemctl poweroff ;;
esac
