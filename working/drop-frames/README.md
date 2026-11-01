# Project: fewer dropped frames in Apertar, and CineMate Log for Apertar

Started 2026-10-29 from a cloud session that read all four repositories. Sources: `Apertar-Core`
`cinemate-port` @ `7678cbf`, `cinemate` `main` @ `4990afc` (full history, 2192 commits), `cinepi-raw`
`main` @ `63a08d5`, `cinemate-handbook` @ `c99ff77`, plus this KB's `working/compare-raw/`,
`working/clearhdr-compare-answer.md` and `lessons/hardware-log.md` 2026-10-26/27.

Status words as in the rest of the KB: **confirmed** (read in the source or measured on the Pi),
**probable** (inferred, reason given), **unconfirmed** (the command that settles it is named).

The handoff for the Mac session that drives the work is `../handoff-drop-frames.md`.

## 0. Outcome (2026-10-31) {#outcome}

**One sentence.** The dropped frames were the recording drive's state, not Apertar's buffer: after about 0.9 TB of writing
without a trim the NVMe stalls for seconds (and can hang its controller); trimming it restores it. Core now trims by itself,
and the campaign also added Log (smaller files), a switchable large RAM buffer with a safety stop, and an on-screen buffer
indicator. Everything is on the `drop-frames` branches of Apertar-Core (`d44b177`, one squashed commit, base `a40112a`, plus three commits on top: `fb5801c`, `c5db8b2`, `014a2bf`; branch head `014a2bf`) and
Apertar-UI (`841d0ed`, one squashed commit, base `ea44bd7`, plus `4959513`, `96a7aa4`, `606f137`; branch head `606f137`): on the Mac, the Pi and GitHub (branch `drop-frames` of
`Tiramisioux/Apertar-Core` and `Tiramisioux/Apertar-UI`; `main` untouched, nothing merged). Updated 2026-11-01: see
"Added 2026-11-01" and "Added 2026-11-01 (later)" below (the earlier hashes were `400dd1f` and `74f39c6`).

### What a trim is, and what we gain

An SSD cannot overwrite data in place: it must erase a block before it writes it. Deleting a file only removes it from the filesystem's
list, so the drive never learns that the space is free. A trim (`fstrim`, also called discard) tells the drive which blocks are unused, so
it can erase them in advance. Without it, a drive that has been written all over must erase while you record, and writes stall for
seconds. Core now trims by itself after big deletes and when a drive is mounted, which takes under a second (927 GB in 0.47 s). The gain:
no stalls, dropped frames or hung drive on a worn-in card. (Measured: the stalls and their cure; the erase-while-recording mechanism is
the standard explanation, not measured here.)

### Findings (each one has its hardware-log entry)

| # | Finding | Evidence | Status |
| --- | --- | --- | --- |
| 1 | After about 0.9 TB of writes without a trim the NVMe (Corsair MP600 Mini, exFAT, mounted without `discard`) stalls for seconds: 18 to 77 % of frames lost, worst file 5 to 10 s; a trim restores it. The first bad run came at 909 to 981 GB, close to the volume size (917 GiB): inference, the filesystem walks the volume once and then rewrites never-trimmed space | 48 overnight runs and 23 two-arm runs: 9 clean runs after a trim, then bad, seen twice; trim before every run 12 of 12 clean (hardware-log 2026-10-30) | measured; the mechanism is inference |
| 2 | In the worst case the drive hangs: four 256 KB writes got no answer for 30 s, `nvme nvme0: Disabling device after reset failure`, exFAT went read-only, `state=dead`, a reboot recovered it. No under-voltage, no PCIe errors, 57 C | kernel log 01:43 to 01:45 | measured |
| 3 | Core itself is clean on a trimmed drive: 10-minute 4K 25 fps 16-bit Clear HDR uncompressed, 15001 frames, 0 dropped, `peak_queue=2/12`, stop `syncfs` 214 ms (A0) | hardware-log 2026-10-30 | measured, one take |
| 4 | Folder layout (single, sub-folders of 500, 1000, 2500), creating files ahead, `fallocate` preallocation, heat (clean at 72 C, bad at 65 C; drive limit 82.9 C) and writer count did not matter. Preallocation was worse | synthetic tests outside Core, overnight set | measured |
| 5 | The once-a-second fsync is not needed on a trimmed drive (A1 clean); the per-frame writeback hint is (A2 lost about 10 % of frames at capture: `dropped_gap_estimate=1491`, `queue-full` 0) | hardware-log 2026-10-30 | measured, one run each |
| 6 | Short takes seemed to lose 2 to 10 frames at capture in the first seconds. Re-measured 2026-11-01: a **steady** loss of about 2 frames a second (7 %) for the whole take while the touch UI runs, 0 with it stopped; the open WebUI adds about 2 %. A0 was clean with the touch UI running, so it is a regression since A0 (UI or what Core sends it) | hardware-log 2026-11-01 (three 60 s takes) | measured; the side that changed is not yet split |
| 7 | `takes.sh` `missing` cannot see capture gaps (the numbering counts written frames). Check frames written against fps x seconds and the `capture-gap` counter | A2 showed `missing=0` | measured |
| 8 | CineMate has no trim or discard either (its automounter mounts exFAT `rw,noatime`, ext4 `rw,noatime,nodiratime,commit=60`); its big RAM buffer is burst absorption, not a faster disk | `storage-automount.py`, handbook grep | read from source |
| 9 | The drive asks for 64 MiB of host memory and gets none (`nvme.max_host_mem_size_mb=0` in the boot arguments) | kernel log | whether it matters: untested |
| 11 | The ladder and `fps_max` said 30 fps for 4K SDR; the startup sensor probe says 60 (10-bit and 12-bit; crops 62.85 to 85.66; Clear HDR 12-bit and 16-bit 30). Cause: the 4K branch of Core's hard-coded fps table returned 30 for SDR too and Core took `min(table, probe)`. Fixed: the probe is authoritative, the table is the fallback, the 16-bit Clear HDR 25 fps limit is a separate back-end cap, lossless JPEG keeps its encoder limit (30 at 4K); the operator sets the practical fps per rung in the Mode Ladder for the drive and build | `list_sensor_modes` and `get_mode_ladder` on the Pi (hardware-log 2026-10-31); code `tableMaximumFpsForResolution` | measured; the fix is not yet run on the Pi |
| 12 | 4K Clear HDR 16-bit lossless JPEG encodes at about 17.5 fps (`estimated_capacity_fps` 17.2 to 17.8, 5 workers, 281 ms a frame, 109 ms of it waiting); the ladder rung "16-bit lossless JPEG <= 25" therefore fills the RAM buffer and the safety stop ends the take after about 19 s at 25 fps (2026-11-01 19:06). The ladder's `ceilings.lossless_jpeg` says 25 for HDR16 | journal `lossless timing` 00:42, 00:49, 19:07 | measured; fix (rung uncompressed, or a ceiling from the encoder) not decided |
| 10 | The CM5 RTC (`rpi-rtc`) works and reads the correct time, but every boot started at one stale time; Core's "Apply Date & Time" writes the RTC and never reads it, and swallows a missing-RTC error | hardware-log 2026-10-31 | partly inference; power-off test open |

### What was built

| Feature | What it does | How it is controlled | Where |
| --- | --- | --- | --- |
| Trim | `scripts/apertar-media-trim` (root helper, validates the path, needs discard support, 20 s limit) and Core's trim worker: trims `/media/RAW` after a delete batch that frees at least 1 GiB and when the drive is mounted; never during a take; `record_start`, photos and media actions wait at most 2 s for a running trim and then end it. A 927 GB trim took 0.47 s | `APERTAR_MEDIA_TRIM=0` turns it off; state `media_trim_last_result/bytes/ms/unix`, `media_trim_running`; manual install block in the Apertar-Core README ("Trim the recording drive") | Core |
| Log | Stores 16-bit as 12, 12 as 10, 10 as 8 bit through a log curve (about 25 % smaller files at 16 to 12) in cDNG (uncompressed and lossless JPEG) and Lossy DNG; always one step down; the DNG carries the inverse as its LinearizationTable. Limits: only unpacked 2-byte raw streams (packed or PiSP-compressed raw records linear and `cdng_log_applied` says so); the 10-to-8 curve is provisional (derived, no CineMate spec); not opened in Resolve yet | one On/Off button (WebUI Recording format card, touch UI Settings > Record); `set_cdng_log value=off|auto` (legacy 12/10/8 read as On); state `cdng_log`, `cdng_log_bits`, `cdng_log_available`, `cdng_log_applied`; the format label says "· Log" | Core, WebUI, touch UI |
| Write-buffer level | Lock-free gauge of the write queue (frames, or bytes in ram mode) | `GET /api/buffer`, state `buffer_used/capacity/fill/mode/unit`, a `buffer` socket event from its own lock-free thread (at most 4 a second) | Core |
| Buffer bar | The level drawn inside the REC/READY pill: red while recording, cropped by the pill's shape | option "Frame buffer bar" (off by default; WebUI Settings > Monitoring, touch UI Monitoring), `set_frame_buffer_bar_enabled` | WebUI, touch UI, HDMI |
| Buffer switch | `frames` (the original 12-frame queue, drops a frame when full; default) or `ram` (a byte-budget queue like CineMate's RAM pool: 0.6 x MemAvailable minus 512 MiB, capped at 0.5 x MemTotal; refuses itself and stays on `frames` when that is smaller than the 12-frame queue, so a small machine such as a Pi Zero keeps the original behaviour) | `[storage] buffer=frames|ram`, `buffer_ram_fraction`, `buffer_ram_floor_mb`, `buffer_ram_max_fraction` in `apertar-hardware.conf` (Config pane, validated with line numbers, read at each take); env `APERTAR_CDNG_BUFFER` and friends override; command `set_buffer_mode`; Frames / RAM buttons (WebUI Settings > Record, touch UI Settings > Record); state `buffer_setting`, `buffer_note` | Core, WebUI, touch UI |
| Safety stop | In `ram` mode the take ends by itself, cleanly, when the buffer is 90 % full (CineMate's "RAM pool exhausted" idea): the queue sets a lock-free flag, a thread runs the same path as `record_stop`. The pill turns green with the READY text hidden and only the bar emptying; the READY text returns at zero; one message says why | `[storage] buffer_stop_percent` (0 = off, 50 to 99; default 90 in ram mode, off in frames mode), env `APERTAR_CDNG_BUFFER_STOP_PERCENT`; state `buffer_safety_stop`, `buffer_stop_percent` | Core, WebUI, touch UI |
| Max fps | The maximum fps of a mode is read from the sensor probe at startup, so 4K SDR offers 60; the table is only the fallback | `APERTAR_FPS_LIMIT=table` restores `min(table, probe)`; the UIs cut their fps lists at `fps_max` | Core (`FpsCeiling.hpp`, `CameraController.cpp`) |
| Dropped-frames count | The take's dropped frames of every kind as a number in the chip that showed "!" (touch UI, HDMI); 0 at each take start, kept after the take, the pre-roll does not count | state and record replies `recording_dropped_frames`, also on the `buffer` and recording events | Core `64bbbaa` (`RecordingDropWarning`), UI `68e1a41` (`DroppedFrameWarning.qml`); measured: matches the journal (18 = 18) |

### Added 2026-11-01 (read from the code on `d44b177` / `841d0ed` unless marked measured)

| Feature | What it does | How it is controlled | Where |
| --- | --- | --- | --- |
| Storage pre-roll | A short take through the real write path at the sensor's maximum fps for the current resolution, its clip deleted afterwards (CineMate's warm-up). Target = `prerollMaximumFps` (probe, only the 16-bit Clear HDR back-end cap kept; not the lossless cap, the ladder or the speed-ramp limits). It pins `FrameDurationLimits {period, period}` on every request (`CameraSession::setPrerollFps`) and waits for the new period (`waitForFramePeriod`, 1 s), then measures fps from the sensor timestamps. Triggers: Core start, card insert, format (once), manual. Left out of: audio, gyro, tally/REC event, counters, the safety stop, the dropped-frames warning. Refused while it runs: record, photo, timelapse, format/eject/mount, speed test, standby. Blue PRE-ROLL pill (WebUI, touch UI, HDMI); italic fps readout shows the pre-roll fps while it runs | `[media] preroll=on` or `off` (default on) and `preroll_seconds` (1 to 10, default 2); env `APERTAR_STORAGE_PREROLL=0` or `=1` beats the file; `storage_preroll` (manual), `set_storage_preroll`; state `storage_preroll_active/last/fps/auto/auto_env`; manual button and On/Off in the WebUI media card, "Storage Pre-roll" in the touch UI Media Speed card | Core (`StoragePreroll.hpp`, `CameraController.cpp`, `ApertarCoreApp.cpp`), WebUI, touch UI, HDMI |
| Clear HDR over the ladder | An explicit `set_clear_hdr` applies while the Mode Ladder is on (`ladderOverride_`). Ends on an fps, resolution, record format, bit depth, Ramp-ready or ladder change, and on restart; the 16-bit follow-up (`set_raw_bit_depth 16`) after turning HDR on does not end it | state `ladder_override` | Core |
| Lossless JPEG fps | The IMX585 lossless cap of 30 is gone: the ceiling is the mode's own maximum (60 in 4K SDR 12-bit). ISO cap 1600 unchanged | `APERTAR_LOSSLESS_FPS_LIMIT=<n>` restores a lower cap (`=30` is the old one) | Core (`FpsCeiling.hpp` `losslessImx585Fps`) |
| Minutes left | Core's estimate (`estimatedRawBytesPerSecond`) and the touch UI's (`CameraPage.qml` `estimatedFrameSizeMB`) count Log's stored bits only when `cdng_log_applied`; the touch UI updates on `cdngLogChanged` | none | Core, touch UI |
| Speed ramp "After the take" | `stay` (default): the fps the ramp ended on stays if it is valid for the mode after the take (no rung change, the sanitiser leaves it), else it returns to the start fps. `return`: always back to the start fps | `set_fps_speed_ramp after=stay` or `after=return`; state `fps_speed_ramp_after`; settings-file key `fps_speed_ramp_after`; preset key `cameraFpsSpeedRampAfter`. WebUI only: the touch UI has no speed-ramp section | Core (`restoreFpsAfterRampLocked`), WebUI |
| WebUI Settings | A search box over all panels (`data-search` keywords, a `MutationObserver` re-runs the filter after renders); Controls page "GPIO in" / "GPIO out"; Tally LED row = pin dropdown first, then function, Active, Test, no On field (a set pin is on); PCF8574 pins listed only when an expander is detected; every pin is a dark dropdown, existing rows too (a pin change moves the control); used pins are greyed with their function and selectable after a confirm that removes the old control; the value-list editor got line/ordering fixes, flicker-free greyed chips and an explanation; Frames/RAM text per selected option plus a short RAM note; ladder: the last rung defaults to its ceiling (the "max 50 must be above 50" bug) and the row range line says "sensor max N fps" | none | WebUI |
| WebUI fixes | The List/Free button in the value-list editor did nothing while it had focus (`renderValueListsEditor` skipped the redraw when a button inside had focus); `/api/state` carries the `buffer_*` and `storage_preroll_*` fields under `system` and the page lifts them to the top level in `renderSnapshot` | none | WebUI |
| Log in the UI | The ladder editor said "Exact, smaller files" for lossless: now only for Clear HDR (SDR: "Smaller files (SDR is sensor-compressed)"). With the ladder off the global Compression setting rules, not the ladder row's. A safety net re-sends the settings event when `cdng_log_applied` changes (`emitLogAppliedIfChangedLocked`) | none | Core, WebUI, touch UI |

Host test for the pre-roll: `tools/storage_preroll_test.cpp` (on `src/util/StoragePreroll.hpp`).

### Added 2026-11-01 (later): safety-stop pill and flush abort, clip names, preview LUTs

Core `fb5801c`, `c5db8b2`, `014a2bf` and UI `4959513`, `96a7aa4`, `606f137`, on top of `d44b177` / `841d0ed`. On GitHub (branch `drop-frames`), the Mac and the Pi. Status per row: **read from code**, **measured**, **untested**.

| Feature | What it does | Controlled by | Status |
| --- | --- | --- | --- |
| Pill READY green while the buffer empties (`fb5801c` / `4959513`) | After a safety stop the pill shows READY in green while the queue drains, also when the "Frame buffer bar" option is off (the WebUI polls `/api/buffer` for it) | none | read from code (WebUI, touch UI, HDMI) |
| Record during the safety-stop flush (`c5db8b2` / `96a7aa4`) | The pill leaves REC at the safety stop (the recording event is sent before the drain; REC and tally go off). Pressing record during the flush aborts the drain (`abortSafetyStopFlush`, `abortSafetyFlush` in the queue): the frames still queued are DISCARDED, frames a writer already took finish, the new take starts at once. The discarded count goes to `discarded_on_stop` (journal), state `buffer_flush_discarded` (kept until the next safety stop) and one toast ("Record pressed during the flush: N unwritten frames at the end of the previous clip were discarded."). A normal stop's drain and the pre-roll are not abortable. **Decision (the owner, 2026-11-01): discard the queued frames and start at once; the old clip is cut short, the frames already written stay** | the record button / `record_start` (before any lock the drain holds) | read from code; the abort itself untested |
| First real safety stop | 2026-11-01 01:00:35, 1289 of 1424 MiB, ram buffer, 4K lossless; the flush took about 3 s | `[storage] buffer=ram` | **measured** (hardware-log 2026-11-01) |
| Configurable clip names (`014a2bf` / `606f137`) | The clip folder name (and the DNG frames, `.wav`, `.mp4` that derive from it) comes from a template. Tokens: `{format}` `{date}` `{date_}` `{yy}` `{mm}` `{dd}` `{time}` `{time-}` `{tc}` `{tc-}` `{clip}` `{cam}` `{sensor}` `{model}` `{res}` `{fps}` `{bits}` `{comp}` `{log}` and free text `{text:..}` (24 characters). Presets: Original (`{format}_{date}_{clip}`, the default; names unchanged), Time of day with dashes (`{format}_{date_}_{tc-}_{clip}`), Time of day compact (`{format}_{date_}_{tc}_{clip}`). Rules: the clip number is the LOWEST free one for the expanded name; `{clip}` exactly once (a missing one is appended as `_{clip}`); at most 100 characters; only `A-Za-z0-9._-`; separator runs collapse; an empty token (e.g. `{log}` with Log off) drops with its separator; the name may not start with `Timelapse` (reserved for timelapse folders). `{tc}` is the wall clock plus the frame within that second at the current fps, taken when the folder is created (the DNG TimeCode tag is 00:00:00:00 in RecRun, so it cannot be used) | commands `set_clip_name_template`, `preview_clip_name`; state `clip_name_template`, `clip_name_example`; WebUI Settings > Record > Clip names (pill composer: HTML5 drag and drop with the mouse, pointer-event long-press with touch or pen, tap a palette pill to add, x removes); touch UI Settings > Record > Clip names card (`ClipNameCard.qml`: QML `Drag` / `DropArea` with tap fallbacks) | Core read from code; host test `tools/clip_name_test.cpp` on `src/util/ClipName.hpp`; WebUI composer and touch card **untested** by hand (the touch UI could not be tried: no touch screen on the rig) |
| Places that parsed the old name | Fixed to stop assuming `cDNG_<date>_C0001`: `ClipProbe.hpp` finds the lossy ratio from `cDNG_3to1` / `lossy3` anywhere in the name, `clipContainerTypeLabel` in `ApertarCoreApp.cpp`, the media library and clip labels, ProRes / H.264 detection | none | read from code |

### Preview LUTs (2026-11-01; not in git)

Core lists `*.cube` files from `/home/pi/LUTs`, `<media root>/LUTs`, `/media/RAW/LUTs` and `/media/*/LUTs` (`lutPreviewSearchDirectories`, `ApertarCoreApp.cpp`); the preview LUT is chosen with `set_lut_preview_file`.

- **Copied from DaVinci Resolve** (private, for the owner's own camera, not redistributed and not in this KB): the Sony S-Log3 / S-Gamut3.Cine LUTs from Resolve's LUT folder, and a custom `CE_Sony_SLog3 to Rec709.cube`, in `/home/pi/LUTs`.
- **Generated**: LogC4 / ARRI Wide Gamut 4, DaVinci Intermediate / DaVinci Wide Gamut and P3-D60 linear exist in Resolve only as built-in colour transforms (no `.cube` to copy), so three 65-point `.cube` files were computed from the published formulas: `Apertar ARRI LogC4 AWG4 to Rec709 gamma2.4.cube`, `Apertar DaVinci Intermediate DWG to Rec709 gamma2.4.cube`, `Apertar P3-D60 Linear to Rec709 gamma2.4.cube`.
- **Method** (script `gen_preview_luts.py`): for each lattice point (red varies fastest, then green, then blue) decode the transfer function to scene-linear (LogC4 per ARRI's LogC4 specification; DaVinci Intermediate per Blackmagic's Wide Gamut Intermediate whitepaper; P3-D60 is already linear), convert the primaries to XYZ and then to Rec.709 (D65; P3-D60 is Bradford-adapted from the D60 white to D65), encode pure gamma 2.4, hard clip to 0..1. No tone mapping, no film look. Output is plain Rec.709 / gamma 2.4, the same as Apertar's "Rec709 / Gamma 2.4" preview profile.
- **Checks done** (in the script's session): LogC4 18 % grey = 0.278396 in, DaVinci Intermediate grey = 0.336043 in, white and the neutral axis stay neutral. **Not compared with Resolve** (open test below).
- **Pairing rule: use the LUT that matches the preview colour profile.** The LUT assumes what the preview image is encoded as; a LogC4 LUT on a Sony S-Log3 preview, or any log LUT on an already Rec.709 preview, gives wrong contrast and colour. Pick the preview colour profile first (`set_cdng_preview_color_profile`), then the LUT named for the same curve and gamut.
- **Where the script lives**: `~/Downloads/apertar-preview-luts/` on the Mac (script plus the three `.cube`). The KB has `working/tools/` for helper scripts; moving it there is offered, not done (it was not asked, and the folder holds the generated LUTs too).

### Log works in Clear HDR 16-bit only (finding, 2026-11-01)

In SDR (12/10-bit) with Lossless JPEG the raw stream is PiSP COMP1 (compressed, lossy, step of 16 codes or more; see `../research-30fps/q7-cinemate.md`). Log's copy worker maps only unpacked 2-byte streams (`planCdngLog`), so it cannot map it: the journal says
`CineMate Log: pisp_comp1 raw stream cannot be mapped on the copy worker, recording linear`, `cdng_log_applied` is false and the UI says so.
Log therefore applies in Clear HDR 16-bit (unpacked) only. The root cause of an HDMI "· Log" that did not follow was not found in the code
(the settings event is built after the reconfigure); the re-emit safety net above covers it.

**Decision (the owner, 2026-11-01):** keep COMP1 for SDR (half the bandwidth: 8.3 MB against 16.6 MB per 4K frame; it is what makes 60 fps
possible) and do not build Log into the SDR lossless path (a Log plus uncompressed SDR stream would be bigger than Lossless JPEG: about
10.4 MB against 7.5 MB; sizes are estimates).

### Pre-roll measured, and the 30 to 24 lesson (2026-11-01)

Measured on the camera: 4K 12-bit SDR cDNG lossless, `storage_preroll_last` = `ok: 2.0 s at 60 fps (measured 60.0), 115 frames, 0.7 GB
written and deleted` (60.0 fps, 115 frames, 688 MB). The first attempt changed only the controls (`applyControls`): the sensor kept
delivering about 24 fps while the log reported 30. Fix: pin the frame duration and wait for the new period. Lesson in `lessons/hardware-log.md`.

### Ruled out or dropped

Sub-folders per clip, creating files ahead, `fallocate` preallocation, writer count, heat as the cause, a bigger queue or more camera buffers
as the fix for capture gaps (they happen before the queue), no in-take sync by default (plan row 2: A2), media tuning, cached SDR buffers
and scheduling parity (rows 3 to 5: shelved until a case needs them), the `discard` mount (deferred: the automounter lives in
Apertar-UI and online discard on exFAT may slow big deletes), and a pre-roll warm-up (no stated mechanism anywhere; the A/B in step 0b
is still written down but is low priority now that drive state explains the big effect).

### Open items (what to do next, in order)

1. **Targets (Patrik): 4K Clear HDR 16-bit 25 fps first, live picture at least 25 fps, original UI look.** The losses follow the touch UI's GPU preview work, mostly focus peaking (hardware-log 2026-11-01, "follow the touch UI's GPU preview work"). Best so far with peaking on: the CPU mask (`APERTAR_PREVIEW_PEAKING=cpu`, UI `4724007`) 3.9 %. Next: the DRM-plane preview like CineMate (`APERTAR_PREVIEW_PLANE=1`: camera on the primary plane, Qt UI on an ARGB overlay in atomic mode, peaking/zebra as GPU overlay marks), then the CPU mask on top. Still open: why A0 was clean with the touch UI running.
2. Open one Log frame in Resolve (12-bit LinearizationTable). Log on the SDR modes is settled: it records linear (see "Log works in Clear HDR 16-bit only").
3. Try `buffer=ram` in the Config pane and force a stall to see the safety stop; check the pill states on the HDMI screen and in the WebUI.
4. The acceptance test for trim: a series of 10-minute takes with deletes in between and no manual trims, past one full pass of the drive
   (4 to 5 takes), against a control with `APERTAR_MEDIA_TRIM=0`.
5. RTC power-off test; the `nvme.max_host_mem_size_mb=0` boot argument (remove it on a test boot).
6. A repeat of A2 and the unfinished A3 / A4 on a trimmed drive; the pre-roll A/B (step 0b): does a pre-roll warm the drive? It is one click now
   (`storage_preroll`), so take it before and after.
7. A 60 fps long take in 4K 12-bit lossless (and 40 / 50): the encoder estimate is about 69 fps (log `lossless timing`) and the data rate
   about 450 MB/s at 60 fps, both unverified over a long take.
8. The RAM queue plus the safety stop, and the safety-stop pill, on the Pi and the HDMI screen.
9. Speed ramp "After the take": stay and return, with a ramp that ends on a valid and on an invalid fps (untested).
10. Clear HDR override with the encoder: turn HDR on with the ladder on, check `ladder_override` and the 16-bit follow-up (untested).
11. HDMI "· Log" following `cdng_log_applied` (the safety net is untested).
12. The flush abort: provoke a safety stop (`buffer=ram`, a stalled drive or a low `buffer_stop_percent`), press record during the flush, then count the old clip's DNGs, read `discarded_on_stop` in the journal and `buffer_flush_discarded` in the state, and see the toast and the pill (REC leaves at the stop, READY green while it empties).
13. The clip-name card: set Time of day compact, record, `ls` the clip folder (names and the `.wav` follow); set Original and check the names are identical to before; drag pills in a browser (mouse DnD, and long-press with touch); the same on the touch UI (not tried: no touch screen).
14. The generated preview LUTs against Resolve exports of the same transforms (same test chart: grey ramp and a colour checker), per profile.

### Found after the reboot (2026-11-01 22:28-22:54; measured, reading not yet confirmed by Patrik)

**`APERTAR_DNG_DONTNEED=sync` (PR #3 knob) makes 4K Clear HDR 16-bit 25 fps clean with the touch UI running.**
3-minute takes, Core `64bbbaa`, UI `c13b846` with no switch, normal GPU preview, peaking + zebra on, audio meter off, WebUI
closed, script `/tmp/take3.sh` (copy in the Mac scratchpad of that session):

| Uptime | Core setting | Lost / 4500 | Free memory before | `pgsteal_kswapd` during the take | low-watermark hits |
| --- | --- | --- | --- | --- | --- |
| 1 min | default `writer` | 1 | fresh boot | not measured | - |
| 5 min | `writer` | 34 | 300 MB | 3.45 M pages | 1805 |
| 9 min | `writer` | 153 | 275 MB | 3.04 M | 948 |
| 13 min | `writer` | 71 | 327 MB | 3.02 M | 990 |
| 19 min | **`sync`** | **0** | 646 MB | 47 k | 8 |
| 23 min | **`sync`** | **0** | 507 MB | 58 k | 11 |

- Probable mechanism: with `writer` the fadvise(DONTNEED) runs on still-dirty pages, frees nothing and drains the per-CPU
  LRU lists on every core per frame (README knob table); the page cache fills (~2.6 GB) and kswapd then reclaims ~13 GB per
  3-minute take. That memory/CPU load plus the UI's display work starves the capture path (single-frame capture gaps).
  `sync` drops the pages after the once-a-second fsync, when they are clean.
- This explains the evening's drift and why a fresh boot was clean; the UI A/B results above were all measured under this
  cache pressure and need re-checking with `sync` before any UI change is kept (with `sync` the original UI is clean).
- Not yet done: a 10-minute take; making `sync` the default in Core (a one-line default change, Patrik decides); lossy DNG
  (the knob table says lossy then behaves as `off`); SDR 12-bit 33 fps; whether `sync` needs `APERTAR_MEDIA_SYNC_MS` > 0.
- The `/run` drop-in `apertar-core.service.d/dontneed.conf` is active until the next reboot.

### Where we stopped (2026-11-01 22:20; read first next session)

Measured tonight after the CPU-mask entry (hardware-log), **not yet confirmed by Patrik as a reading**:

| Setup (4K Clear HDR 16-bit 25 fps, peaking + zebra on unless noted) | Takes | Lost |
| --- | --- | --- |
| `APERTAR_PREVIEW_PLANE=1` (picture on the DRM primary plane, UI c13b846) | 60 s, 48 s, 110 s, 3 min, Patrik 17 s | 0, 1.8, 1.9, 3.4, 1.7 % |
| plane + `APERTAR_PREVIEW_PEAKING=cpu` | 3 min | 3.1 % |
| plane, peaking + zebra off | 3 min | 7.2 % (Qt timing: 37 redraws/s, render 0.7 ms, swap 18.6 ms: flips wait, GPU idle) |
| touch UI stopped, 22:01 | 60 s | 0.13 % |
| GPU preview, GPU IRQs moved to CPU2 (`/proc/irq/173,174`), WebUI open | 3 min | 14 % |
| the same, WebUI closed | 3 min | 18 % |
| fresh Core (22:14), IRQs back to 0-3 | 3 min | 11 % |
| one more, compaction counters | 60 s | 17 % |
| Patrik, after format, SDR 12-bit **uncompressed** 30 fps | 5 s | 24 %; SDR 12-bit lossless 30 fps: 0 |

- **Drift**: the same GPU-preview setup went from ~7 % (19:09-20:30) to 11-18 % (22:00-22:20) although Core, the UI and the
  card (formatted 21:50, trimmed) were fresh. Not heat (SoC 55-57 C, `throttled=0x0`). With the UI stopped it was still clean.
  Memory is fragmented (`/proc/buddyinfo`: no free block >= order 8 in any node; `compact_isolated` 4.8 M pages since boot;
  kcompactd woke 28x in a 60 s take vs 2x idle; CmaFree 0-0.8 MB of 64 MB). Probable contributor; not established.
- All of CPU0 serves rp1-cfe (IRQ 154), v3d (173/174), hvs (175, cannot be moved), usb4 (~700/s) and i2c 1f00074000 (~600/s).
  Moving v3d to CPU2 did not help.
- **Next session, in order**: (1) reboot; (2) baseline 3 min, GPU preview, aids on, WebUI closed (is it back to ~7 % or below?);
  (3) the same with `APERTAR_PREVIEW_PLANE=1`; (4) if (2) is low: repeat every ~30 min to see the drift return, with
  `/proc/vmstat` compaction counters and `buddyinfo`; try `buffer=frames` (no 1.4 GB RAM pool per take) and
  `vm.compaction_proactiveness=0`; (5) why i2c 1f00074000 fires ~600/s.
- State left on the Pi: UI `drop-frames` c13b846 with no switch active (no `/run` drop-in), UI.conf peaking+zebra on,
  audio meter OFF (Patrik turned it off for a test; turn back on), Core 64bbbaa restarted 22:14, IRQ affinity 0-3, card
  formatted (exFAT). The A0-era UI build is in `~/ApertarUI-a0` (unused).

### How to run the new build

On the Pi (`controls` is the old branch, kept as the rollback): `git switch drop-frames` in `~/ApertarCore` and `~/ApertarUI`, then
`cmake --build ~/ApertarCore-build -j2` and `cmake --build ~/ApertarUI/build -j2`, never during a take. The helper install block is in the
Core README; then `sudo systemctl restart apertar-core apertar-ui-direct`. The `[storage]` keys are commented in the default file text; paste
the block into the Config pane to use them.

## 1. The question

Patrik sees more dropped frames with Apertar than with CineMate on the same kind of rig (Pi 5,
IMX585, 4K 25 fps, 16-bit Clear HDR, exFAT on a CFexpress card or NVMe). Why, and what to port.

A frame is lost in Apertar at one of four counted places. The first thing every measurement must
do is say **which counter moved**; the remedies differ.

| Counter (stderr line) | Where | Meaning |
| --- | --- | --- |
| `drop[queue-full]` | `DngRecordingQueue::enqueue` / `hasCapacityForFrame` | the write queue held `maxQueuedFrames_` frames (12 by default): the disk fell behind for more than ~0.5 s |
| `drop[copy-slot]` | `DngRecordingQueue::enqueueCopy` | the copy worker still held `buffers-2` requests: a slow memcpy or a stalled enqueue |
| `drop[capture-gap]` | `CameraSession` cadence tracker | libcamera delivered no frame for a period: the CFE skipped (writeback contention, pipeline-thread stall) |
| `drop[requeue-failed]` | `CameraSession` | a request could not go back to the camera |

`working/tools/takes.sh` prints missing frames, the queue peak and delivery per take; the journal
carries the lines above.

## 2. What the two stacks do differently (confirmed from source)

| Stage | Apertar `cinemate-port` @ `7678cbf` | cinepi-raw @ `63a08d5` + cinemate @ `4990afc` |
| --- | --- | --- |
| Backlog policy | write queue bounded in **frames**: 12 (ext4/exFAT profile), 24 for compressed formats, env `APERTAR_CDNG_QUEUE_FRAMES` max 64; when full the frame is **dropped** (`src/camera/CameraController.cpp` anchor `defaultQueueFrames`, `drop[queue-full]`) | encode threads **block** on a RAM permit sized at 90 % of `MemAvailable` at take start (`cinepi/dng_encoder.cpp` anchors `RAM_FRACTION = 0.90`, `ram_cv_.wait`); the capture loop only ends the take when the pool is gone (`cinepi/cinepi_raw.cpp` anchor `RAM pool exhausted`). 173 frames ≈ 2.9 GB on a 4 GB CM5 (`handbook hardware-log 2026-08-27/28`) |
| Cushion at 4K25 16-bit (16.9 MB/frame) | ~0.5 s (12 frames, 203 MB) | ~7 s on 4 GB, ~12 s on 8 GB |
| Sync during the take | `sync_file_range` per DNG (`startWriteback`, `APERTAR_DNG_WRITEBACK` default on); once a second `fsync` of every DNG finished in that second, then the clip folder (`syncLoop`, `APERTAR_MEDIA_SYNC_MS` default 1000); `syncfs` at stop | none. `open`, `write`, `close`, `posix_fadvise(SEQUENTIAL)` (`diskThread`, anchor `Use standard buffered IO instead of O_DIRECT`); `fadvise(DONTNEED)` was removed in `b71ec67` (2026-03-06) |
| Kernel knobs at mount | ported helper `scripts/apertar-media-tune` (dirty_bytes cushion, scheduler none, nr_requests, rq_affinity, NVMe APST 0) but **opt-in**: `APERTAR_MEDIA_TUNE=1` (`e9dd6b2`) | `services/storage-automount/storage-automount.py`: per connection class `dirty_bytes` 256 MiB–1 GiB, `dirty_background_bytes` 128–256 MiB, `dirty_writeback_centisecs` 150, scheduler none, `nr_requests` 256–512, `rq_affinity` 2, `nvme_core.default_ps_max_latency_us` 0; **default on** for `/media/RAW` |
| Process scheduling | callback thread `setpriority(-5)` under `LimitNICE=-5`; everything else nice 0, no affinity, no ionice | whole `cinepi-raw` process `chrt -f 70`, `ionice -c2 -n0`, `taskset -c 1-3` (`src/module/cinepi_multi.py` `run()`), allowed by `LimitRTPRIO=80` on the unit and `@audio - rtprio 80` in `limits.d`; installer adds `isolcpus=managed_irq,domain,N nohz_full=N rcu_nocbs=N irqaffinity=0..N-1` for the audio core |
| Worker nice | n/a | `--encode-nice -10 --disk-nice -5` **fail** with `Permission denied` on every take (handbook `open-threads.md` "DNG disk workers cannot set their nice level"): contributes nothing |
| Raw camera buffers | 4 SDR, 8 Clear HDR (+2 for FAT/NTFS profiles, 0 for exFAT/ext4), env `APERTAR_RAW_CAMERA_BUFFERS`; held by workers ≤ buffers-2 | `--buffer-count` 8 (ext4/default) or 10 (exFAT/NTFS) from `storage_profiles.py` |
| Buffer cacheability | CPU-cached heap only for Clear HDR unpacked and PiSP COMP1 (`allocateCachedBuffers`, anchor `settings_.clearHdr && rawStreamInfo_.packing == PixelPacking::Unpacked`); SDR raw reads uncached | libcamera default allocation; the DNG is assembled straight from the camera buffer on an encode worker |
| Copies per frame | 1 memcpy on the copy worker (+ a LUT pass in 12-bit Clear HDR), then the writer's row chunks | 1 (camera buffer → pooled TIFF block on the encode worker), then `write()` |
| Per-frame syscalls | ~40 (`write` per 491 520-byte chunk, header, pad, IFD, 2 fadvise, open, close) + `sync_file_range` | ~5 (open, fadvise, one `write`, close) |
| Bytes per frame, 4K 16-bit Clear HDR | 16.9 MB (16-bit) or 12-bit with a LinearizationTable (`57c8fb0`) | 16.9 MB linear, **or 12.7 MB with CineMate Log** (`--log-encode 12`), or 10.6 MB (`10`) |

### What is already measured on this Pi (hardware-log 2026-10-26/27)

- The once-a-second **`syncfs`** cost 12 capture gaps in 3 min; **per-file `fsync` + folder fsync**
  measured **clean** for 3 min at 38 % full (`cDNG_26-10-27_C0002`, 4494 frames, 0 missing).
- A **77–81 % full** card lost 166–676 frames to `queue-full` in 3 min; a fresh format fixed it
  (**probable**: the card's write cache shrinks as it fills).
- T22: dirty-page tuning alone did not remove Clear HDR gaps (those gaps were the uncached-buffer
  problem fixed by `94ac68d`).
- `e9dd6b2`: 16-bit 4K25 ran clean without the media helper, which is why it became opt-in.

So the fsync is not the proven cause on an empty card. It is the first thing to remove **if the
A/B says so**, and Patrik has agreed to lose it. The unanswered question is where today's drops are
counted; the plan starts there.

### Confounders (check before comparing numbers)

1. **Bytes per frame.** If CineMate runs with LOG on, it writes 12.7 MB per 16-bit frame; Apertar
   writes 16.9 MB. Compare at the same stored depth, or port log first (§4).
2. **Card fill.** Both stacks slow down on a nearly full card; compare at the same fill.
3. **Clear HDR 16-bit soaks stalled on CineMate too** (handbook 2026-08-27/28, NTFS via FUSE, ~355 MB/s):
   its advantage is burst absorption, not a faster disk.
4. **Thumbnail.** cinepi-raw writes a 691 KB IFD1 thumbnail per frame by default; Apertar none.

## 3. Remedy plan for Apertar (in order)

Step 0 needs no code. Each later item is one commit, A/B-able by its env knob so the knob matrix
stays usable for regression tests.

| # | Change | Where | Env for A/B | Expect |
| --- | --- | --- | --- | --- |
| 0 | **A/B soak matrix**: 10-min takes, 4K25 16-bit, same card at < 50 % full, one knob per run, count the four `drop[...]` lines | Pi, no build | `APERTAR_MEDIA_SYNC_MS=0`, `APERTAR_DNG_WRITEBACK=0`, `APERTAR_CDNG_QUEUE_FRAMES=64`, `APERTAR_RAW_CAMERA_BUFFERS=10`, `APERTAR_MEDIA_TUNE=1` (needs the sudoers + libexec install) | tells which counter moves and which knob stops it |
| 0b | **Pre-roll A/B** (CineMate's storage pre-roll: a 2 s take at the mode's max fps, deleted, on startup and mount). Runs right after the overnight sub-folder/heat run. Protocol below | Pi, no build | none (defaults environment) | settles whether a short max-fps take before the real one changes its drops; no port unless the rule below says so |
| 1 | **RAM-bounded queue, block instead of drop.** Budget = a fraction of `MemAvailable` at take start (cinepi-raw uses 0.9; start at 0.6 and keep 512 MiB free), in bytes, not frames. Copy worker **waits** while the budget is full; drop only at the copy-slot cap; a pool-exhausted stop ends the take like cinepi-raw. Expose `queue_bytes`/`queue_budget_bytes` in `get_state` for a buffer bar | `DngRecordingQueue` (`maxQueuedFrames_`, `enqueue`, `hasCapacityForFrame`, `copyLoop`, `acquireRawBuffer` pool) | `APERTAR_CDNG_QUEUE_RAM_FRACTION`, `APERTAR_CDNG_QUEUE_FRAMES` kept as a ceiling | queue-full drops become seconds of cushion |
| 2 | **No sync during the take by default.** `APERTAR_MEDIA_SYNC_MS` default 0, `APERTAR_DNG_WRITEBACK` default off; keep the stop-time `syncfs`; keep the audio raw fsync | `DngRecordingQueue::start`, `startWritebackPerFrame`, `syncLoop` | the same two knobs | fewer capture gaps if writeback bursts were the cause; a pulled card loses up to `dirty_expire` |
| 3 | **Media tuning on by default** (the e9dd6b2 objection was the 1 s bound, gone with #2). Installer step for `/usr/local/libexec/apertar-media-tune`, `/etc/sudoers.d/apertar-media`, tmpfiles | `ApertarCoreApp::applyMediaTuning`, `scripts/`, `config/` | `APERTAR_MEDIA_TUNE=0` to disable | bounded dirty pages, NVMe APST off on the CFE, scheduler none |
| 4 | **Cached buffers for SDR raw, 8 of them.** Extend the cached-heap condition to unpacked SDR; `kConfiguredBufferCount` 4 → 8; keep +2 for FAT/NTFS | `allocateCachedBuffers` call site, `rawCameraBufferCount` | `APERTAR_RAW_CACHED_DMABUF`, `APERTAR_RAW_CAMERA_BUFFERS` | copy-slot drops in SDR disappear; CMA use +4 × 16.9 MB |
| 5 | **Scheduling parity.** `LimitRTPRIO=80` on `apertar-core.service`; start script prefix `chrt -f 70 ionice -c2 -n0 taskset -c 1-3` behind `APERTAR_RT=1`; fallback: SCHED_FIFO on the completion and copy threads only | `scripts/start-apertar-core.sh`, `config/` drop-in, `CameraSession::requestComplete` | `APERTAR_RT` | capture thread no longer waits behind writers and the WebUI |
| 6 | **CineMate Log for Apertar** (§4): 20–25 % fewer bytes per frame at the same picture, in parallel with every compression | encoder + format model + UIs | setting, not env | the same card carries 25 fps with margin |

### Where it stands

See section 0 (outcome, findings, what was built). Rows 1 to 5 of the table above were re-planned by the findings:
row 1 became the `frames` / `ram` buffer switch (done), row 2 is dropped (A2), rows 3 to 5 are shelved, row 6 (Log) and the
new trim item are done and wait for their Pi tests.

### Step 0b: the pre-roll A/B (next step, after the overnight run)

**Why it is a question.** CineMate records 2 s at the sensor's max fps on startup (after 1 s) and on every
mount (after 3 s), then deletes the clip (`src/module/storage_preroll.py`, setting
`system.storage.auto_preroll`, default on). No file names what it warms and nothing measured it
(`working/port-raw/s1-storage-cinemate.md` §3, `working/port-raw/critic.md` S4; T29 §5.3 planned the
first-take vs second-take comparison and it was never run). Apertar has no pre-roll. The KB's own guesses
(not CineMate's claims): wake the NVMe from a deep power state (already off here by the boot argument
`nvme_core.default_ps_max_latency_us=0`; re-read it this boot), warm exFAT's allocator, show a slow drive early.
Our stalls so far come minutes into a take, so the prior is low; the test is cheap.

**Protocol** (real takes inside Core; same card, < 50 % full; defaults environment, no drop-in; 4K 25 fps
Clear HDR 16-bit uncompressed; Core started again after the overnight run):

| Arm | Before the real take | Real take |
| --- | --- | --- |
| COLD | remount (Patrik), drive idle until it reads <= 55 °C, then 10 s | 240 s |
| WARM | the same remount and idle, then the pre-roll: `record_start`, 2 s, `record_stop`, delete that clip, 3 s settle (CineMate's `settle_delay`) | 240 s |
| SECOND (control) | none: runs straight after a COLD take, no remount (the T29 §5.3 first vs second take) | 240 s |

- 6 pairs, COLD and WARM alternated (start with either in turn), each pair at least 10 min apart so the drive
  starts at the same temperature; the SECOND take follows each COLD take.
- Recorded per take: each `drop[...]` counter in the first 30 s and in the rest of the take, frames missing,
  `peak_queue`, stop `syncfs` ms, NVMe temperature at start and max (sysfs, every 5 s). Every take starts with
  the same readback of the environment the unit holds.
- Decision rule: the pre-roll earns a port only if WARM beats COLD in at least 5 of 6 pairs, by more than the
  take-to-take spread the overnight run measured for equal conditions. Otherwise the result is written down as
  "no effect on this rig" (hardware-log entry, after Patrik confirms the reading). If it passes, the port is a
  setting (`storage_preroll`, default off at first), never a hidden step, and it must never run while recording.
- Needs from Patrik: `sudo systemctl start apertar-core` (Core is stopped for the overnight run) and the remount
  commands. Claude reads the automounter's own mount path first (read-only) and gives the exact block.

Not worth doing: worker nice levels (CineMate's fail silently); O_DIRECT (T24 skipped, neither
stack ships it).

### Done means

Ten-minute 4K25 16-bit uncompressed take on a < 50 % full card: 0 in every `drop[...]` counter,
queue peak < 25 % of budget, stop `syncfs` < 200 ms; the same with lossless JPEG and with Log 12;
SDR 12-bit at 50 fps unchanged; a pulled card still ends the take as `media_removed` (T28).

## 4. CineMate Log for Apertar: the design

### What it is (cinepi-raw, confirmed)

A per-sample LUT applied before packing: mu-law companding of the signal above black plus a short
linear footroom below black, into `target_bits` codes; the inverse table is written as the DNG
`LinearizationTable` (tag `0xC618`), `BlackLevel`/`WhiteLevel` stay in the linear domain, so any
DNG reader decodes to linear with no LUT. `cinepi/log_lut.hpp` (BSD-2-Clause) is the whole curve;
specs per depth pair ship as JSON with the generator's own table and are cross-checked at load.
A companded 12-bit Clear HDR source is **decompanded first** and then log-encoded with the 16-bit
spec (`build_ccmp_composed`), never with the 12-bit one. Operator model in cinemate
`docs/cinemate-log.md`: Off / On (mode default: 16→12, 12→10) / Force 10 / Force 12; a LOG button
in the Web GUI; a per-camera setting; CineMate has no lossy mode, so it never had to combine them.

Patrik's rule for Apertar: **one step down**: 16 → 12, 12 → 10, 10 → 8, with an explicit target
allowed when it is below the source depth.

### What Apertar already has (confirmed, `cinemate-port` @ `7678cbf`)

- `CdngEncoder::Metadata::linearizationTable` (span of `uint16_t`, must be `2^bitDepth` long) and
  tag `0xC618` emission; `WhiteLevel` from the table's last entry (`src/cdng/CdngEncoder.cpp`,
  anchors `metadata.linearizationTable`, `0xC618`).
- A 65 536-entry forward LUT pass on the **copy worker** for 12-bit Clear HDR
  (`compressClearHdrFrame`, `src/cdng/ClearHdrCcmp.hpp` `compressionLut()`), i.e. exactly the hot
  path a log encode needs; the CCMP expansion table for the composed case.
- Row packers for 8/10/12/16-bit storage (`writeDngRowBytes`, `RawBitDepth`), and the lossy
  path's companding (`src/lossydng/LossyDngEncoder.cpp` `buildCompanding`: square-root curve +
  quantisation + SOF3), which is where the log curve plugs in for Lossy + Log.
- Sensor black level per mode (`src/cdng/BlackLevel.hpp`), the Clear HDR white clamp.

### The format model today, and where Log goes

| Axis | Commands / keys | WebUI | Touch UI | Mode Ladder |
| --- | --- | --- | --- | --- |
| Format | `set_record_format` cdng/mlv/h264/lossydng/prores; state `recording_format` | Recording format card, format buttons | `recordFormatComponent` (`SettingsPage.qml`), `applyRecordingFormat` | per resolution: `compression` |
| Compression | `set_cdng_compression` none/lossless_jpeg; Lossy is a *format* with `set_lossy_dng_ratio` 3:1/5:1; the WebUI select mixes them and `dispatchCdngCompressionSelection` splits | `settingsCdngCompressionSelect` | `applyCdngCompression` | `none`, `lossless_jpeg`, `lossy_3to1`, `lossy_5to1` (`src/camera/ModeLadder.hpp` `knownCompression`) |
| Bit depth | `set_raw_bit_depth` 8/10/12/16; state `raw_bit_depth` | Bit Depth card | `applyRawBitDepth` | per resolution `bits` |
| Clear HDR | `set_clear_hdr`; state `clear_hdr` | switch | switch | per resolution `hdr\|sdr` |

**New axis: storage depth (Log).** It is not a compression and not the sensor bit depth (it is what
is *stored*). Patrik's rule: **Log runs in parallel with every compression**, Uncompressed, Lossless
JPEG and Lossy alike; it is an extra option, never a mode of its own.

| Item | Design |
| --- | --- |
| Setting | `cdng_log`: `off` \| `auto` \| `12` \| `10` \| `8`. `auto` = one step below the source depth. An explicit target ≥ source depth records linear and the state says so (CineMate's rule: not an error) |
| Command | `set_cdng_log value=off\|auto\|12\|10\|8`; applies to cDNG in all three compressions and to Lossy DNG; refused in H.264 and ProRes with the reason; MLV only if MLV readers honour a LinearizationTable (**unconfirmed**: MLV has no such block; start with cDNG and Lossy) |
| State | `cdng_log` (the setting), `cdng_log_bits` (0 = linear, else the stored depth), `cdng_log_available` (false in H.264/ProRes and when the source has no curve) |
| Persisted | `[camera] cdng_log` in `apertar-hardware.conf`, carried across formats like `fps_phase_lock`; presets carry it (allow-list in `apply_preset`) |
| Mode Ladder | the resolution text gains an optional sixth field: `WIDTHxHEIGHT:BITS:hdr\|sdr[:FPS[:COMPRESSION[:log\|log10\|log8]]]`; `effectiveCompression` unchanged; the ladder's JSON gets `log_bits`; the FPS ceiling per compression is measured at the stored depth |
| Encoder | a pure header `src/cdng/LogCurve.hpp` (port of the mu-law + footroom math, not a copy; constants from a generator script kept in `tools/`), built once per (source bits, black, white, target) and cached; applied on the **copy worker** next to `compressClearHdrFrame` (composed with the CCMP expansion in 12-bit Clear HDR); the frame view's `bitDepth` becomes the target so the existing packers and `whiteLevel(layout.bitDepth)` logic follow; `Metadata.linearizationTable` = the inverse table; `BlackLevel` tag stays linear |
| Lossless JPEG + Log | the predictor runs on log codes, which compress at least as well as linear |
| Lossy + Log | the Lossy encoder's own square-root companding (`buildCompanding` in `src/lossydng/LossyDngEncoder.cpp`) is **replaced** by the log curve at the chosen target depth when Log is on; the 3:1 / 5:1 quantisation and SOF3 coding run on the log codes as they run on the square-root codes today, and the file's `LinearizationTable` is the log inverse. One companding per file, never two |
| Size model | `estimatedRawBytesPerSecond` and the WebUI/touch "Time left" use `cdng_log_bits` when non-zero |
| WebUI | Recording format card: a **Log storage** select under Bit Depth (Off / On, one step down / 12-bit / 10-bit / 8-bit), live in every compression including Lossy; the resolution badge reads `4K · 16-bit · Clear HDR · Log 12`; a `LOG` pill on the Live preview row like CineMate's button toggles `auto`/`off` |
| Touch UI | a Log row in `recordFormatComponent` next to Bit Depth (`applyCdngLog` in `ApertarControlBridge`), the FORMAT row subtext shows `Log 12` |
| Sensors | black/white per sensor and mode come from Core's own tables, so IMX477/IMX294 work from day one (the CineMate limitation was spec selection, not the sensor) |

Bytes per 4K frame (3840×2160, no thumbnail): 16-bit 16.6 MB → Log 12 12.4 MB (−25 %); 12-bit
12.4 MB → Log 10 10.4 MB (−17 %); 10-bit 10.4 MB → Log 8 8.3 MB (−20 %).

## 5. Open questions (answer on the Pi)

1. Which counter carries today's drops at 4K25 16-bit on a < 50 % full card? (`takes.sh 1 600`, then
   `journalctl -u apertar-core | grep 'drop\['`.)
2. Does the kernel's own writeback (no fsync, no `sync_file_range`) stall the CFE on this board the
   way `dd conv=fdatasync` did on 2026-10-26? (Step 0, knob 2 alone.)
3. CMA headroom for 8 cached SDR buffers at 4K: `grep Cma /proc/meminfo` before and after.
4. Does `chrt -f 70` on the whole process starve the WebUI's MJPEG thread? (Step 5, watch the preview.)
5. Log: does Resolve honour `LinearizationTable` on an 8-bit stored DNG? (Export one frame, open it.)
6. Does a CineMate-style pre-roll (2 s at max fps, deleted) before the real take change its drops? (Step 0b:
   COLD vs WARM pairs, plus the SECOND-take control.)

## 6. Sources

- Apertar-Core `cinemate-port` @ `7678cbf`: `src/camera/CameraController.cpp` (class
  `DngRecordingQueue`, `syncLoop`, `startWriteback`, `rawCameraBufferCount`, `allocateCachedBuffers`),
  `src/util/MediaProfile.hpp`, `scripts/apertar-media-tune`, `config/apertar-core-capture-priority.conf`,
  `src/cdng/CdngEncoder.cpp`, `src/cdng/ClearHdrCcmp.hpp`, `src/lossydng/LossyDngEncoder.cpp`,
  `src/camera/ModeLadder.hpp`, `src/web/WebControlPage.cpp` (Recording format card).
- cinepi-raw @ `63a08d5`: `cinepi/dng_encoder.cpp`, `cinepi/cinepi_raw.cpp`, `cinepi/log_lut.hpp`,
  `cinepi/log_lut.cpp`, `cinepi/log_encode_arg.hpp`, `cinepi/dng_output_depth.hpp`.
- cinemate @ `4990afc`: `src/module/cinepi_multi.py`, `src/module/storage_profiles.py`,
  `services/storage-automount/storage-automount.py`, `services/cinemate-autostart/*.service`,
  `cinemate-install.sh` (`configure_cmdline`, `configure_audio_rtprio`), `docs/cinemate-log.md`.
- cinemate-handbook @ `c99ff77`: `architecture/cinepi-raw.md`, `lessons/hardware-log.md`
  (2026-08-27/28, 2026-09-13/14/15), `open-threads.md` ("DNG disk workers cannot set their nice level").
- This KB: `working/clearhdr-compare-answer.md` (theory A and B), `working/compare-raw/*.md`,
  `lessons/hardware-log.md` 2026-10-26/27, `tutorials/progress/T29.md`.
