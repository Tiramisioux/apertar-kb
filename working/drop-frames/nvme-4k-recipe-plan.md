# NVMe campaign plan: the best 4K recipe with the fewest writes (plan of 2026-11-07, not started)

Goal (User): find the best recipe for 4K shooting on the NVMe, i.e. how long a take can be, at which fps, with which Apertar and
mount/storage settings. Target 30 min. Dropped frames are the main concern, so **every take ends at the first dropped frame, at buffer
full (Core's 90 % RAM-buffer safety stop) or at 30 min**. Writes to the NVMe are to be kept low: a ladder starting at the highest fps,
smart fps steps, and early ruling out of options that make no difference.

Modes (all three the User named): **4K Clear HDR 16-bit**, **4K Clear HDR 12-bit**, **4K SDR 12-bit**.
Runner: `working/tools/longtakes.py` (extended, see section 9). Labels: measured / probable / unconfirmed.

## 1. What the earlier campaigns taught (and what the plan does about it)

| Lesson | Source | Consequence in this plan |
| --- | --- | --- |
| On the NVMe every 16-bit drop was a **capture gap** (CFE had no free raw buffer; ISP back end behind), the queue peaked at 2 of 12, no write failures. The drive was not the limit at <= 30 fps. | first NVMe run (git `242c0be`) | Decide **per mode and per fps what limits it** (capture-gap vs buffer-full) and test only options that act on that limit. |
| **Time to first drop falls smoothly with fps** (baseline 30 fps 2 s, 29: 3, 28: 4, 27: 6-8, 26: 8-213, 25: 27-453 s) on the earlier board. | same | Do not walk 1 fps at a time: **fit log(T) against fps** from the first two failures and jump to the fps predicted to reach the target time. |
| **Log** stores 16 -> 12 bit (Clear HDR 16-bit) or 12 -> 10 bit (12-bit modes), so smaller files, but the **conversion runs on the CPU** in the cDNG copy worker. In the first NVMe run Log on failed within 2-3 s at every fps although it writes fewer bytes, which fits a CPU cost, not a storage one. The User: the CPU seems to be the 4K limiter, so the cost of Log is worth knowing either way. Core's code applies it only to unpacked 16-bit raw streams; the User says it also applies to the SDR modes, so Core decides per mode. | first NVMe run; `planCdngLog` in Core; User 2026-11-07 | Log is **not ruled out**: it is tested **on top of the winning options** in every mode, in both directions (fewer bytes versus more CPU), with Core's CPU measured per take. |
| TDN adds ~37 ms back-end work per frame (frame time 40 ms); lossless JPEG at 4K Clear HDR 16 encodes at ~17.5 fps. | recipe rows 2, 7 | **Ruled out in theory, never recorded**: TDN everywhere; lossless on 16-bit. |
| Did not help: dirty-page tuning alone, sub-folders, creating files ahead, preallocation, writer thread count, 16 raw buffers, a large RAM write buffer, slowing the touch UI's preview, moving GPU interrupts. FE config queue depth 4 helped a lot (25 fps: 74 s -> 453 s). `dontneed=writer` lost 34-153 frames per 3 min. | recipe sections 2-3 | All of these **excluded a priori**; depth 4 and `dontneed=sync` stay fixed. |
| The USB SSD: `workers`, `queue`, `sync_ms`, `kernel_tune` made **no difference** (3 repeats each, two modes). The limit there was **per file** (12.4 MB frames ~18 fps, 3.1 MB frames ~38 fps) far below the drive's 354 MB/s. | SSD campaign | Storage knobs are tested as **one combined stack**, not one by one; the real storage levers are the structural ones (filesystem, file size, direct I/O). |
| Cinemate: exFAT write() blocks for hundreds of ms under DNG pressure; "ext4 drops less" (new DNG file every frame = directory-entry churn); per-filesystem raw-buffer counts (ext4 8, exFAT 10); 1 MB exFAT clusters helped latency but break macOS. | cinemate-lessons | Filesystem (exFAT vs ext4) is the main **mount option** worth testing, and only if a mode is storage-limited. |
| A hard throughput ceiling shows as a **pool fill after a fixed time**, not scattered drops. | cinemate-lessons | `buffer_full` is its own result and ends the take. |
| An untrimmed NVMe stalls after ~0.9 TB written; >75 % full slows it; the second take after a cold take differs. NVMe controller dropped out twice in October (cause unconfirmed; boot args did not stop it). | drop-frames README, hardware-log | Core trims after deletes (already on); **start temperature and drive fill logged**; a **watchdog** stops the campaign on any NVMe/PCIe error and waits for the User. |
| Results drifted by ~3 fps over hours on the SSD. | SSD campaign | **Control takes** (plain baseline) at the start of each stage and every 8 takes; an option only counts if it beats the **baseline's own spread**. |
| `eject` powers a USB drive off; the automounter wants the label `NVME-RAW` / `RAW`; Core's `mount_media` works. | SSD campaign | Never eject; drive swap and relabel are User steps. |

## 2. Rates and capacity (arithmetic, DNG bytes per frame measured or derived)

| Mode | MB/frame | MB/s at 25 / 30 fps | Mode max fps | 30-min take at 25 / 30 fps |
| --- | --- | --- | --- | --- |
| 4K Clear HDR 16-bit | 16.90 | 422 / 507 | 30 | 760 / 912 GB |
| 4K Clear HDR 12-bit | 12.44 | 311 / 373 | 30 | 560 / 672 GB |
| 4K SDR 12-bit | 12.44 | 311 / 373 (50 fps: 622) | 60 | 560 / 672 GB (50 fps: 1.1 TB, more than the drive) |

NVMe direct writes reached 733-759 MB/s (T22), so 4K SDR 12-bit is storage-possible up to ~57 fps; 4K Clear HDR is limited by the mode
(30) and by capture, not by the drive. The drive is 932 GB: a 30-min take fits up to ~41 fps for SDR 12-bit; above that "until the
drive is full" counts as the pass and the minutes reached are the result. SDR 12-bit above 30 fps is the one place where this drive
may be the limit. (derived)

## 3. Wear budget (the reason for the ladder)

Deleting and trimming do not wear the drive; **writing does**. Cost of a take that passes (HDR16 at 25 fps): 1 min 25 GB, 5 min 127 GB,
10 min 253 GB, 20 min 507 GB, 30 min 760 GB (HDR12/SDR12 at 25 fps: 19 / 93 / 187 / 373 / 560 GB). A take that fails costs only what was
written before it failed (seconds to minutes). The plan is built so that only survivors pay for long takes.

| Stage | Writes, expected (worst case, all pass) |
| --- | --- |
| 0 calibration | 45 GB |
| 1 edge finding, 3 modes | ~1.5 TB (2 TB) |
| 2 screening at the edge | ~0.9 TB (1.5 TB) |
| 3 stacking | ~0.6 TB (1 TB) |
| 4 ladder 10 / 20 / 30 min (3 + 2 + 1 survivors per mode) | ~3 TB (7 TB) |
| 6 soak (2 x 30 min of the final recipes) | ~1.5 TB |
| **Total** | **~4-7 TB expected, hard cap 8 TB** |

The runner keeps a byte counter (files x average file size) and **projects the cost of the next take before it starts**: a take that
would exceed the cap is skipped and the campaign stops with a report. Rated endurance of the Corsair MP600 Mini has not been looked
up (typical 1 TB consumer drives are rated in the hundreds of TBW, so 8 TB would be a percent or two; unconfirmed). To read the
drive's own counter the User runs `sudo nvme smart-log /dev/nvme0` before and after (the runner cannot, no root).

## 4. The ladder: 1, 5, 10, 20, 30 minutes, survivors only

Round | take length | who goes in
--- | --- | ---
1 probe | 60 s | the edge search of each mode (cheap: failing takes stop at the first drop)
2 | 5 min | the probe's edge fps, bracketed
3 | 10 min | at most 3 configs per mode (the stack, the plain baseline, the runner-up)
4 | 20 min | at most 2
5 | 30 min (or until the drive is full) | the best 1

Each round finds the **highest fps that passes** with a bracket search: start at the previous round's best (the top fps in round 1),
after a failure go down by the amount a fit predicts, otherwise 3, 6, 12 fps, then bisect between the highest pass and the lowest
failure (`bracket_search`, tested offline). **Smart steps:**
- capture-gap failures: fit log(T) = a - b x fps on the failed takes so far (T = seconds to the first drop) and jump to the fps where the
  fit reaches the round's target, minus one fps;
- buffer-full failures: jump to `fps x (enqueued - queued at the stop) / enqueued` (+10-35 %), the fps the drive actually wrote;
- failures already on file are reused after a restart.
**A pass ends the search downward (User, 2026-11-07):** once a config passes at some fps in a round, nothing lower is ever tested for it
in that round, and the next round starts from that fps. The only extra tests after a pass are in the gap *above* it (between the highest
pass and the lowest failure, which the 3/6/12 steps can leave). In the 60 s and 5 min rounds that gap is bisected down to 1 fps (cheap);
in the 10, 20 and 30 min rounds it is **left alone once it is 2 fps or less**, so a long take is not spent on a 1 fps refinement: the
result is then right to within 1 fps.
Only **25 fps and above** count as survivors; a config that cannot reach 25 fps at the probe is ruled out without testing 25 if the
fit says it is far below.

## 5. Ruling out options (so nothing is recorded that cannot change the result)

1. **By theory (section 1):** TDN, lossless on 16-bit, 16 raw buffers, depth 2, `dontneed=writer`, thread counts, preallocation,
   sub-folders etc. are never tested. Lossless on the 12-bit modes stays (it shrinks files; unmeasured encoder speed).
2. **By cause:** the probe says per mode whether it is **capture-limited** or **storage-limited** (buffer_full). Capture-limited:
   test the capture options only. Storage-limited: test the storage options and the filesystem only. Both: both.
3. **By result:** each option is run **paired and interleaved** against the plain baseline at the fps just above the baseline's clean
   fps (where outcomes vary), 3 repeats + control takes, 90 s cap, stop at the first drop or buffer full. The metric is the time to stop.
   *Better* = median at least 2x the baseline's median and above the baseline's best control; *worse* = the mirror;
   **otherwise "no difference" and the option is dropped** from every later stage for that mode. The spread is measured from the
   control takes, not assumed.
4. **Group testing** for the storage knobs (`workers`, `queue`, `sync_ms`, `kernel_tune`): one combined variant versus the baseline; if it
   shows no difference all four are dropped at once; if it helps, halve the set to find which one.
5. **Stacking, not a grid:** greedy forward selection (add the best option, re-test, add the next, stop when nothing helps), at most 4
   rounds. No 2^n combinations. **Log is never part of the screening; it is tried on the finished stack** (section 7, step 3b), because
   it trades bytes for CPU and its effect depends on what the rest of the stack already uses.
6. **Same frame size only** for the buffer-full frontier (HDR12 and SDR12 share 12.44 MB: once SDR12 hits buffer full at R MB/s,
   HDR12 at or above R is skipped). Capture-gap results do not transfer between modes.
7. **Simplest wins:** at equal result the config with fewer switches stands in for the tie.

## 6. The options, grouped by how they are applied

| Group | Options | How | Who |
| --- | --- | --- | --- |
| **A. between takes, no restart** | Log on/off (on the winning stack only; whether it applies is checked per mode, see step 0), phase lock, WebUI client (a real client on the Mac), trim on/off, `kernel_tune` (pi-nvme class: dirty 1 GiB / 256 MiB, scheduler none, nr_requests 512, APST 0), writer `workers`, `queue`, `sync_ms`, compression (12-bit modes only) | Core commands, the tuning override file, the root helper called directly | runner |
| **B. needs a Core restart** | FE config queue depth {4 (default), 6}, `dontneed` {sync (default), off}, `writeback` {on, off}, capture thread priority {off, SCHED_FIFO for libcamera's completion thread, whole process under `chrt`}, direct I/O for the DNG writes if the build has the switch (to verify in code first) | runner writes the value to a small file that `start-apertar-core.sh` reads, then pauses with the exact command; the User runs `sudo systemctl restart apertar-core`; the runner checks `/proc/<pid>/environ` | User |
| **C. needs sudo, a remount or a reboot** | HDMI/touch UI stopped (`apertar-ui-direct`), exFAT mount flags, **filesystem exFAT vs ext4 (format: wipes the drive; a Mac cannot read ext4)**, PCIe Gen 3 vs Gen 2 (`config.txt`, 437 MB/s at Gen 2), `nvme.max_host_mem_size_mb` boot argument (untested) | commands staged by the runner, run by the User | User |

Group B and C values are changed **in a few batches** (one restart per value, 3 repeats each, only the paired edge test), so the User
is asked for about 6-8 restarts in total, not one per take. Group C comes last and only when a mode was storage-limited.

## 7. Order of the run

0. **Calibrate** (after the SSD campaign ends and the drive is swapped back): identify the NVMe, PCIe link and class, temperature, free
   space, a 60 s direct-write test (~45 GB), media tune values in effect. **Log probe:** for each of the three modes switch Log on and, if
   Core reports it as not applied, make a 4 s take and keep Core's own reason from the journal (already built into the runner).
1. **Edge finding per mode:** probe round (60 s), then the 5-min bracket. Output: the highest fps with 60 s and 5 min clean, and the
   limiter (capture or storage).
2. **Screening at the edge** (group A, then B in batches), paired and interleaved, with control takes.
3. **Stacking** of the options that helped.
3b. **Log on the winning stack**, in every mode where Core applies it: paired and interleaved against the stack without Log at the edge
   fps (3 repeats, 90 s cap, plus controls), reading both the time to stop and **Core's CPU use** (average, peak, busiest thread) from
   the per-second samples. Three possible outcomes, all worth knowing: Log helps (fewer bytes win), Log hurts (the CPU cost wins), no
   difference. Only a Log stack that wins goes into the ladder as an extra candidate; a loser is recorded and costs no long take.
4. **Ladder** 10 -> 20 -> 30 min for the stack, the plain baseline and the runner-up.
5. **Mount/filesystem session** (group C) if any mode is storage-limited: the best stack re-run at two fps with each variant.
6. **Soak:** the final recipe of each mode twice at 30 min (repeatability and drift).

Mode order: 4K Clear HDR 16-bit first (the hardest target), then 4K SDR 12-bit, then 4K Clear HDR 12-bit last, using the SDR 12-bit
buffer-full frontier to skip what is hopeless.

## 8. What the User gets

- **Duration-versus-fps table per mode and per recipe:** for each fps from the top, the longest clean take seen (seconds to the first
  drop, buffer full, or 30 min) and the cause when it ended. This answers "how long a take can I make at this fps with this recipe".
- **What Log costs and buys per mode:** the change in the clean fps at the edge, the change in file size, and the change in Core's CPU
  use (average and peak, and which thread is busiest), next to the same numbers without Log.
- The **recommended recipe** per mode (switches, tuning values, environment) with the evidence that each switch matters, and the list of
  switches shown to make no difference.
- Writes used (GB, against the cap) and the NVMe temperature at the start and the peak of every take.
- Everything in `longtakes.db` (takes, per-second samples, drop events, Core counters, raw journal lines) and the KB findings page.

## 9. What has to be built before the first take (small, on top of the SSD runner)

Reused as is: stages and pruning, `bracket_search`, the smart step, buffer-full classification from the stats line, the tuning override
and the `kernel_tune` helper call, the database, the Mac WebUI client, mode switching, audio handling, resume.
New:
1. The three modes, no storage exclusion, NVMe temperature (hwmon `nvme`) already read.
2. A 60 s probe round and the **log(T)-versus-fps fit** for capture-gap failures. (**Already built for the SSD run:** the Log probe take
   with Core's own reason, and Core's CPU per second and per take: sum over threads in % of one core, and the busiest thread; both in
   `results.csv`, the per-second samples and `longtakes.db`.)
3. A **write-budget guard** (byte counter, projection before each take, cap, report).
4. **Control takes** and **spread-based "no difference"** (replacing the 2x-baseline rule's single sample).
5. **Group testing** of the storage knobs and the **greedy stacking** stage.
6. The **restart-batch protocol** for group B (a small env file read by `start-apertar-core.sh`, a `NEED_RESTART` message, verification of the
   process environment) and staged commands for group C.
7. An **NVMe watchdog**: stop on any `nvme`, `pcie` or `exFAT` error in the kernel log or `media_alive` false; never retry automatically.
8. The duration-versus-fps report, written into `results.md` and the KB.
9. Tests offline for the fit, the budget guard and the neutrality rule before anything runs on the Pi.

## 10. Open points for the User (defaults chosen)

- "Aperture options" is read as the **Apertar settings** (the switches above). Tell me if aperture/iris means something else.
- Wear cap **8 TB** (default); change it if the drive's rating says otherwise.
- ext4 and a Gen 2 link are optional last steps; they are only worth doing if a mode turns out storage-limited.
- Start after the SSD campaign has finished (about 21:00 today) and the NVMe is back in; it needs the label `NVME-RAW` or `RAW`.
