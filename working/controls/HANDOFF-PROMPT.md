# Prompt for Claude in VS Code: the Controls project (GPIO dropdown and method assigning)

Paste the block below into Claude in VS Code.

---

A cloud session designed the Controls project for me: Cinemate's GPIO dropdown and method assigning, ported in Apertar's own
style, with a system-controlled config file, my I2C hardware and the NeoRotary-on-the-CFE-hat fix. It is in the KB on GitHub,
branch `cloud/speed-ramp-2026-10-27`, folder `working/controls/`. Get it into my KB clone first (files only, no merge):

```bash
cd ~/Documents/Apertar/apertar-kb
git fetch origin cloud/speed-ramp-2026-10-27
git checkout origin/cloud/speed-ramp-2026-10-27 -- working/controls
```

Then read, in this order:
1. `working/controls/README.md` (what each file is) and `working/controls/plan-summary.md` (one page).
2. `working/controls/design-controls.md` (v2), at least §0 short answer, §2.4 recommendation, §3 file/commands/state, §4
   WebUI, §5 the hardware catalog with my rig, §6 the plan, §8 measurements, §9.2 my questions.
3. `working/controls/changes-from-critique.md` where you doubt a decision.
4. The sketch, `working/controls/sketch/`: build and run its test on the Pi (the command is in README.md) against my Core
   tree, `~/ApertarCore/src`. It was written against Core `0296ed1`; tell me if my tree has moved.

What I want from you, in this order:
1. Go through the questions in §9.2 (Q1-Q23) with me, one at a time, with the design's default and what changes if I say
   otherwise. Record my answers in `working/controls/decisions.md`.
2. Run the read-only measurements M1-M8 (§8) with me on the Pi, as pi. M4 (I2C reads) only with Core stopped, as the design
   says; I run the stop and start. Log the results where §8 says.
3. Then turn the plan into tutorials, starting with T36 (one action vocabulary), in the KB format
   (`tutorials/README.md`), and take me through them one at a time. T36-T40 alone give the NeoRotary fix done by software.
4. Keep `config.txt` mine: the design never writes it; it only tells me what to run.

Work as my tutor with the apertar-dev rules: I type the changes; no prediction questions; I run sudo, restarts and reboots
(give me the exact commands); builds only on the Pi; nothing is pushed unless I ask.
