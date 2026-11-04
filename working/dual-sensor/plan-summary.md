# Dual sensor: plan on one page (v2.1)

2026-11-04.
- Full design: `design-dual-sensor.md` in this folder.
- Every critic point and what became of it: `changes-from-critique.md`. Its §5 lists what the verification pass (70
  findings, each re-checked in code) changed in v2.1. Its §6 and §7 list what two re-checks of the v2.1 draft (59
  findings, then 47) changed before it was committed.
- Trees: Core `31d5418` and UI `c153c33` (both `drop-frames`), driver `cd548ef`, libcamera `6b0b49f3` (the Pi's
  `7e9fef0b` has the same helpers), Cinemate `d6cc93e`, cinepi-raw `63a08d5`. The Pi now runs Core `9b5ea14`, which adds
  WebUI, controls and `test_input` changes and nothing in capture or record; re-grep each ref on the Pi tree.
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
   - Both Cores run the same mode ladder, so on two IMX585s both pick the same mode from the same fps.
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
   - **The cost:** with the preview on Cam 1 or PiP Cam 1, every press, the camera's button included, records cam1
     only, with no WAV in v1 (Cinemate writes one per process). The HDMI status pill then reads "READY · CAM1 ONLY · NO
     AUDIO", and "REC · CAM1 ONLY · NO AUDIO" in the take. The alternative is "both always" (Q1).
   - Both cameras start on the same frame slot and stop on the same slot, under one clip number. cam1's folder is
     cam0's name plus `_cam1`, and each two-camera clip folder gets a `slots.txt` for post.
   - There is one WAV, in cam0's folder, and both clips carry the same timecode at each frame, in every format.
   - If cam1 is missing, offline, refused, lost or in standby, cam0 rolls alone and the pill says why. A press that
     asks for cam1 alone (NEXT TAKE CAM1) is refused instead of recording cam0.
   - While cam1 still writes its last take, or applies a change for more than a second, REC is refused for a moment,
     a cam0-only press too while cam1 applies a change; after 10 s of that, cam0 rolls alone. STOP never waits.
   - When the system drops a camera you asked for, the readout says so in italics, e.g. "READY · CAM0 ONLY · CAM1
     OFFLINE".
   - If the link to cam1 drops mid-take, the take goes on and STOP still stops cam1 once the link is back. A primary
     restarted during a cam1 take adopts it, so STOP ends it.
6. **Sync in software, with the phase lock you already have, on one absolute grid.** Each Core locks its frames to
   slots k·T on the kernel clock both read, so no message passes between them, and a restarted Core rejoins by itself.
   - For that, the lock's pushes change VBLANK only. An even-line quantiser smooths them, and the driver rewrites the
     shutter when VBLANK changes.
   - The same changes fix T27's lock-on flicker on one sensor, so they come first, as T57-T58.
   - Estimate: about 30-46 µs at most between the two sensors in the model, about 10 µs RMS; the Part 2 test allows
     55 µs. That is under 0.2 % of a 25 fps frame, and it does not grow with take length.
   - A Speed Ramp take is synced until its first ramp step, then flagged unsynced.
7. **Limits.**
   - Both overlays need the same link frequency: 891 MHz, written on cam1's line too. The fallback, 720 MHz on both,
     caps 4K Clear HDR 16-bit at 25 fps (and 4K SDR and 1080p at 50 fps) on both sensors, cam0 included. At those caps
     the lock can only lengthen frames, so it locks only if the sensor runs fast, and Clear HDR 30 fps is gone.
   - No Core may start or reconfigure while a camera records, because a camera-manager start disturbs the other sensor.
     The exception is a primary restarted or crashed during a cam1 take, which starts at once: with cam1's lock off
     and HBLANK ≠ 0 (24 fps, for example), one frame of that take runs short and dark, and the phase steps.
   - v1 runs both cameras in one mode. 2× 1080p and 2× 4K SDR 12-bit lossless are the targets; 2× 4K Clear HDR
     16-bit will not fit through one NVMe.
8. **API:** 23 new names and 4 files (the cam1 unit, its hardware file, its config folder, and `slots.txt`), plus one
   test-only env. There is no new key for the grid lock: with `fps_phase_lock` on, the lock uses the grid.
9. **Not chosen:**
   - one Core with two cameras;
   - Cinemate's Redis fan-out and its shared-memory compositor;
   - libcamera's `rpi.sync` (no tuning block, no multicast route without the Ethernet cable, and its corrections jump
     the line length);
   - hardware XVS wiring, kept in reserve for row-exact stereo.
10. **Size:** about 2,600 lines and about 83 hours. Everything up to T67 runs on today's rig, against a simulated cam1.

## Steps (T56-T70: playback used T46-T54, and T55 is the Clear HDR preview tutorial)

| # | Title | What you type and test | Time |
| --- | --- | --- | --- |
| T56 | Measure first | No code: the 24 fps HBLANK disturbance from a camera-manager start, dead time in Clear HDR, frame-interval jitter, a syncfs and a second writer during a take (yours, on test takes), record start and stop latency, Core memory | 3 h |
| T57 | The lock on one grid | Phase lock: grid error, quantiser, preview catch-up, `locked`; VBLANK-only pins at three sites; the KB simulator. Pi tests 1.1, 1.2, 1.5, 1.8, 1.10, each with its own drop-in that you add and remove | 7 h |
| T58 | Driver shutter fix, then the T27 retake | SHR rewrite and quieter logs on the driver's local `dual-sensor` branch; the DKMS rebuild is yours. Pi tests 1.3, 1.4, 1.6, 1.9 | 3 h |
| T59 | Camera by port | `--camera`, both pick sites, Clear HDR on the Core's own sensor, the no-sensor exit with a 20 s wait when config.txt names the sensor. The one-sensor rig behaves as before | 3 h |
| T60 | The secondary Core | role gate (photo mode kept off), allowlist, one 403 reply for every :8001 POST (proved with requests that write nothing), start wait, unit and hardware file. The install (sudo) is yours | 4 h |
| T61 | The relay | `ControlClient`, the wrapper and its lock order, command classes, the take state and the busy count, the three-step resync and the compare, the shared ladder, the `cam1` state; tested against a simulated cam1 | 13 h |
| T62 | One slot | `start_us`, `stop_us` with its stop gate, `clip_name`, `tc_offset_us`, no lock stretch once any take is decided, the first and last slot, `slots.txt`; timecode from the slot in every format; the safety-stop branch, tested in T64 | 7 h |
| T63 | Preview source | the setting, end to end | 4 h |
| T64 | Take coordination | policy, override, presets, cam1-only takes (start, 1 s wait, stop), busy sites, refusals, a stop kept while the link is down, the relink rules, a restarted primary adopting a cam1 take, the safety and failure stops, time left | 12 h |
| T65 | Second picture | UI preview client, item and renderer, tried through a socket symlink | 5 h |
| T66 | HDMI layouts | five views, the CAM1 pill, the CAM1 ONLY readout, fallbacks | 6 h |
| T67 | WebUI | second picture, layouts, select, NEXT TAKE, REC label, badge | 5 h |
| T68 | Second IMX585 | yours, in this order: cam1's config.txt line (891 MHz written out) and the no-sensor check, `sudo poweroff` and unplug, the sensor on MIPI1, power on, check that the cam1 unit is active on i2c@70000; then enumeration 2.0, r4-M1 and r4-M2, sync tests 2.1, 2.2, 2.4 | 3 h |
| T69 | Dual takes | the load ladder r4-M5 (2× 1080p first), one-slot takes, every policy and view, REC while cam1 is busy or writing, the WebUI during a take, boot order | 4 h |
| T70 | Touch UI (optional) | builds; you have no touch screen to try it | 4 h |

Each step's last check: with no cam1 configured, a take, Clear HDR and the WebUI behave as before. T57 comes first,
because the relay's live skew (T61) and the one-slot start (T62) use its grid. T58's driver change depends on no step,
but its tests need T57's lock and trace, so it runs after T57. T59, T60 and T63 do not depend on T57-T58.

## Your calls first

- **Q25** Who types: tutorials (you type, Claude tutors), or "you do this one", as for T31-T34 and T47-T51?
- **Q24** Local, never-pushed `dual-sensor` branches on the Pi: Core cut from what it runs when T57 starts (today
  `9b5ea14`), UI from `c153c33`, driver from `cd548ef`?
- **Q12** Driver fix E (the driver rewrites the shutter, SHR, when VBLANK changes) on the driver's `dual-sensor`
  branch, with your DKMS rebuild?
- **Q1** Record policy: follow the preview (default; a Cam 1 or PiP Cam 1 preview records cam1 only on every press,
  the camera's button included, without sound), or both cameras always?
- **Q11** In a take: track the grid (default), or hold the period and accept slow drift?

Then Q20 (which connector is MIPI1 on the Waveshare board), Q5 (891 MHz on both, knowing what 720 costs), Q6 (one mode
for both in v1), Q10 (~50 µs is enough without XVS wiring), Q13-Q14 (a Speed Ramp take is unsynced from its first step;
Clear HDR 30 fps runs flagged "NOT SYNCED"), and the rest with their defaults in design §12.
