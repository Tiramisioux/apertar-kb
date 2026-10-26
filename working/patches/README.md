# Patches

Reference patches for the tutorials, written in a cloud session on 2026-10-26 from source. **Not compiled** (no aarch64/libcamera build there); the tutorials have you type and build each step on the Pi. Apply with `git am` on the stated base if you prefer, then build and run the tutorial's checks.

| Patch | Base | Tutorial | What |
| --- | --- | --- | --- |
| `0001-camera-one-libcamera-request-per-raw-buffer-8-buffer.patch` | Apertar-Core `f60e301` | T23 | requests follow buffers, `kClearHdrBufferCount = 8`, `APERTAR_RAW_CAMERA_BUFFERS`, raw pool kept warm + `reserveRawPool` |
| `0001-cdng-direct-I-O-for-uncompressed-DNGs-IFD-first-layo.patch` | on top of the T23 patch | T24 | O_DIRECT uncompressed cDNG, IFD-first, page-aligned raw copies, `APERTAR_CDNG_DIRECT_IO` |
| `0001-camera-copy-raw-frames-on-a-recorder-worker-not-on-l.patch` | on top of the T24 patch | T25 | copy worker, worker-side requeue, held ≤ buffers-2, `APERTAR_RAW_COPY_WORKERS` |
| `0001-imx585-report-each-mode-s-sensor-window-as-its-crop-.patch` | imx585-v4l2-driver `apertar` @ `e5b74d3` | T26 | per-mode `.crop` in native sensor pixels |

Order for Core: T23 → T24 → T25 (each patch assumes the previous one). The driver patch is independent.
