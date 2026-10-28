# Unverified after the speed-ramp port (2026-10-28)

Things that are built or assumed but not confirmed on hardware. Move an item to `lessons/hardware-log.md` when it is.

| # | What | Why it is open | How to settle it |
| --- | --- | --- | --- |
| 1 | **Auto ISO in IMX585 lossless stays under the cap (1600)** — *partly confirmed 2026-10-28: highest ISO seen 767 (Patrik)*; (Core `12c9075`) | Upstream forced manual ISO in lossless so the AGC could not pass the cap. Here the IMX585 default tuning (`/home/pi/Tuning-Files/defaults-pisp/imx585.json`, channel 0, normal mode) limits the AGC to gain 8 = ISO 800, read from the file, not measured. A different tuning file with a higher gain limit would let auto ISO pass 1600 and slow the lossless encoder. Other sensors are unchecked | Lossless take in auto ISO in a dark scene: `iso_actual` never above 800, `dropped_queue_full=0`. Try the `long` exposure mode (gain 12) too |
| 2 | **The stretched WAV sounds right** (`<clip>_stretched.wav`, Core `78c980d`, `6ea848b`) | Length (= frames / base fps) and pitch (1000 Hz test tone) are measured; how speech and music sound across ramp steps, and the ~25 ms smoothing inside re-timed stretches, are not heard. Resolve conform not tried | Listen to `C0022_stretched.wav` (a 25 → 30 → 25 ramp, small effect) or a new 1080p 25 → 50 → 25 take, under the clip on a 25 fps timeline |
| 3 | **4K SDR 12-bit at 50 fps** (T34 rung 2) | 3840x2076 lost ~12 % as capture gaps with 4 and 8 raw buffers, storage idle (`C0025`, `C0026`); cause unknown (sensor/CSI side?). 4K SDR stays capped at 30 | A longer test later (card full now); try 1 or 2 lower sizes and the 3840x2160 mode at 40-45 fps to find where gaps start |
| 4 | **Switch blink of a class change** (M1) | Only the command-to-reply time (45-110 ms) is measured, not the time to the first frame | M2: CFE timestamps around `set_clear_hdr` |
| 5 | **HDR16 vs SDR12 look at the same ISO/shutter** (M6) | Not graded | Two takes, grey card, in Resolve |
| 6 | ~~Hardware dials~~ **confirmed** 2026-10-28 (Patrik): ISO/WB below the first value → Auto, also in lossless | | |
| 7 | **Clear HDR 16-bit WhiteLevel at high gain** | Cinemate measured the merge clamping below 65535 at gain code 80 (~48600). Apertar writes a fixed level (`CdngEncoder.cpp:1373`); a take at ISO 1585 was never inspected | Take at ISO 1585 in HDR16, check highlights in Resolve |
| 8 | **`temp:` branch hazard** | `cinemate-port-temp`'s Clear HDR 16 → SDR 12 switch in `setFps` has no take check; with T31 it would reconfigure mid-take | Do not merge it back as it is |
