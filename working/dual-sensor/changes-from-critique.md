# Dual sensor: what the critiques changed (2026-11-04)

Two critics read the drafts against the code:
- `sync-critique.md` checked `sync-synthesis.md`. It has 14 claims (S1-S14) and 11 gaps ("Missing" 1-11).
- `critique-merged-v1.md` checked `design-merged-v1.md`. It has 25 points (P1-P25).

This page says, for each point, what `design-dual-sensor.md` (v2) does now:
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
| 3 | Re-enumeration on reconfigure writes HBLANK on the other sensor. Two fixes: keep one CameraManager, or patch the fork's init write | v1 avoids it instead: the busy window (§4.3), both Cores' wait for idle (§3.4), and HBLANK 0 under the lock. The two fixes stay in reserve, used if M2 shows a cost (§11 risk 1) | changed |
| 4 | Fix E is not atomic | as S5 | taken |
| 5 | Clear HDR VMAX parity | as S6 | taken |
| 6 | Shared bandwidth changes the drop rate, D's spread and the holes | §2 bandwidth row; T56 0.5 and 0.6; M1, M5; 2× 4K HDR16 is out | taken |
| 7 | D is not constant (skips, drops, BE contention) | §7.5 "Not in the budget"; the trace in T57 shows it | taken |
| 8 | Clear HDR at 30 fps locks if the sensor runs fast against the Pi | §7.5 table row; Q14 | taken |
| 9 | Two period definitions (decimal 23.976 against 24000/1001) | §7.2: one rational T for the grid, the index and the timecode | taken |
| 10 | The top-fps clamp re-enters the lattice | as S4 | taken |
| 11 | Audio on both Cores | the secondary records no audio (§3.3, §6.3); Q4 | taken |

## 2 Panel critique

| # | Sev. | Point | v2 | Verdict |
| --- | --- | --- | --- | --- |
| P1 | HIGH | Forwarded presets and the resync write UI.conf keys (standby timeout, photo mode) into cam1 | cam1 gets only the camera keys, minus three (§4.4). The idle-standby loop and the photo restore are off on the secondary (§3.3). The check is in T60 | taken |
| P2 | HIGH | "Idle" ignored the storage pre-roll and photo mode, so the resync could copy the pre-roll fps to cam1 just before a take | one idle test (§4.3) for the compare, the resync and both start waits; no compare in photo mode. The check is in T61 | taken |
| P3 | MED | The 500 ms lead delayed every take, cam0-only ones too | the lead applies only when cam1 is in the take (§6.2). The check is in T62 | taken |
| P4 | MED | A quick REC while cam1 still writes: cam1 dropped silently, or it starts late | (a) REC refuses: "Wait for CAM1 to finish writing to media." (§4.6). (b) The relay reads `media_write_state` (§4.1). (d) The delete gates check cam1 too (§4.3). (c) is changed: a late Core is not refused. It starts on its next frame and reports `first_slot`, and the pill shows the offset (§6.2). A take with a known offset beats losing cam1's take for one frame | changed (c) |
| P5 | MED | REC during cam1's forwarded reconfigure | the busy window (§4.3): "CAM1 is applying a change. One moment." The check is in T61 | taken |
| P6 | MED | cam1's stop syncfs can stall cam0's writers | the secondary never syncfs's the volume. It fsyncs its own files, always, not only while the primary records (§3.3): one rule, the same durability for its own take. T56 test 0.5 measures the cost | changed |
| P7 | MED | A lost cam1-only take leaves the tally on and `recording` true | `cam1RecordingActive()` is `cam1.state == recording`. On `lost` the primary publishes `active:false` and undoes the tracking (§4.3, §4.6). The check is in T64 | taken |
| P8 | MED | No rule for a refused forwarded setter; the compare covered 8 of about 40 fields | a refusal sets `cam1.message` and schedules a resync; the compare covers every field the resync sets (§4.4) | taken |
| P9 | MED | No safe command line for hand-run test Cores | the two full lines under §9; the writes-pending check moves to T69 | taken |
| P10 | MED | Both Cores probe at the same moment at every boot | the secondary waits for the primary's socket and for idle. The primary also waits while cam1 records a take of its own, so a restarted primary does not disturb it (§3.4). `RestartSec=5`. The check is in T69 | taken, extended |
| P11 | MED | Photo mode with a cam1 preview source frames on cam1 and shoots cam0 | cam1 sources show cam0, tagged "PHOTO · CAM0" (§5.2) | taken |
| P12 | LOW | POSTs on :8001 bypass the allowlist | every POST on :8001 is refused (§3.3). The check is in T60 | taken |
| P13 | LOW | The secondary's low-power restores wake the whole Pi | they are off on the secondary; `enter_standby` goes to cam1 on a relink during standby (§3.3, §4.6) | taken |
| P14 | LOW | `APERTAR_MEDIA_TUNE=0` was missing | it is in the unit (§3.4) | taken |
| P15 | LOW | The flat parser cannot read cam1's scalars | one scalar reader by key (§4.1) | taken |
| P16 | LOW | With cam0 dead, the primary takes cam1's sensor and the secondary loops | the critic's second fix: the secondary exits 0 on EBUSY (§3.2). The primary keeps today's fallback, so a rig with a dead cam0 still shoots on cam1 | changed (the alternative) |
| P17 | LOW | A "clean" second pane also lost the LUT, desqueeze and rotation | both panes keep the display transforms; only the aids and guides stay on the main pane (§5.2) | taken |
| P18 | LOW | cam1's preview client misses the recording fps cap | `recordingChanged` reaches it (§5.2). The check is in T65 | taken |
| P19 | LOW | Sound Recorder mode still named cameras | `record_cameras` is `none`, the label is "REC SOUND", and an explicit `cameras` is refused (§4.5, §5.3, §6.1) | taken |
| P20 | LOW | Speed ramps with two cameras were not covered | allowed in two-camera takes, unsynced during the ramp; refused in cam1-only takes (§7.6, Q13) | taken |
| P21 | LOW | Four decisions had no question | Q17 (presets carry the policy), Q18 (no preview-source button in v1), Q3 (an explicit `both` with cam1 not ready: cam0 rolls), Q19 (the DNG serial is unchanged in v1) | taken |
| P22 | LOW | A reply timeout would mark cam1 offline during its own stop | offline only on EOF or a failed connect; a slow reply means busy (§4.1) | taken |
| P23 | LOW | A stale socket file made a single-camera rig "configured" | the socket must accept a connection (§4.1) | taken |
| P24 | LOW | The WebUI in Both during a take was not tested | a T69 check (§9, §10 Part 2) | taken |
| P25 | LOW | No install step, no boot check, and the no-sensor exit came too late | the check is in `main()` before `start()` (§3.2); the install and two checks are in §3.4 and T60; `APERTAR_RT` is stated for cam1 | taken |

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
| An explicit `cameras` naming a cam1 that is not ready no longer refuses the take | v1's rule conflicted with the default "cam0 rolls alone" (P21c) |

## 4 Stale KB pages the claim check found

These are not part of the plan. They are fixed in their own KB commit:

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
