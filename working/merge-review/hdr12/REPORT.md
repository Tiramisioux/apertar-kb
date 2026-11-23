# 12-bit Clear HDR "strange output": report

For Patrik. Stack: Apertar-Core `cinemate-port` `01f170c`, Apertar-UI `cinemate-port` `7ea9afc`, imx585 driver `cinemate-port` `cd548ef`, libcamera fork `apertar` `6b0b49f`, CM5, IMX585. Report: "12 bit clear HDR shows strange output". 16-bit Clear HDR fine. No other detail.

Sources: nine reader notes `G1..G9`, `DIGEST.md`, `H-hypotheses.md` and ten skeptic notes `V-H1..V-H10`, all in this folder. Key lines were re-read for this report. Host programs are in `/home/user/build/hdr12-numeric/`. No Pi was run.

Labels:
- **confirmed**: read in code or run on the host.
- **probable**: inferred; the reason is given.
- **unconfirmed**: needs the command named.

Short refs: `CC` = `Apertar-Core/src/camera/CameraController.cpp`, `App` = `Apertar-Core/src/ApertarCoreApp.cpp`, `pisp.cpp` = `libcamera/src/libcamera/pipeline/rpi/pisp/pisp.cpp`.

## 1. Answer

1. Most likely cause (probable, high confidence): the **binned 1920x1080** 12-bit Clear HDR mode is decoded with the full-resolution CCMP curve. The mode is new on this stack. Mid-tones from 4.6 % to 17.5 % of white come out about 16x too dark, grey card included, with a hard step at about 17.5 %. It shows in every output; 4K is not affected. One 1080 capture pair settles it (H1).
2. The touch UI puts you in that mode without showing it. "4K Clear HDR" keeps the SDR size, so a Full HD start becomes binned 1080 under a fixed "4K" label (confirmed defect, H5).
3. Second cause, confirmed in code, but it needs a specific sequence. Switching cDNG <-> MLV while in 12-bit Clear HDR keeps the old storage depth. Either the MLV comes out wrapped (black at 77 % of white) or the cDNG take fails (H2).
4. The strange picture may have been a third-party tool or a clip label. A tool that ignores LinearizationTable shows H12 near black, and two labels are wrong (H9). All in-house players render H12 correctly.
5. At 4K, with a fresh configure and default settings, the code holds together end to end; nothing in it predicts a 4K 12-bit-only fault. `get_state` plus one journal grep decide which of 1-4 applies (section 4, P1-P2).

## 2. What 12-bit Clear HDR is today, hop by hop

Case: colour IMX585, cDNG, Log off, fresh configure. Values are in LSB16 unless marked.

| # | Hop | What it does to the pixel values | Evidence | Label |
| --- | --- | --- | --- | --- |
| 1 | Mode choice (Core) | Clear HDR entered from SDR runs at 12-bit. The size snaps to the nearest of 29 H12 rows: 1920x1080 **binned**, 4K, and 27 1x1 crops. Only mono is pinned to 4K. Auto ISO and auto WB are off; ISO is capped at 720 | `CC:3452-3454`, `CC:3526-3531`, `src/camera/Imx585Modes.hpp:78-87`, `CC:3073-3098`, `CC:2932-2940` @01f170c | confirmed |
| 2 | Sensor switches (Core -> subdev) | WDR=1 is written and read back before libcamera starts; failure aborts. Merge knobs: threshold, blend, gain adder index 1 (+6 dB). Core never writes the CCMP knee, slope or black controls | `CC:7333-7334`, `CC:7034-7037`, `CC:7076-7084`, `include/apertar/core/Types.hpp:206` @01f170c | confirmed |
| 3 | Sensor (driver) | HG/LG built-in combination, then the CCMP compander to 12 bits: 1:1 up to 500 above black, 1/64 up to 11500, 1/16 above. Pedestal 200 codes. Same thresholds in every mode; no binning term | `imx585.c:3604-3613,3688,4130-4163` @cd548ef | confirmed (registers); sensor transfer in binned mode unconfirmed (H1) |
| 4 | CFE capture (libcamera) | 12-bit codes in 16-bit containers (`code << 4`) | `ccmp_unwrap.cpp:143-165` @6b0b49f | confirmed |
| 5 | CcmpUnwrap (libcamera, pipeline thread) | Rewrites the app's raw buffer in place, code -> linear. Codes 0..201 -> 3200; 4095 -> 65520. The curve is read once at configure from the live controls, and only the b=1 curve exists. The stream format is rewritten to 16-bit unpacked | `pisp.cpp:1821-1823`, `:2990-3027`, `:3095-3104`; `ccmp_unwrap.h:57-67` @6b0b49f. The comment at `pisp.cpp:1825-1831` ("NOT rewritten") is stale | confirmed |
| 6 | SW stats, AGC/AWB | Stats come from the unwrapped buffer. AE moves only the shutter, and only with shutter auto on (default off) | `pisp.cpp:3106`; `CC:2425,2438` @01f170c | confirmed |
| 7 | BE / ISP preview | Uses the same unwrapped buffer. One YUV420 Rec709 stream feeds HDMI/touch and the WebUI MJPEG, with the same tuning at both depths. The BE subtracts tuning black 3301/3321/3240 from data whose black is about 3200-3207: slightly crushed, tinted shadows **at both depths** | `CC:8383-8387`, `App:8207-8235` @01f170c; IPA `src/ipa/rpi/pisp/pisp.cpp:695-726` @6b0b49f | confirmed path; tint probable, not 12-bit only |
| 8 | Core configure | Reads the stream as SRGGB16 unpacked, then sets the storage depth: **12 for cDNG, 16 for MLV**. This is the only place it is set | `CC:1640-1643`, `CC:1682-1687`, `CC:8615-8622` @01f170c | confirmed |
| 9 | Copy worker (Core) | memcpy, then give the buffer back. For cDNG only, `compressionLut()` maps linear -> code 0..4095, the exact inverse of hop 5 at b=1. MLV keeps linear 16-bit | `CC:9491-9496`, `CC:5107-5111`, `CC:5134-5135`, `src/cdng/ClearHdrCcmp.hpp:24-30,67-83` @01f170c | confirmed |
| 10 | cDNG encoder | BitsPerSample 12, codes 0 and 202..4095. LinearizationTable = `ccmp::expansionTable()` (4096 entries, b=1 curve). BlackLevel fixed at 3200 (ignores SensorBlackLevels). WhiteLevel 65520 | `CC:4088-4096`; `src/cdng/CdngEncoder.cpp:1338-1340,1490-1491,1703-1707` @01f170c | confirmed |
| 10b | MLV encoder | Linear 16-bit; RAWI 16 / 3201 / 65535 | `src/mlv/MlvEncoder.cpp:1152-1158`, `src/cdng/BlackLevel.hpp:22-35` @01f170c | confirmed |
| 11 | In-house viewers | The WebUI and the touch UI apply the table, then black/white from the tags. H12 and H16 of the same light render within 6/255 (host) | `src/playback/DngFrameReader.hpp:115-121` @01f170c; UI `src/dngdecoder.cpp:1065-1075` @7ea9afc | confirmed |
| 12 | Third-party tools | Correct only if they honour tag 50712. Without it, the brightest code is 1.4 % of range and 18 % grey is 0 | host `/home/user/build/hdr12-numeric/v-h9/vh9.out` | confirmed (mechanism) |

Net: hop 5 and hops 9/10 use the same b=1 curve and invert each other exactly (4096/4096 entries at the driver defaults, host `v_h10`). So a wrong curve at hop 5 reaches the file unchanged, and Core cannot correct it.

## 3. Defects confirmed from code

### D1. A cDNG <-> MLV switch in 12-bit Clear HDR keeps the old storage depth (H2)
- **Lines:**
  - The depth depends on the format: `CC:1640-1643`, `CC:1686-1687`.
  - It enters `rawStreamInfo_` only at configure: `CC:8615-8622`.
  - `setRecordingFormat` reconfigures only on a processed stream, a size change or a `rawBitDepth` change: `CC:11385-11389`.
  - `applySettingsLocked` adds only photo mode, the ISP profile and the Clear HDR toggle: `CC:12725-12727`.
  - Each frame takes the format from the new `settings_` and the depth from the stale `rawInfo`: `CC:9491-9496`.
  - All @01f170c.
- **Effect A, cDNG -> MLV:** the MLV is written as 12-bit and the packer keeps the low 12 bits (`MlvEncoder.cpp:333-336`). RAWI says 12/200/4095, linear black 3200 sits at 77 % of white, and the highs wrap (4096 -> 0, 8000 -> 3904). Host run: `/home/user/build/hdr12-numeric/v-h2/vh2.cpp`.
- **Effect B, MLV -> cDNG:** the 4096-entry table meets a 16-bit view. `writeDngFile` throws "Invalid RAW linearization table." (`CdngEncoder.cpp:1338-1340`), the worker calls `failRecording` (`CC:5299-5304`), and the take stops.
- **Cleared by** any reconfigure: size, depth, Clear HDR toggle, a non-Standard cDNG preview profile, a ladder rung change, or a Core restart.
- **Origin:** fork main `57c8fb0` (same code at `f60e301`). Not a port regression. Upstream 1.6.0 had no format-dependent depth.
- **Fix:** add one line in `applySettingsLocked` at `CC:12727`:
  `requiresReconfigure |= storageRawBitDepthForSettings(nextSettings) != storageRawBitDepthForSettings(settings_);`
  It covers every setter. Cost: switching format in Clear HDR 12 restarts the stream, as a size change does.
- **Host test:** none reaches `CameraController`. Two options:
  1. `tools/clear_hdr_storage_test.cpp` asserts both failure signatures at encoder level.
  2. Move the two helpers into a header beside `RecordingCapabilities.hpp` and assert that the depths differ. That is a code move; decide it with the original developer.

### D2. "4K Clear HDR" is not 4K (H5)
- **Lines:**
  - Fork main pinned colour Clear HDR to 3840x2160 (`CC:2824-2827@f60e301`).
  - `caa0153` removed that pin; the port pins only mono (`CC:3526-3531@01f170c`).
  - The touch UI sends only `set_clear_hdr` (`src/ApertarControlBridge.cpp:703-714@7ea9afc`).
  - It shows the fixed text "4K Clear HDR" (`qml/CameraPage.qml:3382,3457`, `qml/SettingsPage.qml:3296`@7ea9afc) and disables crops (`CameraPage.qml:452,458`).
- **Effect:** Full HD becomes binned 1920x1080 labelled 4K, which is the H1 mode. 3840 crops stay crops. The size controls are locked, so the operator cannot correct this without leaving Clear HDR. 12-bit and 16-bit land on the same row from 4K and from Full HD; they differ only from 1440x1080, 1488x1080 or 1920x1040 (host `v_h5_nearest.cpp`).
- **Stale comments** (they say Core forces 4K, or that the touch UI sends 16-bit):
  - `ApertarControlBridge.cpp:704@7ea9afc`
  - `CameraPage.qml:452@7ea9afc`
  - `App:10451@01f170c`
  - `CC:11602-11603@01f170c`
- **Fix:** in `CameraController::setClearHdr`, after `next.clearHdr = enabled;`, add:
  `if (enabled && !settings_.clearHdr && sensorFamily == SensorFamily::Imx585) next.resolution = Resolution{ 3840, 2160 };`
  An explicit `set_resolution` inside Clear HDR still reaches every H12/H16 row, which keeps the intent of `caa0153`. UI-only alternative: show `root.resolution` instead of "4K".
- **Host test:** the fix needs libcamera. `tools/imx585_modes_test.cpp` can pin the premise: `nearest(Class::H12,1920,1080)` is the binned row, and `find(Class::H12,3840,2160)` exists and is 1x1.

### D3. Clip labels (H9-C)
- **Core WebUI:** `src/playback/ClipProbe.hpp:165-178@01f170c` labels any non-16-bit file with a table "Clear HDR 12-bit companded". Via `Types.hpp:352` that includes H16 Log (stores 12), SDR 12 Log (stores 10) and SDR 10 Log (stores 8).
- **Touch UI:** `src/dngdecoder.cpp:1074@7ea9afc` (`frame.bitsPerSample = 16;`) labels every clip with a table "16-bit". This is upstream code.
- **Fix:**
  - In ClipProbe, compare the table with `ccmp::expansionTable()` (bits 12, size 4096, `std::equal`). Only that table gives "Clear HDR 12-bit companded"; any other gives "Log <bits>-bit".
  - In the touch UI, delete line 1074. Offer it to the original developer as a separate one-line change.
- **Test:** `tools/clip_probe_format_test.cpp`, modelled on `tools/dng_payload_write_test.cpp`. It writes three one-frame clips: 12-bit + CCMP table, 12-bit + another table, 10-bit + a 1024-entry table. The last two fail today.

### D4. The 12-bit ISO cap ignores the gain adder (latent, low)
- **Lines:**
  - The cap depends on depth only (`CC:3017-3023@01f170c`).
  - The comment assumes +12 dB (`CC:2932-2935`), but Core writes +6 dB (`Types.hpp:206`).
  - The cap is new in the port (`8175273`).
- **Effect:** none at the defaults (ISO 720 = code 57 + 6 dB = 23.1 dB, inside 9.6..29.1 dB). With adder 3, 4 or 5, which only the socket, a preset or the conf can set, ISO 720 leaves the window.
- **Fix:**
  - Add `clearHdr12MaxIso(adder)` = {1585, 1429, 716, 359, 180, 100} in `Imx585Modes.hpp`.
  - In the 12-bit branch of `clearHdrIsoCap`, return `std::min(limits.max12, clearHdr12MaxIso(settings.hdrGainAdder))`.
  - Correct the comment.
  - Test in `tools/imx585_modes_test.cpp`.

### D5. Stale libcamera comment
`pisp.cpp:1825-1831@6b0b49f` says "raw buffer is NOT rewritten". The code at `:3095-3104` rewrites it in place before the BE. The comment misled two readers. Fix: rewrite the comment.

### Gap, not a defect (H10)
Core never checks that libcamera unwrapped the buffer (`CC:9491-9492`, `CC:4092`). No path in the shipped stack produces a mismatch.

Optional guard:
- Add `clearHdrFrameMatchesTable()` beside `compressClearHdrFrame` (`CC:1646`). On a sample of the first frame of each take it checks `expansionTable()[compressionLut()[v]] == v`.
- On failure, write one `std::cerr` line and keep linear 16-bit for that take.
- Test: `tools/clear_hdr_ccmp_test.cpp`.

## 4. Causes that need the Pi

Helper used below. Core reads the command name from `"cmd"` (`src/ipc/ControlProtocol.cpp:220@01f170c`), so `{"command":...}` in V-H8.md is wrong.

`ac() { printf '%s\n' "$1" | socat - UNIX-CONNECT:/tmp/apertar-core.sock; }`

### Read-only triage, in order, on the camera as Patrik left it

**P1: state.** Run:
`ac '{"cmd":"get_state"}' | tr , '\n' | grep -E '"(resolution|width|height|raw_bit_depth|clear_hdr|recording_format|cdng_compression|cdng_log|iso|iso_max|hdr_gain_adder|shutter_auto|tuning_file_active)"'`
- 1920x1080 + 12-bit + Clear HDR: H1 is a candidate.
- Any size other than 3840x2160 or 1920x1080: a crop (H4).
- `cdng_log` true: D3.
- adder above 2: D4 is live.

**P2: journal.** Run:
`journalctl -b -u apertar-core --no-pager | grep -E 'camera configured|CcmpUnwrap: rebuilt LUT|CCMP stats linearisation|Invalid RAW linearization|tuning file|recording stats:|drop\['`
- `binning=2 ... raw=1920x1080`: the H1 mode is live.
- `storage_bits=12` while P1 says MLV, or `16` while P1 says cDNG: D1.
- `Invalid RAW linearization`: D1-B happened.
- `CcmpUnwrap` line missing, or not 500/11500/1/64/1/16/200: H10 is alive.
- Many `drop[capture-gap]`: H3.

**P3: sensor controls.** Run `v4l2-ctl -d /dev/v4l-subdevN --list-ctrls` while 12-bit streams. Expect threshold 500 11500, ACMP1 6, ACMP2 4, brightness 50, adder +6dB, gain at most 57. If so, H6 and H10 are out.

**P4: DNG tags.** Run `exiftool -warning -BitsPerSample -Compression -BlackLevel -WhiteLevel -ImageWidth -LinearizationTable <frame.dng>`.
- 12 / 1 or 7 / 3200 / 65520 with a table: the tags are right.
- A warning: the file is damaged.
- Width 1920: the H1 mode.

**P5: MLV levels.** Run:
`python3 -c "import struct,sys;b=open(sys.argv[1],'rb').read(8192);i=b.find(b'RAWI');print(struct.unpack_from('<9I',b,i+20)[6:9])" clip.MLV`
- `(12, 200, 4095)`: D1-A.
- `(16, 3201, 65535)`: healthy.

**P6: WebUI frame.** Run `curl -sD- -o h12.jpg 'http://<cam>:8000/api/media/frame?kind=folder&id=<clip>&n=0&w=640'`, and the same for a 16-bit clip of the same scene.
- WebUI frame fine, his tool dark: H9-B.
- WebUI frame strange too: the samples are wrong (H1, D1 or H4).

### Captures

**P7: H1.** `ac '{"cmd":"set_resolution","width":1920,"height":1080}'`, then record 12-bit and 16-bit Clear HDR with the same scene, shutter and ISO. Repeat the pair at 3840x2160 as a control. Decode each through its own tags and compare patch medians on a grey ramp.
- Confirmed: at 1080, 12-bit patches between 4.6 % and 17.5 % of white read about 16x low, with a step near 17.5 %. The 4K pair matches within 0.3 %.
- Refuted: the 1080 pair matches across the whole ramp.

**P8: D1 repro.** Set Clear HDR 12 in cDNG and restart Core. Then:
1. `ac '{"cmd":"set_record_format","value":"mlv"}'`, then `ac '{"cmd":"record_start"}'`, wait 2 s, `ac '{"cmd":"record_stop"}'`. Run P5 on the MLV and expect (12, 200, 4095).
2. `ac '{"cmd":"set_record_format","value":"cdng"}'` and record. Expect the take to stop with "Invalid RAW linearization table.".

**P9: H4.** Run it only if P1 shows a crop.
1. Run `ac '{"cmd":"set_cdng_compression","value":"none"}'`.
2. Record 1 s in the crop and 1 s at 4K 12-bit.
3. Run `python3 tools/clearhdr-gate/pedestal_check.py <crop> <4K>` from the driver repo.

PEDESTAL, or a top mean at black, confirms H4. Both REAL refutes it.

**P10: H3.** Run it only if Patrik means stutter or black flashes. After the take:
1. Repeat the P2 grep, adding `frame index jump`.
2. Run `top -H -b -n 5 -p $(pgrep -nx apertar-core)` during a 27 fps take, once at 12-bit and once at 16-bit.
3. Repeat the 12-bit take with `QBC_RAW_CPU_WORKER=1`.

How to read it:
- Fewer gaps with the worker: the fix belongs in libcamera.
- `dropped_copy_slot` above 0: try 2 copy workers (`CC:4386`).

**P11: H7 half-bin bias.** Use the P7 4K pair. Compare region means at 600, 1000 and 4000 above black after the 0.988 scale. If 12-bit reads about 32 LSB16 low, fix libcamera `inverse()` and Core `linearAboveBlack()` together.

### Fix sketches for the Pi-dependent causes

**H1 interim, Core only.** Recommended now, since `c1350b0` added the mode "desk-only" with no curve check.
- Delete `{ 1920, 1080, true },` from `kH12Modes` (`Imx585Modes.hpp:79@01f170c`).
- Set `tools/imx585_modes_test.cpp:20` to `== 28`.
- 1920x1080 then resolves to the 1x1 row 1920x1040.

**H1 full fix.** Core and libcamera change together.
- Core:
  - Add `uint32_t binning = 1;` to `ccmp::Params`.
  - `linearAboveBlack` runs its segments on `y*binning` and divides by `binning`.
  - `expansionTable` and `compressionLut` take a binned flag.
  - `CC:4090` and `CC:9491` pass `find(H12,w,h)->binned`.
- libcamera:
  - `CcmpUnwrap::Params` gets `binning`, with `inverse(out*b)/b`.
  - It is set in `initCcmpUnwrap` from analogCrop / outputSize.
- Test, `tools/clear_hdr_ccmp_test.cpp`:
  - The b=1 table is unchanged.
  - The b=4 table is within 0.03 EV of `ccmp(4L)/4+200`.
  - The round trip is exact.

**H4**, if P9 confirms: end the driver range at `IMX585_MODE_4K_12BIT` (`imx585.c:3091-3094@cd548ef`) and shorten `kH12Modes` to the two full-field rows.

**H3**, per P10: either turn the libcamera worker on by default for the CCMP path, or use 2 copy workers for Clear HDR 12 cDNG (`CC:4386`).

## 5. Refuted ideas: do not chase

- **Drops as the "strange output" (H3).** The unwrap replaces the 16-bit endian swap on the same thread (`pisp.cpp:1744-1750`). All 17 journals show 0 copy-slot drops. 16-bit drops too at 30 fps. At 24/25 fps it is one black frame per 13-90 s.
- **OB band in crops (H4 as written).** Driver and Core agree that H12 has no OB rows (`imx585.c:2961-2994@cd548ef`, `Imx585Modes.hpp:202-208@01f170c`). Only the pedestal question is open (P9).
- **12-bit and 16-bit tests ran at different sizes (H5 half).** Both land on the same row from 4K, Full HD and the 3840 crops.
- **HG/LG window clamps 12-bit (H6).** Both depths share one register path; only CCMP_EN/MDBIT differ (`imx585.c:4130-4163`). The default point is inside the window. The in-window peak 4095 maps to WhiteLevel 65520.
- **CCMP banding in mid-tones (H7).** The step at grey is 0.6 % and shot noise dithers it. ACMP1 is already at the gentlest legal slope (`imx585.c:3705-3706,3724`). The proposed histogram test cannot fail.
- **Exposure rules (H8).** Nothing in them depends on depth except the cap. At the defaults the 12-bit effect is 800 -> 720 ISO, a uniform 0.15 stop.
- **In-house player renders a correct file wrong (H9-A).** Both renderers apply the table. The libtiff fallback is never reached for files Core writes.
- **Unwrap not armed, or controls drifting (H10).** Every arming condition holds, nothing writes the controls, and drift would cost at most about 66 LSB16.
- **Lossy DNG + Clear HDR 12.** Unreachable: `RecordingCapabilities.hpp:76-78` refuses the combination.
- **Same at both depths, so not a 12-bit cause:** the `_clearHDR` tuning or rpi.hdr pin, BE black over-subtraction, the blend default, the first-frame black, the launch pedestal.
- **Log composed table.** Off by default. The maths was checked on the host (max 69 LSB16); only the label is wrong (D3).
- **Uncompressed vs lossless.** Same samples.

## 6. What to ask Patrik

1. Where did you see it, and what did it look like: live preview, a player, or a raw converter (which one)?
   - Dark mid-tones with a jump: H1.
   - Wrapped picture, speckle, magenta, raised black: D1-A.
   - Near black in one program only: H9-B.
   - A label: D3.
   - Live preview: rules out D1, D3 and H9.
2. Which size, and how did you enter 12-bit (touch UI from Full HD, WebUI, or the button)? A Full HD start means binned 1080 (H1). A 4K start removes H1 and D2.
3. Did you switch between cDNG and MLV inside Clear HDR with no restart or size change in between? Yes means D1.

## 7. Rules for future work

1. A binned or windowed companded mode is not done until one capture pair checks its transfer curve against a linear mode. "Not all BLC" is not a curve check.
2. Change `ClearHdrCcmp.hpp` and `CcmpUnwrap` together, never one alone. Keep `expansionTable()[compressionLut()[v]] == v` in a host test.
3. When a value that shapes the stream gains a new input, add that input to the reconfigure list in `applySettingsLocked` in the same commit.
4. A UI label that names a mode property ("4K") must read it from Core state. When you remove a Core rule, grep both UIs and the comments for it.
5. Correct any comment that describes behaviour in the same commit that changes the behaviour. Three stale comments misled readers here.
6. Before any analysis, get three facts about the report: which output, which mode and size, which steps. One `get_state` and one `camera configured` line cut ten hypotheses to two.
