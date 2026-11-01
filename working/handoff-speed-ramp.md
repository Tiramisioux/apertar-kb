# Handoff: speed ramping on cinemate-port (T31, T32), then value lists (T33) and the mode ladder (T34)

For: the next `apertar-dev` session in VS Code on the Mac. Written 2026-10-27 at the end of a cloud session. Read this, then
the pages it points to, before touching anything.

## 1. Where things stand

| Item | State |
| --- | --- |
| KB | GitHub `main` `7886e5b` plus the export `apertar-kb-speed-ramp-2026-10-27.zip` (install: its `INSTALL.md`) |
| Core | `cinemate-port` on GitHub at `3c4f07d`. The three Core patches (T31, T32 ×2) apply with plain `git am` on `b606c4f` and on `3c4f07d`, checked in the cloud |
| UI | `cinemate-port` on GitHub at `dc471c1`. The two UI patches (T32) apply with plain `git am`; the whole UI built on the cloud host with Qt 6.4.2 |
| T31 speed ramping | written, moved to `cinemate-port`; not on GitHub `cinemate-port` (`3c4f07d`). Point 1 checks the Pi |
| T32 speed ramping from every control | written; not on GitHub. Point 1 checks the Pi |
| T33 value lists + build `max_fps` | requirements and decisions only (`working/ramp-ladder/README.md` §3.1); no tutorial, no patch |
| T34 mode ladder | requirements, facts and two designs (`working/ramp-ladder/README.md` §3.2); no tutorial, no patch |
| 4K Clear HDR 16-bit | 25 fps is the accepted maximum (Patrik, 2026-10-27); T32 makes Core (its clamp and its PCF pot/button list) and both UIs stop there |

> [!note] 2026-10-28 (VS Code session): point 0 done (KB `60d7d3d`, synced to the Pi). Point 1 check: neither T31 nor T32
> on the Pi (every count 0). The Pi had `temp:` commits on top (Core 6 from `55e7ba9`, UI 6 from `d5a1bf2`); Patrik moved them
> to the local branch `cinemate-port-temp` and reset Pi `cinemate-port` to Core `bda2066`, UI `2d27c46`. All five reference
> patches apply cleanly there, so T31/T32 are typed as written. **Hazard if the temp work comes back:** `d084ed4`/`0bac3db` put
> a Clear HDR 16 → SDR 12 switch in `setFps` through `applySettingsLocked`, which has no take check; with T31 a ramp past 25 in
> Clear HDR 16 would reconfigure the camera mid-take. It must refuse or cap in a take (design A). The running binaries are
> still the temp build until the next Core/UI build.

What the Pi runs today is not known from the cloud. Check first: `ssh apertar 'git -C ~/ApertarCore log --oneline -1; git -C ~/ApertarUI log --oneline -1'`.

The cloud session could not compile `CameraController.cpp` (libcamera) or run anything on a Pi. What Patrik did on the Pi is
not recorded in this export.

> [!todo] 2026-10-28: **listen to the experimental stretched WAV** (`C0034` was deleted; `C0022_stretched.wav` exists, a small 25 → 30 → 25
> ramp; a new 1080p 25 → 50 → 25 take is the better test). Length and pitch are measured; the sound is not checked yet. `ramp-ladder/README.md` 19.

> [!todo] 2026-10-28: the open, unconfirmed items of the port are in `working/unverified-speed-ramp-port.md`.

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
  T32 they show MOVED: +5 in `CameraController.cpp` (the 25 fps cap adds five lines above them) and +1 in `ApertarCoreApp.cpp`
  (one comment line in Core's PCF list).

## 3. The points, in order

Take Patrik through one at a time. Finish each with his result in the right log before starting the next.

**0. Install the export.** Follow `INSTALL.md` from the zip: check the four replaced files against `7886e5b`, copy `kb/.`, look
at `git status`, commit when he is happy. Move the two inbox notes (T31, T32) into Obsidian and add them to the learning-path
note. If he wants the patches on the Pi, sync the KB when he says so (`working/sync.md`: `pull pi main`, `push pi main` from
the Mac); the Pi's `~/apertar-kb` is behind and has none of the five patches until then. The older
`apertar-kb-additions-2026-10-27.zip` is superseded; do not install it.

**1. T31 and T32: check the Pi, then do what is missing.** Neither is on GitHub `cinemate-port`. Check what the Pi has,
read-only:

```bash
ssh apertar 'git -C ~/ApertarCore log --oneline -8; git -C ~/ApertarUI log --oneline -5'
ssh apertar 'grep -c "fpsSpeedRamp\b" ~/ApertarCore/src/camera/CameraController.cpp'        # T31: 11
ssh apertar 'grep -c "FPS ramping works in cDNG and MLV takes only." ~/ApertarCore/src/ApertarCoreApp.cpp'  # T31, ramp_fps refuses up front: 1
ssh apertar 'grep -c "normalizeRawBitDepth(rawBitDepth) == 16" ~/ApertarCore/src/camera/CameraController.cpp'  # T32 cap, Core clamp: 1
ssh apertar 'grep -c "settings.clearHdr && settings.rawBitDepth == 16 ? 25.0" ~/ApertarCore/src/ApertarCoreApp.cpp'  # T32 cap, PCF list: 1
ssh apertar 'grep -c settingsSpeedRamp ~/ApertarCore/src/web/WebControlPage.cpp'          # T32 WebUI block: 18
ssh apertar 'grep -c m_fpsSpeedRamp ~/ApertarUI/src/ApertarControlBridge.cpp'                  # T32 touch UI picker: 2
ssh apertar 'grep -c m_soundRecording ~/ApertarUI/src/ApertarControlBridge.cpp'           # T32 picker, camera takes only: 3
```

Counts of 0 mean the tutorial is not done. Any other count that differs means a step is missing or differs from the patch.
Take him through T31 (tutorial `20261026210000 CINEMATE APERTAR T31 speed-ramping`, steps 4.1-4.8, build, §5 on the Pi), then
T32 (tutorial `20261027213000 CINEMATE APERTAR T32 speed-ramp-every-control`, steps 4.1-4.10, build Core and UI, §5). The
patches in `working/patches/` are the reference if a step will not build. After each:
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

The design is done: `working/ramp-ladder/design/design-T34.md`. It recommends A + R. Rungs change between takes, and an opt-in
Ramp-ready switch starts a ramp take in the top rung. B, switching mid-take with a clip split, is deferred. Before writing
anything, present its §0 and §2 and the open questions Q1, Q2, Q9, Q10 and Q12 (numbering). He chooses. The mockup of the editor:
https://claude.ai/artifact/YKbhhk8aMUS8sxEWa6UfRL.

Measure first on the Pi (the design's §6 has the full list, M0-M8), because the numbers decide what is built:
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
- `working/ramp-ladder/design/design-T34.md` §0-§2 and §6 (before T34).
- `working/ramp-ladder/r1-core.md` "What a ladder implementation must touch" and "Risks", and `r2-cinemate.md` §0 and "Port to
  Apertar" (both before T34).
- `working/research-30fps-answer.md`: why 25 is the Clear HDR 16-bit ceiling.
