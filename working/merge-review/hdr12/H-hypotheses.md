# 12-bit Clear HDR "strange output": ranked hypotheses (assignment H)

Stack: Apertar-Core `cinemate-port` 01f170c, Apertar-UI 7ea9afc, imx585 driver cd548ef, libcamera `apertar` 6b0b49f,
CM5, IMX585. Owner: "12 bit clear HDR shows strange output". 16-bit Clear HDR fine. No other detail.

Sources: DIGEST.md and G1..G9 in this folder. Code re-read for every disagreement (section 3). Labels:
**confirmed** (read in code), **probable** (inferred, reason given), **unconfirmed** (command given).

## 1. Triage on the Pi, read-only, in this order

One journal line and one state read separate most hypotheses. Run them on the camera as the owner left it.

| # | Command | Separates |
| --- | --- | --- |
| T1 | `printf '{"cmd":"get_state"}\n' \| socat - UNIX-CONNECT:/tmp/apertar-core.sock` and read `resolution`, `raw_bit_depth`, `clear_hdr`, `recording_format`, `cdng_compression`, `cdng_log`, `iso`, `iso_max`, `iso_auto`, `wb_auto`, `shutter_auto`, `hdr_gain_adder`, `hdr_blend`, `tuning_file` | H1/H5 (size), H2 (format), H6 (adder, ISO), H8 (auto flags), H9 (Log) |
| T2 | `journalctl -b -u apertar-core --no-pager \| grep -E 'camera configured\|CcmpUnwrap: rebuilt LUT\|CCMP stats linearisation\|Invalid RAW linearization\|recording stats:\|drop\['` | `binning=2` and `raw=1920x1080` -> H1; `storage_bits=12` while state says MLV -> H2; drop lines -> H3; `stream=` not 3840x2160 -> H4/H5; missing LUT line or `T1/T2/slope/blc` not 500/11500/1/64/1/16/200 or `packing` not `unpacked` -> H10 |
| T3 | `v4l2-ctl -d /dev/v4l-subdevN --list-ctrls` (imx585 subdev) while 12-bit Clear HDR streams | H6 (`analogue_gain`, `hdr_gain_adder`), H10 (gradient thresholds 500/11500, slope menus 6/4, `brightness` 50) |
| T4 | `exiftool -BitsPerSample -Compression -BlackLevel -WhiteLevel -LinearizationTable -ImageWidth -ImageHeight <frame.dng>` on one frame of the strange take | H9 (tags right?), H2 (cDNG never written), H10 (table shape) |

Then ask the owner one question: which screen (HDMI/touch preview, WebUI preview, raw converter, clip player) and which size.

## 2. Hypotheses, most likely first

### H1. Binned 1920x1080 12-bit Clear HDR is linearised with the full-resolution (b=1) curve

| Field | Content |
| --- | --- |
| Mechanism | The sensor compands the 2x2 binned sum, so in the binned mode the CCMP knees sit 4x lower in scene light. libcamera's `CcmpUnwrap` and Core's `ccmp::expansionTable()` both have one parameter set with no binning term. The port newly offers binned 1920x1080 in 12-bit Clear HDR. |
| Symptom, where seen | 1920x1080 12-bit only. Codes 326..871 decode at 0.058..0.13x their true level (-4.1 EV; code 700: about 500 instead of about 8380 above black), then a hard step back to about 1.0x at code 872 (about 17 % of white). Crushed, posterised shadows and mid-tones, a tonal break, level-dependent colour shifts. Same in the HDMI/touch preview, WebUI preview, AE metering (shutter auto pushes exposure up), the cDNG in any converter, MLV, both clip players. 4K and 1x1 crops are fine; 16-bit binned 1080 is fine (linear). |
| Lines that would change | libcamera `src/libcamera/pipeline/rpi/pisp/ccmp_unwrap.h:57-67@6b0b49f` (Params without binning) and its builder `pisp.cpp:2990-3023@6b0b49f`; Core `src/cdng/ClearHdrCcmp.hpp:24-30@01f170c` (fixed Params, no binning) and the call at `src/camera/CameraController.cpp:4090-4096@01f170c`. Or drop the row: `src/camera/Imx585Modes.hpp:79@01f170c` `{ 1920, 1080, true }` and driver `imx585.c:3086-3091@cd548ef` (H12 range starts at `IMX585_MODE_1080P_12BIT`). |
| Support | Code side **confirmed**: H12 list starts with the binned row (`Imx585Modes.hpp:79`); driver cd548ef offers it (G5-D1, D3, `c1350b0` re-enabled it after apertar `bb53099` removed it as "returns BLC"); neither table has a binning input (G1-F2, G7-2, G8-F2). Numbers **confirmed** on host: `/home/user/build/hdr12-numeric/hdr12.out:23-25,40` (max error -7611 at code 700, -4.11 EV; Cinemate golden binned table `[700]=8384`). Cinemate's measured model `cinepi-raw cinepi/ccmp_lut.hpp:22-45@63a08d5` "stored_code = ccmp(b*L)/b + P", "At code 400 the decode is 200 full-res and 3387.5 binned". KB records a 2K 12-bit take on 2026-11-07 with no picture check (G1). Entry route is natural: H5 (touch UI "4K Clear HDR" from SDR 1920x1080 lands on this row). 16-bit from the same SDR size lands on the H16 binned 1080 row (`Imx585Modes.hpp:97`), which is linear: "16-bit fine" holds. Origin/apertar offered only 4K in 12-bit (`imx585.c:1430@e5b74d3`), so this is new with the port. |
| Counter-evidence | The b=4 geometry is Cinemate's measurement only; its one cross-check is on the top segment where b=1 and b=4 agree (G7 open). No Apertar capture of binned 12-bit exists. The driver comment `imx585.c:3049-3057@cd548ef` says colour passed binned 12-bit CCMP on 2026-08-10 golden captures (under Cinemate, which used the b=4 table). |
| Provable from code | No. Code half confirmed; sensor behaviour needs one capture pair. |
| Cheapest separating test | T2: `camera configured: ... binning=2(...) raw=1920x1080`. Then same scene and exposure at 1920x1080, one 12-bit and one 16-bit Clear HDR take; decode both through their tags (exiftool/rawpy) and compare patch medians. 12-bit mid patches about 16x lower = confirmed. The same pair at 4K matched within 0.3 % on 2026-10-25 (KB `working/clearhdr-design.md:73`). |

### H2. Storage depth is fixed at configure; a cDNG <-> MLV switch in 12-bit Clear HDR does not reconfigure

| Field | Content |
| --- | --- |
| Mechanism | `storageRawBitDepthForSettings` gives 12 for 12-bit Clear HDR cDNG and 16 for MLV (`CameraController.cpp:1683-1687@01f170c`), assigned to `rawStreamInfo_.bitDepth` only in configureAndStart (`:8615-8621`). `setRecordingFormat` reconfigures only on size, bit depth or processed-stream change (`:11385-11389`); `applySettingsLocked` adds photo mode, ISP colour profile and Clear HDR toggles (`:12725-12727`), not the storage depth. |
| Symptom, where seen | (a) Started in cDNG, switched to MLV: the MLV holds the low 12 bits of the linear 16-bit samples, RAWI 12 / black 200 / white 4095: wrapped picture, speckle, magenta, black at 77 % of white, in any MLV reader and the touch MLV player (G9-F6). Preview and cDNG fine. (b) Started in MLV, switched to cDNG: take stops at frame 1, journal `DNG write failed ... Invalid RAW linearization table.`; empty or one-frame clip. 12-bit Clear HDR only (16-bit stores 16 in both formats, SDR 12 in both). |
| Lines that would change | `src/camera/CameraController.cpp:11386-11389@01f170c`: add `storageRawBitDepthForSettings(next) != storageRawBitDepthForSettings(settings_)` to `requiresReconfigure` (upstream 1.6.0 made storage depth a function of bit depth only, so it never needed this). |
| Support | **Confirmed** in code (re-read here: `:1638-1643`, `:1683-1687`, `:9491-9492` `mapCodes12` keyed on `clearHdrStoresCodes12(settings_)`, `:11385-11389`). G2 reproduced both outcomes with the real encoders on host. Carried from fork main 57c8fb0, not introduced by the port. |
| Counter-evidence | Needs that exact sequence and no reconfigure in between (a size, depth, Clear HDR toggle or Core restart clears it). A ladder rung change that alters size also clears it. |
| Provable from code | Yes (G2 host demo). |
| Cheapest separating test | T1 + T2: state says `recording_format` MLV while the last `camera configured` line says `storage_bits=12` (or cDNG with `storage_bits=16`). On an MLV: `python3 -c "import struct,sys;b=open(sys.argv[1],'rb').read(8192);i=b.find(b'RAWI');print(struct.unpack_from('<9I',b,i+20)[6:9])" clip.MLV` prints `(12, 200, 4095)` for the defect, `(16, 3201, 65535)` healthy. |

### H3. 4K 12-bit Clear HDR drops frames at every fps; the gaps play back as black frames or stutter

| Field | Content |
| --- | --- |
| Mechanism | Per frame, 12-bit Clear HDR adds two full-frame CPU passes the 16-bit mode does not have: libcamera's in-place unwrap on the pipeline thread (`pisp.cpp:3091-3104@6b0b49f`, synchronous in `cfeBufferDequeue` `:2262-2266`) and Core's re-compression on the copy worker (`CameraController.cpp:5134-5135`, LUT at `:1646-1658@01f170c`), plus 12-bit packing. Probable cause of the loss; the loss itself is measured. |
| Symptom, where seen | Not a wrong picture: index holes in the clip folder, dropped-frames chip counting during the take, black flashes in the WebUI Clip Viewer (missing frame drawn black), one-frame gaps in an NLE, MLV buffer full. 16-bit at 25 fps runs clean. |
| Lines that would change | Probable: the unwrap call site `pisp.cpp:3099-3104@6b0b49f` (move off the pipeline thread, `QBC_RAW_CPU_WORKER`), Core's copy worker `CameraController.cpp:5134-5135@01f170c`. Unconfirmed which one limits. |
| Support | **Confirmed** measurements in KB: `working/drop-frames/nvme-campaign/findings.md:170` "HDR12: every step from 30 down to 25 dropped frames within 2-93 s"; `:207,229` 291 frames lost at 30 fps, MLV buffer full at 9 s; `:119,179` HDR16 27 fps carried, 0 dropped at 25 fps for 12.6 min (G1-F4). |
| Counter-evidence | "Strange output" is an odd phrase for drops; the owner would more likely say "drops". Measured on Core 7e6e2a3 (clip-split), 8 commits past 01f170c (no record-path change between them per G1). |
| Provable from code | No (timing). |
| Cheapest separating test | T2 after one 12-bit take: `recording stats:` / `drop[` lines, or count files against the last frame index. |

### H4. Untested 1x1 sensor-windowed crops in 12-bit Clear HDR (pedestal frame or OB band at the top)

| Field | Content |
| --- | --- |
| Mechanism | The port reaches 27 windowed 1x1 crops in 12-bit Clear HDR (driver cd548ef, Core H12 list) that never ran on fork main. The driver carries an unresolved note that Clear HDR leaves about 19 OB rows at the top of a cropped buffer. Core crops OB rows only in 16-bit (`shouldUseRequestedActiveRawCrop` `CameraController.cpp:3663@01f170c` `imx585Clear16`; `Imx585Modes.hpp:203-208` adds OB rows to the transport only for H16). |
| Symptom, where seen | Crop sizes only (3840x1608, 3840x1920, 2048x..., 1440x1080 ...): dark band about 19 rows high at the top, or a flat pedestal (black-level) frame, or off colour; in preview, cDNG, MLV and players alike. 4K and 16-bit fine. |
| Lines that would change | Driver `imx585.c:3086-3091@cd548ef` (H12 mode range) and/or Core `Imx585Modes.hpp:78-87@01f170c` (kH12Modes), `CameraController.cpp:3663` (crop rule), `Imx585Modes.hpp:203-208` (transport). |
| Support | **Confirmed**: mode lists (G5-D1, G3-F1, G4-1); known-issue text `imx585.c:4139-4148@cd548ef`. No hardware record of any 12-bit Clear HDR 1x1 crop (G5-D2, G7-4; Cinemate hid 12-bit before the crop family landed). |
| Counter-evidence | The same commit 728904bb has `imx585.c:579-584@cd548ef`: "12-bit mode (SDR + ClearHDR-12 CCMP): ... Sensor outputs PIX_VWIDTH rows (no OB)", and says the 20 prepended OB rows are a RAW16 effect. Core's H16-only OB handling follows that. The 4K 12-bit capture of 2026-10-25 recorded no top band. **Probable**: the OB band is a 16-bit effect; the pedestal-frame risk for crops stays open. |
| Provable from code | No. |
| Cheapest separating test | T2 `stream=` and `raw=`; if a crop, record 1 s and run `python3 tools/clearhdr-gate/pedestal_check.py <take>` from the driver repo (reads the top rows and the pedestal). |

### H5. The mode itself: "4K Clear HDR" in the touch UI is not 4K, and the 12-bit and 16-bit tests take different routes

| Field | Content |
| --- | --- |
| Mechanism | `caa0153` dropped fork main's pin of colour Clear HDR to 3840x2160 (`CameraController.cpp:2824-2827@f60e301`); now only mono is pinned and the size snaps to the nearest H12/H16 row (`:3526-3531@01f170c`). The touch UI still labels the choice "4K Clear HDR", says Core forces 4K (`Apertar-UI qml/CameraPage.qml:453,1351,3382,3457@7ea9afc`), sends only `set_clear_hdr` (lands at 12-bit) and locks the size controls. The hardware button sends `set_clear_hdr` then `set_raw_bit_depth 16` (`ApertarCoreApp.cpp:10452-10463@01f170c`). |
| Symptom, where seen | Wrong size, field of view or softness for "4K Clear HDR": from SDR 1920x1080 it becomes binned 1080 (and then H1), from 10-bit 1440x1080 binned it becomes 1440x1080 1x1 (a quarter of the field), from a 3840 crop it stays a crop (H4). The size controls are locked, so the operator cannot fix it from the touch UI. 16-bit tested via the button may have been at another size. |
| Lines that would change | Core `CameraController.cpp:3526-3531@01f170c` (restore the 4K pin, or make it a deliberate choice); UI `qml/CameraPage.qml:453,1351-1360,3382,3457@7ea9afc` (label and comments). |
| Support | **Confirmed** in code (G4-1, G4-2, G3-F1, re-read `CameraController.cpp:3518-3531`). |
| Counter-evidence | Not a picture fault by itself; at 4K nothing changes. |
| Provable from code | Yes for the route; which route the owner took needs T1. |
| Cheapest separating test | T1 `resolution` after the owner's "12-bit" entry. Not 3840x2160 = H5 (then H1 or H4 for the picture). |

### H6. The sensor's HG/LG combination window: highlights clamp below WhiteLevel and render grey/pink

| Field | Content |
| --- | --- |
| Mechanism | In 12-bit the built-in combination is valid only for 9.6 dB <= GAIN + EXP_GAIN <= 29.1 dB (driver comment `imx585.c:171-179@cd548ef`). Core writes EXP_GAIN index 1 = +6 dB at every Clear HDR start (`include/apertar/core/Types.hpp:206@01f170c`, `CameraController.cpp:7076-7084`; same on fork main `Types.hpp:159@f60e301`), while its 12-bit ISO cap 720 is derived for +12 dB (`:2934-2936`) and does not follow the user-settable adder 0..5 (`:11761-11767`). Core writes `WhiteLevel = table.back() = 65520` with no measured clamp (`src/cdng/CdngEncoder.cpp:1490-1491`). |
| Symptom, where seen | Outside the window: highlights top out below white, render grey or magenta/pink in a raw converter and in preview, merge knobs look inert (adder 3+ at ISO above about 360, or above the cap if raised). Below the window (ISO 100..about 150 at +6 dB, gain codes 0..11): effect unknown. 12-bit only (16-bit merges to code 80). |
| Lines that would change | `CameraController.cpp:2934-2940,3017-3023@01f170c` (cap as a function of the adder, and a floor), possibly `CdngEncoder.cpp:1490-1491` (measured white). |
| Support | **Confirmed** code facts (G2-X1, G4-3, G5-D6, G7-7). Window measured by Cinemate: peak code 4095 -> 3188 -> 2408 above it (G1-F8, `sources/2026-10-23-clearhdr16-handoff.md:147`); Cinemate latched a measured WhiteLevel after magenta highlights (G7-3). |
| Counter-evidence | At the default adder 1 the upper bound sits at gain code 77, so cap 720 (code 57) is conservative (G7-7 is right on that). The lower bound's effect on CCMP is unconfirmed (AppNote section 5 p.18). Not a port regression (adder and cap identical on fork main). Cinemate's clamp was seen at both depths. |
| Provable from code | No. |
| Cheapest separating test | T1 `hdr_gain_adder`, `iso`; T3 `analogue_gain`. Then one DNG of a blown lamp: max decoded value vs WhiteLevel 65520 at ISO 100 and ISO 640. |

### H7. Inherent 12-bit CCMP encoding: coarse mid segment and clipped sub-black

| Field | Content |
| --- | --- |
| Mechanism | With the driver's curve the middle segment carries linear 500..11500 above black (about -7 to -2.4 stops under clip, which holds 18 % grey at code about 869) on 171 codes, 64 LSB16 per step. libcamera's LUT maps codes 0..201 to 3200, so sub-black noise is gone; Core stores black as code 0. |
| Symptom, where seen | Raw converter after an exposure push: banding/posterisation in shadows and mid-tones, one-sided noise floor and slightly lifted, tinted deep blacks. Not visible in the 8-bit previews or players (G9-F9: about 2 codes per display byte). 16-bit clean. |
| Lines that would change | None in Core (it is the sensor's encoding). Driver slope defaults `imx585.c:557-558,3720-3738@cd548ef` if a gentler curve is wanted, and then Core's `ClearHdrCcmp.hpp:24-30` must follow. |
| Support | **Confirmed** arithmetic (G4-7, G6-4, G8-F4, G9-F9, G1-F7, G2-F8). |
| Counter-evidence | Matches the design; KB knew it. On 2026-10-25 at 4K the 12-bit and 16-bit medians matched (6222 vs 6242), so the model curve is right in the mid segment at 4K (contradicts G6-4's "model may be wrong" at 4K). Step size: G6-4 quotes 6.4 % at linear 4200; 64/4200 is 1.5 % (6.4 % holds near linear 1000). |
| Provable from code | Yes for the quantisation; visibility needs footage. |
| Cheapest separating test | Histogram of stored codes in one 12-bit DNG (spike at 0, nothing in 1..201, sparse 701..871). Visual: same gradient in 12-bit and 16-bit, +2 EV in a converter. |

### H8. Clear HDR exposure rules differ by depth: ISO capped at 720, ISO/WB forced manual, shutter AE on 12-bit stats

| Field | Content |
| --- | --- |
| Mechanism | `enforceClearHdrExposureRules` (`CameraController.cpp:3069-3098@01f170c`, port 8175273) forces auto ISO and auto WB off and holds their last values; `clearHdrIsoCap` lowers ISO above 720 in 12-bit (1585 in 16-bit). Shutter auto stays on and AGC meters libcamera's software stats of the unwrapped buffer. |
| Symptom, where seen | Going from 16-bit (or SDR) to 12-bit: up to 1.1 stop darker preview and files if ISO was above 720, WB and ISO frozen at the last SDR values (colour cast after a light change), a different shutter than 16-bit for the same scene. Preview and files alike. |
| Lines that would change | `CameraController.cpp:2936-2940,3017-3023,3069-3098@01f170c`. |
| Support | **Confirmed** code (G3-F2, G4-5). Fork main ran AE/AWB in 12-bit. |
| Counter-evidence | Applies to both depths except the cap value; a cap is not "strange". |
| Provable from code | Yes. |
| Cheapest separating test | T1 before and after entering 12-bit: `iso`, `iso_max` (720), `iso_auto`, `wb_auto`, `iso_auto_after_clear_hdr`, `wb_auto_after_clear_hdr`, `shutter_us`. |

### H9. The files are right; only a viewer or a label is wrong

| Field | Content |
| --- | --- |
| Mechanism | 12-bit Clear HDR cDNG is uncompressed 12-bit codes under a 4096-entry LinearizationTable with BlackLevel 3200 and WhiteLevel 65520 in the linearised domain; only renderers that apply tag 50712 show it right. Labels: the WebUI calls every non-16-bit table clip "Clear HDR 12-bit companded", including 16-bit Log takes (`src/playback/ClipProbe.hpp:165-178@01f170c`); the touch UI shows 12-bit and Log clips as "16-bit" (`Apertar-UI src/dngdecoder.cpp:1074@7ea9afc`); no tag marks Log. The touch MLV player renders MLV on the ISP-matrix path and cDNG with Reinhard, so the same scene looks different by format. |
| Symptom, where seen | Near-black or crushed frame in a viewer that ignores the table (touch UI libtiff fallback `dngdecoder.cpp:1405-1495`, OS thumbnails, any third-party tool without linearisation); a "12-bit" report that is really a 16-bit Log take; wrong bit-depth label; MLV vs cDNG look difference. |
| Lines that would change | Labels: `ClipProbe.hpp:165-178@01f170c`, `Apertar-UI src/dngdecoder.cpp:1074`; fallback: `dngdecoder.cpp:1405-1495,748-848`. |
| Support | **Confirmed**: both in-house renderers apply the table and render H12 within 6/255 of H16 (G9-F1, F2, host run). Tags self-consistent (G2-F2, G8-F3). Labels **confirmed** (G1-F5, G9-F4, F5). |
| Counter-evidence | The in-house paths are right, the fallback is reached only if the manual parser rejects the file (G9-F3, probable it does not). Resolve and Adobe honour LinearizationTable (BMCC-style DNG). A preview fault cannot be a viewer fault. |
| Provable from code | Yes for the in-house renderers. |
| Cheapest separating test | T4 (tags right), then `curl -sD- -o h12.jpg 'http://<cam>:8000/api/media/frame?kind=folder&id=<clip>&n=0&w=640'` vs the owner's viewer. If the WebUI frame looks right and his tool does not, H9. |

### H10. The linearisation chain is broken: libcamera did not unwrap, or its live controls differ from Core's fixed table

| Field | Content |
| --- | --- |
| Mechanism | Core assumes without a check that every 12-bit Clear HDR buffer is libcamera-unwrapped linear 16-bit with black 3200 (`CameraController.cpp:1683-1685,8498,4090@01f170c`; no stream fact). libcamera arms the unwrap at configure only for imx585, 12-bpp, no QBC, WDR=1 (`pisp.cpp:1821-1823,2974-2988@6b0b49f`) and builds it from live GRAD_TH/GRAD_COMP/BRIGHTNESS (`:2990-3023`); Core's table is fixed at 500/11500/6/4/200 (`ClearHdrCcmp.hpp:24-30`). |
| Symptom, where seen | No unwrap: shadows and mid-tones lifted up to 16x, flat picture, in every output. Controls off defaults: preview right, cDNG wrong (black offset, banding, tone errors up to thousands of codes); MLV right. |
| Lines that would change | Core: a check of the configured format/packing before attaching the table (`CameraController.cpp:4090`, `:9491-9492`); reading the live controls into `ccmp::Params` instead of constants (`ClearHdrCcmp.hpp:24-30`). |
| Support | **Confirmed** that Core has no check (G2-F4) and that the two sides take parameters differently (G1-F6, G2-F3, G6-3, G8-F7). |
| Counter-evidence | Host check: Core's table equals libcamera's LUT for all 4096 codes at the driver defaults, identical on both driver branches (G3-F6, G8-F1, G5-D8). Nothing in Apertar writes those controls (Core writes only +0, +1, +5: `CameraController.cpp:7034-7037`). Re-read here: in the default (no-worker) path the unwrap runs when a job holds both Output0 and Stats (`pisp.cpp:2262-2266`), the BE takes a job only when both are present (`:1087-1093`), and IMX585 has no embedded data (CamHelper default `false`), so no frame skips or doubles the unwrap; the worker path holds the job until the CPU pass ends (`cfeJobReady` `:1104-1111`). |
| Provable from code | No (needs the deployed build and live controls). |
| Cheapest separating test | T2: `CcmpUnwrap: rebuilt LUT ... T1=500 T2=11500 slope_L=1/64 slope_H=1/16 blc_u12=200 ... LUT[4095]=65520` and `camera configured ... format=SRGGB16 ... storage_bits=12 packing=unpacked`; T3 controls at defaults. |

## 3. Disagreements between reports, settled

| Topic | Reports | Settled | How |
| --- | --- | --- | --- |
| Lossy DNG in 12-bit Clear HDR drops 4 LSB | G6-8 (yes) vs G2 (refused) | G2 right; G6-8 unreachable | `include/apertar/core/RecordingCapabilities.hpp:76-78@01f170c` "Lossy cDNG does not support Clear HDR", called in `applySettingsLocked` `CameraController.cpp:12737`; WebUI also refuses (`WebControlPage.cpp:7742`) |
| Can a frame reach Core or the BE without the unwrap? | G8-F6, G3 open (yes, maybe) vs G6-1 (always unwrapped) | Not in the default path | `pisp.cpp:2262-2266` unwrap when both buffers present; `:1087-1093` job complete only then; IMX585 CamHelper `sensorEmbeddedDataPresent()` false, so no third buffer re-runs it; worker path gated by `cpuPending` `:1104-1111`. Probable, not timing-proven |
| OB rows in 12-bit Clear HDR | G3-F1, G5-D2 (~19 rows) vs driver's own `imx585.c:579-584` (no OB in 12-bit) | Open; leans to "16-bit only" | Both comments in the same commit 728904bb; Core's transport adds OB rows only for H16 (`Imx585Modes.hpp:203-208`); no top band recorded at 4K 12-bit. Settle with T2 + pedestal_check.py on one crop |
| Gain adder vs window | G7-7 (cap conservative, fine) vs G4-3/G5-D6 (+6 dB breaks the window) vs G2-X1 (cap ignores adder) | All three right on different bounds | +6 dB: upper bound code 77 (cap 720 = code 57 is safe), lower bound code 12 (ISO about 150; effect unknown); adder 3+ breaks the upper bound under the cap. Same on fork main (`Types.hpp:159@f60e301`) |
| Preview black over-subtraction | G6-6 (12-bit cause) | Not 12-bit specific | IPA branch `src/ipa/rpi/pisp/pisp.cpp:697-726@6b0b49f` (`bitdepth >= 14 \|\| imx585HdrCcmp`) applies the same tuning BE BLC at both depths; 16-bit dark median about 3222 vs 12-bit about 3206, so over-subtraction is of the same size. Moved to section 4 |
| Renderers skip the table | G6-5 (near-black in players) vs G9 (they apply it) | G9 right for the in-house renderers | `src/playback/DngFrameReader.hpp:115-121@01f170c`, `Apertar-UI src/dngdecoder.cpp:1065-1075@7ea9afc`; only the libtiff fallback skips (G9-F3). In H9 |
| Black with the table honoured | G6-5 ("lifted, flat") vs G8-F3 (black at 0.000) | Both | Black code maps exactly to 0; the half-rectified noise floor has a positive mean. Small (H7) |
| Mid-segment step size | G6-4 (6.4 % at linear 4200) vs G4-7 (3 % at 5 stops under) | Arithmetic | 64/4200 = 1.5 %; 6.4 % is at about linear 1000. G4-7's figures hold |
| "Clear HDR 12-bit companded" label vs "16-bit" | G1-F5 vs G9-F4 | Both true | Different UIs: WebUI `ClipProbe.hpp:165-178`, touch `dngdecoder.cpp:1074` |

## 4. Considered and set aside (would hit 16-bit too, or no 12-bit-only symptom)

| Item | Why set aside |
| --- | --- |
| Tuning file without `_clearHDR` (G1-F10, G4-4) | Same file at both depths (`DefaultTuningSelection.hpp:183-198@01f170c`); would darken 16-bit too |
| Blend default 0 if Core's write fails (G5-D5) | Both depths |
| BE black over-subtraction from tuning (G6-6) | Both depths (section 3) |
| First-frame FE black (G6-7) | One frame, both paths |
| Pedestal frame at Clear HDR launch (G7-8) | Any depth |
| Log composed table (G1-F3, G3-F4, G2-F6, G8-F5) | Off by default; maths checked on host (max 69 LSB16); playback effect is a label (H9) |
| Uncompressed instead of lossless (G3-F3) | Same samples, verified by the port's reader |
| Mono needs the ccmp overlay param (G5-D4) | Mono only; rig is colour (assumed, check `grep imx585 /boot/firmware/config.txt`) |
| Windowed 2x2 crops (G5-D7) | Off unless `/sys/module/imx585/parameters/clearhdr_windowed_binning` is Y |
| fps tables, IFD cache key, black clamp domain (G4-9, G2-F9, G2-F10) | Latent, no symptom today |
| Which libcamera build (G1-F11) | Both candidate builds share CcmpUnwrap; T2's LUT line answers it |
