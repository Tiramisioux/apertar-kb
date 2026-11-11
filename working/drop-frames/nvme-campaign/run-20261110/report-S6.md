# NVMe campaign report: S6 (2026-11-11 04:54:49)

Labels: every number here is measured by the runner on this night unless it says derived. Card A936B442006AC2.

## Takes

| take | stage | arm | fps | tier s | outcome | s | dropped | first drop s | numbering gap | boundary drops | Core CPU avg | buffer peak % | nvme max C | GB | merge s | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|

## Fix checks (whole campaign so far)

- **8ec2f1a, part folder made on the writer**: 48 part boundaries crossed in 76 split takes (338769 frames); 0 drops within 64 frames after a boundary; 0 copy-slot drops in all. The buffer around a boundary (1 s before to 3 s after) rose at most 86.9 points above its take median (mean 8.23, 50 boundaries). Expectation if the fix holds: 0 boundary drops, 0 copy-slot drops (night 2 on the old binary: 3 copy-slot drops at 1 of ~40 boundaries).
- **e298d4a, frame index jump logged and counted**: 255 index jumps in Core's stats over the campaign; 0 takes had a numbering gap explained by them (0 frames, no picture lost); 29 takes had missing frames NOT explained by index jumps (each is a drop).
  - 4kHDR16_unc_log0_tdn0_lock0_trim1_web1_fpf5000_fps28_20261110-034628: missing 1, index_jumps 1, frames 3778
  - 4kHDR16_unc_log0_tdn0_lock0_trim1_web1_fpf5000_fps28_20261110-034921: missing 1, index_jumps 1, frames 4252
  - 4kHDR16_unc_log1_tdn0_lock0_trim1_web1_fpf5000_fps28_20261110-110124: missing 1, index_jumps 1, frames 122
  - 4kHDR16_unc_log1_tdn0_lock0_trim1_web1_fpf5000_fps28_20261110-110204: missing 2, index_jumps 2, frames 123 129
  - 4kHDR16_unc_log1_tdn0_lock0_trim1_web1_fpf5000_fps30_20261110-112434: missing 2, index_jumps 2, frames 38 47
  - 4kHDR16_unc_log0_tdn1_lock0_trim1_web1_fpf5000_fps25_20261110-112502: missing 1, index_jumps 1, frames 70
  - 4kHDR16_lossless_log1_tdn0_lock0_trim1_web1_fpf5000_fps25_20261110-112603: missing 2, index_jumps 2, frames 103 108
  - 4kHDR16_lossless_log1_tdn0_lock0_trim1_web1_fpf5000_fps25_20261110-112643: missing 2, index_jumps 2, frames 97 110
  - 4kHDR16_unc_log0_tdn0_lock0_trim1_web1_fpf5000_fps28_20261110-112723: missing 4, index_jumps 4, frames 4406 4408 4414 4416
  - 4kHDR16_lossless_log1_tdn0_lock0_trim1_web1_fpf5000_fps26_20261110-210700: missing 1, index_jumps 1, frames 139
  - jump in 4kHDR16_unc_log0_tdn0_lock0_trim1_web1_fpf5000_fps26_20261111-033235 at frame 16135: skipped 1, dt 76918 us
  - jump in 4kHDR16_unc_log0_tdn0_lock0_trim1_web1_fpf5000_fps26_20261111-033235 at frame 16125: skipped 1, dt 76900 us
  - jump in 4kHDR16_unc_log0_tdn0_lock0_trim1_web1_fpf5000_fps27_20261111-031539 at frame 19108: skipped 1, dt 74023 us
  - jump in 4kHDR16_unc_log0_tdn0_lock0_trim1_web1_fpf5000_fps27_20261111-031539 at frame 19099: skipped 2, dt 111113 us
  - jump in 4kHDR12_unc_log0_tdn0_lock0_trim1_web1_fpf5000_fps30_20261111-030122 at frame 43: skipped 1, dt 66668 us
  - jump in 4kHDR12_unc_log0_tdn0_lock0_trim1_web1_fpf5000_fps30_20261111-030122 at frame 38: skipped 1, dt 66668 us
  - jump in 4kHDR12_unc_log0_tdn0_lock0_trim1_web1_fpf5000_fps25_20261111-025914 at frame 2305: skipped 1, dt 79982 us
  - jump in 4kHDR12_unc_log0_tdn0_lock0_trim1_web1_fpf5000_fps25_20261111-025914 at frame 2292: skipped 1, dt 79959 us
  - jump in 4kHDR12_unc_log0_tdn0_lock0_trim1_web1_fpf5000_fps25_20261111-025826 at frame 294: skipped 1, dt 80001 us
  - jump in 4kHDR12_unc_log0_tdn0_lock0_trim1_web1_fpf5000_fps26_20261111-025743 at frame 174: skipped 1, dt 76925 us

## Merges after the long takes (User, 2026-11-10)

| take | clip | frames | parts | merge s | ms per frame | first ETA error % | intact |
|---|---|---|---|---|---|---|---|
| 00_fps28_20261110-104437 | cDNG_26-11-10_10450114_C0001 | 559 | 3 | 0.1 | 0.179 | None | 1 |
| 00_fps27_20261111-031539 | cDNG_26-11-11_03160218_C0001 | 19116 | 4 | 85.3 | 4.462 | -27.7 | 1 |
| 00_fps26_20261111-033235 | cDNG_26-11-11_03325911_C0002 | 16137 | 4 | 58.4 | 3.619 | -21.7 | 1 |
| 00_fps25_20261111-034627 | cDNG_26-11-11_03465110_C0001 | 18882 | 4 | 67.0 | 3.548 | -15.8 | 1 |
| 00_fps38_20261111-040410 | cDNG_26-11-11_04043335_C0002 | 30231 | 7 | 188.9 | 6.249 | -21.5 | 1 |
| 00_fps37_20261111-043244 | cDNG_26-11-11_04330728_C0001 | 33314 | 7 | 215.8 | 6.478 | -15.6 | 1 |

Model (T7 night 2, derived): 0.1 ms + 0.32 us x files already in the main folder per frame; 45,001 frames in 342 s.

## When does 4K need the split (flat vs split, same mode and fps)

Directory walk share of the frame period, derived: s(t) = 5 x c x fps^2 x t (c in s per entry; flat folder); a split at N caps it at 5 x c x N x fps. The flat control runs past its first drop (to Core's safety stop or the tier length).

| mode | fps | variant | take | outcome | s | first drop s | c ns/entry (CPU slope) | Core CPU min 1 -> last | buffer % last 5 min |
|---|---|---|---|---|---|---|---|---|---|
| 4kHDR16 | 28.0 | split 200 | 00_fps28_20261110-104437 | pass_capped_20s | 20.0 |  |  | None -> 136.5 | 0.1 |
| 4kHDR16 | 27.0 | split 5000 | 00_fps27_20261111-031539 | drop | 708.2 | 708.1 |  | 220.9 -> 219.7 | 3.7 |
| 4kHDR16 | 26.0 | split 5000 | 00_fps26_20261111-033235 | drop | 621.0 | 621.0 |  | 188.9 -> 187.5 | 17.5 |
| 4kHDR16 | 25.0 | split 5000 | 00_fps25_20261111-034627 | buffer_full | 758.1 |  |  | 162.3 -> 152.7 | 4.5 |
| 4kSDR12 | 38.0 | split 5000 | 00_fps38_20261111-040410 | buffer_full | 799.3 |  |  | 261.6 -> 253.6 | 40.8 |
| 4kSDR12 | 37.0 | split 5000 | 00_fps37_20261111-043244 | pass_15min | 900.4 |  |  | 221.6 -> 256.5 | 58.5 |

## Deletes (media route)

- cDNG_26-11-11_03465110_C0001: 18882 frames, 0 parts, warm, budget 0 s, took 19.4 s
- cDNG_26-11-11_03325911_C0002: 16137 frames, 0 parts, warm, budget 0 s, took 36.3 s
- cDNG_26-11-11_03160218_C0001: 19116 frames, 0 parts, warm, budget 0 s, took 32.8 s
- cDNG_26-11-11_03021512_C0029: 1619 frames, 0 parts, warm, budget 0 s, took 2.3 s
- cDNG_26-11-11_03014619_C0028: 50 frames, 0 parts, warm, budget 0 s, took 0.0 s
- cDNG_26-11-11_02593800_C0027: 2320 frames, 0 parts, warm, budget 0 s, took 0.8 s
- cDNG_26-11-11_02584917_C0026: 320 frames, 0 parts, warm, budget 0 s, took 0.0 s
- cDNG_26-11-11_02580622_C0025: 201 frames, 0 parts, warm, budget 0 s, took 0.0 s
- cDNG_26-11-11_02572801_C0024: 93 frames, 0 parts, warm, budget 0 s, took 2.6 s
- cDNG_26-11-11_02564903_C0023: 99 frames, 0 parts, warm, budget 0 s, took 0.0 s

## Decisions

    2026-11-11 04:54:28 [S6] night S6 start: card Corsair MP600 MINI A936B442006AC2 fw ERFM11.1, free 180 GB; Core pid 823; drop-in checked; timers-mask rc=0; smart temp 55 C
    2026-11-11 04:54:28 [S6] fixed state: ladder False, merge False, frames_per_folder 5000, speed ramp False, pre-roll True (ok: 5.0 s at 60 fps (measured 60.0), 299 frames, 1.6 GB written and deleted)
    2026-11-11 04:54:28 [S6] audio baseline: record_audio_enabled=True audio_input_device='hw:2,0' input_devices=['hw:2,0'] -> /home/pi/longtakes/nvme-20261110/audio-forensics/20261111-045428-baseline-S6
    2026-11-11 04:54:28 [S6] GO-S6 found (unconditional): unconditional
    2026-11-11 04:54:28 [S6] S6 4kSDR12: no 30-min split pass and no --flat-control: no flat control
    2026-11-11 04:54:28 [S6] S6 4kHDR16: no 30-min split pass and no --flat-control: no flat control
    2026-11-11 04:54:28 [S6] S6 4kHDR12: no 30-min split pass and no --flat-control: no flat control
    2026-11-11 04:54:28 [S6] stage S6 done
    2026-11-11 04:54:49 [S6] RESTORE OK
