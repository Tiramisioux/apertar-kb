# V-H9: skeptic check of H9 ("files right, only a viewer or a label is wrong")

Assignment V, hypothesis H9. Read-only on the code repos. Host program under
`/home/user/build/hdr12-numeric/v-h9/`. Written 2026-11-17, x86_64, no Pi.

| Ref | What |
| --- | --- |
| Core `cinemate-port` `01f170c` | every Core `path:line` without a ref |
| UI `cinemate-port` `7ea9afc` | every UI `path:line` marked UI |
| UI upstream 1.6.0 `43888e5` | `@upstream-1.6.0` |

## 1. Verdict

H9 splits into three claims. Each was tested on its own.

| Part of H9 | Verdict | Why |
| --- | --- | --- |
| A. An in-house viewer (WebUI viewer, touch player, touch thumbnails, either histogram) shows an H12 cDNG wrong while the file is right | **refuted** | Both renderers apply the table, then the tags. The only table-blind path (UI libtiff fallback) is not reached by any layout Core writes (section 3) |
| B. A third-party tool without LinearizationTable shows H12 near black | **true as a mechanism, narrow as a cause** | Host run: without the table the brightest H12 code normalises to 0.0144, 18 % grey to 0.0000 (section 4). Whether the owner's tool ignores tag 50712 is not code-provable |
| C. Labels are wrong | **confirmed defect, wider than H9 states** | Touch UI says "16-bit" for every table clip. WebUI says "Clear HDR 12-bit companded" for **H16 Log and for SDR Log (10-bit stored)**, not only H16 Log (section 5) |
| D. MLV and cDNG take different render paths in the touch player | **confirmed (code)**, not H12-specific | section 6 |

What H9 cannot explain: anything on the live preview (HDMI, touch live view, WebUI live preview), anything that differs between H12 and H16 inside the in-house players, and file-level differences such as the fixed H12 black (section 7). H9 survives only as "the owner saw a label, or opened H12 in a tool that ignores the table".

## 2. What Core writes for H12 (the input to every viewer)

| Item | Value | Evidence | Status |
| --- | --- | --- | --- |
| BitsPerSample | 12 (`ifd.add(258, ..., &bits)`) | `src/cdng/CdngEncoder.cpp:1472`, `:1650` | confirmed |
| Raw IFD | the root IFD, NewSubFileType 0, Photometric 32803 | `CdngEncoder.cpp:1647`, `:1652`, `:1483` | confirmed |
| LinearizationTable | tag 0xC618, SHORT, count = table size; Core throws unless size == `1 << bits` | `CdngEncoder.cpp:1704-1706`, `:1338-1340` | confirmed |
| Table content | `ccmp::expansionTable()`, 4096 entries, monotonic, last 65520 | `src/camera/CameraController.cpp:4092`; `src/cdng/ClearHdrCcmp.hpp:46-63`; host: `table monotonic: 1, last=65520` | confirmed |
| BlackLevel | RATIONAL x4, 3200/1 (fixed `kBlack16`, ignores `SensorBlackLevels`) | `CameraController.cpp:4093-4095`; `CdngEncoder.cpp:1473-1481`, `:1703` | confirmed |
| WhiteLevel | LONG, `table.back()` = 65520 | `CdngEncoder.cpp:1490-1491`, `:1707` | confirmed |
| Lossless | SOF3, precision = `bits` (12), width = tileWidth/2, 2 components | `src/cdng/LosslessJpegEncoder.cpp:111-145` | confirmed |
| Round trip | `expansion[compression[v]] >= v` for every v 3200..65520, never below (host, 0 failures) | `ClearHdrCcmp.hpp:66-80`; `v-h9/vh9.out` | confirmed |

The tags are self-consistent per the DNG order (table first, then black, then white). The file is "right" relative to libcamera's 16-bit output. It is not proved right relative to the sensor: the table is a constant built from driver defaults and "Core never writes the gradient-compression controls" (`ClearHdrCcmp.hpp:21-22`). That is H10's territory, not H9's.

## 3. Part A: in-house viewers. Refuted

### 3.1 Touch UI, manual parser (`UI src/dngdecoder.cpp`, identical to `@upstream-1.6.0`)

| Step | Code | H12 result |
| --- | --- | --- |
| Raw IFD found | `matchesRawEntries` needs width, height, Photometric CFA/LinearRaw, SPP 1 (`:429-451`) | root IFD matches |
| Compression gate | only 1 or 7 (`:1005-1006`) | Core writes 1 or 7 |
| Tiles | tile path requires compression 7, tile width <= 131070 (`:1008-1013`) | passes |
| lj92 | `jpegWidth * components == width && jpegHeight == rows && precision == bits` (`:59-60`) | Core: `rawWidth/2 * 2`, rows, precision 12 = BitsPerSample 12. Passes |
| Table | `sample >= table.size()` fails the decode (`:1070-1072`) | 12-bit samples < 4096. Passes |
| Black / white | from tags (`:963-978`) after table | 3200 / 65520 on linear values |
| Histogram | same gates and same table step (`:686-736`) | same |

So `decodeManualRaw` returns true for every H12 layout Core writes, and `decodeFileInto` returns before the libtiff code (`:1425-1427`). The libtiff fallback (`:1429-1504`) does ignore tag 50712, and `decodeTiffHistogram` (`:746-848`) too, but they are reached only for a malformed or truncated file. Note also: libtiff cannot decode compression 7 SOF3 tiles, so for a lossless H12 file the fallback fails outright ("no picture"), it does not render near black. Near black from the fallback is possible only for an **uncompressed** H12 frame the manual parser rejects, e.g. a truncated strip (`:1036-1040`, `stripByteCount < requiredBytes` at `:1039`). A truncated strip would hit H16 the same way.

Status: confirmed by reading. Remaining unknown: a file damaged on disk. Settle: `exiftool -warning -BitsPerSample -Compression -StripByteCounts <frame>` on the owner's frame.

### 3.2 WebUI (Core `src/playback/`)

| Step | Evidence |
| --- | --- |
| tags read incl. 0xC618 | `src/playback/DngTags.hpp:262-268` |
| table applied to every sample, clamped to last entry | `src/playback/DngFrameReader.hpp:115-121` |
| norm from tag black / white | `src/playback/RawRender.hpp:267-270` |

No table-blind path exists in Core. Confirmed.

### 3.3 The 6/255 claim

Not re-run (G9's probe uses the port's `RawRender.hpp` unchanged). My own check confirms the input side: with the table, 18 % grey of an H12 frame normalises to 0.1804 against 0.18 linear (`vh9.out`). The renderer maths after the table is shared by H12 and H16, so the in-house pictures can differ only by CCMP quantisation. Confirmed for the input; the 6/255 figure is G9's.

## 4. Part B: tools that ignore the table. Mechanism confirmed, cause unproven

Host program `/home/user/build/hdr12-numeric/v-h9/vh9.cpp` (includes the port's `src/cdng/ClearHdrCcmp.hpp` unchanged; `g++ -std=c++20 -O2 -I/home/user/Apertar-Core/src`). Output `vh9.out`:

```
table[3200]=51373  lin frac=0.7730
max norm w/o table=0.01436 (code 4095)
18% grey: code 870, norm with table 0.1804, w/o table 0.0000
values where expansion[compression[v]] < v: 0
table monotonic: 1, last=65520
```

| Fact | Meaning |
| --- | --- |
| Code 3200 (the tag black read as a code) = 77 % of linear range | a table-blind reader clips everything below 77 % of the HDR range to black |
| Brightest code normalises to 1.4 % | the whole frame sits in the bottom 1.4 % of the range: near black, only the top highlights faintly visible |
| 18 % grey -> 0 | mid tones pure black |

So "H12 near black, H16 fine" in a table-blind tool is real and **specific to H12** (H16 has no table). That matches "12-bit strange, 16-bit fine".

Which tools are table-blind is not in this code. Resolve, Adobe Camera Raw and LibRaw read tag 50712 (probable: it is a DNG 1.0 tag; Blackmagic's own 12-bit cDNG used it). Simple TIFF viewers, image libraries reading the CFA as a plain TIFF, and libtiff-based scripts do not. Status: unconfirmed for the owner's tool. Settle: ask which program; `exiftool -LinearizationTable -b <frame> | head -c 40` proves the tag is there.

The DNG is otherwise conservative (root raw IFD, DNGVersion 1.4 / backward 1.3, `CdngEncoder.cpp:1684-1687`), so a tool that honours 50712 has nothing else in H12 to trip over that H16 lacks, apart from BitsPerSample 12 MSB-first packing, which SDR 12-bit uses too.

## 5. Part C: labels. Confirmed defects

### 5.1 Core clip facts (WebUI FORMAT row)

`src/playback/ClipProbe.hpp:165-178`:

```cpp
        const bool table = !f.first.linearization.empty();
        ...
        if (f.first.bits == 16) look = "Clear HDR 16-bit";
        ...
        else if (table) { look = "Clear HDR 12-bit companded"; f.companded = true; }
        else look = "SDR " + std::to_string(f.first.bits) + "-bit";
```

The rule is "any table on a non-16-bit file = Clear HDR 12-bit". Which takes carry a table:

| Take | Stored bits | Table | Label shown | Correct? | Evidence |
| --- | --- | --- | --- | --- | --- |
| H12, Log off | 12 | CCMP expansion | Clear HDR 12-bit companded | yes | `CameraController.cpp:4090-4095` |
| H12, Log on | 12 | composed Log inverse | Clear HDR 12-bit companded | Log not shown | `CameraController.cpp:4031-4033`, `include/apertar/core/Types.hpp:366-367` |
| **H16, Log on** | 12 | Log inverse | **Clear HDR 12-bit companded** | **no** | `Types.hpp:352` (16 -> 12), `CameraController.cpp:5129` |
| **SDR 12, Log on** | 10 | Log inverse | **Clear HDR 12-bit companded** | **no** (not Clear HDR, not 12-bit) | `Types.hpp:352` (12 -> 10) |
| SDR 10, Log on | 8 | Log inverse | Clear HDR 12-bit companded | no | `Types.hpp:352` (10 -> 8) |
| H16, Log off | 16 | none | Clear HDR 16-bit | yes | |

Wire: `ApertarCoreApp.cpp:7371` (`companded`), `:7399` (`format`). New ground (no `src/playback/` upstream). The SDR Log rows are new relative to G9-F5.

### 5.2 Touch UI bit depth

`UI src/dngdecoder.cpp:1074` sets `frame.bitsPerSample = 16` after applying any table; `UI src/playbackcontroller.cpp:160-163` prints it. Every table clip (H12, any Log) reads "16-bit". The line is upstream code (`grep -n "bitsPerSample = 16" /home/user/wt/ui-upstream/src/dngdecoder.cpp` -> `:1074`), so not a port regression. After decode nothing but the label reads `bitsPerSample` (`grep -n bitsPerSample` over `src/cdngimageprovider.cpp`, `src/playbackcontroller.cpp`: only `:162-163`). Confirmed.

Effect on the report: an owner who opens an H12 clip in the touch player sees "16-bit"; one who opens an H16 Log take in the WebUI sees "Clear HDR 12-bit". Either reads as "12-bit Clear HDR is strange". This is the only part of H9 that is a provable defect.

## 6. Part D: MLV vs cDNG in the touch player

`UI src/MlvReader.cpp:268-273` passes a preview matrix (MLV colour block) or the Apertar colour matrix plus `m_digitalGain` into `renderRawFramePreview`; the cDNG path renders through `cdngimageprovider.cpp` Reinhard + gamma without them. Confirmed that the paths differ. It is the same for H12 and H16, so it cannot explain an H12-only report. The stale-MLV case (G2-F1, G9-F6) is a file defect, not a viewer defect, so it is outside H9.

## 7. Where H9's premise "files are right" is weaker than stated

| Item | Status |
| --- | --- |
| H12 black is the constant 3200; H16 takes `SensorBlackLevels` (`CameraController.cpp:4075-4095`). If the real black after unwrap differs, H12 alone has lifted or crushed shadows in every viewer | confirmed dependency, unconfirmed size (G9-F8) |
| Table is a constant from driver defaults (`ClearHdrCcmp.hpp:21-22`) | confirmed; whether the sensor runs those defaults is H10 |
| Live preview does not read the file | confirmed by architecture; any preview symptom is outside H9 |

## 8. Fix sketches (labels only; nothing in the picture path needs a fix for H9)

### 8.1 Core `src/playback/ClipProbe.hpp:165-178`

Tell the CCMP table apart from a Log table by content; `ClearHdrCcmp.hpp` is already a header-only part of Core.

```cpp
        // FORMAT row (design 4.3): 16-bit = Clear HDR; the CCMP table = Clear HDR 12-bit; any other table = Log
        const bool table = !f.first.linearization.empty();
        const auto &ccmpTable = ccmp::expansionTable();
        const bool ccmp = f.first.bits == 12 && f.first.linearization.size() == ccmpTable.size()
            && std::equal(ccmpTable.begin(), ccmpTable.end(), f.first.linearization.begin());
        ...
        if (f.first.bits == 16) look = "Clear HDR 16-bit";
        else if (lossy3 && table) { ... unchanged ... }
        else if (lossy5 && table) { ... unchanged ... }
        else if (ccmp) { look = "Clear HDR 12-bit companded"; f.companded = true; }
        else if (table) { look = "Log " + std::to_string(f.first.bits) + "-bit"; f.companded = true; }
        else look = "SDR " + std::to_string(f.first.bits) + "-bit";
```

H12 Log then reads "Log 12-bit" (true: its table is the composed Log inverse). The source mode of a Log take stays unknown from the file alone; that needs a tag and is out of scope.

Host test, following `tools/dng_payload_write_test.cpp` (the one test that already drives `CdngEncoder`): `tools/clip_probe_format_test.cpp` writes three one-frame clips into a temp dir with `CdngEncoder` (12-bit + `ccmp::expansionTable()`; 12-bit + a 4096-entry ramp table; 10-bit + a 1024-entry table), runs `probeClip` on each, and checks `formatText` starts with "Clear HDR 12-bit companded", "Log 12-bit", "Log 10-bit". Today the second and third fail.

### 8.2 UI `src/dngdecoder.cpp:1074`

Delete `frame.bitsPerSample = 16;`. Nothing after decode reads it except the label (section 5.2), so the label then shows the stored depth (12 for H12). This touches upstream code; propose it to the original developer as a one-line change, not as part of the port. UI has no host test harness for the decoder; check by opening an H12 clip in the touch player (info row "12-bit").

## 9. What remains for the Pi

| Test | Distinguishes |
| --- | --- |
| Ask the owner which screen or program showed "strange output" | B (third-party tool) and C (label) vs everything else |
| `exiftool -BitsPerSample -Compression -BlackLevel -WhiteLevel -LinearizationTable -warning <H12 frame>` | file tags as section 2; any warning = damaged file (only path to the UI fallback) |
| `curl -sD- -o h12.jpg 'http://<cam>:8000/api/media/frame?kind=folder&id=<H12 clip>&n=0&w=640'` and the same for an H16 clip of one scene | WebUI picture and `X-Histogram` alike = file fine; owner's tool dark = H9-B |
| `printf '{"cmd":"get_state"}\n' \| socat - UNIX-CONNECT:/tmp/apertar-core.sock` -> `raw_bit_depth`, `clear_hdr`, `cdng_log` for the take | a "Clear HDR 12-bit" label on a 16-bit or SDR Log take = H9-C |
| Strange output on the live preview | H9 ruled out; go to the preview / ISP hypotheses |
