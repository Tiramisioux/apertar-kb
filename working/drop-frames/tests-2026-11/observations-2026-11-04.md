# User's takes after evening 3 (2026-11-04, real use, not pre-registered)

Takes User made on the camera after evening 3, outside the test plan: no pre-registration, no take script, no 1 Hz log or
libcamera debug log. They are **measured by User** (the camera's own dropped-frames count) and **unscored**: they inform
the plan, they do not count toward a pre-registered rule or B6. Fields marked "unconfirmed" were not reported; fill them
in from the journal when the Pi is next on (`journalctl -u apertar-core --since <date> --no-pager | grep -E "recording
clip|ApertarCore tuning file|media tune"`).

| # | Mode | Length | Lost | WebUI | Tuning | Core | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| O1 | 4K Clear HDR 16-bit, 25 fps, uncompressed cDNG | 10 min | 0 ("a successful 10 min take") | **open** | unconfirmed (probably `imx585_clearHDR_notdn.json`, TDN off, selected in the touch UI as suggested; not reported) | unconfirmed (`9b5ea14` at the end of evening 3) | measured by User, unscored |
| O2 | 4K Clear HDR 16-bit, 25 fps, lossless JPEG cDNG | unconfirmed | **drops frames** | unconfirmed | unconfirmed | unconfirmed | measured by User, unscored |
| O3 | 4K SDR 12-bit, about 42 fps | unconfirmed | 0 ("without dropped frames") | unconfirmed | automatic (SDR loads `defaults-pisp/imx585.json`), unconfirmed | unconfirmed | measured by User, unscored |

## What they mean (probable unless marked)

- **O1** is the first 10-minute 4K HDR16 25 fps uncompressed take without a lost frame since A0 (2026-10-30, Core
  `a40112a`, TDN on, one take), and the first ever with the WebUI open (on 2026-11-01 an open WebUI added about 2 % of
  losses, `README.md` finding 6). If it ran with TDN off, it supports evening 3's result (`findings-2026-11-04.md` section
  1) under real use and over 10 minutes: the back end has its margin, and the residual single-frame losses of the TDN-off
  P1 test takes (1-2 per 3 min) were absent here. One take: it does not replace B6 (five 10-min takes on two boots).
- **O2** is expected: 4K Clear HDR 16-bit lossless JPEG encodes at about 17.5 fps (`estimated_capacity_fps` 17.2-17.8,
  5 workers, 281 ms a frame, 109 ms of it waiting; `README.md` finding 12), so at 25 fps the RAM buffer fills and frames
  drop. This is Core's encoder capacity, not the ISP back end. The ladder's rung 1 now reads ClearHDR16 <= 30 lossless
  (`handoff-drop-frames-tier1.md`, "State after evening 3"), which asks more than the encoder can give.
- **O3**: 4K SDR 12-bit runs at about 42 fps without loss, well above target 2's 33 fps (met on evening 3: 10 min lossless
  0 / 19,851, 10 min uncompressed 0 / 19,857, `findings-2026-11-04.md` section 3). The compression mode is unconfirmed:
  lossless at 33 fps had a pre-roll capacity of 48.13 fps (so 42 is inside it); uncompressed at 42 fps would write about
  12.4 MB x 42 = ~520 MB/s, close to the drive's derived ~550 MB/s, and heat it faster than the 72 C that 10 min at 33 fps
  reached. SDR12 has no 16-bit swap and no software stats, so its back-end threshold at 42 fps is about 23.4 ms (1000/42 -
  ~0.4) against an S2 of 9.6-12.9 ms at 33 fps (measured on evening 3): the back end has margin there too.

## To make them records

For each: the `recording clip:` line (`dropped_gap_estimate`, `enqueued`, `tune_override`), the `ApertarCore tuning file:`
line, the compression, the length, Core's commit, the drive temperature. With those, O1 and O3 can go into the hardware log
(after User confirms the reading) and O3 can extend target 2's record to the frame rate it reached.

## From the journal (evening 4 lead, 2026-11-04 20:15; measured from Core's log unless labelled)

The journal has two boots between evening 3's power-off and evening 4 (19:00:42, 19:46:52). Clips (all deleted when User
formatted the test card at ~20:10):

| Start | Clip | Compression | Frames | Core's `dropped_gap_estimate` at stop |
| --- | --- | --- | --- | --- |
| 19:00:45 | `cDNG_26_11_04_19004517_C0001` | lossless JPEG | (gone before 19:46) | none logged |
| 19:45:39 | `cDNG_26_11_04_19453901_C0001` | lossless JPEG | 237 | none logged |
| 19:46:56 | `cDNG_26_11_04_19465605_C0001` | lossless JPEG | (gone) | 1 |
| 19:47:02 | `cDNG_26_11_04_19470222_C0001` | lossless JPEG | 181 | 3 |
| 19:50:19 | `cDNG_26_11_04_19501918_C0001` | none | 124 | none logged |
| **19:51:24** | **`cDNG_26_11_04_19512403_C0001`** | **none** | **15,037 (601 s at 25 fps, 16-bit 4K)** | **1** (20:01:25) |
| 20:01:32 | `cDNG_26_11_04_20013201_C0001` | none | 447 | none logged |

- **O1 = the 19:51 take** (User, 20:16: peaking and zebra on; the WebUI open). Core started 19:46:53 on **`defaults-pisp/
  imx585_clearHDR.json (sensor default, pisp)`, the automatic tuning, TDN on**, and logged no tuning change after it: so O1
  ran with TDN **on**, not the TDN-off copy as guessed above (measured from the journal). Core counted 1 lost
  (`dropped_gap_estimate=1`); User's "a successful 10 min take" was the UI's reading (unconfirmed which counter it shows).
- No libcamera debug log, no trace events, no `/run` drop-in in that boot. Evening 3's TDN-on units (58-116 lost per 3 min)
  all ran with the RPi debug log (`RPI:0,RPiStream:0`) to tmpfs and the trace events; A0 (2026-10-30, TDN on, 10 min, clean)
  ran without them. **Unconfirmed hypothesis**: the instrumentation itself costs a large part of the margin with TDN on.
  Tonight's N unit runs with the log (pre-registered); an unlogged N take is proposed to User as an extra, unscored.
- O3 (SDR12 ~42 fps) is not in this journal window: no SDR12 clip after 19:00 (unconfirmed when it was taken).
