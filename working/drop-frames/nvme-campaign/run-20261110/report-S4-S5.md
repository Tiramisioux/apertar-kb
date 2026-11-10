# NVMe campaign report: S4, S5 (2026-11-10 11:35:23)

Labels: every number here is measured by the runner on this night unless it says derived. Card A936B442006AC2.

## Takes

| take | stage | arm | fps | tier s | outcome | s | dropped | first drop s | numbering gap | boundary drops | Core CPU avg | buffer peak % | nvme max C | GB | merge s | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|

## Fix checks (whole campaign so far)

- **8ec2f1a, part folder made on the writer**: 9 part boundaries crossed in 23 split takes (63749 frames); 0 drops within 64 frames after a boundary; 0 copy-slot drops in all. The buffer around a boundary (1 s before to 3 s after) rose at most 4.9 points above its take median (mean 1.19, 11 boundaries). Expectation if the fix holds: 0 boundary drops, 0 copy-slot drops (night 2 on the old binary: 3 copy-slot drops at 1 of ~40 boundaries).
- **e298d4a, frame index jump logged and counted**: 16 index jumps in Core's stats over the campaign; 0 takes had a numbering gap explained by them (0 frames, no picture lost); 9 takes had missing frames NOT explained by index jumps (each is a drop).
  - 4kHDR16_unc_log0_tdn0_lock0_trim1_web1_fpf5000_fps28_20261110-034628: missing 1, index_jumps 1, frames 3778
  - 4kHDR16_unc_log0_tdn0_lock0_trim1_web1_fpf5000_fps28_20261110-034921: missing 1, index_jumps 1, frames 4252
  - 4kHDR16_unc_log1_tdn0_lock0_trim1_web1_fpf5000_fps28_20261110-110124: missing 1, index_jumps 1, frames 122
  - 4kHDR16_unc_log1_tdn0_lock0_trim1_web1_fpf5000_fps28_20261110-110204: missing 2, index_jumps 2, frames 123 129
  - 4kHDR16_unc_log1_tdn0_lock0_trim1_web1_fpf5000_fps30_20261110-112434: missing 2, index_jumps 2, frames 38 47
  - 4kHDR16_unc_log0_tdn1_lock0_trim1_web1_fpf5000_fps25_20261110-112502: missing 1, index_jumps 1, frames 70
  - 4kHDR16_lossless_log1_tdn0_lock0_trim1_web1_fpf5000_fps25_20261110-112603: missing 2, index_jumps 2, frames 103 108
  - 4kHDR16_lossless_log1_tdn0_lock0_trim1_web1_fpf5000_fps25_20261110-112643: missing 2, index_jumps 2, frames 97 110
  - 4kHDR16_unc_log0_tdn0_lock0_trim1_web1_fpf5000_fps28_20261110-112723: missing 4, index_jumps 4, frames 4406 4408 4414 4416
  - jump in 4kHDR16_unc_log0_tdn0_lock0_trim1_web1_fpf5000_fps28_20261110-112723 at frame 4417: skipped 1, dt 71435 us
  - jump in 4kHDR16_unc_log0_tdn0_lock0_trim1_web1_fpf5000_fps28_20261110-112723 at frame 4415: skipped 1, dt 71419 us
  - jump in 4kHDR16_unc_log0_tdn0_lock0_trim1_web1_fpf5000_fps28_20261110-112723 at frame 4409: skipped 1, dt 71407 us
  - jump in 4kHDR16_unc_log0_tdn0_lock0_trim1_web1_fpf5000_fps28_20261110-112723 at frame 4407: skipped 1, dt 71455 us
  - jump in 4kHDR16_lossless_log1_tdn0_lock0_trim1_web1_fpf5000_fps25_20261110-112643 at frame 111: skipped 1, dt 79985 us
  - jump in 4kHDR16_lossless_log1_tdn0_lock0_trim1_web1_fpf5000_fps25_20261110-112643 at frame 98: skipped 1, dt 79985 us
  - jump in 4kHDR16_lossless_log1_tdn0_lock0_trim1_web1_fpf5000_fps25_20261110-112603 at frame 109: skipped 1, dt 80008 us
  - jump in 4kHDR16_lossless_log1_tdn0_lock0_trim1_web1_fpf5000_fps25_20261110-112603 at frame 104: skipped 1, dt 79996 us
  - jump in 4kHDR16_unc_log0_tdn1_lock0_trim1_web1_fpf5000_fps25_20261110-112502 at frame 71: skipped 1, dt 79994 us
  - jump in 4kHDR16_unc_log1_tdn0_lock0_trim1_web1_fpf5000_fps30_20261110-112434 at frame 48: skipped 1, dt 66668 us

## Merges after the long takes (User, 2026-11-10)

| take | clip | frames | parts | merge s | ms per frame | first ETA error % | intact |
|---|---|---|---|---|---|---|---|
| 00_fps28_20261110-104437 | cDNG_26-11-10_10450114_C0001 | 559 | 3 | 0.1 | 0.179 | None | 1 |

Model (T7 night 2, derived): 0.1 ms + 0.32 us x files already in the main folder per frame; 45,001 frames in 342 s.

## When does 4K need the split (flat vs split, same mode and fps)

Directory walk share of the frame period, derived: s(t) = 5 x c x fps^2 x t (c in s per entry; flat folder); a split at N caps it at 5 x c x N x fps. The flat control runs past its first drop (to Core's safety stop or the tier length).

| mode | fps | variant | take | outcome | s | first drop s | c ns/entry (CPU slope) | Core CPU min 1 -> last | buffer % last 5 min |
|---|---|---|---|---|---|---|---|---|---|
| 4kHDR16 | 28.0 | split 200 | 00_fps28_20261110-104437 | pass_capped_20s | 20.0 |  |  | None -> 136.5 | 0.1 |

## Deletes (media route)

- cDNG_26-11-10_03562910-C0007: 8106 frames, 0 parts, cold, budget 9 s, took 10.0 s
- cDNG_26-11-10_03525320-C0006: 4862 frames, 0 parts, cold, budget 3 s, took 3.8 s
- cDNG_26-11-10_03494415-C0005: 4285 frames, 0 parts, cold, budget 2 s, took 2.9 s
- cDNG_26-11-10_03465206-C0004: 3806 frames, 0 parts, cold, budget 2 s, took 2.3 s
- cDNG_26-11-10_03431702-C0003: 5042 frames, 0 parts, cold, budget 3 s, took 5.7 s
- cDNG_26-11-10_03405408-C0002: 1414 frames, 0 parts, cold, budget 0 s, took 0.4 s
- cDNG_26-11-10_03391901-C0001: 1680 frames, 0 parts, cold, budget 0 s, took 0.4 s
- cDNG_26-11-10_10450114_C0001: 559 frames, 0 parts, warm, budget 0 s, took 0.2 s

## Decisions

    2026-11-10 11:34:35 [S4,S5] night S4,S5 start: card Corsair MP600 MINI A936B442006AC2 fw ERFM11.1, free 166 GB; Core pid 820; drop-in checked; timers-mask rc=0; smart temp 63 C
    2026-11-10 11:34:35 [S4,S5] fixed state: ladder False, merge False, frames_per_folder 5000, speed ramp False, pre-roll True (ok: 5.0 s at 30 fps (measured 26.6), 125 frames, 1.5 GB written and deleted)
    2026-11-10 11:34:35 [S4,S5] audio baseline: record_audio_enabled=True audio_input_device='hw:2,0' input_devices=['hw:2,0'] -> /home/pi/longtakes/nvme-20261110/audio-forensics/20261110-113435-baseline-S4_S5
    2026-11-10 11:34:35 [S4,S5] GO-S4 found (unconditional): unconditional
    2026-11-10 11:35:01 [S4,S5] S4 warmup 4kHDR16_unc_log0_tdn0_lock0_trim1_web1_fpf5000 at 27 fps, 60 s: record_start_failed (0.0 s, dropped 4, first drop 0.0, gap 0, boundary 0)
    2026-11-10 11:35:23 [S4,S5] RESTORE OK
