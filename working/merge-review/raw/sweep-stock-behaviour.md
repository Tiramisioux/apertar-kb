# Sweep X3: what changes for a stock Apertar when the port is merged

Whole-port sweep for one kind of problem: behaviour that differs from 1.6.0 on a stock camera with no
configuration change and no new feature switched on. Read-only. Written 2026-11-17.

| Ref | Meaning |
| --- | --- |
| `@port` | Core `cinemate-port` `01f170c`, UI `cinemate-port` `7ea9afc` |
| `@up` | `upstream-1.6.0` (Core `35dbe67`, UI `43888e5`), read in `/home/user/wt/*-upstream` |
| `@main` | fork `origin/main` (Core `f60e301`) |
| `@stock585` | imx585 driver `origin/apertar` `e5b74d3` ("as shipped on the Apertar-Beta 1.6.0 image") |
| `App`, `CC`, `WCP` | `src/ApertarCoreApp.cpp`, `src/camera/CameraController.cpp`, `src/web/WebControlPage.cpp` |

A line number without a ref is `@port`. Labels: **confirmed** (read in code, or run here), **probable**, **unconfirmed**.

## 1. The reference device

Apertar D1 as the original developer runs it: Pi 5, stock image, the square DPI touch screen, IMX585 (stock
`@stock585` driver) or IMX477, stock tuning files, `apertar-hardware.conf` as the 1.6.0 touch UI wrote it (or
none, or one from an older version), records cDNG to a mounted card at `/media/RAW`. Updated to the port's Core
and UI. No env var set, no new helper installed, no new switch touched.

Clear HDR, the Mode Ladder, speed ramp, phase lock, Log, RAM buffer, split folders, clip-name templates and IMX283
are not in 1.6.0 and are off by default (`Types.hpp:138-143`, `ModeLadder.hpp:47`, `BufferBudget.hpp:308`,
`:317`). Their own rules are not stock behaviour; section 5 lists the ones that leak into SDR anyway.

## 2. Result in short

| Verdict | Count | Changes |
| --- | --- | --- |
| (a) keep the 1.6.0 default, new behaviour opt-in | 9 | display fallback; no first-run hardware file; FPS ceiling from the probe and no IMX585 lossless 30 cap; storage pre-roll; preview temporal denoise off for H.264/ProRes; page-cache default drops Lossy DNG's per-file drop; touch-UI timecode tap; red timecode on HDMI; audio-meter outline |
| (c) gate on the hardware present | 4 | IMX585 tables of the cinemate-port driver on the stock driver; lossless ISO 1600 on every sensor; auto ISO in lossless on every sensor; media trim switch with no helper |
| (b) keep: a plain fix, or new and inert on stock | 27 | section 3 rows marked (b) |

The two that break a stock camera outright: the touch UI hides itself when `[display]` has no
`hdmi_external_only` key (X-stock-behaviour-1), and a camera saved at the IMX585 1.85:1 crop fails to configure
on the stock driver (X-stock-behaviour-4).

## 3. The table

Columns: what changes; 1.6.0; port; on by default; needs the new drivers or files; what the D1 does
differently; verdict.

### 3.1 Display, hardware file, Controls

| # | Change | 1.6.0 | Port | Default | Needs | D1 does differently | Verdict |
| --- | --- | --- | --- | --- | --- | --- | --- |
| D1 | Display fallback when `[display]` keys or the file are missing | 720x720 `square`, `hdmi_external_only=false` (UI `DisplayConfigBridge.cpp:14-15@up`, `:579@up`, `:584@up`, `:649@up`, `.hpp:52-59@up`) | 1920x1080 `landscape_large`, `hdmi_external_only=true` (UI `DisplayConfigBridge.cpp:11-12`, `:289`, `:294`, `:357`; `.hpp:52-59`). Commit UI `7c41a27` | on | no | With `hdmi_external_only=true` the main window is hidden (UI `main.cpp:432-433`; `:428-429@up`). A file without that key (any file written before 1.6.0: the key first appears in the squashed 1.6.0 commit `8847105`, **probable**) or no file: no touch UI on the square screen | (a) X-stock-behaviour-1 |
| D2 | Core's hardware template (shown by the Config page for a missing file, saved on first Save) | `[display]` 720, 720, `square` (`App:4312-4322@up`) | 1920, 1080, `landscape_large`, `hdmi_external_only=true` (`App:5089-5098`; `7af9f13`) | on | no | A first Save from the WebUI Config page on a camera without a file writes the HDMI layout | (a) X-stock-behaviour-1 |
| D3 | First-run hardware file | the UI writes its template when `/home/pi/apertar-hardware.conf` is missing (`ensureDefaultHardwareConfigFile`, UI `DisplayConfigBridge.cpp:41@up`, `:587@up`; same in `Ina219Bridge.cpp@up`) | nothing writes it (UI `c9d841f`, 578 lines removed) | on | no | No file appears; the readers use their defaults (INA219 enabled, same as the template, **confirmed** UI `Ina219Bridge.cpp:217`); the display defaults are D1's | (a) X-stock-behaviour-2 |
| D4 | Hardware file validated at start, adopted copy pinned, last-written copy kept | nothing | one log line, `controls_errors`/`_warnings` in state, `hardware-history/adopted-<rev>.conf` (`4d80a35`, `014fa22`) | on | no | New files under Core's config dir. The 1.6.0 UI template gives 0 errors and 0-2 warnings (bus 4, bus 10) with the port's validator (**confirmed**, run here: scratch build of `HardwareConfigText.hpp` on the template text from `DisplayConfigBridge.cpp@up`) | (b) |
| D5 | "Controls: N errors" chip on the camera page | none | shown when `controls_errors > 0` (UI `ea44bd7`, `visible: errors > 0`) | on | no | Nothing on a stock file (warnings only go to Settings > Info) | (b) |
| D6 | Hardware sections re-applied without a Core restart; outside edits picked up | restart needed | controls worker restarts the changed driver groups (`dcf09ee`) | on | no | An edit with nano takes effect without a restart | (b) |
| D7 | GPIO buttons and encoders | read every `poll_ms` (12 ms buttons, 3 ms encoders) | wait for edge events; poll only on a chip without them (`0c49601`, `GpioInput.cpp`) | on | no | Same presses; no 12 ms wake-ups. Press still fires at once (`ButtonGesture.hpp:24-29`) | (b) |
| D8 | Web Config page save | `.bak` + rename, no version (`saveHardwareConfigFile`, `App:5317@up`) | goes through the store; an old page without the revision header gets 409 (`5395fa4`) | on | no | A WebUI tab opened before the update must be reloaded once | (b) |
| D9 | Fan mode from the touch UI | UI writes `config.txt` with `sudo -n install` | UI sends `set_fan_mode`; Core tries direct write, then `/usr/local/libexec/apertar-boot-config`, then the same `sudo -n install` (`App:3529-3610`; UI `41ff827`) | on | helper optional | Same result through the old sudo route | (b) |

### 3.2 Sensor, FPS, ISO

| # | Change | 1.6.0 | Port | Default | Needs | D1 does differently | Verdict |
| --- | --- | --- | --- | --- | --- | --- | --- |
| S1 | FPS ceiling per mode | table only: IMX585 4K 30, crops and 1080p 60 (`CC:2669-2678@up`). Fork main: `min(table, probe)` (`CC:2763-2770@main`) | the startup probe alone when it has a value (`FpsCeiling.hpp:14-19`, `CC:3411-3423`); `APERTAR_FPS_LIMIT=table` restores `min` (`CC:3398-3408`). Commit `d44b177`: "4K SDR 60, it was capped at 30 by a table" | on | no | IMX585 4K offered and accepted up to the driver's `FrameDurationLimits` (60 per the commit, **probable** on `@stock585`). IMX477: whatever the driver reports, instead of Apertar's measured table (**unconfirmed** per mode) | (a) X-stock-behaviour-3 |
| S2 | IMX585 lossless cDNG FPS cap | 30 (`CC:2485-2486@up`) | the mode's maximum (`CC:3134-3144`, `FpsCeiling.hpp:42-45`); `APERTAR_LOSSLESS_FPS_LIMIT=n` restores a cap | on | no | 4K lossless offered to 60 with S1 | (a) X-stock-behaviour-3 |
| S3 | Built-in FPS steps (dial, buttons, pickers) | IMX585 `{24,25,30,50,60}` cut at the table ceiling (`App:1150-1168@up`) | IMX585 adds 100, 120; the ceiling itself is offered when not in the list (`App:1398-1416`; `b0e90ad`, `caa0153`) | on | no | More stops on the dial; the cut follows S1 | (b), follows S1 |
| S4 | IMX585 sizes and sensor configuration | whitelists; 1.85:1 crops 3840x2076 and 1920x1038 as the stock driver has them (`imx585.c:816-826`, `:1006-1016@stock585`); colour IMX585 crops may fall back to auto sensor config (`CC:5993-5996@up`) | tables of the cinemate-port driver (`Imx585Modes.hpp:1-3`, `:39-50`); 2076 and 1038 are moved to 2072 and 1036 everywhere (`CC:446-452`, `:703`, `:10648`, `:12663`; `900d282`); colour IMX585 configures explicitly only and rejects a mode the driver adjusted (`CC:8295-8296`, `:8487-8516`; `caa0153`) | on | **cinemate-port imx585 driver** | The stock driver has no 3840x2072 or 1920x1036. A D1 saved at 1.85:1 is moved to a size the driver lacks; explicit config is rejected and there is no auto fallback, so `configureAndStart` fails ("libcamera rejected camera configurations", `CC:8686-8690`) at boot (**probable**: same failure the commit message reports for the opposite pairing). The 1.85:1 crop is no longer offered | (c) X-stock-behaviour-4 |
| S5 | Lossless cDNG ISO cap | 800, every sensor (`CC:2483@up`) | 1600 (`CC:3100`, `:3151`; `2f43ecc`). Measured on the IMX585 only ("12-bit lossless 4K25 had queue headroom") | on | no | IMX477 4K/2K lossless and IMX585 SDR lossless go to ISO 1600 | (c) X-stock-behaviour-9 |
| S6 | Auto ISO in lossless | sanitiser forces manual ISO (`CC:2484@up`); the dial still offered Auto (`App:8789-8797@up`) | kept on the IMX585 (`CC:3152-3156`); UIs and the dial offer Auto wherever Clear HDR is off (`App:10485`, `WCP:8665`, UI `682a186`) | on | no | IMX585: auto ISO in lossless, bounded only by the default tuning's AGC (commit `b5b787e`: "Unverified: a tuning file with a higher AGC gain would let auto ISO pass the lossless cap"). IMX477 lossless: Auto is offered on every screen, Core turns it off again | (c) X-stock-behaviour-10 |
| S7 | Value lists, greyed values above the ceiling, ceiling added | fixed arrays in three places | `UI.conf` lists, built-ins when empty (`App:1551-1570` = the 1.6.0 arrays, **confirmed** against `App:1281-1288@up`) | on | no | Pickers show values above the ceiling greyed and the ceiling added in italics | (b) |
| S8 | WB dial below the lowest value | stops | Auto, as the 1.6.0 ISO and shutter dials do (`60645d4`; `App:8789-8818@up`) | on | no | One more stop on the WB dial | (b) |
| S9 | Raw requests and buffers | 3 requests for raw takes (`kActiveRequestCount`, `CC:1024@up`, `:6461@up`) | requests follow buffers: 4 SDR, +2 on exFAT/FAT/NTFS (`CC:1458-1470`; `db17860`) | on | no | One more frame of capture headroom | (b) |
| S10 | Raw copy off libcamera's thread; pool kept through the take | copy on the completion thread, pool emptied at stop | copy worker; pool warmed at take start (`351a3ee`, `4abbef0`) | on | no | More RAM held during and after a take | (b) |

### 3.3 Recording and media

| # | Change | 1.6.0 | Port | Default | Needs | D1 does differently | Verdict |
| --- | --- | --- | --- | --- | --- | --- | --- |
| R1 | Storage pre-roll | none | 2 s raw take at the mode's highest fps, then deleted, at Core start, card insert and format (`StoragePreroll.hpp:91-99` `value_or(true)`; `App:10956-10959`, `:11148-11160`; template `# preroll=on` `App:5069-5070`). Raw formats only (`CC:12067-12069`) | **on** | no | Writes and deletes 0.7-1.5 GB at every boot and insert (KB `working/dng-chain-answer.md` s.4); record refused for 3-5 s after start; a blue PRE-ROLL pill. With S1 the take runs at 60 fps in 4K | (a) X-stock-behaviour-5 |
| R2 | Preview temporal denoise | on (tuning file as is) | `previewTdn=false` (`Types.hpp:139`): Core loads a copy of the tuning without `rpi.denoise` tdn, for every format (`CC:7311`; `e625c68`) | **on** (TDN off) | no | Preview noisier; H.264 and ProRes **recordings** lose temporal denoise (see `raw/sweep-knobs.md` X-knobs-4) | (a) X-stock-behaviour-6 |
| R3 | Page-cache drop after a DNG write | cDNG: none. Lossy DNG: `POSIX_FADV_DONTNEED` after every file (`LossyDngEncoder.cpp:82@up`) | `APERTAR_DNG_DONTNEED` unset = `sync`: cDNG drops after the once-a-second fsync (`CdngEncoder.cpp:85-106`, `CC:4760-4765`; `adac040`). Lossy DNG drops only in `writer` mode (`LossyDngEncoder.cpp:102-105`) and its files never reach the sync thread (`noteWrittenFile` only in the cDNG branch, `CC:5290-5294`) | on | no | cDNG: new, measured (0 lost in two 3-min takes). **Lossy DNG: the 1.6.0 drop is gone**; written frames stay in the page cache until kswapd reclaims them, the pattern `adac040` itself blames for lost frames | (a) X-stock-behaviour-7 |
| R4 | Once-a-second fsync of each DNG and the clip folder; writeback started per file | none | `APERTAR_MEDIA_SYNC_MS` default 1000 (`CC:4365`); `APERTAR_DNG_WRITEBACK` default on (`CC:4718`); `4ce382e`, `7d9dd60`, `5b68f1f`, `441e42a` | on | no | A pulled card loses about a second, not the clip folder. More fsyncs during a take (measured clean 10 min on the contributor's CFexpress, C0101) | (b) |
| R5 | Writer workers and queue per filesystem | 4 uncompressed workers, queue 12 (`CC:3324-3330@up`) | ext4/exFAT 4/12 as before; vfat/NTFS 2/16 +2 buffers; other 2/12 (`MediaProfile.hpp:129-142`, `CC:4320-4328`) | on | no | Same on exFAT and ext4. Fewer writers on FAT/NTFS/other | (b) |
| R6 | Record gate | records into `--media` whether mounted or not; only the Sound Recorder needs a mount (`App:8351@up`) | refused with no mount, a pulled card, a dead medium or under 1024 MiB free; also stills and time-lapse (`App:11330-11384`) | on | no | Recording into an unmounted `/media/RAW` (the SD card) is refused; a nearly full card refuses a still | (b), with the launch option of `raw/sweep-knobs.md` X-knobs-5 |
| R7 | Stalled writers end the take | frames drop, the take goes on | full queue and no frame written for 5 s fails the take as media removed (`CC:4861`; `a3ac8da`) | on | no | A take on a card that stalls for 5 s ends | (b) |
| R8 | Pulled CFexpress card | seen when I/O fails | slot bit from `[cfexpress_hat]` (`0b1632f`); latched until remount; UI lazy-unmounts and removes PCIe (UI `dc471c1`); UI follows Core's `media_state` (UI `160898c`) | on | hat reader on bus 10 (no hat: unchanged) | Pull no longer hangs the stop | (b) |
| R9 | Media trim | none | `mediaTrimEnabled=true` (`Types.hpp:140`); worker asks `/usr/local/libexec/apertar-media-trim` via sudo (`App:11484-11514`) | on | **root helper + sudoers** not on a stock image | Nothing runs; one log line; the WebUI Performance card shows Trim on | (c) X-stock-behaviour-11 |
| R10 | Clip merge worker | none | `clip_merge` default on (`BufferBudget.hpp:328`); scans the media root for clip folders with the split marker at start, mount and after each take (`App:11756-11758`) | on | no | Inert: `frames_per_folder` defaults to 0, no marker is written. One directory listing of the root per trigger | (b) |
| R11 | Audio | drift from two end-point stamps; capture to file at stop | least-squares drift fit, writer thread, raw capture on the card once a second (`60ce8e9`, `b606c4f`, `ebdcd08`); ring back to 100 ms (`0358fcf`) | on | no | Resample ratio steadier; audio survives a pull | (b) |
| R12 | MLV black/white level | as written | same as the take's cDNG at every bit depth (`5e9dd1a`) | on | no | MLV metadata corrected | (b) |
| R13 | Downloads and deletes during a take | allowed | download 409 during a take; delete waits for pending writes; record refused while a delete runs ("Deleting media. One moment.", `App:12587`; `a37a902`) | on | no | No downloads while recording | (b) |
| R14 | Clip naming | `<fmt>_<yy-mm-dd>_C####`, lowest free number (`CC` removed lines of `014a2bf`) | template "Original" by default, same names | on | no | Nothing | (b) |

### 3.4 Touch UI and WebUI

| # | Change | 1.6.0 | Port | Default | Needs | D1 does differently | Verdict |
| --- | --- | --- | --- | --- | --- | --- | --- |
| U1 | Timecode tap on the camera page and Settings "Mode" | changes both the screens and the files (`CameraPage.qml:1714@up`, `SettingsPage.qml:3778@up`: `applyTimecodeMode(v)`; Core writes both) | changes only the UI timecode (`CameraPage.qml:1842` sends `"ui"`; Settings splits into UI and File timecode; UI `7029db1`, Core `909aaa5`) | on | no | An operator who taps to Rec Run gets Rec Run on screen and Free Run in the DNGs, MLV, ProRes, H.264 and WAV | (a) X-stock-behaviour-8 |
| U2 | Timecode mode names | Free Run / Rec Run | Time of Day / Clip in WebUI and touch UI (`2c259b9`, UI `08cefcf`); stored values unchanged | on | no | Different words on screen | (b), the original developer's call |
| U3 | Red timecode during a take | touch screen and WebUI red; HDMI white | `recordingRedTimecodeEnabled` default true and HDMI follows it (UI `SettingsBridge.cpp:370`; UI `da2a9b5`) | on | no | HDMI monitor timecode turns red during takes | (a) X-stock-behaviour-12 |
| U4 | Audio meter outline while sound is recorded | none | `audioRecordedOutlineEnabled` default true (UI `SettingsBridge.cpp:371`; UI `5697b54`) | on | no | A faint red outline on the audio meter during takes with sound | (a) X-stock-behaviour-13 |
| U5 | Recording frame, buffer bar | none | both default off (`f4fb084`, UI `841d0ed`) | off | no | Nothing | (b) |
| U6 | Values the camera decides | plain | italic (`e58e7e5`, UI `35b31f6`) | on | no | A ceiling added to a list shows in italics | (b) |
| U7 | `recording` event | collected into the reply of the command that caused it | broadcast to every client (`086443c`) | on | no | The touch UI sees a take started from the WebUI or a button at once, not at the next poll | (b) |
| U8 | Socket line limit | 64 KiB, client dropped silently | 1 MiB (`ControlServer.cpp:16`; `5395fa4`) | on | no | Nothing for stock clients | (b) |
| U9 | WebUI media list | `#mediaBrowserOverlay`: filters, sort, select, download, delete (`WCP:3979@up`) | Clip Browser `#playbackOverlay` (`WCP:6345`): same filters, sort, selection actions; thumbnails decoded by Core (`/api/media/frame`), Clip Viewer; list from a cache (`f91fafa`, `1af26c8`, `bc12c0a`) | on | no | Thumbnails; Core decodes DNGs while the page is open (held during a take); the overlay class name changes | (b) |
| U10 | WebUI settings panes | 9 panels | 11: `controls` and `modes` added; no upstream card removed (card-title diff: 9 added, 0 removed, **confirmed**); Value Lists sits in Controls, Mode Ladder and Activated sensor modes in Modes; Controls and Hardware cards above the Config editor; Performance and Boot Config cards in System; a search box | on | no | More panels and cards; upstream cards where they were | (b) |
| U11 | Time left, Media Removed label | rounds; mount table | rounds down; Core's media state (`bda2066`, `3c4f07d`) | on | no | Matches the touch UI | (b) |

## 4. Silent dependencies a stock image does not have

| Feature | Depends on | On a stock image | Evidence |
| --- | --- | --- | --- |
| IMX585 1.85:1 crops at 3840x2072 / 1920x1036; the 62/62/29/34-mode tables; Clear HDR crops; 10-bit tables | cinemate-port imx585 driver (`cd548ef`) | 1.85:1 fails or vanishes (S4); other table rows the stock driver lacks are not probed and not offered (**probable**: the probe configures each row, `CC:7152-7206`) | `Imx585Modes.hpp:1-3`, `900d282`, `caa0153` |
| IMX283 family | cinemate-port imx283 driver (`68b7dc9`) | not a stock sensor | `c48e693` |
| Media trim | `/usr/local/libexec/apertar-media-trim`, `config/apertar-media-trim.sudoers` | skipped, one log line, switch shows on (R9) | `App:11484-11514` |
| Boot Config card, fan mode | `/usr/local/libexec/apertar-boot-config`, `config/apertar-boot-config.sudoers` | falls back to `sudo -n install`, the 1.6.0 route | `App:3529-3610` |
| Kernel block-queue and dirty-page tuning | `/usr/local/libexec/apertar-media-tune`, `config/apertar-media.sudoers` | opt-in (`APERTAR_MEDIA_TUNE=1` or `kernel_tune`), skipped | `App:11396-11421` |
| Media tuning override file | `config/apertar-media.tmpfiles.conf` (`/run/apertar-media`) | absent, built-in defaults | `raw/sweep-knobs.md` X-knobs-6 |
| `APERTAR_RT=1`, `APERTAR_RT_CAPTURE_PRIORITY` | `config/apertar-core-capture-priority.conf` drop-in (`LimitRTPRIO=80`) | off by default; refused and logged when set | `c57c284`, `6ef0ddc` |
| Stretched WAV after a speed-ramp take | `rubberband-cli` | speed ramp is off; when on, the stretch fails with "is rubberband-cli installed?" | `CC:9938`, `CC:9978-9984` |
| Clear HDR default tuning | a `<stem>_clearHDR.json` beside the default tuning file | Clear HDR off; not in the repo | `DefaultTuningSelection.hpp:191-193` |
| Preview without temporal denoise | write access to `~/.cache/apertar-core/tuning/` | created by Core; on by default (R2) | `e625c68` |
| Clip Browser frames | `third_party/liblj92` in Core (new tree; upstream Core has none) | built in | `1af26c8` |
| libcamera | properties `ScalerCropMaximum`, `PixelArraySize`, `PixelArrayActiveAreas`, controls `FrameDurationLimits`, `SensorTimestamp`, `FrameDuration` are new uses; whether the stock image's libcamera build has all of them | **unconfirmed**: build the port against the stock image's libcamera headers | `git diff upstream-1.6.0 cinemate-port -- src/camera/CameraController.cpp` |
| Env vars of the libcamera fork | none new: Core sets only `LIBCAMERA_RPI_TUNING_FILE`, as 1.6.0 | - | grep `LIBCAMERA_` both trees |

## 5. New-feature rules that leak into SDR

| Rule | Where | Effect |
| --- | --- | --- |
| Clear HDR off forces lossless | `applyClearHdrCompression`, `CC:3028-3032` (`f2ebe6e`) | A user who records SDR uncompressed, tries Clear HDR and turns it off is left on lossless. Not reachable without Clear HDR, which 1.6.0 does not have. Note for the Clear HDR review: restore the compression the take had before Clear HDR |
| Clear HDR holds ISO and WB | `CC:11631-11647` (`8175273`) | Only in Clear HDR |
| Speed ramp "after=stay" | `d44b177` | Only with speed ramp on |

## 6. Findings

### X-stock-behaviour-1 (blocker, a): the display fallback is the contributor's HDMI rig

Same facts as `raw/sweep-knobs.md` X-knobs-2. Added here: a 1.6.0 template carries `hdmi_external_only=false`
(UI `DisplayConfigBridge.cpp:323@up`), but the key first appears in the squashed 1.6.0 commit, so a file written
by an older Apertar has no such key and gets `true` from the port (`DisplayConfigBridge.cpp:357`): the window is
hidden (UI `main.cpp:432-433`). Fix: the four 1.6.0 values back in `DisplayConfigBridge.cpp:11-12`, `:289`,
`:294`, `:357`, `.hpp:52-59` and in Core's template `App:5089-5098`. The HDMI rig keeps its values in its own file.

### X-stock-behaviour-2 (minor, a): no first-run hardware file

UI `c9d841f` removed the writer in `DisplayConfigBridge.cpp` and `Ina219Bridge.cpp`. Reason given: a file moved
away came back as the old template. The port's store now catches that case (`014fa22`: missing, empty, or "starts
like the touch UI's default template"). Fix, upstream style: one first-run writer, in Core (the file's one writer),
`defaultHardwareConfigTemplate()` written through `HardwareConfigStore` when no candidate path has a file and the
store has no last-written copy. The replaced-file check stays for every later start.

### X-stock-behaviour-3 (major, a): FPS ceilings from the probe alone, and no IMX585 lossless 30 cap

`resolveSensorMaxFps(probed, table, tableOnly)` returns the probe unless `APERTAR_FPS_LIMIT=table`
(`FpsCeiling.hpp:14-19`); the IMX585 lossless cap became the mode's maximum (`CC:3134-3144`). 1.6.0: 4K 30 and
lossless 30 (`CC:2671@up`, `CC:2485-2486@up`). Fork main already used `min(table, probe)`. A stock D1 offers 4K
at the driver's figure (60 per `d44b177`), the dials and pickers follow (`App:1398-1416`), and the storage
pre-roll runs at it (`CC:3488-3493`). Fix: default `min(table, probe)` as in `@main`; the probe alone behind
`APERTAR_FPS_LIMIT=probe` (or a `[camera]` key, see X-knobs); IMX585 lossless back to 30 unless
`APERTAR_LOSSLESS_FPS_LIMIT` raises it.

### X-stock-behaviour-4 (major, c): the cinemate-port driver's IMX585 modes on the stock driver

The port moves 3840x2076 and 1920x1038 to 3840x2072 and 1920x1036 in settings, presets, ladder rungs and
`set_resolution` (`CC:446-452`, `:703`, `:10648`, `:12663`). The stock driver has the old sizes and not the new
ones (`imx585.c:816-826`, `:1006-1016@stock585`). Colour IMX585 crops lost their auto-config fallback
(`CC:8295-8296` against `CC:5993-5996@up`) and a driver-adjusted mode is rejected (`CC:8487-8516`). A D1 saved at
1.85:1 fails to configure; the crop is not offered. Fix: let the probe decide. Migrate a size only when
`probedSensorModes` has the new transport size and lacks the old one; keep 2076/1038 in `isImx585LegacyCropResolution`
for a driver that advertises them; restore the auto fallback for a table size the probe did not confirm. Name the
driver requirement in the README. **probable** until run on a stock-driver Pi: `journalctl -u apertar-core | grep
'rejected camera configurations'` with `resolution=3840x2076` in `camera_settings.conf`.

### X-stock-behaviour-5 (major, a): storage pre-roll runs by itself

Same facts as X-knobs-3 (`StoragePreroll.hpp:98`, template `App:5070`). Fix: `value_or(false)`, template
`# preroll=off`. The `storage_preroll` command stays.

### X-stock-behaviour-6 (major, a): preview temporal denoise off also for H.264 and ProRes recordings

Same facts as X-knobs-4 (`Types.hpp:139`, `CC:7311`, `CC:7412`). Fix: strip only when the record format is raw
(`!settings.previewTdn && recordsRawFrames(settings.recordingFormat)`), or `previewTdn = true`.

### X-stock-behaviour-7 (major, a): the new page-cache default removes Lossy DNG's per-file drop

1.6.0 drops every Lossy DNG's pages after the write (`LossyDngEncoder.cpp:82@up`). The port drops them only in
`writer` mode (`LossyDngEncoder.cpp:102-105`); the default is `sync` (`CdngEncoder.cpp:85-106`), and lossy files
never reach the sync thread (`CC:5280-5294`: `noteWrittenFile` is in the cDNG branch only). So a stock Lossy DNG
take keeps every frame in the page cache. Fix, one line in the 1.6.0 shape:

```cpp
    if (dngPageCacheDrop() != DngPageCacheDrop::Off)   // lossy takes have no sync thread: drop here
        ::posix_fadvise(fd, 0, 0, POSIX_FADV_DONTNEED);
```

### X-stock-behaviour-8 (major, a): the touch-UI timecode tap no longer changes the files

1.6.0: the tap and Settings "Mode" set one mode for screens and files (`CameraPage.qml:1714@up`,
`SettingsPage.qml:3778@up`). Port: `applyTimecodeMode(nextMode, "ui")` (`CameraPage.qml:1842`). Core's default
target stays `both` (`909aaa5`). Fix: the tap and the first Settings row send `"both"` while the two modes are
equal; `"ui"` only once the operator has set them apart in the File timecode row.

### X-stock-behaviour-9 (minor, c): lossless ISO 1600 on every sensor

`kLosslessMaxIso = 1600` (`CC:3100`) applies to IMX477 4K/2K lossless too; the evidence (`2f43ecc`) is IMX585
only. Fix: 1600 for `SensorFamily::Imx585`, 800 for the rest, in `enforceLosslessCaptureLimits` and
`maximumIsoForSettings` (`CC:3146-3170`).

### X-stock-behaviour-10 (minor, c): Auto ISO in lossless offered on every sensor

Core keeps auto ISO in lossless only on the IMX585 (`CC:3152-3156`); the dial (`App:10485`), the WebUI
(`WCP:8665`) and the touch UI (UI `682a186`) offer Auto wherever Clear HDR is off. IMX477 lossless: Auto is
offered and undone. 1.6.0 already offered it on the dial (`App:8789-8797@up`). IMX585: bounded only by the
default tuning's AGC (commit `b5b787e`: "Unverified"). Fix: Core publishes `iso_auto_allowed` in the state from
the sanitiser's own rule; the three UIs read it. For a user-picked tuning on the IMX585, keep 1.6.0's manual ISO.

### X-stock-behaviour-11 (minor, c): media trim shows on with no helper

`mediaTrimEnabled = true` (`Types.hpp:140`); without `/usr/local/libexec/apertar-media-trim` the worker logs once
and skips (`App:11505-11514`), while the state and the Performance card say on. Fix: `media_trim_available`
(helper exists and is executable) in the state; the WebUI greys the switch with the install line.

### X-stock-behaviour-12 (nit, a): HDMI timecode turns red during takes

UI `da2a9b5`: "HDMI now follows it too", default true (UI `SettingsBridge.cpp:370`). Fix: the HDMI monitor
follows the switch only when `recordingRedTimecodeEnabled` is set in `UI.conf`, or a separate HDMI key, default off.

### X-stock-behaviour-13 (nit, a): audio meter outline on by default

UI `5697b54`, `SettingsBridge.cpp:371`. Fix: default false, like the recording frame and the buffer bar.

## 7. Unconfirmed

| Claim | Command that settles it |
| --- | --- |
| The stock imx585 driver reports 60 fps for 4K 12-bit to the probe | On a stock-driver Pi: `journalctl -u apertar-core \| grep 'sensor probe'` and `get_state` `fps_max` at 3840x2160 |
| A 1.85:1 saved setting fails at boot on the stock driver (S4) | see X-stock-behaviour-4 |
| The probe's IMX477 figures against Apertar's table | `list_sensor_modes` on a stock IMX477 against `imx477MaximumSupportedFpsForResolution` (`CC@up:2493`) |
| The stock image's libcamera exposes every property the port reads | build `cinemate-port` against the stock image's `/usr/include/libcamera` |
| Files from Apertar before 1.6.0 lack `hdmi_external_only` | an older release's `DisplayConfigBridge.cpp`; the upstream history is squashed |

## Skeptic

Every port line re-read at `cinemate-port` (Core `01f170c`, UI `7ea9afc`) against `upstream-1.6.0`.

| Id | Verdict | Note |
| --- | --- | --- |
| 1 | keep, blocker | Confirmed: `DisplayConfigBridge.cpp:11-12` 1920/1080, `:289` landscape_large, `:294`/`:357` true, `.hpp:52-59` same; `main.cpp:432-433` hides the window. Upstream `DisplayConfigBridge.cpp:14-15,:579,:584,:649`, Core template `App:4320-4329@up` 720/square/false. A D1 that already ran 1.6.0 has a file with `false`; the case is a fresh install (no file, see 2) or a pre-1.6.0 file. |
| 2 | keep, minor, corrected | Confirmed no writer. Correction: the user is not left with nothing to edit; the WebUI hardware editor serves `defaultHardwareConfigTemplate()` when the file is missing (`App:6200-6201`), and its first save writes the HDMI layout of 1. |
| 3 | keep, major, deliberate | Confirmed: `FpsCeiling.hpp:14-19` probe unless tableOnly; `losslessImx585Fps` = mode max (`:42-45`, `CC:3134-3144`). Upstream table 4K 30 (`CC:2671@up`), lossless 30 (`CC:2485-2486@up`); fork main `min` (`core-main CC:2692`). The port comment calls 30 "a policy, not a limit" (encoder ~69 fps measured): deliberate, still a stock change. |
| 4 | keep, major | Confirmed: migration `CC:445-452`, applied `CC:703`; fallback now monochrome/IMX294/IMX577 only (`CC:8295-8296`) against `CC:5993-5996@up`; stock driver `e5b74d3` has only 2076/1038 (`imx585.c:586,:667,:817-830`). Boot failure stays probable until run on a stock-driver Pi. |
| 5 | keep, major | Confirmed: `StoragePreroll.hpp:98` `value_or(true)`; record/photo/format refused while active (`App:12588-12591`). |
| 6 | keep, major | Confirmed: `loadablePath` strips for every format (`CC:7311`), ProRes ISP tuning is built from `activePath` (`CC:7412`). Also strips a tuning file the user picked, though the comment at `CC:7302` says a picked file "is used as given". |
| 7 | keep, major | Confirmed: `LossyDngEncoder.cpp:104` Writer only; upstream `:82` unconditional; default Sync (`CdngEncoder.cpp:85-106`); `noteWrittenFile` only in the cDNG branch (`CC:5293`). |
| 8 | keep, major, deliberate | Confirmed: `CameraPage.qml:1842` sends "ui", `SettingsPage.qml:4011` "ui", `:4026` "files"; Core `App:13286-13297` skips `camera_.setTimecodeMode` for "ui". Upstream tap `CameraPage.qml:1714@up` sends no target. |
| 9 | keep, minor | Confirmed `CC:3100` 1600 for every limited sensor; upstream 800 (`CC:2483@up`). |
| 10 | keep, minor, corrected | Confirmed `CC:3152-3156`, `App:10485` and `WCP:8665` offer Auto unless Clear HDR. Correction: the IMX477 offer-and-undo on the dial already existed in 1.6.0; the new stock behaviour is auto ISO kept in IMX585 lossless (AGC cap unverified for a picked tuning) and Auto offered in the WebUI and touch UI. |
| 11 | keep, downgraded to nit | Confirmed (`Types.hpp:140`, `App:11505-11514`). Nothing is done on a stock image, only the switch misleads; and the skip leaves `media_trim_last_result` empty, so nothing in the state says why. |
| 12 | keep, nit | Confirmed `SettingsBridge.cpp:370` true; `ExternalMonitorWindow.qml:1208` follows it. Upstream HDMI has no red timecode. |
| 13 | keep, nit | Confirmed `SettingsBridge.cpp:371` true; neighbours `:368-369` default false. |

## Final findings

### X-stock-behaviour-1 [stock-behaviour-change, blocker, effort S, deliberate unknown] Display fallback is the HDMI rig: touch UI hidden on a stock camera with no hardware file
where: Apertar-UI/src/DisplayConfigBridge.cpp:11-12 ; :289 ; :294 ; :357 ; Apertar-UI/src/DisplayConfigBridge.hpp:52-59 ; Apertar-UI/src/main.cpp:432-433 ; Apertar-Core/src/ApertarCoreApp.cpp:5089-5098
detail: Port fallback 1920x1080 landscape_large, hdmi_external_only=true (UI 7c41a27); Core's template the same (7af9f13). 1.6.0: 720x720 square false (DisplayConfigBridge.cpp:14-15,:579,:584,:649@upstream-1.6.0; App:4320-4329@upstream-1.6.0). With true, main.cpp:432-433 hides the window. A fresh install has no file (finding 2), so a stock D1 boots with no touch UI (confirmed in code). A pre-1.6.0 file without the key does the same (probable). The first WebUI Config save on a camera without a file writes the HDMI layout. Overlaps X-knobs-2.
fix: Put back 720, 720, "square" and false in DisplayConfigBridge.cpp:11-12, :289, :294, :357, in .hpp:52-59 and in defaultHardwareConfigTemplate() App:5089-5098. The HDMI rig keeps its [display] values in its own apertar-hardware.conf.

### X-stock-behaviour-2 [stock-behaviour-change, minor, effort M, deliberate yes] No first-run hardware file is written any more
where: Apertar-UI/src/DisplayConfigBridge.cpp (ensureDefaultHardwareConfigFile removed, c9d841f) ; Apertar-UI/src/Ina219Bridge.cpp (writer removed) ; Apertar-Core/src/hardware/HardwareConfigStore.cpp ; Apertar-Core/src/ApertarCoreApp.cpp:6200-6201
detail: 1.6.0 UI writes its template when /home/pi/apertar-hardware.conf is missing (DisplayConfigBridge.cpp:41,:587@upstream-1.6.0). Port c9d841f removed both writers because a moved-away file came back as the template; the store now detects that case (014fa22). On a fresh camera no file appears; the WebUI editor shows Core's template (App:6201) and its first save writes it, with finding 1's HDMI values. Until then the UI runs on its compiled fallback.
fix: One first-run writer in Core, the file's single writer: when no candidate path has a file and the store has no last-written copy, write defaultHardwareConfigTemplate() through HardwareConfigStore. Keep the replaced-file check for every later start.

### X-stock-behaviour-3 [stock-behaviour-change, major, effort S, deliberate yes] FPS ceilings come from the probe alone and the IMX585 lossless 30 fps cap is gone
where: Apertar-Core/src/camera/FpsCeiling.hpp:14-19 ; :42-45 ; Apertar-Core/src/camera/CameraController.cpp:3134-3144 ; :3398-3423 ; Apertar-Core/src/ApertarCoreApp.cpp:1398-1416
detail: 1.6.0: IMX585 4K 30 by the table (CC:2671@upstream-1.6.0), lossless 30 (CC:2485-2486@upstream-1.6.0). Fork main: min(table, probe). Port d44b177: probe alone; APERTAR_FPS_LIMIT=table and APERTAR_LOSSLESS_FPS_LIMIT restore the caps. The port comment (CC:3132-3133) calls 30 a policy, the encoder measured ~69 fps. A stock D1 offers and accepts 4K at the driver's figure (about 60, probable); dials, pickers and the storage pre-roll follow. IMX477 ceilings become whatever its driver reports instead of Apertar's measured table.
fix: Default resolveSensorMaxFps to min(table, probe) as on fork main; the probe-only ceiling behind an opt-in (APERTAR_FPS_LIMIT=probe or a [camera] key). IMX585 lossless cap back to 30 by default; APERTAR_LOSSLESS_FPS_LIMIT raises it.

### X-stock-behaviour-4 [stock-behaviour-change, major, effort M, deliberate yes] IMX585 1.85:1 crop sizes of the cinemate-port driver forced on the stock driver
where: Apertar-Core/src/camera/CameraController.cpp:440-452 ; :703 ; :10648 ; :12663 ; :8295-8296 ; :8487-8516 ; Apertar-Core/src/camera/Imx585Modes.hpp:1-3
detail: The port moves 3840x2076 and 1920x1038 to 3840x2072 and 1920x1036 in settings, presets, ladder rungs and set_resolution (900d282), and drops the auto sensor-config fallback for colour IMX585 crops (caa0153; CC:5993-5996@upstream-1.6.0 had it). The stock driver (imx585 origin/apertar e5b74d3, imx585.c:586,:667,:817-830) has only the old sizes. A D1 saved at 1.85:1 is moved to a size its driver lacks, the explicit configure has no fallback, and configureAndStart fails at boot (probable; settle with resolution=3840x2076 in camera_settings.conf on a stock-driver Pi). The 1.85:1 crop also leaves the offers.
fix: Let the probe decide: migrate a size only when probedSensorModes has the new transport size and lacks the old one; keep 2076/1038 valid for a driver that advertises them; restore the auto-config fallback for a table size the probe did not confirm. Name the driver requirement in the README.

### X-stock-behaviour-5 [stock-behaviour-change, major, effort S, deliberate yes] Storage pre-roll runs by itself at start, insert and format
where: Apertar-Core/src/util/StoragePreroll.hpp:98 ; Apertar-Core/src/ApertarCoreApp.cpp:5069-5070 ; :10956-10959 ; :12588-12591
detail: 1.6.0 has no pre-roll. Port: automaticEnabled() returns conf.automatic.value_or(true). At every Core start, card insert and format a stock D1 records a 2 s take at the mode's highest fps and deletes it (0.7-1.5 GB written per run); record, photo, format, eject and standby are refused while it runs (App:12588-12591). Overlaps X-knobs-3.
fix: value_or(false); template line '# preroll=off'. The storage_preroll command stays.

### X-stock-behaviour-6 [stock-behaviour-change, major, effort S, deliberate unknown] Preview temporal denoise off by default also strips TDN from H.264 and ProRes recordings
where: Apertar-Core/include/apertar/core/Types.hpp:139 ; Apertar-Core/src/camera/CameraController.cpp:7302-7318 ; :7412
detail: 1.6.0 loads the tuning file as it is. Port e625c68: previewTdn=false strips rpi.denoise tdn for every record format (CC:7311), and ProRes's ISP tuning is derived from that stripped file (CC:7412). For H.264 and ProRes the ISP output is the recording, so a stock D1 records them without temporal denoise. It also strips a tuning file the user picked, against the comment at CC:7302. Overlaps X-knobs-4.
fix: Strip only when the format records raw frames: if (!settings.previewTdn && recordsRawFrames(settings.recordingFormat)). Or default previewTdn = true.

### X-stock-behaviour-7 [stock-behaviour-change, major, effort S, deliberate no] Default APERTAR_DNG_DONTNEED=sync removes 1.6.0's per-file page-cache drop from Lossy DNG
where: Apertar-Core/src/lossydng/LossyDngEncoder.cpp:102-105 ; Apertar-Core/src/cdng/CdngEncoder.cpp:85-106 ; Apertar-Core/src/camera/CameraController.cpp:5280-5294
detail: 1.6.0 calls posix_fadvise DONTNEED after every Lossy DNG file (LossyDngEncoder.cpp:82@upstream-1.6.0). The port drops only in writer mode; the default is sync (adac040); lossy files never reach the sync thread (noteWrittenFile only in the cDNG branch, CC:5293). A stock Lossy DNG take keeps every frame in the page cache, the kswapd pattern adac040 blames for lost frames. Confirmed in code.
fix: In LossyDngEncoder.cpp: if (dngPageCacheDrop() != DngPageCacheDrop::Off) ::posix_fadvise(fd, 0, 0, POSIX_FADV_DONTNEED); comment 'lossy takes have no sync thread: drop here'.

### X-stock-behaviour-8 [stock-behaviour-change, major, effort S, deliberate yes] Touch-UI timecode tap and Settings Mode no longer change the files' timecode
where: Apertar-UI/qml/CameraPage.qml:1842 ; Apertar-UI/qml/SettingsPage.qml:4011 ; :4026 ; Apertar-Core/src/ApertarCoreApp.cpp:13286-13297
detail: 1.6.0: the tap (CameraPage.qml:1714@upstream-1.6.0) and Settings Mode (SettingsPage.qml:3778@upstream-1.6.0) send no target and set screens and files. Port UI 7029db1: both send target "ui", and Core skips camera_.setTimecodeMode for "ui" (App:13290). An operator who taps to Rec Run sees Rec Run while DNG, MLV, ProRes, H.264 and WAV keep Free Run. Core's default target stays both (909aaa5).
fix: Send "both" from the tap and the first Settings row while UI and file modes are equal; "ui" only once the operator has set them apart in the File timecode row.

### X-stock-behaviour-9 [stock-behaviour-change, minor, effort S, deliberate yes] Lossless cDNG ISO cap raised to 1600 on every sensor
where: Apertar-Core/src/camera/CameraController.cpp:3100 ; :3146-3170
detail: 1.6.0 caps lossless ISO at 800 on every sensor (CC:2483@upstream-1.6.0). Port 2f43ecc: 1600, measured on the IMX585 only. IMX477 4K/2K lossless also reaches 1600, where lossless JPEG slows as noise grows.
fix: Per-sensor cap: 1600 for SensorFamily::Imx585, 800 for the rest, in enforceLosslessCaptureLimits and maximumIsoForSettings.

### X-stock-behaviour-10 [stock-behaviour-change, minor, effort M, deliberate yes] Auto ISO kept in IMX585 lossless and offered in every UI; Core undoes it on other sensors
where: Apertar-Core/src/camera/CameraController.cpp:3152-3156 ; Apertar-Core/src/ApertarCoreApp.cpp:10485 ; Apertar-Core/src/web/WebControlPage.cpp:8665 ; Apertar-UI/qml/CameraPage.qml (682a186)
detail: 1.6.0 forces manual ISO in lossless on every sensor (CC:2484@upstream-1.6.0); its dial already offered Auto (App:8789-8797@upstream-1.6.0), so the dial's offer-and-undo on IMX477 is not new. New: Core keeps auto ISO in IMX585 lossless, bounded only by the default tuning's AGC (b5b787e: 'Unverified' for other tunings), and the WebUI and touch UI now offer Auto wherever Clear HDR is off, which Core undoes on IMX477 lossless.
fix: Core publishes iso_auto_allowed from the sanitiser's own rule; the three UIs read it. On the IMX585 with a user-picked tuning, keep 1.6.0's manual ISO in lossless.

### X-stock-behaviour-11 [stock-behaviour-change, nit, effort S, deliberate unknown] Media trim switch shows on when the root helper is not installed
where: Apertar-Core/include/apertar/core/Types.hpp:140 ; Apertar-Core/src/ApertarCoreApp.cpp:11505-11514 ; :9584
detail: mediaTrimEnabled defaults to true. A stock image has neither /usr/local/libexec/apertar-media-trim nor its sudoers rule; the worker logs once and continues without calling finish(), so media_trim_last_result stays empty while state and the WebUI Performance card say on. Nothing is trimmed; only the display misleads. Upstream has no trim.
fix: Call finish("not-installed", 0, 0) in the skip branch, or add media_trim_available (helper exists and is executable) to the state; the WebUI greys the switch and shows the install line when false.

### X-stock-behaviour-12 [stock-behaviour-change, nit, effort S, deliberate yes] HDMI monitor timecode turns red during takes by default
where: Apertar-UI/src/SettingsBridge.cpp:370 ; Apertar-UI/qml/ExternalMonitorWindow.qml:1208
detail: 1.6.0 HDMI timecode stays white during takes. UI da2a9b5: recordingRedTimecodeEnabled defaults to true and 'HDMI now follows it too'.
fix: HDMI follows the switch only when recordingRedTimecodeEnabled is set in UI.conf, or a separate HDMI key that defaults to off.

### X-stock-behaviour-13 [stock-behaviour-change, nit, effort S, deliberate yes] Audio meter red outline on by default
where: Apertar-UI/src/SettingsBridge.cpp:371
detail: New indicator (UI 5697b54), default true; a stock D1 shows a red outline on the audio meter during takes with sound. Neighbouring indicators (recording frame, buffer bar, :368-369) default false.
fix: Default audioRecordedOutlineEnabled to false.
