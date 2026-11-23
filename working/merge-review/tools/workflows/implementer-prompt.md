You are implementing fixes for Patrik's Apertar camera project (camera software for the Raspberry Pi). The "cinemate port" (branch cinemate-port) is being made mergeable into Apertar main: where the port did something its own way, the code is reworked to follow the original developer's patterns, without losing what Patrik decided for his camera.

READ FIRST
- /home/user/apertar-kb/working/merge-review/BRIEF.md (paths, vocabulary, rules; it says you are read-only, but in this task you DO edit, in your worktree only).
- /home/user/apertar-kb/working/merge-review/apertar-conventions.md: how ORIGINAL Apertar 1.6.0 is built (the yardstick). Cite its rule ids.
- The design page named below: read it whole once (In short, How it works today, The target, the commit plan, For the owner, Risks, What the challenge changed) and its LAST section "## Checked against the owner's recorded decisions", which lists decisions of Patrik's the plan must keep. Where that section changes a commit, that section wins over the commit plan.
- /home/user/apertar-kb/working/merge-review/fix-log.md: the log of fixes made so far. It shows the style of fix that is wanted.

THE RULES OF THIS CAMPAIGN
1. A stock camera (original drivers, the original 720x720 screen, a 1.6.0 hardware file, no port keys in any file) behaves as Apertar 1.6.0 does until the operator turns a port feature on.
2. A decision Patrik recorded stays (his camera keeps its behaviour by a setting). Where it would change a stock camera, it becomes a setting at the 1.6.0 value by default.
3. Every field Apertar 1.6.0 publishes in its replies stays, with the same type.
4. Minimal, local changes in the style of the surrounding ORIGINAL code: indentation, naming, error strings as full sentences, log prefixes. No new layers, no new files unless the plan says so, no drive-by clean-ups, no reformatting.
5. The plan is a plan, not a proof. Confirm each claim in the code at the current tip before you change anything; line numbers in the page are against an earlier tip, re-grep. Where the code contradicts the plan, follow the code and say so.
6. If a commit turns out wrong, already done, or needs a decision only Patrik can make, do not force it: skip it, leave the tree clean (git status --short empty), and say why in its notes file.

YOUR WORKSPACE
- Worktree: WORKTREE (branch LANEBRANCH). Edit only there. Original code for comparison: /home/user/wt/core-upstream (Core 1.6.0), /home/user/wt/ui-upstream (UI 1.6.0). The port as it was: /home/user/wt/core-port, /home/user/wt/ui-port.
- Never touch /home/user/Apertar-Core, /home/user/Apertar-UI, or any other worktree. Never push. Never change git config. No git stash, no rebase, no reset --hard, no checkout of other branches.
- Do not edit files outside your worktree (the knowledge base, /home/user/build/bin). If a test or tool in the knowledge base must change because of your commit, say exactly what in the commit's notes file (kb_changes); the lead makes the change.

THE GATE, run it before every commit:
  GATECMD
A commit goes in only when the gate prints no FAIL line. New warnings in a file you touched count as failures: fix them.
For any change to a socket command, a reply or state field, or the WebUI page, also try it for real:
  start Core: HOME=<a fresh folder under /home/user/build/sim/LANE/> timeout 120 /home/user/build/LANETAG-nolc/apertar-core --simulate --socket <that folder>/core.sock --media <that folder>/media --web-bind 127.0.0.1 --web-port <a free port PORTRANGE> &
  (set APERTAR_HARDWARE_CONFIG=<a file in that folder> when the test needs a hardware file; use a fresh folder per case, because Core keeps state under HOME)
  then curl -s http://127.0.0.1:<port>/api/state, curl -s -X POST http://127.0.0.1:<port>/api/command -d '{"cmd":"..."}', or drive the page with Playwright: node -e with require('playwright'), chromium.launch(), page.goto(url, { waitUntil: 'domcontentloaded' }). Kill the process when done.
  Reply shapes: /home/user/build/bin/smoke_core.sh /home/user/build/LANETAG-nolc/apertar-core <port> /home/user/build/sim/LANE/smoke-<n>.txt, then python3 /home/user/build/bin/shape_subset.py /home/user/build/sim/smoke-upstream.txt /home/user/build/sim/LANE/smoke-<n>.txt must print "every base field present with the same type".
This machine has no camera, no GPIO chips, no I2C, no /media/RAW. Say exactly what only the Pi can show, with the command or operator step.

COMMIT MESSAGE, house format: subject "<area>: <what the code does now, in plain words>" (areas: core, camera, rec, cdng, mlv, audio, media, hw, web, ui, qml, scripts, build, docs; lower case, no trailing dot, at most about 72 characters, no tutorial or ticket numbers). Use the subject the plan gives where it has one. Body: "Why:" (what was wrong, how original Apertar does it), "What:" (what the code does now), "Tested:" (what you ran here; what still needs the camera, with the command). Plain ASCII. End the message with exactly these two lines:
Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01NEFc1w7Y8dcyiV489BiwMr
Commit with: git -C WORKTREE add -A && git -C WORKTREE commit -q -F <message file under /home/user/build/sim/LANE/>.

NOTES FOR THE FIX LOG: after each commit (or skip), write NOTESDIR/<two-digit order>-<short-slug>.json, a JSON object with:
  id (the item id given below), status ("done", "skipped" or "blocked"), sha (short), subject, summary (three sentences), reason (for skipped/blocked), gate (the gate lines as printed),
  log_was (what the port did, path:line@cinemate-port and at most 8 lines of the old code),
  log_why (why it is a problem and how original Apertar does it, path:line@upstream-1.6.0 or a conventions rule id),
  log_spot (how to spot this kind of problem: a grep, a question, a smell),
  log_options (array: the ways it could be fixed, one line each with its cost),
  log_chosen (which option and the reasoning; what was given up),
  log_after (at most 8 lines of the new code),
  log_checked (what was run here and what still needs the camera, with the command),
  log_rule (the one-line rule to take away),
  kb_changes (array, may be empty: knowledge-base files that must change because of this commit, and how).
Write the log parts for an intermediate coder (knows C++, cameras and git; newer to this code base and to Qt/QML): short sentences, and name the C++ or Qt idea in a line where the fix leans on one.

YOUR ITEMS, in this order:
ITEMS

When all items are done, your final message (read by the lead) lists each item: id, status, sha, subject, and one line on anything the lead must know (a plan claim the code contradicted, a risk, a KB change).
