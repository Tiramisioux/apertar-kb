# The recipe: fewer dropped frames in Apertar at 4K Clear HDR 16-bit (as of 2026-11-04)

A summary of the drop-frames campaign (2026-10-26 to 2026-11-04) for the owner and anyone who builds on it. Every row links
back to the page where it was measured. Status words: **measured** (counted on the camera), **probable** (inferred, reason
given), **unconfirmed**. Rig throughout: Pi 5 / CM5 4 GB, IMX585, NVMe (Corsair MP600 Mini) as exFAT on `/media/RAW`.

**Where it stands.** 4K Clear HDR 16-bit uncompressed records clean at **25 fps** and, in 3-minute takes, at **28 fps**
(one clean take; not yet shown over 10 minutes). **30 fps without dropped frames is not reached**: with every measure
below it still loses about 3 frames in 2 minutes (2026-11-04, evening 4).

## 1. The starting analysis: how Apertar writes DNGs, and what turned out to be true

How Core records a cDNG take (read from the source, `README.md` section 2):

- The sensor's frames arrive through the **CFE** (the Pi 5's camera front end) into one of 8 raw buffers. libcamera then
  sends each frame through the **ISP back end**, which makes the preview picture (HDMI, touch UI, WebUI, peaking, zebra).
  Core copies the raw buffer into a write queue and hands the buffer back; writer threads write the DNG files.
- **The DNG is the raw CFE frame.** Nothing the ISP back end does (denoise, colour, preview size) changes the recorded
  pixels. This is what makes it safe to make the preview cheaper.
- A 4K 16-bit frame is 16.9 MB, so 25 fps is ~420 MB/s and 30 fps ~510 MB/s, through the same memory as the ISP.

What was found to hold (each measured unless marked):

1. **A frame is lost in one of four places, and each needs a different cure**: the write queue is full (the drive fell
   behind), the copy slot is busy, the CFE had no buffer when the frame arrived (a capture gap), or a request could not
   be re-queued. Every measurement starts by saying which counter moved. (`README.md` section 1, 2026-10-29)
2. **The drive is fast enough; its state is what matters.** Direct writes reach 733 MB/s. A trimmed drive takes a
   10-minute take clean. An untrimmed drive that has written ~0.9 TB stalls for seconds, and a drive that is ~80 % full
   slows down. (2026-10-26, 2026-10-30)
3. **The hard limit at Clear HDR 16-bit is memory traffic, not the drive.** Memory load alone, with no recording, makes
   the ISP back end slow enough to lose more than half the frames. (evening 2, 2026-11-03, `findings-2026-11-03.md` §1)
4. **Frames are lost when the CFE has no free raw buffer**: user space holds all 8 because frames queue up in front of
   libcamera's single-threaded back end. (2026-11-02, `findings-2026-11-02.md` §1)
5. **More buffers do not cure it.** 16 raw buffers lost more frames, not fewer: the extra buffers fill up too.
   (2026-11-03)

## 2. The measures that helped

Only the measures that removed or reduced dropped frames. Later rows were measured with the earlier ones in place.

| # | Problem | What it meant for recording | Measure | Effect (what it improved) | Established |
| --- | --- | --- | --- | --- | --- |
| 1 | Clear HDR 16-bit ran with too few raw buffers in flight | Short 25 fps uncompressed takes lost frames now and then | **8 raw camera buffers, one request per buffer** (T23) | 25 fps uncompressed: 5 of 5 short takes clean (4 of 5 before); the write queue never builds (measured, 10-s takes) | 2026-10-26 |
| 2 | Lossless JPEG at 4K Clear HDR 16-bit encodes at only ~17.5 fps | At 25 fps the queue fills behind the encoder: 20-35 % of frames lost | **Record Clear HDR 16-bit uncompressed** (the ladder rung for HDR16 should be uncompressed) | 25 fps uncompressed: 0 lost on the same build (measured) | 2026-10-26 (encoder speed measured 2026-11-01) |
| 3 | A `syncfs` of the whole drive once a second made the writers wait for everything in writeback | 782 frames lost to a full queue plus 12 capture gaps in 3 min | **Per-DNG writeback hint plus a once-a-second `fsync` of each finished file** instead of `syncfs` | 0 lost in 3 min (4494 frames); a pulled card keeps everything but the last second | 2026-10-26 / 27 |
| 4 | The NVMe was never told which space was free (no trim) | After ~0.9 TB of writing the drive stalls for seconds: 18-77 % of frames lost; at worst the drive hangs until a reboot | **Trim the drive.** Core now trims by itself when the drive is mounted and after big deletes (927 GB in 0.47 s) | Trimmed before every run: 12 of 12 clean; a 10-minute 25 fps take 0 of 15,001 lost (measured). Side effect: deleted takes cannot be recovered | 2026-10-30 (automatic trim 2026-10-31) |
| 5 | A nearly full drive slows down | 77-81 % full: 166-676 frames lost in 3 min | **Keep the drive well below ~75 % full; format between shoots** | A fresh format removed the losses (probable: the drive's write cache shrinks as it fills) | 2026-10-26 |
| 6 | Core told the kernel to drop each DNG's pages while they were still unwritten (`APERTAR_DNG_DONTNEED=writer`, the old default). That freed nothing, filled the page cache and made the kernel reclaim ~13 GB per 3 min | 34-153 frames lost per 3 min, growing with uptime; it looked like the touch UI's fault | **`APERTAR_DNG_DONTNEED=sync`**: drop the pages after the once-a-second `fsync`, when they are clean. Now Core's default | 3-min takes 0 and 0 lost; a 10-minute take 25 lost (0.17 %, the drive 97 % full); memory reclaim fell ~60x (measured) | 2026-11-01 |
| 7 | The preview's **temporal denoise (TDN)** made the ISP back end read and write a full reference frame for every frame: ~37 ms of work per frame, longer than a 25 fps frame lasts | At 25 fps the back end fell behind and stayed there: 39-116 frames lost per 3 min | **Preview tuning with TDN off** (`imx585_clearHDR_notdn.json`, made with `tools/tdn_strip.py`; spatial denoise stays on). DNGs unchanged; preview noise judged acceptable by the owner (2026-11-04) | Back-end job 37 ms -> 6 ms; 25 fps: 0-2 lost per 3 min instead of 39-116 (probable, n = 2 + 2 units). Raised the clean ceiling from 25 to 27 fps | 2026-11-04 (evening 3) |
| 8 | libcamera keeps only 2 FE configuration buffers in flight; when one comes back late (memory bursts), the next frame cannot start | Single frames lost every minute or so at 28 fps, even with TDN off | **FE Config queue depth 4**: a copy of libcamera's PiSP pipeline file with only `"num_cfe_config_queue": 4` changed, given to Core through `LIBCAMERA_RPI_CONFIG_FILE` | 28 fps, 3 min: 0 of 5,055 lost at depth 4, while the take's late buffers would have cost 4 frames at depth 2; depth 2 lost a frame at 36 s (probable, n = 1 + 1; by the pre-registered rule still inconclusive) | 2026-11-04 (evening 4) |

Row 3 (`b606c4f`) is on `cinemate-port`; row 1 (T23) came with the same `clearhdr-fixes` work (its commit is not named
here). Rows 4 and 6 are only on Core's local `drop-frames` branch, which is what runs on the camera (`9b5ea14`). Rows 7 and 8 exist only as files on the camera and in this KB. Row 5 is how the drive is
used.

## 3. What did not help (so it is not tried again)

Dirty-page tuning (2026-10-26); sub-folders, creating files ahead, preallocation and the number of writer threads
(2026-10-30); 16 raw buffers instead of 8 (2026-11-03); the large RAM write buffer (`buffer=ram` against `frames`) as a
cure for capture gaps (2026-11-03); slowing the touch UI's preview during takes (not monotone, 2026-11-03); moving the
GPU interrupts to another core (2026-11-01).

## 4. What limits 30 fps (probable, 2026-11-04)

At 30 fps with every measure above, the losses are not late FE config buffers: none came back later than four frame
periods, and no frame started late. Instead the back end slows: its job time rises (median 11.9 against 7.5 ms at 28
fps; slowest tenth 24.7 against 12.5 ms), 27 % of its jobs have to wait (3 % at 28 fps), and Core's write queue nearly
fills (11 of 12). The first suspect is memory bandwidth at ~510 MB/s of raw data. Not yet tried against it: Log
(16-bit stored as 12, ~25 % fewer bytes), direct I/O for the DNG writes (no page-cache copy), a smaller preview output
from the ISP while recording.

## 5. What it would take to ship rows 7 and 8

- **TDN off (row 7)**: no new switch is needed. The touch UI (Settings, Tuning File) and the WebUI already select a
  tuning file. To ship it, the TDN-off copy has to be installed next to the defaults in `/home/pi/Tuning-Files`, so the
  selector lists it.
- **Config queue depth 4 (row 8)**: not a UI switch. libcamera reads the file once, when Core opens the camera, so
  changing it needs a Core restart. The way that matches Apertar: `scripts/start-apertar-core.sh` exports
  `LIBCAMERA_RPI_CONFIG_FILE` the same way it already exports `LIBCAMERA_RPI_TUNING_FILE`, pointing at a pipeline file
  Core ships. Before it becomes the default: a check in SDR modes, and the second clean depth-4 take the rule asks for.
- **The ladder** (operator setting, no code): rung 1 for Clear HDR 16-bit should be uncompressed, at most 28 fps. On
  2026-11-04 it read Clear HDR 16-bit up to 30 fps, lossless.

## Sources

`README.md` (sections 0-3), `night-2026-11-01.md`, `lessons/hardware-log.md` (2026-10-26 to 2026-11-01),
`tests-2026-11/findings-2026-11-02.md`, `findings-2026-11-03.md`, `findings-2026-11-04.md`,
`findings-evening4-supervised-2026-11-04.md`, `preregistration.md`.
