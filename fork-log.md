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
| `4ab1057` | Binning per sensor mode and for the current mode (crop width / output width; inferred from the active area when the driver gives no window); `list_sensor_modes`, `get_state` `sensor_binning*`; branch `cinemate-port` | fork-only, Mac + Pi (not on GitHub); built and running 21:39, list_sensor_modes + get_state verified |
| `80ddac1` | Frame-rate phase lock, off by default (`set_fps_phase_lock`, `fps_phase_lock_*` state), T27 reference patch; branch `cinemate-port` | fork-only, Mac + Pi (not on GitHub), built 22:04 with `8f7dc39` |
| `8f7dc39` | `CameraSession::phaseLockStatus` made public (80ddac1 did not compile); branch `cinemate-port` | fork-only, Mac + Pi (not on GitHub) |
| `3a18db0` | Phase-lock pin history 16 deep (8 requests in flight in Clear HDR since T23); branch `cinemate-port` | fork-only, Mac + Pi (not on GitHub) |
| `114bfb9` | Phase-lock history seeded with Core's own pin at arm (false `saturated` right after arming); branch `cinemate-port` | fork-only, Mac + Pi (not on GitHub) |
| `438a342` | Survive a yanked/unmounted drive: media fault latch, probe + watcher, record gate, eject intent, `media_alive` state, WebUI (T28 reference patch); branch `cinemate-port` | fork-only, Mac + Pi (not on GitHub); built 22:27 with `e8bb1b7` |
| `e8bb1b7` | MLV abandon-on-dead-medium moved to the MLV worker (438a342 had it in the DNG loop; build failed); branch `cinemate-port` | fork-only, Mac + Pi (not on GitHub) |
| `56d9137` | Pulled CFexpress card seen at once (HAT slot bit in the media probe); dead-medium stop bounded (DNG writers detached after 2 s), stage times logged; branch `cinemate-port` | fork-only, Mac + Pi (not on GitHub); built 22:43 |

## Apertar-UI · base `upstream-1.6.0` (`43888e5`)

| Commit | Change | Status |
| --- | --- | --- |
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
