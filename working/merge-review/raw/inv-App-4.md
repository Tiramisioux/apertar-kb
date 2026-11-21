# Inventory App-4: ApertarCoreApp.cpp, port lines 10813-12560

Source: `/home/user/build/review/diffs/App.part04.diff` (1822 lines, read completely). Ref `@cinemate-port` `01f170c` unless stated.
Upstream `@upstream-1.6.0` `/home/user/wt/core-upstream`. Stage 1: no judgement.

## 1. What the slice is

One added block of about 1750 lines, inserted between the end of `joinMediaSpeedTest()` (upstream 9085-9089) and `handleCommand` (upstream 9091). Plus 6 added hunks inside `handleCommand`'s head (port 12559-12620). All of the block is new text; nothing from upstream is removed in this slice.

| Port lines | Content | Kind |
| --- | --- | --- |
| 10813-10851 | anon namespace: `mediaEventJson`, `bufferEventJson` | new helpers |
| 10853-10991 | `runMediaWatcher` thread | new worker |
| 10993-11052 | `runBufferEvents` thread | new worker |
| 11054-11081 | `stopMediaWatcher` (joins watcher, buffer, safety-stop threads, and stops preroll, merge, trim) | new |
| 11083-11119 | `runBufferSafetyStop` thread | new worker |
| 11121-11314 | storage pre-roll: `storagePrerollGuard`, `requestStoragePreroll`, `stopStoragePreroll`, `runStoragePreroll`, `runStoragePrerollOnce` | new worker |
| 11316-11330 | `mediaSnapshot()` | new |
| 11331-11339 | `mediaGateBypassed()` | new |
| 11341-11357 | `playbackHoldReason()` | new |
| 11359-11385 | `mediaGateError()` | new |
| 11386-11394 | `mediaProfile()` | new |
| 11396-11440 | `applyMediaTuning` (sudo helper call) | new |
| 11441-11480 | `trimMedia`, `trimMediaAfterDelete`, `mediaTrimMayRun` | new |
| 11482-11594 | `runMediaTrim` worker | new worker |
| 11595-11615 | `mediaTrimStateJson`, `stopMediaTrim` | new |
| 11684-11940 | clip merge: `clipMerge`, `clipMergeMayRun`, `runClipMerge`, `mergeSplitClip`, `endClipMergeRename`, `waitForClipMerge`, `clipMergeStateJson`, `stopClipMerge`; anon helpers `clipMergeNowMs`, `fsyncFolder`, `renameNoReplace`, `listClip` | new worker |
| 11941-11966 | `waitForMediaTrim` | new |
| 11968-12016 | `gpioPeripheralJson` | new |
| 12017-12057 | `i2cPeripheralJson` | new |
| 12059-12226 | static `nvmeDriveSummary`, `cfeHatPeripheralJson`, `outputPeripheralJson`, `i2cBusesJson`; anon `hardwareGroupOf`, `unitReadingSection`, `unitWhat`, `sectionContents`, `monotonicMicros` | new |
| 12228-12243 | `wakeControlsWorker`, `recordingGateActive` | new |
| 12244-12271 | `runControlsWorker` thread | new worker |
| 12273-12351 | `applyHardwareText` (driver-group restart) | new |
| 12353-12381 | `controlsApplyJson` | new |
| 12383-12416 | `noteInputSeen`, `testInputReply` | new |
| 12418-12557 | `handleReadOnlyHardwareCommand`: `get_controls`, `controls_history`, `controls_last_input`, `scan_i2c`, `list_actions` | new second dispatcher |
| 12559-12620 | head of `handleCommand` | original code extended |

## 2. Blame (port commits, by lines in this block)

Counts from `git blame -s -L 10813,12560 cinemate-port`. 12 lines are upstream `35dbe67` (closing braces, `handleCommand` signature).

| Commit | Date | Subject | Lines | Fork-log status / test |
| --- | --- | --- | --- | --- |
| `d44b177` | 2026-10-31 | drop-frames: trim drive, Log, RAM write buffer with safety stop, buffer bar, fps max, storage pre-roll (squash of 19) | 537 | fork-only; fork-log row 138. Pi only. No per-feature test line. Host tests `tools/storage_preroll_test.cpp`, `buffer_budget_test.cpp`, `media_trim_test.sh` exist |
| `dcf09ee` | 2026-10-30 | saves apply without a restart, Listen, history, I2C scan, output tests (T39/T40/T42) | 348 | fork-only (row 129); no test recorded |
| `ba0658d` | 2026-11-08 | merge worker flattens split clips while idle | 317 | fork-only, on GitHub `cinemate-port` (row 188); host test `tools/clip_merge_test.cpp`; Pi build ran since 13:00 boot |
| `438a342` | 2026-10-26 | survive a yanked or unmounted drive (T28) | 111 | fork-only, built 22:27 (row 41); no behaviour test recorded |
| `c34f844` | 2026-10-30 | two- and three-way GPIO switches, CFexpress hat in get_controls | 68 | fork-only (row 125) |
| `0a98868` | 2026-10-29 | clicks and hold on GPIO buttons, 1-0-1 buttons, I2C devices detected (T44) | 67 | fork-only (row 122) |
| `26da30e` | 2026-10-26 | media profile and per-filesystem tuning | 55 | fork-only, "built 23:04, not tested" (row 46) |
| `166cc4d` | 2026-10-29 | GPIO buttons as peripheral on Controls card | 46 | fork-only (row 120) |
| `f5a61b8` | 2026-10-29 | `get_controls`/`set_controls`, read-only hardware commands before the command lock (T37 p3) | 44 | fork-only (row 108) |
| `f91fafa` | 2026-10-29 | Core knows its clips: hold rule, yield window (T47) | 42 | fork-only, Pi tested 2026-10-29 (row 99) |
| `1319967` | 2026-11-03 | WebUI Remote controls card, Try buttons (`test_input`) | 25 | fork-only, Pi only (row 148) |
| `a3ac8da` | 2026-10-26 | pulled card stays removed until remount; stuck writers end the take | 19 | fork-only, built 22:51 (row 44) |
| `64bbbaa` | 2026-11-01 | count dropped frames (`recording_dropped_frames`) | 14 | fork-only |
| `2edc6d0` | 2026-11-02 | media tuning file `~/apertar-media-tune.conf` | 7 | fork-only, built, Core not restarted (row 142) |
| `04bac89` | 2026-11-01 | trim after delete outside Core and after pre-roll delete | 7 | fork-only |
| `68516f1` | 2026-11-08 | rescan for split clips after a merge pauses | 4 | fork-only |
| `ebdcd08`, `e0fa852`, `ce0bd90`, `c5db8b2`, `0b1632f`, `a37a902`, `4d80a35`, `1af26c8`, others | 10-26 .. 11-04 | small edits | 1-3 each | fork-only |

## 3. Features (operator-visible), by region

| Feature | Regions | Commits | Operator gets |
| --- | --- | --- | --- |
| Media watcher and yank survival | 10853-10991, 11316-11385 | 438a342, a3ac8da, 0b1632f, d44b177 | UI/WebUI see mount state, free space, device; a pulled drive or CFexpress card aborts the take as a media fault; record refused with a reason when no media, pulled card, media errored, or < 1 GiB free |
| CFexpress hat card detection | 10853-10991, 12085-12125 | 438a342, 0b1632f, c34f844 | pulled card seen at once, card stays "removed" until remount; Hardware card shows hat status and NVMe model/size/PCIe link |
| Media profile and kernel tuning | 11386-11440 | 26da30e, ebdcd08, 2edc6d0 | recording medium classed (pi-nvme, usb, sd) + filesystem; writer topology picked per class; optional root helper sets block-queue and dirty-page knobs (opt-in) |
| Drive trim worker | 11441-11615, 11941-11966 | d44b177, 04bac89, ce0bd90 | exFAT NVMe trimmed at mount, after deletes freeing >= 1 GiB, after outside deletes, after pre-roll; never overlaps a take; state fields show last result |
| Split-clip merge worker | 11684-11940 | ba0658d, 68516f1 | clips recorded with `frames_per_folder` (part_NNN folders) are flattened back into one folder while camera idle |
| Write buffer events and safety stop | 10993-11052, 11083-11119 | d44b177, 64bbbaa, c5db8b2 | buffer bar level, mode, dropped-frames count pushed as events; at the queue's stop percent Core stops the take cleanly (same as record_stop) |
| Storage pre-roll | 11121-11314 | d44b177 | short raw take through the write path at Core start, card insert, format, or on command; deleted afterwards; result text shown |
| Playback hold and yield window | 10853 (end), 11341-11357, 12559-12620 | f91fafa, a37a902 | playback/download stops when a take, capture, media test, standby or eject starts; hold reason string in state |
| Delete interlock | 12559-12620 | a37a902 | record/capture/timelapse answer "Deleting media. One moment." while a delete runs |
| Controls page backend (Config > Hardware) | 11968-12557 | f5a61b8, 166cc4d, 0a98868, c34f844, dcf09ee, 1319967 | `get_controls` returns file text, validation issues, version info, per-peripheral live status; GPIO line owners; I2C bus list; history of saved versions |
| Hardware file applies without restart | 12228-12351 | dcf09ee | saving the hardware file restarts only the affected driver group (GPIO+PCF8574, NeoRotary4, Grove ADC, CFexpress hat); waits if a take runs; services outside Core listed with a restart command |
| Listen / Try / Test | 12383-12416, 12469-12480 | dcf09ee, 1319967 | `controls_last_input` reports last control that fired; `test_input` fires the saved action of a control as if the pin moved |
| I2C scan | 12471-12520 | dcf09ee | `scan_i2c bus=N` lists answering addresses, with a guess of the device |
| Action catalog for the WebUI | 12521-12556 | f5a61b8, dcf09ee | `list_actions` gives actions plus legal values (ISO, shutter angle, WB, fps, resolution) for the current sensor and Clear HDR state |

## 4. Interfaces added or changed

### Socket commands (all through `handleCommand`; the first five before the command lock)

| Command | Where | Params | Reply members | Notes |
| --- | --- | --- | --- | --- |
| `get_controls` | 12419 | none | `controls{revision,path,display_path,exists,written_by,written_at,errors,warnings,issues,text,replaced,model,peripherals[],i2c_buses,apply,dpi_lines}` | not a flat scalar object: nested objects and arrays |
| `controls_history` | 12453 | `name` optional | `revision,history[{name,saved_at,by,revision}]` or `name,text` | |
| `controls_last_input` | 12471 | none | `seq,section,key,ms_ago` | polled by the page |
| `scan_i2c` | 12481 | `bus` 0-255 | `bus,found[{address,by,guess}]` | refused during take |
| `list_actions` | 12529 | none | action catalog + `values{iso,shutter_angle,shutter_speed,wb,fps,resolution}`, `values_for`, `gestures` | |
| `test_input` | 12561 (in `handleCommand`) | `section`, `key` | `section,key` | runs before lock; takes lock inside the action path |
| `record_stop` (internal) | 11101 | | | the safety-stop thread dispatches it via `dispatchHardwareInputCommand` |
| `storage_preroll` | named only in the busy-guard 12586 | | | handler is outside this slice |
| `set_controls`, `test_output`, `set_media_trim`, `set_clip_merge`, `set_buffer_mode`, `set_storage_preroll` | outside this slice | | | covered by other App units |

`handleCommand` head additions (12560-12612), in order: `handleReadOnlyHardwareCommand` first; `test_input`; `abortSafetyStopFlushForRecord(command.name)` before the lock (also called at 10119 in the hardware-action path); yield-window open for `record_start`, `capture_photo`, `timelapse_start`, `run_media_speed_test`, `enter_standby`, `eject_media`, `format_media`; "Deleting media. One moment." refusal; "Storage pre-roll is running. One moment." refusal for nine commands; the media gate (`mediaGateError`) on `capture_photo`/`record_start`/`timelapse_start`; `waitForMediaTrim(name, 5000)` and `waitForClipMerge(name, 5000)` before takes and media actions.

### HTTP routes
None added in this slice. `playbackHoldReason` feeds `/api/state` `playback_hold` and the `/api/media*` 409 answers elsewhere.

### Events (published with `publishEvent`)

| Event | Lines | Members | Cadence |
| --- | --- | --- | --- |
| `media` | 10813-10826, 10911 | `state,mounted,device,fstype,free_bytes,total_bytes,errno` | when `sameMedium` differs from previous poll |
| `buffer` | 10839-10842, 11033-11045 | `used,capacity,mode` + `bufferMembers` + `recording_dropped_frames` | on change; 250 ms while busy, 1 s idle |
| `controls` | 12342-12346 | `applied` (revision), `groups`, `errors`, `warnings` | after each apply |

### State JSON fields (fragments built here, spliced into `get_state` at 9583/9586)

| Field | Source |
| --- | --- |
| `media_trim_last_result`, `media_trim_last_bytes`, `media_trim_last_ms`, `media_trim_last_unix`, `media_trim_running` | `mediaTrimStateJson` 11595 |
| `clip_merge_pending`, `clip_merge_active`, `clip_merge_last` | `clipMergeStateJson` 11919 |
| `controls_apply` object (`state,detail,pending[{unit,what,command}]`) | `controlsApplyJson` 12353 (inside `get_controls`) |
| `playback_hold` | `playbackHoldReason` 11341 (consumer elsewhere) |

### Config keys (apertar-hardware.conf unless noted)

| Key | Read where in slice | Note |
| --- | --- | --- |
| `[cfexpress_hat] enabled, bus, address` (defaults bus 10, address 0x34) | 10860, 12085-12100 | read by `loadCfeHatConfig()`; slice re-reads on generation change |
| `[media] preroll` (on/off, default on); preroll seconds | 11153 via `parsePrerollConf` | |
| `[storage] clip_merge` (default on) | 11696 via `bufferbudget::clipMergeRequest()` | |
| `[storage] frames_per_folder` | comment 11624 | writer side outside slice |
| `[gpio_buttons] chip` ("auto" or path) | 11988 | |
| `[neorotary4]`, `[pcf8574]`, `[grove_analog]` `bus`, `address` | 12022-12027, 12489-12500 | |
| sections listed in `hardwareGroupOf`/`unitReadingSection`: `gpio_buttons, gpio_encoders, gpio_switches, pcf8574, trigger_output, recording_indicator, neorotary4, grove_analog, cfexpress_hat, storage, ina219, display, imu, mpu6050, bmi160, bmi270, icm42688p, gyro, network` | 12170-12197 | |
| `kernel_tune` in `~/apertar-media-tune.conf` | 11407 | file `kMediaTuneBasePath = /home/pi/apertar-media-tune.conf`, override `/run/apertar-media/media-tune.override.conf` (defined in `src/util/MediaTune.hpp`, outside slice) |

### Environment variables

| Variable | Line | Meaning |
| --- | --- | --- |
| `APERTAR_MEDIA_REQUIRE_MOUNT` | 11336 | `0` turns the record gate off; also off when `simulateCamera` |
| `APERTAR_MEDIA_MIN_FREE_MB` | 11377 | free-space floor, default 1024 |
| `APERTAR_MEDIA_TUNE` | 11403 | `1` enables kernel tuning helper; unset = file `kernel_tune` decides |
| `APERTAR_MEDIA_TRIM` | via `mediaTrimEnvOff()` | `0` off; defined outside slice |
| `APERTAR_STORAGE_PREROLL` | 11154 | `0|1` beats `[media] preroll` for automatic triggers |
| `APERTAR_CLIP_MERGE` | comment 11626 | `0` leaves clips split; read in BufferBudget.hpp |

### Files, scripts, helpers on disk

| Path | Role | Where referenced |
| --- | --- | --- |
| `/usr/local/libexec/apertar-media-tune` | root helper: block queue, vm.dirty_*; run `sudo -n ... apply|restore <disk> <class> <fs>` | 11411 |
| `/usr/local/libexec/apertar-media-trim` | root helper: trim recording drive; exit 3 = unsupported, 4 = timeout | 11484 |
| `scripts/apertar-media-trim`, `scripts/apertar-media-tune`, `config/apertar-media-trim.sudoers`, `config/apertar-media-tune.conf` | repo side of the helpers; install by hand (message at 11504-11508) | |
| `tools/flatten_clip.py` | manual fallback named in merge messages | 11800, 11876 |
| `<clip>/.parts` marker, `<clip>/part_NNN/` | split-clip layout (`framepath::kMarkerName`, `isPartDirName`) | 11745, 11800 |
| `/proc/mounts` (via `mountIdForPath`, `isMountedPath`) | mount check | |
| `/sys/class/nvme/*`, `/sys/block/nvme*n1/size`, `/sys/bus/i2c/devices` | read for hat card and bus list | 12062-12080, 12148 |
| `systemctl show -p ActiveEnterTimestampMonotonic` | per unit | 12361 |
| apertar-hardware.conf (+ history dir) via `hardware::configStore()` | text, revision, history | 12225, 12418-12470 |

### Log lines (journal)
`ApertarCore media:`, `media profile:`, `buffer: safety stop at N %`, `storage preroll:`, `clip merge:`, `controls:` prefixes, with key=value fields. Upstream has no equivalent prefixes for these.

### UI elements
None in this file. Consumers: WebUI Controls/Hardware cards, Performance card (trim/merge switches), buffer bar, Remote controls card, Try buttons (other units).

## 5. ORIGINAL code modified

Only `handleCommand`'s head (upstream 9091-9120 `@upstream-1.6.0`).

| Region | Upstream | Port | Kind |
| --- | --- | --- | --- |
| Start of `handleCommand` | takes `commandMutex_` first | five hardware read commands and `test_input` answered before the lock; `abortSafetyStopFlushForRecord` before the lock | extended in place (new pre-lock dispatch) |
| After lock | `checkRecordingFailure`; media-writes-pending refusal | yield-window open block, delete refusal, pre-roll refusal inserted ahead of media-writes-pending refusal | extended in place |
| Before media-action checks | none | media gate on three record commands | extended in place |
| After speed-test refusal | none | `waitForMediaTrim` + `waitForClipMerge` (5 s block) | extended in place |
| `mediaAction` and speed-test conditions | upstream text | unchanged | not changed |
| Rest of chain (`user_activity`, `set_standby_timeout`...) | upstream | unchanged in this slice | |

Behaviour change: with a missing, pulled, errored, or nearly full media root, `record_start`, `capture_photo`, `timelapse_start` now fail with an error reply where upstream attempted and failed later or in the writer (confirmed: upstream has no `mediaGateError`; upstream isMountedPath at 2017/2034 is used by `eject`/`format` paths). Not in this slice, so no row in section 6 for those.

## 6. New abstractions

| Name | Kind | Files | Purpose | Upstream equivalent for the same job |
| --- | --- | --- | --- | --- |
| media watcher thread (`runMediaWatcher`) | worker thread | ApertarCoreApp.cpp 10853 | poll mount id, statvfs, hat slot each 1 s (250 ms in take); publish `media` event | none. Upstream asks `isMountedPath`/statvfs on demand in `eject`/`format`/state (`@upstream-1.6.0` ApertarCoreApp.cpp:2017, 2034) |
| `MediaSnapshot`, `probeMediaRoot`, `cachedMediaSnapshotOrProbe` | header-only module | src/util/MediaProbe.hpp (292) | mount state struct | none |
| `MediaFault`, `MediaIntent` | header-only modules | src/util/MediaFault.hpp, MediaIntent.hpp | fault latch, eject intent | none |
| `CfeHatReader`, `CfeHatConfig` | header-only class | src/util/CfeHat.hpp (75) | read hat status byte over I2C | none in Core; upstream has the external `apertar-cfe-automounter` service only |
| `MediaProfile`, `MediaTune` | header-only modules | src/util/MediaProfile.hpp (236), MediaTune.hpp (318) | classify medium, per-medium tuning file | none |
| media trim worker (`runMediaTrim`) + helper | worker thread + root helper | ApertarCoreApp.cpp 11482, scripts/apertar-media-trim | trim drive when idle | none. Upstream has no trim and ships no helper script; it does call root helpers `/usr/local/libexec/apertar-standby-usb`, `apertar-standby-low-power` through `sudo -n` (ApertarCoreApp.cpp:1544, 1549) but the repo `scripts/` holds only `start-apertar-core.sh` |
| clip merge worker (`runClipMerge`) | worker thread | ApertarCoreApp.cpp 11725; src/cdng/ClipMerge.hpp (182), FramePath.hpp (79) | flatten part folders | none |
| buffer event thread, safety stop thread | worker threads | 10993, 11083; src/util/BufferBudget.hpp (382) | push buffer level; stop take at threshold | none. Upstream sends state/events from the publisher paths and has two worker threads, preview and MJPEG (`@upstream-1.6.0` ApertarCoreApp.cpp:6825, 6834) |
| storage pre-roll worker | worker thread | 11184; src/util/StoragePreroll.hpp (273) | warm-up take | none |
| controls worker | worker thread | 12244 | apply hardware file on save or every 2 s | none. Upstream reads the hardware file once at start; each class parses its own section (`@upstream-1.6.0` ApertarCoreApp.cpp:3408, 4248 for candidate paths) |
| `hwconf` namespace (`Document`, `parse`, `validate`, `controlRows`, `peripheralSettingsJson`, `modelJson`) | header-only module | src/hardware/HardwareConfigText.hpp (1141), ControlsModel.hpp (390) | parse/validate the whole hardware file | none |
| `hardware::HardwareConfigStore` (`configStore()`) | singleton class | src/hardware/HardwareConfigStore.{hpp,cpp} | file text, revision, history, replaced-by-default detection | none |
| `hardware::actions::catalogJson` | header-only module | src/hardware/ActionCatalog.hpp (360) | catalog of button actions | upstream parses action strings inline: `parseHardwareActionNumber` etc. (ApertarCoreApp.cpp:1358-1408), `hardware::parseButtonActions` (:8635) |
| `hardware::probeI2cAddress`, `GpioChipInfo`, `readGpioChipInfo`, `headerGpioChipPath` | functions in class-less cpp | src/hardware/I2cProbe.cpp, GpioChipInfo.cpp | read-only probe of bus/chip | none |
| `playback` namespace: `Hold`, `HoldSignals`, `playbackYield()`, `trimIdleFrameSlots` | header-only modules | src/playback/PlaybackHold.hpp, DecodeSlots.hpp | one rule: may playback read the card | none (upstream has no playback decoder) |
| second command dispatcher `handleReadOnlyHardwareCommand` | function | 12418 | pre-lock reads | none. Upstream: one chain under one mutex |
| host tests | test programs | tools/*_test.cpp, media_trim_test.sh | | upstream Core has none |

## 7. Removed, narrowed or hidden relative to upstream

None removed in this slice (pure addition). Behaviour narrowing:

| What | Where | Effect |
| --- | --- | --- |
| record/capture/timelapse refused when media gate fails | 12589-12593, 11359 | upstream let the writer find out; now needs mount and 1 GiB free (`APERTAR_MEDIA_MIN_FREE_MB`) |
| record/capture/timelapse/format/eject/mount/speed test/standby refused while pre-roll runs | 12581-12585 | up to `seconds` of refusals after Core start (automatic pre-roll starts 3 s after boot, after trim) |
| record/capture/timelapse refused while a delete runs | 12578 | |
| hardware file edit while a take runs is not applied until the take ends | 12253 | |
| record/capture start waits up to 2 s + 1 s for a running trim, up to 1 s for a rename | 11941, 11905 | |
| `scan_i2c` refused during a take | 12482 | |

## 8. Board assumptions (hard-coded in this slice)

| Assumption | Line | Detail |
| --- | --- | --- |
| CFexpress hat at I2C bus 10, address 0x34 by default | 12085-12092; CfeHat.hpp | Pi 5 / CM5 board with the hat; Pi 5 numbering of the RP1 I2C buses |
| Media device is NVMe on PCIe: `/sys/class/nvme/*/transport == "pcie"`, `/sys/block/nvmeXn1`, link speed/width files | 12059-12082 | PCIe on Pi 5; one NVMe at most (first pcie controller returned) |
| exFAT NVMe stalls after ~0.9 TB; trim after 1 GiB | comment 11450; 11460 | measured on the owner's drive |
| exFAT rename cost model, `RENAME_NOREPLACE` | 11618, 11838 | exFAT card assumed |
| Install paths `/usr/local/libexec/apertar-media-{tune,trim}`; `sudo -n`; user `pi` home (`/home/pi/apertar-media-tune.conf`) | 11404, 11484 | Raspberry Pi OS Lite layout |
| GPIO header chip picked by `headerGpioChipPath()`; chip lines read up to 28 (`readGpioChipInfo(chipPath, 28)`) | 11988-11989 | 28 header lines: Pi 40-pin; chip numbering resolved in GpioChipInfo.cpp (outside slice) |
| Default I2C bus 1 for neorotary4/pcf8574/grove when file omits it; default addresses 0x49, 0x20, 0x04 | 12022, 12489-12500 | |
| Known-address guess table includes 0x1a "IMX585 / IMX283 sensor", 0x34 hat, 0x40-0x45 INA219, 0x68/0x69 gyro | 12499-12504 | |
| `/sys/class/i2c-adapter` missing "on this kernel", so `/sys/bus/i2c/devices` used; `/dev/i2c-6 -> i2c-10` link mentioned | 12145-12147 | kernel and DT overlay specific |
| systemd units `apertar-ui-direct`, `apertar-cfe-automounter`, `apertar-network` | 12184-12197 | the owner's image |
| 4K figures in comments: 415 MB/s for 16-bit 4K25, 0.7-1.4 GB pre-roll clip | 11376, 11300 | comments only |
| Thread nice 10 for merge via `setpriority(PRIO_PROCESS, gettid)` | 11726 | Linux; no core pinning in slice |
| DPI lines (`facts.dpiLines`) from `hardwareConfigFacts()` | 12449 | DPI display on header pins; defined outside slice |
| Fan: none in this slice. RAM size: used only through bufferbudget (RAM mode, `used/capacity` MiB), constants outside slice. Four cores: none in this slice | | |

## 9. Open questions for stage 2 (not judged here)

- Whether `get_controls` nested JSON breaks the flat-scalar rule (Brief hint 1); compare `@upstream-1.6.0` replies.
- `d44b177` is a 19-commit squash; it wrote 537 lines here (watcher additions, buffer events, safety stop, whole pre-roll, trim worker). Split by feature needs the squash's parent history (fork-log row 138, `drop-frames-campaign` on the Pi).
- Pre-roll refusal list names `storage_preroll`, `set_storage_preroll` is in the command list; handlers are outside this slice.
- `controlsApplyJson` shells out `systemctl show` for each pending unit inside the `get_controls` read path (12361), which is documented as lock-free.
