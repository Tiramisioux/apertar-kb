# NVMe campaign: findings

Labels: **measured** (read from this campaign's logs), **derived** (computed from measured numbers), **probable**
(fits the evidence, not tested). Data: `run-20261110/` (the runner's run directory, pulled after each night).

## Night 1: S1 + S2, 2026-11-10 03:32-04:09 (stopped early, then powered off)

**How it ended (measured).** A second void ended the night at 04:07: the two 5-min takes at HDR16 27 fps (C0007,
C0008) recorded 8106 and 8107 frames with no drops but **no audio**. Core logged no `audio capture` line, no WAV in
either folder, and `record_start` did not fail. The restore read back (5000, merge on) and the Pi powered off at 04:09
through Core, as designed.

**S1, the card (measured).** Corsair MP600 Mini A936B442006AC2: 60 GB direct write 780 MB/s (slowest 10-s window
627 MB/s), state60 777 MB/s (slowest window 596 MB/s), max 47 C. The 354 MB/s in the runner's start line is the old
SSD-campaign estimate, not this card.

**S2, HDR16 16:9 (measured).**

| fps | tier | result | first drop | kind | write buffer peak | NVMe start-max C |
| --- | --- | --- | --- | --- | --- | --- |
| 28 | 60 s warm-up | clean | - | - | 2.6 % | 47 |
| 28 | 3 min | clean | - | - | 2.8 % | 65 |
| 28 | 5 min | drop (1 frame) | 135.8 s | capture-gap | 13.0 % | 69 |
| 28 | 3 min | drop (1 frame) | 152.8 s | capture-gap | 11.8 % | 71 |
| 27 | 3 min | clean | - | - | 3.1 % | 73 |
| 27 | 5 min | void, no audio (0 dropped) | - | - | 3.3 % | 74 |
| 27 | 5 min | void, no audio (0 dropped) | - | - | 3.5 % | 76 |

- 28 fps is **out** (cell rule 1-1, third take dropped). 27 fps has a clean 3-min take; its 5-min take is still owed.
- Both drops are **capture gaps** (`dt_us=71423` against `nominal_us=35715`: one missed sensor frame;
  `frame index jump ... skipped=1`), with the write buffer at 12-13 %. The limiter at 28 fps is the capture/ISP side
  (CFE had no free raw buffer), **not the card** (derived: 16.6 MB x 28 = 465 MB/s against a 596-627 MB/s worst window).
- The fix checks: `index_jumps` counted each gap once and matched `dropped`; no numbering gaps, no boundary drops
  (no take crossed 5000 frames with a drop near it).
- **Heat (measured):** back to back, no breaks, the NVMe went from 47 C to 76 C in 30 min, still climbing about
  1-2 C per take; the Pi stayed at 57-61 C. The hourly break (first one due at 04:42) never came.

**The audio loss (probable, not confirmed).** At 03:56:12, at the 16-bit camera reconfigure before C0007, the touch UI
(`run_pi_direct.sh`) began logging `MESA: error: Failed to export gem bo ... to dmabuf` / `Export failed`, about 2000
lines a minute until the power-off. Both silent takes lie in that window; every take before it had audio.
- Core turns audio off silently (`audioOptions.enabled = recordAudioEnabled && inputDevice found`,
  `ApertarCoreApp.cpp:3157`, e298d4a) when its UI.conf read or its `arecord -l` device list comes back without the
  mic; a busy mic would instead have failed `record_start`, which did not happen.
- The UI rewrites `audioInputDevice` in UI.conf from its own device list (`SettingsPage.qml:954`
  `syncAudioDeviceSelections`); a UI whose `arecord` detection fails could write the mic away. Not shown yet.
- Seen after the reboot: the UI's meter `arecord` (`-D plughw:2,0`) holds 48 inherited dmabuf fds of the UI
  (no close-on-exec); CMA is 64 MB in all (55 MB free at idle). CMA exhaustion or an fd leak in the UI would explain
  the export errors; neither was measured during the night.
- Consequence for a shoot (probable): after about 25 min of takes and mode switches, the camera can keep recording
  picture with no sound and no warning.

## Deviations from the preregistration

- 2026-11-10 03:38: no drive-recovery idles between stages or after cold deletes (User: "simulate a shooting
  environment"); merges still waited for.
- 2026-11-10 03:42: a 10-min cooldown break about once an hour, between takes, temperatures logged every 10 s.
- One 3-min take at 28 fps stopped after 51 s for the restart (recorded as not a result, re-run).
