# Patches

Reference patches for the tutorials, written in a cloud session on 2026-10-26 from source. **Not built on a Pi** (no aarch64/libcamera build there); the tutorials have you type and build each step on the Pi. Apply with `git am` on the stated base if you prefer, then build and run the tutorial's checks. Each file is `git format-patch -1` of one commit on the Apertar-Core branch `clearhdr-fixes` (base `f60e301`), so every file is numbered `0001-`; the order below is the commit order and each patch assumes the previous one.

| # | Patch | Tutorial | What | Host checks |
| --- | --- | --- | --- | --- |
| 1 | `0001-camera-one-libcamera-request-per-raw-buffer-8-buffer.patch` | T23 | requests follow buffers, `kClearHdrBufferCount = 8`, `APERTAR_RAW_CAMERA_BUFFERS`, raw pool kept warm | none (libcamera) |
| 2 | `0001-cdng-direct-I-O-for-uncompressed-DNGs-IFD-first-layo.patch` | T24 | O_DIRECT uncompressed cDNG, IFD-first, page-aligned raw copies, `APERTAR_CDNG_DIRECT_IO`. **Amended 2026-10-26:** `#include <iostream>` was missing (caught by `g++ -fsyntax-only`) | `CdngEncoder.cpp` syntax |
| 3 | `0001-camera-copy-raw-frames-on-a-recorder-worker-not-on-l.patch` | T25 | copy worker, worker-side requeue, held ≤ buffers-2, `APERTAR_RAW_COPY_WORKERS` | none (libcamera) |
| 4 | `0001-camera-frame-rate-phase-lock-off-by-default-fps_phas.patch` | T27 | `FramePhaseLock.hpp` PI servo on BOOTTIME, pin after the photo merges, `set_fps_phase_lock`, stats, `APERTAR_PHASE_LOCK_LOG` | header: `tools/phase_lock_sim.cpp` 17/17 |
| 5 | `0001-media-survive-a-yanked-or-unmounted-recording-drive.patch` | T28 | `Media{Fault,Probe,Intent}.hpp`, media watcher thread, errno classes, clean stop, counted losses, `media` event, record gate, eject intent, WebUI | headers: `tools/media_probe_test.cpp`; `MlvEncoder.cpp`, `LossyDngEncoder.cpp`, `AudioRecordingSession.cpp`, `ApertarCoreApp.cpp`, `WebControlPage.cpp` syntax |
| 6 | `0001-media-profile-the-recording-medium-and-tune-the-writ.patch` | T29 | `MediaProfile.hpp` (connection class + filesystem → writer table), queue/workers/direct I/O/buffers follow the medium, root helper `scripts/apertar-media-tune` + sudoers/tmpfiles snippets, `noatime`, `media_class`/`media_profile` in state | header: `tools/media_profile_test.cpp`; `ApertarCoreApp.cpp`, `CdngEncoder.cpp` syntax; `sh -n` on the helper |
| 7 | `0001-audio-writer-thread-and-a-one-second-capture-ring-on.patch` | T30 | audio writer thread + RAM queue, 1 s ALSA ring with 10 ms period (`APERTAR_AUDIO_BUFFER_MS`), negotiated sizes and peak backlog logged | `AudioRecordingSession.cpp` syntax; `TimestampedAudioCapture.cpp` needs `alsa/asoundlib.h` |
| – | `0001-imx585-report-each-mode-s-sensor-window-as-its-crop-.patch` | T26 | imx585-v4l2-driver `apertar` @ `e5b74d3`: per-mode `.crop` in native sensor pixels | none (kernel) |

Patches 4–7 were amended on 2026-10-26 after the workflow's critic pass (phase-lock pin without a `settings_` read, env gains, saturation detection and state telemetry; device-node and NVMe-state checks and a cached snapshot in the media probe; helper after the abort, APST knob). `working/port-raw/critic.md` lists what was folded in and what was left as a stated limit.

`CameraController.cpp` is touched by 1, 3, 4, 5 and 6 and cannot be compiled off the Pi (libcamera headers are generated at build time); every anchor in those hunks was taken from the file at the stated base, and the tutorials build after each step so a slip surfaces at the step that made it. The driver patch is independent of the Core series.

Branch on the Pi: `git -C ~/ApertarCore checkout -b clearhdr-fixes f60e301 && git am ~/apertar-kb/working/patches/0001-camera-one-*.patch ...` in the table's order.
