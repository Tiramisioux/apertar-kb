# Cinemate lessons learned — git history and handbook, applied to the three ports

Read 2026-10-26 for the phase-lock, yank-robustness and storage-media work. Sources: `cinemate@d6cc93e`
(1611 commits), `cinepi-raw@63a08d5` (408), `cinemate-handbook@c99ff77` (102; the "LLM manual":
`orientation/*`, `conventions/philosophy.md`, `lessons/what-the-pi-taught-us.md`, `lessons/hardware-log.md`
with 84 dated entries). Commit bodies were read in full for every commit cited; handbook pages were read
in full except `hardware-log.md`, which was read by section. Each lesson ends with **→** what it changes
in our deliverables (T22–T26 done; T27 phase lock, T28+ yank, T29+ storage).

Status words as in the rest of the KB: CONFIRMED = read in the source or commit; PROBABLE = inferred,
reason given; UNKNOWN = not established anywhere.

---

## 1. Method lessons from the handbook (apply to every tutorial step)

| Lesson (handbook wording, shortened) | Where | → in our tutorials |
|---|---|---|
| "A claim about what the code says can be settled by reading. A claim about what the machine does cannot." 5 of 16 source-only predictions were contradicted on the Pi; 2 of 3 desk diagnoses were wrong about the mechanism. | what-the-pi-taught-us.md "The working rule" | Every step that touches the Pi writes the prediction down first (`check` lines in the `%% tutor` block), then runs. Patches are labelled "not compiled here". |
| "Measure before you argue from resources" — a design option was rejected on a RAM figure that was 2× wrong. | ibid. | Storage: read `free -m` and `grep Cma /proc/meminfo` before choosing buffer counts; never argue from "a small board". |
| "A default is a claim, not a fact — verify the value the hardware actually receives"; six copies of a default, one checked, a week lost. | ibid. | Phase lock: read back `FrameDuration` metadata, not the request. Storage: read back `/proc/sys/vm/dirty_bytes`, `/sys/block/*/queue/*` after the helper writes them. |
| "Add the observability that could FALSIFY the fix, not the number consistent with it." | ibid. | Phase lock logs the phase error (grows if the lock fails), not `locked=1`. Yank logs the errno and the classification, not "media removed". |
| "A log line is only evidence if one build could have printed it." Log values, not conclusions. | ibid. | Tutorials print the running commit before measuring; log lines carry numbers (`err_us=`, `errno=`). |
| "A guard that reads the present cannot defend against a job that runs later." | ibid. (2026-09-07 getty case) | A record-start media gate is necessary, not sufficient: the writer must classify the errno at the moment of the write. |
| "A fallback whose failure mode is 'yes' is not a fallback." A plain NVMe was labelled CFE by a sysfs node that exists on every Pi 5. | ibid.; hardware-log 2026-09-05; commit 888093c | Media-class detection must be able to return `unknown`; CFE only via the hat's own I2C answer at 0x34. |
| "A tool exiting 0 does not mean it answered" — unprivileged `blkid -c /dev/null` returns empty with rc 0. | ibid.; commit 34f8c59 | Every probe in Core's media code requires non-empty output before it counts. |
| "A workaround that does two things credits the wrong half." | ibid. (2026-09-20) | Storage: never change `dirty_bytes` and the scheduler in one step; separate them and measure each. |
| "Duplicated truth must be deleted, or carry a named reason and a check. A comment is not a check." "When this project routes, it wins. When it copies and comments, it loses." | conventions/philosophy.md | Tuning numbers live in one table in Core (the media profile) that the UI and docs read; one gate in `handleCommand` covers socket, WebUI and buttons. |
| "Fail visible, never silent — the operator must never be shown a plausible wrong number." `fps_actual` showed the install-time seed 24 for the life of the system. | philosophy.md; cinemate b029d7f (2026-08-31) | State exposes *measured* cadence and write failures, not only the switch position. |
| "Degrade in ladders whose last rung still produces a usable answer." | philosophy.md | Yank: the take must end with a usable clip and an honest message even when the unmount fails. |
| "The file is the witness, not the control that was supposed to configure it." | what-the-pi-taught-us.md | Post-take verdicts come from files on disk (count and sizes), not from the frame counter. |
| "The Pi is the runtime truth"; the codebase keeps comments that record falsified experiments. | philosophy.md | Our answers keep the "surprises" sections and the UNKNOWN lists. |

---

## 2. Phase lock — what Cinemate learned, in order (cinepi-raw unless marked)

| Commit (date) | What happened | → ours |
|---|---|---|
| `bf717fa` (2026-06-11) first version, off by default, VBLANK-only "so the 4K static failure mode of the getBlanking HMAX-stretch patch cannot recur"; runtime Redis keys for gains. | An earlier libcamera `getBlanking` patch that stretched HMAX produced a broken ("static") 4K image. | Apertar's qbc libcamera carries an IMX585 `getBlanking` lattice search (`4cff971`, post-tag) that may re-choose HMAX per microsecond. T27 step: pin two durations 1 µs apart and read back `HBLANK`/`FrameDuration`; if HMAX moves, measure rolling-shutter skew and exposure before enabling. |
| `85d0326` (06-11) pure integral was an undamped oscillator: railed the ±150 µs clamp, VBLANK swung ±15 lines, average still locked (−15 ppm from +1066). | First Pi test. | Ours is PI from the start; host simulation shows 13.9 µs max error, 3 adjacent requests. |
| `55562b6` (06-12) gains verified: kp 0.06, ki 0.0015, deadband 6 µs; +1066 ppm → −9 ppm; 2–3 line dither, ±12 µs duration, 0.03 % exposure variation, 0 drops. | imx585 mode0 25 fps. | Same gains. Pi expectation for T27: `FrameDuration` alternates by ~11 µs; drop estimate stays 0. |
| `d038556` (06-12) lock runs in preview so a take starts locked. | | Same. |
| `e74e3e4`, `3b3ff60`, `4537153` (06-13/14) three iterations: a 186 ms reconfigure stall leaked into the accumulator; takes started −90 ms, then −169 ms; final policy: preview gap > 1.5 frames re-arms, recording gap is absorbed as missed frames, preview half-frame backstop. | imx585 mode1 24 fps each time. | Final policy implemented; host simulation checks all three. T27 reproduces their failing case: switch mode, record within 2 s, inspect the first frames' phase error. |
| `5b4b209` (06-15) reference = `FrameWallClock` "= the audio clock"; `--sync` client suppressed. | Dual-sensor unify. | Core's audio is stamped on CLOCK_BOOTTIME, so the Core reference is `SensorTimestamp` (BOOTTIME): no audio change. Core has one sensor: no role gate. |
| `28b30cc` (06-15) control law moved to a pure header with 4624-check unit tests "that exercise the shipped code path, not a copy". | | `FramePhaseLock.hpp` is pure; `working/tools/phase_lock_sim.cpp` compiles against the shipped header and passes 17 checks here (the only compile-verified part of the patch). |
| cinemate `0b8e947` (06-15) default on in Cinemate, off in standalone cinepi-raw; `2f79397` (06-16) static per-mode correction table removed, kept revertable; `8e5d940` schema says safe on `--sync` rigs. | | Core default off until T27 has measured it. Core has no correction table; its `nextFrameIndex` rounding and WAV end model (p2) simply become exact. |
| `4cca1fb` (10-02) `--phase-lock [0\|1]` so it can be set without the harness. | | `set_fps_phase_lock enabled=true/false` + persisted setting, state field. |
| `3c6477e` (08-26) SMPTE frame base was rounded from measured `FrameDuration`; at 24.5 fps it flipped 24/25 by sensor mode; "cost a day of chasing a commit that never existed". | | Checked in Core: `FrameDuration` metadata feeds only the gap estimator's nominal (`trackRecordingCadence`) and the WAV end model's fallback when fps is unknown; DNG FrameRate (0xC764), DNG/MLV timecode and MLV fps come from `settings.fps`. No hazard; T27 asserts the FrameRate tag is unchanged with the lock on. |
| `07504d0` (06-02) `FrameDuration` is µs, not ns; the 1000× error made 191,622 phantom holes on a 194-frame take. | | Core normalises the unit heuristically (`normalizeFrameDurationToUs`). T27 logs the raw value once. |
| `dcd2b65` (06-02) one shared "latest wall clock" scalar overwritten by the main thread while 4 encode workers drained → phantom TC holes; fixed by stamping each frame's own timestamp into the queue item. | | T25's `PendingCopy` carries the frame's metadata; never let a worker read a shared "latest" value. |
| cinemate `b029d7f` (08-31) `fps_actual` was never measured; a dead second mechanism hid it; average the intervals and invert, because mean(1/dt) > 1/mean(dt) under jitter (40.25 vs 40.00). | | T27's measurement computes 1/mean(dt). State shows measured cadence next to the switch. |
| cinemate `56bf88c` (06-05) a sensor running fast (more frames than expected) is not loss; only a shortfall latches the warning. | | Core's estimator counts gaps only; keep it that way. |
| `94102f7` (07-06) BOOTTIME→REALTIME offset must be one system-wide constant sampled once, not anchored at first-frame arrival (two synced cams drifted by a constant). | | Core's `RecordingClock` samples one offset per clip (p2 §3) — same shape, nothing to do. |
| handbook: "two per-frame phase-lock telemetry keys, written once per frame, with zero reader". | what-the-pi-taught-us.md | No per-frame publish in Core: stats at record stop, env-gated trace every 250 frames. |

---

## 3. Audio — the June 2026 "audio sync from 3.3" campaign (cinepi-raw) and what it means for Core

| Commit (date) | Lesson |
|---|---|
| `fed2ede` (06-01) SCHED_FIFO for the capture loop + xrun silence fill. `b9dd1c1` dsnoop backlog from a slow idle-monitor shutdown appeared as a constant audio start offset ("intercept"). | Shutdown ordering of a monitor can look like a sync offset. |
| `6ccfabd` (06-03) silence fill only on `-EPIPE` missed the 4K 24-bit case: USB capture under-delivers **with no xrun**; a 6-min take came out 2.55 s short with zero fill events. Fix: reconcile frames written against wall clock on every read. | Sample loss can be silent. |
| `5021ba3` (06-03) 40 ms ALSA buffer on every path; under 4K NVMe load the cheap 16-bit mic stalled hundreds of ms per event, 62 s lost in one take (281 pads). Record path gets a 2 s ring (idle monitor keeps 40 ms). | The ring must outlast the storage stall. |
| `ffb61fd` (06-03) exFAT `write()` blocks for hundreds of ms under DNG pressure; a capture thread that writes to disk cannot read the ring; dedicated writer thread + RAM queue; "the average audio bitrate (~100–290 KB/s) is trivial for the drive". | The capture thread must never touch the medium. |
| `521dc72` (06-03) Pi 4/5 (their words) USB mic and NVMe/USB SSD share one xHCI; FIFO priority 80 and pin capture to the last core. `cab91a9`, `7551a16`, `d7a8d2b` (06-07) a stale recorder profile pinned DNG workers onto the audio core → garbage WAV start TC or no WAV; invariant locked by a test; installer adds `isolcpus=…3 nohz_full=3 rcu_nocbs=3 irqaffinity=0-2` on 4-core boards. | Affinity tables need a check, not a comment. |
| `8e21f4a` (06-06) reconciliation tolerance tuned up to periodFrames/4 (~5.3 ms): the 1.3 ms one injected ~3 frames of silence per 6 min from scheduling jitter. | A fill threshold below the scheduler jitter manufactures drift. |
| `8282087` (06-03) the 1 s ALSA drain tail after stop pushed the WAV ~0.5 s past the picture; last clap read late by up to 7 frames. | WAV length must equal picture length. |
| `7398b62` (06-03) **ADC ppm correction removed**: clap-delta on clean 2K takes showed the RØDE clock ~0 ppm; the earlier 1130/1797 ppm numbers "were fitting bracketing noise from a whole-file duration-ratio method. Applying +1797 ppm was itself the source of the late drift"; residual 4K errors were storage-contention sample loss. | **A whole-take frames/duration ratio cannot tell clock drift from sample loss.** |
| `c740406` (06-03) a dead-WAV wait (5 s) delayed the next take's capture launch by 2.3 s; the first clap was never recorded and "looked like a sync error". | Serialised finalisation of take N must not delay capture of take N+1. |

**Core today (CONFIRMED from source, `apertar-core@2a6f114`):**
- The reader thread does ALSA read → gain → `rawStream_.write()` into `clipFolder/audio_capture.raw` **on the recording medium** (`src/audio/AudioRecordingSession.cpp:233`, `:472`).
- ALSA buffer is 100 ms: `snd_pcm_set_params(…, 0, 100000)` (`src/audio/TimestampedAudioCapture.cpp:189-190`); `SND_PCM_NONBLOCK`, `avail_min` = 10 ms.
- Discontinuities > 10 ms (from `snd_pcm_htimestamp`) are padded with silence (`AudioRecordingSession.cpp:431-440`) — this *is* Cinemate's wall-clock reconciliation, already present.
- No SCHED_FIFO, no affinity anywhere in Core (grep); DNG workers only get a nice value (`CameraController.cpp:3869`, copy worker `:7201`).
- `finalizeWav` measures drift as frames/(audioEnd−audioStart) over the whole take and resamples when 20–2000 ppm (`:526-531`).
- Finalisation runs synchronously inside `stop()` (`:365-372` → `finalizeWav`), reopening the raw file on the medium.

**→ Deliverables:**
1. Phase lock (T27): no audio change (BOOTTIME reference). State that in the tutorial and why.
2. Storage (T29+): add a writer thread with a RAM queue between the reader and `rawStream_`, and a 1–2 s ALSA buffer on the record path (`snd_pcm_set_params` latency argument). Keep the 10 ms discontinuity padding — it is the correct reconciliation. Measure before/after: count `ApertarCore audio discontinuity:` lines per take on exFAT under Clear HDR.
3. Drift-measurement hazard: Core's `measured_drift_ppm` is the whole-take ratio Cinemate retired. Padded gaps are already compensated, but silent under-delivery is not and would be "corrected" by stretching. T29 check: compare `measured_drift_ppm` between an idle 2K take and a Clear HDR take on the same mic; a difference of more than a few ppm is loss, not clock. Consider a per-device calibrated ppm with a tight clamp instead of a free fit.
4. USB topology: Pi 5/CM5 expose two xHCI controllers through RP1; put the mic and a USB SSD on different controllers (`lsusb -t`). Pi 4 has one.
5. Finalisation of take N must not block take N+1 (Cinemate `c740406`): Core finalises synchronously in `stop()` — a medium-dead stop must bound this (see §4).

---

## 4. Yank — history (cinemate unless marked)

| Commit (date) | Lesson |
|---|---|
| `8f49468` (2026-05-11) first `_handle_storage_error` funnel: a yank is handled as a clean unmount (no body; 56/20 lines in `ssd_monitor.py`). | Start of the design. |
| `f08c818` (05-31) `umount` EBUSY looped on exFAT eject until a hardware I/O error; fix: `sync` then `umount -l`. | Lazy unmount is the only unmount that always returns. |
| `3259da7` (06-09) "pull SSD, NVMe/CFE not recognised even after reconnect": `_active_raw` had been set even when the mount failed. Active + standby model; promotion from every loss path plus a periodic safety net; failed-device cooldown cleared on removal; partition-of-disk matching (`sda` vs `sdaa`). "Validated with a 20-assertion local simulation … Live Pi verification pending." | State must change only on real success; every loss path must converge on one handler; simulate the state machine on the host. |
| `1e56cb6` (06-09) lazy unmount is asynchronous: the mountpoint still read as mounted when promotion ran; poll ≤ 2 s for it to free. Verified live. | After `umount -l`, "is it mounted" lags. |
| `c8f06c9` (06-09) a USB stick mount re-applied the global `vm.dirty_*` for its own class, silently overriding the recording drive's tuning. | Global knobs only for the recording target. |
| `58fc7c2` (06-10) EIO while counting files in one corrupt clip dir (dirty NTFS after a hot-swap) was read as a yank → unmount → automount remount → same dir → loop. Fix: errors on paths *inside* the volume are local; device loss shows on the mount root (statvfs); path checks are pure string ops that cannot hang. | Classify by *where* the error occurred, not only by errno. |
| cinepi-raw `8b705c8` + cinemate `5fbef52` (06-10) write failures (open/write/short write/close) counted at the syscall and published live; "write-stage loss produces no TC gap, so it was invisible to the timing-based drop tiers until the post-take file count — this is the only live signal". NTFS marked not recommended. | Count failures where they happen; show them live. |
| cinepi-raw `32b7db3` → `5cb392d` → `b76e3e7`/cinemate `bc249ed`/`329cfc8` (2025-06 → 2026-06) rec-start while the previous take still flushes: first aborted the take, then dropped the backlog (`clearPool`), finally **blocks the start until every buffered frame is on disk** (`framesInFlight` gate); cinemate `ff59dd8` (09-07) then found a stop-time relaunch mid-drain SIGTERM'd the recorder and truncated the clip. | Never discard a backlog to make room; never restart a recorder while it drains. |
| `34f8c59` (08-25) unprivileged `blkid` empty-but-rc-0 broke mount after unmount 10/10; fixed 10/10 by requiring non-empty output. | Probes must say no. |
| `f01b6cd` (08-26) `umount` makes udev emit `change`; the worker routed `add` and `change` identically → a deliberate unmount was remounted "typically inside a second"; "unmount, wait, pull" was never safe. Eject-intent flag file under `/run`, written *before* unmount, cleared on real `remove` or successful remount; both halves degrade safely alone. | Deliberate eject needs an ownership token the automounter honours. |
| `888093c` (09-05) CFE-hat fallback that could not say no (see §1). | |
| hardware-log: no dated entry records a drive pulled during a take (y1 §Q6 grep). | **All Cinemate yank behaviour is design, not Pi evidence.** |

**→ Deliverables (with y1/y2):** Core already stops a cDNG/MLV/H.264/ProRes take within ~1 s of the first failed write (latched `RecordingFailure` + 1 s supervisor); lossy DNG does not (its async writer only logs). What is missing: a media-alive probe on the mount root in its own thread (never under `commandMutex_`), errno classification, a "medium dead" stop that does not reopen the medium and is time-bounded, counting the frames discarded after the latch, a media event + `media_state` for the UIs, record gates, and an eject-intent flag shared with the automounter. Tutorial T28 does the actual pull with predictions written first — the one measurement Cinemate never recorded.

---

## 5. Storage media — history and numbers

| Commit (date) | Lesson |
|---|---|
| `9184c68` (2025-11-09) storage-automount tuning table lands (per-class `dirty_bytes`, `nr_requests`, `scheduler`, `rq_affinity`, NVMe APST latency 0, ext4 `noatime,nodiratime,commit=60`). `2294d25` earlier WIP carried `chrt`/`ionice`. | Kernel-side tuning from day one, root-owned. |
| `e577437` (2025-10-22) pre-roll warm-up: record 2 s at max fps on mount/startup, delete the take. Later: `a6536e6` wait for startup, `bb5a065` defer dynamic resolution, `345f1ee` make it optional, `f023d92` run at sensor max fps, `734f7be` skip with no camera. | The mechanism it warms is **never stated** (s1 §3): no handbook measurement exists. → T29 measures first-take vs second-take drops before adopting it. |
| `2a49fa1` (2026-05-17) per-filesystem recorder profiles (workers, affinity, nice); `c1b6875` mount options in Redis. | Writer topology follows the filesystem; kernel tuning follows the connection. |
| `31126f2` (05-31) raw-buffer headroom; `a61a589` (06-01) per-filesystem: ext4 8, exFAT/NTFS 10 — "frame drops are disk-write-latency-bound; exFAT/NTFS produce spikier write+metadata latency (FAT/dir-entry churn from a new DNG file every frame)… matches the field observation that ext4 drops less"; ~25 MB CMA per 4K buffer. `e1dccd0` docs: "more RAM = more tolerance for storage hiccups". | Buffers are a latency cushion, not throughput. T23's 8 Clear HDR buffers follow the same reasoning; the media profile sets it per filesystem. |
| `130b93e`/`18a6d74` (05-31) backlog sampled only on frame delivery hid the spike that precedes a drop; publish a high-water mark instead. | UI meters need peaks, not instantaneous samples. Core has `peak_queue` in its stop stats; expose it live. |
| `86c38f6`, `53bdfaf` (05-31/06-01) default format exFAT; 1 MB clusters tried for write latency and reverted because they break macOS; `0142c5b` vfat must not alias to exFAT. | |
| `d7a8d2b` (06-07) USB SSD gets a smaller dirty cushion (256/128 MiB): "write speed falls off a cliff once its SLC cache is exhausted (~90 s into a 4K take); a large dirty buffer turns that into one long `balance_dirty_pages` stall — a burst of dropped frames"; Pi 4 caps ext4 disk workers 8→4 (shared xHCI). The 90 s figure has no measurement in the handbook (s1 §6). | The dirty cushion is a trade: smoothness vs one long stall. T29 measures the cliff with `writeback_watch.py`. |
| `c8f06c9` (06-09) apply global sysctls only for the active RAW target; restore when none remain. | |
| `5fbef52` (06-10) NTFS not recommended; handbook 2026-08-27/28: NTFS-over-FUSE NVMe sustains ~264 MB/s (12-bit 21 fps, 2520/2520 clean) but every 16-bit soak (~355 MB/s) filled the 173-frame pool in 15–22 s. | A hard throughput ceiling shows as a pool fill after a fixed time, not as scattered drops. |
| docs/settings-json.md 2026-09-13 table: 4K 16-bit ClearHDR + Log at 25 fps measured 317–334 MB/s sustained, "never dropped a frame, never failed a write, never let the disk queue past two" (media/filesystem not stated; PROBABLE exFAT on NVMe). | Target number for Apertar's own Clear HDR path. |
| changelog 3.3.1: "exFAT support and filesystem-aware storage profiles… IMX585 25 fps at 4K to SSD without frame drops"; "vmax cropping… reduces write speed needed to disk". | |
| handbook 2026-09-15: `/media/RAW` (exFAT/NTFS) has no ownership model; `cp -a` fails there. | Core's helpers must not `chown` on FAT-family media. |
| cinemate `9ba3b12`, `c336af9` (06-04) erase/format raced the scanner; recording guard added. | Destructive media ops need the recording guard and the intent flag. |

**→ Deliverables (with s1):** a Core media profile keyed on *connection* (NVMe on PCIe, USB UAS, USB mass-storage, SD, other) for kernel knobs via a root helper, and on *filesystem* (ext4, exFAT, ntfs/ntfs3/fuseblk, vfat, unknown) for writer workers, queue depth, raw buffer count, direct I/O on/off (T24's O_DIRECT must be re-tested on FUSE), audio ring/writer thread; global knobs only while recording to that target; peak backlog live; pre-roll only if T29's measurement shows a first-take penalty.

---

## 6. Things Cinemate got wrong that we must not copy

- Per-frame Redis telemetry with no reader (handbook).
- `and self.ssd_monitor.get_space_left` — a bound method, always truthy: the space gate never gated (y1 Q7 #12).
- Mount test by substring over `/proc/mounts` (`/media/RAW` matches `/media/RAW1`) (y1 Q7 #2).
- An internal stop (`setRecording(false)` on pool exhaustion) that is never published; the controller finds out from its own watchdog (y1 Q7 #4).
- A post-take verdict that counts a short DNG with size > 0 as present and goes blind when the drive is gone (y1 Q4).
- `fps_actual` never measured for the life of the system (cinemate `b029d7f`).
- A stale recorder profile that pinned workers onto the audio core (`7551a16`).
- ADC ppm correction fitted from a whole-file ratio (`7398b62`).
- Three mode-switch iterations on the phase lock that each shipped before the failing case (mode switch then record) was in a test (`e74e3e4` → `4537153`).
- Zero hardware record of the one event the yank code exists for.

## 7. What Cinemate got right that we copy as *logic*

- PI servo with deadband and clamp, whole-µs requests as the dither, preview pre-convergence, split gap policy, pure header + tests.
- Writer thread between capture and disk; large ring on the record path; wall-clock reconciliation; WAV ends with the picture.
- Yank funnel: errno set on the mount root only; lazy unmount from a non-blocking call; eject intent before unmount; promotion/standby concept (Core: "next take has a target").
- Write failures counted at the syscall and shown live; peak backlog; buffer count per filesystem; global sysctls only for the recording target; smaller cushion for USB SSDs.
- "Block the start until the backlog is written" rather than discarding it.
