# R1: every Core code path a speed-ramp mode ladder would touch (Apertar-Core `d4ad539`)

Reader R1, cloud session, 2026-10-27. Read-only. Nothing built or run.
Tree: Apertar-Core (cloud branch `clearhdr-fixes`) at `d4ad539` (T23..T31 on `f60e301`).

Short names used below (all `@d4ad539` unless marked):
- `CC` = `src/camera/CameraController.cpp`
- `Hdr` = `src/camera/CameraController.hpp`
- `App` = `src/ApertarCoreApp.cpp`
- `Web` = `src/web/WebControlPage.cpp`
- `Types` = `include/apertar/core/Types.hpp`
- `QML` = Apertar-UI `qml/CameraPage.qml`, from the KB map `llm/ui-map.md` (refs against `upstream-1.6.0`, `ui-map.md:5`). The UI source is not here, so every QML line is UNCONFIRMED.

Labels: CONFIRMED = I opened the line. PROBABLE = derived (I say how). UNCONFIRMED = not checked.

---

## (a) How settings select a sensor mode

There is no "sensor mode" object in the settings. A mode is the triple
**(resolution, rawBitDepth, clearHdr)** in `CaptureSettings` (`Types:124-176`). CONFIRMED.

**1. Accepted resolutions.**
- `isImx585LowResolutionAlias` `CC:375-379`: 1920x1080, 1928x1090. CONFIRMED.
- `isImx585FullHdCropResolution` `CC:381-392`: nine 1920-wide crops, 1920x1038 down to 1920x752. CONFIRMED.
- `isImx585HighResolutionAlias` `CC:394-399`: 3840x2160, 3856x2180, 3840x2200 (the 16-bit Clear HDR readout counts as 4K). CONFIRMED.
- `isImx585Raw12CropResolution` `CC:401-412`: nine 3840-wide crops, 3840x2076 down to 3840x1504. CONFIRMED.
- These match the facts' nine 3840 crops and nine 1920 crops. CONFIRMED.
- The same lists gate `clampCaptureSettings` (`CC:557-571`, unknown size falls back to the default 3840x2160) and `CameraController::validateResolution` (`CC:10098-10116`). CONFIRMED.

**2. Normalising the request.** `normalizedResolutionForSensor` `CC:2461-2512`. For IMX585 (`CC:2496-2508`):
- 1332x990, 2028x1080, 2028x1520 and the low aliases become 1920x1080.
- 1920 crops and 3840 crops pass through unchanged.
- The high aliases become 3840x2160.
- Anything else becomes 1920x1080. CONFIRMED.

**3. Resolution to sensor mode.** `sensorModeForRequestedResolution` `CC:2290-2361`. IMX585 branch `CC:2330-2356`:
- Pixel format and bit depth come from `rawBitDepth` (`CC:2296-2297`). CONFIRMED.
- Crops map to themselves. 4K maps to 3840x2160. CONFIRMED.
- With 16-bit and 3840x2160, the raw mode becomes 3840x2200 (`CC:2353-2354`). CONFIRMED.
- `dngModel` is "IMX585-AAQJ1". CONFIRMED.

**4. Only one candidate per request on IMX585.** `sensorModeCandidatesForRequestedResolution` (`CC:2372-2459`) returns after the first candidate for every family except IMX477 and IMX577 (`CC:2440-2441`). CONFIRMED.
- So a rung that libcamera rejects has no fallback on IMX585.
- One exception: for the 3840 crops, `configureAndStart` may retry with libcamera's own sensor config (`allowAutoSensorConfigFallback`, `CC:6681-6684`, `:6702`). That retry could pick a different sensor mode without telling anyone. PROBABLE (from the loop shape; not seen on hardware).

**5. Bit depth and Clear HDR.**
- `supportedRawBitDepthForSensor` `CC:2803-2828`. IMX585 (`CC:2814-2818`): Clear HDR allows 16 or 12 (anything else becomes 12). SDR allows 10 or 12. CONFIRMED.
- `sanitizeSettingsForSensor` `CC:2830-2876`:
  - H.264 and ProRes force 10-bit and Clear HDR off (`CC:2834-2840`). CONFIRMED.
  - Clear HDR forces the resolution to 3840x2160 (`CC:2855-2858`). CONFIRMED.
  - It clamps fps to the mode's ceiling (`CC:2863-2873`). CONFIRMED.
  - It then runs `enforceLosslessCaptureLimits` (`CC:2874`). CONFIRMED.
- Clear HDR is a sensor control, not a libcamera format. `setSensorWideDynamicRange` (`CC:5668-5695`) writes `V4L2_CID_WIDE_DYNAMIC_RANGE` on the subdev. It retries 4 times, 50 ms apart, on EBUSY "while the previous stream is still winding down" (`CC:5680-5689`). It runs in `CameraSession::start` before the CameraManager exists (`CC:5910`). The HDR knobs follow (`CC:5912`). CONFIRMED.
- Clear HDR also swaps the tuning file to the `_clearHDR` variant (`CC:5895-5899`, `:5902-5904`). CONFIRMED.

**6. Per-format saved profiles.**
- `formatSettings_` is a `std::map<RecordingFormat, CaptureSettings>` and `stillSettings_` is an `optional<CaptureSettings>` (`Hdr:143-144`). CONFIRMED.
- Each profile is a whole `CaptureSettings`, so it carries its own resolution, rawBitDepth, clearHdr and fps.
- Profile keys are cdng (lossy DNG shares it, `settingsProfileFormat` `CC:621-624`), mlv, h264, prores and still (`CC:650-663`). CONFIRMED.
- `setRecordingFormat` swaps in the saved profile of the new format. It keeps only `tuningFile`, `timecodeMode` and the metering from the current one (`CC:9074-9088`). CONFIRMED.
- `restoreModeGeometryLocked` (`CC:10080-10096`) copies resolution, rawBitDepth, clearHdr and fps from the saved profile. It is used only when photo mode toggles (`setStillExposureMode` `CC:9007-9008`, `startTimelapse` `CC:9637-9638`). CONFIRMED.
- `persistSettingsLocked` (`CC:10071-10078`) writes `settings_` into the active profile on every commit. CONFIRMED.

---

## (b) The fps ceilings

**Probe.**
- `struct SensorMode` (`Hdr:33-40`): format, bitDepth, size, clearHdr, maxFps, crop. CONFIRMED.
- `probeSensorModes` (`CC:5753-5833`):
  - It runs once for WDR off and once for WDR on (`CC:5762`).
  - It configures every raw format and size and reads `FrameDurationLimits.min` (`CC:5809-5811`).
  - It logs one line per mode and the total time (`CC:5821-5831`). CONFIRMED.
- `probeSensorModesOnce` (`CC:5835-5848`) is called from the first `CameraSession::start` (`CC:5909`). `APERTAR_SENSOR_PROBE=0` turns it off (`CC:5843`). CONFIRMED.
- KB result: 42 modes in 63 ms on the Pi (`working/sensor-capabilities.md:51`). CONFIRMED in the KB, as given.
- `CameraController::sensorModes` (`CC:9916-9920`) returns the probe list. `list_sensor_modes` (`App:9517-9534`) prints it. CONFIRMED.

**Ceiling functions.**
- `probedMaximumFps(size, bitDepth, clearHdr)` (`CC:2723-2732`) matches the probe exactly on size, bit depth and WDR state. CONFIRMED.
- `tableMaximumFpsForResolution` (`CC:2736-2792`). IMX585 (`CC:2777-2786`):
  - 3840x2160 returns `clearHdr && !sensorLimitKnown ? 25.0 : 30.0` (`CC:2780`). So 4K is 30 in SDR too.
  - The 3840 crops return 60 (`CC:2781-2782`).
  - 1920x1080 and the 1920 crops return 60 (`CC:2783-2785`). CONFIRMED.
- `maximumSupportedFpsForResolution` (`CC:2794-2801`) returns min(table, probe) when the probe has the mode, and the table otherwise. It looks the probe up with `sensorModeForRequestedResolution`'s raw size, so 16-bit Clear HDR finds 3840x2200. CONFIRMED.
- Users: `sanitizeSettingsForSensor` (`CC:2863`) and `configureAndStart` (`CC:6945-6951`; there the fps is clamped to the newly configured mode). CONFIRMED.
- `enforceLosslessCaptureLimits` (`CC:2559-2580`): any IMX585 cDNG with `LosslessJpeg` is capped at **30 fps at every resolution**, and ISO at 800 (`CC:2564-2579`). Uncompressed cDNG (the default, `Types:152`), MLV and lossy DNG are not capped here. CONFIRMED.
- Hard bounds: `clampCaptureSettings` and `setFps` accept 0 < fps <= 280 (`CC:573-574`, `:8822-8825`). No lower bound above zero. CONFIRMED.

**Exactly what lets 3840x2160 SDR use the probed 60.**
1. `CC:2780`: split the line.
   - Clear HDR: `sensorLimitKnown ? 30 : 25` (as today).
   - SDR: `sensorLimitKnown ? 60 : 30` (or any value of 60 or more, since the probe then wins through `min`).
   - CONFIRMED that this is the only Core cap on 4K SDR uncompressed: the sanitiser and `configureAndStart` both go through `maximumSupportedFpsForResolution`.
2. Keep 30 when the probe is off or failed (`sensorLimitKnown == false`). The 30 at an unknown link frequency is the safe value. PROBABLE (the comment at `CC:2778-2779` gives 25 for Clear HDR at 720 MHz; the SDR figure at 720 MHz is UNCONFIRMED).
3. The three UI copies cap 4K at 30. Each must change, and must look at `clear_hdr`:
   - `App:1151-1154` (`maximumPcfFpsForSettings`, hardware dial and buttons).
   - `Web:4976-4978` (`maximumSupportedFpsForSnapshot`).
   - QML `maximumSupportedFpsForResolution` `:733` (UNCONFIRMED, KB `ui-map.md:151`).
   - CONFIRMED for App and Web.
4. Leave `enforceLosslessCaptureLimits` alone. 4K at 50 fps is meant for uncompressed cDNG or MLV. The 622 MB/s needs T24 O_DIRECT (facts).

---

## (c) The change path and its cost

**Gates while recording.** All CONFIRMED:
- `setResolution` `CC:8772-8775`.
- `setRawBitDepth` `CC:9251-9254`.
- `setClearHdr` `CC:9287-9290`.
- Also format (`CC:9061`), compression (`:9110`), lossy ratio (`:9126`), ProRes profile (`:9142`), tuning (`:9185`), H.264 resolution (`:9419`), still mode (`:9001`), ProRes colour (`:9155`), preview profile (`:9168`), HDR knobs (`:9316-9317`).

**`applySettingsLocked(next, requiresReconfigure, commit)` `CC:10004-10069`.**
- It forces a reconfigure when photo mode, the ISP colour profile or Clear HDR changes (`CC:10006-10008`). CONFIRMED.
- It reconfigures (`session_->reconfigure`) or only pushes controls (`applyControls`) (`CC:10035-10037`). CONFIRMED.
- **Recovery runs only when `commit` is true** (`CC:10039-10052`): reconfigure back to `settings_`, stay Ready. CONFIRMED.
- With `commit == false`, which is how T31 ramp steps call it, a failed reconfigure goes straight to `state_ = Error` (`CC:10054`). There is no recovery. CONFIRMED.
- On success: `settings_ = session_->currentSettings()`. Then persist and emit only if commit (`CC:10061-10068`). CONFIRMED.

**`CameraSession::reconfigure` = `stop()` + `start()`** (`CC:6122-6134`). CONFIRMED.

**What `stop()` does** (`CC:6057-6120`). All CONFIRMED:
- Closes the recording frame gate (`recordingFramesEnabled_ = false`, `CC:6060`).
- Disconnects `requestCompleted` and calls `camera_->stop()` (`CC:6063-6066`).
- Releases the phase lock (`CC:6071-6076`).
- **Stops every recorder:** gyro, H.264, ProRes, the DNG/MLV queue (`recorder_.stop()`, which joins the writer workers and so drains the queue, `CC:3583-3697`), audio (WAV finalised), photo writer (`CC:6078-6083`).
- Drops pending photos and any still exposure (`CC:6084-6093`).
- Unmaps raw and preview buffers, clears requests, the cached ProRes and raw dma-bufs, and the allocator (`CC:6094-6107`).
- Releases the camera and **stops and destroys the CameraManager** (`CC:6109-6118`).

**What `start()` does** (`CC:5878-6041`). All CONFIRMED:
- Resolves tuning, calls the probe (once), sets WDR and the HDR knobs (`CC:5891-5913`).
- **Builds a new CameraManager** in a loop of up to 3 tries (`CC:5917-6006`).
  - A second CameraManager is built when the default tuning path for the detected model differs (`CC:5961-5979`).
  - **And again whenever the ISP colour profile is a log profile** (`logPreview`, `CC:5905`, `:5986-6004`). That covers any cDNG preview profile other than Standard (`activeIspColorProfile`, `Types:183-190`).
- Acquires the camera, sanitises, then `configureAndStart` (`CC:6013-6029`).

**What `configureAndStart` does** (`CC:6656-7076`). All CONFIRMED:
- Walks the candidate list (one on IMX585).
- Buffer count: `rawCameraBufferCount(clearHdr)` (`CC:6767-6769`). That is 4 SDR and 8 Clear HDR (`kConfiguredBufferCount`/`kClearHdrBufferCount`, `CC:1063-1067`), plus the media profile's extra on exFAT/NTFS (comment `CC:1184-1186`), env 3..16 (`CC:1181-1189`).
- Calls `validate` and `configure` (`CC:6823`, `:6841`).
- Clamps fps to the new mode (`CC:6945-6951`).
- Allocates buffers. In Clear HDR the raw buffers are CPU-cached dma-heap buffers (`CC:7010-7014`).
- Maps the raw buffers (`CC:7022`) and tops up the raw copy pool to 6 (`CC:7024-7025`).
- Makes one request per buffer (`CC:7036`, `:7149-7188`).
- Sets the copy worker's hold limit to buffers−2 (`CC:7041-7046`).
- Starts the camera with the initial controls and queues all requests (`CC:7048-7074`).

**Can it run during a take?** No. CONFIRMED.
- If the gates were simply removed, `stop()` would end every recorder. The DNGs, the WAV and the gyro file would be closed.
- `writeFpsRampLog` would not run. It is only called from `stopRecording`, `CC:6350`.
- The frame gate would stay closed after `start()`.
- Yet the controller's `recording_` and `state_ = Recording` would stay set. Nothing in `applySettingsLocked` touches them.
- So the UI would show a running take that writes nothing.

**Why it is slow.** PROBABLE, from the steps above. None of it is timed in Core.
1. `recorder_.stop()` drains the DNG queue synchronously. The queue holds up to 12 frames (24 for compressed DNG), or the media profile's value (`CC:3505-3509`). Core logs "recorder stop time" when this takes over 0.2 s (`CC:3683-3689`).
2. The audio stop finalises the WAV.
3. The CameraManager is torn down and rebuilt: pipeline handler, IPA load, tuning parse. Twice with a log preview profile.
4. A Clear HDR change adds WDR retries of up to 4 x 50 ms (`CC:5680-5689`) and a different tuning file.
5. Allocation and mmap of 4-10 raw buffers (12.4 MB each for 4K 12-bit packed; 16.9 MB each in Clear HDR, comment `CC:1064`), plus the preview buffers.
6. Sensor stream-on, then the first frames.

Cinemate's 186 ms (facts) did not rebuild the camera manager. Core's figure is UNCONFIRMED and probably larger.

**Cheaper path, not in the code today.** For an SDR-to-SDR switch (same WDR state, same tuning), the CameraManager could probably be kept:
- `camera_->stop()`, free the buffers, `configure()` a new configuration, allocate, `start()`.
- That is `configureAndStart` without `start()`'s manager loop.
- PROBABLE. libcamera allows reconfiguring an acquired, stopped camera.
- A WDR change probably needs the manager rebuilt. The driver's mode list changes with WDR, and the tuning file changes. PROBABLE.

---

## (d) T31 ramp code

**Controller.** All CONFIRMED:
- `setFps(fps, takeOnly)` `CC:8799-8844`.
  - `takeOnly` refuses once the take has ended (`CC:8802-8807`).
  - `rampingTake = recording_ && fps changed` (`CC:8808`).
  - It is refused without `fpsRampEnabled`, and for H.264, ProRes and photo (`CC:8809-8821`).
  - The request is sanitised with the *current* resolution, so it is clamped to the running mode's ceiling (`CC:8830-8836`).
  - It then calls `applyFpsStepLocked(effectiveFps, rampingTake, commit = !rampingTake)` (`CC:8843`).
- `applyFpsStepLocked` `CC:8846-8885`:
  - Shutter policy: angle rescales, exposure clamps to the frame and keeps `rampNominalShutterUs_` (`CC:8852-8869`).
  - It marks `rampTakeChanged_` and logs (`CC:8872-8878`).
  - It calls `applySettingsLocked(next, false, commit)`, i.e. **no reconfigure** (`CC:8879`), and emits the UI event even when not committing (`CC:8880-8881`).
- `restoreFpsAfterRampLocked` `CC:8887-8904`: after a ramped take, it goes back to `rampTakeBaseFps_` and persists. It restores **fps only**. Callers: `stopRecording` `CC:9815`, `checkRecordingFailure` `CC:9840`, shutdown `CC:8708-8716`. The base is recorded at `CC:9556`.
- `setFpsRamp` `CC:9458-9472`: the flag cannot change during a take.

**Session.** All CONFIRMED:
- `applyControls` (`CC:6136-6172`) calls `noteFpsChange` on every rate change (`CC:6163`). It also releases the phase lock (`CC:6159-6162`).
- `noteFpsChange` (`CC:8047-8065`) adds a grace window and queues an event.
- `stampFpsRampEvents` (`CC:8075-8085`) stamps events with a frame index and returns the take's **base fps**. That value is every frame's `FrameRate` and timecode rate (`CC:7752`).
- `pairFpsRampEvents` (`CC:8099-8134`) finds the first frame that runs at the new period.
- `writeFpsRampLog` (`CC:8138-8192`) writes `fps-ramp.txt` into `recorder_.folderPathString()` at stop. **It then clears `recordingBaseFps_`, the events and the stamp count** (`CC:8144-8151`).
- State: `FpsRampEvent`, `rampEvents_`, `recordingBaseFps_`, `rampFirstWallClockUs_` (`CC:8566-8584`). They are reset at `startRecording` (`CC:6188-6199`).

**App stepper.** All CONFIRMED:
- `startFpsRamp(to, seconds)` `App:9174-9221`.
  - `seconds == 0` jumps in one `setFps`.
  - Otherwise a thread makes `|to−from|` steps (1 fps each, at most 200), waiting on a condition variable between steps (`App:9193-9203`).
  - Each step calls `setFps(.., takeScoped)`.
- **It stops at a mode's limit like this:** after a step it reads back `settings().fps`. If the value did not move, it logs "fps ramp stopped: <x> fps is this mode's limit" and ends (`App:9208-9215`). A refused step also ends it (`App:9205-9207`).
- `stopFpsRamp` `App:9223-9233`. It is called at `record_start` (`App:11013`), `record_stop` (`App:11174`), a recording failure (`App:7065`, `:9391`), the media watcher (`App:9265`) and shutdown (`App:6959`).
- Command `ramp_fps {to, seconds}` `App:9800-9809` (seconds clamped 0..600). `set_fps_ramp {enabled, shutter}` `App:9788-9798`.
- State fields: `fps_ramp_stepping` and `fps_take_base` (`App:7884-7885`, web state only).

---

## (e) Recording lifecycle

**Controller.** All CONFIRMED:
- `startRecording` `CC:9517-9567`: checks, then `session_->startRecording(mediaRoot_, settings_, audio, gyro)` (`CC:9545`). It sets `recording_`, `rampTakeBaseFps_`, `state_ = Recording` and emits.
- `stopRecording` `CC:9805-9822`: session stop, fps restore, error and fault, emit.
- `checkRecordingFailure` `CC:9824-9846`: called by the App loop. It ends the take through `session_->stopRecording(mediumGone)` on a write error or a yank.

**Session `startRecording`** `CC:6174-6316`. All CONFIRMED:
1. Reconfigures if a photo stream override is active (`CC:6181`).
2. Resets `recordingClock_` (one BOOTTIME→wall offset per clip), the gap estimate and all ramp state (`CC:6187-6202`).
3. `DngRecordingQueue::reserveClipFolder` and create the folder (`CC:6204-6211`).
4. Gyro `start(clipFolder)`. A gyro failure is only logged (`CC:6213-6226`).
5. Audio `start(clipFolder, options{fps, timecodeMode, fpsRamp})`. An audio failure fails the take (`CC:6228-6246`).
6. H.264/ProRes: their recorders `startAtFolder` (`CC:6248-6296`).
7. Raw: media profile, then `recorder_.startAtFolder(clipFolder)` (`CC:6298-6303`).
8. Opens the frame gate with the cadence wait armed (`CC:6307`).

The App's `record_start` broadcasts `prepare_recording` and sleeps 220 ms before this when audio is on (`App:11094-11097`). CONFIRMED.

**Session `stopRecording`** `CC:6322-6358`. In order, CONFIRMED:
- close the frame gate
- capture and phase-lock stats
- gyro stop
- H.264 stop
- `recorder_.stop(mediumGone)`
- `writeFpsRampLog`
- ProRes stop
- audio stop (finalise unless the medium is gone)

**Clip naming and numbering.** `allocateClipFolder` `CC:3854-3896`. CONFIRMED:
- Format prefix: `cDNG_`, `MLV_`, `H264_`, `cDNG_3to1_`/`cDNG_5to1_`, `ProRes_`.
- Then `%y-%m-%d`, then `_C####`, the **first number whose folder does not exist** (1..9999).
- Frames are `<clip>_<9-digit index>.dng` (`CC:3898-3905`). The MLV is `<clip>.MLV` (`CC:3488`).
- `reelName` = clip name (`CC:3819`).
- There is no take id separate from the clip folder.

**Frame index.**
- `DngRecordingQueue::startAtFolder` resets `frameIndex_` to 0 (`CC:3451`). CONFIRMED.
- `nextFrameIndex(ts, countOnly)` `CC:3734-3742`. With `fpsRampEnabled` it counts 0, 1, 2 ... (`CC:7741`). CONFIRMED.

**Timecode.** All CONFIRMED:
- RecRun in DNG = `frameIndex / round(metadata.fps)`, with `metadata.fps` = the take base (`CdngEncoder.cpp:333-349`).
- FreeRun in DNG uses `timecodeWallClockUs`. During a ramp that is `rampFirstWallClockUs_ + frameIndex/base`. `rampFirstWallClockUs_` is re-anchored whenever `frameIndex == 0` (`CC:7753-7759`).
- MLV writes one INFO timecode at open (`MlvEncoder.cpp:1115-1119`).
- The WAV's iXML/BWF timecode is computed from the clip start (`AudioRecordingSession.cpp:118-140`, `:792-819`).

**Format differences.**
- MLV writes `MLVI` with the fps (`MlvEncoder.cpp:1081-1093`) and `RAWI` with width, height, bit depth and black/white levels **once, at open** (`MlvEncoder.cpp:1180-1195`; open on the first frame `CC:4070-4072`). So a mode change needs a new MLV file. CONFIRMED.
- DNG carries size per frame. Editors expect one format per folder (facts).
- H.264 and ProRes cannot ramp at all (`CC:8816-8819`). CONFIRMED.

**Audio and gyro per clip.**
- Both start with the clip folder and stop at clip end. They are not take-level objects (`CC:6213-6246`, `:6345-6352`). CONFIRMED.
- Gyro aligns at `frameIndex == 0` (`CC:7792-7793`). Audio follows every frame through `observeVideoFrame` (`CC:7794`). CONFIRMED.
- With `fpsRamp`, the WAV ends at the last frame's own duration (`Types:211`). CONFIRMED.

**What ending one clip and opening the next inside one take would need.** PROBABLE, from the lines above:
1. **Take id.** The controller keeps `recording_` and `rampTakeBaseFps_` across the split. The session needs a take-level "clip index". Today the take is the clip folder.
2. **Clip suffix.** `allocateClipFolder` scans for the first free `_C####`. A sub-clip name such as `<take>_C0007_2` (or Cinemate's scheme, see R2) has to be built from the first clip's name, not by a new scan. Otherwise the second clip becomes `C0008` and looks like a new take. Decide whether `reelName` (`CC:3819`) stays the take name.
3. **Base fps continuity.** `recordingBaseFps_` is set from `settings.fps` at session start (`CC:6193`) and cleared by `writeFpsRampLog` (`CC:8151`). A split must flush the clip's events without clearing the base, and must not re-read the current (mid-ramp) fps as the base.
4. **Timecode offset.** RecRun restarts at 00:00:00:00 in every new folder (frame index 0). It needs an offset of "frames written so far in this take", or the index must keep counting (DNG names would then not start at 0). FreeRun re-anchors at index 0 (`CC:7756`). That is honest wall time, so the switch gap shows as a jump.
5. **Ramp log.** One `fps-ramp.txt` per clip folder, plus a line for the switch: from/to mode, last frame of clip N, first frame of clip N+1, gap in µs or frames.
6. **Audio.** Either one WAV per clip (stop/start: the gap's audio is lost, and the ALSA reopen time is unmeasured) or one take-level WAV in the first folder (real time across the gap). Today's code only does per clip.
7. **Gyro.** The same choice.
8. **Cadence and drops.** Re-arm the cadence gate (`CC:7474-7480`) for the new rate. Reset `haveLastRecordingSensorTimestamp_` or open a grace window, or the switch gap is counted as drops (`CC:8230-8237`) and raises the dropped-frame warning.
9. **Raw copy pool.** After a switch to a bigger frame, the pool's smaller buffers never fit (`CC:3781-3782`). `reserveRawPool` adds nothing when it already holds 6 (`CC:4156`). PROBABLE: fresh 12 MB allocations on the copy worker for the first frames.
10. **Restore at stop.** Restore the start rung (resolution, bit depth, Clear HDR), not only the fps. That is one more reconfigure after the take.

---

## (f) App side: commands, state, settings, persistence

**Handlers.** CONFIRMED:
- `set_fps` `App:9598-9604`
- `set_resolution` `App:9637-9646`
- `set_raw_bit_depth` `App:9720-9733`
- `set_clear_hdr` `App:9735-9742`
- `set_fps_ramp` `App:9788-9798`
- `ramp_fps` `App:9800-9809`
- `record_start` `App:11010-11105` (stops the stepper first, `:11013`)
- `record_stop` `App:11173-11185`
- `list_sensor_modes` `App:9517-9534`
- `help` list `App:9537` (a new command must be added there)

**Hardware dial and buttons.** CONFIRMED:
- `target == "fps"` picks from `availablePcfFpsOptions` (`App:8565-8573`).
- Step actions (`App:8827-8832`).
- `fps<number>` action (`App:8755-8759`).
- Resolution dial (`App:8575-8585`) uses `availablePcfResolutionOptions` (`App:1195`).

**State and settings JSON: three writers.** A new field must go into all three. CONFIRMED:
1. `settingsEvent` `CC:141-200`. Pushed to the touch UI on every emit. Fields include `resolution`, `width`, `height`, `fps`, `raw_bit_depth`, `clear_hdr`, `fps_ramp`, `fps_ramp_keep_exposure` (`CC:146-149`, `:176-177`, `:189-190`).
2. `settingsBody` `App:168-221`. Command replies and `get_state` (`App:9561`).
3. `buildWebStateJson` `App:7743-…`. The WebUI's `/api/state` (`App:7186`, polled at `Web:10260`). Fields `resolution`/`width`/`height`/`fps` at `App:7899-7902`, `clear_hdr` `:7927`, `fps_ramp` `:7929-7930`, `raw_bit_depth` `:7935`.

**Persistence.** CONFIRMED:
- File `$XDG_CONFIG_HOME/apertar-core/camera_settings.conf` or `~/.config/...` (`CC:357-368`).
- Reader `loadPersistedCaptureSettings` `CC:632-771`. Profile prefixes `profile.<still|cdng|mlv|h264|prores>.` at `CC:650-663`. Keys `resolution_width`/`_height`, `fps`, `raw_bit_depth`, `clear_hdr`, `fps_ramp`, `fps_ramp_keep_exposure` (`CC:667-672`, `:715-718`, `:735-738`).
- Writer `writeCaptureSettings` `CC:774-818` (e.g. `fps_ramp` `:809`).
- Async persister `CC:833-…`. `persistSettingsLocked` `CC:10071-10078`.

**Where a new setting would go.** Follow the T31 pattern of `fpsRampEnabled`: `Types:130-133` → JSON `CC:189`, `App:204-205`, `App:7929` → reader `CC:735` → writer `CC:809` → setter like `setFpsRamp` (`CC:9458`, `Hdr:78`) → command like `set_fps_ramp` (`App:9788`) → `help` (`App:9537`). CONFIRMED pattern.

**Where a code array (no UI) would go.** A `static constexpr` table in `CC`'s anonymous namespace. It belongs next to `tableMaximumFpsForResolution` (`CC:2736`) or next to the IMX477/IMX577 mode arrays in `sensorModeCandidatesForRequestedResolution` (`CC:2399-2457`, the existing style for per-sensor mode lists). PROBABLE: best fit.

**Persistence trap.** Commit-true setters run during a take. Example: `setIso` → `applySettingsLocked(next, false)` with commit defaulting to true (`CC:8917`, `Hdr:116`) → `persistSettingsLocked`. That writes the *current* `settings_` into the profile. A mid-ladder resolution would be persisted the same way T31's mid-ramp fps is. `restoreFpsAfterRampLocked` re-persists only the fps (`CC:8894-8899`). CONFIRMED path.

---

## (g) The three selectable-fps arrays and their filters

**WebUI.** CONFIRMED:
- `const fpsPresets = [24, 25, 30, 35, 40, 45, 50, 60, 70 … 240, 280]` at `Web:4039`.
- `availableFpsOptionsForSnapshot` `Web:4992-5019`:
  - IMX585 presets are cut to ≤ 60 (`Web:4994-4996`).
  - Then ≤ `maximumSupportedFpsForSnapshot` (`Web:4928-4990`; IMX585 4K = 30 at `:4976-4978`, crops and 1080 = 60 at `:4979-4987`).
  - Then the H.264 cap (`Web:4998-5000`) and the lossless caps (IMX585 lossless 30, `Web:5013-5018`).
- Consumer: the fps button row `Web:9398`, `:9910-9916`. A click sends a plain `set_fps`, which is a jump, not a ramp.

**Hardware (dial, buttons).** CONFIRMED:
- `availablePcfFpsOptions` `App:1163-1180`. Presets `{24, 25, 30, 50, 60}` for IMX585 (`App:1167-1170`), filtered by `maximumPcfFpsForSettings` (`App:1089-1160`).
- IMX585 4K = 30 at `:1150-1153`. 1080 = 60 at `:1155-1157`. The 3840 and 1920 crops fall through to the default 60 at `:1160`. Clear HDR is not looked at.

**Touch UI.** UNCONFIRMED, from the KB map:
- `fpsOptions` `QML:498`, `availableFpsOptions` `QML:802`, `maximumSupportedFpsForResolution` `QML:733` (KB `ui-map.md:148`, `:151`).
- `ensureValidFpsSelection` (`QML:1549`) and `ensureValidResolutionSelection` (`QML:1366`) **send `set_fps` / `set_resolution` on their own when the sensor, the resolution or the format changes** (KB `ui-map.md:469`, `:578`).

**Lowest fps.** None of the arrays goes below 24. CONFIRMED (`Web:4039`, `App:1170`). Core itself takes any fps > 0 (`CC:8822`). "From the lowest possible fps" today means `set_fps`/`ramp_fps` by command, or new low entries in these arrays.

**How the UIs learn the current mode.** CONFIRMED for Core:
- Only through `resolution`/`width`/`height`/`raw_bit_depth`/`clear_hdr`/`fps` in the three JSON writers (f).
- The touch UI parses the `settings` event (`ApertarControlBridge::applyCoreMessage :1257`, KB `ui-map.md:505`, UNCONFIRMED).
- No field names the sensor mode, its probed ceiling, a ladder rung or a clip index.
- `list_sensor_modes` is on demand only.

**With a ladder,** the filters should cap at the ladder's top rung, not at the current mode. Otherwise the 4K row offers 24/25/30 and never 50. PROBABLE.

---

## (h) Existing auto-mode logic in Core

`grep -i "dynamic|ladder|substitut|auto_mode|fallback.*mode"` over `CC`, `App` and `Web` finds no mode ladder or dynamic resolution. CONFIRMED. The nearest things:
- IMX477 and IMX577 candidate fallbacks: larger crop first, then smaller, then other widths (`CC:2399-2457`). They are used only to get *a* configuration accepted, at start. CONFIRMED.
- The libcamera-chosen sensor config retry for IMX585 3840 crops (`CC:6681-6684`, `:6702`). CONFIRMED.
- H.264 uses a fixed capture size per sensor (`processedVideoCaptureResolutionForSensor`, `CC:1991-1996`). CONFIRMED.
- The ramp stepper's "mode's limit" stop (`App:9208-9215`) is the only place that reacts to a ceiling during a take. CONFIRMED.

---

## What a ladder implementation must touch

Ordered from the first change to the last. Each item names its file:line.

1. **Ceilings first (ladder A needs only this).**
   - `tableMaximumFpsForResolution` `CC:2780` (4K SDR to the probed 60).
   - `maximumPcfFpsForSettings` `App:1151-1154`.
   - `maximumSupportedFpsForSnapshot` `Web:4976-4978`.
   - QML `maximumSupportedFpsForResolution` `:733` (KB).
2. **Ladder table** (code array). A new `constexpr` list in `CC` beside `CC:2736` or `CC:2399`. Each rung is {resolution, rawBitDepth, clearHdr, up-threshold fps}, plus a hysteresis value. Check each rung at start against `validateResolution` `CC:10098`, `supportedRawBitDepthForSensor` `CC:2803`, `sanitizeSettingsForSensor` `CC:2830` and the probe `probedMaximumFps` `CC:2723`.
3. **On/off and state.** A flag beside `fpsRampEnabled` (`Types:130-133`). Add it to the JSON at `CC:189`, `App:204-205`, `App:7929`, the persister at `CC:735-738`, `:809-810`, a setter like `setFpsRamp` `CC:9458` / `Hdr:78`, a command beside `App:9788`, and `help` `App:9537`. Add new state fields to the same three JSON writers (rung, clip index in take).
4. **Decision point.** `CameraController::setFps` `CC:8799-8844`, at the clamp `CC:8830-8836`. When the requested fps is above the current rung's ceiling (or crosses a threshold either way), choose the target rung *directly*, even across several rungs: a WebUI click can jump 24 → 50 (`Web:9910-9916`).
5. **New controller step** (e.g. `switchRungInTakeLocked`). It bypasses the user gates (`CC:8772`, `:9251`, `:9287`). It must have a recovery path, unlike `applySettingsLocked` with `commit = false` (`CC:10039` vs `:10054`).
6. **New session split** that does not use `stop()` as it is (`CC:6057-6120`):
   - close the clip: the raw parts of `stopRecording` `CC:6322-6358` (`recorder_.stop`, per-clip ramp log)
   - camera stop / configure / start: `configureAndStart` `CC:6656-7076`, keeping the CameraManager for SDR↔SDR; a full `reconfigure` `CC:6122` only for a WDR change
   - open the next clip: the raw parts of `startRecording` `CC:6174-6316`
7. **Clip folder naming.** `allocateClipFolder` `CC:3854-3896`, `reserveClipFolder` `CC:3569-3579`. Sub-clip names come from the take's first name. `startAtFolder` `CC:3445-3565` (resets `frameIndex_` `:3451`, sets `clipName_` `:3486`).
8. **Base fps across clips.** `recordingBaseFps_` set at `CC:6193`, cleared at `CC:8151`. `stampFpsRampEvents` `CC:8075-8085`.
9. **Timecode continuity.** RecRun in `CdngEncoder.cpp:333-349` (needs a take frame offset in `Metadata`). FreeRun anchor `CC:7756`. MLV INFO `MlvEncoder.cpp:1115-1119`. WAV `AudioRecordingSession.cpp:792-819`.
10. **Ramp log.** `writeFpsRampLog` `CC:8138-8192`. Split per clip, add a switch line. `noteFpsChange` `CC:8047` for the grace.
11. **Drop accounting and cadence gate.** `trackRecordingCadence` `CC:8194-8247`, gate `CC:7470-7486`, `recordingGapEstimate_`/`dropWarning_`.
12. **Audio and gyro policy across the split.** `CC:6213-6246`, `:6345-6352`; `AudioRecordingSession::start/stop` (`src/audio/AudioRecordingSession.hpp:30-40`).
13. **Raw pool after an up-switch.** `reserveRawPool` `CC:4150-4161`, `recycleRawBuffer` `CC:4120-4140`.
14. **Stepper.** `startFpsRamp` `App:9174-9221`. The "mode's limit" stop (`App:9208-9215`) should only fire at the ladder's top. Each step blocks on the controller mutex during a switch.
15. **Restore at stop.** `restoreFpsAfterRampLocked` `CC:8887-8904` also restores the start rung and re-persists. Callers `CC:9815`, `:9840`, `:8708-8716`. Base captured at `CC:9556`.
16. **Selectable-fps filters.** `Web:4992-5019`, `App:1163-1180`, `QML:802` (KB). With the ladder on, cap at the top rung. The arrays themselves stay as Patrik's edit points: `Web:4039`, `App:1167-1170`, `QML:498`.

## Risks seen in the code

1. **A mid-take reconfigure silently ends the take.** `stop()` stops every recorder (`CC:6078-6083`) and closes the frame gate (`CC:6060`). The controller still says Recording. No ramp log is written. CONFIRMED.
2. **No recovery for take-scoped reconfigures.** With `commit = false`, a failed switch puts the camera in Error (`CC:10039-10054`). CONFIRMED.
3. **Reconfigure rebuilds the CameraManager.** Twice with a log preview profile (`CC:5917-5918`, `:5986-6004`). A Clear HDR change adds WDR retries and a tuning change (`CC:5680-5689`, `:5895-5899`). The cost is unmeasured in Core and probably above Cinemate's 186 ms. PROBABLE.
4. **`recorder_.stop()` drains the queue synchronously under the controller mutex** (`CC:3583-3605`). On exFAT under load this can be hundreds of ms (it logs above 0.2 s, `CC:3683-3689`). PROBABLE.
5. **The base fps is lost at the clip boundary.** `writeFpsRampLog` clears `recordingBaseFps_` (`CC:8151`). A second clip would take the current fps as its base. CONFIRMED.
6. **RecRun timecode restarts at zero in every new folder** (`CdngEncoder.cpp:333-336`). FreeRun re-anchors at index 0 (`CC:7756`). CONFIRMED.
7. **The switch gap counts as dropped frames** and sets the drop warning (`CC:8230-8237`). CONFIRMED path; the gap size is UNCONFIRMED.
8. **Lossless cDNG on IMX585 is capped at 30 at every size** (`CC:2574-2579`). Ladders above 30 only work in uncompressed cDNG, MLV or lossy DNG. CONFIRMED.
9. **Four copies of the ceiling table** (`CC:2777-2786`, `App:1151-1160`, `Web:4976-4987`, QML `:733`). Raising one leaves the UI offering less or more than Core allows. CONFIRMED for three, KB for QML.
10. **The touch UI may fight a Core-driven switch.** `ensureValidFpsSelection` / `ensureValidResolutionSelection` send `set_fps` / `set_resolution` when the resolution changes (KB `ui-map.md:469`, `:578`). A resolution change mid-take could make the UI send a `set_fps`, which a ramp take accepts as a step. UNCONFIRMED (needs the UI source).
11. **No IMX585 fallback candidate.** A rejected rung fails the switch (`CC:2440-2441`). The crop auto-config retry could pick another sensor mode silently (`CC:6681-6684`). PROBABLE.
12. **fps is silently clamped at configure.** Switching to a rung with a lower ceiling clamps fps (`CC:6945-6951`) with no event of its own. CONFIRMED.
13. **Persistence pollution.** Any commit-true setter during the take writes the current rung into the profile (`CC:10071-10078`). The T31 restore only fixes fps (`CC:8887-8904`). CONFIRMED.
14. **Raw copy pool after an up-switch.** The smaller pooled buffers never fit (`CC:3781-3782`, `:4156`). The first frames allocate on the copy worker. PROBABLE.
15. **MLV cannot change mode in one file.** `RAWI` and `MLVI` are written once at open (`MlvEncoder.cpp:1081-1093`, `:1180-1195`). CONFIRMED.
16. **The probe must have run.** With `APERTAR_SENSOR_PROBE=0`, `sensorLimitKnown` is false and 4K SDR stays 30 even after the table change (`CC:2799`, `:5843`). CONFIRMED.
17. **Buffer memory at a Clear HDR rung.** 8 (+2 on exFAT) cached 16.9 MB raw buffers (`CC:1063-1067`, `:7010-7014`), plus the 6-buffer copy pool. A ladder that switches into Clear HDR mid-take allocates this during the gap. PROBABLE.
18. **No preset array below 24 fps** (`Web:4039`, `App:1170`). "The lowest possible fps" is reachable only by command. CONFIRMED.
