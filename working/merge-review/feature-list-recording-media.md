# Feature list: Recording, files, audio, media and playback

Area: what the cinemate port added to original Apertar 1.6.0 in the write path, the files, audio, storage media and Core-side playback.
Sources: inventories CC-2, CC-3, Encoders-audio, Media-fault-tune, Media-buffer-split, Playback, App-1, App-3, `raw/FEATURES.json`, `fork-log.md`. Names of commands, routes, env vars and files were re-checked by grep in `/home/user/Apertar-Core` @cinemate-port `01f170c`.

"Stock camera" = a camera running `cinemate-port` with no config edits. Already done on the improvement branch (`/home/user/wt/core-work`), noted where it changes a default: `0977dd6` automatic storage pre-roll off by default; `615b48c` Lossy DNG drops its pages after the write again; `e4246ee` get_state sends `media_state` once; `05eaafa`/`b923c06` preview TDN limited to raw formats. The GPIO chip fix (`04fe197`) is in another area.

Relation words: extends in place / beside upstream / replaces upstream / new area. "Tested" quotes what commits and fork-log say. "Desk" = host test or Mac, no camera.

## Table

| # | Feature | Default for a stock camera | Relation to 1.6.0 | Tested |
| --- | --- | --- | --- | --- |
| 1 | Pulled-drive survival, media state, record gate | on | beside + replaces `stop()` join | Pi 2026-10-26 pull tests |
| 2 | Take durability: 1 s sync, writeback, DONTNEED modes | on (DONTNEED=sync) | new area | Pi pull test C0011 |
| 3 | Media profile, tuning file, `apertar-tune`, kernel tune | profile on, tune file absent, kernel tune off | extends + new area | built; mostly not run |
| 4 | Direct DNG payload write | on | extends in place | host test only |
| 5 | Raw copy hand-off and warm raw pool | on | beside / replaces | Pi 4K Clear HDR takes; pool syntax only |
| 6 | CineMate Log in the files | off | beside | Pi 16 to 12 once; not opened in Resolve |
| 7 | One black/white level for MLV and cDNG | on | moves + rewrites | host test only |
| 8 | Audio writer thread, 1 s fsync, drift fit | on | replaces | Pi (fit, pull test) |
| 9 | Speed ramp: audio, timecode, stretched WAV | ramp off; stretch on when ramp on | extends + new area | Pi 2026-10-28 |
| 10 | Clip name templates | default name unchanged | replaces naming code | host test only |
| 11 | Dropped-frame count, pre-roll mute | on | extends in place | Pi |
| 12 | RAM write buffer, buffer bar, safety stop | off (frames mode) | extends + new area | Pi 5 once 2026-11-01 |
| 13 | Storage pre-roll | auto on in the port; off on the branch | new area | Pi 5 2026-11-01 |
| 14 | Split takes, merge worker, `flatten_clip.py` | off (0); merge on | extends + new area | desk + Pi build |
| 15 | Drive trim | on | new area | Pi mount trim |
| 16 | Clip Browser facts and clip info (Core) | on | extends + new route | Pi 2026-10-29 |
| 17 | Frame as JPEG with histogram | on | new area (second decoder) | Pi 2026-10-29 |
| 18 | Playback hold, yielding downloads and deletes | on | beside + extends | Pi 2026-10-29 |
| 19 | Sound for the WebUI viewer | on | new area | Pi, Chrome only |
| 20 | Playback of every DNG size Core writes | on | beside | host test only |
| 21 | Web preview rate cap during a raw take | off (30 fps) | extends in place | not run |

Left to other areas (one line each at the end).

## 1. Pulled-drive survival, media state, record gate

- **Operator gets:** pulling or losing the recording drive ends the take with a named fault and a message instead of a hang, files up to the pull are kept, and record is refused with a reason when the medium is missing, dead or has under 1 GiB free.
- **How used:** nothing to switch. Touch UI and HDMI show MEDIA REMOVED or MEDIA ERROR; the WebUI reads `/api/state`. Gate off with `APERTAR_MEDIA_REQUIRE_MOUNT=0`.
- **Socket / HTTP:** event `media {state, mounted, device, fstype, free_bytes, total_bytes, errno}`; `record_start`, `capture_photo`, `timelapse_start` refused by the gate in `handleCommand`; `record_start` can fail with "previous take's writers are still blocked". `eject_media` and `mount_media` write and clear a flag file.
- **State:** `recording_fault` (`media_removed`, `media_full`, and others from `MediaFault.hpp`), `media_state`, `media_alive`, `media_device`, `media_fstype`; `media_class`, `media_profile` (feature 3).
- **Config / env:** `APERTAR_DEAD_MEDIUM_STOP_MS` (2000), `APERTAR_WRITE_STALL_MS` (5000), `APERTAR_MEDIA_REQUIRE_MOUNT`, `APERTAR_MEDIA_MIN_FREE_MB` (1024), `APERTAR_MEDIA_RUN_DIR` (`/run/apertar-media`); `[cfexpress_hat] enabled/bus/address` (section already existed in 1.6.0).
- **Touches in 1.6.0:** `CameraController::stop`, both `workerLoop`s, `failRecording`, H.264 finalize (extended or replaced: upstream joins every writer unconditionally); MLV, Lossy DNG and audio write error paths (abandon the queue on a dead medium); `ApertarCoreApp` state builders (upstream calls `isMountedPath` in each; now a watcher thread and `MediaProbe.hpp`). Beside: `MediaFault.hpp`, `MediaProbe.hpp`, `CfeHat.hpp` (third reader of the CFexpress I2C status byte, after the UI's `CfeAutomounter` I2cHat and a Python helper in App), `MediaIntent.hpp`. UI: `MediaStatusBridge::updateStatus`, `ApertarControlBridge` (UI `160898c`); `CfeAutomounter::handleSurpriseRemoval` (UI `dc471c1`).
- **Needs:** CFexpress slot bit needs the CFexpress HAT on I2C; Pi 4/CM4 case not tested. The eject flag has no reader: no code in Apertar-UI/src reads `/run/apertar-media/eject`, so it has no effect today.
- **Tested:** Pi 2026-10-26 pull tests (C0010, C0011 258 of 281 frames readable) found the bugs fixed in `a3ac8da`; `438a342` itself "desk only".
- **Commits:** `438a342` `e8bb1b7` `0b1632f` `a3ac8da` `70e8376` `3c4f07d`; UI `160898c` `dc471c1`.
- **For development:** a take can now end by three paths (user stop, safety stop, dead medium) and writers may be detached (`liveWorkers_`, `mediumGone_`); any new writer must honour the abandon rule and the watcher owns the media state, not the state builders.

## 2. Take durability: once-a-second sync, writeback, DONTNEED modes

- **Operator gets:** a pulled card or crash keeps a take up to about the last second; the sync no longer causes queue drops.
- **How used:** automatic. Tune with env or the media tuning file (feature 3).
- **Config / env:** `APERTAR_MEDIA_SYNC_MS` (1000, 0 = off), `APERTAR_DNG_WRITEBACK`, `APERTAR_DNG_DONTNEED=sync|writer|off`; tune keys `sync_ms`, `writeback`, `dontneed`. The `recording clip:` log line now ends with `dontneed= writeback= sync_ms=`.
- **Touches:** `CdngEncoder` page-cache handling (replaces upstream's unconditional `posix_fadvise DONTNEED` after each write with a process-wide gated mode), `CameraController` recorder (new sync thread, per-frame writeback; upstream has no fsync, syncfs or sync_file_range), `LossyDngEncoder` (has no sync thread, so `sync` acts as off; branch `615b48c` restores the per-file drop).
- **Tested:** Pi: C0004 clean, C0005 782 drops with syncfs, C0007 3 min clean, pull test C0011. `adac040` "not built on the Pi" when written; fork-log rows 140-142 record later builds.
- **Commits:** `4ce382e` `7d9dd60` `5b68f1f` `441e42a` `0ed07ea` `adac040` `766aba8` `48f8b8c`.
- **For development:** the sync thread and the DONTNEED mode form one contract with the writers; change a writer's flush order only with a pull test on the Pi.

## 3. Media profile, tuning file, `apertar-tune`, kernel tune

- **Operator gets:** writer count, queue depth and raw buffer count follow the mounted medium (ext4/exFAT 4/12/+0, FAT/NTFS 2/16/+2); a tuning file lets a tester change write-path knobs without systemd drop-ins; optional kernel tuning for the drive.
- **How used:** `~/apertar-media-tune.conf` (sections `[default]`, filesystem, class, class.fs; keys `dontneed`, `writeback`, `sync_ms`, `raw_buffers`, `extra_raw_buffers`, `workers`, `queue`, `kernel_tune`); RAM-only override `/run/apertar-media/media-tune.override.conf`; CLI `apertar-tune show|set KEY=VALUE [--section S]|unset KEY|clear|init [--from PATH]`. Kernel tune with `APERTAR_MEDIA_TUNE=1` or `kernel_tune=on`. Mounts made by Core carry `noatime`.
- **State:** `media_class`, `media_profile`.
- **Env:** `APERTAR_MEDIA_TUNE`; existing `APERTAR_RAW_CAMERA_BUFFERS`, `APERTAR_CDNG_UNCOMPRESSED_WORKERS`, `APERTAR_CDNG_QUEUE_FRAMES` now default from the profile.
- **Touches:** `rawCameraBufferCount`, worker count and queue depth in the recorder (extended in place; env overrides kept); `mountDeviceAtMediaPath` and the reinsert helper (noatime, `umask=0002`). Beside: `MediaProfile.hpp`, `MediaTune.hpp` (third config file with its own parser), `scripts/apertar-media-tune` (root helper via `sudo -n`, same pattern as upstream's two standby helpers), `config/apertar-media.sudoers`, `config/apertar-media.tmpfiles.conf`, `scripts/apertar-tune`.
- **Needs:** helper and sudoers installed by hand (`26da30e` "added but not installed"); the tune file path is hardcoded to `/home/pi`.
- **Tested:** `26da30e` "built, not tested"; exFAT row measured (C0106 lost 166 frames at 2/16/+2, C0101 held 10 min at 4/12/0); FAT, NTFS and other rows are starting points; `2edc6d0` built, Core not restarted at log time; `apertar-tune` desk only, on the Pi; the 46-check host test named in `MediaTune.hpp` is not in the repo.
- **Commits:** `26da30e` `0358fcf` `2edc6d0` `46d0e8c` `ebdcd08`.
- **For development:** this is a third config surface beside `camera_settings.conf` and `apertar-hardware.conf`; a developer adding a write-path knob must decide env, hardware file or tune file.

## 4. Direct DNG payload write

- **Operator gets:** fewer dropped frames on Clear HDR 16-bit: one `write()` per frame instead of a 16.6 MB copy plus 34 writes.
- **Used:** automatic. `APERTAR_DNG_PAYLOAD_COPY=1` forces the old path; `APERTAR_DNG_WRITE_ROWS` (1..4096, default 64) sets rows per write on the scratch path.
- **Touches:** `writeRawPayload` in `src/cdng/CdngEncoder.cpp`, extended in place with an early-return path beside the scratch path.
- **Tested:** host test byte-identical on six layouts (`tools/dng_payload_write_test.cpp`); no Pi timing under this hash.
- **Commits:** `e55557d`.
- **For development:** any change to the DNG header layout must keep both paths byte-identical; run `tools/dng_payload_write_test.sh`.

## 5. Raw copy hand-off and warm raw pool

- **Operator gets:** fewer capture drops on 16-bit takes (copy leaves libcamera's completion thread; new drop reason `copy-slot`); the first frames of a take no longer stall on 16.6 MB allocations.
- **Used:** automatic. Env `APERTAR_RAW_COPY_WORKERS` (1..2), `APERTAR_RAW_POOL_WARM`.
- **Touches:** `CameraController` capture-complete path (beside), the raw pool (replaces: no longer cleared at stop and start).
- **Tested:** copy hand-off on the Pi with 4K Clear HDR 16-bit takes; pool warm `4abbef0` syntax check only, no fork-log row.
- **Commits:** `fc7eb16` `43a54f3` `351a3ee` `db17860` `d9f00d4` `4abbef0` `0ed07ea`.
- **For development:** memory held across takes; budget changes interact with the RAM write buffer (feature 12).

## 6. CineMate Log in the files

- **Operator gets:** Log On/Off for cDNG, lossless JPEG and Lossy DNG: about 25 % smaller files (16 to 12 bit), the inverse stored in the DNG LinearizationTable, black and white stay linear.
- **Used:** WebUI Log switch; `set_cdng_log value=off|on`; `camera_settings.conf cdng_log`.
- **State:** `cdng_log`, `cdng_log_bits`, `cdng_log_available`, `cdng_log_applied`.
- **Touches:** `LossyDngEncoder` (beside its square-root companding), `CameraController` (beside `compressClearHdrFrame`, `planCdngLog`); new header `src/cdng/LogCurve.hpp`; generator `tools/gen_log_curve.py`.
- **Needs:** nothing extra. Touch UI reads `cdng_log_bits`.
- **Tested:** host golden tables; Pi 16 to 12 once, one frame 12,451,344 bytes, not opened in Resolve. Fork-log: "not yet run on the camera" at squash time.
- **Commits:** `d44b177`. (Port commit `56e135c` on the branch tells Log from Clear HDR 12-bit in clip info.)
- **For development:** the curve is a fixed table shared by encoder and the DNG tags; changing it changes every file written.

## 7. One black/white level for MLV and cDNG

- **Operator gets:** MLV files from 16-bit takes carry the right black level (about 3200, was 200); both formats of one take agree.
- **Touches:** `BlackLevel.hpp` (already on fork main; now holds `whiteLevel`/`blackLevelForEncodedDepth` that upstream kept as two private copies), `CdngEncoder.cpp`, `MlvEncoder.cpp`.
- **Tested:** `tools/black_level_test.cpp`; no camera test.
- **Commits:** `5e9dd1a`.
- **For development:** old MLV files differ from new ones; do not re-privatise the helpers.

## 8. Audio writer thread, one-second fsync, drift fit

- **Operator gets:** fewer audio dropouts when storage stalls; raw PCM synced each second so a pulled card keeps the audio; WAV drift correction from a least-squares fit over all block stamps; log lines `peak_backlog_kb`, `buffer_frames`, `points=`, `endpoint_ppm=`.
- **Used:** automatic. `APERTAR_AUDIO_BUFFER_MS` (100..4000, default 100).
- **Touches:** `AudioRecordingSession`, `TimestampedAudioCapture` (replace upstream's reader-writes-to-file and `snd_pcm_set_params` open; `finalizeWav` ratio replaced by the fit, thresholds 20..2000 ppm kept). On a yanked medium the raw PCM stays and the WAV is not finalised.
- **Tested:** `60ce8e9` built, not tested; pull test kept 5.02 s raw and the WAV recovered; fit -15 ppm over 6968 points on the Pi (C0013).
- **Commits:** `60ce8e9` `0358fcf` `b606c4f` `ebdcd08` `438a342` `e8bb1b7`.
- **For development:** Cinemate itself later retired the whole-take ratio method; this port still resamples.

## 9. Speed ramp: audio, timecode, stretched WAV

- **Operator gets:** WAV length and FreeRun timecode stay right when FPS changes inside a cDNG/MLV take; optionally a second WAV `<clip>_stretched.wav` that follows the slow motion with pitch kept.
- **Used:** `set_fps_speed_ramp` (with `audio=real|stretch`), `fps-ramp.txt` sidecar in the clip.
- **State:** `fps_speed_ramp_stretch_audio` (default on, takes effect only when the ramp switch is on).
- **Touches:** `observeVideoFrame`, the timecode call and Metadata struct (extended), `nextFrameIndex` numbering by count (extended). The stretch is new: detached `rubberband` process through `/bin/sh -c`.
- **Needs:** package `rubberband-cli` for the stretched WAV.
- **Tested:** Pi 2026-10-28 (C0030-C0032); stretch `ca7b7c2` "desk only" in its message, Pi in hardware-log.
- **Commits:** `d9f00d4` `faa2958` `ca7b7c2`.
- **For development:** the ramp switch itself belongs to the camera-modes area; this entry covers its effect on files and audio.

## 10. Clip name templates

- **Operator gets:** compose the clip folder name from tokens and free text with a live example; the default reproduces the old name byte for byte.
- **Used:** WebUI Settings Record, Clip names card (pill composer, drag and drop); `set_clip_name_template value=`, `preview_clip_name value=`; touch UI Clip names card (`606f137`, untested by hand).
- **State / config:** `clip_name_template`, `clip_name_example`; `camera_settings.conf clip_name_template`.
- **Touches:** `allocateClipFolder` / `reserveClipFolder(..., sensor)` in `CameraController.cpp` replace the inline `put_time` + `_C%04d` loop; new `src/util/ClipName.hpp` grammar.
- **Tested:** `tools/clip_name_test.cpp`; no Pi test.
- **Commits:** `014a2bf`.
- **For development:** the grammar is new; the folder name feeds playback, delete and the facts cache.

## 11. Dropped-frame count and pre-roll mute

- **Operator gets:** UIs show the running count of dropped frames instead of a bare "!"; pre-roll drops are not reported.
- **State:** `recording_dropped_frames` (state, record replies, recording events, `buffer` event).
- **Touches:** `RecordingDropWarning.hpp` extended (latch kept).
- **Tested:** Pi per fork-log row 139.
- **Commits:** `64bbbaa` `d44b177`.
- **For development:** every drop path must call the counter, including the new `copy-slot` reason.

## 12. RAM write buffer, buffer level and bar, safety stop, record during flush

- **Operator gets:** the write queue can be sized in bytes from free RAM instead of 12 frames; a red bar in the REC pill shows how full it is; at 90 % in RAM mode the take ends cleanly with every queued frame written; pressing record during that drain discards the old queue and starts at once with a toast.
- **Used:** Settings Frames / RAM buttons; `set_buffer_mode value=frames|ram`; `GET /api/buffer` (lock-free, WebUI polls ~4 Hz); `UI.conf frame_buffer_bar_enabled` via `set_frame_buffer_bar_enabled`; HDMI monitor item "Frame Buffer Bar".
- **State:** `buffer_used`, `buffer_capacity`, `buffer_fill`, `buffer_mode`, `buffer_unit`, `buffer_setting`, `buffer_note`, `buffer_safety_stop`, `buffer_stop_percent`, `buffer_flush_discarded`, `discarded_on_stop`; event `buffer`.
- **Config / env:** `[storage] buffer`, `buffer_ram_fraction` (0.6), `buffer_ram_floor_mb` (512), `buffer_ram_max_fraction` (0.5), `buffer_stop_percent` (90 in ram, 0 in frames); `APERTAR_CDNG_BUFFER`, `APERTAR_CDNG_QUEUE_RAM_FRACTION`, `APERTAR_CDNG_QUEUE_RAM_FLOOR_MB`, `APERTAR_CDNG_QUEUE_RAM_MAX_FRACTION`, `APERTAR_CDNG_BUFFER_STOP_PERCENT`.
- **Touches:** `DngRecordingQueue` enqueue/recycle/stop (extended; byte budget beside the frame limit, never below 12 frames); `record_start` aborts a flush before the command lock; new `BufferBudget.hpp`; process-wide atomics and a global `std::function` for the safety stop (upstream has no equivalent).
- **Tested:** host `buffer_budget_test` 28, `storage_buffer_conf_test` 64; Pi 5 2026-11-01 first safety stop at 1289 of 1424 MiB; `c5db8b2` no test, owner decision 2026-11-01.
- **Commits:** `d44b177` (squash of 19) `fb5801c` `c5db8b2`; UI `841d0ed` `4959513`.
- **For development:** the safety stop calls `record_stop` from its own thread; keep that path out of the command mutex.

## 13. Storage pre-roll

- **Operator gets:** a 2 s raw test take at the mode's top fps that is deleted afterwards, to warm the drive; blue PRE-ROLL pill.
- **Used:** button in Settings; `storage_preroll [seconds]`; `set_storage_preroll value=on|off`; `[media] preroll`, `preroll_seconds`; `APERTAR_STORAGE_PREROLL=0|1`.
- **State:** `storage_preroll_active`, `storage_preroll_auto`, `storage_preroll_auto_env`, `storage_preroll_fps`, `storage_preroll_last`.
- **Touches:** new thread and header `StoragePreroll.hpp`; `record_stop` and `format_media` changed; the take goes through the real recorder.
- **Stock camera:** in the port the automatic runs (Core start, card insert, format) are on, so a stock camera records a 2 s throwaway take at start. On the improvement branch (`0977dd6`) the automatic pre-roll is off by default; the button and command still work.
- **Tested:** host `storage_preroll_test` 53; Pi 5 2026-11-01 (hardware-log); the Clear HDR override not run.
- **Commits:** `d44b177`.
- **For development:** the pre-roll uses the live recorder; a change to the recorder's start path must keep the pre-roll exclusions.

## 14. Split takes, merge worker, `flatten_clip.py`

- **Operator gets:** a take can store frames in `<clip>/part_NNN/` every N frames (100..100000) to avoid the growing exFAT create cost; while idle Core merges split clips back into one folder; a script does it by hand.
- **Used:** Settings System Performance "Frames per folder"; `set_frames_per_folder value=0|100..100000`; `set_clip_merge enabled=true|false`; `python3 -I tools/flatten_clip.py <clip> [--apply] [--dry-run] [--unflatten N]`.
- **Config / env / state:** `[storage] frames_per_folder` (0), `clip_merge` (on); `APERTAR_CDNG_FRAMES_PER_FOLDER`, `APERTAR_CLIP_MERGE=0`; `frames_per_folder`, `frames_per_folder_env`, `clip_merge_enabled`, `clip_merge_env_off`, `clip_merge_pending`, `clip_merge_active`, `clip_merge_last`; files `part_NNN/` and `.parts`.
- **Touches:** frame path construction in `CameraController` (extended; new `FramePath.hpp`); the merge worker copies the trim worker's pattern (`ClipMerge.hpp`); playback reads parts in Core (`ClipFrames.hpp`, `ClipProbe.hpp`) and in the UI (new `src/ClipFrameFiles.hpp`, `cdngimageprovider.cpp`, `cliplistmodel.cpp`, `playbackcontroller.cpp`, UI `7ea9afc`).
- **Stock camera:** 0 means a stock camera never splits and nothing is merged.
- **Tested:** desk `frame_path_test` 34, `clip_merge_test` 23; Pi build rc 0; camera runs with `frames_per_folder=0` only; `ba0658d` "not yet run on the camera"; UI `7ea9afc` no run recorded.
- **Commits:** `d7dd337` `9ec37b5` `ba0658d` `68516f1` `01f170c`; UI `7ea9afc`.
- **For development:** every code path that lists, deletes, downloads or zips a clip must read both layouts; MLV and the pre-roll are never split.

## 15. Drive trim

- **Operator gets:** the recording drive is trimmed after a delete of 1 GiB or more and at mount, never during a take; journal lines show the result.
- **Used:** WebUI Settings "media trim" On/Off; `set_media_trim enabled=true|false`; `camera_settings.conf media_trim`; `APERTAR_MEDIA_TRIM=0`.
- **State:** `media_trim_enabled`, `media_trim_env_off`, `media_trim_last_result`, `media_trim_last_bytes`, `media_trim_last_ms`, `media_trim_last_unix`, `media_trim_running`.
- **Touches:** new worker thread in `ApertarCoreApp` plus root helper `scripts/apertar-media-trim` and `config/apertar-media-trim.sudoers` (call pattern as upstream's standby helpers, but upstream has no sudoers file in the repo).
- **Needs:** helper installed to `/usr/local/libexec/apertar-media-trim`, passwordless sudo for user `pi`.
- **Tested:** Pi trim at mount (927 GB in 0.47 s) on an earlier build; host `media_trim_test.sh` covers argument paths only.
- **Commits:** `d44b177` `00f2327` `ce0bd90`.
- **For development:** delete routes wait for the merge worker and set `mediaDeleteActive_`; trim must stay out of takes.

## 16. Clip Browser facts and clip info (Core side)

- **Operator gets:** each cDNG take in the WebUI list shows its own fps, duration, holes, recorded timecode, shot date, format and dropped count; the list is fast (first list 4.2 s, then 20 ms).
- **Used:** WebUI Clip Browser (WebUI part belongs to the WebUI area); `GET /api/media` (new item fields `playable`, `play_reason`, `format`, `fps`, `fps_fallback`, `first_number`, `last_number`, `missing_frames`, `empty_frames`, `ramp`, `token`, `timecode_start`, `has_audio`, shot-date fields, reply field `held`); `GET /api/media/clip?kind=folder&id=` (nine metadata rows plus SOUND, FORMAT, DROPPED, holes, cache token, audio URL).
- **Touches:** `discoverMediaLibraryItems`, `MediaLibraryItem`, `buildMediaLibraryJson` (extended; upstream's recursive scan stays as fallback); new `src/playback/ClipProbe.hpp`, `ClipFrames.hpp`, `DngTags.hpp`; cache keyed on the folder mtime plus the last part's mtime.
- **Tested:** Pi 2026-10-29; host 41 + 22 checks (`frames_test.cpp` lives in the KB, not the repo).
- **Commits:** `f91fafa` `ab4cc92` `d7dd337`.
- **For development:** upstream's media routes only listed, downloaded and deleted; the list now has a second source of truth (the cache).

## 17. Frame as JPEG with histogram

- **Operator gets:** the WebUI shows any frame of a take rendered in the touch UI's raw look, with a raw histogram.
- **Used:** `GET /api/media/frame?kind=folder&id=&n=&w=&v=` (w 320/480/640/960/1280/1920; 200/400/404/409/503; headers `X-Frame-Number`, `X-Frame-Index`, `X-Frame-Count`, `X-Histogram`, `X-Frame-Source`, `X-Decode-Ms`); `APERTAR_PLAYBACK_WORKERS` (2, clamp 1-4).
- **Touches:** nothing of 1.6.0 Core (it has no playback). Beside the touch UI's decoder (`dngdecoder.cpp`, `cdngimageprovider.cpp`): a Qt-free copy inside Core (`PlaybackFrames.cpp`, `DngFrameReader.hpp`, `RawRender.hpp`, `DecodeSlots.hpp`). New `third_party/liblj92`; `CMakeLists.txt` now `LANGUAGES C CXX`.
- **Needs:** vendored liblj92. About 92 MiB decode slots plus 32 MB caches.
- **Tested:** Pi 2026-10-29: 64-271 ms a frame, 0.8 ms cached; the 40.4 vs 24.5 ms buffer comparison was measured on x86.
- **Commits:** `1af26c8`.
- **For development:** two decoders now exist; a rendering change in the touch UI must be mirrored here or the pictures differ.

## 18. Playback hold, yielding downloads and deletes

- **Operator gets:** playback and downloads stop before the first frame of a take, photo, timelapse, media test, standby or eject; a delete from the WebUI waits for pending writes and record, photo and timelapse are refused with "Deleting media. One moment." while it runs.
- **Used:** automatic; WebUI folder button disabled in a take. Routes `GET /api/media/download`, `/download-selected` (409 in a hold, stream stops within a 64 KB chunk), `POST /api/media/delete`, `/delete-selected` (409).
- **State:** `playback_hold` in `/api/state`; list field `held`; internal `mediaDeleteActive_`.
- **Touches:** `handleCommand` (yield window opened for `record_start`, `capture_photo`, `timelapse_start`, `run_media_speed_test`, `enter_standby`, `eject_media`, `format_media`), the media watcher, `buildWebStateJson`, the download and delete routes (extended in place); `WebServer.cpp` gets 206, 409, 416 reason phrases; new `PlaybackHold.hpp`.
- **Tested:** Pi 2026-10-29: download stopped within 0.3 s of a take; 409/400 in a take; record during delete (Q23) not tested live.
- **Commits:** `f91fafa` `a37a902`.
- **For development:** any new long-running route must check the hold and yield; a take must never wait for a reader.

## 19. Sound for the WebUI viewer

- **Operator gets:** the viewer plays a take's WAV with seeking; the audio is the clock, mapped by frame number so takes with drops stay in step.
- **Used:** `GET /api/media/file?kind=folder&id=&name=<clip>.wav` (200/206/416, `Accept-Ranges`, 409 in a hold).
- **Touches:** new `streamFileRangeToClient`, `parseSingleByteRange` beside upstream's `streamFileToClient` (no range); reuses existing `wavFormatForFile`.
- **Tested:** Pi 2026-10-29 Range and 416 in Chrome; Safari, Firefox and phone not tested.
- **Commits:** `fa19856`.
- **For development:** only WAV names are served; widening the name check opens file download by path.

## 20. Playback of every DNG size Core writes

- **Operator gets:** IMX283 (5472x3648) and IMX294 (4144/4176 wide) clips open in the WebUI browser and viewer; before they were refused above 4096x3072.
- **Touches:** size gate in `src/playback/DngTags.hpp` with a 40 MiB per-slot assert; `tools/dng_limits_test.cpp` (not in CMake).
- **Tested:** host only; no Pi run for this commit.
- **Commits:** `618b2f1` (merge `4b2eeac`).
- **For development:** new sensors with larger frames need this limit and the decode-slot memory checked.

## 21. Web preview rate cap during a raw take

- **Operator gets:** the WebUI MJPEG preview can be capped or paused while a raw take runs, to reduce drops.
- **Used:** env `APERTAR_WEB_PREVIEW_RECORDING_FPS` (default 30 = unchanged, 0 = off); no UI.
- **Touches:** `captureWebPreviewFrame` path in `ApertarCoreApp.cpp` (extended).
- **Tested:** `fb557e9` syntax check, "not run on the Pi".
- **Commits:** `fb557e9` `766aba8`.
- **For development:** an env var only; if kept, it should become a setting.

## Seen in these units, main home is another area

- Lossless cDNG limits, max fps from the sensor probe, `iso_max`/`fps_max`, Clear HDR exposure rules and compression choice, IMX585 modes from tables, IMX283 family, binning in the state, mode ladder, phase lock, preview TDN, conform FPS: camera modes area.
- Boot Config card and fan mode through the config writer, `POST /api/config` through `HardwareConfigStore`, value lists and knob/button changes, one action vocabulary (`list_actions`), error replies with `code` and `revision`: hardware config and inputs area.
- WebUI Clip Browser and Viewer pages, Performance card, Clip names card layout, and touch UI buffer bar, pills and toast: WebUI and touch UI areas (only the Core-side contract is listed here).
- Build without libcamera (`5f5cea2`) and the host tests in `tools/` not wired into CMake: build area.
