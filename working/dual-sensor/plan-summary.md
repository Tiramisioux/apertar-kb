# Dual sensor: plan on one page (v2)

2026-11-04.
- Full design: `design-dual-sensor.md` in this folder.
- Every critic point and what became of it: `changes-from-critique.md`.
- Trees: Core `31d5418` and UI `c153c33` (both `drop-frames`, what the Pi runs), driver `cd548ef`, libcamera
  `6b0b49f3` (the Pi's `7e9fef0b` has the same helpers), Cinemate `d6cc93e`, cinepi-raw `63a08d5`.
- Nothing changed on the Pi. Its hardware was read there, read-only (`r5-pi-hardware.md`). The second sensor is not
  attached yet.

## Recommendation

1. **Two Cores, one per sensor.** The primary runs cam0 as today; a second unit runs cam1 with `--camera cam1`.
   - libcamera allows one camera manager per process, and every reconfigure restarts it. In one process a mode change
     on one camera would stop the other.
   - Cinemate made the same choice. Two Cores need about ten targeted changes; one Core with two cameras would be
     weeks of refactor.
2. **The primary stays the only door.** The UI, the WebUI and the buttons talk to the primary only.
   - A new `ControlClient` in the primary forwards the camera settings to cam1, and cam1 refuses everything else.
   - With no cam1 configured, nothing changes.
3. **Three fixes come first, because a second Core cannot run without them:**
   - pick the camera by port;
   - write Clear HDR and the HDR knobs to the Core's own sensor (today: the first imx585 found, which can be the
     other one);
   - give the secondary its own socket, web port and config, with the buttons, standby, audio, trim and pre-roll off.
4. **Display: one setting, `previewSource`** = Both (default), Cam 0, Cam 1, PiP Cam 0 or PiP Cam 1. These are
   Cinemate's five views and its PiP geometry.
   - It copies the `externalMonitorMode` setting end to end: UI.conf key, command, state field, WebUI select.
   - The HDMI window gets a second picture, the WebUI a second `<img>` from cam1's :8001.
   - A cam1 view without a frame falls back to cam0, and a CAM1 pill shows cam1's state, drops and sync.
5. **Recording follows the preview, as in Cinemate,** unless "Record both cameras" is on. The WebUI's NEXT TAKE pills
   override it for one press, and the REC label says what one press records.
   - Both cameras start on the same frame slot and stop on the same slot, under one clip number. cam1's folder is
     cam0's name plus `_cam1`.
   - There is one WAV, in cam0's folder, and both clips carry the same timecode at each frame.
   - If cam1 is not ready, cam0 rolls alone and the pill says why.
6. **Sync in software, with the phase lock you already have, on one absolute grid.** Each Core locks its frames to
   slots k·T on the kernel clock both read, so no message passes between them, and a restarted Core rejoins by itself.
   - For that, the lock's pushes change VBLANK only. An even-line quantiser smooths them, and the driver rewrites the
     shutter when VBLANK changes.
   - The same changes fix T27's lock-on flicker on one sensor, so they come first, as T57-T58.
   - Estimate: 30-55 µs at most between the two sensors, about 10 µs RMS. That is under 0.2 % of a 25 fps frame, and
     it does not grow with take length.
7. **Limits.**
   - Both overlays need the same link frequency: 891 MHz, written on cam1's line too.
   - No Core may start or reconfigure while a camera records, because a camera-manager start disturbs the other sensor.
   - v1 runs both cameras in one mode. 2× 1080p and 2× 4K SDR 12-bit lossless are the targets; 2× 4K Clear HDR
     16-bit will not fit through one NVMe.
8. **API:** 14 new names, each copying an existing pattern. There is no new key for the grid lock: with
   `fps_phase_lock` on, the lock uses the grid.
9. **Not chosen:**
   - one Core with two cameras;
   - Cinemate's Redis fan-out and its shared-memory compositor;
   - libcamera's `rpi.sync` (no tuning block, no multicast route without the Ethernet cable, and its corrections jump
     the line length);
   - hardware XVS wiring, kept in reserve for row-exact stereo.
10. **Size:** about 2,200 lines and about 70 hours. Everything up to T67 runs on today's rig, against a simulated cam1.

## Steps (T56-T70: playback used T46-T54, and T55 is the Clear HDR preview tutorial)

| # | Title | What you type and test | Time |
| --- | --- | --- | --- |
| T56 | Measure first | No code: the 24 fps HBLANK disturbance from a camera-manager start, dead time in Clear HDR, frame-interval jitter, a syncfs and a second writer during a take, record-start latency, Core memory | 3 h |
| T57 | The lock on one grid | Phase lock: grid error, quantiser, preview catch-up, `locked`; VBLANK-only pins at three sites; the KB simulator. Pi tests 1.1, 1.2, 1.5, 1.8 | 7 h |
| T58 | Driver shutter fix, then the T27 retake | SHR rewrite and quieter logs on the driver branch; the DKMS rebuild is yours. Pi tests 1.3, 1.4, 1.6, 1.7, 1.9 | 3 h |
| T59 | Camera by port | `--camera`, both pick sites, Clear HDR on the Core's own sensor, the no-sensor exit. The one-sensor rig behaves as before | 3 h |
| T60 | The secondary Core | role gate, allowlist, :8001 POSTs refused, start wait, unit and hardware file. The install (sudo) is yours | 4 h |
| T61 | The relay | `ControlClient`, the wrapper, command classes, idle and busy, resync and compare, the `cam1` state; tested against a simulated cam1 | 10 h |
| T62 | One slot | `start_us`, `stop_us`, `clip_name`, `tc_offset_us`, `first_slot`; timecode from the slot | 4 h |
| T63 | Preview source | the setting, end to end | 4 h |
| T64 | Take coordination | policy, override, cam1-only takes, busy sites, refusals, time left | 7 h |
| T65 | Second picture | UI preview client, item and renderer, tried through a socket symlink | 5 h |
| T66 | HDMI layouts | five views, the CAM1 pill, fallbacks | 6 h |
| T67 | WebUI | second picture, layouts, select, NEXT TAKE, REC label, badge | 5 h |
| T68 | Second IMX585 | yours: the sensor, the config.txt line, a reboot, enable the unit; then enumeration and sync tests 2.0-2.4 | 3 h |
| T69 | Dual takes | the load ladder (2× 1080p first), one-slot takes, every policy and view, boot order | 4 h |
| T70 | Touch UI (optional) | builds; you have no touch screen to try it | 4 h |

Each step's last check: with no cam1 configured, a take, Clear HDR and the WebUI behave as before. T57-T58 and T59-T67
do not depend on each other.

## Your calls first

- **Q25** Who types: tutorials (you type, Claude tutors), or "you do this one", as for T31-T34 and T47-T51?
- **Q24** A local branch `dual-sensor` on the Pi, cut from what it runs when T57 starts?
- **Q12** Driver fix E on the driver branch, with your DKMS rebuild?
- **Q1** Record policy: follow the preview (default), or both cameras always?
- **Q11** In a take: track the grid (default), or hold the period and accept slow drift?

Then Q20 (which connector is MIPI1 on the Waveshare board), Q6 (one mode for both in v1), Q10 (~50 µs is enough
without XVS wiring), Q13-Q14 (speed ramps and Clear HDR 30 fps run unsynced, flagged), and the rest with their
defaults in design §12.
