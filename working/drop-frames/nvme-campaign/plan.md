# NVMe 4K campaign on the Corsair cards: the plan (2026-11-08)

Written in a cloud session for Patrik after a research pass over the KB (the drop-frames campaign, the SSD long-take run and its
re-analysis, the dng-chain feasibility work, the exFAT directory probe, the runner `longtakes.py`) and a critique round (statistics,
rig engineering, operator and wear, a red team on the numbers, an independent challenger design; `nvme-campaign/critique/`). It builds on
three pages that stay authoritative for their parts and are not repeated here: `nvme-4k-recipe-plan.md` (2026-11-07: the capture-side
ruling-out rules and the runner extensions), `storage-slowdown-plan.md` (branch `claude/practical-johnson-he481b`, 2026-11-08: the
storage mechanisms M1-M11 and the buffer-as-a-meter method) and `longtakes-test-structure.md` (how the runner ran the SSD campaign).
Labels as in the KB: **measured** / **derived** / **probable** / **unconfirmed**; **web** for internet facts (URLs in
`nvme-campaign/research/R8-online-sources.md`). Numbers are decimal GB.

## 0. In one paragraph

Everything runs on the media Patrik shoots with: Corsair MP600 Mini 1 TB cards in CFexpress Type B adapters in the camera's hat, about
990 GB usable each. One card is the campaign card (the record's test card, serial `A936B442006AC2`, if Patrik agrees: its drive facts
and SMART history are in the KB); the other card(s) get a short check at the end. A detached runner on the Pi (`longtakes.py`,
extended by the build list) records every take, fills a database and rewrites a status page between takes; the Opus thread plans,
installs with Patrik, reads the status and decides between tiers (a `GO-<stage>` sentinel file the runner waits for before each long tier). The ladder is 3 -> 5 -> 15 -> 30 minutes with stop-on-drop at every
tier, two concordant takes per screening decision, capture-side levers screened at 3 minutes, the folder split tested at 30 minutes (unsplit first below
the 60 % create share, split first above it), no cool-down, no fill rule (only "does it fit"), clips deleted only when the next take needs the space. Audio is
watched on every take after the "ALSA capture: Broken pipe" stop of 2026-11-08. Budget: 10 TB on the campaign card, about 1.7 % of its
600 TBW rating (web); with the ~31-33 TB the card already carries, about 570 full-card shooting days remain by that rating (the drive's
own SMART estimate is more generous).

## 1. The owner's requirements and where each is met

| # | Requirement (2026-11-08) | Where |
| --- | --- | --- |
| R1 | Unsupervised; 4K Clear HDR 16-bit and SDR 12-bit first; the 4K full-frame and crop modes | §4, §6 |
| R2 | Levers: storage tuning, compression, Log, TDN, phase lock, WebUI on/off (+ FE depth 4, clip split) | §5 |
| R3 | Minimize writes; 3 -> 5 -> 15 -> 30 min | §6, §8 |
| R4 | Prognoses per stage; eliminate at the first dropped frame, stop the take | §7; **deviation to confirm**: the take stops at its first drop, but at the 3-min tier a cell is eliminated only after a second concordant take (the record's spread at the edge fps makes one take a coin flip); Patrik can revert to "one drop = out" and accept the position-artifact risk |
| R5 | Clear the card only when the next take needs the space; delete all campaign clips at the end | §6 fill gate, §9 |
| R6 | No NVMe cool-down; temperature logged, never gated | §5, §7 |
| R7 | A robust detached Pi script; the database filled between takes | §9 |
| R8 | Monitoring from ssh between takes: what, why, progress | §9 |
| R9 | Folder split examined | §2 (the probe), §6 S5/S6 |
| R10 | The 75 % rule removed | §3, §6 |
| R11 | Make the best of the card in use (the runner adapts to any size) | §3 |
| R12 | All tests on the Corsair cards, as in real life; a check on the other card(s) | §6 Part B |
| R13 | Does splitting matter for long recordings | §6 S5/S6, §7 signatures |
| R14 | 30 min drop-free in all 4K modes; executed by an Opus thread in VS Code | §7 claims, §10 |
| R15 | Keep an eye on audio (the Broken-pipe stop) | §5a |

## 2. What the plan rests on (labelled; detail in `nvme-campaign/research/`)

- **The drive is the record's drive.** Every earlier drive fact was measured on a Corsair MP600 Mini 1 TB (serial `A936B442006AC2`, firmware
  ERFM11.1): 733 MB/s direct writes for 5 s in the pSLC cache, 415 MB/s for 10 min by Core (measured); 525 MB/s for 60 s (derived from a 2026-10-28 crop take on an old build and an untrimmed, 78-82 %
  full card); no Core-pattern datum of 600 MB/s or more longer than 5 s exists on this card, so SDR12 at 42 fps and above is unmeasured
  drive territory and the meter take is its instrument; stalls
  for seconds after ~0.9 TB written without a trim, cured by a trim (measured, synthetic, 2026-10-30); Core trims at mount and after deletes
  >= 1 GiB per poll (confirmed; the trigger can miss slow small-file deletes, derived); 34 -> 54 C in 10 min at 415 MB/s, 72 C after 10 min
  of SDR at 410 MB/s (measured); 25.3 TB written at 3 % used on 2026-11-02, 29.0 TB after evening 3 (measured). Its own SMART thresholds: 82.9 C warning, 85 C critical (measured); 72 C was reached twice with 0 drops. Web: pSLC ~50 GB, post-cache
  ~800 MB/s, throttle ~80 C, 0-65 C spec, 600 TBW; two variants share the name (E21T 2023, E27T R2 2024; the CORE Mini is QLC with 250 TBW):
  the test card's firmware ERFM11.1 points at the E27T R2 (probable); S0 reads `nvme id-ctrl` through the helper instead of a label. The CFe-B adapter shell removes convection and adds mass (probable); the record's temperatures were probably measured in this same
  hat slot and shell (the test card has lived there since October), so they stand; the curve per card comes from the long takes.
- **Capture side, 4K Clear HDR 16-bit uncompressed** (recipe.md rows 1-8; take ledger R1): 25 fps clean for 10 min in 4 of 7 takes, all with
  TDN on and the WebUI closed; O1 (owner, 10 min, WebUI open, TDN on) lost 1 by Core's count; TDN off removes the back-end bottleneck (37 ->
  6 ms per frame, measured, p = 1/6); FE Config depth 4 removes the single-frame losses at 28 fps (probable, n = 1 + 1); 30 fps loses ~3
  frames in 2 min even so (a second limit, memory bandwidth suspected, unconfirmed). **No take longer than 602 s exists in the record**, and
  none of the clean 10-min takes ran with TDN off or depth 4.
- **4K SDR 12-bit**: 33 fps clean for 10 min, lossless and uncompressed (measured); ~42 fps clean once (owner, unscored). Not every 4K
  drop on this drive was a capture gap: the 77-81 %-full and the never-trimmed takes lost to a full write queue (measured), so the
  campaign reads the counter, never assumes the regime. 4K Clear HDR 12-bit:
  no long take on record.
- **Encoders**: HDR16 lossless 16.8-18.5 fps (measured): out above 16 fps; SDR12 lossless 48 fps capacity at 33 fps, 2.8 cores (measured,
  pre-roll): probably CPU-bound near 50 fps. Log on HDR16 = 12.45 MB per frame (measured, one DNG); Log on HDR12 did not shrink files on the
  SSD and Log + lossless made larger files than lossless alone (measured): no HDR16 Log + lossless arm is assumed.
- **The SSD run re-read**: 32 "late" buffer_full failures kept pace for 7-28 min and then filled the buffer within a minute while Core's CPU
  doubled in proportion to the files written; 78 "slow" ones were the write pattern's steady capacity (fsync + FLUSH per file, per-cluster
  allocation under the filesystem lock); the RAM budget varied 250-1,283 MiB; the trim state was never recorded (measured / derived).
- **The directory walk, measured** (probe, 2026-11-08, on this card): c = 63.3 ns per directory entry; create cost = -0.18 ms + 316.6 ns x
  files (5 entries per frame file): 14.1 ms at 45,000 files (35 % of a 25 fps period), 16.9 ms at 54,000 (51 % at 30 fps), 18.6 ms at
  59,400 (61 % at 33 fps); a merge's rename costs what a create costs at the target's size (verified live: 0.10-0.45 ms per file at 500-1,503 files, 0.72 ms at
  4,503); warm unlink 5 us per file; **the cold-cache unlink is measured** (probe step 4): linear in the files already deleted, 52.8 ns per
  entry, 13.6 s for 10,000 files; a flat 45,000-frame clip deleted after a boot costs ~4.5 min (derived), a clip split in parts of 1,000 ~6 s. The probe's pre-registered rule made the knob a prerequisite of the 15- and 30-min stages and the split A/B mandatory; this plan
  deviates knowingly: the 15-min tier runs unsplit only (the walk is 17 % of the period there, a predicted small effect; the statistics
  critique F4) and the mandatory A/B lives in the 30-min tier and the soak. The SSD
  run's 30-min passes at 45,006-59,412 files in one folder show single folders surviving those counts when the drive pattern has margin.
- **Core on the camera** (fork-log 2026-11-08): `cinemate-port` `ba0658d` since the 13:00 boot, then the two merge-worker fixes `68516f1` and `01f170c` found by the verification: Log, `buffer=ram` with the safety stop,
  trim, pre-roll, the media tune file, `set_preview_tdn`, `set_fps_phase_lock` ({d, d+1}), `set_media_trim`, `[storage] frames_per_folder`
  (0), `tools/flatten_clip.py`, the merge worker (`clip_merge` on by default; `APERTAR_CLIP_MERGE=0` forces off). UI `7ea9afc` reads split
  clips. **The clip-split knob is verified on the Pi** (`nvme-campaign/clip-split-verify.md`, steps 2-9 all pass: split take 1503 = enqueued, flatten, merge on and off, merge pauses 33 ms after `record_start` and the take during the pause lost 0 frames, restart mid-merge keeps the invariant, delete mid-merge clean). One verification take ended with the audio fault of §5a. **This Core base logs no `dropped_gap_estimate` line**: the drop checks are `recording_dropped_frames` and enqueued = written; which per-drop journal lines (`drop[kind]`) this binary prints is to be confirmed before S2 (the runner's first-drop time and loss classification read them).
- **Board**: CM5 Lite C0 (`c041a0`), the board of the SSD run; recorded per session.

## 3. Arithmetic (derived from measured frame sizes)

Frame bytes: HDR16 uncompressed **16.59 MB** (the 2160-row file; measured), HDR16 Log 12 **12.45 MB** (measured, one DNG), SDR12 and HDR12
uncompressed 12.44 MB (derived), SDR10 10.37 MB (derived), SDR12 lossless ~5.98 MB (measured, one scene), crops 3840x2072/2076 ~11.95 MB
and 3840x1608 9.26 MB at 12-bit (derived). Card: 999,960,870,912 B, 10 GB reserve -> ~990 GB usable.

| Arm | MB/s at 25 / 28 / 30 / 33 fps | GB per 3 / 5 / 15 / 30 min (25 fps) | files per 30 min (25 / 30 / 33 fps) | 30 min: fill of an empty card | max minutes (25 / 30 fps) |
| --- | --- | --- | --- | --- | --- |
| HDR16 uncompressed | 415 / 465 / 498 / - (30 is the mode max) | 75 / 124 / 373 / 747 | 45,000 / 54,000 / - | 75 % at 25, 84 % at 28, 90 % at 30 | 39.8 / 33.2 |
| HDR16 Log 12 | 311 / 349 / 374 / - | 56 / 93 / 280 / 560 | same | 56 / 63 / 67 % | 53.0 / 44.2 |
| SDR12 and HDR12 uncompressed | 311 / 348 / 373 / 411 | 56 / 93 / 280 / 560 | 45,000 / 54,000 / 59,400 | 56 / 63 / 67 / 74 %; 42 fps 94 % | 53.0 / 44.2 (33 fps 40.2; 42 fps 31.6) |
| SDR12 lossless | 150 / 168 / 179 / 197 (50 fps 299) | 27 / 45 / 135 / 269 | same (50 fps 90,000) | 27-36 %; 50 fps 54 % | 110 / 92 (50 fps 55) |
| SDR10 uncompressed | 259 / 290 / 311 / 342 | 47 / 78 / 233 / 467 | same | 47-62 % | 63.6 / 53.0 |
| Crop 3840x2072 SDR12 | 298 / 334 / 358 / 394 | 54 / 90 / 269 / 537 | same | 54-71 % | 55.3 / 46.1 |

Create cost at the end of a single-folder take (from the measured fit, as a share of the frame period): 15,000 files 4.6 ms; 22,500
6.9 ms (17 % at 25 fps); 45,000 14.1 ms (35 %); 50,400 15.8 ms (44 % at 28 fps); 54,000 16.9 ms (51 % at 30 fps); 59,400 18.6 ms (61 %
at 33 fps); **75,600 files (42 fps) 23.75 ms = 100 % of the 23.8 ms period; 90,000 (50 fps) 28.3 ms = 142 %**. The 25 % line: 32,161 files
at 25 fps, 28,777 at 28, 26,898 at 30, 24,505 at 33, 19,400 at 42.
**Split-first rule** (the challenger's finding): an arm whose 30-min create share is >= 60 % of its period (SDR12 or HDR12 uncompressed at
>= 33 fps, lossless SDR12 at >= 33 fps, anything at >= 42 fps) runs its 30-min tier SPLIT FIRST, because the unsplit take is a predicted
failure in minute 20-25 from the directory alone; its unsplit control is bought only if the owner wants the failure recorded. Arms
below 60 % (HDR16 at 25-30 fps: 35-51 %) run unsplit first as §6 says. A 30-min SDR12 recipe at >= 42 fps therefore requires the split.
Rules that follow: the fill gate is physical (free >= planned x 1.03 + 10 GB); a 30-min HDR16 uncompressed take needs an empty, trimmed card
and ends at 75-90 % full (the near-full condition is tested, not avoided); the runner reads the card's model, serial and size at the start
of every evening, recomputes this table, and after an arm's first take replaces the model's bytes per frame with the measured mean.

## 4. Modes

Primary: 4K Clear HDR 16-bit (3840x2200 raw, 16-bit unpacked), 4K SDR 12-bit (3840x2160), 4K Clear HDR 12-bit (3840x2160, CCMP).
Secondary (the owner's "4K full-frame cropped options"): the full-width crops Core offers at 10/12-bit (3840x2076 or 2072 for 1.85:1,
whichever the installed driver probes; 3840x1608 for 2.39:1; the others 2024, 1920, 1744, 1728, 1632, 1536, 1504 on request). 16-bit
height crops exist (31.9-42.4 fps) but their heights are not in the KB: S0 probes every crop with `list_sensor_modes` and a `set_resolution`
read-back per bit depth, a refused crop is `skipped_unavailable` (never a campaign stop), and the owner chooses per crop between a
confirmation at the winner's fps + 1 and a short ceiling search (down from the full-frame fps + 3, n = 2 at the final fps). Crops are
predicted from the full-frame result (fewer bytes, a lighter back end) and confirmed with two 3-min takes each at the winner's settings
plus 1 fps; their 30-min status is "predicted, untested beyond 3 min" unless a 30-min crop take is bought (one per crop, ~540 GB).

## 5. Levers: fixed state, screened levers, conditional tests

Fixed for every take (the recipe and the owner's real use): `dontneed=sync`, writeback on, `sync_ms` 1000, 8 raw buffers, FE Config depth 4
(the pipeline YAML copy via `LIBCAMERA_RPI_CONFIG_FILE`: the ONLY line of the campaign drop-in, armed once per evening by the root
helper with a Core restart and an environ read-back; no libcamera debug log, unlike the evening-4 helper), `buffer=ram`
at the record's keys (`buffer_ram_fraction 0.6`, `buffer_ram_floor_mb 512`): on this board that gave 250-1,283 MiB, median 635 (the SSD
run, measured; the 1,424 MiB of 2026-11-01 needed ~3.2 GB available), so expect 0.7-1.3 GB = 1.7-3 s of HDR16 input; the budget is logged
per take and every buffer_full is read in seconds of input; a fixed-MiB Core key (`buffer_ram_mb`, small) is the one change that would
make it constant (build list E), trim on, the pre-roll ON as in real use (it runs once per Core start, not per take; the unscored warm-up follows it), the merge worker OFF
(`set_clip_merge enabled=false` over the socket, read back per take, restored after; one mechanism, not the env variable as well), the ladder switched off by the runner at session start and restored in its `finally` (the gate stops on a ladder that is on), TDN off
through `set_preview_tdn` only (not the evening-3 tuning copy as well), peaking + zebra on, the touch UI
drawing, audio ON as the owner uses it, the WebUI stand-in client CONNECTED (the owner's requirement; `webui_remote.py` on the Mac under
caffeinate), no libcamera debug log and no tracefs (the campaign runs as real use runs; the 1 Hz sampler is the only instrument), the
card's model and serial checked per evening, nothing else on the Pi.

| Lever | Values | Stage | Expectation (label) | Takes |
| --- | --- | --- | --- | --- |
| fps | the record's bracket per mode (HDR16 25-30 starting at 28: the C0 board's only 4K HDR16 datum is a clean 135 s at 30 fps, n = 1, so 30 stays in; SDR12 from a meter take 5-10 % above the record's clean 42 fps, i.e. 44-46 fps, then capacity -1 / -2; HDR12 from 30), step 1 | S2 | HDR16: 27-28 clean at 3 min, 30 not (measured / probable) | the walk |
| Log | off vs on at HDR16 only (16 -> 12 stored). Not an arm for HDR12: Log does not change HDR12's bytes (the LUT is composed with the CCMP expansion; 2K 3.12 MB and 4K 12.50 MB with or without Log, measured on the SSD run) | S2 (ABBA) | fewer bytes vs copy-worker CPU; untried on the NVMe beyond 5 s (R1) | 4 |
| WebUI client | on (fixed) vs off | S2 (ABBA) | ~2 % more losses with it open under page-cache pressure (2026-11-01); O1 clean with it open | 4 |
| TDN | off (fixed); ONE unlogged TDN-on 3-min take at 25 fps | S2 | tests O1's instrumentation hypothesis: 0-2 lost supports it, >= 10 confirms TDN off for real use | 1 |
| phase lock | off (fixed); at most one 60-s probe of the {d, d+1} fix | S2 | drops + flicker on the old build (measured); no bearing on elimination | 0-1 |
| compression | per arm a manual `storage_preroll` reading first (encoder capacity, ~1 GB); a 3-min walk only for arms whose capacity exceeds the uncompressed edge (SDR12 lossless; HDR16 lossless + Log only if its pre-roll says > 25 fps) | S2 | HDR16 lossless out (17.6 fps); SDR12 lossless 48 fps capacity | 2-4 |
| storage knobs as one group | base vs {workers 1, queue 24, sync_ms 2000, kernel_tune on} | only if a 4K arm ends in buffer_full | no effect on the SSD (measured) | 2 meter takes |
| frames_per_folder | 0 vs 5,000 (the probe's N: <= 25,000 entries per folder) | S5 (30 min): unsplit first below the 60 % create share, split first above it; S6 soak as the split variant | 35-61 % of the period at the 30-min targets (measured c) | the pair |
| FE depth | 4 (fixed); optional control block: depth 2 vs 4 at 28 fps HDR16, one ABBA pair (the KB's missing second clean D4 take), needs two Core restarts with Patrik present; depth 6 only if late Config buffers appear at the edge | S2, optional | depth 4 removed the 28-fps losses (probable, n = 1 + 1) | 4 (optional) |
| Core patches of the storage plan (ftruncate, one FLUSH per tick, drain fix, trim trigger) | each A/B'd with the meter | S6, conditional | storage-limited arms only | ~100 GB |

### 5a. Audio: what the campaign watches (R15)

Facts: Core captures through a 100 ms ALSA ring with a 10 ms period (`audio capture: buffer_frames=4800 period_frames=480 requested_ms=100/10`
in every take's journal; `APERTAR_AUDIO_BUFFER_MS` 100-4000); the T30 writer thread sits between capture and the raw file, which is fsynced
once a second; in the SSD run the writer's backlog peaked at 30-2,764 KB per take (up to ~9.6 s of audio at 288 KB/s: the raw-file writes stall for
seconds under DNG pressure on the T7, measured; on this card the two recorded peaks were 9 and 16 KB); the KB's old reading says xruns are handled with `snd_pcm_recover`, yet a 3-min take on 2026-11-08
ended after 32 s with `ALSA capture: Broken pipe` (all frames written, merge off). Cinemate's history treats this class with a real-time
capture thread, a 2-s ring and silence fill on an xrun. Candidate causes: **the part boundary first**: the fault take (C0005 of `clip-split-verify.md`) ran with `frames_per_folder` 200 at 25 fps,
so a part folder was created every 8 s; the stop came at 32 s with 799 frames written, i.e. exactly at frame 800, the start of `part_004`
(derived from the page's figures). Whatever the boundary does on the copy side or the sync thread (the new folder's creation and its
fsync under the filesystem lock) is the first thing to read in the diff `f4a1393..01f170c`. Then: a kcompactd proactive-compaction burst
(period ~32.8 s, evening 3's analysis) holding the capture thread past 100 ms; the writer backlog pushing back into capture if its queue
is bounded; a USB device hiccup.
- **Every take records**: the `audio capture` line (format, ring), `audio writer: peak_backlog_kb`, `audio discontinuity` events, `audio sync`
  (trim and pad samples), `audio clock` drift and correction, any ALSA error; `peak_backlog_kb` becomes a column and a trend to watch.
- **Outcome `audio_fault`**: Core logs the stop as `recording failure: fault=write_error ... ALSA capture: Broken pipe` (clip-split-verify.md), so the runner reads `ALSA capture` in the failure line, not the fault word, and assigns `audio_fault` before the walk decides anything
  (a fault never steps the arm's fps down). A take that Core ends on an audio error is its own result: not a video drop, never eliminating an arm alone;
  repeated once; the journal window, the vmstat compaction counters and the kernel's usb lines at that second are kept with it.
- **Rate so far**: 1 audio fault in 9 takes on the clip-split build against 0 in the 72 SSD-run takes that actually carried audio (110 of
  its 182 takes recorded none, and the runner never flagged it): suggestive, not significant. The runner therefore also checks that the
  `audio capture` line exists in every take's window (`audio_missing` otherwise, a void for a real-use take) and reads the `audio sync`
  trim/pad samples per take, because audio can under-deliver silently with no xrun at all (Cinemate's lesson 6ccfabd; Core's
  `measured_drift_ppm` is a whole-take ratio that would hide it).
- **The Core fix is a prerequisite of the long tiers** (S4-S6, Part B): a real shoot with audio must not lose a take to a 100 ms gap. S2 may
  run at the 100 ms ring to measure the fault rate; if the fix is not in by night 2, the long tiers run with `APERTAR_AUDIO_BUFFER_MS=1000`
  as a recorded deviation. Two audio faults on one arm = the arm is "out with audio" (reported apart from video eliminations); a faulted
  long take is not repeated automatically.
- **Desk task first**: the Opus thread records the frame index at the fault against the part boundaries (800 = boundary), then pulls that take's journal window (the error line, the stop reason, `peak_backlog_kb`) and reads
  `AudioRecordingSession.cpp` / `TimestampedAudioCapture.cpp` at `ba0658d`: if an xrun ends a take today, the Core fix (recover, pad the gap
  with silence, log an `audio discontinuity`, continue) comes before the campaign, because a real shoot must not lose a take to a 100 ms gap.
- **Levers if it recurs**, in order: `APERTAR_AUDIO_BUFFER_MS` 1000-2000 (no code); `vm.compaction_proactiveness=0` through the helper
  (`compact0` / `compact-restore` exist); the Core fix above. S0 checks once which USB controller the microphone shares.

## 6. Stages

**S0 Preflight** (desk + Pi, Patrik present for sudo; ~2 h): **Patrik's footage is offloaded from the campaign card first** (the
card is his shooting medium; the runner deletes only folders in its database and treats any other folder as a void of the run);
`fsck.exfat -n` on the card (the 2026-11-08 mount reported "Volume was not properly unmounted"; the record holds 1,535 unsafe shutdowns
and three controller deaths) and again after any unclean shutdown; the systemd timers that could run during a take masked for the
campaign (`fstrim.timer`, `apt-daily*`, `man-db`, `logrotate`; the helper does it and restores them); status check (binary `01f170c` or later; `get_state` shows `frames_per_folder`,
`clip_merge_enabled`, `cdng_log`, `buffer_setting`, `recording_dropped_frames`; the mounted card's model, serial, size and part number;
helpers; cmdline; media tune file; ladder); the clip-split verification is on record (`clip-split-verify.md`): read it, do not repeat it; instead one forced-drop check of which journal lines this binary prints per drop (`drop[kind]`, `recording stats`, `recording failure`) so the runner's classification is tested before S2; the audio-fault forensics of §5a; the campaign root
helper and its exact-command sudoers installed by Patrik; the campaign drop-in armed (the FE depth 4 YAML line only; the YAML copied to `/run/apertar-media/` by the runner at start, as pi);
the merge switched off over the socket; the pre-roll stays ON as in real use (it runs at Core start,
not per take; the warm-up take follows it);
the power check (`vcgencmd get_throttled`, `pmic_read_adc`, the kernel log for under-voltage); smart-log baseline (data units written,
percentage used, temperature); `fstrim`; the probe's step 4 is done (cold delete measured); the runner's
smoke test (`--max-seconds 20 --only 1`) proving `buffer_used` at 1 Hz. Writes: ~20 GB.

**S1 Camera-free probes** (~1 h, ~150 GB): `storage_facts.sh`; one direct write of 60 GB with a 1 Hz bandwidth log (Core idle, not stopped: stopping it needs sudo; trimmed card): on the Pi's Gen 3 x1 link (~760 MB/s) both the
pSLC rate and the post-cache floor of this card (~800 MB/s, web) sit above the link, so no knee is expected; the probe confirms the
link-limited rate and starts the temperature record of the card inside its CFe-B shell (the real thermal curve comes from the long
takes, with smart-log's thermal counters read between takes); the write-pattern matrix at 4K size (`exfat_write_probe.py`: default, workers 1, prealloc, fsync none, direct, subdir 5000; ~30 GB);
a 60-s full-speed write after the trim and again after the first full-card take and delete (drive state). Optional (owner's call,
~120 GB): the paced small-file probe (`exfat_write_probe.py`, 1 MB files at 25 and 42 files/s for 30 min, flat vs `--subdir 5000`),
which shows the directory effect at the real create rates without the camera and would make the SDR12 unsplit control skippable.

**S2 Screening at 3 min** (one night, unsupervised; ~2.2 TB), per mode (HDR16, SDR12, HDR12, then the two crops): an unscored 60-s warm-up
after every Core restart or mode switch; the fps walk inside the record's bracket, step 1, two concordant takes per decision (2 drops = out; a 3-min clean
take is confirmed by its 5-min take in S3 rather than by a second 3-min take; 1-1 = a third 3-min take decides); the limiter per failure (capture gap / buffer_full / drive event / audio_fault);
controls at the start and end of each mode block at the edge fps; the lever variants paired ABBA at the edge fps (Log, WebUI off); the single
TDN-on take at 25 fps; the phase-lock probe if wanted; the compression arms via the pre-roll reading first. Output per mode: the clean 3-min
fps, the limiter, the lever verdicts, the prognosis table (§7).

**S3 Confirmation at 5 min** (inside S2's mode block, right after a cell's first clean 3-min take; ~0.4 TB in all): the 5-min take IS
the second concordant take of that cell (the owner's tier, the challenger's economy): 3-min clean + 5-min clean = "clean at 3 and 5 min",
the cell is carried; a 5-min drop = "1 clean, 1 drop", a third 3-min take decides and the runner-up fps gets its own 5-min take.

**S4 15 min** (~1.5 h, ~1.1 TB): one UNSPLIT take per mode of the best arm, ordered so that the second take starts on the card the
first one filled (no delete between them while they fit: the second ends near 75 % full on a trimmed card, fill as a deliberate
covariate, the gate deletes only before the third); Core's CPU slope and the buffer curve are read as the directory
meter; the runner-up only if the best drops.

**S5 30 min** (~2 h, ~2.2 TB): per mode on an empty, trimmed card; the card ends 56-90 % full. Arms below the 60 % create share run
UNSPLIT FIRST; the split member (frames_per_folder 5,000) runs in S5 only if the unsplit take drops after ~minute 10 with the directory
signature (§7), otherwise it is the soak of S6. Arms at or above the 60 % share (§3) run SPLIT FIRST; their unsplit control is the
owner's option. MLV: one diagnostic 30-min take per mode only if both cDNG takes of a mode dropped late (owner's call).

**S6 Soak and conditional work** (~2 h, ~2.2 TB): the final recipe per mode once more at 30 min as the SPLIT variant where the unsplit take
passed (the A/B in the conservative order at no extra bytes: heat and process age work against the split); the storage plan's Core patches
only where S1/S5 showed a storage limit at 4K; a 30-min crop take if the owner buys it.

**Part B, the other Corsair card(s)** (one evening per card, Patrik swaps the card): Patrik's footage offloaded; part number (a QLC
CORE Mini is refused), serial and size recorded; `fsck.exfat -n`; the trim at mount seen in the journal; the adapter noted per card; the runner's
card detection recomputes §3; by default the 60-GB knee probe, one 30-min take of the winning HDR16 arm (the question that matters per card) and one 15-min take of
the heaviest SDR12 arm (~1.4 TB and ~2 h per card); the other modes' 30-min takes as Patrik's option (~0.6-0.75 TB each); labelled
"n = 1 per card". Cards of the same model and firmware should behave alike; trim state, fill history and the adapter's thermal contact differ per
card, which is what this check sees. ~1.4 TB per card by default.

**Fill gate (every stage)**: free >= planned x 1.03 + 10 GB, else delete the OLDEST campaign clips (from the database, keyed by card serial, clip name, mtime
and take id, since clip names repeat after every format; never the owner's folders) through Core's media-delete route (`POST /api/media/delete` by exact name: it pauses a running merge, deletes and trims in
~0.5 s, measured in the clip-split verification), never by `rm`; re-read df. Clips are deleted in the boot
that wrote them (5 us per file); a delete after a reboot is budgeted at ~4.5 min per flat 30-min clip (measured slope, derived total) and
never started within 10 min of a planned take. At the end of each part every campaign clip is deleted and one `fstrim` runs.

## 7. Rules, pre-registered before the first take

- **A take ends** at its first dropped frame (any Core counter), at Core's safety stop (`buffer_full`, a result), at an audio fault
  (`audio_fault`, a result of its own), at the tier length, or at the capacity guard (6 GiB free: `pass_drive_full`). Recorded: time to the
  first drop (read from the 1 Hz samples of `recording_dropped_frames`, not from journal lines this binary may not print), the limiter
  (from the stats line and the buffer flags), the file count at the stop, the buffer level and Core CPU series, the device's write latency series, the audio lines,
  temperatures, fill.
- **Decisions need two concordant takes** at the screening tier (a deviation from "one drop = out", see R4); a confirmation take costs its time
  to the drop, which for the single-frame losses of the record came in minute 2-3, i.e. up to a full 3-min take (25-75 GB at HDR16).
  A single late frame is repeated once: reproduced = the arm is out for the goal whatever the mechanism; not reproduced = both recorded, the
  arm carried.
- **Elimination reasoning**: under every known mechanism the hazard grows within a take (files, fill, heat, process age), so a drop at t < L
  puts the arm out at L and above; a clean take of n frames bounds the loss rate only at 3/n (95 %), so a clean 3-min take says "not
  hopeless", never "will hold 30 min".
- **Lever verdicts**: "better" = beats every pooled control at the edge fps AND matches the pre-registered direction AND replicates (ABBA);
  "worse" = drops before every control; otherwise "not shown (n = 1 pair)", not terminal, but the lever does not go to the long tiers; at
  most one lever variant per mode goes forward (best + runner-up); a lever is tested only against the limit it can act on (capture levers
  against capture gaps, storage levers against buffer_full; Log in both regimes).
- **No fitted log(T) prognosis** on the capture side; the next fps comes from the failing take's mechanism (a steady back-end deficit gives
  the capacity; rare single frames mean step 1 fps with two concordant takes). The prognosis per cell is a survival table: clean exposure
  (frames, pooled across tiers; pooling assumes a constant hazard, which the growing costs deny, so the bound is a floor), the 95 % rate
  bound (3/n), the losses that bound allows in a 30-min take, the model expectation with its
  unmeasured terms named.
- **Buffer_full** is reported as seconds of input absorbed (budget / rate), never raw seconds; the budget is logged per take.
- **Meter takes** (storage-limited arms only): fps from the budget (5-10 % overshoot, 30-60 s), the integral identity (fps minus drain summed
  = final buffer level) and the device cross-check part of the record; capacity reported with its window and spread.
- **Long tiers**: after an EARLY drop (before minute 10, capture gaps, no time-growing signature) the arm steps down 1 fps for the next
  tier; after a LATE drop (after minute 10) with a signature the fps stays and the attribution plus the split rule apply.
- **Split verdict**: a late drop is attributed by pre-registered signatures, read in this order: (a) Core's CPU slope consistent with 77-133 ns per directory entry (the in-take all-in
  value of the SSD run's 17 long takes; the probe's 63.3 ns is the walk alone) + the buffer rising only in the last minutes + flat device
  latency -> directory; device write ticks per write rising with fill -> drive state; temperature rising with latency
  -> heat; dirty/writeback KB rising -> page cache; none -> capture side. Four readings of the pair: unsplit drops late with signature (a) and split
  holds -> *consistent with* the directory mattering at that length (effect = the time difference and the CPU slope; one pair cannot
  prove it, the strong statement is the probe's c plus the in-take slope); both hold -> no effect seen at that length; both drop at
  similar times -> not the directory; split drops and unsplit holds -> recorded with its heat and age confound, no claim. Split second
  is the conservative order.
- **Position and drift**: a 60-s unscored warm-up after every Core restart, reboot and mode switch; a lever pair never starts a block; `takes_since_restart`, `uptime_s`,
  MemFree, the buddyinfo order-8 count on every record; if a block's end control differs from its start control by more than the pooled
  spread, the block's lever verdicts are flagged "drift".
- **Void** (decided from the checks before any analysis): the mode line differs from the request; `fps_speed_ramp` true; a client lost
  mid-take (a missing client BEFORE a take is a WAIT state, not a void: the runner waits for the Mac stand-in); a build or another session active; the card serial wrong; the FE YAML's md5 wrong; `clip_merge` on when
  it should be off; `frames_per_folder` not as the arm says; Core's PID changed under the runner; the card not mounted read-write. The
  runner repeats a void once.
- **Stop the night**: `critical_warning` != 0, a kernel `nvme` / `pcie` / exFAT error, Core `error`, `media_alive` false, a runner crash, a
  second void, an under-voltage event, two audio faults in a row, the write budget reached, and any kernel move to 6.18.y before its NVMe
  silent-corruption fix (web; `nvme.sgl_threshold=0` is the workaround). Restore, write the status, leave the Pi on, Patrik decides. A Pi reset ends the night: the `/run` drop-in (FE depth 4, merge off) is
  gone with it, so the runner resumes only after the helper's status shows the drop-in re-armed and `fsck.exfat -n` clean, and writes
  "WAITING: re-arm" to the status until then (mechanism: a resume sentinel plus an `@reboot` line for pi that starts the runner once in
  WAITING mode; it reads `get_throttled` bits 16-19 for the under-voltage history of the boot).
- **Runner liveness**: the runner writes a heartbeat file every 60 s; an independent watcher (a second detached script) sends
  `record_stop` and writes the status when the heartbeat is older than 180 s while Core records, so a dead runner cannot leave Core
  recording until the card is full; the status carries a liveness line.
- **Temperature and heat de-aliasing**: logged every second, reported per take (start, end, max), never gated; smart-log (temperature,
  thermal transition counters, critical warning) read through the helper between every take, not only at the evening's ends; the mode
  order is rotated between S5 and S6 and per Part B card (pre-registered) so heat is not aliased with mode; a take that ends with the card above 75 C is flagged
  (the MP600 Mini throttles near 80 C, web; its spec range ends at 65 C).
- **Claims table** (what the campaign can say at the end): one clean 30-min take = "recorded once at these settings; loss rate < 6.7e-5 per
  frame (95 %), up to 3 losses per 30 min still compatible"; two = "2 of 2; < 3.3e-5". Never "30 min drop-free in all 4K modes" as a
  property. Crops: "predicted, untested beyond 3 min" unless bought. Other cards: "one take per card". Eliminations carry a graded strength:
  a steady deficit within seconds is strong; a single frame at minute 2 of one take is weak until repeated.

## 8. Wear budget (expected / worst, GB, on the campaign card)

| Stage | GB | Notes |
| --- | --- | --- |
| S0 + S1 | 130 / 250 | the 60 GB knee probe is the one deliberate write; the paced probe (~120 GB) only if bought |
| S2 | 2,200 / 3,000 | mostly short failures; a clean HDR16 take is 75 GB |
| S3 | 400 / 600 | one 5-min take per mode (+ runner-up on a drop) |
| S4 | 1,100 / 1,500 | one 15-min take per mode |
| S5 | 2,200 / 3,000 | one 30-min take per mode; the split member only on a late drop |
| S6 | 2,200 / 3,000 | the soak as the split variant; patches conditional |
| **Campaign card** | **~9 / ~14 TB** (the operator critic's recount at the likely edges) | cap 10 TB (~1.7 % of 600 TBW, web); the card held 29 TB on 2026-11-04 and ~31-33 TB after the 11-07/08 runs (derived), so about 570 shooting days of 1 TB remain by the rating |
| Part B, per other card | 1,400 / 3,000 | knee probe + one 30-min HDR16 + one 15-min SDR12 by default; the other 30-min takes on request |

A 30-min take is never repeated "to make sure" unless void; the one exception Patrik may buy is a second 30-min take of each mode's
winning arm (the statistics critic's most valuable extra: "happened once" becomes 2 of 2 and the rate bound halves), ~750 GB per mode.
The Part B check costs ~1.4 TB per card by default. If the budget must shrink: the optional second 30-min takes and the paced probe first,
then the crops' long takes, then Part B's extras beyond the HDR16 take; S3 stays (it is the confirmation take of every carried cell).

## 9. Runner, database, monitoring (R7, R8)

`longtakes.py` is the runner. **Its base is the unmerged branch `claude/practical-johnson-he481b` (49c6f46)**, which since 2026-11-08
already carries the fit gate, the kernel-log watchdog, `--budget-gb` with a projection, a lock, new stages and the sampler columns
(buffer level, device counters, dirty pages, trim state) this plan reads; merge it or build on it first (the build list's item A0). Its
`--fix-budget` default (0.9 / 256) must not be used: the plan keeps 0.6 / 512. What the runner does and lacks against this plan:
`nvme-campaign/research/R10-longtakes-runner.md` (anchored to main) and the rig critique's build-list review
(`nvme-campaign/critique/C2-rig-engineering.md` §3). The build list (`nvme-campaign/build-list.md`) is the work before the first scored
take: its section H (the re-anchored list) supersedes the item numbers above it where they conflict.
Between takes the runner appends one record per take to `longtakes.db` (takes; 1 Hz samples incl. the buffer level, device counters,
dirty pages, trim state, temperatures, Core CPU; drop events; Core counters; the audio lines; journal lines) and rewrites `status.md` /
`status.json` atomically with: the current or next take (arm, fps, planned length and GB, expected end), the stage, progress (takes and GB
done and remaining, hours), the survivors and eliminated arms with their reasons, the prognosis table, the fill, the last temperatures,
the smart-log readings, the audio trend, the last 10 rows, and the tail of `decisions.log`. From ssh: `cat ~/longtakes/<run>/status.md`
(one small read; written only between takes). Never during a take: `journalctl`, `ls /media/RAW`, builds, a second Core client, a second
WebUI.

## 10. Time frame and the Opus thread's job

Build and verify (one evening, Patrik present ~2 h) -> S0 and S1 (the same evening) -> night 1: S2 and S3 -> night 2: S4 and S5 -> night 3:
S6 -> one evening per other card. About 20 hours of Pi time in all; Patrik is needed for the sudo steps at the start of each night, the card
swaps, and the go/no-go between tiers (asynchronous through the status file). The handoff is `handoff-nvme-campaign.md`.

## 11. Open points for Patrik

1. Which card is the campaign card (default: the record's `A936B442006AC2`) and the part numbers of all cards (MN / MNR2 / CMN).
2. Which 4K crops (default 1.85:1 and 2.39:1); a 30-min crop take, yes or no.
3. MLV as a diagnostic take (yes/no). 4. The optional depth-2 control block at 28 fps (two Core restarts with you present) and the paced
small-file probe (~120 GB), yes or no. 5. The 10 TB cap, and whether a second 30-min take per winning arm (~750 GB each) is bought.
6. The campaign sudoers helper in two parts: a read-only alias the detached runner may call (`smartlog`, `status`, `fstrim`, `fsck-ro`,
`audio-usb`, `timers-mask/unmask`) and an interactive-only helper that refuses without a tty (`arm`/`disarm` the drop-in, `restart-core`,
`compact0`/`restore`, `drop-caches`, `reboot`, `poweroff`).
7. The audio fix in Core before the campaign if §5a's desk read shows an xrun ends a take.
