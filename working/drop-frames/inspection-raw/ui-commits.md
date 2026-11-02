# Apertar-UI `drop-frames` commits under review: keep, revert or park

Independent inspection, 2026-11-02, desk only (no Pi). Repo `/home/user/tiramisioux/apertar-ui`, branch
`origin/drop-frames` @ `c13b846`, `origin/main` @ `4415a55`. Status words as in the KB: **confirmed** (read in the
source, or measured on the Pi and agreed), **measured** (numbers are real, reading not agreed), **probable**
(inferred, reason given), **unconfirmed** (the measurement is named).

What was read: every diff of the six commits (`git show`), the whole of `DrmPreviewPlane.cpp/.hpp`, the renderer's
`render()` dispatch, `main.cpp`'s two renderer set-ups, the earlier branch commits `841d0ed`..`41ff827`, Core
`adac040` (`ApertarCoreApp.cpp` `runBufferEvents`, `CameraController.cpp` `recording_health`), the night report
(sections 1-8), the take table, the hardware log of 2026-10-30/31 and 2026-11-01, and the handoff.

## 1. Verdict in one table

| Commit | What it is | Lines | Default path (switch off) | Measured on the Pi | Recommendation |
| --- | --- | --- | --- | --- | --- |
| `68e1a41` | dropped-frames chip shows the count | +29/-5 | one `contains()` + int compare per `buffer` event (<= 4/s) and per state reply; QML text changes only when the count changes | works: 18 = 18 (hardware log 2026-11-01, "numbers work") | **keep** |
| `c234d77` | `APERTAR_UI_PREVIEW_RECORDING_FPS` caps the preview while recording | +39 | one `if (m_recording && m_recordingFpsCap >= 0)` per preview frame, false when unset; a Qt signal connection | cap 0: 0 of 1498 (#30); cap 12: 2.88 % (#31), both under the `writer` regime | **keep as the test instrument**, never a default. It is the only way to remove the UI's preview work during a take without `SIGSTOP` (which hangs the record start at the audio open). B8 needs it |
| `a51c95e` | `APERTAR_PREVIEW_PEAKING=fast`, edge from an R8 import of the Y plane | +90/-1 | the shared fragment shader gains `uniform sampler2D uTexLuma` and a uniform branch; 4 extra GL calls per draw on both render paths (uniform x2, bind texture 0 to unit 5, unbind) | 8.83 % (#34) against 6-10 % baseline: no gain | **park** on `drop-count`, revert from `drop-frames` |
| `322d329` | `APERTAR_PREVIEW_DIRECT` forces the Pi 3 direct path on Pi 4/5 | +6 | one `envFlagEnabled()` at construction | a no-op on this rig (see 2.4) | **revert** |
| `4724007` | `APERTAR_PREVIEW_PEAKING=cpu`, CPU edge mask once per preview frame | +122/-8 | a 3-way uniform branch in the shader; `m_currentImported` bookkeeping on every import path; `<linux/dma-buf.h>` | 3.88 % (#44), UI CPU 19.6 % (12 % unchanged) | **park** on `drop-count`, revert from `drop-frames` |
| `c13b846` | `APERTAR_PREVIEW_PLANE`, picture on the DRM primary plane, Qt on an ARGB overlay | +805/-5 | two env checks (one before `QGuiApplication`, one in `render()`), one `glUniform1i` per draw, `vec4 mark` arithmetic inside the zebra/peaking branches and a final select per fragment; **new hard build requirement**: `pkg-config` + `libdrm` (`pkg_check_modules(... REQUIRED ...)`) | 0 (#46), then 1.82, 1.93, 3.13, 3.42 % (#47-#50); **7.22 % with the aids off** (#58) | **park** on `preview-plane`, revert from `drop-frames`, do not merge |

Reading of the measurements (confirmed from the take table): every A/B of 19:46-22:20 was taken under the `writer`
regime that drifted from 7 % to 18 % during the evening (night report section 3), and the unmodified GPU preview with
peaking and zebra on was clean under `sync` (#74 0/4505, #75 0/4509, #80 0/15025). None of the four preview-path
commits is needed for target 1. The plane series contradicts itself (aids off lost more than aids on), which is what a
drifting regime looks like, not a UI property.

Where this differs from night report 8.4: only on `c234d77` (8.4 says park; I say keep, because the re-test that 8.4
itself calls for in B8 needs it). Everything else agrees.

## 2. Each commit: what it does off, what it does on, risk

### 2.1 `68e1a41` dropped-frames chip shows the number (keep)

- Off/on: no switch; always active.
- Cost on the default path (confirmed): `src/ApertarControlBridge.cpp:1347` calls `applyRecordingDroppedFrames(message)`
  on every `buffer` event and `:1457` on every state reply; the function (`:2652-2662`) is one `contains()`, one
  `toInteger`, one `std::clamp`, one compare, and a signal only on change. Core sends the `buffer` event at most four
  times a second while a take runs (`Apertar-Core` `adac040:src/ApertarCoreApp.cpp:10951-11008`: 250 ms loop, event on a
  changed level or a changed dropped count) and a `recording_health` event on each new drop
  (`src/camera/CameraController.cpp:10353-10358`).
- UI work caused: `qml/DroppedFrameWarning.qml:7` width follows the label, `qml/CameraPage.qml:2715` moves the Controls
  chip by that width: a relayout and one redraw per changed count, i.e. one per dropped frame. At the night's 7 % that
  was about 1.75 redraws/s on top of about 29/s (measured, `QSG_RENDER_TIMING`, #35-#36); at 0 drops, nothing. A
  feedback loop in principle (a drop causes UI work), negligible in size (probable).
- New thread/timer/poll/dependency: none.
- Risk: nil. Confirmed on the rig.

### 2.2 `c234d77` `APERTAR_UI_PREVIEW_RECORDING_FPS` (keep as an instrument)

- Off (confirmed): `src/ApertarPreviewSocketClient.cpp:29` reads the variable once; unset leaves `m_recordingFpsCap = -1`,
  so the per-frame check at `:489` is one false `&&`. `src/main.cpp:351-352` connects `recordingChanged` to
  `setRecording()` (`:37-43`): one call per take start/stop.
- On: frames above the cap are closed and dropped before import (`:489-498`), in `handlePreviewFrame` only. Buffer
  registrations arrive as a separate `preview_buffer` event (Core `ApertarCoreApp.cpp:14504`) handled by
  `handlePreviewBuffer`, so a dropped frame cannot lose a slot registration (confirmed). The UI sends nothing back to
  Core for a frame (no ack/release message in `ApertarPreviewSocketClient.cpp`; Core has no such handler either), so a
  dropped frame cannot starve Core's preview pool (probable: by absence in both sources).
- Why keep: it is the one switch that turns the UI's whole preview pipeline (import, shader, redraw) off during a take
  while the UI keeps running, its state poll, audio meter and socket intact. `SIGSTOP` cannot do that (the record start
  hung at the audio open, night report section 6), and stopping the UI changes much more than the preview. The B8
  re-test under `sync` ("does the preview still cost anything?") is exactly `cap=0` vs unset, interleaved. It mirrors
  Core's existing `APERTAR_WEB_PREVIEW_RECORDING_FPS`, which fits the "extend an existing knob" rule.
- Risk: low. One operator-facing caveat: `cap=0` relies on `recordingChanged` reaching the socket client; if the UI
  misses the stop (socket drop), the preview stays frozen until the next state refresh (30 s poll,
  `ApertarControlBridge.cpp:18`). Acceptable for a test knob; a reason never to make it a default.

### 2.3 `a51c95e` `APERTAR_PREVIEW_PEAKING=fast` (park)

- Off (confirmed): `m_fastPeaking` false (`PreviewWindowRenderer.cpp:319-324`), no R8 import. But the shared fragment
  shader now declares `uniform sampler2D uTexLuma` and `uniform int uFastPeaking` and selects
  `uFastPeaking == 1 ? fastEdgeStrength(vUv) : edgeStrength(...)` per fragment when peaking is on; and both render
  paths execute `glUniform1i(m_lumaTexLoc, 5); glUniform1i(m_fastPeakingLoc, 0); glActiveTexture(GL_TEXTURE5);
  glBindTexture(GL_TEXTURE_2D, 0)` plus the unbind on every draw (`:2288-2292`, `:2532-2536`). If the GLSL compiler
  flattens the uniform branch, both edge functions run per fragment with peaking on; if it branches, the cost is a
  uniform test. Which one V3D does here is **unconfirmed** (`V3D_DEBUG=shaderdb` on the Pi prints the instruction
  count of the fragment shader; compare `41ff827` with `c13b846`). The planar (Pi 3) and CPU programs compile the same
  source with an unset sampler; harmless but untested.
- On: a second `EGLImage` per buffer (once per buffer, released with it, `:1924-1953`), three R8 fetches instead of
  three YUV-to-RGB samples. The edge is taken from raw Y, not from the converted luma the standard path uses, so with
  the exposure-reference (log) preview the result differs from the standard one (the commit says so).
- Measured: 8.83 % vs 6-10 % baseline under `writer` (#34): no gain even in the regime it was written for.
- Risk: low when off, but it touches the default shader for no measured benefit. Park on `drop-count` (that worktree is
  at `4724007`, which contains it), revert from `drop-frames`.

### 2.4 `322d329` `APERTAR_PREVIEW_DIRECT` (revert)

- Off: one `envFlagEnabled("APERTAR_PREVIEW_DIRECT")` in the constructor (`PreviewWindowRenderer.cpp:311-314`).
- On: sets `m_directWindowRendering`, which `render()` already honours (`:2745`). **On this rig it is a no-op**
  (confirmed): with `hdmi_external_only=true` the main window is hidden (`src/main.cpp:438-439`) and the HDMI picture
  is the external-monitor window, whose renderer is created with `renderer.setDirectWindowRendering(true)`
  (`src/main.cpp:179`) regardless of the switch. The take that "tested" it (#39, 5.42 %) measured spread.
- It would be a real change only for a touch-screen main window on a Pi 4/5, which nobody has run. Its journal line
  ("drawing straight into the window") is misleading on the HDMI-only rig. Six lines, nothing lost by reverting; if a
  touch-screen test ever needs it, it is one commit to cherry-pick from `drop-count`.

### 2.5 `4724007` `APERTAR_PREVIEW_PEAKING=cpu` (park)

- Off (confirmed): `m_cpuPeaking` false (`:319-326`), no `mmap`, no mask. The shader's select becomes three-way
  (`uFastPeaking == 2 ? texture2D(uTexLuma, vUv).r : ...`), same compile-time question as 2.3. `m_currentImported`
  (a pointer into `std::unordered_map` storage, stable across rehash, reset on erase and cleanup: `:1382`, `:1801`,
  `:1966`, `:2023`) is maintained on every import path: a few stores per frame.
- On (confirmed from the diff): once per preview frame on the render thread, `updateCpuEdgeMask()` (`:1309-1368`)
  reads the whole Y plane of a dma-buf through `mmap` between `DMA_BUF_IOCTL_SYNC` start/end, runs a 921,600-pixel
  loop, and uploads a 0.9 MB `GL_LUMINANCE` texture with `glTexSubImage2D`. Memory traffic per frame: about 0.9 MB read
  from (possibly uncached) dma-buf memory, 0.9 MB written, 0.9 MB read by the GPU upload, about 70 MB/s at 25 fps. It
  moves GPU work to the CPU rather than removing work: measured UI CPU 19.6 % against 12 % (hardware log 2026-11-01).
- Measured: 3.88 % (#44) under `writer`, "looks the same" (Patrik). Not needed under `sync`.
- Risk when on: moderate (a per-frame CPU loop on the render thread on a 4-core board whose capture thread is the thing
  we protect). Park on `drop-count`, revert from `drop-frames`.

### 2.6 `c13b846` `APERTAR_PREVIEW_PLANE` (park, do not merge)

- Off (confirmed): `src/main.cpp:266-270` tests the variable before `QGuiApplication`; `render()` tests it once
  (`PreviewWindowRenderer.cpp:2671-2676`); `m_plane` stays null so `showOnPlane()` is never called (`:2741` short-
  circuits). The shader gains `uniform int uOverlayOnly` (`:735`), `vec4 mark = vec4(0.0)` (`:912`) with two `mark`
  assignments inside the zebra and peaking branches (`:936`, `:944`) and `gl_FragColor = uOverlayOnly == 1 ? mark :
  outColor` (`:949`); one more `glUniform1i` per draw. Small, unmeasured.
- Build (confirmed): `CMakeLists.txt:14-15` `find_package(PkgConfig REQUIRED)` + `pkg_check_modules(LIBDRM REQUIRED
  IMPORTED_TARGET libdrm)`, `:226` links `PkgConfig::LIBDRM`. The README's apt line (`README.md:234-241`) does not
  list `libdrm-dev`; on the Pi it was present (the build was clean), on a fresh image the documented recipe now fails at
  configure. The headers (`<libdrm/drm_fourcc.h>`) were already included before the branch, the link is new. The
  feature itself also needs the Qt private headers (`APERTAR_HAS_DISPLAY_POWER`, `CMakeLists.txt:231-250`) for
  Qt's `dri_fd`; without them it logs and does nothing (`DrmPreviewPlane.cpp:254-257`).
- On (confirmed from the source): `configureQt()` opens the KMS device (the config's `device`, else `/dev/dri/card1`,
  `:278-282`), probes connector/CRTC/planes with atomic + universal planes, **writes a copy of the KMS config with
  `format: argb8888` next to the original** (`:303`) and sets `QT_QPA_EGLFS_KMS_CONFIG`, `_ATOMIC`, `_PLANES_FOR_CRTCS`,
  `_ZPOS` for the process (`:309-313`). `attach()` takes Qt's DRM fd, sets `COLOR_ENCODING`/`COLOR_RANGE` on the primary
  plane and **starts a display thread** (`:389`). Per new preview buffer: `drmPrimeFDToHandle` + `drmModeAddFB2`
  (`:439-448`), cached by buffer key. Per frame: one legacy `drmModeSetPlane` from the display thread (`:505`), which
  blocks about one vblank, while Qt page-flips the overlay with atomic commits on the same fd. The window is made
  transparent (`:421`), zebra/peaking are drawn as premultiplied marks only. LUT, grayscale, false colour, SMPTE and 90
  degree rotation fall back to the GPU path with `hide()` (plane off): toggling an aid switches the whole picture
  between the HVS scaler (BT.709 limited, plane) and the shader's own conversion, a visible change in colour/scaling
  (probable, not seen).
- Thread safety as read: `show()`/`hide()`/`releaseBuffers()` run on the render thread, `applyJob` on the display
  thread; the mutex, `m_busy` wait before `drmModeRmFB` (`:550-560`), atomic `m_failed`/`m_warned` and the join in the
  destructor look right. No page-flip events are requested, so Qt's event reader is not confused (comment at `:511`).
- Interaction with Qt (probable): two commit streams on one CRTC serialise in the DRM core; the only timing we have is
  #60 (`QSG_RENDER_TIMING` with the plane): swap 18.6 ms mean against 8.7 ms without it (#35), i.e. the UI's swap
  waited longer with the plane active. Not a loss by itself, but a sign the two streams contend.
- Measured: 0 (#46), 1.82 (#47), 1.93 (#48), 3.42 % (#50); plane + `cpu` 3.13 % (#49); **plane with the aids off
  7.22 % (#58)**, worse than with them on and equal to the baseline. The `QSG_RENDER_TIMING` take with the plane showed
  render 0.7 ms (the GPU work really was removed) and the losses stayed: whatever cost the frames was not the GPU work.
- Memory-bandwidth arithmetic, since "memory-bus contention" was the probable mechanism quoted for the plane (numbers
  from the formats, probable, not measured): capture 16.9 MB x 25 = 422 MB/s into RAM, plus Core's copies and the
  writeback (about 4-5 passes, about 2 GB/s); preview 1280x720 YUV420 = 1.4 MB x 25 = 35 MB/s written by the ISP and
  read by the GPU; a 1920x1080 RGBA pass is 8.3 MB, the direct path draws about two passes per redraw at about 30
  redraws/s = 0.5 GB/s, the FBO path about 1 GB/s; scan-out 1080p60 = 0.5 GB/s. The display stack is about 1 GB/s of a
  bus whose theoretical rate is 17 GB/s (LPDDR4X-4267, 32-bit); the plane removes about half of that 1 GB/s. The
  numbers do not support "the GPU preview saturates memory", and they match the measurement: removing the GPU work did
  not remove the losses.
- Risk: when on, medium-high (reconfigures the display stack at start-up, writes a file, unexercised failure branches,
  operator-visible mode switches); when off, low but real (805 lines, a hard build dependency the README does not
  name, 100 lines in the renderer's hot path). Not needed for target 1. Park on `preview-plane`; revisit only if B7
  (target 2) shows UI-correlated loss under `sync` and B8 confirms it.

## 3. Does any UI commit since `ea44bd7` add per-frame or periodic work that could explain the 7 % on its own?

Inventory of `ea44bd7..c13b846` (14 commits, 22 files, +2636/-151), looking for anything that runs without an operator
action. The A0-era UI itself: the night report names `1cf98ad` as the worktree `~/ApertarUI-a0`; that hash is not in
this clone (`git log 1cf98ad` fails), so "A0-era UI" here means `ea44bd7` (2026-10-30 01:00, seven hours before A0),
the last branch commit before the drop-frames UI work. Check on the Pi with `git -C ~/ApertarUI-a0 log -1` which
commit that worktree really holds.

| Commit | New per-frame / periodic work on the default path | Size of it |
| --- | --- | --- |
| `841d0ed` buffer bar, pill, Frames/RAM, Log, pre-roll | **Yes, event-driven**: `applyBufferState()` on each Core `buffer` event (<= 4/s while recording) emits `bufferFillChanged` on change (`ApertarControlBridge.cpp:2698`); `qml/StatusChip.qml:97-117` and `qml/ExternalMonitorWindow.qml:1109-1133` bind an Item's width to the fill with `Behavior on width { NumberAnimation { duration: 150 } }` (`StatusChip.qml:106-107`, `ExternalMonitorWindow.qml:1124-1125`). The Item is `visible: bufferBarVisible` (false by default, `StatusChip.qml:104`, `ExternalMonitorWindow.qml:1121`), **but the binding and the Behavior are live whatever the option says**: each changed level starts a 150 ms animation on an invisible item in the visible HDMI window. Qt Quick renders every vsync while an animation runs (probable: Qt's render-loop design; not verified in this Qt build). In `frames` mode the sampled level is 0, 1 or 2 of 12 and changes often; in `ram` mode (the 19:09 takes ran with `buffer=ram`, hardware log) it changes at every 250 ms sample | bounded by measurement: with the preview at 25 fps the UI redrew about 29 times a second (#35-#36, 582 frames in 20 s), so at most about 4 extra redraws/s were happening, not a jump to 60 Hz. Small; and the same code was running in the clean `sync` takes (#74, #75, #80, `frames` mode) |
| `841d0ed` SettingsBridge | one key added to the pre-existing 10 s external-settings poll (`SettingsBridge.cpp:433`) | nil |
| `4959513`, `96a7aa4` | QML bindings on existing state | nil |
| `606f137` Clip names card | two one-shot debounce `Timer`s (350 ms preview, 1000 ms save, `ClipNameCard.qml:332-341`) and a 0 ms one-shot (`ClipNamePill.qml:92`), all started by edits in Settings > Record, stopped when a take starts | nil during a take |
| `5697b54`, `e061be8` audio-meter outline | a border-colour binding; the meter itself (`arecord` subprocess, 70 ms decay timer `AudioMeterBridge.cpp:15`, Core `audio_level` events) is pre-existing on `main` | nil (and #38, meter off, lost 8.9 %: the meter is not the 7 %) |
| `41ff827` fan mode via Core | command path only | nil |
| `68e1a41` | one compare per `buffer` event/state; a relayout per dropped frame (2.1) | nil at 0 drops |
| `c234d77` | one false `&&` per preview frame | nil |
| `a51c95e`, `4724007`, `c13b846` | shader uniforms/branches and 5-6 GL calls per draw (2.3, 2.5, 2.6) | small; unmeasured (`V3D_DEBUG=shaderdb`) |

Pre-existing periodic work, unchanged by the branch, for the record: `SystemStatsBridge` 1 s timer
(`SystemStatsBridge.cpp:10`), the Core state poll every 30 s when steady (`ApertarControlBridge.cpp:18`), the settings
poll every 10 s, the audio meter.

Conclusion (probable): nothing in `ea44bd7..c13b846` adds per-camera-frame work on the default path beyond a handful
of GL calls; the only new periodic work is the `buffer`-event-driven 150 ms `Behavior` animation, and the measured
redraw rate (29/s) bounds its effect to a few redraws a second. The Core side changed more between A0 (`a40112a`) and
the 19:09 take (`4b2eeac`/`64bbbaa`): the `buffer` event thread, `recording_health` events, the warm raw pool, the
one-shot 16.9 MB `write()`, the RAM-buffer code (night report 8.2 Q5). The UI cannot explain 7 % on its own; the
hypothesis that remains is the one the night report reached: the UI's ordinary redraws were the last straw on a memory
regime that `writer` created, and `sync` removed the regime (#74, #75, #80 ran the same UI, same aids, 0 lost).

Hygiene, independent of the decision (optional, one line each): `Behavior on width { enabled: root.bufferBarVisible;
NumberAnimation { duration: 150 } }` in `StatusChip.qml` and the matching `enabled:` in `ExternalMonitorWindow.qml`
stop the invisible bar from animating. It removes the one periodic candidate instead of measuring it.

## 4. The test that shows it: UI `ea44bd7` vs `c13b846` under `sync` (test U1)

- Question: does the UI branch (all 14 commits, switches off) cost any frames under `sync`, compared with the A0-era UI?
- Setup: Core `adac040` built (sync default), the `/run` `dontneed.conf` drop-in removed; decide once whether the #80
  dirty limits are on and keep them the same for every take; drive trimmed and below 50 % (delete + `fstrim` between
  takes); WebUI closed; no build during takes; peaking + zebra on, audio meter as Patrik normally runs it;
  `buffer=frames` for the main run (the regime of #74-#80) and one extra pair in `ram` mode (the mode of the 19:09
  takes, and the mode in which the bar's level changes at every sample). Build the old UI in a worktree
  (`git -C ~/ApertarUI worktree add ~/ApertarUI-a0 ea44bd7` if `~/ApertarUI-a0` is not already it; `cmake --build`
  there, not during a take) and switch the service's `ExecStart` to the other binary with a `/run` drop-in + `systemctl
  restart apertar-ui-direct` between takes. Order: c13b846, ea44bd7, c13b846, ea44bd7, each 3 minutes (`take3v2.sh`),
  then the `ram` pair. Record UI CPU (`pidstat -p <ui pid> 1`) during each take.
- Duration: 6 x 3 min + restarts, about 35 minutes.
- Numbers: 4,500 frames per take, 9,000 per arm; 0 of 9,000 bounds the loss rate below 0.033 % (95 %); a 0.5 %
  effect is 22 frames in one take, so the design is far more sensitive than needed to see anything like the 7 %.
- Decision rule: both arms 0 (or <= 1): the UI branch adds nothing measurable under `sync`; the "A0 regression"
  reading of the 2026-11-01 hardware-log entry is closed (it was the regime), and the keep/revert decision above
  stands on code grounds alone. `ea44bd7` clean and `c13b846` losing >= 3 in both of its takes: something in the UI
  branch costs under `sync`; split next with a build at `41ff827` (before the six commits) to separate the feature set
  `841d0ed..41ff827` from the switches, and apply the `Behavior` `enabled:` fix as the first candidate. Both arms lose:
  the UI is not the variable; back to the Core-side plan (B1-B4).
- Zero-take companion (U2): a 20 s `QSG_RENDER_TIMING=1` take per UI build during a `ram`-mode take (not counted for
  losses; the logging adds load) and count frames per second: 25-30 means the preview drives the redraws; 50-60 means
  an animation is running continuously and the `Behavior` fix matters.

## 5. Mechanics of the park/revert

- The parked tips exist only as worktrees on the Mac (`preview-plane` @ `c13b846`, `drop-count` @ `4724007`); neither
  branch is on GitHub (`git branch -a` in this clone shows only `origin/drop-frames` and `origin/main`). Push them
  before anything is reverted, or the park is one laptop away from loss: `git push origin preview-plane drop-count`.
- Revert on `drop-frames`, newest first, which applies cleanly because each commit builds on the previous one:
  `git revert --no-edit c13b846 4724007 322d329 a51c95e`. `c234d77` and `68e1a41` stay (different files, no conflict).
  Reverts keep the fork-log consistent (one row per commit, including the reverts). The alternative, since nothing is
  merged and `drop-frames` is fork-only, is `git reset --hard c234d77` + force-push after the parked branches are safe;
  Patrik decides, the revert is the safer of the two.
- After the revert: rebuild the UI on the Pi (`cmake --build` in the UI build dir, not during a take) and restart
  `apertar-ui-direct`; the CMake `libdrm` requirement goes away with `c13b846`.
- Fork-log: rows 175-180 of `fork-log.md` cover the six commits; add rows for the reverts and note where each parked
  commit lives.

## 6. Claims and their status

| Claim | Status | Evidence |
| --- | --- | --- |
| all six switches are off by default and the default path of each is a few instructions per frame or draw | confirmed | sections 2.1-2.6, file:line |
| `322d329` is a no-op with `hdmi_external_only=true` | confirmed | `main.cpp:179` `setDirectWindowRendering(true)` on the external renderer; `main.cpp:438-439` hides the main window |
| `c13b846` adds a hard build dependency the README does not list | confirmed | `CMakeLists.txt:14-15, 226`; `README.md:234-241` |
| `c13b846` starts a thread and writes a file only when on | confirmed | `DrmPreviewPlane.cpp:303, 389` behind `configureQt()`/`attach()` |
| the four preview-path commits were justified only by takes under the `writer` regime | confirmed | night report section 3; takes #30-#58 |
| the plane did not control the losses (aids off with the plane: 7.22 %) | measured | take #58 vs #46-#50 |
| the unmodified GPU preview is clean at target 1 under `sync` | measured | #74, #75, #80 |
| the GPU preview is about 1 GB/s of a 17 GB/s bus; the plane saves about 0.5 GB/s | probable | arithmetic from the formats in 2.6, not measured |
| `841d0ed`'s invisible buffer bar animates on each changed level even with the option off | confirmed (code) / probable (that Qt renders during it) | `StatusChip.qml:104-107`, `ExternalMonitorWindow.qml:1121-1125`; Core `ApertarCoreApp.cpp:10951-11008` |
| that animation adds at most a few redraws a second | measured bound | 29 redraws/s with a 25 fps preview (#35-#36) |
| the UI's share of the 7 % is conditional on the memory regime, not a cost of its own | probable | same UI, same aids: 7-18 % under `writer`, 0 under `sync` |
| a dropped frame under `c234d77` cannot lose a buffer registration or starve Core | confirmed / probable | separate `preview_buffer` event (`ApertarCoreApp.cpp:14504`); no ack message in either source |
| the shader's uniform branches cost nothing when off | unconfirmed | `V3D_DEBUG=shaderdb` instruction counts, `41ff827` vs `c13b846` |
