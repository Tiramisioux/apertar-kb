# e3-collect.sh cut <unit> | clips <unit> | delete <unit>   (as pi, on the Pi, never during a take)
# cut:    from /run/apertar-media/e3-<unit>.out's OFF<n> lines, cut libcamera-e3.log into <unit>-<take>.log per take
#         (bytes OFFk..OFFk+1, the take names from the "===== <take>" lines), and copy be-cfg.json to be-cfg-<unit>.json
#         with its mtime printed.
# clips:  print each take's "recording clip:" folder.
# delete: rm -rf exactly those folders (each must be /media/RAW/cDNG_<digits/underscores>_C<4 digits>, a directory).
set -eu
R=/run/apertar-media; MODE=$1; U=$2; OUT=$R/e3-$U.out; LC=$R/libcamera-e3.log
[ -f "$OUT" ] || { echo "no $OUT"; exit 1; }
clips(){ grep -oE '^recording clip: /media/RAW/[^ ]+' "$OUT" | awk '{print $3}'; }
case "$MODE" in
  cut)
    offs=$(grep -E '^OFF[0-9]+ [0-9]+$' "$OUT" | awk '{print $2}' | tr '\n' ' ')
    takes=$(grep -E '^===== ' "$OUT" | awk '{print $2}' | tr '\n' ' ')
    set -- $offs; i=0
    for t in $takes; do
      a=$1; b=$2; shift
      tail -c +$((a + 1)) "$LC" | head -c $((b - a)) > "$R/$U-$t.log"
      echo "cut $U-$t.log bytes $a..$b ($(wc -l < "$R/$U-$t.log") lines; Using tuning file lines: $(grep -c 'Using tuning file' "$R/$U-$t.log"))"
      i=$((i + 1))
    done
    if [ -f "$R/be-cfg.json" ]; then cp -p "$R/be-cfg.json" "$R/be-cfg-$U.json"; echo "be-cfg-$U.json mtime $(stat -c %y "$R/be-cfg-$U.json")"; else echo "no be-cfg.json"; fi
    ;;
  clips) clips ;;
  delete)
    for d in $(clips); do
      case "$d" in /media/RAW/cDNG_*_C[0-9][0-9][0-9][0-9]) ;; *) echo "REFUSED (pattern): $d"; continue ;; esac
      echo "$d" | grep -qE '^/media/RAW/cDNG_[0-9_]+_C[0-9]{4}$' || { echo "REFUSED (chars): $d"; continue; }
      [ -d "$d" ] || { echo "not a directory (already gone?): $d"; continue; }
      rm -rf -- "$d" && echo "deleted $d"
    done
    sync; df -h /media/RAW | awk 'NR==2{print "fill: "$3" used of "$2" ("$5")"}'
    ;;
  *) echo "usage: e3-collect.sh cut|clips|delete <unit>"; exit 2 ;;
esac
