# NVMe campaign: preregistration (2026-11-10, before S1)

Written before any campaign take. Changing anything here after S1 starts goes in findings.md as a deviation.

## Die rolls (d6, Python `secrets`, 2026-11-10 03:30:07, rolled by Claude as Patrik asked)

| Lever / stage | Roll | Rule | Result |
| --- | --- | --- | --- |
| ABBA log | 1 | odd = baseline first (AB), even = BA | AB |
| ABBA web | 5 | same | AB |
| S5 mode order | 1 | (roll-1)-th permutation below | 4kHDR16, 4kSDR12, 4kHDR12 |
| S6 mode order | 3 | same | 4kSDR12, 4kHDR16, 4kHDR12 |
| Part B | later | rolled per card before Part B | - |

Permutations of (4kHDR16, 4kSDR12, 4kHDR12), itertools order: 1 HDR16,SDR12,HDR12 · 2 HDR16,HDR12,SDR12 ·
3 SDR12,HDR16,HDR12 · 4 SDR12,HDR12,HDR16 · 5 HDR12,HDR16,SDR12 · 6 HDR12,SDR12,HDR16.

## Decisions (Patrik 2026-11-10: "defaults", "do only 16:9", "skip" S0's attended checks)

- Card A936B442006AC2 (Corsair MP600 Mini, 1 TB); 10 TB written cap; no second 30-min take.
- **16:9 only**: no 1.85:1 / 2.39:1 crop arms, no crop probe (`CROPS=` stays empty).
- MLV no; depth-2 block no; paced probe no; phase-lock probe no.
- R4 deviation accepted: at the 3-min tier a cell is out only after two concordant drops (cell rule below).
- R13 deviation accepted: no split pair at 15 min; the 30-min pair is S5 unsplit / S6 split.
- Part B default: 30-min HDR16 + 15-min SDR12 per card.
- Power off between nights (poweroff-after-night.sh, after the restore list reads back).
- **S0 skipped as an attended session.** Done read-only: power (`get_throttled` 0x0, EXT5V 5.02 V), card empty
  (932 GB free), binary e298d4a with `index_jumps=` in the stats line (smoke 2026-11-10). Not done: the forced-drop
  check (the per-drop journal lines are read from the first real drop instead), fsck.exfat -n, the smart-log
  baseline and timer masking (helper not installed yet: no smart rows until it is; man-db.timer may fire at 13:17).

## Thresholds (plan §7)

- Cell (S2/S3): clean 3-min + clean 5-min = carried; two concordant 3-min drops = out; 1-1 = a third 3-min take
  decides, then the 5-min; a 5-min drop = a third 3-min, then a second 5-min. Walk 1 fps, up while carried, down while out.
- Start fps: HDR16 28, SDR12 from the meter (44/46/50), HDR12 30. HDR16 lossless+Log arm only above 25 fps pre-roll.
- A take stops at its first dropped frame. A numbering gap (missing == index_jumps, every drop counter 0) is not a drop.
  A boundary drop = a drop within 64 frames after a multiple of frames_per_folder.
- Void (repeat, not a verdict): Core PID change, FE depth != 4, audio missing or ALSA fault, card serial, rw mount,
  ramp/ladder/pre-roll-auto/merge state, tuning, UI not drawing, busy sessions, web client died.
- Fill gate: free >= planned x 1.03 + 10 GB, deleting the oldest ledger clips through the media route.
- Split need: directory walk s(t) = 5·c·fps²·t, t* = 0.6 / (5c·fps²), c = 63.3 ns (probe); measured c per flat take.
- Merge after every take of 15 min or more; Core's `clip merge: done` seconds recorded.

## Dry-run plan (model sizes; the runner replaces them with measured means)

```
card usable ~990 GB; fill gate: free >= planned x 1.03 + 10 GB; split 5000 frames per folder; merge after tiers >= 900 s
4kHDR16 16.59 MB/frame; at 28 fps: 3 min 84 GB, 5 min 139 GB, 15 min 418 GB, 30 min 836 GB (871 GB with margin); flat walk share at 30 min 45 %, split 4.4 %
4kSDR12 12.44 MB/frame; at 44 fps: 3 min 99 GB, 5 min 164 GB, 15 min 493 GB, 30 min 985 GB (1025 GB with margin; fit-limited); flat walk share 110 %, split 7.0 %
4kHDR12 12.44 MB/frame; at 30 fps: 3 min 67 GB, 5 min 112 GB, 15 min 336 GB, 30 min 672 GB (702 GB with margin); flat walk share 51 %, split 4.7 %
```
