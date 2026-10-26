# Prompt: start the Apertar ↔ Cinemate port tutorials (paste into Claude Code on the Pi)

```text
/apertar-dev Work with me on the Cinemate-port tutorials T22 to T30, one at a time, as a tutor.
I type and build every change myself. Do NOT apply the reference patches
(~/apertar-kb/working/patches/ and ~/apertar-cinemate-port-2026-10-26/03-core-patches/) and do not
edit, build or restart anything for me; give hints before answers.

Setup, in this order:
1. Read ~/apertar-kb/llm/README.md and llm/tutoring.md section 7 (tutor sessions), then
   ~/apertar-kb/working/cinemate-lessons.md.
2. Run `python3 ~/apertar-kb/tutorials/tutorial.py list` and `... refs T22`. Tell me which line refs moved.
3. The work stays OFF GitHub. Check `git -C ~/ApertarCore status -sb`; if there is no local branch
   `clearhdr-fixes`, tell me the one command to create it from main (f60e301). I run it.
   Publish must never move that branch.

Then start T22 (measure first, no code change): `tutorial.py show T22`, quote step 1 only, ask for my
prediction, let me run it, verify with `tutorial.py check`, log with `tutorial.py log`. After T22 ask
whether to continue with T23. T26 (driver) is independent; T23 to T30 build on each other in order.
```
