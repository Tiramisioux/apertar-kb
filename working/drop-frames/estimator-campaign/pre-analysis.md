# Pre-analysis: sustained frame rate per mode, NVMe and SSD (2026-11-21)

Written before the warm-drive block P6 and the ladder block P4 are in; the full analysis replaces this. Labels:
**measured** (a take shows it), **derived** (computed from measured numbers), **probable** (the best reading of the
evidence), **unconfirmed**.

Data used:
- NVMe, Corsair MP600 Mini on the CFE hat:
  - estimator set `EST-05fb8f1-a`: 143 probes of 60 s on clip-split 05fb8f1, single sensor, mic attached (P0, P1, P1b, P2) and 12 validation combinations (P3);
  - the clip-split 7e6e2a3 set `est`: 56 probes;
  - the NVMe nights' 3-, 5- and 15-min takes (S2, S4, ARMS; `../nvme-campaign/findings.md`).
- SSD, Samsung T7 over USB (2K modes only, older build b755383, `../ssd-campaign/README.md`): nights 1-2, including 30-min takes, split and flat.

Raw: `../nvme-campaign/run-20261110/est-05fb8f1-a/` (probes.jsonl, validation.jsonl, estimate.md / estimate-table.csv).

## 1. The table

Capacity = what the 60-s probe sustained at the reference levers (TDN off, lock off, WebUI on, audio on, aids on):
- **cap**: the rate the writers kept up with, taken from the RAM buffer's fill slope or Core's write stats;
- **delivered**: frames that reached the recorder per second, when frames were lost before it.

Sustained = what a long take holds. The table rounds down for the ~2 fps a warm drive costs.

| Mode / format | NVMe 60-s capacity (measured) | NVMe long take (measured) | Limited by | Drops came from | Expected sustained NVMe | Expected sustained T7 SSD |
| --- | --- | --- | --- | --- | --- | --- |
| 4K HDR16 uncompressed | 28 clean; 30: 51-65 dropped | 27-28 carried 3+5 min; 15 min: 27, 26 dropped at 708/621 s, 25 buffer full at 758 s | back end at 30, warm drive at 25-27 (~420-470 MB/s) | capture gaps at 30; buffer full from warm-drive pauses after ~10 min | 27 up to ~10 min; **no 15-min fps found yet** (<= 24 probable, P6 tests 27/26) | ~6 (derived: 105 MB/s / 16.6 MB) |
| 4K HDR16 uncompressed + Log | 25.5-26.3 delivered | 25 carried 3+5 min | back end (Log costs ~40-50 % Core CPU) | capture gaps (95-260/min at 28-30) | 24-25 (derived) | ~6 |
| 4K HDR16 lossless | 14.6-15.5 | 25: buffer full at 12-13 s | encoder (CPU ~190 %) | buffer full | **14** (derived) | ~10 (derived, ~10 MB/frame) |
| 4K HDR16 lossless + Log | 30 "fit", but 240-526 dropped | out at 25 | back end + encoder | capture gaps (240-500/min) | ~14 (probable; the 30 reading is wrong, see 4) | ~10 |
| 4K HDR16 MLV | 27-28 | - | storage / back end | buffer full, capture gaps | ~26 (derived) | ~6 |
| 4K HDR12 uncompressed | 26.0-26.5 delivered | S2: dropped at every fps 25-30 within 2-93 s | back end | capture gaps (200-230/min at 30) | **<= 24** (probable; nothing held 3 min) | ~8 |
| 4K HDR12 lossless | 30 "fit", 121-268 dropped | - | back end | capture gaps | ~24 (probable) | ~12 |
| 4K HDR12 MLV | 23.4-26.2 | - | back end | capture gaps, buffer full | ~23 | ~8 |
| 4K SDR12 uncompressed | 40.5-49.9 (cold 520-580 MB/s) | 38: buffer full at 95-800 s; **37 passed 15 min** | storage (~460-475 MB/s warm) | buffer full | **37** (measured, 15 min) | ~8 (105 MB/s / 12.4 MB) |
| 4K SDR12 lossless | 40.8-42.3 | 43 passed 3+5 min (S2, 7e6e2a3) | encoder (CPU ~200 %) | buffer full | 40 (derived; P6 tests) | ~18 (derived, ~5.7 MB/frame) |
| 4K SDR12 lossy 3:1 | 37.9-40.8 | - | encoder (CPU ~230 %) | buffer full | 37 (derived; P6 tests) | ~30 (derived, 3.5 MB/frame) |
| 4K SDR12 lossy 5:1 | 43 | - | encoder | buffer full | 41 (derived) | ~41 (encoder, 2 MB/frame fits) |
| 4K SDR12 MLV | 25.7-26.0 at 311-316 MB/s | - | MLV writer (one file, CPU 69 %) | buffer full | ~25 (probable) | ~8 |
| 4K SDR10 uncompressed | 43.8-46.6 | - | back end / storage | buffer full, capture gaps | ~43 | ~10 |
| 4K SDR10 lossless | 45.6-47.4 | - | encoder | buffer full | ~45 | ~20 |
| 4K SDR10 lossy 3:1 / 5:1 | 41 / 44 | - | encoder | buffer full | 39 / 43 | ~35 / ~43 |
| 4K SDR10 MLV | 10.8-11.1 at 116-120 MB/s | - | MLV writer | buffer full | **unconfirmed** (11 looks wrong: SDR12 MLV does 26) | - |
| 2880x2160 crop SDR12 uncompressed / lossless | 53 / 59 | - | storage / encoder | buffer full | 51 / 56 (derived) | ~11 / ~24 |
| 4K ProRes HQ (standard colour) | 28.2-29.3 delivered | - | encoder (CPU ~340 %) | ProRes queue full + capture gaps | **27** | 27 (derived: ~88 MB/s at 30, under the T7's 105) |
| 4K ProRes HQ ARRI LogC4 | 42.4-43.8 delivered | P3 at 46: dropped | encoder | capture gaps, ProRes queue | ~40 (unconfirmed why it beats standard HQ) | same |
| 4K ProRes 422 / LT / Proxy | 41.5 / 43.8-44.9 / 47.2-47.5 | - | encoder (CPU 220-300 %) | capture gaps | 40 / 43 / 45 | same |
| H.264 2560x1440 | 47.1-47.5 delivered | - | encoder (CPU ~210 %) | capture gaps (~750/min at 60) | 45 | same |
| H.264 1920x1080 | 60 clean | P3 with TDN + lock: dropped at 60 | sensor (60) | with TDN on: capture gaps | 60 (TDN off) | 60 |
| 2K HDR16 uncompressed / lossless / Log / MLV | 30 (the mode's top) | - | sensor | none | **30** | uncompressed ~18 (measured meter); lossless 27 passed 30 min (measured) |
| 2K SDR12 uncompressed | 60 | - | sensor | none | 60 | **32** (measured, split, 4 x 30 min) |
| 2K SDR12 lossless / lossy / MLV | 60 | - | sensor | none | 60 | lossless 48 passed 30 min (measured); lossy ~60 (derived) |
| 2K ProRes HQ / 422 / Proxy | 60 | - | sensor | none | 60 | 60 |
| 2K ProRes LT | 59.95 (1 gap) | - | sensor | one capture gap | 60 (probable) | 60 |

All NVMe capacities are measured on 05fb8f1. The SSD column is derived for 4K: the T7 sustains ~100-105 MB/s during
takes (measured) and was never tested in 4K.

## 2. Switches (levers): what they cost

P2 ran a 16-run design (2^(5-1)) on three anchors: back end (HDR16 uncompressed at 28, twice), encoder (HDR16
lossless at 25) and storage (SDR12 uncompressed at the top). Effects are mean(on) - mean(off), derived.

| Switch | Back end (capture gaps per minute) | Encoder / storage | Reading |
| --- | --- | --- | --- |
| **TDN (preview temporal denoise)** | **+288** (both repeats agree; noise SE 13) | "+0.25 / +0.32" on log capacity | **The one lever that matters.** It costs about 290 lost frames a minute at the HDR16 edge. The positive capacity number is probably an artefact: frames lost before the recorder never reach the writers, so the buffer fills more slowly and the meter reads high. |
| Phase lock | +24 to +31 | +0.12 storage, ~0 encoder | A small cost at the edge (about 2 SE). |
| Preview aids (peaking + zebra) | -47 to -58 | ~0 | Fewer gaps with the aids on (unconfirmed why); no reason to turn them off. |
| Audio recording (WAV) | +4 to +14 | +0.09 storage | Small. |
| WebUI connected | +9 to +39 | ~0 | Small; the second back-end run reads higher. |
| TDN x aids | -39 to -48 | -0.06 | The largest interaction; it partly offsets TDN. |

## 2b. When each switch matters

Read from the lever design's 48 takes, split by what limits the mode (P2). The anchors:
- **back end**: 4K HDR16 uncompressed at 28, about 1 fps under its edge;
- **encoder**: 4K HDR16 lossless at 25, above its capacity of 15;
- **storage**: 4K SDR12 uncompressed at 60, above the drive.

Plus the 12 validation takes and the first-block probes. "Clean" = 0 frames dropped in 60 s.

| Switch | Matters when | Doesn't matter when | Evidence |
| --- | --- | --- | --- |
| **TDN** | **Any 4K sensor mode**, every format, any distance from the edge. With TDN on, 0 of 24 design takes were clean, against 16 of 24 with it off. 4K HDR16 at 25 dropped 173 frames (about 3 fps under its edge). 4K HDR16 at 23 and 4K HDR12 MLV at 23 dropped. Even H.264 1080p, which reads the 4K sensor, dropped at 60. | **2K**: every TDN-on take at 2K was clean (5 of 5). That covers SDR12 uncompressed at 60, lossy 5:1 at 60, ProRes 422 and Proxy at 60, and HDR16 lossless + Log at 23. | measured. Mechanism probable: the preview denoise runs in the ISP back end on the 4K input, and its time pushes the back end past the frame period; frames are then lost before the recorder, and Core's CPU *falls* (147 % vs 221 %) because less arrives. |
| **Phase lock** | Only within about 1 fps of a **back-end edge** (4K HDR16 at 28 with TDN off): 7-24 gaps per minute on against 1-4 off, and the takes that dropped 6-67 frames had it on. | Encoder-limited (HDR16 lossless: 8 of 8 clean with TDN off, lock on or off). Storage-limited (the buffer fills at the same rate). 2K. | measured, small n (4 + 4 per anchor) |
| **Audio recording (WAV)** | The same as the lock: near a back-end edge, +3 to +25 gaps per minute. One extra writer thread, about 10 % more Core CPU at the edge. | Encoder- or storage-limited, 2K. | measured, small n |
| **WebUI connected** | Near a back-end edge: +6 to +15 gaps per minute. | Elsewhere. | measured, small n |
| **Preview aids (peaking + zebra)** | Near a back-end edge it *helps*: fewer gaps with the aids on (0-9 against 8-19 gaps per minute). | Elsewhere. | measured; why unconfirmed (the aids may change the preview's path or rate) |
| **Log** (a format setting, not a lever) | 4K HDR16: about -2 to -3 fps and capture gaps (uncompressed 28 -> 25-26; lossless + Log drops hundreds a minute). | 2K HDR16: Log at 30 is clean. | measured |
| **Split (frames_per_folder 5000)** | Long cDNG takes: on any drive past t* = 1.9e6 / fps² seconds flat (50 min at 25 fps, 14 min at 48, 9 min at 60). On the T7 already at 2K 32 fps for 30 min. | MLV, ProRes and H.264 (one file); short takes. | measured (T7) + derived |

**In one line:** in 4K, TDN off is the rule; it decides clean or not at any fps. The other switches only count within
about 1 fps of a back-end edge (4K HDR16, 4K HDR12, 4K Log). There, lock, audio and WebUI each cost a few frames a
minute and the aids help a little. When the drive or the encoder limits the mode, only the fps and the format count.
At 2K, nothing measured here matters.

## 3. What caused the dropped frames

| Cause | Where it shows | Mechanism | Label |
| --- | --- | --- | --- |
| **Capture gaps** | 4K HDR12 (all formats), HDR16 at 30, any Log in 4K HDR16, 4K ProRes and H.264 1440, everything with TDN on | Frames never reach the recorder: the ISP / back end / copy path cannot keep the sensor's rate. Core CPU 250-340 % in those probes. | measured (counters); mechanism probable |
| **Buffer full** (Core's 90 % safety stop) | uncompressed SDR at the drive's limit, lossless and lossy in 4K, MLV | The writers (drive, or the compression CPU) are slower than capture; the 1.1 GiB RAM buffer fills in 8-17 s at 60 fps. | measured |
| **Warm-drive write pauses** (NVMe) | every 15-min take that failed (HDR16 25-27, SDR12 38), at 10-13 min | Once warm (72-78 °C) the drive stops taking writes for ~2 s; at 450 MB/s that is ~900 MB, which fills the buffer. The 1-min write rate stays flat. Thermal throttle or garbage collection: unconfirmed. | measured (samples); cause probable |
| **ProRes queue full** | 4K ProRes HQ at 60 | The encoder's own queue. | measured |
| **exFAT folder walk** (flat folders) | T7 30-min flat takes, NVMe prognosis | Each new file walks the folder: 0.32 µs x files already in it. A flat folder slows a long take until it stops; the 5000-frame split removes this. | measured (T7, NVMe probe) |
| Copy-slot drop at a part boundary | T7, 1 event (3 frames) | `mkdir` of the next part folder on the copy thread | probable, rare |
| Frame-number jump | T7, 1 event | Timestamp numbering, not a lost frame | probable, rare |

## 3b. The split take: why it works, and what it costs

**What it does.** With `frames_per_folder` = N (5000 by default), Core writes a take's frames into part folders
`part_001`, `part_002`, ... of N frames each, inside the clip folder. After the take the merge worker moves them back
into one folder (the merge is on), so the clip looks like a plain cDNG folder again.

**Why a flat folder fails a long take (measured on the T7 and in the NVMe probe; the formula is derived).**
- exFAT keeps a folder's entries in a list, with no index. Creating a file walks the whole list to check the name,
  under the file system's lock: W(n) = 0.32 µs x n, where n is the number of files already in the folder. The same slope
  was measured on both drives (317 ns NVMe probe, T7 S3).
- In a flat take n grows with time (n = fps x t), so the walk's share of the frame budget grows as
  s(t) = 0.32 µs x fps² x t. The campaign's rule is that a flat folder holds while s < 0.6. That gives
  t* = 1.9e6 / fps² seconds:
  - 50 min at 25 fps
  - 31 min at 32 fps
  - 14 min at 48 fps
  - 8.8 min at 60 fps
  - 3.2 min at 100 fps
- On the T7 this showed exactly. Core CPU climbed from 52-57 % to 125-131 % over flat 30-min takes, and two of three
  stopped at 29 min. With the split, CPU stayed at 50-58 % for 4 x 30 min, the buffer peaked at 7 %, and all were clean
  (measured).

**Why the split fixes it (derived).** No folder holds more than N files, so the walk is capped at 0.32 µs x N
= 1.6 ms per file at N = 5000. At 32 fps that is 5 % of the frame budget; at 60 fps about 10 %; at 100 fps 16 %. Each
part folder starts empty, so the cost no longer grows with the take's length.

**What it costs.**
- *A part boundary* every N frames: the next part folder is created (`mkdir`) on the copy thread. On the T7 one
  boundary out of ~40 stalled long enough (behind 30 queued UAS writes) that all six copy slots were busy, and 3 frames
  were refused (probable, n = 1). A fix, not built yet: create part k+1 from a writer thread, or ahead of time when part
  k starts.
- *The merge after the take*: 342 s for a 30-min 2K take of 45,000 frames (measured). The per-file time grows with the
  main folder, because the merge's moves walk the same list (0.8 ms per file early, 7.6 ms average). During a merge the
  campaign waits; a new take during a merge competes with it for the drive.
- *Deletes*: a folder with parts deletes in about linear time per part. A flat 30,000-frame folder took 157 s to
  delete on a cold drive (measured, NVMe EST day).

**On the NVMe in 4K (measured / probable).**
- 4K takes at 25-40 fps reach N = 5000 in 2-3.5 min, so a 15-min take has 4-7 parts.
- The 15-min failures were not at part boundaries. They came at 10-13 min as warm-drive pauses, with the buffer
  jumping from 0 to 700-900 MB within 2-3 s, so they are a drive effect, not a folder effect.
- The flat 30-min controls (S6) never ran: no mode passed 30 min with the split first. So "when does 4K need the split"
  is still derived only. At 4K's 25-40 fps the walk alone would allow 20-50 min flat, but the 4K CPU load (190-340 %)
  leaves less headroom than 2K had.

**Rule kept:** split at 5000 for every cDNG and lossy DNG take; MLV, ProRes and H.264 write one file per take and
don't need it.

## 4. Known errors in the estimator (why P3 met 6 of 12)

- The 60-s probes see a cold drive. Long takes on NVMe lose about 2 fps (SDR12: 39 -> 37) and more at HDR16 (measured).
- Lossless or lossy at the 4K HDR edge ("4kHDR16 lj:log 30", "4kHDR12 lj 30"): the fit reads 30 while hundreds of frames dropped. Delivered frames should cap it: model bug, probable.
- TDN combinations are overestimated: 3 of the 6 misses had TDN on (HDR16 unc, HDR12 MLV, H.264 1080 at 60). The model adds levers as main effects, and TDN's real cost on the back end is larger than its capacity term says.
- The MLV SDR10 reading (11 fps) and ProRes LogC4 beating standard HQ: unconfirmed, to check against the raw takes.

## 5. Recommendations (best setup per use)

**Always:**
- TDN off while recording (the biggest single cause of lost frames).
- Split at 5000 frames, merge after the take.
- Phase lock only when you need it.
- Leave aids, audio and WebUI as you like.

| Use | NVMe (MP600 Mini) | T7 SSD |
| --- | --- | --- |
| 4K, best image, long takes | HDR16 uncompressed at 24-25 for takes under ~10 min; for longer takes wait for P6 | not possible (6 fps) |
| 4K HDR, longer takes | SDR12 uncompressed at 37 (15 min proven) as the SDR fallback; HDR16 lossless only to 14 | - |
| 4K high frame rate | SDR12 lossless 40 / lossy 5:1 41 / crop 2880x2160 lossless 56 | lossy 5:1 ~41 (derived) |
| 4K delivery codecs | ProRes HQ 27, ProRes 422 40, ProRes LT 43, Proxy 45; H.264 1440 45 | same (encoder-limited) |
| 2K | everything at the mode's top (HDR 30, SDR 60) | SDR12 lossless 48, uncompressed 32 (split), HDR16 lossless 27 |

## 6. For the full analysis

- P6 (running tonight): 15-min warm takes at the estimate and one below for six modes. This is the warm-drive correction.
- P4: the Mode Ladder with these thresholds (27 / 40) switching modes on fps changes (running).
- Model fixes: cap the capacity at delivered frames when frames drop; give TDN its back-end term; the warm penalty from P6.
- Check against the raw takes: MLV SDR10, ProRes LogC4, the aids effect's sign.
- The SSD in 4K: the column above is derived only (the user accepts the older build's SSD data).
