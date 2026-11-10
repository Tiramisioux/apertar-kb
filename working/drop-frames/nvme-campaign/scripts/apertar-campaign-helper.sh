#!/bin/sh
# apertar-campaign-helper.sh <word> [AUDIO_MS] [--dry-run]
#
# Root helper for the NVMe 4K campaign (apertar-kb working/drop-frames/nvme-campaign/plan.md, build list row D). Patrik installs a
# root-owned copy as /usr/local/libexec/apertar-campaign-helper; the sudoers file campaign-sudoers lets user pi run exactly the
# words below (INSTALL.md). Pattern: working/tools/drop-frames-2026-11-01/e4-helper.sh.
# Preview: sh apertar-campaign-helper.sh <word> --dry-run   (prints what it would do, changes nothing, may run as a normal user)
# Without --dry-run it refuses to run as non-root (exit 1, nothing changed). Exactly one word; anything else prints usage, exit 2.
#
# Two kinds of words.
# UNATTENDED (sudoers NOPASSWD: the detached runner calls them with `sudo -n`; read-only, reversible, or fstrim):
#   smartlog       `nvme smart-log /dev/nvme0 -o json` (plain output if the json form fails). Read-only.
#   status         read-only: the campaign drop-in (content or absent), Core's MainPID and its LIBCAMERA_ / APERTAR_ environment
#                  lines, ls -l and md5 of /run/apertar-media/pisp-pipeline.yaml, `systemctl is-enabled` of each campaign timer,
#                  vm.compaction_proactiveness and the saved original.
#   fsck-ro        `fsck.exfat -n <device behind /media/RAW>` (check only, never repairs); prints its exit code.
#   audio-usb      read-only: `lsusb -t`, and per ALSA card its id, its USB bus/device (usbbus) and its sysfs path (which xHCI).
#   fstrim         `fstrim -v /media/RAW`, only if /media/RAW is an exfat mount (refuses otherwise). Irreversible on freed blocks;
#                  safe only because the runner deletes nothing but its own database-keyed clips.
#   timers-mask    for each of fstrim.timer apt-daily.timer apt-daily-upgrade.timer man-db.timer logrotate.timer: a missing unit
#                  is reported and skipped; the others are recorded as active/inactive in /run/nvme-campaign-timers.active (only
#                  if that file does not exist yet, so a second mask keeps the first record), then `systemctl mask --runtime --now`.
#                  Prints is-enabled per timer. A runtime mask is cleared by any reboot.
#   timers-unmask  `systemctl unmask --runtime` for the same list, then `systemctl start` of only those timers the record says
#                  were active before the mask (no record: none are started, and it says so); removes the record; is-enabled.
# INTERACTIVE ONLY (refuse with exit 1 unless stdin is a terminal; sudoers WITHOUT NOPASSWD, so Patrik's password is the guard
# and the runner's `sudo -n` fails closed):
#   arm [AUDIO_MS] Refuses (nothing changed) unless /home/pi/Tuning-Files/pipeline/pisp-depth4.yaml is a regular file, not a
#                  symlink, with md5 88929ca34bc8e4e8d4ab5ffaac1e2b64 (FE Config queue depth 4). Copies it to
#                  /run/apertar-media/pisp-pipeline.yaml (mode 0644; via a temp file in that folder and a rename, so a symlink
#                  there is replaced, never followed), checks the copy's md5, writes the drop-in
#                    /run/systemd/system/apertar-core.service.d/zz-nvme-campaign.conf  (mode 0644) with exactly
#                    [Service]
#                    Environment=LIBCAMERA_RPI_CONFIG_FILE=/run/apertar-media/pisp-pipeline.yaml
#                  plus, only when AUDIO_MS (a whole number 100-4000) is given, the line
#                    Environment=APERTAR_AUDIO_BUFFER_MS=<AUDIO_MS>
#                  then `systemctl daemon-reload`, `systemctl restart apertar-core`, waits up to 30 s for active + a MainPID,
#                  prints Core's LIBCAMERA_ / APERTAR_ environment lines and FAILS (exit 1) unless LIBCAMERA_RPI_CONFIG_FILE is
#                  among them and names a file with the depth 4 md5 (or APERTAR_AUDIO_BUFFER_MS differs from AUDIO_MS when
#                  given). Since 2026-11-06 /home/pi/start-apertar-core.sh exports LIBCAMERA_RPI_CONFIG_FILE itself (the
#                  Tuning-Files depth 4 path); that export wins over the drop-in, so Core shows that path: accepted, with a note.
#   disarm         `rm -f` of that one drop-in, daemon-reload, restart apertar-core, wait, print the environment. The /run YAML
#                  copy is left in place (harmless without the drop-in; gone at the next boot).
#   restart-core   restart apertar-core, wait, print the environment.
#   compact0       saves vm.compaction_proactiveness to /run/nvme-campaign-compact.orig (only if that file does not exist), writes 0.
#   compact-restore writes back the saved value (absent: the kernel default 20, and says so); the .orig file is kept.
#   reboot         `systemctl reboot`        poweroff   `systemctl poweroff`
#
# What it writes (nothing else): /run/apertar-media/pisp-pipeline.yaml (and its temp file, renamed or removed),
#   /run/systemd/system/apertar-core.service.d/ (directory) and .../zz-nvme-campaign.conf, /run/nvme-campaign-timers.active,
#   /run/nvme-campaign-compact.orig, /proc/sys/vm/compaction_proactiveness, runtime timer masks (systemctl, under /run).
#   Deletions: `rm -f` of zz-nvme-campaign.conf (disarm), of /run/nvme-campaign-timers.active (timers-unmask), of a leftover temp file.
#   Restarts apertar-core (arm, disarm, restart-core); trims /media/RAW (fstrim); reboots / powers off (reboot / poweroff).
#   No /etc, no /boot, no defaults-pisp, no installed libcamera files, no other sysctl.
#
# How to undo it by hand:
#   sudo rm -f /run/systemd/system/apertar-core.service.d/zz-nvme-campaign.conf
#   sudo systemctl daemon-reload && sudo systemctl restart apertar-core
#   sudo systemctl unmask --runtime fstrim.timer apt-daily.timer apt-daily-upgrade.timer man-db.timer logrotate.timer
#   sudo systemctl start fstrim.timer man-db.timer logrotate.timer        (those that were active; see /run/nvme-campaign-timers.active)
#   echo <old value> | sudo tee /proc/sys/vm/compaction_proactiveness   (old value in /run/nvme-campaign-compact.orig; default 20)
#   A reboot also undoes all of it (/run and /proc/sys are not persistent). An fstrim cannot be undone.
set -eu
umask 022
PATH=/usr/sbin:/usr/bin:/sbin:/bin
export PATH

UNIT=apertar-core
DIR=/run/systemd/system/apertar-core.service.d
FILE=$DIR/zz-nvme-campaign.conf
SRC=/home/pi/Tuning-Files/pipeline/pisp-depth4.yaml
SRC_MD5=88929ca34bc8e4e8d4ab5ffaac1e2b64
YDIR=/run/apertar-media
YAML=$YDIR/pisp-pipeline.yaml
MEDIA=/media/RAW
NVME=/dev/nvme0
TIMERS="fstrim.timer apt-daily.timer apt-daily-upgrade.timer man-db.timer logrotate.timer"
TREC=/run/nvme-campaign-timers.active
COMPACT=/proc/sys/vm/compaction_proactiveness
ORIG=/run/nvme-campaign-compact.orig

WORDS="smartlog|status|fsck-ro|audio-usb|fstrim|timers-mask|timers-unmask|arm|disarm|restart-core|compact0|compact-restore|reboot|poweroff"
MODE=""
DRY=0
AUDIO=""
PID=0

say() { printf '%s\n' "$*"; }
usage() { say "usage: sh apertar-campaign-helper.sh <$WORDS> [AUDIO_MS, arm only] [--dry-run]"; }

for a in "$@"; do
  case "$a" in
    smartlog|status|fsck-ro|audio-usb|fstrim|timers-mask|timers-unmask|arm|disarm|restart-core|compact0|compact-restore|reboot|poweroff)
      [ -z "$MODE" ] || { usage; exit 2; }; MODE=$a ;;
    --dry-run) [ "$DRY" -eq 0 ] || { usage; exit 2; }; DRY=1 ;;
    *)
      if [ "$MODE" = arm ] && [ -z "$AUDIO" ]; then
        case "$a" in ""|*[!0-9]*) usage; exit 2 ;; esac
        AUDIO=$a
      else
        usage; exit 2
      fi ;;
  esac
done
[ -n "$MODE" ] || { usage; exit 2; }
if [ -n "$AUDIO" ]; then
  if [ "$AUDIO" -lt 100 ] || [ "$AUDIO" -gt 4000 ]; then say "AUDIO_MS must be a whole number from 100 to 4000"; exit 2; fi
fi

if [ "$(id -u)" -ne 0 ] && [ "$DRY" -eq 0 ]; then
  say "apertar-campaign-helper: must run as root (sudo /usr/local/libexec/apertar-campaign-helper $MODE), or use --dry-run to preview. Nothing was changed."
  exit 1
fi

die() { say ""; say "!!!!!! apertar-campaign-helper: $* !!!!!!"; exit 1; }

# run_cmd <cmd...>: run a command (or say that it would run); a failure ends the helper.
run_cmd() {
  if [ "$DRY" -eq 1 ]; then say "  would run: $*"; return 0; fi
  say "  run: $*"
  "$@" || die "command failed: $*"
}

first_line() {
  l=""
  # head, not `read`: a procfs sysctl file gives EOF to any read past offset 0 (e4-helper, 2026-11-04)
  if [ -r "$1" ]; then l=$(head -n 1 "$1" 2>/dev/null) || true; fi
  [ -n "$l" ] || l="?"
  printf '%s\n' "$l"
}

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

core_env() { # core_env <pid>: Core's LIBCAMERA_ and APERTAR_ environment lines (empty if none or unreadable)
  case "$1" in ""|0|*[!0-9]*) return 0 ;; esac
  [ -r "/proc/$1/environ" ] || return 0
  tr '\0' '\n' < "/proc/$1/environ" 2>/dev/null | grep -E '^(LIBCAMERA_|APERTAR_)' || true
}

print_environ() {
  case "$1" in ""|0|*[!0-9]*) say "  (no MainPID)"; return 0 ;; esac
  if [ ! -r "/proc/$1/environ" ]; then say "  /proc/$1/environ: not readable"; return 0; fi
  pe_out=$(core_env "$1")
  if [ -n "$pe_out" ]; then printf '%s\n' "$pe_out" | sed 's/^/  /'; else say "  (no LIBCAMERA_ or APERTAR_ lines)"; fi
}

need_tty() {
  if [ -t 0 ]; then return 0; fi
  if [ "$DRY" -eq 1 ]; then
    say "  NOTE: '$MODE' is interactive only: a real run would refuse here (stdin is not a terminal), exit 1, nothing changed."
    say "  (dry run continues to show what it would do from a terminal)"
    return 0
  fi
  die "'$MODE' is interactive only: run it yourself from a terminal (stdin is not a terminal). Nothing was changed."
}

restart_and_show() {
  OLDPID=$(systemctl show -p MainPID --value "$UNIT" 2>/dev/null || true)
  run_cmd systemctl restart "$UNIT"
  if [ "$DRY" -eq 1 ]; then
    say "  would wait up to 30 s for: systemctl is-active $UNIT = active and a non-zero MainPID"
    say "  would print every LIBCAMERA_ / APERTAR_ line of /proc/<MainPID>/environ"
    return 0
  fi
  wait_core || die "$UNIT is not active with a MainPID within 30 s of the restart (state: $(systemctl is-active "$UNIT" 2>/dev/null || true))"
  say "  $UNIT active, MainPID ${OLDPID:-?} -> $PID"
  say "  LIBCAMERA_ / APERTAR_ lines in Core's environment (MainPID $PID):"
  print_environ "$PID"
}

# ---- arm -------------------------------------------------------------------------------------------------------------
do_arm() {
  need_tty
  say "source YAML $SRC:"
  BAD=""
  if [ ! -e "$SRC" ] && [ ! -L "$SRC" ]; then BAD="$SRC does not exist"
  elif [ -L "$SRC" ]; then BAD="$SRC is a symlink"
  elif [ ! -f "$SRC" ]; then BAD="$SRC is not a regular file"
  else
    sm=$(file_md5 "$SRC")
    [ "$sm" = "$SRC_MD5" ] || BAD="$SRC has md5 '$sm', not $SRC_MD5 (the recorded FE depth 4 file)"
  fi
  [ -d "$YDIR" ] || BAD="${BAD:+$BAD; }$YDIR does not exist (Core makes it at start)"
  if [ -n "$BAD" ]; then
    say "  FAIL: $BAD"
    [ "$DRY" -eq 1 ] || die "refusing to arm, nothing was changed"
    say "  (dry run: a real run would refuse here, exit 1, and write nothing; below is what it would do if the checks passed)"
  else
    say "  OK: regular file, md5 $sm; $YDIR exists"
    say "  num_cfe_config_queue lines:"; { grep -n num_cfe_config_queue "$SRC" || true; } | sed 's/^/    /'
  fi
  DROPIN="[Service]
Environment=LIBCAMERA_RPI_CONFIG_FILE=$YAML"
  [ -z "$AUDIO" ] || DROPIN="$DROPIN
Environment=APERTAR_AUDIO_BUFFER_MS=$AUDIO"
  say "YAML copy $YAML:"
  if [ -e "$YAML" ] || [ -L "$YAML" ]; then say "  old: $(ls -l "$YAML" 2>&1) md5 $(file_md5 "$YAML")"; else say "  old: absent"; fi
  if [ "$DRY" -eq 1 ]; then
    say "  would copy $SRC to a temp file in $YDIR, chmod 0644, rename it to $YAML, check its md5 = $SRC_MD5"
  else
    tmp=$(mktemp "$YDIR/.pisp-pipeline.XXXXXX") || die "cannot make a temp file in $YDIR"
    if ! cat "$SRC" > "$tmp" || ! chmod 0644 "$tmp" || ! mv -f "$tmp" "$YAML"; then
      rm -f "$tmp"; die "cannot write $YAML"
    fi
    ym=$(file_md5 "$YAML")
    [ "$ym" = "$SRC_MD5" ] || die "$YAML has md5 '$ym' after the copy, not $SRC_MD5 (the drop-in was NOT written)"
    say "  new: $(ls -l "$YAML") md5 $ym"
  fi
  say "drop-in $FILE:"
  if [ -f "$FILE" ]; then say "  old content:"; sed 's/^/    /' "$FILE"; else say "  old content: absent"; fi
  say "  new content:"; printf '%s\n' "$DROPIN" | sed 's/^/    /'
  if [ "$DRY" -eq 1 ]; then
    if [ -d "$DIR" ]; then say "  would reuse existing directory $DIR"; else say "  would create directory $DIR"; fi
    say "  would write $FILE (mode 0644)"
  else
    mkdir -p -- "$DIR" || die "cannot create $DIR"
    printf '%s\n' "$DROPIN" > "$FILE" || die "cannot write $FILE"
    chmod 0644 "$FILE" || die "cannot chmod $FILE"
  fi
  run_cmd systemctl daemon-reload
  restart_and_show
  [ "$DRY" -eq 0 ] || return 0
  env_now=$(core_env "$PID")
  # /home/pi/start-apertar-core.sh exports LIBCAMERA_RPI_CONFIG_FILE itself since 2026-11-06 (the depth 4 file under
  # Tuning-Files): a script export wins over the drop-in's Environment=. Either path is armed if its md5 is the depth 4 one.
  cf=$(printf '%s\n' "$env_now" | sed -n 's/^LIBCAMERA_RPI_CONFIG_FILE=//p' | head -n 1)
  [ -n "$cf" ] || die "ARM FAILED: LIBCAMERA_RPI_CONFIG_FILE is NOT in Core's environment (MainPID $PID)"
  cm=$(file_md5 "$cf")
  [ "$cm" = "$SRC_MD5" ] || die "ARM FAILED: Core's LIBCAMERA_RPI_CONFIG_FILE=$cf has md5 '$cm', not $SRC_MD5"
  [ "$cf" = "$YAML" ] || say "  note: Core uses $cf (exported by /home/pi/start-apertar-core.sh, which wins over the drop-in); same md5, depth 4"
  if [ -n "$AUDIO" ]; then
    printf '%s\n' "$env_now" | grep -qx "APERTAR_AUDIO_BUFFER_MS=$AUDIO" \
      || die "ARM FAILED: APERTAR_AUDIO_BUFFER_MS=$AUDIO is NOT in Core's environment (MainPID $PID)"
  fi
  say "ARMED: Core (MainPID $PID) runs with the FE depth 4 YAML${AUDIO:+ and a ${AUDIO} ms audio ring}"
}

do_disarm() {
  need_tty
  if [ -e "$FILE" ]; then
    if [ "$DRY" -eq 1 ]; then say "  would remove $FILE"; else rm -f -- "$FILE"; say "  removed $FILE"; fi
    say "  zz-nvme-campaign.conf: present -> absent"
  else
    say "  zz-nvme-campaign.conf: absent -> absent"
  fi
  run_cmd systemctl daemon-reload
  restart_and_show
  say "  $YAML is left in place (harmless without the drop-in; gone at the next boot)"
}

# ---- timers ----------------------------------------------------------------------------------------------------------
unit_exists() { systemctl list-unit-files --no-legend "$1" 2>/dev/null | grep -q .; }

show_timers() {
  say "timers (is-enabled / is-active):"
  for t in $TIMERS; do
    say "  $t: $(systemctl is-enabled "$t" 2>/dev/null || true) / $(systemctl is-active "$t" 2>/dev/null || true)"
  done
}

do_timers_mask() {
  fails=""
  if [ -e "$TREC" ]; then
    say "  $TREC exists (first mask's record kept):"; sed 's/^/    /' "$TREC"
    rec_new=0
  else
    rec_new=1
    if [ "$DRY" -eq 1 ]; then say "  would write $TREC with each timer's is-active state"; else : > "$TREC" || die "cannot write $TREC"; fi
  fi
  for t in $TIMERS; do
    if ! unit_exists "$t"; then say "  $t: no such unit, skipped"; continue; fi
    act=$(systemctl is-active "$t" 2>/dev/null || true)
    if [ "$rec_new" -eq 1 ] && [ "$DRY" -eq 0 ]; then printf '%s %s\n' "$t" "${act:-unknown}" >> "$TREC"; fi
    if [ "$DRY" -eq 1 ]; then say "  would run: systemctl mask --runtime --now $t   (now: $act)"; continue; fi
    say "  run: systemctl mask --runtime --now $t   (was: $act)"
    systemctl mask --runtime --now "$t" || fails="$fails $t"
  done
  show_timers
  [ -z "$fails" ] || die "mask failed for:$fails"
}

do_timers_unmask() {
  fails=""
  for t in $TIMERS; do
    if ! unit_exists "$t"; then say "  $t: no such unit, skipped"; continue; fi
    if [ "$DRY" -eq 1 ]; then say "  would run: systemctl unmask --runtime $t"; continue; fi
    say "  run: systemctl unmask --runtime $t"
    systemctl unmask --runtime "$t" || fails="$fails $t"
  done
  if [ -r "$TREC" ]; then
    # shellcheck disable=SC2013   # one unit name per line, no spaces
    for t in $(awk '$2 == "active" {print $1}' "$TREC"); do
      if [ "$DRY" -eq 1 ]; then say "  would run: systemctl start $t   (active before the mask)"; continue; fi
      say "  run: systemctl start $t   (active before the mask)"
      systemctl start "$t" || fails="$fails start:$t"
    done
    if [ "$DRY" -eq 1 ]; then say "  would remove $TREC"; else rm -f -- "$TREC"; say "  removed $TREC"; fi
  else
    say "  $TREC absent: no record of which timers were active, none started (a reboot starts the enabled ones)"
  fi
  show_timers
  [ -z "$fails" ] || die "failed:$fails"
}

# ---- compaction ------------------------------------------------------------------------------------------------------
set_compact() {
  sc_old=$(first_line "$COMPACT")
  if [ "$DRY" -eq 1 ]; then say "  would set vm.compaction_proactiveness: $sc_old -> $1"; return 0; fi
  if printf '%s\n' "$1" > "$COMPACT"; then
    say "  vm.compaction_proactiveness: $sc_old -> $(first_line "$COMPACT")"
  else
    die "cannot write $1 to $COMPACT"
  fi
}

do_compact0() {
  need_tty
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
  need_tty
  if [ -r "$ORIG" ]; then
    cr_val=$(first_line "$ORIG")
    case "$cr_val" in ""|"?"|*[!0-9]*) die "$ORIG holds '$cr_val', not a number; nothing changed" ;; esac
  else
    cr_val=20
    say "  orig file absent, writing the kernel default 20"
  fi
  set_compact "$cr_val"
  say "  $ORIG is kept"
}

# ---- read-only and trim words ----------------------------------------------------------------------------------------
do_smartlog() {
  if [ "$DRY" -eq 1 ]; then say "  would run: nvme smart-log $NVME -o json   (plain output if that fails)"; return 0; fi
  nvme smart-log "$NVME" -o json 2>/dev/null && return 0
  say "  (json form failed; plain output)"
  nvme smart-log "$NVME" || die "nvme smart-log $NVME failed"
}

do_status() {
  say "drop-in $FILE:"
  if [ -f "$FILE" ]; then sed 's/^/  /' "$FILE"; else say "  absent"; fi
  st_pid=$(systemctl show -p MainPID --value "$UNIT" 2>/dev/null || true)
  say "$UNIT: $(systemctl is-active "$UNIT" 2>/dev/null || true), MainPID ${st_pid:-?}"
  say "LIBCAMERA_ / APERTAR_ lines in its environment:"
  print_environ "$st_pid"
  say "YAML $YAML:"
  if [ -e "$YAML" ] || [ -L "$YAML" ]; then
    say "  $(ls -l "$YAML" 2>&1)"
    ym=$(file_md5 "$YAML")
    say "  md5 $ym ($( [ "$ym" = "$SRC_MD5" ] && echo "= the recorded depth 4 file" || echo "NOT $SRC_MD5"))"
  else
    say "  absent"
  fi
  say "start script /home/pi/start-apertar-core.sh, LIBCAMERA_RPI_CONFIG_FILE lines:"
  { grep -n 'LIBCAMERA_RPI_CONFIG_FILE' /home/pi/start-apertar-core.sh 2>/dev/null || say "  (none, or not readable)"; } | sed 's/^/  /'
  show_timers
  if [ -f "$TREC" ]; then say "$TREC:"; sed 's/^/  /' "$TREC"; else say "$TREC: absent"; fi
  say "vm.compaction_proactiveness: $(first_line "$COMPACT")"
  if [ -f "$ORIG" ]; then say "$ORIG: $(first_line "$ORIG")"; else say "$ORIG: absent"; fi
}

do_fsck_ro() {
  dev=$(findmnt -no SOURCE "$MEDIA" 2>/dev/null || true)
  case "$dev" in
    /dev/*) ;;
    *) [ "$DRY" -eq 1 ] || die "no block device mounted on $MEDIA (findmnt: '$dev')"
       say "  FAIL: no block device mounted on $MEDIA (findmnt: '$dev'); a real run would stop here, exit 1"; dev="<device of $MEDIA>" ;;
  esac
  say "  device $dev ($(findmnt -no FSTYPE "$MEDIA" 2>/dev/null || true)) on $MEDIA"
  if [ "$DRY" -eq 1 ]; then say "  would run: fsck.exfat -n $dev   (check only, no repair) and print its exit code"; return 0; fi
  say "  run: fsck.exfat -n $dev"
  set +e
  fsck.exfat -n "$dev"
  rc=$?
  set -e
  say "fsck.exfat -n exit code: $rc"
  return 0
}

do_audio_usb() {
  if command -v lsusb > /dev/null 2>&1; then say "lsusb -t:"; lsusb -t 2>&1 | sed 's/^/  /' || true; else say "lsusb: not found"; fi
  say "ALSA cards:"
  found=0
  for c in /proc/asound/card[0-9]*; do
    [ -d "$c" ] || continue
    found=1
    n=${c#/proc/asound/card}
    id=$(first_line "$c/id")
    bus="-"; [ -r "$c/usbbus" ] && bus=$(first_line "$c/usbbus")
    sp=$(readlink -f "/sys/class/sound/card$n/device" 2>/dev/null || printf '?')
    say "  card$n id=$id usbbus=$bus sysfs=$sp"
  done
  [ "$found" -eq 1 ] || say "  (no /proc/asound/card*)"
}

do_fstrim() {
  fst=$(findmnt -no FSTYPE "$MEDIA" 2>/dev/null || true)
  if [ "$fst" != exfat ]; then
    [ "$DRY" -eq 1 ] || die "$MEDIA is not an exfat mount (fstype '$fst'); refusing to trim"
    say "  FAIL: $MEDIA is not an exfat mount (fstype '$fst'); a real run would refuse here, exit 1"
  fi
  run_cmd fstrim -v "$MEDIA"
}

# ---- main ------------------------------------------------------------------------------------------------------------
say "apertar-campaign-helper mode=$MODE${AUDIO:+ audio_ms=$AUDIO} dry_run=$DRY   $(date '+%F %T')"

if ! command -v systemctl > /dev/null 2>&1; then
  if [ "$DRY" -eq 1 ]; then say "note: systemctl not found on this machine (dry run continues)"; else die "systemctl not found"; fi
fi

case "$MODE" in
  smartlog) do_smartlog ;;
  status) do_status ;;
  fsck-ro) do_fsck_ro ;;
  audio-usb) do_audio_usb ;;
  fstrim) do_fstrim ;;
  timers-mask) do_timers_mask ;;
  timers-unmask) do_timers_unmask ;;
  arm) do_arm ;;
  disarm) do_disarm ;;
  restart-core) need_tty; restart_and_show ;;
  compact0) do_compact0 ;;
  compact-restore) do_compact_restore ;;
  reboot) need_tty; run_cmd systemctl reboot ;;
  poweroff) need_tty; run_cmd systemctl poweroff ;;
esac
