# b1-cinepi-buffers-completion — cinepi-raw buffer counts and what runs on libcamera's completion thread

THEORY B, part 1. Reader: source only, camera not run. Status tags: CONFIRMED = line opened and read; PROBABLE = inferred, reason given; UNKNOWN = not derivable from these repos.

Repos read: cinepi-raw @ 63a08d5 (dev); cinemate @ d6cc93e (dev); libcamera(cinemate) @ bfe0b76. Core/libcamera(qbc)/imx585 were not needed for these six questions.

---

## Q1. Which thread copies the raw frame out of the libcamera buffer; what runs on libcamera's requestCompleted thread

**Headline (CONFIRMED): cinepi-raw never copies the raw frame on the completion thread, and the main loop does not copy it either. The only full-frame read of the camera buffer happens on a DngEncoder encode worker, inside dng_save(), which reads straight out of the mmap'd dma-heap buffer.**

### What runs on libcamera's requestCompleted thread (RPiCamApp::requestComplete)
- cinepi-raw/core/rpicam_app.cpp:921@63a08d5 `camera_->requestCompleted.connect(this, &RPiCamApp::requestComplete);`
- :1212 `void RPiCamApp::requestComplete(Request *request)`; :1214-1220 a cancelled request posts `MsgType::Timeout` and returns.
- :1223-1233 one `DMA_BUF_IOCTL_SYNC` ioctl per buffer in the request with `DMA_BUF_SYNC_START | DMA_BUF_SYNC_READ` (:1224). Two buffers per request in Cinemate's configuration (see Q2) => 2 ioctls.
- :1237 `CompletedRequest *r = new CompletedRequest(sequence_++, request);` — core/completed_request.hpp:23-27@63a08d5 copies `r->buffers()` (BufferMap) and `r->metadata()` (ControlList) and calls `r->reuse()` :26. Metadata copy, not pixel copy.
- :1238 `CompletedRequestPtr payload(r, [this](CompletedRequest *cr) { this->queueRequest(cr); });` — the shared_ptr deleter IS the requeue (Q3).
- :1240-1243 inserted into `completed_requests_` under mutex.
- :1247-1253 instantaneous framerate from `controls::SensorTimestamp` (`payload->framerate = 1e9 / (timestamp - last_timestamp_)` :1252).
- :1255 `post_processor_.Process(payload); // post-processor can re-use our shared_ptr`.

### What PostProcessor::Process does on that same thread
- cinepi-raw/core/post_processor.cpp:107@63a08d5 `void PostProcessor::Process(CompletedRequestPtr &request)`.
- :109-112 if `stages_.empty()` -> `callback_(request)` inline. The callback is `msg_queue_.Post(Msg(MsgType::RequestComplete, std::move(r)))` (rpicam_app.cpp:254-255). Cinemate always has stages (Q4), so this branch is not taken.
- :115-116 lock `mutex_`, `requests_.push(std::move(request))`.
- :118-131 `process_fn` runs `stage->Process(request)` for every stage and sets a promise.
- :135 `futures_.push(promise.get_future())`.
- :136 `std::thread { process_fn, std::ref(requests_.back()), std::move(promise) }.detach();` => **one detached pthread created per frame, on the libcamera completion thread**.
- :139-167 `outputThread` (created in Start :99) waits until `futures_.front()` is ready (:149-152), pops FIFO, and `callback_(request)` :165 posts to the app's `msg_queue_`. This re-serialises frames in completion order (head-of-line: a slow stage on frame N delays delivery of N+1... to the main loop even if N+1 finished).

So the completion thread's per-frame work is: 2 cache-sync ioctls, a BufferMap+ControlList copy, a set insert, a queue push, a promise/future, and a pthread_create. No pixel touching. (The pipeline-internal rev16 byte swap for 16-bit modes is libcamera's own and happens before requestCompleted fires — Established 1, not re-derived.)

### Where the raw frame is actually read
- Main loop (cinepi-raw/cinepi/cinepi_raw.cpp:454@63a08d5) `app.EncodeBuffer(completed_request, app.RawStream(), app.LoresStream());`
- cinepi-raw/cinepi/cinepi_recorder.hpp:49@63a08d5 `void EncodeBuffer(CompletedRequestPtr &completed_request, Stream *stream, Stream *lostream)`: :68 `BufferWriteSync w(this, completed_request->buffers[stream]);` (a `DMA_BUF_SYNC_START | DMA_BUF_SYNC_RW` ioctl, core/buffer_sync.cpp:16-36@63a08d5; its destructor at end of EncodeBuffer issues SYNC_END :38-46 — so the write-sync is NOT held while the encoder reads); :69 `mem = w.Get()` returns the mmap span; :101-104 `encode_buffer_queue_.push(completed_request); // creates a new reference`; :105 `encoder_->EncodeBuffer2(buffer->planes()[0].fd.get(), mem[0].size(), (void *)mem[0].data(), info, losize, lodata, loinfo, timestamp_ns / 1000, completed_request->metadata);` — passes the **pointer** into the camera buffer.
- cinepi-raw/cinepi/dng_encoder.cpp:455@63a08d5 `EncodeBuffer2(...)`: :461 `std::lock_guard<std::mutex> lock(encode_mutex_);` :465-478 builds `EncodeItem item = { mem, size, info, lomem, losize, loinfo, metadata, timestamp_us, index_++, folder, 0, clip_ceiling_gen_ }`; :479 `encode_queue_.push(item);` :480 `frames_in_flight_.fetch_add(1)`. cinepi-raw/cinepi/dng_encoder.hpp:517@63a08d5 `void *mem;` — the item holds a raw pointer, no copy. (The ControlList `met` :523 is copied by value.)
- Encode worker cinepi-raw/cinepi/dng_encoder.cpp:2013@63a08d5 `void DngEncoder::encodeThread(int num)`: pops under `encode_mutex_` :2027-2036; :2240-2251 `tiff_size = dng_save(num, mem_buf, static_cast<const uint8_t *>(encode_item.mem), ...)` — **the camera buffer is the source operand of dng_save on the encode worker**.
- Inside dng_save for 14/16-bit: dng_encoder.cpp:1425-1433@63a08d5 comment `/* 14- or 16-bit → copy verbatim, one active row each */`, `rowBytes = (info.width * dng_info.bits + 7) / 8` :1426, per-row `write_pod(buf, raw + y * info.stride, rowBytes)` :1432; `write_pod` is a bounds-checked `std::memcpy` into the pooled TIFF buffer (cinepi-raw/cinepi/ifd_builder.hpp:173-181@63a08d5). So the 16-bit path is one full-frame memcpy per frame on an encode worker; the 12-bit path packs/compresses row by row there instead (:1259 `pack_row_12bit`, :1321 `pack_row_16_to_12bit`, lossless JPEG elsewhere).
- Worker count: `encode_worker_count_ = std::max<uint32_t>(1, options_->encode_workers)` dng_encoder.cpp:292@63a08d5; default `encode_workers { 2 }` cinepi-raw/cinepi/raw_options.hpp:59@63a08d5, `disk_workers { 8 }` :60. Cinemate passes `--encode-workers 4 --disk-workers 8 --encode-affinity 1-2 --disk-affinity 1-2 --encode-nice -10 --disk-nice -5` for ext4 (cinemate/src/module/storage_profiles.py:61-73@d6cc93e, args built :156-171) and 4/2/1-2/2 for the default-safe profile (:52-60). Thread names `dng-enc-N` / `dng-dsk-N` (dng_encoder.cpp:2015, :2316).

---

## Q2. Buffer counts in the configure path cinepi-raw uses

### Which Configure* cinepi-raw calls
- cinepi-raw/cinepi/cinepi_raw.cpp:83@63a08d5 `app.ConfigureVideo(CinePIRecorder::FLAG_VIDEO_RAW, 0);` — the only live Configure call (`ConfigureViewfinder` is commented out at :58 and :84).

### ConfigureVideo (cinepi-raw/core/rpicam_app.cpp:610@63a08d5)
- :614 `have_lores_stream = options_->lores_width && options_->lores_height;` :615 `have_raw_stream = !options_->no_raw;` :616 `alias_lores_to_video = have_raw_stream && have_lores_stream;`
- :618-622 roles: `VideoRecording`, then `Raw` when have_raw_stream, then `Viewfinder` only when `have_lores_stream && !alias_lores_to_video`. Cinemate always passes `--lores-width/--lores-height` (cinemate/src/module/cinepi_multi.py:687-688@d6cc93e) and never `--no-raw`, so **alias is true: exactly two streams — stream 0 (YUV420 "video", which IS the lores/preview stream) and stream 1 (raw). No third stream.**
- :630 `cfg.bufferCount = 6; // 6 buffers is better than 4` (stream 0). :631-632 `if (options_->buffer_count > 0) cfg.bufferCount = options_->buffer_count;`
- :657 `configuration_->at(1).bufferCount = configuration_->at(0).bufferCount;` (raw = stream-0 count).
- :699 `configuration_->at(lores_index).bufferCount = configuration_->at(0).bufferCount;` — only reached in the non-alias branch (:683), so not in Cinemate's path.
- :660-676 alias branch: stream 0's size is set to the lores size fitted inside the raw size (`fit_lores_to_raw`, cinepi/lores_fit.hpp) :666-675.
- :706-711 `streams_["video"] = at(0)`, `streams_["raw"] = at(1)`, `streams_["lores"] = at(0)` when alias.
- Other Configure* bufferCount lines, for completeness (not cinepi-raw's path): ConfigureViewfinder :359 (:409-410 `viewfinder_buffer_count`, :420 lores = at(0), :430 raw = at(0)); ConfigureZsl :454 (:473-477, :497, :530); ConfigureStill :549 (:571 `bufferCount = 2`, :573 `= 3`, :574-575 `buffer_count`, :595).
- Option text: cinepi-raw/core/options.hpp:199@63a08d5 `("buffer-count", ... default_value(0), "Number of in-flight requests (and buffers) configured for video, raw, and still.")`; :200 `viewfinder-buffer-count`.

### Allocation (setupCapture, rpicam_app.cpp:1120@63a08d5)
- :1125 `configuration_->validate()`; :1131 `camera_->configure(configuration_.get())`.
- :1141-1165 for every stream, `for (unsigned int i = 0; i < config.bufferCount; i++)` :1145 -> `dma_heap_.alloc(name.c_str(), config.frameSize)` :1148, `mmap(NULL, config.frameSize, PROT_READ | PROT_WRITE, MAP_SHARED, ...)` :1159, stored in `mapped_buffers_` :1160.
- cinepi-raw/core/dma_heaps.cpp:26-27@63a08d5 heap order `"/dev/dma_heap/vidbuf_cached"`, then `"/dev/dma_heap/linux,cma"`; comment :22-23 "vidbuf_cached sym links to either the system heap (Pi 5) or the CMA allocator (Pi 4 and below)". **cinepi-raw's buffers are app-allocated, CPU-cached system-heap buffers on Pi 5** (the same class of memory Core moved to in 94ac68d; Cinemate's own "~25 MB of CMA at 4K" comment in storage_profiles.py:36 is Pi-4-era wording).
- Requests: `makeRequests` :1173-1210 creates one Request per stream-0 buffer (:1189-1197) and throws `"concurrent streams need matching numbers of buffers"` :1200 otherwise. StartCamera queues them all :925.

### Resulting counts
| Launch | stream 0 (video = lores, YUV420) | stream 1 (raw) | separate lores stream | in-flight requests |
|---|---|---|---|---|
| `--buffer-count 8` (Cinemate ext4 and default-safe profiles, storage_profiles.py:59,:72; `args += ["--buffer-count", str(buffer_count)]` cinepi_multi.py:866@d6cc93e; exfat/ntfs profiles use 10, :82,:93) | 8 | 8 | none (aliased) | 8 |
| no option (`cfg.bufferCount = 6`) | 6 | 6 | none | 6 |

Each request carries 2 buffers (one raw + one YUV420). CONFIRMED from the lines above.

Note on Cinemate's count: `buffer_count = int(profile.get("buffer_count", 8))` cinepi_multi.py:846@d6cc93e, overridable by `sensors.raw_buffer_count` in settings :849-852.

---

## Q3. When exactly the camera buffer goes back to libcamera — CompletedRequestPtr lifetime

Mechanism (CONFIRMED): the shared_ptr deleter created at rpicam_app.cpp:1238 calls `queueRequest(cr)`. The buffer returns to libcamera **when the last CompletedRequestPtr reference is dropped, on whichever thread drops it.**

`queueRequest` (rpicam_app.cpp:975@63a08d5): :977 `BufferMap buffers(std::move(completed_request->buffers));` :981 `camera_stop_mutex_`; :986-996 look up/erase in `completed_requests_`; :1000 `delete completed_request;` :1003 return if camera stopped or not found; :1005-1019 per buffer `DMA_BUF_SYNC_END | DMA_BUF_SYNC_READ` ioctl (:1009, :1015) then `request->addBuffer` :1018; :1022-1024 pending `controls_` moved into the request; :1027 `camera_->queueRequest(request)`.

Reference holders, in the order they appear and release:
1. **PostProcessor** — `requests_` queue (post_processor.cpp:116) until `outputThread` moves it out :160 and hands it to `callback_` :165, which `std::move`s it into the `Msg` posted to `msg_queue_` (rpicam_app.cpp:255). Net: the post-processor holds no reference once the message is posted; the detached stage thread's `std::ref(requests_.back())` is a reference, not a copy.
2. **Main loop's Msg** — cinepi_raw.cpp:383 `Msg msg = app.WaitFor(3000 ms)`; :405 `CompletedRequestPtr &completed_request = std::get<CompletedRequestPtr>(msg.payload);` is a reference into `msg`, which lives until the next loop iteration's `WaitFor` assigns a new `msg` (i.e. until the next frame arrives, roughly one frame period later).
3. **Encoder** — cinepi_recorder.hpp:103 `encode_buffer_queue_.push(completed_request)` (only while recording). Released by `encodeBufferDone` :158-174, which pops `encode_buffer_queue_.front()` :169-172 ("drop shared_ptr reference"). `encodeBufferDone` is bound as `input_done_callback_` (:42) and is called by the encode worker at dng_encoder.cpp:2304 (`/* mark the camera buffer as reusable */` :2303) **after `dng_save` returns, i.e. after the 16-bit memcpy / 12-bit pack-or-compress is complete and the DiskItem is queued (:2281-2295), but before the disk write.** Also on the dng_save error path :2272. The disk thread (:2314-2404) never touches the CompletedRequestPtr; it works on the pooled TIFF buffer only.
4. **Preview** — `ShowPreview` rpicam_app.cpp:1087-1095: `preview_item_ = PreviewItem(completed_request, stream); // copy the shared_ptr here` :1091 if no frame is pending, else `preview_frames_dropped_++` :1093 (non-blocking, latest-frame-wins). `previewThread` :1288 moves it out :1299, stores `preview_completed_requests_[fd] = std::move(item.completed_request)` :1337, calls `preview_->Show(fd, span, info)` :1339; the reference is dropped in `previewDoneCallback(fd)` :1258-1265 ("drop shared_ptr reference" :1264) when the DRM/EGL preview releases that fd (for NullPreview synchronously inside Show, per comment :1328-1335).

So: **while recording, the raw+lores buffer pair goes back to libcamera at the LAST of {encode worker finishing dng_save for that frame, main loop receiving the next frame, preview done-callback for that fd}.** The preview stage (ccmpPreview etc.) is not a holder: it finished before the message reached the main loop. While idle (not recording), the holders are only 2 and 4.

**PROBABLE hazard (source reading only):** `encodeBufferDone` assumes in-order completion (comment cinepi_recorder.hpp:160-163 "we're just assuming everything is done in order") but there are 4 encode workers (Cinemate) finishing dng_save concurrently; a worker finishing frame N+1 before N pops frame N's CompletedRequestPtr. The holder COUNT is right (one pop per finished encode) but the IDENTITY can be wrong, so a camera buffer can be requeued while another worker is still reading it (tearing, not a drop). Not confirmed on hardware.

---

## Q4. Where post-processing stages run; do they block the main loop or the completion thread; per-frame cost they log

### Which stages are active under Cinemate
- cinepi-raw/cinepi/cinepi_raw.cpp:57@63a08d5 `app.EnsureFirstPostProcessingStage("ccmpPreview");` (rationale comment :48-56; `EnsureFirstStage` post_processor.cpp:44-67 inserts at the front :65 unless the JSON already names it).
- Installer JSON cinemate/cinemate-install.sh:1359-1365@d6cc93e: `"sharedContext": {}` and `"mjpegPreview": {"port": 8000}` (per-camera files :1367-1381, port 8001 for cam1). Dual-sensor file adds `dualHdmiPreview` (cinemate/src/module/cinepi_multi.py:388-396@d6cc93e). `--post-process-file` passed at cinepi_multi.py:693.
- Loaded by `post_processor_.Read(options_->post_process_file)` rpicam_app.cpp:251-252.
=> Stage chain per frame: ccmpPreview -> sharedContext -> mjpegPreview (-> dualHdmiPreview in dual mode). `stages_` is never empty, so every frame takes the detached-thread path.

### Where they run (CONFIRMED)
- All stages run inside the **per-frame detached std::thread** created at post_processor.cpp:136 — not on libcamera's completion thread (which only spawns it) and not on the main loop (which only sees the frame after `outputThread` posts it). The stage author says so: cinepi-raw/cinepi/ccmpPreviewStage.cpp:158-164@63a08d5 "PostProcessor::Process() spawns a DETACHED THREAD PER REQUEST, so two frames can be inside Process() at once ... the work is ~3 ms against a 20-40 ms frame period, so serialising here costs nothing real"; `std::mutex mutex_` :165, taken at Process :526.

### Do they block anything?
- Completion thread: no — it returns right after `detach()`.
- Main loop: not directly; indirectly via `outputThread`'s FIFO (post_processor.cpp:149-152, 158-161): frame N+1 cannot be delivered before frame N's stages finish. Also the ccmpPreview mutex serialises the stage work across frames. Also `BufferWriteSync lw(app_, lores)` at ccmpPreviewStage.cpp:555 is a `DMA_BUF_SYNC_START|RW` ioctl; comment :550-552 says these "block on the DMA fence for buffers the ISP may still be writing".
- Note the stages themselves hold no CompletedRequestPtr copy; they cannot delay buffer return except through the above delivery delay.

### What each stage does per frame and what it logs
- **ccmpPreview** (ccmpPreviewStage.cpp:524 `Process`): per-frame colour gains/CCM from metadata :535-544; `BufferReadSync rr` raw (no ioctl, buffer_sync.cpp:54-66) + `BufferWriteSync lw` lores :554-555, sync time accumulated :558-560; `measureClamp(raw.data())` :590 (sampled rows); "ONE RENDER PER FRAME" comment :592-603 — 16-bit: `renderer_.correctHighlightsInPlace(raw.data(), lores.data())` :607 (in-place fix of clipped pixels; the comment says the earlier full software re-render "dropped frames at 4K", matching handbook 2026-09-15 as given); 12-bit: `renderer_.render(raw.data(), lores.data())` :609 (full software render of the lores frame from raw). Cost log every `kMaxCodeReportFrames = 120` (:175) frames at info level, :655-660: `"ccmpPreview: cost/frame — {} {:.2f} ms, buffer sync {:.2f} ms, measure {:.2f} ms, total {:.2f} ms; delivering {:.2f} fps ({:.1f} ms/frame available) over {} frames"` (render/highlight-pass ms, sync ms, measure ms, total, fps the stage saw). Comment :641-646: "if it reads 22 against a requested 25, three frames a second are going missing somewhere".
- **sharedContext** (sharedContextStage.cpp:212 `Process`): copies `PispStatsOutput` into shm :229-234 (memcpy of the stats blob only), writes raw/isp fds, lengths, framerate, sequence :237-245, metadata fields :246. No pixel work, no timing log.
- **mjpegPreview** (`mjpegStreamStage`, mjpegPreviewStage.cpp:290 `Process`): `BufferReadSync r` on the lores stream :300; `compressToJPEG(buffer, jpegBuffer)` :306 (libjpeg-turbo on the YUV420 lores); `streamer_->publish` :318 (HTTP multipart). Timing logs at **trace** level only :328-330: `"Duration of WriteSync: {} microseconds."`, `"Duration of Compression: ..."`, `"Duration of Publish: ..."`; client-count debug every kClientCountLogEveryNFrames :323-325.
- **dualHdmiPreview** (dualHdmiPreviewStage.cpp:583 `Process`): `BufferReadSync` :608 on the preview stream; `composeAndShow` (primary) or `publishSecondary` :612-615. No timing log.

Other per-frame work on the MAIN thread (not a stage, but on the frame path): `controller.process(completed_request)` cinepi_raw.cpp:408 does one synchronous pipelined Redis round trip per frame — cinepi-raw/cinepi/cinepi_controller.cpp:686-700@63a08d5 `pipe.publish(CHANNEL_STATS, ...)`, `.set(ts_key)`, `.set(tc_key)`, `.get("fps_user")`, `.get("is_recording")`, `pipe.exec()` :699; comment :676-683 "This runs on the capture thread, so collapsing 4-6 round trips into 1 keeps Redis stalls off the frame path".

---

## Q5. Per-frame timing instrumentation / log lines

| Where | Level | Text / fields |
|---|---|---|
| cinepi-raw/cinepi/cinepi_recorder.hpp:92-96@63a08d5 | LOG(1), per frame when `abs(fps_measured - fps_setting) > 1` | `"Frame Drop!!!!!     FPS measured:" << fps_measured << " FPS settings:" << fps_setting` (sensor-timestamp delta vs FrameDuration; only while recording, inside EncodeBuffer) |
| cinepi-raw/cinepi/dng_encoder.cpp:2298-2301@63a08d5 | spdlog debug, per frame | `"Thread[{}] {} Time taken for the encode: {} ms, disk queue:{}  Size:{}"` (encode worker, from `start_time` :2202 to after DiskItem push; disk_buffer_.size() = disk queue depth) |
| dng_encoder.cpp:2401-2403 | debug, per frame | `"Thread[{}] {} Time taken for the disk io: {} milliseconds"` (open+write+close) |
| dng_encoder.cpp:2347 | info, per frame | `"DNG written: {}"` (logged BEFORE the write, :2347 precedes open :2352) |
| dng_encoder.cpp:2294 | counter | `noteBufferDepth(disk_buffer_.size())` -> high-water mark `buffer_hwm_` (dng_encoder.hpp:204-208), read/reset by `bufferSizeMaxAndReset()` :201-203 |
| dng_encoder.cpp:2129-2135 | counter | `dropped_frames_ += raw_elapsed - 1` when the sensor-timestamp gap between consecutive encoded frames is >= 2 frame periods (TC step under encode_mutex_) |
| cinepi-raw/cinepi/cinepi_controller.cpp:636-647@63a08d5 | Redis `cp_stats` JSON, per frame | `framerate` (libcamera's instantaneous, from requestComplete), `frameCount`, `tcFrameCount`, `droppedFrames`, `writeFailures`, `bufferSize`, `bufferSizeMax`, `framesInFlight`, `timestamp`, `cameraPort` — published at :691 |
| cinepi-raw/cinepi/ccmpPreviewStage.cpp:655-660@63a08d5 | info, every 120 frames | `"ccmpPreview: cost/frame — ... total {:.2f} ms; delivering {:.2f} fps ({:.1f} ms/frame available) over {} frames"` |
| mjpegPreviewStage.cpp:328-330 | trace | `"Duration of WriteSync/Compression/Publish: {} microseconds."` |
| rpicam_app.cpp:1247-1253 | field | `payload->framerate` from SensorTimestamp deltas (feeds sharedContext :244 and cp_stats) |
| rpicam_app.cpp:1093, :1349, :1340 | counters; logged once at shutdown :193-195 LOG(2) | `preview_frames_dropped_`, `preview_frames_displayed_` ("frames displayed N, dropped M") |
| dng_encoder.cpp:1084-1085, :1087 | info, once per setup | `"RAM pool: up to {} frames  (~{} MB)"`, `"Encoder configured – {}×{} {}-bit, buffer {} MB"`; `max_ram_buffers_ = 0.90 * MemAvailable / dng_info.buffer_size` :1079-1082 |
| dng_encoder.cpp:314 | info, once | `"DngEncoder started with {} encode worker(s) and {} disk worker(s)"` |
| cinepi_controller.cpp:37-39 | comment (measured by author) | thumbnail "+4.0 ms/frame of encode time (+18% over no thumbnail at all) ... against a 40 ms frame budget at 25 fps, with zero dropped frames and a disk queue that never exceeded 2" |

No log line reports the libcamera completion-thread duration or the post-processor queue depth (`futures_.size()`). UNKNOWN whether Cinemate runs cinepi-raw at debug level so that the per-frame encode/disk timings appear (not checked; out of this question's scope).

---

## Q6. Memory per buffer, 3840x2200 16-bit, and total with 8 buffers

- Raw stream pixel format for a 16-bit mode is unpacked 16 bpp (`mode_to_pixel_format(options_->mode)` rpicam_app.cpp:654; `sensorConfig->bitDepth = options_->mode.bit_depth` :656). Bytes per row = 3840 x 2 = **7680 B**.
- Stride/frameSize come from the V4L2 format libcamera negotiates: libcamera(cinemate)/src/libcamera/pipeline/rpi/common/pipeline_base.cpp:347-348@bfe0b76 `stream->stride = format.planes[0].bpl; stream->frameSize = format.planes[0].size;`; the PiSP pipeline sets `bpl` from `libpisp::compute_optimal_stride` (libcamera(cinemate)/src/libcamera/pipeline/rpi/pisp/pisp.cpp:235-253@bfe0b76). libpisp is not vendored here, so the alignment constant is UNKNOWN; but 7680 is a multiple of 512, so for any alignment <= 512 B the stride stays 7680. PROBABLE stride 7680.
- **Per raw buffer: 7680 x 2200 = 16,896,000 B = 16.9 MB (16.11 MiB)** (PROBABLE; exact if the kernel adds no trailing padding to `sizeimage`).
- 8 raw buffers: **135,168,000 B = 135.2 MB (128.9 MiB)**. 6 raw buffers: 101,376,000 B = 101.4 MB.
- Lores/video stream (stream 0, YUV420), same count: Cinemate sizes it with `compute_preview_geometry` (cinemate/src/module/sensor_detect.py:383@d6cc93e): `PREVIEW_TARGET_LINES = 720`, `PREVIEW_PADDING_X = 94`, `PREVIEW_PADDING_Y = 50` (:378-380); canvas default 1920x1080 (cinepi_multi.py:590) -> aw = 1732, ah = 980; `lores_h = min(target_lines, ah, height)` :488 = 720; `lores_w = int(lores_h * desqueezed_aspect)` :489. With the 3840x2200 transport carrying a 3840x2160 active image (sensor_detect.py:768 comment) aspect = 16:9 -> **1280x720**; with no crop annotation (fallback aspect 3840/2200) -> 1256x720. Per YUV420 buffer at 1280x720: 1280 x 720 x 1.5 = **1,382,400 B (1.38 MB)** (PROBABLE; libpisp may pad the stride). 8 lores buffers: **11,059,200 B (11.1 MB)**.
- **Total camera-side dma-heap memory with `--buffer-count 8`: 135.2 MB + 11.1 MB = ~146.2 MB (139.5 MiB)**, all from `vidbuf_cached` (system heap, cached). With 6: ~109.7 MB.
- Not counted (UNKNOWN sizes): libcamera's internal CFE config/stats and ISP intermediate buffers; the encoder's pooled TIFF buffers (`dng_info.buffer_size` each, up to `max_ram_buffers_` = 90 % of MemAvailable, dng_encoder.cpp:1079-1082), which for 16-bit are >= 16.9 MB each and are the dominant RAM consumer while recording.
- Cross-check against Cinemate's own estimate: storage_profiles.py:36-37 "Each extra buffer costs ~25 MB of CMA at 4K (raw + video streams share the count)" — higher than the 18.3 MB computed here; PROBABLE the comment predates the aliased-lores change or assumed a larger video stream.

---

## Summary table — threads on cinepi-raw's per-frame path (16-bit 4K, Cinemate launch)

| Thread | Per-frame work | Touches raw pixels? |
|---|---|---|
| libcamera pipeline/completion thread | (pipeline-internal rev16 swap, given) + requestComplete: 2 DMA_BUF_SYNC_START ioctls, CompletedRequest (BufferMap+ControlList copy), framerate, PostProcessor::Process: mutex, queue, promise, pthread_create+detach | No |
| per-frame detached stage thread | ccmpPreview (mutex; lores write-sync ioctl; measureClamp sampled rows; 16-bit: correctHighlightsInPlace on raw+lores / 12-bit: full lores render from raw), sharedContext (stats memcpy to shm), mjpegPreview (libjpeg-turbo on lores, HTTP publish) | Yes, read-only sampling / in-place highlight fix (16-bit); full read (12-bit render) |
| PostProcessor outputThread | futures FIFO -> msg_queue_.Post | No |
| main thread (cinepi_raw.cpp loop) | WaitFor; controller.process (one synchronous Redis pipeline exec); triggerRec; EncodeBuffer (raw write-sync ioctl, fps check, 2 queue pushes); ShowPreview (shared_ptr copy) | No |
| preview thread | BufferReadSync, DRM Show of lores | No (lores only) |
| dng-enc-N (4, cores 1-2, nice -10) | RAM permit; pooled buffer; dng_save: TIFF header + full-frame row memcpy (16-bit) or pack/compress (12-bit) from the camera buffer; DiskItem push; **releases CompletedRequestPtr here** | Yes — the only full read of the raw frame |
| dng-dsk-N (8 on ext4, cores 1-2, nice -5) | buffered open/write/close of the pooled TIFF buffer, POSIX_FADV_SEQUENTIAL, no fsync, no DONTNEED | No (pooled buffer) |

## Surprises
1. cinepi-raw has no app-side copy of the raw frame at all before encode; the encoder reads the camera buffer in place and the buffer is held through the encode but not through the disk write. Core (Established 4) copies the whole frame on libcamera's completion thread — that is the structural difference THEORY B is about.
2. The post-processor creates and detaches a pthread per frame on libcamera's completion thread.
3. cinepi-raw's camera buffers are app-allocated from `vidbuf_cached` (cached system heap on Pi 5), never the CFE's internal allocations.
4. `encodeBufferDone` pops the FIFO front regardless of which frame finished, while 4 encode workers run concurrently — a probable buffer-identity hazard (tearing), not a drop mechanism.
5. `BufferWriteSync` in `EncodeBuffer` ends its SYNC_END before the encoder reads; `BufferReadSync` performs no ioctl at all (relies on requestComplete's SYNC_START).
6. Disk writes are plain buffered write() without `posix_fadvise(DONTNEED)` or fsync (contrast Core's DONTNEED-before-close).

## Unanswered / UNKNOWN
- Exact libpisp stride alignment for the 16-bit raw and the YUV420 lores (libpisp not in these repos); numbers above assume no padding beyond 512-B alignment.
- Whether the driver reports a crop annotation for 3840x2200 on the Pi (decides 1280x720 vs 1256x720 lores).
- Whether Cinemate runs cinepi-raw with spdlog debug enabled (decides whether the per-frame encode/disk ms lines exist in logs).
- Actual per-frame durations on hardware for the detached stage thread, the main-loop Redis round trip, and the 16-bit memcpy in dng_save (no hardware run).

## Verification

Adversarial verifier pass over the reader's findings above. Every citation was opened at the checkout (cinepi-raw @ 63a08d5, cinemate @ d6cc93e, libcamera(cinemate) @ bfe0b76) with grep -n for the anchor and sed -n for the window. Verdicts: CONFIRMED / CORRECTED (exact correction given) / REFUTED / UNVERIFIABLE. This section is written incrementally; a later block supersedes nothing earlier unless it says so.

### Block 1 — rpicam_app.cpp core, post_processor.cpp, completed_request.hpp, buffer_sync.cpp, dma_heaps.cpp, options.hpp, cinepi_raw.cpp main loop, cinepi_recorder.hpp

| Reader cite | Verdict | What the source shows |
|---|---|---|
| cinepi-raw/core/rpicam_app.cpp:921@63a08d5 `requestCompleted.connect` | CONFIRMED | line 921 exactly |
| rpicam_app.cpp:1212-1255 requestComplete | CONFIRMED | function body 1212-1256; `post_processor_.Process(payload)` at 1255 |
| rpicam_app.cpp:1224 `DMA_BUF_SYNC_START \| DMA_BUF_SYNC_READ` | CORRECTED | the flags line is **1225**; 1224 is `struct dma_buf_sync dma_sync {};` |
| rpicam_app.cpp:1238 deleter -> queueRequest | CONFIRMED | 1238 exactly |
| rpicam_app.cpp:1247-1253 framerate | CONFIRMED | `payload->framerate = 1e9 / ...` at 1252 |
| completed_request.hpp:23-27 | CONFIRMED | ctor 23-27, `r->reuse()` at 26 |
| post_processor.cpp:107-137 Process / detach | CONFIRMED | Process 107-137; `.detach()` at 136 |
| post_processor.cpp:109-112 stages_.empty() inline callback | CONFIRMED | 109-113 |
| post_processor.cpp:139-167 outputThread | CONFIRMED | 139-167; `wait_for(0s)` at 151; `callback_(request)` at 165 |
| post_processor.cpp:149-161, 160-165 | CONFIRMED | |
| post_processor.cpp:44-67 EnsureFirstStage | CONFIRMED (minor) | function is 44-68; `stages_.insert(stages_.begin(), ...)` at 66 |
| rpicam_app.cpp:254-255 SetCallback -> msg_queue_.Post | CONFIRMED | |
| rpicam_app.cpp:251-252 post_processor_.Read | CONFIRMED | |
| rpicam_app.cpp:193-195 preview counters at shutdown | CONFIRMED | LOG(2) in ~RPiCamApp |
| rpicam_app.cpp:614-622 alias_lores_to_video | CONFIRMED | 616 defines it; 621-622 Viewfinder role only when !alias |
| rpicam_app.cpp:630-632 `6 buffers is better than 4` | CONFIRMED | 630; override 631-632 |
| rpicam_app.cpp:657 raw bufferCount = at(0) | CONFIRMED | |
| rpicam_app.cpp:699 lores bufferCount (non-alias) | CONFIRMED | inside `if (have_lores_stream && !alias_lores_to_video)` at 689 |
| rpicam_app.cpp:660-676 fit_lores_to_raw | CONFIRMED | block 660-675; `fit_lores_to_raw` call 666-667; `at(0).size = lores_size` 673 |
| rpicam_app.cpp:706-711 streams_["lores"] = at(0) | CONFIRMED (minor) | the quoted line is **710**; 706 video, 708 raw, 712 non-alias lores |
| rpicam_app.cpp:1173-1200 makeRequests | CORRECTED | makeRequests starts 1173; the quoted throw `concurrent streams need matching numbers of buffers` is at **1202**, outside the cited window. One Request per stream-0 buffer: 1189-1199 |
| options.hpp:199-200 | CONFIRMED | `buffer-count` 199, `viewfinder-buffer-count` 200 |
| Other Configure* bufferCount lines 409-410, 420, 430, 473-477, 497, 530, 571, 573, 574-575, 595 | CONFIRMED | grep -n: 410, 420, 430, 474, 477, 497, 530, 571, 573, 575, 595 all `bufferCount` assignments; 409 and 574 are the `if` guards |
| rpicam_app.cpp:1141-1165 alloc+mmap | CONFIRMED | loop 1140-1165; alloc 1148; mmap PROT_READ\|PROT_WRITE, MAP_SHARED at 1159 |
| dma_heaps.cpp:22-27 | CONFIRMED | comment 22-23; `vidbuf_cached` 27, `linux,cma` 28 |
| rpicam_app.cpp:975-1028 queueRequest | CONFIRMED | SYNC_END\|READ at 1008; `camera_->queueRequest` at 1027 |
| rpicam_app.cpp:1087-1095 ShowPreview | CONFIRMED | copy at 1091, dropped++ at 1093 |
| rpicam_app.cpp:1337-1339 | CONFIRMED | |
| rpicam_app.cpp:1258-1265 previewDoneCallback | CONFIRMED | erase at 1264 |
| buffer_sync.cpp:16-46 BufferWriteSync | CONFIRMED | ctor 16-37 (START\|RW at 20), dtor 39-47 (END\|RW at 42) |
| buffer_sync.cpp:54-66 BufferReadSync no ioctl | CONFIRMED | comment 63-64 |
| cinepi_raw.cpp:83 ConfigureVideo(FLAG_VIDEO_RAW, 0) | CONFIRMED | only configure call in the loop; `//app.ConfigureViewfinder()` commented at 58 and 84 |
| cinepi_raw.cpp:48-57 EnsureFirstPostProcessingStage | CONFIRMED | call at 57, comment 49-56 |
| cinepi_raw.cpp:383, 405, 408-462, 454 | CONFIRMED | WaitFor 383; payload 405; process 408; EncodeBuffer 454; ShowPreview 462 |
| cinepi_recorder.hpp:68-69 BufferWriteSync in EncodeBuffer | CONFIRMED | |
| cinepi_recorder.hpp:92-96 Frame Drop LOG(1) | CONFIRMED | `if(abs(fps_measured - fps_setting) > 1)` 95, LOG 96 |
| cinepi_recorder.hpp:103-105 push + EncodeBuffer2 | CONFIRMED | |
| cinepi_recorder.hpp:158-174 encodeBufferDone | CONFIRMED | `just assuming everything is done in order` at 161; pop at 172 |

Claim-level notes from this block:
- Q1 "2 ioctls per request": the loop at 1226-1235 does one ioctl per buffer in `request->buffers()`; with the alias configuration that is 2 buffers (video/lores + raw). CONFIRMED.
- Q1 "CompletedRequest copies BufferMap + ControlList": completed_request.hpp:24 copy-constructs `buffers(r->buffers())` and `metadata(r->metadata())`. CONFIRMED.
- Note on Q3: `BufferWriteSync w` in EncodeBuffer (cinepi_recorder.hpp:68) is destroyed at the end of EncodeBuffer (:106), i.e. the DMA_BUF_SYNC_END|RW is issued BEFORE the encode worker reads the buffer; the reader's surprise item on this is CONFIRMED.

### Block 2 — dng_encoder.cpp/.hpp, ifd_builder.hpp, raw_options.hpp, cinepi_controller.cpp, stages, cinemate, libcamera(cinemate)

| Reader cite | Verdict | What the source shows |
|---|---|---|
| cinepi-raw/cinepi/dng_encoder.cpp:455-481 EncodeBuffer2 | CONFIRMED | signature 455; `encode_queue_.push(item)` 479; `frames_in_flight_.fetch_add` 480 |
| dng_encoder.hpp:514-535 struct EncodeItem / encode_queue_ | CONFIRMED | `void *mem` 517; `std::queue<EncodeItem> encode_queue_` 535 |
| dng_encoder.cpp:2240-2251 dng_save call | CORRECTED | `tiff_size = dng_save(` is at **2239**, args through 2250; `encode_item.mem` passed as the raw source at 2242 |
| dng_encoder.cpp:1425-1432 14/16-bit per-row write_pod | CONFIRMED | comment 1425; `write_pod(buf, raw + y * info.stride, rowBytes)` 1432; rowBytes = (width*bits+7)/8 at 1426 |
| ifd_builder.hpp:173-181 write_pod = memcpy | CONFIRMED | memcpy at 178 |
| raw_options.hpp:59-60 encode_workers{2}, disk_workers{8} | CONFIRMED | |
| dng_encoder.cpp:292-293 worker counts from options | CONFIRMED | 292-293; hard-coded 2/8 fallback at 300-301 |
| dng_encoder.cpp:305-314 thread spawn | CONFIRMED (minor) | encodeThread emplace 307, diskThread emplace 311; `DngEncoder started with` log is at **313-315**, not 314 |
| dng_encoder.cpp:2281-2308 DiskItem push, encode log, input_done_callback_ | CONFIRMED | `disk_buffer_.push` 2293; `noteBufferDepth` 2294; debug encode-time log 2300-2301; `/* mark the camera buffer as reusable */` 2303; `input_done_callback_(nullptr)` 2304 |
| dng_encoder.cpp:2272 error-path input_done_callback_ | CONFIRMED | |
| dng_encoder.cpp:2314-2404 diskThread | CONFIRMED | 2314 start; DiskItem.mem_buf only; `frames_in_flight_.fetch_sub` 2389 after close (2375-2380) |
| dng_encoder.cpp:2298-2301 encode-time debug log | CONFIRMED (minor) | the `console->debug(...)` is 2300-2301 (2298-2299 compute end_time/duration) |
| dng_encoder.cpp:2401-2403 disk-io debug log | CONFIRMED | 2403 |
| dng_encoder.cpp:2347 `DNG written` info before the write | CONFIRMED | 2347; `open(...)` 2352 |
| dng_encoder.cpp:2294 noteBufferDepth | CONFIRMED | |
| dng_encoder.hpp:201-208 bufferSizeMaxAndReset / noteBufferDepth | CONFIRMED | 201 / 204 |
| dng_encoder.cpp:2129-2135 dropped_frames_ | CONFIRMED | `if (raw_elapsed >= 2)` 2134, `dropped_frames_ += raw_elapsed - 1` 2135 |
| dng_encoder.cpp:1079-1087 RAM_FRACTION / RAM pool / Encoder configured | CORRECTED | RAM_FRACTION 1079; `RAM pool: up to {} frames` 1084-1085; `Encoder configured – {}×{} {}-bit, buffer {} MB` is at **1089-1091**, outside the cited window |
| dng_encoder.cpp:314 `DngEncoder started with` | CORRECTED | **313** |
| dng_encoder.cpp:2352-2374 buffered open/fadvise/write, no fsync, no DONTNEED | CONFIRMED | open 2352, POSIX_FADV_SEQUENTIAL 2356, write 2360; grep for fsync/fdatasync/POSIX_FADV in the file: only the one SEQUENTIAL hit |
| cinepi_controller.cpp:676-699 pipelined Redis round trip | CONFIRMED | `This runs on the capture thread` 683; `pipe.publish(CHANNEL_STATS` 691; `.get("fps_user")` 697, `.get("is_recording")` 698; `pipe.exec()` 699 |
| cinepi_controller.cpp:636-647 cp_stats JSON fields | CONFIRMED | framerate 637 ... framesInFlight 646, timestamp 647, cameraPort 648 |
| cinepi_controller.cpp:37-39 "+4.0 ms/frame ... disk queue never exceeded 2" | CONFIRMED | 37-39 |
| ccmpPreviewStage.cpp:158-165 "DETACHED THREAD PER REQUEST ... ~3 ms against a 20-40 ms frame period" + mutex_ | CONFIRMED | comment 158-164, `std::mutex mutex_` 165 |
| ccmpPreviewStage.cpp:175 kMaxCodeReportFrames = 120 | CONFIRMED | |
| ccmpPreviewStage.cpp:524-612 Process | CONFIRMED (minor) | Process starts 524 and runs well past 612 (report block to ~665); measureClamp 592; `ONE RENDER PER FRAME` comment 595-604; correctHighlightsInPlace 607 / render 609 |
| ccmpPreviewStage.cpp:550-557 BufferReadSync/BufferWriteSync "block on the DMA fence" | CONFIRMED | comment 550-552, rr 554, lw 555 |
| ccmpPreviewStage.cpp:592-603 "dropped frames at 4K" | CONFIRMED (minor) | the sentence is at 601-603 |
| ccmpPreviewStage.cpp:655-660 cost/frame info log | CONFIRMED | 655-660 |
| sharedContextStage.cpp:212-249 | CONFIRMED | Process 212-251; memcpy of PispStatsOutput 233; framerate 243; no pixel access, no timing log |
| mjpegPreviewStage.cpp:290-331 / 328-330 | CONFIRMED | class is `mjpegStreamStage` (Process 290-334); BufferReadSync 300; compressToJPEG 307; trace durations 328-330 |
| dualHdmiPreviewStage.cpp:583-617 | CONFIRMED | Process 583-617; BufferReadSync 607; composeAndShow 612 / publishSecondary 614 |
| cinemate/src/module/storage_profiles.py:52-73,156-171 | CONFIRMED | default-safe 51-60, ext4 61-73; recorder_profile_args 156-171 |
| storage_profiles.py:59,72,82,93 buffer_count | CONFIRMED | "8","8","10","10" |
| storage_profiles.py:63 encode_workers "4" (ext4) | CONFIRMED | all four profiles say "4" (53, 63, 76, 86) |
| storage_profiles.py:32-37 "~25 MB of CMA at 4K" | CONFIRMED | 36-37 |
| cinepi_multi.py:687-688, 693, 866 | CONFIRMED | --lores-width/height 687-688; --post-process-file 693; --buffer-count 866 |
| cinepi_multi.py:388-396 dual JSON | CONFIRMED | cfg dict 388-397 |
| cinepi_multi.py:590, 608-617 | CONFIRMED (minor) | fw,fh 590; `px, py = 94, 50` is at **609**, compute_preview_geometry at 616. NOTE 597-607: an attached HDMI's active framebuffer size OVERRIDES the configured 1920x1080 canvas, so the lores size is display-dependent |
| cinemate-install.sh:1359-1381 | CONFIRMED | post-processing.json 1359-1366 (port 8000), post-processing1.json 1375-1382 (port 8001) |
| sensor_detect.py:378-380, 483-493, 768 | CONFIRMED | constants 378-380; `lores_h = min(target_lines, ah, height)` 487, `lores_w = int(lores_h * desqueezed_aspect)` 488; OB-rows comment 767-768 |
| libcamera(cinemate)/src/libcamera/pipeline/rpi/common/pipeline_base.cpp:347-348 | CONFIRMED | stride/frameSize from V4L2 format |
| libcamera(cinemate)/src/libcamera/pipeline/rpi/pisp/pisp.cpp:235-253 computeOptimalStride | CONFIRMED | `libpisp::compute_optimal_stride(fmt)` 239; YUV420 Y stride = 2*stride2 at 247-249; bpl 251-253. libpisp is only a meson wrap (libcamera/subprojects/libpisp.wrap), not vendored |

Numbers recomputed (Q6): 3840 x 2 B = 7,680 B/row; x 2200 = 16,896,000 B (16.11 MiB) per raw buffer; x8 = 135,168,000 B (128.9 MiB); x6 = 101,376,000 B. 1280x720 YUV420 = 1,382,400 B; x8 = 11,059,200 B. 8+8 total = 146,227,200 B (139.45 MiB). Per request pair = 18,278,400 B (18.3 MB). 1256x720x1.5 = 1,356,480 B. All of the reader's figures reproduce. These assume stride == width*bpp with no libpisp padding (see unanswered).

### Block 3 — claim-level verdicts

| # | Reader claim | Verdict | Notes |
|---|---|---|---|
| 1 | Q1: requestComplete does only 2 SYNC_START\|READ ioctls, builds CompletedRequest (BufferMap+ControlList copy, Request::reuse), computes framerate, calls post_processor_.Process | CONFIRMED | one cite off by one (flags at :1225, not :1224) |
| 2 | Q1: PostProcessor::Process spawns one detached std::thread per frame; outputThread re-serialises via futures FIFO; inline path only when stages_ empty, never under Cinemate | CONFIRMED | "never under Cinemate" holds because ccmpPreviewStage.cpp is compiled into cinepi-raw (cinepi-raw/cinepi/meson.build:29@63a08d5), registers NAME "ccmpPreview" (ccmpPreviewStage.cpp:69, :681) and is force-inserted at cinepi_raw.cpp:57 |
| 3 | Q1: no thread copies the raw frame before encoding; encode worker reads the mmap'd camera buffer in place inside dng_save; 16-bit = per-row memcpy via write_pod | CONFIRMED | cites corrected: dng_save call 2239-2250; `DngEncoder started` 313 |
| 4 | Q2: ConfigureVideo(FLAG_VIDEO_RAW,0) is the only configure; alias_lores_to_video -> exactly 2 streams; stream0 bufferCount 6 default / --buffer-count; raw copies it; requests = stream0 count. Numbers 8/8/8 and 6/6/6 | CONFIRMED | makeRequests quote is at :1202 (cite said 1173-1200). "never --no-raw": grep of cinemate/src for `no-raw`/`no_raw` returns nothing (absence, CONFIRMED). `--lores-width/--lores-height` are unconditional in the args list (cinepi_multi.py:687-688) |
| 5 | Q2: buffers app-allocated from /dev/dma_heap/vidbuf_cached (system heap on Pi 5), one alloc+mmap per buffer per stream | CONFIRMED | |
| 6 | Q3: buffer pair returns when the last CompletedRequestPtr drops; holders = main-loop Msg, encode_buffer_queue_ (released after dng_save, before disk write), preview_completed_requests_[fd]; post-processor not a holder after outputThread posts | CONFIRMED, two refinements | (a) the main-loop Msg is a loop-body local (`CinePIRecorder::Msg msg = app.WaitFor(...)` at cinepi_raw.cpp:383) destroyed at the iteration's closing brace cinepi_raw.cpp:465@63a08d5, i.e. immediately after ShowPreview (:462) and BEFORE the next WaitFor — not "until the next WaitFor returns". (b) the preview holder exists only with a DRM/EGL preview. Cinemate's default is preview_enabled=True (cinemate/src/module/cinepi_multi.py:260,966@d6cc93e; main.py:901 calls `cinepi.start_all()` with no argument) so single-sensor launches pass `-p ox,oy,pw,ph` (cinepi_multi.py:807-808) and the DRM holder is real; dual-sensor passes `--nopreview` (cinepi_multi.py:806) and NullPreview::Show calls `done_callback_(fd)` synchronously (cinepi-raw/preview/null_preview.cpp:21@63a08d5), so the reference is released inside previewThread at once. input_done_callback_ -> encodeBufferDone binding: cinepi_recorder.hpp:42 |
| 7 | Q3 hazard: encodeBufferDone pops front regardless of which frame finished; 4 workers -> identity can be wrong (tearing), not a drop mechanism | PROBABLE (label honest) | Mechanism CONFIRMED in source: FIFO dequeue under encode_mutex_ (dng_encoder.cpp:2035-2036) but completion unordered; between dequeue and dng_save a worker may block on `ram_cv_.wait` (~2174) and, for every non-first frame of a take, on `clip_ceiling_cv_.wait_for(... seconds(2) ...)` (~2222-2224), so skew is plausible. Qualification the reader did not state: a wrongly released buffer is only overwritten when its re-queued Request reaches the CFE, i.e. after the requests already queued at libcamera drain (up to bufferCount-1 = 7 frame periods, ~280 ms at 25 fps); visible tearing therefore needs a worker skew of that order, and the window narrows precisely when the app is holding many buffers (encode backlog). Count-correctness (not a drop mechanism) CONFIRMED |
| 8 | Q4: chain ccmpPreview -> sharedContext -> mjpegPreview (+ dualHdmiPreview in dual mode); all stages run in the per-frame detached thread; indirect effects via outputThread FIFO, ccmpPreview mutex, BufferWriteSync fence | CONFIRMED | Order mechanics: PostProcessor::Read pushes stages in JSON key order (post_processor.cpp:26-41; boost ptree keeps file order), called from OpenCamera (rpicam_app.cpp:251-252, invoked at cinepi_raw.cpp:47); EnsureFirstStage then inserts at index 0 (post_processor.cpp:66) from cinepi_raw.cpp:57. Single-sensor file is /home/pi/post-processing{index}.json (cinepi_multi.py:644); dual file only `if self.multi` (:652-653) |
| 9 | Q4: per-frame stage work and logged cost (ccmpPreview one render/highlight pass + 120-frame cost line; sharedContext memcpy of stats; mjpegPreview libjpeg + trace timings; dualHdmi compose) | CONFIRMED | mjpeg class is `mjpegStreamStage`, registered as "mjpegPreview" (mjpegPreviewStage.cpp:70) |
| 10 | Q4 extra: main loop does one pipelined Redis round trip per frame in controller.process | CONFIRMED | |
| 11 | Q5: instrumentation list (11 items); no completion-thread duration or futures_ depth log | CONFIRMED with cite fixes | `Encoder configured` 1089-1091; `DngEncoder started` 313; encode-time debug 2300-2301. ADDED gating fact: items (2) and (3) are `console->debug`; spdlog's level is set only from the Redis key `log_level` (cinepi-raw/cinepi/cinepi_controller.cpp:190 GET at startup, :327-329 apply, :1060-1062 live), and nothing in cinemate writes that key (grep: only `set_log_level` which sets Python's own logging level, cinepi_multi.py:1344-1345, and a commented `# cinepi.set_log_level('INFO')` at main.py:929). PROBABLE (spdlog's library default level is info — not from these repos): under Cinemate the per-frame encode/disk-io timing lines are NOT emitted; the info-level lines (`DNG written`, ccmpPreview cost/frame, `RAM pool`, `Encoder configured`, `DngEncoder started`) are |
| 12 | Q6: 16,896,000 B per raw buffer; 135,168,000 B for 8; 1,382,400 B lores; 146,227,200 B total; strides via libpisp (alignment unknown) | PROBABLE (label honest); numbers CONFIRMED by recomputation | computeOptimalStride is applied to the raw stream (pisp.cpp:1227@bfe0b76), the CFE format (:1441) and each BE output (:1305), so both the 16-bit raw and the YUV420 lores strides go through libpisp. libpisp is only a meson wrap pinned to v1.2.0 (libcamera(cinemate)/subprojects/libpisp.wrap@bfe0b76), so the alignment remains UNKNOWN from these repos. Lores canvas caveat: an attached HDMI's active framebuffer size overrides the configured 1920x1080 (cinepi_multi.py:597-607), so 1280x720 assumes a 1080p display |
| 13 | Disk path: buffered open + POSIX_FADV_SEQUENTIAL + one write + close, no fsync, no DONTNEED | CONFIRMED | |

### Added (settled from source)

- A1. Lores 1280 vs 1256 (reader's unanswered #2): the Cinemate 7modes driver's 3840x2200 16-bit mode entry carries `.crop = { .left = 0, .top = 0, .width = IMX585_PIXEL_ARRAY_WIDTH, .height = IMX585_PIXEL_ARRAY_HEIGHT }` = 3840x2160 (imx585(cinemate-7modes)/imx585.c:787-798@bd57617; defines :220-221, TOP_4K=20 at :243); set_pad_format stores `*v4l2_subdev_state_get_crop(sd_state, 0) = mode->crop` (:1938) and get_selection returns it for V4L2_SEL_TGT_CROP (:2207-2209). The apertar branch's mode table has the same crop for that mode (imx585(apertar)/imx585.c:1185,1190-1195@e5b74d3; set_pad_format :2129). cinepi-raw's `mode-crop (l,t)/WxH` annotation that Cinemate parses is read from driver custom V4L2 controls, not from the selection API (cinepi-raw/core/driver_mode_metadata.hpp:187-226@63a08d5 VIDIOC_G_EXT_CTRLS/VIDIOC_QUERYCTRL; options.cpp:433-434, 473-480). PROBABLE: with a Cinemate driver branch the active aspect is 16:9 and lores = 1280x720 (1,382,400 B). Which driver branch is on the Pi, and whether its custom controls are exported, is not derivable here.
- A2. spdlog debug lines under Cinemate: see claim 11. Reader's unanswered #3 settled as PROBABLE-no.
- A3. Preview mode under Cinemate: single-sensor `-p` (DRM) by default, dual `--nopreview`; NullPreview releases synchronously (claim 6).
- A4. Main-loop Msg lifetime ends at cinepi_raw.cpp:465 (claim 6).
- A5. Hazard window for the out-of-order pop is bounded by libcamera's queued-request depth (claim 7).
- A6. computeOptimalStride covers raw, CFE and BE outputs (claim 12).

### Still unknown

- U1. libpisp stride alignment for the 16-bit raw and YUV420 lores (libpisp not vendored; wrap pins v1.2.0; GitHub fetch of raspberrypi/libpisp is not enabled for this session and is outside the listed repos). Note 7680 B is a multiple of 64, 128, 256 and 512, so any alignment up to 512 B leaves the raw stride at width*2; a stride rule that deliberately avoids power-of-two multiples (if libpisp has one) could still change it.
- U2. On-hardware durations of the detached stage thread, the Redis round trip and the 16-bit memcpy (no camera run).
- U3. Whether the out-of-order encodeBufferDone pop ever produces a torn DNG on the Pi.

### Cite corrections in one list

rpicam_app.cpp:1224 -> 1225; rpicam_app.cpp:1173-1200 -> throw at 1202; rpicam_app.cpp:706-711 -> quoted line 710; post_processor.cpp:44-67 -> 44-68 (insert at 66); dng_encoder.cpp:2240-2251 -> 2239-2250; dng_encoder.cpp:314 -> 313; dng_encoder.cpp:1079-1087 -> `Encoder configured` at 1089-1091; dng_encoder.cpp:2298-2301 -> log at 2300-2301; ccmpPreviewStage.cpp:524-612 -> Process continues to ~665; ccmpPreviewStage.cpp:592-603 -> sentence at 601-603; cinepi_multi.py:608-617 -> `px, py = 94, 50` at 609. Everything else exact.
