# Apertar-UI navigation map

An LLM jump table for the big Apertar-UI files.

- Refs are against `upstream-1.6.0`. Fork HEAD `29ed99b` only changes build files, so line numbers are the same.
- Core refs are against Apertar-Core `ed400ba`.
- Paths are repo-relative (`qml/…`, `src/…`). Core paths are written `Core:src/…`.
- Every line number below comes from a real grep on 2026-10-25.
- Background (process model, startup, wire format, preview path, launcher) is already in [architecture/ui.md](../architecture/ui.md). It is not repeated here.

**How to use this map.** Line numbers drift. The **anchor** column holds a grep string that should still match after edits. Run `grep -n '<anchor>' <file>` first, then read about 40 lines around the hit.

---

## 1. Chapter maps

### 1.1 `qml/SettingsPage.qml` (9851 lines)

The root is `Item { id: root }`. `settingsState` (`:16`) is `settingsBridge`, passed in by `Main.qml:569`. Every other bridge is used as a bare global context property.

**Section → item-id → Component dispatch.** The sidebar picks `selectedSection`. Each section `Column` runs a `Repeater` over its stored order. The `*ComponentForId()` function maps an item id to a `Component`, and a Loader builds that Component.

| Lines | Chapter | Key ids / functions | Anchor |
| --- | --- | --- | --- |
| 1-16 | Imports (`TimelapseIntervals.js as Intervals` `:4`), `signal backRequested` `:9`, `selectedSection: "Monitoring"` `:15` | `settingsState` | `property string selectedSection` |
| 17-59 | Layout flags (`standardLandscapeLayout` = `landscape` **only**, `:23`) and size tokens | `settingsSidebarWidth` `:50` | `readonly property bool standardLandscapeLayout` |
| 61-109 | Local aid mirrors (`:61-68`), sensor detection (`imx577/477/294/585Detected` `:87-90`), record-format flags (`:98-109`) | `recordFormat` `:98` | `readonly property bool cdngRecordFormat` |
| 110-225 | **Per-sensor resolution and crop tables** (copy of CameraPage, see §4) | `imx477ResolutionOptions` `:110`, `imx294Raw10ResolutionOptions` `:143`, `imx585Raw12ResolutionOptions` `:151`, `h264BaseResolutionOptions` `:221` | `imx585Raw12ResolutionOptions:` |
| 226-247 | Still/timelapse formats, battery types, battery text | `stillFormatOptions` `:226`, `batteryTypeOptions` `:230` | `stillFormatOptions:` |
| 248-324 | Date/time draft and time-zone list | `systemTimezoneOptions` `:254` | `property var systemTimezoneOptions` |
| 325-702 | Resolution/crop helpers and photo-timelapse helpers | `normalizedRecordResolution` `:564`, `applyRecordResolutionValue` `:627` (→ `applyResolution` `:630`), `applyPhotoTimelapse` `:678` | `function applyRecordResolutionValue` |
| 703-749 | Popup open/close state flags | `powerConfirmOpen`, `formatConfirmOpen`, `wifiPasswordPopupOpen`, `presetNamePopupOpen`, `gyroCalibrationRunning` | `property bool powerConfirmOpen` |
| 750-770 | Gyro option lists and keyboard layouts | `gyroDriverOptions` `:750`, `wifiLetterKeyboardRows` `:753` | `gyroDriverOptions:` |
| 771-878 | **Default item order per section** and the favourite candidates | `defaultMonitoringOrder` `:771`, `defaultRecordOrder` `:784`, `defaultAudioOrder` `:794`, `defaultPowerOrder` `:798`, `defaultSystemOrder` `:803`, `defaultWifiOrder` `:815`, `defaultInfoOrder` `:821`, `defaultSidebarOrder` `:827`, `favoriteCandidateOrder` `:838` | `readonly property var defaultSidebarOrder` |
| 879-925 | Favourites/reorder state; `onSelectedSectionChanged` `:889` (calls `wifiBridge.refresh` `:901` and `audioDeviceBridge.refresh` `:906`) | | `onSelectedSectionChanged:` |
| 926-1281 | Section order machinery and favourites | `normalizedSectionOrder` `:999`, `applySectionOrder` `:1040`, `sectionItemTitle` `:1064`, `sourceSectionForItemId` `:1161`, `saveReorderPopup` `:1273` | `function normalizedSectionOrder` |
| 1282-1347 | Value converters for aids | `zebraLevelToThreshold` `:1282`, `focusThresholdToValue` `:1304`, `falseColorModeToInt` `:1318`, `opacityLabelToValue` `:1326` | `function zebraLevelToThreshold` |
| 1348-1401 | Connections: `audioDeviceBridge` `:1348`, `apertarControlBridge` (`onGyroCalibrationFinished` `:1363`), `gyroConfigBridge` (`onConfigSaveFinished` `:1373`), `settingsState` `:1379`; Timer `gyroCalibrationStartDelay` `:1387` → `calibrateGyro()` `:1399` | | `id: gyroCalibrationStartDelay` |
| 1403-1780 | System helpers: battery estimate `:1472-1585`, media `:1586-1626`, power confirm `:1637-1673`, eject `:1674`, format `:1689`, date/time `:1708-1760`, fan `:1761` | `executeEjectMedia` `:1679`, `executeFormatMedia` `:1695`, `executePendingPowerAction` `:1657`, `executeApplyFanMode` `:1761` | `function executeFormatMedia` |
| 1781-1975 | Wi-Fi connect flow and on-screen keyboard | `openWifiConnect` `:1788`, `submitWifiConnect` `:1818`, `saveHotspotEdit` `:1848`, `wifiKeyboardInsert` `:1925` | `function submitWifiConnect` |
| 1976-2109 | Presets and preset keyboard | `savePresetFromDraft` `:1996`, `importPresetsFromMedia` `:2004`, `applyPresetByName` `:2010`, `exportPresetByName` `:2016`, `executePresetDelete` `:2040` | `function applyPresetByName` |
| 2110-2215 | Gyro label maps, `updateSectionActivity` `:2139`, `releaseBackgroundWork` `:2153`, `Component.onCompleted` `:2167`, Connections `wifiBridge` `:2182`, `sharedDropdownController` `:2191`, the reorder/sidebar models `:2196-2214` | | `function updateSectionActivity` |
| 2216-2384 | **Dispatch tables: item id → Component**, plus the LUT and tuning-file label helpers | `monitoringComponentForId` `:2216`, `recordComponentForId` `:2318`, `audioComponentForId` `:2330`, `powerComponentForId` `:2336`, `systemComponentForId` `:2343`, `wifiComponentForId` `:2357`, `infoComponentForId` `:2365`, `favoriteComponentForId` `:2373` | `function monitoringComponentForId` |
| 2385-6109 | **One `Component` per settings item.** Table below | | `id: <name>Component` |
| 6111-6328 | Reorder delegates and drag layer | `reorderDelegate` `:6111`, `sidebarReorderDelegate` `:6221`, `reorderDragLayer` `:6318` | `id: sidebarReorderDelegate` |
| 6330-7211 | **Page layout**: `header` `:6335`, `contentArea` `:6409`, `sidebar` `:6416` / `sidebarListView` `:6428`, `panel` `:6463`, `sectionFlick` `:6475`, section columns (below), `dropdownOverlay` `:7198` | | `id: sectionFlick` |
| 7213-9850 | **Popups/cards**, one `Rectangle` each with `visible: root.<flag>`. Table below | | `visible: root.<flag>` |

**Section columns inside `sectionFlick`.**

| Section (`selectedSection`) | Column id : line | Repeater model : line | Dispatcher |
| --- | --- | --- | --- |
| Favorites | `favoritesColumn` :6506 | `root.favoriteItems()` :6633 | `favoriteComponentForId` |
| Monitoring | `monitoringColumn` :6647 | :6685 | `monitoringComponentForId` |
| System | `systemColumn` :6695 | :6733 | `systemComponentForId` |
| Presets | `presetsColumn` :6743 | `settingsState.presetNames` :6894 | inline delegate. No Component. Apply button calls `applyPresetByName` :6911 |
| Wi-Fi | `wifiColumn` :6932 | :6970 | `wifiComponentForId` |
| Record | `recordColumn` :6980 | :7018 (only while `pageOpen`) | `recordComponentForId` |
| Power (shown as "Media", `:1122`) | `powerColumn` :7028 | :7066 | `powerComponentForId` |
| Audio | `audioColumn` :7076 | :7114 | `audioComponentForId` |
| Info | `infoColumn` :7124 | :7162 | `infoComponentForId` |
| (fallback) | `placeholderSection` :7172 | | |

**Settings item Components.** The bridge column lists the members each Component reads or calls (extracted by script). `settingsState` means `settingsBridge`. A Component that touches only `settingsState` writes `UI.conf` and **sends no socket command**.

| Lines | Component id | Title | Bridges and members |
| --- | --- | --- | --- |
| 2385-2426 | `monitoringExternalMonitorComponent` | External Monitor | settingsState: externalMonitorEnabled/Mode/InfoOverlay/Orientation |
| 2428-2648 | `monitoringLutPreviewComponent` | LUT Preview | settingsState: lutPreviewEnabled, lutPreviewFile, refreshLutPreviewOptions() |
| 2650-2684 | `monitoringFocusPeakingComponent` | Focus Peaking | settingsState: focusPeakingEnabled/Threshold/Color |
| 2686-2713 | `monitoringZebraComponent` | Zebra | settingsState: zebraEnabled, zebraThreshold |
| 2715-2747 | `monitoringFalseColorComponent` | False Color | settingsState: falseColorEnabled, falseColorMode |
| 2749-2783 | `monitoringGuidesComponent` | Guides | settingsState: guidesEnabled/Type/Thickness |
| 2785-2805 | `monitoringSmpteComponent` | SMPTE Bars | settingsState: smpteEnabled |
| 2807-2834 | `monitoringCenterMarkerComponent` | Center Marker | settingsState: centerMarkerEnabled/Type |
| 2836-2863 | `monitoringHorizontalLevelComponent` | Horizontal Level | settingsState: horizontalLevelEnabled/Color |
| 2865-2885 | `monitoringGreyscaleComponent` | Greyscale | settingsState: grayscaleEnabled (QML id says "greyscale", the property says "grayscale") |
| 2887-2913 | `monitoringAnamorphicComponent` | Anamorphic Desqueeze | settingsState: anamorphicDesqueezeEnabled, anamorphicRatio |
| 2915-3025 | `recordStillModeComponent` | Still Mode | settingsState: photo*; apertarControlBridge: applyPhotoModeEnabled/LongExposureEnabled/BracketingEnabled/BracketingEv/Timelapse |
| 3027-3065 | `recordSoundRecorderComponent` | Sound Recorder | settingsState: soundRecorderEnabled; apertarControlBridge.applyPhotoModeEnabled; audioDeviceBridge.hasInputDevices |
| 3067-3110 | `recordExposureCompensationComponent` | Exposure Compensation | apertarControlBridge: applyExposureCompensation, applyExposureMetering, exposure* |
| 3112-3116 | (function `exposureCompensationLabel`, between Components) | | |
| 3118-3320 | `recordFormatComponent` | Format | apertarControlBridge: applyRecordingFormat :3210, applyProresProfile :3235, applyRawBitDepth :3240, applyCdngCompression :3260, applyProresColorProfile :3284, applyCdngPreviewColorProfile :3306, applyH264Resolution :3166/:3188; resolution via `applyRecordBaseResolution` :3170 / `applyRecordCropResolution` :3191 |
| 3322-3498 | `recordTuningFileComponent` | Tuning File | apertarControlBridge.applyTuningFile :3458; settingsState.refreshTuningFileOptions() |
| 3500-3751 | `recordGyroComponent` | Gyro | settingsState.recordGyroEnabled; gyroConfigBridge: setDriverName, setOrientation, adjustSyncOffsetMs, setLevelReference, live accel*; calibrate button → `startGyroCalibration()` :3725 |
| 3753-3782 | `recordTimecodeComponent` | Timecode | settingsState.timecodeMode; apertarControlBridge.applyTimecodeMode :3778 |
| 3784-3860 | `recordAutofocusComponent` | Autofocus | apertarControlBridge: applyAutofocusMode :3813 / Range :3827 / Speed :3841 / Window :3855 |
| 3862-4014 | `audioOptionsComponent` | Audio | settingsState: recordAudioEnabled, liveAudioMonitoringEnabled, audioMeterEnabled, audioInput/OutputDevice; audioDeviceBridge: select*, refreshCaptureCapabilities :3936/:3989 |
| 4016-4053 | `audioLevelsComponent` | Levels | settingsState: inputVolume, headphoneVolume |
| 4055-4441 | `powerBatteryComponent` | Battery | settingsState: batteryCapacity, customBattery*; powerBridge.sensorAvailable |
| 4443-4519 | `powerBatteryInfoComponent` | Battery Info | powerBridge |
| 4521-4548 | `powerAutoPowerOffComponent` | Auto Power Off | settingsState.sleepMode |
| 4550-4606 | `systemCameraStandbyComponent` | Camera Standby | settingsState: standbyTimeoutSeconds, standbyUsbPowerOff |
| 4608-4634 | `systemUiOrientationComponent` | UI Orientation | settingsState.uiOrientation |
| 4636-4651 | `systemDisplayCalibrationComponent` | Display Calibration | displayCalibrationBridge (via `DisplayCalibrationPanel`) |
| 4653-4697 | `systemControlsOpacityComponent` | Controls Transparency | settingsState: cameraControlsOpacity, cameraControlsMode |
| 4699-4938 | `systemDateTimeComponent` | Date & Time | settingsState.dateTimeOverlayEnabled; applies through `executeApplyDateTime` → systemActionBridge |
| 4940-5118 | `systemMediaComponent` | Media | mediaBridge: mediaMounted, free/totalBytes, mountableDriveOptions, refreshMountableDrives |
| 5120-5190 | `systemFormatMediaComponent` | Format Media | mediaBridge.mediaMounted; opens `formatConfirmOpen` |
| 5192-5327 | `systemMediaSpeedComponent` | Media Speed | mediaBridge.startWriteSpeedTest :5323, writeSpeed* |
| 5329-5385 | `systemThermalComponent` | Thermal | systemActionBridge.fanMode, statsBridge.socTempC |
| 5387-5452 | `systemPowerActionsComponent` | Power Actions | apertarControlBridge.enterStandby :5420 (`objectName: "standbyButton"` :5413); restart/shutdown → `openPowerConfirmation` :5429/:5438 |
| 5454-5472 | `wifiToggleComponent` | Wi-Fi | wifiBridge.setWifiEnabled |
| 5474-5587 | `wifiCurrentNetworkComponent` | Current Network | wifiBridge: currentSsid, disconnectCurrent, refresh :5573 |
| 5589-5793 | `wifiHotspotComponent` | Hotspot | wifiBridge: start/stopHotspot, hotspotSsid/Password |
| 5795-5986 | `wifiAvailableNetworksComponent` | Available Networks | wifiBridge.networks |
| 5988-6019 | `infoCameraComponent` | Camera | deviceInfoBridge.backendName, apertarPreviewBridge.connected/statusText |
| 6021-6056 | `infoSbcComponent` | SBC | deviceInfoBridge |
| 6058-6086 | `infoSystemComponent` | System | deviceInfoBridge |
| 6088-6109 | `infoSystemDriveComponent` | System Drive | deviceInfoBridge |

**Popups (7213-9850).** Each popup is a scrim `Rectangle` plus a card `Rectangle`, matched by the visibility flag.

| Lines | `visible:` flag | What |
| --- | --- | --- |
| 7213 / 7230 | `favoriteManagerOpen` | Favourite manager (`favoriteManagerCard`) |
| 7479 / 7496 | `reorderPopupOpen` | Reorder (`reorderPopupCard`) |
| 7688 | `powerConfirmOpen` | Scrim for the power confirm |
| 7748 | `presetNamePopupOpen` | "Save Current Preset" with keyboard |
| 8016 | `presetDeleteConfirmOpen` | "Delete Preset?" |
| 8152 | `hotspotEditPopupOpen` | Hotspot SSID/password editor |
| 8438 | `wifiPasswordPopupOpen` | "Join <ssid>" password keyboard |
| 8711 | `formatConfirmOpen` | "Format Media?" → `executeFormatMedia()` :8840 |
| 8847 | `formatSuccessOpen` | "Media Formatted" |
| 8948 | `ejectConfirmOpen` | "Eject Media?" → `executeEjectMedia()` :9074 |
| 9081 | `mediaMountErrorOpen` | "Mount Failed" |
| 9180 | `powerConfirmOpen` | Restart/shutdown card → `executePendingPowerAction()` :9308 |
| 9315 | `powerErrorOpen` | "Power Action Failed" |
| 9391 / 9468 | `thermalApplySuccessOpen` / `thermalApplyErrorOpen` | Fan mode result |
| 9545 / 9776 | `timeApplySuccessOpen` / `timeApplyErrorOpen` | Date/time result |
| 9622 / 9699 | `ejectErrorOpen` / `formatErrorOpen` | Media errors |

### 1.2 `qml/CameraPage.qml` (4160 lines)

**Indentation trap.** From about `:635` to `:1925`, functions, properties and handlers sit at **column 0** inside `Item { id: root }`. The file also has 52 tab-indented lines. Do not use indentation depth to find block ends. Use the `// =====` banner comments instead (`grep -n '// [A-Z]' qml/CameraPage.qml`).

Inputs set by `Main.qml:496-517`: `bridge` = `apertarPreviewBridge`, `controlBridge` = `apertarControlBridge`, `settingsState` = `settingsBridge`.

| Lines | Chapter | Key ids / functions | Anchor |
| --- | --- | --- | --- |
| 1-22 | Imports (`TimelapseIntervals.js as Intervals` `:3`), fonts (tabs `:12-15`), signals `openSettingsRequested` `:8`, `openClipBrowserRequested` `:9`, `bridge`/`controlBridge` `:19-20` | | `signal openClipBrowserRequested` |
| 23-57 | Recording flags, warning text, `settingsState` `:33`, layout flags `:38-56` | | `property var settingsState` |
| 58-106 | Colour helpers, `updateHorizontalLevelPolling` `:71` | | `function updateHorizontalLevelPolling` |
| 107-213 | Size tokens: top bar, quick menu, bottom stats | | `quickMenuPanelWidth` (2 hits) |
| 214-322 | Mirrors of `settingsState` (timecodeMode `:214`, photo* `:215-224`, audio `:230-233`, anamorphic `:236-237`), battery functions `:249-290`, power overlay `:299-315`, photo capture state `:316-321` | `estimatedBatteryPercent` `:271` | `function estimatedBatteryPercent` |
| 323-376 | **Local copies of Core values** (`fps` `:323`, `iso` `:341`, `shutterAngle`, `shutterSpeed`, `wb`, `resolution` `:345`, `recordingFormat` `:347`, `rawBitDepthValue` `:357`, `cdngCompressionValue` `:360`), sensor detection `:363-376` | `imx585Detected` `:373` | `property string iso:` |
| 377-483 | **Per-sensor resolution and crop tables** (copy of SettingsPage `:110-225`) | `imx477ResolutionOptions` `:377`, `imx585CropRatioOptions` `:423`, `h264BaseResolutionOptions` `:476` | `imx585FullHdCropRatioOptions:` |
| 484-523 | **Option lists**: `resolutionOptions` `:484`, `shutterOptions` `:492` (angles/speeds are hard-coded), `fpsOptions` `:498`, lossless-mode gates `:499-510`, `isoOptions` `:511`, `formatDisplayValue`/`Subtext` `:514-523` | | `readonly property var isoOptions` |
| 524-570 | Zoom/pan, dropdown and quick-menu state | `previewZoom` `:524`, `quickMenuOpen` `:535`, `selectedCaptureMode` `:542` | `property bool quickMenuOpen` |
| 571-634 | Quick-menu slots 0-5 (guides, centre marker, peaking, false colour, zebra, grayscale). Taps write `settingsState.*Enabled` `:622-632` | `triggerQuickMenuSlot` `:617` | `function triggerQuickMenuSlot` |
| 646-828 | **FPS limit tables per sensor** (copy of Core, see §4) | `maximumSupportedFpsForResolution` `:733`, `imx477MaximumSupportedFpsForResolution` `:672`, `availableFpsOptions` `:802` | `function maximumSupportedFpsForResolution` |
| 829-1370 | Resolution and size estimate helpers | `estimatedFrameSizeMB` `:896`, `updateMediaEstimate` `:939`, `cropRatioLabelForResolution` `:1016`, `aspectRatioForResolution` `:1138`, `applyResolutionValue` `:1208`, `applyResolutionBase` `:1218`, `applyCropResolution` `:1235`, `normalizedResolutionForCurrentSensor` `:1271`, `ensureValidResolutionSelection` `:1355` | `function ensureValidResolutionSelection` |
| 1372-1478 | Photo timer, burst and sequence | `applyQuickTimelapseInterval` `:1410`, `queueNextPhotoInSequence` `:1439` (→ `capturePhoto` `:1447`), `beginPhotoCaptureSequence` `:1460` | `function beginPhotoCaptureSequence` |
| 1479-1538 | Capture-mode menu (`selectCaptureMode` `:1493`), preview zoom (`toggleHardwarePreviewZoom` `:1528`) | | `function selectCaptureMode` |
| 1539-1655 | **Core sync and record/timelapse requests** | `ensureValidFpsSelection` `:1539`, `syncControlValuesFromBridge` `:1555`, `requestRecordingState` `:1583`, `requestTimelapseState` `:1615` | `function requestRecordingState` |
| 1656-1731 | Warnings, **timecode computed in QML** (`formatTimecode` `:1677`, `updateTimecodeDisplay` `:1692`, `toggleTimecodeMode` `:1709`), false-colour maps `:1717-1731` | | `function updateTimecodeDisplay` |
| 1733-1814 | `timecodeFrames`/`timecode` props `:1733-1734`, date timer, `on*Changed` handlers (photo mode `:1750`, resolution, sensor detection) | | `property string timecode:` |
| 1815-1925 | Connections: `mediaBridge` `:1815`, **`root.controlBridge` `:1824-1897`** (`onFpsChanged` `:1838` … `onPhotoCaptured` `:1888`), `root.bridge` (preview, `onFrameArrived` `:1901`), `root.settingsState` `:1911` | | `target: root.controlBridge` |
| 1926-1960 | Timers (`photoCountdownTimer` `:1947`) | | `id: photoCountdownTimer` |
| 1961-2722 | **PREVIEW AREA** `previewContainer` `:1966` (objectName `:1967`). `CameraPreviewItem` `preview` `:1973-1997` (objectName `previewItem` `:1975`), `StillExposureOverlay` `:1999`, photo flash `:2007-2100`, touch/pan/tap `:2117-2346`, GUIDES `guideOverlay` `:2352` (`selectedAspectRatio` `:2379`), `HorizontalLevelOverlay` `:2506`, `FalseColorLegend` `:2528`, STATUS CHIP `captureStatusChip` `:2550` (`DroppedFrameWarning` `:2569`, timer/burst chips `:2599-2720`, `TimelapseIntervalPicker` `:2675`) | | `objectName: "previewItem"` |
| 2724-2846 | STATIC OVERLAY (cached) `staticOverlay` `:2729`, menu label `:2792` | | `id: staticOverlay` |
| 2848-3561 | DYNAMIC OVERLAY `dynamicOverlay` `:2852`. **Top stats**: `TopDropdownStat` FPS `:2886` (→ `applyFps` `:2910`), ISO `:2918` (`:2942`), shutter `:2950` (`:2975`/`:2981`), WB `:2990` (`:3016`). Quick menu: edge swipe `:3042`, `quickMenuPanel` `:3117`, resolution `:3170-3327` (→ `applyResolutionBase` `:3315`), crop `:3328-3477` (→ `applyCropResolution` `:3458`), slot grid `:3478-3560` | | `id: quickMenuPanel` |
| 3563-3659 | BOTTOM STATS: `InfoLine` FORMAT `:3578`, MEDIA `:3594`, CPU `:3623`, POWER `:3642` | | `label: "MEDIA"` |
| 3660-3979 | TIMECODE and bottom controls: `timecodeMetrics` `:3666`, `bottomControlsRow` `:3673`, `clipBrowserBtn` `:3690`, `audioMeterOverlay` `:3713`, `timecodeBox` `:3727` (tap → `toggleTimecodeMode` `:3763`), RECORD BUTTON `recordBtn` `:3773` (click logic `:3791-3830`), `captureModeMenu` `:3843`, `compactAudioMeterOverlay` `:3901`, `dateTimePageChip` `:3928` | | `id: recordBtn` |
| 3980-4158 | Record-warning scrim and `recordWarningCard` `:4001` | | `id: recordWarningCard` |

### 1.3 `qml/Main.qml` (945 lines)

There is **no StackView**. Pages switch on `currentPage` (`"camera"` / `"browser"` / `"player"`) and `Loader.active`. `CameraPage` is always instantiated. Settings is a retained Loader overlay.

| Lines | Chapter | Key ids / functions | Anchor |
| --- | --- | --- | --- |
| 1-15 | Root `Window`, size from `displayConfigBridge` | | `Window {` |
| 16-34 | Page state: `currentPage` `:16`, `settingsOpen` `:17`, `settingsPageRetained` `:18`, `lastSettingsSection` `:20`, clip selection `:22-25`, power-button popup state `:30-34` | | `property string currentPage` |
| 35-38 | **C++ read contract**: `powerButtonShutdownHoldActive` `:35`, `monitorRecordingActive` `:36`, `monitorTimelapseActive` `:37`, `monitorTimecode` `:38`. They are read by name in `ExternalMonitorRuntimeBridge.cpp:137-153` and `ExternalMonitorManager.cpp:113-300` | | `readonly property bool monitorRecordingActive` |
| 39-61 | Layout flags (`standardLandscapeLayout` = `landscape` or `landscape_large`, `:43-44`), controls opacity/mode, rotation math `:56-61` | `effectiveUiRotationDegrees` `:60` | `effectiveUiRotationDegrees:` |
| 63-86 | `onSettingsOpenChanged` / `onCurrentPageChanged` (retain/release the settings page) | | `onCurrentPageChanged:` |
| 88-211 | Functions: `scheduleSettingsPreload` `:88`, `releaseSettingsBackgroundWork` `:93`, `handleFirstPreviewFrame` `:104`, power-button shutdown `:118-180`, `updateBackgroundAudioMonitoring` `:181`, `startAutoPowerOffWarning` `:188`. `Component.onCompleted` `:204` (`connectToCore()` `:207`) | | `function releaseSettingsBackgroundWork` |
| 213-283 | Connections: preview `onFrameArrived` `:216`; settingsBridge `:227`; sleepManager `:241`; power button and control `:262` (`wakeFromStandby` `:272`) | | `function onButtonPressed` |
| 285-332 | **`hardware_action` router**: `power_button_press`, `standby_power_sleep`, `standby_power_wake`, `zoom_toggle`, `settings` `:314-315`, `clip_browser` `:320-321`, `quick_menu` | | `function onHardwareActionTriggered` |
| 334-415 | Timers: `settingsPreloadTimer` (750 ms) `:334`, `startupServicesTimer` `:346`, `settingsHideTimer` `:353`, `autoPowerOffCountdownTimer` `:364`, `powerButtonShutdownTimer` `:390`; hold animations `:398-415` | | `id: settingsPreloadTimer` |
| 417-467 | Clip navigation: `selectClip` `:417` (→ `"player"` `:423`), `selectClipAt`, `removeSelectedClip` `:445` | | `function selectClip` (2 hits) |
| 469-494 | Fonts, `uiScene` `:474` with the `Rotation` transform | | `id: uiScene` |
| 496-517 | `CameraPage { id: cameraPage }` | | `id: cameraPage` |
| 519-578 | `settingsScrim` `:519`, `settingsPageLoader` `:535` (`active: currentPage==="camera" && settingsPageRetained` `:539`; `SettingsPage` `:567`) | | `id: settingsPageLoader` |
| 580-607 | `clipBrowserPageLoader` (`active: currentPage === "browser"` `:584`) | | `id: clipBrowserPageLoader` |
| 609-640 | `clipPlayerPageLoader` (`"player"` `:613`), back → browser `:634` | | `id: clipPlayerPageLoader` |
| 642-772 | `autoPowerOffWarningCard` `:657` | | `id: autoPowerOffWarningCard` |
| 774-942 | `powerButtonShutdownCard` `:774` | | `id: powerButtonShutdownCard` |

### 1.4 `qml/ClipPlayerPage.qml` (2272 lines)

The page uses only `playbackController`. Members: `playing` (16 uses), `frameCount`, `currentClipName`, `videoClip`, `currentFrameIndex`, `frameSource`, `fastFrameSource`, `histogramBins`, `clipMetadata`, `seekToFrame()` `:102`, `togglePlayback()` `:1126`/`:1610`, `stop()` `:288`/`:2263`.

| Lines | Chapter | Key ids / functions | Anchor |
| --- | --- | --- | --- |
| 1-63 | Props and split-layout size tokens. `splitLandscapePlaybackLayout` = `landscape_medium` `:28` | | `splitLandscapePlaybackLayout:` |
| 64-67 | Signals `backRequested`, `previousClipRequested`, `nextClipRequested`, `deleteRequested` | | `signal deleteRequested` |
| 89-210 | Functions: `scrubPlayback` `:95`, `updateVideoFrame` `:141` (comment `:146` on decoder starvation), `warmPlaybackFrames` `:157`, `beginClipTransition` `:182` | | `function updateVideoFrame` |
| 211-292 | Header: title column, back `backArea` `:285` | | `id: backArea` |
| 294-2271 | `playerPanel` `:295` | | `id: playerPanel` |
| 355-517 | `clipContent` / `playerPreviewFrame` `:360` / `playbackImage` `:382`, fps chip, play state, `frameBadge` `:503` | | `id: playbackImage` |
| 519-667 | Info button, progress bar (`progressBarTrack` `:613`, `progressHandle` `:637`) | | `id: progressHandle` |
| 670-1252 | **Split landscape** (`visible: splitLandscapePlaybackLayout`): `landscapeInfoPanel` `:671`, `landscapePlaybackControls` `:984`, `landscapeHistogramCanvas` `:1201` | | `id: landscapeInfoPanel` |
| 1254-1656 | **Compact/square**: `compactProgressBar` `:1255`, `deleteButton` `:1318`, `histogramCanvas` `:1413`, `compactInfoButton` `:1466`, `transportControls` `:1522` | | `id: transportControls` |
| 1658-1694 | `clipRevealAnim` | | `id: clipRevealAnim` |
| 1696-2053 | Info overlay (`infoOpen`, `infoColumn` `:1739`) | | `id: infoColumn` |
| 2055-2270 | Delete confirm (`deleteConfirmOpen`, `confirmDeleteArea` `:2259`) | | `id: confirmDeleteArea` |

### 1.5 `qml/ExternalMonitorWindow.qml` (1347 lines)

This is a separate root `Window`. It is loaded in-process by `ExternalMonitorManager`, or as the root of the monitor-only process (`main.cpp:155`). Bridges are bare globals: `settingsBridge`, `apertarControlBridge`, `apertarPreviewBridge`, `monitorRuntimeBridge`, `mediaBridge`, `gyroConfigBridge`, `audioMeterBridge`. **In the monitor-only process, `gyroConfigBridge` is absent and `audioMeterBridge` is null** (`main.cpp:147-154`), so every use needs a `typeof` guard.

| Lines | Chapter | Key ids / functions | Anchor |
| --- | --- | --- | --- |
| 5-33 | Root `Window`; shutdown and capture state from `monitorRuntimeBridge` `:9-31` | | `property bool shutdownPopupVisible` |
| 34-180 | **Label/state copies of CameraPage**: `shutterDisplayValue` `:83`, `recordingFormatValue` `:86`, `processedVideoDefaultResolutionValue` `:104`, `formatInfoValue` `:112`, `previewImageAspectRatio` `:115`, `remainingValue` `:119`, `selectedAspectRatio` `:134`, `topMonitorInfoItems` `:163-169` (FORMAT/FPS/ISO/SHUTTER/WB), `timecode` `:172` | | `topMonitorInfoItems:` |
| 181-282 | Functions: `aspectRatioForResolution` `:203`, `formatTimecode` `:214`, `updateTimecodeDisplay` `:225`, HUD layout `:249-266`, `updateHorizontalLevelPolling` `:267` | | `function formatTimecode` |
| 283-349 | Connections (control and preview `:283`, reconnect `:290`), preview `:314`, control `:327`; `freeRunTimecodeTimer` `:344` | | `id: freeRunTimecodeTimer` |
| 351-1211 | `monitorSurface` `:352` | | `id: monitorSurface` |
| 360-390 | `StillExposureOverlay`; `CameraPreviewItem` `preview` `:367` (objectName `externalPreviewItem` `:368`). Assist-feed aid bindings come from `settingsBridge` | | `objectName: "externalPreviewItem"` |
| 392-463 | Photo flash and feedback animation | | `id: externalPhotoCaptureFeedbackAnimation` |
| 465-740 | `guideOverlay` `:466` (about 25 hard-positioned `Rectangle` guide bars) | | `id: guideOverlay` |
| 741-779 | `HorizontalLevelOverlay` `:742`, `FalseColorLegend` `:764` | | `id: horizontalLevelOverlay` |
| 781-1210 | Info HUD (`visible: infoOverlayEnabled && !smpteEnabled` `:785`): `topInfoRow` `:788`, RESOLUTION `:899-940`, `hdmiAudioMeterPanel` `:945`, `statusRow` `:1063`, `DroppedFrameWarning` `:1103`, `timecodeText` `:1127`, REMAINING `remainingColumn` `:1140` | | `id: hdmiAudioMeterPanel` |
| 1213-1346 | Power-button shutdown mirror (scrim `:1213`, card `:1228`) | | `visible: root.shutdownPopupVisible` (2 hits) |

### 1.6 `src/ApertarControlBridge.cpp` (2460 lines)

| Lines | Chapter | Key functions | Anchor |
| --- | --- | --- | --- |
| 15-115 | Anonymous helpers: poll intervals `:17-18`, cDNG compression normalisers `:33-73`, shutter preset snapping `:74-115` | `normalizeCdngCompressionValue` `:33`, `snapToNearestPreset` `:74` | `constexpr int kSteadyStatePollIntervalMs` |
| 116-148 | Constructor (event socket, refresh timer) | | `ApertarControlBridge::ApertarControlBridge(` |
| 149-249 | Property getters | | `QString ApertarControlBridge::fps() const` |
| 250-853 | **Invokables → socket commands** (table in §2.2) | `applyFps` `:255` … `calibrateGyro` `:832` | `bool ApertarControlBridge::apply` (28 hits) |
| 855-883 | `refreshFromCore` (`get_state` `:864`), `updateRefreshTimer` | | `void ApertarControlBridge::refreshFromCore` |
| 884-1012 | **`UI.conf` `camera/*` persistence**: `loadPersistedCameraSettings` `:884`, `saveCurrentCameraSettings` `:973` (53 `camera/` key uses) | | `camera/hasSaved` (2 hits) |
| 1013-1107 | `sendCoreCommand`: socket path `:1032`, request build `:1047`, blocking read loop, timeouts | | `bool ApertarControlBridge::sendCoreCommand` |
| 1108-1181 | Exposure comp/metering, presets (`cameraPresetSettings` `:1118`, `applyCameraPreset` `:1152` → `apply_preset` `:1160`), standby/wake, `user_activity` `:1179` | | `bool ApertarControlBridge::applyCameraPreset` |
| 1182-1260 | **`applyCoreMessage` event router** (events `:1185-1257`) | | `void ApertarControlBridge::applyCoreMessage` |
| 1261-1556 | `applyCoreState`: Core keys → properties | | `void ApertarControlBridge::applyCoreState` |
| 1557-1590 | Event socket connect and read | | `void ApertarControlBridge::processEventSocketMessages` |
| 1591-1760 | Shutter math, `format*Value` display formatters | `formatRecordingFormatValue` `:1672` | `QString ApertarControlBridge::formatResolutionValue` |
| 1761-2216 | `parse*Value`. **`parseResolutionValue` `:1797-2006` is a hard-coded per-string `if` table**; `parseH264ResolutionValue` `:2007`; `parseRecordingFormatValue` `:2063`; AF presets `:2154`; `audioDeviceIdFromSelection` `:2191` | | `bool ApertarControlBridge::parseResolutionValue` |
| 2217-2460 | Setters that emit NOTIFY (`setFps` `:2230` … `setLastError` `:2453`) | | `void ApertarControlBridge::setFps` |

### 1.7 `src/SettingsBridge.cpp` (2314 lines)

| Lines | Chapter | Key functions | Anchor |
| --- | --- | --- | --- |
| 17-284 | Anonymous helpers: value coercion `:19-55`, list parsing `:56-103`, LUT and tuning path normalisers `:104-123`, assist colour `:124`, **search dirs** `lutSearchDirectories` `:140` (`/home/pi/LUTs`, `$APERTAR_MEDIA_ROOT/LUTs`, `/media/RAW/LUTs`, `/media/*/LUTs`) and `tuningFileSearchDirectories` `:164`, `normalizePhotoFormat` `:188`, `normalizePhotoTimelapse` `:223`, `normalizeBatteryType` `:258` | | `QStringList lutSearchDirectories` |
| 285-433 | Constructor: `QSettings("CinePi","UI")` `:287`, normaliser lambdas (Clean/Assist feed `:289-294`), **loads every key `:324-407`**, file watcher and 10 s poll `:411-431` | | `m_settings("CinePi", "UI")` |
| 434-591 | `setControlBridge` `:434`, file state, watch paths, **`pollExternalSettings` `:502-591`** (re-reads every key; second key list) | | `void SettingsBridge::pollExternalSettings` |
| 592-1568 | Getter/setter pairs in header order. Pattern: `if (!m_externalSettingsSyncing) m_settings.setValue("<key>", v); m_settings.sync(); emit …` (zebra `:597-607`) | `setZebraEnabled` `:597` … `setSleepMode` `:1559` | `void SettingsBridge::set<Name>` |
| 807-871 | `refreshLutPreviewOptions` `:807`, `refreshTuningFileOptions` `:842` | | `void SettingsBridge::refreshLutPreviewOptions` |
| 1569-1703 | Section order lists (`monitoringOrder` … `favoritesOrder`) | | `QStringList SettingsBridge::sidebarOrder` |
| 1704-1936 | Preset API: `saveCurrentAsPreset` `:1719`, `loadPreset` `:1745`, `deletePreset` `:1769`, `exportPresetToPath` `:1788`, `importPresetsFromPath` `:1827`, `clearPresetStatus` `:1932` | | `bool SettingsBridge::loadPreset` |
| 1937-2029 | Preset paths (`presetsDirectoryPath` `:1937`: AppData `presets`, else legacy) | | `QString SettingsBridge::presetsDirectoryPath` |
| 2030-2108 | `serializeCurrentSettings` (camera part via `cameraPresetSettings()` `:2091`) | | `QJsonObject SettingsBridge::serializeCurrentSettings` |
| 2109-2191 | `applySettingsObject` (camera part via `applyCameraPreset` `:2117` → `apply_preset`) | | `bool SettingsBridge::applySettingsObject` |
| 2192-2314 | Preset file IO, `reloadPresetNames` `:2267`, `setPresetStatus` `:2306` | | `void SettingsBridge::reloadPresetNames` |

### 1.8 `src/PreviewWindowRenderer.cpp` (2466 lines)

| Lines | Chapter | Key functions | Anchor |
| --- | --- | --- | --- |
| 31-186 | Helpers: `runningOnRaspberryPi3` `:33`, `envFlagEnabled` `:43`, `PreviewUvRect` `:73`, `uploadLumaPlane` `:120` | | `bool runningOnRaspberryPi3` |
| 187-289 | `.cube` LUT atlas parser | `parseLutAtlasFile` `:187` | `::parseLutAtlasFile` (2 hits) |
| 290-341 | Constructor/destructor; env fallbacks `APERTAR_PREVIEW_FORCE_{CPU,PLANAR,EGL}` `:296-301` | | `APERTAR_PREVIEW_FORCE_CPU` (2 hits) |
| 342-475 | Qt wiring: `scheduleWindowUpdate` `:342`, `setPreviewItem` `:357`, `handleWindowChanged` `:384`, `syncState` `:410` (CameraPreviewItem → GL state), `connectBridgeSignals` `:428`, dma-buf fd helpers `:446-475` | | `void PreviewWindowRenderer::syncState` |
| 476-677 | GL init, `compileShader` `:485`, LUT textures `:503-642`, `bindExposureReference` `:643` | | `bool PreviewWindowRenderer::ensureLutTexture` |
| 678-1224 | **`initializePipeline`, the GLSL sources.** `vs` `:681`, `fsPreamble` `:692`, `fsCommon` `:702`: `exposureReferenceRgb` `:730`, `applyPreviewLut` `:740`, SMPTE `:764-807`, false colour `:808-853` (mode switch `:884-890`), peaking `peakingLuminance` `:854` / `edgeStrength` `:857` (**texel hard-coded 1/1920 x 1/1080 `:858`**), `main` `:867`; passthrough `:914`; external-OES vs planar source `:920`/`:927`; program link `:975-1016`; uniform lookups `:1117-1166` | | `static const char *fsCommon` |
| 1225-1293 | `ensurePreviewTarget` `:1225`, `cleanupImportedBuffers` `:1261` | | `void PreviewWindowRenderer::cleanupImportedBuffers` |
| 1294-1603 | Fallbacks: `uploadPlanarYuvTexture` `:1294`, `uploadCpuFallbackTexture` `:1411`, `ensurePlanarProcessingTexture` `:1581` | | `bool PreviewWindowRenderer::uploadCpuFallbackTexture` |
| 1604-1856 | **`ensureImported`**: dma-buf → EGLImage → `GL_TEXTURE_EXTERNAL_OES` | | `void PreviewWindowRenderer::ensureImported` |
| 1857-1968 | Geometry: `previewDisplayAspect` `:1857`, `previewRectInPixels` `:1873`, cache state `:1892-1968` | | `PreviewWindowRenderer::previewRectInPixels` |
| 1969-2387 | `renderProcessedPreview` `:1969`, `blitPreviewToWindow` `:2165`, `renderDirectToWindow` `:2194` | | `void PreviewWindowRenderer::renderProcessedPreview` |
| 2388-2466 | `render()` (the `beforeRenderPassRecording` entry point) | | `void PreviewWindowRenderer::render()` |

### 1.9 `src/main.cpp` (521 lines)

| Lines | Chapter | Anchor |
| --- | --- | --- |
| 1-45 | Includes | `#include "ExternalMonitorManager.hpp"` |
| 46-130 | Screen helpers: `screenIsHdmi` `:46`, `screenLooksLikeInternalPanel` `:61`, `internalTouchPanelPresent` `:75`, `mainUiScreenForNormalMode` `:90`, `externalMonitorScreen` `:121` | `QScreen *mainUiScreenForNormalMode` |
| 131-237 | `runMonitorOnly`: bridges `:133-144`, **monitor-only context properties `:147-154`**, load `ExternalMonitorWindow.qml` `:155`, `findChild("externalPreviewItem")` `:176-177`, `connectToCore` `:228` | `int runMonitorOnly` |
| 241-273 | `main`: GLES format, `QSG_RENDER_LOOP=basic` `:255-256`, `setDefaultFormat` `:265` | `int main(int argc` |
| 274-276 | `qmlRegisterType<CameraPreviewItem>("Apertar",1,0,…)` `:274`; `APERTAR_MONITOR_ONLY` branch `:275` | `qmlRegisterType<CameraPreviewItem>` |
| 278-349 | Bridge construction `:278-307`, signal fan-out (`userActivity` → `notifyUserActivity` `:330`), standby reconnect `:346` | `SleepManager::userActivity` |
| 350-373 | Image providers `cdng`/`cdngthumb`/`cdngplay`/`video`/`videothumb` `:354-360` | `addImageProvider` (5 hits) |
| 374-397 | **Normal-mode context properties `:374-396`**, `engine.load(Main.qml)` `:397` | `setContextProperty("settingsBridge"` (2 hits) |
| 405-420 | `core-start-ready` file | `APERTAR_CORE_START_READY_FILE` |
| 428-459 | Screen choice, `hdmiExternalOnly`, `windowed` | `mainUiScreenForNormalMode()` (2 hits) |
| 463-499 | `main-ui-ready` on the first `frameSwapped` `:499` | `APERTAR_UI_READY_FILE` |
| 502-518 | `findChild("previewContainer"/"previewItem")` `:502-503`, `PreviewWindowRenderer` `:510`, `ExternalMonitorManager` `:513-518` | `findChild<CameraPreviewItem *>("previewItem")` |

---

## 2. QML ↔ C++ binding table

### 2.1 Registrations in `src/main.cpp`

The only registered QML type is `CameraPreviewItem`. Everything else is a context property.

| QML name | C++ class (decl) | Normal mode line | Monitor-only line |
| --- | --- | --- | --- |
| `import Apertar 1.0` → `CameraPreviewItem` | `CameraPreviewItem` (`src/CameraPreviewItem.hpp:8`) | `:274` (`qmlRegisterType`) | same (registered before the branch) |
| `apertarPreviewBridge` | `ApertarPreviewSocketClient` (`ApertarPreviewSocketClient.hpp:15`) | `:374` | `:147` |
| `statsBridge` | `SystemStatsBridge` (`SystemStatsBridge.hpp:6`) | `:375` | absent |
| `deviceInfoBridge` | `DeviceInfoBridge` (`DeviceInfoBridge.hpp:6`) | `:376` | absent |
| `displayConfigBridge` | `DisplayConfigBridge` (`DisplayConfigBridge.hpp:6`) | `:377` | `:151` |
| `systemActionBridge` | `SystemActionBridge` (`SystemActionBridge.hpp:7`) | `:378` | absent |
| `displayCalibrationBridge` | `DisplayCalibrationBridge` (`DisplayCalibration.hpp:20`) | `:379` | absent (constructed `:144`, not exposed) |
| `powerButtonBridge` | `PowerButtonBridge` (`PowerButtonBridge.hpp:9`) | `:380` | absent |
| `sleepManager` | `SleepManager` (`SleepManager.hpp:9`) | `:381` | absent |
| `mediaBridge` | `MediaStatusBridge` (`MediaStatusBridge.hpp:12`) | `:382` | `:150` = **`ExternalMonitorRuntimeBridge`** (different class, same name) |
| `powerBridge` | `Ina219Bridge` (`Ina219Bridge.hpp:7`) | `:383` | absent |
| `gyroConfigBridge` | `GyroConfigBridge` (`GyroConfigBridge.hpp:9`) | `:384` | **absent** |
| `wifiBridge` | `WifiBridge` (`WifiBridge.hpp:10`) | `:385` | absent |
| `audioDeviceBridge` | `AudioDeviceBridge` (`AudioDeviceBridge.hpp:14`) | `:386` | absent |
| `audioMeterBridge` | `AudioMeterBridge` (`AudioMeterBridge.hpp:12`) | `:387` | `:153-154` = **null** |
| `apertarControlBridge` | `ApertarControlBridge` (`ApertarControlBridge.hpp:12`) | `:388` | `:148` |
| `settingsBridge` | `SettingsBridge` (`SettingsBridge.hpp:13`) | `:389` | `:149` |
| `hdmiExternalOnly` | plain `bool` | `:390` | absent |
| `clipModel` | `ClipListModel` (`cliplistmodel.h:7`) | `:391` | absent |
| `playbackController` | `PlaybackController` (`playbackcontroller.h:18`) | `:392` | absent |
| `cdngThumbProvider` / `cdngPlayProvider` | `CdngImageProvider` (`cdngimageprovider.h:13`) | `:393` / `:394` | absent |
| `videoProvider` | `VideoImageProvider` (`VideoPlayback.hpp:22`) | `:395` | absent |
| `monitorRuntimeBridge` | `ExternalMonitorRuntimeBridge` (`ExternalMonitorRuntimeBridge.hpp:15`) | `:396` (Publisher) | `:152` (Subscriber) |

**Implicit name contracts (C++ ↔ QML by string).**

| C++ looks up | QML definition |
| --- | --- |
| `findChild<QQuickItem*>("previewContainer")` `main.cpp:502` | `CameraPage.qml:1967` |
| `findChild<CameraPreviewItem*>("previewItem")` `main.cpp:503` | `CameraPage.qml:1975` |
| `findChild<CameraPreviewItem*>("externalPreviewItem")` `main.cpp:176-177`, `ExternalMonitorManager.cpp:231` | `ExternalMonitorWindow.qml:368` |
| `property("currentPage")`, `property("standbyActive")`, `property("powerButtonShutdown*")`, `property("monitor*")` in `ExternalMonitorManager.cpp:113-300` and `ExternalMonitorRuntimeBridge.cpp:137-153` | `Main.qml:16`, `:27`, `:30-38` |

### 2.2 `ApertarControlBridge` (`src/ApertarControlBridge.hpp`)

All 43 properties are **read-only** (NOTIFY only). Writes go through invokables.

**Q_PROPERTY (header line):** fps:16, iso:17, shutterAngle:18, shutterSpeed:19, whiteBalance:20, whiteBalanceAvailable:21, exposureCompensation:22, exposureCompensationAvailable:23, autoExposureEnabled:24, exposureMetering:25, exposureMeteringOptions:26, resolution:27, recordingFormat:28, proresProfile:29, proresColorProfile:30, cdngPreviewColorProfile:31, previewExposureReference:32, cdngCompression:33, rawCompressionSupported:34, rawRecordingSupported:35, proresSupported:36, h264HardwareEncoding:37, h264MaxWidth:38, h264MaxFps:39, tuningFile:40, rawBitDepth:41, h264Resolution:42, sensorName:43, autofocusMode:44, autofocusRange:45, autofocusSpeed:46, autofocusWindow:47, recording:48, recordingHasDroppedFrames:49, standby:50, timelapseActive:51, timelapseShotCount:52, stillExposureActive:53, mediaWritesPending:54, stillExposureRemainingSeconds:55, audioInputLevel:56, connected:57, lastError:58.

**Non-NOTIFY signals used by QML:** `recordingFailed`, `gyroCalibrationFinished`, `timelapseFrameCaptured`, `photoCaptured`, `photoCaptureFailed`, `externalRecordingPreparationRequested`, `hardwareActionTriggered` (header `:146-182`).

| Q_INVOKABLE | .hpp | .cpp | Core command(s) | Core handler (`Core:src/ApertarCoreApp.cpp`) |
| --- | --- | --- | --- | --- |
| `enterStandby()` | 98 | 1166 | `enter_standby` | 9138 |
| `wakeFromStandby()` | 99 | 1171 | `wake` | 9174 |
| `notifyUserActivity()` | 100 | 1176 | `user_activity` (event socket, id -2, no reply) | 9118 |
| `refresh()` | 110 | 250 | `get_state` (async, via `refreshFromCore` `:864`) | 9218 |
| `applyFps(s)` | 111 | 255 | `set_fps`, then `set_shutter_us` | 9275, 9284 |
| `applyIso(s)` | 112 | 291 | `set_iso` / `set_iso_auto` | 9242 / 9269 |
| `applyExposureCompensation(ev)` | 113 | 1108 | `set_exposure_compensation` | 9251 |
| `applyExposureMetering(s)` | 114 | 1113 | `set_exposure_metering` | 9260 |
| `applyShutterAngle(s)` | 115 | 318 | `set_shutter_us` / `set_shutter_auto` | 9284 / 9293 |
| `applyShutterSpeed(s)` | 116 | 348 | `set_shutter_us` / `set_shutter_auto` | 9284 / 9293 |
| `applyWhiteBalance(s)` | 117 | 377 | `set_wb {kelvin}` / `set_wb_auto` | 9299 / 9308 |
| `applyResolution(s)` | 118 | 408 | `set_resolution` | 9314 |
| `applyRecordingFormat(s)` | 119 | 429 | `set_record_format`, `set_lossy_dng_ratio`, `set_prores_profile` | 9326, 9351, 9378 |
| `applyProresProfile(s)` | 120 | 494 | `set_prores_profile` | 9378 |
| `applyProresColorProfile(s)` | 121 | 477 | `set_prores_color_profile` | 9369 |
| `applyCdngPreviewColorProfile(s)` | 122 | 486 | `set_cdng_preview_color_profile` | 9360 |
| `applyCdngCompression(s)` | 123 | 516 | `set_record_format` + `set_lossy_dng_ratio`, or `set_cdng_compression` | 9326, 9351, 9340 |
| `applyTuningFile(path)` | 124 | 550 | `set_tuning_file` | 9388 |
| `applyRawBitDepth(s)` | 125 | 576 | `set_raw_bit_depth` | 9397 |
| `applyH264Resolution(s)` | 126 | 601 | `set_h264_resolution` | 9412 |
| `applyTimecodeMode(s)` | 127 | 622 | `set_timecode_mode` | 9424 |
| `applyAutofocusMode/Range/Speed/Window` | 128-131 | 638/654/670/686 | `set_af_mode` / `set_af_range` / `set_af_speed` / `set_af_window` | 9439 / 9448 / 9457 / 9466 |
| `applyPhotoTimelapse(v, fmt)` | 132 | 712 | `set_photo_timelapse` | 9946 |
| `applyPhotoModeEnabled(b)` | 133 | 724 | `set_photo_mode_enabled` | 9573 |
| `applyCaptureMode(s)` | 134 | 731 | `set_capture_mode` | 9537 |
| `applyPhotoLongExposureEnabled(b)` | 135 | 736 | `set_photo_long_exposure_enabled` | 9623 |
| `applyPhotoBracketingEnabled(b)` | 136 | 743 | `set_photo_bracketing_enabled` | 9600 |
| `applyPhotoBracketingEv(ev)` | 137 | 817 | `set_photo_bracketing_ev` | 9612 |
| `setTimelapseActive(b, v, fmt)` | 138 | 750 | `timelapse_start` / `timelapse_stop` | 10740 / 10775 |
| `setRecording(b)` | 139 | 777 | `record_start` (audio/gyro args read from `UI.conf` `:783-807`) / `record_stop` | 10623 / 10783 |
| `capturePhoto(fmt, n)` | 140 | 822 | `capture_photo` | 10716 |
| `calibrateGyro()` | 141 | 832 | `calibrate_gyro` | 9705 |
| (not invokable) `applyCameraPreset(obj)` | — | 1152 | `apply_preset` `:1160` | 10230 |

Core handler lines are the `command.name == "…"` branch inside `ApertarCoreApp::handleCommand` (`:9091`). For gated commands, the earlier hits at `:9095-9113` are pre-dispatch gates, not handlers.

### 2.3 `SettingsBridge` (`src/SettingsBridge.hpp`)

It sends **no** socket commands of its own. Presets reach Core only through `ApertarControlBridge::applyCameraPreset` (`apply_preset`).

**Q_PROPERTY (all READ+WRITE unless marked R):** zebraEnabled:17, zebraThreshold:18, focusPeakingEnabled:20, focusPeakingThreshold:21, focusPeakingColor:23, grayscaleEnabled:25, smpteEnabled:26, anamorphicDesqueezeEnabled:27, anamorphicRatio:28, falseColorEnabled:30, falseColorMode:31 (int), lutPreviewEnabled:32, lutPreviewFile:33, lutPreviewOptions:34 R, tuningFileOptions:35 R, horizontalLevelEnabled:36, horizontalLevelColor:37, guidesEnabled:39, guidesType:40, guidesThickness:41, centerMarkerEnabled:42, centerMarkerType:43, uiOrientation:44, cameraControlsOpacity:45, cameraControlsMode:46, externalMonitorEnabled:47, externalMonitorMode:48, externalMonitorInfoOverlay:49, externalMonitorOrientation:50, dateTimeOverlayEnabled:51, timecodeMode:52, photoModeEnabled:53, photoLongExposureEnabled:54, photoBracketingEnabled:55, photoBracketingEv:56, photoTimer:57, photoBurst:58, photoFormat:59, photoTimelapse:60, soundRecorderEnabled:61, recordAudioEnabled:62, recordGyroEnabled:63, liveAudioMonitoringEnabled:64, audioMeterEnabled:65, audioInputDevice:66, audioOutputDevice:67, audioSampleFormat:68, audioSampleRate:69, audioChannels:70, inputVolume:71, headphoneVolume:72, batteryType:73, batteryCapacity:74, customBatteryWh:75, customBatteryFullVoltage:76, customBatteryEmptyVoltage:77, sleepMode:78, standbyTimeoutSeconds:79, standbyUsbPowerOff:80, monitoringOrder:81, recordOrder:82, audioOrder:83, powerOrder:84, systemOrder:85, wifiOrder:86, infoOrder:87, sidebarOrder:88, favoritesOrder:89, presetNames:90 R, presetStatusText:91 R, presetStatusError:92 R.

| Q_INVOKABLE | .hpp | .cpp | Core command | QML caller |
| --- | --- | --- | --- | --- |
| `refreshLutPreviewOptions()` | 139 | 807 | — (filesystem scan) | `monitoringLutPreviewComponent` |
| `refreshTuningFileOptions()` | 142 | 842 | — | `recordTuningFileComponent` |
| `saveCurrentAsPreset(name)` | 299 | 1719 | — (reads camera via `cameraPresetSettings`) | `SettingsPage.qml:2000` |
| `loadPreset(name)` | 300 | 1745 | `apply_preset` (indirect, `SettingsBridge.cpp:2117` → `ApertarControlBridge.cpp:1160`) | `SettingsPage.qml:2013` |
| `deletePreset(name)` | 301 | 1769 | — | `:2025`, `:2044` |
| `exportPresetToPath(name, mount)` | 302 | 1788 | — | `:2019` |
| `importPresetsFromPath(mount)` | 303 | 1827 | — | `:2007` |
| `clearPresetStatus()` | 304 | 1932 | — | `:1983`, `:2032` |

### 2.4 `MediaStatusBridge` (`src/MediaStatusBridge.hpp`)

Commands go through `coreMediaCommand` (`MediaStatusBridge.cpp:20`): a per-command socket with fixed id 42001.

**Q_PROPERTY:** mediaMounted:15, mountPath:16 (CONSTANT), statusText:17, lastActionError:18, frameSizeMB:20 (W, set by CameraPage), fps:21 (W), freeBytes:22, totalBytes:23, remainingSeconds:24, remainingMinutesText:25, remainingStills:26, remainingStillsText:27, writeSpeedTestRunning:28, lastWriteSpeedMBps:29, writeSpeedResultText:30, writeSpeedDetailText:31, writeSpeedError:32, mediaTypeLabel:33, mediaPromptLabel:34, mountableDrives:35, mountableDriveOptions:36.

| Q_INVOKABLE | .hpp | .cpp | Core command | Core handler |
| --- | --- | --- | --- | --- |
| `ejectMedia()` | 69 | 1180 | `eject_media` (60 s, `:1183`) | 10589 |
| `formatMedia(fs)` | 70 | 1189 | `format_media {filesystem}` (360 s, `:1192`) | 10579 |
| `startWriteSpeedTest()` | 71 | 1198 | `run_media_speed_test` (`:1201`), then polls `get_media_test_state` (`pollCoreWriteSpeedTest` `:1210`, send `:1214`) | 10616 / 10608 |
| `refreshMountableDrives()` | 72 | 675 | — (`lsblk`) | |
| `setDriveDiscoveryActive(b)` | 73 | 288 | — | |
| `mountDrive(dev)` | 74 | 1105 | — (`sudo -n mount`) | |
| `mountDriveByDisplayName(s)` | 75 | 1160 | — | |

### 2.5 `DisplayConfigBridge` (`src/DisplayConfigBridge.hpp`)

All properties are CONSTANT, read once from `[display]`. There are **no invokables**.

uiWidth:9, uiHeight:10, uiLayout:11, uiRotationDegrees:12, controlsOpacity:13, zoomToggleFactor:14, windowed:15, hdmiExternalOnly:16, squareLayout:17, landscapeLayout:18, compactLandscapeLayout:19, regularLandscapeLayout:20, portraitLayout:21, compactPortraitLayout:22, configPath:23.

### 2.6 `GyroConfigBridge` (`src/GyroConfigBridge.hpp`)

It sends no Core command. It reads and writes `[imu]` in `apertar-hardware.conf` and polls I2C itself. Gyro calibration goes through `apertarControlBridge.calibrateGyro()`.

**Q_PROPERTY:** driver:12, syncMode:13, orientation:14, syncOffsetMs:15, syncOffsetText:16, sampleRateHz:17, configPath:18, livePollingEnabled:19 (W), livePollingIntervalMs:20 (W), liveAccelOnly:21 (W), liveAvailable:22, liveStatusText:23, accelXG:24, accelYG:25, accelZG:26, gyroXDps:27, gyroYDps:28, gyroZDps:29, accelRangeG:30, gyroRangeDps:31, levelReferenceSet:32, levelReferenceText:33, levelAccelXG:34, levelAccelYG:35, levelAccelZG:36.

| Q_INVOKABLE | .hpp | .cpp |
| --- | --- | --- |
| `refresh()` | 68 | 668 |
| `setDriverName(s)` | 69 | 680 |
| `setLivePollingEnabled(b)` | 70 | 699 |
| `setLivePollingIntervalMs(n)` | 72 | 725 |
| `setLiveAccelOnly(b)` | 73 | 736 |
| `setLivePollingRequest(owner, …)` | 74 | 746 |
| `setLevelReference()` | 78 | 803 |
| `clearLevelReference()` | 79 | 842 |
| `setOrientation(s)` | 80 | 862 |
| `setSyncOffsetMs(v)` | 81 | 881 |
| `adjustSyncOffsetMs(d)` | 82 | 895 |
| `resetSyncOffset()` | 83 | 900 |

### 2.7 `WifiBridge` (`src/WifiBridge.hpp`)

It sends no Core command. It runs `nmcli` and keeps `hotspotSsid`/`hotspotPassword` in `UI.conf` (`WifiBridge.cpp:130-134`, `:252`, `:262`; defaults `Apertar`/`apertarcam` `:497-498`).

**Q_PROPERTY:** networks:14, scanning:15, connecting:16, wifiAvailable:17, wifiEnabled:18, statusText:19, currentSsid:20, wifiDevice:21, hotspotActive:22, hotspotSsid:23 (W), hotspotPassword:24 (W), hotspotStatusText:25, lastError:26.

| Q_INVOKABLE | .hpp | .cpp |
| --- | --- | --- |
| `refresh()` | 47 | 169 |
| `setWifiEnabled(b)` | 48 | 186 |
| `connectToNetwork(ssid, pw)` | 49 | 200 |
| `disconnectCurrent()` | 50 | 229 |
| `startHotspot()` | 51 | 266 |
| `stopHotspot()` | 52 | 323 |

---

## 3. Reverse index: Core socket command → sender → QML trigger

Socket path default `/tmp/apertar-core.sock`. `APERTAR_CONTROL_SOCKET` overrides it for the control, media, audio and
system bridges (`ApertarControlBridge.cpp:1168`, `:1805`@c153c33), not for the preview client: its path is the
argument of `connectToCore` (`ApertarPreviewSocketClient.hpp:30`).

| Command | Sent from | Triggered by (QML) |
| --- | --- | --- |
| `set_fps` (+`set_shutter_us`) | `ApertarControlBridge.cpp:270` (`:283`) | FPS `TopDropdownStat` `CameraPage.qml:2910`. `ensureValidFpsSelection` `:1549` would send it on sensor, resolution and format changes (`:334`, `:567`, `:1765-1811`), but it returns at once while a control bridge exists (`:1540-1541`), as on the rig |
| `set_iso` / `set_iso_auto` | `:309` / `:294` | ISO dropdown `CameraPage.qml:2942` |
| `set_shutter_us` / `set_shutter_auto` | `:339`, `:368` / `:321`, `:351` | Shutter dropdown `CameraPage.qml:2981` (angle), `:2975` (speed, photo mode) |
| `set_wb` / `set_wb_auto` | `:399` / `:384` | WB dropdown `CameraPage.qml:3016` |
| `set_resolution` | `:417` | Quick menu `applyResolutionBase` `CameraPage.qml:3315` / `applyCropResolution` `:3458` → `applyResolutionValue` `:1211`; `ensureValidResolutionSelection` `:1366` (returns at once while a control bridge exists, `:1357-1358`); Settings Format card `SettingsPage.qml:3170`/`:3191` → `applyRecordResolutionValue` `:630` |
| `set_h264_resolution` | `:610` | `CameraPage.qml:1224`, `:1241`; `SettingsPage.qml:3166`, `:3188` (`recordFormatComponent`) |
| `set_record_format` (+`set_lossy_dng_ratio`, `set_prores_profile`) | `:457` (`:460`, `:468`) | Format choice `SettingsPage.qml:3210` |
| `set_prores_profile` | `:508` | `SettingsPage.qml:3235` |
| `set_raw_bit_depth` | `:590` | `SettingsPage.qml:3240` |
| `set_cdng_compression` / `set_lossy_dng_ratio` / `set_record_format` | `:537` / `:530` / `:528`, `:535` | cDNG compression choice `SettingsPage.qml:3260` |
| `set_prores_color_profile` | `:482` | `SettingsPage.qml:3284` |
| `set_cdng_preview_color_profile` | `:491` | `SettingsPage.qml:3306` |
| `set_tuning_file` | `:565` | `SettingsPage.qml:3458` (`recordTuningFileComponent`) |
| `set_timecode_mode` | `:630` | Timecode card `SettingsPage.qml:3778`; tap on `timecodeBox` `CameraPage.qml:3763` → `toggleTimecodeMode` `:1714` |
| `set_af_mode` / `_range` / `_speed` / `_window` | `:646` / `:662` / `:678` / `:697` | `SettingsPage.qml:3813` / `:3827` / `:3841` / `:3855` |
| `set_exposure_compensation` / `set_exposure_metering` | `:1110` / `:1115` | `SettingsPage.qml:3093` / `:3107` |
| `set_photo_mode_enabled` | `:728` | Still Mode toggle `SettingsPage.qml:2985`; Sound Recorder `:3058` |
| `set_photo_long_exposure_enabled` | `:738` | `SettingsPage.qml:2944` |
| `set_photo_bracketing_enabled` / `_ev` | `:745` / `:819` | `SettingsPage.qml:2953` / `:3016` |
| `set_photo_timelapse` | `:721` | `CameraPage.qml:1414` (`applyQuickTimelapseInterval` ← `TimelapseIntervalPicker` `:2689`); `SettingsPage.qml:698` (`applyPhotoTimelapse` ← `customIntervalPopup` `:237`, Still Mode `:3003`, `:3021`) |
| `set_capture_mode` | `:733` | Capture-mode menu `CameraPage.qml:3892` → `selectCaptureMode` `:1496` |
| `record_start` / `record_stop` | `:810` | `recordBtn` click `CameraPage.qml:3822`/`:3824` → `requestRecordingState` `:1588`; auto-stop on entering photo mode `:1752` |
| `timelapse_start` / `timelapse_stop` | `:763` | `recordBtn` in timelapse mode `CameraPage.qml:3800` → `requestTimelapseState` `:1633`; auto-stop `:1758` |
| `capture_photo` | `:829` | `recordBtn` in photo mode `CameraPage.qml:3809` → `beginPhotoCaptureSequence` `:1460` → `queueNextPhotoInSequence` `:1447` (also repeats from `photoCountdownTimer` `:1942`) |
| `calibrate_gyro` | `:835` | Gyro card button `SettingsPage.qml:3725` → `startGyroCalibration` `:1627` → Timer `:1387` → `:1399` |
| `apply_preset` | `:1160` | Preset Apply `SettingsPage.qml:6911` → `applyPresetByName` `:2010` → `settingsState.loadPreset` `:2013` → `SettingsBridge.cpp:2117` |
| `enter_standby` | `:1168` | `standbyButton` `SettingsPage.qml:5420` |
| `wake` | `:1173` | `Main.qml:272` (power-button Connections) |
| `user_activity` | `:1179` (event socket) | No QML. `SleepManager::userActivity` → `main.cpp:330` |
| `get_state` | `:864` | No QML. Refresh timer (1 s / 30 s) and `refresh()` |
| `preview_subscribe` | `ApertarPreviewSocketClient.cpp:147` | `apertarPreviewBridge.connectToCore()`: `Main.qml:207`, `ExternalMonitorWindow.qml:290`, `main.cpp:228`, `:346` |
| `audio_capabilities` | `AudioDeviceBridge.cpp:330` (`refreshCaptureCapabilities` `:317`) | `SettingsPage.qml:2141` (`updateSectionActivity`), `:3936`, `:3989` (`audioOptionsComponent`) |
| `eject_media` | `MediaStatusBridge.cpp:1183` | Eject confirm `SettingsPage.qml:9074` → `executeEjectMedia` `:1681` |
| `format_media` | `MediaStatusBridge.cpp:1192` | Format confirm `SettingsPage.qml:8840` → `executeFormatMedia` `:1697` |
| `run_media_speed_test` | `MediaStatusBridge.cpp:1201` | `systemMediaSpeedComponent` `SettingsPage.qml:5323` |
| `get_media_test_state` | `MediaStatusBridge.cpp:1214` | No QML. Poll inside `pollCoreWriteSpeedTest` `:1210` |

**Events the UI consumes** (`ApertarControlBridge::applyCoreMessage`, `:1182-1260`): `photo_write_error` `:1185`; `standby` / `still_exposure` / `timelapse_progress` / `media_write_state` `:1191-1192`; `audio_level` `:1196`; `recording` `:1201`; `recording_health` `:1213`; `timelapse` `:1218`; `timelapse_frame` `:1235`; `photo_capture` `:1240`; `prepare_recording` `:1245`; `hardware_action` `:1250` (→ `Main.qml:285-332`); `settings` `:1257`.

---

## 4. Duplicated truths

Each row lists every copy that must change together.

| Truth | Copies (path:line) | Risk |
| --- | --- | --- |
| **Per-sensor resolution and crop lists** | `qml/SettingsPage.qml:110-225`; `qml/CameraPage.qml:377-483`; `qml/CameraPage.qml:484-490` (inline imx577 list); `src/ApertarControlBridge.cpp:1797-2006` (`parseResolutionValue`, string → WxH); Core: `Core:src/camera/CameraController.cpp:2289` (`sensorModeCandidatesForRequestedResolution`), `:385` (`isImx585Raw12CropResolution`), `Core:src/ApertarCoreApp.cpp:1182` (`availablePcfResolutionOptions`), `Core:src/web/WebControlPage.cpp:5068`, `:5120`, `:5268`, `:5372` (WebUI JS) | A new mode needs about 6 edits. A string missing from `parseResolutionValue` fails silently |
| **Resolution helper functions** | Same names in both QML files: `isFourKResolution` (`SettingsPage.qml:332` / `CameraPage.qml:956`), `cropRatioLabelForResolution` (`:392` / `:1016`), `sensorBaseResolutionForValue` (`:453` / `:1077`), `sensorCropOptionsForBase` (`:474` / `:1098`), `h264CropOptionsForBase` (`:523` / `:1167`), `normalizedRecordResolution` `SettingsPage:564` vs `normalizedResolutionForCurrentSensor` `CameraPage:1271` | The copies drift independently |
| **Max-fps per resolution** | `qml/CameraPage.qml:646-828` (`maximumSupportedFpsForResolution` `:733`, e.g. `101.68` `:736`); `Core:src/camera/CameraController.cpp:2493`, `:2629` (`:2659`); `Core:src/ApertarCoreApp.cpp:1076` (`maximumPcfFpsForSettings`, `:1084`); `Core:src/web/WebControlPage.cpp:4830-4876`, `:4935` | The UI offers an fps that Core clamps (`CameraController.cpp:2740`) |
| **Shutter angle/speed and ISO option lists** | `CameraPage.qml:492-497` (shutterOptions), `:511` (isoOptions, with lossless ISO limit); `ApertarControlBridge.cpp:74-115` (preset snapping) | Snapping tolerance must cover every listed angle |
| **Record-format names** | `SettingsPage.qml:3199-3206` (`cDNG`/`MLV`/`H.264`/`ProRes`); `CameraPage.qml:347-353`, `:517-523` (`formatDisplaySubtext`); `ApertarControlBridge.cpp:2063` (`parseRecordingFormatValue`), `:1672` (`formatRecordingFormatValue`), `:33-73` (cDNG compression aliases); `ExternalMonitorWindow.qml:86`, `:112` | Display labels and wire values are mapped in C++ and re-derived in two QML files |
| **cDNG compression values** (`none`, `lossless_jpeg`, `lossy_3to1`, `lossy_5to1`) | `SettingsPage.qml:3252`; `CameraPage.qml:360`, `:499-510`, `:519-523`; `ApertarControlBridge.cpp:33-73` | |
| **Photo formats** | `SettingsPage.qml:226-227`; `SettingsBridge.cpp:188` (`normalizePhotoFormat`); `Core:src/ApertarCoreApp.cpp:445` (`normalizePhotoFormatValue`) | |
| **Timelapse intervals** | `qml/TimelapseIntervals.js` (imported by `CameraPage.qml:3`, `SettingsPage.qml:4`, `TimelapseIntervalPicker.qml:2`, `TimelapseIntervalDialog.qml:3`); `SettingsBridge.cpp:223`; `Core:src/ApertarCoreApp.cpp:472` | The JS is shared inside the UI. Core normalises separately |
| **`UI.conf` `[General]` keys** (66 keys) | Reader/writer `SettingsBridge.cpp:324-407` (load), `:520-578` (poll), setters `:603-1700`; second UI reader `ApertarControlBridge.cpp:783-791` (`record_start` args: soundRecorderEnabled, recordAudioEnabled, recordGyroEnabled, liveAudioMonitoringEnabled, inputVolume, headphoneVolume, audioInput/OutputDevice); `WifiBridge.cpp:130-134` (hotspot*). Core: `Core:src/ApertarCoreApp.cpp:1641` (`readSharedUiSettings`, keys `:1672-1805`, defaults struct around `:1621-1629`), `:1850` (`updateSharedUiGeneralSettings`, the writer), `:6522` (`buildCurrentPresetPayload`, `:6578-6659`), `:9485-9530` (WebUI `handleUiToggle` map), `:10420-10520` (`apply_preset` UI updates) | A key renamed on one side is silently ignored on the other. Defaults currently agree (liveAudioMonitoring=true, inputVolume=60, headphoneVolume=55) |
| **`UI.conf` `camera/*` keys** (UI-only camera persistence) | `ApertarControlBridge.cpp:884-1012` | Only the UI uses these; Core has no `camera/` reads |
| **Preset JSON schema and directory** | `SettingsBridge.cpp:2030-2191` (UI keys), `ApertarControlBridge.cpp:1118-1165` (camera part); `SettingsBridge.cpp:1937` (dir); Core `Core:src/ApertarCoreApp.cpp:6522` (payload), `:10230` (`apply_preset`), `:5220-5228` (candidate preset dirs `Apertar-UI/presets`, `ApertarUI/presets`, `~/.config/CinePi/UI/presets`) | |
| **Settings item ids and order** | `SettingsPage.qml:771-878` (default orders), dispatch `:2216-2384`, titles `sectionItemTitle` `:1064`, icons `sidebarIconForId` `:1129`, `sourceSectionForItemId` `:1161`; stored in `UI.conf` `*Order` keys (`SettingsBridge.cpp:399-407`) | A new item needs about 5 edits in one file. Stale stored orders are fixed by `normalizedSectionOrder` `:999` |
| **Aid option strings** | False-colour names: `SettingsPage.qml:2730-2735`, `falseColorModeToInt` `SettingsPage.qml:1318` and `CameraPage.qml:1717`, inverse `:1403` / `:1725`, shader int switch `PreviewWindowRenderer.cpp:884-890`. Zebra `%` ↔ threshold `SettingsPage.qml:1282`/`:2701`. Peaking Low/Medium/High `SettingsPage.qml:1304`/`:2665` and Core WebUI `Core:src/ApertarCoreApp.cpp:9734`. Peaking default threshold `CameraPreviewItem.hpp:137` (0.08) vs `PreviewWindowRenderer.hpp:132` / `CameraPage.qml:1984` (0.04) | |
| **External-monitor feed names** | `SettingsBridge.cpp:289-294` (normaliser; "Overlay Feed" maps to "Assist Feed"); `SettingsPage.qml:2399-2406`; `ExternalMonitorWindow.qml:49` | |
| **Monitor-state socket fields** | Writer `ExternalMonitorRuntimeBridge.cpp:249-261`; reader `:292-308`; header props `ExternalMonitorRuntimeBridge.hpp:18-30`; source props read by name `ExternalMonitorRuntimeBridge.cpp:137-153` ← `Main.qml:16`, `:30-38`; second by-name reader `ExternalMonitorManager.cpp:113-300`; consumer `ExternalMonitorWindow.qml:9-31`, `:173` | Renaming a `Main.qml` property breaks HDMI with no error (`QVariant` is invalid, so the value is false/empty) |
| **CameraPage vs ExternalMonitorWindow labels** | `shutterDisplayValue` (`CameraPage:491` / `EMW:83`), `processedVideoDefaultResolutionValue` (`:469` / `:104`), `h264OutputResolutionValue` (`:470` / `:105`), `previewImageAspectRatio` (`:481` / `:115`), format line (`formatDisplayValue` `:514` / `formatInfoValue` `EMW:112`), remaining (`InfoLine MEDIA` `:3594` / `remainingValue` `EMW:119`), `aspectRatioForResolution` (`:1138` / `:203`), `formatTimecode` (`:1677` / `:214`), `updateTimecodeDisplay` (`:1692` / `:225`), guide aspect `selectedAspectRatio` (`:2379` / `:134`), guide geometry (`guideOverlay` `:2352` / `EMW:466-740`), `CameraPreviewItem` property bindings (`CameraPage:1973-1997` / `EMW:367-390`) | HDMI shows different text from the panel after a one-sided edit. The timecode is computed independently in each window |
| **Battery estimate** | `CameraPage.qml:249-290` vs `SettingsPage.qml:1472-1560`; types `SettingsPage.qml:230` vs `SettingsBridge.cpp:258` | |
| **Hardware action names** | Core emit: `Core:src/hardware/GpioInput.cpp:133-135`, `Core:src/hardware/Pcf8574Input.cpp:167-174`, `Core:src/ApertarCoreApp.cpp:8666`, `:8949`; forced-broadcast whitelist `Core:src/ApertarCoreApp.cpp:10829-10838`; UI router `Main.qml:285-332` | |
| **Socket path** | `ApertarControlBridge.cpp:1032`, `:1567`; `MediaStatusBridge.cpp:23`; `AudioDeviceBridge.cpp:347`; `ApertarPreviewSocketClient.hpp:30` (ignores the env override); Core `Core:src/ApertarCoreApp.hpp:33` | |
| **QML file list** | `CMakeLists.txt:19-52` (AOT) vs `qml.qrc` | **Finding:** `qml/DroppedFrameWarning.qml` is in `CMakeLists.txt:40` but **missing from `qml.qrc`**. It is used at `CameraPage.qml:2569` and `ExternalMonitorWindow.qml:1103`. A non-AOT build (`APERTAR_QML_AOT=OFF`, the default when cross-compiling, `CMakeLists.txt:56-61`) should then fail to load CameraPage. Present since `upstream-1.6.0`. **Unconfirmed** by a build |
| **Gyro driver names** | `SettingsPage.qml:750` (`MPU6050`, `BMI160`, `BMI270`, `ICM42688-P`), labels `:2110-2131`; `GyroConfigBridge.cpp` driver parsing | |

---

## 5. QML grep recipes and traps

### Build and resources

| Fact | Ref |
| --- | --- |
| QML is compiled in via `qt_add_qml_module(ApertarUI URI Apertar.UI … QML_FILES ${APERTAR_QML_FILES})` when `APERTAR_QML_AOT=ON` (native default) | `CMakeLists.txt:184-196`, option `:61` |
| `RESOURCE_PREFIX /` and `NO_RESOURCE_TARGET_PATH` mean files live at `qrc:/qml/<File>.qml`. That is why `main.cpp:397` loads `qrc:/qml/Main.qml` | `CMakeLists.txt:187-188` |
| Non-AOT falls back to `qml.qrc` (31 entries). Fonts and icons are in `resources.qrc` (53 entries) in both modes | `CMakeLists.txt:197-199` |
| Every QML edit needs a rebuild; there is no on-disk QML at runtime. A new `.qml` file must be added to **both** `CMakeLists.txt:19-52` and `qml.qrc` | |
| `InlineChoice.qml` is in neither list. `GyroOrientationIndicator.qml` is built but unused | |

### Finding things

| Need | Recipe |
| --- | --- |
| Which Component renders settings item X | `grep -n '"X") return' qml/SettingsPage.qml`, then `grep -n 'id: <thatComponent>' qml/SettingsPage.qml` |
| All settings Components and their ranges | `grep -n '^    Component {' -A1 qml/SettingsPage.qml` (the `id:` is always on the next line) |
| Which popup a flag drives | `grep -n 'visible: root.<flag>' qml/SettingsPage.qml` |
| Where component id `foo` is defined | `grep -rn 'id: *foo\b' qml/`. Ids are file-scoped, so `previewItem`, `guideOverlay`, `horizontalLevelOverlay`, `falseColorLegend` and `infoColumn` exist in several files |
| Where a reusable type is defined | The file name is the type: `MonitoringRow {` → `qml/MonitoringRow.qml`. `CameraPreviewItem` is C++ (`import Apertar 1.0`) |
| Every caller of a bridge method | `grep -rnE '(apertarControlBridge|controlBridge|settingsState|settingsBridge)\.applyIso\(' qml/` (CameraPage uses `root.controlBridge.`, SettingsPage uses bare `apertarControlBridge.`) |
| Every reader of a property | `grep -rn '\.zebraEnabled\b' qml/` (catches `settingsState.`, `settingsBridge.`, `root.settingsState.`) |
| Socket command senders | `grep -nE 'sendCoreCommand\(|coreMediaCommand\(|"cmd"' src/*.cpp` |
| UI.conf keys | `grep -noE 'setValue\("[A-Za-z/]+"' src/SettingsBridge.cpp` plus `grep -n 'm_settings.value(QStringLiteral' src/ApertarControlBridge.cpp` |
| CameraPage section starts | `grep -n '// [A-Z]' qml/CameraPage.qml` (PREVIEW AREA `:1962`, GUIDES `:2348`, STATUS CHIP `:2547`, STATIC OVERLAY `:2725`, DYNAMIC OVERLAY `:2849`, BOTTOM STATS `:3564`, TIMECODE `:3661`, RECORD BUTTON `:3769`) |
| C++ method body | `grep -n '^[A-Za-z].*ClassName::method(' src/ClassName.cpp` |

### Traps

| Trap | Detail |
| --- | --- |
| Mixed indentation | `CameraPage.qml` has 52 tab lines and drops to column 0 for about `:635-1925`. `SettingsPage.qml` has 79 tab lines. Use banners or `id:` anchors, not indent depth |
| Bridge naming differs per file | CameraPage receives bridges as properties (`root.controlBridge`, `root.bridge`, `root.settingsState`). SettingsPage uses `root.settingsState` plus bare globals. ExternalMonitorWindow uses only bare globals |
| `mediaBridge` is two classes | `MediaStatusBridge` in the main process, `ExternalMonitorRuntimeBridge` in monitor-only (`main.cpp:150`). Only the shared member names work in `ExternalMonitorWindow.qml` |
| Missing context properties in monitor-only | `gyroConfigBridge`, `wifiBridge`, `statsBridge` and others are undefined. `audioMeterBridge` is null. The code guards with `typeof x !== "undefined" && x` (120 such guards across `qml/`) |
| Signal handler naming | Qt 6 style `function onFooChanged() {}` inside `Connections { target: … }`. No old-style `onFoo:` inside Connections was found. Component signals use `onValueSelected: function(v) {…}` (`SettingsChoice.valueSelected(string)`). Property-change handlers are `on<Prop>Changed:` at element level |
| Optimistic local copies | CameraPage holds `iso`, `fps`, … (`:323-360`), set on selection and refreshed in `Connections` `:1824-1897`. A new Core value needs a property, a handler and the apply call |
| Automatic commands with no user action | none from these two: `ensureValidFpsSelection` / `ensureValidResolutionSelection` return at once while a control bridge exists (`CameraPage.qml:1540-1541`, `:1357-1358`), which the rig always has; Core validates its own settings |
| GUI thread blocks | Every invokable in §2.2/§2.4 blocks QML until Core replies (up to 60 s `record_stop`, 360 s `format_media`). See the KB |
| Same flag, different meaning | `standardLandscapeLayout` = `landscape` only in `SettingsPage.qml:23`, but `landscape` or `landscape_large` in `Main.qml:43-44` and `ClipPlayerPage.qml:24-25` |
| Greyscale vs grayscale | QML ids and item ids say `greyscale` (`monitoringGreyscaleComponent`, item id `greyscale`). The property and UI.conf key say `grayscaleEnabled` |
| "Power" section label | The sidebar id `Power` is shown as "Media" (`SettingsPage.qml:1122`). The `power*` battery Components live in the **System** section (`systemComponentForId` `:2343`) |
| Settings page lifetime | The page is created 750 ms after the first preview frame (`Main.qml:88-91`, `:334`) and kept while on the camera page. `Record` Repeater content builds only while `pageOpen` (`SettingsPage.qml:7018`) |
