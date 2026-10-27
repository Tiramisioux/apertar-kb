# Prompt for Claude in VS Code (paste this, and attach the zip)

I've attached `apertar-kb-speed-ramp-2026-10-27.zip`, an export from a cloud session. Unzip it to `~/Downloads/`. Read its
`INSTALL.md` first, then `kb/working/handoff-speed-ramp.md`, then the files that handoff lists under "Read first".

Then take me through the points in section 3 of the handoff, in order and one at a time:

- 0: install the export into `~/Documents/Apertar/apertar-kb`;
- 1: T31 (speed ramping in Core) and T32 (the WebUI Speed Ramp block, the touch UI picker, the 25 fps ceiling). Check on
  the Pi what is already in, then take me through what is missing;
- 2: T33, the value lists and `max_fps=50`;
- 3: T34, the mode ladder: present designs A and B first, and let me choose.

Work as my tutor with the `apertar-dev` rules in the handoff's section 2:

- I type the changes; the patches in `working/patches/` are references.
- No prediction questions.
- I run sudo, restarts and reboots; give me the exact commands.
- Build only on the Pi.
- Nothing is pushed unless I ask.

Before each step, tell me in two or three lines what it changes, the first command, and the risk. After each step, log the
result where the handoff says.
