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
