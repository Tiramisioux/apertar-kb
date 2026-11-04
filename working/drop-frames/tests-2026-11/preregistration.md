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
imx585 driver `cd548ef`; Patrik's ladder; Core's `tuning_file` back to automatic, read back. At campaign end: `cmdline.txt` from the backup; the baseline-UI worktree removed
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
- [ ] Core `tuning_file` back to automatic, read back (`ST`, `J`, the libcamera line, the settings file against the 'before' record; `tier1-prep-2026-11-03.md` section 4)
- [ ] `sudo nvme smart-log /dev/nvme0` after each evening
- [ ] after an unsupervised run: `sudo rm /etc/sudoers.d/apertar-b1-arm /usr/local/libexec/apertar-b1-arm` (User)

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
| P1 (21:40) | **590 / 3,915** | 239.9 | 40.9 | 44 | **849,185** | saturated from 20 s on, BE 43-44 ms; G1 IPC 1.31; frames mode confirmed (no `queue_budget` on the clip line) |
| P2 (21:44) | 181 / 4,325 | 216.0 | 39.1 | 41 | 42,988 | saturated from 20 s on; G1 IPC 1.33 |

**Reading against the rule:** losing takes with the back end at ~40-44 ms: the RAM queue's footprint is not what slows
the back end (frames mode is not better, n = 1). `[storage] buffer` goes back to `ram` with the restore list.

## Memory load without a take, evening 2 (no recording; unscored)

Written before the run. Core idle with the live preview and libcamera's debug log on; 30 s baseline, then 60 s with
two `dd if=/dev/zero of=/dev/null bs=64M` processes as user pi (memory write load, no file, no recording), then 30 s
after. Rule: the back end's per-frame time (`Input re-queue to ISP` -> `ISP Input buffer complete`, median per 10 s)
rising from its idle level to >= ~30 ms under the load and falling back after = memory contention alone slows the
back end (the mechanism of the losing takes, without the recording path); no change = the slowdown needs something of
the recording path itself (its DMA, its buffers), not bandwidth in general.

| Run | Mode | ISP back end median / p90, no load | under 2 x `dd` (60 s) | after | Camera delivery under load |
| --- | --- | --- | --- | --- | --- |
| 21:50 | idle ladder rung, 4K SDR12 30 fps (8.3 MB frames) | 10.9 / 13.3 ms | 23.6-23.8 / 26-27 ms | 10.9 ms | 33.3 ms (no loss) |
| 21:55 | take mode, 4K Clear HDR 16-bit 25 fps uncompressed, not recording | 10.9 / 12.3 ms | **95 / 148 ms**, wait **605 ms** | 10.9 ms | **92 ms (~11 fps: more than half the frames lost)** |

**Reading against the rule:** in the take mode the back end rises from its idle level far past ~30 ms under memory load
alone and falls straight back after it: memory contention alone slows the ISP back end and, through the serial
pipeline, starves the CFE (**measured**; the dd load is heavier than a take's traffic, so it shows the chain, not the
size of a take's share). In SDR12 the back end doubles (23.7 ms) and stays under its frame interval. This is the
mechanism of the losing takes (G of the inspection, located in the ISP back end): what loads memory during a take,
and why it tips one take and not the next, is the open question.

## TDN off by a tuning copy, evening 3 (Tier 1 (1), `tier0-2026-11-03.md` section 5; unscored)

Pre-registered in this commit (its hash goes into the findings), pushed before the warm-up with User's OK. Analysis =
`be_overlap.py` and `take3v3.sh` as in this commit's parent (re-run on `raw-2026-11-03.tgz` they reproduce the TDN-on
columns below); any later change to a metric is a listed deviation.
Core `c747f09` (fixed in advance; listed deviation, decided with User before any data: the plan fixed `31d5418`, the Pi's build carries two later WebUI commits, `fe5d592` and `c747f09`, from another session, which add the `test_input` socket command and WebUI code only, nothing in the capture or record path, code read 2026-11-04), UI `c153c33`. Each unit as G2: sync (`b1-arm.sh sync`, Core restarted per unit), 8 raw
buffers, 4K Clear HDR 16-bit uncompressed 25 fps, full preview (`ui switches:` empty), `warm.bin` before P1, libcamera's log
to `/run/apertar-media/libcamera-e3.log`, test card serial A936B442006AC2, P1 + P2 of 3 min by `take3v3.sh`, the same
chart and light in every unit. Arms: **F** = `set_tuning_file path=/home/pi/Tuning-Files/imx585_clearHDR_notdn.json`
(`defaults-pisp/imx585_clearHDR.json` minus its 3 `tdn` blocks, `tools/tdn_strip.py`); **N** = `set_tuning_file path=`
(automatic, TDN on). SDN with TDN off (printed by `tdn_strip.py`, the same in `normal`, `hdr`, `night`): `deviation_no_tdn` 3.2, `strength_no_tdn` 0.75 (with TDN: `deviation` 1.6, `strength` 0.5); the copy is 134,482 B, the source 134,888 B, md5 `f53de0fe87cd8a44a8f8e203ddb6839d` before and after.

Design (User picks before the block; the order is drawn before this entry is committed and written here with the date,
time and method): **A** = one block of 4 units, 2 F + 2 N, in one of the 6 balanced orders FFNN, FNFN, FNNF, NFFN, NFNF,
NNFF (die 1-6); **B** (a short evening) = N F N. Never the N unit only at the end. The unscored warm-up runs on the first
unit's arm. The 27-fps unit (section 6) runs only if every F unit of the block reads Support with margin (fixed now; User
may decide otherwise before the block). The tuning is switched while not recording, after the unit's `b1-arm.sh sync`, and read back
(`ST`, `J` on the new PID, the take's `mode:` line). Per-unit statistics, fixed now: P2 queued share (back end) and P1 + P2
lost (losses). Test (A): exact one-sided permutation test F < N on each; minimum p = 1/6, so one block gives at most
"probable"; a second block on another evening (stratified, minimum p 1/36) before TDN-off becomes a default.

**Drawn: design A, 2026-11-04 01:05 CET, die rolled by User (result 4), after the copy and before any take of the block: NFFN = unit 1 N (`u1`), unit 2 F (`u2`), unit 3 F (`u3`), unit 4 N (`u4`); the warm-up runs on N.** Target 2 (`tier1-prep-2026-11-03.md` section 7) runs after the block with the tuning back on automatic (User, 2026-11-04).

Question: does removing the 16-bit TDN reference (~37.6 of ~57.6 MB per frame) keep the BE jobs under the ~23 ms point
where the next frame's swap and RawStats join them, at full preview?

Readout per take (`be_overlap.py <dir> --prefix e3`): section 1 S2 median, swap and stats medians; section 2 isolated S2
(overlap 0-0.5 ms, slack > 16 ms; read at n >= 500 only) and the > 6 ms bin with its n (reported, not a criterion: it is
selected by job length, 36.9-44.5 ms in all 8 TDN-on takes while their S2 medians span 11.1-42.9); section 4 threshold,
jobs at or past it (r = 0.998 with the queued share over 8 takes, so not an independent criterion), queued share, largest
20-s queued share, job count; section 6 CPU per frame (CameraManager, recording threads, UI); losses (`dropped_gap_estimate`
/ `enqueued`). Each take is one observation: frames are not replicates (the inspection struck a frame-level Fisher test,
`inspection-2026-11-02.md:64`).

| Readout | TDN on, g2 P1 / P2 (measured) | TDN on, 8 logged takes, 4 treatments | Model A (bound: all of S2 x 0.347) | Model B (expected: idle job 10-13 ms, only the overlap stretch scales) |
| --- | --- | --- | --- | --- |
| Lost | 2 / 108 | 0-590 | 0 | 0 |
| S2 median (ms) | 27.3 / 37.7 | 11.1-42.9 | 4-8 | 10-15 |
| S2 isolated [n] (ms) | 15.8 [1,543] / 19.8 [32] | 10.4-16.3 (n >= 500) | 4-8 | 10-13 |
| Jobs with > 6 ms swap overlap | 0.49 / 0.84 | 0.10-0.91 | < 0.02 | <= 0.05 |
| Threshold (ms) | 22.4 / 20.8 | 20.3-23.6 | 21-25 | 21-25 |
| Jobs >= threshold | 0.56 / 0.95 | 0.11-0.97 | < 0.02 | <= 0.10 |
| Queued share | 0.52 / 0.90 | 0.12-0.91 | < 0.05 | <= 0.10 |
| Largest 20-s queued share | 0.63 / 0.93 | 0.26-0.94 | < 0.1 | <= 0.2 |

Model A is only a bound: an idle job takes ~10.9 ms in SDR12 and HDR16 alike (`preregistration.md:325-326`), so it does not
scale with its input bytes when uncontended; Model B is expected.

Rule, per F unit (against the same evening's N units; without them, against g2):
- **Support**: in both takes queued share <= 0.2, jobs >= threshold <= 0.2, no 20-s bin with queued share >= 0.5, and <= 2
  lost. Reading: with TDN removed the back end stays below the threshold at full preview (measured, n = the F units); that
  this is the back end's own bytes rather than less contention for the swap, RawStats and the copy is probable (secondary,
  fixed now: section 1 swap and stats medians and section 6 CPU per frame against the N units; if they get faster too, part
  of the relief is system-wide). **Support with margin** (the gate for unit 2) = Support plus S2 median <= 15 ms in both.
- **BE relieved, losses elsewhere**: the BE criteria of Support met in both takes, > 2 lost: something other than the BE
  holds the raw buffers. Next: section 1's queue, S1, S3, S4, cycle and the trace; no unit 2.
- **Refute**: either take with queued share >= 0.5 and section 1 S2 median >= 0.85 x the same-evening N value at that
  position (without N units: 0.85 x g2's 27.3 / 37.7 = 23.2 / 32.0 ms). Reading: removing TDN does not keep the back end
  out of saturation at full preview, or TDN was not off per frame (positive check below). Next: the Tier 2 swap/RawStats
  change.
- **Partial**: no Refute, P2 queued share < 0.5 (below every TDN-on P2: 0.54-0.91) and Support missed: TDN is a lever but
  not enough (probable). Next: the Tier 2 change with TDN-off as its companion; no unit 2.
- **Inconclusive**: anything else (e.g. a clean unit with P2 queued >= 0.5): no TDN effect shown, no next step decided here.

Base rate: with TDN on, full preview and 8 buffers, P1 lost <= 2 in 5 of 6 units and P2 in 0 of 6 (47-181 lost); a clean
unit has occurred 0 times in 6 (one-sided 95 % upper bound 0.39), and once in all 9 sync units (pv0b, preview off). The
"~1 in 4" of `preregistration.md:268-269` (also used at `:289-290`) assumed the losing take was equally likely P1 or P2; it
was P2 in all 4 B1 units, so it is not a valid base rate. A clean F unit would be the first clean P2 at full preview: a
real but weak signal on its own (pv0b-P2 lost 0 at a queued share of 0.54). Saturation began within 20-40 s in 4 of 8 takes;
pv12-P1 tipped at 160-200 s: 3 minutes shows only an early onset, hence the 20-s criterion.

**Void** (the whole unit: restart, `warm.bin`, P1, P2, repeated once after the cool-down; a second void ends it as void;
void units stay in the table). Decided from the checks alone, before `be_overlap.py` runs:
- manipulation check: the `mode:` line's Core values (the first `fps=`, before "(asked: ...)") read 3840x2160 / 25 / Clear
  HDR True / 16 / none, and its `tuning_file` is the copy (F) or `''` (N); the `Using tuning file` lines from the take's own
  mode set (the two near the window's start) name the copy (F) or `.../defaults-pisp/imx585_clearHDR.json` (N), and the
  window's last one, from `take3v3.sh`'s ladder restore (SDR12), names the copy (F) or `.../defaults-pisp/imx585.json` (N)
  (measured: every evening-2 window ends with such an `imx585.json` line, e.g. `g2-P1.log:98561`); with an `ApertarCore cDNG
  preview colour:` line in the window, the take's lines name `/home/pi/.cache/apertar-prores/<profile>.json` instead, with
  `grep -c '"tdn"'` on that one file 0 (F) / 3 (N); `ST` not `error` after the switch; `grep -c '"tdn"'` on the copy 0;
- positive check, if libcamera writes it: `LIBCAMERA_RPI_PISP_CONFIG_DUMP=/run/apertar-media/be-cfg.json` in the log
  drop-in dumps the first frame's BE configuration at each configure (upstream `pisp.cpp:2782-2797@6b0b49f` per
  `research-30fps-answer.md:231-232`; unread in the qbc fork). Copy it after each unit's P2 as `be-cfg-<unit>.json`, with its mtime.
  Before reading it, check which mode it describes: written at each configure it shows the ladder restore's SDR12 mode,
  written once it shows the mode at Core's start (unread in the qbc fork); only a dump of the take's 4K 16-bit input counts.
  Pass: `bayer_enables & 0x140 == 0` for F and set for N (TDN on gives 0x47075d). No dump of the take's mode = no positive
  check: a Refute then reads "not shown". User also looks at the preview noise (the lead asks him once per arm);
- card serial or `warm.bin` check failed; NVMe > 40 C at P1's start (P2 starts hot by design: 47-55 C on evening 2);
  `throttled` not 0x0 on any take's `drive:` line; drive fill > 2 % at P1 (every reference P1 started at 1 %); a non-empty
  `ui switches:` line, a WebUI client or a build.

The back-end readouts alone are void (the unit is then read on losses against the base rate, not against the rule) if the
`.out` has no `clocks at record_start` line, `be_overlap.py` prints `seeded from uptime`, or the window's job count is not
within 1 % of 173 s x 25 - lost (all 8 TDN-on takes are).

| Unit | Arm | Take | Lost | S2 median | S2 isolated [n] | threshold; jobs >= it | queued; largest 20-s | swap / stats | CPU cam / rec / UI | Note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | | P1 (hh:mm) | | | | | | | | tuning and mode lines, serial, uptime_s, NVMe / SoC C, throttled, fill, MemFree |
| 1 | | P2 (hh:mm) | | | | | | | | |

UI CPU per frame differing by > 20 % between the arms means the preview-noise confounder is live: report it with the
reading (20 % is a judgement, not derived). **Reading against the rule:** (after the block, measured / probable).

Changes from the Tier 0 rule (`tier0-2026-11-03.md` section 5): <= 2 lost instead of 0 + 0; jobs >= threshold and the 20-s
criterion added; the > 6 ms bin no longer a criterion; Refute requires saturation and compares the S2 median with the
same-evening N units; same-evening TDN-on units added. Before any data (2026-11-03 review of the handoff): the
manipulation check reads the take's own lines and the ladder restore's line separately (as first written it voided every
N take); the 27-fps gate needs every F unit; the positive check counts only a dump of the take's mode.

### Deviations before any data, evening 3 (2026-11-04 ~01:30, decided with User; no take had run)

- **Core `9b5ea14`, not `c747f09`.** Another session rewrote `fe5d592`/`c747f09` as `1319967`/`b64e6f6` and added `9b5ea14`
  (a remote-only GPIO button; DPI-held pins greyed), committed at 01:22 after building an uncommitted tree at 01:19. The lead
  rebuilt `~/ApertarCore-build` from the clean `9b5ea14` tree (User's OK); every unit runs on that binary. Diff `31d5418..9b5ea14`:
  `WebControlPage.cpp`, `ControlsModel.hpp`, `HardwareConfigText.hpp`, the `test_input` command in `ApertarCoreApp.cpp/.hpp`;
  nothing in the capture or record path (code read). The warm-up attempt at 01:09 never recorded (a WebUI client).
- **Unsupervised run.** User is away from ~01:35. The root steps (`b1-arm.sh sync|save|restore`, removing the libcamera-log
  drop-in, `nvme smart-log`, `systemctl poweroff`) run through a root-owned byte copy of `b1-arm.sh`
  (`/usr/local/libexec/apertar-b1-arm`, md5 `4e2fecc6896609c27cb0783a89c56315` = the KB file) and `/etc/sudoers.d/apertar-b1-arm`,
  exact commands only; both are removed by User after the run (restore list). Consequences, fixed now:
  - No preview-noise look by User (the F arm's noise is not assessed tonight).
  - Every "stop and ask User" of the plan becomes: `record_stop` if recording, end the evening, the full restore read back,
    the reason written into the findings. Voids follow the rule as written (repeat once after the cool-down; a second void
    ends the unit as void).
  - The optional preview-only `dd` run (tier1-prep section 8 step 11) is skipped.
  - At the end, after the restore, the copy of `/run/apertar-media` to the Mac and the KB push: `systemctl poweroff` (User's
    request).
- **Manipulation check, the `Using tuning file` lines (01:35, after the unscored warm-up, before any scored take).** On
  `9b5ea14` the ladder restore at the end of `take3v3.sh` leaves the camera in 4K Clear HDR 16-bit (30 fps, lossless JPEG,
  ladder on), not SDR12 as on evening 2 (`31d5418` lets HDR16 run past 25), so the next take's mode set (25 fps,
  uncompressed) reloads no tuning and the window holds no `Using tuning file` line (measured: the warm-up's window has 0;
  the log's three loads are at Core's start, 01:27:26). As written the check would void every unit for lines that do not
  exist. Replaced by: the **last `Using tuning file` line before the window's start** (OFF0 for P1, OFF1 for P2) names the
  copy (F) or `.../defaults-pisp/imx585_clearHDR.json` (N), and every such line inside the window names that same file;
  the `mode:` line's `tuning_file`, `ST` not `error` and `J` on the new PID as written. The positive check is available:
  the dump is written at configure (the warm-up's, N, at Core's start: `bayer_enables` 0x47074d, `& 0x140` = 0x140 set,
  input 3840x2200 stride 7680 = the take's 16-bit 4K input); it counts if its mtime is after the unit's tuning switch (F)
  or Core's start (N) and its input is 3840 wide at stride 7680.
- Unscored warm-up (N, 01:28): 54 lost / 4,453 enqueued (reported, not scored).

### Results, TDN block (filled per unit; numbers from `be_overlap.py --prefix e3` on each unit's copy, consoles `e3-<unit>.out`)

| Unit | Arm | Take | Lost | S2 median | S2 isolated [n] | threshold; jobs >= it | queued; largest 20-s | swap / stats | CPU cam / rec / UI | Note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | N | P1 (01:42) | 58 / 4,448 | 37.0 | 18.3 [30] (n < 500, not read) | 20.6; 0.93 | 0.91; 0.93 | 9.2 / 6.7 | 18.2 / 34.4 / 4.5 | valid: mode 4K/25/HDR/16/none, `tuning_file ''`, last load before the window `defaults-pisp/imx585_clearHDR.json`, none inside; dump `bayer_enables` 0x47074d (TDN set); serial ok, uptime_s 2714, NVMe 39.85 / SoC 58.2 C, 0x0, fill 1 %, MemFree 460 MB; 4,268 jobs (4,267 expected) |
| 1 | N | P2 (01:46) | 39 / 4,468 | 36.8 | 18.0 [39] (not read) | 21.0; 0.94 | 0.92; 0.95 | 9.1 / 6.7 | 18.2 / 34.8 / 4.4 | valid; uptime_s 2942, NVMe 49.85 / SoC 55.4 C, 0x0, fill 8 %, MemFree 640 MB; 4,284 jobs (4,286) |
| 2 | F | P1 (02:02) | 1 / 4,512 | 5.9 | 5.9 [4,301] | 23.8; 0.00 | 0.00; 0.01 | 8.1 / 6.0 | 16.0 / 30.1 / 3.4 | valid: `tuning_file` the copy, `ST` ready, `J` `(custom, pisp)`, last load before the window the copy, none inside; dump written after the switch (01:50:53 > 01:50:51), `bayer_enables` 0x47060d (`& 0x140` = 0: TDN off), input 3840x2200 stride 7680; uptime_s 3919, NVMe 39.85 / SoC 57.6 C, 0x0, fill 1 %, MemFree 534 MB; 4,325 jobs (4,324) |
| 2 | F | P2 (02:06) | 0 / 4,511 | 5.9 | 5.9 [4,314] | 23.8; 0.00 | 0.00; 0.00 | 8.1 / 5.9 | 16.0 / 30.2 / 3.4 | valid; uptime_s 4146, NVMe 55.85 / SoC 54.3 C, 0x0, fill 8 %, MemFree 705 MB; 4,325 jobs (4,325) |

| 3 | F | P1 (02:22) | 1 / 4,512 | 5.9 | 5.9 [4,293] | 23.7; 0.00 | 0.00; 0.01 | 8.2 / 6.0 | 16.1 / 30.5 / 3.6 | **void (whole unit): NVMe 40.85 C at the unit start** (`nvme at unit start: 40850`; the loop's check had passed on a 39.85 reading and printed a second read; loop fixed to print and check one reading, twice). Otherwise as unit 2: copy loaded, dump TDN off (0x47060d, at Core's start 02:11:51), uptime_s 5130, SoC 57.6 C, 0x0, fill 1 %, MemFree 456 MB; 4,324 jobs (4,324) |
| 3 | F | P2 (02:26) | 0 / 4,512 | 5.9 | 5.9 [4,304] | 23.6; 0.00 | 0.00; 0.01 | 8.2 / 6.1 | 16.1 / 30.2 / 3.5 | void with the unit; uptime_s 5356, NVMe 51.85 / SoC 56.5 C, 0x0, fill 8 %; 4,325 jobs |

| 3r | F | P1 (02:43) | 2 / 4,509 | 5.9 | 5.9 [4,299] | 23.6; 0.00 | 0.00; 0.01 | 8.3 / 6.0 | 16.1 / 30.5 / 3.6 | valid (the repeat of unit 3): copy loaded before the window, none inside; dump TDN off (0x47060d, Core's start 02:31:32); NVMe 39.85 C at the unit start and 39.85 before OFF0, SoC 57.1 C, 0x0, fill 1 %, uptime_s 6381, MemFree 470 MB; 4,322 jobs (4,323) |
| 3r | F | P2 (02:47) | 0 / 4,513 | 5.9 | 5.9 [4,306] | 23.8; 0.00 | 0.00; 0.01 | 8.2 / 6.0 | 16.0 / 30.3 / 3.4 | valid; uptime_s 6608, NVMe 59.85 / SoC 56.0 C, 0x0, fill 8 %, MemFree 739 MB; 4,325 jobs (4,325) |

| 4 | N | P1 (03:03) | 115 / 4,391 | 37.5 | 17.9 [31] (not read) | 20.9; 0.94 | 0.91; 0.94 | 9.2 / 6.7 | 18.3 / 35.1 / 4.5 | valid: `tuning_file ''`, `defaults-pisp/imx585_clearHDR.json` before the window, none inside; dump TDN on (0x47074d, Core's start 02:51:29); NVMe 39.85 C at the start and before OFF0, SoC 57.1 C, 0x0, fill 1 %, uptime_s 7599, MemFree 462 MB; 4,212 jobs (4,210) |
| 4 | N | P2 (03:07) | 116 / 4,389 | 37.3 | 19.9 [27] (not read) | 20.5; 0.95 | 0.91; 0.94 | 9.2 / 6.7 | 18.3 / 35.4 / 4.5 | valid; uptime_s 7826, NVMe 57.85 / SoC 54.9 C, 0x0, fill 8 %, MemFree 1,214 MB; 4,208 jobs (4,209) |

Units 2 and 3r against the rule (measured, n = 2 F units): **Support with margin** in both takes of each (3r-P1 at the <= 2 lost limit). UI CPU per frame 3.4 against
4.4-4.5 ms in unit 1 (-24 %): the preview-noise confounder is live by the pre-registered 20 % line (reported, not decided).

**Reading against the rule (block of 4 valid units, NFFN; unit 3 void and repeated as 3r):**
- Each F unit (2, 3r): **Support with margin** in both takes (measured, n = 2): queued 0.00 (largest 20-s 0.00-0.01), jobs >=
  threshold 0.00, lost 1 + 0 and 2 + 0, S2 median 5.9 ms against 36.8-37.5 ms in the N units of the same evening.
- Permutation tests, F < N, one block (`b1_test.py --tdn`): P2 queued share T = 0.00, p = 1/6; P1 + P2 lost T = 3, p = 1/6;
  complete separation on both, the minimum one block can give: **probable** by the pre-registration. A second block on
  another evening (minimum p 1/36) before TDN-off becomes a default.
- Secondary (fixed in advance): the swap (9.1-9.2 -> 8.1-8.3 ms) and RawStats (6.7 -> 5.9-6.1 ms) also get faster with TDN
  off, CameraManager 18.2-18.3 -> 16.0-16.1 and the recording threads 34.4-35.4 -> 30.1-30.5 ms CPU per frame: part of the
  relief is system-wide (less memory traffic for everyone, probable), but the BE job itself drops from ~37 to 5.9 ms, far
  below the ~10.9 ms idle figure of evening 2: removing the TDN reference shortens the job even when uncontended (Model B
  expected 10-15 ms; measured below it).
- UI CPU per frame 3.4-3.6 against 4.4-4.5 ms (-20 to -24 %): the preview-noise confounder is live by the 20 % line; the UI
  does less work per frame with TDN off (reported; User did not look at the preview tonight).
- Gate for the 27-fps unit (every F unit Support with margin): **met**; it runs next (section 6 of tier1-prep).

### Results, the conditional 27-fps unit (tier1-prep section 6; F)

| Unit | Arm | Take | Lost | S2 median / p90 | S2 isolated [n] | threshold; jobs >= it | queued; largest 20-s | cycle | swap / stats | CPU cam / rec / UI | Note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 27 | F | P1 (03:23) | 1 / 4,874 | 7.1 / 12.2 | 6.9 [4,499] | 19.6; 0.01 | 0.02; 0.06 | 36.8 | 8.7 / 6.6 | 17.4 / 35.4 / 3.9 | valid: mode fps 27.0, the copy, dump TDN off (0x47060d, after the switch 03:12:10); NVMe 39.85 C at the start and before OFF0, SoC 56.5 C, 0x0, fill 1 %, uptime_s 8778, MemFree 443 MB; 4,670 jobs (4,670) |
| 27 | F | P2 (03:27) | 1 / 4,876 | 8.4 / 14.9 | 7.7 [3,925] | 18.6; 0.04 | 0.08; 0.13 | 36.9 | 9.1 / 6.7 | 18.2 / 46.4 / 4.2 | valid; NVMe 59.85 / SoC 55.4 C, 0x0, fill 9 %, MemFree 664 MB; 4,670 jobs (4,671) |

**Reading (section 6 rule):** both takes meet the Support criteria: 27 fps with TDN off becomes a candidate for B6-style
10-min takes (probable, n = 1). The margin is smaller than at 25 (queued 0.02-0.08 against 0.00, S2 p90 12-15 against 8 ms),
and P2 (drive hot) costs 46.4 ms of recording-thread CPU per frame against 35.4 in P1 (measured).

## Frame-rate sweep above 25 fps, 4K Clear HDR 16-bit uncompressed, evening 3 (User's request 01:40; exploratory, unscored)

Written before any take of the sweep (Tier 1's block was running; the arm rule below does not depend on its numbers beyond
the pre-registered reading). Question (User): from which frame rate above 25 does 4K Clear HDR 16-bit uncompressed lose
frames, and where do the losses come from?

- **When**: after the TDN block (and after the conditional 27-fps unit of `tier1-prep-2026-11-03.md` section 6, if it runs),
  before the tuning goes back to automatic and before target 2. If the evening has ended early on a stop condition, no sweep.
- **Arm, fixed now** (amended 01:45 before any sweep take, User: "the best configuration"): the arm that did better in the
  block on its two pre-registered per-unit statistics: F (the TDN-off copy) if its mean P1 + P2 lost and its mean P2 queued
  share are both lower than N's; N (automatic, TDN on) if both are higher or equal; if the two disagree, the arm with fewer
  mean lost. (First written: F only if both F units read Support.) Core `9b5ea14`, sync, 8 raw buffers, full preview, libcamera log as the block.
- **Steps**: one 3-min take per step, `TAKE_FPS` = 26, 27, 28, 29, 30 in that order (30 = Core's `fps_max` in 4K), each its
  own unit as in target 2: Core restarted (`apertar-b1-arm sync`) before each step, the tuning set and read back, the unit
  loop's checks (NVMe <= 40 C, serial, `warm.bin`, fill <= 2 %), the clip folder deleted after it. If the conditional 27-fps
  unit ran, its P1 is the 27 step (not repeated).
- **Stop rule**: the sweep climbs while a step loses <= 2 frames; the first step with > 2 lost is the last one ("the onset"),
  or 30 if none loses. A step whose `mode:` line reads another fps than asked is void and ends the sweep (Core clamps it).
- **Why, per step (readout, labelled measured / probable)**: `be_overlap.py` section 1 cycle (must be ~1000/fps ms) and S2
  median; section 4 threshold (frame period - dequeue to start), jobs >= it, queued share, largest 20-s share; section 6 CPU
  per frame; from the console and the 1 Hz log: `dropped_queue_full`, `peak_queue`, NVMe write latency and MB/s, CSI-2 OVLF.
  Reading, fixed now: losses with queued >= 0.5 and `dropped_queue_full` = 0 = the ISP back end (the block's mechanism);
  `dropped_queue_full` > 0 or a full write queue = the drive or the write path (4K 16-bit at 30 fps is ~0.5 GB/s, near the
  ~550 MB/s derived for the drive); CSI-2 OVLF > 0 in the losing seconds = the receiver; none of these = unexplained, said so.
  The trace (`apertar-b1-arm save` after the last step) shows whether the raw buffers ran out (`owned_by_drv = 0`).
- n = 1 per step: the onset is a first estimate, not a bound (two clean 3-min takes bound the loss rate only at < 0.077 %).

### Results, the sweep (arm F: mean lost 1.5 against 164 for N, mean P2 queued 0.00 against 0.915)

| Step | Take | Lost | S2 median / p90 | threshold; jobs >= it | queued; largest 20-s | cycle | CPU cam / rec / UI | `dropped_queue_full`; `peak_queue` | Note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 26 | s26-P1 (03:44) | 0 / 4,693 | 6.4 / 10.6 | 21.4; 0.00 | 0.01; 0.03 | 38.1 | 17.0 / 33.5 / 3.7 | 0; 2/12 | valid: mode fps 26.0, the copy, dump TDN off; NVMe 39.85 C, 0x0, fill 1 %, MemFree 701 MB; 4,498 jobs (4,498) |
| 27 | u27-P1 (03:23) | 1 / 4,874 | 7.1 / 12.2 | 19.6; 0.01 | 0.02; 0.06 | 36.8 | 17.4 / 35.4 / 3.9 | 0; 2/12 | the 27-fps unit's P1 (not repeated) |
