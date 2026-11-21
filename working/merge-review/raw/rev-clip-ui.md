# Review: clip-split touch-UI commits (3ebbd23 .. 371e1eb, 20 commits after 7ea9afc)

Tree: /home/user/wt/ui-clip (clip-split). Yardstick: apertar-conventions.md (UIC-, QML-). Read-only. Judged: the 20 clip-split commits only, not U4-U13.

## Summary

| Question | Answer | Label |
| --- | --- | --- |
| Does a stock camera pay for a second preview client? | No. `syncCam1Preview` (src/main.cpp:~403) connects `apertarPreviewBridge1` only when `cam1Present` or the test flag. With no cam1 the client is disconnected: no socket, no reconnect timer (`disconnectFromCore` stops it, ApertarPreviewSocketClient.cpp:106-110) | confirmed |
| Does the hidden cam1 item cost GPU? | A second `PreviewWindowRenderer` object is built in `ensureWindow` (ExternalMonitorManager.cpp:242-248). `render()` returns before `initialize()` while the item is hidden (PreviewWindowRenderer.cpp:2458-2459), so no shader, texture or import. Cost: one object and its signal links | confirmed |
| Do the info overlay, aids, recording frame look as 1.6.0 on a stock camera? | Yes by reading: every new term is gated by `cam1Present` / `layoutKind` / `wipeActive`, all false without cam1 (EMW:214-300). Main preview item is full surface as before (`mainPaneWidth = monitorSurface.width`) | confirmed (desk), unconfirmed on a screen |
| Stock-visible changes | Media card rows, a fourth clip-name preset, renderer import eviction, hidden-item render skip. See CLIP-U-6, CLIP-U-11 | confirmed |
| Worst problems | Wipe edge vs scissor in portrait HDMI, 250 lines of raw cam1 JSON formatting in QML, off-pattern Settings rows, Pi 4 GPU cost of two full draws (unmeasured), merge-rate logic in main.cpp with a stale `record_cameras` bug | |

No High finding. Counts: High 0, Medium 5, Low 7.

## Final findings

### CLIP-U-1. Wipe cut and wipe line disagree on a rotated HDMI monitor

- Category: bug (renderer, bindings)
- Severity: Medium. Label: probable (read, not run; needs an HDMI set to Portrait with a cam1)
- Where: src/PreviewWindowRenderer.cpp:2323-2343@clip-split (scissor); qml/ExternalMonitorWindow.qml:806-811 (`monitorSurface rotation`), ~line 905 (wipe edge `Rectangle`)@clip-split
- What it does: the scissor is set in window pixels from the item's scene rect (`mapRectToScene`, `previewRectInPixels`, PreviewWindowRenderer.cpp:1902-1916): "left fraction" is the window's left edge. The white edge line is a QML item inside `monitorSurface`, which is rotated by `externalMonitorRotation` (+-90 in Portrait). With a +-90 rotation the picture is cut along the window's x axis, the line is drawn along the surface's x axis, which is the window's y axis. Vertical wipe has the same split. With 0/180 they agree: the fit rect is the same in both places.
- The Apertar way: the HDMI window derives geometry from the surface and passes display transforms to the renderer through item properties (`displayRotation`); nothing in the renderer assumes an unrotated window. Precedent: `displayRotation` handled per shader quad, PreviewWindowRenderer.cpp:2250-2285.
- Why it matters: portrait HDMI is a supported setting; wipe would cut one way and show its edge another way.
- Fix: map the fractions through `displayRotation` in `renderDirectToWindow` (swap left/top and flip for 90/-90/180), or take the cut as a rect from QML. Test with Portrait Left/Right.
- Effort: S

### CLIP-U-2. About 250 lines of cam1 parsing and formatting in the HDMI window QML

- Category: mismatch (UIC-4, UIC-11, QML-8, QML-10) and slop
- Severity: Medium. Label: confirmed
- Where: qml/ExternalMonitorWindow.qml:214-470 (`cam1S`, `cam1ResolutionValue`, `cam1RecordingFormat`, `cam1PreviewAspectResolution`, `cam1IsoInUse`, `cam1WbInUse`, `cam1IsoOnAddedCap`, `cam1ShutterAngle()`, `cam1ModeText()`, `differingValues()`, `cam1Tied()`) and src/main.cpp:322-350 (`syncMediaRates`) and src/ApertarControlBridge.cpp:1523-1537 (`applyCam1State`)@clip-split
- What it does: `ApertarControlBridge::cam1Settings` is a raw `QVariantMap`; QML reads `iso_auto`, `shutter_us`, `wb_kelvin`, `raw_bit_depth` and rebuilds display strings, shutter angle, the 1928x1090 -> 1920x1080 fold, recording-format naming, and the Clear HDR cap test. The same width/height/resolution parse runs three times: in `applyCam1State`, in the `main.cpp` lambda, in QML. `cam1Settings` UI.conf ties are a comma string split in QML (`cam1Tied`).
- The Apertar way: Core settings reach QML as display strings; the bridge owns `parse*Value` / `format*Value` pairs (UIC-11: ACB hpp 211-243 @upstream). QML formats no raw Core numbers. The HDMI window reads bridge properties (`apertarControlBridge.shutterAngle`, `.iso`, `.whiteBalance`) with no JSON knowledge.
- Why it matters: one place to change when Core renames a key; the original developer must read 250 lines of derived-value QML to find what CAM1 shows. Two sensors with different key names would break silently.
- Fix: parse once in `applyCam1State` into display-string properties (`cam1Iso`, `cam1ShutterAngle`, `cam1Wb`, `cam1Fps`, `cam1ModeText`, `cam1ResolutionValue`); expose ties as a `QStringList` or per-control bools from SettingsBridge. EMW keeps only layout and pane logic. `m_cam1Resolution` is then used, today it is only logged (ApertarControlBridge.cpp:1534-1536).
- Effort: M

### CLIP-U-3. Split Long Takes and Merge Split Clips rows ignore the page's text and size conventions

- Category: mismatch (QML-13, QML-16, QML-17, QML-8, QML-25, QML-3) and slop
- Severity: Medium. Label: confirmed
- Where: qml/SettingsPage.qml:5396-5523@clip-split (new rows inside `systemMediaComponent`, opened at :5220)
- What it does: the new `Text` items use `font.pixelSize: 14 / 12` with no layout-flag ternary, no `font.family`, no `renderType: Text.NativeRendering`, colours `#9aa5b1`, `#d7d9de`, `#73ffffff` (off palette). The neighbouring text in the same card uses `interRegular`, `root.largeLandscapeLayout ? 19 : (root.standardLandscapeLayout ? 14 : 13)`, `#8cffffff`, NativeRendering (SettingsPage.qml:5340-5360). On/Off is two `ActionTile`s with `tone` as a radio pair; `TogglePill` is the page's boolean control (SettingsPage.qml:2562, 3801, 5164). `applyFramesPerFolder` / `applyClipMerge` are `void`; failure sets `lastError` and QML never shows it (QML-8 pattern: `if (bridge && !bridge.apply...)` then error popup). Nothing disables Split Long Takes during a take (QML-25); whether Core refuses it is unconfirmed (`set_frames_per_folder` in Core). Labels carry env var names ("set by APERTAR_CDNG_FRAMES_PER_FOLDER"); the merge progress Repeater uses `Repeater { model: 2 }` with an `index === 0` switch.
- The Apertar way: sizes from layout flags (QML-13), Inter fonts, NativeRendering, palette hex (QML-16/17), a `TogglePill` for on/off, bool-returning invokables with an error popup (UIC-9, QML-8), descriptions short (QML-29).
- Why it matters: on the 720x720 screen these rows will not scale with the others; text without NativeRendering renders differently from the rest of the card.
- Fix: copy the card's token set; use `TogglePill` for merge; make both invokables return `bool` and show `lastError`; disable the split field while `recording`; move the env-var note into the description line; render the two merge progress bars as two explicit items.
- Effort: M

### CLIP-U-4. Pi 4 GPU and memory cost of two full draws is unmeasured

- Category: Pi-model risk
- Severity: Medium. Label: unconfirmed (needs a Pi 4 with two sensors: `perf`/`gpu_busy`, `dmesg`, and drops over a 3 minute take in Both, PiP, stack)
- Where: src/PreviewWindowRenderer.cpp:2323-2430 (blend + scissor), src/ExternalMonitorManager.cpp:242-248, qml/ExternalMonitorWindow.qml:827-903 (two `CameraPreviewItem`s)@clip-split
- What it does: with cam1 present each HDMI frame draws two external-OES textures; in stack, a blend over a full-screen first draw (every pixel written twice); aids (zebra, peaking, false colour) in a wipe run the process shader on one item and the passthrough on the other. Each renderer owns its programs and import map (up to 16 buffers x 3 fds each, per the eviction comment). Pi 4 has no headroom note in the code or the design for this path.
- The Apertar way: Pi-model limits are stated where they bind (platform rules PLT; Pi 4 vs 5 paths). Nothing here says what runs on Pi 4.
- Why it matters: the owner's rig is dual-sensor on HDMI; a Pi 4 may drop preview frames or recording frames when the GPU is busy.
- Fix: measure first; if it hurts, offer Both/PiP only on Pi 5, or draw the second item at a lower rate. State the outcome in the design doc.
- Effort: M (measure) / L (if rework)

### CLIP-U-5. Record-rate logic sits in main.cpp and a stale `record_cameras` zeroes REMAINING

- Category: bug and mismatch (UIC-1, UIC-4)
- Severity: Medium. Label: confirmed (read); stale case needs cam1 to vanish while the last `record_cameras` was `cam1` or `none`
- Where: src/main.cpp:322-364 (`syncMediaRates`, 5 `connect`s); src/ApertarControlBridge.cpp:1474-1483, 1560-1575 (`applyCam1State` / `clearCam1State`)@clip-split; src/MediaStatusBridge.cpp:388-401
- What it does: a 30-line lambda computes the cam1 size scale from `cam1Settings`, `resolution()`, `rawBitDepth()` and hands four numbers to `MediaStatusBridge::setCameraRates`. `clearCam1State` clears the cam1 fields but not `m_recordCameras`. After cam1 disappears with `m_recordCameras == "cam1"` (or `"none"`), `cam0InTake` is false in the lambda and `recalculateRemaining` adds no cam0 rate: REMAINING becomes 0 on a one-sensor rig. Core publishes `record_cameras` only with cam1 present (ApertarCoreApp.cpp:2312@work/improve), so it never overwrites the stale value.
- The Apertar way: `main()` wires with `connect` and setters (UIC-1, main.cpp:374-396@upstream); a computation belongs in the bridge that owns the number (`MediaStatusBridge::recalculateRemaining`, fed by `setFps` from QML/bridge).
- Why it matters: stock behaviour after a cam1 unplug; the dual rate also sits where the original developer will not look.
- Fix: reset `m_recordCameras` in `clearCam1State` (emit `recordCamerasChanged`); move the scale computation into `ApertarControlBridge` (one `cam1SizeScale` property) so `main()` keeps one connect.
- Effort: S

### CLIP-U-6. Renderer changes also alter the stock cam0 path

- Category: stock-behaviour change
- Severity: Low. Label: confirmed (read), probable on effect
- Where: src/PreviewWindowRenderer.cpp:1673-1676, 1808-1836 (stale import eviction), :2457-2459 (`if (!m_item->isVisible()) return;`), :421-422 (reset on bridge change)@clip-split
- What it does: (a) buffers not used for 64 ticks are destroyed on the next new import for every renderer including the stock one; the loop copies the body of `cleanupImportedBuffers` (:1520-1545) and calls `eglGetProcAddress` per entry. The 64 limit assumes Core's preview pool is under 64 buffers (unconfirmed; the comment says 16). (b) A hidden item now skips render: the stock main item sits under `monitorSurface visible: !standby`, so in standby the renderer no longer redraws its last frame; `CameraPreviewItem` has no `visibleChanged` hook (grep: none), so redraw on show waits for the next frame or property change.
- The Apertar way: leak fixes are a separate, described commit; a changed stock path is named as such. Shared cleanup is one function.
- Why it matters: (a) is a real fd leak fix, probably wanted, but sits inside a dual-sensor series; (b) could leave one stale or black frame on wake.
- Fix: split (a) into its own commit with a helper `destroyImported(entry)` used by both loops; add `connect` or `itemChange` for visibility so `update()` runs on show.
- Effort: S

### CLIP-U-7. Test scaffolding left in the product

- Category: slop
- Severity: Low. Label: confirmed
- Where: src/main.cpp:293-295, 399-401, 438-439; src/main.cpp:148 (`cam1InsetTest=false` in `runMonitorOnly`); qml/ExternalMonitorWindow.qml:216-228, 735-742@clip-split
- What it does: `APERTAR_UI_CAM1_INSET` forces a `PiP Cam 0` view and connects the cam1 client to a symlink of cam0's socket for the bench test (commit ec459bd). It is a context property in both processes, read in four QML places.
- The Apertar way: bench knobs are env vars read once in Core with a named place (R8); no UI context property for a test. Upstream has no such flag.
- Why it matters: one more mode to reason about in every `cam1Wanted` expression.
- Fix: remove once T65/T69 bench checks pass; or keep as one documented env var read in the client, not in QML.
- Effort: S

### CLIP-U-8. Socket path literals added at every call site; cam1 path has no override

- Category: mismatch (UIC-14) and slop
- Severity: Low. Label: confirmed
- Where: src/main.cpp:391, 399, 404 (`"/tmp/apertar-core-cam1.sock"`), :229; qml/Main.qml:207; qml/ExternalMonitorWindow.qml:735-742@clip-split
- What it does: every `connectToCore()` of cam0 became `connectToCore("/tmp/apertar-core.sock")`, which is the existing default argument (ApertarPreviewSocketClient.hpp:32). The cam1 path is a literal at 2 sites with no `APERTAR_*` override. The standby connect/disconnect logic is now in `main.cpp` and in EMW for both clients.
- The Apertar way: app-owned paths are literals with an `APERTAR_*` env override beside them (UIC-14, ACB:1032 @upstream); unchanged call sites stay unchanged.
- Why it matters: noise in stock code (Main.qml, runMonitorOnly); a second path with no override.
- Fix: revert the cam0 call edits; give the client or ACB one `cam1SocketPath()` with `APERTAR_CORE_CAM1_SOCKET`.
- Effort: S

### CLIP-U-9. Internal ticket and design codes in comments

- Category: slop (QML-20, STY)
- Severity: Low. Label: confirmed
- Where: qml/ExternalMonitorWindow.qml:214, 220, 276, 360, 412, 541, 559, 596, 1965; qml/SettingsPage.qml:5470; qml/StatusChip.qml:122; src/PreviewWindowRenderer.cpp:2323; src/SettingsBridge.cpp:649; src/SettingsBridge.hpp:49; src/ApertarControlBridge.hpp:60, 501; src/ApertarControlBridge.cpp:2811, 2912; src/ApertarPreviewSocketClient.cpp:55, .hpp:22; src/CameraPreviewItem.hpp:31; src/ExternalMonitorManager.hpp:43; src/main.cpp:293, 322@clip-split
- What it does: comments cite T65, T66, T69, A5, P11, U-new6, "v2.5 A2", "section 5.2", "KB trap 7", "KB clip-merge-progress-plan.md", and "the User's choice".
- The Apertar way: short why-lines, no ticket numbers (QML-20 `CPg:1961-1963`; grep of T-numbers in upstream QML = 0).
- Why it matters: meaningless to the original developer; the KB is not in the repo.
- Fix: rewrite each to the reason in plain words.
- Effort: S

### CLIP-U-10. New state parsing idioms in `applyBufferState` and a void/int invokable pair

- Category: mismatch (UIC-4, UIC-9, UIC-10) and slop
- Severity: Low. Label: confirmed
- Where: src/ApertarControlBridge.cpp:2912-2978, 704-733@clip-split; src/ApertarControlBridge.cpp:1:3 (`#include <QDebug>`)
- What it does: 65 lines add four local lambdas (`flag`, `number`, `takeInt`, `takeText`) to `applyBufferState`, with a `progressChanged` flag; upstream does inline `if (state.contains(k)) { compare; assign; emit }`. `applyFramesPerFolder(int)` and `applyClipMerge(bool)` are `void`; `applyBufferMode` next to them is also `void` (a precedent). `applyFramesPerFolder` error text is "Invalid frames per folder." (no action). `m_cam1Resolution` is stored only for a `qInfo` line.
- The Apertar way: inline compare/assign/emit (UIC-4, ACB:1263-1312 @upstream), full-sentence errors (UIC-9).
- Why it matters: the lambdas are the only ones in the file; the next editor sees two styles.
- Fix: inline the compares or move to one small helper used by every field; drop `m_cam1Resolution` unless used.
- Effort: S

### CLIP-U-11. Changes a stock camera can see

- Category: stock-behaviour change (decision, not a defect)
- Severity: Low. Label: confirmed
- Where: qml/SettingsPage.qml:5396-5523; qml/ClipNameCard.qml:23-27; qml/StatusChip.qml:122-145; qml/CameraPage.qml:2709-2714@clip-split
- What it does: the Media card gets Split Long Takes and Merge Split Clips rows whenever Core sends `frames_per_folder` / `clip_merge_enabled` (the port Core always does); the Clip Name card gets a fourth preset "Standard" with `{tc}`, a copy of Core's `kStandardTemplate` (a string that must change with Core); the READY pill gets a grey merge fill while a merge runs.
- The Apertar way: a stock camera looks as 1.6.0 unless Patrik chose otherwise.
- Why it matters: these are the clip-split feature itself, so they are intended; the owner should confirm them as stock-visible. The preset template is a second copy of a Core constant.
- Fix: confirm in the merge notes; fetch the standard template from Core's state instead of a literal.
- Effort: S

### CLIP-U-12. Merge fill and merge progress expression copied three times

- Category: slop (QML-11)
- Severity: Low. Label: confirmed
- Where: qml/StatusChip.qml:122-145; qml/ExternalMonitorWindow.qml:1795-1820; qml/CameraPage.qml:2709-2714; qml/SettingsPage.qml:5470-5480@clip-split
- What it does: the share-done expression (`clipMergeEnabled && AllClips > 0 && AllTotal > 0 && Paused === "" ? done/total : -1`) is written in CameraPage and EMW; the 25-line fill item is a copy in StatusChip and in the HDMI pill.
- The Apertar way: an element both screens show is a small standalone QML file used by both (QML-11, `DroppedFrameWarning.qml`); derived values live in the bridge (UIC-11).
- Why it matters: two copies drift.
- Fix: a bridge property `clipMergeProgress` (double, -1 = none); one `MergeFill.qml` in both QML lists (QML-14).
- Effort: S
