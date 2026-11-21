# The fixes already made, checked against the owner's recorded decisions

Read 2026-11-20/21 against `../owner-recorded-decisions-a.md` (DA-*), `../owner-recorded-decisions-b.md` (DB-*), their
source pages, the KB tools and the rig snapshots of the NVMe campaign
(`working/drop-frames/nvme-campaign/run-20261110/audio-forensics/20261111-090228-baseline-EST/`: `UI.conf`,
`api_state.json`, 2026-11-11 09:02). Commits: Core `01f170c..8bfc242` (C1-C30), UI `7ea9afc..ac1fc28` (U1-U3), imx283
`68b7dc9..36d484b` (D2-1), and the held lane commit `lane-core1 19e7eb8`. Code read at `@core-work` / `@ui-work`
(improvement branch), `@cinemate-port`, `@upstream-1.6.0`.

Rule: a recorded decision stays. Where it makes a stock camera (original driver, 720x720 screen, a 1.6.0 hardware file,
no port keys) behave differently from 1.6.0, it becomes a setting at the 1.6.0 value. A fix that restores 1.6.0 for a
stock camera is right, but the rig must be able to get its behaviour back with a setting, and he is told how.

Rig facts used (KB): CM5 Lite, one IMX585 on cam0 (an IMX283 on cam1 from 2026-11-10, unplugged 2026-11-11), CFexpress
hat on bus 1, HDMI monitor, no touch screen, no IMU (`[imu]`/`[mpu6050]` template leftovers enabled), NeoRotary 4 on bus 1.

## Verdicts

| fix (log id, commit) | touches decision (id, his words) | verdict | what changes, or what his rig must do |
| --- | --- | --- | --- |
| C1 `04fe197` GPIO chip a setting again | Review request 16 (2026-11-17): "Put the GPIO chip definition back"; DA-40 (2026-10-30): "GPIO settings card: On, Pressed (low/high), Pull, Debounce; poll_ms and chip stay text-only" | needs his answer (poll_ms only) | Request 16 replaces DA-40 for `chip`. It does not cover `poll_ms`, which C1 also put on the card (`ControlsModel.hpp`, "Poll every (ms)"). Variant if he keeps DA-40: drop the one `poll_ms` row, keep `chip`. His file has `chip=auto` in both `[gpio_buttons]` and `[gpio_encoders]`: equal values, so the new `gpio_chip_shared` warning does not fire (`HardwareConfigText.hpp`, test `trim(buttons) != trim(encoders)`, confirmed). Its Pi check needs a second gpiochip he does not have: "not run", for the original developer |
| C2 `7dc6f7a` + U1 `6a59d83` 720x720 fallback | none of his (DA notes: the T38 1080p fallback "no row names Patrik") | fine | Rig file (KB copy 2026-11-08) has `ui_width=1920 ui_height=1080 ui_layout=landscape_large hdmi_external_only=true`: no change if the live file still has them (step 1) |
| U2 `2d9cf94` + C3 `ff4c7c5` audio outline off | none (`92d0970`/`e061be8` carry no "(Patrik)") | fine | His `UI.conf` (2026-11-11) has no `audioRecordedOutlineEnabled` key, so the red outline he had on HDMI (port default on) goes off. If he wants it: step 6 |
| U3 `ac1fc28` HDMI timecode white until the key is stored | DB-39 / DA-97, request 27: "Red timecode while recording as an option, default on (the touch screen and WebUI were always red, HDMI never)"; off keeps all three white | known conflict, **corrected**: right by the rule, his rig not affected | Stock: touch and WebUI red, HDMI white = 1.6.0 (`ExternalMonitorWindow.qml:1129@upstream-1.6.0` white). His `UI.conf` (2026-11-11) holds `recordingRedTimecodeEnabled=true`, so `recordingRedTimecodeSet` is true and HDMI stays red (probable; step 5 confirms). Only after a `UI.conf` reset does HDMI go white until he toggles Red Timecode off and on. Small honesty gap left: on a stock camera the switch reads "On (touch screen, HDMI, WebUI)" while HDMI is white; the Settings line should say HDMI follows once the switch is used |
| C4 `e4246ee` media_state once | none | fine | `longtakes.py:466, :587, :1727` read `media_state`; the value is unchanged |
| C5 `0977dd6` pre-roll off by default | nvme-campaign plan "the pre-roll stays ON as in real use" (`plan.md:231, :307`); DB-71 tests as in real life; DB-65 "everything back" | known conflict, **confirmed**: right by the rule | 2026-11-11 state: `storage_preroll_auto=true`, last "ok: 5.0 s at 60 fps": it ran by default. The KB file has no `[media]`. After C5: `longtakes.py:2766` marks every take bad (`storage_preroll_auto` must be true); `e3-unit.sh:19-20` waits for `reason=start.*result=`, but the off line is "reason=start not requested ..." (`App:11148@core-work`, no `result=`), so it prints NOT STARTED after 10 min. Way back: step 3 (`set_storage_preroll value=on` writes `[media] preroll=on`, `App:12902-12928@core-work`) |
| C6 `615b48c` lossy DNG drops pages in the writer under `sync` | DB-65 `APERTAR_DNG_DONTNEED=sync` default; DB-71 / DB-74 campaign recipes; DB-93 "Core changes stay knob-gated" | needs his answer | Restores 1.6.0 for stock (`LossyDngEncoder.cpp:82@upstream-1.6.0`). On his rig `sync` used to leave lossy pages to the kernel; now it drops per file. Lossy 3:1 / 5:1 are cDNG compressions on his camera (`RecordingFormat::LossyDng`, `CC:3046-3051`) and were measured on 2026-11-11 (estimator: "lossy DNG 3:1 and 5:1 at 60", 2880x2160 3:1 lasted 28 s). No setting gives the old pair back (`off` also stops the cDNG drop). Variant: once storage-settings commit 24 makes `writer` the stock default, `sync` (his opt-in through `~/apertar-media-tune.conf`) can mean "no drop" for lossy again, as measured; until then tell him, and re-run one lossy 3:1 probe (step 11) |
| C7 `b923c06` TDN switch leaves H.264/ProRes alone | DB-65 preview TDN switch, default off | fine | His switch was about the monitor of raw takes ("the raw DNGs never change"); H.264/ProRes record the ISP output, so they keep TDN. No KB test arm uses TDN off in H.264/ProRes (the estimator ran "TDN off" as the reference for raw) |
| C8 `d1dcdee` test_input refuses scripts | DA-28 / DA-29 scripts on (physical) buttons; DA-104 / DB-65 Remote controls kept (`1319967`, "another session", no decision on scripts) | fine | Remote controls and Try keep every non-script action. A remote row mapped to a script now needs the physical button. His file maps no script |
| C9 `3650027` preview TDN on by default | DB-65 "preview temporal-denoise switch default off" | known conflict, **confirmed**: right by the rule | 2026-11-11 state `preview_tdn=false`, active tuning `imx585_clearHDR_notdn.json`. Core writes every key on every save (`writeCaptureSettings`, `CC:975@core-work`, also each `profile.<format>.` copy), so `preview_tdn=false` is in his `camera_settings.conf` (probable; step 2). It matters: the estimator measured "HDR16 with TDN on at 25" dropping 128 frames (`nvme-campaign/findings.md:206`) |
| C10 `0d13a6f` photo mode follows the switch | DB-65 | fine | Photo stills are developed from the raw frame (`CC:6845-6852`) |
| C11 `9bd7610` reconfigure on Clear HDR storage-depth change | DB-1 / DB-2 / DA-86 (12 and 16 bit, user picks) | fine | A cDNG <-> MLV switch in 12-bit Clear HDR restarts the stream |
| C12 `93cab28` entering Clear HDR on the IMX585 starts at 3840x2160 | DB-3 "16-bit is 4K only"; DB-50 Clear HDR pills; DB-45 ladder blocks manual changes; DA-95 "4K Clear HDR" label | fine | The touch entry "4K Clear HDR" now gets 4K; the WebUI pills still send the size and resend the FPS only with the ladder off. Touch check on HDMI with a mouse (DA-77) |
| C13 `a36c52f` binned 1920x1080 held back in 12-bit Clear HDR | DA-86 / DB-1 Clear HDR 12-bit is a user mode; DB-72 "keep Clear HDR 12-bit as a primary mode"; DB-78 / DB-81 driver tables are his | needs his answer | Not a stock issue (1.6.0 / fork main offer no such row). It removes a mode he recorded: "2kHDR12 25 fps" on 2026-11-07 (`nvme-campaign/plan.md:52`, frame size 3.12 MB at `:242`), on a probable cause. Keep held until the capture pair (hdr12 P7) or he says the binned output looked right; way back: revert `a36c52f` (step 8) |
| C14 `56e135c` clip label Clear HDR 12-bit vs Log | DA-67 FORMAT row; DA-53 copy the touch UI's wording for parity | fine | WebUI FORMAT row only. The touch Clip Viewer still labels from its own probe (DA-60: clip facts from Core later); parity gap noted, not a decision conflict |
| D2-1 `36d484b` imx283 `crop_vmax` off by default | DB-79 "keep `always-on` ... with `crop_vmax=0 experimental_modes=0`"; DB-81 ask him before a driver change | fine | The default now equals his setting. Driver commit only on the draft PR; DB-81 is met if he is told before it is installed (step 12) |
| C15 `b13ccb5` playback JPEG handle | none | fine | none |
| C16 `9ec7bbf` clip-name example from a listing | DA-75 (readdir of 105,000 entries costs 3.7 s on his card) | fine | That figure is one clip folder; the new readdir lists the media root (clip folders) once a second while idle, never in a take. Check on the Pi as the log says |
| C17 `a663cfc` part folders made by the writers | DA-105 / DB-66 / DB-67 clip split, `frames_per_folder=5000` + merge; DB-68 his dead-medium fix | fine | Keeps and extends the bounded stop he asked for. Pi check with his 5000 split (the log's example uses 100) |
| C18 `bfd032e` audio writer queue capped | campaign lever `APERTAR_AUDIO_BUFFER_MS` (storage audit) untouched | fine | Cap 64 MB (`APERTAR_AUDIO_WRITER_BYTES`). Largest backlog in his campaign journals: `peak_backlog_kb=2570` (2.5 MB), 25 times below the cap. The `audio writer: peak_backlog_kb=` line is unchanged |
| C19 `7f188a5` audio_url encoding | none | fine | none |
| C20 `6a05fe5` key edit in every copy of a section | DA-3 Core writes the file | fine | Upstream's rule. The log's IMU example cannot be tried on his rig (no IMU) |
| C21 `0c85297` missing file seeded from /boot | DA-84 per-instance `APERTAR_HARDWARE_CONFIG` for a cam1 Core | fine | His `/boot/firmware` copy is "dead" (stale). Only hit when `~/apertar-hardware.conf` is missing; for a cam1 instance started without its copied file (`design-dual-sensor.md:253` copies first) the seed would be that stale copy. Note for the dual-sensor work |
| C22 `fe269e7` get_controls -> GET /api/config | DA-1 "with the functionality of Apertar api"; DA-38 hat on Config > Hardware | fine | KB tools follow: `tutorials/tutorial.py:48-50` (comment added; the two old names still sit in `SAFE_CORE_CMDS`, harmless), `working/tools/controls_page_test.js:8-9, :36, :70-77` serves both |
| C23 `3660aab` controls_history -> /api/config/history | DA-25 "History: 20 versions + a pinned 'Before Controls'"; DA-18 Undo | fine | Store untouched. Over ssh: `curl -s localhost:8000/api/config/history` |
| C24 `bdef3d1` I2C scan bounded at 1 s | DA-8 detect and show; DA-2 his bus-1 fix | fine, unmeasured on his bus | His bus 1 has the hat MCU 0x34 and the seesaw 0x49 behind a Qwiic hub; scan time never recorded (HANDOFF-next test 4 has the result, not the time). Step 9 |
| C25 `d40a1d6` list_actions without values | none | fine | KB `controls_page_test.js:36-37` handles both catalog shapes |
| C26 `4b5ad25` three commands under the command lock | DA-23 Listen + phone; DA-24 Listen on a fresh board | fine | Listen now waits behind a long command; no decision on its latency |
| C27 `43d8a19` whole-file save written, checker advises | DA-18 "red banner + Undo last save"; DA-20 / Q17 stale-save merge | fine | Key edits still refused on a new error (KB `controls_store_test.cpp:139` still passes). Fix-log text to correct: C27 says the stale-merge path "is deleted by commit 5"; the audit dropped commit 5, so the merge stays, and its merged text is not refused on new errors but is shown as a review first (DA-20) |
| C28 `1a417c8` Undo/restore of a kept version | DA-4 / Q2 "`[run_script]` paths: ssh only; the browser cannot write them"; DA-18 Undo; DA-28 / DA-29 | fine: **keeps Q2** | Guard in `saveLocked` (`HardwareConfigStore.cpp:350-355@core-work`) runs for every save: whole text (POST `/api/config`, `set_controls text=`, restore), stale merge and key edits, trusted or not. A new path passes only when a kept version (history folder or `hardware-last-written.conf`, `:46-53`) has exactly those paths. Edge: a version saved while the switch was unset counts as kept |
| C29 `f4de756` the ssh-only rule as `APERTAR_SCRIPT_PATHS=ssh` | DA-4 / Q2 kept; stock rule | fine: **keeps Q2 on his rig only with the switch** | Unset = 1.6.0 (browser writes paths), stated in README:177. His rig must set it (step 4). Breaks a KB test: `working/tools/controls_store_test.cpp:149, :151` expect the refusal with no variable set; the audit's planned `setenv` before section 5 is not in the file (step 10) |
| C30 `8bfc242` sanity checks on every whole-file save | none | fine | 1.6.0's sentences |
| held `lane-core1 19e7eb8` FPS/ISO step lists end at the last listed value | **DB-36, request 24** (2026-10-28, `working/ramp-ladder/README.md:77-78`, "What Patrik asked for"): "values above the mode's ceiling stay visible but greyed out, and the system adds the capped value (`fps_max`) as the top selectable entry, marked as camera-set. Same for ISO with `iso_max`"; DB-37 approved T33 design; DB-34 free stepping | **conflict** | It reverses request 24 for knobs, buttons and pots only. The WebUI (`cappedValueEntries`, `WCP:7575-7584@core-work`) and the touch UI (`CameraPage.qml:858-860@ui-work`) still add the ceiling, so the screens offer a step (e.g. 27 at 4K Clear HDR 16-bit, DB-15) the knob cannot reach. The commit's "add the ceiling to the list in UI.conf" is no way back: a fixed 27 shows in every mode. But request 24 does change a stock camera (1.6.0 `availablePcfFpsOptions`, `App:1150-1167@upstream-1.6.0`, and the WebUI `availableFpsOptionsForSnapshot`, `WCP:4992-5021@upstream-1.6.0`, list presets at or under the ceiling, hide the rest, add the ceiling only when none fits). Variant: one `UI.conf [General]` bool next to the T33 keys (e.g. `stepsAddCeiling`, default false = 1.6.0, written by `set_value_steps`), read by Core's `selectableValueSteps`, the WebUI and the touch `cappedValueEntries`: false = 1.6.0 on all three screens (values above hidden, ceiling only when none fits), true = request 24 everywhere. Keep the commit's free-stepping ceiling (`selectableValueCeiling`) as it is. His rig sets the key (step 7) |

Not his camera's hardware (Pi checks to mark "not run" or hand to the original developer): C1 second gpiochip; C20,
C21 IMU writes (no IMU); C24 Pi 4 / CM4 timings; U2, U3, C12 touch-screen checks (seen on HDMI with a mouse, DA-77).

## Steps for the owner's rig before the improvement branch goes on it

He runs every `sudo`, restart and drop-in himself; Claude gives the block (standing rule).

| # | check or command | why |
| --- | --- | --- |
| 1 | `grep -A12 '^\[display\]' ~/apertar-hardware.conf` shows `ui_width=1920 ui_height=1080 ui_layout=landscape_large hdmi_external_only=true` | C2, U1: the fallback is the 720x720 panel again |
| 2 | `grep -c '^preview_tdn=false' ~/.config/apertar-core/camera_settings.conf` is not 0; if 0: `python3 ~/apertar-kb/working/tools/core.py set_preview_tdn enabled=false` | C9: TDN on cost 128 frames at 4K Clear HDR 16-bit 25 fps on 2026-11-11 |
| 3 | `python3 ~/apertar-kb/working/tools/core.py set_storage_preroll value=on`, then `grep -A2 '^\[media\]' ~/apertar-hardware.conf` shows `preroll=on` | C5: pre-roll off by default; `longtakes.py:2766` and `e3-unit.sh:19-20` need it on |
| 4 | `sudo systemctl edit apertar-core` with `[Service]` / `Environment=APERTAR_SCRIPT_PATHS=ssh`, `sudo systemctl daemon-reload`, `sudo systemctl restart apertar-core`; check `tr '\0' '\n' < /proc/$(systemctl show -p MainPID --value apertar-core)/environ \| grep SCRIPT_PATHS`. Undo: `sudo systemctl revert apertar-core` only if no other drop-in lives in `override.conf` (else delete the line) | C29: keeps his Q2; unset, the WebUI may set script paths as in 1.6.0 |
| 5 | `grep recordingRedTimecodeEnabled ~/.config/CinePi/UI.conf` (present, `=true`, on 2026-11-11) | U3: HDMI is red only while the key is stored |
| 6 | Optional: `python3 ~/apertar-kb/working/tools/core.py set_audio_recorded_outline_enabled enabled=true` (or the switch in Settings > Monitoring) | U2, C3: his `UI.conf` has no key, so the outline goes off |
| 7 | If 19e7eb8 lands with the variant: `stepsAddCeiling=true` under `[General]` in `~/.config/CinePi/UI.conf` (name per the final commit) | request 24 on knobs, buttons and both screens |
| 8 | If he records binned 1920x1080 12-bit Clear HDR (2kHDR12): build with `git revert a36c52f`, or wait for the hdr12 P7 capture pair | C13 holds the mode back |
| 9 | `time python3 ~/apertar-kb/working/tools/core.py scan_i2c bus=1` lists 0x34 and 0x49 in well under 1 s | C24: a slower healthy scan is refused |
| 10 | KB, not the Pi: `working/tools/controls_store_test.cpp` gets `setenv("APERTAR_SCRIPT_PATHS", "ssh", 1);` before section 5 (line 137) | C29: lines 149 and 151 fail without it |
| 11 | One 60-s lossy 3:1 probe at the estimator's settings (4K, 60 fps) against the 2026-11-11 result | C6: the lossy write path changed under `sync` |
| 12 | Only when the imx283 driver from the draft PR is installed (he decides, DB-81): `cat /sys/module/imx283/parameters/crop_vmax` prints `N`; his modprobe line `crop_vmax=0` can stay | D2-1 |

## The review's open questions, against his recorded decisions

| # | answered by | the answer |
| --- | --- | --- |
| 1 storage switches location | open | DA-3 (Core owns the hardware file) fits A; DA-84 needs per-instance files either way; the storage audit's read-only takeover stands |
| 2 Boot Config "Edit file" | open | DA-78 / DA-79 / DB-82 bind both options (in place, Apertar layout, no fence, no template); DA-81 rollback. No decision on free text |
| 3 IMX585 1.85:1 names | open | DB-78: the duplicate `3840x2072` entry "left for the owner to decide"; DB-81 ask before a driver change |
| 4 FPS ceilings, lossless policy | DB-52, DB-35 / DA-94, DB-17 / DA-96, DB-20, DB-21 | Keep his: fps max from the probe (`APERTAR_FPS_LIMIT=table` restores the table), lossless ISO 1600, auto ISO in lossless. Option B in form; stock at 1.6.0 behind the switch. Recommendation A contradicts DB-52 |
| 5 media tuning file | 2026-11-02 request (`media-tune-file.md:3-5`), DA-104 / DB-65, DA-88 | B: keep the file, `/run` override and `apertar-tune` (storage audit) |
| 6 first-run file writer | DA-3 / Q1 | A: Core |
| 7 Mode Ladder persistence | open | no decision on the file |
| 8 Mode Ladder rules | DB-49 (in part) | "no illegal values (the editor never sends what Core would refuse)": Core is the authority, so A, but the approved editor's look and behaviour stay (DB-49, DB-51) |
| 9 timecode split and labels | DA-76; DA-99 none | Keep the split (`set_timecode_mode target=ui\|files\|both`), labels Free Run / Rec Run (his words); stock default "same as mode" |
| 10 clip-name drag and drop | open | DA-42 is the Controls editor's drag, not clip names |
| 11 keep the big features | DA-104 / DB-65, DA-105 / DB-66, DA-43, DA-1, DB-22 / DB-27 | Keep all; each that changes a stock camera off by default |
| 12 hardware-file engines | DA-3, DA-20, DA-25 (store, history, merge); DA-1 manual editing; DA-78 (Boot Config engine) | Keep the store and hwconf (the merge DA-20 and the checks depend on it); Boot Config engine size follows row 2 |
| 13 edge events, phase lock, fsync sweep, safety stop | DA-35; DA-87 / DB-56; DB-60 / DB-65; DB-61 | Keep all four (phase lock off) |
| 14 host tests | open | DA-15 (his live file as fixture) favours keep |
| 15 structured editor | DA-1, DA-37, DA-42 (in part) | Chip box (multi-action drag) is his "drag and drop" request (DA-42): keep. Pin-claim cascade and review re-derivation: open |
| 16 script paths from the browser | DA-4 / Q2, DA-28, DA-29 | B, done: C28 + C29, `APERTAR_SCRIPT_PATHS=ssh` on his rig, 1.6.0 unset |
| 17 phone Back | DA-43, design D19, DA-56 (tried, `fork-log.md:102`) | Keep |
| 18 stretched WAV | DA-93 / DB-30, request 19 | Keep in Core, default on, fixed launch (speed ramp is off by default, so stock unaffected) |
| 19 fan mode through Core | DA-80 | Keep the single writer |
| 20 raw request count | open | none |
| 21 pre-roll fps | hardware-log 842-855 (sensor maximum confirmed by him), DB-52; preroll audit | Not "recordable maximum" while `longtakes.py:3194-3205` uses the pre-roll as the encoder reading; sensor maximum or the audit's B |
| 22 button held at start | DA-34, DA-39 | Keep the inversion behind `invert_on_start` (default off = 1.6.0); against the recommendation |
| 23 IMX585 size the class lacks | open | none (C13's Pi check expects today's refusal) |
| 24 imx585 960/1024 families | open | DB-78, DB-81: driver tables are his |
| 25 knob-arrow hold-to-repeat | open | DA-48 covers frame step only |
| 26 the word Auto in badges | open | DB-33 binds the colour (auto values white, not italic), not the word |
| 27 white Controls dropdowns | open | no "(Patrik)" on `d44b177` |
| 28 presets carry TDN and trim | open | DA-92 puts `conform_fps` in presets; nothing on TDN or trim |
| 29 sensor_binning fields | open | no KB tool reads them (`grep` of `working/tools/*.py`) |
| 30 AI attribution | standing rules (DA-59, DB rules) in part | In the fork: Claude's commits carry `Co-Authored-By`, his typed commits none, "User" never his name. The form for upstream stays his |
| 31 driver branch | open | DB-80 / DB-81: ask him; the installed driver is what runs |

Answered: 4, 5, 6, 9, 11, 12, 13, 16, 17, 18, 19, 21 (in part), 22; partly: 8, 15, 30. Open: 1, 2, 3, 7, 10, 14, 20, 23-29, 31.
