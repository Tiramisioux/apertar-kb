# Dual sensor: what the critiques changed (2026-11-04)

Two critics read the drafts against the code:
- `sync-critique.md` checked `sync-synthesis.md`. It has 14 claims (S1-S14) and 11 gaps ("Missing" 1-11).
- `critique-merged-v1.md` checked `design-merged-v1.md`. It has 25 points (P1-P25).

This page says, for each point, what `design-dual-sensor.md` does now (v2.1; rows the verification pass changed say
"v2.1", and §5 lists that pass; rows the re-check of the v2.1 draft changed name §6, which lists it; §7 lists a
final re-check):
- **taken**: the critic's fix, as written;
- **changed**: fixed, but differently;
- **not taken**: with the reason.

The claim check's corrections to the reader reports r1-r5 are in the design's §13 and in `claim-check.md`.

Step numbers in `critique-merged-v1.md` are the merged v1's. v2 renumbered them:

| v1 | T55 | T56 | T57 | T58 | T59 | T60 | T61 | T62 | T63 | T64 | T65 | T66 | T67 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| v2 | T56 | T59 | T60 | T61 | T62 | T63 | T64 | T65 | T66 | T67 | T68 | T69 | T70 |

v2's T57 (the lock on one grid) and T58 (the driver SHR fix and the T27 retake) are new.

## 1 Sync critique

### The three refutations

| # | The synthesis said | The critic found | v2 | Verdict |
| --- | --- | --- | --- | --- |
| S8 | A Core restart's HBLANK write is harmless, because the other sensor runs HBLANK 0 | Only while the other Core is grid-locked. The base pin `{d, d}` (CC:2406-2415) takes the lattice in every release window: at 24 fps, HMAX 625 with hblank 524, and a foreign write costs a 5 ms step | The base pin is `{d, d+1}` whenever the lock is on (§7.3 fix A). Test 1.10 reads HBLANK during an fps-change grace | taken |
| S9 | Never stretch in a take: the stretched frame would fail the FrameDuration test | That test guards only the first frame (CC:9068-9074). The real cost: a stretch of s moves the time index by s/T and leaves a phantom hole above T/2 | The rule stays, with the right reason (§7.4) | taken |
| S10 | Hold option at 24 fps: 355 ppm off, about 5 holes per 10 min | 178 ppm, and the frames run fast: no holes, but about 107 ms of picture gain per 10 min. The lattice's exact 625 × 4950 point is also available | The hold policy is kept in reserve with the exact point and its cost, HBLANK ≠ 0 (§7.6) | taken |

### Corrections to claims that hold

| # | Correction | v2 | Verdict |
| --- | --- | --- | --- |
| S3 | The grid is on CLOCK_MONOTONIC, SensorTimestamp's domain. Compute `start_us` and the late check there | §7.2 clock; §6.2 step 1 | taken |
| S4 | At a mode's top fps, `{d, d+1}` can collapse to min == max (ipa_base.cpp:1788-1792) | the saturation check expects it (§7.3) | taken |
| S5 | The driver uses no register hold, so VMAX and SHR are two separate writes | fix E names the hold as an option, if the datasheet confirms it (§7.3) | taken |
| S6 | Clear HDR's VMAX parity is unknown: the quantum may be 29.6 µs | §7.3 "Steps"; test 1.9 | taken |
| S11 | N = 6 is PROBABLE, and D in Clear HDR is an ESTIMATE | §7.4 dead time; test 0.4 measures it | taken |
| S12 | The accuracy budget assumes uncorrelated jitter, a constant D and no CFE bias | §7.5: the budget's title and the "Not in the budget" list; test 2.2 decides | taken |
| S13 | "FrameWallClock is per process" is a weak objection: both fits estimate the same offset | §7.2 now says why SensorTimestamp is better: it has no fit noise | taken |
| S14 | Whether the leader drives XVS is unconfirmed (the driver's comments contradict each other) | §7.6 hardware XVS; test 2.5 scopes the leader's pin first | taken |

S1, S2 and S7 hold with no correction. They are §7.1 and the HBLANK row of §2.

### What the synthesis missed

| # | Gap | v2 | Verdict |
| --- | --- | --- | --- |
| 1 | Frame-start interrupt coupling: a bias plus a bimodal skew | §7.5 "Not in the budget"; test 2.2 looks for two peaks; CPU affinity is Patrik's system setting | taken |
| 2 | The base pin stays `{d, d}` | as S8 | taken |
| 3 | Re-enumeration on reconfigure writes HBLANK on the other sensor. Two fixes: keep one CameraManager, or patch the fork's init write | v1 avoids it instead: the busy window (§4.3), the secondary's wait for idle (§3.4; v2.1: a restarted primary does not wait), and HBLANK 0 under the lock. The two fixes stay in reserve, used if r4-M2 shows a cost (§11 risk 1) | changed |
| 4 | Fix E is not atomic | as S5 | taken |
| 5 | Clear HDR VMAX parity | as S6 | taken |
| 6 | Shared bandwidth changes the drop rate, D's spread and the holes | §2 bandwidth row; T56 0.5 and 0.6; r4-M1, r4-M5; 2× 4K HDR16 is out | taken |
| 7 | D is not constant (skips, drops, BE contention) | §7.5 "Not in the budget"; the trace in T57 shows it | taken |
| 8 | Clear HDR at 30 fps locks if the sensor runs fast against the Pi | §7.5 table row; Q14 | taken |
| 9 | Two period definitions (decimal 23.976 against 24000/1001) | §7.2: one rational T for the grid, the index and the timecode | taken |
| 10 | The top-fps clamp re-enters the lattice | as S4 | taken |
| 11 | Audio on both Cores | the secondary records no audio (§3.3, §6.3); Q4 | taken |

## 2 Panel critique

| # | Sev. | Point | v2 | Verdict |
| --- | --- | --- | --- | --- |
| P1 | HIGH | Forwarded presets and the resync write UI.conf keys (standby timeout, photo mode) into cam1 | cam1 gets only the camera keys, minus the photo keys and the clip template, with `timecodeMode` sent as `cameraTimecodeMode` and its value mapped to `free_run` or `rec_run` (§4.4, v2.1, §6). On the secondary itself (§3.3): the standby timer is off; photo mode, long exposure and bracketing are forced off at start; `apply_preset` ignores its four photo keys and writes no UI.conf key (v2.1, §6). The check stays in T60, which also reads cam1's photo flags | taken |
| P2 | HIGH | "Idle" ignored the storage pre-roll and photo mode, so the resync could copy the pre-roll fps to cam1 just before a take | one idle test (§4.3) for the compare, the resync and the secondary's start wait (a restarted primary does not wait, §3.4; final/cons-7 in §7); no compare in photo mode. The check is in T61 | taken |
| P3 | MED | The 500 ms lead delayed every take, cam0-only ones too | the lead applies only when cam1 is in the take (§6.2). The check is in T62 | taken |
| P4 | MED | A quick REC while cam1 still writes: cam1 dropped silently, or it starts late | (a) REC refuses: "Wait for CAM1 to finish writing to media." (§4.6). (b) The relay reads `media_write_state` (§4.1). (d) The delete gates check cam1 too (§4.3). (c) is changed: a late Core is not refused. It starts on its next frame and records its first slot (v2.1: in get_state as `recording_first_slot` and in `slots.txt`, not in the reply), and the pill shows the offset (§6.2). A take with a known offset beats losing cam1's take for one frame | changed (c) |
| P5 | MED | REC during cam1's forwarded reconfigure | the busy window (§4.3): v2.1 counts cam1 busy while a forward is queued or in flight (§6: a count kept apart from the take state); any REC press, a cam0-only one too (§6), waits up to 1 s, then gets "CAM1 is applying a change. One moment."; after 10 s cam0 rolls alone. The check is in T69, with the real cam1 and the Mode Ladder off (v2.1, §6) | taken |
| P6 | MED | cam1's stop syncfs can stall cam0's writers | the secondary never syncfs's the volume. It fsyncs its own files, always, not only while the primary records (§3.3): one rule, the same durability for its own take. T56 test 0.5 measures the cost | changed |
| P7 | MED | A lost cam1-only take leaves the tally on and `recording` true | `cam1RecordingActive()` reads cam1's take state (§6: not the shown word, so a forward in flight never hides the take). When cam1 leaves the take, the primary publishes `active:false` and undoes the tracking; a link drop keeps the take and the tally (§4.3, §4.6; §6). The check is in T64 | taken |
| P8 | MED | No rule for a refused forwarded setter; the compare covered 8 of about 40 fields | a refusal sets `cam1.message` and schedules a resync; the compare covers every field the resync sets (§4.4) | taken |
| P9 | MED | No safe command line for hand-run test Cores | the two full lines under §9; the writes-pending check moves to T69 | taken |
| P10 | MED | Both Cores probe at the same moment at every boot | the secondary waits up to 30 s for the primary's socket, then for idle (§3.4). v2.1: the unit has no `PartOf=`, a restarted primary does not wait for cam1, and on link it adopts a running cam1 take (§4.6); §6: it holds its trim and Start pre-roll until cam1 answers. `RestartSec=5`. The install checks are in T60, the adopt check in T64, and the primary restart under the real unit in T69 (§6) | taken, changed in v2.1 |
| P11 | MED | Photo mode with a cam1 preview source frames on cam1 and shoots cam0 | cam1 sources show cam0, tagged "PHOTO · CAM0" (§5.2) | taken |
| P12 | LOW | POSTs on :8001 bypass the allowlist | every POST on :8001 is refused, with one 403 reply before any route logic (§3.3, §6). The check is in T60 | taken |
| P13 | LOW | The secondary's low-power restores wake the whole Pi | they are off on the secondary; `enter_standby` goes to cam1 on a relink during standby, and `wake` on a relink while the primary is awake (§3.3, §4.6, §6) | taken |
| P14 | LOW | `APERTAR_MEDIA_TUNE=0` was missing | it is in the unit (§3.4) | taken |
| P15 | LOW | The flat parser cannot read cam1's scalars | one scalar reader by key (§4.1) | taken |
| P16 | LOW | With cam0 dead, the primary takes cam1's sensor and the secondary loops | the critic's second fix: the secondary exits 0 on EBUSY (§3.2). The primary keeps today's fallback, so a rig with a dead cam0 still shoots on cam1 | changed (the alternative) |
| P17 | LOW | A "clean" second pane also lost the LUT, desqueeze and rotation | both panes keep the display transforms; only the aids and guides stay on the main pane (§5.2) | taken |
| P18 | LOW | cam1's preview client misses the recording fps cap | `recordingChanged` reaches it (§5.2). The check is in T65 | taken |
| P19 | LOW | Sound Recorder mode still named cameras | `record_cameras` is `none`, the label is "REC SOUND", and an explicit `cameras` is refused (§4.5, §5.3, §6.1) | taken |
| P20 | LOW | Speed ramps with two cameras were not covered | allowed in two-camera takes; v2.1: frames keep the slot index until the first ramp step, then count, and the take is flagged unsynced from that step (§6: in every take with `start_us`); refused in cam1-only takes (§6.2, §7.6, Q13) | taken |
| P21 | LOW | Four decisions had no question | Q17 (presets carry the policy), Q18 (no preview-source button in v1), Q3 (an explicit `both` with cam1 down: cam0 rolls; v2.1: an explicit `cam1` is refused), Q19 (the DNG serial is unchanged in v1) | taken |
| P22 | LOW | A reply timeout would mark cam1 offline during its own stop | offline only on EOF or a failed connect (§4.1). §6: a slow reply keeps the last state, and during a stop it reads `writing` (§4.5); `busy` now means only a forward queued or in flight | taken |
| P23 | LOW | A stale socket file made a single-camera rig "configured" | the socket must accept a connection (§4.1) | taken |
| P24 | LOW | The WebUI in Both during a take was not tested | test 2.6, in T69 (§10 Part 2) | taken |
| P25 | LOW | No install step, no boot check, and the no-sensor exit came too late | the check is in `main()` before `start()` (§3.2; v2.1: it looks again for up to 20 s when config.txt names the sensor); the install and its checks are in §3.4 and T60 (v2.1: it copies the start script and the hardware file, and creates an empty config folder (`mkdir /home/pi/.config-cam1`), first); v2.1: both Cores run without `APERTAR_RT` | taken |

## 3 Changes to the merged v1 that no critic asked for

| Change | Why |
| --- | --- |
| The sync slot's options A and B became one grid lock with origin 0 (A). `origin_ns` and `at_us` are dropped | both Cores read one clock, so a message adds nothing, and a restarted Core rejoins by itself (§7.2). Patrik asked for the phase lock (r5) |
| No new key: with `fps_phase_lock` on, the lock uses the grid | the least intrusive choice. For one camera the grid only picks the phase, and the same change fixes T27's flicker (§7.2) |
| The lock's own fixes (VBLANK-only pins, the quantiser Q, driver fix E) come first, as T57-T58 | they help the one-sensor rig now (the T27 flicker), and their Part 1 results decide the sync design before any plumbing (§9) |
| Stop on one slot (`stop_us`), not one relay latency apart | both clips hold the same slots, k0 to k1−1 (§6.2) |
| Timecode from the slot time plus the primary's `tc_offset_us` | the same timecode at each index on both clips, whatever the jitter (§6.3) |
| `cam1.locked` and `cam1.skew_us` from the frame times the relay already reads | Patrik sees "SYNC 12 µs" or "NOT SYNCED" without a scope (§7.6) |
| The preview-source setting (T63) comes before take coordination (T64) | the follow-the-preview policy reads it |
| An explicit `cameras=both` with cam1 down no longer refuses the take; v2.1 refuses an explicit `cameras=cam1` instead of recording cam0 | v1's rule conflicted with the default "cam0 rolls alone" (P21c); recording cam0 for a press that named cam1 alone would mislead (consistency#1) |

## 4 Stale KB pages the claim check found

These are not part of the plan, and they got their own KB commit. The pages describe the `upstream-1.6.0`
baseline, which was right about K1, K3, K5, K8 and X6. Those got a note on what the fork (`31d5418`, what the Pi
runs) does instead. K2 got a note that it does not apply on the rig's CM5. K4, K6 and X5 were wrong at the baseline
too and were corrected. K7 needs no change: the maps already say their line counts are upstream-1.6.0's.

| Id | Page | Was | Is |
| --- | --- | --- | --- |
| K1 | architecture/drivers.md:118 | Core has no Clear HDR support | Core writes WDR and the HDR knobs on the first imx585 subdev (CC:6875-6970) |
| K2 | architecture/drivers.md:112 | a possible regulator bug | not applicable on the CM5: both labels are one regulator |
| K3 | architecture/config.md:91 | `hdmi_external_only` defaults to false | it defaults to true (DisplayConfigBridge.cpp:294, 354-357) |
| K4 | llm/README.md trap 13, llm/ui-map.md | the UI sends set_fps and set_resolution by itself | not while a control bridge exists, which the rig always has |
| K5 | architecture/build.md:96 | the drop-in sets LimitNICE | LimitNICE=-5 and LimitRTPRIO=80 |
| K6 | llm/ui-map.md:465 | APERTAR_CONTROL_SOCKET moves the UI's socket | not for the preview client, whose path is `connectToCore`'s argument |
| K7 | llm/core-map.md, llm/ui-map.md | line counts of upstream-1.6.0 | drop-frames counts; use the grep anchors |
| K8 | architecture/drivers.md:122-124, architecture/core.md:360 | four sensor families; the pick at CC:5304 | imx283 too; the pick at CC:7262-7265 and CC:7063-7066 |
| X5 | architecture/overview.md:5 | a Pi 5 4 GB | a CM5 Lite 4 GB on a Waveshare CM5-IO-BASE-A |
| X6 | llm/README.md, architecture/config.md, architecture/core.md | the hardware file is read once at start | Core re-reads it every 2 s and restarts only the changed groups, never during its own take |

## 5 Verification pass (2026-11-04): v2 → v2.1

Six reviewers read v2 against the code at the refs, each from one angle:
- consistency between the plan's own sections (`consistency#1-15`);
- the Core refs of §3-§4 and §5-§8 (`core-refs-3-4#1-11`, `core-refs-5-8#1-9`);
- the UI, libcamera, driver and arithmetic (`ui-lib-drv-math#1-10`);
- the operator's view and the rules for working on the rig (`operator-rules#1-15`);
- a red team (`red-team#1-10`).

Every finding then went to an adversarial verifier, which re-read the evidence and tried to refute it. All 70 held
(54 confirmed, 16 partly: the problem was real, but part of its claim or fix was overstated). None was refuted. Each
was folded into v2.1 as below. "Taken" means the verifier's corrected fix as written, "changed" means fixed
differently, with the reason.

### Recording and takes

| Findings | v2.1 | Verdict |
| --- | --- | --- |
| consistency#1 | REC with cam1 not ready has one rule (§6.1 table, §4.3, §4.6, Q3, summary item 5): `not_found`, `offline`, `refused`, `lost`, `standby` drop cam1 and cam0 rolls; `writing` refuses; `busy` refuses after a 1 s wait, and after 10 s cam0 rolls; an explicit `cameras=cam1` is refused. §6: a cam0-only press waits for a busy cam1 too, and any `record_start` during a cam1-only take gets "CAM1 is recording." | taken (the 1 s wait: see consistency#8 and core-refs-3-4#3 below) |
| consistency#8 | the `idle` state word is gone; `ready` plus `record_cameras` say whether cam1 is in the next take; the pill is white or grey from `record_cameras`; "idle" is only the §4.3 test | taken (dropped rather than renamed: `record_cameras` already carries it) |
| core-refs-5-8#1, red-team#6 | the reply comes at once, as today; the actual first slot is recorded (§6: for raw from the index anchor, CC:4640-4641; ProRes at CC:10144-10145 and H.264 at CC:10181-10184, inside `recordProcessedPreviewFrame`, CC:10089) and published in get_state (`recording_first_slot`), the journal and a sidecar `slots.txt` | changed: a get_state field instead of a new event. The relay polls get_state every second anyway, and an event would add an API name |
| core-refs-5-8#2, red-team#5 | the stop gate (CC:9064-9081), `stop_us` threaded App:14387 → CC:12264/12278 → CC:7664, a bounded wait before the gate closes (CC:7671), a late stop with "stopped N frames late", cam1's stop ahead of the FIFO, safety stops send cam1 the next slot; test 2.3 expects equal counts only when neither Core is late. §6: the safety stop is told apart by `safetyStopState().active`, the failure stops go through one helper, and a late cam1 stop reaches `cam1.message` | taken |
| core-refs-5-8#3 | the take-pending flag joins `recordingFramesEnabled_` in the lock's step (CC:8778-8782, 8813); both halves of the gate test are quoted; step 5 stays PROBABLE and cites R-new3 | changed (§6): v2.1 set the flag only in takes with cam1 and dropped the fix's second half. §6 sets `takePending_` in every take, and each Core records where its last stretch lands, so a take's gate opens after it |
| core-refs-5-8#4 | `tc_offset_us` and T reach ProRes and H.264; `wallClockTimestampUs` follows the slot for DNG and MLV; three files added to T62 | taken |
| core-refs-5-8#6 | cam1 takes `clip_name` verbatim and checks it against ClipName.hpp's rules; an existing folder refuses the take | taken |
| red-team#1 | Speed Ramp numbers frames by count (CC:9334): two-camera takes keep the time index until the first ramp step, then count, flagged unsynced; a test in T62 and 2.3; Q13 and the summary say so. §6: the rule keys on `start_us`, the switch frame goes into `fps-ramp.txt`, and a test-only env forces the gap | taken (option a) |
| core-refs-3-4#8 | a cam1-only take does what `startSoundRecording` and `stopSoundRecording` do: `syncRecordingTracking` and the `recording` events, which drive the tally (App:14465-14473); App:8100 and 11965 are the LED's initial value only | taken |
| red-team#8 | §6.2 says the tally and the RecordingStart pulse lead frame 0 by up to the lead; a pulse at `start_us` waits for v2 | taken (the second option) |
| operator-rules#1 | the cost of following the preview is stated in §0, §6.1, Q1 and the summary; the HDMI status pill reads "READY · CAM1 ONLY · NO AUDIO" (§6: and "REC · CAM1 ONLY · NO AUDIO" in the take); "both always" is offered | taken; the default is still Patrik's call (Q1) |
| operator-rules#7 | the WebUI REC label names this page's press; with a NEXT TAKE pill set, a second line says what the camera's button records | taken |
| operator-rules#15 | when the system drops a camera the operator asked for, the REC label and the record readout are italic (`.system-value`, `cameraSet`); Auto stays plain | taken; §6 makes it buildable: an HDMI readout for a dropped cam1 ("READY · CAM0 ONLY · CAM1 OFFLINE"), italic through `font.italic` on the status pill's Text, and a `.record-label.system-value` selector in the WebUI |

### The relay

| Findings | v2.1 | Verdict |
| --- | --- | --- |
| consistency#2, core-refs-3-4#2, operator-rules#5 | both Cores run the primary's ladder: `set_mode_ladder` is forwarded and sent before `apply_preset` in the resync; the compare covers the ladder; "its own ladder stays off" is gone from §4.4 and Q15. §6: `set_mode_ladder` only when cam1's ladder differs; no mode keys under an active ladder or an override; `ladder_text` skipped; a 3-resync cap | taken: the shared-ladder option (operator-rules#5's least code). The held-off model would need a whole-mode push after every fps change and a camera-set mark on :8001 |
| consistency#3, operator-rules#12, core-refs-3-4#10 | a §3.3 row: `apply_preset`'s UI.conf writes (App:13996, 13978, 13981-14071) are skipped on the secondary, so T60's check holds; the relay also strips the bracketing keys and sends `timecodeMode` as `cameraTimecodeMode`; the POST list has 9 branches, with App:9166. §6: the secondary also ignores the four photo keys (App:13772-13786) and forces photo mode off at start, and `timecodeMode`'s value is mapped | taken (option a) |
| core-refs-3-4#1 | `settingsBody` is App:298-379; §4.4 lists the compared and the skipped fields. §6: `exposure_metering` compared; `ladder_text` and six more fields skipped | taken |
| core-refs-3-4#3 | cam1 is busy from the send of any forwarded command until its reply. §6: busy is a count of forwards queued or in flight, kept apart from the take state, and the wrapper counts under `commandMutex_` | changed: plus a 1 s wait before a refusal, so a quick setter in flight never refuses a REC press |
| core-refs-3-4#11 | `enter_standby` is forwarded only when the primary's reply has `"standby":true`, without `idle_timeout` | taken |
| red-team#3 | relink rules (§4.6): rejoin under the same `clip_name`, adopt when the primary has no take, else the orphan stop; frame lines carry no fds; a T69 check stalls the primary for 10 s | changed (§6): v2.1's adopt also caught a take the operator had stopped while the link was down. Now a stop that cannot be sent is kept and sent on relink, only a process that has had no take adopts, `recording_clip_name` names cam1's take, the rules also run at each poll, and the stall lasts 30 s |

### Start, unit and install

| Findings | v2.1 | Verdict |
| --- | --- | --- |
| consistency#5, operator-rules#4, red-team#2, core-refs-3-4#4 | no `PartOf=`; a restarted primary does not wait for cam1 and adopts its take on link; deploys and r4-M1 name both units. §6: §0 item 8 names the exception, and the restarted primary holds its trim and Start pre-roll until cam1 answers | taken for consistency#5 and red-team#2 (the "cam1 takes survive" option). Changed for core-refs-3-4#4 and operator-rules#4: their primary wait needs `App::start` reordered, so that the socket and web server start before `camera_.start` (App:8034 against 8056, 8068). v2.1 keeps today's order and accepts the cost |
| consistency#4 | the install copies the start script (checked with `cmp` and a grep) and the hardware file, and creates an empty config folder (`mkdir /home/pi/.config-cam1`), before `enable` | taken |
| consistency#6, red-team#9 | the 30 s socket wait has a timeout path: log one line, start without the idle wait; T60 notes the 30 s | taken |
| core-refs-3-4#5 | the port's I2C node goes to `openImx585Subdev` and its four users (CC:6927, 6962 via 7241/11563/12527, 7043, 6896). §6: a `--camera` node value names the node itself | taken |
| core-refs-3-4#6 | the unit has `User=pi` and the live `WorkingDirectory=`; test 0.1 supplies the rest; a get_state as pi (§6: in T68, once cam1 runs) | taken (a Python line, since core.py's socket path is fixed) |
| core-refs-3-4#7, red-team#7 | when config.txt names a sensor on the port, the no-sensor check looks again every 0.5 s for up to 20 s; the primary waits the same way for cam0's subdev | taken (20 s) |
| core-refs-3-4#9 | the gated part of the standby loop is App:8267-8282; its supervisor (App:8263-8266) stays on | taken |
| operator-rules#6 | Q24: a local `dual-sensor` branch in each repo; fix E goes on the driver's; the summary defines E | changed: Core is cut from what the Pi runs when T57 starts (now 9b5ea14), not from 31d5418 |
| red-team#4 | both Cores run without `APERTAR_RT`; RT, if wanted, is per thread (`APERTAR_RT_CAPTURE_PRIORITY`, CC:8988-8992) | taken (the ref is CC:8988-8992 at 31d5418, not the finding's CC:8672-8699) |

### Display

| Findings | v2.1 | Verdict |
| --- | --- | --- |
| consistency#7, operator-rules#13, ui-lib-drv-math#2, red-team#10 | the HDMI and WebUI fallback follows the frames alone; a same-inode socket counts as configured, with cam1 `offline`; the symlink tests expect OFFLINE in the pill. §6: the link decides first, so `not_found` needs no link; the pill check is in T66 | taken. The UI override for the second client's socket (ui-lib-drv-math#2, red-team#10) is not taken: it would add an env name, and the frames-only fallback makes the symlink test work |
| consistency#13, core-refs-5-8#5, ui-lib-drv-math#5 | the preset sites are out of §5.1's copy list; `previewSource` is neither saved in nor applied from presets in v1 | taken |
| core-refs-5-8#8 | the second WebUI stream drops its `src` while its pane is hidden and while the playback browser is open (`pbPauseLive`/`pbResumeLive`) | taken |
| ui-lib-drv-math#3 | cam1's liveness counts received frames before the recording cap (`framesReceived`); a T65 check with the cap at 0 (§6: `framesReceived` keeps moving; the main-pane check is in T66) | taken |

### Sync

| Findings | v2.1 | Verdict |
| --- | --- | --- |
| ui-lib-drv-math#1 | the cost of 720 MHz (4K Clear HDR 16-bit capped at 25.000 fps, 4K SDR and 1080p at 50.000 fps, on both sensors) is in §0, §2, risk 10, Q5 and the summary (§6: the summary and risk 10 also give the lock's cost) | taken (medium, not high: §7.5 was already headed 891 MHz) |
| core-refs-5-8#7 | §7.6 says ramp steps carry the base pin, so fix A covers them while the lock is on | taken |
| ui-lib-drv-math#6 | §7.4's PI-only figures: under 1 ms after 5-8 s, under 50 µs after 230-350 frames, `locked` after that | taken |

### Steps and tests

| Findings | v2.1 | Verdict |
| --- | --- | --- |
| consistency#9, operator-rules#9 | T57 comes first; T58's driver change depends on no step, but its checks (1.3, 1.4, 1.6, 1.9) need T57's pins, quantiser and trace, so T58 runs after T57 (§6); T59, T60 and T63 do not depend on T57-T58 | taken |
| consistency#10, ui-lib-drv-math#4, operator-rules#10 | test 1.10 is in T57, read inside a grace lengthened to 200 frames; the summary's T68 row names its tests | taken |
| consistency#11, ui-lib-drv-math#10 | the REC-while-busy check moves to T69 (§6: with the Mode Ladder off); T61 reads the journal; T62's first-frame check is [`start_us`, `start_us` + T) | taken (option 2) |
| consistency#12 | 0.7 times the stop too; T69 adds REC while cam1 writes and a delete of a missing clip; test 2.6 is new; T65 measures the GUI drops | taken |
| consistency#15 | r4-M1, r4-M2 and r4-M5 name r4's measurement plans; bare M ids stay claim-check ids | taken |
| ui-lib-drv-math#7 | test 1.9 predicts the truncation outcome and adds a second pin at VMAX 5406 | taken |
| ui-lib-drv-math#8 | test 1.1's parenthesis gives T27's readbacks and says 25 fps tells fix A apart only through Q | taken |
| ui-lib-drv-math#9 | test 1.5: within about 13 frames of the arm, 27-29 after a `set_fps` in Clear HDR; the trace marks the arm | taken |
| operator-rules#2 | refusals are proved with commands that change nothing (`set_zebra_enabled`, a delete of a missing clip); never `format_media`, `eject_media`, a `set_boot_config` without `dry_run`, or a real delete. §6: one 403 gate reply, and each POST is probed with a request its own handler refuses before writing | taken |
| operator-rules#3 | T68's order: the config.txt line, `sudo poweroff` and unplug, the sensor, power on, the unit; Q20 starts from power off. §6: T60 already enabled the unit, so T68's last step checks that it is active | taken |
| operator-rules#8 | a drop-in for 1.1 and the trace, with its undo and `systemctl show`; T60 checks a start line, not /run files; 1.7 is dropped. §6: one drop-in per test, the deadband only for 1.1 | taken (the drop option for 1.7) |
| operator-rules#14 | 0.3, 0.5 and 0.6 are marked Patrik's load runs; 0.6 has an exact `fio` line and its `rm`; 0.8 reads VmHWM and MemAvailable with a criterion; two-sensor reads find each subdev by name. §6: 0.6 checks for fio and makes its folder first; 0.8 has an ESTIMATE and a read before STOP | taken; the plan names only cam0's subdev ("imx585 10-001a", read in r5), since cam1's bus is unread |

### Numbers

| Findings | v2.1 | Verdict |
| --- | --- | --- |
| consistency#14, core-refs-5-8#9, operator-rules#11 | §8 counts 21 names and 4 files after v2.1's changes (v2 had 20 and 3, not 14); "each copying an existing pattern" is gone; `audio_enabled` is App:14231-14233. §6: 23 names (+`recording_clip_name`, +`adopted`), 4 files and one test-only env | taken (recounted) |
| (the summary's accuracy line) | about 30-46 µs maximum in the model; test 2.2 allows 55 | taken |

## 6 Re-check of the v2.1 draft (2026-11-04)

Before the commit, five reviewers read the v2.1 draft against the code at the refs, each from one angle:
- whether each §5 fix landed as its verifier meant (`fixes-a/F1-F14`, `fixes-b/F1-F8`);
- whether the design, the summary and this page agree (`fixes-c-crossfile/F1-F14`);
- whether the new code refs hold (`refs/F1-F7`);
- what breaks under the new rules (a red team, `red-team/RT-1` to `RT-16`).

Each finding went to an adversarial verifier, as in §5. All 59 held (35 confirmed, 24 partly; 8 high, 28 medium, 23
low), and none was refuted. Several were problems the v2.1 edits themselves had made: the T58 order, the exemption in
§6.1, the bare `timecodeMode` rename, `ladder_text` in the compare, the bundled drop-in, T60 checks that one sensor
cannot run, the adopt rule, and `not_found` against the symlink tests. Each was folded into v2.1 before the commit, as
below.

### Recording and takes

| Findings | v2.1 after the re-check | Verdict |
| --- | --- | --- |
| fixes-a/F2, fixes-c-crossfile/F4 | a cam0-only REC also waits for a busy cam1, then gets "One moment.", so cam0 never starts during cam1's manager start; any `record_start` during a cam1-only take gets "CAM1 is recording." (§4.3 table, §6.1, Q3) | taken |
| fixes-a/F13 | §0 item 5 and summary item 5 list refused and standby, and say that a press for cam1 alone is refused | taken |
| red-team/RT-4 | the lock reads `takePending_ \|\| recordingFramesEnabled_`; every take that passes the gates sets it, and a later refusal or the gate's close clears it (§6.2, §7.4); a T62 check | taken; amended in §7 (final/landed-RT4: not in cam1-only or Sound Recorder takes) |
| red-team/RT-8 | each Core records the slot its last stretch lands on, and a take's gate opens after it; the lead is max(500 ms, (D+2)·T + L); cam1's `record_start` stays behind the queued forwards | taken (the late-start branch, not the "unsynced" flag); amended in §7 (final/landed-RT8: two latencies in the lead) |
| fixes-b/F4, fixes-c-crossfile/F10, red-team/RT-11 | `recording_last_slot` is defined (k1−1 on time, the real last slot when late) and kept with the first slot until the next take; the relay turns cam1's late stop into "CAM1 stopped N frames late"; raw takes its first slot from the index anchor; ProRes and H.264 shift after a drop, which `slots.txt` cannot place | taken |
| refs/F4 | frame 0 of ProRes and H.264 is at CC:10144-10145 and CC:10181-10184; a T62 check for both formats | taken |
| refs/F6 | cam1 accepts `kMaxNameChars` + 5 characters; T62 checks 105, and T64 a 96-100-character cam0 name | taken |
| fixes-b/F5, refs/F7, red-team/RT-13 | the safety stop is told apart by `safetyStopState().active`; one helper at the four `checkRecordingFailure()` sites queues cam1's next-slot stop and keeps the tally on; checks in T62 and T64 with `APERTAR_CDNG_BUFFER_STOP_PERCENT=50` | changed: the state flag, not refs/F7's new `safety=true` field, which would add an API name; amended in §7 (the tally goes off at once; the checks move to T64, with a load) |
| fixes-b/F7, red-team/RT-15 | the Speed Ramp rule keys on `start_us`; the switch frame goes into `fps-ramp.txt`'s header; `APERTAR_TEST_DROP_FRAME` forces the gap (test only, §8) | taken |
| red-team/RT-14 | the relay never calls a controller accessor that takes `mutex_`: the command thread publishes the flags and the settings body; `record_stop` waits up to 200 ms until cam1's stop is written | taken |

### The relay

| Findings | v2.1 after the re-check | Verdict |
| --- | --- | --- |
| fixes-a/F1, fixes-c-crossfile/F1, refs/F1 | on the secondary, `apply_preset` ignores the four photo keys and writes no UI.conf key; photo mode, long exposure and bracketing are forced off at start; T60 reads cam1's photo flags and its `camera_settings.conf` | taken |
| fixes-a/F11, refs/F2 | `timecodeMode`'s value is mapped to `rec_run` or `free_run` as App:13975-13977 maps it; a T61 check with a SettingsBridge-style preset | taken |
| fixes-a/F3, fixes-a/F10, refs/F3 | `ladder_text` is skipped; the ladder's definition, `ladder_override` and `exposure_metering` are compared; six more fields are placed; T61-T66 run with the ladder off and manual ISO or a non-lossless format | taken |
| fixes-a/F14, red-team/RT-1 | the resync's three steps: `set_mode_ladder` only when it differs and not in a processed format; `apply_preset` without mode keys under an active ladder or an override; `set_clear_hdr` for an override. Each is sent whatever the last reply, and a 3-resync cap ends a loop; a T69 check | taken (RT-1's form, with fixes-a/F14's resend after step 2); amended in §7 (final/landed-RT1: the cap pauses the triggers) |
| red-team/RT-16 | the compare uses only a cam1 get_state newer than the last forward's reply, skips while forwards are pending, and resyncs after two differing compares in a row | taken |
| red-team/RT-3 | a take state and a forward count, shown as one word ranked lost > recording > writing > busy > ready; a slow poll during a stop reads `writing`; a T64 script | taken |
| red-team/RT-6 | the wrapper takes `commandMutex_` after the read-only commands and the flush abort, and counts the forward before it unlocks | taken; amended in §7 (final/landed-RT6: the relay's own setters count too) |
| fixes-a/F4, fixes-b/F1, fixes-c-crossfile/F3, red-team/RT-5, red-team/RT-12 | the relink rules, in order: rejoin, send a pending stop, adopt only in a process that has had no take, else the orphan stop. They also run at each poll; `recording_clip_name` names cam1's take; a link drop keeps the take state and the tally; an adopt sends `adopted:true` and no pulse; T64 tests through a socket forwarder | changed: the forwarder (fixes-c-crossfile/F3) instead of RT-5's relink-delay env, which would add a name to the primary; amended in §7 (final/landed-RT5: a STOP during a drop ends the take state) |
| fixes-b/F2, red-team/RT-9 | the link decides cam1's state first; `not_found` only with no link; cam1 stays configured once its socket has accepted | taken |
| fixes-c-crossfile/F12 | a slow reply keeps the last state; on a link with the primary awake, a cam1 in standby gets `wake`; a §4.6 row | taken (the drop option for "a slow reply means busy") |

### Start, unit and install

| Findings | v2.1 after the re-check | Verdict |
| --- | --- | --- |
| fixes-a/F5, red-team/RT-2 | §0 item 8 and the summary name the restart exception; core-refs-3-4#4 and operator-rules#4 are marked changed in §5; the ControlClient starts before the trim and watcher threads, and a "cam1 unknown" flag holds the trim and the Start pre-roll; a T64 check | taken (option b); amended in §7 (final/landed-RT2a, final/landed-RT2b: the flag is set before the threads start, and the T64 check follows the trim wait) |
| fixes-a/F7 | a `--camera` value other than cam0 or cam1 names the I2C node, and its port is the `__symbols__` entry; a T60 check of the WDR write | taken |
| fixes-a/F12, fixes-c-crossfile/F13 | T59 runs the binary directly with the T60 line's env and `--camera cam1`; T68's no-sensor check goes through the installed unit, and its last step checks that the unit is active | taken; amended in §7 (final/landed-F13: T59 makes the cam1 hardware file and config folder first) |
| fixes-b/F3, fixes-c-crossfile/F6 | T60 keeps only the install checks one sensor allows (the grep, `is-enabled`, the boot's no-sensor line, NRestarts 0); the get_state as pi moves to T68, the primary restart under the real unit to T69 | taken |
| fixes-c-crossfile/F14 | P25 and consistency#4 say the install creates an empty config folder | taken |
| fixes-c-crossfile/F5 | one 403 gate reply before any route logic; each POST is probed with a request its own handler refuses before writing; the rule is "never a `set_boot_config` without `dry_run`" | taken |

### Display

| Findings | v2.1 after the re-check | Verdict |
| --- | --- | --- |
| fixes-c-crossfile/F8, fixes-c-crossfile/F11, refs/F5, red-team/RT-7 | the status pill says what a press records whenever it differs from the choice or the screen: CAM1 ONLY in the next take and the running one, an italic CAM0 ONLY · CAM1 <state> when the system drops cam1, and an amber NO SIGNAL readout. HDMI italics come from `font.italic` on the pill's Text; the WebUI's label selector joins the italic rule; "CAM1 has no picture." only for a stream that stalled; checks in T66 and T67 | taken; amended in §7 (final/landed-RT7-F11: the readout also shows whenever cam0 sits out) |
| fixes-a/F8 | T65 checks `cam1.state`, CB's parse and `framesReceived` under the cap; the pill and main-pane checks move to T66 | taken |

### Steps and tests

| Findings | v2.1 after the re-check | Verdict |
| --- | --- | --- |
| fixes-a/F6, fixes-c-crossfile/F7 | T58 runs after T57, because its checks need T57's pins, quantiser and trace | taken |
| fixes-a/F9 | the T69 busy check runs with the Mode Ladder off | taken |
| fixes-b/F6, red-team/RT-10 | the T69 stall is a `kill -STOP` of the primary's MainPID for 30 s, with both outcomes predicted; the relay logs link down and relink | taken |
| fixes-c-crossfile/F2 | one drop-in per test: the deadband for 1.1 only, the trace alone for 1.2 and 1.4-1.8, the grace for 1.10 | taken |
| fixes-c-crossfile/F9 | 0.6 checks for fio and makes its folder; 0.8 has an ESTIMATE and a MemAvailable read before STOP | taken |

### Numbers

| Findings | v2.1 after the re-check | Verdict |
| --- | --- | --- |
| fixes-b/F8 | the summary's item 7 and risk 10 give the lock's cost at 720 MHz | taken |
| (recount after the above) | §8: 23 names (+`recording_clip_name`, +`adopted`) and 4 files, plus one test-only env; §9: about 2,500 lines and 80 h (T60 160 lines; T61 520, 12 h; T62 200, 7 h; T64 330, 10 h) | taken; superseded by §7's recount |

## 7 Final re-check (2026-11-04)

Before the commit, four reviewers read the draft against the code at the refs once more, after the §6 fixes, each
from one angle:
- whether each §6 fix landed as its verifier meant (`landed-*`, 11 findings);
- whether the design, the summary and this page agree (`cons-1` to `cons-18`);
- whether the new code refs hold (`refs-1` to `refs-4`);
- what breaks under the new rules (a red team, `rt-1` to `rt-14`).

Each finding went to an adversarial verifier, as in §5 and §6. All 47 held (33 confirmed, 14 partly; 6 high, 15
medium, 26 low), and none was refuted. The ids carry `final/` here, so they do not collide with §6's. Two §6 fixes
drew two findings each: `final/landed-RT2a` is the T64 pre-roll check and `final/landed-RT2b` the flag's start race;
`final/landed-RT13a` is the safety-stop check with no load and `final/landed-RT13b` the T62 check that proves nothing.

The six high ones:
- `takePending_` was never cleared on the primary after a cam1-only take, which ended the acquisition stretch for good;
- a T64 pre-roll check that a correct build fails;
- the relay's own setters were not counted as busy, so cam0 could start during a resync's manager start;
- STOP was refused while cam1 was busy;
- a crashed cam1 could not restart during its own cam1-only take, so the tally stayed on with nothing recording;
- a race in which a poll adopted or stopped cam1's half of a take that was still starting.

Several were again made by the earlier edits: the merged RT-7/F11 readout condition, T62 checks that the §6 fixes left
with nothing to measure, "both Cores' start waits", and two meanings of L in the lead.

### Recording and takes

| Findings | v2.1 after the final re-check | Verdict |
| --- | --- | --- |
| final/landed-RT4, final/rt-4 | `takePending_` only on a Core whose own camera records the take: on the primary never in a cam1-only or Sound Recorder take, whose stop never reaches CC:7671 (§6.2 step 5, §7.4); a T64 check that the primary still stretches after a cam1-only take | taken |
| final/landed-RT8, final/cons-5 | the lead is max(500 ms, L_start + T, (D+2)·T + L_cam1): L_start is the slower Core's time from the pick to its armed gate, which 0.7 bounds; L_cam1 is the pick-to-receipt time on cam1, which the relay logs per take; about 0.53-0.84 s in Clear HDR; T62's hand-made `start_us` uses it | changed: landed-RT8's two latencies, with cons-5's armed-gate definition |
| final/cons-3, final/rt-13 | a "cam1-only take" paragraph in §6.2: steps 1-3 and cam1's side of 5-6, no step 4; the press waits 1 s for cam1; a refusal gives cam1's reason, no reply gives "CAM1 did not answer." and a stop for a late start, remembered for rule 2; the stop is the two-camera stop without the local call; §4.6's refusal row; a T64 check with `kill -STOP` | taken |
| final/rt-2, final/rt-6 | the command thread publishes the starting take (the clip_name sent cam1, verbatim, and its cameras) before the relay sends cam1's `record_start`; every remembered take and pending stop carries that name, and the rules compare cam1's `recording_clip_name` with it (§4.1, §4.6, §6.2 step 3); T64: 20 two-camera and 20 cam1-only takes, none stopped or adopted | taken |
| final/cons-6 | slot timecode keys on `tc_offset_us`, which each Core sees, not on "both cameras and locked" (§6.3) | taken |
| final/rt-10 | a failure stop turns the tally off at once, as today; "keeps the tally on" is gone (§6.2, §4.6) | taken (the drop, not a tally hold) |
| final/rt-11 | the stop's wait for the relay is bounded at the stop lead minus 2T, and the stop lead is max(100 ms, 3T) until 0.7 measures it; a wait that runs out still stops cam0 on the same `stop_us` (§4.1, §6.2) | changed: a stop lead of at least 3T, so the bound stays positive at any fps |
| final/cons-14 | presets carry `recordBothCamerasEnabled` at the `recordAudioEnabled` sites (App:7797, 14003; WCP:18657; SettingsBridge.cpp:2184, 2276), in T64's files, with a check | taken (Q17 stays yes) |

### The relay

| Findings | v2.1 after the final re-check | Verdict |
| --- | --- | --- |
| final/cons-1, final/landed-RT6, final/rt-5 | the pending count covers every setter the relay sends cam1: the wrapper's forwards, the resync's three steps, and the relink's `wake` and `enter_standby`; reads and the record commands never count. The relay bumps the count, re-reads the published take, and backs off while a take is starting (§4.1, §4.3, §4.5); T61 and T69 checks | taken (cons-1's scope with rt-5's hand-off; the pending and orphan stops rt-5 would count read `writing` instead) |
| final/cons-2 | the 1 s wait, "One moment." and the 10 s drop gate `record_start` only; STOP, the WebUI's stop and cam0's buffer safety stop never wait; `record_stop` is back on the busy row's list, as in v1 (§4.3, §4.5, §4.6, Q3); a T64 check | taken |
| final/landed-RT1 | after the cap, no trigger schedules a resync until a compare passes, cam1 answers ok to a forwarded change, or a relink; `refused` joins the ranking: lost > recording > writing > refused > busy > ready (§4.4, §4.5); a T61 check | taken |
| final/rt-3 | `CameraController::start` sets `ladderOverride_` when the ladder is active and a rewrite of the started settings would change the mode, so both Cores agree after a one-Core restart; on the one-sensor rig get_state then shows the override after such a restart (§4.4, T61); a T69 check | taken |
| final/landed-RT5, final/cons-11, final/rt-7 | `lost` has an end: after cam1's own safety or failure stop it lasts until the running take stops; after a link drop until the relink, a STOP during the drop included, which ends the take state and keeps the pending stop. `offline` excludes that case (§4.5, §4.6) | taken |
| final/cons-18 | the exposure setters are `set_iso(_auto)`, `set_shutter_*`, `set_exposure_*` and `set_wb(_auto)`, as in v1; `set_af_*` and `set_hdr_*` are not (§4.2, Q7). `user_activity` passes both rows, as in v1 | taken |
| final/cons-7 | "the compare, the resync and the secondary's start wait" (§4.3, and the P2 row in §2) | taken |
| final/rt-12 | risk 11 names the case left open: a primary restarted between a link-down STOP and the relink adopts the stopped take, and one STOP ends it again | taken (documented; v1 keeps no pending-stop file under /run) |

### Start, unit and install

| Findings | v2.1 after the final re-check | Verdict |
| --- | --- | --- |
| final/rt-1, final/cons-4 | the secondary's start wait does not count a cam1-only take against idle, so a crashed cam1 restarts and relinks, and "cam1 back without its take" ends the take with the tally off (§3.4, §4.6, §7.6); a T64 check | taken (cons-4's option a) |
| final/landed-RT2a, final/refs-1 | the T64 adopt check follows the 2-min trim wait: no trim or pre-roll result line before the stop, then the trim's, then the pre-roll's; a take kept running over about 2 min shows result=skipped before the stop | taken (landed-RT2a's wording, refs-1's longer take as the alternative) |
| final/refs-2 | the trim joins the writes-pending sites, so it waits for cam1's drain (§4.3); a T69 check of the journal order on the real cam1 | taken |
| final/landed-RT2b, final/rt-14 | `App::start` sets the "cam1 unknown" flag before the trim and watcher threads whenever config.txt names cam1 or the socket path exists; it ends at the first get_state or after 2 s of failed connects of any kind (§3.4) | changed: rt-14's test, without landed-RT2b's synchronous first connect |
| final/landed-F13 | T59 writes the cam1 hardware file and makes the config folder before its check (§3.4's install steps 2-3, early) | taken |
| final/cons-12 | §0 item 8 and summary item 7: with cam1's lock off and HBLANK ≠ 0, one frame runs short and dark, and the phase steps; the README names the restart exception | taken |

### Display

| Findings | v2.1 after the final re-check | Verdict |
| --- | --- | --- |
| final/landed-RT7-F11 | the status pill's readout shows whenever cam0 sits out, or `record_cameras` differs from the choice or the screen (§5.2) | taken |
| final/rt-8 | NO SIGNAL only while cam1's client has had no frame since it connected; a stalled stream reads "READY · CAM1 NO PICTURE", and the press is refused. For a busy cam1, `record_cameras` follows the 10 s drop, so "CAM0 ONLY · CAM1 BUSY" shows only once a press would roll cam0 (§4.5, §5.2); T66 and T69 checks | taken, plus the busy readout, which rt-8 raised without a fix |
| final/rt-9 | the 1 s of a stalled stream runs from the later of cam1's last frame and its last reply to a reconfigure or `wake` (§6.1) | taken |
| final/cons-13 | in Sound Recorder mode the NEXT TAKE pills are hidden and the page sends no `cameras` (§5.3); a T67 check | taken |
| final/cons-16 | T67's check starts with cam1 configured (the symlink or the simulated cam1) | taken |
| final/refs-4 | split DRM: v1 shows cam0 only in the monitor-only process, with every EMW use of the cam1 client behind a `typeof` guard, as `gyroConfigBridge` has (§5.2, T65) | taken (the guard, the existing pattern; a second client in that process waits) |

### Steps and tests

| Findings | v2.1 after the final re-check | Verdict |
| --- | --- | --- |
| final/landed-RT13a, final/refs-3 | T64's safety-stop check names its load: 4K Clear HDR 16-bit lossless JPEG at 25 fps, whose encoder runs at about 17.5 fps (drop-frames README row 12), or a 4-frame queue | taken (refs-3's load, landed-RT13a's queue as the alternative) |
| final/landed-RT13b, final/cons-9 | T62's safety-stop check is dropped, since its takes are cam0-only; T62 builds the branch and T64 tests it; the summary's T62 row says so | changed: dropped, not kept as a regression check, which would need a load too |
| final/cons-8 | the `<next>_cam1` folder check moves to T64, with CC:1182-1197 in its files | taken |
| final/cons-10 | T62: without the fields, frame 0 is the first frame after the gate arms, and press to frame 0 matches 0.7 | taken |
| final/cons-15 | the speed-ramp refusal in a cam1-only take is §4.3's "cam1 records alone" row (§7.6) | taken |
| final/cons-17 | T57's trace prints every frame, before the early return for an inactive lock, so test 1.2 has data (§7.4, §10) | taken |

### Numbers

| Findings | v2.1 after the final re-check | Verdict |
| --- | --- | --- |
| (recount after the above) | §8 unchanged: 23 names and 4 files, plus one test-only env; §9: about 2,600 lines and 83 h (T61 550, 13 h; T64 410, 12 h; T65 155; T66 230; T67 205) | taken |
