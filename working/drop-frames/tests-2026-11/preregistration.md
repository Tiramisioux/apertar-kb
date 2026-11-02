# Pre-registration, drop-frames tests 2026-11

Written 2026-11-02 before the first B1 take.
The plan is [inspection-2026-11-02.md](../inspection-2026-11-02.md) section 8.3; this page fixes B1's rule and the evening restore list in advance.
Analysis script: [b1_test.py](../../tools/drop-frames-2026-11-01/b1_test.py).

## Changes from the plan agreed before B1

- Take durations as in the plan (User, 2026-11-02): 3 min in B1, B2, B4, U1; 10 min in B3, T1, B-lossy, B6, B7.
- B0.7: `rp1_cfe.track_csi2_errors=1` was already in `cmdline.txt` before 11-01; only `psi=1` was added (backup `cmdline.txt.bak-20261102`). The running `rp1_cfe` lists no such parameter in sysfs, but its debugfs `csi2_errors` counters count (17,460 VC0 `UNMATCHED` before a Core restart, 0 after), so the flag is in effect; `csi2_errors` is read from debugfs.
- Installing `nvme-cli` (B0.10) upgraded util-linux 2.41 -> 2.41.5 (`fstrim` among it) and enabled `nvmf-autoconnect.service`, `nvmefc-boot-connections.service` and `uuidd.socket`: fixed for the whole campaign.
- A0 ran at 34,994 s of uptime (B0.2), so T1's uptime is fixed at ~35,000 s.
- The drive was emptied 2026-11-02 (take #80's clip deleted on User's instruction); nothing on `/media/RAW` must be kept.

## B1

**B1. Interleaved `writer` vs `sync` (the claim's core).**

- Question: with the UI drawing (peaking + zebra on, audio meter in one written state), does `writer` lose more frames at
  capture than `sync` on the same boot, in random order, from the same start state; and is the per-frame cycle slower (G)?
- Fixed: Core `adac040`+journal line; mode by the `/run` drop-in in **both** arms (`Environment=APERTAR_DNG_DONTNEED=<arm>`,
  verified in `environ`: Core prints nothing for a valid value, `CdngEncoder.cpp:86-93`); `SYNC_MS` 1000, `WRITEBACK` on;
  stock sysctl; `buffer=ram`; the UI from B0.9 with no switch; 4K Clear HDR 16-bit uncompressed 25 fps; tracefs buffer 8 MiB
  per CPU set once after each reboot.
- Unit (the scored element): `sudo sh b1-arm.sh <arm>` (restart; Core's mount trim and pre-roll follow,
  `ApertarCoreApp.cpp:10904, 11272`) -> `cat /media/RAW/warm.bin > /dev/null` and record MemFree (equalizes the start: on
  11-01 the arms began at 275-327 vs 507-788 MB; this puts `sync` in its least favourable state, that of #74/#75/#78) ->
  **P1**, 3 min -> **P2**, 3 min, no restart, no delete (the #69 -> #70 positions) -> delete the unit's two folders (Core's
  free-space trim follows, `:10856-10861`) -> cool to <= 40 C.
- Block: reboot -> one unscored 3-min `sync` warm-up take (no unit is first after boot) -> 4 units, 2 per arm, in one of the
  6 balanced orders drawn with a die before the block and written into the KB. Two blocks; extension: a third block in a
  freshly drawn order.
- Analysis (fixed in advance, all one-sided, writer > sync): per-unit lost = P1 + P2; exact permutation test stratified by
  block. Attainable minimum p: 1/36 = 0.028 (2 blocks), 1/216 = 0.0046 (3). Manipulation check: `pgsteal_kswapd` >= 10x higher
  in every `writer` take than in every `sync` take, or the run is void (the drop-in did not take). Covariate: MemFree before
  P1 and P2. Also reported: P1 and P2 separately per arm.
- Duration: per unit ~15 min (restart + pre-roll 1.5, preload 0.5, two takes 6 + stats 1, delete 0.5, cool-down 5); per
  block ~70 min with the reboot, the password and the warm-up; **~2 h 20 min**, +70 min for the extension block.
- Decision rule:
  - **p <= 0.05** and the manipulation check holds: the mode is the lever at the take level (Q1 settled).
  - **0.05 < p <= 0.2**: run the third block, then decide on all three.
  - **p > 0.2**: no mode effect shown with a restart per unit. Before calling it chance, compare `writer` P2 here with B4's
    positions 3-4 (no restart): B4 losing and B1 clean = process age or position is the lever, not the mode.
  - **Position**: `writer` P1 clean and P2 losing in both blocks reproduces #69 -> #70.
  - **G** (G1 per take; G2 in B2): IPC lower and cycles/frame higher under `writer` at equal instructions = G present.
  - **Stall** (per losing take, M4/M5 on the 1 Hz loss times and the CFE holes): a Core or libcamera thread in `_begin`
    with >= 20 ms episodes, and P(hole within 100 ms after an episode) above the take's base rate and above the same figure
    under `sync` = A (a `throttle_direct_reclaim` sleep comes before its `_begin` line, `vmscan.c:6525-6529`, and is invisible
    there: M6 sees it; `pgscan_direct_throttle` is system-wide and names no thread). Wait (field 2) growing >= 40 ms in losing seconds = C (B5 pins every kswapd). `majflt` rising in losing
    seconds = H. None of these, with G present = G alone. None, with G absent = B2 (M3, M6).

## B1 block orders (drawn before each block)

The 6 balanced orders (2 writer W, 2 sync S): WWSS, WSWS, WSSW, SWWS, SWSW, SSWW; die 1-6 in that order.

| Block | Drawn (date, time, method) | Order of the 4 units |
| --- | --- | --- |
| 1 | 2026-11-02 ~19:10 CET, die rolled by User (result 1), after the block's reboot and before any take of the block | WWSS: unit 1 writer, unit 2 writer, unit 3 sync, unit 4 sync |
| 2 | | |
| 3 (extension) | | |

## Restore list (end of every evening)

**Restore list (end of every evening; Patrik's next shoot inherits none of it):** `[storage] buffer=ram`; the sysctls (B3's
reset, read back); the helper's `restore` if B3 applied it; the fill files and `warm.bin` if Patrik wants the space;
`APERTAR_MEDIA_TRIM` drop-in gone; every `/run` drop-in gone (`dontneed.conf`, `LIBCAMERA_LOG_LEVELS`, UI `ExecStart`);
tracefs events off and `buffer_size_kb` back (or reboot); `link-frequency` 891 MHz; `kernel.latencytop=0`; swap on; the
imx585 driver `cd548ef`; Patrik's ladder. At campaign end: `cmdline.txt` from the backup; the baseline-UI worktree removed
when Patrik agrees. `sudo nvme smart-log /dev/nvme0` after each evening.

Checklist (end of every evening):

- [ ] `[storage] buffer=ram`
- [ ] the sysctls (B3's reset, read back)
- [ ] the helper's `restore` if B3 applied it
- [ ] the fill files and `warm.bin` if Patrik wants the space
- [ ] `APERTAR_MEDIA_TRIM` drop-in gone
- [ ] every `/run` drop-in gone (`dontneed.conf`, `LIBCAMERA_LOG_LEVELS`, UI `ExecStart`)
- [ ] tracefs events off and `buffer_size_kb` back (or reboot)
- [ ] `link-frequency` 891 MHz
- [ ] `kernel.latencytop=0`
- [ ] swap on
- [ ] the imx585 driver `cd548ef`
- [ ] Patrik's ladder
- [ ] `sudo nvme smart-log /dev/nvme0` after each evening

At campaign end:

- [ ] `cmdline.txt` from the backup
- [ ] the baseline-UI worktree removed when Patrik agrees

## Results

### B1

| Block | Unit | Arm | P1 lost | P2 lost | P1 MemFree | P2 MemFree | P1 pgsteal_kswapd | P2 pgsteal_kswapd | Valid |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 1 | writer | 357 / 4,148 | 50 / 4,457 | 622 MB | 346 MB | 3,713,840 | 3,442,560 | yes (G1 missing: tid gone after the mode change; fixed for unit 2) |
| 1 | 2 | writer | 280 / 4,224 | 40 / 4,467 | 621 MB | 370 MB | 3,755,840 | 3,333,312 | yes; deviation: NVMe 40.85 C at the unit start (the cool-down wait timed out at 12 min); G1 IPC 1.41 / 1.40 |

Block 1 warm-up (unscored, `sync`, 19:03): 17 / 4,489 lost, `pgsteal_kswapd` 0, `pageoutrun` 0, G1 IPC 1.45; VC0 OVLF 22 between the arm and 19:07 (the window includes the pre-roll and mode switches).
Unit 1 CSI-2 VC0 OVLF per take (1 Hz log): P1 58 in 14 s (all 14 s also lost frames; frames were lost in 173 s), P2 54 in 12 s (1 of them lost frames).

### B2

| Take | Test / arm / cell | Lost | Valid | Note |
| --- | --- | --- | --- | --- |
| | | | | |

### B3

| Cell | Evening | Take | Sysctl | Fill at start | Lost | pageoutrun | Valid |
| --- | --- | --- | --- | --- | --- | --- | --- |
| | | | | | | | |

### B4 + T1

| Take | Test / arm / cell | Lost | Valid | Note |
| --- | --- | --- | --- | --- |
| | | | | |

### T2

| Take | Test / arm / cell | Lost | Valid | Note |
| --- | --- | --- | --- | --- |
| | | | | |

### U1 (+U2)

| Take | Test / arm / cell | Lost | Valid | Note |
| --- | --- | --- | --- | --- |
| | | | | |

### B5

| Take | Test / arm / cell | Lost | Valid | Note |
| --- | --- | --- | --- | --- |
| | | | | |

### B6

| Take | Test / arm / cell | Lost | Valid | Note |
| --- | --- | --- | --- | --- |
| | | | | |

### B7

| Take | Test / arm / cell | Lost | Valid | Note |
| --- | --- | --- | --- | --- |
| | | | | |

### B8 / U3

| Take | Test / arm / cell | Lost | Valid | Note |
| --- | --- | --- | --- | --- |
| | | | | |

### B-lossy

| Take | Test / arm / cell | Lost | Valid | Note |
| --- | --- | --- | --- | --- |
| | | | | |
