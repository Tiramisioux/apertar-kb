# Review: unit "UI-bridges" (stage 2 of 3)

Scope: `git -C /home/user/Apertar-UI diff --minimal origin/main cinemate-port -- <15 paths>`, saved as
`/home/user/build/review/rev-UI-bridges.diff` (1648 lines, read whole). Inventory:
`raw/inv-UI-bridges.md`. Yardstick: `raw/conv-ui-cpp.md` (rule ids UI-*), `raw/conv-hardware-config.md`.
Refs: `@up` = UI `upstream-1.6.0` `43888e5` (= `@main` for every scope file but `ApertarControlBridge.hpp`),
`@port` = `cinemate-port` `7ea9afc`. Core `@port` = `01f170c`, Core `@up` = `35dbe67`.

## 1. What went from DisplayConfigBridge.cpp (-297) and Ina219Bridge.cpp (-280)

| Removed | Upstream behaviour that went with it | Label |
| --- | --- | --- |
| `ensureDefaultHardwareConfigFile()` in `DisplayConfigBridge.cpp:41-326@up`, called at `:587@up` | At UI start, a missing `/home/pi/apertar-hardware.conf` is created from a full commented template (every section, action names, pin examples, `chip=auto` / `gpiochip=auto` lines, `[display] 720x720 square hdmi_external_only=false`). Upstream Core never writes it; it only shows its own template in the WebUI editor (`Core:ApertarCoreApp.cpp:5297@up`) | confirmed |
| Second copy in `Ina219Bridge.cpp:69-342@up`, called at `:497@up` | Same file, 5 s later; normally a no-op. Pure duplication upstream (conv-hardware-config section 6) | confirmed |
| Includes `QDir`, `QSaveFile`, `QTextStream` in both | none | confirmed |
| 5 default lines in `DisplayConfigBridge.cpp` / 4 in `.hpp` (not a removal: `7c41a27`) | Fallback 720x720 `square`, `hdmi_external_only=false` became 1920x1080 `landscape_large`, `hdmi_external_only=true` | confirmed |

Reader defaults equal the template for INA219 (bus 4, 0x40, enabled: `Ina219Bridge.cpp:42-43`, `:217@port`),
the CFE automounter (bus 10, 0x34, `/media/RAW`, `1000110000.pcie`, enabled: `CfeAutomounter.cpp:38-39`,
`:104-111@port`) and the hotspot delay (60 s: `WifiBridge.cpp:27@port`). So `c9d841f` alone changes no runtime
value except: no file on disk to edit, `/boot/*/apertar-hardware.conf` stays live, the chip lines are gone, and
`Ina219Bridge.cpp:262-267@port` now logs "using defaults in /home/pi/apertar-hardware.conf" for a file that does
not exist. `7c41a27` is the change that alters what the operator sees.

Commit reasons (intent, not proof): `c9d841f` "A file moved away with mv ... came back as that template and
silently undid the NeoRotary fix. Core now owns the file and offers to restore it." `7c41a27` "with no hardware
file ... the touch UI fell back to 720x720 ... A restart during a test with the file moved away showed it."
Both rig-driven, both "desk only".

## 2. Findings

| Id | Sev | Category | Title |
| --- | --- | --- | --- |
| UI-bridges-F1 | blocker | removed-upstream-behaviour | Display fallback changed from the 720x720 touch panel to HDMI-only 1080p |
| UI-bridges-F2 | major | removed-upstream-behaviour | The UI no longer creates the default hardware file |
| UI-bridges-F3 | minor | bug | Preview cap drops frames before `frameArrived`, so Rec Run UI timecode slows or stops |
| UI-bridges-F4 | minor | slop | `APERTAR_UI_PREVIEW_RECORDING_FPS` is an experiment knob left in |
| UI-bridges-F5 | minor | mismatch | Six new command invokables return `void` |
| UI-bridges-F6 | minor | slop | Ticket tags and Cinemate names in code comments |
| UI-bridges-F7 | minor | removed-upstream-behaviour | Camera-screen timecode tap no longer changes file timecode; `target` ignored by original Core |
| UI-bridges-F8 | minor | bug | `ControlsWarning.qml` missing from `qml.qrc` |
| UI-bridges-F9 | minor | bug | Core media override never cleared when Core goes away |
| UI-bridges-F10 | minor | bug | Surprise-removal acts on one undebounced I2C sample |
| UI-bridges-F11 | nit | removed-upstream-behaviour | Fan mode now needs a running Core |

### F1 Display fallback: HDMI 1080p, touch window hidden (blocker)

Port: `DisplayConfigBridge.cpp:11-12@port` `kDefaultUiWidth = 1920; kDefaultUiHeight = 1080;`, `:289`
`m_uiLayout = QStringLiteral("landscape_large");`, `:294` `m_hdmiExternalOnly = true;`, `:354-357` missing-key
fallback `true`; `DisplayConfigBridge.hpp:52-59@port`. Core template follows (`Core:ApertarCoreApp.cpp:5089-5098@port`,
commit `7af9f13`).

Upstream: `DisplayConfigBridge.cpp:14-15@up` `720`, `:579` `"square"`, `:584` `false`, `:646-649` fallback
`false`; Core template `ui_width=720 ... ui_layout=square ... hdmi_external_only=false`
(`Core:ApertarCoreApp.cpp:4320-4329@up`). README `@up:3`: "Apertar-UI is the touchscreen interface".

Effect: `main.cpp:428-429@up` / `:432-433@port` `if (hdmiExternalOnly) { window->hide(); }`. A fresh install,
or any file whose `[display]` lacks `hdmi_external_only`, now hides the touch UI on a touch-panel camera. The
product's primary display mode is replaced by the contributor's rig (`night-2026-11-01.md:242`: rig has no touch
screen). Deliberate: yes (commit message), but no consideration of other rigs recorded.

Rework: revert `7c41a27` (UI) and the `[display]` part of Core `7af9f13`. The rig sets
`ui_width=1920 ui_height=1080 ui_layout=landscape_large hdmi_external_only=true` in its own file. Effort S.

### F2 No default hardware file from the UI (major)

Port removes both writers (`c9d841f`). Nothing creates the file at start: Core's store returns `""` when absent and
uses the template only for the editor (`Core:ApertarCoreApp.cpp:6188-6202@port`). Upstream: the UI is the only
automatic creator (section 1). Lost for the operator: a documented file on disk to edit over SSH; the GPIO
`chip=auto` lines under `[gpio_buttons]` / `[gpio_encoders]` (only present in the UI template,
`DisplayConfigBridge.cpp:161`, `:172@up`) - the same class of loss as the GPIO-chip setting the owner already had
restored. Side effects: `/boot/firmware/apertar-hardware.conf` stays a live candidate; the unchanged UI gyro
writer (`GyroConfigBridge.cpp:1577-1590@port`) now creates a stub file with one section; misleading INA219 log
(`Ina219Bridge.cpp:262-267@port`).

Deliberate: yes (`c9d841f`, paired with Core `014fa22` "spot a hardware file replaced by a default"). The
problem it fixes (a moved file came back as template) is a rig incident; Core's replaced-file detection already
covers it without removing first-run creation.

Rework (upstream pattern): restore `ensureDefaultHardwareConfigFile()` and its call in `DisplayConfigBridge`
(the upstream copy, with upstream `[display]` values). Removing the duplicate in `Ina219Bridge` may stay as its
own commit ("drop the second template copy; DisplayConfigBridge runs first") - a clean dedupe a maintainer can
accept. If the owner wants Core as the single writer instead, Core must create the file from
`defaultHardwareConfigTemplate()` at start when missing, and that template must carry the chip lines; document it
as new architecture. Effort S. Risk: Core `014fa22` treats a file "that starts like the touch UI's default
template" as replaced; check it does not flag a first-run file (adopted version is pinned at Core start, before
or after the UI writes).

### F3 Preview cap breaks Rec Run UI timecode (minor, bug, only with the env var)

`ApertarPreviewSocketClient.cpp:488-498@port` returns (after `closeAttachedFds()`) before `emit frameArrived()`.
`CameraPage.qml:2038-2045@port` counts `frameArrived` for Rec Run while recording (inventory O6). With
`APERTAR_UI_PREVIEW_RECORDING_FPS=12` on a 25 fps take the on-screen timecode runs at about half speed; with `0`
it stops. Failing input: env `=0`, Rec Run, record 10 s: timecode shows 00:00:00:00. Rework: drop the knob (F4),
or count the frame before dropping it.

### F4 `APERTAR_UI_PREVIEW_RECORDING_FPS` experiment knob (minor, slop / new-ground)

`ApertarPreviewSocketClient.cpp:25-43`, `:488-498`; `.hpp:36`, `:95-98`; `main.cpp:351-352@port`. Comment calls
it an "A/B knob like Core's APERTAR_WEB_PREVIEW_RECORDING_FPS" (a port-only Core variable). Off by default.
Upstream env knobs exist (`APERTAR_PREVIEW_FORCE_{CPU,PLANAR,EGL}`, `PreviewWindowRenderer.cpp:296-301@up`) but
they select a render path, not an experiment. KB `sweep-knobs.md:153` classes it developer-only; the drop-frames
synthesis says "keep as the test instrument, never a default". Not wired into the monitor-only process (O7).
Verdict: simplify - remove from the merge branch; keep on a test branch. Deliberate: yes (`c234d77`, used on the
rig `hardware-log.md:992-993`).

### F5 `void` command invokables (minor, mismatch)

Port: `ApertarControlBridge.hpp:194-200@port` `Q_INVOKABLE void applyBufferMode(...)`, `applyStoragePreroll()`,
`applyStoragePrerollAuto(bool)`, `applyClipNameTemplate(...)`, `requestClipNamePreview(...)`, `applyCdngLog(bool)`.
Upstream: every `apply*` returns `bool` (`ApertarControlBridge.hpp:111-141@up`, e.g.
`Q_INVOKABLE bool applyClearHdr(bool enabled);` right next to them); UI-I1. Bodies already early-return on
`sendCoreCommand` failure (`ApertarControlBridge.cpp:618-727@port`). Rework: return `bool`, `return false` on the
existing failure paths, `return true` at the end; QML may keep ignoring it. Effort S.

### F6 Ticket tags in comments (minor, slop)

`ApertarControlBridge.hpp:82` "T45: ...", `:435` "(T31)", `:424` "CineMate Log", `SettingsBridge.hpp:95` and
`SettingsBridge.cpp:1767` "T33: ...", `ApertarPreviewSocketClient.cpp:26` "A/B knob". Upstream comments explain
why in one line with no ticket ids (conv-ui-cpp section 11). Rework: delete the tags; "CineMate Log" -> "cDNG log
encoding". Effort S.

### F7 Timecode target (minor, removed-upstream-behaviour + protocol)

Header `ApertarControlBridge.hpp:203@port` changes `applyTimecodeMode(QString)` (`:127@up`) to
`(QString, QString target)` with no default. Body `ApertarControlBridge.cpp:750-771@port`. Upstream: one call set
Core's timecode and `UI.conf timecodeMode` together (`ApertarControlBridge.cpp:622-636@up`). Port: the tap on the
camera screen sends `target=ui` (`CameraPage.qml:1842@port`) and no longer changes clip timecode. With an
unmodified original Core the extra `target` key is ignored, so `ui` changes the file timecode too, while the UI
does not update `fileTimecodeMode`. Deliberate: yes (`7029db1`). Owned by unit UI-control-bridge; recorded here for
the header. Rework: keep the upstream one-argument invokable as the default behaviour (`target` defaults to
`both`), add the split as a separate setting.

### F8 `ControlsWarning.qml` not in `qml.qrc` (minor, bug)

`CMakeLists.txt:41@port` lists it; `qml.qrc@port` does not. Non-AOT builds (`APERTAR_QML_AOT=OFF`, default when
cross-compiling, `CMakeLists.txt:59-64@port`) load `qrc:/qml/Main.qml` (`main.cpp:401`), so `CameraPage.qml:2711`
`ControlsWarning {}` would not resolve. Upstream has the same gap for `DroppedFrameWarning.qml` (absent from
`qml.qrc@main`). Rework: add both to `qml.qrc` in the same order as `CMakeLists.txt`. Effort S. Not built here.

### F9 Stale Core media state (minor, bug)

`MediaStatusBridge.cpp:1245-1257@port` skips `QStorageInfo` while `m_coreMediaKnown && !alive && state in
{removed,error}`. Nothing clears it: `ApertarControlBridge::setConnected` (`:2840-2852@port`) does not reset
`m_coreMediaState`, and `setCoreMediaState` ignores empty state (`:1417`). Failing input: card pulled (Core sends
`removed`), Core stops, card re-inserted and mounted by the automounter: the touch UI keeps `mediaMounted=false`
until Core returns. Also O2: status text stays "MEDIA REMOVED" after a later non-mounted state (no QML reader).
Rework: on disconnect emit `coreMediaStateChanged("", true)` and let `MediaStatusBridge::setCoreMediaState`
clear `m_coreMediaKnown` on empty state. Effort S.

### F10 Surprise removal on one sample (minor, bug, probable)

`CfeAutomounter.cpp:549-550@port`: one read with bit 0 set while mounted -> `handleSurpriseRemoval()` -> lazy
unmount + PCIe remove. Upstream acts on single samples too (`:547`, `:551@up`), but only to mount when unmounted or
on a deliberate eject press. A single I2C glitch during a take now drops the recording card. Label probable:
`readButtons` (`:402-421@port`) filters only `0x69`. Rework: require the bit on two consecutive polls (200 ms)
before treating it as a pull. Effort S.

### F11 Fan mode needs Core (nit)

`SystemActionBridge.cpp:65-97`, `:404-409@port`. Upstream UI wrote `config.txt` itself (`:431-476@up`) with code
identical to upstream Core's `applyFanMode` (`Core:ApertarCoreApp.cpp:3127-3175@up`). The port now sends the
upstream Core command `set_fan_mode` (exists `@up :10568`). This removes a duplicate and matches the WebUI path;
the only loss is that the touch UI cannot change the fan while Core is down, with a clear message
("Connect to Apertar Core before changing the fan mode.", UI-I9). Deliberate: yes (`41ff827`). Verdict keep;
mention in the handoff.

## 3. Abstractions (inventory section 6)

| Name | Verdict | Reason |
| --- | --- | --- |
| `coreFanModeCommand()` | keep | Near copy of upstream `coreMediaCommand()` (`MediaStatusBridge.cpp:20-43@up`); UI-S3' allows a small private socket client, UI-I8 copies helpers. Same JSON-line protocol and env override |
| `coreMediaStateChanged` + `MediaStatusBridge::setCoreMediaState` | keep | Bridge-to-bridge signal wired in `main.cpp` (UI-S1, like `standbyChanged -> mediaBridge.setStandby` `main.cpp:335-342@up`). Fix F9 |
| `ApertarPreviewSocketClient::setRecording` + throttle | simplify | Remove with the knob (F4); has F3 |
| `SettingsBridge::reloadValueSteps` + six read-only list properties | keep | Read in ctor and `pollExternalSettings` (UI-N5), camelCase UI.conf keys (UI-I5), read-only like `presetNames`. Drop the T33 tag |
| `Automounter::handleSurpriseRemoval` | keep | Private method, `std::cout/cerr` style of the helper, comment says why. Add debounce (F10) |
| `Automounter::removePcieDevice` | keep | Extracts the upstream inline block unchanged so eject and pull share it |
| Per-feature appliers `applyBufferState`, `applyCdngLogState`, `applyClipNameState`, `applyRecordingDroppedFrames`, `setControlsStatus` | keep | One feature's keys arrive in both an event and `get_state`; upstream also factors shared readers (`applyShutterFromMicroseconds`). Bodies are in the UI-control-bridge unit. Nit: `setControlsStatus` is declared among the members (`ApertarControlBridge.hpp:453@port`), move it to the private methods |
| "Known" flags (`storagePrerollAutoKnown`, `clipNameKnown`, empty `bufferSetting`, `m_cdngLogApplied = true`) | keep | Hide controls against an original Core that never sends the key; closest upstream analogue is capability fields (`recording_capabilities`). Acceptable for UI/Core version skew |
| `ControlsWarning.qml`, `ClipNameCard.qml`, `ClipNamePill.qml` registration | keep | Same lists, same order as upstream; add `ControlsWarning.qml` to `qml.qrc` (F8) |

## 4. Conforms

- Four UI.conf switches (`recordingFrameEnabled`, `frameBufferBarEnabled`, `recordingRedTimecodeEnabled`,
  `audioRecordedOutlineEnabled`) follow recipe R3 exactly: ctor read with inline default
  (`SettingsBridge.cpp:368-371@port`), `pollExternalSettings` (`:552-555`), guarded setter with `sync()` +
  `updateSettingsFileState()` (`:1150-1216`, same shape as `setDateTimeOverlayEnabled` `:1123-1138@up`), presets
  (`:2170-2173`, `:2262-2265`). UI-I5, UI-N5.
- New `ApertarControlBridge` properties are read-only with NOTIFY; shared NOTIFY signals
  (`cameraSetValuesChanged`, `cdngLogChanged`) follow `recordingCapabilitiesChanged`
  (`ApertarControlBridge.hpp:34-39@up`). UI-S4.
- `bufferSafetyStopped(QString)` mirrors `recordingFailed(QString)` (`ApertarControlBridge.hpp:180@up`).
- `main.cpp:318-319`, `:351-352@port`: cross-bridge wiring with `QObject::connect` in `main()`. UI-S1.
- `MediaStatusBridge::updateStatus` extended in place with a two-line why-comment.
- `CfeAutomounter` extended in place, helper style kept (UI-I6 `std::cerr` in std-only helpers).
- Fan mode: the duplicate of Core's config.txt writer is gone, the UI uses an existing upstream Core command,
  `applyFanMode` stays `bool` + `lastError` (UI-I1) and keeps mode validation and the read path.
- `CMakeLists.txt` / `qml.qrc` lists keep upstream order.

## 5. Not judged here (other units)

`ApertarControlBridge.cpp` bodies, Core handlers for the new commands (`set_buffer_mode`, `set_cdng_log`,
`storage_preroll`, `set_storage_preroll`, `set_clip_name_template`, `preview_clip_name`) and their on/off / auto/off
string values versus upstream's `"true"`/`"false"` (UI-I4), Core's `HardwareConfigStore` and the Core template.

## Skeptic

Every finding re-read on both sides (`/home/user/Apertar-UI` @cinemate-port, `/home/user/wt/ui-upstream` and `/home/user/wt/core-upstream` @upstream-1.6.0, `/home/user/Apertar-Core` @cinemate-port).

| Id | Verdict | Why |
| --- | --- | --- |
| F1 | stands | Confirmed: port `DisplayConfigBridge.cpp:11-12,289,294,354-357` = 1920/1080/landscape_large/true; upstream `:14-15,579,584,646-649` = 720/720/square/false. Files written by upstream templates carry `hdmi_external_only=false` (UI `:323`, Core `:4329`@upstream-1.6.0), so the hit is a missing file or an older file without the key. With F2 a fresh install has no file, so the touch panel always shows nothing (`main.cpp:432-433`). Blocker holds. |
| F2 | corrected | Removal confirmed. The rework "restore the UI writer" fights the port's own Core restore check (Core 014fa22 flags a file that "starts like the touch UI's default template"), so a restored UI writer would re-create the hazard c9d841f removed and trip Core's check. Primary rework is now: Core writes the file from `defaultHardwareConfigTemplate()` when it is missing and no last-written copy exists. Also: the Core template has no `chip=auto` under `[gpio]`/`[gpio_encoders]` (port `ApertarCoreApp.cpp:5137-5144`); the upstream UI template had it under `[gpio_buttons]`/`[gpio_encoders]` (`:161,:172`@upstream-1.6.0). GyroConfigBridge stub claim not re-verified, removed from the finding. |
| F3 | stands | Confirmed: `ApertarPreviewSocketClient.cpp:488-498` returns before `frameArrived`; `CameraPage.qml:2038-2045` counts `frameArrived` for Rec Run; `Main.qml:499` binds `bridge: apertarPreviewBridge`. Only with the env var set. Fixed by F4. |
| F4 | stands | Confirmed at the cited lines; commit c234d77 calls it "an A/B knob". |
| F5 | corrected | Five of six are `apply*` and break the bool rule (`ApertarControlBridge.hpp:111-141`@upstream-1.6.0, all `bool` except `refresh`, `notifyUserActivity`). `requestClipNamePreview` is a query, not a command; `void` matches upstream `refresh()`. Scope cut to five. |
| F6 | corrected | Cited lines confirmed. More T-tags in the unit's own files: `ApertarControlBridge.cpp:275` (T31). The QML sites (`CameraPage.qml:518`, `ControlsWarning.qml:3`, `SettingsPage.qml:6455`, `TopDropdownStat.qml:11,100`) belong to the QML unit; listed for the sweep. |
| F7 | corrected | The "unmodified original Core ignores target" point is moot: port Core reads `target` with default `both` (`ApertarCoreApp.cpp:13286`@cinemate-port), and UI and Core ship as a pair. What stands: the camera-screen tap now changes only the UI timecode (`CameraPage.qml:1842`), upstream's tap changed both. Deliberate (7029db1). Severity minor -> nit. |
| F8 | stands | Confirmed: `CMakeLists.txt:41` has it, `qml.qrc` does not; non-AOT path adds `qml.qrc` (`CMakeLists.txt:202`) and loads `qrc:/qml/Main.qml` (`main.cpp:401`). The port did add `ClipNameCard`/`ClipNamePill` to qml.qrc, so the miss is an oversight. |
| F9 | stands | Confirmed: `MediaStatusBridge.cpp:1245-1257` early return; `ApertarControlBridge.cpp:1417` ignores empty state; `setConnected` (`:2840-2853`) does not clear media state. The status text is never reset on the later path (only `setMediaMounted` at `:1286`). |
| F10 | corrected | Upstream also acts on single samples: the eject release `lastEject && !eject -> unmountPcie()` (`CfeAutomounter.cpp:549-550`@upstream-1.6.0). The difference is the action: upstream `unmountPcie` uses `umount2(path, 0)` (`:704`), which fails on a busy mount during a take; the port's `handleSurpriseRemoval` does `MNT_DETACH` plus PCIe remove (`:735-740`@cinemate-port), which cannot be refused. A failed read already returns `nullopt` (`:410-416`@upstream-1.6.0), so only a wrong byte read cleanly triggers it. Stays minor, probable. |
| F11 | stands | Confirmed. The private synchronous `QLocalSocket` client has an upstream precedent in `MediaStatusBridge.cpp:15-35`@upstream-1.6.0 (id 42001); the port copies it (id 42002). Keep. |

## Final findings

### UI-bridges-F1 [removed-upstream-behaviour, blocker] Display fallback changed from 720x720 touch panel to HDMI-only 1080p (touch window hidden)
- where: `src/DisplayConfigBridge.cpp:11-12`, `:289`, `:294`, `:354-357`, `src/DisplayConfigBridge.hpp:52-59`, Core `src/ApertarCoreApp.cpp:5089-5098` (all @cinemate-port)
- port way: `kDefaultUiWidth=1920`, `kDefaultUiHeight=1080`, `m_uiLayout="landscape_large"`, `m_hdmiExternalOnly=true`, missing-key fallback `true`; Core template mirrors it (Core 7af9f13).
- Apertar way: `src/DisplayConfigBridge.cpp:14-15` 720/720, `:579` "square", `:584` false, `:646-649` fallback false; upstream templates write `hdmi_external_only=false` (UI `:323`, Core `ApertarCoreApp.cpp:4320-4329`) (all @upstream-1.6.0). README: "Apertar-UI is the touchscreen interface".
- why it matters: `main.cpp:432-433` hides the main window when `hdmiExternalOnly` is set. A missing file, or an older file without the key, shows no touch UI on a touch-panel camera. With F2 a fresh install has no file at all, so every fresh port install starts HDMI-only. Upstream's primary display mode becomes the contributor's rig.
- rework: Revert UI 7c41a27 (constants, start values, hpp member defaults, missing-key fallback to 720/720/square/false). Revert the `[display]` block in Core `defaultHardwareConfigTemplate()` (from 7af9f13). The rig sets `ui_width=1920 ui_height=1080 ui_layout=landscape_large hdmi_external_only=true` in its own `apertar-hardware.conf`.
- effort: S
- deliberate: yes. 7c41a27: a test restart with the file moved away showed 720x720 on the rig's HDMI. No touch-panel camera considered.

### UI-bridges-F2 [removed-upstream-behaviour, major] Nothing creates the default apertar-hardware.conf at first start any more
- where: `src/DisplayConfigBridge.cpp:35-38` (writer gone), `src/Ina219Bridge.cpp:63-66` (writer gone), `src/Ina219Bridge.cpp:262-267`; Core `src/ApertarCoreApp.cpp:6190-6202`, `:5137-5144` (all @cinemate-port)
- port way: both `ensureDefaultHardwareConfigFile()` writers and calls deleted (c9d841f). Core's store returns the template text when the file is missing (`ApertarCoreApp.cpp:6200-6201`) but does not write it; only the WebUI editor shows it. Core 014fa22 flags a missing file or one that "starts like the touch UI's default template" and offers a restore.
- Apertar way: `src/DisplayConfigBridge.cpp:41-326`, `:587`@upstream-1.6.0 writes `/home/pi/apertar-hardware.conf` from a full commented template when missing, with `chip=auto` under `[gpio_buttons]`/`[gpio_encoders]` (`:161`, `:172`) and `gpiochip=auto` under the outputs (`:110`, `:123`). Second copy in `Ina219Bridge.cpp:69-342`, `:497`. Upstream Core only shows its template.
- why it matters: a fresh image has no documented file to edit, and with F1 it starts HDMI-only. The Core template lacks the `chip=` lines for `[gpio]`/`[gpio_encoders]`, the same class of loss as the GPIO-chip setting the owner had restored. The INA219 log names a file that does not exist.
- rework: Do not restore the UI writer: it would re-create the hazard c9d841f removed and trip Core's own "replaced by the touch UI template" check. Instead Core writes the file from `defaultHardwareConfigTemplate()` at start when it is missing and no `hardware-last-written.conf` exists (when one exists, keep today's "missing, restore?" path). Add `chip=auto` under `[gpio]` and `[gpio_encoders]` in the Core template. Keep the Ina219Bridge copy removed. Document "Core is the single writer of apertar-hardware.conf" as considered new architecture for the original developer.
- effort: S
- deliberate: yes. c9d841f: a moved file came back as the template and undid the NeoRotary fix; "Core now owns the file and offers to restore it" (Core 014fa22). Desk-only test.

### UI-bridges-F3 [bug, minor] Preview cap drops frames before frameArrived, so the Rec Run UI timecode slows or stops
- where: `src/ApertarPreviewSocketClient.cpp:488-498`, `qml/CameraPage.qml:2038-2045`, `qml/Main.qml:499` (@cinemate-port)
- port way: with `APERTAR_UI_PREVIEW_RECORDING_FPS` set, frames over the cap return before `emit frameArrived()`.
- Apertar way: no precedent; upstream emits `frameArrived` for every frame and counts it the same way (`qml/CameraPage.qml:1901-1908`@upstream-1.6.0).
- why it matters: Rec Run timecode counts `frameArrived` while recording. env=0: a 10 s take shows 00:00:00:00. env=12 on a 25 fps take: timecode runs at about half speed. Only when the env var is set.
- rework: Remove the knob (F4). If it stays on a test branch, count the frame for timecode before dropping it.
- effort: S
- deliberate: no. No KB or commit note on the timecode interaction.

### UI-bridges-F4 [slop, minor] APERTAR_UI_PREVIEW_RECORDING_FPS experiment knob left in the merge branch
- where: `src/ApertarPreviewSocketClient.cpp:25-43`, `src/ApertarPreviewSocketClient.hpp:36,95-98`, `src/main.cpp:351-352` (@cinemate-port)
- port way: env var read in the constructor ("A/B knob like Core's APERTAR_WEB_PREVIEW_RECORDING_FPS"), `setRecording` wired from `recordingChanged`, throttle in `handlePreviewFrame`. Off by default.
- Apertar way: upstream env knobs select a render path only: `APERTAR_PREVIEW_FORCE_{CPU,PLANAR,EGL}` (`src/PreviewWindowRenderer.cpp:296-301`@upstream-1.6.0). No experiment throttles.
- why it matters: a test instrument with a known bug (F3) reads as a product feature to the original developer.
- rework: Drop `setRecording`, the four members, the env read and the `main.cpp` connect from the merge branch. Keep them on a test branch.
- effort: S
- deliberate: yes. c234d77 ("an A/B knob"); used on the rig with =12 and =0 (`lessons/hardware-log.md:992-993`); KB `sweep-knobs.md:153`: developer-only, "never a default".

### UI-bridges-F5 [mismatch, minor] Five new apply* invokables return void instead of bool
- where: `src/ApertarControlBridge.hpp:194-200`, `src/ApertarControlBridge.cpp:618-727` (@cinemate-port)
- port way: `Q_INVOKABLE void applyBufferMode, applyStoragePreroll, applyStoragePrerollAuto, applyClipNameTemplate, applyCdngLog`.
- Apertar way: every `apply*` returns `bool` and sets `lastError` on failure (`src/ApertarControlBridge.hpp:111-141`@upstream-1.6.0, e.g. `Q_INVOKABLE bool applyRawBitDepth(const QString &displayValue);`). Only `refresh()` and `notifyUserActivity()` are void. `requestClipNamePreview` is a query like `refresh()` and may stay void.
- why it matters: breaks a one-line rule a maintainer relies on; QML cannot react to a refused command.
- rework: Change the five to `bool`: return the `sendCoreCommand` result / `false` on the existing early returns, `true` at the end. QML may ignore it.
- effort: S
- deliberate: no. No commit or KB note.

### UI-bridges-F6 [slop, minor] Ticket tags and Cinemate names in code comments
- where: `src/ApertarControlBridge.hpp:82`, `:424`, `:435`, `src/ApertarControlBridge.cpp:275`, `src/SettingsBridge.hpp:95`, `src/SettingsBridge.cpp:1767`, `src/ApertarPreviewSocketClient.cpp:26` (@cinemate-port). Same tags in QML (QML unit): `qml/CameraPage.qml:518`, `qml/ControlsWarning.qml:3`, `qml/SettingsPage.qml:6455`, `qml/TopDropdownStat.qml:11,100`.
- port way: "T45: ...", "(T31)", "T33: ...", "CineMate Log", "A/B knob".
- Apertar way: one or two lines on why, no ticket ids (conv-ui-cpp section 11, e.g. `src/ApertarControlBridge.cpp:861-862`@upstream-1.6.0).
- why it matters: ids mean nothing to the original developer; "CineMate" names another project.
- rework: Delete the T-tags. Rename "CineMate Log" to "cDNG log encoding". Drop the "A/B knob" comment with F4.
- effort: S
- deliberate: no

### UI-bridges-F7 [removed-upstream-behaviour, nit] The camera-screen timecode tap no longer changes clip timecode
- where: `src/ApertarControlBridge.hpp:202-203`, `src/ApertarControlBridge.cpp:750-771`, `qml/CameraPage.qml:1842` (@cinemate-port); Core `src/ApertarCoreApp.cpp:13286`@cinemate-port
- port way: `applyTimecodeMode(displayValue, target)` with no default; the CameraPage tap sends `target=ui`. Port Core defaults a missing target to `both`, so the protocol stays compatible.
- Apertar way: `src/ApertarControlBridge.cpp:622-636`@upstream-1.6.0: one call sends `set_timecode_mode` and writes UI.conf `timecodeMode`; Core changes clip timecode too.
- why it matters: an upstream operator gesture changes meaning (shown timecode only). Product decision, not architecture.
- rework: Give the invokable `target = QStringLiteral("both")` as default so the upstream one-argument call keeps its meaning; record the tap change in the handoff. Owned by unit UI-control-bridge.
- effort: S
- deliberate: yes. 7029db1 "UI timecode and file timecode are set apart".

### UI-bridges-F8 [bug, minor] ControlsWarning.qml missing from qml.qrc (non-AOT builds)
- where: `CMakeLists.txt:41`, `qml.qrc` (@cinemate-port)
- port way: added to `APERTAR_QML_FILES` only; the same branch did add `ClipNameCard.qml`/`ClipNamePill.qml` to qml.qrc.
- Apertar way: the two lists mirror each other (`CMakeLists.txt:19-52`, `qml.qrc:3-33`@upstream-1.6.0). Upstream has the same gap for `DroppedFrameWarning.qml`.
- why it matters: with `APERTAR_QML_AOT=OFF` (default when cross-compiling, `CMakeLists.txt:59-64`) the build adds `qml.qrc` (`:202`) and `main.cpp:401` loads `qrc:/qml/Main.qml`; `ControlsWarning {}` in CameraPage would not resolve and the page fails to load.
- rework: Add `qml/ControlsWarning.qml` and `qml/DroppedFrameWarning.qml` to qml.qrc in CMakeLists order.
- effort: S
- deliberate: no

### UI-bridges-F9 [bug, minor] Core media override in MediaStatusBridge is never cleared when Core goes away
- where: `src/MediaStatusBridge.cpp:288-296`, `:1245-1257`, `src/ApertarControlBridge.cpp:1415-1422`, `:2840-2853` (@cinemate-port)
- port way: `updateStatus` returns early with `mediaMounted=false` while the last Core state is removed/error and not alive. `setConnected(false)` does not reset it; empty states are ignored.
- Apertar way: no precedent; upstream uses `QStorageInfo` only (`MediaStatusBridge.cpp:1232-1234`@upstream-1.6.0).
- why it matters: pull the card (Core sends removed), Core stops, the card is re-inserted and mounted by the automounter: the touch UI shows no media until Core returns. `statusText` stays "MEDIA REMOVED" after a later state (no QML reader today).
- rework: On disconnect, ApertarControlBridge clears `m_coreMediaState` and emits `coreMediaStateChanged("", true)`; `MediaStatusBridge::setCoreMediaState` clears `m_coreMediaKnown` on an empty state and resets `statusText`.
- effort: S
- deliberate: no

### UI-bridges-F10 [bug, minor] Surprise card removal acts on one undebounced I2C sample, with an unrefusable unmount
- where: `src/CfeAutomounter.cpp:549-550`, `:726-746` (@cinemate-port)
- port way: one read with the insert bit newly set while mounted calls `handleSurpriseRemoval`: `umount2(MNT_DETACH)` plus PCIe device remove.
- Apertar way: upstream also acts on single samples (eject release -> `unmountPcie()`, `src/CfeAutomounter.cpp:549-550`@upstream-1.6.0), but its unmount is `umount2(path, 0)` (`:704`), which fails on a busy mount during a take. Failed reads return `nullopt` (`:410-416`), so only a wrong byte read cleanly triggers either path.
- why it matters: probable: one corrupt I2C byte during a take detaches the recording card and removes its PCIe device; the upstream path would refuse while files are open.
- rework: Require the insert bit on two consecutive 100 ms polls before `handleSurpriseRemoval`.
- effort: S
- deliberate: no

### UI-bridges-F11 [removed-upstream-behaviour, nit] Fan mode change from the touch UI now needs a running Core
- where: `src/SystemActionBridge.cpp:65-97`, `:404-409` (@cinemate-port)
- port way: `applyFanMode` sends Core's `set_fan_mode` over a private synchronous `QLocalSocket` (id 42002, 1 s connect, 8 s reply).
- Apertar way: upstream UI wrote config.txt itself with `sudo -n install` (`src/SystemActionBridge.cpp:431-476`@upstream-1.6.0), duplicating Core's `applyFanMode` (Core `ApertarCoreApp.cpp:3127-3175`); upstream Core already has `set_fan_mode`. The private socket client copies upstream `MediaStatusBridge.cpp:15-35` (id 42001).
- why it matters: no fan change while Core is down; clear operator message. Removes a duplicate writer.
- rework: Keep. Mention in the handoff.
- effort: S
- deliberate: yes. 41ff827: Core owns config.txt with a lock; the UI write could race a Boot Config save.
