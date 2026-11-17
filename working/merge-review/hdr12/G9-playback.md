# G9: playback and thumbnails of 12-bit Clear HDR clips (cinemate-port)

Assignment G9 of the "12 bit clear HDR shows strange output" investigation. Read-only on the code repos. Nothing
ran on a camera. Written 2026-11-17 (x86_64 cloud session, no Pi).

| Ref | What |
| --- | --- |
| Core `cinemate-port` `01f170c` (`/home/user/Apertar-Core`) | every Core `path:line` without a ref |
| UI `cinemate-port` `7ea9afc` (`/home/user/Apertar-UI`) | every UI `path:line` without a ref |
| UI fork main `4415a55`, upstream 1.6.0 `43888e5` | `@main`, `@upstream-1.6.0` |
| G2 report (`hdr12/G2-core-record-path.md`) | what Core writes. Not re-derived here |

Short names as in G2: **H12** Clear HDR 12-bit, **H16** Clear HDR 16-bit, **S12** SDR 12-bit. LSB16 = one step
on the 16-bit scale. Labels: **confirmed** (read in code at the ref, or run on this host), **probable** (inferred,
reason given), **unconfirmed** (command named).

## 1. Short answer

- None of the playback renderers is the cause of a picture that differs between H12 and H16. Both renderers (Core
  for the WebUI, the touch UI's decoder) apply the LinearizationTable **before** black and white, then take
  BlackLevel and WhiteLevel from the tags. An H12 cDNG (12-bit CCMP codes + table, black 3200, white 65520) and an
  H16 cDNG (linear, black 3201, white 65535) of the same light give the same picture and the same histogram.
  Host run with the port's own `RawRender.hpp`: largest pixel difference 6/255, largest histogram bin difference
  0.032 (section 6).
- So if H12 looks strange in the WebUI viewer or the touch player but H16 does not, the **samples in the file**
  differ, not the rendering. The renderers show faithfully what libcamera delivered and Core stored (G2: the
  stored H12 values equal libcamera's to within one table step). The cause sits upstream of the file: libcamera's
  unwrap, the driver mode or registers, or a stale configure (G2-F1).
- The touch UI decoder is unchanged by the port and identical to upstream 1.6.0 and fork main
  (`diff -q /home/user/wt/ui-upstream/src/dngdecoder.cpp /home/user/Apertar-UI/src/dngdecoder.cpp` prints
  nothing; same for `cdngimageprovider.cpp` upstream vs main; the port's diff to `cdngimageprovider.cpp`,
  `playbackcontroller.cpp`, `cliplistmodel.cpp` only changes how frame files are listed, for `part_NNN/` folders).
- Real but non-picture defects found: the touch UI calls an H12 clip "16-bit" (F4); Core's clip facts call an
  H16 **Log** clip "Clear HDR 12-bit companded" (F5); nothing marks a Log clip, and every renderer un-logs it
  through the table, so a Log clip plays back looking linear (F5).
- Paths that would make H12 look wrong exist only in fallbacks or in the G2-F1 stale state: the touch UI's
  libtiff fallback ignores the table (H12 near black, histogram all in bin 0, F3); a stale H12 MLV plays back as a
  wrapped picture in the touch MLV player (F6).

## 2. The renderers, what they read

| Renderer | Used by | Files |
| --- | --- | --- |
| **R-Core** | WebUI clip browser thumbnails (`w=320`) and the WebUI Clip Viewer (`w` 640..1920), `/api/media/frame`, header `X-Histogram` | `src/playback/DngTags.hpp`, `DngFrameReader.hpp`, `RawRender.hpp`, `PlaybackFrames.cpp`, `ClipProbe.hpp`; route `src/ApertarCoreApp.cpp:8475-8549` |
| **R-UI** | touch clip browser thumbnails (`image://cdngthumb`), touch player frames (`image://cdng`, `image://cdngplay`), touch histogram | UI `src/dngdecoder.cpp` (decode + histogram), `src/cdngimageprovider.cpp` (render), `src/playbackcontroller.cpp`, `src/cliplistmodel.cpp` |
| **R-UI MLV** | touch player for `.mlv` | UI `src/MlvReader.cpp` -> `renderRawFramePreview` (`src/cdngimageprovider.cpp:821`) |

R-Core is new ground (no `src/playback/` in `/home/user/wt/core-upstream` or `/home/user/wt/core-main`; added by
`f91fafa`, `ab4cc92`, `1af26c8`, `618b2f1`). Its header says it is a named copy of R-UI
(`src/playback/RawRender.hpp:3-9`).

### 2.1 Tags read

| Tag | R-Core | R-UI manual path | R-UI libtiff fallback |
| --- | --- | --- | --- |
| 256/257 size, 258 BitsPerSample, 259 Compression, 262 Photometric, 277 | `DngTags.hpp:248-254` | `dngdecoder.cpp:926-951` | `:1443-1470` (`TIFFGetField`) |
| 0x828E CFAPattern | `DngTags.hpp:255-261` | `:959-961` | `:1476-1490` |
| 0xC61A BlackLevel (50714) | first value only, any numeric type incl. RATIONAL: `DngTags.hpp:262`, `:137-153` | first value, SHORT/LONG/RATIONAL/SRATIONAL: `dngdecoder.cpp:963-968`, `:343-372` | first value: `:1475` |
| 0xC61D WhiteLevel (50717) | `DngTags.hpp:263` | `:970-978`; if white <= black: `(1 << min(bits,15)) - 1` | `:1476`; default `(1 << min(bits,15)) - 1` |
| 0xC618 LinearizationTable (50712) | `DngTags.hpp:264-268` | `:1065-1075` | **not read** |
| 0xC68D ActiveArea | not read | `:980-989` | `:1477-1483` |
| 322/323/324/325 tiles, 273/279 strip | `DngTags.hpp:269-284` | `:924-1020` | libtiff |
| 0xC621/0xC622 CM, 0xC714/0xC715 FM, 0xC628 AsShotNeutral, 0xC627 AnalogBalance | `DngTags.hpp:293-304` | `applyColorMetadataFromEntries` `:378-420` | not read in `decodeFileInto` |
| 51044 FrameRate | `DngTags.hpp:285` | `detectFrameRate` `:1508-1573` | - |
| any Log marker | none exists. `grep -n -i log src/cdng/CdngEncoder.cpp` finds no tag; `grep -rn -i log src/playback/` finds nothing | none | none |

### 2.2 Order: table, then black and white

| Renderer | Table applied | Then black / white | Evidence |
| --- | --- | --- | --- |
| R-Core picture | after unpack / lj92 decode, to every sample, clamped to the last entry | `norm = clamp((s - black) / (white - black), 0, 1)` | `DngFrameReader.hpp:115-121`; `RawRender.hpp:267-270` |
| R-Core histogram (`X-Histogram`) | same samples as the picture | `(s - black) / (white - black)`, 48 bins, `counts^0.65`, x1000 as integers | `PlaybackFrames.cpp:228-233`; `RawRender.hpp:332-349` |
| R-UI picture, manual path | after unpack / lj92 decode; any code past the table fails the decode (falls to libtiff) | `renderRawPreviewImpl` `cdngimageprovider.cpp:608-613` | `dngdecoder.cpp:1065-1075` |
| R-UI histogram, manual path | per sampled row, before the bin | `HistogramAccumulator::consumeCurrentRow` `dngdecoder.cpp:505-518` | `dngdecoder.cpp:687-692`, `:731-738` |
| R-UI picture, libtiff fallback | **no** | black and white from tags, on raw codes | `dngdecoder.cpp:1405-1495` |
| R-UI histogram, libtiff fallback | **no** | same | `dngdecoder.cpp:748-848` |

Black and white are always from the tags (no constants, no bit-depth guess) except the fallback white when the tag
is missing or not above black. Both renderers read the first BlackLevel only; Core writes four equal values in
Clear HDR (G2 section 3.1), so no loss.

### 2.3 Layout handling

| Layout | R-Core | R-UI |
| --- | --- | --- |
| BitsPerSample 12, uncompressed, MSB-first packed | `DngFrameReader.hpp:69-73` (pairs, 3 bytes) | `unpackSamples` `dngdecoder.cpp:1181-1199` (NEON + scalar) |
| BitsPerSample 16, uncompressed LE | `:67-68` | `:1146-1152` |
| 10-bit | `:74-80` | `:1154-1180` |
| Compression 7 (lossless JPEG tiles) | lj92, checks `jw * jcomp == tileWidth`, `jh == tileLength`; does not check precision | lj92, checks `precision == bits` (`dngdecoder.cpp:49-64`) |
| Other compression (lossy DNG 34892) | refused: "Unsupported DNG layout" `DngTags.hpp:307-311` | refused by the manual path `:1005-1006`, then libtiff |
| BitsPerSample after decode | stays 12 in `DngInfo` (only used for the label) | set to **16** when a table was applied (`dngdecoder.cpp:1074`) |

### 2.4 Rendering (identical maths in both, confirmed by reading)

Quad debayer (one RGB per 2x2), white balance from AsShotNeutral x AnalogBalance (default 2.8/1/1.6), camera->sRGB
from ForwardMatrix or inverted ColorMatrix (blend by neutral ratio), Reinhard `x/(1+x)`, saturation 1.35 with
highlight roll-off, gamma 2.2 (`RawRender.hpp:258-329`; UI `cdngimageprovider.cpp:587-698`). Full white after
Reinhard is 0.5, so the brightest grey a cDNG renders is byte 186 (host, section 6), for every clip type.

## 3. What each clip type looks like

Input per G2 section 3.1 (fresh configure, the normal case).

| Clip | File | R-Core thumb / viewer / histogram | R-UI thumb / player / histogram |
| --- | --- | --- | --- |
| H12 cDNG, uncompressed or lossless, Log off | 12-bit CCMP codes, table 4096 (CCMP expansion), black 3200, white 65520 | **correct**: same as H16 within 6/255 (CCMP step quantisation in the 64-LSB16 zone); histogram same as H16 | **correct**, same maths. Info panel says "16-bit" (F4) |
| H12 cDNG, Log on | 12-bit Log codes, table = Log inverse, black 3200, white 65520 | un-logged by the table: **looks linear**, same as Log off within the Log error (69 LSB16, G2 section 5). Format line "Clear HDR 12-bit companded" | same, un-logged; "16-bit" |
| H16 cDNG, Log off | 16-bit linear, black 3201, white 65535 | **correct** | **correct**; "16-bit" |
| H16 cDNG, Log on | 12-bit Log codes + Log inverse table, 3200 / 65520 | looks linear; format line **"Clear HDR 12-bit companded"** (wrong, F5) | looks linear; "16-bit" |
| S12 cDNG (PiSP decode, no table) | 12-bit, black 200, white 4095 | correct; within 10/255 of H12 for the same linear light (host) | correct; "12-bit" |
| H12 MLV (fresh) | 16-bit linear, RAWI black 3201, white 65535 | WebUI has no MLV thumbnail or viewer (`pbThumbUrl` only for `format === "cdng"`, `WebControlPage.cpp:11709-11713`) | R-UI MLV: same as an H16 MLV. MLV uses a different look than cDNG (F7) |
| H12 MLV after a cDNG -> MLV switch without reconfigure (G2-F1) | 12-bit, low 12 bits of linear, black 200, white 4095 | not shown | **wrapped picture**: noise, speckle, false colour (F6) |
| H12 cDNG after an MLV -> cDNG switch without reconfigure (G2-F1) | take fails at the first frame (G2) | "No frames in the folder." or not listed (unconfirmed) | not listed or no picture (unconfirmed) |
| H12 cDNG read through the R-UI libtiff fallback | codes against black 3200 / white 65520 | n/a | **near black** (brightest byte 60 of 255), histogram all in bin 0 (F3) |

Brightness of all Clear HDR clips: white = full HDR scale (65520 / 65535). A scene exposed for mid grey therefore
sits low and renders darker than an SDR clip of the same scene exposed the same way. This holds for H12 and H16
alike, so it cannot explain "12-bit strange, 16-bit fine".

## 4. Findings

| ID | Claim | Status | Symptom (where) | Evidence | Settle with |
| --- | --- | --- | --- | --- | --- |
| G9-F1 | R-Core applies LinearizationTable before black/white and takes black/white from the tags; an H12 cDNG renders like the H16 cDNG of the same light (max 6/255) and gives the same `X-Histogram` (max bin diff 0.032) | confirmed (code + host) | none. Rules out the WebUI viewer, WebUI thumbnails and `X-Histogram` as the source of an H12-only difference | `DngFrameReader.hpp:115-121`; `DngTags.hpp:262-268`; `RawRender.hpp:267-270`, `:332-349`; `PlaybackFrames.cpp:228-233`; host probe section 6 | on the Pi: `curl -sD- -o h12.jpg 'http://<cam>:8000/api/media/frame?kind=folder&id=<H12 clip>&n=<n>&w=640'`, same for an H16 clip of the same scene, compare the pictures and `X-Histogram` |
| G9-F2 | R-UI's manual path does the same (table then tags) for picture and histogram; the decoder is unchanged from upstream 1.6.0 | confirmed | none in the touch player / browser | `dngdecoder.cpp:1065-1075`, `:687-692`, `:731-738`, `:963-978`; `cdngimageprovider.cpp:608-613`; `diff -q` vs `/home/user/wt/ui-upstream` empty | same clip pair in the touch player |
| G9-F3 | R-UI's libtiff fallback (`decodeFileInto` after a manual failure, `decodeTiffHistogram`) ignores LinearizationTable; an H12 or Log clip read there renders near black and the histogram piles in bin 0. Reached only if the manual parser rejects the file (e.g. a code past the table, a malformed tag). Upstream has the same code | confirmed (code), probable not reached for Core's files (the manual parser accepts every layout Core writes; a 4096 table covers every 12-bit code) | touch player / thumbnail black or almost black, histogram flat at the left, **H12 only** (H16 has no table) | `dngdecoder.cpp:1405-1495`, `:748-848`, `:1070-1072` (`sample >= table.size()` -> fail) | add a log line in `decodeFileInto` when `decodeManualRaw` fails, play an H12 clip on the Pi |
| G9-F4 | Touch UI reports an H12 (and any Log) clip as "16-bit": `decodeManualRaw` sets `bitsPerSample = 16` after the table, and the info panel prints it. WebUI prints "12-bit" and "Clear HDR 12-bit companded" for the same clip | confirmed | label only (touch player info: bit depth "16-bit" for a 12-bit mode) | `dngdecoder.cpp:1074`; `playbackcontroller.cpp:160-163`, `:1176-1179`; Core `ClipProbe.hpp:172-178`, `ApertarCoreApp.cpp:7370-7371`, `:7388`, `:7399` | open an H12 clip in both players |
| G9-F5 | Nothing in the DNG marks Log. Every renderer (and every DNG reader) un-logs a Log clip through its inverse table, so Log plays back looking linear. Core's format line keys on (bits, table) only, so an **H16 Log** clip reads "Clear HDR 12-bit companded" and an H12 Log clip cannot be told from H12 linear | confirmed | WebUI clip info FORMAT row wrong for H16 Log; no "Log" anywhere in playback. A user expecting a flat Log picture sees a normal one | `ClipProbe.hpp:165-178`; `include/apertar/core/Types.hpp:364-371` (Log stores 12 bits, G2 section 5); `grep -n -i log src/cdng/CdngEncoder.cpp` (no tag) | record H16 with Log on, open in WebUI clip info |
| G9-F6 | The touch MLV player renders a G2-F1 stale H12 MLV (12-bit view of the low 12 bits of linear 16-bit, RAWI black 200 white 4095) as a wrapped picture | confirmed by chaining G2-F1 with `MlvReader.cpp:88-101`, `:61-69`; picture look probable | touch player MLV: speckle, banding rings, magenta/green blotches; **H12 only**, and only after a format switch without a reconfigure | G2 section 3.2 and G2-F1; `MlvReader.cpp:255-276` | on the Pi: H12 cDNG take, switch to MLV, take; `mlv_dump -v` RAWI bits; play it |
| G9-F7 | MLV and cDNG of the same scene look different in the touch UI: MLV uses the ISP-matrix path (`srgb8`, clip, digital gain from EXPO, no Reinhard) when a preview matrix or Apertar IDNT is present; cDNG uses Reinhard + gamma 2.2. Same for H12 and H16 | probable (read `MlvReader.cpp:148-158`, `:210-211`, `:268-273`, `cdngimageprovider.cpp:654-663`; whether Core writes the matrix block not checked) | MLV brighter / more contrasty than cDNG in the touch player, all modes | as listed | play the same scene as cDNG and MLV |
| G9-F8 | The renderers trust the file's black. H12's black is fixed at 3200 and ignores `SensorBlackLevels`; H16's comes from `SensorBlackLevels` (G2 section 6). If the true black after libcamera's unwrap is not 3200, H12 alone shows lifted (grey, low contrast) or crushed shadows with a colour cast near black in **every** renderer, raw converters included | confirmed (dependency), unconfirmed whether the true black differs | grey or tinted blacks in H12 only, all viewers | G2: `CC:4093-4095`, `CdngEncoder.cpp:1476-1479` | on the Pi, lens cap on, H12 cDNG: `exiftool -BlackLevel` and the mean of the stored codes through the table, vs 3200 |
| G9-F9 | CCMP quantisation is visible only in grading, not in playback: codes 701..871 (171 codes, 64 LSB16 per step) cover linear 0.9 %..18 % of range; on the 8-bit preview that is display bytes 30..109, about 2 codes per byte. A raw converter pushing shadows/midtones will show banding in H12 that H16 does not have | confirmed (host numbers, section 6) for the default knees/slopes; whether the driver's slopes are the intended ones is G-other's angle | posterised midtones after an exposure push in a raw converter, H12 only. Not visible in R-Core / R-UI | `src/cdng/ClearHdrCcmp.hpp:24-30`; host `steps` probe | open an H12 and an H16 frame of a smooth gradient in Resolve, +2 EV |
| G9-F10 | If libcamera did **not** decompand (handed 12-bit codes in 16-bit containers), Core's compression LUT would map every sample <= 3200 to code 0 and the renderers would show an almost black frame with faint highlights; H16 unaffected | probable (from `ClearHdrCcmp.hpp:69-83` and G2 section 4) | WebUI / touch playback almost black for H12 | G2 section 4 | `journalctl -u apertar-core | grep 'camera configured'` must say `format=SRGGB16` in H12; check one stored code histogram |

## 5. What does not differ between H12 and H16 in playback

| Item | Same for H12 and H16 | Evidence |
| --- | --- | --- |
| Frame lists, `part_NNN/` handling | the port's only change in the touch UI playback files | `git -C /home/user/Apertar-UI diff origin/main cinemate-port -- src/cdngimageprovider.cpp src/playbackcontroller.cpp src/cliplistmodel.cpp`; `src/ClipFrameFiles.hpp` |
| JPEG cache key | clip id + frame number + width + token; no format input | `PlaybackFrames.cpp:185` |
| Size caps | 5472 x 3648; IMX585 rows fit | `DngTags.hpp:29-44`, `:307-311` |
| `X-Histogram` transport | 48 integers 0..1000, drawn as `value/1000` | `PlaybackFrames.cpp:230-233`; `WebControlPage.cpp:12370`, `:12284-12301` |
| Thumbnail URL | first frame, `w=320`, only cDNG | `WebControlPage.cpp:11709-11713` |

## 6. Host evidence

Probe at `/tmp/claude-0/-home-user/c92f0a57-d507-5425-af34-ea239a4bf210/scratchpad/g9/probe.cpp` and `steps.cpp`,
built with `g++ -std=c++20 -O2 -I/home/user/Apertar-Core/src`. Uses the port's `src/cdng/ClearHdrCcmp.hpp` and
`src/playback/RawRender.hpp` unchanged. A 256x128 ramp of linear values 3200..65520 (plus noise) stored three ways:
H12 = `expansion[compression[v]]` with black 3200 / white 65520; H16 = `v` with 3201 / 65535; S12 = `v >> 4` with
200 / 4095.

```
H12 (table applied) vs H16 render: max |diff| = 6 of 255
H12 vs S12 (same linear >>4) render: max |diff| = 10 of 255
H12 codes without table, black 3200 white 65520: brightest output byte = 60
histogram H12 vs H16 max bin diff = 0.032; no-table histogram bins>0: 0
code  700 lin  3693 norm 0.0079 byte  28
code  701 lin  3757 norm 0.0089 byte  30
code  871 lin 14505 norm 0.1814 byte 109
code 4095 lin 65520 norm 1.0000 byte 186
codes 701..871 cover bytes 30..109 with 171 codes
```

G2 section 10 already showed the port's `DngFrameReader` returns libcamera's values from real encoder output
(uncompressed and lossless, 0 differing samples). Together: file -> R-Core picture is correct for H12.

## 7. Open questions

- Which screen the owner looked at. If it was a playback screen, F1/F2 say the file content is the thing to check:
  compare the `X-Histogram` of an H12 and an H16 clip of one scene; a large difference means the samples differ.
- Whether Core's MLV writer emits the preview-matrix / IDNT blocks that switch R-UI MLV to the ISP path (F7).
- Whether a G2-F1 stale cDNG take leaves an empty folder the browsers list.
