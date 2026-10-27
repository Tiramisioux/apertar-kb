# Handoff: continue the Cinemate-port tutorials T26-T30 (from the Mac)

For: the next `apertar-dev` session on the Mac. Written 2026-10-26 at the end of the T22-T25 session. Read this, then the pages it
points to, before touching anything.

## 1. Where things stand

| Item | State |
| --- | --- |
| T22 measure drops | finished, hardware-log entries 2026-10-26 (corrected: its takes were lossless JPEG, encoder-bound) |
| T23 requests follow buffers | done, Core `db17860` |
| T24 direct I/O | **skipped**: uncompressed 25 fps is clean, the write queue never builds |
| T25 copy off the completion thread | done, Core `43a54f3`, `fc7eb16`, `351a3ee`; follow-up `d9f00d4` (audio end follows queued frames) |
| 30 fps 16-bit Clear HDR | **parked**: ~28 fps ceiling inside libcamera / the PiSP back end. Separate research handoff for Fable: `working/handoff-30fps-clearhdr16.md`. Not part of this handoff |
| T26-T30 | written (cloud session), not started. Notes in `tutorials/inbox/`, reference patches in `working/patches/` |

Branches (all on GitHub, pushed only from the Mac and only when Patrik asks):

- Core `Tiramisioux/Apertar-Core` **`cinemate-port`** @ `d9f00d4` (Mac, Pi and GitHub identical). `main` @ `f60e301` untouched.
- libcamera `Tiramisioux/libcamera` **`apertar`** @ `6b0b49f` (L1 row-step stats, L2 worker thread). **Not in use**: the Pi runs the
  system libcamera again (`/usr/local`, `7e9fef0`); the private build stays in `~/opt/libcamera-apertar`, inert without a drop-in.
- Driver `Tiramisioux/imx585-v4l2-driver` **`apertar`** @ `e5b74d3`.

Pi state: Core `d9f00d4` running, 25 fps, uncompressed, Clear HDR 16-bit, system libcamera. Test clips C0001-C0100 on
`/media/RAW`, none deleted.

## 2. How this session worked (Patrik's rules, keep them)

- **Claude runs on the Mac; the Pi is the test machine** over `ssh apertar`. No VS Code Remote, language server or Claude on the Pi
  (Claude was removed from the Pi on 2026-10-26; transcripts were backed up first).
- **Tutor mode, Patrik decides when Claude edits.** When he asks for a change: make it, say what changed, verify with a read-only
  check. **No prediction questions unless he asks for them.**
- The loop is `working/mac-driven-loop.md`: edit and commit on the Mac (`cinemate-port`), push to the Pi's staging branch
  (`git push ssh://apertar/home/pi/ApertarCore cinemate-port:cinemate-port-mac`), on the Pi `git merge --ff-only
  cinemate-port-mac`, build on the Pi (`cmake --build ~/ApertarCore-build -j2`, never while a take runs).
- **Patrik runs** `sudo`, service restarts, reboots, `/boot/firmware` edits, systemd drop-ins, DKMS. Give him exact commands.
- Commits Claude writes: `<area>: <imperative>`, Why/What, `Tested:` line, Co-Authored-By trailer. Add a fork-log row for every
  Core/driver/libcamera commit; log tutorial progress with `tutorial.py log` and commit it.
- Test with `working/tools/takes.sh N secs` (prints missing frames, queue, delivery). WAV vs picture: `/tmp/wavcheck.py` was ad hoc;
  copy it into `working/tools/` if you need it again.

## 3. T26-T30 in order, and what to expect

| ID | What | Repo | Depends on | Patch state on today's base | Risk |
| --- | --- | --- | --- | --- | --- |
| T26 | Driver reports each mode's real sensor window as its crop | driver `apertar` | nothing | **applies** on `e5b74d3` | DKMS rebuild + **reboot** (Patrik); wrong table = no camera until revert |
| T27 | Frame-rate phase lock (off by default, `set_fps_phase_lock`) | Core | nothing | **applies** on `d9f00d4` | Core rebuild; only the servo header was compiled before (host sim) |
| T28 | Survive a yanked / unmounted recording drive | Core | T27 in the patch stack | **small conflict**: one context line in `AudioRecordingSession.cpp` (`observeVideoFrame`, changed by `d9f00d4`); the hunk itself (`stop(bool finalize)`) is unaffected | the take involves pulling the drive: predictions written first |
| T29 | Media profile (tune the writer per medium/filesystem) | Core | T28 | fails only because T28 is missing | root helper for kernel knobs (Patrik) |
| T30 | Audio writer thread + 1 s capture ring | Core | T29 | applies on `d9f00d4`, but re-check after T29 | touches the same file as `d9f00d4`: re-read `observeVideoFrame` |

**Added to the port (Patrik, 2026-10-27):** two WebUI tutorials from the 2026-10-25 import, notes in the Obsidian APERTAR folder
(`20261025215321 … webui-false-recording-tutorial`, `20261025215322 … webui-time-left-investigation`):

| ID | What | Repo | State on `cinemate-port` | Left to do |
| --- | --- | --- | --- | --- |
| T20 | WebUI "records" with no drive (WebUI half of T18) | Core (WebUI) | Steps 2, 3, 5 **done** by T28 + follow-ups; **Step 4 done** in `6ae70b5` (Core's `capture.storage` = "Media Removed"/"Media Error"): Core gate, HAT slot bit + pulled latch, `!hasMedia` in the record button's disabled rule, `hasMedia` from `media_alive`, MEDIA REMOVED pill | Step 4: capture strip / Settings media card say "Media removed" from `media_state` (the strip still prints `capture.storage`); Step 6 checklist incl. hardware button and `--simulate`. The note's `media_state` values (`ok/dead/none`) differ from T28's (`mounted/removed/error/none`): use T28's |
| T21 | WebUI "Time left" vs HDMI | Core (+ UI later) | **done in `6ae70b5`** (estimate = touch UI model incl. 16-bit; label names format + "bar: 2 h"); test pending | Port the touch UI's per-frame model into `estimatedRawBytesPerSecond` (bits from `rawBitDepth`, **16 included**: Clear HDR 16-bit over-reports by about a third today), lossless/lossy/MLV/H.264 rules; truthful `time_left_label`; decide the 120-minute bar. T29's media profile does not touch it |

Before each tutorial: `python3 tutorials/tutorial.py refs TNN`. T27-T30 report many MOVED/MISSING refs because their line numbers
are at the cloud session's patch commits (`9e6df59`, `f2fa35b`, `75e9f57`, `25397cd`), not at `d9f00d4`. Fix the refs in the note
against the real tree as each step lands; use the search strings, not line numbers. T26's 6 refs are OK.

Things the T22-T25 work changes for these notes:

- T25 moved the raw copy into `DngRecordingQueue` (copy worker, `enqueueCopy`, release callback). Any T28/T29 step that touches
  `recordRawFrame`, the queue's start/stop or "frames discarded after the latch" must account for frames held by the copy worker
  (`stopCopyWorkers` releases them).
- T29's raw buffer count per filesystem must agree with T23's `rawCameraBufferCount` (8 in Clear HDR) and T25's buffers-2 hold limit.
- T24 is skipped: any note step that uses `alignedRawData` or direct I/O does not apply (T25's note was already adjusted).
- The audio recorder now keeps earliest/latest frame times (`d9f00d4`); T30's writer thread must keep that.

## 4. Open items outside the tutorials (ask Patrik which first)

- `fsck.exfat -n /dev/nvme0n1p2` (Patrik): exFAT was left marked dirty after the NVMe drop.
- NVMe drop at 19:35:32 (`CSTS=0xffffffff`): boot args `nvme_core.default_ps_max_latency_us=0 pcie_aspm=off` added; needs a long
  idle watch before calling it fixed.
- Tutorial notes T22-T30 live in `tutorials/inbox/`; copying them into the Obsidian APERTAR notes folder is still to do (the vault
  path in `tutorials/README.md` was not found from this session).
- `deploy_to_pi.sh` has not been run since the KB moved on; the Pi's `~/apertar-kb` is behind (tools there are used by `takes.sh`).

- ~~**Journal unusable**~~ **fixed 2026-10-26 21:44** (Patrik: `systemd-machine-id-setup`, drop-in `apertar-core.service.d/libcamera-log.conf` with `LIBCAMERA_LOG_LEVELS=IPARPI:ERROR`, reboot; `journalctl -u apertar-core -b` works as `pi`, 0 IPA warnings). Was (found during T27 3.1): `/etc/machine-id` is missing (not empty), so journald writes
  flat files in `/run/log/journal/` that `journalctl` does not open ("No journal files were opened"); `/var/log/journal` unused,
  nothing survives a reboot. And the system libcamera's IPA logs `WARN IPARPI ipa_base.cpp:1450 No HDR algorithm available` on
  every frame in Clear HDR 16-bit (~25/s), so the 8 MB runtime journal rotates into a root-only archive within minutes and
  Core's own lines are gone from the readable file. Blocks T27 3.2 / 5.x (journal greps). **Probable** fixes (Patrik):
  `sudo systemd-machine-id-setup` + reboot; quieter IPA via `LIBCAMERA_LOG_LEVELS=IPARPI:ERROR` for apertar-core.

- **NVMe drops (2026-10-26 19:35, 22:29):** PCIe was Gen 3 (`config.txt:36`); now **Gen 2** on test (22:33, backup
  `config.txt.bak-gen3`). 437 MB/s, 30 s 16-bit take clean. Watch for `CSTS=0xffffffff`; if none for days, keep Gen 2 (or go
  back to Gen 3 after reseating the HAT). `/cDNG_26-10-26_C0030` has bad directory entries: delete, then `fsck.exfat` with repair.

- **Session 2026-10-26 evening, summary:** T26 confirmed (driver crops, `cinemate-port` `24172e6`); Core binning `4ab1057`;
  T27 built and **left off** (sensor ~1.5 ppm vs the Pi crystal, lock flickers and drops frames on the lattice libcamera);
  T28 applied (`438a342`, fix `e8bb1b7`) plus CFE follow-ups `56d9137`, `da48974`, `227ea7b` and UI `cinemate-port`
  (`160898c`, `dc471c1`): CFE pull/re-insert works without reboot. Journal persistent (`50-apertar-persistent.conf`),
  `IPARPI:ERROR` drop-in, PCIe Gen 2 on test. Branches renamed: Core `clearhdr-fixes` and driver `apertar-tiramisioux` are now
  `cinemate-port`; UI got `cinemate-port` too.
- ~~Open: a stopped take is lost if the card is pulled within ~30 s~~ `0586273`: syncfs once a second and at stop (to be tested,
  also for throughput at Gen 2/Gen 3). T29 `ffb87db` (no direct I/O, helper not installed) and T30 `a99691e` applied, built, untested.
- **T28 not finished:** 5.1 eject gate, USB-stick pull, 5.3 eject intent; T29/T30 after it.

- **Temporary fixes to review (Patrik, 2026-10-27, all `temp:` in the subject, on GitHub `cinemate-port`):** Core `753f181` ISO
  1600 in lossless, `c5d0c37` 33 fps (superseded by `315e390`), `13a350f` 16-bit Clear HDR = 25 fps uncompressed (switches to
  12-bit SDR lossless above 25), `315e390` build fix + WebUI fps 25/33/50; UI `def5d45` ISO 1600, `f149744` FORMAT line bit
  depth + Clear HDR, `0165b70` resolution button toggles Clear HDR 16 ↔ SDR 12, `2464b60` fps 25/33/50, `f23c243` HDMI RESOLUTION caption with bit depth + Clear HDR, Core `3c2f2c5` / UI `d8098d0` 25/33/50 everywhere incl. the rotary, rotary Clear HDR toggle, auto-return to 16-bit Clear HDR at ≤25 fps, IMX585 4K SDR 60, Core `eb9cc39` Clear HDR on = uncompressed / off = lossless however switched, **lossless cap 50 (unmeasured: 33/50 fps 12-bit lossless 4K may drop frames)**. Not yet run on the
  Pi (built only): restart Core and UI to try them. 

## 5. Read first

`llm/README.md` → `llm/tutoring.md` §7 → `working/mac-driven-loop.md` → `working/cinemate-lessons.md` (§4 yank, §5 media,
§3 audio: they feed T28-T30) → `lessons/hardware-log.md` (2026-10-26 entries) → `fork-log.md` → the T26 note.
