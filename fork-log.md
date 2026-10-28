# Fork log: Tiramisioux forks vs Apertar-Studio

How my forks differ from Apertar-Studio, and what has gone upstream. One row per fork commit.
For talking to the maintainer: each row points at a commit on GitHub (`Tiramisioux/<repo>`).

Kept current by the `apertar-dev` skill, on the Mac and on the Pi, in the same session as the
commit, PR or upstream release. Check: `scripts/fork_log_check.sh` (skill folder).

**Status:** `fork-only` (stays in the fork) · `offer` (worth a PR or issue) · `PR <link>` ·
`upstream <version>` (landed: move the row to "Landed upstream") · `dropped`.
`#N` = row N in `lessons/upstream-issues.md`.

## Apertar-Core · base `upstream-1.6.0` (`35dbe67`)

Branch `cinemate-port` (Core and driver) was named `clearhdr-fixes` (Core) / `apertar-tiramisioux` (driver) until 2026-10-26; older KB pages use the old names.

2026-10-28: the `temp:` commits (Core `753f181`..`eb9cc39`, UI `def5d45`..`d8098d0`) moved to the local Pi branch `cinemate-port-temp`; Pi `cinemate-port` reset to Core `87011d4`, UI `2d27c46`, so T31/T32 are typed on the tree they were written for (all five reference patches apply cleanly there). GitHub `cinemate-port` and the Mac still point at the temp tips; the next publish of `cinemate-port` will need a decision (force or a new branch).

| Commit | Change | Status |
| --- | --- | --- |
| `65ccfa8` | `.gitignore` for build dirs and editor state | fork-only |
| `ed400ba` | Executable bit back on `scripts/start-apertar-core.sh` (lost in the web upload, #6) | offer |
| `631721d` | Clear HDR for the IMX585: `clear_hdr`, 16-bit (3840x2200 crop), merge knobs, `<sensor>_clearHDR.json` tuning; 12-bit experimental, needs the tuning file and a LinearizationTable | offer (after the open items) |
| `e1c10cd` | Clear HDR 12-bit mode stored as linear 16-bit (fixes the purple picture: low-12-bit wrap); lossy refused in all Clear HDR | offer (with `631721d`) |
| `57c8fb0` | Clear HDR 12-bit stored as real 12-bit codes + DNG LinearizationTable (libcamera's CcmpUnwrap curve, bit-exact); Clear HDR forces 4K; `set_clear_hdr` errors in ProRes/H.264 | offer (with `631721d`, `e1c10cd`) |
| `9fa7918` | WebUI: "4K Clear HDR" resolution and 16-bit bit depth, greyed where unavailable; Clear HDR is 12/16-bit only | offer (with the Clear HDR set) |
| `94ac68d` | Clear HDR raw streams get CPU-cached buffers (libcamera's per-frame CPU passes ran on uncached CFE buffers: ~4 fps -> 25) | offer (with the Clear HDR set) |
| `f60e301` | Startup sensor-mode probe (both WDR states, `FrameDurationLimits`), fps limits from it (Clear HDR 4K 30 at 891 MHz), `list_sensor_modes` | offer (after 30 fps recording is clean) |
| `db17860` | One libcamera request per raw buffer, 8 buffers in Clear HDR (T23); branch `cinemate-port` | on GitHub (`cinemate-port`, 2026-10-26) |
| `43a54f3` | dma-buf read sync as a free helper, no behaviour change (T25 4.1); branch `cinemate-port` | on GitHub (`cinemate-port`, 2026-10-26) |
| `fc7eb16` | Raw copy hand-off API and copy worker in the DNG queue, not wired in yet (T25 4.2-4.4); branch `cinemate-port` | on GitHub (`cinemate-port`, 2026-10-26) |
| `351a3ee` | Raw frames copied on a recorder worker, request requeued after the copy, buffers-2 held (T25 4.5-4.7); branch `cinemate-port` | on GitHub (`cinemate-port`, 2026-10-26) |
| `d9f00d4` | Audio recorder told about a raw frame only once the write queue accepted it; WAV start/end order-proof (follow-up to T25); branch `cinemate-port` | on GitHub (`cinemate-port`, 2026-10-26) |
| `4ab1057` | Binning per sensor mode and for the current mode (crop width / output width; inferred from the active area when the driver gives no window); `list_sensor_modes`, `get_state` `sensor_binning*`; branch `cinemate-port` | fork-only, on GitHub (`cinemate-port`); built and running 21:39, list_sensor_modes + get_state verified |
| `80ddac1` | Frame-rate phase lock, off by default (`set_fps_phase_lock`, `fps_phase_lock_*` state), T27 reference patch; branch `cinemate-port` | fork-only, on GitHub (`cinemate-port`), built 22:04 with `8f7dc39` |
| `8f7dc39` | `CameraSession::phaseLockStatus` made public (80ddac1 did not compile); branch `cinemate-port` | fork-only, on GitHub (`cinemate-port`) |
| `3a18db0` | Phase-lock pin history 16 deep (8 requests in flight in Clear HDR since T23); branch `cinemate-port` | fork-only, on GitHub (`cinemate-port`) |
| `114bfb9` | Phase-lock history seeded with Core's own pin at arm (false `saturated` right after arming); branch `cinemate-port` | fork-only, on GitHub (`cinemate-port`) |
| `438a342` | Survive a yanked/unmounted drive: media fault latch, probe + watcher, record gate, eject intent, `media_alive` state, WebUI (T28 reference patch); branch `cinemate-port` | fork-only, on GitHub (`cinemate-port`); built 22:27 with `e8bb1b7` |
| `e8bb1b7` | MLV abandon-on-dead-medium moved to the MLV worker (438a342 had it in the DNG loop; build failed); branch `cinemate-port` | fork-only, on GitHub (`cinemate-port`) |
| `56d9137` | Pulled CFexpress card seen at once (HAT slot bit in the media probe); dead-medium stop bounded (DNG writers detached after 2 s), stage times logged; branch `cinemate-port` | fork-only, on GitHub (`cinemate-port`); built 22:43 |
| `da48974` | Pulled card latched removed until remounted (mount id); write stall (5 s, queue full / during stop) ends the take as media removed; branch `cinemate-port` | fork-only, on GitHub (`cinemate-port`); built 22:51 |
| `227ea7b` | `media_state`/`media_alive` in the socket's `get_state` (for the touch UI); branch `cinemate-port` | fork-only, on GitHub (`cinemate-port`); built 22:54 |
| `ffb87db` | Media profile (class + filesystem → workers/queue/raw buffers), noatime; root helper added, not installed; T29 without its direct-I/O step (needs T24); branch `cinemate-port` | fork-only, on GitHub (`cinemate-port`); built 23:04, not tested |
| `a99691e` | Audio writer thread + 1 s ALSA ring, 10 ms period (T30 reference patch); branch `cinemate-port` | fork-only, on GitHub (`cinemate-port`); built 23:04, not tested |
| `0586273` | `syncfs` on the clip folder once a second during a take and at every stop, so a pulled card keeps all but the last ~1-2 s; branch `cinemate-port` | fork-only, on GitHub (`cinemate-port`); built 23:07, not tested |
| `e2f55a2` | exFAT keeps 4 writers/queue 12 (T29's 2/16/+2 lost 166 frames in 3 min, C0106); audio ring 100 ms by default (1 s made the drift figure unreliable); branch `cinemate-port` | fork-only, on GitHub (`cinemate-port`); built |
| `775083f` | Each DNG's writeback started right after it is written (`sync_file_range`, async), so the 1 s syncfs no longer bursts; branch `cinemate-port` | fork-only, on GitHub (`cinemate-port`); built; alone clean (C0004), with 1 s syncfs 782 drops (C0005) |
| `77867e6` | Once-a-second sync is an `fsync` of the clip folder, not `syncfs` (which stalled the writers); full syncfs stays at stop; branch `cinemate-port` | fork-only, on GitHub (`cinemate-port`); built 23:48; C0007 3 min clean (0 missing, peak 2/12) |
| `a070e1b` | `recording` event broadcast to every client (the touch UI heard takes started elsewhere only on its 30 s poll); branch `cinemate-port` | fork-only, on GitHub (`cinemate-port`); built 23:54; offer upstream |
| `6fee0e4` | Sync thread fsyncs each DNG finished in the last second, then the folder (folder fsync alone left 0-byte files after a pull, C0010); branch `cinemate-port` | fork-only, on GitHub (`cinemate-port`); built 23:58; pull test C0011: 258/281 frames readable |
| `7a545d9` | Audio writer fsyncs `audio_capture.raw` once a second (was 0 bytes after a pull); branch `cinemate-port` | fork-only, on GitHub (`cinemate-port`); pull test: 5.02 s raw audio kept, WAV recovered |
| `e9dd6b2` | Media tuning helper opt-in (`APERTAR_MEDIA_TUNE=1`); audio drift = least-squares slope over all blocks, not two endpoints; branch `cinemate-port` | fork-only, on GitHub (`cinemate-port`); tested: no helper call after restart; C0013 fit -15 ppm (6968 points) |
| `6ae70b5` | Storage label "Media Removed"/"Media Error" from the watcher (T20 Step 4); time-left estimate follows format and bit depth, 16 included, truthful label (T21); branch `cinemate-port` | fork-only, on GitHub (`cinemate-port`); T21 tested (agrees with HDMI up to rounding); T20 pull tested |
| `87011d4` | Time left rounds down in Core (tenths) and the WebUI, like the touch UI (HDMI 35 vs WebUI 36); branch `cinemate-port` | fork-only, on GitHub (`cinemate-port`); done (Patrik, 2026-10-27) |
| `76094a9` | Speed ramping behind `fps_speed_ramp` (`set_fps_speed_ramp enabled= [shutter=angle\|exposure]`): FPS changes in cDNG/MLV takes, count numbering, one base rate, real-time WAV, grace, `fps-ramp.txt`, restore at stop (T31 without the `ramp_fps` stepper); branch `cinemate-port` | fork-only, Pi only; built 2026-10-28, not tested |
| `753f181` | ISO 1600 allowed in lossless cDNG (cap was 800) and in the WebUI's lossless list; branch `cinemate-port-temp` (Pi, since 2026-10-28) | **temp** (to review), still on GitHub `cinemate-port` and the Mac; works on the Pi (Patrik, 2026-10-27 23:08) |
| `c5d0c37` | WebUI: 33 fps in the frame-rate list; branch `cinemate-port-temp` (Pi, since 2026-10-28) | **temp** (to review), still on GitHub `cinemate-port` and the Mac; works on the Pi (Patrik, 2026-10-27 23:08) |
| `13a350f` | 16-bit Clear HDR = 25 fps uncompressed: >25 fps switches to 12-bit SDR (lossless cDNG); entering Clear HDR sets uncompressed and ≤25 fps; branch `cinemate-port-temp` (Pi, since 2026-10-28) | **temp** (to review), still on GitHub `cinemate-port` and the Mac; works on the Pi (Patrik, 2026-10-27 23:08) |
| `315e390` | Clear HDR helpers moved above `setFps` (13a350f did not build); WebUI frame rates 25/33/50 for the IMX585 and others; branch `cinemate-port-temp` (Pi, since 2026-10-28) | **temp** (to review), still on GitHub `cinemate-port` and the Mac; works on the Pi (Patrik, 2026-10-27 23:08) |
| `3c2f2c5` | 25/33/50 fps for hardware inputs too; IMX585 4K SDR up to 60 (probe), lossless cap 50; rotary resolution press toggles 16-bit Clear HDR ↔ 12-bit SDR; back to ≤25 fps restores 16-bit Clear HDR after an automatic switch; WebUI shows 25/33/50 in Clear HDR; branch `cinemate-port-temp` (Pi, since 2026-10-28) | **temp** (to review), still on GitHub `cinemate-port` and the Mac; works on the Pi (Patrik, 2026-10-27 23:08) |
| `eb9cc39` | Clear HDR on = uncompressed cDNG, off = lossless, also by toggle (rotary, touch UI, WebUI); branch `cinemate-port-temp` (Pi, since 2026-10-28) | **temp** (to review), still on GitHub `cinemate-port` and the Mac; works on the Pi (Patrik, 2026-10-27 23:08) |

## Apertar-UI · base `upstream-1.6.0` (`43888e5`)

| Commit | Change | Status |
| --- | --- | --- |
| `d8098d0` | Touch UI: 25/33/50 in 16-bit Clear HDR, IMX585 4K SDR up to 60, lossless cap 50; branch `cinemate-port-temp` (Pi, since 2026-10-28) | **temp** (to review), still on GitHub `cinemate-port` and the Mac; works on the Pi (Patrik, 2026-10-27 23:08) |
| `f23c243` | HDMI monitor: RESOLUTION caption shows bit depth and Clear HDR for raw takes; branch `cinemate-port-temp` (Pi, since 2026-10-28) | **temp** (to review), still on GitHub `cinemate-port` and the Mac; works on the Pi (Patrik, 2026-10-27 23:08) |
| `2464b60` | Touch UI frame rates 25/33/50 (IMX585 and others); branch `cinemate-port-temp` (Pi, since 2026-10-28) | **temp** (to review), still on GitHub `cinemate-port` and the Mac; works on the Pi (Patrik, 2026-10-27 23:08) |
| `0165b70` | Touch UI: resolution button toggles 4K 16-bit Clear HDR ↔ 12-bit SDR; 33 fps in the list; branch `cinemate-port-temp` (Pi, since 2026-10-28) | **temp** (to review), still on GitHub `cinemate-port` and the Mac; works on the Pi (Patrik, 2026-10-27 23:08) |
| `f149744` | Touch UI FORMAT line: bit depth and Clear HDR for raw takes ("16-bit · Clear HDR · Uncompressed"); branch `cinemate-port-temp` (Pi, since 2026-10-28) | **temp** (to review), still on GitHub `cinemate-port` and the Mac; works on the Pi (Patrik, 2026-10-27 23:08) |
| `def5d45` | Touch UI: ISO 1600 in the lossless cDNG list; branch `cinemate-port-temp` (Pi, since 2026-10-28) | **temp** (to review), still on GitHub `cinemate-port` and the Mac; works on the Pi (Patrik, 2026-10-27 23:08) |
| `2d27c46` | Touch UI counts "16-bit" as 16 bits in the frame-size estimate (HDMI time left was a third too long: 50 vs 37 min); branch `cinemate-port` | fork-only, on GitHub (`cinemate-port`); done (Patrik, 2026-10-27) |
| `dc471c1` | CFE automounter: card pulled while mounted → lazy unmount + PCIe remove, so the next insert remounts (T18 step 5a); branch `cinemate-port` | fork-only; installed 22:59, tested on the Pi (pull + re-insert, no reboot) |
| `160898c` | Touch UI follows Core's media state (MEDIA REMOVED / ERROR) instead of only the mount table; branch `cinemate-port` (created 2026-10-26 from `main` `4415a55`, on GitHub, Mac, Pi) | fork-only, on GitHub (`cinemate-port`); built 22:55, tested |
| `66d6d19` | Stop tracking the committed `build/` tree (551 files, 18 MB, #5) | offer |
| `29ed99b` | Executable bits and `mesa-minimal` symlinks restored (#6) | offer |
| `4415a55` | Touch UI: "4K Clear HDR" resolution (quick menu + settings) and 16-bit bit depth, greyed where unavailable; bridge `clearHdr` / `applyClearHdr` | offer (needs Core `631721d`+) |

## libcamera · `Tiramisioux/libcamera` branch `apertar` · base will127534 `qbc-pisp-handler` (`7e9fef0`)

The Pi runs `v0.7.1+qbcfork.20260522-7-7e9fef0b` from `/usr/local` (confirmed 2026-10-26: version string in the installed library,
and `7e9fef0` is the head of will127534's branch). Branch `apertar` created at exactly that commit on 2026-10-26. Mac clone:
`~/Documents/Apertar/libcamera`; Pi clone `~/libcamera` (public, cloned by Patrik, push disabled) (`origin` = Tiramisioux, `qbc` = will127534, fetch only). The `cinemate*` branches are Cinemate's: never touch them from here.
Flow (Patrik, 2026-10-26): like Core. Edit and commit on the Mac on `apertar`; to the Pi with
`git push ssh://apertar/home/pi/libcamera apertar:apertar-mac`, then on the Pi `git merge --ff-only apertar-mac`; build on the Pi only.
GitHub (`origin`) only from the Mac, when Patrik says publish. `apertar_publish.sh` does not cover this repo.

| Commit | Change | Status |
| --- | --- | --- |
| `7e9fef0` | base, unchanged (will127534 `qbc-pisp-handler`) | upstream of the fork |
| `889567a` | `QBC_RAW_STATS_ROW_STEP=N`: software raw stats read every Nth Bayer row pair (default 1 = unchanged); built on the Pi into `~/opt/libcamera-apertar`; 30 fps ~26 -> ~28.5 | on GitHub (`apertar`) |
| `6b0b49f` | `QBC_RAW_CPU_WORKER=1`: endian swap, CCMP unwrap and SW raw stats on a worker thread (default off); safe on the Pi, no 30 fps gain | on GitHub (`apertar`) |

## imx585-v4l2-driver · branch `apertar` · base will127534 `qbc-pisp-handler` (`1644466`)

| Commit | Change | Status |
| --- | --- | --- |
| `e5b74d3` | 18 aspect-ratio crop modes, exactly as shipped on the 1.6.0 image, which is in no published commit (#12) | offer |
| `24172e6` | branch `cinemate-port` (on GitHub, Mac, Pi; 2026-10-26): each mode's crop = its real sensor window (T26) | fork-only; DKMS-installed 21:36, crops verified via list_sensor_modes |

Not taken: Apertar-Studio `main` is 4 commits past the base (`3680bf4`, `c0f5404`, `11178c8`,
`70bdb26`: format hardening, HMAX table, RAW10 4K, CCMP Clear HDR gate).

## Not in any commit

| What | Where | Status |
| --- | --- | --- |
| `imx585_clearHDR.json` (`imx585.json` minus the `rpi.hdr` entry): needed by `631721d`, lives outside the repo | Pi `~/Tuning-Files/defaults-pisp/`, must go into every image | fork-only (stock `rpi.hdr` pins exposure/gain in Clear HDR; worth an upstream issue) |
| `src/prores/README.md`, `src/prores/ffmpeg/` ship on the 1.6.0 image but are missing from upstream git (#7) | Pi `~/ApertarCore`, untracked | offer (issue) |

## Pull requests

None yet (checked 2026-10-25: `gh pr list --repo Apertar-Studio/<repo> --author Tiramisioux --state all`).

## Landed upstream

None yet.
