# Prompt for Claude Sonnet in VS Code: the Controls project (GPIO dropdown and method assigning)

Paste the block below into Claude (Sonnet) in VS Code on the Mac. Claude writes the code; Patrik tests, confirms and gives
feedback at every check-in. Written for Sonnet: exact sections to read, hard rules, a check-in after every step.

---

You are building the Apertar Controls project with me. A cloud session designed it: Cinemate's GPIO dropdown and method
assigning, ported in Apertar's own style, with one system-controlled config file (`~/apertar-hardware.conf`, written only by
Core), an easy editor and a text editor on the same file, my I2C hardware, and the NeoRotary 4 on the CFE hat's bus 1 done by
software. Nothing is built yet. **You write the code.** I test on the camera, confirm, and give feedback at every check-in.

## Step 0. Get the design (files only, no merge)

```bash
cd ~/Documents/Apertar/apertar-kb
git fetch origin cloud/speed-ramp-2026-10-27
git checkout origin/cloud/speed-ramp-2026-10-27 -- working/controls
```

## How we work (my loop: `working/mac-driven-loop.md`, `working/sync.md`, `working/build-deploy.md`)

- You run on the Mac and reach the Pi over ssh (`ssh apertar`). Do not run tools that load the Pi (no VS Code server or
  language server there).
- You write code in the Mac clones (`~/Documents/Apertar/Apertar-Core`, `…/Apertar-UI`) on a work branch `controls`, made
  from the branch the Pi runs. Bring that branch over first and show me what you got:
  `git -C ~/Documents/Apertar/Apertar-Core fetch ssh://apertar/home/pi/ApertarCore cinemate-port:cinemate-port`
  (the same for Apertar-UI from `~/ApertarUI`), then `git switch -c controls cinemate-port` in each.
- To get a step onto the Pi: `apertar_push_to_pi.sh <core|ui> controls --dry-run` (the apertar-dev skill's scripts folder,
  next to `apertar_publish.sh`), show me the output, and run it for real only after I say yes.
- Build on the Pi: `ssh apertar 'cmake --build ~/ApertarCore-build -j2'` (UI: `~/ApertarUI/build`). Never while a take runs:
  check `get_state` first.
- I run every `sudo`: service restarts, installs, reboots. You give me the exact command and wait for my output. Nobody
  edits `/boot/firmware/config.txt` except me; the design never writes it.
- Nothing is pushed to GitHub unless I ask.

## Hard rules

1. Small steps. A step is one tutorial row of the plan (T36, T37, …) or a part of one. Never start the next step before I
   confirm the last one.
2. Never invent a file path, line number or function name. Find every code site in the Mac clone with the design's search
   string (`grep -n`). The design was written against Core `0296ed1` and touch UI `5aab7e2`; the trees have moved since
   (T33/T34). If a search string is missing or found twice, stop and tell me; do not guess.
3. If the design and the code disagree, show both and ask which way to go.
4. Match the surrounding code: naming, comment density, style. No drive-by refactors.
5. Label what you say about the code CONFIRMED (you saw it), PROBABLE (derived; say how) or UNCONFIRMED.
6. A failing build or test stops the step: show me the error, fix it, run it again.
7. Ask when unsure. Do not fill gaps with guesses.

## The check-in (after every step, always this shape)

1. **What changed:** files and line counts (`git diff --stat`), and the key parts of the diff in a few lines each.
2. **Checks you ran:** the host or Pi build result, the sketch or unit tests, read-only Pi checks over ssh (`python3 ~/apertar-kb/working/tools/core.py get_state`,
   `curl -s http://127.0.0.1:8000/api/state`), each with its real output.
3. **What I should test on the camera:** numbered, concrete (which knob to turn, which page to open, what I should see), and
   the restart command if one is needed.
4. **Questions** for me, if any.
Then stop and wait. When I report back: fix what I found, show the fix the same way, and ask again. Commit the step on
`controls` (a clear message in the repo's style) only after I confirm it works. Then write or update the step's note in
`tutorials/inbox/` in the KB format (`tutorials/README.md`): what changed, why, how it was checked, how to undo; its tutor
block's `ref` and `check` lines must pass `python3 ~/Documents/Apertar/apertar-kb/tutorials/tutorial.py refs <T>`.

## What to read (in this order, only these parts first)

All paths under `working/controls/`. Line ranges are for `design-controls.md` v2 (1,886 lines).

1. `README.md` (the file list) and `plan-summary.md` (one page, read all of it).
2. `design-controls.md`:
   - §0 Short answer, lines 69-141
   - §2.4 Recommendation and §2.5, lines 383-413
   - §3.1-§3.5 the file, the schema, the vocabulary, who writes, the commands, lines 416-687
   - §4.1 the Controls panel and §4.4 the I2C devices card, lines 898-1012 and 1044-1113
   - §5 the hardware catalog with my rig, lines 1146-1232
   - §6 the plan file by file, lines 1233-1377
   - §8 measurements M1-M8, lines 1675-1782
   - §9.2 my questions Q1-Q23, lines 1813-1840
3. When a step needs it: §3.6-§3.8 live apply, refusals, lost changes (688-895), §7 tutorial outlines and the tutor blocks
   (1378-1674), §9.1 risks (1785-1812).
4. `changes-from-critique.md`, the critiques and the reader reports `r1`-`r4`: only to answer a question.

## Phase 1. My decisions (before any code)

Go through Q1-Q23 from §9.2 with me, ONE question per message: the question, the design's default, and what changes if I say
otherwise. Start with Q1 (keep the path), Q3 (apply hand edits automatically), Q4 (hold and double press at 800/350 ms),
Q5 (save during a take) and Q7 (turn off the INA219), then the rest in order. Write each answer to
`working/controls/decisions.md` as a table (Q, my answer, date). When all are answered, show me the table and stop.

## Phase 2. Measurements on the Pi (read-only)

Run M1-M8 from §8 over ssh, one at a time, exactly as §8 writes them, and show me each output:
- M4 (I2C reads of the NeoRotary, the hat, the IMU, the TMP117) runs ONLY with Core stopped: reading the seesaw while Core
  polls it can fire phantom knob turns. I stop and start Core; give me the commands.
- Anything that needs `sudo` (some journal reads): give me the command, I run it.
- M8 belongs after T39; skip it now.
- After each: say what it changes in the design (§2.5), and ask before logging it in `lessons/hardware-log.md` (Q13).
Then summarize what changed and stop.

## Phase 3. The sketch

`working/controls/sketch/` (`hardware/ActionCatalog.hpp`, `hardware/HardwareConfigText.hpp`, `controls_test.cpp`; 78 checks
pass in the cloud against Core `0296ed1`). Build and run its test against the `controls` branch (the command is in
`README.md`; `-I` points at the clone's `src`), on the Mac if it builds there, else on the Pi. Show me the result. If a check
fails because the tree moved, stop and show which.

## Phase 4. Build T36-T40, one step at a time

Follow §6 for the code sites and §7 for the order of each tutorial, starting with T36 (one action vocabulary:
`ActionCatalog.hpp` replaces the three `normalizeSingleAction` copies, plus `list_actions`). The sketch's headers are the
starting point for T36 and T37. After each step, the check-in above. T36-T40 give the NeoRotary fix done by software; ask
before starting T41-T45.
