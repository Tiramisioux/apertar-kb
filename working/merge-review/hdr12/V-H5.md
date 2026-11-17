# V-H5: skeptic pass on "the mode itself" (Clear HDR no longer pinned to 4K)

Refs: Core `01f170c`, UI `7ea9afc`, fork main Core `f60e301`, UI `4415a55`. All code re-read; readers' notes not used as proof.

## Verdict

| Part of H5 | Result |
| --- | --- |
| caa0153 removed the 3840x2160 pin for colour IMX585 | confirmed |
| Touch UI '4K Clear HDR' sends only `set_clear_hdr`, lands in 12-bit at the nearest H12 row of the SDR size | confirmed |
| Touch UI locks crops; any size pick leaves Clear HDR | confirmed |
| Hardware button enters 16-bit | confirmed |
| "12-bit and 16-bit tests may differ in size" | refuted for the common sizes (4K, Full HD, 3840 crops): both depths land on the same row. Holds only from 1440x1080, 1488x1080, 1920x1040 |
| H5 explains "12-bit strange, 16-bit fine" | unlikely (probable not-a-cause). It is a real defect: the UI promises 4K and Core does not deliver it |

## Evidence

| Claim | Where | Label |
| --- | --- | --- |
| Main pinned Clear HDR: `if (sensorFamily == SensorFamily::Imx585 && settings.clearHdr) settings.resolution = Resolution{ 3840, 2160 };` | `src/camera/CameraController.cpp:2824-2827@f60e301` | confirmed |
| Port pins only mono: `if (sensorFamily == SensorFamily::Imx585 && monochromeSensor && settings.clearHdr)`; then `normalizedResolutionForSensor(..., rawBitDepth, clearHdr)` | `src/camera/CameraController.cpp:3526-3531@01f170c` | confirmed |
| IMX585 normaliser: `find()` else `nearest()` in the class table | `CameraController.cpp:512-518,2831-2835@01f170c` | confirmed |
| H12 table has 29 rows, first `{1920,1080,binned}`, last `{1440,1080,1x1}` | `src/camera/Imx585Modes.hpp:78-87@01f170c` | confirmed |
| `setClearHdr` sanitises `next` (with the new size) and applies it | `CameraController.cpp:11615-11660@01f170c` | confirmed |
| Bridge `applyClearHdr` sends only `set_clear_hdr`; comment "Core ... forces 4K" stale | `src/ApertarControlBridge.cpp:703-714@7ea9afc` | confirmed |
| Quick menu: "clearhdr" -> `applyClearHdr(true)`; any other size -> `applyClearHdr(false)` first | `qml/CameraPage.qml:1351-1360@7ea9afc` | confirmed |
| Crops disabled in Clear HDR: `cropControlsEnabled: processedVideoRecordFormat \|\| !clearHdrActive`; comment "Core forces 4K" stale | `qml/CameraPage.qml:452,458@7ea9afc` | confirmed |
| Label is fixed text "4K Clear HDR" whatever the size | `qml/CameraPage.qml:3382,3457@7ea9afc`, `qml/SettingsPage.qml:3296@7ea9afc` | confirmed |
| Touch UI Settings offers 16-bit only while Clear HDR is on (`rawBitDepthOptionEnabled`) | `qml/SettingsPage.qml:658-672@7ea9afc` | confirmed |
| Hardware `clear_hdr`: `set_clear_hdr true` then `set_raw_bit_depth 16`; comment "as the touch UI's resolution button does" stale | `src/ApertarCoreApp.cpp:10450-10465@01f170c` | confirmed |
| Same stale claim in `setRawBitDepth` ("the hardware clear_hdr action and the touch UI send it") | `CameraController.cpp:11602-11604@01f170c` | confirmed |
| UI behaviour unchanged from fork main (`applyQuickResolution` identical, 12-bit entry); only Core changed | `qml/CameraPage.qml:1241-1249@4415a55` | confirmed |

## Host check (what size each route lands on)

`/home/user/build/hdr12-numeric/v_h5_nearest.cpp`, built with `g++ -std=c++20 -I/home/user/Apertar-Core/src`, uses the port's own `Imx585Modes.hpp` `find()`/`nearest()`. (Skips `imx585AliasResolution`; the sizes below are table rows or UI options.)

| SDR size before entry | 12-bit (touch UI) | 16-bit (button, or Settings 16-bit after entry) |
| --- | --- | --- |
| 3840x2160 (UI "4K") | 3840x2160 1x1 | 3840x2160 1x1 |
| 1920x1080 (UI "Full HD") | 1920x1080 binned | 1920x1080 binned |
| 3840x1608 crop | 3840x1608 | 3840x1608 |
| 3840x2076 (UI 1.85 option) | 3840x2072 | 3840x2072 |
| 1920x804 binned | 1920x800 1x1 (half the field width) | 1920x800 1x1 |
| 1920x1040 | 1920x1040 1x1 | 1920x1016 1x1 |
| 1440x1080 (S10 binned) | 1440x1080 1x1 (narrow crop) | 1920x1080 binned (full field) |
| 1488x1080 binned | 1440x1080 1x1 | 1920x1080 binned |

Reading: from the two touch-UI base sizes (4K, Full HD) the 12-bit and 16-bit entries give the same size and binning. The "12 vs 16 differ" case needs a 1440/1488-wide or 1920x1040 start, reachable from the WebUI or the ladder, not the touch UI base list.

## Why this is unlikely to be the owner's symptom

- At 4K nothing changes (both routes 3840x2160). The owner says "4K Clear HDR" is the mode he uses in the UI label, but the label proves nothing (fixed text).
- From Full HD both depths run the same binned 1080 row, so a 12-only fault would still need a cause below Core's size choice (driver 12-bit binned ClearHDR mode, ccmp/unwrap). H5 then only changes which driver mode is under test, it is not the fault.
- Where H5 alone makes 12 and 16 differ (1440-wide start) the 12-bit picture is a narrow 1x1 crop: "reframed", not "strange". An owner would more likely call that "cropped".

What would keep H5 alive: the owner was at Full HD when testing 12-bit, and the 12-bit binned H12 row is itself broken (driver / OB rows / ccmp at 2x2). That is a driver question for G5, not this hypothesis.

## Pi test (unchanged, sharpened)

```
printf '{"cmd":"get_state"}\n' | socat - UNIX-CONNECT:/tmp/apertar-core.sock
```
Read `resolution`, `raw_bit_depth`, `clear_hdr` right after the owner's 12-bit entry and again in 16-bit. Same resolution in both = H5 is not the 12/16 difference. 12-bit not 3840x2160 = the UI label defect is live; then repeat the 12-bit test after `set_resolution 3840 2160` to see whether the "strange output" goes away.

## Defect and fix sketch (label/lock vs Core)

Defect (confirmed): the touch UI calls the mode "4K Clear HDR", hides the size and blocks crops, but Core keeps the SDR size's nearest H12 row. An operator at Full HD records binned 1080 labelled 4K and cannot change it without leaving Clear HDR.

Smallest fix in the original style, in Core, where main had it: entering Clear HDR from off picks 4K; explicit `set_resolution` while in Clear HDR still takes any H12/H16 row (caa0153's intent).

```cpp
// CameraController::setClearHdr, after `next.clearHdr = enabled;`
    // Clear HDR is entered at 4K, as the UIs label it; set_resolution picks another Clear HDR row after.
    if (enabled && !settings_.clearHdr && sensorFamily == SensorFamily::Imx585)
        next.resolution = Resolution{ 3840, 2160 };
```

Plus fix the stale comments: `ApertarControlBridge.cpp:704`, `CameraPage.qml:452`, `ApertarCoreApp.cpp:10451`, `CameraController.cpp:11602-11603`. Alternative (UI side, no Core change): show `root.resolution` next to "Clear HDR" instead of the fixed "4K" text.

Host test: `setClearHdr` lives in `CameraController` (needs libcamera), so the fix itself is not host-testable. What `tools/imx585_modes_test.cpp` can pin is the premise: `nearest(Class::H12, 1920, 1080)` is the binned 1920x1080 row, not 3840x2160, and `find(Class::H12, 3840, 2160)` exists and is 1x1. The fix is verified on the Pi with the `get_state` above (resolution 3840x2160 after a Full HD -> 4K Clear HDR tap).
