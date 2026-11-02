# Critique of `verdict-draft.md` (section 8): engineering judgement for Patrik

Adversarial pass, 2026-11-02, desk only, run on Opus. Lens: does the plan follow Patrik's rules (least intrusive
change, extend existing knobs, nothing else on the Pi during a take, Patrik runs `sudo`); are the code recommendations
(`adac040`, the dirty-limits path, UI keep/revert) consistent with the evidence and the KB conventions; are the
durations realistic at ~250 GB per 10-minute take; is anything unsafe for the drive or the camera.

Status words as in the KB: **confirmed** (read in source or record, or tested here), **probable** (inferred, reason
given), **unconfirmed** (the measurement is named). `draft:N` = line N of `inspection/verdict-draft.md`. Core lines are
`adac040` unless named; kernel lines are `rpi-6.12.y` @ `5bd564a` in `/home/user/tiramisioux/kernel-rpi`.

I read the draft in full, the five examiner reports, and `critique-statistics.md`. I do not repeat its points. Where
they bear on engineering I cite them as S-R1, S-R3 and so on: S-R1 (`min_free_kbytes` never engaged in #80), S-R3 (B1's
restart + trim before every take may null the effect), S-R14 (B4 does not fit on the drive). I agree with all three.

## 0. Verdict

**Needs revision.** The code half is mostly sound:

- `adac040` is a 10-line default flip.
- The journal-line addition, keeping `APERTAR_MEDIA_SYNC_MS` and `APERTAR_DNG_WRITEBACK`, and the UI keep/park split are right.
- The four reverts apply cleanly (I tested them).

Seven problems need fixing before Patrik runs anything:

1. **The mechanism search looks for the wrong shape.** The draft treats a lost frame as a 40 ms stall of one thread and
   builds M4-M6 to find "who stalls". The KB has already measured the mechanism behind this symptom (2026-10-26):
   - libcamera's serial per-frame cycle slows under memory contention (IPC 1.87 -> 1.30).
   - Eight buffers absorb the deficit for a few seconds; after that the CFE skips single frames at a steady rate.
   - Losing 1.4-7 % of frames at 25 fps then needs only ~0.6-3 ms of extra cycle time per frame. No 40 ms hole is
     needed.
   - The instruments for this (`hwcount.py`, `libcam_stages.py`) already exist and need no `sudo` or package. The draft
     never mentions them. (E1)
2. **Data safety.** `rm -rf /media/RAW/cDNG_*` before every take deletes every clip Core has ever written to the drive,
   Patrik's own clips included. (E2)
3. **Drive and camera safety.** B3(f) deliberately drives the NVMe into the untrimmed state that killed the controller
   on 2026-10-30, with Core's trim switched off. Its trim reasoning also misreads Core's trim triggers. (E3)
4. **What ships is not what is tested.** "Make `APERTAR_MEDIA_TUNE=1` the install default" turns on six further knobs
   (block queue, `rq_affinity`, writeback interval, APST) that no cell tests. The one sysctl the draft favours
   (`min_free_kbytes`) never engaged in #80 (S-R1). (E4)
5. **Observer effect in a memory-pressure test.**
   - The trace buffer pins 256 MiB, not 64 MiB. (E5)
   - `perf sched record` writes hundreds of MB to the root filesystem during the losing take. (E6)
6. **Rule violations.**
   - The take script embeds `sudo`. (E7)
   - "Push the parked tips first" ignores the push-only-when-asked rule, and its stated reason is wrong. (E12)
   - `git revert --no-edit` does not follow the commit convention. (E12)
7. **Commands that fail as written.**
   - `journalctl -b -1` cannot cover the 21:51-23:01 window, which spans two boots. (E8)
   - The sysctl reset writes 0 to two knobs whose kernel minimum is above 0. (E9)
   - `git worktree add ~/ApertarUI-a0` targets a path that already exists. (E10)
   - B-lossy asks for lossy DNG in Clear HDR, which Apertar does not support. (E13)

Durations: the draft's 9-10 h is about 12-14 h once cool-downs, builds, `sudo` prompts after reboots and the fixes are
counted. That is four to five evenings and about 7-8.5 TB of writes (section 5).

## 1. What holds (checked)

| Draft item | Check | Status |
| --- | --- | --- |
| `adac040` is the only behavioural change since the 11-01 binary (`64bbbaa`) | `git log 64bbbaa..adac040`: `6707b08` (web thumbnails), `d08b88f` (merge), `adac040`; 4 files, +14/-14 | confirmed |
| Journal line `dontneed= writeback= sync_ms=` after `media_fs=` (draft:362) | `CameraController.cpp:4346-4369`. The KB parser reads only the first three fields (`takes_from_journal.py:47-48`), so extra fields do not break it | confirmed |
| Leave `APERTAR_MEDIA_SYNC_MS` 1000 and `APERTAR_DNG_WRITEBACK` on (draft:363-364) | pull safety needs the per-file fsync (hardware-log 2026-10-26, C0010 vs C0011); the writeback kick is the only per-frame kick in `sync` | confirmed (code) |
| Dirty limits "the Apertar way" = `APERTAR_MEDIA_TUNE` + helper (draft:366) | `scripts/apertar-media-tune:73-100`; `ApertarCoreApp.cpp:11355-11385`; applied at every mount, including Core's first probe (`:10903`). This is the path the handoff asks for | confirmed |
| CineMate sets no `min_free_kbytes` | `storage-automount.py:319-335`; `grep -rn min_free /home/user/cinemate` returns nothing | confirmed |
| `322d329` is a no-op here | `apertar-ui c13b846:src/main.cpp:179` (`setDirectWindowRendering(true)` on the external renderer), `:438-439` (main window hidden) | confirmed |
| `c13b846` adds a hard libdrm build dependency the README does not list | `CMakeLists.txt:15, 226`; README apt block `README.md:233-241` has no `libdrm-dev` | confirmed |
| `git revert --no-edit c13b846 4724007 322d329 a51c95e` "applies cleanly" (draft:372) | tested in a scratch clone of `origin/drop-frames`: 4 commits, no conflict; the resulting tree against `41ff827` is exactly `68e1a41` + `c234d77` (8 files, +68/-5) | confirmed |
| Never write `/proc/irq/154/smp_affinity` | `cofactors.md` §3.1 chain (`rp1.c:144-157`, `pcie-brcmstb.c:664-674, 720-724`, `kernel/irq/msi.c:663-670`) | confirmed (source, as cited) |
| RAM write-buffer mode allocates no extra pool while the queue stays shallow | the pool grows only on a miss (`CameraController.cpp:4791-4816`); `ram` only lifts the cap (`:5466-5471`); the warm pool is the idle size in both modes (`:4830-4858`, `:5459-5462`) | confirmed (code) / probable (no RSS measured) |

## 2. Refuted or weak claims (most severe first)

### E1. "Who stalls, and why the UI matters, is the open mechanism"; "cannot make a 40 ms hole"; "the GPU saturates the bus is not supported" (draft:28, :38-39, :45, :49, :99-100, :107-114, M4-M6)

The draft never considers a mechanism the KB has already measured.

**What 2026-10-26 measured** (`hardware-log.md:153-202`, Clear HDR 16-bit 4K, 30 fps):

| Measurement | Preview only | Recording |
| --- | --- | --- |
| libcamera's CameraManager thread | IPC 1.87, ~25 M cycles/frame | IPC 1.30, ~36 M cycles/frame |
| instructions and L3 refills per frame | same | same |
| back-end start interval | 33.3 ms | 36.2 ms |

- The thread was 54 % busy, not saturated.
- Every gap was exactly one frame, every 5-9 frames; the first gap came only after 27-47 frames.
- Reading confirmed in that entry: memory contention slows a serial per-frame stage (swap + software stats + IPA + back
  end). The 8 CFE buffers absorb the deficit, and then the CFE skips one frame each time the pipeline falls a full
  frame behind.

**The 11-01 symptom has the same signature** (`hardware-log.md:907-920`): every gap one frame (`dt_us` ~80,000), 1.7-2.3
per second, steady from second 3-5 to the end of the take.

**The deficit needed is small.** At 25 fps the budget is 40 ms against ~36 ms of cycle while recording (the 10-26
figure at 30 fps settings). A loss fraction f needs a cycle of 40 / (1 - f) ms:

| Loss rate | Cycle needed | Extra per frame |
| --- | --- | --- |
| 1.4 % | 40.6 ms | ~0.6 ms |
| 7 % | 43.0 ms | ~3 ms |

**It fits the night's contrasts** with no stall at all:

- UI stopped: clean.
- 12.5 fps: clean (80 ms budget).
- 1080p: clean (a quarter of the swap/stats work).
- The preview-rate dose response 0 / 12 / 25 fps gave 0 / 2.9 / ~7.5 % (S-R5).
- 12 camera buffers did not help (#41, 10.6 %): more buffers only delay the first gap.
- `SCHED_FIFO` did not help (#22): priority cannot buy back memory latency.

**What the draft gets wrong as a result:**

- The draft's own test of the drain asks whether it can make a 40 ms hole (draft:28, :45). The right test is whether
  it adds a few ms to libcamera's per-frame cycle.
  - The drain still fails that test: <= 0.2 ms per frame on CPU0, against the ~0.6-3 ms needed.
  - So the conclusion survives; only the reasoning has to change.
- "~1 GB/s of a ~17 GB/s bus" (draft:99-100) dismisses the UI's memory traffic on a saturation argument.
  - 2026-10-26 measured a 45 % slowdown of the same passes from recording traffic of the same order.
  - Saturation is not needed. Latency and L3 contention (2 MB, shared) on a memory-bound pass with ~10 % margin suffice.

**What the measurement plan would see.** If this is the mechanism, M4 finds no `CameraManager` reclaim, M5 finds no
40 ms wait, and B2/M6 finds no 40 ms hole. Every branch of the B1 secondary rule then ends in "neither = B2/M3"
(draft:238), and B2's time is spent on an absent stall. M5 also reads only schedstat field 2 (wait). Field 1 (run ns
per second) is what grows if the thread's own work slows; the rule "no wait growth = asleep" (draft:121) misreads that
case.

**Status:** probable. The record shows the signature; arithmetic from the record.

**Fix (least intrusive, existing instruments):**

1. Add mechanism G to Q4: libcamera's serial cycle exceeds the frame period under memory or cache contention.
2. In every B1 take, run `python3 -I ~/apertar-kb/working/tools/hwcount.py <core pid> <CameraManager tid> 60`.
   - It counts user-space PMU events and needs no `sudo` and no package.
   - `perf_event_paranoid` 2 allows it for Core's own uid; it ran on this Pi on 10-26.
   - Prediction under G: cycles per frame and IPC worse under `writer` than under `sync` at the same instruction count.
   - Under a pure stall mechanism, IPC is equal between arms.
3. Run one unscored take per arm with `LIBCAMERA_LOG_LEVELS=...,RPI:0,RPiStream:0` and parse it with
   `working/tools/libcam_stages.py`.
   - Prediction under G: back-end start interval > 40 ms under `writer` + UI and <= 40 ms under `sync`.
   - Merge with the existing `IPARPI:ERROR` setting (`cofactors.md:116`, set outside the repo). Otherwise the later
     `Environment=` replaces it and the silenced per-frame warnings return.
4. Read schedstat field 1 as well as field 2.
5. Replace "cannot make a 40 ms hole" with "adds <= 0.2 ms per frame against a ~0.6-3 ms deficit".

### E2. "Before every take, both arms: `rm -rf /media/RAW/cDNG_*`" (draft:212; also B3 and U1 by reference)

- Core names every clip `cDNG_<date>_..._C000N` (`takes-2026-11-01.raw.txt:2, 7, 12`), so the glob matches all of
  them. Patrik's own clips are in that set (#52-#57 were "Patrik's own takes after a format", night report §3).
- The rule that Patrik decides when to format (handoff) means he owns what is on the drive.
- With the configurable clip-name template (project README, `014a2bf`/`606f137`), the glob can also miss.
- **Status:** confirmed (names and glob).
- **Fix:**
  - Ask Patrik once whether anything on `/media/RAW` must be kept.
  - Delete only the take's own folder, read from its line:
    `journalctl -u apertar-core --since "$T1" --no-pager | grep -oP 'recording clip: \K\S+' | tail -1`, then `rm -rf` that path.

### E3. B3(f): ">= 0.9 TB written since the last trim, then `rm` ... with `APERTAR_MEDIA_TRIM=0` so the pre-roll delete does not trim" (draft:272, :274, :212)

**Safety.** This is the state in which the drive hung on 2026-10-30 (`hardware-log.md:714-720`):

- "four 256 KB writes got no answer for 30 s, `nvme nvme0: Disabling device after reset failure`, exFAT set the volume
  read-only ... `state` read `dead`; a reboot brought it back".
- The overnight runs in that state lost 29-77 % with files stuck 5.5-10.2 s.
- exFAT has no journal, so a device death mid-write can leave a dirty volume. Recovery needs `fsck.exfat` and possibly
  physical access.

**Value.** Low:

- #78's tail had no queue-full signature (the draft itself, draft:82-83).
- Core now trims at mount, after any delete >= 1 GiB, and after every pre-roll, so production does not reach 0.9 TB
  untrimmed.

**Misread code.** "Core's own trim runs only on deletes it sees" (draft:212) and "Core's trim policy must also cover
`rm` deletes" (draft:272) are both wrong:

- Core's media watcher requests a trim when free space jumps >= 1 GiB between two polls while idle
  (`ApertarCoreApp.cpp:10856-10861`). The README says so: "also when the delete was made outside Core" (`README.md:305`).
- Every Core start requests a mount trim (`:10903-10904`).
- So `APERTAR_MEDIA_TRIM=0` must be in force **before** the 0.9 TB is written and before the `rm`, not only for the
  pre-roll. Otherwise the cell is void without anyone noticing.

**Status:** confirmed (source and record).

**Fix:**

- Drop (f), or run it only with Patrik's explicit OK, with nothing of value on the drive and `fsck.exfat` at hand.
- Stop at the first queue-full burst.
- Set `TRIM=0` and restart Core before the preparation.
- Verify with `journalctl -u apertar-core --since <prep start> | grep -c 'media: trim'` = 0.
- Afterwards, remove the drop-in and `fstrim`. A format is not needed, and formatting is Patrik's call.

### E4. "make `APERTAR_MEDIA_TUNE=1` the install default" and the `MINFREE` column (draft:281, :334, :366)

**The helper does far more than B3 tests.** With `APERTAR_MEDIA_TUNE=1`, `pi-nvme` also applies:

- scheduler `none`, `nr_requests` 512, `rq_affinity` 2;
- `dirty_writeback_centisecs` 150, `dirty_expire_centisecs` 3000;
- `nvme_core.default_ps_max_latency_us` 0.

(`scripts/apertar-media-tune:73-100`.) B3 sets only the dirty pair and `min_free_kbytes` by hand. `rq_affinity` 2 moves
block completion to the submitting CPUs. That interacts with CPU0, which the draft treats as an open co-factor.

**The draft presumes the favoured knob.** It writes "expect the dirty pair to be inert and `min_free_kbytes` to be the
knob" (draft:366). But #80 recorded `pgsteal_kswapd` 0 and low-watermark hits 0 (night §2), so no watermark, raised or
not, was ever reached (S-R1).

**The opt-in was deliberate.** The code comment gives two reasons (`ApertarCoreApp.cpp:11357-11359`):

- "16-bit 4K25 ran clean without it" (still true under `sync`, #74/#75).
- A pulled-card bound that the per-file fsync has since made moot (`core-code.md` §6.3).

**Status:** confirmed (helper and #80 counters) / probable (the `rq_affinity` interaction).

**Fix:**

- Install the helper and sudoers in B0, with `APERTAR_MEDIA_TUNE` unset.
- Run B3's knob cells through the helper itself, so a cell equals what would ship:
  `sudo /usr/local/libexec/apertar-media-tune apply nvme0n1 pi-nvme exfat`, plus a hand `min_free_kbytes` only in the
  cell that tests it.
- Write no `MINFREE` column until a take shows the knob engaging (`pgsteal_kswapd` > 0 with the knob at stock, and
  less with it raised).
- Keep the default opt-in until B6 passes with the exact set.

### E5. "`echo 65536 > $S/buffer_size_kb`" on every B1 take (draft:217)

- `buffer_size_kb` is per CPU (ftrace documentation; `kernel/trace` is not in the checkout).
- 4 CPUs (`bcm2712_defconfig:52`) x 64 MiB = **256 MiB** of unmovable ring-buffer pages, pinned until reset.
- That is ~6 % of RAM and ~10 % of the ~2.6 GB cache headroom, inside the memory-pressure regime under test. It makes
  B1's regime differ from 11-01 and from shooting.
- It is symmetric between arms, but it shifts the effect size the plan wants to measure.
- **Status:** probable.
- **Fix:**
  - Use 8192 KB per CPU (32 MiB total).
  - After the take, check `cat $S/per_cpu/cpu*/stats | grep overrun` = 0; enlarge only if events were lost.
  - Size from M2's `allocstall_*` once it is known.
  - Write the default back after the session (or reboot).

### E6. B2/M6: `perf sched record -a -- sleep 60` during a losing take, after `sudo apt install linux-perf` (draft:123, :196, :244-246)

**Observer effect.**

- `perf sched record -a` records every scheduler event system-wide into `perf.data` in the current directory, i.e. on
  the root filesystem. On a 4-writer, 25 fps system that is plausibly 5-10 MB/s, so 300-600 MB of dirty page cache
  (**unconfirmed**: rate not measured).
- perf also uses CPU of its own, inside the regime and on the cycle budget of E1.

**Least intrusive alternative.** The draft's own tracefs covers it with no package:

```
echo "prev_pid == $T || next_pid == $T" > $S/events/sched/sched_switch/filter
echo 'stacktrace if prev_pid == '$T' && prev_state & 3' > $S/events/sched/sched_switch/trigger
echo "pid == $T" > $S/events/sched/sched_wakeup/filter
```

This gives one thread's run/sleep timeline and the kernel stack at each sleep, at near-zero volume (**probable**:
`CONFIG_STACKTRACE` comes with tracing; M0 confirms).

**Package fit.** Whether Raspberry Pi OS's `linux-perf` matches 6.12.75+rpt-rpi-2712 is **unconfirmed** (check
`perf --version` against `uname -r` before relying on it).

**Fix:** tracefs as above. If perf is used anyway: `-o /dev/shm/perf.data -m 16M`, and say that the take is not scored.

### E7. `take3v3.sh` prints `sudo dmesg | grep -c Orphanded` and reads debugfs `csi2_errors` (draft:189-195)

- The handoff rule: "Claude edits and drives the Pi over ssh; Patrik runs everything with `sudo`." A script Claude
  launches must not call `sudo`.
- `sudo -n` also fails after each B1 reboot (night §6).
- **Status:** confirmed (rule).
- **Fix:**
  - Keep the script unprivileged: `journalctl -k -b --no-pager | grep -c Orphanded` (pi is normally in `adm`), and
    `systemctl show -p MainPID --value` for the pids.
  - Put each take's privileged steps into one reviewed root script that Patrik runs (`sudo sh /tmp/b1-arm.sh writer`):
    drop-in, restart, trim, tracefs on, `csi2_errors` read.
  - That script prints what it changed, as the rule asks ("say what changed after each step").

### E8. Record check `journalctl -u apertar-core -b -1 ... | grep -E 'media: trim|delete'` for "between 21:51 and 23:01" (draft:90, :172)

- The window spans boot 1 (to 22:26) and boot 2 (from 22:27, night §2).
- `-b -1` selects one boot, and which one depends on whether the Pi has rebooted since. Either way it misses part of
  the window.
- **Status:** confirmed (logic).
- **Fix:**
  - First run `journalctl --list-boots` (it also shows whether the journal is persistent at all).
  - Then `journalctl -u apertar-core --since "2026-11-01 21:50" --until "2026-11-01 23:13" --no-pager | grep -E 'media: trim|delete'`.

### E9. Reset `sudo sysctl ... vm.dirty_bytes=0 vm.dirty_background_bytes=0 ...` (draft:263)

- `dirty_bytes` has a minimum of `2 * PAGE_SIZE` (`mm/page-writeback.c:2295, 2330`) and `dirty_background_bytes` a
  minimum of 1 (`:2313`). Both writes return EINVAL.
- The end state is right only by side effect: the ratio handlers zero the byte values (`:516`, and `:546` when the ratio
  changes).
- The helper's own `restore` has the same quirk: it logs "cannot set" and recovers through the ratios.
- **Status:** confirmed (source).
- **Fix:**
  - `sudo sysctl vm.dirty_ratio=20 vm.dirty_background_ratio=10 vm.min_free_kbytes=16384`.
  - Then read back `cat /proc/sys/vm/{dirty_ratio,dirty_background_ratio,dirty_bytes,dirty_background_bytes,min_free_kbytes}`
    and expect `20 10 0 0 16384`.

### E10. U1: `git -C ~/ApertarUI worktree add ~/ApertarUI-a0 ea44bd7 unless B0's check shows it already is` (draft:312)

- The night report states `~/ApertarUI-a0` is already a built worktree at `1cf98ad` (night §4).
- `git worktree add` to an existing path fails.
- `1cf98ad` is in no clone (`git cat-file -t 1cf98ad` fails in `/home/user/tiramisioux/apertar-ui`), so nobody can say
  from here what it contains or whether it is what ran at A0.
- The build time of a second UI is not in U1's 40 min.
- **Status:** confirmed.
- **Fix:** B0 reads `git -C ~/ApertarUI-a0 log --oneline -5` and
  `git -C ~/ApertarUI-a0 merge-base --is-ancestor ea44bd7 HEAD && echo descends`.
  - If `1cf98ad` is `ea44bd7` plus local A0-era changes: use the existing build. It needs no build and is what ran.
  - Otherwise: `git -C ~/ApertarUI worktree add ~/ApertarUI-ea44bd7 ea44bd7` and build it in B0 (not during a take),
    budgeting 10-20 min (**unconfirmed**: a UI build has not been timed in the KB).

### E11. UI reverts: when? (draft:369-372 against B1 "UI `c13b846`", draft:207-208, and B6 "UI as shipped", draft:335)

- No step puts the four reverts and the UI rebuild into the test sequence.
- If they land after U1, B6 certifies a UI binary (`41ff827` + `68e1a41` + `c234d77`) that no earlier test ran.
- If they land before B1, B1's fixed condition "`c13b846`" is wrong.
- **Status:** confirmed (plan text).
- **Fix:** do the reverts and the rebuild in B0, so that every test from B1 on runs the UI that would ship. The reverted
  paths are off by default, so B1 is not changed by this beyond the libdrm link. Alternatively keep `c13b846` through B6
  and add one confirming 10-min take after the revert.

### E12. "Push the parked tips first ... the park is one laptop away from loss until pushed" and `git revert --no-edit` (draft:372)

**The reason is wrong.**

- `c13b846` and `4724007` are already in `origin/drop-frames`' history (`git log origin/drop-frames`). A revert keeps
  them reachable.
- The Mac branches `preview-plane` @ `c13b846` and `drop-count` @ `4724007` only name commits that are already on
  GitHub.
- Nothing is at risk, so the push can wait for Patrik's ask, as the rule says ("push only when Patrik asks").

**The convention.**

- `--no-edit` produces `Revert "..."` messages.
- The handoff requires `<area>: <imperative>` with `Why:` / `What:` / `Tested:` and the Co-Authored-By trailer.
- The fork log's revert precedents are conventional commits (`fork-log.md:77` "reverts e58ae40", `:155`).

**Status:** confirmed.

**Fix:** for each revert, `git revert --no-commit <sha>` and then
`git commit -m "ui: drop APERTAR_PREVIEW_PLANE from drop-frames (parked on preview-plane)" -m "Why: ... What: reverts c13b846 ... Tested: ..."`.
Write four fork-log rows. Push the parked branch names only when Patrik asks.

### E13. B-lossy "One 10-min Lossy 3:1 take at 4K Clear HDR 16-bit 25 fps" and its fix shape (draft:350-354)

**The combination is unsupported.** Lossy DNG has no Clear HDR in Apertar:

- `ModeLadder.hpp:227-228` ("lossy DNG does not support Clear HDR").
- `CameraController.cpp:3022` ("lossy DNG ... no Clear HDR").
- `WebControlPage.cpp:7641-7642`.
- Commit `e1c10cd` "refuse lossy in Clear HDR".

The Lossy + Log plan is an SDR question.

**The fix shape.** The draft proposes `sync_file_range(WAIT_BEFORE|WRITE|WAIT_AFTER)` + DONTNEED on the single
`LossyDngDiskWriter` thread:

- That adds a third page-drop path and makes the only lossy disk writer wait for each file's I/O.
- Routing lossy paths into the existing `noteWrittenFile` / sync thread reuses the mechanism `adac040` relies on.
- It also gives lossy the per-file pull-safety fsync it lacks today (`core-code.md` §1.5).
- That is the "extend existing" choice.

**Status:**

- Refusal: confirmed in the ladder, WebUI and comments; the direct `set_record_format` path is not traced (probable).
- Fix shape: probable.

**Fix:**

- Run B-lossy at 4K SDR 12-bit, 3:1, at 25 fps or 33 fps (target 2).
- Read `estimated_capacity_fps` first.
- If it loses frames, prefer the `noteWrittenFile` route.

### E14. B1/T1/U1 switch `[storage] buffer` to `frames` (draft:207, :289, :311)

- Patrik runs `ram` (`hardware-log.md:910`; `queue_budget=` on every 11-01 stats line).
- B1's job is to replicate 11-01, not A0.
- In code the modes are memory-equivalent while `peak_queue` stays at 2 (section 1), so the switch buys nothing.
- It adds one more difference from 11-01, and no step restores Patrik's setting.
- **Status:** confirmed (setting) / probable (equivalence).
- **Fix:** run B1 and B3 in `ram`. Use `frames` only in T1 (A0's protocol). Restore `ram` after.

### E15. Thermal control: "start only below 55 C" with 1-2 min cool-down (draft:189, :215, :225, :289)

- A0 started at 34 C and ended at 54 C over 10 minutes (`hardware-log.md:745`). A1/A2 used <= 55 C, and A2 lost 10 %.
- With a 55 C rule, a 10-min take may start at 54 C and end near 74 C. That is not unsafe (warning 82.9 C,
  `hardware-log.md:716`), but cells and arms then start up to 20 C apart.
- A 1-2 min cool-down cannot bring 54 C back to 34 C.
- **Status:** confirmed (record) / unconfirmed (cooling rate).
- **Fix:**
  - Use a fixed start band (for example <= 40 C).
  - Log the max temperature and `sudo nvme smart-log /dev/nvme0` before and after each 10-min take (thermal
    transition counts, warning-temperature time).
  - Budget 5-10 min of cool-down per 10-min take.
  - Add `vcgencmd get_throttled` per take. It was checked only once, during boot 1's drift (`README.md:204`).

### E16. "the PCIe 'msi' parent SPI of the whole RP1 could be moved" (draft:331, from `cofactors.md` §3.1)

**Probably infeasible.**

- `/proc/irq/<N>/` is created only for IRQs that exist when `init_irq_proc` runs at boot (`kernel/irq/proc.c:421-437`)
  or that are requested through `__setup_irq` (`kernel/irq/manage.c:1833`).
- A chained parent mapped at PCIe probe never calls `request_irq`. It shows in `/sys/kernel/irq/`, which is where the
  cofactors' finder loop looks, but likely has no `smp_affinity` file.

**Unsafe if it works.** It moves camera, USB, I2C and the Ethernet that carries ssh at once, with a reboot as the only
undo. That is the same class of risk the draft forbids for IRQ 154.

**Status:** probable (source).

**Fix:** delete it from the plan.

### E17. M1 decision band: "~1,500 per 60 s = the claim; ~0 ... = refuted" (draft:122, :238-240)

- `lru_add_drain_all` queues one `lru_add_drain_per_cpu` per CPU with pending batches (`mm/swap.c:865-874`). So the
  claim predicts up to 4 executions per drain: 1,500-6,000 per 60 s, fewer when calls coalesce (`:830-840`).
- Compaction also drains (`mm/compaction.c:2931, 2999`), and compaction activity can differ by arm.
- An outcome such as writer 400 / sync 50 therefore has no reading.
- **Status:** confirmed (source).
- **Fix:** trace `workqueue:workqueue_queue_work` instead of only `_execute_start`. The line's task field names who
  queued the drain: Core's writer threads (the claim) or `kcompactd0` (not the claim). Read it as
  `grep lru_add_drain_per_cpu $S/trace | awk '{print $1}' | sort | uniq -c`.

### E18. "the kernel offers four candidates" / mechanism list and labels (draft:44, :107-114, :361)

- "Refuted (source)" for the drain needs exFAT's `writepages` to have put every dirty folio under writeback before the
  walk.
  - `fs/exfat` is not in the checkout. The kernel examiner labels that step probable (`kernel.md` §1.1).
  - Under the KB conventions the row reads: refuted (mm source) / probable overall.
- The draft changes `README.md:324`, the comment at `CameraController.cpp:4707-4708` and upstream issue #44 before M1,
  which costs one 60 s window inside B1.
- **Fix:** keep the text changes until M1 has run. Put them in the same commit as the journal line only if M1 is done
  by then.

### E19. "append `psi=1 rp1_cfe.track_csi2_errors=1` to `/boot/firmware/cmdline.txt`. Both are harmless" (draft:197-198)

- `cmdline.txt` must stay a single line. A broken line leaves a headless camera unbootable.
- No backup and no removal step at the end of the campaign.
- Both flags change every later take against 11-01:
  - PSI accounting runs in the scheduler hot path.
  - The CSI-2 error IRQs land on CPU0 if errors occur.
- **Status:** probable (overhead small, not measured).
- **Fix:**
  - `sudo cp /boot/firmware/cmdline.txt /boot/firmware/cmdline.txt.bak-20261102`
  - `sudo sed -i '1 s/$/ psi=1 rp1_cfe.track_csi2_errors=1/' /boot/firmware/cmdline.txt`
  - `wc -l` must be 1, then reboot.
  - Restore from the backup at the end of the campaign.
  - Name both flags as a fixed difference from 11-01.

### E20. Smaller items

| Draft | Problem | Fix | Status |
| --- | --- | --- | --- |
| "Install the helper ..., sudoers to `/etc/sudoers.d/`" (draft:366) | no owner/mode and no `visudo` check. A NOPASSWD rule on a file pi can write is a root escalation; a broken sudoers.d file breaks every `sudo` | copy the trim pattern of `README.md:307-313`: `install -m 0755 -o root -g root`, `install -m 0440`, `visudo -cf`, `sudo -n` proof | confirmed |
| "adac040 not before B1 confirms the mode is the lever" (draft:374) against "No separation: keep `sync` for the lower reclaim alone" (draft:232-233) | B1 cannot gate a default that is kept whatever B1 shows | gate `main` on B6 only | confirmed (text) |
| `take3v2.sh` `pgrep -f apertar-core \| head -1`; UI `pgrep -f "^/home/pi/ApertarUI/build/Apertar-UI"` | after B1's per-take restarts, any long-running `journalctl -fu apertar-core` has a lower pid, so the wrong `environ`/RSS is read. In U1 the old UI runs from another path and is missed | `systemctl show -p MainPID --value apertar-core` / `apertar-ui-direct` | confirmed (script) |
| "unplug the board" (NeoRotary, draft:332) | hot-unplugging a device on a live I2C bus can hold SDA low and hang bus 1 | `poll_ms=1000` in `apertar-hardware.conf` plus a service restart, or unplug powered off | probable |
| T2(c) "driver `24172e6` via `setup.sh` and a reboot" (draft:300) | DKMS rebuild + reboot down and back up (~2 x 10 min) not budgeted. Today's Core probed modes on `cd548ef` (`hardware-log.md:899-906`); check `get_state` ready and the mode list on the old driver | budget it; restore `cd548ef` the same evening | probable |
| 8.4 written as decisions ("build it", "revert") | the handoff says "Patrik decides" | phrase 8.4 as recommendations with the decision left to Patrik | confirmed (text) |

## 3. What the plan does not consider

1. **Mechanism G and the existing instruments** (E1): `hwcount.py` and `libcam_stages.py`, `hardware-log.md:153-202`.
2. **A restore list per evening.** Nothing in the plan puts back:
   - `[storage] buffer=ram`;
   - the sysctls (with E9's command);
   - `fill.bin` (650 GiB, about 70 % of Patrik's drive, if left);
   - `APERTAR_MEDIA_TRIM=0`;
   - the `cmdline.txt` flags at the end;
   - `link-frequency` back to 891 MHz after B5;
   - the tracefs buffer size;
   - the `LIBCAMERA_LOG_LEVELS` merge;
   - the old-UI worktree (when done);
   - and, after B3(f), an `fstrim` before Patrik's next shoot.

   Patrik's next shoot must not inherit any of them.
3. **Drive-endurance and thermal bookkeeping.**
   - `sudo nvme smart-log /dev/nvme0` before the campaign and after each evening: `data_units_written`,
     `percentage_used`, thermal counters.
   - The campaign writes ~7-8.5 TB (section 5). On a consumer 1 TB drive that is probably a few percent of rated life
     at most (**unconfirmed**: the rating is not in the KB).
4. **Pre-registration as an engineering step.** Write B1's rule and the restore list into the KB before the first take
   (S's "Missing" section makes the statistical case).
5. **Journal persistence.** `journalctl --list-boots` before any `-b -1` record check (E8). If the journal is volatile,
   the 11-01 checks are gone and must be redone as takes.
6. **One root script per arm** reviewed by Patrik (E7). It turns ~4 `sudo` blocks per take x 8-12 takes into one
   command per take. It is also the only way the per-take timing in draft:225 is realistic after a reboot, when `sudo`
   asks for the password.

## 4. Safety summary (drive and camera)

| Step | Risk | Severity | Change |
| --- | --- | --- | --- |
| `rm -rf /media/RAW/cDNG_*` (B1, B3, U1) | deletes Patrik's footage | high | delete the take's own folder; ask once (E2) |
| B3(f) untrimmed 0.9 TB with `TRIM=0` | NVMe controller reset failure, exFAT read-only, possible dirty volume (10-30 record) | high | drop, or explicit OK + nothing to lose + stop at first queue-full (E3) |
| RP1 MSI parent affinity (B5) | moves ssh/USB/I2C/camera IRQs at once; reboot is the only undo | medium (probably infeasible) | remove (E16) |
| `cmdline.txt` edit (B0.7) | unbootable headless camera on a typo | medium | backup, single-line sed, `wc -l` (E19) |
| sudoers install without `visudo` (8.4) | broken `sudo` | low-medium | README trim pattern (E20) |
| `fill.bin` / `TRIM=0` left behind | Patrik shoots with 30 % of the drive, or on a drive Core no longer trims | medium | restore list (section 3) |
| 54 C start, 10-min takes | ~74 C end; not unsafe (warning 82.9 C), but confounds cells | low | start band (E15) |
| hot-unplug NeoRotary | I2C bus 1 hang | low | `poll_ms` (E20) |

## 5. Durations and drive budget

Per-take figures use the draft's own step times plus the fixes above. A 10-min take writes 15,000 x 16.6 MB = 249 GB
(232 GiB). A 3-min take writes 75 GB. The volume is ~917-931 GiB (`hardware-log.md:710, 725`).

| Block | Draft | Realistic | Why | Writes |
| --- | --- | --- | --- | --- |
| B0 | ~1 h | 1.5-2 h | + baseline UI decision/build (E10), + reverts and UI rebuild (E11), helper install with `visudo`, `cmdline` backup + reboot (password) | - |
| B1 | ~75 min (+40) | 90-110 min (+45); ~2 h 15 min with S-R3's warm-up takes | cool-down band, one root script per take, `hwcount` per take; the 75 min assumes `sudo -n` works after reboots, which it does not (night §6) | 0.6 TB (+0.3; +0.6 with warm-ups) |
| B2 | ~25 min | 25 min | conditional | 0.15 TB |
| B3 | ~3 h | 3.5-4.5 h | 6 x (10 rec + 5 set-up/stats + 5-10 cool-down) = 2-2.5 h; one `dd` fill ~20 min if `fallocate` fails (reuse it for (d) and (e)); (f)'s prep in the stall zone 45-60 min (10-30 runs slowed to 5-10 s per file there), or 0 if dropped; repeats of (c)/(d) 30-45 min | 1.5 TB takes + 0.67 TB fill + 0.9 TB (f) |
| B4 + T1 | ~55 min | infeasible as written (4 x 232 GiB > volume, S-R14); 60-70 min with 3-min followers or deletes | | 0.5-1 TB |
| U1 | ~40 min | 55-70 min | + baseline UI build unless `1cf98ad` is usable | 0.45 TB |
| B5 | 1-1.5 h | 1.5-2 h if the 1440 pair runs | two reboots, `config.txt` change and restore | 0.25-1 TB |
| B6 | ~30 min | ~40 min | two boots | 0.5 TB |
| B7 | ~30 min | 30-40 min | | 0.4-0.5 TB |
| B8 | 25-50 min | same | conditional | 0.2-0.4 TB |
| B-lossy | ~15 min | ~15 min at SDR (E13) | | 0.08 TB |
| **Total** | **9-10 h, 3-4 evenings** | **~12-14 h, 4-5 evenings** | | **~7-8.5 TB** |

(**probable**: per-step times from the draft and the record, cool-down rates unmeasured.)

## 6. Commands that settle the engineering questions (Patrik runs `sudo`; nothing run from here)

| Question | Command | Reading |
| --- | --- | --- |
| Is mechanism G present? | during a `writer` and a `sync` take: `T=$(ps -L -o tid,comm -p $(systemctl show -p MainPID --value apertar-core) \| awk '$2=="CameraManager"{print $1}'); python3 -I ~/apertar-kb/working/tools/hwcount.py $(systemctl show -p MainPID --value apertar-core) $T 60` | `writer` IPC lower and cycles/frame higher at equal instructions/frame = the per-frame cycle slows (G). Equal = a stall mechanism (A/B/C/E) |
| Does libcamera's cycle exceed 40 ms? | one unscored take per arm with a `/run` drop-in `Environment=LIBCAMERA_LOG_LEVELS=IPARPI:ERROR,RPI:0,RPiStream:0`, restart, 30 s window, `journalctl -u apertar-core --since -40s -o cat > /tmp/s.log; python3 -I ~/apertar-kb/working/tools/libcam_stages.py /tmp/s.log` | back-end start interval median > 40 ms under `writer` + UI and <= 40 ms under `sync` = G |
| Who calls the LRU drain? | `echo 1 > $S/events/workqueue/workqueue_queue_work/enable`; 60 s; `grep lru_add_drain_per_cpu $S/trace \| awk '{print $1}' \| sort \| uniq -c` | writer-thread comms = the claim's drain exists; only `kcompactd0`/kworkers = not Core's |
| Did the trace buffer lose events at 8 MiB per CPU? | `grep overrun $S/per_cpu/cpu*/stats` | 0 everywhere = big enough |
| Was #78's drive trimmed? | `journalctl --list-boots`; `journalctl -u apertar-core --since "2026-11-01 21:50" --until "2026-11-01 23:13" --no-pager \| grep -E 'media: trim\|delete'` | a `result=trimmed` line after 22:47 and before 23:02 = clean NAND for #78 |
| What is in `~/ApertarUI-a0`? | `git -C ~/ApertarUI-a0 log --oneline -5; git -C ~/ApertarUI-a0 merge-base --is-ancestor ea44bd7 HEAD && echo descends` | descends + A0-era date = use it as U1's/T2(a)'s baseline without a build |
| Drive health and heat | `sudo nvme smart-log /dev/nvme0` before and after each evening | `percentage_used`, `data_units_written`, thermal transition counts; any `critical_warning` != 0 = stop |
| SoC throttling | `vcgencmd get_throttled` before and after each take | 0x0 = no throttle; bit 1 or 2 set = heat or voltage confound |
