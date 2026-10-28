# R3: Apertar Core as the server for a WebUI playback

This is a reader report for the playback project. Patrik's brief is "port the playback function from cinemate, in the most Apertar like style". His decision of 2026-10-28 is "make the playback in web ui similar to the current touch ui".

This file covers **Apertar Core only**:

- what is on the card;
- what the DNG/MLV/H.264/ProRes writers put in the files;
- what the HTTP server can and cannot serve today;
- the CPU/IO budget and the interlocks;
- where a playback view would sit in the WebUI page.

It is a read of the code, not a design. Section 6 lists the gaps that follow from the read, each one labelled. No tree was edited.

## Sources and labels

| Prefix | File | Tree and commit |
| --- | --- | --- |
| `App` | `src/ApertarCoreApp.cpp` | Core, `scratchpad/controls/core-tip` @ `eb9cc39` |
| `App.hpp` | `src/ApertarCoreApp.hpp` | Core @ `eb9cc39` |
| `WS` | `src/web/WebServer.cpp` (`WS.hpp` for the header) | Core @ `eb9cc39` |
| `Web` | `src/web/WebControlPage.cpp` (the WebUI page) | Core @ `eb9cc39` |
| `CC` | `src/camera/CameraController.cpp` | Core @ `eb9cc39` |
| `Cdng` | `src/cdng/CdngEncoder.cpp` | Core @ `eb9cc39` |
| `Mlv` | `src/mlv/MlvEncoder.cpp` | Core @ `eb9cc39` |
| `core:` | any other path in Core | Core @ `eb9cc39` |
| `ui:` | Apertar touch UI, `scratchpad/controls/ui-tip` | `d8098d0` |
| `kb:` | `/home/user/apertar-kb` | `7fe621b` (HEAD and clean when read) |

The scratchpad is `/tmp/claude-0/-home-user-apertar-kb/17fc979d-f346-53ac-97ad-c8caa225a57d/scratchpad`.

Every `prefix:line` is at the commit in the table.

Each claim carries one of three labels:

- **[C] CONFIRMED**: I opened that line.
- **[P] PROBABLE**: derived from lines I opened. The derivation is given.
- **[U] UNCONFIRMED**: not checked in code. This includes browser behaviour and anything about the running Pi.

---

## 0. In one screen

- **Media root.** The default is `/media/RAW`. It is set by `--media`, and the start script passes `$APERTAR_MEDIA_ROOT`, defaulting to `/media/RAW`. [C] `App.hpp:35`; `core:src/main.cpp:33,60-62`; `core:scripts/start-apertar-core.sh:5,21`.
- **Clip folders.** Every take is a top-level folder, `<FMT>_<yy-mm-dd>_C<nnnn>`, and the files inside are named after the folder. [C] `CC:4169-4221`. The details are in §1.2.
- **Clip index.** Core already has one, but only over HTTP: `GET /api/media` returns a JSON list of folders, stills and audio. It rescans the card on every call. There is no index command on the socket. [C] `App:7307-7312`, `App:6422-6588`, `App:9634`.
  - It has nothing per file.
  - Its FPS is the camera's **current** setting, not the clip's.
  - Its duration is `--` for every container format.
  - [C] `App:6490-6493`, `App:7821-7824`.
- **Thumbnails.** No DNG that Core writes has one.
  - IFD0 is the raw image (NewSubFileType 0), and its next-IFD pointer is 0.
  - The IFD sits at the **end** of the file.
  - [C] `Cdng:1528-1529`, `Cdng:1387-1392`; `core:src/cdng/IfdBuilder.hpp:123`.
  - MLV, MP4 and MOV carry no thumbnail either. [C] §2.
- **The web server.** It is a hand-written HTTP/1.1 server:
  - one detached thread per connection, at most 32;
  - `Connection: close` and `Cache-Control: no-store` on every response;
  - **no Range, no HEAD, no ETag**;
  - streamed bodies carry no `Content-Length`.
  - [C] `WS:127-154`, `WS:253-293`; a grep finds no range code.
- **Downloads.** Core already serves media as downloads: one folder as a ZIP (`zip -0` through a fork) or one still. **No route serves one file from inside a clip folder.** [C] `App:7343-7462`.
- **Live preview.** It travels as MJPEG, `/preview.mjpeg`, at most 640×360, quality 75, at most 30 fps, and only while someone watches. [C] `App:62-65`, `App:7255-7268`, `App:8273-8486`.
  - The downscale runs **on libcamera's completion thread**. [C] `App:8281-8282`, `App:7136-7137`, `CC:7707`.
- **Core does not know when anyone plays a clip.**
  - The touch UI scans `/media/RAW` itself. [C] `ui:src/cliplistmodel.cpp:174`.
  - `record_start` from any source has no playback gate. [C] `App:9483-9508`.
  - The hardware record button records straight through Core. [C] `App:9056-9061`.
  - Downloads are allowed while recording. Deletes are not. [C] `App:7343` vs `App:7660-7666`.
- **The WebUI already has a "Clip Browser" overlay.** [C] `Web:2447-2449`, `Web:3979-4030`.
  - A folder button in the top bar opens it.
  - It has filters for Clips, Stills, Timelapse and Audio.
  - Each row offers Download and Delete.
  - It has no thumbnails and no player.
  - The web icon folder already ships `play`, `pause`, `next`, `previous` and `film` PNGs. They are byte-identical to the touch UI's and are unused by the page. [C] (a `cmp` of the icon files; a grep of `Web` for each icon finds nothing).
- **CPU budget.** With 4K Clear HDR 16-bit at 30 fps, the camera is already limited by memory contention on libcamera's thread.
  - Memory traffic alone (`dd` to tmpfs) costs frames.
  - Lossless cDNG at 25 fps is encoder-bound and drops frames.
  - Anything the server reads or decodes during a take competes for that budget.
  - [C] `kb:lessons/hardware-log.md:87,108,113,161-164`.

---

## 1. Media layout on disk

### 1.1 Media root and mount

- **Root.** `Options.mediaRoot` defaults to `/media/RAW`. [C] `App.hpp:35`. `CC::mediaRootPath` falls back to the same value when the option is empty. [C] `CC:923-927`.
- **Mounted?** `isMountedPath()` decides by reading `/proc/mounts`. [C] `App:2046-2061`. The media list uses it. [C] `App:7822`.
- **Alive?** The media watcher's snapshot says whether the medium answers (§4.5). The record gate uses that snapshot. [C] `App:9413-9440`.
- **The two can disagree.** The code's own comment: "the mount table keeps a pulled or dead medium listed". [C] `App:7874-7876`.

### 1.2 Folder and file names per format

All names use local time, `%y-%m-%d`, and a 4-digit counter running from 1 to 9999. A clip takes the first counter whose folder does not yet exist. [C] `CC:4169-4211`.

| Format (setting) | Folder (top level of the root) | Media file(s) inside | Source |
| --- | --- | --- | --- |
| cDNG uncompressed or lossless JPEG | `cDNG_26-10-28_C0001/` | `cDNG_26-10-28_C0001_000000000.dng` … (`<clip>_` + 9-digit frame index + `.dng`) | [C] `CC:4182`, `CC:4200-4208`, `CC:4214-4221`, `CC:3996-3998` |
| Lossy DNG 3:1 / 5:1 | `cDNG_3to1_…_C0001/` or `cDNG_5to1_…` | Same per-frame `.dng` naming | [C] `CC:4190-4192`; writer `core:src/lossydng/LossyDngEncoder.cpp:527` |
| MLV | `MLV_…_C0001/` | `MLV_…_C0001.MLV` (one file, **upper-case** extension) | [C] `CC:4184-4186`, `CC:3483`, `CC:3996-3997` |
| H.264 | `H264_…_C0001/` | `H264_…_C0001.mp4`. While recording it is `….mp4.writing`, renamed at stop. | [C] `CC:4187-4189`, `CC:4607-4610` |
| ProRes | `ProRes_…_C0001/` | `ProRes_…_C0001.mov` | [C] `CC:4193-4195`; `core:src/prores/ProresRecorder.cpp:59` |

**The frame index.** The frame number is the take's own counter. The DNG also carries it in `PageName` (tag 285), together with the clip name in `DocumentName`/`ImageDescription` (269/270). [C] `Cdng:1553-1558`.

- The index starts at 0 [P]: `frameIndex_ = 0` at take start, `CC:3447`. The point where it increments was not opened.
- Dropped frames leave gaps in the numbering [P]: the KB derives gaps from frame indices (`kb:lessons/hardware-log.md:165`).

### 1.3 Sidecars and temporary files in a clip folder

| File | When | Format | Source |
| --- | --- | --- | --- |
| `<clip>.wav` | Recording with audio on, any format | WAV or RF64, `fmt ` + `bext` + `iXML` + `data`; PCM, or IEEE float when the format is `float32`; WAVE_FORMAT_EXTENSIBLE above 2 channels | [C] `core:src/audio/AudioRecordingSession.cpp:249-251`, `:900-960` (chunk writes at 908, 912, 919, 939, 954, 960); formats `auto/s16/s24/s32/float32` at `core:src/audio/AudioSample.hpp:11-12` |
| `audio_capture.raw` | While recording; removed when the WAV is finalised | Raw PCM | [C] `AudioRecordingSession.cpp:249`, `:421-423` |
| `audio_capture.raw` left behind | Medium gone at stop: the WAV is not finalised | Raw PCM | [C] `AudioRecordingSession.cpp:414` |
| `<clip>.gcsv` | Gyro recording on | Gyroflow CSV | [C] `core:src/hardware/Mpu6050RecordingSession.cpp:1418-1421` |
| `<clip>_recovery.json` | ProRes, written and fsync'd at clip open | JSON: clip path, width, height, fps, fourcc, pix_fmt `yuv422p10le`, colour profile | [C] `core:src/prores/ProresEncoder.cpp:1249-1282`; name at `core:src/prores/ProresRepair.cpp:167-173` |
| `fps-ramp.txt` | **Not at this tip.** It belongs to the T31 speed-ramp work, which is not on `eb9cc39`. | — | [C] a grep for `ramp` in `core:src` finds no such file write (only `LossyJpeg12` and WebUI strings) |
| Per-clip metadata JSON | **None.** No writer creates one in a clip folder. | — | [C] a grep of `ofstream`/`fopen` in `core:src` lists only the WAV, the raw temp, the gyro files, the ProRes sidecar, presets and settings |

**Audio inside the containers.** There is none: MP4, MOV and MLV are video-only.

- The H.264 muxer creates one stream. [C] `core:src/video/LibavH264EncoderPlugin.cpp:124`.
- The ProRes muxer creates one stream. [C] `ProresEncoder.cpp:929`.
- The MLV header says `kAudioClassNone`. [C] `Mlv:1089`.
- So a player that wants sound must play `<clip>.wav` alongside the picture. [P] Follows from the three lines above.

### 1.4 Stills, timelapse and sound recorder

**Stills** go to `Photos/Still_<yy-mm-dd>_C<nnnn>.<ext>`. [C] `CC:956-998`.

- The extension is `.dng`, `.jpg`, `.png` or `.tif`.
- Bracketed shots add the suffix `_EVm1`, `_EV0`, `_EVp1`, `_BRm`, `_BR0` or `_BRp`. [C] `CC:945`.
- A DNG+JPEG still is two files with the same stem. [C] `CC:5781-5808`.

**Timelapse** goes to `Timelapse_<yy-mm-dd>_C<nnnn>/`, one file per shot, named `<folder>_<9-digit index>.<ext>`. [C] `CC:1000-1047`.

**Sound recorder** (WAV only) goes to `Audio/Audio_<yy-mm-dd>_C<nnnn>/Audio_…_C<nnnn>.wav`. [C] `App:1474-1509`, `App:8545-8566`, `AudioRecordingSession.cpp:250-251`.

### 1.5 How Core knows the clips: `GET /api/media`

**Route.** `GET /api/media` calls `buildMediaLibraryJson()`. That calls `discoverMediaLibraryItems(mediaRoot, settings.fps)` when `/proc/mounts` lists the root, and returns an empty list otherwise. [C] `App:7307-7312`, `App:7819-7855`.

**Response.**

```
{"ok":true, "mounted":bool, "media_root":"/media/RAW", "items":[
  {"id","kind","category","type","name","size_bytes","size_text","file_count",
   "frame_count","duration_text","fps_text","modified_text","modified_ms","download_url"} ...]}
```

[C] `App:7828-7853`; the struct is at `App:5609-5626`.

**Discovery rules.** [C] `App:6422-6588`

| Kind / category | What counts | `id` | `type` |
| --- | --- | --- | --- |
| `folder` / `clip` or `timelapse` | Any top-level folder except `Photos` and `Audio` that contains, anywhere below it (recursive), a still-image file (`.dng .jpg .jpeg .png .tif .tiff`) or a container (`.mp4 .m4v .mov .mlv`). `Timelapse_` prefix → timelapse. | folder name | `"Timelapse"`, else the container label (`"MLV Clip"`, `"ProRes Clip"` for a `prores_*.mov`, `"H.264 Clip"` for an `h264_*.mp4`, `"Video Clip"`), else `"cDNG Clip"` |
| `still` / `still` | Files in `Photos/` grouped by lower-cased stem | `Photos/<stem>` | `"DNG + JPEG Still"` etc. |
| `folder` / `audio` | Sub-folders of `Audio/` holding a `.wav` | `Audio/<folder>` | `"WAV Audio"` |

[C] Extension tests `App:5807-5836`; scan loop `App:6443-6497`; stills `App:6499-6536`; audio `App:6538-6580`; sort newest first `App:6582-6586`.

**Per-item numbers.**

- `size_bytes`, `file_count` and `frame_count`: a **recursive stat of every file** in the folder. `frame_count` counts still-image files. [C] `App:6055-6092`, `App:6487-6489`.
- `duration_text`:
  - cDNG: `frame_count / current fps`;
  - containers: `"--"`;
  - audio: parsed from the WAV header, RF64-aware.
  - [C] `App:6490-6492`, `App:5887-5905`, `App:5926-6006`, `App:6574`.
- `fps_text`: `compactNumber(fps)`, where `fps` is `camera_.settings().fps` **at request time**. It is not the clip's rate. [C] `App:6493`, `App:7821-7824`.
- `download_url`: `/api/media/download?kind=…&id=…`. [C] `App:6280-6283`.

**What this means for a playback list.** [P] Each point is derived from the rules above.

1. **Wrong FPS and duration.** A clip shot at 50 fps and listed while the camera is set to 25 shows "25 FPS" and twice its real duration.
2. **No container metadata.** MLV, H.264 and ProRes clips show `"--"` duration and a `file_count` instead of frames (`Web:7609-7620`).
3. **Takes in progress.**
   - A cDNG, MLV or ProRes take **is listed while it records**: the `.dng`, `.MLV` or `.mov` exist from the first write. Nothing marks it "recording".
   - An H.264 take is **invisible** until stop, because `.mp4.writing` matches no extension.
4. **Unplayable listed items.** A ProRes `.mov` has no `moov` until `av_write_trailer` (`ProresEncoder.cpp:1229-1236`). It is listed but cannot be played until stop. If the take was interrupted, it stays unplayable, because `prores_repair::repairAll` is declared and defined (`core:src/prores/ProresRepair.hpp:64`, `ProresRepair.cpp:359`) but **has no caller** in Core. [C] grep.
5. **A JPEG poster written into a clip folder would break the list.**
   - It would count as a frame.
   - The type scan stops at the first match (`App:6470-6471`), so an H.264 folder whose `.jpg` is iterated first would be labelled `"cDNG Clip"` with a frame-based duration.
   - A poster or thumbnail cache therefore needs a non-image extension, a location outside the scanned tree, or a skip rule like the ones for `Photos` and `Audio` (`App:6452`).
6. **Scan cost.** Every call walks every file of every clip: thousands of `stat`s for long cDNG takes, with no cache. The WebUI calls it when the browser opens, on Refresh, and after deletes (`Web:6182-6183`, `Web:11398`, `Web:10439`, `Web:10492`).

**No socket command lists media.** The `help` list has none. [C] `App:9634`. The touch UI does not use `/api/media`: its `ClipListModel` reads `/media/RAW` directly. [C] `ui:src/cliplistmodel.cpp:174`, `:450-457`.

---

## 2. The writers: what a player can read, and where a thumbnail could come from

### 2.1 cDNG layout (uncompressed, lossless JPEG, and lossy via the same encoder)

**File order.** [C] `Cdng:1384-1392`, `Cdng:1740-1777`

1. An 8-byte TIFF header (`II*\0` + IFD0 offset).
2. The payload at offset 8: either the uncompressed strip, or the lossless-JPEG tiles written first with `pwrite` of the header afterwards (`Cdng:1343-1351`, `1759-1767`).
3. Padding to 4 bytes.
4. **IFD0 plus the EXIF IFD at the tail**.

**IFD0.** [C] `Cdng:1522-1632`, `Cdng:1643-1653`; `IfdBuilder.hpp:113-154`

- `NewSubFileType` = 0 (full resolution). [C] `Cdng:1528-1529`
- Width, height, bits, compression 1 or 7.
- Photometric CFA (32803), or LinearRaw for mono (34892).
- Strip or tile tags, orientation, CFA pattern, black and white levels.
- Colour matrices, AsShotNeutral, DefaultCrop, BaselineExposure.
- CinemaDNG `TimeCodes` and `FrameRate`, `ReelName`, `CameraLabel`, `DateTime`.
- An EXIF IFD with ExposureTime, ISO and DateTimeOriginal.
- **No `SubIFDs` tag, no second IFD**: the next-IFD field is written as 0.

**Per-clip facts a player can read from any frame.** Without a sidecar, a server can get FPS, timecode, ISO, shutter, size and date for the clip info by reading the last few KB of the first DNG. [P] The tags above are all in IFD0/EXIF, and IFD0 is at the tail at the offset in bytes 4-7.

**Lossy DNG.** It is written by the same `CdngEncoder` into a memfd and then written out asynchronously. Same layout, compression 7, plus a `LinearizationTable`. [C] `core:src/lossydng/LossyDngEncoder.cpp:527`, `Cdng:1586-1588`.

**DNG stills.** They use the same `writeDngFile`, through an atomic temp file. A processed JPG, PNG or TIF is written **beside** the DNG only when the photo format asks for one. [C] `CC:5705-5729`, `CC:5781-5808`.

### 2.2 Could Core embed a thumbnail like cinepi-raw does?

**The reference: what cinepi-raw does.** R1 documents it in detail (see `scratchpad/playback/r1-cinemate-playback.md` §3).

- It chains a JPEG IFD1 (NewSubFileType 1, 640×360, quality 85) after IFD0.
- It points IFD0's next-IFD field at that IFD1 ("decision 7").
- Measured cost: +4.0 ms per frame (+18 %) at 4K Clear HDR 16-bit 25 fps, about 10-25 KB per frame.

**What Core already has for this.**

- **The lores/preview plane is in the same libcamera request as the raw frame.** Each request carries the preview, optional H.264 and raw buffers (`CC:7432-7434`). `requestComplete` publishes the preview frame (`CC:7707`), then hands the same request to `recordRawFrame` (`CC:7723`). [C]
  - The raw copy worker holds the request until its `memcpy` is done, and only then calls `releaseHeldRequest` (`CC:4088-4097`). [C]
  - So the matching preview buffer stays valid exactly as long as the raw copy needs. [P] A request is requeued only after release.
- **The preview stream size.** It is about 1280×720, bounded to the sensor aspect (`CC:1051-1052`, `CC:2952`), YUV420 in three planes (`CC:8396-8429`). [C]
- **A ready JPEG path from YUV planes.**
  - `encodeYuv420ToJpeg` uses TurboJPEG `tjCompressFromYUVPlanes` with `TJFLAG_FASTDCT`. [C] `App:4165-4214`
  - It has a libjpeg fallback. [C] `App:4216`
  - The nearest-neighbour planar downscaler is `downsampleNearestPlane`, with `scaledWebPreviewSize` to fit 640×360. [C] `App:4041-4055`
  - The CMake build defines `APERTARCORE_HAS_TURBOJPEG`/`HAS_JPEG`. [C] `core:CMakeLists.txt:120-130`
  - All of this lives in `ApertarCoreApp.cpp`'s anonymous namespace, not in `CC` or `cdng/`. [C] `App:4035-4230`

**What an embedded thumbnail would need.** [P] Each step is derived from the lines cited.

1. **Map the preview buffers in raw mode.** `CC` maps them only in "processed" mode (H.264/ProRes) (`CC:7279-7286`, `CC:7827-7884`). For cDNG and MLV it has no CPU pointer of its own; App maps them separately for the MJPEG (`App:8226-8271`).
2. **Make the thumbnail in the copy worker, not on the completion thread.**
   - The completion thread is the critical one (`kb:lessons/hardware-log.md:153-200`).
   - The copy worker already owns the request (`CC:4072-4117`).
   - A 640×360 nearest downscale reads about a quarter of a 1.4 MB plane.
3. **Carry the JPEG into the encoder.** That means a new `Metadata` field, for example a byte span (`core:src/cdng/CdngEncoder.hpp:24-85`).
4. **Write it after IFD0 and patch IFD0's next-IFD word.**
   - The word sits at `2 + 12·count` from the IFD0 start (`IfdBuilder.hpp:117-123`).
   - Uncompressed frames reuse a cached IFD0 template (`Cdng:1507-1520`, `1634-1738`), so the pointer must be patched per frame like the other patched fields.
   - Lossless rebuilds IFD0 every frame (`!lossless` in `templateMatches`, `Cdng:1508`).
5. **Lossy DNG** inherits the change through the shared encoder (`LossyDngEncoder.cpp:527`).
6. **MLV** has no thumbnail block in Core's writer (§2.4). A per-clip poster is the only cheap route there.

**Cost.** Core's version would likely cost **less than Cinemate's +4 ms**. [P] Core encodes straight from YUV planes with TurboJPEG FASTDCT, while cinepi-raw converts YUV to RGB first and uses libjpeg defaults (R1 §3.2 point 6). [U] Not measured on Core.

**Bandwidth.** The added bytes are about 0.1 % of a 16.6 MB frame. [P] 10-25 KB against 16,590,340 bytes (`kb:lessons/hardware-log.md:140`).

**The open risk.** Does Resolve or Adobe accept a chained IFD1 in Core's files? [U] It is not checked in Cinemate either (R1 §3.2, handbook open item).

**Cheaper alternatives.** [P] Each is derived from the code cited.

- **(a) One poster JPEG per clip** at record start or stop, from the latest preview frame. App already does exactly this conversion for every MJPEG frame (`App:8295-8366`, `App:8393-8400`).
  - Cost: one encode per take.
  - It must be stored where the media scan cannot mistake it for a frame (§1.5 point 5).
- **(b) On-demand server decode.** Core has **no** DNG reader, **no** lossless-JPEG decoder (`core:src/cdng/LosslessJpegEncoder.hpp` declares only an encoder; a grep for `decode` finds nothing) and no H.264/ProRes decoder.
  - The only raw-to-RGB code is the still path. It does a **full-resolution** bilinear demosaic from the in-memory camera buffer, not from a file (`CC:1607-1680`).
  - Uncompressed DNG and MLV could be subsampled from the file without a codec.
  - A 4K 16-bit frame is 16.6 MB. Reading every 4th row still touches about a quarter of it, roughly 4 MB per frame. [P] At 7680 bytes per row the rows are larger than a page.

### 2.3 What else a player needs to know about cDNG

- **Frame size.** 4K Clear HDR 16-bit uncompressed is 16,590,340 bytes per file. [C] `kb:lessons/hardware-log.md:140`. Serving raw DNGs to a browser for decoding is therefore impractical at frame rate. [P] 25 fps × 16.6 MB is 415 MB/s.
- **Frame rate.** The rate in the file is `FrameRate` (SRational), from `metadata.fps`. [C] `Cdng:1420-1422`, `Cdng:1627`.

### 2.4 MLV

**Blocks written.** [C] `Mlv:1077-1097`, `Mlv:1105-1290`, `Mlv:1020-1040`

- `MLVI`, with frame count, fps numerator and denominator, `kVideoClassRaw` and `kAudioClassNone`.
- `RTCI`, `INFO`, `VERS`, `IDNT`, `RAWI`, `EXPO`, `WBAL`.
- `DEBG` (the preview colour matrix).
- One `VIDF` per frame. The payload is the uncompressed raw frame (`metadata.compression = Uncompressed`, `CC:4002`).

**Header frame count.** It is written as the start value and **patched at close** (`Mlv:1066`, `Mlv:1293-1301`). [C] A clip that is in progress or was interrupted therefore reads 0 frames in the header. [P]

**Container shape.** Single file, no `.M00` chunks, no `.IDX` index. [C] The grep found no chunking or index code. [P] The file also has a single-file `fileCount` of 1 (`Mlv:1086`).

**Random access.** `WBAL` and `DEBG` blocks are re-emitted mid-clip when the white balance or the CCM changes (`Mlv:1013-1016`, `Mlv:1273`). [C] Frame N is therefore not at a fixed offset. A server needs one pass over the 8-byte block headers to build an index. [P]

**Who reads MLV today.** The touch UI has `MlvReader` (`ui:src/MlvReader.cpp`). Core has none. [C] Core has no MLV reader (only the encoder in `src/mlv/`).

### 2.5 H.264 (`.mp4`)

**Writers.** The in-process libav plugin uses `avformat_alloc_output_context2(…"mp4"…)`. The `pipe` backend runs ffmpeg with `-f mp4`. [C] `core:src/video/LibavH264EncoderPlugin.cpp:118`, `CC:4697-4750`.

**Encoder settings.** [C] `LibavH264EncoderPlugin.cpp:137-148`, `181-189`

- `yuv420p`, GOP = round(fps), no B-frames.
- Hardware `h264_v4l2m2m`: High profile, level 4.0, BT.709.
- Software: x264 `ultrafast`, CRF 22 by default.

**Size.** The default encode size is 2560×1440 (`CC:1053-1054`). The Pi 3/4 hardware encoder is capped at 1080p30 (`CC:4576-4580`). [C]

**Where the index sits.** Neither backend asks for `+faststart`. `avformat_write_header(…, nullptr)` gets no options (`LibavH264EncoderPlugin.cpp:374`), and no `movflags` appears anywhere. [C] So the `moov` index sits **at the end** of the file. [P] FFmpeg's MP4 muxer default.

**In a browser.** A browser `<video>` can play these files natively. [U] Browser codec support was not checked here. To start and seek without downloading the whole file, it needs HTTP Range (§3.4). [U]

### 2.6 ProRes (`.mov`)

- **Encoding.** 10-bit 4:2:2 (`yuv422p10le`), profile `apco`/`apcs`/`apcn`/`apch`. The `moov` is written at close. [C] `ProresEncoder.cpp:1229-1279`.
- **Index.** The `moov` is written at close and repair is not wired in (§1.5 point 4). [C]
- **In a browser.** Chrome and Firefox do not decode ProRes; Safari on macOS may. [U] Browser fact, not checked here. A WebUI player needs a server-side frame source for ProRes: a poster, or decoded frames. [P]

---

## 3. The web server

### 3.1 Thread model and limits (`WS`)

| Aspect | Value | Source |
| --- | --- | --- |
| Bind / port | `0.0.0.0:8000` by default; `--web-bind`, `--web-port` (0 disables) | [C] `App.hpp:36-37`; `core:src/main.cpp:34-35,64-80`; `WS:190` |
| Start script | Passes neither flag, so the defaults apply | [C] `start-apertar-core.sh:21`. How Core is launched on Patrik's Pi (unit file) is not in either tree [U] |
| Accept | One thread, `listen` backlog 16 | [C] `WS:220`, `WS:228` |
| Per connection | One **detached** `std::thread` per accepted socket; at most **32** live clients (the 33rd is closed at once) | [C] `WS:268-291`, `WS:271-272` |
| Socket timeouts | `SO_SNDTIMEO` and `SO_RCVTIMEO` of 5 s (comment: a dropped Wi-Fi viewer must not stay counted) | [C] `WS:263-267` |
| Request read | 10 s deadline; 1 MiB maximum (413); `Transfer-Encoding` → 400; one request per connection | [C] `WS:23`, `WS:304-354`, `WS:332`, `WS:345-348` |
| Keep-alive | None: every response says `Connection: close` | [C] `WS:133`, `WS:147` |
| Caching | Every response says `Cache-Control: no-store`, hard-coded before the handler's own headers | [C] `WS:134`, `WS:148` |
| Reason phrases | Only 200/204/400/403/404/405/413/500/503. Any other status prints "OK". | [C] `WS:59-73` |
| Shutdown | `stop()` shuts every client socket and waits for the handlers to exit | [C] `WS:232-251` |

**Locks.** The handler runs on the client's thread. Only `/api/command` takes Core's `commandMutex_`, inside `handleCommand`. File and list routes take no Core-wide lock. [C] `App:7231-7237`, `App:9485`.

### 3.2 Routes (all in `App::handleWebRequest`, `App:7239-7795`)

| Method and path | Response | Notes | Source |
| --- | --- | --- | --- |
| `OPTIONS *` | 204 | No CORS headers | [C] `App:7241-7246` |
| `GET /`, `/index.html` | `text/html`, the whole page from one raw string | — | [C] `App:7248-7253`; `Web:7`, `Web:11657` |
| `GET /preview.mjpeg` | `multipart/x-mixed-replace; boundary=frame`, streamed | 503 if built without JPEG | [C] `App:7255-7268` |
| `GET /icons/<name>` | `image/png` from the source tree's `src/web/icons` | Name checks: no `/`, `\`, `..` | [C] `App:7270-7298`, `App:2452-2473` |
| `GET /api/state` | JSON camera, system and UI state | Polled by the page every 1 s | [C] `App:7300-7305`; `Web:11652` |
| `GET /api/media` | JSON media list | §1.5 | [C] `App:7307-7312` |
| `GET/POST /api/config` | Hardware config file read and save | — | [C] `App:7314-7341` |
| `GET /api/media/download?kind=folder&id=…` | `application/zip`, streamed from `zip -r -0 -q -` (forked, cwd = the media root) | 503 without `/usr/bin/zip` | [C] `App:7358-7398`, `App:6350-6420` |
| `GET /api/media/download?kind=still&id=Photos/<stem>` | One file streamed with its MIME type, or a ZIP for a group | — | [C] `App:7400-7455`, `App:6285-6305` |
| `GET /api/media/download-selected?item=kind:id&…` | ZIP | — | [C] `App:7464-7504` |
| `GET /api/presets`, `/api/presets/download/<f>`; `POST /api/presets/import…`, `/save`, `/delete` | JSON | — | [C] `App:7506-7647` |
| `POST /api/media/delete`, `/api/media/delete-selected` | JSON | **Refused while recording, sound recording or timelapse** | [C] `App:7649-7781` (gate at `7660-7666`, `7732-7738`) |
| `POST /api/command` | JSON reply of `handleCommand` | §3.6 | [C] `App:7783-7788` |
| Anything else | 404 (GET/POST) or 405 | `HEAD` gets 405 | [C] `App:7790-7794` |

**Path safety for media IDs.**

- `isSafeMediaRelativeId` rejects absolute paths, `\`, NUL, `.` and `..`.
- `resolveMediaLibraryPath` and `pathIsInsideRoot` compare `weakly_canonical` paths.
- Stills are restricted to `Photos/<stem>`.
- [C] `App:5640-5655`, `App:5690-5709`, `App:5790-5805`, `App:6094-6141`.
- These are ready to reuse for a per-file route. [P]

### 3.3 Binary and streamed bodies

There are two body modes. [C] `WS:384-391`, `WS:127-154`

- **Buffered.** `response.body` is sent with a `Content-Length`. Icons and presets use it, read whole into memory with `readBinaryFileString` (`App:2475-2483`).
- **Streamed.** `response.streaming` plus a `streamWriter(fd)` callback. The header has **no `Content-Length`** and no chunked encoding: the body ends when the socket closes.

**File streaming.** It is an `std::ifstream` read in 64 KiB chunks, written with `send(MSG_NOSIGNAL)`. It has no `sendfile`, no `O_DIRECT`/`fadvise` and no rate limit, and it stops silently on any read or send failure. [C] `App:6319-6348`.

**Truncation is invisible.** With no `Content-Length`, a stream cut short by a pulled card or a 5 s send timeout looks to the browser like a complete, shorter file. [P] Follows from the header with no length and the silent stop.

### 3.4 Missing for media playback

Each item was checked by a grep of `WS` and `App` for `range`, `Accept-Ranges`, `Content-Range`, `206`, `ETag`, `Last-Modified`, `If-None-Match`, `sendfile` and `HEAD`, which found nothing. [C]

- **HTTP Range / 206 / 416.** Without them a `<video>` or `<audio>` element cannot seek or fetch a tail `moov`. [U] Browser behaviour. Also, a paused element stops reading, and Core's 5 s `SO_SNDTIMEO` then drops the connection (`WS:263-267`). Without Range, the browser cannot resume where it stopped. [P]
- **HEAD**, **ETag/Last-Modified/304**, and a way to **override `Cache-Control: no-store`**. Thumbnails would otherwise be fetched again on every view. [P] `WS:134` is written before the handler's headers, so a second `Cache-Control` header would conflict.
- **`Content-Length` on streamed files.** It is needed for progress and for spotting truncation.
- **A per-file route inside a clip folder** (a DNG frame, the WAV, the MP4/MOV/MLV). Today only whole folders (ZIP) and stills are served.
- **A per-clip detail route**: real FPS, resolution, codec, audio present, timecode, frame list, recording-in-progress.
- **Keep-alive.** Each request costs a TCP connect and a thread spawn. That is fine at a few requests per second. At Cinemate's one-JPEG-per-GET at 25 fps it is 25 thread spawns and connects per second. [P] Not measured on the Pi.

### 3.5 The MJPEG preview path

1. **Encoder thread.** One encoder thread starts with the web server, if it was compiled with JPEG. [C] `App:6969-6978`, `App:8372-8414`.
2. **Mapping.** Each preview slot is `mmap`ed once when it is registered. [C] `App:8226-8271`.
3. **Grab.** For each live frame, **only if `mjpegClientCount_ > 0`**, `captureWebPreviewFrame` does a nearest-neighbour downscale of the three planes to at most 640×360. It is limited to 30 fps. [C] `App:7097-7099`, `App:7136-7137`, `App:8273-8366`, `App:62-64`.
   - It runs on **libcamera's completion thread**. The code's own comment: "This runs on libcamera's completion thread." [C] `App:8281-8282`; called from `CC:7707` via the preview callback `App:6925`.
4. **Encode.** The encoder thread JPEG-encodes at quality 75 into `latestMjpegFrame_`. [C] `App:8393-8411`, `App:65`.
5. **Send.** Each viewer thread sends the newest frame as a multipart part (`--frame`, `Content-Type`, `Content-Length`), waiting up to 1 s per frame. [C] `App:8440-8486`.
6. **Standby.** The encoder stops and restarts on wake. [C] `App:9546-9547`, `App:9590-9596`. While it is stopped the page retries every 1.5 s. [C] `Web:8613-8617`.

**Consequence.** An open WebUI tab adds downscale work to libcamera's completion thread on every preview frame, up to 30 fps. During a take that thread is already the bottleneck (`kb:lessons/hardware-log.md:153-200`). [P] A playback view should therefore stop the live `<img>` stream while it is open, which is not done today (§5.2).

### 3.6 Auth, LAN exposure, CSRF

**No authentication.** Any host that can reach port 8000 can do all of the following, over Wi-Fi, hotspot or Ethernet: [C] `App:7239-7795` has no auth check; the dispatcher has no allowlist, `App:9483-11286`.

- list, download and delete media;
- edit the hardware config;
- run any command, including `format_media`, `restart_system`, `power_off_system` and `shutdown`.

**Cross-site guard.**

- A request whose `Sec-Fetch-Site` is `cross-site` is refused with 403.
- So is a request whose `Origin` is not `http://<Host>`.
- A request with no `Origin` is allowed (CLI and native clients).
- [C] `WS:156-170`, `WS:370-373`.
- A thumbnail `<img>` on another site's page would therefore be refused, while the camera's own page works. [P]

### 3.7 The `/api/command` dispatcher

**Body.** A **flat** JSON object: `{"cmd":"…","id":n,…}`. Values are strings or bare values, and `cmd` is required. [C] `core:src/ipc/ControlProtocol.cpp:164-233`.

**Reply.** It comes from `handleCommand`. [C] `App:7231-7237`, `App:7783-7788`.

- The HTTP status is always 200; errors are `{"ok":false,"error":…}`.
- Events raised during the command are **not** returned to the web caller. The socket path appends them (`App:7201-7229`).

**Locking and gates.**

- `handleCommand` takes `commandMutex_` for the whole command. [C] `App:9485`
- Common gates: media writes pending (`App:9487-9489`), the media gate (`App:9490-9494`), media actions while recording (`App:9495-9504`), the speed test (`App:9505-9507`), capture in standby (`App:9605-9608`). [C]
- `user_activity`, `wake`, any `set_*`, `capture_photo`, `record_*` and `timelapse_*` refresh the standby idle timer. [C] `App:9508-9516`
- No command concerns playback, clips or thumbnails. [C] `App:9634`

**Events.** They go only to Unix-socket clients (`controlServer_.broadcast`). The web has no push channel (no SSE or WebSocket) and polls instead. [C] `App:11289-11320`; `Web:11652`.

---

## 4. CPU/IO budget, interlocks, standby, media watcher

### 4.1 Budget during recording (measured, KB)

Pi 5 (4 GB), IMX585, 4K Clear HDR 16-bit, exFAT on NVMe:

- **Uncompressed 25 fps**: clean. **Lossless JPEG 25 fps**: queue full, 20-35 % lost. The lossless encoder tops out near 18 fps. [C] `kb:lessons/hardware-log.md:93-95,108-113`.
- **30 fps, uncompressed**: ~26 fps delivered.
  - libcamera's CameraManager thread is 54 % busy, IPC 1.87 → 1.30.
  - Cores are at 59/44/48/38 %, and five other Core threads at 18-20 % each.
  - [C] `kb:lessons/hardware-log.md:158-165`
- The limit is libcamera's single event thread, slowed by memory contention. [C] `kb:lessons/hardware-log.md:177-200`
- "Memory traffic alone (dd to tmpfs, no NVMe) costs frames." [C] `kb:lessons/hardware-log.md:87`

**For playback.** During a take, anything that reads the card heavily or decodes video on the Pi takes from the same memory budget as the take. That covers serving DNGs or MLV frames, transcoding, and ZIP downloads, which are allowed while recording. [P] The rule above plus §4.3. Cinemate answers frame and WAV requests with 409 while recording (R1 §0). Core has no such rule yet.

**The idle WebUI's own load.** [C] `App:2818-2836`, `App:2298-2320`, `App:2086`.

- `/api/state` is polled every 1 s per open tab.
- It runs `arecord -l` and `aplay -l` (cached 2 s), `lsblk` (cached 3 s) and an uncached `lsblk -no LABEL` for the mounted device.
- The per-poll fork cost during a take is not measured. [U]

### 4.2 Outside recording

- **Preview only.** CameraManager is 41 % busy at 30 fps. [C] `kb:lessons/hardware-log.md:161`.
- **The rest.** The MJPEG encoder idles unless a viewer is connected (§3.5).
- **Headroom.** There is spare CPU for serving thumbnails or JPEG frames. [P] With no take, the preview pipeline is the main load. [U] Not measured for a playback load.

### 4.3 Record/playback interlocks today

- **Core has no notion of playback.** No state, command or event mentions it. [C] A grep of `App` and `CC` for "playback" finds only ALSA device parsing (`App:2522-2688`).
- **The touch UI's player is invisible to Core.**
  - It reads files directly (`ui:src/cliplistmodel.cpp:174`).
  - It sends only a throttled `user_activity` on touches (`ui:src/SleepManager.cpp:201-205`, `ui:src/ApertarControlBridge.cpp:1190-1194`).
  - [C]
- **The `clip_browser` hardware action.** Core only publishes it as an event for the UI to open its browser. [C] `App:9142-9145`.
- **Recording can start at any moment.**
  - The WebUI record button, the touch UI and the GPIO `record_toggle` all reach `handleCommand("record_start")`. [C] `App:9056-9061`.
  - Its gates are media-related only (§3.7).
  - A playback design must therefore assume a take can begin mid-playback, and must stop or refuse its own media reads then. [P]
- **Existing media gates.**
  - Deletes are refused while recording, sound recording or timelapse. [C] `App:7660-7666`.
  - Downloads (ZIP and stills) are **not** gated. [C] `App:7343-7504`.
- **Signals a playback endpoint can check.** All are available without the command mutex: [C] `App:7863-7865`, `App:7995-8015`, `App:9399-9408`.
  - `camera_.isRecording()`
  - `soundRecordingActive()`
  - `camera_.timelapseActive()`
  - `camera_.mediaWriteStatus().pending`
  - `mediaSnapshot()`
- **The same signals in `/api/state`.** `state`, `recording`, `sound_recording`, `timelapse_active`, `media_writes_pending`, `media_mounted`, `media_state` and `media_alive`. [C] `App:7995`, `8000`, `8008`, `8009`, `8015`, `8069-8071`.

### 4.4 Standby

**The idle timer.** It is checked once a second in `wait()`. When the configured timeout passes with the camera `Ready` and no activity, Core issues `enter_standby`. [C] `App:7167-7199`.

- Recording, timelapse and sound recording keep resetting it.
- "Activity" means only the commands in §3.7. **`get_state` and file downloads do not count.** [C] `App:9508-9514`.
- The WebUI sends `user_activity` on `pointerdown` and `keydown`, throttled to 1 s. [C] `Web:11546-11559`.
- A WebUI playback that runs untouched longer than the timeout would therefore let the camera drop into standby mid-playback. [P] Follows from the lines above. The touch UI is in the same position whenever no touch happens. [P]

**What standby stops and keeps.** [C] `App:9535-9570`; helper `ui:src/StandbyLowPower.cpp:44-66`

- It stops the preview publisher and the MJPEG encoder.
- It runs `apertar-standby-low-power all`: the CPU governor goes to powersave, NVMe runtime PM to `auto`, and Bluetooth is rfkilled.
- It optionally cuts USB power.
- **The web server keeps running.** Files can still be served in standby, but slower, and the NVMe has to resume. [P] From the governor and runtime-PM settings.

**Wake.** `wake` restores everything. [C] `App:9571-9604`.

### 4.5 Media watcher and a pulled card during playback

**The watcher thread.** [C] `App:9299-9386`

- Every 1 s (250 ms while recording) it asks two questions:
  - Is the root a mount in `/proc/mounts`?
  - Does `statvfs`/the device probe answer?
- With the CFexpress HAT it also reads card presence.
- It publishes a `media` event on change.
- It aborts a take on loss.
- It stores the snapshot (`state`, `mounted()`, device, fstype, free/total, errno).

**Where the web sees it.** Through `/api/state` (`media_state`, `media_alive`), so within about 1-2 s of the change. [C] `App:8070-8071`. [P] 1 s watcher period plus a 1 s page poll.

**Gaps during playback.**

1. **The list endpoint trusts the mount table.** `/api/media` uses `isMountedPath` (the mount table), not the watcher. On a yanked drive that is still listed, it walks a dead filesystem. [C] `App:7822` and the comment at `App:7874-7876`.
2. **A dead NVMe can block reads.** NVMe is declared dead only after the controller's I/O timeout, 30-60 s. [C] `kb:working/yank-answer.md:70`. Until then, reads from a pulled NVMe can block the serving thread. [P] Same mechanism as the writers stuck in `write()` (`CC:3610-3615`).
3. **Truncated streams look complete** (§3.3).

**Recommendation.** [P] A playback route should check `mediaSnapshot().mounted()` first and answer 503 or 409 otherwise, which is what the record gate already does with the same snapshot (`App:9413-9431`).

---

## 5. The WebUI page (`Web`)

### 5.1 How the page is built

- **One raw string.** The whole page is a single C++ raw string literal, `R"APERTAR( … )APERTAR"`, from line 7 to line 11657: HTML, inline `<style>` and inline `<script>`. No external JS or CSS; icons come from `/icons/`. [C] `Web:5-11660`.
- **Layout.** [C] `Web:2423-2728`
  - **Top bar**: brand, date and time, status pill, **folder button `mediaBrowserButton` ("Open clip browser")**, settings button. [C] `Web:2424-2454`
  - **Main grid, left column**:
    - preview card: `<img id="previewStream">` + `<canvas id="previewProcessedCanvas">`, SMPTE bars, false-colour legend, grid, badges, centre overlay, timecode, record button;
    - "Camera settings" card.
    - [C] `Web:2456-2593`
  - **Main grid, right column**: System telemetry cards and "Current capture". [C] `Web:2595-2727`
- **Settings overlay.** `#settingsOverlay`: a sidebar `nav` of `data-panel` buttons (Favorites, Monitoring, Record, Audio, Media (`data-panel="power"`), System, Presets, Config, Info) and `settings-panel` sections. [C] `Web:2731-2783`, `Web:2796ff`.
  - Titles and copy live in `settingsPanelMeta`. [C] `Web:4165-4180`
  - `setSettingsPanel` toggles the `active` class. [C] `Web:6186-6198`
- **Clip Browser overlay.** `#mediaBrowserOverlay`, a fixed full-screen blurred overlay with a 900×760 rounded "shell". [C] `Web:3979-4030`, CSS `Web:1122-1160`.
  - Only one overlay is open at a time: opening one closes the other. [C] `Web:6167-6184`
  - It closes on backdrop click or Escape. [C] `Web:11610-11623`
- **Page state.** One `state` object (`mediaBrowserOpen`, `mediaLibrary`, `mediaBrowserFilter` "clip", `mediaBrowserSort` "newest", …). [C] `Web:4233-4245`.
- **Server calls.**
  - `sendCommand(payload)` POSTs to `/api/command` with an optimistic snapshot patch and a re-fetch. [C] `Web:9148-9183`
  - `fetchState` polls every 1 s. [C] `Web:10249`, `Web:11652`

### 5.2 The existing Clip Browser (the natural home for playback)

**Header.** Title **"Clip Browser"**; copy "Download or delete clips, stills, timelapses, and audio recordings from mounted media."; a Back button. [C] `Web:3988-3995`.

**Toolbar.**

- Filter buttons **Clips / Stills / Timelapse / Audio** (`data-media-filter`).
- Count pill.
- "Refresh Media".
- Sort "Newest First / Oldest First".
- Selection bar: Select All / Clear / Download Selected / Delete Selected.
- [C] `Web:3998-4024`

**Rows.** `renderMediaLibrary` builds one `.media-row` per item. [C] `Web:7707-7831`; row CSS `Web:1341-1365`.

- Row contents: select control, type chip, name, "Updated …", stat chips (frames or files, "Duration …", FPS, size), and **Download** (`<a download>`) and **Delete** buttons.
- **No thumbnail and no click-to-play.** Clicking a row toggles selection. [C] `Web:7750-7754`

**Loading.** The list is fetched on open and on Refresh, and the fetch is not repeated while one is in flight. [C] `Web:6182-6183`, `Web:10403-10420`.

**The live preview keeps streaming** behind the open browser. `setMediaBrowserOpen` does not touch `#previewStream`. [C] `Web:6176-6184`. While the overlay is open, Core's MJPEG work (§3.5) and one browser connection stay in use. [P]

### 5.3 Picture elements the page already has

- **`<img id="previewStream">`**, fed by `/preview.mjpeg?stream=<nonce>`, with retry on error. [C] `Web:2460`, `Web:8597-8622`.
- **`<canvas id="previewProcessedCanvas">`** with a WebGL path for false colour, zebra, grayscale and focus peaking, drawn from the `<img>`. [C] `Web:2461`, `Web:7903-7915`, `Web:8434-8470`.
  - It could post-process playback frames in the same way if a playback `<img>` fed it. [P]
- **No `<video>` and no `<audio>` element** anywhere in the page. [C] A grep of `Web` for `<video` and `<audio` finds nothing.
- **Unused icons.** `/icons/play.png`, `pause.png`, `next.png`, `previous.png` and `film.png` exist in `core:src/web/icons/`. They are identical to the touch UI's `ui:qml/icons/*.png` (`cmp`). The page does not use them. [C]

### 5.4 Where a Playback view would go

This is derived; it is not in the code. [P]

- **Inside the Clip Browser overlay, not under Settings.**
  - The WebUI already mirrors the touch UI's entry point: a folder button on the camera screen opens a "Clip Browser" (`Web:2447`, `ui:qml/ClipBrowserButton.qml`).
  - Patrik asked for the touch UI's flow (R2).
  - Cinemate's Playback is a settings-editor tab (R1 §1.1), which is the arrangement Patrik did not ask for.
- **Shape.**
  - The browser rows gain a thumbnail and open a player view when clicked.
  - The player view replaces the list inside the same shell, or sits in a sibling overlay at a higher z-index.
  - Back returns to the list.
  - Selection keeps working through the existing select control.
- **Opening the player should**:
  - stop `#previewStream` by setting an empty `src`, and restart it on close;
  - send `user_activity` while playing (§4.4);
  - watch `recording` / `media_alive` in the 1 s poll, to stop playback when a take starts or the card goes.

---

## 6. Gaps and cheap additions, server side

Each item is **[P]**, derived from the sections cited. None of them is a design decision.

| # | Gap at `eb9cc39` | Evidence | Smallest Core-side change that would close it |
| --- | --- | --- | --- |
| G1 | No per-file media route (frame, WAV, MP4, MOV, MLV) | §3.2 | `GET /api/media/file?id=<clip>/<file>`, reusing `isSafeMediaRelativeId`, `resolveMediaLibraryPath` and `mediaContentTypeForFile`. The MIME map lacks `.mlv` (`App:6285-6305`). |
| G2 | No Range, HEAD, length or cache control | §3.3-3.4 | Parse `Range` in the route and answer 206 with `Content-Range` and `Content-Length`, reading with `pread`. Add 206/304/409/416 to `reasonPhrase` (`WS:59-73`). Make `Cache-Control` overridable (`WS:134`). |
| G3 | No thumbnails in any file | §2.1-2.2, §2.4-2.6 | (a) JPEG IFD1 per DNG frame, made in the copy worker from the same request's preview plane (Cinemate's model); or (b) one poster JPEG per take from the preview stream, stored outside the scanned tree. MLV, H.264 and ProRes have only (b) or server decode. |
| G4 | The list's FPS and duration are wrong or missing per clip; no codec, resolution or audio info; takes in progress are not flagged | §1.5 | Read IFD0 of the first DNG (tail), the MLVI/RAWI header, the ProRes `_recovery.json`, and MP4/MOV `moov`. Flag the active take: Core knows it (`DngRecordingQueue::folderPath()`, `CC:4015-4018`) but does not expose it. |
| G5 | No playback/record interlock | §4.3 | New playback routes answer 409 while recording, sound recording, timelapse or media writes are pending, as Cinemate does. Whether to gate downloads too is Patrik's call. |
| G6 | Standby during passive viewing | §4.4 | The page sends `user_activity` while playing, or the playback routes count as activity. |
| G7 | Pulled card mid-playback | §4.5 | Check `mediaSnapshot()` before serving; use the watcher instead of `/proc/mounts` for `/api/media`; always send a `Content-Length`. |
| G8 | MJPEG work on libcamera's thread while a viewer is open | §3.5 | The page stops the preview stream while the player is open. A Core-side option would move the downscale off the completion thread (out of scope here). |
| G9 | ProRes interrupted takes stay unplayable | §1.5 point 4 | Call `prores_repair::repairAll(mediaRoot)` at start; the sidecar comment already promises it (`ProresEncoder.cpp:1275`). |
| G10 | MLV random access | §2.4 | Build the frame-offset index once per clip by walking the block headers, and cache it in memory. |

---

## 7. Not verified here

- **Browsers.** How Chrome, Firefox and Safari handle Core's MP4 (moov at end) without Range, RF64 WAV, 24-bit or float WAV, and ProRes MOV. [U]
- **Thumbnail cost on Core.** The real per-frame cost of a TurboJPEG thumbnail from the preview plane, on the Pi during a 4K take. [U]
- **The preview buffers' memory type.** Whether they are CPU-cached, which affects the cost of reading them in the copy worker. The App already reads them for MJPEG at up to 30 fps. [U]
- **Reader tolerance.** Whether Resolve or Adobe accept a chained JPEG IFD1 in Core's DNGs. [U]
- **How Core is started on the Pi.** No systemd unit for Core is in either tree, so whether `--web-port` or `--web-bind` are set is unknown. [U]
- **The touch UI side.** Its per-clip info, how it decodes frames, and its own guards are in R2 (`scratchpad/playback/r2-apertar-ui-player.md`), not repeated here.
