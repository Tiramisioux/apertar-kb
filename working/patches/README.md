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

## Speed-ramp series (2026-10-27, on `cinemate-port`)

Written in a cloud session on top of `cinemate-port` as it is on GitHub: Core `7a545d9`, Apertar-UI `dc471c1`. Each patch applies
with plain `git am` in this order (checked in the cloud). **Not built on a Pi.**

| # | Patch | Repo | Tutorial | What | Host checks |
| --- | --- | --- | --- | --- | --- |
| 8 | `0001-camera-speed-ramping-FPS-changes-during-cDNG-MLV-tak.patch` | Core | T31 | `fps_ramp` setting: FPS changes during cDNG/lossy/MLV takes, count-based numbering, one `FrameRate`/timecode base per clip, WAV ended at the last frame's own duration, shutter policy `angle`/`exposure`, grace for the gap estimate and the phase lock, `fps-ramp.txt` per take, `set_fps_ramp` + `ramp_fps` stepper | `ApertarCoreApp.cpp`, `AudioRecordingSession.cpp`, `CdngEncoder.cpp`, `LossyDngEncoder.cpp`, `MlvEncoder.cpp`, `WebControlPage.cpp` syntax |
| 9 | `0001-camera-cap-4K-Clear-HDR-16-bit-at-25-fps.patch` | Core | T32 | 25 fps ceiling for 4K Clear HDR 16-bit in `tableMaximumFpsForResolution` and the WebUI's `maximumSupportedFpsForSnapshot` | `WebControlPage.cpp` syntax |
| 10 | `0001-web-speed-ramp-block-in-the-Recording-format-card.patch` | Core | T32 | Speed Ramp block under Bit Depth (On/Off, Shutter Sync, Ramp to … over …, ×2, Back) | `WebControlPage.cpp` syntax, `node --check` of the page script, Chromium against a mocked `/api/state` |
| 11 | `0001-ui-4K-Clear-HDR-16-bit-offers-FPS-up-to-25.patch` | UI | T32 | the touch UI's FPS list stops at 25 in 4K Clear HDR 16-bit | whole UI built with Qt 6.4.2 |
| 12 | `0001-ui-FPS-picker-sends-only-set_fps-during-a-speed-ramp.patch` | UI | T32 | in a ramp take the touch UI picker leaves the shutter to Core and saves nothing | whole UI built with Qt 6.4.2 |

Patch 8 replaces the first T31 patch, which was written for the cloud branch `clearhdr-fixes` (`d4ad539`). On `cinemate-port`
three things differ, and the tutorial says where: the session's `recordingBaseFps()` sits in the public section (no `friend`
line; `8f7dc39`'s pattern), the WAV end uses the latest frame's duration (`d9f00d4`), and `fps-ramp.txt` is written inside the
timed stop (`56d9137`). `CameraController.cpp` (patches 8 and 9) cannot be compiled off the Pi.

```bash
git -C ~/ApertarCore am ~/apertar-kb/working/patches/0001-camera-speed-ramping-*.patch ~/apertar-kb/working/patches/0001-camera-cap-4K-*.patch ~/apertar-kb/working/patches/0001-web-speed-ramp-*.patch
git -C ~/ApertarUI am ~/apertar-kb/working/patches/0001-ui-4K-*.patch ~/apertar-kb/working/patches/0001-ui-FPS-picker-*.patch
```
