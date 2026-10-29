# Prompt for Claude in VS Code: the Playback project (WebUI playback like the touch UI)

Paste the block below into Claude in VS Code.

---

A cloud session designed the Playback project for me: playback in the WebUI that looks and behaves like the touch UI's Clip
Browser and Clip Viewer, with Cinemate's browser mechanics. It is in the KB on GitHub, branch `cloud/speed-ramp-2026-10-27`,
folder `working/playback/`. Get it into my KB clone first (files only, no merge):

```bash
cd ~/Documents/Apertar/apertar-kb
git fetch origin cloud/speed-ramp-2026-10-27
git checkout origin/cloud/speed-ramp-2026-10-27 -- working/playback
```

Then read, in this order:
1. `working/playback/README.md` (what each file is) and `working/playback/plan-summary.md` (one page).
2. `working/playback/design-playback.md` (v2): the short answer, the decision, the touch-UI-to-WebUI element map, Core's
   routes and the yield-to-recording rule, the plan, the measurements, and the questions.
3. `working/playback/r2-apertar-ui-player.md`: the touch UI's player, which the WebUI copies.
4. `working/playback/changes-from-critique.md` where you doubt a decision.
5. The sketch, `working/playback/sketch/`: build lines are at the top of each `.cpp`. It was written against Core `eb9cc39`
   and touch UI `d8098d0`; tell me if my trees have moved.

What I want from you, in this order:
1. Go through my questions with me, one at a time, with the design's default and what changes if I say otherwise. First
   Q1 (~5-8 fps for lossless 4K), Q19 (the frame-number clock on both screens), Q21 (downloads during a take), Q22 (the
   touch UI in T54) and Q9 (which Cinemate options; suggested O1, O4, O5, O10). Record my answers in
   `working/playback/decisions.md`.
2. T46, the measurements on my Pi, before any code.
3. Then turn the plan into tutorials T46-T54 in the KB format (`tutorials/README.md`) and take me through them one at a
   time. It comes after the controls project (T36-T45) unless I say otherwise (Q17).

Work as my tutor with the apertar-dev rules: I type the changes; no prediction questions; I run sudo, restarts and reboots
(give me the exact commands); builds only on the Pi; nothing is pushed unless I ask.
