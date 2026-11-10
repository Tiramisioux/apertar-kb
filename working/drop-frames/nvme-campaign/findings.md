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

**The touch UI leaks 48 dmabuf fds per camera reconfigure (measured 2026-11-10 after the reboot).** The Qt UI
(Apertar-UI) held 48 dmabuf fds at boot (81 fds in all), 144 after two reconfigures (177 fds), 192 after the smoke take's
(225 fds); its soft limit is 1024 open files. Night 1 reconfigured the camera about twice per take over ~10 takes
(derived: 81 + 48 x ~19 = ~1000, the limit), and `Failed to export gem bo to dmabuf` is what Mesa logs when that export
cannot get a new fd. **Probable chain:** the UI runs out of fds at about the 19th reconfigure -> its dmabuf exports fail
(the MESA flood) -> it can no longer start `arecord` (its device list and meter) -> the mic leaves its view, and Core,
which reads the UI's settings and device list at `record_start`, records without audio and says nothing. To be shown by
the next run: `ui_fds` per sample against the first silent take. Also: the meter's `arecord` inherits 48 of the UI's
dmabuf fds (no close-on-exec), so it pins the preview buffers it was started with.

**Fixed in the UI (2026-11-10, Pi UI `25eeb47`, branch clip-split, built and running from 10:49).** The leak is in
`PreviewWindowRenderer`'s import cache: keyed by the dmabuf inode, never pruned when a reconfigure keeps the preview
layout. Each entry is now stamped when used and entries unused for 64 imports are destroyed with their fds. Measured:
8 bit-depth reconfigures, UI dmabuf fds 48 -> 72 then flat (the old build: +48 per 2 reconfigures); no MESA errors.
The run from 10:5x is the test: sound in every take = the chain above confirmed in practice.

**What the runner logs from now on (User: "log carefully the loss of sound").** Every 5 s in the samples: `ui_fds`,
`ui_dmabuf`, `arec_fds`, `core_fds`, `cma_free_kb`, `audio_ready` (Core's /api/state: record audio on and the configured
device in its input list), and `uiconf_rec` / `uiconf_dev` / `uiconf_mtime` read straight from UI.conf. Before every take
the same check (waits up to 60 s for the mic), in the row as `audio_pre` / `ui_pre`. After every take the UI's journal
(`journal-ui/`, `ui_mesa_errors`). On the night start, on a failed pre-check and after every silent take a snapshot in
`audio-forensics/<time>-<tag>/`: UI.conf, /proc/asound (cards, pcm, who holds the capture device), `arecord -l` as Core
runs it, per-process fd kinds and limits, memory/CMA, the full /api/state and the UI + Core journal since the last take
with audio; one line per snapshot in `audio-events.log`. Silent takes now count as picture results (`--audio-optional`),
flagged `audio_missing=1`.

## Day run: S2 resumed + S4,S5 chained, 2026-11-10 10:51-11:36 (stopped by Core, then powered off)

**How it ended (measured).** At 11:30:32, stopping the end-control take (HDR16 28 fps, after its first drop at 159 s),
Core logged `no frame written for 5101 ms, treating the medium as gone`, then `1 writer(s) still blocked on the removed
medium, left behind`. Every later `record_start` (SDR12 warm-up 11:32, S4's warm-up 11:35) failed with `The previous
take's writers are still blocked on the removed medium (1)`. No kernel NVMe/PCIe error; Core's own merges wrote to the
card normally at 11:33. The chain started S4,S5, it failed the same way, the restore read back, the Pi powered off.

**Core bug behind the stop (probable, from the code; the stuck thread could not be inspected).** `stop()` waits up to
`APERTAR_DEAD_MEDIUM_STOP_MS` for writers on a "gone" medium, detaches the ones still busy, and at its end sets
`stopping_ = false` unconditionally (`CameraController.cpp:4614`, e298d4a; the stuck-writer path came with a3ac8da). A
writer that was only slow wakes up, sees `stopping_ == false`, waits for work again and never returns, so
`liveWorkers_` stays 1 and `startAtFolder` refuses until Core restarts. Candidate fix: keep `stopping_` true when
writers were left behind (`startAtFolder` clears it once `liveWorkers_` is 0). Not changed (Core edits need Patrik's OK).

**The card stalls when nearly full (measured; cause on the drive's side probable).** The two takes where writing fell
behind both ran the card past 96 %: the web-lever A1 take (`buffer_full` at 138.6 s, fill 96.0 %, 37 GB free) and the
end control (drop at 159.2 s, fill 96.9 %, 29 GB free). In both the write rate fell from ~470 MB/s to 16-120 MB/s within
2 s while the buffer filled (91 % / 59 %). Two other takes passed 95.8 % and 97.1 % clean; no take below 94 % stalled.
Core had trimmed after every delete. NVMe 70-72 C at the stalls, 74 C on a clean take. The runner's fill gate kept only
need + 10 GB free; **changed: at least 10 % of the card stays free after every take** (`FILL_HEADROOM`, deployed).
For shooting (probable): this card should not be filled past ~95 % in 4K HDR16.

**The UI fix works (measured).** 14 takes and ~28 camera reconfigures: sound in every take (`audio_missing` 0,
`audio_pre` ready each time), UI fds 101-105 and dmabufs 72 throughout, no MESA line in any snapshot.

**S2 results, HDR16 16:9 (measured).**

| take | fps | tier | result | first drop | kind |
| --- | --- | --- | --- | --- | --- |
| walk (owed 5-min) | 27 | 5 min | clean | - | - |
| ABBA Log, A (Log off) x2 | 28 | 3 min | clean, clean | - | - |
| ABBA Log, B (Log on) x2 | 28 | 3 min | drop, drop | 4.8 s, 4.8 s | capture-gap |
| ABBA WebUI, A (client on) | 28 | 3 min | buffer_full | 138.6 s | card stall at 96 % (see above) |
| ABBA WebUI, B (client off) x2 | 28 | 3 min | clean, clean | - | - |
| ABBA WebUI, A (client on) | 28 | 3 min | clean | - | - |
| Log at 30 | 30 | 3 min | drop | 1.7 s | capture-gap |
| TDN on at 25 | 25 | 3 min | drop | 3.7 s | capture-gap |
| lossless + Log (pre-roll 26.6 fps) x2 | 25 | 3 min | drop, drop | 4.8 s, 4.7 s | capture-gap |
| end control | 28 | 3 min | drop | 159.2 s | card stall at 96.9 % |

- HDR16 uncompressed: **27 fps carried** (3 + 5 min clean); 28 fps out from night 1. 28 fps then ran five clean 3-min
  takes today: its night-1 capture gaps are intermittent, not a hard edge (measured).
- **Log costs more than 1 fps at 28** (both Log takes dropped within 5 s, both baselines clean; measured, n=2+2).
- **TDN on fails even at 25 fps** (one take, 3.7 s); **HDR16 lossless + Log fails at 25 fps** (two takes) although its
  pre-roll measured 26.6 fps. All of these are capture gaps, the capture/ISP side, not the card.
- WebUI client: no effect shown (its one failure is the 96 % card stall; three client-on/off takes clean).
- Merges (Core, at the restore, 14 pending clips): 1.0-1.9 ms per file, 8105 files in 15.8 s.
- Heat: NVMe 62-74 C back to back; the run lasted 41 min, so no hourly break came.
- Not reached: SDR12, HDR12, the SDR12 lossless arm, S4, S5.

## Evening run S2,S4,S5, 2026-11-10 21:06-21:09 (stopped by Claude: Patrik had asked to prepare, not start)

- Core `7e6e2a3`, UI `25eeb47`. HDR16 lossless + Log re-walked from its new pre-roll (27.7 fps measured): 26 fps dropped
  at 5.7 s and 9.8 s (capture gaps, buffer 2.3 %); the arm is out at 25 and 26 fps (measured). Sound in both takes, UI
  fds 80-101. The runner was stopped by SIGTERM before its next take; restore read back OK; nothing else recorded.

## Deviations from the preregistration

- 2026-11-10 03:38: no drive-recovery idles between stages or after cold deletes (User: "simulate a shooting
  environment"); merges still waited for.
- 2026-11-10 03:42: a 10-min cooldown break about once an hour, between takes, temperatures logged every 10 s.
- One 3-min take at 28 fps stopped after 51 s for the restart (recorded as not a result, re-run).
- 2026-11-10 10:45: takes without audio count (`--audio-optional`, User: "have the tests continue even without sound");
  audio faults no longer end the night. Takes with `audio_missing=1` ran without the audio writer's load.
- 2026-11-10 20:55: the fill gate keeps at least 10 % of the card free after every take (was need + 10 GB).
