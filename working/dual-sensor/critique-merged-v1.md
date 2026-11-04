<!-- Dual sensor, design panel (2026-11-04): the completeness critic of design-merged-v1.md, which re-read the code (Core 31d5418, UI c153c33). Frozen: what was taken over is in design-dual-sensor.md and changes-from-critique.md. -->

# Dual sensor: critique of the merged design v1

## Verdict

Not ready yet. The three claims the design leans on most hold in code: one hook with four callers, start-at-T as one value (CC:7631/7649), and the Sound Recorder pattern. Two holes would still make two-camera takes silently wrong. First, forwarded presets and the resync write UI.conf keys such as standbyTimeoutSeconds and photoModeEnabled into cam1. Second, 'idle' ignores the primary's storage pre-roll and photo mode, so cam1 can be resynced to the pre-roll fps just before a take. Once those are fixed, REC is gated on cam1's pending writes and in-flight changes, and the 500 ms lead applies only to takes that include cam1, it can become the plan. The rest are edits to §1-§4 and to the step checks.

## Points

### P1 · HIGH · Presets and resync (§2)

- **Issue.** A forwarded apply_preset, and the resync built from it, write UI.conf keys into cam1's own UI.conf. The design strips only the clip template, audio and gyro keys, which breaks its own rule that UI.conf keys are primary only. (1) standbyTimeoutSeconds turns cam1's idle timer on. That timer is off today only because cam1's UI.conf holds 0 (claim-check C8). user_activity is not forwarded and polls do not count as activity, so cam1 goes to standby on its own, for example during a long cam0-only take, when it gets no commands. It then stays asleep until the primary itself sleeps and wakes, and every take in between silently drops it as not ready. (2) photoModeEnabled puts cam1 into still mode, and every secondary start applies it again from UI.conf.
- **Evidence.** apply_preset writes UI.conf keys through addBoolUpdate/addStringUpdate: photoModeEnabled at App:13996@31d5418 and standbyTimeoutSeconds at 14070 (block 13994-14071). photoModeEnabled also goes into presetSettings (13772-13773). Every saved preset carries both (7782, 7814). The idle loop reads that instance's own UI.conf every second and fires enter_standby (8269-8281). Only its own takes (8270-8273) and the commands at 12229-12235 reset it. Start restores photo mode from UI.conf (8042-8048). Design §2: 'without the clip template, audio and gyro keys'; 'user_activity ... not forwarded | idle standby is off on cam1 (claim-check C8)'.
- **Fix.** Send cam1 only the camera keys that apply_preset parses into presetSettings, minus photoModeEnabled, photoLongExposureEnabled and cameraClipNameTemplate. Send none of the addBoolUpdate/addStringUpdate (UI.conf) keys. Apply this to user presets and to the resync, then add set_mode_ladder. In the role gate, also skip the idle-standby loop (App:8253-8285) and the photo restore at start (8042-8048) on the secondary. T58 check: apply a preset that has standbyTimeoutSeconds=60 and photoModeEnabled=true. cam1's UI.conf stays unchanged and cam1 is still awake after 2 min.

### P2 · HIGH · Meaning of 'idle' for the compare, the resync and the secondary's start wait (§1, §2)

- **Issue.** The design never defines 'only while both cameras are idle'. The secondary's start wait checks only recording:true. Both miss the primary's storage pre-roll, which runs at every start, card insert and format. The pre-roll is a real take, but it leaves `recording` false and runs at a raised fps. The 1 s compare therefore sees an fps difference, and the resync applies the pre-roll fps to cam1 as an ordinary setting. If REC comes after the pre-roll ends but before the next compare and resync, a both-camera take starts with cam1 at the pre-roll fps. Each Core's take gates then block every fix until the take ends. Photo mode does the same thing: it swaps the primary to the still profile's resolution, bit depth, Clear HDR and fps, and the compare pushes those to cam1. Each resync is a manager start on cam1, which writes HBLANK on cam0's sensor (X7). The secondary's own start can also land inside the primary's start pre-roll.
- **Evidence.** Pre-roll: it saves settings_ and applies fps = prerollMaximumFps without committing (CC:11908-11933@31d5418), then calls session_->startRecording with prerollTake_ set (11946-11956). isRecording returns recording_ (CC:12458-12462). get_state has recording = camera || sound (App:12503). The pre-roll has its own gate (App:12199-12203). storage_preroll_active is in the buffer text (App:245-259), and that event is broadcast at once (14435). A start pre-roll runs on the first mounted cycle (StoragePreroll.hpp:186-196). Photo mode restores the still geometry (CC:11124-11148, 12636-12652). Claim-check X7: reconfigure 'only while neither camera records'.
- **Fix.** Use one idle test for the compare, the resync and the secondary's start wait. Idle means: camera Ready, and none of recording, storage_preroll_active, timelapse_active, still_exposure_active, media_writes_pending or photo mode. Do not compare in photo mode. The secondary reads storage_preroll_active from the primary's buffer event, so no new name is needed. T61 check: with the simulated cam1 linked, run storage_preroll on the primary. cam1's fps never changes.

### P3 · MEDIUM · Start at T on takes without cam1 (§4 Start, decision 4)

- **Issue.** Step 1 sets T = now + 500 ms on every record_start. Nothing limits the lead to takes that include cam1. The single-camera rig and every cam0-only take therefore start frame 0 about 0.5 s later than today. REC, the tally and the trigger pulse still fire at command time, so the gap from the pulse to frame 0 grows by about 0.5 s. This step breaks 'with no second camera the rig behaves exactly as today'.
- **Evidence.** startRecording returns right after it sets recordingStartBootUs_ (CC:7631-7632, 7649-7650@31d5418). It also emits the recording event (CC:11867), and the tally and the RecordingStart pulse follow that event (App:14465-14468). T59's check covers only an explicit start_us.
- **Fix.** Send start_us and add the lead only when cam1 is in the take. A take without cam1 keeps today's 'now'. T59/T61 check: with no cam1 configured, the journal shows frame 0 within one period of the press, as before.

### P4 · MEDIUM · Back-to-back takes while cam1 is still writing (§4)

- **Issue.** A quick REC after a stop fails in two ways. (1) The primary refuses REC while its own writes are pending. cam1's pending writes only make cam1 'not ready', so cam1 is dropped from the take with no refusal. (2) The relay learns `writing` only from the 1 s poll, and that poll waits behind cam1's stop and its syncfs. A stale `ready` therefore queues record_start behind the stop, and cam1 starts late. The design only logs late starts. The media-delete gates also check only cam0's pending writes.
- **Evidence.** App:12204-12206@31d5418: record_start refuses with 'Wait for the current capture to finish writing to media.' while camera_.mediaWritesPending(). Pending includes recordingStopInProgress_ and h264 finalizing (CC:7368-7378) and stays set through syncfs (CC:4744, 7714-7716). get_state is answered under commandMutex_ (App:12176-12182, 12498). media_write_state is broadcast at once (14434), but the relay 'skips every event except recording'. Delete gates: 8990 and 9072. Claim-check R2 asks to 'refuse or flag a T that has already passed'.
- **Fix.** (a) The record_start gate (12204-12206) also refuses while cam1 would be in the take and is writing: 'Wait for CAM1 to finish writing to media.' (b) The relay also reads cam1's media_write_state event. (c) The secondary refuses a start_us more than one period in the past, so the state becomes refused with the message 'late'. (d) The delete gates at 8990 and 9072 also check cam1's pending writes.

### P5 · MEDIUM · REC while cam1 is still applying a forwarded change (§2 take-state rules)

- **Issue.** cam1 runs a forwarded reconfigure or wake after the primary has already replied ok. That covers resolution, format, Clear HDR, bit depth, an fps rung change and the resync's apply_preset. Each of these is a CameraManager start. The take-state rules gate cam1 only while it records. A REC pressed during cam1's change therefore starts cam0's take while cam1's manager start writes HBLANK=min on cam0's streaming sensor, and cam1 joins late or not at all. A poll cannot see this, because cam1's get_state waits behind that same command.
- **Evidence.** Design §2: 'After a local ok, the wrapper queues "both" commands for cam1.' Claim-check new finding 4 (block 3): every manager start (Core start, standby wake, reconfigure) runs sensor init on every sensor (CC:7445-7448, 7247@31d5418). X7: one frame at min_hmax plus a phase step. get_state runs after commandMutex_ (App:12176-12182, 12498); only five read-only commands answer before the lock (12032-12171).
- **Fix.** The relay marks cam1 busy from the moment it sends a reconfigure-type command or wake until the reply arrives. In that window record_start refuses with the existing 'One moment.' pattern (App:12198, 12203), for example 'CAM1 is applying a change. One moment.' After a bounded time, drop cam1 from the take. T58 check: send set_resolution, then REC within 1 s.

### P6 · MEDIUM · cam1 stopping alone mid-take (§4 Failures, risk 4)

- **Issue.** The design says cam0 keeps rolling after cam1's buffer safety stop. But every stop runs syncfs on the whole exFAT volume, and on this rig a syncfs during a take stalled the writers. So a cam1 safety stop can cost cam0 frames or set off cam0's own safety stop. A cam1 safety stop is most likely to happen when the shared NVMe is saturated, which is exactly when cam0 is most exposed. Risk 4's fio test does not measure this.
- **Evidence.** syncToMedium calls ::syncfs (CC:4744@31d5418) after each stop (7714-7715). CC:4314-4318: 'syncfs here waited for every page in flight and stalled the writers: 782 queue drops in 3 min'. Claim-check new finding 3 (block 3).
- **Fix.** While the primary records, the secondary skips the stop syncfs. Its once-a-second fsync of its own files already bounds the loss (CC:4314-4316); fsyncing only its own folder also works. T55 adds a measurement: run `sync -f /media/RAW` during a 4K take and count drops.

### P7 · MEDIUM · cam1-only take that is lost or safety-stopped (§4)

- **Issue.** The primary publishes recording active:true for a cam1-only take but sends active:false only on record_stop. If cam1 is lost or safety-stops, the tally stays red, REC stays shown, and syncRecordingTracking(true) is never undone. If cam1RecordingActive() means 'the take includes cam1' rather than 'cam1 reports recording', `recording` also stays true. The restarted secondary then waits forever, because it waits while the primary shows recording:true.
- **Evidence.** The Sound Recorder publishes and syncs tracking at both ends: App:10031-10034 and 10045@31d5418 (syncRecordingTracking at 9949). The tally follows the event (14465-14472). The design describes the cam1-only take in §4 and the secondary's start wait in §1.
- **Fix.** Define cam1RecordingActive() as cam1.state == recording. On `lost`, or when cam1 stops on its own during a cam1-only take, publish active:false and call syncRecordingTracking(false), as stopSoundRecording does. Extend T61's 'cam1 killed mid-take' check: tally off, recording false, and the restarted cam1 links again.

### P8 · MEDIUM · One side refuses a forwarded setter (§2)

- **Issue.** There is no rule for a non-ok reply to a forwarded command. The compare checks 8 fields, but the resync sets about 40. A refusal or drift in any of these goes unseen: fps_phase_lock, timecode mode, conform fps, cDNG log and compression, h264 options, the HDR knobs, speed ramp, tuning and the ladder. For example, a cam1 that refuses set_fps_phase_lock runs unlocked: no sync, and no warning.
- **Evidence.** Design §2 has the 8-field compare list. settingsBody carries the other fields, fps_phase_lock among them (App:298-356@31d5418, 352). The relay already matches replies by id. Claim-check R4: compare the resulting state.
- **Fix.** A non-ok reply sets cam1.message and schedules one resync at the next idle moment. The compare covers every field the resync sets.

### P9 · MEDIUM · Hand-run test Cores in T57, T58, T61 and T63 (steps)

- **Issue.** No step gives the command line, and the start script cannot pass --simulate. A test Core started without --socket binds the primary's socket at once, because under --simulate it opens no camera first. Without --web-port it then fails on :8000, and its stop() unlinks /tmp/apertar-core.sock, which is the primary's socket file. Without XDG_CONFIG_HOME and APERTAR_HARDWARE_CONFIG, the resync writes the primary's UI.conf and camera_settings.conf. Separately, T61's check 'format_media refused while cam1 writes' cannot pass with a simulated cam1, because a simulated Core never has pending writes.
- **Evidence.** scripts/start-apertar-core.sh:44@31d5418 and the design's ARGS have no --simulate. Claim-check C1: ControlServer.cpp:124 unlinks, then binds. C2: a failed web bind calls controlServer_.stop() (App:8067-8077), which unlinks the path (ControlServer.cpp:169-170). C5: config dirs are shared. CC:12331-12335: mediaWritesPending() is false when simulateCamera_ is set.
- **Fix.** Give one full line in T58 and reuse it in T61 and T63: `XDG_CONFIG_HOME=/home/pi/.config-cam1 APERTAR_HARDWARE_CONFIG=/home/pi/apertar-hardware-cam1.conf APERTAR_STORAGE_PREROLL=0 APERTAR_MEDIA_TRIM=0 APERTAR_MEDIA_TUNE=0 /home/pi/ApertarCore-build/apertar-core --simulate --camera cam1 --socket /tmp/apertar-core-cam1.sock --web-port 8001 --media /media/RAW`. T57 uses the same line without --simulate and with --camera i2c@88000. Move the writes-pending check to T66.

### P10 · MEDIUM · Start order at boot and on every PartOf restart (§1)

- **Issue.** Under 'no primary socket means no take', the secondary never waits at boot. The primary binds its socket only after its camera start, so at every boot and restart both Cores probe and configure at the same moment. This drops two requests: r2's 'ordering after the primary's camera open' with a restart backoff, and D1b's 'configure one after the other'.
- **Evidence.** Camera start App:8034, socket bind 8056@31d5418. r2-core-instances.md:107: 'ordering after the primary's camera open (avoids two simultaneous probes), restart backoff'. Claim-check D1b: 'Relay configures one after the other to rule out the min_vmax race'. The probe toggles WDR (CC:7159). C2: a restart loop re-runs the probe each time.
- **Fix.** The secondary waits up to about 30 s for the primary's socket to accept a connection, then waits for the idle test, and proceeds after the timeout. Add RestartSec to the cam1 unit. T66 check: after a boot, cam1's 'Registered camera' line comes after the primary's socket bind.

### P11 · MEDIUM · Photo mode and timelapse with a cam1 preview source (§3, §4)

- **Issue.** Photos and timelapse run on the primary only, but in photo mode the HDMI can still show Cam 1 or PiP Cam 1 full screen. The operator frames on cam1 while the capture button shoots cam0. Neither §3 nor §4 says what the HDMI or the WebUI shows in photo mode.
- **Evidence.** The hardware capture_photo and timelapse dispatches are at App:10541-10563@31d5418, and still_mode maps to set_photo_mode_enabled at 10592. The design's layout table and its §4 'Which cameras' cover recording only.
- **Fix.** In photo mode or during a timelapse, treat cam1 sources as Cam 0, the same fallback as 'cam1 not ready', or tag the screen 'PHOTO · CAM0'. Pair this with no compare in photo mode.

### P12 · LOW · :8001 POST routes (§1, §2, T57)

- **Issue.** The secondary allowlist sits on the command path, but only /api/command reaches handleCommand. Every other POST on :8001 bypasses it. /api/config writes cam1's hardware file and can switch its buffer mode. The preset routes write the shared store. Media delete is gated only on cam1's own take, so a delete through :8001 can remove the folder cam0 is writing. Boot-config writes config.txt. §1 says 'reads and MJPEG only' and T57 says 'POSTs refused', but neither names a mechanism.
- **Evidence.** /api/command App:9180@31d5418. /api/config 8588 (store.replace, then refreshBufferRequest at 8632). Presets 8861, 8909 and 8946. Media delete 8972 and 9054, gated at 8983/8990 and 9065/9072. Boot-config 9136.
- **Fix.** On the secondary, one check in the HTTP dispatch refuses every POST. T57's check lists the 7 routes.

### P13 · LOW · Role gate: low-power restores (§1)

- **Issue.** The role gate skips standby's machine-wide steps but not the restores. App::start and App::stop also run the low-power restore and turn USB back on, and so does wake. A secondary restart or stop during the primary's standby therefore takes the whole Pi out of low power. A relink during standby also leaves cam1 awake.
- **Evidence.** App:7985-7997, 8163-8172 and 12294-12304@31d5418. Claim-check C8: 'Also not switchable: the low-power restore at every start and stop'. New finding 2 (block 3): 'a role flag (no power button, no restore)'.
- **Fix.** Skip the start, stop and wake restores on the secondary. On wake, the secondary's restore only repeats the primary's. On relink, if the primary is in standby, send enter_standby to cam1. T57 check: with the standby flag files present, the secondary's start and stop log no restore.

### P14 · LOW · cam1 unit environment (§1)

- **Issue.** APERTAR_MEDIA_TUNE=0 is missing from the cam1 unit. Without it, the shared /home/pi/apertar-media-tune.conf decides through kernel_tune. The secondary's media watcher then also applies and restores the block queue and vm.dirty_* settings when the mount changes.
- **Evidence.** App:11361-11367@31d5418. MediaTune.hpp:27 (kMediaTuneBasePath is a fixed path). App:10903 and 10923. Claim-check new finding 7 (block 3).
- **Fix.** Add APERTAR_MEDIA_TUNE=0 to the cam1 unit's Environment.

### P15 · LOW · Relay reply parsing (§2, T58)

- **Issue.** The relay needs scalar fields from cam1's get_state, and the existing parsers cannot read them. The flat parser stops at the first `}` (claim-check R6), and nested arrays and objects come before recording_format, clear_hdr and fps_phase_lock. extractJsonStringField reads strings only.
- **Evidence.** settingsBody: ladder_tops at App:319@31d5418, then the exposure-metering object (325), recording_capabilities (338), recording_format (339), preview_exposure_reference (349), clear_hdr (351) and fps_phase_lock (352). extractJsonStringField is at 5918.
- **Fix.** Name one helper that reads a number, bool or string by key and skips nested values, and size it into T58.

### P16 · LOW · Camera pick with a dead cam0 (§1)

- **Issue.** With cam0's sensor dead and a cam1 sensor configured, 'else today's rule' gives cam1's sensor to the primary. When the first CFE registers no camera, the next camera's handler holds all four media devices. The secondary then fails to acquire and loops under Restart=on-failure, and each try is a manager start on the sensor the primary is using.
- **Evidence.** Design §1 'Camera pick' (CC:7262-7265@31d5418). Claim-check new finding 1 (block 1): the next camera's handler holds both pipelines. C2: the restart loop.
- **Fix.** When config.txt names a cam1 sensor, the primary does not fall back to it. Alternatively, the secondary exits 0 on EBUSY with one log line.

### P17 · LOW · Second HDMI pane is 'clean' (§3)

- **Issue.** 'Clean' also drops the display transforms, not just the overlays. The LUT, anamorphic desqueeze, SMPTE, displayRotation and previewAspectRatio are not overlay-gated. In Both, cam0 shows the LUT look while cam1 shows flat log, and on a rotated monitor the cam1 pane is not rotated.
- **Evidence.** EMW:404-428@c153c33: zebra, peaking, grayscale and false colour are overlay-gated. lutPreviewEnabled, lutPreviewFile, smpte, desqueeze, displayRotation and previewAspectRatio are not.
- **Fix.** Both panes keep the display transforms. Only the overlays and guides stay on the main pane.

### P18 · LOW · cam1 preview client during takes (§3, T62)

- **Issue.** The new preview client is not connected to setRecording. The recording preview-fps cap (APERTAR_UI_PREVIEW_RECORDING_FPS) therefore reaches only cam0's client, and cam1's client keeps drawing at full rate during takes, when GUI-thread load matters most (risk 8).
- **Evidence.** UI src/main.cpp:351-352@c153c33 connects recordingChanged to apertarPreviewBridge.setRecording only. setRecording is declared in ApertarPreviewSocketClient.hpp.
- **Fix.** Connect the second client in T62. In T63, compare drops during a take with both clients running.

### P19 · LOW · Sound Recorder mode (§2 state, §3 WebUI)

- **Issue.** With soundRecorderEnabled set, REC records sound only and returns before the camera path, so cam1 is never told to start. Yet record_cameras and the 'REC CAM0 + CAM1' label still name cameras.
- **Evidence.** App:14225@31d5418: soundOnly falls back to the UI.conf key. App:14284-14291: the sound-only branch returns. The camera path, where the start-at-T code goes, begins at 14294.
- **Fix.** While sound-only, omit record_cameras or set it to none, and label the button REC SOUND. Refuse an explicit `cameras` in that mode.

### P20 · LOW · Speed ramp (T31) with two cameras (§4, §5)

- **Issue.** The design says nothing about speed ramps with two cameras. In a cam1-only take the ramp is refused: the cam1-busy rule allows only exposure setters. In a both-camera take, each fps step reaches cam1 one relay latency later and releases both phase locks. Each lock then needs 250-350 frames to pull in, so the cameras are not synced during a ramp.
- **Evidence.** CC:7490-7493@31d5418: any fps change releases phaseLock_. Claim-check X-new2 gives the pull-in time. Design §2 has the cam1-busy row.
- **Fix.** State both facts in §4 and §5. Add a question with a default: 'Speed ramp in two-camera takes? Default: allowed, unsynced during the ramp, refused in cam1-only takes.'

### P21 · LOW · Questions for Patrik (§8)

- **Issue.** Four decisions have no question or default. (a) Do presets carry recordBothCamerasEnabled? recordAudioEnabled and externalMonitorMode are already in presets. (b) Should a hardware button cycle the preview source? With no touch screen, the WebUI is the only way to change it. (c) An explicit `cameras` that names a not-ready cam1 is refused, so a NEXT TAKE 'Both' press records nothing. That conflicts with the default 'cam0 rolls alone'. (d) Both cameras write the same DNG serial and camera label.
- **Evidence.** Preset keys: App:7768-7769, 7797 and 14027@31d5418. The external_monitor action: ActionCatalog.hpp:72 and App:10627-10629. Design §4: 'An explicit cameras that names it is refused'. DNG identity: CC:3800-3842.
- **Fix.** Add the four questions with defaults: (a) yes, like recordAudioEnabled; (b) no in v1; (c) cam0 rolls alone and the CAM1 pill says why; (d) unchanged in v1, the _cam1 folder tells the clips apart.

### P22 · LOW · Offline detection (§2, T58)

- **Issue.** T58's 'offline 2 s after a stop' does not say whether offline means EOF or a reply timeout. A timeout rule would mark cam1 offline in the middle of its own stop, because cam1's get_state waits behind its command lock and cam1's safety-stop drain holds that lock. Since §2 drops commands while cam1 is offline, those commands would be lost.
- **Evidence.** Lock at App:12176-12182@31d5418; get_state at 12498. The comment at 12178-12180 says the safety-stop thread 'holds commandMutex_'. Design §2: 'Commands sent while cam1 is offline are dropped'.
- **Fix.** cam1 is offline only on EOF or a failed connect. A slow reply means busy.

### P23 · LOW · 'cam1 configured' by socket file (§1)

- **Issue.** ControlServer removes its socket file only in a clean stop(). A crashed or killed test Core leaves /tmp/apertar-core-cam1.sock behind. The single-camera rig then counts as configured and shows CAM1 OFFLINE and a black Both pane.
- **Evidence.** src/ipc/ControlServer.cpp:169-170@31d5418 unlinks only in stop(). Design §1: 'or the cam1 socket exists (for tests)'.
- **Fix.** Use 'the cam1 socket accepts a connection' instead of 'the file exists'.

### P24 · LOW · WebUI Both during a take (T64, T66)

- **Issue.** With the WebUI showing Both, both Cores encode MJPEG during a take, on top of the two recordings. T64 runs no take, and T66 does not name this case.
- **Evidence.** MJPEG encodes only while a client views it (App:9735@31d5418). The T64 and T66 checks are in design §6.
- **Fix.** Add a T66 take with the WebUI open in Both, and count drops per camera.

### P25 · LOW · cam1 unit install and the no-sensor exit (T56, T57)

- **Issue.** T57 creates the cam1 unit, but no step installs or enables it (Patrik's sudo). No check covers a boot with no sensor (exit 0, so the unit ends inactive, not failed) or a primary restart (PartOf). The unit also inherits APERTAR_RT, which runs both Cores under SCHED_FIFO on the same CPUs 1-3. The no-sensor check must run in main() before app.start(). Inside start() it would come too late: start() first runs the low-power restore and starts the trim, pre-roll and media-watcher threads, and a false start() exits 1.
- **Evidence.** Restore and threads come before camera_.start (App:7985-8034@31d5418). A false start() exits 1 (src/main.cpp:108-111). APERTAR_RT and taskset: scripts/start-apertar-core.sh:20 onward. r2-core-instances.md:107 lists APERTAR_RT_CPUS for the unit.
- **Fix.** Add the install to T56 and T57, with two checks: after enabling, a boot leaves apertar-core-cam1 inactive (exit 0), and a primary restart does not loop. State APERTAR_RT and APERTAR_RT_CPUS for cam1.
