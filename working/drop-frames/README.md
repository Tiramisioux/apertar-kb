# Project: fewer dropped frames in Apertar, and CineMate Log for Apertar

Started 2026-10-29 from a cloud session that read all four repositories. Sources: `Apertar-Core`
`cinemate-port` @ `7678cbf`, `cinemate` `main` @ `4990afc` (full history, 2192 commits), `cinepi-raw`
`main` @ `63a08d5`, `cinemate-handbook` @ `c99ff77`, plus this KB's `working/compare-raw/`,
`working/clearhdr-compare-answer.md` and `lessons/hardware-log.md` 2026-10-26/27.

Status words as in the rest of the KB: **confirmed** (read in the source or measured on the Pi),
**probable** (inferred, reason given), **unconfirmed** (the command that settles it is named).

The handoff for the Mac session that drives the work is `../handoff-drop-frames.md`.

## 1. The question

Patrik sees more dropped frames with Apertar than with CineMate on the same kind of rig (Pi 5,
IMX585, 4K 25 fps, 16-bit Clear HDR, exFAT on a CFexpress card or NVMe). Why, and what to port.

A frame is lost in Apertar at one of four counted places. The first thing every measurement must
do is say **which counter moved**; the remedies differ.

| Counter (stderr line) | Where | Meaning |
| --- | --- | --- |
| `drop[queue-full]` | `DngRecordingQueue::enqueue` / `hasCapacityForFrame` | the write queue held `maxQueuedFrames_` frames (12 by default): the disk fell behind for more than ~0.5 s |
| `drop[copy-slot]` | `DngRecordingQueue::enqueueCopy` | the copy worker still held `buffers-2` requests: a slow memcpy or a stalled enqueue |
| `drop[capture-gap]` | `CameraSession` cadence tracker | libcamera delivered no frame for a period: the CFE skipped (writeback contention, pipeline-thread stall) |
| `drop[requeue-failed]` | `CameraSession` | a request could not go back to the camera |

`working/tools/takes.sh` prints missing frames, the queue peak and delivery per take; the journal
carries the lines above.

## 2. What the two stacks do differently (confirmed from source)

| Stage | Apertar `cinemate-port` @ `7678cbf` | cinepi-raw @ `63a08d5` + cinemate @ `4990afc` |
| --- | --- | --- |
| Backlog policy | write queue bounded in **frames**: 12 (ext4/exFAT profile), 24 for compressed formats, env `APERTAR_CDNG_QUEUE_FRAMES` max 64; when full the frame is **dropped** (`src/camera/CameraController.cpp` anchor `defaultQueueFrames`, `drop[queue-full]`) | encode threads **block** on a RAM permit sized at 90 % of `MemAvailable` at take start (`cinepi/dng_encoder.cpp` anchors `RAM_FRACTION = 0.90`, `ram_cv_.wait`); the capture loop only ends the take when the pool is gone (`cinepi/cinepi_raw.cpp` anchor `RAM pool exhausted`). 173 frames ≈ 2.9 GB on a 4 GB CM5 (`handbook hardware-log 2026-08-27/28`) |
| Cushion at 4K25 16-bit (16.9 MB/frame) | ~0.5 s (12 frames, 203 MB) | ~7 s on 4 GB, ~12 s on 8 GB |
| Sync during the take | `sync_file_range` per DNG (`startWriteback`, `APERTAR_DNG_WRITEBACK` default on); once a second `fsync` of every DNG finished in that second, then the clip folder (`syncLoop`, `APERTAR_MEDIA_SYNC_MS` default 1000); `syncfs` at stop | none. `open`, `write`, `close`, `posix_fadvise(SEQUENTIAL)` (`diskThread`, anchor `Use standard buffered IO instead of O_DIRECT`); `fadvise(DONTNEED)` was removed in `b71ec67` (2026-03-06) |
| Kernel knobs at mount | ported helper `scripts/apertar-media-tune` (dirty_bytes cushion, scheduler none, nr_requests, rq_affinity, NVMe APST 0) but **opt-in**: `APERTAR_MEDIA_TUNE=1` (`e9dd6b2`) | `services/storage-automount/storage-automount.py`: per connection class `dirty_bytes` 256 MiB–1 GiB, `dirty_background_bytes` 128–256 MiB, `dirty_writeback_centisecs` 150, scheduler none, `nr_requests` 256–512, `rq_affinity` 2, `nvme_core.default_ps_max_latency_us` 0; **default on** for `/media/RAW` |
| Process scheduling | callback thread `setpriority(-5)` under `LimitNICE=-5`; everything else nice 0, no affinity, no ionice | whole `cinepi-raw` process `chrt -f 70`, `ionice -c2 -n0`, `taskset -c 1-3` (`src/module/cinepi_multi.py` `run()`), allowed by `LimitRTPRIO=80` on the unit and `@audio - rtprio 80` in `limits.d`; installer adds `isolcpus=managed_irq,domain,N nohz_full=N rcu_nocbs=N irqaffinity=0..N-1` for the audio core |
| Worker nice | n/a | `--encode-nice -10 --disk-nice -5` **fail** with `Permission denied` on every take (handbook `open-threads.md` "DNG disk workers cannot set their nice level"): contributes nothing |
| Raw camera buffers | 4 SDR, 8 Clear HDR (+2 for FAT/NTFS profiles, 0 for exFAT/ext4), env `APERTAR_RAW_CAMERA_BUFFERS`; held by workers ≤ buffers-2 | `--buffer-count` 8 (ext4/default) or 10 (exFAT/NTFS) from `storage_profiles.py` |
| Buffer cacheability | CPU-cached heap only for Clear HDR unpacked and PiSP COMP1 (`allocateCachedBuffers`, anchor `settings_.clearHdr && rawStreamInfo_.packing == PixelPacking::Unpacked`); SDR raw reads uncached | libcamera default allocation; the DNG is assembled straight from the camera buffer on an encode worker |
| Copies per frame | 1 memcpy on the copy worker (+ a LUT pass in 12-bit Clear HDR), then the writer's row chunks | 1 (camera buffer → pooled TIFF block on the encode worker), then `write()` |
| Per-frame syscalls | ~40 (`write` per 491 520-byte chunk, header, pad, IFD, 2 fadvise, open, close) + `sync_file_range` | ~5 (open, fadvise, one `write`, close) |
| Bytes per frame, 4K 16-bit Clear HDR | 16.9 MB (16-bit) or 12-bit with a LinearizationTable (`57c8fb0`) | 16.9 MB linear, **or 12.7 MB with CineMate Log** (`--log-encode 12`), or 10.6 MB (`10`) |

### What is already measured on this Pi (hardware-log 2026-10-26/27)

- The once-a-second **`syncfs`** cost 12 capture gaps in 3 min; **per-file `fsync` + folder fsync**
  measured **clean** for 3 min at 38 % full (`cDNG_26-10-27_C0002`, 4494 frames, 0 missing).
- A **77–81 % full** card lost 166–676 frames to `queue-full` in 3 min; a fresh format fixed it
  (**probable**: the card's write cache shrinks as it fills).
- T22: dirty-page tuning alone did not remove Clear HDR gaps (those gaps were the uncached-buffer
  problem fixed by `94ac68d`).
- `e9dd6b2`: 16-bit 4K25 ran clean without the media helper, which is why it became opt-in.

So the fsync is not the proven cause on an empty card. It is the first thing to remove **if the
A/B says so**, and Patrik has agreed to lose it. The unanswered question is where today's drops are
counted; the plan starts there.

### Confounders (check before comparing numbers)

1. **Bytes per frame.** If CineMate runs with LOG on, it writes 12.7 MB per 16-bit frame; Apertar
   writes 16.9 MB. Compare at the same stored depth, or port log first (§4).
2. **Card fill.** Both stacks slow down on a nearly full card; compare at the same fill.
3. **Clear HDR 16-bit soaks stalled on CineMate too** (handbook 2026-08-27/28, NTFS via FUSE, ~355 MB/s):
   its advantage is burst absorption, not a faster disk.
4. **Thumbnail.** cinepi-raw writes a 691 KB IFD1 thumbnail per frame by default; Apertar none.

## 3. Remedy plan for Apertar (in order)

Step 0 needs no code. Each later item is one commit, A/B-able by its env knob so the knob matrix
stays usable for regression tests.

| # | Change | Where | Env for A/B | Expect |
| --- | --- | --- | --- | --- |
| 0 | **A/B soak matrix**: 10-min takes, 4K25 16-bit, same card at < 50 % full, one knob per run, count the four `drop[...]` lines | Pi, no build | `APERTAR_MEDIA_SYNC_MS=0`, `APERTAR_DNG_WRITEBACK=0`, `APERTAR_CDNG_QUEUE_FRAMES=64`, `APERTAR_RAW_CAMERA_BUFFERS=10`, `APERTAR_MEDIA_TUNE=1` (needs the sudoers + libexec install) | tells which counter moves and which knob stops it |
| 1 | **RAM-bounded queue, block instead of drop.** Budget = a fraction of `MemAvailable` at take start (cinepi-raw uses 0.9; start at 0.6 and keep 512 MiB free), in bytes, not frames. Copy worker **waits** while the budget is full; drop only at the copy-slot cap; a pool-exhausted stop ends the take like cinepi-raw. Expose `queue_bytes`/`queue_budget_bytes` in `get_state` for a buffer bar | `DngRecordingQueue` (`maxQueuedFrames_`, `enqueue`, `hasCapacityForFrame`, `copyLoop`, `acquireRawBuffer` pool) | `APERTAR_CDNG_QUEUE_RAM_FRACTION`, `APERTAR_CDNG_QUEUE_FRAMES` kept as a ceiling | queue-full drops become seconds of cushion |
| 2 | **No sync during the take by default.** `APERTAR_MEDIA_SYNC_MS` default 0, `APERTAR_DNG_WRITEBACK` default off; keep the stop-time `syncfs`; keep the audio raw fsync | `DngRecordingQueue::start`, `startWritebackPerFrame`, `syncLoop` | the same two knobs | fewer capture gaps if writeback bursts were the cause; a pulled card loses up to `dirty_expire` |
| 3 | **Media tuning on by default** (the e9dd6b2 objection was the 1 s bound, gone with #2). Installer step for `/usr/local/libexec/apertar-media-tune`, `/etc/sudoers.d/apertar-media`, tmpfiles | `ApertarCoreApp::applyMediaTuning`, `scripts/`, `config/` | `APERTAR_MEDIA_TUNE=0` to disable | bounded dirty pages, NVMe APST off on the CFE, scheduler none |
| 4 | **Cached buffers for SDR raw, 8 of them.** Extend the cached-heap condition to unpacked SDR; `kConfiguredBufferCount` 4 → 8; keep +2 for FAT/NTFS | `allocateCachedBuffers` call site, `rawCameraBufferCount` | `APERTAR_RAW_CACHED_DMABUF`, `APERTAR_RAW_CAMERA_BUFFERS` | copy-slot drops in SDR disappear; CMA use +4 × 16.9 MB |
| 5 | **Scheduling parity.** `LimitRTPRIO=80` on `apertar-core.service`; start script prefix `chrt -f 70 ionice -c2 -n0 taskset -c 1-3` behind `APERTAR_RT=1`; fallback: SCHED_FIFO on the completion and copy threads only | `scripts/start-apertar-core.sh`, `config/` drop-in, `CameraSession::requestComplete` | `APERTAR_RT` | capture thread no longer waits behind writers and the WebUI |
| 6 | **CineMate Log for Apertar** (§4): 20–25 % fewer bytes per frame at the same picture, in parallel with every compression | encoder + format model + UIs | setting, not env | the same card carries 25 fps with margin |

Not worth doing: worker nice levels (CineMate's fail silently); O_DIRECT (T24 skipped, neither
stack ships it).

### Done means

Ten-minute 4K25 16-bit uncompressed take on a < 50 % full card: 0 in every `drop[...]` counter,
queue peak < 25 % of budget, stop `syncfs` < 200 ms; the same with lossless JPEG and with Log 12;
SDR 12-bit at 50 fps unchanged; a pulled card still ends the take as `media_removed` (T28).

## 4. CineMate Log for Apertar: the design

### What it is (cinepi-raw, confirmed)

A per-sample LUT applied before packing: mu-law companding of the signal above black plus a short
linear footroom below black, into `target_bits` codes; the inverse table is written as the DNG
`LinearizationTable` (tag `0xC618`), `BlackLevel`/`WhiteLevel` stay in the linear domain, so any
DNG reader decodes to linear with no LUT. `cinepi/log_lut.hpp` (BSD-2-Clause) is the whole curve;
specs per depth pair ship as JSON with the generator's own table and are cross-checked at load.
A companded 12-bit Clear HDR source is **decompanded first** and then log-encoded with the 16-bit
spec (`build_ccmp_composed`), never with the 12-bit one. Operator model in cinemate
`docs/cinemate-log.md`: Off / On (mode default: 16→12, 12→10) / Force 10 / Force 12; a LOG button
in the Web GUI; a per-camera setting; CineMate has no lossy mode, so it never had to combine them.

Patrik's rule for Apertar: **one step down**: 16 → 12, 12 → 10, 10 → 8, with an explicit target
allowed when it is below the source depth.

### What Apertar already has (confirmed, `cinemate-port` @ `7678cbf`)

- `CdngEncoder::Metadata::linearizationTable` (span of `uint16_t`, must be `2^bitDepth` long) and
  tag `0xC618` emission; `WhiteLevel` from the table's last entry (`src/cdng/CdngEncoder.cpp`,
  anchors `metadata.linearizationTable`, `0xC618`).
- A 65 536-entry forward LUT pass on the **copy worker** for 12-bit Clear HDR
  (`compressClearHdrFrame`, `src/cdng/ClearHdrCcmp.hpp` `compressionLut()`), i.e. exactly the hot
  path a log encode needs; the CCMP expansion table for the composed case.
- Row packers for 8/10/12/16-bit storage (`writeDngRowBytes`, `RawBitDepth`), and the lossy
  path's companding (`src/lossydng/LossyDngEncoder.cpp` `buildCompanding`: square-root curve +
  quantisation + SOF3), which is where the log curve plugs in for Lossy + Log.
- Sensor black level per mode (`src/cdng/BlackLevel.hpp`), the Clear HDR white clamp.

### The format model today, and where Log goes

| Axis | Commands / keys | WebUI | Touch UI | Mode Ladder |
| --- | --- | --- | --- | --- |
| Format | `set_record_format` cdng/mlv/h264/lossydng/prores; state `recording_format` | Recording format card, format buttons | `recordFormatComponent` (`SettingsPage.qml`), `applyRecordingFormat` | per resolution: `compression` |
| Compression | `set_cdng_compression` none/lossless_jpeg; Lossy is a *format* with `set_lossy_dng_ratio` 3:1/5:1; the WebUI select mixes them and `dispatchCdngCompressionSelection` splits | `settingsCdngCompressionSelect` | `applyCdngCompression` | `none`, `lossless_jpeg`, `lossy_3to1`, `lossy_5to1` (`src/camera/ModeLadder.hpp` `knownCompression`) |
| Bit depth | `set_raw_bit_depth` 8/10/12/16; state `raw_bit_depth` | Bit Depth card | `applyRawBitDepth` | per resolution `bits` |
| Clear HDR | `set_clear_hdr`; state `clear_hdr` | switch | switch | per resolution `hdr\|sdr` |

**New axis: storage depth (Log).** It is not a compression and not the sensor bit depth (it is what
is *stored*). Patrik's rule: **Log runs in parallel with every compression**, Uncompressed, Lossless
JPEG and Lossy alike; it is an extra option, never a mode of its own.

| Item | Design |
| --- | --- |
| Setting | `cdng_log`: `off` \| `auto` \| `12` \| `10` \| `8`. `auto` = one step below the source depth. An explicit target ≥ source depth records linear and the state says so (CineMate's rule: not an error) |
| Command | `set_cdng_log value=off\|auto\|12\|10\|8`; applies to cDNG in all three compressions and to Lossy DNG; refused in H.264 and ProRes with the reason; MLV only if MLV readers honour a LinearizationTable (**unconfirmed**: MLV has no such block; start with cDNG and Lossy) |
| State | `cdng_log` (the setting), `cdng_log_bits` (0 = linear, else the stored depth), `cdng_log_available` (false in H.264/ProRes and when the source has no curve) |
| Persisted | `[camera] cdng_log` in `apertar-hardware.conf`, carried across formats like `fps_phase_lock`; presets carry it (allow-list in `apply_preset`) |
| Mode Ladder | the resolution text gains an optional sixth field: `WIDTHxHEIGHT:BITS:hdr\|sdr[:FPS[:COMPRESSION[:log\|log10\|log8]]]`; `effectiveCompression` unchanged; the ladder's JSON gets `log_bits`; the FPS ceiling per compression is measured at the stored depth |
| Encoder | a pure header `src/cdng/LogCurve.hpp` (port of the mu-law + footroom math, not a copy; constants from a generator script kept in `tools/`), built once per (source bits, black, white, target) and cached; applied on the **copy worker** next to `compressClearHdrFrame` (composed with the CCMP expansion in 12-bit Clear HDR); the frame view's `bitDepth` becomes the target so the existing packers and `whiteLevel(layout.bitDepth)` logic follow; `Metadata.linearizationTable` = the inverse table; `BlackLevel` tag stays linear |
| Lossless JPEG + Log | the predictor runs on log codes, which compress at least as well as linear |
| Lossy + Log | the Lossy encoder's own square-root companding (`buildCompanding` in `src/lossydng/LossyDngEncoder.cpp`) is **replaced** by the log curve at the chosen target depth when Log is on; the 3:1 / 5:1 quantisation and SOF3 coding run on the log codes as they run on the square-root codes today, and the file's `LinearizationTable` is the log inverse. One companding per file, never two |
| Size model | `estimatedRawBytesPerSecond` and the WebUI/touch "Time left" use `cdng_log_bits` when non-zero |
| WebUI | Recording format card: a **Log storage** select under Bit Depth (Off / On, one step down / 12-bit / 10-bit / 8-bit), live in every compression including Lossy; the resolution badge reads `4K · 16-bit · Clear HDR · Log 12`; a `LOG` pill on the Live preview row like CineMate's button toggles `auto`/`off` |
| Touch UI | a Log row in `recordFormatComponent` next to Bit Depth (`applyCdngLog` in `ApertarControlBridge`), the FORMAT row subtext shows `Log 12` |
| Sensors | black/white per sensor and mode come from Core's own tables, so IMX477/IMX294 work from day one (the CineMate limitation was spec selection, not the sensor) |

Bytes per 4K frame (3840×2160, no thumbnail): 16-bit 16.6 MB → Log 12 12.4 MB (−25 %); 12-bit
12.4 MB → Log 10 10.4 MB (−17 %); 10-bit 10.4 MB → Log 8 8.3 MB (−20 %).

## 5. Open questions (answer on the Pi)

1. Which counter carries today's drops at 4K25 16-bit on a < 50 % full card? (`takes.sh 1 600`, then
   `journalctl -u apertar-core | grep 'drop\['`.)
2. Does the kernel's own writeback (no fsync, no `sync_file_range`) stall the CFE on this board the
   way `dd conv=fdatasync` did on 2026-10-26? (Step 0, knob 2 alone.)
3. CMA headroom for 8 cached SDR buffers at 4K: `grep Cma /proc/meminfo` before and after.
4. Does `chrt -f 70` on the whole process starve the WebUI's MJPEG thread? (Step 5, watch the preview.)
5. Log: does Resolve honour `LinearizationTable` on an 8-bit stored DNG? (Export one frame, open it.)

## 6. Sources

- Apertar-Core `cinemate-port` @ `7678cbf`: `src/camera/CameraController.cpp` (class
  `DngRecordingQueue`, `syncLoop`, `startWriteback`, `rawCameraBufferCount`, `allocateCachedBuffers`),
  `src/util/MediaProfile.hpp`, `scripts/apertar-media-tune`, `config/apertar-core-capture-priority.conf`,
  `src/cdng/CdngEncoder.cpp`, `src/cdng/ClearHdrCcmp.hpp`, `src/lossydng/LossyDngEncoder.cpp`,
  `src/camera/ModeLadder.hpp`, `src/web/WebControlPage.cpp` (Recording format card).
- cinepi-raw @ `63a08d5`: `cinepi/dng_encoder.cpp`, `cinepi/cinepi_raw.cpp`, `cinepi/log_lut.hpp`,
  `cinepi/log_lut.cpp`, `cinepi/log_encode_arg.hpp`, `cinepi/dng_output_depth.hpp`.
- cinemate @ `4990afc`: `src/module/cinepi_multi.py`, `src/module/storage_profiles.py`,
  `services/storage-automount/storage-automount.py`, `services/cinemate-autostart/*.service`,
  `cinemate-install.sh` (`configure_cmdline`, `configure_audio_rtprio`), `docs/cinemate-log.md`.
- cinemate-handbook @ `c99ff77`: `architecture/cinepi-raw.md`, `lessons/hardware-log.md`
  (2026-08-27/28, 2026-09-13/14/15), `open-threads.md` ("DNG disk workers cannot set their nice level").
- This KB: `working/clearhdr-compare-answer.md` (theory A and B), `working/compare-raw/*.md`,
  `lessons/hardware-log.md` 2026-10-26/27, `tutorials/progress/T29.md`.
