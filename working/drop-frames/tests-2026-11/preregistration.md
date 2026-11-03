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

Block 2 measurement changes (not the takes): `vb2/vb2_buf_done` filtered to the CFE raw node (`type == 1 && bytesused > 10000000`), the saved trace chowned to the sudo user (b1-arm.sh `df56ba0`).

The 6 balanced orders (2 writer W, 2 sync S): WWSS, WSWS, WSSW, SWWS, SWSW, SSWW; die 1-6 in that order.

| Block | Drawn (date, time, method) | Order of the 4 units |
| --- | --- | --- |
| 1 | 2026-11-02 ~19:10 CET, die rolled by User (result 1), after the block's reboot and before any take of the block | WWSS: unit 1 writer, unit 2 writer, unit 3 sync, unit 4 sync |
| 2 | 2026-11-02 ~20:50 CET, die rolled by User (result 4), before the block's reboot | SWWS: unit 1 sync, unit 2 writer, unit 3 writer, unit 4 sync |
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
| 1 | 3 | sync | 1 / 4,512 | 47 / 4,459 | 609 MB | 925 MB | 54,720 | 37,760 | yes; NVMe 38.85 C at the start; G1 IPC 1.50 / 1.44. Before it: an extra `writer` arm at 19:48 and a second `sync` arm at 19:49:31 (no take in between) |
| 1 | 4 | sync | 0 / 4,512 | 108 / 4,397 | 553 MB | 764 MB | 58,816 | 44,672 | yes; NVMe 39.85 C at the check (40.85 C a second later, the sensor's 1 C step); G1 IPC 1.49 / 1.43 |
| 2 | 1 | sync | 1 / 4,510 | 72 / 4,435 | 619 MB | 1060 MB | 55,971 | 32,319 | yes; NVMe 38.85 C at the start; G1 IPC 1.53 / 1.44; arm run twice (20:54:05, 20:56:39), the second is the unit's restart |
| 2 | 2 | writer | 2 / 4,510 | 250 / 4,257 | 605 MB | 355 MB | 4,052,408 | 3,383,360 | yes; NVMe 39.85 C at the check (40.85 C at the print); G1 IPC 1.46 / 1.41 |
| 2 | 3 | writer | 225 / 4,281 | 7 / 4,503 | 592 MB | 360 MB | 3,842,368 | 3,763,648 | yes; NVMe 39.85 C at the start; G1 IPC 1.43 / 1.40 |
| 2 | 4 | sync | 0 / 4,514 | 80 / 4,424 | 604 MB | 837 MB | 56,640 | 46,464 | yes; NVMe 37.85 C at the start; G1 IPC 1.50 / 1.44; a `writer` arm ran by mistake at 22:27 before the unit's `sync` arm (no take in between) |

**B1 result (b1_test.py on both blocks, 2026-11-02 22:50):** per-unit lost writer 407, 320 | 252, 232; sync 48, 108 | 73, 80.
Exact one-sided permutation test stratified by block: T = 1,211, 1 of 36 relabelings >= T, **p = 1/36 = 0.028**.
Manipulation check PASS (min writer `pgsteal_kswapd` 3,333,312 >= 10 x max sync 58,816). P1 / P2 per arm: writer
216 / 87 mean, sync 0.5 / 77 mean. MemFree before P1: writer 592-622 MB, sync 553-619 MB.

Against the decision rule: p <= 0.05 with the manipulation check holding: **the mode is the lever at the take level
(Q1 settled)**. Position (writer P1 clean, P2 losing in both blocks): not reproduced (writer P1 lost in 3 of 4 units).
G: CameraManager IPC lower under writer (P1 1.41-1.46) than under sync (P1 1.49-1.53): G present (**probable**:
instructions per frame not compared). Stall: `allocstall` 0-5 per take, `pgmajfault` ~0: A and H not supported.
The sync residual (one take per unit losing 47-108, warm-ups 9-17) is CFE raw-buffer starvation without reclaim:
[findings-2026-11-02.md](findings-2026-11-02.md).

Block 2 warm-up (unscored, `sync`, 20:50): 9 / 4,497 lost, `pgsteal_kswapd` 0, G1 IPC 1.44; raw-node trace: 9 completions with `owned_by_drv = 0` (minutes 1/6/2, as the losses 1/6/2).

Block 1 (b1_test.py, 2026-11-02 20:40): per-unit lost writer 407, 320; sync 48, 108; complete separation within the block, p = 1/6 (the minimum one block can reach; the pre-registered decision needs block 2). Manipulation check PASS (min writer `pgsteal_kswapd` 3,333,312 >= 10 x max sync 58,816). P1 / P2 per arm: writer 357, 280 / 50, 40; sync 1, 0 / 47, 108.

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

## Exploratory, evening 2 (2026-11-03): 16 raw camera buffers (User's request; outside the plan, unscored)

Written before the take. Question: does doubling the raw buffers (8 -> 16, `apertar-tune set raw_buffers=16`, the
override file; Core restarted by `b1-arm.sh sync --trace-buffer` after a reboot) remove the CFE raw-buffer starvation
that every B1 sync unit showed (48-108 lost per unit, one losing take each; 11-01 #41: 12 buffers under writer, no
effect)? Setup as a B1 sync unit: Core `4b14a79`, UI `c153c33`, drive emptied (User's 25 clips deleted), `warm.bin`
read before P1, P1 + P2 3 min each, NVMe <= 40 C at the start, raw-node trace filtered as in block 2. Verified before
P1: journal `RAW buffers: ... count=16` and `media tune: ... override=/dev/shm/... raw_buffers=16`.

Rule: both takes <= 2 lost **and** no `owned_by_drv = 0` completion in the trace during the takes -> run a confirming
mini-block (2 units at 16, 2 at 8, order by die) before 16 goes into the base file. Otherwise: 16 does not cure it at
n = 1 (report mean `owned_by_drv` per take: if it rises by ~8 while losses stay, user space holds the extra buffers too,
a throughput deficit; if it rises and losses fall but not to 0, a partial cure) and the evening goes on to G2/M6.

First attempt (20:07, no take run): the override, then in `/dev/shm`, was deleted by logind's `RemoveIPC` when the
session that wrote it ended; Core started with `raw_buffers=8`. The override moved to `/run/apertar-media/`
(Core `2edc6d0`, tools in the KB); the try runs after that.

| Take | Lost | `owned_by_drv = 0` | Mean `owned_by_drv` | `pgsteal_kswapd` | G1 IPC | Note |
| --- | --- | --- | --- | --- | --- | --- |
| warm-up (unscored, 20:14) | 0 / 4,510 | 1 | 14.46 (of 16) | 0 | 1.52 | first take after the boot's arms; B1 warm-ups at 8 buffers lost 17 and 9 |
| P1 (20:19) | 26 / 4,475 | 1 | 6.52 (30 s bins 11.8 4.9 4.5 4.6 4.4 6.1 9.9) | 69,848 | 1.44 | NVMe 39.85 C at the start |
| P2 (20:23) | 123 / 4,377 | 1 | 5.69 (10.1 4.2 4.1 4.1 4.0 4.1 9.8) | 67,840 | 1.44 | |

**Reading against the rule:** not clean (26 + 123 = 149 lost; B1 sync units at 8 buffers 48-108): 16 buffers do not
cure it (**measured**, n = 1 unit); no mini-block. User space takes up the extra buffers: after ~30 s it holds ~11.5 of
16 at a steady level (at 8: ~6 in a losing take, ~1.5 in a clean one), as the rule's first branch predicted. New: the
losses at 16 come **without** CFE starvation (one `owned_by_drv = 0` per take against 26 and 123 lost), while at 8 the
two counts matched in 8 of 8 takes: a second loss path behind the CFE (libcamera's pipeline or Core), **unconfirmed**
where. The override was cleared at 20:28 (`apertar-tune clear`); the base file keeps `raw_buffers = 8`.

## G2 under sync, evening 2 (2026-11-03; adapted from 8.3 B2 G2, unscored)

Written before the takes. B1 left the sync residual open (one take per unit losing, CFE raw-buffer starvation at 8
buffers), so G2 runs as one sync unit (P1 + P2, 3 min each, 8 raw buffers, `warm.bin` before P1) with
`LIBCAMERA_LOG_LEVELS=IPARPI:ERROR,RPI:0,RPiStream:0` (a `/run` drop-in that sorts after the `/etc` `libcamera-log.conf`,
so the merged value wins), parsed per take with `working/tools/libcam_stages.py` from `journalctl -o cat`. The plan's
writer-vs-sync comparison is replaced by losing-vs-clean within the arm; if both takes lose or both stay clean, the
comparison is with B1's numbers only and says less.

Rule: a stage (CFE dequeue -> IPA signalled -> ISP input queued -> ISP input complete) whose median or p90 is clearly
longer in the losing take than in the clean one, while the CFE arrival interval stays at 40 ms, holds the buffers
(libcamera; G in its narrow sense). All stages equal and only the CFE arrival interval or Core's own handling differing:
the holding is outside these stages (Core's completion path, the copy, or the preview), next M6. A journald
"Suppressed" line in the window makes that take's stage numbers void (rate limit).

| Take | Lost | cfe -> signal median / p90 (ms) | signal -> be_start | be_start -> be_done | CFE interval median / p90 | Note |
| --- | --- | --- | --- | --- | --- | --- |
| P1 (20:37) | 2 / 4,510 | 16.5 / 27.5 | 0.5 / 1.2 | 20.8 / 40.5 | 40.0 / 40.1 | raw stats 6.5 ms; per 20 s: BE 21-37 ms, wait flat ~17 ms |
| P2 (20:41) | 108 / 4,398 | **199.9 / 230.6** | 0.5 / 1.4 | **37.7 / 46.9** | 40.0 / 40.1 | raw stats 6.7 ms; per 20 s: BE pinned at 39 ms and the wait at ~215 ms from 20-40 s on |

libcamera's log went to `LIBCAMERA_LOG_FILE=/run/apertar-media/libcamera-g2.log` (journald suppressed ~half the lines at
~425/s; no take ran with the journal route), every frame logged (5,554 and 5,425 traced), no drop lines. Preview only
(before the take): BE ~10 ms, wait 0.1 ms.

**Reading against the rule:** in the losing take the ISP back-end stage (`Input re-queue to ISP` -> `ISP Input buffer
complete`) is clearly longer (median 37.7 vs 20.8 ms) while the CFE delivers every 40 ms, and frames wait ~200 ms (~5
frames) before the IPA step: the raw buffers are held in front of the back end (**measured**, n = 1 pair). The take is
in one of two states: near capacity but stable (P1) or saturated from its first 20-40 s on (P2). Whether the 39 ms is
ISP work or the back end waiting for something periodic (an output buffer, a request returned by Core after the
preview) is **unconfirmed**: libcamera starts a frame in the back end only with a free request.

## UI preview off during the take, evening 2 (B2 "UI dose-response" row, its 0 point, under sync; unscored)

Written before the takes. One sync unit as above (G2 log on, 8 raw buffers) with `APERTAR_UI_PREVIEW_RECORDING_FPS=0`
in a `/run` drop-in for `apertar-ui-direct` (UI restart): while recording, the UI hands every preview frame back
unimported and undrawn (`ApertarPreviewSocketClient.cpp:488-494`). Rule: both takes <= 2 lost and the back end at its
preview-only level (wait < 20 ms in every 20-s bin) = the UI's preview handling paces the per-frame cycle (the 11-01
dose-response under writer, now under sync), next the 12-fps point; losses and a saturated back end as before = the
preview consumer is not the gate, next M6 on the back end's wait.

| Take | Lost | wait median (ms) | BE median (ms) | max 20-s wait | Note |
| --- | --- | --- | --- | --- | --- |
| P1 (20:53) | 4 / 3,030 | - | - | - | **void**: the CFexpress test card was pulled while mounted at 20:52:26 and a 67 %-full card with User's 10-28 clips mounted at 20:52:59 (cold, 25 C, so the cool-down check passed at once; no `warm.bin` on it, MemFree 2.8 GB at the start; queue peak 78/12) |
| P2 (20:57) | - | - | - | - | **void**: stopped by the lead at ~20:58 (wrong card); that card was pulled while mounted at 20:58:49 |

| P1 repeat (21:00) | **0 / 4,512** | 15.2 | 10.3 | 16 | test card (Corsair MP600 MINI, serial A936B442006AC2) checked before P1 and P2; per 20 s wait 14-16, BE 9-13 ms (preview-only level) |
| P2 repeat (21:04) | **0 / 4,508** | 16.4 | 21.8 | 18 | per 20 s wait 16-18, BE rising 21 -> 30-35 ms; G1 IPC 1.57 / 1.48 |

**Reading against the rule:** both takes <= 2 lost and the wait < 20 ms in every 20-s bin: the UI's preview handling
paces the per-frame cycle (**probable**: n = 1 unit; with B1's rate of one losing take per sync unit, two clean takes
by chance are ~1 in 4). The back end still slows in P2 without the UI drawing (21 -> 35 ms), as in G2's clean P1: the
UI is the load that tips the system, not the only one. Next by the rule: the 12-fps point.

Repeated 21:00 on the test card (rows above). The two test clips (`cDNG_26_11_03_20533423_C0001`, `cDNG_26_11_03_20571717_C0001`) are on User's card until it is back: delete only those, after a read-only `fsck.exfat -n`. Method note: the unit loop's cool-down check cannot tell a swapped card; it should also check the medium (serial, `warm.bin` present) before P1.


## UI preview at 12 fps during the take, evening 2 (the dose-response's middle point, under sync; unscored)

Written before the takes. As the preview-off unit, with `APERTAR_UI_PREVIEW_RECORDING_FPS=12` (the UI shows at most 12
of the 25 frames per second while recording). Rule: both takes <= 2 lost with the wait < 20 ms in every 20-s bin = a
12-fps preview during takes is enough margin (a candidate default while recording, User decides); a losing take with
the saturated wait = 12 fps still tips it: next a preview change that does not gate the cycle.

| Take | Lost | wait median (ms) | BE median (ms) | max 20-s wait | Note |
| --- | --- | --- | --- | --- | --- |
| P1 (21:22) | 4 / 4,503 | 19.7 | 34.9 | 152 | per 20 s BE 35-38 ms, the wait tipping at 160-200 s; `pgsteal_kswapd` 95 k; G1 IPC 1.41 |
| P2 (21:25) | **330 / 4,175** | 221.6 | 39.3 | 240 | saturated from 20 s on, BE 41-43 ms (above the 40-ms frame interval); `pgsteal_kswapd` **723 k**; G1 IPC **1.29** |

**Reading against the rule:** a losing take with the saturated wait: 12 fps still tips it. With the other units the
preview dose-response under sync is **not monotone** (off: 0 + 0; 12 fps: 4 + 330; full: 2 + 108 here, 48-108 per unit
in B1): the UI's preview handling is **not supported** as the main lever under sync, and the preview-off unit's
"probable" is withdrawn (chance ~1 in 4 at n = 1). What all ten logged takes share (**measured**): the ISP back end
takes ~10 ms per frame with the preview alone and 20-43 ms while recording, and a take loses frames when it reaches
~40 ms; the worst take also had the most reclaim (723 k) and the lowest CameraManager IPC (1.29). The common suspect is
memory contention slowing the back end (a DMA engine) while recording: G in the inspection's broad sense, located in
the ISP back end (**probable**).

## `[storage] buffer=frames` instead of `ram`, evening 2 (A0's mode; unscored)

Written before the takes. As the G2 unit (sync, 8 raw buffers, full preview: the UI cap drop-in removed, `warm.bin`
before P1, libcamera log to the file), with `set_buffer_mode value=frames` (Patrik's `[storage] buffer`; back to
`ram` afterwards). Both modes copy each frame into Core's raw pool; `frames` caps the write queue at 12 frames
(~200 MB) instead of a RAM budget of up to ~1.3 GB, so the test is about the memory the queue and its pool tie up,
not about a copy fewer. Rule: both takes <= 2 lost and the back end below ~30 ms in every 20-s bin = the RAM queue's
footprint is a lever (next: a smaller `buffer_ram_fraction` as the shipping candidate, User decides); a losing take
with the back end at ~40 ms = the queue's footprint is not what slows the back end.

| Take | Lost | wait median (ms) | BE median (ms) | max 20-s BE | `pgsteal_kswapd` | Note |
| --- | --- | --- | --- | --- | --- | --- |
| | | | | | | |
