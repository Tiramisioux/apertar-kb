# rev-CC-1: review of `src/camera/CameraController.cpp`, port lines 1-2712 (CC.part01.diff)

Stage 2 of 3. Yardstick: `raw/conv-core-camera.md` (rule ids S*, I*, N*) and `raw/conv-core-command-plane.md` (C1-*).
`apertar-conventions.md` does not exist yet. Inventory: `raw/inv-CC-1.md` (F*, H*, C*, R*, N* there are inventory ids, prefixed `inv-` below).

Refs: a bare `:n` is `CC` @cinemate-port (`01f170c`). `@up` = `/home/user/wt/core-upstream` (`35dbe67`). `@main` = fork main `f60e301`.
All claims **confirmed** unless marked **P** (probable).

## 1. Verdict in one table

| Id | Title | Cat | Sev | Deliberate |
| --- | --- | --- | --- | --- |
| CC-1-F1 | IMX585 1.85:1 crops rewritten to the forked driver's sizes; Core tied to the cinemate-port driver | removed-upstream-behaviour | blocker | yes |
| CC-1-F2 | Raw buffer count reads a new media tuning file and sysfs class, not an env knob | mismatch | major | yes |
| CC-1-F3 | `kActiveRequestCount` removed: requests now equal buffers; 8 x 16.9 MB in Clear HDR, no memory check | removed-upstream-behaviour | minor | yes |
| CC-1-F4 | New persisted booleans written `true`/`false` and parsed by string compare | mismatch | minor | no |
| CC-1-F5 | `modeLadderPath` is a line-for-line copy of `persistedSettingsPath` | duplication | minor | no |
| CC-1-F6 | `conform_fps`: stored, published, clamped, carried, never read | slop | minor | yes (unfinished) |
| CC-1-F7 | Ticket numbers, other-project names and history in comments | slop | minor | no |
| CC-1-F8 | Clip template parsed inside `clampCaptureSettings` on every clamp | mismatch | minor | unknown |
| CC-1-F9 | `ladder_text`: a pre-formatted display line built by Core | new-ground | minor | unknown |
| CC-1-F10 | `applyCdngLogFrame` repeats the row loop of `compressClearHdrFrame` | duplication | minor | no |
| CC-1-F11 | `{res}` token labels by width only: 5472x3648 and 4056x3040 become "4K" | bug | minor | no |
| CC-1-F12 | Include order: three includes above the file's own header | mismatch | nit | no |
| CC-1-F13 | Small inconsistencies: `imx283::` vs `apertar::imx585::`; `ladder_resolution` vs `ladderRung`; `fps_speed_ramp_after` string from a bool; `{cam}` always `cam0`; one `assert` | slop | nit | no |

## 2. Findings

### CC-1-F1 IMX585 1.85:1 crops rewritten; Core tied to the forked driver (blocker)

Port:
- `:446-453` `migratedImx585CropResolution`: `3840x2076 -> 3840x2072`, `1920x1038 -> 1920x1036`.
- `:703` `settings.resolution = migratedImx585CropResolution(settings.resolution);` at the top of `clampCaptureSettings`, for every sensor, on every load, write and set.
- `:441-445` comment: "the new driver has neither" of the old sizes.
- `:2667-2679` IMX585 mode = row of `Imx585Modes.hpp` tables (copied from the `cinemate-port` driver, `Imx585Modes.hpp:3-16`).

Upstream:
- `CC:366-396 @up` `isImx585FullHdCropResolution` / `isImx585Raw12CropResolution` list 1038 and 2076, matching the Apertar driver.
- Driver `origin/apertar` `imx585.c:816-817` `.height = 1038`, `:1006-1007` `.height = 2076`. No 2072 or 1036 (`inv-K6`).
- Upstream retires saved selections only inside the per-sensor normaliser, for sizes no supported driver offers (`CC:513-518 @up`).
- N7: capabilities detected at run time; hard-coded sensor tables are the exception, with `validate()` as the last word.

Effect: on the stock Apertar driver a saved, preset or requested 3840x2076 / 1920x1038 is rewritten to a size the driver lacks. The port's probe drops rows that `validate()` changes (`:7181-7183`, `config->at(0).size != size`) **P**: the operator loses both 1.85:1 crops on the original driver, and the ~20 table rows the stock driver lacks depend on the probe to disappear. Merging Core without the driver fork changes original behaviour.

Rework:
1. Delete the unconditional migration from `clampCaptureSettings` (:703).
2. Make `isImx585KnownResolution` accept both 3840x2076/1920x1038 and 3840x2072/1920x1036 (add the two old rows to the SDR tables, flagged as old-driver rows, or keep `isImx585LegacyCropResolution` with both heights).
3. In `imx585ModeForResolution` (:512-518) / the IMX585 case of `sensorModeForRequestedResolution`, choose the row the running driver offers: the probed list (`probedSensorModes`, :3306-3308) when filled, else the table. Map 2076<->2072 and 1038<->1036 there, the way upstream's normaliser maps sizes (`CC:511-532 @up`).
4. `migrateImx585LadderRungs` (:455-462) goes with it; ladder rungs get the same probe-based mapping.
5. Rewrite the comment to one line of why (I19).

Effort M. Risk: the probe runs once at start; the mapping needs a defined answer when the probe did not run (`--simulate`, probe failure): fall back to the old upstream sizes.

### CC-1-F2 Raw buffer count reads a media tuning file (major)

Port `:1458-1470`:
```
const unsigned int extra = mediaExtraRawBuffersForConfiguredRoot();
const MediaTune tune = mediaTuneForConfiguredRoot();
const unsigned int fallback = tune.rawBuffers ? *tune.rawBuffers : std::min(16u, base + extra);
return unsignedEnvValue("APERTAR_RAW_CAMERA_BUFFERS", fallback, 3, 16);
```
`MediaTune.hpp:27-28`: `/home/pi/apertar-media-tune.conf`, `/run/apertar-media/media-tune.override.conf`. `MediaProfile.hpp:110-121` reads `/sys/class/block/<disk>/device`.

Upstream: internal tuning is `APERTAR_<AREA>_<KNOB>` read where used, default plus bounds (I9); "internal tuning stays out of the files the operator edits" (N11); the camera side reads no config file but `camera_settings.conf`, tuning JSON and the colour profile file (S22). Neighbours in the same span: `h264CameraBufferCount` `CC:1124-1128 @up` and `proresCameraBufferCount` `CC:1130-1134 @up` are one `unsignedEnvValue` line each.

Also:
- Comment `:1461-1463` says exFAT gets two more buffers "as Cinemate's profiles do"; `MediaProfile.hpp:142` gives exFAT `extraRawBuffers = 0`. The comment is wrong.
- `MediaProfile.hpp:132` "for T24's direct I/O, which this fork does not carry; unused" (dead member, ticket number).

Rework (this unit's surface): 
```
unsigned int rawCameraBufferCount(bool clearHdr)
{
    return unsignedEnvValue("APERTAR_RAW_CAMERA_BUFFERS", clearHdr ? kClearHdrBufferCount : kConfiguredBufferCount, 3, 16);
}
```
If the FAT/NTFS +2 is kept, compute it from the filesystem type in Core (one `statfs`) as a plain `+2`, no file. Remove `MediaTune` from this path; the wider media-tune feature (`:4364`, `:4718`, `:10543`) is judged in its own slice. Effort M (S for this function).

### CC-1-F3 `kActiveRequestCount` removed (minor)

Upstream `CC:1024 @up` `kActiveRequestCount = 3` with 4 buffers; `CC:6460-6461 @up` `: processedYuvMode ? h264CameraBufferCount() : kActiveRequestCount;` keeps one RAW buffer out of the request queue. Port queues one request per buffer (`:1335-1338`, `:1458`; uses at `:8379-8381`, `:8846-8848`): 4/4 SDR, 8/8 Clear HDR.

Deliberate: commit `db17860` measured capture gaps 41 -> 1 per take, Pi, 4K Clear HDR 16-bit. Behaviour change for every raw take, SDR included, tested only in Clear HDR.

pi-compat: 8 x 16.9 MB = 135 MB of CPU-cached buffers in Clear HDR, up to 16 via env, no check against RAM or `recordingCapabilities()`. Comment names the Pi 5 CFE (`:1337`). Clear HDR is not gated to Pi 5 in `RecordingCapabilities.hpp` (only lossy+Clear HDR is refused, `:77-78`) **P**: a 2 GB Pi 4 could configure it.

Rework: keep SDR at upstream's 4 buffers / 3 requests unless the SDR change is measured too; keep 8 for Clear HDR. One-line why-comment, no board name. Document the change for the original developer. Effort S.

### CC-1-F4 Persisted boolean style (minor)

Port writes `fps_phase_lock`, `preview_tdn`, `media_trim`, `fps_speed_ramp`, `fps_speed_ramp_keep_exposure`, `fps_speed_ramp_stretch_audio` as `"true"/"false"` (:974-979) and reads them with `value == "true" || value == "1"` (:885-896); `media_trim` reads anything but `false`/`0` as true (:889-890). `iso_auto_after_clear_hdr` and `wb_auto_after_clear_hdr` follow upstream (:945, :956, `std::stoul(value) != 0`).

Upstream `CC:749 @up` `output << prefix << "iso_auto=" << s.isoAuto` (writes 0/1), `CC:659-660 @up` `settings.isoAuto = std::stoul(value) != 0;` inside the `try` (I15). Fork main started `clear_hdr=true/false` (`CC:784 @main`).

Rework: write `<< s.fpsPhaseLock` etc., read `std::stoul(value) != 0`; also accept `true`/`false` on read for files the port already wrote (I15: a retired form is still read). `fps_speed_ramp_after` is a string made from a bool (`fpsSpeedRampReturn`): either an enum with `toString` (I11) or a 0/1 key `fps_speed_ramp_return`. Effort S.

### CC-1-F5 `modeLadderPath` copies `persistedSettingsPath` (minor)

`:404-415` repeats `:417-428` (= `CC:342-353 @up`) with the file name changed. A separate file per concern has upstream precedent (`UI.conf`, `/home/pi/apertar-color-profiles.conf`), so the file itself is acceptable. Rework: one `coreConfigFilePath(const char *fileName)` used by both, or `persistedSettingsPath().parent_path() / "mode_ladder.conf"` with the temp fallback handled once. Drop "T34:" from the comment. Effort S.

### CC-1-F6 `conform_fps` dead setting (minor)

`:172` event field, `:696-697` clamp (literal `25.0` where I14 uses `CaptureSettings{}.conformFps`), `:817-818` / `:942` persistence, `:11354-11364` carry across formats, `set_conform_fps` (App:13270), preset key `cameraConformFps` (WCP:19111). No reader (`Types.hpp:135-137` "nothing derives from it yet"); no control in either UI (`inv-N1`). It widens the three hand-kept settings lists (I13) for nothing. Rework: delete across CC, Types, App (both serialisers and the command), WCP preset key, until a consumer exists. Effort S.

### CC-1-F7 Internal names and narration in comments (minor)

| Line | Text |
| --- | --- |
| :403 | `// T34: the mode ladder lives beside camera_settings.conf ...` |
| :441-445 | "(cinemate-modes, the cinemate-port driver branch). The Apertar-Beta 1.6.0 driver had ..., windows that started at PIX_VST 54 ..." |
| :1108 | `// ---- Clip names (src/util/ClipName.hpp) ------...` banner |
| :1461-1463 | "as Cinemate's profiles do (8 ext4 / 10 exFAT-NTFS)" (also wrong, see F2) |
| :1660 | "One take's CineMate Log" |
| `Types.hpp:188-189` | `// Runtime (T34): ...` |
| `ModeLadder.hpp:319` | `"# Apertar mode ladder (T34). ..."` written into the operator's `mode_ladder.conf` |

Upstream I19: comments rare, one to three lines of why, no ticket numbers, no banners (`CC`: 0 `TODO`, 0 block comments @up). Rework: delete the banner and ticket numbers; reduce each to one why-line; name the Log feature without another product's brand. Effort S.

### CC-1-F8 Template validation inside `clampCaptureSettings` (minor)

`:698-702` parses `clipNameTemplate` on every clamp; clamp runs on every load, write and persist (`:925, :931, :933, :938, :1016`). `nextClipFolderName` parses again with its own fallback (:1194-1196). Upstream's clamp is absolute numeric ranges plus resets to `CaptureSettings{}` (S15 step 2, `CC:534-601 @up`); string values are validated by the setter (I1/I2) and by the load chain (I15). The setter already parses (`:11848`). Rework: drop the block from clamp; in the `clip_name_template` load branch keep the value only if `parse(value).ok`. Effort S.

### CC-1-F9 `ladder_text` display string from Core (minor, new-ground)

`:185` `ladder_text` carries e.g. "Resolution 1 · 3840×2160 · ClearHDR16 · ≤25 · Uncompressed" (`Types.hpp:189`), UTF-8 glyphs included. Upstream's `settings` event carries values; wording and layout are done by each client (S12; WebUI and QML format sizes themselves). The parts are partly published already (`ladder_resolution`, `ladder_count`, `ladder_tops`). Verdict: simplify. Publish the missing parts as scalars and let the two UIs compose the line, or keep it and document it as the one display string. Effort S-M (UI readers).

### CC-1-F10 Row loop duplicated (minor)

`:1671-1680` `applyCdngLogFrame` is the loop of `compressClearHdrFrame` (`:1647-1658`, fork main `CC:1335-1346 @main`) with `cdnglog::applyTable` for the inner loop. Rework: one `applyRowLookupTable(data, size, width, height, stride, lut)` used by both. Effort S.

### CC-1-F11 `{res}` label by width (minor bug)

`:1123-1130`: width >= 3500 -> "4K". IMX283 5472x3648 (`Imx283Modes.hpp`) and IMX477 4056x3040 get "4K"; 1332x990 gets "990p". Input: IMX283 at full sensor, template `{res}` -> folder says 4K. Rework: label from the DCI/UHD classes with an explicit 5K/6K step, or emit `<width>x<height>`. Effort S.

### CC-1-F12 Include order (nit)

`:1-3` `FramePhaseLock.hpp`, `FpsCeiling.hpp`, `<optional>` above `camera/CameraController.hpp`. Upstream I21: own header first (`CC:1 @up`). Rework: move them into the project and std groups. Effort S.

### CC-1-F13 Small inconsistencies (nit)

- `imx283::` (:660, :670) vs `apertar::imx585::` (:491); both namespaces are `apertar::<x>` and the file is inside `namespace apertar`: use the short form for both.
- JSON `ladder_resolution` from member `ladderRung` (:180): rename the member.
- `{cam}` is the constant `cam0` (:1157): a token with one value; drop it or document it.
- `<cassert>` (:43) for one `assert` at :4596; upstream uses only `static_assert` (`CC:1697 @up`).
- `#endif // APERTARCORE_HAS_LIBCAMERA` directly followed by `enum class SensorFamily` with no blank line (:2268).
- `APERTAR_IMX585_MIN_MODE_WIDTH` (`Imx585Modes.hpp:107`) decides which modes the operator sees (hides 22 of 62 rows); N11 keeps env knobs for internal tuning. Acceptable as a bench knob; say so in a comment.

## 3. Abstraction verdicts

| Name | Verdict | Reason |
| --- | --- | --- |
| `apertar::imx585` mode tables (`Imx585Modes.hpp`) | keep | Pure, std-only header named after the concept (S4); replaces two whitelists and an if-chain with one lookup. Condition: F1 (tables must cover the stock Apertar driver, probe decides) |
| `apertar::imx283` mode table (`Imx283Modes.hpp`) | keep | Same shape as above; IMX283 is new hardware. The CC side mirrors the IMX294 helpers by name (`normalizedImx283ResolutionForBitDepth` <-> `normalizedImx294ResolutionForBitDepth`, `imx283TransportForActiveResolution` <-> `imx294ReadoutForActiveResolution`) |
| IMX585 size migration (`migratedImx585CropResolution`, `migrateImx585LadderRungs`) | rework-to-upstream-pattern | Upstream retires sizes in the per-sensor normaliser, not by rewriting every sensor's setting in clamp. Make the mapping depend on the running driver (F1) |
| `apertar::clipname` engine + `clipNameValues`, `nextClipFolderName` | simplify | New ground, operator-visible, default reproduces upstream's name (`inv-N13`); header shared by CC, App, WCP so `src/util` is defensible (S6). Simplify: validate in setter and load not in clamp (F8), drop `{cam}`, fix `{res}` (F11), drop the banner |
| `modeLadderPath()` | simplify | Copy of `persistedSettingsPath` (F5) |
| `apertar::ladder` (`ModeLadder.hpp`) | keep | Only `ladder::Rung` is used here; the feature is judged in the slices that hold its logic. Remove "T34" from the file header it writes |
| `ladderTopsJson` | keep | Inline `...Json()` helper is upstream's idiom (I12); could sit next to the type in `ModeLadder.hpp` |
| `rawCameraBufferCount(bool)` | simplify | One `unsignedEnvValue` line like its two neighbours (F2) |
| Media profile and tuning file (`MediaProfile.hpp`, `MediaTune.hpp`) as used here | rework-to-upstream-pattern | Upstream tunes with env vars only, no config file on the camera side (I9, N11, S22). Wider use judged in its own slice |
| `CdngLogTake`, `applyCdngLogFrame` | simplify | Struct is fine; the frame loop is a copy (F10) |
| `apertar::cdnglog` (`LogCurve.hpp`) | keep | Pure header (S4); only included here |
| `activeAreaScalerCrop` (in upstream's `ScalerCropGeometry.hpp`) | keep | Added to the upstream header next to `centeredRawWindowScalerCrop`; same signature style |
| Headers included here, used later (`FramePhaseLock`, `FpsCeiling`, `TuningTdnStrip`, `FramePath`, `MediaFault`, `BufferBudget`, `StoragePreroll`) | keep (not judged here) | Their use is outside this slice |

## 4. What conforms

| What | Rule | Where |
| --- | --- | --- |
| 27 `settings` fields added in place, none removed/renamed/reordered, same fields added to both App serialisers | I13, C1-S14 | :163-246; `inv-3.1` |
| `ladder_tops` array: the event already carries a short list of arrays/objects | C1 5.5 | :186 |
| 12 persisted keys as `else if (key == ...)` branches inside the existing `try`; per-profile prefix unchanged | I15, S20 | :817-900, :936-989 |
| New camera-wide switches carried across format profiles the way upstream carries `timecodeMode` | N14 | :11347-11368 vs `CC:7946-7950 @up` |
| Runtime members on `CaptureSettings` with a trailing "Runtime ..., not persisted" comment | S21 | `Types.hpp:157, :177, :188-189` |
| IMX283 as a fifth `SensorFamily`, a substring in `detectSensorFamily`, a case in each sensor switch | S11 | :2272, :2569-2570, :2581, :2283-2284, :2635-2642, :2722 |
| IMX283 ScalerCrop branch inside `controlsForSettings`, crop maths in the upstream geometry header | S10, S4 | :2486-2501; `ScalerCropGeometry.hpp:66-92` |
| `conform_fps` clamp in the absolute-range layer (apart from the literal default) | I2 | :696-697 |
| Build without libcamera: guards closed/reopened around pure helpers, no code moved; makes I18 true (upstream fails to compile with `APERTARCORE_HAS_LIBCAMERA=0`, `inv-K4`) | I18, N12 | :1355-1356, :2268, :2309-2317, :2576-2626, :2687 |
| `nextClipFolderName` throws upstream's exact sentence, lowest free number wins | I4, N10 | :1196-1197 vs `CC:3675 @up` |
| `APERTAR_RAW_CAMERA_BUFFERS` name and bounds | I9 | :1469 |
| Local-time block in `clipNameValues` copied rather than shared | S6 (upstream copies small helpers per use) | :1141-1146 vs `CC:935-940 @up` |

## 5. Protocol

No socket or HTTP shape changes in this slice. The `settings` event only gains keys; an unmodified original UI ignores unknown keys **P** (its readers look keys up by name, `conv-core-command-plane.md` 5.5). No field removed or retyped. `ladder_text` carries UTF-8 (`·`, `×`); `escapeJson` passes bytes >= 0x80 unchanged, as upstream.

## 6. Commands run

```
git -C /home/user/imx585-v4l2-driver show origin/apertar:imx585.c | grep -n ".width = \|.height = "
sed -n 7145,7215p /home/user/Apertar-Core/src/camera/CameraController.cpp        (probe)
sed -n 6455,6465p /home/user/wt/core-upstream/src/camera/CameraController.cpp      (kActiveRequestCount use)
grep -n "mediaTrimEnabled|clipNameTemplate =|fpsPhaseLock =" src/camera/CameraController.cpp
sed -n 130,150p src/util/MediaProfile.hpp; sed -n 20,40p src/util/MediaTune.hpp
sed -n 300,344p src/camera/ModeLadder.hpp
grep -n "assert(" /home/user/wt/core-upstream/src/camera/CameraController.cpp
grep -rln "ClipName.hpp|clipname::" src include tools
```

## Skeptic

Checked at Core `cinemate-port` 01f170c, `upstream-1.6.0` 35dbe67, fork `main` f60e301, driver `origin/apertar` e5b74d3 and `cinemate-port` cd548ef.

| id | verdict | why |
| --- | --- | --- |
| CC-1-F1 | corrected | Confirmed: migration at CC:703 (in clamp, after the metering/clip-name lines, not "the top"), CC:10514, 10648, 11060, 12663; old driver has 2076/1038 (origin/apertar imx585.c:591, 817), port driver 2072/1036 (imx585.c:1122, 1409). Rework was incomplete: the IMX585 probe only configures rows of the port's own table (CC:7166-7174 `tableProbe` -> `apertar::imx585::offered`), so with the old driver 2072/1036 fail `config->at(0).size != size` (CC:7187) and 2076/1038 are never tried. The mapping must also put the old-driver rows into the probe list. |
| CC-1-F2 | corrected | Code and comment error confirmed (comment CC:1461-1463 says exFAT +2; MediaProfile.hpp:142 gives exFAT 0). Severity to minor: the second config file belongs to the media-tune slice; in this unit it is one read plus a wrong comment. Upstream already has env-only buffer knobs (CC:1124-1134@upstream-1.6.0), so the rework is right. |
| CC-1-F3 | stands | kActiveRequestCount=3 at CC:1024, used CC:6461@upstream-1.6.0; port uses rawCameraBufferCount for buffers (CC:8381) and requests (CC:8848). Clear HDR not gated by board (RecordingCapabilities.hpp:66-81@cinemate-port). Commit db17860 measured only 4K Clear HDR 16-bit. |
| CC-1-F4 | stands | CC:885-898 and 974-980 confirmed; upstream 0/1 + stoul (CC:659-660, 749@upstream-1.6.0); port's own iso_auto_after_clear_hdr uses 0/1 (CC:945). Minor note: fps_speed_ramp_after writes return/stay, which already looks like an upstream enum string; only the bool backing is odd. |
| CC-1-F5 | corrected | Copy confirmed (CC:403-427). Severity to nit: upstream itself repeats the XDG rule three times (App:343, App:535, HardwareConfigStore.cpp:127@upstream-1.6.0), so a copy is upstream style; parent_path() of persistedSettingsPath() is still the tidy fix. |
| CC-1-F6 | corrected | No reader confirmed (grep: only store/clamp/serialise/carry/set). Where corrected: the preset key is in App (App:7851 export, App:14353-14357 import), not WCP; WCP has 0 mentions. |
| CC-1-F7 | stands | All quoted lines confirmed (CC:403, 441-445, 1108, 1461-1463, 1660; Types.hpp:184-189; ModeLadder.hpp:319). Upstream CC has 0 `// ----` banners. Wider: 69 "Cinemate"/"CineMate" mentions in src+include outside WCP (MediaProbe/MediaIntent/MediaProfile, LossyDngEncoder), for the slop slice. |
| CC-1-F8 | dropped | Upstream clamp normalises a string too: `normalizeExposureMetering(settings.exposureMetering)` at CC:534-535@upstream-1.6.0. clamp is the shared sanitiser for load, presets and writes, so the template check there follows the Apertar way. |
| CC-1-F9 | corrected | Confirmed: Core composes the line (CC:10911-10935) and publishes it (CC:185); upstream event has values only. "Both UIs" is wrong: only the WebUI reads it (WCP:8421, 13911, 15920); the touch UI has 0 hits. |
| CC-1-F10 | corrected | Loop pair confirmed (CC:1647-1656, 1671-1680). Severity to nit: compressClearHdrFrame is fork-main code, not upstream; the inner op differs (lut[] vs cdnglog::applyTable); 6 lines each. |
| CC-1-F11 | stands | CC:1123-1130 confirmed: 5472 and 4056 widths give "4K", 1332x990 gives "990p". Only hits templates using {res} (default `{format}_{date}_{clip}`, ClipName.hpp:23). |
| CC-1-F12 | stands | CC:1-3@cinemate-port vs CC:1@upstream-1.6.0 own header first. |
| CC-1-F13 | stands | imx283:: (CC:660, 7 uses) vs apertar::imx585:: (16 uses), both namespaces are apertar::x; ladder_resolution from ladderRung (CC:180); v.cam = "cam0" (CC:1157); <cassert> (CC:43) for one assert (CC:4596), upstream has only static_assert (CC:1697@upstream-1.6.0); #endif then enum (CC:2268-2269). |

## Final findings

### CC-1-F1 [removed-upstream-behaviour, blocker] IMX585 1.85:1 crops rewritten to forked-driver sizes; Core tied to the cinemate-port driver
- where: src/camera/CameraController.cpp:441-462@cinemate-port ; :703 ; :10514 ; :10648 ; :11060 ; :12663 ; :2667-2679 ; :7166-7190 (probe) ; src/camera/Imx585Modes.hpp:3-16@cinemate-port
- port way: migratedImx585CropResolution rewrites 3840x2076->3840x2072 and 1920x1038->1920x1036 unconditionally inside clampCaptureSettings (every sensor, every load/write/set), in set_resolution, presets and ladder rungs. IMX585 modes come from tables copied from the cinemate-port driver, and the startup probe for an IMX585 only configures rows of that table.
- Apertar way: isImx585FullHdCropResolution / isImx585Raw12CropResolution list 1038 and 2076 (CC:366-396@upstream-1.6.0), matching driver origin/apertar imx585.c:591, 817. Upstream retires sizes only in the per-sensor normaliser (CC:511-532@upstream-1.6.0). Capabilities are detected at run time and validate() has the last word.
- why it matters: With the original Apertar driver every saved, preset or requested 1.85:1 crop is rewritten to a size the driver lacks; the probe drops 2072/1036 (size mismatch, CC:7187) and never tries 2076/1038, so the operator loses both 1.85:1 crops (probable, not run on a Pi). Core can only be merged together with the driver fork.
- rework: Remove the migration from clampCaptureSettings, set_resolution, presets and ladder load. Give the IMX585 table both heights for the 1.85:1 row (2072/2076 and 1036/1038) so the table probe tries both and keeps the one the driver accepts. In imx585ModeForResolution / the IMX585 case of sensorModeForRequestedResolution map 2076<->2072 and 1038<->1036 to whichever size probedSensorModes holds; if the probe did not run, fall back to the upstream sizes. migrateImx585LadderRungs is replaced by the same mapping. Cut the comment to one line of why.
- effort M; deliberate yes (commit 900d282 and comment CC:441-445: the new driver has neither old size; not run on a Pi).

### CC-1-F2 [mismatch, minor] Raw buffer count reads the media tuning file and a sysfs media class
- where: src/camera/CameraController.cpp:1456-1470@cinemate-port ; src/util/MediaTune.hpp:27-28@cinemate-port ; src/util/MediaProfile.hpp:126-150@cinemate-port
- port way: rawCameraBufferCount: env var wins, then raw_buffers from /home/pi/apertar-media-tune.conf or /run/apertar-media/media-tune.override.conf, then base + a per-filesystem extra from sysfs. The comment cites Cinemate's profiles and says exFAT gets +2; the table gives exFAT 0 (MediaProfile.hpp:142). MediaWriterSettings.directIo is marked "for T24 ... unused".
- Apertar way: h264CameraBufferCount and proresCameraBufferCount are one unsignedEnvValue line each (CC:1124-1134@upstream-1.6.0); internal tuning is APERTAR_<AREA>_<KNOB>, kept out of operator files.
- why it matters: Ties the camera path to a second config file (to be judged in the media-tune slice); the comment is wrong; dead field with a ticket number.
- rework: rawCameraBufferCount(bool clearHdr) { return unsignedEnvValue("APERTAR_RAW_CAMERA_BUFFERS", clearHdr ? kClearHdrBufferCount : kConfiguredBufferCount, 3, 16); }. Keep a +2 for FAT/NTFS only if measured. Fix or remove the comment. Decide MediaTune in its own slice.
- effort M; deliberate yes (commits 26da30e, 2edc6d0; MediaProfile.hpp:140-142 records exFAT measurements C0101, C0106).

### CC-1-F3 [removed-upstream-behaviour, minor] kActiveRequestCount removed: one request per buffer in every raw take; 135 MB of Clear HDR buffers without a board check
- where: src/camera/CameraController.cpp:1334-1338@cinemate-port ; :8379-8381 ; :8846-8848
- port way: Requests = buffers: 4/4 in SDR, 8/8 in Clear HDR (8 x 16.9 MB), up to 16 through the env var. The comment names the Pi 5 CFE.
- Apertar way: kActiveRequestCount = 3 with kConfiguredBufferCount = 4 (CC:1023-1024@upstream-1.6.0), used at CC:6460-6461@upstream-1.6.0, which keeps one RAW buffer out of the queue.
- why it matters: Every raw take changes behaviour, but only 4K Clear HDR 16-bit was measured. Clear HDR is not gated by board in RecordingCapabilities.hpp:66-81 (confirmed), so a low-RAM Pi 4 could allocate 135 MB (probable).
- rework: Keep SDR at upstream's 4 buffers / 3 requests unless the SDR change is measured. Keep 8 for Clear HDR. One-line why comment without a board name; document the change for the original developer.
- effort S; deliberate yes (commit db17860: capture gaps 41 -> 1 per take, Pi, 4K Clear HDR 16-bit).

### CC-1-F4 [mismatch, minor] New persisted booleans written true/false and parsed by string compare
- where: src/camera/CameraController.cpp:885-898@cinemate-port ; :974-980
- port way: fps_phase_lock, preview_tdn, media_trim, fps_speed_ramp, fps_speed_ramp_keep_exposure, fps_speed_ramp_stretch_audio written "true"/"false", read with value == "true" || value == "1"; media_trim reads anything but false/0 as true. fps_speed_ramp_after is "return"/"stay" backed by a bool.
- Apertar way: output << prefix << "iso_auto=" << s.isoAuto (0/1, CC:749@upstream-1.6.0); settings.isoAuto = std::stoul(value) != 0 (CC:659-660@upstream-1.6.0). The port's own iso_auto_after_clear_hdr uses this style (CC:945).
- why it matters: One file holds two boolean styles.
- rework: Write << s.field, read std::stoul(value) != 0, also accepting true/false on read for files the port already wrote. Back fps_speed_ramp_after with an enum plus toString/fromString, or make it a 0/1 key.
- effort S; deliberate no.

### CC-1-F5 [duplication, nit] modeLadderPath is a line-for-line copy of persistedSettingsPath
- where: src/camera/CameraController.cpp:403-415@cinemate-port
- port way: Copy of the XDG/HOME/temp path function with only the file name changed, plus a "T34:" comment.
- Apertar way: persistedSettingsPath (CC:342-353@upstream-1.6.0). Upstream itself repeats the rule (App:343, App:535, HardwareConfigStore.cpp:127@upstream-1.6.0); separate files per concern exist upstream.
- why it matters: Small; a second copy in the same file next to the first.
- rework: persistedSettingsPath().parent_path() / "mode_ladder.conf" (or one helper taking the file name). Drop T34.
- effort S; deliberate no.

### CC-1-F6 [slop, minor] conform_fps: stored, published, clamped and carried, but never read
- where: src/camera/CameraController.cpp:172, 696-697, 817-818, 942, 11354-11364, 11812@cinemate-port ; include/apertar/core/Types.hpp:135-137 ; src/ApertarCoreApp.cpp:320, 7851, 9484, 13270, 14353-14357@cinemate-port
- port way: Settings field, persisted key, clamp (literal 25.0), format carry, set_conform_fps command, preset key in App. Types.hpp: "nothing derives from it yet". Neither UI has a control (WCP 0 mentions; touch UI 0).
- Apertar way: Settings lists are kept by hand, so each field costs three edits; defaults from CaptureSettings{}.field. Upstream has no unused settings.
- why it matters: Dead surface in the protocol, the settings file, presets and three serialisers.
- rework: Delete it from CC, Types.hpp, both App serialisers, the App command, the command list and the App preset export/import until a consumer exists.
- effort S; deliberate yes (Types.hpp:135-137; commit d7ff071 "desk only").

### CC-1-F7 [slop, minor] Ticket numbers, other-project names and history in comments and the written ladder file
- where: src/camera/CameraController.cpp:403, 441-445, 1108, 1461-1463, 1660@cinemate-port ; include/apertar/core/Types.hpp:184-189 ; src/camera/ModeLadder.hpp:319
- port way: "T34:", "cinemate-modes, the cinemate-port driver branch", "Apertar-Beta 1.6.0 driver had...", a "---- Clip names ----" banner, "as Cinemate's profiles do", "CineMate Log", and "(T34)" in the header written into mode_ladder.conf.
- Apertar way: comments are rare, one to three lines of why, no ticket numbers, no banners (0 `// ----` banners in CC@upstream-1.6.0).
- why it matters: Names mean nothing to the original developer; history narration ages badly; the ladder file carries an internal ticket to the operator.
- rework: Delete the banner and ticket numbers; cut each comment to one line of why; name the Log feature without another product's brand; remove T34 from the ladder file header. (The same pattern, 69 mentions, runs through MediaProbe/MediaIntent/MediaProfile/LossyDngEncoder: slop slice.)
- effort S; deliberate no.

### CC-1-F9 [new-ground, minor] ladder_text: a pre-formatted display line built by Core
- where: src/camera/CameraController.cpp:185, 10911-10935@cinemate-port ; include/apertar/core/Types.hpp:189
- port way: The settings event carries a line such as "Resolution 1 · 3840×2160 · ClearHDR16 · ≤25 · Uncompressed", UTF-8 glyphs included. Only the WebUI reads it (WCP:8421, 13911, 15920); the touch UI does not.
- Apertar way: no precedent. Upstream's settings event carries values only (CC:136-187@upstream-1.6.0); each client formats them.
- why it matters: Core takes over WebUI wording; a second client would get a different split of formatting.
- rework: Publish the missing parts as scalars and compose the line in the WebUI, or keep it and document it as the only display string Core sends.
- effort S; deliberate unknown.

### CC-1-F10 [duplication, nit] applyCdngLogFrame repeats the row loop of compressClearHdrFrame
- where: src/camera/CameraController.cpp:1647-1656, 1671-1680@cinemate-port
- port way: Two copies of the stride/size-checked row loop over 16-bit rows.
- Apertar way: compressClearHdrFrame (CC:1335-1346@main) is fork-main code; upstream has neither.
- why it matters: Two 6-line loops to keep correct.
- rework: One row-walker taking a per-row callable, or leave as is.
- effort S; deliberate no.

### CC-1-F11 [bug, minor] {res} clip-name token labels by width only
- where: src/camera/CameraController.cpp:1123-1130@cinemate-port
- port way: width >= 3500 gives "4K"; 1900-1999 wide gives "1080p"; otherwise "<height>p".
- Apertar way: no precedent.
- why it matters: An IMX283 5472x3648 or IMX477 4056x3040 take is named "4K"; 1332x990 gives "990p". Affects only templates with {res} (default `{format}_{date}_{clip}`).
- rework: Label explicit classes (UHD/DCI 4K, 5K, 6K) or emit <width>x<height>.
- effort S; deliberate no.

### CC-1-F12 [mismatch, nit] Three includes above the file's own header
- where: src/camera/CameraController.cpp:1-3@cinemate-port
- port way: FramePhaseLock.hpp, FpsCeiling.hpp and <optional> come before camera/CameraController.hpp.
- Apertar way: own header first (CC:1@upstream-1.6.0), then project headers, then std headers.
- why it matters: Breaks the include order.
- rework: Move them into the project and std groups.
- effort S; deliberate no.

### CC-1-F13 [slop, nit] Small inconsistencies: namespace spelling, member/key names, constant token, lone assert
- where: src/camera/CameraController.cpp:660, 180, 1157, 43, 4596, 2268@cinemate-port
- port way: imx283:: vs apertar::imx585:: (both are apertar::x); JSON ladder_resolution from member ladderRung; {cam} token always "cam0"; <cassert> for one assert; #endif directly followed by enum class.
- Apertar way: one namespace style; wire names match members; upstream uses only static_assert (CC:1697@upstream-1.6.0).
- why it matters: Small reading friction.
- rework: Short namespace form for both tables; rename the member to ladderResolution; drop {cam}; replace the assert with an explicit check or remove it; blank line after #endif.
- effort S; deliberate no.

Dropped: CC-1-F8 (upstream clamp also normalises a string, CC:534-535@upstream-1.6.0).
