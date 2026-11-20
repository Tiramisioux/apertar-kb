#!/bin/bash
# Save everything that only lives in this container into the knowledge base and push it:
#  - the review's helper scripts and agent workflows (tools/)
#  - every lane commit that is not yet on the improvement branch, as patches (lanes/<lane>/)
# then commit and push the KB. Usage: save_all.sh "<commit subject>"
MR=/home/user/apertar-kb/working/merge-review
mkdir -p $MR/tools/bin $MR/tools/workflows
cp /home/user/build/bin/*.sh /home/user/build/bin/*.py /home/user/build/bin/*.js $MR/tools/bin/ 2>/dev/null
for f in /home/user/build/review/*.js; do case "$(basename $f)" in _*) ;; *) cp "$f" $MR/tools/workflows/;; esac; done
save_lane() {   # <lane worktree> <integration worktree> <folder>
  local wt=$1 main=$2 dir=$MR/lanes/$3
  rm -rf "$dir"; mkdir -p "$dir"
  [ -d "$wt" ] || return
  # commits of the lane whose change is not on the integration branch (compared by patch id)
  local n=0
  for sha in $(git -C "$wt" cherry "$(git -C "$main" rev-parse HEAD)" HEAD | awk '$1=="+"{print $2}'); do
    n=$((n+1)); git -C "$wt" format-patch -q -1 --start-number $n -o "$dir" "$sha"
  done
  [ -n "$(git -C "$wt" status --porcelain)" ] && git -C "$wt" diff > "$dir/uncommitted-work.diff"
  [ -z "$(ls -A "$dir")" ] && rmdir "$dir"
  echo "  $3: $n patches"
}
save_lane /home/user/wt/lane-core1 /home/user/wt/core-work core-bugs
save_lane /home/user/wt/lane-hdr   /home/user/wt/core-work core-command-plane
save_lane /home/user/wt/lane-core3 /home/user/wt/core-work core-hardware-inputs
save_lane /home/user/wt/lane-core4 /home/user/wt/core-work core-camera-modes
save_lane /home/user/wt/lane-ui1   /home/user/wt/ui-work   ui-touch-ui
cd /home/user/apertar-kb && git add -A working/merge-review && if git diff --cached --quiet; then echo "  KB: nothing new"; else
git commit -q -m "${1:-merge-review: save point}

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01NEFc1w7Y8dcyiV489BiwMr" && git push -q origin claude/awesome-pasteur-qzsiow 2>&1 | tail -1; echo "  KB pushed: $(git log --oneline -1 | cut -c1-80)"; fi
