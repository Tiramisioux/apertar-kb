# Verify: other edges (i1-i6, f1-f3), TOURS, "Try 3 and 6" card

Refs: official = upstream-1.6.0 worktrees, fork = Apertar-Core 01f170c, Apertar-UI 7ea9afc.

## Correct (checked in both modes)
- i1 publishPreviewFrame(libcamera::Request*) CC (up:7228, fork:10063); i5; i4 events and fds (App up:10891-10940, fork:14949-14998; SCM_RIGHTS ControlServer.cpp up:66, fork:69; eglCreateImageKHR failed UI PreviewWindowRenderer.cpp:1771 both)
- i6 /preview.mjpeg (App up:7109, fork:8373), q75, 640x360 (App up:60-63, fork:84-87), WebControlPage.cpp img src with ?stream=
- i3 clip folder + 9-digit frame name (frameFilename, CC up:3683, fork:5217); id from sensor timestamp (nextFrameIndex)
- f1 SettingsBridge setZebraEnabled writes zebraEnabled, no socket command (grep set_zebra in UI: 0 hits both)
- f2 set_zebra_enabled -> handleUiToggle -> updateSharedUiGeneralSettings (QtIniLock, [General], atomicWrite; up App:9495, fork:13358); no event emitted, both modes
- f3 QFileSystemWatcher::fileChanged -> pollExternalSettings (SettingsBridge.cpp up:413, fork:418)
- Tours: all step ids exist; touch, web, knob order matches flows.md A1/A5 and fork code (dispatch("set_iso") fork App:10166)
- Card: GET /api/state (App up:7154, fork:8428), top-level "iso": number once in buildWebStateJson (up:7861, fork:9485); POST /api/command -> handleWebCommand -> parseControlCommand (key "cmd", string values OK, number() uses stod) -> set_iso (up:9242, fork:12968). curl has no Origin, so allowedBrowserOrigin passes. Rebuild hint matches both READMEs.

## Discrepancies: see StructuredOutput (4, all imprecise)

## Recheck

Second checker, re-derived from code in both trees (fork = Apertar-Core@cinemate-port 01f170c, official = wt/core-upstream@upstream-1.6.0).

| # | Item | Verdict | Why |
| --- | --- | --- | --- |
| 1 | E.i2.what | stands (fork) | Fork: `recordRawFrame` fills a `PendingCopy` and calls `recorder_.enqueueCopy(std::move(copy))` (CC:9505@cinemate-port); `enqueueCopy` is "Never blocks, never copies" (CC:5066). `copyLoop` does `acquireRawBuffer` + `memcpy`, then `releaseHeldRequest(copy.request)` (CC:5105-5114@cinemate-port), then queues for writing. Official: copy happens in the completion callback, `recorder_.acquireRawBuffer(rawSize)` + `copyRawBytes(...)` (CC:6932-6933@upstream-1.6.0). Arrow is fork:true, so the fork text should name the copy worker. Current text kept for official via up. |
| 2 | E.i3.what | stands (fork) | Fork: `nextFrameIndex(int64_t timestampUs, bool countOnly = false)` (CC:4679@cinemate-port); `timeIndex` is 0 when `countOnly`; caller passes `/*countOnly=*/settings_.fpsSpeedRamp` (CC:9455). During a speed ramp frames are numbered 0,1,2... with no gap. Official: `nextFrameIndex(int64_t timestampUs)` only (CC:3518@upstream-1.6.0), statement true. |
| 3 | TOURS.frame.steps | dropped | `highlight()` (index.html:569-571) lights an edge's `f` and `t` nodes whenever an edge is shown. Step i5 lights SCREEN; step i6 lights PUB and BROWSEROUT. Both destinations are shown. Adding node steps is a style choice, not an error. |
| 4 | TOURS.zebra.steps | dropped | Same mechanism: step c4 lights BROWSER. The route is right in both trees: WebUI `sendCommand({ cmd: "set_zebra_enabled", ... })` (WCP:10087@upstream-1.6.0; fork WCP has it too), same POST /api/command, then f2/f3. c4/c5 show ISO code by design as the shared route example; no statement in the map is false. Style only. |

## Final discrepancies

### 1. E.i2.what (mode: fork, imprecise)

- Map says: `what:"While recording, each RAW frame is copied into a recycled buffer and queued for the writer threads."` (no up override for what)
- Code says: `/home/user/Apertar-Core/src/camera/CameraController.cpp:9505@cinemate-port` `if (!recorder_.enqueueCopy(std::move(copy)))`; `:5066` "Never blocks, never copies."; `:5105` `std::vector<uint8_t> rawCopy = acquireRawBuffer(copy.size);` then `:5114` `releaseHeldRequest(copy.request);`. Official: `/home/user/wt/core-upstream/src/camera/CameraController.cpp:6932-6933@upstream-1.6.0` `acquireRawBuffer(rawSize)` + `copyRawBytes(...)` inside recordRawFrame.
- Corrected: `what:"While recording, each RAW frame is handed to a copy worker, which copies it into a recycled buffer, gives the camera buffer back and queues the copy for the writer threads."` and extend the existing up to `up:{code:"recordRawFrame(request, whiteBalance);",what:"While recording, each RAW frame is copied into a recycled buffer and queued for the writer threads."}`

### 2. E.i3.what (mode: fork, imprecise)

- Map says: `what:"The frame number comes from the sensor timestamp, so a dropped frame leaves a gap in the numbering."`
- Code says: `/home/user/Apertar-Core/src/camera/CameraController.cpp:4679@cinemate-port` `uint64_t nextFrameIndex(int64_t timestampUs, bool countOnly = false)`; `:9455` `recorder_.nextFrameIndex(timestampUs, /*countOnly=*/settings_.fpsSpeedRamp);`. Official `/home/user/wt/core-upstream/src/camera/CameraController.cpp:3518@upstream-1.6.0` `uint64_t nextFrameIndex(int64_t timestampUs)`.
- Corrected: `what:"The frame number comes from the sensor timestamp, so a dropped frame leaves a gap in the numbering. During an fps speed ramp frames are counted instead."` plus `up:{what:"The frame number comes from the sensor timestamp, so a dropped frame leaves a gap in the numbering."}`
