# Tutorials

Patrik learns Apertar by making each change himself. So when a problem comes up, the
`apertar-dev` skill writes a tutorial **first**. It does not make the change itself unless Patrik
asks it to ("just do it", "fix it for me").

## Where tutorials live

Obsidian vault `Patrik Obsidian`, folder `02_PROJEKT/CINEMATE/APERTAR/notes/`.
Disk path: `~/local anteckningar/obsidian vaults/Patrik Obsidian/02_PROJEKT/CINEMATE/APERTAR/notes/`.

- File name: `<YYYYMMDDHHMMSS> CINEMATE APERTAR <topic>.md`, topic in kebab-case or snake_case.
- Frontmatter, exactly these keys (the APERTAR hub picks the note up via `projekt`):

```yaml
---
datum: 2026-10-25 18:00:00
kontext: CINEMATE
projekt: "#APERTAR"
fritext: <topic>
typ: digital anteckning
---
```

- End the note with the tags `#CINEMATE` and `#APERTAR` on their own lines.
- **Written on the Pi?** The vault isn't there. Claude saves the note, already named and formatted as
  above, in `~/apertar-kb/tutorials/inbox/`. After the next KB sync the Mac side moves each inbox file
  into the vault folder (`git mv` out of `inbox/` is wrong: the vault isn't in the repo; copy, then
  `git rm` the inbox copy) and adds the index row.
- Obsidian syntax: callouts `> [!note]`, collapsible answers `> [!tip]- Answer`, wikilinks
  `[[file name|label]]`. Not MkDocs `!!!`.
- Never rename a folder by case only (Syncthing `_CaseConflict` trap).

## Shape of a tutorial

Reference example: `20261025152945 CINEMATE APERTAR start-tutorials` (the I2C/DPI diagnosis). It
shows the depth wanted: a rig table, the exact symptom output, the evidence with `path:line`
refs, the resolution, the side effects, what upstream could change, open questions, sources.
A learning tutorial adds the doing: Patrik runs and types every step.

| # | Section | Contents |
| --- | --- | --- |
| 0 | Header | Title = the outcome ("Make HDMI the touch screen at 1080p"). One status line. **You will learn** (2-4 bullets). **Risk** (reboot? `config.txt`? can it brick boot? how to undo). Time estimate |
| 1 | The problem | Exact symptom, command output in a code block, what was expected |
| 2 | How this part works | The mental model in under a page. Diagram if it helps. "Open `src/…/X.cpp` and read lines A-B" reading assignments |
| 3 | Find it yourself | Guided checks. Each: command, **prediction** ("you should see…"), a question. Answers in collapsed `> [!tip]- Answer` callouts so they don't spoil |
| 4 | Make the change | Numbered steps. File, location (`path:line`, plus a search string in case lines moved), the change and why. Show the target code; Patrik types it. One **Check:** per step |
| 5 | Build, deploy, test | Exact commands (VS Code task names too), expected output, what success looks like on the camera |
| 6 | Commit and push | Which machine, `git add <files>`, the full commit message in house format, `git push`, then `apertar_status.sh` |
| 7 | If it went wrong | Table: what you see / what it means / what to do. Always includes how to undo |
| 8 | What you learned, going further | Recap. 1-2 follow-up exercises. Upstream issue/PR it could become |
| 9 | Sources | Files with commit/release, docs, datasheets, KB pages |

Rules:

- Commands are copy-pasteable, one per line, with a comment saying what each proves.
- `path:line` refs name the version (`upstream-1.6.0` or a fork sha). Add a grep string as backup.
- Mark anything not verified on this Pi **unconfirmed**, with the command that would settle it.
- Never put the Pi password or any token in a tutorial.
- Short sentences. Tables over prose. No scene-setting intro.

## Step numbers and the tutor block

So the tutor (`apertar-dev`, Mac or Pi) can check a tutorial and Patrik's progress, every new
tutorial has:

- **Numbered steps** in sections 3 and 4: a bold line starting with the number,
  `**3.1 Is anyone home?**`, `**4.2 Find where it was saved** (Pi):`. "I'm at 4.2" then means one thing.
- A **tutor block** just above the closing tags. Obsidian hides `%% … %%` in reading view:

```
%% tutor
ref core src/ApertarCoreApp.cpp 9091 std::string ApertarCoreApp::handleCommand
ref ui src/ApertarControlBridge.cpp 1013 bool ApertarControlBridge::sendCoreCommand
check 3.1 | curl -s -m 3 -X POST http://127.0.0.1:8000/api/command -d '{"cmd":"ping"}' | "pong":true
check 4.1 | grep -n 'label: "CODEC"' /home/pi/ApertarUI/qml/CameraPage.qml | CODEC
%%
```

| Line | Format | Rules |
| --- | --- | --- |
| `ref` | `ref <core\|ui\|drv> <repo path> <line> <literal anchor>` | One per `path:line` the note asks him to read or edit. The anchor = a literal string that occurs once in that file (rest of the line) |
| `check` | `check <step> \| <command> \| <expected regex>` | The step's **Check:** as a command that runs **on the Pi** (`127.0.0.1`, `/home/pi/…`). Read-only only: `tutorial.py` refuses anything else (no `set_*`, no `sudo`, no `>`, no `git checkout`). For a code change, check the source file or `git diff`, not the running camera |

Check it before handing the note over (the Mac: notes in Obsidian; the Pi: `~/apertar-tutorials`):

```bash
python3 ~/Documents/Apertar/apertar-kb/tutorials/tutorial.py refs T01     # every ref still at its line on the Pi tree
python3 ~/Documents/Apertar/apertar-kb/tutorials/tutorial.py show T01     # outline, checks, progress
```

Working through a tutorial together: `llm/tutoring.md` §7. Progress lives in
`tutorials/progress/<ID>.md` (written by `tutorial.py log`, committed in the KB).

## Index

The planned order (learning path T01-T15, with the mental model each builds) is in
`llm/tutoring.md` §5 and, for Patrik, in the Obsidian note
`20261025190000 CINEMATE APERTAR learning-path`. Keep both in step with this table.

| Date | Note | Topic | Status |
| --- | --- | --- | --- |
| 2026-10-23 | `20261025152945 CINEMATE APERTAR start-tutorials` | I2C bus 1 missing: DPI overlays, CFE hat Qwiic hub, NeoRotary 4 | Done on hardware, confirmed |
| 2026-10-25 | `20261025191000 CINEMATE APERTAR T01 talk-to-core` | T01: the command protocol by hand (curl + Python socket) | written |
| 2026-10-25 | `20261025190927 CINEMATE APERTAR clearhdr16-tutorial` | **T16.** 16-bit Clear HDR on the IMX585, Steps 0-8 (WDR switch, 16-bit raw path, HDR knobs, guards, UI). External workbook (Downloads). Checked on the Pi 2026-10-25: Core/UI refs valid; driver refs are Apertar-Studio `main`, and on `e5b74d3` WDR=1 still offers 12-bit (mode [10]); callout + tutor block added | written |
| 2026-10-25 | `20261025193414 CINEMATE APERTAR tally-gpio21-tutorial` | **T17.** Tally LED on GPIO 21: which definition wins, polarity, wiring test. External workbook (Downloads). Pi-checked: GPIO 21 is the trigger output's pin on this rig; callout + tutor block added. Done at the rig 2026-10-25 (section route, Cinemate wiring); note moved to `APERTAR/_archive/` | confirmed |
| 2026-10-25 | `20261025193415 CINEMATE APERTAR media-yank-tutorial` | **T18.** Yanked card/drive: `media_mounted` = alive, record gates, abort on removal, CFE surprise removal, USB remount. External workbook (Downloads). Pi-checked: refs valid, Step 0 and the automounter install corrected in the callout; tutor block added | written |
| 2026-10-25 | `20261025194053 CINEMATE APERTAR T19 list-sensor-modes` | **T19.** Core reports the sensor's real modes (`list_sensor_modes`, from libcamera's Raw stream formats); first step from hard-coded mode lists to the Cinemate model | written |
| 2026-10-25 | `20261025215321 CINEMATE APERTAR webui-false-recording-tutorial` | **T20.** WebUI records with no drive: honest record button, `media_state`; WebUI half of T18. External workbook (Downloads). Pi-checked; box + tutor block added | done (Steps 2-5 on `cinemate-port`; pull tested 2026-10-27) |
| 2026-10-25 | `20261025215322 CINEMATE APERTAR webui-time-left-investigation` | **T21.** WebUI "Time left" vs HDMI: two estimate models; port the QML model into Core. External investigation (Downloads). Pi-checked: 16-bit Clear HDR flips the error direction; box + tutor block added | done (`3c4f07d`; agrees with HDMI up to rounding) |
| 2026-10-26 | `20261026041000 CINEMATE APERTAR T22 clearhdr-drops-measure` | **T22.** Where Clear HDR frames are lost: CSI-2 error counters (`rp1_cfe.track_csi2_errors=1`), writeback vs direct `dd`, tmpfs test, Cinemate's sysctl knobs, "has no buffer" debug. Measurement only; inbox (cloud session) | done (measured; lossless takes were encoder-bound) |
| 2026-10-26 | `20261026041500 CINEMATE APERTAR T23 requests-follow-buffers` | **T23.** One libcamera request per raw buffer (`kActiveRequestCount = 3` capped every mode at 3), 8 buffers in Clear HDR, warm raw pool. Patch `working/patches/0001-camera-one-libcamera-request-...` | done (`db17860`) |
| 2026-10-26 | `20261026042000 CINEMATE APERTAR T24 cdng-direct-io` | **T24.** Uncompressed cDNG with O_DIRECT: IFD-first layout, StripOffsets on a page boundary, page-aligned raw copies, `APERTAR_CDNG_DIRECT_IO`. Patch `working/patches/0001-cdng-direct-I-O-...` (not compiled) | skipped (uncompressed 25 fps clean without it) |
| 2026-10-26 | `20261026042500 CINEMATE APERTAR T25 raw-copy-off-completion-thread` | **T25.** Raw copy on a recorder worker with worker-side requeue (H.264 `PreviewJob.release` pattern), held requests ≤ buffers-2. Patch `working/patches/0001-camera-copy-raw-frames-...` (not compiled) | done (`43a54f3`, `fc7eb16`, `351a3ee`, `d9f00d4`) |
| 2026-10-26 | `20261026043000 CINEMATE APERTAR T26 driver-crop-rectangles` | **T26.** `apertar` driver: per-mode `.crop` in native sensor pixels so `ScalerCropMaximum` is real (Cinemate's invariant, fixed there in `951aeee`). DKMS + reboot. Patch `working/patches/0001-imx585-report-each-mode-...` | confirmed (`24172e6`, binning `4ab1057`) |
| 2026-10-26 | `20261026090000 CINEMATE APERTAR T27 frame-rate-phase-lock` | **T27.** Optional frame-rate phase lock: measure today's cadence error, run the host simulation of the servo, check the HMAX/VBLANK hazard, enable `set_fps_phase_lock`. BOOTTIME reference, so no audio change. Patch `working/patches/0001-camera-frame-rate-phase-lock-...` (not compiled; header simulated) | done, lock off (sensor ~1.5 ppm; lock flickers on the lattice libcamera) |
| 2026-10-26 | `20261026091000 CINEMATE APERTAR T28 yanked-media-robustness` | **T28.** Drive pulled mid-take: media watcher (mount table + statvfs on the root), errno classes, stop path that never reopens a gone medium, counted losses, `media` event, record gate, eject intent. Supersedes the Core half of T18. Patch `working/patches/0001-media-survive-a-yanked-...` (5 of 11 files host syntax-checked) | done for CFE (pull + re-insert, pull-safe takes); USB pull, 5.1, 5.3 open |
| 2026-10-26 | `20261026092000 CINEMATE APERTAR T29 media-profile` | **T29.** Media profile: connection class + filesystem from sysfs and the mount table; uncompressed-cDNG workers, queue, direct I/O and camera buffers follow the medium (env wins); root helper `apertar-media-tune` for block-queue and `vm.dirty_*`; `noatime`; `takes.sh` comparison on/off; the pre-roll question measured. Patch `working/patches/0001-media-profile-...` | done without direct I/O (`26da30e`, `0358fcf`; helper opt-in `ebdcd08`) |
| 2026-10-26 | `20261026093000 CINEMATE APERTAR T30 audio-writer-thread` | **T30.** Audio under storage load: writer thread + RAM queue, 1 s ALSA ring with a 10 ms period, discontinuity counts and the drift-vs-loss check. Patch `working/patches/0001-audio-writer-thread-...` | done (`60ce8e9`; 100 ms ring; drift from a fit over all blocks `ebdcd08`) |
| 2026-10-26 | `20261026210000 CINEMATE APERTAR T31 speed-ramping` | **T31.** Speed ramping: FPS changes inside a cDNG/MLV take behind `fps_speed_ramp`; count-based numbering, one `FrameRate`/timecode base per clip, real-time WAV, shutter policy, grace for the gap estimate and the phase lock, `fps-ramp.txt`, `ramp_fps` stepper (refuses up front in a take it cannot ramp). Rebased onto `cinemate-port` `b606c4f` (2026-10-27). Patch `working/patches/0001-camera-speed-ramping-...`; inbox (cloud session) | done (`faa2958`, switch-only API; tested C0030-C0032) |
| 2026-10-27 | `20261027213000 CINEMATE APERTAR T32 speed-ramp-every-control` | **T32.** Speed ramping from every control: Cinemate-style Speed Ramp block in the WebUI's Recording format card, the touch UI picker leaves the shutter to Core in a camera ramp take, 25 fps ceiling for 4K Clear HDR 16-bit in Core (clamp and PCF list), WebUI and touch UI. Patches `working/patches/0001-camera-cap-4K-...`, `0001-web-speed-ramp-...`, `0001-ui-4K-...`, `0001-ui-FPS-picker-...`; inbox (cloud session) | done (ported 2026-10-28; C0022 ramp from the controls) |
| 2026-10-29 | (not yet written; project page `working/drop-frames/README.md`, work order `working/handoff-drop-frames.md`) | **T35.** Fewer dropped frames: A/B knob matrix, RAM-bounded write queue that blocks instead of dropping, no in-take fsync by default, media tuning on by default, cached SDR raw buffers, scheduling parity; plus **CineMate Log for Apertar** (16→12, 12→10, 10→8, one step down, `set_cdng_log`) | planned |
| 2026-10-29 | (no note; results in `working/playback/measurements.md`) | **T46.** Playback measurements on the Pi: the bench (one 4K frame, cold and warm), small requests per second, the list's cost (6.8 s), the NVMe link (Gen 3, 800 MB/s), locale, movie plugin. No touch screen on this Pi, so M2, M5, M12 (touch half) and M13 are skipped; M6, M7 and the rest not done | measured, partly |
| 2026-10-29 | `20261029200000 CINEMATE APERTAR T47 core-knows-its-clips` | **T47.** WebUI playback part 1: the frame list with its holes (`ClipFrames.hpp`), the hold rule and yield window (`PlaybackHold.hpp`), the DNG tags and the recorded timecode (`DngTags.hpp`); host test `t47_test.cpp` (41 checks, passes on the Pi). Part A written; part B (per-clip facts, `/api/media/clip`, `playback_hold`) follows | done 2026-10-29 by Claude on the Pi (Core `f91fafa`, `ab4cc92`); the note stays as the explanation |
| 2026-10-29 | (no note; `working/playback/design-playback.md` §6) | **T48.** Core draws a frame: `/api/media/frame` by frame number, liblj92, decode slots, JPEG caches, the touch UI's look (Core `1af26c8`) | done by Claude, tested |
| 2026-10-29 | (no note) | **T49.** WebUI Clip Browser in the touch UI's shape: cards, thumbnails, long-press selection, Remove/Download Selected (Core `bc12c0a`, `27eac5a`) | done by Claude, tested |
| 2026-10-29 | (no note) | **T50.** WebUI Clip Viewer: frame-number clock, black holes, scrub, frame step, metadata, hold card (`4629de2`); downloads and deletes yield to a take (`a37a902`) | done by Claude, tested |
| 2026-10-29 | (no note) | **T51.** Sound: `/api/media/file` with Range, the `<audio>` as the clock (`fa19856`, `4fa0432`). T52 MLV, T53 ProRes/H.264, T54 touch UI still to do (`working/playback/HANDOFF-next.md`) | done by Claude, tested in Chrome |
| 2026-10-29 | `20261029215000 CINEMATE APERTAR T36 one-action-vocabulary` | **T36.** Controls project step 1: one action vocabulary (`ActionCatalog.hpp`, replaces six copies) and `list_actions`; host test `working/tools/controls_test.cpp`. Core `916c1dd` on branch `controls` | done 2026-10-29 by Claude, tested on the camera |
| 2026-10-29 | `20261029224000 CINEMATE APERTAR T37 core-owns-the-hardware-file` | **T37.** Controls project step 2: Core owns `apertar-hardware.conf` (text model, validator, one store with lock, revision, history), the IMU writers through it, `get_controls` / `set_controls`, validated at start. Core `controls` `3526e4b`, `c509e9f`, `f5a61b8`, `4d80a35` | done 2026-10-29 by Claude, tested on the camera |
| 2026-10-29 | `20261029231000 CINEMATE APERTAR T38 no-silent-overwrites` | **T38.** Controls project step 3: the Config page and `/api/config` through the store (revision header, 409 for an old or stale page, issues with line numbers), the socket line limit 1 MiB, a replaced hardware file detected and restorable, the touch UI no longer writes a default file, HDMI 1080p as the display fallback. Core `controls` `5395fa4`, `effb804`, `014fa22`, `7af9f13`; UI `c9d841f`, `7c41a27` | done 2026-10-29 by Claude, tested on the camera and in Chrome |
| 2026-10-29 | (not yet written; project page `working/drop-frames/README.md`, work order `working/handoff-drop-frames.md`) | **T35.** Fewer dropped frames: A/B knob matrix, RAM-bounded write queue that blocks instead of dropping, no in-take fsync by default, media tuning on by default, cached SDR raw buffers, scheduling parity; plus **CineMate Log for Apertar** (16→12, 12→10, 10→8, one step down, `set_cdng_log`) | built on the `drop-frames` branches (Mac, Pi, GitHub; updated 2026-11-01 with the storage pre-roll, speed-ramp "After the take", the Log-in-SDR finding); Pi tests open: `working/drop-frames/README.md` section 0 |
| 2026-11-03 | `20261103234000 CINEMATE APERTAR T55 clearhdr16-steady-preview` | **T55.** A steady 4K 16-bit Clear HDR preview: name the flicker, then find its stage with existing switches (Clean Feed, WebUI with aids off, idle against take, 12- against 16-bit, 4K against 1080p); a calm tuning copy (no CE, no adaptive ALSC, no TDN) through `set_tuning_file`, bisect, then edit `imx585_clearHDR.json` (not in git, backup first); zebra 90 % / peaking 0.20 for the aids. Diagnosis: `working/clearhdr16-preview.md`. Pi-checked 2026-11-03: 21 refs OK, 16 read-only checks | written |

Status values: `written` → `in progress` → `done` (Patrik did it) → `confirmed` (result on hardware,
logged in `lessons/hardware-log.md`).
