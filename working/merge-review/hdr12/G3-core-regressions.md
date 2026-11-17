# G3: what the port changed in Core for 12-bit Clear HDR (since fork main)

Scope: Apertar-Core `origin/main` `f60e301` .. `cinemate-port` `01f170c`. Case under study: IMX585 colour,
Clear HDR on, `raw_bit_depth=12` (class H12). Read-only review; nothing run on a Pi.
One host check was run (below, C1). The driver and libcamera were read only where Core relies on a value from them.

## Verdict in five lines

1. The 4K H12 cDNG record path is the same as on main: same CCMP table, same code mapping, same tags.
   The mapping only moved from libcamera's completion thread to the copy worker. **Confirmed.**
2. The CCMP table in Core still matches the cinemate-port driver defaults and the libcamera fork's CcmpUnwrap LUT,
   entry for entry. **Confirmed** (host check C1).
3. The biggest change is **caa0153**: H12 is no longer forced to 3840x2160. 28 other sizes are now reachable,
   including 2x2 binned 1920x1080 and the 1440/1920/2048/3840 crops. None of them ran on main. Most likely cause
   if the owner was not at 4K. **Confirmed change, effect probable.**
4. **8175273** (with 6d217c7, b5b787e, 60645d4): H12 now forces manual ISO and manual WB and caps ISO at 720.
   On main, AE and AWB ran in H12. Exposure and white balance behave differently from main. **Confirmed.**
5. **f2ebe6e / 3cae990**: Clear HDR now switches cDNG to Uncompressed, and Log (d44b177) can be switched on per
   ladder rung. Both change the file layout, not the pixel values (Log: different curve, same linear result).
   **Confirmed change, low risk.**

## Commit table

Every commit in `origin/main..cinemate-port` that `-G'clear_?hdr|ccmp|lineari[sz]ation|gradationCompanded|blackLevel|whiteLevel|bitsPerSample|rawBitDepth|codes12'`
(case-insensitive) or `-S ClearHdrCcmp|LinearizationTable|H12|clearHdr` matched in `src include`. 59 commits; the ones
whose only hit is the `commands` list in `handleCommand` or a WebUI label are grouped at the end.

| Commit | What it does to 12-bit Clear HDR | Risk | Can change |
| --- | --- | --- | --- |
| caa0153 camera: imx585 modes from tables | Drops main's "Clear HDR = 4K" rule. H12 offers 29 driver rows (`Imx585Modes.hpp:78-87`), incl. binned 1920x1080 and crops. Sizes not in H12 snap to the nearest H12 row. Colour IMX585 is configured explicitly only and refused if the driver adjusts size or ScalerCropMaximum | **High** (new, untested sizes) | mode (size, fps), file, preview |
| 8175273 camera: Clear HDR holds ISO and WB, caps ISO per mode | H12 turns auto ISO and auto WB off (held values), ISO cap `max12 = 720` | **Medium** | exposure, WB, file look |
| 6d217c7 / 97adea0 | Refactor of the same cap (`clearHdrIsoCap`), `iso_max` in state | low | exposure |
| b5b787e / 60645d4 / b0e90ad | Auto ISO / Auto WB not offered in Clear HDR on dials and WebUI | low | UI only |
| f2ebe6e camera: Clear HDR records uncompressed | Turning Clear HDR on sets `cdngCompression = Uncompressed` | low-medium | file layout |
| 3cae990 / e16033e / 88e644d / 0041ba0 / ab972fe | Mode ladder: a rung carries `clearHdr`, bits, compression (default `none` in HDR), lossy refused in HDR; a ladder can switch into H12 between takes | medium (mode chosen by FPS, not the user) | mode |
| d44b177 drop-frames (Log, etc.) | CineMate Log. For H12 cDNG: `cdngLogBits` = 12 when Log is on, composed table CCMP-expand then Log, LinearizationTable = Log inverse, black 3200 | low (off by default) | file, only with Log on |
| fc7eb16 / 351a3ee camera: copy worker | `compressClearHdrFrame` moves from the libcamera callback to the copy worker (`copy.mapCodes12`). Same gate, same function | low | file |
| db17860 / 26da30e | 8 raw buffers in Clear HDR; buffer count by medium | low | drops only |
| e55557d cdng: direct payload write | Only unpacked 16-bit and 8-bit take the direct path. H12 cDNG is Bits12: scratch path as before | none | - |
| 5e9dd1a mlv: same black and white as cDNG | MLV H12 (stored as linear 16-bit): black 200 -> 3201. Main declared 200 on 16-bit data | fix (was wrong on main) | MLV file |
| 31d5418 / b5847c7 | 16-bit fps cap added, then removed. No H12 effect | none | - |
| 8e8ea2e / ac00fb0 presets | Presets carry `clearHdr` and the HDR knobs (EXP_TH, blend, gain adder) and push them live | low | sensor merge if a preset holds odd knobs |
| f91fafa / 1af26c8 Core clips and frame renderer | New Core reader applies the LinearizationTable; H12 renders on the 3200..65520 scale like H16 | low | WebUI player |
| e625c68 preview TDN off | Preview tuning copy without TDN, all modes | low, not H12-specific | preview noise |
| c48e693 IMX283 | `clearHdr=false` when another sensor is present and no imx585 subdev | none for IMX585 | - |
| 66b324d / eaf9538 / ff33d2d / e25fd2b / 15bba86 / 920beb0 / 1ef94fe / da8ca9f / b8ee23f / 8bcc5dd / e58ae40 / fee41e6 / 3c4f07d | WebUI: H12 class pills, labels, ladder editor, time left by bit depth | none for the file | WebUI labels |
| 80ddac1 / faa2958 / d7ff071 / f4fb084 / 916c1dd / f5a61b8 / 243fe2c / dcf09ee / 014a2bf / 92d0970 / 2955ef8 / fa19856 / 646a194 / 9a081dd / f95567d / ce0bd90 / d7dd337 / ba0658d | Hit only in the `commands` list, labels, a clip-name token, WAV `bitsPerSample`, IMX283 code, or an action to toggle Clear HDR | none | - |

## Findings

### F1. H12 is no longer pinned to 4K (caa0153). Confirmed change, effect probable.

- Main: `src/camera/CameraController.cpp:2824-2827@main`
  "Clear HDR exists only at 4K on the driver ... `if (sensorFamily == SensorFamily::Imx585 && settings.clearHdr) settings.resolution = Resolution{ 3840, 2160 };`"
- Port: `src/camera/CameraController.cpp:3526-3530@cinemate-port` pins 4K for the **mono** sensor only, then
  `normalizedResolutionForSensor(..., settings.rawBitDepth, settings.clearHdr)` snaps to the nearest H12 row.
- H12 rows: `src/camera/Imx585Modes.hpp:78-87@cinemate-port` (binned 1920x1080 first, 3840 crops down to 1504,
  1920/2048 crops, 1440x1080).
- Core assumes transport == active for H12 (no optical-black rows): `Imx585Modes.hpp:6-9@cinemate-port`.
- The driver still carries this note in its stream-on path, unchanged from `apertar`:
  `imx585.c:4139@cinemate-port` "Known issue: ClearHDR mode leaves ~19 OB rows at the top of the cropped buffer,
  regardless of PIX_VST ... HDR keeps the residual top-bar." Another note (`imx585.c:582@cinemate-port`) says the
  12-bit modes emit no OB. The two notes disagree. Main never ran H12 crops, so neither was tested through Core.
- Binned H12 at 1920x1080 is offered on colour (`imx585.c` get_mode_table comment: "colour passed binned 12-bit CCMP
  Clear HDR on the 2026-08-10 golden captures"). Main never ran it through Core.
- Side note: `sensorModeForRequestedResolution` looks H12 up in the **S12** table:
  `CameraController.cpp:2670@cinemate-port` `classFor(selection.bitDepth, selection.bitDepth == 16)`.
  Harmless today: every H12 size is also in S12 with the same binning and transport. It breaks if the tables diverge.
- Symptom if this is it: only at non-4K sizes. Recorded file and preview with a dark band at the top (OB rows), or a
  size or binning other than the one picked. Also a size jump when Clear HDR is turned on from an SDR size H12 lacks
  (e.g. 1920x1036 binned snaps to the nearest H12 row).
- Settle: ask which resolution. On the Pi, record 1 s of H12 at 3840x2160 and at 3840x1608 and at binned 1920x1080.
  Check the Core log line `ApertarCore camera configured: ... stream=... storage_bits=12 packing=...`. Check
  `max(row 0..30)` against the scene in a DNG (needs the Pi).

### F2. H12 exposure and WB are manual and capped (8175273). Confirmed.

- `CameraController.cpp:3073-3098@cinemate-port` `enforceClearHdrExposureRules`: `isoAuto=false`,
  `whiteBalanceAuto=false`, `iso = min(iso, cap)`.
- Cap: `CameraController.cpp:2938@cinemate-port` `uint32_t max12 = 720;` (`max16 = 1585`).
  Override in `apertar-hardware.conf [camera] clear_hdr_iso_max_12bit`.
- Main has no such rule: no `isoAutoAfterClearHdr` field in `include/apertar/core/Types.hpp@main`, and main's
  sanitiser (`CameraController.cpp:2800-2840@main`) leaves auto ISO and WB alone.
- On H12, libcamera linearises the AGC statistics with CcmpUnwrap (`ccmp_unwrap.h:22-26@libcamera apertar`), so
  AE and AWB were usable on main.
- Symptom if this is it: after turning 12-bit Clear HDR on, exposure and WB freeze at the last SDR values. ISO
  above 720 is silently lowered. The image looks darker, or has a colour cast that stays as the light changes.
  16-bit shows the same freeze, but with cap 1585.
- Settle: `get_state` on the Pi before and after `set_clear_hdr enabled=true` at `raw_bit_depth=12`: compare
  `iso`, `iso_auto`, `wb_auto`, `iso_max`.

### F3. Clear HDR switches cDNG to Uncompressed (f2ebe6e). Confirmed change, low risk.

- `CameraController.cpp:3028-3032@cinemate-port` `applyClearHdrCompression`: Clear HDR on -> `Uncompressed`.
  Ladder default for a Clear HDR rung is `none` (`ModeLadder.hpp:43@cinemate-port`).
- H12 codes then go through the 12-bit packed uncompressed writer (`writeDngRowBytes`, scratch path, because
  `rowCopyIsIdentity` is false for Bits12, `CdngEncoder.cpp:1989@cinemate-port`). SDR 12-bit uncompressed uses the
  same writer, and so does the new Core reader (`DngFrameReader.hpp:69-72@cinemate-port`, DNG big-endian 12-bit
  packing).
- Symptom if this is it: a raw converter that reads uncompressed 12-bit with a LinearizationTable wrongly. Unlikely.
- Settle: one H12 uncompressed DNG and one H12 lossless DNG of the same scene. Compare them after linearisation
  (`tools/` host reader or rawpy on the desk).

### F4. Log on H12 (d44b177). Confirmed path, only with Log on.

- `include/apertar/core/Types.hpp:362-371@cinemate-port`: H12 cDNG with Log -> 12 stored bits.
- `CameraController.cpp:3982-4000@cinemate-port`: `codes12` -> source 16, black 3200, white 65520.
- `CameraController.cpp:4032-4033@cinemate-port`: `buildComposed(*params, ccmp::expansionTable())` and
  `containerTable(forward, 0, ccmp::compressionLut())`.
- `CameraController.cpp:5124-5133@cinemate-port`: the copy worker applies the table and replaces the
  LinearizationTable with the Log inverse. Black is 3200 on container scale.
- `LogCurve.hpp:166-177@cinemate-port`: the forward table is indexed by CCMP code; the inverse is that of the 16-bit
  curve. The maths is consistent.
- Default `cdngLog = Off` (`Types.hpp:192@cinemate-port`). A ladder rung with `:log` turns it on
  (`ModeLadder.hpp:168@cinemate-port`).
- Symptom if this is it: only with Log on. The H12 file holds Log codes. Any viewer that skips the
  LinearizationTable shows a flat, washed-out picture. The touch UI and HDMI may also apply a Log view
  (`cdng_log_applied`, `CameraController.cpp:12873@cinemate-port`). Not H12-specific: 16-bit Log behaves the same.
- Settle: `get_state` -> `cdng_log`, `cdng_log_applied`; Core log line `CineMate Log 16->12 ... composed with the CCMP expansion`.

### F5. CCMP mapping preserved through the copy-worker move (fc7eb16, 351a3ee). Confirmed.

- Main: `CameraController.cpp:7273-7275@main`, applied in the libcamera callback after the copy.
- Port: the gate is computed at enqueue, `CameraController.cpp:9491-9492@cinemate-port`:
  `copy.mapCodes12 = clearHdrStoresCodes12(settings_) && rawInfo.packing == PixelPacking::Unpacked && rawInfo.unpackedBytesPerSample == 2u && rawInfo.bitDepth == RawBitDepth::Bits12;`
  The mapping is applied on the worker copy, `CameraController.cpp:5134-5135@cinemate-port`.
- `clearHdrStoresCodes12`, `compressClearHdrFrame`, `storageRawBitDepthForSettings` are byte-identical
  (`CameraController.cpp:1640-1693@cinemate-port` vs `1328-1360@main`). So is the metadata block that sets the
  table and black 3200 (`4090-4096@cinemate-port` vs `3280-3286@main`).
- Pre-existing gap, same on main: the LinearizationTable is attached whenever `clearHdrStoresCodes12` holds
  (`4090@cinemate-port`), but the codes are mapped only for unpacked 16-bit containers. If the raw stream ever
  arrives as PISP_COMP1, the file holds linear values under a CCMP table, and every value above the first knee
  blows out. Same code on main, so this is not a port regression. It becomes one only if the port's mode or format
  choice changes the stream format (see F1).
- Settle: the Core log line `storage_bits=12 packing=unpacked container_bytes=2` on the Pi for each H12 size.

### F6. CCMP table still matches driver and libcamera. Confirmed (C1).

- `src/cdng/ClearHdrCcmp.hpp` is unchanged main..port (no diff).
- Driver defaults are unchanged apertar -> cinemate-port: `grad_thresh_def[2] = { 500, 11500 }`
  (`imx585.c:3688@cinemate-port`), ACMP1 def 6, ACMP2 def 4, `IMX585_BLKLEVEL_DEFAULT 50` (x4 = 200 in libcamera).
- Core never writes GRAD_TH, GRAD_COMP_L/H or BRIGHTNESS. It writes only `+0` EXP_TH, `+1` blend and `+5` gain adder
  (`CameraController.cpp:7034-7037@cinemate-port`).
- C1 host check: libcamera `CcmpUnwrap::setParams` formula (`ccmp_unwrap.cpp:31-130@apertar 6b0b49f`) vs Core
  `ccmp::expansionTable()`: 0 mismatches over 4096 codes, `T[200]=3200`, `T[4095]=65520`, and `compressionLut`
  round-trips every distinct entry. Codes 0..199 all expand to 3200, so black and sub-black pixels are stored as code 0.
  This is correct under the table and the same as on main.
  Test source: `/tmp/claude-0/-home-user/c92f0a57-d507-5425-af34-ea239a4bf210/scratchpad/ccmpchk/t.cpp`.

### F7. DNG and MLV level refactor (5e9dd1a). Confirmed.

- cDNG: `kDngBlackLevel`/`whiteLevel`/`blackLevelForEncodedDepth` were replaced by `kDefaultSourceBlackLevel`,
  `encodedWhiteLevel` and `encodedBlackLevel` (`BlackLevel.hpp:21-38@cinemate-port`) with the same arithmetic. H12 cDNG still
  declares BlackLevel 3200 and WhiteLevel = `linearizationTable.back()` = 65520 (`CdngEncoder.cpp:1490-1491@cinemate-port`).
- MLV H12 is stored as libcamera's linear 16-bit. Main declared black 200 on that data
  (`MlvEncoder.cpp:1156@main`, no 16-bit scaling). The port declares 3201 (`MlvEncoder.cpp:1154@cinemate-port`).
  This fixes main. A converter now subtracts the real pedestal, so MLV H12 looks darker in the shadows than it did
  on main. That is correct, but a user can see it as "different".

### F8. New Core playback renderer handles H12. Confirmed.

- `DngTags.hpp:262-267@cinemate-port` reads BlackLevel, WhiteLevel and the LinearizationTable.
  `DngFrameReader.hpp:115-121@cinemate-port` applies the table. `RawRender.hpp:142-144@cinemate-port` normalises
  with black and white after linearisation (3200..65520), the same scale as H16.
- `ClipProbe.hpp:175@cinemate-port` labels it "Clear HDR 12-bit companded" (label only).
- Not checked: the touch UI player and the UI-side renderers (other agents).

## Most likely Core-side causes, ranked

1. **caa0153**, `CameraController.cpp:3526-3530@cinemate-port` (4K pin now mono-only) plus `Imx585Modes.hpp:78-87`. Any non-4K H12 take has never run on this stack.
2. **8175273**, `CameraController.cpp:3073-3098` and `2938@cinemate-port`. Manual ISO and WB, ISO <= 720, in H12.
3. **d44b177**, only if Log is on: `CameraController.cpp:5124-5133@cinemate-port`.
4. **f2ebe6e**, `CameraController.cpp:3028-3032@cinemate-port`. Uncompressed H12. Low.

For 4K H12 with Log off, Core writes the same file as main. If the owner's "strange output" happens there, look
outside Core: the libcamera worker thread (6b0b49f, an in-place CcmpUnwrap pass racing the completed request?),
the driver branch, the UI renderers.

## Open questions

- Which resolution, recording format (cDNG / MLV), compression, and whether Log or the Mode Ladder were on.
- libcamera `6b0b49f` "optional worker thread for the raw CPU passes": does the in-place CcmpUnwrap finish before the
  request reaches Core? Core now holds requests longer (copy worker, 351a3ee). That changes the timing, not the
  order. Settle: read `pisp.cpp:2141` and `3100@apertar` and the worker's completion path (libcamera agent).
- Does the driver emit OB rows at the top in H12 crops (`imx585.c:4139` vs `:582@cinemate-port`)? Needs the Pi.
