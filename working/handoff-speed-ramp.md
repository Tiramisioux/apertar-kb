# Handoff: speed ramping on cinemate-port (T31, T32), then value lists (T33) and the mode ladder (T34)

For: the next `apertar-dev` session in VS Code on the Mac. Written 2026-10-27 at the end of a cloud session. Read this, then
the pages it points to, before touching anything.

## 1. Where things stand

| Item | State |
| --- | --- |
| KB | GitHub `main` `d65b2ef` plus the export `apertar-kb-speed-ramp-2026-10-27.zip` (install: its `INSTALL.md`) |
| Core | `cinemate-port` on GitHub at `6ae70b5`. The three Core patches (T31, T32 ×2) apply with plain `git am` on `7a545d9` and on `6ae70b5`, checked in the cloud |
| UI | `cinemate-port` on GitHub at `dc471c1`. The two UI patches (T32) apply with plain `git am`; the whole UI built on the cloud host with Qt 6.4.2 |
| T31 speed ramping | written, moved to `cinemate-port`; not on GitHub `cinemate-port` (`6ae70b5`). Point 1 checks the Pi |
| T32 speed ramping from every control | written; not on GitHub. Point 1 checks the Pi |
| T33 value lists + build `max_fps` | requirements and decisions only (`working/ramp-ladder/README.md` §3.1); no tutorial, no patch |
| T34 mode ladder | requirements, facts and two designs (`working/ramp-ladder/README.md` §3.2); no tutorial, no patch |
| 4K Clear HDR 16-bit | 25 fps is the accepted maximum (Patrik, 2026-10-27); T32 makes Core and both UIs stop there |

What the Pi runs today is not known from the cloud. Check first: `ssh apertar 'git -C ~/ApertarCore log --oneline -1; git -C ~/ApertarUI log --oneline -1'`.

The cloud session could not compile `CameraController.cpp` (libcamera) or run anything on a Pi. What Patrik did on the Pi is
not recorded in this export.

## 2. Rules (unchanged, keep them)

- `working/handoff-T26-T30.md` §2 and `working/mac-driven-loop.md`: Claude on the Mac, the Pi over `ssh apertar`, build on the
  Pi only (`cmake --build ~/ApertarCore-build -j2`, `cmake --build ~/ApertarUI/build -j2`), never while a take runs.
- **Tutor mode.** Patrik types every change from the tutorial. The patches are references. Claude edits only when he says so.
  **No prediction questions** unless he asks.
- **Patrik runs** `sudo`, service restarts, reboots, `/boot/firmware`, drop-ins, DKMS. Give him exact commands.
- **Nothing is pushed** unless Patrik asks, and then only from the Mac.
- Commits: `<area>: <imperative>`, Why/What, `Tested:` line, Co-Authored-By trailer. A fork-log row for every Core/UI commit.
  Tutorial progress: `tutorial.py log`.
- Before each tutorial: `python3 tutorials/tutorial.py refs T31` (or `T32`). T31's refs are exact on a tree with T31 only. After
  T32 they show MOVED +5, because the 25 fps cap adds five lines above them.

## 3. The points, in order

Take Patrik through one at a time. Finish each with his result in the right log before starting the next.

**0. Install the export.** Follow `INSTALL.md` from the zip: check the four replaced files against `d65b2ef`, copy `kb/.`, look
at `git status`, commit when he is happy. Move the two inbox notes (T31, T32) into Obsidian and add them to the learning-path
note. The older `apertar-kb-additions-2026-10-27.zip` is superseded; do not install it.

**1. T31 and T32: check the Pi, then do what is missing.** Neither is on GitHub `cinemate-port`. Check what the Pi has,
read-only:

```bash
ssh apertar 'git -C ~/ApertarCore log --oneline -8; git -C ~/ApertarUI log --oneline -5'
ssh apertar 'grep -c fpsRampEnabled ~/ApertarCore/src/camera/CameraController.cpp'        # T31: 11
ssh apertar 'grep -c "normalizeRawBitDepth(rawBitDepth) == 16" ~/ApertarCore/src/camera/CameraController.cpp'  # T32 cap: 1
ssh apertar 'grep -c settingsSpeedRamp ~/ApertarCore/src/web/WebControlPage.cpp'          # T32 WebUI block: 17
ssh apertar 'grep -c m_fpsRamp ~/ApertarUI/src/ApertarControlBridge.cpp'                  # T32 touch UI picker: 2
```

Counts of 0 mean the tutorial is not done. Take him through T31 (tutorial `20261026210000 CINEMATE APERTAR T31 speed-ramping`,
steps 4.1-4.8, build, §5 on the Pi), then T32 (tutorial `20261027213000 CINEMATE APERTAR T32 speed-ramp-every-control`, steps
4.1-4.10, build Core and UI, §5). The patches in `working/patches/` are the reference if a step will not build. After each:
- add fork-log rows for the commits;
- set the tutorial's status in both indexes and in the learning-path note;
- log `tutorial.py` progress.

Three questions only the Pi can answer, from T31 §5; write the answers into `lessons/hardware-log.md`:
- does MLV App play a ramped MLV at the header rate (slow motion) or at the real per-frame times?
- the measured `lag_frames=` against the expected N+2, and whether N+6 frames of grace is enough;
- whether a 2× `FrameDurationLimits` step on a running stream passes without a frame hiccup.

**2. T33: value lists and the build's maximum.** Write the tutorial first, then he types it. The decisions so far are in
`working/ramp-ladder/README.md` §3.1:
- ISO, shutter-angle, FPS and WB lists in `~/.config/CinePi/UI.conf` `[General]`, the file Core and the touch UI already share;
- a Cinemate-style chip editor in the WebUI;
- Core's pots and buttons and both UIs read the same lists;
- `[camera] max_fps=50` in `apertar-hardware.conf`;
- Core publishes `fps_max`, and the UIs cut their lists at it.

Keep the WebUI "Camera settings" pane (FPS / ISO / shutter pills) as the quick-access menu in the field: it shows his lists, it
is not replaced. Ask him before building whether he wants Cinemate's "free" stepping too; it is not decided.

**3. T34: the mode ladder.** His ladder for this build: 4K Clear HDR 16-bit from the lowest rate up to 25, then 4K SDR 12-bit up
to 50. The editor: drag and drop the activated modes into order, an optional threshold per rung, a toggle that makes Core
honour it.

Before writing anything, present design A (switch between takes, Cinemate's rule) and B (switch mid-take with a clip split),
with the critique in `working/ramp-ladder/README.md` §3.2 and the reader reports beside it. He chooses.

Measure first on the Pi, because the numbers decide A or B:
- **4K SDR 12-bit at 50.** Core caps 4K SDR at 30 today and the probe says 60. Lift the cap on a test branch, then take
  uncompressed, lossy DNG 3:1 and MLV at 50 with `takes.sh`. 4K 12-bit uncompressed at 50 needs about 622 MB/s; the NVMe gave
  437 MB/s on Gen 2.
- **The cost of a switch.** Time a Clear HDR 16 → SDR 12 switch in preview: journal timestamps from the `set_clear_hdr`
  command to the first frame.

## 4. Read first

- `INSTALL.md` (in the zip): what the export contains and how to install it.
- `working/ramp-ladder/README.md`: Patrik's ten requests from 2026-10-27, what is done, and T33/T34 decisions and open questions.
- `working/ramp-answer.md` §0 and §3: what speed ramping does to the DNGs, timecode, WAV and phase lock. It cites the cloud
  commit `d4ad539`; T31 cites `cinemate-port`.
- `working/patches/README.md`, section "Speed-ramp series": the five patches and their order.
- `working/ramp-ladder/r1-core.md` "What a ladder implementation must touch" and "Risks", and `r2-cinemate.md` §0 and "Port to
  Apertar" (both before T34).
- `working/research-30fps-answer.md`: why 25 is the Clear HDR 16-bit ceiling.
