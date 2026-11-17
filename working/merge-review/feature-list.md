# Feature list: what the cinemate port adds to Apertar

One page for all areas. It lists what the port lets an operator do that original Apertar 1.6.0 could not. Commands,
state fields, config keys, env knobs, commits and test notes are in the area files:
`feature-list-camera-modes.md` (C), `feature-list-controls-system.md` (H), `feature-list-recording-media.md` (R),
`feature-list-webui.md` (W), `feature-list-touch-ui.md` (T). The Src column gives the row number there.

Refs: Core `cinemate-port` `01f170c`, UI `7ea9afc`, imx585 `cd548ef`, imx283 `68b7dc9`. Baseline `upstream-1.6.0`.
Relation: **new** = new area with no upstream code; **beside** = added next to upstream code; **extends** = upstream
code changed in place; **replaces** = upstream code removed for the port's. Default: what a stock camera gets on
`cinemate-port`. Where the improvement branch `work/improve` already changed it back, the column says so. Tested: what
the commit texts and `fork-log.md` record. "desk" = built or run on the x86 desk machine, never on a camera.

## Camera, sensors and modes

| Feature | Operator gets | Relation | On by default? | Tested where | Src |
| --- | --- | --- | --- | --- | --- |
| Mode Ladder | An ordered size list. The chosen FPS picks size, bit depth, Clear HDR and compression between takes. A ceiling per entry holds during a take | new, hooks into six setters | off | Pi 2026-10-28 (socket, two takes, presets); Clear HDR override not run | C1 |
| IMX585 modes from tables | 40 SDR sizes per depth, Clear HDR lists, 1:1 and 2.55:1 crops, 10-bit. The 1.85:1 crops are renamed 2072/1036 | replaces the whitelist code | on: new size list, modes under 1280 wide hidden | desk only | C2 |
| IMX585 driver modes and timing | 187 modes incl. RAW10 4K, crops with real sensor windows, new HMAX/VMAX tables | replaces driver tables | on once the driver is installed | Pi: crops listed 2026-10-26, 7-mode pass 2026-08-31; 1920/2048 families host only | C3 |
| IMX585 driver Clear HDR colour and gate | 12- and 16-bit binned 1080p Clear HDR, colour by default, mono needs `ccmp`, a developer gate for windowed binning | extends driver functions | on for colour | CM5, link 891 MHz, 7 modes; windowed gate never run | C4 |
| IMX283 sensor family | An IMX283 module works: 57 modes, active-area crops | extends sensor enum and switches, new driver port | nothing unless an IMX283 is fitted | Core desk only; driver built, one preview frame, DNGs 2x2 only | C5 |
| Mode geometry controls | `v4l2-ctl` shows binning, crop and active area per mode | beside, in both drivers | on with the new drivers | Pi 2026-10-26 (585); 283 on CM5 | C6 |
| Sensor-probe FPS ceiling | 4K SDR up to 60 fps; IMX585 lossless no longer capped at 30; `fps_max` in state | extends the fork-main probe, flips the rule | on: higher ceilings | host test; Pi note: 4K Clear HDR 16 reaches 27 fps | C7 |
| Binning and crop per mode | `list_sensor_modes` and state say binning and crop | extends the fork-main probe | on | Pi (`list_sensor_modes`, `get_state`) | C8 |
| Values the camera decides | Auto ISO and WB freeze in Clear HDR and return in SDR. Screens show the gain or Kelvin in use, held values in italics, `iso_actual`, `iso_max`. An ISO Lock entry freezes auto ISO at the measured gain | extends setters and screens in place | on (holds only in Clear HDR) | Pi preview 2026-10-28; touch `f1edf96` by Patrik; `7840438`, `35b31f6` built only | C9, T2 |
| Preview temporal denoise switch | A faster preview at 4K Clear HDR 16-bit. DNGs unchanged | beside the tuning-file selection | port: off. `work/improve`: on, as 1.6.0 (`3650027`); the switch now leaves H.264, ProRes alone | desk; Pi build 2026-11-04 | C10 |
| Raw camera buffer count | Fewer capture gaps: 4 buffers SDR, 8 Clear HDR, +2 on FAT/NTFS. No control | replaces a constant | on, silent | Pi 4K Clear HDR 16-bit: gaps 41 to 1 | C11 |
| Frame-rate phase lock | A servo holds the sensor frame rate against the audio clock on long takes | new (header-only servo) | off | owner's long-take drift check on the Pi | C note, CAM-28 |
| Conform FPS | A setting that is saved, set and published, with no reader and no control | new, no consumer | stored as 25, does nothing | none | C note, CAM-18 |

## Recording, files and audio

| Feature | Operator gets | Relation | On by default? | Tested where | Src |
| --- | --- | --- | --- | --- | --- |
| Pulled-drive survival, media state, record gate | A pulled or dead drive ends the take with a named fault instead of a hang. Files up to the pull stay. Record is refused with a reason without media or under 1 GiB free | beside, replaces the `stop()` join | on | Pi 2026-10-26 pull tests | R1 |
| Take durability | A pull or crash keeps the take up to about the last second; the sync no longer causes queue drops | new (1 s sync, writeback, DONTNEED modes) | on (DONTNEED=sync) | Pi pull test C0011 | R2 |
| Media profile, tuning file, kernel tune | Writer count, queue depth and raw buffers follow the mounted medium; a tester's tuning file and `apertar-tune`; optional kernel tuning | extends, new | profile on; tune file absent; kernel tune off | built; mostly not run | R3 |
| Direct DNG payload write | Fewer drops in Clear HDR 16-bit: one `write()` per frame instead of a 16.6 MB copy and 34 writes | extends in place | on | host test only | R4 |
| Raw copy hand-off and warm raw pool | Fewer drops on 16-bit takes: the copy leaves libcamera's thread; first frames no longer wait for allocations | beside, replaces | on | Pi 4K Clear HDR takes; pool syntax only | R5 |
| Log for cDNG, lossless JPEG and Lossy DNG | About 25 % smaller files (16 to 12 bit); the inverse curve in the DNG LinearizationTable | beside | off | Pi 16 to 12 once; not opened in Resolve | R6 |
| One black and white level for MLV and cDNG | MLV from 16-bit takes carries the right black level (about 3200, was 200) | moves and rewrites | on | host test only | R7 |
| Audio writer thread, 1 s fsync, drift fit | Fewer audio dropouts when storage stalls; a pulled card keeps the audio; WAV drift fitted over all block stamps | replaces | on | Pi (fit, pull test) | R8 |
| Speed ramp | FPS can change inside a cDNG/MLV take. WAV length and timecode stay right; optional `<clip>_stretched.wav` follows the slow motion | extends, new | ramp off; stretch on when the ramp is on | Pi 2026-10-28 | R9 |
| Clip name templates and composers | Clip folder, frame, sound and video names from tokens and text, with a live example. WebUI drag composer, touch Clip Names card | replaces the naming code; new page and touch cards | on; default name unchanged byte for byte | Core host test; WebUI page not run; touch card untested on the panel | R10, W4 |
| Dropped-frame count, pre-roll mute | The UIs show the running drop count instead of a bare "!"; pre-roll drops are not reported | extends in place | on | Pi | R11 |
| RAM write buffer, buffer bar, safety stop | The write queue can be sized from free RAM. A red bar in the REC pill shows the fill. At 90 % the take ends with every frame written; record during the drain starts a new take | extends, new | off (frames mode); bar off | Pi 5 once 2026-11-01; pill states not seen on screen | R12, T4, W6 |
| Storage pre-roll | A 2 s raw test take at the mode's top fps, deleted after, to warm the drive; a blue PRE-ROLL pill | new | port: auto on (boot, card insert, format). `work/improve`: off (`0977dd6`) | Pi 5 2026-11-01 | R13 |
| Split takes and merge worker | Frames go into `<clip>/part_NNN/` every N frames to avoid the exFAT create cost; Core merges them back while idle; `flatten_clip.py` by hand | extends, new | split off (0); merge on | desk, Pi build | R14 |
| Drive trim | The drive is trimmed after a delete of 1 GiB or more and at mount, never in a take | new | on | Pi mount trim | R15 |

## Media and playback (WebUI)

| Feature | Operator gets | Relation | On by default? | Tested where | Src |
| --- | --- | --- | --- | --- | --- |
| Clip Browser | A grid of clip cards (thumbnail, duration, drops, format, date, timecode), filter, sort, multi-select, download and remove. Fast listing from a facts cache | replaces the media list; new Core route | on | headless Chrome against a Pi's Core 2026-10-29 | R16, W1 |
| Clip Viewer | Play a clip in the browser: scrub, frame step, previous/next, histogram, recorded timecode, black for dropped frames, Info panel, sound with the WAV as the clock | new (second JPEG decoder) | on | Pi 2026-10-29, Chrome only | R17, R19, W2 |
| Playback hold, yielding downloads and deletes | Playback and downloads stop before a take, photo, timelapse, media test, standby or eject; a delete waits for pending writes | beside, extends | on | Pi 2026-10-29 | R18 |
| Playback of every DNG size Core writes | IMX283 and IMX294 clips open in the browser and viewer (before: refused above 4096x3072) | beside | on | host test only | R20 |
| Web preview rate cap in raw takes | The WebUI MJPEG preview can be capped or paused during a raw take | extends in place | off (30 fps) | not run | R21 |

## Controls, hardware file and system

| Feature | Operator gets | Relation | On by default? | Tested where | Src |
| --- | --- | --- | --- | --- | --- |
| One writer for the hardware file | A save no longer overwrites a newer file. A stale page is refused and keeps its text. 20 versions with Undo; a file replaced by a default is detected | replaces `saveHardwareConfigFile` | on; changes the Config page save | Pi: store test, live `mv` restore; page desk only | H1 |
| Hardware file checker | Errors and warnings with line numbers at start and on the Config page (duplicates, claimed pins, DPI pins, unknown actions); error counts on the touch chip | new | on; logs at start | desk; Pi build | H2 |
| Controls page | Config > Hardware: one row per button, knob, PCF pin, encoder and switch with actions, free and used pins, live input state | new, beside the readers | on | Pi: real chip read; page against a mock | H3 |
| Saves apply without a restart | Only the changed drivers restart, after the take ends | new; extends `start()`/`stop()` | on | desk; Pi build | H4 |
| Listen, I2C scan, output test | Shows the last control that fired; scans an I2C bus; blinks the tally LED or pulses the trigger once | new | on, WebUI only | desk (mock); Pi build | H5 |
| Remote-only buttons and Try | Buttons with no GPIO pin, run from a Remote controls card; Try runs a control's saved action | new | on, WebUI only | Pi, in the drop-frame tests | H6 |
| One action vocabulary | The same action names on every input; a typo logs "Did you mean"; an action dropdown per sensor | replaces three normalisers | on | host test 20/20; Pi build | H7 |
| `clear_hdr` button action | A button or knob push toggles Clear HDR on the IMX585 | extends in place | off until mapped | desk | H8 |
| Click and Hold gestures | Up to five actions per push: Press, Single, Double, Triple, Hold | extends in place | off until a gesture key is set | desk; Pi build | H9 |
| 1-0-1 (normally closed) buttons | A button that reads pressed at start is treated as wired the other way | extends in place | **on, changes behaviour** | desk | H10 |
| Edge events instead of GPIO polling | The input thread sleeps until an edge or a gesture timer; `poll_ms` stays for chips without edges | replaces the poll loop | **on** | desk; Pi build | H11 |
| Two- and three-way GPIO switches | Switch positions run actions; the start position is applied once | new section | off | desk; Pi build | H12 |
| Default hardware template, no UI-written file | A missing file starts from Core's template; the touch UI no longer writes one | extends the template, removes UI code | port: HDMI 1080p monitor. `work/improve`: 720x720 square again (`7dc6f7a`, UI `6a59d83`); still no first-run file | desk | H13 |
| IMU config through the store | Level reference, calibration and orientation saves are atomic and in the history | replaces two line editors | on | Pi builds; no gyro on the rig | H14 |
| Boot Config card (`config.txt`) | Pick sensor per connector, link frequency, overclock, audio buses and display in the WebUI; review the changed lines; save and reboot; free-text edit | new | card on; saving needs the root helper | desk and mock server; never on a Pi | H15 |
| Fan mode through Core's writer | Fan changes no longer race a Boot Config save; both UIs go through Core | extends `applyFanMode`, removes UI code | on | Pi build only | H16 |
| Real-time scheduling switches | Run Core under SCHED_FIFO on cores 1-3, or only libcamera's completion thread; RT capture priority knob | extends the start script and drop-in | off | no result recorded; the capture priority measured with no effect | H17 |

## Screens: touch UI, HDMI and WebUI

| Feature | Operator gets | Relation | On by default? | Tested where | Src |
| --- | --- | --- | --- | --- | --- |
| Value lists and capped pickers | Own ISO, shutter angle, FPS and WB lists, free stepping, flicker-free angles for 50/60 Hz. Pickers and inputs grey values above `iso_max` / `fps_max` | new (UI.conf), replaces the hard-coded lists | built-in lists; ceiling greying on | Patrik 2026-10-28 (4 of 5 commits); `682a186` built only | H18, T1 |
| Recording indicators | Switches for a red frame, red timecode, audio recorded outline and the buffer bar, on touch, HDMI and WebUI | extends in place | frame off, bar off, red timecode on. Audio outline: port on, `work/improve` off (`ff4c7c5`, UI `2d9cf94`); HDMI timecode white (UI `ac1fc28`) | frame and red timecode Patrik 2026-10-28; outline not recorded | H19, T3, W5 |
| UI timecode and file timecode apart | The files' timecode can differ from the screens'; labels Time of Day / Clip | extends `set_timecode_mode`, renames labels | both follow one setting until changed | built, not tested | H20, W8 |
| Raw readout | Resolution line with bit depth and Clear HDR, Log in the codec label, exact shutter angle, time left from stored bits, rounded down | extends in place | on | Patrik 2026-10-27/28 (most); Log suffix desk only | T5, W9 |
| Presets carry more settings | Presets and format profiles carry Log, Clear HDR, phase lock, timecode mode, speed ramp, clip-name template and other new keys | extends in place | on | Log and preset keys desk only | W9, `8e8ea2e` |
| Settings search | A search box over the WebUI Settings; shows only matching cards or rows | new | on | desk (`node --check`) | W3 |
| Performance card | One WebUI card for preview TDN, drive trim, phase lock, frames per folder and clip merge (features above) | new card | trim on, merge on, phase lock off, split off | desk; not run | W7 |
| Touch preview cap while recording | `APERTAR_UI_PREVIEW_RECORDING_FPS=N` caps preview frames in a take, to test whether preview work costs frames | beside | off (variable unset) | Pi, hardware log only | T6 |

## Build and integration

| Feature | Operator gets | Relation | On by default? | Tested where | Src |
| --- | --- | --- | --- | --- | --- |
| Integrator files and host tests | Install files for the root helpers (sudoers, tmpfiles); 20 host tests in `tools/` outside CMake | beside the upstream standby helpers | none installed | helper and host tests on the desk | H21 |
| Build without libcamera | Core builds and runs `--simulate` without libcamera again | extends the existing guards (`5f5cea2`) | build option | desk builds | C note |

## Count

| Area | Entries in the area file | Rows here |
| --- | --- | --- |
| Camera, sensors and modes | 11 table rows + 2 from its notes (phase lock, conform FPS) | 13 (T2 merged into "Values the camera decides") |
| Recording and media | 21 | 20 (R16 + W1, R17 + R19 + W2 merged) |
| Controls and system | 21 | 17; H18, H19, H20 merged into Screens rows; H21 under Build |
| WebUI | 9 | 2 own rows (Settings search, Performance card); W1, W2, W4 to W6, W8, W9 merged |
| Touch UI | 6 | 1 own row (preview cap); T1 to T5 merged |
| In no area table | 2 (presets carry more settings, build without libcamera) | 2 |
| **Total** | **72 entries** | **60 features** |

Ten visible default changes for a stock camera on `cinemate-port`: IMX585 size list and renamed crops, higher FPS ceilings and
IMX585 lossless at 60 fps, preview TDN off, storage pre-roll on, HDMI 1080p template, audio outline on, 1-0-1 button
inversion, edge events replacing the poll loop, drive trim and clip merge on. `work/improve` reverted preview TDN,
pre-roll, the template display and the audio outline.
