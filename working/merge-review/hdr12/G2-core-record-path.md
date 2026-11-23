# G2: Core's record path for 12-bit Clear HDR (IMX585) at cinemate-port

Assignment G2 of the "12 bit clear HDR shows strange output" investigation. Read-only on the code repos.
Nothing ran on a camera. Written 2026-11-17 in a cloud session (x86_64, no Pi, no sensor).

| Ref used | What |
| --- | --- |
| Core `cinemate-port` `01f170c` (`/home/user/Apertar-Core`) | every `path:line` without a ref is read here |
| Core fork main `f60e301` (`/home/user/wt/core-main`) | `@main`, to see what the port changed |
| Core upstream 1.6.0 `35dbe67` (`/home/user/wt/core-upstream`) | `@upstream-1.6.0`, the measuring stick |
| libcamera `apertar` `6b0b49f` (`/home/user/tiramisioux/libcamera`) | only to pin what Core assumes it receives |
| driver `cinemate-port` `cd548ef`, `apertar` `e5b74d3` | only the CCMP control ids and defaults |

Short names: **H12** = Clear HDR 12-bit, **H16** = Clear HDR 16-bit, **S12** = SDR 12-bit (the class names of
`src/camera/Imx585Modes.hpp:11`). `CC` = `src/camera/CameraController.cpp`. LSB16 = one step on the 16-bit scale.

Labels: **confirmed** (read in code at the ref, or run on this host with the real encoder), **probable**
(inferred, reason given), **unconfirmed** (the command that settles it is named).

Host evidence used (section 10): the real `CdngEncoder`, `LosslessJpegEncoder` and `MlvEncoder` of `01f170c`
compiled with plain `g++`, fed with the frame view and metadata that `CC` builds in H12, read back with the port's
own `src/playback/DngFrameReader.hpp`. The host tests `tools/log_curve_test.cpp`, `black_level_test.cpp`,
`dng_limits_test.cpp`, `imx585_modes_test.cpp` pass at `01f170c`.

## 1. Short answer

- Core asks the sensor for the 12-bit mode (`SRGGB12_CSI2P`, sensor bit depth 12, transport size = active size)
  and then **assumes** libcamera hands back unpacked 16-bit **linear** samples, black 3200, white 65520
  (`CC:1684-1685`). Core never checks that. In Clear HDR the exact-mode check skips the bit-depth test (`CC:8498`).
- cDNG: the copy worker maps every linear sample back to its 12-bit CCMP code (`CC:5134-5135`, `CC:1647-1658`).
  The encoder writes BitsPerSample 12, the 4096-entry expansion as LinearizationTable, BlackLevel 3200,
  WhiteLevel 65520. Black and white are in the linearised domain, which is where a DNG reader applies them.
  Host run: the port's reader gets back libcamera's values with 0 differing samples, uncompressed and lossless.
- MLV: no table exists in MLV, so H12 is stored as linear 16-bit: RAWI bits 16, black 3201, white 65535. An H12
  MLV is a 16-bit file. Log is refused in MLV. Lossy DNG is refused in all Clear HDR.
- Log on (cDNG): one table lookup replaces the CCMP mapping. Stored: 12-bit Log codes plus the 16->12 Log inverse
  table, BlackLevel 3200, WhiteLevel 65520. Largest error against libcamera's value: 69 LSB16.
- **One real defect sits in this path (G2-F1).** The storage depth (12 for cDNG, 16 for MLV) is fixed when the
  camera is configured, from the recording format. Switching cDNG <-> MLV does not reconfigure when size, depth
  and Clear HDR stay the same. After such a switch in H12: an MLV take stores the low 12 bits of the linear
  16-bit samples (a wrapped picture; the same loss the commit message of `e1c10cd@main` calls "purple with
  speckle"), or a cDNG take fails at its first frame with "Invalid RAW linearization table.". H16 and S12 cannot
  be hit. The defect is on fork main since `57c8fb0`; the port carries it.
- After a fresh configure, Core's writers store what libcamera delivered, to within one table step. A strange
  picture in that state comes from before Core (libcamera's expansion, the driver mode, the sensor knobs) or from
  the reader. A 12-bit Clear HDR MLV of the same scene is the split test: it holds libcamera's samples untouched.
- The port did not change the H12 arithmetic. `ClearHdrCcmp.hpp` is byte-identical to fork main. The new "write
  straight from the frame" path is not taken by 12-bit views. The black and white helpers moved to
  `BlackLevel.hpp` with the same numbers. The copy worker does the same lookup on another thread.

## 2. The frame, hop by hop (H12, cDNG, Log off, fresh configure)

| # | Hop | What Core does | Evidence |
| --- | --- | --- | --- |
| 1 | Settings | Clear HDR survives only on an IMX585 and in a raw format. Depth becomes 12 or 16. Size becomes the nearest row of class H12 (29 rows, first row 1920x1080 **binned**). Auto ISO and auto WB off, ISO capped at 720 | `CC:3511-3512`, `CC:3520-3521`, `CC:3451-3453`, `CC:3530-3532`, `CC:2831-2835`, `Imx585Modes.hpp:78-87`, `CC:3073-3086`, `CC:2937-2939` |
| 2 | Sensor switches | Before libcamera starts: `wide_dynamic_range=1` written and read back; merge knobs written: threshold (control +0), blend (+1), gain adder (+5). The gradation controls (+2, +3, +4) and the black level are never written by Core | `CC:7333-7335`, `CC:7005-7032`, `CC:7034-7037`, `CC:7076-7084`; `grep -rn "V4L2_CID_BRIGHTNESS\|GRAD" src include` prints nothing |
| 3 | Mode candidate | One candidate. Pixel format `SRGGB12_CSI2P`, bit depth 12. The class lookup is `classFor(12, 12 == 16)` = **S12**, not H12: the function has no Clear HDR input. Transport size = active size (only H16 adds optical-black rows) | `CC:8283-8286`, `CC:2618-2627`, `CC:2591-2603`, `CC:2667-2679`, `Imx585Modes.hpp:117-122`, `:203-208` |
| 4 | Configure | Roles VideoRecording + Raw. Raw stream: that pixel format, that size, 8 buffers. Explicit sensor configuration: output size, bit depth 12. `validate()` Invalid or `configure()` failure rejects the candidate | `CC:8332-8337`, `CC:8410-8418`, `CC:1338`, `CC:1458-1469`, `CC:8435-8460` |
| 5 | Exact-mode check | Raw stream size must equal the request. **Bit depth is not checked in Clear HDR** (`else if (!sanitized.clearHdr)`). ScalerCropMaximum must equal the H12 row x binning | `CC:8485-8529`, quote: `CC:8498` `else if (!sanitized.clearHdr) {     // Clear HDR 12-bit reads out linear 16-bit samples` |
| 6 | What Core believes it got | Reads the configured stream: format name, stride, frame size. `formatToRawView` maps `SRGGB16` to 16-bit unpacked. Transport depth 16, 2 bytes per sample. Then the **storage depth** replaces the stream depth: `storageRawBitDepthForSettings()` = 12 for cDNG, 16 for MLV | `CC:8584-8624`, `CC:3892`, `CC:1682-1694`, `CC:1640-1644` |
| 7 | Journal line | `ApertarCore camera configured: ... format=SRGGB16 stride=... storage_bits=12 packing=unpacked transport_bits=16 container_bytes=2` (cDNG). MLV: `storage_bits=16`, no `transport_bits` | `CC:8644-8661` |
| 8 | Buffers | Clear HDR + unpacked: Core allocates CPU-cached dma-bufs for the raw stream and maps them | `CC:8701-8716` |
| 9 | Frame completes | `recordRawFrame`: active offset 0, size = stride x height (no crop in H12). Builds the metadata (hop 10) and a `PendingCopy`: `mapCodes12` = settings say codes12 **and** stream is unpacked, 2 bytes, storage depth 12. View: width, height, stride, `bitDepth` = storage depth (12), `unpackedBytesPerSample` 2, `sampleBits` 12, packing unpacked, pattern | `CC:9388-9517`, quote `CC:9491-9492`, `CC:9493-9501` |
| 10 | Metadata | Black levels from libcamera's `SensorBlackLevels` / 16, else tuning, else 200. Then, if settings say codes12 and the sensor is an IMX585: table = `ccmp::expansionTable()`, all four black levels = 3200, `blackLevelsOnContainerScale = true`. This test does **not** look at the stream | `CC:4072-4096` |
| 11 | Copy worker | sync dma-buf, `memcpy` to a pooled buffer, give the request back. Log take: apply the Log copy table. Else if `mapCodes12`: `compressClearHdrFrame` = `row[x] = lut[row[x]]` with `ccmp::compressionLut()`. Samples are now codes 0..4095 in 16-bit containers | `CC:5088-5149`, `CC:1647-1658` |
| 12 | Queue | `enqueue`: clip name, frame file name, compression = the cDNG compression setting | `CC:4969-5022`, `CC:4998` |
| 13 | Writer | One `CdngEncoder` per writer thread per take. `writeDngFile` | `CC:5231-5295`, `CC:5245`, `CC:4378-4379` |
| 14 | Encoder | Section 3 | `src/cdng/CdngEncoder.cpp` |

Same hops for H16: candidate `SRGGB16`, depth 16, class H16, transport = active + 40 rows (20 binned); the rows
are cropped (`CC:3663`, `CC:3727-3740`); storage depth 16; no `mapCodes12`; no table. For S12 on a Pi 5 / CM5 the
stream comes back as `PISP_COMP1`; storage depth 12 (`CC:8616-8617`); no copy-side mapping.

What `RawFrameView` and `Metadata` carry about Clear HDR (confirmed):

| Field | Filled where | H12 cDNG value |
| --- | --- | --- |
| `RawFrameView::bitDepth` (`include/apertar/core/Types.hpp:264`) | `CC:9496`; overwritten by a Log take `CC:5127` | 12 (the storage depth, not the stream depth) |
| `RawFrameView::unpackedBytesPerSample` (`:265`) | `CC:9497` | 2 |
| `RawFrameView::sampleBits` (`:268`) | `CC:9498` | 12 (`settings_.rawBitDepth`); only the Lossy encoder reads it |
| `RawFrameView::gradationCompanded` (`:269`) | **never set to true anywhere** (`grep -rn gradationCompanded src include`: read at `src/lossydng/LossyDngEncoder.cpp:456`, `:464`, `:468`; assigned false at `:534`). Same on `@main` and `@upstream-1.6.0` | false. H12 codes are companded and the flag says no. No effect: only the Lossy encoder reads it and Lossy is refused in Clear HDR |
| `Metadata::linearizationTable` (`src/cdng/CdngEncoder.hpp:34`) | `CC:4092`; Log take `CC:5129`; Lossy `LossyDngEncoder.cpp:544` | 4096 entries, static storage |
| `Metadata::blackLevels`, `blackLevelsOnContainerScale` (`CdngEncoder.hpp:57-58`) | `CC:4089`, `CC:4093-4095`; Log `CC:5130-5133` | 3200 x4, true |
| white level | no field. Derived in the encoder: `table.back()` or full scale of the depth (`CdngEncoder.cpp:1490-1491`) | 65520 |
| "this is Clear HDR" | no field in the view or the metadata. Every consumer infers it from (depth, table) | - |

## 3. What the encoders write

DNG readers apply LinearizationTable first, then BlackLevel and WhiteLevel on the table's output.

### 3.1 cDNG (`src/cdng/CdngEncoder.cpp`)

| Step | Code | H12 result |
| --- | --- | --- |
| Table size guard | `:1338-1340`: table size must be `1 << bits(frame.bitDepth)`, else `throw "Invalid RAW linearization table."` | 4096 == 1 << 12, passes |
| Layout | `prepareUnpackedLayout` `:1968-1978`: depth 12, row bytes = width x 12 / 8 | 12-bit packed strip |
| Payload, uncompressed | `writeRawPayload` `:1980-2033`. `rowCopyIsIdentity` `:1079-1088` is true only for 16-bit and 1-byte 8-bit views, so H12 takes the scratch path: `writeDngRowBytes` `:1171-1176` -> `Csi2RawConverter::packDng12Row` `:1290-1301` | 12 bits per sample, MSB first, **`src[x] & 0x0FFF`**: a value above 4095 loses its high bits without a word |
| Payload, lossless | `:1378-1471`. `readJpegSamples` `:1203-1212` reads the 16-bit container as is (no mask). `jpegEncoder_.begin(..., 12, ...)` `:1420`. Tiles of 128 rows `:55-70`, `:1354` | Compression 7, 12-bit lossless JPEG of the codes |
| Lossy inputs | `jpegSampleLookup`, `jpegSampleShift`, `compactJpegCodes` (`:1342-1346`, `:1399-1407`, `:1420-1421`) are set only by `LossyDngEncoder.cpp:541-545` | not used. Lossy + Clear HDR is refused: `include/apertar/core/RecordingCapabilities.hpp:76-78`, called at `CC:11313`, `CC:12002`, `CC:12737` |
| BitsPerSample (258) | `:1472`, `:1650` | 12 |
| BlackLevel (0xC61A) | `:1473-1481` -> `encodedBlackLevel(3200, Bits12, true)` -> `src/cdng/BlackLevel.hpp:12-19`: on container scale the value is kept, then clamped to `white - 1` of the **12-bit** depth (4094) | 3200/1 x4, RATIONAL. Linearised domain. Correct. (3200 passes only because it is below 4094, G2-F9) |
| LinearizationTable (0xC618) | `:1704-1706`, SHORT x 4096 | `[0..201]=3200, [202]=3201, [700]=3693, [701]=3757, [871]=14505, [872]=14576, [4095]=65520` |
| WhiteLevel (0xC61D) | `:1490-1491`: `table.back()` when a table is attached, `:1707` | 65520, LONG. Linearised domain. Correct |
| Other | BlackLevelRepeatDim 2x2 `:1696-1701`; DNGVersion 1.4.0.0, backward 1.3.0.0 `:1684-1687`; UniqueCameraModel "Blackmagic Micro Cinema Camera" `CC:3846-3851`; tags sorted ascending `src/cdng/IfdBuilder.hpp:101-115` | - |
| IFD template cache | `:1625-1638`, key `:1569-1595`. The table and WhiteLevel are inside the cached bytes and **not** in the key. Safe today: one encoder per writer thread per take (`CC:5245`), the clip name is part of the match (`:1630`), lossless never reuses the template (`:1626`) | G2-F10 |

Every case, with numbers (confirmed by the host run unless marked):

| Case | BitsPerSample | Payload | Table | Black | White | Domain of black / white |
| --- | --- | --- | --- | --- | --- | --- |
| H12 cDNG uncompressed, Log off | 12 | CCMP codes 0 and 202..4095, MSB-first packed | 4096, CCMP expansion | 3200 | 65520 | linearised (table output). Consistent |
| H12 cDNG lossless, Log off | 12 | same codes, lossless JPEG tiles | same | 3200 | 65520 | linearised. Consistent |
| H12 cDNG, Log on | 12 | Log codes 32..4095 | 4096, Log inverse: `[0]=2721 [31]=3192 [32]=3200 [4095]=65520` | 3200 | 65520 | linearised. Consistent |
| H12 MLV | 16 | linear 3200..65520, LE16 | none | 3201 | 65535 | stored = linear. Black 1 high, white 15 above the data maximum |
| H12 still (photo mode) DNG | 16 | linear | none | 3201 | 65535 | same as H16 (`CC:9629-9637`, `CC:1642`). Read in code, not run |
| H12 Lossy DNG | - | refused | - | - | - | - |
| H16 cDNG, Log off | 16 | linear, written straight from the frame | none | 3201 (200 x 65535 / 4095) | 65535 | stored = linear |
| H16 cDNG, Log on | 12 | Log codes | 4096, same Log inverse | 3200 | 65520 | linearised. Read in code (`CC:3996-3998`, `CC:4035-4037`), not run |
| S12 cDNG (PISP_COMP1) | 12 | top 12 bits of the PiSP decode | none | `SensorBlackLevels` / 16 (200 for 3200) | 4095 | stored = linear. Read in code, not run |
| Stale H12 MLV (G2-F1) | 12 | **low 12 bits of the linear samples** | none | 200 | 4095 | wrong: data is 16-bit linear |

### 3.2 MLV (`src/mlv/MlvEncoder.cpp`)

| Step | Code | H12 result (fresh configure) |
| --- | --- | --- |
| Layout | `prepareRawLayout` `:816-844`: depth = `frame.bitDepth` | 16, row bytes = width x 2 |
| Payload | `writeRawPayload` `:903-904`: 16-bit view is copied | linear samples as delivered |
| RAWI levels | `writeRawInfoBlock` `:1152-1158` -> `encodedBlackLevel(blackLevels[0], Bits16, false)`, `encodedWhiteLevel(Bits16)` (`BlackLevel.hpp:22-35`) | bits 16, black 3201, white 65535 |
| A 12-bit view | `:917-918` -> `packMlvRaw12Row` -> `(p >> 0) & 0x0fff` (`:333-336`; NEON `:303`) | used only with a stale depth: wraps |

The port changed the MLV black (`5e9dd1a`): `@main` `src/mlv/MlvEncoder.cpp:166-176` scaled only for 8 and 10 bits,
so a 16-bit container declared black 200. The port declares 3201. That is a fix, for H12 and H16 alike.

## 4. What `src/cdng/ClearHdrCcmp.hpp` provides

| Item | Value | Evidence |
| --- | --- | --- |
| Parameters, fixed | knee1 500, knee2 11500, slope1 6 (1/64), slope2 4 (1/16), black 200 | `:24-30` |
| `kBlack16` | 3200 | `:32` |
| `expansionTable()` | 4096 entries, code -> linear 16-bit: `black x 16 + L x (65520 - 3200) / L(4095)`, `L(4095) = 63084` | `:47-65` |
| `compressionLut()` | 65536 entries, linear -> lowest code whose expansion reaches the value | `:69-83` |
| Unchanged by the port | `git -C /home/user/Apertar-Core diff --stat origin/main cinemate-port -- src/cdng/ClearHdrCcmp.hpp` is empty | confirmed |

Host numbers (confirmed, the probes named at the end of section 10):

- The table equals libcamera's `CcmpUnwrap` LUT (formula transcribed from
  `src/libcamera/pipeline/rpi/pisp/ccmp_unwrap.cpp:54-129@6b0b49f`) for the driver defaults 500 / 11500 / 6 / 4 /
  black 200: 0 differing entries. Driver defaults are the same on both branches (`imx585.c:3688`, `:3725`, `:3736`,
  `:159@cd548ef`; `:1822`, `:1859`, `:1870`, `:149@e5b74d3`).
- `expansion[compression[v]] == v` for all 4096 table values.
- Codes 0..201 all expand to 3200. The compression LUT sends 3200 to code **0**. A stored H12 frame never holds
  codes 1..201. Values below black do not exist: libcamera clips them first (`ccmp_unwrap.cpp:121-122@6b0b49f`).
- Table steps: 1 LSB16 for codes 202..700, 64 for 701..871, 71 at 872, 16 above.
- libcamera reads the four parameters **live** from the driver (`pisp.cpp:2990-3023@6b0b49f`); Core's are constants.

## 5. The Log switch in H12 (`src/cdng/LogCurve.hpp`)

| Step | Code | H12 |
| --- | --- | --- |
| Stored depth | `cdngLogBits` `include/apertar/core/Types.hpp:364-371` | cDNG: On = 12, Off = 0 (linear path). Any other 12-bit source would give 10 |
| Refusals | MLV: "Log is not supported in MLV yet." `CC:11423-11425`. H.264, ProRes `CC:11417-11422`. Lossy + Clear HDR is refused before Log matters | - |
| Plan | `planCdngLog` `CC:3974-4013`: `codes12` true; needs an unpacked 2-byte stream (`CC:3983-3988`); source depth forced to 16 (`CC:3991`); black 3200, white 65520 (`CC:3996-3998`); `makeParams(16, 12, 3200, 65520)` | curve 16->12, mu 10000, footroom 32 codes / 487 LSB (`LogCurve.hpp:65-69`) |
| Tables | `buildCdngLogTake` `CC:4016-4044`: `buildComposed(params, expansionTable())` (`LogCurve.hpp:166-176`): forward[code] = Log code of the code's expansion, 4096 entries; inverse = the plain 16->12 inverse, 4096 entries. `copyTable = containerTable(forward, 0, compressionLut())` (`LogCurve.hpp:191-203`), 65536 entries | journal: `ApertarCore CineMate Log 16->12 mu=10000 black=3200 white=65520 footroom=32/487 composed with the CCMP expansion` (`CC:4041-4042`) |
| Applied | copy worker `CC:5120-5133`: only if the view is unpacked, 2 bytes, depth == `viewDepth` (12) and `mapCodes12 == codes12`. One lookup replaces `compressClearHdrFrame`. Then view depth = 12, table = inverse, black = 3200 on container scale | BitsPerSample 12, WhiteLevel = `inverse.back()` = 65520 |
| If refused | the take records linear, as with Log off (`CC:4015`, `CC:5134-5135`) | CCMP codes + CCMP table |

Host numbers (confirmed): `copyTable[3200] = 32`, `copyTable[65520] = copyTable[65535] = 4095`; decoded against
libcamera's values: largest error 69 LSB16, 0.22 % of the signal above black at worst. No sample lands in the
footroom (codes 0..31): the input never goes below 3200.

In S12 on a Pi 5 the stream is `PISP_COMP1`, so the cDNG copy worker cannot map it and Log records linear
(`CC:3983-3987`). With Log on, H12 and H16 produce the same kind of file. With Log off they do not.

## 6. Where H12 leaves the H16 and S12 paths

| Decision | H12 | H16 | S12 (Pi 5) | Keyed on | Evidence |
| --- | --- | --- | --- | --- | --- |
| Requested pixel format | `SRGGB12_CSI2P` | `SRGGB16` | `SRGGB12_CSI2P` | depth | `CC:2591-2603` |
| Class used for the transport size | S12 (not H12) | H16 | S12 | depth alone: `classFor(bits, bits == 16)` | `CC:2670` |
| Class used for the size list and the crop check | H12 | H16 | S12 | depth + Clear HDR | `CC:2831-2835`, `CC:8511` |
| Optical-black rows cropped | no | yes | no | `rawBitDepth == 16` alone | `CC:3663`, `Imx585Modes.hpp:203-208`, `:220-232` |
| Bit-depth test in the exact-mode check | skipped | skipped | done | Clear HDR alone | `CC:8498` |
| Stream Core expects back | unpacked u16, **software-expanded** | unpacked u16, native | `PISP_COMP1` | libcamera | `CC:1684-1685`, `CC:8499-8500` |
| Storage depth | 12 (cDNG) / 16 (MLV, still) | 16 | 12 | depth + Clear HDR + **format** + photo mode | `CC:1682-1694` |
| Copy-side mapping | linear -> CCMP code (or -> Log code) | none (or -> Log code) | none | `mapCodes12` | `CC:9491-9492`, `CC:5120-5136` |
| Table in the DNG | CCMP expansion (or Log inverse) | none (or Log inverse) | none | settings + sensor family | `CC:4090-4096` |
| Black in the DNG | 3200, fixed, ignores `SensorBlackLevels` | `SensorBlackLevels` / 16 scaled: 3201 | `SensorBlackLevels` / 16: 200 | table present | `CC:4093-4095`, `CdngEncoder.cpp:1476-1479` |
| White in the DNG | 65520 (`table.back()`) | 65535 | 4095 | table present, else depth | `CdngEncoder.cpp:1490-1491` |
| Payload write | packed through scratch, mask 0x0FFF | straight from the frame, one `write()` | PiSP decode, top 12 bits | view depth alone | `CdngEncoder.cpp:1079-1088`, `:1161-1176`, `:1989-1990` |
| Log | composed table, stored 12 | plain 16->12, stored 12 | refused (stream is PiSP) | depth + Clear HDR + format | `Types.hpp:368-369`, `CC:3982-3993` |
| MLV container | 16-bit | 16-bit | 12-bit | storage depth | `MlvEncoder.cpp:836-839` |
| ISO cap | 720 | 1585 | none | `rawBitDepth == 16` | `CC:3017-3023`, `CC:2937-2939` |
| Raw buffers | base 8, CPU-cached | base 8, CPU-cached | base 4 | Clear HDR | `CC:1334-1338`, `CC:1458-1469`, `CC:8703-8707` |
| Bytes-per-second estimate (remaining time) | 12 bits, also for MLV, which stores 16 | 16 | 12 | `rawBitDepth` alone | `src/ApertarCoreApp.cpp:5608-5617` |

## 7. Inconsistencies

| # | Kind | What | Effect today | Evidence |
| --- | --- | --- | --- | --- |
| I1 | one fact decided in three places | Storage depth: at configure, from settings (`CC:8615-8622`). Copy-side mapping: per frame, from settings **and** that stored depth (`CC:9491-9492`). Table and black 3200: per frame, from settings and sensor family only (`CC:4090`). No Clear HDR field travels with the frame | G2-F1 when the format changes without a reconfigure | section 2 table |
| I2 | wrong-size table | Table of 4096 entries on a 16-bit view | refused by the guard: the take fails (G2-F1 b) | `CdngEncoder.cpp:1338-1340` |
| I3 | depth label trusted without a range check | A 12-bit view is packed with `& 0x0FFF` (cDNG `CdngEncoder.cpp:1293-1294`, MLV `MlvEncoder.cpp:333-336`) | silent wrap when the samples are 16-bit linear (G2-F1 a). The same loss as the bug `e1c10cd@main` fixed for cDNG | - |
| I4 | wrong domain, latent | `blackLevelForSampleBits(black, bits, onContainerScale = true)` clamps a linearised-domain black to `2^bits - 2` of the stored depth. Host: 5000 on a 12-bit container becomes 4094 | none: 3200 < 4094 | `BlackLevel.hpp:12-19` |
| I5 | levels 1 and 15 off | Linear 16-bit files (H16 cDNG, H12/H16 MLV, stills) declare black 3201 and white 65535; the data has black 3200 and, in H12, never exceeds 65520 | 0.02 %: clipped highlights sit at 0.9998 | section 3 |
| I6 | branch keyed on depth alone | `CC:2670`: H12 is looked up in the S12 table | none today: every H12 row is an S12 row with the same binning and transport (host check: 29 rows, 0 differences). Breaks the day the two tables differ | `Imx585Modes.hpp:40-87` |
| I7 | check removed for a whole mode family | The exact-mode check drops the bit-depth test for all Clear HDR, although the stated reason covers only the stream format of H12 | none seen: libcamera's `validate()` still refuses a sensor configuration it cannot match | `CC:8498-8509` |
| I8 | fixed table, live source | Core's CCMP constants against libcamera's live control values | none at the driver defaults; G2-F3 otherwise | `ClearHdrCcmp.hpp:22-30`, `pisp.cpp:2990-3023@6b0b49f` |
| I9 | cache key narrower than the cached content | DNG IFD template holds the table and WhiteLevel; the key does not | none (encoder per take). `PhotoCaptureWriter` keeps one encoder for its life (`CC:6873`); stills never carry a table (`CC:1642`) | `CdngEncoder.cpp:1569-1638` |
| I10 | dead flag | `RawFrameView::gradationCompanded` never true | none | section 2 |
| I11 | estimate keyed on depth alone | H12 MLV stores 16 bits per sample; the bytes-per-second estimate uses 12 | remaining recording time reads about 33 % too long in H12 MLV | `ApertarCoreApp.cpp:5608-5617` |

Not found: a table attached to data that is already linear and written without an error; data shifted or scaled
twice. The H12 chain is expand (libcamera) -> compress (Core) -> expand (reader), or expand -> code -> Log code ->
Log inverse. Each pair cancels.

## 8. What the port changed in this path, against fork main

| Change | Touches H12? | Evidence |
| --- | --- | --- |
| `e55557d` direct write of 16-bit and 1-byte 8-bit payloads | no: a 12-bit view is not an identity copy | `CdngEncoder.cpp:1079-1088`; `git diff --minimal origin/main cinemate-port -- src/cdng/CdngEncoder.cpp` |
| Black / white helpers moved to `BlackLevel.hpp` | same arithmetic | `@main` `src/cdng/CdngEncoder.cpp:89-93`, `:113-118`, `:1356-1374` against `BlackLevel.hpp:22-35` |
| `5e9dd1a` MLV levels | H12 MLV black 200 -> 3201 | section 3.2 |
| Copy worker (`PendingCopy`, `copyLoop`) | the same LUT pass, moved off libcamera's completion thread | `@main` `src/camera/CameraController.cpp:7273-7275` against `CC:5134-5135` |
| Log (`d44b177`) | new first branch in the copy worker; replaces the table and the black for the take | section 5 |
| Driver mode tables (`Imx585Modes.hpp`) | H12 now runs at 29 sizes, the first one binned. Fork main forced every Clear HDR mode to 3840x2160; the port keeps that rule for the mono sensor only | `@main` `src/camera/CameraController.cpp:2824-2827` against `CC:3526-3531` |
| Reconfigure rule on a format change | unchanged, and that is the defect (G2-F1) | `@main` `src/camera/CameraController.cpp:8306-8309` = `CC:11387-11390` |

## 9. Findings

### G2-F1. cDNG <-> MLV switch in H12 leaves a stale storage depth (confirmed in code and on the host; not run on the Pi)

- Chain:
  - `CC:1640-1644`: `clearHdrStoresCodes12` is true only for `recordingFormat == RecordingFormat::Cdng`.
  - `CC:1686-1687`: Clear HDR storage depth = 12 if that is true, else 16.
  - `CC:8615-8622`: the only place that stores it in `rawStreamInfo_.bitDepth`, inside `configureAndStart`
    (`grep -n "rawStreamInfo_\.bitDepth = " src/camera/CameraController.cpp`: lines 8617, 8621).
  - `CC:11387-11390`: `setRecordingFormat` reconfigures only for a processed-video format, another size or
    another `rawBitDepth`. `CC:12725-12727` adds photo mode, ISP colour profile, Clear HDR. cDNG <-> MLV with the
    same mode and the default preview profile is none of these.
  - `CC:12758-12760` -> `applyControls` `CC:7565-7598`: sets controls and `settings_`. No stream state.
  - `CC:9491-9496`: per frame, `mapCodes12` and the table follow the **new** format; the view depth is the **old**
    storage depth.
- Upstream precedent: `@upstream-1.6.0` `src/camera/CameraController.cpp:1301-1308` makes the storage depth a
  function of `rawBitDepth` only, and `:7967-7969` reconfigures when `rawBitDepth` changes. Fork main `57c8fb0`
  added the format to the function (`@main` `:1328-1332`) without adding it to the rule. The preset path does
  reconfigure on a format change (`CC:12672`).
- Two outcomes, both H12 only:

| Direction | State after the switch | What is written | What the operator sees |
| --- | --- | --- | --- |
| a. configured as cDNG, now MLV | view depth 12, no mapping, no table | RAWI bits 12, black 200, white 4095; each sample = linear value & 0x0FFF (3200 -> 3200, 10016 -> 1824, 32405 -> 3733) | **MLV file**: black areas sit at 77 % of white ((3200 - 200) / (4095 - 200)), tones wrap every 4096 levels. Expected look: the one the commit message of `e1c10cd@main` gives for the same loss in a DNG, "purple with speckle", plus posterised bands. Preview and a cDNG take of the same session are fine |
| b. configured as MLV, now cDNG | view depth 16, no mapping, table of 4096 attached | nothing: `Invalid RAW linearization table.` at the first frame (`CdngEncoder.cpp:1338-1340`), then `failRecording` (`CC:5299-5304`) | **the take stops at once** with a recording error; journal `ApertarCore DNG write failed for ...: Invalid RAW linearization table.` |

- Once both format profiles hold the same H12 mode, every later switch skips the reconfigure
  (`CC:11338-11372` restores the per-format profile). The depth then stays at whatever the last reconfigure set.
- H16: storage depth 16 in both formats. S12: 12 in both. Neither can go stale.
- Cleared by anything that reconfigures: size, depth, Clear HDR toggle, photo mode, tuning file, Core restart.
- Could it be the owner's report: yes if MLV was part of the test. The MLV picture of outcome a is the symptom
  family the KB records for 2026-10-25 (low-12-bit wrap). Not known which outputs the owner looked at.
- Settle on the Pi (5 minutes): section 11, check P2.

### G2-F2. After a fresh configure the H12 cDNG is self-consistent (confirmed in code and on the host)

- BitsPerSample 12, table 4096, BlackLevel 3200, WhiteLevel 65520, black and white in the table's output domain.
- Host: uncompressed and lossless files written by the real encoder decode, through the port's own reader, to
  libcamera's input values with 0 differing samples of 16384.
- Consequence: a strange H12 cDNG recorded right after a configure is strange before Core's writer, or in the
  reader. Split test: an H12 MLV of the same scene holds libcamera's samples untouched (section 3.2). If the MLV
  shows the same fault, Core's cDNG path is cleared.
- Could cause strange output: no.

### G2-F3. Core stores libcamera's values rounded up to its own fixed table (confirmed)

- `compressionLut()` picks the lowest code whose expansion reaches the value (`ClearHdrCcmp.hpp:69-83`). If
  libcamera's LUT is built from other control values than 500 / 11500 / 6 / 4 / 200, its values do not sit on
  Core's grid.
- Host numbers, error of the decoded cDNG against libcamera's value:

| libcamera LUT built from | codes affected | largest error | largest relative error above black + 200 | distinct levels in -> out |
| --- | --- | --- | --- | --- |
| driver defaults | 0 | 0 | 0 | 3889 -> 3889 |
| slopes 2 / 6 (libcamera's fallback when the controls do not read, `pisp.cpp:3003-3004@6b0b49f`) | 3361 | 70 LSB16 | 12.8 % | 3896 -> 1376 |
| knee1 2000 | 3444 | 63 | 12.8 % | 3896 -> 2251 |
| black register 64 instead of 50 | 3906 | 63 | 6.6 % | 3833 -> 3291 |

- Symptom: **cDNG only**: banding in the dark mid-tones (linear 3693..14505, where Core's step is 64 LSB16).
  Preview and MLV right. No gross tone error. Not reachable at the driver defaults, which Core does not change.
- Could cause strange output: maybe (needs a changed driver control).
- Settle (needs the Pi): `journalctl -b -u apertar-core --no-pager | grep 'CcmpUnwrap: rebuilt LUT'`; expected
  `T1=500 T2=11500 slope_L=1/64 slope_H=1/16 blc_u12=200`.

### G2-F4. Core does not verify that the buffer was expanded (confirmed)

- The whole H12 path rests on the comment at `CC:1684-1685`. No metadata says "expanded". `CC:8498` skips the depth
  test. The table is attached from settings alone (`CC:4090`).
- If a frame arrives as raw codes left-aligned (code << 4, the layout `CcmpUnwrap::process` reads:
  `lut_[(buf[i] >> 4) & 0xFFFu]`, `ccmp_unwrap.cpp:159`, `:163@6b0b49f`), Core stores it faithfully. Host: code 300
  -> 4800 -> stored code 718 -> decoded 4831; the right value is 3298. Code 700: 11217 instead of 3693. Code 4095:
  65520, right.
- Symptom then: lifted, flat picture, shadows and mid-tones up to 16 times too bright against the highlights, in
  cDNG, MLV and preview alike. In every H12 size. H16 fine.
- libcamera source at `6b0b49f` does expand in place (`pisp.cpp:3100-3104`; worker path `:822-832`). So this is a
  check, not a suspect.
- Could cause strange output: maybe (only if libcamera's expansion is off or not the build the Pi runs).
- Settle (needs the Pi): section 11, check P1.

### G2-F5. An H12 MLV is a 16-bit file (confirmed)

- RAWI bits 16, black 3201, white 65535 (host run). 16.6 MB a frame at 4K. Same layout as H16 MLV.
- The bytes-per-second estimate uses 12 bits (`ApertarCoreApp.cpp:5608`): remaining time reads too long.
- Symptom: none in the picture. An MLV reader shows "16-bit" for a mode called 12-bit.
- Could cause strange output: no.

### G2-F6. Log in H12 is consistent (confirmed in code and on the host)

- Section 5. Tags and payload agree; error within 69 LSB16.
- Could cause strange output: no. Not opened in a third-party converter here.

### G2-F7. Depth-only branches around H12 (confirmed)

- Section 6: `CC:2670` (class S12 for H12), `CC:3663` (crop only at 16), `CC:8498` (depth test skipped in all Clear
  HDR), `ApertarCoreApp.cpp:5608` (estimate).
- Host: every H12 row is in S12 with the same binning and transport, so `CC:2670` returns the right size today.
- Could cause strange output: no (today).

### G2-F8. Black is stored as code 0; sub-black never reaches the file (confirmed)

- Section 4. Inherited from libcamera's LUT. H16 keeps sub-black values.
- Symptom: one-sided noise floor in the deepest shadows of H12; a slight tint after a strong lift.
- Could cause strange output: no (too small for "strange").

### G2-F9. The on-container-scale black is clamped in the stored depth's range (confirmed, latent)

- `BlackLevel.hpp:16-18`. Host: `encodedBlackLevel(5000, Bits12, true)` = 4094.
- Could cause strange output: no. 3200 is below 4094.

### G2-F10. The IFD template cache key does not cover the table or WhiteLevel (confirmed, latent)

- `CdngEncoder.cpp:1569-1638`. A long-lived encoder that sees the same clip name, size, depth and compression with
  and without a table would reuse the wrong template. No such encoder exists in the take path (`CC:5245`).
- Could cause strange output: no.

## 10. Host evidence

Built from `/home/user/Apertar-Core` at `01f170c`, sources and output outside the repo. `git status --short` stays
empty. Build and run (replace `$D` by any directory outside the repos that holds `g2_demo.cpp`):

```
cd /home/user/Apertar-Core && mkdir -p $D/out && gcc -O1 -c third_party/liblj92/lj92.c -o $D/lj92.o && \
g++ -std=c++20 -O1 -I src -I include -I third_party/liblj92 $D/g2_demo.cpp src/cdng/CdngEncoder.cpp \
    src/cdng/LosslessJpegEncoder.cpp src/color/ColorProfileConfig.cpp src/mlv/MlvEncoder.cpp $D/lj92.o \
    -o $D/g2_demo -lyaml -lpthread && $D/g2_demo $D/out
```

Output (two `ApertarCore ...` notices about missing config files on stderr left out). `differing` and
`max_abs_err` compare the samples the port's reader returns with the linear values libcamera would have delivered:

```
h12_cdng.dng               bits=12 compression=1 black=3200 white=65520 table=4096 differing=0 max_abs_err=0
h12_cdng_lossless.dng      bits=12 compression=7 black=3200 white=65520 table=4096 differing=0 max_abs_err=0
h16_cdng.dng               bits=16 compression=1 black=3201 white=65535 table=0 differing=0 max_abs_err=0
h12_cdng_log.dng           bits=12 compression=1 black=3200 white=65520 table=4096 differing=13330 max_abs_err=69
h12_mlv.MLV                RAWI bits_per_pixel=16 black_level=3201 white_level=65535
h12_mlv_stale.MLV          RAWI bits_per_pixel=12 black_level=200 white_level=4095
h12_cdng_stale.dng         exception: Invalid RAW linearization table.
```

`g2_demo.cpp`. The few lines that live in `CC`'s anonymous namespace are transcribed and marked; everything
written to disk comes from the real encoders, everything read back from the port's reader. The frame is 64x256
and sweeps all 4096 codes.

```cpp
// G2 host demo: the real CdngEncoder, LosslessJpegEncoder and MlvEncoder (cinemate-port 01f170c) fed with the
// frame view and metadata CameraController builds in IMX585 Clear HDR 12-bit, read back with the port's reader.
#include "cdng/CdngEncoder.hpp"
#include "cdng/ClearHdrCcmp.hpp"
#include "cdng/LogCurve.hpp"
#include "mlv/MlvEncoder.hpp"
#include "playback/DngFrameReader.hpp"
#include <cstdio>
#include <cstring>
#include <fcntl.h>
#include <fstream>
#include <iterator>
#include <string>
#include <unistd.h>
#include <vector>
using namespace apertar;
static const uint32_t W = 64, H = 256;
static std::string dir;

static std::vector<uint8_t> linearFrame()            // what libcamera delivers: expansion-table values
{
    std::vector<uint8_t> b(size_t(W) * H * 2);
    auto *px = reinterpret_cast<uint16_t *>(b.data());
    for (uint32_t i = 0; i < W * H; ++i) px[i] = ccmp::expansionTable()[(i * 4095u) / (W * H - 1)];
    return b;
}
static RawFrameView view(const std::vector<uint8_t> &b, RawBitDepth storage)   // CameraController.cpp:9493-9501
{
    RawFrameView v; v.data = b.data(); v.size = b.size(); v.width = W; v.height = H; v.stride = W * 2;
    v.bitDepth = storage; v.unpackedBytesPerSample = 2; v.sampleBits = 12; v.packing = PixelPacking::Unpacked;
    return v;
}
static CdngEncoder::Metadata meta(bool codes12)       // CameraController.cpp:4072-4096
{
    CdngEncoder::Metadata m; m.hasBlackLevels = true;
    for (float &x : m.blackLevels) x = 200.0f;        // SensorBlackLevels / 16
    if (codes12) {
        m.linearizationTable = std::span<const uint16_t>(ccmp::expansionTable());
        for (float &x : m.blackLevels) x = float(ccmp::kBlack16);
        m.blackLevelsOnContainerScale = true;
    }
    m.clipName = m.reelName = "demo"; m.frameFileName = "demo_000000000.dng"; m.wallClockTimestampUs = 1700000000000000ull;
    return m;
}
static void compress(std::vector<uint8_t> &b)         // CameraController.cpp:1647-1658
{
    auto *px = reinterpret_cast<uint16_t *>(b.data());
    for (uint32_t i = 0; i < W * H; ++i) px[i] = ccmp::compressionLut()[px[i]];
}
static void readBack(const std::string &name)         // the port's own reader against libcamera's values
{
    const auto ref = linearFrame(); const auto *want = reinterpret_cast<const uint16_t *>(ref.data());
    const int fd = ::open((dir + "/" + name).c_str(), O_RDONLY);
    playback::DngInfo info; std::string error; std::vector<uint16_t> got; std::vector<uint8_t> scratch;
    if (fd < 0 || !playback::readDngInfo(fd, info, error) ||
        playback::readDngSamples(fd, info, got, scratch, error) != playback::ReadStatus::Ok) {
        std::printf("%-26s read failed: %s\n", name.c_str(), error.c_str()); return;
    }
    long worst = 0; size_t differing = 0;
    for (size_t i = 0; i < got.size(); ++i) { const long e = labs(long(got[i]) - long(want[i])); differing += e != 0; worst = std::max(worst, e); }
    std::printf("%-26s bits=%u compression=%u black=%.0f white=%.0f table=%zu differing=%zu max_abs_err=%ld\n", name.c_str(),
                info.bits, info.compression, info.black, info.white, info.linearization.size(), differing, worst);
    ::close(fd);
}
static void rawi(const std::string &name)
{
    std::ifstream f(dir + "/" + name, std::ios::binary); std::string b((std::istreambuf_iterator<char>(f)), {});
    const size_t i = b.find("RAWI"); uint32_t v[9]; std::memcpy(v, b.data() + i + 20, sizeof v);
    std::printf("%-26s RAWI bits_per_pixel=%u black_level=%u white_level=%u\n", name.c_str(), v[6], v[7], v[8]);
}
static void mlv(const std::string &name, RawBitDepth storage)
{
    CaptureSettings s; s.clearHdr = true; s.rawBitDepth = 12; s.recordingFormat = RecordingFormat::Mlv;
    auto b = linearFrame(); auto v = view(b, storage); auto m = meta(false);   // MLV: mapCodes12 false, no table
    MlvEncoder e; std::string err;
    e.open(dir + "/" + name, s, v, m, &err); e.writeFrame(v, m, &err); e.close();
    rawi(name);
}
int main(int argc, char **argv)
{
    dir = argc > 1 ? argv[1] : ".";
    {   // H12 cDNG as configured for cDNG: storage 12, codes, CCMP table. Uncompressed and lossless.
        auto b = linearFrame(); compress(b); auto m = meta(true);
        CdngEncoder().writeDngFile(dir + "/h12_cdng.dng", view(b, RawBitDepth::Bits12), m);
        m.compression = CdngCompression::LosslessJpeg;
        CdngEncoder().writeDngFile(dir + "/h12_cdng_lossless.dng", view(b, RawBitDepth::Bits12), m);
    }
    {   // H16 cDNG: storage 16, no table.
        auto b = linearFrame();
        CdngEncoder().writeDngFile(dir + "/h16_cdng.dng", view(b, RawBitDepth::Bits16), meta(false));
    }
    {   // H12 cDNG with Log on: the copy worker's first branch, CameraController.cpp:5120-5133.
        auto b = linearFrame(); auto m = meta(true);
        const auto p = cdnglog::makeParams(16, 12, ccmp::kBlack16, 65520);
        const auto tables = cdnglog::buildComposed(*p, std::span<const uint16_t>(ccmp::expansionTable()));
        const auto copyTable = cdnglog::containerTable(tables.forward, 0, std::span<const uint16_t>(ccmp::compressionLut()));
        cdnglog::applyTable(reinterpret_cast<uint16_t *>(b.data()), W * H, copyTable.data());
        m.linearizationTable = std::span<const uint16_t>(tables.inverse);
        for (float &x : m.blackLevels) x = float(p->blackLevel);
        CdngEncoder().writeDngFile(dir + "/h12_cdng_log.dng", view(b, RawBitDepth::Bits12), m);
        readBack("h12_cdng.dng"); readBack("h12_cdng_lossless.dng"); readBack("h16_cdng.dng"); readBack("h12_cdng_log.dng");
    }
    mlv("h12_mlv.MLV", RawBitDepth::Bits16);          // configured for MLV: storage 16
    mlv("h12_mlv_stale.MLV", RawBitDepth::Bits12);    // G2-F1 a: configured for cDNG, then set_record_format mlv
    {   // G2-F1 b: configured for MLV (storage 16), then set_record_format cdng: table attached, view 16-bit.
        auto b = linearFrame();
        try { CdngEncoder().writeDngFile(dir + "/h12_cdng_stale.dng", view(b, RawBitDepth::Bits16), meta(true)); std::printf("stale cDNG written\n"); }
        catch (const std::exception &e) { std::printf("%-26s exception: %s\n", "h12_cdng_stale.dng", e.what()); }
    }
    return 0;
}
```

The table numbers of sections 3, 4, 5, 7 and 9 come from two more probes built with
`g++ -std=c++20 -I include -I src` only: Core's `expansionTable()` / `compressionLut()` against a transcription of
libcamera's LUT formula (`ccmp_unwrap.cpp:54-129@6b0b49f`) for several parameter sets, the table steps, the Log
composition, and `find()` of every H12 row in class S12. They are not kept; each number is reproducible from the
headers named beside it.

Gaps in the existing host tests: `tools/dng_payload_write_test.cpp:29-36` has a 12-bit unpacked control case but
none with a LinearizationTable; no test covers a format switch.

## 11. Five-minute checks

No Pi needed:

| # | Check | Command |
| --- | --- | --- |
| H1 | The storage depth depends on the format | `sed -n '1640,1644p;1682,1694p' /home/user/Apertar-Core/src/camera/CameraController.cpp` |
| H2 | It is stored only at configure | `grep -n "rawStreamInfo_\.bitDepth = " /home/user/Apertar-Core/src/camera/CameraController.cpp` |
| H3 | A format switch does not reconfigure for it | `sed -n '11385,11390p;12723,12727p;12758,12760p;7596p' /home/user/Apertar-Core/src/camera/CameraController.cpp` |
| H4 | The frame uses the old depth and the new format | `sed -n '9491,9496p;4090,4096p' /home/user/Apertar-Core/src/camera/CameraController.cpp` |
| H5 | What the encoders then do | `sed -n '1338,1340p;1290,1301p' src/cdng/CdngEncoder.cpp; sed -n '326,336p;915,920p;1152,1158p' src/mlv/MlvEncoder.cpp` (in `/home/user/Apertar-Core`) |
| H6 | Upstream had no such dependency | `sed -n '1301,1308p;7967,7969p' /home/user/wt/core-upstream/src/camera/CameraController.cpp` |
| H7 | The files | build and run the demo of section 10 |

On the Pi:

| # | Check | Command and expected result |
| --- | --- | --- |
| P1 | What Core got, and that libcamera expanded | In H12: `journalctl -b -u apertar-core --no-pager \| grep -E 'camera configured\|CcmpUnwrap: rebuilt LUT' \| tail -4`. Expected: `format=SRGGB16 ... storage_bits=12 packing=unpacked transport_bits=16` (cDNG) or `storage_bits=16` (MLV), and a `CcmpUnwrap: rebuilt LUT ... T1=500 T2=11500 slope_L=1/64 slope_H=1/16 blc_u12=200` line. `packing=pisp_comp1` or no LUT line: Core's assumption is broken (G2-F4) |
| P2 | G2-F1 | First make both formats hold the same H12 mode: select Clear HDR, 12-bit and one size once in cDNG and once in MLV; leave the cDNG preview profile at Standard (another profile forces a reconfigure, `CC:12726`). **a.** Restart Core in cDNG (`sudo systemctl restart apertar-core.service`); the `camera configured` line reads `storage_bits=12`. Switch the record format to MLV in the WebUI (it sends `{"cmd":"set_record_format","value":"mlv"}` to `POST /api/command`, `src/web/WebControlPage.cpp:16001`, `src/ApertarCoreApp.cpp:9214`). Touch nothing else. No new `camera configured` line appears. Record 2 s. Then `python3 -c "import struct,sys;b=open(sys.argv[1],'rb').read(8192);i=b.find(b'RAWI');print(struct.unpack_from('<9I',b,i+20)[6:9])" <clip>.MLV`. Healthy: `(16, 3201, 65535)`. Defect: `(12, 200, 4095)`. **b.** Restart Core in MLV, switch to cDNG, record: `journalctl -b -u apertar-core --no-pager \| grep 'Invalid RAW linearization table'` prints the failed frame |
| P3 | Split test for any strange cDNG | Same scene, H12, one cDNG take and one MLV take, each after `sudo systemctl restart apertar-core.service` in that format (a start always configures with the current format, `CC:7274-7290`, `CC:8615`). MLV wrong too: the fault is before Core's writers |
| P4 | Tags of a recorded H12 frame | `exiftool -BitsPerSample -Compression -BlackLevel -WhiteLevel -LinearizationTable <frame>.dng`. Expected: 12, table of 4096 starting `3200 3200 ...` ending `65520`, black `3200 3200 3200 3200`, white 65520. With Log on the table starts `2721` |

## 12. Seen in passing, for the other angles

| What | Why it matters for H12 | Evidence | Label |
| --- | --- | --- | --- |
| HDR gain adder against the fixed ISO cap | The 720 cap is derived for an adder of +12 dB ("the sensor merges HG and LG only while GAIN + EXP_GAIN <= 29.1 dB", a code comment). The adder is user-settable 0..5 (+0 .. +29.1 dB) and the cap does not follow it. Adder 3 (+18 dB) leaves the window above gain 11.1 dB (about ISO 360); adder 5 at any gain. H16 has another limit. Core's default is 1 (+6 dB), which is inside | `CC:2933-2939`, `CC:3017-3023`, `CC:11754-11768`, `CC:7082`, `Types.hpp:206`; driver menu `imx585.c:335-337@cd548ef` | unconfirmed. Settle: `curl -s http://127.0.0.1:8000/api/state \| grep -o '"hdr_gain_adder":[0-9]*'` |
| Binned H12 | Core's table and black have no binning input, same as libcamera's LUT. The first H12 row, 1920x1080, is binned. If the sensor's curve differs when binned, Core records the wrong linear values faithfully. G1 lists this as its F2 | `ClearHdrCcmp.hpp:24-30`, `Imx585Modes.hpp:78-79` | Core side confirmed; the sensor side is not Core's |
| libcamera worker path | With the raw CPU worker, the expansion runs only inside `if (job.rawStats && job.stats)` | `pisp.cpp:822-832@6b0b49f` | for the libcamera angle |
| WebUI clip label | "Clear HDR 12-bit companded" is derived from (not 16-bit, has a table), so H16 takes with Log read the same | G1, its F5 | - |

## 13. Not covered

- Preview, exposure and white balance behaviour, the players' rendering, the driver registers, libcamera's
  internals beyond the three facts Core relies on. Other agents' angles.
- No file was opened in a third-party raw converter. The reader used is the port's own.
- Nothing was run on the camera. G2-F1 is proven for the code and for the written bytes, not for the owner's
  session.
- A fix was not made. The smallest one that follows upstream's rule (H6): let `setRecordingFormat` reconfigure
  when `storageRawBitDepthForSettings(next) != storageRawBitDepthForSettings(settings_)`, next to the existing
  terms at `CC:11387-11389`.
- The relayed user request of this run (reinsert the chip definition for GPIO, because GPIO can come from another
  chip such as a microcontroller) is a Controls task. It is outside assignment G2 and was not acted on.
