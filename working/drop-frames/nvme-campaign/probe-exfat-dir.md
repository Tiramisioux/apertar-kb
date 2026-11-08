# exFAT directory probe: create, unlink and merge cost against file count (2026-11-08)

Zero-wear probe on the camera's recording card. It creates N empty files in one new folder, then unlinks them, timing each
call. Empty files allocate no cluster, so the only bytes written were the folders' own directory entries: 9.7 MB at the
most, all freed. The question it answers: how much a frame-file create costs in one exFAT folder as the folder grows. On
rpi-6.12.y every create walks all of the folder's entries under `s_lock` (V-F4 row 16), and Core writes 5 entries per
frame file. Labels follow the KB: **measured** (read off this run), **derived** (arithmetic on measured numbers),
**unconfirmed**.

Run by Claude over ssh, 12:18-12:34 Pi clock, at the owner's request. Core was running and idle (not recording, no
pre-roll), nothing was building, and the WebUI Media page was closed (Core's clip list walks unknown folders only when that
page asks, `ApertarCoreApp.cpp` anchor `discoverMediaLibraryItems`; no timer). Scripts and raw files:
[probe-exfat-dir-raw/](probe-exfat-dir-raw/) (`exfat_dir_probe.py` as briefed, `exfat_merge_probe.py` for step 3b).

## Step 0: state (measured, pasted)

```
/dev/nvme0n1p2 exfat rw,noatime,uid=1000,gid=1000,fmask=0002,dmask=0002,allow_utime=0020,iocharset=utf8,errors=remount-ro
Filesystem        1B-blocks       Used    Available Use% Mounted on
/dev/nvme0n1p2 999960870912 3615752192 996345118720   1% /media/RAW
Corsair MP600 MINI
A936B442006AC2
512
6.12.75+rpt-rpi-2712
 12:18:05 up 2 min,  2 users,  load average: 0.36, 0.23, 0.09
cDNG_26-11-07_C0001
{'state': 'ready', 'recording': False, 'storage_preroll_active': False, 'media_trim_last_unix': None}
0
26850
```

- The card is the KB's test card (serial `A936B442006AC2`, as in findings-2026-11-03/-04). 128 KiB clusters.
- `/media/RAW` held only `cDNG_26-11-07_C0001` (218 entries, the owner's). It did **not** hold the 11-04 clip and
  `warm.bin` that the brief expected: the drive had been emptied before this boot (root mtime 11:58). The probe touched only
  its own `probe_exfat_dir_*` folders, so this did not block it.
- Core binary: `cinemate-port` `f4a1393`, built 2026-11-04 21:52 (`/proc/<pid>/exe` = `~/ApertarCore-build/apertar-core`).
- Two side events during the run (measured, from the kernel log and the CSV): a USB drive (`sda`) was unplugged at about 12:21
  (not used by the probe). One burst of slow creates at files 42,841-42,849 (68 ms decaying to 46 ms) coincides with Claude's
  `ls <probe folder> | wc -l` at 12:24:45, a readdir of the same folder under the same lock (probable cause). It is the only
  burst in 60,000 creates.

## Step 2: 60,000 files, 33-character names (5 entries each)

Create (measured; per block of 1000, the full table is in `exfat_probe_60k.out`):

| files | median ms | p90 ms | max ms |
| ---: | ---: | ---: | ---: |
| 1,000 | 0.159 | 0.290 | 0.533 |
| 5,000 | 1.399 | 1.559 | 2.055 |
| 10,000 | 2.961 | 3.276 | 3.961 |
| 15,000 | 4.529 | 5.050 | 5.581 |
| 20,000 | 6.123 | 6.785 | 7.707 |
| 30,000 | 9.325 | 10.140 | 10.591 |
| 40,000 | 12.530 | 13.333 | 14.136 |
| 45,000 | 14.006 | 14.756 | 15.346 |
| 50,000 | 15.587 | 16.335 | 16.589 |
| 54,000 | 16.914 | 17.605 | 17.893 |
| 60,000 | 18.911 | 19.504 | 20.641 |

- Fit of the block medians: **median_ns = −183,673 + 316.64 × files** (measured). Straight line from the first block to
  the last. The process used one core at 100 % throughout (CPU time = wall time at 4:55), so the walk is pure CPU on cached
  entries.
- **c = 316.64 / 5 = 63.3 ns per directory entry** (derived). That is below the KB's estimate of 80-250 ns (F4, H14, V-F4
  row 18) and inside A0/A1's bound (c < ~450 ns).
- Create total 576.8 s, folder fsync 2.6 ms, `st_size 0 st_blocks 0` (measured). Directory growth 9,699,328 B, against
  9,600,000 B expected (60,000 × 5 × 32 B rounded up to 74 clusters of 128 KiB) (measured).
- Periodic spikes: none at the directory's cluster boundaries (a new 128 KiB cluster every 819.2 files). The median at the
  73 boundary files is 9.76 ms, the next files' 9.68 ms (derived from the CSV). The p90 sits 0.5-1 ms above the median all
  along; the max column is that plus the one burst above.

Unlink, warm cache, in creation order (measured): **5 µs per file, flat** (fit 5,164 ns + 0.00 × files), total 0.5 s
wall (0.34 s inside the calls) for 60,000 files. No walk: the unlink of a name just looked up in this boot finds its slot
directly.

## Step 3: 20,000 files, 16-character names (4 entries each)

Fit **median_ns = −138,911 + 250.10 × files**, so **c = 250.10 / 4 = 62.5 ns** (measured / derived): the same constant as
at 5 entries. The cost scales with directory entries, not with files. Create total 50.9 s, unlink 0.2 s, directory
2,621,440 B (measured).

## Step 3b: merge cost (rename from a 10,000-file folder into a 10,000-file folder)

Two folders of 10,000 empty files (`probe_exfat_dir_123143`, `probe_exfat_dir_123201`, each fit about 309 ns per file, c ≈
62 ns). Then every file of the second was renamed into the first in creation order, file i of the second becoming frame
number 10,000 + i. Numbering continues, as a flatten of split parts does, so no name collides. Both folders were removed
afterwards, in the same boot.

| renamed | target folder holds | median ms | p90 ms | max ms |
| ---: | ---: | ---: | ---: | ---: |
| 1,000 | 11,000 | 3.266 | 3.638 | 4.351 |
| 5,000 | 15,000 | 4.561 | 5.085 | 5.705 |
| 10,000 | 20,000 | 6.141 | 6.851 | 7.616 |

- Fit **median_ns = 2,955,754 + 319.03 × renamed** (measured). Written against the target folder's size D = 10,000 +
  renamed, this is about 319 ns × D − 0.23 ms: **a rename costs what a create costs at the same target size** (derived:
  create at 10,000 = 2.96 ms, rename at D = 10,000 = 2.96 ms). The source lookup adds no visible slope (its slot is found
  by the same short walk each time).
- Per file at 10,000 files: **3.0-3.3 ms** (measured). Extrapolated (derived from the create fit, since the two have the
  same slope): **14.1 ms at 45,000** and **16.9 ms at 54,000**.
- Whole-clip merge of N files = Σ cost(k) for k < N, about 158 ns × N² (derived): **≈ 5.2 min for 45,000, ≈ 7.5 min for
  54,000, ≈ 14 s for 10,000**. That is below the brief's 8-21 min, which assumed c = 80-250 ns. Part folders of 5,000 add a
  short source walk (≤ 1.6 ms per rename at the start of a part) (derived, unmeasured). Wall time of this run was 96 s for
  48 s inside the renames: the script's own `lexists` check before each rename is a second walk of the target.

## Step 4 (cold-cache delete): prepared, not measured

The warm-cache unlink is 5 µs per file; the cold-cache figure (a delete after a reboot) is still **unconfirmed**.
`probe_exfat_dir_125428` (10,000 empty files, create fit 309.0 ns per file) was made on the test card at 12:54 and kept.
The owner's `drop_caches` ran after a reboot at about 13:00 that changed the drive: the NVMe was out and the Samsung T7
(`/dev/sda1`) was on `/media/RAW` for the SSD campaign, so the `--delete-only` run found no folder and did nothing.
**The folder is still on the NVMe test card.** The first mount of that card after a boot is a cold cache by itself: run
`python3 -I ~/exfat_dir_probe.py --delete-only --dir /media/RAW/probe_exfat_dir_125428` then, before anything lists the
folder (WebUI Media page closed; Core's merge scan only checks for `.parts`, and the touch UI's clip browser stays shut),
and record the result here. It also removes the folder (zero wear: empty files).

## Step 5: afterwards (measured)

- `journalctl -u apertar-core --since "-1 hour" | grep "media:"`: the last trims are the boot ones (11:58:42/45 mount,
  11:58:52 delete), none during or after the probe. No clusters were freed, so none was expected.
- `df -B1 /media/RAW`: used 3,615,752,192 B, as at the start.
- `ls -la /media/RAW`: only `cDNG_26-11-07_C0001`.
- NVMe 26.9 °C at the start, 34.9 °C at the end.

## Predicted create cost against the frame period (derived from the 60,000 fit)

| files in the folder | create ms | 25 fps (40 ms) | 30 fps (33.3 ms) | 33 fps (30.3 ms) | 50 fps (20 ms) |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 15,000 | 4.57 | 11 % | 14 % | 15 % | 23 % |
| 22,500 | 6.94 | 17 % | 21 % | 23 % | 35 % |
| 45,000 (30 min at 25) | 14.07 | **35 %** | 42 % | 46 % | 70 % |
| 54,000 (30 min at 30) | 16.91 | 42 % | **51 %** | 56 % | 85 % |
| 59,400 (30 min at 33) | 18.62 | 47 % | 56 % | **61 %** | 93 % |
| 90,000 | 28.31 | 71 % | 85 % | 93 % | 142 % |

This is the walk alone, one create, empty files, an idle machine. In a take the same lock also carries the writers' block
mappings and the fsyncs (F4 §2.3), so these figures are a floor on what the lock carries per frame (derived).

Largest folder for a create of at most 25 % of the period, N = 0.25 × period / (5 × c) (derived, c = 63.3 ns): **31,600
files at 25 fps, 26,300 at 30, 23,900 at 33, 15,800 at 50**. The brief's suggested campaign value of 5,000 files per folder
(a part every 3.3 min at 25 fps) keeps the create under 1.6 ms (≤ 5 % at 33 fps).

## The pre-registered rule: outcome

Rule (decided before the data): at the campaign's target N, a create cost of at most 25 % of the frame period keeps one
folder as the default; above 25 %, a Core knob `[storage] frames_per_folder` (default off) plus a flatten script become
prerequisites of the 15/30-min stages, and the split A/B (one folder vs split, same arm, back to back) is mandatory.

**Outcome: above 25 % at all three targets** (35 % at 45,000 / 25 fps, 51 % at 54,000 / 30 fps, 61 % at 59,400 / 33 fps;
derived). So `frames_per_folder` and the flatten script are prerequisites of the 15/30-min stages, and the split A/B is
mandatory. The 15-min stage at 25 fps (22,500 files, 17 %) is under the line on its own, but the long stages are not.
Either way the campaign runner deletes clips in the boot that wrote them: the warm unlink is 5 µs per file, and the
cold-cache unlink is unmeasured (step 4).

## Summary block (for the planning session)

```
exFAT directory probe, 2026-11-08, test card A936B442006AC2, kernel 6.12.75+rpt-rpi-2712, Core idle (f4a1393):
c = 63.3 ns per directory entry (5-entry names, 60,000 files; 62.5 ns with 4-entry names): measured, linear, no cluster-boundary spikes.
create cost (fit -0.18 ms + 316.6 ns x files): 45,000 files 14.1 ms = 35 % of 40 ms (25 fps); 54,000 files 16.9 ms = 51 % of 33.3 ms (30 fps); 59,400 files 18.6 ms = 61 % of 30.3 ms (33 fps).
unlink, warm cache: 5 us per file, flat; 60,000 files in 0.5 s. Cold cache: not run (needs sudo).
merge (rename into a growing folder) = create cost at the target's size: 3.0-3.3 ms per file at 10,000; 14.1 ms at 45,000, 16.9 ms at 54,000 (derived); whole clip ~5.2 min (45,000), ~7.5 min (54,000).
rule: ABOVE 25 % at every target -> frames_per_folder knob + flatten script are prerequisites of the 15/30-min stages; split A/B mandatory. 25 % ceiling: 31,600 files at 25 fps, 26,300 at 30, 23,900 at 33, 15,800 at 50.
```
